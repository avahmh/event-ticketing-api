from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from events.models import Event
from tickets.models import EventSeat, ReservationSeat, Reservation, OrderItem, Order
from .models import Seat, Organizer, Venue


def _venue_coords(venue):
    if not venue or not venue.has_map:
        return None, None
    return float(venue.latitude), float(venue.longitude)


def _serialize_organizer(org, request=None):
    return {
        "id": org.id,
        "name": org.name,
        "slug": org.slug,
        "description": org.description or "",
        "logo_url": org.resolve_logo_url(request),
        "website": org.website or "",
        "phone": org.phone or "",
        "venues": [
            {
                "id": v.id,
                "name": v.name,
                "city": v.city or "",
                "area": v.area or "",
                "photo_url": v.resolve_photo_url(request),
                "address": v.address or "",
                "latitude": _venue_coords(v)[0],
                "longitude": _venue_coords(v)[1],
            }
            for v in org.venues.all()
        ],
        "halls": [
            {
                "id": h.id,
                "name": h.name,
                "venue_id": h.venue_id,
                "venue_name": h.venue.name if h.venue_id else "",
            }
            for h in org.halls.select_related("venue")
        ],
    }


def _serialize_venue(venue, request=None):
    lat, lng = _venue_coords(venue)
    return {
        "id": venue.id,
        "name": venue.name,
        "city": venue.city or "",
        "area": venue.area or "",
        "address": venue.address or "",
        "description": venue.description or "",
        "photo_url": venue.resolve_photo_url(request),
        "latitude": lat,
        "longitude": lng,
        "halls": [
            {"id": h.id, "name": h.name, "capacity_type": h.capacity_type}
            for h in venue.halls.all()
        ],
        "organizers": [
            {
                "id": o.id,
                "name": o.name,
                "logo_url": o.resolve_logo_url(request),
            }
            for o in venue.organizers.filter(is_active=True)
        ],
    }


def list_organizers(request):
    orgs = (
        Organizer.objects.filter(is_active=True)
        .prefetch_related("venues", "halls__venue")
        .order_by("name")
    )
    return JsonResponse(
        [_serialize_organizer(o, request) for o in orgs],
        safe=False,
    )


def list_venues(request):
    venues = (
        Venue.objects.prefetch_related("halls", "organizers")
        .order_by("name")
    )
    return JsonResponse(
        [_serialize_venue(v, request) for v in venues],
        safe=False,
    )


def _seat_status_for_session(seat_id, event_seats, sold_ids, reserved_ids, seat_kind, session_id):
    if seat_kind == Seat.KIND_BLOCKED:
        return "blocked"
    if seat_id in sold_ids:
        return "sold"
    if seat_id in reserved_ids:
        return "reserved"
    if session_id:
        if seat_id in event_seats:
            return "available"
        return "blocked"
    es = event_seats.get(seat_id)
    if es and es.status == EventSeat.STATUS_AVAILABLE:
        return "available"
    if es and es.status == EventSeat.STATUS_RESERVED:
        return "reserved"
    return "sold"


def event_seatmap(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    if not event.is_reserved_seating or not event.hall_id:
        return JsonResponse(
            {"error": "Event does not have reserved seating"},
            status=400,
        )
    event_seats = {
        es.seat_id: es
        for es in EventSeat.objects.filter(event=event).select_related("seat")
    }
    session_id = request.GET.get("session_id")
    sold_ids = set()
    reserved_ids = set()
    if session_id:
        now = timezone.now()
        sold_ids = set(
            OrderItem.objects.filter(
                order__event=event,
                order__session_id=session_id,
                order__status=Order.STATUS_CONFIRMED,
            ).values_list("seat_id", flat=True)
        )
        reserved_ids = set(
            ReservationSeat.objects.filter(
                reservation__event=event,
                reservation__session_id=session_id,
                reservation__status=Reservation.STATUS_ACTIVE,
                reservation__reserved_until__gt=now,
            ).values_list("seat_id", flat=True)
        )
    hall = event.hall
    seats_data = []
    prices = []
    for seat in hall.seats.all().order_by("sort_order", "grid_r", "grid_c", "id"):
        es = event_seats.get(seat.id)
        st = _seat_status_for_session(
            seat.id,
            event_seats,
            sold_ids,
            reserved_ids,
            seat.kind,
            session_id,
        )
        price = float(es.price) if es and es.price is not None else None
        if price is not None and st != "blocked":
            prices.append(price)
        seats_data.append(
            {
                "id": seat.id,
                "row": seat.row_label,
                "number": seat.seat_number,
                "label": f"{seat.row_label}{seat.seat_number}",
                "status": st,
                "price": price,
                "grid_c": seat.grid_c,
                "grid_r": seat.grid_r,
                "kind": seat.kind,
            }
        )
    layout = hall.layout_json if isinstance(hall.layout_json, dict) else {}
    stage = layout.get("stage") or {"edge": "north", "label": "صحنه اجرا"}
    grid = layout.get("grid") or {}
    seat_cs = [seat.grid_c for seat in hall.seats.all()]
    seat_rs = [seat.grid_r for seat in hall.seats.all()]
    if seat_cs:
        min_c, max_c = min(seat_cs), max(seat_cs)
        min_r, max_r = min(seat_rs), max(seat_rs)
        grid_cols = int(grid.get("cols") or (max_c + 1))
        seat_width = max_c - min_c + 1
        start_col = max(0, (grid_cols - seat_width) // 2)
    else:
        min_c = max_c = min_r = max_r = start_col = 0
        grid_cols = int(grid.get("cols") or 1)
    aisle_cells = [
        {"c": c.get("c"), "r": c.get("r")}
        for c in (layout.get("cells") or [])
        if isinstance(c, dict) and c.get("t") in ("a", "st")
    ]
    stage_cells = [
        {"c": c.get("c"), "r": c.get("r")}
        for c in (layout.get("cells") or [])
        if isinstance(c, dict) and c.get("t") == "st"
    ]
    price_min = min(prices) if prices else 0
    price_max = max(prices) if prices else 0
    section = {"id": 0, "name": "نقشه", "row_prefix": "", "seats": seats_data}
    zone = {"id": 0, "name": hall.name, "sections": [section]}
    return JsonResponse(
        {
            "event_id": event.id,
            "hall": {"id": hall.id, "name": hall.name},
            "zones": [zone],
            "layout_meta": {
                "grid": grid,
                "stage": stage,
                "aisle_cells": aisle_cells,
                "stage_cells": stage_cells,
                "seat_bounds": {
                    "min_c": min_c,
                    "max_c": max_c,
                    "min_r": min_r,
                    "max_r": max_r,
                    "start_col": start_col,
                    "grid_cols": grid_cols,
                },
                "source": "seats_db",
            },
            "price_range": {"min": price_min, "max": price_max},
        }
    )
