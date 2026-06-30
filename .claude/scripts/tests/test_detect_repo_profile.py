"""Tests for detect-repo-profile.py (PLAN-083 Wave 0a sub-agent 0.6).

Stdlib unittest only. >=18 tests covering:
  - all 4 fixture detection outcomes (4 tests)
  - fail-CLOSED invariants on unknown / ambiguous structure (3 tests)
  - manual_override respected when present (2 tests)
  - YAML output validates against on-disk schema (2 tests)
  - confirm-profile updates manual_override flag (2 tests)
  - signals list populated correctly (2 tests)
  - --json schema validity (1 test)
  - YAML emit / parse round-trip + safety (3 tests)
  - schema enum membership drift (1 test)
  - exit codes (3 tests)
"""

from __future__ import annotations

import io
import json
import re
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from typing import List, Tuple

# Make script importable as a module from staging dir.
_HERE = Path(__file__).resolve().parent
_STAGING = _HERE.parent
sys.path.insert(0, str(_STAGING))

import importlib.util as _ilu

_spec = _ilu.spec_from_file_location(
    "detect_repo_profile", str(_STAGING / "detect-repo-profile.py")
)
assert _spec is not None and _spec.loader is not None
detect_repo_profile = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(detect_repo_profile)

FIXTURES = _STAGING / "fixtures"
SCHEMA_PATH = _STAGING / "repo-profile.schema.json"

# PLAN-091 Wave E unblock — the 4 fixture directories +
# repo-profile.schema.json are NOT committed at the PLAN-091 base SHA.
# Skip the fixture-dependent test classes until PLAN-093 Tier-5
# finalization creates them. Set CEO_REQUIRE_REPO_PROFILE_FIXTURES=1 to
# force the tests (will FAIL until PLAN-093 lands the fixtures).
_FIXTURES_OK = (
    FIXTURES.is_dir()
    and (FIXTURES / "cloned-trading-repo").is_dir()
    and (FIXTURES / "monorepo").is_dir()
    and (FIXTURES / "mixed-frontend-backend").is_dir()
    and (FIXTURES / "missing-package-manifest").is_dir()
    and SCHEMA_PATH.is_file()
)
_SKIP_NO_FIXTURES = unittest.skipUnless(
    _FIXTURES_OK,
    "detect-repo-profile fixtures missing — PLAN-093 Tier-5 finalization creates them",
)


def _run_cli(argv: List[str]) -> Tuple[int, str, str]:
    out = io.StringIO()
    err = io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        rc = detect_repo_profile.main(argv)
    return rc, out.getvalue(), err.getvalue()


def _copy_fixture(name: str, dest: Path) -> Path:
    src = FIXTURES / name
    shutil.copytree(src, dest, dirs_exist_ok=True)
    return dest


