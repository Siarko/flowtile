import os
import parse
from PIL import ImageFont
from PIL.ImageDraw import ImageDraw


from src.render.bounding_box import BoundingBox
from src.render.component_renderer import ComponentContentRenderer
from src.render.registry import register
from src.screens import Component
from src.screens_schema import RENDERER_PROGRESSBAR

@register(RENDERER_PROGRESSBAR)
class ProgressBarRenderer(ComponentContentRenderer):
    def render(self, canvas: ImageDraw, component: Component, bb: BoundingBox) -> None:
        min_value = self.get_option("min", 0)
        max_value = self.get_option("max", 100)
        font_color = component.prop_access.get(component.color)

        line_count = len(component.data_lines)
        if line_count == 0:
            return
        line_size = bb.h / line_count
        y = bb.y

        for var_set in component.data_variables:
            value = int(var_set.get("value", 0))
            min_value = int(min_value)
            max_value = int(var_set.get("max", max_value))
            w = int(bb.w * (value - min_value) / (max_value - min_value))
            canvas.rectangle((bb.x, y, bb.x+w, y+line_size), font_color)
