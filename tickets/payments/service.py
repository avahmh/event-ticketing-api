import uuid
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from events.models import Event
from tickets.models import (
    EventSeat,
    Payment,
    Reservation,
    Order,
    OrderItem,
    OutboxEvent,
)


def fake_payment_url(authority: str) -> str:
    return f"/payments/fake/{authority}/"


def start_payment(*, order: Order, provider: str, idempotency_key: str) -> Payment:
    if provider != Payment.PROVIDER_FAKE:
        raise ValueError("Unsupported provider")

    existing = Payment.objects.filter(idempotency_key=idempotency_key).first()
    if existing:
        return existing

    payment = Payment(
        provider=provider,
        authority=str(uuid.uuid4()),
        idempotency_key=idempotency_key,
        order=order,
        status=Payment.STATUS_PENDING,
    )
    try:
        payment.save(force_insert=True)
        return payment
    except IntegrityError:
        return Payment.objects.select_related("order").get(idempotency_key=idempotency_key)


def finalize_payment(*, authority: str, provider: str, success: bool) -> dict:
    if provider != Payment.PROVIDER_FAKE:
        raise ValueError("Unsupported provider")

    with transaction.atomic():
        payment = (
            Payment.objects.select_for_update()
            .select_related("order", "order__event")
            .get(authority=authority)
        )

        if payment.status in (
            Payment.STATUS_SUCCEEDED,
            Payment.STATUS_FAILED,
            Payment.STATUS_CANCELLED,
        ):
            return {"order_id": payment.order_id, "status": payment.status}

        order = (
            Order.objects.select_for_update()
            .filter(id=payment.order_id)
            .select_related("event")
            .get()
        )

        reservation = Reservation.objects.filter(
            event=order.event,
            idempotency_key=order.idempotency_key,
        ).select_for_update().first()

        if success:
            order.status = Order.STATUS_CONFIRMED
            order.save(update_fields=["status"])

            if reservation:
                reservation.status = Reservation.STATUS_CONFIRMED
                reservation.save(update_fields=["status"])

            for item in order.items.select_related("seat").all():
                if item.seat_id:
                    item.seat.event_seats.filter(event=order.event).update(status=EventSeat.STATUS_SOLD)

            payment.status = Payment.STATUS_SUCCEEDED
            payment.save(update_fields=["status"])

            outbox_exists = OutboxEvent.objects.filter(
                event_type="order_confirmed",
                payload__order_id=order.id,
            ).exists()
            if not outbox_exists:
                OutboxEvent.objects.create(
                    event_type="order_confirmed",
                    payload={
                        "order_id": order.id,
                        "event_id": order.event_id,
                        "quantity": order.quantity,
                    },
                )
            return {
                "order_id": order.id,
                "event_id": order.event_id,
                "status": order.status,
            }

        order.status = Order.STATUS_CANCELLED
        order.save(update_fields=["status"])

        for item in order.items.select_related("seat").all():
            if item.seat_id:
                EventSeat.objects.filter(
                    event=order.event,
                    seat=item.seat,
                ).update(status=EventSeat.STATUS_AVAILABLE)

        if reservation:
            reservation.status = Reservation.STATUS_CANCELLED
            reservation.save(update_fields=["status"])

        payment.status = Payment.STATUS_FAILED
        payment.save(update_fields=["status"])

        return {
            "order_id": order.id,
            "event_id": order.event_id,
            "status": order.status,
        }

