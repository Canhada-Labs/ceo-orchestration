"""PLAN-112-FOLLOWUP-pair-rail-decide-canonical — W0 golden-input freeze.

Captures the OBSERVABLE output of ``_decide_with_matrix()`` for the
REACHABLE cases {A, B, F} + kill-switch + sentinel-bypass into immutable
in-test golden fixtures, BEFORE the W2 refactor touches a line.

Observable surface per plan §3 W0 (byte-identity contract):
  - the returned decision dict (``decision`` absent -> implicit allow;
    ``systemMessage`` content),
  - the emitted ``pair_rail_case`` audit row's ``case`` field,
  - the emitted row's ``precondition_met`` field (matters for Case B),
  - the emitted row's verdict pair (``claude_verdict`` / ``codex_verdict``).

NO C/D/E claims -- those cases are NOT reachable from the procedural
``base`` dict (plan §2a.2 / §2a.4). The golden set is {A, B, F,
kill-switch, sentinel-bypass} only.

This test is BEHAVIOR-PRESERVING by construction: the GOLDEN constants
below are the frozen pre-refactor truth. After the W2 delegation to
``_lib.pair_rail_decide.detect_case`` lands, this exact test must still
pass byte-identically -- it is the drift guard.

Path resolution mirrors test_check_pair_rail_matrix.py (canonical OR
staging). stdlib only.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile
import types
import unittest
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import patch

# ---------------------------------------------------------------------------
# Path resolution -- staging OR canonical position (mirrors matrix test).
# ---------------------------------------------------------------------------
_THIS_FILE = Path(__file__).resolve()
_IS_STAGING = "staging" in _THIS_FILE.parts and "phase-3" in _THIS_FILE.parts

if _IS_STAGING:
    _REPO_ROOT = _THIS_FILE.parents[6]
    _HOOKS_DIR = _THIS_FILE.parents[1] / "hooks"
    _LIB_PARENT = _THIS_FILE.parents[1]
else:
    # Canonical: file at .claude/hooks/tests/<this>.py.
    _REPO_ROOT = _THIS_FILE.parents[3]
    _HOOKS_DIR = _THIS_FILE.parents[1]  # = .claude/hooks/
    _LIB_PARENT = _THIS_FILE.parents[1]

if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))
if str(_LIB_PARENT) not in sys.path:
    sys.path.insert(0, str(_LIB_PARENT))

_HOOK_PATH = _HOOKS_DIR / "check_pair_rail.py"


def _load_hook() -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(
        "check_pair_rail_golden",
        str(_HOOK_PATH),
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


try:
    _CPR = _load_hook()
except Exception as exc:  # pragma: no cover - import guard
    raise ImportError(
        f"Failed to load check_pair_rail.py from {_HOOK_PATH}: {exc}"
    ) from exc


_MINIMAL_CATALOGUE_YAML = """\
catalogue_version: "1.0.0-rc.1"
plan: PLAN-081
phase: 3
spec_ref: PLAN-075/spec.md §11
adr_refs: [ADR-107, ADR-108]

violations:

  - id: cr-bug-null-deref
    severity_default: P0
    description: Null deref reachable from public entry point
    scope: code-review
