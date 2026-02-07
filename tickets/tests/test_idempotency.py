import threading
from django.test import TransactionTestCase, Client
from django.urls import reverse
from django.db import connection
from events.models import Event
from tickets.models import TicketInventory, Order

class ConcurrentIdempotencyTest(TransactionTestCase):

    def setUp(self):
        self.event = Event.objects.create(title="Concurrent Idem Event", starts_at="2026-03-01T20:00:00Z")
        TicketInventory.objects.create(event=self.event, total=5, available=5)
        self.url = reverse("purchase-ticket", args=[self.event.id])

    def make_request(self):
        client = Client()
        client.post(self.url, {"quantity": 3}, HTTP_IDEMPOTENCY_KEY="idem-concurrent")
        connection.close()

    def test_concurrent_idempotent_requests(self):
        t1 = threading.Thread(target=self.make_request)
        t2 = threading.Thread(target=self.make_request)
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        orders = Order.objects.filter(event=self.event, idempotency_key="idem-concurrent")
        self.assertEqual(orders.count(), 1)

        inventory = TicketInventory.objects.get(event=self.event)
        self.assertEqual(inventory.available, 2)
