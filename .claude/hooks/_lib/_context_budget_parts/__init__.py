"""Implementation sections for the context-budget CLI compatibility facade.

Functions execute against the facade globals, preserving patched dependencies.
"""

from __future__ import annotations

from copy import deepcopy
from importlib import import_module
from types import FunctionType
from typing import Any, Dict, Tuple


def _bind(function: FunctionType, namespace: Dict[str, Any]) -> FunctionType:
    bound = FunctionType(
        function.__code__, namespace, function.__name__,
        function.__defaults__, function.__closure__,
    )
    bound.__kwdefaults__ = function.__kwdefaults__
    bound.__annotations__ = dict(function.__annotations__)
    bound.__dict__.update(function.__dict__)
    bound.__qualname__ = function.__qualname__
    bound.__module__ = namespace["__name__"]
    return bound


def install(namespace: Dict[str, Any], modules: Tuple[str, ...]) -> None:
    """Re-export all declarations, including private names, in the facade."""
    declarations: Dict[str, Any] = {}
    for name in modules:
        module = import_module("{}.{}".format(__name__, name))
        declarations.update({key: getattr(module, key) for key in module.__all__})
        namespace.setdefault("__annotations__", {}).update(
            getattr(module, "__annotations__", {})
        )
    namespace.update(deepcopy(declarations))
    for name, original in declarations.items():
        if isinstance(original, FunctionType):
            namespace[name] = _bind(original, namespace)
        elif isinstance(original, type) and original.__module__.startswith(__name__):
            # Never change an imported template class: independent facade
            # imports (including test import-by-path) need independent methods.
            attributes = {
                key: value for key, value in vars(original).items()
                if key not in ("__dict__", "__weakref__")
            }
            bound_class = type(original.__name__, original.__bases__, attributes)
            for method_name, method in vars(bound_class).items():
                if isinstance(method, FunctionType):
                    setattr(bound_class, method_name, _bind(method, namespace))
            bound_class.__module__ = namespace["__name__"]
            namespace[name] = bound_class
