#!/usr/bin/env python3
"""check-model-deprecations.py — permanent model-deprecation checker.

PLAN-135 W0/W1 (unit w0r): the S230 heroic sweep made a permanent
instrument. Scans one or more directory trees for Claude model-id literals
listed in the sidecar JSON ledger (`model-deprecations.json`, same dir) and
classifies every hit by retirement proximity:

  BREAK  — id is already retired (API requests fail today) on a non-inert path
  WARN   — id retires within --warn-days (default 60) on a non-inert path
  INFO   — id is deprecated but retirement is farther out (or undated)
  INERT  — path matches a ledger `inert_path_rules` entry (negative fixtures,
           prose docs, historical run results, by-design id carriers — the
           S230 triage classes, configurable in the ledger, NOT hardcoded)

Scan targets (precedence): argv roots > CEO_DEPRECATION_SCAN_ROOTS
(os.pathsep-separated) > this framework repo itself. Matching logic reuses
the S230 sweep (.claude/plans/PLAN-135/research/sweep_deprecated_models.py):
os.walk with SKIP_DIRS pruning, 2MB cap, binary sniff, utf-8/ignore decode,
finditer with line numbers — but with ledger-driven patterns instead of
hardcoded ones and WITHOUT the hardcoded Owner-machine repo list.

Exit codes:
  0 — report mode (always), or --check with no BREAK/WARN, or infra
      fail-open (missing/corrupt ledger, bad --today: advisory + exit 0)
  1 — --check only: at least one non-inert BREAK or <=warn-days WARN
  2 — CLI usage error (argparse)

Evidence convention (S230 postfix): the final human line is always
`LIVE-BREAKS-REMAINING: <n>` so a saved run is committable evidence.

Wired as: 5th read-only agent input of the `nightly-hygiene` saved workflow
(--json mode) + non-fatal pre-flight WARN step in scripts/upgrade.sh
(staged for Owner ceremony — upgrade.sh is canonical).

Stdlib-only. Python >= 3.9. Read-only: writes NO files, emits NO audit
events (it must stay runnable under ADR-136-AMEND-1 read-only confinement).
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
from typing import Dict, List, Optional, Tuple

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_LEDGER_PATH = os.path.join(SCRIPT_DIR, "model-deprecations.json")
# .claude/scripts/check-model-deprecations.py -> repo root is parents[2]
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, os.pardir, os.pardir))

ENV_SCAN_ROOTS = "CEO_DEPRECATION_SCAN_ROOTS"
WARN_DAYS_DEFAULT = 60
MAX_DISPLAY_PER_ROOT = 50  # sweep parity; --json output is never capped

# S230 sweep parity (sweep_deprecated_models.py) + low-risk additions.
SKIP_DIRS = {
    "node_modules", ".git", "dist", "build", ".next", "venv", ".venv",
    "__pycache__", ".pytest_cache", "coverage", ".turbo", "out",
    "htmlcov", ".claude.bak",
}
MAX_BYTES = 2_000_000

SEV_BREAK = "BREAK"
SEV_WARN = "WARN"
SEV_INFO = "INFO"
SEV_INERT = "INERT"


def _advisory(msg: str) -> None:
    sys.stderr.write("[check-model-deprecations] advisory: %s\n" % msg)


def parse_iso_date(value: object) -> Optional[datetime.date]:
    """Lenient ISO date parse; None on anything unparseable (fail-open)."""
    if not isinstance(value, str):
        return None
    try:
        return datetime.date.fromisoformat(value.strip())
    except (ValueError, AttributeError):
        return None


def load_ledger(path: str) -> Optional[Dict]:
    """Load the JSON ledger. None on missing/corrupt (caller fail-opens)."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError, UnicodeDecodeError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("models"), list):
        return None
    return data


def build_matcher(
    ledger: Dict,
) -> Tuple[Optional["re.Pattern[str]"], Dict[str, Dict]]:
    """One combined regex over every model_id + alias, longest-first.

    Longest-first alternation guarantees `claude-opus-4-1-20250805` wins
    over its bare alias `claude-opus-4-1` at the same position (no double
    count, sweep-pattern fidelity). The trailing guard refuses to match
    when the id continues with an alphanumeric or '.', so e.g.
    `claude-opus-4-10` or `claude-2.10` never false-hit.
    """
    literal_map: Dict[str, Dict] = {}
    for entry in ledger.get("models", []):
        if not isinstance(entry, dict):
            continue
        model_id = entry.get("model_id")
        if not isinstance(model_id, str) or not model_id:
            continue
        literals = [model_id]
        aliases = entry.get("aliases")
        if isinstance(aliases, list):
            literals.extend(a for a in aliases if isinstance(a, str) and a)
        for lit in literals:
            literal_map.setdefault(lit, entry)
    if not literal_map:
        return None, {}
    alternation = "|".join(
        re.escape(lit)
        for lit in sorted(literal_map, key=len, reverse=True)
    )
    pattern = re.compile("(?:%s)(?![A-Za-z0-9.])" % alternation)
    return pattern, literal_map


