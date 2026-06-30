"""Tests for .claude/scripts/lint-skills.py — P1-05 Wave 0 PLAN-074.

Runs the linter via subprocess so it is tested as a black-box CLI,
matching how validate-governance.sh invokes it.  Tests are skipped
(not failed) when the linter script is absent (adopter installs where
the script was not promoted yet).
"""
from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Locate the linter (staged path fallback to canonical path)
# ---------------------------------------------------------------------------

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent  # .claude/scripts/tests/ -> .claude/scripts -> .claude -> ceo-orchestration
_CANONICAL = _REPO_ROOT / ".claude" / "scripts" / "lint-skills.py"
_STAGING = _REPO_ROOT / ".claude" / "plans" / "PLAN-074" / "staging" / "lint-skills-patched.py"

# Use canonical (post-ceremony) path; skip if absent
if _CANONICAL.exists():
    LINTER = _CANONICAL
elif _STAGING.exists():
    LINTER = _STAGING
else:
    LINTER = None

pytestmark = pytest.mark.skipif(
    LINTER is None,
    reason="lint-skills.py not found at canonical or staging path — skipping in adopter install",
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run(args: list, extra_env=None) -> subprocess.CompletedProcess:
    import os
    env = os.environ.copy()
    if extra_env:
        env.update(extra_env)
    return subprocess.run(
        [sys.executable, str(LINTER)] + args,
        capture_output=True,
        text=True,
        env=env,
    )


def _make_skill(tmp_path: Path, **overrides) -> Path:
    """Write a minimal valid SKILL.md and return the directory path."""
    skill_dir = tmp_path / "test-skill"
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file = skill_dir / "SKILL.md"

    description = overrides.get(
        "description",
        "Detailed guide for engineers building production-grade Python services with testing",
    )
    body = overrides.get(
        "body",
        textwrap.dedent("""\
            ## When to Apply

            Use this skill whenever you need to write production-grade Python code.
            This applies to any backend service, library, or CLI tool. Apply it
            consistently across the entire codebase for uniform quality and style.

            ## Anti-Patterns

            Avoid global state and mutable defaults.
            Never bypass validation layers. Always handle errors explicitly.
            Do not use bare except clauses. Prefer specific exception types.

            ## Examples

            Always write unit tests alongside the implementation code.
            Use parametrize to cover multiple cases efficiently and cleanly.

            ## Correct vs Wrong

            Correct: explicit error handling, typed parameters, documented contracts.
            Wrong: silent failures, type-ignoring, undocumented side effects.

            ```python
            # Example: correct pattern
            def greet(name: str) -> str:
                if not name:
                    raise ValueError("name must not be empty")
                return f"Hello, {name}"
            ```

            Additional guidance for production deployments follows below.
            Always validate inputs at system boundaries. Use pydantic or dataclasses.
            Document all public APIs with clear docstrings and usage examples.
            Run mypy in strict mode and keep zero type errors at all times.
            """) * 3,  # ensure >= 1024 bytes with multiple H2 sections
    )
    fm_extras = overrides.get("fm_extras", "")
    # name: is required by LINT-FM-00b; include a default unless overridden via fm_extras
    name_field = "" if "name:" in fm_extras else "name: test-skill\n"

    content = f"---\ndescription: {description}\n{name_field}{fm_extras}---\n{body}"
    skill_file.write_text(content, encoding="utf-8")
    return skill_file


# ---------------------------------------------------------------------------
# Known-good exemplars (3 real skills)
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not (_REPO_ROOT / ".claude" / "skills" / "core" / "code-review-checklist" / "SKILL.md").exists(),
    reason="Exemplar skill not found",
)
def test_exemplar_code_review_checklist():
    skill_path = str(_REPO_ROOT / ".claude" / "skills" / "core" / "code-review-checklist" / "SKILL.md")
    result = _run([skill_path, "--summary"])
    assert result.returncode == 0, f"Expected exit 0 for exemplar. stderr={result.stderr!r}"
    assert "0 error(s)" in result.stdout, f"Expected 0 errors. stdout={result.stdout!r}"


