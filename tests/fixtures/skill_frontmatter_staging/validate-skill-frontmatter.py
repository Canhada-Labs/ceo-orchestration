#!/usr/bin/env python3
"""
validate-skill-frontmatter.py — Wave 0 frontmatter validators for PLAN-074.

Three validators:
  V1 — inspired_by: completeness + format + archive path check (ADJ-B4 / Codex P1-01 + P1-02)
  V2 — runtime_mechanism: false REQUIRED (explicit) for docs/playbooks/ (ADJ-F2 / Codex P2-02)
  V3 — PII inheritance enforcement for sensitive domains (ADJ-C4)

Usage (called from validate-governance.sh or check-skill-health.sh):
  python3 .claude/scripts/validate-skill-frontmatter.py --v1 <SKILL.md>
  python3 .claude/scripts/validate-skill-frontmatter.py --v2 <playbook.md>
  python3 .claude/scripts/validate-skill-frontmatter.py --v3 <SKILL.md> [--domain <name>]
  python3 .claude/scripts/validate-skill-frontmatter.py --all <file> [--domain <name>]

Optional (V1 archive path check):
  --archive-index <path>  Path to upstream-archive-index.txt (generated from archive .tar.zst).
                          If omitted, archive path check is SKIPPED (warn only).

Exit codes:
  0   PASS (or WARN-only result — no errors)
  1   ERROR (at least one violation)
  2   Usage / argument error

Note: After Wave 0 ceremony, this file is promoted from
  .claude/plans/PLAN-074/staging/validate-skill-frontmatter.py
to
  .claude/scripts/validate-skill-frontmatter.py
"""
from __future__ import annotations

import re
import sys
import os
import argparse
from typing import Optional, Set

# ---------------------------------------------------------------------------
# Minimal YAML frontmatter parser (stdlib only — no PyYAML dependency)
# ---------------------------------------------------------------------------

def _parse_frontmatter(text: str) -> Optional[dict]:
    """
    Parse YAML-style frontmatter delimited by '---' lines.
    Returns a flat dict of top-level string/list/dict values.
    Handles simple scalar values, quoted strings, inline lists, and nested blocks.
    Returns None if no frontmatter found.
    """
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    end = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end = i
            break
    if end is None:
        return None
    fm_lines = lines[1:end]
    return _parse_yaml_block(fm_lines)


def _detect_indent(lines: list) -> int:
    """Return the minimum indentation of non-blank lines."""
    min_ind = 9999
    for line in lines:
        stripped = line.rstrip()
        if stripped and not stripped.lstrip().startswith("#"):
            ind = len(stripped) - len(stripped.lstrip())
            if ind < min_ind:
                min_ind = ind
    return min_ind if min_ind < 9999 else 0


def _parse_yaml_sequence(lines: list, item_indent: int) -> list:
    """
    Parse a YAML block sequence (lines starting with '- ' at item_indent).
    Each item may be a scalar or a nested mapping.
    """
    items: list = []
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        if not line:
            i += 1
            continue
        leading = len(line) - len(line.lstrip())
        if leading < item_indent:
            break  # Back to parent level
        lstripped = line.lstrip()
        if leading == item_indent and lstripped.startswith("- "):
            # New list item
            rest = lstripped[2:].strip()
            if not rest:
                # Block item — collect child lines
                child_lines: list = []
                i += 1
                while i < len(lines):
                    cl = lines[i].rstrip()
                    if not cl:
                        i += 1
                        continue
                    cl_ind = len(cl) - len(cl.lstrip())
                    if cl_ind <= item_indent:
                        break
                    child_lines.append(cl)
                    i += 1
                if child_lines:
                    child_ind = _detect_indent(child_lines)
                    items.append(_parse_yaml_block(child_lines, child_ind))
                else:
                    items.append(None)
            elif ":" in rest:
                # Inline key: val for first field, rest are children
                child_lines_2: list = [" " * (item_indent + 2) + rest]
                i += 1
                while i < len(lines):
                    cl = lines[i].rstrip()
                    if not cl:
                        i += 1
                        continue
                    cl_ind = len(cl) - len(cl.lstrip())
                    if cl_ind <= item_indent:
                        break
                    child_lines_2.append(cl)
                    i += 1
                child_ind2 = _detect_indent(child_lines_2)
                items.append(_parse_yaml_block(child_lines_2, child_ind2))
            else:
                items.append(rest.strip("\"'"))
                i += 1
        else:
            i += 1
    return items


