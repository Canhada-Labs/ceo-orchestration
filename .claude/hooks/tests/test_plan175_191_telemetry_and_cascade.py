"""Evidence at the returned router payload, never at a mocked API call."""

import pytest

from _lib._skill_telemetry_router import (
    resolve_skill_slug_from_path,
    select_cheap_tier_cascade,
)


@pytest.fixture
def skill_fixture(tmp_path):
    skill = tmp_path / "workspace" / ".claude" / "skills" / "core" / "real-skill"
    skill.mkdir(parents=True)
    skill_file = skill / "SKILL.md"
    skill_file.write_text("# Verified skill\n", encoding="utf-8")
    return skill_file


def test_absolute_skill_file_returns_real_slug(skill_fixture):
    assert resolve_skill_slug_from_path(str(skill_fixture)) == "real-skill"


def test_relative_skill_file_returns_real_slug(skill_fixture, monkeypatch):
    monkeypatch.chdir(skill_fixture.parents[4])
    assert resolve_skill_slug_from_path(".claude/skills/core/real-skill/SKILL.md") == "real-skill"


def test_symlink_alias_uses_target_slug(skill_fixture, tmp_path):
    alias = tmp_path / "invented-alias.md"
    alias.symlink_to(skill_fixture)
    assert resolve_skill_slug_from_path(str(alias)) == "real-skill"


def test_directory_with_real_skill_file_is_accepted(skill_fixture):
    assert resolve_skill_slug_from_path(str(skill_fixture.parent)) == "real-skill"


@pytest.mark.parametrize(
    "suffix",
    [
        ("core", "flat-skill"),
        ("frontend", "flat-skill"),
        ("domains", "trading-hft", "flat-skill"),
        ("domains", "trading-hft", "skills", "flat-skill"),
    ],
)
def test_inventory_skill_layouts_are_recognized(tmp_path, suffix):
    skill = tmp_path / ".claude" / "skills"
    for component in suffix:
        skill /= component
    skill.mkdir(parents=True)
    skill_file = skill / "SKILL.md"
    skill_file.write_text("# Valid inventoried layout", encoding="utf-8")
    assert resolve_skill_slug_from_path(str(skill_file)) == "flat-skill"


def test_deep_arbitrary_nesting_is_not_a_skill(tmp_path):
    impostor = tmp_path / ".claude" / "skills" / "ops" / "extra" / "deep" / "fake" / "SKILL.md"
    impostor.parent.mkdir(parents=True)
    impostor.write_text("# Arbitrary nesting", encoding="utf-8")
    assert resolve_skill_slug_from_path(str(impostor)) == "unknown"


@pytest.mark.parametrize("bad_path", ["", "../outside/SKILL.md", "\x00", 17])
def test_bad_skill_paths_never_invent_a_slug(bad_path):
    assert resolve_skill_slug_from_path(bad_path) == "unknown"


def test_nonexistent_skill_file_never_invents_slug(skill_fixture):
    assert resolve_skill_slug_from_path(str(skill_fixture.parent / "missing.md")) == "unknown"


def test_traversal_to_existing_skill_is_still_rejected(skill_fixture):
    traversing = skill_fixture.parent / ".." / "real-skill" / "SKILL.md"
    assert resolve_skill_slug_from_path(str(traversing)) == "unknown"


def test_existing_file_outside_skill_tree_is_unknown(tmp_path):
    impostor = tmp_path / "fake" / "SKILL.md"
    impostor.parent.mkdir()
    impostor.write_text("# Not registered", encoding="utf-8")
    assert resolve_skill_slug_from_path(str(impostor)) == "unknown"


def test_symlink_to_external_impostor_is_unknown(skill_fixture, tmp_path):
    external = tmp_path / "external" / "SKILL.md"
    external.parent.mkdir()
    external.write_text("# External", encoding="utf-8")
    skill_fixture.unlink()
    skill_fixture.symlink_to(external)
    assert resolve_skill_slug_from_path(str(skill_fixture)) == "unknown"


@pytest.mark.parametrize(
    ("complexity", "expected_tiers", "max_tier"),
    [
        ("low", ["haiku"], "haiku"),
        ("medium", ["haiku", "sonnet"], "sonnet"),
        ("high", ["haiku", "sonnet", "opus"], "opus"),
    ],
)
def test_positive_budget_returns_advisory_not_cost_guarantee(
    complexity, expected_tiers, max_tier
):
    payload = select_cheap_tier_cascade(complexity, 0.01)
    assert payload == {
        "status": "advisory_only",
        "task_complexity": complexity,
        "budget_cap_usd": "0.01",
        "tiers": expected_tiers,
        "max_tier": max_tier,
        "estimated_cost_usd": None,
        "requires_independent_verification": True,
        "requires_price_and_token_check": True,
        "executes_models": False,
        "reason": "cost_and_quality_unverified; escalate_only_after_independent_failure",
    }


def test_zero_budget_blocks_all_tiers():
    payload = select_cheap_tier_cascade("high", 0)
    assert payload["status"] == "blocked"
    assert payload["tiers"] == []
    assert payload["budget_cap_usd"] == "0"
    assert payload["reason"] == "budget_exhausted"


@pytest.mark.parametrize("bad_budget", [-1, float("nan"), float("inf"), float("-inf"), True, "n/a"])
def test_invalid_budget_blocks_all_tiers(bad_budget):
    payload = select_cheap_tier_cascade("high", bad_budget)
    assert payload["status"] == "blocked"
    assert payload["tiers"] == []
    assert payload["budget_cap_usd"] is None
    assert payload["reason"] == "invalid_budget"


def test_unknown_complexity_blocks_without_guessing():
    payload = select_cheap_tier_cascade("financial", 100)
    assert payload["status"] == "blocked"
    assert payload["tiers"] == []
    assert payload["reason"] == "invalid_complexity"


def test_micro_budget_not_asserted_affordable():
    payload = select_cheap_tier_cascade("high", 0.000000001)
    assert payload["status"] == "advisory_only"
    assert payload["estimated_cost_usd"] is None
    assert payload["requires_price_and_token_check"] is True
    assert payload["executes_models"] is False
