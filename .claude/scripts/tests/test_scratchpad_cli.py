"""Unit tests for `scripts/scratchpad.py` (PLAN-011 Phase 7).

Covers set/get/list/delete round-trip, clear safety interlock, JSON
output, CEO_SOTA_DISABLE short-circuit, --plan override, and the
64 KiB cap delegation to state_store.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path


_SCRIPTS_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _SCRIPTS_DIR.parent.parent
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

_spec = importlib.util.spec_from_file_location(
    "scratchpad_cli", _SCRIPTS_DIR / "scratchpad.py"
)
scratchpad = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
assert _spec.loader is not None
_spec.loader.exec_module(scratchpad)  # type: ignore[union-attr]

from _lib import state_store  # noqa: E402
from _lib.state_store import DEFAULT_VALUE_MAX_BYTES  # noqa: E402


def _append_plan_transition(
    audit_path: Path,
    *,
    plan_id: str,
    session_id: str,
) -> None:
    event = {
        "action": "plan_transition",
        "plan_id": plan_id,
        "from_status": "reviewed",
        "to_status": "executing",
        "editor_tool": "Edit",
        "file_path": f".claude/plans/{plan_id}.md",
        "transition_legal": True,
        "session_id": session_id,
        "project": "",
        "event_schema": "v2",
        "ts": "2026-04-14T00:00:00Z",
        "tokens_in": None,
        "tokens_out": None,
        "tokens_total": None,
    }
    audit_path.parent.mkdir(parents=True, exist_ok=True)
    with audit_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")


class ScratchpadCLITest(unittest.TestCase):
    def setUp(self) -> None:
        # Snapshot + scrub env
        self._env = {}
        for k in list(os.environ.keys()):
            if k.startswith("CEO_") or k.startswith("CLAUDE_") or k == "HOME":
                self._env[k] = os.environ[k]

        self.tmp = Path(tempfile.mkdtemp(prefix="ceo-scratchpad-test-"))
        self.home = self.tmp / "home"
        self.state_root = self.home / ".claude" / "state"
        self.audit_dir = self.home / ".claude" / "projects" / "test"
        self.audit_dir.mkdir(parents=True, exist_ok=True)
        self.audit_log = self.audit_dir / "audit-log.jsonl"

        os.environ["HOME"] = str(self.home)
        os.environ["CEO_STATE_ROOT"] = str(self.state_root)
        os.environ["CEO_AUDIT_LOG_DIR"] = str(self.audit_dir)
        os.environ["CEO_AUDIT_LOG_PATH"] = str(self.audit_log)
        os.environ["CEO_AUDIT_LOG_ERR"] = str(self.audit_dir / "audit-log.errors")
        os.environ["CEO_AUDIT_LOG_LOCK"] = str(self.audit_dir / "audit-log.lock")
        os.environ.pop("CEO_SOTA_DISABLE", None)

    def tearDown(self) -> None:
        # Scrub + restore env
        for k in list(os.environ.keys()):
            if k.startswith("CEO_") or k.startswith("CLAUDE_") or k == "HOME":
                if k not in self._env:
                    del os.environ[k]
        for k, v in self._env.items():
            os.environ[k] = v
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self, argv):
        """Run main(argv); return (exit_code, stdout_str)."""
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = scratchpad.main(argv)
        return rc, buf.getvalue()


# --- round-trip ---------------------------------------------------------


class TestRoundTrip(ScratchpadCLITest):
    def test_set_get_round_trip_explicit_plan(self) -> None:
        rc, out = self._run(["set", "phase1-done", "true", "--plan", "PLAN-011"])
        self.assertEqual(rc, scratchpad.EXIT_OK, out)
        rc, out = self._run(["get", "phase1-done", "--plan", "PLAN-011"])
        self.assertEqual(rc, scratchpad.EXIT_OK)
        self.assertIn("true", out)

    def test_set_then_list(self) -> None:
        self._run(["set", "k1", "v1", "--plan", "PLAN-011"])
        self._run(["set", "k2", "v2", "--plan", "PLAN-011"])
        rc, out = self._run(["list", "--plan", "PLAN-011"])
        self.assertEqual(rc, scratchpad.EXIT_OK)
        self.assertIn("k1", out)
        self.assertIn("k2", out)

    def test_delete_existing_key_ok(self) -> None:
        self._run(["set", "k", "v", "--plan", "PLAN-011"])
        rc, out = self._run(["delete", "k", "--plan", "PLAN-011"])
        self.assertEqual(rc, scratchpad.EXIT_OK)
        # get after delete -> not found
        rc, out = self._run(["get", "k", "--plan", "PLAN-011"])
        self.assertEqual(rc, scratchpad.EXIT_OK)
        self.assertIn("not found", out)

    def test_delete_missing_key_returns_no_op_exit(self) -> None:
        rc, out = self._run(["delete", "ghost", "--plan", "PLAN-011"])
        self.assertEqual(rc, scratchpad.EXIT_NO_OP)
        self.assertIn("no-op", out.lower())

    def test_get_missing_key(self) -> None:
        rc, out = self._run(["get", "ghost", "--plan", "PLAN-011"])
        self.assertEqual(rc, scratchpad.EXIT_OK)
        self.assertIn("not found", out)


# --- clear safety -------------------------------------------------------


class TestClear(ScratchpadCLITest):
    def test_clear_without_confirm_refuses(self) -> None:
        self._run(["set", "k", "v", "--plan", "PLAN-011"])
        rc, out = self._run(["clear", "--plan", "PLAN-011"])
        self.assertEqual(rc, scratchpad.EXIT_USAGE)
        self.assertIn("--confirm", out)
        # Data still present
        rc, out = self._run(["list", "--plan", "PLAN-011"])
        self.assertIn("k", out)

    def test_clear_with_confirm_ok(self) -> None:
        self._run(["set", "k1", "v1", "--plan", "PLAN-011"])
        self._run(["set", "k2", "v2", "--plan", "PLAN-011"])
        rc, out = self._run(["clear", "--plan", "PLAN-011", "--confirm"])
        self.assertEqual(rc, scratchpad.EXIT_OK)
        self.assertIn("2", out)  # keys_cleared
        rc, out = self._run(["list", "--plan", "PLAN-011"])
        self.assertIn("empty", out.lower())


# --- JSON mode ----------------------------------------------------------


class TestJsonMode(ScratchpadCLITest):
    def test_json_get_payload_shape(self) -> None:
        self._run(["set", "k", "hello", "--plan", "PLAN-011"])
        rc, out = self._run(["get", "k", "--plan", "PLAN-011", "--json"])
        self.assertEqual(rc, scratchpad.EXIT_OK)
        data = json.loads(out.strip().splitlines()[-1])
        self.assertEqual(data["kind"], "get")
        self.assertTrue(data["found"])
        self.assertEqual(data["plan_id"], "PLAN-011")
        self.assertEqual(data["value"], "hello")

    def test_json_list_payload_shape(self) -> None:
        self._run(["set", "a", "1", "--plan", "PLAN-011"])
        self._run(["set", "b", "2", "--plan", "PLAN-011"])
        rc, out = self._run(["list", "--plan", "PLAN-011", "--json"])
        self.assertEqual(rc, scratchpad.EXIT_OK)
        data = json.loads(out.strip().splitlines()[-1])
        self.assertEqual(data["kind"], "list")
        self.assertEqual(sorted(data["keys"]), ["a", "b"])
        self.assertEqual(data["count"], 2)

    def test_json_set_payload_shape(self) -> None:
        rc, out = self._run(
            ["set", "k", "v", "--plan", "PLAN-011", "--ttl", "60", "--json"]
        )
        self.assertEqual(rc, scratchpad.EXIT_OK)
        data = json.loads(out.strip().splitlines()[-1])
        self.assertEqual(data["kind"], "set")
        self.assertEqual(data["plan_id"], "PLAN-011")
        self.assertEqual(data["ttl_seconds"], 60)


# --- kill switch --------------------------------------------------------


class TestKillSwitch(ScratchpadCLITest):
    def test_sota_disable_short_circuits_set(self) -> None:
        os.environ["CEO_SOTA_DISABLE"] = "1"
        rc, out = self._run(["set", "k", "v", "--plan", "PLAN-011"])
        self.assertEqual(rc, scratchpad.EXIT_OK)
        self.assertIn("disabled", out.lower())
        # sqlite file must NOT exist
        sqlite_path = self.state_root / "scratchpad" / "PLAN-011.sqlite"
        self.assertFalse(
            sqlite_path.exists(),
            "CEO_SOTA_DISABLE=1 must not write to sqlite",
        )

    def test_sota_disable_short_circuits_get(self) -> None:
        # Pre-seed a value (real write), then flip kill switch
        self._run(["set", "k", "v", "--plan", "PLAN-011"])
        os.environ["CEO_SOTA_DISABLE"] = "1"
        rc, out = self._run(["get", "k", "--plan", "PLAN-011"])
        self.assertEqual(rc, scratchpad.EXIT_OK)
        self.assertIn("disabled", out.lower())

    def test_sota_disable_json_output(self) -> None:
        os.environ["CEO_SOTA_DISABLE"] = "1"
        rc, out = self._run(["list", "--plan", "PLAN-011", "--json"])
        self.assertEqual(rc, scratchpad.EXIT_OK)
        data = json.loads(out.strip().splitlines()[-1])
        self.assertEqual(data["kind"], "disabled")


# --- plan derivation / overrides ---------------------------------------


class TestPlanDerivation(ScratchpadCLITest):
    def test_set_without_plan_derives_from_audit_log(self) -> None:
        os.environ["CLAUDE_SESSION_ID"] = "sess-alpha"
        _append_plan_transition(
            self.audit_log, plan_id="PLAN-042", session_id="sess-alpha"
        )
        rc, out = self._run(["set", "k", "v"])
        self.assertEqual(rc, scratchpad.EXIT_OK, out)
        # Value went into PLAN-042 directory
        sqlite_path = self.state_root / "scratchpad" / "PLAN-042.sqlite"
        self.assertTrue(sqlite_path.exists())

    def test_derivation_failure_exits_no_op(self) -> None:
        # No session, no audit-log transitions
        rc, out = self._run(["set", "k", "v"])
        self.assertEqual(rc, scratchpad.EXIT_NO_OP)
        self.assertIn("error", out.lower())

    def test_explicit_plan_wins_over_derivation(self) -> None:
        os.environ["CLAUDE_SESSION_ID"] = "sess-alpha"
        _append_plan_transition(
            self.audit_log, plan_id="PLAN-042", session_id="sess-alpha"
        )
        rc, _ = self._run(["set", "k", "v", "--plan", "PLAN-099"])
        self.assertEqual(rc, scratchpad.EXIT_OK)
        # Wrote to PLAN-099, NOT PLAN-042
        self.assertTrue(
            (self.state_root / "scratchpad" / "PLAN-099.sqlite").exists()
        )
        self.assertFalse(
            (self.state_root / "scratchpad" / "PLAN-042.sqlite").exists()
        )


# --- cap delegation -----------------------------------------------------


class TestValueCap(ScratchpadCLITest):
    def test_state_store_too_large_maps_to_exit_4(self) -> None:
        """CLI translates ``StateStoreValueTooLarge`` -> EXIT_TOO_LARGE.

        We monkey-patch :func:`scratchpad.open_store` to return a fake
        store whose ``set()`` raises the too-large error. This isolates
        the CLI's exit-code mapping from the redact-DoS-guard
        interaction that clamps input at 64 KiB (testing the pure cap
        wiring rather than end-to-end redactor math).
        """

        class FakeStore:
            def __init__(self) -> None:
                self.store_name = "scratchpad"
                self.plan_id = "PLAN-011"

            def __enter__(self):
                return self

            def __exit__(self, *a) -> None:
                return None

            def set(self, key, value, ttl_seconds=None):  # noqa: ARG002
                from _lib.state_store import StateStoreValueTooLarge

                raise StateStoreValueTooLarge(
                    "value is 99999 bytes, cap is 65536"
                )

        original = scratchpad.open_store
        scratchpad.open_store = lambda *a, **k: FakeStore()
        try:
            rc, out = self._run(["set", "k", "v", "--plan", "PLAN-011"])
        finally:
            scratchpad.open_store = original

        self.assertEqual(rc, scratchpad.EXIT_TOO_LARGE)
        self.assertIn("cap", out.lower())


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
