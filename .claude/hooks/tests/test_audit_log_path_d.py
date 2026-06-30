"""test_audit_log_path_d.py — PLAN-079 unit tests for Path D archetype mapping.

Per PLAN-079 §6 spec (Codex MCP gate #23 hardened) — extend
`audit_log.extract_skill()` with a Path D fallback that maps the 5
canonical archetypes (`code-reviewer`, `security-engineer`,
`qa-architect`, `performance-engineer`, `devops`) to their canonical
skill names per ADR-051. Closes the observability gap surfaced S87/S88
(20/26 unknown agent_spawn rows on canonical archetype dispatches
without inline SKILL CONTENT envelope).

## Test target wiring (Codex G23-02 hardening)

Loads canonical `.claude/hooks/audit_log.py` POST-CEREMONY (preferred).
Falls back to staged `.claude/plans/PLAN-079/staged-patches/audit_log.py.new`
PRE-CEREMONY. If both exist post-ceremony, asserts byte-identity to
prevent silent drift between staged + canonical. If neither has Path D
exposed (`_path_d_lookup` symbol), tests hard-fail (SkipTest is NOT used
— governance must not silently pass on missing canonical).

Path precedence reaffirmed:

| Path | Pattern                                              | Source     |
|------|------------------------------------------------------|------------|
| (a)  | ``^SKILL: <name>$`` line-anchored                    | prompt     |
| (b)  | ``^@.claude/skills/<scope>/<name>/SKILL.md sha256=$`` | prompt    |
| (c)  | ``## SKILL CONTENT`` block + ``SKILL LOADED: <name>`` | prompt    |
| (d)  | ``subagent_type`` ∈ canonical-5                       | metadata  |

Path D is TAIL fallback — Paths A/B/C always win when present.
Path D fires on EMPTY prompt (legit empty-body case).
Path D does NOT fire on SANITIZE-REJECTED prompt (Codex G23-03 — the
rejected prompt may have contained a conflicting SKILL claim we failed
to parse; preserving "unknown" surfaces the rejection signal).

Stdlib only. Real-fs invariant per S7/U7 — no mocks.
"""
from __future__ import annotations

import importlib.util
import re
import sys
import unittest
from pathlib import Path

# Hygiene: TestEnvContext for env isolation (S79 Block 10b reaffirmed
# S78 #4: even pure-function tests subclass TestEnvContext for parity).
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _lib.testing import TestEnvContext  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
CANONICAL = REPO_ROOT / ".claude" / "hooks" / "audit_log.py"
STAGED_NEW = (
    REPO_ROOT
    / ".claude"
    / "plans"
    / "PLAN-079"
    / "staged-patches"
    / "audit_log.py.new"
)
AGENTS_DIR = REPO_ROOT / ".claude" / "agents"


