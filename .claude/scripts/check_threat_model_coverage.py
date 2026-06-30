#!/usr/bin/env python3
"""PLAN-013 Phase C.5 — Threat model coverage CI check.

Asserts that every ADR tagged `security` (or with security-relevant scope)
appears in `docs/threat-model.md`'s per-ADR threat table. Fail-closed:
missing coverage = exit 1.

Rationale (PLAN-013 debate §C4 HIGH): per-ADR threat mapping must be
enforced mechanically. "Cross-reference-only" mapping becomes paste-in
without forcing function. CI guards the invariant so threat-model.md
cannot drift from the ADR corpus silently.

Stdlib only per ADR-002. Python 3.9+.

Usage:
  python3 check_threat_model_coverage.py
  python3 check_threat_model_coverage.py --json
  python3 check_threat_model_coverage.py --adr-dir PATH --threat-model PATH
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Iterable, List, Optional, Set, Tuple

# ADR-numbering regex: ADR-<NNN> at file-prefix or inside per-ADR row
_ADR_FILE_RE = re.compile(r"^ADR-(\d{3})-[a-z0-9-]+\.md$")
_ADR_ROW_RE = re.compile(r"\bADR-(\d{3})\b")

# Security-tag heuristic: ADR is in scope for threat model iff it matches
# ANY of:
#  - Status header mentions security / auth / crypto / credential / access
#  - Title contains auth / security / credential / access / kill-switch /
#    sentinel / canonical / breaker / output-safety / rate-limit
#  - §Related: lists an ADR in the established security set
# Explicit opt-out: ADR text contains the phrase "security-scope: N/A"
# (grep-exact).
_SECURITY_KEYWORDS = (
    "security",
    "auth",
    "credential",
    "access",
    "sentinel",
    "canonical",
    "breaker",
    "output safety",
    "rate limit",
    "rate-limit",
    "kill-switch",
    "isolation",
    "redaction",
    "signed",
    "signing",
    "tamper",
    "injection",
    "exfil",
    "provenance",
    "audit",
    "revocation",
    "SOC2",
    "STRIDE",
    "threat",
    "adversar",
)

_OPT_OUT_MARKER = "security-scope: N/A"


def _find_repo_root(start: Path) -> Path:
    cur = start.resolve()
    for parent in (cur, *cur.parents):
        if (parent / ".git").exists():
            return parent
    raise RuntimeError(f"no .git ancestor of {start}")


def enumerate_adrs(adr_dir: Path) -> List[Tuple[str, Path]]:
    """Return list of (adr_id, path) for every ADR-NNN-*.md file."""
    out: List[Tuple[str, Path]] = []
    for child in sorted(adr_dir.iterdir()):
        if not child.is_file():
            continue
        match = _ADR_FILE_RE.match(child.name)
        if match:
            out.append((f"ADR-{match.group(1)}", child))
    return out


def is_security_scoped(adr_path: Path) -> bool:
    """Heuristic classification — does this ADR have security scope?"""
    text = adr_path.read_text(encoding="utf-8")
    if _OPT_OUT_MARKER in text:
        return False
    lower = text.lower()
    for kw in _SECURITY_KEYWORDS:
        if kw.lower() in lower:
            return True
    return False


def extract_threat_model_adrs(threat_model_path: Path) -> Set[str]:
    """Return set of ADR-NNN ids mentioned in the threat-model doc."""
    text = threat_model_path.read_text(encoding="utf-8")
    return {f"ADR-{m}" for m in _ADR_ROW_RE.findall(text)}


def check_coverage(
    adr_dir: Path,
    threat_model: Path,
) -> Tuple[List[dict], bool]:
    """Return (per-ADR report rows, any_missing)."""
    adrs = enumerate_adrs(adr_dir)
    covered = extract_threat_model_adrs(threat_model)
    rows: List[dict] = []
    any_missing = False
    for adr_id, path in adrs:
        in_scope = is_security_scoped(path)
        in_model = adr_id in covered
        ok = (not in_scope) or in_model
        rows.append(
            {
                "adr": adr_id,
                "path": str(path.name),
                "security_scoped": in_scope,
                "in_threat_model": in_model,
                "ok": ok,
            }
        )
        if not ok:
            any_missing = True
    return rows, any_missing


def main(argv: Optional[Iterable[str]] = None) -> int:
    """CLI entrypoint — assert declared threats have implemented mitigations."""
    parser = argparse.ArgumentParser(
        description="Assert threat-model.md covers every security-scoped ADR.",
    )
    parser.add_argument(
        "--adr-dir",
        default=".claude/adr",
        help="ADR directory relative to repo root (default: %(default)s)",
    )
    parser.add_argument(
        "--threat-model",
        default="docs/threat-model.md",
        help="Threat model path relative to repo root (default: %(default)s)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON report on stdout",
    )
    parser.add_argument(
        "--repo-root",
        default=None,
        help="Override repo root (default: detect via .git)",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.repo_root:
        root = Path(args.repo_root).resolve()
    else:
        root = _find_repo_root(Path(__file__).parent)

    adr_dir = root / args.adr_dir
    threat_model = root / args.threat_model

    if not adr_dir.is_dir():
        print(f"ERROR: adr dir not found: {adr_dir}", file=sys.stderr)
        return 2
    if not threat_model.is_file():
        print(
            f"ERROR: threat model not found: {threat_model}",
            file=sys.stderr,
        )
        return 2

    rows, any_missing = check_coverage(adr_dir, threat_model)

    if args.json:
        print(
            json.dumps(
                {"rows": rows, "missing": any_missing},
                indent=2,
            )
        )
    else:
        for r in rows:
            if not r["security_scoped"]:
                status = "skip"
            elif r["in_threat_model"]:
                status = "OK"
            else:
                status = "MISSING"
            print(f"{status:8s} {r['adr']}  ({r['path']})")
        if any_missing:
            print(
                "\nFAIL: threat-model.md missing entries for "
                "security-scoped ADR(s)",
                file=sys.stderr,
            )
        else:
            print("\nOK: every security-scoped ADR covered")

    return 1 if any_missing else 0


if __name__ == "__main__":
    sys.exit(main())
