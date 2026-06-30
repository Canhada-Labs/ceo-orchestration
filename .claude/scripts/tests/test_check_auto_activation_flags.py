"""Tests for check-auto-activation-flags.py — PLAN-088 W5.2 / AC17 / M-4."""

from __future__ import annotations

import importlib.util
import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

_THIS = Path(__file__).resolve()
_SCRIPT = _THIS.parent.parent / "check-auto-activation-flags.py"


def _load_verifier_module():
    spec = importlib.util.spec_from_file_location(
        "check_auto_activation_flags", str(_SCRIPT)
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


verifier = _load_verifier_module()


def _build_full_env_file() -> str:
    """Build a synthetic .env.example with all 14 AUTO env-vars set correctly."""
    lines = [
        "# PLAN-088 god-mode AUTO-USABLE env template",
        "CEO_CACHE_DISCIPLINE=1",
        "CEO_SKIP_WIZARD=0",
        "CEO_ESTIMATE_VIBES=0",
        "CEO_PHASE_REFINE_DISABLE=0",
        "CEO_SKIP_TIER_POLICY_CHECK=0",
        "CEO_MULTI_MODEL_MANUAL=0",
        "CEO_MCP_ROUTING_DISABLE=0",
        "CEO_PAIR_RAIL_DISABLE=0",
        "CEO_PAIR_RAIL_PHASE=SHADOW",
        "CEO_BENCHMARK_BATCH_MODE=1",
        "CEO_STREAMING_DISABLE=0",
        "CEO_THINKING_AUTO_DISABLE=0",
        "CEO_AUTO_SPECIALIZE=1",
        "CEO_SKIP_COOKBOOK_HINT=0",
    ]
    return "\n".join(lines) + "\n"


def _build_env_with_violation() -> str:
    """Flip CEO_AUTO_SPECIALIZE=1 to 0 unexpectedly (would change default behavior)."""
    text = _build_full_env_file()
    return text.replace(
        "CEO_AUTO_SPECIALIZE=1",
        "CEO_AUTO_SPECIALIZE=2",  # violation: not 1 nor "" (empty)
    )


class _Fixture:
    def __init__(self) -> None:
        self.tmp = tempfile.mkdtemp(prefix="aaf-")
        self.env_path = Path(self.tmp) / ".env.example"
        self.last_stdout = ""
        self.last_stderr = ""

    def write(self, text: str) -> None:
        self.env_path.write_text(text, encoding="utf-8")

    def run(self) -> int:
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = verifier.verify(self.env_path)
        self.last_stdout = out.getvalue()
        self.last_stderr = err.getvalue()
        return rc

    def cleanup(self) -> None:
        try:
            if self.env_path.exists():
                self.env_path.unlink()
            os.rmdir(self.tmp)
        except OSError:
            pass


class TestCheckAutoActivationFlags(unittest.TestCase):
    def setUp(self) -> None:
        self.fx = _Fixture()

    def tearDown(self) -> None:
        self.fx.cleanup()

    def test_valid_env_passes(self) -> None:
        self.fx.write(_build_full_env_file())
        rc = self.fx.run()
        self.assertEqual(rc, 0,
                         "expected PASS; stderr=%r stdout=%r"
                         % (self.fx.last_stderr, self.fx.last_stdout))
        self.assertIn("PASS", self.fx.last_stdout)

    def test_missing_var_fails(self) -> None:
        # Drop CEO_CACHE_DISCIPLINE entirely
        text = _build_full_env_file().replace("CEO_CACHE_DISCIPLINE=1\n", "")
        self.fx.write(text)
        rc = self.fx.run()
        self.assertEqual(rc, 1)
        self.assertIn("CEO_CACHE_DISCIPLINE", self.fx.last_stderr)
        self.assertIn("missing", self.fx.last_stderr)

    def test_value_mismatch_fails(self) -> None:
        self.fx.write(_build_env_with_violation())
        rc = self.fx.run()
        self.assertEqual(rc, 1)
        self.assertIn("CEO_AUTO_SPECIALIZE", self.fx.last_stderr)

    def test_telemetry_invariant_comment_accepts_mismatch(self) -> None:
        # Mark CEO_AUTO_SPECIALIZE with telemetry-invariant comment;
        # then a non-canonical value should be accepted.
        text = _build_full_env_file().replace(
            "CEO_AUTO_SPECIALIZE=1",
            "CEO_AUTO_SPECIALIZE=2  # telemetry-invariant",
        )
        self.fx.write(text)
        rc = self.fx.run()
        self.assertEqual(rc, 0,
                         "telemetry-invariant comment must accept any value; "
                         "stderr=%r stdout=%r"
                         % (self.fx.last_stderr, self.fx.last_stdout))

    def test_missing_env_file_skips(self) -> None:
        # Run against non-existent path: should SKIP (exit 0) per AC17
        # informational-only semantics.
        rc = verifier.verify(Path("/nonexistent/.env.example"))
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
