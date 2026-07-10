#!/usr/bin/env python3
"""check-substrate-watch.py — Claude Code + Agent-SDK substrate drift watch.

PLAN-135 W5 unit o8o11o12 (O12). The heroic manual changelog sweeps (S214,
S230, and THIS plan's 8-dimension research pass) became a permanent nightly
instrument: a small read-only checker that compares the substrate version this
framework was last RECONCILED against (`.claude/scripts/substrate-watch.json`
`last_seen`) with the version actually installed locally — and surfaces the
fetch-the-upstream-changelog step as a PENDING-OWNER recipe (agents stay
no-network under ADR-136-AMEND-1; the doc fetch costs no model tokens but is
the one network action, so it is Owner-run by design).

A newer upstream/installed version is NOT a defect: it is a prompt to re-run
verify-the-knob-routes before trusting an assumption baked against an older
surface (the S217/S228 silent-knob class). Detection only; never a BREAK.

Semantics:
  - `last_seen.version == "unknown"` OR `_meta.source_stale == true`
      -> status "stale-ledger" (advisory): the ledger has never been Owner
         -refreshed against the live changelog. ONE finding, disposition=defer.
  - a code-registered probe (selected by the component's `key`, see
    `_PROBE_ARGV`) resolves an installed version that differs from
    `last_seen.version` -> status "drift": ONE finding per component
    (disposition=fix-or-defer; claim names old vs installed).
  - everything matches and the ledger is fresh -> status "current".

Probing is OPT-IN (`--probe-installed`): by default the checker does NOT run
any version command (zero side effects, suitable for the read-only nightly
agent which then reports the ledger state + recipe). With `--probe-installed`
it runs each component's CODE-DEFINED read-only version probe — the argv is
hardcoded in `_PROBE_ARGV`, keyed on the component `key`; the ledger can NEVER
supply a command (Codex R2 P0) — with a short timeout and fail-soft.

Exit codes:
  0 — report mode (always), or --check with a fresh ledger + no drift,
      or infra fail-open (missing/corrupt ledger: advisory + exit 0)
  1 — --check only: ledger stale OR drift detected (a maintenance signal,
      not infra failure)
  2 — CLI usage error (argparse)

PLAN-155 Wave 0 (debate A12) extended coverage to the Codex HOST-harness
substrate: the `codex_harness` ledger entry watches the codex-cli release
feed AND the developers.openai.com/codex/{hooks,config-reference,rules} doc
pages; both codex-keyed components now carry a code-defined version probe
(`codex --version`), and a detected codex drift attaches the code-registered
fixture re-record runbook (`_DRIFT_RUNBOOKS`): bump the pin via the ADR-111
ceremony FIRST, then re-record the Wave-1 adapter fixtures.

Stdlib-only. Python >= 3.9. Read-only (never writes; --refresh only PRINTS
the recipe, it does not fetch). Emits NO audit events.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess  # nosec B404 — read-only version probes, opt-in, fail-soft
import sys
from typing import Any, Dict, List, Optional, Tuple

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_LEDGER_PATH = os.path.join(SCRIPT_DIR, "substrate-watch.json")

_VERSION_RE = re.compile(r"(\d+\.\d+\.\d+(?:[-.][0-9A-Za-z.\-]+)?)")
_PROBE_TIMEOUT_S = 8.0

# Closed registry of version probes (PLAN-135 Codex R1/R2 P0). The full argv for
# each component — INCLUDING any `-e`/`-c` interpreter payload — is hardcoded HERE,
# keyed on the component's `key`. The ledger (and `--ledger <file>`) can only
# SELECT a key; it can NEVER supply the command. This closes the RCE class
# completely: an allowlist of argv[0] is insufficient because `python3`/`node`/
# `npx` are themselves arbitrary-code-execution vectors (`python3 -c <evil>`).
# Unknown key -> no probe. The ledger's descriptive `local_probe` (if present)
# is intentionally NOT executed; it is human documentation only.
_PROBE_ARGV: Dict[str, List[str]] = {
    "claude_code": ["claude", "--version"],
    "agent_sdk_ts": [
        "node", "-e",
        "console.log(require('@anthropic-ai/claude-agent-sdk/package.json').version)",
    ],
    "agent_sdk_py": [
        "python3", "-c",
        "import importlib.metadata as m; print(m.version('claude-agent-sdk'))",
    ],
    # PLAN-155 Wave 0 (debate A12): the Codex substrate is watched by TWO
    # ledger entries backed by the SAME read-only binary probe — `codex_cli`
    # (pair-rail reviewer flag-surface, PLAN-142 lineage; previously had no
    # probe registered) and `codex_harness` (Codex-as-HOST hooks/config/rules
    # schema surface, PLAN-155).
    "codex_cli": ["codex", "--version"],
    "codex_harness": ["codex", "--version"],
}

# Code-registered drift runbooks (PLAN-155 Wave 0, debate A12). Same posture
# as _PROBE_ARGV (Codex R2 P0): the ledger can only SELECT a component key —
# it can NEVER supply alert/procedure text of its own. When a component with
# a registered runbook drifts, the runbook is attached to that report row
# (`runbook`) and printed in text mode, so the alert names the exact
# re-record procedure instead of a bare version delta.
_CODEX_FIXTURE_RUNBOOK = (
    "codex-cli drift — fixture re-record runbook (PLAN-155 debate A12): do "
    "NOT re-record fixtures against the new binary directly. (1) bump the "
    "pin FIRST via the ADR-111 pin ceremony (codex-cli-pin.txt + "
    "codex-cli-binary-sha256.txt); (2) THEN re-record the PLAN-155 Wave-1 "
    "host-adapter fixtures under .claude/hooks/tests/fixtures/adapters/codex/ "
    "(each fixture carries _meta.codex_cli_version; the pin-range test stays "
    "RED until fixtures are re-recorded or explicitly waived); (3) run the "
    "per-bump re-verification checklist in ADR-161 (hook envelope schema, "
    "PreToolUse interception surface, /hooks trust-hash keying, SubagentStart "
    "continue:false, Stop decision:block, execpolicy prefix_rule syntax)."
)
_DRIFT_RUNBOOKS: Dict[str, str] = {
    "codex_cli": _CODEX_FIXTURE_RUNBOOK,
    "codex_harness": _CODEX_FIXTURE_RUNBOOK,
}


def load_ledger(path: str) -> Optional[Dict[str, Any]]:
    """Read the substrate-watch ledger. None on any failure (fail-open)."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        if not isinstance(data, dict):
            return None
        return data
    except (OSError, ValueError):
        return None


