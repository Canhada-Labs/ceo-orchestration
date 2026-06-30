"""PLAN-023 Phase B — audit-verify-chain.py CLI tests.

Covers exit-code contract:
- 0 intact / 1 tamper / 2 key missing / 3 malformed / 4 perm.

Covers semantics:
- Chain with 3 entries verifies clean.
- Bit-flip on entry 2 reports tamper at line 2.
- Deletion of entry 2 is detected (line 3's prev_hmac no longer matches).
- Transition-entry rule: hmac-less entry after hmac-bearing = tamper.
- Pre-v2.9 zone (all entries lack hmac) is tolerated → exit 0.
- JSON output format.
- --key-file override works.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent.parent.parent
_HOOKS = _REPO / ".claude" / "hooks"
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))

from _lib import audit_hmac  # noqa: E402
from _lib.audit_hmac import (  # noqa: E402
    GENESIS_PREV,
    compute_entry_hmac,
    hex_digest,
)

_CLI = _REPO / ".claude" / "scripts" / "audit-verify-chain.py"


def _build_chain(key: bytes, entries):
    """Return newline-joined JSON lines + list of raw hmac bytes."""
    prev = GENESIS_PREV
    lines = []
    digests = []
    for e in entries:
        h = compute_entry_hmac(key, prev, e)
        full = dict(e)
        full["hmac"] = hex_digest(h)
        lines.append(json.dumps(full, sort_keys=True, separators=(",", ":")))
        digests.append(h)
        prev = h
    return "\n".join(lines) + "\n", digests


class AuditVerifyChainCliTest(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="plan-023-cli-")
        self.tmp = Path(self._tmp.name)
        self.log_path = self.tmp / "audit-log.jsonl"
        self.key_path = self.tmp / "audit-key"
        self.key_path.write_bytes(b"\x42" * 32)
        os.chmod(self.key_path, 0o600)
        self.key = self.key_path.read_bytes()

    def tearDown(self):
        self._tmp.cleanup()

    def _run(self, *extra_args, stdin_bytes=None):
        cmd = [
            sys.executable,
            str(_CLI),
            "--log-file", str(self.log_path),
            "--key-file", str(self.key_path),
        ]
        cmd.extend(extra_args)
        return subprocess.run(
            cmd,
            capture_output=True,
            input=stdin_bytes,
            text=stdin_bytes is None or isinstance(stdin_bytes, str),
        )

    def test_empty_log_exits_0(self):
        self.log_path.write_text("")
        r = self._run()
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_intact_chain_exits_0(self):
        entries = [{"action": "a", "n": 1}, {"action": "a", "n": 2},
                   {"action": "a", "n": 3}]
        content, _ = _build_chain(self.key, entries)
        self.log_path.write_text(content)
        r = self._run()
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_intact_chain_verbose_prints_summary(self):
        entries = [{"a": 1}, {"a": 2}]
        content, _ = _build_chain(self.key, entries)
        self.log_path.write_text(content)
        r = self._run("--verbose")
        self.assertEqual(r.returncode, 0)
        self.assertIn("OK: chain intact", r.stderr)
        self.assertIn("verified=2", r.stderr)

    def test_bit_flip_at_entry_2_exits_1(self):
        entries = [{"a": 1}, {"a": 2}, {"a": 3}]
        content, _ = _build_chain(self.key, entries)
        lines = content.strip().split("\n")
        # Flip the "a" value in line 2 but keep its hmac recorded.
        parsed = json.loads(lines[1])
        parsed["a"] = 99
        lines[1] = json.dumps(parsed, sort_keys=True, separators=(",", ":"))
        self.log_path.write_text("\n".join(lines) + "\n")
        r = self._run()
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("line 2", r.stderr)

    def test_tamper_json_output(self):
        entries = [{"a": 1}, {"a": 2}]
        content, _ = _build_chain(self.key, entries)
        lines = content.strip().split("\n")
        parsed = json.loads(lines[1])
        parsed["a"] = 99
        lines[1] = json.dumps(parsed, sort_keys=True, separators=(",", ":"))
        self.log_path.write_text("\n".join(lines) + "\n")
        r = self._run("--json")
        self.assertEqual(r.returncode, 1)
        data = json.loads(r.stdout.strip())
        self.assertEqual(data["status"], "tamper")
        self.assertEqual(data["line"], 2)

    def test_malformed_json_line_exits_3(self):
        self.log_path.write_text("not json at all\n")
        r = self._run()
        self.assertEqual(r.returncode, 3, r.stderr)

    def test_missing_key_exits_2(self):
        self.log_path.write_text("")  # empty log
        # Point key-file at nonexistent path.
        cmd = [
            sys.executable,
            str(_CLI),
            "--log-file", str(self.log_path),
            "--key-file", str(self.tmp / "nonexistent-key"),
        ]
        r = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(r.returncode, 2, r.stderr)

    def test_wrong_key_perm_exits_4(self):
        self.log_path.write_text("")
        # Set key perms to 0644 and ensure exit 4.
        os.chmod(self.key_path, 0o644)
        r = self._run()
        self.assertEqual(r.returncode, 4, r.stderr)

    def test_pre_v29_zone_only_exits_0(self):
        # All lines lack hmac; considered pre-v2.9 and tolerated.
        self.log_path.write_text(
            json.dumps({"a": 1}) + "\n" +
            json.dumps({"a": 2}) + "\n"
        )
        r = self._run()
        self.assertEqual(r.returncode, 0, r.stderr)

    def test_transition_violation_exits_1(self):
        # entry 1 has hmac; entry 2 lacks hmac → transition violation.
        entries = [{"a": 1}]
        content, _ = _build_chain(self.key, entries)
        content += json.dumps({"a": 2}) + "\n"  # hmac-less after hmac
        self.log_path.write_text(content)
        r = self._run()
        self.assertEqual(r.returncode, 1, r.stderr)
        self.assertIn("transition_violation", r.stderr + r.stdout)

    def test_deletion_of_interior_entry_exits_1(self):
        # Build 3-entry chain then drop line 2.
        entries = [{"a": 1}, {"a": 2}, {"a": 3}]
        content, _ = _build_chain(self.key, entries)
        lines = content.strip().split("\n")
        del lines[1]  # drop entry 2
        self.log_path.write_text("\n".join(lines) + "\n")
        r = self._run()
        self.assertEqual(r.returncode, 1, r.stderr)


if __name__ == "__main__":
    unittest.main()
