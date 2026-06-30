#!/usr/bin/env python3
"""summarize-benchmarks.py — convert a benchmark JSON result file into a
Markdown table suitable for $GITHUB_STEP_SUMMARY.

Usage:
    python3 summarize-benchmarks.py <results.json> [<results.json> ...]

Emits Markdown to stdout. Takes multiple files so the workflow can loop
over benchmark-results/*.json and capture the full summary in one pass.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def emit_one(path: Path) -> None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        print(f"### `{path.name}` — FAILED TO READ")
        print(f"- error: `{e}`")
        print("")
        return

    bench = data.get("benchmark", {})
    overall = data.get("overall", {})
    skill = bench.get("skill", "?")
    version = bench.get("version", "?")
    health = overall.get("health", "?")
    passed = overall.get("passed", 0)
    total = overall.get("total", 0)
    score = overall.get("score", 0)
    pct = int(score * 100) if isinstance(score, (int, float)) else 0

    print(f"### {skill} (v{version}) — {health}")
    print(f"- Passed: {passed} / {total} ({pct}%)")
    print(f"- Model: `{data.get('model', '?')}`")
    print(f"- Repetitions: {data.get('repetitions', '?')}× median")
    print("")
    print("| ID | Name | Score | Status | Type |")
    print("|---|---|---:|---|---|")
    for s in data.get("scenarios", []):
        sid = s.get("id", "?")
        name = s.get("name", "")
        median = s.get("median_score", 0)
        status = "PASS" if s.get("passed") else "FAIL"
        stype = "control" if s.get("control") else "positive"
        print(f"| `{sid}` | {name} | {median} | {status} | {stype} |")
    print("")


def main(argv: list) -> int:
    if not argv:
        print("Usage: summarize-benchmarks.py <results.json> [...]", file=sys.stderr)
        return 2
    print("## Skill benchmark summary")
    print("")
    for arg in argv:
        path = Path(arg)
        if not path.is_file():
            print(f"### `{path.name}` — not found")
            print("")
            continue
        emit_one(path)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
