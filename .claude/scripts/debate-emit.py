#!/usr/bin/env python3
"""debate-emit.py — thin CLI wrapper around emit_debate_event.

Sprint 5 A.1. Called from .claude/commands/debate.md at each debate
round phase so the audit log captures the full lifecycle (start,
per-agent critiques landing, consensus synthesis). Allows audit-query.py
to surface debate activity without scraping the plan subdir.

## Usage

    debate-emit.py <phase> <plan_id> <round> [options]

    phase: start | agent-done | consensus
    plan_id: PLAN-NNN
    round: 1..3

## Options

    --agent <slug>                  Archetype slug (or "consensus")
    --artifact <path>               Path to critique/consensus file
    --consensus-adjustments N       Only for phase=consensus

## Exit codes

    0 — emission succeeded (or fail-open path taken silently)
    1 — bad args
    2 — _lib unavailable (best-effort: still exit 0 on missing module
        so invoking scripts don't break CI in isolated envs)

## Fail-open contract

This CLI never blocks the debate flow. If audit_emit isn't importable
(e.g. running from a clone without hooks/_lib), we log to stderr and
return 0.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional


def _parse(argv: List[str]) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Emit a debate_event to the audit log"
    )
    p.add_argument(
        "phase",
        choices=["start", "agent-done", "consensus"],
        help="Phase of the debate round",
    )
    p.add_argument("plan_id", help="Plan identifier (PLAN-NNN)")
    p.add_argument("round", type=int, help="Round number (1..3)")
    p.add_argument(
        "--agent",
        default="",
        help="Archetype slug for agent-done, or 'consensus' for consensus phase",
    )
    p.add_argument(
        "--artifact",
        default=None,
        help="Path to critique/consensus artifact file",
    )
    p.add_argument(
        "--consensus-adjustments",
        type=int,
        default=None,
        help="Count of plan adjustments (only with phase=consensus)",
    )
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — emit a debate-round record into the audit-log stream."""
    args = _parse(argv if argv is not None else sys.argv[1:])

    if args.round < 1 or args.round > 3:
        print(
            f"ERROR: round must be 1..3 (got {args.round})",
            file=sys.stderr,
        )
        return 1

    if args.phase == "consensus" and not args.agent:
        args.agent = "consensus"

    if args.phase == "agent-done" and not args.agent:
        print(
            "ERROR: --agent required with phase=agent-done",
            file=sys.stderr,
        )
        return 1

    # Make _lib.audit_emit importable from sibling hooks/_lib/
    hooks_dir = Path(__file__).resolve().parent.parent / "hooks"
    if str(hooks_dir) not in sys.path:
        sys.path.insert(0, str(hooks_dir))

    try:
        from _lib.audit_emit import emit_debate_event
    except Exception as e:
        # Fail-open: don't break the caller
        print(
            f"[debate-emit] audit_emit unavailable ({type(e).__name__}); "
            "skipping event",
            file=sys.stderr,
        )
        return 0

    try:
        emit_debate_event(
            plan_id=args.plan_id,
            round_num=args.round,
            phase=args.phase,
            agent=args.agent,
            artifact_path=args.artifact,
            consensus_adjustments_count=args.consensus_adjustments,
        )
    except Exception as e:  # pragma: no cover
        print(
            f"[debate-emit] emit failed ({type(e).__name__}: {e})",
            file=sys.stderr,
        )
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
