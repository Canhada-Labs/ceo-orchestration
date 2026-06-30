"""test_extract_skill.py — PLAN-065 Phase 1 unit tests for extract-skill.py.

Per PLAN-065 §4.1 spec:

- 3-path SKILL extraction matrix (Format-A inline / Format-B reference /
  Format-C `## SKILL CONTENT` block)
- ≥3 fixtures per path × 3 paths = ≥9 native/mitigated/legacy
- 6 ReDoS / Sec MF-7 hardening fixtures (timeout-safe within 100ms each)
- Determinism: every fixture has exactly one expected outcome
- Tests floor 102 (R1 adjustment) — covers Phase 1 surface; Phase 6
  conformance harness extends with mutation gate.

Stdlib only. TestEnvContext for any test that uses $HOME / project dir.
This module's tests are pure-function; TestEnvContext is used here for
hygiene parity with sibling test files (S79 closeout lesson).
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
import unittest
from pathlib import Path
from typing import Any

# Hygiene: TestEnvContext for env isolation (S79 lesson — even pure-function
# tests subclass TestEnvContext to ensure no $HOME / $CLAUDE_PROJECT_DIR
# bleed-through if module-level imports ever grow that surface).
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks"))
from _lib.testing import TestEnvContext  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / ".claude" / "scripts" / "extract-skill.py"


def _load_module():
    """Load extract-skill.py as importable module (hyphenated filename)."""
    spec = importlib.util.spec_from_file_location("extract_skill", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["extract_skill"] = mod
    spec.loader.exec_module(mod)
    return mod


_M = _load_module()
extract_skill = _M.extract_skill
extract_skill_cached = _M.extract_skill_cached
extract_many = _M.extract_many
cache_clear = _M.cache_clear
Result = _M.Result


# ---------------------------------------------------------------------------
# Section 1 — Path A (Format-A inline) — happy path + variants (≥10)
# ---------------------------------------------------------------------------


class TestPathA(TestEnvContext):
    """Format-A: ``^SKILL: <name>$`` (line-anchored)."""

    def test_path_a_native_basic(self):
        r = extract_skill("SKILL: code-review\n")
        self.assertEqual(r.skill, "code-review")
        self.assertEqual(r.path, "a")
        self.assertEqual(r.rejected_reason, "")

    def test_path_a_native_alphanumeric(self):
        r = extract_skill("SKILL: skill42-v2\n")
        self.assertEqual(r.skill, "skill42-v2")
        self.assertEqual(r.path, "a")

    def test_path_a_native_single_char(self):
        r = extract_skill("SKILL: a\n")
        self.assertEqual(r.skill, "a")
        self.assertEqual(r.path, "a")

    def test_path_a_mitigated_dispatch_with_header(self):
        # Mitigated dispatch (ADR-082) injects ## DISPATCH MITIGATION before SKILL line
        prompt = (
            "## DISPATCH MITIGATION\n"
            "Routed via general-purpose; original archetype: code-reviewer.\n\n"
            "SKILL: code-review\n"
            "## SKILL CONTENT\n"
            "...redacted...\n"
        )
        r = extract_skill(prompt)
        self.assertEqual(r.skill, "code-review")
        self.assertEqual(r.path, "a")

    def test_path_a_legacy_with_extra_whitespace(self):
        # Legacy emit may use a tab, ensure tolerated
        r = extract_skill("SKILL:\tsecurity-review\n")
        self.assertEqual(r.skill, "security-review")
        self.assertEqual(r.path, "a")

    def test_path_a_legacy_trailing_whitespace(self):
        r = extract_skill("SKILL: qa-architecture   \n")
        self.assertEqual(r.skill, "qa-architecture")

    def test_path_a_first_match_wins(self):
        prompt = "SKILL: code-review\nLater: SKILL: other-skill\n"
        r = extract_skill(prompt)
        self.assertEqual(r.skill, "code-review")

    def test_path_a_inside_codeblock_still_matches(self):
        # PLAN-065 §4.1 grammar choice: line-anchored, no codeblock awareness.
        # This is INTENTIONAL — sub-agent prompts are not user content.
        prompt = "```\nSKILL: code-review\n```\n"
        r = extract_skill(prompt)
        self.assertEqual(r.skill, "code-review")

    def test_path_a_uppercase_name_rejected(self):
        # Grammar is [a-z0-9][a-z0-9-]*; uppercase rejected → falls through to none
        r = extract_skill("SKILL: Code-Review\n")
        self.assertEqual(r.skill, "unknown")
        self.assertEqual(r.path, "none")

    def test_path_a_starting_dash_rejected(self):
        # Grammar requires [a-z0-9] start
        r = extract_skill("SKILL: -leading-dash\n")
        self.assertEqual(r.skill, "unknown")


# ---------------------------------------------------------------------------
# Section 2 — Path B (Format-B reference) — happy path + variants (≥10)
# ---------------------------------------------------------------------------


class TestPathB(TestEnvContext):
    """Format-B: ``^@.claude/skills/<tier>/<name>/SKILL.md sha256=<64-hex>$``."""

    SHA = "a" * 64

    def test_path_b_core_native(self):
        r = extract_skill(f"@.claude/skills/core/code-review/SKILL.md sha256={self.SHA}\n")
        self.assertEqual(r.skill, "code-review")
        self.assertEqual(r.path, "b")

    def test_path_b_frontend_native(self):
        r = extract_skill(f"@.claude/skills/frontend/audit-page/SKILL.md sha256={self.SHA}\n")
        self.assertEqual(r.skill, "audit-page")
        self.assertEqual(r.path, "b")

    def test_path_b_domain_fintech(self):
        r = extract_skill(
            f"@.claude/skills/domains/fintech/skills/payment-rails/SKILL.md sha256={self.SHA}\n"
        )
        self.assertEqual(r.skill, "payment-rails")
        self.assertEqual(r.path, "b")

    def test_path_b_domain_edtech(self):
        r = extract_skill(
            f"@.claude/skills/domains/edtech/skills/quiz-builder/SKILL.md sha256={self.SHA}\n"
        )
        self.assertEqual(r.skill, "quiz-builder")
        self.assertEqual(r.path, "b")

    def test_path_b_mitigated_dispatch_with_header(self):
        prompt = (
            "## DISPATCH MITIGATION\n"
            "Routed via general-purpose; original archetype: vp-engineering.\n\n"
            "## SKILL REFERENCE\n"
            f"@.claude/skills/core/vp-engineering/SKILL.md sha256={self.SHA}\n"
        )
        r = extract_skill(prompt)
        self.assertEqual(r.skill, "vp-engineering")
        self.assertEqual(r.path, "b")

    def test_path_b_legacy_extra_spaces_after_md(self):
        r = extract_skill(
            f"@.claude/skills/core/lesson-review/SKILL.md  sha256={self.SHA}\n"
        )
        # Multiple spaces is NOT in grammar (single-or-tab). Should not match.
        # Grammar uses \s+ between SKILL.md and sha256= — \s matches single+,
        # so this DOES match. Just confirms.
        self.assertEqual(r.skill, "lesson-review")
        self.assertEqual(r.path, "b")

    def test_path_b_invalid_short_sha_rejected(self):
        short = "a" * 63
        r = extract_skill(f"@.claude/skills/core/code-review/SKILL.md sha256={short}\n")
        self.assertEqual(r.skill, "unknown")

    def test_path_b_invalid_long_sha_rejected(self):
        too_long = "a" * 65
        r = extract_skill(f"@.claude/skills/core/code-review/SKILL.md sha256={too_long}\n")
        self.assertEqual(r.skill, "unknown")

    def test_path_b_uppercase_sha_rejected(self):
        r = extract_skill(f"@.claude/skills/core/code-review/SKILL.md sha256={'A' * 64}\n")
        self.assertEqual(r.skill, "unknown")

    def test_path_b_path_traversal_in_skill_name_rejected(self):
        # Attacker sets `<name>` = `../etc/passwd` — rejected by grammar.
        r = extract_skill(
            f"@.claude/skills/core/../etc/passwd/SKILL.md sha256={self.SHA}\n"
        )
        self.assertEqual(r.skill, "unknown")
        self.assertEqual(r.path, "none")


# ---------------------------------------------------------------------------
# Section 3 — Path C (## SKILL CONTENT block + SKILL LOADED line) (≥4)
# ---------------------------------------------------------------------------


class TestPathC(TestEnvContext):
    """Path C — block-with-name fallback (legacy / third-party adapters)."""

    def test_path_c_block_with_name(self):
        prompt = (
            "## AGENT PROFILE\n"
            "code-reviewer\n\n"
            "## SKILL CONTENT\n"
            "SKILL LOADED: code-review\n"
            "...content...\n"
        )
        r = extract_skill(prompt)
        self.assertEqual(r.skill, "code-review")
        self.assertEqual(r.path, "c")

    def test_path_c_block_without_name_returns_unknown(self):
        prompt = (
            "## SKILL CONTENT\n"
            "...content body without SKILL LOADED line...\n"
        )
        r = extract_skill(prompt)
        self.assertEqual(r.skill, "unknown")
        self.assertEqual(r.path, "none")

    def test_path_c_block_without_skill_loaded_marker(self):
        # Block heading present but no SKILL LOADED line → unknown
        prompt = "## SKILL CONTENT\nthis is content\n"
        r = extract_skill(prompt)
        self.assertEqual(r.skill, "unknown")

    def test_path_c_path_a_takes_precedence(self):
        # Both Path A and Path C present → Path A wins
        prompt = (
            "SKILL: payment-rails\n"
            "## SKILL CONTENT\n"
            "SKILL LOADED: code-review\n"
        )
        r = extract_skill(prompt)
        self.assertEqual(r.skill, "payment-rails")
        self.assertEqual(r.path, "a")


# ---------------------------------------------------------------------------
# Section 4 — Sec MF-7 hardening fixtures (≥6) + determinism
# ---------------------------------------------------------------------------


class TestSecurityHardening(TestEnvContext):
    """Sec MF-7 — Path traversal, NUL injection, homoglyph, length DoS, ReDoS."""

    def test_sec_path_traversal_inline(self):
        r = extract_skill("SKILL: ../../etc/passwd\n")
        self.assertEqual(r.skill, "unknown")

    def test_sec_unicode_homoglyph_cyrillic_o(self):
        # Cyrillic 'о' (U+043E) looks like ASCII 'o' but is in different script.
        # NFKC normalizes compat chars but does NOT fold cross-script; grammar
        # rejects on charset.
        r = extract_skill("SKILL: cоde-review\n")
        self.assertEqual(r.skill, "unknown")

    def test_sec_nul_byte_injection_rejected(self):
        r = extract_skill("SKILL: code-review\x00admin\n")
        self.assertEqual(r.skill, "unknown")
        self.assertEqual(r.rejected_reason, "nul_byte")

    def test_sec_oversize_input_rejected(self):
        big = "x" * (_M.MAX_INPUT_CHARS + 1)
        r = extract_skill(big)
        self.assertEqual(r.skill, "unknown")
        self.assertEqual(r.rejected_reason, "oversize")

    def test_sec_skill_name_max_length(self):
        # Grammar caps captured group at 256; 257-char name → no match
        long_name = "a" * 257
        r = extract_skill(f"SKILL: {long_name}\n")
        self.assertEqual(r.skill, "unknown")

    def test_sec_redos_pathological_alternation(self):
        # ReDoS attempt: deeply nested-looking input. Grammar is anchored +
        # bounded, but smoke-test that 100ms budget never breached.
        attacker = "SKILL: " + ("a-" * 1000) + "\n"  # 2001-char name → rejected
        t0 = time.perf_counter()
        r = extract_skill(attacker)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        # 100ms hard budget per spec
        self.assertLess(elapsed_ms, 100.0)
        self.assertEqual(r.skill, "unknown")

    def test_sec_redos_long_input_no_match(self):
        # 999 KiB of garbage → must complete fast and return unknown.
        garbage = "lorem ipsum dolor sit amet " * 30000  # ~810 KiB
        garbage = garbage[: _M.MAX_INPUT_BYTES - 100]
        t0 = time.perf_counter()
        r = extract_skill(garbage)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        self.assertLess(elapsed_ms, 100.0)
        self.assertEqual(r.skill, "unknown")

    def test_sec_path_b_traversal_in_path_segment_rejected(self):
        sha = "a" * 64
        # @.claude/skills/core/../../../etc/passwd/SKILL.md … grammar rejects
        r = extract_skill(
            f"@.claude/skills/core/../../etc/SKILL.md sha256={sha}\n"
        )
        self.assertEqual(r.skill, "unknown")

    def test_sec_empty_string_rejected(self):
        r = extract_skill("")
        self.assertEqual(r.skill, "unknown")
        self.assertEqual(r.rejected_reason, "empty")

    def test_sec_non_string_rejected(self):
        r = extract_skill(None)  # type: ignore[arg-type]
        self.assertEqual(r.skill, "unknown")
        self.assertEqual(r.rejected_reason, "non_string")
        r2 = extract_skill(12345)  # type: ignore[arg-type]
        self.assertEqual(r2.skill, "unknown")
        self.assertEqual(r2.rejected_reason, "non_string")


# ---------------------------------------------------------------------------
# Section 5 — Determinism (back-to-back identical input ⇒ identical output)
# ---------------------------------------------------------------------------


class TestDeterminism(TestEnvContext):
    """PLAN-065 acceptance — every fixture deterministic, not statistical."""

    def test_determinism_path_a(self):
        prompt = "SKILL: code-review\n"
        results = [extract_skill(prompt) for _ in range(5)]
        skills = {r.skill for r in results}
        paths = {r.path for r in results}
        self.assertEqual(skills, {"code-review"})
        self.assertEqual(paths, {"a"})

    def test_determinism_path_b(self):
        sha = "a" * 64
        prompt = f"@.claude/skills/core/lesson-review/SKILL.md sha256={sha}\n"
        results = [extract_skill(prompt) for _ in range(5)]
        skills = {r.skill for r in results}
        self.assertEqual(skills, {"lesson-review"})

    def test_determinism_unknown(self):
        prompt = "lorem ipsum"
        results = [extract_skill(prompt) for _ in range(5)]
        self.assertTrue(all(r.skill == "unknown" for r in results))


# ---------------------------------------------------------------------------
# Section 6 — Cache (--cached / extract_skill_cached)
# ---------------------------------------------------------------------------


class TestCache(TestEnvContext):
    def setUp(self):
        super().setUp()
        cache_clear()

    def test_cache_hit_returns_same_result(self):
        prompt = "SKILL: code-review\n"
        r1 = extract_skill_cached(prompt)
        r2 = extract_skill_cached(prompt)
        self.assertEqual(r1.skill, "code-review")
        self.assertIs(r1, r2)  # cache returns the SAME Result object

    def test_cache_clear(self):
        prompt = "SKILL: code-review\n"
        extract_skill_cached(prompt)
        cache_clear()
        r2 = extract_skill_cached(prompt)
        self.assertEqual(r2.skill, "code-review")
        # After clear, second call is a fresh Result instance
        r3 = extract_skill_cached(prompt)
        self.assertIs(r2, r3)

    def test_cache_eviction_at_bound(self):
        # Force the cache to evict by pushing past _CACHE_MAX_ENTRIES.
        # Smoke-only: confirm no exception, no unbounded growth.
        for i in range(_M._CACHE_MAX_ENTRIES + 50):
            extract_skill_cached(f"SKILL: skill-{i}\n")
        self.assertLessEqual(len(_M._cache), _M._CACHE_MAX_ENTRIES)

    def test_cache_non_string_passes_through(self):
        # Non-string short-circuits to extract_skill (no caching).
        r = extract_skill_cached(None)  # type: ignore[arg-type]
        self.assertEqual(r.skill, "unknown")


# ---------------------------------------------------------------------------
# Section 7 — extract_many (ThreadPoolExecutor parallelism + timeout)
# ---------------------------------------------------------------------------


class TestExtractMany(TestEnvContext):
    def test_extract_many_preserves_order(self):
        prompts = [
            "SKILL: code-review\n",
            "SKILL: lesson-review\n",
            "lorem ipsum",
            "SKILL: payment-rails\n",
        ]
        results = extract_many(prompts, max_workers=2)
        self.assertEqual(len(results), 4)
        self.assertEqual(results[0].skill, "code-review")
        self.assertEqual(results[1].skill, "lesson-review")
        self.assertEqual(results[2].skill, "unknown")
        self.assertEqual(results[3].skill, "payment-rails")

    def test_extract_many_handles_empty(self):
        results = extract_many([], max_workers=4)
        self.assertEqual(results, [])

    def test_extract_many_handles_single(self):
        results = extract_many(["SKILL: code-review\n"], max_workers=4)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].skill, "code-review")

    def test_extract_many_handles_non_string_in_batch(self):
        results = extract_many([None, 123, "SKILL: code-review\n"], max_workers=2)
        self.assertEqual(results[0].skill, "unknown")
        self.assertEqual(results[1].skill, "unknown")
        self.assertEqual(results[2].skill, "code-review")

    def test_extract_many_max_workers_clamped(self):
        # max_workers=0 → forced to 1; should not raise
        results = extract_many(["SKILL: code-review\n"], max_workers=0)
        self.assertEqual(len(results), 1)


# ---------------------------------------------------------------------------
# Section 8 — Result dataclass invariants (frozen, hashable)
# ---------------------------------------------------------------------------


class TestResult(TestEnvContext):
    def test_result_is_frozen(self):
        r = extract_skill("SKILL: code-review\n")
        with self.assertRaises(Exception):
            r.skill = "tampered"  # type: ignore[misc]

    def test_result_fields(self):
        r = extract_skill("SKILL: code-review\n")
        self.assertEqual(r.skill, "code-review")
        self.assertEqual(r.path, "a")
        self.assertEqual(r.rejected_reason, "")
        self.assertGreater(r.duration_ms, 0.0)


# ---------------------------------------------------------------------------
# Section 9 — CLI (subprocess) smoke tests
# ---------------------------------------------------------------------------


class TestCli(TestEnvContext):
    def test_cli_stdin_basic(self):
        import subprocess
        proc = subprocess.run(
            [sys.executable, str(SCRIPT)],
            input="SKILL: code-review\n",
            capture_output=True,
            text=True,
            timeout=5,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout.strip(), "code-review")

    def test_cli_stdin_unknown(self):
        import subprocess
        proc = subprocess.run(
            [sys.executable, str(SCRIPT)],
            input="lorem ipsum",
            capture_output=True,
            text=True,
            timeout=5,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertEqual(proc.stdout.strip(), "unknown")

    def test_cli_json_format(self):
        import subprocess
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--json"],
            input="SKILL: code-review\n",
            capture_output=True,
            text=True,
            timeout=5,
        )
        self.assertEqual(proc.returncode, 0)
        out = json.loads(proc.stdout.strip())
        self.assertEqual(out["skill"], "code-review")
        self.assertEqual(out["path"], "a")
        self.assertIn("duration_ms", out)

    def test_cli_batch_mode(self):
        import subprocess
        import tempfile
        sha = "a" * 64
        with tempfile.NamedTemporaryFile(
            "w", suffix=".jsonl", delete=False
        ) as f:
            f.write(json.dumps({"prompt": "SKILL: code-review\n"}) + "\n")
            f.write(json.dumps({"prompt": f"@.claude/skills/core/lesson-review/SKILL.md sha256={sha}\n"}) + "\n")
            f.write(json.dumps({"prompt": "lorem ipsum"}) + "\n")
            batch = f.name
        try:
            proc = subprocess.run(
                [sys.executable, str(SCRIPT), "--batch", batch],
                capture_output=True, text=True, timeout=5,
            )
            self.assertEqual(proc.returncode, 0)
            lines = proc.stdout.strip().split("\n")
            self.assertEqual(len(lines), 3)
            self.assertTrue(lines[0].startswith("code-review\t"))
            self.assertTrue(lines[1].startswith("lesson-review\t"))
            self.assertTrue(lines[2].startswith("unknown\t"))
        finally:
            os.unlink(batch)

    def test_cli_batch_missing_file(self):
        import subprocess
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--batch", "/nonexistent/path.jsonl"],
            capture_output=True, text=True, timeout=5,
        )
        self.assertEqual(proc.returncode, 2)

    def test_cli_oversize_truncated_to_unknown(self):
        # CLI must NOT OOM on hostile stdin. _read_stdin_bounded caps reads.
        import subprocess
        big = "x" * (_M.MAX_INPUT_BYTES + 1024)
        proc = subprocess.run(
            [sys.executable, str(SCRIPT)],
            input=big,
            capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn(proc.stdout.strip(), ("unknown",))


# ---------------------------------------------------------------------------
# Section 10 — Module-level constants pinned (regression guard)
# ---------------------------------------------------------------------------


class TestPinnedConstants(TestEnvContext):
    """Pin invariants — any drift requires PR review."""

    def test_max_input_bytes_pinned_1MiB(self):
        self.assertEqual(_M.MAX_INPUT_BYTES, 1024 * 1024)

    def test_max_skill_name_chars_pinned_256(self):
        self.assertEqual(_M.MAX_SKILL_NAME_CHARS, 256)

    def test_per_extract_timeout_pinned_100ms(self):
        self.assertEqual(_M.PER_EXTRACT_TIMEOUT_S, 0.1)

    def test_cache_max_entries_pinned_1024(self):
        self.assertEqual(_M._CACHE_MAX_ENTRIES, 1024)


if __name__ == "__main__":
    unittest.main()
