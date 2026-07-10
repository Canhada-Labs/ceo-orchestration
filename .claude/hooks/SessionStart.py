#!/usr/bin/env python3
"""SessionStart lifecycle hook (PLAN-028 / ADR-056).

Fires at the start of every Claude Code session. Three responsibilities:

1. **Audit init** — emit a typed `session_start` event with session id,
   timestamp, hook version, and governance-file health snapshot.
2. **Cache warmup** — read Gate-1 governance files (CLAUDE.md,
   PROTOCOL.md, team.md, frontend-team.md) into process memory to
   warm the OS page cache for the first spawn call. Best-effort;
   failures log breadcrumb + continue.
3. **Governance state validate** — assert expected governance files
   exist + their SHA-256 hashes align with prior session (drift
   signal). Kill-switch aware.

## Fail-open contract (ADR-005)

Any internal exception → `{"decision":"allow"}`. The hook NEVER
blocks the session start on its own bug. Governance errors are
surfaced via breadcrumb to `audit-log.errors` and via an audit
event (`session_start(governance_state=degraded, reason=...)`),
but the session continues — the Owner sees the warning in the
audit-log dashboard, not in a broken session startup.

## Kill-switch

`CEO_EXTENDED_LIFECYCLE=0` disables this hook (and the three
siblings — SessionEnd/UserPromptSubmit/Stop). Default is ON
post-PLAN-028 land.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

_KILL_SWITCH_ENV = "CEO_EXTENDED_LIFECYCLE"
_HOOK_VERSION = "1.0.0"
_GATE_1_FILES: List[str] = [
    "CLAUDE.md",
    "PROTOCOL.md",
    ".claude/team.md",
    ".claude/frontend-team.md",
    ".claude/skills/core/ceo-orchestration/SKILL.md",
]

# PLAN-155 Wave 3b (SENT-CX-E) — Codex kill-switch surface boot tripwire.
#
# The `.codex` registration/rules/managed files + the operator `AGENTS.md`
# are the rail's OWN disarm surface under the Codex harness (debate A8).
# The edit-time canonical guard (check_canonical_edit.py `_CANONICAL_GUARDS`,
# same wave) blocks unsentineled writes to them; this boot re-hash is the
# BACKSTOP tripwire for the case where the edit-time guard was bypassed
# (shell-escape residual, or an out-of-session mutation). Because
# `SessionStart.py` is itself in `_KERNEL_PATHS`
# (check_arbitration_kernel.py), this extension rides the SENT-CX-E
# `CEO_KERNEL_OVERRIDE=PLAN-155-CODEX-KILLSWITCH-GUARD-EXTENSION` + ACK
# ceremony (pair-rail S265 F2 — corrects an earlier "sentinel-only" claim).
#
# RED-on-absence semantics (debate A2): a kill-switch file that was present
# and is now missing OR mutated turns the boot re-hash RED (a RED stderr
# breadcrumb + a governance-degraded systemMessage note). Silence from a
# fail-open rail is not health — vacuous green is the S254 dead-gate class
# this wave exists to catch.
#
# NO yellow-fatigue: the whole check is a NO-OP unless the Codex harness is
# actually installed (a `.codex` registration marker present). "Absent
# because never installed" is NOT red — in particular, in THIS framework
# repo the root `AGENTS.md` is the reviewer contract and there is no
# `.codex/`, so the tripwire never engages here.
_KILLSWITCH_FILES: List[str] = [
    ".codex/hooks.json",
    ".codex/config.toml",
    ".codex/rules/ceo.rules",
    "requirements.toml",
    "AGENTS.md",
]

#: Presence of ANY of these under the repo root means the Codex harness
#: registration is installed — the signal that arms the kill-switch
#: tripwire. Without one of them the surface files (`AGENTS.md`,
#: `requirements.toml`) are unrelated to Codex and MUST NOT be tracked
#: (no false RED on this repo's reviewer-contract `AGENTS.md`).
_KILLSWITCH_INSTALL_MARKERS: List[str] = [
    ".codex/hooks.json",
    ".codex/config.toml",
    ".codex/rules/ceo.rules",
]

#: Relative location of the persisted baseline hash manifest, under the
#: per-project state dir (the `onboarded.flag` precedent). The baseline
#: lives OUTSIDE the repo tree (and outside `.codex/`) so a repo-scoped
#: edit does not touch it; an attacker with full shell can rewrite both —
#: that is the documented residual, backstopped by CODEOWNERS/CI at push.
_KILLSWITCH_BASELINE_NAME = "codex_killswitch_baseline.json"


def _emit_observe(system_message: Optional[str] = None) -> str:
    """Emit a schema-compliant lifecycle hook output.

    Per Claude Code hook schema, lifecycle events (SessionStart /
    SessionEnd / Stop) accept only top-level fields:
      continue: bool, systemMessage: str, suppressOutput: bool,
      stopReason: str, decision: "approve" | "block".
    The `"allow"` value is NOT in the enum for lifecycle events.
    Observational hooks emit {"continue": true, "systemMessage": ...}.
    """
    out: Dict[str, object] = {"continue": True}
    if system_message:
        out["systemMessage"] = system_message
    return json.dumps(out, ensure_ascii=False)


def _kill_switch_active() -> bool:
    """True if CEO_EXTENDED_LIFECYCLE is set to '0' or 'false'."""
    val = os.environ.get(_KILL_SWITCH_ENV, "").strip().lower()
    return val in {"0", "false", "off", "no"}


def _gate_1_hash(repo_root: Path) -> Dict[str, Optional[str]]:
    """Return sha256 per Gate-1 file, or None if file absent."""
    result: Dict[str, Optional[str]] = {}
    for rel in _GATE_1_FILES:
        p = repo_root / rel
        try:
            if not p.is_file():
                result[rel] = None
                continue
            result[rel] = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
        except Exception:
            result[rel] = None
    return result


def _warmup_gate_1(repo_root: Path) -> int:
    """Read Gate-1 files into page cache. Returns bytes read (for audit)."""
    total = 0
    for rel in _GATE_1_FILES:
        p = repo_root / rel
        try:
            if p.is_file():
                total += len(p.read_bytes())
        except Exception:
            continue
    return total


# ---------------------------------------------------------------------------
# PLAN-155 Wave 3b (SENT-CX-E) — Codex kill-switch surface boot tripwire
# ---------------------------------------------------------------------------


def _hash_file16(path: Path) -> Optional[str]:
    """sha256[:16] of a file, or None if absent/unreadable (same shape as
    ``_gate_1_hash``)."""
    try:
        if not path.is_file():
            return None
        return hashlib.sha256(path.read_bytes()).hexdigest()[:16]
    except Exception:
        return None


def _codex_harness_installed(repo_root: Path) -> bool:
    """True iff a Codex-harness registration marker is present under the repo.

    The signal that the kill-switch tripwire should engage. Absent → the
    surface files (``AGENTS.md`` / ``requirements.toml``) are unrelated to
    Codex and are NOT tracked (no yellow-fatigue; no false RED on this
    repo's reviewer-contract ``AGENTS.md``). Never raises.
    """
    for rel in _KILLSWITCH_INSTALL_MARKERS:
        try:
            if (repo_root / rel).is_file():
                return True
        except Exception:
            continue
    return False


def _killswitch_baseline_path(repo_root: Path) -> Optional[Path]:
    """Resolve the persisted baseline path, or None on failure.

    Prefers the explicit ``CEO_PROJECT_STATE_DIR`` override (the isolated
    per-project state dir used by tests / subprocess hooks); falls back to
    the HOME-based per-project state dir (``_maybe_emit_first_run_wizard``
    precedent). Never raises.
    """
    try:
        override = os.environ.get("CEO_PROJECT_STATE_DIR", "").strip()
        if override:
            base = Path(override)
        else:
            base = Path.home() / ".claude" / "projects" / repo_root.name / "state"
        return base / _KILLSWITCH_BASELINE_NAME
    except Exception:
        return None


def _killswitch_hashes(repo_root: Path) -> Dict[str, str]:
    """Current sha256[:16] per PRESENT kill-switch file (absent files omitted)."""
    result: Dict[str, str] = {}
    for rel in _KILLSWITCH_FILES:
        h = _hash_file16(repo_root / rel)
        if h is not None:
            result[rel] = h
    return result


def _load_killswitch_baseline(path: Optional[Path]) -> Optional[Dict[str, str]]:
    """Load the baseline manifest (dict of rel→hash16), or None if absent/bad.

    A corrupt/foreign baseline is treated as absent (re-baseline on this
    boot) rather than raising. Never raises.
    """
    if path is None:
        return None
    try:
        if not path.is_file():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return None
        return {
            str(k): str(v)
            for k, v in data.items()
            if isinstance(k, str) and isinstance(v, str)
        }
    except Exception:
        return None


def _store_killswitch_baseline(path: Optional[Path], hashes: Dict[str, str]) -> None:
    """Best-effort write of the baseline manifest. Never raises."""
    if path is None:
        return
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(hashes, ensure_ascii=False, sort_keys=True),
            encoding="utf-8",
        )
    except Exception:
        return


def _check_killswitch_surface(repo_root: Path) -> Tuple[str, Optional[str], bool]:
    """Boot-time re-hash of the Codex kill-switch surface (debate A8 backstop).

    Returns ``(status, note, red)`` where ``status`` is one of
    ``"absent"`` (harness not installed — no-op),
    ``"baselined"`` (first sighting — baseline recorded, informational),
    ``"armed"`` (unchanged vs baseline — green),
    ``"tampered"`` (a tracked file is MISSING or MUTATED vs baseline — RED),
    ``"error"`` (internal failure — fail-open, no-op). ``note`` is an
    optional systemMessage fragment; ``red`` is True only for
    ``"tampered"``. NEVER raises (fail-open per ADR-005).

    RED-on-absence (debate A2): a file present at baseline time that is now
    missing OR whose hash changed is a tamper signal. The baseline is NOT
    overwritten on a RED verdict — the signal persists across boots until
    the surface is legitimately re-armed (delete the baseline, or re-run
    the installer arming check, Wave 5). A NEW surface file appearing (a
    legit install of another surface component) refreshes the baseline and
    is not RED.
    """
    try:
        if not _codex_harness_installed(repo_root):
            return ("absent", None, False)

        current = _killswitch_hashes(repo_root)
        baseline_path = _killswitch_baseline_path(repo_root)
        baseline = _load_killswitch_baseline(baseline_path)

        if baseline is None:
            # First sighting under an installed harness — record the
            # baseline. Informational, never RED (nothing to compare to).
            _store_killswitch_baseline(baseline_path, current)
            return (
                "baselined",
                (
                    "kill-switch tripwire: baselined %d Codex surface file(s)"
                    % len(current)
                ),
                False,
            )

        missing = sorted(rel for rel in baseline if rel not in current)
        mutated = sorted(
            rel for rel, h in baseline.items()
            if rel in current and current[rel] != h
        )
        added = sorted(rel for rel in current if rel not in baseline)

        if missing or mutated:
            # Do NOT overwrite the baseline — preserve the signal.
            detail = "kill-switch tripwire: RED"
            if mutated:
                detail += " — %d mutated %s" % (len(mutated), mutated)
            if missing:
                detail += " — %d removed %s" % (len(missing), missing)
            return ("tampered", detail, True)

        if added:
            # A new surface component was installed legitimately — extend
            # the baseline to cover it. Not RED.
            merged = dict(baseline)
            merged.update(current)
            _store_killswitch_baseline(baseline_path, merged)

        return (
            "armed",
            "kill-switch tripwire: %d Codex surface file(s) unchanged" % len(current),
            False,
        )
    except Exception:
        # Fail-open per ADR-005 — a tripwire bug never breaks the boot.
        return ("error", None, False)


# PLAN-136 W3 S2 — trusted persistent-instructions channel (PLAN-133 G1).
# The single trusted MOIM file at the project root. The BLOCKING validator
# (`_lib/guardrail_validator.validate_trusted_file`) refuses to load it when an
# injection pattern / oversize is detected, and the boot records the refusal via
# `audit_emit.emit_persistent_instructions_blocked` (no body / no path echoed).
_TRUSTED_INSTRUCTIONS_REL = ".claude/instructions.md"


def _validate_injection_channels(
    *,
    repo_root: Path,
    session_id: str,
) -> Tuple[int, int]:
    """Wire the (previously inert) injection validators into SessionStart.

    PLAN-136 W3 S2. Two channels, both BLOCKING + fail-OPEN:

    * **G1** — the single trusted MOIM file ``.claude/instructions.md`` at the
      project root. ``validate_trusted_file`` returns a ``Verdict``; on
      ``decision == "block"`` we emit ``persistent_instructions_blocked`` and the
      file is NOT loaded (this function never loads it — the refusal is the
      contract; a separate loader would consume the ``allow`` verdicts).
    * **G3** — every nested ``.claude/hints.md`` repo-root-and-below.
      ``validate_hierarchical_hints`` returns ``(loaded, blocked)``; we emit one
      ``hint_provenance_recorded`` per discovered entry (loaded AND blocked) so
      the provenance ledger sees the full discovery, never the body or the path.

    Fail-OPEN contract (ADR-005): ANY exception in this block is swallowed — a
    bug in the validator/emitter MUST NOT break SessionStart. Each emit is
    additionally guarded so a single bad entry can't abort the rest. Mirrors the
    fail-soft ordering of ``_emit_session_start``.

    Returns ``(instructions_blocked, hints_blocked)`` integer counts for an
    informational ``systemMessage`` only — never used to block the session.
    """
    instructions_blocked = 0
    hints_blocked = 0
    try:
        from _lib import guardrail_validator as _gv  # type: ignore
        from _lib import audit_emit as _ae  # type: ignore
    except Exception:
        return (0, 0)

    project_dir = str(repo_root)

    # --- G1: trusted MOIM file -------------------------------------------
    try:
        verdict = _gv.validate_trusted_file(
            _TRUSTED_INSTRUCTIONS_REL, project_dir=project_dir
        )
        if getattr(verdict, "decision", "allow") == "block":
            instructions_blocked = 1
            try:
                _ae.emit_persistent_instructions_blocked(
                    reason=str(getattr(verdict, "reason", "other")),
                    family_hits=int(getattr(verdict, "family_hits", 0)),
                    bytes_scanned=int(getattr(verdict, "bytes_scanned", 0)),
                    session_id=session_id,
                    project=project_dir,
                )
            except Exception:
                pass
    except Exception:
        pass

    # --- G3: hierarchical per-directory hints ----------------------------
    try:
        loaded, blocked = _gv.validate_hierarchical_hints(project_dir)
        for entry in list(loaded) + list(blocked):
            try:
                _ae.emit_hint_provenance_recorded(
                    reason=str(getattr(entry, "reason", "other")),
                    rel_dir_depth=int(getattr(entry, "rel_dir_depth", 0)),
                    family_hits=int(getattr(entry, "family_hits", 0)),
                    bytes_scanned=int(getattr(entry, "bytes_scanned", 0)),
                    session_id=session_id,
                    project=project_dir,
                )
            except Exception:
                continue
        hints_blocked = len(list(blocked))
    except Exception:
        pass

    return (instructions_blocked, hints_blocked)


def _emit_session_start(
    *,
    session_id: str,
    governance_state: str,
    gate_1_hashes: Dict[str, Optional[str]],
    warmup_bytes: int,
    repo_root: Path,
) -> None:
    """Best-effort audit event. Never raises."""
    try:
        from _lib import audit_emit  # type: ignore
        # Use emit_generic if available (ADR-055 v2.9), else emit a minimal
        # line via audit_emit internal API. Fall through silently on error.
        emitter = getattr(audit_emit, "emit_generic", None)
        if emitter is not None:
            emitter(
                action="session_start",
                session_id=session_id,
                hook_version=_HOOK_VERSION,
                governance_state=governance_state,
                gate_1_hashes=gate_1_hashes,
                warmup_bytes=warmup_bytes,
                project=str(repo_root),
            )
    except Exception:
        return


def decide(*, repo_root: Path, session_id: str) -> str:
    """Pure decision function — returns JSON for stdout.

    Returns `allow` unconditionally (SessionStart never blocks).
    Side effects: audit emit + cache warmup.
    """
    if _kill_switch_active():
        return _emit_observe(system_message="SessionStart: kill-switch active, no-op")

    try:
        gate_1_hashes = _gate_1_hash(repo_root)
        warmup_bytes = _warmup_gate_1(repo_root)
        missing = [k for k, v in gate_1_hashes.items() if v is None]
        governance_state = "degraded" if missing else "healthy"
        _emit_session_start(
            session_id=session_id,
            governance_state=governance_state,
            gate_1_hashes=gate_1_hashes,
            warmup_bytes=warmup_bytes,
            repo_root=repo_root,
        )
        # PLAN-136 W3 S2 — wire the (previously inert) injection validators.
        # Self-contained fail-OPEN: never raises (see helper docstring); the
        # outer try/except below is belt-and-suspenders per ADR-005.
        instructions_blocked, hints_blocked = _validate_injection_channels(
            repo_root=repo_root, session_id=session_id
        )
        guard_note = ""
        if instructions_blocked or hints_blocked:
            guard_note = (
                f" [injection-guard: blocked {instructions_blocked} "
                f"instruction-file + {hints_blocked} hint(s)]"
            )
        # PLAN-155 Wave 3b (SENT-CX-E) — Codex kill-switch surface boot
        # re-hash. No-op unless the Codex harness is installed; RED (stderr
        # breadcrumb + systemMessage note) when a tracked surface file is
        # missing or mutated vs the recorded baseline. Never blocks the boot.
        ks_status, ks_note, ks_red = _check_killswitch_surface(repo_root)
        ks_suffix = f" [{ks_note}]" if ks_note else ""
        if ks_red:
            # The RED breadcrumb (debate A2 / A8): silence from a fail-open
            # rail is not health — surface the tamper to the audit-log
            # dashboard AND the session banner, without breaking the boot.
            sys.stderr.write(
                f"[SessionStart] KILLSWITCH-TRIPWIRE-RED: {ks_note}\n"
            )
        if missing:
            return _emit_observe(
                system_message=(
                    f"SessionStart: governance degraded — missing "
                    f"{len(missing)} Gate-1 file(s): {missing[:3]}"
                    f"{guard_note}{ks_suffix}"
                )
            )
        return _emit_observe(
            system_message=(
                f"SessionStart: healthy ({len(gate_1_hashes)} Gate-1 files "
                f"warm, {warmup_bytes} bytes){guard_note}{ks_suffix}"
            )
        )
    except Exception as e:
        # Fail-open per ADR-005
        sys.stderr.write(
            f"[SessionStart] FATAL: {type(e).__name__}: {e}\n"
        )
        return _emit_observe()


def _maybe_emit_first_run_wizard(repo_root: Path) -> None:
    """PLAN-093 Wave C.1 — emit first_run_wizard_dispatched once per project.

    Detection: absence of `~/.claude/projects/<project>/state/onboarded.flag`.
    Fail-soft: never raises (audit-log absence / OSError swallowed).
    """
    try:
        flag = Path.home() / ".claude" / "projects" / repo_root.name / "state" / "onboarded.flag"
    except Exception:
        return
    if flag.exists():
        return
    try:
        flag.parent.mkdir(parents=True, exist_ok=True)
        flag.touch()
    except OSError:
        return
    try:
        from _lib import audit_emit as _ae  # type: ignore
        if hasattr(_ae, "emit_generic"):
            _ae.emit_generic("first_run_wizard_dispatched", project=repo_root.name)
    except Exception:
        pass


def main() -> int:
    """Hook entry point. Emits schema-compliant lifecycle JSON output.

    Reads SessionStart payload via Adapter Layer (ADR-014) to extract
    the session-id breadcrumb. SessionStart is registered as a
    matcher-free hook in .claude/settings.json § hooks.SessionStart.
    Output shape: `{"continue": true, "systemMessage": "..."}` — no
    `decision` field (lifecycle schema does NOT accept "allow").
    """
    try:
        from _lib.adapters import claude as _claude_adapter  # noqa: E402
    except Exception:
        sys.stdout.write(_emit_observe() + "\n")
        return 0

    try:
        event = _claude_adapter.read_event(phase="SessionStart")
    except Exception:
        sys.stdout.write(_emit_observe() + "\n")
        return 0

    session_id = (
        os.environ.get("CLAUDE_SESSION_ID", "")
        or getattr(event, "session_id", "") or ""
    )
    if not session_id:
        session_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")

    repo_root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())

    _maybe_emit_first_run_wizard(repo_root)  # PLAN-093 Wave C.1

    try:
        out = decide(repo_root=repo_root, session_id=session_id)
    except Exception as e:
        sys.stderr.write(f"[SessionStart] FATAL: {type(e).__name__}: {e}\n")
        sys.stdout.write(_emit_observe() + "\n")
        return 0

    sys.stdout.write(out + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
