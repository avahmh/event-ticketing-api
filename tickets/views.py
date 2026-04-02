import json
import uuid

from django.shortcuts import render
from django.db import transaction, IntegrityError, DatabaseError
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from events.models import Event
from datetime import timedelta
from django.utils import timezone
from .models import TicketInventory, Order, OutboxEvent, Payment
from . import services
from .payments.service import start_payment, finalize_payment, fake_payment_url
import structlog
import logging
import time
logger = structlog.getLogger()


MAX_RETRIES = 5
RETRY_DELAY = 0.1  # seconds

@csrf_exempt
@require_http_methods(["PATCH"])
def cancel_order(request, order_id):
    try:
        with transaction.atomic():
            order = Order.objects.select_for_update().get(id=order_id)
            if order.status == "cancelled":
                return JsonResponse({"message": "Order already cancelled"}, status=400)
            if order.status != Order.STATUS_CONFIRMED:
                return JsonResponse({"error": "Order cannot be cancelled"}, status=400)
            items = list(order.items.select_related("seat").all())
            if items:
                from .models import EventSeat
                for oi in items:
                    if oi.seat_id:
                        EventSeat.objects.filter(
                            event=order.event,
                            seat=oi.seat,
                        ).update(status=EventSeat.STATUS_AVAILABLE)
            else:
                try:
                    inventory = order.event.inventory
                    inventory.available += order.quantity
                    inventory.save()
                except TicketInventory.DoesNotExist:
                    pass
            order.status = "cancelled"
            order.save()
            logger.info(
                "order_cancelled",
                order_id=order.id,
                event_id=order.event_id,
            )
        return JsonResponse({"message": "Order cancelled", "order_id": order.id})
    except Order.DoesNotExist:
        return JsonResponse({"error": "Order not found"}, status=404)


def get_order(request, order_id):
    try:
        order = Order.objects.get(id=order_id)
        return JsonResponse({
            "id": order.id,
            "event_id": order.event_id,
            "quantity": order.quantity,
            "status": order.status,
            "idempotency_key": order.idempotency_key
        })
    except Order.DoesNotExist:
        return JsonResponse({"error": "Order not found"}, status=404)

def list_event_orders(request, event_id):
    page = int(request.GET.get("page", 1))
    page_size = int(request.GET.get("page_size", 10))
    offset = (page - 1) * page_size
    limit = offset + page_size

    orders = Order.objects.filter(event_id=event_id).values("id", "quantity", "status", "idempotency_key")[offset:limit]

    return JsonResponse({
        "page": page,
        "page_size": page_size,
        "orders": list(orders),
    })


@csrf_exempt
@require_POST
def purchase_ticket(request, event_id):

    quantity = int(request.POST.get("quantity", 0))
    idempotency_key = request.headers.get("Idempotency-Key")

    if not idempotency_key:
        return JsonResponse(
            {"error": "Idempotency-Key header is required"},
            status=400
        )

    if quantity <= 0:
        return JsonResponse(
            {"error": "Invalid quantity"},
            status=400
        )

    event = get_object_or_404(Event, id=event_id)

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            with transaction.atomic():

                # 🔒 DB-level lock
                inventory = TicketInventory.objects.select_for_update().get(
                    event=event
                )

                logger.info(f"Before purchase: available={inventory.available}")

                if inventory.available < quantity:
                    return JsonResponse(
                        {"error": "Not enough tickets available"},
                        status=409
                    )

                # کم کردن موجودی
                inventory.available -= quantity
                inventory.save()

                logger.info(
                    "inventory_updated",
                    event_id=event.id,
                    remaining=inventory.available
                )

                # ساخت سفارش
                order = Order.objects.create(
                    event=event,
                    quantity=quantity,
                    status=Order.STATUS_CONFIRMED,
                    idempotency_key=idempotency_key
                )

                logger.info(
                    "order_created",
                    order_id=order.id,
                    event_id=event.id,
                    quantity=quantity
                )

                OutboxEvent.objects.create(
                    event_type="order_confirmed",
                    payload={
                        "order_id": order.id,
                        "event_id": order.event_id,
                        "quantity": order.quantity
                    }
                )

            return JsonResponse(
                {
                    "order_id": order.id,
                    "status": order.status
                },
                status=201
            )

        except IntegrityError:
            # key duplicate → idempotent retry
            existing_order = Order.objects.get(event=event, idempotency_key=idempotency_key)
            return JsonResponse({
                "order_id": existing_order.id,
                "status": existing_order.status,
                "message": "Duplicate request (idempotent)"
            }, status=200)

        except DatabaseError as e:
            # Detect deadlock or serialization failure
            logger.warning(f"Database error on attempt {attempt}: {e}")
            if attempt == MAX_RETRIES:
                return JsonResponse({"error": "Could not process order, please retry later"}, status=500)
            else:
                # Sleep a bit before retry
                time.sleep(RETRY_DELAY)
                continue

        except Exception as e:
            return JsonResponse(
                {"error": "Internal server error"},
                status=500
            )


