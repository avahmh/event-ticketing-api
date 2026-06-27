from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0002_event_homepage_fields"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="poster",
            field=models.ImageField(
                blank=True,
                help_text="تصویر پوستر را از رایانه آپلود کنید.",
                null=True,
                upload_to="event_posters/%Y/%m/",
                verbose_name="پوستر",
            ),
        ),
        migrations.AlterField(
            model_name="event",
            name="poster_url",
            field=models.URLField(
                blank=True,
                help_text="اگر فایل آپلود نکردید، می‌توانید لینک مستقیم تصویر بگذارید.",
                verbose_name="لینک پوستر",
            ),
        ),
    ]
