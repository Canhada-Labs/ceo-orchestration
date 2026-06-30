#!/usr/bin/env python3
"""scan-upstream-injection.py — PLAN-074 Wave 0 upstream injection scanner.

Scans a directory tree of .md files for prompt-injection signatures that
could indicate the upstream repo was crafted to subvert an LLM.

Pattern catalogue per ADR-077 + ADR-083 + _lib/injection_patterns.py:
  - system_reminder_spoof   HIGH   <system-reminder> variants
  - role_flip               HIGH   "Ignore previous instructions", "You are now"
  - tool_spoof              HIGH   fenced tool_result / claude_code blocks
  - exfiltration            HIGH   credentials leak / env / ssh key patterns
  - script_inject           HIGH   <script>, <iframe>, javascript: URI
  - base64_payload          MEDIUM long base64 strings outside code fences
  - homoglyph               MEDIUM NFKC normalization changes content
  - prompt_leakage          LOW    "your system prompt", "show me the prompt"

CLI:
    python3 scan-upstream-injection.py <root_dir> [--out report.md]
                                       [--severity-floor LOW|MEDIUM|HIGH]

Exit: 0 = no HIGH findings; 1 = HIGH findings present.
"""
from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Severity constants
# ---------------------------------------------------------------------------

LOW = "LOW"
MEDIUM = "MEDIUM"
HIGH = "HIGH"

_SEVERITY_ORDER = {LOW: 0, MEDIUM: 1, HIGH: 2}

# ---------------------------------------------------------------------------
# Pattern catalogue
# ---------------------------------------------------------------------------
# Each entry: (pattern_id, severity, regex_string, flags)
# Ordering within groups is intent-clarifying only.

