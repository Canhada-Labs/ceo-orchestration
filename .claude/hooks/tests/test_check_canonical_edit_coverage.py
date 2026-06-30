"""In-process coverage uplift for check_canonical_edit.py.

PLAN-112-FOLLOWUP-coverage-doctrine-reconcile (S157) / ADR-139 Tier-1.

The subprocess suite covers many sentinel-grant paths; this module
drives the parser/match helpers, the env-override (CEO_SENTINEL_UNLOCK)
Scope-parsing routes, the GPG fail-CLOSED branches and main()'s
fail-open / fail-CLOSED hook-fault handling in-process.

The env-override path lets us exercise Tier-1 / Tier-2 Scope parsing
without a real detached GPG signature (the override skips GPG verify by
design — a sub-agent cannot forge the dual-auth env pair).
"""

from __future__ import annotations

import io
import json
import os
import sys
import unittest
from pathlib import Path
from unittest import mock

from _lib.testing import TestEnvContext  # noqa: E402

import check_canonical_edit as cce  # noqa: E402

# Dual-auth env pair that satisfies the override regex.
_UNLOCK = {"CEO_SENTINEL_UNLOCK": "PLAN-112-coverage-uplift",
           "CEO_SENTINEL_UNLOCK_ACK": "I-ACCEPT"}


class CanonicalHelpersTest(TestEnvContext):

    def setUp(self):
        super().setUp()
        cce._SENTINEL_VERIFY_CACHE.clear()

    # --- _parse_scope_paths_from_text ------------------------------------

    def test_parse_scope_no_header(self):
        self.assertEqual(cce._parse_scope_paths_from_text("no scope here"), set())

    def test_parse_scope_bullets_and_skips(self):
        text = (
            "Scope:\n"
            "  - .claude/policies/a.yml\n"
            "Sub-header (group):\n"      # sub-header — skipped, keep going
            "  - .claude/policies/b.yml\n"
            "  - .\n"                      # normalizes to "." — dropped
        )
        paths = cce._parse_scope_paths_from_text(text)
        self.assertIn(".claude/policies/a.yml", paths)
        self.assertIn(".claude/policies/b.yml", paths)
        self.assertNotIn(".", paths)

    def test_parse_scope_control_char_rejected(self):
        text = "Scope:\n  - .claude/policies/\x01evil.yml\n"
        self.assertEqual(cce._parse_scope_paths_from_text(text), set())

    # --- segment matchers ------------------------------------------------

    def test_fnmatch_double_star(self):
        self.assertTrue(cce._fnmatch_segments(".claude/a/b/c.md", ".claude/**/c.md"))
        self.assertTrue(cce._fnmatch_segments(".claude/c.md", ".claude/**/c.md"))

    def test_fnmatch_single_star_and_literal(self):
        self.assertTrue(cce._fnmatch_segments(".github/workflows/x.yml",
                                              ".github/workflows/*.yml"))
        self.assertFalse(cce._fnmatch_segments(".github/workflows/x.txt",
                                               ".github/workflows/*.yml"))

    def test_is_canonical_true_false_outside(self):
        canon = str(Path(self.project_dir) / ".github" / "workflows" / "z.yml")
        noncanon = str(Path(self.project_dir) / "src" / "main.py")
        outside = "/tmp/somewhere/else.yml"
        self.assertTrue(cce._is_canonical(canon, Path(self.project_dir)))
        self.assertFalse(cce._is_canonical(noncanon, Path(self.project_dir)))
        self.assertFalse(cce._is_canonical(outside, Path(self.project_dir)))

    # --- persona-coverage emit -------------------------------------------

    def test_persona_emit_bypass(self):
        with mock.patch.dict(os.environ, {"CEO_PERSONA_COVERAGE_EMIT": "0"}):
            cce._emit_persona_coverage_synthesized(".github/workflows/z.yml")

    def test_persona_emit_default(self):
        # Real audit_emit writes to the isolated audit dir; must not raise.
        cce._emit_persona_coverage_synthesized(".github/workflows/z.yml")

    # --- sentinel cache helpers ------------------------------------------

    def test_sentinel_cache_stats_shape(self):
        stats = cce.sentinel_cache_stats()
        self.assertIn("hit_count", stats)
        self.assertIn("miss_count", stats)
        self.assertIn("size", stats)

    def test_extract_mcp_target_paths(self):
        self.assertEqual(cce._extract_mcp_target_paths("not-a-dict"), [])
        out = cce._extract_mcp_target_paths(
            {"path": ".github/workflows/z.yml", "edits": ["a.yml", "b.yml"]})
        self.assertIn(".github/workflows/z.yml", out)

    def test_find_sentinels_drops_symlink(self):
        base = Path(self.project_dir) / ".claude" / "plans" / "PLAN-777" / "architect" / "round-1"
        base.mkdir(parents=True, exist_ok=True)
        real = Path(self.project_dir) / "real-approved.md"
        real.write_text("Approved-By: @owner abc123\n", encoding="utf-8")
        link = base / "approved.md"
        link.symlink_to(real)
        found = cce._find_sentinels(Path(self.project_dir))
        self.assertNotIn(link.resolve(), [f.resolve() for f in found])


