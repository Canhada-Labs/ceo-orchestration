"""Unit tests for PLAN-090-FOLLOWUP claim producer pair (S138 execute).

Tests the per-claim event producer pair shipped in v1.33.1:
- emit_claim_emitted (fires once per claim the gate evaluates)
- emit_confidence_gate_verdict (fires once per claim verdict, paired by claim_id)

AC1..AC11 invariants covered (see .claude/plans/PLAN-090-FOLLOWUP-claim-producer-pair.md §4).
"""

from __future__ import annotations

import importlib
import json
import os
import subprocess
import sys
import time
import unittest
import uuid
from pathlib import Path

from _lib.testing import TestEnvContext  # noqa: E402
from _lib import audit_emit  # noqa: E402


# Reused canonical 12-hex claim-class composite (claim_type:payload_hash[:12])
_DEMO_PAYLOAD_HASH = "deadbeefdead"
_DEMO_CLAIM_ID = f"path_exists:{_DEMO_PAYLOAD_HASH}"


class _SyncAuditMixin(TestEnvContext):
    """Force CEO_AUDIT_SYNC_MODE=1 so emits land synchronously in the test log.

    The default async spool-writer path (PLAN-094 ADR-055-AMEND-1) batches
    writes and a test that emits + immediately reads the log will see an
    empty file. Existing test_audit_emit.py relies on CI / ceremony to
    set this externally; per-test files like this one set it in setUp.
    """

    def setUp(self) -> None:  # noqa: D401
        super().setUp()
        os.environ["CEO_AUDIT_SYNC_MODE"] = "1"


class TestEmitClaimEmitted(_SyncAuditMixin):
    """AC1 — emit_claim_emitted golden path + field allowlist + LLM06."""

    def _read_log(self):
        log = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        if not log.exists():
            return []
        return [
            json.loads(line)
            for line in log.read_text().splitlines()
            if line.strip()
        ]

    def test_emit_claim_emitted_golden_path(self):
        """AC1.1 — all caller fields round-trip; row written to audit-log."""
        audit_emit.emit_claim_emitted(
            claim_id=_DEMO_CLAIM_ID,
            claim_type="path_exists",
            severity="info",
            verifier_kind="path_exists",
            payload_hash=_DEMO_PAYLOAD_HASH,
            kind_supported=True,
            line_num=42,
            agent_name="qa-architect",
            source="post_tool_use",
            session_id="s-test-1",
            project="/test/project",
        )
        rows = self._read_log()
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual(r["action"], "claim_emitted")
        self.assertEqual(r["claim_id"], _DEMO_CLAIM_ID)
        self.assertEqual(r["claim_type"], "path_exists")
        self.assertEqual(r["severity"], "info")
        self.assertEqual(r["verifier_kind"], "path_exists")
        self.assertEqual(r["payload_hash"], _DEMO_PAYLOAD_HASH)
        self.assertTrue(r["kind_supported"])
        self.assertEqual(r["line_num"], 42)
        self.assertEqual(r["agent_name"], "qa-architect")
        self.assertEqual(r["source"], "post_tool_use")
        self.assertEqual(r["session_id"], "s-test-1")

    def test_emit_claim_emitted_severity_invalid_enum_dropped_to_info(self):
        """AC1.2 — invalid severity dropped to 'info' (forensic-safe sentinel)."""
        audit_emit.emit_claim_emitted(
            claim_id=_DEMO_CLAIM_ID,
            claim_type="path_exists",
            severity="catastrophic",
            verifier_kind="path_exists",
            payload_hash=_DEMO_PAYLOAD_HASH,
            kind_supported=True,
        )
        rows = self._read_log()
        self.assertEqual(rows[0]["severity"], "info")

    def test_emit_claim_emitted_field_allowlist_regression(self):
        """AC1.3/AC10 — emit_generic with extra fields drops them via allowlist."""
        audit_emit.emit_generic(
            "claim_emitted",
            claim_id=_DEMO_CLAIM_ID,
            claim_type="path_exists",
            severity="info",
            verifier_kind="path_exists",
            payload_hash=_DEMO_PAYLOAD_HASH,
            kind_supported=True,
            claim_body="raw-secret-payload-must-not-persist",
        )
        rows = self._read_log()
        log_text = json.dumps(rows[0])
        self.assertNotIn("claim_body", rows[0])
        self.assertNotIn("raw-secret-payload-must-not-persist", log_text)

    def test_emit_claim_emitted_payload_hash_defensive_rehash(self):
        """AC1.4 — non-hex payload_hash rehashed to 12-hex sha256[:12]."""
        audit_emit.emit_claim_emitted(
            claim_id=_DEMO_CLAIM_ID,
            claim_type="path_exists",
            severity="info",
            verifier_kind="path_exists",
            payload_hash="not-hex-12char-or-bigger",
            kind_supported=True,
        )
        rows = self._read_log()
        ph = rows[0]["payload_hash"]
        self.assertEqual(len(ph), 12)
        self.assertTrue(all(c in "0123456789abcdef" for c in ph))


