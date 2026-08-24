"""runtime_paths.py — THE single resolver for per-project runtime state.

PLAN-182 W1 deliverable. Implements the ADR-001 S318 amendment
(slug becomes normative) + ADR-079 S318 amendment (salt unit = project).

## Contract (ADR-001 S318 amendment, ratified 2026-08-20)

1. ``<project-slug>`` is the **native Claude Code path-based slug** of
   the project's absolute path: ``str(path)`` with every ``/`` replaced
   by ``-`` (e.g. ``/Users/u/repo`` → ``-Users-u-repo``). This is the
   SAME derivation the current harness uses for
   ``~/.claude/projects/<slug>/`` (memory, transcripts), so framework
   runtime state co-locates with harness state for the same project.
2. **One resolver, imported by the whole family.** No file in the
   audit/state family may re-derive the directory locally. Every module
   that previously built the literal
   ``$HOME/.claude/projects/ceo-orchestration`` delegates here.
3. **Family-atomicity:** ``runtime_state_dir()`` is the ONE base dir;
   log, key, lock, errors, ``.salt``, rotation siblings and sidecars
   are all resolved as children of it (per-family wrappers may keep
   their own more-specific env overrides, but their DEFAULT is this
   base — never a locally re-derived path).

## Precedence (highest first)

1. ``CLAUDE_PROJECT_DIR_NATIVE`` — documented whole-directory override
   (ADR-001 Decision; this module is its FIRST consumer — the original
   spec fiction of an override with zero consumers is repaired here).
2. ``$HOME/.claude/projects/<slug(project_dir())>`` where
   ``project_dir()`` is ``CLAUDE_PROJECT_DIR`` (the harness-set project
   root) when present, else ``os.getcwd()``.

## Slug-family archaeology (measured S319, do not "fix")

``~/.claude/projects/`` holds THREE spellings grown by different
eras/agents:

- ``--Users-...`` (double leading dash): legacy harness derivation
  (``'-' + path.replace('/', '-')``). Frozen legacy trees; never
  written by this module.
- ``-Users-...`` (single leading dash): CURRENT harness derivation and
  the ADR-001 normative form. This module emits ONLY this spelling.
- ``ceo-orchestration`` (bare literal): the four-month defect this
  module cures (587-file family, PLAN-182 W0). Reachable read-only via
  :func:`legacy_state_dir` for migration/W2 custody tooling ONLY.

## Symlink honesty

``project_dir()`` absolutizes (``os.path.abspath``) but does NOT
``realpath()``: the harness slugs the launch path as given, and native
alignment (co-location with harness memory) wins over symlink
canonicalization. Two spellings of one repo via symlinks therefore get
two state dirs — same behavior the harness itself has for its memory
dirs. Documented limitation, pinned by test.

## CLI contract (PLAN-182 OQ-6 — Owner decision 2026-08-22, landed S326)

Shell consumers get the SAME resolver, never a rebuilt literal::

    python3 .claude/hooks/_lib/runtime_paths.py [--state-dir | --slug |
                                                 --project-dir] [--project PATH]

- ``--state-dir`` (default): :func:`runtime_state_dir`; ``--slug``:
  :func:`project_slug`; ``--project-dir``: the slug input.
- ``--project PATH`` replaces the slug INPUT (``CLAUDE_PROJECT_DIR`` / cwd).
  ``CLAUDE_PROJECT_DIR_NATIVE`` still wins for ``--state-dir`` — it is the
  documented operator override, not a default.
- Read-only: prints ONE path + newline on stdout, creates nothing, exit 0.
  Usage error: exit 2, message on stderr, NOTHING on stdout (a caller doing
  ``dir="$(...)"`` must never capture prose as a path).
- ONE invocation convention. An inline ``python3 -c`` in a template would
  be a second one, and the class this cures is "a local branch that
  re-derives the path" (CLAUDE.md §4). Consumers: the two pre-push review
  gates in ``templates/{codex,grok}/``, ``ceo-backup.sh``, ``ceo-restore.sh``.

Leaf module: stdlib only, imports nothing from ``_lib`` (loadable from
any hook, mirrors ``injection_salt``'s constraint). Python ≥ 3.9.
"""

