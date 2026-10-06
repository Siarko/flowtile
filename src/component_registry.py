import copy

from graphlib import TopologicalSorter
from typing import Any
from collections.abc import Callable

from .component import Component

ComponentData = dict[str, Any]
ComponentNameData = dict[str, ComponentData]
ComponentSource = list[list[ComponentNameData]]

from .screens_schema import Key as SchemaKeys, Direction, Align, AlignV, Key

_components = {}
_persistent_components = []

def _extract_screen_components(config: dict[str, Any]) -> ComponentSource:
    result = []
    for screen_name, screen_data in config.items():
        root_component = screen_data.get(SchemaKeys.SCREENS_COMPONENT)
        if type(root_component) == dict:
            for c_name, c_data in root_component.items():
                result.append({c_name: c_data})
    return result

def _flatten_components(sources: list[ComponentSource], blacklist: list[str]) -> dict:
    result = {}
    for source in sources:
        for component_set in source:
            for c_name, c_data in component_set.items():
                if c_name in result.keys() or c_name in blacklist:
                    raise Exception(f"Redefinition of component {c_name}. Components can be defined only once!")
                children = c_data.get(SchemaKeys.COMPONENT_CHILDREN)
                if type(children) == dict:
                    result.update(_flatten_components([[children]], list(result.keys())))
                    c_data[SchemaKeys.COMPONENT_CHILDREN] = list(children.keys())
                result[c_name] = c_data
    return result


def _process_inheritance(components: ComponentNameData) -> dict:
    result = {}
    topo_sort = TopologicalSorter()
    for c_name, c in components.items():
        parent = c.get(SchemaKeys.COMPONENT_PARENT)
        if parent:
            topo_sort.add(c_name, parent)
        else:
            topo_sort.add(c_name)

    for c_name in list(topo_sort.static_order()):
        component = components.get(c_name)
        parent_name = component.get(SchemaKeys.COMPONENT_PARENT)
        if parent_name is None:
            result[c_name] = component
        else:
            merged = copy.deepcopy(result.get(parent_name))
            if merged is None:
                raise Exception(f"Component \"{c_name}\" parent \"{parent_name}\" does not exist!")
            for prop in component[Key.COMPONENT_EXPLICIT_PROPERTIES]:
                merged[prop] = component[prop]
            result[c_name] = merged
    return result

def load_components(config: dict, component_allocator: Callable[[str, dict], Component]) -> None:
    component_sources = [
        [config[SchemaKeys.COMPONENTS] if SchemaKeys.COMPONENTS in config else {}],
        _extract_screen_components(config[SchemaKeys.SCREENS])
    ]
    components = _process_inheritance(_flatten_components(component_sources, []))
    for component_name, component_data in components.items():
        component = component_allocator(component_name, component_data)
        _components[component_name] = component
        if component.persist:
            _persistent_components.append(component_name)

def get_component(name: str) -> Component:
    if name in _components:
        return _components[name]
    raise Exception(f"Component \"{name}\" does not exist!")

def get_persistent_components() -> list[Component]:
    result = []
    for component_name in _persistent_components:
        result.append(get_component(component_name))
    return result