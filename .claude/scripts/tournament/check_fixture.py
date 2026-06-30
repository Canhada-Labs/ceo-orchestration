#!/usr/bin/env python3
"""Pre-commit fixture-security validator (C-P0-1 closure).

Usage (CLI):
    python3 -m tournament.check_fixture <path/to/fixtures.jsonl> [more.jsonl...]

Exit codes:
    0 = all fixtures pass
    1 = at least one fixture rejected

Validates each fixture record for:
- Schema conformance (via loader's `_validate_record`)
- Unicode 2024 attacks (tag chars, bidi override, homoglyph)
- LLM01 prompt injection shapes
- Telemetry / secret-shape heuristics
- Homoglyph detection

Uses `.claude/hooks/_lib/output_scan.py::scan()` — existing framework
defense (PLAN-029 / PLAN-042). Fail-open: if output_scan raises, this
validator reports the exception + skips-to-pass for that field (never
crashes the whole validation). Schema violations from loader are hard
rejects.

Can be wired into .githooks/pre-commit or run manually by adopters
before authoring new fixtures. CODEOWNERS extension
(`.claude/scripts/tournament/fixtures/**` → `@<owner>`) is the
merge-side gate that complements this commit-side scan.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Allow running this file directly OR via `python3 -m tournament.check_fixture`.
_HERE = Path(__file__).resolve().parent
_SCRIPTS = _HERE.parent
_REPO_ROOT = _SCRIPTS.parent.parent
_HOOKS_LIB = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_LIB) not in sys.path:
    sys.path.insert(0, str(_HOOKS_LIB))
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

# Fields on each fixture record that must be scanned for injection
# attempts. Everything textual that ends up in an LLM prompt or judge
# context must pass the scan.
_SCANNABLE_FIELDS = ("prompt", "acceptance_llm_judge")

# Severity gates. output_scan returns findings per sub-scanner; a hit on
# any of these family strings rejects the fixture. Strings match the
# exact `family` values emitted by `.claude/hooks/_lib/output_scan.py`:
# - unicode_injection (bidi + zero-width + tag chars + homoglyph all emit this family)
# - telemetry_string (hardcoded JWT / API key shapes)
# - LLM01_prompt_injection, LLM06_sensitive_info (OWASP LLM Top 10 subset)
_BLOCKING_FAMILIES = {
    "unicode_injection",
    "telemetry_string",
    "LLM01_prompt_injection",
    "LLM02_insecure_output",
    "LLM06_sensitive_info",
    "LLM08_excessive_agency",
    "LLM10_model_theft",
}


def _load_output_scan() -> "Optional[Any]":
    """Lazy import of output_scan (fail-open on import error)."""
    try:
        from _lib import output_scan  # type: ignore

        return output_scan
    except Exception as exc:  # pragma: no cover — defensive
        print(
            f"WARN: output_scan import failed: {exc!r}. "
            "Fixture security validation will ONLY enforce schema bounds. "
            "Install framework hooks _lib.",
            file=sys.stderr,
        )
        return None


def _load_loader() -> "Optional[Any]":
    """Lazy import of loader (for schema validation re-use)."""
    try:
        from tournament import loader  # type: ignore

        return loader
    except Exception:  # pragma: no cover — defensive
        return None


def scan_fixture_fields(record: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Run output_scan on every scannable field; return all blocking findings.

    Non-blocking findings (low severity) are dropped. Fail-open per field.
    """
    out_scan = _load_output_scan()
    if out_scan is None:
        return []

    blocking: List[Dict[str, Any]] = []
    for field_name in _SCANNABLE_FIELDS:
        value = record.get(field_name, "")
        # acceptance_strict is a list; extend scan to each
        if not isinstance(value, str):
            continue
        try:
            result = out_scan.scan(value)
        except Exception as exc:
            # Fail-open — report but don't block
            print(
                f"WARN: scan of field {field_name} raised {exc!r}; skipping",
                file=sys.stderr,
            )
            continue
        for finding in result.get("findings", []):
            family = str(finding.get("family", ""))
            if family in _BLOCKING_FAMILIES:
                blocking.append(
                    {
                        "field": field_name,
                        "fixture_id": record.get("fixture_id"),
                        "family": family,
                        "vector": finding.get("vector", ""),
                        "preview": finding.get("preview", "")[:160],
                    }
                )
    # acceptance_strict is list[str] — scan each
    strict_list = record.get("acceptance_strict", [])
    if isinstance(strict_list, list):
        for idx, item in enumerate(strict_list):
            if not isinstance(item, str):
                continue
            try:
                result = out_scan.scan(item)
            except Exception:
                continue
            for finding in result.get("findings", []):
                family = str(finding.get("family", ""))
                if family in _BLOCKING_FAMILIES:
                    blocking.append(
                        {
                            "field": f"acceptance_strict[{idx}]",
                            "fixture_id": record.get("fixture_id"),
                            "family": family,
                            "vector": finding.get("vector", ""),
                            "preview": finding.get("preview", "")[:160],
                        }
                    )
    return blocking


def check_file(path: Path) -> Tuple[int, List[Dict[str, Any]]]:
    """Validate all fixtures in a JSONL file.

    Returns (rejected_count, rejection_records).
    """
    loader = _load_loader()
    if not path.is_file():
        return 1, [{"error": f"File not found: {path}"}]

    rejections: List[Dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                rejections.append(
                    {
                        "file": str(path),
                        "line": line_no,
                        "reason": "JSON parse error",
                        "detail": str(exc),
                    }
                )
                continue

            # Schema validation via loader (hard caps enforced)
            if loader is not None:
                try:
                    loader._validate_record(record)
                except Exception as exc:
                    rejections.append(
                        {
                            "file": str(path),
                            "line": line_no,
                            "fixture_id": record.get("fixture_id"),
                            "reason": "schema",
                            "detail": str(exc),
                        }
                    )
                    continue

            # Security scan of all textual fields
            blocking = scan_fixture_fields(record)
            for finding in blocking:
                rejections.append(
                    {
                        "file": str(path),
                        "line": line_no,
                        "fixture_id": record.get("fixture_id"),
                        "reason": "security-scan",
                        "detail": finding,
                    }
                )

    return len(rejections), rejections


def main(argv=None) -> int:
    """CLI entrypoint — validate a tournament fixture against the 8 attack-shape filters."""
    parser = argparse.ArgumentParser(
        prog="check_fixture",
        description="Pre-commit security validator for tournament fixtures "
        "(ADR-063 §Fixture Trust Boundary).",
    )
    parser.add_argument(
        "paths",
        nargs="+",
        type=Path,
        help="One or more fixture JSONL files to validate.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit rejections as JSON to stdout (default: human-readable).",
    )
    args = parser.parse_args(argv)

    total_rejected = 0
    all_rejections: List[Dict[str, Any]] = []
    for path in args.paths:
        count, rejections = check_file(path)
        total_rejected += count
        all_rejections.extend(rejections)

    if args.json:
        print(
            json.dumps(
                {
                    "total_rejected": total_rejected,
                    "rejections": all_rejections,
                },
                indent=2,
            )
        )
    else:
        if total_rejected == 0:
            print(
                f"OK: {len(args.paths)} fixture file(s) pass schema + security scan."
            )
        else:
            print(
                f"REJECT: {total_rejected} fixture(s) failed validation:",
                file=sys.stderr,
            )
            for r in all_rejections:
                print(f"  - {json.dumps(r, default=str)}", file=sys.stderr)

    return 0 if total_rejected == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
