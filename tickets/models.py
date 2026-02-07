from django.db import models
from events.models import Event

class TicketInventory(models.Model):
    event = models.OneToOneField(
        Event,
        on_delete=models.CASCADE,
        related_name="inventory"
    )
    total = models.PositiveIntegerField()
    available = models.PositiveIntegerField()

    def __str__(self):
        return f"{self.event.title} | {self.available}/{self.total}"


class Order(models.Model):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    FAILED = "failed"

    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (CONFIRMED, "Confirmed"),
        (FAILED, "Failed"),
    ]

    event = models.ForeignKey(Event, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=PENDING
    )

    idempotency_key = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("event", "idempotency_key")
