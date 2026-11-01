"""Component loading must retain the hook's infrastructure fail-open."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
import tempfile

from _subprocess_helpers import run_in_process_group
from _lib.testing import TestEnvContext


class TestComponentLoading(TestEnvContext):
    def test_missing_component_allows_spawn(self):
        hooks = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as temp:
            isolated = Path(temp) / "hooks"
            isolated.mkdir()
            shutil.copy2(hooks / "check_agent_spawn.py", isolated)
            shutil.copytree(
                hooks / "_lib", isolated / "_lib",
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "model_routing.py"),
            )
            result = run_in_process_group(
                [sys.executable, str(isolated / "check_agent_spawn.py")],
                input="{}", text=True, capture_output=True,
                env=self.subprocess_env(), check=False, timeout=30,
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout), {})
        self.assertIn("model_routing", result.stderr)
        self.assertNotIn("Fatal Python error", result.stderr)