def _extract_version(text: str) -> Optional[str]:
    """First semver-ish token in `text` (e.g. 'claude 1.2.3 (...)' -> '1.2.3')."""
    match = _VERSION_RE.search(text or "")
    return match.group(1) if match else None


def _run_version_cmd(argv: List[str]) -> subprocess.CompletedProcess:
    """Execute a registered version probe (shell=False). Test seam — unit tests
    patch THIS symbol to script probe output without touching a real binary."""
    return subprocess.run(  # nosec B603 — fixed argv from _PROBE_ARGV (code-defined, NOT ledger-controlled)
        argv,
        shell=False,
        capture_output=True,
        text=True,
        timeout=_PROBE_TIMEOUT_S,
    )


def _probe_installed(key: str) -> Tuple[Optional[str], str]:
    """Resolve the installed version for component ``key`` via its code-defined
    probe in ``_PROBE_ARGV``. Returns (version|None, note).

    The command is NEVER taken from ledger data (Codex R2 P0) — only the key
    selects which hardcoded argv runs. Fail-soft: an unregistered key, missing
    binary, non-zero exit, timeout, or unparseable output all degrade to
    (None, <reason>) — never raises.
    """
    argv = _PROBE_ARGV.get(key)
    if not argv:
        return None, "no probe registered for component %r" % key
    try:
        proc = _run_version_cmd(argv)
    except (subprocess.TimeoutExpired, OSError) as exc:
        return None, "probe unavailable (%s)" % type(exc).__name__
    if proc.returncode != 0:
        return None, "probe exit %d (not installed?)" % proc.returncode
    version = _extract_version((proc.stdout or "") + " " + (proc.stderr or ""))
    if version is None:
        return None, "probe ran but no version token parsed"
    return version, "ok"


