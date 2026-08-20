"""Mirror test for check-time-unit.py (PLAN-180 W0 — ADR-081 Step 3).

Pins the AC-W0.1 regression pair against the REAL corpus (the anchors are
actual lines, not imagined vocabulary — closed sets must be derived):

- POSITIVE: the historical PLAN-153:397 line ("adds ~1-2 weeks wall-clock,
  zero token cost") IS flagged — weeks used as effort. S317: that line was
  CURED in the live plan by Owner decision (18de98e: it now declares
  external-wait semantics per ADR-081), which killed a positive control
  that lived on mutable prose — the checker went silent and three tests
  broke on a legitimate edit. The vocabulary still comes from the real
  corpus, but it is now FROZEN as a fixture, so curing a finding can never
  again disarm the control that proves the checker fires. The cure itself
  became a checked claim (test_live_plan_153_anchor_stays_cured).
- NEGATIVE: PLAN-172-honest-speed-e0b-e5-e6.md yields ZERO findings —
  its "estende 2 semanas"/"por 1-2 semanas" lines are telemetry/window
  waits (janela / por-N-semanas idiom), not effort.
- NEGATIVE: "hold 24h" / "soak 7d" fixtures are never flagged.
- The tool is ADVISORY: exit code is 0 in every mode, findings or not.
- ADR-081 itself is excluded from the default corpus (it quotes the
  banned vocabulary as its own counter-examples).

Runs the script as a subprocess (the CI invocation shape). Env-isolated by inheriting TestEnvContext (env-hygiene gate compliance); no network.
"""
from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

_SCRIPT = _REPO_ROOT / ".claude" / "scripts" / "check-time-unit.py"
_LIVE_153 = _REPO_ROOT / ".claude" / "plans" / "PLAN-153-ecc-comparative-uplift.md"
_NEG_ANCHOR = _REPO_ROOT / ".claude" / "plans" / "PLAN-172-honest-speed-e0b-e5-e6.md"

# The pre-cure PLAN-153:397 text, verbatim from git (18de98e^). Frozen so the
# positive control survives edits to the live corpus.
_FROZEN_POSITIVE_LINE = (
    "   (adds ~1-2 weeks wall-clock, zero token cost); (c) hybrid — skip for new"
)
_FROZEN_ANCHOR_LINE_NO = 4


def _run(*args: str) -> "subprocess.CompletedProcess[str]":
    return subprocess.run(
        [sys.executable, str(_SCRIPT), *args],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        universal_newlines=True, cwd=str(_REPO_ROOT))


def _frozen_anchor_file(test: unittest.TestCase) -> str:
    """Write the frozen historical anchor to a temp .md and return its path.

    The flagged line lands at _FROZEN_ANCHOR_LINE_NO by construction.
    """
    with tempfile.NamedTemporaryFile(
            "w", suffix=".md", delete=False, encoding="utf-8") as fh:
        fh.write("created: 2026-08-01\n"
                 "\n"
                 "1. Soak windows (frozen excerpt of PLAN-153:397).\n"
                 + _FROZEN_POSITIVE_LINE + "\n")
        path = fh.name
    test.addCleanup(lambda: Path(path).unlink(missing_ok=True))
    return path


class CheckTimeUnitTests(TestEnvContext):
    def test_frozen_positive_anchor_is_flagged(self) -> None:
        # Controle POSITIVO: se este parar de disparar, o checker morreu.
        path = _frozen_anchor_file(self)
        proc = _run(path)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn(":{0}:".format(_FROZEN_ANCHOR_LINE_NO), proc.stdout)
        self.assertIn("weeks wall-clock", proc.stdout)

    def test_live_plan_153_anchor_stays_cured(self) -> None:
        # A cura do Owner (18de98e) vira claim VERIFICADA: reintroduzir o
        # "adds ~1-2 weeks wall-clock" cru no PLAN-153 quebra este teste.
        proc = _run(str(_LIVE_153))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("0 finding(s)", proc.stdout)

    def test_negative_anchor_plan_172_external_wait_not_flagged(self) -> None:
        proc = _run(str(_NEG_ANCHOR))
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("0 finding(s)", proc.stdout)

    def test_hold_and_soak_windows_are_never_flagged(self) -> None:
        with tempfile.NamedTemporaryFile(
                "w", suffix=".md", delete=False, encoding="utf-8") as fh:
            fh.write("created: 2026-08-01\n"
                     "hold 24h antes do GA (ADR-103)\n"
                     "SKILL.md exige SP-NNN + soak 7d\n"
                     "coleta de telemetria por 30 dias\n")
            tmp = fh.name
        try:
            proc = _run(tmp)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn("0 finding(s)", proc.stdout)
        finally:
            Path(tmp).unlink()

    def test_effort_weeks_in_dated_fixture_is_flagged(self) -> None:
        with tempfile.NamedTemporaryFile(
                "w", suffix=".md", delete=False, encoding="utf-8") as fh:
            fh.write("created: 2026-08-01\n"
                     "a implementacao leva ~2-3 semanas\n")
            tmp = fh.name
        try:
            proc = _run(tmp)
            self.assertEqual(proc.returncode, 0)
            self.assertIn("1 finding(s)", proc.stdout)
        finally:
            Path(tmp).unlink()

    def test_advisory_exit_zero_even_with_findings(self) -> None:
        proc = _run(_frozen_anchor_file(self))
        self.assertEqual(proc.returncode, 0)
        self.assertNotIn("0 finding(s)", proc.stdout)

    def test_default_corpus_excludes_adr_081_itself(self) -> None:
        proc = _run()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertNotIn("ADR-081-token-as-time-unit.md:", proc.stdout)

    def test_json_mode_is_machine_readable(self) -> None:
        import json as _json
        proc = _run(_frozen_anchor_file(self), "--json")
        rows = _json.loads(proc.stdout)
        self.assertTrue(
            any(r["line"] == _FROZEN_ANCHOR_LINE_NO for r in rows))


if __name__ == "__main__":
    unittest.main()
