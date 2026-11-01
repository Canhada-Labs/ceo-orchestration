"""Bind canonical-edit components to the legacy hook's public namespace.

The hook exposes mutable globals, counters and injectable functions. A normal
re-export would give implementations a different globals dictionary, breaking
both callers that patch those seams and independent imports of the hook. Bind
the compiled functions once at import time instead of copying mutable state or
synchronizing it around calls. Source locations and signatures remain intact.
"""
from __future__ import annotations

from types import FunctionType

from . import paths, sentinels, session_roots


def bind(namespace: dict) -> None:
    """Install implementations with the owning hook's globals and identity."""
    for component in (paths, sentinels, session_roots):
        for name in component.__all__:
            original = getattr(component, name)
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
