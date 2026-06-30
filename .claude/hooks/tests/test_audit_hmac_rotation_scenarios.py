"""PLAN-045 F-07-06 — HMAC-chain rotation threat-model scenarios.

Covers three rotation-window scenarios flagged in PLAN-044 dim 07 audit:

1. **rotation-mid-chain preserves verifiability** — after rotation the
   new file's chain starts at genesis; verify-chain on EACH file
   independently returns intact.
2. **rotation-then-tampered-file-1 is detected** — mutating one entry
   in the pre-rotation file is caught by ``verify_chain`` when run
   on that file. (Per-file chain integrity is the guarantee.)
3. **rotation-then-delete-file-1 is undetected** — ADR-055 §Out-of-scope
   documented gap: per-file chain independence means the rotated-off
   file's HMAC anchor is not linked to the new file's genesis; an
   attacker with filesystem write can delete file-1 and the surviving
   file-2 still verifies clean.

The third case is a *negative* assertion: the test PROVES the gap
exists so a future cross-file anchor fix (see ADR-055 §Future work)
can tighten the invariant and break this test — the test becomes a
guardrail against re-regressing.

Python 3.9+, stdlib only. Uses TestEnvContext convention from
test_audit_hmac.py (temp dir + env scrub).
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

_HOOKS = Path(__file__).resolve().parent.parent

from _lib import audit_hmac  # noqa: E402
from _lib.audit_hmac import (  # noqa: E402
    GENESIS_PREV,
    compute_entry_hmac,
    get_or_create_key,
    hex_digest,
    reset_chain_on_rotation,
)


class _RotationTestBase(unittest.TestCase):
    """Share TemporaryDirectory + env isolation for rotation scenarios."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(prefix="plan-045-f0706-")
        self.tmp = Path(self._tmp.name)
        self._saved_env = {
            k: os.environ.get(k)
            for k in (
                "CEO_AUDIT_LOG_PATH",
                "CEO_AUDIT_KEY_PATH",
                "CEO_AUDIT_LAST_HMAC_PATH",
                "CEO_AUDIT_HMAC_DISABLE",
                "HOME",
                "CEO_PROJECT_STATE_DIR",
            )
        }
        os.environ["CEO_AUDIT_LOG_PATH"] = str(self.tmp / "audit-log.jsonl")
        os.environ["CEO_AUDIT_KEY_PATH"] = str(self.tmp / "audit-key")
        os.environ["CEO_AUDIT_LAST_HMAC_PATH"] = str(
            self.tmp / "audit-log.last-hmac"
        )
        os.environ.pop("CEO_AUDIT_HMAC_DISABLE", None)
        audit_hmac._reset_key_cache_for_test()
        self.key = get_or_create_key()

    def tearDown(self) -> None:
        audit_hmac._reset_key_cache_for_test()
        for k, v in self._saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self._tmp.cleanup()

    # ── Helpers ──

    def _append_chain(self, log_path: Path, entries, start_prev=GENESIS_PREV):
        """Append entries to log_path, chaining HMACs from start_prev.

        Returns the final HMAC bytes (last entry's hmac, raw).
        """
        prev = start_prev
        with log_path.open("a", encoding="utf-8") as fh:
            for entry in entries:
                payload = {k: v for k, v in entry.items() if k != "hmac"}
                h = compute_entry_hmac(self.key, prev, payload)
                entry_out = dict(payload)
                entry_out["hmac"] = hex_digest(h)
                fh.write(json.dumps(entry_out) + "\n")
                prev = h
        return prev

    def _run_verify(self, log_path: Path) -> int:
        """Invoke audit-verify-chain.py via direct import of its verify() fn.

        Returns the exit code. Uses a minimal (line_num, raw) generator
        mirroring the script's _iter_lines helper.
        """
        # Dynamic import of the verify() public function.
        import importlib.util
        script = (
            Path(__file__).resolve().parent.parent.parent
            / "scripts" / "audit-verify-chain.py"
        )
        spec = importlib.util.spec_from_file_location(
            "_avc_ext", str(script)
        )
        assert spec is not None and spec.loader is not None
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)  # type: ignore[attr-defined]

        def gen():
            with log_path.open("r", encoding="utf-8") as fh:
                for i, raw in enumerate(fh, start=1):
                    yield (i, raw)

        return mod.verify(
            gen(), self.key, since=1, json_output=True, verbose=False
        )


