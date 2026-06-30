#!/usr/bin/env python3
"""skill-import-rubric — validate a candidate skill for import.

PLAN-033 Wave B deliverable. Stdlib-only CLI that enforces the
framework's curation rubric on any SKILL.md sourced from an external
corpus (e.g. `antigravity-awesome-skills`, community submissions) before
the Owner signs off on an SP-NNN chain.

The rubric is deliberately strict: most upstream skills fail. That is
the point — we prefer 20 well-curated skills over 200 noise-level ones
(PLAN-026 audit finding 08, ultimate-guide rubric).

Usage::

    skill-import-rubric.py <path-to-SKILL.md>              # validate one
    skill-import-rubric.py --dir <path>                    # validate all SKILL.md under dir
    skill-import-rubric.py --json <path>                   # machine-readable output
    skill-import-rubric.py --strict --dir <path>           # exit non-zero on any fail

Rubric (all must pass):

    R1. File at path named SKILL.md.
    R2. Non-whitespace size >= 512 bytes (matches canonical skill floor).
    R3. Valid YAML frontmatter between leading `---` fences with:
        - `name:` key (non-empty string)
        - `description:` key (non-empty string)
    R4. At least one ``## `` heading OR one ``###`` sub-heading.
    R5. At least one checklist-like block — a markdown list whose items
        begin with ``- [`` (checkbox items) OR a ``## Checklist`` /
        ``## Checks`` section followed by at least 3 list items.
    R6. No forbidden patterns (offensive-security keywords) in the
        body. Kept narrow — false positives are fine for curation
        (Owner decides case-by-case on the residual). Extendable via
        the ``--forbidden-extra`` flag.
    R7. No UTF-8 BOM. No bidi-override / tag characters in headings
        or body (safety — LLM01 hardening).

Exit codes::

    0 — all passed (or no files found and --strict not set)
    1 — at least one failure (and --strict set, or single-file mode)
    2 — CLI / IO error

Rubric version: 1.  Bump + update tests if any rule changes.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

RUBRIC_VERSION = 1
MIN_NONWS_BYTES = 512

# Forbidden-keyword first-pass filter. Not comprehensive — curation
# is Owner-gated; this catches the most obvious offensive-security
# pastes at rubric time. PLAN-045 F-01-12 expansion: 8 → 24 entries.
# Additions case-by-case; keep phrases specific (e.g. "phishing
# campaign" not bare "phishing" — security skills legitimately
# discuss threat models).
_DEFAULT_FORBIDDEN = (
    # Offensive operations
    "phishing campaign",
    "credential harvesting tutorial",
    "malware development",
    "exploit kit",
    "ransomware tutorial",
    "rootkit development",
    "keylogger tutorial",
    "ddos attack tutorial",
    "crypter builder",
    "c2 infrastructure setup",
    # Jailbreak patterns
    "jailbreak claude",
    "jailbreak gpt",
    "dan prompt",
    "bypass ai safety",
    # Authentication bypass
    "how to bypass authentication",
    "bypass 2fa",
    "crack password hash",
    "session hijack tutorial",
    # Data exfiltration
    "steal cookies tutorial",
    "dump database credentials",
    # Supply-chain attack
    "typosquatting guide",
    "dependency confusion attack",
    # Spam / illicit commerce
    "buy stolen credentials",
    "sell exploit 0day",
)

# LLM01 hardening — these code points never appear in a legit skill.
_BIDI_MARKS = [
    "\u202a", "\u202b", "\u202c", "\u202d", "\u202e",
    "\u2066", "\u2067", "\u2068", "\u2069",
]
_ZERO_WIDTH = ["\u200b", "\u200c", "\u200d", "\u2060", "\ufeff"]

_FRONTMATTER_RE = re.compile(
    r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL | re.MULTILINE
)
_CHECKBOX_RE = re.compile(r"^\s*-\s*\[( |x|X)\]\s", re.MULTILINE)
_LIST_ITEM_RE = re.compile(r"^\s*-\s+\S", re.MULTILINE)
_HEADING_RE = re.compile(r"^#{1,3}\s+\S", re.MULTILINE)


@dataclass
class RubricFinding:
    rule: str
    ok: bool
    detail: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain-dict view for JSON serialization."""
        return {"rule": self.rule, "ok": self.ok, "detail": self.detail}


