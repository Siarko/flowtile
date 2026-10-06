import enum
from enum import Enum
from typing import Generic, TypeVar

import src.variable_store as vs

class PropertyType(Enum):
    VALUE = "value"
    VARIABLE = "variable"

T = TypeVar("T")

class Property(Generic[T]):

    def __init__(self, prop_type: PropertyType, value, datatype: type | None = None):
        self.prop_type = prop_type
        self.value = value
        self.datatype = datatype

    def get(self, component_name: str) -> T:
        value = None
        if self.prop_type == PropertyType.VALUE:
            value = self.value
        elif self.prop_type == PropertyType.VARIABLE:
            path = self.value.split(".")
            if len(path) == 1:
                value = vs.get(component_name, self.value)
            elif len(path) == 2:
                value = vs.get(path[0], path[1])
            else:
                raise RuntimeError("Incorrect path supplied for variable in component {}: {}", component_name, self.value)
        if self.datatype is not None:
            if issubclass(self.datatype, enum.Enum):
                return self.datatype(value)
        return value

class ComponentPropertyAccessor:

    def __init__(self, component_name: str):
        self.component_name = component_name

    def get(self, prop: Property):
        return prop.get(self.component_name)