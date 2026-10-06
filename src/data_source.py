from __future__ import annotations
from typing import TYPE_CHECKING, Callable

from src.data_source_type import DataSourceType

if TYPE_CHECKING:
    from src.screens import Component


class DataSource:
    def __init__(self, name: str):
        self.name = name
        self.content: list[str] = []
        self.callback: Callable[[Component], list[str]] | None = None
        self.content_type: DataSourceType = DataSourceType.TEXT

    def get_name(self):
        return self.name

    def set_content(self, content: list[str]):
        self.content = content

    def set_callback(self, callback: Callable[[Component], list[str]] | None):
        self.callback = callback

    def get_content(self, component: Component) -> list[str]:
        if self.callback is not None:
            return self.callback(component)
        return self.content

    def set_content_type(self, content_type: DataSourceType):
        self.content_type = content_type

    def get_content_type(self) -> DataSourceType:
        return self.content_type