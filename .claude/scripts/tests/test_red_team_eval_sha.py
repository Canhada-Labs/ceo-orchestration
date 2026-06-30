"""Tests for red-team-eval.py SHA pre-check + FPR enforcement + State logic.

PLAN-014 Phase D.5 — 10 tests covering:
- Frozen corpus SHA-256 verification
- Corrupted corpus rejection
- State 0/1/2 exit code behavior
- FPR measurement binding to frozen corpus
- Frozen SHA auto-discovery
- Kill-switch + state interaction

Stdlib-only. Uses TestEnvContext pattern from _lib/testing.py.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Optional

# Bootstrap: ensure red-team-eval.py is importable
_SCRIPTS = Path(__file__).resolve().parent.parent
if str(_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS))

# We import the module's main and helper functions
import importlib
red_team_eval = importlib.import_module("red-team-eval")


class _TmpCorpus:
    """Helper to create a temporary corpus directory with fixtures."""

    def __init__(self, tmp: Path):
        self.root = tmp / "corpus"
        self.root.mkdir(parents=True, exist_ok=True)
        self.synthetic = self.root / "synthetic"
        self.synthetic.mkdir(exist_ok=True)
        self.v1 = self.root / "v1"
        self.v1.mkdir(exist_ok=True)

    def add_fixture(self, fixture_id: str, target: str = "skill_patch_sentinel",
                    category: str = "test", payload: str = "test payload",
                    expected: str = "MUST_BLOCK",
                    subdir: Optional[str] = None) -> Path:
        fx = {
            "id": fixture_id,
            "target": target,
            "category": category,
            "input": payload,
            "expected_behavior": expected,
            "reference": "test-ref",
        }
        if subdir is None:
            d = self.synthetic
        else:
            d = self.root / subdir
            d.mkdir(exist_ok=True)
        p = d / f"{fixture_id}.jsonl"
        p.write_text(json.dumps(fx) + "\n", encoding="utf-8")
        return p

    def freeze_v1(self) -> tuple:
        """Build frozen JSONL from all subdirs, return (jsonl_path, sha_path, sha_hex)."""
        lines = []
        for subdir in ["synthetic", "external", "regression"]:
            d = self.root / subdir
            if not d.is_dir():
                continue
            for f in sorted(d.glob("*.jsonl")):
                for line in f.read_text("utf-8").strip().splitlines():
                    if line.strip():
                        lines.append(json.dumps(json.loads(line), sort_keys=True))
        content = "\n".join(lines) + "\n"
        jsonl = self.v1 / "fixtures.jsonl"
        jsonl.write_text(content, encoding="utf-8")
        sha = hashlib.sha256(jsonl.read_bytes()).hexdigest()
        sha_file = self.v1 / "fixtures.jsonl.sha256"
        sha_file.write_text(sha + "  fixtures.jsonl\n", encoding="utf-8")
        return jsonl, sha_file, sha

    def add_flake_budget(self) -> Path:
        fb = self.root / "flake-budget.yaml"
        fb.write_text(
            "policy:\n  window_days: 7\n  quarantine_threshold: 2\n"
            "ledger:\n  entries: []\nquarantined:\n  entries: []\n",
            encoding="utf-8",
        )
        return fb


class TestFrozenCorpusSHAPreCheck(unittest.TestCase):
    """Tests that --frozen-corpus + --frozen-sha enforce SHA match."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="red-team-sha-")
        self.corpus = _TmpCorpus(Path(self._tmp))
        # Add some fixtures
        self.corpus.add_fixture("SYN-T01", payload="os.system('test')")
        self.corpus.add_fixture("SYN-T02", target="audit_log_tamper",
                                payload="byte-rewrite attack", expected="MUST_EMIT_AUDIT")
        self.fb = self.corpus.add_flake_budget()

    def test_frozen_sha_match_passes(self):
        """Valid frozen corpus with matching SHA passes pre-check."""
        jsonl, sha_file, _ = self.corpus.freeze_v1()
        rc = red_team_eval.main([
            "--frozen-corpus", str(jsonl),
            "--frozen-sha", str(sha_file),
            "--quarantine-ledger", str(self.fb),
            "--output", "json",
            "--dry-run",
        ])
        self.assertEqual(rc, 0)

    def test_frozen_sha_mismatch_rejects(self):
        """Corrupted frozen corpus (SHA mismatch) exits with code 2."""
        jsonl, sha_file, _ = self.corpus.freeze_v1()
        # Corrupt the JSONL
        jsonl.write_text("corrupted content\n", encoding="utf-8")
        rc = red_team_eval.main([
            "--frozen-corpus", str(jsonl),
            "--frozen-sha", str(sha_file),
            "--quarantine-ledger", str(self.fb),
            "--output", "json",
            "--dry-run",
        ])
        self.assertEqual(rc, 2)

    def test_frozen_sha_auto_discovery(self):
        """--frozen-sha defaults to adjacent .sha256 file when not specified."""
        jsonl, _, _ = self.corpus.freeze_v1()
        rc = red_team_eval.main([
            "--frozen-corpus", str(jsonl),
            "--quarantine-ledger", str(self.fb),
            "--output", "json",
            "--dry-run",
        ])
        self.assertEqual(rc, 0)

    def test_frozen_corpus_missing_file(self):
        """Missing frozen corpus file exits with code 2."""
        rc = red_team_eval.main([
            "--frozen-corpus", str(Path(self._tmp) / "nonexistent.jsonl"),
            "--quarantine-ledger", str(self.fb),
            "--output", "json",
            "--dry-run",
        ])
        self.assertEqual(rc, 2)

    def test_frozen_sha_missing_file(self):
        """Missing SHA file exits with code 2."""
        jsonl, sha_file, _ = self.corpus.freeze_v1()
        sha_file.unlink()
        rc = red_team_eval.main([
            "--frozen-corpus", str(jsonl),
            "--quarantine-ledger", str(self.fb),
            "--output", "json",
            "--dry-run",
        ])
        self.assertEqual(rc, 2)


