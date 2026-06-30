"""ADR-136-AMEND-2 §4.3 — per-child audit-log isolation for swarm fan-out.

When a coordinator fans work out to N child agents, every child inherits
the parent session's environment — including ``CEO_AUDIT_LOG_DIR`` (the
canonical audit-dir contract resolved by ``audit_emit._audit_dir`` /
``audit_hmac._audit_dir_from_env``). If all children share the parent's
audit dir, their PreToolUse/PostToolUse emits land on the *parent's live
audit chain*. S185 watched exactly that vector grow the live chain
73 -> 1925 entries during a 101-sub-agent Workflow run: the children
share the parent's hook rail, and ``env -i`` does not isolate session
hooks (only explicitly-run code).

This module gives each child a *distinct* ``CEO_AUDIT_LOG_DIR`` under a
per-child subdir (``<root>/child-<slot>/``), so:

  * each child writes to its own audit dir + sidecars (key, last-hmac,
    chain-length counter) -> no cross-child counter sharing (the S168
    split-counter class), and
  * the parent's live chain is never touched by child emits.

The root is the parent's ``CEO_AUDIT_LOG_DIR`` when present (so children
nest under the run's audit root), else a safe default under a runtime /
tmp dir — never the bare ``$HOME`` audit dir, which is the live chain we
are trying to protect.

## Contract

``child_audit_env(base_env, child_slot)`` returns a *new* dict. The
``base_env`` mapping is COPIED and never mutated; only the returned copy
carries the per-child ``CEO_AUDIT_LOG_DIR``. The function is
deterministic / idempotent for a given (root, slot): the same inputs
always yield the same child dir.

This module is stdlib-only and never raises on the happy path — it
mints a directory string, it does not create or write any file.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Dict, Mapping


# Canonical audit-dir env var — matches audit_emit._audit_dir /
# audit_hmac._audit_dir_from_env. Kept as a module constant so the
# coupling to the kernel contract is one obvious edit-site.
AUDIT_DIR_ENV = "CEO_AUDIT_LOG_DIR"

# Per-child subdir prefix under the run's audit root.
CHILD_DIR_PREFIX = "child-"

# Stable bucket for the derived default root when the parent did not pin
# an audit dir. Lives under the OS tmp dir so child emits stay well off
# the live $HOME audit chain.
_DEFAULT_ROOT_LEAF = "ceo-swarm-children"


def child_audit_root(base_env: Mapping[str, str]) -> Path:
    """Resolve the root dir under which per-child audit dirs are nested.

    Precedence:

      ``CEO_AUDIT_LOG_DIR`` from ``base_env`` (the run's audit root) ->
      a safe default ``<tmpdir>/ceo-swarm-children`` (never the bare
      $HOME audit dir, which is the live chain we isolate children from).

    ``base_env`` is read only — never mutated.
    """
    root = base_env.get(AUDIT_DIR_ENV)
    if root:
        return Path(root)
    # No parent audit root pinned: derive a safe sandbox under the OS
    # tmp/runtime dir. tempfile.gettempdir() honors TMPDIR/TEMP and
    # always resolves to a writable location.
    return Path(tempfile.gettempdir()) / _DEFAULT_ROOT_LEAF


def child_audit_dir(base_env: Mapping[str, str], child_slot: int) -> Path:
    """Return the distinct audit dir for ``child_slot`` (no I/O).

    ``<root>/child-<slot>/`` where ``<root>`` comes from
    :func:`child_audit_root`. Deterministic for a given (root, slot).
    """
    return child_audit_root(base_env) / "{}{}".format(CHILD_DIR_PREFIX, int(child_slot))


def child_audit_env(base_env: Mapping[str, str], child_slot: int) -> Dict[str, str]:
    """Return a NEW env dict with a per-child ``CEO_AUDIT_LOG_DIR``.

    The returned dict is a shallow copy of ``base_env`` with
    ``CEO_AUDIT_LOG_DIR`` re-pointed at ``<root>/child-<slot>/`` so the
    child writes its audit log + HMAC sidecars under its own dir and the
    parent live chain is untouched.

    Invariants:

      * ``base_env`` is COPIED, never mutated (caller's mapping is safe
        to reuse for the next child).
      * Two distinct slots yield two distinct ``CEO_AUDIT_LOG_DIR``
        values.
      * Idempotent: the same ``(base_env, child_slot)`` always yields the
        same ``CEO_AUDIT_LOG_DIR``.
      * No directory is created here — this is pure env derivation; the
        child process / its audit writer mkdir's lazily on first emit.

    No file I/O, no network, never raises on the happy path.
    """
    # Shallow-copy into a plain dict so the result is a fresh, mutable
    # mapping the caller fully owns, and base_env is provably untouched.
    out: Dict[str, str] = dict(base_env)
    out[AUDIT_DIR_ENV] = str(child_audit_dir(base_env, child_slot))
    return out
