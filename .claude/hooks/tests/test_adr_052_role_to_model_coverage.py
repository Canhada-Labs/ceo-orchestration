"""PLAN-086 Wave B — _ADR_052_ROLE_TO_MODEL VETO-floor coverage gate (AC B.2).

Shell-grep verification (AC5 §1) + importlib loader (AC5 §2).
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Dict


_REQUIRED = (
    "incident-commander",
    "identity-trust-architect",
    "threat-detection-engineer",
    "llm-finops-architect",
)
_EXPECTED_FLOOR = "claude-opus-4-8"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _audit_log_path() -> Path:
    return _repo_root() / ".claude" / "hooks" / "audit_log.py"


def _load_audit_log_module():
    path = _audit_log_path()
    spec = importlib.util.spec_from_file_location("ceo_audit_log_under_test", str(path))
    if spec is None or spec.loader is None:
        raise ImportError(f"could not build spec for {path}")
    module = importlib.util.module_from_spec(spec)
    hooks_dir = path.parent
    if str(hooks_dir) not in sys.path:
        sys.path.insert(0, str(hooks_dir))
    spec.loader.exec_module(module)
    return module


class TestShellGrep(unittest.TestCase):
    """AC5 §1 — shell grep verifies each archetype appears."""

    def test_each_archetype_present(self) -> None:
        path = _audit_log_path()
        self.assertTrue(path.exists())
        for archetype in _REQUIRED:
            result = subprocess.run(
                ["grep", "-q", f'"{archetype}"', str(path)],
                check=False,
            )
            self.assertEqual(
                result.returncode, 0,
                f"missing {archetype!r} (grep -q failed)",
            )

    def test_provenance_comment_present(self) -> None:
        result = subprocess.run(
            ["grep", "-q", "PLAN-074 Wave 1c provenance", str(_audit_log_path())],
            check=False,
        )
        self.assertEqual(result.returncode, 0)

    def test_appendix_doc_referenced(self) -> None:
        result = subprocess.run(
            [
                "grep", "-q",
                "docs/PLAN-086-adr-052-role-extension.md",
                str(_audit_log_path()),
            ],
            check=False,
        )
        self.assertEqual(result.returncode, 0)


class TestImportlibLoad(unittest.TestCase):
    """AC5 §2 — importlib loads dict, checks keys + values."""

    @classmethod
    def setUpClass(cls) -> None:
        cls._mod = _load_audit_log_module()

    def test_dict_attribute(self) -> None:
        self.assertTrue(hasattr(self._mod, "_ADR_052_ROLE_TO_MODEL"))
        self.assertIsInstance(self._mod._ADR_052_ROLE_TO_MODEL, dict)

    def test_each_archetype_key_present(self) -> None:
        table: Dict[str, str] = self._mod._ADR_052_ROLE_TO_MODEL
        for archetype in _REQUIRED:
            self.assertIn(archetype, table)

    def test_each_archetype_opus_floor(self) -> None:
        table: Dict[str, str] = self._mod._ADR_052_ROLE_TO_MODEL
        for archetype in _REQUIRED:
            self.assertEqual(table[archetype], _EXPECTED_FLOOR)

    def test_canonical_5_preserved(self) -> None:
        table: Dict[str, str] = self._mod._ADR_052_ROLE_TO_MODEL
        for archetype in (
            "code-reviewer", "security-engineer", "qa-architect",
            "performance-engineer", "devops",
        ):
            self.assertIn(archetype, table)


if __name__ == "__main__":
    unittest.main()
