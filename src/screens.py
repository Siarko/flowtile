import enum
import os
from typing import AnyStr, List, Callable

from PIL.ImageDraw import ImageDraw

import src
from . import component_registry
from .render.bounding_box import BoundingBox
from src.component import Component
from .screen_animation import ScreenAnimation
from .screens_schema import Key, SourceType


class Screen:
    def __init__(self, screen_id: str):
        self.screen_id = screen_id
        self.label: str | None = None
        self.component: str | None = None

    def set_component(self, component_name: str):
        self.component = component_name

    def get_label(self) -> str:
        return self.label or self.screen_id

    def has_label(self) -> bool:
        return self.label is not None

    def get_component(self) -> str:
        if self.component is None:
            raise Exception(f"Root component for screen {self.screen_id} not set")
        return self.component

    def prepare(self, skip: list[str]):
        (component_registry.get_component(self.get_component()).prepare(skip))

    def draw(self, canvas: ImageDraw, bb: BoundingBox):
        (component_registry.get_component(self.get_component()).draw(canvas, bb))

    def get_all_commands(self):
        return self._get_component_commands(component_registry.get_component(self.get_component()))


    def _get_component_commands(self, component: Component) -> list[dict[str, str | bool]]:
        result = []
        if component.source:
            if component.source[Key.COMPONENT_SOURCE_TYPE] == SourceType.COMMAND:
                result.append({
                    "name": component.source[Key.COMPONENT_SOURCE_NAME],
                    "persistent": component.persist
                })
        for child in component.children:
            result.extend(self._get_component_commands(component_registry.get_component(child)))
        return result


class ScreenManager:
    def __init__(self):
        self.screens: dict[str, Screen] = {}
        self.previous_screen: str | None = None
        self.current_screen: str | None = None
        self.screen_change_handler: Callable[[Screen | None, Screen], None] | None = None
        self.screen_change_complete_handler: Callable[[Screen | None, Screen], None] | None = None
        self.screen_animation: ScreenAnimation = ScreenAnimation()
        self.home_screen: str | None = None
        self.complete_handler_used: bool = False


    def set_on_change(self, handler: Callable[[Screen | None, Screen], None]):
        self.screen_change_handler = handler

    def set_on_change_complete(self, handler: Callable[[Screen | None, Screen], None]):
        self.screen_change_complete_handler = handler

    def add_screen(self, screen: Screen):
        self.screens[screen.screen_id] = screen

    def set_home_screen(self, screen_name: str):
        self.home_screen = screen_name

    def call_screen_change_complete(self):
        if self.screen_change_complete_handler and self.previous_screen is not None and self.current_screen is not None:
            self.screen_change_complete_handler(
                self.screens[self.previous_screen],
                self.screens[self.current_screen]
            )

    def get_current_screen(self) -> Screen:
        if self.current_screen is None:
            if self.home_screen is None:
                raise Exception(f"Home screen is not set")
            self.set_current_screen(self.home_screen)
        if self.current_screen is None:
            raise Exception("No default screen defined")
        return self.screens[self.current_screen]

    def set_current_screen(self, screen_id: str):
        if screen_id not in self.screens:
            print(f"Trying to navigate to non existing screen - {screen_id}")
            return
        self.previous_screen = self.current_screen
        self.current_screen = screen_id
        if self.screen_change_handler is not None:
            if self.previous_screen is None:
                self.screen_change_handler(None, self.screens[self.current_screen])
            else:
                self.screen_change_handler(self.screens[self.previous_screen], self.screens[self.current_screen])

    def set_screen_animation(self, animation: ScreenAnimation):
        self.screen_animation = animation

    def draw(self, canvas: ImageDraw, device):
        screen = self.get_current_screen()
        if self.previous_screen is None:
            screen.draw(canvas, BoundingBox(0,0,device.width-1, device.height-1))
        else:
            bb_old, bb_new = self.screen_animation.step(BoundingBox(0,0, device.width-1, device.height-1))
            if bb_old is not None:
                self.complete_handler_used = False
                self.screens[self.previous_screen].draw(canvas, bb_old)
            elif not self.complete_handler_used:
                self.complete_handler_used = True
                self.call_screen_change_complete()
            screen.draw(canvas, bb_new)
