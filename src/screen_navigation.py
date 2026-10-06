from typing import Callable

from src.axis import *
from src.exceptions import NavigationException
from src.screens_schema import Key


class NavigationDirection(enum.Enum):
    LEFT = 0
    RIGHT = 1
    UP = 2
    DOWN = 3


_DIRECTION_MAP = {
    NavigationDirection.LEFT: Direction.ROW,
    NavigationDirection.RIGHT: Direction.ROW,
    NavigationDirection.UP: Direction.COLUMN,
    NavigationDirection.DOWN: Direction.COLUMN,
}


class NavigationOption:
    def __init__(self, direction: NavigationDirection, screen: str):
        self.direction = direction
        self.screen = screen

    def get_screen(self):
        return self.screen

    def get_direction(self):
        return self.direction


class ScreenNavigation:
    def __init__(self):
        self.axes: dict[str, Axis] = {}
        self.root_axis: str | None = None
        self.current_axis: str | None = None
        self._screen_handler: Callable[[str, NavigationDirection], None] | None = None

    def add_axis(self, axis: Axis):
        self.axes[axis.name] = axis

    def get_axis(self, axis_name: str) -> Axis:
        return self.axes[axis_name]

    def set_root_axis(self, axis_name: str):
        if axis_name not in self.axes:
            raise NavigationException(f"Axis \"{axis_name}\" is not defined, add it first")
        self.root_axis = axis_name
        self.current_axis = axis_name

    def get_root_axis(self) -> str:
        if self.root_axis is None:
            raise NavigationException(f"Root Axis is not defined")
        return self.root_axis

    def get_current_axis(self) -> str:
        if self.current_axis is None:
            raise NavigationException("No axis is currently selected")
        return self.current_axis

    def get_current_screen(self) -> str:
        element = self.axes[self.get_current_axis()].get_current_element()
        if element.element_type != AxisElementType.SCREEN:
            raise NavigationException("Navigation error - current selected axis element is not a screen")
        return element.name

    def get_home_screen(self) -> str:
        root_axis = self.get_axis(self.get_root_axis())
        if root_axis.default is None:
            raise NavigationException(f"Root Axis does not have default screen defined")
        return root_axis.default

    def navigate(self, direction: NavigationDirection) -> bool:
        axis, anchor = self._resolve_navigation_axis(self.get_current_screen(), direction)
        if axis is None:
            return False
        axis.go_to(anchor)
        increment = 1 if direction in (NavigationDirection.RIGHT, NavigationDirection.DOWN) else -1
        element = axis.navigate(increment)
        if element is None:
            return False
        self.current_axis = element.name if element.element_type == AxisElementType.AXIS else axis.name
        self.call_screen_handler(self.get_current_screen(), direction)
        return True

    def _resolve_navigation_axis(self, screen: str, direction: NavigationDirection) -> tuple[Axis | None, str]:
        for ax_name in get_screen_references(self.axes, screen):
            if self.axes[ax_name].direction == _DIRECTION_MAP[direction]:
                return self.axes[ax_name], screen
        current = self.get_current_axis()
        ref = get_axis_reference(self.axes, current)
        if ref is not None:
            return self.axes[ref], current
        return None, ''

    def set_screen_handler(self, handler: Callable[[str, NavigationDirection], None]):
        self._screen_handler = handler

    def call_screen_handler(self, screen: str, direction: NavigationDirection):
        if self._screen_handler is not None:
            self._screen_handler(screen, direction)

    def get_possible_directions(self, screen: str | None = None) -> list[NavigationOption]:
        if screen is None:
            screen = self.get_current_screen()
        result = []
        for direction in NavigationDirection:
            axis, anchor = self._resolve_navigation_axis(screen, direction)
            if axis is None:
                continue
            element = axis.peek_from(anchor, 1 if direction in (NavigationDirection.RIGHT, NavigationDirection.DOWN) else -1)
            if element is None:
                continue
            target = self._element_to_screen(element)
            if target is not None and target != screen:
                result.append(NavigationOption(direction, target))
        return result

    def _element_to_screen(self, element: AxisElement) -> str | None:
        if element.element_type == AxisElementType.SCREEN:
            return element.name
        target = self.axes.get(element.name)
        if target is None:
            return None
        current = target.get_current_element()
        return current.name if current.element_type == AxisElementType.SCREEN else None


def get_screen_references(axes: dict[str, Axis], screen: str) -> list[str]:
    result = []
    for ax_name, axis in axes.items():
        for element in axis.get_elements():
            if element.element_type == AxisElementType.SCREEN and element.name == screen:
                result.append(ax_name)
    return result


def get_axis_reference(axes: dict[str, Axis], axis: str) -> str | None:
    for ax_name, ax in axes.items():
        for element in ax.get_elements():
            if element.element_type == AxisElementType.AXIS and element.name == axis:
                return ax_name
    return None


def validate_config(axes: dict[str, Axis], root_axis: str):
    for ax_name, axis in axes.items():
        for element in axis.get_elements():
            if element.element_type == AxisElementType.AXIS:
                bound_axis = axes.get(element.name)
                if bound_axis is None:
                    raise NavigationException(
                        f"Axis \"{ax_name}\" intersects axis \"{element.name}\" which is not defined")
                if bound_axis.direction == axis.direction:
                    raise NavigationException(
                        f"Axis \"{ax_name}\" intersects axis \"{element.name}\" with the same direction - must be perpendicular")
            else:
                screen_references = get_screen_references(axes, element.name)
                if len(screen_references) > 2:
                    raise NavigationException(f"Screen \"{element.name}\" is on more than 2 axes: {screen_references}")
    root = axes[root_axis]
    if root.default is None:
        raise NavigationException(f"Root axis \"{root_axis}\" must have a default screen defined")
    default_element = root.get_element(root.default)
    if default_element is None:
        raise NavigationException(
            f"Root axis \"{root_axis}\" default \"{root.default}\" is not an element of this axis")
    if default_element.element_type != AxisElementType.SCREEN:
        raise NavigationException(
            f"Root axis \"{root_axis}\" default \"{root.default}\" must be a screen, not an axis")


def load_from_config(config: dict):
    result = ScreenNavigation()
    root_axis_name: str | None = None
    for axis_name, axis_data in config.items():
        axis = Axis(axis_name)
        axis.set_direction(axis_data[Key.DIRECTION])
        axis.set_default(axis_data[Key.NAV_DEFAULT])
        axis.set_wrap(axis_data[Key.NAV_WRAP])
        if axis_data[Key.NAV_ROOT]:
            root_axis_name = axis_name
        for element_data in axis_data[Key.NAV_ELEMENTS]:
            element = AxisElement(element_data[Key.NAV_ELEMENTS_NAME], element_data[Key.NAV_ELEMENTS_TYPE])
            axis.add_element(element)
        result.add_axis(axis)
    if root_axis_name is None:
        raise NavigationException("No root axis defined")
    result.set_root_axis(root_axis_name)
    validate_config(result.axes, root_axis_name)
    return result
