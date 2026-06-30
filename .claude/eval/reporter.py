#!/usr/bin/env python3
"""reporter.py — PLAN-133 C3 reward-benchmark reporter.

Renders the runner's results dict (see ``runner.run_suite``) as a harbor-style
markdown report: one row per task with **reward, trial status, cost (quota:
attempts + tokens), compute (turns), and a flaky flag**, plus a summary line.
Cost is reported as subscription-quota draw (attempts + tokens), NOT dollars
(S220/ADR-144 — on a subscription the cost metric is quota, not USD).

Pure + stdlib-only: ``emit_markdown(results) -> str`` and
``emit_json(results) -> str`` are deterministic given the same results dict, so
they are trivially unit-testable. The reporter never spends quota and never
imports the Anthropic SDK.

Also usable standalone to re-render a saved run:

    python3 .claude/eval/reporter.py results.json [--json]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List


_STATUS_GLYPH = {"pass": "PASS", "partial": "PARTIAL", "fail": "FAIL"}


def _pct(n: int, d: int) -> int:
    return int(round((n / d) * 100)) if d else 0


def emit_markdown(results: Dict[str, Any]) -> str:
    """Render the suite results as a markdown report (harbor-style rows)."""
    lines: List[str] = []
    task_count = int(results.get("task_count", 0))
    status_counts = results.get("status_counts", {}) or {}
    n_pass = int(status_counts.get("pass", 0))
    n_partial = int(status_counts.get("partial", 0))
    n_fail = int(status_counts.get("fail", 0))
    mean_reward = results.get("mean_reward", 0.0)
    flaky_count = int(results.get("flaky_count", 0))
    agg = results.get("aggregation", "worst")
    reps = int(results.get("repetitions", 1))

    lines.append(f"## Eval suite: `{results.get('suite', '?')}`")
    lines.append("")
    lines.append(
        f"- **Tasks:** {task_count} · **Repetitions:** {reps}× ({agg}-of-N)"
    )
    lines.append(
        f"- **Pass rate:** {n_pass}/{task_count} "
        f"({_pct(n_pass, task_count)}%) · partial {n_partial} · fail {n_fail}"
    )
    lines.append(f"- **Mean reward:** {mean_reward}")
    # Cost == quota draw: total orchestration attempts + tokens (NOT dollars).
    total_attempts = sum(int(t.get("attempts", 0)) for t in results.get("tasks", []))
    lines.append(
        f"- **Quota (cost):** {total_attempts} orchestration attempts · "
        f"{int(results.get('total_tokens', 0))} tokens · "
        f"{int(results.get('total_turns', 0))} turns"
    )
    if flaky_count:
        lines.append(f"- **Flaky tasks:** {flaky_count} (reward unstable across reps)")
    if results.get("duration_s") is not None:
        lines.append(f"- **Duration:** {results.get('duration_s')}s")
    lines.append(f"- **Timestamp:** {results.get('timestamp', '')}")
    lines.append("")

    # Harbor-style table: reward + status + cost (quota) + compute + flaky.
    lines.append("| Task | Category | Reward | Status | Attempts | Tokens | Turns | Flaky |")
    lines.append("|---|---|---:|---|---:|---:|---:|---|")
    for t in results.get("tasks", []):
        status = _STATUS_GLYPH.get(t.get("status", ""), t.get("status", "?"))
        flaky = "FLAKY" if t.get("flaky") else ""
        lines.append(
            f"| `{t.get('id', '?')}` | {t.get('category', '')} "
            f"| {t.get('reward', 0.0)} | {status} "
            f"| {int(t.get('attempts', 0))} | {int(t.get('tokens', 0))} "
            f"| {int(t.get('turns', 0))} | {flaky} |"
        )
    return "\n".join(lines)


def emit_json(results: Dict[str, Any]) -> str:
    return json.dumps(results, indent=2, ensure_ascii=False)


def main(argv: List[str]) -> int:
    if not argv or argv[0] in ("-h", "--help"):
        print("usage: reporter.py results.json [--json]", file=sys.stderr)
        return 2
    path = Path(argv[0])
    try:
        results = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"ERROR: could not read results JSON: {e}", file=sys.stderr)
        return 2
    if "--json" in argv[1:]:
        print(emit_json(results))
    else:
        print(emit_markdown(results))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
