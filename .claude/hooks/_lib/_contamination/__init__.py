"""Implementation modules for :mod:`check_contamination`."""

from __future__ import annotations

from types import FunctionType


def bind_personal_paths(namespace: dict, component) -> None:
    """Bind Rule 2 to the public facade's mutable global namespace.

    Tests and downstream hooks patch ``check_contamination`` globals directly.
    Rebinding the extracted functions gives every lookup that same dictionary,
    rather than creating a stale copied set of collaborators in this package.
    """
    for name in component.__all__:
        value = getattr(component, name)
        if isinstance(value, FunctionType):
            value = FunctionType(
                value.__code__, namespace, value.__name__, value.__defaults__,
                value.__closure__,
            )
            value.__kwdefaults__ = getattr(
                getattr(component, name), "__kwdefaults__", None)
            value.__annotations__ = getattr(
                getattr(component, name), "__annotations__", {}).copy()
            value.__doc__ = getattr(component, name).__doc__
            value.__module__ = namespace["__name__"]
        namespace[name] = value
