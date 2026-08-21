"""PLAN-163 T3.1/T3.2 — audit_emit extension suite for the two new
CC 2.1.220 lifecycle actions (``directory_added_recorded`` +
``notification_lifecycle``).

Dedicated functional coverage for the pack's ``audit_emit`` additions
(the EmitterCoverageGate xfail ledger stays as-is; this is the dedicated
suite in the PLAN-116 / PLAN-124 precedent shape):

  * REGISTRATION — both actions in ``_KNOWN_ACTIONS`` (321 -> 323), and
    NEITHER in ``_EMIT_GENERIC_PASSTHROUGH`` (deny-by-default preserved).
  * TYPED EMITTERS — closed-enum pass-through + coercion (off-enum
    ``source``/``notification_type`` -> other, NEVER echoed), hash-prefix
    shape gates (exact 16-hex / 12-hex or ""; off-shape incl. OVERSIZE is
    DROPPED to "", never truncated — the r6 F2 alias lesson), strict-bool
    ``has_title``.
  * DISPATCH-GATE (direct ``emit_generic`` caller) — the same VALUE
    re-coercion runs in the dedicated scrub branch, and any extra field
    (``directory`` raw path, ``message``/``title`` text, arbitrary ghost
    keys) is STRIPPED before the event reaches the signed chain.
  * NO-VALUE-ECHO — raw path / message / title / off-enum strings appear
    NOWHERE in the log after any of the above.

COUPLING NOTE: the 323-action ``audit_emit`` lives ONLY in the PLAN-163
staged pack until the pack ceremony. Canonical-first resolution keeps
this file green in BOTH trees (PLAN-135 W2 staged-test precedent).
AC-B7 + PLAN-119 WS-C: the pack module is bound in ``sys.modules`` AND
the ``_lib`` package attribute per-test with addCleanup restore + a
tearDown canonical re-import.

Stdlib-only, Python >= 3.9, ``from __future__ import annotations``.
"""

from __future__ import annotations

import hashlib
import importlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path

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
_CANON_AE = _LIVE_HOOKS / "_lib" / "audit_emit.py"
_STAGED_AE = (
    _repo_root / ".claude" / "plans" / "PLAN-163" / "staged" / "main-pack"
    / ".claude" / "hooks" / "_lib" / "audit_emit.py"
)
_AE_MARKER = "def emit_notification_lifecycle"


def _pick(canonical: Path, staged: Path, marker: str) -> Path:
    try:
        if canonical.is_file() and marker in canonical.read_text(encoding="utf-8"):
            return canonical
    except OSError:
        pass
    if staged.is_file() and marker in staged.read_text(encoding="utf-8"):
        return staged
    raise FileNotFoundError(
        "PLAN-163 audit_emit not found in canonical (%s) or staged (%s)"
        % (canonical, staged)
    )


_AE_SRC = _pick(_CANON_AE, _STAGED_AE, _AE_MARKER)

if str(_LIVE_HOOKS) not in sys.path:
    sys.path.insert(0, str(_LIVE_HOOKS))  # canonical _lib package

from _lib.testing import TestEnvContext  # noqa: E402
import _lib as _LIB_PKG  # noqa: E402

_SENTINEL = object()


def _load_module(modname: str, path: Path):
    spec = importlib.util.spec_from_file_location(modname, str(path))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[modname] = mod
    spec.loader.exec_module(mod)
    return mod


class _Plan163Base(TestEnvContext):
    """Isolated audit dir + the pack audit_emit bound transiently."""

    def setUp(self) -> None:
        super().setUp()
        saved_mod = sys.modules.get("_lib.audit_emit", _SENTINEL)
        saved_attr = getattr(_LIB_PKG, "audit_emit", _SENTINEL)
        self.ae = _load_module("_lib.audit_emit", _AE_SRC)
        _LIB_PKG.audit_emit = self.ae

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
        # top-level teardown (idempotent) before TestEnvContext tears down.
        importlib.import_module("_lib.audit_emit")
        super().tearDown()

    # -- helpers -----------------------------------------------------------
    def _events(self, action: str) -> list:
        events = []
        for line in self.read_audit_log().splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except Exception:
                continue
            if ev.get("action") == action:
                events.append(ev)
        return events

    def _one(self, action: str) -> dict:
        events = self._events(action)
        self.assertEqual(
            len(events), 1,
            "expected exactly 1 %s event, got %d" % (action, len(events)),
        )
        return events[0]

    def _assert_baseline(self, ev: dict, action: str) -> None:
        self.assertEqual(ev["action"], action)
        self.assertEqual(ev["event_schema"], "v2")
        self.assertIn("ts", ev)
        for k in ("tokens_in", "tokens_out", "tokens_total"):
            self.assertIn(k, ev)
        self.assertIn("session_id", ev)
        self.assertIn("project", ev)


