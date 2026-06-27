from django.db import migrations, models


def backfill_seat_grid(apps, schema_editor):
    Seat = apps.get_model("venues", "Seat")
    for s in Seat.objects.all():
        gc, gr = 0, 0
        if getattr(s, "pos_x", None) is not None:
            try:
                gc = max(0, int(float(s.pos_x)))
            except (TypeError, ValueError):
                gc = 0
        if getattr(s, "pos_y", None) is not None:
            try:
                gr = max(0, int(float(s.pos_y)))
            except (TypeError, ValueError):
                gr = 0
        if gc == 0 and gr == 0 and s.id:
            gr = (s.id // 100) % 500
            gc = s.id % 100
        Seat.objects.filter(pk=s.pk).update(grid_c=gc, grid_r=gr)


class Migration(migrations.Migration):

    dependencies = [
        ("venues", "0004_alter_hall_options_alter_seat_options_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="seat",
            name="grid_c",
            field=models.PositiveIntegerField(default=0, verbose_name="ستون شبکه"),
        ),
        migrations.AddField(
            model_name="seat",
            name="grid_r",
            field=models.PositiveIntegerField(default=0, verbose_name="ردیف شبکه"),
        ),
        migrations.AddField(
            model_name="seat",
            name="kind",
            field=models.CharField(
                choices=[
                    ("standard", "عادی"),
                    ("vip", "VIP"),
                    ("wheelchair", "ویلچر"),
                    ("blocked", "مسدود"),
                ],
                default="standard",
                max_length=20,
                verbose_name="نوع صندلی",
            ),
        ),
        migrations.RunPython(backfill_seat_grid, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="seat",
            name="pos_x",
        ),
        migrations.RemoveField(
            model_name="seat",
            name="pos_y",
        ),
        migrations.RemoveField(
            model_name="seat",
            name="section",
        ),
        migrations.DeleteModel(
            name="Section",
        ),
        migrations.DeleteModel(
            name="Zone",
        ),
    ]
