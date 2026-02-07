from django.urls import path
from .views import purchase_ticket
from tickets.views import list_event_orders, get_order, cancel_order

urlpatterns = [
    path(
        "events/<int:event_id>/tickets/",
        purchase_ticket,
        name="purchase-ticket"
    ),
    path("events/<int:event_id>/orders/", list_event_orders, name="list-event-orders"),
    path("orders/<int:order_id>/", get_order, name="get-order"),
    path("orders/<int:order_id>/cancel/", cancel_order, name="cancel-order"),

]