@dataclass
class RubricResult:
    path: Path
    findings: List[RubricFinding] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """True iff every rubric rule is marked ``ok``."""
        return all(f.ok for f in self.findings)

    def to_dict(self) -> Dict[str, Any]:
        """Return a plain-dict view (path + pass/fail + rubric version + findings)."""
        return {
            "path": str(self.path),
            "passed": self.passed,
            "rubric_version": RUBRIC_VERSION,
            "findings": [f.to_dict() for f in self.findings],
        }


# ---------------------------------------------------------------------------
# Individual rules
# ---------------------------------------------------------------------------


def _rule_r1_filename(path: Path) -> RubricFinding:
    ok = path.name == "SKILL.md"
    return RubricFinding("R1", ok, "" if ok else f"filename != SKILL.md: {path.name}")


def _rule_r2_nonws_bytes(content: str) -> RubricFinding:
    nonws = re.sub(r"\s", "", content)
    size = len(nonws.encode("utf-8"))
    ok = size >= MIN_NONWS_BYTES
    return RubricFinding(
        "R2",
        ok,
        "" if ok else f"non-ws size {size} < {MIN_NONWS_BYTES}",
    )


def _rule_r3_frontmatter(content: str) -> RubricFinding:
    m = _FRONTMATTER_RE.match(content)
    if not m:
        return RubricFinding("R3", False, "no leading `---` fenced frontmatter")
    yaml_body = m.group(1)
    # Parse minimal YAML — we only need `name` + `description`. Use
    # `[ \t]` instead of `\s` for mid-line whitespace so the regex does
    # NOT cross newline boundaries and accidentally consume the next
    # YAML key as the value (caught by the R3 empty-name test).
    name_match = re.search(
        r"^[ \t]*name:[ \t]*(.*?)[ \t]*$", yaml_body, re.MULTILINE
    )
    desc_match = re.search(
        r"^[ \t]*description:[ \t]*(.*?)[ \t]*$", yaml_body, re.MULTILINE
    )
    if not name_match or not name_match.group(1).strip():
        return RubricFinding("R3", False, "missing / empty `name:`")
    if not desc_match or not desc_match.group(1).strip().strip('"').strip("'"):
        return RubricFinding("R3", False, "missing / empty `description:`")
    return RubricFinding("R3", True, "")


def _rule_r4_has_headings(content: str) -> RubricFinding:
    ok = bool(_HEADING_RE.search(content))
    return RubricFinding("R4", ok, "" if ok else "no `##` / `###` headings found")


def _rule_r5_checklist(content: str) -> RubricFinding:
    # Either: ≥1 checkbox-style item, OR a `## Checklist|Checks|Rules`
    # section followed by ≥3 plain list items.
    if _CHECKBOX_RE.search(content):
        return RubricFinding("R5", True, "checkbox items present")
    # Look for a checklist section header
    m = re.search(
        r"^#{1,3}\s+(Checklist|Checks|Rules|Review checklist)\b",
        content,
        re.MULTILINE | re.IGNORECASE,
    )
    if m:
        section_start = m.end()
        # Take next 60 lines as the section slice
        next_heading = re.search(r"^#{1,3}\s+\S", content[section_start:], re.MULTILINE)
        section_end = (
            section_start + (next_heading.start() if next_heading else len(content))
        )
        section = content[section_start:section_end]
        items = _LIST_ITEM_RE.findall(section)
        if len(items) >= 3:
            return RubricFinding(
                "R5",
                True,
                f"checklist section with {len(items)} items",
            )
    return RubricFinding(
        "R5", False, "no checkbox items AND no Checklist / Checks section with ≥3 items"
    )


def _rule_r6_no_forbidden(
    content: str, forbidden_extra: Optional[List[str]] = None
) -> RubricFinding:
    body = content.lower()
    forbidden = list(_DEFAULT_FORBIDDEN)
    if forbidden_extra:
        forbidden.extend(s.lower() for s in forbidden_extra)
    hits = [kw for kw in forbidden if kw.lower() in body]
    if hits:
        return RubricFinding(
            "R6",
            False,
            f"forbidden keyword(s) present: {', '.join(hits[:3])}",
        )
    return RubricFinding("R6", True, "")


