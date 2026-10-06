from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from PIL.ImageDraw import ImageDraw

if TYPE_CHECKING:
    from src.screens import Component
    from src.render.bounding_box import BoundingBox


class ComponentContentRenderer(ABC):

    def __init__(self):
        self.options = {}

    def prepare(self, component: Component):
        pass

    @abstractmethod
    def render(self, canvas: ImageDraw, component: Component, bb: BoundingBox) -> None: ...

    def set_options(self, options: dict) -> None:
        self.options = options

    def get_option(self, name: str, default):
        if name not in self.options:
            return default
        return self.options[name]
