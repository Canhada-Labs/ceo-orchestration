"""Bonus tests for `.claude/scripts/check_atlas_fpr.py` (PLAN-085 G.1a).

Three small cases exercising the FPR script's exit-code contract:

    1. corpus-missing: graceful exit 1 (no Python traceback).
    2. threshold-met (FPR <= threshold): exit 0.
    3. threshold-exceeded: exit 1.

The script is heuristic-mode in G.1a (registry lookup keyed on
`action` for labeled negatives). G.1b convergence is documented
inline in `check_atlas_fpr.py`'s module docstring.
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from typing import List


_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _REPO_ROOT / ".claude" / "scripts" / "check_atlas_fpr.py"


def _run(argv: List[str]) -> subprocess.CompletedProcess:
    """Run check_atlas_fpr.py with given args; capture out/err."""
    return subprocess.run(
        [sys.executable, str(_SCRIPT), *argv],
        capture_output=True,
        text=True,
        check=False,
    )


class TestCheckAtlasFpr(unittest.TestCase):

    def test_corpus_missing_graceful_exit_2(self) -> None:
        """Missing corpus dir -> graceful exit 2 (usage error), helpful stderr.

        Matches the script's convention (2 = usage/infra error, 1 = FPR
        threshold exceeded) and test_check_atlas_fpr_extensions.py.
        """
        with tempfile.TemporaryDirectory() as td:
            nonexistent = Path(td) / "does-not-exist"
            proc = _run(["--corpus", str(nonexistent), "--threshold", "0.15"])
            self.assertEqual(
                proc.returncode,
                2,
                f"expected exit 2 on missing corpus; got {proc.returncode}\n"
                f"stdout: {proc.stdout!r}\nstderr: {proc.stderr!r}",
            )
            self.assertIn("corpus directory not found", proc.stderr)
            # Defense: no Python traceback should leak.
            self.assertNotIn("Traceback", proc.stderr)

    def test_threshold_met_exit_0(self) -> None:
        """All-benign corpus with no positive actions -> FPR 0.0 PASS."""
        with tempfile.TemporaryDirectory() as td:
            corpus = Path(td)
            ndjson = corpus / "benign.ndjson"
            # 10 labeled-benign events; NONE use a registry action,
            # so per-mapping FP = 0, TN = 10, FPR = 0.0.
            events = [
                {"action": "agent_spawn", "attack": False},
                {"action": "plan_transition", "attack": False},
                {"action": "debate_event", "attack": False},
                {"action": "lesson_write", "attack": False},
                {"action": "benchmark_run", "attack": False},
                {"action": "session_start", "attack": False},
                {"action": "session_end", "attack": False},
                {"action": "policy_evaluated", "attack": False},
                {"action": "rag_query_issued", "attack": False},
                {"action": "tournament_run_started", "attack": False},
            ]
            ndjson.write_text(
                "\n".join(json.dumps(e) for e in events) + "\n",
                encoding="utf-8",
            )
            proc = _run(["--corpus", str(corpus), "--threshold", "0.15"])
            self.assertEqual(
                proc.returncode,
                0,
                f"expected exit 0; got {proc.returncode}\n"
                f"stdout: {proc.stdout!r}\nstderr: {proc.stderr!r}",
            )
            self.assertIn("PASS", proc.stdout)

    def test_threshold_exceeded_exit_1(self) -> None:
        """Negative event mis-fires a registry action -> FPR > 0."""
        with tempfile.TemporaryDirectory() as td:
            corpus = Path(td)
            ndjson = corpus / "mixed.ndjson"
            # 1 labeled-benign event using `prompt_injection_detected`
            # action (the heuristic will mis-assign AML.T0051 to a
            # negative -> FP=1, TN=0 for that mapping; FPR=1.0).
            events = [
                {
                    "action": "prompt_injection_detected",
                    "attack": False,
                    "note": "false-positive: benign quoted phrase",
                },
            ]
            ndjson.write_text(
                "\n".join(json.dumps(e) for e in events) + "\n",
                encoding="utf-8",
            )
            proc = _run(["--corpus", str(corpus), "--threshold", "0.15"])
            self.assertEqual(
                proc.returncode,
                1,
                f"expected exit 1 on FPR breach; got {proc.returncode}\n"
                f"stdout: {proc.stdout!r}\nstderr: {proc.stderr!r}",
            )
            self.assertIn("FAIL", proc.stdout)


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
