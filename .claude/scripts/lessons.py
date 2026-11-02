#!/usr/bin/env python3
"""Reflexion lessons — CRUD + relevance ranking.

Sprint 3 Item A. Implements Shinn et al. 2023 "Reflexion" pattern for
the ceo-orchestration framework. When a benchmark scenario fails, the
runner writes a lesson file. When an agent is spawned, the top-3 most
relevant lessons are injected into the prompt.

## Lesson storage

Each lesson is a JSON file under:

    $HOME/.claude/projects/<slug>/lessons/<lesson_id>.json

Lesson IDs are SHA-256 hashes of (scenario_id + created_at). Files are
human-readable JSON, one per lesson.

## Relevance ranking

    score = archetype_match × scope_overlap × recency_decay

- archetype_match: 1.0 if exact match, 0.3 if related, 0.0 otherwise
- scope_overlap: Jaccard similarity of lesson scope_tags vs task keywords
- recency_decay: exp(-days_since_lesson / 90) — 90-day e-folding time
  (half-life ≈ 62.4 days; PLAN-154 A14 docstring fix — the old
  "90-day half-life" wording overstated retention)

Top 3 by score, capped at 2K total tokens of injected content.

## PLAN-154 — gated learning loop (candidate lifecycle)

Distiller-proposed lesson CANDIDATES live in a separate namespace,
``<lessons_dir>/candidates/<lesson_id>.json``, so no legacy reader
(``list_lessons`` / ``get_top_k`` / ``build_index`` / prune / ranker)
can ever surface a non-approved candidate into a spawn prompt.

State machine (zero self-activation — constraint 5):

    add_candidate() ──> PENDING ──/lesson-review approve──> APPROVED
                          │  │
                          │  └──(TTL 30d)──> EXPIRED      (terminal)
                          └──(scan hit / scanner down /
                              tamper at approve)──> QUARANTINED (terminal)

- The promotion boundary is fail-CLOSED (A4): injection-scanner
  unavailable OR scan hit at ``add_candidate`` → QUARANTINED.
- Approval events in the HMAC chain carry
  ``sha256(trigger + "\\n" + advisory_text)`` (A6). Renderers verify
  the recomputed hash against the chain BEFORE rendering; the chain —
  not this mutable ``$HOME`` store — is the integrity anchor.
- Every time function takes an injectable ``now_fn`` (A9); the wall
  clock is only the default.
- Candidate vocabulary is bounded (A5): advisory_text ≤ 200 chars, no
  backticks, no newlines, no control chars; trigger/scope_tags are
  closed-character-class tokens.

## CLI

    python3 lessons.py write --scenario-id X --archetype Y --remember "..." --scope "tag1,tag2" --agent-response "..." --expected "..."
    python3 lessons.py top3 --archetype Y --keywords "tag1,tag2"
    python3 lessons.py list
    python3 lessons.py prune --older-than-days 180
    # PLAN-154 candidate lifecycle:
    python3 lessons.py add-candidate --trigger t --text "..." --scope "a,b"
    python3 lessons.py candidates [--status PENDING] [--json]
    python3 lessons.py approve <lesson_id>
    python3 lessons.py expire-sweep

## Constraints

- stdlib-only, Python >= 3.9
- Directory scan capped at 1000 files (debate consensus R-DEV3)
- All agent_response content passes through _lib.redact before storage
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

# Make _lib importable — lessons.py lives in .claude/scripts/,
# _lib lives in .claude/hooks/_lib/
_HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))
from _lib import runtime_paths as _rp  # noqa: E402  # PLAN-182 W1 single resolver

try:
    from _lib.redact import redact_secrets
except ImportError:
    # Graceful degradation — if _lib isn't available, no-op redaction
    def redact_secrets(text: str) -> str:  # type: ignore[misc]
        return text

try:
    from _lib.filelock import FileLock, FileLockTimeout
    _FILELOCK_AVAILABLE = True
except ImportError:
    _FILELOCK_AVAILABLE = False

try:
    from _lib.audit_emit import emit_lesson_write as _emit_lesson_write
    from _lib.audit_emit import emit_lesson_read as _emit_lesson_read
    _AUDIT_EMIT_AVAILABLE = True
except ImportError:
    _AUDIT_EMIT_AVAILABLE = False


# Maximum lesson files to scan per query (debate consensus R-DEV3)
_MAX_SCAN = 1000

# Maximum total tokens of injected lesson content
_MAX_INJECT_TOKENS = 2000

# Approximate chars per token for budget estimation
_CHARS_PER_TOKEN = 4

# ---------------------------------------------------------------------------
# PLAN-154 — candidate lifecycle constants (constraints 3/5, A5/A9)
# ---------------------------------------------------------------------------

# Candidate states. QUARANTINED and EXPIRED are TERMINAL — no transition
# ever leaves them (A4/A9). APPROVED is reached ONLY via approve_candidate
# (the /lesson-review human gate); nothing self-activates.
STATUS_PENDING = "PENDING"
STATUS_APPROVED = "APPROVED"
STATUS_QUARANTINED = "QUARANTINED"
STATUS_EXPIRED = "EXPIRED"
CANDIDATE_STATUSES = frozenset(
    {STATUS_PENDING, STATUS_APPROVED, STATUS_QUARANTINED, STATUS_EXPIRED}
)
TERMINAL_STATUSES = frozenset({STATUS_QUARANTINED, STATUS_EXPIRED})

# TTL for PENDING candidates (constraint 5). Expiry is STRICT: a
# candidate expires when age > TTL (exactly-at-TTL is NOT expired —
# golden-value boundary tests pin TTL±1s). The 7-day warning window is
# COUNT-ONLY data; no candidate text ever travels through it (A9).
CANDIDATE_TTL_DAYS = 30
CANDIDATE_WARN_DAYS = 7

# Bounded candidate vocabulary (A5). advisory_text: length-capped,
# backtick-free, newline-free, control-char-free. trigger + scope tags:
# closed-character-class tokens (injection-inert by construction).
from _lib._lessons_parts.config import CANDIDATE_TEXT_MAX_CHARS
_CANDIDATE_TOKEN_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,63}$")
_MAX_CANDIDATE_TAGS = 16

# Bounded HMAC-chain scan (A6 verify-before-render). The chain rotates at
# 10 MiB per file (audit_rotation.py); we scan the current file plus the
# most recent rotated siblings, newest first, under a total byte budget.
_CHAIN_SCAN_MAX_FILES = 4
_CHAIN_SCAN_MAX_BYTES = 48 * 1024 * 1024

# Audit actions emitted by the candidate lifecycle. Registration in
# audit_emit._KNOWN_ACTIONS is integrator-owned (4-file coupling);
# pre-registration, emit_generic() is a schema-compliant no-op.
_ACTION_CANDIDATE_WRITTEN = "lesson_candidate_written"
_ACTION_APPROVED = "lesson_approved"
_ACTION_QUARANTINED = "lesson_quarantined"
_ACTION_EXPIRED = "lesson_expired"
_ACTION_INTEGRITY_FLAG = "lesson_integrity_flag"


@dataclass
class Lesson:
    """A single reflexion lesson.

    PLAN-006 Phase 4 (ADR-015): extended with `hit_count` / `miss_count`
    for outcome tracking. Absence (or zero) = untested; populated via
    `record_outcome()` when a benchmark run applies this lesson.
    """

    lesson_id: str = ""
    created_at: str = ""  # ISO 8601
    scenario_id: str = ""
    archetype: str = ""
    remember_this: str = ""  # ≤ 200 chars
    scope_tags: List[str] = field(default_factory=list)
    agent_response: str = ""  # redacted before storage
    expected_response: str = ""
    # Outcome loop (ADR-015)
    hit_count: int = 0
    miss_count: int = 0
    last_outcome_at: str = ""  # ISO 8601 of most recent hit/miss

    def hit_rate(self) -> Optional[float]:
        """Ratio hits / (hits + misses). None when n < 3 (low signal)."""
        n = self.hit_count + self.miss_count
        if n < 3:
            return None
        return self.hit_count / n


# Bind declarations to this facade so runtime lookups honor monkeypatches.
from _lib._audit_emit_parts import install as _install_lessons_parts
_install_lessons_parts(globals(), ("storage_audit", "lessons", "candidates", "render", "cli"),
                       package="_lib._lessons_parts")
del _install_lessons_parts
if not __annotations__:
    del __annotations__

if __name__ == "__main__":
    sys.exit(main())
