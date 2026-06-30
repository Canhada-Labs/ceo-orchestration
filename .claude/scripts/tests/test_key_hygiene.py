"""Unit tests for key-hygiene.py (PLAN-135 W5 O9) — mock transport only.

NO network, NO live Admin API calls (HARD RULE — zero paid/live spend).
Every HTTP interaction goes through a scripted MockHttp callable injected
via ``main(argv, http=...)``.

Load-bearing invariants under test:
  - admin key comes from env ONLY (no CLI flag accepts it);
  - the key value NEVER appears on stdout/stderr (S206 lesson);
  - error paths are redacted (``sk-ant-…`` scrubbed);
  - mutations REFUSE without explicit --confirm (zero network I/O);
  - dormant fail-soft (exit 0, nothing done) without the env key;
  - rotation-log auto-append matches the documented Log-table format.
"""

from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "key_hygiene", SCRIPTS_DIR / "key-hygiene.py"
)
key_hygiene = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
assert spec.loader is not None
spec.loader.exec_module(key_hygiene)  # type: ignore[union-attr]

FAKE_ADMIN_KEY = "sk-ant-admin01-FAKE-TEST-VALUE-000000"

ROTATION_LOG_FIXTURE = """# API key rotation log

> Append-only log.
> NEVER paste a key into this file.

## Log

| Date       | Key                | Reason          | Rotated by | Outcome | Notes |
|------------|--------------------|-----------------|------------|---------|-------|
| 2026-04-14 | ANTHROPIC_API_KEY  | initial setup   | @owner     | ok      | seed row. |

**Latest rotation window (Anthropic):** 2026-06-03.

## Some other section

Prose that must remain untouched.
"""


def _api_key(key_id: str, name: str = "key", status: str = "active") -> dict:
    return {
        "id": key_id,
        "type": "api_key",
        "name": name,
        "status": status,
        "partial_key_hint": "sk-ant-api03-R2D...igAA",
        "created_at": "2026-01-01T00:00:00Z",
        "workspace_id": None,
        "created_by": {"id": "user_x", "type": "user"},
    }


