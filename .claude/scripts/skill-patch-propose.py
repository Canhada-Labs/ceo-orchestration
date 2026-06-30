#!/usr/bin/env python3
"""skill-patch-propose.py — draft a SKILL.md patch proposal from lessons.

ADR-031, Sprint 11 Phase 4 (CR1 mitigation bundle).

Flow
----
1. Load the target SKILL.md (``<skill-dir>/SKILL.md``).
2. Load one or more lesson files from the ``--lessons`` path.
3. **REJECT** if any lesson fails the CR1 mitigation filters:
   - bidi / zero-width / control-char detected in raw source
   - scan-injection.py reports any flag
   - a line in the lesson exceeds 8000 chars (long-line hide)
   - homoglyph detected (mixed-script identifier heuristic)
4. Draft a unified diff versus current SKILL.md. Today this is a
   **conservative appender**: each qualifying lesson becomes one
   bulleted line under a new ``## Accrued lessons (SP-NNN)`` section.
   Tomorrow's merge strategies can plug in; the contract is that the
   diff is small, auditable, and reversible.
5. **REJECT** if the diff adds a fenced executable code block (python/
   bash/sh/js/ts) without ``CEO_SKILL_PATCH_ALLOW_CODE=1``.
6. **REJECT** if the diff exceeds 200 added + removed lines.
7. Write ``SP-NNN-<skill-slug>-<YYYY-MM-DD>.md`` under
   ``.claude/proposals/`` with YAML frontmatter + rationale +
   unified diff in a ``diff`` fence.

Rejections write ``SP-REJECTED-<timestamp>.md`` for audit. They do NOT
consume a sequence number.

``CEO_SOTA_DISABLE=1`` → exit 0 no-op (prints single-line stderr msg).

Stdlib-only. GPG is not invoked at propose time (apply.py handles that).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import difflib
import glob
import hashlib
import os
import re
import subprocess
import sys
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Tuple


_REPO_ROOT = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()).resolve()
_PROPOSALS_DIR = _REPO_ROOT / ".claude" / "proposals"
_SCAN_INJECTION = _REPO_ROOT / ".claude" / "scripts" / "scan-injection.py"

# Attack-character detectors
_BIDI_CODEPOINTS = frozenset({
    0x202A, 0x202B, 0x202C, 0x202D, 0x202E,  # embedding + override
    0x2066, 0x2067, 0x2068, 0x2069,           # isolate
})
_ZERO_WIDTH_CODEPOINTS = frozenset({
    0x200B,  # ZWSP
    0x200C,  # ZWNJ
    0x200D,  # ZWJ
    0x200E,  # LRM
    0x200F,  # RLM
    0xFEFF,  # ZWNBSP / BOM
})

# Fenced executable code block detector.
_FENCED_CODE_RE = re.compile(
    r"(?m)^\s*```\s*(python|python3|bash|sh|zsh|js|javascript|ts|typescript)\b"
)

# Homoglyph heuristic — any mixed-script word token (Cyrillic chars in an
# ASCII-looking token). Word is a sequence of non-whitespace chars.
_WORD_RE = re.compile(r"\S+")

# Long-line hide attack: a single line longer than this is rejected.
_MAX_LINE_CHARS = 8000

# Diff size cap (added + removed)
_DIFF_SIZE_CAP = 200


# -----------------------------------------------------------------------------
# Attack detectors
# -----------------------------------------------------------------------------


def _has_bidi_or_zero_width(text: str) -> Tuple[bool, str]:
    """Return (found, reason) — True if any bidi/zero-width chars present."""
    for ch in text:
        cp = ord(ch)
        if cp in _BIDI_CODEPOINTS:
            return True, f"bidi codepoint U+{cp:04X}"
        if cp in _ZERO_WIDTH_CODEPOINTS:
            return True, f"zero-width codepoint U+{cp:04X}"
    return False, ""


def _has_homoglyph(text: str) -> Tuple[bool, str]:
    """Heuristic: word-like token contains BOTH Latin and non-Latin scripts.

    We only flag Latin+Cyrillic mixtures (the classic api_key attack).
    Mixed-script in punctuation / comments is common in docs, so we only
    look at word tokens.
    """
    for match in _WORD_RE.finditer(text):
        tok = match.group(0)
        has_latin = False
        has_cyrillic = False
        for ch in tok:
            if ch.isalpha():
                try:
                    name = unicodedata.name(ch)
                except ValueError:
                    continue
                if name.startswith("LATIN "):
                    has_latin = True
                elif name.startswith("CYRILLIC "):
                    has_cyrillic = True
            if has_latin and has_cyrillic:
                return True, f"mixed-script token near byte {match.start()}"
    return False, ""


def _has_long_line(text: str) -> Tuple[bool, str]:
    for i, line in enumerate(text.splitlines(), 1):
        if len(line) > _MAX_LINE_CHARS:
            return True, f"line {i} is {len(line)} chars (> {_MAX_LINE_CHARS})"
    return False, ""


def _has_fenced_executable_code(text: str) -> Tuple[bool, str]:
    m = _FENCED_CODE_RE.search(text)
    if m:
        return True, f"fenced code block language={m.group(1)!r}"
    return False, ""


def _scan_lesson_via_subprocess(lesson_path: Path) -> Tuple[bool, str]:
    """Run scan-injection.py on the lesson; return (hit, reason).

    scan-injection.py exits 0 even on hits (advisory tool), so we parse
    its stdout to check for any match.
    """
    if not _SCAN_INJECTION.exists():
        return False, ""
    try:
        proc = subprocess.run(
            [sys.executable, str(_SCAN_INJECTION), "--json", str(lesson_path)],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, OSError) as e:
        return True, f"subprocess error: {type(e).__name__}: {e}"
    if proc.returncode != 0:
        return True, f"scan-injection exit {proc.returncode}: {proc.stderr[:120]}"
    # scan-injection prints JSON with `matched` bool
    out = proc.stdout or "{}"
    import json as _json
    try:
        parsed = _json.loads(out)
    except _json.JSONDecodeError:
        return True, "scan-injection produced invalid JSON"
    if parsed.get("matched"):
        fc = parsed.get("family_counts", {})
        return True, f"scan-injection flags: {fc}"
    return False, ""


# -----------------------------------------------------------------------------
# Proposal drafting
# -----------------------------------------------------------------------------


def _iter_lessons(lessons_arg: str) -> List[Path]:
    """Resolve the --lessons argument to a list of paths.

    Accepts a directory (all .md/.json files at top level), a single
    file, or a glob pattern.
    """
    p = Path(lessons_arg)
    if p.is_dir():
        out = []
        for ext in ("*.md", "*.json"):
            out.extend(sorted(p.glob(ext)))
        return out
    if p.is_file():
        return [p]
    # Treat as glob
    matches = [Path(x) for x in sorted(glob.glob(lessons_arg))]
    return [m for m in matches if m.is_file()]


def _read_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _resolve_skill_md(skill_slug: str, override: Optional[str]) -> Optional[Path]:
    """Locate the SKILL.md for the given slug."""
    if override:
        p = Path(override)
        if not p.is_absolute():
            p = _REPO_ROOT / p
        if p.is_file():
            return p.resolve()
        return None
    # Search under core, frontend, and domains.
    candidates = [
        _REPO_ROOT / ".claude" / "skills" / "core" / skill_slug / "SKILL.md",
        _REPO_ROOT / ".claude" / "skills" / "frontend" / skill_slug / "SKILL.md",
    ]
    for c in candidates:
        if c.is_file():
            return c.resolve()
    # Walk domains/*/skills/<slug>/SKILL.md
    domains_dir = _REPO_ROOT / ".claude" / "skills" / "domains"
    if domains_dir.is_dir():
        for d in sorted(domains_dir.iterdir()):
            candidate = d / "skills" / skill_slug / "SKILL.md"
            if candidate.is_file():
                return candidate.resolve()
    return None


def _next_proposal_id() -> str:
    """Return the next monotonic SP-NNN ID (zero-padded 3-digit)."""
    existing = 0
    if _PROPOSALS_DIR.is_dir():
        for entry in _PROPOSALS_DIR.iterdir():
            m = re.match(r"SP-(\d{3})-", entry.name)
            if m:
                n = int(m.group(1))
                if n > existing:
                    existing = n
    return f"SP-{existing + 1:03d}"


def _extract_lesson_summary(text: str, lesson_path: Path) -> str:
    """Extract a single-line, punctuation-safe summary from a lesson file.

    Preference order:
    1. A line starting with ``remember:`` or ``summary:`` (YAML-ish)
    2. The first non-heading, non-empty paragraph line
    3. The filename stem
    """
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        low = line.lower()
        if low.startswith("remember:") or low.startswith("summary:"):
            _, _, rest = line.partition(":")
            summary = rest.strip().strip("\"'")
            if summary:
                return _collapse(summary, 240)
        if line.startswith("#"):
            continue
        if line.startswith("---"):
            continue
        return _collapse(line, 240)
    return lesson_path.stem


def _collapse(text: str, max_len: int) -> str:
    t = " ".join(text.split())
    if len(t) > max_len:
        t = t[: max_len - 1] + "…"
    return t


def _draft_new_skill_text(
    current: str, lessons: List[Tuple[Path, str]], proposal_id: str
) -> str:
    """Append an 'Accrued lessons' section to the SKILL.md.

    Idempotent: if a block for this proposal_id already exists we replace
    it (avoids double-append during repeated runs during testing).
    """
    section_header = f"## Accrued lessons ({proposal_id})"
    body_lines = [section_header, ""]
    for lesson_path, lesson_text in lessons:
        summary = _extract_lesson_summary(lesson_text, lesson_path)
        body_lines.append(f"- {summary} _(source: {lesson_path.name})_")
    body_lines.append("")
    new_block = "\n".join(body_lines)

    # Remove any pre-existing block with the same proposal_id (idempotent
    # during testing).
    pattern = re.compile(
        r"\n## Accrued lessons \(" + re.escape(proposal_id) + r"\).*?(?=\n## |\Z)",
        flags=re.DOTALL,
    )
    cleaned = pattern.sub("", current)

    if cleaned and not cleaned.endswith("\n"):
        cleaned += "\n"
    return cleaned + "\n" + new_block + "\n"


def _compute_unified_diff(old: str, new: str, relpath: str) -> str:
    diff_lines = difflib.unified_diff(
        old.splitlines(keepends=True),
        new.splitlines(keepends=True),
        fromfile=f"a/{relpath}",
        tofile=f"b/{relpath}",
        lineterm="\n",
    )
    return "".join(diff_lines)


def _count_diff_lines(diff: str) -> Tuple[int, int]:
    """Count added and removed lines in a unified diff."""
    added = 0
    removed = 0
    for line in diff.splitlines():
        if line.startswith("+++") or line.startswith("---"):
            continue
        if line.startswith("+"):
            added += 1
        elif line.startswith("-"):
            removed += 1
    return added, removed


# -----------------------------------------------------------------------------
# Rejection writer
# -----------------------------------------------------------------------------


def _write_rejection(reason_code: str, detail: str) -> Path:
    _PROPOSALS_DIR.mkdir(parents=True, exist_ok=True)
    ts = _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%S")
    path = _PROPOSALS_DIR / f"SP-REJECTED-{ts}.md"
    body = (
        "---\n"
        "kind: skill_patch_rejected\n"
        f"rejected_at: {_dt.datetime.now(_dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}\n"
        f"reason_code: {reason_code}\n"
        "---\n\n"
        f"# Rejected skill-patch proposal\n\n{detail}\n"
    )
    path.write_text(body, encoding="utf-8")
    return path


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------


def _build_frontmatter(
    *,
    proposal_id: str,
    skill_slug: str,
    archetype: str,
    source_lessons: List[str],
    diff_added: int,
    diff_removed: int,
    sha256_of_diff: str,
) -> str:
    now = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    lines = ["---"]
    lines.append(f"id: {proposal_id}")
    lines.append(f"skill_slug: {skill_slug}")
    lines.append(f"archetype: {archetype}")
    lines.append(f"proposed_at: {now}")
    lines.append("source_lessons:")
    for lid in source_lessons:
        lines.append(f"  - {lid}")
    lines.append("scan_injection_pass: true")
    lines.append(f"diff_size_added: {diff_added}")
    lines.append(f"diff_size_removed: {diff_removed}")
    lines.append(f"sha256_of_diff: {sha256_of_diff}")
    lines.append("claims_declared: false")
    lines.append("status: draft")
    lines.append("approved_by: null")
    lines.append("applied_at: null")
    lines.append("promoted_at: null")
    lines.append("shadow_mode: true")
    lines.append("---")
    return "\n".join(lines) + "\n"


def _build_main_parser() -> argparse.ArgumentParser:
    """Construct argparse parser for skill-patch-propose.

    Extracted from main() for decomposition (PLAN-019 P2-002); tests
    can instantiate without invoking main.
    """
    parser = argparse.ArgumentParser(
        description="Draft a SKILL.md patch proposal from lessons (ADR-031).",
    )
    parser.add_argument("--archetype", required=True)
    parser.add_argument("--skill", required=True, dest="skill_slug")
    parser.add_argument("--lessons", required=True)
    parser.add_argument(
        "--skill-md",
        default=None,
        help="Override auto-resolution of the target SKILL.md path.",
    )
    return parser


def _scan_single_lesson(
    lp: Path, raw: str
) -> Optional[Tuple[str, str]]:
    """Run CR1 scanners on a single lesson's raw text.

    Returns ``None`` if the lesson passes every check, otherwise a
    ``(reason_code, human_message)`` tuple that main() will pass to
    :func:`_write_rejection`.
    """
    bidi, bidi_reason = _has_bidi_or_zero_width(raw)
    if bidi:
        return "bidi_or_zero_width", f"Lesson {lp.name}: {bidi_reason}"

    homo, homo_reason = _has_homoglyph(raw)
    if homo:
        return "homoglyph_hit", f"Lesson {lp.name}: {homo_reason}"

    long_line, long_reason = _has_long_line(raw)
    if long_line:
        return "long_line_hidden_payload", f"Lesson {lp.name}: {long_reason}"

    # CR1 row #3: reject if source lesson contains fenced executable
    # code (even if our conservative summary extractor would drop
    # it). This is defense-in-depth against a summary-extractor bug
    # smuggling the fenced block through. Override via
    # CEO_SKILL_PATCH_ALLOW_CODE=1 routes to second-stage review.
    fenced_src, fenced_src_reason = _has_fenced_executable_code(raw)
    if fenced_src and os.environ.get("CEO_SKILL_PATCH_ALLOW_CODE") != "1":
        return (
            "fenced_executable_code",
            f"Lesson {lp.name}: {fenced_src_reason} (source). "
            f"Override with CEO_SKILL_PATCH_ALLOW_CODE=1 for human review.",
        )

    scan_hit, scan_reason = _scan_lesson_via_subprocess(lp)
    if scan_hit:
        reason_code = (
            "subprocess_error"
            if scan_reason.startswith("subprocess error")
            else "scan_injection_hit"
        )
        return reason_code, f"Lesson {lp.name}: {scan_reason}"

    # CR1 row #4 (source-size arm): any single lesson exceeding
    # ~200 source lines is a vector for slipping bloated content
    # past review. Reject — the Owner can split the lesson if
    # legitimate.
    src_line_count = raw.count("\n")
    if src_line_count > _DIFF_SIZE_CAP:
        return (
            "diff_too_large",
            f"Lesson {lp.name}: source is {src_line_count} lines "
            f"(cap={_DIFF_SIZE_CAP}).",
        )

    return None


def _collect_accepted_lessons(
    lesson_paths: List[Path],
) -> Tuple[Optional[int], List[Tuple[Path, str]]]:
    """Walk candidate lessons, rejecting the batch on first CR1 hit.

    Returns ``(exit_code, accepted)``. If ``exit_code`` is not None, the
    caller must return it after the rejection has already been recorded
    via :func:`_write_rejection` + stderr by this function. On success
    returns ``(None, accepted_lessons)``.
    """
    accepted_lessons: List[Tuple[Path, str]] = []
    for lp in lesson_paths:
        raw = _read_file(lp)
        if not raw:
            continue
        rejection = _scan_single_lesson(lp, raw)
        if rejection is not None:
            reason_code, message = rejection
            _write_rejection(reason_code, message)
            sys.stderr.write(
                f"[skill-patch-propose] rejected: {message}\n"
            )
            return 1, []
        accepted_lessons.append((lp, raw))

    if not accepted_lessons:
        _write_rejection(
            "skill_target_missing",
            "No lessons survived the CR1 scan (every lesson was empty).",
        )
        sys.stderr.write(
            "[skill-patch-propose] rejected: 0 lessons survived scan\n"
        )
        return 1, []
    return None, accepted_lessons


def _draft_and_validate_diff(
    skill_md: Path,
    accepted_lessons: List[Tuple[Path, str]],
    proposal_id: str,
) -> Tuple[Optional[int], str, str, int, int]:
    """Produce the unified diff and enforce fenced-code + size caps.

    Returns ``(exit_code, diff, relpath, added, removed)``. If
    ``exit_code`` is not None, a rejection has already been written
    and the caller should return it.
    """
    current_skill = _read_file(skill_md)
    new_skill = _draft_new_skill_text(
        current_skill, accepted_lessons, proposal_id
    )
    relpath = str(skill_md.relative_to(_REPO_ROOT)).replace(os.sep, "/")
    diff = _compute_unified_diff(current_skill, new_skill, relpath)

    # --- Fenced-code check on the DIFF (what gets applied) ----------------
    fenced, fenced_reason = _has_fenced_executable_code(diff)
    if fenced and os.environ.get("CEO_SKILL_PATCH_ALLOW_CODE") != "1":
        _write_rejection(
            "fenced_executable_code",
            f"Diff contains fenced code: {fenced_reason}. "
            f"Override with CEO_SKILL_PATCH_ALLOW_CODE=1 for a human-reviewed "
            f"second-stage pass.",
        )
        sys.stderr.write(
            f"[skill-patch-propose] rejected: {fenced_reason}\n"
        )
        return 1, "", "", 0, 0

    added, removed = _count_diff_lines(diff)
    if added + removed > _DIFF_SIZE_CAP:
        _write_rejection(
            "diff_too_large",
            f"Diff is {added}+ / {removed}- lines = {added + removed} "
            f"(cap={_DIFF_SIZE_CAP}).",
        )
        sys.stderr.write(
            f"[skill-patch-propose] rejected: diff too large "
            f"({added + removed} > {_DIFF_SIZE_CAP})\n"
        )
        return 1, "", "", 0, 0

    return None, diff, relpath, added, removed


def _write_proposal_file(
    *,
    proposal_id: str,
    skill_slug: str,
    archetype: str,
    accepted_lessons: List[Tuple[Path, str]],
    diff: str,
    relpath: str,
    added: int,
    removed: int,
) -> int:
    """Render + write the proposal Markdown under ``.claude/proposals/``.

    Always returns 0 — the caller has already validated inputs via
    :func:`_draft_and_validate_diff`.
    """
    sha_hex = hashlib.sha256(diff.encode("utf-8")).hexdigest()
    today = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d")
    filename = f"{proposal_id}-{skill_slug}-{today}.md"
    target = _PROPOSALS_DIR / filename
    _PROPOSALS_DIR.mkdir(parents=True, exist_ok=True)

    source_lesson_ids = [lp.stem for lp, _ in accepted_lessons]
    frontmatter = _build_frontmatter(
        proposal_id=proposal_id,
        skill_slug=skill_slug,
        archetype=archetype,
        source_lessons=source_lesson_ids,
        diff_added=added,
        diff_removed=removed,
        sha256_of_diff=sha_hex,
    )

    rationale_lines = [
        f"# {proposal_id} — skill patch proposal",
        "",
        f"**Target:** `{relpath}`  ",
        f"**Archetype:** {archetype}  ",
        f"**Lessons folded in:** {len(accepted_lessons)}",
        "",
        "## Rationale",
        "",
        "Automated fold of accrued lessons into the skill file. "
        "Each lesson below was scanned for injection + Unicode attack "
        "characters + homoglyphs + long-line truncation + fenced "
        "executable code before inclusion (ADR-031 CR1 mitigation).",
        "",
        "## Source lessons",
        "",
    ]
    for lp, lt in accepted_lessons:
        rationale_lines.append(f"- `{lp.name}` — {_extract_lesson_summary(lt, lp)}")
    rationale_lines.append("")
    rationale_lines.append("## Proposed diff")
    rationale_lines.append("")
    rationale_lines.append("```diff")
    rationale_lines.append(diff.rstrip("\n"))
    rationale_lines.append("```")
    rationale_lines.append("")
    rationale = "\n".join(rationale_lines)

    target.write_text(frontmatter + "\n" + rationale + "\n", encoding="utf-8")
    print(
        f"[skill-patch-propose] wrote {target.relative_to(_REPO_ROOT)} "
        f"({added}+/{removed}- lines, sha256={sha_hex[:12]}…)"
    )
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """Draft a skill-patch proposal from accrued lessons (ADR-031).

    Orchestrates: CLI parse → skill resolution → lesson enumeration →
    CR1 scan per lesson → unified-diff draft + size/fenced-code gate →
    proposal file write. Helpers handle the heavy lifting; see
    :func:`_collect_accepted_lessons`, :func:`_draft_and_validate_diff`,
    :func:`_write_proposal_file`.
    """
    parser = _build_main_parser()
    args = parser.parse_args(argv)

    if os.environ.get("CEO_SOTA_DISABLE") == "1":
        sys.stderr.write("[skill-patch-propose] CEO_SOTA_DISABLE=1 — no-op\n")
        return 0

    skill_md = _resolve_skill_md(args.skill_slug, args.skill_md)
    if skill_md is None:
        _write_rejection(
            "skill_target_missing",
            f"Could not locate SKILL.md for skill_slug={args.skill_slug!r} "
            f"(tried core/, frontend/, domains/*/skills/).",
        )
        sys.stderr.write(
            f"[skill-patch-propose] rejected: skill target missing for "
            f"{args.skill_slug!r}\n"
        )
        return 1

    lesson_paths = _iter_lessons(args.lessons)
    if not lesson_paths:
        _write_rejection(
            "skill_target_missing",
            f"No lessons matched --lessons={args.lessons!r}.",
        )
        sys.stderr.write(
            f"[skill-patch-propose] rejected: no lessons matched "
            f"{args.lessons!r}\n"
        )
        return 1

    # --- CR1 mitigations: per-lesson scan ---------------------------------
    rc, accepted_lessons = _collect_accepted_lessons(lesson_paths)
    if rc is not None:
        return rc

    # --- Draft diff -------------------------------------------------------
    proposal_id = _next_proposal_id()
    rc, diff, relpath, added, removed = _draft_and_validate_diff(
        skill_md, accepted_lessons, proposal_id
    )
    if rc is not None:
        return rc

    # --- Write proposal ---------------------------------------------------
    return _write_proposal_file(
        proposal_id=proposal_id,
        skill_slug=args.skill_slug,
        archetype=args.archetype,
        accepted_lessons=accepted_lessons,
        diff=diff,
        relpath=relpath,
        added=added,
        removed=removed,
    )


if __name__ == "__main__":
    sys.exit(main())
