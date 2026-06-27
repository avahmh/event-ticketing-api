from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("venues", "0002_venue_area_venue_city"),
    ]

    operations = [
        migrations.AddField(
            model_name="hall",
            name="layout_json",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
