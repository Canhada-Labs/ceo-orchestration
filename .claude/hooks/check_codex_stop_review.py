#!/usr/bin/env python3
"""Inverted pair-rail Stop-review gate for the Codex harness (PLAN-155 Wave 6).

## What this hook is

The pair-rail, direction-INVERTED. Under Claude Code the operating model is
Anthropic and the cross-LLM reviewer is OpenAI Codex (``check_pair_rail.py`` +
``_lib/adapters/codex.py`` role 2). Under the **Codex** harness this hook
inverts it: **the operating model is OpenAI Codex and the reviewer is
Anthropic Claude** (``claude -p``, non-interactive, verified on claude
2.1.206). The "no single model is both author and sole reviewer" property
holds in BOTH directions — the same-vendor caveat is direction-neutral, not
deleted (see ``PLAN-155/artifacts/same-vendor-caveat-inverted.md``).

Registered ONLY in ``templates/codex/hooks.json`` (Stop entry) — it is a
Codex-harness surface, never wired into this repo's ``.claude/settings.json``.

## Behavior (Stop event, verified codex-cli 0.139.0 primitive)

On Stop, codex 0.139 ENFORCES ``{"decision":"block","reason":...}`` — it
auto-continues the turn, feeds ``reason`` to the model, and re-fires Stop with
``stop_hook_active: true`` (transcript:
``PLAN-155/artifacts/stop-block-transcript.md``). This hook uses that
primitive:

1. If the session touched NO L3/canonical paths → allow (``{}``); nothing to
   review.
2. If it touched canonical paths and a matching **APPROVE** review record
   exists → allow.
3. If a matching **REJECT** record exists → block with the findings (address
   them, re-review) — unless this is the loop-guard re-entry
   (``stop_hook_active``), in which case allow-with-loud + RED breadcrumb
   (never infinite-block; the pre-push gate is the teeth).
4. If NO matching record exists → block with the review instruction (run the
   ``claude -p`` reviewer, pipe its verdict to ``--record``) — unless
   ``stop_hook_active`` (the model was told and did not produce a record):
   allow-with-loud + RED breadcrumb (review ABANDONED; pre-push backstop).

## Capability-matrix status (binding vocabulary)

**PARTIAL, stop-time + push-time.** Residuals, each named:

- **Kill-the-session / refuse-twice.** Killing the ``codex`` process, or
  hitting stop twice without producing a record, abandons the Stop gate. The
  git **pre-push** review gate (``templates/codex/pre-push-review-gate.sh``)
  is the teeth for that path. RED-on-absence: the abandonment is
  breadcrumbed to ``audit-log.errors``, never silently allowed-and-forgotten.
- **Hook death / de-trust = silent allow.** A killed/untrusted hook is a
  silent no-op on codex (``PLAN-155/artifacts/failure-semantics-matrix.md``);
  the Wave-5 arming check + the RED-on-absence chain assertions
  (``scripts/codex-advisory-teeth.py``) are the detection layer.
- **Reviewer provenance not attested.** The ``--record`` path reads the
  reviewer's stdout; it cannot prove ``claude -p`` actually produced it (an
  operator could pipe ``echo APPROVE``). Backstops: pre-push + CI review
  record; the operator-visible instruction; CODEOWNERS at push.
- **Path-set fingerprint, not content.** A review record is keyed to the
  SORTED canonical PATH SET, not the byte content — re-editing the same
  files after an APPROVE could ride a stale record within one session. The
  finer layers are the next-Stop re-review and CI.

## Reviewer pin (OQ3 — PROVISIONAL, pending Owner ratification)

- model: ``claude-opus-4-8`` (override ``CEO_PAIR_RAIL_REVIEWER_MODEL``)
- per-review token ceiling: ``100000`` (override
  ``CEO_PAIR_RAIL_REVIEWER_MAX_TOKENS``)
- verdict vocabulary: ``VERDICT: APPROVE`` / ``VERDICT: REJECT`` with
  ``file:line`` findings.

Mirror of the Codex reviewer pin (``.claude/governance/codex-cli-pin.txt``);
a ``docs/provider-pricing.md``-consistent row + this named override land in
the same commit that ratifies OQ3 (Wave 7 docs sweep).

## Contract

- Stdlib only, Python >= 3.9, ``from __future__ import annotations``.
- Dispatch seam (PLAN-155 Wave 1, debate A1): the adapter is resolved via
  ``_lib.adapters.resolve()`` so ``CEO_HOOK_ADAPTER=codex`` emits the codex
  Stop wire and the default/claude path stays sane.
- Fail-open on INFRASTRUCTURE (parse error / import failure / git absent →
  allow, breadcrumb); this is NOT a security edit-matcher, so a garbled Stop
  event does not fail-closed (a Stop-block on garbage would wedge every
  session). The RED-on-absence breadcrumbs are the honesty layer.
- Kill-switch: ``CEO_CODEX_STOP_REVIEW=0`` → allow (no-op).

## Modes

- default: Stop-hook decision (reads the Stop envelope from stdin).
- ``--record --session <id>``: read a ``claude -p`` reviewer transcript from
  stdin, parse the verdict + ``file:line`` findings, append a review-log
  record. Exits 0 on every path (a broken reviewer records ``UNAVAILABLE``,
  never a fabricated APPROVE).
- ``--emit-instruction``: print the block instruction text (test/inspection).
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

_KILL_SWITCH_ENV = "CEO_CODEX_STOP_REVIEW"
_HOOK_VERSION = "1.0.0"

_REVIEW_LOG_FILENAME = "codex-review-log.jsonl"
_REVIEW_LOG_MAX_LINES = 2000  # bounded; oldest dropped on append

_DEFAULT_REVIEWER_MODEL = "claude-opus-4-8"  # OQ3 PROVISIONAL
_DEFAULT_REVIEWER_MAX_TOKENS = 100000  # OQ3 PROVISIONAL

# Verdict vocabulary (mirror of the Codex-side pair-rail labels).
_VERDICT_APPROVE = "APPROVE"
_VERDICT_REJECT = "REJECT"
_VERDICT_UNAVAILABLE = "UNAVAILABLE"


# ---------------------------------------------------------------------------
# breadcrumbs / audit err sidecar (RED-on-absence honesty layer)
# ---------------------------------------------------------------------------

def _breadcrumb(msg: str) -> None:
    sys.stderr.write("# check_codex_stop_review: %s\n" % str(msg)[:200])


def _audit_err_path() -> Path:
    audit_dir = os.environ.get("CEO_AUDIT_LOG_DIR")
    if audit_dir:
        base = Path(audit_dir)
    else:
        home = os.environ.get("HOME") or "/tmp"
        base = Path(home) / ".claude" / "projects" / "ceo-orchestration"
    override = os.environ.get("CEO_AUDIT_LOG_ERR")
    return Path(override) if override else base / "audit-log.errors"


def _write_red_breadcrumb(msg: str) -> None:
    """RED-on-absence: record an abandoned/unavailable review to the audit
    err sidecar (the same sidecar Wave 4 uses). Never raises."""
    line = "%s STOP-REVIEW-RED %s" % (
        datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        str(msg)[:400],
    )
    _breadcrumb(msg)
    try:
        path = _audit_err_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:
        return


# ---------------------------------------------------------------------------
# state dir + review log (check_subagent_start.py resolution precedent)
# ---------------------------------------------------------------------------

def _state_dir() -> Path:
    override = os.environ.get("CEO_CODEX_REVIEW_STATE_DIR")
    if override:
        return Path(override)
    audit_dir = os.environ.get("CEO_AUDIT_LOG_DIR")
    if audit_dir:
        return Path(audit_dir)
    home = os.environ.get("HOME") or "/tmp"
    return Path(home) / ".claude" / "projects" / "ceo-orchestration" / "state"


def _review_log_path() -> Path:
    return _state_dir() / _REVIEW_LOG_FILENAME


def _append_review_record(record: Dict[str, Any]) -> bool:
    """Append one review record (JSONL). Bounded, atomic-ish, never raises."""
    try:
        path = _review_log_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        lines: List[str] = []
        if path.is_file():
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except Exception:
                lines = []
        lines.append(json.dumps(record, ensure_ascii=False, sort_keys=True))
        if len(lines) > _REVIEW_LOG_MAX_LINES:
            lines = lines[-_REVIEW_LOG_MAX_LINES:]
        tmp = path.with_name(path.name + ".tmp.%d" % os.getpid())
        tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
        os.replace(str(tmp), str(path))
        return True
    except Exception as exc:  # pragma: no cover — defensive
        _breadcrumb("review-log append failed: %s" % str(exc)[:120])
        return False


def _read_review_records() -> List[Dict[str, Any]]:
    path = _review_log_path()
    if not path.is_file():
        return []
    out: List[Dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception:
                continue
            if isinstance(obj, dict):
                out.append(obj)
    except Exception:
        return out
    return out


def latest_review_record(
    session_id: str, fingerprint: str
) -> Optional[Dict[str, Any]]:
    """Most-recent review record matching this session AND path-set
    fingerprint. A record with a non-matching fingerprint (the canonical
    path set changed since it was written) does NOT satisfy the gate."""
    match: Optional[Dict[str, Any]] = None
    for rec in _read_review_records():
        if str(rec.get("session_id") or "") != session_id:
            continue
        if str(rec.get("fingerprint") or "") != fingerprint:
            continue
        match = rec  # later lines win (append order == chronological)
    return match


# ---------------------------------------------------------------------------
# L3 / canonical path detection (working tree)
# ---------------------------------------------------------------------------

# Fallback prefix set — mirror of check_canonical_edit._CANONICAL_PREFIXES.
# Used ONLY if the real predicate cannot be imported. Coarser (first-segment
# prefix) — it over-triggers review, which is the safe direction (a missed
# L3 touch is the danger; an extra review is not).
_FALLBACK_CANONICAL_PREFIXES = frozenset(
    {".claude", ".github", "scripts", "SPEC", "PROTOCOL.md"}
)


def _import_is_canonical():  # type: ignore[no-untyped-def]
    """Import check_canonical_edit._is_canonical, or None on failure."""
    try:
        import check_canonical_edit as _cce  # type: ignore
        fn = getattr(_cce, "_is_canonical", None)
        return fn if callable(fn) else None
    except Exception:
        return None


def _is_l3_path(rel_path: str, repo_root: Path, is_canonical) -> bool:
    """True if rel_path is an L3/canonical governed path.

    Primary: check_canonical_edit._is_canonical (source of truth — the same
    predicate the edit-time guard uses; its guard set is a superset covering
    hooks/kernel/plans/ADRs/workflows). Fallback: first-segment prefix match.
    """
    if is_canonical is not None:
        try:
            return bool(is_canonical(str(repo_root / rel_path), repo_root))
        except Exception:
            pass
    first_seg = rel_path.replace(os.sep, "/").split("/", 1)[0]
    return first_seg in _FALLBACK_CANONICAL_PREFIXES


def _git_changed_paths(repo_root: Path) -> List[str]:
    """Repo-relative paths changed in the working tree (tracked diff vs HEAD
    + untracked). Empty on any git failure (fail-open)."""
    paths: List[str] = []

    def _run(args: List[str]) -> List[str]:
        try:
            proc = subprocess.run(
                ["git", "-C", str(repo_root)] + args,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=10,
            )
        except Exception:
            return []
        if proc.returncode != 0:
            return []
        text = proc.stdout.decode("utf-8", errors="replace")
        return [ln.strip() for ln in text.splitlines() if ln.strip()]

    # Tracked, staged + unstaged, against HEAD.
    paths.extend(_run(["diff", "--name-only", "HEAD"]))
    # Untracked (new files not yet added).
    paths.extend(_run(["ls-files", "--others", "--exclude-standard"]))
    # Dedup preserving order.
    seen = set()
    uniq: List[str] = []
    for p in paths:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    return uniq


def l3_paths(repo_root: Path) -> List[str]:
    """Sorted unique L3/canonical paths touched in the working tree."""
    is_canonical = _import_is_canonical()
    out = [
        p
        for p in _git_changed_paths(repo_root)
        if _is_l3_path(p, repo_root, is_canonical)
    ]
    return sorted(set(out))


def fingerprint(paths: List[str]) -> str:
    """sha256 over the sorted unique path set. Stable across processes."""
    joined = "\n".join(sorted(set(paths)))
    return hashlib.sha256(joined.encode("utf-8", errors="replace")).hexdigest()


# ---------------------------------------------------------------------------
# reviewer pin + instruction
# ---------------------------------------------------------------------------

def reviewer_model() -> str:
    val = os.environ.get("CEO_PAIR_RAIL_REVIEWER_MODEL", "").strip()
    return val or _DEFAULT_REVIEWER_MODEL


def reviewer_max_tokens() -> int:
    raw = os.environ.get("CEO_PAIR_RAIL_REVIEWER_MAX_TOKENS", "").strip()
    if raw:
        try:
            return int(raw)
        except ValueError:
            pass
    return _DEFAULT_REVIEWER_MAX_TOKENS


def build_review_instruction(
    *, session_id: str, paths: List[str], repo_root: Path
) -> str:
    """The Stop-block instruction text handed to the operating (Codex) model.

    Direction-neutral same-vendor property is stated inline: the operator is
    OpenAI Codex and the reviewer is Anthropic Claude.
    """
    model = reviewer_model()
    max_tok = reviewer_max_tokens()
    path_list = " ".join(paths)
    hook_path = str(Path(__file__).resolve())
    # A single copy-paste pipeline the model can run as one Bash tool call:
    #   diff of the L3 paths -> claude -p reviewer -> --record.
    review_cmd = (
        "git -C {root} diff HEAD -- {paths} | "
        "claude -p --model {model} "
        "'INVERTED PAIR-RAIL CROSS-MODEL REVIEW. You are a READ-ONLY reviewer "
        "(Anthropic Claude) reviewing a diff produced by an OpenAI Codex "
        "session against governed (L3/canonical) paths. Do NOT emit any "
        "patch/diff. Judge governance + correctness. End with exactly one "
        "line: \"VERDICT: APPROVE\" or \"VERDICT: REJECT\"; if REJECT, list "
        "findings as file:line above it.' "
        "| python3 {hook} --record --session {sid}"
    ).format(
        root=str(repo_root),
        paths=path_list,
        model=model,
        hook=hook_path,
        sid=session_id,
    )
    return (
        "STOP GATE -- inverted pair-rail (Codex operates, Claude reviews). "
        "This session edited L3/canonical paths that require a cross-model "
        "review before you may stop:\n"
        "  " + "\n  ".join(paths) + "\n\n"
        "No single model is both author and sole reviewer: here the operating "
        "model is OpenAI Codex and the reviewer is Anthropic Claude. Run the "
        "review and record its verdict (one Bash call):\n\n"
        "  " + review_cmd + "\n\n"
        "Reviewer pinned to " + model + " (PROVISIONAL, OQ3; override "
        "CEO_PAIR_RAIL_REVIEWER_MODEL); token ceiling " + str(max_tok) + " "
        "(CEO_PAIR_RAIL_REVIEWER_MAX_TOKENS). On APPROVE you may stop; on "
        "REJECT, address the file:line findings and let this gate re-review. "
        "Killing the session abandons this gate -- the git pre-push review "
        "gate is the backstop."
    )


# ---------------------------------------------------------------------------
# verdict parsing (--record mode)
# ---------------------------------------------------------------------------

def parse_verdict(reviewer_stdout: str) -> Tuple[str, List[str]]:
    """Parse a reviewer transcript into (verdict, findings).

    Fail-SAFE: an empty / verdict-less transcript is ``UNAVAILABLE``, NEVER a
    fabricated APPROVE (RED-on-absence: absence of a clear APPROVE is not
    approval). An explicit REJECT wins over an APPROVE if both appear (the
    stricter reading). ``file:line`` findings are surfaced (clamped).
    """
    if not isinstance(reviewer_stdout, str) or not reviewer_stdout.strip():
        return _VERDICT_UNAVAILABLE, []

    lines = reviewer_stdout.splitlines()
    verdict: Optional[str] = None
    # Scan for an explicit "VERDICT:" line first (the pinned vocabulary).
    for ln in lines:
        up = ln.strip().upper()
        if up.startswith("VERDICT:"):
            tail = up.split(":", 1)[1].strip()
            if tail.startswith(_VERDICT_REJECT):
                return _VERDICT_REJECT, _extract_findings(lines)
            if tail.startswith(_VERDICT_APPROVE):
                verdict = _VERDICT_APPROVE
    if verdict == _VERDICT_APPROVE:
        return _VERDICT_APPROVE, _extract_findings(lines)

    # No "VERDICT:" line — fall back to a bare token, REJECT-biased.
    joined_up = reviewer_stdout.upper()
    if _VERDICT_REJECT in joined_up:
        return _VERDICT_REJECT, _extract_findings(lines)
    if _VERDICT_APPROVE in joined_up:
        return _VERDICT_APPROVE, _extract_findings(lines)
    return _VERDICT_UNAVAILABLE, []


def _extract_findings(lines: List[str]) -> List[str]:
    """Best-effort file:line finding extraction (clamped)."""
    import re

    pat = re.compile(r"[\w./\-]+\.[A-Za-z0-9]+:\d+")
    out: List[str] = []
    for ln in lines:
        for m in pat.findall(ln):
            if m not in out:
                out.append(m)
        if len(out) >= 50:
            break
    return out[:50]


def _record_main(argv: List[str]) -> int:
    """--record mode: parse the reviewer transcript on stdin, append a record."""
    session_id = ""
    fp_override = ""
    it = iter(range(len(argv)))
    for i in it:
        if argv[i] == "--session" and i + 1 < len(argv):
            session_id = argv[i + 1]
        elif argv[i] == "--fingerprint" and i + 1 < len(argv):
            fp_override = argv[i + 1]
    session_id = session_id or os.environ.get("CLAUDE_SESSION_ID", "") or ""

    try:
        reviewer_stdout = sys.stdin.read()
    except Exception:
        reviewer_stdout = ""

    verdict, findings = parse_verdict(reviewer_stdout)

    repo_root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    fp = fp_override or fingerprint(l3_paths(repo_root))

    record = {
        "session_id": session_id,
        "verdict": verdict,
        "reviewer_model": reviewer_model(),
        "fingerprint": fp,
        "findings": findings,
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hook_version": _HOOK_VERSION,
    }
    _append_review_record(record)
    if verdict == _VERDICT_UNAVAILABLE:
        _write_red_breadcrumb(
            "reviewer produced no parseable verdict (recorded UNAVAILABLE) "
            "session=%s" % session_id[:64]
        )
    # Human-readable acknowledgement (the model sees this in the Bash output).
    sys.stdout.write(
        "recorded review verdict=%s findings=%d fingerprint=%s\n"
        % (verdict, len(findings), fp[:12])
    )
    return 0


# ---------------------------------------------------------------------------
# Stop-hook decision + emit
# ---------------------------------------------------------------------------

def decide(
    *,
    repo_root: Path,
    session_id: str,
    stop_hook_active: bool,
):  # -> Decision-like object built by the caller
    """Pure decision: returns (allow, reason_or_none, system_message, red).

    ``red`` True marks a RED-on-absence event the caller must breadcrumb.
    """
    paths = l3_paths(repo_root)
    if not paths:
        return (
            True,
            None,
            "Stop-review: no L3/canonical paths touched; no cross-model "
            "review required.",
            False,
        )

    fp = fingerprint(paths)
    rec = latest_review_record(session_id, fp)

    if rec is not None:
        verdict = str(rec.get("verdict") or "").upper()
        model = str(rec.get("reviewer_model") or "?")
        if verdict == _VERDICT_APPROVE:
            return (
                True,
                None,
                "Stop-review: cross-model review APPROVE by %s over %d L3 "
                "path(s)." % (model, len(paths)),
                False,
            )
        if verdict == _VERDICT_REJECT:
            findings = rec.get("findings") or []
            fstr = (
                " Findings: " + "; ".join(str(f) for f in findings[:20])
                if findings
                else ""
            )
            if stop_hook_active:
                # Loop-guard re-entry with a standing REJECT: do NOT
                # infinite-block. Allow-with-loud; pre-push is the teeth.
                return (
                    True,
                    None,
                    "Stop-review: standing REJECT not cleared on loop-guard "
                    "re-entry; allowing stop (pre-push gate is the backstop)."
                    + fstr,
                    True,
                )
            return (
                False,
                "STOP GATE -- the cross-model reviewer (%s) returned REJECT "
                "for this diff. Address the findings, then let this gate "
                "re-review before stopping.%s" % (model, fstr),
                None,
                False,
            )
        # UNAVAILABLE or unknown verdict on record: reviewer was attempted
        # but produced nothing usable. Reviewer-unavailable posture (ADR-161
        # A20): do not block forever on a broken reviewer.
        return (
            True,
            None,
            "Stop-review: recorded verdict is %s (reviewer unavailable/"
            "unparseable); allowing stop (pre-push + CI are the backstops)."
            % (verdict or "UNKNOWN"),
            True,
        )

    # No matching record.
    if stop_hook_active:
        # The model was already told to review and did not produce a record.
        # Do not infinite-block: allow-with-loud + RED. Pre-push is the teeth.
        return (
            True,
            None,
            "Stop-review: review ABANDONED (no record after block); allowing "
            "stop. The git pre-push review gate is the backstop.",
            True,
        )
    instruction = build_review_instruction(
        session_id=session_id, paths=paths, repo_root=repo_root
    )
    return (False, instruction, None, False)


def _emit(adapter, contract, *, allow: bool, reason, system_message) -> None:
    """Emit the Stop decision through the resolved adapter (event-driven
    host egress). Stop family: block => {"decision":"block","reason"},
    allow => {} (+ systemMessage)."""
    decision = contract.Decision(
        allow=allow,
        reason=reason,
        system_message=system_message,
        extra={"hookEventName": "Stop"},
    )
    adapter_basename = (getattr(adapter, "__name__", "") or "").rsplit(".", 1)[-1]
    try:
        if adapter_basename == "claude":
            adapter.emit_decision(decision)
        else:
            adapter.emit_decision(decision, event=None)
    except Exception:
        # Last-resort: emit the codex Stop wire directly so a block is never
        # dropped (foreign JSON would be a silent allow — the S254 class).
        out: Dict[str, Any] = {}
        if not allow:
            out = {"decision": "block", "reason": reason or "review required"}
        elif system_message:
            out = {"systemMessage": system_message}
        sys.stdout.write(json.dumps(out, ensure_ascii=False) + "\n")


def _stop_main() -> int:
    if os.environ.get(_KILL_SWITCH_ENV, "").strip().lower() in {
        "0",
        "false",
        "off",
        "no",
    }:
        sys.stdout.write("{}\n")
        return 0

    try:
        from _lib import adapters as _adapters  # noqa: E402
        from _lib import contract as _contract  # noqa: E402
    except Exception:
        # Infrastructure import failure → fail-open allow (never wedge Stop).
        sys.stdout.write("{}\n")
        return 0

    adapter = _adapters.resolve()

    try:
        event = adapter.read_event(phase="Stop")
    except Exception:
        _emit(adapter, _contract, allow=True, reason=None, system_message=None)
        return 0

    if getattr(event, "parse_error", None):
        # Garbled Stop envelope is INFRASTRUCTURE (not a security edit
        # matcher) → allow. A Stop-block on garbage would wedge sessions.
        _emit(adapter, _contract, allow=True, reason=None, system_message=None)
        return 0

    raw = getattr(event, "raw_payload", {}) or {}
    session_id = str(getattr(event, "session_id", "") or "") or (
        os.environ.get("CLAUDE_SESSION_ID", "") or "unknown-session"
    )
    stop_hook_active = bool(raw.get("stop_hook_active"))
    repo_root = Path(
        str(getattr(event, "project", "") or "")
        or os.environ.get("CLAUDE_PROJECT_DIR")
        or os.getcwd()
    )

    try:
        allow, reason, system_message, red = decide(
            repo_root=repo_root,
            session_id=session_id,
            stop_hook_active=stop_hook_active,
        )
    except Exception as exc:
        _breadcrumb("decide() raised (fail-open allow): %s" % str(exc)[:120])
        _emit(adapter, _contract, allow=True, reason=None, system_message=None)
        return 0

    if red and system_message:
        _write_red_breadcrumb(system_message + " session=" + session_id[:64])

    _emit(
        adapter,
        _contract,
        allow=allow,
        reason=reason,
        system_message=system_message,
    )
    return 0


def main() -> int:
    argv = sys.argv[1:]
    if "--emit-instruction" in argv:
        repo_root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
        sid = os.environ.get("CLAUDE_SESSION_ID", "") or "unknown-session"
        sys.stdout.write(
            build_review_instruction(
                session_id=sid, paths=l3_paths(repo_root), repo_root=repo_root
            )
            + "\n"
        )
        return 0
    if "--record" in argv:
        return _record_main(argv)
    return _stop_main()


if __name__ == "__main__":
    sys.exit(main())
