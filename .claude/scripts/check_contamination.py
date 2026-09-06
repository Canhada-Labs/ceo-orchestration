#!/usr/bin/env python3
"""check_contamination.py — detect project-specific references outside allowlist.

Sprint 3 Item E.2. Port of check-contamination.sh to Python, using the
shared _lib.file_walker.FileWalker. Per debate consensus R-VP2, the
bash script remains as a thin wrapper that invokes this module so
Sprint 4+ can retire the wrapper cleanly.

## What it detects

NFKC-normalized regex match against a pattern built in TWO parts:

    (a) generic placeholder terms, hardcoded below in
        `_PLACEHOLDER_TERMS` — these ship to adopters as a working
        template; replace or extend them when forking.
    (b) PRIVATE terms, read at scan time from the SCANNED repo's
        `scripts/contamination-terms.txt` (see `_load_private_terms`).
        That file is deliberately OUTSIDE the install/upgrade manifest,
        so no maintainer identity is ever written into an adopter's
        checkout. An adopter may create the same file to guard THEIR
        own handle / private project names.

When the private file is absent the pattern is placeholder-only. That is
the EXPECTED adopter state, not a failure.

Files matching the pattern outside the allowlist fail the check.

## Allowlist

Exact paths + glob patterns (see `_ALLOWLIST_*` below). Binary file
suffixes are excluded by extension.

One NEGATIVE exception overrides the allowlist (deny wins over allow):
per-plan `LEDGER.md` / `LEDGER-ARCHIVE.md` files under `.claude/plans/`
are ALWAYS scanned, even though `.claude/plans/*` exempts the tree they
live in. See `is_never_allowlisted` for why. For that class alone, a file
that is not valid UTF-8 is REPORTED rather than skipped — unparseable
input is blocked, per the CLAUDE.md §4 security-matcher rule.

## Rule 2 — `personal-path`

A second, independent rule flags an absolute HOME directory
(`/Users/<name>/...`, `/home/<name>/...`, or the harness slug form
`-Users-<name>-...`) under `docs/` and `.claude/plans/` — the two
trees the term rule above exempts almost wholesale. It reports
`file:line` and never the matched line itself.

NOTHING is exempt by NAME or by SUFFIX: every in-scope tracked path
is read and matched the same way, symlinks included (a link is its
target string). Waivers act on a hit that was already found, and
are explicit: one `<path> | sha256:<64 hex> | <reason>` row in
`.claude/scripts/contamination-personal-path-allowlist.txt`, which
waives that file only while its bytes still hash to the recorded
digest. There is no second waiver and nothing is earned by a NAME:
a signed sentinel is waived by such a row like any other file.
See the RULE 2 block below for the full contract and its declared
blind spots.

## Exit codes

- 0 — clean
- 1 — contamination found (printed to stdout)
- 2 — fatal error (unreadable INPUT: the terms file, the
      personal-path allowlist, or an in-scope file that exists
      and cannot be read)
"""

from __future__ import annotations

import argparse
import errno
import hashlib
import os
import re
import stat
import subprocess
import sys
import time
import unicodedata
from pathlib import Path
from typing import Dict, List, NamedTuple, Optional, Tuple

# Import the shared walker from _lib/
_HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))
from _lib.file_walker import FileWalker  # noqa: E402


# Contamination tokens, in TWO parts — see the module docstring.
#
#   1. _PLACEHOLDER_TERMS (in code) — generic placeholders, shipped to
#      adopters as a working template.
#   2. Private terms loaded from _PRIVATE_TERMS_RELPATH inside the
#      SCANNED repo. They live outside the delivered tree because this
#      guard used to be its own contamination vector: it was the only
#      file in the install/upgrade manifest carrying the maintainer's
#      real name, and it survived CI by allowlisting
#      ITSELF. PLAN-183 W2 A7 removed both halves of that defect — the
#      identity moved out of the delivered file, and the self-exemption
#      was dropped from _ALLOWLIST_EXACT so this module is now scanned
#      by its own pattern.
#      Do NOT relocate the terms file under .claude/scripts/ — that tree
#      is delivered wholesale by upgrade.sh regardless of extension.
#
# Absent file => placeholder-only pattern, silently (the expected adopter
# state is not an infrastructure failure). A file that EXISTS but cannot
# be read is an INPUT failure and is surfaced as fatal by main().
_PLACEHOLDER_TERMS = (
    r"acme\s*[Ll]edger",
    r"example[\s._\-]*owner",
    r"Example\s+Owner",
)

_PRIVATE_TERMS_RELPATH = "scripts/contamination-terms.txt"


def _load_private_terms(repo_root: Path) -> List[str]:
    """Extra regex alternatives declared by the repo being scanned.

    Returns [] when the file is absent (normal in an adopter checkout).
    Propagates OSError when the file exists but cannot be read.
    """
    path = repo_root / _PRIVATE_TERMS_RELPATH
    if not path.is_file():
        return []
    terms: List[str] = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        terms.append(line)
    return terms


def build_pattern(repo_root: Path) -> "re.Pattern":
    """Placeholder terms plus any private terms declared by this repo.

    There is deliberately NO module-level constant holding the full
    pattern: a name that silently omits the private half is the exact
    false-green shape this indirection exists to remove.
    """
    alts = list(_PLACEHOLDER_TERMS) + _load_private_terms(repo_root)
    return re.compile("|".join(alts))

# Allowlist — mirrors the case block in check-contamination.sh
#
# Philosophy: the check defends the FRAMEWORK CORE (hooks, scripts,
# skills/core, skills/frontend, templates) from leaking project-specific
# references. It does NOT apply to:
#   - Historical decision records (ADRs carry Accepted-By owner handles)
#   - Plan artifacts (PLAN-*/ subfolders document adopter context)
#   - Adopter-facing documentation (docs/ explains framework to adopters)
#   - Adopter-specific tooling (check-originator-residue, compare-adopters,
#     adopter-metrics, log-friction — explicitly about adopter workflow)
#   - Published compliance contract (SPEC/v1/ references concrete examples)
#   - Benchmarks against named peers (benchmarks/public/vs-*.md)
#   - Case studies (docs/case-studies/ inherits adopter names by design)
#   - Issue templates (.github/ISSUE_TEMPLATE surfaces project context)
#   - Historical archives (CLAUDE_FULL.md is the overflow-log for CLAUDE.md)
_ALLOWLIST_EXACT = {
    "LICENSE",
    "CHANGELOG.md",
    # ---- S214: audit report + plugin builder reference identity tokens by-design ----
    "MORNING-REPORT-S214.md",   # CTO audit report that AUDITS the Owner-identity leak (must name the tokens)
    "REPORT-S225-fable-audit.md",  # S225 Fable audit: documents identity-leak findings (E5-F10, E7) — same rationale as MORNING-REPORT-S214
    "scripts/build-plugin.py",  # plugin builder: sanitize_paths()/identity_report() match these tokens to strip/report them
    "scripts/contamination-terms.txt",  # the private terms list itself — identity lives here BY DESIGN; never delivered (scripts/ contributes zero manifest files)
    ".github/workflows/validate.yml",
    ".github/CODEOWNERS",
    ".claude/scripts/check-contamination.sh",
    # NOTE: .claude/scripts/check_contamination.py is deliberately NOT
    # allowlisted. Self-exemption is what let the maintainer identity sit
    # inside this very file while CI reported green (PLAN-183 W2 A7). The
    # module is now scanned by its own pattern; if identity re-enters it,
    # the guard fails on itself.
    ".claude/scripts/tests/test_check_contamination.py",
    ".claude/hooks/tests/test_check_canonical_edit.py",
    "CLAUDE.md",
    "CLAUDE_FULL.md",
    "RELEASE.md",
    "SECURITY.md",
    "docs/QUICKSTART.md",
    "docs/QUICKSTART.pt-BR.md",
    "docs/GUIA-COMPLETO.md",
    "docs/GUIA-COMPLETO.pt-BR.md",
    "docs/HONEST-LIMITATIONS.md",
    "docs/ROADMAP-CLOSURE.md",
    "docs/threat-model.md",
    "docs/soc2-audit-mapping.md",
    "docs/fixture-budget.md",
    "docs/opus-4-7-baseline.md",
    "docs/opus-4-7-operations.md",
    "docs/opus-4-7-phase6-report.md",
    "docs/UPGRADE-PROCEDURE.md",
    "docs/SLO-SLA.md",
    ".claude/scripts/check-framework-updates.sh",
    ".claude/scripts/adopter-metrics.py",
    ".claude/scripts/compare-adopters.py",
    ".claude/scripts/check-originator-residue.py",
    ".claude/scripts/log-friction.sh",
    ".claude/scripts/tests/test_admin_invite.py",
    ".claude/scripts/tests/test_check_originator_residue.py",
    ".claude/scripts/tests/test_compare_adopters.py",
    ".claude/policies/.drift-manifest.json",
    # ---- audit-v2 Wave C-bis hot-fix (2026-04-27) ------------------
    # Pre-existing legitimate references to the Owner / canonical
    # repo URL surfaced after CLAUDE.md ADR-count drift was fixed
    # (which was masking these in CI). Each entry below is a
    # human-reviewed legitimate reference (Owner attribution in
    # ceremony scripts, GPG roster, design-intent github URLs, etc).
    # ----------------------------------------------------------------
    # Hook-lib files with Owner attribution in docstrings (canonical;
    # fix would require new sentinel ceremony — defer to future cleanup
    # ADR; allowlist now to unblock CI):
    ".claude/hooks/_lib/escalation_signals.py",
    ".claude/hooks/_lib/rag_events.py",
    ".claude/hooks/check_tier_policy.py",
    # Owner GPG fingerprint roster (by design — references Owner's key):
    ".claude/sentinel-signers.txt",
    ".claude/skill-patch-signers.txt",
    # Operational docs with design-intent github.com/<owner>/ URLs
    # (issue tracker, release page, etc.):
    "docs/READINESS-STATUS.md",
    "docs/CEO-MODEL-ROUTING.md",
    "docs/ROADMAP.md",
    "docs/SP-NNN-OWNER-WORKFLOW.md",
    "docs/rotation-log.md",
    "docs/SECURITY.md",
    # Detector test fixtures reference Owner repo paths in mock-event
    # bodies (legitimate test data):
    ".claude/scripts/detectors/tests/fixtures.py",
    # SBOM generator hard-codes upstream URL (single source of truth):
    ".claude/scripts/generate-sbom.py",
    # ---- S155 CI-cleanup (2026-05-22) ------------------------------
    # Same pattern as the 2026-04-27 batch above: pre-existing legitimate
    # Owner / canonical-repo references that were masked in CI by the
    # contract/ADR-count/perf red layers, surfaced once those were fixed.
    # Each is human-reviewed: non-template-content (not shipped to adopters)
    # OR a canonical-repo reference OR a detector test fixture. NOT personal
    # contamination in shipped template content.
    # ----------------------------------------------------------------
    # LLM03 supply-chain detector treats the framework's CANONICAL repo
    # (github.com/<owner>/) as trusted alongside github.com/anthropics/ —
    # adopters clone framework updates from it (canonical-repo reference):
    ".claude/hooks/_lib/output_scan.py",
    # Detector / canonical-edit / mcp-guard test fixtures carry Owner repo
    # paths in mock-event bodies as legitimate test data (same rationale as
    # detectors/tests/fixtures.py + replay/tests/* below):
    ".claude/hooks/tests/test_check_canonical_edit_markers.py",
    ".claude/hooks/tests/test_check_canonical_edit_mcp.py",
    ".claude/hooks/tests/test_mcp_canonical_guard.py",
    ".claude/scripts/tests/test_success_receipt.py",
    "tests/unit/test_output_scan_llm03.py",
    # GPG sentinel-signer roster — references Owner key by design (like
    # sentinel-signers.txt / skill-patch-signers.txt above):
    ".claude/security/sentinel-signers-registry.yaml",
    # Owner brief + internal design docs (Owner attribution / setup paths;
    # like the operational docs allowlisted above):
    "BUNDLE-OWNER-BRIEF.md",
    "docs/GIF-CAPTURE-SPEC.md",
    "docs/PERMISSION-MODEL-DESIGN.md",
    "docs/security-bash-canonical-guards.md",
}

_ALLOWLIST_GLOBS = {
    # NOTE: fnmatch `*` matches across `/` boundaries here (unlike the
    # `glob` module). A single `*` after the directory prefix is enough
    # to cover all nested files — no need for `**`.
    # Plan artifacts (all file types under .claude/plans/, including
    # WAR-ROOM/, SPRINT-NN-ROADMAP.md, PLAN-NNN-*.md, PLAN-NNN/...).
    # Wave C-bis (2026-04-27): broadened from `PLAN-*.md` + `PLAN-*`
    # to `*` so non-PLAN- artifacts (WAR-ROOM, SPRINT-NN, README) get
    # covered without per-file additions.
    ".claude/plans/*",
    # Domain squads (by design — each domain lists real-world owners)
    ".claude/skills/domains/*",
    # CI workflow templates distributed to adopters
    "templates/.github/workflows/*",
    # NPM shim — URLs reference canonical repo owner
    "npm/*",
    # ADRs — architectural decision records carry Owner Accepted-By
    ".claude/adr/ADR-*.md",
    # Published SPEC — concrete examples reference owner/projects
    "SPEC/*",
    # Docs subfolders that document the framework's ecosystem:
    # case studies, research (external competitive analysis),
    # site HTML, etc.
    "docs/case-studies/*",
    "docs/research/*",
    "docs/site/*",
    # Benchmarks against named peers
    "benchmarks/*",
    # Issue templates
    ".github/ISSUE_TEMPLATE/*",
    # Owner ceremony archive (Wave C moved 17 OWNER-*.sh here; each
    # script references Owner's GPG key + project paths by design):
    ".claude/scripts/owner-ceremony/*",
    # Forensic ceremony archive — historical Owner ceremony scripts
    # retained for chain-of-custody. Never re-executed. PLAN-063 S5.
    "scripts/local/historical/*",
    # Architect ceremony sentinels — GPG-signed `approved.md` per round
    # MUST carry Owner handle + key fingerprint by design (the sentinel IS
    # the canonical Owner authorization artifact). PLAN-072 + PLAN-069 Wave D
    # surfaced this as latent debt (S81 2026-05-03).
    ".claude/architect/*",
    # Replay redaction test corpus — fixtures + tests in
    # .claude/scripts/replay/tests/ MUST contain `/Users/devuser/` and
    # similar OS-path shapes because they are the regression markers proving
    # the redactor strips them. Removing the literals defeats the test.
    # PLAN-069 Phase 1 Wave A+B canonical test surface (S81 2026-05-03).
    ".claude/scripts/replay/tests/*",
    # ---- S155 CI-cleanup (2026-05-22) — non-template-content zones ----
    # Owner-run ceremony / restart tooling at repo root + scripts/local/ +
    # the .claude mirror. Reference Owner path/key by design; never shipped
    # to adopters (extends the existing scripts/local/historical/* +
    # owner-ceremony/* allowlist):
    "scripts/local/*",
    ".claude/scripts/local/*",
    "OWNER-*.sh",
    # Historical Owner-ceremony archive at repo root (archive/): retired
    # ceremony scripts (OWNER-*-CEREMONY.sh) + the Owner bundle brief moved
    # here for chain-of-custody. Each references the Owner path / @handle /
    # GPG key by design; never re-executed, never shipped to adopters
    # (extends owner-ceremony/* + scripts/local/historical/*). S165 CI-green.
    "archive/*",
    # Detector test corpora — ATLAS + red-team fixtures MUST carry realistic
    # /Users/<owner>/ + canonical-repo-URL shapes because they are the
    # regression markers proving the LLM03 supply-chain + secret/path
    # detectors fire (same rationale as .claude/scripts/replay/tests/*):
    "tests/fixtures/atlas/*",
    "tests/fixtures/red-team-corpus/*",
}

# ---------------------------------------------------------------------------
# NEGATIVE exception to the allowlist — deny WINS over allow
# ---------------------------------------------------------------------------
# `.claude/plans/*` in _ALLOWLIST_GLOBS exempts the plan tree WHOLESALE
# (fnmatch's `*` crosses `/`, as the note on that set says). That exemption
# was written for plan PROSE: hand-authored artifacts a maintainer reads
# before committing, which legitimately name adopter context.
#
# PLAN-179 W2 puts a different KIND of file in the same tree. A per-plan
# `LEDGER.md` is written INCREMENTALLY, mid-session, by the model, from
# material that includes agent returns and tool output — and this repository
# is PUBLIC. A blanket exemption over a machine-appended file is a standing
# leak path, not a reviewed one, and "the model was told to write
# identifiers only" is an instruction, not a control.
#
# The cure is a NEGATIVE exception for that ONE class rather than "add
# coverage": dropping `.claude/plans/*` would drag every plan artifact into
# the scan and regrow exactly the noise the exemption exists to remove.
#
# Matched by BASENAME under `.claude/plans/`, at ANY depth — deliberately
# NOT by glob. `.claude/plans/*/LEDGER.md` misses both
# `.claude/plans/LEDGER.md` and a ledger parked one directory deeper, and a
# rule an author sidesteps by moving the file is not a rule.
_NEVER_ALLOWLISTED_BASENAMES = frozenset({
    "LEDGER.md",          # check_ledger_checkpoint.LEDGER_BASENAME
    "LEDGER-ARCHIVE.md",  # check_ledger_checkpoint.LEDGER_ARCHIVE_BASENAME
})
_NEVER_ALLOWLISTED_ROOT = (".claude", "plans")


def is_never_allowlisted(rel_path: str) -> bool:
    """True for a file the allowlist must NOT be able to exempt.

    ``rel_path`` is repo-relative and POSIX-separated. Kept a pure
    function so the test can drive it directly and `scan()` can consult
    it BEFORE the walker's allowlist — deny wins over allow.
    """
    parts = rel_path.split("/")
    root = _NEVER_ALLOWLISTED_ROOT
    return (
        len(parts) > len(root)
        and tuple(parts[: len(root)]) == root
        and parts[-1] in _NEVER_ALLOWLISTED_BASENAMES
    )


# Suffixes to skip (binary / non-text files)
_SKIP_SUFFIXES = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp",
    ".pdf", ".ico", ".zip",
}


