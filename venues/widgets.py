from django.forms.widgets import Textarea
from django.utils.safestring import mark_safe


class SeatmapLayoutWidget(Textarea):
    def render(self, name, value, attrs=None, renderer=None):
        attrs = attrs.copy() if attrs else {}
        attrs.setdefault("id", "id_layout_json")
        attrs.setdefault("class", "vLargeTextField")
        attrs.setdefault("rows", 6)
        attrs.setdefault("cols", 80)
        attrs.setdefault(
            "style",
            "font-family:monospace;font-size:11px;max-height:120px;",
        )
        ta = super().render(name, value, attrs, renderer)
        return mark_safe(
            '<div class="seatmap-admin-wrap">'
            + ta
            + '<div id="seatmap-editor-root"></div>'
            + "</div>"
        )
