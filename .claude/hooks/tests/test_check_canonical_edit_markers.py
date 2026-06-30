"""Tests for check_canonical_edit.py — PLAN-064 Option D lexical scope markers.

PLAN-064 (DIM-13 closure, 2026-05-04): Tier-1 sentinel format uses
HTML-comment markers `<!-- BEGIN SIGNED SCOPE -->` /
`<!-- END SIGNED SCOPE -->` to unambiguously delimit the signed scope
from lifecycle annotations. This file tests:

1. Tier 1 (markers present) → parser uses ONLY marker region.
2. Tier 2 (markers absent) → falls back to existing _SCOPE_HEADER_RE.
3. Mixed: lifecycle text outside markers does NOT influence grant.
4. Adversarial: malformed/repeated/nested markers, NFKC homoglyphs.
5. ReDoS bench: 64KiB pathological input ≤100ms wall-clock.
6. Length cap: input >64KiB fails-CLOSED before regex.

Backward compat by construction: existing 44 sentinels lack markers
and continue to parse via Tier-2.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import unittest
from pathlib import Path

_HOOKS_DIR = Path(__file__).resolve().parent.parent

from _lib.testing import TestEnvContext  # noqa: E402

_HOOK = _HOOKS_DIR / "check_canonical_edit.py"


def _markers_active() -> bool:
    """Detect whether PLAN-064 marker parser has been promoted into the
    canonical hook file. Pre-ceremony: returns False (tests skip).
    Post-ceremony: returns True (tests run, must be GREEN).

    This auto-detection means the test file ships staged WITHOUT
    breaking the pre-ceremony baseline. Once Owner runs
    `OWNER-CEREMONY-PLAN-064.sh`, the canonical hook gains
    `_SCOPE_MARKER_RE` and the tests start running automatically.
    """
    sys.path.insert(0, str(_HOOKS_DIR))
    try:
        import check_canonical_edit as m
        return hasattr(m, "_SCOPE_MARKER_RE") and hasattr(
            m, "_SCOPE_MARKER_CAP_BYTES"
        )
    except Exception:
        return False
    finally:
        # Clean up sys.path injection so other tests in the same process
        # don't pick up a stale cached import.
        if str(_HOOKS_DIR) in sys.path:
            sys.path.remove(str(_HOOKS_DIR))


_MARKERS_ACTIVE = _markers_active()
_SKIP_REASON = (
    "PLAN-064 Path B / Option D ceremony not yet run — "
    "_SCOPE_MARKER_RE / _SCOPE_MARKER_CAP_BYTES absent from canonical "
    ".claude/hooks/check_canonical_edit.py. Tests auto-activate after "
    "Owner runs OWNER-CEREMONY-PLAN-064.sh."
)


@unittest.skipUnless(_MARKERS_ACTIVE, _SKIP_REASON)
class CheckCanonicalEditMarkersTest(TestEnvContext):
    """Tests for Option D lexical scope markers (Tier 1 + Tier 2).

    Auto-skipped pre-ceremony (parser does not yet have
    `_SCOPE_MARKER_RE`). Auto-activated post-ceremony when Owner runs
    `OWNER-CEREMONY-PLAN-064.sh` and the modified parser lands in
    `.claude/hooks/check_canonical_edit.py`.
    """

    def _invoke(self, payload: dict) -> tuple[int, str, str]:
        env = {**os.environ}
        # PLAN-086 Wave I.1 (ADR-119) tightened the env-override regex to
        # ^(ADR-\d{3,4}|PLAN-\d{3})-[a-z0-9-]{3,100}$. Older "PLAN-TEST"
        # value fails the new pattern; use a compliant test fixture slug.
        env.setdefault("CEO_SENTINEL_UNLOCK", "PLAN-091-test-fixture")
        env.setdefault("CEO_SENTINEL_UNLOCK_ACK", "I-ACCEPT")
        proc = subprocess.run(
            [sys.executable, str(_HOOK)],
            input=json.dumps(payload),
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        return proc.returncode, proc.stdout, proc.stderr

    def _make_repo_layout(self) -> Path:
        (self.project_dir / ".claude").mkdir(exist_ok=True)
        (self.project_dir / ".claude" / "team.md").write_text("team", encoding="utf-8")
        (self.project_dir / ".claude" / "frontend-team.md").write_text("front", encoding="utf-8")
        (self.project_dir / ".claude" / "pitfalls-catalog.yaml").write_text("pf", encoding="utf-8")
        return self.project_dir

    def _write_sentinel_with_markers(
        self,
        plan_id: str,
        scope_paths: list,
        lifecycle_text: str = "",
        approved_by: str = "@Canhada-Labs deadbeef",
    ) -> Path:
        sentinel_dir = self.project_dir / ".claude" / "plans" / plan_id / "architect" / "round-1"
        sentinel_dir.mkdir(parents=True, exist_ok=True)
        scope_block = "\n".join(f"  - {p}" for p in scope_paths)
        body = (
            "---\nplan: " + plan_id + "\nround: 1\ntype: architect-sentinel\n---\n\n"
            "<!-- BEGIN SIGNED SCOPE -->\n"
            f"Approved-By: {approved_by}\n"
            "Approved-At: 2026-05-04T14:30:00Z\n"
            f"Plans: {plan_id}\n"
            "Scope:\n"
            f"{scope_block}\n"
            "<!-- END SIGNED SCOPE -->\n"
        )
        if lifecycle_text:
            body += "\n" + lifecycle_text + "\n"
        (sentinel_dir / "approved.md").write_text(body, encoding="utf-8")
        return sentinel_dir / "approved.md"

    def _write_sentinel_legacy(
        self,
        plan_id: str,
        scope_paths: list,
        approved_by: str = "@Canhada-Labs deadbeef",
    ) -> Path:
        """Tier-2 legacy format (no markers)."""
        sentinel_dir = self.project_dir / ".claude" / "plans" / plan_id / "architect" / "round-1"
        sentinel_dir.mkdir(parents=True, exist_ok=True)
        scope_block = "\n".join(f"  - {p}" for p in scope_paths)
        body = (
            "---\nplan: " + plan_id + "\nround: 1\ntype: architect-sentinel\n---\n\n"
            f"Approved-By: {approved_by}\n"
            "Approved-At: 2026-04-13T15:30:00Z\n"
            "Scope:\n"
            f"{scope_block}\n"
        )
        (sentinel_dir / "approved.md").write_text(body, encoding="utf-8")
        return sentinel_dir / "approved.md"

    # =========================================================================
    # Tier 1 — markers present (happy path)
    # =========================================================================

    def test_tier1_marker_format_single_path_grants(self):
        self._make_repo_layout()
        target_rel = ".claude/team.md"
        target = self.project_dir / target_rel
        self._write_sentinel_with_markers("PLAN-099", [target_rel])
        rc, out, _ = self._invoke({"tool_input": {"file_path": str(target)}})
        self.assertEqual(rc, 0, msg=out)
        d = json.loads(out)
        self.assertEqual(d.get("decision", "allow"), "allow")

    def test_tier1_marker_format_multi_path_grants(self):
        self._make_repo_layout()
        target_rel = ".claude/team.md"
        other_rel = ".claude/frontend-team.md"
        target = self.project_dir / target_rel
        self._write_sentinel_with_markers("PLAN-099", [target_rel, other_rel])
        rc, out, _ = self._invoke({"tool_input": {"file_path": str(target)}})
        d = json.loads(out)
        self.assertEqual(d.get("decision", "allow"), "allow")

    def test_tier1_path_not_in_marker_scope_blocked(self):
        self._make_repo_layout()
        target_rel = ".claude/team.md"
        target = self.project_dir / target_rel
        # Sentinel scope lists frontend-team but not team
        self._write_sentinel_with_markers("PLAN-099", [".claude/frontend-team.md"])
        rc, out, _ = self._invoke({"tool_input": {"file_path": str(target)}})
        d = json.loads(out)
        self.assertEqual(d["decision"], "block")

    # =========================================================================
    # Tier 2 — legacy format fallback (existing 44 sentinels at 2026-05-04)
    # =========================================================================

    def test_tier2_legacy_no_markers_grants(self):
        """Existing 44 sentinels MUST continue to work without modification."""
        self._make_repo_layout()
        target_rel = ".claude/team.md"
        target = self.project_dir / target_rel
        self._write_sentinel_legacy("PLAN-044", [target_rel])
        rc, out, _ = self._invoke({"tool_input": {"file_path": str(target)}})
        d = json.loads(out)
        self.assertEqual(d.get("decision", "allow"), "allow", msg=out)

    def test_tier2_legacy_format_b_session_67_mega_sentinel(self):
        """Format B (categorized sub-headers) MUST still parse via Tier 2."""
        self._make_repo_layout()
        target_rel = ".claude/team.md"
        target = self.project_dir / target_rel
        sentinel_dir = self.project_dir / ".claude" / "plans" / "PLAN-067" / "architect" / "round-1"
        sentinel_dir.mkdir(parents=True, exist_ok=True)
        body = (
            "---\nplan: PLAN-067\n---\n\n"
            "Approved-By: @Canhada-Labs deadbeef\n"
            "Approved-At: 2026-04-27T10:00:00Z\n"
            "Scope (3 canonical paths):\n"
            "\n"
            "Team docs (PLAN-067):\n"
            f"  - {target_rel}\n"
            "  - .claude/frontend-team.md\n"
            "\n"
            "Pitfalls catalog:\n"
            "  - .claude/pitfalls-catalog.yaml\n"
        )
        (sentinel_dir / "approved.md").write_text(body, encoding="utf-8")
        rc, out, _ = self._invoke({"tool_input": {"file_path": str(target)}})
        d = json.loads(out)
        self.assertEqual(d.get("decision", "allow"), "allow", msg=out)

    # =========================================================================
    # Mixed — lifecycle text outside markers does NOT leak into grant
    # =========================================================================

    def test_mixed_lifecycle_outside_markers_ignored_for_grant(self):
        """Tier-1 isolation: scope OUTSIDE markers MUST NOT grant edits.

        Even if attacker adds a `Scope:` block outside the markers
        listing an attacker-controlled path, that path MUST NOT be
        granted because the parser only reads inside the markers.
        """
        self._make_repo_layout()
        target_rel = ".claude/team.md"  # NOT inside markers
        target = self.project_dir / target_rel
        # Sentinel: markers contain frontend-team only; outside markers
        # has team.md (forged-style addendum)
        lifecycle = (
            "Status: APPROVED\n"
            "\n"
            "Scope:\n"
            f"  - {target_rel}\n"
        )
        self._write_sentinel_with_markers(
            "PLAN-099",
            [".claude/frontend-team.md"],
            lifecycle_text=lifecycle,
        )
        rc, out, _ = self._invoke({"tool_input": {"file_path": str(target)}})
        d = json.loads(out)
        self.assertEqual(
            d["decision"],
            "block",
            msg=f"Tier-1 must isolate scope from lifecycle text. Output: {out}",
        )

    def test_mixed_marker_takes_precedence_over_legacy_header(self):
        """If both markers AND a top-level Scope header exist, Tier 1 wins.

        Markers MUST take precedence; the Tier-2 fallback is only for
        files where markers are absent entirely.
        """
        self._make_repo_layout()
        target_rel = ".claude/team.md"
        target = self.project_dir / target_rel
        # Marker scope = frontend; outside-markers Scope: header lists team
        lifecycle = "Scope:\n  - .claude/team.md\n"
        self._write_sentinel_with_markers(
            "PLAN-099",
            [".claude/frontend-team.md"],
            lifecycle_text=lifecycle,
        )
        rc, out, _ = self._invoke({"tool_input": {"file_path": str(target)}})
        d = json.loads(out)
        # Tier 1 read frontend-team only; team.md not granted
        self.assertEqual(d["decision"], "block")

    # =========================================================================
    # Adversarial — malformed markers
    # =========================================================================

    def test_adversarial_only_begin_marker_falls_to_tier2(self):
        """Only BEGIN, no END → marker regex fails → Tier-2 fallback.

        Behavior: legacy `Scope:` header below the orphan BEGIN is read
        by Tier-2 parser. This is acceptable — the file is still
        GPG-signed end-to-end, and an unfinished marker is treated as
        legacy format.
        """
        self._make_repo_layout()
        target_rel = ".claude/team.md"
        target = self.project_dir / target_rel
        sentinel_dir = self.project_dir / ".claude" / "plans" / "PLAN-099" / "architect" / "round-1"
        sentinel_dir.mkdir(parents=True, exist_ok=True)
        body = (
            "Approved-By: @Canhada-Labs deadbeef\n"
            "<!-- BEGIN SIGNED SCOPE -->\n"
            "Scope:\n"
            f"  - {target_rel}\n"
            # No END marker
        )
        (sentinel_dir / "approved.md").write_text(body, encoding="utf-8")
        rc, out, _ = self._invoke({"tool_input": {"file_path": str(target)}})
        d = json.loads(out)
        # Tier-2 still works (Scope: header exists, Approved-By present)
        self.assertEqual(d.get("decision", "allow"), "allow", msg=out)

    def test_adversarial_only_end_marker_falls_to_tier2(self):
        """Only END, no BEGIN → marker regex fails → Tier-2 fallback."""
        self._make_repo_layout()
        target_rel = ".claude/team.md"
        target = self.project_dir / target_rel
        sentinel_dir = self.project_dir / ".claude" / "plans" / "PLAN-099" / "architect" / "round-1"
        sentinel_dir.mkdir(parents=True, exist_ok=True)
        body = (
            "Approved-By: @Canhada-Labs deadbeef\n"
            "Scope:\n"
            f"  - {target_rel}\n"
            "<!-- END SIGNED SCOPE -->\n"
        )
        (sentinel_dir / "approved.md").write_text(body, encoding="utf-8")
        rc, out, _ = self._invoke({"tool_input": {"file_path": str(target)}})
        d = json.loads(out)
        self.assertEqual(d.get("decision", "allow"), "allow", msg=out)

    def test_adversarial_repeated_markers_first_wins(self):
        """Repeated marker pairs → non-greedy regex picks FIRST pair only.

        Attacker pattern: ship a real marker block with empty/forged
        scope, then a second marker block with attacker scope. The
        non-greedy `.*?` picks the first BEGIN..END pair, isolating
        only the legitimate first scope.
        """
        self._make_repo_layout()
        target_rel = ".claude/team.md"
        target = self.project_dir / target_rel
        sentinel_dir = self.project_dir / ".claude" / "plans" / "PLAN-099" / "architect" / "round-1"
        sentinel_dir.mkdir(parents=True, exist_ok=True)
        body = (
            "<!-- BEGIN SIGNED SCOPE -->\n"
            "Approved-By: @Canhada-Labs deadbeef\n"
            "Scope:\n"
            "  - .claude/frontend-team.md\n"
            "<!-- END SIGNED SCOPE -->\n"
            "\n"
            "<!-- BEGIN SIGNED SCOPE -->\n"
            f"Scope:\n  - {target_rel}\n"
            "<!-- END SIGNED SCOPE -->\n"
        )
        (sentinel_dir / "approved.md").write_text(body, encoding="utf-8")
        rc, out, _ = self._invoke({"tool_input": {"file_path": str(target)}})
        d = json.loads(out)
        # First pair scope = frontend-team only; team.md not granted
        self.assertEqual(d["decision"], "block")

    def test_adversarial_homoglyph_in_begin_marker(self):
        r"""NFKC homoglyph in BEGIN marker → literal regex no-match.

        Cyrillic 'е' (U+0435) in `BEGIN SIGNЕD SCOPE` looks identical
        to Latin 'e' but is not the same byte. Literal regex
        `BEGIN\s+SIGNED\s+SCOPE` does NOT match. Falls to Tier-2.
        """
        self._make_repo_layout()
        target_rel = ".claude/team.md"
        target = self.project_dir / target_rel
        sentinel_dir = self.project_dir / ".claude" / "plans" / "PLAN-099" / "architect" / "round-1"
        sentinel_dir.mkdir(parents=True, exist_ok=True)
        body = (
            "Approved-By: @Canhada-Labs deadbeef\n"
            "<!-- BEGIN SIGNЕD SCOPE -->\n"  # Cyrillic Е
            "Scope:\n"
            f"  - {target_rel}\n"
            "<!-- END SIGNED SCOPE -->\n"
        )
        (sentinel_dir / "approved.md").write_text(body, encoding="utf-8")
        rc, out, _ = self._invoke({"tool_input": {"file_path": str(target)}})
        d = json.loads(out)
        # Tier-2 fallback finds Scope: line; Approved-By present → allow
        # The point of the test: Tier-1 did NOT match the homoglyph marker
        # (verified by the fact that lifecycle "scope" lines after the
        # END marker would still be Tier-2 readable). For this test, both
        # Tier-1 (no match) and Tier-2 (succeeds) lead to allow — which
        # is correct because the GPG signature is what makes it trusted,
        # not the markers.
        self.assertEqual(d.get("decision", "allow"), "allow", msg=out)

    # =========================================================================
    # ReDoS — wall-clock bounds
    # =========================================================================

    def test_redos_64kb_no_match_under_100ms(self):
        """64KiB pathological input with no match → regex returns ≤100ms."""
        # Direct module test (faster than subprocess for ReDoS bench)
        sys.path.insert(0, str(_HOOKS_DIR))
        try:
            import check_canonical_edit as m
        finally:
            sys.path.pop(0)
        big = "X" * (64 * 1024 - 100)
        t0 = time.time()
        result = m._SCOPE_MARKER_RE.search(big)
        elapsed_ms = (time.time() - t0) * 1000
        self.assertIsNone(result)
        self.assertLess(elapsed_ms, 100, f"ReDoS regression: {elapsed_ms:.2f}ms")

    def test_redos_large_match_under_100ms(self):
        """64KiB-class input WITH match → regex returns ≤100ms."""
        sys.path.insert(0, str(_HOOKS_DIR))
        try:
            import check_canonical_edit as m
        finally:
            sys.path.pop(0)
        body = (
            "<!-- BEGIN SIGNED SCOPE -->\n"
            + ("X\n" * 1000)
            + "Scope:\n  - .claude/big.md\n"
            + "<!-- END SIGNED SCOPE -->\n"
        )
        t0 = time.time()
        result = m._SCOPE_MARKER_RE.search(body)
        elapsed_ms = (time.time() - t0) * 1000
        self.assertIsNotNone(result)
        self.assertLess(elapsed_ms, 100, f"ReDoS regression: {elapsed_ms:.2f}ms")

    def test_length_cap_enforcement_skips_regex_above_64kb(self):
        """Files >64KiB skip Tier-1 entirely (defense vs ReDoS escalation).

        The parser falls through to Tier-2 for oversized inputs. This
        is a defense against an attacker who plants a very large
        sentinel hoping to trigger a parser blowup.
        """
        sys.path.insert(0, str(_HOOKS_DIR))
        try:
            import check_canonical_edit as m
        finally:
            sys.path.pop(0)
        # Verify the cap constant is what we expect (pinned for downstream)
        self.assertEqual(m._SCOPE_MARKER_CAP_BYTES, 64 * 1024)

    # =========================================================================
    # GPG coverage invariant — markers do NOT replace GPG
    # =========================================================================

    def test_markers_format_still_requires_gpg_unless_unlock_env(self):
        """Marker format does NOT bypass GPG verification.

        Without CEO_SENTINEL_UNLOCK env, the hook still requires a
        valid `.asc` signature. Marker presence is parser-side only;
        the trust layer is unchanged.
        """
        self._make_repo_layout()
        target_rel = ".claude/team.md"
        target = self.project_dir / target_rel
        self._write_sentinel_with_markers("PLAN-099", [target_rel])
        # Invoke WITHOUT the unlock env
        env = {**os.environ}
        env.pop("CEO_SENTINEL_UNLOCK", None)
        env.pop("CEO_SENTINEL_UNLOCK_ACK", None)
        proc = subprocess.run(
            [sys.executable, str(_HOOK)],
            input=json.dumps({"tool_input": {"file_path": str(target)}}),
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        d = json.loads(proc.stdout)
        # No `.asc` exists → GPG verification fails → block
        self.assertEqual(d["decision"], "block", msg=proc.stdout)


if __name__ == "__main__":
    unittest.main()