# ---------------------------------------------------------------------------
# RULE 2 — `personal-path`: absolute home paths under docs/ and .claude/plans/
# ---------------------------------------------------------------------------
# The TERM rule above exempts those two trees almost entirely: `.claude/plans/*`
# is a WHOLESALE glob (fnmatch's `*` crosses `/`) and most of `docs/` sits on
# the exact allowlist. Both exemptions were written for PROSE that legitimately
# names adopter context; neither was ever a decision about absolute HOME paths.
# This repository is PUBLIC, and the plan tree is where frozen rail transcripts
# and ceremony logs land — which is exactly where a `/Users/<name>/` leaks.
# PLAN-186 §Riscos recorded the follow-up (Codex P1, S339); this rule is it.
#
# WHAT IT FLAGS: an absolute home directory whose owner segment is a REAL name
# — `/Users/<name>/...`, `/home/<name>/...`, and the harness slug form
# `-Users-<name>-...` that a project state directory carries. The documented
# placeholder style (`/Users/<user>/`, `/Users/devuser/`, `/home/runner/`) is
# not a hit: `<` is not a path character, and the generic owner segments are
# listed below.
#
# NOTHING IS EXEMPT BY NAME OR BY SUFFIX. Every in-scope tracked path is
# read and matched the SAME WAY -- no basename, no extension and no
# directory decides that a file is not looked at. Three versions of this
# pack shipped a name-shaped skip and the pair-rail found each of them:
# `*.asc` exempt by suffix (v2, land round 1), `*-approved.md` exempt by
# basename (v2, round cure-2), and `OWNER-*.sh` exempt by basename BEFORE
# any content was read (v3, land round 1 -- the finding that dropped the
# pack). Each time the bypass was one rename: a tracked symlink
# `docs/OWNER-leak.sh -> /Users/<owner>/repo` walked through the gate that
# `docs/plain-leak.md` with the SAME target failed. The class is closed by
# REMOVAL, not by enumerating the safe names -- which is the only closure
# this repository has ever made stick (CLAUDE.md, S336 lesson).
#
# WAIVERS therefore act on a hit that has ALREADY been found, and come
# from exactly ONE place:
#   * the tracked allowlist file, ONE `<path> | sha256:<64 hex> | <reason>`
#     row per file. A row is a human decision with the decision written
#     down, and BOTH halves are checked: the reason must contain a
#     character that is actually shown and none that is a control or a
#     format character, so a reason of zero-width spaces -- which
#     satisfied the grammar and waived a real leak (round 19) -- is
#     MALFORMED. There is no glob, no directory prefix and no generated
#     baseline, because every shape that waives a file nobody named is the
#     shape this rule exists to remove. THE ROW IS PINNED TO CONTENT: it
#     waives the file only while the bytes the scan read hash to the
#     recorded digest, so a row cannot waive a file FOREVER (pair-rail,
#     land round 1, P2) -- one added byte and the waiver lapses, the gate
#     goes red, and a human re-reads the file and re-records the digest.
#     TRACKEDNESS IS VERIFIED, not assumed: an allowlist git cannot
#     confirm is read as EMPTY, so a `touch`ed copy waives nothing
#     (`_personal_path_allowlist_is_tracked`).
#
# THERE IS NO SECOND WAIVER, AND NO RULE WAIVER AT ALL. A signed
# sentinel (`approved.md` / `*-approved.md`) used to be forgiven by a
# RULE that asked four questions of content -- a sibling `.asc`, an
# armoured signature body over a size floor, an `Approved-By`
# fingerprint a tracked row granted, and not-a-symlink. Every one of
# those answers is TRANSPLANTABLE by anyone who can write a file: the
# sidecar is not bound to the document, and the Owner's fingerprint is
# published. So `docs/leak-approved.md` with a copied `.asc` was waived
# while the same bytes under another name were a finding -- exemption
# by NAME in a content-shaped costume, which is the one class this rule
# exists to remove. It waived ZERO hits on this tree (CENSUS below), so
# deleting it moved no row and closed the surface outright.
#
# A signature this gate can actually VERIFY would be a second waiver
# earned by content; that needs `gpg` and a keyring, and it is
# `.claude/plans/PLAN-186-FOLLOWUP-sentinel-gpg-verification.md`. Until
# it lands, a frozen signed artifact carrying a home path is waived the
# same way everything else is: by a row pinned to its digest -- and a
# signature freezes that digest, so the row cannot go stale behind
# anyone's back.
#
# The rule NEVER prints a matched LINE — its findings land in a PUBLIC CI log,
# and a gate that quotes the leak it found is a second copy of it. It prints
# `file:line`, which is what a human needs to go and look.
#
# THAT RULE APPLIES TO THE GATE'S OWN OUTPUT, at one choke point. Everything
# this rule prints that it did not compose itself — a waiver REASON, an
# allowlist path outside the repo, an ignored CLI token, the REASON an
# OSError carries — goes through `_personal_path_safe`, which runs the
# rule's own predicate over the string and replaces it wholesale when it
# names a home directory. Two of those fatal prints were interpolating
# `_oserror_reason(exc)` RAW until the text lane of round 20 injected an
# error whose diagnostic carried a home path and watched it print at rc 2;
# an exhaustive-sounding sentence beside four safe call sites is how the
# fifth stays unnoticed. There is ONE deliberate exception and it is not a
# print: the row offered by `--emit-personal-path-rows`, which the parser
# has to read back, is built from `hit.rel` under two explicit refusals --
# see `_personal_path_safe`. Four separate
# print sites were found leaking by the pair-rail (round cure-1, P2 x3); they
# were four instances of one shape, so the cure is one predicate at the
# boundary, not four redactions. A contaminated waiver reason is ALSO refused
# at parse time, so it never reaches a printer at all.
#
# A tracked SYMLINK is scanned as what git stores: the TARGET STRING. Not
# doing so was a false negative with a one-line trigger (rail round cure-1,
# P1) — `is_file()` follows the link, so a dangling link read as "absent" and
# a resolvable one had someone else's file scanned in its place, while the
# `/Users/<name>/…` in the committed link payload was never looked at.
#
# FAIL-CLOSED ON INPUT (CLAUDE.md §4): an allowlist that exists and cannot be
# read or DECODED (a single non-UTF-8 byte used to raise through the CLI as a
# traceback carrying the absolute checkout path — rail round cure-1, P2), and
# an in-scope file that exists and cannot be read, are both fatal
# (rc 2) — an unverified scan is not a clean one. That fatal names the file the
# way every other line of this rule does — repo-relative, NEVER absolute:
# `str(OSError)` embeds `filename`, and on an operator machine that filename is
# the very `/Users/<name>/...` this rule exists to keep out of a public log
# (`_oserror_reason` below is what strips it; measured, cured,
# controlled). A file that is TRACKED but
# ABSENT from the worktree is skipped: absence is not unreadable input. Bytes
# that are not valid UTF-8 are REPLACED, never skipped, so "the guard could not
# parse it" cannot read as "the guard found nothing".
#
# DECLARED BLIND SPOTS (a rule that names what it cannot see):
#   * a path split across two lines, or assembled from fragments;
#   * the Windows form, and the `-home-<name>-` slug form (the latter would
#     fire on ordinary hyphenated prose such as `-home-page-`);
#   * a HYPHENATED owner in the SLUG form only: `-Users-dev-jane-repo` reads
#     as owner `dev`, a placeholder, and is missed (pair-rail round cure-2,
#     P2 — DECLARED, not cured). Reading further would mean treating
#     `-Users-runner-work-repo` as owner `runner-work`, which is not on the
#     placeholder list, so the fail-closed reading fires on the documented
#     placeholder style the rule exists to protect. The direct form
#     `/Users/dev-jane/` IS caught (that regex accepts `-`), and a document
#     carrying the slug almost always carries the direct form too;
#   * a relative `Users/<name>/...` with no leading slash;
#   * a personal path glued straight onto a preceding word character
#     (`x/Users/<name>`) — the price of not firing on every `.../home/<page>`
#     URL route, a shape docs legitimately carry;
#   * TWO undecodable bytes in one line: the second reading removes every
#     U+FFFD at once, so `/Us<FF>ers/<FF>name` is covered, but a byte that
#     decodes to a VALID character (rather than to U+FFFD) is not modelled at
#     all — this rule is a leak detector, not an adversary-proof filter;
#   * THE INDEX IS ENUMERATED AND THE WORKTREE IS READ. `git ls-files`
#     names the entries; the bytes come from the filesystem. Stage a
#     leaking blob and then overwrite or delete it in the worktree and
#     the scan sees the clean copy, while `git commit` lands the staged
#     one -- and a row pins the WORKTREE bytes, not necessarily the bytes
#     being landed (pair-rail round 1, P1, both lanes). DECLARED, not
#     cured: closing it means reading blobs through `git cat-file`
#     instead of the filesystem, which changes what every digest in the
#     shipped allowlist means. It is also the pre-existing behaviour of
#     RULE 1 and of `FileWalker`, and in CI -- where this gate runs -- the
#     index and the worktree are the same tree by construction;
#   * the owner class is a DELIMITER class, so an owner segment that
#     CONTAINS one of the delimiters (`<`, `>`, a quote, a comma, a
#     closing bracket) is still read short. That set is exactly what
#     keeps `/Users/<user>/` clean without a special case, and the trade
#     is deliberate: the alternative fires on the documented placeholder
#     style this rule exists to encourage;
#   * `/./Users/<name>/...` is missed -- the lookbehind rejects a leading
#     `.`, which is what keeps the rule off `../home/x` and
#     `example.com/home/index`. Same family as the relative form above;
#   * a row waives the WHOLE file AT ONE DIGEST: two leaks added in the
#     same edit are waived together by the row that records that edit's
#     sha256. What a row can no longer do is waive the NEXT edit -- the
#     digest is the thing a reviewer re-approves;
#   * a FROZEN artifact is waived by a row like anything else. There is
#     no rule waiver to earn, so the operator cost of a signed sentinel
#     that really does carry a home path is one row -- and because a
#     signature freezes the bytes, that row's digest cannot lapse
#     without the signature lapsing first;
#   * a symlink's TARGET is scanned as text, so a link to a file whose
#     CONTENT carries a personal path is judged by the link, not by that
#     file — the file itself is scanned on its own if it is tracked and in
#     scope, and out of scope it was never this rule's subject;
#   * TRACKED is not COMMITTED. The allowlist's trackedness is
#     verified, so a file git never heard of waives nothing — but an
#     UNCOMMITTED edit to a tracked allowlist still grants. That edit
#     is a `git diff`, which is the reviewable artifact the claim was
#     always about, and refusing it would make "add the row, run the
#     gate, commit it in the same change" impossible in that order.
#
# CENSUS — the table most "MEASURED" notes below are derived from. Two are
# not, and say so where they stand: the case-variant fold and the NUL
# refusal each name their own instrument, because each counts a different
# population than this table does. A note that cites this table when it
# measured something else would be the drift this block exists to stop.
#
# It is the SOURCE, not the only occurrence: a note repeats a figure
# from it inline (the 242 waived files) because the
# sentence is unreadable without it. Each says CENSUS beside the number
# so a reader knows where it came from, and a claim of exclusivity that
# the file itself contradicts is worse than none (pair-rail round 3, P3).
#
# Every "MEASURED" note below cites this table instead of carrying a figure
# of its own. Three of them had already drifted by the time a cross-vendor
# review read the module (S344): two docstrings were a generation behind the
# disk, while sibling comments in this same file carried the current ones. A
# number written in six places is six chances to be wrong; written once,
# with the command beside it, it is one thing to re-run.
#
# Measured 2026-09-04 (S344) at 056e11c, on the tree with this rule applied
# and staged. From the repository root:
#
#   git ls-files -z | tr '\0' '\n' | grep -c .                      -> 5222
#   git ls-files 'docs/*' '.claude/plans/*' | wc -l                 -> 2171
#   git ls-files 'docs/*' '.claude/plans/*' \
#     | grep -cE '(^|/)(approved|.*-approved)\.md$'                 ->   75
#   ... the same list, counting those with `test -f "$f.asc"`       ->   75
#   git ls-files 'docs/*' '.claude/plans/*' | grep -c '\.asc$'      ->   82
#
# The rest is this module's own predicates driven over `git ls-files`, plus
# one `python3 .claude/scripts/check_contamination.py` for the verdict line:
#
#   * in-scope `.asc`: 0 are symlinks, 0 carry a hit line, and every one
#     decodes to the same 147-byte signature body;
#   * in-scope sentinels: 75, and NONE of them carries a hit. That is the
#     number that made the DELETION of the rule waiver free: 34 of them
#     passed the four checks the deleted rule asked, and not one of those
#     34 had anything to be forgiven. A waiver that forgives nothing is
#     an attack surface with no user;
#   * in-scope files carrying a hit: 242 — each one waived by a row whose
#     digest matches, with 0 unwaived, 0 digest mismatches, 0 stale and
#     0 malformed rows;
#   * what the REMOVED name exemptions were hiding, measured on this tree
#     before they were removed: of 54 in-scope `OWNER-*.sh` scripts, 0
#     carry a hit (they name the checkout through `$HOME` and `$CEO_REPO`,
#     never literally); of 75 in-scope sentinels, 0 carry a hit; 0 in-scope
#     paths are symlinks; 0 in-scope regular files carry a binary suffix.
#     EVERY exemption this rule ever had waived exactly nothing — so the
#     uniform scan and the deleted `_SKIP_SUFFIXES` branch move ZERO rows,
#     and the waived count is the same 242 before and after;
#   * in-scope paths hitting on their own NAME: 0. Tracked paths that are
#     undecodable in scope: 0;
#   * hit lines over every tracked file: 4238 under the widened `\w` pair
#     and 4237 under the ASCII one. The ONE line they disagree on is the
#     non-ASCII example spelled out in the `_PERSONAL_PATH_HOME_RE` note
#     below — a line under `.claude/scripts/`, which this rule never scans,
#     so the widening moves no ROW.
#
# These figures AGE with the tree; they are dated and pinned to a base so a
# reader can tell staleness from drift. Re-run the commands before quoting
# them, and change them HERE — not in the prose that cites them.

#: Only these two trees. The rule deliberately does NOT widen the walk — the
#: term rule already sees everything else.
_PERSONAL_PATH_SCOPE = (".claude/plans/", "docs/")

#: `/Users/<seg>` and `/home/<seg>`. The lookbehind keeps the rule off URL
#: routes and nested directories (`example.com/home/index`, `/srv/home/x`):
#: a home path is written from a path root, so it is preceded by `/`, a quote,
#: a space or a line start — never by a word character.
#:
#: BOTH separators are `/+`, not `/` (pair-rail land round 1, P2):
#: `/Users//<owner>/repo` is the same directory to every filesystem and
#: every shell, and it read CLEAN (reproduced: `False` against `True` on
#: the single-slash form). A matcher that a doubled separator walks past is
#: a matcher with a one-keystroke bypass. MEASURED over every tracked file
#: before it was chosen: the widened pair and the v3 pair answer
#: IDENTICALLY on all 4238 hit lines — zero disagreements, in scope or out
#: — so this closes a hole and moves no row.
#:
#: The owner class is `\w` (UNICODE), not `[A-Za-z0-9]` (pair-rail round 1,
#: P2). An ASCII-only class was wrong in BOTH directions: `/Users/<é>…` did
#: not match at all, and — worse — a name whose ASCII PREFIX is a placeholder
#: was TRUNCATED to it (`/Users/devé/` read as owner `dev`, which the
#: placeholder set forgives), so a real owner was reported clean. Matching
#: the whole segment is what makes the placeholder comparison meaningful.
#: MEASURED before choosing it — the CENSUS above carries both
#: counts. The two pairs answer identically over every tracked file
#: but ONE line: the non-ASCII example this note spells out, which
#: is the very class the widening exists to catch. That line lives
#: under `.claude/scripts/`, out of this rule's scope, so the
#: correction moves no ROW on this tree.
#: The owner class is a DELIMITER class, not a character whitelist
#: (pair-rail round 1, P1). `[\w.\-]+` stopped at the first character it
#: did not know, and a segment read HALFWAY is worse than one not read at
#: all: `/Users/dev+zzfake/repo` was truncated to owner `dev`, which is on
#: the placeholder list, so a real owner was reported CLEAN. Round 1 of the
#: previous version fixed the ASCII half of exactly this and the class was
#: still a whitelist, so the shape came back for `+`, `$`, `~` and every
#: other legal filename character. Enumerating the legal ones is the thing
#: that keeps failing; the class now takes everything up to a character
#: that ENDS a path segment in prose.
#:
#: `<` and `>` are in the delimiter set, and that is what keeps the
#: documented placeholder style clean without a special case: in
#: `/Users/<user>/x` the very first character after the literal is a
#: delimiter, so there is no match at all — not a match the placeholder
#: list has to forgive.
#:
#: MEASURED over every tracked file, BOTH matchers together, before it
#: was chosen: 20 lines change answer (4238 -> 4258), ALL of them out of
#: this rule's scope, and every one is the widening being RIGHT — a shell
#: `${USER_NAME}` expansion, regex sources spelling `/Users/[A-Za-z]...`,
#: and byte fixtures in this rule's own tests. ZERO in-scope
#: disagreements, so zero rows move. The cost is declared: a regex or a
#: shell variable written inside `docs/` now needs a row, which is the
#: recoverable failure this rule is built around.
#:
#: BOTH matchers are built from ONE delimiter set, below. Round 2 of the
#: rail found the reason that matters: the first cure widened the DIRECT
#: matcher and left the SLUG one a whitelist, so `-Users-dev+<real>-repo`
#: still read as owner `dev` — the same defect, one regex over. Two
#: matchers of the same thing that can be edited apart WILL be edited
#: apart; the shared constant is what makes that impossible rather than
#: unlikely.
_PERSONAL_PATH_SEG_DELIMS = r"""/\s"'`,;:)\]}<>|"""
#: The lookbehind excludes a WORD character, a dot and a tilde -- the
#: forms that make the slash part of something else (`x/Users/`,
#: `./Users/`, `~/Users/`). It used to exclude `-` as well, which made
#: a unified-diff DELETION line invisible: `-/Users/<real>/work` in a
#: frozen diff read clean while the `+` line beside it was a hit
#: (pair-rail round 4, P1). A hyphen does not attach a path to a
#: preceding word the way a letter does, and MEASURED over every
#: tracked file the removal moves ZERO lines.
#:
#: The ROOT TOKEN is CASE-FOLDED; nothing else is. On the default
#: case-insensitive macOS volume this rule was written for,
#: `/users/<owner>/x` names the same directory as `/Users/<owner>/x`,
#: and the exact-case matcher answered False for it -- a decision made
#: by SPELLING rather than by content, which is the failure this whole
#: rule exists to remove (pair-rail round 16, P2). `/USERS/`, `/Home/`
#: and `/HOME/` were the same hole.
#:
#: Written as explicit per-character classes rather than a pattern-wide
#: `re.IGNORECASE`. The honest reason is LOCALITY, not behaviour: a flag
#: would not change what is captured (the owner segment keeps its own
#: case either way) and the delimiter class holds no letters. The two
#: spellings are NOT equivalent, and saying they were was the second
#: overstatement in this note: `re.IGNORECASE` folds U+017F LATIN SMALL
#: LETTER LONG S onto `s` and the explicit `[Ss]` class does not
#: (measured: ignorecase True, explicit False -- text lane, round 23).
#: The explicit classes are therefore the NARROWER spelling as well as
#: the local one, and a letter entering either class would widen the
#: fold silently. The classes put the fold where a
#: reader can see its extent. (Stated wrongly here once, as a
#: behavioural claim, and caught by the round-17 text lane.)
#:
#: MEASURED before shipping. The comparison only means something on the
#: tree WITHOUT the cure: run over a tree that already folds, the
#: instrument compares the fold against itself and answers zero for
#: free. `measure-case-variant-root.py` therefore reads its matcher from
#: the tree it is pointed at, and the number quoted here is its run
#: against the PRE-cure derivation -- see the CENSUS block above and
#: EVIDENCE section J, which also carry the two different in-scope
#: counts (the census counts with git pathspec globs, the instrument
#: with this rule's own scope predicate) so neither reads as a
#: correction of the other. The finding: the fold moves ZERO lines.
#:
#: `/users/me`, `/Users/me/x` and `/users/alice/x` stay clean because
#: `me` and `alice` are PLACEHOLDERS. That is why the estimate of five
#: false positives does not reproduce -- FOUR of those lines are the HTTP
#: route `/users/me` (three in one document, one in a frozen transcript)
#: and the fifth is a `HOME/CLAUDE_PROJECT_DIR` example, which is not a
#: home path at all. The estimate was made against an implementation
#: that had lost the placeholder filter.
#:
#: The narrower form proposed first -- fold only when the owner segment
#: matches the repo private-term pattern -- was measured and REJECTED,
#: with the reason stated exactly. `build_pattern()` never matches
#: nothing: it always carries `_PLACEHOLDER_TERMS`. In an adopter, with
#: no `scripts/contamination-terms.txt`, it reduces TO those three
#: alternatives -- so the narrowed fold would fire only for an owner
#: segment spelled like one of the three `_PLACEHOLDER_TERMS` at the top
#: of this file, and never for a real handle. (Those three are NOT
#: written out here: this module must not match the pattern it builds,
#: and quoting them made it do exactly that -- caught by
#: `test_delivered_module_is_not_itself_contaminated`, which is the
#: PLAN-183 W2 A7 guard doing its job on this very edit.)
#: A cure that fires only where its author declared a
#: terms file is a fail-open by configuration: the class this file
#: closes, not one it adds.
#: The leading run is ONE literal `/` guarded by a fixed-width
#: lookbehind, not `/+`. `/+` after a lookbehind can restart at every
#: slash of a run, and each restart rescans the rest of it: `"/" * 16000`
#: followed by a home path took 1.833 s on the machine that measured it,
#: and 8 000 took 0.48 s -- quadratic, on a line a committed file can
#: carry (mechanism lane, round 21, A1; reproduced). The slash is
#: CONSUMED and there is ONE lookbehind, `(?<![\w.~]/)`, which carries
#: the same start condition the old pattern did: it refuses the position
#: only when the character before that slash makes it part of something
#: else AND there is no second slash -- which is exactly what
#: `(?<![\w.~])/+` said. (An earlier draft of this note described two
#: lookbehinds and quoted a `(?<=/)` that the final pattern does not
#: have, because the slash was made a literal so the mask could keep
#: replacing it -- text lane, round 23.) Verified as a DIFFERENTIAL over
#: every in-scope tracked file plus the boundary forms `/Users/x`,
#: `//Users/x`, `a/Users/x`, `a//Users/x`, `./Users/x`, `~/Users/x`:
#: zero disagreements. The match now begins at the LAST slash of the
#: run rather than the first, which is why the `/` is CONSUMED and not
#: asserted -- `_personal_path_mask_rel` replaces the match, and a mask
#: that dropped the slash would rewrite the path it masks.
_PERSONAL_PATH_HOME_RE = re.compile(
    r"/(?<![\w.~]/)(?:[Uu][Ss][Ee][Rr][Ss]|[Hh][Oo][Mm][Ee])/+([^"
    + _PERSONAL_PATH_SEG_DELIMS + "]+)"
)

