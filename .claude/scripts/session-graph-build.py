#!/usr/bin/env python3
"""session-graph-build.py — Build a strictly-derived session graph for a plan.

PLAN-011 Phase 11 (VP Engineering). See ADR-038 + SPEC/v1/session-graph.schema.md.

The session graph is a **derived view** over the audit log + git history.
It is NEVER a new source of truth. Every field surfaced in the graph has
a traceable source event in ``audit-log.jsonl`` (or a commit in git),
and the mapping is enumerated in SPEC/v1/session-graph.schema.md §Reverse
map.

Usage::

    # one plan, encrypted by default
    session-graph-build.py --plan PLAN-010

    # all plans with status != done
    session-graph-build.py --all-active

    # plaintext (debug only; emits WARNING when no key available)
    session-graph-build.py --plan PLAN-010 --no-encrypt

    # custom window
    session-graph-build.py --plan PLAN-010 --since 7d

Env kill-switch (M3 consensus, S4)::

    CEO_SOTA_DISABLE=1 session-graph-build.py --plan PLAN-010
    # -> exits 0 with no output

Encryption (M3 consensus)::

    - If ``age`` is on PATH AND ``~/.claude/age-recipient.txt`` exists,
      encrypt with age.
    - Else if ``gpg`` is on PATH AND ``$CEO_GPG_FINGERPRINT`` is set,
      encrypt with gpg (``--encrypt --recipient "$CEO_GPG_FINGERPRINT"``).
    - Else WARN on stderr and fall back to plaintext. Never block.

Retention
---------
Default ``--since`` window is **30d** (M3 consensus — session graph is
not an archival tool; long-window analytics ride on the raw audit log).
Set ``--since forever`` to disable the filter.

Stdlib only; Python 3.9+; fail-safe on missing inputs (prints to stderr
and exits non-zero only on **invalid args**, never on missing data).
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
from typing import Any, Dict, Iterable, List, Optional, Tuple


# Resolve _lib/audit_emit + _lib/plan_frontmatter
_SCRIPTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = _SCRIPTS_DIR.parent.parent
HOOKS_DIR = REPO_ROOT / ".claude" / "hooks"
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))

from _lib import audit_emit as _audit_emit  # noqa: E402
from _lib import plan_frontmatter as _frontmatter  # noqa: E402


DEFAULT_SINCE_DAYS = 30  # M3 consensus
_PLAN_FILE_RE = re.compile(r"^PLAN-(\d{3})(?:-[a-z0-9-]+)?\.md$")
_PLAN_ID_RE = re.compile(r"^PLAN-\d{3}$")

# Graph schema version — bumped on any field addition/removal.
GRAPH_SCHEMA_VERSION = "1.0.0"


# ---------------------------------------------------------------------------
# Env helpers
# ---------------------------------------------------------------------------


def sota_disabled() -> bool:
    """Return True if ``CEO_SOTA_DISABLE=1`` is set (S4 kill-switch)."""
    return os.environ.get("CEO_SOTA_DISABLE", "").strip() == "1"


def _plans_dir() -> Path:
    env = os.environ.get("CEO_PLANS_DIR")
    if env:
        return Path(env)
    return REPO_ROOT / ".claude" / "plans"


def _default_graph_dir() -> Path:
    """Default ``$HOME/.claude/projects/<proj>/session-graphs/``."""
    override = os.environ.get("CEO_SESSION_GRAPH_DIR")
    if override:
        return Path(override)
    home = Path(os.environ.get("HOME") or str(Path.home()))
    project = os.environ.get("CEO_PROJECT_NAME") or "ceo-orchestration"
    return home / ".claude" / "projects" / project / "session-graphs"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _ts_compact() -> str:
    return _utc_now().strftime("%Y%m%dT%H%M%SZ")


def _parse_iso_ts(ts: Optional[str]) -> Optional[datetime]:
    if not ts or not isinstance(ts, str):
        return None
    try:
        # audit-log timestamps are YYYY-MM-DDTHH:MM:SSZ
        return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
    except ValueError:
        try:
            return datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            return None


def parse_since(value: str) -> Optional[timedelta]:
    """Parse ``30d`` | ``12h`` | ``forever`` into a timedelta (or None for forever).

    Raises ValueError on unrecognized input.
    """
    v = value.strip().lower()
    if v in ("forever", "all", "none"):
        return None
    m = re.match(r"^(\d+)\s*([smhd])$", v)
    if not m:
        raise ValueError(
            f"--since must be <N>[s|m|h|d] or 'forever' (got: {value!r})"
        )
    n = int(m.group(1))
    unit = m.group(2)
    if unit == "s":
        return timedelta(seconds=n)
    if unit == "m":
        return timedelta(minutes=n)
    if unit == "h":
        return timedelta(hours=n)
    return timedelta(days=n)


# ---------------------------------------------------------------------------
# Event aggregation
# ---------------------------------------------------------------------------


def _iter_plan_events(
    plan_id: str,
    since: Optional[datetime],
    path: Optional[Path] = None,
) -> Iterable[Dict[str, Any]]:
    """Yield audit events scoped to ``plan_id`` whose ts >= ``since``.

    Events without a plan_id field are included only if they reference
    the plan via ``artifact_path`` or similar. Currently only
    plan_id-tagged events participate in the session graph.
    """
    for ev in _audit_emit.iter_events(path=path):
        ev_plan = ev.get("plan_id")
        if ev_plan != plan_id:
            # debate_event / plan_transition / lesson_* may carry plan_id
            # directly. Others are skipped.
            continue
        if since is not None:
            ts = _parse_iso_ts(ev.get("ts"))
            if ts is None or ts < since:
                continue
        yield ev


def _session_bucket_from_events(
    events: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Group events by session_id and produce session summaries.

    Each session record derives from ONLY audit-log fields. No synthesis:
    fields that can't be derived are simply omitted.

    Returns list sorted by start_ts asc.
    """
    by_session: Dict[str, Dict[str, Any]] = {}
    for ev in events:
        sid = ev.get("session_id") or ""
        rec = by_session.setdefault(
            sid,
            {
                "session_id": sid,
                "start_ts": None,
                "end_ts": None,
                "spawn_count": 0,
                "debate_rounds": [],
                "event_count": 0,
                "action_counts": {},
                "source_event_refs": [],  # reverse map integrity check
            },
        )
        rec["event_count"] += 1
        action = ev.get("action", "")
        rec["action_counts"][action] = rec["action_counts"].get(action, 0) + 1
        ts = _parse_iso_ts(ev.get("ts"))
        if ts is not None:
            if rec["start_ts"] is None or ts < _parse_iso_ts(rec["start_ts"]):
                rec["start_ts"] = ev.get("ts")
            if rec["end_ts"] is None or ts > _parse_iso_ts(rec["end_ts"]):
                rec["end_ts"] = ev.get("ts")
        # Reverse map: every field we surface has an action that fed it.
        rec["source_event_refs"].append(
            {"action": action, "ts": ev.get("ts")}
        )
        if action == "agent_spawn":
            rec["spawn_count"] += 1
        elif action == "debate_event":
            rnd = ev.get("round")
            if rnd is not None and rnd not in rec["debate_rounds"]:
                rec["debate_rounds"].append(rnd)
    # Sort rounds + events for determinism
    for rec in by_session.values():
        rec["debate_rounds"].sort()
        rec["source_event_refs"].sort(key=lambda e: e.get("ts") or "")

    def _key(rec: Dict[str, Any]) -> str:
        return rec.get("start_ts") or ""

    return sorted(by_session.values(), key=_key)


