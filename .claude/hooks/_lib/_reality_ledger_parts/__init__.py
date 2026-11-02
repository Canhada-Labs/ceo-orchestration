"""Bind domain declarations to each reality-ledger facade import."""
from __future__ import annotations

from copy import deepcopy
from importlib import import_module
from types import FunctionType

_MODULES = (
    "constants", "walking", "environment", "claims", "audit_actions",
    "estimate_history", "estimate_detection", "estimate_emission",
    "findings", "dispatch",
)


def _bind_function(fn, namespace):
    bound = FunctionType(fn.__code__, namespace, fn.__name__, fn.__defaults__, fn.__closure__)
    bound.__kwdefaults__ = deepcopy(fn.__kwdefaults__)
    bound.__annotations__ = dict(fn.__annotations__)
    bound.__dict__.update(fn.__dict__)
    bound.__qualname__ = fn.__qualname__
    bound.__module__ = namespace["__name__"]
    bound.__doc__ = fn.__doc__
    return bound


def _bind_class(cls, namespace):
    attributes = {}
    for name, value in vars(cls).items():
        if name in ("__dict__", "__weakref__"):
            continue
        if isinstance(value, FunctionType):
            value = _bind_function(value, namespace)
        elif isinstance(value, (staticmethod, classmethod)):
            value = type(value)(_bind_function(value.__func__, namespace))
        attributes[name] = value
    attributes["__module__"] = namespace["__name__"]
    return type(cls)(cls.__name__, cls.__bases__, attributes)


def install(namespace):
    declarations = {}
    for name in _MODULES:
        module = import_module(f"{__name__}.{name}")
        declarations.update({key: getattr(module, key) for key in module.__all__})
        namespace.setdefault("__annotations__", {}).update(getattr(module, "__annotations__", {}))
    namespace.update(deepcopy(declarations))
    for name, value in declarations.items():
        if isinstance(value, FunctionType):
            namespace[name] = _bind_function(value, namespace)
        elif isinstance(value, type):
            namespace[name] = _bind_class(value, namespace)
