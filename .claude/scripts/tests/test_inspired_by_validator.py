"""Tests for validate-skill-frontmatter.py V1/V2/V3 — P1-05 Wave 0 PLAN-074.

Imports the validator directly (not subprocess) for speed and detail.
Falls back gracefully (skip) when the module is absent.
"""
from __future__ import annotations

import importlib.util
import sys
import textwrap
from pathlib import Path
from typing import Optional

import pytest

# ---------------------------------------------------------------------------
# Locate the validator (staged → canonical fallback)
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent  # .claude/scripts/tests -> .claude/scripts -> .claude -> ceo-orchestration
_STAGING_PATH = _REPO_ROOT / "tests" / "fixtures" / "skill_frontmatter_staging" / "validate-skill-frontmatter.py"
_CANONICAL_PATH = _REPO_ROOT / ".claude" / "scripts" / "validate-skill-frontmatter.py"

_MODULE_PATH: Optional[Path] = None
if _STAGING_PATH.exists():
    _MODULE_PATH = _STAGING_PATH
elif _CANONICAL_PATH.exists():
    _MODULE_PATH = _CANONICAL_PATH

pytestmark = pytest.mark.skipif(
    _MODULE_PATH is None,
    reason="validate-skill-frontmatter.py not found at staging or canonical path — skipping",
)

# ---------------------------------------------------------------------------
# Dynamic import
# ---------------------------------------------------------------------------

_module = None

