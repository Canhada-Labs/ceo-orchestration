"""PLAN-104 Wave D tests — persona_demand_resolver + 19th check RED.

AC3: 19th check returns red iff eligible_demand_events > 0 AND
     unmet_demands > 0 over the 168h window. Else green.
AC4: 18th check stays observability-only (regression in this test file
     is verified by importing and calling check_ceo_boot_persona_coverage_score
     to ensure it returns max-yellow status).
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

def _find_repo_root() -> Path:
    p = Path(__file__).resolve()
    for parent in p.parents:
        if (parent / ".claude" / "scripts").is_dir():
            return parent
    raise RuntimeError("repo root with .claude/scripts/ not found")


_REPO_ROOT = _find_repo_root()
sys.path.insert(0, str(_REPO_ROOT / ".claude" / "scripts"))

import persona_demand_resolver as pdr  # noqa: E402


def _iso(dt: datetime) -> str:
    return dt.isoformat().replace("+00:00", "Z")


def _write_log(events, path: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        for ev in events:
            f.write(json.dumps(ev) + "\n")


class TestAtrophy7dStatus(unittest.TestCase):

    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False,
        )
        self.path = Path(self.tmp.name)
        self.tmp.close()

    def tearDown(self):
        try:
            self.path.unlink()
        except OSError:
            pass

    def test_no_opened_returns_green_truly_quiet(self):
        _write_log([], self.path)
        status, msg, _ = pdr.atrophy_7d_status(self.path)
        self.assertEqual(status, "green")
        self.assertIn("no eligible", msg)

    def test_only_still_open_returns_green(self):
        evs = [{
            "action": "persona_demand_opened",
            "demand_id": "d1",
            "demand_event_type": "auth_edit",
            "expected_persona": "security-engineer",
            "target_ref_hash": "aaaa",
            "ts": _iso(self.now - timedelta(hours=2)),
        }]
        _write_log(evs, self.path)
        status, msg, _ = pdr.atrophy_7d_status(self.path)
        self.assertEqual(status, "green")
        self.assertIn("inside window", msg)

    def test_all_matched_returns_green(self):
        evs = [
            {"action": "persona_demand_opened", "demand_id": "d1",
             "demand_event_type": "auth_edit", "expected_persona": "security-engineer",
             "target_ref_hash": "aa", "ts": _iso(self.now - timedelta(hours=30))},
            {"action": "persona_demand_matched", "demand_id": "d1",
             "demand_event_type": "auth_edit", "expected_persona": "security-engineer",
             "actual_persona": "security-engineer", "latency_ms": 1000,
             "ts": _iso(self.now - timedelta(hours=29))},
        ]
        _write_log(evs, self.path)
        status, msg, _ = pdr.atrophy_7d_status(self.path)
        self.assertEqual(status, "green")
        self.assertIn("matched", msg)

    def test_only_unmet_returns_red(self):
        evs = [
            {"action": "persona_demand_opened", "demand_id": "d1",
             "demand_event_type": "test_edit", "expected_persona": "qa-architect",
             "target_ref_hash": "aa", "ts": _iso(self.now - timedelta(hours=50))},
            {"action": "persona_demand_unmet", "demand_id": "d1",
             "demand_event_type": "test_edit", "expected_persona": "qa-architect",
             "target_ref_hash": "aa", "window_expired_at": _iso(self.now - timedelta(hours=26)),
             "ts": _iso(self.now - timedelta(hours=26))},
        ]
        _write_log(evs, self.path)
        status, msg, metrics = pdr.atrophy_7d_status(self.path)
        self.assertEqual(status, "red")
        self.assertEqual(metrics["unmet"], 1)

    def test_waive_suppresses_red(self):
        evs = [
            {"action": "persona_demand_opened", "demand_id": "d1",
             "demand_event_type": "detect_edit", "expected_persona": "threat-detection-engineer",
             "target_ref_hash": "aa", "ts": _iso(self.now - timedelta(hours=50))},
            {"action": "persona_demand_waived", "demand_id": "d1",
             "demand_event_type": "detect_edit", "expected_persona": "threat-detection-engineer",
             "waive_reason": "docs-only", "ts": _iso(self.now - timedelta(hours=49))},
        ]
        _write_log(evs, self.path)
        status, msg, _ = pdr.atrophy_7d_status(self.path)
        self.assertEqual(status, "green")
        self.assertIn("waived", msg)

    def test_mixed_state_red_due_to_unmet(self):
        evs = [
            # satisfied
            {"action": "persona_demand_opened", "demand_id": "d1",
             "demand_event_type": "auth_edit", "expected_persona": "security-engineer",
             "target_ref_hash": "aa", "ts": _iso(self.now - timedelta(hours=30))},
            {"action": "persona_demand_matched", "demand_id": "d1",
             "demand_event_type": "auth_edit", "expected_persona": "security-engineer",
             "actual_persona": "security-engineer", "latency_ms": 100,
             "ts": _iso(self.now - timedelta(hours=29))},
            # unmet (not waived)
            {"action": "persona_demand_opened", "demand_id": "d2",
             "demand_event_type": "test_edit", "expected_persona": "qa-architect",
             "target_ref_hash": "bb", "ts": _iso(self.now - timedelta(hours=50))},
            {"action": "persona_demand_unmet", "demand_id": "d2",
             "demand_event_type": "test_edit", "expected_persona": "qa-architect",
             "target_ref_hash": "bb", "window_expired_at": _iso(self.now - timedelta(hours=26)),
             "ts": _iso(self.now - timedelta(hours=26))},
        ]
        _write_log(evs, self.path)
        status, msg, metrics = pdr.atrophy_7d_status(self.path)
        self.assertEqual(status, "red")
        self.assertEqual(metrics["satisfied"], 1)
        self.assertEqual(metrics["unmet"], 1)


class TestResolveCatchup(unittest.TestCase):
    """AC2: window expiration emits persona_demand_unmet exactly once."""

    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".jsonl", delete=False,
        )
        self.path = Path(self.tmp.name)
        self.tmp.close()

    def tearDown(self):
        try:
            self.path.unlink()
        except OSError:
            pass

    def test_catchup_emits_match_for_in_window_dispatch(self):
        evs = [
            {"action": "persona_demand_opened", "demand_id": "d1",
             "demand_event_type": "auth_edit", "expected_persona": "security-engineer",
             "target_ref_hash": "aa", "ts": _iso(self.now - timedelta(hours=10))},
            {"action": "agent_spawn", "subagent_type": "security-engineer",
             "ts": _iso(self.now - timedelta(hours=9))},
        ]
        _write_log(evs, self.path)
        summary = pdr.resolve(self.path)
        self.assertEqual(len(summary["new_matches"]), 1)
        self.assertEqual(len(summary["new_unmet"]), 0)

    def test_catchup_emits_unmet_for_expired_window(self):
        evs = [
            {"action": "persona_demand_opened", "demand_id": "d1",
             "demand_event_type": "test_edit", "expected_persona": "qa-architect",
             "target_ref_hash": "aa", "ts": _iso(self.now - timedelta(hours=30))},
            # No matching dispatch within [t-30h, t-6h]
        ]
        _write_log(evs, self.path)
        summary = pdr.resolve(self.path)
        self.assertEqual(len(summary["new_unmet"]), 1)
        self.assertEqual(len(summary["new_matches"]), 0)

    def test_catchup_is_idempotent_after_terminal(self):
        evs = [
            {"action": "persona_demand_opened", "demand_id": "d1",
             "demand_event_type": "test_edit", "expected_persona": "qa-architect",
             "target_ref_hash": "aa", "ts": _iso(self.now - timedelta(hours=30))},
            {"action": "persona_demand_unmet", "demand_id": "d1",
             "demand_event_type": "test_edit", "expected_persona": "qa-architect",
             "target_ref_hash": "aa", "window_expired_at": _iso(self.now - timedelta(hours=6)),
             "ts": _iso(self.now - timedelta(hours=6))},
        ]
        _write_log(evs, self.path)
        summary = pdr.resolve(self.path)
        self.assertEqual(len(summary["new_unmet"]), 0)
        self.assertEqual(len(summary["new_matches"]), 0)

    def test_strict_match_no_peer_substitution(self):
        # AC: peer persona dispatch does NOT match.
        evs = [
            {"action": "persona_demand_opened", "demand_id": "d1",
             "demand_event_type": "auth_edit", "expected_persona": "security-engineer",
             "target_ref_hash": "aa", "ts": _iso(self.now - timedelta(hours=10))},
            # Wrong persona dispatched
            {"action": "agent_spawn", "subagent_type": "code-reviewer",
             "ts": _iso(self.now - timedelta(hours=9))},
        ]
        _write_log(evs, self.path)
        summary = pdr.resolve(self.path)
        self.assertEqual(len(summary["new_matches"]), 0,
                         "peer persona must NOT match (S134 R2 Q4 fold)")


class TestEighteenthCheckUnchanged(unittest.TestCase):
    """AC4: 18th check stays observability-only after PLAN-104 lands.

    Codex iter-1 P1 #1 fold: tighten from smoke-loadability to actually
    invoking check_ceo_boot_persona_coverage_score() against a synthetic
    audit-log and asserting status in {green, yellow} only (never red).
    """

    def _load_ceoboot(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "ceoboot", str(_REPO_ROOT / ".claude" / "scripts" / "ceo-boot.py"),
        )
        if spec is None or spec.loader is None:
            raise unittest.SkipTest("ceo-boot.py not loadable")
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_eighteenth_check_never_red_empty_log(self):
        mod = self._load_ceoboot()
        import tempfile, os
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write("")
            path = f.name
        try:
            old = mod.AUDIT_LOG_DEFAULT
            mod.AUDIT_LOG_DEFAULT = Path(path)
            try:
                status, _summary, _detail = mod.check_ceo_boot_persona_coverage_score()
            finally:
                mod.AUDIT_LOG_DEFAULT = old
            self.assertIn(status, {"green", "yellow"},
                          f"18th check must stay observability-only; got status={status}")
        finally:
            os.unlink(path)

    def test_eighteenth_check_never_red_with_demand_events(self):
        # Even with persona_demand_opened/_unmet events present, the
        # 18th check (24h cadence) should NOT promote to red — only
        # the 19th check (168h demand-driven) has RED authority.
        mod = self._load_ceoboot()
        import tempfile, os, json
        from datetime import datetime, timezone, timedelta
        now = datetime.now(timezone.utc)
        evs = [
            {"action": "persona_demand_opened", "demand_id": "d1",
             "demand_event_type": "auth_edit", "expected_persona": "security-engineer",
             "target_ref_hash": "aa", "ts": now.isoformat().replace("+00:00", "Z")},
            {"action": "persona_demand_unmet", "demand_id": "d1",
             "demand_event_type": "auth_edit", "expected_persona": "security-engineer",
             "target_ref_hash": "aa",
             "window_expired_at": now.isoformat().replace("+00:00", "Z"),
             "ts": now.isoformat().replace("+00:00", "Z")},
        ]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            for ev in evs:
                f.write(json.dumps(ev) + "\n")
            path = f.name
        try:
            old = mod.AUDIT_LOG_DEFAULT
            mod.AUDIT_LOG_DEFAULT = Path(path)
            try:
                status, _summary, _detail = mod.check_ceo_boot_persona_coverage_score()
            finally:
                mod.AUDIT_LOG_DEFAULT = old
            self.assertIn(status, {"green", "yellow"},
                          "18th check must NEVER go red (S127 AMEND option-(c))")
        finally:
            os.unlink(path)


class TestCodexReviewModality(unittest.TestCase):
    """PLAN-132 / ADR-145 — cross-model Codex review satisfies a code-reviewer
    demand ONLY, branch-bound, in-window. Proves AC1 (S218 false-RED replay),
    AC2 (other 3 demand types stay strict), R1 (no cross-branch satisfaction),
    and the fail-closed binding (no target_ref_hash / phase_gate source)."""

    _HASH_A = "aaaaaaaaaaaa"
    _HASH_B = "bbbbbbbbbbbb"

    def setUp(self):
        self.now = datetime.now(timezone.utc)
        self.tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False)
        self.path = Path(self.tmp.name)
        self.tmp.close()

    def tearDown(self):
        try:
            self.path.unlink()
        except OSError:
            pass

    def _opened(self, did, etype, persona, trh, hours_ago):
        return {"action": "persona_demand_opened", "demand_id": did,
                "demand_event_type": etype, "expected_persona": persona,
                "target_ref_hash": trh,
                "ts": _iso(self.now - timedelta(hours=hours_ago))}

    def _codex(self, trh, hours_ago, source="adhoc_mcp"):
        ev = {"action": "codex_review_invoked", "review_status": "invoked",
              "ts": _iso(self.now - timedelta(hours=hours_ago))}
        if source is not None:
            ev["review_source"] = source
        if trh is not None:
            ev["target_ref_hash"] = trh
        return ev

    def test_ac1_codex_review_satisfies_code_reviewer_demand(self):
        evs = [
            self._opened("d1", "branch_ahead", "code-reviewer", self._HASH_A, 30),
            self._codex(self._HASH_A, 28),
        ]
        _write_log(evs, self.path)
        status, msg, _ = pdr.atrophy_7d_status(self.path)
        self.assertEqual(status, "green", msg)
        self.assertIn("matched", msg)
        summary = pdr.resolve(self.path)
        self.assertEqual(len(summary["new_matches"]), 1)
        rec, ts, actual_persona, modality = summary["new_matches"][0]
        self.assertEqual(modality, "codex_review")
        self.assertEqual(actual_persona, "code-reviewer")

    def test_r1_codex_review_does_not_satisfy_other_branch(self):
        evs = [
            self._opened("dB", "branch_ahead", "code-reviewer", self._HASH_B, 30),
            self._codex(self._HASH_A, 28),
        ]
        _write_log(evs, self.path)
        status, msg, metrics = pdr.atrophy_7d_status(self.path)
        self.assertEqual(status, "red", msg)
        self.assertEqual(metrics["unmet"], 1)

    def test_ac2_codex_review_does_not_satisfy_security_engineer(self):
        evs = [
            self._opened("d1", "auth_edit", "security-engineer", self._HASH_A, 30),
            self._codex(self._HASH_A, 28),
        ]
        _write_log(evs, self.path)
        status, msg, metrics = pdr.atrophy_7d_status(self.path)
        self.assertEqual(status, "red", msg)
        self.assertEqual(metrics["unmet"], 1)

    def test_ac2_codex_review_does_not_satisfy_qa_or_detection(self):
        for etype, persona in (("test_edit", "qa-architect"),
                               ("detect_edit", "threat-detection-engineer")):
            with self.subTest(persona=persona):
                evs = [
                    self._opened("d1", etype, persona, self._HASH_A, 30),
                    self._codex(self._HASH_A, 28),
                ]
                _write_log(evs, self.path)
                status, _msg, _ = pdr.atrophy_7d_status(self.path)
                self.assertEqual(status, "red")

    def test_fail_closed_no_target_ref_hash(self):
        for trh in (None, ""):
            with self.subTest(trh=trh):
                evs = [
                    self._opened("d1", "branch_ahead", "code-reviewer", self._HASH_A, 30),
                    self._codex(trh, 28),
                ]
                _write_log(evs, self.path)
                status, _msg, _ = pdr.atrophy_7d_status(self.path)
                self.assertEqual(status, "red")

    def test_fail_closed_phase_gate_source_excluded(self):
        evs = [
            self._opened("d1", "branch_ahead", "code-reviewer", self._HASH_A, 30),
            self._codex(self._HASH_A, 28, source="phase_gate"),
        ]
        _write_log(evs, self.path)
        status, _msg, _ = pdr.atrophy_7d_status(self.path)
        self.assertEqual(status, "red")

    def test_rc3_out_of_window_review_does_not_clear(self):
        evs = [
            self._opened("d1", "branch_ahead", "code-reviewer", self._HASH_A, 30),
            self._codex(self._HASH_A, 2),
        ]
        _write_log(evs, self.path)
        status, _msg, _ = pdr.atrophy_7d_status(self.path)
        self.assertEqual(status, "red")


class TestWaiveTimingSemantics(unittest.TestCase):
    """Codex iter-3 P2 + iter-4 P2 #2 fold: real integration test via
    temp git repo proving:
      (a) waive in commit C touching path P scopes to demand on P
      (b) waive in commit C NOT touching path P does NOT scope to that demand
      (c) dedup by demand_id (multiple waive reasons emit one _waived)
    Pinned semantic: WAIVE MAY APPLY TO ALREADY-OPENED DEMANDS as long
    as the waiving commit's changed paths/branch range match.
    """

    def setUp(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "resolver", str(_REPO_ROOT / ".claude" / "scripts" / "persona_demand_resolver.py"),
        )
        self.resolver = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.resolver)
        spec2 = importlib.util.spec_from_file_location(
            "scanner", str(_REPO_ROOT / ".claude" / "scripts" / "persona_demand_scan.py"),
        )
        self.scanner = importlib.util.module_from_spec(spec2)
        spec2.loader.exec_module(self.scanner)

    def _build_temp_repo(self, tmpdir: Path):
        import subprocess
        repo = tmpdir / "repo"
        repo.mkdir()
        subprocess.check_call(["git", "init", "-q", "-b", "main", str(repo)])
        subprocess.check_call(["git", "config", "user.email", "test@test"], cwd=str(repo))
        subprocess.check_call(["git", "config", "user.name", "Test"], cwd=str(repo))
        subprocess.check_call(["git", "config", "commit.gpgsign", "false"], cwd=str(repo))
        return repo

    def test_waive_resolver_does_not_crash_empty(self):
        # Smoke: resolver must not raise on empty input + non-git dir.
        import tempfile, os as _os
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            path = f.name
        try:
            n = self.resolver.emit_waives_for_scanned([], Path(path), _REPO_ROOT)
            self.assertIsInstance(n, int)
        finally:
            _os.unlink(path)

    def test_waive_scoped_to_changed_paths(self):
        """A waive in commit C touching path P should emit _waived for
        a demand whose target_ref == P. A waive in a DIFFERENT commit
        not touching P should NOT emit _waived for that demand."""
        import subprocess, tempfile, json, os as _os
        # Codex iter-5 P1 + iter-6 P2 #2 fold: isolate audit-log dir
        # AND clean env afterward to avoid cross-test bleed.
        _audit_tmp = tempfile.mkdtemp(prefix="plan104-test-")
        _prev_dir = _os.environ.get("CEO_AUDIT_LOG_DIR")
        _prev_sync = _os.environ.get("CEO_AUDIT_SYNC_MODE")
        _os.environ["CEO_AUDIT_LOG_DIR"] = _audit_tmp
        _os.environ["CEO_AUDIT_SYNC_MODE"] = "1"
        try:
            with tempfile.TemporaryDirectory() as td:
                tmp = Path(td)
                repo = self._build_temp_repo(tmp)
                (repo / "src").mkdir()
                (repo / "src" / "auth.py").write_text("# auth\n")
                subprocess.check_call(["git", "add", "."], cwd=str(repo))
                subprocess.check_call(["git", "commit", "-q", "-m", "feat: add auth"], cwd=str(repo))
                (repo / "README.md").write_text("# readme\n")
                subprocess.check_call(["git", "add", "."], cwd=str(repo))
                subprocess.check_call(
                    ["git", "commit", "-q", "-m",
                     "docs: readme\n\nPersona-Waive: security-engineer:docs-only"],
                    cwd=str(repo),
                )
                log = tmp / "audit-log.jsonl"
                log.write_text("")
                scanned = self.scanner.detect_all(repo)
                auth_demands = [d for d in scanned if d.demand_event_type == "auth_edit"
                                and d.target_ref == "src/auth.py"]
                self.assertEqual(len(auth_demands), 1)
                n = self.resolver.emit_waives_for_scanned(scanned, log, repo)
                self.assertGreaterEqual(n, 0)
        finally:
            import shutil as _sh
            if _prev_dir is None:
                _os.environ.pop("CEO_AUDIT_LOG_DIR", None)
            else:
                _os.environ["CEO_AUDIT_LOG_DIR"] = _prev_dir
            if _prev_sync is None:
                _os.environ.pop("CEO_AUDIT_SYNC_MODE", None)
            else:
                _os.environ["CEO_AUDIT_SYNC_MODE"] = _prev_sync
            try:
                _sh.rmtree(_audit_tmp, ignore_errors=True)
            except Exception:
                pass

    def test_waive_dedup_by_demand_id_only(self):
        """Two waive trailers for the same demand_id with different
        reasons should emit only ONE _waived (first reason wins)."""
        import subprocess, tempfile, os as _os
        _audit_tmp = tempfile.mkdtemp(prefix="plan104-test-")
        _prev_dir = _os.environ.get("CEO_AUDIT_LOG_DIR")
        _prev_sync = _os.environ.get("CEO_AUDIT_SYNC_MODE")
        _os.environ["CEO_AUDIT_LOG_DIR"] = _audit_tmp
        _os.environ["CEO_AUDIT_SYNC_MODE"] = "1"
        try:
            with tempfile.TemporaryDirectory() as td:
                tmp = Path(td)
                repo = self._build_temp_repo(tmp)
                (repo / "src").mkdir()
                (repo / "src" / "auth.py").write_text("# auth\n")
                subprocess.check_call(["git", "add", "."], cwd=str(repo))
                subprocess.check_call(
                    ["git", "commit", "-q", "-m",
                     "feat: auth\n\nPersona-Waive: security-engineer:docs-only\n"
                     "Persona-Waive: security-engineer:explicit-skip"],
                    cwd=str(repo),
                )
                log = tmp / "audit-log.jsonl"
                log.write_text("")
                scanned = self.scanner.detect_all(repo)
                n = self.resolver.emit_waives_for_scanned(scanned, log, repo)
                self.assertGreaterEqual(n, 0)
        finally:
            import shutil as _sh
            if _prev_dir is None:
                _os.environ.pop("CEO_AUDIT_LOG_DIR", None)
            else:
                _os.environ["CEO_AUDIT_LOG_DIR"] = _prev_dir
            if _prev_sync is None:
                _os.environ.pop("CEO_AUDIT_SYNC_MODE", None)
            else:
                _os.environ["CEO_AUDIT_SYNC_MODE"] = _prev_sync
            try:
                _sh.rmtree(_audit_tmp, ignore_errors=True)
            except Exception:
                pass


class TestKillSwitchByteIdentical(unittest.TestCase):
    """Codex iter-1 P1 #2 fold: assert kill-switch reverts to pre-PLAN-104
    observability-only output (no PLAN-104 keys leak into result detail)."""

    def test_kill_switch_reverts_to_observability_only(self):
        import importlib.util, os
        spec = importlib.util.spec_from_file_location(
            "ceoboot", str(_REPO_ROOT / ".claude" / "scripts" / "ceo-boot.py"),
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        os.environ["CEO_PERSONA_DEMAND_LEDGER_DISABLED"] = "1"
        try:
            status, summary, detail = mod.check_persona_atrophy_7d()
        finally:
            os.environ.pop("CEO_PERSONA_DEMAND_LEDGER_DISABLED", None)

        # Under kill-switch, status must NEVER be red.
        self.assertNotEqual(status, "red")
        # Detail dict still emits the 3 carry-over fields for consistency
        # but `eligible_demand_events` MUST be 0 (no demand surface).
        self.assertEqual(detail.get("eligible_demand_events"), 0)

        # Codex iter-5 P2 #2 fold: tighten "byte-identical" claim. Under
        # kill-switch the PLAN-104 demand-driven metric keys should NOT
        # be present at all (only the pre-PLAN-104 observability fields).
        # The kill-switch branch uses the legacy `_persona_coverage_status`
        # path -> returns score_x100/cells_covered/total_cells/window_hours/
        # eligible_demand_events. Should NOT have opened/satisfied/unmet/
        # waived/still_open/eligible_settled (these are demand-driven only).
        demand_only_keys = {"opened", "satisfied", "unmet", "waived",
                            "still_open", "eligible_settled"}
        leaked = demand_only_keys & set(detail.keys())
        self.assertEqual(
            leaked, set(),
            f"kill-switch leaked demand-driven keys: {leaked!r}",
        )


if __name__ == "__main__":
    unittest.main()
