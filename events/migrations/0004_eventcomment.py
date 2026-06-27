from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0003_event_poster"),
    ]

    operations = [
        migrations.CreateModel(
            name="EventComment",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("author_name", models.CharField(max_length=80, verbose_name="نام")),
                ("body", models.TextField(verbose_name="متن نظر")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user_key", models.CharField(blank=True, max_length=100)),
                (
                    "event",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="comments",
                        to="events.event",
                    ),
                ),
            ],
            options={
                "verbose_name": "نظر",
                "verbose_name_plural": "نظرات",
                "ordering": ["-created_at"],
            },
        ),
    ]
