from django.urls import path
from . import views

urlpatterns = [
    path("", views.list_events, name="list-events"),
    path("<int:event_id>/sessions/", views.event_sessions, name="event-sessions"),
    path("<int:event_id>/rate/", views.rate_event, name="event-rate"),
    path("<int:event_id>/comments/", views.event_comments, name="event-comments"),
]