_PATTERNS: List[Tuple[str, str, str, int]] = [
    # -- system-reminder spoofing ------------------------------------------
    # Framework-specific tags that must never appear in upstream content.
    # Widened per ADR-077/083 to catch bypass variants.
    (
        "system_reminder_spoof",
        HIGH,
        r"<\s*system[-_ ]?reminder\s*>",
        re.IGNORECASE,
    ),
    (
        "system_reminder_spoof",
        HIGH,
        r"<\s*/\s*system[-_ ]?reminder\s*>",
        re.IGNORECASE,
    ),
    (
        "system_reminder_spoof",
        HIGH,
        r"\[SYSTEM\s+REMINDER\]",
        re.IGNORECASE,
    ),
    (
        "system_reminder_spoof",
        HIGH,
        r"\[IMPORTANT\s+NOTICE\]",
        re.IGNORECASE,
    ),
    # Provider chat-template tokens
    (
        "system_reminder_spoof",
        HIGH,
        r"<\|im_start\|>",
        0,
    ),
    (
        "system_reminder_spoof",
        HIGH,
        r"<\|im_end\|>",
        0,
    ),
    (
        "system_reminder_spoof",
        HIGH,
        r"<\|start_header_id\|>",
        0,
    ),
    (
        "system_reminder_spoof",
        HIGH,
        r"\[INST\]",
        0,
    ),
    (
        "system_reminder_spoof",
        HIGH,
        r"\[/INST\]",
        0,
    ),
    # -- role-flip attacks --------------------------------------------------
    (
        "role_flip",
        HIGH,
        r"\bIgnore\s+(?:(?:all|the|any|your|all\s+the)\s+)?previous\s+(?:instructions|messages|directives|context)\b",
        re.IGNORECASE,
    ),
    (
        "role_flip",
        HIGH,
        r"\bDisregard\s+(?:(?:all|the|any|your)\s+)?(?:previous|prior|above|earlier|the\s+system)\b",
        re.IGNORECASE,
    ),
    (
        "role_flip",
        HIGH,
        r"\bForget\s+(?:(?:all|your|the)\s+)?(?:previous|prior|earlier|training|instructions)\b",
        re.IGNORECASE,
    ),
    (
        "role_flip",
        HIGH,
        r"\bYou\s+are\s+now\b",
        re.IGNORECASE,
    ),
    (
        "role_flip",
        HIGH,
        r"\bAct\s+as\s+(?:a\s+)?(?:new|different|unrestricted|jailbreak)",
        re.IGNORECASE,
    ),
    (
        "role_flip",
        HIGH,
        r"\bPretend\s+(?:you\s+are|to\s+be)\b",
        re.IGNORECASE,
    ),
    (
        "role_flip",
        HIGH,
        r"\bOverride\s+(?:(?:the|a|any|your)\s+)?(?:system|default|safety)\b",
        re.IGNORECASE,
    ),
    # -- tool spoofing ------------------------------------------------------
    # Fenced blocks that claim to be tool_result or claude_code output
    (
        "tool_spoof",
        HIGH,
        r"```\s*tool_result",
        re.IGNORECASE,
    ),
    (
        "tool_spoof",
        HIGH,
        r"```\s*claude_code",
        re.IGNORECASE,
    ),
    (
        "tool_spoof",
        HIGH,
        r"```\s*function_call",
        re.IGNORECASE,
    ),
    (
        "tool_spoof",
        HIGH,
        r"<\s*tool[-_ ]?use[-_ ]?id\s*>",
        re.IGNORECASE,
    ),
    (
        "tool_spoof",
        HIGH,
        r"<\s*tool[-_ ]?result\s*>",
        re.IGNORECASE,
    ),
    # -- exfiltration markers ----------------------------------------------
    (
        "exfiltration",
        HIGH,
        r"\bsend\s+(?:credentials?|passwords?|tokens?|secrets?|keys?)\s+to\b",
        re.IGNORECASE,
    ),
    (
        "exfiltration",
        HIGH,
        r"\b(?:POST|curl)\s+.*https?://(?!(?:github\.com|anthropic\.com|claude\.ai))",
        re.IGNORECASE,
    ),
    (
        "exfiltration",
        HIGH,
        r"\becho\s+\$(?:AWS_|OPENAI_|ANTHROPIC_|API_KEY|SECRET|TOKEN|PASSWORD)",
        re.IGNORECASE,
    ),
    (
        "exfiltration",
        HIGH,
        r"\bcat\s+~/\.ssh/",
        re.IGNORECASE,
    ),
    (
        "exfiltration",
        HIGH,
        r"\b(?:leak|exfiltrate|steal|harvest)\s+(?:credentials?|data|tokens?|secrets?|keys?|passwords?)\b",
        re.IGNORECASE,
    ),
    (
        "exfiltration",
        HIGH,
        r"\bcat\s+~/\.(?:aws|env|bashrc|zshrc|profile|netrc)\b",
        re.IGNORECASE,
    ),
    # -- HTML/JS injection -------------------------------------------------
    (
        "script_inject",
        HIGH,
        r"<\s*script[\s>]",
        re.IGNORECASE,
    ),
    (
        "script_inject",
        HIGH,
        r"<\s*/\s*script\s*>",
        re.IGNORECASE,
    ),
    (
        "script_inject",
        HIGH,
        r"<\s*iframe[\s>]",
        re.IGNORECASE,
    ),
    (
        "script_inject",
        HIGH,
        r"javascript\s*:",
        re.IGNORECASE,
    ),
    # -- base64 payload (long strings outside code fences) -----------------
    # Flagged at MEDIUM — long base64 in prose context is suspicious.
    # We detect conservatively: ≥64 contiguous base64-alphabet chars.
    (
        "base64_payload",
        MEDIUM,
        r"(?<![`\w])[A-Za-z0-9+/]{64,}={0,2}(?![`\w])",
        0,
    ),
    # -- prompt leakage ----------------------------------------------------
    (
        "prompt_leakage",
        LOW,
        r"\byour\s+system\s+prompt\b",
        re.IGNORECASE,
    ),
    (
        "prompt_leakage",
        LOW,
        r"\byour\s+instructions\s+are\b",
        re.IGNORECASE,
    ),
    (
        "prompt_leakage",
        LOW,
        r"\bshow\s+me\s+(?:your\s+)?(?:the\s+)?(?:system\s+)?prompt\b",
        re.IGNORECASE,
    ),
    (
        "prompt_leakage",
        LOW,
        r"\bprint\s+(?:your\s+)?(?:full\s+)?system\s+prompt\b",
        re.IGNORECASE,
    ),
    (
        "prompt_leakage",
        LOW,
        r"\brepeat\s+(?:your\s+)?(?:initial\s+)?instructions\b",
        re.IGNORECASE,
    ),
]


