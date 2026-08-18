#!/usr/bin/env python3
"""PLAN-179 W0 US1 (amendment 8.6) — live CHANNEL probe for post-compaction
governance injection.

## The one question this probe answers

ADR-153 proved the compaction hooks FIRE. It never proved their OUTPUT is
CONSUMED. Lesson [[feedback-event-probe-is-not-channel-probe]]: a sonda de
EVENTO nao e uma sonda de CANAL. So the question here is narrow and paid:

    does governance text emitted as ``hookSpecificOutput.additionalContext``
    by ``PostCompact`` and/or by ``SessionStart(matcher=compact)`` actually
    survive into the model's post-compaction context?

Three outcomes, one paid compaction (amendment 8.6): BOTH channels deliver,
exactly ONE delivers, NEITHER delivers. A negative result is a deliverable —
it redirects PLAN-179 W1 away from ``additionalContext`` (see PLAN-179 §4 W0
and the E5 finding: the hooks doc lists ``systemMessage``/``terminalSequence``
for PostCompact and denies ``additionalContext`` on SessionStart, yet
``turbo_sessionstart.py`` uses it and works — so the doc is imprecise OR the
events differ, and doctrine 3 says we resolve that with a live probe).

## Contract (all of it binding — amendment 8.6)

- **OPERATOR / LOCAL ONLY.** Every operator mode REFUSES with exit 2 when
  ``$CI`` or ``$GITHUB_ACTIONS`` is truthy. This probe spends real money
  (it needs a real compaction) and mutates local state; CI must never run
  it. Recovery route for an operator whose shell exports ``CI``: unset it —
  there is deliberately NO override env var (an override would defeat the
  guard the first time CI inherited it).
- **Strict no-op unless armed.** The injection side (``--hook``) emits the
  canary ONLY when ``$CEO_COMPACTION_PROBE_CANARY`` names a readable run
  state file. Unarmed — or armed with an unreadable file — it prints ``{}``
  and exits 0. The probe must not change production behaviour by existing.
- **Fail-open in ``--hook`` only.** ``--hook`` runs inside a live session:
  ANY problem there degrades to ``{}`` + exit 0 (CLAUDE.md §4 — hooks never
  block the session on infrastructure). That is also why ``--hook`` is the
  single mode exempt from the exit-2 CI refusal: a non-zero exit from a
  wired hook is read by the harness as a hook error, so in CI it no-ops
  instead. Operator modes fail LOUD.
- **Idempotent accounting.** Each ``--arm`` APPENDS a record to the run file
  AND one JSONL line to ``runs.jsonl``. US2 (compaction-frequency
  measurement) SUBTRACTS the ``kind == "arm"`` lines so probe-induced
  compactions do not contaminate the real frequency count.
- **No audit event.** A new audit action would need ``_KNOWN_ACTIONS`` +
  an allowlist/scrub branch (house rule) — out of scope for a W0 probe.
  The evidence lives in the run file, which is the falsifiable record.
- Stdlib only, Python >= 3.9.

## State layout (gitignored — ``.claude/state/`` is NON-COMMIT, PLAN-163 T3.1)

    .claude/state/probe-postcompact/<utc-stamp>.json   one armed run
    .claude/state/probe-postcompact/runs.jsonl         append-only ledger

## Modes

    --arm                     mint both canaries, persist, print operator steps
    --hook <channel>          injection side; wired temporarily by the operator
    --verify <observation>    0 = BOTH found, 3 = exactly ONE, 1 = NEITHER
    --status                  list armed runs + verdicts
    --self-test               in-process assertions (no compaction, no spend)

## Exit codes

    0  both canaries found (or a clean --arm/--status/--self-test/--hook)
    1  NEITHER canary found (or --self-test failed)
    2  refused: CI detected, usage error, or self-observation attempt
    3  PARTIAL: exactly one canary found (the interesting outcome)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

SCHEMA_VERSION = 1

# PLAN-179 W0 US1 — the env var that ARMS the injection side. Absent => no-op.
CANARY_ENV = "CEO_COMPACTION_PROBE_CANARY"

STATE_REL = os.path.join(".claude", "state", "probe-postcompact")
LEDGER_NAME = "runs.jsonl"

CHANNEL_POST = "postcompact"
CHANNEL_SS = "sessionstart-compact"
CHANNELS = (CHANNEL_POST, CHANNEL_SS)

# The harness event name each channel rides on (the payload key the harness
# reads back). PostCompact and SessionStart differ — that difference is
# precisely the E5 uncertainty this probe measures.
_EVENT_NAME = {CHANNEL_POST: "PostCompact", CHANNEL_SS: "SessionStart"}

CANARY_PREFIX = {CHANNEL_POST: "CANARY-POST-", CHANNEL_SS: "CANARY-SS-"}

EXIT_OK = 0
EXIT_NEITHER = 1
EXIT_REFUSED = 2  # shared with argparse usage errors — both mean "did not run"
EXIT_PARTIAL = 3

VERDICT_BOTH = "both"
VERDICT_NEITHER = "neither"
VERDICT_POST_ONLY = "postcompact-only"
VERDICT_SS_ONLY = "sessionstart-compact-only"


# --------------------------------------------------------------------------
# environment
# --------------------------------------------------------------------------
def _env_truthy(val: Optional[str]) -> bool:
    """CI-style boolean: truthy unless empty / 0 / false / no / off.

    Same reading as ``check-hook-stdout-schema.py:_env_truthy`` so an
    operator with ``CI=0`` in their shell is not locked out.
    """
    if val is None:
        return False
    return val.strip().lower() not in ("", "0", "false", "no", "off")


def ci_reason() -> Optional[str]:
    """Name the env var that makes this a CI context, or None. (8.6)"""
    for var in ("CI", "GITHUB_ACTIONS"):
        if _env_truthy(os.environ.get(var)):
            return var
    return None


def repo_root() -> Path:
    """``$CLAUDE_PROJECT_DIR`` first (tests isolate through it), else the
    nearest ``.git`` ancestor, else this file's directory."""
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env).resolve()
    here = Path(__file__).resolve()
    for cand in here.parents:
        if (cand / ".git").exists():
            return cand
    return here.parent


