#!/usr/bin/env python3
"""verify-adr-118-rationale.py — Mechanical verifier for ADR-118 §3 Rationale.

Per PLAN-088 W4.3 / M-27 / Sec-7 / handoff §9.4 / §13 + R2 iter-1 C10 fold:
asserts that ADR-118's §3 SHA-pin Rationale table proves
`capability_surface_delta=0` for every conversion in the canonical 13
(10 AUTO + 3 SEMI, sourced from
`.claude/plans/PLAN-084/automation-gap-roadmap.yaml`).

Mechanical checks performed:

  1. Parses ADR-118 §3 markdown table cleanly.
  2. Verifies the row set matches the canonical 13 (AUTO-01..AUTO-10 +
     SEMI-11/12/13) — neither subset nor superset.
  3. Verifies every row has a non-empty "First-shipped SHA" column
     matching one of:
       - 40 lowercase hex characters
       - 7+ lowercase hex characters (abbreviated git SHA)
       - the literal marker `ANCESTRAL-PRE-PLAN-084`
  4. Verifies every row has a non-empty integer "Trigger-wire LoC"
     column (0 is acceptable; rejects empty / non-numeric).
  5. Verifies "Surface delta" column equals exactly `0` for every row.
  6. Scans the ADR body for anti-pattern keywords that would imply a
     primitive being introduced (`new_capability`, `new primitive`,
     `NEW capability primitive`, etc.); FAIL if any match.

Exit codes:
  0  — all checks pass
  1  — one or more checks fail (specific row/reason printed to stderr)
  2  — input file missing or malformed

Stdlib-only per CLAUDE.md §5 (Python >= 3.9; from __future__ annotations).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple

DEFAULT_ADR_PATH = ".claude/adr/ADR-118-god-mode-auto-usable-state.md"
DEFAULT_ROADMAP_PATH = ".claude/plans/PLAN-084/automation-gap-roadmap.yaml"

# Frozen canonical-13 list (in-line fallback if roadmap YAML is unreadable).
FROZEN_CANONICAL_13: Tuple[str, ...] = (
    "AUTO-01", "AUTO-02", "AUTO-03", "AUTO-04", "AUTO-05",
    "AUTO-06", "AUTO-07", "AUTO-08", "AUTO-09", "AUTO-10",
    "SEMI-11", "SEMI-12", "SEMI-13",
)

RATIONALE_SECTION_HEADER_RE = re.compile(
    r"^##\s*§\s*3\b[^\n]*$", re.MULTILINE
)
NEXT_HEADING_RE = re.compile(r"^#{2,3}\s+", re.MULTILINE)
TABLE_ROW_RE = re.compile(r"^\|(?:[^\n|]*\|){4,}[^\n|]*\|\s*$", re.MULTILINE)

HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
HEX_SHORT_RE = re.compile(r"^[0-9a-f]{7,39}$")
ANCESTRAL_MARKER = "ANCESTRAL-PRE-PLAN-084"

# Anti-pattern keyword set: deliberately conservative. Flags phrasing
# that implies a primitive is being introduced rather than wired.
ANTI_PATTERN_KEYWORDS: Tuple[str, ...] = (
    "new_capability",
    "new primitive",
    "NEW capability primitive",
    "introduce capability",
    "introduces capability",
    "ships new capability",
)

CONVERSION_ID_RE = re.compile(r"^(AUTO-\d{2}|SEMI-\d{2})$")


def _err(msg: str) -> None:
    print(msg, file=sys.stderr)


def _read_text(path: Path) -> Optional[str]:
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        _err("FAIL: cannot read %s: %s" % (path, exc))
        return None


def _load_canonical_13_from_roadmap(roadmap_path: Path) -> List[str]:
    """Parse `priority_conversions:` of the YAML and collect `id:` lines."""
    text = _read_text(roadmap_path)
    if text is None:
        _err("warn: roadmap %s unreadable; using FROZEN_CANONICAL_13" % roadmap_path)
        return list(FROZEN_CANONICAL_13)

    ids: List[str] = []
    for line in text.splitlines():
        m = re.match(r"^\s*-?\s*id:\s*((?:AUTO|SEMI)-\d{2})\s*$", line)
        if m:
            ids.append(m.group(1))
    if len(ids) != 13:
        _err("warn: roadmap parsed %d ids (expected 13); using fallback" % len(ids))
        return list(FROZEN_CANONICAL_13)
    return ids


def _extract_rationale_section(adr_text: str) -> Optional[str]:
    m = RATIONALE_SECTION_HEADER_RE.search(adr_text)
    if m is None:
        _err("FAIL: §3 Rationale section header not found in ADR-118")
        return None
    start = m.end()
    tail = adr_text[start:]
    next_m = NEXT_HEADING_RE.search(tail)
    if next_m is None:
        return tail
    return tail[: next_m.start()]


def _parse_table_rows(section: str) -> List[List[str]]:
    rows: List[List[str]] = []
    for line in TABLE_ROW_RE.findall(section):
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if all(set(c) <= set("-:") and c for c in cells):
            continue
        rows.append(cells)
    return rows


def _check_anti_pattern_keywords(adr_text: str) -> List[str]:
    failures: List[str] = []
    lowered = adr_text.lower()
    for kw in ANTI_PATTERN_KEYWORDS:
        if kw.lower() in lowered:
            failures.append(
                "anti-pattern keyword found: %r — refactor or split into "
                "a non-PLAN-088 ADR" % kw
            )
    return failures


def _check_table_rows(rows: List[List[str]], canonical_ids: List[str]) -> List[str]:
    failures: List[str] = []
    data_rows: List[List[str]] = []
    for r in rows:
        if len(r) < 5:
            continue
        if CONVERSION_ID_RE.match(r[0]):
            data_rows.append(r)

    if len(data_rows) != 13:
        failures.append(
            "row count = %d (expected 13 — canonical 10 AUTO + 3 SEMI)"
            % len(data_rows)
        )

    seen_ids: List[str] = []
    canonical_set = set(canonical_ids)

    for idx, row in enumerate(data_rows, start=1):
        while len(row) < 5:
            row.append("")
        conv_id, primitive, sha, loc, surface = row[0], row[1], row[2], row[3], row[4]

        if conv_id not in canonical_set:
            failures.append(
                "row %d: conversion ID %r not in canonical-13 set "
                "(loaded from automation-gap-roadmap.yaml)" % (idx, conv_id)
            )
        if conv_id in seen_ids:
            failures.append(
                "row %d: conversion ID %r appears more than once" % (idx, conv_id)
            )
        seen_ids.append(conv_id)

        if not primitive:
            failures.append(
                "row %d (%s): capability primitive cell is empty"
                % (idx, conv_id)
            )

        sha_norm = sha.strip().strip("`")
        if not sha_norm:
            failures.append(
                "row %d (%s): SHA cell is empty (require 40-hex or %s)"
                % (idx, conv_id, ANCESTRAL_MARKER)
            )
        elif sha_norm == ANCESTRAL_MARKER:
            pass
        elif HEX40_RE.match(sha_norm) or HEX_SHORT_RE.match(sha_norm):
            pass
        else:
            failures.append(
                "row %d (%s): SHA %r does not match 40-hex / 7+ hex short "
                "/ %s marker" % (idx, conv_id, sha_norm, ANCESTRAL_MARKER)
            )

        loc_norm = loc.strip().strip("`").lstrip("~")
        if not loc_norm:
            failures.append(
                "row %d (%s): trigger-wire LoC cell is empty" % (idx, conv_id)
            )
        else:
            try:
                loc_int = int(loc_norm)
                if loc_int < 0:
                    failures.append(
                        "row %d (%s): trigger-wire LoC = %d is negative"
                        % (idx, conv_id, loc_int)
                    )
            except ValueError:
                failures.append(
                    "row %d (%s): trigger-wire LoC %r is not an integer"
                    % (idx, conv_id, loc_norm)
                )

        surface_norm = surface.strip().strip("`")
        if surface_norm != "0":
            failures.append(
                "row %d (%s): surface delta = %r (must equal exactly '0' "
                "— this is the load-bearing capability_surface_delta=0 claim)"
                % (idx, conv_id, surface_norm)
            )

    missing = canonical_set - set(seen_ids)
    if missing:
        failures.append(
            "missing canonical conversions: %s" % sorted(missing)
        )

    return failures


def run(adr_path: Path, roadmap_path: Path) -> int:
    adr_text = _read_text(adr_path)
    if adr_text is None:
        return 2

    canonical_ids = _load_canonical_13_from_roadmap(roadmap_path)
    section = _extract_rationale_section(adr_text)
    if section is None:
        return 2
    rows = _parse_table_rows(section)
    if not rows:
        _err("FAIL: no markdown table rows found in §3 Rationale section")
        return 1

    failures: List[str] = []
    failures.extend(_check_table_rows(rows, canonical_ids))
    failures.extend(_check_anti_pattern_keywords(adr_text))

    if failures:
        _err("ADR-118 §3 Rationale verifier: FAIL (%d issue(s))" % len(failures))
        for f in failures:
            _err("  - " + f)
        return 1

    print("ADR-118 §3 Rationale verifier: PASS")
    print("  - 13 canonical rows verified (10 AUTO + 3 SEMI)")
    print("  - all SHAs valid (40-hex / short hex / ANCESTRAL marker)")
    print("  - all trigger-wire LoC integers parsed")
    print("  - all surface_delta cells equal '0'")
    print("  - no anti-pattern keywords detected in ADR body")
    return 0


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description=(
            "Mechanical verifier for ADR-118 §3 Rationale SHA-pin table — "
            "asserts capability_surface_delta=0 across the canonical 13."
        )
    )
    p.add_argument("--adr-path", default=DEFAULT_ADR_PATH)
    p.add_argument("--roadmap-path", default=DEFAULT_ROADMAP_PATH)
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    return run(Path(args.adr_path), Path(args.roadmap_path))


if __name__ == "__main__":
    sys.exit(main())