#: The harness slug form (`/` replaced by `-`), e.g. a project state directory
#: named `-Users-<name>-<repo>`. `-` separates segments here, so it cannot be
#: part of one: the capture is lazy up to the next `-`. `-+` for the same
#: reason the two above are `/+`: the slug of `/Users//<owner>` is
#: `-Users--<owner>`, and it read clean. Same differential, same answer:
#: zero disagreements over every tracked file.
#:
#: The owner class is the SHARED delimiter set plus `-`, which is this
#: form's own separator. Built from the same constant as the direct
#: matcher (pair-rail round 2, P1): widening one and not the other left
#: `-Users-dev+<real>-repo` reading as the placeholder `dev`.
#:
#: The TERMINATOR is that same class, and it took a second round to be
#: (mechanism lane, round 20). It used to be `(?:-|$)` -- a hyphen or the
#: end of the line -- so any ordinary punctuation after the owner hid the
#: whole slug: `~/.claude/projects/-Users-<owner>/memory/`,
#: `docs/-Users-<owner>/note.md` and a quoted `"-Users-<owner>"` all read
#: CLEAN while `-Users-<owner>-repo` was a hit. The class the capture
#: cannot CONTAIN and the class it may END at are the same class, which
#: is the only spelling of this that has no third case.
#:
#: MEASURED over 2 189 in-scope tracked files and 1 744 389 lines before
#: it shipped (`measure-slug-terminator.py`): the widening alone moved SIX
#: lines, all six the elided `-Users-<ellipsis>` in prose about the slug
#: families. That elision is what the placeholder list is FOR, so the
#: Unicode ellipsis joined it beside the ASCII spelling, and the pair
#: together move ZERO lines.
#: The root token folds here for the same reason and in the same way as
#: in the direct matcher above: a slug is derived from a path, so a
#: case-variant path yields a case-variant slug, and one matcher folding
#: while its twin did not is how `-Users-dev+<real>-repo` got through
#: once already (round 2, P1). Both fold, from the same reasoning.
_PERSONAL_PATH_SLUG_RE = re.compile(
    r"-[Uu][Ss][Ee][Rr][Ss]-+([^" + _PERSONAL_PATH_SEG_DELIMS
    + r"-]+?)(?=[-" + _PERSONAL_PATH_SEG_DELIMS + r"]|$)"
)

#: Home-directory owner segments that are NEUTRAL PLACEHOLDERS, not people.
#: Docs and tests are supposed to use these, so flagging them would punish the
#: correct behaviour and push authors toward worse examples. Every entry is a
#: generic word or a CI/system account; adding a real handle here would make
#: this list the contamination it guards against (the PLAN-183 W2 A7 shape).
#: `git ls-files -s` renders a symlink with this mode. It is the ONLY
#: authority this rule accepts on whether an entry is a link, because the
#: filesystem is not one: under `core.symlinks=false` git materialises a
#: mode-120000 entry as a REGULAR FILE whose content is the target string,
#: so `Path.is_symlink()` answers False for a link: the link's TARGET
#: STRING would be scanned as ordinary content on one checkout and as a
#: link on another (pair-rail round 1, P1). Asking git
#: also removes the check/use race: the classification and the read no
#: longer come from two separate filesystem answers.
_PERSONAL_PATH_LINK_MODE = "120000"

#: The index modes this rule knows how to turn into bytes: a regular
#: file, an executable file, and a symlink (whose blob is its target
#: string). ANY OTHER mode -- today the 160000 gitlink, tomorrow
#: whatever git adds -- is refused by name rather than skipped: a
#: gitlink in scope opened as a directory, yielded no blob, and still
#: counted as a file the walk had seen, so the scan reported clean
#: without reading it (pair-rail round 3, P1). A mode this rule cannot
#: read is an unverified entry, not a clean one.
_PERSONAL_PATH_BLOB_MODES = frozenset({"100644", "100755", "120000"})

#: How many ancestors the allowlist symlink walk will examine before it
#: gives up -- and giving up is a REFUSAL, never a fall-through.
_PERSONAL_PATH_ANCESTOR_CAP = 64

#: `O_NOFOLLOW` where the platform has it. A regular-file read opens with
#: it, so 'this is not a link' is decided by the SAME syscall that hands
#: back the inode — not by an `is_symlink()` a moment earlier that
#: something could invalidate before the read (pair-rail round 1, P1).
_PERSONAL_PATH_O_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)

#: `open(O_RDONLY)` on a FIFO BLOCKS until a writer connects, so the
#: `fstat` that classifies the inode is never reached and the scan hangs
#: until an outer CI timeout instead of returning a verdict (pair-rail
#: round 3, P2; measured, still blocked at 25 s). `O_NONBLOCK` makes the
#: open return immediately for a non-regular inode, which is then
#: rejected by the fstat that already existed. It is a no-op for the
#: regular files this rule actually reads.
_PERSONAL_PATH_O_NONBLOCK = getattr(os, "O_NONBLOCK", 0)

#: Compared lowercased.
_PERSONAL_PATH_PLACEHOLDERS = frozenset({
    "...",        # an elided segment, `/Users/.../project`
    "\u2026",     # the SAME elision as one character, `-Users-\u2026-repo`
    "a", "b", "x", "y", "u",
    "adopter", "alice", "bob", "carol",
    "ci", "runner", "ubuntu", "root",       # CI / container accounts
    "dev", "devuser", "example", "home", "me", "someone", "tmp",
    "test", "testuser", "user", "username", "you", "youruser",
})

#: The tracked allowlist, NEXT TO this file, under `.claude/scripts/`.
#:
#: IT DOES NOT YET TRAVEL WITH A FRESH INSTALL, and saying that it did was
#: a claim about code that is not there (pair-rail round 2, P2):
#: `scripts/install.sh` copies `*.sh`, `*.py` and `*.yaml` out of this
#: directory and nothing copies a `.txt`. An adopter therefore gets the
#: rule and no allowlist, which the rule reads as EMPTY — fail-closed, so
#: their own findings are reported rather than silently waived, but it is
#: not the delivery this line used to promise. `install.sh` is CANONICAL,
#: so the fix is a signed ceremony (`scripts-fu`), not this free pack.
#: It must be TRACKED to waive anything: the gate confirms that with
#: git before it parses a row, and an untracked copy reads as empty.
_PERSONAL_PATH_ALLOWLIST_REL = (
    ".claude/scripts/contamination-personal-path-allowlist.txt"
)

#: An explicitly EMPTY value for a path option. `argparse` distinguishes
#: omission (`default=None`) from `--root ""`, and the module then read
#: both by truthiness: the empty string silently selected the DEFAULT, so
#: the gate scanned the checkout this file lives in and returned green
#: while the operator believed it had scanned somewhere else (pair-rail
#: round 4, P1). An empty path is not a path; it is a usage error.
_PERSONAL_PATH_EMPTY_OPTION = (
    "%s was given an EMPTY value; an empty path is not a path, and "
    "treating it as \"not given\" would silently scan the default "
    "instead"
)

#: A reason an emitted row still carries. Refused by the parser so a row
#: pasted from `--emit-personal-path-rows` cannot be committed unreasoned.
_PERSONAL_PATH_UNREASONED = "REPLACE-WITH-REASON"

#: Cap on what the CLI prints per section — the shipped allowlist waives
#: hundreds of frozen artifacts, and a wall of them hides the one that matters.
_PERSONAL_PATH_PRINT_CAP = 20

#: EVERY alternative of BOTH regexes above requires one of these literals
#: UP TO THE CASE OF THE ROOT TOKEN, so a line holding none of them -- in
#: any case spelling -- cannot match either. That is why the fast path is
#: `_PERSONAL_PATH_LITERAL_RE` below and no longer `str.__contains__`:
#: since v4.9 the matchers fold the root, and an exact-case containment
#: test would reject `/users/<owner>/x` before either matcher ran -- the
#: fast path would have become a filter of its own, which is exactly what
#: this note promised it never would (round 17, text lane: the paragraph
#: here described code that had already been replaced). It remains a
#: SEMANTIC EQUIVALENCE, not a performance claim — the framework makes no
#: speed claim (CLAUDE.md §1), and pair-rail round 1 (P2) removed the
#: measured one that stood here. A differential test drives the predicate
#: and a regex-only reference over the same corpus and demands the same
#: answer.
_PERSONAL_PATH_LITERALS = ("/Users/", "/home/", "-Users-")

#: The fast path asks the SAME question as the matchers, so it folds the
#: root token the same way -- and it is DERIVED from the tuple above
#: rather than written out a second time. A second spelling of the same
#: authority that silently omits the fold is the false-green shape this
#: file removes wherever it finds it: before this, the fast path rejected
#: `/users/<owner>/x` by exact case and the folded matchers below were
#: never reached (pair-rail round 16, P2).
_PERSONAL_PATH_LITERAL_RE = re.compile("|".join(
    "".join(
        "[%s%s]" % (char.upper(), char.lower()) if char.isalpha()
        else re.escape(char)
        for char in literal
    )
    for literal in _PERSONAL_PATH_LITERALS
))

#: Seconds a SINGLE in-scope file may spend in the line matcher before
#: the scan refuses it. The matcher is linear per line since the cure
#: above, so this is not the fix for that defect and does not claim to
#: be: it is the boundary for the general case, an arbitrary tracked file
#: fed to a regex engine. Fail-CLOSED, like every other unreadable INPUT
#: here (CLAUDE.md section 4): the file is REFUSED, rc 2, never reported
#: clean. Generous on purpose -- the largest in-scope file in this
#: repository scans in well under a second -- because a deadline that
#: fires on a slow runner turns a gate into a coin toss.
_PERSONAL_PATH_FILE_BUDGET_S = 30.0

#: What `bytes.decode(errors="replace")` leaves where a byte was not valid
#: UTF-8. Its presence makes the line's FIRST reading untrustworthy — see
#: `line_is_personal_path_hit`.
#:
#: DECLARED FALSE POSITIVE (pair-rail round 4, P2): U+FFFD is itself a
#: valid character, so a name or a line that CONTAINS one deliberately is
#: read here as a decoding failure. By the time this rule sees a name,
#: `FileWalker` has already decoded it with `errors="replace"`, so the
#: two cases are no longer distinguishable at this layer. The direction
#: is the safe one -- the gate REFUSES rather than waives, and the
#: remedy it prints (rename the file) is correct for both -- and the fix
#: means carrying raw bytes through the walker, which is a change to the
#: older rule's contract.
_PERSONAL_PATH_REPLACEMENT = "�"

#: Every mark a decoder can leave where it could not read a byte: U+FFFD
#: from `errors="replace"`, and the lone surrogates U+DC80-U+DCFF from
#: `errors="surrogateescape"` — which is what the OS hands back for a
#: symlink target and what the symlink branch used to feed this matcher
#: RAW (pair-rail land round 1, P1: the surrogate is not U+FFFD, so the
#: second reading never fired and `/Users/dev<0xFF>zzfake/` read as the
#: placeholder `dev`). One regex, so a new marker is added in one place.
_PERSONAL_PATH_UNDECODABLE_RE = re.compile("[\ufffd\udc80-\udcff]")

class PersonalPathHit(NamedTuple):
    """One in-scope file, its 1-based hit lines, and the digest of
    the bytes that produced them.

    `sha256` is over the RAW BYTES this scan matched — a file's content,
    or a symlink's target string — taken from the SAME read, never a
    second one. A row waives a file by naming that digest, so hashing
    any other bytes than the ones that were matched would let a row
    waive content nobody scanned (and would race an edit between the
    two reads). It is None when there were no BODY hits to pin — a
    name-only hit, or no readable content — and a hit with no digest
    is unwaivable by construction, which is the fail-closed default.
    """

    rel: str
    lines: Tuple[int, ...]
    sha256: Optional[str] = None
    #: The same bytes with CRLF folded to LF. NOTHING is ever waived on
    #: this digest -- it exists only so a mismatch caused by a checkout
    #: EOL filter can be NAMED instead of looking like an edit nobody
    #: made (pair-rail round 3, P2). Diagnosis, not a second key.
    sha256_lf: Optional[str] = None


class PersonalPathScan(NamedTuple):
    """What the walk found: the hits, and nothing else.

    There is no rule-waived map any more. It carried the ONE waiver
    the scan decided for itself -- the signed-sentinel rule, deleted
    with the refuter's F1 -- and a field that is always empty is a
    channel waiting to be re-opened. Every waiver now comes from the
    tracked allowlist and is applied by `personal_path_verdict`, which
    stays pure so tests can drive every split without a filesystem.

    Each in-scope entry is read exactly once, AS A SUBJECT. That is
    now literally true: the sidecar read a sentinel used to cause is
    gone with the rule that needed it (pair-rail round 2, P3, which
    the deletion answers rather than qualifies).
    """

    hits: List[PersonalPathHit]


class PersonalPathRow(NamedTuple):
    """One allowlist row: the digest it pins, and the reason a human wrote.

    `rowno` is the 1-based line the row was read from. A row is refused by
    NUMBER -- that is the only address an operator can act on -- and the
    reason check below runs after the load, in the caller that knows the
    repository, so the row has to carry where it came from.
    """

    sha256: str
    reason: str
    rowno: int = 0


class PersonalPathVerdict(NamedTuple):
    """Split of the scan against the allowlist. `waived` keeps the reasons.

    `mismatched` is its own category and not a kind of `unwaived`: a row
    exists and NAMES this file, but the bytes moved since a human read
    them. The operator action is different (re-read the file, re-record
    the digest, not write a new decision), so the report says so.
    """

    unwaived: List[PersonalPathHit]
    waived: List[Tuple[str, str]]      # (rel, reason)
    stale: List[str]
    malformed: List[int]
    mismatched: List[str]


def in_personal_path_scope(rel_path: str) -> bool:
    """True for a repo-relative POSIX path inside the rule's two trees.

    A tracked entry that IS a scope root, or an ancestor of one, counts.
    Git stores no directories, so such an entry can only be a SYMLINK:
    `docs -> /Users/<owner>/repo` replaces the whole tree with a link,
    and the plain `startswith` answered False for it — the scope test
    itself was a way out of the scope (pair-rail round 1, P1, both
    lanes). MEASURED: no such entry exists on this tree, so the
    widening moves no row; it removes a shape.
    """
    if rel_path.startswith(_PERSONAL_PATH_SCOPE):
        return True
    prefix = rel_path + "/"
    return any(scope.startswith(prefix) for scope in _PERSONAL_PATH_SCOPE)


def _personal_path_owner_segments(line: str) -> List[str]:
    """Lowercased home-directory owner segments named on ``line``."""
    segments = [m.group(1) for m in _PERSONAL_PATH_HOME_RE.finditer(line)]
    segments += [m.group(1) for m in _PERSONAL_PATH_SLUG_RE.finditer(line)]
    return [s.lower() for s in segments]


def _personal_path_names_a_person(line: str) -> bool:
    """One reading of ``line``: does it name a non-placeholder home owner?"""
    if not _PERSONAL_PATH_LITERAL_RE.search(line):
        return False
    return any(
        seg not in _PERSONAL_PATH_PLACEHOLDERS
        for seg in _personal_path_owner_segments(line)
    )