def _rule_r7_no_bidi_no_bom(content: str) -> RubricFinding:
    if content.startswith("\ufeff"):
        return RubricFinding("R7", False, "leading UTF-8 BOM")
    for mark in _BIDI_MARKS + _ZERO_WIDTH:
        if mark in content:
            return RubricFinding(
                "R7",
                False,
                f"bidi / zero-width code point U+{ord(mark):04X} present",
            )
    return RubricFinding("R7", True, "")


def evaluate(
    path: Path,
    forbidden_extra: Optional[List[str]] = None,
) -> RubricResult:
    """Evaluate a single file and return a RubricResult."""
    result = RubricResult(path=path)
    result.findings.append(_rule_r1_filename(path))
    try:
        content = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        result.findings.append(
            RubricFinding("R0", False, f"file not found: {path}")
        )
        return result
    except (OSError, UnicodeDecodeError) as exc:
        result.findings.append(RubricFinding("R0", False, f"read error: {exc}"))
        return result
    result.findings.append(_rule_r2_nonws_bytes(content))
    result.findings.append(_rule_r3_frontmatter(content))
    result.findings.append(_rule_r4_has_headings(content))
    result.findings.append(_rule_r5_checklist(content))
    result.findings.append(_rule_r6_no_forbidden(content, forbidden_extra))
    result.findings.append(_rule_r7_no_bidi_no_bom(content))
    return result


def evaluate_dir(root: Path, forbidden_extra: Optional[List[str]] = None) -> List[RubricResult]:
    """Evaluate every SKILL.md under root recursively."""
    out: List[RubricResult] = []
    for p in sorted(root.rglob("SKILL.md")):
        out.append(evaluate(p, forbidden_extra))
    return out


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _render_text(results: List[RubricResult]) -> str:
    lines: List[str] = []
    for r in results:
        mark = "PASS" if r.passed else "FAIL"
        lines.append(f"[{mark}] {r.path}")
        for f in r.findings:
            if not f.ok:
                lines.append(f"   - {f.rule}: {f.detail}")
    passed = sum(1 for r in results if r.passed)
    lines.append("")
    lines.append(f"Summary: {passed}/{len(results)} passed (rubric v{RUBRIC_VERSION})")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser for the skill-import-rubric CLI."""
    p = argparse.ArgumentParser(
        prog="skill-import-rubric",
        description="Validate a candidate SKILL.md against the curation rubric.",
    )
    g = p.add_mutually_exclusive_group(required=True)
    g.add_argument("path", nargs="?", type=Path, help="Path to a single SKILL.md")
    g.add_argument("--dir", type=Path, help="Validate every SKILL.md under a directory")
    p.add_argument("--json", action="store_true", help="Machine-readable JSON output")
    p.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero if any file fails (default: exit 0 on --dir)",
    )
    p.add_argument(
        "--forbidden-extra",
        action="append",
        default=[],
        metavar="KEYWORD",
        help="Additional forbidden keywords (case-insensitive); may repeat",
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — apply the 7-rule import rubric to a candidate SKILL.md."""
    parser = build_parser()
    args = parser.parse_args(argv)

    forbidden = list(args.forbidden_extra) if args.forbidden_extra else None
    try:
        if args.dir is not None:
            if not args.dir.is_dir():
                print(f"not a directory: {args.dir}", file=sys.stderr)
                return 2
            results = evaluate_dir(args.dir, forbidden)
        else:
            assert args.path is not None
            results = [evaluate(args.path, forbidden)]
    except Exception as exc:  # safety net
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps([r.to_dict() for r in results], indent=2))
    else:
        print(_render_text(results))

    if not results:
        return 0
    any_failed = any(not r.passed for r in results)
    if args.dir is None:
        # single-file mode: non-pass is exit 1
        return 0 if results[0].passed else 1
    # dir mode: strict controls exit code
    if args.strict and any_failed:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
