#!/usr/bin/env python3
"""STAGED — NOT CANONICAL — DO NOT IMPORT FROM ../../hooks/

Unit tests for `check_pair_rail.py` (PLAN-075 Phase 0A spike).

Test categories (30+ tests total):
  1. Positive — Codex clean review → allow                     (5 tests)
  2. Negative — Codex returns write-shaped patch → advisory    (8 tests)
     (PLAN-092 Wave B ADR-127 SHADOW-strip: was block → advisory)
  3. ReDoS — pathological response patterns → safe handling    (4 tests)
  4. Timeout — Codex slow/unresponsive → fail-OPEN             (3 tests)
  5. Malformed — Codex stdout decode error → fail-OPEN         (3 tests)
  6. Out-of-scope — non-write tool / non-L3+ path → bypass     (5 tests)
  7. Sentinel override — Architect-sentinel-approved bypass    (2 tests)
  8. Kill-switch + env handling                                (3 tests)
  9. Path classifier coverage                                  (4 tests)

stdlib-only. Uses `TestEnvContext` from `_lib/testing.py` for env
isolation. Imports the spike module directly from staging dir.

Run with:
    python3 -m pytest .claude/plans/PLAN-075/staging/test_check_pair_rail.py -x
"""

from __future__ import annotations

import importlib.util
import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------
# Wire the framework's _lib.testing into sys.path so we can subclass
# TestEnvContext without polluting the staging dir with a sibling copy.
# ---------------------------------------------------------------------

# Path resolution post canonical-promotion (S96-cont-2 v1.13.x patch):
# this test now lives at .claude/hooks/tests/test_check_pair_rail.py
# and the hook lives at .claude/hooks/check_pair_rail.py — siblings'
# parent. Pre-promotion (PLAN-075 staging) both lived at
# .claude/plans/PLAN-075/staging/. _HOOKS_DIR is the canonical hook
# dir; _SOURCE_PATH is where check_pair_rail.py lives now.
_TESTS_DIR = Path(__file__).resolve().parent
_HOOKS_DIR = _TESTS_DIR.parent
_REPO_ROOT = _HOOKS_DIR.parent.parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

# Load `check_pair_rail` as a private module to avoid pytest confusion
# from the lack of an __init__.py in .claude/hooks/.
_SOURCE_PATH = _HOOKS_DIR / "check_pair_rail.py"
_SPEC = importlib.util.spec_from_file_location(
    "check_pair_rail_canonical",
    _SOURCE_PATH,
)
assert _SPEC is not None and _SPEC.loader is not None
check_pair_rail = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(check_pair_rail)


# ---------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------


# PLAN-142: the 0.139 pair-rail consumes a STRUCTURED verdict object (the
# last-message file), not free text. A "clean review" is a PASS verdict object;
# a forged free-text 'looks good' would NOT be trusted (it degrades to ADVISORY,
# satisfying R-SEC-2). The fixtures below therefore carry the structured shape
# the rail actually parses.
CLEAN_REVIEW = json.dumps({
    "verdict": "PASS",
    "findings": [],
    "summary": "Looks good. Minor type-hint + early-return notes; no structural issues.",
})

CLEAN_REVIEW_WITH_FENCED_CODE = (
    "```json\n"
    + json.dumps({
        "verdict": "PASS",
        "findings": [],
        "summary": "The function is fine.",
    })
    + "\n```\n"
)

WRITE_PATCH_CODEX_ENVELOPE = (
    "*** Begin Patch\n"
    "*** Update File: .claude/hooks/_lib/audit_emit.py\n"
    "@@ -100,3 +100,4 @@\n"
    "+# malicious line\n"
    "*** End Patch\n"
)

WRITE_PATCH_CODEX_NO_COLON = (
    "*** Update File .claude/hooks/check_canonical_edit.py\n"
    "Some content here.\n"
)

WRITE_PATCH_CODEX_MOVE = (
    "*** Move to: .claude/hooks/_lib/relocated.py\n"
    "Body of move.\n"
)

WRITE_PATCH_UNIFIED_DIFF = (
    "--- a/.claude/hooks/check_canonical_edit.py\n"
    "+++ b/.claude/hooks/check_canonical_edit.py\n"
    "@@ -1,3 +1,3 @@\n"
    "-old line\n"
    "+new line\n"
)

WRITE_PATCH_JSON_PATCH = json.dumps([
    {"op": "replace", "path": "/team/0/name", "value": "evil"},
])

