from django.db.models import Count, Q
from django.http import JsonResponse
from events.models import Event
from tickets.models import EventSeat


def list_events(request):
    events = Event.objects.select_related("inventory").all()
    reserved_ids = [e.id for e in events if e.is_reserved_seating]
    seat_stats = {}
    if reserved_ids:
        qs = (
            EventSeat.objects.filter(event_id__in=reserved_ids)
            .values("event_id")
            .annotate(
                total=Count("id"),
                available=Count("id", filter=Q(status=EventSeat.STATUS_AVAILABLE)),
            )
        )
        seat_stats = {row["event_id"]: row for row in qs}
    out = []
    for e in events:
        if e.is_reserved_seating:
            stats = seat_stats.get(e.id) or {"total": 0, "available": 0}
            item = {
                "id": e.id,
                "title": e.title,
                "starts_at": e.starts_at.isoformat() if e.starts_at else None,
                "available": stats["available"],
                "total": stats["total"],
                "is_reserved_seating": True,
            }
        else:
            inv = getattr(e, "inventory", None)
            item = {
                "id": e.id,
                "title": e.title,
                "starts_at": e.starts_at.isoformat() if e.starts_at else None,
                "available": inv.available if inv else 0,
                "total": inv.total if inv else 0,
                "is_reserved_seating": False,
            }
        out.append(item)
    return JsonResponse(out, safe=False)