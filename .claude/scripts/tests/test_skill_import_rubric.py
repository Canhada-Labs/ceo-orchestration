"""PLAN-033 tests — skill-import-rubric.py curation validator.

Parametrized structural tests for each of the 7 rubric rules plus CLI
exit-code behavior. Stdlib-only + pytest.
"""
from __future__ import annotations

import importlib.util
import io
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import pytest


def _load_module():
    here = Path(__file__).resolve().parent.parent
    src = here / "skill-import-rubric.py"
    mod_name = "skill_import_rubric_under_test"
    spec = importlib.util.spec_from_file_location(mod_name, src)
    mod = importlib.util.module_from_spec(spec)
    # Register in sys.modules BEFORE exec so dataclass __module__ resolution
    # works on Python 3.9 (sys.modules.get(__module__).__dict__ else raises).
    sys.modules[mod_name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


sr = _load_module()


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


_GOOD_FRONTMATTER = (
    "---\n"
    "name: sample-skill\n"
    "description: A sample skill used in test fixtures.\n"
    "---\n\n"
)


def _make_skill(
    tmp: Path,
    frontmatter: str = _GOOD_FRONTMATTER,
    body: str = "",
    filename: str = "SKILL.md",
) -> Path:
    if not body:
        # Generate a body that comfortably exceeds 512 non-ws bytes +
        # has headings + checklist + no forbidden keywords.
        body = "\n".join(
            [
                "# Sample Skill",
                "",
                "## Purpose",
                "",
                "This skill exists to serve as a fixture for the curation",
                "rubric tests. The body must exceed the 512 non-ws byte",
                "floor, include at least one heading, and include at least",
                "one checklist-style item.",
                "",
                "## Checklist",
                "",
                "- [ ] Validate frontmatter",
                "- [ ] Validate non-ws size",
                "- [ ] Validate structure",
                "- [ ] Validate no forbidden content",
                "- [ ] Validate UTF-8 cleanliness",
                "",
                "## Notes",
                "",
                "The sample content here is intentionally long enough to",
                "cross the 512 non-ws byte floor. Padding continues until",
                "we are safely above that threshold. Lorem ipsum dolor sit",
                "amet, consectetur adipiscing elit, sed do eiusmod tempor",
                "incididunt ut labore et dolore magna aliqua.",
            ]
        )
    p = tmp / filename
    p.write_text(frontmatter + body, encoding="utf-8")
    return p


# ===========================================================================
# A. Individual rule tests (parametrized across rule IDs)
# ===========================================================================


class RuleR1FilenameTests:
    def test_skill_md_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = _make_skill(Path(tmp))
            r = sr.evaluate(p)
            assert next(f for f in r.findings if f.rule == "R1").ok

    def test_non_skill_md_filename_fails(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            p = _make_skill(Path(tmp), filename="skill.md")
            r = sr.evaluate(p)
            r1 = next(f for f in r.findings if f.rule == "R1")
            assert not r1.ok
            assert "SKILL.md" in r1.detail


def test_r1_passes_for_canonical_filename() -> None:
    RuleR1FilenameTests().test_skill_md_passes()


def test_r1_fails_for_lowercase() -> None:
    RuleR1FilenameTests().test_non_skill_md_filename_fails()


# --- R2: non-ws size ---

@pytest.mark.parametrize(
    "body_size,expect_ok",
    [
        (50, False),       # tiny
        (200, False),      # still under 512 (net of frontmatter)
        (400, False),      # still below after frontmatter overhead
        (600, True),       # comfortably above 512 even net of frontmatter
        (2000, True),      # large
    ],
)
def test_r2_nonws_threshold(body_size: int, expect_ok: bool) -> None:
    """R2 checks total non-ws byte count including frontmatter. Because
    our test frontmatter contributes ~60 non-ws bytes, the boundary is
    near 450 characters of body — we parametrize well inside each side
    of the boundary to avoid off-by-one flakes."""
    with tempfile.TemporaryDirectory() as tmp:
        body = "# Title\n\n" + ("x" * body_size)
        p = _make_skill(Path(tmp), body=body)
        r = sr.evaluate(p)
        r2 = next(f for f in r.findings if f.rule == "R2")
        assert r2.ok == expect_ok


# --- R3: frontmatter ---


def test_r3_missing_frontmatter_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        p = _make_skill(Path(tmp), frontmatter="")
        r = sr.evaluate(p)
        r3 = next(f for f in r.findings if f.rule == "R3")
        assert not r3.ok


def test_r3_missing_name_fails() -> None:
    fm = "---\ndescription: without a name\n---\n\n"
    with tempfile.TemporaryDirectory() as tmp:
        p = _make_skill(Path(tmp), frontmatter=fm)
        r = sr.evaluate(p)
        r3 = next(f for f in r.findings if f.rule == "R3")
        assert not r3.ok
        assert "name" in r3.detail


def test_r3_missing_description_fails() -> None:
    fm = "---\nname: no-desc-skill\n---\n\n"
    with tempfile.TemporaryDirectory() as tmp:
        p = _make_skill(Path(tmp), frontmatter=fm)
        r = sr.evaluate(p)
        r3 = next(f for f in r.findings if f.rule == "R3")
        assert not r3.ok


def test_r3_empty_name_fails() -> None:
    fm = "---\nname:   \ndescription: desc\n---\n\n"
    with tempfile.TemporaryDirectory() as tmp:
        p = _make_skill(Path(tmp), frontmatter=fm)
        r = sr.evaluate(p)
        r3 = next(f for f in r.findings if f.rule == "R3")
        assert not r3.ok


def test_r3_good_frontmatter_passes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        p = _make_skill(Path(tmp))
        r = sr.evaluate(p)
        r3 = next(f for f in r.findings if f.rule == "R3")
        assert r3.ok


# --- R4: headings ---


def test_r4_no_headings_fails() -> None:
    body = "No headings here. Just prose.\n" + ("x " * 400)
    with tempfile.TemporaryDirectory() as tmp:
        p = _make_skill(Path(tmp), body=body)
        r = sr.evaluate(p)
        r4 = next(f for f in r.findings if f.rule == "R4")
        assert not r4.ok


def test_r4_h2_passes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        p = _make_skill(Path(tmp))
        r = sr.evaluate(p)
        r4 = next(f for f in r.findings if f.rule == "R4")
        assert r4.ok


def test_r4_h3_only_passes() -> None:
    body = "### Sub only\n\n" + ("word " * 200) + "\n- [ ] item"
    with tempfile.TemporaryDirectory() as tmp:
        p = _make_skill(Path(tmp), body=body)
        r = sr.evaluate(p)
        r4 = next(f for f in r.findings if f.rule == "R4")
        assert r4.ok


# --- R5: checklist ---


def test_r5_checkbox_item_passes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        p = _make_skill(Path(tmp))
        r = sr.evaluate(p)
        r5 = next(f for f in r.findings if f.rule == "R5")
        assert r5.ok


def test_r5_checklist_section_three_items_passes() -> None:
    body = (
        "## Heading\n\n"
        + ("word " * 200)
        + "\n\n## Checklist\n\n- a\n- b\n- c\n- d\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        p = _make_skill(Path(tmp), body=body)
        r = sr.evaluate(p)
        r5 = next(f for f in r.findings if f.rule == "R5")
        assert r5.ok


def test_r5_no_checklist_fails() -> None:
    body = "## Heading\n\nNo list items here.\n" + ("x " * 400)
    with tempfile.TemporaryDirectory() as tmp:
        p = _make_skill(Path(tmp), body=body)
        r = sr.evaluate(p)
        r5 = next(f for f in r.findings if f.rule == "R5")
        assert not r5.ok


def test_r5_checklist_section_with_two_items_fails() -> None:
    body = "## H\n" + ("word " * 200) + "\n## Checks\n\n- a\n- b\n"
    with tempfile.TemporaryDirectory() as tmp:
        p = _make_skill(Path(tmp), body=body)
        r = sr.evaluate(p)
        r5 = next(f for f in r.findings if f.rule == "R5")
        assert not r5.ok


# --- R6: forbidden keywords ---


@pytest.mark.parametrize(
    "keyword",
    [
        "phishing campaign",
        "credential harvesting tutorial",
        "malware development",
        "exploit kit",
        "jailbreak Claude",
        "jailbreak GPT",
        "how to bypass authentication",
        "ransomware tutorial",
    ],
)
def test_r6_forbidden_keyword_fails(keyword: str) -> None:
    # Build a body with the keyword embedded; still satisfies size + headings.
    body = (
        "## H\n\n"
        + ("padding " * 200)
        + f"\n\nNote: {keyword} material.\n\n- [ ] any item\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        p = _make_skill(Path(tmp), body=body)
        r = sr.evaluate(p, forbidden_extra=None)
        r6 = next(f for f in r.findings if f.rule == "R6")
        assert not r6.ok, f"{keyword!r} must trigger R6"


def test_r6_clean_body_passes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        p = _make_skill(Path(tmp))
        r = sr.evaluate(p)
        r6 = next(f for f in r.findings if f.rule == "R6")
        assert r6.ok


def test_r6_additional_keywords_can_be_injected() -> None:
    body = (
        "## H\n\n"
        + ("padding " * 200)
        + "\n\nThis mentions MY_CUSTOM_FORBIDDEN_TOKEN.\n\n- [ ] item\n"
    )
    with tempfile.TemporaryDirectory() as tmp:
        p = _make_skill(Path(tmp), body=body)
        r = sr.evaluate(p, forbidden_extra=["my_custom_forbidden_token"])
        r6 = next(f for f in r.findings if f.rule == "R6")
        assert not r6.ok


# --- R7: BOM / bidi / zero-width ---


def test_r7_clean_content_passes() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        p = _make_skill(Path(tmp))
        r = sr.evaluate(p)
        r7 = next(f for f in r.findings if f.rule == "R7")
        assert r7.ok


@pytest.mark.parametrize(
    "mark",
    ["\u202e", "\u2066", "\u2067", "\u2068", "\u2069"],
)
def test_r7_bidi_override_fails(mark: str) -> None:
    body = "## H\n\n" + ("word " * 200) + f"\n{mark}x\n- [ ] a"
    with tempfile.TemporaryDirectory() as tmp:
        p = _make_skill(Path(tmp), body=body)
        r = sr.evaluate(p)
        r7 = next(f for f in r.findings if f.rule == "R7")
        assert not r7.ok


@pytest.mark.parametrize("mark", ["\u200b", "\u200c", "\u200d", "\u2060", "\ufeff"])
def test_r7_zero_width_marks_fail(mark: str) -> None:
    # Skip BOM for the middle-of-content case — it triggers a different
    # branch. We only need to verify that zero-width chars are detected
    # anywhere in the body.
    body = "## H\n\n" + ("word " * 200) + f"\nsome{mark}text\n- [ ] a"
    with tempfile.TemporaryDirectory() as tmp:
        p = _make_skill(Path(tmp), body=body)
        r = sr.evaluate(p)
        r7 = next(f for f in r.findings if f.rule == "R7")
        assert not r7.ok


def test_r7_utf8_bom_at_start_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "SKILL.md"
        p.write_text("\ufeff" + _GOOD_FRONTMATTER + "## H\n\n" + "word " * 200 + "\n- [ ] a", encoding="utf-8")
        r = sr.evaluate(p)
        r7 = next(f for f in r.findings if f.rule == "R7")
        assert not r7.ok


# ===========================================================================
# B. RubricResult aggregation
# ===========================================================================


def test_passed_true_when_all_rules_ok() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        p = _make_skill(Path(tmp))
        r = sr.evaluate(p)
        assert r.passed, f"findings: {[(f.rule, f.ok, f.detail) for f in r.findings]}"


def test_passed_false_when_any_rule_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        p = _make_skill(Path(tmp), frontmatter="")  # R3 fails
        r = sr.evaluate(p)
        assert not r.passed


def test_to_dict_shape() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        p = _make_skill(Path(tmp))
        r = sr.evaluate(p)
        d = r.to_dict()
        assert d["path"] == str(p)
        assert d["passed"] is True
        assert d["rubric_version"] == sr.RUBRIC_VERSION
        assert len(d["findings"]) == 7


# ===========================================================================
# C. evaluate_dir recursive
# ===========================================================================


def test_evaluate_dir_finds_all_skill_md() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "skill-a").mkdir()
        (root / "skill-b").mkdir()
        _make_skill(root / "skill-a")
        _make_skill(root / "skill-b")
        results = sr.evaluate_dir(root)
        assert len(results) == 2
        paths = {r.path.parent.name for r in results}
        assert paths == {"skill-a", "skill-b"}


def test_evaluate_dir_empty_returns_empty() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        results = sr.evaluate_dir(Path(tmp))
        assert results == []


# ===========================================================================
# D. CLI behavior (main function via argparse)
# ===========================================================================


def _run_cli(argv: List[str]) -> int:
    return sr.main(argv)


def test_cli_single_file_pass_exit_0(capsys: Any) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        p = _make_skill(Path(tmp))
        rc = _run_cli([str(p)])
    assert rc == 0


def test_cli_single_file_fail_exit_1(capsys: Any) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        p = _make_skill(Path(tmp), frontmatter="")
        rc = _run_cli([str(p)])
    assert rc == 1


def test_cli_dir_pass_exit_0(capsys: Any) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "one").mkdir()
        _make_skill(Path(tmp) / "one")
        rc = _run_cli(["--dir", str(Path(tmp))])
    assert rc == 0


def test_cli_dir_strict_fail_exit_1(capsys: Any) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "one").mkdir()
        _make_skill(Path(tmp) / "one", frontmatter="")  # fails
        rc = _run_cli(["--dir", str(Path(tmp)), "--strict"])
    assert rc == 1


def test_cli_dir_non_strict_exits_0_even_when_failing(capsys: Any) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "one").mkdir()
        _make_skill(Path(tmp) / "one", frontmatter="")
        rc = _run_cli(["--dir", str(Path(tmp))])
    assert rc == 0


def test_cli_json_output_parses(capsys: Any) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        p = _make_skill(Path(tmp))
        rc = _run_cli([str(p), "--json"])
    assert rc == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert isinstance(payload, list)
    assert len(payload) == 1
    assert payload[0]["passed"] is True
    assert payload[0]["rubric_version"] == sr.RUBRIC_VERSION


def test_cli_not_a_directory_exits_2(capsys: Any) -> None:
    rc = _run_cli(["--dir", "/nonexistent/definitely-not-a-dir"])
    assert rc == 2


def test_cli_missing_file_finding_surfaces(capsys: Any) -> None:
    rc = _run_cli(["/nonexistent/SKILL.md"])
    # File not found → R0 finding → not passed → exit 1
    assert rc == 1


# ===========================================================================
# E. Module-level constants
# ===========================================================================


def test_rubric_version_is_positive_integer() -> None:
    assert isinstance(sr.RUBRIC_VERSION, int)
    assert sr.RUBRIC_VERSION >= 1


def test_min_nonws_bytes_matches_floor() -> None:
    assert sr.MIN_NONWS_BYTES == 512
