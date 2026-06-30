"""PLAN-086 Wave H.3+H.4 — detect-repo-profile branch coverage + audit emit.

H.3a — engine-only branch detected.
H.3b — cmd_show plain text (non-JSON) output.
H.4  — confirm-profile emits repo_profile_confirmed via _emit_profile_confirmed.
"""

from __future__ import annotations

import importlib.util as _ilu
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from typing import List, Tuple
from unittest.mock import patch

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parents[2]
_SCRIPTS_DIR = _REPO_ROOT / ".claude" / "scripts"

_spec = _ilu.spec_from_file_location(
    "detect_repo_profile",
    str(_SCRIPTS_DIR / "detect-repo-profile.py"),
)
assert _spec is not None and _spec.loader is not None
drp = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(drp)


def _run_cli(argv: List[str]) -> Tuple[int, str, str]:
    out = io.StringIO()
    err = io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = drp.main(argv)
    return rc, out.getvalue(), err.getvalue()


class TestEngineOnlyDetection(unittest.TestCase):
    """H.3a — engine-only branch: frontend_votes==0, engine_votes>0."""

    def test_pyproject_fastapi_detects_engine(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "repo"
            target.mkdir()
            (target / "pyproject.toml").write_text(
                "[tool.poetry.dependencies]\n"
                "fastapi = \"^0.100\"\n"
                "uvicorn = \"^0.23\"\n"
                "sqlalchemy = \"^2.0\"\n",
                encoding="utf-8",
            )
            rc, out, err = _run_cli(["detect", "--target", str(target), "--json"])
            self.assertEqual(rc, 0, msg=f"rc={rc} out={out} err={err}")
            payload = json.loads(out.strip())
            self.assertEqual(payload["risk_class"], "engine")


class TestShowCommandPlainText(unittest.TestCase):
    """H.3b — cmd_show non-JSON output branch."""

    def test_show_plain_text(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "repo"
            target.mkdir()
            (target / "package.json").write_text(
                '{"dependencies": {"next": "^14", "react": "^18"}}',
                encoding="utf-8",
            )
            rc_detect, _, _ = _run_cli(["detect", "--target", str(target)])
            self.assertEqual(rc_detect, 0)

            rc, out, err = _run_cli(["show", "--target", str(target)])
            self.assertEqual(rc, 0)
            self.assertIn("risk_class:", out)
            self.assertFalse(out.strip().startswith("{"))


class TestConfirmProfileEmits(unittest.TestCase):
    """H.4 — confirm-profile calls _emit_profile_confirmed."""

    def test_confirm_profile_calls_emit(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "repo"
            target.mkdir()

            captured: List[dict] = []

            def fake_emit(name: str, tgt: Path) -> None:
                captured.append({"name": name, "target": str(tgt)})

            with patch.object(drp, "_emit_profile_confirmed", side_effect=fake_emit):
                rc, out, err = _run_cli(
                    ["confirm-profile", "generic", "--target", str(target)]
                )

            self.assertEqual(rc, 0, msg=f"rc={rc} out={out} err={err}")
            self.assertEqual(len(captured), 1)
            self.assertEqual(captured[0]["name"], "generic")

    def test_emit_helper_is_fail_open(self) -> None:
        """Direct call to _emit_profile_confirmed must not raise."""
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "repo"
            target.mkdir()
            try:
                drp._emit_profile_confirmed("frontend", target)
            except Exception as exc:
                self.fail(f"_emit_profile_confirmed raised: {exc}")


if __name__ == "__main__":
    unittest.main()
