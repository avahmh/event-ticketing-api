from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from tickets.models import Order, TicketInventory


class Command(BaseCommand):

    def handle(self, *args, **kwargs):

        expired_orders = Order.objects.filter(
            status=Order.STATUS_RESERVED,
            reserved_until__lt=timezone.now()
        )

        for order in expired_orders:

            with transaction.atomic():

                inventory = TicketInventory.objects.select_for_update().get(
                    event=order.event
                )

                inventory.available += order.quantity
                inventory.save()

                order.status = Order.STATUS_EXPIRED
                order.save()

                print(f"Expired order {order.id}")