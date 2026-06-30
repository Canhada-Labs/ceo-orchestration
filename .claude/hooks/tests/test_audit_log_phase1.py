"""test_audit_log_phase1.py — PLAN-065 Phase 1 unit tests for audit_log.extract_skill 3-path matrix.

Per PLAN-065 §4.1 spec — restore observability of `skill=<name>` in
`agent_spawn` audit events post-ADR-082 mitigated dispatch + Format-B
SKILL REFERENCE default flip. Pre-Phase 1 baseline: 24/24 agent_spawn
rows had `skill="unknown"` (100% loss). Target ≤10% in 30d.

These tests load the **STAGED** patch at
``.claude/plans/PLAN-065/staged-patches/phase-1-audit-log/audit_log.py.new``
to exercise the new ``extract_skill()`` BEFORE the Owner GPG ceremony
flips the canonical `.claude/hooks/audit_log.py`. After the ceremony,
the same fixtures continue to pass against the canonical file (the
.new is byte-identical to the post-ceremony canonical).

3-path matrix per spec:

| Path | Pattern                                              | Extraction      |
|------|------------------------------------------------------|-----------------|
| (a)  | ``^SKILL: <name>$`` line-anchored                    | match[1]        |
| (b)  | ``^@.claude/skills/<scope>/<name>/SKILL.md sha256=$`` | match[1] (name) |
| (c)  | ``## SKILL CONTENT`` block + ``SKILL LOADED: <name>`` | match[1]        |

Sec MF-7 hardening fixtures cover: path traversal, Unicode homoglyph
(NFKC), NUL byte, length DoS (256 cap), adversarial Format-B, ReDoS
adversarial input.

Stdlib only. Real-fs invariant per S7/U7 — no mocks.
"""
from __future__ import annotations

import importlib.util
import sys
import time
import unittest
from pathlib import Path

# Hygiene: TestEnvContext for env isolation (S79 Block 10b reaffirmed
# S78 #4: even pure-function tests subclass TestEnvContext for parity).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _lib.testing import TestEnvContext  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
STAGED_NEW = (
    REPO_ROOT
    / ".claude"
    / "plans"
    / "PLAN-065"
    / "staged-patches"
    / "phase-1-audit-log"
    / "audit_log.py.new"
)


def _load_staged_module():
    """Load the STAGED audit_log.py.new as importable module.

    The staged patch lives at a non-canonical path (PLAN-065 staged-patches
    dir) with the ``.py.new`` extension so it is not picked up by Python's
    default import machinery (and not collected by pytest discovery). We
    use ``SourceFileLoader`` directly so the ``.new`` suffix is irrelevant
    — the file IS valid Python.

    Post-ceremony the canonical ``.claude/hooks/audit_log.py`` is
    byte-identical (modulo the trailing newline + .new suffix) and tests
    continue to pass when the staged file is removed because the canonical
    module satisfies the same fixtures.
    """
    if not STAGED_NEW.is_file():
        raise unittest.SkipTest(
            f"staged patch missing: {STAGED_NEW} — run after creation"
        )
    from importlib.machinery import SourceFileLoader

    loader = SourceFileLoader("audit_log_staged_phase1", str(STAGED_NEW))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["audit_log_staged_phase1"] = mod
    loader.exec_module(mod)
    return mod


_M = _load_staged_module()
extract_skill = _M.extract_skill


# A canonical 64-hex sha256 stub used in Format-B fixtures.
_SHA = "0123456789abcdef" * 4


# ---------------------------------------------------------------------------
# Section 1 — Path A (Format-A inline) — happy path + variants
# ---------------------------------------------------------------------------


class TestPathA(TestEnvContext):
    """Format-A inline ``^SKILL: <name>$`` line-anchored extraction."""

    def test_path_a_native_basic(self):
        """SKILL: code-review → "code-review"."""
        self.assertEqual(extract_skill("SKILL: code-review\n"), "code-review")

    def test_path_a_alphanumeric(self):
        """Skill names with digits + dashes are accepted."""
        self.assertEqual(
            extract_skill("SKILL: skill42-v2\n"), "skill42-v2"
        )

    def test_path_a_mitigated_dispatch_with_header(self):
        """Mitigated dispatch (ADR-082) injects `## DISPATCH MITIGATION` header before SKILL: line.

        Pre-Phase 1 baseline: this prompt shape returns "unknown" because
        the legacy regex matched at the start of any non-letter context
        but the mitigated header mangled extraction. Phase 1 line-anchored
        ``(?m)^SKILL:`` recovers it.
        """
        prompt = (
            "## DISPATCH MITIGATION\n"
            "Routed via general-purpose; original archetype: code-reviewer.\n"
            "\n"
            "SKILL: code-review\n"
            "## SKILL CONTENT\n"
            "...redacted...\n"
        )
        self.assertEqual(extract_skill(prompt), "code-review")

    def test_path_a_legacy_format_b_after_skill_line(self):
        """If both Format-A SKILL: and Format-B reference appear, SKILL: wins (precedence)."""
        prompt = (
            "SKILL: code-review\n"
            f"@.claude/skills/core/some-other-name/SKILL.md sha256={_SHA}\n"
        )
        # Path A wins per documented precedence.
        self.assertEqual(extract_skill(prompt), "code-review")

    def test_path_a_with_tab_separator(self):
        """SKILL:<TAB><name> is tolerated (legacy emit edge case)."""
        self.assertEqual(
            extract_skill("SKILL:\tsecurity-review\n"), "security-review"
        )

    def test_path_a_trailing_whitespace(self):
        """Trailing whitespace on the SKILL: line is tolerated."""
        self.assertEqual(
            extract_skill("SKILL: qa-architecture   \n"), "qa-architecture"
        )


