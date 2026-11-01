#!/usr/bin/env python3
"""PostToolUse Agent audit log — Python single-file hook with rotation.

Port of `.claude/scripts/audit-log.sh` to stdlib Python. Bash version
remains untouched until A.4 flips settings.json to the Python shim.

## Schema

Identical to AUDIT-LOG-SCHEMA.md with these additions:

- `hook_duration_ms` (integer) — wallclock duration of the hook itself,
  measured at end of processing. Enables `audit-query.py stats --latency`
  analysis in Sprint 3 without re-instrumenting the hooks.

PLAN-020 Phase 0 item 1 (audit-log v2.7 schema bump — ADDITIVE):

- `usage_metadata` (object|null) — Anthropic API usage_metadata
  passthrough. Keys: `cache_creation_input_tokens`,
  `cache_read_input_tokens`, `uncached_input_tokens`, `output_tokens`,
  `thinking_tokens`. Each is integer or null. Captured per spawn for
  cache-coverage analysis (PLAN-020 §6 sub-target measurement).
- `cache_coverage_bps` (int|null) — derived metric in integer
  basis-points (ratio × 10000, clamped [0, 10000]):
  `cache_read / (cache_read + cache_creation + uncached)`. Null if
  totals unavailable. PLAN-020 §6 acceptance: P50 +10pp vs Phase 0
  baseline. PLAN-118 WS-E (S181): replaced the legacy `cache_coverage`
  float — floats break the HMAC-covered payload (canonical_json
  no-float invariant). The derivation helper still returns the float
  ratio; the producer converts to bps before the entry dict.
- `rail` (string|null) — spawn dispatch rail: `"native"` |
  `"custom"` | null (legacy / unknown). Discriminator for ADR-050
  dual-rail A/B harness. PLAN-019 emitters (pre-PLAN-020) emit null;
  PLAN-020 Phase 1+ emitters set the value.

All three fields are ADDITIVE — older consumers ignore them safely.

PLAN-021 ADR-052 (audit-log v2.8 schema bump — ADDITIVE):

- `model` (string|null) — Claude model ID used for the spawn. Values
  are canonical Anthropic IDs of the CURRENT fleet (e.g.
  `"claude-fable-5"`, `"claude-opus-5"`, `"claude-sonnet-5"`,
  `"claude-haiku-4-5"`; N-1 ids like `"claude-opus-4-8"` remain valid
  in replay), or null if unknown. Captured from `tool_response.model`
  when Anthropic API
  emits it, else null. Enables forensic correlation: if a
  Sonnet-routed review misses a bug, the audit log proves which
  model made the decision.

Field is ADDITIVE — older consumers ignore; pre-v2.8 emitters emit
null.

PLAN-065 Phase 1 (audit-log v2.15 — extract_skill 3-path matrix):

- `extract_skill()` ports the validated 3-path logic from
  `.claude/scripts/extract-skill.py` (58 tests, ReDoS-hardened) inline
  into the hook so audit-log emit covers Format-A inline / Format-B
  reference / Format-C `## SKILL CONTENT` block fallback. Restores
  observability of `skill=<name>` post-ADR-082 mitigated dispatch +
  Format-B SKILL REFERENCE default flip. Pre-Phase 1 baseline: 24/24
  agent_spawn rows had `skill="unknown"` (100% loss). Target ≤10%
  unknown in 30d post-merge.

  Sec MF-7 hardening: NFKC normalize, NUL byte denied, length cap
  256 chars on captured group, path traversal denied (the captured
  group grammar excludes `/` `..` `\\`), regex bounded quantifiers
  `{0,255}` (no nested unbounded alternation — ReDoS-safe).

PLAN-079 (extract_skill Path D — canonical archetype mapping):

- Path D added to `extract_skill()` as a TAIL fallback (after Paths
  A/B/C miss). Maps the 5 canonical archetypes — `code-reviewer`,
  `security-engineer`, `qa-architect`, `performance-engineer`,
  `devops` — to their canonical skill names per ADR-051 (sub-agents
  load skills via `.claude/agents/<name>.md` reference, not inline).
  Closes the observability gap S87/S88 surfaced (20/26 unknown
  agent_spawn rows on canonical-archetype dispatches without
  inline SKILL CONTENT).

  Backwards compat: signature changed from `extract_skill(prompt)`
  to `extract_skill(prompt, subagent_type="")` — default arg
  preserves all single-arg callers. Frozen mapping constant
  `_ARCHETYPE_TO_SKILL` (no runtime I/O); drift-detector test
  (`test_audit_log_path_d.py`) asserts the table matches the
  "Loads <skill> skill via reference" phrase in each
  `.claude/agents/<archetype>.md` description frontmatter.

  Sec MF-7 defense-in-depth: `subagent_type` is normalized via
  `strip().lower()` (case-fold mirrors `check_agent_spawn.py:204`
  archetype-routing precedent), then validated POST-NORMALIZE
  against `_ARCHETYPE_NAME_RE` (`^[a-z][a-z0-9\\-]{0,63}$` with
  `.fullmatch`). A raw-length pre-bound (`len > 80`) caps
  hot-path allocation. Rejected silently: slash, dot-traversal,
  NUL, unicode, oversize, non-string. Uppercase is INTENTIONALLY
  case-folded (NOT rejected) — matches Agent-tool emitter
  flexibility for the routing layer.

## Rotation

NEW in Sprint 2: monthly rotation by size threshold.

Before writing, if `audit-log.jsonl` exists and its size > ROTATE_AT_BYTES
(default 10 MB), rename to `audit-log-YYYY-MM.jsonl` (current month) and
start a fresh file. If the monthly file already exists (second rotation
in the same month), append `-1`, `-2`, etc.

The rotation rename happens UNDER the lock so a concurrent writer can't
append to a file that's about to be moved.

## Safety properties

1. Fail-open: any exception writes a breadcrumb to `audit-log.errors`
   and exits 0. The user's session MUST NOT be blocked by this hook.
2. Silent on stdout: composable with the reminder hook.
3. Env-var overrides (`CEO_AUDIT_LOG_*`) for testability.
4. Redaction via `_lib.redact` (property-tested).
5. Locking via `_lib.filelock` (fcntl.flock).

## Decomposition candidates

This module has accreted ~7 responsibilities across PLAN-019..PLAN-079.
Tracked decomposition targets for PLAN-085+ readers (NO extraction in
PLAN-087 — doc-only surface; per `F-A-CR-D0016` P2 + PLAN-084 evolution
roadmap):

- **Path A — `extract_skill()` extraction.** Lines for the 3-path
  matrix (Format-A inline / Format-B reference / Format-C ``## SKILL
  CONTENT`` block) plus Path D canonical archetype map are a
  self-contained extraction target. Candidate destination:
  `_lib/skill_extract.py` (already exists as the standalone module
  `.claude/scripts/extract-skill.py` — the in-hook copy duplicates
  logic kept inline so audit-log emit covers the dispatch hot path
  without subprocess fork). Extraction would centralize the regex
  contract; trade-off is per-spawn import cost.
- **Path B — `usage_metadata` / `cache_coverage_bps` derivation.** The
  v2.7 / v2.8 schema bump logic (lines ~15-43 in this docstring) is
  arithmetic on `tool_response`. Candidate destination:
  `_lib/usage_metadata.py` (mirrors `_lib/tokens.py` adapter pattern).
- **Path C — HMAC chain integration.** The audit-chain HMAC writer
  is currently invoked from this hook's main path. Candidate
  destination: `_lib/audit_hmac.py` (already exists as the HMAC
  verifier — the writer-side wrapper would mirror the
  ``verify_chain()`` API). Extraction unblocks the two-writer
  asymmetry surfaced as PLAN-084 finding C.1.
- **Path D — Orchestrator split.** The PostToolUse dispatch logic
  (rotation + redaction + emit + HMAC + breadcrumb fallback) is the
  remaining "orchestrator" after Paths A/B/C peel off. Candidate
  destination: keep `audit_log.py` as a ~150-line thin shim that
  delegates to the four `_lib/*` modules.

Each Path is sized to one PLAN-08x phase; extraction order is
A → C → B → D (Path C unblocks the two-writer fix, so it lands
ahead of B/D).
"""

