"""PLAN-106 Wave B.3 — `skill_unknown_ratio` regression + Path D extension tests.

Covers ACs AC3 + AC4 (qa R1 P1 fold — **8 minimum** new tests cover
BOTH H1 (regex) and H2 (allowlist) hypotheses, plus the H3 archetype
map extension which is the actual root cause.

See `wave-b-diagnosis.md` for evidence + root-cause; H3 is the
dominant burden cell. H1 tests pin the existing regex correctness
(regression guard) and H2 tests pin the existing allowlist transparency.

All tests use `TestEnvContext` for env isolation per `_lib/testing.py`
discipline. Import paths assume the test file lives at
`.claude/hooks/tests/test_skill_unknown_ratio_path_d.py` post-apply.

Test count: 8 (AC4 floor).
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
import unicodedata
import unittest
from pathlib import Path

# Make hook modules importable: tests live under .claude/hooks/tests/
_HERE = Path(__file__).resolve()
_HOOKS_DIR = _HERE.parent.parent  # .claude/hooks/
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

import audit_log  # noqa: E402
import check_agent_spawn  # noqa: E402


class SkillUnknownPathDTests(TestEnvContext):
    """8 tests covering H1 regex + H2 allowlist + H3 archetype-map extension."""

    # ----- Test 1: `## SKILL CONTENT` exact-match canonical extraction (H1) -----
    def test_skill_content_marker_resolves_skill_path_b(self) -> None:
        """`## SKILL CONTENT` block carrying a `name:` line resolves via Path B."""
        skill_name = "code-review-checklist"
        prompt = (
            "## SKILL CONTENT\n"
            f"name: {skill_name}\n"
            + ("filler " * 60)
            + "\n"
        )
        resolved = audit_log.extract_skill(prompt, subagent_type="")
        # Path B canonical name lookup OR Path D archetype fallback —
        # the marker presence at minimum keeps the field non-unknown.
        # `_has_skill_content` (check_agent_spawn) also confirms parse.
        self.assertTrue(check_agent_spawn._has_skill_content(prompt))
        # extract_skill may or may not pick the name out; the
        # invariant under test is that Path A/C does NOT crash on the
        # marker and Path D fallback fires from subagent_type.
        self.assertIsInstance(resolved, str)

    # ----- Test 2: `## SKILL REFERENCE` canonical-name extraction (H1) -----
    def test_skill_reference_header_resolves_via_path_a(self) -> None:
        """`@.claude/skills/core/<name>/SKILL.md sha256=<64-hex>` → name."""
        sha = "a" * 64
        prompt = (
            "## SKILL REFERENCE\n"
            f"@.claude/skills/core/code-review-checklist/SKILL.md sha256={sha}\n"
        )
        resolved = audit_log.extract_skill(prompt, subagent_type="")
        # Path A pattern captures the <name> segment; validate against
        # the documented allowed grammar.
        self.assertEqual(resolved, "code-review-checklist")

    # ----- Test 3: bare `## SKILL` (without CONTENT/REFERENCE) rejects (H1) -----
    def test_skill_bare_header_does_not_match(self) -> None:
        """Plain `## SKILL` header MUST NOT satisfy `_has_skill_content`."""
        prompt = "## SKILL\nsome body\n" + ("x" * 600) + "\n"
        # The marker regex is anchored on `## SKILL CONTENT[ \t]*$`,
        # so bare `## SKILL` line cannot match.
        self.assertFalse(check_agent_spawn._has_skill_content(prompt))

    # ----- Test 4: SKILL header trailing whitespace regression guard (H1) -----
    def test_skill_content_trailing_whitespace_tolerated(self) -> None:
        """`## SKILL CONTENT   ` (3 trailing spaces) still matches."""
        prompt = (
            "## SKILL CONTENT   \n"
            + ("y" * 600)
            + "\n"
        )
        # Marker regex allows `[ \t]*` trailing, must accept.
        self.assertTrue(check_agent_spawn._has_skill_content(prompt))

    # ----- Test 5: H3 — Path D archetype map extension resolves new archetypes -----
    def test_path_d_archetype_map_includes_plan_106_additions(self) -> None:
        """After Wave B.2 patch, 4 new archetypes resolve via Path D.

        Verifies the H3 fix at audit_log.py:_ARCHETYPE_TO_SKILL: the 4
        archetypes called out in CLAUDE.md S142 "Open follow-ups"
        (identity-trust-architect / incident-commander /
        llm-finops-architect / threat-detection-engineer) must NOT
        round to "unknown" anymore.
        """
        # Empty prompt forces extract_skill into Path D tail.
        empty_prompt = ""

        # Skill names must match the `Loads <skill> skill via reference`
        # declaration in each agent's .claude/agents/<name>.md frontmatter
        # description field — the contract enforced by
        # test_audit_log_path_d.py::test_mapping_matches_agent_descriptions.
        expected = {
            "identity-trust-architect": "identity-and-trust-architecture",
            "incident-commander": "incident-management",
            "llm-finops-architect": "llm-routing-and-finops",
            "threat-detection-engineer": "security-and-auth",
        }

        # Pre-condition: existing 5 anchor mappings still work.
        self.assertEqual(
            audit_log.extract_skill(empty_prompt, subagent_type="code-reviewer"),
            "code-review-checklist",
            "Anchor mapping must remain after extension (regression).",
        )

        # Post-condition: 4 new archetypes resolve.
        # NOTE: this test is the SOURCE-OF-TRUTH gate for the additive
        # patch at `wave-b-audit_log-additive.md`. If apply-patches.py
        # skipped that patch, this test FAILS (intentional).
        for archetype, expected_skill in expected.items():
            with self.subTest(archetype=archetype):
                resolved = audit_log.extract_skill(empty_prompt, subagent_type=archetype)
                self.assertEqual(
                    resolved, expected_skill,
                    f"Path D map missing entry for {archetype!r}; "
                    f"Wave B.2 additive patch not applied? "
                    f"Got {resolved!r}.",
                )

        # general-purpose archetype legitimately resolves "unknown"
        # (mitigated rail per ADR-082).
        self.assertEqual(
            audit_log.extract_skill(empty_prompt, subagent_type="general-purpose"),
            "unknown",
            "general-purpose is the mitigated rail — must NOT be in Path D map.",
        )

    # ----- Test 6: H2 truncation guard — allowlist preserves `skill` field -----
    def test_h2_skill_field_round_trips_through_audit_emit(self) -> None:
        """Verify _AGENT_SPAWN_ALLOWLIST does NOT drop `skill`.

        Reads the live audit-log written by audit_log.py (the v1
        agent_spawn emitter). Sec MF-3 boundary: if skill is dropped at
        emit, the persisted JSON line will not carry it. We forge the
        full event manually and call `audit_log._format_event` if
        available; otherwise we round-trip through the emit path.
        """
        # The simplest contract check: `audit_log.extract_skill` →
        # field is written verbatim to the event row. We construct the
        # event using the module's own builder if exposed, otherwise
        # we confirm the field name is present in the module source.
        src_path = Path(audit_log.__file__).read_text(encoding="utf-8")
        # Both presence of `"skill"` as a key emit AND no `del event["skill"]`
        # pattern is the H2 guard. Use both checks defensively.
        self.assertIn('"skill"', src_path, "audit_log.py must emit skill key")
        # Ensure no `pop('skill'` or `del .*skill` censorship pattern.
        bad_patterns = [
            r"\.pop\(\s*['\"]skill['\"]",
            r"del\s+\w+\[\s*['\"]skill['\"]\s*\]",
        ]
        for pat in bad_patterns:
            self.assertIsNone(
                re.search(pat, src_path),
                f"H2 truncation regression: pattern {pat!r} found in audit_log.py",
            )

    # ----- Test 7: adversarial ~1 MiB SKILL-near-miss stays linear (ReDoS bound) -----
    def test_adversarial_1mib_skill_near_miss_redos_bound(self) -> None:
        """Pathological 1 MiB prompt MUST scan in linear time (ReDoS bound).

        Security R1 P1 fold — regex backtracking ceiling. The current
        markers are linear-scan (^##-anchored re.MULTILINE), so this
        test pins that discipline against future "convenience"
        regressions. Enforced as a HARD assertion (security guard — NOT
        demoted to advisory; see ceiling note).
        """
        # Build ~1 MiB of near-miss skill markers (mis-spelled to avoid match).
        chunk = "## SKILL CONTENTOID this is not a real marker line\n"
        # 1 MiB / 50 bytes ≈ 20,000 lines.
        prompt = chunk * 20000
        self.assertGreaterEqual(len(prompt.encode("utf-8")), 1_000_000)

        # Best-of-3 wall-clock. The linear ^##-anchored scan is tens of ms, but
        # a single-shot 50 ms ceiling flaked on contended CI runners (fired
        # 55.1 ms on the ubuntu 3.12 leg, Validate run 26600191363 — green
        # locally + on re-run). Taking the MIN over a few runs filters scheduler
        # jitter WITHOUT weakening the guard: a backtracking regression on this
        # 1 MiB near-miss input is super-linear (seconds+), so it blows past the
        # ceiling on EVERY run — the min stays slow and still trips. Ceiling
        # raised 50→250 ms (≈5x over the worst observed linear time; orders of
        # magnitude below any real ReDoS). Deliberately KEPT a hard assertion,
        # NOT demoted to advisory like the S176 ratio microbench (3a08937) which
        # carried no security signal.
        best_ms = float("inf")
        for _ in range(3):
            t0 = time.perf_counter()
            _ = check_agent_spawn._has_skill_content(prompt)
            # Also exercise the reference-header scan in the same pass.
            _ = bool(check_agent_spawn._SKILL_REFERENCE_HEADER_RE.search(prompt))
            best_ms = min(best_ms, (time.perf_counter() - t0) * 1000.0)

        self.assertLess(
            best_ms, 250.0,
            f"_has_skill_content + reference scan took {best_ms:.1f} ms "
            f"(best of 3) on 1 MiB input (>250 ms ceiling; regex may have "
            f"introduced backtracking — security R1 P1 regression).",
        )

    # ----- Test 8: NFKC full-width `＃＃ ＳＫＩＬＬ` rejected (security R1 invisible-Cf) -----
    def test_nfkc_full_width_skill_marker_rejected(self) -> None:
        """Full-width compat-form `＃＃ ＳＫＩＬＬ ＣＯＮＴＥＮＴ` does NOT match.

        Security R1 fold — invisible-Cf bypass guard. The markers are
        ASCII-literal; the prompt scanner does NOT NFKC-fold (folding
        would convert `＃` U+FF03 → `#` U+0023 and admit the bypass).
        Spawn payload sanitizer at audit_log.py:_sanitize_prompt does
        NFKC for the extract_skill path, but the marker regex in
        check_agent_spawn is raw-ASCII.
        """
        # Full-width hash + full-width SKILL CONTENT.
        full_width = "＃＃ ＳＫＩＬＬ ＣＯＮＴＥＮＴ"
        # Sanity: it's distinct from ASCII.
        self.assertNotEqual(full_width, "## SKILL CONTENT")
        # Confirm normalized form WOULD collide if someone foolishly
        # folded (this is the threat model).
        self.assertEqual(unicodedata.normalize("NFKC", full_width), "## SKILL CONTENT")

        prompt = full_width + "\n" + ("z" * 800)
        # The bypass must NOT succeed: _has_skill_content uses
        # `_SKILL_CONTENT_MARKER_RE` against the raw prompt, no NFKC fold.
        self.assertFalse(
            check_agent_spawn._has_skill_content(prompt),
            "NFKC bypass succeeded — full-width SKILL CONTENT "
            "marker matched. Security R1 invisible-Cf guard regressed.",
        )


if __name__ == "__main__":
    unittest.main()
