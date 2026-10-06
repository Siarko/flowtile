from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, auto
from typing import Callable, Any

from .environment import Environment
from .nodes import Node, VariableNode


class ValueType(Enum):
    INT = auto()
    FLOAT = auto()
    NUMERIC = auto()
    BOOL = auto()
    STRING = auto()
    LIST = auto()
    NODE = auto()
    ANY = auto()

    def matches(self, value: Any) -> bool:
        if self is ValueType.ANY:
            return True
        if self is ValueType.BOOL:
            return isinstance(value, bool)
        if self is ValueType.NUMERIC:
            return isinstance(value, (int, float)) and not isinstance(value, bool)
        if self is ValueType.INT:
            return isinstance(value, int) and not isinstance(value, bool)
        if self is ValueType.FLOAT:
            return isinstance(value, float)
        if self is ValueType.STRING:
            return isinstance(value, str)
        if self is ValueType.LIST:
            return isinstance(value, list)
        if self is ValueType.NODE:
            return isinstance(value, Node)
        raise AssertionError(f"Unhandled ValueType: {self}")


class FunctionCallError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


@dataclass(frozen=True)
class FunctionSpec:
    name: str
    param_types: list[ValueType]
    impl: Callable[..., Any]
    requires_context: bool = False

    @property
    def arity(self) -> int:
        return len(self.param_types)

    def call(self, args: list[Any], env: Environment | None = None) -> Any:
        if len(args) != self.arity:
            raise FunctionCallError(
                f"{self.name}() expects {self.arity} argument(s), got {len(args)}"
            )
        if self.requires_context and env is None:
            raise FunctionCallError(
                f"{self.name}() expects access to runtime environment"
            )
        for i, (expected_type, value) in enumerate(zip(self.param_types, args)):
            if not expected_type.matches(value):
                raise FunctionCallError(
                    f"{self.name}() argument {i} expects {expected_type.name}, "
                    f"got {type(value).__name__} ({value!r})"
                )
        if self.requires_context:
            return self.impl(env, *args)
        return self.impl(*args)

class FunctionRegistry:
    def __init__(self):
        self._functions: dict[str, FunctionSpec] = {}

    def register(self, spec: FunctionSpec) -> None:
        if spec.name in self._functions:
            raise ValueError(f"Function '{spec.name}' is already registered")
        self._functions[spec.name] = spec


    def get(self, name: str) -> FunctionSpec:
        try:
            return self._functions[name]
        except KeyError:
            raise FunctionCallError(f"Unknown function: '{name}'")


    def call(self, name: str, args: list[Any], env: Environment | None = None) -> Any:
        return self.get(name).call(args, env)

    def __contains__(self, name: str) -> bool:
        return name in self._functions

    def extend(self, other: "FunctionRegistry") -> "FunctionRegistry":
        merged = FunctionRegistry()
        merged._functions = {**self._functions, **other._functions}
        return merged

def build_core_registry() -> FunctionRegistry:
    def _div(a, b):
        if b == 0:
            raise FunctionCallError("Division by zero")
        return a / b

    def _is_defined(environment: Environment, node: Node):
        if isinstance(node, VariableNode):
            return environment.exists(node.name)
        raise FunctionCallError(f"Trying to check if {type(node).__name__} is defined")

    def _log(environment: Environment, message: Any):
        prefix = "TRANSFORM"
        if environment.exists("log_prefix"):
            prefix = environment.get("log_prefix")
        print(f"[{prefix}] " + message)
    registry = FunctionRegistry()

    registry.register(FunctionSpec("add", [ValueType.NUMERIC, ValueType.NUMERIC], lambda a, b: a + b))
    registry.register(FunctionSpec("sub", [ValueType.NUMERIC, ValueType.NUMERIC], lambda a, b: a - b))
    registry.register(FunctionSpec("mul", [ValueType.NUMERIC, ValueType.NUMERIC], lambda a, b: a * b))
    registry.register(FunctionSpec("div", [ValueType.NUMERIC, ValueType.NUMERIC], _div))
    registry.register(FunctionSpec("mod", [ValueType.NUMERIC, ValueType.NUMERIC], lambda a, b: a % b))
    registry.register(FunctionSpec("pow", [ValueType.NUMERIC, ValueType.NUMERIC], lambda a, b: a ** b))
    registry.register(FunctionSpec("neg", [ValueType.NUMERIC], lambda a: -a))

    registry.register(FunctionSpec("eq", [ValueType.ANY, ValueType.ANY], lambda a, b: a == b))
    registry.register(FunctionSpec("neq", [ValueType.ANY, ValueType.ANY], lambda a, b: a != b))
    registry.register(FunctionSpec("gt", [ValueType.NUMERIC, ValueType.NUMERIC], lambda a, b: a > b))
    registry.register(FunctionSpec("lt", [ValueType.NUMERIC, ValueType.NUMERIC], lambda a, b: a < b))
    registry.register(FunctionSpec("gteq", [ValueType.NUMERIC, ValueType.NUMERIC], lambda a, b: a >= b))
    registry.register(FunctionSpec("lteq", [ValueType.NUMERIC, ValueType.NUMERIC], lambda a, b: a <= b))

    registry.register(FunctionSpec("and", [ValueType.BOOL, ValueType.BOOL], lambda a, b: a and b))
    registry.register(FunctionSpec("or", [ValueType.BOOL, ValueType.BOOL], lambda a, b: a or b))
    registry.register(FunctionSpec("not", [ValueType.BOOL], lambda a: not a))

    registry.register(FunctionSpec("con", [ValueType.ANY, ValueType.ANY], lambda a, b: str(a)+""+str(b)))
    registry.register(FunctionSpec("is_defined", [ValueType.NODE], _is_defined, requires_context=True))
    registry.register(FunctionSpec("is_none", [ValueType.ANY], lambda a: a is None))
    registry.register(FunctionSpec("log", [ValueType.ANY], _log, requires_context=True))

    return registry
