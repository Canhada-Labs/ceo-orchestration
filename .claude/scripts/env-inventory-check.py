#!/usr/bin/env python3
"""env-inventory-check.py — consumed-env-var drift checker (PLAN-135 W5 O8).

The S218 footgun class made a permanent instrument: a single env var set
outside the reviewed surface (`CLAUDE_CODE_SUBAGENT_MODEL=haiku`, removed in
S218/ADR-144) silently re-routed every subagent for weeks. This script keeps
ONE canonical inventory of the `CLAUDE_*` / `ANTHROPIC_*` / `CEO_*` names the
framework's code references, and diffs the live tree against it so any NEW
name (an unreviewed env surface) or VANISHED name (stale inventory) surfaces
in the nightly-hygiene sweep (dimension vi) instead of in a future incident.

Semantics (documented honest boundary): the scan collects every matching
TOKEN in framework code files — a superset of strictly-consumed vars (a
constant or docstring mention counts). That over-inclusion is deliberate:
drift detection cares about names ENTERING or LEAVING the reviewed surface,
and token-level scanning is deterministic where "is this line really a read?"
heuristics are not.

Scan scope: code files (.py .sh .js .json) under the framework's live roots,
excluding tests/, fixtures/, archived + generated trees, and .claude/plans/
(experiment code is not framework surface). settings JSON files are included
because their `env` blocks are a settings-set env channel (threat-model §2).

Inventory: `.claude/scripts/env-inventory.json` (same dir). Regenerate with
`--generate` after any REVIEWED env-surface change.

Exit codes:
  0 — report mode (always), or --check with zero drift, or infra fail-open
      (corrupt inventory: advisory + exit 0)
  1 — --check only: drift found (new or stale names), or inventory MISSING
      (the inventory file is part of the contract, not infra)
  2 — CLI usage error (argparse)

Wired as: 6th read-only agent input of the `nightly-hygiene` saved workflow
(--json mode). Stdlib-only. Python >= 3.9. Read-only except --generate
(which writes ONLY the inventory file); emits NO audit events (must stay
runnable under ADR-136-AMEND-1 read-only confinement).
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
from typing import Dict, List, Optional, Set

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_INVENTORY_PATH = os.path.join(SCRIPT_DIR, "env-inventory.json")
# .claude/scripts/env-inventory-check.py -> repo root is parents[2]
REPO_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, os.pardir, os.pardir))

SCHEMA_VERSION = "1.0"

#: Var-name shape: prefix + body that ENDS alphanumeric, so concatenation
#: fragments like `"CEO_AUDIT_" + name` never enter the inventory.
TOKEN_RE = re.compile(r"\b(?:CLAUDE|ANTHROPIC|CEO)_[A-Z0-9_]*[A-Z0-9]\b")

#: Framework surface roots, relative to the repo root.
SCAN_ROOTS = (
    ".claude/hooks",
    ".claude/scripts",
    ".claude/workflows",
    ".claude/commands",
    ".claude/settings.json",
    "scripts",
    "templates",
)

SCAN_EXTENSIONS = (".py", ".sh", ".js", ".json")

#: Directory basenames pruned everywhere (check-model-deprecations parity +
#: test/fixture trees — tests mint synthetic CEO_* names by design).
SKIP_DIRS = {
    "tests", "fixtures", "perf", "__pycache__", ".pytest_cache",
    "_lib_archived", "node_modules", ".git", "htmlcov", "coverage",
    ".venv", "venv", "dist", "build",
}

MAX_BYTES = 2_000_000


def _advisory(msg: str) -> None:
    sys.stderr.write("[env-inventory-check] advisory: %s\n" % msg)


def scan_consumed(repo_root: str = REPO_ROOT) -> Dict[str, List[str]]:
    """Scan the framework surface; return {var_name: sorted [relpath, ...]}.

    Deterministic: roots in declared order, os.walk sorted, evidence paths
    sorted + deduplicated. Never raises — unreadable files are skipped with
    an advisory.
    """
    found: Dict[str, Set[str]] = {}

    def _scan_file(path: str) -> None:
        rel = os.path.relpath(path, repo_root)
        try:
            if os.path.getsize(path) > MAX_BYTES:
                return
            with open(path, "rb") as fh:
                text = fh.read().decode("utf-8", errors="ignore")
        except OSError as exc:
            _advisory("unreadable %s (%s)" % (rel, exc.__class__.__name__))
            return
        for name in TOKEN_RE.findall(text):
            found.setdefault(name, set()).add(rel)

    for root in SCAN_ROOTS:
        target = os.path.join(repo_root, root)
        if os.path.isfile(target):
            if target.endswith(SCAN_EXTENSIONS):
                _scan_file(target)
            continue
        if not os.path.isdir(target):
            continue
        for dirpath, dirnames, filenames in os.walk(target):
            dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIRS)
            for fname in sorted(filenames):
                if fname.endswith(SCAN_EXTENSIONS):
                    _scan_file(os.path.join(dirpath, fname))

    return {name: sorted(paths) for name, paths in sorted(found.items())}


def load_inventory(path: str) -> Optional[Dict]:
    """Load the inventory JSON. None on missing/corrupt (caller decides)."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        _advisory("corrupt inventory %s (%s)" % (path, exc.__class__.__name__))
        return None
    if not isinstance(data, dict) or not isinstance(data.get("vars"), dict):
        _advisory("inventory %s has no usable `vars` object" % path)
        return None
    return data


