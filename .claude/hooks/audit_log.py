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
  are canonical Anthropic IDs: `"claude-opus-4-8"`,
  `"claude-sonnet-4-6"`, `"claude-haiku-4-5-20251001"`, or null if
  unknown. Captured from `tool_response.model` when Anthropic API
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


def audit_paths() -> Dict[str, Path]:
    """Resolve the audit log paths from env vars with sensible defaults."""
    home = Path(os.environ.get("HOME") or str(Path.home()))
    default_dir = home / ".claude" / "projects" / "ceo-orchestration"

    audit_dir = Path(os.environ.get("CEO_AUDIT_LOG_DIR") or str(default_dir))
    audit_log = Path(
        os.environ.get("CEO_AUDIT_LOG_PATH") or str(audit_dir / "audit-log.jsonl")
    )
    audit_err = Path(
        os.environ.get("CEO_AUDIT_LOG_ERR") or str(audit_dir / "audit-log.errors")
    )
    audit_lock = Path(
        os.environ.get("CEO_AUDIT_LOG_LOCK")
        or str(audit_dir / "audit-log.lock")
    )
    return {
        "dir": audit_dir,
        "log": audit_log,
        "err": audit_err,
        "lock": audit_lock,
    }


def rotate_threshold() -> int:
    """Rotation threshold in bytes, overridable via env for tests."""
    raw = os.environ.get("CEO_AUDIT_LOG_ROTATE_BYTES")
    if raw:
        try:
            return int(raw)
        except ValueError:
            pass
    return DEFAULT_ROTATE_AT_BYTES


# -----------------------------------------------------------------------------
# Field extraction
# -----------------------------------------------------------------------------


def bucket_prompt_length(n: int) -> str:
    """Bucket a prompt length into the fixed histogram buckets."""
    if n < 256:
        return "<256"
    if n < 1024:
        return "<1024"
    if n < 4096:
        return "<4096"
    if n < 16384:
        return "<16384"
    if n < 65536:
        return "<65536"
    return ">=65536"


def _sanitize_prompt(prompt: str) -> Optional[str]:
    """PLAN-065 Phase 1 / Sec MF-7 — NFKC normalize + NUL-strip + length cap.

    Returns the safe text for regex scanning, or None if rejected. Never
    raises. Mirrors ``extract-skill.py._sanitize`` pre-regex hardening.

    Rejections:
    - non-string inputs (defense-in-depth)
    - empty / whitespace-only
    - over ``_MAX_INPUT_CHARS`` code points or ``_MAX_INPUT_BYTES`` UTF-8
    - NUL byte present (post-NFKC)
    """
    if not isinstance(prompt, str):
        return None
    if not prompt or not prompt.strip():
        return None
    if len(prompt) > _MAX_INPUT_CHARS:
        return None
    # NFKC normalize first — homoglyph defense (Cyrillic 'о' U+043E → 'o' folds
    # under NFKC so Cyrillic-only homoglyphs that LOOK like 'o' survive as
    # distinct code-points, then the validator's strict ASCII charset rejects).
    normalized = unicodedata.normalize("NFKC", prompt)
    if "\x00" in normalized:
        return None
    if len(normalized.encode("utf-8", errors="replace")) > _MAX_INPUT_BYTES:
        return None
    return normalized


def _validate_skill_name(name: str) -> bool:
    """Defense-in-depth: re-validate captured skill name post-extract.

    Even though each path's regex already bounds the captured group, we
    re-validate here so a future grammar drift cannot smuggle a
    pathological name out via a regex edge case.

    Path-traversal patterns are denied here: the captured-group grammars
    exclude ``/`` ``..`` ``\\`` already, but we add an explicit anchor.
    """
    if not name or len(name) > _MAX_SKILL_NAME_CHARS:
        return False
    if "/" in name or ".." in name or "\\" in name:
        return False
    if not _SKILL_NAME_CHARSET_RE.match(name):
        return False
    return True


def _path_d_lookup(subagent_type: str) -> str:
    """PLAN-079 Path D — resolve subagent_type to canonical skill name.

    Returns the mapped skill if subagent_type is one of the 5 canonical
    archetypes (``code-reviewer``, ``security-engineer``, ``qa-architect``,
    ``performance-engineer``, ``devops``); otherwise returns ``"unknown"``.

    Normalization: ``strip().lower()`` is applied to mirror the
    archetype-routing precedent in ``check_agent_spawn.py:204``
    (``_extract_archetype_from_payload``). Case-fold is intentional —
    Agent-tool emitters may pass mixed case for the same archetype.

    Defense-in-depth (Sec MF-7):
    - Non-string input rejected (``isinstance(subagent_type, str)``)
    - Raw input length capped at 80 chars BEFORE normalize to bound
      strip/lower allocation cost on the hot audit-hook path (Codex
      G23-04)
    - Post-normalize charset enforced via ``_ARCHETYPE_NAME_RE.fullmatch``
      (anchored both ends) — slash, dot-traversal, NUL, unicode rejected

    Never raises.
    """
    if not isinstance(subagent_type, str):
        return "unknown"
    # G23-04: bound raw length before allocating strip/lower copy.
    # 80 leaves headroom for whitespace + 64-char post-normalize cap.
    if len(subagent_type) > 80:
        return "unknown"
    name = subagent_type.strip().lower()
    if not _ARCHETYPE_NAME_RE.fullmatch(name):
        return "unknown"
    return _ARCHETYPE_TO_SKILL.get(name, "unknown")