# ---------------------------------------------------------------------------
# Git derivation (commits on the plan file)
# ---------------------------------------------------------------------------


def _find_plan_file(plan_id: str) -> Optional[Path]:
    """Return the plan markdown file for ``plan_id`` (or None)."""
    plans = _plans_dir()
    if not plans.is_dir():
        return None
    for p in sorted(plans.iterdir()):
        if not p.is_file():
            continue
        m = _PLAN_FILE_RE.match(p.name)
        if not m:
            continue
        if f"PLAN-{m.group(1)}" == plan_id:
            return p
    return None


def _git_log_for_file(file_path: Path, since: Optional[datetime]) -> List[Dict[str, Any]]:
    """Return a list of ``{sha, subject, author_ts}`` for commits touching the file.

    Newest first. Empty list on any git error (fail-safe: the plan file
    may live in a subdir that was renamed, or git may not be present).
    """
    if not file_path.exists():
        return []
    cmd = [
        "git",
        "log",
        "--follow",
        "--pretty=format:%H%x09%at%x09%s",
        "--",
        str(file_path),
    ]
    if since is not None:
        cmd.insert(2, "--since=" + since.strftime("%Y-%m-%dT%H:%M:%SZ"))
    try:
        out = subprocess.check_output(
            cmd,
            cwd=str(REPO_ROOT),
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=10,
        )
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return []
    commits: List[Dict[str, Any]] = []
    for line in out.splitlines():
        parts = line.split("\t", 2)
        if len(parts) != 3:
            continue
        sha, author_ts, subject = parts
        commits.append(
            {
                "sha": sha,
                "author_ts": int(author_ts) if author_ts.isdigit() else 0,
                "subject": subject,
            }
        )
    return commits


