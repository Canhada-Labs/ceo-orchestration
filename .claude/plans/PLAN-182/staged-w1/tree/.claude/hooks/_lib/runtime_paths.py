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

Leaf module: stdlib only, imports nothing from ``_lib`` (loadable from
any hook, mirrors ``injection_salt``'s constraint). Python ≥ 3.9.
"""

from __future__ import annotations

import os
import stat as stat_mod
from pathlib import Path
from typing import Optional, Union

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


def runtime_state_dir() -> Path:
    """Return the per-project runtime state base dir (family root).

    Precedence: ``CLAUDE_PROJECT_DIR_NATIVE`` (whole-dir override) →
    ``$HOME/.claude/projects/<project_slug()>``. Callers create it with
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
    return _home() / ".claude" / "projects" / project_slug()


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