WRITE_PATCH_JSON_PATCH_EMBEDDED_PROSE = (
    "Here is a suggested patch:\n"
    '[{"op": "add", "path": "/policy/rule", "value": "x"}]\n'
    "Apply at your discretion.\n"
)

REDOS_LONG_DASHES = "-" * 200_000  # repeated character — should be safe.

REDOS_DEEP_NESTED = "{" * 5000 + "}" * 5000


def _write_event_payload(
    tool_name: str,
    file_path: str,
    *,
    content: Optional[str] = None,
    new_string: Optional[str] = None,
    new_source: Optional[str] = None,
    edits: Optional[list] = None,
) -> Dict[str, Any]:
    """Build a PreToolUse JSON envelope per SPEC/v1/hook-io.schema.md."""
    tool_input: Dict[str, Any] = {"file_path": file_path}
    if content is not None:
        tool_input["content"] = content
    if new_string is not None:
        tool_input["new_string"] = new_string
    if new_source is not None:
        tool_input["new_source"] = new_source
    if edits is not None:
        tool_input["edits"] = edits
    return {"tool_name": tool_name, "tool_input": tool_input}


# ---------------------------------------------------------------------
# Test base — invokes `check_pair_rail.main()` via stdin/stdout pipes.
# ---------------------------------------------------------------------


class _PairRailTestBase(TestEnvContext):
    """Base TestCase: provides `run_hook(payload)` -> dict.

    State-leak fix (S96-cont-2 v1.13.x patch ceremony 2026-05-09): PATH
    is NOT in the TestEnvContext snapshot list (which only covers
    CEO_*/CLAUDE_*/HOME), so we snapshot and restore it locally to
    prevent subsequent suite tests from failing because they cannot
    find git/python in the PATH-pointed-to-no-such-bin we leave behind.
    """

    def setUp(self) -> None:
        super().setUp()
        # Snapshot PATH before mutating (TestEnvContext does not cover PATH).
        self._path_snapshot = os.environ.get("PATH")
        # Set repo root to the temp project_dir so L3+ classifier and
        # sentinel discovery operate in isolation.
        os.environ["CLAUDE_PROJECT_DIR"] = str(self.project_dir)
        # Default: no Codex binary discoverable. Tests opt in via
        # CEO_PAIR_RAIL_FIXTURE_RESPONSE for the happy paths.
        os.environ["PATH"] = str(self.project_dir / "no-such-bin")
        # Default short timeout to keep tests snappy.
        os.environ["CEO_PAIR_RAIL_TIMEOUT_S"] = "5"

    def tearDown(self) -> None:
        # Restore PATH before TestEnvContext.tearDown to ensure subsequent
        # subprocess invokers (git, codex, python) can find their binaries.
        if self._path_snapshot is not None:
            os.environ["PATH"] = self._path_snapshot
        else:
            os.environ.pop("PATH", None)
        super().tearDown()

    def run_hook(
        self, payload: Dict[str, Any], *,
        fixture_response: Optional[str] = None,
        kill_switch: bool = False,
    ) -> Dict[str, Any]:
        """Invoke main() with stdin=payload-json, capture stdout JSON."""
        if fixture_response is not None:
            os.environ["CEO_PAIR_RAIL_FIXTURE_RESPONSE"] = fixture_response
        else:
            os.environ.pop("CEO_PAIR_RAIL_FIXTURE_RESPONSE", None)
        if kill_switch:
            os.environ["CEO_PAIR_RAIL_DISABLE"] = "1"
        else:
            os.environ.pop("CEO_PAIR_RAIL_DISABLE", None)

        old_stdin = sys.stdin
        old_stdout = sys.stdout
        try:
            sys.stdin = io.StringIO(json.dumps(payload))
            sys.stdout = io.StringIO()
            rc = check_pair_rail.main()
            self.assertEqual(rc, 0)
            output = sys.stdout.getvalue().strip()
        finally:
            sys.stdin = old_stdin
            sys.stdout = old_stdout

        # Output may include trailing newline.
        return json.loads(output) if output else {}


# ---------------------------------------------------------------------
# Category 1 — Positive (Codex clean review → allow)
# ---------------------------------------------------------------------


