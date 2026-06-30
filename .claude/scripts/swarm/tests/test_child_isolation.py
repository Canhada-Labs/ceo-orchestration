"""ADR-136-AMEND-2 §4.3 — per-child audit-log isolation tests.

Verifies child_audit_env mints a distinct CEO_AUDIT_LOG_DIR per child
slot, honors an existing root, never mutates base_env, and is
idempotent for a repeated slot. Pure env derivation — no I/O, no git,
no network.
"""
from __future__ import annotations

import tempfile
from pathlib import Path

from .._child_isolation import (
    AUDIT_DIR_ENV,
    CHILD_DIR_PREFIX,
    child_audit_dir,
    child_audit_env,
    child_audit_root,
)


# -----------------------------------------------------------------------
# Two children -> two distinct dirs
# -----------------------------------------------------------------------
def test_two_children_distinct_dirs() -> None:
    base = {AUDIT_DIR_ENV: "/run/audit"}
    env0 = child_audit_env(base, 0)
    env1 = child_audit_env(base, 1)

    assert env0[AUDIT_DIR_ENV] != env1[AUDIT_DIR_ENV]
    assert env0[AUDIT_DIR_ENV] == str(Path("/run/audit") / "child-0")
    assert env1[AUDIT_DIR_ENV] == str(Path("/run/audit") / "child-1")


def test_child_dir_nested_under_root_with_prefix() -> None:
    base = {AUDIT_DIR_ENV: "/run/audit"}
    env = child_audit_env(base, 7)
    child = Path(env[AUDIT_DIR_ENV])
    assert child.name == "{}{}".format(CHILD_DIR_PREFIX, 7)
    assert child.parent == Path("/run/audit")


# -----------------------------------------------------------------------
# base_env object not mutated
# -----------------------------------------------------------------------
def test_base_env_not_mutated() -> None:
    base = {AUDIT_DIR_ENV: "/run/audit", "OTHER": "keep"}
    snapshot = dict(base)
    base_id = id(base)

    out = child_audit_env(base, 3)

    # original mapping untouched (same value, same object)
    assert base == snapshot
    assert id(base) == base_id
    # returned dict is a different object
    assert out is not base
    # unrelated keys carried through to the copy
    assert out["OTHER"] == "keep"
    # only the audit dir differs from the source
    assert out[AUDIT_DIR_ENV] != base[AUDIT_DIR_ENV]


def test_base_env_without_audit_dir_not_mutated() -> None:
    base = {"PATH": "/usr/bin"}
    snapshot = dict(base)

    out = child_audit_env(base, 0)

    # base had no audit dir and still has none after the call
    assert base == snapshot
    assert AUDIT_DIR_ENV not in base
    # the copy gained a per-child audit dir
    assert AUDIT_DIR_ENV in out
    assert out["PATH"] == "/usr/bin"


# -----------------------------------------------------------------------
# Root honored when present
# -----------------------------------------------------------------------
def test_root_honored_from_base_env() -> None:
    base = {AUDIT_DIR_ENV: "/custom/run/root"}
    assert child_audit_root(base) == Path("/custom/run/root")

    env = child_audit_env(base, 2)
    assert env[AUDIT_DIR_ENV] == str(Path("/custom/run/root") / "child-2")


def test_default_root_under_tmp_when_unset() -> None:
    base = {"PATH": "/usr/bin"}  # no CEO_AUDIT_LOG_DIR
    root = child_audit_root(base)
    tmp = Path(tempfile.gettempdir())

    # default root lives under the OS tmp dir, NOT the bare $HOME chain
    assert tmp in root.parents or root.parent == tmp
    # and the child dir nests under it
    env = child_audit_env(base, 4)
    assert env[AUDIT_DIR_ENV] == str(root / "child-4")


def test_default_root_distinct_from_parent_live_chain() -> None:
    # When unset, children must NOT resolve to the same dir for two slots
    base = {"HOME": "/home/dev"}
    env0 = child_audit_env(base, 0)
    env1 = child_audit_env(base, 1)
    assert env0[AUDIT_DIR_ENV] != env1[AUDIT_DIR_ENV]
    # never the bare home audit dir
    assert "/home/dev" not in env0[AUDIT_DIR_ENV]


# -----------------------------------------------------------------------
# Idempotent for the same slot
# -----------------------------------------------------------------------
def test_idempotent_same_slot() -> None:
    base = {AUDIT_DIR_ENV: "/run/audit"}
    a = child_audit_env(base, 5)
    b = child_audit_env(base, 5)
    assert a == b
    assert a[AUDIT_DIR_ENV] == b[AUDIT_DIR_ENV]
    # repeated derivation is stable across the helper layers too
    assert child_audit_dir(base, 5) == child_audit_dir(base, 5)


def test_int_coercion_of_slot() -> None:
    # bool is an int subclass; ensure plain-int rendering (no "True")
    base = {AUDIT_DIR_ENV: "/run/audit"}
    env = child_audit_env(base, 0)
    assert env[AUDIT_DIR_ENV].endswith("child-0")


# -----------------------------------------------------------------------
# Returned dict is a plain, independently-mutable dict
# -----------------------------------------------------------------------
def test_returned_dict_is_independent() -> None:
    base = {AUDIT_DIR_ENV: "/run/audit"}
    out = child_audit_env(base, 1)
    out["EXTRA"] = "x"
    assert "EXTRA" not in base
