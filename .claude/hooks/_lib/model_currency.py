"""Anchored model-family currency rules for PLAN-176."""
from __future__ import annotations

import re
from typing import Iterable, Optional

_RETIRED = frozenset({"claude-opus-4-1"})
_LEGACY_WORKING = frozenset({"claude-fable-5", "claude-fable-5-1"})
_LEGACY_FLOOR = frozenset({"claude-fable-5"})
_TAIL = r"(?:[.-][0-9]+)*(?:-[a-z][a-z0-9]*)*"
_ALLOWED = re.compile(
    r"^(?:claude-(?:opus|sonnet|haiku)-[4-9]" + _TAIL
    + r"|gpt-[5-9]" + _TAIL + r"|o[3-9]" + _TAIL
    + r"|gemini-[2-9]" + _TAIL + r"|grok-[3-9]" + _TAIL + r")$"
)
_FLOOR = re.compile(r"^(?:claude-opus-[4-9]" + _TAIL + r"|gpt-[5-9]" + _TAIL + r"|o[3-9]" + _TAIL + r")$")
_PREFIXES = tuple(
    ["claude-%s-%d" % (family, major) for family in ("opus", "sonnet", "haiku") for major in range(4, 10)]
    + ["gpt-%d" % major for major in range(5, 10)]
    + ["o%d" % major for major in range(3, 10)]
    + ["gemini-%d" % major for major in range(2, 10)]
    + ["grok-%d" % major for major in range(3, 10)]
)


def _explicit(name: str, models: Optional[Iterable[str]]) -> bool:
    return models is not None and name in frozenset(models)


def availability_entries(explicit_models: Iterable[str]) -> list:
    """Stable explicit IDs followed by native major-version availability prefixes."""
    out = []
    for model in list(explicit_models) + list(_PREFIXES):
        if model not in out:
            out.append(model)
    return out


def is_allowed_model(name: object, explicit_models: Optional[Iterable[str]] = None) -> bool:
    """Accept approved semantic families or an explicit legacy working ID."""
    return isinstance(name, str) and name not in _RETIRED and (
        bool(_ALLOWED.fullmatch(name)) or _explicit(name, explicit_models)
        or (explicit_models is None and name in _LEGACY_WORKING)
    )


def is_veto_floor_model(name: object, explicit_models: Optional[Iterable[str]] = None) -> bool:
    """Accept VETO-capable families or an explicit legacy floor ID."""
    return isinstance(name, str) and name not in _RETIRED and (
        bool(_FLOOR.fullmatch(name)) or _explicit(name, explicit_models)
        or (explicit_models is None and name in _LEGACY_FLOOR)
    )


def main(argv: Optional[list] = None) -> int:
    """Exit 0 for an admitted model, 1 for rejection, 2 for invalid usage."""
    import sys

    args = list(sys.argv[1:] if argv is None else argv)
    veto = args[:1] == ["--veto"]
    if veto:
        args = args[1:]
    if len(args) != 1:
        return 2
    predicate = is_veto_floor_model if veto else is_allowed_model
    return 0 if predicate(args[0]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