@pytest.mark.skipif(
    not (_REPO_ROOT / ".claude" / "skills" / "core" / "security-and-auth" / "SKILL.md").exists(),
    reason="Exemplar skill not found",
)
def test_exemplar_security_and_auth():
    skill_path = str(_REPO_ROOT / ".claude" / "skills" / "core" / "security-and-auth" / "SKILL.md")
    result = _run([skill_path, "--summary"])
    assert result.returncode == 0, f"Expected exit 0 for exemplar. stderr={result.stderr!r}"
    assert "0 error(s)" in result.stdout, f"Expected 0 errors. stdout={result.stdout!r}"


@pytest.mark.skipif(
    not (_REPO_ROOT / ".claude" / "skills" / "core" / "ceo-orchestration" / "SKILL.md").exists(),
    reason="Exemplar skill not found",
)
def test_exemplar_ceo_orchestration():
    skill_path = str(_REPO_ROOT / ".claude" / "skills" / "core" / "ceo-orchestration" / "SKILL.md")
    result = _run([skill_path, "--summary"])
    assert result.returncode == 0, f"Expected exit 0 for exemplar. stderr={result.stderr!r}"
    assert "0 error(s)" in result.stdout, f"Expected 0 errors. stdout={result.stdout!r}"


# ---------------------------------------------------------------------------
# Synthetic fixture tests
# ---------------------------------------------------------------------------

def test_generic_description_triggers_error(tmp_path):
    """description: 'expert in foo' should trigger LINT-FM-03 ERROR."""
    skill_file = _make_skill(tmp_path, description="expert in Python programming and software design")
    result = _run([str(skill_file), "--summary"])
    assert result.returncode == 1
    assert "LINT-FM-03" in result.stdout


def test_short_description_triggers_error(tmp_path):
    """description under 50 chars should trigger LINT-FM-02 ERROR."""
    skill_file = _make_skill(tmp_path, description="A skill")
    result = _run([str(skill_file), "--summary"])
    assert result.returncode == 1
    assert "LINT-FM-02" in result.stdout


def test_short_body_triggers_error(tmp_path):
    """body < 1024 bytes should trigger LINT-STRUCT-01 ERROR."""
    skill_file = _make_skill(
        tmp_path,
        body="## When to Apply\n\nShort body.\n\n## Anti-Patterns\n\nNot much here.\n\n```python\npass\n```\n",
    )
    result = _run([str(skill_file), "--summary"])
    assert result.returncode == 1
    assert "LINT-STRUCT-01" in result.stdout


def test_single_h2_triggers_error(tmp_path):
    """body with only 1 H2 section should trigger LINT-STRUCT-02 ERROR."""
    big_body = "## When to Apply\n\n" + ("Some substantial text here. " * 50) + "\n\n```python\npass\n```\n"
    skill_file = _make_skill(tmp_path, body=big_body)
    result = _run([str(skill_file), "--summary"])
    assert result.returncode == 1
    assert "LINT-STRUCT-02" in result.stdout


def test_dropped_at_without_drop_category_triggers_error(tmp_path):
    """dropped_at without drop_category should trigger LINT-FM-30 ERROR."""
    skill_file = _make_skill(tmp_path, fm_extras="dropped_at: 2026-01-01\n")
    result = _run([str(skill_file), "--summary"])
    assert result.returncode == 1
    assert "LINT-FM-30" in result.stdout


def test_valid_skill_exits_zero(tmp_path):
    """A fully valid SKILL.md should exit 0 with 0 errors."""
    skill_file = _make_skill(tmp_path)
    result = _run([str(skill_file), "--summary"])
    assert result.returncode == 0, (
        f"Expected valid skill to exit 0. stdout={result.stdout!r} stderr={result.stderr!r}"
    )
    assert "0 error(s)" in result.stdout


# ---------------------------------------------------------------------------
# LINT-FM-00b: name: field rules
# ---------------------------------------------------------------------------