class TestRotationMidChainPreservesVerifiability(_RotationTestBase):
    """Scenario 1: rotation mid-chain leaves both files independently verifiable."""

    def test_post_rotation_both_files_verify_intact(self) -> None:
        file1 = self.tmp / "audit-log.jsonl.1"
        file2 = self.tmp / "audit-log.jsonl"

        entries_1 = [
            {"action": "agent_spawn", "session_id": "s1", "seq": 1,
             "ts": "2026-04-20T00:00:00Z", "event_schema": "v2.9"},
            {"action": "agent_spawn", "session_id": "s1", "seq": 2,
             "ts": "2026-04-20T00:00:01Z", "event_schema": "v2.9"},
            {"action": "session_end", "session_id": "s1", "seq": 3,
             "ts": "2026-04-20T00:00:02Z", "event_schema": "v2.9"},
        ]
        self._append_chain(file1, entries_1)

        # Simulate rotation: clear sidecar, new file starts from genesis.
        reset_chain_on_rotation()

        entries_2 = [
            {"action": "session_start", "session_id": "s2", "seq": 1,
             "ts": "2026-04-20T00:01:00Z", "event_schema": "v2.9"},
            {"action": "agent_spawn", "session_id": "s2", "seq": 2,
             "ts": "2026-04-20T00:01:01Z", "event_schema": "v2.9"},
        ]
        self._append_chain(file2, entries_2)

        # Per-file verification on each — both must return intact (exit 0).
        self.assertEqual(self._run_verify(file1), 0,
                         "file1 should verify intact after rotation")
        self.assertEqual(self._run_verify(file2), 0,
                         "file2 should verify intact as a new chain")


class TestRotationThenTamperedFile1IsDetected(_RotationTestBase):
    """Scenario 2: tampering with pre-rotation file is caught per-file."""

    def test_post_rotation_tamper_in_file1_breaks_chain(self) -> None:
        file1 = self.tmp / "audit-log.jsonl.1"
        entries = [
            {"action": "agent_spawn", "session_id": "s1", "seq": 1,
             "ts": "2026-04-20T00:00:00Z", "event_schema": "v2.9"},
            {"action": "agent_spawn", "session_id": "s1", "seq": 2,
             "ts": "2026-04-20T00:00:01Z", "event_schema": "v2.9"},
            {"action": "session_end", "session_id": "s1", "seq": 3,
             "ts": "2026-04-20T00:00:02Z", "event_schema": "v2.9"},
        ]
        self._append_chain(file1, entries)
        reset_chain_on_rotation()
        # New file2 is unrelated to the tamper scenario; skip.

        # Tamper: mutate entry #2's seq field WITHOUT updating its hmac.
        lines = file1.read_text(encoding="utf-8").splitlines()
        rec = json.loads(lines[1])
        rec["seq"] = 99  # tamper
        lines[1] = json.dumps(rec)
        file1.write_text("\n".join(lines) + "\n", encoding="utf-8")

        # verify-chain on file1 detects tamper (exit 1 = EXIT_TAMPER).
        self.assertEqual(self._run_verify(file1), 1,
                         "file1 tamper must be detected post-rotation")


class TestRotationThenDeleteFile1IsUndetected(_RotationTestBase):
    """Scenario 3: ADR-055 known gap — rotated-off file deletion is silent.

    This test intentionally PASSES today because per-file chain independence
    means there is no cross-file anchor linking file-2's genesis to file-1's
    tail HMAC. If a future cross-file anchor mitigation lands (ADR-055
    §Future work — external OTEL append-only sink OR a cross-file-manifest
    sidecar), this test should be updated or inverted.
    """

    def test_delete_file1_leaves_file2_verifying_clean(self) -> None:
        file1 = self.tmp / "audit-log.jsonl.1"
        file2 = self.tmp / "audit-log.jsonl"

        self._append_chain(file1, [
            {"action": "agent_spawn", "session_id": "s1", "seq": 1,
             "ts": "2026-04-20T00:00:00Z", "event_schema": "v2.9"},
            {"action": "session_end", "session_id": "s1", "seq": 2,
             "ts": "2026-04-20T00:00:01Z", "event_schema": "v2.9"},
        ])
        reset_chain_on_rotation()
        self._append_chain(file2, [
            {"action": "session_start", "session_id": "s2", "seq": 1,
             "ts": "2026-04-20T00:01:00Z", "event_schema": "v2.9"},
        ])

        # Attacker deletes file1 entirely after rotation.
        file1.unlink()

        # file2 still verifies clean — this is the documented gap.
        self.assertEqual(self._run_verify(file2), 0,
                         "ADR-055 gap: post-rotation file-1 deletion is "
                         "NOT detected by per-file chain verification. "
                         "A cross-file anchor (OTEL append-only sink or "
                         "manifest sidecar) would tighten this.")


if __name__ == "__main__":
    unittest.main()
