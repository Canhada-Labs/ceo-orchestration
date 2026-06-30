#!/usr/bin/env python3
"""check-flip-criteria-drift — governance drift guard (PLAN-012 Phase 2).

Prevents PLAN-NNN flip tables from saying "N=100" while the owning ADR
still says "N=30". For each flip in the plan's Dependency Graph table,
extract the criterion prose + Owning ADR reference; assert that every
numeric threshold token in the plan appears in the ADR body.

Allowlist file (``--allowlist``, default
``.claude/scripts/flip-criteria-drift-allowlist.txt``) documents
mismatches that lag the ADR by design — the flip PR amends the ADR
in-place per ADR-041 §4. TSV: ``Flip\\tADR\\tToken``; ``#`` = comment.

Exit codes: 0 clean or all-allowlisted, 1 drift, 2 parse error.
Stdlib only; Python >=3.9.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Header text for the plan's dependency-graph table. Matches PLAN-012's
# current structure. Drift-checker itself must stay in lockstep with this.
DEPENDENCY_GRAPH_HEADER = "## Dependency Graph"

# The ADR directory used when resolving bare "ADR-NNN" references.
ADR_DIR = Path(".claude/adr")

# Default allowlist file. Format: tab-separated `Flip\tADR\tToken` lines.
DEFAULT_ALLOWLIST = Path(".claude/scripts/flip-criteria-drift-allowlist.txt")


# Numeric threshold tokens extracted from prose. Tight set to keep
# FP rate low — over-eager tokenization produces noisy failures.
_NUMERIC_TOKEN_PATTERNS: Tuple[re.Pattern[str], ...] = (
    re.compile(r"N\s*[≥≤=]\s*\d+"),                   # N≥100 / N=100
    re.compile(r"κ\s*[≥≤=]\s*\d+\.?\d*"),             # κ≥0.8
    re.compile(r"[≥≤]?\s*\d+\.?\d*\s*%"),             # ≤5% / 20%
    re.compile(r"\d+\s+weekly\s+runs?", re.IGNORECASE),  # 4 weekly runs
    re.compile(r"\d+\s+weeks?", re.IGNORECASE),
    re.compile(r"\d+\s+days?", re.IGNORECASE),
    re.compile(r"\d+\s+consecutive", re.IGNORECASE),
    re.compile(r"[≥≤]\s*\d+\s+\w+"),                  # ≥200 pairs
    re.compile(r"p(?:50|95|99)"),
)


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

class FlipRow:
    """One row from the plan's Dependency Graph table."""

    def __init__(
        self,
        plan_id: str,
        flip_label: str,
        criterion_prose: str,
        adr_refs: List[str],
        source_line: int,
    ) -> None:
        self.plan_id = plan_id
        self.flip_label = flip_label
        self.criterion_prose = criterion_prose
        self.adr_refs = adr_refs
        self.source_line = source_line


class DriftReport:
    """Accumulates mismatches for the final exit-1 report."""

    def __init__(self) -> None:
        self.rows: List[Tuple[FlipRow, str, List[str]]] = []
        self.allowlisted: List[Tuple[FlipRow, str, List[str]]] = []

    def add(self, flip: FlipRow, adr_ref: str, missing_tokens: List[str]) -> None:
        self.rows.append((flip, adr_ref, missing_tokens))

    def add_allowlisted(
        self, flip: FlipRow, adr_ref: str, tokens: List[str]
    ) -> None:
        self.allowlisted.append((flip, adr_ref, tokens))

    def is_clean(self) -> bool:
        return not self.rows

    def write(self, stream) -> None:
        for flip, adr_ref, tokens in self.rows:
            stream.write(
                f"DRIFT: {flip.flip_label} (line {flip.source_line}) — "
                f"tokens missing from {adr_ref}: {tokens}\n"
            )


def parse_allowlist(path: Path) -> Set[Tuple[str, str, str]]:
    """Return a set of ``(flip_label, adr_ref, token)`` tuples.

    Missing file ⇒ empty allowlist. Format is TSV; lines starting with
    ``#`` or empty lines are ignored.
    """
    if not path.is_file():
        return set()
    entries: Set[Tuple[str, str, str]] = set()
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            raise ParseError(
                f"allowlist {path}: expected 3 tab-separated cols, got {parts!r}"
            )
        entries.add((parts[0].strip(), parts[1].strip(), parts[2].strip()))
    return entries


class ParseError(Exception):
    """Raised when the plan/ADR format deviates from expectation."""


# ---------------------------------------------------------------------------
# Plan parsing
# ---------------------------------------------------------------------------