from __future__ import annotations

import getpass
import json
import os
import re
import stat
import sys
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

# Make `.claude/hooks/` importable so `_lib` resolves.
_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib import contract as _contract  # noqa: E402
from _lib import payload as _payload  # noqa: E402  (response_kind helper)
from _lib import redact as _redact  # noqa: E402
from _lib import tokens as _tokens  # noqa: E402  (PLAN-006 Phase 5b / ADR-016)
from _lib.adapters import claude as _claude_adapter  # noqa: E402
from _lib.filelock import FileLock, FileLockTimeout  # noqa: E402
try:
    from _lib import runtime_paths as _rp  # noqa: E402  # PLAN-182 W1 single resolver
except Exception:  # pragma: no cover — partial upgrade: hook stays FAIL-OPEN (rail r1 P1-4)
    _rp = None  # type: ignore[assignment]


def _rp_state_dir():
    """Resolver com fallback de partial-upgrade (arquivo novo ausente).

    Fail-open: o hook NUNCA crasha por falta do resolvedor; degrada ao
    comportamento legado com aviso em stderr.
    """
    if _rp is not None:
        return _rp.runtime_state_dir()
    import sys as _s
    _s.stderr.write("# hook: _lib/runtime_paths ausente — fallback legado (partial upgrade)\n")
    from pathlib import Path as _P
    import os as _o
    _h = _o.environ.get("HOME") or str(_P.home())
    return _P(_h) / ".claude" / "projects" / "ceo-orchestration"  # rp-allow: partial-upgrade-fallback


