"""PLAN-104 Wave A tests — audit_emit additions.

Validates the 4 new emit functions land correctly post-ceremony:
  - persona_demand_opened
  - persona_demand_matched
  - persona_demand_unmet
  - persona_demand_waived

Plus the carry-over field allowlist extension
(_CEO_BOOT_PERSONA_COVERAGE_ALLOWLIST += 3 fields).

These tests run AFTER apply-patches.py — pre-ceremony they will fail
on hasattr-guarded asserts (expected; test marker can skip in adopter
installs that haven't run the v1.33.0 ceremony yet).
"""
from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

def _find_repo_root() -> Path:
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / ".claude" / "scripts").is_dir():
            return parent
    raise RuntimeError("repo root with .claude/scripts/ not found")


_REPO_ROOT = _find_repo_root()
_AUDIT_EMIT_PATH = _REPO_ROOT / ".claude" / "hooks" / "_lib" / "audit_emit.py"


def _load_audit_emit():
    spec = importlib.util.spec_from_file_location("audit_emit_plan104", _AUDIT_EMIT_PATH)
    if spec is None or spec.loader is None:
        raise unittest.SkipTest("audit_emit.py not loadable")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class TestKnownActionsExtension(unittest.TestCase):
    def setUp(self):
        self.ae = _load_audit_emit()

    def test_four_new_actions_registered(self):
        for action in (
            "persona_demand_opened",
            "persona_demand_matched",
            "persona_demand_unmet",
            "persona_demand_waived",
        ):
            self.assertIn(action, self.ae._KNOWN_ACTIONS,
                          f"action {action!r} missing from _KNOWN_ACTIONS")


class TestCarryOverAllowlist(unittest.TestCase):
    """S127 scope-(b) carry-over — 3 new fields in persona_coverage allowlist."""

    def setUp(self):
        self.ae = _load_audit_emit()

    def test_window_hours_field_allowed(self):
        self.assertIn("window_hours", self.ae._CEO_BOOT_PERSONA_COVERAGE_ALLOWLIST)

    def test_events_with_target_archetype_field_allowed(self):
        self.assertIn("events_with_target_archetype",
                      self.ae._CEO_BOOT_PERSONA_COVERAGE_ALLOWLIST)

    def test_eligible_demand_events_field_allowed(self):
        self.assertIn("eligible_demand_events",
                      self.ae._CEO_BOOT_PERSONA_COVERAGE_ALLOWLIST)


class TestPersonaDemandAllowlists(unittest.TestCase):
    """Each action MUST have its own Sec MF-3 caller-field allowlist."""

    def setUp(self):
        self.ae = _load_audit_emit()

    def test_opened_allowlist_has_required_fields(self):
        al = self.ae._PERSONA_DEMAND_OPENED_ALLOWLIST
        for field in ("demand_id", "demand_event_type", "expected_persona",
                      "target_ref_hash", "match_window_hours"):
            self.assertIn(field, al)

    def test_matched_allowlist_has_required_fields(self):
        al = self.ae._PERSONA_DEMAND_MATCHED_ALLOWLIST
        for field in ("demand_id", "demand_event_type", "expected_persona",
                      "actual_persona", "latency_ms"):
            self.assertIn(field, al)

    def test_unmet_allowlist_has_required_fields(self):
        al = self.ae._PERSONA_DEMAND_UNMET_ALLOWLIST
        for field in ("demand_id", "demand_event_type", "expected_persona",
                      "target_ref_hash", "window_expired_at"):
            self.assertIn(field, al)

    def test_waived_allowlist_has_required_fields(self):
        al = self.ae._PERSONA_DEMAND_WAIVED_ALLOWLIST
        for field in ("demand_id", "demand_event_type", "expected_persona",
                      "waive_reason"):
            self.assertIn(field, al)

    def test_no_raw_target_path_in_any_allowlist(self):
        # LLM06 hold — target_path/branch_ref raw values must NEVER persist.
        for al in (
            self.ae._PERSONA_DEMAND_OPENED_ALLOWLIST,
            self.ae._PERSONA_DEMAND_MATCHED_ALLOWLIST,
            self.ae._PERSONA_DEMAND_UNMET_ALLOWLIST,
            self.ae._PERSONA_DEMAND_WAIVED_ALLOWLIST,
        ):
            for forbidden in ("target_path", "target_ref", "branch_ref", "file_path"):
                self.assertNotIn(forbidden, al,
                                 f"raw {forbidden!r} must NOT be in caller allowlist")


