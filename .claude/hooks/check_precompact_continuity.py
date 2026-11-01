#!/usr/bin/env python3
"""PLAN-135 W2 H1 (ADR-153 compaction-continuity) — PreCompact governance
snapshot.

Compaction is the OTHER way a session's protocol state dies — the
closeout-guard (S228) covers only Stop. When the Claude Code harness fires
``PreCompact`` (manual ``/compact`` or auto context-window threshold), this
hook snapshots, into the plan-scoped scratchpad, the governance state the
post-compaction transcript would otherwise forget:

  - ``plan_id`` — the PLAN-NNN currently scoped to the session (derived from
    the audit-log ``plan_transition`` events, NOT an env var — agent-spoofable;
    scratchpad_lib.resolve_plan_id doctrine);
  - ``execution_unit`` — the active execution-unit position (the first
    unchecked ``- [ ]`` checkbox in the current plan file, repo-relative path
    + line + sanitized label);
  - ``ceremony_flags`` — pending Owner-GPG ceremony breadcrumbs (executable
    ``finish-*.sh`` under ``staged/**`` / ``scripts/local/`` newer than the
    last git tag — the closeout-guard's signal, reused);
  - ``hmac_chain`` — a READ-ONLY breadcrumb of the audit HMAC-chain state
    (last-hmac hex PREFIX + chain-length counter) so a post-compaction
    integrity check has the pre-compaction anchor.

The matching ``PostCompact`` hook (``check_postcompact_reinject.py``) reads
this snapshot back and reinjects governance POINTERS (not the snapshot body)
via ``additionalContext``.

## PLAN-179 W1 US3 — session-scope fallback (the ADR-153 fires-proof cure)

The S309 fires-proof was NEGATIVE for the dominant path: ``resolve_plan_id``
needs a ``plan_transition`` event *from this same session*, and a real session
emits ~0 of those (2 events in 12.515 log lines), so every long session — the
only kind that ever compacts — snapshotted NOTHING. The write is no longer
skipped when the plan is unresolved: it goes to a SESSION-scoped store
(``scratchpad_lib.open_session_scratchpad``) and reports the new outcome
``written_session_scope``. Per emenda r1-C1 the session id comes ONLY from the
hook input — if the derivation would fall back to ``CLAUDE_SESSION_ID`` (env,
agent-spoofable — consensus M2) the fallback is REFUSED and the outcome stays
``scratchpad_unavailable``; the scope is recorded in the blob's own
``scope_kind`` field, never by overloading ``plan_id`` (the store's
plan-isolation invariant stays intact).

## Contract

- ADVISORY + fail-open (PLAN-091 S116 doctrine: parse errors / missing files /
  derivation failures / timeouts → stderr breadcrumb + emit ``{}``). NEVER
  blocks — a crashed snapshot must not stop a compaction.
- Time budget ``TIME_BUDGET_S`` (subprocess git capped; budget-blown → snapshot
  what we have, never noise).
- Emits ONE closed-enum ``compaction_continuity_snapshot`` audit event
  (registered in BOTH ``_KNOWN_ACTIONS`` and SPEC v2.43) carrying ONLY closed
  enums + counters: ``trigger`` (manual/auto/other), ``snapshot_outcome``
  (written/written_session_scope/scratchpad_unavailable/error/other),
  ``plan_id`` (PLAN-NNN or ``unknown``), ``chain_length`` (clamped int). The
  snapshot BODY (plan path text, checkbox label, ceremony paths, last-hmac
  hex) is written to the scratchpad — NEVER to the audit wire.
- Snapshot privacy: the write is plan- or session-scoped and secrets-redacted
  by ``state_store.set``; the audit emit carries no path/label text.
  **PLAN-179 amendment 8.3 (debate C9):** this claim used to be FALSE on the
  path actually taken — ``state_store.set`` redacts ``isinstance(value, str)``
  ONLY and this hook handed it ``payload.encode("utf-8")``, i.e. bytes, which
  the store trusts verbatim. The snapshot is now passed as a ``str`` so the
  store's own redactor runs. Same rule for the session-scoped write.
- Kill-switch: ``CEO_COMPACTION_CONTINUITY=0`` (shared with the PostCompact
  reinjection half). It also disables the session-store GC below — the switch
  turns the whole feature off, housekeeping included.
- PLAN-179 rail finding C: this hook is the PRODUCTION CALLER of
  ``scratchpad_lib.gc_orphan_session_stores`` (see ``_gc_session_stores``).
  The session-scope fallback creates one sqlite store per unresolved-plan
  session and row-TTL expiry cannot unlink a FILE, so without a caller the
  fallback accumulated files without bound. The sweep runs last, is bounded by
  the library's own per-run cap, respects the remaining time budget and is
  fail-open: no snapshot outcome depends on it.
- PLAN-179 W0 US2b progress guard: OBSERVE + NOTIFY only (see
  ``_progress_guard``); it emits ``context_pressure_observed`` and a stderr
  breadcrumb, and is DISABLED unless ``CEO_CONTEXT_PROGRESS_FLOOR_TOKENS`` is
  set. It cannot halt a compaction — PreCompact has no deny channel.
- Stdlib only, Python >= 3.9.

## Scratchpad key

``compaction_continuity`` (single JSON blob, <64 KiB; ``set`` overwrites). The
PostCompact half reads this exact key — in the plan scope first, then (PLAN-179
W1 US3) in the session scope.
"""
from __future__ import annotations

