from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("venues", "0007_organizer_venue_photo"),
    ]

    operations = [
        migrations.AddField(
            model_name="venue",
            name="latitude",
            field=models.DecimalField(
                blank=True,
                decimal_places=6,
                help_text="مثلاً 35.699739 — از Google Maps یا OpenStreetMap کپی کنید.",
                max_digits=9,
                null=True,
                verbose_name="عرض جغرافیایی",
            ),
        ),
        migrations.AddField(
            model_name="venue",
            name="longitude",
            field=models.DecimalField(
                blank=True,
                decimal_places=6,
                help_text="مثلاً 51.391472",
                max_digits=9,
                null=True,
                verbose_name="طول جغرافیایی",
            ),
        ),
    ]
