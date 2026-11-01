"""status context-budget declarations."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .compaction import ENV_AUTO_COMPACT_THRESHOLD
from .summarization import ENV_SUMMARIZE_OLDEST
from .middle_out import ENV_MIDDLE_OUT_DEGRADE

__all__ = ('PROBE_VERDICT_KEEP', 'PROBE_VERDICT_REMOVE_PENDING', 'PROBE_STATUS', 'PROBE_STATUS_NOTE', 'probe_status', 'scan_tool_loops', '_render_human', '_render_loops_human')

# ---------------------------------------------------------------------------
# PLAN-179 W3 item US11 — declared probe status (orphan-probe debt ledger)
# ---------------------------------------------------------------------------
#
# "An orphan probe that stays is debt that LOOKS like coverage." The three
# PLAN-133 Wave D decision probes above (D1/D2/D5) are complete, tested, and
# CALLED BY NOBODY. Silence is the failure mode: a reader sees a `--*-decision`
# flag plus a test class and concludes the behaviour is wired.
#
# This block makes the state EXPLICIT and machine-readable. It is descriptive
# only — it changes no behaviour, gates nothing, and is rendered in `--json`,
# in the human report, and standalone via `--probe-status`.
#
# Every "measured" field below was established by grep/count on 2026-08-18 and
# is reproducible; the commands are recorded in
# `.claude/plans/PLAN-179/orphan-probe-decision.md`. `observed_emits` counted
# 0 of each action across 7972 parsed audit-log events.

# Closed verdict enum, so a reader (or a future gate) can branch on it.
PROBE_VERDICT_KEEP = "keep_exported_policy"   # no in-repo consumer is possible
PROBE_VERDICT_REMOVE_PENDING = "remove_pending_test_codeletion"

PROBE_STATUS = (
    {
        "probe": "D1",
        "subject": "proactive auto-compaction policy (hysteresis)",
        "entrypoints": ("decide_compaction", "--compact-decision"),
        "env_flag": ENV_AUTO_COMPACT_THRESHOLD,
        "audit_actions": (
            "context_auto_compacted",
            "context_auto_compact_suppressed",
        ),
        "canonical_emit_landed": True,
        "emitters_in_repo": 0,
        "observed_emits": 0,
        "verdict": PROBE_VERDICT_KEEP,
        "consumer": (
            "a HOST LOOP that owns its own context-management step (an adopter "
            "API/SDK harness). It does not exist here and cannot: Claude Code "
            "owns compaction, and the pinned hook schema gives PreCompact NO "
            "hookSpecificOutput arm, so a hook may observe or block a "
            "compaction but never drive one."
        ),
        "why_not_removed": (
            "the canonical half IS landed (audit_emit + SPEC v1 + the golden "
            "audit registry). Deleting the decision half here would orphan a "
            "canonical surface that only an Owner-GPG ceremony may touch."
        ),
        "removal_scope": (
            "Owner-GPG ceremony: .claude/hooks/_lib/audit_emit.py, "
            "SPEC/v1/audit-log.schema.md, .claude/data/audit-registry.golden.txt, "
            "this block, and the matching tests."
        ),
    },
    {
        "probe": "D2",
        "subject": "summarize oldest verbose subagent outputs (protect last N)",
        "entrypoints": ("decide_summarization", "--summarize-decision"),
        "env_flag": ENV_SUMMARIZE_OLDEST,
        "audit_actions": (
            "subagent_output_summarized",
            "subagent_output_summarize_skipped",
        ),
        "canonical_emit_landed": False,
        "emitters_in_repo": 0,
        "observed_emits": 0,
        "verdict": PROBE_VERDICT_REMOVE_PENDING,
        "consumer": (
            "none, and none is buildable here: D2 requires a cheap-tier MODEL "
            "call to produce the digest, and this framework's in-path code is "
            "stdlib-only and no-network by construction."
        ),
        "why_not_removed": (
            "the deletion must remove the probe AND its test in the SAME "
            "change; the test file was outside the authoring agent's file "
            "assignment. Removing the probe alone would turn a green suite red "
            "— strictly worse than the declared debt."
        ),
        "removal_scope": (
            "non-canonical, no ceremony: the D2 block in this file, the "
            "--summarize-decision / --output-sizes / --output-sizes-file CLI "
            "surface, and class TestSummarizationPolicy in "
            ".claude/scripts/tests/test_context_budget.py."
        ),
    },
    {
        "probe": "D5",
        "subject": "middle-out degradation ladder on context overflow",
        "entrypoints": (
            "decide_middle_out_degradation",
            "apply_middle_out_degradation",
            "--middle-out-decision",
        ),
        "env_flag": ENV_MIDDLE_OUT_DEGRADE,
        "audit_actions": (
            "context_middle_out_degraded",
            "context_middle_out_degrade_failed",
        ),
        "canonical_emit_landed": True,
        "emitters_in_repo": 0,
        "observed_emits": 0,
        "verdict": PROBE_VERDICT_KEEP,
        "consumer": (
            "the same absent HOST LOOP as D1 — the component that assembles "
            "the context and discovers the overflow. Claude Code assembles its "
            "own context; this framework never sees the message list."
        ),
        "why_not_removed": (
            "identical to D1: the canonical emit half is landed, so removal is "
            "a ceremony, not a script edit."
        ),
        "removal_scope": (
            "Owner-GPG ceremony: .claude/hooks/_lib/audit_emit.py, "
            "SPEC/v1/audit-log.schema.md, .claude/data/audit-registry.golden.txt, "
            "this block, and the matching tests."
        ),
    },
)

# One line per probe, rendered in the human report so the debt is visible to a
# reader who never opens the JSON.
PROBE_STATUS_NOTE = (
    "Decision probes D1/D2/D5 in this CLI have ZERO callers and have never "
    "fired — they are reference policy, NOT coverage. Verdicts, consumers and "
    "removal scope: probe_status() / --probe-status (PLAN-179 W3 US11)."
)


def probe_status() -> List[Dict[str, Any]]:
    """Return the declared D1/D2/D5 probe-status records (fresh, mutable).

    Descriptive only. Tuples are converted to lists so the result is
    JSON-serialisable and a caller mutating it cannot corrupt the module
    constant.
    """
    out: List[Dict[str, Any]] = []
    for rec in PROBE_STATUS:
        item: Dict[str, Any] = {}
        for key, value in rec.items():
            item[key] = list(value) if isinstance(value, tuple) else value
        out.append(item)
    return out


# ---------------------------------------------------------------------------
# Optional P3 fold-in: tool-loop scan (ECC ecc-context-monitor idea)
# ---------------------------------------------------------------------------


def scan_tool_loops(
    audit_log: Path, min_run: int = 3,
) -> Dict[str, Any]:
    """Flag runs of N identical *consecutive* tool-calls in an audit-log.

    Reads a JSONL audit-log read-only; for each line, derives a tool key from
    ``tool_name`` (fallback ``action``). A run of ``>= min_run`` identical
    consecutive keys is flagged (an agent stuck in a tool loop). Advisory:
    tolerant of malformed lines, never blocks, never echoes payload content.
    Returns ``{loops: [...], lines_scanned, error?}``.
    """
    text = _read_text(audit_log)
    if text is None:
        return {"loops": [], "lines_scanned": 0, "error": "unreadable"}

    keys: List[str] = []
    scanned = 0
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        scanned += 1
        try:
            obj = json.loads(line)
        except (json.JSONDecodeError, ValueError):
            # Malformed line breaks the consecutive run (use a sentinel).
            keys.append("\x00malformed")
            continue
        if not isinstance(obj, dict):
            keys.append("\x00malformed")
            continue
        key = obj.get("tool_name") or obj.get("action") or "\x00unknown"
        keys.append(str(key))

    loops: List[Dict[str, Any]] = []
    i = 0
    n = len(keys)
    while i < n:
        j = i
        while j < n and keys[j] == keys[i]:
            j += 1
        run_len = j - i
        key = keys[i]
        if run_len >= min_run and not key.startswith("\x00"):
            loops.append({
                "tool": key,
                "consecutive_count": run_len,
                "start_index": i,
                "message": (
                    "{n} consecutive '{tool}' calls (>= {m}) — possible tool "
                    "loop".format(n=run_len, tool=key, m=min_run)
                ),
            })
        i = j

    return {"loops": loops, "lines_scanned": scanned}


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _render_human(report: Dict[str, Any], top: int) -> str:
    lines: List[str] = []
    lines.append("# context-budget report")
    lines.append("# heuristic: {}".format(report["heuristic"]))
    lines.append(
        "# grand total: ~{} est tokens across the always-loaded surface".format(
            report["grand_total_est_tokens"],
        )
    )
    lines.append("")
    lines.append("## per-category")
    lines.append("  {:<12} {:>6} {:>8} {:>10}".format(
        "category", "files", "lines", "est_tok"))
    for c in report["categories"]:
        if c["category"] == CAT_MCP:
            extra = "servers={}".format(c.get("server_count", 0))
            if c.get("over_subscribed"):
                extra += " OVER-SUBSCRIBED"
            lines.append("  {:<12} {:>6} {:>8} {:>10}  {}".format(
                c["category"], c["file_count"], "-", "-", extra))
        else:
            lines.append("  {:<12} {:>6} {:>8} {:>10}".format(
                c["category"], c["file_count"], c["total_lines"], c["est_tokens"]))
    lines.append("")

    lines.append("## top {} reduction candidates (by est tokens)".format(top))
    if not report["top_candidates"]:
        lines.append("  (none — no files inventoried)")
    else:
        for e in report["top_candidates"]:
            lines.append("  ~{:>7} tok  {:>5}L  [{}]  {}".format(
                e["est_tokens"], e["lines"], e["category"], e["path"]))
    lines.append("")

    # PLAN-153 Wave C item 5 — top-3 savings opportunities.
    savings = report.get("savings_top3", [])
    lines.append("## top-3 savings opportunities (progressive disclosure)")
    if not savings:
        lines.append(
            "  (none — no un-split SKILL.md over {} lines)".format(
                THRESHOLD_SKILL_LINES))
    else:
        for s in savings:
            lines.append(
                "  {}. {} — {}L, ~{} est tok; potential saving ~{} est tok "
                "per activation".format(
                    s["rank"], s["path"], s["lines"], s["est_tokens"],
                    s["est_saving_tokens"]))
            lines.append("     why ranked: {}".format(s["reason"]))
            lines.append("     mechanism: {}".format(s["mechanism"]))
            if s.get("caveat"):
                lines.append("     caveat: {}".format(s["caveat"]))
    lines.append("")

    lines.append("## flags ({} total)".format(report["flag_count"]))
    if not report["flags"]:
        lines.append("  OK: no heavy-file / bloat / over-subscription flags.")
    else:
        for f in report["flags"]:
            lines.append("  [{}] {}".format(f["kind"], f.get("path", f["category"])))
            lines.append("      {}".format(f["message"]))
    lines.append("")

    # PLAN-179 W3 US11 — declared probe status (debt, not coverage).
    probes = report.get("probe_status", [])
    if probes:
        lines.append("## decision-probe status (D1/D2/D5 — reference policy, "
                     "NOT wired)")
        for p in probes:
            lines.append("  [{}] {} — verdict={}".format(
                p.get("probe"), p.get("subject"), p.get("verdict")))
            lines.append("      emitters in repo: {} | observed emits: {} | "
                         "canonical emit landed: {}".format(
                             p.get("emitters_in_repo"),
                             p.get("observed_emits"),
                             p.get("canonical_emit_landed"),
                         ))
            lines.append("      missing consumer: {}".format(p.get("consumer")))
        lines.append("")

    lines.append("## honesty notes")
    for note in report.get("notes", []):
        lines.append("  - {}".format(note))
    if not report.get("scanner_available", True):
        lines.append(
            "  - DEGRADED: _lib/injection_patterns unavailable — displayed "
            "identifiers fell back to the charset allowlist only.")
    lines.append("")
    lines.append("# advisory only — this tool never blocks and never writes "
                 "outside stdout.")
    return "\n".join(lines)


def _render_loops_human(result: Dict[str, Any]) -> str:
    lines: List[str] = []
    lines.append("# tool-loop scan")
    lines.append("# lines scanned: {}".format(result.get("lines_scanned", 0)))
    if result.get("error"):
        lines.append("# error: {}".format(result["error"]))
    loops = result.get("loops", [])
    if not loops:
        lines.append("  OK: no tool loops detected.")
    else:
        for lp in loops:
            lines.append("  [tool_loop] {}".format(lp["message"]))
    lines.append("")
    lines.append("# advisory only.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