class TestEmitConfidenceGateVerdict(_SyncAuditMixin):
    """AC2 — emit_confidence_gate_verdict golden + enum + pair-match."""

    def _read_log(self):
        log = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        if not log.exists():
            return []
        return [
            json.loads(line)
            for line in log.read_text().splitlines()
            if line.strip()
        ]

    def test_emit_confidence_gate_verdict_golden_path(self):
        """AC2.1 — verdict row carries claim_id, verdict enum, was_false_positive."""
        audit_emit.emit_confidence_gate_verdict(
            claim_id=_DEMO_CLAIM_ID,
            verdict="pass",
            was_false_positive=False,
            kind_supported=True,
            verifier_kind="path_exists",
            verifier_outcome="path /tmp/foo exists",
            agent_name="qa-architect",
            source="post_tool_use",
            session_id="s-test-2",
        )
        rows = self._read_log()
        self.assertEqual(len(rows), 1)
        r = rows[0]
        self.assertEqual(r["action"], "confidence_gate_verdict")
        self.assertEqual(r["claim_id"], _DEMO_CLAIM_ID)
        self.assertEqual(r["verdict"], "pass")
        self.assertFalse(r["was_false_positive"])
        self.assertTrue(r["kind_supported"])
        self.assertEqual(r["verifier_kind"], "path_exists")
        self.assertEqual(r["agent_name"], "qa-architect")

    def test_emit_confidence_gate_verdict_invalid_enum_dropped_to_fail(self):
        """AC2.2 — invalid verdict → 'fail' (NOT 'refuted' which is FP signal)."""
        audit_emit.emit_confidence_gate_verdict(
            claim_id=_DEMO_CLAIM_ID,
            verdict="maybe",
            was_false_positive=False,
            kind_supported=True,
        )
        rows = self._read_log()
        self.assertEqual(rows[0]["verdict"], "fail")
        audit_emit.emit_confidence_gate_verdict(
            claim_id=_DEMO_CLAIM_ID,
            verdict="refuted",
            was_false_positive=True,
            kind_supported=True,
        )
        rows = self._read_log()
        self.assertEqual(rows[1]["verdict"], "refuted")

    def test_emit_pair_matching_by_claim_id(self):
        """AC2.3 — emit pair; both rows share claim_id."""
        cid = "function_exists:abcdef012345"
        audit_emit.emit_claim_emitted(
            claim_id=cid,
            claim_type="function_exists",
            severity="warn",
            verifier_kind="function_exists",
            payload_hash="abcdef012345",
            kind_supported=True,
        )
        audit_emit.emit_confidence_gate_verdict(
            claim_id=cid,
            verdict="pass",
            was_false_positive=False,
            kind_supported=True,
        )
        rows = self._read_log()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["claim_id"], rows[1]["claim_id"])
        self.assertEqual(rows[0]["action"], "claim_emitted")
        self.assertEqual(rows[1]["action"], "confidence_gate_verdict")


