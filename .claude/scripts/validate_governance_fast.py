#!/usr/bin/env python3
"""validate_governance_fast.py — PLAN-082 Codex Item A fast profile.

Replaces the slow full `validate-governance.sh` walk for Tier-S ceo-boot
consumption. Budget: <2s wall-clock. Codex MCP `019e175b…` verdict
Option 4 (two-tier split): fast profile runs cheap structural checks
only; full profile (`validate-governance.sh` without `--fast`) keeps
running in CI / pre-commit / explicit ceremonies.

Fast checks:
1. settings.json JSON parse
2. Required governance files present (CLAUDE.md, PROTOCOL.md, team rosters)
3. Active hook references in settings.json point to files that exist,
   are executable, and `py_compile` cleanly (for .py hooks)
4. Python shim `.claude/hooks/_python-hook.sh` exists + executable
5. PLAN-SCHEMA §1 invariants (subdirs + filenames under .claude/plans/)
6. PLAN-SCHEMA §13 verification declarations (``Check:`` per execution
   unit) — PROSPECTIVE: only plans with ``created: >= 2026-06-12`` and a
   non-terminal status (PLAN-134 W1, doctrine V0)

Out-of-scope (full profile only):
- Skill frontmatter V3/V2 sweeps, ADR scans, doc drift counts,
  domain bundle audits, native-agent reciprocity, hash scans

Usage:
    validate_governance_fast.py            # human-readable
    validate_governance_fast.py --json     # machine-readable JSON

Exit:
    0 if errors == []
    1 otherwise

Stdlib only, Python 3.9+.
"""
from __future__ import annotations

import argparse
import json
import os
import py_compile
import re
import sys
import time
from pathlib import Path
from typing import List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]

_HOOK_PY_RE = re.compile(r"\.claude/hooks/[A-Za-z0-9_./-]+\.py")
# Shim invocation: `_python-hook.sh <script.py>` — the script arg may be a
# basename (resolved to .claude/hooks/<basename>) or a relative path.
_SHIM_INVOCATION_RE = re.compile(
    r"_python-hook\.sh[\"']?\s+[\"']?([A-Za-z0-9_./-]+\.py)"
)
# PLAN-SCHEMA.md §1.4 — Followup plans address residual work descoped from a
# parent. They preserve the parent's NNN for visual linkage, with `FOLLOWUP` as
# a sub-segment, mirroring the canonical ADR amendment convention
# (`ADR-NNN-AMEND-M-<slug>.md`). The followup carries its parent's identity
# by design — GPG-signed sentinels and shipped tags referring to
# "PLAN-NNN-FOLLOWUP" remain stable across schema evolution. Multi-followup
# disambiguation uses kebab-slug suffix (`PLAN-NNN-FOLLOWUP-<slug>`) — see
# PLAN-SCHEMA.md §1.4 "Multi-followup".
_PLAN_FILENAME_RE = re.compile(
    r"^PLAN-[0-9]{3}(-FOLLOWUP)?-[a-z0-9]+(-[a-z0-9]+)*\.md$"
)
_SPRINT_FILENAME_RE = re.compile(r"^SPRINT-[0-9]+.*\.md$")
_KNOWN_GOV_FILES = {
    "README.md",
    "PLAN-SCHEMA.md",
    "AUDIT-LOG-SCHEMA.md",
    "DEBATE-SCHEMA.md",
}
# Subdir regex mirrors filename regex's `-FOLLOWUP[-<slug>]` tolerance so that
# a shipped followup's artifact subdir (sentinels/, forensics/, etc.) can match
# its plan file 1:1 when multiple followups share a parent NNN.
_VALID_PLAN_SUBDIR_RE = re.compile(
    r"^PLAN-[0-9]{3}(-FOLLOWUP(-[a-z0-9]+(-[a-z0-9]+)*)?)?$"
)
_VALID_PLAN_SUBDIR_FIXED = {"examples", "archive", "WAR-ROOM", "_templates"}
_REQUIRED_FILES = (
    "CLAUDE.md",
    "PROTOCOL.md",
    ".claude/team.md",
    ".claude/frontend-team.md",
)


