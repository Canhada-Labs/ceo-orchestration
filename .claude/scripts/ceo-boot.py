#!/usr/bin/env python3
"""ceo-boot.py — PLAN-065 Phase 3 production session-boot autopilot.

Single command at session start that consolidates governance reads + state
digest + recommendations. Per PLAN-065 §4.3 acceptance:

- 15 Tier-S checks dispatched parallel via ThreadPoolExecutor (stdlib)
- Per-check timeout 500 ms; aggregate wall-clock budget 5 s
- ``--short`` defaults to cached mode (≤2 s budget; cache-hit ≤200 ms)
- ``--json`` emits machine-readable digest
- Idempotent (back-to-back identical mod timestamps + transient failures)
- Recommendations engine (rule-based; ≤5 items)
- Audit emit hasattr-guarded — works pre + post canonical ceremony

Stdlib only. Python 3.9+.

Run from repo root:

    python3 .claude/scripts/ceo-boot.py             # full digest
    python3 .claude/scripts/ceo-boot.py --short     # cached top-line
    python3 .claude/scripts/ceo-boot.py --json      # machine output
    python3 .claude/scripts/ceo-boot.py --bench     # bench harness

Slash command: ``/ceo-boot`` (see ``.claude/commands/ceo-boot.md``).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import resource
import subprocess
import sys
import time
import tracemalloc
import unicodedata
from concurrent.futures import (
    ThreadPoolExecutor,
    TimeoutError as FuturesTimeout,
    as_completed,
    wait as futures_wait,
)
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
import sys as _sys_rp
from pathlib import Path as _Path_rp
_HOOKS_RP = _Path_rp(__file__).resolve()
for _anc in _HOOKS_RP.parents:
    if (_anc / ".claude" / "hooks" / "_lib").is_dir():
        if str(_anc / ".claude" / "hooks") not in _sys_rp.path:
            _sys_rp.path.insert(0, str(_anc / ".claude" / "hooks"))
        break
from _lib import runtime_paths as _rp  # noqa: E402  # PLAN-182 W1 single resolver

REPO_ROOT = Path(__file__).resolve().parents[2]


# PLAN-087 Wave C.4 — module-level plan-glob cache.
# Populated lazily on first call to _get_plan_paths(); subsequent calls
# within the same /ceo-boot subprocess return the cached sorted list.
# Process-scoped (no TTL); each /ceo-boot invocation is a fresh subprocess
# so the cache cannot go stale within a single invocation.
_PLAN_GLOB_CACHE: Optional[List[Path]] = None




def check_governance_validate() -> Tuple[str, str, Any]:
    """PLAN-082 Codex Item A: dispatch fast-profile validator.

    Calls `validate-governance.sh --fast --json` (delegates to
    `validate_governance_fast.py`) with a 1.8 s timeout. Parses JSON
    output; `rc != 0` is the red truth signal (NOT `stdout.count("ERROR")`
    — Codex 6th-option catch: the full validator emits `FAIL:` in some
    sections without printing literal "ERROR", which underclassified
    failures as yellow).
    """
    script = REPO_ROOT / ".claude" / "scripts" / "validate-governance.sh"
    if not script.exists():
        return "yellow", "validate-governance missing", None
    try:
        proc = subprocess.run(
            ["bash", str(script), "--fast", "--json"],
            capture_output=True, text=True, timeout=1.8, cwd=str(REPO_ROOT),
        )
    except subprocess.TimeoutExpired:
        return "red", "validate timeout (fast)", None
    rc = proc.returncode
    try:
        payload = json.loads(proc.stdout) if proc.stdout else {}
    except (json.JSONDecodeError, ValueError):
        payload = {}
    errors = payload.get("errors", []) if isinstance(payload, dict) else []
    warnings = payload.get("warnings", []) if isinstance(payload, dict) else []
    n_err = len(errors) if isinstance(errors, list) else 0
    n_warn = len(warnings) if isinstance(warnings, list) else 0
    # rc != 0 is the red truth (Codex 6th-option catch).
    if rc != 0:
        status = "red"
        summary = f"fast fail: {n_err} error(s)"
    elif n_warn:
        status = "yellow"
        summary = f"fast pass, {n_warn} warn(s)"
    else:
        status = "green"
        summary = "fast pass"
    return status, summary, {"rc": rc, "errors": n_err, "warnings": n_warn, "profile": "fast"}

# Declarations live beside the reusable hook library so the installer carries
# them recursively. They execute in this facade dictionary: private symbols,
# mutable state, and monkeypatch seams retain their historical identity.
from _lib._ceo_boot_parts import install as _install_ceo_boot_parts  # noqa: E402

_install_ceo_boot_parts(globals())
del _install_ceo_boot_parts

# === PLAN-065 Phase 2 audit_emit wire ===
# `_emit_ceo_boot_emitted_safe` and `_emit_ceo_boot_check_skipped_safe` are
# real declarations in the ordered parts above. This surface marker belongs
# to the script entry point because the delivery guard checks it there.


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
