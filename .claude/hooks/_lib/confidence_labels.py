"""Confidence labels — vibecoder UX primitive (PLAN-083 Wave 1 sub-agent 1.10).

A small, pure classifier that assigns one of three confidence labels to a
proposed action so that downstream UX surfaces (Wave 2 recommender 2.2,
receipt formatter 2.3) can decide whether to auto-proceed, ask for
confirmation, or refuse without explicit override.

## Levels (ordered by escalation)

- **SAFE**         — read-only / observational. Auto-proceed.
- **NEEDS_CONFIRM** — limited writes outside canonical paths, single Edit
                       ops, non-trading-profile script execution. Prompt
                       user before proceeding.
- **RISKY**        — canonical-guarded edits, settings.json changes,
                       sentinel modifications, trading-profile writes,
                       git push to main, force-push, kernel-override
                       invocations, bulk operations on >10 files. Refused
                       unless an explicit override env var is set.

## API (pure)

    classify(action_type: str, context: dict) -> Confidence
    as_emoji_free_marker(c: Confidence) -> str
    prompt_for_confirmation(c: Confidence, action_description: str) -> bool

## Override env vars (exact-value contract)

- `CEO_CONFIDENCE_AUTO_CONFIRM=1` — auto-allow NEEDS_CONFIRM. Truthy
  check is **exact equality with "1"** (not "true"/"yes"/etc.); ceremony
  scripts must opt in deliberately.
- `CEO_CONFIDENCE_BYPASS_RISKY=I-ACCEPT-CONSEQUENCES` — explicit RISKY
  override. **Must equal the literal string** `I-ACCEPT-CONSEQUENCES`;
  no truthy aliasing. Designed to be unmistakable in audit log + shell
  history.

## Design invariants

1. **Fail-medium on unknown.** `classify("unknown_thing", {})` returns
   `NEEDS_CONFIRM`, never SAFE (no fail-OPEN), never RISKY (no
   fail-CLOSED — we want progress without coercing the user).
2. **No leak.** Return values carry only the level + a short reason
   code; raw paths, content, and tokens never appear in the return
   value (Sec MF-3 alignment).
3. **Idempotent.** `classify(x, ctx) == classify(x, ctx)` for the same
   inputs, no hidden state.
4. **Stdlib only.** Python 3.9+ compatible. No third-party imports.

## Consumers

- Wave 2 sub-agent 2.2 (recommender) calls `classify()` for each
  candidate action and uses `as_emoji_free_marker()` to decorate the
  top-3 recommendations.
- Wave 2 sub-agent 2.3 (receipt) calls `classify()` for actions taken
  during a session, then groups them by level in the closing receipt.

See `integration-with-wave-2.md` (alongside this file) for the wiring.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from typing import Any, Dict, Mapping, Optional, Tuple


# ---------------------------------------------------------------------------
# Public level constants
# ---------------------------------------------------------------------------

# String constants chosen over Enum so they survive JSON round-trips
# unchanged (audit log emit + Wave 2 receipt formatter both serialize).
SAFE: str = "safe"
NEEDS_CONFIRM: str = "needs-confirm"
RISKY: str = "risky"

ALL_LEVELS: Tuple[str, str, str] = (SAFE, NEEDS_CONFIRM, RISKY)


# ---------------------------------------------------------------------------
# Override env-var contract (exact-value)
# ---------------------------------------------------------------------------

ENV_AUTO_CONFIRM: str = "CEO_CONFIDENCE_AUTO_CONFIRM"
ENV_AUTO_CONFIRM_VALUE: str = "1"

ENV_BYPASS_RISKY: str = "CEO_CONFIDENCE_BYPASS_RISKY"
ENV_BYPASS_RISKY_VALUE: str = "I-ACCEPT-CONSEQUENCES"


# ---------------------------------------------------------------------------
# Classification result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Confidence:
    """Immutable classification result.

    Carries only the level + a short reason code (no paths, no content).
    """

    level: str          # one of ALL_LEVELS
    reason_code: str    # short stable code, e.g. "read_only_tool"

    def __post_init__(self) -> None:
        if self.level not in ALL_LEVELS:
            # Defensive: should be unreachable via classify(), but guard
            # constructor direct callers (tests, other consumers).
            raise ValueError(
                "Confidence.level must be one of "
                + ",".join(ALL_LEVELS)
            )


# ---------------------------------------------------------------------------
# Internal classification tables
# ---------------------------------------------------------------------------

# Read-only action types — always SAFE regardless of context.
_READ_ONLY_ACTIONS: frozenset = frozenset({
    "read",
    "read_file",
    "audit_query_read",
    "status_check",
    "help_me",
    "list_files",
    "git_status",
    "git_log",
    "git_diff",
})

# Action types that are always RISKY (never demoted by context).
_ALWAYS_RISKY_ACTIONS: frozenset = frozenset({
    "canonical_edit",
    "settings_json_edit",
    "sentinel_modify",
    "trading_profile_write",
    "git_push_main",
    "git_force_push",
    "kernel_override",
})

# Action types that default to NEEDS_CONFIRM (context may escalate).
_DEFAULT_CONFIRM_ACTIONS: frozenset = frozenset({
    "write",
    "edit",
    "single_edit",
    "script_execute",
    "bash_execute",
})

# Bulk-operation threshold: > this count escalates a write to RISKY.
_BULK_FILE_THRESHOLD: int = 10


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def classify(action_type: str, context: Optional[Mapping[str, Any]]) -> Confidence:
    """Classify a proposed action.

    Args:
        action_type: Short stable identifier for the kind of action.
            See `_READ_ONLY_ACTIONS`, `_ALWAYS_RISKY_ACTIONS`,
            `_DEFAULT_CONFIRM_ACTIONS` for known values.
        context: Optional dict carrying signals that escalate the
            classification. Recognized keys:
                - "file_count": int   — if > _BULK_FILE_THRESHOLD escalates
                  any write/edit to RISKY (bulk_op).
                - "profile": str      — "trading-readonly" makes any
                  write RISKY (trading_profile_write).
                - "canonical": bool   — True forces RISKY (canonical_path).
                - "target_branch": str — "main" + git push action → RISKY.

    Returns:
        Confidence(level, reason_code). Never raises.

    Invariants:
        - Pure function (no I/O, no env reads).
        - Unknown action_type → NEEDS_CONFIRM with reason_code="unknown_action".
        - No path/content/token text in the return value.
    """
    if not isinstance(action_type, str) or action_type == "":
        return Confidence(level=NEEDS_CONFIRM, reason_code="empty_action_type")

    ctx: Mapping[str, Any] = context if context is not None else {}

    # Rule 1: explicit canonical signal → RISKY (highest priority)
    if ctx.get("canonical") is True:
        return Confidence(level=RISKY, reason_code="canonical_path")

    # Rule 2: always-risky action types
    if action_type in _ALWAYS_RISKY_ACTIONS:
        return Confidence(level=RISKY, reason_code=action_type)

    # Rule 3: read-only action types → SAFE
    if action_type in _READ_ONLY_ACTIONS:
        return Confidence(level=SAFE, reason_code="read_only")

    # Rule 4: writes under trading-readonly profile → RISKY
    profile = ctx.get("profile")
    if (
        action_type in _DEFAULT_CONFIRM_ACTIONS
        and isinstance(profile, str)
        and profile == "trading-readonly"
    ):
        return Confidence(level=RISKY, reason_code="trading_profile_write")

    # Rule 5: bulk operations (> threshold) → RISKY
    file_count = ctx.get("file_count")
    if (
        action_type in _DEFAULT_CONFIRM_ACTIONS
        and isinstance(file_count, int)
        and file_count > _BULK_FILE_THRESHOLD
    ):
        return Confidence(level=RISKY, reason_code="bulk_op")

    # Rule 6: known confirm-class actions → NEEDS_CONFIRM
    if action_type in _DEFAULT_CONFIRM_ACTIONS:
        return Confidence(level=NEEDS_CONFIRM, reason_code=action_type)

    # Rule 7: unknown action_type — fail-medium (not OPEN, not CLOSED)
    return Confidence(level=NEEDS_CONFIRM, reason_code="unknown_action")


def as_emoji_free_marker(c: Confidence) -> str:
    """Return a bracketed text marker suitable for plain-text UI.

    No emojis (per repo discipline). Stable mapping for downstream parsers.

    Args:
        c: A Confidence result.

    Returns:
        One of "[SAFE]", "[NEEDS-CONFIRM]", "[RISKY]".

    Raises:
        TypeError: if c is not a Confidence.
        ValueError: if c.level is not a known level (should be unreachable
            for instances built via classify(); guard for direct callers).
    """
    if not isinstance(c, Confidence):
        raise TypeError("as_emoji_free_marker requires a Confidence instance")
    if c.level == SAFE:
        return "[SAFE]"
    if c.level == NEEDS_CONFIRM:
        return "[NEEDS-CONFIRM]"
    if c.level == RISKY:
        return "[RISKY]"
    # Unreachable via Confidence.__post_init__ guard.
    raise ValueError("unknown confidence level: " + str(c.level))


def prompt_for_confirmation(
    c: Confidence,
    action_description: str,
    stdin: Optional[Any] = None,
    stdout: Optional[Any] = None,
    env: Optional[Mapping[str, str]] = None,
) -> bool:
    """Prompt the user for confirmation given a confidence level.

    Behavior:
        - SAFE          → returns True immediately (auto-proceed).
        - NEEDS_CONFIRM → if ENV_AUTO_CONFIRM == "1" returns True;
                           otherwise prints prompt to stdout, reads a
                           single line from stdin, returns True if the
                           response (case-insensitive, stripped) is in
                           {"y", "yes"}; False otherwise.
        - RISKY         → returns True ONLY if ENV_BYPASS_RISKY equals
                           the exact string ENV_BYPASS_RISKY_VALUE;
                           False otherwise (does not even prompt — the
                           user must opt in via env var, never via a
                           free-text "yes" that could be auto-filled).

    Args:
        c: Confidence result.
        action_description: Short human-readable text describing the
            action. **Caller is responsible for redaction** — this
            module does not strip secrets.
        stdin: File-like object with a `.readline()` method. Defaults
            to `sys.stdin`. Mockable in tests.
        stdout: File-like object with a `.write()` method. Defaults
            to `sys.stdout`. Mockable in tests.
        env: Mapping for env var lookup (test injection). Defaults to
            `os.environ`.

    Returns:
        bool — True if the action should proceed, False otherwise.

    Notes:
        - Reading stdin in a non-interactive context (e.g. EOF) returns
          False (refuse).
        - This function performs no audit emit; the caller decides
          whether to log the outcome.
    """
    if not isinstance(c, Confidence):
        raise TypeError("prompt_for_confirmation requires a Confidence instance")

    _env: Mapping[str, str] = env if env is not None else os.environ
    _stdin = stdin if stdin is not None else sys.stdin
    _stdout = stdout if stdout is not None else sys.stdout

    if c.level == SAFE:
        return True

    if c.level == RISKY:
        # Exact-value contract: truthy aliasing forbidden.
        return _env.get(ENV_BYPASS_RISKY, "") == ENV_BYPASS_RISKY_VALUE

    # NEEDS_CONFIRM path
    if _env.get(ENV_AUTO_CONFIRM, "") == ENV_AUTO_CONFIRM_VALUE:
        return True

    try:
        _stdout.write(
            "[NEEDS-CONFIRM] "
            + (action_description if isinstance(action_description, str) else "")
            + " [y/N]: "
        )
        _stdout.flush()
    except Exception:  # pragma: no cover — stdout write failure is exotic
        # Fail-medium: if we can't even print, refuse.
        return False

    try:
        line = _stdin.readline()
    except Exception:  # pragma: no cover
        return False

    if not line:
        # EOF / non-interactive — refuse.
        return False

    return line.strip().lower() in ("y", "yes")