def state_dir(root: Optional[Path] = None) -> Path:
    return (root or repo_root()) / STATE_REL


def _utc_now() -> datetime:
    # tz-aware (not utcnow()): utcnow() is deprecated on newer runtimes and
    # this file must stay warning-clean from 3.9 through current.
    return datetime.now(timezone.utc)


def _utc_iso(now: Optional[datetime] = None) -> str:
    return (now or _utc_now()).strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc_stamp(now: Optional[datetime] = None) -> str:
    """Filename-safe UTC stamp (no colons — the state file is a path)."""
    return (now or _utc_now()).strftime("%Y%m%dT%H%M%SZ")


# --------------------------------------------------------------------------
# run state
# --------------------------------------------------------------------------
def mint_run() -> Dict[str, Any]:
    """Mint the TWO canaries for ONE paid compaction (amendment 8.6)."""
    return {
        "schema": SCHEMA_VERSION,
        "plan": "PLAN-179",
        "wave_item": "W0-US1",
        "run_id": uuid.uuid4().hex[:12],
        "armed_utc": _utc_iso(),
        "canary_post": CANARY_PREFIX[CHANNEL_POST] + uuid.uuid4().hex[:12],
        "canary_ss": CANARY_PREFIX[CHANNEL_SS] + uuid.uuid4().hex[:12],
        "records": [],
    }


