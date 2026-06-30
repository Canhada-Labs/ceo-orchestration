"""Tests for optimizer._skeleton — kill-switches, env knobs, HMAC-safe audit shim.

The load-bearing assertion lives here: ``safe_emit`` must be a SILENT no-op for
an action that is not in ``audit_emit._KNOWN_ACTIONS`` (it must NOT call
``emit_generic``, so no ``audit-log.errors`` breadcrumb is written before the
canonical bundle registers the new actions).
"""

from __future__ import annotations

from unittest import mock

from optimizer import _skeleton


# --- kill_switch_off truth table --------------------------------------------

def test_kill_switch_off_truth_table(monkeypatch):
    for val in ("0", "false", "off", "no", "FALSE", "Off", " no "):
        monkeypatch.setenv("CEO_X", val)
        assert _skeleton.kill_switch_off("CEO_X") is True, val
    for val in ("1", "true", "on", "yes", "", "anything"):
        monkeypatch.setenv("CEO_X", val)
        assert _skeleton.kill_switch_off("CEO_X") is False, val


def test_kill_switch_default_on(monkeypatch):
    monkeypatch.delenv("CEO_MISSING", raising=False)
    # default '1' => not off
    assert _skeleton.kill_switch_off("CEO_MISSING") is False


def test_optimizer_enabled(monkeypatch):
    monkeypatch.delenv("CEO_OPTIMIZER", raising=False)
    assert _skeleton.optimizer_enabled() is True
    monkeypatch.setenv("CEO_OPTIMIZER", "0")
    assert _skeleton.optimizer_enabled() is False


# --- env_int clamping --------------------------------------------------------

def test_env_int_default_and_clamp(monkeypatch):
    monkeypatch.delenv("CEO_K", raising=False)
    assert _skeleton.env_int("CEO_K", 50, 10, 100) == 50
    monkeypatch.setenv("CEO_K", "5")      # below lo
    assert _skeleton.env_int("CEO_K", 50, 10, 100) == 10
    monkeypatch.setenv("CEO_K", "9999")   # above hi
    assert _skeleton.env_int("CEO_K", 50, 10, 100) == 100
    monkeypatch.setenv("CEO_K", "garbage")
    assert _skeleton.env_int("CEO_K", 50, 10, 100) == 50
    monkeypatch.setenv("CEO_K", "")       # empty -> default
    assert _skeleton.env_int("CEO_K", 50, 10, 100) == 50


def test_env_int_swapped_bounds(monkeypatch):
    monkeypatch.setenv("CEO_K", "42")
    # lo>hi is tolerated (swapped internally)
    assert _skeleton.env_int("CEO_K", 0, 100, 10) == 42


# --- estimate_tokens ---------------------------------------------------------

def test_estimate_tokens():
    assert _skeleton.estimate_tokens("") == 1
    assert _skeleton.estimate_tokens("abcd") == 1
    assert _skeleton.estimate_tokens("a" * 400) == 100


# --- _coerce_field: HMAC-safe scalars ---------------------------------------

def test_coerce_field_no_float_no_bool():
    assert _skeleton._coerce_field(True) == 1
    assert _skeleton._coerce_field(False) == 0
    assert isinstance(_skeleton._coerce_field(True), int)
    assert not isinstance(_skeleton._coerce_field(True), bool)
    assert _skeleton._coerce_field(3.7) == 4
    assert isinstance(_skeleton._coerce_field(3.7), int)
    assert _skeleton._coerce_field(42) == 42
    assert _skeleton._coerce_field("hi") == "hi"
    # bounded strings
    assert len(_skeleton._coerce_field("x" * 999)) == 200
    assert isinstance(_skeleton._coerce_field({"a": 1}), str)


# --- safe_emit: the load-bearing guard --------------------------------------

def test_safe_emit_unknown_action_is_silent_noop():
    """An unknown action must NOT reach emit_generic (no audit-log.errors spam)."""
    import types as _t
    stub = _t.ModuleType("audit_emit")
    stub._KNOWN_ACTIONS = {"some_real_action"}
    calls = []
    stub.emit_generic = lambda action, **kw: calls.append((action, kw))
    lib = _t.ModuleType("_lib")
    lib.audit_emit = stub
    with mock.patch.dict("sys.modules", {"_lib": lib, "_lib.audit_emit": stub}):
        assert _skeleton.safe_emit("__totally_unknown__", x=1) is False
        assert calls == []          # emit_generic NEVER called
        # a known action DOES get through (and is coerced)
        assert _skeleton.safe_emit("some_real_action", flag=True, ratio=2.6) is True
        assert calls[0][0] == "some_real_action"
        assert calls[0][1]["flag"] == 1        # bool coerced
        assert calls[0][1]["ratio"] == 3        # float coerced
        assert not isinstance(calls[0][1]["flag"], bool)


def test_safe_emit_import_failure_returns_false():
    import types as _t
    lib = _t.ModuleType("_lib")  # no audit_emit attribute
    with mock.patch.dict("sys.modules", {"_lib": lib}):
        # force the `from _lib import audit_emit` to fail
        assert _skeleton.safe_emit("anything") is False


def test_safe_emit_never_raises():
    # repo_root=None and a weird field type must not raise
    assert _skeleton.safe_emit("x", repo_root=None, weird=object()) in (True, False)
