from itertools import count

import os
from PIL import ImageFont
from PIL.ImageDraw import ImageDraw

from src.render.bounding_box import BoundingBox
from src.render.component_renderer import ComponentContentRenderer
from src.render.registry import register
from src.screens import Component
from src.screens_schema import Align, AlignV, RENDERER_TEXT_LINE_SPACE
from src.screens_schema import RENDERER_TEXT

_FONT_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'font')
_DEFAULT_FONT = 'Tiny5-Regular.ttf'

@register(RENDERER_TEXT)
class TextRenderer(ComponentContentRenderer):
    def render(self, canvas: ImageDraw, component: Component, bb: BoundingBox) -> None:
        line_spacing = self.get_option(RENDERER_TEXT_LINE_SPACE, 0)
        font_file = component.font_name or _DEFAULT_FONT
        font_size = component.prop_access.get(component.font_size)
        font_color = component.prop_access.get(component.color)
        font = ImageFont.truetype(os.path.join(_FONT_DIR, font_file), font_size)
        align = component.align.get(component.name)
        align_v = component.align_v.get(component.name)
        line_height = font_size + line_spacing

        if align == Align.LEFT:
            text_x = bb.x
            anchor_h = "l"
        elif align == Align.CENTER:
            text_x = bb.x + bb.w / 2
            anchor_h = "m"
        else:
            text_x = bb.x + bb.w
            anchor_h = "r"

        if align_v == AlignV.TOP:
            text_y = bb.y
            anchor_v = "t"
        elif align_v == AlignV.MIDDLE:
            all_lines_h = len(component.data_lines) * line_height - line_spacing
            text_y = bb.y + bb.h/2 - all_lines_h/2 + line_height/2
            anchor_v = "m"
        else:
            text_y = bb.y + bb.h
            anchor_v = "b"
            line_height *= -1

        for line in component.data_lines:
            text = line

            canvas.text(
                (text_x, text_y),
                text,
                anchor=anchor_h+anchor_v,
                fill=font_color,
                font=font
            )
            text_y += line_height