def load_run(path: Path) -> Dict[str, Any]:
    """Read a run file. Raises on unreadable/invalid — callers decide."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("run state is not a JSON object")
    return data


def _write_run(path: Path, run: Dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(run, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _append_ledger(directory: Path, run: Dict[str, Any],
                   record: Dict[str, Any]) -> None:
    """Append ONE JSONL line to the subtract-ledger (amendment 8.6).

    US2 counts ``kind == "arm"`` lines and subtracts them from the observed
    compaction frequency, so the probe cannot inflate its own measurement.
    """
    directory.mkdir(parents=True, exist_ok=True)
    line = {
        "utc": record.get("utc"),
        "run_id": run.get("run_id"),
        "kind": record.get("kind"),
        "channel": record.get("channel"),
        "verdict": record.get("verdict"),
        "state_file": run.get("state_file"),
    }
    with (directory / LEDGER_NAME).open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(line, sort_keys=True) + "\n")


def append_record(path: Path, record: Dict[str, Any]) -> Dict[str, Any]:
    """APPEND (never overwrite) a record to the run file + the ledger."""
    run = load_run(path)
    rec = dict(record)
    rec.setdefault("utc", _utc_iso())
    records = run.get("records")
    if not isinstance(records, list):
        records = []
    records.append(rec)
    run["records"] = records
    _write_run(path, run)
    _append_ledger(path.parent, run, rec)
    return run


def _new_run_path(directory: Path, now: Optional[datetime] = None) -> Path:
    """``<utc-stamp>.json``, with a suffix when two arms share a second."""
    stamp = _utc_stamp(now)
    path = directory / (stamp + ".json")
    n = 1
    while path.exists():
        path = directory / ("%s-%d.json" % (stamp, n))
        n += 1
    return path


def list_runs(root: Optional[Path] = None) -> List[Path]:
    directory = state_dir(root)
    if not directory.is_dir():
        return []
    return sorted(p for p in directory.glob("*.json") if p.is_file())


def latest_run_path(root: Optional[Path] = None) -> Optional[Path]:
    runs = list_runs(root)
    return runs[-1] if runs else None


def arm(root: Optional[Path] = None) -> Tuple[Path, Dict[str, Any]]:
    """Mint + persist a run; returns ``(state_path, run)``."""
    directory = state_dir(root)
    directory.mkdir(parents=True, exist_ok=True)
    path = _new_run_path(directory)
    run = mint_run()
    run["state_file"] = path.name
    _write_run(path, run)
    run = append_record(path, {"kind": "arm", "channel": None, "verdict": None})
    return path, run


# --------------------------------------------------------------------------
# injection side (--hook)
# --------------------------------------------------------------------------
def canary_text(channel: str, state_path: Optional[str] = None) -> str:
    """The line injected for ``channel`` — or "" when the probe is UNARMED.

    PLAN-179 W0 US1 / amendment 8.6: absent ``$CEO_COMPACTION_PROBE_CANARY``
    is a STRICT no-op. Any read failure is also a no-op (fail-open: this
    runs inside a live session).
    """
    if channel not in CHANNELS:
        return ""
    raw = state_path if state_path is not None else os.environ.get(CANARY_ENV)
    if not raw:
        return ""
    try:
        run = load_run(Path(raw))
    except Exception:
        return ""
    key = "canary_post" if channel == CHANNEL_POST else "canary_ss"
    token = run.get(key)
    if not isinstance(token, str) or not token:
        return ""
    return (
        "[PLAN-179 W0 US1 channel probe — operator-armed, local only] "
        "If you can read this line after a compaction, echo this token "
        "VERBATIM in your next reply: " + token
    )


def hook_payload(channel: str, state_path: Optional[str] = None
                 ) -> Dict[str, Any]:
    """The hook stdout object — ``{}`` when unarmed (schema-compliant allow)."""
    text = canary_text(channel, state_path)
    if not text:
        return {}
    return {
        "hookSpecificOutput": {
            "hookEventName": _EVENT_NAME[channel],
            "additionalContext": text,
        }
    }


def _record_injection(channel: str, state_path: Optional[str]) -> None:
    """Best-effort: note that the channel FIRED (distinct from consumed).

    Without this, a NEITHER verdict cannot distinguish "the hook never ran"
    from "the hook ran and the harness dropped its output" — and that
    distinction is the whole point of a channel probe.
    """
    raw = state_path if state_path is not None else os.environ.get(CANARY_ENV)
    if not raw:
        return
    try:
        append_record(Path(raw), {"kind": "inject", "channel": channel,
                                  "verdict": None})
    except Exception:
        pass  # fail-open — a live session must never break on probe I/O


# --------------------------------------------------------------------------
# detection / verdict
# --------------------------------------------------------------------------
def detect(text: str, run: Dict[str, Any]) -> Tuple[bool, bool]:
    """``(post_found, ss_found)`` — exact-token containment, nothing fuzzy."""
    post = run.get("canary_post")
    ss = run.get("canary_ss")
    found_post = bool(isinstance(post, str) and post and post in text)
    found_ss = bool(isinstance(ss, str) and ss and ss in text)
    return found_post, found_ss


def verdict_for(found_post: bool, found_ss: bool) -> Tuple[str, int]:
    """Map the two booleans onto ``(verdict, exit-code)``."""
    if found_post and found_ss:
        return VERDICT_BOTH, EXIT_OK
    if found_post:
        return VERDICT_POST_ONLY, EXIT_PARTIAL
    if found_ss:
        return VERDICT_SS_ONLY, EXIT_PARTIAL
    return VERDICT_NEITHER, EXIT_NEITHER


def _is_self_observation(observation: Path, run_path: Path) -> bool:
    """Guard: the run file and the ledger CONTAIN the canaries verbatim.

    Verifying against them would always say "both delivered" — a probe that
    cannot fail. Refuse instead (exit 2).
    """
    obs = observation.resolve()
    if obs == run_path.resolve():
        return True
    try:
        return obs.parent.resolve() == run_path.parent.resolve()
    except OSError:
        return False


# --------------------------------------------------------------------------
# modes
# --------------------------------------------------------------------------
def _arm_instructions(path: Path, run: Dict[str, Any]) -> List[str]:
    """The exact operator steps. Printed, never executed by this script."""
    me = str(Path(__file__).resolve())
    return [
        "PLAN-179 W0 US1 — channel probe ARMED (run_id=%s)" % run["run_id"],
        "state file : %s" % path,
        "canary #1  : %s   (channel %s)" % (run["canary_post"], CHANNEL_POST),
        "canary #2  : %s   (channel %s)" % (run["canary_ss"], CHANNEL_SS),
        "",
        "OPERATOR STEPS (local only — one paid compaction, two canaries):",
        "",
        "1. Arm the injection side in the shell that will start the session:",
        '     export %s="%s"' % (CANARY_ENV, path),
        "",
        "2. Wire BOTH channels in .claude/settings.local.json — the",
        "   per-machine, GITIGNORED layer. NEVER .claude/settings.json:",
        "   that file is canonical + guarded, and this wiring is temporary.",
        '     PostCompact  -> python3 "%s" --hook %s' % (me, CHANNEL_POST),
        '     SessionStart (matcher "compact")',
        '                  -> python3 "%s" --hook %s' % (me, CHANNEL_SS),
        "",
        "3. Start a session in that shell and reach a REAL compaction",
        "   (let the context fill, or run /compact).",
        "",
        "4. Immediately after compaction, ask the model: 'print verbatim any",
        "   line starting with CANARY- that you can see in your context'.",
        "   Save the raw reply to a file, e.g. /tmp/obs.txt.",
        "",
        "5. Verify (0 = both, 3 = exactly one, 1 = neither):",
        '     python3 "%s" --verify /tmp/obs.txt' % me,
        "",
        "6. Unwire settings.local.json and unset %s." % CANARY_ENV,
        "",
        "Accounting: this arm added one 'arm' line to %s; US2 subtracts"
        % LEDGER_NAME,
        "those lines so probe-induced compactions do not contaminate the",
        "real compaction-frequency measurement (amendment 8.6).",
    ]


def cmd_arm(root: Optional[Path] = None) -> int:
    path, run = arm(root)
    for line in _arm_instructions(path, run):
        print(line)
    return EXIT_OK


def _resolve_run_path(explicit: Optional[str],
                      root: Optional[Path] = None) -> Optional[Path]:
    """--state, then $CEO_COMPACTION_PROBE_CANARY, then the newest run."""
    if explicit:
        return Path(explicit)
    env = os.environ.get(CANARY_ENV)
    if env:
        return Path(env)
    return latest_run_path(root)


def cmd_verify(observation_arg: str, state_arg: Optional[str],
               root: Optional[Path] = None) -> int:
    run_path = _resolve_run_path(state_arg, root)
    if run_path is None or not run_path.is_file():
        sys.stderr.write(
            "REFUSED: no armed run found (run --arm first, or pass --state).\n"
        )
        return EXIT_REFUSED
    observation = Path(observation_arg)
    if not observation.is_file():
        sys.stderr.write("REFUSED: observation file not found: %s\n"
                         % observation)
        return EXIT_REFUSED
    if _is_self_observation(observation, run_path):
        sys.stderr.write(
            "REFUSED: self-observation — the observation file lives in the "
            "probe state dir, which already contains the canaries verbatim.\n"
        )
        return EXIT_REFUSED
    try:
        run = load_run(run_path)
    except Exception as exc:
        sys.stderr.write("REFUSED: unreadable run state: %s\n" % str(exc)[:120])
        return EXIT_REFUSED
    text = observation.read_text(encoding="utf-8", errors="replace")
    found_post, found_ss = detect(text, run)
    verdict, code = verdict_for(found_post, found_ss)
    append_record(run_path, {
        "kind": "verdict", "channel": None, "verdict": verdict,
        "found_postcompact": found_post, "found_sessionstart_compact": found_ss,
        "observation_bytes": len(text.encode("utf-8")),
    })
    print("verdict: %s" % verdict)
    print("  %s : %s" % (CHANNEL_POST, "DELIVERED" if found_post else "absent"))
    print("  %s : %s" % (CHANNEL_SS, "DELIVERED" if found_ss else "absent"))
    print("recorded in: %s" % run_path)
    return code


def cmd_status(root: Optional[Path] = None) -> int:
    directory = state_dir(root)
    runs = list_runs(root)
    print("state dir : %s" % directory)
    print("armed env : %s" % (os.environ.get(CANARY_ENV) or "(unset — no-op)"))
    print("runs      : %d" % len(runs))
    for path in runs:
        try:
            run = load_run(path)
        except Exception as exc:
            print("  %s  UNREADABLE (%s)" % (path.name, str(exc)[:60]))
            continue
        verdicts = [r.get("verdict") for r in run.get("records", [])
                    if isinstance(r, dict) and r.get("kind") == "verdict"]
        injects = [r.get("channel") for r in run.get("records", [])
                   if isinstance(r, dict) and r.get("kind") == "inject"]
        print("  %s  run_id=%s  injected=%s  verdict=%s"
              % (path.name, run.get("run_id"),
                 ",".join(sorted(set(c for c in injects if c))) or "-",
                 verdicts[-1] if verdicts else "-"))
    return EXIT_OK


def _self_test_cases(tmp: Path) -> List[Tuple[str, bool]]:
    """(name, ok) pairs — the probe's own falsifiability checks.

    Caller (``cmd_self_test``) restores ``$CEO_COMPACTION_PROBE_CANARY``:
    the unarmed case has to see it ABSENT, and a self-test must not leave
    the operator's shell state changed.
    """
    os.environ.pop(CANARY_ENV, None)
    cases = [("unarmed hook is a strict no-op",
              hook_payload(CHANNEL_POST) == {} and canary_text(CHANNEL_SS) == "")]
    path, run = arm(tmp)
    cases.append(("arm persists a run file", path.is_file()))
    cases.append(("arm appends one ledger line",
                  (tmp / STATE_REL / LEDGER_NAME).read_text(
                      encoding="utf-8").count("\n") == 1))
    payload = hook_payload(CHANNEL_POST, str(path))
    injected = payload.get("hookSpecificOutput", {}).get("additionalContext", "")
    cases.append(("armed hook injects the postcompact canary",
                  run["canary_post"] in injected))
    cases.append(("channels carry distinct canaries",
                  run["canary_ss"] not in injected))
    cases.append(("detect: neither", detect("nothing here", run) == (False, False)))
    cases.append(("detect: both",
                  detect(run["canary_post"] + " " + run["canary_ss"], run)
                  == (True, True)))
    cases.append(("verdict mapping",
                  verdict_for(True, True) == (VERDICT_BOTH, EXIT_OK)
                  and verdict_for(True, False) == (VERDICT_POST_ONLY, EXIT_PARTIAL)
                  and verdict_for(False, True) == (VERDICT_SS_ONLY, EXIT_PARTIAL)
                  and verdict_for(False, False) == (VERDICT_NEITHER, EXIT_NEITHER)))
    obs = tmp / "obs.txt"
    obs.write_text("model said: " + run["canary_ss"], encoding="utf-8")
    cases.append(("verify partial exits 3",
                  cmd_verify(str(obs), str(path), tmp) == EXIT_PARTIAL))
    cases.append(("verify refuses self-observation",
                  cmd_verify(str(path), str(path), tmp) == EXIT_REFUSED))
    return cases


def cmd_self_test() -> int:
    import tempfile

    saved = os.environ.get(CANARY_ENV)
    try:
        with tempfile.TemporaryDirectory() as td:
            cases = _self_test_cases(Path(td))
    finally:
        if saved is None:
            os.environ.pop(CANARY_ENV, None)
        else:
            os.environ[CANARY_ENV] = saved
    failed = 0
    for name, ok in cases:
        print("  %s %s" % ("PASS" if ok else "FAIL", name))
        if not ok:
            failed += 1
    print("self-test: %d/%d passed" % (len(cases) - failed, len(cases)))
    return EXIT_OK if failed == 0 else EXIT_NEITHER


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------
def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="probe_postcompact_channel.py",
        description="PLAN-179 W0 US1 — live channel probe (operator/local only).",
    )
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("--arm", action="store_true",
                   help="mint both canaries, persist, print operator steps")
    g.add_argument("--hook", choices=list(CHANNELS),
                   help="injection side (wired temporarily by the operator)")
    g.add_argument("--verify", metavar="FILE",
                   help="verify observed post-compaction text")
    g.add_argument("--status", action="store_true", help="list armed runs")
    g.add_argument("--self-test", dest="self_test", action="store_true",
                   help="in-process assertions; no compaction, no spend")
    p.add_argument("--state", metavar="PATH", default=None,
                   help="explicit run state file (default: $%s, else newest)"
                        % CANARY_ENV)
    return p


def main(argv: Optional[List[str]] = None) -> None:
    """Always raises SystemExit — the exit code IS the verdict."""
    args = _build_parser().parse_args(argv)

    if args.hook:
        # PLAN-179 W0 US1 — the ONE mode exempt from the exit-2 refusal: a
        # wired hook must never exit non-zero (the harness reads that as a
        # hook error). In CI it degrades to the same `{}` no-op as unarmed.
        if ci_reason() is not None:
            print("{}")
            raise SystemExit(EXIT_OK)
        try:
            payload = hook_payload(args.hook, args.state)
            if payload:
                _record_injection(args.hook, args.state)
        except Exception as exc:  # fail-open inside a live session
            sys.stderr.write("# probe_postcompact_channel fail-open: %s\n"
                             % str(exc)[:120])
            payload = {}
        print(json.dumps(payload))
        raise SystemExit(EXIT_OK)

    reason = ci_reason()
    if reason is not None:
        sys.stderr.write(
            "REFUSED: probe_postcompact_channel is OPERATOR/LOCAL ONLY and "
            "$%s is set (amendment 8.6). It spends a real compaction and "
            "mutates local state. Unset $%s to run it locally.\n"
            % (reason, reason)
        )
        raise SystemExit(EXIT_REFUSED)

    if args.arm:
        raise SystemExit(cmd_arm())
    if args.verify:
        raise SystemExit(cmd_verify(args.verify, args.state))
    if args.status:
        raise SystemExit(cmd_status())
    raise SystemExit(cmd_self_test())


if __name__ == "__main__":
    main()
