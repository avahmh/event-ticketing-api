from django.db import models


class Venue(models.Model):
    name = models.CharField(
        max_length=200,
        verbose_name="نام مکان",
        help_text="نام نمایشی برای مخاطب و لیست رویدادها (مثلاً تالار وحدت). این فیلد عنوان مکان است، نه آدرس کامل.",
    )
    address = models.TextField(
        blank=True,
        verbose_name="آدرس",
        help_text="آدرس پستی کامل یا توضیح مسیر. برای فیلتر «کجا» از شهر و محله استفاده کنید.",
    )
    timezone = models.CharField(
        max_length=50,
        default="Asia/Tehran",
        verbose_name="منطقهٔ زمانی",
    )
    city = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="شهر",
        help_text="مثلاً تهران؛ برای فیلتر مکان در سایت.",
    )
    area = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="محله / منطقه",
        help_text="مثلاً ونک یا منطقه ۳؛ اختیاری.",
    )
    description = models.TextField(blank=True, verbose_name="توضیحات")
    photo = models.ImageField(
        upload_to="venues/%Y/%m/",
        blank=True,
        null=True,
        verbose_name="تصویر مکان",
    )
    photo_url = models.URLField(blank=True, verbose_name="لینک تصویر مکان")
    latitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name="عرض جغرافیایی",
        help_text="مثلاً 35.699739 — از Google Maps یا OpenStreetMap کپی کنید.",
    )
    longitude = models.DecimalField(
        max_digits=9,
        decimal_places=6,
        null=True,
        blank=True,
        verbose_name="طول جغرافیایی",
        help_text="مثلاً 51.391472",
    )

    class Meta:
        verbose_name = "مکان برگزاری"
        verbose_name_plural = "مکان‌های برگزاری"

    def resolve_photo_url(self, request=None):
        if self.photo:
            url = self.photo.url
        elif self.photo_url:
            url = self.photo_url
        else:
            url = ""
        if request and url.startswith("/"):
            return request.build_absolute_uri(url)
        return url

    @property
    def has_map(self):
        return self.latitude is not None and self.longitude is not None

    def __str__(self):
        return self.name


class Organizer(models.Model):
    name = models.CharField(max_length=200, verbose_name="نام برگزارکننده")
    slug = models.SlugField(
        max_length=220,
        unique=True,
        blank=True,
        verbose_name="شناسه URL",
    )
    description = models.TextField(blank=True, verbose_name="توضیحات")
    logo = models.ImageField(
        upload_to="organizers/%Y/%m/",
        blank=True,
        null=True,
        verbose_name="لوگو / تصویر",
    )
    logo_url = models.URLField(blank=True, verbose_name="لینک لوگو")
    website = models.URLField(blank=True, verbose_name="وب‌سایت")
    phone = models.CharField(max_length=30, blank=True, verbose_name="تلفن")
    venues = models.ManyToManyField(
        Venue,
        blank=True,
        related_name="organizers",
        verbose_name="مکان‌های برگزاری",
    )
    halls = models.ManyToManyField(
        "Hall",
        blank=True,
        related_name="organizers",
        verbose_name="سالن‌ها",
    )
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "برگزارکننده"
        verbose_name_plural = "برگزارکننده‌ها"
        ordering = ["name"]

    def resolve_logo_url(self, request=None):
        if self.logo:
            url = self.logo.url
        elif self.logo_url:
            url = self.logo_url
        else:
            url = ""
        if request and url.startswith("/"):
            return request.build_absolute_uri(url)
        return url

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify

            base = slugify(self.name, allow_unicode=True) or "organizer"
            slug = base
            n = 1
            while Organizer.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                n += 1
                slug = f"{base}-{n}"
            self.slug = slug
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Hall(models.Model):
    CAPACITY_GENERAL = "general"
    CAPACITY_RESERVED = "reserved"
    CAPACITY_CHOICES = [
        (CAPACITY_GENERAL, "ورود آزاد"),
        (CAPACITY_RESERVED, "صندلی‌دار"),
    ]
    venue = models.ForeignKey(
        Venue,
        on_delete=models.CASCADE,
        related_name="halls",
        verbose_name="مکان",
    )
    name = models.CharField(
        max_length=200,
        verbose_name="نام سالن",
        help_text="نام سالن داخل همان مکان (مثلاً سالن اصلی، سالن شماره ۲).",
    )
    capacity_type = models.CharField(
        max_length=20,
        choices=CAPACITY_CHOICES,
        default=CAPACITY_RESERVED,
        verbose_name="نوع ظرفیت",
    )
    layout_json = models.JSONField(
        default=dict,
        blank=True,
        verbose_name="ویرایشگر نقشه (JSON)",
        help_text="نسخه ۲؛ ذخیره با فرم سالن و همگام با جدول صندلی‌ها.",
    )

    class Meta:
        verbose_name = "سالن"
        verbose_name_plural = "سالن‌ها"

    def __str__(self):
        return f"{self.venue.name} / {self.name}"


class Seat(models.Model):
    KIND_STANDARD = "standard"
    KIND_VIP = "vip"
    KIND_WHEELCHAIR = "wheelchair"
    KIND_BLOCKED = "blocked"
    KIND_CHOICES = [
        (KIND_STANDARD, "عادی"),
        (KIND_VIP, "VIP"),
        (KIND_WHEELCHAIR, "ویلچر"),
        (KIND_BLOCKED, "مسدود"),
    ]
    hall = models.ForeignKey(
        Hall,
        on_delete=models.CASCADE,
        related_name="seats",
        verbose_name="سالن",
    )
    row_label = models.CharField(max_length=20, verbose_name="ردیف")
    seat_number = models.CharField(max_length=20, verbose_name="شماره")
    grid_c = models.PositiveIntegerField(default=0, verbose_name="ستون شبکه")
    grid_r = models.PositiveIntegerField(default=0, verbose_name="ردیف شبکه")
    kind = models.CharField(
        max_length=20,
        choices=KIND_CHOICES,
        default=KIND_STANDARD,
        verbose_name="نوع صندلی",
    )
    sort_order = models.PositiveIntegerField(default=0, verbose_name="ترتیب")

    class Meta:
        ordering = ["sort_order", "grid_r", "grid_c", "row_label", "seat_number"]
        unique_together = [("hall", "row_label", "seat_number")]
        verbose_name = "صندلی"
        verbose_name_plural = "صندلی‌ها"

    def __str__(self):
        return f"{self.row_label}{self.seat_number}"
