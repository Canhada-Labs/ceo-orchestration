"""Shared stdlib foundation for the PLAN-122 optimizer package.

Every leaf module imports from here (and from ``types``) and from NOTHING else in
the package, so the leaves are parallel-author-safe. This module holds:

* the ``sys.path`` bootstrap to ``.claude/hooks`` (for best-effort ``_lib`` import),
* the ``os.environ``-only kill-switch reader (mirrors
  ``UserPromptSubmit._kill_switch_active``),
* the **defensive audit-emit shim** that probes ``_KNOWN_ACTIONS`` membership
  BEFORE calling ``emit_generic`` so that, before the canonical bundle registers
  the new actions, the optimizer is a silent no-op and never spams
  ``audit-log.errors`` (the load-bearing pre-activation defense),
* a bounded token estimator + clamped int-knob reader for the governors.

NO heavy work at import time. Nothing here raises into a caller.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Optional

# Values that mean "switch is OFF" (case-insensitive, stripped).
_OFF_VALUES = frozenset({"0", "false", "off", "no"})


def repo_hooks_lib(repo_root: Path) -> None:
    """Insert ``<repo_root>/.claude/hooks`` at ``sys.path[0]`` if absent.

    Lets ``from _lib import ...`` resolve when the optimizer runs outside pytest
    (the repo ``conftest.py`` already seeds this path for the test tree).
    Idempotent; never raises.
    """
    try:
        candidate = str((Path(repo_root) / ".claude" / "hooks").resolve())
        if candidate not in sys.path:
            sys.path.insert(0, candidate)
    except Exception:
        # Path resolution is best-effort; a failure here just means _lib stays
        # unavailable and safe_emit becomes a no-op. Never block the caller.
        return


def kill_switch_off(var: str, default: str = "1") -> bool:
    """True iff ``os.environ[var]`` (or ``default``) is an OFF value.

    ``os.environ`` ONLY — never reads a file (a prompt-injected sub-agent must
    not be able to flip a switch by writing an in-repo config). Mirrors
    ``UserPromptSubmit._kill_switch_active``.
    """
    try:
        return os.environ.get(var, default).strip().lower() in _OFF_VALUES
    except Exception:
        return False


def optimizer_enabled() -> bool:
    """True unless ``CEO_OPTIMIZER`` is OFF (group switch, default-ON)."""
    return not kill_switch_off("CEO_OPTIMIZER")


def estimate_tokens(text: str) -> int:
    """Bounded O(1) token-count heuristic: ``max(1, len(text)//4)``.

    No regex, no large allocation. Used by the width/budget/rate governors.
    """
    try:
        return max(1, len(text) // 4)
    except Exception:
        return 1


def env_int(var: str, default: int, lo: int, hi: int) -> int:
    """Read an OPTIMIZER int knob from ``os.environ``, clamped to ``[lo, hi]``.

    Returns ``default`` (itself clamped) on a missing or non-numeric value.
    OPTIMIZER-group config only — never a SAFETY switch.
    """
    try:
        raw = os.environ.get(var)
        value = int(raw) if raw is not None and raw.strip() else int(default)
    except (ValueError, TypeError):
        value = int(default)
    if lo > hi:
        lo, hi = hi, lo
    return max(lo, min(hi, value))


def _coerce_field(value: object) -> object:
    """Coerce an audit field to an HMAC-safe scalar.

    bool → int(0/1) (Python ``bool`` serialises as JSON ``true``/``false`` which
    differs from the int the schema expects); float → int(round) (a float nulls
    the HMAC and breaks the chain — PLAN-118 root-cause #2); int/str pass through;
    anything else → bounded str. The ``bool`` check MUST precede the ``int`` check
    because ``bool`` is a subclass of ``int``.
    """
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, float):
        return int(round(value))
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return value[:200]
    return str(value)[:200]


def safe_emit(action: str, repo_root: Optional[Path] = None, **fields: object) -> bool:
    """Defensive audit emit. Returns True iff an event was actually written.

    Best-effort ``from _lib import audit_emit``; if the import fails, return
    False. **GUARD:** if ``action`` is not in ``audit_emit._KNOWN_ACTIONS``,
    return False WITHOUT calling ``emit_generic`` — this is what keeps the
    optimizer silent (no ``audit-log.errors`` breadcrumbs) before the canonical
    bundle registers the new actions. All field values are coerced HMAC-safe
    (no floats, no bools) at this boundary. Never raises.
    """
    try:
        if repo_root is not None:
            repo_hooks_lib(repo_root)
        try:
            from _lib import audit_emit  # type: ignore[import]
        except Exception:
            return False
        known = getattr(audit_emit, "_KNOWN_ACTIONS", None)
        if not known or action not in known:
            # Pre-activation (bundle not yet applied) OR a typo: stay silent.
            return False
        safe_fields = {k: _coerce_field(v) for k, v in fields.items()}
        audit_emit.emit_generic(action, **safe_fields)
        return True
    except Exception:
        # An audit emit must NEVER block or crash the optimizer / the hook.
        return False
