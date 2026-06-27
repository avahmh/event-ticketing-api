from django.contrib import admin
from .models import TicketInventory, Order, EventRowPrice


class EventRowPriceInline(admin.TabularInline):
    model = EventRowPrice
    extra = 0
    fields = ("row_label", "price")


admin.site.register(TicketInventory)
admin.site.register(Order)
admin.site.register(EventRowPrice)
