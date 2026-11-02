"""Isolated implementation templates for profile-opus-4-7.py."""
from __future__ import annotations

from copy import deepcopy
from importlib import import_module
from types import FunctionType
from typing import Any, Dict, Tuple


_IMPORTS = frozenset((
    "argparse", "hashlib", "json", "math", "os", "shutil", "subprocess",
    "sys", "tempfile", "time", "datetime", "timezone", "Path", "Any",
    "Callable", "Dict", "List", "Optional", "Tuple",
))


def _bind(function: FunctionType, namespace: Dict[str, Any]) -> FunctionType:
    bound = FunctionType(
        function.__code__, namespace, function.__name__,
        function.__defaults__, function.__closure__,
    )
    bound.__kwdefaults__ = deepcopy(function.__kwdefaults__)
    bound.__annotations__ = dict(function.__annotations__)
    bound.__dict__.update(function.__dict__)
    bound.__qualname__ = function.__qualname__
    bound.__module__ = namespace["__name__"]
    return bound


def install(namespace: Dict[str, Any], modules: Tuple[str, ...]) -> None:
    """Export every original private/public declaration to facade globals."""
    declarations: Dict[str, Any] = {}
    for name in modules:
        module = import_module("{}.{}".format(__name__, name))
        namespace.setdefault("__annotations__", {}).update(
            getattr(module, "__annotations__", {})
        )
        declarations.update({
            key: value for key, value in vars(module).items()
            if not key.startswith("__") and key not in _IMPORTS
        })

    namespace.update(deepcopy(declarations))
    for name, original in declarations.items():
        if isinstance(original, FunctionType):
            namespace[name] = _bind(original, namespace)
        elif isinstance(original, type) and original.__module__.startswith(__name__):
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

    # The 103-line original docstring is stored unchanged as documentation,
    # rather than inflating the latency implementation past the size ceiling.
    docs = import_module("{}.hook_latency_docs".format(__name__))
    namespace["run_hook_latency"].__doc__ = docs.HOOK_LATENCY_DOC
