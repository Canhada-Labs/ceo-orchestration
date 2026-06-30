#!/usr/bin/env python3
"""check-canonical-doc-freshness.py — PLAN-112-FOLLOWUP-canonical-doc-refresh-gate.

Release gate that fails when a canonical doc's machine-readable
`last-reviewed` stamp is more MINOR releases behind the live VERSION than
its tier allows. Closes F-D4 (canonical docs drift stale with nothing in
CI to catch it).

## Stamp convention (W1)

A single grep-friendly HTML-comment line near the top of each in-scope doc:

    <!-- last-reviewed: 2026-05-24 v1.43.0 -->

HTML-comment form chosen for: grep-friendliness, no YAML-structure risk,
portability across CommonMark renderers, and invisibility in rendered docs.

## Tier map + thresholds

A doc FAILS when (MINOR releases behind the live VERSION) > its tier
threshold:

    security-critical  (N=1): SECURITY.md, VERSIONING.md, SBOM.md
    general            (N=3): README.md, INSTALL.md, SUPPORT.md,
                              .claude/adr/README.md

PROTOCOL.pt-BR.md is EXCLUDED — its sync stamp is owned by
PLAN-112-FOLLOWUP-protocol-en-semver-sync.

Bootstrap: a doc stamped at the current VERSION is 0 behind → fresh. The
gate only bites once a doc falls far enough behind (first meaningful
enforcement on v1.44.0+).

## Fail-closed

A doc with a MISSING or MALFORMED stamp FAILS-CLOSED (not skip) with an
explicit message. A newly-added canonical doc without a stamp therefore
fails the gate — a naive `stamp or continue` would make the gate theater.

## Emergency bypass (logged, never silent)

Set `CEO_DOC_FRESHNESS_WAIVER=<reason>` to bypass with a logged warning.
release.yml exports it from an Owner-signed `doc_freshness:` entry in
`.claude/governance/governance-waivers.yaml` for the release version (same
pattern as the RC-hold waiver). The checker also reads that file directly
when present.

## Usage

    python3 .claude/scripts/check-canonical-doc-freshness.py
    python3 .claude/scripts/check-canonical-doc-freshness.py --json
    python3 .claude/scripts/check-canonical-doc-freshness.py --repo-root <path>

Exit 0 fresh (or waived) / 1 stale-or-malformed-or-missing.

## Stdlib-only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Dict, List, Optional, Tuple

# Doc -> tier threshold (MINOR-releases-behind allowed before failing).
DOC_TIERS: Dict[str, int] = {
    "SECURITY.md": 1,
    "VERSIONING.md": 1,
    "SBOM.md": 1,
    "README.md": 3,
    "INSTALL.md": 3,
    "SUPPORT.md": 3,
    ".claude/adr/README.md": 3,
}

STAMP_RE = re.compile(
    r"<!--\s*last-reviewed:\s*(\d{4}-\d{2}-\d{2})\s+v(\d+)\.(\d+)\.(\d+)\s*-->"
)
VERSION_RE = re.compile(r"^\s*(\d+)\.(\d+)\.(\d+)")


def parse_version(text: str) -> Optional[Tuple[int, int, int]]:
    m = VERSION_RE.match(text.strip())
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)), int(m.group(3)))


def minor_releases_behind(
    cur: Tuple[int, int, int], stamp: Tuple[int, int, int]
) -> int:
    """How many MINOR releases the stamp is behind the current VERSION.

    MAJOR bumps count as a large jump (1000 minors) so a stale-across-major
    doc always trips. A stamp at or ahead of current returns <= 0.
    """
    cur_major, cur_minor, _ = cur
    st_major, st_minor, _ = stamp
    return (cur_major - st_major) * 1000 + (cur_minor - st_minor)


def waiver_active(repo_root: str, version_str: str) -> Optional[str]:
    """Return a waiver reason if bypass is authorized, else None.

    Primary: CEO_DOC_FRESHNESS_WAIVER env (release.yml exports it).
    Fallback: a `doc_freshness:` list entry in governance-waivers.yaml whose
    `- version:` matches the release version (line-scan, mirroring the awk
    flag-based parse the release.yml gates use).
    """
    env = (os.environ.get("CEO_DOC_FRESHNESS_WAIVER") or "").strip()
    if env:
        return f"env CEO_DOC_FRESHNESS_WAIVER={env}"

    waivers = os.path.join(repo_root, ".claude", "governance", "governance-waivers.yaml")
    try:
        with open(waivers, encoding="utf-8") as fh:
            in_section = False
            for line in fh:
                if re.match(r"^doc_freshness:\s*$", line):
                    in_section = True
                    continue
                if in_section and re.match(r"^[a-z_]+:\s*$", line):
                    break  # next top-level key ends the section
                if in_section and re.match(
                    r"^\s*-\s*version:\s*" + re.escape(version_str) + r"\s*$", line
                ):
                    return f"governance-waivers.yaml doc_freshness: {version_str}"
    except OSError:
        pass
    return None


def check(repo_root: str) -> Tuple[List[dict], Tuple[int, int, int], str]:
    """Return (results, cur_version_tuple, version_str)."""
    with open(os.path.join(repo_root, "VERSION"), encoding="utf-8") as fh:
        version_str = fh.read().strip()
    cur = parse_version(version_str)
    if cur is None:
        raise SystemExit(f"FATAL: unparseable VERSION: {version_str!r}")

    results: List[dict] = []
    for rel, threshold in DOC_TIERS.items():
        path = os.path.join(repo_root, rel)
        entry: dict = {"doc": rel, "threshold": threshold, "status": "ok"}
        try:
            text = open(path, encoding="utf-8").read()
        except OSError:
            entry.update(status="missing-file",
                         detail=f"{rel} not found on disk (fail-closed)")
            results.append(entry)
            continue

        m = STAMP_RE.search(text)
        if not m:
            if "last-reviewed" in text:
                entry.update(status="malformed-stamp",
                             detail=f"{rel} has a 'last-reviewed' token but it does "
                                    f"not match `<!-- last-reviewed: YYYY-MM-DD vX.Y.Z -->` "
                                    f"(fail-closed)")
            else:
                entry.update(status="absent-stamp",
                             detail=f"{rel} has no last-reviewed stamp (fail-closed)")
            results.append(entry)
            continue

        stamp = (int(m.group(2)), int(m.group(3)), int(m.group(4)))
        behind = minor_releases_behind(cur, stamp)
        entry.update(stamp_date=m.group(1),
                     stamp_version=f"{stamp[0]}.{stamp[1]}.{stamp[2]}",
                     minor_behind=behind)
        if behind > threshold:
            entry.update(status="stale",
                         detail=f"{rel} stamped v{stamp[0]}.{stamp[1]}.{stamp[2]} is "
                                f"{behind} MINOR release(s) behind v{version_str} "
                                f"(tier allows {threshold})")
        results.append(entry)
    return results, cur, version_str


def main() -> int:
    ap = argparse.ArgumentParser(description="Canonical doc freshness gate")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--repo-root", default=None)
    args = ap.parse_args()

    repo_root = args.repo_root or os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    results, _cur, version_str = check(repo_root)
    failures = [r for r in results if r["status"] != "ok"]
    waiver = waiver_active(repo_root, version_str)

    if args.json:
        print(json.dumps(
            {"version": version_str, "results": results,
             "failures": [r["doc"] for r in failures],
             "waiver": waiver}, indent=2))
    else:
        print(f"=== canonical-doc-freshness gate (VERSION {version_str}) ===")
        for r in results:
            mark = "OK " if r["status"] == "ok" else "!! "
            extra = r.get("detail") or f"stamp v{r.get('stamp_version','?')} ({r.get('minor_behind','?')} behind, tier {r['threshold']})"
            print(f"  {mark}{r['doc']:28s} {r['status']:14s} {extra}")
        if failures:
            print("")
            print(f"{len(failures)} doc(s) stale/malformed/absent.")

    if failures:
        if waiver:
            # Logged + surfaced bypass — never a silent skip.
            msg = (f"::warning::canonical-doc-freshness gate BYPASSED via "
                   f"{waiver} ({len(failures)} doc(s) would fail: "
                   f"{', '.join(r['doc'] for r in failures)})")
            print(msg, file=sys.stderr)
            return 0
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
