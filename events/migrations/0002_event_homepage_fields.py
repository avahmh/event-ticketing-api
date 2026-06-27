from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="event",
            name="event_type",
            field=models.CharField(
                choices=[
                    ("cinema", "سینما"),
                    ("theater", "تئاتر"),
                    ("concert", "کنسرت"),
                ],
                default="theater",
                max_length=20,
                verbose_name="نوع",
            ),
        ),
        migrations.AddField(
            model_name="event",
            name="genre",
            field=models.CharField(blank=True, max_length=100, verbose_name="ژانر"),
        ),
        migrations.AddField(
            model_name="event",
            name="poster_url",
            field=models.URLField(
                blank=True,
                help_text="لینک تصویر پوستر (اختیاری).",
                verbose_name="آدرس پوستر",
            ),
        ),
        migrations.AddField(
            model_name="event",
            name="is_featured",
            field=models.BooleanField(
                default=False,
                verbose_name="ویژه (اسلایدر صفحه اول)",
            ),
        ),
        migrations.AlterField(
            model_name="event",
            name="is_reserved_seating",
            field=models.BooleanField(default=False, verbose_name="صندلی‌دار"),
        ),
    ]
