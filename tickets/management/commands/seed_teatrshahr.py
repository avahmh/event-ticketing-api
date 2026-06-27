from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.utils import timezone

from events.models import Event, EventSession
from tickets.models import EventSeat, TicketInventory
from venues.models import Hall, Seat, Venue, Organizer

class Command(BaseCommand):
    help = "Seed TeatrShahr sample venue, hall, grid seats, sessions, and events"

    def _seed_theater_layout(self, hall):
        Seat.objects.filter(hall=hall).delete()
        cells = []
        sort = 0

        def add_seat(gc, gr, row_label, seat_no, kind=Seat.KIND_STANDARD):
            nonlocal sort
            sort += 1
            seat = Seat.objects.create(
                hall=hall,
                row_label=str(row_label),
                seat_number=str(seat_no),
                grid_c=gc,
                grid_r=gr,
                kind=kind,
                sort_order=gr * 1000 + gc,
            )
            cells.append(
                {
                    "c": gc,
                    "r": gr,
                    "t": "s",
                    "seat_id": seat.id,
                    "kind": kind,
                    "row_label": str(row_label),
                    "seat_number": str(seat_no),
                }
            )
            return seat

        def add_aisle(gc, gr):
            cells.append({"c": gc, "r": gr, "t": "a"})

        left_nums = list(range(15, 22))
        mid_nums = list(range(5, 17))
        right_nums = list(range(1, 7))

        for row in range(11):
            gr = row
            rl = str(row + 1)
            if row < 9:
                for i, sn in enumerate(left_nums):
                    add_seat(i, gr, rl, sn)
                add_aisle(7, gr)
                for i, sn in enumerate(mid_nums):
                    add_seat(8 + i, gr, rl, sn)
                add_aisle(21, gr)
                for i, sn in enumerate(right_nums):
                    add_seat(22 + i, gr, rl, sn)
            else:
                for i, sn in enumerate(right_nums):
                    add_seat(22 + i, gr, rl, sn)

        hall.layout_json = {
            "version": 2,
            "grid": {"cols": 30, "rows": 14},
            "stage": {"edge": "north", "label": "صحنه اجرا"},
            "cells": cells,
        }
        hall.save(update_fields=["layout_json"])

    def handle(self, *args, **options):
        venue, _ = Venue.objects.get_or_create(
            name="تالار وحدت",
            defaults={
                "address": "تهران، پارک دانشجو",
                "city": "تهران",
                "area": "منطقه ۶",
                "timezone": "Asia/Tehran",
                "latitude": "35.699739",
                "longitude": "51.391472",
            },
        )
        venue.address = "تهران، پارک دانشجو"
        venue.city = "تهران"
        venue.area = "منطقه ۶"
        venue.latitude = "35.699739"
        venue.longitude = "51.391472"
        venue.save(update_fields=["address", "city", "area", "latitude", "longitude"])

        hall, _ = Hall.objects.get_or_create(
            venue=venue,
            name="سالن اصلی",
            defaults={"capacity_type": Hall.CAPACITY_RESERVED},
        )
        if hall.capacity_type != Hall.CAPACITY_RESERVED:
            hall.capacity_type = Hall.CAPACITY_RESERVED
            hall.save(update_fields=["capacity_type"])

        self._seed_theater_layout(hall)

        organizer, _ = Organizer.objects.get_or_create(
            name="سینما کده",
            defaults={
                "description": "سامانه فروش بلیت سینما، تئاتر و کنسرت",
                "is_active": True,
            },
        )
        organizer.venues.add(venue)
        organizer.halls.add(hall)

        base_start = timezone.now().replace(hour=19, minute=0, second=0, microsecond=0)
        if base_start < timezone.now():
            base_start += timedelta(days=1)

        def seed_sessions(event, offsets):
            EventSession.objects.filter(event=event).delete()
            for day_offset, sh, sm, eh, em, standing in offsets:
                start = base_start + timedelta(days=day_offset, hours=sh - 19, minutes=sm)
                end = base_start + timedelta(days=day_offset, hours=eh - 19, minutes=em)
                EventSession.objects.create(
                    event=event,
                    starts_at=start,
                    ends_at=end,
                    standing_total=standing,
                    standing_available=standing,
                )

        session_offsets = [
            (0, 19, 0, 20, 0, 20),
            (0, 22, 0, 23, 0, 23),
            (1, 19, 0, 20, 0, 0),
            (1, 22, 0, 23, 0, 15),
        ]

        reserved_event, _ = Event.objects.get_or_create(
            title="کنسرت — کینگ رام",
            defaults={
                "description": "اجرای زنده با صندلی‌دار",
                "starts_at": base_start,
                "venue": venue,
                "hall": hall,
                "sale_starts_at": timezone.now() - timedelta(days=1),
                "sale_ends_at": base_start + timedelta(days=7),
                "is_reserved_seating": True,
                "organizer": organizer,
                "purchase_notes": (
                    "در هنگام خرید دقت کنید؛ بلیت قابل استرداد نیست.\n"
                    "ترافیک اطراف سالن در ساعات اجرا سنگین است؛ زودتر حرکت کنید.\n"
                    "پارکینگ محدود است؛ از حمل‌ونقل عمومی استفاده کنید."
                ),
            },
        )
        reserved_event.venue = venue
        reserved_event.hall = hall
        reserved_event.is_reserved_seating = True
        reserved_event.event_type = Event.TYPE_CONCERT
        reserved_event.genre = "موسیقی"
        reserved_event.is_featured = True
        reserved_event.organizer = organizer
        reserved_event.purchase_notes = (
            "در هنگام خرید دقت کنید؛ بلیت قابل استرداد نیست.\n"
            "ترافیک اطراف سالن در ساعات اجرا سنگین است؛ زودتر حرکت کنید.\n"
            "پارکینگ محدود است؛ از حمل‌ونقل عمومی استفاده کنید."
        )
        reserved_event.save()

        seed_sessions(reserved_event, session_offsets)

        theater_event, _ = Event.objects.get_or_create(
            title="نمایش — شازده کوچولو",
            defaults={
                "description": "نمایش خانوادگی بر اساس اثر سنت‌اگزوپری",
                "starts_at": base_start,
                "venue": venue,
                "hall": hall,
                "sale_starts_at": timezone.now() - timedelta(days=1),
                "sale_ends_at": base_start + timedelta(days=14),
                "is_reserved_seating": True,
                "organizer": organizer,
                "event_type": Event.TYPE_THEATER,
                "genre": "خانوادگی",
                "is_featured": True,
            },
        )
        theater_event.venue = venue
        theater_event.hall = hall
        theater_event.is_reserved_seating = True
        theater_event.event_type = Event.TYPE_THEATER
        theater_event.genre = "خانوادگی"
        theater_event.is_featured = True
        theater_event.organizer = organizer
        theater_event.save()
        seed_sessions(theater_event, session_offsets)

        cinema_event, _ = Event.objects.get_or_create(
            title="فیلم — شهر فراموشی",
            defaults={
                "description": "اکران ویژه در سالن اصلی",
                "starts_at": base_start + timedelta(hours=2),
                "venue": venue,
                "hall": hall,
                "sale_starts_at": timezone.now() - timedelta(days=1),
                "sale_ends_at": base_start + timedelta(days=10),
                "is_reserved_seating": True,
                "organizer": organizer,
                "event_type": Event.TYPE_CINEMA,
                "genre": "درام",
                "is_featured": False,
            },
        )
        cinema_event.venue = venue
        cinema_event.hall = hall
        cinema_event.is_reserved_seating = True
        cinema_event.event_type = Event.TYPE_CINEMA
        cinema_event.genre = "درام"
        cinema_event.organizer = organizer
        cinema_event.save()
        seed_sessions(
            cinema_event,
            [
                (0, 17, 30, 19, 30, 0),
                (0, 20, 0, 22, 0, 0),
                (1, 17, 30, 19, 30, 0),
                (2, 20, 0, 22, 0, 0),
            ],
        )

        created_event_seats = 0
        for event in (reserved_event, theater_event, cinema_event):
            for seat in Seat.objects.filter(hall=hall):
                sn = int(seat.seat_number) if seat.seat_number.isdigit() else 10
                if sn <= 6:
                    price = Decimal("1400000")
                elif sn <= 10:
                    price = Decimal("1300000")
                else:
                    price = Decimal("1200000")
                _, created = EventSeat.objects.update_or_create(
                    event=event,
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
        self.stdout.write(self.style.SUCCESS(f"Concert event id: {reserved_event.id}"))
        self.stdout.write(self.style.SUCCESS(f"Theater event id: {theater_event.id}"))
        self.stdout.write(self.style.SUCCESS(f"Cinema event id: {cinema_event.id}"))
        self.stdout.write(self.style.SUCCESS(f"General event id: {ga_event.id}"))
        self.stdout.write(
            self.style.SUCCESS(f"EventSeat rows created: {created_event_seats}")
        )
        self.stdout.write(
            self.style.SUCCESS(f"Hall seats: {hall.seats.count()}")
        )
