#!/usr/bin/env python3
"""cc-native-usage-pull.py — native subagent token-usage rollup (PLAN-178 W1.2-1).

Reads the HARNESS-NATIVE per-agent transcripts under

    ~/.claude/projects/<cwd-slug>/<SESSION-UUID>/subagents/

and aggregates token usage PER AGENT for the AC-3 dual-print (native source vs
audit-log). The source fingerprint was measured live in
``.claude/plans/PLAN-178/w12-native-cost-probe.md`` (S1-S2):

  rails — the category comes from the PATH SHAPE, never from ``taskKind``
  (which cannot distinguish the rails on this corpus; probe S3 blocker):
    task:     ``<SESSION-UUID>/subagents/agent-a*.jsonl``                 (+ paired ``.meta.json``)
    workflow: ``<SESSION-UUID>/subagents/workflows/wf_*/agent-a*.jsonl``  (+ paired ``.meta.json``)
    journal:  ``subagents/workflows/wf_*/journal.jsonl`` — per-workflow bookkeeping,
              NOT an agent transcript; NEVER enters the rollup (counted in
              ``skipped.journal_excluded`` so the exclusion stays observable).

  meta invariants (416/416 measured): ``agentType`` + ``spawnDepth``. ``model``
  is ABSENT from every workflow-path meta (338/338) — for those agents the model
  falls back to the first ``message.model`` observed in the transcript itself
  (probe S6.5). A transcript with NO paired meta (1 in today's corpus, probe
  S1.2) is KEPT: rail inferred from the path, ``agentType`` = ``"unknown-no-meta"``.

  tokens live in ``message.usage`` per transcript line:
  ``input_tokens`` / ``output_tokens`` / ``cache_creation_input_tokens`` /
  ``cache_read_input_tokens`` (probe S1.5).

Doctrine (mirrors cc-analytics-pull.py + CLAUDE.md section 4 fail-open-on-infra):
  - READ-ONLY snapshot-read of a LIVE corpus — concurrent sessions append while
    we read, so transcripts are parsed line-by-line with a per-line try/except
    (a truncated tail line lands in ``skipped.malformed_lines``, never fatal);
  - ZERO network — this module deliberately has no urllib/socket/requests;
  - fail-soft: every infrastructure failure exits 0 with a stderr breadcrumb.
    No session with ``subagents/`` (or root absent) means ``{"available": false,
    "dormant": true}`` on stdout, exit 0. An unreadable/malformed meta skips
    THAT agent and counts it in ``skipped.meta_unreadable``.

Non-goals here (probe S5/S6.6): NO plan-id resolution — the native source has
no plan field in any of the 416 metas, and this script must not become the 6th
divergent plan-id resolver. The rollup is per-session; the session-to-plan join
is the caller's problem (resolver #1, parameterized, documented N>=2 caveat).

Stdlib only - Python >= 3.9 - no _lib imports (standalone, like cc-analytics-pull.py).
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

_SCHEMA = "cc-native-usage/v1"
_RAILS = ("task", "workflow")
# rollup name -> message.usage key (probe S2 usage_chaves)
_TOKEN_FIELDS = (
    ("input", "input_tokens"),
    ("output", "output_tokens"),
    ("cache_creation", "cache_creation_input_tokens"),
    ("cache_read", "cache_read_input_tokens"),
)
_JOURNAL_BASENAME = "journal.jsonl"


def project_slug(project_dir: str) -> str:
    """<cwd-slug> = absolute project path with '/' replaced by '-' (probe S1.1)."""
    return os.path.abspath(project_dir).replace("/", "-")


def native_root(project_dir: Optional[str] = None, home: Optional[str] = None) -> str:
    """~/.claude/projects/<cwd-slug> — derived from $CLAUDE_PROJECT_DIR + $HOME."""
    pd = project_dir or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    base = home or os.path.expanduser("~")
    return os.path.join(base, ".claude", "projects", project_slug(pd))


def _empty_tokens() -> Dict[str, int]:
    return {name: 0 for name, _ in _TOKEN_FIELDS}


def _as_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def load_meta(path: str) -> Tuple[Optional[Dict], str]:
    """(meta, status) with status in {"ok", "missing", "unreadable"}. Never raises."""
    if not os.path.exists(path):
        return None, "missing"
    try:
        with open(path, "r", encoding="utf-8") as fh:
            obj = json.load(fh)
    except (OSError, ValueError):
        return None, "unreadable"
    if not isinstance(obj, dict):
        return None, "unreadable"
    return obj, "ok"


def parse_transcript(path: str) -> Tuple[Dict[str, int], int, int, Optional[str], int]:
    """Sum ``message.usage`` token fields line-by-line (snapshot-read of a
    possibly still-growing file). Returns (tokens, usage_events,
    malformed_lines, model, usage_no_core) — model = first ``message.model``
    observed, the workflow-path fallback of probe S6.5; usage_no_core counts
    ``message.usage`` dicts carrying NEITHER ``input_tokens`` NOR
    ``output_tokens`` (fingerprint drift sonda — codex S306 P1 cure: such a
    line is schema drift, never a zero-token event). May raise OSError
    (caller counts it)."""
    tokens = _empty_tokens()
    events = 0
    malformed = 0
    usage_no_core = 0
    model: Optional[str] = None
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except ValueError:
                malformed += 1        # truncated tail of a live file — skip, never fatal
                continue
            if not isinstance(obj, dict):
                malformed += 1
                continue
            msg = obj.get("message")
            if not isinstance(msg, dict):
                continue
            if model is None and isinstance(msg.get("model"), str) and msg.get("model"):
                model = msg["model"]
            usage = msg.get("usage")
            if not isinstance(usage, dict):
                continue
            if ("input_tokens" not in usage) and ("output_tokens" not in usage):
                usage_no_core += 1    # drift sonda: valid JSON, wrong shape
                continue
            events += 1
            for name, key in _TOKEN_FIELDS:
                tokens[name] += _as_int(usage.get(key))
    return tokens, events, malformed, model, usage_no_core


def _agent_record(session_id: str, rail: str, tpath: str,
                  skipped: Dict[str, int], drift: Dict[str, int]) -> Optional[Dict]:
    """One rollup record per transcript, or None when the agent is skipped."""
    meta_path = tpath[: -len(".jsonl")] + ".meta.json"
    meta, status = load_meta(meta_path)
    if status == "unreadable":
        skipped["meta_unreadable"] += 1
        sys.stderr.write("cc-native-usage: unreadable meta — agent skipped: %s\n" % meta_path)
        return None
    try:
        tokens, events, malformed, transcript_model, no_core = parse_transcript(tpath)
    except OSError as e:
        skipped["transcript_unreadable"] += 1
        sys.stderr.write("cc-native-usage: unreadable transcript — agent skipped: %s (%s)\n"
                         % (tpath, e))
        return None
    skipped["malformed_lines"] += malformed
    drift["usage_missing_core_keys"] += no_core
    if meta is None:                  # probe S1.2 edge: transcript with no paired meta
        agent_type = "unknown-no-meta"
        meta_model = None             # type: Optional[str]
    else:
        # Fingerprint invariants (416/416 measured): agentType + spawnDepth.
        # A meta that parses but lacks either is schema DRIFT (sonda), not a
        # normal shape variant — counted so collect() can degrade.
        if "agentType" not in meta or "spawnDepth" not in meta:
            drift["meta_invariant_missing"] += 1
        raw_type = meta.get("agentType")
        agent_type = raw_type if isinstance(raw_type, str) and raw_type else "unknown"
        raw_model = meta.get("model")
        meta_model = raw_model if isinstance(raw_model, str) and raw_model else None
    record = {
        "session_id": session_id,
        "rail": rail,
        "agent": os.path.basename(tpath)[: -len(".jsonl")],
        "agentType": agent_type,
        # meta model wins; the transcript message.model is the ONLY route for
        # the workflow path, whose meta never carries model (probe S1.3).
        "model": meta_model or transcript_model,
        "tokens": tokens,
        "usage_events": events,
    }
    if rail == "workflow":
        record["workflow_id"] = os.path.basename(os.path.dirname(tpath))
    if meta is not None and isinstance(meta.get("name"), str):
        record["name"] = meta["name"]
    return record


def _dormant(root: str, reason: str) -> Dict:
    return {"schema": _SCHEMA, "available": False, "dormant": True,
            "reason": reason, "root": root}


def collect(root: str) -> Dict:
    """Walk the native source once (snapshot-read) -> the full rollup payload."""
    root = os.path.expanduser(root)
    if not os.path.isdir(root):
        return _dormant(root, "native projects root absent")
    sessions = sorted(
        e for e in os.listdir(root) if os.path.isdir(os.path.join(root, e)))
    with_subagents = [
        s for s in sessions if os.path.isdir(os.path.join(root, s, "subagents"))]
    if not with_subagents:
        return _dormant(
            root, "no session has subagents/ (%d session dirs scanned)" % len(sessions))
    agents: List[Dict] = []
    skipped = {"meta_unreadable": 0, "transcript_unreadable": 0,
               "malformed_lines": 0, "journal_excluded": 0}
    drift = {"usage_missing_core_keys": 0, "meta_invariant_missing": 0,
             "path_shape_zero_glob": 0}
    transcripts_found = 0
    for sid in with_subagents:
        sub = os.path.join(root, sid, "subagents")
        # journal.jsonl is per-workflow bookkeeping with NO meta — excluded from
        # the rollup by contract (probe S6.2); counted so the exclusion is visible.
        skipped["journal_excluded"] += len(
            glob.glob(os.path.join(sub, "workflows", "wf_*", _JOURNAL_BASENAME)))
        rail_globs = (
            ("task", os.path.join(sub, "agent-a*.jsonl")),
            ("workflow", os.path.join(sub, "workflows", "wf_*", "agent-a*.jsonl")),
        )
        for rail, pattern in rail_globs:
            for tpath in sorted(glob.glob(pattern)):
                if os.path.basename(tpath) == _JOURNAL_BASENAME:
                    continue          # defense-in-depth; the globs cannot match it
                transcripts_found += 1
                record = _agent_record(sid, rail, tpath, skipped, drift)
                if record is not None:
                    agents.append(record)
    totals = {key: {"agents": 0, "usage_events": 0, "tokens": _empty_tokens()}
              for key in _RAILS + ("all",)}
    for record in agents:
        for bucket in (totals[record["rail"]], totals["all"]):
            bucket["agents"] += 1
            bucket["usage_events"] += record["usage_events"]
            for name in bucket["tokens"]:
                bucket["tokens"][name] += record["tokens"][name]
    # Path-shape sonda (codex S306 r2 P2 cure): an os.walk sweep counts every
    # agent transcript ANYWHERE under subagents/ — if it sees MORE than the
    # two known globs matched, the harness moved the layout (e.g. a new
    # directory level) and the difference is invisible to the rollup. A
    # journal-only workflow (benign, covered by tests) trips nothing: the
    # walk ignores journals and non-agent files.
    walk_seen = 0
    for sid in with_subagents:
        sub = os.path.join(root, sid, "subagents")
        for dirpath, _dirs, files in os.walk(sub):
            for fn in files:
                if (fn.startswith("agent-a") and fn.endswith(".jsonl")
                        and fn != _JOURNAL_BASENAME):
                    walk_seen += 1
    if walk_seen > transcripts_found:
        drift["path_shape_zero_glob"] = walk_seen - transcripts_found
    # Fingerprint drift sondas (probe S2 / codex S306 P1 cure): ANY hit means
    # the harness schema moved under us — the payload degrades to
    # available:false so consumers fall back to the audit-log, but agents/
    # totals/drift stay in the payload for forensics (nothing silenced).
    drifted = any(v > 0 for v in drift.values())
    if drifted:
        sys.stderr.write(
            "cc-native-usage: schema drift detected (%s) — degrading to "
            "available:false; consumers must fall back to the audit-log\n"
            % json.dumps(drift))
    return {
        "schema": _SCHEMA,
        "available": not drifted,
        "dormant": False,
        "drift": drift,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "root": root,
        "sessions_scanned": len(sessions),
        "sessions_with_subagents": len(with_subagents),
        "agents": agents,
        "totals": totals,
        "skipped": skipped,
    }


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Native subagent token-usage rollup (PLAN-178 W1.2-1) — read-only, "
                    "ZERO network. Reads ~/.claude/projects/<cwd-slug>/<SESSION-UUID>/"
                    "subagents/ and prints a per-agent JSON rollup on stdout; dormant "
                    "(exit 0) when the native source is absent.")
    ap.add_argument("--root", default=None,
                    help="override the native projects root (default: derived from "
                         "$CLAUDE_PROJECT_DIR + $HOME per the probe S1.1 fingerprint)")
    ap.add_argument("--compact", action="store_true", help="single-line JSON output")
    args = ap.parse_args(argv)
    # Kill-switch (W1.2-5b, env-inventory.json): structurally off, exit 0.
    if os.environ.get("CEO_NATIVE_COST_DISABLE", "") == "1":
        print(json.dumps({"schema": _SCHEMA, "available": False,
                          "disabled": True}, indent=2))
        return 0
    try:
        root = os.path.expanduser(args.root) if args.root else native_root()
        payload = collect(root)
    except Exception as e:            # infra fail-soft by contract (CLAUDE.md section 4)
        sys.stderr.write("cc-native-usage: infra error — %s\n" % e)
        print(json.dumps({"schema": _SCHEMA, "available": False,
                          "dormant": False, "infra_error": True}))
        return 0
    print(json.dumps(payload, indent=None if args.compact else 2, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
