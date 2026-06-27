from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("venues", "0006_alter_seat_options_alter_hall_layout_json_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="venue",
            name="description",
            field=models.TextField(blank=True, verbose_name="توضیحات"),
        ),
        migrations.AddField(
            model_name="venue",
            name="photo",
            field=models.ImageField(
                blank=True,
                null=True,
                upload_to="venues/%Y/%m/",
                verbose_name="تصویر مکان",
            ),
        ),
        migrations.AddField(
            model_name="venue",
            name="photo_url",
            field=models.URLField(blank=True, verbose_name="لینک تصویر مکان"),
        ),
        migrations.CreateModel(
            name="Organizer",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=200, verbose_name="نام برگزارکننده")),
                (
                    "slug",
                    models.SlugField(
                        blank=True,
                        max_length=220,
                        unique=True,
                        verbose_name="شناسه URL",
                    ),
                ),
                ("description", models.TextField(blank=True, verbose_name="توضیحات")),
                (
                    "logo",
                    models.ImageField(
                        blank=True,
                        null=True,
                        upload_to="organizers/%Y/%m/",
                        verbose_name="لوگو / تصویر",
                    ),
                ),
                ("logo_url", models.URLField(blank=True, verbose_name="لینک لوگو")),
                ("website", models.URLField(blank=True, verbose_name="وب\u200cسایت")),
                ("phone", models.CharField(blank=True, max_length=30, verbose_name="تلفن")),
                ("is_active", models.BooleanField(default=True, verbose_name="فعال")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "halls",
                    models.ManyToManyField(
                        blank=True,
                        related_name="organizers",
                        to="venues.hall",
                        verbose_name="سالن\u200cها",
                    ),
                ),
                (
                    "venues",
                    models.ManyToManyField(
                        blank=True,
                        related_name="organizers",
                        to="venues.venue",
                        verbose_name="مکان\u200cهای برگزاری",
                    ),
                ),
            ],
            options={
                "verbose_name": "برگزارکننده",
                "verbose_name_plural": "برگزارکننده\u200cها",
                "ordering": ["name"],
            },
        ),
    ]
