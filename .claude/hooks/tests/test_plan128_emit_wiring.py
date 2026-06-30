from __future__ import annotations

import json
import os
import unittest
from pathlib import Path

from _lib.testing import TestEnvContext  # noqa: E402
from _lib import audit_emit  # noqa: E402


class TestPlan128EmitWiring(TestEnvContext):
    """PLAN-128 §7 — accelerator catch-emit closed-enum + Sec MF-3 scrub/coerce/clamp.

    TestEnvContext sets CEO_AUDIT_SYNC_MODE=1 (+ sandbox HOME/audit paths), so emits are
    readable synchronously (the framework default is async-spool). [[feedback-test-set-ceo-audit-sync-mode]]
    """

    def _last(self):
        log = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        rows = [json.loads(line) for line in log.read_text().splitlines() if line.strip()]
        return rows[-1] if rows else {}

    def test_actions_registered(self):
        self.assertIn("verify_after_edit_finding", audit_emit._KNOWN_ACTIONS)
        self.assertIn("adequacy_gate_flag", audit_emit._KNOWN_ACTIONS)

    def test_verify_finding_valid(self):
        audit_emit.emit_generic("verify_after_edit_finding",
                                checker="py_compile", lang="python", finding_count=3)
        e = self._last()
        self.assertEqual(e["action"], "verify_after_edit_finding")
        self.assertEqual(e["checker"], "py_compile")
        self.assertEqual(e["lang"], "python")
        self.assertEqual(e["finding_count"], 3)

    def test_verify_invalid_enum_coerced_never_echoes_raw(self):
        audit_emit.emit_generic("verify_after_edit_finding",
                                checker="/etc/passwd", lang="rust", finding_count=1)
        e = self._last()
        self.assertEqual(e["checker"], "other")
        self.assertEqual(e["lang"], "other")
        self.assertNotIn("/etc/passwd", json.dumps(e))

    def test_verify_count_clamped(self):
        audit_emit.emit_generic("verify_after_edit_finding",
                                checker="ruff", lang="python", finding_count=9999)
        self.assertEqual(self._last()["finding_count"], 99)
        audit_emit.emit_generic("verify_after_edit_finding",
                                checker="ruff", lang="python", finding_count=-5)
        self.assertEqual(self._last()["finding_count"], 0)

    def test_verify_forbidden_fields_dropped(self):
        audit_emit.emit_generic("verify_after_edit_finding",
                                checker="ruff", lang="python", finding_count=1,
                                file_path="/Users/x/secret.py", source="print(API_KEY)")
        e = self._last()
        self.assertNotIn("file_path", e)
        self.assertNotIn("source", e)
        self.assertNotIn("secret.py", json.dumps(e))

    def test_adequacy_flag_valid_and_coerced(self):
        audit_emit.emit_generic("adequacy_gate_flag",
                                flag_reason="weak_assertion", lang="python", flag_count=2)
        e = self._last()
        self.assertEqual(e["flag_reason"], "weak_assertion")
        self.assertEqual(e["flag_count"], 2)
        audit_emit.emit_generic("adequacy_gate_flag",
                                flag_reason="totally-made-up", lang="python", flag_count=1)
        self.assertEqual(self._last()["flag_reason"], "other")


if __name__ == "__main__":
    unittest.main()