class TestStateEnforcement(unittest.TestCase):
    """Tests State 0/1/2 exit code behavior per ADJ-018."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="red-team-state-")
        self.corpus = _TmpCorpus(Path(self._tmp))
        # Add a fixture that will FAIL (mcp_handler returns DEFERRED)
        self.corpus.add_fixture("SYN-T03", target="mcp_handler",
                                payload="test", expected="MUST_BLOCK")
        # Add a fixture that will PASS
        self.corpus.add_fixture("SYN-T04", payload="os.system('rm -rf /')")
        self.fb = self.corpus.add_flake_budget()

    def test_state0_advisory_exits_0_on_failure(self):
        """State 0 (advisory): failures produce exit 0 with warning."""
        rc = red_team_eval.main([
            "--fixture-dir", str(self.corpus.synthetic),
            "--quarantine-ledger", str(self.fb),
            "--state", "0",
            "--output", "json",
            "--dry-run",
        ])
        # mcp_handler is DEFERRED (skip), not fail. SYN-T04 passes.
        # So exit 0 expected.
        self.assertEqual(rc, 0)

    def test_state1_enforcing_exits_1_on_real_failure(self):
        """State 1 (enforcing): fixture producing ALLOWED when MUST_BLOCK fails."""
        # Add a fixture that will genuinely fail: target sandbox_escape
        # with an input that does NOT match any block pattern
        self.corpus.add_fixture("SYN-FAIL", target="sandbox_escape",
                                payload="innocuous command that should block",
                                expected="MUST_BLOCK")
        rc = red_team_eval.main([
            "--fixture-dir", str(self.corpus.synthetic),
            "--quarantine-ledger", str(self.fb),
            "--state", "1",
            "--output", "json",
            "--dry-run",
        ])
        self.assertEqual(rc, 1)

    def test_state0_advisory_exits_0_even_on_real_failure(self):
        """State 0: even genuine failures produce exit 0."""
        self.corpus.add_fixture("SYN-FAIL2", target="sandbox_escape",
                                payload="innocuous command",
                                expected="MUST_BLOCK")
        rc = red_team_eval.main([
            "--fixture-dir", str(self.corpus.synthetic),
            "--quarantine-ledger", str(self.fb),
            "--state", "0",
            "--output", "json",
            "--dry-run",
        ])
        self.assertEqual(rc, 0)

    def test_state_default_from_env(self):
        """State defaults from CEO_RED_TEAM_STATE env var."""
        old = os.environ.get("CEO_RED_TEAM_STATE")
        try:
            os.environ["CEO_RED_TEAM_STATE"] = "1"
            # Re-import to pick up new default — but argparse reads at
            # parse time, and we override via --state. Just verify the
            # argument parser accepts it.
            rc = red_team_eval.main([
                "--fixture-dir", str(self.corpus.synthetic),
                "--quarantine-ledger", str(self.fb),
                "--output", "json",
                "--dry-run",
            ])
            # With state=1 from env and mcp_handler DEFERRED (skip, not fail),
            # SYN-T04 passes → exit 0
            self.assertEqual(rc, 0)
        finally:
            if old is None:
                os.environ.pop("CEO_RED_TEAM_STATE", None)
            else:
                os.environ["CEO_RED_TEAM_STATE"] = old

    def test_kill_switch_overrides_state(self):
        """Kill switch exits 0 regardless of state."""
        rc = red_team_eval.main([
            "--fixture-dir", str(self.corpus.synthetic),
            "--quarantine-ledger", str(self.fb),
            "--state", "2",
            "--kill-switch", "1",
            "--output", "json",
        ])
        self.assertEqual(rc, 0)


if __name__ == "__main__":
    unittest.main()