def build_report(
    ledger: Optional[Dict[str, Any]],
    *,
    probe_installed: bool = False,
) -> Dict[str, Any]:
    """Pure-ish builder (the only impurity is the opt-in version probe).

    Returns a dict with: status, summary, source_stale, components[].
    NEVER raises.
    """
    if ledger is None:
        return {
            "schema": 1,
            "fail_open": True,
            "status": "current",
            "summary": "substrate-watch ledger missing/corrupt — advisory, "
            "treated as no-drift (run from the repo root; the ledger ships at "
            ".claude/scripts/substrate-watch.json)",
            "source_stale": False,
            "components": [],
        }

    meta = ledger.get("_meta") if isinstance(ledger.get("_meta"), dict) else {}
    source_stale = bool(meta.get("source_stale", False))
    components_in = ledger.get("components")
    components_in = components_in if isinstance(components_in, list) else []

    rows: List[Dict[str, Any]] = []
    any_drift = False
    any_unknown = False
    for comp in components_in:
        if not isinstance(comp, dict):
            continue
        last_seen = comp.get("last_seen") if isinstance(comp.get("last_seen"), dict) else {}
        seen_version = str(last_seen.get("version", "unknown"))
        row: Dict[str, Any] = {
            "key": comp.get("key", "?"),
            "label": comp.get("label", comp.get("key", "?")),
            "last_seen_version": seen_version,
            "last_seen_date": str(last_seen.get("date", "unknown")),
            "installed_version": None,
            "probe_note": "not probed (--probe-installed off)",
            "drift": False,
            "runbook": None,
        }
        if seen_version == "unknown":
            any_unknown = True
        if probe_installed:
            installed, note = _probe_installed(str(comp.get("key", "")))
            row["installed_version"] = installed
            row["probe_note"] = note
            if (
                installed is not None
                and seen_version != "unknown"
                and installed != seen_version
            ):
                row["drift"] = True
                any_drift = True
                # Attach the code-registered runbook (None-safe): the alert
                # names the fixture re-record procedure, not just the delta.
                row["runbook"] = _DRIFT_RUNBOOKS.get(str(comp.get("key", "")))
        rows.append(row)

    if source_stale or any_unknown:
        status = "stale-ledger"
        summary = (
            "substrate-watch ledger never Owner-refreshed against the live "
            "changelog (source_stale or last_seen=unknown) — PENDING-OWNER: %s"
            % str(meta.get("refresh_recipe", "run --refresh for the recipe"))
        )
    elif any_drift:
        status = "drift"
        drifted = [r["key"] for r in rows if r["drift"]]
        summary = "installed substrate differs from last-reconciled for: %s" % drifted
    else:
        status = "current"
        summary = "substrate reconciled — installed matches last_seen for all components"

    return {
        "schema": 1,
        "fail_open": False,
        "status": status,
        "summary": summary,
        "source_stale": source_stale,
        "components": rows,
    }


_REFRESH_RECIPE = """\
PENDING-OWNER substrate-watch refresh (no model tokens; one doc fetch each):
  For each component in .claude/scripts/substrate-watch.json:
    1. WebFetch the _meta.sources value for that key. A STRING is one
       URL; a LIST means fetch EACH URL in it (PLAN-155 A12: e.g.
       codex_harness = release feed + the three host-harness doc pages).
    2. Single-URL key: read the topmost version + release date on the
       page. LIST key: last_seen.version tracks the versioned feed (the
       first URL); the doc pages carry no version — record last_seen.date
       as the newest visible 'last updated' across ALL pages, and treat
       ANY observed change on a doc page as drift for that component
       EVEN IF the release feed shows no new version (docs-only schema
       drift is exactly the class this entry watches; on drift follow
       the component's registered runbook in _DRIFT_RUNBOOKS).
    3. Set components[key].last_seen.version + .date to those values.
    4. Set _meta.fetched to today and _meta.source_stale to false.
  This is Owner-run by design — the nightly agent stays no-network
  (ADR-136-AMEND-1). The fetch bills no model tokens; record nothing
  billable. After it lands, dimension vii reports 'current' until the
  next upstream release."""


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Claude Code + Agent-SDK substrate drift watch (PLAN-135 O12)."
    )
    parser.add_argument(
        "--ledger", default=DEFAULT_LEDGER_PATH,
        help="path to substrate-watch.json (default: alongside this script)",
    )
    parser.add_argument(
        "--json", action="store_true", dest="as_json",
        help="emit the JSON report (nightly-hygiene dimension vii consumes this)",
    )
    parser.add_argument(
        "--probe-installed", action="store_true", dest="probe_installed",
        help="opt-in: run each component's read-only version command (fail-soft)",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="exit 1 if the ledger is stale or drift is detected (maintenance signal)",
    )
    parser.add_argument(
        "--refresh", action="store_true",
        help="PRINT the PENDING-OWNER refresh recipe (does NOT fetch anything)",
    )
    args = parser.parse_args(argv)

    if args.refresh:
        print(_REFRESH_RECIPE)
        return 0

    ledger = load_ledger(args.ledger)
    report = build_report(ledger, probe_installed=args.probe_installed)

    if args.as_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print("substrate-watch: %s — %s" % (report["status"], report["summary"]))
        for row in report["components"]:
            installed = row["installed_version"] or "(not probed)"
            mark = "DRIFT" if row["drift"] else "ok"
            print(
                "  [%s] %-28s last_seen=%s installed=%s (%s)"
                % (mark, row["label"], row["last_seen_version"], installed, row["probe_note"])
            )
            if row["drift"] and row.get("runbook"):
                print("         runbook: %s" % row["runbook"])
        if report["status"] != "current":
            sys.stderr.write("advisory: run --refresh for the PENDING-OWNER recipe\n")

    if args.check and report["status"] in ("stale-ledger", "drift"):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
