"""Tests for PLAN-163 T3.2 — check_notification.py (Notification observer).

Covers the four contract pillars of the T3.2 hook:

  1. CLOSED VOCABULARY — the harness ``notification_type`` enum is OPEN;
     the hook normalizes to {agent_needs_input, agent_completed,
     permission_request, other} and an off-enum value coerces to ``other``
     WITHOUT the raw string ever persisting (no-value-echo).
  2. NO-VALUE-ECHO — ``message`` / ``title`` TEXT never reaches the audit
     log (or the errors sidecar); only ``has_title`` (bool) and
     ``message_sha256_prefix`` (12-hex hash prefix) persist.
  3. KILL-SWITCH — ``CEO_NOTIFICATION_TELEMETRY=0`` → ``{}`` exit 0, no
     read, no emit.
  4. INFRA FAIL-OPEN — garbage stdin / non-dict input → ``{}`` exit 0,
     breadcrumb only, never a crash (pure observer: stdout is ALWAYS
     ``{}``).

COUPLING NOTE (PLAN-135 W2 staged-test precedent): the hook + the
T3.1/T3.2-bearing ``audit_emit`` (323-action set) live ONLY in the
PLAN-163 staged pack until the pack ceremony copies them onto the
canonical positions. This test therefore resolves both CANONICAL-FIRST
(green in the post-apply tree) and falls back to the staged pack copy in
the live pre-ceremony tree.

PLAN-118 AC-B7 isolation: the staged ``_lib.audit_emit`` is bound in
``sys.modules`` AND as the ``_lib`` package attribute ONLY for the
duration of a test method (S228 lesson
[[feedback-fake-audit-emit-leaked-as-lib-package-attribute]]), restored
via addCleanup + re-asserted canonical in tearDown (PLAN-119 WS-C gate).
Env isolation via TestEnvContext (no bare os.environ writes outside it).

Stdlib-only, Python >= 3.9, ``from __future__ import annotations``.
"""

from __future__ import annotations

import hashlib
import importlib
import importlib.util
import io
import json
import os
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

# --- Repo-root discovery + canonical-first source resolution. ---
_THIS = Path(__file__).resolve()
_repo_root = None
for parent in _THIS.parents:
    if (parent / ".claude" / "hooks" / "_lib").is_dir() and (
        parent / ".claude" / "plans"
    ).is_dir():
        _repo_root = parent
        break
assert _repo_root is not None, "could not locate repo root from test path"

_LIVE_HOOKS = _repo_root / ".claude" / "hooks"
_STAGED_HOOKS = (
    _repo_root / ".claude" / "plans" / "PLAN-163" / "staged" / "main-pack"
    / ".claude" / "hooks"
)

_CANON_HOOK = _LIVE_HOOKS / "check_notification.py"
_STAGED_HOOK = _STAGED_HOOKS / "check_notification.py"
_CANON_AE = _LIVE_HOOKS / "_lib" / "audit_emit.py"
_STAGED_AE = _STAGED_HOOKS / "_lib" / "audit_emit.py"

_HOOK_MARKER = "notification_lifecycle"  # emitted action (present in both)
_AE_MARKER = "def emit_notification_lifecycle"  # T3.2 emitter (pack-only)


def _pick(canonical: Path, staged: Path, marker: str) -> Path:
    """Canonical IF it exists and carries the marker (applied tree), else
    the staged pack copy (live pre-ceremony tree)."""
    try:
        if canonical.is_file() and marker in canonical.read_text(encoding="utf-8"):
            return canonical
    except OSError:
        pass
    if staged.is_file() and marker in staged.read_text(encoding="utf-8"):
        return staged
    raise FileNotFoundError(
        "T3.2 source not found in canonical (%s) or staged (%s); marker=%r"
        % (canonical, staged, marker)
    )


_HOOK_SRC = _pick(_CANON_HOOK, _STAGED_HOOK, _HOOK_MARKER)
_AE_SRC = _pick(_CANON_AE, _STAGED_AE, _AE_MARKER)

if str(_LIVE_HOOKS) not in sys.path:
    sys.path.insert(0, str(_LIVE_HOOKS))  # canonical _lib package

from _lib.testing import TestEnvContext  # noqa: E402
import _lib as _LIB_PKG  # noqa: E402  (package-attribute rebind — see setUp)

_SENTINEL = object()