@transaction.atomic
def reserve_ticket(request, event_id):

    quantity = int(request.POST.get("quantity"))

    event = Event.objects.get(id=event_id)

    inventory = TicketInventory.objects.select_for_update().get(
        event=event
    )

    if inventory.available < quantity:
        return JsonResponse(
            {"error": "Not enough tickets"},
            status=409
        )

    inventory.available -= quantity
    inventory.save()

    reserved_until = timezone.now() + timedelta(minutes=5)

    order = Order.objects.create(
        event=event,
        quantity=quantity,
        status=Order.STATUS_RESERVED,
        reserved_until=reserved_until,
        idempotency_key=str(uuid.uuid4())
    )

    OutboxEvent.objects.create(
        event_type="ticket_reserved",
        payload={
            "order_id": order.id,
            "event_id": event.id,
            "quantity": quantity
        }
    )

    return JsonResponse({
        "order_id": order.id,
        "reserved_until": reserved_until
    })


@transaction.atomic
def confirm_order(request, order_id):

    order = Order.objects.select_for_update().get(id=order_id)

    if order.status != Order.STATUS_RESERVED:
        return JsonResponse(
            {"error": "Order not reservable"},
            status=400
        )

    if order.reserved_until < timezone.now():
        return JsonResponse(
            {"error": "Reservation expired"},
            status=400
        )

    order.status = Order.STATUS_CONFIRMED
    order.save()

    OutboxEvent.objects.create(
        event_type="order_confirmed",
        payload={
            "order_id": order.id
        }
    )

    return JsonResponse({"status": "confirmed"})


@csrf_exempt
@require_POST
def reserve_seats(request, event_id):
    try:
        body = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    seat_ids = body.get("seat_ids") or []
    idempotency_key = request.headers.get("Idempotency-Key")
    if not idempotency_key:
        return JsonResponse({"error": "Idempotency-Key header is required"}, status=400)
    if not seat_ids or not isinstance(seat_ids, list):
        return JsonResponse({"error": "seat_ids list required"}, status=400)
    seat_ids = [int(s) for s in seat_ids]
    reservation, err = services.reserve_seats(event_id, seat_ids, idempotency_key)
    if err:
        return JsonResponse({"error": err}, status=400 if err != "Reservation conflict" else 409)
    return JsonResponse({
        "reservation_id": reservation.id,
        "reserved_until": reservation.reserved_until.isoformat(),
        "seat_ids": seat_ids,
    }, status=201)


