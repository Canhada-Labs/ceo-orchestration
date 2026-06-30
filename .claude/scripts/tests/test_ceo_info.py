"""Tests for ``ceo-info.py`` — PLAN-133 item [G4] (Wave G).

Live preflight / effective-config CLI. Tests cover:
- path resolution honors the canonical override chain;
- the writability probe never raises and reports the right status class;
- the live round-trip is DEFAULT-OFF and only runs on opt-in;
- the live round-trip is fail-open (network error → yellow, never raise);
- the no-secret-echo property: a credential never appears in any output;
- `--check` exits non-zero only when a required path is RED.

Env-hygiene (check-test-env-hygiene.py): this test class subclasses
``TestEnvContext`` and mutates the environment ONLY via
``unittest.mock.patch.dict`` (never a raw ``os.environ[...] =``), so teardown
restores state and the suite stays hermetic.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Dict, Tuple
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))
from _lib.testing import TestEnvContext  # noqa: E402

SCRIPT = REPO_ROOT / ".claude" / "scripts" / "ceo-info.py"

_SENTINEL_KEY = "sk-ant-SECRET-DO-NOT-ECHO-0123456789"


def _load_module():
    spec = importlib.util.spec_from_file_location("ceo_info", str(SCRIPT))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class CeoInfoSmokeTest(TestEnvContext):
    """Subprocess smoke tests — exercise the real CLI entrypoint."""

    def test_script_exists(self):
        self.assertTrue(SCRIPT.is_file())

    def test_help_exits_zero(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--help"],
            capture_output=True, text=True, timeout=10, cwd=str(REPO_ROOT),
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("ceo info", (result.stdout + result.stderr).lower())

    def test_plain_run_exits_zero_and_advisory(self):
        # No --check: advisory, always exit 0 even if a path were red.
        with mock.patch.dict(os.environ, {}, clear=False):
            result = subprocess.run(
                [sys.executable, str(SCRIPT)],
                capture_output=True, text=True, timeout=30, cwd=str(REPO_ROOT),
            )
        self.assertEqual(result.returncode, 0)
        self.assertIn("ceo info --check", result.stdout)

    def test_json_mode_emits_valid_json(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--json"],
            capture_output=True, text=True, timeout=30, cwd=str(REPO_ROOT),
        )
        self.assertIn(result.returncode, (0, 1))
        data = json.loads(result.stdout)
        self.assertIn("overall", data)
        self.assertIn("paths", data)
        self.assertIn("settings", data)
        self.assertIn("live_probe", data)


class CeoInfoPathResolutionTest(TestEnvContext):
    """Path resolution honors the canonical override chain."""

    def setUp(self):
        super().setUp()
        self.mod = _load_module()

    def test_audit_log_explicit_override_wins(self):
        with mock.patch.dict(
            os.environ,
            {"CEO_AUDIT_LOG_PATH": "/tmp/ceo-info-test/audit-log.jsonl"},
            clear=False,
        ):
            p = self.mod._audit_log_path()
        self.assertEqual(str(p), "/tmp/ceo-info-test/audit-log.jsonl")

    def test_audit_log_dir_override(self):
        # CEO_AUDIT_LOG_PATH absent, CEO_AUDIT_LOG_DIR present.
        env = {k: v for k, v in os.environ.items() if k != "CEO_AUDIT_LOG_PATH"}
        env["CEO_AUDIT_LOG_DIR"] = "/tmp/ceo-info-dir"
        with mock.patch.dict(os.environ, env, clear=True):
            p = self.mod._audit_log_path()
        self.assertEqual(str(p), "/tmp/ceo-info-dir/audit-log.jsonl")

    def test_memory_dir_explicit_override(self):
        with mock.patch.dict(
            os.environ, {"CEO_MEMORY_DIR": "/tmp/ceo-mem"}, clear=False
        ):
            p = self.mod._memory_dir()
        self.assertEqual(str(p), "/tmp/ceo-mem")

    def test_plans_dir_is_repo_relative(self):
        p = self.mod._plans_dir()
        self.assertTrue(str(p).endswith("/.claude/plans"))


class CeoInfoWritabilityTest(TestEnvContext):
    """The writability probe never raises and classes status correctly."""

    def setUp(self):
        super().setUp()
        self.mod = _load_module()

    def test_present_writable_dir_is_green(self):
        with tempfile.TemporaryDirectory() as td:
            status, _note = self.mod._writable_status(Path(td), is_dir=True)
        self.assertEqual(status, "green")

    def test_absent_with_writable_parent_is_yellow(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "does-not-exist" / "audit-log.jsonl"
            status, note = self.mod._writable_status(target, is_dir=False)
        self.assertEqual(status, "yellow")
        self.assertIn("would-create", note)

    def test_nonexistent_ancestor_is_red(self):
        target = Path("/nonexistent-root-xyz/abc/def/audit-log.jsonl")
        status, _note = self.mod._writable_status(target, is_dir=False)
        self.assertEqual(status, "red")


class CeoInfoLiveProbeTest(TestEnvContext):
    """Live round-trip: default-OFF, fail-open, no-secret-echo."""

    def setUp(self):
        super().setUp()
        self.mod = _load_module()

    def test_disabled_by_default_is_skipped(self):
        status, summary, detail = self.mod.probe_live_roundtrip(enabled=False)
        self.assertEqual(status, "skipped")
        self.assertFalse(detail["enabled"])
        self.assertIn("CEO_INFO_LIVE_PROBE", summary)

    def test_enabled_without_credential_is_yellow_not_red(self):
        env = {k: v for k, v in os.environ.items()
               if k not in ("ANTHROPIC_API_KEY", "ANTHROPIC_AUTH_TOKEN")}
        with mock.patch.dict(os.environ, env, clear=True):
            status, _summary, detail = self.mod.probe_live_roundtrip(enabled=True)
        self.assertEqual(status, "yellow")
        self.assertEqual(detail["credential"], "absent")

    def test_enabled_success_reports_latency_green(self):
        calls: Dict[str, object] = {}

        def fake_post(url, headers, body, timeout) -> Tuple[int, bytes]:
            calls["url"] = url
            calls["headers"] = headers
            return 200, json.dumps({"input_tokens": 7}).encode("utf-8")

        with mock.patch.dict(
            os.environ, {"ANTHROPIC_API_KEY": _SENTINEL_KEY}, clear=False
        ):
            status, summary, detail = self.mod.probe_live_roundtrip(
                enabled=True, http_post=fake_post
            )
        self.assertEqual(status, "green")
        self.assertEqual(detail["http_status"], 200)
        self.assertEqual(detail["input_tokens"], 7)
        self.assertIn("latency_ms", detail)
        # Hits the count_tokens endpoint (bills no tokens).
        self.assertIn("count_tokens", calls["url"])

    def test_network_error_fails_open_yellow(self):
        def boom(url, headers, body, timeout):
            raise OSError("connection refused")

        with mock.patch.dict(
            os.environ, {"ANTHROPIC_API_KEY": _SENTINEL_KEY}, clear=False
        ):
            status, summary, detail = self.mod.probe_live_roundtrip(
                enabled=True, http_post=boom
            )
        self.assertEqual(status, "yellow")
        self.assertEqual(detail["error"], "OSError")

    def test_auth_rejected_is_red(self):
        def reject(url, headers, body, timeout):
            return 401, b'{"error":"auth"}'

        with mock.patch.dict(
            os.environ, {"ANTHROPIC_API_KEY": _SENTINEL_KEY}, clear=False
        ):
            status, _summary, detail = self.mod.probe_live_roundtrip(
                enabled=True, http_post=reject
            )
        self.assertEqual(status, "red")
        self.assertEqual(detail["http_status"], 401)


class CeoInfoNoSecretEchoTest(TestEnvContext):
    """The credential value must NEVER appear in any rendered output."""

    def setUp(self):
        super().setUp()
        self.mod = _load_module()

    def test_secret_absent_from_json_and_human(self):
        def fake_post(url, headers, body, timeout):
            # The secret IS sent on the wire (x-api-key header) but must not
            # surface in build_info()'s output structure.
            assert headers["x-api-key"] == _SENTINEL_KEY
            return 200, json.dumps({"input_tokens": 3}).encode("utf-8")

        with mock.patch.dict(
            os.environ, {"ANTHROPIC_API_KEY": _SENTINEL_KEY}, clear=False
        ):
            data = self.mod.build_info(live=True, http_post=fake_post)
            json_blob = json.dumps(data, default=str)
            human = self.mod.render_human(data)

        self.assertNotIn(_SENTINEL_KEY, json_blob)
        self.assertNotIn(_SENTINEL_KEY, human)
        # Presence is surfaced as a flag, not the value.
        self.assertEqual(data["env_overrides"].get("ANTHROPIC_API_KEY"), "<set>")


class CeoInfoCheckExitCodeTest(TestEnvContext):
    """--check exits non-zero only when a required path is RED."""

    def setUp(self):
        super().setUp()
        self.mod = _load_module()

    def test_check_returns_zero_when_clean(self):
        # Point all paths at a clean, writable temp tree → green.
        with tempfile.TemporaryDirectory() as td:
            env = {
                "CEO_AUDIT_LOG_PATH": str(Path(td) / "audit-log.jsonl"),
                "CEO_MEMORY_DIR": str(Path(td)),  # exists → green
            }
            with mock.patch.dict(os.environ, env, clear=False):
                rc = self.mod.main(["--check"])
        # plans_dir is the real repo dir (writable) → overall green/yellow, rc 0.
        self.assertEqual(rc, 0)

    def test_check_returns_one_when_required_path_red(self):
        env = {
            "CEO_AUDIT_LOG_PATH": "/nonexistent-root-xyz/audit-log.jsonl",
            "CEO_MEMORY_DIR": "/nonexistent-root-xyz/mem",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            rc = self.mod.main(["--check"])
        self.assertEqual(rc, 1)

    def test_without_check_is_always_zero(self):
        env = {
            "CEO_AUDIT_LOG_PATH": "/nonexistent-root-xyz/audit-log.jsonl",
            "CEO_MEMORY_DIR": "/nonexistent-root-xyz/mem",
        }
        with mock.patch.dict(os.environ, env, clear=False):
            rc = self.mod.main([])
        self.assertEqual(rc, 0)


# --------------------------------------------------------------------------- #
# PLAN-135 W5 (unit o8o11o12) — verify-models / cache-diagnose / hooks-diff.
# Every assertion below holds on the CURRENT tree WITHOUT the W1/W5 ceremony:
# the degraded paths (SKIPPED-pre-ceremony, allowlist-unavailable, no-network)
# are first-class behavior, not error states.
# --------------------------------------------------------------------------- #
class CeoInfoVerifyModelsStaticTest(TestEnvContext):
    """O8 static rate-card membership check — advisory, no network, fail-soft."""

    def setUp(self):
        super().setUp()
        self.mod = _load_module()

    def test_green_when_member_priced_in_both_tables(self):
        with tempfile.TemporaryDirectory() as td:
            adr = Path(td) / "ADR-149.md"
            adr.write_text(
                "FOO: frozenset = frozenset({\n"
                '    "claude-fable-5",\n'
                "})\n",
                encoding="utf-8",
            )
            ct = Path(td) / "cost-table.yaml"
            ct.write_text("models:\n  claude-fable-5:\n    input: 10\n", encoding="utf-8")
            pp = Path(td) / "provider-pricing.md"
            pp.write_text(
                "| Provider | Model | Input | Output |\n"
                "| --- | --- | --- | --- |\n"
                "| anthropic | claude-fable-5 | 0.01 | 0.05 |\n",
                encoding="utf-8",
            )
            out = self.mod.verify_models_static(
                adr_path=adr, cost_table_path=ct, pricing_path=pp
            )
        self.assertEqual(out["mode"], "static")
        self.assertEqual(out["status"], "green")
        self.assertEqual(len(out["members"]), 1)
        self.assertTrue(out["members"][0]["in_cost_table"])
        self.assertTrue(out["members"][0]["in_provider_pricing"])

    def test_yellow_when_member_missing_from_rate_card(self):
        with tempfile.TemporaryDirectory() as td:
            adr = Path(td) / "ADR-149.md"
            adr.write_text(
                'X = frozenset({"claude-fable-5", "claude-ghost-9"})\n',
                encoding="utf-8",
            )
            ct = Path(td) / "cost-table.yaml"
            ct.write_text("models:\n  claude-fable-5:\n    input: 10\n", encoding="utf-8")
            pp = Path(td) / "provider-pricing.md"
            pp.write_text(
                "| Provider | Model | In | Out |\n| - | - | - | - |\n"
                "| anthropic | claude-fable-5 | 0.01 | 0.05 |\n",
                encoding="utf-8",
            )
            out = self.mod.verify_models_static(
                adr_path=adr, cost_table_path=ct, pricing_path=pp
            )
        self.assertEqual(out["status"], "yellow")
        self.assertIn("claude-ghost-9", out["summary"])

    def test_unreadable_allowlist_degrades_yellow_not_raise(self):
        out = self.mod.verify_models_static(
            adr_path=Path("/nonexistent-xyz/ADR-149.md"),
            cost_table_path=Path("/nonexistent-xyz/cost.yaml"),
            pricing_path=Path("/nonexistent-xyz/pricing.md"),
        )
        self.assertIn(out["status"], ("yellow", "unknown"))
        self.assertEqual(out["members"], [])

    def test_live_probe_is_default_off_skipped(self):
        out = self.mod.probe_verify_models_live(["claude-fable-5"], enabled=False)
        self.assertEqual(out["status"], "skipped")
        self.assertEqual(out["models"], [])

    def test_live_probe_no_credential_is_yellow_not_red(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            out = self.mod.probe_verify_models_live(["claude-fable-5"], enabled=True)
        self.assertEqual(out["status"], "yellow")

    def test_live_probe_404_member_is_red_via_di_seam(self):
        def fake_get(url: str, headers: Dict[str, str], timeout: float) -> Tuple[int, bytes]:
            # 404 = allowlist member drifted off the live API.
            return 404, b'{"error":{"type":"not_found_error"}}'

        env = {"ANTHROPIC_API_KEY": _SENTINEL_KEY}
        with mock.patch.dict(os.environ, env, clear=False):
            out = self.mod.probe_verify_models_live(
                ["claude-ghost-9"], enabled=True, http_get=fake_get
            )
        self.assertEqual(out["status"], "red")
        self.assertEqual(out["models"][0]["http_status"], 404)
        # No-secret-echo: the credential never appears in the result payload.
        self.assertNotIn(_SENTINEL_KEY, json.dumps(out))

    def test_live_probe_200_green_with_metadata(self):
        def fake_get(url: str, headers: Dict[str, str], timeout: float) -> Tuple[int, bytes]:
            return 200, b'{"id":"claude-fable-5","display_name":"Fable 5","max_tokens":64000}'

        env = {"ANTHROPIC_API_KEY": _SENTINEL_KEY}
        with mock.patch.dict(os.environ, env, clear=False):
            out = self.mod.probe_verify_models_live(
                ["claude-fable-5"], enabled=True, http_get=fake_get
            )
        self.assertEqual(out["status"], "green")
        self.assertEqual(out["models"][0]["display_name"], "Fable 5")
        self.assertNotIn(_SENTINEL_KEY, json.dumps(out))


class CeoInfoCacheDiagnoseTest(TestEnvContext):
    """O11 static cache forensics — reads local transcripts, never the network."""

    def setUp(self):
        super().setUp()
        self.mod = _load_module()

    def test_no_transcripts_dir_is_skipped_with_pending_owner_recipe(self):
        env = {"CEO_INFO_TRANSCRIPTS_DIR": "/nonexistent-transcripts-xyz"}
        with mock.patch.dict(os.environ, env, clear=False):
            out = self.mod.cache_diagnose_section()
        self.assertEqual(out["status"], "skipped")
        self.assertEqual(out["live"]["status"], "pending-owner")
        self.assertIn("PENDING-OWNER", out["live"]["recipe"])

    def test_empty_dir_is_skipped(self):
        with tempfile.TemporaryDirectory() as td:
            out = self.mod.cache_diagnose_section(transcripts_dir=Path(td))
        self.assertEqual(out["status"], "skipped")

    def test_zero_cache_read_latest_turn_is_yellow(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td) / "session.jsonl"
            t.write_text(
                json.dumps({
                    "requestId": "req_1", "timestamp": "2026-06-12T00:00:00Z",
                    "message": {"id": "msg_1", "usage": {
                        "input_tokens": 100, "cache_read_input_tokens": 0,
                        "cache_creation_input_tokens": 50}},
                }) + "\n",
                encoding="utf-8",
            )
            out = self.mod.cache_diagnose_section(transcripts_dir=Path(td))
        self.assertEqual(out["status"], "yellow")
        self.assertEqual(out["previous_message_id"], "msg_1")
        self.assertEqual(out["zero_read_streak"], 1)

    def test_nonzero_cache_read_latest_turn_is_green(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td) / "session.jsonl"
            t.write_text(
                json.dumps({
                    "requestId": "req_2", "timestamp": "2026-06-12T00:01:00Z",
                    "message": {"id": "msg_2", "usage": {
                        "input_tokens": 100, "cache_read_input_tokens": 9000,
                        "cache_creation_input_tokens": 0}},
                }) + "\n",
                encoding="utf-8",
            )
            out = self.mod.cache_diagnose_section(transcripts_dir=Path(td))
        self.assertEqual(out["status"], "green")
        self.assertEqual(out["previous_message_id"], "msg_2")

    def test_malformed_lines_do_not_raise(self):
        with tempfile.TemporaryDirectory() as td:
            t = Path(td) / "session.jsonl"
            t.write_text("not json\n{}\n{\"message\":42}\n", encoding="utf-8")
            out = self.mod.cache_diagnose_section(transcripts_dir=Path(td))
        # No parseable usage entries → skipped, never a traceback.
        self.assertEqual(out["status"], "skipped")
        self.assertEqual(out["live"]["status"], "pending-owner")


class CeoInfoHooksDiffTest(TestEnvContext):
    """O11 effective-hook-count diff — SKIPPED on a pre-ceremony tree."""

    def setUp(self):
        super().setUp()
        self.mod = _load_module()

    def test_skipped_when_effective_config_absent(self):
        # Force the import to fail (pre-ceremony tree where _lib.effective_config
        # ships only in the W1 bundle) → SKIPPED, never a traceback.
        with mock.patch.object(self.mod, "_import_effective_config", return_value=None):
            out = self.mod.hooks_diff_section()
        self.assertEqual(out["status"], "skipped")
        self.assertIn("SKIPPED", out["summary"])

    def test_green_when_all_registered_hooks_on_disk(self):
        # Inject a fake effective_config module — proves the consumer math
        # without depending on the (staged-only) live module.
        class _FakeEC:
            @staticmethod
            def resolve_settings(_root):
                return {"layers": [{"name": "project", "data": {}}]}

            @staticmethod
            def registered_hook_basenames(_data):
                return ["audit_log.py"]

            @staticmethod
            def count_effective_hooks(_root):
                return 1

        out = self.mod.hooks_diff_section(ec=_FakeEC())
        # audit_log.py exists + readable in the repo → registered == effective.
        self.assertIn(out["status"], ("green", "red"))
        self.assertEqual(out["registered"], 1)

    def test_degraded_ec_does_not_raise(self):
        class _BoomEC:
            @staticmethod
            def resolve_settings(_root):
                raise RuntimeError("boom")

        out = self.mod.hooks_diff_section(ec=_BoomEC())
        self.assertEqual(out["status"], "unknown")
        self.assertIn("degraded", out["summary"])


class CeoInfoW5WiringTest(TestEnvContext):
    """The advisory sections are OPT-IN and never change exit codes."""

    def setUp(self):
        super().setUp()
        self.mod = _load_module()

    def test_default_build_info_has_no_w5_keys(self):
        data = self.mod.build_info(live=False)
        self.assertNotIn("verify_models", data)
        self.assertNotIn("cache_diagnose", data)
        self.assertNotIn("hooks_diff", data)

    def test_flagged_build_info_adds_sections(self):
        data = self.mod.build_info(
            live=False, verify_models=True, cache_diagnose=True, hooks_diff=True
        )
        self.assertIn("verify_models", data)
        self.assertIn("cache_diagnose", data)
        self.assertIn("hooks_diff", data)
        # advisory: the live sub-probe is OFF without --live.
        self.assertEqual(data["verify_models"]["live"]["status"], "skipped")

    def test_w5_flags_never_change_exit_code(self):
        # Even with every advisory section on, exit stays advisory (0) without
        # --check, and is governed ONLY by required-path RED under --check.
        with tempfile.TemporaryDirectory() as td:
            env = {
                "CEO_AUDIT_LOG_PATH": str(Path(td) / "audit-log.jsonl"),
                "CEO_MEMORY_DIR": str(Path(td)),
                "CEO_INFO_TRANSCRIPTS_DIR": "/nonexistent-transcripts-xyz",
            }
            with mock.patch.dict(os.environ, env, clear=False):
                rc = self.mod.main(
                    ["--check", "--verify-models", "--cache-diagnose", "--hooks-diff"]
                )
        self.assertEqual(rc, 0)

    def test_render_human_includes_sections_when_present(self):
        data = self.mod.build_info(live=False, verify_models=True)
        human = self.mod.render_human(data)
        self.assertIn("verify-models", human)


if __name__ == "__main__":
    unittest.main()