def extract_skill(prompt: str, subagent_type: str = "") -> str:
    """Return the skill name extracted from a spawn prompt, or 'unknown'.

    PLAN-065 Phase 1 — 3-path matrix; PLAN-079 — +Path D archetype map.

    Order of precedence:

      A. Format-A inline ``^SKILL: <name>$`` (line-anchored)
      B. Format-B reference
         ``^@.claude/skills/<scope>/<name>/SKILL.md sha256=<64hex>$``
      C. Format-C ``## SKILL CONTENT`` block + ``SKILL LOADED: <name>`` line
      D. Path D (PLAN-079) — ``subagent_type`` ∈ canonical-5 archetypes
         maps to the skill loaded via ``.claude/agents/<name>.md`` per
         ADR-051. Tail fallback only — never overrides an explicit
         Path A/B/C envelope.

    Multi-format prompts: Path A wins (line-order preference per
    PLAN-065 spec). Path D fires only if Paths A/B/C miss AND
    ``subagent_type`` is provided + valid.

    Path D edge case (Codex gate #23 hardened):
    - Fires on TRULY EMPTY ``prompt`` (legitimate empty-body case)
    - Does NOT fire on ``_sanitize_prompt``-rejected prompt (G23-03)
      — rejected prompts may have contained a conflicting `SKILL:`
      envelope we failed to parse; preserving "unknown" surfaces the
      rejection signal in forensic logs
    - Does NOT fire on non-string ``prompt`` (G23-09) — None, False,
      0, list, dict all return "unknown" before reaching Path D

    Sanitization (Sec MF-7) runs once before any path regex on the
    prompt. The ``subagent_type`` input is independently validated
    against ``_ARCHETYPE_NAME_RE`` inside ``_path_d_lookup`` (post-
    `strip().lower()` normalize, with raw-length pre-bound). Never
    raises — returns ``"unknown"`` on any rejection.

    The legacy single-arg signature (``str -> str``) remains supported
    via the default ``subagent_type=""`` arg — pre-PLAN-079 callers
    continue to work unchanged.

    Path D firing rules (Codex gate #23 hardened):

    | prompt              | subagent_type    | result                  |
    |---------------------|------------------|-------------------------|
    | non-string          | any              | "unknown" (G23-09)      |
    | "" (empty)          | canonical-5      | mapped skill (Path D)   |
    | "" (empty)          | other / ""       | "unknown"               |
    | str, sanitize=None  | any              | "unknown" (G23-03)      |
    | str, Path A match   | any              | Path A name (precedence)|
    | str, Path B match   | any              | Path B name (precedence)|
    | str, Path C match   | any              | Path C name (precedence)|
    | str, A/B/C miss     | canonical-5      | mapped skill (Path D)   |
    | str, A/B/C miss     | other / ""       | "unknown"               |
    """
    # Codex G23-09: type-check prompt BEFORE the falsy-short-circuit
    # so non-string prompts (None, False, 0, [], {}) don't silently fall
    # through to Path D fallback via the `if not prompt` branch.
    if not isinstance(prompt, str):
        return "unknown"
    if not prompt:
        # Empty prompt is a legitimate case (archetype dispatch with no
        # user-visible body). Path D may resolve from subagent_type alone.
        if subagent_type:
            return _path_d_lookup(subagent_type)
        return "unknown"
    safe = _sanitize_prompt(prompt)
    if safe is None:
        # Codex G23-03: prompt was REJECTED by Sec MF-7 hardening
        # (oversize, NUL byte, whitespace-only). Do NOT fall back to
        # Path D — the rejected prompt may have contained a different
        # SKILL envelope we failed to parse. Returning the mapped
        # archetype skill here would silently override a conflicting
        # (but malformed) explicit claim. Returning "unknown" preserves
        # the rejection signal so downstream forensics see the parse
        # failure, not a synthesized skill identity.
        return "unknown"

    # Path A — Format-A inline (precedence wins on multi-format).
    m = _SKILL_PATH_A_RE.search(safe)
    if m:
        name = m.group(1)
        if _validate_skill_name(name):
            return name

    # Path B — Format-B reference.
    m = _SKILL_PATH_B_RE.search(safe)
    if m:
        name = m.group(1)
        if _validate_skill_name(name):
            return name

    # Path C — `## SKILL CONTENT` block fallback (legacy).
    if _SKILL_PATH_C_HEADER_RE.search(safe):
        m = _SKILL_PATH_C_LOADED_RE.search(safe)
        if m:
            name = m.group(1)
            if _validate_skill_name(name):
                return name

    # Path D — PLAN-079 canonical archetype → skill mapping (last resort).
    if subagent_type:
        return _path_d_lookup(subagent_type)

    return "unknown"


def has_profile(prompt: str) -> bool:
    """True if the spawn prompt contains an `## AGENT PROFILE` section (spawn discipline marker)."""
    if not prompt:
        return False
    return bool(_PROFILE_RE.search(prompt))


def has_file_assignment(prompt: str) -> bool:
    """True if the spawn prompt contains a `## FILE ASSIGNMENT` section (anti-collision marker)."""
    if not prompt:
        return False
    return bool(_FILE_ASSIGNMENT_RE.search(prompt))