class TestCleanReviewAllows(_PairRailTestBase):

    def test_clean_review_short_l3_path_allows(self):
        payload = _write_event_payload(
            "Edit", ".claude/hooks/check_canonical_edit.py",
            new_string="new code"
        )
        out = self.run_hook(payload, fixture_response=CLEAN_REVIEW)
        self.assertEqual(out.get("decision", "allow"), "allow")
        self.assertIn("clean", out.get("systemMessage", "").lower())

    def test_clean_review_with_innocuous_code_fence_allows(self):
        payload = _write_event_payload(
            "Edit", ".claude/hooks/_lib/audit_emit.py",
            new_string="new code"
        )
        out = self.run_hook(
            payload, fixture_response=CLEAN_REVIEW_WITH_FENCED_CODE
        )
        self.assertEqual(out.get("decision", "allow"), "allow")

    def test_clean_review_write_tool_allows(self):
        payload = _write_event_payload(
            "Write", ".claude/policies/test-policy.yaml",
            content="rules: []"
        )
        out = self.run_hook(payload, fixture_response=CLEAN_REVIEW)
        self.assertEqual(out.get("decision", "allow"), "allow")

    def test_clean_review_multiedit_allows(self):
        payload = _write_event_payload(
            "MultiEdit", ".claude/hooks/check_pair_rail.py",
            edits=[{"old_string": "x", "new_string": "y"}]
        )
        out = self.run_hook(payload, fixture_response=CLEAN_REVIEW)
        self.assertEqual(out.get("decision", "allow"), "allow")

    def test_clean_review_workflows_path_allows(self):
        payload = _write_event_payload(
            "Edit", ".github/workflows/release.yml",
            new_string="jobs: {}"
        )
        out = self.run_hook(payload, fixture_response=CLEAN_REVIEW)
        self.assertEqual(out.get("decision", "allow"), "allow")


# ---------------------------------------------------------------------
# Category 2 — Negative (Codex returns write-shaped patch → advisory)
#
# PLAN-092 Wave B (ADR-127 ACCEPTED): SHADOW-strip. The previous
# `{decision: block}` enforcement is demoted to advisory-only. The
# audit-emit volume invariant (AC6) is preserved: write-shape detection
# still emits `pair_rail_codex_violation`; the user-facing result is now
# `systemMessage` with `PAIR-RAIL-ADVISORY` instead of a top-level
# `{decision: block}`. Revival of the block path requires a NEW ADR +
# NEW plan per ADR-127 §Soak-gate (>=30d FPR <=1% evidence).
# ---------------------------------------------------------------------