@_SKIP_NO_FIXTURES
class FixtureMonorepoTest(unittest.TestCase):
    def test_monorepo_fails_closed_to_trading_readonly(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "repo"
            _copy_fixture("monorepo", target)
            rc, out, err = _run_cli(["detect", "--target", str(target), "--json"])
            # Soft fail-CLOSED exit 1 for ambiguous-low-confidence.
            self.assertEqual(rc, 1, msg=f"rc={rc} out={out} err={err}")
            payload = json.loads(out.strip())
            self.assertEqual(payload["risk_class"], "trading-readonly")
            self.assertEqual(payload["confidence"], "low")
            self.assertIn("fallback:ambiguous-fail-closed", payload["signals"])


@_SKIP_NO_FIXTURES
class FixtureMissingManifestTest(unittest.TestCase):
    def test_missing_manifest_returns_unknown_exit_2(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "repo"
            _copy_fixture("missing-package-manifest", target)
            rc, out, err = _run_cli(["detect", "--target", str(target), "--json"])
            self.assertEqual(rc, 2, msg=f"rc={rc} out={out} err={err}")
            payload = json.loads(out.strip())
            self.assertEqual(payload["risk_class"], "unknown-needs-owner-confirmation")
            self.assertIn("fallback:no-signals", payload["signals"])

    def test_missing_manifest_NEVER_silent_generic(self) -> None:
        """Critical invariant: no-signals MUST NOT silently fall through to generic."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "repo"
            _copy_fixture("missing-package-manifest", target)
            rc, out, _err = _run_cli(["detect", "--target", str(target), "--json"])
            payload = json.loads(out.strip())
            self.assertNotEqual(payload["risk_class"], "generic")
            self.assertNotEqual(rc, 0)


@_SKIP_NO_FIXTURES
class FixtureMixedFrontendBackendTest(unittest.TestCase):
    def test_mixed_fullstack_resolves_to_frontend_medium(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "repo"
            _copy_fixture("mixed-frontend-backend", target)
            rc, out, err = _run_cli(["detect", "--target", str(target), "--json"])
            self.assertEqual(rc, 0, msg=f"rc={rc} out={out} err={err}")
            payload = json.loads(out.strip())
            self.assertEqual(payload["risk_class"], "frontend")
            self.assertEqual(payload["confidence"], "medium")
            self.assertIn("mixed:frontend+engine", payload["signals"])
            # Owner can override via confirm-profile engine.
            rc2, _out, _err = _run_cli(
                ["confirm-profile", "engine", "--target", str(target)]
            )
            self.assertEqual(rc2, 0)


@_SKIP_NO_FIXTURES
class FixtureClonedTradingRepoTest(unittest.TestCase):
    def test_trading_repo_detects_trading_readonly_high(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "repo"
            _copy_fixture("cloned-trading-repo", target)
            rc, out, err = _run_cli(["detect", "--target", str(target), "--json"])
            self.assertEqual(rc, 0, msg=f"rc={rc} out={out} err={err}")
            payload = json.loads(out.strip())
            self.assertEqual(payload["risk_class"], "trading-readonly")
            self.assertEqual(payload["confidence"], "high")
            # Must emit env + strategies + exchanges hits.
            self.assertTrue(any("env:exchange-api-key" in s for s in payload["signals"]))
            self.assertTrue(any("dir:strategies/" in s for s in payload["signals"]))
            self.assertTrue(any("dir:exchanges/" in s for s in payload["signals"]))


@_SKIP_NO_FIXTURES
class ManualOverrideTest(unittest.TestCase):
    def test_existing_manual_override_respected_no_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "repo"
            _copy_fixture("cloned-trading-repo", target)
            # First, confirm a profile.
            rc, _o, _e = _run_cli(
                ["confirm-profile", "engine", "--target", str(target)]
            )
            self.assertEqual(rc, 0)
            # Now detect — must NOT overwrite (manual_override=true).
            rc2, out2, _e2 = _run_cli(["detect", "--target", str(target), "--json"])
            payload = json.loads(out2.strip())
            self.assertEqual(payload["result"], "manual-override-respected")
            self.assertEqual(payload["manual_override_risk_class"], "engine")
            # Detection-only should still detect trading-readonly.
            self.assertEqual(payload["would-have-detected"], "trading-readonly")
            self.assertTrue(payload["diverged"])
            # Diverged -> rc 3.
            self.assertEqual(rc2, 3)

    def test_manual_override_persists_in_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "repo"
            _copy_fixture("mixed-frontend-backend", target)
            rc, _o, _e = _run_cli(
                ["confirm-profile", "fintech", "--target", str(target),
                 "--notes", "manual ACK for testing"]
            )
            self.assertEqual(rc, 0)
            yaml_path = target / ".claude" / "repo-profile.yaml"
            self.assertTrue(yaml_path.exists())
            text = yaml_path.read_text(encoding="utf-8")
            self.assertIn('manual_override: true', text)
            self.assertIn('risk_class: "fintech"', text)
            self.assertIn('manual ACK', text)


@_SKIP_NO_FIXTURES
class SchemaConformanceTest(unittest.TestCase):
    def test_emitted_yaml_validates_against_handcoded_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "repo"
            _copy_fixture("cloned-trading-repo", target)
            rc, _out, _err = _run_cli(["detect", "--target", str(target)])
            self.assertEqual(rc, 0)
            yaml_path = target / ".claude" / "repo-profile.yaml"
            text = yaml_path.read_text(encoding="utf-8")
            parsed = detect_repo_profile.parse_yaml(text)
            # Should validate cleanly against hand-coded schema.
            detect_repo_profile._validate_against_schema(parsed)

    def test_handcoded_schema_matches_json_schema_enums(self) -> None:
        """Cross-check: hand-coded VALID_PROFILES must match repo-profile.schema.json."""
        with SCHEMA_PATH.open("r", encoding="utf-8") as fh:
            schema = json.load(fh)
        risk_class_enum = schema["properties"]["risk_class"]["enum"]
        self.assertEqual(set(risk_class_enum), set(detect_repo_profile.VALID_PROFILES))
        confidence_enum = schema["properties"]["confidence"]["enum"]
        self.assertEqual(set(confidence_enum), {"high", "medium", "low"})


class ConfirmProfileTest(unittest.TestCase):
    def test_confirm_profile_rejects_unknown_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "repo"
            target.mkdir()
            rc, _o, err = _run_cli(
                ["confirm-profile", "totally-fake", "--target", str(target)]
            )
            self.assertEqual(rc, 3)
            self.assertIn("unknown profile name", err)

    def test_confirm_profile_rejects_unknown_sentinel(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "repo"
            target.mkdir()
            rc, _o, err = _run_cli(
                ["confirm-profile", "unknown-needs-owner-confirmation",
                 "--target", str(target)]
            )
            self.assertEqual(rc, 3)
            self.assertIn("no-signals sentinel", err)

    def test_confirm_profile_generic_explicit_only(self) -> None:
        """`generic` is reachable via Owner ACK only — never auto-detect."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "repo"
            target.mkdir()
            rc, _o, _e = _run_cli(
                ["confirm-profile", "generic", "--target", str(target)]
            )
            self.assertEqual(rc, 0)
            yaml_path = target / ".claude" / "repo-profile.yaml"
            parsed = detect_repo_profile.parse_yaml(yaml_path.read_text())
            self.assertEqual(parsed["risk_class"], "generic")
            self.assertEqual(parsed["manual_override"], True)


@_SKIP_NO_FIXTURES
class SignalsFieldTest(unittest.TestCase):
    def test_trading_signals_include_specific_dirs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "repo"
            _copy_fixture("cloned-trading-repo", target)
            rc, out, _e = _run_cli(["detect", "--target", str(target), "--json"])
            self.assertEqual(rc, 0)
            payload = json.loads(out.strip())
            sigs = payload["signals"]
            self.assertIn("dir:strategies/", sigs)
            self.assertIn("dir:exchanges/", sigs)

    def test_no_signals_yields_fallback_marker(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "repo"
            _copy_fixture("missing-package-manifest", target)
            rc, out, _e = _run_cli(["detect", "--target", str(target), "--json"])
            self.assertEqual(rc, 2)
            payload = json.loads(out.strip())
            self.assertEqual(payload["signals"], ["fallback:no-signals"])


@_SKIP_NO_FIXTURES
class JsonShapeTest(unittest.TestCase):
    def test_json_output_is_valid_and_contains_required_fields(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "repo"
            _copy_fixture("cloned-trading-repo", target)
            rc, out, _e = _run_cli(["detect", "--target", str(target), "--json"])
            self.assertEqual(rc, 0)
            payload = json.loads(out.strip())  # must parse cleanly
            for key in ("command", "risk_class", "confidence", "signals", "manual_override", "wrote"):
                self.assertIn(key, payload)


class YamlSafetyTest(unittest.TestCase):
    def test_parse_yaml_rejects_anchor(self) -> None:
        bad = '---\nrisk_class: &anchor "frontend"\n'
        with self.assertRaises(ValueError):
            detect_repo_profile.parse_yaml(bad)

    def test_parse_yaml_rejects_alias(self) -> None:
        bad = '---\nrisk_class: *somealias\n'
        with self.assertRaises(ValueError):
            detect_repo_profile.parse_yaml(bad)

    def test_parse_yaml_rejects_flow_map(self) -> None:
        bad = '---\nnested: {a: 1}\n'
        with self.assertRaises(ValueError):
            detect_repo_profile.parse_yaml(bad)

    def test_parse_yaml_rejects_bare_string(self) -> None:
        """YAML 1.1 surprises (no/yes/on/off/2026-01-01) — only quoted strings accepted."""
        bad = '---\nrisk_class: frontend\n'  # unquoted -> rejected
        with self.assertRaises(ValueError):
            detect_repo_profile.parse_yaml(bad)

    def test_emit_yaml_round_trip(self) -> None:
        original = {
            "schema_version": "1",
            "risk_class": "trading-readonly",
            "detected_at": "2026-05-11T15:42:01Z",
            "confidence": "high",
            "manual_override": False,
            "created_at": "2026-05-11T15:42:01Z",
            "signals": ["dir:strategies/", "env:exchange-api-key"],
            "manual_review_paths": ["strategies/**", "**/.env"],
        }
        text = detect_repo_profile.emit_yaml(original)
        parsed = detect_repo_profile.parse_yaml(text)
        # bool/list/string preserved
        self.assertEqual(parsed["risk_class"], "trading-readonly")
        self.assertEqual(parsed["manual_override"], False)
        self.assertEqual(parsed["signals"], ["dir:strategies/", "env:exchange-api-key"])
        self.assertEqual(parsed["manual_review_paths"], ["strategies/**", "**/.env"])


@_SKIP_NO_FIXTURES
class ShowCommandTest(unittest.TestCase):
    def test_show_when_absent_returns_exit_2(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "repo"
            target.mkdir()
            rc, out, _e = _run_cli(["show", "--target", str(target), "--json"])
            self.assertEqual(rc, 2)
            payload = json.loads(out.strip())
            self.assertEqual(payload["result"], "absent")

    def test_show_after_detect_returns_profile(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "repo"
            _copy_fixture("cloned-trading-repo", target)
            _run_cli(["detect", "--target", str(target)])
            rc, out, _e = _run_cli(["show", "--target", str(target), "--json"])
            self.assertEqual(rc, 0)
            payload = json.loads(out.strip())
            self.assertEqual(payload["profile"]["risk_class"], "trading-readonly")


@_SKIP_NO_FIXTURES
class ManualReviewPathsTest(unittest.TestCase):
    def test_trading_readonly_populates_manual_review_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "repo"
            _copy_fixture("cloned-trading-repo", target)
            rc, _o, _e = _run_cli(["detect", "--target", str(target)])
            self.assertEqual(rc, 0)
            yaml_text = (target / ".claude" / "repo-profile.yaml").read_text()
            parsed = detect_repo_profile.parse_yaml(yaml_text)
            paths = parsed.get("manual_review_paths", [])
            self.assertIsInstance(paths, list)
            self.assertGreaterEqual(len(paths), 10, msg=f"need >=10 paths, got {len(paths)}")
            self.assertIn("strategies/**", paths)
            self.assertIn("exchanges/**", paths)


@_SKIP_NO_FIXTURES
class CreatedAtPersistenceTest(unittest.TestCase):
    def test_created_at_preserved_across_redetect(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "repo"
            _copy_fixture("cloned-trading-repo", target)
            rc1, _o, _e = _run_cli(["detect", "--target", str(target)])
            self.assertEqual(rc1, 0)
            first = detect_repo_profile.parse_yaml(
                (target / ".claude" / "repo-profile.yaml").read_text()
            )
            first_created = first["created_at"]
            # Re-detect.
            rc2, _o, _e = _run_cli(["detect", "--target", str(target)])
            self.assertEqual(rc2, 0)
            second = detect_repo_profile.parse_yaml(
                (target / ".claude" / "repo-profile.yaml").read_text()
            )
            self.assertEqual(second["created_at"], first_created)


@_SKIP_NO_FIXTURES
class TimestampFormatTest(unittest.TestCase):
    def test_detected_at_is_rfc3339_utc(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "repo"
            _copy_fixture("cloned-trading-repo", target)
            rc, out, _e = _run_cli(["detect", "--target", str(target), "--json"])
            self.assertEqual(rc, 0)
            yaml_text = (target / ".claude" / "repo-profile.yaml").read_text()
            parsed = detect_repo_profile.parse_yaml(yaml_text)
            self.assertRegex(parsed["detected_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
            self.assertRegex(parsed["created_at"], r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")


class PathSafetyTest(unittest.TestCase):
    def test_target_must_exist(self) -> None:
        rc, _o, err = _run_cli(["detect", "--target", "/nonexistent/path/xyz123"])
        self.assertEqual(rc, 3)
        self.assertIn("does not exist", err)


class DefaultPathsTraversalTest(unittest.TestCase):
    def test_skip_node_modules_and_dot_git(self) -> None:
        """Detector must not crawl into node_modules / .git / .venv."""
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "repo"
            target.mkdir()
            # Inject a fake `node_modules/strategies/` that would FALSE-positive
            # to trading-readonly if traversal was unbounded.
            (target / "node_modules" / "strategies").mkdir(parents=True)
            (target / ".git").mkdir()
            (target / "package.json").write_text(
                '{"dependencies": {"next": "^14"}}', encoding="utf-8"
            )
            rc, out, _e = _run_cli(["detect", "--target", str(target), "--json"])
            self.assertEqual(rc, 0)
            payload = json.loads(out.strip())
            self.assertEqual(payload["risk_class"], "frontend")
            # No spurious trading signal.
            self.assertNotIn("dir:strategies/", payload["signals"])


if __name__ == "__main__":
    unittest.main()
