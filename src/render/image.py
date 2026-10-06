import os
from PIL import Image
from PIL.ImageDraw import ImageDraw

from src.render.bounding_box import BoundingBox
from src.render.component_renderer import ComponentContentRenderer
from src.render.registry import register
from src.screens import Component
from src.screens_schema import AlignV, Align
from src.screens_schema import RENDERER_IMAGE

_IMAGE_DIR = os.path.join(os.path.dirname(__file__), '..', '..', 'images')

@register(RENDERER_IMAGE)
class ImageRenderer(ComponentContentRenderer):
    def render(self, canvas: ImageDraw, component: Component, bb: BoundingBox) -> None:
        align = component.align.get(component.name)
        align_v = component.align_v.get(component.name)
        for line in component.data_lines:
            image_path = os.path.join(_IMAGE_DIR, line)
            try:
                img = Image.open(image_path).convert('L')
                img.thumbnail((bb.w, bb.h), Image.Resampling.LANCZOS)
                img_w, img_h = img.size
                if align == Align.LEFT:
                    img_x = bb.x
                elif align == Align.CENTER:
                    img_x = bb.x + (bb.w - img_w) // 2
                else:
                    img_x = bb.x + bb.w - img_w
                if align_v == AlignV.TOP:
                    img_y = bb.y
                elif align_v == AlignV.MIDDLE:
                    img_y = bb.y + (bb.h - img_h) // 2
                else:
                    img_y = bb.y + bb.h - img_h
                canvas._image.paste(img, (img_x, img_y))
            except Exception as e:
                print(f"Failed to load image {image_path}: {e}")