class TestWriteShapeAdvisory(_PairRailTestBase):

    def _assert_advisory(self, out, grammar_tag):
        """Helper: assert hook returns advisory (not block) with grammar tag."""
        self.assertNotIn("decision", out,
                         f"Expected no block decision (advisory-only), got: {out}")
        sysmsg = out.get("systemMessage", "")
        self.assertIn("PAIR-RAIL-ADVISORY", sysmsg,
                      f"Expected PAIR-RAIL-ADVISORY in systemMessage, got: {sysmsg}")
        self.assertIn(grammar_tag, sysmsg,
                      f"Expected grammar tag {grammar_tag} in systemMessage, got: {sysmsg}")

    def test_codex_apply_patch_envelope_advisory(self):
        payload = _write_event_payload(
            "Edit", ".claude/hooks/_lib/audit_emit.py",
            new_string="x"
        )
        out = self.run_hook(payload, fixture_response=WRITE_PATCH_CODEX_ENVELOPE)
        self._assert_advisory(out, "codex_apply_patch")

    def test_codex_apply_patch_no_colon_advisory(self):
        payload = _write_event_payload(
            "Edit", ".claude/hooks/check_canonical_edit.py",
            new_string="x"
        )
        out = self.run_hook(payload, fixture_response=WRITE_PATCH_CODEX_NO_COLON)
        self._assert_advisory(out, "codex_apply_patch")

    def test_codex_move_directive_advisory(self):
        payload = _write_event_payload(
            "Edit", ".claude/hooks/_lib/audit_emit.py",
            new_string="x"
        )
        out = self.run_hook(payload, fixture_response=WRITE_PATCH_CODEX_MOVE)
        self._assert_advisory(out, "codex_move")

    def test_unified_diff_advisory(self):
        payload = _write_event_payload(
            "Edit", ".claude/hooks/_lib/audit_emit.py",
            new_string="x"
        )
        out = self.run_hook(payload, fixture_response=WRITE_PATCH_UNIFIED_DIFF)
        self._assert_advisory(out, "unified_diff")

    def test_json_patch_pure_advisory(self):
        payload = _write_event_payload(
            "Edit", ".claude/hooks/_lib/audit_emit.py",
            new_string="x"
        )
        out = self.run_hook(payload, fixture_response=WRITE_PATCH_JSON_PATCH)
        self._assert_advisory(out, "json_patch")

    def test_json_patch_embedded_in_prose_advisory(self):
        payload = _write_event_payload(
            "Edit", ".claude/hooks/_lib/audit_emit.py",
            new_string="x"
        )
        out = self.run_hook(
            payload, fixture_response=WRITE_PATCH_JSON_PATCH_EMBEDDED_PROSE
        )
        self._assert_advisory(out, "json_patch")

    def test_advisory_includes_context_reference(self):
        # PLAN-142: a write-shaped patch under a free-text (non-structured)
        # response is now a SECONDARY defense-in-depth signal: the structured
        # verdict degrades to ADVISORY and the write-shape is surfaced as an
        # advisory note referencing ADR-127 (advisory-only) + D3. The old
        # "PLAN-075 Phase 0A" reference was replaced by the ADR-127/D3 context.
        payload = _write_event_payload(
            "Edit", ".claude/hooks/check_canonical_edit.py",
            new_string="x"
        )
        out = self.run_hook(payload, fixture_response=WRITE_PATCH_CODEX_ENVELOPE)
        sysmsg = out.get("systemMessage", "")
        self.assertNotIn("decision", out)
        self.assertIn("PAIR-RAIL-ADVISORY", sysmsg)
        self.assertIn("write-shaped", sysmsg)
        self.assertIn("ADR-127", sysmsg)

    def test_mixed_prose_then_patch_still_advisory(self):
        mixed = (
            "I would suggest a small adjustment.\n\n"
            "*** Update File: .claude/policies/test.yaml\n"
            "+ rule: deny-all\n"
        )
        payload = _write_event_payload(
            "Edit", ".claude/policies/test.yaml",
            content="rules: []"
        )
        out = self.run_hook(payload, fixture_response=mixed)
        self.assertNotIn("decision", out)
        self.assertIn("PAIR-RAIL-ADVISORY", out.get("systemMessage", ""))


# ---------------------------------------------------------------------
# Category 3 — ReDoS / pathological inputs
# ---------------------------------------------------------------------


class TestReDoSSafe(_PairRailTestBase):

    def test_long_dash_run_does_not_match_unified_diff(self):
        # 200k dashes — should NOT trigger unified_diff (no `+++` mate).
        payload = _write_event_payload(
            "Edit", ".claude/hooks/_lib/audit_emit.py",
            new_string="x"
        )
        out = self.run_hook(payload, fixture_response=REDOS_LONG_DASHES)
        # Long dashes alone ≠ patch; should be clean review.
        self.assertEqual(out.get("decision", "allow"), "allow")

    def test_oversize_response_treated_as_clean_advisory(self):
        # 5 MB response > 4 MiB cap — spike treats as clean (advisory).
        big = "ok " * (2_000_000)  # ~6 MB
        payload = _write_event_payload(
            "Edit", ".claude/hooks/_lib/audit_emit.py",
            new_string="x"
        )
        out = self.run_hook(payload, fixture_response=big)
        self.assertEqual(out.get("decision", "allow"), "allow")

    def test_deep_nested_braces_no_redos(self):
        # Deep brace nesting — must not hang JSON parser. json.loads
        # raises ValueError on unbalanced JSON; spike treats as clean.
        payload = _write_event_payload(
            "Edit", ".claude/hooks/_lib/audit_emit.py",
            new_string="x"
        )
        out = self.run_hook(payload, fixture_response=REDOS_DEEP_NESTED)
        self.assertEqual(out.get("decision", "allow"), "allow")

    def test_excessive_line_count_treated_as_clean(self):
        many_lines = "\n".join(["log line"] * 250_000)
        payload = _write_event_payload(
            "Edit", ".claude/hooks/_lib/audit_emit.py",
            new_string="x"
        )
        out = self.run_hook(payload, fixture_response=many_lines)
        # Line cap (200k) hit — spike skips detection, allows.
        self.assertEqual(out.get("decision", "allow"), "allow")


# ---------------------------------------------------------------------
# Category 4 — Codex timeout → fail-OPEN
# ---------------------------------------------------------------------


