from django.contrib import admin
from django.utils.html import format_html

from tickets.services import sync_event_seats

from .models import Event, EventSession, EventRating, EventComment


class EventSessionInline(admin.TabularInline):
    model = EventSession
    extra = 1
    verbose_name = "سانس"
    verbose_name_plural = "سانس‌ها"
    fields = (
        "title",
        "starts_at",
        "ends_at",
        "standing_total",
        "standing_available",
    )
    ordering = ("starts_at",)


class EventCommentInline(admin.TabularInline):
    model = EventComment
    extra = 0
    verbose_name = "نظر"
    verbose_name_plural = "نظرات"
    fields = ("author_name", "author_email", "body", "created_at", "user_key")
    readonly_fields = ("created_at",)
    ordering = ("-created_at",)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    change_form_template = "admin/events/event/change_form.html"
    list_display = (
        "title",
        "event_type",
        "starts_at",
        "venue",
        "is_featured",
        "poster_preview_thumb",
        "is_reserved_seating",
        "organizer",
    )
    list_filter = ("event_type", "is_reserved_seating", "is_featured", "venue", "organizer")
    search_fields = ("title", "organizer__name", "description", "genre")
    list_editable = ("is_featured",)
    readonly_fields = ("poster_preview", "wallpaper_preview")
    inlines = (EventSessionInline, EventCommentInline)
    autocomplete_fields = ("organizer", "venue", "hall")
    fieldsets = (
        (
            "تصاویر",
            {
                "classes": ("wide", "event-images-top"),
                "fields": (
                    ("poster", "poster_url"),
                    "poster_preview",
                    ("wallpaper", "wallpaper_url"),
                    "wallpaper_preview",
                ),
                "description": "پوستر عمودی برای کارت‌ها؛ بنر عریض برای اسلایدر و بالای صفحهٔ خرید.",
            },
        ),
        (
            "رویداد",
            {
                "fields": (
                    "title",
                    "description",
                    ("event_type", "genre"),
                    "is_featured",
                    "organizer",
                    ("starts_at", "sale_starts_at", "sale_ends_at"),
                )
            },
        ),
        ("مکان", {"fields": (("venue", "hall"), "is_reserved_seating")}),
        (
            "صفحه خرید",
            {
                "fields": ("purchase_notes",),
                "description": "هر خط یک نکته در صفحهٔ خرید نمایش داده می‌شود.",
            },
        ),
    )

    actions = ("sync_event_seats_action",)

    @admin.action(description="همگام‌سازی صندلی‌ها از نقشهٔ سالن")
    def sync_event_seats_action(self, request, queryset):
        total = 0
        for event in queryset:
            if not event.hall_id or not event.is_reserved_seating:
                continue
            result = sync_event_seats(event)
            total += result["created"]
        self.message_user(
            request,
            f"همگام‌سازی انجام شد. {total} صندلی جدید برای رویدادهای انتخاب‌شده ساخته شد.",
        )

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        obj = form.instance
        if obj.hall_id and obj.is_reserved_seating:
            sync_event_seats(obj)

    @admin.display(description="پوستر")
    def poster_preview_thumb(self, obj):
        url = obj.resolve_poster_url()
        if not url:
            return "—"
        return format_html(
            '<img src="{}" alt="" style="max-height:40px;border-radius:4px" />',
            url,
        )

    @admin.display(description="پیش‌نمایش پوستر")
    def poster_preview(self, obj):
        url = obj.resolve_poster_url()
        if not url:
            return "پوستری ثبت نشده — فایل آپلود کنید یا لینک بگذارید."
        return format_html(
            '<img src="{}" alt="" style="max-width:220px;max-height:320px;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,.15)" />',
            url,
        )

    @admin.display(description="پیش‌نمایش بنر")
    def wallpaper_preview(self, obj):
        url = obj.resolve_wallpaper_url()
        if not url:
            return "بنری ثبت نشده — فایل عریض آپلود کنید یا لینک بگذارید."
        return format_html(
            '<img src="{}" alt="" style="max-width:420px;max-height:120px;border-radius:8px;box-shadow:0 4px 12px rgba(0,0,0,.15)" />',
            url,
        )


@admin.register(EventSession)
class EventSessionAdmin(admin.ModelAdmin):
    list_display = (
        "event",
        "title",
        "starts_at",
        "ends_at",
        "standing_total",
        "standing_available",
    )
    list_filter = ("event",)
    search_fields = ("title", "event__title")
    ordering = ("-starts_at",)
    autocomplete_fields = ("event",)


@admin.register(EventRating)
class EventRatingAdmin(admin.ModelAdmin):
    list_display = ("event", "score", "created_at", "user_key")
    list_filter = ("event",)


@admin.register(EventComment)
class EventCommentAdmin(admin.ModelAdmin):
    list_display = ("event", "author_name", "body_preview", "created_at")
    list_filter = ("event",)
    search_fields = ("author_name", "body", "event__title")
    ordering = ("-created_at",)

    @admin.display(description="متن")
    def body_preview(self, obj):
        return obj.body[:60] + ("…" if len(obj.body) > 60 else "")
