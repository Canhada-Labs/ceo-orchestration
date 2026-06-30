"""Tests for .claude/scripts/self_test.py (PLAN-133 C5).

The /self-test harness drives the three core governance guard hooks
IN-PROCESS against crafted payloads and asserts each BLOCKS, with a
$0-hermetic invariant (no Anthropic client constructed).

Covered:
- each guard scenario individually returns "block" against its payload;
- the end-to-end report passes and is hermetic;
- the Anthropic-import sentinel HAS TEETH (detects a synthetic import) and
  is fully reversed on exit (no poisoned import system);
- a real run imports NO anthropic module;
- the manifest parser is fail-open on a missing/garbled file;
- main() returns 0 on PASS, --json emits a parseable object;
- strict-vs-advisory infra-error handling.

Env hygiene (PLAN-019 P1-QA-3): this module subclasses TestEnvContext and
uses unittest.mock.patch.dict for any env mutation — never os.environ[...]=.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPT = REPO_ROOT / ".claude" / "scripts" / "self_test.py"

# Seed sys.path so _lib + the guard hooks resolve (conftest also does this,
# but keep the module self-sufficient if run in isolation).
for _p in (
    str(REPO_ROOT / ".claude" / "hooks"),
    str(REPO_ROOT / ".claude" / "scripts"),
):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from _lib.testing import TestEnvContext  # noqa: E402


def _load_module():
    spec = importlib.util.spec_from_file_location("ceo_self_test", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    # Register BEFORE exec so dataclasses can resolve string annotations on
    # Py3.9 (it reads sys.modules[cls.__module__].__dict__ — a None there
    # raises AttributeError during class creation).
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


_mod = _load_module()


class TestIndividualGuardDrivers(TestEnvContext):
    """Each guard, driven against its crafted payload, must BLOCK."""

    def test_spawn_missing_profile_blocks(self):
        verdict, _detail = _mod.drive_spawn_guard()
        self.assertEqual(verdict, "block")

    def test_canonical_edit_no_sentinel_blocks(self):
        verdict, _detail = _mod.drive_canonical_edit_guard()
        self.assertEqual(verdict, "block")

    def test_bash_destructive_blocks(self):
        verdict, _detail = _mod.drive_bash_safety_guard()
        self.assertEqual(verdict, "block")


class TestEndToEndReport(TestEnvContext):
    """The full report passes and is hermetic on a healthy framework."""

    def test_run_self_test_passes(self):
        report = _mod.run_self_test()
        self.assertTrue(
            report.passed,
            msg="self-test should PASS on the live framework: %s"
            % (report.to_dict(),),
        )
        self.assertEqual(len(report.scenarios), 3)
        self.assertTrue(all(s.actual == "block" for s in report.scenarios))

    def test_run_self_test_is_hermetic(self):
        report = _mod.run_self_test()
        self.assertFalse(
            report.anthropic_imported,
            msg="the self-test must construct NO Anthropic client",
        )
        self.assertIsNone(report.anthropic_module)


class TestAnthropicSentinel(TestEnvContext):
    """The hermeticity assertion must have teeth and be reversible."""

    def test_sentinel_detects_synthetic_anthropic_import(self):
        # The root token must be exactly an anthropic client package. A
        # submodule (anthropic.<x>) has root "anthropic" → recorded; the
        # underlying import still fails (no such submodule) but recording
        # happens BEFORE the orig __import__ is invoked.
        sentinel = _mod._AnthropicImportSentinel()
        with sentinel:
            try:
                __import__("anthropic.this_submodule_does_not_exist_zzz")
            except ImportError:
                pass
        self.assertIsNotNone(sentinel.imported_module)
        self.assertTrue(sentinel.imported_module.startswith("anthropic"))

    def test_sentinel_ignores_non_anthropic_lookalike(self):
        # A name that merely *starts with* "anthropic" but is a different
        # root token (e.g. "anthropicfoo") must NOT be flagged — we match on
        # the exact root package, not a substring prefix.
        sentinel = _mod._AnthropicImportSentinel()
        with sentinel:
            try:
                __import__("anthropicfoo_not_a_client_zzz")
            except ImportError:
                pass
        self.assertIsNone(sentinel.imported_module)

    def test_sentinel_restores_builtins_import(self):
        import builtins

        original = builtins.__import__
        with _mod._AnthropicImportSentinel():
            self.assertIsNot(builtins.__import__, original)
        # Fully reversed on exit — no poisoned import system left behind.
        self.assertIs(builtins.__import__, original)

    def test_sentinel_ignores_preloaded_anthropic_module(self):
        # Simulate a module already loaded BEFORE the run; it must not be
        # counted against the run (only NEW imports are).
        fake_name = "anthropic_preloaded_marker_zzz"
        with mock.patch.dict(sys.modules, {fake_name: mock.MagicMock()}):
            sentinel = _mod._AnthropicImportSentinel()
            with sentinel:
                __import__(fake_name)  # already loaded → re-import is a no-op
            self.assertIsNone(sentinel.imported_module)

    def test_run_fails_overall_if_anthropic_imported_mid_run(self):
        # Patch the sentinel so its tripped flag is set while every guard still
        # blocks; the overall verdict must be FAIL (hermeticity is mandatory).
        orig_exit = _mod._AnthropicImportSentinel.__exit__

        def _exit_then_trip(self, *exc):  # noqa: ANN001
            self.imported_module = "anthropic"
            return orig_exit(self, *exc)

        with mock.patch.object(
            _mod._AnthropicImportSentinel, "__exit__", _exit_then_trip
        ):
            report = _mod.run_self_test()
        self.assertTrue(all(s.actual == "block" for s in report.scenarios))
        self.assertTrue(report.anthropic_imported)
        self.assertFalse(report.passed)


class TestManifestParser(TestEnvContext):
    """The stdlib manifest parser is fail-open and reads the real file."""

    def test_missing_manifest_returns_empty_failopen(self):
        out = _mod.load_manifest(Path("/no/such/manifest/self_test.yaml"))
        self.assertEqual(out.get("scenarios"), [])

    def test_real_manifest_lists_three_scenarios(self):
        manifest = REPO_ROOT / ".claude" / "eval" / "self_test.yaml"
        out = _mod.load_manifest(manifest)
        ids = [s.get("id") for s in out.get("scenarios", [])]
        self.assertIn("spawn_missing_profile", ids)
        self.assertIn("canonical_edit_no_sentinel", ids)
        self.assertIn("bash_destructive_rm_rf", ids)
        self.assertEqual(out.get("hermetic"), "true")
        self.assertEqual(out.get("no_live_spawn"), "true")


class TestCli(TestEnvContext):
    """The CLI returns the right exit code and JSON shape."""

    def test_main_returns_zero_on_pass(self):
        rc = _mod.main([])
        self.assertEqual(rc, 0)

    def test_main_json_is_parseable(self):
        from io import StringIO

        buf = StringIO()
        with mock.patch.object(sys, "stdout", buf):
            rc = _mod.main(["--json"])
        self.assertEqual(rc, 0)
        obj = json.loads(buf.getvalue())
        self.assertTrue(obj["passed"])
        self.assertFalse(obj["anthropic_imported"])
        self.assertEqual(len(obj["scenarios"]), 3)


class TestInfraStrictness(TestEnvContext):
    """Infra errors are hard-fail in strict mode, advisory otherwise."""

    def test_strict_infra_error_fails(self):
        with mock.patch.object(
            _mod, "drive_spawn_guard",
            return_value=("infra_error", "boom"),
        ):
            report = _mod.run_self_test(strict_infra=True)
        self.assertFalse(report.passed)
        spawn = [s for s in report.scenarios if s.guard == "check_agent_spawn"][0]
        self.assertEqual(spawn.actual, "infra_error")
        self.assertFalse(spawn.passed)

    def test_advisory_infra_error_does_not_fail_that_scenario(self):
        with mock.patch.object(
            _mod, "drive_spawn_guard",
            return_value=("infra_error", "boom"),
        ):
            report = _mod.run_self_test(strict_infra=False)
        spawn = [s for s in report.scenarios if s.guard == "check_agent_spawn"][0]
        self.assertTrue(spawn.passed)  # demoted to advisory skip


# ---------------------------------------------------------------------------
# PLAN-135 W1 S3 — tamper-tripwire assertion section.
# These tests are green BOTH pre-ceremony (effective_config absent → the
# section reports "skipped", a passing advisory) AND post-ceremony (module
# present → real classification must "detect"). The detection/missed paths
# are exercised against a patched fake resolver so the LIVE tree never
# depends on the staged module (PLAN-135 coupling rule).
# ---------------------------------------------------------------------------


def _fake_resolver(findings):
    fake = mock.MagicMock()
    fake.TAMPER_DISABLE_ALL_HOOKS = "settings_tamper_disable_all_hooks"
    fake.TAMPER_ENDPOINT_REMAP = "settings_tamper_endpoint_remap"
    fake.TAMPER_PERMISSION_BYPASS = "settings_tamper_permission_bypass"
    fake.TAMPER_HOOK_COUNT_MISMATCH = "settings_tamper_hook_count_mismatch"
    fake.classify_tampering.return_value = findings
    return fake


_ALL_EXPECTED_CLASSES = (
    "settings_tamper_disable_all_hooks",
    "settings_tamper_endpoint_remap",
    "settings_tamper_permission_bypass",
    "settings_tamper_hook_count_mismatch",
)


class TestTamperTripwireSection(TestEnvContext):
    """PLAN-135 W1 S3 — the 4th (separate) self-test section."""

    def test_drive_returns_passing_verdict_on_this_tree(self):
        # Pre-ceremony: "skipped" (module absent). Post-ceremony: "detect".
        # Both are passing verdicts — the test is green on either tree.
        verdict, _detail = _mod.drive_tamper_tripwires()
        self.assertIn(verdict, ("detect", "skipped"))

    def test_skipped_when_module_unavailable(self):
        with mock.patch.object(
            _mod, "_load_effective_config",
            side_effect=ImportError("not installed"),
        ):
            verdict, detail = _mod.drive_tamper_tripwires()
        self.assertEqual(verdict, "skipped")
        self.assertIn("pre-PLAN-135-W1", detail)

    def test_detect_with_fake_resolver(self):
        findings = [
            {"class": c, "layer": "local", "detail": "redacted"}
            for c in _ALL_EXPECTED_CLASSES
        ]
        with mock.patch.object(
            _mod, "_load_effective_config",
            return_value=_fake_resolver(findings),
        ):
            verdict, detail = _mod.drive_tamper_tripwires()
        self.assertEqual(verdict, "detect")
        self.assertIn("secrets redacted", detail)

    def test_missed_when_detection_gutted(self):
        with mock.patch.object(
            _mod, "_load_effective_config",
            return_value=_fake_resolver([]),
        ):
            verdict, detail = _mod.drive_tamper_tripwires()
        self.assertEqual(verdict, "missed")
        self.assertIn("NOT detected", detail)

    def test_missed_when_secret_leaks_into_detail(self):
        findings = [
            {"class": c, "layer": "local", "detail": "x"}
            for c in _ALL_EXPECTED_CLASSES
        ]
        findings[1]["detail"] = (
            "ANTHROPIC_AUTH_TOKEN=%s" % _mod._TAMPER_PROBE_SECRET
        )
        with mock.patch.object(
            _mod, "_load_effective_config",
            return_value=_fake_resolver(findings),
        ):
            verdict, detail = _mod.drive_tamper_tripwires()
        self.assertEqual(verdict, "missed")
        self.assertIn("leaked", detail)

    def test_missed_fails_the_overall_run(self):
        with mock.patch.object(
            _mod, "drive_tamper_tripwires",
            return_value=("missed", "tamper class(es) NOT detected: x"),
        ):
            report = _mod.run_self_test()
        self.assertFalse(report.passed)
        self.assertEqual(len(report.tamper), 1)
        self.assertFalse(report.tamper[0].passed)
        # The 3-scenario C5 contract is untouched.
        self.assertEqual(len(report.scenarios), 3)

    def test_skipped_does_not_fail_the_overall_run(self):
        with mock.patch.object(
            _mod, "drive_tamper_tripwires",
            return_value=("skipped", "pre-ceremony"),
        ):
            report = _mod.run_self_test()
        self.assertTrue(report.passed)
        self.assertEqual(len(report.tamper), 1)
        self.assertTrue(report.tamper[0].passed)
        self.assertTrue(
            any("settings_tamper" in n for n in report.infra_notes)
        )

    def test_report_shape_scenarios_count_unchanged(self):
        report = _mod.run_self_test()
        self.assertEqual(len(report.scenarios), 3)
        self.assertEqual(len(report.tamper), 1)
        self.assertTrue(report.passed)
        d = report.to_dict()
        self.assertIn("tamper", d)
        self.assertEqual(len(d["tamper"]), 1)
        self.assertEqual(
            d["tamper"][0]["id"], "settings_tamper_classes_detected"
        )

    def test_human_format_renders_tamper_section(self):
        report = _mod.run_self_test()
        out = _mod._format_human(report)
        self.assertIn("tamper tripwires (PLAN-135 W1 S3)", out)

    def test_strict_infra_error_in_tamper_fails(self):
        with mock.patch.object(
            _mod, "drive_tamper_tripwires",
            return_value=("infra_error", "classifier raised"),
        ):
            report = _mod.run_self_test(strict_infra=True)
        self.assertFalse(report.passed)

    def test_advisory_infra_error_in_tamper_does_not_fail(self):
        with mock.patch.object(
            _mod, "drive_tamper_tripwires",
            return_value=("infra_error", "classifier raised"),
        ):
            report = _mod.run_self_test(strict_infra=False)
        self.assertTrue(report.passed)


if __name__ == "__main__":
    unittest.main()
