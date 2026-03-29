from django.db import models


class Event(models.Model):
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    starts_at = models.DateTimeField()
    venue = models.ForeignKey(
        "venues.Venue", on_delete=models.SET_NULL, null=True, blank=True, related_name="events"
    )
    hall = models.ForeignKey(
        "venues.Hall", on_delete=models.SET_NULL, null=True, blank=True, related_name="events"
    )
    sale_starts_at = models.DateTimeField(null=True, blank=True)
    sale_ends_at = models.DateTimeField(null=True, blank=True)
    is_reserved_seating = models.BooleanField(default=False)

    def __str__(self):
        return self.title