# -----------------------------------------------------------------------------
# Constants
# -----------------------------------------------------------------------------

# Default rotation threshold: 10 MB. Overridable via CEO_AUDIT_LOG_ROTATE_BYTES.
DEFAULT_ROTATE_AT_BYTES = 10 * 1024 * 1024

# PLAN-065 Phase 1 — Sec MF-7 input bounds.
# Cap inputs at 1 MiB to keep the regex engine in linear-time territory.
# Plans / prompts beyond this size are extreme outliers; rejecting them is
# preferred over feeding pathological input to the regex engine.
_MAX_INPUT_CHARS = 1024 * 1024  # 1 MiB hard cap
_MAX_INPUT_BYTES = _MAX_INPUT_CHARS

# Skill-name max length (PLAN-065 §4.1 fixture spec — 256-char cap).
_MAX_SKILL_NAME_CHARS = 256

# Allowed skill-name character class — ``[a-z0-9][a-z0-9\-]*`` anchored.
# Used as defense-in-depth re-validation post-extract.
_SKILL_NAME_CHARSET_RE = re.compile(r"^[a-z0-9][a-z0-9\-]*$")

# PLAN-065 Phase 1 — 3-path SKILL extraction matrix.
#
# Path A — Format-A inline. Line-anchored ``^SKILL: <name>$``. Bounded
# {0,255} quantifier on the captured group, no nested unbounded alternation
# (ReDoS-safe). Mirrors the validated grammar in extract-skill.py:_PATH_A_RE.
_SKILL_PATH_A_RE = re.compile(
    r"(?m)^SKILL:[ \t]+([a-z0-9][a-z0-9\-]{0,255})\s*$",
)

# Path B — Format-B reference (mitigated dispatch + SKILL REFERENCE default).
#   @.claude/skills/core/<name>/SKILL.md sha256=<64-hex>
#   @.claude/skills/frontend/<name>/SKILL.md sha256=<64-hex>
#   @.claude/skills/domains/<domain>/skills/<name>/SKILL.md sha256=<64-hex>
# Captured group is the skill <name> path-segment, not the domain.
_SKILL_PATH_B_RE = re.compile(
    r"(?m)^@\.claude/skills/"
    r"(?:core|frontend|domains/[a-z0-9][a-z0-9\-]{0,63}/skills)"
    r"/([a-z0-9][a-z0-9\-]{0,255})/SKILL\.md"
    r"\s+sha256=[0-9a-f]{64}\s*$",
)

