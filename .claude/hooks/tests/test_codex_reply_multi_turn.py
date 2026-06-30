"""PLAN-086 Wave C R-016 → PLAN-142 — codex-reply multi-turn resume RETIRED.

PLAN-142 (codex-cli 0.139 migration): the resume flag was REMOVED on 0.139
(session resume is now an ``exec resume`` subcommand). PLAN-142 does not
reimplement multi-turn resume (no production consumer ever exercised it), so
the CLI-shape helper rejects a ``resume_thread_id`` loudly and ``invoke_codex``
no longer carries the kwarg. These tests pin that retirement so a future
reintroduction is a conscious, tested choice.
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parents[1]
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.adapters.codex import make_invoke_command  # noqa: E402


class TestResumeRetired(unittest.TestCase):
    """PLAN-142 — resume_thread_id is rejected loud (no resume flag on 0.139)."""

    def test_resume_thread_id_raises_not_implemented(self) -> None:
        with self.assertRaises(NotImplementedError):
            make_invoke_command(
                "continuation prompt",
                output_last_message_path="/tmp/o.json",
                resume_thread_id="019e1c3f-46fd",
            )

    def test_resume_none_builds_normally(self) -> None:
        argv = make_invoke_command(
            "first prompt",
            output_last_message_path="/tmp/o.json",
            resume_thread_id=None,
        )
        self.assertNotIn("--resume", argv)
        self.assertIn("exec", argv)

    def test_resume_empty_string_builds_normally(self) -> None:
        argv = make_invoke_command(
            "first prompt",
            output_last_message_path="/tmp/o.json",
            resume_thread_id="",
        )
        self.assertNotIn("--resume", argv)


class TestInvokeCodexSignature(unittest.TestCase):
    """PLAN-142 — invoke_codex() no longer carries resume_thread_id / strict_json."""

    def test_signature_drops_retired_kwargs(self) -> None:
        import importlib.util as _ilu
        _spec = _ilu.spec_from_file_location(
            "codex_invoke",
            str(Path(__file__).resolve().parents[3] / ".claude" / "scripts" / "codex_invoke.py"),
        )
        assert _spec is not None and _spec.loader is not None
        ci = _ilu.module_from_spec(_spec)
        _spec.loader.exec_module(ci)
        import inspect
        sig = inspect.signature(ci.invoke_codex)
        self.assertNotIn("resume_thread_id", sig.parameters)
        self.assertNotIn("strict_json", sig.parameters)


if __name__ == "__main__":
    unittest.main()
