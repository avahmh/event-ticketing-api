from django.urls import path
from .views import (
    purchase_ticket,
    list_event_orders,
    get_order,
    cancel_order,
    reserve_seats,
    confirm_reservation,
    fake_payment_page,
    pay_order,
)

urlpatterns = [
    path("events/<int:event_id>/tickets/", purchase_ticket, name="purchase-ticket"),
    path("events/<int:event_id>/orders/", list_event_orders, name="list-event-orders"),
    path("events/<int:event_id>/reservations/", reserve_seats, name="reserve-seats"),
    path("events/<int:event_id>/reservations/confirm/", confirm_reservation, name="confirm-reservation"),
    path("orders/<int:order_id>/", get_order, name="get-order"),
    path("orders/<int:order_id>/cancel/", cancel_order, name="cancel-order"),
    path("orders/<int:order_id>/pay/", pay_order, name="pay-order"),
    path("payments/fake/<int:order_id>/", fake_payment_page, name="fake-payment-page"),
]
