import importlib.util
import sys
from enum import Enum
from pathlib import Path
from typing import Callable

class DeviceInitializer:
    def __init__(self, name: str, initializer_method: Callable):
        self.name = name
        self.initializer_method = initializer_method

    def get_name(self) -> str:
        return self.name

    def initialize(self):
        return self.initializer_method()

class DeviceType(Enum):
    SCREEN = "screen",
    JOYSTICK = "joystick"

_DEVICES: dict[DeviceType, DeviceInitializer | None] = {
    DeviceType.SCREEN: None,
    DeviceType.JOYSTICK: None,
}

def register_screen_provider(provider_name):
    def decorator(cls):
        _DEVICES[DeviceType.SCREEN] = DeviceInitializer(provider_name, cls)
        return cls

    return decorator

def register_joystick_provider(provider_name):
    def decorator(cls):
        _DEVICES[DeviceType.JOYSTICK] = DeviceInitializer(provider_name, cls)
        return cls

    return decorator

def load_user_initializer_path(path: str | None, cwd: str):
    if path is None:
        return
    file = Path(path)
    if not file.is_absolute():
        file = Path(cwd) / file
    if not file.is_file():
        raise RuntimeError(f"Hardware initializer file not found: {path}")
    module_name = f"user_hardware_{len(sys.modules)}_{file.stem}"
    spec = importlib.util.spec_from_file_location(module_name, file)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load hardware initializer from: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    try:
        spec.loader.exec_module(module)
    except Exception:
        del sys.modules[module_name]
        raise

def get_device_initializer(device_type: DeviceType) -> DeviceInitializer:
    device = _DEVICES[device_type]
    if device is None:
        raise Exception(device_type.name + " device not assigned")
    return device
