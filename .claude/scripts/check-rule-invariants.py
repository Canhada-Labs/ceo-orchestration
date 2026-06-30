#!/usr/bin/env python3
"""check-rule-invariants.py — fail-closed phrase-DELETION / parity detector.

PLAN-139 Wave A. Catches a load-bearing "spine" phrase being silently
dropped from a first-party TRACKED doc (``CLAUDE.md``, ``PROTOCOL.md``)
during a careless compaction or rewrite. Each invariant pins a phrase to
the file(s) it must appear in; if the (normalized) phrase is no longer a
substring of a listed file's (normalized) content, the check fails CLOSED
(exit 1) and names the ``id + file + phrase`` of every miss.

## What this is NOT

This is **parity tooling, NOT a tamper / security control.** It detects
*deletion* (a spine phrase vanishing), not *corruption*. A phrase that is
still present but has been semantically neutered — surrounded by negating
text, moved into an example, contradicted two lines later — PASSES this
check. That is acceptable and by design: a substring-presence detector
cannot and does not verify the surrounding semantics. For tamper
detection use the HMAC-chained audit log + canonical-edit ceremony; this
script only answers "is the load-bearing phrase still literally here?".

## Normalization

Both the pinned phrase and each file's content are, in a single pass:
  1. NFKC-normalized (so e.g. full-width / compatibility variants and
     composed/decomposed forms compare equal), then
  2. whitespace-collapsed — every run of whitespace (spaces, tabs,
     newlines) becomes a single ASCII space, then stripped.

Presence is a SUBSTRING test (>= 1 occurrence), never an exact count, so
a phrase split across a line break or padded with NBSP / doubled spaces
is still detected as present.

## Adopter skip

This check is framework-only. When the framework marker file
``.claude/adr/ADR-001-runtime-state-directory.md`` is ABSENT under the
target tree, the script exits 0 with an advisory note. The skip is keyed
on that specific ADR file — NOT on ``.claude/adr/`` existing (install.sh
ships ``.claude/adr/README.md`` to every adopter), NOT on a
``scripts/install.sh`` (adopters routinely ship their own installer, so it
is not a framework marker), and NOT on ``CLAUDE.md`` presence.

## Usage

    python3 .claude/scripts/check-rule-invariants.py
    python3 .claude/scripts/check-rule-invariants.py --repo <path>
    python3 .claude/scripts/check-rule-invariants.py --json
    python3 .claude/scripts/check-rule-invariants.py --list

Exit code: 0 when every invariant phrase is present (or adopter-skip), 1
when any invariant phrase is missing from a listed file.

## Stdlib-only

unicodedata + re + filesystem reads. No third-party deps, no eval, no
shell-out, no network, no YAML (ADR-002).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# The invariant registry.
#
# Each tuple is (id, phrase, files, rationale):
#   id        — short stable identifier (used in miss reports + --list).
#   phrase    — the load-bearing spine phrase. MUST already be NFKC-normal
#               (the self-test asserts phrase == NFKC(phrase)).
#   files     — tuple of repo-relative paths the phrase must appear in.
#   rationale — why this phrase is load-bearing (human note only).
#
# Every phrase below was grep-verified present (>= 1) in EVERY listed file
# on the live tree, and survives NFKC + whitespace-collapse. Pin SPINE
# phrases only — never anything from a CHANGELOG or volatile "Current
# Work" section.
# ---------------------------------------------------------------------------
INVARIANTS = (
    (
        "fail-open-on-infra",
        "Fail-open on infra",
        ("CLAUDE.md",),
        "Hooks never block the user session on infrastructure bugs — the "
        "fail-open discipline. Dropping it would invite fail-closed hooks.",
    ),
    (
        "spawn-agent-profile",
        "## AGENT PROFILE",
        ("CLAUDE.md",),
        "Spawn protocol requires the AGENT PROFILE section; check_agent_spawn "
        "blocks spawns missing it.",
    ),
    (
        "spawn-skill-content",
        "## SKILL CONTENT",
        ("CLAUDE.md",),
        "Spawn protocol requires the SKILL CONTENT section (load-bearing for "
        "named spawns).",
    ),
    (
        "spawn-file-assignment",
        "## FILE ASSIGNMENT",
        ("CLAUDE.md",),
        "Spawn protocol requires the FILE ASSIGNMENT section (load-bearing for "
        "named spawns).",
    ),
    (
        "stdlib-only",
        "stdlib only",
        ("CLAUDE.md",),
        "Critical rule: Python is stdlib only (zero third-party runtime deps). "
        "Losing this opens the door to dependency creep.",
    ),
    (
        "three-strike-rule",
        "three-strike",
        ("CLAUDE.md",),
        "Governance: the three-strike rule (PROTOCOL.md) — a core gate of the "
        "Plan -> Debate -> Execute machine.",
    ),
    (
        "tamper-evident-audit",
        "tamper-evident",
        ("CLAUDE.md",),
        "The tamper-evident audit log is the central auditability claim of the "
        "framework.",
    ),
    (
        "plan-debate-execute",
        "Plan → Debate → Execute",
        ("CLAUDE.md", "PROTOCOL.md"),
        "Cross-file invariant: the governance gating ceremony name must stay "
        "verbatim (arrows + spacing) in BOTH the contract and the protocol.",
    ),
    (
        "three-strike-protocol",
        "3-strike",
        ("PROTOCOL.md",),
        "PROTOCOL.md spells the rule '3-strike'; pinning the protocol-side "
        "spelling guards the governance machine's escalation rule.",
    ),
)

# Type alias for one registry row.
Invariant = Tuple[str, str, Tuple[str, ...], str]

# Framework-only marker: present in the framework repo, absent in an
# adopter's target tree. Keyed on this SPECIFIC ADR file — and ONLY this
# file. NOT on the .claude/adr/ directory (install.sh ships
# .claude/adr/README.md to every adopter — Codex C1) and NOT on
# scripts/install.sh: an adopter routinely ships its OWN scripts/install.sh,
# so counting it as a framework marker would defeat the adopter skip and
# red the adopter's validate gate on framework-only phrases it does not
# have (Codex pair-rail P2). The ADR record itself is framework-only:
# install.sh ships only adr/README.md, never the individual ADR-*.md files.
_PRIMARY_MARKER = Path(".claude") / "adr" / "ADR-001-runtime-state-directory.md"


def _normalize(text: str) -> str:
    """NFKC-normalize then collapse all whitespace runs to a single space.

    Single pass, deterministic, linear-time. The whitespace collapse uses
    ``\\s+`` (matches spaces, tabs, newlines, and other Unicode spaces
    after NFKC), so a phrase split across a line break or padded with
    NBSP / doubled spaces compares equal to its single-spaced form.
    """
    normalized = unicodedata.normalize("NFKC", text)
    return re.sub(r"\s+", " ", normalized).strip()


def _validate_registry(invariants: Tuple[Invariant, ...] = INVARIANTS) -> None:
    """Self-test the registry literals. Raises ValueError on a defect.

    Uses explicit ``raise ValueError`` (NOT ``assert``) so registry defects
    still fail CLOSED under ``python -O`` — which strips ``assert`` — since a
    fail-closed guard must never silently skip its own self-test (Codex
    pair-rail P2).

    Guarantees:
      - no phrase is empty / whitespace-only after normalization, and
      - every phrase literal is already NFKC-normalized (phrase ==
        NFKC(phrase)) so the on-disk constant is canonical.
    """
    for inv in invariants:
        inv_id, phrase, files, _rationale = inv
        if not (isinstance(inv_id, str) and inv_id):
            raise ValueError("invariant id must be non-empty")
        if not isinstance(phrase, str):
            raise ValueError("phrase must be a string for %r" % (inv_id,))
        if not _normalize(phrase):
            raise ValueError(
                "invariant %r has an empty/whitespace phrase after normalize"
                % (inv_id,)
            )
        if phrase != unicodedata.normalize("NFKC", phrase):
            raise ValueError(
                "invariant %r phrase literal is not NFKC-normalized" % (inv_id,)
            )
        if not (isinstance(files, tuple) and files):
            raise ValueError(
                "invariant %r must list at least one file" % (inv_id,)
            )


def _is_framework_repo(repo: Path) -> bool:
    """True only when the framework-only ADR-001 marker is present under
    ``repo``. Deliberately does NOT accept ``scripts/install.sh`` as a
    marker — adopters routinely ship their own installer, and counting it
    would defeat the adopter skip (Codex pair-rail P2)."""
    return (repo / _PRIMARY_MARKER).is_file()


def check_invariants(
    repo: Path,
    invariants: Tuple[Invariant, ...] = INVARIANTS,
) -> Dict[str, Any]:
    """Check every invariant against the tree rooted at ``repo``.

    Returns a report dict:
      {
        "skipped": bool,             # adopter-skip taken
        "reason": str,               # populated when skipped
        "checked": int,              # invariant rows examined
        "files_read": int,           # distinct files read
        "misses": [ {id, file, phrase, rationale, error?}, ... ],
        "ok": bool,                  # True when no misses (and not error)
      }

    A file that cannot be read (missing / OSError) is reported as a miss
    for every phrase pinned to it — a vanished file fails CLOSED, same as
    a vanished phrase.
    """
    _validate_registry(invariants)

    if not _is_framework_repo(repo):
        return {
            "skipped": True,
            "reason": (
                "adopter context: skipping rule-invariant check "
                "(framework marker %s absent)" % _PRIMARY_MARKER.as_posix()
            ),
            "checked": 0,
            "files_read": 0,
            "misses": [],
            "ok": True,
        }

    # Read + normalize each distinct listed file exactly once.
    norm_cache: Dict[str, Optional[str]] = {}
    misses: List[Dict[str, Any]] = []

    def _norm_file(rel: str) -> Optional[str]:
        if rel in norm_cache:
            return norm_cache[rel]
        path = repo / rel
        try:
            raw = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            norm_cache[rel] = None
            return None
        value = _normalize(raw)
        norm_cache[rel] = value
        return value

    for inv in invariants:
        inv_id, phrase, files, rationale = inv
        needle = _normalize(phrase)
        for rel in files:
            haystack = _norm_file(rel)
            if haystack is None:
                misses.append({
                    "id": inv_id,
                    "file": rel,
                    "phrase": phrase,
                    "rationale": rationale,
                    "error": "file missing or unreadable",
                })
                continue
            if needle not in haystack:
                misses.append({
                    "id": inv_id,
                    "file": rel,
                    "phrase": phrase,
                    "rationale": rationale,
                })

    files_read = sum(1 for v in norm_cache.values() if v is not None)
    return {
        "skipped": False,
        "reason": "",
        "checked": len(invariants),
        "files_read": files_read,
        "misses": misses,
        "ok": not misses,
    }


def _print_list() -> None:
    """Print the invariant registry (the --list output)."""
    print("# rule invariants (%d)" % len(INVARIANTS))
    for inv_id, phrase, files, rationale in INVARIANTS:
        print("  [%s]" % inv_id)
        print("    phrase:    %r" % phrase)
        print("    files:     %s" % ", ".join(files))
        print("    rationale: %s" % rationale)
        print()


def _cli(argv: List[str]) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Fail-closed phrase-deletion / parity detector for first-party "
            "tracked docs (PLAN-139 Wave A). Parity tooling, NOT a tamper guard."
        )
    )
    parser.add_argument(
        "--repo",
        "--repo-root",
        dest="repo",
        default=".",
        help="target tree root (default: cwd). --repo-root is an alias.",
    )
    parser.add_argument(
        "--json", action="store_true", help="machine-readable JSON output"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        dest="list_invariants",
        help="print the invariant registry constant and exit 0",
    )
    args = parser.parse_args(argv)

    # --list always self-tests the registry first (cheap correctness gate).
    if args.list_invariants:
        try:
            _validate_registry()
        except ValueError as exc:
            sys.stderr.write("check-rule-invariants: registry self-test FAILED: %s\n" % exc)
            return 1
        _print_list()
        return 0

    repo = Path(args.repo).resolve()
    try:
        report = check_invariants(repo)
    except ValueError as exc:
        # Registry literal defect — fail CLOSED, this is a code bug.
        sys.stderr.write("check-rule-invariants: registry self-test FAILED: %s\n" % exc)
        return 1

    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        if report["skipped"]:
            print(report["reason"])
        elif report["ok"]:
            print(
                "check-rule-invariants: OK — %d invariant(s) present across %d file(s)"
                % (report["checked"], report["files_read"])
            )
        else:
            sys.stderr.write(
                "check-rule-invariants: %d MISSING invariant phrase(s) "
                "(fail-CLOSED):\n" % len(report["misses"])
            )
            for m in report["misses"]:
                detail = m.get("error", "phrase not found")
                sys.stderr.write(
                    "  [%s] %s :: %r  (%s)\n"
                    % (m["id"], m["file"], m["phrase"], detail)
                )

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
