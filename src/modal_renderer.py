import time
from collections import deque
from dataclasses import dataclass
from enum import Enum
from typing import Generator

from PIL.ImageDraw import ImageDraw

from .data_source import DataSource
from .data_source_type import DataSourceType
from .render.bounding_box import BoundingBox
from .screens import Screen, Component
import src.data_source_collection as DataSourceCollection


class ModalType(Enum):
    INFO = "info"
    WARN = "warn"
    ERROR = "error"


@dataclass
class Modal:
    type: ModalType
    title: str
    message: str
    expire_at: float


class ModalRenderer:
    SOURCE_TYPE = 'modal.type'
    SOURCE_TITLE = 'modal.title'
    SOURCE_MESSAGE = 'modal.message'

    def __init__(self, modal_screen: Screen):
        self.modal_screen = modal_screen
        self._queue: deque[Modal] = deque()
        self.register_data_sources()

    def register_data_sources(self):
        type_data_source = DataSource(self.SOURCE_TYPE)
        type_data_source.set_content_type(DataSourceType.IMAGE)
        type_data_source.set_callback(lambda component: ["modal/"+self._queue[0].type.value+".png"] if self.is_active() else [])
        DataSourceCollection.register(type_data_source)

        title_data_source = DataSource(self.SOURCE_TITLE)
        title_data_source.set_callback(lambda component: [self._queue[0].title] if self.is_active() else [])
        DataSourceCollection.register(title_data_source)

        content_data_source = DataSource(self.SOURCE_MESSAGE)
        content_data_source.set_callback(lambda component: [self._queue[0].message] if self.is_active() else [])
        DataSourceCollection.register(content_data_source)

    def queue(self, modal_type: ModalType, title: str, message: str, timeout: int = 5):
        self._queue.append(Modal(
            type=modal_type,
            title=title,
            message=message,
            expire_at=time.time() + timeout,
        ))

    def is_active(self) -> bool:
        while self._queue and self._queue[0].expire_at <= time.time():
            self._queue.popleft()
        return bool(self._queue)

    def render(self, canvas: ImageDraw, device):
        if not self.is_active():
            return
        self.modal_screen.prepare([])
        bb = BoundingBox(10, 10, device.width-20, device.height-20)
        self.modal_screen.draw(canvas, bb)

    def _iter_components(self, screen: Screen) -> Generator[Component, None, None]:
        for component in screen.get_components():
            yield component
            yield from self._iter_children(component)

    def _iter_children(self, component: Component) -> Generator[Component, None, None]:
        for child in component.children.values():
            yield child
            yield from self._iter_children(child)