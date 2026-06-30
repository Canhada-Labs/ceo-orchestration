#!/usr/bin/env python3
"""check_protocol_semver_cascade.py — PreToolUse advisory hook (PLAN-110 Wave D + PLAN-138 Wave D).

Detects PROTOCOL.md edit WITHOUT a paired ADR-AMEND edit in the same
tool-call session. Fail-OPEN: emits warning audit event
`protocol_edit_missing_amend_paired`, never blocks the session.

PLAN-138 Wave D (ADR-156) widens the hook into a *constitution
sync-cascade*: on ANY PROTOCOL.md edit (both the well-behaved
paired-amend path and the missing-amend path) it re-verifies a small,
explicit dependent-set and ships a **Sync Impact Report** through
`additionalContext` (booleans/counts only — NEVER echoing matched file
text). This is the downstream-sync half of spec-kit's (v0.11.0)
constitution cascade. It is advisory + **fail-OPEN ALWAYS**: it never
emits `permissionDecision`, never blocks the Owner GPG ceremony, never
increments ERRORS. A bad/garbage/binary dependent file, a blown time
budget, or the kill-switch all degrade to today's behavior.

Doctrine: PROTOCOL.md changes require semver discipline + Sync Impact
Report per `constitution.md:L302-L305` port. ADR-NNN-AMEND-M is the
canonical paired-edit pattern.

Kill-switch: CEO_PROTOCOL_SYNC_CASCADE=0 suppresses the Sync Impact
Report (the legacy missing-amend WARN still ships). Stdlib only, Python >= 3.9.

Activation: registered in .claude/settings.json PreToolUse chain.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Stdlib-only. Python >= 3.9.

# Sub-2s doctrine deadline (ADR-156 / D.1 / D.3). The hook fails OPEN and the
# real probe is ~5 targeted reads (<100ms warm), so 1.8s is an 18x safety teto,
# not the expected cost — it bounds a pathological dependent-set without ever
# stalling the PreToolUse chain. Checked in every probe loop. (Codex R1 P1#1:
# the doc + AC say sub-2s, so the constant matches them; 5.0 was a build drift.)
TIME_BUDGET_S = 1.8

# Per-file read cap for every dependent-set probe (bytes). Bounds the
# work even if a dependent file is pathologically large; we only need a
# section anchor, never the whole file.
_DEP_READ_CAP = 65536

# Printable-ASCII clamp length for any disk-sourced fragment rendered
# into the report (Codex S228 injection defense). We prefer
# booleans/counts over echoing matched text, but clamp defensively.
_FRAGMENT_CLAMP = 80


def _read_input() -> Dict:
    try:
        return json.loads(sys.stdin.read() or "{}")
    except json.JSONDecodeError:
        return {}


def _tool_targets_protocol(payload: Dict) -> bool:
    tool = payload.get("tool_name") or ""
    if tool not in {"Edit", "Write", "MultiEdit"}:
        return False
    inputs = payload.get("tool_input") or {}
    path = (inputs.get("file_path") or "").replace("\\", "/")
    return path.endswith("/PROTOCOL.md") or path == "PROTOCOL.md"


def _amend_in_session(payload: Dict) -> bool:
    """Heuristic: scan recent edits in same session for ADR-NNN-AMEND-M.

    F-NEW-2 fix (Codex Loop C): treat ONLY edits whose path or content
    references the explicit ``ADR-NNN-AMEND-M`` (or ``AMEND-M``) form
    as evidence of a paired amend. Edits to base ADR files under
    ``.claude/adr/`` alone are NOT proof of a paired amend (otherwise
    any ADR cleanup would silence the warning).
    """
    # Defensive: framework MAY provide session_edits in payload.context;
    # if absent, we fall back to advisory-only (no warning emitted on absence
    # of evidence — fail-OPEN per Tier-A doctrine).
    context = payload.get("context") or {}
    recent = context.get("session_edits") or []
    if not isinstance(recent, list):
        return False
    # Match the explicit AMEND-M suffix. Examples that match:
    #   .claude/adr/ADR-115-AMEND-1.md
    #   .claude/adr/ADR-100-AMEND-2-frob.md
    #   "(see ADR-123-AMEND-1 §2)"  (content excerpt)
    path_pattern = re.compile(r"/ADR-\d{3,}-AMEND-\d+", re.IGNORECASE)
    content_pattern = re.compile(r"ADR-\d{3,}-AMEND-\d+", re.IGNORECASE)
    for entry in recent:
        path = str(entry.get("file_path") or "")
        if path_pattern.search(path):
            return True
        text = str(entry.get("content_excerpt") or "")
        if content_pattern.search(text):
            return True
    return False


# ----------------------------------------------------------------------
# PLAN-138 Wave D (ADR-156) — constitution sync-cascade.
#
# The dependent-set is small, explicit, and keyed on STRUCTURAL anchors
# (section headings / frontmatter markers) NOT exact byte/line counts —
# so Wave A's §14 PLAN-SCHEMA addition and any legitimate renumber do
# NOT cry wolf. Each item is a (label, path, kind) where `kind` selects
# the probe. Probes return a boolean PRESENT/ABSENT (or None when the
# file is unreadable → INDETERMINATE, fail-open). The report renders
# booleans/counts only — matched file text is NEVER echoed.
# ----------------------------------------------------------------------


def _sanitize_path(rel: str) -> str:
    """Clamp any disk-sourced fragment rendered into the report.

    Printable-ASCII only (everything else → '?'), length-clamped. A
    filename / matched fragment carrying newlines or control chars could
    otherwise forge extra ``additionalContext`` lines (Codex S228 P0).
    """
    try:
        text = str(rel)
    except Exception:
        return ""
    cleaned = "".join(ch if 0x20 <= ord(ch) <= 0x7E else "?" for ch in text)
    return cleaned[:_FRAGMENT_CLAMP]


def _read_head(path: Path, deadline: float) -> Optional[str]:
    """Read up to _DEP_READ_CAP bytes as text; None on any failure / deadline.

    Fail-OPEN: a missing/binary/oversized/permission-denied file yields
    None and the caller treats the probe as INDETERMINATE, never a crash.
    """
    if time.monotonic() > deadline:
        return None
    try:
        with open(path, "rb") as fh:
            raw = fh.read(_DEP_READ_CAP)
    except OSError:
        return None
    try:
        return raw.decode("utf-8", errors="replace")
    except Exception:
        return None


def _probe_contains(path: Path, needle: str, deadline: float) -> Optional[bool]:
    """True if `needle` appears in the head of `path`; None if unreadable."""
    text = _read_head(path, deadline)
    if text is None:
        return None
    return needle in text


def _probe_regex(path: Path, pattern: "Optional[re.Pattern[str]]", deadline: float) -> Optional[bool]:
    """True if `pattern` matches the head of `path`; None if unreadable/no pattern."""
    if pattern is None:
        return None
    text = _read_head(path, deadline)
    if text is None:
        return None
    return bool(pattern.search(text))


def _probe_skill_frontmatter(path: Path, deadline: float) -> Optional[bool]:
    """LINT-FM-04/05 surrogate: the SKILL.md opens with a YAML frontmatter
    block (``---`` fence) carrying ``name:`` + ``description:`` keys.

    Targeted read of the head only (never the whole ~59KB SKILL.md), and
    NOT a shell-out to lint-skills.py — booleans only, fail-open.
    """
    text = _read_head(path, deadline)
    if text is None:
        return None
    if not text.lstrip().startswith("---"):
        return False
    # First frontmatter block ends at the next line that is exactly '---'.
    lines = text.splitlines()
    try:
        start = next(i for i, ln in enumerate(lines) if ln.strip() == "---")
    except StopIteration:
        return False
    block: List[str] = []
    for ln in lines[start + 1:]:
        if ln.strip() == "---":
            break
        block.append(ln)
    joined = "\n".join(block)
    return ("name:" in joined) and ("description:" in joined)


# Structural anchor for PLAN-SCHEMA §5: a markdown H2 heading numbered 5
# whose text is the required-body-sections section. Anchored on the
# heading shape, not on any byte count downstream of it.
_PLAN_SCHEMA_S5 = re.compile(r"(?m)^##\s*5\.\s+Required body sections")

_PROBE_REGEX_TABLE: Dict[str, "re.Pattern[str]"] = {
    "plan_schema_s5": _PLAN_SCHEMA_S5,
}


def _dependent_set(cwd: Path) -> List[Tuple[str, Path, str]]:
    """The small explicit dependent-set, documented in docs/PROTOCOL-SEMVER.md.

    Returns (label, path, kind) tuples. `kind` selects the probe:
      'contains:<needle>'  — substring present in head
      'regex:<key>'        — named regex (see _PROBE_REGEX_TABLE)
      'frontmatter'        — SKILL.md YAML frontmatter validity surrogate
      'present'            — file exists + non-empty head
    Keyed on STRUCTURAL anchors, never byte/line counts.
    """
    return [
        # [1] CLAUDE.md §Critical Rules present (heading text is the anchor).
        ("CLAUDE.md Critical Rules",
         cwd / "CLAUDE.md", "contains:Critical Rules"),
        # [2] PLAN-SCHEMA §5 required-body-sections heading present.
        ("PLAN-SCHEMA.md §5 Required body sections",
         cwd / ".claude" / "plans" / "PLAN-SCHEMA.md",
         "regex:plan_schema_s5"),
        # [3] ceo-orchestration SKILL.md frontmatter valid (LINT-FM-04/05).
        ("ceo-orchestration SKILL.md frontmatter",
         cwd / ".claude" / "skills" / "core" / "ceo-orchestration" / "SKILL.md",
         "frontmatter"),
        # [4] DEBATE-SCHEMA.md present.
        ("DEBATE-SCHEMA.md present",
         cwd / ".claude" / "plans" / "DEBATE-SCHEMA.md", "present"),
        # [5] validate-governance.sh still references PLAN-SCHEMA.
        ("validate-governance.sh references PLAN-SCHEMA",
         cwd / ".claude" / "scripts" / "validate-governance.sh",
         "contains:PLAN-SCHEMA"),
    ]


def _verify_dependent_set(cwd: Path, deadline: float) -> List[Tuple[str, str]]:
    """Probe each dependent-set item; return (sanitized_label, status).

    status ∈ {"PRESENT", "MISSING/DRIFT", "INDETERMINATE"}. INDETERMINATE
    means the probe could not read the file (fail-open) — distinct from
    MISSING/DRIFT (read OK but the structural anchor is gone). Booleans
    only; matched file text is NEVER echoed. The per-probe deadline is
    checked in the loop AND inside _read_head so a pathological
    dependent-set can never blow the budget.
    """
    findings: List[Tuple[str, str]] = []
    for label, path, kind in _dependent_set(cwd):
        if time.monotonic() > deadline:
            # Budget blown → mark the rest INDETERMINATE and stop probing.
            findings.append((_sanitize_path(label), "INDETERMINATE"))
            break
        result: Optional[bool]
        if kind == "frontmatter":
            result = _probe_skill_frontmatter(path, deadline)
        elif kind == "present":
            text = _read_head(path, deadline)
            result = bool(text and text.strip()) if text is not None else None
        elif kind.startswith("contains:"):
            result = _probe_contains(path, kind.split(":", 1)[1], deadline)
        elif kind.startswith("regex:"):
            result = _probe_regex(path, _PROBE_REGEX_TABLE.get(kind.split(":", 1)[1]), deadline)
        else:
            result = None
        if result is None:
            status = "INDETERMINATE"
        elif result:
            status = "PRESENT"
        else:
            status = "MISSING/DRIFT"
        findings.append((_sanitize_path(label), status))
    return findings


def _sync_impact_report(findings: List[Tuple[str, str]]) -> str:
    """Render the Sync Impact Report as sanitized booleans/counts only.

    Every label is re-sanitized at render time (defense-in-depth — a
    label can only carry printable ASCII so a control char in a matched
    fragment can never forge an extra line). Status values are from a
    closed set, never disk-sourced.
    """
    closed = {"PRESENT", "MISSING/DRIFT", "INDETERMINATE"}
    present = sum(1 for _, st in findings if st == "PRESENT")
    total = len(findings)
    lines = [
        "Sync Impact Report (advisory, fail-open — booleans only): "
        "%d/%d dependent artifacts PRESENT." % (present, total),
    ]
    for label, status in findings:
        safe = _sanitize_path(label)
        safe_status = status if status in closed else "INDETERMINATE"
        lines.append("  - %s: %s" % (safe, safe_status))
    return "\n".join(lines)


def _emit_warning() -> None:
    """Emit `protocol_edit_missing_amend_paired` audit action (fail-OPEN)."""
    # Defensive import — if audit_emit kernel unavailable, swallow silently
    # (fail-OPEN per PLAN-091-followup S116 doctrine).
    try:
        from _lib import audit_emit  # type: ignore
    except Exception:
        return
    try:
        # Use generic dispatch — typed wrapper may not exist until Owner
        # GPG-signed kernel override applies the new action allowlist.
        if hasattr(audit_emit, "emit_protocol_edit_missing_amend_paired"):
            audit_emit.emit_protocol_edit_missing_amend_paired(
                protocol_path="PROTOCOL.md",
                amend_present=False,
                hook_origin="check_protocol_semver_cascade",
            )
        else:
            # Fallback: best-effort breadcrumb (kernel will dedupe).
            audit_emit.emit_generic(  # type: ignore[attr-defined]
                action="protocol_edit_missing_amend_paired",
                protocol_path="PROTOCOL.md",
                amend_present=False,
                hook_origin="check_protocol_semver_cascade",
            )
    except Exception:
        # Final fail-OPEN: hook NEVER blocks on infra bugs.
        return


def _cwd_root() -> Path:
    """Repo root for dependent-set probes. CLAUDE_PROJECT_DIR wins; else cwd."""
    env = os.environ.get("CLAUDE_PROJECT_DIR", "").strip()
    if env:
        try:
            return Path(env)
        except Exception:
            return Path.cwd()
    return Path.cwd()


def _build_sync_report(deadline: float) -> Optional[str]:
    """The Sync Impact Report string, or None if the kill-switch is set
    or anything fails (fail-open)."""
    if os.environ.get("CEO_PROTOCOL_SYNC_CASCADE", "1") == "0":
        return None
    try:
        findings = _verify_dependent_set(_cwd_root(), deadline)
        if not findings:
            return None
        return _sync_impact_report(findings)
    except Exception:
        # Fail-OPEN: any error in the advisory cascade degrades to no report.
        return None


def main() -> int:
    payload = _read_input()
    # PIN ordering (ADR-156): read_input -> _tool_targets_protocol short-circuit
    # (ZERO dependent-set file reads on a non-PROTOCOL payload) -> only THEN
    # the deadline + dependent-set probe. This keeps the hot path a no-op.
    if not _tool_targets_protocol(payload):
        print("{}")  # allow — non-PROTOCOL edit, zero dependent-set reads
        return 0

    # Past the short-circuit: this IS a PROTOCOL.md edit. Build the Sync
    # Impact Report (kill-switch + fail-open inside _build_sync_report).
    deadline = time.monotonic() + TIME_BUDGET_S
    report = _build_sync_report(deadline)

    if _amend_in_session(payload):
        # Well-behaved common case. Previously returned bare {} here; now
        # we STILL ship the Sync Impact Report (ADR-156) when available.
        if report:
            out = {"hookSpecificOutput": {"additionalContext": report}}
            print(json.dumps(out))
        else:
            print("{}")  # allow — paired edit present, report suppressed/failed-open
        return 0

    # Missing-amend path: emit the legacy advisory audit event + WARN, and
    # append the Sync Impact Report as extra lines when available.
    _emit_warning()
    warn = (
        "WARN: PROTOCOL.md edit detected without paired ADR-NNN-AMEND-M. "
        "Per PROTOCOL.md semver doctrine (port of spec-kit "
        "constitution.md:L302-L305), protocol-level changes should "
        "ship paired with an ADR-AMEND. Advisory-only — non-blocking. "
        "If this is a typo-fix or formatting-only edit, ignore."
    )
    additional = warn + ("\n\n" + report if report else "")
    out = {
        "hookSpecificOutput": {
            "additionalContext": additional,
        },
    }
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
