"""_lib/audit_emit_dispatch.py — lazy-import dispatch shim (PLAN-094 Wave E).

Closes PLAN-090 v1.24.0 AC9c spawn-hook microbench regression: p95=73.22ms
vs 53.73ms baseline (ratio 1.363 > 1.05 limit) + p99=75.68ms vs 55.46ms
(ratio 1.364 > 1.10 limit). Attributed to `_lib/audit_emit.py` 5688-LoC
module cold-import (E.1 baseline: 119ms cumulative, self 11ms; `inspect`
contributes 8ms, `typing` 7ms — combined 31ms of import-time tax).

ADR-115 §exception #1 P0 security ship-before-perf rationale: v1.24.0
prioritized capability_surface_delta=0 (ADR-118 Phase C enforcing) over
perf closure. PLAN-094 absorbs the closure per ADR-124 §Part 2 mechanical
hotfix scope.

## Architecture — PEP 562 module-level __getattr__

Python 3.7+ supports module-level `__getattr__` (PEP 562). On first
attribute access for an `emit_<action>` name, the dispatch shim imports
the full `audit_emit` module ON DEMAND, retrieves the real attr, caches
it in the dispatch module's namespace, and returns it. Subsequent
accesses hit the local cache — zero re-import cost.

The ALLOW path of `check_agent_spawn.py` (line 2-3KB of pre-decision
logic) does NOT call any emit function. It imports
`_lib.audit_emit_dispatch` instead of `_lib.audit_emit`; the shim itself
imports only `sys`, `typing` (stdlib, already in interpreter base);
audit_emit cold-import is deferred until a hook actually emits an event.

## API parity

All public surface of `_lib.audit_emit` is available via the shim:

- `emit_generic(action, **fields)` — called explicitly in 139 sites
- 172 `emit_<action>` typed wrappers (count as of HEAD `5c65a58`)
- `_KNOWN_ACTIONS` constant (frozenset)
- `_ATLAS_REGISTRY` constant (Dict[action, ATT&CK technique])
- `iter_events()` generator

Private helpers (`_audit_emit`, `_format_payload`, etc.) are NOT
re-exposed — the dispatch module is a public-API mirror, not a full
proxy.

## Compatibility — monkeypatch + __wrapped__

`unittest.mock.patch("_lib.audit_emit_dispatch.emit_X")` works because
PEP 562 `__getattr__` only fires when the attribute is NOT in the
module's `globals()`. After first access, the real attr is set into
`globals()` via `setattr(sys.modules[__name__], name, attr)`, so future
lookups skip `__getattr__` and find the cached attr. A `mock.patch`
replaces the cached attr — subsequent calls hit the mock.

`__wrapped__` attribute: explicit dispatch wrappers for top-N hot-path
emit names that pytest fixtures patch heavily (sub-agent #1 list TBD —
based on grep frequency from Wave 0 Finding 3: top-10 = emit_generic,
emit_allow, emit_decision, emit_observe, emit_audit, emit_veto_triggered,
emit_and_read, emit_task_candidate_markers, emit_block, emit_debate_event).

## Stdlib-only allow-path

Imports allowed at module top-level:
- `sys` (already imported by Python)
- `typing` (already-imported by Python; the cost saving is on `inspect`
  which audit_emit imports transitively)
- `importlib.util` (cheap)

NO imports of: `inspect`, `audit_emit`, `_lib.canonical_json`, `_lib.audit_hmac`.

Deferred imports (lazy, inside `_load_real`):
- `_lib.audit_emit` (full module)
- Any transitive imports it pulls (`inspect`, `typing.get_type_hints`, etc.)
"""
from __future__ import annotations

import sys
from typing import Any, Optional


_REAL_MODULE: Optional[Any] = None


def _load_real() -> Any:
    """Import the full `_lib.audit_emit` on first call; subsequent calls
    return the cached module reference. Fail-open: ImportError surfaces
    via standard Python machinery (caller's try/except)."""
    global _REAL_MODULE
    if _REAL_MODULE is None:
        # Inline import — only triggers on first emit call.
        from _lib import audit_emit  # type: ignore[import-not-found]
        _REAL_MODULE = audit_emit
    return _REAL_MODULE


def emit_generic(action: str, **fields: Any) -> None:
    """Explicit hot-path wrapper for the 139 call sites that use
    `emit_generic(action, **fields)` directly. First call lazy-imports
    + replaces this function in the module namespace.
    """
    real = _load_real().emit_generic
    setattr(sys.modules[__name__], "emit_generic", real)
    real(action, **fields)


emit_generic.__wrapped__ = None  # type: ignore[attr-defined]
# ^ Placeholder for unittest.mock.patch compatibility marker. Tests can
# detect this is the dispatch shim version pre-first-call.


def __getattr__(name: str) -> Any:
    """PEP 562 module-level lazy proxy.

    Triggers ONLY when `name` is not in `globals()`. After first hit,
    the real attribute is cached in `globals()` via `setattr` so future
    accesses skip this function entirely.

    Returns the real attribute from `_lib.audit_emit` for:
    - emit_<action> names
    - _KNOWN_ACTIONS constant
    - _ATLAS_REGISTRY constant
    - iter_events generator

    Raises AttributeError for any private (`_audit_emit`, etc.) names
    or unknown attributes — preserves the public-API surface.
    """
    if not (
        name.startswith("emit_")
        or name in ("_KNOWN_ACTIONS", "_ATLAS_REGISTRY", "iter_events")
    ):
        raise AttributeError(
            f"module {__name__!r} has no attribute {name!r} "
            f"(private symbols not re-exposed)"
        )

    real = _load_real()
    try:
        attr = getattr(real, name)
    except AttributeError as e:
        raise AttributeError(
            f"_lib.audit_emit has no attribute {name!r} — possible "
            f"shim/real drift; rebuild dispatch module"
        ) from e

    setattr(sys.modules[__name__], name, attr)
    return attr


# ---------------------------------------------------------------------------
# AC E.6 sanity floor — shim import-time must stay <5ms
# ---------------------------------------------------------------------------
# This module imports only `sys` + `typing` at module top; both are
# pre-loaded by the Python interpreter on startup. The `from typing
# import Any, Optional` is a no-op cost at runtime (just a dict lookup).
#
# Verify via:
#   python3 -X importtime -c "import _lib.audit_emit_dispatch"
# Expected: shim self < 200µs; total cumulative < 5ms.
#
# Any future addition to top-level imports MUST be benchmarked against
# this budget.


# ---------------------------------------------------------------------------
# Kill-switch — CEO_AUDIT_EMIT_LAZY_IMPORT_DISABLED=1 reverts to eager
# ---------------------------------------------------------------------------
# When set, the module top-level eagerly imports the real audit_emit and
# re-exposes its entire public surface (replicates pre-Wave-E behavior).
# Use for incident response if the lazy proxy introduces unexpected
# behavior (e.g. mock.patch races).

import os  # noqa: E402 — guarded by kill-switch check below

if os.environ.get("CEO_AUDIT_EMIT_LAZY_IMPORT_DISABLED", "") == "1":
    _eager = _load_real()
    for _name in dir(_eager):
        if _name.startswith("emit_") or _name in (
            "_KNOWN_ACTIONS",
            "_ATLAS_REGISTRY",
            "iter_events",
        ):
            globals()[_name] = getattr(_eager, _name)
    del _eager
