from decimal import Decimal
import os
from django.db import transaction, IntegrityError
from django.utils import timezone
from datetime import timedelta

from events.models import Event, EventSession
from venues.models import Seat
from .redis_lock import MultiRedisLock, seat_lock_keys
from .models import (
    EventSeat,
    Reservation,
    ReservationSeat,
    Order,
    OrderItem,
    OutboxEvent,
)
from .session_stats import seat_taken_for_session


RESERVATION_MINUTES = int(os.environ.get("RESERVATION_MINUTES", "10"))
SEAT_LOCK_TTL_SECONDS = int(os.environ.get("SEAT_LOCK_TTL_SECONDS", "8"))


def sync_event_seats(event):
    """Create/update EventSeat rows from the event hall layout."""
    if not event.hall_id or not event.is_reserved_seating:
        return {"created": 0, "updated": 0, "removed": 0}

    from .models import EventRowPrice

    row_prices = {
        rp.row_label: rp.price
        for rp in EventRowPrice.objects.filter(event=event)
    }
    hall_seat_ids = set()
    created = 0
    updated = 0

    with transaction.atomic():
        for seat in Seat.objects.filter(hall_id=event.hall_id).order_by("sort_order", "id"):
            hall_seat_ids.add(seat.id)
            if seat.kind == Seat.KIND_BLOCKED:
                continue
            price = row_prices.get(seat.row_label)
            es, was_created = EventSeat.objects.get_or_create(
                event=event,
                seat=seat,
                defaults={
                    "status": EventSeat.STATUS_AVAILABLE,
                    "price": price,
                },
            )
            if was_created:
                created += 1
                continue
            if price is not None and es.price != price:
                es.price = price
                es.save(update_fields=["price"])
                updated += 1

        removed = (
            EventSeat.objects.filter(event=event)
            .exclude(seat_id__in=hall_seat_ids)
            .filter(status=EventSeat.STATUS_AVAILABLE)
            .delete()[0]
        )

    return {"created": created, "updated": updated, "removed": removed}


def reserve_seats(event_id, seat_ids, idempotency_key, session_id=None):
    event = Event.objects.get(id=event_id)
    if not event.is_reserved_seating:
        return None, "Event is not reserved seating"
    try:
        keys = seat_lock_keys(event_id, seat_ids)
        with MultiRedisLock(keys, SEAT_LOCK_TTL_SECONDS) as lock:
            if lock is None:
                return None, "Seat is busy, retry"
        with transaction.atomic():
            existing = Reservation.objects.filter(
                event_id=event_id,
                idempotency_key=idempotency_key,
                status=Reservation.STATUS_ACTIVE,
            ).first()
            if existing:
                return existing, None
            seats = list(
                Seat.objects.filter(
                    id__in=seat_ids,
                    hall_id=event.hall_id,
                )
            )
            if len(seats) != len(seat_ids):
                return None, "Invalid or duplicate seat"
            for seat in seats:
                if seat.kind == Seat.KIND_BLOCKED:
                    return None, "Seat not available"
            event_seats = EventSeat.objects.select_for_update().filter(
                event=event,
                seat_id__in=seat_ids,
            )
            by_seat = {es.seat_id: es for es in event_seats}
            if len(by_seat) != len(seat_ids):
                return None, "One or more seats not available for this event"
            session = None
            if session_id:
                session = EventSession.objects.filter(id=session_id, event_id=event_id).first()
                if not session:
                    return None, "Invalid session"
            now = timezone.now()
            for seat in seats:
                if seat_taken_for_session(event, seat.id, session_id, now=now):
                    return None, "Seat already taken or reserved"
            if not session_id:
                for es in by_seat.values():
                    if es.status != EventSeat.STATUS_AVAILABLE:
                        return None, "Seat already taken or reserved"
            reserved_until = now + timedelta(minutes=RESERVATION_MINUTES)
            reservation = Reservation.objects.create(
                event=event,
                idempotency_key=idempotency_key,
                reserved_until=reserved_until,
                status=Reservation.STATUS_ACTIVE,
                session=session,
            )
            total = Decimal("0")
            for seat in seats:
                ReservationSeat.objects.create(
                    reservation=reservation,
                    seat=seat,
                )
                es = by_seat[seat.id]
                if not session_id:
                    es.status = EventSeat.STATUS_RESERVED
                    es.save(update_fields=["status"])
                total += es.price or Decimal("0")
            return reservation, None
    except IntegrityError:
        existing = Reservation.objects.filter(
            event_id=event_id,
            idempotency_key=idempotency_key,
        ).first()
        if existing and existing.status == Reservation.STATUS_ACTIVE:
            return existing, None
        return None, "Reservation conflict"