def test_missing_name_triggers_error(tmp_path):
    """Frontmatter without name: should trigger LINT-FM-00b ERROR."""
    # Write a skill file manually without name: field
    skill_dir = tmp_path / "no-name-skill"
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file = skill_dir / "SKILL.md"
    description = "Detailed guide for engineers building production-grade Python services with testing"
    body = textwrap.dedent("""\
        ## When to Apply

        Use this skill for production Python code. This applies to backend services,
        libraries, and CLI tools. Apply consistently for quality and style throughout.

        ## Anti-Patterns

        Avoid global state and mutable defaults. Never bypass validation layers.
        Always handle errors explicitly. Do not use bare except clauses.

        ```python
        def example() -> str:
            return "valid"
        ```
        """) * 3
    # Intentionally omit name: field
    skill_file.write_text(f"---\ndescription: {description}\n---\n{body}", encoding="utf-8")
    result = _run([str(skill_file), "--summary"])
    assert result.returncode == 1, (
        f"Expected exit 1 for missing name:. stdout={result.stdout!r}"
    )
    assert "LINT-FM-00b" in result.stdout


def test_valid_name_no_error(tmp_path):
    """name: present with valid lowercase-hyphen value should produce no error."""
    skill_file = _make_skill(tmp_path, fm_extras="name: my-skill-name\n")
    result = _run([str(skill_file), "--summary"])
    # Should not produce ERROR for LINT-FM-00b; may have other warnings
    assert "LINT-FM-00b" not in result.stdout or "WARN" in result.stdout.split("LINT-FM-00b")[0].rsplit("\n", 1)[-1], (
        f"Expected no LINT-FM-00b error for valid name. stdout={result.stdout!r}"
    )
    # Specifically: no ERROR for name field
    lines_with_name_rule = [ln for ln in result.stdout.splitlines() if "LINT-FM-00b" in ln]
    for ln in lines_with_name_rule:
        assert "ERROR" not in ln, f"Unexpected ERROR for valid name: {ln!r}"


def test_invalid_name_case_triggers_warn(tmp_path):
    """name: with mixed case or underscores should produce WARN LINT-FM-00b."""
    skill_file = _make_skill(tmp_path, fm_extras="name: MySkill_Name\n")
    result = _run([str(skill_file), "--summary"])
    lines_with_rule = [ln for ln in result.stdout.splitlines() if "LINT-FM-00b" in ln]
    assert lines_with_rule, f"Expected LINT-FM-00b finding. stdout={result.stdout!r}"
    # The finding should be a WARN, not an ERROR (exit code may still be 0 if no other errors)
    assert any("WARN" in ln for ln in lines_with_rule), (
        f"Expected WARN severity for invalid name case. findings={lines_with_rule!r}"
    )


# ---------------------------------------------------------------------------
# PLAN-117 WS-C: LINT-FM-04 (description <= max) + LINT-FM-05 (strict YAML)
# + --only-rules scoping. These are the multi-harness frontmatter hygiene gate.
# ---------------------------------------------------------------------------

def test_long_description_triggers_fm04(tmp_path):
    """description > --max-description should trigger LINT-FM-04 ERROR."""
    long_desc = "Production engineering guidance. " + ("keyword " * 200)  # > 1024 chars
    skill_file = _make_skill(tmp_path, description=long_desc)
    result = _run([str(skill_file), "--max-description=1024", "--summary"])
    assert result.returncode == 1, f"stdout={result.stdout!r}"
    assert "LINT-FM-04" in result.stdout


def test_max_description_threshold_is_configurable(tmp_path):
    """--max-description controls the FM-04 threshold; under it = no FM-04."""
    desc = "Detailed guide for engineers building production-grade Python services with testing"
    skill_file = _make_skill(tmp_path, description=desc)
    # len(desc) ~ 82; with a tiny threshold it must fire, with default it must not
    fired = _run([str(skill_file), "--max-description=40", "--summary"])
    assert "LINT-FM-04" in fired.stdout and fired.returncode == 1
    clean = _run([str(skill_file), "--max-description=1024", "--summary"])
    assert "LINT-FM-04" not in clean.stdout


def test_default_max_description_is_1024(tmp_path):
    """With no --max-description flag the default 1024 applies (a 1100-char desc fires)."""
    skill_file = _make_skill(tmp_path, description="x marks the spot. " + ("alpha " * 200))
    result = _run([str(skill_file), "--summary"])
    assert "LINT-FM-04" in result.stdout and result.returncode == 1