import contextlib
import fnmatch
import glob
import json
import os
import re
import stat as stat_mod
import subprocess
import sys
import time
from typing import Any, Dict, Iterator, List, Optional, Tuple

# Make the local `_lib` importable (matches the pattern of existing hooks).
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

TIME_BUDGET_S = 2.5
SCRATCHPAD_KEY = "compaction_continuity"
MAX_CEREMONY_FLAGS = 5
# Snapshot blob is capped well under the scratchpad 64 KiB per-key limit; the
# label/path clamps below keep it small regardless.
_LABEL_CLAMP = 160
_PATH_CLAMP = 200

# PLAN-179 W1 US3 / emenda r1-C2 — the session-scoped store is created per
# session id, so it accumulates files the plan-scoped one does not. Every
# session-scope write carries an EXPLICIT ttl so an orphaned snapshot expires
# on its own even before the file-level GC item ships. Hygiene value (7 days),
# not a decision-bearing number.
SESSION_SNAPSHOT_TTL_S = 7 * 24 * 3600

# PLAN-179 W0 US2b — progress-guard floor. The plan's own words: "requer o `F`
# medido acima; até lá o piso não tem valor honesto". So there is NO default
# here: absent/malformed env => the guard is a NO-OP. Once W0 measures F and T
# the operator sets the env var; a literal default would be a magic number
# shipped ahead of its measurement.
PROGRESS_FLOOR_ENV = "CEO_CONTEXT_PROGRESS_FLOOR_TOKENS"

# PLAN-179 W0 US2b / amendment 8.1 — WIRE CONTRACT for `context_pressure_observed`.
#
# INTEGRATION DEFECT CLOSED HERE (PLAN-179 W0/W1 cross-file pass): this hook
# used to compute a TOKEN-COUNT bucket (`used_tokens // 10000`, clamped 999)
# and emit it as `used_tokens_bucket=` alongside `floor_tokens=`. Neither field
# name exists in `_lib/audit_emit._CONTEXT_PRESSURE_OBSERVED_ALLOWLIST`, whose
# scrub is DENY-BY-DEFAULT — so both were dropped and every emit landed as a
# bare `used_bucket=0`. The wire field is `used_bucket` and it is a COARSE
# INTEGER PERCENT rung (share of the context window consumed), never a raw or
# token-derived count: a raw count is a transcript-size side channel, and a
# FLOAT under the HMAC chain discards the WHOLE event
# ([[feedback-float-in-hmac-field-drops-whole-event]]).
#
# The rung SET is DERIVED from audit_emit at call time, never restated here
# ([[feedback-closed-sets-must-be-derived-not-recalled]]): a literal copy would
# drift from the scrub branch that validates it and the event would coerce to
# the 0 sentinel forever, i.e. exactly the silent dead instrument this pass
# exists to remove.
_PRESSURE_RUNGS_ATTR = "_CONTEXT_PRESSURE_USED_BUCKETS_PCT"
# This producer's value inside audit_emit._CONTEXT_PRESSURE_EVENT_SOURCES.
_PRESSURE_EVENT_SOURCE = "precompact"
# audit_emit's documented "unrecognized / absent bucket" sentinel — deliberately
# OUTSIDE the percent enum so a consumer can always tell a real rung from a
# coerced one. Emitted when the hook input carries no context-window accounting.
_PRESSURE_BUCKET_UNKNOWN = 0
# `should_emit_context_pressure(used_bucket, state_dir)` keeps its edge-trigger
# marker under `<project>/.claude/state` (its own docstring names that path).
_PRESSURE_STATE_SUBPATH = (".claude", "state")

# Candidate shapes for the harness's context-window accounting. These MIRROR
# `.claude/scripts/statusline-ceo.py:context_pct()` — the one place in this repo
# that already reverse-engineered the harness payload — rather than being
# guessed here. Absent ⇒ no percent is invented
# ([[feedback-measurement-must-list-its-inputs]]).
_CONTEXT_WINDOW_KEYS = ("context_window", "context", "context_usage")
_CONTEXT_PCT_KEYS = ("used_percentage", "used_pct", "percent_used")
_CONTEXT_USED_KEYS = ("used_tokens", "input_tokens", "total_input_tokens")
_CONTEXT_SIZE_KEYS = ("context_window_size", "max_tokens", "size")

# The implementation is split into installable hooks/_lib modules. Loading the
# real source files into this facade preserves private names, global state and
# monkeypatch seams from the historical hook. Compatibility markers remain
# here for staged source selectors: written_session_scope, _sidecar_override_safe.
from _lib._precompact_parts import install as _install_precompact_parts  # noqa: E402

_install_precompact_parts(globals())
del _install_precompact_parts


if __name__ == "__main__":
    main()