def _check_settings_json(repo: Path, errors: List[str], warnings: List[str]) -> dict:
    settings = repo / ".claude" / "settings.json"
    if not settings.exists():
        warnings.append("settings_json:missing")
        return {}
    try:
        return json.loads(settings.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        errors.append(f"settings_json:parse_fail:{exc.__class__.__name__}")
        return {}


def _check_required_files(repo: Path, errors: List[str]) -> None:
    for rel in _REQUIRED_FILES:
        if not (repo / rel).is_file():
            errors.append(f"required_file_missing:{rel}")


def _normalize_hook_ref(ref: str) -> str:
    """Resolve a raw command-line .py ref to canonical `.claude/hooks/<name>.py`.

    Inputs we see in settings.json:
    - `.claude/hooks/check_X.py` (absolute relative) — pass through
    - `$CLAUDE_PROJECT_DIR/.claude/hooks/check_X.py` — strip env-var prefix
    - `check_X.py` (basename from shim invocation) — prepend `.claude/hooks/`
    """
    s = ref
    # Strip ${CLAUDE_PROJECT_DIR}/ or $CLAUDE_PROJECT_DIR/
    s = re.sub(r"^\$\{?CLAUDE_PROJECT_DIR\}?/", "", s)
    if "/" not in s:
        return f".claude/hooks/{s}"
    return s


def _extract_hook_paths(settings_data: dict) -> List[str]:
    """Walk settings.json hook tables; return canonical relative paths.

    Detects both direct `.claude/hooks/X.py` references AND shim-invoked
    `_python-hook.sh <basename>.py` patterns. Output order = first-seen.
    """
    seen: List[str] = []
    seen_set: set = set()
    hooks = settings_data.get("hooks") if isinstance(settings_data, dict) else None
    if not isinstance(hooks, dict):
        return []
    for hook_list in hooks.values():
        if not isinstance(hook_list, list):
            continue
        for entry in hook_list:
            if not isinstance(entry, dict):
                continue
            inner = entry.get("hooks") if isinstance(entry.get("hooks"), list) else []
            for cmd_obj in inner:
                if not isinstance(cmd_obj, dict):
                    continue
                cmd_str = cmd_obj.get("command", "")
                if not isinstance(cmd_str, str):
                    continue
                refs: List[str] = []
                refs.extend(_HOOK_PY_RE.findall(cmd_str))
                refs.extend(_SHIM_INVOCATION_RE.findall(cmd_str))
                for raw in refs:
                    canonical = _normalize_hook_ref(raw)
                    if canonical not in seen_set:
                        seen_set.add(canonical)
                        seen.append(canonical)
    return seen


def _check_active_hooks(
    repo: Path, settings_data: dict, errors: List[str], warnings: List[str]
) -> int:
    hook_paths = _extract_hook_paths(settings_data)
    checked = 0
    for rel in hook_paths:
        abs_path = repo / rel
        if not abs_path.is_file():
            errors.append(f"hook_missing:{rel}")
            continue
        try:
            py_compile.compile(str(abs_path), doraise=True)
        except (py_compile.PyCompileError, OSError) as exc:
            errors.append(f"hook_py_compile_fail:{rel}:{exc.__class__.__name__}")
            continue
        checked += 1
    return checked


def _check_python_shim(repo: Path, errors: List[str], warnings: List[str]) -> None:
    shim = repo / ".claude" / "hooks" / "_python-hook.sh"
    if not shim.is_file():
        warnings.append("python_shim:missing")
        return
    if not os.access(shim, os.X_OK):
        errors.append("python_shim:not_executable")


def _check_plan_schema(repo: Path, errors: List[str]) -> None:
    plan_dir = repo / ".claude" / "plans"
    if not plan_dir.is_dir():
        return
    for entry in plan_dir.iterdir():
        name = entry.name
        if entry.is_dir():
            if name in _VALID_PLAN_SUBDIR_FIXED:
                continue
            if _VALID_PLAN_SUBDIR_RE.match(name):
                continue
            errors.append(f"plan_schema_subdir:{name}")
            continue
        if entry.is_file():
            if name == ".DS_Store":
                continue
            if name in _KNOWN_GOV_FILES:
                continue
            if _SPRINT_FILENAME_RE.match(name):
                continue
            if not _PLAN_FILENAME_RE.match(name):
                errors.append(f"plan_schema_filename:{name}")


def _extract_plan_id(path: Path) -> Optional[str]:
    """Read the frontmatter ``id:`` of a plan file (first ``id:`` inside the
    leading ``---``...``---`` block, anchored at the start of the file).
    Fail-soft: unreadable/absent → None. A Markdown horizontal rule later in
    the body must NOT be mistaken for a frontmatter fence (mirrors
    ``_extract_plan_status`` + ceo-boot.py's ``re.match(r"^---...")``)."""
    try:
        with path.open(encoding="utf-8") as fh:
            in_fm = False
            first = True
            for line in fh:
                s = line.strip()
                if first:
                    first = False
                    if s != "---":
                        return None
                    in_fm = True
                    continue
                if s == "---":
                    break
                if in_fm and s.startswith("id:"):
                    return s[3:].strip()
    except (OSError, UnicodeDecodeError):
        return None
    return None


def _check_plan_id_uniqueness(repo: Path, errors: List[str]) -> None:
    """PLAN-112-FOLLOWUP-plan-093-followup-collision W3 — enforce frontmatter
    ``id:`` uniqueness across root-level plan files. Two plans sharing one id
    (the PLAN-093-FOLLOWUP dual-id class) make every ``id:`` reference
    ambiguous. Root level only (``iterdir``, non-recursive) so PLAN-NNN/
    artifact subdirs + PLAN-112/sandbox clones never trip a false duplicate."""
    plan_dir = repo / ".claude" / "plans"
    if not plan_dir.is_dir():
        return
    id_to_files: dict = {}
    for entry in plan_dir.iterdir():
        if not entry.is_file() or not _PLAN_FILENAME_RE.match(entry.name):
            continue
        pid = _extract_plan_id(entry)
        if pid:
            id_to_files.setdefault(pid, []).append(entry.name)
    for pid in sorted(id_to_files):
        files = id_to_files[pid]
        if len(files) > 1:
            errors.append(f"plan_id_duplicate:{pid}:{','.join(sorted(files))}")


_LEGAL_PLAN_STATUSES = frozenset(
    {"draft", "reviewed", "executing", "done", "abandoned", "refused", "superseded"}
)


def _extract_plan_status(path: Path) -> Optional[str]:
    """Read the frontmatter ``status:`` of a plan file (first ``status:``
    inside the leading ``---``...``---`` block). Fail-soft: unreadable or
    absent → None. Mirrors ``_extract_plan_id`` so a body-only ``status:``
    line (e.g. ``- **status:** done``) is deliberately NOT matched."""
    try:
        with path.open(encoding="utf-8") as fh:
            in_fm = False
            first = True
            for line in fh:
                s = line.strip()
                if first:
                    first = False
                    # Frontmatter MUST be anchored at the start of the file
                    # (mirrors ceo-boot.py's ``re.match(r"^---...")``). A plain
                    # Markdown horizontal rule later in the body must NOT be
                    # mistaken for a frontmatter fence — otherwise a body-only
                    # status would satisfy this gate while staying invisible to
                    # the boot detectors (Codex S213 [P2]).
                    if s != "---":
                        return None
                    in_fm = True
                    continue
                if s == "---":
                    break  # end of the leading frontmatter block
                if in_fm and s.startswith("status:"):
                    return s[len("status:"):].strip()
    except (OSError, UnicodeDecodeError):
        return None
    return None


def _check_plan_frontmatter_status(repo: Path, errors: List[str]) -> None:
    """PLAN-SCHEMA §2 (required fields) + §4 (lifecycle states) — every plan
    MUST carry a legal ``status:`` in its YAML frontmatter, not only in body
    prose. ceo-boot's plan-state detectors (plans_executing /
    plans_reviewed_pending / plans_draft + the stranded-executing and
    active-plan-burn checks deriving from them) read ``status:`` from the
    frontmatter ONLY; a body-only status is invisible to governance (the
    S213 PLAN-128-executing blind-spot). Root level only (``iterdir``,
    non-recursive) so PLAN-NNN/ artifact subdirs never trip it. Mirrors the
    bash gate in validate-governance.sh §1 item 4."""
    plan_dir = repo / ".claude" / "plans"
    if not plan_dir.is_dir():
        return
    for entry in plan_dir.iterdir():
        if not entry.is_file() or not _PLAN_FILENAME_RE.match(entry.name):
            continue
        status = _extract_plan_status(entry)
        if not status:
            errors.append(f"plan_status_missing:{entry.name}")
        elif status not in _LEGAL_PLAN_STATUSES:
            errors.append(f"plan_status_illegal:{entry.name}:{status}")


def _check_plan_id_presence(repo: Path, errors: List[str]) -> None:
    """PLAN-SCHEMA §2 (required fields) — every plan MUST carry an ``id:`` in
    its YAML frontmatter. The id-uniqueness guard is fail-soft on id-less
    files (it only flags duplicates), so a plan with no id at all silently
    escaped governance until this presence gate. Root level only. Mirrors the
    bash gate in validate-governance.sh §1 item 5."""
    plan_dir = repo / ".claude" / "plans"
    if not plan_dir.is_dir():
        return
    for entry in plan_dir.iterdir():
        if not entry.is_file() or not _PLAN_FILENAME_RE.match(entry.name):
            continue
        if not _extract_plan_id(entry):
            errors.append(f"plan_id_missing:{entry.name}")


# --- PLAN-SCHEMA §13 — verification declaration per execution unit -----------
# PLAN-134 W1 item 1 (VeriMAP steal, R3): doctrine V0 of the deterministic-
# first verification cascade. Every execution unit (markdown checkbox in a
# Waves/Progress-log-style section) must declare its mechanical check (V1)
# upfront via a `Check:` line, or explicitly `Check: none (doc-only)`.
# PROSPECTIVE: plans created before 2026-06-12 (the ~155 existing plans) are
# grandfathered and must never redden. Terminal-status plans are exempt.
_VCHECK_ENFORCE_FROM = "2026-06-12"
_VCHECK_STATUSES = frozenset({"draft", "reviewed", "executing"})
# A checkbox is enforced when ANY enclosing heading title starts with one of
# these (case-insensitive): `wave` covers "Waves" / "Wave 1" / "Wave A — …".
_VCHECK_SECTION_PREFIXES = ("wave", "progress log", "items", "sprint plan")
_VCHECK_CHECKBOX_RE = re.compile(r"^\s*-\s\[[ xX~]\]\s*(.*)$")
_VCHECK_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
# `Check:` token: case-sensitive, preceded by start-of-line or a non-word
# char (so "PreCheck:" never matches), followed by a non-empty value.
_VCHECK_DECL_RE = re.compile(r"(?:^|[^\w])Check:\s*\S")
_VCHECK_ISO_DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")


def _extract_plan_created(path: Path) -> Optional[str]:
    """Read the frontmatter ``created:`` of a plan file (first ``created:``
    inside the leading ``---``...``---`` block, anchored at the start of the
    file). Fail-soft: unreadable/absent → None. Mirrors ``_extract_plan_id``
    / ``_extract_plan_status``."""
    try:
        with path.open(encoding="utf-8") as fh:
            in_fm = False
            first = True
            for line in fh:
                s = line.strip()
                if first:
                    first = False
                    if s != "---":
                        return None
                    in_fm = True
                    continue
                if s == "---":
                    break
                if in_fm and s.startswith("created:"):
                    raw = s[len("created:"):].strip()
                    # YAML-quoted dates (created: "2026-06-12") must not
                    # dodge the prospective gate (Codex S228 finding #5).
                    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
                        raw = raw[1:-1].strip()
                    return raw
    except (OSError, UnicodeDecodeError):
        return None
    return None


def _vcheck_scan_body(path: Path, errors: List[str]) -> None:
    """Scan one plan body for PLAN-SCHEMA §13.2 coverage. A checkbox item is
    covered when a ``Check:`` declaration is (1) inline on the checkbox line,
    (2) on a later line before the next checkbox/heading (continuation), or
    (3) between the block's heading and its FIRST checkbox (block-level —
    covers every checkbox in the block; any heading resets it). Fenced code
    blocks are ignored."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return

    def _flush(pend: Optional[list]) -> None:
        if pend is not None and not pend[2]:
            errors.append(
                "plan_vcheck_missing:{}:L{}:{}".format(
                    path.name, pend[0], pend[1][:60]
                )
            )

    in_fence = False
    # (level, is_enforced) per open heading — enforced if ANY enclosing
    # heading title starts with a §13.3 prefix.
    heading_stack: List[tuple] = []
    block_covered = False
    pending: Optional[list] = None  # [lineno, item_text, covered]
    for lineno, raw in enumerate(lines, 1):
        stripped = raw.strip()
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        hm = _VCHECK_HEADING_RE.match(raw)
        if hm:
            _flush(pending)
            pending = None
            level = len(hm.group(1))
            title = hm.group(2).strip().lower()
            while heading_stack and heading_stack[-1][0] >= level:
                heading_stack.pop()
            heading_stack.append(
                (level, title.startswith(_VCHECK_SECTION_PREFIXES))
            )
            block_covered = False
            continue
        if not any(flag for _, flag in heading_stack):
            continue
        cm = _VCHECK_CHECKBOX_RE.match(raw)
        if cm:
            _flush(pending)
            covered = block_covered or bool(_VCHECK_DECL_RE.search(raw))
            pending = [lineno, cm.group(1).strip(), covered]
        elif _VCHECK_DECL_RE.search(raw):
            if pending is not None:
                pending[2] = True
            else:
                block_covered = True
    _flush(pending)


def _check_plan_vcheck_declarations(repo: Path, errors: List[str]) -> None:
    """PLAN-SCHEMA §13 — every execution unit declares its mechanical check
    upfront (PLAN-134 W1, doctrine V0). Prospective: only plans whose
    frontmatter ``created:`` is an ISO date >= 2026-06-12 AND whose status is
    draft/reviewed/executing. Missing or non-ISO ``created:`` → grandfathered
    (fail-soft, matching the other plan gates). Root level only."""
    plan_dir = repo / ".claude" / "plans"
    if not plan_dir.is_dir():
        return
    for entry in sorted(plan_dir.iterdir()):
        if not entry.is_file() or not _PLAN_FILENAME_RE.match(entry.name):
            continue
        created = _extract_plan_created(entry)
        if not created or not _VCHECK_ISO_DATE_RE.match(created):
            continue
        if created < _VCHECK_ENFORCE_FROM:
            continue
        if _extract_plan_status(entry) not in _VCHECK_STATUSES:
            continue
        _vcheck_scan_body(entry, errors)


def run(repo: Path) -> dict:
    """Execute the fast profile. Returns a result dict."""
    t0 = time.monotonic()
    errors: List[str] = []
    warnings: List[str] = []
    checks_run: List[str] = []

    checks_run.append("settings_json")
    settings_data = _check_settings_json(repo, errors, warnings)

    checks_run.append("required_files")
    _check_required_files(repo, errors)

    checks_run.append("active_hooks")
    hooks_checked = _check_active_hooks(repo, settings_data, errors, warnings)

    checks_run.append("python_shim")
    _check_python_shim(repo, errors, warnings)

    checks_run.append("plan_schema")
    _check_plan_schema(repo, errors)

    checks_run.append("plan_id_uniqueness")
    _check_plan_id_uniqueness(repo, errors)

    checks_run.append("plan_frontmatter_status")
    _check_plan_frontmatter_status(repo, errors)

    checks_run.append("plan_id_presence")
    _check_plan_id_presence(repo, errors)

    checks_run.append("plan_vcheck_declarations")
    _check_plan_vcheck_declarations(repo, errors)

    duration_ms = int((time.monotonic() - t0) * 1000)
    return {
        "profile": "fast",
        "rc": 1 if errors else 0,
        "duration_ms": duration_ms,
        "errors": errors,
        "warnings": warnings,
        "checks_run": checks_run,
        "hooks_checked": hooks_checked,
    }


def _format_human(result: dict) -> str:
    lines = [
        "=== Governance Validation (fast profile) ===",
        f"  duration: {result['duration_ms']} ms",
        f"  checks:   {', '.join(result['checks_run'])}",
        f"  hooks_checked: {result['hooks_checked']}",
        f"  errors:   {len(result['errors'])}",
        f"  warnings: {len(result['warnings'])}",
    ]
    if result["errors"]:
        lines.append("")
        lines.append("FAIL:")
        for e in result["errors"]:
            lines.append(f"  - {e}")
    if result["warnings"]:
        lines.append("")
        lines.append("WARN:")
        for w in result["warnings"]:
            lines.append(f"  - {w}")
    lines.append("")
    lines.append("PASS" if result["rc"] == 0 else f"FAIL: {len(result['errors'])} error(s)")
    return "\n".join(lines)


def main(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(description="Fast governance validation")
    parser.add_argument("--json", action="store_true", help="Emit JSON")
    parser.add_argument(
        "--repo", default=str(REPO_ROOT), help="Repo root (default: parents[2])"
    )
    args = parser.parse_args(argv)
    repo = Path(args.repo).resolve()
    result = run(repo)
    if args.json:
        print(json.dumps(result, sort_keys=True))
    else:
        print(_format_human(result))
    return result["rc"]


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