"""

_L3_PATH_REL = ".claude/hooks/_lib/payload.py"


def _make_repo(tmp_path: Path) -> Path:
    policies_dir = tmp_path / ".claude" / "policies"
    policies_dir.mkdir(parents=True, exist_ok=True)
    (policies_dir / "rubric-violation-catalogue.yaml").write_text(
        _MINIMAL_CATALOGUE_YAML, encoding="utf-8"
    )
    return tmp_path


def _reset_catalogue_cache() -> None:
    _CPR._RUBRIC_CATALOGUE_CACHE = None  # type: ignore[attr-defined]


def _l3_abs(repo_root: Path) -> str:
    return str(repo_root / _L3_PATH_REL)


def _read_sink(sink_path: Path) -> List[Dict[str, Any]]:
    if not sink_path.exists():
        return []
    events: List[Dict[str, Any]] = []
    for line in sink_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            try:
                events.append(json.loads(line))
            except ValueError:
                pass
    return events


def _case_rows(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [e for e in events if e.get("action") == "pair_rail_case" or "case" in e]


# ---------------------------------------------------------------------------
# GOLDEN constants -- the frozen pre-refactor truth (plan §3 W0).
# These are IMMUTABLE: the W2 refactor must keep every field byte-identical.
# ---------------------------------------------------------------------------

# Case A -- clean review: allow (no decision key) + sysmsg "review clean"
#           + case=A row, PASS/PASS, precondition_met=False (default).
_GOLDEN_A = {
    "sysmsg_substr": "review clean",
    "case": "A",
    "precondition_met": False,
    "claude_verdict": "PASS",
    "codex_verdict": "PASS",
}

# Case B -- write-shaped advisory: allow (no decision key) + sysmsg
#           "PAIR-RAIL-ADVISORY" + case=B row, PASS/BLOCK.
#           precondition_met=False because the procedural grammar carries
#           NO file:line / rubric_id (check_pair_rail.py:1200-1206 ->
#           _validate_provider_pair returns (False, "missing_file_line")).
_GOLDEN_B = {
    "sysmsg_substr": "PAIR-RAIL-ADVISORY",
    "case": "B",
    "precondition_met": False,
    "claude_verdict": "PASS",
    "codex_verdict": "BLOCK",
}

# Case F -- Codex unavailable: allow (no decision key) + sysmsg
#           "Codex unavailable" + case=F row, PASS/TIMEOUT (unavailable
#           coerces to TIMEOUT for schema, check_pair_rail.py:1166-1169).
_GOLDEN_F = {
    "sysmsg_substr": "Codex unavailable",
    "case": "F",
    "claude_verdict": "PASS",
    "codex_verdict": "TIMEOUT",
}

# Sentinel-bypass -- allow + sysmsg "bypass via Architect sentinel"
#                    + NO matrix case emit (Owner-authorized).
_GOLDEN_SENTINEL = {
    "sysmsg_substr": "bypass via Architect sentinel",
}


class TestGoldenInputFreeze(unittest.TestCase):
    """W0 -- pin the observable output for the reachable cases.

    These tests MUST pass identically before AND after the W2 refactor.
    """

    def setUp(self) -> None:
        _reset_catalogue_cache()
        self._orig = {
            k: os.environ.get(k)
            for k in (
                "CEO_PAIR_RAIL_FIXTURE_RESPONSE",
                "CEO_PAIR_RAIL_AUDIT_SINK",
                "CEO_PAIR_RAIL_DISABLE",
                "CEO_PAIR_RAIL_CODEX_BIN",
            )
        }

    def tearDown(self) -> None:
        _reset_catalogue_cache()
        for key, val in self._orig.items():
            if val is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = val

    # ------------------------------------------------------------------
    # Case A
    # ------------------------------------------------------------------
    def test_golden_case_a_clean_review(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            sink = Path(td) / "sink.jsonl"
            # PLAN-142: Case A (clean review -> PASS/PASS) now comes from a
            # STRUCTURED verdict object, not free text. A forged free-text
            # "looks good" degrades to ADVISORY (R-SEC-2), which is no longer
            # Case A. The golden input is updated to the structured PASS object
            # the 0.139 rail actually parses; the observable output (sysmsg
            # "review clean" + case=A PASS/PASS) is preserved.
            os.environ["CEO_PAIR_RAIL_FIXTURE_RESPONSE"] = json.dumps({
                "verdict": "PASS",
                "findings": [],
                "summary": "Code looks good. No issues found.",
            })
            os.environ["CEO_PAIR_RAIL_AUDIT_SINK"] = str(sink)
            result = _CPR._decide_with_matrix(
                tool_name="Write",
                file_path=_l3_abs(repo),
                proposed_content="x = 1",
                repo_root=repo,
                timeout_s=5.0,
            )
            self.assertNotIn("decision", result)
            self.assertIn(_GOLDEN_A["sysmsg_substr"], result.get("systemMessage", ""))
            rows = _case_rows(_read_sink(sink))
            a_rows = [r for r in rows if r.get("case") == "A"]
            self.assertEqual(len(a_rows), 1, f"expected exactly one case=A row; got {rows}")
            row = a_rows[0]
            self.assertEqual(row.get("claude_verdict"), _GOLDEN_A["claude_verdict"])
            self.assertEqual(row.get("codex_verdict"), _GOLDEN_A["codex_verdict"])
            self.assertEqual(bool(row.get("precondition_met")), _GOLDEN_A["precondition_met"])

    # ------------------------------------------------------------------
    # Case B
    # ------------------------------------------------------------------
    def test_golden_case_b_write_shape_advisory(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            sink = Path(td) / "sink.jsonl"
            os.environ["CEO_PAIR_RAIL_FIXTURE_RESPONSE"] = (
                "*** Update File: .claude/hooks/_lib/payload.py\n"
                "+ x = 1\n"
            )
            os.environ["CEO_PAIR_RAIL_AUDIT_SINK"] = str(sink)
            result = _CPR._decide_with_matrix(
                tool_name="Write",
                file_path=_l3_abs(repo),
                proposed_content="y = 2",
                repo_root=repo,
                timeout_s=5.0,
            )
            self.assertNotIn("decision", result)
            self.assertIn(_GOLDEN_B["sysmsg_substr"], result.get("systemMessage", ""))
            rows = _case_rows(_read_sink(sink))
            b_rows = [r for r in rows if r.get("case") == "B"]
            self.assertEqual(len(b_rows), 1, f"expected exactly one case=B row; got {rows}")
            row = b_rows[0]
            self.assertEqual(row.get("claude_verdict"), _GOLDEN_B["claude_verdict"])
            self.assertEqual(row.get("codex_verdict"), _GOLDEN_B["codex_verdict"])
            # precondition_met is the load-bearing byte-identity field for B.
            self.assertEqual(
                bool(row.get("precondition_met")),
                _GOLDEN_B["precondition_met"],
                "Case-B precondition_met drifted -- byte-identity violation",
            )

    # ------------------------------------------------------------------
    # Case F
    # ------------------------------------------------------------------
    def test_golden_case_f_codex_unavailable(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            sink = Path(td) / "sink.jsonl"
            # CRITICAL: the fixture env MUST be UNSET. With a fixture set
            # (even ""), _invoke_codex_review returns it verbatim as a
            # "review" — empty string parses as a clean review (Case A),
            # NOT unavailable. Real Case F requires the subprocess spawn
            # path to fail; we force that with a nonexistent binary.
            os.environ.pop("CEO_PAIR_RAIL_FIXTURE_RESPONSE", None)
            os.environ["CEO_PAIR_RAIL_AUDIT_SINK"] = str(sink)
            os.environ["CEO_PAIR_RAIL_CODEX_BIN"] = "/nonexistent/codex-bin-zzz"
            result = _CPR._decide_with_matrix(
                tool_name="Write",
                file_path=_l3_abs(repo),
                proposed_content="z = 3",
                repo_root=repo,
                timeout_s=1.0,
            )
            self.assertNotIn("decision", result)
            sysmsg = result.get("systemMessage", "")
            # The exact unavailable-vs-timeout wording can vary by platform
            # spawn error, but it MUST be a Codex-fail sysmsg -> Case F.
            self.assertTrue(
                any(
                    s in sysmsg
                    for s in ("Codex unavailable", "Codex timeout", "Codex malformed")
                ),
                f"expected a Codex-fail sysmsg; got {sysmsg!r}",
            )
            rows = _case_rows(_read_sink(sink))
            f_rows = [r for r in rows if r.get("case") == "F"]
            self.assertEqual(len(f_rows), 1, f"expected exactly one case=F row; got {rows}")
            row = f_rows[0]
            self.assertEqual(row.get("claude_verdict"), _GOLDEN_F["claude_verdict"])
            # Codex unavailable + timeout both coerce to TIMEOUT; malformed -> MALFORMED.
            self.assertIn(row.get("codex_verdict"), ("TIMEOUT", "MALFORMED"))

    # ------------------------------------------------------------------
    # Kill-switch
    # ------------------------------------------------------------------
    def test_golden_kill_switch_no_matrix_emit(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            sink = Path(td) / "sink.jsonl"
            os.environ["CEO_PAIR_RAIL_DISABLE"] = "1"
            os.environ["CEO_PAIR_RAIL_AUDIT_SINK"] = str(sink)
            result = _CPR._decide_with_matrix(
                tool_name="Write",
                file_path=_l3_abs(repo),
                proposed_content="z = 42",
                repo_root=repo,
                timeout_s=5.0,
            )
            self.assertNotIn("decision", result)
            rows = _case_rows(_read_sink(sink))
            matrix_rows = [r for r in rows if r.get("case") in ("A", "B", "C", "D", "E", "F")]
            self.assertEqual(matrix_rows, [], f"kill-switch must not emit a matrix case; got {matrix_rows}")

    # ------------------------------------------------------------------
    # Sentinel-bypass
    # ------------------------------------------------------------------
    def test_golden_sentinel_bypass_no_matrix_emit(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo = _make_repo(Path(td))
            sink = Path(td) / "sink.jsonl"
            os.environ["CEO_PAIR_RAIL_AUDIT_SINK"] = str(sink)
            os.environ["CEO_PAIR_RAIL_FIXTURE_RESPONSE"] = "Looks good."
            with patch.object(_CPR, "_sentinel_grants_pair_rail_bypass", return_value=True):
                result = _CPR._decide_with_matrix(
                    tool_name="Write",
                    file_path=_l3_abs(repo),
                    proposed_content="a = 1",
                    repo_root=repo,
                    timeout_s=5.0,
                )
            self.assertNotIn("decision", result)
            self.assertIn(_GOLDEN_SENTINEL["sysmsg_substr"], result.get("systemMessage", ""))
            rows = _case_rows(_read_sink(sink))
            matrix_rows = [r for r in rows if r.get("case") in ("A", "B", "C", "D", "E", "F")]
            self.assertEqual(matrix_rows, [], f"sentinel-bypass must not emit a matrix case; got {matrix_rows}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