def build_inventory(consumed: Dict[str, List[str]], today: str) -> Dict:
    """Build a fresh inventory document from a scan result."""
    return {
        "schema_version": SCHEMA_VERSION,
        "_comment": (
            "Canonical inventory of CLAUDE_*/ANTHROPIC_*/CEO_* names referenced "
            "by framework code (PLAN-135 W5 O8 — the S218 footgun class). "
            "Token-level superset of strictly-consumed vars; see "
            "env-inventory-check.py docstring. Regenerate with --generate "
            "after any REVIEWED env-surface change."
        ),
        "generated_by": "env-inventory-check.py --generate",
        "generated_at": today,
        "scan_roots": list(SCAN_ROOTS),
        "vars": {
            name: {"evidence": paths[:3], "sites": len(paths)}
            for name, paths in consumed.items()
        },
    }


def diff_inventory(consumed: Dict[str, List[str]], inventory: Dict) -> Dict:
    """Diff a live scan against the inventory. Returns the report dict."""
    inventoried = set(inventory.get("vars", {}))
    live = set(consumed)
    new = sorted(live - inventoried)
    stale = sorted(inventoried - live)
    return {
        "status": "drift" if (new or stale) else "clean",
        "new": [
            {"name": n, "evidence": consumed[n][:3], "sites": len(consumed[n])}
            for n in new
        ],
        "stale": [{"name": n} for n in stale],
        "counts": {
            "live": len(live),
            "inventoried": len(inventoried),
            "new": len(new),
            "stale": len(stale),
        },
    }


def render_human(report: Dict, inventory_path: str) -> str:
    out: List[str] = []
    out.append("# env-inventory-check — %s" % report["status"].upper())
    out.append("inventory: %s" % inventory_path)
    c = report["counts"]
    out.append(
        "live=%d inventoried=%d new=%d stale=%d"
        % (c["live"], c["inventoried"], c["new"], c["stale"])
    )
    for row in report["new"]:
        out.append(
            "NEW   %s  (%d site(s); e.g. %s)"
            % (row["name"], row["sites"], "; ".join(row["evidence"]))
        )
    for row in report["stale"]:
        out.append("STALE %s  (inventoried but no longer referenced)" % row["name"])
    out.append("ENV-DRIFT: %d" % (c["new"] + c["stale"]))
    return "\n".join(out)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="consumed CLAUDE_*/ANTHROPIC_*/CEO_* env-var drift checker"
    )
    parser.add_argument("--inventory", default=DEFAULT_INVENTORY_PATH,
                        help="inventory JSON path (default: env-inventory.json)")
    parser.add_argument("--repo-root", default=REPO_ROOT,
                        help="repo root to scan (default: this checkout)")
    parser.add_argument("--generate", action="store_true",
                        help="write a fresh inventory from the live scan")
    parser.add_argument("--check", action="store_true",
                        help="exit 1 on drift or missing inventory")
    parser.add_argument("--json", action="store_true", help="emit JSON report")
    args = parser.parse_args(argv)

    consumed = scan_consumed(args.repo_root)

    if args.generate:
        today = datetime.date.today().isoformat()
        doc = build_inventory(consumed, today)
        try:
            with open(args.inventory, "w", encoding="utf-8") as fh:
                json.dump(doc, fh, indent=2, sort_keys=False, ensure_ascii=False)
                fh.write("\n")
        except OSError as exc:
            sys.stderr.write("env-inventory-check: cannot write %s (%s)\n"
                             % (args.inventory, exc.__class__.__name__))
            return 2
        print("wrote %s (%d vars)" % (args.inventory, len(consumed)))
        return 0

    inventory = load_inventory(args.inventory)
    if inventory is None:
        missing = not os.path.exists(args.inventory)
        report = {
            "status": "no-inventory" if missing else "corrupt-inventory",
            "new": [], "stale": [],
            "counts": {"live": len(consumed), "inventoried": 0,
                       "new": 0, "stale": 0},
        }
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            print("# env-inventory-check — %s" % report["status"].upper())
            print("inventory: %s" % args.inventory)
            print("run: python3 .claude/scripts/env-inventory-check.py --generate")
            print("ENV-DRIFT: unknown")
        if args.check and missing:
            return 1  # the inventory file is part of the contract
        return 0      # corrupt = infra → fail-open advisory (exit 0)

    report = diff_inventory(consumed, inventory)
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(render_human(report, args.inventory))
    if args.check and report["status"] == "drift":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