class TestRegistration(_Plan163Base):
    """Both actions registered; deny-by-default topology preserved."""

    def test_actions_registered_and_count(self) -> None:
        self.assertIn("directory_added_recorded", self.ae._KNOWN_ACTIONS)
        self.assertIn("notification_lifecycle", self.ae._KNOWN_ACTIONS)
        # 321 (PLAN-161) + 2 PLAN-163 T3.1/T3.2 = 323;
        # + 1 PLAN-165 P2 (night_mode_toggled) = 324.
        # + 1 PLAN-179 W0 US2 (context_pressure_observed) = 325.
        # + 1 PLAN-174 W1 registration completion, SENT-S318 pack
        #   (ceremony_lint_unlock_used) = 326; +1 PLAN-182 W1 SENT-S319
        #   (salt_rotation_registered) = 327.
        self.assertEqual(len(self.ae._KNOWN_ACTIONS), 327)

    def test_never_passthrough(self) -> None:
        for action in ("directory_added_recorded", "notification_lifecycle"):
            self.assertNotIn(
                action, self.ae._EMIT_GENERIC_PASSTHROUGH,
                "%s must route through its dedicated scrub branch, "
                "NEVER _EMIT_GENERIC_PASSTHROUGH" % action,
            )

    def test_allowlists_are_closed_and_exact(self) -> None:
        env = self.ae._CODEX_AUDIT_ENVELOPE
        self.assertEqual(
            self.ae._DIRECTORY_ADDED_RECORDED_ALLOWLIST - env,
            frozenset({"source", "directory_hash_prefix"}),
        )
        self.assertEqual(
            self.ae._NOTIFICATION_LIFECYCLE_ALLOWLIST - env,
            frozenset({
                "notification_type", "has_title", "message_sha256_prefix",
            }),
        )


class TestDirectoryAddedTypedEmitter(_Plan163Base):
    """emit_directory_added_recorded — enum + shape gates."""

    def test_basic_emit(self) -> None:
        # 12-hex — the exact token check_directory_added.py:_hash_prefix()
        # computes (producer/consumer contract).
        prefix = hashlib.sha256(b"/tmp/ws-a").hexdigest()[:12]
        self.ae.emit_directory_added_recorded(
            source="slash_command",
            directory_hash_prefix=prefix,
            session_id="s-dar-1",
            project="/t",
        )
        ev = self._one("directory_added_recorded")
        self._assert_baseline(ev, "directory_added_recorded")
        self.assertEqual(ev["source"], "slash_command")
        self.assertEqual(ev["directory_hash_prefix"], prefix)
        self.assertEqual(len(ev["directory_hash_prefix"]), 12)
        self.assertEqual(ev["session_id"], "s-dar-1")

    def test_all_enum_sources_accepted(self) -> None:
        for src in ("slash_command", "register_repo_root",
                    "session_start_snapshot", "other"):
            self.ae.emit_directory_added_recorded(
                source=src, session_id="s-%s" % src,
            )
        sources = sorted(
            e["source"] for e in self._events("directory_added_recorded")
        )
        self.assertEqual(
            sources,
            ["other", "register_repo_root", "session_start_snapshot",
             "slash_command"],
        )

    def test_off_enum_source_coerces_never_echoes(self) -> None:
        self.ae.emit_directory_added_recorded(
            source="launch_flag_RAW_SENTINEL", session_id="s",
        )
        ev = self._one("directory_added_recorded")
        self.assertEqual(ev["source"], "other")
        self.assertNotIn("launch_flag_RAW_SENTINEL", self.read_audit_log())

    def test_prefix_shape_gate_drops_never_truncates(self) -> None:
        cases = [
            "a" * 11,            # short
            "a" * 13,            # oversize (would alias if truncated)
            "a" * 16,            # legacy 16-hex length is ALSO off-shape
            "A" * 12,            # uppercase
            "g" * 12,            # non-hex
            "/tmp/raw-path",     # raw-path smuggle attempt
        ]
        for bad in cases:
            self.ae.emit_directory_added_recorded(
                source="slash_command", directory_hash_prefix=bad,
                session_id="s-shape",
            )
        events = self._events("directory_added_recorded")
        self.assertEqual(len(events), len(cases))
        for ev in events:
            self.assertEqual(ev["directory_hash_prefix"], "")
        self.assertNotIn("/tmp/raw-path", self.read_audit_log())

    def test_empty_prefix_allowed(self) -> None:
        self.ae.emit_directory_added_recorded(source="register_repo_root")
        ev = self._one("directory_added_recorded")
        self.assertEqual(ev["directory_hash_prefix"], "")