def _parse_yaml_block(lines: list, indent: int = 0) -> dict:
    """Parse a simple YAML block (non-recursive for top-level keys only)."""
    result: dict = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.rstrip()
        if not stripped or stripped.lstrip().startswith("#"):
            i += 1
            continue
        leading = len(stripped) - len(stripped.lstrip())
        if leading < indent:
            # Dedent past our block — stop
            break
        if leading > indent:
            # Deeper line at unexpected indent — skip (child already consumed)
            i += 1
            continue
        lstripped = stripped.lstrip()
        if ":" not in lstripped:
            i += 1
            continue
        colon_pos = lstripped.index(":")
        key = lstripped[:colon_pos].strip()
        rest = lstripped[colon_pos + 1:].strip()

        if rest == "" or rest == "|" or rest == ">":
            # Peek at children to see if it's a sequence or mapping
            children: list = []
            i += 1
            child_indent: Optional[int] = None
            while i < len(lines):
                child_line = lines[i].rstrip()
                if not child_line:
                    children.append(child_line)
                    i += 1
                    continue
                cl = len(child_line) - len(child_line.lstrip())
                if child_indent is None and child_line.lstrip():
                    child_indent = cl
                if child_indent is not None and cl < child_indent:
                    break
                children.append(child_line)
                i += 1
            if not children:
                result[key] = None
            else:
                eff_indent = child_indent if child_indent is not None else (indent + 2)
                # Detect sequence vs mapping
                first_content = next((l.lstrip() for l in children if l.strip()), "")
                if first_content.startswith("- "):
                    result[key] = _parse_yaml_sequence(children, eff_indent)
                else:
                    nested = _parse_yaml_block(children, eff_indent)
                    result[key] = nested if nested else children
        elif rest.startswith("[") and rest.endswith("]"):
            inner = rest[1:-1]
            items = [item.strip().strip("'\"") for item in inner.split(",") if item.strip()]
            result[key] = items
            i += 1
        else:
            val = rest.strip("\"'")
            result[key] = val
            i += 1

    return result


def _get_nested(fm: dict, *keys) -> Optional[object]:
    """Navigate nested dict; return None if any key missing."""
    cur: object = fm
    for k in keys:
        if not isinstance(cur, dict):
            return None
        cur = cur.get(k)  # type: ignore[assignment]
    return cur


# ---------------------------------------------------------------------------
# V1 — inspired_by: validator (ADJ-B4 / Codex P1-01 + P1-02)
# ---------------------------------------------------------------------------

# 7-value canonical allowlist (ADR-060 §Frontmatter validator, Codex P1-01 hardening)
# Meanings:
#   structural_inspiration  — overall structure / section layout borrowed
#   partial_reuse           — small code samples or tables reused with adaptation
#   topic_only              — topic/domain acknowledged; no structural carry-over
#   deliverable_template    — output format / deliverable template adapted
#   severity_scale          — severity/classification scale (industry-standard, e.g. SEV1-4)
#   convention              — single conventional primitive (header format, token, etc.)
#   pattern_reference       — architectural/design pattern referenced by name only
ALLOWED_RELATIONSHIPS = {
    "structural_inspiration",
    "partial_reuse",
    "topic_only",
    "deliverable_template",
    "severity_scale",
    "convention",
    "pattern_reference",
}

# source: field format: <owner>/<repo>/<path>@<40-hex-sha>
# The path portion is everything between the second '/' and the '@'
SOURCE_RE = re.compile(
    r"^[a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+/([^@]+)@[a-f0-9]{40}$"
)

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _load_archive_index(archive_index_path: str) -> Optional[Set[str]]:
    """
    Load the upstream archive index file.
    Returns a set of normalised paths (without leading './' prefix).
    Returns None if the file cannot be read (non-fatal — archive check skipped).
    """
    try:
        with open(archive_index_path, encoding="utf-8", errors="replace") as fh:
            paths: Set[str] = set()
            for line in fh:
                p = line.strip()
                if p.startswith("./"):
                    p = p[2:]
                if p:
                    paths.add(p)
        return paths
    except OSError:
        return None


