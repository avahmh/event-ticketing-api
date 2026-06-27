from django.db.models import Min
from django.utils import timezone

from tickets.models import EventSeat
from tickets.session_stats import session_seat_stats


def _event_capacity(event):
    if event.is_reserved_seating:
        stats = session_seat_stats(event)
        return stats["available"], stats["total"]
    inv = getattr(event, "inventory", None)
    total = inv.total if inv else 0
    available = inv.available if inv else 0
    return available, total


def _min_price(event):
    agg = EventSeat.objects.filter(event=event, price__isnull=False).aggregate(
        m=Min("price")
    )
    if agg["m"] is not None:
        return float(agg["m"])
    return None


def _session_time_label(starts_at, now):
    if not starts_at:
        return ""
    local = timezone.localtime(starts_at)
    now_local = timezone.localtime(now)
    day_start = now_local.replace(hour=0, minute=0, second=0, microsecond=0)
    event_day = local.replace(hour=0, minute=0, second=0, microsecond=0)
    diff_days = (event_day - day_start).days
    time_str = local.strftime("%H:%M")
    if diff_days == 0:
        prefix = "امشب"
    elif diff_days == 1:
        prefix = "فردا"
    elif diff_days == 2:
        prefix = "پس‌فردا"
    else:
        prefix = local.strftime("%d/%m")
    return f"{prefix} {time_str}"


def nearest_session_payload(event, now=None):
    now = now or timezone.now()
    upcoming = (
        event.sessions.filter(starts_at__gte=now).order_by("starts_at").first()
    )
    if upcoming:
        sess = upcoming
        is_past = False
    else:
        sess = event.sessions.order_by("-starts_at").first()
        is_past = True if sess else False

    if sess:
        if event.is_reserved_seating:
            stats = session_seat_stats(event, sess.id)
            available = stats["available"]
            is_full = stats["is_full"]
        else:
            available, total = _event_capacity(event)
            is_full = available <= 0
        return {
            "id": sess.id,
            "starts_at": sess.starts_at.isoformat() if sess.starts_at else None,
            "available": available,
            "is_full": is_full,
            "is_past": is_past,
            "label": _session_time_label(sess.starts_at, now) if not is_past else "پایان یافته",
        }

    available, total = _event_capacity(event)
    is_past = bool(event.starts_at and event.starts_at < now)
    return {
        "id": None,
        "starts_at": event.starts_at.isoformat() if event.starts_at else None,
        "available": available,
        "is_full": available <= 0,
        "is_past": is_past,
        "label": _session_time_label(event.starts_at, now)
        if event.starts_at and not is_past
        else ("پایان یافته" if is_past else "به‌زودی"),
    }


def serialize_event_card(event, *, now=None, avg_rating=0, rating_count=0, request=None):
    now = now or timezone.now()
    available, total = _event_capacity(event)
    nearest = nearest_session_payload(event, now)
    min_price = _min_price(event)
    return {
        "id": event.id,
        "title": event.title,
        "description": (event.description or "")[:200],
        "starts_at": event.starts_at.isoformat() if event.starts_at else None,
        "available": available,
        "total": total,
        "sold": max(total - available, 0),
        "is_reserved_seating": event.is_reserved_seating,
        "event_type": event.event_type,
        "genre": event.genre or "",
        "poster_url": event.resolve_poster_url(request),
        "wallpaper_url": event.resolve_wallpaper_url(request),
        "is_featured": event.is_featured,
        "venue_name": event.venue.name if event.venue else "",
        "hall_name": event.hall.name if event.hall else "",
        "rating": float(avg_rating or 0),
        "rating_count": rating_count or 0,
        "organizer": event.organizer.name if event.organizer else "",
        "organizer_id": event.organizer_id,
        "organizer_logo_url": (
            event.organizer.resolve_logo_url(request) if event.organizer else ""
        ),
        "city": getattr(event.venue, "city", "") if event.venue else "",
        "area": getattr(event.venue, "area", "") if event.venue else "",
        "min_price": min_price,
        "nearest_session": nearest,
    }