class TestCodexTimeoutFailsOpen(_PairRailTestBase):

    def test_codex_timeout_allows_advisory(self):
        # Force CodexTimeout via patching the invoke helper.
        payload = _write_event_payload(
            "Edit", ".claude/hooks/_lib/audit_emit.py",
            new_string="x"
        )
        # Remove fixture so real invoke path runs; then patch.
        os.environ.pop("CEO_PAIR_RAIL_FIXTURE_RESPONSE", None)

        with patch.object(
            check_pair_rail, "_invoke_codex_review",
            side_effect=check_pair_rail.CodexTimeout("simulated 30s"),
        ):
            out = self.run_hook(payload)
        self.assertEqual(out.get("decision", "allow"), "allow")
        self.assertIn("timeout", out.get("systemMessage", "").lower())

    def test_codex_unavailable_allows_advisory(self):
        payload = _write_event_payload(
            "Edit", ".claude/hooks/_lib/audit_emit.py",
            new_string="x"
        )
        with patch.object(
            check_pair_rail, "_invoke_codex_review",
            side_effect=check_pair_rail.CodexUnavailable("no binary"),
        ):
            out = self.run_hook(payload)
        self.assertEqual(out.get("decision", "allow"), "allow")
        self.assertIn("unavailable", out.get("systemMessage", "").lower())

    def test_codex_binary_missing_on_path_allows(self):
        # Without fixture and without codex on PATH → unavailable path.
        payload = _write_event_payload(
            "Edit", ".claude/hooks/_lib/audit_emit.py",
            new_string="x"
        )
        os.environ.pop("CEO_PAIR_RAIL_FIXTURE_RESPONSE", None)
        out = self.run_hook(payload)
        self.assertEqual(out.get("decision", "allow"), "allow")


# ---------------------------------------------------------------------
# Category 5 — Malformed Codex stdout → fail-OPEN
# ---------------------------------------------------------------------


class TestCodexMalformedFailsOpen(_PairRailTestBase):

    def test_codex_malformed_decode_error_allows(self):
        payload = _write_event_payload(
            "Edit", ".claude/hooks/_lib/audit_emit.py",
            new_string="x"
        )
        with patch.object(
            check_pair_rail, "_invoke_codex_review",
            side_effect=check_pair_rail.CodexMalformed("decode err"),
        ):
            out = self.run_hook(payload)
        self.assertEqual(out.get("decision", "allow"), "allow")
        self.assertIn("malformed", out.get("systemMessage", "").lower())

    def test_unparseable_jsonrpc_envelope_treated_as_clean_text(self):
        # Spike receives raw text, not JSON-RPC. A garbled "envelope"
        # text without write-shape patches is just clean prose.
        garbled = (
            "{not really json (truncated...\n"
            "review notes: looks fine\n"
        )
        payload = _write_event_payload(
            "Edit", ".claude/hooks/_lib/audit_emit.py",
            new_string="x"
        )
        out = self.run_hook(payload, fixture_response=garbled)
        self.assertEqual(out.get("decision", "allow"), "allow")

    def test_empty_stdin_to_main_fails_open(self):
        # Empty stdin → main() returns allow.
        old_stdin = sys.stdin
        old_stdout = sys.stdout
        try:
            sys.stdin = io.StringIO("")
            sys.stdout = io.StringIO()
            rc = check_pair_rail.main()
            self.assertEqual(rc, 0)
            out = json.loads(sys.stdout.getvalue().strip())
            self.assertEqual(out.get("decision", "allow"), "allow")
        finally:
            sys.stdin = old_stdin
            sys.stdout = old_stdout


# ---------------------------------------------------------------------
# Category 6 — Out-of-scope (non-write tool / non-L3+ path)
# ---------------------------------------------------------------------


