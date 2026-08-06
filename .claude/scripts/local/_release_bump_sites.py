#!/usr/bin/env python3
# ============================================================================
# _release_bump_sites.py — the ONE source of truth for the release version
# sites, and the only writer of them.
#
# Why a module and not a heredoc. Until PLAN-166/W0 this table lived inside
# `release.sh` as a `python3 - <<'PY'` heredoc. That had two costs that both
# showed up in the v1.3.0-rc.1 re-pass:
#
#   1. the site list existed TWICE — once in the heredoc (the writer) and once
#      in the driver's `VERSION_FILES` array (the dry-run restore list). A list
#      that must match another list by hand does not stay matched; a restore
#      list shorter than the write list leaves debris (the S273 class).
#   2. it was untestable. `--today` could not be pinned, so the D+1
#      non-idempotence (F2) could not be exercised by a test.
#
# Both are closed here: the driver DERIVES its restore list from
# `print-sites --include-generated`, and `--today` is a REQUIRED parameter with
# NO DEFAULT (a parameter that changes the verdict never has a default —
# frozen-evidence lesson).
#
# Idempotence contract (F2). A `last-reviewed:` stamp asserts "this document
# was re-read FOR THIS RELEASE". Re-dating it without re-reading is a false
# claim on a surface that a signed tag then covers. So the four stamp sites
# skip the ENTIRE line — neither date nor version — when the version already
# on the stamp is the target. `--restamp` is the named, explicit route for a
# real re-review.
#
# The two stamp oracles (do not collapse them). `npm/README.md` is watched by
# verify-counts' VERSION_SITES; SBOM.md / SECURITY.md / VERSIONING.md are
# watched ONLY by check-canonical-doc-freshness.py. Both oracles decide on the
# VERSION in the stamp, never on the date — which is what makes freezing the
# date safe.
#
# The support window (kinds "minor"/"prev_minor" — v1.3.0 re-pass, F-sites).
# verify-counts' VERSION_SITES also watches "Current MINOR (vX.Y.x)" and
# "Previous MINOR (vX.Y.x)" in SECURITY.md and VERSIONING.md (S293). Those
# sites were OUTSIDE this table at birth, so the next MINOR bump would write
# everything else, then DIE at the driver's own verify-counts call with a
# half-written tree (outside --dry-run there is no restore trap). The rule the
# oracle enforces is mechanical — Current = the target's minor, Previous = the
# minor immediately before it — so this writer derives both from --target and
# the "ONE source of truth" claim above stays true. The single non-derivable
# case, an X.0.0 target, is SKIPPED loudly and never guessed: the oracle
# cannot value-check it either (it derives prev="" at X.0), and a MAJOR
# support-window transition is release-train judgment, not sed.
# ============================================================================
"""Release version-site table + writer (stdlib only, Python >= 3.9)."""

from __future__ import annotations

import argparse
import os
import re
import sys
from typing import Callable, List, Optional, Sequence, Tuple

SEMVER = r"\d+\.\d+\.\d+"
STAMP_RX = r"(last-reviewed: )(\d{4}-\d{2}-\d{2})( +v)(" + SEMVER + r")"
DATE_RX = re.compile(r"\A\d{4}-\d{2}-\d{2}\Z")

# Kinds:
#   "plain"      — literal regex substitution, no stamp semantics.
#   "stamp"      — "last-reviewed: <date> v<version>"; skipped wholesale when
#                  the version already equals the target (unless --restamp).
#   "minor"      — support-window site carrying the TARGET's minor (vX.Y.x).
#   "prev_minor" — support-window site carrying the minor immediately BEFORE
#                  the target; not derivable at X.0.0 (skipped loudly there).
PLAIN = "plain"
STAMP = "stamp"
MINOR = "minor"
PREV_MINOR = "prev_minor"

