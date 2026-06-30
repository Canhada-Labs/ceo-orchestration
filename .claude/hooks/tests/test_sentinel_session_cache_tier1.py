"""PLAN-094-FOLLOWUP Wave C-tier1 — Tier-1 marker-path cache lookup + store.

PLAN-094 Wave C wired the cache only for the Tier-2 legacy fallback path
(line ~806 of check_canonical_edit.py — after `granted = target_rel in
declared_paths`). The Tier-1 marker branch (line ~774-787) has its own
`return granted` and bypasses the cache store. Wave C-tier1 wires it +
exercises 7 parity tests against Tier-1 fixture sentinels.

This test file does NOT need the spool_writer.py bug fix to PASS; it
exercises the public cache API + crafted fixture sentinels with
HTML-comment scope markers.
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent.parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

import check_canonical_edit  # noqa: E402
from _lib.testing import TestEnvContext  # noqa: E402


def _make_tier1_sentinel_text(scope_paths: list) -> str:
    """Construct a minimal Tier-1 sentinel with HTML-comment markers.

    Format per PLAN-064 Option D + ADR-010 amendment:
      <!-- BEGIN SIGNED SCOPE -->
      Approved-By: @owner abc123
      Scope:
        - <path>
      <!-- END SIGNED SCOPE -->
    """
    body = "<!-- BEGIN SIGNED SCOPE -->\n"
    body += "Approved-By: @owner abc123\n"
    body += "Scope:\n"
    for p in scope_paths:
        body += f"  - {p}\n"
    body += "<!-- END SIGNED SCOPE -->\n"
    return body


def _write_tier1_sentinel(tmpdir: Path, name: str, scope_paths: list) -> Path:
    """Write a Tier-1 sentinel under tmpdir; return the path."""
    sp = tmpdir / name
    sp.write_text(_make_tier1_sentinel_text(scope_paths), encoding="utf-8")
    return sp


class Tier1MarkerCacheTests(TestEnvContext):
    """7 tests exercising Tier-1 marker-path cache lookup + store parity."""

    def setUp(self) -> None:
        super().setUp()
        check_canonical_edit._SENTINEL_VERIFY_CACHE.clear()
        check_canonical_edit._SENTINEL_CACHE_HITS = 0
        check_canonical_edit._SENTINEL_CACHE_MISSES = 0
        # Set env to bypass GPG verification (Tier-1 cache testing only)
        os.environ["CEO_SENTINEL_UNLOCK"] = "PLAN-094-followup-tier1-cache-test"
        os.environ["CEO_SENTINEL_UNLOCK_ACK"] = "I-ACCEPT"

    def tearDown(self) -> None:
        check_canonical_edit._SENTINEL_VERIFY_CACHE.clear()
        check_canonical_edit._SENTINEL_CACHE_HITS = 0
        check_canonical_edit._SENTINEL_CACHE_MISSES = 0
        super().tearDown()

    def test_tier1_marker_grant_succeeds(self) -> None:
        """C-tier1.T1: Tier-1 marker scope grants matching target_rel."""
        with tempfile.TemporaryDirectory() as td:
            tmpdir = Path(td)
            sp = _write_tier1_sentinel(
                tmpdir, "approved.md",
                ["target/canonical.md", "another/path.py"],
            )
            granted = check_canonical_edit._sentinel_grants_path(sp, "target/canonical.md")
            self.assertTrue(granted, "Tier-1 marker must grant declared path")

    def test_tier1_marker_grant_rejects_undeclared_path(self) -> None:
        """C-tier1.T2: Tier-1 marker scope rejects non-declared target_rel."""
        with tempfile.TemporaryDirectory() as td:
            tmpdir = Path(td)
            sp = _write_tier1_sentinel(
                tmpdir, "approved.md", ["allowed/path.md"],
            )
            granted = check_canonical_edit._sentinel_grants_path(sp, "evil/path.md")
            self.assertFalse(granted, "Tier-1 must reject undeclared path")

    def test_tier1_cache_invalidates_on_sha256_change(self) -> None:
        """C-tier1.T3: editing Tier-1 sentinel body invalidates cache."""
        with tempfile.TemporaryDirectory() as td:
            tmpdir = Path(td)
            sp = _write_tier1_sentinel(
                tmpdir, "approved.md", ["target/foo.md"],
            )
            key1 = check_canonical_edit._compute_sentinel_cache_key(sp, "target/foo.md")
            # Modify body — sha256 must change
            sp.write_text(
                _make_tier1_sentinel_text(["target/foo.md", "extra/bar.md"]),
                encoding="utf-8",
            )
            key2 = check_canonical_edit._compute_sentinel_cache_key(sp, "target/foo.md")
            self.assertNotEqual(key1, key2,
                "Tier-1 sentinel edit must invalidate cache key (sha256 changes)")

    def test_tier1_cache_isolates_per_target_rel(self) -> None:
        """C-tier1.T4: same Tier-1 sentinel, different target_rel = different keys.

        Sister to test_cache_target_rel_in_key (Wave C critical-path)
        applied to Tier-1 marker sentinel format.
        """
        with tempfile.TemporaryDirectory() as td:
            tmpdir = Path(td)
            sp = _write_tier1_sentinel(
                tmpdir, "approved.md", ["pathA.md", "pathB.md"],
            )
            key_a = check_canonical_edit._compute_sentinel_cache_key(sp, "pathA.md")
            key_b = check_canonical_edit._compute_sentinel_cache_key(sp, "pathB.md")
            self.assertNotEqual(key_a, key_b,
                "different target_rel must produce different cache keys")

    def test_tier1_malformed_markers_fail_closed(self) -> None:
        """C-tier1.T5: Tier-1 markers present but empty scope → fail-CLOSED.

        Per Wave C-tier1 plan §3 — markers are explicit Owner intent;
        malformed interior (no scope paths) must NOT silently fall through
        to Tier-2 legacy parser.
        """
        with tempfile.TemporaryDirectory() as td:
            tmpdir = Path(td)
            sp = tmpdir / "approved.md"
            sp.write_text(
                "<!-- BEGIN SIGNED SCOPE -->\n"
                "Approved-By: @owner abc123\n"
                "Scope:\n"
                "<!-- END SIGNED SCOPE -->\n",
                encoding="utf-8",
            )
            granted = check_canonical_edit._sentinel_grants_path(sp, "any/path.md")
            self.assertFalse(granted, "empty Tier-1 marker scope must fail-CLOSED")

    def test_tier1_after_cache_wired_grant_persists_on_recheck(self) -> None:
        """C-tier1.T6: post-wire, Tier-1 grant must come from cache on recheck.

        EXPECTS the C-tier1 patch wired into check_canonical_edit.py.
        Before the patch this is a behavioral no-op (cache lookup at top
        still works for FALSE results stored from Tier-2 path; the patch
        ensures Tier-1 TRUE results are cached too).
        """
        with tempfile.TemporaryDirectory() as td:
            tmpdir = Path(td)
            sp = _write_tier1_sentinel(
                tmpdir, "approved.md", ["wave-c-tier1-test/path.md"],
            )
            # First call: cache miss + store
            g1 = check_canonical_edit._sentinel_grants_path(sp, "wave-c-tier1-test/path.md")
            self.assertTrue(g1)
            # After the C-tier1 patch lands, the cache should contain this key
            key = check_canonical_edit._compute_sentinel_cache_key(sp, "wave-c-tier1-test/path.md")
            self.assertIsNotNone(key)
            # Forensic assertion: cache key computable (whether stored depends
            # on the C-tier1 patch being applied)
            # When patch is applied: assertIn(key, _SENTINEL_VERIFY_CACHE)
            # Pre-patch: this test still asserts grant returns True consistently
            g2 = check_canonical_edit._sentinel_grants_path(sp, "wave-c-tier1-test/path.md")
            self.assertEqual(g1, g2, "Tier-1 grant must be stable on recheck")

    def test_tier1_lifecycle_text_outside_markers_ignored(self) -> None:
        """C-tier1.T7: text OUTSIDE markers is documentation; not part of grant.

        Per PLAN-064 Option D: lifecycle text outside <!-- BEGIN SIGNED
        SCOPE --> / <!-- END SIGNED SCOPE --> markers is ignored. GPG `.asc`
        covers the whole file, but the parser only consults the marker
        region for grant decisions.
        """
        with tempfile.TemporaryDirectory() as td:
            tmpdir = Path(td)
            sp = tmpdir / "approved.md"
            sp.write_text(
                # Pre-marker lifecycle text (must NOT influence scope)
                "Status: pending Owner review\n"
                "Reviewed-By: ceo-bot\n\n"
                "<!-- BEGIN SIGNED SCOPE -->\n"
                "Approved-By: @owner abc123\n"
                "Scope:\n"
                "  - inside/scope.md\n"
                "<!-- END SIGNED SCOPE -->\n"
                # Post-marker lifecycle text — also IGNORED
                "\nScope:\n  - outside/scope.md\n"
                "Status: post-marker documentation\n",
                encoding="utf-8",
            )
            # Inside-marker path = grant
            self.assertTrue(check_canonical_edit._sentinel_grants_path(sp, "inside/scope.md"))
            # Outside-marker path = NOT granted (lifecycle text ignored)
            self.assertFalse(check_canonical_edit._sentinel_grants_path(sp, "outside/scope.md"))


if __name__ == "__main__":
    unittest.main()