# ---------------------------------------------------------------------------
# Plan markdown derivation
# ---------------------------------------------------------------------------


def _extract_section(body: str, heading_re: str) -> List[str]:
    """Return list of stripped bullet lines under a matching level-2 heading.

    Stops at the next level-2 heading or EOF.
    """
    lines = body.splitlines()
    out: List[str] = []
    in_section = False
    h_re = re.compile(heading_re, re.IGNORECASE)
    for line in lines:
        if h_re.match(line.strip()):
            in_section = True
            continue
        if in_section and line.startswith("## "):
            break
        if in_section:
            stripped = line.strip()
            if stripped.startswith("- ") or stripped.startswith("* "):
                out.append(stripped[2:].strip())
    return out


def _last_phase_status(body: str) -> str:
    """Scan plan markdown for the most recent ``Phase N`` checkbox status.

    Returns a short summary like ``"Phase 8: done"`` or ``"Phase 7: in_progress"``,
    or ``"unknown"`` if no phase lines are found. Purely derived — no
    synthesis.
    """
    phase_re = re.compile(
        r"^-?\s*\[([ xX])\]\s*Phase\s+(\d+)\s*[—:\-]?\s*(.*?)$",
        re.IGNORECASE,
    )
    last_done = None
    last_pending = None
    for line in body.splitlines():
        m = phase_re.match(line.strip())
        if not m:
            continue
        marker, n, _ = m.groups()
        phase_num = int(n)
        if marker.strip().lower() == "x":
            if last_done is None or phase_num > last_done:
                last_done = phase_num
        else:
            if last_pending is None or phase_num < last_pending:
                last_pending = phase_num
    if last_pending is not None and (last_done is None or last_pending > last_done):
        return f"Phase {last_pending}: pending"
    if last_done is not None:
        return f"Phase {last_done}: done"
    return "unknown"


def _derive_plan_markdown(
    plan_file: Optional[Path],
) -> Dict[str, Any]:
    """Parse the plan file (frontmatter + deferred + owner actions + last phase).

    Returns an empty-ish dict if the plan file is absent — fail-safe.
    """
    if plan_file is None or not plan_file.is_file():
        return {
            "status": "unknown",
            "title": "",
            "deferred": [],
            "owner_actions": [],
            "last_phase_status": "unknown",
            "source_file": None,
        }
    try:
        content = plan_file.read_text(encoding="utf-8")
    except OSError:
        return {
            "status": "unknown",
            "title": "",
            "deferred": [],
            "owner_actions": [],
            "last_phase_status": "unknown",
            "source_file": str(plan_file),
        }
    fm = _frontmatter.parse_frontmatter(content)
    deferred = _extract_section(content, r"^##\s+Deferred")
    if not deferred:
        deferred = _extract_section(content, r"^##\s+Deferred\s+to\s+")
    owner_actions = _extract_section(content, r"^##\s+Owner\s+action\s+items")
    if not owner_actions:
        owner_actions = _extract_section(content, r"^##\s+Owner\s+actions")
    try:
        source_file = str(plan_file.relative_to(REPO_ROOT))
    except ValueError:
        source_file = str(plan_file)
    return {
        "status": str(fm.get("status", "unknown")),
        "title": str(fm.get("title", "")),
        "deferred": deferred,
        "owner_actions": owner_actions,
        "last_phase_status": _last_phase_status(content),
        "source_file": source_file,
    }


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------


