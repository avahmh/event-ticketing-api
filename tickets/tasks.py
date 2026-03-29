from celery import shared_task
from django.utils import timezone

from .models import OutboxEvent
from . import services


@shared_task
def expire_reservations():
    released = services.release_expired_reservations()
    return {"released": released}


@shared_task
def process_outbox():
    events = OutboxEvent.objects.filter(processed=False).order_by("created_at")[:50]
    processed = 0
    for event in events:
        event.processed = True
        event.processed_at = timezone.now()
        event.save(update_fields=["processed", "processed_at"])
        processed += 1
    return {"processed": processed}