def line_is_personal_path_hit(line: str) -> bool:
    """True when ``line`` names a home directory that is not a placeholder.

    TWO readings, because one of them is not enough. An undecodable byte in
    the line is UNPARSEABLE INPUT, and the decoder's U+FFFD SPLITS a literal
    (`/Us<0xFF>ers/`, which the fast path then rejects) and can make an owner
    segment unrecognisable. Fail CLOSED per the CLAUDE.md §4 rule for security
    matchers — the reading with the replacement removed is what the author's
    bytes could have meant, so a hit in EITHER reading is a hit.

    (An earlier version of this paragraph said U+FFFD TRUNCATES an owner
    segment to a placeholder prefix, with `/Users/dev<0xFF>name` reading as
    owner `dev`. That was true of an older owner class and is not true of
    this one: U+FFFD is not in the shared delimiter set, so the capture is
    the whole `dev<U+FFFD>name` and the line is a HIT in the FIRST reading.
    Measured on this module — text lane, round 23. The three clauses below
    are unchanged; only the example was wrong.)

    Two readings were still not enough (pair-rail land round 1, P1): the
    removal can RECONSTRUCT a placeholder as easily as the truncation can
    produce one — `/Users/dev<0xFF>user/work` reads as owner `dev` with
    the marker in place and as `devuser` with it removed, and BOTH are on
    the placeholder list, so a real owner hid behind one byte. Enumerating
    readings cannot close that: whatever the pair of readings answers, the
    matcher does not KNOW what the bytes said.

    So the third clause is the CLAUDE.md §4 rule itself, stated once: an
    unreadable byte on a line that names a home path in EITHER reading is
    unparseable input inside a security matcher, and unparseable input is
    a HIT. A human then looks at the bytes; the recoverable failure is one
    allowlist row with a written reason.

    Monotone: each clause can only ADD findings. On the tree this
    shipped from all three agreed — the CENSUS above counts the hit
    files, and NO in-scope file carries an undecodable byte on a
    home-path line at all.
    """
    if _personal_path_names_a_person(line):
        return True
    if not _PERSONAL_PATH_UNDECODABLE_RE.search(line):
        return False
    stripped = _PERSONAL_PATH_UNDECODABLE_RE.sub("", line)
    if _personal_path_names_a_person(stripped):
        return True
    return bool(_PERSONAL_PATH_LITERAL_RE.search(line)
                or _PERSONAL_PATH_LITERAL_RE.search(stripped))


def personal_path_hit_lines(
    text: str, deadline: Optional[float] = None,
) -> Tuple[int, ...]:
    """1-based line numbers of every hit line in ``text``.

    Returns NUMBERS, never content: the caller — including a CLI whose output
    lands in a public CI log — is left with nothing quotable.

    `split("\\n")`, NOT `splitlines()`: the report is `file:line`, and a human
    resolves that with `sed -n '<N>p'` or `grep -n`, both of which count
    `\\n`. `splitlines()` ALSO breaks on `\\v`, `\\f`, `\\x1c`-`\\x1e`, U+2028
    and U+2029 — one vertical tab in a frozen transcript would shift every
    line number after it, and a finding that points at the wrong line is a
    finding a reviewer cannot check. NFKC therefore runs PER LINE, after the
    split, so normalisation cannot move the boundaries either.

    ``deadline`` is a `time.monotonic()` value, not a duration, so the
    budget belongs to the CALLER that knows what it is scanning. When it
    passes, the scan REFUSES the file (`PersonalPathUnreadable`, which
    the CLI renders as rc 2) instead of returning the lines it had found:
    a partial answer from a security matcher is not a clean file.

    It is consulted AFTER every line, and the claim is exactly that: it
    bounds the file ACROSS its lines. It does NOT interrupt work already
    running inside one line, and `unicodedata.normalize` is work that can
    itself be super-linear -- 140 000 combining marks followed by 140 000
    more took 38.186 s in one call (mechanism lane, round 22). After such
    a line the deadline fires, so the outcome is a NAMED refusal instead
    of a silent green; the seconds spent on that line are not recovered,
    and the honest boundary for them is the outer CI timeout.
    """
    hits: List[int] = []
    for lineno, line in enumerate(text.split("\n"), start=1):
        if line_is_personal_path_hit(unicodedata.normalize("NFKC", line)):
            hits.append(lineno)
        # AFTER the line, and after EVERY line -- both halves are the
        # cure, and each was a defect on its own. Checking every 512th
        # line left a document of ONE line unchecked. Checking at the TOP
        # of the body left it unchecked too, for a subtler reason: the
        # single check then runs before any work has been done, and the
        # loop ends without another one. Measured after that cure:
        # 140 000 U+0315 followed by 140 000 U+0300 took 72.2 s and
        # returned 0 on a 30 s budget. After the line, there is something
        # to detect; before it, there is not.
        if deadline is not None and time.monotonic() > deadline:
            raise PersonalPathUnreadable(
                "matching did not finish within the per-file deadline of "
                "%.0f s (stopped after line %d); the file is REFUSED "
                "rather than reported clean"
                % (_PERSONAL_PATH_FILE_BUDGET_S, lineno))
    return tuple(hits)


class PersonalPathUnreadable(Exception):
    """An in-scope file that EXISTS and cannot be read — fatal, not skipped."""


class PersonalPathBlob(NamedTuple):
    """The bytes git stores for a tracked entry, and whether it is a link.

    The link fact travels WITH the bytes because it is decided inside the
    same `try` that read them. Asking the filesystem a second time is how
    two pair-rail findings in a row were built (round cure-2, P1+P2): a
    decision taken outside the boundary that is supposed to contain it.
    """

    raw: bytes
    is_symlink: bool


def _personal_path_blob(
    path: Path, rel: str, index_is_link: bool = False,
) -> Optional[PersonalPathBlob]:
    """The BYTES git stores for a tracked entry, or None when there are none.

    ONE classification, inside ONE try. Spreading it over an `is_symlink()`
    outside the try, a suffix test before it and a read inside it produced two
    pair-rail findings in a row (round cure-2, P1+P2): the suffix test skipped
    a symlink by its NAME — `docs/photo.png -> /Users/<name>/photo.png` walked
    straight through the gate — and `is_symlink()` itself raises
    `PermissionError` when an ancestor directory is unsearchable, which
    escaped `PersonalPathUnreadable` as an rc-1 traceback carrying the
    absolute path. Two symptoms, one shape: a decision taken outside the
    boundary that is supposed to contain it.

    * a SYMLINK is its target STRING — that is the blob git stores, and where
      a `/Users/<name>/…` sits. Following the link would scan someone else's
      file instead, and a dangling one would read as absent;
    * a tracked path with no file is None: absence is not unreadable INPUT;
    * NOTHING IS SKIPPED BY NAME. v3 skipped a regular file whose SUFFIX
      was in `_SKIP_SUFFIXES`, which is the term rule's list, written for
      a different question. It was the last name-shaped skip left in this
      rule after the `.asc` and `*-approved.md` ones were removed, and
      leaving it would have kept the class alive in a third form: an image
      carries the author's home path in its metadata all the time, which
      is precisely the leak this rule exists to find. MEASURED before it
      was removed (CENSUS above): ZERO in-scope regular files carry one of
      those suffixes, so the removal moves no row and costs no read that
      the rule was not already paying;
    * BYTES, not text. Decoding is the CALLER's, in one place, so the
      digest a waiver is pinned to is taken from the same object that was
      matched. `errors="replace"` there, never `strict`: an undecodable
      blob must not be SKIPPED (the fail-open the LEDGER exception above
      had to cure by hand), and the replacement is deterministic.

    Every OSError on any of those steps becomes `PersonalPathUnreadable` with
    `rel` and the REASON — never `exc`, whose str() carries the absolute
    filename — and `from None`, because an uncaught one would print the
    chained OSError repr and leak the same path through the traceback.
    """
    try:
        if index_is_link:
            # git said mode 120000. On a normal checkout that is a link
            # and the blob is the target string; under
            # `core.symlinks=false` it is a regular file whose CONTENT is
            # that same string. Both readings give the bytes git stores.
            #
            # ONE reader for both, and the SAME reader the non-link branch
            # uses. Asking `is_symlink()` and then `is_file()` was three
            # questions about three moments, and the answer to each is
            # whatever `pathlib` decides to swallow: on the supported floor
            # `is_symlink()` RAISES under an unsearchable ancestor (measured,
            # 3.9.6) while `os.path.lexists` answers False for anything it
            # cannot stat -- so the v4.2 shape was one pathlib change away
            # from reading a present-but-unreadable entry as ABSENT
            # (mechanism lane, round 11). `_personal_path_read_nofollow`
            # classifies by ERRNO in a single open: absence is `ENOENT` /
            # `ENOTDIR`, a link is `ELOOP` and comes back as its target
            # string, a directory or a device is fatal, and any other
            # OSError propagates to the sanitised fatal below.
            blob = _personal_path_read_nofollow(path)
            if blob is None:
                # ABSENT. A tracked path with no file is not unreadable
                # INPUT -- the one documented `None` of this function.
                return None
            # git's INDEX decides link-ness, never the filesystem: under
            # `core.symlinks=false` the entry is a regular file and the
            # reader says so, but the bytes are still a link payload and
            # must be denied every waiver a link is denied.
            return PersonalPathBlob(raw=blob.raw, is_symlink=True)
        return _personal_path_read_nofollow(path)
    except PersonalPathUnreadable as exc:
        # The reader below raises this for a DIRECTORY or a FIFO left where
        # a tracked file should be, and it is not an OSError -- so it went
        # past the clause below and the fatal named the reason without the
        # SUBJECT. In a large tree that is a message an operator cannot act
        # on (mechanism lane, round 14). The path is MASKED, like every
        # other path this rule prints.
        raise PersonalPathUnreadable(
            "%s: %s" % (_personal_path_mask_rel(rel), exc)) from None
    except OSError as exc:
        raise PersonalPathUnreadable(
            "%s: %s" % (rel, _oserror_reason(exc))) from None


def _personal_path_read_nofollow(path: Path) -> Optional[PersonalPathBlob]:
    """Read an entry git called a REGULAR FILE, refusing to follow a link.

    `is_symlink()` then `read_bytes()` are two answers about two moments:
    replace the file with a link between them and the read follows it
    while the recorded classification still says "not a link" — enough
    to scan a link's target as though it were file content, and (while
    the rule waiver still existed) enough to earn it (pair-rail round
    1, P1).
    `O_NOFOLLOW` collapses both into one syscall: either it opens the
    inode the name pointed at, or it refuses because that name is a link.

    A refusal is not an error here, it is a FINDING: git enumerated this
    entry as a regular file and the filesystem disagrees, so the link is
    scanned as a link — its TARGET STRING is the content matched, never
    followed — and `is_symlink=True` travels with the blob. The target
    may well be clean; what is closed is the path where a link was read
    as the file it points at.

    A non-regular inode does NOT yield None. A directory raises
    `PersonalPathUnreadable` (errno EISDIR below), and so does a FIFO, a
    socket or a device at the `S_ISREG` test, because git enumerated a
    blob here and the disk holds something that is not one: an entry
    this rule cannot read is an UNVERIFIED entry, not a clean one
    (pair-rail round 4, P1 -- returning None here was a silent skip, and
    this docstring went on saying so until round 17 read it). `None` is
    for an entry that is simply ABSENT (ENOENT / ENOTDIR). The open
    carries
    `O_NONBLOCK` so that classification can happen at all -- without it
    a FIFO left in place of a tracked file blocks the open until a
    writer connects and the scan never reaches the fstat below
    (pair-rail round 3, P2).
    """
    try:
        fd = os.open(str(path),
                     os.O_RDONLY | _PERSONAL_PATH_O_NOFOLLOW
                     | _PERSONAL_PATH_O_NONBLOCK)
    except OSError as exc:
        if exc.errno in (errno.ELOOP, getattr(errno, "EMLINK", None)):
            return PersonalPathBlob(
                raw=os.fsencode(os.readlink(path)), is_symlink=True)
        if exc.errno in (errno.ENOENT, errno.ENOTDIR):
            return None
        if exc.errno == errno.EISDIR:
            # PRESENT and not readable as a blob. Returning None here
            # made a tracked path replaced by a DIRECTORY a silent
            # skip (pair-rail round 4, P1).
            raise PersonalPathUnreadable(
                "a tracked entry is a DIRECTORY on disk; it exists and "
                "holds no blob, so the scan has no verdict for it")
        raise
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            # A FIFO, a socket, a device: PRESENT, and not a blob.
            # `O_NONBLOCK` (round 3) stopped the hang; returning None
            # here then turned the hang into a CLEAN UNREAD SCAN, which
            # is worse (pair-rail round 4, P1). Fail-closed: the mode is
            # named, the path is not.
            raise PersonalPathUnreadable(
                "a tracked entry is not a regular file on disk "
                "(st_mode 0o%o); it exists and holds no blob, so the "
                "scan has no verdict for it"
                % stat.S_IFMT(os.fstat(fd).st_mode))
        chunks = []
        while True:
            block = os.read(fd, 1 << 20)
            if not block:
                break
            chunks.append(block)
        return PersonalPathBlob(raw=b"".join(chunks), is_symlink=False)
    finally:
        os.close(fd)


def _personal_path_index_modes(repo_root: Path) -> Dict[str, str]:
    """`{repo-relative path: git index mode}` for every tracked entry.

    The rule asks git — not the filesystem — whether an entry is a link
    (see `_PERSONAL_PATH_LINK_MODE`). Failing to get that answer is not a
    reason to guess: a scan that cannot classify its inputs is an
    unverified scan, which this rule already calls fatal everywhere else.
    """
    try:
        proc = subprocess.run(
            ["git", "ls-files", "-s", "-z"],
            cwd=str(repo_root), capture_output=True, check=False,
            timeout=60,
        )
    except (OSError, subprocess.SubprocessError):
        raise PersonalPathUnreadable(
            "cannot read the git index (git unavailable or timed out); "
            "the scan cannot tell a symlink from a file") from None
    if proc.returncode != 0:
        raise PersonalPathUnreadable(
            "cannot read the git index (git ls-files -s exited %d); the "
            "scan cannot tell a symlink from a file" % proc.returncode)
    modes: Dict[str, str] = {}
    for entry in proc.stdout.decode("utf-8", errors="replace").split("\0"):
        if not entry:
            continue
        head, _, name = entry.partition("\t")
        if name:
            modes[name] = head.split(" ", 1)[0]
    return modes


#: The line number a PATH hit is reported under. A hit in the NAME has no
#: line, and `file:0` is the shape every reader of `grep -n` already knows
#: means "not a line of content". The report prints a legend for it.
_PERSONAL_PATH_NAME_LINE = 0


def _personal_path_undecodable_in_scope(rel: str) -> bool:
    """True when an undecodable path is, or might be, this rule's subject.

    The first cut raised on ANY undecodable tracked path, so a legal
    byte-name under `assets/` turned the whole gate rc 2 for a rule that
    does not scan `assets/` at all (pair-rail round 2, P2). The fail-closed
    rule is about a matcher's INPUT, and out of scope it was never input.

    UNDECIDABLE counts as in scope, and the test for it is exact rather
    than a segment count: `in_personal_path_scope` is a `startswith` over
    `_PERSONAL_PATH_SCOPE`, so the verdict is fully determined by the
    characters BEFORE the first marker unless one of the prefixes is still
    alive at that point -- i.e. unless the marker falls inside a prefix and
    everything decoded so far matches it. `do<marker>s/note.md` is fatal
    (`docs/` is still alive at index 2); `assets/img<marker>.png` is not
    (no prefix survives its first character).
    """
    match = _PERSONAL_PATH_UNDECODABLE_RE.search(rel)
    if match is None:
        return False
    if in_personal_path_scope(rel):
        return True
    head = rel[:match.start()]
    return any(len(head) < len(prefix) and prefix.startswith(head)
               for prefix in _PERSONAL_PATH_SCOPE)


def _personal_path_assert_enumerable(repo_root: Path) -> None:
    """Fatal unless git really did enumerate ZERO tracked files.

    `FileWalker._iter_git_tracked` returns an EMPTY iterator when `git` is
    missing, times out, or exits non-zero (`_lib/file_walker.py:80-93`) --
    the same shape a genuinely empty repository has. A gate that prints
    "no contamination" because it looked at nothing is a false green, and
    an enumeration that failed is not a verdict (pair-rail round 1, P2).

    This is a GATE, not a hook: the CLAUDE.md §4 fail-open applies to hooks
    that must not block a user session. Nothing here blocks a session, and
    the module already answers rc 2 for an in-scope file it cannot read --
    so an enumeration it cannot trust is rc 2 too, by the same rule.

    Called ONLY when the walk yielded nothing, so the ordinary run pays for
    no second enumeration. The message names no path.
    """
    try:
        proc = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=str(repo_root), capture_output=True, check=False, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        raise PersonalPathUnreadable(
            "cannot enumerate tracked files (git unavailable or timed "
            "out); the scan looked at nothing and has no verdict") from None
    if proc.returncode != 0:
        raise PersonalPathUnreadable(
            "cannot enumerate tracked files (git ls-files exited %d); the "
            "scan looked at nothing and has no verdict" % proc.returncode)
    listed = [name for name in proc.stdout.split(b"\0") if name]
    if listed:
        # The RETRY worked and the repository is NOT empty, so the walk
        # that yielded nothing was the thing that failed. Checking only
        # the return code here turned a transient first failure into a
        # clean verdict over zero files (pair-rail round 1, P1, both
        # lanes) — the exact false green this assertion exists to stop.
        raise PersonalPathUnreadable(
            "the walk yielded NOTHING while git lists %d tracked file(s); "
            "the enumeration failed and the scan has no verdict"
            % len(listed))


