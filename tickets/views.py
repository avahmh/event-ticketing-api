from django.shortcuts import render
from django.db import transaction, IntegrityError, DatabaseError
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from events.models import Event
from .models import TicketInventory, Order
import logging
import time
logger = logging.getLogger(__name__)

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

            # rollback inventory
            inventory = order.event.inventory
            inventory.available += order.quantity
            inventory.save()

            order.status = "cancelled"
            order.save()

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

                # ساخت سفارش
                order = Order.objects.create(
                    event=event,
                    quantity=quantity,
                    status=Order.CONFIRMED,
                    idempotency_key=idempotency_key
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
