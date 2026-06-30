#!/usr/bin/env python3
"""Policy shadow-mode runner — PLAN-014 Phase A.5.

Standalone CLI that runs a single recorded tool-call event through both
the legacy Python hook and the new declarative YAML policy, diffs the
6-tuple observable vector, and emits a structured drift report.

Invoked by the 2-week shadow-mode CI window (Phase A.7) via cron or
release-gate cadence; for A.5 we ship the runner + its tests and defer
wiring. The runner NEVER executes real tool-calls — input is always a
pre-recorded event file (JSON).

## Usage

    policy-shadow-runner --hook bash_safety --event-file event.json
    policy-shadow-runner --hook plan_edit --event-file event.json \\
                         --output drift.log.jsonl

Exit 0 if no un-allow-listed drift; exit 1 if drift detected.

## Report schema (see SPEC §N/A — local to the shadow window)

    {
      "ts": "<ISO-8601 UTC>",
      "hook": "bash_safety",
      "fixture_id": "<sha-16>",
      "drift_detected": false,
      "dimensions": {
        "decision":    {"py": "...", "yaml": "...", "match": bool},
        "reason_key":  {"py": "...", "yaml": "...", "match": bool},
        "audit_hash":  {"py": "...", "yaml": "...", "match": bool},
        "stdout":      {"py": "...", "yaml": "...", "match": bool,
                        "allowlisted": bool},
        "stderr_exit": {"py": "...", "yaml": "...", "match": bool},
        "p95_ms":      {"py": 0.0, "yaml": 0.0, "ratio": 0.0, "match": bool}
      }
    }

Stdlib only.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import sys
import time
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Make _lib importable
_REPO_ROOT = Path(__file__).resolve().parents[2]
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib import policy as _policy  # noqa: E402
from _lib import policy_preprocessors as _pp  # noqa: E402
from _lib import audit_emit as _audit_emit  # noqa: E402

import check_bash_safety as _py_bash  # noqa: E402
import check_plan_edit as _py_plan  # noqa: E402


_POLICIES_DIR = _REPO_ROOT / ".claude" / "policies"
_BASH_POLICY_PATH = _POLICIES_DIR / "bash-safety.policy.yaml"
_PLAN_POLICY_PATH = _POLICIES_DIR / "plan-edit.policy.yaml"


# ---------------------------------------------------------------------------
# Shared with harness (duplicated here to keep runner self-contained)
# ---------------------------------------------------------------------------

_BASH_REASON_MARKERS: Tuple[Tuple[str, str], ...] = (
    ("API credential", "credential_leak"),
    ("`rm` with -r and -f", "rm_rf_destructive"),
    ("`git reset --hard`", "git_reset_hard"),
    ("`git push --force`", "git_push_force"),
)

_PLAN_REASON_MARKERS: Tuple[Tuple[str, str], ...] = (
    ("illegal status value", "illegal_status_value"),
    ("illegal transition", "illegal_transition"),
    ("'reviewed' requires", "missing_reviewed_at"),
    ("non-empty", "missing_related_commits"),
    ("'done' requires", "missing_completed_at"),
    ("Abandonment reason", "missing_abandonment_reason"),
)

_ALLOWLISTED_MESSAGE_DEVIATIONS = frozenset({
    "credential_leak",
    "illegal_transition",
    "illegal_status_value",
})


def _py_bash_reason_to_key(reason: str) -> str:
    for needle, key in _BASH_REASON_MARKERS:
        if needle in reason:
            return key
    return ""


def _py_plan_reason_to_key(reason: str) -> str:
    for needle, key in _PLAN_REASON_MARKERS:
        if needle in reason:
            return key
    return ""


class _AuditCapture:
    """Collect audit events without touching disk."""

    def __init__(self) -> None:
        self.events: List[Dict[str, Any]] = []
        self._patched: List[Tuple[str, Any]] = []

    def __enter__(self) -> "_AuditCapture":
        for name in ("emit_policy_evaluated", "emit_policy_denied",
                     "emit_policy_error", "emit_veto_triggered",
                     "emit_plan_transition"):
            if hasattr(_audit_emit, name):
                orig = getattr(_audit_emit, name)
                self._patched.append((name, orig))
                setattr(_audit_emit, name,
                        lambda _name=name, **kw: self.events.append(
                            {"action": _name.replace("emit_", ""), **kw}))
        return self

    def __exit__(self, *exc: Any) -> None:
        for name, orig in self._patched:
            setattr(_audit_emit, name, orig)


def _canonical_hash(events: List[Dict[str, Any]]) -> str:
    cleaned = [
        {k: v for k, v in ev.items() if k not in (
            "duration_ms", "session_id", "project")}
        for ev in events
    ]
    payload = json.dumps(cleaned, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


# ---------------------------------------------------------------------------
# Per-hook runners
# ---------------------------------------------------------------------------


def _run_bash_yaml(policy: _policy.Policy, event: Dict[str, Any]) -> Dict[str, Any]:
    out_buf = io.StringIO()
    err_buf = io.StringIO()
    with _AuditCapture() as cap:
        t0 = time.monotonic()
        with redirect_stdout(out_buf), redirect_stderr(err_buf):
            res = policy.decide(event)
        ms = (time.monotonic() - t0) * 1000.0
    if res["decision"] == "allow":
        # PLAN-091 schema-fix: Claude Code hook schema rejects top-level
        # {"decision":"allow"} (enum is "approve"|"block"). Mirror the
        # python adapter's emit shape (empty body on allow path) so the
        # py/yaml 6-tuple comparison stays byte-identical.
        env = {}
    else:
        env = {"decision": "block",
               "reason": res.get("message", res.get("reason", ""))}
    return {
        "decision": res["decision"],
        "reason_key": res.get("reason", "") if res["decision"] == "block" else "",
        "audit_hash": _canonical_hash(cap.events),
        "stdout": json.dumps(env, ensure_ascii=False),
        "stderr_exit": err_buf.getvalue() + f"|exit=0",
        "elapsed_ms": ms,
    }


def _run_bash_py(event: Dict[str, Any]) -> Dict[str, Any]:
    tool_input = event.get("tool_input") or {}
    command = str(tool_input.get("command") or "")
    derived = event.get("_derived_bash") or {}
    forced = str(derived.get("credential_leak_provider") or "")
    forced_r = str(derived.get("credential_leak_redacted") or "")
    orig_checker = _py_bash._check_credential_leak
    if forced:
        _py_bash._check_credential_leak = (  # type: ignore
            lambda _c, _p=forced, _r=forced_r: (_p, _r or f"{_p}:****"))
    out_buf = io.StringIO()
    err_buf = io.StringIO()
    try:
        with _AuditCapture() as cap:
            t0 = time.monotonic()
            with redirect_stdout(out_buf), redirect_stderr(err_buf):
                dec = _py_bash.decide_command(command)
                if (not dec.allow and dec.reason
                        and "API credential" in dec.reason):
                    hit = _py_bash._check_credential_leak(command)
                    if hit:
                        _py_bash._emit_credential_leak_event(hit[0], hit[1])
            ms = (time.monotonic() - t0) * 1000.0
    finally:
        _py_bash._check_credential_leak = orig_checker  # type: ignore
    env_str = dec.to_json()
    env = json.loads(env_str)
    reason_text = env.get("reason", "")
    return {
        "decision": "allow" if dec.allow else "block",
        "reason_key": _py_bash_reason_to_key(reason_text) if not dec.allow else "",
        "audit_hash": _canonical_hash(cap.events),
        "stdout": env_str,
        "stderr_exit": err_buf.getvalue() + f"|exit=0",
        "elapsed_ms": ms,
    }


def _run_plan_yaml(policy: _policy.Policy, event: Dict[str, Any]) -> Dict[str, Any]:
    return _run_bash_yaml(policy, event)  # same contract


def _run_plan_py(event: Dict[str, Any]) -> Dict[str, Any]:
    derived = event.get("_derived_plan") or {}
    out_buf = io.StringIO()
    err_buf = io.StringIO()
    with _AuditCapture() as cap:
        t0 = time.monotonic()
        with redirect_stdout(out_buf), redirect_stderr(err_buf):
            if not derived.get("is_plan_file"):
                dec = _py_plan.Decision(allow=True)
            elif not derived.get("status_changed"):
                dec = _py_plan.Decision(allow=True)
            else:
                old_s = str(derived.get("old_status") or "")
                new_s = str(derived.get("new_status") or "")
                reason = _py_plan._check_transition(old_s, new_s)
                if reason:
                    dec = _py_plan.Decision(allow=False, reason=reason)
                else:
                    fm: Dict[str, Any] = {}
                    if derived.get("reviewed_at_present"):
                        fm["reviewed_at"] = "2026-01-01"
                    if derived.get("completed_at_present"):
                        fm["completed_at"] = "2026-01-01"
                    if derived.get("related_commits_nonempty"):
                        fm["related_commits"] = ["abc1234"]
                    # Session 75 F7 — refused_adr field synthesis.
                    if derived.get("refused_adr_present"):
                        fm["refused_adr"] = (
                            "ADR-093"
                            if derived.get("refused_adr_well_formed")
                            else "not-an-adr"
                        )
                    # Session 76 audit-v3 (DIM-11) — ADR-092 enforcement
                    # field synthesis: refused_at + reopen_*. Mirrors the
                    # shape policy_preprocessors derives so the Python and
                    # YAML paths stay byte-identical.
                    if derived.get("refused_at_present"):
                        fm["refused_at"] = "2026-04-29"
                    if derived.get("reopen_via_present"):
                        fm["reopen_via"] = (
                            "ADR-092"
                            if derived.get("reopen_via_well_formed")
                            else "not-an-adr"
                        )
                    if derived.get("reopen_trigger_present"):
                        fm["reopen_trigger"] = (
                            "synthetic external soak signal"
                        )
                    body = ("\n## Abandonment reason\nstub\n"
                            if derived.get("abandonment_reason_present") else "")
                    if derived.get("reopen_criteria_section_present"):
                        body += "\n## Reopen criteria\nstub\n"
                    r2 = _py_plan._check_required_fields(old_s, new_s, fm, body)
                    dec = (_py_plan.Decision(allow=False, reason=r2) if r2
                           else _py_plan.Decision(allow=True))
        ms = (time.monotonic() - t0) * 1000.0
    env_str = dec.to_json()
    env = json.loads(env_str)
    reason_text = env.get("reason", "")
    return {
        "decision": "allow" if dec.allow else "block",
        "reason_key": _py_plan_reason_to_key(reason_text) if not dec.allow else "",
        "audit_hash": _canonical_hash(cap.events),
        "stdout": env_str,
        "stderr_exit": err_buf.getvalue() + f"|exit=0",
        "elapsed_ms": ms,
    }


# ---------------------------------------------------------------------------
# 6-tuple diff
# ---------------------------------------------------------------------------


def _diff_report(py: Dict[str, Any], yaml_: Dict[str, Any], hook: str,
                 fixture_id: str) -> Dict[str, Any]:
    reason_key = py.get("reason_key") or yaml_.get("reason_key") or ""
    stdout_allowlisted = reason_key in _ALLOWLISTED_MESSAGE_DEVIATIONS

    decision_match = py["decision"] == yaml_["decision"]
    reason_match = py["reason_key"] == yaml_["reason_key"]
    # audit_hash parity is NOT asserted as drift (Python pre-dates
    # policy_evaluated); we report but don't fail on it.
    audit_match = True  # advisory dimension
    if py["decision"] == "block" and not stdout_allowlisted:
        stdout_match = py["stdout"] == yaml_["stdout"]
    elif py["decision"] == "allow":
        stdout_match = py["stdout"] == yaml_["stdout"]
    else:
        stdout_match = True  # allow-listed
    stderr_match = True  # stderr breadcrumbs differ by design; exit always 0

    ratio = (yaml_["elapsed_ms"] / py["elapsed_ms"]) if py["elapsed_ms"] > 0 \
        else 0.0
    latency_match = ratio <= 1.20

    drift = not all([decision_match, reason_match, stdout_match])

    report = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "hook": hook,
        "fixture_id": fixture_id,
        "drift_detected": bool(drift),
        "dimensions": {
            "decision": {
                "py": py["decision"], "yaml": yaml_["decision"],
                "match": decision_match,
            },
            "reason_key": {
                "py": py["reason_key"], "yaml": yaml_["reason_key"],
                "match": reason_match,
            },
            "audit_hash": {
                "py": py["audit_hash"], "yaml": yaml_["audit_hash"],
                "match": audit_match,
            },
            "stdout": {
                "py": py["stdout"], "yaml": yaml_["stdout"],
                "match": stdout_match, "allowlisted": stdout_allowlisted,
            },
            "stderr_exit": {
                "py": py["stderr_exit"], "yaml": yaml_["stderr_exit"],
                "match": stderr_match,
            },
            "p95_ms": {
                "py": py["elapsed_ms"], "yaml": yaml_["elapsed_ms"],
                "ratio": ratio, "match": latency_match,
            },
        },
    }
    return report


def _fixture_id(event: Dict[str, Any]) -> str:
    payload = json.dumps(event, sort_keys=True, separators=(",", ":"),
                         ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def run_shadow(hook: str, event: Dict[str, Any]) -> Dict[str, Any]:
    """Run both paths + return the structured report."""
    if hook == "bash_safety":
        policy = _policy.load(_BASH_POLICY_PATH)
        if "_derived_bash" not in event:
            event = _pp.bash_safety_preprocess(event)
        yaml_res = _run_bash_yaml(policy, event)
        py_res = _run_bash_py(event)
    elif hook == "plan_edit":
        policy = _policy.load(_PLAN_POLICY_PATH)
        if "_derived_plan" not in event:
            event = _pp.plan_edit_preprocess(event)
        yaml_res = _run_plan_yaml(policy, event)
        py_res = _run_plan_py(event)
    else:
        raise ValueError(f"unknown hook: {hook!r}")
    return _diff_report(py_res, yaml_res, hook, _fixture_id(event))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        prog="policy-shadow-runner",
        description=(
            "Runs both Python and YAML paths on a single recorded tool-call "
            "event, diffs the 6-tuple, emits a structured drift report to "
            "stdout. If --output is set, appends a JSONL line to the drift log."
        ),
    )
    p.add_argument("--hook", required=True, choices=("bash_safety", "plan_edit"))
    p.add_argument("--event-file", required=True,
                   help="Path to JSON file containing the tool-call event.")
    p.add_argument("--output", default=None,
                   help="Optional JSONL drift log file; appended to.")
    return p.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — execute a policy in shadow-mode and diff vs live."""
    args = _parse_args(argv)
    event_path = Path(args.event_file)
    if not event_path.is_file():
        print(f"error: --event-file does not exist: {event_path}",
              file=sys.stderr)
        return 1
    try:
        with open(event_path, "r", encoding="utf-8") as f:
            event = json.load(f)
    except (OSError, ValueError) as e:
        print(f"error: cannot read event file: {e}", file=sys.stderr)
        return 1
    try:
        report = run_shadow(args.hook, event)
    except (_policy.PolicyLoadError, ValueError) as e:
        print(f"error: shadow run failed: {e}", file=sys.stderr)
        return 1

    line = json.dumps(report, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)
    print(line)
    if args.output:
        try:
            with open(args.output, "a", encoding="utf-8") as f:
                f.write(line + "\n")
        except OSError as e:
            print(f"warning: cannot append to --output: {e}", file=sys.stderr)
            # Do not fail on log-write; the authoritative report is on stdout.

    return 1 if report["drift_detected"] else 0


if __name__ == "__main__":
    sys.exit(main())
