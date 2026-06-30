"""Trust-root environment snapshot (PLAN-085 Wave E / ADR-040-AMEND-2 Layer 1).

ADR-116 entry #13 — kernel-tier HARD-DENY protects this module so the trust
root cannot be silently mutated by a sub-agent edit. ADR-040-AMEND-2 §Layer 1
specifies an at-import-time snapshot of CEO_* environment variables present
in the parent shell at process launch. Subsequent code paths that need to
verify "was this env var ALREADY set when the process started?" consult
``ORIGINAL_CEO_ENV`` rather than ``os.environ`` (which can be mutated by
in-process subprocess.run env= overrides, library calls, or test fixtures).

The snapshot is **read-only** and **process-scoped**. Reset on process
restart. NEVER export, NEVER persist, NEVER ship across spawn boundaries.

Mature 4-layer credential-block emergency-override provenance enforcement
(ADR-040-AMEND-2) builds on this primitive:

- **Layer 1** (this module): trust-root snapshot at import time
- **Layer 2** (spawn dispatcher): sanitize CEO_* from sub-agent prompt payload
- **Layer 3** (subprocess launchers): strip CEO_* from child env unless
  explicitly forwarded
- **Layer 4** (CI workflow lint): reject CI YAML that injects
  CEO_CREDENTIAL_BLOCK_EMERGENCY_OVERRIDE into job env

This module ships Layer 1 only. Layers 2-4 are wave-distributed targets
per ADR-040-AMEND-2 §scope.

Discipline: stdlib-only, Python >= 3.9, ``from __future__ annotations``.
"""

from __future__ import annotations

import os
from typing import Dict, FrozenSet, Optional


_TRUSTED_PREFIXES = ("CEO_",)
_DENY_KEYS: FrozenSet[str] = frozenset()


def _capture_snapshot() -> Dict[str, str]:
    """Return a copy of os.environ filtered to CEO_* keys at import time."""
    snap: Dict[str, str] = {}
    for key, value in os.environ.items():
        if key in _DENY_KEYS:
            continue
        for prefix in _TRUSTED_PREFIXES:
            if key.startswith(prefix):
                snap[key] = value
                break
    return snap


#: Read-only snapshot of trusted CEO_* env vars at process trust-anchor time.
#: Callers MUST NOT mutate. Use ``get_trusted(key, default)`` for typed access.
ORIGINAL_CEO_ENV: Dict[str, str] = _capture_snapshot()


def get_trusted(key: str, default: Optional[str] = None) -> Optional[str]:
    """Return the value of ``key`` from the import-time CEO_* snapshot.

    Returns ``default`` (None unless overridden) if the key was NOT present
    at process trust-anchor time. In-process mutations of ``os.environ``
    AFTER import are ignored — that is the whole point of this primitive.
    """
    return ORIGINAL_CEO_ENV.get(key, default)


def was_present_at_anchor(key: str) -> bool:
    """True iff ``key`` was set (any non-empty value) at process anchor time."""
    return bool(ORIGINAL_CEO_ENV.get(key))


__all__ = [
    "ORIGINAL_CEO_ENV",
    "get_trusted",
    "was_present_at_anchor",
]
