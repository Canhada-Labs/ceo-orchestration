"""Domain implementations for the public ``_lib.audit_emit`` facade.

The facade historically owns mutable state and every helper lookup. Ordinary
function re-exports would silently bypass monkeypatches on that facade. Bind
the original code objects to its namespace instead: signatures, source files,
tracebacks and inspect.isfunction remain intact, with no proxy per event.

Imported parts are private declaration templates. Each facade import/reload
gets fresh mutable values and fresh functions; never mutate the templates.
"""

from __future__ import annotations

from copy import deepcopy
from importlib import import_module
from types import FunctionType
from typing import Any, Dict, Tuple


def install(namespace: Dict[str, Any], modules: Tuple[str, ...]) -> None:
    """Publish declarations with the facade as their sole runtime namespace."""
    declarations = {}
    for name in modules:
        module = import_module(f"{__name__}.{name}")
        declarations.update({key: getattr(module, key) for key in module.__all__})
        namespace.setdefault("__annotations__", {}).update(
            getattr(module, "__annotations__", {})
        )
    # One memo preserves aliases between mutable declarations, and a reload
    # cannot inherit rate-limit counters or registry edits from a prior import.
    namespace.update(deepcopy(declarations))
    for name, original in declarations.items():
        if not isinstance(original, FunctionType):
            continue
        bound = FunctionType(
            original.__code__, namespace, original.__name__,
            original.__defaults__, original.__closure__,
        )
        bound.__kwdefaults__ = deepcopy(original.__kwdefaults__)
        bound.__annotations__ = dict(original.__annotations__)
        bound.__dict__.update(original.__dict__)
        bound.__qualname__ = original.__qualname__
        bound.__module__ = namespace["__name__"]
        namespace[name] = bound
