"""PLAN-102 Wave C — per-class swarm enable gate runtime.

STAGED for ceremony Phase A1 copy to
`.claude/hooks/_lib/swarm_enable_gate.py`. The ceremony apply-patches.py
performs the copy with Owner-signed sentinel (approved.md.asc) covering
the canonical destination per ADR-010.

## Doctrine (P0 #5 fold)

ADR-133 §Decision §Part 1 §6 declares a 6-layer kill-switch chain. The
S139 / S141 PLAN-100 / PLAN-101 ships covered Layers 1+2 (master kill +
secondary kill) and Layers 5+6 (SIGTERM/SIGKILL + cgroups via existing
`kill_switch.py` + `_process_group.py`). PLAN-102 adds the RUNTIME
check primitive for Layers 3 + 4:

- Layer 3 — GPG sentinel at `.claude/data/swarm/<class>-enabled.md.asc`
  must exist AND carry a valid detached signature against
  `.claude/sentinel-signers.txt` allowlist (fail-CLOSED).
- Layer 4 — Env flag `CEO_SWARM_<CLASS_UPPER>_ENABLED == "1"` (EXACT
  match per S139 partial-match-non-interference doctrine).

`is_class_enabled(class_tier)` returns (True, "") only when BOTH gates
pass. Otherwise `(False, "<reason>")` with one of:

- `sentinel_absent` — `.asc` file missing
- `sentinel_bad_signature` — gpg/allowlist verification failed
- `env_flag_unset` — `CEO_SWARM_<CLASS>_ENABLED` not present
- `env_flag_not_1` — present but not EXACT "1"
- `stdlib_gpg_unavailable` — gpg binary missing
- `gate_disabled` — `CEO_SWARM_ENABLE_GATE_DISABLE=1` short-circuit

Stdlib only (gpg_verify is already a stdlib-wrapping helper). Python
>= 3.9.

## Coordinator integration

This module PLANTS the gate capability. Wiring into
`.claude/scripts/swarm/coordinator.py` (calling `is_class_enabled()`
at the dispatch entry) is a follow-up plan PLAN-102-FOLLOWUP per
PLAN-102 §6b. The current ship stages the gate module as opt-in
capability surface — staged-capability pattern (PLAN-104 persona-
demand ledger Phase 2 precedent + ADR-104-AMEND-1 staged-capability
contract).
"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple


_VALID_CLASSES = ("vibecoder", "CTO", "team")
_GATE_KILL_ENV = "CEO_SWARM_ENABLE_GATE_DISABLE"


def is_disabled() -> bool:
    """Hook-level kill-switch — `CEO_SWARM_ENABLE_GATE_DISABLE=1`
    short-circuits `is_class_enabled` to (False, "gate_disabled").
    Used for emergency operations or test isolation. EXACT match per
    S139 partial-match-non-interference doctrine."""
    return os.environ.get(_GATE_KILL_ENV, "") == "1"


def _sentinel_path(repo_root: Path, class_tier: str) -> Path:
    return repo_root / ".claude" / "data" / "swarm" / f"{class_tier}-enabled.md.asc"


def _sentinel_body_path(repo_root: Path, class_tier: str) -> Path:
    """Path to the (optional) body file the .asc detaches over.

    The repo doesn't yet ship a body convention. We adopt: the body is
    a single-line `<class>-enabled` next to the `.asc`. The Owner
    creates both files at per-class opt-in time; ceremony does NOT
    create them — Owner-physical only.
    """
    return repo_root / ".claude" / "data" / "swarm" / f"{class_tier}-enabled.md"


def _allowlist_path(repo_root: Path) -> Path:
    return repo_root / ".claude" / "sentinel-signers.txt"


def _repo_root() -> Path:
    """Resolve repo root from `CLAUDE_PROJECT_DIR` env or cwd fallback."""
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env)
    return Path(os.getcwd())


def is_class_enabled(class_tier: str) -> Tuple[bool, str]:
    """Return (enabled, reason).

    Returns (True, "") only when BOTH:
      1. GPG sentinel `.claude/data/swarm/<class>-enabled.md.asc`
         exists AND verifies against `.claude/sentinel-signers.txt`.
      2. Env `CEO_SWARM_<CLASS_UPPER>_ENABLED == "1"` (EXACT match).

    Both default-CLOSED; fail-CLOSED on any infra error (the gate is
    a SAFETY surface — flag-on means "Owner consented", absence of
    signal means "do NOT proceed"). See ADR-133 §Decision §Part 1 §6.
    """
    if is_disabled():
        return (False, "gate_disabled")

    if class_tier not in _VALID_CLASSES:
        # Unknown class never enabled.
        return (False, "env_flag_unset")

    # Layer 4 (env): EXACT match "1".
    env_key = f"CEO_SWARM_{class_tier.upper()}_ENABLED"
    raw = os.environ.get(env_key)
    if raw is None:
        return (False, "env_flag_unset")
    if raw != "1":
        return (False, "env_flag_not_1")

    # Layer 3 (sentinel): GPG verify against allowlist.
    repo = _repo_root()
    sentinel = _sentinel_path(repo, class_tier)
    body = _sentinel_body_path(repo, class_tier)
    if not sentinel.is_file():
        return (False, "sentinel_absent")
    if not body.is_file():
        # Body required for detached-sig verification; missing == absent
        return (False, "sentinel_absent")

    allowlist = _allowlist_path(repo)
    if not allowlist.is_file():
        return (False, "sentinel_bad_signature")

    try:
        # gpg_verify is the canonical helper (PLAN-045 Wave 1 P0-01/02).
        # Defer import so the module loads in test environments without
        # the full _lib package on sys.path; callers wire _HOOKS.
        from _lib.gpg_verify import verify_detached  # type: ignore[import-not-found]
    except ImportError:
        return (False, "stdlib_gpg_unavailable")

    try:
        ok, _fpr, _reason = verify_detached(
            signed_file=body,
            signature_file=sentinel,
            allowlist_path=allowlist,
        )
    except Exception:
        return (False, "sentinel_bad_signature")

    if not ok:
        return (False, "sentinel_bad_signature")

    return (True, "")
