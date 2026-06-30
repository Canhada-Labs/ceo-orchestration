"""Unit tests for handlers/list_pitfalls.py — universal + domain catalog."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

# Bootstrap sys.path.
_TESTS_DIR = Path(__file__).resolve().parent
_SERVER_DIR = _TESTS_DIR.parent
_CLAUDE_DIR = _SERVER_DIR.parent.parent
_HOOKS_DIR = _CLAUDE_DIR / "hooks"
for _p in (_HOOKS_DIR, _SERVER_DIR, _SERVER_DIR / "handlers"):
    _sp = str(_p)
    if _sp not in sys.path:
        sys.path.insert(0, _sp)

from _lib.testing import TestEnvContext  # noqa: E402

from handlers import list_pitfalls  # type: ignore[import-not-found]  # noqa: E402


_UNIVERSAL_FIXTURE = """\
# Comments allowed
pitfalls:
  - id: GEN-001
    rule: "no race conditions"
    whenToUse: "any concurrent code"
    agents: [PerformanceEngineer]
  - id: GEN-002
    rule: "no SQL injection"
    whenToUse: "any DB query"
    agents: [SecurityEngineer]
"""

_DOMAIN_FIXTURE = """\
pitfalls:
  - id: FIN-001
    rule: "settlement times"
    whenToUse: "any payment flow"
    agents: [BillingEngineer]
"""


class TestListPitfalls(TestEnvContext):

    def _seed_universal(self):
        path = self.project_dir / ".claude" / "pitfalls-catalog.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_UNIVERSAL_FIXTURE, encoding="utf-8")

    def _seed_domain(self, domain: str = "fintech"):
        path = (
            self.project_dir
            / ".claude"
            / "skills"
            / "domains"
            / domain
            / "pitfalls.yaml"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_DOMAIN_FIXTURE, encoding="utf-8")

    def test_universal_only_when_no_domain_param(self):
        self._seed_universal()
        result = list_pitfalls.handle(
            params={}, context={"project_dir": self.project_dir}
        )
        ids = sorted(p["id"] for p in result["pitfalls"])
        self.assertEqual(ids, ["GEN-001", "GEN-002"])
        self.assertEqual(result["total"], 2)
        # All tagged scope=universal.
        for p in result["pitfalls"]:
            self.assertEqual(p["scope"], "universal")

    def test_unknown_domain_returns_universal_no_error(self):
        self._seed_universal()
        result = list_pitfalls.handle(
            params={"domain": "no-such-domain"},
            context={"project_dir": self.project_dir},
        )
        # Universal still returned; no error.
        self.assertEqual(len(result["pitfalls"]), 2)
        self.assertNotIn("warning", result)

    def test_domain_pitfalls_appended(self):
        self._seed_universal()
        self._seed_domain("fintech")
        result = list_pitfalls.handle(
            params={"domain": "fintech"},
            context={"project_dir": self.project_dir},
        )
        ids = sorted(p["id"] for p in result["pitfalls"])
        self.assertEqual(ids, ["FIN-001", "GEN-001", "GEN-002"])
        # FIN-001 must be tagged scope=domain and domain=fintech.
        fin = next(p for p in result["pitfalls"] if p["id"] == "FIN-001")
        self.assertEqual(fin["scope"], "domain")
        self.assertEqual(fin["domain"], "fintech")


if __name__ == "__main__":
    unittest.main()