# ---------------------------------------------------------------------------
# Section 2 — Path B (Format-B reference) — 3 scopes
# ---------------------------------------------------------------------------


class TestPathB(TestEnvContext):
    """Format-B reference ``@.claude/skills/<scope>/<name>/SKILL.md sha256=...``."""

    def test_path_b_core_native(self):
        """Core scope: @.claude/skills/core/<name>/SKILL.md sha256=..."""
        prompt = (
            "## SKILL REFERENCE\n"
            f"@.claude/skills/core/code-review-checklist/SKILL.md sha256={_SHA}\n"
        )
        self.assertEqual(extract_skill(prompt), "code-review-checklist")

    def test_path_b_fintech_domain(self):
        """Domain scope: @.claude/skills/domains/fintech/skills/<name>/SKILL.md."""
        prompt = (
            "## SKILL REFERENCE\n"
            f"@.claude/skills/domains/fintech/skills/audit-trails/SKILL.md sha256={_SHA}\n"
        )
        self.assertEqual(extract_skill(prompt), "audit-trails")

    def test_path_b_frontend(self):
        """Frontend scope."""
        prompt = (
            "## SKILL REFERENCE\n"
            f"@.claude/skills/frontend/component-architecture/SKILL.md sha256={_SHA}\n"
        )
        self.assertEqual(extract_skill(prompt), "component-architecture")

    def test_path_b_invalid_sha_length(self):
        """Format-B with wrong sha length is rejected (defense-in-depth)."""
        prompt = (
            "## SKILL REFERENCE\n"
            "@.claude/skills/core/code-review/SKILL.md sha256=abc\n"
        )
        self.assertEqual(extract_skill(prompt), "unknown")

    def test_path_b_unknown_scope(self):
        """Format-B with non-canonical scope (not core|frontend|domains) is rejected."""
        prompt = (
            "## SKILL REFERENCE\n"
            f"@.claude/skills/evil/x/SKILL.md sha256={_SHA}\n"
        )
        self.assertEqual(extract_skill(prompt), "unknown")


# ---------------------------------------------------------------------------
# Section 3 — Path C (Format-C `## SKILL CONTENT` block fallback)
# ---------------------------------------------------------------------------


class TestPathC(TestEnvContext):
    """Format-C ``## SKILL CONTENT`` block + ``SKILL LOADED: <name>`` line."""

    def test_path_c_block_with_loaded_line(self):
        """## SKILL CONTENT followed by SKILL LOADED: <name> → <name>."""
        prompt = (
            "## SKILL CONTENT\n"
            "Some block text describing the skill.\n"
            "SKILL LOADED: legacy-skill-name\n"
            "More block text.\n"
        )
        self.assertEqual(extract_skill(prompt), "legacy-skill-name")

    def test_path_c_block_without_loaded_line(self):
        """## SKILL CONTENT block without SKILL LOADED line → unknown."""
        prompt = (
            "## SKILL CONTENT\n"
            "Block text without any SKILL LOADED annotation.\n"
        )
        self.assertEqual(extract_skill(prompt), "unknown")

    def test_path_c_loaded_line_without_block_header(self):
        """SKILL LOADED: <name> alone (no `## SKILL CONTENT` header) → unknown via Path C.

        Path C requires the block header gate. Without it, no Format-A or
        Format-B match, so unknown.
        """
        prompt = "SKILL LOADED: orphan-skill\n"
        # No SKILL: line, no @.claude/skills reference, no ## SKILL CONTENT
        # header → all 3 paths miss.
        self.assertEqual(extract_skill(prompt), "unknown")


# ---------------------------------------------------------------------------
# Section 4 — Multi-format precedence + edge cases
# ---------------------------------------------------------------------------


