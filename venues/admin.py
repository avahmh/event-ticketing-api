from django.contrib import admin
from .models import Venue, Hall, Zone, Section, Seat


@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    list_display = ("name", "timezone")


@admin.register(Hall)
class HallAdmin(admin.ModelAdmin):
    list_display = ("name", "venue", "capacity_type")
    list_filter = ("capacity_type",)


class SeatInline(admin.TabularInline):
    model = Seat
    extra = 0
    fk_name = "section"


@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ("name", "hall", "sort_order")
    list_filter = ("hall",)


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ("name", "zone", "row_prefix", "sort_order")
    list_filter = ("zone",)
    inlines = [SeatInline]


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ("row_label", "seat_number", "section", "hall", "pos_x", "pos_y")
    list_filter = ("hall",)