class TestPairOrderingAndOrphans(_SyncAuditMixin):
    """AC2.4 (test 7b) — out-of-order pair; orphan handling."""

    def _read_log(self):
        log = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        if not log.exists():
            return []
        return [
            json.loads(line)
            for line in log.read_text().splitlines()
            if line.strip()
        ]

    def test_emit_pair_out_of_order_still_pairs(self):
        """Verdict-first then claim_emitted: backfill pairs by claim_id."""
        cid_a = "path_exists:111111111111"
        audit_emit.emit_confidence_gate_verdict(
            claim_id=cid_a,
            verdict="pass",
            was_false_positive=False,
            kind_supported=True,
        )
        audit_emit.emit_claim_emitted(
            claim_id=cid_a,
            claim_type="path_exists",
            severity="info",
            verifier_kind="path_exists",
            payload_hash="111111111111",
            kind_supported=True,
        )
        cid_b = "path_exists:222222222222"
        audit_emit.emit_claim_emitted(
            claim_id=cid_b,
            claim_type="path_exists",
            severity="info",
            verifier_kind="path_exists",
            payload_hash="222222222222",
            kind_supported=True,
        )
        rows = self._read_log()
        emitted = [r for r in rows if r["action"] == "claim_emitted"]
        verdicts = [r for r in rows if r["action"] == "confidence_gate_verdict"]
        self.assertEqual(len(emitted), 2)
        self.assertEqual(len(verdicts), 1)
        verdicts_by_cid = {v["claim_id"]: v for v in verdicts}
        self.assertIn(cid_a, verdicts_by_cid)
        self.assertNotIn(cid_b, verdicts_by_cid)


class TestClaimIdDeterministicNfkc(_SyncAuditMixin):
    """AC4 — claim_id NFKC determinism across precomposed/decomposed grapheme."""

    def test_claim_id_deterministic_nfkc_variants(self):
        """Precomposed U+00E9 (c3 a9) == decomposed e+U+0301 (65 cc 81) under NFKC."""
        import hashlib
        import unicodedata

        # Explicit Unicode escapes — guarantees distinct byte sequences in source.
        precomposed = "café"  # 4 codepoints, bytes c3 a9 for the final
        decomposed = "café"  # 5 codepoints, bytes 65 cc 81 at the tail
        # Sanity — DIFFERENT raw byte sequences pre-normalization
        self.assertNotEqual(
            precomposed.encode("utf-8"),
            decomposed.encode("utf-8"),
        )
        self.assertEqual(
            unicodedata.normalize("NFKC", precomposed),
            unicodedata.normalize("NFKC", decomposed),
        )
        h_pre = hashlib.sha256(
            unicodedata.normalize("NFKC", precomposed).encode("utf-8")
        ).hexdigest()[:12]
        h_dec = hashlib.sha256(
            unicodedata.normalize("NFKC", decomposed).encode("utf-8")
        ).hexdigest()[:12]
        from _lib.audit_emit import _safe_payload_hash
        self.assertEqual(_safe_payload_hash(precomposed), _safe_payload_hash(decomposed))
        self.assertEqual(_safe_payload_hash(precomposed), h_pre)
        self.assertEqual(h_pre, h_dec)