def test_strict_yaml_catches_invalid_frontmatter(tmp_path):
    """--strict-yaml flags frontmatter that fails a strict YAML parse (LINT-FM-05)."""
    pytest.importorskip("yaml", reason="strict-yaml check is best-effort; no-ops without PyYAML")
    # quoted-scalar-then-trailing-text: 'X' — more  (the requirement-quality-checklist class)
    bad_desc = "'Unit Tests for English' — validates requirements writing quality and rejects bad specs"
    skill_file = _make_skill(tmp_path, description=bad_desc)
    result = _run([str(skill_file), "--strict-yaml", "--summary"])
    assert result.returncode == 1, f"stdout={result.stdout!r}"
    assert "LINT-FM-05" in result.stdout


def test_strict_yaml_passes_valid_frontmatter(tmp_path):
    """A valid SKILL.md passes --strict-yaml with no FM-05."""
    pytest.importorskip("yaml")
    skill_file = _make_skill(tmp_path)
    result = _run([str(skill_file), "--strict-yaml", "--max-description=1024", "--summary"])
    assert result.returncode == 0, f"stdout={result.stdout!r} stderr={result.stderr!r}"
    assert "LINT-FM-05" not in result.stdout


def test_only_rules_suppresses_other_findings(tmp_path):
    """--only-rules=LINT-FM-04 must suppress an unrelated rule (e.g. generic FM-03)."""
    # 'expert in ...' triggers FM-03 normally; with --only-rules it must be suppressed.
    skill_file = _make_skill(tmp_path, description="expert in Python programming and software design")
    full = _run([str(skill_file), "--summary"])
    assert "LINT-FM-03" in full.stdout and full.returncode == 1
    scoped = _run([str(skill_file), "--only-rules=LINT-FM-04,LINT-FM-05", "--summary"])
    assert "LINT-FM-03" not in scoped.stdout
    assert scoped.returncode == 0, f"stdout={scoped.stdout!r}"


def test_fm04_still_fires_under_only_rules(tmp_path):
    """LINT-FM-04 must still fire when it is in the --only-rules allowlist."""
    long_desc = "Production engineering guidance. " + ("keyword " * 200)  # > 1024 chars
    skill_file = _make_skill(tmp_path, description=long_desc)
    result = _run([str(skill_file), "--max-description=1024",
                   "--only-rules=LINT-FM-04,LINT-FM-05", "--summary"])
    assert result.returncode == 1, f"stdout={result.stdout!r}"
    assert "LINT-FM-04" in result.stdout


def test_fm05_still_fires_under_only_rules(tmp_path):
    """LINT-FM-05 must still fire when it is in the --only-rules allowlist."""
    pytest.importorskip("yaml")
    bad_desc = "'Unit Tests for English' — validates requirements writing quality and rejects bad specs"
    skill_file = _make_skill(tmp_path, description=bad_desc)
    result = _run([str(skill_file), "--strict-yaml",
                   "--only-rules=LINT-FM-04,LINT-FM-05", "--summary"])
    assert result.returncode == 1, f"stdout={result.stdout!r}"
    assert "LINT-FM-05" in result.stdout


@pytest.mark.skipif(
    not (_REPO_ROOT / ".claude" / "skills").is_dir(),
    reason="skills corpus not present (adopter install)",
)
def test_live_corpus_passes_wsc_gate():
    """Integration: the whole live skills corpus passes the scoped WS-C gate.

    This is the CI teeth for PLAN-117 WS-C (runs in jobs that install PyYAML):
    any SKILL.md whose description exceeds 1024 chars OR fails a strict YAML
    parse fails this test. Scoped via --only-rules so pre-existing unrelated
    lint findings (e.g. LINT-FM-10) do not affect it.
    """
    pytest.importorskip("yaml", reason="strict-yaml leg needs PyYAML for full teeth")
    skills_dir = str(_REPO_ROOT / ".claude" / "skills")
    result = _run([
        "--quiet", "--strict-yaml", "--max-description=1024",
        "--only-rules=LINT-FM-04,LINT-FM-05", skills_dir,
    ])
    assert result.returncode == 0, (
        f"Live corpus has a SKILL.md over 1024 chars or invalid YAML.\n{result.stdout}"
    )


