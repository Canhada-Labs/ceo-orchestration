#!/usr/bin/env python3
"""benchmarks/replay.py — deterministic spawn-sequence replay (PLAN-020 Phase 6).

Replays a captured spawn sequence (e.g. PLAN-019 Phase 2 Wave 2A) with
the Anthropic API mocked. Measures token costs + cache amortization +
spawn-prompt deltas between rails (custom inline vs native reference).

Provides the **A4 acceptance** signal for PLAN-020 Phase 6 §6 Sub-target
"Spawn-prompt tokens delta ≥ 20% reduction on reference rail."

## Modes

- `--rail inline`: replay all spawns as `## SKILL CONTENT` inline
- `--rail reference`: replay all spawns as `## SKILL REFERENCE`
- `--rail both`: replay both, emit comparison report

## Inputs

`replay-fixtures/<name>.jsonl` — one JSON object per line:

    {"spawn_id": "...", "archetype": "...", "task": "...", "skill": "..."}

## Outputs

JSON to stdout (or to `--output` path):

    {
      "fixture": "plan-019-wave-2a.jsonl",
      "n_spawns": 12,
      "rail": "both",
      "results": {
        "inline": {"total_tokens": ..., "avg_per_spawn": ...},
        "reference": {"total_tokens": ..., "avg_per_spawn": ...},
        "delta_pct": ...
      }
    }

## PLAN-133 C2 — spawn→tool-call JSON-stream record/playback

A second, hermetic structural-equality convention (NOT a parallel oracle —
the same module, the same canonicalization discipline as
`replay-session.canonical_payload_hash`). Records a normalized golden for a
captured spawn→tool-call JSON stream and plays a candidate stream back
against it, asserting STRUCTURAL equality (volatile fields — `ts`,
`session_id`, `tokens_*`, `duration_ms`, `request_id`, `cost_*`, `pid`,
`latency_ms` — are dropped before hashing, so two runs that differ only in
wall-clock/token telemetry compare equal). $0, no Anthropic client.

    python3 benchmarks/replay.py record   <stream.jsonl> --golden <golden.json>
    python3 benchmarks/replay.py playback <stream.jsonl> --golden <golden.json>

`playback` exits 0 on structural match, 2 on divergence (emits a
deterministic diff), 1 on infra error (fixture/golden missing). The
record/playback behavior is OPT-IN via the subcommand — the legacy
top-level `replay.py <fixture>` invocation (the rail benchmark) is
unchanged and remains the default when no subcommand is given.

## Stdlib only. No Anthropic SDK dependency.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


REPO_ROOT = Path(
    os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
).resolve()


# ---------------------------------------------------------------------------
# PLAN-133 C2 — spawn→tool-call JSON-stream record/playback
#
# Volatile fields that MUST be dropped before structural comparison. Mirrors
# the convention in `.claude/scripts/replay/replay-session.py`
# (canonical_payload_hash drops ts/session_id/tokens_*/duration_ms) so the
# two harnesses share ONE golden discipline rather than diverging.
# ---------------------------------------------------------------------------
_VOLATILE_KEYS = frozenset(
    {
        "ts",
        "timestamp",
        "session_id",
        "request_id",
        "requestId",
        "message_id",
        "tokens_in",
        "tokens_out",
        "tokens_total",
        "duration_ms",
        "latency_ms",
        "cost_usd",
        "cost_usd_cents",
        "pid",
        "hostname",
        "uuid",
        "id",
    }
)

STREAM_SCHEMA = "benchmarks-replay-stream.v1"


def estimate_tokens(text: str) -> int:
    """Rough heuristic: 1 token ~= 4 chars (English-Portuguese mix).

    Replace with Anthropic tokenizer counts when audit_log v2.7
    cache-header capture lands in production data.
    """
    return max(1, len(text) // 4)


def load_fixture(path: Path) -> List[Dict]:
    """Load JSONL spawn fixture. Each line is one spawn entry."""
    if not path.is_file():
        raise FileNotFoundError(f"Fixture not found: {path}")
    entries = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError as exc:
            print(
                f"WARN: skipping malformed line: {exc}", file=sys.stderr
            )
            continue
    return entries


def build_inline_prompt(entry: Dict) -> str:
    """Synthesize a Format A inline spawn prompt from fixture entry."""
    skill_path = (
        REPO_ROOT / ".claude" / "skills" / "core" / entry["skill"] / "SKILL.md"
    )
    persona = (
        f"PERSONA: {entry['archetype']}\n"
        f"BACKGROUND: stub for replay\n"
        f"FOCUS: {entry.get('focus', 'general')}\n"
    )
    skill_body = ""
    if skill_path.is_file():
        skill_body = skill_path.read_text(encoding="utf-8")
    prompt = (
        f"## AGENT PROFILE\n{persona}\n\n"
        f"## SKILL CONTENT\nSKILL: {entry['skill']}\n\n{skill_body}\n\n"
        f"## FILE ASSIGNMENT\n- CAN edit: {entry.get('files', '...')}\n\n"
        f"## TASK\n{entry['task']}\n"
    )
    return prompt


def build_reference_prompt(entry: Dict) -> str:
    """Synthesize a Format B reference spawn prompt from fixture entry."""
    skill_path = (
        REPO_ROOT / ".claude" / "skills" / "core" / entry["skill"] / "SKILL.md"
    )
    persona = (
        f"PERSONA: {entry['archetype']}\n"
        f"BACKGROUND: stub for replay\n"
        f"FOCUS: {entry.get('focus', 'general')}\n"
    )
    skill_hash = ""
    if skill_path.is_file():
        skill_hash = hashlib.sha256(skill_path.read_bytes()).hexdigest()
    skill_rel = f".claude/skills/core/{entry['skill']}/SKILL.md"
    prompt = (
        f"## AGENT PROFILE\n{persona}\n\n"
        f"## SKILL REFERENCE\n\n"
        f"@{skill_rel} sha256={skill_hash}\n\n"
        f"(Sub-agent will Read SKILL.md after spawn.)\n\n"
        f"## FILE ASSIGNMENT\n- CAN edit: {entry.get('files', '...')}\n\n"
        f"## TASK\n{entry['task']}\n"
    )
    return prompt


def replay_rail(
    entries: List[Dict],
    builder,
    rail_name: str,
) -> Dict:
    total_tokens = 0
    per_spawn_tokens = []
    per_spawn_bytes = []
    for entry in entries:
        prompt = builder(entry)
        token_est = estimate_tokens(prompt)
        per_spawn_tokens.append(token_est)
        per_spawn_bytes.append(len(prompt))
        total_tokens += token_est
    n = len(entries)
    return {
        "rail": rail_name,
        "n_spawns": n,
        "total_tokens_estimate": total_tokens,
        "avg_per_spawn_tokens": (total_tokens // n) if n else 0,
        "min_spawn_tokens": min(per_spawn_tokens) if n else 0,
        "max_spawn_tokens": max(per_spawn_tokens) if n else 0,
        "total_bytes": sum(per_spawn_bytes),
        "avg_per_spawn_bytes": (sum(per_spawn_bytes) // n) if n else 0,
    }


# ---------------------------------------------------------------------------
# PLAN-133 C2 — record/playback core
# ---------------------------------------------------------------------------


def canonical_event(event: Any) -> Any:
    """Strip volatile fields recursively + return a deterministically-ordered
    structure suitable for stable hashing.

    Dicts: drop `_VOLATILE_KEYS`, recurse into the rest, sort keys.
    Lists: recurse element-wise (ORDER IS PRESERVED — a spawn→tool-call
    stream's ordering is semantically load-bearing).
    Scalars: returned as-is.
    """
    if isinstance(event, dict):
        out = {}
        for key in sorted(event.keys()):
            if key in _VOLATILE_KEYS:
                continue
            out[key] = canonical_event(event[key])
        return out
    if isinstance(event, list):
        return [canonical_event(item) for item in event]
    return event


def canonical_stream(events: List[Any]) -> List[Any]:
    """Normalize a full spawn→tool-call stream (list of events).

    Event ORDER is preserved (the sequence is the contract); only the
    fields inside each event are canonicalized + volatile-stripped.
    """
    return [canonical_event(ev) for ev in events]


def stream_digest(events: List[Any]) -> str:
    """Deterministic SHA-256 over the canonical (volatile-stripped) stream.

    Uses sort_keys + compact separators so the digest is stable across
    Python versions, PYTHONHASHSEED, and dict-insertion order.
    """
    canon = canonical_stream(events)
    blob = json.dumps(
        canon, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    )
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def build_golden(events: List[Any]) -> Dict[str, Any]:
    """Build the golden record for a stream: schema + digest + canonical
    body + count. The canonical body is embedded so a reviewer can diff a
    golden by eye and so playback can produce a structural diff offline."""
    canon = canonical_stream(events)
    return {
        "schema": STREAM_SCHEMA,
        "n_events": len(events),
        "stream_digest": stream_digest(events),
        "canonical_stream": canon,
    }


def _first_divergence(
    golden_canon: List[Any], candidate_canon: List[Any]
) -> Optional[Dict[str, Any]]:
    """Return a deterministic description of the FIRST structural divergence
    between two canonical streams, or None if identical.

    Compared on the compact-JSON serialization of each event so nested
    dict/list order differences surface deterministically.
    """
    if len(golden_canon) != len(candidate_canon):
        return {
            "kind": "length_mismatch",
            "golden_n_events": len(golden_canon),
            "candidate_n_events": len(candidate_canon),
        }
    for idx, (g_ev, c_ev) in enumerate(zip(golden_canon, candidate_canon)):
        g_blob = json.dumps(g_ev, sort_keys=True, separators=(",", ":"))
        c_blob = json.dumps(c_ev, sort_keys=True, separators=(",", ":"))
        if g_blob != c_blob:
            return {
                "kind": "event_mismatch",
                "index": idx,
                "golden_event": g_ev,
                "candidate_event": c_ev,
            }
    return None


def playback(
    candidate_events: List[Any], golden: Dict[str, Any]
) -> Dict[str, Any]:
    """Compare a candidate stream against a golden record. Pure: no I/O.

    Returns a deterministic report dict with `match` (bool), the two
    digests, and — on mismatch — the first structural divergence.
    """
    cand_digest = stream_digest(candidate_events)
    golden_digest = golden.get("stream_digest", "")
    match = cand_digest == golden_digest
    report: Dict[str, Any] = {
        "schema": STREAM_SCHEMA,
        "match": match,
        "golden_digest": golden_digest,
        "candidate_digest": cand_digest,
        "n_events": len(candidate_events),
    }
    if not match:
        golden_canon = golden.get("canonical_stream")
        if golden_canon is None:
            # Golden has no embedded body (digest-only) — cannot diff, but the
            # digest mismatch is authoritative.
            report["divergence"] = {"kind": "digest_only_golden"}
        else:
            report["divergence"] = _first_divergence(
                golden_canon, canonical_stream(candidate_events)
            )
    return report


def _cmd_record(args: argparse.Namespace) -> int:
    """`record` subcommand: write the golden for a stream fixture."""
    stream_path = Path(args.stream)
    if not stream_path.is_absolute():
        stream_path = REPO_ROOT / args.stream
    try:
        events = load_fixture(stream_path)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    golden = build_golden(events)
    golden_text = json.dumps(golden, indent=2, sort_keys=True) + "\n"
    golden_path = Path(args.golden)
    if not golden_path.is_absolute():
        golden_path = REPO_ROOT / args.golden
    golden_path.parent.mkdir(parents=True, exist_ok=True)
    golden_path.write_text(golden_text, encoding="utf-8")
    print(
        f"OK: recorded golden {args.golden} "
        f"({golden['n_events']} events, digest {golden['stream_digest'][:12]}…)"
    )
    return 0


def _cmd_playback(args: argparse.Namespace) -> int:
    """`playback` subcommand: assert structural equality vs golden.

    Exit 0 = match, 2 = structural divergence, 1 = infra error (fail-open:
    a missing fixture/golden is an infra fault, NOT a test failure).
    """
    stream_path = Path(args.stream)
    if not stream_path.is_absolute():
        stream_path = REPO_ROOT / args.stream
    golden_path = Path(args.golden)
    if not golden_path.is_absolute():
        golden_path = REPO_ROOT / args.golden
    try:
        events = load_fixture(stream_path)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if not golden_path.is_file():
        print(f"ERROR: golden not found: {golden_path}", file=sys.stderr)
        return 1
    try:
        golden = json.loads(golden_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"ERROR: malformed golden: {exc}", file=sys.stderr)
        return 1
    report = playback(events, golden)
    output_text = json.dumps(report, indent=2, sort_keys=True)
    if args.output:
        out_path = Path(args.output)
        out_path.write_text(output_text + "\n", encoding="utf-8")
        print(f"OK: wrote {args.output}")
    else:
        sys.stdout.write(output_text + "\n")
    return 0 if report["match"] else 2


def main() -> int:
    # PLAN-133 C2: a subcommand prefix (`record`/`playback`) selects the
    # stream record/playback path; otherwise the legacy rail-benchmark CLI
    # runs unchanged (the first positional is a fixture path).
    if len(sys.argv) > 1 and sys.argv[1] in ("record", "playback"):
        return _main_stream(sys.argv[1:])
    return _main_rail()


def _main_stream(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(
        prog="replay.py",
        description="PLAN-133 C2 spawn→tool-call JSON-stream record/playback",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    rec = sub.add_parser("record", help="record a golden for a stream fixture")
    rec.add_argument("stream", help="path to stream JSONL fixture")
    rec.add_argument(
        "--golden", required=True, help="path to write the golden JSON"
    )

    pb = sub.add_parser("playback", help="assert structural equality vs golden")
    pb.add_argument("stream", help="path to candidate stream JSONL fixture")
    pb.add_argument("--golden", required=True, help="path to the golden JSON")
    pb.add_argument(
        "--output", default=None, help="optional report output path"
    )

    args = parser.parse_args(argv)
    if args.cmd == "record":
        return _cmd_record(args)
    return _cmd_playback(args)


def _main_rail() -> int:
    parser = argparse.ArgumentParser(
        description="PLAN-020 Phase 6 spawn replay benchmark"
    )
    parser.add_argument(
        "fixture",
        type=str,
        help="Path to JSONL fixture file (e.g. replay-fixtures/plan-019-wave-2a.jsonl)",
    )
    parser.add_argument(
        "--rail",
        choices=["inline", "reference", "both"],
        default="both",
        help="Which spawn format to replay (default: both)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Optional output path (default: stdout)",
    )
    args = parser.parse_args()

    fixture_path = Path(args.fixture)
    if not fixture_path.is_absolute():
        fixture_path = REPO_ROOT / args.fixture

    try:
        entries = load_fixture(fixture_path)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    result = {
        "schema": "benchmarks-replay.v1",
        "fixture": str(fixture_path.relative_to(REPO_ROOT)),
        "n_spawns": len(entries),
        "rail": args.rail,
        "results": {},
    }

    if args.rail in ("inline", "both"):
        result["results"]["inline"] = replay_rail(
            entries, build_inline_prompt, "inline"
        )

    if args.rail in ("reference", "both"):
        result["results"]["reference"] = replay_rail(
            entries, build_reference_prompt, "reference"
        )

    if args.rail == "both":
        inline_total = result["results"]["inline"]["total_tokens_estimate"]
        ref_total = result["results"]["reference"]["total_tokens_estimate"]
        if inline_total > 0:
            delta_pct = round(
                (inline_total - ref_total) * 100.0 / inline_total, 2
            )
            result["delta_pct_savings"] = delta_pct
            result["a4_acceptance_target"] = 20.0
            result["a4_acceptance_pass"] = delta_pct >= 20.0

    output_text = json.dumps(result, indent=2)
    if args.output:
        Path(args.output).write_text(output_text + "\n", encoding="utf-8")
        print(f"OK: wrote {args.output}")
    else:
        sys.stdout.write(output_text + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
