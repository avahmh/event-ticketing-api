from django.db import transaction


def build_layout_v2_from_seats(hall):
    cells = []
    for s in hall.seats.all().order_by("grid_r", "grid_c", "id"):
        cells.append(
            {
                "c": s.grid_c,
                "r": s.grid_r,
                "t": "s",
                "seat_id": s.id,
                "kind": s.kind,
                "row_label": s.row_label,
                "seat_number": s.seat_number,
            }
        )
    max_c = max((x["c"] for x in cells), default=0) + 1
    max_r = max((x["r"] for x in cells), default=0) + 1
    return {
        "version": 2,
        "grid": {"cols": max(24, max_c + 2), "rows": max(14, max_r + 2)},
        "stage": {"edge": "north", "label": "صحنه اجرا"},
        "cells": cells,
    }


def sync_hall_layout_to_seats(hall):
    layout = hall.layout_json or {}
    if not isinstance(layout, dict) or layout.get("version") != 2:
        return
    cells = layout.get("cells")
    if not isinstance(cells, list):
        return
    from .models import Seat

    seat_cells = [
        x for x in cells if isinstance(x, dict) and x.get("t") == "s"
    ]
    if not seat_cells:
        Seat.objects.filter(hall=hall).delete()
        return

    with transaction.atomic():
        wanted = set()
        for cell in cells:
            if not isinstance(cell, dict) or cell.get("t") != "s":
                continue
            c = int(cell.get("c", 0))
            r = int(cell.get("r", 0))
            kind = cell.get("kind") or Seat.KIND_STANDARD
            if kind not in dict(Seat.KIND_CHOICES):
                kind = Seat.KIND_STANDARD
            rl = (cell.get("row_label") or "R")[:20]
            sn = str(cell.get("seat_number") or "1")[:20]
            sid = cell.get("seat_id")
            if sid:
                seat = (
                    Seat.objects.select_for_update()
                    .filter(id=int(sid), hall_id=hall.id)
                    .first()
                )
                if not seat:
                    continue
                seat.grid_c = c
                seat.grid_r = r
                seat.kind = kind
                seat.row_label = rl
                seat.seat_number = sn
                seat.sort_order = r * 10000 + c
                seat.save(
                    update_fields=[
                        "grid_c",
                        "grid_r",
                        "kind",
                        "row_label",
                        "seat_number",
                        "sort_order",
                    ]
                )
                wanted.add(seat.id)
            else:
                seat = Seat.objects.create(
                    hall=hall,
                    row_label=rl,
                    seat_number=sn,
                    grid_c=c,
                    grid_r=r,
                    kind=kind,
                    sort_order=r * 10000 + c,
                )
                cell["seat_id"] = seat.id
                wanted.add(seat.id)
        to_remove = Seat.objects.filter(hall=hall).exclude(id__in=wanted)
        to_remove.delete()
        hall.layout_json = layout
        hall.save(update_fields=["layout_json"])
