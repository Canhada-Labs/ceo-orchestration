#!/usr/bin/env python3
"""session-resume.py — Project a "how to continue this plan" prompt.

PLAN-011 Phase 11 (VP Engineering). Companion to ``session-graph-build.py``.

The resume projection is a **read-only** view derived from the session
graph (which is itself derived from audit-log + git). No new state is
written. No audit events are emitted by this script. The output is a
prompt fragment the CEO can feed to a fresh Claude Code session to
reconstruct context for a plan that was interrupted.

Usage::

    session-resume.py --plan PLAN-010
    session-resume.py --plan PLAN-010 --json

Kill-switch::

    CEO_SOTA_DISABLE=1 session-resume.py --plan PLAN-010
    # -> exit 0, no output

Behavior
--------
1. Locate the most recent graph under
   ``$HOME/.claude/projects/<proj>/session-graphs/<plan>-<ts>.json*``.
   - If the newest matching graph is **encrypted** (``.age`` or ``.gpg``)
     AND the user has the matching key, decrypt in memory.
   - If no decryptable graph exists OR the newest is older than 24h,
     rebuild in-memory via ``session-graph-build.build_graph(...)``.
2. Project the graph into a human-readable (or JSON) "resume" view.

Stdlib only; Python 3.9+. Fail-safe on missing inputs — emits a
user-friendly message and returns exit code 3 (not a traceback).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

# Import sibling module. The hyphen in filename forces importlib.
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location(
    "session_graph_build", _SCRIPTS_DIR / "session-graph-build.py"
)
_sgb = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
assert _spec.loader is not None
_spec.loader.exec_module(_sgb)  # type: ignore[union-attr]


_GRAPH_FILE_RE = re.compile(
    r"^(PLAN-\d{3})-(\d{8}T\d{6}Z)\.json(?:\.age|\.gpg|\.plain\.json)?$"
)
FRESH_GRAPH_WINDOW = timedelta(hours=24)


# ---------------------------------------------------------------------------
# Graph discovery + decryption
# ---------------------------------------------------------------------------


def _graph_dir() -> Path:
    return _sgb._default_graph_dir()


def _find_latest_graph(plan_id: str) -> Optional[Path]:
    """Return newest matching graph file, or None."""
    d = _graph_dir()
    if not d.is_dir():
        return None
    candidates: List[Tuple[str, Path]] = []
    for p in d.iterdir():
        m = _GRAPH_FILE_RE.match(p.name)
        if m and m.group(1) == plan_id:
            candidates.append((m.group(2), p))
    if not candidates:
        return None
    candidates.sort(reverse=True)
    return candidates[0][1]


def _graph_is_fresh(path: Path) -> bool:
    try:
        mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    except OSError:
        return False
    return (datetime.now(timezone.utc) - mtime) < FRESH_GRAPH_WINDOW


def _try_decrypt(path: Path) -> Optional[bytes]:
    """Return decrypted JSON bytes, or None if unable.

    Plaintext files pass through unchanged.
    """
    if path.suffix == ".age":
        if not shutil.which("age"):
            return None
        try:
            proc = subprocess.run(
                ["age", "-d", "-i",
                 str(Path(os.environ.get("HOME") or str(Path.home())) /
                     ".claude" / "age-identity.txt"),
                 str(path)],
                check=True,
                capture_output=True,
                timeout=30,
            )
            return proc.stdout
        except (subprocess.SubprocessError, FileNotFoundError, OSError):
            return None
    if path.suffix == ".gpg":
        if not shutil.which("gpg"):
            return None
        try:
            proc = subprocess.run(
                ["gpg", "--batch", "--yes", "--decrypt", str(path)],
                check=True,
                capture_output=True,
                timeout=30,
            )
            return proc.stdout
        except (subprocess.SubprocessError, FileNotFoundError, OSError):
            return None
    # Plaintext passthrough
    try:
        return path.read_bytes()
    except OSError:
        return None


def _load_graph_from_disk_or_build(
    plan_id: str,
    *,
    force_rebuild: bool = False,
) -> Tuple[Dict[str, Any], str]:
    """Return (graph, source) where source is 'disk:<path>' or 'live'."""
    if not force_rebuild:
        cached = _find_latest_graph(plan_id)
        if cached and _graph_is_fresh(cached):
            payload = _try_decrypt(cached)
            if payload is not None:
                try:
                    return json.loads(payload.decode("utf-8")), f"disk:{cached.name}"
                except (UnicodeDecodeError, json.JSONDecodeError):
                    pass
    # Rebuild in-memory. Default 30d window.
    graph = _sgb.build_graph(
        plan_id, since=timedelta(days=_sgb.DEFAULT_SINCE_DAYS)
    )
    return graph, "live"


# ---------------------------------------------------------------------------
# Projection
# ---------------------------------------------------------------------------


def _fmt_ts(ts: Optional[str]) -> str:
    if not ts:
        return "?"
    return ts


def _synthesize_next_action(graph: Dict[str, Any]) -> str:
    """Synthesize ONE line of "what the CEO should do next" from derived data.

    This is derived synthesis — we only describe what the data shows.
    """
    last = graph.get("last_phase_status", "unknown")
    status = graph.get("plan_status", "unknown")
    owner_actions = graph.get("owner_actions") or []
    deferred = graph.get("deferred") or []
    if status == "done":
        return (
            "Plan is DONE. Review Owner action items if present; otherwise "
            "no further work on this plan."
        )
    if owner_actions:
        return (
            f"Owner action required before continuing ({len(owner_actions)} "
            f"items listed above)."
        )
    if last.startswith("Phase "):
        m = re.match(r"Phase\s+(\d+):\s*(pending|done)", last)
        if m:
            n, marker = m.groups()
            if marker == "pending":
                return (
                    f"Resume Phase {n} (marked pending). Spawn the owning "
                    f"archetype per team.md routing."
                )
            nxt = int(n) + 1
            return (
                f"Phase {n} done. Advance to Phase {nxt} (check plan "
                f"markdown for scope)."
            )
    if deferred:
        return (
            f"No active phase marker. Review {len(deferred)} deferred items "
            f"and draft the next phase."
        )
    return "No resume signal available — open the plan markdown manually."


def project_resume(graph: Dict[str, Any]) -> Dict[str, Any]:
    """Return a structured resume projection (used by both text + json).

    Keys:
        plan_id, plan_title, plan_status, generated_at,
        last_commit {sha, subject, author_ts}, last_phase_status,
        open_deferred [str], owner_actions [str], next_action (str),
        session_count, event_count, commit_count
    """
    commits = graph.get("commits") or []
    last_commit: Optional[Dict[str, Any]] = commits[0] if commits else None
    return {
        "plan_id": graph.get("plan_id", ""),
        "plan_title": graph.get("plan_title", ""),
        "plan_status": graph.get("plan_status", "unknown"),
        "generated_at": graph.get("generated_at", ""),
        "last_commit": last_commit,
        "last_phase_status": graph.get("last_phase_status", "unknown"),
        "open_deferred": list(graph.get("deferred") or []),
        "owner_actions": list(graph.get("owner_actions") or []),
        "next_action": _synthesize_next_action(graph),
        "session_count": int(graph.get("session_count", 0)),
        "event_count": int(graph.get("event_count", 0)),
        "commit_count": int(graph.get("commit_count", 0)),
    }


def render_text(projection: Dict[str, Any], source: str) -> str:
    """Render a session-resume plan graph as human-readable text."""
    lines: List[str] = []
    plan_id = projection["plan_id"]
    title = projection.get("plan_title") or "(no title)"
    lines.append(f"# Resume {plan_id}")
    lines.append("")
    lines.append(f"Title: {title}")
    lines.append(f"Status: {projection['plan_status']}")
    lines.append(f"Graph source: {source}")
    lines.append(f"Generated at: {projection['generated_at'] or '?'}")
    lines.append("")
    lines.append("## Last commit")
    lc = projection["last_commit"]
    if lc:
        sha = lc.get("sha", "?")
        subj = lc.get("subject", "?")
        lines.append(f"{sha[:12]} — {subj}")
    else:
        lines.append("(no commits on this plan file)")
    lines.append("")
    lines.append("## Last phase")
    lines.append(projection["last_phase_status"])
    lines.append("")
    lines.append("## Open deferred")
    deferred = projection["open_deferred"]
    if deferred:
        for item in deferred:
            lines.append(f"- {item}")
    else:
        lines.append("(none)")
    lines.append("")
    lines.append("## Owner action items")
    oa = projection["owner_actions"]
    if oa:
        for item in oa:
            lines.append(f"- {item}")
    else:
        lines.append("(none)")
    lines.append("")
    lines.append("## Recommended next action (CEO)")
    lines.append(projection["next_action"])
    lines.append("")
    lines.append(
        f"(sessions={projection['session_count']} "
        f"events={projection['event_count']} "
        f"commits={projection['commit_count']})"
    )
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — resume a plan across sessions via its derived graph."""
    if _sgb.sota_disabled():
        return 0

    parser = argparse.ArgumentParser(
        prog="session-resume",
        description="Project a 'how to continue this plan' prompt.",
    )
    parser.add_argument("--plan", dest="plan_id", required=True, help="PLAN-NNN")
    parser.add_argument(
        "--json",
        dest="as_json",
        action="store_true",
        help="Machine-readable JSON output",
    )
    parser.add_argument(
        "--rebuild",
        action="store_true",
        help="Skip disk cache; always rebuild the graph in-memory",
    )

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0

    if not _sgb._PLAN_ID_RE.match(args.plan_id):
        sys.stderr.write(
            f"error: --plan must match PLAN-NNN (got {args.plan_id!r})\n"
        )
        return 2

    # Validate plan exists (user-friendly error, not a traceback).
    plan_file = _sgb._find_plan_file(args.plan_id)
    if plan_file is None:
        sys.stderr.write(
            f"error: plan {args.plan_id} not found under "
            f"{_sgb._plans_dir()} (run `ls .claude/plans/` to verify)\n"
        )
        return 3

    graph, source = _load_graph_from_disk_or_build(
        args.plan_id, force_rebuild=args.rebuild
    )
    projection = project_resume(graph)

    if args.as_json:
        sys.stdout.write(
            json.dumps(
                {"source": source, "projection": projection},
                indent=2,
                sort_keys=False,
            )
            + "\n"
        )
    else:
        sys.stdout.write(render_text(projection, source))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
