"""Bind spool writer declarations to the compatibility facade namespace."""
from __future__ import annotations

from importlib import import_module
from types import FunctionType


def install(namespace, modules):
    """Publish functions so runtime global lookup observes facade monkeypatches."""
    declarations = {}
    for name in modules:
        module = import_module("%s.%s" % (__name__, name))
        declarations.update({key: getattr(module, key) for key in module.__all__})
    for name, original in declarations.items():
        if isinstance(original, FunctionType):
            bound = FunctionType(
                original.__code__, namespace, original.__name__,
                original.__defaults__, original.__closure__,
            )
            bound.__kwdefaults__ = original.__kwdefaults__
            bound.__annotations__ = original.__annotations__
            bound.__dict__.update(original.__dict__)
            bound.__qualname__ = original.__qualname__
            bound.__module__ = namespace["__name__"]
            namespace[name] = bound
        else:
            namespace[name] = original
