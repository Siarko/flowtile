import enum

from src.direction import Direction
from src.exceptions import NavigationException


class AxisElementType(enum.Enum):
    SCREEN = "screen"
    AXIS = "axis"

class AxisElement:
    def __init__(self, name: str, element_type: AxisElementType):
        self.name = name
        self.element_type = element_type

class Axis:
    def __init__(self, name: str):
        self.name = name
        self.direction: Direction = Direction.ROW
        self.default: str | None = None
        self._default_set = False
        self.wrap: bool = True
        self._elements: list[AxisElement] = []
        self.current_element: int = 0

    def set_direction(self, direction: Direction):
        self.direction = direction

    def set_default(self, name: str):
        self.default = name
        self._default_set = False

    def set_wrap(self, wrap: bool):
        self.wrap = wrap

    def add_element(self, element: AxisElement):
        self._elements.append(element)
        self._init_default()

    def set_elements(self, elements: list[AxisElement]):
        self._elements = elements
        self._init_default()

    def get_elements(self):
        return self._elements

    def get_element(self, name: str, element_type: AxisElementType | None = None):
        for element in self._elements:
            if element.name == name and (element_type is None or element.element_type == element_type):
                return element
        return None

    def _init_default(self):
        if self.default is None and len(self._elements) > 0:
            self.default = self._elements[0].name
        if self.default is not None and not self._default_set:
            self._default_set = self.go_to(self.default)

    def go_to(self, name: str) -> bool:
        idx = self._find_index(name)
        if idx is not None:
            self.current_element = idx
            return True
        return False

    def _peek_from(self, anchor: int, increment: int = 1) -> int | None:
        idx = anchor
        if idx is None:
            return None
        idx += increment
        n = len(self._elements)
        if idx >= n:
            idx = 0 if self.wrap else n - 1
        elif idx < 0:
            idx = n - 1 if self.wrap else 0
        return idx

    def peek_from(self, anchor: str, increment: int = 1) -> AxisElement | None:
        idx = self._find_index(anchor)
        if idx is None:
            return None
        next_id = self._peek_from(idx, increment)
        if next_id is None:
            return None
        return self._elements[next_id]

    def navigate(self, increment: int = 1) -> None | AxisElement:
        if len(self._elements) == 0:
            raise NavigationException(f"Axis {self.name} has no elements")
        if increment == 0:
            return None
        next_id = self._peek_from(self.current_element, increment)
        if next_id is not None:
            self.current_element = next_id
        return self.get_current_element()

    def get_current_element(self):
        return self._elements[self.current_element]

    def _find_index(self, name):
        for i, element in enumerate(self._elements):
            if element.name == name:
                return i
        return None
