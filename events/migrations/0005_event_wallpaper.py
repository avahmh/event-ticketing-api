from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0004_eventcomment"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="wallpaper",
            field=models.ImageField(
                blank=True,
                help_text="تصویر عریض افقی برای اسلایدر و بالای صفحه رویداد (مثل بنر تیوال).",
                null=True,
                upload_to="event_wallpapers/%Y/%m/",
                verbose_name="بنر / والپیپر",
            ),
        ),
        migrations.AddField(
            model_name="event",
            name="wallpaper_url",
            field=models.URLField(
                blank=True,
                help_text="لینک تصویر عریض افقی (اختیاری).",
                verbose_name="لینک بنر",
            ),
        ),
    ]
