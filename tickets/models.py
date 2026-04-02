from django.db import models
from events.models import Event


class TicketInventory(models.Model):
    event = models.OneToOneField(
        Event,
        on_delete=models.CASCADE,
        related_name="inventory",
    )
    total = models.PositiveIntegerField()
    available = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.event.title} | {self.available}/{self.total}"


class EventSeat(models.Model):
    STATUS_AVAILABLE = "available"
    STATUS_RESERVED = "reserved"
    STATUS_SOLD = "sold"
    STATUS_CHOICES = [
        (STATUS_AVAILABLE, "Available"),
        (STATUS_RESERVED, "Reserved"),
        (STATUS_SOLD, "Sold"),
    ]
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="event_seats"
    )
    seat = models.ForeignKey(
        "venues.Seat", on_delete=models.CASCADE, related_name="event_seats"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_AVAILABLE
    )
    price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    class Meta:
        unique_together = [("event", "seat")]


class Reservation(models.Model):
    STATUS_ACTIVE = "active"
    STATUS_CONFIRMED = "confirmed"
    STATUS_EXPIRED = "expired"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_EXPIRED, "Expired"),
        (STATUS_CANCELLED, "Cancelled"),
    ]
    event = models.ForeignKey(
        Event, on_delete=models.CASCADE, related_name="reservations"
    )
    reserved_until = models.DateTimeField()
    idempotency_key = models.CharField(max_length=255, unique=True)
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["event", "status"]),
            models.Index(fields=["reserved_until"]),
        ]


class ReservationSeat(models.Model):
    reservation = models.ForeignKey(
        Reservation, on_delete=models.CASCADE, related_name="seats"
    )
    seat = models.ForeignKey(
        "venues.Seat", on_delete=models.CASCADE, related_name="reservation_seats"
    )

    class Meta:
        unique_together = [("reservation", "seat")]


class Order(models.Model):
    STATUS_RESERVED = "reserved"
    STATUS_CONFIRMED = "confirmed"
    STATUS_CANCELLED = "cancelled"
    STATUS_EXPIRED = "expired"

    STATUS_CHOICES = [
        (STATUS_RESERVED, "Reserved"),
        (STATUS_CONFIRMED, "Confirmed"),
        (STATUS_CANCELLED, "Cancelled"),
        (STATUS_EXPIRED, "Expired"),
    ]

    event = models.ForeignKey("events.Event", on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_RESERVED,
    )
    reserved_until = models.DateTimeField(null=True, blank=True)
    idempotency_key = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    total_amount = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True
    )
    currency = models.CharField(max_length=3, default="USD")

    class Meta:
        unique_together = ("event", "idempotency_key")


class OrderItem(models.Model):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, related_name="items"
    )
    seat = models.ForeignKey(
        "venues.Seat",
        on_delete=models.CASCADE,
        related_name="order_items",
        null=True,
        blank=True,
    )
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)


class Payment(models.Model):
    PROVIDER_FAKE = "fake"
    PROVIDER_CHOICES = [
        (PROVIDER_FAKE, "Fake"),
    ]

    STATUS_PENDING = "pending"
    STATUS_SUCCEEDED = "succeeded"
    STATUS_FAILED = "failed"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SUCCEEDED, "Succeeded"),
        (STATUS_FAILED, "Failed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    provider = models.CharField(max_length=20, choices=PROVIDER_CHOICES, default=PROVIDER_FAKE)
    authority = models.CharField(max_length=255, unique=True)
    idempotency_key = models.CharField(max_length=255, unique=True)

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="payments")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class OutboxEvent(models.Model):

    EVENT_TYPES = [
        ("order_confirmed", "Order Confirmed"),
        ("order_cancelled", "Order Cancelled"),
    ]

    event_type = models.CharField(
        max_length=50,
        choices=EVENT_TYPES
    )

    payload = models.JSONField()

    processed = models.BooleanField(default=False)

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    processed_at = models.DateTimeField(
        null=True,
        blank=True
    )

    class Meta:
        ordering = ["created_at"]