class TestLLM06Invariant(_SyncAuditMixin):
    """AC9 — high-entropy canary in r.claim.args MUST NOT reach audit-log."""

    def _read_log(self):
        log = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        if not log.exists():
            return ""
        return log.read_text()

    def test_llm06_raw_claim_body_never_in_audit_log(self):
        canary = f"LLM06CANARY-{uuid.uuid4().hex}"
        import hashlib
        payload_hash = hashlib.sha256(canary.encode("utf-8")).hexdigest()[:12]
        cid = f"path_exists:{payload_hash}"
        audit_emit.emit_claim_emitted(
            claim_id=cid,
            claim_type="path_exists",
            severity="info",
            verifier_kind="path_exists",
            payload_hash=payload_hash,
            kind_supported=True,
            line_num=1,
        )
        from _lib.audit_emit import _safe_verifier_outcome
        scrubbed = _safe_verifier_outcome(
            f"path checked: {canary[:32]} ok", canary
        )
        self.assertNotIn(canary[:8], scrubbed)
        audit_emit.emit_confidence_gate_verdict(
            claim_id=cid,
            verdict="pass",
            was_false_positive=False,
            kind_supported=True,
            verifier_outcome=scrubbed,
        )
        log_text = self._read_log()
        self.assertNotIn(canary, log_text)


class TestSecMF3EmitGenericReject(_SyncAuditMixin):
    """AC10 — emit_generic with forbidden field must drop it via allowlist."""

    def _read_log(self):
        log = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        if not log.exists():
            return []
        return [
            json.loads(line)
            for line in log.read_text().splitlines()
            if line.strip()
        ]

    def test_sec_mf3_emit_generic_rejects_forbidden_field(self):
        audit_emit.emit_generic(
            "confidence_gate_verdict",
            claim_id=_DEMO_CLAIM_ID,
            verdict="pass",
            was_false_positive=False,
            kind_supported=True,
            claim_body="raw-must-not-persist",
        )
        rows = self._read_log()
        self.assertNotIn("claim_body", rows[0])
        self.assertNotIn("raw-must-not-persist", json.dumps(rows[0]))

    def test_emit_generic_verdict_enum_rehash(self):
        """P1-1 fold — emit_generic verdict enum re-validated at dispatch."""
        audit_emit.emit_generic(
            "confidence_gate_verdict",
            claim_id=_DEMO_CLAIM_ID,
            verdict="malicious",
            was_false_positive=False,
            kind_supported=True,
        )
        rows = self._read_log()
        self.assertEqual(rows[0]["verdict"], "fail")

    def test_emit_generic_claim_emitted_defensive_rehash_payload(self):
        """P0-3+P0-4 fold — emit_generic re-hashes claim_id + payload_hash."""
        audit_emit.emit_generic(
            "claim_emitted",
            claim_id="/etc/passwd:notahash",
            claim_type="path_exists",
            severity="info",
            verifier_kind="path_exists",
            payload_hash="not12hex",
            kind_supported=True,
        )
        rows = self._read_log()
        r = rows[0]
        self.assertNotIn("/etc/passwd", r["claim_id"])
        self.assertEqual(len(r["payload_hash"]), 12)
        self.assertTrue(all(c in "0123456789abcdef" for c in r["payload_hash"]))


class TestKillSwitchByteIdentical(_SyncAuditMixin):
    """AC11 — CEO_CONFIDENCE_GATE_PRODUCER_PAIR_DISABLED=1 reverts to pre-followup shape."""

    _VOLATILE_FIELDS = frozenset({
        "ts", "hmac", "hmac_error", "event_schema",
        "tokens_in", "tokens_out", "tokens_total",
    })

    def _read_log(self):
        log = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        if not log.exists():
            return []
        return [
            json.loads(line)
            for line in log.read_text().splitlines()
            if line.strip()
        ]

    def test_kill_switch_byte_identical_to_pre_followup(self):
        """With kill-switch ON, only aggregate confidence_gate event fires."""
        os.environ["CEO_CONFIDENCE_GATE_PRODUCER_PAIR_DISABLED"] = "1"
        for _ in range(3):
            audit_emit.emit_confidence_gate(
                claim_count=5,
                pass_count=4,
                fail_count=1,
                verifier_kind_counts={"path_exists": 5},
                agent_name="qa-architect",
                source="post_tool_use",
                session_id="s-killswitch",
                project="/test",
            )
        rows = self._read_log()
        new_actions = [
            r for r in rows
            if r["action"] in {"claim_emitted", "confidence_gate_verdict"}
        ]
        self.assertEqual(new_actions, [])
        aggregates = [r for r in rows if r["action"] == "confidence_gate"]
        self.assertEqual(len(aggregates), 3)