def build_graph(
    plan_id: str,
    *,
    since: Optional[timedelta] = None,
    audit_log_path: Optional[Path] = None,
) -> Dict[str, Any]:
    """Build the derived session graph for ``plan_id``.

    The graph contains ONLY derived data. Every field either maps to an
    audit-log action (see SPEC reverse map) or a git commit. Unknown plan
    = empty graph + no error.

    Args:
        plan_id: ``PLAN-NNN`` string.
        since: optional timedelta window; None = full history.
        audit_log_path: optional override (for tests).

    Returns:
        dict matching SPEC/v1/session-graph.schema.md.
    """
    now = _utc_now()
    since_dt: Optional[datetime] = (now - since) if since is not None else None

    plan_file = _find_plan_file(plan_id)
    plan_md = _derive_plan_markdown(plan_file)

    events = list(_iter_plan_events(plan_id, since_dt, audit_log_path))
    sessions = _session_bucket_from_events(events)

    commits = _git_log_for_file(plan_file, since_dt) if plan_file else []

    graph: Dict[str, Any] = {
        "schema_version": GRAPH_SCHEMA_VERSION,
        "plan_id": plan_id,
        "generated_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "window": {
            "since": since_dt.strftime("%Y-%m-%dT%H:%M:%SZ") if since_dt else None,
            "until": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
        "plan_status": plan_md["status"],
        "plan_title": plan_md["title"],
        "last_phase_status": plan_md["last_phase_status"],
        "sessions": sessions,
        "session_count": len(sessions),
        "event_count": len(events),
        "commits": commits,
        "commit_count": len(commits),
        "deferred": plan_md["deferred"],
        "owner_actions": plan_md["owner_actions"],
        "source_plan_file": plan_md["source_file"],
    }
    return graph


# ---------------------------------------------------------------------------
# Encryption
# ---------------------------------------------------------------------------


def _age_recipient() -> Optional[str]:
    """Return the age recipient string if configured (and ``age`` is on PATH)."""
    if not shutil.which("age"):
        return None
    env = os.environ.get("CEO_AGE_RECIPIENT_FILE")
    p = Path(env).expanduser() if env else (
        Path(os.environ.get("HOME") or str(Path.home())) / ".claude" / "age-recipient.txt"
    )
    if not p.is_file():
        return None
    try:
        return p.read_text(encoding="utf-8").strip()
    except OSError:
        return None


def _gpg_fingerprint() -> Optional[str]:
    if not shutil.which("gpg"):
        return None
    fp = os.environ.get("CEO_GPG_FINGERPRINT", "").strip()
    return fp or None


def _encrypt_bytes(
    payload: bytes, *, out: Path, stderr_warn
) -> Tuple[Path, str]:
    """Encrypt ``payload`` to ``out``. Returns (written_path, method).

    Tool priority: age > gpg > plaintext (with WARNING to stderr).
    """
    age_recipient = _age_recipient()
    if age_recipient:
        cmd = ["age", "-r", age_recipient, "-o", str(out)]
        try:
            proc = subprocess.run(
                cmd,
                input=payload,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=30,
            )
            return out, "age"
        except (subprocess.SubprocessError, FileNotFoundError, OSError) as exc:
            stderr_warn(f"age encryption failed ({exc!r}); trying next tool")

    gpg_fp = _gpg_fingerprint()
    if gpg_fp:
        cmd = [
            "gpg",
            "--batch",
            "--yes",
            "--trust-model",
            "always",
            "--encrypt",
            "--recipient",
            gpg_fp,
            "--output",
            str(out),
        ]
        try:
            proc = subprocess.run(
                cmd,
                input=payload,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=30,
            )
            return out, "gpg"
        except (subprocess.SubprocessError, FileNotFoundError, OSError) as exc:
            stderr_warn(f"gpg encryption failed ({exc!r}); falling back to plaintext")

    # Plaintext fallback
    stderr_warn(
        "no encryption key available (set CEO_GPG_FINGERPRINT or "
        "~/.claude/age-recipient.txt); writing PLAINTEXT"
    )
    plain_path = out.with_suffix(".plain.json") if out.suffix in (".age", ".gpg") else out
    plain_path.write_bytes(payload)
    try:
        os.chmod(plain_path, 0o600)
    except OSError:
        pass
    return plain_path, "plaintext"


