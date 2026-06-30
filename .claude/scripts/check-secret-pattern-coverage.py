#!/usr/bin/env python3
"""Advisory: per-family fixture coverage report for exchange secret patterns.

PLAN-087 Wave E.3 (F-A-TDE-T-0004 P3 Codex CONFIRM). The file
``.claude/policies/secret-patterns-exchange.yaml`` ships multiple
exchange families; each pattern entry carries a per-pattern
``fpr_target`` field but the catalog has no aggregated
``fpr_per_family`` key. This advisory script enumerates per-family
pattern counts + per-family ``fpr_target`` distribution
(min / mean / max) WITHOUT enforcing any threshold.

Advisory contract (SKILL §Detection-as-Code):

* exit 0 ALWAYS (never gates CI)
* output to stdout in stable line-oriented format
* no third-party YAML dep (stdlib only per ADR-002) — minimal
  line-oriented parser scoped to the known two-space-indent shape

Future PLAN-091+ may elevate to budget enforcement after pre-deploy
FPR measurement on historical audit-log data. See PLAN-091 row
"F-A-SEC-T-0014 per-repo-stack regex parity audit".
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
_CATALOG = _REPO_ROOT / ".claude" / "policies" / "secret-patterns-exchange.yaml"

# Regexes scoped to the shape of secret-patterns-exchange.yaml:
#   - id: <slug>
#     family: <name>
#     regex: '...'
#     fpr_target: 0.15
# Tolerates trailing comments and quoted/unquoted values.
_ID_RE = re.compile(r"^\s*-\s*id:\s*(\S+)\s*$")
_FAMILY_RE = re.compile(r"^\s*family:\s*(\S+)\s*$")
_FPR_RE = re.compile(r"^\s*fpr_target:\s*([0-9]+(?:\.[0-9]+)?)\s*$")
_CONFIDENCE_RE = re.compile(r"^\s*confidence:\s*(\S+)\s*$")


def _parse_catalog(path: Path) -> List[Dict[str, object]]:
    """Yield one dict per pattern entry. Best-effort, never raises."""
    out: List[Dict[str, object]] = []
    if not path.is_file():
        return out
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return out
    current: Optional[Dict[str, object]] = None
    for line in text.splitlines():
        m_id = _ID_RE.match(line)
        if m_id is not None:
            if current is not None:
                out.append(current)
            current = {"id": m_id.group(1)}
            continue
        if current is None:
            continue
        m_fam = _FAMILY_RE.match(line)
        if m_fam is not None:
            current["family"] = m_fam.group(1)
            continue
        m_fpr = _FPR_RE.match(line)
        if m_fpr is not None:
            try:
                current["fpr_target"] = float(m_fpr.group(1))
            except ValueError:
                pass
            continue
        m_conf = _CONFIDENCE_RE.match(line)
        if m_conf is not None:
            current["confidence"] = m_conf.group(1)
            continue
    if current is not None:
        out.append(current)
    return out


def _aggregate_by_family(
    entries: List[Dict[str, object]],
) -> Dict[str, Dict[str, object]]:
    """Group by family; compute count + fpr_target min/mean/max."""
    groups: Dict[str, List[Dict[str, object]]] = {}
    for e in entries:
        fam = e.get("family")
        if not isinstance(fam, str):
            continue
        groups.setdefault(fam, []).append(e)
    agg: Dict[str, Dict[str, object]] = {}
    for fam, items in groups.items():
        fprs: List[float] = [
            x["fpr_target"]
            for x in items
            if isinstance(x.get("fpr_target"), float)
        ]
        row: Dict[str, object] = {
            "pattern_count": len(items),
            "fpr_target_count": len(fprs),
        }
        if fprs:
            row["fpr_target_min"] = min(fprs)
            row["fpr_target_max"] = max(fprs)
            row["fpr_target_mean"] = round(sum(fprs) / len(fprs), 4)
        else:
            row["fpr_target_min"] = None
            row["fpr_target_max"] = None
            row["fpr_target_mean"] = None
        agg[fam] = row
    return agg


def _format_report(agg: Dict[str, Dict[str, object]]) -> str:
    lines: List[str] = []
    lines.append(
        "# Advisory: per-family fixture coverage "
        "(PLAN-087 Wave E.3 / F-A-TDE-T-0004)"
    )
    lines.append("# Catalog: .claude/policies/secret-patterns-exchange.yaml")
    lines.append(
        "# Exit 0 always - never gates CI. SKILL section "
        "Detection-as-Code."
    )
    lines.append("")
    header = (
        "family            patterns  fpr_count  fpr_min  fpr_mean  fpr_max"
    )
    lines.append(header)
    lines.append("-" * len(header))
    for fam in sorted(agg.keys()):
        r = agg[fam]

        def _fmt(v: object) -> str:
            if v is None:
                return "-"
            if isinstance(v, float):
                return f"{v:.4f}"
            return str(v)

        lines.append(
            f"{fam:<17} "
            f"{r['pattern_count']:>8}  "
            f"{r['fpr_target_count']:>9}  "
            f"{_fmt(r['fpr_target_min']):>7}  "
            f"{_fmt(r['fpr_target_mean']):>8}  "
            f"{_fmt(r['fpr_target_max']):>7}"
        )
    lines.append("")
    lines.append(
        "# Total families: " + str(len(agg))
    )
    return "\n".join(lines)


def main() -> int:
    entries = _parse_catalog(_CATALOG)
    if not entries:
        print(
            "# ADVISORY (PLAN-087 E.3): catalog not parseable or absent at "
            + str(_CATALOG)
        )
        print("# Total families: 0")
        return 0  # advisory: never fail
    agg = _aggregate_by_family(entries)
    print(_format_report(agg))
    return 0


if __name__ == "__main__":
    sys.exit(main())
