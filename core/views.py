from django.shortcuts import render


def home(request):
    return render(request, "frontend/index.html")


def event_detail_page(request, event_id):
    return render(request, "frontend/event_detail.html", {"event_id": event_id})


def organizers_page(request):
    return render(request, "frontend/organizers.html")


def venues_page(request):
    return render(request, "frontend/venues.html")
