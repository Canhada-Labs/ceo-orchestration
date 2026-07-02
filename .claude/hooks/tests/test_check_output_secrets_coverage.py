"""In-process coverage uplift for check_output_secrets.py.

PLAN-112-FOLLOWUP-coverage-doctrine-reconcile (S157) / ADR-139 Tier-1.

The subprocess suite (test_check_output_secrets.py) covers the happy
paths; this module drives `decide()`, `main()` and the emit/derive
helpers in-process, forcing the fail-open `except` branches and the
first-fire / suppressed / kill-switch routes with surgical mocks.

Contract preserved: the hook ALWAYS continues (advisory) and NEVER
raises — every branch ends in `_emit_observe(...)`.
"""

from __future__ import annotations

import io
import json
import os
import sys
import unittest
from unittest import mock

from _lib.testing import TestEnvContext  # noqa: E402

import check_output_secrets as cos  # noqa: E402


class _RecordingEmitter:
    """Stand-in audit_emit module that records emit_generic calls."""

    def __init__(self, raise_exc=None):
        self.calls = []
        self._raise = raise_exc

    def emit_generic(self, **kwargs):
        if self._raise is not None:
            raise self._raise
        self.calls.append(kwargs)


class _Dedup:
    def __init__(self, suppressed=False, ttl=24, raise_exc=None):
        self._ret = (suppressed, ttl)
        self._raise = raise_exc

    def check_and_record(self, rph, csh, pid):
        if self._raise is not None:
            raise self._raise
        return self._ret


class _Payload:
    def __init__(self, tool_input=None):
        self.tool_input = tool_input