def now_iso_utc() -> str:
    """ISO 8601 UTC timestamp with second precision (e.g. 2026-04-11T13:15:47Z)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def now_month_slug() -> str:
    """YYYY-MM for the current UTC month — used for rotated filenames."""
    return datetime.now(timezone.utc).strftime("%Y-%m")


# -----------------------------------------------------------------------------
# Entry builder
# -----------------------------------------------------------------------------


def build_entry(
    *,
    event: "_contract.NormalizedEvent | _payload.HookPayload",
    project_dir: str,
    hook_duration_ms: int,
) -> Optional[Dict[str, Any]]:
    """Construct a JSONL row from a NormalizedEvent (or legacy HookPayload).

    Accepts either type for backward compatibility with older tests.
    Returns None if the event indicates a non-Agent tool (defensive — the
    matcher should already filter to Agent).
    """
    tool_name = getattr(event, "tool_name", "")
    if tool_name and tool_name not in ("Agent", "unknown"):
        return None

    description = getattr(event, "description", "") or ""
    prompt = getattr(event, "prompt", "") or ""
    session_id = getattr(event, "session_id", "") or ""
    subagent_type = getattr(event, "subagent_type", "") or ""
    tool_response = getattr(event, "tool_response", {}) or {}

    desc_preview = _redact.redact_secrets(description)
    desc_hash = _redact.hash_description(description)
    # PLAN-079: pass subagent_type for Path D archetype-mapping fallback.
    skill = extract_skill(prompt, subagent_type)

    # PLAN-006 Phase 5b (ADR-016): extract token counts from tool_response.
    # Always emit the keys (even if None) so consumers can distinguish
    # "post-ADR-016 emitter with unknown shape" from "pre-ADR-016 emitter".
    tin, tout = _tokens.extract_tokens(tool_response)
    ttotal = _tokens.total_tokens(tool_response)

    # PLAN-020 Phase 0 item 1: capture Anthropic usage_metadata for cache
    # coverage analysis. Additive v2.7 fields. Null-safe for emitters that
    # don't provide usage_metadata (legacy + non-Anthropic adapters).
    usage_metadata = _extract_usage_metadata(tool_response)
    # PLAN-118 WS-E (S181): the derived ratio is a FLOAT, which
    # ``canonical_json.encode()`` forbids in HMAC-covered payloads
    # (``CanonicalJsonError`` → fail-open ``hmac:null`` → chain one-way-rule
    # break → whole-chain ``tamper``). Encode as integer basis-points
    # (ratio × 10000, clamped 0..10000) BEFORE it reaches the entry dict.
    # Mirrors the S164 ``hit_rate`` → ``hit_rate_bps`` class fix; closes the
    # last live float-in-HMAC leak (the agent_spawn observer path that the
    # S164 emit_* introspection guard never covered).
    cache_coverage = _compute_cache_coverage(usage_metadata)
    cache_coverage_bps = (
        max(0, min(10000, int(round(cache_coverage * 10000))))
        if cache_coverage is not None
        else None
    )

    # PLAN-020 Phase 1: dual-rail discriminator. Detect from prompt
    # structure (## SKILL REFERENCE = native rail; ## SKILL CONTENT =
    # custom inline rail) OR from subagent_type matching canonical-5.
    rail = _detect_rail(prompt, subagent_type)

    # PLAN-021 ADR-052: model discriminator. Captured from Anthropic
    # API response when present. Null-safe for non-Anthropic adapters.
    # PLAN-044 audit-v2 C3-P0-01 (Wave B): fall back to ADR-052
    # role-to-model policy when tool_response.model is null (default
    # behavior of Task tool response shape at v1.11.0).
    model = _extract_model(tool_response, subagent_type=subagent_type)

    # PLAN-044 audit-v2 C3-P0-08 (Wave B): archetype + dispatch_mode
    # fields. Audit-telemetry.py per-archetype rollups depend on these
    # being non-null. ADR-082 per-archetype dispatch claim was undone
    # at v1.11.0 because no emitter wrote them. Wave B closes the gap.
    archetype = subagent_type if (
        isinstance(subagent_type, str) and subagent_type
    ) else None
    dispatch_mode = _resolve_dispatch_mode(subagent_type or "", rail)

    # PLAN-080 Phase 1 (M2-C3 + M2-CDX-1 iter 2): capture dispatch_archetype_hint
    # from the IN-PROMPT marker emitted by inject-agent-context.sh:
    #   `<!-- ceo-dispatch-archetype-hint: <slug> -->`
    # The marker propagates cross-process via the recorded `prompt` payload —
    # env vars do NOT survive the inject-agent-context.sh subprocess → Agent
    # tool dispatch → audit hook subprocess chain (Codex iter 2 finding).
    #
    # Validated via the same NFKC + ≤64 char + charset `^[a-z][a-z0-9-]*$` +
    # control/JSON-meta rejection contract as `_lib.audit_emit._validate_dispatch_archetype_hint`.
    # On rejection (or marker absent): returns None (fail-open). The field is
    # always emitted in the audit row — null when no hint is set/validated,
    # validated string otherwise.
    dispatch_archetype_hint = _extract_dispatch_archetype_hint(prompt)

    entry: Dict[str, Any] = {
        "ts": now_iso_utc(),
        "action": "agent_spawn",
        "session_id": session_id,
        "project": project_dir,
        "tool": tool_name or "Agent",
        "subagent_type": subagent_type,
        "desc_preview": desc_preview,
        "desc_hash": desc_hash,
        "skill": skill,
        "has_profile": has_profile(prompt),
        "has_file_assignment": has_file_assignment(prompt),
        "prompt_len_bucket": bucket_prompt_length(len(prompt)),
        "response_kind": _payload.response_kind(tool_response),
        "hook_duration_ms": int(hook_duration_ms),
        # Tokens (ADR-016): optional nullable, always-present.
        "tokens_in": tin,
        "tokens_out": tout,
        "tokens_total": ttotal,
        # PLAN-020 v2.7 additions (ADDITIVE — older consumers ignore).
        "usage_metadata": usage_metadata,
        # PLAN-118 WS-E (S181): integer basis-points (ratio × 10000) — the
        # legacy float ``cache_coverage`` field is REMOVED (it caused
        # CanonicalJsonError + fail-open hmac:null on every real spawn).
        "cache_coverage_bps": cache_coverage_bps,
        "rail": rail,
        # PLAN-021 v2.8 addition (ADDITIVE — ADR-052 multi-model).
        "model": model,
        # PLAN-044 audit-v2 v2.14 additions (Wave B C3-P0-08).
        "archetype": archetype,
        "dispatch_mode": dispatch_mode,
        # PLAN-080 Phase 1 v2.24 addition (M2-C3 + M2-CDX-1) —
        # dispatch_archetype_hint captured pre-ADR-082-mitigation.
        # Validated via _lib.audit_emit redaction contract.
        # Always-present (null when env unset or validation rejected).
        "dispatch_archetype_hint": dispatch_archetype_hint,
    }
    return entry


# -----------------------------------------------------------------------------
# PLAN-020 v2.7 cache-header capture helpers (Phase 0 item 1)
# -----------------------------------------------------------------------------

# Canonical-5 archetypes that ship with native subagent files (ADR-050).
# Rail discrimination: archetype is "native" IFF its name matches AND
# subagent_type is non-empty. Else "custom" if classic spawn signal is
# present. Else null (legacy / unknown).
_CANONICAL_5 = frozenset({
    "code-reviewer",
    "security-engineer",
    "qa-architect",
    "performance-engineer",
    "devops",
})

# Native rail spawn-prompt sentinel (additive ADR-051; co-exists with
# the legacy "## SKILL CONTENT" inline sentinel).
_SKILL_REFERENCE_RE = re.compile(
    r"^##\s+SKILL\s+REFERENCE\s*$", re.MULTILINE
)
_SKILL_CONTENT_RE = re.compile(
    r"^##\s+SKILL\s+CONTENT\s*$", re.MULTILINE
)


def _extract_usage_metadata(tool_response: Any) -> Optional[Dict[str, Any]]:
    """Extract Anthropic usage_metadata from a tool_response payload.

    Returns a dict with `cache_creation_input_tokens`,
    `cache_read_input_tokens`, `uncached_input_tokens`, `output_tokens`,
    `thinking_tokens` — each int or None. Returns None if the payload
    has no `usage_metadata` field at all (legacy / non-Anthropic).

    Defensive: never raises; returns None on any unexpected shape.
    """
    if not isinstance(tool_response, dict):
        return None
    usage = tool_response.get("usage_metadata")
    if not isinstance(usage, dict):
        # Some emitters may put it under "usage" or in nested response.
        usage = tool_response.get("usage")
        if not isinstance(usage, dict):
            return None

    def _coerce_int(value: Any) -> Optional[int]:
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.isdigit():
            return int(value)
        return None

    return {
        "cache_creation_input_tokens": _coerce_int(
            usage.get("cache_creation_input_tokens")
        ),
        "cache_read_input_tokens": _coerce_int(
            usage.get("cache_read_input_tokens")
        ),
        "uncached_input_tokens": _coerce_int(usage.get("uncached_input_tokens")),
        "output_tokens": _coerce_int(usage.get("output_tokens")),
        "thinking_tokens": _coerce_int(usage.get("thinking_tokens")),
    }


def _compute_cache_coverage(
    usage_metadata: Optional[Dict[str, Any]],
) -> Optional[float]:
    """Derived metric: cache_read / (cache_read + cache_creation + uncached).

    Returns None if the inputs are missing or the denominator is zero
    (defensive against synthetic / mocked payloads).
    """
    if not usage_metadata:
        return None
    cache_read = usage_metadata.get("cache_read_input_tokens") or 0
    cache_creation = usage_metadata.get("cache_creation_input_tokens") or 0
    uncached = usage_metadata.get("uncached_input_tokens") or 0
    denom = cache_read + cache_creation + uncached
    if denom <= 0:
        return None
    return round(cache_read / denom, 4)


# PLAN-080 Phase 1 (M2-C3 + M2-CDX-1 iter 2) — in-prompt hint marker pattern.
# inject-agent-context.sh emits this marker once near the top of every spawn
# prompt; audit_log.py extracts the slug at PostToolUse audit time. The
# regex captures the slug into group 1 and validates the charset inline.
_DISPATCH_HINT_MARKER_RE = re.compile(
    r"<!--\s*ceo-dispatch-archetype-hint:\s*([a-z][a-z0-9-]{0,63})\s*-->",
    re.IGNORECASE,
)


def _extract_dispatch_archetype_hint(prompt: str) -> Optional[str]:
    """PLAN-080 Phase 1 (M2-C3 + M2-CDX-1 iter 2) — extract validated hint.

    Searches `prompt` for the in-prompt marker:
      `<!-- ceo-dispatch-archetype-hint: <slug> -->`

    Falls back to `CEO_DISPATCH_ARCHETYPE_HINT` env var ONLY if the marker
    is absent (advisory path; env vars do not reliably propagate across the
    /spawn subprocess → Agent tool dispatch → audit hook subprocess chain
    per Codex Phase 1 iter 2 finding).

    Validation contract (mirrors `_lib.audit_emit._validate_dispatch_archetype_hint`):
      1. NFKC normalize
      2. Length ≤ 64 chars post-NFKC
      3. Charset `^[a-z][a-z0-9-]*$` (lowercase prefix; hyphens + digits)
      4. Reject control bytes (0x00-0x1f, 0x7f-0x9f), null, JSON-meta `{}[]:",\\`

    On rejection: return None (fail-open per audit hook contract; never blocks).
    On marker absent + env unset: return None.
    On accept: return normalized lowercase slug.
    """
    raw: Optional[str] = None
    # Primary path: in-prompt marker
    if isinstance(prompt, str) and prompt:
        m = _DISPATCH_HINT_MARKER_RE.search(prompt)
        if m:
            raw = m.group(1)
    # Fallback path: env var (advisory; may be set by future direct callers)
    if not raw:
        raw = os.environ.get("CEO_DISPATCH_ARCHETYPE_HINT")
    if not raw:
        return None
    # Defensive try/except — must NEVER throw under fail-open contract.
    try:
        # NFKC normalize then lowercase (regex was case-insensitive)
        norm = unicodedata.normalize("NFKC", raw).lower()
        # Length cap (post-NFKC)
        if len(norm) > 64 or len(norm) == 0:
            return None
        # Charset: ^[a-z][a-z0-9-]*$
        if not re.match(r"^[a-z][a-z0-9-]*$", norm):
            return None
        # Defensive: reject if any control byte slipped through
        if any(ord(c) < 0x20 or 0x7f <= ord(c) <= 0x9f for c in norm):
            return None
        # Defensive: JSON-meta chars
        if any(c in '{}[]:,"\\' for c in norm):
            return None
        return norm
    except Exception:  # pragma: no cover (defensive — extraction never throws)
        return None


def _extract_model(
    tool_response: Any,
    subagent_type: Optional[str] = None,
) -> Optional[str]:
    """PLAN-021 ADR-052: extract Claude model ID from tool_response.

    Anthropic API responses include a `model` field (e.g. "claude-opus-4-8",
    "claude-sonnet-4-6", "claude-haiku-4-5-20251001"). Some adapters nest
    it under `response.model` or `content.model`. Returns the string if
    found, else falls back to ADR-052 role-to-model policy table when
    `subagent_type` is supplied; otherwise None.

    Canonical IDs (PLAN-021 ADR-052 §Role-to-model distribution):
      - claude-opus-4-8        → orchestrator + critical VETOs
      - claude-sonnet-4-6      → mid-complexity workers
      - claude-haiku-4-5-20251001 → high-frequency fan-out

    PLAN-044 audit-v2 C3-P0-01 fix (Wave B): the Task tool response
    shape from Claude Code's hook payload omits the `model` field on
    100% of agent_spawn events (verified at audit time: 199/199 events
    had `model: null`). Without an authoritative observation, the
    fallback uses the ADR-052 policy table — adopters reading the
    audit-log get a *policy-derived* model identity, not an
    *observation-derived* one. The two diverge only when an adopter
    overrides ADR-052 (then the audit-log over-reports the policy
    model rather than the actual model — known limitation; downstream
    cost reports re-resolve via subagent_type when present).
    """
    if isinstance(tool_response, dict):
        # Direct top-level (most Anthropic SDK shapes)
        model = tool_response.get("model")
        if isinstance(model, str) and model:
            return model
        # Nested under "response" (some adapter shapes)
        resp = tool_response.get("response")
        if isinstance(resp, dict):
            m = resp.get("model")
            if isinstance(m, str) and m:
                return m
        # Nested under "usage_metadata" sibling-content
        usage = tool_response.get("usage_metadata")
        if isinstance(usage, dict):
            m = usage.get("model")
            if isinstance(m, str) and m:
                return m

    # Wave B fallback — ADR-052 role-to-model policy table.
    if isinstance(subagent_type, str) and subagent_type:
        policy_model = _ADR_052_ROLE_TO_MODEL.get(subagent_type)
        if policy_model:
            return policy_model
    return None


# PLAN-044 audit-v2 C3-P0-01 — ADR-052 §Role-to-model distribution table.
# Used as fallback when tool_response.model is null (which happens on 100%
# of Task-dispatched spawns at v1.11.0). Pinned to canonical IDs from
# ADR-052; if an adopter overrides ADR-052 they should also override
# this table OR pre-populate tool_response.model upstream.
_ADR_052_ROLE_TO_MODEL: Dict[str, str] = {
    # Canonical-5 VETO archetypes — Opus floor per ADR-052 + ADR-080
    "code-reviewer": "claude-opus-4-8",
    "security-engineer": "claude-opus-4-8",
    "qa-architect": "claude-sonnet-4-6",
    "performance-engineer": "claude-sonnet-4-6",
    "devops": "claude-haiku-4-5-20251001",  # E5-F7: align to ADR-052 + devops.md
    # Mitigated rail — general-purpose dispatch inherits CEO model.
    # Default-CEO is Opus 4.8 unless CEO_MODEL_DOWNSHIFT is honored.
    "general-purpose": "claude-opus-4-8",
    # Probe / specialty archetypes
    "growth-engineer": "claude-sonnet-4-6",
    "billing-engineer": "claude-sonnet-4-6",
    "compliance-specialist": "claude-sonnet-4-6",
    "chaos-engineer": "claude-sonnet-4-6",
    "data-engineer": "claude-sonnet-4-6",
    "real-time-systems-engineer": "claude-sonnet-4-6",
    "refactoring-lead": "claude-sonnet-4-6",
    "vp-engineering": "claude-opus-4-8",
    "vp-product": "claude-sonnet-4-6",
    "vp-operations": "claude-sonnet-4-6",
    # PLAN-074 Wave 1c provenance — see docs/PLAN-086-adr-052-role-extension.md
    # 4 VETO-floor archetypes added per PLAN-086 Wave B (R-019 ROLE_TO_MODEL ext).
    # ADR-052 §Veto-floor expansion (lines 186-210) names these as VETO-floor;
    # llm-finops-architect carries Opus floor for cost-ceiling integrity (see
    # docs §2 §Why llm-finops-architect). ADR-052 bytes NOT mutated (anti-churn).
    "incident-commander": "claude-opus-4-8",
    "identity-trust-architect": "claude-opus-4-8",
    "threat-detection-engineer": "claude-opus-4-8",
    "llm-finops-architect": "claude-opus-4-8",
}


def _resolve_dispatch_mode(
    subagent_type: str,
    rail: Optional[str],
) -> Optional[str]:
    """PLAN-044 audit-v2 C3-P0-08 — Wave B: derive dispatch_mode field.

    Maps (subagent_type, rail) → "native" | "mitigated" per the
    PLAN-061 / ADR-082 dispatch policy:

      - canonical-5 native rail → "native" (full tool grant per
        ADR-052 floor; H4 anomaly does NOT apply because empirically
        only `code-reviewer` is reliable; PLAN-061 default-on routes
        the other 4 via mitigated).
      - any non-canonical archetype → "mitigated" (general-purpose
        with persona injected via `## SKILL CONTENT`).
      - rail=None or unknown → None (legacy / pre-PLAN-061).

    See ADR-082 §Routing decision and `inject-agent-context.sh` for
    the live override matrix (CEO_DISPATCHER_MODE,
    CEO_MITIGATION_DISABLE).
    """
    if not isinstance(subagent_type, str):
        return None
    # Canonical-5 native rail — only code-reviewer routes natively
    # by default per PLAN-061 / ADR-082. Other 4 are mitigated.
    if subagent_type == "code-reviewer" and rail == "native":
        return "native"
    if subagent_type in _CANONICAL_5 and rail == "custom":
        # Older inline ## SKILL CONTENT prompt — pre-PLAN-061 spawn.
        return "native_legacy"
    if rail is None:
        return None
    # Default mitigated rail for non-canonical-5 + non-cr canonicals
    # under PLAN-061 default-on.
    return "mitigated"


def _detect_rail(prompt: str, subagent_type: str) -> Optional[str]:
    """Detect spawn dispatch rail (native vs custom) from prompt + subagent.

    Heuristic order:
    1. If subagent_type matches a canonical-5 archetype name AND the
       prompt has `## SKILL REFERENCE` sentinel → "native".
    2. Else if prompt has `## SKILL CONTENT` (legacy inline) → "custom".
    3. Else if prompt has `## SKILL REFERENCE` only → "native"
       (subagent_type may be empty for some adapters).
    4. Else None (unknown / pre-PLAN-020 / non-spawn event).
    """
    if not isinstance(prompt, str):
        return None
    has_reference = bool(_SKILL_REFERENCE_RE.search(prompt))
    has_content = bool(_SKILL_CONTENT_RE.search(prompt))
    is_canonical = (
        isinstance(subagent_type, str) and subagent_type in _CANONICAL_5
    )

    if is_canonical and has_reference:
        return "native"
    if has_content:
        return "custom"
    if has_reference:
        return "native"
    return None


# -----------------------------------------------------------------------------
# Rotation
# -----------------------------------------------------------------------------


def rotate_if_needed(log_path: Path, threshold_bytes: int) -> Optional[Path]:
    """Rename log_path to a monthly rotated file if it exceeds the threshold.

    Must be called UNDER the lock so no concurrent writer can race.

    PLAN-045 Wave 2 P0-08: delegates to ``_lib.audit_rotation.rotate_if_needed``
    so both write paths (this ``append_entry`` + ``_lib.audit_emit._write_event``)
    share identical rotation semantics. Preserves the existing call
    signature for backwards compatibility.

    PLAN-044 audit-v2 C6-P0-02 fix (Wave B): on successful rotation,
    invoke ``audit_hmac.reset_chain_on_rotation()`` so the HMAC chain
    starts a fresh genesis on the new log file. Without this, rotated
    logs continue chain from the previous final hmac into the new
    file's genesis row, which `audit-verify-chain.py` cannot validate
    (genesis is by definition prev_hmac=GENESIS_PREV; a non-genesis
    prev_hmac after rotation looks like silent tamper). Pattern was
    already correct in ``_lib.audit_emit._write_event`` — Wave B brings
    ``audit_log.py`` to parity.

    Returns the rotated path if rotation happened, None otherwise.
    """
    try:
        from _lib.audit_rotation import rotate_if_needed as _shared_rotate
    except ImportError:
        # Defensive: if the shared primitive isn't available (partial
        # install), fall back to the inlined legacy implementation so
        # rotation still works in the classic path.
        rotated = _legacy_rotate_inline(log_path, threshold_bytes)
    else:
        rotated = _shared_rotate(log_path, threshold_bytes, now_month_slug())

    # PLAN-044 audit-v2 C6-P0-02 — reset the per-process HMAC chain
    # state so the next entry written to the fresh log file is a
    # GENESIS_PREV-rooted row. Best-effort: missing _lib.audit_hmac
    # is non-fatal (older installs); chain integrity tests will catch
    # any rotated row that violates the genesis rule.
    if rotated is not None:
        try:
            from _lib import audit_hmac as _audit_hmac
            if hasattr(_audit_hmac, "reset_chain_on_rotation"):
                _audit_hmac.reset_chain_on_rotation()
        except Exception:
            pass
    return rotated


def _legacy_rotate_inline(
    log_path: Path, threshold_bytes: int
) -> Optional[Path]:
    """Fallback rotation for the rare case ``_lib.audit_rotation`` is missing.

    Kept in-line so a half-installed framework still rotates. Mirrors
    the behavior of the shared primitive byte-for-byte.
    """
    try:
        if not log_path.is_file():
            return None
        size = log_path.stat().st_size
        if size <= threshold_bytes:
            return None
    except OSError:
        return None

    month = now_month_slug()
    base = log_path.parent / f"{log_path.stem}-{month}.jsonl"
    candidate = base
    counter = 1
    while candidate.exists():
        candidate = log_path.parent / f"{log_path.stem}-{month}-{counter}.jsonl"
        counter += 1
        if counter > 1000:
            return None

    try:
        os.replace(str(log_path), str(candidate))
    except OSError:
        return None
    return candidate


# -----------------------------------------------------------------------------
# Error breadcrumb
# -----------------------------------------------------------------------------


def write_breadcrumb(err_path: Path, message: str) -> None:
    """Best-effort write to the errors log. Never raises."""
    try:
        err_path.parent.mkdir(parents=True, exist_ok=True)
        ts = now_iso_utc()
        with open(err_path, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] {message}\n")
    except OSError:
        # Last-resort: stderr
        try:
            sys.stderr.write(f"[audit-log] breadcrumb write failed: {message}\n")
        except Exception:  # pragma: no cover
            pass


# -----------------------------------------------------------------------------
# PLAN-045 F-01-06 — symlink + ownership defense
# -----------------------------------------------------------------------------


def _is_safe_audit_path(
    path: Path, expected_uid: int
) -> Tuple[bool, str]:
    """Check audit path for symlink + ownership safety.

    Returns ``(True, "")`` if safe (nonexistent OR real file/dir owned
    by ``expected_uid``). Returns ``(False, reason)`` if unsafe
    (symlink OR owner mismatch).

    Uses ``os.lstat`` (not ``stat``) so symlinks themselves are
    inspected rather than their targets. Never raises.

    ## Threat model

    1. **Symlink redirection.** An attacker with write access to
       ``$HOME/.claude/projects/`` creates
       ``ceo-orchestration -> /tmp/evil``. Every append goes to
       attacker-controlled path, defeats tamper-evident audit trail.
    2. **UID squatting.** Another user's process creates the audit
       directory. Hook runs as current user → fails to open for
       append (EACCES) OR leaks sensitive data into foreign-owned
       file if perms are too permissive.

    Both are refused before any write. The caller logs a breadcrumb
    to the /tmp fallback path and returns silently (fail-open on
    session; forensic trail preserved).
    """
    try:
        st = path.lstat()
    except FileNotFoundError:
        # Nonexistent is safe — the normal first-write path.
        return (True, "")
    except OSError as e:
        return (False, f"lstat_error:{e.__class__.__name__}")
    if stat.S_ISLNK(st.st_mode):
        return (False, "symlink_rejected")
    if st.st_uid != expected_uid:
        return (
            False,
            f"uid_mismatch:owner={st.st_uid} proc={expected_uid}",
        )
    return (True, "")


def _fallback_security_breadcrumb(message: str) -> None:
    """Breadcrumb to ``/tmp`` fallback when primary audit dir is unsafe.

    Mirrors ``_lib.audit_emit._fallback_log_path`` pattern. Never
    raises. Writes under the current user's namespaced filename so
    multi-user systems don't clobber each other.
    """
    try:
        try:
            user = getpass.getuser() or "unknown"
        except Exception:
            user = os.environ.get("USER") or "unknown"
        user = "".join(
            c for c in user if c.isalnum() or c in ("-", "_", ".")
        )
        fallback = Path("/tmp") / f"ceo-audit-fallback-{user}.log"
        ts = now_iso_utc()
        with open(fallback, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] audit-log security: {message}\n")
    except Exception:
        pass


# -----------------------------------------------------------------------------
# Append entry under lock
# -----------------------------------------------------------------------------


def append_entry(
    entry: Dict[str, Any],
    *,
    paths: Dict[str, Path],
    threshold_bytes: int,
) -> None:
    """Append a single JSONL line under the lock, rotating if needed.

    Any failure is logged to the errors breadcrumb and swallowed (fail-open).

    PLAN-045 F-01-06: pre-write symlink + ownership check on audit dir
    and audit log file. On violation, breadcrumb to /tmp fallback +
    return silently (fail-open on session; entry dropped but forensic
    trail preserved via fallback + upstream audit_emit).
    """
    # F-01-06 symlink + uid defense BEFORE any mkdir/write.
    # Rationale: an attacker who plants a symlink in the audit dir can
    # redirect writes. Ownership mismatch indicates another user's
    # process created the path. Both warrant refusal + breadcrumb.
    expected_uid = os.geteuid()
    ok, reason = _is_safe_audit_path(paths["dir"], expected_uid)
    if not ok:
        _fallback_security_breadcrumb(
            f"audit dir unsafe: {paths['dir']} ({reason})"
        )
        return
    ok, reason = _is_safe_audit_path(paths["log"], expected_uid)
    if not ok:
        _fallback_security_breadcrumb(
            f"audit log unsafe: {paths['log']} ({reason})"
        )
        return
    # Ensure dir exists with restrictive perms
    # PLAN-024 F-sec-001 P1 fix: mkdir(mode=0o700) closes TOCTOU micro-window
    # between mkdir() and os.chmod() where same-UID attacker could win a race.
    try:
        paths["dir"].mkdir(parents=True, exist_ok=True, mode=0o700)
        # Belt-and-braces: retighten in case dir pre-existed with looser perms
        try:
            os.chmod(paths["dir"], 0o700)
        except OSError:
            pass
    except OSError as e:
        write_breadcrumb(paths["err"], f"cannot create audit dir: {e}")
        return

    # PLAN-085 Wave B.3 — inline HMAC computation closes the two-writer
    # chain gap (F-C1-001 / T0-line-168 transition_violation root cause).
    # 100% of agent_spawn events now carry hmac field per ADR-055.
    # Reuses _lib/audit_hmac primitives; fail-OPEN per CLAUDE.md §5.
    entry.setdefault("hmac", None)
    entry.setdefault("hmac_error", None)
    _b3_hmac_digest_bytes = None
    try:
        from _lib import audit_hmac as _audit_hmac
        if not _audit_hmac.is_disabled():
            _b3_key = _audit_hmac.get_or_create_key()
            _b3_prev = _audit_hmac.read_prev_hmac()
            _b3_entry_sans = {
                k: v for k, v in entry.items()
                if k not in ("hmac", "hmac_error")
            }
            _b3_hmac_digest_bytes = _audit_hmac.compute_entry_hmac(
                _b3_key, _b3_prev, _b3_entry_sans
            )
            entry["hmac"] = _audit_hmac.hex_digest(_b3_hmac_digest_bytes)
    except Exception as _b3_he:
        entry["hmac"] = None
        entry["hmac_error"] = type(_b3_he).__name__

    line = json.dumps(entry, ensure_ascii=False, separators=(",", ":"))

    try:
        with FileLock(paths["lock"], timeout=2.5):
            # Rotate inside the lock so writers can't race past a rename
            rotate_if_needed(paths["log"], threshold_bytes)
            try:
                # PLAN-024 F-sec-002 P1 fix: os.open with mode=0o600 sets perms
                # at create-time, closing the default-umask window between
                # open() and os.chmod().
                fd = os.open(
                    paths["log"],
                    os.O_WRONLY | os.O_CREAT | os.O_APPEND,
                    0o600,
                )
                with os.fdopen(fd, "a", encoding="utf-8") as f:
                    f.write(line + "\n")
                    # PLAN-025 F-obs-002: flush + fsync so the append survives
                    # process/OS crash. Audit is source-of-truth for governance;
                    # silent loss after write() but before OS flush = forensic gap.
                    # Cost: one syscall per spawn (~200us). Tolerable vs the
                    # governance invariant "every spawn is recorded".
                    f.flush()
                    try:
                        os.fsync(f.fileno())
                    except (OSError, AttributeError):
                        # AttributeError on platforms without fsync; OSError on
                        # read-only fds or closed streams. Both acceptable — the
                        # write already succeeded; fsync is best-effort durability.
                        pass
                # Belt-and-braces: retighten in case file pre-existed looser
                try:
                    os.chmod(paths["log"], 0o600)
                except OSError:
                    pass
                # PLAN-085 Wave B.3 — update last-hmac sidecar within lock
                # so the next writer reads the correct prev_hmac. Best-effort.
                if _b3_hmac_digest_bytes is not None:
                    try:
                        from _lib import audit_hmac as _audit_hmac_tail
                        _audit_hmac_tail.write_last_hmac(_b3_hmac_digest_bytes)
                    except Exception:
                        pass
            except OSError as e:
                write_breadcrumb(paths["err"], f"append failed: {e}  line={line[:200]}")
    except FileLockTimeout:
        write_breadcrumb(
            paths["err"],
            f"lock timeout (stale?)  would-log={line[:200]}",
        )
    except Exception as e:  # pragma: no cover
        write_breadcrumb(paths["err"], f"unexpected error: {e}")


# -----------------------------------------------------------------------------
# PLAN-155 Wave 4 — Codex host-wire audit-chain path (SENT-CX-B / ADR-161)
# -----------------------------------------------------------------------------
#
# Under OpenAI Codex (CEO_HOOK_ADAPTER=codex) the same audit_log.py hook is
# registered on the PostToolUse `*` matcher (templates/codex/hooks.json) and,
# via the headless `scripts/codex-exec-wrapper.sh`, is fed synthesized
# SessionStart/Stop bracket envelopes. The codex path reads the codex host
# wire through the codex adapter and appends metadata-only records to the SAME
# HMAC chain via `_lib.audit_emit` (the single-writer emitter that verify_chain
# validates). Two NEW registered actions keep the per-tool append and the
# turn-level backstop COUNTABLE separately (PLAN-155 Wave 4-A / Wave 4-B):
#
#   PostToolUse (any tool)  -> emit_codex_tool_recorded   (per-tool append, A)
#   Stop / SubagentStop     -> emit_codex_turn_ended      (turn backstop, B)
#   SessionStart            -> emit_session_start          (boot bracket; only
#                              reached via the wrapper — production codex
#                              routes SessionStart to SessionStart.py, so there
#                              is no double-count)
#
# The claude (default) path below is UNCHANGED and byte-identical when
# CEO_HOOK_ADAPTER is unset/`claude`. Completeness residual (named, ADR-161 +
# degradation page): partial shell interception means a per-tool row may be
# absent — absence is not evidence of absence of activity. verify_chain() and
# the HMAC chain shape are untouched; this path only appends.

# Closed tool-name enum mirror of _lib.audit_emit._CODEX_TOOL_RECORDED_TOOL_NAME_ENUM.
# The codex adapter has already aliased apply_patch -> Write/Edit and
# spawn_agent -> Task before we see the event; here we only fold mcp__* down to
# `mcp_other` (MF-SEC-1) and leave the emitter to coerce any residual miss to
# `other`.
def _codex_tool_enum(tool_name: str) -> str:
    """Map a normalized codex tool name to the closed audit enum. Never raises."""
    if not isinstance(tool_name, str) or not tool_name:
        return "other"
    if tool_name.startswith("mcp__"):
        return "mcp_other"
    return tool_name


def _codex_audit_main(t0: float) -> int:
    """Codex host-wire audit append (PLAN-155 Wave 4). Exits 0 on every path.

    Reads the codex host envelope via the codex adapter and appends the
    matching metadata-only action to the shared HMAC chain through
    `_lib.audit_emit`. Fail-open per SPEC/v1 §4 — the audit hook is
    observability, not an enforcement gate, so an unresolved adapter / parse
    error / import failure breadcrumbs and returns 0 (the completeness bound is
    already the named residual; a security matcher would fail CLOSED instead,
    but this is not one).
    """
    try:
        from _lib.adapters import codex as _codex_adapter
        from _lib import audit_emit as _audit_emit
    except Exception as e:  # pragma: no cover — infrastructure import failure
        try:
            write_breadcrumb(
                audit_paths()["err"],
                f"codex audit import failed (fail-open): {type(e).__name__}",
            )
        except Exception:
            pass
        return 0

    try:
        event = _codex_adapter.read_post_event()
    except Exception as e:  # pragma: no cover — adapter never raises by contract
        write_breadcrumb(
            audit_paths()["err"],
            f"codex read_post_event raised (fail-open): {type(e).__name__}",
        )
        return 0

    if getattr(event, "parse_error", None):
        write_breadcrumb(
            audit_paths()["err"],
            f"codex stdin parse error: {event.parse_error}",
        )
        return 0

    # The codex wire's event name WINS over the phase arg (host adapter sets
    # NormalizedEvent.phase = hook_event_name). raw_payload carries the raw
    # codex scalars (stop_hook_active, etc.).
    hook_event = str(getattr(event, "phase", "") or "")
    raw_payload = getattr(event, "raw_payload", {}) or {}
    session_id = str(getattr(event, "session_id", "") or "")
    project_dir = str(getattr(event, "project", "") or "") or (
        os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    )

    try:
        if hook_event == "PostToolUse":
            tool_enum = _codex_tool_enum(str(getattr(event, "tool_name", "") or ""))
            _audit_emit.emit_codex_tool_recorded(
                session_id=session_id,
                tool_name_enum=tool_enum,
                hook_event_name="PostToolUse",
                project=project_dir,
            )
        elif hook_event in ("Stop", "SubagentStop"):
            # source: derive from the event, unless the headless wrapper
            # overrode it (CEO_CODEX_TURN_SOURCE) to mark a wrapper bracket.
            derived = "subagent_stop" if hook_event == "SubagentStop" else "stop"
            source = os.environ.get("CEO_CODEX_TURN_SOURCE") or derived
            stop_active = bool(raw_payload.get("stop_hook_active"))
            _audit_emit.emit_codex_turn_ended(
                session_id=session_id,
                source=source,
                stop_hook_active=stop_active,
                project=project_dir,
            )
        elif hook_event == "SessionStart":
            # Boot bracket — only reached when the wrapper pipes a SessionStart
            # envelope here (production routes SessionStart -> SessionStart.py).
            emit_ss = getattr(_audit_emit, "emit_session_start", None)
            if emit_ss is not None:
                emit_ss(session_id=session_id, project=project_dir)
        # else: UserPromptSubmit / SubagentStart / PreToolUse are not this
        # hook's job under codex — return 0 (no append).
    except Exception as e:  # pragma: no cover — emit is fail-open by contract
        write_breadcrumb(
            audit_paths()["err"],
            f"codex audit emit failed (fail-open): {type(e).__name__}",
        )
    return 0


def _grok_tool_enum(tool_name: str) -> str:
    """Map a normalized grok tool name to the closed audit enum. Never raises.

    The grok adapter has already aliased run_terminal_command -> Bash,
    search_replace -> Edit, spawn_subagent -> Task, etc. before we see the
    event; here we only fold mcp__* down to `mcp_other` (MF-SEC-1) and leave
    the emitter to coerce any residual miss to `other`.
    """
    if not isinstance(tool_name, str) or not tool_name:
        return "other"
    if tool_name.startswith("mcp__"):
        return "mcp_other"
    return tool_name


def _grok_audit_main(t0: float) -> int:
    """Grok host-wire audit append (PLAN-156 Wave 4). Exits 0 on every path.

    Mirror of `_codex_audit_main`: reads the grok host envelope via the grok
    adapter and appends the matching metadata-only action to the shared HMAC
    chain through `_lib.audit_emit`. Fail-open per SPEC/v1 §4 — the audit hook
    is observability, not enforcement, so an unresolved adapter / parse error
    / import failure breadcrumbs and returns 0.

    Grok specifics: PostToolUse is passive (a deny cannot block), but the
    append still lands. SessionEnd is unreliable in headless runs, so
    turn-ended accounting hangs off Stop / SubagentStop (completeness caveat,
    ADR-162).
    """
    try:
        from _lib.adapters import grok as _grok_adapter
        from _lib import audit_emit as _audit_emit
    except Exception as e:  # pragma: no cover — infrastructure import failure
        try:
            write_breadcrumb(
                audit_paths()["err"],
                f"grok audit import failed (fail-open): {type(e).__name__}",
            )
        except Exception:
            pass
        return 0

    try:
        event = _grok_adapter.read_post_event()
    except Exception as e:  # pragma: no cover — adapter never raises by contract
        write_breadcrumb(
            audit_paths()["err"],
            f"grok read_post_event raised (fail-open): {type(e).__name__}",
        )
        return 0

    if getattr(event, "parse_error", None):
        write_breadcrumb(
            audit_paths()["err"],
            f"grok stdin parse error: {event.parse_error}",
        )
        return 0

    hook_event = str(getattr(event, "phase", "") or "")
    session_id = str(getattr(event, "session_id", "") or "")
    project_dir = str(getattr(event, "project", "") or "") or (
        os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    )

    try:
        if hook_event == "PostToolUse":
            tool_enum = _grok_tool_enum(str(getattr(event, "tool_name", "") or ""))
            _audit_emit.emit_grok_tool_recorded(
                session_id=session_id,
                tool_name_enum=tool_enum,
                hook_event_name="PostToolUse",
                project=project_dir,
            )
        elif hook_event in ("Stop", "SubagentStop"):
            derived = "subagent_stop" if hook_event == "SubagentStop" else "stop"
            source = os.environ.get("CEO_GROK_TURN_SOURCE") or derived
            _audit_emit.emit_grok_turn_ended(
                session_id=session_id,
                source=source,
                project=project_dir,
            )
        # else: SessionStart / UserPromptSubmit / SubagentStart / PreToolUse
        # are not this hook's job under grok — return 0 (no append).
    except Exception as e:  # pragma: no cover — emit is fail-open by contract
        write_breadcrumb(
            audit_paths()["err"],
            f"grok audit emit failed (fail-open): {type(e).__name__}",
        )
    return 0


# -----------------------------------------------------------------------------
# Main entry point
# -----------------------------------------------------------------------------


def main() -> int:
    """PostToolUse hook entry point.

    PLAN-006 Phase 1 final migration (ADR-014): uses
    `claude_adapter.read_post_event()` with explicit PostToolUse phase
    (R-SB1 fix). Reads stdin, extracts fields, redacts, writes one
    JSONL line to the audit log under lock. Silent on stdout. Exits 0
    on all paths (fail-open governance contract).

    PLAN-155 Wave 4: under CEO_HOOK_ADAPTER=codex the codex host-wire path
    (`_codex_audit_main`) handles the append via `_lib.audit_emit`; the claude
    path below is byte-identical when the env var is unset/`claude`.
    """
    t0 = time.monotonic()
    _adapter = os.environ.get("CEO_HOOK_ADAPTER")
    if _adapter == "codex":
        return _codex_audit_main(t0)
    if _adapter == "grok":
        return _grok_audit_main(t0)
    try:
        event = _claude_adapter.read_post_event()
        if event.parse_error:
            paths = audit_paths()
            write_breadcrumb(
                paths["err"],
                f"stdin parse error: {event.parse_error}",
            )
            return 0

        # Filter: only care about Agent spawns
        if event.tool_name and event.tool_name not in ("Agent", "unknown"):
            return 0

        project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
        try:
            project_dir = str(Path(project_dir).resolve())
        except OSError:
            pass

        duration_ms = int((time.monotonic() - t0) * 1000)
        entry = build_entry(
            event=event, project_dir=project_dir, hook_duration_ms=duration_ms
        )
        if entry is None:
            return 0

        paths = audit_paths()
        append_entry(
            entry,
            paths=paths,
            threshold_bytes=rotate_threshold(),
        )
        return 0
    except Exception as e:  # pragma: no cover — catastrophic
        try:
            paths = audit_paths()
            write_breadcrumb(paths["err"], f"fatal: {e.__class__.__name__}: {e}")
        except Exception:
            pass
        return 0


if __name__ == "__main__":
    sys.exit(main())
