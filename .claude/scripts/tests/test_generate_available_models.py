"""test_generate_available_models.py — generator for the ADR-149 model mirror.

PLAN-135 W1 unit s1. LIVE test (state-agnostic): runs green on the
pre-ceremony tree (live ADR-149 has no Amendment 1 -> VETO-floor fallback
path) AND post-ceremony (Amendment 1 applied -> working-set path), because
every deterministic branch is exercised against tempfile fixtures, and the
single live-ADR case only asserts invariants true in both states.

Post-apply mirror assertions (settings == generator output) live in the
STAGED .claude/plans/PLAN-135/staged/w1/files/.claude/hooks/tests/
test_available_models_mirror.py — not here (COUPLING RULE).

Stdlib-only. Python >= 3.9.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parents[1]
_REPO_ROOT = _SCRIPTS_DIR.parents[1]
sys.path.insert(0, str(_REPO_ROOT / ".claude" / "hooks"))

from _lib.testing import TestEnvContext  # noqa: E402

GENERATOR = _SCRIPTS_DIR / "generate-available-models.py"
LIVE_ADR = _REPO_ROOT / ".claude" / "adr" / "ADR-149-model-id-allowlist.md"

VETO_FLOOR = ["claude-opus-4-8", "claude-fable-5"]
WORKING_SET = [
    "claude-opus-4-8",
    "claude-fable-5",
    "claude-sonnet-4-6",
    "claude-haiku-4-5",
]

AMENDED_ADR = """# ADR-149 fixture (amended)

```python
VETO_FLOOR_ALLOWED: frozenset = frozenset({
    "claude-opus-4-8",   # floor
    "claude-fable-5",    # floor
})
```

## Amendment 1

```python
AVAILABLE_MODELS_WORKING_SET: tuple = (
    "claude-opus-4-8",    # floor
    "claude-fable-5",     # floor
    "claude-sonnet-4-6",  # tier
    "claude-haiku-4-5",   # tier
)
```
"""

UNAMENDED_ADR = """# ADR-149 fixture (base only)

```python
VETO_FLOOR_ALLOWED: frozenset = frozenset({
    "claude-opus-4-8",   # floor
    "claude-fable-5",    # floor
})
```
"""


def _run(*args: str) -> "subprocess.CompletedProcess":
    return subprocess.run(
        [sys.executable, str(GENERATOR)] + list(args),
        capture_output=True,
        text=True,
        timeout=30,
    )


class _Base(TestEnvContext):
    def _write(self, name: str, content: str) -> Path:
        path = Path(self.project_dir) / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        return path

    def _write_settings(self, payload: dict, local: "dict | None" = None) -> Path:
        path = self._write("settings.json", json.dumps(payload))
        if local is not None:
            self._write("settings.local.json", json.dumps(local))
        return path


class TestGenerateMode(_Base):
    def test_live_adr_parses_state_agnostic(self) -> None:
        """Green pre- AND post-ceremony: ids are a superset of the VETO floor
        and a subset of the working-set union, whichever block is live."""
        proc = _run("--adr", str(LIVE_ADR))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        ids = json.loads(proc.stdout)["availableModels"]
        self.assertTrue(ids)
        for member in VETO_FLOOR:
            self.assertIn(member, ids)
        for member in ids:
            self.assertIn(member, WORKING_SET)

    def test_amended_adr_emits_working_set_in_order(self) -> None:
        adr = self._write("adr.md", AMENDED_ADR)
        proc = _run("--adr", str(adr))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["availableModels"], WORKING_SET)
        self.assertIn("AVAILABLE_MODELS_WORKING_SET", proc.stderr)
        self.assertNotIn("falling back", proc.stderr)

    def test_unamended_adr_falls_back_to_veto_floor_with_note(self) -> None:
        adr = self._write("adr.md", UNAMENDED_ADR)
        proc = _run("--adr", str(adr))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["availableModels"], VETO_FLOOR)
        self.assertIn("falling back", proc.stderr)

    def test_adr_without_any_block_is_infra_error(self) -> None:
        adr = self._write("adr.md", "# no blocks here\n")
        proc = _run("--adr", str(adr))
        self.assertEqual(proc.returncode, 2)

    def test_missing_adr_is_infra_error(self) -> None:
        proc = _run("--adr", str(Path(self.project_dir) / "absent.md"))
        self.assertEqual(proc.returncode, 2)


class TestCheckMode(_Base):
    def setUp(self) -> None:
        super().setUp()
        self.adr = self._write("adr.md", AMENDED_ADR)

    def _check(self, settings_path: Path) -> "subprocess.CompletedProcess":
        return _run("--adr", str(self.adr), "--settings", str(settings_path), "--check")

    def test_check_graceful_when_keys_absent(self) -> None:
        settings = self._write_settings({"hooks": {}})
        proc = self._check(settings)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("pre-ceremony", proc.stdout)

    def test_check_match_exits_zero(self) -> None:
        settings = self._write_settings(
            {"availableModels": WORKING_SET, "fallbackModel": ["claude-opus-4-8"]}
        )
        proc = self._check(settings)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("MATCH", proc.stdout)

    def test_check_flags_available_models_drift(self) -> None:
        settings = self._write_settings({"availableModels": VETO_FLOOR})
        proc = self._check(settings)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("drift", proc.stderr)

    def test_check_flags_fallback_escaping_working_set(self) -> None:
        settings = self._write_settings(
            {"availableModels": WORKING_SET, "fallbackModel": ["claude-opus-4-5"]}
        )
        proc = self._check(settings)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("escapes", proc.stderr)

    def test_check_flags_fallback_chain_over_cap(self) -> None:
        settings = self._write_settings(
            {
                "availableModels": WORKING_SET,
                "fallbackModel": [
                    "claude-opus-4-8",
                    "claude-fable-5",
                    "claude-sonnet-4-6",
                    "claude-haiku-4-5",
                ],
            }
        )
        proc = self._check(settings)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("chain length", proc.stderr)

    def test_check_local_layer_addition_is_visible_drift(self) -> None:
        # availableModels MERGES across layers: a local-layer addition is
        # exactly the tamper/drift --check must surface (ADR-149 A1.4).
        settings = self._write_settings(
            {"availableModels": WORKING_SET},
            local={"availableModels": ["claude-opus-4-5"]},
        )
        proc = self._check(settings)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("drift", proc.stderr)

    def test_check_local_fallback_chain_wins_wholesale(self) -> None:
        # fallbackModel does NOT merge: the local layer replaces the chain.
        settings = self._write_settings(
            {"availableModels": WORKING_SET, "fallbackModel": ["claude-opus-4-8"]},
            local={"fallbackModel": ["claude-opus-4-5"]},
        )
        proc = self._check(settings)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("escapes", proc.stderr)


if __name__ == "__main__":
    unittest.main()