# ---------------------------------------------------------------------------
# PLAN-135 W3 K1 (UNIT k1b): LINT-FM-40 (paths: auto-activation globs) +
# LINT-FM-41 (context: enum fork|main). Both OPTIONAL fields — absence must
# never produce a finding. Validation is strict-YAML-oracle when PyYAML is
# present, stdlib raw-extractor fallback otherwise; these tests must pass in
# BOTH regimes, so none of them importorskip yaml.
# ---------------------------------------------------------------------------

_K1_GATE_SCOPE = "--only-rules=LINT-FM-04,LINT-FM-05,LINT-FM-40,LINT-FM-41"


def test_paths_block_list_valid_exits_zero(tmp_path):
    """paths: as a block list of non-empty glob strings is valid (no FM-40)."""
    skill_file = _make_skill(
        tmp_path, fm_extras='paths:\n  - "src/payments/**"\n  - "**/billing/**"\n')
    result = _run([str(skill_file), "--strict-yaml", "--summary"])
    assert result.returncode == 0, f"stdout={result.stdout!r}"
    assert "LINT-FM-40" not in result.stdout


def test_paths_inline_list_valid_exits_zero(tmp_path):
    """paths: as an inline [a, b] list of glob strings is valid (no FM-40)."""
    skill_file = _make_skill(
        tmp_path, fm_extras='paths: ["src/payments/**", "src/ledger/**"]\n')
    result = _run([str(skill_file), "--strict-yaml", "--summary"])
    assert result.returncode == 0, f"stdout={result.stdout!r}"
    assert "LINT-FM-40" not in result.stdout


def test_paths_scalar_triggers_fm40(tmp_path):
    """paths: with a bare scalar (not a list) must trigger LINT-FM-40 ERROR."""
    skill_file = _make_skill(tmp_path, fm_extras="paths: src/payments/**\n")
    result = _run([str(skill_file), "--strict-yaml", "--summary"])
    assert result.returncode == 1, f"stdout={result.stdout!r}"
    assert "LINT-FM-40" in result.stdout


def test_paths_empty_list_triggers_fm40(tmp_path):
    """paths: [] (empty list) must trigger LINT-FM-40 ERROR."""
    skill_file = _make_skill(tmp_path, fm_extras="paths: []\n")
    result = _run([str(skill_file), "--strict-yaml", "--summary"])
    assert result.returncode == 1, f"stdout={result.stdout!r}"
    assert "LINT-FM-40" in result.stdout


def test_paths_empty_entry_triggers_fm40(tmp_path):
    """paths: list with an empty-string entry must trigger LINT-FM-40 ERROR."""
    skill_file = _make_skill(tmp_path, fm_extras='paths:\n  - ""\n')
    result = _run([str(skill_file), "--strict-yaml", "--summary"])
    assert result.returncode == 1, f"stdout={result.stdout!r}"
    assert "LINT-FM-40" in result.stdout


def test_paths_non_string_entry_triggers_fm40(tmp_path):
    """paths: list with a mapping entry must trigger LINT-FM-40 ERROR."""
    skill_file = _make_skill(tmp_path, fm_extras='paths:\n  - {glob: "x"}\n')
    result = _run([str(skill_file), "--strict-yaml", "--summary"])
    assert result.returncode == 1, f"stdout={result.stdout!r}"
    assert "LINT-FM-40" in result.stdout


def test_context_fork_valid_exits_zero(tmp_path):
    """context: fork is a valid enum value (no FM-41)."""
    skill_file = _make_skill(tmp_path, fm_extras="context: fork\n")
    result = _run([str(skill_file), "--strict-yaml", "--summary"])
    assert result.returncode == 0, f"stdout={result.stdout!r}"
    assert "LINT-FM-41" not in result.stdout


