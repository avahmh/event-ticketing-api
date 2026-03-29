from django.urls import path
from . import views

urlpatterns = [
    path("events/<int:event_id>/seatmap/", views.event_seatmap, name="event-seatmap"),
]