class TestNotificationTypedEmitter(_Plan163Base):
    """emit_notification_lifecycle — vocabulary + shape + bool gates."""

    def test_basic_emit(self) -> None:
        prefix = hashlib.sha256(b"a message").hexdigest()[:12]
        self.ae.emit_notification_lifecycle(
            notification_type="agent_needs_input",
            has_title=True,
            message_sha256_prefix=prefix,
            session_id="s-nl-1",
            project="/t",
        )
        ev = self._one("notification_lifecycle")
        self._assert_baseline(ev, "notification_lifecycle")
        self.assertEqual(ev["notification_type"], "agent_needs_input")
        self.assertIs(ev["has_title"], True)
        self.assertEqual(ev["message_sha256_prefix"], prefix)

    def test_off_enum_type_coerces_never_echoes(self) -> None:
        self.ae.emit_notification_lifecycle(
            notification_type="free text that could be a SECRET-ECHO",
            session_id="s",
        )
        ev = self._one("notification_lifecycle")
        self.assertEqual(ev["notification_type"], "other")
        self.assertNotIn("SECRET-ECHO", self.read_audit_log())

    def test_prefix_shape_gate_drops_never_truncates(self) -> None:
        cases = [
            "b" * 11,                 # short
            "b" * 13,                 # oversize (alias-if-truncated class)
            "B" * 12,                 # uppercase
            "the message itself",     # content smuggle attempt
        ]
        for bad in cases:
            self.ae.emit_notification_lifecycle(
                notification_type="agent_completed",
                message_sha256_prefix=bad,
                session_id="s-shape",
            )
        events = self._events("notification_lifecycle")
        self.assertEqual(len(events), len(cases))
        for ev in events:
            self.assertEqual(ev["message_sha256_prefix"], "")
        self.assertNotIn("the message itself", self.read_audit_log())

    def test_has_title_is_strict_bool(self) -> None:
        self.ae.emit_notification_lifecycle(
            notification_type="agent_completed",
            has_title="a-truthy-string",  # type: ignore[arg-type]
        )
        ev = self._one("notification_lifecycle")
        self.assertIs(ev["has_title"], True)
        self.assertNotIn("a-truthy-string", self.read_audit_log())


class TestDispatchGateDirectCaller(_Plan163Base):
    """Direct emit_generic callers hit the SAME coercion + strip boundary."""

    def test_directory_ghost_fields_stripped(self) -> None:
        self.ae.emit_generic(
            "directory_added_recorded",
            source="slash_command",
            directory_hash_prefix="0123456789ab",
            directory="/Users/someone/private-client-repo",  # raw path
            cwd="/Users/someone",                            # ghost
            transcript_path="/tmp/tx.jsonl",                 # ghost
            session_id="s-gg-1",
        )
        ev = self._one("directory_added_recorded")
        self.assertEqual(ev["source"], "slash_command")
        self.assertEqual(ev["directory_hash_prefix"], "0123456789ab")
        for ghost in ("directory", "cwd", "transcript_path"):
            self.assertNotIn(ghost, ev)
        self.assertNotIn("private-client-repo", self.read_audit_log())

    def test_directory_value_recoercion_on_generic_path(self) -> None:
        self.ae.emit_generic(
            "directory_added_recorded",
            source="not_an_enum_member",
            directory_hash_prefix="Z" * 12,
            session_id="s-gg-2",
        )
        ev = self._one("directory_added_recorded")
        self.assertEqual(ev["source"], "other")
        self.assertEqual(ev["directory_hash_prefix"], "")
        self.assertNotIn("not_an_enum_member", self.read_audit_log())

    def test_notification_ghost_fields_stripped(self) -> None:
        self.ae.emit_generic(
            "notification_lifecycle",
            notification_type="agent_needs_input",
            has_title=True,
            message_sha256_prefix="0a1b2c3d4e5f",
            message="RAW-MESSAGE-MUST-NOT-PERSIST",  # ghost content
            title="RAW-TITLE-MUST-NOT-PERSIST",      # ghost content
            session_id="s-gg-3",
        )
        ev = self._one("notification_lifecycle")
        self.assertEqual(ev["notification_type"], "agent_needs_input")
        self.assertEqual(ev["message_sha256_prefix"], "0a1b2c3d4e5f")
        for ghost in ("message", "title"):
            self.assertNotIn(ghost, ev)
        log_body = self.read_audit_log()
        self.assertNotIn("RAW-MESSAGE-MUST-NOT-PERSIST", log_body)
        self.assertNotIn("RAW-TITLE-MUST-NOT-PERSIST", log_body)

    def test_notification_value_recoercion_on_generic_path(self) -> None:
        self.ae.emit_generic(
            "notification_lifecycle",
            notification_type="verbatim wire string",
            has_title="yes",
            message_sha256_prefix="not-hex!",
            session_id="s-gg-4",
        )
        ev = self._one("notification_lifecycle")
        self.assertEqual(ev["notification_type"], "other")
        self.assertIs(ev["has_title"], True)
        self.assertEqual(ev["message_sha256_prefix"], "")
        self.assertNotIn("verbatim wire string", self.read_audit_log())

    def test_event_keys_subset_of_allowlist(self) -> None:
        """The persisted row carries ONLY allowlisted keys (deny-by-default)."""
        self.ae.emit_generic(
            "notification_lifecycle",
            notification_type="agent_completed",
            has_title=False,
            message_sha256_prefix="",
            ghost_key_one="x",
            ghost_key_two=2,
            session_id="s-gg-5",
        )
        ev = self._one("notification_lifecycle")
        self.assertTrue(
            set(ev.keys()) <= set(self.ae._NOTIFICATION_LIFECYCLE_ALLOWLIST),
            "row leaked non-allowlisted key(s): %s"
            % sorted(set(ev.keys())
                     - set(self.ae._NOTIFICATION_LIFECYCLE_ALLOWLIST)),
        )