def _load_module():
    global _module
    if _module is not None:
        return _module
    if _MODULE_PATH is None:
        pytest.skip("validate-skill-frontmatter.py not available")
    spec = importlib.util.spec_from_file_location("validate_skill_frontmatter", _MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    _module = mod
    return _module


@pytest.fixture(autouse=True)
def validator_module():
    """Ensure the module is loaded before each test."""
    return _load_module()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_skill(tmp_path: Path, frontmatter: str, body: str = "") -> Path:
    """Write a SKILL.md with provided frontmatter block content and optional body."""
    if not body:
        body = textwrap.dedent("""\
            ## When to Apply

            Use this skill for all production deployments.

            ## Anti-Patterns

            Never bypass validation.

            ```python
            pass
            ```
            """) * 4
    skill_file = tmp_path / "SKILL.md"
    skill_file.write_text(f"---\n{frontmatter}\n---\n{body}", encoding="utf-8")
    return skill_file


def _validate_v1(tmp_path: Path, frontmatter: str) -> list:
    """Call validate_v1 and return only ERROR lines (filter out WARN lines).

    When archive_index is None (staging version), V1 emits a WARN for
    each inspired_by source that it cannot path-check.  We suppress those
    WARNs here so tests can focus on schema-compliance ERRORs only.
    """
    mod = _load_module()
    fm = mod._parse_frontmatter(f"---\n{frontmatter}\n---\n")
    if fm is None:
        fm = {}
    import inspect
    sig = inspect.signature(mod.validate_v1)
    if "archive_index" in sig.parameters:
        # archive_index=None → V1 skips path existence check and emits WARNs.
        # We filter out WARN lines so tests only see schema-compliance ERRORs.
        results = mod.validate_v1(str(tmp_path / "SKILL.md"), fm, archive_index=None)
        return [r for r in results if not r.startswith("V1 WARN")]
    return mod.validate_v1(str(tmp_path / "SKILL.md"), fm)


def _validate_v2(tmp_path: Path, frontmatter: str, path_override: Optional[str] = None) -> list:
    mod = _load_module()
    fm = mod._parse_frontmatter(f"---\n{frontmatter}\n---\n")
    if fm is None:
        fm = {}
    filepath = path_override or str(tmp_path / "SKILL.md")
    return mod.validate_v2(filepath, fm)


def _validate_v3(tmp_path: Path, frontmatter: str, domain: Optional[str] = None) -> tuple:
    mod = _load_module()
    fm = mod._parse_frontmatter(f"---\n{frontmatter}\n---\n")
    if fm is None:
        fm = {}
    return mod.validate_v3(str(tmp_path / "SKILL.md"), fm, domain_override=domain)


# ---------------------------------------------------------------------------
# V1 — inspired_by validator
# ---------------------------------------------------------------------------

class TestV1InspiredBy:
    def test_pass_no_inspired_by(self, tmp_path):
        """Skill without inspired_by is valid (V1 does not apply)."""
        errors = _validate_v1(
            tmp_path,
            "description: A skill without any inspired_by field",
        )
        assert errors == []

    def test_pass_valid_entry(self, tmp_path):
        """Valid inspired_by entry with all required fields passes."""
        frontmatter = textwrap.dedent("""\
            description: A properly attributed skill with all required fields
            inspired_by:
              - source: msitarzewski/agency-agents/engineering/backend.md@a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2
                license: MIT
                relationship: structural_inspiration
                authored_by: Alice
                authored_at: 2024-01-15
            """)
        errors = _validate_v1(tmp_path, frontmatter)
        assert errors == [], f"Expected PASS, got: {errors}"

    def test_fail_missing_license(self, tmp_path):
        """inspired_by entry missing 'license' should raise V1 ERROR."""
        frontmatter = textwrap.dedent("""\
            description: A skill that is missing the license field in inspired_by
            inspired_by:
              - source: owner/repo/path/file.md@a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2
                relationship: structural_inspiration
                authored_by: Alice
                authored_at: 2024-01-15
            """)
        errors = _validate_v1(tmp_path, frontmatter)
        assert any("license" in e for e in errors), f"Expected missing-license error, got: {errors}"

    def test_fail_missing_relationship(self, tmp_path):
        """inspired_by entry missing 'relationship' should raise V1 ERROR."""
        frontmatter = textwrap.dedent("""\
            description: A skill that is missing the relationship field in inspired_by
            inspired_by:
              - source: owner/repo/path/file.md@a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2
                license: MIT
                authored_by: Alice
                authored_at: 2024-01-15
            """)
        errors = _validate_v1(tmp_path, frontmatter)
        assert any("relationship" in e for e in errors), f"Expected missing-relationship error, got: {errors}"

    def test_fail_bad_source_format(self, tmp_path):
        """source without @SHA40 suffix should raise V1 ERROR."""
        frontmatter = textwrap.dedent("""\
            description: A skill with a malformed source reference in inspired_by
            inspired_by:
              - source: owner/repo/path/file.md
                license: MIT
                relationship: structural_inspiration
                authored_by: Alice
                authored_at: 2024-01-15
            """)
        errors = _validate_v1(tmp_path, frontmatter)
        assert any("source" in e for e in errors), f"Expected source-format error, got: {errors}"

    def test_fail_bad_authored_at_format(self, tmp_path):
        """authored_at not ISO YYYY-MM-DD should raise V1 ERROR."""
        frontmatter = textwrap.dedent("""\
            description: A skill with an incorrectly formatted authored_at date field
            inspired_by:
              - source: owner/repo/path/file.md@a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2
                license: MIT
                relationship: structural_inspiration
                authored_by: Alice
                authored_at: 15/01/2024
            """)
        errors = _validate_v1(tmp_path, frontmatter)
        assert any("authored_at" in e for e in errors), f"Expected authored_at error, got: {errors}"


# ---------------------------------------------------------------------------
# V2 — runtime_mechanism validator
# ---------------------------------------------------------------------------

class TestV2RuntimeMechanism:
    def test_non_playbook_path_skipped(self, tmp_path):
        """V2 does not apply to files outside docs/playbooks/."""
        errors = _validate_v2(
            tmp_path,
            "description: A regular skill not under docs/playbooks/",
            path_override=str(tmp_path / "SKILL.md"),
        )
        assert errors == []

    def test_playbook_absent_key_errors_p2_02(self, tmp_path):
        """docs/playbooks/ file without runtime_mechanism key → ERROR (Codex P2-02 hardening).

        The staging validator has P2-02 strict mode: the key MUST be present and
        set to false. Key absent is now an ERROR, not a pass.
        """
        errors = _validate_v2(
            tmp_path,
            "description: A playbook without any runtime_mechanism key present",
            path_override=".claude/docs/playbooks/my-playbook.md",
        )
        assert len(errors) > 0, "Expected P2-02 ERROR for absent runtime_mechanism key"
        assert any("runtime_mechanism" in e for e in errors), (
            f"Expected runtime_mechanism mention. errors={errors}"
        )

    def test_playbook_false_passes(self, tmp_path):
        """docs/playbooks/ file with runtime_mechanism: false → pass."""
        errors = _validate_v2(
            tmp_path,
            "description: A playbook that explicitly sets runtime_mechanism to false\nruntime_mechanism: false",
            path_override=".claude/docs/playbooks/my-playbook.md",
        )
        assert errors == [], f"Expected PASS for runtime_mechanism: false. errors={errors}"

    def test_playbook_true_fails(self, tmp_path):
        """docs/playbooks/ file with runtime_mechanism: true → ERROR (strict P2-02).

        Both absent and true are errors per Codex P2-02 hardening in staging validator.
        """
        errors = _validate_v2(
            tmp_path,
            "description: A playbook that incorrectly sets runtime_mechanism to true\nruntime_mechanism: true",
            path_override=".claude/docs/playbooks/my-playbook.md",
        )
        assert len(errors) > 0, f"Expected V2 ERROR for runtime_mechanism: true. errors={errors}"
        assert any("true" in e or "runtime_mechanism" in e for e in errors), (
            f"Expected runtime_mechanism:true mention. errors={errors}"
        )


# ---------------------------------------------------------------------------
# V3 — PII inheritance validator
# ---------------------------------------------------------------------------

class TestV3PIIInheritance:
    def test_legal_domain_missing_inherits_errors(self, tmp_path):
        """legal domain skill missing inherits → V3 ERROR."""
        errors, warnings = _validate_v3(
            tmp_path,
            "description: A legal domain skill that forgot to inherit the LGPD compliance skill",
            domain="legal",
        )
        assert any("inherits" in e or "compliance-lgpd" in e for e in errors), (
            f"Expected V3 ERROR about missing inherits. errors={errors}"
        )

    def test_legal_domain_with_inherits_and_pii_passes(self, tmp_path):
        """legal domain skill with both inherits + pii_handling=required → pass."""
        errors, warnings = _validate_v3(
            tmp_path,
            textwrap.dedent("""\
                description: A legal domain skill with proper LGPD inheritance and PII handling set
                inherits: [core/compliance-lgpd]
                pii_handling: required
                """),
            domain="legal",
        )
        assert errors == [], f"Expected V3 PASS, got errors: {errors}"

    def test_fintech_domain_without_inherits_passes(self, tmp_path):
        """fintech domain skill without inherits → pass (PII not required for fintech)."""
        errors, warnings = _validate_v3(
            tmp_path,
            "description: A fintech domain skill that does not need LGPD inheritance",
            domain="fintech",
        )
        assert errors == [], f"Expected V3 PASS for fintech domain. errors={errors}"
        # fintech is not in PII_WARN_DOMAINS either, so no warnings expected
        assert warnings == [], f"Expected no warnings for fintech. warnings={warnings}"

    def test_non_pii_domain_no_inherits_passes(self, tmp_path):
        """community domain without inherits → pass (not PII-required domain)."""
        errors, warnings = _validate_v3(
            tmp_path,
            "description: A community domain skill that does not require PII inheritance",
            domain="community",
        )
        assert errors == [], f"Expected V3 PASS for community domain. errors={errors}"
