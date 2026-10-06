from typing import Callable, Any
import src.transform.lang.functions as flowline_functions

import importlib.util
import sys
from pathlib import Path

METHOD_TYPE = Callable[[list[Any]], list[Any]]

_FUNCTION_REGISTRY = flowline_functions.build_core_registry()

def register_function(name: str, argument_types: list[flowline_functions.ValueType], context: bool = False):
    def decorator(cls):
        _FUNCTION_REGISTRY.register(flowline_functions.FunctionSpec(
            name, argument_types, cls, context
        ))
        return cls
    return decorator

def load_user_functions(function_paths: list[str]):
    for path in function_paths:
        file = Path(path)
        if not file.is_file():
            raise RuntimeError(f"User functions file not found: {path}")

        module_name = f"user_functions_{len(sys.modules)}_{file.stem}"

        spec = importlib.util.spec_from_file_location(module_name, file)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Cannot load user functions from: {path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        try:
            spec.loader.exec_module(module)
        except Exception:
            del sys.modules[module_name]
            raise

def get_function_registry():
    return _FUNCTION_REGISTRY