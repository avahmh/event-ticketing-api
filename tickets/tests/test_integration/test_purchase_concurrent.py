import threading
import uuid
from django.test import TransactionTestCase, Client
from django.urls import reverse
from events.models import Event
from tickets.models import TicketInventory, Order
from django.db import connection

class TicketPurchaseIntegrationTest(TransactionTestCase):

    reset_sequences = True  # ensures IDs are predictable

    def setUp(self):
        # ساخت event
        self.event = Event.objects.create(
            title="Integration Test Event",
            starts_at="2026-03-01T20:00:00Z"
        )

        # موجودی محدود برای تست concurrency
        TicketInventory.objects.create(
            event=self.event,
            total=5,
            available=5
        )

        self.url = reverse("purchase-ticket", args=[self.event.id])

    def make_purchase(self, quantity=1):
        client = Client()
        # هر درخواست idempotency key یکتا
        key = str(uuid.uuid4())
        client.post(
            self.url,
            {"quantity": quantity},
            HTTP_IDEMPOTENCY_KEY=key
        )
        connection.close()  # خیلی مهم برای هر thread

    def test_concurrent_purchases_with_retry(self):
        """
        شبیه‌سازی چند request همزمان با موجودی محدود
        """
        threads = []
        num_requests = 10  # تعداد request همزمان
        for _ in range(num_requests):
            t = threading.Thread(target=self.make_purchase, args=(1,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # بررسی تعداد orderها و موجودی
        orders_count = Order.objects.count()
        available_tickets = TicketInventory.objects.get(event=self.event).available

        print(f"Orders created: {orders_count}")
        print(f"Available tickets left: {available_tickets}")

        # Assertions
        self.assertEqual(orders_count, 5)
        self.assertEqual(available_tickets, 0)
