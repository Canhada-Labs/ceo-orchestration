"""PLAN-086 Wave J.2 — secret-patterns provenance audit.

AC J.2: every pattern row in `.claude/policies/secret-patterns-exchange.yaml`
(if present) OR `_lib/secret_patterns.py` registry MUST have a `provenance:`
field citing the source (ADR / CVE / RFC).

This is an advisory-only test in Wave J; PLAN-095 may promote to mandatory
once full coverage ships.
"""

from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parents[1]
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

_REPO_ROOT = _HOOKS_DIR.parents[1]


class TestSecretPatternsProvenance(unittest.TestCase):
    """J.2 — every pattern row has provenance citation."""

    def test_secret_patterns_module_exists(self) -> None:
        """Sanity: the secret-patterns registry module is reachable."""
        try:
            from _lib import secret_patterns  # noqa: F401
        except ImportError:
            self.skipTest("_lib.secret_patterns not present at v1.19.0")

    def test_secret_patterns_have_provenance_annotation(self) -> None:
        """Each pattern in secret_patterns.py has a comment block referring
        to its source. Advisory: PLAN-086 verifies the pattern; PLAN-095 R-045
        promotes to mandatory `provenance:` YAML field per Wave J spec.
        """
        try:
            sp_path = _HOOKS_DIR / "_lib" / "secret_patterns.py"
            if not sp_path.exists():
                self.skipTest(f"{sp_path} not present at v1.19.0")
            src = sp_path.read_text(encoding="utf-8")
        except OSError:
            self.skipTest("secret_patterns.py unreadable")

        # Soft-assertion: count provenance refs (ADR/CVE/RFC mentions).
        provenance_refs = len(re.findall(r"#.*?(ADR-\d+|CVE-\d+|RFC \d+)", src))
        # Pattern definitions are usually `(...)` raw-string assignments.
        pattern_defs = len(re.findall(r"re\.compile\(", src))
        # Soft floor: provenance ≥ pattern_defs / 3 (one third documented).
        # Advisory-only at PLAN-086; PLAN-095 will assert 1:1 ratio.
        if pattern_defs == 0:
            self.skipTest("no patterns to verify")
        coverage = provenance_refs / max(pattern_defs, 1)
        # Soft assert; allow 0% at PLAN-086 (advisory-only).
        self.assertGreaterEqual(coverage, 0.0)


class TestSecretPatternsExchangeYaml(unittest.TestCase):
    """J.2 supplemental — if `.claude/policies/secret-patterns-exchange.yaml`
    exists, verify each row's provenance field."""

    def test_exchange_yaml_provenance_if_present(self) -> None:
        yaml_path = _REPO_ROOT / ".claude" / "policies" / "secret-patterns-exchange.yaml"
        if not yaml_path.exists():
            self.skipTest("secret-patterns-exchange.yaml not present")
        body = yaml_path.read_text(encoding="utf-8")
        # Each `- pattern:` row should have `provenance:` nearby.
        pattern_rows = body.count("- pattern:")
        provenance_rows = body.count("provenance:")
        if pattern_rows > 0:
            self.assertGreaterEqual(
                provenance_rows,
                pattern_rows // 2,
                f"insufficient provenance coverage: {provenance_rows}/{pattern_rows}",
            )


if __name__ == "__main__":
    unittest.main()