@csrf_exempt
@require_POST
def confirm_reservation(request, event_id):
    try:
        body = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    reservation_id = body.get("reservation_id")
    idempotency_key = request.headers.get("Idempotency-Key") or body.get("idempotency_key")
    if not reservation_id:
        return JsonResponse({"error": "reservation_id required"}, status=400)
    order, err = services.confirm_reservation(
        reservation_id, idempotency_key, event_id=event_id
    )
    if err:
        return JsonResponse({"error": err}, status=400)
    payment = start_payment(
        order=order,
        provider=Payment.PROVIDER_FAKE,
        idempotency_key=order.idempotency_key,
    )
    payment_url = request.build_absolute_uri(fake_payment_url(payment.authority))
    return JsonResponse({
        "order_id": order.id,
        "status": order.status,
        "total_amount": str(order.total_amount) if order.total_amount else None,
        "payment_url": payment_url,
    }, status=201)


def fake_payment_page(request, authority):
    payment = (
        Payment.objects.select_related("order", "order__event")
        .filter(authority=authority)
        .first()
    )
    if not payment:
        return JsonResponse({"error": "Payment not found"}, status=404)

    order_id = payment.order_id
    event_id = payment.order.event_id

    html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><title>Fake Payment</title></head>
<body style="font-family:system-ui,sans-serif;max-width:520px;margin:2rem auto;padding:1rem;">
<h2>Fake Payment Gateway</h2>
<p>Order #{order_id}</p>
<div style="display:flex;gap:0.5rem;">
  <button onclick="pay('success')" style="padding:0.5rem 0.8rem;">Pay Success</button>
  <button onclick="pay('failed')" style="padding:0.5rem 0.8rem;">Pay Failed</button>
</div>
<pre id="out" style="margin-top:1rem;background:#f3f4f6;padding:0.75rem;border-radius:6px;"></pre>
<script>
async function pay(status) {{
  try {{
    const r = await fetch('/payments/fake/callback/', {{
      method:'POST',
      headers: {{'Content-Type':'application/json'}},
      body: JSON.stringify({{authority: '{authority}', status}})
    }});
    let data;
    try {{
      data = await r.json();
    }} catch (e) {{
      data = {{ raw: await r.text(), http_status: r.status }};
    }}
    document.getElementById('out').textContent = JSON.stringify(data, null, 2);
    if (status === 'success' && r.ok) {{
      const redirectUrl = '/?paid=1&event_id=' + encodeURIComponent(data.event_id || '{event_id}');
      if (window.opener && !window.opener.closed) {{
        try {{
          window.opener.location.href = redirectUrl;
        }} catch (e) {{}}
      }}
      setTimeout(() => {{
        window.location.href = redirectUrl;
      }}, 700);
    }}
  }} catch (e) {{
    document.getElementById('out').textContent = 'JS error: ' + String(e);
  }}
}}
</script>
</body>
</html>"""
    return HttpResponse(html)


@csrf_exempt
@require_POST
def fake_payment_callback(request):
    try:
        body = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    authority = body.get("authority")
    status = body.get("status", "failed")
    if not authority:
        return JsonResponse({"error": "authority required"}, status=400)
    success = status == "success"
    try:
        result = finalize_payment(
            authority=authority,
            provider=Payment.PROVIDER_FAKE,
            success=success,
        )
    except Payment.DoesNotExist:
        return JsonResponse({"error": "Payment not found"}, status=404)
    return JsonResponse(result)


@csrf_exempt
@require_POST
def pay_order(request, order_id):
    try:
        body = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    status = body.get("status", "success")
    success = status == "success"
    try:
        payment = Payment.objects.select_related("order").filter(
            order_id=order_id,
            provider=Payment.PROVIDER_FAKE,
        ).first()
        if not payment:
            return JsonResponse({"error": "Payment not found"}, status=404)
        result = finalize_payment(
            authority=payment.authority,
            provider=Payment.PROVIDER_FAKE,
            success=success,
        )
        result["message"] = "Payment captured" if success else "Payment failed, order cancelled"
        return JsonResponse(result)
    except Order.DoesNotExist:
        return JsonResponse({"error": "Order not found"}, status=404)