def _load_module(modname: str, path: Path):
    spec = importlib.util.spec_from_file_location(modname, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[modname] = mod  # register before exec (typing on py3.9)
    spec.loader.exec_module(mod)
    return mod


# Loaded once at import under a unique name (never shadows a canonical hook).
notif_hook = _load_module("staged_check_notification_t32", _HOOK_SRC)


class _stdin:
    """Context manager: feed a string to sys.stdin for hook main()."""

    def __init__(self, data: str) -> None:
        self._data = data
        self._orig = None

    def __enter__(self):
        self._orig = sys.stdin
        sys.stdin = io.StringIO(self._data)
        return self

    def __exit__(self, *exc):
        sys.stdin = self._orig
        return False


class _T32Base(TestEnvContext):
    """Isolated audit dir + the pack audit_emit bound transiently."""

    def setUp(self) -> None:
        super().setUp()
        os.environ.pop("CEO_NOTIFICATION_TELEMETRY", None)
        os.environ.pop("CLAUDE_SESSION_ID", None)
        # Bind the 323-action pack audit_emit ONLY for this test, then
        # restore — AC-B7-safe. BOTH the sys.modules entry AND the _lib
        # package attribute must be rebound (S228 lesson): the hook's lazy
        # `from _lib import audit_emit` resolves the package ATTRIBUTE.
        saved_mod = sys.modules.get("_lib.audit_emit", _SENTINEL)
        saved_attr = getattr(_LIB_PKG, "audit_emit", _SENTINEL)
        self.audit_emit = _load_module("_lib.audit_emit", _AE_SRC)
        _LIB_PKG.audit_emit = self.audit_emit

        def _restore() -> None:
            if saved_mod is _SENTINEL:
                sys.modules.pop("_lib.audit_emit", None)
            else:
                sys.modules["_lib.audit_emit"] = saved_mod
            if saved_attr is _SENTINEL:
                try:
                    delattr(_LIB_PKG, "audit_emit")
                except AttributeError:
                    pass
            else:
                _LIB_PKG.audit_emit = saved_attr
        self.addCleanup(_restore)

    def tearDown(self) -> None:
        # PLAN-119 WS-C audit-isolation gate: re-assert canonical in a
        # top-level teardown (idempotent — _restore already ran via
        # addCleanup) before TestEnvContext tears down.
        importlib.import_module("_lib.audit_emit")
        super().tearDown()

    # -- helpers -----------------------------------------------------------
    def _run(self, payload) -> "tuple[str, int]":
        data = payload if isinstance(payload, str) else json.dumps(payload)
        with redirect_stdout(io.StringIO()) as out:
            with _stdin(data):
                rc = notif_hook.main()
        return out.getvalue(), rc

    def _events(self) -> list:
        events = []
        for line in self.read_audit_log().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except Exception:
                continue
            if ev.get("action") == "notification_lifecycle":
                events.append(ev)
        return events


class TestClosedVocabulary(_T32Base):
    """Pillar 1 — open harness enum -> closed persisted vocabulary."""

    def test_on_enum_types_pass_through(self) -> None:
        for ntype in ("agent_needs_input", "agent_completed",
                      "permission_request"):
            stdout, rc = self._run({
                "hook_event_name": "Notification",
                "notification_type": ntype,
                "message": "m-%s" % ntype,
                "session_id": "s-%s" % ntype,
            })
            self.assertEqual(json.loads(stdout), {})
            self.assertEqual(rc, 0)
        types = sorted(e["notification_type"] for e in self._events())
        self.assertEqual(
            types,
            ["agent_completed", "agent_needs_input", "permission_request"],
        )

    def test_off_enum_coerces_to_other_and_never_echoes(self) -> None:
        raw_type = "brand_new_kind_ZZ_OFFENUM_SENTINEL"
        stdout, rc = self._run({
            "hook_event_name": "Notification",
            "notification_type": raw_type,
            "message": "hello",
            "session_id": "s-off",
        })
        self.assertEqual(json.loads(stdout), {})
        self.assertEqual(rc, 0)
        events = self._events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["notification_type"], "other")
        # The raw off-enum string never persists ANYWHERE (log or sidecar).
        self.assertNotIn(raw_type, self.read_audit_log())
        self.assertNotIn(raw_type, self.read_audit_errors())

    def test_non_string_type_coerces_to_other(self) -> None:
        self._run({
            "hook_event_name": "Notification",
            "notification_type": 42,
            "message": "m",
        })
        events = self._events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["notification_type"], "other")

    def test_case_variant_is_off_enum(self) -> None:
        # Exact byte match only — no case-folding normalization.
        self._run({
            "hook_event_name": "Notification",
            "notification_type": "Agent_Needs_Input",
            "message": "m",
        })
        events = self._events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["notification_type"], "other")


