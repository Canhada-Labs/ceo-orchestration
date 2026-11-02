#!/usr/bin/env python3
"""context-budget.py — static context-inventory audit (advisory, never blocks).

PLAN-124 WS-4. Stdlib-only, loopback / read-only — like
``check-staleness.py`` and our other advisory scanners. This tool inventories
the **always-loaded / Gate-1 + skill surface** that we re-pay every session
(CLAUDE.md §0 cache discipline, ~44,786-token gate-boot cost) and produces:

  * a per-category estimated-token table, and
  * a top-N ranked list of reduction candidates (heaviest files / bloated
    frontmatter / MCP over-subscription).

It harvests the **mechanism** from ECC's ``skills/context-budget/SKILL.md``
(token inventory + heavy-file flagging + top optimizations) re-implemented in
stdlib Python under our patterns. ECC is MIT; this is a re-implementation, not
a vendored copy.

## What is inventoried (categories)

| Category    | Surface                                                  |
|-------------|----------------------------------------------------------|
| claude_md   | ``CLAUDE.md``                                            |
| protocol    | ``PROTOCOL.md``                                          |
| team        | ``.claude/team.md`` + ``.claude/frontend-team.md``       |
| core_skill  | ``.claude/skills/core/ceo-orchestration/SKILL.md``       |
| agents      | ``.claude/agents/*.md``                                  |
| skills      | ``.claude/skills/**/SKILL.md``                           |
| commands    | ``.claude/commands/*.md``                                |
| mcp         | MCP subscription surface (``.mcp.json`` / settings)      |

## Heavy-file thresholds (from the ECC reference)

  * agents          > 200 lines
  * skills          > 400 lines
  * rules/commands  > 100 lines
  * frontmatter ``description:`` > 200 chars  (bloated description)
  * MCP servers     > 5 configured            (over-subscription)

## Token estimate

Reuses the repo's documented chars/4 heuristic (see
``profile-opus-4-7.py:estimate_gate_boot_token_cost`` — "1 token ≈ 4 chars").
This is an **estimate** for monotonic diff tracking, NOT the Anthropic
tokenizer. Every report labels it as such.

## Usage

    python3 .claude/scripts/context-budget.py
    python3 .claude/scripts/context-budget.py --json
    python3 .claude/scripts/context-budget.py --top 5
    python3 .claude/scripts/context-budget.py --repo-root <path>
    python3 .claude/scripts/context-budget.py --tool-loop-scan <audit-log.jsonl>
    python3 .claude/scripts/context-budget.py --compact-decision \
        --used-tokens 170000 --window-tokens 200000   # D1 auto-compaction probe
    python3 .claude/scripts/context-budget.py --summarize-decision \
        --output-sizes '[12000,800,30000,500]'        # D2 summarize-oldest probe
    python3 .claude/scripts/context-budget.py --middle-out-decision \
        --message-sizes '[50000,800,50000,500]' \
        --budget-tokens 60000                          # D5 middle-out ladder probe
    python3 .claude/scripts/context-budget.py --probe-status  # D1/D2/D5 debt state

Exit code: always 0 (advisory) — never blocks a session, never writes outside
stdout. Use ``--strict`` to exit 1 when any heavy-file / over-subscription
flag fires (for an opt-in advisory CI lint).

## PLAN-153 Wave C item 5 — /context-budget command surface

The ``/context-budget`` slash command (``.claude/commands/context-budget.md``)
fronts this CLI. Wave C additions on top of the PLAN-124 inventory:

  * ``savings_top3`` — top-3 progressive-disclosure savings opportunities.
    Candidate = a SKILL.md over the heavy-skill line threshold with NO
    ``references/`` dir yet (already-split skills self-retire from the list).
    The PLAN-153 Wave C item 1 **designated pilots**
    (``core/testing-strategy``, ``core/security-and-auth``) rank first WHEN
    the scan finds them still un-split — that ordering is a plan decision,
    not a pure size rank, and each entry says which rule ranked it.
  * ``notes`` — honesty block rendered in both outputs: chars/4 is an
    ESTIMATE (not a tokenizer); this is a STATIC audit (activation-time cost,
    not runtime usage — retire/merge/improve judgement is /skill-health's
    scope, and neither tool can measure greenfield domains; PLAN-153 debate A
    must-fix 4).
  * Untrusted-data fence (debate B unseen-2): scanned file content is DATA,
    never instructions. The only free text this report re-displays (MCP
    server names from config files) passes ``_lib/injection_patterns`` +
    a conservative charset allowlist; hits render as
    ``[REDACTED-INJECTION-PATTERN]``. Frontmatter descriptions are only
    MEASURED (length), never displayed.
  * ``--scheduled`` — any scheduled wrapper must pass it so
    ``CEO_SOTA_DISABLE`` is honored.

## PLAN-179 W3 item US11 — probe status (the D1/D2/D5 orphan verdict)

This file also carries three **decision probes** harvested from PLAN-133
Wave D: D1 (proactive auto-compaction), D2 (summarize oldest verbose
subagent outputs), D5 (middle-out degradation ladder). Every one of them is
a pure decision function plus a ``--*-decision`` CLI mode. **None of them has
a caller.** An orphan probe that stays silent looks like coverage, so the
state is now DECLARED rather than implied, machine-readably, in
``probe_status()`` — surfaced in ``--json``, in the human report, and via
``--probe-status``.

Summary of the verdict (full reasoning + measurements:
``.claude/plans/PLAN-179/orphan-probe-decision.md``):

  * **D1 — KEEP as an exported policy, not as coverage.** Its canonical audit
    twin (``context_auto_compacted`` / ``context_auto_compact_suppressed``)
    IS landed in ``.claude/hooks/_lib/audit_emit.py``, ``SPEC/v1/
    audit-log.schema.md`` and ``.claude/data/audit-registry.golden.txt``.
    Deleting the decision half would orphan a canonical half that only an
    Owner-GPG ceremony may touch. The consumer that does not exist is a HOST
    LOOP that owns its own context-management step; Claude Code owns
    compaction itself, so this repo cannot be that consumer.
  * **D5 — KEEP, same shape as D1** (``context_middle_out_degraded`` /
    ``context_middle_out_degrade_failed`` are likewise landed canonical).
  * **D2 — REMOVE (pending).** D2 has NO canonical twin: its emit actions
    appear nowhere but this file. Removal must delete the probe AND
    ``TestSummarizationPolicy`` in ``.claude/scripts/tests/
    test_context_budget.py`` in one change; that test file was outside the
    authoring agent's file assignment, so the deletion is scoped and recorded,
    not half-applied. Deleting the probe alone would turn 144 green tests red.

## Stdlib-only

Filesystem walks + ``json`` for MCP config + a regex frontmatter parse. No
deps; never reads outside the given repo-root; never mutates anything.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Heuristic + thresholds
# ---------------------------------------------------------------------------

# Repo-canonical token estimate: 1 token ≈ 4 chars (English-Portuguese mix).
# Mirrors profile-opus-4-7.py. Estimate only; not the Anthropic tokenizer.
CHARS_PER_TOKEN = 4

# Heavy-file line thresholds (from the ECC context-budget reference).
THRESHOLD_AGENT_LINES = 200
THRESHOLD_SKILL_LINES = 400
THRESHOLD_RULE_LINES = 100  # commands / rules
# Bloated frontmatter `description:` length (chars).
THRESHOLD_DESCRIPTION_CHARS = 200
# MCP over-subscription: more than this many configured servers.
THRESHOLD_MCP_SERVERS = 5

# Category labels (stable keys for --json consumers).
CAT_CLAUDE_MD = "claude_md"
CAT_PROTOCOL = "protocol"
CAT_TEAM = "team"
CAT_CORE_SKILL = "core_skill"
CAT_AGENTS = "agents"
CAT_SKILLS = "skills"
CAT_COMMANDS = "commands"
CAT_MCP = "mcp"

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


# ---------------------------------------------------------------------------
# PLAN-153 Wave C — untrusted-data fence (debate B unseen-2)
# ---------------------------------------------------------------------------
#
# Everything this tool reads is repo file content — rendered as DATA, never
# as instructions. The only free-text field re-displayed verbatim-ish is the
# MCP server name (a key in a JSON config); it passes the harness-mimicry
# injection scan + a conservative charset allowlist before display (mirrors
# skill-health.py `fence_token`). Frontmatter descriptions are only MEASURED
# (length), never displayed, so they need no display fence.

_HOOKS_DIR = str(Path(__file__).resolve().parent.parent / "hooks")
if _HOOKS_DIR not in sys.path:
    sys.path.insert(0, _HOOKS_DIR)

try:
    from _lib import injection_patterns as _injection_patterns  # type: ignore
except Exception:  # pragma: no cover - exercised via monkeypatch in tests
    _injection_patterns = None  # type: ignore[assignment]

REDACTED = "[REDACTED-INJECTION-PATTERN]"

# Conservative charset for identifier-like fields (MCP server names). No
# whitespace / angle brackets / pipes survive, so no catalogued injection
# pattern can survive either; the scanner still runs first when available.
_TOKEN_ALLOWED = re.compile(r"[^A-Za-z0-9._:/@#+()-]")



# Bind extracted declarations to this original CLI module namespace.
from _lib._context_budget_parts import install as _install_context_parts
_install_context_parts(globals(), (
    "inventory", "compaction", "summarization", "middle_out", "status",
))
del _install_context_parts

def _cli(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(
        description="ceo-orchestration context-budget audit (advisory, "
                    "read-only, never blocks)",
    )
    parser.add_argument(
        "--repo-root", default=".", help="project root (default: cwd)")
    parser.add_argument(
        "--json", action="store_true", help="machine-readable JSON output")
    parser.add_argument(
        "--top", type=int, default=10,
        help="how many top reduction candidates to rank (default: 10)")
    parser.add_argument(
        "--strict", action="store_true",
        help="exit 1 if any flag fires (opt-in advisory CI lint)")
    parser.add_argument(
        "--scheduled", action="store_true",
        help="mark this run as scheduled machinery (honors CEO_SOTA_DISABLE)")
    parser.add_argument(
        "--tool-loop-scan", metavar="AUDIT_LOG", default=None,
        help="(P3) flag N identical consecutive tool-calls in an audit-log "
             "JSONL file, then exit")
    parser.add_argument(
        "--loop-min", type=int, default=3,
        help="min consecutive identical tool-calls to flag a loop (default: 3)")
    # PLAN-133 D1 — auto-compaction decision probe (advisory; default-OFF unless
    # CEO_AUTO_COMPACT_THRESHOLD is set in the environment).
    parser.add_argument(
        "--compact-decision", action="store_true",
        help="(D1) print the proactive auto-compaction decision for a context "
             "snapshot, then exit. Default-OFF: requires CEO_AUTO_COMPACT_THRESHOLD.")
    parser.add_argument("--used-tokens", type=int, default=None,
                        help="(D1) current context usage in tokens")
    parser.add_argument("--window-tokens", type=int, default=None,
                        help="(D1) model context window in tokens")
    parser.add_argument("--reclaimable-tokens", type=int, default=None,
                        help="(D1) estimated tokens a compaction would free")
    parser.add_argument("--armed", dest="armed", action="store_true", default=True,
                        help="(D1) re-arm flag is set (default)")
    parser.add_argument("--disarmed", dest="armed", action="store_false",
                        help="(D1) re-arm flag is cleared (post-compaction)")
    parser.add_argument("--turns-since-compaction", type=int, default=None,
                        help="(D1) turns elapsed since the last compaction")
    # PLAN-133 D2 — oldest-verbose-output summarization decision probe
    # (advisory; default-OFF unless CEO_SUMMARIZE_OLDEST is set). Reads an
    # ordered list of per-output token sizes (oldest first) from a JSON file or
    # inline, and prints the summarization plan, then exits.
    parser.add_argument(
        "--summarize-decision", action="store_true",
        help="(D2) print the oldest-verbose-output summarization plan for a "
             "list of subagent output token-sizes, then exit. Default-OFF: "
             "requires CEO_SUMMARIZE_OLDEST.")
    parser.add_argument(
        "--output-sizes", metavar="JSON", default=None,
        help="(D2) JSON array of per-output est-token sizes (OLDEST FIRST), "
             "e.g. '[12000, 800, 30000, 500]'")
    parser.add_argument(
        "--output-sizes-file", metavar="PATH", default=None,
        help="(D2) path to a JSON file holding the per-output size array")
    # PLAN-133 D5 — middle-out degradation ladder decision probe (advisory;
    # default-OFF unless CEO_MIDDLE_OUT_DEGRADE is set). Reads an ordered list of
    # per-message token sizes (oldest first) + a budget, and prints the
    # degradation plan, then exits. Decision only — never elides anything.
    parser.add_argument(
        "--middle-out-decision", action="store_true",
        help="(D5) print the middle-out degradation plan for a list of message "
             "token-sizes + a token budget, then exit. Default-OFF: requires "
             "CEO_MIDDLE_OUT_DEGRADE.")
    parser.add_argument(
        "--message-sizes", metavar="JSON", default=None,
        help="(D5) JSON array of per-message est-token sizes (OLDEST FIRST), "
             "e.g. '[50000, 800, 50000, 500]'")
    parser.add_argument(
        "--message-sizes-file", metavar="PATH", default=None,
        help="(D5) path to a JSON file holding the per-message size array")
    parser.add_argument(
        "--budget-tokens", type=int, default=None,
        help="(D5) the token budget the assembled context must fit within")
    # PLAN-179 W3 US11 — print the declared D1/D2/D5 probe status and exit.
    parser.add_argument(
        "--probe-status", action="store_true",
        help="(US11) print the declared orphan-probe status for the D1/D2/D5 "
             "decision probes (verdict, missing consumer, removal scope), "
             "then exit. Descriptive only.")
    args = parser.parse_args(argv)

    # CEO_SOTA_DISABLE contract: any *scheduled* machinery must honor it.
    if args.scheduled and os.environ.get("CEO_SOTA_DISABLE"):
        print("[context-budget] skipped: CEO_SOTA_DISABLE is set "
              "(scheduled run)")
        return 0

    # Clamp a negative --top to 0 (least-surprising): a negative limit would
    # otherwise SKIP the slice and return ALL candidates plus print a
    # nonsensical "top -N" header. 0 cleanly means "rank nothing".
    if args.top is not None and args.top < 0:
        args.top = 0

    # US11 fold-in mode — independent of the inventory. Pure description of the
    # probe debt; reads nothing, writes nothing, always exit 0.
    if args.probe_status:
        print(json.dumps(probe_status(), indent=2))
        return 0

    # D1 fold-in mode — independent of the inventory. Advisory + read-only:
    # prints the decision dict, never compacts, never emits, always exit 0.
    if args.compact_decision:
        decision = decide_compaction(
            args.used_tokens,
            args.window_tokens,
            reclaimable_tokens=args.reclaimable_tokens,
            armed=args.armed,
            turns_since_last_compaction=args.turns_since_compaction,
        )
        print(json.dumps(decision, indent=2))
        return 0

    # D2 fold-in mode — independent of the inventory. Advisory + read-only:
    # prints the summarization plan, never summarizes, never emits, exit 0.
    if args.summarize_decision:
        sizes: Any = []
        raw = None
        if args.output_sizes_file:
            raw = _read_text(Path(args.output_sizes_file))
        elif args.output_sizes is not None:
            raw = args.output_sizes
        if raw is not None:
            try:
                sizes = json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                sizes = []  # fail-open: malformed input ⇒ empty (disabled-ish)
        plan = decide_summarization(sizes)
        print(json.dumps(plan, indent=2))
        return 0

    # D5 fold-in mode — independent of the inventory. Advisory + read-only:
    # prints the degradation plan, never elides, never emits, exit 0.
    if args.middle_out_decision:
        msg_sizes: Any = []
        raw = None
        if args.message_sizes_file:
            raw = _read_text(Path(args.message_sizes_file))
        elif args.message_sizes is not None:
            raw = args.message_sizes
        if raw is not None:
            try:
                msg_sizes = json.loads(raw)
            except (json.JSONDecodeError, ValueError):
                msg_sizes = []  # fail-open: malformed input ⇒ empty
        budget = args.budget_tokens if args.budget_tokens is not None else 0
        plan = decide_middle_out_degradation(msg_sizes, budget)
        print(json.dumps(plan, indent=2))
        return 0

    # P3 fold-in mode — independent of the inventory.
    if args.tool_loop_scan is not None:
        result = scan_tool_loops(Path(args.tool_loop_scan), min_run=args.loop_min)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(_render_loops_human(result))
        # Advisory: exit 0 unless --strict and loops were found.
        if args.strict and result.get("loops"):
            return 1
        return 0

    repo = Path(args.repo_root).resolve()
    report = build_inventory(repo, top=args.top)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(_render_human(report, args.top))

    if args.strict and report["flag_count"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