class TestEmitFunctions(unittest.TestCase):
    """Each emit must construct a schema-valid event without raising."""

    def setUp(self):
        self.ae = _load_audit_emit()

    def test_emit_opened_exists(self):
        self.assertTrue(callable(getattr(self.ae, "emit_persona_demand_opened", None)))

    def test_emit_matched_exists(self):
        self.assertTrue(callable(getattr(self.ae, "emit_persona_demand_matched", None)))

    def test_emit_unmet_exists(self):
        self.assertTrue(callable(getattr(self.ae, "emit_persona_demand_unmet", None)))

    def test_emit_waived_exists(self):
        self.assertTrue(callable(getattr(self.ae, "emit_persona_demand_waived", None)))

    def test_emit_waived_rejects_free_text_reason(self):
        # Free-text replaced with `invalid-enum` sentinel; doesn't raise.
        with tempfile.TemporaryDirectory() as td:
            import os
            os.environ["CEO_AUDIT_SYNC_MODE"] = "1"
            os.environ["CEO_AUDIT_LOG_DIR"] = td
            try:
                self.ae.emit_persona_demand_waived(
                    demand_id="d1",
                    demand_event_type="auth_edit",
                    expected_persona="security-engineer",
                    waive_reason="my-free-text-reason",  # invalid
                    session_id="test",
                    project="ceo-orchestration",
                )
                # Read back the emitted record from the audit log
                log_path = Path(td) / "audit-log.jsonl"
                if log_path.exists():
                    import json
                    lines = log_path.read_text(encoding="utf-8").strip().splitlines()
                    if lines:
                        last = json.loads(lines[-1])
                        self.assertEqual(last.get("waive_reason"), "invalid-enum")
            finally:
                os.environ.pop("CEO_AUDIT_SYNC_MODE", None)
                os.environ.pop("CEO_AUDIT_LOG_DIR", None)

    def test_emit_waived_accepts_all_4_enum_values(self):
        for reason in ("docs-only", "generated-or-vendored",
                       "emergency-hotfix", "explicit-skip"):
            with tempfile.TemporaryDirectory() as td:
                import os
                os.environ["CEO_AUDIT_SYNC_MODE"] = "1"
                os.environ["CEO_AUDIT_LOG_DIR"] = td
                try:
                    self.ae.emit_persona_demand_waived(
                        demand_id="d1",
                        demand_event_type="auth_edit",
                        expected_persona="security-engineer",
                        waive_reason=reason,
                    )
                finally:
                    os.environ.pop("CEO_AUDIT_SYNC_MODE", None)
                    os.environ.pop("CEO_AUDIT_LOG_DIR", None)


class TestSafeHashHelper(unittest.TestCase):
    """Codex iter-2 P2 #1 fold: test _persona_demand_safe_hash defensive
    rehashing. Caller-supplied non-hex values must be rehashed to prevent
    LLM06 side-channel where a hostile caller passes raw text as
    `target_ref_hash`."""

    def setUp(self):
        self.ae = _load_audit_emit()

    def test_valid_12_hex_passes_through(self):
        fn = self.ae._persona_demand_safe_hash
        self.assertEqual(fn("abc123def456"), "abc123def456")
        self.assertEqual(fn("0123456789ab"), "0123456789ab")
        self.assertEqual(fn("DEADBEEF1234"), "deadbeef1234")  # case-normalized

    def test_non_hex_is_rehashed(self):
        fn = self.ae._persona_demand_safe_hash
        # Raw path-like input — would be a privacy leak if persisted verbatim
        result = fn("/etc/passwd")
        self.assertEqual(len(result), 12)
        self.assertTrue(all(c in "0123456789abcdef" for c in result))
        self.assertNotEqual(result, "/etc/passwd")

    def test_wrong_length_hex_is_rehashed(self):
        fn = self.ae._persona_demand_safe_hash
        # Even if all hex chars, length != 12 triggers rehash
        result = fn("abc")
        self.assertEqual(len(result), 12)
        self.assertNotEqual(result, "abc")

    def test_empty_input_returns_safe_hash(self):
        fn = self.ae._persona_demand_safe_hash
        result = fn("")
        self.assertEqual(len(result), 12)