def _extract_source_path(source: str) -> Optional[str]:
    """
    Extract the path portion from a source: field value.
    Format: <owner>/<repo>/<path>@<40-hex-sha>
    Returns the <path> substring (everything between 2nd '/' and '@').
    Example:
      "msitarzewski/agency-agents/engineering/engineering-threat-detection-engineer.md@abc...def"
      -> "engineering/engineering-threat-detection-engineer.md"
    """
    m = SOURCE_RE.match(source)
    if not m:
        return None
    return m.group(1)


def validate_v1(
    filepath: str,
    fm: dict,
    archive_index: Optional[Set[str]] = None,
) -> list:
    """
    V1 — inspired_by: validator.

    Checks (Codex P1-01):
    - Each entry MUST contain: source, license, relationship, authored_by, authored_at
    - authored_by / authored_at MUST be INSIDE each entry (per-entry, not top-level)
    - relationship MUST be one of the 7-value canonical allowlist
    - authored_at MUST be ISO YYYY-MM-DD

    Checks (Codex P1-02 — archive path validation):
    - source: path portion MUST exist in archive_index (if index provided)
    - If archive_index is None (not supplied), path check is SKIPPED (WARN emitted)

    Returns list of ERROR strings (empty = PASS).
    WARNINGs are prefixed with 'V1 WARN' and do not affect exit code.
    """
    errors: list = []
    raw = fm.get("inspired_by")
    if raw is None:
        # No inspired_by key — V1 does not apply
        return errors

    # Detect if authored_by / authored_at appear at TOP LEVEL of frontmatter
    # (P1-01 schema violation: they must be inside each inspired_by entry)
    if "authored_by" in fm:
        errors.append(
            f"V1 ERROR [{filepath}]: 'authored_by' found at frontmatter top level — "
            "it must be inside each 'inspired_by' entry (Codex P1-01: per-entry attribution)"
        )
    if "authored_at" in fm:
        errors.append(
            f"V1 ERROR [{filepath}]: 'authored_at' found at frontmatter top level — "
            "it must be inside each 'inspired_by' entry (Codex P1-01: per-entry attribution)"
        )

    # inspired_by may be a list of dicts or a single dict
    entries: list = []
    if isinstance(raw, list):
        entries = raw
    elif isinstance(raw, dict):
        entries = [raw]
    else:
        errors.append(
            f"V1 ERROR [{filepath}]: 'inspired_by' must be a list or mapping, got {type(raw).__name__}"
        )
        return errors

    for idx, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(
                f"V1 ERROR [{filepath}]: 'inspired_by[{idx}]' must be a mapping, got {type(entry).__name__}"
            )
            continue
        # Required per-entry fields (Codex P1-01: authored_by + authored_at inside entry)
        for field in ("source", "license", "relationship", "authored_by", "authored_at"):
            if field not in entry:
                errors.append(
                    f"V1 ERROR [{filepath}]: 'inspired_by[{idx}]' missing required field '{field}'"
                )
        # source format: owner/repo/path@SHA40
        source = entry.get("source", "")
        if source and not SOURCE_RE.match(source):
            errors.append(
                f"V1 ERROR [{filepath}]: 'inspired_by[{idx}].source' must match "
                f"'<owner>/<repo>/<path>@<40hexSHA>' — got: {source!r}"
            )
        # P1-02 — archive path existence check
        if source and SOURCE_RE.match(source):
            path_in_archive = _extract_source_path(source)
            if path_in_archive is not None:
                if archive_index is None:
                    errors.append(
                        f"V1 WARN [{filepath}]: 'inspired_by[{idx}].source' archive index not "
                        f"provided — skipping path existence check for: {path_in_archive!r} "
                        "(pass --archive-index to enable P1-02 validation)"
                    )
                elif path_in_archive not in archive_index:
                    errors.append(
                        f"V1 ERROR [{filepath}]: 'inspired_by[{idx}].source' path not found in "
                        f"archive index — '{path_in_archive}' does not exist in upstream archive "
                        "(Codex P1-02: inspired_by source path not found in archive index)"
                    )
        # relationship allowlist (7-value canonical, Codex P1-01)
        rel = entry.get("relationship", "")
        if rel and rel not in ALLOWED_RELATIONSHIPS:
            errors.append(
                f"V1 ERROR [{filepath}]: 'inspired_by[{idx}].relationship' must be one of "
                f"{sorted(ALLOWED_RELATIONSHIPS)} — got: {rel!r}"
            )
        # authored_at ISO date
        authored_at = entry.get("authored_at", "")
        if authored_at and not DATE_RE.match(str(authored_at)):
            errors.append(
                f"V1 ERROR [{filepath}]: 'inspired_by[{idx}].authored_at' must be ISO date "
                f"YYYY-MM-DD — got: {authored_at!r}"
            )

    return errors


