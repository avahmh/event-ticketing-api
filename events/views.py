from django.http import JsonResponse
from tickets.models import Order
from events.models import Event


def list_events(request):
    events = Event.objects.all().values("id", "title", "starts_at")
    return JsonResponse(list(events), safe=False)