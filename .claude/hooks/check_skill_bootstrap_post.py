#!/usr/bin/env python3
"""PostToolUse observer: SKILL.md bootstrap TOCTOU forensic guard.

PLAN-042 ITEM 7 (FINDING-17 Wave A retrospective debate Round 1,
security-engineer P1).

## Threat model

`check_skill_patch_sentinel.py::_bootstrap_bypass_allows` (ADR-059)
allows a SKILL.md Write when:

1. `CEO_SKILL_BOOTSTRAP` env matches the target skill_slug exactly.
2. `CEO_SKILL_BOOTSTRAP_ACK=I-ACCEPT`.
3. The target path does NOT already exist.

The `target.exists()` check is Time-of-Check. Between the check and
the actual Write-tool invocation (Time-of-Use) a concurrent agent
could plant content at the same path. The PreToolUse hook would still
emit `decision: allow` because at Time-of-Check the file was absent.

## Defense (this hook)

A PostToolUse observer computes the SHA-256 of the resulting SKILL.md
file, correlates it with any recent `skill_bootstrap_used` audit
event, and emits `skill_bootstrap_post_hash` with:

- `skill_slug`
- `sha256` of the bytes on disk after Write
- `bootstrap_event_correlated` (bool) — was an audit-log
  `skill_bootstrap_used` event observed within the last 5 seconds?
- `suspicious_delay_s` — seconds between the bootstrap_used event
  and this PostToolUse; > 5 s or < 0 s flag anomaly
- `file_size` — bytes on disk

Observer role: the hook does NOT block retroactively (PostToolUse
schema does not support it). It creates the forensic trail that
audit-dashboard / audit-query can use to detect concurrent-race
attacks. An operator workflow on the event stream can quarantine
suspicious writes after the fact.

## Fail-open contract (ADR-005)

Any internal exception → `{"continue": true}` with no system message.
The hook never blocks the user on its own bug (it cannot block
anyway — PostToolUse is advisory).

## Kill-switch

`CEO_SKILL_BOOTSTRAP_POST=0` disables the observer entirely.

## Registration

`.claude/settings.json` PostToolUse Edit|Write|MultiEdit.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Dict, Optional

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

_HOOK_VERSION = "1.0.0"
_KILL_SWITCH_ENV = "CEO_SKILL_BOOTSTRAP_POST"
_SKILL_MD_SUFFIX = "/SKILL.md"
_SKILL_DIR_PREFIX = ".claude/skills/"


def _kill_switch_active() -> bool:
    val = os.environ.get(_KILL_SWITCH_ENV, "").strip().lower()
    return val in {"0", "false", "off", "no"}


def _emit_observe(system_message: Optional[str] = None) -> str:
    out: Dict[str, object] = {"continue": True}
    if system_message:
        out["systemMessage"] = system_message
    return json.dumps(out, ensure_ascii=False)


def _is_skill_md(rel_path: str) -> bool:
    """True iff rel_path targets a SKILL.md under `.claude/skills/`."""
    if not rel_path:
        return False
    rel = rel_path.replace(os.sep, "/")
    if not rel.startswith(_SKILL_DIR_PREFIX):
        return False
    if not rel.endswith(_SKILL_MD_SUFFIX):
        return False
    return True


def _skill_slug(rel_path: str) -> str:
    """Extract the skill_slug (parent dir name) for a SKILL.md path."""
    try:
        return Path(rel_path).parent.name
    except Exception:
        return ""


def _sha256_file(path: Path) -> Optional[str]:
    try:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except Exception:
        return None


def _recent_bootstrap_event(
    repo_root: Path, skill_slug: str, window_s: float = 5.0
) -> Optional[float]:
    """Return UNIX timestamp of the most recent skill_bootstrap_used
    event for this skill_slug in the audit-log, if within the window.

    Returns None if no event, or event is outside the window, or the
    audit-log cannot be read.
    """
    try:
        log_candidates = [
            repo_root / ".claude" / "state" / "audit-log.jsonl",
            Path.home()
            / ".claude" / "projects" / "ceo-orchestration" / "audit-log.jsonl",
        ]
        now = time.time()
        for log_path in log_candidates:
            if not log_path.exists() or not log_path.is_file():
                continue
            # Read the file in reverse: most recent events are at the
            # tail. Linear scan is fine for typical audit-log size.
            try:
                with log_path.open("r", encoding="utf-8", errors="replace") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        if "skill_bootstrap_used" not in line:
                            continue
                        try:
                            ev = json.loads(line)
                        except Exception:
                            continue
                        if ev.get("action") != "skill_bootstrap_used":
                            continue
                        if ev.get("skill_slug") != skill_slug:
                            continue
                        ts = ev.get("ts") or ev.get("timestamp")
                        if ts is None:
                            continue
                        try:
                            if isinstance(ts, (int, float)):
                                ts_val = float(ts)
                            else:
                                # ISO 8601 — parse best-effort via
                                # fromisoformat (stdlib, 3.9+).
                                from datetime import datetime
                                ts_str = str(ts).replace("Z", "+00:00")
                                ts_val = datetime.fromisoformat(
                                    ts_str
                                ).timestamp()
                        except Exception:
                            continue
                        if (now - ts_val) <= window_s and ts_val <= now + 1:
                            return ts_val
            except OSError:
                continue
        return None
    except Exception:
        return None


def _emit_post_hash(
    *,
    skill_slug: str,
    sha256: Optional[str],
    file_size: int,
    bootstrap_ts: Optional[float],
    suspicious_delay_s: Optional[float],
    anomaly: bool,
    project: str,
) -> None:
    """Best-effort audit event. Never raises.

    ``bootstrap_ts`` is emitted as ``bootstrap_ts_s`` integer epoch-seconds.
    ``suspicious_delay_s`` is emitted as ``suspicious_delay_ms`` integer
    milliseconds (-1 when not applicable). Both conversions prevent
    CanonicalJsonError from the HMAC-covered canonical_json encoder which
    forbids floats in HMAC-covered fields.
    """
    try:
        from _lib import audit_emit  # type: ignore
        emitter = getattr(audit_emit, "emit_generic", None)
        if emitter is None:
            return
        # Convert floats to ints: canonical_json forbids floats in HMAC fields.
        ts_int = int(bootstrap_ts) if bootstrap_ts is not None else 0
        delay_ms = (
            int(round(suspicious_delay_s * 1000))
            if suspicious_delay_s is not None
            else -1
        )
        emitter(
            action="skill_bootstrap_post_hash",
            skill_slug=skill_slug,
            sha256=sha256 or "",
            file_size=file_size,
            bootstrap_event_correlated=bootstrap_ts is not None,
            bootstrap_ts_s=ts_int,
            suspicious_delay_ms=delay_ms,
            anomaly=anomaly,
            hook_version=_HOOK_VERSION,
            project=project,
        )
    except Exception:
        return


def decide(
    *, file_path: str, repo_root: Path, project: str
) -> str:
    """Pure decision function. Always observe (non-blocking) — emits bootstrap-integrity findings via audit_emit."""
    if _kill_switch_active():
        return _emit_observe()

    if not file_path:
        return _emit_observe()

    try:
        target = Path(file_path)
        rel = str(
            target.resolve().relative_to(repo_root.resolve())
        ).replace(os.sep, "/")
    except (ValueError, OSError):
        return _emit_observe()

    if not _is_skill_md(rel):
        return _emit_observe()

    slug = _skill_slug(rel)
    if not slug:
        return _emit_observe()

    # Resolve the target on disk (may not exist if a prior step failed).
    try:
        sha = _sha256_file(target) if target.exists() else None
        size = target.stat().st_size if target.exists() else 0
    except OSError:
        sha = None
        size = 0

    bootstrap_ts = _recent_bootstrap_event(repo_root, slug)
    now = time.time()
    if bootstrap_ts is not None:
        delay = max(0.0, now - bootstrap_ts)
    else:
        delay = None

    # Anomaly rules:
    # - No correlated bootstrap event but the file content looks freshly
    #   written (we cannot tell from hash alone, so correlation=False is
    #   informational only).
    # - Delay > 5s between bootstrap event and PostToolUse: possible
    #   concurrent writer raced past the TOC check.
    anomaly = False
    if bootstrap_ts is not None and delay is not None and delay > 5.0:
        anomaly = True

    _emit_post_hash(
        skill_slug=slug,
        sha256=sha,
        file_size=size,
        bootstrap_ts=bootstrap_ts,
        suspicious_delay_s=delay,
        anomaly=anomaly,
        project=project,
    )

    if anomaly:
        return _emit_observe(
            system_message=(
                f"SKILL-BOOTSTRAP-TOCTOU: forensic anomaly — slug={slug}, "
                f"delay={delay:.2f}s from bootstrap_used event "
                "(see audit-log)"
            )
        )
    return _emit_observe()


def main() -> int:
    """Hook entrypoint. Parses PostToolUse payload; invokes `decide()`; fail-open on any parse error."""
    try:
        from _lib import payload as _payload  # noqa: E402
    except Exception:
        sys.stdout.write(_emit_observe() + "\n")
        return 0

    try:
        parsed = _payload.parse_stdin()
    except Exception:
        sys.stdout.write(_emit_observe() + "\n")
        return 0

    if parsed.raw_error:
        sys.stdout.write(_emit_observe() + "\n")
        return 0

    tool_name = parsed.tool_name or ""
    if tool_name not in {"Edit", "Write", "MultiEdit"}:
        sys.stdout.write(_emit_observe() + "\n")
        return 0

    tool_input = parsed.tool_input if isinstance(parsed.tool_input, dict) else {}
    file_path = str(tool_input.get("file_path") or "")
    repo_root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    project = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()

    try:
        out = decide(file_path=file_path, repo_root=repo_root, project=project)
    except Exception as e:
        sys.stderr.write(
            f"[check_skill_bootstrap_post] FATAL: {type(e).__name__}: {e}\n"
        )
        sys.stdout.write(_emit_observe() + "\n")
        return 0

    sys.stdout.write(out + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
