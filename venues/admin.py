import json

from django.contrib import admin, messages
from django.db.models import Count
from django import forms
from django.utils.html import format_html
from .models import Venue, Hall, Seat, Organizer
from .services import build_layout_v2_from_seats, sync_hall_layout_to_seats
from .widgets import SeatmapLayoutWidget


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ("name", "city", "area", "has_map_display", "hall_count", "organizer_count", "timezone")
    search_fields = ("name", "city", "area", "address")
    readonly_fields = ("linked_organizers", "map_preview")
    fieldsets = (
        (
            "مکان",
            {
                "fields": ("name", "city", "area", "description"),
                "description": "یک مکان می‌تواند چند سالن و چند برگزارکننده داشته باشد.",
            },
        ),
        (
            "تصویر",
            {"fields": ("photo", "photo_url")},
        ),
        (
            "موقعیت روی نقشه",
            {
                "fields": ("address", "latitude", "longitude", "map_preview"),
                "description": (
                    "آدرس را بنویسید و مختصات را از نقشه کپی کنید "
                    "(در Google Maps روی مکان راست‌کلیک → مختصات). "
                    "با ذخیره، نقشه در صفحه مکان و خرید بلیت نمایش داده می‌شود."
                ),
            },
        ),
        (
            "جزئیات",
            {"fields": ("timezone", "linked_organizers")},
        ),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(_hc=Count("halls", distinct=True), _oc=Count("organizers", distinct=True))
        )

    @admin.display(description="تعداد سالن")
    def hall_count(self, obj):
        return getattr(obj, "_hc", obj.halls.count())

    @admin.display(description="برگزارکننده")
    def organizer_count(self, obj):
        return getattr(obj, "_oc", obj.organizers.count())

    @admin.display(description="برگزارکننده‌های مرتبط")
    def linked_organizers(self, obj):
        names = list(obj.organizers.values_list("name", flat=True)[:20])
        if not names:
            return "— (از منوی برگزارکننده‌ها به این مکان وصل کنید)"
        return "، ".join(names)

    @admin.display(description="نقشه", boolean=True)
    def has_map_display(self, obj):
        return obj.has_map

    @admin.display(description="پیش‌نمایش نقشه")
    def map_preview(self, obj):
        if not obj.has_map:
            return "عرض و طول جغرافیایی را وارد و ذخیره کنید."
        url = (
            f"https://www.openstreetmap.org/?mlat={obj.latitude}&mlon={obj.longitude}"
            f"#map=16/{obj.latitude}/{obj.longitude}"
        )
        return format_html(
            '<a href="{}" target="_blank" rel="noopener">مشاهده موقعیت در نقشه</a>',
            url,
        )


@admin.register(Organizer)
class OrganizerAdmin(admin.ModelAdmin):
    list_display = ("name", "logo_thumb", "is_active", "venue_count", "hall_count", "phone")
    list_filter = ("is_active",)
    search_fields = ("name", "description", "phone")
    prepopulated_fields = {"slug": ("name",)}
    filter_horizontal = ("venues", "halls")
    readonly_fields = ("logo_preview",)
    fieldsets = (
        (
            "برگزارکننده",
            {
                "fields": (
                    "name",
                    "slug",
                    "description",
                    "is_active",
                    "phone",
                    "website",
                )
            },
        ),
        (
            "تصویر",
            {"fields": ("logo", "logo_url", "logo_preview")},
        ),
        (
            "مکان و سالن",
            {
                "fields": ("venues", "halls"),
                "description": "مکان‌های برگزاری و سالن‌هایی که این برگزارکننده در آن‌ها اجرا دارد.",
            },
        ),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .annotate(_vc=Count("venues", distinct=True), _hc=Count("halls", distinct=True))
        )

    @admin.display(description="لوگو")
    def logo_thumb(self, obj):
        url = obj.resolve_logo_url()
        if not url:
            return "—"
        return format_html(
            '<img src="{}" alt="" style="max-height:36px;border-radius:4px" />',
            url,
        )

    @admin.display(description="پیش‌نمایش لوگو")
    def logo_preview(self, obj):
        url = obj.resolve_logo_url()
        if not url:
            return "لوگو ثبت نشده."
        return format_html(
            '<img src="{}" alt="" style="max-width:160px;max-height:160px;border-radius:8px" />',
            url,
        )

    @admin.display(description="مکان")
    def venue_count(self, obj):
        return getattr(obj, "_vc", obj.venues.count())

    @admin.display(description="سالن")
    def hall_count(self, obj):
        return getattr(obj, "_hc", obj.halls.count())


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = (
        "row_label",
        "seat_number",
        "hall",
        "grid_c",
        "grid_r",
        "kind",
    )
    list_filter = ("hall", "kind")
    search_fields = ("row_label", "seat_number")
    fields = (
        "hall",
        "row_label",
        "seat_number",
        "grid_c",
        "grid_r",
        "kind",
        "sort_order",
    )
    readonly_fields = fields

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return True


