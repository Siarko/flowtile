
_DATA = {}

def clear(component_name: str):
    _DATA[component_name] = {}

def set(component_name: str, var_name: str, data):
    if component_name not in _DATA:
        _DATA[component_name] = {}
    _DATA[component_name][var_name] = data

def set_multiple(component_name: str, variables: dict):
    if component_name not in _DATA:
        _DATA[component_name] = {}
    _DATA[component_name].update(variables)


def get(component_name: str, var_name: str, default = None):
    if component_name not in _DATA:
        return default
    component_store = _DATA[component_name] or {}
    if var_name in component_store:
        return component_store[var_name]
    return default
