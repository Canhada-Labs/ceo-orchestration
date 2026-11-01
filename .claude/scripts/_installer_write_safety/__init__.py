"""Bind split installer-census components to the legacy module namespace."""
from __future__ import annotations
from copy import deepcopy
from types import FunctionType
from . import commands, engine, model, operands, report, syntax, verdicts_a, verdicts_b


def _bind_function(original, namespace):
    bound = FunctionType(original.__code__, namespace, original.__name__, original.__defaults__, original.__closure__)
    bound.__kwdefaults__ = original.__kwdefaults__
    bound.__annotations__ = original.__annotations__.copy()
    bound.__dict__.update(original.__dict__)
    bound.__doc__ = original.__doc__
    bound.__qualname__ = original.__qualname__
    bound.__module__ = namespace["__name__"]
    return bound


def _bind_class(original, namespace):
    if not getattr(original, "__module__", "").startswith("_installer_write_safety"):
        return original
    attrs = dict(vars(original))
    attrs.pop("__dict__", None)
    attrs.pop("__weakref__", None)
    for slot in attrs.get("__slots__", ()):
        attrs.pop(slot, None)
    for name, member in list(attrs.items()):
        if isinstance(member, FunctionType):
            attrs[name] = _bind_function(member, namespace)
        elif isinstance(member, staticmethod):
            attrs[name] = staticmethod(_bind_function(member.__func__, namespace))
        elif isinstance(member, classmethod):
            attrs[name] = classmethod(_bind_function(member.__func__, namespace))
    clone = type(original)(original.__name__, original.__bases__, attrs)
    clone.__module__ = namespace["__name__"]
    clone.__qualname__ = original.__qualname__
    return clone


def bind(namespace):
    """Export every legacy name against one patchable facade namespace."""
    mutable_state = {}
    for component in (engine, syntax, commands, operands, model, verdicts_a, verdicts_b, report):
        for name in component.__all__:
            original = getattr(component, name)
            if isinstance(original, FunctionType):
                namespace[name] = _bind_function(original, namespace)
            elif isinstance(original, type):
                namespace[name] = _bind_class(original, namespace)
            elif isinstance(original, (dict, list, set)):
                namespace[name] = deepcopy(original, mutable_state)
            else:
                namespace[name] = original
