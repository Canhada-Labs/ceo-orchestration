#!/usr/bin/env python3
"""Governance Hook: cross-plan scratchpad access guard.

PLAN-011 Phase 7. Registered in `.claude/settings.json` under
`hooks.PreToolUse.Bash` (appended after `check_bash_safety.py`). Runs
via the `_python-hook.sh` shim.

## What it enforces

When a Bash command invokes ``scratchpad.py`` with an explicit
``--plan PLAN-X``, the hook derives the current session's plan via
:func:`scratchpad_lib.resolve_plan_id` and blocks the call if the two
do not match. This defends against consensus M2's concern: an agent
with subshell execution could attempt ``scratchpad.py get --plan PLAN-X``
to sniff another plan's notes. The filesystem boundary in state_store
already isolates the sqlite files, but the CLI itself had no gate on
the ``--plan`` override until this hook.

## When it DOES NOT block

- Not a scratchpad command (first token is not python + scratchpad.py).
- ``--plan`` flag is omitted — derivation happens inside the CLI,
  and cross-plan is impossible there (CLI uses resolve_plan_id()).
- Current session has no resolvable plan (e.g. no plan_transition
  events yet): fail-open. Without a trust anchor we cannot compute a
  mismatch.
- Parse failures / infrastructure errors: fail-open per ADR-002
  (hooks never block a user session on infra bugs).

## Output contract

Writes a single-line JSON decision to stdout:

    {"decision":"allow"}
    {"decision":"block","reason":"scratchpad --plan ..."}

Exit code is always 0. Claude Code reads the decision from stdout.
"""

from __future__ import annotations

import re
import shlex
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib import contract as _contract  # noqa: E402
from _lib.adapters import claude as _claude_adapter  # noqa: E402


# Naive top-level operator split — same approach as check_bash_safety.py.
# Quoted operators are over-split but shlex.split on each chunk fails
# closed so the chunk is skipped. Fail-safe.
_SUBCOMMAND_SPLIT_RE = re.compile(r"\s*(?:&&|\|\||[;|])\s*")

# Regex that identifies a scratchpad.py invocation. Tokens are compared
# post-shlex; we only match when the first non-python-interpreter token
# ends with "scratchpad.py".
_SCRATCHPAD_SUFFIX = "scratchpad.py"


@dataclass
class Decision:
    """Typed decision for unit tests."""

    allow: bool
    reason: Optional[str] = None


def _split_subcommands(command: str) -> List[str]:
    if not command or not command.strip():
        return []
    parts = _SUBCOMMAND_SPLIT_RE.split(command)
    return [p for p in (s.strip() for s in parts) if p]


def _tokenize(subcommand: str) -> List[str]:
    try:
        return shlex.split(subcommand)
    except ValueError:
        return []


def _is_python_interpreter(token: str) -> bool:
    """Return True when token looks like a python interpreter."""
    base = token.rsplit("/", 1)[-1]
    return base in {"python", "python3", "python3.9", "python3.10", "python3.11", "python3.12", "python3.13"}


def _tokens_target_scratchpad(tokens: List[str]) -> bool:
    """Return True if tokens represent a scratchpad.py invocation.

    Accepts three shapes:
        python3 .claude/scripts/scratchpad.py ...
        python3 -m something .claude/scripts/scratchpad.py ...  (rare)
        ./.claude/scripts/scratchpad.py ...                     (direct exec)

    The match is on the suffix ``scratchpad.py`` — the rest of the
    path is irrelevant so test fixtures can live at any absolute path.
    """
    if not tokens:
        return False
    # Direct execution: ./scratchpad.py or path ending in scratchpad.py
    if tokens[0].endswith(_SCRATCHPAD_SUFFIX):
        return True
    # Interpreter form: python[3] <...> scratchpad.py
    if _is_python_interpreter(tokens[0]):
        for t in tokens[1:]:
            if t.startswith("-"):
                continue
            if t.endswith(_SCRATCHPAD_SUFFIX):
                return True
            # First non-flag token that is NOT scratchpad.py -> different script
            return False
    return False


def _extract_plan_override(tokens: List[str]) -> Optional[str]:
    """Parse ``--plan PLAN-X`` or ``--plan=PLAN-X`` from tokens.

    Returns None if no ``--plan`` flag is present.
    """
    for i, t in enumerate(tokens):
        if t == "--plan":
            if i + 1 < len(tokens):
                return tokens[i + 1]
            return None
        if t.startswith("--plan="):
            return t.split("=", 1)[1]
    return None


def _resolve_current_session_plan() -> Optional[str]:
    """Return the current session's plan id, or None on any failure.

    Import is lazy so hook import time stays small and test
    environments that swap env vars mid-run see fresh state.
    """
    try:
        from _lib.scratchpad_lib import PlanIdDerivationError, resolve_plan_id
    except Exception:  # pragma: no cover — defensive
        return None
    try:
        return resolve_plan_id()
    except PlanIdDerivationError:
        return None
    except Exception:  # pragma: no cover — fail-open on any infra error
        return None


def decide_command(command: str) -> Decision:
    """Pure decision function — no I/O, trivially unit-testable."""
    if not command or not command.strip():
        return Decision(allow=True)

    for subcommand in _split_subcommands(command):
        tokens = _tokenize(subcommand)
        if not tokens:
            continue
        if not _tokens_target_scratchpad(tokens):
            continue

        override = _extract_plan_override(tokens)
        if override is None:
            # --plan omitted -> derivation happens in CLI; cross-plan impossible.
            continue

        # --plan present: resolve session plan and compare.
        session_plan = _resolve_current_session_plan()
        if session_plan is None:
            # No trust anchor -> fail-open.
            continue

        if override != session_plan:
            return Decision(
                allow=False,
                reason=(
                    f"scratchpad --plan {override} but session is scoped to "
                    f"{session_plan}. Cross-plan scratchpad access is denied "
                    "(consensus M2). Run without --plan to use the derived "
                    "plan_id, or switch sessions."
                ),
            )
    return Decision(allow=True)


def _to_contract_decision(d: Decision) -> _contract.Decision:
    if d.allow:
        return _contract.allow()
    return _contract.block(d.reason or "")


def main() -> int:
    """Hook entry point — fail-open on any exception."""
    try:
        event = _claude_adapter.read_event(phase="PreToolUse")
        if event.parse_error:
            print(
                f"[check_scratchpad_access] WARN: stdin parse error: {event.parse_error}",
                file=sys.stderr,
            )
            _claude_adapter.emit_decision(_contract.allow())
            return 0

        command = event.command or ""
        if not command and isinstance(event.tool_input, dict):
            command = str(event.tool_input.get("command") or "")

        decision = decide_command(command)
        _claude_adapter.emit_decision(_to_contract_decision(decision))
        return 0
    except Exception as e:  # pragma: no cover
        print(
            f"[check_scratchpad_access] FATAL: {e.__class__.__name__}: {e}",
            file=sys.stderr,
        )
        _claude_adapter.emit_decision(_contract.allow())
        return 0


if __name__ == "__main__":
    sys.exit(main())
