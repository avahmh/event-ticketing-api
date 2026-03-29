from django.db import models


class Venue(models.Model):
    name = models.CharField(max_length=200)
    address = models.TextField(blank=True)
    timezone = models.CharField(max_length=50, default="UTC")

    def __str__(self):
        return self.name


class Hall(models.Model):
    CAPACITY_GENERAL = "general"
    CAPACITY_RESERVED = "reserved"
    CAPACITY_CHOICES = [
        (CAPACITY_GENERAL, "General admission"),
        (CAPACITY_RESERVED, "Reserved seating"),
    ]
    venue = models.ForeignKey(Venue, on_delete=models.CASCADE, related_name="halls")
    name = models.CharField(max_length=200)
    capacity_type = models.CharField(
        max_length=20, choices=CAPACITY_CHOICES, default=CAPACITY_RESERVED
    )

    def __str__(self):
        return f"{self.venue.name} / {self.name}"


class Zone(models.Model):
    hall = models.ForeignKey(Hall, on_delete=models.CASCADE, related_name="zones")
    name = models.CharField(max_length=100)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]
        unique_together = [("hall", "name")]

    def __str__(self):
        return f"{self.hall.name} / {self.name}"


class Section(models.Model):
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name="sections")
    name = models.CharField(max_length=100)
    row_prefix = models.CharField(max_length=20, blank=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]
        unique_together = [("zone", "name")]

    def __str__(self):
        return f"{self.zone.name} / {self.name}"


class Seat(models.Model):
    section = models.ForeignKey(
        Section, on_delete=models.CASCADE, related_name="seats", null=True, blank=True
    )
    hall = models.ForeignKey(
        Hall, on_delete=models.CASCADE, related_name="seats", null=True, blank=True
    )
    row_label = models.CharField(max_length=20)
    seat_number = models.CharField(max_length=20)
    pos_x = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True, help_text="X for seat map"
    )
    pos_y = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True, help_text="Y for seat map"
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "row_label", "seat_number"]
        unique_together = [("hall", "row_label", "seat_number")]

    def save(self, *args, **kwargs):
        if self.section_id:
            self.hall_id = self.section.zone.hall_id
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.row_label}{self.seat_number}"
