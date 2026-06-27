from django.db import models


class Event(models.Model):
    TYPE_CINEMA = "cinema"
    TYPE_THEATER = "theater"
    TYPE_CONCERT = "concert"
    TYPE_CHOICES = [
        (TYPE_CINEMA, "سینما"),
        (TYPE_THEATER, "تئاتر"),
        (TYPE_CONCERT, "کنسرت"),
    ]

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
    is_reserved_seating = models.BooleanField(default=False, verbose_name="صندلی‌دار")
    event_type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=TYPE_THEATER,
        verbose_name="نوع",
    )
    genre = models.CharField(max_length=100, blank=True, verbose_name="ژانر")
    poster = models.ImageField(
        upload_to="event_posters/%Y/%m/",
        blank=True,
        null=True,
        verbose_name="پوستر",
        help_text="تصویر پوستر را از رایانه آپلود کنید.",
    )
    poster_url = models.URLField(
        blank=True,
        verbose_name="لینک پوستر",
        help_text="اگر فایل آپلود نکردید، می‌توانید لینک مستقیم تصویر بگذارید.",
    )
    wallpaper = models.ImageField(
        upload_to="event_wallpapers/%Y/%m/",
        blank=True,
        null=True,
        verbose_name="بنر / والپیپر",
        help_text="تصویر عریض افقی برای اسلایدر و بالای صفحه رویداد (مثل بنر تیوال).",
    )
    wallpaper_url = models.URLField(
        blank=True,
        verbose_name="لینک بنر",
        help_text="لینک تصویر عریض افقی (اختیاری).",
    )
    is_featured = models.BooleanField(
        default=False,
        verbose_name="پیشنهاد ویژه",
        help_text="در اسلایدر بالای صفحهٔ اول نمایش داده می‌شود.",
    )
    organizer = models.ForeignKey(
        "venues.Organizer",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="events",
        verbose_name="برگزارکننده",
    )
    purchase_notes = models.TextField(
        blank=True,
        verbose_name="نکات خرید",
        help_text="هر خط یک نکته در صفحهٔ خرید نمایش داده می‌شود.",
    )

    class Meta:
        verbose_name = "رویداد"
        verbose_name_plural = "رویدادها"

    DEFAULT_POSTER_PATHS = {
        TYPE_CINEMA: "/static/frontend/posters/cinema.svg",
        TYPE_THEATER: "/static/frontend/posters/theater.svg",
        TYPE_CONCERT: "/static/frontend/posters/concert.svg",
    }

    DEFAULT_WALLPAPER_PATHS = {
        TYPE_CINEMA: "/static/frontend/wallpapers/cinema.svg",
        TYPE_THEATER: "/static/frontend/wallpapers/theater.svg",
        TYPE_CONCERT: "/static/frontend/wallpapers/concert.svg",
    }

    def resolve_poster_url(self, request=None):
        if self.poster:
            url = self.poster.url
        elif self.poster_url:
            url = self.poster_url
        else:
            url = self.DEFAULT_POSTER_PATHS.get(self.event_type, "")
        if request and url.startswith("/"):
            return request.build_absolute_uri(url)
        return url

    def resolve_wallpaper_url(self, request=None):
        if self.wallpaper:
            url = self.wallpaper.url
        elif self.wallpaper_url:
            url = self.wallpaper_url
        else:
            url = self.DEFAULT_WALLPAPER_PATHS.get(self.event_type, "")
        if request and url.startswith("/"):
            return request.build_absolute_uri(url)
        return url

    def __str__(self):
        return self.title


class EventSession(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="sessions")
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True)
    title = models.CharField(max_length=200, blank=True)
    standing_total = models.PositiveIntegerField(
        default=0,
        verbose_name="ظرفیت ایستاده",
        help_text="بلیت بیرون از ظرفیت (صفر = غیرفعال).",
    )
    standing_available = models.PositiveIntegerField(
        default=0,
        verbose_name="مانده ایستاده",
    )

    class Meta:
        ordering = ["starts_at", "id"]
        verbose_name = "سانس"
        verbose_name_plural = "سانس‌ها"

    def __str__(self):
        return self.title or f"{self.event.title} @ {self.starts_at}"


class EventRating(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="ratings")
    score = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    user_key = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "امتیاز رویداد"
        verbose_name_plural = "امتیازهای رویداد"


class EventComment(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="comments")
    author_name = models.CharField(max_length=80, verbose_name="نام", blank=True)
    author_email = models.EmailField(blank=True, verbose_name="ایمیل")
    body = models.TextField(verbose_name="متن نظر")
    created_at = models.DateTimeField(auto_now_add=True)
    user_key = models.CharField(max_length=100, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "نظر"
        verbose_name_plural = "نظرات"

    def __str__(self):
        label = self.author_name or "مهمان"
        return f"{label}: {self.body[:40]}"
