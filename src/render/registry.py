from src.render.component_renderer import ComponentContentRenderer

_types: dict[str, type[ComponentContentRenderer]] = {}
_instances: dict[str, ComponentContentRenderer] = {}


def register(name: str):
    def decorator(cls):
        if not issubclass(cls, ComponentContentRenderer):
            raise TypeError(f"{cls.__name__} does not implement ComponentContentRenderer")
        _types[name] = cls
        return cls
    return decorator


def get(name: str, instance_id: str) -> ComponentContentRenderer:
    if name not in _types:
        raise KeyError(f"No content renderer registered: {name}")
    key = name + "-" +instance_id
    if key not in _instances:
        _instances[key] = _types[name]()
    return _instances[key]