def _write_output(
    graph: Dict[str, Any],
    *,
    output_path: Optional[Path],
    plan_id: str,
    encrypt: bool,
    stderr_warn,
) -> Tuple[Path, str]:
    """Serialize + write (encrypted or plain) the graph. Returns (path, method)."""
    payload = (json.dumps(graph, indent=2, sort_keys=False) + "\n").encode("utf-8")

    if output_path is None:
        ts = _ts_compact()
        default_dir = _default_graph_dir()
        default_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
        output_path = default_dir / f"{plan_id}-{ts}.json.age"

    output_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

    if not encrypt:
        # Explicit plaintext. Warn if user asked for plaintext on a real run.
        stderr_warn("writing PLAINTEXT (--no-encrypt)")
        # Strip .age/.gpg suffix if present for plaintext path
        if output_path.suffix in (".age", ".gpg"):
            output_path = output_path.with_suffix("")
        output_path.write_bytes(payload)
        try:
            os.chmod(output_path, 0o600)
        except OSError:
            pass
        return output_path, "plaintext-explicit"

    return _encrypt_bytes(payload, out=output_path, stderr_warn=stderr_warn)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _active_plan_ids() -> List[str]:
    """Return sorted list of PLAN-NNN whose plan file is not ``status: done``."""
    plans = _plans_dir()
    if not plans.is_dir():
        return []
    out: List[str] = []
    for p in sorted(plans.iterdir()):
        if not p.is_file():
            continue
        m = _PLAN_FILE_RE.match(p.name)
        if not m:
            continue
        try:
            fm = _frontmatter.parse_frontmatter(p.read_text(encoding="utf-8"))
        except OSError:
            continue
        status = str(fm.get("status", "")).strip()
        if status and status != "done":
            out.append(f"PLAN-{m.group(1)}")
    return out


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — derive a session-resume graph from the current plan state."""
    if sota_disabled():
        # S4: kill-switch — silent no-op.
        return 0

    parser = argparse.ArgumentParser(
        prog="session-graph-build",
        description="Build a strictly-derived session graph for a plan.",
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--plan", dest="plan_id", help="PLAN-NNN identifier")
    group.add_argument(
        "--all-active",
        action="store_true",
        help="Build graphs for every plan with status != done",
    )
    parser.add_argument(
        "--since",
        default=f"{DEFAULT_SINCE_DAYS}d",
        help=f"Window: <N>[s|m|h|d] or 'forever'. Default: {DEFAULT_SINCE_DAYS}d",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output path. Default: $HOME/.claude/projects/<proj>/session-graphs/<plan>-<ts>.json.age",
    )
    enc = parser.add_mutually_exclusive_group()
    enc.add_argument(
        "--encrypt",
        dest="encrypt",
        action="store_true",
        default=True,
        help="Encrypt output (default, age→gpg→plaintext fallback)",
    )
    enc.add_argument(
        "--no-encrypt",
        dest="encrypt",
        action="store_false",
        help="Emit plaintext JSON (debug only; WARNING on stderr)",
    )

    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0

    try:
        since_td = parse_since(args.since)
    except ValueError as exc:
        sys.stderr.write(f"error: {exc}\n")
        return 2

    if args.plan_id is not None and not _PLAN_ID_RE.match(args.plan_id):
        sys.stderr.write(
            f"error: --plan must match PLAN-NNN (got {args.plan_id!r})\n"
        )
        return 2

    def _warn(msg: str) -> None:
        sys.stderr.write(f"WARNING: session-graph-build: {msg}\n")

    plan_ids: List[str]
    if args.all_active:
        plan_ids = _active_plan_ids()
        if not plan_ids:
            sys.stdout.write("no active plans found (noop)\n")
            return 0
    else:
        plan_ids = [args.plan_id]

    out_path: Optional[Path] = (
        Path(args.output).expanduser() if args.output else None
    )
    if args.all_active and out_path is not None:
        sys.stderr.write(
            "error: --output cannot be combined with --all-active\n"
        )
        return 2

    written = 0
    for pid in plan_ids:
        graph = build_graph(pid, since=since_td)
        path, method = _write_output(
            graph,
            output_path=out_path,
            plan_id=pid,
            encrypt=args.encrypt,
            stderr_warn=_warn,
        )
        sys.stdout.write(
            f"graph: {pid} -> {path} ({method}, "
            f"{graph['session_count']} sessions, "
            f"{graph['event_count']} events, "
            f"{graph['commit_count']} commits)\n"
        )
        written += 1
    sys.stdout.write(f"wrote: {written}\n")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