def scan_personal_paths(repo_root: Path) -> PersonalPathScan:
    """Every in-scope tracked file carrying a personal path — ALL of them.

    UNIFORM: every in-scope tracked path is read and matched the same
    way. No basename, no suffix and no directory decides that a file is
    not looked at, because three versions of this pack shipped such a
    skip and the pair-rail found each one (`.asc` by suffix, sentinels by
    basename, `OWNER-*.sh` by basename — the last of those dropped v3 at
    the land). This function decides NO waiver at all: it reports what
    it found, and the only thing that may forgive a finding is a
    content-pinned row, applied later by `personal_path_verdict`.

    Walks tracked files with NO path allowlist at all: the term rule's
    allowlist is what hid this class, and consulting it here would
    re-hide it.

    The PATH is a subject, not just an address (pair-rail land round 2,
    G3). `docs/-Users-<name>-project/note.md` with a clean body used to
    pass, though the rule's own predicate answers True on that string --
    the slug form in a directory name is exactly what the harness writes,
    and it is a RENAME, not a waiver.
    MEASURED before choosing it (CENSUS at the top of this block):
    ZERO in-scope tracked paths hit on their own name today, so the
    new subject adds no row.

    **A waiver waives the BODY, never the NAME** (pair-rail round 1, P1).
    The v2 cut tested exemption BEFORE the path, so an exempt file under
    a contaminated directory -- `docs/-Users-<name>-x/wave-approved.md`
    -- was `continue`d and its own path never examined. Ordering cured
    the symptom; v4 removed the shape. Nothing is skipped at all now,
    so there is no ordering left to get wrong: the name is judged and
    the body is read, always, and only a row may forgive BODY lines.
    `personal_path_verdict` refuses to consider any waiver for a hit
    carrying line 0, and the allowlist parser separately refuses a row
    naming a home directory -- two independent reasons a name cannot be
    waived, neither of them a property of one parser.

    Raises ``PersonalPathUnreadable`` when a file that exists cannot be
    read, and when a tracked path is not valid UTF-8: `FileWalker` decodes
    `git ls-files -z` with `errors="replace"`, so such an entry arrives as
    a name that does not exist, `is_file()` answers False and the file was
    SKIPPED IN SILENCE (pair-rail land round 2, G2). A path the scan cannot
    address is unparseable input, and unparseable input in a security
    matcher is fatal (CLAUDE.md §4). MEASURED (CENSUS above): ZERO
    tracked paths are undecodable in scope.
    The message names NO path -- a mangled name is the one string the
    redactor cannot reason about, so nothing about it is echoed.

    Also raises it when the walk yielded NOTHING and git cannot confirm the
    tree is empty, and when the set of paths the walk actually saw does
    not COVER the index -- see `_personal_path_assert_enumerable`. A
    PARTIAL walk is a false green with a smaller blast radius than an
    empty one, and the index is already in hand, so it costs nothing to
    refuse it (pair-rail round 2: the empty-only assertion was the weaker
    half of the question it was asking; round 3: so was counting, because
    a walk that yields one path twice has the right COUNT and the wrong
    coverage).

    And when an in-scope entry carries an index mode this rule cannot
    turn into bytes (`_PERSONAL_PATH_BLOB_MODES`): a gitlink opened as a
    directory, yielded nothing, and still counted as a file the walk had
    seen (pair-rail round 3, P1). Out-of-scope entries are unaffected --
    the scope test comes first, so a submodule elsewhere in the tree is
    not this rule's business.
    """
    walker = FileWalker(repo_root=repo_root, mode="git")
    modes = _personal_path_index_modes(walker.repo_root)
    hits: List[PersonalPathHit] = []
    # IDENTITIES, not a count. `seen == len(modes)` was satisfied by a
    # walk that yielded one path twice while another tracked file was
    # never read, and reported clean over it (pair-rail round 3, P1).
    # A set answers the question the assertion was always asking:
    # WHICH tracked files did this scan actually look at?
    seen_rels = set()
    for path in walker.iter_files():
        try:
            rel = path.relative_to(walker.repo_root).as_posix()
        except ValueError:
            rel = path.as_posix()
        seen_rels.add(rel)
        if _personal_path_undecodable_in_scope(rel):
            raise PersonalPathUnreadable(
                "a tracked path is not valid UTF-8; the scan cannot "
                "address it (rename it, then re-run)")
        if not in_personal_path_scope(rel):
            continue
        # An index mode this rule cannot turn into bytes is a REFUSAL,
        # not a skip: the 160000 gitlink opened as a directory, gave
        # `None`, and still counted as seen (pair-rail round 3, P1).
        # The message names the MODE and a masked path -- a path can
        # itself be the leak this rule exists to keep out of a log.
        # A MISSING mode is not a pass. `modes` and the walk are two
        # enumerations of the same index taken moments apart, so an
        # in-scope path the snapshot does not know is an inconsistent
        # scan -- and `modes.get(rel) is None` skipped the whole check
        # (pair-rail round 4, P2).
        entry_mode = modes.get(rel)
        if entry_mode is None:
            raise PersonalPathUnreadable(
                "%s: in scope and absent from the index snapshot taken "
                "by this same call; the scan is inconsistent and has "
                "no verdict" % _personal_path_mask_rel(rel))
        if entry_mode not in _PERSONAL_PATH_BLOB_MODES:
            raise PersonalPathUnreadable(
                "%s: index mode %s is not a blob this rule can read; "
                "the scan has no verdict for it"
                % (_personal_path_mask_rel(rel), entry_mode))
        lines: Tuple[int, ...] = ()
        # The NAME is judged, and nothing waives a name.
        if line_is_personal_path_hit(unicodedata.normalize("NFKC", rel)):
            lines += (_PERSONAL_PATH_NAME_LINE,)
        digest: Optional[str] = None
        digest_lf: Optional[str] = None
        blob = _personal_path_blob(
            path, rel,
            index_is_link=modes.get(rel) == _PERSONAL_PATH_LINK_MODE)
        if blob is not None:
            # A NUL is not text, and this matcher only reads text.
            # A UTF-16 or UTF-32 document decodes HERE, with
            # `errors="replace"`, into ASCII interleaved with NULs:
            # every one of those bytes is individually VALID UTF-8, so
            # THE LINE THAT CARRIES THE HOME PATH produces no U+FFFD,
            # the second reading of `line_is_personal_path_hit` never
            # fires for it, and the NULs split every literal the fast
            # path looks for. (The BOM does decode to two U+FFFD, on the
            # FIRST line -- text lane, round 19. It is a different line,
            # and the second reading is per line, so it never reaches
            # the one being hidden.) Reproduced
            # (mechanism lane, round 18): the same two lines committed
            # under `docs/` twice, once as UTF-8 and once as UTF-16,
            # gave ONE hit -- the UTF-16 copy read CLEAN.
            #
            # Unparseable input to a security matcher is fail-CLOSED
            # (CLAUDE.md section 4), so this REFUSES rather than scan a
            # decoding it cannot trust. MEASURED before shipping by the
            # pack instrument `measure-nul-census.py`, which prints both
            # numbers and is runnable from the repository root: of the
            # in-scope tracked files, ZERO carry a NUL -- the refusal
            # moves no file, it removes a shape. (The instrument counts
            # with a git pathspec, so its total is its own derivation
            # rather than a correction of the CENSUS table above.) The
            # message names the MASKED path and the remedy.
            if b"\x00" in blob.raw:
                raise PersonalPathUnreadable(
                    "%s: the bytes carry a NUL, so they are not the "
                    "UTF-8 text this rule reads (a UTF-16/UTF-32 or "
                    "binary blob); re-encode it as UTF-8, then re-run"
                    % _personal_path_mask_rel(rel))
            text = blob.raw.decode("utf-8", errors="replace")
            try:
                body = personal_path_hit_lines(
                    text,
                    deadline=time.monotonic() + _PERSONAL_PATH_FILE_BUDGET_S)
            except PersonalPathUnreadable as exc:
                # The refusal has to say WHICH file. Raised from the line
                # loop it named a deadline and nothing else, and the CLI
                # printed `FATAL: cannot read in-scope file matching did
                # not finish ...` -- true, and useless among thousands of
                # scanned entries (mechanism lane, round 22). Masked, like
                # every other path this rule prints.
                raise PersonalPathUnreadable(
                    "%s: %s" % (_personal_path_mask_rel(rel), str(exc)))
            if body:
                lines += body
                # Hashed only for a file that HIT, and hashed from the
                # bytes that were matched: this digest is what a row
                # pins, so it must describe the content the scan saw,
                # not the content a second read would find.
                digest = hashlib.sha256(blob.raw).hexdigest()
                digest_lf = hashlib.sha256(
                    blob.raw.replace(b"\r\n", b"\n")).hexdigest()
        if lines:
            hits.append(
                PersonalPathHit(rel=rel, lines=lines, sha256=digest,
                                sha256_lf=digest_lf))
    missed = set(modes) - seen_rels
    extra = seen_rels - set(modes)
    if extra:
        # The walk yielded a path the index snapshot does not hold.
        # Symmetric to `missed`, and equally a sign that the two
        # enumerations disagree (pair-rail round 4, P2).
        raise PersonalPathUnreadable(
            "the walk yielded %d file(s) git does not have in the "
            "index; the scan is inconsistent and has no verdict"
            % len(extra))
    if missed:
        # `modes` came from `git ls-files -s` in THIS call, so it is the
        # authoritative SET of what the walk should have seen. Zero was
        # only the loudest case: a walk that stops early is unverified in
        # exactly the same way, and reports clean over the files it never
        # reached. Comparing SETS rather than counts closes the shape a
        # count cannot see -- one path yielded twice and another never
        # (pair-rail round 3, P1). The message counts; it names no path,
        # because a path can be the leak.
        if not seen_rels:
            _personal_path_assert_enumerable(walker.repo_root)
        raise PersonalPathUnreadable(
            "the walk saw %d distinct file(s) and MISSED %d of the %d "
            "git has in the index; an incomplete scan has no verdict"
            % (len(seen_rels), len(missed), len(modes)))
    hits.sort(key=lambda h: h.rel)
    return PersonalPathScan(hits=hits)


#: `<path> | sha256:<64 hex> | <reason>`. The path carries no space and no
#: `|`; the digest is over the bytes the scan matched; the reason is
#: everything after the second `|`, stripped, and must not be empty.
#:
#: THE DIGEST IS THE CURE for "a row waives the file FOREVER" (pair-rail
#: land round 1, P2). A row used to be a decision about a PATH, and a path
#: outlives the reading that justified waiving it: the frozen transcript a
#: human read once could grow a second leak years later and stay silent.
#: Pinned to content, the row is a decision about BYTES -- it expires the
#: moment those bytes change, which is exactly when a human should look
#: again. The recoverable failure is loud and cheap: the gate names the
#: file, `--emit-personal-path-rows` prints the new row, a human re-reads
#: and commits it.
#:
#: A v3-shaped two-field row does NOT match, and an unmatched row is
#: MALFORMED, not ignored -- so an allowlist carried over from the previous
#: version fails the gate loudly instead of waiving without a digest.
#: The reason is captured GREEDILY and the trailing `\s*$` is gone. They
#: were an overlapping pair -- a lazy capture that grows one character at a
#: time while `\s*$` retries behind it -- and over a run of whitespace that
#: is quadratic: one row whose reason held 64 000 interior spaces took
#: 16.687 s (mechanism lane, round 22; reproduced). Nothing is lost, because
#: the caller has already applied `line.strip()`: there is no trailing
#: whitespace left for `\s*$` to consume, so the two spellings accept the
#: same rows and capture the same fields. That equivalence is MEASURED as a
#: differential over the 242 shipped rows and a table of row shapes rather
#: than argued from the pattern.
_PERSONAL_PATH_ROW_RE = re.compile(
    r"^([^\s|]+)\s*\|\s*sha256:([0-9A-Fa-f]{64})\s*\|\s*(\S.*)$")


#: How many ASCII letters or digits a written reason must carry, counted
#: after NFKC. Eight is a WORD, not a mark: no filler, no combining mark
#: and no invisible codepoint reaches it, whatever category a future
#: Unicode revision puts it in. MEASURED on the shipped allowlist before
#: choosing the number: the seven reasons carry 60 to 112 each.
_PERSONAL_PATH_REASON_MIN_INK = 8


def _personal_path_reason_is_visible(reason: str) -> bool:
    r"""True when ``reason`` is a decision a reviewer can actually READ.

    TWO POSITIVE conditions. Neither is a list of what is forbidden, and
    that is the whole point. The deny-list form of this predicate was
    defeated three rounds running, each time by a character one category
    further out: `Cf` zero-width and bidi (round 19), `Mn` combining
    marks (round 20), and then `Lo`/`So` fillers -- U+3164 HANGUL
    FILLER, U+115F, U+2800 BRAILLE PATTERN BLANK -- which "carry ink" by
    category and render as nothing (round 21). Enumerating categories
    cannot close a class whose next member has not been named yet.
    Asking what a written sentence HAS can.

    * after NFKC, at least `_PERSONAL_PATH_REASON_MIN_INK` characters
      from `[A-Za-z0-9]`. ASCII only, and COUNTED rather than merely
      present: eight letters or digits is a word somebody typed. Every
      filler of every category contributes ZERO, so the whole family
      closes at once, including its unnamed members. NFKC runs first so
      a full-width or mathematical spelling counts as the word it is --
      the same folding the path predicate already asks for;
    * every character PRINTABLE, `str.isprintable()`. That is the
      stdlib's own answer rather than a category list of this module's:
      False for C0/C1 controls, for the format characters, for the
      separators other than a plain space, and for whatever a later
      Unicode revision adds to those. It keeps the round-19 finding
      closed -- `reviewed 2026<CR>HIDDEN` carries EIGHTEEN ASCII
      letters and digits, more than twice the threshold, and is still
      refused because it renders as a row overwritten in the terminal
      that shows it. That is the case which proves the two conditions
      are not redundant: ink alone would pass it. And it is done without
      this module owning a list of what is invisible.

    `\r` is excluded from the FILE-level class two hundred lines up and
    refused HERE, and that is not an inconsistency: there it is the
    terminator of a physical line the row loop counts, and here it is a
    character somebody put inside a written decision.

    A row whose reason fails this is MALFORMED by row NUMBER, which is
    the address the operator can act on, and it waives nothing.
    """
    if not reason.isprintable():
        return False
    folded = unicodedata.normalize("NFKC", reason)
    ink = sum(
        1 for char in folded
        if ("0" <= char <= "9") or ("A" <= char <= "Z")
        or ("a" <= char <= "z")
    )
    return ink >= _PERSONAL_PATH_REASON_MIN_INK