# (path, kind, pattern) — patterns anchored exactly as their oracle checks
# them, so historical version mentions elsewhere in the file are never touched.
_SITES: List[Tuple[str, str, str]] = [
    ("VERSION", PLAIN, r"\A\s*" + SEMVER + r"\s*\Z"),
    ("npm/package.json", PLAIN, r'("version"\s*:\s*")' + SEMVER + r'(")'),
    ("pyproject.toml", PLAIN, r'(?m)^(version\s*=\s*")' + SEMVER + r'(")'),
    ("INSTALL.md", PLAIN, r"(--pin v)" + SEMVER),
    (
        "docs/ARCHITECTURE.md",
        PLAIN,
        r"(currently\s+v)" + SEMVER + r"(, aligned with the repo)",
    ),
    # Present in the watched list but currently carries no such literal; a zero
    # match here is fine — verify-counts is the oracle, not this table.
    ("README.md", PLAIN, r"(VERSION=)" + SEMVER),
    ("SBOM.md", PLAIN, r"(\*\*Version:\*\* `)" + SEMVER + r"(`)"),
    # --- the support window (oracle: verify-counts VERSION_SITES modes
    #     "minor"/"prev_minor", S293). Patterns anchored exactly as the
    #     oracle's — SECURITY.md bolds the label, VERSIONING.md does not. ---
    ("SECURITY.md", MINOR, r"(\*\*Current MINOR\*\* \(`v)\d+\.\d+(\.x`\))"),
    ("VERSIONING.md", MINOR, r"(Current MINOR \(`v)\d+\.\d+(\.x`\))"),
    ("SECURITY.md", PREV_MINOR, r"(\*\*Previous MINOR\*\* \(`v)\d+\.\d+(\.x`\))"),
    ("VERSIONING.md", PREV_MINOR, r"(Previous MINOR \(`v)\d+\.\d+(\.x`\))"),
    # --- the four review stamps (idempotence-critical) ---
    ("npm/README.md", STAMP, STAMP_RX),
    ("SBOM.md", STAMP, STAMP_RX),
    ("SECURITY.md", STAMP, STAMP_RX),
    ("VERSIONING.md", STAMP, STAMP_RX),
]

# Written by the bump PHASE but not by this module: `build-plugin.py
# --write-manifests` regenerates them from VERSION. They belong in any
# derived restore/guard list, which is why they are exported here instead of
# being re-typed by every caller (the duplicated-list failure this module
# exists to kill).
GENERATED_BY_BUMP: List[str] = [
    ".claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json",
]


def site_paths(include_generated: bool = False) -> List[str]:
    """Every path this module may write, de-duplicated, in table order."""
    out: List[str] = []
    for path, _kind, _rx in _SITES:
        if path not in out:
            out.append(path)
    if include_generated:
        for path in GENERATED_BY_BUMP:
            if path not in out:
                out.append(path)
    return out


def _plain_replacement(pattern: str, target: str) -> str:
    """Replacement string for a PLAIN site, rebuilt from its group count."""
    if pattern.startswith(r"\A"):  # the bare VERSION file
        return target + "\n"
    groups = re.compile(pattern).groups
    if groups == 0:
        return target
    if groups == 1:
        return r"\g<1>" + target
    return r"\g<1>" + target + r"\g<2>"


def _stamp_replacer(
    target: str, today: str, restamp: bool
) -> Callable[["re.Match"], str]:
    def _repl(m: "re.Match") -> str:
        if not restamp and m.group(4) == target:
            # Defense in depth: the whole line is left byte-identical. Both
            # stamp oracles read the VERSION, so freezing the date costs
            # nothing and re-dating without re-reading would be a false claim.
            return m.group(0)
        return m.group(1) + today + m.group(3) + target

    return _repl