class SentinelGrantsPathTest(TestEnvContext):

    def setUp(self):
        super().setUp()
        cce._SENTINEL_VERIFY_CACHE.clear()

    def _sentinel(self, body: str, name="approved.md") -> Path:
        d = Path(self.project_dir) / ".claude" / "plans" / "PLAN-999" / "architect" / "round-1"
        d.mkdir(parents=True, exist_ok=True)
        s = d / name
        s.write_text(body, encoding="utf-8")
        return s

    def test_read_error_returns_false(self):
        missing = Path(self.project_dir) / "no-such-sentinel.md"
        self.assertFalse(cce._sentinel_grants_path(missing, ".github/workflows/z.yml"))

    def test_no_approved_by_returns_false(self):
        s = self._sentinel("just some text without the marker\n")
        self.assertFalse(cce._sentinel_grants_path(s, ".github/workflows/z.yml"))

    def test_gpg_unavailable_fail_closed(self):
        s = self._sentinel("Approved-By: @owner abcdef1234\nScope:\n  - x.yml\n")
        with mock.patch.object(cce, "_gpg_verify", None):
            self.assertFalse(cce._sentinel_grants_path(s, "x.yml"))

    def test_gpg_bad_signature_fail_closed(self):
        s = self._sentinel("Approved-By: @owner abcdef1234\nScope:\n  - x.yml\n")
        fake = mock.Mock()
        fake.verify_detached.return_value = (False, "", "bad-sig")
        with mock.patch.object(cce, "_gpg_verify", fake):
            self.assertFalse(cce._sentinel_grants_path(s, "x.yml"))

    def test_env_override_tier2_grant(self):
        s = self._sentinel(
            "Approved-By: @owner abcdef1234\nScope:\n"
            "  - .github/workflows/z.yml\n")
        with mock.patch.dict(os.environ, _UNLOCK):
            self.assertTrue(
                cce._sentinel_grants_path(s, ".github/workflows/z.yml"))
            # A path NOT in scope is not granted.
            self.assertFalse(
                cce._sentinel_grants_path(s, ".github/workflows/other.yml"))

    def test_env_override_no_scope_fail_closed(self):
        s = self._sentinel("Approved-By: @owner abcdef1234\n(no scope block)\n")
        with mock.patch.dict(os.environ, _UNLOCK):
            self.assertFalse(cce._sentinel_grants_path(s, "x.yml"))

    def test_env_override_tier1_markers_grant(self):
        body = (
            "Approved-By: @owner abcdef1234\n"
            "<!-- BEGIN SIGNED SCOPE -->\n"
            "Scope:\n"
            "  - .github/workflows/z.yml\n"
            "<!-- END SIGNED SCOPE -->\n"
            "lifecycle text outside markers - ignored\n"
        )
        s = self._sentinel(body)
        with mock.patch.dict(os.environ, _UNLOCK):
            self.assertTrue(
                cce._sentinel_grants_path(s, ".github/workflows/z.yml"))

    def test_env_override_tier1_markers_malformed_fail_closed(self):
        body = (
            "Approved-By: @owner abcdef1234\n"
            "<!-- BEGIN SIGNED SCOPE -->\n"
            "no bullets in here at all\n"
            "<!-- END SIGNED SCOPE -->\n"
        )
        s = self._sentinel(body)
        with mock.patch.dict(os.environ, _UNLOCK):
            self.assertFalse(cce._sentinel_grants_path(s, ".github/workflows/z.yml"))

    # --- GPG-success YAML-registry signer rail (727-768) -----------------

    def _gpg_ok_ctx(self, valid=True, why="ok"):
        """Build mocks: GPG verify ok + YAML registry + valid/invalid signer."""
        registry_yaml = Path(self.project_dir) / "sentinel-signers.yaml"
        registry_yaml.write_text("signers: [FPR123]\n", encoding="utf-8")
        fake_gpg = mock.Mock()
        fake_gpg.verify_detached.return_value = (True, "FPR123", "ok")
        fake_signers = mock.Mock()
        fake_signers.load_registry.return_value = {"FPR123": {}}
        fake_signers.is_valid_signer.return_value = (valid, why)
        return registry_yaml, fake_gpg, fake_signers

    def test_gpg_ok_valid_signer_grants(self):
        s = self._sentinel(
            "Approved-By: @owner abcdef1234\nScope:\n"
            "  - .github/workflows/z.yml\n")
        # sibling .asc so the sig path exists (content irrelevant — verify mocked)
        s.with_name(s.name + ".asc").write_text("sig", encoding="utf-8")
        reg, fake_gpg, fake_signers = self._gpg_ok_ctx(valid=True)
        with mock.patch.object(cce, "_gpg_verify", fake_gpg), \
                mock.patch.object(cce, "_sentinel_signers", fake_signers), \
                mock.patch.object(cce, "_SENTINEL_SIGNERS_REGISTRY_YAML", reg), \
                mock.patch.object(cce, "_BOOTSTRAP_REGISTRY_SHA256", None):
            self.assertTrue(
                cce._sentinel_grants_path(s, ".github/workflows/z.yml"))

    def test_gpg_ok_invalid_signer_fail_closed(self):
        s = self._sentinel(
            "Approved-By: @owner abcdef1234\nScope:\n"
            "  - .github/workflows/z.yml\n")
        s.with_name(s.name + ".asc").write_text("sig", encoding="utf-8")
        reg, fake_gpg, fake_signers = self._gpg_ok_ctx(valid=False, why="not-allowed")
        with mock.patch.object(cce, "_gpg_verify", fake_gpg), \
                mock.patch.object(cce, "_sentinel_signers", fake_signers), \
                mock.patch.object(cce, "_SENTINEL_SIGNERS_REGISTRY_YAML", reg), \
                mock.patch.object(cce, "_BOOTSTRAP_REGISTRY_SHA256", None):
            self.assertFalse(
                cce._sentinel_grants_path(s, ".github/workflows/z.yml"))

    def test_gpg_ok_bootstrap_sha_mismatch_fail_closed(self):
        s = self._sentinel(
            "Approved-By: @owner abcdef1234\nScope:\n"
            "  - .github/workflows/z.yml\n")
        s.with_name(s.name + ".asc").write_text("sig", encoding="utf-8")
        reg, fake_gpg, fake_signers = self._gpg_ok_ctx(valid=True)
        with mock.patch.object(cce, "_gpg_verify", fake_gpg), \
                mock.patch.object(cce, "_sentinel_signers", fake_signers), \
                mock.patch.object(cce, "_SENTINEL_SIGNERS_REGISTRY_YAML", reg), \
                mock.patch.object(cce, "_BOOTSTRAP_REGISTRY_SHA256", "deadbeef" * 8):
            # computed sha of the YAML != pinned bootstrap sha -> fail-closed
            self.assertFalse(
                cce._sentinel_grants_path(s, ".github/workflows/z.yml"))

    def test_gpg_ok_caches_grant_decision(self):
        s = self._sentinel(
            "Approved-By: @owner abcdef1234\nScope:\n"
            "  - .github/workflows/z.yml\n")
        s.with_name(s.name + ".asc").write_text("sig", encoding="utf-8")
        reg, fake_gpg, fake_signers = self._gpg_ok_ctx(valid=True)
        with mock.patch.object(cce, "_gpg_verify", fake_gpg), \
                mock.patch.object(cce, "_sentinel_signers", fake_signers), \
                mock.patch.object(cce, "_SENTINEL_SIGNERS_REGISTRY_YAML", reg), \
                mock.patch.object(cce, "_BOOTSTRAP_REGISTRY_SHA256", None):
            first = cce._sentinel_grants_path(s, ".github/workflows/z.yml")
            second = cce._sentinel_grants_path(s, ".github/workflows/z.yml")
        self.assertTrue(first)
        self.assertEqual(first, second)


