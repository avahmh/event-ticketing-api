from django.utils import timezone

from venues.models import Seat
from .models import EventSeat, Order, OrderItem, Reservation, ReservationSeat


def _sellable_seat_ids(event):
    if not event.hall_id:
        return set()
    return set(
        Seat.objects.filter(hall_id=event.hall_id)
        .exclude(kind=Seat.KIND_BLOCKED)
        .values_list("id", flat=True)
    )


def session_seat_stats(event, session_id=None):
    sellable = _sellable_seat_ids(event)
    total = len(sellable)
    if not total:
        return {"total": 0, "available": 0, "sold": 0, "reserved": 0, "is_full": True}

    now = timezone.now()
    if session_id:
        sold_ids = set(
            OrderItem.objects.filter(
                order__event=event,
                order__session_id=session_id,
                order__status=Order.STATUS_CONFIRMED,
                seat_id__in=sellable,
            ).values_list("seat_id", flat=True)
        )
        reserved_ids = set(
            ReservationSeat.objects.filter(
                reservation__event=event,
                reservation__session_id=session_id,
                reservation__status=Reservation.STATUS_ACTIVE,
                reservation__reserved_until__gt=now,
                seat_id__in=sellable,
            ).values_list("seat_id", flat=True)
        )
    else:
        sold_ids = set(
            EventSeat.objects.filter(
                event=event,
                seat_id__in=sellable,
                status=EventSeat.STATUS_SOLD,
            ).values_list("seat_id", flat=True)
        )
        reserved_ids = set(
            EventSeat.objects.filter(
                event=event,
                seat_id__in=sellable,
                status=EventSeat.STATUS_RESERVED,
            ).values_list("seat_id", flat=True)
        )

    sold = len(sold_ids)
    reserved = len(reserved_ids - sold_ids)
    available = max(0, total - sold - reserved)
    return {
        "total": total,
        "available": available,
        "sold": sold,
        "reserved": reserved,
        "is_full": available <= 0,
    }


def seat_taken_for_session(event, seat_id, session_id, *, now=None):
    if not session_id:
        es = EventSeat.objects.filter(event=event, seat_id=seat_id).first()
        if not es or es.status != EventSeat.STATUS_AVAILABLE:
            return True
        return False

    now = now or timezone.now()
    if OrderItem.objects.filter(
        order__event=event,
        order__session_id=session_id,
        order__status=Order.STATUS_CONFIRMED,
        seat_id=seat_id,
    ).exists():
        return True
    return ReservationSeat.objects.filter(
        reservation__event=event,
        reservation__session_id=session_id,
        reservation__status=Reservation.STATUS_ACTIVE,
        reservation__reserved_until__gt=now,
        seat_id=seat_id,
    ).exists()
