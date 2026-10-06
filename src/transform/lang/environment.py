from __future__ import annotations

from typing import Any

class UndefinedVariableError(Exception):
    def __init__(self, name: str):
        super().__init__(f"Undefined variable: '{name}'")
        self.name = name


class VariableTypeConflictError(Exception):
    def __init__(self, name: str, existing_value: Any, attempted_value: Any):
        super().__init__(
            f"Variable '{name}' type conflict: existing={type(existing_value).__name__}, "
            f"attempted={type(attempted_value).__name__}"
        )
        self.name = name


class Environment:
    def __init__(self, static_store: dict[str, Any]):
        self._static = static_store
        self._dynamic: dict[str, Any] = {}

    def exists(self, name: str) -> bool:
        return name in self._dynamic or name in self._static

    def get(self, name: str) -> Any:
        if name in self._static:
            return self._static[name]
        if name in self._dynamic:
            return self._dynamic[name]
        raise UndefinedVariableError(name)

    def declare(self, name: str, default_value: Any) -> None:
        if not self.exists(name):
            self._dynamic[name] = default_value

    def set(self, name: str, value: Any) -> None:
        if name in self._static:
            self._static[name] = value
        else:
            self._dynamic[name] = value

    def append_to_list(self, name: str, value: Any) -> None:
        if not self.exists(name):
            self.declare(name, [])
        current = self.get(name)
        if not isinstance(current, list):
            raise VariableTypeConflictError(name, current, value)
        current.append(value)

    def child_scope(self) -> "Environment":
        child = Environment(self._static)
        child._dynamic = dict(self._dynamic)
        return child

    def set_multiple(self, var_set: dict):
        for k,v in var_set.items():
            self.set(k, v)

    def dump(self):
        result = {}
        result.update(self._static)
        result.update(self._dynamic)
        return result

    def flush(self):
        self._dynamic.clear()