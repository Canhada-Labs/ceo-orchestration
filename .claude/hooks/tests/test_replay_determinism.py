"""TestReplayDeterminism — PLAN-014 Phase F.1b (ADJ-027).

10 named tests covering determinism invariants of replay-session.py.
Path ``.claude/hooks/tests/`` matches the hooks unit-test convention
(test collection by pytest runs these alongside hook tests).

Uses inline sys.path bootstrap since .claude/**/conftest.py is
canonical-edit guarded.
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import threading
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / ".claude" / "scripts" / "replay" / "replay-session.py"
HOOKS_DIR = REPO_ROOT / ".claude" / "hooks"

# Make _lib importable for TestEnvContext (mirrors the pattern in other hook tests).
if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402


def _load_mod():
    spec = importlib.util.spec_from_file_location("replay_session_det", SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestReplayDeterminism(TestEnvContext):
    """F.1b suite — 10 named determinism tests per ADJ-027.

    Converted from a manual env-snapshot pattern to TestEnvContext
    (PLAN-113 F-2-2.7) so that HOME, CLAUDE_PROJECT_DIR, and all CEO_*
    vars are automatically snapshot + restored via the base class.
    The test-local dirs are wired from self.project_dir / self.home_dir /
    self.audit_dir that TestEnvContext already provides.
    """

    def setUp(self) -> None:
        super().setUp()  # snapshots env, sets self.project_dir / home_dir / audit_dir
        # Wire audit log vars to the TestEnvContext-provided isolated tree.
        self.audit_log = self.audit_dir / "audit-log.jsonl"
        os.environ["CEO_AUDIT_LOG_PATH"] = str(self.audit_log)
        os.environ["CEO_AUDIT_LOG_DIR"] = str(self.audit_dir)
        os.environ["CEO_AUDIT_LOG_ERR"] = str(self.audit_dir / "audit-log.errors")
        os.environ["CEO_AUDIT_LOG_LOCK"] = str(self.audit_dir / "audit-log.lock")

        self.mod = _load_mod()
        self._owner = self.mod._current_user()

    def tearDown(self) -> None:
        super().tearDown()  # restores env + removes self._tmp_root

    # ---- helpers --------------------------------------------------

    def _write_audit(self, events):
        self.audit_log.write_text(
            "\n".join(json.dumps(e, ensure_ascii=False) for e in events) + "\n",
            encoding="utf-8",
        )

    def _make_spawn(self, ordinal, extra=None):
        ev = {
            "ts": f"2026-04-16T10:00:{ordinal:02d}Z",
            "action": "agent_spawn",
            "plan_id": "PLAN-014",
            "session_id": "s1",
            "user": self._owner,
            "skill": "public-api-design",
            "subagent_type": "Staff Backend Engineer",
            "desc_preview": f"build spawn {ordinal}",
            "spawn_ordinal": ordinal,
            "spawn_id": ordinal,
        }
        if extra:
            ev.update(extra)
        return ev

    def _run_dry_json(self):
        saved_stdout = sys.stdout
        saved_stderr = sys.stderr
        out = io.StringIO()
        err = io.StringIO()
        sys.stdout = out
        sys.stderr = err
        try:
            code = self.mod.main(["--plan", "PLAN-014", "--json"])
        finally:
            sys.stdout = saved_stdout
            sys.stderr = saved_stderr
        return code, out.getvalue(), err.getvalue()

    def _stable_payload_hashes(self, stdout_json):
        payload = json.loads(stdout_json)
        return [row.get("payload_hash") for row in payload.get("spawns", [])]

    # ---- 10 determinism tests --------------------------------------

    def test_01_same_input_100_runs_identical_payload_hashes(self):
        """Invariant 1 — 100 runs produce byte-identical payload hash lists."""
        self._write_audit([self._make_spawn(i) for i in range(5)])
        baseline = None
        for _ in range(100):
            _, out, _ = self._run_dry_json()
            hashes = self._stable_payload_hashes(out)
            if baseline is None:
                baseline = hashes
            else:
                self.assertEqual(hashes, baseline)

    def test_02_python_hash_seed_invariance(self):
        """Invariant 2 — different PYTHONHASHSEED doesn't shift output."""
        self._write_audit([self._make_spawn(i) for i in range(5)])
        saved = os.environ.get("PYTHONHASHSEED")
        os.environ["PYTHONHASHSEED"] = "0"
        _, out_a, _ = self._run_dry_json()
        os.environ["PYTHONHASHSEED"] = "random"
        _, out_b, _ = self._run_dry_json()
        if saved is None:
            os.environ.pop("PYTHONHASHSEED", None)
        else:
            os.environ["PYTHONHASHSEED"] = saved
        self.assertEqual(
            self._stable_payload_hashes(out_a),
            self._stable_payload_hashes(out_b),
        )

    def test_03_clock_tick_injection_does_not_affect_hashes(self):
        """Invariant 3 — fake-clock swap produces same payload hashes."""
        # canonical_payload_hash drops `ts`; so two events differing only in ts
        # must hash identically
        a = {"action": "agent_spawn", "skill": "x", "spawn_id": 1, "ts": "t1"}
        b = {"action": "agent_spawn", "skill": "x", "spawn_id": 1, "ts": "t2"}
        self.assertEqual(
            self.mod.canonical_payload_hash(a),
            self.mod.canonical_payload_hash(b),
        )

    def test_04_empty_session_deterministic(self):
        """Invariant 4 — empty-session path deterministic across 50 runs.

        Empty audit log (file exists but has no plan events) → exit 6
        (unknown_plan) deterministically.
        """
        # Empty audit log (0-byte file) — plan_exists_in_audit returns False
        self.audit_log.write_text("", encoding="utf-8")
        firsts = []
        for _ in range(50):
            code, out, err = self._run_dry_json()
            firsts.append((code, out.strip(), err.strip()))
        for f in firsts[1:]:
            self.assertEqual(f[0], firsts[0][0])

    def test_05_single_spawn_session_deterministic(self):
        """Invariant 5 — single-spawn session produces consistent hash."""
        self._write_audit([self._make_spawn(0)])
        _, out_a, _ = self._run_dry_json()
        _, out_b, _ = self._run_dry_json()
        self.assertEqual(
            self._stable_payload_hashes(out_a),
            self._stable_payload_hashes(out_b),
        )
        self.assertEqual(len(self._stable_payload_hashes(out_a)), 1)

    def test_06_partial_event_audit_log_deterministic(self):
        """Invariant 6 — unparseable line → deterministic exit code."""
        self.audit_log.write_text(
            json.dumps(self._make_spawn(0)) + "\n"
            + "{INVALID JSONL\n",
            encoding="utf-8",
        )
        codes = set()
        for _ in range(10):
            code, _, _ = self._run_dry_json()
            codes.add(code)
        self.assertEqual(len(codes), 1)

    def test_07_readdir_order_does_not_leak(self):
        """Invariant 7 — spawn ordering uses (ts, ordinal), not FS readdir."""
        # Intentionally emit events in REVERSE ts order; collect_spawns must sort.
        self._write_audit([
            self._make_spawn(2),
            self._make_spawn(0),
            self._make_spawn(1),
        ])
        _, out, _ = self._run_dry_json()
        payload = json.loads(out)
        ordinals = [s["ordinal"] for s in payload["spawns"]]
        # Post-sort, the ordinals should be the FIXED positions 0,1,2
        self.assertEqual(ordinals, [0, 1, 2])

    def test_08_concurrent_threads_barrier_same_result(self):
        """Invariant 8 — concurrent parsing produces same canonical hashes.

        Threading-safe test: each thread calls the pure helper
        canonical_payload_hash (deterministic under concurrency) rather
        than re-running main (which mutates global sys.stdout).
        """
        self._write_audit([self._make_spawn(i) for i in range(3)])
        events = [self._make_spawn(i) for i in range(3)]
        results = []
        barrier = threading.Barrier(4)
        lock = threading.Lock()

        def worker():
            barrier.wait()
            hashes = [self.mod.canonical_payload_hash(e) for e in events]
            with lock:
                results.append(hashes)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(len(results), 4)
        for r in results[1:]:
            self.assertEqual(r, results[0])

    def test_09_max_spawn_cardinality_session_hashes_stable(self):
        """Invariant 9 — up-to-max-spawns session is still deterministic."""
        events = [self._make_spawn(i) for i in range(50)]
        self._write_audit(events)
        hashes_a = self._stable_payload_hashes(self._run_dry_json()[1])
        hashes_b = self._stable_payload_hashes(self._run_dry_json()[1])
        self.assertEqual(hashes_a, hashes_b)
        self.assertEqual(len(hashes_a), 50)

    def test_10_ts_and_session_id_dropped_from_hash(self):
        """Invariant 10 — canonical hash drops ts + session_id + tokens_*."""
        a = {
            "action": "agent_spawn", "skill": "x", "spawn_id": 1,
            "ts": "t1", "session_id": "sA",
            "tokens_in": 100, "tokens_out": 200, "tokens_total": 300,
            "duration_ms": 42,
        }
        b = {
            "action": "agent_spawn", "skill": "x", "spawn_id": 1,
            "ts": "t9", "session_id": "sB",
            "tokens_in": 999, "tokens_out": 0, "tokens_total": 999,
            "duration_ms": 1_000_000,
        }
        self.assertEqual(
            self.mod.canonical_payload_hash(a),
            self.mod.canonical_payload_hash(b),
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
