from django.shortcuts import render
from django.db import transaction, IntegrityError
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from events.models import Event
from .models import TicketInventory, Order
import logging
logger = logging.getLogger(__name__)


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

    except Exception as e:
        return JsonResponse(
            {"error": "Internal server error"},
            status=500
        )
