from __future__ import annotations

from copy import deepcopy
from importlib import import_module
from types import FunctionType
from typing import Any, Dict, Tuple

def install(namespace: Dict[str, Any], modules: Tuple[str, ...]) -> None:
    declarations = {}
    for name in modules:
        module = import_module(f"{__name__}.{name}")
        declarations.update({key: getattr(module, key) for key in module.__all__})
        namespace.setdefault("__annotations__", {}).update(getattr(module, "__annotations__", {}))
    namespace.update(deepcopy(declarations))
    for name, original in declarations.items():
        if not isinstance(original, FunctionType):
            continue
        bound = FunctionType(original.__code__, namespace, original.__name__, original.__defaults__, original.__closure__)
        bound.__kwdefaults__ = deepcopy(original.__kwdefaults__)
        bound.__annotations__ = dict(original.__annotations__)
        bound.__dict__.update(original.__dict__)
        bound.__qualname__ = original.__qualname__
        bound.__module__ = namespace["__name__"]
        namespace[name] = bound