def confirm_reservation(reservation_id, idempotency_key=None, event_id=None):
    qs = Reservation.objects.filter(
        id=reservation_id,
        status=Reservation.STATUS_ACTIVE,
    ).select_related("event").prefetch_related("seats__seat")
    reservation = qs.first()
    if not reservation:
        return None, "Reservation not found or expired"
    if event_id is not None and reservation.event_id != event_id:
        return None, "Reservation does not belong to this event"
    if reservation.reserved_until < timezone.now():
        return None, "Reservation expired"
    key = reservation.idempotency_key
    with transaction.atomic():
        reservation = Reservation.objects.select_for_update().get(id=reservation_id)
        if reservation.status != Reservation.STATUS_ACTIVE:
            return None, "Reservation already used or expired"
        order = Order.objects.filter(
            event=reservation.event,
            idempotency_key=key,
        ).first()
        if order:
            return order, None
        total = Decimal("0")
        order = Order.objects.create(
            event=reservation.event,
            quantity=reservation.seats.count(),
            status=Order.STATUS_RESERVED,
            reserved_until=reservation.reserved_until,
            idempotency_key=key,
            session=reservation.session,
        )
        for rs in reservation.seats.select_related("seat").all():
            es = EventSeat.objects.get(event=reservation.event, seat=rs.seat)
            price = es.price or Decimal("0")
            total += price
            OrderItem.objects.create(
                order=order,
                seat=rs.seat,
                quantity=1,
                unit_price=price,
            )
        order.total_amount = total
        order.save(update_fields=["total_amount"])
        reservation.status = Reservation.STATUS_CONFIRMED
        reservation.save(update_fields=["status"])
        return order, None


def complete_order_payment(order_id, success=True):
    with transaction.atomic():
        order = Order.objects.select_for_update().get(id=order_id)
        if order.status == Order.STATUS_CONFIRMED:
            return order, None
        if order.status != Order.STATUS_RESERVED:
            return None, "Order is not payable"

        if success:
            order.status = Order.STATUS_CONFIRMED
            order.save(update_fields=["status"])
            if not order.session_id:
                for item in order.items.select_related("seat").all():
                    if item.seat_id:
                        EventSeat.objects.filter(
                            event=order.event,
                            seat=item.seat,
                        ).update(status=EventSeat.STATUS_SOLD)
            OutboxEvent.objects.create(
                event_type="order_confirmed",
                payload={
                    "order_id": order.id,
                    "event_id": order.event_id,
                    "quantity": order.quantity,
                },
            )
            return order, None

        order.status = Order.STATUS_CANCELLED
        order.save(update_fields=["status"])
        if not order.session_id:
            for item in order.items.select_related("seat").all():
                if item.seat_id:
                    EventSeat.objects.filter(
                        event=order.event,
                        seat=item.seat,
                    ).update(status=EventSeat.STATUS_AVAILABLE)
        return order, None


def release_expired_reservations():
    from .models import EventSeat
    now = timezone.now()
    expired = Reservation.objects.filter(
        status=Reservation.STATUS_ACTIVE,
        reserved_until__lt=now,
    ).prefetch_related("seats__seat")
    released = 0
    for res in expired:
        with transaction.atomic():
            res = Reservation.objects.select_for_update().get(id=res.id)
            if res.status != Reservation.STATUS_ACTIVE:
                continue
            res.status = Reservation.STATUS_EXPIRED
            res.save(update_fields=["status"])
            if not res.session_id:
                for rs in res.seats.select_related("seat").all():
                    EventSeat.objects.filter(
                        event=res.event,
                        seat=rs.seat,
                    ).update(status=EventSeat.STATUS_AVAILABLE)
            released += 1
    return released