def _load_one(label: str, path: Path):
    """Load a Python file as a module via SourceFileLoader."""
    from importlib.machinery import SourceFileLoader

    loader = SourceFileLoader(label, str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[label] = mod
    loader.exec_module(mod)
    return mod


def _load_target_module():
    """Codex G23-02 hardening — prefer canonical post-ceremony.

    Logic:
      1. If canonical exists AND has ``_path_d_lookup`` → use canonical.
      2. If staged exists AND canonical has Path D → assert byte-identity
         (catches mid-ceremony drift).
      3. If canonical lacks Path D AND staged exists → use staged
         (pre-ceremony test path).
      4. If neither has Path D → HARD FAIL (no SkipTest — governance
         must not silently pass on missing canonical implementation).
    """
    canonical_mod = None
    if CANONICAL.is_file():
        canonical_mod = _load_one("audit_log_canonical_p79", CANONICAL)
        if hasattr(canonical_mod, "_path_d_lookup"):
            # Post-ceremony: canonical wins. Verify byte-identity if
            # staged still exists (catches accidental staged drift).
            if STAGED_NEW.is_file():
                cb = CANONICAL.read_bytes()
                sb = STAGED_NEW.read_bytes()
                if cb != sb:
                    raise AssertionError(
                        f"PLAN-079 governance violation: canonical "
                        f"({len(cb)}B) and staged ({len(sb)}B) differ "
                        f"post-ceremony. Re-stage or cleanup STAGED_NEW."
                    )
            return canonical_mod

    # Pre-ceremony: canonical lacks Path D. Use staged.
    if STAGED_NEW.is_file():
        staged_mod = _load_one("audit_log_staged_p79", STAGED_NEW)
        if hasattr(staged_mod, "_path_d_lookup"):
            return staged_mod
        raise AssertionError(
            f"PLAN-079 staged file at {STAGED_NEW} lacks _path_d_lookup — "
            f"staged patch corrupt or pre-PLAN-079."
        )

    raise AssertionError(
        f"PLAN-079: neither canonical (with Path D) at {CANONICAL} "
        f"nor staged at {STAGED_NEW} resolves. Ceremony incomplete."
    )


_M = _load_target_module()
extract_skill = _M.extract_skill
_path_d_lookup = _M._path_d_lookup
_ARCHETYPE_TO_SKILL = _M._ARCHETYPE_TO_SKILL


# A canonical 64-hex sha256 stub used in Format-B fixtures.
_SHA = "0123456789abcdef" * 4


# ---------------------------------------------------------------------------
# Section 1 — Mapping correctness (5 cases — one per canonical archetype)
# ---------------------------------------------------------------------------


class TestPathDMappingCorrectness(TestEnvContext):
    """Each canonical archetype resolves to its expected skill name."""

    def test_code_reviewer_maps_to_code_review_checklist(self):
        self.assertEqual(
            extract_skill("", subagent_type="code-reviewer"),
            "code-review-checklist",
        )

    def test_security_engineer_maps_to_security_and_auth(self):
        self.assertEqual(
            extract_skill("", subagent_type="security-engineer"),
            "security-and-auth",
        )

    def test_qa_architect_maps_to_testing_strategy(self):
        self.assertEqual(
            extract_skill("", subagent_type="qa-architect"),
            "testing-strategy",
        )

    def test_performance_engineer_maps_to_performance_engineering(self):
        self.assertEqual(
            extract_skill("", subagent_type="performance-engineer"),
            "performance-engineering",
        )

    def test_devops_maps_to_devops_ci_cd(self):
        self.assertEqual(
            extract_skill("", subagent_type="devops"),
            "devops-ci-cd",
        )


# ---------------------------------------------------------------------------
# Section 2 — Path A/B/C precedence over Path D
# ---------------------------------------------------------------------------


class TestPathDPrecedence(TestEnvContext):
    """Paths A/B/C always win over Path D when prompt carries explicit envelope."""

    def test_path_a_wins_over_archetype_mapping(self):
        """Explicit `SKILL: foo` overrides `subagent_type=code-reviewer`."""
        prompt = "SKILL: my-custom-skill\n"
        self.assertEqual(
            extract_skill(prompt, subagent_type="code-reviewer"),
            "my-custom-skill",
        )

    def test_path_b_wins_over_archetype_mapping(self):
        """Explicit Format-B reference overrides archetype mapping."""
        prompt = (
            f"@.claude/skills/core/audit-trails/SKILL.md sha256={_SHA}\n"
        )
        self.assertEqual(
            extract_skill(prompt, subagent_type="security-engineer"),
            "audit-trails",
        )

    def test_path_c_wins_over_archetype_mapping(self):
        """Format-C `## SKILL CONTENT` block overrides archetype mapping."""
        prompt = (
            "## SKILL CONTENT\n"
            "SKILL LOADED: component-architecture\n"
            "...redacted body...\n"
        )
        self.assertEqual(
            extract_skill(prompt, subagent_type="qa-architect"),
            "component-architecture",
        )


# ---------------------------------------------------------------------------
# Section 3 — Non-canonical archetypes return "unknown"
# ---------------------------------------------------------------------------


class TestPathDNonCanonical(TestEnvContext):
    """subagent_type values outside canonical-5 return 'unknown'."""

    def test_general_purpose_returns_unknown(self):
        """`general-purpose` is intentionally NOT mapped (generic dispatch)."""
        self.assertEqual(
            extract_skill("", subagent_type="general-purpose"),
            "unknown",
        )

    def test_explore_returns_unknown(self):
        """`Explore` is a built-in tool, not a canonical archetype.

        Lower form `explore` also misses the mapping table.
        """
        self.assertEqual(extract_skill("", subagent_type="explore"), "unknown")

    def test_attacker_archetype_returns_unknown(self):
        """Bogus archetype (potential injection vector) returns unknown."""
        self.assertEqual(
            extract_skill("", subagent_type="attacker-archetype"),
            "unknown",
        )


# ---------------------------------------------------------------------------
# Section 4 — Defense-in-depth — pathological subagent_type rejected
# ---------------------------------------------------------------------------


class TestPathDDefenseInDepth(TestEnvContext):
    """Sec MF-7 — pathological subagent_type values normalized or rejected."""

    def test_uppercase_normalized_via_strip_lower(self):
        """`Code-Reviewer` → case-folded → resolves to `code-review-checklist`.

        Codex G23-01 / Plan §3 case-fold semantics: case-fold is INTENTIONAL,
        mirrors `check_agent_spawn.py:204` archetype-routing precedent
        (Agent-tool emitters may pass mixed case for the same archetype;
        rejecting would be a usability regression for the routing layer).
        """
        self.assertEqual(
            extract_skill("", subagent_type="Code-Reviewer"),
            "code-review-checklist",
        )

    def test_dot_traversal_rejected(self):
        """`..` (path-traversal) rejected by charset."""
        self.assertEqual(
            extract_skill("", subagent_type="../code-reviewer"),
            "unknown",
        )

    def test_slash_rejected(self):
        """Forward slash rejected by charset."""
        self.assertEqual(
            extract_skill("", subagent_type="code/reviewer"),
            "unknown",
        )

    def test_oversize_post_normalize_rejected(self):
        """subagent_type >64 chars post-normalize rejected by charset bound."""
        oversize = "code-reviewer" + ("-" + "x" * 60)
        self.assertEqual(
            extract_skill("", subagent_type=oversize),
            "unknown",
        )

    def test_oversize_raw_pre_normalize_rejected(self):
        """Codex G23-04: huge raw subagent_type bounded BEFORE normalize alloc.

        ``_path_d_lookup`` rejects ``len(subagent_type) > 80`` before
        ``strip().lower()`` allocation. Verifies the pre-normalize cap
        fires (vs the post-normalize charset cap).
        """
        huge = "x" * 1000
        self.assertEqual(
            extract_skill("", subagent_type=huge),
            "unknown",
        )

    def test_unicode_rejected(self):
        """Unicode (homoglyph attack) rejected."""
        # Cyrillic 'с' (U+0441) looks like ASCII 'c'.
        attack = "сode-reviewer"
        self.assertEqual(extract_skill("", subagent_type=attack), "unknown")

    def test_nul_byte_rejected(self):
        """NUL byte in subagent_type rejected."""
        self.assertEqual(
            extract_skill("", subagent_type="code-reviewer\x00"),
            "unknown",
        )

    def test_non_string_rejected(self):
        """Non-string subagent_type rejected (e.g., None, int, list)."""
        self.assertEqual(_path_d_lookup(None), "unknown")  # type: ignore
        self.assertEqual(_path_d_lookup(42), "unknown")  # type: ignore
        self.assertEqual(_path_d_lookup(["code-reviewer"]), "unknown")  # type: ignore


# ---------------------------------------------------------------------------
# Section 5 — Edge cases — Path D fires on empty prompt; rejected → unknown
# ---------------------------------------------------------------------------


class TestPathDPromptEdgeCases(TestEnvContext):
    """Path D fires on EMPTY prompt; preserves 'unknown' on REJECTED prompt.

    Codex G23-03 hardening: a prompt rejected by Sec MF-7 (oversize, NUL,
    non-string, whitespace-only) does NOT fall back to Path D — the
    rejected prompt may have contained a conflicting SKILL envelope we
    failed to parse, and silently overriding it with the archetype map
    would mask the parse failure in forensic logs.
    """

    def test_empty_prompt_path_d_fires(self):
        """Empty prompt + valid archetype → mapped skill (legit empty case)."""
        self.assertEqual(
            extract_skill("", subagent_type="code-reviewer"),
            "code-review-checklist",
        )

    def test_whitespace_only_prompt_path_d_fires(self):
        """Whitespace-only prompt is sanitize-rejected; preserves 'unknown'.

        ``_sanitize_prompt`` rejects ``not prompt.strip()`` → Path D
        does NOT fire because sanitize returned None (rejection signal).
        Pre-G23-03 behavior would have fired Path D — fixed.
        """
        self.assertEqual(
            extract_skill("   \t\n  ", subagent_type="code-reviewer"),
            "unknown",
        )

    def test_oversize_prompt_returns_unknown_not_path_d(self):
        """Codex G23-03: oversize prompt rejection preserves 'unknown'."""
        oversize_prompt = "x" * (1024 * 1024 + 1)
        self.assertEqual(
            extract_skill(oversize_prompt, subagent_type="security-engineer"),
            "unknown",
        )

    def test_nul_byte_prompt_returns_unknown_not_path_d(self):
        """Codex G23-03: NUL-byte prompt rejection preserves 'unknown'."""
        nul_prompt = "valid prefix\x00valid suffix"
        self.assertEqual(
            extract_skill(nul_prompt, subagent_type="qa-architect"),
            "unknown",
        )

    def test_rejected_prompt_with_skill_envelope_returns_unknown(self):
        """Threat model: rejected prompt with explicit SKILL claim → 'unknown'.

        Even when the rejected prompt contains a `SKILL:` envelope, Path D
        does NOT silently override. The audit log preserves 'unknown' so
        forensic review sees the parse failure, not a synthesized identity.
        """
        nul_with_skill = "SKILL: my-skill\x00\n"
        self.assertEqual(
            extract_skill(nul_with_skill, subagent_type="code-reviewer"),
            "unknown",
        )

    def test_falsy_non_string_prompt_returns_unknown_not_path_d(self):
        """Codex G23-09: non-string falsy prompts (None, False, 0, [], {})
        + canonical archetype must return 'unknown' — type-check runs
        BEFORE the `if not prompt` short-circuit so non-string prompts
        don't silently fall through to Path D fallback.

        Pre-G23-09 behavior: `extract_skill(None, "code-reviewer")` returned
        `"code-review-checklist"` because `not None` is True → empty-prompt
        branch fired Path D. Fixed via `if not isinstance(prompt, str)`.
        """
        for falsy_non_string in (None, False, 0, [], {}, b""):
            with self.subTest(prompt=falsy_non_string):
                self.assertEqual(
                    extract_skill(falsy_non_string, subagent_type="code-reviewer"),  # type: ignore
                    "unknown",
                )


# ---------------------------------------------------------------------------
# Section 6 — Backwards compat — single-arg legacy callers
# ---------------------------------------------------------------------------


class TestPathDBackwardsCompat(TestEnvContext):
    """Pre-PLAN-079 single-arg callers continue to work unchanged."""

    def test_legacy_single_arg_path_a(self):
        """Single-arg Path A still works."""
        self.assertEqual(extract_skill("SKILL: code-review\n"), "code-review")

    def test_legacy_single_arg_empty(self):
        """Single-arg empty → 'unknown' (no Path D)."""
        self.assertEqual(extract_skill(""), "unknown")

    def test_legacy_single_arg_no_envelope(self):
        """Single-arg without envelope → 'unknown' (no Path D)."""
        self.assertEqual(extract_skill("hello world\n"), "unknown")


# ---------------------------------------------------------------------------
# Section 7 — Drift detector — mapping table matches frontmatter ONLY
# ---------------------------------------------------------------------------


class TestPathDDriftDetector(TestEnvContext):
    """Mapping table matches `.claude/agents/<archetype>.md` description.

    Codex G23-05 hardening: parses ONLY the YAML frontmatter
    `description:` field (NOT the body), so a stale phrase elsewhere in
    the file cannot satisfy the test if `description:` drifts away.
    """

    _FRONTMATTER_RE = re.compile(r"(?ms)\A---\s*\n(.*?)^---\s*$")
    _DESC_FIELD_RE = re.compile(r"(?m)^description:\s*(.+?)$")
    _LOADS_RE = re.compile(
        r"Loads\s+([a-z0-9][a-z0-9\-]+)\s+skill\s+via\s+reference"
    )

    def _extract_description(self, content: str):
        """Return the YAML description field value, or None on parse fail."""
        fm_m = self._FRONTMATTER_RE.search(content)
        if not fm_m:
            return None
        frontmatter = fm_m.group(1)
        desc_m = self._DESC_FIELD_RE.search(frontmatter)
        if not desc_m:
            return None
        return desc_m.group(1)

    def test_mapping_matches_agent_descriptions(self):
        if not AGENTS_DIR.is_dir():
            self.fail(f"agents dir missing: {AGENTS_DIR}")

        mismatches = []
        for archetype, expected_skill in _ARCHETYPE_TO_SKILL.items():
            agent_file = AGENTS_DIR / f"{archetype}.md"
            if not agent_file.is_file():
                mismatches.append(
                    f"{archetype}: agent file missing at {agent_file}"
                )
                continue

            content = agent_file.read_text(encoding="utf-8", errors="replace")
            description = self._extract_description(content)
            if description is None:
                mismatches.append(
                    f"{archetype}: YAML frontmatter description field "
                    f"missing or unparseable in {agent_file.name}"
                )
                continue

            loads_m = self._LOADS_RE.search(description)
            if not loads_m:
                mismatches.append(
                    f"{archetype}: 'Loads <skill> skill via reference' "
                    f"phrase not found in description field of "
                    f"{agent_file.name}"
                )
                continue

            declared_skill = loads_m.group(1)
            if declared_skill != expected_skill:
                mismatches.append(
                    f"{archetype}: description declares "
                    f"'{declared_skill}' but mapping table says "
                    f"'{expected_skill}'"
                )

        self.assertEqual(
            mismatches,
            [],
            "Drift detected between _ARCHETYPE_TO_SKILL and "
            ".claude/agents/*.md description frontmatter:\n  - "
            + "\n  - ".join(mismatches),
        )

    def test_drift_detector_rejects_body_only_phrase(self):
        """Negative control: if 'Loads X skill via reference' appears in
        body but NOT in description, the detector must report a mismatch.

        Synthesized fixture verifies the detector reads frontmatter ONLY
        (Codex G23-05 hardening). We do not write to .claude/agents/* —
        instead we test the helper directly with synthetic content.
        """
        body_only = (
            "---\n"
            "name: test\n"
            "description: Generic description without the magic phrase.\n"
            "---\n\n"
            "# Body header\n"
            "Loads phantom-skill skill via reference (PLAN-020 ADR-051).\n"
        )
        description = self._extract_description(body_only)
        self.assertIsNotNone(description)
        # The description field does NOT contain "Loads ... skill via reference"
        self.assertIsNone(self._LOADS_RE.search(description))


if __name__ == "__main__":
    unittest.main()
