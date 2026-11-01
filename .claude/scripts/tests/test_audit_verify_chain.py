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


class StrictAgainstCounterContractFu144Test(unittest.TestCase):
    """PLAN-194-FOLLOWUP-v1-4-4-backlog, item 5 (FD-26) + Owner decision S363-4.

    Under --strict-against-counter the outcome is always one of the five documented
    rcs, with a named reason, one JSON object on stdout under --json and no traceback.
    Without the flag the CLI keeps the behaviour it had before the strict contract.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="fu144-strict-")
        self.tmp = Path(self._tmp.name)
        self.log_path = self.tmp / "audit-log.jsonl"
        self.key_path = self.tmp / "audit-key"
        self.counter_path = self.tmp / "audit-log.chain-length"
        self.key_path.write_bytes(b"\x42" * 32)
        os.chmod(self.key_path, 0o600)
        self.key = self.key_path.read_bytes()
        content, _ = _build_chain(self.key, [{"a": 1}, {"a": 2}])
        self.log_path.write_text(content)
        self.env = dict(os.environ)
        self.env["HOME"] = str(self.tmp)
        self.env["CEO_AUDIT_CHAIN_LENGTH_PATH"] = str(self.counter_path)
        self.env["PYTHONIOENCODING"] = "utf-8"
        for name in ("CEO_AUDIT_LOG_PATH", "CEO_AUDIT_LOG_DIR"):
            self.env.pop(name, None)

    def tearDown(self):
        self._tmp.cleanup()

    def _cli(self, *args, stdin=None, log=True, timeout=30):
        cmd = [sys.executable, str(_CLI), "--key-file", str(self.key_path)]
        if log:
            cmd += ["--log-file", str(self.log_path)]
        cmd += list(args)
        return subprocess.run(
            cmd, capture_output=True, input=stdin, env=self.env, timeout=timeout)

    def _json_report(self, proc):
        lines = proc.stdout.decode("utf-8").splitlines()
        self.assertEqual(len(lines), 1, proc.stdout)
        return json.loads(
            lines[0], parse_constant=lambda name: self.fail("non-JSON constant " + name))

    def _assert_named(self, proc, rc, reason):
        self.assertEqual(proc.returncode, rc, proc.stdout + proc.stderr)
        self.assertNotIn(b"Traceback", proc.stderr)
        self.assertIn(reason, self._json_report(proc)["reason"])

    def test_fu144_truncation_is_a_named_report_not_a_traceback(self):
        """_format_report(entry=None) raised AttributeError: rc 1 only by accident."""
        self.counter_path.write_text("5\n")
        proc = self._cli("--strict-against-counter", "--json")
        self._assert_named(proc, 1, "chain_length_truncation")
        report = self._json_report(proc)
        self.assertEqual(report["status"], "tamper")
        self.assertEqual((report["verified_count"], report["expected_length"]), (2, 5))
        human = self._cli("--strict-against-counter")
        self.assertEqual(human.returncode, 1)
        self.assertNotIn(b"Traceback", human.stderr)
        self.assertIn(b"chain_length_truncation", human.stderr)

    def test_fu144_counter_absent_is_rc0_and_visible(self):
        """S363-4: an absent counter passes, but says so, in every output mode."""
        self.assertFalse(self.counter_path.exists())
        proc = self._cli("--strict-against-counter", "--json")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(self._json_report(proc)["chain_length_source"], "absent")
        quiet = self._cli("--strict-against-counter")
        self.assertEqual(quiet.returncode, 0, quiet.stderr)
        self.assertIn(b"chain_length_source=absent", quiet.stderr)

    def test_fu144_counter_present_and_override_name_their_source(self):
        self.counter_path.write_text("2\n")
        proc = self._cli("--strict-against-counter", "--json")
        self.assertEqual(self._json_report(proc)["chain_length_source"], "sidecar")
        proc = self._cli("--strict-against-counter", "--json", "--counter-override", "2")
        self.assertEqual(self._json_report(proc)["chain_length_source"], "override")
        self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_fu144_counter_unreadable_is_named_and_fail_closed(self):
        """S363-4: read_chain_length() maps each of these to 0 (pass). Strict refuses."""
        for body in (b"abc\n", b"", b"-1\n", b"\xff\xfe\n", b"1_000\n"):
            self.counter_path.write_bytes(body)
            self._assert_named(
                self._cli("--strict-against-counter", "--json"), 3, "chain_length_unreadable")
        self.counter_path.unlink()
        self.counter_path.mkdir()
        self._assert_named(
            self._cli("--strict-against-counter", "--json"), 3, "chain_length_unreadable")
        self.counter_path.rmdir()
        os.mkfifo(self.counter_path)
        self._assert_named(
            self._cli("--strict-against-counter", "--json"), 3, "chain_length_unreadable")

    def test_fu144_stdin_and_file_agree_on_invalid_utf8(self):
        """The r3 false claim: the same bytes were PASS on stdin and rc 3 in a file."""
        self.counter_path.write_text("0\n")
        bad = b'{"a":"\xff"}\n'
        self.log_path.write_bytes(bad)
        as_file = self._cli("--strict-against-counter", "--json")
        as_stdin = self._cli("--strict-against-counter", "--json", "--stdin", stdin=bad, log=False)
        self._assert_named(as_file, 3, "log_undecodable")
        self._assert_named(as_stdin, 3, "log_undecodable")
        env_c = dict(self.env, LC_ALL="C", LANG="C")
        env_c.pop("PYTHONIOENCODING", None)
        self.env = env_c
        self._assert_named(
            self._cli("--strict-against-counter", "--json", "--stdin", stdin=bad, log=False),
            3, "log_undecodable")

    def test_fu144_non_regular_log_is_refused_without_hanging(self):
        """A FIFO in the log's place used to block forever on the read."""
        self.log_path.unlink()
        os.mkfifo(self.log_path)
        self._assert_named(
            self._cli("--strict-against-counter", "--json", timeout=20), 3, "log_not_regular")
        self.log_path.unlink()
        self.log_path.mkdir()
        self._assert_named(self._cli("--strict-against-counter", "--json"), 3, "log_not_regular")
        self.log_path.rmdir()
        self._assert_named(self._cli("--strict-against-counter", "--json"), 3, "log_not_found")

    def test_fu144_invalid_override_never_reaches_the_argparse_rc(self):
        """rc 2 means key missing in this CLI's contract, so strict cannot borrow it.
        The override is judged before --help, in either order of the flags."""
        for value in ("abc", "-1", "1_000", "+5", ""):
            self._assert_named(
                self._cli("--strict-against-counter", "--json", "--counter-override=" + value),
                3, "counter_override_invalid")
        for args in (
            ("--counter-override", "abc", "--strict-against-counter", "--help", "--json"),
            ("--strict-against-counter", "--help", "--counter-override", "abc", "--json"),
        ):
            self._assert_named(self._cli(*args), 3, "counter_override_invalid")
        help_ok = self._cli("--strict-against-counter", "--counter-override", "3", "--help")
        self.assertEqual(help_ok.returncode, 0, help_ok.stderr)
        self.assertIn(b"usage:", help_ok.stdout)

    def test_fu144_other_argument_errors_are_named_under_strict(self):
        self._assert_named(
            self._cli("--strict-against-counter", "--json", "--since", "abc"), 3, "invalid_arguments")
        self._assert_named(self._cli("--strict-against-counter", "--json", "--nope"), 3, "invalid_arguments")
        self._assert_named(self._cli("--strict-against-counter", "--json", "--since"), 3, "invalid_arguments")

    def test_fu144_every_failure_under_strict_json_is_one_json_object(self):
        """A malformed line and a bad hmac reported on stderr only: empty --json stdout."""
        self.counter_path.write_text("0\n")
        self.log_path.write_text("not json\n")
        self._assert_named(self._cli("--strict-against-counter", "--json"), 3, "malformed_json_line")
        self.log_path.write_text('{"hmac":"' + "z" * 64 + '"}\n')
        self._assert_named(self._cli("--strict-against-counter", "--json"), 3, "hmac_field_unparseable")
        self.log_path.write_text('{"ts":NaN,"action":NaN,"hmac":"' + "0" * 64 + '"}\n')
        self._assert_named(self._cli("--strict-against-counter", "--json"), 3, "malformed_json_line")
        self.log_path.write_text("[" * 200000 + "\n")
        self._assert_named(self._cli("--strict-against-counter", "--json"), 3, "malformed_json_line")

    def test_fu144_key_failures_are_json_under_strict(self):
        self.counter_path.write_text("0\n")
        os.chmod(self.key_path, 0o644)
        self._assert_named(self._cli("--strict-against-counter", "--json"), 4, "key_unusable")
        self.key_path.unlink()
        self._assert_named(self._cli("--strict-against-counter", "--json"), 2, "key_missing")

    def test_fu144_non_strict_keeps_the_pre_contract_behaviour(self):
        """The promise the r3 caught as false: non-strict stays as the base left it."""
        self.assertEqual(self._cli("--counter-override", "abc", "--help").returncode, 2)
        self.assertEqual(self._cli("--help", "--counter-override", "abc").returncode, 0)
        self.assertEqual(self._cli("--since", "abc").returncode, 2)
        self.assertEqual(self._cli("--nope").returncode, 2)
        self.assertEqual(self._cli("--st").returncode, 2)
        self.counter_path.write_text("abc\n")
        proc = self._cli("--json")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            proc.stdout, b'{"status":"intact","verified_count":2,"pre_v29_count":0}\n')
        self.assertEqual(self._cli().stderr, b"")
        self.log_path.write_text("not json\n")
        proc = self._cli("--json")
        self.assertEqual((proc.returncode, proc.stdout), (3, b""))
        self.assertIn(b"line 1 is malformed JSON", proc.stderr)
        fifo_free = subprocess.run(
            [sys.executable, str(_CLI), "--key-file", str(self.key_path), "--log-file", "/dev/stdin"],
            input=b"", capture_output=True, env=self.env, timeout=30)
        self.assertEqual(fifo_free.returncode, 0, fifo_free.stderr)


if __name__ == "__main__":
    unittest.main()