def compile_inert_rules(
    ledger: Dict,
) -> List[Tuple[str, "re.Pattern[str]"]]:
    """Compile ledger inert_path_rules; bad rules are skipped (advisory)."""
    rules: List[Tuple[str, "re.Pattern[str]"]] = []
    raw = ledger.get("inert_path_rules")
    if not isinstance(raw, list):
        return rules
    for item in raw:
        if not isinstance(item, dict):
            continue
        rule_id = item.get("rule_id")
        rule_pattern = item.get("pattern")
        if not isinstance(rule_id, str) or not isinstance(rule_pattern, str):
            continue
        try:
            rules.append((rule_id, re.compile(rule_pattern)))
        except re.error as exc:
            _advisory("inert rule %r skipped (bad regex: %s)" % (rule_id, exc))
    return rules


def resolve_roots(
    cli_roots: List[str], env_value: Optional[str]
) -> List[str]:
    """argv roots > CEO_DEPRECATION_SCAN_ROOTS > the framework repo itself."""
    if cli_roots:
        candidates = list(cli_roots)
    elif env_value:
        candidates = [p for p in env_value.split(os.pathsep) if p.strip()]
    else:
        candidates = [REPO_ROOT]
    return [os.path.abspath(os.path.expanduser(p.strip())) for p in candidates]


def classify_entry(
    entry: Dict, today: datetime.date, warn_days: int
) -> Tuple[str, str]:
    """(severity, label) for one ledger entry relative to `today`."""
    retirement = parse_iso_date(entry.get("retirement"))
    if retirement is None:
        return SEV_INFO, "DEPRECATED-NO-DATE"
    if retirement <= today:
        return SEV_BREAK, "ALREADY-RETIRED"
    label = "RETIRE-%s" % retirement.isoformat()
    if (retirement - today).days <= warn_days:
        return SEV_WARN, label
    return SEV_INFO, label


def first_inert_rule(
    rel_path: str, inert_rules: List[Tuple[str, "re.Pattern[str]"]]
) -> Optional[str]:
    for rule_id, rule_re in inert_rules:
        if rule_re.search(rel_path):
            return rule_id
    return None


def scan_root(
    root: str,
    pattern: "re.Pattern[str]",
    literal_map: Dict[str, Dict],
    inert_rules: List[Tuple[str, "re.Pattern[str]"]],
    today: datetime.date,
    warn_days: int,
) -> List[Dict]:
    """S230 sweep walk, ledger-driven; returns one dict per hit."""
    hits: List[Dict] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            path = os.path.join(dirpath, fn)
            try:
                if os.path.getsize(path) > MAX_BYTES:
                    continue
                with open(path, "rb") as fh:
                    raw = fh.read()
                if b"\x00" in raw[:8192]:
                    continue
                text = raw.decode("utf-8", errors="ignore")
            except OSError:
                continue
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            inert_rule = first_inert_rule(rel, inert_rules)
            for m in pattern.finditer(text):
                entry = literal_map.get(m.group(0))
                if entry is None:  # pragma: no cover — map covers pattern
                    continue
                severity, label = classify_entry(entry, today, warn_days)
                hit = {
                    "root": root,
                    "path": rel,
                    "line": text.count("\n", 0, m.start()) + 1,
                    "matched": m.group(0),
                    "model_id": entry.get("model_id"),
                    "replacement": entry.get("replacement"),
                    "retirement": entry.get("retirement"),
                    "label": label,
                    "severity": SEV_INERT if inert_rule else severity,
                }
                if inert_rule:
                    hit["inert_rule"] = inert_rule
                hits.append(hit)
    return hits


def summarize(hits: List[Dict]) -> Dict[str, int]:
    summary = {"breaks": 0, "warns": 0, "info": 0, "inert": 0,
               "total": len(hits)}
    for hit in hits:
        sev = hit["severity"]
        if sev == SEV_BREAK:
            summary["breaks"] += 1
        elif sev == SEV_WARN:
            summary["warns"] += 1
        elif sev == SEV_INERT:
            summary["inert"] += 1
        else:
            summary["info"] += 1
    return summary