class DecideTest(TestEnvContext):

    def setUp(self):
        super().setUp()
        cce._SENTINEL_VERIFY_CACHE.clear()
        self.repo = Path(self.project_dir)

    def test_decide_empty_allows(self):
        self.assertEqual(cce.decide(file_path="", repo_root=self.repo), "{}")

    def test_decide_noncanonical_allows(self):
        p = str(self.repo / "src" / "main.py")
        self.assertEqual(cce.decide(file_path=p, repo_root=self.repo), "{}")

    def test_decide_canonical_no_sentinel_blocks(self):
        p = str(self.repo / ".github" / "workflows" / "z.yml")
        out = json.loads(cce.decide(file_path=p, repo_root=self.repo))
        self.assertEqual(out["decision"], "block")

    def test_decide_canonical_with_sentinel_allows(self):
        # Plant a sentinel granting the canonical path; env-override skips GPG.
        d = self.repo / ".claude" / "plans" / "PLAN-999" / "architect" / "round-1"
        d.mkdir(parents=True, exist_ok=True)
        (d / "approved.md").write_text(
            "Approved-By: @owner abcdef1234\nScope:\n"
            "  - .github/workflows/z.yml\n", encoding="utf-8")
        p = str(self.repo / ".github" / "workflows" / "z.yml")
        with mock.patch.dict(os.environ, _UNLOCK):
            out = cce.decide(file_path=p, repo_root=self.repo)
        # allow (system message present, no block)
        self.assertNotIn("decision", json.loads(out))


