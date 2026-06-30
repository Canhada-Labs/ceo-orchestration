#!/usr/bin/env python3
"""PLAN-104 Wave B — persona-demand event detector.

Stateless local-git scanner. Iterates a bounded horizon
(git log HEAD~500 --since=168h --name-only) and emits one
persona_demand_opened event per detected demand_id NOT already
present in the audit-log (idempotency via demand_id dedup; no
sidecar state file per S134 R2 Q7 fold).

Four demand sources (S134 R2 sec 2.1):
  - branch_ahead   — non-trunk branch >=1 commit ahead of origin/main -> code-reviewer
  - auth_edit      — auth-touching file edited                         -> security-engineer
  - test_edit      — new test file OR mutation-testing config          -> qa-architect
  - detect_edit    — SIEM rule / detection-as-code change              -> threat-detection-engineer

Match window: 24h (uniform across types per S134 R2 Q3 fold).

Invoked from /ceo-boot (or stand-alone). Kill-switch:
CEO_PERSONA_DEMAND_LEDGER_DISABLED=1.

PLAN-104 sec 2.1 (S134 R2 Q1+Q2+Q3+Q4 folds — local git introspection
ONLY; no pre-commit hook surface; no GitHub API; strict-match no peer
substitution; uniform 24h window).
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import os
import re
import subprocess
import sys
import time
import unicodedata
from pathlib import Path
from typing import Iterator, List, NamedTuple, Optional, Set, Tuple

DEFAULT_AUDIT_LOG = Path(
    os.environ.get(
        "CEO_AUDIT_LOG_DIR",
        str(Path.home() / ".claude" / "projects" / "ceo-orchestration"),
    )
) / "audit-log.jsonl"

MATCH_WINDOW_HOURS = 24
SCAN_HORIZON_COMMITS = 500
SCAN_HORIZON_HOURS = 168

AUTH_PATTERNS: Tuple[str, ...] = (
    "*auth*", "*jwt*", "*oauth*", "*token*", "*session*",
    "*credential*", "*idp*", "*sso*",
)
TEST_PATTERNS: Tuple[str, ...] = (
    "tests/**/*.py", "tests/**/*.ts", "tests/**/*.js",
    "test_*.py", "*_test.py",
    "mutmut.cfg", "mutpy.cfg", ".mutation.toml",
)
DETECT_PATTERNS: Tuple[str, ...] = (
    "detections/**", "*.sigma", "*.yar", "*.yara", "siem-rules/**",
)

PERSONA_FOR_TYPE = {
    "branch_ahead": "code-reviewer",
    "auth_edit": "security-engineer",
    "test_edit": "qa-architect",
    "detect_edit": "threat-detection-engineer",
}


class DemandEvent(NamedTuple):
    demand_id: str
    demand_event_type: str
    expected_persona: str
    target_ref: str  # raw — NEVER persisted, hashed at emit time


def _norm(s: str) -> str:
    return unicodedata.normalize("NFKC", s)


def _demand_id(preimage: str) -> str:
    return hashlib.sha256(_norm(preimage).encode("utf-8")).hexdigest()[:16]


def _target_ref_hash(target_ref: str) -> str:
    return hashlib.sha256(_norm(target_ref).encode("utf-8")).hexdigest()[:12]


def _git(args: List[str], cwd: Optional[Path] = None) -> str:
    try:
        out = subprocess.check_output(
            ["git"] + args, cwd=str(cwd) if cwd else None,
            stderr=subprocess.DEVNULL, text=True,
        )
        return out
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


def _glob_to_regex(pat: str) -> str:
    """Translate glob with `**` recursive segment match into a regex.

    `**` matches zero+ characters including `/`; `*` matches any chars
    except `/`; `?` matches single non-`/` char; everything else literal.
    """
    out: List[str] = []
    i = 0
    while i < len(pat):
        ch = pat[i]
        if ch == "*":
            if i + 1 < len(pat) and pat[i + 1] == "*":
                out.append(".*")
                i += 2
                if i < len(pat) and pat[i] == "/":
                    i += 1
            else:
                out.append("[^/]*")
                i += 1
        elif ch == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(ch))
            i += 1
    return "^" + "".join(out) + "$"


def _path_matches(path: str, patterns: Tuple[str, ...]) -> bool:
    """Glob-with-double-star match. Case-sensitive."""
    for pat in patterns:
        if "**" in pat:
            if re.match(_glob_to_regex(pat), path):
                return True
        elif fnmatch.fnmatch(path, pat):
            return True
    return False


def _scan_branch_ahead(repo_root: Path) -> Iterator[DemandEvent]:
    """Detect ALL non-trunk local branches >=1 commit ahead of trunk.

    Codex iter-1 P0 #3 fold: spec requires "non-trunk branch ahead of
    trunk" (PLAN-104 sec 2.1), not "current HEAD branch ahead". A
    feature branch the operator hasn't checked out today still
    represents code-review demand. Enumerate all local refs.
    """
    base_ref = "origin/main"
    base_sha = _git(["rev-parse", base_ref], cwd=repo_root).strip()
    if not base_sha:
        base_ref = "main"
        base_sha = _git(["rev-parse", base_ref], cwd=repo_root).strip()
    if not base_sha:
        return

    refs_out = _git(
        ["for-each-ref", "--format=%(refname:short)", "refs/heads/"],
        cwd=repo_root,
    )
    seen_branches: Set[str] = set()
    for line in refs_out.splitlines():
        branch = line.strip()
        if not branch or branch in ("main", "master") or branch in seen_branches:
            continue
        seen_branches.add(branch)
        ahead = _git(
            ["rev-list", "--count", f"{base_ref}..{branch}"], cwd=repo_root,
        ).strip()
        try:
            n = int(ahead)
        except ValueError:
            continue
        if n < 1:
            continue
        # `branch:` prefix on target_ref disambiguates branch vs file
        # path at the resolver join site. The preimage (used for
        # demand_id) uses the bare branch name per PLAN-104 §2.2.
        # Codex iter-4 P2 #1: documented dual-namespace usage.
        target_ref = f"branch:{branch}"
        preimage = f"branch_ahead:{branch}:{base_sha}"
        yield DemandEvent(
            demand_id=_demand_id(preimage),
            demand_event_type="branch_ahead",
            expected_persona=PERSONA_FOR_TYPE["branch_ahead"],
            target_ref=target_ref,
        )


def _scan_commit_files(repo_root: Path, hours: int) -> Iterator[DemandEvent]:
    """Detect file-edit demands in commits within the horizon."""
    horizon_anchor = f"HEAD~{SCAN_HORIZON_COMMITS}"
    has_horizon = _git(["rev-parse", horizon_anchor], cwd=repo_root).strip()
    rev_range = f"{horizon_anchor}..HEAD" if has_horizon else "HEAD"
    log_output = _git(
        [
            "log", rev_range,
            f"--since={hours}h",
            "--name-only",
            "--pretty=format:__COMMIT__%H",
            "--no-merges",
        ],
        cwd=repo_root,
    )
    current_sha = ""
    for line in log_output.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("__COMMIT__"):
            current_sha = line[len("__COMMIT__"):]
            continue
        if not current_sha:
            continue
        path = line
        if _path_matches(path, AUTH_PATTERNS):
            preimage = f"file_edit_auth:{path}:{current_sha}"
            yield DemandEvent(
                demand_id=_demand_id(preimage),
                demand_event_type="auth_edit",
                expected_persona=PERSONA_FOR_TYPE["auth_edit"],
                target_ref=path,
            )
        if _path_matches(path, TEST_PATTERNS):
            preimage = f"file_edit_test:{path}:{current_sha}"
            yield DemandEvent(
                demand_id=_demand_id(preimage),
                demand_event_type="test_edit",
                expected_persona=PERSONA_FOR_TYPE["test_edit"],
                target_ref=path,
            )
        if _path_matches(path, DETECT_PATTERNS):
            preimage = f"file_edit_detect:{path}:{current_sha}"
            yield DemandEvent(
                demand_id=_demand_id(preimage),
                demand_event_type="detect_edit",
                expected_persona=PERSONA_FOR_TYPE["detect_edit"],
                target_ref=path,
            )


def _existing_demand_ids(audit_log: Path, hours: int) -> Set[str]:
    """Return demand_ids already emitted within window. Stateless dedup source."""
    if not audit_log.exists():
        return set()
    cutoff = time.time() - hours * 3600
    out: Set[str] = set()
    try:
        with audit_log.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if ev.get("action") != "persona_demand_opened":
                    continue
                ts = ev.get("ts") or ev.get("timestamp", "")
                try:
                    from datetime import datetime
                    if datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp() < cutoff:
                        continue
                except (ValueError, TypeError, AttributeError):
                    continue
                did = ev.get("demand_id")
                if did:
                    out.add(did)
    except OSError:
        return set()
    return out


def detect_all(repo_root: Path) -> List[DemandEvent]:
    """Return ALL detected demands (no dedup against audit-log).

    Codex iter-3 P0 fold: the waive resolver needs the full candidate
    set (including demands already opened in audit-log) so a waive
    added in a later commit can still apply to an earlier-opened
    demand. The previous `scan()` returned only NEW demands and made
    "waive later" semantics impossible.

    Use this for waive matching; use `scan()` for emit_opened dedup.
    """
    if os.environ.get("CEO_PERSONA_DEMAND_LEDGER_DISABLED") == "1":
        return []
    out: List[DemandEvent] = []
    seen: Set[str] = set()
    for ev in _scan_branch_ahead(repo_root):
        if ev.demand_id in seen:
            continue
        seen.add(ev.demand_id)
        out.append(ev)
    for ev in _scan_commit_files(repo_root, SCAN_HORIZON_HOURS):
        if ev.demand_id in seen:
            continue
        seen.add(ev.demand_id)
        out.append(ev)
    return out


def scan(repo_root: Path, audit_log: Path = DEFAULT_AUDIT_LOG) -> List[DemandEvent]:
    """Return NEW demand events (deduped against audit-log).

    Caller of emit_opened uses this to skip already-emitted demands.
    For waive matching that must cover already-opened demands, use
    `detect_all()` instead (Codex iter-3 P0).
    """
    if os.environ.get("CEO_PERSONA_DEMAND_LEDGER_DISABLED") == "1":
        return []
    already = _existing_demand_ids(audit_log, SCAN_HORIZON_HOURS)
    return [ev for ev in detect_all(repo_root) if ev.demand_id not in already]


def emit_opened(events: List[DemandEvent], session_id: str = "") -> int:
    """Emit persona_demand_opened for each event. Returns count emitted.

    Hasattr-guarded: works in adopter installs that haven't run the
    PLAN-104 kernel ceremony yet (emit is no-op until audit_emit
    extension lands).
    """
    if not events:
        return 0
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "hooks" / "_lib"))
        import audit_emit as _ae
    except Exception:
        return 0
    n = 0
    for ev in events:
        try:
            fn = getattr(_ae, "emit_persona_demand_opened", None)
            if fn is None:
                return 0
            fn(
                demand_id=ev.demand_id,
                demand_event_type=ev.demand_event_type,
                expected_persona=ev.expected_persona,
                target_ref_hash=_target_ref_hash(ev.target_ref),
                match_window_hours=MATCH_WINDOW_HOURS,
                session_id=session_id,
                project="ceo-orchestration",
            )
            n += 1
        except Exception:
            continue
    return n


def main() -> int:
    parser = argparse.ArgumentParser(description="persona-demand event detector")
    parser.add_argument("--repo", default=".", help="repo root (default: cwd)")
    parser.add_argument("--audit-log", default=str(DEFAULT_AUDIT_LOG))
    parser.add_argument("--json", action="store_true", help="emit JSONL to stdout")
    parser.add_argument("--no-emit", action="store_true", help="skip audit_emit (dry-run)")
    args = parser.parse_args()

    repo = Path(args.repo).resolve()
    log = Path(args.audit_log).resolve()
    events = scan(repo, log)
    if args.json:
        for ev in events:
            print(json.dumps({
                "demand_id": ev.demand_id,
                "demand_event_type": ev.demand_event_type,
                "expected_persona": ev.expected_persona,
                "target_ref_hash": _target_ref_hash(ev.target_ref),
            }))
    else:
        for ev in events:
            print(f"[{ev.demand_event_type}] demand_id={ev.demand_id} expected={ev.expected_persona}")
    if not args.no_emit:
        n = emit_opened(events)
        if not args.json:
            print(f"# emitted {n}/{len(events)} persona_demand_opened events", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
