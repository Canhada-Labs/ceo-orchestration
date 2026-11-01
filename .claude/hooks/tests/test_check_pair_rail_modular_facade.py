"""The split pair-rail facade keeps dynamic globals, reload and CLI behavior."""
from __future__ import annotations

import importlib
import importlib.util
import io
import json
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from _lib.testing import TestEnvContext


_HOOKS = Path(__file__).resolve().parents[1]
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))

import check_pair_rail


class TestPairRailModularFacade(TestEnvContext):
    def test_private_detector_patch_changes_consumed_payload(self):
        with patch.object(check_pair_rail, "_detect_write_shaped_patch", return_value="probe"):
            with patch.object(check_pair_rail, "_load_codex_adapter", return_value=None):
                verdict, grammar = check_pair_rail._consume_codex_review("review")
        self.assertEqual((verdict, grammar), ("ADVISORY", "probe"))

    def test_main_uses_patched_matrix_decision(self):
        event = {"tool_name": "Edit", "tool_input": {"file_path": "README.md"}}
        output = io.StringIO()
        with patch("sys.stdin", io.StringIO(json.dumps(event))):
            with patch.object(check_pair_rail, "_decide_with_matrix", return_value={"decision": "allow", "probe": 1}):
                with redirect_stdout(output):
                    self.assertEqual(check_pair_rail.main(), 0)
        self.assertEqual(json.loads(output.getvalue()), {"decision": "allow", "probe": 1})

    def test_alternate_import_and_reload_keep_facade_binding(self):
        path = _HOOKS / "check_pair_rail.py"
        spec = importlib.util.spec_from_file_location("pair_rail_facade_probe", path)
        module = importlib.util.module_from_spec(spec)
        self.assertIsNotNone(spec.loader)
        spec.loader.exec_module(module)
        with patch.object(module, "_detect_write_shaped_patch", return_value="alternate"):
            with patch.object(module, "_load_codex_adapter", return_value=None):
                self.assertEqual(module._consume_codex_review("review"), ("ADVISORY", "alternate"))
        check_pair_rail._CURRENT_REVIEW_ID = "probe"
        importlib.reload(check_pair_rail)
        self.assertEqual(check_pair_rail._CURRENT_REVIEW_ID, "")

    def test_script_main_accepts_empty_event(self):
        result = subprocess.run(
            [sys.executable, str(_HOOKS / "check_pair_rail.py")],
            input="",
            text=True,
            capture_output=True,
            timeout=15,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {})


if __name__ == "__main__":
    unittest.main()
