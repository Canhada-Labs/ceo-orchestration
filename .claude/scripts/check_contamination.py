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
      personal-path allowlist, or a file this scan had to read
      that exists and cannot be read; or an enumeration of the
      index the scan cannot prove it covered)
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
from _lib._contamination import bind_personal_paths as _bind_personal_paths
from _lib._contamination import personal_path_policy as _personal_path_policy
from _lib._contamination import personal_path_scanner as _personal_path_scanner
from _lib._contamination.term_scan import find_violations as _find_term_violations


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
    # Only real ABSENCE means "no private terms". `is_file()` also said False for a
    # dangling link and a directory, which dropped the whole term list in silence.
    if not os.path.lexists(path):
        return []
    if not stat.S_ISREG(os.stat(path).st_mode):  # a FIFO would block the read below
        raise OSError(errno.EINVAL, "not a regular file")
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


# Rule 2 policy data lives with its detailed rationale; keep every mutable
# symbol exposed on this facade for established monkeypatch-based callers.
from _lib._contamination import personal_constants as _personal_constants
for _key, _value in vars(_personal_constants).items():
    if _key.startswith("_PERSONAL_PATH_"):
        globals()[_key] = _value
del _key, _value

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


#: `git ls-files -s` mode of a submodule entry: it has no blob in this repository,
#: so it is the one mode RULE 1 releases by name (and only this one).
_TERM_GITLINK_MODE = "160000"

# ---------------------------------------------------------------------------
# RULE 1 (`scan`) — census of the borders where it could answer "clean" without
# having looked, taken before changing it (PLAN-186-FOLLOWUP AC-7; item 11 of the
# 1.4.4 backlog: the pack fell twice in the rail, by edges AC-7 had not listed).
# CURED, each with a test named test_fu144_* in test_check_contamination_personal_path.py:
#   * empty or partial walk: FileWalker turns a git failure into an empty iterator.
#     The set of paths seen must COVER the index (a set, not a count, for the reason
#     RULE 2 paid for in pair-rail S344 round 3);
#   * an index that cannot be read (git missing, timeout, rc != 0): refused;
#   * a name that is not valid UTF-8: both sides of the proof decode with
#     errors="replace", so two such names collapse into one and the sets compare equal
#     over an unread file. Refused over the WHOLE index before any comparison; RULE 2's
#     scope exception does not apply, because this rule's scope is every tracked path;
#   * a tracked symlink (120000): its blob is the target STRING. read_bytes() followed
#     it, so a term in the payload was never read and someone else's file was judged;
#   * an index mode other than file, executable, link or gitlink: refused;
#   * a file that exists and cannot be read, or a non-regular inode at a tracked path
#     (a FIFO used to hang the read): rc 2. This reverses a deliberate "fail-OPEN,
#     INFRASTRUCTURE" note; it is a gate, not a hook, as _personal_path_assert_enumerable
#     already argues, so nothing here blocks a session;
#   * a terms file that is not a regular file was read as absent (`_load_private_terms`).
# DECLARED, not cured:
#   * one stray non-UTF-8 byte still makes this rule skip an ordinary file whole (a term
#     beside it goes unseen). Outside the LEDGER class that is a pinned decision, not an
#     oversight: test_an_undecodable_non_plan_file_is_still_skipped calls it what keeps
#     the exception narrow. Changing it is the Owner's call, not this pack's;
#   * the path allowlist remains an exemption; all other indexed blobs are scanned;
#   * a UTF-16 document does not match;
#   * the index is enumerated and the worktree is read, as in RULE 2's blind spots;
#   * a U+FFFD that is really in a tracked name is refused too (the safe direction).
# ---------------------------------------------------------------------------


# Export extracted declarations, binding their code to the facade globals.
# Fail-closed index proofs and monkeypatch interception retain one namespace.
from types import FunctionType as _FunctionType
from _lib._contamination import (
    personal_facade_io as _personal_facade_io,
    personal_reporting as _personal_reporting,
    cli_checks as _cli_checks,
)
for _component in (_personal_facade_io, _personal_reporting, _cli_checks):
    for _name, _original in vars(_component).items():
        if isinstance(_original, _FunctionType) and _original.__module__ == _component.__name__:
            _bound = _FunctionType(
                _original.__code__, globals(), _original.__name__,
                _original.__defaults__, _original.__closure__,
            )
            _bound.__kwdefaults__ = _original.__kwdefaults__
            _bound.__annotations__ = dict(_original.__annotations__)
            _bound.__dict__.update(_original.__dict__)
            _bound.__qualname__ = _original.__qualname__
            _bound.__module__ = __name__
            globals()[_name] = _bound
        elif isinstance(_original, type) and _original.__module__ == _component.__name__:
            globals()[_name] = _original

_bind_personal_paths(globals(), _personal_path_scanner)
_bind_personal_paths(globals(), _personal_path_policy)
_personal_path_verdict_impl = personal_path_verdict
# Publish the wrapper over the original policy implementation.
_original = _personal_facade_io.personal_path_verdict
_bound = _FunctionType(_original.__code__, globals(), _original.__name__,
                       _original.__defaults__, _original.__closure__)
_bound.__annotations__ = dict(_original.__annotations__)
_bound.__module__ = __name__
personal_path_verdict = _bound
del _component, _name, _original, _bound

if __name__ == "__main__":
    sys.exit(main())