# ---------------------------------------------------------------------------
# V2 — runtime_mechanism: false REQUIRED for docs/playbooks/ (ADJ-F2 / Codex P2-02)
# ---------------------------------------------------------------------------

def validate_v2(filepath: str, fm: dict) -> list:
    """
    V2 — docs/playbooks/ files MUST carry runtime_mechanism: false (explicit).

    Codex P2-02 hardening: key absent is now also an ERROR (not just key=true).
    ADR-060 §Playbook docs lint rule: "MUST carry runtime_mechanism: false".
    The key must be present AND its value must be false.

    Returns list of ERROR strings.
    """
    errors: list = []
    # Only applies to files under docs/playbooks/
    normalized = filepath.replace("\\", "/")
    if "docs/playbooks/" not in normalized:
        return errors

    raw_val = fm.get("runtime_mechanism")

    if raw_val is None:
        # P2-02 strict mode: key ABSENT is now an ERROR
        errors.append(
            f"V2 ERROR [{filepath}]: docs/playbooks/ file is missing required key "
            "'runtime_mechanism: false' — "
            "ADR-060 §Playbook docs lint rule requires explicit "
            "`runtime_mechanism: false` marker (Codex P2-02 hardening). "
            "Add `runtime_mechanism: false` to the frontmatter."
        )
        return errors

    # Normalise: YAML true/false may be parsed as string "true"/"false" or bool
    if isinstance(raw_val, bool):
        is_true = raw_val
    else:
        is_true = str(raw_val).strip().lower() == "true"

    if is_true:
        errors.append(
            f"V2 ERROR [{filepath}]: docs/playbooks/ file has 'runtime_mechanism: true' — "
            "playbooks MUST be docs-only (ADR-060 §Playbook docs lint rule requires explicit "
            "`runtime_mechanism: false` marker, Codex P2-02 hardening). "
            "If runtime elevation is intentional, open a new ADR amendment."
        )
    return errors


# ---------------------------------------------------------------------------
# V3 — PII inheritance enforcement (ADJ-C4)
# ---------------------------------------------------------------------------

# Domains that MUST have PII inheritance (ERROR if missing)
PII_REQUIRED_DOMAINS = {
    "legal",
    "healthcare",
    "real-estate-finance",
    "hr",
    "finance-accounting",
}

# Domains that SHOULD have PII inheritance (WARN if missing)
PII_WARN_DOMAINS = {
    "retail",
    "hospitality",
}


def _extract_domain_from_path(filepath: str) -> Optional[str]:
    """
    Extract domain name from skill path like:
      .claude/skills/domains/<domain>/skills/<skill>/SKILL.md
    Returns None if path doesn't match.
    """
    normalized = filepath.replace("\\", "/")
    m = re.search(r"\.claude/skills/domains/([^/]+)/", normalized)
    if m:
        return m.group(1)
    return None


def _has_inherits_lgpd(fm: dict) -> bool:
    """Check if frontmatter inherits core/compliance-lgpd."""
    inherits = fm.get("inherits")
    if inherits is None:
        return False
    if isinstance(inherits, str):
        return "core/compliance-lgpd" in inherits
    if isinstance(inherits, list):
        return any("core/compliance-lgpd" in str(item) for item in inherits)
    return False


def _has_pii_handling_required(fm: dict) -> bool:
    """Check if frontmatter has pii_handling: required."""
    val = fm.get("pii_handling")
    if val is None:
        return False
    return str(val).strip().lower() == "required"