def parse_plan_dependency_graph(plan_text: str) -> List[FlipRow]:
    """Extract rows from ``## Dependency Graph`` table (PLAN-012 §C4 schema).

    Columns: ``| Flip/Item | Blocks | Blocked-by | Owning ADR(s) | Execute in |``.
    Returns FlipRow per ``**Flip #NN**`` row. Non-flip rows skipped.
    """
    lines = plan_text.splitlines()
    start: Optional[int] = None
    for idx, line in enumerate(lines):
        if line.strip() == DEPENDENCY_GRAPH_HEADER:
            start = idx
            break
    if start is None:
        raise ParseError(
            f"plan does not contain section header {DEPENDENCY_GRAPH_HEADER!r}"
        )

    # Find the header row within this section (line starts with "|").
    table_start: Optional[int] = None
    for idx in range(start + 1, len(lines)):
        if lines[idx].lstrip().startswith("|"):
            table_start = idx
            break
        # Stop if we hit the next `##` section without finding the table.
        if lines[idx].startswith("## "):
            raise ParseError(
                "reached next section before locating dependency-graph table"
            )
    if table_start is None:
        raise ParseError("no table rows found under Dependency Graph header")

    # The next line must be the separator (|---|---|...).
    sep = lines[table_start + 1].strip()
    if not sep.startswith("|") or "---" not in sep:
        raise ParseError(
            f"expected table separator on line {table_start + 2}, got {sep!r}"
        )

    flip_pattern = re.compile(r"\*\*Flip\s+#(\d+)\*\*")
    # Track whether we saw any flip row at all (even deferred) so that
    # an all-deferred table doesn't raise. An empty table = genuine
    # parse-error; a table with only deferred flips = valid, no-op.
    saw_any_flip = False
    rows: List[FlipRow] = []
    for idx in range(table_start + 2, len(lines)):
        line = lines[idx]
        stripped = line.strip()
        if not stripped.startswith("|"):
            break
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if len(cells) < 5:
            continue  # malformed row — skip quietly
        flip_cell, _blocks, blocked_by, owning_adr_cell, execute_in = cells[:5]
        flip_m = flip_pattern.search(flip_cell)
        if not flip_m:
            continue  # deliverable row (D1/D3/D4...), not a flip
        saw_any_flip = True
        flip_label = f"Flip #{flip_m.group(1)}"
        adr_refs = _extract_adr_refs(owning_adr_cell)
        if not adr_refs:
            continue  # flip without owning ADR — nothing to drift against
        # Deferred flips (DEFER Sprint 15/16, DEFER post-#5, etc.) carry
        # revised criteria in the plan that intentionally lead the ADR
        # text — the flip PR in the target sprint is the one that
        # amends the ADR (per ADR-041 §4). Skip deferred rows so the
        # drift-checker stays clean pre-amendment. Once the flip is
        # in flight its "Execute in" cell drops "DEFER" and this
        # checker starts enforcing.
        if "DEFER" in execute_in.upper():
            continue
        # Criterion prose = "Blocked-by" column; that's where the authoritative
        # numeric thresholds live per PLAN-012's own convention.
        rows.append(
            FlipRow(
                plan_id=_extract_plan_id(plan_text) or "PLAN-???",
                flip_label=flip_label,
                criterion_prose=blocked_by,
                adr_refs=adr_refs,
                source_line=idx + 1,  # 1-based
            )
        )
    if not saw_any_flip:
        raise ParseError(
            "dependency-graph table parsed but zero flip rows discovered"
        )
    return rows


def _extract_plan_id(plan_text: str) -> Optional[str]:
    """Best-effort extraction of ``id: PLAN-NNN`` from YAML frontmatter."""
    m = re.search(r"^id:\s*(PLAN-\d+)", plan_text, flags=re.MULTILINE)
    return m.group(1) if m else None


def _extract_adr_refs(cell: str) -> List[str]:
    """Return every ``ADR-NNN`` substring from a plan cell."""
    return re.findall(r"ADR-\d{3}", cell)


# ---------------------------------------------------------------------------
# Token extraction + comparison
# ---------------------------------------------------------------------------

def extract_threshold_tokens(prose: str) -> Set[str]:
    """Return the set of numeric threshold tokens found in prose.

    Normalisation: collapse internal whitespace so ``N ≥ 100`` and
    ``N≥100`` compare equal; strip leading/trailing whitespace.
    """
    found: Set[str] = set()
    for pattern in _NUMERIC_TOKEN_PATTERNS:
        for m in pattern.finditer(prose):
            token = re.sub(r"\s+", "", m.group(0))
            found.add(token)
    return found


def compare_tokens_against_adr(
    plan_tokens: Set[str], adr_text: str
) -> List[str]:
    """Return the subset of plan tokens NOT present in the ADR body.

    The check normalises whitespace on the ADR side the same way.
    """
    normalised_adr = re.sub(r"\s+", "", adr_text)
    missing: List[str] = []
    for token in sorted(plan_tokens):
        if token not in normalised_adr:
            missing.append(token)
    return missing


# ---------------------------------------------------------------------------
# ADR loading
# ---------------------------------------------------------------------------

