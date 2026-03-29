from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from events.models import Event
from tickets.models import EventSeat, TicketInventory
from venues.models import Hall, Seat, Section, Venue, Zone


class Command(BaseCommand):
    help = "Seed TeatrShahr sample venue, hall, seats, and events"

    def handle(self, *args, **options):
        venue, _ = Venue.objects.get_or_create(
            name="TeatrShahr",
            defaults={
                "address": "Daneshjoo Park, Tehran",
                "timezone": "Asia/Tehran",
            },
        )

        hall, _ = Hall.objects.get_or_create(
            venue=venue,
            name="TeatrShahr Main Hall",
            defaults={"capacity_type": Hall.CAPACITY_RESERVED},
        )
        if hall.capacity_type != Hall.CAPACITY_RESERVED:
            hall.capacity_type = Hall.CAPACITY_RESERVED
            hall.save(update_fields=["capacity_type"])

        zone_specs = [
            ("Left Block", 10),
            ("Right Block", 20),
            ("VIP Left", 30),
            ("VIP Right", 40),
            ("Fan Pit", 50),
        ]

        zones = {}
        for name, order in zone_specs:
            zone, _ = Zone.objects.get_or_create(
                hall=hall,
                name=name,
                defaults={"sort_order": order},
            )
            if zone.sort_order != order:
                zone.sort_order = order
                zone.save(update_fields=["sort_order"])
            zones[name] = zone

        sections = {}
        section_specs = [
            ("Left Block", "L-A", "A", 10),
            ("Left Block", "L-B", "B", 20),
            ("Left Block", "L-C", "C", 30),
            ("Right Block", "R-A", "A", 10),
            ("Right Block", "R-B", "B", 20),
            ("Right Block", "R-C", "C", 30),
            ("VIP Left", "VIP-L", "VL", 10),
            ("VIP Right", "VIP-R", "VR", 10),
            ("Fan Pit", "FAN", "F", 10),
        ]

        for zone_name, sec_name, row_prefix, order in section_specs:
            section, _ = Section.objects.get_or_create(
                zone=zones[zone_name],
                name=sec_name,
                defaults={"row_prefix": row_prefix, "sort_order": order},
            )
            updated = False
            if section.row_prefix != row_prefix:
                section.row_prefix = row_prefix
                updated = True
            if section.sort_order != order:
                section.sort_order = order
                updated = True
            if updated:
                section.save(update_fields=["row_prefix", "sort_order"])
            sections[sec_name] = section

        Seat.objects.filter(hall=hall).delete()

        self._upsert_section_grid(sections["L-A"], rows=7, cols=10, start_x=8, start_y=14, gap_x=2.2, gap_y=2.1)
        self._upsert_section_grid(sections["L-B"], rows=7, cols=10, start_x=8, start_y=30, gap_x=2.2, gap_y=2.1)
        self._upsert_section_grid(sections["L-C"], rows=6, cols=10, start_x=8, start_y=46, gap_x=2.2, gap_y=2.1)

        self._upsert_section_grid(sections["R-A"], rows=7, cols=10, start_x=66, start_y=14, gap_x=2.2, gap_y=2.1)
        self._upsert_section_grid(sections["R-B"], rows=7, cols=10, start_x=66, start_y=30, gap_x=2.2, gap_y=2.1)
        self._upsert_section_grid(sections["R-C"], rows=6, cols=10, start_x=66, start_y=46, gap_x=2.2, gap_y=2.1)

        self._upsert_section_rows(sections["VIP-L"], row_counts=[7, 6, 6, 5, 5], start_x=10, start_y=64, gap_x=2.1, gap_y=2.2)
        self._upsert_section_rows(sections["VIP-R"], row_counts=[7, 6, 6, 5, 5], start_x=73, start_y=64, gap_x=2.1, gap_y=2.2)

        reserved_event, _ = Event.objects.get_or_create(
            title="TeatrShahr - Hamlet",
            defaults={
                "description": "Reserved seating show",
                "starts_at": timezone.now() + timedelta(days=3),
                "venue": venue,
                "hall": hall,
                "sale_starts_at": timezone.now() - timedelta(days=1),
                "sale_ends_at": timezone.now() + timedelta(days=2),
                "is_reserved_seating": True,
            },
        )
        if reserved_event.venue_id != venue.id or reserved_event.hall_id != hall.id or not reserved_event.is_reserved_seating:
            reserved_event.venue = venue
            reserved_event.hall = hall
            reserved_event.is_reserved_seating = True
            reserved_event.save(update_fields=["venue", "hall", "is_reserved_seating"])

        all_hall_seats = list(Seat.objects.filter(hall=hall).select_related("section__zone"))

        created_event_seats = 0
        for seat in all_hall_seats:
            zone_name = seat.section.zone.name if seat.section_id else ""
            if "VIP" in zone_name:
                price = Decimal("22.00")
            elif "Fan Pit" in zone_name:
                price = Decimal("16.00")
            else:
                price = Decimal("12.00")

            _, created = EventSeat.objects.update_or_create(
                event=reserved_event,
                seat=seat,
                defaults={
                    "status": EventSeat.STATUS_AVAILABLE,
                    "price": price,
                },
            )
            if created:
                created_event_seats += 1

        ga_event, _ = Event.objects.get_or_create(
            title="TeatrShahr - Open Concert",
            defaults={
                "description": "General admission sample",
                "starts_at": timezone.now() + timedelta(days=10),
                "venue": venue,
                "hall": hall,
                "is_reserved_seating": False,
            },
        )
        TicketInventory.objects.update_or_create(
            event=ga_event,
            defaults={"total": 1200, "available": 1200},
        )

        self.stdout.write(self.style.SUCCESS("TeatrShahr sample data is ready."))
        self.stdout.write(self.style.SUCCESS(f"Reserved event id: {reserved_event.id}"))
        self.stdout.write(self.style.SUCCESS(f"General event id: {ga_event.id}"))
        self.stdout.write(self.style.SUCCESS(f"EventSeat rows created: {created_event_seats}"))

    def _upsert_section_grid(self, section, rows, cols, start_x, start_y, gap_x, gap_y):
        for r in range(rows):
            row_label = f"{section.row_prefix}{r + 1}"
            for c in range(cols):
                seat_no = str(c + 1)
                pos_x = Decimal(str(start_x + c * gap_x))
                pos_y = Decimal(str(start_y + r * gap_y))
                sort_order = (r + 1) * 100 + (c + 1)
                Seat.objects.update_or_create(
                    hall=section.zone.hall,
                    row_label=row_label,
                    seat_number=seat_no,
                    defaults={
                        "section": section,
                        "pos_x": pos_x,
                        "pos_y": pos_y,
                        "sort_order": sort_order,
                    },
                )

    def _upsert_section_rows(self, section, row_counts, start_x, start_y, gap_x, gap_y):
        for r, cols in enumerate(row_counts):
            row_label = f"{section.row_prefix}{r + 1}"
            for c in range(cols):
                seat_no = str(c + 1)
                pos_x = Decimal(str(start_x + c * gap_x))
                pos_y = Decimal(str(start_y + r * gap_y))
                sort_order = (r + 1) * 100 + (c + 1)
                Seat.objects.update_or_create(
                    hall=section.zone.hall,
                    row_label=row_label,
                    seat_number=seat_no,
                    defaults={
                        "section": section,
                        "pos_x": pos_x,
                        "pos_y": pos_y,
                        "sort_order": sort_order,
                    },
                )