def validate_v3(
    filepath: str,
    fm: dict,
    domain_override: Optional[str] = None,
) -> tuple:
    """
    V3 — PII inheritance.
    Returns (errors, warnings).
    """
    errors: list = []
    warnings: list = []

    domain = domain_override or _extract_domain_from_path(filepath)
    if domain is None:
        return errors, warnings

    has_lgpd = _has_inherits_lgpd(fm)
    has_pii = _has_pii_handling_required(fm)

    if domain in PII_REQUIRED_DOMAINS:
        if not has_lgpd:
            errors.append(
                f"V3 ERROR [{filepath}]: PII-required domain '{domain}' SKILL.md must have "
                "'inherits: [core/compliance-lgpd]' in frontmatter (ADJ-C4)."
            )
        if not has_pii:
            errors.append(
                f"V3 ERROR [{filepath}]: PII-required domain '{domain}' SKILL.md must have "
                "'pii_handling: required' in frontmatter (ADJ-C4)."
            )
    elif domain in PII_WARN_DOMAINS:
        if not has_lgpd:
            warnings.append(
                f"V3 WARN [{filepath}]: PII-touching domain '{domain}' SKILL.md should have "
                "'inherits: [core/compliance-lgpd]' (lower-risk domain — WARN only, per Sec ADJ-C4)."
            )
        if not has_pii:
            warnings.append(
                f"V3 WARN [{filepath}]: PII-touching domain '{domain}' SKILL.md should have "
                "'pii_handling: required' (lower-risk domain — WARN only, per Sec ADJ-C4)."
            )

    return errors, warnings


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main(argv: list) -> int:
    parser = argparse.ArgumentParser(
        description="validate-skill-frontmatter.py — Wave 0 PLAN-074 validators V1/V2/V3",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("file", help="Path to the file to validate")
    parser.add_argument("--v1", action="store_true", help="Run V1 (inspired_by validator)")
    parser.add_argument("--v2", action="store_true", help="Run V2 (runtime_mechanism lint)")
    parser.add_argument("--v3", action="store_true", help="Run V3 (PII inheritance)")
    parser.add_argument("--all", dest="all_validators", action="store_true", help="Run all validators")
    parser.add_argument("--domain", default=None, help="Override domain name (for V3)")
    parser.add_argument(
        "--archive-index",
        default=None,
        metavar="PATH",
        help=(
            "Path to upstream-archive-index.txt for V1 archive path check (P1-02). "
            "Generate with: zstd -d -c <archive>.tar.zst | tar -tf - | grep '\\.md$' | sort > index.txt. "
            "If omitted, path existence check is skipped (WARN emitted)."
        ),
    )

    args = parser.parse_args(argv)

    filepath = args.file
    if not os.path.isfile(filepath):
        print(f"ERROR: file not found: {filepath}", file=sys.stderr)
        return 2

    with open(filepath, encoding="utf-8", errors="replace") as fh:
        content = fh.read()

    fm = _parse_frontmatter(content)
    if fm is None:
        fm = {}

    run_v1 = args.v1 or args.all_validators
    run_v2 = args.v2 or args.all_validators
    run_v3 = args.v3 or args.all_validators

    if not (run_v1 or run_v2 or run_v3):
        # Default: run all
        run_v1 = run_v2 = run_v3 = True

    # Load archive index for V1 P1-02 check
    archive_index: Optional[Set[str]] = None
    if run_v1 and args.archive_index:
        archive_index = _load_archive_index(args.archive_index)
        if archive_index is None:
            print(
                f"WARN: could not read archive index file: {args.archive_index!r} — "
                "V1 archive path check disabled",
                file=sys.stderr,
            )

    all_errors: list = []
    all_warnings: list = []

    if run_v1:
        v1_results = validate_v1(filepath, fm, archive_index=archive_index)
        # Separate WARNs from ERRORs (V1 uses 'V1 WARN' prefix for non-fatal)
        for msg in v1_results:
            if msg.startswith("V1 WARN"):
                all_warnings.append(msg)
            else:
                all_errors.append(msg)

    if run_v2:
        all_errors.extend(validate_v2(filepath, fm))

    if run_v3:
        errs, warns = validate_v3(filepath, fm, domain_override=args.domain)
        all_errors.extend(errs)
        all_warnings.extend(warns)

    for w in all_warnings:
        print(w)

    for e in all_errors:
        print(e)

    return 1 if all_errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