def locate_adr_file(adr_ref: str, adr_dir: Path) -> Path:
    """Resolve ``ADR-NNN`` to a path under ``.claude/adr/``.

    ADR files follow the naming convention ``ADR-NNN-<slug>.md``. There
    is exactly one match per reference under normal operation.
    """
    if not adr_dir.is_dir():
        raise ParseError(f"ADR directory not found: {adr_dir}")
    matches = sorted(adr_dir.glob(f"{adr_ref}-*.md"))
    if not matches:
        raise ParseError(f"no ADR file matches {adr_ref} under {adr_dir}")
    if len(matches) > 1:
        # Accept first lexicographically but log the ambiguity.
        sys.stderr.write(
            f"WARN: multiple ADR files match {adr_ref}; using {matches[0]}\n"
        )
    return matches[0]


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

def check_drift(
    plan_path: Path,
    adr_dir: Path,
    allowlist_path: Optional[Path] = None,
) -> DriftReport:
    """Top-level entry: parse plan, load ADRs, compare, return report.

    Any parse failure raises ``ParseError`` (caller maps to exit 2).
    Entries matched by the allowlist are recorded separately (they
    do NOT trip exit 1) but are still visible via ``--verbose``.
    """
    if not plan_path.is_file():
        raise ParseError(f"plan file not found: {plan_path}")
    plan_text = plan_path.read_text(encoding="utf-8")
    rows = parse_plan_dependency_graph(plan_text)

    allowed: Set[Tuple[str, str, str]] = (
        parse_allowlist(allowlist_path) if allowlist_path else set()
    )

    report = DriftReport()
    for flip in rows:
        plan_tokens = extract_threshold_tokens(flip.criterion_prose)
        if not plan_tokens:
            # No numeric thresholds in the plan for this flip — nothing
            # to drift against. Skip silently (the deferred-flip rows
            # often look like "— D3 + ..." without hard numbers).
            continue
        for adr_ref in flip.adr_refs:
            adr_path = locate_adr_file(adr_ref, adr_dir)
            adr_text = adr_path.read_text(encoding="utf-8")
            missing = compare_tokens_against_adr(plan_tokens, adr_text)
            if not missing:
                continue
            # Partition missing tokens into real drift vs allowlisted.
            real: List[str] = []
            allowed_here: List[str] = []
            for token in missing:
                if (flip.flip_label, adr_ref, token) in allowed:
                    allowed_here.append(token)
                else:
                    real.append(token)
            if real:
                report.add(flip, adr_ref, real)
            if allowed_here:
                report.add_allowlisted(flip, adr_ref, allowed_here)
    return report


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    """Build the argparse parser for the flip-criteria-drift CLI."""
    p = argparse.ArgumentParser(
        prog="check-flip-criteria-drift",
        description=(
            "Detect drift between a PLAN's Dependency Graph flip criteria "
            "and their owning ADRs. Exit 0 clean, 1 drift, 2 parse error."
        ),
    )
    p.add_argument(
        "--plan",
        required=True,
        type=Path,
        help="Path to the plan file to check (e.g., PLAN-012-sprint-12-stub.md).",
    )
    p.add_argument(
        "--adr-dir",
        type=Path,
        default=ADR_DIR,
        help="Directory containing ADR-NNN-*.md files (default: .claude/adr).",
    )
    p.add_argument(
        "--allowlist",
        type=Path,
        default=DEFAULT_ALLOWLIST,
        help=(
            "Path to drift allowlist TSV (flip\\tADR\\ttoken per line). "
            "Missing file → empty allowlist. "
            "Default: .claude/scripts/flip-criteria-drift-allowlist.txt"
        ),
    )
    p.add_argument(
        "--no-allowlist",
        action="store_true",
        help="Disable the allowlist entirely (strict mode).",
    )
    p.add_argument(
        "--verbose",
        action="store_true",
        help="Print per-flip token comparison even on clean runs.",
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — enforce FPR observation window flip-criteria invariants."""
    parser = build_parser()
    args = parser.parse_args(argv)
    allowlist = None if args.no_allowlist else args.allowlist
    try:
        report = check_drift(args.plan, args.adr_dir, allowlist_path=allowlist)
    except ParseError as exc:
        sys.stderr.write(f"PARSE-ERROR: {exc}\n")
        return 2
    if args.verbose and report.allowlisted:
        for flip, adr_ref, tokens in report.allowlisted:
            print(
                f"ALLOWLISTED: {flip.flip_label} ({adr_ref}) — {tokens}"
            )
    if report.is_clean():
        suffix = ""
        if report.allowlisted:
            suffix = (
                f" ({len(report.allowlisted)} allowlisted mismatch(es) "
                f"— see {allowlist})"
            )
        print(
            f"OK: {args.plan} flip criteria align with owning ADRs{suffix}"
        )
        return 0
    report.write(sys.stderr)
    sys.stderr.write(
        f"\nFAIL: {len(report.rows)} drift mismatch(es); update either plan "
        f"or ADR to reconcile.\n"
    )
    return 1


if __name__ == "__main__":  # pragma: no cover — CLI entry
    sys.exit(main())