# Path C — `## SKILL CONTENT` block fallback. Used when neither Format-A
# nor Format-B was emitted (legacy / third-party adapter surface). The block
# heading has a sibling `SKILL LOADED: <name>` annotation.
_SKILL_PATH_C_HEADER_RE = re.compile(
    r"(?m)^##[ \t]+SKILL[ \t]+CONTENT\b",
)
_SKILL_PATH_C_LOADED_RE = re.compile(
    r"(?m)^SKILL[ \t]+LOADED:[ \t]+([a-z0-9][a-z0-9\-]{0,255})\s*$",
)

# PLAN-079 Path D — canonical archetype subagent_type → skill mapping.
#
# Sub-agent dispatches via ``Agent({subagent_type:"<archetype>"})`` load
# their persona + skill via ``.claude/agents/<archetype>.md`` reference
# per ADR-051 (PLAN-020). When the spawn prompt does NOT carry an
# explicit Format-A/B/C SKILL envelope, Paths A-C all miss and the
# pre-PLAN-079 behavior recorded ``skill="unknown"``. This frozen map
# closes the observability gap by mapping the 5 canonical archetypes
# to their loaded skill name. Frozen baseline pattern (mirrors
# ``_FROZEN_BASELINE`` in tier_policy/_constants.py) — no runtime I/O
# against agent files; drift-detector test asserts the table matches
# the "Loads <skill> skill via reference" phrase in each
# ``.claude/agents/<archetype>.md`` description frontmatter.
_ARCHETYPE_TO_SKILL: Dict[str, str] = {
    "code-reviewer": "code-review-checklist",
    "security-engineer": "security-and-auth",
    "qa-architect": "testing-strategy",
    "performance-engineer": "performance-engineering",
    "devops": "devops-ci-cd",
    # PLAN-106 Wave B.2 (H3 fix) — additional archetypes recorded as
    # `unknown` in 24h rolling because Path D lookup missed them. The
    # canonical skill name on the right-hand side must match a real
    # `.claude/skills/**/<name>/SKILL.md`. If the file is absent at
    # adopter time the map still resolves the string; the downstream
    # consumer is `audit_log.py:extract_skill()` Path D tail which
    # records the string verbatim — no I/O.
    "identity-trust-architect": "identity-and-trust-architecture",
    "incident-commander": "incident-management",
    "llm-finops-architect": "llm-routing-and-finops",
    "threat-detection-engineer": "security-and-auth",
}

# Defense-in-depth charset for ``subagent_type`` AFTER `strip().lower()`
# normalize (untrusted spawn-payload field). Bounded {0,63} quantifier —
# no nested unbounded alternation (ReDoS-safe). Validated POST-NORMALIZE
# via `.fullmatch` — uppercase input is case-folded BEFORE this check
# (intentional, mirrors check_agent_spawn.py:204). Rejects (post-normalize):
# dot-traversal `..`, slashes, NUL, unicode, oversize.
_ARCHETYPE_NAME_RE = re.compile(r"^[a-z][a-z0-9\-]{0,63}$")

# Governance markers in the prompt
_PROFILE_RE = re.compile(r"^(## AGENT PROFILE|## PERSONA|PERSONA:)", re.MULTILINE)
_FILE_ASSIGNMENT_RE = re.compile(r"^## FILE ASSIGNMENT", re.MULTILINE)


# -----------------------------------------------------------------------------
# Path resolution
# -----------------------------------------------------------------------------



# Runtime declarations are split into installable, inspectable library files.
# They execute once in this facade dictionary so private names, mutable globals
# and monkeypatch seams retain the historical lookup behavior.
from pathlib import Path as _FacadePath

_PARTS = (
    "paths_skills", "entries_usage", "rotation_storage", "adapters_runtime",
)
_FACADE_DOC = __doc__

def _install_parts() -> None:
    """Execute ordered real source fragments in this module namespace."""
    namespace = globals()
    directory = _FacadePath(__file__).resolve().parent / "_lib" / "_audit_log_parts"
    for part_name in _PARTS:
        part_path = directory / (part_name + ".py")
        source = part_path.read_text(encoding="utf-8")
        exec(compile(source, str(part_path), "exec"), namespace, namespace)


_install_parts()
__doc__ = _FACADE_DOC
del _install_parts, _FacadePath, _FACADE_DOC
