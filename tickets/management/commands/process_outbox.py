from django.core.management.base import BaseCommand
from django.utils import timezone

from tickets.models import OutboxEvent
import structlog

logger = structlog.getLogger()

class Command(BaseCommand):

    help = "Process outbox events"

    def handle(self, *args, **kwargs):

        events = OutboxEvent.objects.filter(
            processed=False
        ).order_by("created_at")[:50]

        for event in events:

            self.publish_event(event)

            event.processed = True
            event.processed_at = timezone.now()
            event.save()

    def publish_event(self, event):

        # print("Publishing event:", event.event_type)
        # print("Payload:", event.payload)

        logger.info(
            "outbox_event_published",
            event_type=event.event_type,
            payload=event.payload
        )