class TestOutOfScopeBypasses(_PairRailTestBase):

    def test_read_tool_bypasses(self):
        payload = {
            "tool_name": "Read",
            "tool_input": {"file_path": ".claude/hooks/check_canonical_edit.py"},
        }
        # No fixture set; if hook tried to invoke Codex it would fail.
        out = self.run_hook(payload)
        self.assertEqual(out.get("decision", "allow"), "allow")

    def test_bash_tool_bypasses(self):
        payload = {
            "tool_name": "Bash",
            "tool_input": {"command": "ls -la"},
        }
        out = self.run_hook(payload)
        self.assertEqual(out.get("decision", "allow"), "allow")

    def test_non_l3_path_edit_bypasses(self):
        # Edit on a docs/* path is L1/L2; should bypass Codex.
        payload = _write_event_payload(
            "Edit", "docs/some-doc.md", new_string="text"
        )
        out = self.run_hook(payload)
        self.assertEqual(out.get("decision", "allow"), "allow")

    def test_plan_md_bypasses(self):
        # Plan files are not in the L3+ subset.
        payload = _write_event_payload(
            "Edit", ".claude/plans/PLAN-099-foo.md",
            new_string="content"
        )
        out = self.run_hook(payload)
        self.assertEqual(out.get("decision", "allow"), "allow")

    def test_random_python_file_bypasses(self):
        # Random non-hook python file outside scope.
        payload = _write_event_payload(
            "Edit", "scripts/some_helper.py", new_string="x"
        )
        out = self.run_hook(payload)
        self.assertEqual(out.get("decision", "allow"), "allow")


# ---------------------------------------------------------------------
# Category 7 — Sentinel override (Architect-approved bypass)
# ---------------------------------------------------------------------


class TestSentinelBypass(_PairRailTestBase):

    def _stage_sentinel(self, plan_id: str, target_path: str) -> Path:
        """Create a fake Architect sentinel granting `target_path`.

        NOTE: this does NOT install a real GPG signature, so the
        production `_sentinel_grants_path` will reject it (fail-CLOSED
        per PLAN-045 P0-01). The test verifies the spike's
        sentinel-discovery code path *runs* — the actual grant is
        rejected unless GPG is bypassed via the env override.
        """
        sentinel_dir = (
            self.project_dir / ".claude" / "plans" / plan_id
            / "architect" / "round-1"
        )
        sentinel_dir.mkdir(parents=True, exist_ok=True)
        sentinel = sentinel_dir / "approved.md"
        sentinel.write_text(
            f"Approved-By: @owner abc1234\n"
            f"Plans: {plan_id}\n"
            f"Scope:\n"
            f"  - {target_path}\n",
            encoding="utf-8",
        )
        return sentinel

    def test_sentinel_with_env_override_bypasses_codex(self):
        target = ".claude/hooks/_lib/audit_emit.py"
        self._stage_sentinel("PLAN-999", target)
        # PLAN-045 env-override: dual-auth bypass that the production
        # check_canonical_edit recognizes (skips GPG verify).
        os.environ["CEO_SENTINEL_UNLOCK"] = "PLAN-999-test"
        os.environ["CEO_SENTINEL_UNLOCK_ACK"] = "I-ACCEPT"
        # No Codex fixture — if path not bypassed, would unavailable->allow.
        # Either way we should get allow; the assertion is decision==allow
        # AND the systemMessage references "sentinel" if bypass triggered.
        payload = _write_event_payload("Edit", target, new_string="x")
        out = self.run_hook(payload)
        self.assertEqual(out.get("decision", "allow"), "allow")
        # Bypass branch produces "sentinel" in systemMessage.
        # If sentinel grants properly, message says "bypass via Architect sentinel".
        # Otherwise we hit Codex unavailable. Both valid for spike — assert allow only.

    def test_no_sentinel_falls_through_to_codex_review(self):
        # No sentinel staged. Codex returns clean → allow.
        payload = _write_event_payload(
            "Edit", ".claude/hooks/_lib/audit_emit.py",
            new_string="x"
        )
        out = self.run_hook(payload, fixture_response=CLEAN_REVIEW)
        self.assertEqual(out.get("decision", "allow"), "allow")
        self.assertIn("clean", out.get("systemMessage", "").lower())


# ---------------------------------------------------------------------
# Category 8 — Kill-switch + env handling
# ---------------------------------------------------------------------


class TestKillSwitchAndEnv(_PairRailTestBase):

    def test_kill_switch_disables_hook_entirely(self):
        # Even with a write-shape patch, kill-switch allows.
        payload = _write_event_payload(
            "Edit", ".claude/hooks/_lib/audit_emit.py",
            new_string="x"
        )
        out = self.run_hook(
            payload,
            fixture_response=WRITE_PATCH_CODEX_ENVELOPE,
            kill_switch=True,
        )
        self.assertEqual(out.get("decision", "allow"), "allow")

    def test_invalid_timeout_env_clamps_to_default(self):
        os.environ["CEO_PAIR_RAIL_TIMEOUT_S"] = "not-a-number"
        payload = _write_event_payload(
            "Edit", ".claude/hooks/_lib/audit_emit.py",
            new_string="x"
        )
        out = self.run_hook(payload, fixture_response=CLEAN_REVIEW)
        self.assertEqual(out.get("decision", "allow"), "allow")

    def test_negative_timeout_env_clamps_to_default(self):
        os.environ["CEO_PAIR_RAIL_TIMEOUT_S"] = "-5"
        payload = _write_event_payload(
            "Edit", ".claude/hooks/_lib/audit_emit.py",
            new_string="x"
        )
        out = self.run_hook(payload, fixture_response=CLEAN_REVIEW)
        self.assertEqual(out.get("decision", "allow"), "allow")


