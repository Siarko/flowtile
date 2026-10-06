import time
import parse
from PIL.ImageDraw import ImageDraw

from src import component
from src.render.bounding_box import BoundingBox
from src.render.component_renderer import ComponentContentRenderer
from src.render.registry import register
from src.screens import Component
from src.screens_schema import RENDERER_CHART

@register(RENDERER_CHART)
class ImageRenderer(ComponentContentRenderer):

    def __init__(self):
        super().__init__()
        self.history = []
        self.displayed_min: float | None = None
        self.displayed_max: float | None = None
        self.last_render_time: float = 0.0

    def prepare(self, component: Component):
        samples = self.get_option("sample_count", 20)
        format = self.get_option("format", "{value:d}")
        for line in component.data_lines:
            result = parse.parse(format, line)
            if result is None:
                continue
            if len(self.history) >= samples:
                self.history.pop(0)
            self.history.append(int(result.named.get("value", 0)))

    def render(self, canvas: ImageDraw, component: Component, bb: BoundingBox) -> None:
        min_value = self.get_option("min", 0)
        max_value = self.get_option("max", 100)
        auto_scale = self.get_option("autoscale", False)
        underline_color = self.get_option("background", 100)
        line_size = self.get_option("line_size", 1)
        horizontal_grid_lines = self.get_option("grid_values", 5)
        vertical_grid_lines = self.get_option("grid_time", 7)
        show_max = self.get_option("show_max_value", False)

        if auto_scale and self.history:
            min_value, max_value = self.autoscale()
        value_range = max_value - min_value or 1
        line_color = component.prop_access.get(component.color)

        def to_y(v: float) -> int:
            return max(bb.y, min(bb.y2, int(bb.y2 - (v - min_value) / value_range * bb.h)))

        def to_x(i: int, n: int) -> int:
            return bb.x if n <= 1 else int(bb.x + i / (n - 1) * (bb.w - 1))

        # grid
        grid_color = self.get_option("grid_color", 60)
        for i in range(horizontal_grid_lines):
            y = bb.y + int((i + 1) * bb.h / (horizontal_grid_lines + 1))
            canvas.line([(bb.x, y), (bb.x2, y)], fill=grid_color, width=1)
        for i in range(vertical_grid_lines):
            x = bb.x + int((i + 1) * bb.w / (vertical_grid_lines + 1))
            canvas.line([(x, bb.y), (x, bb.y2)], fill=grid_color, width=1)

        if len(self.history) < 2:
            return

        n = len(self.history)
        points = [(to_x(i, n), to_y(v)) for i, v in enumerate(self.history)]

        # fill under chart
        if underline_color != -1:
            for i in range(len(points) - 1):
                x1, y1 = points[i]
                x2, y2 = points[i + 1]
                canvas.polygon([(x1, y1), (x2, y2), (x2, bb.y2), (x1, bb.y2)], fill=underline_color)

        # chart line
        for i in range(len(points) - 1):
            canvas.line([points[i], points[i + 1]], fill=line_color, width=line_size)

        # min/max boundary lines
        canvas.line([(bb.x, bb.y), (bb.x, bb.y2)], fill=line_color, width=1)

        if show_max and self.history:
            peak_value = max(self.history)
            peak_idx = self.history.index(peak_value)
            px, py = points[peak_idx]
            canvas.text((px + 2, max(bb.y, py)), str(peak_value), fill=line_color)

    def autoscale(self):
        target_min = float(min(self.history))
        target_max = float(max(self.history))
        scale_time = self.get_option("scale_time", 1.0)
        now = time.time()
        dt = now - self.last_render_time
        self.last_render_time = now
        if self.displayed_min is None:
            self.displayed_min = target_min
            self.displayed_max = target_max
        else:
            alpha = min(1.0, dt / scale_time)
            self.displayed_min += alpha * (target_min - self.displayed_min)
            self.displayed_max += alpha * (target_max - self.displayed_max)
        return self.displayed_min, self.displayed_max