class TestUnhashableValueCoercionH4(_Plan163Base):
    """H4 (PLAN-163 fix-pass) — a direct emit_generic / wrapper caller that
    passes an UNHASHABLE value (dict/list) for an enum-membership field must
    NOT raise: ``x in frozenset`` raises ``TypeError: unhashable type`` for a
    dict/list ``x``, which would break emit_generic's documented never-raises
    contract (fail-OPEN by exception — the row silently vanishes). The
    isinstance-str guard makes a non-str value off-enum -> coerced to the
    closed default, and the raw value never reaches the signed chain.
    """

    def test_generic_directory_source_unhashable_no_raise(self) -> None:
        # Pre-fix this call raised TypeError inside emit_generic.
        self.ae.emit_generic(
            "directory_added_recorded",
            source={"raw": "/Users/someone/DICT-SMUGGLE"},  # unhashable dict
            session_id="s-h4-1",
        )
        ev = self._one("directory_added_recorded")
        self.assertEqual(ev["source"], "other")
        self.assertNotIn("DICT-SMUGGLE", self.read_audit_log())

    def test_generic_notification_type_unhashable_no_raise(self) -> None:
        self.ae.emit_generic(
            "notification_lifecycle",
            notification_type=["LIST-SMUGGLE"],  # unhashable list
            session_id="s-h4-2",
        )
        ev = self._one("notification_lifecycle")
        self.assertEqual(ev["notification_type"], "other")
        self.assertNotIn("LIST-SMUGGLE", self.read_audit_log())

    def test_generic_directory_prefix_unhashable_no_raise(self) -> None:
        # directory_hash_prefix already isinstance-guarded; a dict must not
        # raise and must coerce to "" (regression lock on the shape gate).
        self.ae.emit_generic(
            "directory_added_recorded",
            source="slash_command",
            directory_hash_prefix={"nested": "PREFIX-DICT"},
            session_id="s-h4-3",
        )
        ev = self._one("directory_added_recorded")
        self.assertEqual(ev["directory_hash_prefix"], "")
        self.assertNotIn("PREFIX-DICT", self.read_audit_log())

    def test_generic_notification_prefix_unhashable_no_raise(self) -> None:
        self.ae.emit_generic(
            "notification_lifecycle",
            notification_type="agent_completed",
            message_sha256_prefix=["PREFIX-LIST"],
            session_id="s-h4-4",
        )
        ev = self._one("notification_lifecycle")
        self.assertEqual(ev["message_sha256_prefix"], "")
        self.assertNotIn("PREFIX-LIST", self.read_audit_log())

    def test_wrapper_directory_source_unhashable_no_raise(self) -> None:
        self.ae.emit_directory_added_recorded(
            source={"raw": "WRAP-DICT-SMUGGLE"},  # type: ignore[arg-type]
            session_id="s-h4-5",
        )
        ev = self._one("directory_added_recorded")
        self.assertEqual(ev["source"], "other")
        self.assertNotIn("WRAP-DICT-SMUGGLE", self.read_audit_log())

    def test_wrapper_notification_type_unhashable_no_raise(self) -> None:
        self.ae.emit_notification_lifecycle(
            notification_type=["WRAP-LIST-SMUGGLE"],  # type: ignore[arg-type]
            session_id="s-h4-6",
        )
        ev = self._one("notification_lifecycle")
        self.assertEqual(ev["notification_type"], "other")
        self.assertNotIn("WRAP-LIST-SMUGGLE", self.read_audit_log())


if __name__ == "__main__":
    unittest.main()
