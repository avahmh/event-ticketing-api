from django.urls import path
from .views import purchase_ticket

urlpatterns = [
    path(
        "events/<int:event_id>/tickets/",
        purchase_ticket,
        name="purchase-ticket"
    ),
]