class MainTest(TestEnvContext):

    def setUp(self):
        super().setUp()
        cce._SENTINEL_VERIFY_CACHE.clear()

    def _run_main(self, payload):
        data = json.dumps(payload) if isinstance(payload, (dict, list)) else str(payload)
        old_in, old_out = sys.stdin, sys.stdout
        sys.stdin = io.StringIO(data)
        sys.stdout = io.StringIO()
        try:
            rc = cce.main()
            out = sys.stdout.getvalue()
        finally:
            sys.stdin, sys.stdout = old_in, old_out
        return rc, out

    def test_main_read_event_exception_allows(self):
        with mock.patch("_lib.adapters.claude.read_event",
                        side_effect=RuntimeError("adapter")):
            rc, _ = self._run_main({"tool_input": {}})
        self.assertEqual(rc, 0)

    def test_main_no_candidate_paths_allows(self):
        rc, _ = self._run_main({"tool_name": "Edit", "tool_input": {}})
        self.assertEqual(rc, 0)

    def test_main_mcp_candidate_paths(self):
        with mock.patch.dict(os.environ,
                             {"CLAUDE_PROJECT_DIR": str(self.project_dir)}):
            rc, _ = self._run_main({
                "tool_name": "mcp__fs__write",
                "tool_input": {"path": str(Path(self.project_dir) / "src" / "x.py")},
            })
        self.assertEqual(rc, 0)

    def test_main_canonical_no_sentinel_blocks(self):
        canon = str(Path(self.project_dir) / ".github" / "workflows" / "z.yml")
        with mock.patch.dict(os.environ,
                             {"CLAUDE_PROJECT_DIR": str(self.project_dir)}):
            rc, out = self._run_main({
                "tool_name": "Edit",
                "tool_input": {"file_path": canon},
            })
        self.assertEqual(rc, 0)
        self.assertIn("block", out)

    def test_main_decide_raises_canonical_fail_closed(self):
        canon = str(Path(self.project_dir) / ".github" / "workflows" / "z.yml")
        with mock.patch.dict(os.environ,
                             {"CLAUDE_PROJECT_DIR": str(self.project_dir)}), \
                mock.patch("check_canonical_edit.decide",
                           side_effect=RuntimeError("boom")):
            rc, out = self._run_main({
                "tool_name": "Edit",
                "tool_input": {"file_path": canon},
            })
        self.assertEqual(rc, 0)
        self.assertIn("block", out)

    def test_main_decide_raises_noncanonical_allows(self):
        noncanon = str(Path(self.project_dir) / "src" / "main.py")
        with mock.patch.dict(os.environ,
                             {"CLAUDE_PROJECT_DIR": str(self.project_dir)}), \
                mock.patch("check_canonical_edit.decide",
                           side_effect=RuntimeError("boom")):
            rc, out = self._run_main({
                "tool_name": "Edit",
                "tool_input": {"file_path": noncanon},
            })
        self.assertEqual(rc, 0)
        self.assertNotIn("block", out)


if __name__ == "__main__":
    unittest.main()
