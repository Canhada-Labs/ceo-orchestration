"""PLAN-052 Phase 6 — MCP injection scanner empirical repro harness.

Closes PLAN-044 audit-v2 reopen_trigger: "26 additional MCP adversarial
fixtures shipped (50 total) + Phase 6 soak harness empirical run."

Analogous to ``test_rail_anomaly_repro.py``: a stdlib-only CLI tool
(NOT a pytest module despite the legacy ``test_*`` naming convention
inherited from ``test_rail_anomaly_repro.py``) that scores a corpus of
adversarial + benign fixtures against ``_lib/mcp_injection_scan.py``.

Reports per-corpus TP / FP / FN / TN, per-category detection rate, FPR,
and severity classification accuracy. Emits markdown + JSON for both
the soak baseline and ongoing weekly runs.

## Corpus format (.claude/scripts/swarm/fixtures/mcp_corpus.json)

Single JSON array; each entry::

    {
      "id": "adv-harness-001",
      "label": "adversarial" | "benign",
      "category": "harness_mimicry" | ... | "tricky_words",
      "expected_severity": "low" | "medium" | "high",
      "expected_match": true | false,
      "content": "<system-reminder>...</system-reminder>",
      "notes": "..."
    }

## Scoring

For each fixture:

- ``TP`` — label=adversarial AND ``finding.matched`` True
- ``FP`` — label=benign AND ``finding.matched`` True
- ``FN`` — label=adversarial AND ``finding.matched`` False
- ``TN`` — label=benign AND ``finding.matched`` False

Severity-classification accuracy is computed per adversarial fixture:
``finding.severity == fixture["expected_severity"]``? Only counted
when the fixture matched (TPs only).

## CLI

::

    python3 .claude/scripts/swarm/test_mcp_injection_repro.py \\
        --corpus .claude/scripts/swarm/fixtures/mcp_corpus.json \\
        --output .claude/plans/PLAN-052/soak/baseline.md \\
        --json-output .claude/plans/PLAN-052/soak/baseline.json

Default paths point at the canonical corpus + the PLAN-052 soak dir.

Exit codes:
- 0 — success (corpus scored; report emitted)
- 1 — corpus not found / malformed JSON / scanner not importable
- 2 — at least one FP found (advisory; soak operator decides whether
       to tune patterns or accept)

Stdlib-only.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[3]
HOOKS_DIR = REPO_ROOT / ".claude" / "hooks"


def _import_scanner() -> Any:
    """Import ``_lib.mcp_injection_scan`` from the canonical hooks dir.

    Adds the hooks dir to ``sys.path`` if not already present. Returns
    the module. Raises ``ImportError`` if the lib is missing.
    """
    if str(HOOKS_DIR) not in sys.path:
        sys.path.insert(0, str(HOOKS_DIR))
    from _lib import mcp_injection_scan as mod  # type: ignore  # noqa: WPS433
    return mod


# =============================================================================
# Data model
# =============================================================================


@dataclass
class FixtureScore:
    """Result of scoring a single fixture."""

    fixture_id: str
    label: str
    category: str
    expected_severity: str
    expected_match: bool
    actual_match: bool
    actual_severity: str
    family_counts: Dict[str, int]
    outcome: str  # "TP" | "FP" | "FN" | "TN"
    severity_correct: Optional[bool]  # None when fixture did not match
    notes: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fixture_id": self.fixture_id,
            "label": self.label,
            "category": self.category,
            "expected_severity": self.expected_severity,
            "expected_match": self.expected_match,
            "actual_match": self.actual_match,
            "actual_severity": self.actual_severity,
            "family_counts": dict(self.family_counts),
            "outcome": self.outcome,
            "severity_correct": self.severity_correct,
            "notes": self.notes,
        }


@dataclass
class CorpusReport:
    """Aggregated metrics across the full corpus."""

    total: int = 0
    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0
    severity_correct: int = 0
    severity_evaluable: int = 0  # fixtures that matched (denominator)
    per_category: Dict[str, Dict[str, int]] = field(default_factory=dict)
    fixture_scores: List[FixtureScore] = field(default_factory=list)

    def detection_rate(self) -> float:
        """TP / (TP + FN). Adversarial recall."""
        denom = self.tp + self.fn
        if denom == 0:
            return 0.0
        return self.tp / denom

    def fpr(self) -> float:
        """FP / (FP + TN). False-positive rate on benign corpus."""
        denom = self.fp + self.tn
        if denom == 0:
            return 0.0
        return self.fp / denom

    def severity_accuracy(self) -> float:
        """severity_correct / severity_evaluable."""
        if self.severity_evaluable == 0:
            return 0.0
        return self.severity_correct / self.severity_evaluable

    def to_json_summary(self) -> Dict[str, Any]:
        return {
            "total": self.total,
            "tp": self.tp,
            "fp": self.fp,
            "fn": self.fn,
            "tn": self.tn,
            "detection_rate": round(self.detection_rate(), 4),
            "fpr": round(self.fpr(), 4),
            "severity_accuracy": round(self.severity_accuracy(), 4),
            "severity_correct": self.severity_correct,
            "severity_evaluable": self.severity_evaluable,
            "per_category": dict(self.per_category),
            "fixture_scores": [s.to_dict() for s in self.fixture_scores],
        }


# =============================================================================
# Loading + scoring
# =============================================================================


def load_corpus(path: Path) -> List[Dict[str, Any]]:
    """Load + validate the corpus JSON. Raises ``ValueError`` on shape errors."""
    if not path.is_file():
        raise FileNotFoundError("corpus not found at {p}".format(p=path))
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("corpus root must be a JSON array")
    required = {
        "id",
        "label",
        "category",
        "expected_severity",
        "expected_match",
        "content",
    }
    for i, entry in enumerate(data):
        if not isinstance(entry, dict):
            raise ValueError("entry {i} is not an object".format(i=i))
        missing = required - set(entry.keys())
        if missing:
            raise ValueError(
                "entry {i} ({eid}) missing keys: {m}".format(
                    i=i, eid=entry.get("id", "?"), m=sorted(missing)
                )
            )
        if entry["label"] not in {"adversarial", "benign"}:
            raise ValueError(
                "entry {eid} has invalid label: {l}".format(
                    eid=entry["id"], l=entry["label"]
                )
            )
    return data


def score_fixture(scanner: Any, entry: Dict[str, Any]) -> FixtureScore:
    """Run scanner on a single fixture; return score row."""
    # Normalize backslash-n in JSON string to actual newlines for realism.
    content = entry["content"]
    if isinstance(content, str):
        content = content.replace("\\n", "\n")

    finding = scanner.scan_tool_result(
        content,
        server_id="repro",
        tool_name="corpus_test",
    )

    expected_match = bool(entry["expected_match"])
    label = entry["label"]
    actual_match = bool(finding.matched)
    actual_severity = finding.severity

    if label == "adversarial":
        outcome = "TP" if actual_match else "FN"
    else:  # benign
        outcome = "FP" if actual_match else "TN"

    severity_correct: Optional[bool]
    if actual_match:
        severity_correct = actual_severity == entry["expected_severity"]
    else:
        severity_correct = None

    return FixtureScore(
        fixture_id=str(entry["id"]),
        label=label,
        category=str(entry["category"]),
        expected_severity=str(entry["expected_severity"]),
        expected_match=expected_match,
        actual_match=actual_match,
        actual_severity=actual_severity,
        family_counts=dict(finding.family_counts),
        outcome=outcome,
        severity_correct=severity_correct,
        notes=str(entry.get("notes", "")),
    )


def aggregate(scores: List[FixtureScore]) -> CorpusReport:
    """Build CorpusReport from per-fixture scores."""
    report = CorpusReport()
    report.fixture_scores = list(scores)
    report.total = len(scores)

    per_cat: Dict[str, Dict[str, int]] = defaultdict(
        lambda: {"tp": 0, "fp": 0, "fn": 0, "tn": 0, "total": 0}
    )

    for s in scores:
        per_cat[s.category]["total"] += 1
        if s.outcome == "TP":
            report.tp += 1
            per_cat[s.category]["tp"] += 1
        elif s.outcome == "FP":
            report.fp += 1
            per_cat[s.category]["fp"] += 1
        elif s.outcome == "FN":
            report.fn += 1
            per_cat[s.category]["fn"] += 1
        elif s.outcome == "TN":
            report.tn += 1
            per_cat[s.category]["tn"] += 1

        if s.severity_correct is not None:
            report.severity_evaluable += 1
            if s.severity_correct:
                report.severity_correct += 1

    report.per_category = dict(per_cat)
    return report


# =============================================================================
# Output formatting
# =============================================================================


def format_markdown(report: CorpusReport, *, corpus_path: str) -> str:
    """Render a markdown report for the soak log."""
    lines: List[str] = []
    lines.append("# MCP injection scanner — empirical repro report")
    lines.append("")
    lines.append("**Corpus:** `{p}`".format(p=corpus_path))
    lines.append("**Total fixtures:** {n}".format(n=report.total))
    lines.append("")
    lines.append("## Aggregate metrics")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append("| TP (adversarial detected) | {n} |".format(n=report.tp))
    lines.append("| FN (adversarial missed) | {n} |".format(n=report.fn))
    lines.append("| FP (benign flagged) | {n} |".format(n=report.fp))
    lines.append("| TN (benign passed) | {n} |".format(n=report.tn))
    lines.append("| Detection rate (TP / (TP+FN)) | {r:.2%} |".format(
        r=report.detection_rate()
    ))
    lines.append("| FPR (FP / (FP+TN)) | {r:.2%} |".format(r=report.fpr()))
    lines.append("| Severity accuracy (correct/{d}) | {r:.2%} |".format(
        d=report.severity_evaluable, r=report.severity_accuracy()
    ))
    lines.append("")

    lines.append("## Per-category breakdown")
    lines.append("")
    lines.append("| Category | Total | TP | FP | FN | TN |")
    lines.append("|---|---:|---:|---:|---:|---:|")
    for cat in sorted(report.per_category.keys()):
        row = report.per_category[cat]
        lines.append(
            "| {cat} | {t} | {tp} | {fp} | {fn} | {tn} |".format(
                cat=cat,
                t=row["total"],
                tp=row["tp"],
                fp=row["fp"],
                fn=row["fn"],
                tn=row["tn"],
            )
        )
    lines.append("")

    fps = [s for s in report.fixture_scores if s.outcome == "FP"]
    fns = [s for s in report.fixture_scores if s.outcome == "FN"]

    if fps:
        lines.append("## False positives ({n})".format(n=len(fps)))
        lines.append("")
        lines.append("| Fixture | Category | Detected severity | Notes |")
        lines.append("|---|---|---|---|")
        for s in fps:
            lines.append(
                "| `{id}` | {cat} | {sev} | {n} |".format(
                    id=s.fixture_id,
                    cat=s.category,
                    sev=s.actual_severity,
                    n=s.notes,
                )
            )
        lines.append("")

    if fns:
        lines.append("## False negatives ({n})".format(n=len(fns)))
        lines.append("")
        lines.append("| Fixture | Category | Expected severity | Notes |")
        lines.append("|---|---|---|---|")
        for s in fns:
            lines.append(
                "| `{id}` | {cat} | {sev} | {n} |".format(
                    id=s.fixture_id,
                    cat=s.category,
                    sev=s.expected_severity,
                    n=s.notes,
                )
            )
        lines.append("")

    lines.append("## Soak window discipline")
    lines.append("")
    lines.append(
        "Per ADR-057 / PLAN-052 §Phase 6, this baseline starts a 14-day "
        "soak window in default ADVISORY mode. FPR target ≤ 1% across "
        "100+ MCP tool calls. If FPR ≤ 1% at end of soak, propose flipping "
        "the default to STRICT in a follow-up ADR. If FPR > 1%, tune "
        "detectors + extend soak."
    )
    lines.append("")
    lines.append("Re-run via:")
    lines.append("")
    lines.append("```bash")
    lines.append(
        "python3 .claude/scripts/swarm/test_mcp_injection_repro.py "
        "--output .claude/plans/PLAN-052/soak/run-NNNN.md"
    )
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


# =============================================================================
# CLI
# =============================================================================


def _default_corpus_path() -> Path:
    return Path(__file__).resolve().parent / "fixtures" / "mcp_corpus.json"


def _default_md_output() -> Path:
    return REPO_ROOT / ".claude" / "plans" / "PLAN-052" / "soak" / "baseline.md"


def _default_json_output() -> Path:
    return REPO_ROOT / ".claude" / "plans" / "PLAN-052" / "soak" / "baseline.json"


def _parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="test_mcp_injection_repro",
        description=(
            "PLAN-052 Phase 6 empirical repro harness for "
            "_lib/mcp_injection_scan.py. Scores adversarial + benign "
            "fixtures, emits markdown + JSON reports."
        ),
    )
    parser.add_argument(
        "--corpus",
        type=Path,
        default=_default_corpus_path(),
        help="Path to corpus JSON (default: fixtures/mcp_corpus.json)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=_default_md_output(),
        help="Path to markdown output (default: PLAN-052/soak/baseline.md)",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        default=_default_json_output(),
        help="Path to JSON output (default: PLAN-052/soak/baseline.json)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress stdout summary; still writes outputs",
    )
    return parser.parse_args(argv)


def run(
    corpus_path: Path,
    md_output: Path,
    json_output: Path,
    *,
    quiet: bool = False,
) -> Tuple[CorpusReport, int]:
    """Run the harness end-to-end. Returns (report, exit_code)."""
    try:
        scanner = _import_scanner()
    except ImportError as e:
        print("error: scanner import failed: {e}".format(e=e), file=sys.stderr)
        return CorpusReport(), 1

    try:
        corpus = load_corpus(corpus_path)
    except (FileNotFoundError, ValueError) as e:
        print("error: corpus load failed: {e}".format(e=e), file=sys.stderr)
        return CorpusReport(), 1

    scores = [score_fixture(scanner, entry) for entry in corpus]
    report = aggregate(scores)

    md_output.parent.mkdir(parents=True, exist_ok=True)
    md_output.write_text(
        format_markdown(report, corpus_path=str(corpus_path)),
        encoding="utf-8",
    )

    json_output.parent.mkdir(parents=True, exist_ok=True)
    json_output.write_text(
        json.dumps(report.to_json_summary(), indent=2, sort_keys=True),
        encoding="utf-8",
    )

    if not quiet:
        print("=== MCP injection scanner repro ===")
        print("corpus: {p}".format(p=corpus_path))
        print(
            "TP={tp} FN={fn} FP={fp} TN={tn} detection={dr:.2%} fpr={fpr:.2%}".format(
                tp=report.tp,
                fn=report.fn,
                fp=report.fp,
                tn=report.tn,
                dr=report.detection_rate(),
                fpr=report.fpr(),
            )
        )
        print("md:   {p}".format(p=md_output))
        print("json: {p}".format(p=json_output))

    if report.fp > 0:
        return report, 2
    return report, 0


def main(argv: Optional[List[str]] = None) -> int:
    args = _parse_args(argv)
    _, code = run(
        args.corpus,
        args.output,
        args.json_output,
        quiet=args.quiet,
    )
    return code


if __name__ == "__main__":
    sys.exit(main())