class TestNoValueEcho(_T32Base):
    """Pillar 2 — message/title content NEVER persists; hash + bool only."""

    def test_message_and_title_text_absent_from_log(self) -> None:
        msg = "NOTIF-BODY-SENTINEL quoting sk-fake-secret-0001 output"
        title = "NOTIF-TITLE-SENTINEL"
        self._run({
            "hook_event_name": "Notification",
            "notification_type": "agent_needs_input",
            "message": msg,
            "title": title,
            "session_id": "s-nve",
        })
        events = self._events()
        self.assertEqual(len(events), 1)
        ev = events[0]
        # The whole log — every byte — is free of the content.
        log_body = self.read_audit_log()
        for fragment in (msg, title, "NOTIF-BODY-SENTINEL",
                         "NOTIF-TITLE-SENTINEL", "sk-fake-secret-0001"):
            self.assertNotIn(fragment, log_body)
        self.assertNotIn("message", ev)   # no raw-message key at all
        self.assertNotIn("title", ev)     # no raw-title key at all
        # What DOES persist: presence bool + 12-hex hash prefix.
        self.assertIs(ev["has_title"], True)
        expected_prefix = hashlib.sha256(
            msg.encode("utf-8")
        ).hexdigest()[:12]
        self.assertEqual(ev["message_sha256_prefix"], expected_prefix)
        self.assertEqual(len(ev["message_sha256_prefix"]), 12)

    def test_missing_message_and_title(self) -> None:
        self._run({
            "hook_event_name": "Notification",
            "notification_type": "agent_completed",
        })
        events = self._events()
        self.assertEqual(len(events), 1)
        self.assertIs(events[0]["has_title"], False)
        self.assertEqual(events[0]["message_sha256_prefix"], "")

    def test_empty_title_is_not_a_title(self) -> None:
        self._run({
            "hook_event_name": "Notification",
            "notification_type": "agent_completed",
            "message": "m",
            "title": "",
        })
        events = self._events()
        self.assertEqual(len(events), 1)
        self.assertIs(events[0]["has_title"], False)

    def test_session_id_threaded_from_event(self) -> None:
        self._run({
            "hook_event_name": "Notification",
            "notification_type": "agent_completed",
            "message": "m",
            "session_id": "sess-threaded-1",
        })
        events = self._events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["session_id"], "sess-threaded-1")

    def test_session_id_env_fallback(self) -> None:
        with mock.patch.dict(
            os.environ, {"CLAUDE_SESSION_ID": "sess-from-env"}
        ):
            self._run({
                "hook_event_name": "Notification",
                "notification_type": "agent_completed",
                "message": "m",
            })
        events = self._events()
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["session_id"], "sess-from-env")


class TestKillSwitch(_T32Base):
    """Pillar 3 — CEO_NOTIFICATION_TELEMETRY=0 -> {} exit 0, no emit."""

    def test_kill_switch_suppresses_emit(self) -> None:
        with mock.patch.dict(
            os.environ, {"CEO_NOTIFICATION_TELEMETRY": "0"}
        ):
            stdout, rc = self._run({
                "hook_event_name": "Notification",
                "notification_type": "agent_needs_input",
                "message": "should never be hashed",
            })
        self.assertEqual(json.loads(stdout), {})
        self.assertEqual(rc, 0)
        self.assertEqual(self._events(), [])
        self.assertEqual(self.read_audit_log(), "")

    def test_kill_switch_other_values_do_not_kill(self) -> None:
        with mock.patch.dict(
            os.environ, {"CEO_NOTIFICATION_TELEMETRY": "1"}
        ):
            self._run({
                "hook_event_name": "Notification",
                "notification_type": "agent_completed",
                "message": "m",
            })
        self.assertEqual(len(self._events()), 1)


class TestInfraFailOpen(_T32Base):
    """Pillar 4 — pure observer: {} exit 0 on every infra failure."""

    def test_garbage_stdin_fails_open(self) -> None:
        stdout, rc = self._run("this is {{{ not json")
        self.assertEqual(json.loads(stdout), {})
        self.assertEqual(rc, 0)
        self.assertEqual(self._events(), [])

    def test_non_dict_json_fails_open(self) -> None:
        stdout, rc = self._run("[1, 2, 3]")
        self.assertEqual(json.loads(stdout), {})
        self.assertEqual(rc, 0)
        self.assertEqual(self._events(), [])

    def test_empty_stdin_fails_open_without_vacuous_row(self) -> None:
        stdout, rc = self._run("")
        self.assertEqual(json.loads(stdout), {})
        self.assertEqual(rc, 0)
        # Empty payload = nothing to record (an all-coerced row would only
        # be audit noise) — and never a crash, never a block.
        self.assertEqual(self._events(), [])

    def test_stdout_is_always_bare_allow(self) -> None:
        # The Notification event's only output arm is additionalContext;
        # this observer never uses it — stdout is exactly {}.
        for payload in (
            {"notification_type": "agent_needs_input", "message": "m"},
            {"notification_type": "nope"},
            "garbage",
        ):
            stdout, rc = self._run(payload)
            self.assertEqual(json.loads(stdout), {})
            self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
