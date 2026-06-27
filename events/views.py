from django.db.models import Avg, Count, Prefetch
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
import json

from events.models import Event, EventSession, EventRating, EventComment
from events.listing import serialize_event_card
from tickets.session_stats import session_seat_stats


def _event_capacity(event):
    if event.is_reserved_seating:
        stats = session_seat_stats(event)
        return stats["available"], stats["total"]
    inv = getattr(event, "inventory", None)
    total = inv.total if inv else 0
    available = inv.available if inv else 0
    return available, total


def list_events(request):
    now = timezone.now()
    events = (
        Event.objects.select_related("inventory", "venue", "hall", "organizer")
        .prefetch_related(
            Prefetch(
                "sessions",
                queryset=EventSession.objects.order_by("starts_at"),
            )
        )
        .annotate(
            avg_rating=Avg("ratings__score"),
            rating_count=Count("ratings"),
        )
        .all()
    )
    out = [
        serialize_event_card(
            e,
            now=now,
            avg_rating=e.avg_rating,
            rating_count=e.rating_count,
            request=request,
        )
        for e in events
    ]
    return JsonResponse(out, safe=False)


def event_sessions(request, event_id):
    event = (
        Event.objects.select_related("inventory", "venue", "hall", "organizer")
        .annotate(
            avg_rating=Avg("ratings__score"),
            rating_count=Count("ratings"),
        )
        .filter(id=event_id)
        .first()
    )
    if not event:
        return JsonResponse({"error": "Event not found"}, status=404)

    available, total = _event_capacity(event)
    sessions_qs = EventSession.objects.filter(event_id=event_id).order_by("starts_at")
    sessions = []
    for s in sessions_qs:
        stats = session_seat_stats(event, s.id)
        sessions.append(
            {
                "id": s.id,
                "title": s.title,
                "starts_at": s.starts_at.isoformat() if s.starts_at else None,
                "ends_at": s.ends_at.isoformat() if s.ends_at else None,
                "available": stats["available"],
                "total": stats["total"],
                "is_full": stats["is_full"],
                "standing_total": s.standing_total,
                "standing_available": s.standing_available,
            }
        )

    notes = [
        line.strip()
        for line in (event.purchase_notes or "").splitlines()
        if line.strip()
    ]
    return JsonResponse(
        {
            "event": {
                "id": event.id,
                "title": event.title,
                "description": event.description or "",
                "is_reserved_seating": event.is_reserved_seating,
                "venue_name": event.venue.name if event.venue else "",
                "hall_name": event.hall.name if event.hall else "",
                "starts_at": event.starts_at.isoformat() if event.starts_at else None,
                "available": available,
                "total": total,
                "rating": float(event.avg_rating or 0),
                "rating_count": event.rating_count or 0,
                "organizer": event.organizer.name if event.organizer else "",
                "organizer_id": event.organizer_id,
                "organizer_logo_url": (
                    event.organizer.resolve_logo_url(request) if event.organizer else ""
                ),
                "city": getattr(event.venue, "city", "") if event.venue else "",
                "area": getattr(event.venue, "area", "") if event.venue else "",
                "venue_address": event.venue.address if event.venue else "",
                "venue_latitude": (
                    float(event.venue.latitude)
                    if event.venue and event.venue.latitude is not None
                    else None
                ),
                "venue_longitude": (
                    float(event.venue.longitude)
                    if event.venue and event.venue.longitude is not None
                    else None
                ),
                "purchase_notes": notes,
                "poster_url": event.resolve_poster_url(request),
                "wallpaper_url": event.resolve_wallpaper_url(request),
            },
            "sessions": sessions,
        }
    )


@csrf_exempt
@require_POST
def rate_event(request, event_id):
    try:
        body = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)
    score = body.get("score")
    try:
        score = int(score)
    except (TypeError, ValueError):
        return JsonResponse({"error": "score must be integer 1-5"}, status=400)
    if score < 1 or score > 5:
        return JsonResponse({"error": "score must be between 1 and 5"}, status=400)
    event = Event.objects.filter(id=event_id).first()
    if not event:
        return JsonResponse({"error": "Event not found"}, status=404)
    user_key = request.headers.get("X-User-Key", "")
    EventRating.objects.create(event=event, score=score, user_key=user_key or "")
    agg = event.ratings.aggregate(
        avg_rating=Avg("score"),
        rating_count=Count("id"),
    )
    return JsonResponse(
        {
            "event_id": event.id,
            "rating": float(agg["avg_rating"] or 0),
            "rating_count": agg["rating_count"] or 0,
        },
        status=201,
    )


def _serialize_comment(c):
    return {
        "id": c.id,
        "author_name": c.author_name or "مهمان",
        "author_email": c.author_email or "",
        "body": c.body,
        "created_at": c.created_at.isoformat() if c.created_at else None,
    }


@csrf_exempt
def event_comments(request, event_id):
    event = Event.objects.filter(id=event_id).first()
    if not event:
        return JsonResponse({"error": "Event not found"}, status=404)

    if request.method == "GET":
        comments = event.comments.all()[:100]
        return JsonResponse(
            {
                "event_id": event.id,
                "comments": [_serialize_comment(c) for c in comments],
            }
        )

    if request.method != "POST":
        return JsonResponse({"error": "Method not allowed"}, status=405)

    try:
        body = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    author_name = (body.get("author_name") or "").strip()
    author_email = (body.get("author_email") or "").strip()
    text = (body.get("body") or "").strip()
    if len(author_name) > 80:
        return JsonResponse({"error": "نام خیلی طولانی است"}, status=400)
    if author_email and len(author_email) > 120:
        return JsonResponse({"error": "ایمیل خیلی طولانی است"}, status=400)
    if not text:
        return JsonResponse({"error": "متن نظر الزامی است"}, status=400)
    if len(text) > 2000:
        return JsonResponse({"error": "متن نظر خیلی طولانی است"}, status=400)

    user_key = request.headers.get("X-User-Key", "")
    comment = EventComment.objects.create(
        event=event,
        author_name=author_name,
        author_email=author_email,
        body=text,
        user_key=user_key or "",
    )
    return JsonResponse(_serialize_comment(comment), status=201)
