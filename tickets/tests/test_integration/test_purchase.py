import uuid

from django.test import TransactionTestCase
from django.urls import reverse
import threading
from events.models import Event
from tickets.models import TicketInventory, Order
from django.db import connection

class ConcurrentInventorySafetyTest(TransactionTestCase):

    def setUp(self):
        # ساخت event
        self.event = Event.objects.create(
            title="Test Event",
            starts_at="2026-03-01T20:00:00Z"
        )

        # ساخت inventory
        TicketInventory.objects.create(
            event=self.event,
            total=5,
            available=5
        )

        self.url = reverse(
            "purchase-ticket",
            args=[self.event.id]
        )

    def make_request(self):
        from django.test import Client
        client = Client()
        client.post(
            self.url,
            {"quantity": 3},
            # HTTP_IDEMPOTENCY_KEY="idem-concurrent"
            HTTP_IDEMPOTENCY_KEY=str(uuid.uuid4())

        )
        connection.close()  

    def test_concurrent_purchase_does_not_oversell(self):

        t1 = threading.Thread(target=self.make_request)
        t2 = threading.Thread(target=self.make_request)

        t1.start()
        t2.start()

        t1.join()
        t2.join()

        #  اینا عمداً FAIL می‌ش
        print("orders:", Order.objects.count())
        print(
            "available:",
            TicketInventory.objects.get(event=self.event).available
        )

        self.assertEqual(Order.objects.count(), 1)

        inventory = TicketInventory.objects.get(event=self.event)
        self.assertEqual(inventory.available, 2)