# ---------------------------------------------------------------------------
# Compiled pattern cache
# ---------------------------------------------------------------------------

_COMPILED: Optional[
    List[Tuple[str, str, re.Pattern[str]]]  # (pattern_id, severity, compiled)
] = None


def _get_compiled() -> List[Tuple[str, str, re.Pattern[str]]]:
    global _COMPILED
    if _COMPILED is None:
        out: List[Tuple[str, str, re.Pattern[str]]] = []
        for pid, sev, pat, flags in _PATTERNS:
            try:
                out.append((pid, sev, re.compile(pat, flags)))
            except re.error:
                continue
        _COMPILED = out
    return _COMPILED


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Finding:
    severity: str
    path: str
    line: int
    pattern_id: str
    preview: str  # ≤80 chars, non-printable replaced with ␣


@dataclass
class ScanStats:
    files_scanned: int = 0
    total_bytes: int = 0
    findings: List[Finding] = field(default_factory=list)
    counts: Dict[str, int] = field(default_factory=lambda: {HIGH: 0, MEDIUM: 0, LOW: 0})


# ---------------------------------------------------------------------------
# Core scanning functions
# ---------------------------------------------------------------------------

_MAX_FILE_BYTES = 512 * 1024  # 512 KiB per file


def _clean_preview(text: str, max_len: int = 80) -> str:
    """Replace non-printable chars (except space) with ␣ and truncate."""
    out: List[str] = []
    for ch in text[:max_len]:
        if ch == "\n" or ch == "\r" or ch == "\t":
            out.append("␣")
        elif ch.isprintable():
            out.append(ch)
        else:
            out.append("␣")
    result = "".join(out)
    if len(text) > max_len:
        result = result[: max_len - 1] + "…"
    return result


def _make_preview(line_text: str, match_start: int, match_end: int) -> str:
    """Build an ≤80 char preview centred on the match within the line."""
    radius = 30
    a = max(0, match_start - radius)
    b = min(len(line_text), match_end + radius)
    snippet = line_text[a:b]
    if a > 0:
        snippet = "…" + snippet
    if b < len(line_text):
        snippet = snippet + "…"
    return _clean_preview(snippet, 80)


def _is_in_code_fence(lines: List[str], line_idx: int) -> bool:
    """Return True if line_idx is inside a fenced code block (``` or ~~~)."""
    fence_count = 0
    for i, ln in enumerate(lines):
        if i >= line_idx:
            break
        stripped = ln.strip()
        if stripped.startswith("```") or stripped.startswith("~~~"):
            fence_count += 1
    # Odd count = inside a fence
    return fence_count % 2 == 1