def _format_hit(hit: Dict) -> str:
    if hit["severity"] == SEV_INERT:
        tag = "INERT:%s" % hit.get("inert_rule", "?")
    else:
        tag = "%s/%s" % (hit["severity"], hit["label"])
    extra = ""
    if hit["severity"] in (SEV_BREAK, SEV_WARN) and hit.get("replacement"):
        extra = "  (-> %s)" % hit["replacement"]
    return "   [%s] %s:%d  %s%s" % (
        tag, hit["path"], hit["line"], hit["matched"], extra)


def _resolve_today(raw: Optional[str]) -> datetime.date:
    if raw:
        parsed = parse_iso_date(raw)
        if parsed is not None:
            return parsed
        _advisory("--today %r unparseable — falling back to the real date "
                  "(fail-open)" % raw)
    return datetime.date.today()


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="check-model-deprecations.py",
        description="Scan directory trees for deprecated/retiring Claude "
                    "model ids (ledger-driven; S230 sweep made permanent).")
    parser.add_argument("roots", nargs="*",
                        help="directories to scan (default: "
                             "$CEO_DEPRECATION_SCAN_ROOTS, else this repo)")
    parser.add_argument("--json", action="store_true", dest="as_json",
                        help="emit a machine-readable JSON report")
    parser.add_argument("--check", action="store_true",
                        help="exit 1 if any non-inert BREAK or <=warn-days "
                             "WARN hit exists (else 0)")
    parser.add_argument("--today", default=None, metavar="YYYY-MM-DD",
                        help="inject 'today' for deterministic runs/tests")
    parser.add_argument("--ledger", default=DEFAULT_LEDGER_PATH,
                        help="ledger path (default: sidecar "
                             "model-deprecations.json)")
    parser.add_argument("--warn-days", type=int, default=WARN_DAYS_DEFAULT,
                        help="WARN window in days before retirement "
                             "(default: %(default)s)")
    args = parser.parse_args(argv)

    today = _resolve_today(args.today)
    ledger = load_ledger(args.ledger)
    if ledger is None:
        _advisory("ledger missing/corrupt at %s — deprecation check skipped "
                  "(fail-open, exit 0)" % args.ledger)
        if args.as_json:
            print(json.dumps({"schema": 1, "fail_open": True,
                              "error": "ledger_missing_or_corrupt",
                              "ledger": args.ledger}, indent=1))
        else:
            print("LIVE-BREAKS-REMAINING: UNKNOWN (ledger unavailable)")
        return 0

    pattern, literal_map = build_matcher(ledger)
    if pattern is None:
        _advisory("ledger has no usable model entries — nothing to scan "
                  "(fail-open, exit 0)")
        return 0
    inert_rules = compile_inert_rules(ledger)
    roots = resolve_roots(args.roots, os.environ.get(ENV_SCAN_ROOTS))
    meta = ledger.get("_meta") if isinstance(ledger.get("_meta"), dict) else {}
    source_stale = bool(meta.get("source_stale", False))

    all_hits: List[Dict] = []
    scanned_roots: List[str] = []
    skipped_roots: List[str] = []
    for root in roots:
        if not os.path.isdir(root):
            skipped_roots.append(root)
            if not args.as_json:
                print("-- skip (missing): %s" % root)
            continue
        scanned_roots.append(root)
        root_hits = scan_root(root, pattern, literal_map, inert_rules,
                              today, args.warn_days)
        all_hits.extend(root_hits)
        if not args.as_json:
            print("== %s: %d hit(s)" % (root, len(root_hits)))
            for hit in root_hits[:MAX_DISPLAY_PER_ROOT]:
                print(_format_hit(hit))
            if len(root_hits) > MAX_DISPLAY_PER_ROOT:
                print("   ... +%d more" %
                      (len(root_hits) - MAX_DISPLAY_PER_ROOT))

    summary = summarize(all_hits)
    if args.as_json:
        print(json.dumps({
            "schema": 1,
            "today": today.isoformat(),
            "warn_days": args.warn_days,
            "ledger": args.ledger,
            "source_stale": source_stale,
            "ledger_fetched": meta.get("fetched"),
            "roots": scanned_roots,
            "roots_skipped": skipped_roots,
            "summary": summary,
            "hits": all_hits,
        }, indent=1))
    else:
        if source_stale:
            _advisory("ledger metadata says source_stale=true — refresh it "
                      "from the official deprecations page")
        print("")
        print("SUMMARY: breaks=%d warns=%d info=%d inert=%d total=%d "
              "(today=%s, warn_days=%d, source_stale=%s)" % (
                  summary["breaks"], summary["warns"], summary["info"],
                  summary["inert"], summary["total"], today.isoformat(),
                  args.warn_days, str(source_stale).lower()))
        # S230 postfix evidence convention — ALWAYS the final line.
        print("LIVE-BREAKS-REMAINING: %d" % summary["breaks"])

    if args.check and (summary["breaks"] > 0 or summary["warns"] > 0):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
