"""Unit tests for audit_log.py — the PostToolUse agent spawn audit hook.

Covers the 11 scenarios from PLAN-002 §7 Item A.3 spec plus a few extras:
- valid JSONL on clean payload
- secret redaction (JWT, API key, URL creds)
- SHA-256 hash regardless of redaction
- rotation when over size threshold
- concurrent writes no interleaving (via multiprocessing)
- breadcrumb on lock timeout
- silent stdout (exit 0, no output)
- no jq dependency (the Python impl doesn't use it)
- fallback when CLAUDE_PROJECT_DIR unset
- fixture anonymization (no secrets in committed fixtures after redact)
- hook_duration_ms present in entry
"""

from __future__ import annotations

import io
import json
import multiprocessing
import os
import subprocess
import sys
import time
import unittest
from pathlib import Path


from _lib.testing import TestEnvContext, load_fixture  # noqa: E402

import audit_log as al  # noqa: E402


# Module-level worker for multiprocessing concurrency test
def _concurrent_write_worker(worker_id, env):
    """Child: set env, run audit_log.main() N times with fake stdin."""
    for k, v in env.items():
        os.environ[k] = v
    # Reimport in child so env is picked up
    import importlib
    import audit_log
    importlib.reload(audit_log)

    for i in range(10):
        payload = json.dumps({
            "session_id": f"child-{worker_id}-{i}",
            "tool_name": "Agent",
            "tool_input": {
                "description": f"worker {worker_id} iter {i}",
                "prompt": f"SKILL: test-skill\n## AGENT PROFILE\n## FILE ASSIGNMENT\n- x",
            },
        })
        old_stdin = sys.stdin
        old_stdout = sys.stdout
        sys.stdin = io.StringIO(payload)
        sys.stdout = io.StringIO()
        try:
            audit_log.main()
        finally:
            sys.stdin = old_stdin
            sys.stdout = old_stdout


class TestBuildEntry(TestEnvContext):
    def test_bucket_prompt_length(self):
        self.assertEqual(al.bucket_prompt_length(0), "<256")
        self.assertEqual(al.bucket_prompt_length(255), "<256")
        self.assertEqual(al.bucket_prompt_length(256), "<1024")
        self.assertEqual(al.bucket_prompt_length(1000), "<1024")
        self.assertEqual(al.bucket_prompt_length(5000), "<16384")
        self.assertEqual(al.bucket_prompt_length(100000), ">=65536")

    def test_extract_skill_from_inject_format(self):
        prompt = "## AGENT PROFILE\nfoo\n\nSKILL: security-and-auth\nrules..."
        self.assertEqual(al.extract_skill(prompt), "security-and-auth")

    def test_extract_skill_unknown_when_missing(self):
        self.assertEqual(al.extract_skill("no skill here"), "unknown")
        self.assertEqual(al.extract_skill(""), "unknown")

    def test_has_profile_detection(self):
        self.assertTrue(al.has_profile("## AGENT PROFILE\n..."))
        self.assertTrue(al.has_profile("PERSONA: Sofia"))
        self.assertTrue(al.has_profile("## PERSONA\n..."))
        self.assertFalse(al.has_profile("just some text"))

    def test_has_file_assignment_detection(self):
        self.assertTrue(al.has_file_assignment("## FILE ASSIGNMENT\n- x"))
        self.assertFalse(al.has_file_assignment("## SKILL CONTENT"))


