"""Unit tests for ``.claude/scripts/approval_gate.py`` (PLAN-190 W3).

The property under test: APPROVED only when every rule passes; anything
missing, ambiguous or inconsistent is REJECTED with the rule named. Fixtures
are neutral (no consumer data)."""
from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path

_REPO = Path(__file__).resolve()
while not (_REPO / ".claude").is_dir() or not (_REPO / "VERSION").is_file():
    if _REPO.parent == _REPO:
        raise RuntimeError("repo root not found")
    _REPO = _REPO.parent
sys.path.insert(0, str(_REPO / ".claude" / "hooks"))
from _lib.testing import TestEnvContext  # noqa: E402

SCRIPT = _REPO / ".claude" / "scripts" / "approval_gate.py"
FIX = _REPO / "tests" / "fixtures" / "approval"


def _load_module():
    spec = importlib.util.spec_from_file_location("approval_gate", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


class ApprovalGateDecide(TestEnvContext):
    def setUp(self):
        super().setUp()
        self.ag = _load_module()
        self.policy = json.loads((FIX / "policy-default.json").read_text(encoding="utf-8"))
        self.ok = json.loads((FIX / "evidence-approved.json").read_text(encoding="utf-8"))

    def _reject(self, evidence, needle):
        out = self.ag.decide(self.policy, evidence)
        self.assertEqual(out["decision"], "REJECTED", out)
        self.assertTrue(any(needle in r for r in out["reasons"]), "expected reason containing %r, got %s" % (needle, out["reasons"]))
        return out

    def test_fixture_is_approved(self):
        out = self.ag.decide(self.policy, self.ok)
        self.assertEqual(out["decision"], "APPROVED", out)
        self.assertEqual(out["reasons"], [])
        self.assertEqual(len(out["policy_sha256"]), 64)

    def test_score_below_minimum_is_rejected(self):
        e = copy.deepcopy(self.ok); e["review"]["score"] = 6
        self._reject(e, "below minimum")

    def test_score_as_prose_is_ambiguous_and_rejected(self):
        e = copy.deepcopy(self.ok); e["review"]["score"] = "bom, aprovável"
        self._reject(e, "not numeric")

    def test_score_fraction_on_wrong_scale_is_rejected(self):
        e = copy.deepcopy(self.ok); e["review"]["score"] = "4/5"
        self._reject(e, "denominator")

    def test_score_fraction_on_right_scale_is_accepted(self):
        e = copy.deepcopy(self.ok); e["review"]["score"] = "8/10"
        self.assertEqual(self.ag.decide(self.policy, e)["decision"], "APPROVED")

    def test_blocking_severity_is_rejected(self):
        e = copy.deepcopy(self.ok); e["review"]["findings"].append({"severity": "P0", "where": "x:1", "text": "boom"})
        self._reject(e, "blocking severity P0")

    def test_severity_outside_enum_is_ambiguous_and_rejected(self):
        e = copy.deepcopy(self.ok); e["review"]["findings"].append({"severity": "alta, mas aceitável", "where": "x:1", "text": "prosa"})
        self._reject(e, "not in enum")

    def test_open_p1_beyond_cap_is_rejected(self):
        e = copy.deepcopy(self.ok); e["review"]["findings"].append({"severity": "P1", "where": "x:1", "text": "real"})
        self._reject(e, "exceed max_open")

    def test_missing_findings_key_is_rejected_not_treated_as_none(self):
        e = copy.deepcopy(self.ok); del e["review"]["findings"]
        self._reject(e, "review.findings missing")

    def test_review_of_older_revision_is_rejected(self):
        e = copy.deepcopy(self.ok); e["review"]["reviewed_rev"] = "ffffffffffffffffffffffffffffffffffffffff"
        self._reject(e, "final revision")

    def test_missing_reviewed_rev_is_rejected(self):
        e = copy.deepcopy(self.ok); del e["review"]["reviewed_rev"]
        self._reject(e, "reviewed_rev missing")

    def test_review_not_run_is_rejected(self):
        e = copy.deepcopy(self.ok); e["review"]["ran"] = False
        self._reject(e, "did not run")

    def test_failing_gate_command_is_rejected(self):
        e = copy.deepcopy(self.ok); e["gate"][0]["rc"] = 1
        self._reject(e, "rc=1")

    def test_gate_with_failures_is_rejected_even_when_rc_zero(self):
        e = copy.deepcopy(self.ok); e["gate"][0]["failed"] = 2
        self._reject(e, "failed=2")

    def test_empty_gate_is_rejected(self):
        e = copy.deepcopy(self.ok); e["gate"] = []
        self._reject(e, "gate missing or empty")

    def test_wrong_schema_is_rejected(self):
        e = copy.deepcopy(self.ok); e["schema"] = "something/else"
        self._reject(e, "evidence.schema")

    def test_invalid_policy_is_rejected_before_anything_else(self):
        p = copy.deepcopy(self.policy); p["severities"]["blocking"] = ["P9"]
        out = self.ag.decide(p, self.ok)
        self.assertEqual(out["decision"], "REJECTED")
        self.assertTrue(any("invalid policy" in r for r in out["reasons"]))

    def test_multiple_defects_all_named(self):
        e = copy.deepcopy(self.ok)
        e["review"]["score"] = 3
        e["gate"][0]["rc"] = 2
        out = self._reject(e, "below minimum")
        self.assertTrue(any("rc=2" in r for r in out["reasons"]))


class ApprovalGateCLI(TestEnvContext):
    def _run(self, policy_path, evidence_path, extra=()):
        return subprocess.run([sys.executable, str(SCRIPT), "decide", "--policy", str(policy_path), "--evidence", str(evidence_path), *extra],
                              capture_output=True, text=True, timeout=60, cwd=str(_REPO))

    def test_cli_rc_0_on_approved_and_3_on_rejected(self):
        ok = self._run(FIX / "policy-default.json", FIX / "evidence-approved.json", ["--json"])
        self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
        self.assertEqual(json.loads(ok.stdout)["decision"], "APPROVED")
        with tempfile.TemporaryDirectory() as td:
            bad = Path(td) / "bad.json"
            e = json.loads((FIX / "evidence-approved.json").read_text(encoding="utf-8")); e["review"]["score"] = 1
            bad.write_text(json.dumps(e), encoding="utf-8")
            r = self._run(FIX / "policy-default.json", bad)
            self.assertEqual(r.returncode, 3)
            self.assertIn("REJECTED", r.stdout)

    def test_cli_rc_2_on_unreadable_input(self):
        r = self._run(FIX / "policy-default.json", Path("/definitely/missing.json"))
        self.assertEqual(r.returncode, 2)
        self.assertIn("REJECTED", r.stdout)