from __future__ import annotations

import os
import stat as stat_mod
import sys
from pathlib import Path
from typing import List, Optional, Union

__all__ = [
    "project_dir",
    "project_slug",
    "runtime_state_dir",
    "legacy_state_dir",
    "LEGACY_PROJECT_LITERAL",
]

# The literal the family grew for four months (PLAN-182 W0: 587 files).
# Exists ONLY so migration/W2 custody tooling has one named handle on
# the historical location. Runtime resolution NEVER falls back to it.
LEGACY_PROJECT_LITERAL = "ceo-orchestration"


def project_dir() -> Path:
    """Return the project's absolute path (the slug input).

    ``CLAUDE_PROJECT_DIR`` (set by the harness for hooks and most
    tool invocations) wins; ``os.getcwd()`` is the fallback for CLIs
    invoked from the repo root. Absolutized, NOT realpath'd (see
    module docstring §Symlink honesty).
    """
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(os.path.abspath(env))
    return Path(os.path.abspath(os.getcwd()))


def project_slug(path: Optional[Union["os.PathLike[str]", str]] = None) -> str:
    """Native path-based slug: absolute path with ``/`` → ``-``.

    ``/Users/u/my-repo`` → ``-Users-u-my-repo``. Dots, underscores and
    pre-existing dashes are preserved (the ADR-001 amendment normalizes
    ONLY the separator; the current harness does the same). This kills
    the cured defect class (two checkouts sharing a BASENAME never
    collide) but is NOT fully injective: paths differing only in
    dash-vs-slash positions (``/srv/a-b/c`` vs ``/srv/a/b-c``) share a
    slug — the SAME residual the native harness derivation has for its
    memory/transcript dirs (rail r2 C, declared; diverging from the
    native derivation would break co-location, an ADR-001 S318 Owner
    decision).
    """
    p = Path(os.path.abspath(os.fspath(path))) if path is not None else project_dir()
    return str(p).replace(os.sep, "-")


def _home() -> Path:
    home = os.environ.get("HOME")
    return Path(home) if home else Path.home()


def runtime_state_dir(
    project: Optional[Union["os.PathLike[str]", str]] = None,
) -> Path:
    """Return the per-project runtime state base dir (family root).

    Precedence: ``CLAUDE_PROJECT_DIR_NATIVE`` (whole-dir override) →
    ``$HOME/.claude/projects/<project_slug(project)>``. ``project`` (S326,
    CLI ``--project``) replaces only the slug INPUT; ``None`` keeps the
    ``CLAUDE_PROJECT_DIR`` / cwd derivation. Callers create it with
    mode ``0o700`` (creation stays at the call sites that already own
    mkdir + permission-validation semantics, e.g. ``spool_writer``).

    Deliberately uncached — the work is two ``os.environ.get``, an
    optional ``getcwd`` and one ``str.replace``. Callers that cache MUST key
    on every input that can change the result
    (``CLAUDE_PROJECT_DIR_NATIVE``, ``CLAUDE_PROJECT_DIR``, ``HOME``,
    and cwd when ``CLAUDE_PROJECT_DIR`` is unset) — the PLAN-182 W1
    spool cache cure.
    """
    native = os.environ.get("CLAUDE_PROJECT_DIR_NATIVE")
    if native:
        return Path(native)
    return _home() / ".claude" / "projects" / project_slug(project)


