"""Components shared by the ``check_agent_spawn`` hook.

The package deliberately lives below ``_lib`` so hook inventory counters do
not mistake its modules for independently registered hook entry points.
"""
from __future__ import annotations

from types import FunctionType

from . import file_assignment, skill_reference


def bind(namespace: dict) -> None:
    """Preserve legacy mutable globals without copying state between calls."""
    for component in (skill_reference, file_assignment):
        for name in component.__all__:
            original = getattr(component, name)
            if not isinstance(original, FunctionType):
                namespace[name] = original
                continue
            bound = FunctionType(
                original.__code__, namespace, original.__name__,
                original.__defaults__, original.__closure__,
            )
            bound.__kwdefaults__ = original.__kwdefaults__
            bound.__annotations__ = original.__annotations__.copy()
            bound.__dict__.update(original.__dict__)
            bound.__doc__ = original.__doc__
            bound.__qualname__ = original.__qualname__
            bound.__module__ = namespace["__name__"]
            namespace[name] = bound
