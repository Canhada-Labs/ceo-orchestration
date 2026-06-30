"""PLAN-019 DevOps-P2 — CI workflow invariants.

Grey-box tests validating that the three workflow edits landed by
PLAN-019 Wave 3D are present in the YAML files. actionlint in CI
still catches structural errors; these tests pin the specific rules
we care about so any regressive edit (revert, misplaced merge
conflict resolution) is caught at pytest time.

Covered:
- DevOps-P2-1  release.yml 14-day staleness check on 6 advisories.
- DevOps-P2-4  validate.yml check-test-env-hygiene step is hard-fail
               (no `|| true`, no `|| echo ::warning::`).
- DevOps-P2-5  formal-verify.yml SHA-pins aligned with 14 sibling
               workflows (actions/checkout@de0fac2, upload-artifact
               @043fb46).
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

_REPO = Path(__file__).resolve().parent.parent.parent.parent
_WF = _REPO / ".github" / "workflows"

# Bootstrap TestEnvContext so env isolation holds.
_HOOKS_DIR = _REPO / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))
from _lib.testing import TestEnvContext  # noqa: E402


class ReleaseStalenessTest(TestEnvContext):
    """DevOps-P2-1 — 14-day staleness check is wired into release gate."""

    def setUp(self):
        super().setUp()
        self.source = (_WF / "release.yml").read_text(encoding="utf-8")

    def test_staleness_days_constant(self):
        self.assertIn("STALENESS_DAYS=14", self.source)

    def test_staleness_secs_computed(self):
        self.assertIn("STALENESS_SECS=$((STALENESS_DAYS * 86400))", self.source)

    def test_all_six_workflows_listed(self):
        # The 6 advisory workflows whose staleness + health is gated.
        for wf in (
            "chaos.yml",
            "otel-smoke.yml",
            "perf-profile.yml",
            "adapter-live.yml",
            "red-team.yml",
            "formal-verify.yml",
        ):
            self.assertIn(wf, self.source, f"{wf} missing from advisory list")

    def test_zero_runs_fails_gate(self):
        # The critical fix: empty runs_json must FAIL, not continue.
        self.assertIn(
            "zero runs recorded; staleness gate fails",
            self.source,
        )

    def test_stale_message_format(self):
        # Error message must cite the workflow name + days + threshold.
        # This pins the user-facing format so operators can grep for it.
        self.assertIn(
            "stale — last run $days days ago",
            self.source,
        )

    def test_latest_started_parsed_from_json(self):
        # The fix reads startedAt from gh run list JSON.
        self.assertIn(".[0].startedAt", self.source)

    def test_gnu_date_used_for_iso8601_parse(self):
        # GNU date -d parses ISO-8601 on Linux runners.
        self.assertIn("date -u -d \"$latest_started\" +%s", self.source)

    def test_no_legacy_notice_on_empty(self):
        # Regression: the old "no recent runs, skipping" notice path is gone.
        self.assertNotIn("no recent runs, skipping", self.source)


class ValidateHygieneHardFailTest(TestEnvContext):
    """DevOps-P2-4 — check-test-env-hygiene.py flipped to hard-fail."""

    def setUp(self):
        super().setUp()
        self.source = (_WF / "validate.yml").read_text(encoding="utf-8")

    def test_hygiene_step_exists(self):
        self.assertIn("check-test-env-hygiene.py", self.source)

    def test_step_renamed_to_hard_fail(self):
        # The step label explicitly notes the hard-fail transition.
        self.assertIn("hard-fail post P2-4", self.source)

    def test_no_or_true_bypass(self):
        # Find the hygiene step block and confirm no "|| true" or "|| echo"
        # advisory bypass inside it.
        match = re.search(
            r"TestEnvContext hygiene — AST check.*?(?=\n      - name:|\n      # --)",
            self.source,
            flags=re.DOTALL,
        )
        self.assertIsNotNone(match, "could not locate hygiene step block")
        block = match.group(0)
        self.assertNotIn("|| true", block)
        self.assertNotIn("|| echo", block)

    def test_legacy_advisory_grep_still_present(self):
        # The legacy ADJ-028 grep is kept as advisory continuity during
        # allowlist drain — it should NOT have been dropped.
        self.assertIn("legacy grep", self.source)


class FormalVerifyShaPinAlignmentTest(TestEnvContext):
    """DevOps-P2-5 — formal-verify.yml pins match 14 sibling workflows."""

    def setUp(self):
        super().setUp()
        self.source = (_WF / "formal-verify.yml").read_text(encoding="utf-8")

    def test_checkout_sha_aligned_to_v6_0_2(self):
        # The canonical repo-wide SHA-pin for actions/checkout@v6.0.2.
        self.assertIn(
            "actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd",
            self.source,
        )

    def test_old_v4_2_2_checkout_sha_removed(self):
        # Previous pin at v4.2.2 should be gone.
        self.assertNotIn(
            "actions/checkout@11bd71901bbe5b1630ceea73d27597364c9af683",
            self.source,
        )

    def test_upload_artifact_sha_aligned_to_v7_0_1(self):
        # The canonical repo-wide SHA-pin for actions/upload-artifact@v7.0.1.
        self.assertIn(
            "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
            self.source,
        )

    def test_old_v4_6_2_upload_sha_removed(self):
        self.assertNotIn(
            "actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02",
            self.source,
        )

    def test_pin_comment_documents_alignment(self):
        # The comment trail explains WHY the bump happened so Dependabot
        # PRs don't silently re-drift.
        self.assertIn("DevOps-P2-5", self.source)
        self.assertIn("alignment", self.source.lower())


class PythonHookCacheTest(TestEnvContext):
    """Perf-P2-002 — _python-hook.sh caches resolved interpreter."""

    def setUp(self):
        super().setUp()
        hook_path = _REPO / ".claude" / "hooks" / "_python-hook.sh"
        self.source = hook_path.read_text(encoding="utf-8")

    def test_cache_dir_function_present(self):
        self.assertIn("_cache_dir()", self.source)

    def test_path_hash_function_present(self):
        # PATH-hash in cache filename so brew-installed python upgrades
        # automatically invalidate the cache.
        self.assertIn("_path_hash()", self.source)

    def test_cache_file_path_per_path_sig(self):
        self.assertIn("resolved-py-${_PATH_SIG}", self.source)

    def test_no_cache_env_escape_hatch(self):
        # Operators can disable the cache via CEO_PYHOOK_NO_CACHE=1.
        self.assertIn("CEO_PYHOOK_NO_CACHE", self.source)

    def test_atomic_cache_write(self):
        # mv -f from $$-suffixed tempfile avoids partial writes if the
        # hook is interrupted mid-cache-populate.
        self.assertIn("${_CACHE_FILE}.$$", self.source)
        self.assertIn("mv -f \"$_tmp_cache\" \"$_CACHE_FILE\"", self.source)

    def test_cache_dir_mode_0700(self):
        # User-scoped cache: 0700 prevents another unix user from
        # reading or hijacking the cached interpreter path.
        self.assertIn("chmod 0700 \"$_CACHE_DIR\"", self.source)


class FixtureBudgetDocTest(TestEnvContext):
    """Perf-P2-006 — fixture-budget.md exists with required sections."""

    def setUp(self):
        super().setUp()
        doc = _REPO / "docs" / "fixture-budget.md"
        self.assertTrue(doc.exists(), "docs/fixture-budget.md missing")
        self.source = doc.read_text(encoding="utf-8")

    def test_has_hard_cap_section(self):
        self.assertIn("Hard cap", self.source)

    def test_has_soft_cap_section(self):
        self.assertIn("Soft cap", self.source)

    def test_has_total_repo_cap(self):
        # The 10 MB total repo hard cap is the core invariant.
        self.assertIn("10 MB", self.source)

    def test_has_snapshot_date(self):
        # A concrete snapshot lets future engineers measure drift.
        self.assertIn("2026-04-17", self.source)

    def test_has_exception_policy(self):
        # Exception policy pointer is mandatory so future-exceptions go
        # through ADRs not quiet directory bloat.
        self.assertIn("Exception policy", self.source)

    def test_references_plan_019(self):
        self.assertIn("PLAN-019", self.source)


if __name__ == "__main__":
    unittest.main()
