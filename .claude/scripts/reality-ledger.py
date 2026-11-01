#!/usr/bin/env python3
"""reality-ledger.py — Adaptive Execution Kernel claim-vs-evidence detector (advisory-only).

PLAN-071 §4.3 Phase 2 deliverable. Walks the repo for divergence between
documented claims and runtime/code evidence, emitting findings in markdown
(local triage) or JSON/JSONL (audit-log + GH issue body) format.

ADVISORY ONLY: this script never blocks the CEO. Output is consumed by
humans + weekly CI advisory. Exit code 0 = success (with or without
findings), 2 = detector internal error (Sec NTH #5).

Detectors v1.14.0 (5 active; #5 default_flip_orphan deferred to v1.15.0+):
  1. runtime_read_missing       — env-var documented but no AST-level read
  2. installable_claim_drift    — installable claim, but install at HEAD fails
  3. model_assignment_divergence — claimed model != observed-majority model
  4. enforcement_commit_unpopulated — ADR ACCEPTED but no enforcement_commit SHA
  6. audit_action_phantom       — emitted action missing in _KNOWN_ACTIONS

Exclusions (anti-self-referential, post Round 1 R-SEC3):
  All detectors exclude `task-route.py`, `reality-ledger.py`, and
  `owner-ceremony/archive/**` from grep targets.

Output rendering (R2 R-CR-R2-3 + Codex P1 #1):
  --format markdown      INCLUDES claim_source_path  (local triage only)
  --format json/jsonl    EXCLUDES claim_source_path; SHA-only (audit-safe)

Audit emission (deferred until KERNEL ceremony Phase 5 lands
`reality_ledger_finding` action in `audit_emit._KNOWN_ACTIONS`):
  hasattr-guarded best-effort emit; advisory-only fallback when unwired.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import sys
import time
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, FrozenSet, Iterable, List, Optional, Tuple

# ---------------------------------------------------------------------------
# _lib / hooks imports — composition, not reimplementation
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
_HOOKS_LIB = _REPO_ROOT / ".claude" / "hooks"

if str(_HOOKS_LIB) not in sys.path:
    sys.path.insert(0, str(_HOOKS_LIB))

try:
    from _lib.redact import redact_secrets  # noqa: F401  used in actual_evidence
    from _lib.secret_patterns import (
        _install_itimer_guard,
        _clear_itimer_guard,
        ScanBudgetExceeded,
    )
except ImportError as exc:
    sys.stderr.write(
        f"[reality-ledger] FATAL import error: {exc.__class__.__name__}: {exc}\n"
    )
    sys.exit(2)

# audit_emit is imported lazily / hasattr-guarded inside _try_emit_finding
# so that running the script in environments where the action is not yet
# registered (pre-Phase-5 KERNEL ceremony) still works as advisory-only.

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Domain declarations are bound to this module's globals, preserving callers'
# historical ability to replace helpers and constants on the facade.
from _lib._reality_ledger_parts import install as _install_parts

_install_parts(globals())

if __name__ == "__main__":
    sys.exit(main())
