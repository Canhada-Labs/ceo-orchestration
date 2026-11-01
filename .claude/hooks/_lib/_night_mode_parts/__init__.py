"""Night-mode implementation declarations bound into the CLI facade.

Each import constructs fresh functions with the facade's globals so tests and
callers patching facade symbols continue to affect the implementation.
"""

from __future__ import annotations

from importlib import import_module
from types import FunctionType
from typing import Any, Dict, Tuple


def install(namespace: Dict[str, Any], modules: Tuple[str, ...]) -> None:
    for module_name in modules:
        module = import_module(f"{__name__}.{module_name}")
        for name in module.__all__:
            original = getattr(module, name)
            if isinstance(original, FunctionType):
                bound = FunctionType(
                    original.__code__, namespace, original.__name__,
                    original.__defaults__, original.__closure__,
                )
                bound.__kwdefaults__ = dict(original.__kwdefaults__ or {})
                bound.__annotations__ = dict(original.__annotations__)
                bound.__dict__.update(original.__dict__)
                bound.__qualname__ = original.__qualname__
                bound.__module__ = namespace["__name__"]
                namespace[name] = bound
            else:
                namespace[name] = original