def _personal_path_allowlist_is_tracked(
    repo_root: Path, allowlist_path: Path,
) -> bool:
    """True only when git CONFIRMS the allowlist is in the index.

    Every waiver in this rule -- and there is exactly one kind, the
    content-pinned `<path> | sha256:<64 hex> | <reason>` row -- rests on
    ONE claim: the allowlist is a TRACKED file, so a waiver is something
    somebody COMMITTED and not something somebody left in a working tree.
    Nothing checked that claim. The parser asked `is_file()` and read the
    bytes; git was never consulted, in a rule that asks git every other
    question it has.

    This used to say "a reviewable DIFF", and the r13 decision removed
    that premise: whether the file RENDERS in `git diff` is no longer a
    property this rule rests on, because four rail rounds showed it can
    be taken away by whoever controls the repository. What survives is
    the smaller, checkable claim above -- an untracked file is not a
    decision anybody recorded -- and the visibility of what was granted
    now comes from `_personal_path_honoured_rows`, which prints it.

    MEASURED on the framework's own tree (cross-vendor lane, S344, P2):
    `git rm --cached` the allowlist and the file is still on disk, byte for
    byte, unknown to git -- and the gate still waived 242 files. A claim a
    security matcher does not check is not a
    control, it is a comment.

    Fail-CLOSED, by the rule `_personal_path_assert_enumerable` already
    states: this is a GATE, not a hook, so an answer git cannot give is not
    a yes. Git missing, git timing out, git exiting non-zero, a path
    OUTSIDE the repository, a SYMLINK anywhere between the file and the
    root, an ancestor walk that ran out of budget, and an index mode that
    is not a regular blob all read as NOT tracked -- and an untracked
    allowlist is read as EMPTY, exactly like an absent one, so every hit
    is unwaived.

    HONEST LIMIT, declared in the header: TRACKED is not COMMITTED. An
    uncommitted edit to a tracked allowlist still grants, because that edit
    IS a `git diff` -- the reviewable artifact the claim was always about --
    and refusing it would make "add the row, run the gate, commit it in the
    same change" impossible to do in that order.
    """
    # A SYMLINK is not the file it points at. `resolve()` follows it, so an
    # UNTRACKED link aimed at a tracked file answered TRACKED and its rows
    # were then trusted — a waiver channel opened by a
    # `ln -s` nobody reviewed (pair-rail round 2, P1). Every component
    # between the repository and the file is asked, not just the last: a
    # linked PARENT directory redirects the path just as completely.
    #
    # ROUND 3 hardened this same block twice more, so it is written here
    # in its final form rather than patched again downstream: the budget
    # is a REFUSAL when exhausted (P1), and the catch is a BOUNDARY
    # because `resolve()` raises a bare RuntimeError for a symlink loop
    # on Python 3.9 (P2, both lanes).
    try:
        probe = allowlist_path
        root_real = repo_root.resolve()
        reached_root = False
        for _ in range(_PERSONAL_PATH_ANCESTOR_CAP):
            if probe.is_symlink():
                return False
            if probe.resolve() == root_real or probe.parent == probe:
                reached_root = True
                break
            probe = probe.parent
        if not reached_root:
            # The budget was EXHAUSTED, not satisfied. Falling through
            # here left the remaining ancestors unexamined, so an
            # allowlist deeper than the cap below an untracked link was
            # resolved THROUGH that link and git confirmed the TARGET
            # (pair-rail round 3, P1). A check that runs out of budget
            # is an unfinished check, and an unfinished check in a
            # security matcher is a no.
            return False
    except Exception:
        # A BOUNDARY, not a type list -- the fourth time in this file.
        # `Path.resolve()` raises a bare RuntimeError for a symlink LOOP
        # on Python 3.9, so `except OSError` let an rc-1 traceback
        # carrying the supplied absolute path escape from here
        # (pair-rail round 3, P2, both lanes).
        return False
    try:
        rel = allowlist_path.resolve().relative_to(
            repo_root.resolve()).as_posix()
    except Exception:
        # Outside the repository, so git is not its reviewer and nothing in
        # it can be a reviewable diff. `--personal-path-allowlist` still
        # NAMES the file in the report; it simply waives nothing.
        return False
    # `--` ends OPTION parsing; it does not make the operand LITERAL. An
    # allowlist path containing pathspec magic — `allow-*.txt`, or an
    # explicit `:(glob)` — matched OTHER tracked files, so an untracked
    # file answered TRACKED and its rows were then
    # trusted (pair-rail round 1, P1, both lanes; reproduced with a
    # nonexistent path literally named `*`). Two independent defences:
    # `:(literal)` magic, and a check that what came back is EXACTLY the
    # one path asked about — the second holds even where the first is
    # unsupported.
    try:
        proc = subprocess.run(
            ["git", "ls-files", "-z", "--error-unmatch",
             "--", ":(literal)" + rel],
            cwd=str(repo_root), capture_output=True, check=False, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    if proc.returncode != 0:
        return False
    listed = [name for name
              in proc.stdout.decode("utf-8", errors="replace").split("\0")
              if name]
    if listed != [rel]:
        return False
    # The INDEX MODE, not the filesystem. Under `core.symlinks=false`
    # git materialises a mode-120000 entry as a REGULAR FILE whose
    # content is the target string: `is_symlink()` above answers False
    # for a link, git confirms the NAME, and a link payload shaped like
    # a valid waiver row was parsed and GRANTED -- a leaking file got a
    # clean verdict (pair-rail round 3, P1, both lanes; reproduced on
    # disk). This is the round-1 lesson -- link status comes from the
    # index, never from the filesystem -- applied to the SECOND of the
    # two surfaces that needed it. Only a regular blob can be an
    # allowlist; 120000, the 160000 gitlink and any mode added later
    # are refused, so the answer does not depend on this checkout's
    # `core.symlinks` setting.
    try:
        mode = _personal_path_index_modes(repo_root).get(rel)
    except Exception:
        # A SECOND git call, with a second way to fail. It is outside
        # the caller's scan boundary, so an escape here was an rc-1
        # traceback instead of the documented empty-allowlist behaviour
        # (pair-rail round 4, P2, both lanes). An answer git cannot
        # give is not a yes -- the same rule as every branch above.
        return False
    return mode in ("100644", "100755")


def load_personal_path_allowlist(
    path: Path,
) -> Tuple[Dict[str, "PersonalPathRow"], List[int]]:
    """Parse into ``({rel: row}, malformed row numbers)``.

    Malformed rows are RETURNED by 1-based row number — never by content, so
    the report cannot echo a hand-written path — and never dropped silently: a
    file the parser could not read whole is not a file that waives anything. A
    DUPLICATE path is malformed too, and its entry is REMOVED rather than
    resolved to one of the two: the ambiguity fails closed. So is a row whose
    reason is still the emitted placeholder, and an absolute or `..` path.

    An ABSENT file parses as empty — also fail-closed: every hit reads as
    unwaived. Propagates OSError when the file exists but cannot be read, and
    UnicodeDecodeError when it cannot be DECODED — both are INPUT failures the
    caller turns into rc 2. Neither is swallowed here: a file this function
    could not read WHOLE waives nothing, and must not read as waiving nothing
    quietly.
    """
    entries: Dict[str, PersonalPathRow] = {}
    malformed: List[int] = []
    # ONE read, through the SAME no-follow helper the subject files go
    # through. `is_file()` then `read_text()` was a check and a use of
    # two different inodes: trackedness validated the name, and this
    # re-opened it, so replacing the validated file with a symlink in
    # the gap delivered a crafted untracked row to the waiver
    # (pair-rail round 4, P1). A LINK is refused rather than followed,
    # and a present-but-special inode is fatal, not "absent" -- the
    # helper answers all three questions in one syscall.
    blob = _personal_path_read_nofollow(path)
    if blob is None:
        # ABSENT, exactly as `is_file()` answered before: an allowlist
        # that is not there waives nothing and is not an error. Every
        # OTHER failure -- unreadable, undecodable, a special inode --
        # PROPAGATES, because a file that exists and cannot be read
        # WHOLE must not read as waiving nothing quietly.
        return entries, malformed
    if blob.is_symlink:
        raise PersonalPathUnreadable(
            "the allowlist is a SYMLINK; a link is a claim about "
            "another file, not a reviewable waiver list")
    seen_twice = set()
    # `split("\n")`, NOT `splitlines()` -- the same cure, for the same
    # reason, as `_personal_path_hit_lines` three hundred lines up.
    # `splitlines()` breaks on a bare CR, `\v`, `\f`, `\x1c`-`\x1e`,
    # U+2028 and U+2029; git counts LINES by LF. A tracked file holding
    #     `# reviewed<CR>docs/leak.md | sha256:<64 hex> | reason`
    # is ONE insertion in the diff a human reviews, and `splitlines()`
    # read it as a comment PLUS a granted waiver -- reproduced, rc 0 with
    # the leak waived (mechanism lane, round 13). A waiver a reviewer
    # cannot see ends the only claim a waiver makes.
    # Counted the way git counts, the whole physical line is one row, it
    # starts with `#`, and there is no waiver to grant. A row carrying a
    # stray separator inside it then fails `_PERSONAL_PATH_ROW_RE` and is
    # MALFORMED by number, which is what ambiguous input gets here.
    decoded = blob.raw.decode("utf-8")
    # A control byte in a waiver list makes the row say one thing to
    # this parser and another to whoever reads it, so the FILE is
    # refused. Round 18 found it as a NUL: a row appended with a NUL
    # inside its reason waived a real hit at rc 0 while the 320-row diff
    # rendered as one binary line.
    #
    # What this comment used to add -- that ONE NUL inside git's first
    # 8000 bytes makes `git diff` print `Binary files ... differ` for the
    # WHOLE file -- is NOT a rule git has: an explicit `diff` attribute
    # forces a text diff despite the NUL (round 21, B3; reproduced,
    # numstat `-/-` becomes `2/0`). The claim is withdrawn here as it was
    # withdrawn two hundred lines above, and the refusal stays for the
    # harm that IS a property of the bytes: display.
    #
    # The refusal is over the FILE, not the row: the blindness is the
    # file's, and a list whose other rows a reviewer cannot read either
    # is not a list this rule may consult. It names the row NUMBER and
    # the CODEPOINT -- never the content, which is the same discipline
    # every other refusal in this parser keeps.
    # An INTERIOR carriage return, which the class above deliberately does
    # not carry. `\s*` in the row grammar CONSUMES it, so
    # `<path> | sha256:<hex> | <CR># reviewed` reached the reason predicate
    # as `# reviewed`, waived at rc 0, and git emitted the CR raw -- the
    # row renders overwritten in the terminal that reviews it (text lane,
    # round 20; reproduced). The predicate can only judge what the grammar
    # hands it, so the question is asked HERE, where the physical row still
    # exists. A row ENDING in CR is untouched: that is the CRLF checkout
    # this parser has always accepted, and it is the only reason `\r` is
    # outside the class above.
    for rowno, raw in enumerate(decoded.split("\n"), 1):
        if "\r" in raw.rstrip("\r"):
            raise PersonalPathUnreadable(
                "the allowlist carries a carriage return INSIDE row %d "
                "(not as its line ending); git emits it raw and the row "
                "renders overwritten, so NONE of the rows waives anything "
                "(remove it, then re-run)" % rowno)
    control = _PERSONAL_PATH_ALLOWLIST_CONTROL_RE.search(decoded)
    if control is not None:
        raise PersonalPathUnreadable(
            "the allowlist carries the control character U+%04X on row "
            "%d; a control character rewrites how the row DISPLAYS in "
            "the terminal that renders it, so the row can say one thing "
            "to this parser and another to its reader -- NONE of them "
            "waives anything (remove the character, then re-run)"
            % (ord(control.group(0)),
               decoded.count("\n", 0, control.start()) + 1))
    for rowno, raw in enumerate(decoded.split("\n"), 1):
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            # A COMMENT is not a waiver, and until round 10 that meant
            # nothing read it at all: this file lives OUTSIDE both
            # `_PERSONAL_PATH_SCOPE` prefixes, so the rule never scans
            # it, and the parser skipped `#` lines before any predicate.
            # `archived from /Users/<name>/...` written one line above
            # the row it explains was therefore the one place in this
            # repository where a home path was examined by NOTHING
            # (mechanism lane, round 10, A-P2-2).
            # Same refusal a ROW naming a home directory gets, for the
            # same reason -- the waiver file is subject to the rule it
            # waives -- and it is reported by ROW NUMBER, so the fix is
            # the line the operator is already looking at. MEASURED on
            # the shipped allowlist before choosing this: 76 comment
            # lines, 0 of them malformed under this predicate.
            if _personal_path_hit_either(line):
                malformed.append(rowno)
            continue
        match = _PERSONAL_PATH_ROW_RE.match(line)
        if match is None:
            # Includes every row that carries no `sha256:<64 hex>` field:
            # a v3-shaped row, a truncated digest, a digest with a
            # non-hex character -- and, since the signer directive was
            # deleted with the rule waiver it fed, a leftover
            # `signer-fingerprint: <40 hex>` line from a v4.0 allowlist.
            # A row the parser cannot read WHOLE waives nothing and says
            # so (rc 1): an adopter upgrading is told which lines to
            # delete rather than having them silently ignored.
            malformed.append(rowno)
            continue
        rel = match.group(1)
        sha = match.group(2).lower()
        reason = match.group(3)
        if (
            reason == _PERSONAL_PATH_UNREASONED
            # A reason a reviewer cannot SEE is not a written decision:
            # zero-width and bidirectional characters satisfied `\S`
            # (mechanism lane, round 19; reproduced, rc 0 with the leak
            # waived). MALFORMED by number, like every other row this
            # parser cannot read.
            or not _personal_path_reason_is_visible(reason)
            or rel.startswith("/")
            or ".." in rel.split("/")
            # A row that itself names a home directory would be printed back
            # on a GREEN run (the reason is echoed grouped). Refused at the
            # source, so no printer ever sees it: the waiver file is subject
            # to the rule it waives, which is what makes it reviewable.
            or _personal_path_hit_either(line)
        ):
            malformed.append(rowno)
            continue
        if rel in entries or rel in seen_twice:
            malformed.append(rowno)
            seen_twice.add(rel)
            entries.pop(rel, None)
            continue
        entries[rel] = PersonalPathRow(
            sha256=sha, reason=reason, rowno=rowno)
    return entries, malformed


def personal_path_verdict(
    scan: PersonalPathScan,
    allowlist: Dict[str, "PersonalPathRow"],
    malformed: Optional[List[int]] = None,
) -> PersonalPathVerdict:
    """Split ``scan`` against the allowlist. Kept pure so tests drive it.

    There is ONE waiver -- a row pinned to the content's sha256 -- and a
    NAME hit short-circuits it: a path that names a home directory is
    unwaivable by a row and by anything a future version adds here,
    because the check sits above every branch that could forgive.
    Renaming the file is the only cure, which is what the report tells
    the reader.

    A row that names the file but pins OTHER bytes does not waive and
    does not fall through to "unwaived" either: it is `mismatched`, its
    own category, because the operator action is to re-read the file and
    re-record the digest rather than to write a fresh decision. A hit
    with no digest at all (nothing readable to pin) can never match a
    row, which is the fail-closed default.
    """
    unwaived: List[PersonalPathHit] = []
    waived: List[Tuple[str, str]] = []
    mismatched: List[str] = []
    for hit in scan.hits:
        if _PERSONAL_PATH_NAME_LINE in hit.lines:
            unwaived.append(hit)
            continue
        row = allowlist.get(hit.rel)
        if row is None:
            unwaived.append(hit)
            continue
        if hit.sha256 is None or row.sha256 != hit.sha256:
            mismatched.append(hit.rel)
            continue
        waived.append((hit.rel, row.reason))
    found = set(hit.rel for hit in scan.hits)
    stale = sorted(rel for rel in allowlist if rel not in found)
    return PersonalPathVerdict(
        unwaived=unwaived, waived=waived, stale=stale,
        malformed=list(malformed or []), mismatched=sorted(mismatched),
    )


def _report_personal_path_eol_suspicion(
    scan: "PersonalPathScan", allowlist: Dict[str, "PersonalPathRow"],
    verdict: "PersonalPathVerdict",
) -> None:
    """Name a mismatch that a checkout EOL filter explains.

    A clone with `core.autocrlf=true` (or any other checkout EOL
    filter) hands the worktree CRLF where the committed blob holds LF.
    Every shipped digest was taken over the LF bytes, so on such a
    checkout every row mismatches at once and the gate is permanently
    red for a reason nothing in its output explains -- the operator
    looks for an edit that was never made (pair-rail round 3, P2).

    It states WHAT was observed and not WHY: a deliberate CRLF edit
    produces the same evidence as a checkout filter, and the earlier
    wording asserted the filter (pair-rail round 4, P3).

    NOTHING IS WAIVED HERE. Waiving on the normalised digest would
    forgive bytes the scan did not hash, which is the one thing this
    rule refuses to do; hashing canonical git content instead is the
    index-vs-worktree boundary this pack declares and does not cross.
    So the verdict is unchanged -- rc 1, the files still named -- and
    this adds one line saying which knob to turn.
    """
    by_rel = dict((hit.rel, hit) for hit in scan.hits)
    suspect = [
        rel for rel in verdict.mismatched
        if by_rel.get(rel) is not None
        and by_rel[rel].sha256_lf is not None
        and allowlist.get(rel) is not None
        and allowlist[rel].sha256 == by_rel[rel].sha256_lf
    ]
    if not suspect:
        return
    print("    (%d of those differ from the recorded digest ONLY in "
          "line endings." % len(suspect))
    print("     That is what was observed, not why: a checkout EOL "
          "filter")
    print("     (`core.autocrlf`) and a deliberate CRLF edit look the "
          "same here.")
    print("     If it is the filter, `git config core.autocrlf input` "
          "or a")
    print("     `* text=auto eol=lf` attribute restores the bytes the "
          "digests")
    print("     were taken over. Nothing is waived on the folded "
          "digest.)")


def _print_personal_path_group(
    title: str, rows: List[str], cap: Optional[int] = None,
) -> None:
    """Print at most `cap` rows, then say how many hid. LAYOUT ONLY.

    `cap` defaults to `_PERSONAL_PATH_PRINT_CAP`, the FINDING cap: a
    red run names the first 20 and counts the rest, because the
    operator's next move is to open one of them.

    It does NOT escape. That is the cure for a collision the r13 print
    made reachable (mechanism lane, round 23; reproduced): a path
    becomes text in `_personal_path_mask_rel`, which escapes it, and
    this printer used to escape it AGAIN. Escaping twice is injective on
    its own; escaping twice HERE and once in the honoured block is not,
    because the image of the double escape meets the image of the single
    one -- an unwaived `docs/x<LF>y.md` and a waived file literally named
    `docs/x\x0ay.md` rendered as the same line in the same report.

    So there is ONE boundary and every caller crosses it: a path is
    passed to this function already masked. `title` is composed by this
    module and is not a path, so it is printed as it is written.
    """
    limit = _PERSONAL_PATH_PRINT_CAP if cap is None else cap
    if not rows:
        return
    print("  %s:" % title)
    for row in rows[:limit]:
        print("    - %s" % row)
    if len(rows) > limit:
        print("    ... and %d more" % (len(rows) - limit))


def _personal_path_display(path: Path, repo_root: Path) -> str:
    """``path`` relative to the repo when inside it, else its absolute form.

    The gate refuses to print a matched LINE; printing the absolute path of a
    file under the operator's home would put a home directory back into the
    output through the side door.
    """
    try:
        # MASKED, not returned raw (pair-rail round 2, P2): an in-repo
        # override such as `docs/-Users-<name>-x/allow.txt` put the owner
        # segment into the untracked notice and into the remediation
        # text. Only the OUTSIDE-repo branch went through the boundary,
        # as if a path inside the repository could not name a person.
        return _personal_path_mask_rel(
            path.resolve().relative_to(repo_root).as_posix())
    except Exception:
        # OUTSIDE the repository — `--personal-path-allowlist ~/somewhere`.
        # `str(path)` here was the same leak by the same side door (rail round
        # cure-1, P2): the name is all a reader needs to know WHICH file the
        # gate could not use, and the directory is what must not be printed.
        return "<outside the repository>/%s" % _personal_path_safe(path.name)


#: C0, DEL and C1 — every byte a terminal or a CI log reads as a COMMAND
#: rather than as text. `\n` is the one that matters most here: git allows a
#: newline in a tracked filename, which is why the scan enumerates with `-z`.
def _personal_path_renders_as_itself(value: str) -> bool:
    """True when no character of ``value`` needs escaping to be PRINTED.

    `str.isprintable()`, asked of the whole string, and the claim is
    exactly the stdlib's: False for the control, format, surrogate,
    private-use, unassigned and non-space separator categories. It is
    NOT a promise that every character is visible -- U+2800 BRAILLE
    PATTERN BLANK and U+034F COMBINING GRAPHEME JOINER are printable and
    render as nothing. That is the right shape for what this predicate
    is FOR: escaping, so two different files cannot print as one line,
    and so nothing that rewrites a terminal reaches the log. Invisibility
    is refused where invisibility is the harm -- in the reason
    predicate, which counts ink rather than asking a category. This replaced the
    codepoint range `[\x00-\x1f\x7f-\x9f]`, which named C0, DEL and C1
    and stopped there -- so a tracked filename carrying U+202E
    RIGHT-TO-LEFT OVERRIDE went through the escaper UNCHANGED and printed
    raw into the honoured-row log, the one place a waiver is visible at
    all since the r13 decision (mechanism lane, round 22; reproduced).

    The class was never "C0 plus C1". It is "a character that does not
    render as itself", and the standard library already answers that
    question for every category, including the ones a later Unicode
    revision adds: `Cc`, `Cf`, `Cs`, `Co`, `Cn`, `Zl`, `Zp` and the
    separators other than a plain space. One question, one authority,
    asked by both the escaper and the row emitter so they cannot drift --
    the same removal-not-enumeration move the reason predicate made one
    round earlier.
    """
    return value.isprintable()

#: The same class MINUS the three characters that are ordinary text in a
#: waiver list: `\t`, `\n`, and the `\r` the row loop already counts as
#: part of its physical line. Everything else in C0/DEL/C1 is refused
#: there rather than escaped, because an escaped control is a DIFFERENT
#: string to the row grammar.
#:
#: The harm is DISPLAY, and the claim is deliberately no larger than
#: that: ESC, VT, FF and DEL rewrite how a row renders in the terminal
#: that shows it, so a row can say one thing to this parser and another
#: to its reader. An earlier note here ALSO said a NUL makes git render
#: the whole list as `Binary files ... differ`. That is not a rule git
#: has -- an explicit `diff` attribute forces a text diff despite a NUL
#: (round 21, B3; reproduced, numstat `-/-` becomes `2/0`) -- and this
#: rule no longer rests on how git renders anything: see
#: `_personal_path_honoured_rows`, which states what was granted instead
#: of hoping somebody reads a diff.
_PERSONAL_PATH_ALLOWLIST_CONTROL_RE = re.compile(
    "[\x00-\x08\x0b\x0c\x0e-\x1f\x7f-\x9f]")


def _personal_path_escape_controls(value: str) -> str:
    r"""``value`` with every character that does not RENDER escaped.

    `\xNN` below U+0100, `\uXXXX` below U+10000, `\UXXXXXXXX` above it,
    so the escape is unambiguous at every width.

    A tracked path may contain a NEWLINE, and this rule prints paths. Printed
    verbatim, `docs/ok<newline>::warning::forged.md` puts a line beginning
    `::warning::` into the log — a GitHub Actions WORKFLOW COMMAND, forged by
    a file in the pull request the gate is judging (mechanism lane, round 12;
    reproduced). ESC sequences reach the same output and can rewrite the
    waived inventory as it is rendered.

    Escaping, not refusing: the operator still has to be able to SEE which
    path it is, and a refusal here would be a second, silent way for a file
    to escape the report.

    INJECTIVE, and that took a second round to get right. Escaping only the
    controls made `docs/x<newline>y.md` and the literal four-character
    `docs/x\x0ay.md` render IDENTICALLY (text lane, round 13; reproduced,
    COLLIDE: True) -- two different tracked files, one line in a report whose
    entire job is naming WHICH file leaked, and a hostile filename able to
    impersonate another one. The escape character is therefore escaped FIRST,
    which is the ordinary cure and the only one that keeps the mapping
    reversible: a backslash becomes two, then a control becomes `\xNN`.

    MEASURED on the shipped allowlist before this shipped: 0 of 242 waived
    paths, 0 of 242 reasons and 0 of 76 comment lines carry a control
    character or a backslash, so a green run prints exactly what it printed
    before.
    """
    out: List[str] = []
    for char in value.replace("\\", "\\\\"):
        if _personal_path_renders_as_itself(char):
            out.append(char)
        elif ord(char) < 0x100:
            out.append("\\x%02x" % ord(char))
        elif ord(char) < 0x10000:
            out.append("\\u%04x" % ord(char))
        else:
            out.append("\\U%08x" % ord(char))
    return "".join(out)


def _personal_path_hit_either(value: str) -> bool:
    """True when the RAW string or its NFKC folding names a home directory.

    Asking only the folded reading is a BYPASS, and it was live in three
    places: the allowlist ROW check, the comment check the round-10 cure
    added, and the redaction choke point below. NFKC turns a full-width
    owner segment into an ASCII one, and the ASCII one may be on the
    PLACEHOLDER list -- so `/Users/<full-width dev>/private`, a real and
    distinct directory, folded into `/Users/dev/private` and answered
    False (text lane, round 12; measured raw=True nfkc=False).

    Folding can only ever turn a person into a placeholder, never a
    placeholder into a person, so the raw reading is the one that must not
    be skipped. Both are asked; either is enough.
    """
    if line_is_personal_path_hit(value):
        return True
    return line_is_personal_path_hit(unicodedata.normalize("NFKC", value))


def _personal_path_safe(value: str) -> str:
    """``value``, unless it names a home directory — then a redaction.

    The choke point for everything this rule PRINTS that it did not
    compose itself: a waiver reason written by a human, an allowlist path
    outside the repository, a CLI token it is about to name as ignored. Each
    of those was measured leaking in its own way; they are one shape, and the
    predicate that decides a FINDING is the same predicate that decides
    whether the gate may echo a string. A rule that redacts what it found and
    prints what it was handed is not a rule about leaks.

    ONE deliberate exception, named here because this docstring used to
    claim there were none (text lane, round 19): the row offered by
    `--emit-personal-path-rows` is not prose, it is a line the PARSER has
    to read back, and the escaping this function does to stay injective --
    a backslash becomes two -- makes that line name a different path. That
    row is built from `hit.rel` under two explicit refusals instead (a path
    that names a home directory, and a path carrying a control character),
    which is the same containment reached without corrupting the key.
    """
    if _personal_path_hit_either(value):
        return "<redacted: names a home directory>"
    # Everything that leaves this function goes into a log a human and a CI
    # runner both read. The redaction above answers "may this be printed";
    # this answers "is what is printed still TEXT" (mechanism lane, round 12).
    return _personal_path_escape_controls(value)


def _personal_path_mask_owner(match, replacement: str) -> str:
    """``replacement`` for this owner segment -- unless it is a PLACEHOLDER.

    The mask asks the SAME question the matcher asks: is this lowercased
    owner segment on `_PERSONAL_PATH_PLACEHOLDERS`? `alice`, `bob`,
    `devuser`, `runner` are the segments the rule exists NOT to flag, and
    replacing them told a reviewer nothing while making two different
    tracked files -- and a real owner -- render as one line (mechanism
    lane, round 24; reproduced before it was believed).

    The RAW lowercased segment decides, and only it. NFKC folding can turn
    a full-width owner into an ASCII placeholder, never a placeholder into
    a person, so consulting the folded reading here is the bypass and not
    the safeguard -- the same asymmetry `_personal_path_hit_either` states
    from the other side.

    `match.group(0)` is returned verbatim rather than re-spelled: the point
    is that the reader can tell WHICH file, and `/Users//alice` and
    `-Users--alice` are not the same path as their normal forms. A
    function replacement is used, so what is returned is taken literally --
    no backslash re-interpretation on a path that carries one.
    """
    if match.group(1).lower() in _PERSONAL_PATH_PLACEHOLDERS:
        return match.group(0)
    return replacement


def _personal_path_mask_rel(rel: str) -> str:
    """``rel`` with every NON-PLACEHOLDER home-owner segment replaced.

    A finding a reviewer cannot LOCATE is not a finding, and a PATH hit
    handed straight to `_personal_path_safe` comes back as the whole string
    redacted. So the owner segment -- the only part that is the leak -- is
    replaced and the rest of the path survives. `_personal_path_safe` still
    runs last and owns the verdict: if the masking missed a form, the whole
    string is redacted and the gate loses precision, never containment.
    """
    masked = _PERSONAL_PATH_HOME_RE.sub(
        lambda m: _personal_path_mask_owner(m, "/home/<redacted-owner>"), rel)
    # No trailing `-` in the replacement: since the round-20 cure the
    # terminator is a LOOKAHEAD, so the separator is no longer consumed by
    # the match, and supplying it again rendered
    # `-Users-<redacted-owner>--project`. A mask has to follow the matcher
    # it masks (text lane of the battery, round 20).
    masked = _PERSONAL_PATH_SLUG_RE.sub(
        lambda m: _personal_path_mask_owner(m, "-Users-<redacted-owner>"),
        masked)
    return _personal_path_safe(masked)


def _oserror_reason(exc: Exception) -> str:
    """The REASON an OSError carries — never the path it names.

    `str(OSError)` renders as `[Errno 13] Permission denied: <filename>`, and
    that filename is ABSOLUTE. Printing it on the fatal path puts a home
    directory back into the output through the same side door
    `_personal_path_display` closes three lines up: a gate that refuses to
    quote the leak it found must not leak while REFUSING to scan.

    `strerror` is the reason with no path in it. When it is missing (an
    OSError raised without an errno, or a subclass carrying only args) the
    class name is the most that can be said without quoting a path — a vaguer
    message is a cheaper price than a second copy of the leak. BOTH rules of
    this module use it: the term rule terms-file fatal leaked the same way.

    It also serves `UnicodeDecodeError` (no `strerror`, so: the class name),
    which is why the parameter is typed `Exception`. A decode failure on an
    INPUT file is fatal here, and its str() would quote the offending BYTES.

    And `re.error`, which is the same shape one layer further in: a private
    term is compiled as a RAW REGEX, so a malformed one (`(?P</Users/<name>>)`)
    raises with the offending pattern inside the message — the home path
    the terms file exists to hide, printed by the machinery that hides it
    (pair-rail round 1, P1). Its class name is the bare word `error`, which
    says nothing, so this one case is named instead of classified.
    """
    if isinstance(exc, re.error):
        return "it contains an invalid regular expression"
    strerror = getattr(exc, "strerror", None)
    if strerror:
        return str(strerror)
    return exc.__class__.__name__


def _personal_path_honoured_rows(
    waived: List[Tuple[str, str]],
    allowlist: Dict[str, "PersonalPathRow"],
) -> Tuple[List[str], str]:
    """The row set this run HONOURED, one line each, and a digest over it.

    `<path> | sha256:<64 hex> | <reason>` -- the three fields of the row
    that granted, in the row's own grammar, sorted by path, UNCAPPED.

    This replaced a counted, capped, reason-grouped inventory, and the
    reason is the four rounds that ended in the decision above it.
    Rounds 18 to 21 defended a PREMISE -- that a waiver is reviewable
    because a human can read the allowlist in `git diff` -- and each
    round found another way to make git render that file unreadable: a
    NUL in the bytes, a `-diff` attribute, a named binary driver, a
    driver named `unspecified`, `core.bigFileThreshold=1` with no
    attribute at all. Every cure for those decided by a NAME, which is
    the one thing this rule refuses to do anywhere else.

    So the premise is gone, and with it the question. The gate asks git
    NOTHING about how the list renders. It states what it honoured on
    every run that reaches a VERDICT -- green, red, and on stderr under
    `--emit-personal-path-rows` -- and a reader who never opens a diff
    still sees the waiver that granted. A run that cannot READ its input
    returns 2 before any of this, and prints no set, because at that
    point there is no waiver set to state: an unreadable allowlist waives
    nothing, which is the fail-closed answer and not a silent one. Readability of the allowlist file in
    `git diff` is no longer a security property of this rule -- the
    sha256-pinned row is, and it is unchanged.

    Only rows that actually waived a file appear. A row matching no file
    waives nothing and is reported as stale; a row whose digest no
    longer matches waives nothing and is reported as mismatched.

    The DIGEST is over the canonical `<path>NUL<sha256>NUL<reason>` join
    of that set, in the same order, so two runs are comparable by one
    line. It is computed from the ROW values and not from the printed
    text: masking and escaping are display, and a digest that moved with
    the display would report a waiver change when only a rendering
    changed.

    `allowlist[rel]` cannot miss: `personal_path_verdict` builds every
    pair in ``waived`` from a row it found in this same mapping. Paths
    and reasons go through the maskers on the way OUT, like every other
    printer here, because this report reaches a public CI log.
    """
    canonical: List[str] = []
    rows: List[str] = []
    for rel, reason in sorted(waived):
        sha = allowlist[rel].sha256
        canonical.append("%s\0%s\0%s" % (rel, sha, reason))
        rows.append(
            "%s | sha256:%s | %s"
            % (_personal_path_mask_rel(rel), sha,
               _personal_path_safe(reason)))
    digest = hashlib.sha256(
        "\n".join(canonical).encode("utf-8")).hexdigest()
    return rows, digest


def _print_personal_path_honoured(
    rows: List[str], digest: str, stream,
) -> None:
    """Print the honoured set. No cap: a cap is a place a waiver hides.

    The old inventory was capped at 400 lines and said how many it hid,
    which is fine for a worklist and wrong for THIS: the hidden ones are
    exactly the ones nobody would see. The stream is a parameter because
    `--emit-personal-path-rows` owns stdout for rows meant to be pasted,
    so its copy goes to stderr.
    """
    print("  honoured allowlist rows (%d, set sha256:%s):"
          % (len(rows), digest), file=stream)
    for row in rows:
        print("    %s" % row, file=stream)


def _emit_personal_path_rows(scan: PersonalPathScan,
                             allowlist: Dict[str, "PersonalPathRow"]) -> int:
    """`--emit-personal-path-rows`: a row per file that is not waived TODAY.

    A convenience for the human who must then write each reason — the emitted
    reason is `REPLACE-WITH-REASON`, which the parser REFUSES, so a paste that
    skips the decision fails the gate instead of passing it.

    It emits for a file whose row exists but whose DIGEST no longer matches,
    because that is the ordinary workflow now: the file was edited, the
    waiver lapsed, and what the operator needs is the new digest. The reason
    still comes out unreasoned — a re-approval is a decision too.

    A hit with no digest is a NAME hit, and no row can waive a name. Those
    are COUNTED on stderr instead of printed as rows, because stdout here
    exists to be pasted into the allowlist and a row that the parser
    refuses by construction is not something to paste.
    """
    nameless = 0
    unexpressible = 0
    for hit in scan.hits:
        # The NAME first, in the SAME order the verdict uses it — nothing
        # waives a path. This ordering was a cure when a rule waiver was
        # consulted ahead of it and swallowed a mixed hit (pair-rail
        # round 1, P2, both lanes); the waiver is gone, and the ordering
        # stays because a mixed hit HAS a digest, so "no digest" was
        # never the full test for a name hit.
        if (hit.sha256 is None
                or _PERSONAL_PATH_NAME_LINE in hit.lines):
            nameless += 1
            continue
        row = allowlist.get(hit.rel)
        if row is not None and row.sha256 == hit.sha256:
            continue
        # The row is built from the path the PARSER will read, not from
        # the path the REPORT would print. `_personal_path_safe` is the
        # display choke point and, to stay injective, it doubles a
        # backslash: `docs/a\b.md` is a legal git path and came out of
        # it as `docs/a\\b.md`, which fails the probe below and was
        # counted "unexpressible" -- with a note blaming whitespace --
        # while a HAND-WRITTEN row for that same path parses and waives
        # (mechanism lane, round 18; reproduced). Display escaping is
        # not row grammar.
        #
        # The two properties that boundary owned here are kept as
        # explicit refusals, because both are real: a path that NAMES a
        # home directory must not be printed at all (round cure-2, P2),
        # and a path carrying a control character cannot be offered as
        # a row -- escaped it is a DIFFERENT path to the parser, and
        # raw it would put a terminal command in the output. Such a
        # file has to be RENAMED, not waived, which is what the note
        # below says.
        if (_personal_path_hit_either(hit.rel)
                or not _personal_path_renders_as_itself(hit.rel)):
            unexpressible += 1
            continue
        candidate = ("%s | sha256:%s | %s"
                     % (hit.rel, hit.sha256, _PERSONAL_PATH_UNREASONED))
        # The emitter is judged by the PARSER, not by its own formatting.
        # `docs/frozen log.md` is a valid git path and an INVALID row:
        # `_PERSONAL_PATH_ROW_RE` refuses whitespace and `|` in the path
        # field, so the advertised paste produced a MALFORMED row and the
        # frozen artifact ended with no usable waiver at all, from a mode
        # that had exited 0 (mechanism lane, round 11; reproduced).
        # Producer and consumer share one grammar: the row is offered only
        # if the parser that will read it accepts it AND resolves it back
        # to the same path.
        probe = _PERSONAL_PATH_ROW_RE.match(candidate)
        if probe is None or probe.group(1) != hit.rel:
            unexpressible += 1
            continue
        print(candidate)
    if nameless:
        print(
            "NOTE: %d file(s) hit on their own PATH and have no row form: "
            "rename them" % nameless, file=sys.stderr)
    if unexpressible:
        print(
            "NOTE: %d file(s) have a path this rule cannot offer as a row "
            "(whitespace, `|`, a control character, or a home directory "
            "written into the path itself) and have no row form: rename "
            "them — a row emitted for such a path is one the parser "
            "refuses, or one no reviewer could read"
            % unexpressible, file=sys.stderr)
    return 0


def report_personal_paths(
    repo_root: Path, allowlist_path: Path, fail_on_stale: bool = False,
    emit_rows: bool = False,
) -> int:
    """Run the rule. 0 = clean, 1 = findings, 2 = unreadable input."""
    allowlist: Dict[str, PersonalPathRow] = {}
    malformed: List[int] = []
    if not _personal_path_allowlist_is_tracked(
            repo_root, allowlist_path):
        # NOT fatal: an allowlist git cannot confirm is read as EMPTY,
        # exactly like an absent one, so every hit comes out unwaived.
        # The reason is PRINTED and not assumed — a gate that quietly
        # stops waiving looks identical to a gate that found nothing.
        # It goes to stderr under --emit-personal-path-rows, whose
        # stdout exists to be PASTED and must stay rows-only.
        print(
            "• personal-path: %s is not tracked by git — reading it "
            "as EMPTY, so no row waives"
            % _personal_path_display(allowlist_path, repo_root),
            file=(sys.stderr if emit_rows else sys.stdout),
        )
    else:
        try:
            allowlist, malformed = (
                load_personal_path_allowlist(allowlist_path))
        except PersonalPathUnreadable as exc:
            # The loader RAISES this -- for an allowlist that is a
            # directory or a device on disk, and for one git records as
            # a link -- and it is not an OSError, so it escaped the
            # tuple below as an rc-1 TRACEBACK whose frames name the
            # checkout (mechanism lane, round 10, A-P2-1; reproduced).
            # The comment on the tuple below is the post-mortem of the
            # identical bug with UnicodeDecodeError, one class earlier:
            # a fatal that is not NAMED here is a fatal that prints a
            # path. Same verdict as the scan's handler, rc 2, and the
            # message goes through the choke point because it is text
            # this module composed about a file it could not read.
            print(
                "FATAL: cannot read %s: %s"
                % (_personal_path_display(allowlist_path, repo_root),
                   _personal_path_safe(str(exc))),
                file=sys.stderr,
            )
            return 2
        except (OSError, UnicodeDecodeError, re.error) as exc:
            # Fail-CLOSED on INPUT, like the terms file: an allowlist
            # that exists and cannot be read — or cannot be DECODED —
            # leaves the rule unverified, not satisfied.
            # UnicodeDecodeError is NOT an OSError, so before it was
            # named here it escaped as a traceback (rc 1, absolute
            # checkout path in the frames) instead of this sanitised
            # rc 2.
            print(
                "FATAL: cannot read %s: %s"
                % (_personal_path_display(allowlist_path, repo_root),
                   _personal_path_safe(_oserror_reason(exc))),
                file=sys.stderr,
            )
            return 2
    if allowlist:
        # The REASON is the only text on a green run this module did not
        # compose, and v4.1 made it PRINTED: the waived inventory groups
        # 242 files under SEVEN human sentences. The redaction
        # choke point asks whether a string names a HOME DIRECTORY; it
        # cannot ask whether it names one of RULE 1's private terms,
        # because those are compiled from the repository root and the
        # choke point has none (text lane, round 12: leaving that open was
        # judged indefensible for a gate that ships).
        #
        # It does not need to. The reasons are read in ONE place, and that
        # place is called with `repo_root`. A row whose reason names a
        # private term is MALFORMED -- refused by row number, before any
        # printer sees it -- which is the same verdict a row naming a home
        # directory already gets, from the same file, for the same reason.
        # MEASURED on the shipped allowlist: 0 of 242 reasons match.
        try:
            terms = build_pattern(repo_root)
        except Exception as exc:
            # A BOUNDARY, not a type list -- the fifth time in this file.
            # Compiling a private-terms file is arbitrary regex work: 2 000
            # open parentheses raise `RecursionError`, which is not in any
            # of the three names this clause used to carry, and emit mode
            # RETURNS before `main()`'s catch-all -- so the traceback
            # escaped with rc 1 and the checkout path in its frames
            # (mechanism lane, round 14; this repository already has a
            # probe for that input).
            # Fail-CLOSED on INPUT, like every other unreadable input here:
            # a terms file that exists and cannot be read leaves the reasons
            # unverified, not verified.
            print(
                "FATAL: cannot read %s: %s"
                % (_PRIVATE_TERMS_RELPATH,
                   _personal_path_safe(_oserror_reason(exc))),
                file=sys.stderr,
            )
            return 2
        # BOTH readings, for the same reason the path predicate asks both:
        # a private term spelled with full-width characters passes a raw
        # search and is then printed into the waived inventory (mechanism
        # lane, round 14).
        offenders = [
            rel for rel in sorted(allowlist)
            if (terms.search(allowlist[rel].reason)
                or terms.search(unicodedata.normalize(
                    "NFKC", allowlist[rel].reason)))
        ]
        for rel in offenders:
            malformed.append(allowlist[rel].rowno)
            del allowlist[rel]
        malformed.sort()
    try:
        scan = scan_personal_paths(repo_root)
    except PersonalPathUnreadable as exc:
        print("FATAL: cannot read in-scope file %s"
              % _personal_path_safe(str(exc)), file=sys.stderr)
        return 2
    except OSError as exc:
        # The ENUMERATION failed, not one file: the index query the walker
        # runs, or git itself. `PersonalPathUnreadable` names the first case
        # only, so this used to escape as an UNCAUGHT exception -- and an
        # uncaught exception prints a traceback whose FRAME lines carry the
        # absolute checkout path, which is the one string this rule exists to
        # keep out of the output (text lane, land round 1; reproduced by
        # injecting PermissionError into the walker before it was believed).
        # Same sanitised exit as every other fatal in this rule.
        print("FATAL: cannot enumerate in-scope files: %s"
              % _personal_path_safe("%s: %s" % (type(exc).__name__, exc)),
              file=sys.stderr)
        return 2

    verdict = personal_path_verdict(scan, allowlist, malformed)
    # FIRST, and on EVERY run: the honoured set is the same statement
    # whether the verdict is green or red, and `--emit-personal-path-rows`
    # returns before a verdict is printed at all. Its stdout must stay
    # rows-only, so its copy goes to stderr.
    _print_personal_path_honoured(
        *_personal_path_honoured_rows(verdict.waived, allowlist),
        stream=(sys.stderr if emit_rows else sys.stdout))

    if emit_rows:
        # MALFORMED rows are not suppressed by this mode. The rows on
        # stdout are computed AGAINST the waiver set, so a waiver set the
        # parser could not read whole makes the emission itself
        # unreliable — and returning 0 here told an operator who had just
        # seen rc 1 that the problem had gone away (pair-rail round 2,
        # P2). stdout stays rows-only; the reason goes to stderr.
        rc = _emit_personal_path_rows(scan, allowlist)
        if malformed:
            print(
                "NOTE: %d malformed allowlist row(s) — the rows above "
                "were computed against a waiver set that does not parse; "
                "fix those rows and re-run" % len(malformed),
                file=sys.stderr)
            return 1
        return rc

    if verdict.stale:
        # Advisory by design: a row waives ONE path, so a row matching nothing
        # waives nothing. Fatal-by-default would turn every archived plan —
        # and every adopter checkout, which has none of these artifacts — red.
        print("• personal-path: %d allowlist row(s) match no file (stale)"
              % len(verdict.stale))

    if not (verdict.unwaived or verdict.malformed or verdict.mismatched):
        if fail_on_stale and verdict.stale:
            print("❌ personal-path: stale allowlist rows, with --fail-on-stale")
            # MASKED here, because the printer no longer escapes: the
            # stale list is the one place that handed it raw rels.
            _print_personal_path_group(
                "STALE",
                [_personal_path_mask_rel(rel) for rel in verdict.stale])
            return 1
        print("✓ personal-path: no absolute home paths outside the allowlist "
              "under docs/ or .claude/plans/ (%d row(s) honoured, above)"
              % len(verdict.waived))
        return 0

    print("❌ personal-path: absolute home path(s) with no allowlist row")
    rows: List[str] = []
    name_hits = False
    for hit in verdict.unwaived:
        for lineno in hit.lines:
            if lineno == _PERSONAL_PATH_NAME_LINE:
                name_hits = True
            rows.append("%s:%d"
                        % (_personal_path_mask_rel(hit.rel), lineno))
    _print_personal_path_group("file:line", rows)
    _print_personal_path_group(
        "row sha256 no longer matches the file (re-read it, then record "
        "the new digest)",
        [_personal_path_mask_rel(rel) for rel in verdict.mismatched],
    )
    _report_personal_path_eol_suspicion(scan, allowlist, verdict)
    if name_hits:
        print("    (`:0` = the PATH itself names a home directory. Rename")
        print("     the file -- an allowlist row naming one is refused.)")
    # Row NUMBERS, composed here: nothing of the file's content reaches
    # this list, which is why it needs no masking now that the printer
    # does none.
    _print_personal_path_group(
        "MALFORMED allowlist rows (expected `<path> | sha256:<64 hex> | "
        "<reason>`)",
        ["row %d" % rowno for rowno in verdict.malformed],
    )
    print("")
    print("Cure, in order of preference:")
    print("  1. remove the absolute path — a placeholder (/Users/<user>/, "
          "$HOME, ~) says the same thing;")
    print("  2. if the file is a FROZEN artifact that must not be rewritten, "
          "add ONE row per file to")
    print("     %s" % _personal_path_display(allowlist_path, repo_root))
    print("     in the form `<path> | sha256:<64 hex> | <reason>`, and")
    print("     COMMIT IT IN THE SAME CHANGE so the waiver is reviewable")
    print("     — an allowlist git does not TRACK is read as empty. The")
    print("     digest pins the row to the bytes you read: edit the file")
    print("     and the waiver lapses, on purpose. Rows to start from,")
    print("     digests already filled in:")
    print("       python3 .claude/scripts/check_contamination.py "
          "--emit-personal-path-rows")
    print("NOTHING is exempt by NAME, by SUFFIX or by SIGNATURE — not")
    print("OWNER-*.sh, not *.asc, not approved.md. Every in-scope file is")
    print("scanned the same way, and the ONLY waiver is a row pinned to")
    print("the sha256 of the content it waives. A signed sentinel is")
    print("waived by such a row like anything else: the signature freezes")
    print("the bytes, so the digest cannot lapse behind your back.")
    return 1


class PersonalPathUsage(Exception):
    """A CLI token this gate refuses to guess at — fatal, never ignored."""


class _PersonalPathParser(argparse.ArgumentParser):
    """An `argparse` that refuses through THIS module's boundary.

    `ArgumentParser.error()` writes its message to stderr and exits 2,
    and that message QUOTES the offending token verbatim — measured:
    `--emit-personal-path-rows=<value>` prints
    `ignored explicit argument '<value>'`, and a value on this CLI can
    BE an absolute home path (a mistyped `--root`, a stray positional).
    A gate that refuses to quote the leak it FOUND must not quote one
    while refusing to RUN; this was the fourth instance of that shape,
    and it is cured where the other three were: at the boundary, by the
    rule's own predicate.

    Precision is traded for containment on purpose. `_personal_path_safe`
    replaces the WHOLE message when it names a home directory, so the
    operator loses the token and keeps the rc — which is the same bargain
    every other print site in this rule makes.
    """

    def error(self, message):        # argparse hook; always raises
        raise PersonalPathUsage(_personal_path_safe(message))


def _personal_path_option_near_miss(
    parser: "argparse.ArgumentParser", token: str,
) -> bool:
    """True when ``token`` is a PREFIX of a long option this parser knows.

    Derived from the parser rather than from a list written here: a list
    of option names beside the options themselves is a second place to
    forget, and the next flag added would quietly leave this check
    behind. `_actions` is argparse's own registry of what it accepts.

    `--` and `-` are excluded: the first is argparse's positional
    separator and a prefix of literally every long option.
    """
    head = token.split("=", 1)[0]
    if not head.startswith("--") or head in ("-", "--"):
        return False
    known = [opt for action in parser._actions
             for opt in action.option_strings]
    if head in known:
        return False
    return any(opt.startswith(head) for opt in known)


def _parse_args(argv: Optional[List[str]]) -> "argparse.Namespace":
    """CLI surface. No argument changes what the DEFAULT run enforces.

    Raises ``PersonalPathUsage`` for a token that is a prefix of a real
    option; `main` turns that into rc 2 with the token redacted, because
    a stray argument can BE an absolute home path and argparse's own
    usage error would print it verbatim.
    """
    # `allow_abbrev=False` (pair-rail land round 1, P2). argparse accepts a
    # unique PREFIX of a long option by default, so `--emit-personal-path-row`
    # — one character short, and a plausible typo — silently selected
    # `--emit-personal-path-rows` and put the gate into its non-gating mode:
    # rows on stdout, rc 0, no verdict. A security matcher must not have a
    # spelling that turns it off, and abbreviation is a whole family of them.
    parser = _PersonalPathParser(
        prog="check_contamination.py", allow_abbrev=False,
        description="Contamination gate: the term rule, plus the "
                    "personal-path rule over docs/ and .claude/plans/.",
    )
    parser.add_argument(
        "--root", default=None,
        help="repository to scan (default: the checkout this file lives in)",
    )
    parser.add_argument(
        "--personal-path-allowlist", default=None,
        help="allowlist for the personal-path rule (default: %s under the "
             "root). It must be a git-TRACKED file inside the root; "
             "anything else is read as EMPTY and waives nothing"
             % _PERSONAL_PATH_ALLOWLIST_REL,
    )
    parser.add_argument(
        "--emit-personal-path-rows", action="store_true",
        help="print an unreasoned allowlist row for every unwaived file; "
             "exit 0, 1 when the allowlist holds MALFORMED rows, or 2 "
             "when an input cannot be read (stdout stays rows-only in "
             "every case). The emitted reason is refused by the parser",
    )
    parser.add_argument(
        "--fail-on-stale", action="store_true",
        help="also fail when an allowlist row matches no file. OFF by "
             "default: the shipped allowlist names framework artifacts that "
             "an adopter checkout legitimately does not have",
    )
    # `parse_known_args`, NOT `parse_args`: the module this rule joined ignored
    # argv ENTIRELY, and the delivered wrapper `check-contamination.sh` execs
    # it with "$@" — so a strict parser turns an argument that used to do
    # nothing into an rc-2 CI failure in an adopter checkout this repo cannot
    # grep. The tolerance is preserved; the SILENCE is not. An ignored token is
    # NAMED on stderr, because `--fail-on-stalee` quietly doing nothing is how
    # an operator reads a check that never ran as a check that passed. The exit
    # code is unchanged — naming it is the whole cure.
    args, unknown = parser.parse_known_args(argv)
    # A token that is a PREFIX of a known option is the abbreviation
    # argparse used to accept, and it is fail-CLOSED here rather than
    # ignored: an operator who typed nine tenths of `--emit-personal-path-
    # rows` MEANT that flag, and the tolerance above exists for arguments
    # this module never had, not for near-misses on the ones it has. It
    # is the same fail-closed reading the allowlist parser gives a row
    # it cannot match WHOLE: MALFORMED and named, never a line skipped
    # while the operator believes it took effect.
    if args.emit_personal_path_rows and args.fail_on_stale:
        # One asks for a VERDICT to be stricter, the other suppresses the
        # verdict entirely. Accepted together, `--fail-on-stale` was
        # silently ignored and the run returned 0 where it returned 1
        # without the emit flag (pair-rail round 2, P2). Two flags whose
        # combination has no honest meaning are a usage error, not a
        # precedence rule for the operator to memorise.
        raise PersonalPathUsage(
            "--emit-personal-path-rows and --fail-on-stale contradict "
            "each other: one prints rows instead of a verdict, the other "
            "makes the verdict stricter")
    near = [tok for tok in unknown
            if _personal_path_option_near_miss(parser, tok)]
    if near:
        raise PersonalPathUsage(
            "unrecognised argument(s) %s — each is a PREFIX of a real "
            "option, which this gate refuses rather than guesses"
            % " ".join(_personal_path_safe(tok) for tok in near))
    if unknown:
        # The rule applies to this line too. A token can BE an absolute home
        # path (a stray positional, a mistyped `--root` value), and this NOTE
        # lands in the same public log as the findings — so the module runs its
        # own predicate over what it is about to echo. argparse-strict printed
        # the raw token in its usage error; ignoring it in silence printed
        # nothing at all. Naming it, redacted, is the only one of the three
        # that is both visible and safe.
        shown = [_personal_path_safe(tok) for tok in unknown]
        print(
            "NOTE: ignoring unrecognised argument(s): %s" % " ".join(shown),
            file=sys.stderr,
        )
    # An EXPLICITLY EMPTY path option is a usage error, not "not
    # given". Reading it by truthiness downstream silently selected the
    # default: `--root ""` scanned the checkout this file lives in and
    # returned green (pair-rail round 4, P1).
    for flag, value in (("--root", args.root),
                        ("--personal-path-allowlist",
                         args.personal_path_allowlist)):
        if value is not None and not str(value).strip():
            raise PersonalPathUsage(_PERSONAL_PATH_EMPTY_OPTION % flag)
    return args


def scan(repo_root: Path) -> List[Path]:
    """Return list of files where the pattern matched, excluding allowlist."""
    walker = FileWalker(
        repo_root=repo_root,
        mode="git",
        path_allowlist_exact=_ALLOWLIST_EXACT,
        path_allowlist_globs=_ALLOWLIST_GLOBS,
    )

    pattern = build_pattern(repo_root)

    violations: List[Path] = []
    for path in walker.iter_files():
        # Skip binaries by suffix
        if path.suffix.lower() in _SKIP_SUFFIXES:
            continue
        # Relative to the WALKER's root, which is already `.resolve()`d.
        # Using the caller's unresolved `repo_root` would raise here the
        # moment the two differ — which on macOS they routinely do
        # (`/tmp` is a symlink to `/private/tmp`).
        try:
            rel = path.relative_to(walker.repo_root).as_posix()
        except ValueError:
            rel = path.as_posix()
        if walker.is_allowlisted(path) and not is_never_allowlisted(rel):
            continue
        try:
            raw = path.read_bytes()
        except OSError:
            continue
        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            # rail round-1 P1. For an ordinary file this skip is fine: the
            # allowlist already decided the file is not interesting, and an
            # undecodable blob that slipped past _SKIP_SUFFIXES is noise.
            #
            # For the never-allowlisted class it is a FAIL-OPEN, and it was
            # reachable: ONE stray 0xFF byte anywhere in a plan `LEDGER.md`
            # made `scan()` skip the WHOLE file, marker and all — measured,
            # the probe returned `[]` on a ledger that carried a placeholder
            # handle in valid UTF-8 two lines below the bad byte.
            #
            # These files exist BECAUSE nobody reads them before they are
            # committed, so "the guard could not parse it" must not read the
            # same as "the guard found nothing". Fail CLOSED, per the
            # CLAUDE.md §4 rule for security matchers: unparseable INPUT is
            # blocked, never waved through. The OSError arm above stays
            # fail-OPEN on purpose — an unreadable file is INFRASTRUCTURE.
            if is_never_allowlisted(rel):
                violations.append(path)
            continue
        normalized = unicodedata.normalize("NFKC", text)
        if pattern.search(normalized):
            violations.append(path)
    return violations


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint — the term rule, then the personal-path rule."""
    try:
        args = _parse_args(argv)
    except PersonalPathUsage as exc:
        # Fail-CLOSED on a CLI token this gate will not guess at.
        # The message is already redacted at the raise site: a
        # stray argument can BE an absolute home path, and this
        # line lands in the same public log as the findings.
        print("FATAL: %s" % exc, file=sys.stderr)
        return 2
    try:
        repo_root = (
            Path(args.root).resolve() if args.root is not None
            else Path(__file__).resolve().parent.parent.parent
        )
    except Exception as exc:
        # A BOUNDARY, not a type list. `resolve()` raises
        # OSError for some failures and a bare RuntimeError for
        # a symlink LOOP on Python 3.9, so naming OSError alone
        # still left the traceback (pair-rail round 2, the same
        # shape twice in one file).
        # `resolve()` raises on a symlink LOOP, and it raised
        # BEFORE any guarded path: an rc-1 traceback carrying
        # the supplied path and this file's absolute location
        # (pair-rail round 2, P2). That path is chosen by
        # whoever runs the gate and can BE a home directory.
        print("FATAL: cannot resolve --root: %s"
              % _personal_path_safe(_oserror_reason(exc)),
              file=sys.stderr)
        return 2
    try:
        is_repo = ((repo_root / ".git").exists()
                   or (repo_root / ".git").is_dir())
    except Exception as exc:
        # The boundary above ENDED before this test, so an
        # unsearchable resolved root raised PermissionError here
        # and the traceback carried the root -- chosen by whoever
        # runs the gate, and able to BE a home directory
        # (pair-rail round 3, P2).
        print("FATAL: cannot inspect --root: %s"
              % _personal_path_safe(_oserror_reason(exc)),
              file=sys.stderr)
        return 2
    if not is_repo:
        # Not a git repo — exit 2
        print("FATAL: not inside a git repo", file=sys.stderr)
        return 2

    allowlist_path = (
        Path(args.personal_path_allowlist)
        if args.personal_path_allowlist is not None
        else repo_root / _PERSONAL_PATH_ALLOWLIST_REL
    )
    if args.emit_personal_path_rows:
        # Rows ONLY: the term report would make the output
        # unpasteable, and this mode exists to be pasted.
        return report_personal_paths(
            repo_root, allowlist_path, emit_rows=True,
        )

    try:
        violations = scan(repo_root)
    except Exception as exc:
        # A BOUNDARY, not a list of exception types. The term
        # scan reads a file and COMPILES what is in it as a raw
        # regex, so its failure modes are open-ended: OSError,
        # UnicodeDecodeError and re.error were each named here
        # after a rail round found them, and round 2 then found
        # RecursionError (2000 open parens in a private term),
        # which escaped as an rc-1 traceback carrying the
        # absolute checkout path. Enumerating exception types is
        # the same shape as enumerating safe filenames, and it
        # failed the same way three times.
        #
        # Anything that stops this scan leaves the pattern
        # incomplete, and an incomplete pattern is an unverified
        # scan, not a clean one (CLAUDE.md section 4: a GATE
        # fails closed on input). The REASON, never `exc`: its
        # str() carries an ABSOLUTE filename or the offending
        # PATTERN, and on an operator machine both are a home
        # path. The message names no path of its own either,
        # because after this catch-all the failure is no longer
        # necessarily the terms file.
        if isinstance(exc, (OSError, UnicodeDecodeError, re.error)):
            # Known INPUT failures of the terms file: keep the
            # precision where there is precision to be had.
            print(
                "FATAL: cannot read %s: %s"
                % (_PRIVATE_TERMS_RELPATH,
                   _personal_path_safe(_oserror_reason(exc))),
                file=sys.stderr,
            )
        else:
            print(
                "FATAL: the term scan did not complete: %s"
                % _personal_path_safe(_oserror_reason(exc)),
                file=sys.stderr,
            )
        return 2

    # BOTH rules always run — a term hit must not hide a path hit —
    # and a fatal (2) must never be reported as a mere finding (1).
    rc_terms = _report_terms(violations, repo_root)
    rc_paths = report_personal_paths(
        repo_root, allowlist_path,
        fail_on_stale=args.fail_on_stale,
    )
    return max(rc_terms, rc_paths)


def _report_terms(violations: List[Path], repo_root: Path) -> int:
    """The term rule's report. NOT byte-identical to the pre-v4 output: paths go through `_personal_path_mask_rel`, the plan glob was corrected, and a Rule 2 note is appended (text lane, round 23, which found the old sentence still claiming otherwise). The SHAPE and the verdict are unchanged."""
    if not violations:
        print("✓ No contamination outside allowed zones")
        return 0

    print("❌ Contamination found in the following files:")
    for v in violations:
        rel = v.relative_to(repo_root)
        print("  - %s" % _personal_path_mask_rel(rel.as_posix()))
    print("")
    print("Allowed zones:")
    print("  - LICENSE")
    print("  - CHANGELOG.md")
    print("  - .claude/skills/domains/**")
    print("  - .claude/plans/* (the WHOLE plan tree, recursively — "
          "fnmatch `*` crosses `/`)")
    print("      EXCEPT LEDGER.md / LEDGER-ARCHIVE.md at any depth under")
    print("      .claude/plans/ — machine-appended, always scanned")
    print("      (such a file is ALSO reported when it is not valid UTF-8:")
    print("       unparseable input is blocked, not skipped)")
    print("  - npm/** (NPM shim — uses owner handle in URLs)")
    print("  - .github/workflows/validate.yml")
    print("  - .github/CODEOWNERS (live config — Owner handle expected)")
    print("  - .claude/scripts/check-contamination.sh")
    print("  - scripts/contamination-terms.txt (private terms list — not delivered)")
    print("  - .claude/scripts/tests/test_check_contamination.py (uses pattern as fixture)")
    print("  - CLAUDE.md (framework master context — Owner path expected)")
    print("  - RELEASE.md (release procedure — Owner path + canonical repo URL)")
    print("  - SECURITY.md (vulnerability disclosure — Owner contact + canonical URL expected)")
    print("  - docs/QUICKSTART.md (install instructions — canonical repo URL)")
    print("  - docs/UPGRADE-PROCEDURE.md (upgrade playbook — canonical repo for gh CLI)")
    print("  - docs/SLO-SLA.md (SLO doc — references named adopter for production data point)")
    print("  - .claude/scripts/check-framework-updates.sh (tool — default upstream URL)")
    print("  - templates/.github/workflows/* (copies of live CI files)")
    print("")
    print("NOTE: those zones exempt the TERM rule only. Absolute home")
    print("paths under docs/ and .claude/plans/ are governed by the")
    print("personal-path rule, which no zone above can waive.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