class HallAdminForm(forms.ModelForm):
    class Meta:
        model = Hall
        fields = "__all__"
        widgets = {
            "layout_json": SeatmapLayoutWidget(),
        }


@admin.register(Hall)
class HallAdmin(admin.ModelAdmin):
    form = HallAdminForm
    change_form_template = "admin/venues/hall_change_form.html"
    save_on_top = True
    list_display = ("name", "venue", "capacity_type", "seat_count")
    list_filter = ("capacity_type", "venue")
    search_fields = ("name", "venue__name")
    autocomplete_fields = ("venue",)
    fieldsets = (
        (
            "سالن",
            {
                "fields": ("venue", "name", "capacity_type"),
                "description": "سالن جدید = نقشه جدید. بعد از پر کردن این بخش، پایین صفحه شبکه را بکشید و یک بار ذخیره کنید.",
            },
        ),
        (
            "نقشه صندلی (شبکه عمومی)",
            {
                "fields": ("layout_json",),
                "description": (
                    "هر سالن نقشهٔ خودش را دارد. اندازهٔ شبکه را تنظیم کنید، با قلم‌مو صندلی/راهرو/صحنه بکشید، "
                    "سپس «برچسب صندلی‌ها» را برای شماره‌گذاری ردیف‌ها بزنید و «ذخیره» کنید. "
                    "خروجی همین نقشه در صفحهٔ خرید بلیت (انتخاب صندلی با صحنه و راهرو) نمایش داده می‌شود."
                ),
            },
        ),
    )

    class Media:
        css = {"all": ("admin/venues/seatmap_editor.css",)}
        js = ("admin/venues/seatmap_editor.js",)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_sc=Count("seats"))

    @admin.display(description="تعداد صندلی")
    def seat_count(self, obj):
        return getattr(obj, "_sc", obj.seats.count())

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        sync_hall_layout_to_seats(obj)
        n = obj.seats.count()
        from events.models import Event
        from tickets.services import sync_event_seats

        synced = 0
        for event in Event.objects.filter(hall=obj, is_reserved_seating=True):
            result = sync_event_seats(event)
            synced += result["created"] + result["updated"]
        self.message_user(
            request,
            f"نقشه با دیتابیس همگام شد. این سالن اکنون {n} صندلی دارد."
            + (f" ({synced} ردیف صندلی رویداد به‌روز شد.)" if synced else ""),
            messages.SUCCESS,
        )

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        if object_id:
            from django.contrib.admin.utils import unquote

            obj = self.get_object(request, unquote(object_id))
            if obj is not None:
                lj = obj.layout_json or {}
                if (
                    lj.get("version") != 2
                    or not lj.get("cells")
                ) and obj.seats.exists():
                    extra_context["bootstrap_layout_json"] = json.dumps(
                        build_layout_v2_from_seats(obj),
                        ensure_ascii=False,
                    )
        return super().changeform_view(
            request, object_id, form_url, extra_context=extra_context
        )