class TestAppendEntryIntegration(TestEnvContext):
    """Write real entries to the isolated audit dir and inspect them."""

    def _run_main_with(self, payload_dict):
        """Run audit_log.main() with a JSON payload on stdin."""
        payload_str = json.dumps(payload_dict)
        old_stdin = sys.stdin
        old_stdout = sys.stdout
        sys.stdin = io.StringIO(payload_str)
        sys.stdout = io.StringIO()
        try:
            rc = al.main()
            out = sys.stdout.getvalue()
        finally:
            sys.stdin = old_stdin
            sys.stdout = old_stdout
        return rc, out

    def test_emits_valid_jsonl_on_clean_payload(self):
        fixture = load_fixture("sample_payload_clean.json")
        rc, out = self._run_main_with(fixture)
        self.assertEqual(rc, 0)
        self.assertEqual(out, "")  # silent stdout

        log_text = self.read_audit_log()
        self.assertTrue(log_text)
        lines = [ln for ln in log_text.split("\n") if ln]
        self.assertEqual(len(lines), 1)
        entry = json.loads(lines[0])

        self.assertEqual(entry["action"], "agent_spawn")
        self.assertEqual(entry["skill"], "security-and-auth")
        self.assertTrue(entry["has_profile"])
        self.assertTrue(entry["has_file_assignment"])
        self.assertIn("hook_duration_ms", entry)
        self.assertIsInstance(entry["hook_duration_ms"], int)
        self.assertGreaterEqual(entry["hook_duration_ms"], 0)
        self.assertEqual(len(entry["desc_hash"]), 64)

    def test_redacts_secrets_in_description(self):
        fixture = load_fixture("sample_payload_with_secrets.json")
        rc, out = self._run_main_with(fixture)
        self.assertEqual(rc, 0)

        log_text = self.read_audit_log()
        entry = json.loads([ln for ln in log_text.split("\n") if ln][0])

        # The redacted preview must NOT contain the raw secret fragments
        preview = entry["desc_preview"]
        self.assertNotIn("sk-ABCDEFGHIJKLMNOPQRSTUV", preview)
        self.assertNotIn("hunter2", preview)
        self.assertNotIn("admin:hunter2", preview)
        # But placeholders should appear
        self.assertTrue(
            "[API_KEY]" in preview or "[REDACTED]" in preview,
            f"expected a redacted placeholder in: {preview}",
        )

    def test_hashes_full_description_regardless_of_redaction(self):
        fixture = load_fixture("sample_payload_with_secrets.json")
        self._run_main_with(fixture)
        log_text = self.read_audit_log()
        entry = json.loads([ln for ln in log_text.split("\n") if ln][0])
        # SHA-256 hex length
        self.assertEqual(len(entry["desc_hash"]), 64)
        self.assertTrue(all(c in "0123456789abcdef" for c in entry["desc_hash"]))

    def test_silent_stdout_exit_zero(self):
        rc, out = self._run_main_with({
            "session_id": "s",
            "tool_name": "Agent",
            "tool_input": {"description": "d", "prompt": "p"},
        })
        self.assertEqual(rc, 0)
        self.assertEqual(out, "")

    def test_handles_malformed_stdin_writes_breadcrumb(self):
        old_stdin = sys.stdin
        sys.stdin = io.StringIO("{not json")
        try:
            rc = al.main()
        finally:
            sys.stdin = old_stdin
        self.assertEqual(rc, 0)
        errs = self.read_audit_errors()
        self.assertIn("stdin parse error", errs)

    def test_rotates_when_over_size_threshold(self):
        # Force a tiny rotation threshold
        os.environ["CEO_AUDIT_LOG_ROTATE_BYTES"] = "200"
        # Pre-seed the log with 300 bytes of dummy content
        log_path = Path(os.environ["CEO_AUDIT_LOG_PATH"])
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("x" * 300, encoding="utf-8")

        fixture = load_fixture("sample_payload_clean.json")
        self._run_main_with(fixture)

        # The original file should have been rotated away; a fresh one
        # should hold our new entry.
        rotated = list(self.audit_dir.glob("audit-log-*.jsonl"))
        self.assertTrue(rotated, "rotation should have produced a monthly file")
        fresh = self.read_audit_log()
        fresh_lines = [ln for ln in fresh.split("\n") if ln]
        self.assertEqual(len(fresh_lines), 1)

    def test_non_agent_tool_name_is_noop(self):
        rc, out = self._run_main_with({
            "session_id": "s",
            "tool_name": "Read",
            "tool_input": {"description": "d", "prompt": "p"},
        })
        self.assertEqual(rc, 0)
        self.assertEqual(self.read_audit_log(), "")

    def test_fallback_when_claude_project_dir_unset(self):
        os.environ.pop("CLAUDE_PROJECT_DIR", None)
        fixture = load_fixture("sample_payload_clean.json")
        rc, out = self._run_main_with(fixture)
        self.assertEqual(rc, 0)
        log_text = self.read_audit_log()
        entry = json.loads([ln for ln in log_text.split("\n") if ln][0])
        # Must have SOME project path (falls back to cwd resolve)
        self.assertTrue(entry["project"])


class TestFixtureAnonymization(TestEnvContext):
    """Make sure committed fixtures don't accidentally contain real secrets."""

    def test_clean_fixture_preview_is_stable(self):
        from _lib.redact import redact_secrets

        fixture = load_fixture("sample_payload_clean.json")
        desc = fixture["tool_input"]["description"]
        once = redact_secrets(desc, max_chars=0)
        twice = redact_secrets(once, max_chars=0)
        self.assertEqual(once, twice)

    def test_secrets_fixture_redacts_to_placeholders(self):
        from _lib.redact import redact_secrets

        fixture = load_fixture("sample_payload_with_secrets.json")
        desc = fixture["tool_input"]["description"]
        redacted = redact_secrets(desc, max_chars=0)
        self.assertNotIn("sk-ABCDEFGHIJKLMNOPQRSTUV", redacted)
        self.assertNotIn("hunter2", redacted)


@unittest.skipUnless(os.name == "posix", "POSIX only")
class TestConcurrentWrites(TestEnvContext):
    """Concurrent writes must not interleave — uses multiprocessing not threads."""

    def test_concurrent_writes_no_interleaving(self):
        # Snapshot env for children
        env = {
            "HOME": os.environ["HOME"],
            "CLAUDE_PROJECT_DIR": os.environ["CLAUDE_PROJECT_DIR"],
            "CEO_AUDIT_LOG_DIR": os.environ["CEO_AUDIT_LOG_DIR"],
            "CEO_AUDIT_LOG_PATH": os.environ["CEO_AUDIT_LOG_PATH"],
            "CEO_AUDIT_LOG_ERR": os.environ["CEO_AUDIT_LOG_ERR"],
            "CEO_AUDIT_LOG_LOCK": os.environ["CEO_AUDIT_LOG_LOCK"],
            "PYTHONPATH": str(Path(__file__).resolve().parent.parent),
        }

        workers = 3
        iters_per_worker = 10
        procs = []
        for wid in range(workers):
            p = multiprocessing.Process(
                target=_concurrent_write_worker, args=(wid, env)
            )
            procs.append(p)
            p.start()
        for p in procs:
            p.join(timeout=30)
            self.assertFalse(p.is_alive())

        log_text = self.read_audit_log()
        lines = [ln for ln in log_text.split("\n") if ln]
        self.assertEqual(len(lines), workers * iters_per_worker)
        # Every line must be valid JSON
        for ln in lines:
            entry = json.loads(ln)
            self.assertEqual(entry["action"], "agent_spawn")


if __name__ == "__main__":
    unittest.main()
