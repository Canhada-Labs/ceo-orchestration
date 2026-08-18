#!/usr/bin/env python3
"""Check plans/ADRs for human-time vocabulary used as EFFORT — advisory.

PLAN-180 W0 — executes the deferred Step 3 of ADR-081 (token-as-time-unit,
ACCEPTED 2026-04-25): effort estimates in this repo are expressed in
tokens + sessions; human calendar time is legitimate ONLY for external
waits (soak, hold, SLA, deprecation windows, telemetry collection) and
for the derived `eta_calendar:` field.

Advisory-only by design (ADR-081 Step 3: "not blocking"): exit code is
ALWAYS 0. Findings go to stdout as `path:line: excerpt`.

## What is flagged

Human-time effort vocabulary on a line of a NEW artifact (frontmatter
`created:`/`Date:` >= 2026-04-25, or any file passed explicitly in argv):
`weeks`, `semanas`, `dev-dias`, `dias uteis`, `horas de trabalho`,
`sprints de`, `meses`, `man-days`, `wall-clock` paired with a duration.

## What is NOT flagged (whitelist of legitimate wait contexts)

- the `external_wait:` and `eta_calendar:` frontmatter values;
- lines carrying external-wait vocabulary: soak, hold, SLA, deprecation,
  EOL, retention, janela, telemetria, observacao/observação, coleta,
  espera, aguarda, retrospectivo, expira, TTL, prazo legal;
- durations of PROCESS waits like "hold 24h" / "soak 7d" (hour/day
  tokens attached to wait words are the wait itself, not effort).

The corpus anchors (AC-W0.1, real lines — regression pair):
- MUST flag   PLAN-153-ecc-comparative-uplift.md:397  "adds ~1-2 weeks wall-clock"
- MUST NOT    PLAN-172…:66   "estende 2 semanas UMA vez" (telemetry
  window extension — the line carries "janela"/retrospectivo context)

Usage:
    python3 .claude/scripts/check-time-unit.py            # scan new corpus
    python3 .claude/scripts/check-time-unit.py FILE...    # scan exact files
    python3 .claude/scripts/check-time-unit.py --json     # machine output

stdlib-only, Python >= 3.9.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple

ADR_081_CUTOFF = "2026-04-25"

#: Effort vocabulary. Derived from the real leak corpus (S310 survey),
#: not from imagination (closed sets must be derived, not recalled).
_EFFORT_RE = re.compile(
    r"(?ix)"
    r"(?:~?\d+(?:[-–]\d+)?\s*(?:weeks?|semanas?)\b"
    r"|\b(?:weeks?|semanas?|meses|months?)\s+(?:of|de)\s+(?:work|trabalho|effort|esforc)"
    r"|\bdev[- ]dias?\b"
    r"|\bdias?\s+uteis\b|\bdias?\s+úteis\b"
    r"|\bhoras?\s+de\s+trabalho\b"
    r"|\bsprints?\s+de\b"
    r"|\bman[- ]days?\b"
    r"|\bperson[- ]weeks?\b)"
)

#: Legitimate-wait context: if ANY of these appears on the line, the
#: line is treated as external wait / process window, never effort.
_WAIT_RE = re.compile(
    r"(?i)(?:\b(?:external_wait|eta_calendar|soak|hold|sla|deprecat\w*|eol"
    r"|retention|retencao|retenção|janela|telemetria|telemetry"
    r"|observacao|observação|observation|coleta|collection|espera"
    r"|aguarda\w*|retrospectivo|expir\w*|ttl|prazo\s+legal"
    r"|max[- ]age|rotation|rotacao|rotação)\b"
    r"|\bpor\s+~?\d+(?:[-–]\d+)?\s*(?:semanas?|weeks?|dias?|days?)\b"
    r"|\bfor\s+~?\d+(?:[-–]\d+)?\s*(?:weeks?|days?)\b)"
)

_DATE_RE = re.compile(r"(?im)^(?:created|date|Data):\s*[\"']?(\d{4}-\d{2}-\d{2})")


def _artifact_is_new(text: str) -> bool:
    m = _DATE_RE.search(text[:2000])
    if not m:
        return False  # undated legacy corpus stays out of the default scan
    return m.group(1) >= ADR_081_CUTOFF


def _scan_text(path: str, text: str) -> List[Tuple[str, int, str]]:
    findings: List[Tuple[str, int, str]] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        if not _EFFORT_RE.search(line):
            continue
        if _WAIT_RE.search(line):
            continue
        findings.append((path, lineno, line.strip()[:160]))
    return findings


def _default_corpus(root: Path) -> List[Path]:
    out: List[Path] = []
    out.extend(sorted((root / ".claude" / "plans").glob("PLAN-*.md")))
    # ADR-081 itself is excluded: the doctrine document QUOTES the banned
    # vocabulary as its own counter-examples.
    out.extend(sorted(
        p for p in (root / ".claude" / "adr").glob("ADR-*.md")
        if p.name != "ADR-081-token-as-time-unit.md"))
    return out


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    as_json = "--json" in argv
    argv = [a for a in argv if a != "--json"]
    root = Path(__file__).resolve().parents[2]

    if argv:
        files = [Path(a) for a in argv]
        explicit = True
    else:
        files = _default_corpus(root)
        explicit = False

    findings: List[Tuple[str, int, str]] = []
    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            print("# check-time-unit: unreadable %s: %s" % (f, exc), file=sys.stderr)
            continue
        if not explicit and not _artifact_is_new(text):
            continue
        findings.extend(_scan_text(str(f), text))

    if as_json:
        print(json.dumps(
            [{"path": p, "line": n, "excerpt": e} for p, n, e in findings],
            ensure_ascii=False))
    else:
        for p, n, e in findings:
            print("%s:%d: %s" % (p, n, e))
        print("# check-time-unit (ADR-081, advisory): %d finding(s)" % len(findings))
    return 0  # ADVISORY: never blocks (ADR-081 Step 3)


if __name__ == "__main__":
    sys.exit(main())