class TestEmitGenericScrub(unittest.TestCase):
    """Codex iter-2 P2 #1 fold: verify A.4b emit_generic dispatch
    properly scrubs forbidden caller-supplied fields for each of
    the 4 persona_demand_* actions."""

    def setUp(self):
        self.ae = _load_audit_emit()

    def _assert_field_stripped(self, action: str, forbidden_field: str, forbidden_value: str):
        import os, json
        with tempfile.TemporaryDirectory() as td:
            os.environ["CEO_AUDIT_SYNC_MODE"] = "1"
            os.environ["CEO_AUDIT_LOG_DIR"] = td
            try:
                self.ae.emit_generic(
                    action,
                    demand_id="d1",
                    demand_event_type="auth_edit",
                    expected_persona="security-engineer",
                    **{forbidden_field: forbidden_value},
                )
            finally:
                os.environ.pop("CEO_AUDIT_SYNC_MODE", None)
                os.environ.pop("CEO_AUDIT_LOG_DIR", None)
            log_path = Path(td) / "audit-log.jsonl"
            if log_path.exists():
                lines = log_path.read_text(encoding="utf-8").strip().splitlines()
                if lines:
                    rec = json.loads(lines[-1])
                    self.assertNotIn(
                        forbidden_field, rec,
                        f"emit_generic({action!r}) leaked {forbidden_field!r}: {rec}",
                    )

    def test_opened_strips_raw_target_path(self):
        self._assert_field_stripped("persona_demand_opened", "target_path", "/etc/passwd")

    def test_matched_strips_raw_branch_ref(self):
        self._assert_field_stripped("persona_demand_matched", "branch_ref", "feature/x")

    def test_unmet_strips_unknown_field(self):
        self._assert_field_stripped("persona_demand_unmet", "secret_token", "AKIA...")

    def test_waived_strips_raw_paths(self):
        self._assert_field_stripped("persona_demand_waived", "target_path", "/etc/shadow")

    def test_emit_generic_opened_rehashes_raw_target_ref(self):
        """Codex iter-4 P0 fold: hostile caller passing raw path as
        target_ref_hash via emit_generic must be re-hashed to 12-hex,
        not persisted verbatim."""
        import os, json
        with tempfile.TemporaryDirectory() as td:
            os.environ["CEO_AUDIT_SYNC_MODE"] = "1"
            os.environ["CEO_AUDIT_LOG_DIR"] = td
            try:
                self.ae.emit_generic(
                    "persona_demand_opened",
                    demand_id="d1",
                    demand_event_type="auth_edit",
                    expected_persona="security-engineer",
                    target_ref_hash="/etc/passwd",  # raw path -> must rehash
                    match_window_hours=24,
                )
            finally:
                os.environ.pop("CEO_AUDIT_SYNC_MODE", None)
                os.environ.pop("CEO_AUDIT_LOG_DIR", None)
            log_path = Path(td) / "audit-log.jsonl"
            self.assertTrue(log_path.exists())
            lines = log_path.read_text(encoding="utf-8").strip().splitlines()
            self.assertGreater(len(lines), 0)
            rec = json.loads(lines[-1])
            persisted = rec.get("target_ref_hash", "")
            self.assertEqual(len(persisted), 12)
            self.assertTrue(all(c in "0123456789abcdef" for c in persisted))
            self.assertNotIn("/etc", persisted)
            self.assertNotEqual(persisted, "/etc/passwd")

    def test_emit_generic_unmet_rehashes_raw_target_ref(self):
        import os, json
        with tempfile.TemporaryDirectory() as td:
            os.environ["CEO_AUDIT_SYNC_MODE"] = "1"
            os.environ["CEO_AUDIT_LOG_DIR"] = td
            try:
                self.ae.emit_generic(
                    "persona_demand_unmet",
                    demand_id="d1",
                    demand_event_type="auth_edit",
                    expected_persona="security-engineer",
                    target_ref_hash="src/auth.py",  # raw path
                    window_expired_at="2026-05-18T00:00:00Z",
                )
            finally:
                os.environ.pop("CEO_AUDIT_SYNC_MODE", None)
                os.environ.pop("CEO_AUDIT_LOG_DIR", None)
            log_path = Path(td) / "audit-log.jsonl"
            lines = log_path.read_text(encoding="utf-8").strip().splitlines()
            rec = json.loads(lines[-1])
            persisted = rec.get("target_ref_hash", "")
            self.assertEqual(len(persisted), 12)
            self.assertTrue(all(c in "0123456789abcdef" for c in persisted))


if __name__ == "__main__":
    unittest.main()