def scan_file(
    path: Path,
    root: Path,
    compiled: List[Tuple[str, str, re.Pattern[str]]],
    severity_floor: str,
) -> List[Finding]:
    """Scan a single file; return list of Finding objects."""
    findings: List[Finding] = []
    try:
        raw = path.read_bytes()
    except OSError:
        return findings

    if len(raw) > _MAX_FILE_BYTES:
        raw = raw[:_MAX_FILE_BYTES]

    try:
        text = raw.decode("utf-8", errors="replace")
    except Exception:
        return findings

    rel_path = str(path.relative_to(root))
    lines = text.splitlines()
    floor_val = _SEVERITY_ORDER[severity_floor]

    # Build a per-line offset map for O(1) line-number lookup from char offset
    offsets: List[int] = []
    pos = 0
    for ln in lines:
        offsets.append(pos)
        pos += len(ln) + 1  # +1 for newline

    def _char_to_line(char_offset: int) -> Tuple[int, int]:
        """Return (line_number_1based, col_offset_0based)."""
        lo, hi = 0, len(offsets) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if offsets[mid] <= char_offset:
                lo = mid
            else:
                hi = mid - 1
        col = char_offset - offsets[lo]
        return lo + 1, col  # 1-based line

    # Homoglyph scan: detect if NFKC normalization changes any line
    for line_idx, ln in enumerate(lines):
        normalized = unicodedata.normalize("NFKC", ln)
        if normalized != ln:
            if _SEVERITY_ORDER[MEDIUM] >= floor_val:
                preview = _clean_preview(ln[:80])
                findings.append(
                    Finding(
                        severity=MEDIUM,
                        path=rel_path,
                        line=line_idx + 1,
                        pattern_id="homoglyph",
                        preview=preview,
                    )
                )

    # Regex-pattern scan
    for pid, sev, cpat in compiled:
        if _SEVERITY_ORDER[sev] < floor_val:
            continue
        for m in cpat.finditer(text):
            line_no, col = _char_to_line(m.start())
            line_idx = line_no - 1

            # For base64_payload: skip matches inside code fences
            if pid == "base64_payload":
                if line_idx < len(lines) and _is_in_code_fence(lines, line_idx):
                    continue

            line_text = lines[line_idx] if line_idx < len(lines) else ""
            # Compute match position within the line
            line_start_offset = offsets[line_idx] if line_idx < len(offsets) else 0
            m_start_in_line = m.start() - line_start_offset
            m_end_in_line = m.end() - line_start_offset
            preview = _make_preview(line_text, m_start_in_line, m_end_in_line)
            findings.append(
                Finding(
                    severity=sev,
                    path=rel_path,
                    line=line_no,
                    pattern_id=pid,
                    preview=preview,
                )
            )

    return findings


def scan_directory(
    root: Path,
    severity_floor: str = LOW,
) -> ScanStats:
    """Walk root and scan all .md files."""
    stats = ScanStats()
    compiled = _get_compiled()

    md_files = sorted(root.rglob("*.md"))
    for fpath in md_files:
        stats.files_scanned += 1
        try:
            stats.total_bytes += fpath.stat().st_size
        except OSError:
            pass
        file_findings = scan_file(fpath, root, compiled, severity_floor)
        for f in file_findings:
            stats.findings.append(f)
            stats.counts[f.severity] = stats.counts.get(f.severity, 0) + 1

    return stats


# ---------------------------------------------------------------------------
# Report builder
# ---------------------------------------------------------------------------