class MockHttp:
    """Scripted (status, body) responses; records every call."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []  # (method, url, headers, body)

    def __call__(self, method, url, headers, body):
        self.calls.append((method, url, headers, body))
        if not self.responses:
            raise AssertionError("MockHttp exhausted — unexpected call: " + url)
        status, payload = self.responses.pop(0)
        text = payload if isinstance(payload, str) else json.dumps(payload)
        return status, text


class KeyHygieneTestBase(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="ceo-keyhyg-test-"))
        self.log_path = self.tmp / "rotation-log.md"
        self.log_path.write_text(ROTATION_LOG_FIXTURE, encoding="utf-8")
        self._env_backup = dict(os.environ)
        os.environ.pop("ANTHROPIC_ADMIN_KEY", None)
        # Silence the best-effort audit emit, but record invocations.
        self._emits = []
        self._orig_emit = key_hygiene._audit_emit
        key_hygiene._audit_emit = lambda op, **f: self._emits.append((op, f))

    def tearDown(self) -> None:
        key_hygiene._audit_emit = self._orig_emit
        os.environ.clear()
        os.environ.update(self._env_backup)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_cli(self, argv, http=None):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = key_hygiene.main(argv, http=http)
        return rc, out.getvalue(), err.getvalue()

    def mut_args(self, *extra):
        return list(extra) + [
            "--reason", "compromise",
            "--rotated-by", "@tester",
            "--rotation-log", str(self.log_path),
        ]

    def log_rows(self):
        lines = self.log_path.read_text(encoding="utf-8").splitlines()
        return [ln for ln in lines if ln.startswith("|")]


class TestDormantFailSoft(KeyHygieneTestBase):
    def test_list_dormant_exit0_no_http(self) -> None:
        http = MockHttp([])
        rc, out, _ = self.run_cli(["list"], http=http)
        self.assertEqual(rc, 0)
        self.assertIn("DORMANT", out)
        self.assertEqual(http.calls, [])

    def test_deactivate_dormant_even_with_confirm(self) -> None:
        http = MockHttp([])
        rc, out, _ = self.run_cli(
            ["deactivate", "--key-id", "apikey_1", "--confirm"] + self.mut_args(),
            http=http,
        )
        self.assertEqual(rc, 0)
        self.assertIn("DORMANT", out)
        self.assertEqual(http.calls, [])
        self.assertEqual(len(self.log_rows()), 3)  # header + sep + seed only

    def test_incident_dormant(self) -> None:
        http = MockHttp([])
        rc, out, _ = self.run_cli(
            ["incident", "--confirm"] + self.mut_args(), http=http
        )
        self.assertEqual(rc, 0)
        self.assertIn("DORMANT", out)
        self.assertEqual(http.calls, [])


class TestConfirmGate(KeyHygieneTestBase):
    def test_deactivate_refuses_without_confirm(self) -> None:
        os.environ["ANTHROPIC_ADMIN_KEY"] = FAKE_ADMIN_KEY
        http = MockHttp([])
        rc, out, _ = self.run_cli(
            ["deactivate", "--key-id", "apikey_1"] + self.mut_args(), http=http
        )
        self.assertEqual(rc, key_hygiene.EXIT_REFUSED)
        self.assertIn("REFUSED", out)
        self.assertEqual(http.calls, [])  # zero network I/O before the gate
        self.assertEqual(len(self.log_rows()), 3)

    def test_incident_refuses_without_confirm(self) -> None:
        os.environ["ANTHROPIC_ADMIN_KEY"] = FAKE_ADMIN_KEY
        http = MockHttp([])
        rc, out, _ = self.run_cli(["incident"] + self.mut_args(), http=http)
        self.assertEqual(rc, key_hygiene.EXIT_REFUSED)
        self.assertIn("REFUSED", out)
        self.assertEqual(http.calls, [])


class TestList(KeyHygieneTestBase):
    def test_pagination_follows_last_id(self) -> None:
        os.environ["ANTHROPIC_ADMIN_KEY"] = FAKE_ADMIN_KEY
        http = MockHttp([
            (200, {"data": [_api_key("apikey_1")], "has_more": True,
                   "first_id": "apikey_1", "last_id": "apikey_1"}),
            (200, {"data": [_api_key("apikey_2")], "has_more": False,
                   "first_id": "apikey_2", "last_id": "apikey_2"}),
        ])
        rc, out, _ = self.run_cli(["list", "--json"], http=http)
        self.assertEqual(rc, 0)
        self.assertEqual(len(http.calls), 2)
        self.assertIn("after_id=apikey_1", http.calls[1][1])
        payload = json.loads(out)
        self.assertEqual(payload["count"], 2)

    def test_status_filter_and_headers(self) -> None:
        os.environ["ANTHROPIC_ADMIN_KEY"] = FAKE_ADMIN_KEY
        http = MockHttp([(200, {"data": [], "has_more": False})])
        rc, _, _ = self.run_cli(["list", "--status", "active"], http=http)
        self.assertEqual(rc, 0)
        method, url, headers, body = http.calls[0]
        self.assertEqual(method, "GET")
        self.assertIn("status=active", url)
        self.assertEqual(headers["x-api-key"], FAKE_ADMIN_KEY)
        self.assertEqual(headers["anthropic-version"], "2023-06-01")
        self.assertIsNone(body)

    def test_key_value_never_echoed(self) -> None:
        os.environ["ANTHROPIC_ADMIN_KEY"] = FAKE_ADMIN_KEY
        http = MockHttp([(200, {"data": [_api_key("apikey_1")], "has_more": False})])
        rc, out, err = self.run_cli(["list"], http=http)
        self.assertEqual(rc, 0)
        self.assertNotIn(FAKE_ADMIN_KEY, out)
        self.assertNotIn(FAKE_ADMIN_KEY, err)

    def test_non_200_is_api_error_and_redacted(self) -> None:
        os.environ["ANTHROPIC_ADMIN_KEY"] = FAKE_ADMIN_KEY
        http = MockHttp([(401, '{"error": "bad key ' + FAKE_ADMIN_KEY + '"}')])
        rc, out, err = self.run_cli(["list"], http=http)
        self.assertEqual(rc, key_hygiene.EXIT_API_ERROR)
        self.assertNotIn(FAKE_ADMIN_KEY, out + err)
        self.assertIn("sk-ant-[REDACTED]", err)


class TestDeactivate(KeyHygieneTestBase):
    def test_happy_path_appends_documented_row(self) -> None:
        os.environ["ANTHROPIC_ADMIN_KEY"] = FAKE_ADMIN_KEY
        http = MockHttp([(200, _api_key("apikey_9", name="ci-key", status="inactive"))])
        rc, out, _ = self.run_cli(
            ["deactivate", "--key-id", "apikey_9", "--confirm"] + self.mut_args(),
            http=http,
        )
        self.assertEqual(rc, 0)
        method, url, headers, body = http.calls[0]
        self.assertEqual(method, "POST")
        self.assertTrue(url.endswith("/v1/organizations/api_keys/apikey_9"))
        self.assertEqual(json.loads(body.decode("utf-8")), {"status": "inactive"})
        self.assertEqual(headers["content-type"], "application/json")
        rows = self.log_rows()
        self.assertEqual(len(rows), 4)  # header + sep + seed + new
        new_row = rows[-1]
        self.assertRegex(
            new_row,
            r"^\| \d{4}-\d{2}-\d{2} \| ANTHROPIC_API_KEY \| compromise \| @tester \| ok \| .*\|$",
        )
        self.assertIn("apikey_9(ci-key)", new_row)
        self.assertIn("deactivated: apikey_9(ci-key)", out)
        # Untouched surroundings survive.
        text = self.log_path.read_text(encoding="utf-8")
        self.assertIn("## Some other section", text)
        self.assertIn("**Latest rotation window (Anthropic):**", text)
        # Audit pair telemetry attempted.
        self.assertEqual(self._emits[-1][0], "deactivate")

    def test_row_inserted_inside_log_table(self) -> None:
        os.environ["ANTHROPIC_ADMIN_KEY"] = FAKE_ADMIN_KEY
        http = MockHttp([(200, _api_key("apikey_9"))])
        rc, _, _ = self.run_cli(
            ["deactivate", "--key-id", "apikey_9", "--confirm"] + self.mut_args(),
            http=http,
        )
        self.assertEqual(rc, 0)
        lines = self.log_path.read_text(encoding="utf-8").splitlines()
        seed_idx = next(i for i, ln in enumerate(lines) if "seed row" in ln)
        self.assertTrue(lines[seed_idx + 1].startswith("| "))  # right after seed
        self.assertFalse(lines[seed_idx + 2].startswith("|"))  # table still ends there


class TestIncident(KeyHygieneTestBase):
    def test_deactivates_all_active_minus_excluded(self) -> None:
        os.environ["ANTHROPIC_ADMIN_KEY"] = FAKE_ADMIN_KEY
        http = MockHttp([
            (200, {"data": [
                _api_key("apikey_a", name="leaked-1"),
                _api_key("apikey_b", name="leaked-2"),
                _api_key("apikey_new", name="replacement"),
            ], "has_more": False}),
            (200, _api_key("apikey_a", name="leaked-1", status="inactive")),
            (200, _api_key("apikey_b", name="leaked-2", status="inactive")),
        ])
        rc, out, _ = self.run_cli(
            ["incident", "--confirm", "--exclude-key-id", "apikey_new"]
            + self.mut_args(),
            http=http,
        )
        self.assertEqual(rc, 0)
        posts = [c for c in http.calls if c[0] == "POST"]
        self.assertEqual(len(posts), 2)
        self.assertNotIn("apikey_new", " ".join(c[1] for c in posts))
        rows = self.log_rows()
        self.assertEqual(len(rows), 4)  # exactly ONE new row
        self.assertIn("deactivated 2 org key(s)", rows[-1])
        self.assertIn("apikey_new", rows[-1])  # survivor recorded
        self.assertIn("provision the replacement in the Console", rows[-1])
        self.assertIn("incident: deactivated 2 key(s)", out)

    def test_no_active_keys_noop(self) -> None:
        os.environ["ANTHROPIC_ADMIN_KEY"] = FAKE_ADMIN_KEY
        http = MockHttp([(200, {"data": [], "has_more": False})])
        rc, out, _ = self.run_cli(
            ["incident", "--confirm"] + self.mut_args(), http=http
        )
        self.assertEqual(rc, 0)
        self.assertIn("no active keys", out)
        self.assertEqual(len(self.log_rows()), 3)  # no log row on a no-op


class TestRotationLogHelpers(KeyHygieneTestBase):
    def test_build_row_redacts_and_strips_pipes(self) -> None:
        row = key_hygiene.build_rotation_row(
            reason="compromise",
            rotated_by="@tester",
            notes="oops sk-ant-admin01-SHOULD-NOT-LEAK and | a pipe",
            today="2026-06-12",
        )
        self.assertNotIn("SHOULD-NOT-LEAK", row)
        self.assertIn("sk-ant-[REDACTED]", row)
        self.assertEqual(row.count("|"), 7)  # 6 columns -> exactly 7 pipes

    def test_append_raises_without_log_heading(self) -> None:
        bad = self.tmp / "bad.md"
        bad.write_text("# nothing here\n", encoding="utf-8")
        with self.assertRaises(key_hygiene.AdminApiError):
            key_hygiene.append_rotation_entry(bad, "| r |")

    def test_append_failure_surfaces_row_for_manual_paste(self) -> None:
        os.environ["ANTHROPIC_ADMIN_KEY"] = FAKE_ADMIN_KEY
        bad = self.tmp / "bad.md"
        bad.write_text("# no Log heading\n", encoding="utf-8")
        http = MockHttp([(200, _api_key("apikey_9"))])
        rc, out, err = self.run_cli(
            ["deactivate", "--key-id", "apikey_9", "--confirm",
             "--reason", "compromise", "--rotated-by", "@tester",
             "--rotation-log", str(bad)],
            http=http,
        )
        self.assertEqual(rc, key_hygiene.EXIT_API_ERROR)
        self.assertIn("paste this row manually", out)
        self.assertIn("ANTHROPIC_API_KEY", out)  # the row itself surfaced


class TestKeyCustody(KeyHygieneTestBase):
    def test_no_cli_flag_accepts_the_admin_key(self) -> None:
        # The parser must not expose any --admin-key/--key/--api-key option.
        rc, _, _ = self.run_cli(["list", "--admin-key", FAKE_ADMIN_KEY])
        self.assertEqual(rc, key_hygiene.EXIT_USAGE)
        for action_flag in ("--admin-key", "--api-key", "--key"):
            parser = key_hygiene.build_parser()
            opts = []
            for action in parser._subparsers._group_actions[0].choices.values():  # type: ignore[union-attr]
                for act in action._actions:
                    opts.extend(act.option_strings)
            self.assertNotIn(action_flag, opts)

    def test_redact_helper(self) -> None:
        self.assertEqual(
            key_hygiene._redact("x sk-ant-api03-abc123 y"),
            "x sk-ant-[REDACTED] y",
        )
        self.assertEqual(key_hygiene._redact(None), "")

    def test_real_audit_emit_never_raises(self) -> None:
        # Exercise the genuine fail-soft emit (action may be unregistered).
        self._orig_emit("test_probe", key_count=0)


class TestUsage(KeyHygieneTestBase):
    def test_missing_subcommand_is_usage_error(self) -> None:
        rc, _, _ = self.run_cli([])
        self.assertEqual(rc, key_hygiene.EXIT_USAGE)

    def test_invalid_reason_rejected(self) -> None:
        rc, _, _ = self.run_cli(
            ["deactivate", "--key-id", "k", "--confirm", "--reason", "because"]
        )
        self.assertEqual(rc, key_hygiene.EXIT_USAGE)


if __name__ == "__main__":
    unittest.main()