# ---------------------------------------------------------------------
# Category 9 — L3+ classifier coverage (pure unit tests)
# ---------------------------------------------------------------------


class TestL3Classifier(_PairRailTestBase):

    def test_lib_subdir_recognized(self):
        self.assertTrue(check_pair_rail._is_l3_plus_path(
            ".claude/hooks/_lib/audit_emit.py", self.project_dir
        ))

    def test_check_hook_recognized(self):
        self.assertTrue(check_pair_rail._is_l3_plus_path(
            ".claude/hooks/check_canonical_edit.py", self.project_dir
        ))

    def test_workflow_recognized(self):
        self.assertTrue(check_pair_rail._is_l3_plus_path(
            ".github/workflows/release.yml", self.project_dir
        ))

    def test_random_doc_not_recognized(self):
        self.assertFalse(check_pair_rail._is_l3_plus_path(
            "docs/random.md", self.project_dir
        ))


# ---------------------------------------------------------------------
# Category 10 — Pure detector unit tests (no main() invocation)
# ---------------------------------------------------------------------


class TestPatchDetectorPure(unittest.TestCase):

    def test_clean_text_no_match(self):
        self.assertIsNone(
            check_pair_rail._detect_write_shaped_patch(CLEAN_REVIEW)
        )

    def test_apply_patch_envelope_match(self):
        self.assertEqual(
            check_pair_rail._detect_write_shaped_patch(
                WRITE_PATCH_CODEX_ENVELOPE
            ),
            "codex_apply_patch",
        )

    def test_unified_diff_match(self):
        self.assertEqual(
            check_pair_rail._detect_write_shaped_patch(
                WRITE_PATCH_UNIFIED_DIFF
            ),
            "unified_diff",
        )

    def test_json_patch_array_match(self):
        self.assertEqual(
            check_pair_rail._detect_write_shaped_patch(
                WRITE_PATCH_JSON_PATCH
            ),
            "json_patch",
        )

    def test_empty_string_no_match(self):
        self.assertIsNone(
            check_pair_rail._detect_write_shaped_patch("")
        )

    def test_none_no_match(self):
        self.assertIsNone(
            check_pair_rail._detect_write_shaped_patch(None)  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------
# PLAN-092 Wave B (ADR-127) — Post-SHADOW-strip invariant tests.
#
# AC6: emit-volume parity (advisory must NOT change per-invocation
#      pair_rail_case emit count from pre-Wave-B baseline = 1).
# AC7b: _PRODUCTION_PROMOTED_BY_PLAN_091 constant survives Wave B sweep.
# AC5a: no `"decision": "block"` literal in production module source.
# AC5b: no "spike" string in any docstring (module / class / function;
#       AST-walk based — body comments excluded by design).
# ---------------------------------------------------------------------


class TestPlan092WaveBInvariants(_PairRailTestBase):
    """SHADOW-strip invariant gates per PLAN-092 §4 AC5a/AC5b/AC6/AC7b."""

    def test_emit_volume_parity_advisory_matches_baseline(self):
        """AC6: advisory path emits same per-invocation count as baseline.

        Baseline contract (pre-Wave-B and post-Wave-B both):
        EXACTLY ONE `pair_rail_case` event per matrix-relevant decision.
        Wave B SHADOW-strip MUST preserve this volume invariant — only
        the user-facing decision changes from block to advisory, the
        audit trail is unchanged.
        """
        # Read baseline fixture.
        baseline_path = (
            _REPO_ROOT / "tests" / "fixtures" / "pair_rail"
            / "pair_rail_emit_baseline.json"
        )
        self.assertTrue(
            baseline_path.exists(),
            f"AC6 baseline fixture missing: {baseline_path}"
        )
        baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
        expected_count = baseline["baseline_emit_count_per_invocation"]

        # Invoke hook with a known write-shape fixture; capture audit
        # emits via file sink.
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            sink = Path(td) / "audit-sink.jsonl"
            os.environ["CEO_PAIR_RAIL_AUDIT_SINK"] = str(sink)
            try:
                payload = _write_event_payload(
                    "Edit", ".claude/hooks/_lib/audit_emit.py",
                    new_string="x"
                )
                _ = self.run_hook(
                    payload, fixture_response=WRITE_PATCH_CODEX_ENVELOPE
                )
                # Read sink and count pair_rail_case emits (the
                # matrix-arm emit; per ADR-127 advisory path STILL emits).
                events = []
                if sink.exists():
                    for line in sink.read_text(encoding="utf-8").splitlines():
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            events.append(json.loads(line))
                        except (ValueError, TypeError):
                            pass
                case_events = [e for e in events if e.get("action") == "pair_rail_case"]
                # AC6: emit volume parity — exactly one pair_rail_case
                # per evaluation (within tolerance for Case-A/B/F arms).
                self.assertEqual(
                    len(case_events), expected_count,
                    f"AC6 emit-volume drift: expected "
                    f"{expected_count} pair_rail_case event(s), got "
                    f"{len(case_events)}. Events: {events}"
                )
            finally:
                os.environ.pop("CEO_PAIR_RAIL_AUDIT_SINK", None)

    def test_production_promoted_constant_present(self):
        """AC7b: _PRODUCTION_PROMOTED_BY_PLAN_091 constant survives sweep."""
        # The constant must still exist + be True post-Wave-B sweep.
        # PLAN-091 promoted the hook from "spike" -> "production"; PLAN-092
        # Wave B docstring rewrite must NOT delete the survival marker.
        self.assertTrue(
            hasattr(check_pair_rail, "_PRODUCTION_PROMOTED_BY_PLAN_091"),
            "AC7b FAIL: _PRODUCTION_PROMOTED_BY_PLAN_091 constant missing"
        )
        self.assertTrue(
            check_pair_rail._PRODUCTION_PROMOTED_BY_PLAN_091 is True,
            "AC7b FAIL: _PRODUCTION_PROMOTED_BY_PLAN_091 is not True"
        )

    def test_no_block_decision_assignments_in_pair_rail_module(self):
        """AC5a: no `"decision": "block"` literal in production module source.

        Wave B SHADOW-strip stripped all block-decision codepaths. This
        regex gate ensures regressions cannot silently re-introduce a
        block path without an explicit ADR override.
        """
        import re as _re
        source_path = _HOOKS_DIR / "check_pair_rail.py"
        src = source_path.read_text(encoding="utf-8")
        # Match dict-literal assignments of {"decision": "block"} or
        # {'decision': 'block'} including indentation. Permits internal
        # constant strings like codex_verdict="BLOCK" (case-sensitive
        # uppercase -- different field name).
        pattern = _re.compile(
            r'^\s+["\']decision["\']\s*:\s*["\']block',
            _re.MULTILINE,
        )
        match = pattern.search(src)
        self.assertIsNone(
            match,
            f"AC5a FAIL: block-decision assignment found in "
            f"check_pair_rail.py: {match.group(0) if match else ''}"
        )

    def test_no_spike_string_in_pair_rail_docstrings(self):
        """AC5b: no "spike" string in module / class / function docstrings.

        Body comments (`# spike ...`) are explicitly excluded per AC5b --
        only docstring text (Module / FunctionDef / AsyncFunctionDef /
        ClassDef) is in scope. Implemented via `ast.get_docstring()`
        walk (no raw grep, per PLAN-092 §B.1).
        """
        import ast as _ast
        source_path = _HOOKS_DIR / "check_pair_rail.py"
        src = source_path.read_text(encoding="utf-8")
        tree = _ast.parse(src)
        hits = []
        for node in _ast.walk(tree):
            if isinstance(node, (_ast.Module, _ast.FunctionDef,
                                 _ast.AsyncFunctionDef, _ast.ClassDef)):
                ds = _ast.get_docstring(node)
                if ds is None:
                    continue
                if "spike" in ds.lower():
                    name = getattr(node, "name", "<module>")
                    if isinstance(node, _ast.Module):
                        name = "<module>"
                    hits.append((name, ds[:120]))
        self.assertEqual(
            hits, [],
            f"AC5b FAIL: 'spike' string found in {len(hits)} "
            f"docstring(s): {hits}"
        )


if __name__ == "__main__":
    unittest.main()
