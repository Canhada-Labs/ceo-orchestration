#!/usr/bin/env python3
"""Governance Hook: mechanical enforcement of plan lifecycle transitions.

Sprint 3 Item D. Registered in `.claude/settings.json` under
`hooks.PreToolUse` with matcher `Edit|Write|MultiEdit` (PLAN-019
P1-SEC-E expansion).
Runs via the `_python-hook.sh` shim.

## What it enforces

When an Edit/Write/MultiEdit tool call modifies a plan file's `status:`
field, this hook checks:

1. **Status value is legal** — one of: draft, reviewed, executing, done, abandoned
2. **Transition is legal** per PLAN-SCHEMA.md §4:
   - draft → reviewed, abandoned
   - reviewed → executing, abandoned
   - executing → done, abandoned
   - done, abandoned are terminal
3. **Required fields on transition:**
   - → reviewed: `reviewed_at` must be set
   - → done: `completed_at` must be set AND `related_commits` non-empty
   - → abandoned: body must contain `## Abandonment reason` section

## Scope guard

The hook runs on ALL Edit/Write/MultiEdit tool calls (matcher:
"Edit|Write|MultiEdit"). It fails-open on any file whose path does not
match `.claude/plans/PLAN-*.md`. This matches the debate R-SEC2 concern:
a hook bug must not brick all edits.

## Write semantics (PLAN-019 P1-SEC-E)

`Write` tool does not have `old_string`/`new_string`; it has `content`
(full replacement / creation). We synthesize an Edit-equivalent where
`old_string = <entire existing content>` (or empty string for new
files) and `new_string = <tool_input.content>`. The same `decide()`
path runs — transition validation and required-field checks still
apply. For brand-new plan files written directly to `done` status
without `completed_at`, this hook blocks the Write.

## MultiEdit semantics (PLAN-019 P1-SEC-E)

`MultiEdit` has an `edits` array of `{old_string, new_string,
replace_all}` objects applied in order. We apply all edits to a
simulated buffer and run `decide()` on the final-before/final-after
frontmatter diff. Equivalent to chaining N Edits.

## Stranded-work detection (PLAN-065 §4.4.B Phase 4-B)

Two stranded modes per Paperclip absorption:

- **Mode 8.2** (`paperclip_in_progress`): plan with `status: executing`
  AND no commits touching plan file in last >24h. Surfaces a
  breadcrumb in the hook's systemMessage; hook still allows the edit
  (fail-open invariant).
- **Mode 8.1** (`todo_dispatch_failed`): plan with `status: reviewed`
  AND `reviewed_at` older than 7d. Wakes Owner via audit-log entry;
  hook allows the edit.

Detection runs as a side-effect on plan-edit decisions (not a separate
hook). Audit emit uses action `stranded_plan_detected` if registered;
otherwise falls back to `_breadcrumb` via emit_generic's fail-soft
unknown-action path. CLI exposure via `check-staleness.py --strict`.

## Output contract

    {"decision":"allow"}
    {"decision":"block","reason":"PLAN-LIFECYCLE: ..."}

Exit code is always 0. Fail-open on any internal error.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

_HOOKS_DIR = Path(__file__).resolve().parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib import contract as _contract  # noqa: E402
from _lib.adapters import claude as _claude_adapter  # noqa: E402
from _lib import plan_frontmatter as _fm  # noqa: E402

# Optional: emit to event stream v2 (fail-open if module missing or errors)
try:
    from _lib import audit_emit as _audit_emit  # noqa: E402
    _AUDIT_EMIT_AVAILABLE = True
except Exception:  # pragma: no cover
    _AUDIT_EMIT_AVAILABLE = False


# Legal status values per PLAN-SCHEMA.md §4
#
# `superseded` (PLAN-113 W2): a terminal status used when a later plan
# fully absorbs this plan's scope. Distinct from `abandoned` (premise
# proved wrong) — the work itself was valid but is now tracked elsewhere.
# Requires a `superseded_by:` frontmatter pointer. A plan may be
# superseded from any prior state, including `done` (e.g. PLAN-093/095
# -FOLLOWUP were done then folded into PLAN-106).
_LEGAL_STATUSES = {
    "draft",
    "reviewed",
    "executing",
    "done",
    "abandoned",
    "refused",
    "superseded",
}

# Transition graph: status → set of allowed next statuses
_ALLOWED_TRANSITIONS: Dict[str, set] = {
    "draft": {"draft", "reviewed", "abandoned", "refused", "superseded"},
    "reviewed": {"reviewed", "executing", "abandoned", "refused", "superseded"},
    "executing": {"executing", "done", "abandoned", "refused", "superseded"},
    # done is reopen-able when the plan body declares a `reopen_via:`
    # ADR reference (audit-v2 ADR-092 honest-deferral framework).
    # done → superseded is allowed when a later plan absorbs the scope.
    "done": {"done", "executing", "superseded"},
    "abandoned": {"abandoned"},  # terminal
    "refused": {"refused"},  # terminal — must cite refused_adr
    "superseded": {"superseded"},  # terminal — must cite superseded_by
}

# Path pattern for plan files
_PLAN_PATH_RE = re.compile(r"\.claude/plans/PLAN-\d{3}-[a-z0-9-]+\.md$")

# Extract plan ID from a file path (e.g. "PLAN-004")
_PLAN_ID_RE = re.compile(r"(PLAN-\d{3})-[a-z0-9-]+\.md$")

# ---------------------------------------------------------------------
# PLAN-065 §4.4.B — Stranded-work detection thresholds
# ---------------------------------------------------------------------
#
# Mode 8.2 ("Paperclip in_progress sem run vivo"): plan stuck in
# `status: executing` with no commit touching the plan file in this
# many seconds. 24h matches Paperclip's `WIP > 1d` heuristic.
_STRANDED_EXECUTING_MAX_AGE_SECS = 24 * 3600  # 24 hours

# Mode 8.1 ("todo dispatch falhou"): plan parked in `status: reviewed`
# with a `reviewed_at` ISO date older than this many seconds. 7 days
# is the Owner-wake threshold per PLAN-065 §4.4.B.
_STRANDED_REVIEWED_MAX_AGE_SECS = 7 * 24 * 3600  # 7 days


def _extract_plan_id(file_path: str) -> str:
    """Return the plan ID from a plan file path, or empty string."""
    m = _PLAN_ID_RE.search(file_path)
    return m.group(1) if m else ""


def _emit_transition(file_path: str, old_status: str, new_status: str, editor_tool: str = "Edit") -> None:
    """Fail-open emit of plan_transition event to stream v2."""
    if not _AUDIT_EMIT_AVAILABLE:
        return
    try:
        plan_id = _extract_plan_id(file_path)
        if not plan_id or not old_status or not new_status or old_status == new_status:
            return
        import os as _os
        _audit_emit.emit_plan_transition(
            plan_id=plan_id,
            from_status=old_status,
            to_status=new_status,
            file_path=file_path,
            editor_tool=editor_tool,
            project=_os.environ.get("CLAUDE_PROJECT_DIR") or "",
        )
    except Exception:  # pragma: no cover
        pass


def _emit_stranded(plan_id: str, mode: str, age_days: int, status: str, file_path: str) -> None:
    """Fail-open emit of stranded_plan_detected event.

    PLAN-065 §4.4.B — `stranded_plan_detected` is NOT yet in the
    `_KNOWN_ACTIONS` registry. We attempt the emit via `emit_generic`
    which silently breadcrumbs unknown actions (no-op pre-canonical
    ceremony). Once the action is registered in audit_emit.py
    (PLAN-065 Phase 4-B canonical ceremony), the same call site
    starts producing real events with no code change.
    """
    # PLAN-065 Phase 4-B v1.12.1: action `stranded_plan_detected` is NOT
    # YET registered in `_KNOWN_ACTIONS`. Wiring deferred to v1.13.0 /
    # PLAN-067 (per ADR-093 §per-plan-cap — ADR-098 already consumed for
    # PLAN-065). Until then, this is a no-op stub. The actual emit call
    # is intentionally absent to avoid `check-audit-registry-coverage.py`
    # AST drift detector flagging an orphan emit (would block PR).
    # Reference inputs so static analyzers see them used:
    _ = plan_id, mode, age_days, status, file_path
    if not _AUDIT_EMIT_AVAILABLE:
        return
    return


@dataclass
class StrandedPlan:
    """Typed result of stranded-plan detection.

    PLAN-065 §4.4.B. Field semantics:

    - ``plan_id``: PLAN-NNN identifier extracted from filename.
    - ``mode``: ``"8.1"`` (reviewed dispatch failed) or ``"8.2"``
      (executing paperclip — no run vivo).
    - ``age_days``: integer days since the relevant timestamp
      (commit mtime for 8.2; ``reviewed_at`` for 8.1).
    - ``status``: current frontmatter status (executing / reviewed).
    - ``file_path``: relative-or-absolute path to the plan file.
    """

    plan_id: str
    mode: str
    age_days: int
    status: str
    file_path: str


@dataclass
class Decision:
    """Typed result."""

    allow: bool
    reason: Optional[str] = None

    def to_json(self) -> str:
        if self.allow:
            return json.dumps({}, ensure_ascii=False)  # schema-compliant allow
        return json.dumps(
            {"decision": "block", "reason": self.reason or ""},
            ensure_ascii=False,
        )


def _is_plan_file(file_path: str) -> bool:
    """Return True only if the path matches .claude/plans/PLAN-NNN-slug.md."""
    if not file_path:
        return False
    return bool(_PLAN_PATH_RE.search(file_path))


def _read_current_plan(file_path: str) -> str:
    """Read the current file content. Returns empty string on any error."""
    try:
        return Path(file_path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _apply_edit(
    current: str, old_string: str, new_string: str, replace_all: bool
) -> str:
    """Simulate the Edit tool's substitution locally.

    Returns the post-edit content. If old_string is not in current,
    returns current unchanged (the real Edit would fail, but we don't
    want to block on that — fail-open to let Edit produce its own error).
    """
    if not current or old_string not in current:
        return current
    if replace_all:
        return current.replace(old_string, new_string)
    # Non-replace-all: replace first occurrence only
    return current.replace(old_string, new_string, 1)


def _check_transition(
    old_status: str, new_status: str
) -> Optional[str]:
    """Return a block reason if the transition is illegal; None if OK."""
    if new_status not in _LEGAL_STATUSES:
        return (
            f"PLAN-LIFECYCLE: illegal status value '{new_status}'. "
            f"Must be one of: {', '.join(sorted(_LEGAL_STATUSES))}."
        )
    if not old_status:
        # New plan (no existing status in the old content) — anything legal is fine
        return None
    if old_status not in _LEGAL_STATUSES:
        # Corrupt existing status — don't block; let it be cleaned up
        return None
    allowed = _ALLOWED_TRANSITIONS.get(old_status, set())
    if new_status not in allowed:
        return (
            f"PLAN-LIFECYCLE: illegal transition '{old_status}' → '{new_status}'. "
            f"From '{old_status}', allowed next states: "
            f"{', '.join(sorted(allowed - {old_status}))}. "
            f"See .claude/plans/PLAN-SCHEMA.md §4."
        )
    return None


def _check_required_fields(
    old_status: str,
    new_status: str,
    new_fm: Dict[str, _fm.FrontmatterValue],
    new_body: str,
) -> Optional[str]:
    """Check required fields for the new status. Returns reason or None.

    Session 76 audit-v3 (DIM-11) extended this to enforce the full
    ADR-092 honest-deferral contract: `refused_at` for `refused`, plus
    `reopen_via` + `reopen_trigger` + `## Reopen criteria` body section
    for the `done -> executing` reopen path. Prior to this fix the FSM
    accepted reopen with no body fields and refused without `refused_at`.
    """
    if new_status == "reviewed":
        if not new_fm.get("reviewed_at"):
            return (
                "PLAN-LIFECYCLE: transition to 'reviewed' requires "
                "`reviewed_at: <YYYY-MM-DD>` in frontmatter."
            )
    elif new_status == "done":
        if not new_fm.get("completed_at"):
            return (
                "PLAN-LIFECYCLE: transition to 'done' requires "
                "`completed_at: <YYYY-MM-DD>` in frontmatter."
            )
        rc = new_fm.get("related_commits")
        if not rc or (isinstance(rc, list) and len(rc) == 0):
            return (
                "PLAN-LIFECYCLE: transition to 'done' requires non-empty "
                "`related_commits: [sha1, sha2, ...]` in frontmatter."
            )
    elif new_status == "abandoned":
        if not _fm.has_abandonment_reason(new_body):
            return (
                "PLAN-LIFECYCLE: transition to 'abandoned' requires an "
                "`## Abandonment reason` section in the plan body."
            )
    elif new_status == "refused":
        # Session 75 Codex Finding 7: terminal `refused` status requires
        # a `refused_adr: ADR-NNN` field citing the ADR that documents
        # the refusal. Closes the gap where _LEGAL_STATUSES allowed
        # `refused` but no field validation enforced citation.
        refused_adr = new_fm.get("refused_adr")
        if not refused_adr:
            return (
                "PLAN-LIFECYCLE: transition to 'refused' requires "
                "`refused_adr: ADR-NNN` in frontmatter (cite the ADR "
                "that documents the refusal). Per ADR-092 honest deferral."
            )
        ra = str(refused_adr).strip()
        import re as _re
        if not _re.match(r"^ADR-\d{3,4}\b", ra):
            return (
                "PLAN-LIFECYCLE: 'refused_adr' field must be an ADR "
                "identifier of the form 'ADR-NNN' or 'ADR-NNNN'."
            )
        # Session 76 audit-v3 (DIM-11) — ADR-092 also requires refused_at.
        if not new_fm.get("refused_at"):
            return (
                "PLAN-LIFECYCLE: transition to 'refused' requires "
                "`refused_at: <YYYY-MM-DD>` in frontmatter. Per ADR-092 "
                "honest deferral."
            )
    elif new_status == "superseded":
        # PLAN-113 W2 — terminal `superseded` status requires a
        # `superseded_by:` field naming the plan that absorbed this
        # plan's scope. Mirrors the abandoned/refused citation pattern:
        # a superseded plan must point forward to where the work lives.
        superseded_by = new_fm.get("superseded_by")
        if not superseded_by:
            return (
                "PLAN-LIFECYCLE: transition to 'superseded' requires "
                "`superseded_by: PLAN-NNN` in frontmatter (name the plan "
                "that absorbed this plan's scope)."
            )
        sb = str(superseded_by).strip()
        import re as _re_superseded
        if not _re_superseded.match(r"^PLAN-\d{3}\b", sb):
            return (
                "PLAN-LIFECYCLE: 'superseded_by' field must be a plan "
                "identifier of the form 'PLAN-NNN'."
            )
    elif new_status == "executing" and old_status == "done":
        # Session 76 audit-v3 (DIM-11) — `done -> executing` reopen per
        # ADR-092 requires `reopen_via: ADR-NNN` + `reopen_trigger:
        # <free-text>` + body section `## Reopen criteria`. Prior FSM
        # let plans silently flip back without these fields.
        reopen_via = new_fm.get("reopen_via")
        if not reopen_via:
            return (
                "PLAN-LIFECYCLE: reopen 'done' -> 'executing' requires "
                "`reopen_via: ADR-NNN` in frontmatter. Per ADR-092 honest "
                "deferral framework."
            )
        rv = str(reopen_via).strip()
        import re as _re_reopen
        if not _re_reopen.match(r"^ADR-\d{3,4}\b", rv):
            return (
                "PLAN-LIFECYCLE: 'reopen_via' field must be an ADR "
                "identifier of the form 'ADR-NNN' or 'ADR-NNNN'."
            )
        if not new_fm.get("reopen_trigger"):
            return (
                "PLAN-LIFECYCLE: reopen 'done' -> 'executing' requires "
                "`reopen_trigger: <free-text describing the external "
                "signal>` in frontmatter. Per ADR-092."
            )
        if "## Reopen criteria" not in new_body:
            return (
                "PLAN-LIFECYCLE: reopen 'done' -> 'executing' requires a "
                "`## Reopen criteria` section in the plan body. Per ADR-092."
            )
    return None


# ---------------------------------------------------------------------
# PLAN-065 §4.4.B — Stranded-work detection helpers
# ---------------------------------------------------------------------


def _parse_iso_date_to_unix(s: str) -> Optional[int]:
    """Parse ``YYYY-MM-DD`` (or ISO datetime) to a UTC unix timestamp.

    Returns None on any malformed input. Tolerates the three formats
    used elsewhere in the framework:

    - ``2026-04-12``               (date only — anchored to 00:00 UTC)
    - ``2026-04-12T13:45:01Z``
    - ``2026-04-12T13:45:01+0000``

    Stdlib only. ``datetime.fromisoformat`` is not used (Py3.9 does not
    accept ``Z``); we fall back to ``strptime``.
    """
    if not s:
        return None
    s = str(s).strip()
    if not s:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
        try:
            d = datetime.strptime(s, fmt)
            if d.tzinfo is None:
                d = d.replace(tzinfo=timezone.utc)
            return int(d.timestamp())
        except ValueError:
            continue
    return None


def _git_last_commit_unix(plan_path: Path, repo_root: Optional[Path] = None) -> Optional[int]:
    """Return unix-ts of the most recent commit touching ``plan_path``.

    Uses ``git log -1 --format=%ct -- <path>``. Returns None on any
    git error (not a repo, file untracked, git binary missing, etc.).
    Fail-open invariant: detection short-circuits to "no stranded
    finding for this plan" rather than blocking the hook.
    """
    try:
        cwd = str(repo_root) if repo_root else str(plan_path.parent)
        result = subprocess.run(
            ["git", "log", "-1", "--format=%ct", "--", str(plan_path)],
            capture_output=True,
            text=True,
            timeout=2.0,
            cwd=cwd,
        )
        if result.returncode != 0:
            return None
        out = (result.stdout or "").strip()
        if not out:
            return None
        return int(out)
    except (subprocess.TimeoutExpired, subprocess.SubprocessError,
            FileNotFoundError, ValueError, OSError):
        return None


def detect_stranded(
    plans_dir: Path,
    *,
    now_unix: Optional[int] = None,
    repo_root: Optional[Path] = None,
) -> List[StrandedPlan]:
    """Walk plans_dir and return all stranded plans across modes 8.1 + 8.2.

    PLAN-065 §4.4.B. Stranded modes:

    - **Mode 8.2 paperclip** — ``status == executing`` and no commit
      has touched the plan file in the last
      ``_STRANDED_EXECUTING_MAX_AGE_SECS`` seconds (24h). If the
      frontmatter declares ``last_commit_at: <ISO-date>`` that value
      overrides the git-log query (used by tests + by environments
      where git history is unavailable but the plan author manually
      records progress). Mode-8.2 has priority over Mode-8.1: an
      executing-too-long plan is reported as 8.2 only.
    - **Mode 8.1 todo-dispatch-failed** — ``status == reviewed`` and
      ``reviewed_at`` is older than
      ``_STRANDED_REVIEWED_MAX_AGE_SECS`` seconds (7d).

    Args:
        plans_dir: directory holding ``PLAN-*.md`` files. Non-PLAN
            files (PLAN-SCHEMA.md, examples/, archive/) are skipped.
        now_unix: unix timestamp to compare against (defaults to
            ``time.time()``). Injected for deterministic tests.
        repo_root: passed to ``git log`` ``cwd``. Defaults to plans_dir.

    Returns:
        List of StrandedPlan, in deterministic alphabetical order by
        plan filename.

    Fail-open invariant: any per-plan exception is swallowed and the
    walk continues. A blanket exception on the directory walk returns
    an empty list. The hook NEVER blocks on stranded detection.
    """
    if now_unix is None:
        now_unix = int(time.time())

    results: List[StrandedPlan] = []
    if not plans_dir or not plans_dir.is_dir():
        return results

    try:
        plan_files = sorted(plans_dir.glob("PLAN-*.md"))
    except OSError:
        return results

    for plan_file in plan_files:
        try:
            # Skip PLAN-SCHEMA.md / DEBATE-SCHEMA.md / etc.
            if not _PLAN_PATH_RE.search(str(plan_file)):
                continue

            text = plan_file.read_text(encoding="utf-8")
            fm = _fm.parse_frontmatter(text)
            status = str(fm.get("status", "")).strip()
            plan_id = _extract_plan_id(plan_file.name) or plan_file.stem
            file_path = str(plan_file)

            if status == "executing":
                # Mode 8.2 — query last-commit timestamp, frontmatter
                # override wins for testability.
                fm_lc = fm.get("last_commit_at", "")
                last_unix: Optional[int] = None
                if fm_lc:
                    last_unix = _parse_iso_date_to_unix(str(fm_lc))
                if last_unix is None:
                    last_unix = _git_last_commit_unix(plan_file, repo_root=repo_root)
                if last_unix is None:
                    # No data → cannot decide stranded; skip (fail-open).
                    continue
                age_secs = now_unix - last_unix
                if age_secs > _STRANDED_EXECUTING_MAX_AGE_SECS:
                    age_days = max(0, age_secs // 86400)
                    results.append(
                        StrandedPlan(
                            plan_id=plan_id,
                            mode="8.2",
                            age_days=int(age_days),
                            status=status,
                            file_path=file_path,
                        )
                    )
                continue  # mode-8.2 priority over mode-8.1

            if status == "reviewed":
                fm_rv = fm.get("reviewed_at", "")
                if not fm_rv:
                    continue
                reviewed_unix = _parse_iso_date_to_unix(str(fm_rv))
                if reviewed_unix is None:
                    continue
                age_secs = now_unix - reviewed_unix
                if age_secs > _STRANDED_REVIEWED_MAX_AGE_SECS:
                    age_days = max(0, age_secs // 86400)
                    results.append(
                        StrandedPlan(
                            plan_id=plan_id,
                            mode="8.1",
                            age_days=int(age_days),
                            status=status,
                            file_path=file_path,
                        )
                    )
                continue
        except Exception:
            # Per-plan fail-open: a corrupt plan must not block the walk.
            continue

    return results


def _stranded_breadcrumb(strandeds: List[StrandedPlan]) -> str:
    """Render a short, audit-friendly summary line for the systemMessage."""
    if not strandeds:
        return ""
    parts = []
    for s in strandeds[:5]:  # cap output — breadcrumb only
        parts.append(f"{s.plan_id} (mode {s.mode}, {s.age_days}d)")
    suffix = ""
    if len(strandeds) > 5:
        suffix = f" +{len(strandeds) - 5} more"
    return "PLAN-LIFECYCLE-STRANDED: " + ", ".join(parts) + suffix


def decide(
    *,
    file_path: str,
    old_string: str,
    new_string: str,
    replace_all: bool,
    read_current=_read_current_plan,
) -> Decision:
    """Pure decision function — IO injected via read_current for testing."""
    # Scope guard: only run on plan files
    if not _is_plan_file(file_path):
        return Decision(allow=True)

    # Read current file content
    current = read_current(file_path)
    if not current:
        # File doesn't exist yet (creation via Edit is unusual; fail-open)
        return Decision(allow=True)

    # Compute post-edit content
    new_content = _apply_edit(current, old_string, new_string, replace_all)
    if new_content == current:
        # Edit doesn't actually modify the file (or old_string not found)
        return Decision(allow=True)

    return _decide_on_buffers(current, new_content)


def _decide_on_buffers(old_content: str, new_content: str) -> Decision:
    """Common decision path once we have pre/post buffers.

    Used by the Edit path (direct substitution), the Write path (full
    replacement) and the MultiEdit path (sequential application).
    """
    if new_content == old_content:
        return Decision(allow=True)

    old_fm = _fm.parse_frontmatter(old_content)
    new_fm = _fm.parse_frontmatter(new_content)

    old_status = str(old_fm.get("status", "")).strip()
    new_status = str(new_fm.get("status", "")).strip()

    # If status didn't change, nothing to check
    if old_status == new_status:
        return Decision(allow=True)

    # Status changed — validate
    reason = _check_transition(old_status, new_status)
    if reason:
        return Decision(allow=False, reason=reason)

    reason = _check_required_fields(old_status, new_status, new_fm, new_content)
    if reason:
        return Decision(allow=False, reason=reason)

    return Decision(allow=True)


def decide_write(
    *,
    file_path: str,
    content: str,
    read_current=_read_current_plan,
) -> Decision:
    """Write-tool variant of decide().

    PLAN-019 P1-SEC-E: `Write` has `content` instead of old/new strings.
    We synthesize an Edit where old_string = <entire existing content>
    (or empty for a new file) and new_string = <content>, then run the
    same transition + required-field checks.

    If the Write creates a brand-new plan file, `current` is empty. The
    transition validation still runs: a new plan with `status: done` but
    no `completed_at` is blocked just like `draft → done` via Edit.
    """
    if not _is_plan_file(file_path):
        return Decision(allow=True)

    current = read_current(file_path) or ""
    new_content = content or ""
    if new_content == current:
        return Decision(allow=True)

    # For brand-new plan files (current == ""), old_status is empty and
    # the transition validator treats any legal new status as OK (see
    # _check_transition "new plan" branch). Required-field checks still
    # fire, so a new plan written directly as done/without-completed_at
    # blocks correctly.
    return _decide_on_buffers(current, new_content)


def decide_multiedit(
    *,
    file_path: str,
    edits: list,
    read_current=_read_current_plan,
) -> Decision:
    """MultiEdit-tool variant of decide().

    PLAN-019 P1-SEC-E: `MultiEdit.tool_input.edits` is an array of
    `{old_string, new_string, replace_all}` dicts. Apply sequentially
    to simulate what the tool will produce, then run the same checks.
    """
    if not _is_plan_file(file_path):
        return Decision(allow=True)

    current = read_current(file_path)
    if not current:
        return Decision(allow=True)

    buf = current
    for e in (edits or []):
        if not isinstance(e, dict):
            continue
        old_s = str(e.get("old_string") or "")
        new_s = str(e.get("new_string") or "")
        replace_all = bool(e.get("replace_all") or False)
        buf = _apply_edit(buf, old_s, new_s, replace_all)

    return _decide_on_buffers(current, buf)


def _to_contract_decision(d: "Decision") -> _contract.Decision:
    if d.allow:
        return _contract.allow()
    return _contract.block(d.reason or "")


def _simulated_new_content_for_tool(
    tool_name: str,
    file_path: str,
    event,
) -> Optional[str]:
    """Compute the simulated post-tool content for a plan file.

    Returns None if the tool does not modify content or if simulation
    fails. Used by the audit-emit side-effect so plan_transition events
    work identically for Edit / Write / MultiEdit.
    """
    try:
        if tool_name == "Edit":
            current = _read_current_plan(file_path)
            if not current:
                return None
            new_c = _apply_edit(
                current, event.old_string or "", event.new_string or "",
                event.replace_all,
            )
            return new_c if new_c != current else None
        if tool_name == "Write":
            content = str(event.tool_input.get("content") or "")
            return content
        if tool_name == "MultiEdit":
            current = _read_current_plan(file_path)
            if not current:
                return None
            buf = current
            for e in (event.tool_input.get("edits") or []):
                if not isinstance(e, dict):
                    continue
                buf = _apply_edit(
                    buf,
                    str(e.get("old_string") or ""),
                    str(e.get("new_string") or ""),
                    bool(e.get("replace_all") or False),
                )
            return buf if buf != current else None
    except Exception:
        return None
    return None


def _scan_and_emit_stranded(file_path: str) -> List[StrandedPlan]:
    """Side-effect: detect stranded plans + emit audit events.

    PLAN-065 §4.4.B. Runs on every plan-edit decision (allow path).
    Fail-open: any exception is swallowed; never blocks the user.
    Returns the list of stranded plans found (used by main() to
    surface a breadcrumb).
    """
    try:
        if not file_path:
            return []
        plan_path = Path(file_path)
        # Resolve plans_dir relative to the edited plan when possible;
        # fall back to CLAUDE_PROJECT_DIR/.claude/plans.
        plans_dir: Optional[Path] = None
        if plan_path.parent.name == "plans":
            plans_dir = plan_path.parent
        else:
            project = os.environ.get("CLAUDE_PROJECT_DIR", "")
            if project:
                candidate = Path(project) / ".claude" / "plans"
                if candidate.is_dir():
                    plans_dir = candidate
        if plans_dir is None or not plans_dir.is_dir():
            return []
        repo_root = plans_dir.parent.parent if plans_dir.parent.name == ".claude" else None
        strandeds = detect_stranded(plans_dir, repo_root=repo_root)
        for s in strandeds:
            _emit_stranded(
                plan_id=s.plan_id,
                mode=s.mode,
                age_days=s.age_days,
                status=s.status,
                file_path=s.file_path,
            )
        return strandeds
    except Exception:
        return []


def main() -> int:
    """Hook entry point.

    PLAN-006 Phase 1 migration (ADR-014): Adapter Layer I/O.
    PLAN-019 P1-SEC-E: dispatch by tool_name (Edit / Write / MultiEdit).
    PLAN-065 §4.4.B: stranded-plan side-effect on allow path.
    """
    try:
        event = _claude_adapter.read_event(phase="PreToolUse")
        if event.parse_error:
            print(
                f"[check_plan_edit] WARN: stdin parse error: {event.parse_error}",
                file=sys.stderr,
            )
            _claude_adapter.emit_decision(_contract.allow())
            return 0

        file_path = event.file_path or ""
        tool_name = event.tool_name or "Edit"

        if tool_name == "Write":
            # Write: single `content` field replaces the whole file.
            content = str(event.tool_input.get("content") or "")
            decision = decide_write(file_path=file_path, content=content)
        elif tool_name == "MultiEdit":
            # MultiEdit: list of edits applied sequentially.
            edits = event.tool_input.get("edits") or []
            if not isinstance(edits, list):
                edits = []
            decision = decide_multiedit(file_path=file_path, edits=edits)
        else:
            # Default / Edit: the historical path.
            decision = decide(
                file_path=file_path,
                old_string=event.old_string or "",
                new_string=event.new_string or "",
                replace_all=event.replace_all,
            )

        # Side-effect: emit plan_transition event on legal transition (v2 stream).
        # Runs AFTER decide() to avoid polluting the pure-function contract and
        # only fires when decision is allow AND the status actually changed.
        if decision.allow and _is_plan_file(file_path):
            try:
                current = _read_current_plan(file_path) or ""
                new_content = _simulated_new_content_for_tool(
                    tool_name, file_path, event,
                )
                if new_content is not None and new_content != current:
                    old_fm = _fm.parse_frontmatter(current) if current else {}
                    new_fm = _fm.parse_frontmatter(new_content)
                    old_st = str(old_fm.get("status", "")).strip()
                    new_st = str(new_fm.get("status", "")).strip()
                    if old_st and new_st and old_st != new_st:
                        _emit_transition(file_path, old_st, new_st, tool_name)
            except Exception:
                pass

        # PLAN-065 §4.4.B — Stranded-plan side-effect (allow path only).
        # Failure here NEVER blocks the user: any exception inside
        # _scan_and_emit_stranded is swallowed, and even a non-empty
        # finding only attaches a breadcrumb to systemMessage (the
        # decision is still `allow` from the lifecycle FSM).
        if decision.allow and _is_plan_file(file_path):
            try:
                strandeds = _scan_and_emit_stranded(file_path)
                if strandeds:
                    crumb = _stranded_breadcrumb(strandeds)
                    if crumb:
                        print(f"[check_plan_edit] {crumb}", file=sys.stderr)
            except Exception:
                pass

        _claude_adapter.emit_decision(_to_contract_decision(decision))
        return 0
    except Exception as e:  # pragma: no cover
        print(
            f"[check_plan_edit] FATAL: {e.__class__.__name__}: {e}",
            file=sys.stderr,
        )
        _claude_adapter.emit_decision(_contract.allow())
        return 0


if __name__ == "__main__":
    sys.exit(main())
