from django.core.management.base import BaseCommand
from events.models import Event
from tickets.models import EventSeat
from venues.models import Seat


class Command(BaseCommand):
    help = "Create EventSeat rows for all seats in the event's hall (reserved-seating events only)."

    def add_arguments(self, parser):
        parser.add_argument("event_id", type=int)

    def handle(self, *args, **options):
        event_id = options["event_id"]
        event = Event.objects.get(id=event_id)
        if not event.hall_id or not event.is_reserved_seating:
            self.stdout.write(self.style.ERROR("Event has no hall or is not reserved seating."))
            return
        created = 0
        for seat in Seat.objects.filter(hall=event.hall):
            _, c = EventSeat.objects.get_or_create(
                event=event,
                seat=seat,
                defaults={"status": EventSeat.STATUS_AVAILABLE},
            )
            if c:
                created += 1
        self.stdout.write(self.style.SUCCESS(f"Created {created} event seats for event {event_id}."))