def build_report(root: Path, stats: ScanStats, severity_floor: str) -> str:
    """Build the markdown report."""
    import datetime

    date_str = datetime.date.today().isoformat()
    sha_str = "783f6a72bfd7f3135700ac273c619d92821b419a"

    high_findings = [f for f in stats.findings if f.severity == HIGH]
    medium_findings = [f for f in stats.findings if f.severity == MEDIUM]
    low_findings = [f for f in stats.findings if f.severity == LOW]

    lines: List[str] = [
        "# PLAN-074 Wave 0 — Upstream injection scan",
        "",
        f"**Date:** {date_str}",
        f"**Target:** msitarzewski/agency-agents @ {sha_str}",
        f"**Scanner:** .claude/scripts/scan-upstream-injection.py",
        f"**Files scanned:** {stats.files_scanned}",
        f"**Total bytes:** {stats.total_bytes:,}",
        f"**Severity floor:** {severity_floor}",
        "",
        "## Summary",
        "",
        "| Severity | Count |",
        "|---|---|",
        f"| HIGH | {stats.counts.get(HIGH, 0)} |",
        f"| MEDIUM | {stats.counts.get(MEDIUM, 0)} |",
        f"| LOW | {stats.counts.get(LOW, 0)} |",
        "",
        "## HIGH findings",
        "",
    ]

    if not high_findings:
        lines.append("None — clean.")
    else:
        for f in high_findings:
            lines.append(
                f"- `{f.path}:{f.line}` **{f.pattern_id}** — `{f.preview}`"
            )
    lines.append("")

    lines.append("## MEDIUM findings")
    lines.append("")
    if not medium_findings:
        lines.append("None — clean.")
    else:
        # Group by pattern_id for readability
        by_pid: Dict[str, List[Finding]] = {}
        for f in medium_findings:
            by_pid.setdefault(f.pattern_id, []).append(f)
        for pid, flist in sorted(by_pid.items()):
            lines.append(f"### {pid} ({len(flist)} finding(s))")
            lines.append("")
            for f in flist[:20]:
                lines.append(
                    f"- `{f.path}:{f.line}` — `{f.preview}`"
                )
            if len(flist) > 20:
                lines.append(f"- … and {len(flist) - 20} more (omitted for brevity)")
            lines.append("")

    lines.append("## LOW findings")
    lines.append("")
    if not low_findings:
        lines.append("None — clean.")
    else:
        by_pid_low: Dict[str, List[Finding]] = {}
        for f in low_findings:
            by_pid_low.setdefault(f.pattern_id, []).append(f)
        total_low = len(low_findings)
        lines.append(f"Total: {total_low} LOW finding(s) across {len(by_pid_low)} pattern(s).")
        lines.append("")
        for pid, flist in sorted(by_pid_low.items()):
            lines.append(f"**{pid}** ({len(flist)}): sample — `{flist[0].path}:{flist[0].line}` `{flist[0].preview}`")
        lines.append("")

    lines.append("## Disposition")
    lines.append("")
    high_count = stats.counts.get(HIGH, 0)
    med_count = stats.counts.get(MEDIUM, 0)
    if high_count == 0:
        lines.append(
            "No HIGH findings detected. The upstream repo (`msitarzewski/agency-agents` "
            f"@ `{sha_str[:8]}`) is **structurally safe for inspiration**. "
            "Skills derived from this corpus do not require individual injection review "
            "beyond the standard PLAN-074 Pass-2 quality gate."
        )
    else:
        lines.append(
            f"**{high_count} HIGH finding(s) detected.** Each inspired skill drawn from "
            "a file with a HIGH finding MUST undergo explicit injection review during the "
            "relevant Wave before merge. Reviewer agent must confirm the pattern was "
            "contextual (e.g. documentation example) and not adversarial before the skill "
            "is promoted to canonical."
        )
    if med_count > 0:
        lines.append("")
        lines.append(
            f"**{med_count} MEDIUM finding(s)** (base64 payloads or homoglyphs). "
            "These are advisory — verify individually if the source file is selected "
            "as inspiration. Most are likely legitimate base64 in code examples."
        )
    lines.append("")
    lines.append(
        "_Scan produced by `.claude/scripts/scan-upstream-injection.py` "
        "(PLAN-074 Wave 0, ADR-077 + ADR-083 pattern catalogue)._"
    )

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="PLAN-074 Wave 0 upstream injection scanner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("root_dir", help="Directory to scan (recursively for .md files)")
    parser.add_argument(
        "--out",
        default=None,
        help="Write report to this file instead of stdout",
    )
    parser.add_argument(
        "--severity-floor",
        choices=["LOW", "MEDIUM", "HIGH"],
        default="LOW",
        help="Minimum severity to include in output (default: LOW)",
    )
    args = parser.parse_args(argv)

    root = Path(args.root_dir).resolve()
    if not root.is_dir():
        print(f"ERROR: {root} is not a directory", file=sys.stderr)
        return 2

    severity_floor = args.severity_floor

    stats = scan_directory(root, severity_floor)
    report = build_report(root, stats, severity_floor)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(report, encoding="utf-8")
        print(
            f"Scan complete: {stats.files_scanned} files, "
            f"{stats.counts.get(HIGH, 0)} HIGH / "
            f"{stats.counts.get(MEDIUM, 0)} MEDIUM / "
            f"{stats.counts.get(LOW, 0)} LOW → {out_path}",
            file=sys.stderr,
        )
    else:
        sys.stdout.write(report)

    # Exit 1 if any HIGH findings
    return 1 if stats.counts.get(HIGH, 0) > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