def test_context_main_valid_exits_zero(tmp_path):
    """context: main (explicit default) is a valid enum value (no FM-41)."""
    skill_file = _make_skill(tmp_path, fm_extras="context: main\n")
    result = _run([str(skill_file), "--strict-yaml", "--summary"])
    assert result.returncode == 0, f"stdout={result.stdout!r}"
    assert "LINT-FM-41" not in result.stdout


def test_context_invalid_enum_triggers_fm41(tmp_path):
    """context: with a non-enum value must trigger LINT-FM-41 ERROR."""
    skill_file = _make_skill(tmp_path, fm_extras="context: forked\n")
    result = _run([str(skill_file), "--strict-yaml", "--summary"])
    assert result.returncode == 1, f"stdout={result.stdout!r}"
    assert "LINT-FM-41" in result.stdout


def test_context_list_form_triggers_fm41(tmp_path):
    """context: as a list (wrong type) must trigger LINT-FM-41 ERROR."""
    skill_file = _make_skill(tmp_path, fm_extras="context:\n  - fork\n")
    result = _run([str(skill_file), "--strict-yaml", "--summary"])
    assert result.returncode == 1, f"stdout={result.stdout!r}"
    assert "LINT-FM-41" in result.stdout


def test_absent_k1_fields_produce_no_findings(tmp_path):
    """Both fields are OPTIONAL: a skill without them has no FM-40/41 findings."""
    skill_file = _make_skill(tmp_path)
    result = _run([str(skill_file), "--strict-yaml", "--summary"])
    assert result.returncode == 0, f"stdout={result.stdout!r}"
    assert "LINT-FM-40" not in result.stdout
    assert "LINT-FM-41" not in result.stdout


def test_fm40_fires_under_extended_gate_scope(tmp_path):
    """LINT-FM-40 must fire under the extended WS-C --only-rules allowlist."""
    skill_file = _make_skill(tmp_path, fm_extras="paths: src/payments/**\n")
    result = _run([str(skill_file), "--strict-yaml", _K1_GATE_SCOPE, "--summary"])
    assert result.returncode == 1, f"stdout={result.stdout!r}"
    assert "LINT-FM-40" in result.stdout


def test_fm41_fires_under_extended_gate_scope(tmp_path):
    """LINT-FM-41 must fire under the extended WS-C --only-rules allowlist."""
    skill_file = _make_skill(tmp_path, fm_extras="context: nope\n")
    result = _run([str(skill_file), "--strict-yaml", _K1_GATE_SCOPE, "--summary"])
    assert result.returncode == 1, f"stdout={result.stdout!r}"
    assert "LINT-FM-41" in result.stdout


def test_old_gate_scope_suppresses_fm40_41(tmp_path):
    """Pre-K1 scope (FM-04,FM-05 only) suppresses FM-40/41 — proves the new
    rules ride exclusively on the --only-rules allowlist (backward compat)."""
    skill_file = _make_skill(
        tmp_path, fm_extras="paths: src/payments/**\ncontext: nope\n")
    result = _run([str(skill_file), "--strict-yaml",
                   "--only-rules=LINT-FM-04,LINT-FM-05", "--summary"])
    assert result.returncode == 0, f"stdout={result.stdout!r}"
    assert "LINT-FM-40" not in result.stdout
    assert "LINT-FM-41" not in result.stdout


@pytest.mark.skipif(
    not (_REPO_ROOT / ".claude" / "skills").is_dir(),
    reason="skills corpus not present (adopter install)",
)
def test_live_corpus_passes_extended_wsc_gate():
    """Integration: the whole skills corpus passes the K1-extended WS-C gate.

    Mirrors the validate-governance.sh §6b scope after PLAN-135 W3: any
    SKILL.md with a malformed paths: list or a non-enum context: fails here.
    Skills without the fields are untouched (fields are optional).
    """
    skills_dir = str(_REPO_ROOT / ".claude" / "skills")
    result = _run([
        "--quiet", "--strict-yaml", "--max-description=1024",
        _K1_GATE_SCOPE, skills_dir,
    ])
    assert result.returncode == 0, (
        f"Corpus has a SKILL.md with malformed paths:/context: (or FM-04/05).\n{result.stdout}"
    )