class OutputSecretsHelperTest(TestEnvContext):

    # --- pure helpers ----------------------------------------------------

    def test_emit_observe_variants(self):
        d = json.loads(cos._emit_observe())
        self.assertTrue(d["continue"])
        self.assertNotIn("systemMessage", d)
        d2 = json.loads(cos._emit_observe("hi"))
        self.assertEqual(d2["systemMessage"], "hi")

    def test_dedup_disabled_env(self):
        for val in ("0", "false", "OFF", "no"):
            with mock.patch.dict(os.environ, {"CEO_OUTPUT_SCAN_DEDUP": val}):
                self.assertTrue(cos._dedup_disabled())
        with mock.patch.dict(os.environ, {"CEO_OUTPUT_SCAN_DEDUP": "1"}):
            self.assertFalse(cos._dedup_disabled())

    def test_safe_pattern_id(self):
        self.assertEqual(cos._safe_pattern_id({"pattern_id": "LLM01_x"}), "LLM01_x")
        # No pattern_id -> derived from family short form.
        self.assertEqual(
            cos._safe_pattern_id({"family": "telemetry_beacon"}),
            "telemetry_unknown_vector",
        )
        self.assertEqual(cos._safe_pattern_id({}), "unknown_unknown_vector")

    def test_safe_family(self):
        self.assertEqual(cos._safe_family({"family": "LLM02"}), "LLM02")
        self.assertEqual(cos._safe_family({}), "unknown")
        self.assertEqual(cos._safe_family({"family": 123}), "unknown")

    # --- _emit_per_pattern_finding branches ------------------------------

    def _finding(self):
        return {"pattern_id": "LLM01_direct", "family": "LLM01"}

    def test_per_pattern_first_fire(self):
        emitter = _RecordingEmitter()
        cos._emit_per_pattern_finding(
            session_id="s", tool_name="Bash", finding=self._finding(),
            project="p", audit_emit_mod=emitter, repo_path_hash="r",
            command_sha="c", dedup_mod=_Dedup(suppressed=False),
        )
        self.assertEqual(len(emitter.calls), 1)
        self.assertEqual(emitter.calls[0]["action"], "output_scan_finding")

    def test_per_pattern_suppressed(self):
        emitter = _RecordingEmitter()
        cos._emit_per_pattern_finding(
            session_id="s", tool_name="Bash", finding=self._finding(),
            project="p", audit_emit_mod=emitter, repo_path_hash="r",
            command_sha="c", dedup_mod=_Dedup(suppressed=True, ttl=5),
        )
        self.assertEqual(emitter.calls[0]["action"], "output_scan_finding_suppressed")

    def test_per_pattern_dedup_raises_is_first_fire(self):
        emitter = _RecordingEmitter()
        cos._emit_per_pattern_finding(
            session_id="s", tool_name="Bash", finding=self._finding(),
            project="p", audit_emit_mod=emitter, repo_path_hash="r",
            command_sha="c", dedup_mod=_Dedup(raise_exc=RuntimeError("x")),
        )
        self.assertEqual(emitter.calls[0]["action"], "output_scan_finding")

    def test_per_pattern_dedup_disabled_skips_dedup(self):
        emitter = _RecordingEmitter()
        with mock.patch.dict(os.environ, {"CEO_OUTPUT_SCAN_DEDUP": "0"}):
            cos._emit_per_pattern_finding(
                session_id="s", tool_name="Bash", finding=self._finding(),
                project="p", audit_emit_mod=emitter, repo_path_hash="r",
                command_sha="c", dedup_mod=_Dedup(suppressed=True),
            )
        # dedup skipped -> treated as first-fire
        self.assertEqual(emitter.calls[0]["action"], "output_scan_finding")

    def test_per_pattern_no_emitter(self):
        # An object without emit_generic -> getattr returns None -> return.
        cos._emit_per_pattern_finding(
            session_id="s", tool_name="Bash", finding=self._finding(),
            project="p", audit_emit_mod=object(), repo_path_hash="r",
            command_sha="c", dedup_mod=None,
        )

    def test_per_pattern_emitter_raises_swallowed(self):
        emitter = _RecordingEmitter(raise_exc=RuntimeError("emit down"))
        cos._emit_per_pattern_finding(
            session_id="s", tool_name="Bash", finding=self._finding(),
            project="p", audit_emit_mod=emitter, repo_path_hash="r",
            command_sha="c", dedup_mod=_Dedup(suppressed=False),
        )

    # --- aggregate sidecar REMOVED (PLAN-152 economics-01) ----------------

    def test_aggregate_sidecar_helpers_removed(self):
        # PLAN-106's 24h deprecation window elapsed; PLAN-152 economics-01
        # removed the aggregate twin (it doubled HMAC appends + filelocks on
        # the all-tools PostToolUse hot path). Regression-pin the removal.
        self.assertFalse(hasattr(cos, "_emit_aggregate_sidecar"))
        self.assertFalse(hasattr(cos, "_emit_audit_finding"))
        self.assertFalse(hasattr(cos, "_DEPRECATION_WINDOW_HOURS"))

    def test_decide_emits_no_aggregate_twin(self):
        # PLAN-152 economics-01 Check: after a scan hit, ONLY per-pattern
        # output_scan_finding events emit — no aggregate twin. The aggregate
        # shape carried no pattern_id and total_findings=N; per-pattern
        # carries pattern_id and total_findings=1.
        from _lib import audit_emit as real_audit_emit
        calls = []
        with mock.patch.dict(os.environ, {"CEO_OUTPUT_SCAN_DEDUP": "0"}):
            with mock.patch.object(real_audit_emit, "emit_generic",
                                   lambda **kw: calls.append(kw)):
                out = cos.decide(
                    tool_response="normal‮reverse",
                    tool_name="Bash",
                    session_id="s",
                    project="p",
                )
        self.assertIn("continue", json.loads(out))
        self.assertTrue(calls, "expected at least one per-pattern emit")
        for c in calls:
            self.assertEqual(c["action"], "output_scan_finding")
            self.assertEqual(c["total_findings"], 1)
            self.assertIn("pattern_id", c)

    # --- _derive_command_sha branches ------------------------------------

    def test_derive_command_sha_str_input(self):
        sha = cos._derive_command_sha(
            tool_name="Bash", raw_response="resp",
            parsed_payload=_Payload(tool_input="ls -la"))
        self.assertEqual(len(sha), 64)

    def test_derive_command_sha_dict_input(self):
        sha = cos._derive_command_sha(
            tool_name="Bash", raw_response="resp",
            parsed_payload=_Payload(tool_input={"cmd": "ls"}))
        self.assertEqual(len(sha), 64)

    def test_derive_command_sha_fallback_str_response(self):
        sha = cos._derive_command_sha(
            tool_name="Bash", raw_response="raw text",
            parsed_payload=_Payload(tool_input=None))
        self.assertEqual(len(sha), 64)

    def test_derive_command_sha_fallback_nonstr_response(self):
        sha = cos._derive_command_sha(
            tool_name="Bash", raw_response={"k": "v"},
            parsed_payload=_Payload(tool_input=None))
        self.assertEqual(len(sha), 64)