def bump(
    target: str,
    today: str,
    *,
    restamp: bool = False,
    root: Optional[str] = None,
    out=None,
) -> int:
    """Rewrite every version site to `target`. Returns files CHANGED."""
    if not DATE_RX.match(today):
        raise ValueError("--today must be YYYY-MM-DD, got %r" % (today,))
    if not re.match(r"\A" + SEMVER + r"\Z", target):
        raise ValueError("--target must be a bare semver, got %r" % (target,))
    stream = out if out is not None else sys.stdout
    base = root or os.getcwd()
    # Support-window derivation, BEFORE any byte is written: whether every
    # site is writable is decided up front, never discovered mid-loop with a
    # half-bumped tree behind it.
    _maj, _min = (int(x) for x in target.split(".")[:2])
    minor_target = "%d.%d" % (_maj, _min)
    prev_minor = "%d.%d" % (_maj, _min - 1) if _min > 0 else None
    changed = 0
    for path, kind, pattern in _SITES:
        if kind == PREV_MINOR and prev_minor is None:
            # X.0.0: Previous MINOR is not derivable from the target, and the
            # oracle skips value-checking it there too (prev="" at X.0). Never
            # guess a support-window promise — leave it and say so, loudly.
            print(
                "  !!   %s: Previous MINOR left untouched — not derivable "
                "from %s (X.0.0); the support window needs release-train "
                "judgment here" % (path, target),
                file=stream,
            )
            continue
        full = os.path.join(base, path)
        try:
            with open(full, encoding="utf-8") as fh:
                src = fh.read()
        except OSError:
            print("  --   %s absent, skipped" % path, file=stream)
            continue
        written = target
        if kind == STAMP:
            new, n = re.subn(pattern, _stamp_replacer(target, today, restamp), src)
            label = "review stamp"
        elif kind == MINOR:
            written = minor_target
            new, n = re.subn(pattern, r"\g<1>" + written + r"\g<2>", src)
            label = "support-window (Current MINOR) site"
        elif kind == PREV_MINOR:
            written = prev_minor
            new, n = re.subn(pattern, r"\g<1>" + written + r"\g<2>", src)
            label = "support-window (Previous MINOR) site"
        else:
            new, n = re.subn(pattern, _plain_replacement(pattern, target), src)
            label = "version site"
        if n == 0:
            print(
                "  --   %s: no %s found (ok if unwatched)" % (path, label),
                file=stream,
            )
            continue
        if new == src:
            print(
                "  --   %s: %s already at %s (line untouched)"
                % (path, label, written),
                file=stream,
            )
            continue
        with open(full, "w", encoding="utf-8") as fh:
            fh.write(new)
        changed += 1
        print(
            "  ok   %s (%d %s%s -> %s)"
            % (path, n, label, "" if n == 1 else "s", written),
            file=stream,
        )
    return changed


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="_release_bump_sites.py",
        description="Release version-site table + writer (single source).",
    )
    sub = parser.add_subparsers(dest="cmd")

    p_list = sub.add_parser(
        "print-sites",
        help="print every path the bump may write, one per line",
    )
    p_list.add_argument(
        "--include-generated",
        action="store_true",
        help="also print the plugin manifests regenerated by build-plugin.py",
    )

    p_bump = sub.add_parser("bump", help="rewrite the version sites")
    # NO DEFAULT, BY CONTRACT. `--today` decides whether a signed
    # "last-reviewed" claim moves; a parameter that changes the verdict is
    # never defaulted (frozen-evidence lesson).
    p_bump.add_argument("--today", required=True, help="YYYY-MM-DD (required)")
    p_bump.add_argument("--target", required=True, help="bare semver, e.g. 1.3.0")
    p_bump.add_argument(
        "--restamp",
        action="store_true",
        help="force the review stamps to move even at the same version",
    )
    p_bump.add_argument("--root", default=None, help="repo root (default: cwd)")

    args = parser.parse_args(argv)
    if args.cmd == "print-sites":
        for path in site_paths(include_generated=args.include_generated):
            print(path)
        return 0
    if args.cmd == "bump":
        try:
            bump(
                args.target,
                args.today,
                restamp=args.restamp,
                root=args.root,
            )
        except ValueError as exc:
            print("FAIL: %s" % exc, file=sys.stderr)
            return 2
        return 0
    parser.print_usage(sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
