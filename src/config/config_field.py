from typing import Any

class ConfigField:
    def __init__(self, key: str | list[str], default: Any = None):
        self.key: str | list[str] = key
        self.default = default