class OutputSecretsDecideTest(TestEnvContext):

    def _decide(self, scan_result, **kw):
        with mock.patch("_lib.output_scan.scan", return_value=scan_result):
            return cos.decide(
                tool_response=kw.get("tool_response", "x"),
                tool_name=kw.get("tool_name", "Bash"),
                session_id=kw.get("session_id", "s"),
                project=str(self.project_dir),
                parsed_payload=kw.get("parsed_payload"),
            )

    def test_decide_output_scan_import_fail(self):
        with mock.patch.dict(sys.modules, {"_lib.output_scan": None}):
            out = cos.decide(tool_response="x", tool_name="Bash",
                             session_id="s", project="p")
        self.assertTrue(json.loads(out)["continue"])

    def test_decide_scan_raises(self):
        with mock.patch("_lib.output_scan.scan", side_effect=RuntimeError("x")):
            out = cos.decide(tool_response="x", tool_name="Bash",
                             session_id="s", project="p")
        self.assertTrue(json.loads(out)["continue"])

    def test_decide_zero_findings(self):
        out = self._decide({"total_findings": 0})
        d = json.loads(out)
        self.assertTrue(d["continue"])
        self.assertNotIn("systemMessage", d)

    def test_decide_findings_not_list(self):
        out = self._decide({"total_findings": 2, "findings": "not-a-list",
                            "family_counts": {"LLM01": 2}})
        self.assertIn("systemMessage", json.loads(out))

    def test_decide_with_findings_emits_and_messages(self):
        out = self._decide({
            "total_findings": 2,
            "findings": [
                {"pattern_id": "LLM01_a", "family": "LLM01"},
                "not-a-dict",  # exercises the isinstance continue
            ],
            "family_counts": {"LLM01": 2},
        }, parsed_payload=_Payload(tool_input="ls"))
        self.assertIn("systemMessage", json.loads(out))

    def test_decide_audit_emit_unavailable(self):
        # audit_emit import yields None -> skip emit, still messages.
        with mock.patch.dict(sys.modules, {"_lib.audit_emit": None}):
            out = self._decide({
                "total_findings": 1,
                "findings": [{"pattern_id": "p", "family": "LLM01"}],
                "family_counts": {"LLM01": 1},
            })
        self.assertIn("systemMessage", json.loads(out))

    def test_decide_rph_derive_raises(self):
        with mock.patch("_lib.output_scan_dedup.derive_repo_path_hash_from_env",
                        side_effect=RuntimeError("x")):
            out = self._decide({
                "total_findings": 1,
                "findings": [{"pattern_id": "p", "family": "LLM01"}],
                "family_counts": {"LLM01": 1},
            }, parsed_payload=_Payload(tool_input="ls"))
        self.assertIn("systemMessage", json.loads(out))


class OutputSecretsMainTest(TestEnvContext):

    def _run_main(self, payload):
        data = json.dumps(payload) if isinstance(payload, (dict, list)) else str(payload)
        old_in, old_out = sys.stdin, sys.stdout
        sys.stdin = io.StringIO(data)
        sys.stdout = io.StringIO()
        try:
            rc = cos.main()
            out = sys.stdout.getvalue()
        finally:
            sys.stdin, sys.stdout = old_in, old_out
        return rc, json.loads(out)

    def test_main_payload_import_fail(self):
        with mock.patch.dict(sys.modules, {"_lib.payload": None}):
            rc, out = self._run_main({"tool_name": "Bash"})
        self.assertEqual(rc, 0)
        self.assertTrue(out["continue"])

    def test_main_parse_raises(self):
        with mock.patch("_lib.payload.parse_stdin", side_effect=RuntimeError("x")):
            rc, out = self._run_main({"tool_name": "Bash"})
        self.assertEqual(rc, 0)
        self.assertTrue(out["continue"])

    def test_main_clean_output(self):
        rc, out = self._run_main(
            {"tool_name": "Bash", "tool_response": "ordinary output"})
        self.assertEqual(rc, 0)
        self.assertTrue(out["continue"])

    def test_main_dict_response(self):
        rc, out = self._run_main(
            {"tool_name": "Read", "tool_response": {"content": "hi"}})
        self.assertEqual(rc, 0)
        self.assertTrue(out["continue"])

    def test_main_none_response(self):
        rc, out = self._run_main({"tool_name": "Bash"})
        self.assertEqual(rc, 0)
        self.assertTrue(out["continue"])

    def test_main_decide_raises(self):
        with mock.patch("check_output_secrets.decide", side_effect=RuntimeError("x")):
            rc, out = self._run_main(
                {"tool_name": "Bash", "tool_response": "x"})
        self.assertEqual(rc, 0)
        self.assertTrue(out["continue"])


if __name__ == "__main__":
    unittest.main()
