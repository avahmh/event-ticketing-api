from django.db import migrations, models
import django.db.models.deletion


def migrate_organizer_names(apps, schema_editor):
    Event = apps.get_model("events", "Event")
    Organizer = apps.get_model("venues", "Organizer")
    for event in Event.objects.all():
        old_name = (getattr(event, "organizer_old", None) or "").strip()
        if not old_name:
            continue
        org, _ = Organizer.objects.get_or_create(
            name=old_name,
            defaults={"is_active": True},
        )
        if event.venue_id and not org.venues.filter(pk=event.venue_id).exists():
            org.venues.add(event.venue_id)
        if event.hall_id and not org.halls.filter(pk=event.hall_id).exists():
            org.halls.add(event.hall_id)
        event.organizer = org
        event.save(update_fields=["organizer"])


class Migration(migrations.Migration):

    dependencies = [
        ("events", "0005_event_wallpaper"),
        ("venues", "0007_organizer_venue_photo"),
    ]

    operations = [
        migrations.RenameField(
            model_name="event",
            old_name="organizer",
            new_name="organizer_old",
        ),
        migrations.AddField(
            model_name="event",
            name="organizer",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="events",
                to="venues.organizer",
                verbose_name="برگزارکننده",
            ),
        ),
        migrations.RunPython(migrate_organizer_names, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="event",
            name="organizer_old",
        ),
    ]