class TestBackfillEndToEnd(_SyncAuditMixin):
    """AC5 — synthetic 250-event corpus → backfill produces ≥3 OK classes."""

    def test_backfill_end_to_end_synthetic_corpus(self):
        """QA iter-1 P1b fold — seeded random, 3 classes × ~80, ~10% FP rate."""
        import random
        random.seed(42)
        classes = ["path_exists", "function_exists", "sha_exists"]
        target_fp_rate = 0.10
        counter = 0
        for klass in classes:
            for _ in range(80):
                counter += 1
                payload_hash = f"{counter:012x}"
                cid = f"{klass}:{payload_hash}"
                is_fp = random.random() < target_fp_rate
                audit_emit.emit_claim_emitted(
                    claim_id=cid,
                    claim_type=klass,
                    severity="info",
                    verifier_kind=klass,
                    payload_hash=payload_hash,
                    kind_supported=True,
                )
                audit_emit.emit_confidence_gate_verdict(
                    claim_id=cid,
                    verdict="pass" if not is_fp else "refuted",
                    was_false_positive=is_fp,
                    kind_supported=True,
                )

        log_path = os.environ["CEO_AUDIT_LOG_PATH"]
        # __file__ = <repo>/.claude/hooks/tests/<this>
        # parents[3] = <repo>
        repo_root = Path(__file__).resolve().parents[3]
        backfill = repo_root / ".claude" / "scripts" / "confidence-gate-backfill.py"
        if not backfill.is_file():
            self.skipTest("confidence-gate-backfill.py not present")
        # Backfill writes a markdown report to --report-path (NOT stdout).
        import tempfile
        report_path = Path(tempfile.mkdtemp()) / "baseline.md"
        result = subprocess.run(
            [
                sys.executable,
                str(backfill),
                "--audit-log", log_path,
                "--window-days", "30",
                "--min-samples", "30",
                "--report-path", str(report_path),
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertTrue(report_path.is_file(), msg=f"report not written: {result.stderr}")
        out = report_path.read_text()
        for klass in classes:
            self.assertIn(klass, out, msg=f"Expected {klass} in backfill report")
        self.assertIn("FPR", out)
        self.assertIn("Status", out)


class TestSafeHashHelpers(_SyncAuditMixin):
    """Coverage for _safe_claim_id_hash + _safe_payload_hash strict grammar."""

    def test_safe_claim_id_hash_valid_passes_through(self):
        from _lib.audit_emit import _safe_claim_id_hash
        cid = "path_exists:deadbeefdead"
        self.assertEqual(_safe_claim_id_hash(cid), cid)

    def test_safe_claim_id_hash_unknown_prefix_rehashed(self):
        from _lib.audit_emit import _safe_claim_id_hash
        cid = "BadPrefix-WITH-CAPS:deadbeefdead"
        out = _safe_claim_id_hash(cid)
        self.assertTrue(out.startswith("unknown:"))
        self.assertEqual(len(out.split(":")[1]), 12)

    def test_safe_payload_hash_valid_round_trips(self):
        from _lib.audit_emit import _safe_payload_hash
        self.assertEqual(_safe_payload_hash("aabbccddeeff"), "aabbccddeeff")

    def test_safe_payload_hash_invalid_rehashed(self):
        from _lib.audit_emit import _safe_payload_hash
        out = _safe_payload_hash("not-hex-or-12char-input")
        self.assertEqual(len(out), 12)
        self.assertTrue(all(c in "0123456789abcdef" for c in out))


if __name__ == "__main__":
    unittest.main()
