from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from events.models import Event
from tickets.models import EventSeat


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
    hall = event.hall
    zones = []
    for zone in hall.zones.prefetch_related("sections__seats").all():
        sections_data = []
        for section in zone.sections.all():
            seats_data = []
            for seat in section.seats.all():
                es = event_seats.get(seat.id)
                status = es.status if es else "available"
                price = float(es.price) if es and es.price else None
                seats_data.append({
                    "id": seat.id,
                    "row": seat.row_label,
                    "number": seat.seat_number,
                    "label": f"{seat.row_label}{seat.seat_number}",
                    "status": status,
                    "price": price,
                    "pos_x": float(seat.pos_x) if seat.pos_x else None,
                    "pos_y": float(seat.pos_y) if seat.pos_y else None,
                })
            sections_data.append({
                "id": section.id,
                "name": section.name,
                "row_prefix": section.row_prefix,
                "seats": seats_data,
            })
        zones.append({"id": zone.id, "name": zone.name, "sections": sections_data})
    return JsonResponse({
        "event_id": event.id,
        "hall": {"id": hall.id, "name": hall.name},
        "zones": zones,
    })
