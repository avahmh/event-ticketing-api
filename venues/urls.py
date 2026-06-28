from django.urls import path
from . import views

urlpatterns = [
    path("api/organizers/", views.list_organizers, name="list-organizers"),
    path("api/venues/", views.list_venues, name="list-venues"),
    path("events/<int:event_id>/seatmap/", views.event_seatmap, name="event-seatmap"),
]
