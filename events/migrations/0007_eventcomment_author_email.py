from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0006_event_organizer_fk"),
    ]

    operations = [
        migrations.AddField(
            model_name="eventcomment",
            name="author_email",
            field=models.EmailField(blank=True, verbose_name="ایمیل"),
        ),
        migrations.AlterField(
            model_name="eventcomment",
            name="author_name",
            field=models.CharField(blank=True, max_length=80, verbose_name="نام"),
        ),
    ]