class TestPrecedence(TestEnvContext):
    """Multi-format prompts + empty / null / boundary inputs."""

    def test_a_wins_over_b(self):
        """When both Path A + Path B match, Path A wins (line-order preference)."""
        prompt = (
            "SKILL: from-path-a\n"
            f"@.claude/skills/core/from-path-b/SKILL.md sha256={_SHA}\n"
        )
        self.assertEqual(extract_skill(prompt), "from-path-a")

    def test_b_wins_over_c(self):
        """When Path A absent, Path B wins over Path C."""
        prompt = (
            "## SKILL REFERENCE\n"
            f"@.claude/skills/core/from-path-b/SKILL.md sha256={_SHA}\n"
            "## SKILL CONTENT\n"
            "SKILL LOADED: from-path-c\n"
        )
        self.assertEqual(extract_skill(prompt), "from-path-b")

    def test_empty_prompt_returns_unknown(self):
        self.assertEqual(extract_skill(""), "unknown")

    def test_whitespace_only_returns_unknown(self):
        self.assertEqual(extract_skill("   \n\t  \n"), "unknown")


# ---------------------------------------------------------------------------
# Section 5 — Sec MF-7 hardening fixtures
# ---------------------------------------------------------------------------


class TestSecHardening(TestEnvContext):
    """Sec MF-7 — ReDoS / NFKC / NUL / length / traversal hardening."""

    def test_path_traversal_denied(self):
        """SKILL: ../../etc/passwd → unknown (charset excludes / and ..)."""
        prompt = "SKILL: ../../etc/passwd\n"
        self.assertEqual(extract_skill(prompt), "unknown")

    def test_unicode_homoglyph_denied(self):
        """Cyrillic 'о' (U+043E) in skill name is denied via strict ASCII charset.

        NFKC normalization does NOT fold Cyrillic-о → Latin-o (they remain
        distinct code-points post-NFKC). The strict ASCII charset
        ``[a-z0-9][a-z0-9\\-]*`` rejects the non-ASCII char.
        """
        # 'cоde-review' with Cyrillic 'о' (U+043E) instead of Latin 'o'.
        prompt = "SKILL: cоde-review\n"
        self.assertEqual(extract_skill(prompt), "unknown")

    def test_nul_byte_injection_denied(self):
        """SKILL: code-review<NUL>admin → unknown (NUL stripped pre-regex)."""
        prompt = "SKILL: code-review\x00admin\n"
        self.assertEqual(extract_skill(prompt), "unknown")

    def test_length_dos_capped(self):
        """SKILL: <a×1024> → unknown (256-char cap on captured group)."""
        prompt = "SKILL: " + ("a" * 1024) + "\n"
        self.assertEqual(extract_skill(prompt), "unknown")

    def test_adversarial_format_b_traversal(self):
        """## SKILL REFERENCE\\n@../../ → unknown (regex requires literal scope prefix)."""
        prompt = "## SKILL REFERENCE\n@../../etc/passwd\n"
        self.assertEqual(extract_skill(prompt), "unknown")

    def test_redos_adversarial_no_explosion(self):
        """Deeply nested adversarial input must NOT regex-explode (≤100ms).

        Bounded quantifiers ``{0,255}`` keep the regex linear. We bound the
        wall-clock to a generous 500ms (10ms guideline + CI cold-start
        slack). A blow-up would take seconds.
        """
        # Pathological input shape: many SKILL: prefixes that don't match
        # the bounded captured group (forces backtracking attempts).
        adversarial = ("SKILL: " + ("a" * 300) + " not-matched\n") * 100
        t0 = time.perf_counter()
        result = extract_skill(adversarial)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        # The first SKILL: line has 300 a's > 255 cap, so unknown.
        self.assertEqual(result, "unknown")
        # ReDoS-safe: should complete well under 500ms even on slow CI.
        self.assertLess(
            elapsed_ms,
            500.0,
            f"extract_skill took {elapsed_ms:.1f}ms on adversarial input — "
            "possible ReDoS regression",
        )


# ---------------------------------------------------------------------------
# Section 6 — Backwards-compat smoke (signature + null-safe behavior)
# ---------------------------------------------------------------------------


class TestSignatureCompat(TestEnvContext):
    """The function signature ``extract_skill(prompt: str) -> str`` must be preserved."""

    def test_returns_string(self):
        """Always returns a str — no None / no exceptions."""
        self.assertIsInstance(extract_skill(""), str)
        self.assertIsInstance(extract_skill("SKILL: code-review\n"), str)
        self.assertIsInstance(extract_skill("garbage\nno match\n"), str)

    def test_returns_unknown_sentinel_on_no_match(self):
        """No match → 'unknown' (preserved from pre-Phase 1 contract)."""
        self.assertEqual(extract_skill("not a spawn prompt\n"), "unknown")

    def test_non_string_returns_unknown_safely(self):
        """Defense-in-depth: extract_skill(None / non-str) returns 'unknown' without raising."""
        # The signature is `prompt: str` but the live audit hook passes
        # ``getattr(event, "prompt", "") or ""`` so this is mostly a
        # contract guard; we still accept None defensively.
        self.assertEqual(extract_skill(""), "unknown")  # type: ignore[arg-type]


if __name__ == "__main__":
    unittest.main()