def ensure_state_dir(path: Optional[Path] = None,
                     tighten: bool = True) -> Path:
    """Create (if needed) and best-effort TIGHTEN the state dir to 0700.

    rail r2 F: the native slug dir often pre-exists 0755 (the harness
    creates it for memory/transcripts); ``mkdir(mode=0o700,
    exist_ok=True)`` does NOT change an existing dir mode, so the W1
    modes invariant needs an explicit, central self-heal (the
    ``spool_writer._state_dir`` precedent). Never raises: creators stay
    fail-open; on any error the caller proceeds with the path as-is.

    rail r5 hardening:
    - ``tighten=False`` (callers pass it when ANY env override selected
      the directory): only mkdir, NEVER chmod — a deliberately-0750
      compliance/vault dir chosen by the operator keeps its mode.
    - symlink guard: a user-owned symlinked state dir is left untouched
      (path-based chmod would FOLLOW the link and change the target);
      mirrors the spool_writer O_NOFOLLOW discipline at the cheap end.
    """
    d = path if path is not None else runtime_state_dir()
    try:
        d.mkdir(parents=True, exist_ok=True, mode=0o700)
        if not tighten:
            return d
        st = os.lstat(str(d))
        if stat_mod.S_ISLNK(st.st_mode):
            return d
        if (st.st_mode & 0o777) != 0o700 and st.st_uid == os.getuid():
            os.chmod(str(d), 0o700)
    except OSError:
        pass
    return d


def legacy_state_dir() -> Path:
    """The pre-W1 literal dir — migration/W2 custody tooling ONLY.

    Runtime code MUST NOT call this as a fallback: resolving state
    here re-opens the cross-tenant mixing the W1 closes. The name is
    deliberately loud so ``derive-audit-family.py --assert-migrated``
    style sweeps can allowlist the few sanctioned callers.
    """
    return _home() / ".claude" / "projects" / LEGACY_PROJECT_LITERAL


# ---------------------------------------------------------------------------
# CLI — the resolver for SHELL consumers (PLAN-182 OQ-6; Owner decision
# 2026-08-22, S322; landed S326).
#
# The two pre-push review gates delivered to adopters and the operator
# scripts ceo-backup.sh / ceo-restore.sh are bash. Without a CLI they rebuilt
# the literal locally — the class W1 closed for Python — and a review APPROVE
# recorded in one adopter satisfied the gate in ANOTHER (shared state dir).
# Contract: module docstring §CLI contract. Keep it a thin printer: every
# rule lives in the functions above, the CLI only chooses which one to call.
# ---------------------------------------------------------------------------

_CLI_MODES = ("--state-dir", "--slug", "--project-dir")
_CLI_USAGE = (
    "usage: runtime_paths.py [--state-dir | --slug | --project-dir] "
    "[--project PATH]\n"
    "  --state-dir     per-project runtime state dir (default)\n"
    "  --slug          native path-based project slug\n"
    "  --project-dir   the project dir the slug is derived from\n"
    "  --project PATH  derive for PATH instead of CLAUDE_PROJECT_DIR / cwd\n"
)


def _cli(argv: List[str]) -> int:
    """Parse ``argv`` (no argparse: keeps the leaf tiny and the usage text
    byte-stable) and print exactly one path. Returns the exit status."""
    mode = "--state-dir"
    mode_seen = False
    project: Optional[str] = None
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in _CLI_MODES:
            if mode_seen:
                sys.stderr.write("runtime_paths: one mode flag only\n" + _CLI_USAGE)
                return 2
            mode, mode_seen = arg, True
        elif arg == "--project":
            # A missing value must never swallow the NEXT option as a path
            # (pair-rail r6/r8 P2: `--project --slug` and `--project -h`
            # printed a valid-looking state dir for a project literally
            # named after the option). Any token that starts with "-" is an
            # option, not a PATH; a real path beginning with "-" is not
            # supported — use an absolute path.
            if i + 1 >= len(argv) or not argv[i + 1] or argv[i + 1].startswith("-"):
                sys.stderr.write("runtime_paths: --project needs a PATH\n" + _CLI_USAGE)
                return 2
            project = argv[i + 1]
            i += 1
        elif arg in ("-h", "--help"):
            sys.stdout.write(_CLI_USAGE)
            return 0
        else:
            sys.stderr.write("runtime_paths: unknown argument %r\n%s" % (arg, _CLI_USAGE))
            return 2
        i += 1
    if mode == "--project-dir":
        out = Path(os.path.abspath(project)) if project is not None else project_dir()
    elif mode == "--slug":
        out = project_slug(project)
    else:
        out = runtime_state_dir(project)
    sys.stdout.write("%s\n" % out)
    return 0


if __name__ == "__main__":
    sys.exit(_cli(sys.argv[1:]))
