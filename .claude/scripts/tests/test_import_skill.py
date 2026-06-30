"""PLAN-033 tests — import-skill.py attribution + SP-NNN wrapper."""
from __future__ import annotations

import importlib.util
import io
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List

import pytest


def _load_module():
    here = Path(__file__).resolve().parent.parent
    src = here / "import-skill.py"
    mod_name = "import_skill_under_test"
    spec = importlib.util.spec_from_file_location(mod_name, src)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


imp = _load_module()


# Build a source SKILL.md that passes the rubric for test fixtures.
_GOOD_BODY = "\n".join(
    [
        "# Sample",
        "",
        "## Purpose",
        "",
        "Body long enough to pass the 512-byte floor. " * 12,
        "",
        "## Checklist",
        "",
        "- [ ] Item a",
        "- [ ] Item b",
        "- [ ] Item c",
    ]
)


def _write_source(tmp: Path, frontmatter: str = None, body: str = _GOOD_BODY) -> Path:
    if frontmatter is None:
        frontmatter = (
            "---\n"
            "name: upstream-skill\n"
            "description: An upstream skill imported as a test fixture.\n"
            "trigger: foo bar\n"
            "---\n\n"
        )
    # Rubric R1 requires filename == SKILL.md. Use a unique subdirectory.
    sub = tmp / "upstream-dir"
    sub.mkdir(exist_ok=True)
    p = sub / "SKILL.md"
    p.write_text(frontmatter + body, encoding="utf-8")
    return p


# ===========================================================================
# A. provenance builder
# ===========================================================================


def test_build_provenance_has_all_required_keys() -> None:
    prov = imp.build_provenance(
        upstream="org/repo@v1.0",
        license_spdx="CC-BY-4.0",
        sp_nnn="SP-042",
    )
    assert set(prov.keys()) >= {"source", "license", "sp_chain", "imported_at", "imported_by"}


def test_build_provenance_optional_owner_sha() -> None:
    prov = imp.build_provenance(
        upstream="org/repo@v1.0",
        license_spdx="CC-BY-4.0",
        sp_nnn="SP-042",
        owner_sha256="a" * 64,
    )
    assert "owner_sha256" in prov


def test_build_provenance_quotes_source_string() -> None:
    prov = imp.build_provenance("org/repo@v1.0", "CC-BY-4.0", "SP-042")
    assert prov["source"].startswith('"') and prov["source"].endswith('"')


def test_build_provenance_iso_timestamp_format() -> None:
    prov = imp.build_provenance("org/repo@v1.0", "CC-BY-4.0", "SP-042")
    # 2026-04-19T12:34:56Z shape
    assert re.match(
        r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", prov["imported_at"]
    )


# ===========================================================================
# B. frontmatter merge
# ===========================================================================


def test_merge_preserves_existing_keys_and_appends_provenance() -> None:
    original = "name: orig\ndescription: orig desc\ntrigger: foo"
    provenance = imp.build_provenance("org/repo@v1.0", "CC-BY-4.0", "SP-042")
    merged = imp._merge_frontmatter(original, provenance)
    assert "name: orig" in merged
    assert "description: orig desc" in merged
    assert "trigger: foo" in merged
    assert "source:" in merged
    assert "license:" in merged
    assert "sp_chain: SP-042" in merged


def test_merge_replaces_existing_provenance_keys() -> None:
    original = (
        "name: x\n"
        "description: y\n"
        "license: MIT\n"
        "source: legacy/source"
    )
    provenance = {"source": '"new/upstream@v2"', "license": '"CC-BY-4.0"'}
    merged = imp._merge_frontmatter(original, provenance)
    assert "MIT" not in merged
    assert "legacy/source" not in merged
    assert '"CC-BY-4.0"' in merged
    assert '"new/upstream@v2"' in merged


def test_merge_keeps_original_order_for_non_provenance_keys() -> None:
    original = "name: x\ndescription: y\ntrigger: foo\nbar: qux"
    provenance = imp.build_provenance("o/r@1", "CC-BY-4.0", "SP-001")
    merged = imp._merge_frontmatter(original, provenance)
    lines = merged.splitlines()
    # Original keys appear first (in order), provenance after.
    idx_name = next(i for i, ln in enumerate(lines) if ln.startswith("name:"))
    idx_desc = next(i for i, ln in enumerate(lines) if ln.startswith("description:"))
    idx_trigger = next(i for i, ln in enumerate(lines) if ln.startswith("trigger:"))
    idx_bar = next(i for i, ln in enumerate(lines) if ln.startswith("bar:"))
    idx_source = next(i for i, ln in enumerate(lines) if ln.startswith("source:"))
    assert idx_name < idx_desc < idx_trigger < idx_bar < idx_source


# ===========================================================================
# C. run_import end-to-end
# ===========================================================================


def test_run_import_writes_target_with_provenance() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        src = _write_source(Path(tmp))
        # Use monkeypatched target path under the tmp dir to avoid
        # writing into the real repo tree.
        fake_target = Path(tmp) / "out" / "SKILL.md"
        _orig = imp.target_path
        try:
            imp.target_path = lambda d, s: fake_target
            tgt = imp.run_import(
                source=src,
                domain="community",
                slug="sample",
                upstream="org/repo@v1",
                license_spdx="CC-BY-4.0",
                sp_nnn="SP-099",
            )
        finally:
            imp.target_path = _orig
        assert tgt == fake_target
        out = fake_target.read_text(encoding="utf-8")
        assert "sp_chain: SP-099" in out
        assert "CC-BY-4.0" in out
        assert "name: upstream-skill" in out  # original preserved


def test_run_import_fails_when_target_exists_without_force() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        src = _write_source(Path(tmp))
        fake_target = Path(tmp) / "out" / "SKILL.md"
        fake_target.parent.mkdir(parents=True)
        fake_target.write_text("existing", encoding="utf-8")
        _orig = imp.target_path
        try:
            imp.target_path = lambda d, s: fake_target
            with pytest.raises(FileExistsError):
                imp.run_import(
                    source=src,
                    domain="community",
                    slug="sample",
                    upstream="org/repo@v1",
                    license_spdx="CC-BY-4.0",
                    sp_nnn="SP-099",
                )
        finally:
            imp.target_path = _orig


def test_run_import_force_overwrites_existing() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        src = _write_source(Path(tmp))
        fake_target = Path(tmp) / "out" / "SKILL.md"
        fake_target.parent.mkdir(parents=True)
        fake_target.write_text("stale", encoding="utf-8")
        _orig = imp.target_path
        try:
            imp.target_path = lambda d, s: fake_target
            tgt = imp.run_import(
                source=src,
                domain="community",
                slug="sample",
                upstream="org/repo@v1",
                license_spdx="CC-BY-4.0",
                sp_nnn="SP-099",
                force=True,
            )
            assert "stale" not in tgt.read_text(encoding="utf-8")
        finally:
            imp.target_path = _orig


def test_run_import_rejects_source_that_fails_rubric() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        # Source has no frontmatter → rubric R3 fail.
        bad = _write_source(Path(tmp), frontmatter="")
        fake_target = Path(tmp) / "out" / "SKILL.md"
        _orig = imp.target_path
        try:
            imp.target_path = lambda d, s: fake_target
            with pytest.raises(ValueError, match="rubric"):
                imp.run_import(
                    source=bad,
                    domain="community",
                    slug="sample",
                    upstream="org/repo@v1",
                    license_spdx="CC-BY-4.0",
                    sp_nnn="SP-099",
                )
        finally:
            imp.target_path = _orig


def test_run_import_skip_rubric_bypasses_gate() -> None:
    # PLAN-045 Wave 1 F-01-08: --skip-rubric now requires Owner auth
    # (owner_sha256 + .asc signature + signer allowlist). The test
    # monkey-patches ``_verify_skip_rubric_authorization`` to return a
    # fake signer fpr so the gate logic is exercised WITHOUT needing
    # a real GPG keyring in this unit test (the real-gpg path is
    # covered by ``test_import_skill_skip_rubric_auth.py``).
    with tempfile.TemporaryDirectory() as tmp:
        bad = _write_source(Path(tmp), frontmatter="")  # still bad
        fake_target = Path(tmp) / "out" / "SKILL.md"
        _orig_target = imp.target_path
        _orig_verify = imp._verify_skip_rubric_authorization
        try:
            imp.target_path = lambda d, s: fake_target
            imp._verify_skip_rubric_authorization = (
                lambda *a, **kw: "0000000000000000000000000000000000000000"
            )
            with pytest.raises(ValueError, match="frontmatter"):
                imp.run_import(
                    source=bad,
                    domain="community",
                    slug="sample",
                    upstream="org/repo@v1",
                    license_spdx="CC-BY-4.0",
                    sp_nnn="SP-099",
                    owner_sha256="a" * 64,
                    skip_rubric=True,
                )
        finally:
            imp.target_path = _orig_target
            imp._verify_skip_rubric_authorization = _orig_verify


def test_license_allowlist_rejects_unknown() -> None:
    """PLAN-045 F-14-03: --license must be in SPDX allowlist."""
    with tempfile.TemporaryDirectory() as tmp:
        src = _write_source(Path(tmp))
        with pytest.raises(ValueError, match="not in the SPDX allowlist"):
            imp.run_import(
                source=src,
                domain="community",
                slug="sample",
                upstream="org/repo@v1",
                license_spdx="AGPL-3.0",  # not in allowlist
                sp_nnn="SP-099",
            )


def test_license_allowlist_accepts_cc_by() -> None:
    """CC-BY-4.0 is in the built-in allowlist."""
    with tempfile.TemporaryDirectory() as tmp:
        src = _write_source(Path(tmp))
        fake_target = Path(tmp) / "out" / "SKILL.md"
        _orig = imp.target_path
        try:
            imp.target_path = lambda d, s: fake_target
            imp.run_import(
                source=src,
                domain="community",
                slug="cc-by-ok",
                upstream="org/repo@v1",
                license_spdx="CC-BY-4.0",
                sp_nnn="SP-099",
            )
        finally:
            imp.target_path = _orig
        assert fake_target.is_file()


def test_license_allowlist_verbose_form_normalised() -> None:
    """Verbose form 'Apache 2.0' canonicalises to 'Apache-2.0'."""
    with tempfile.TemporaryDirectory() as tmp:
        src = _write_source(Path(tmp))
        fake_target = Path(tmp) / "out" / "SKILL.md"
        _orig = imp.target_path
        try:
            imp.target_path = lambda d, s: fake_target
            imp.run_import(
                source=src,
                domain="community",
                slug="apache-ok",
                upstream="org/repo@v1",
                license_spdx="Apache 2.0",
                sp_nnn="SP-099",
            )
        finally:
            imp.target_path = _orig
        # Verify the canonical form lands in the output frontmatter.
        text = fake_target.read_text(encoding="utf-8")
        assert 'license: "Apache-2.0"' in text


def test_upstream_at_main_rejected() -> None:
    """PLAN-045 F-11-03: @main is a mutable branch ref, reject."""
    with tempfile.TemporaryDirectory() as tmp:
        src = _write_source(Path(tmp))
        with pytest.raises(ValueError, match="mutable branch ref"):
            imp.run_import(
                source=src,
                domain="community",
                slug="sample",
                upstream="sickn33/antigravity-awesome-skills@main",
                license_spdx="CC-BY-4.0",
                sp_nnn="SP-099",
            )


def test_upstream_at_master_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        src = _write_source(Path(tmp))
        with pytest.raises(ValueError, match="mutable branch ref"):
            imp.run_import(
                source=src,
                domain="community",
                slug="sample",
                upstream="org/repo@master",
                license_spdx="CC-BY-4.0",
                sp_nnn="SP-099",
            )


def test_upstream_commit_sha_accepted() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        src = _write_source(Path(tmp))
        fake_target = Path(tmp) / "out" / "SKILL.md"
        _orig = imp.target_path
        try:
            imp.target_path = lambda d, s: fake_target
            imp.run_import(
                source=src,
                domain="community",
                slug="sha-ok",
                upstream="org/repo@" + ("a" * 40),
                license_spdx="CC-BY-4.0",
                sp_nnn="SP-099",
            )
        finally:
            imp.target_path = _orig
        assert fake_target.is_file()


def test_upstream_tag_accepted() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        src = _write_source(Path(tmp))
        fake_target = Path(tmp) / "out" / "SKILL.md"
        _orig = imp.target_path
        try:
            imp.target_path = lambda d, s: fake_target
            imp.run_import(
                source=src,
                domain="community",
                slug="tag-ok",
                upstream="org/repo@v1.2.3",
                license_spdx="CC-BY-4.0",
                sp_nnn="SP-099",
            )
        finally:
            imp.target_path = _orig
        assert fake_target.is_file()


def test_upstream_missing_at_rejected() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        src = _write_source(Path(tmp))
        with pytest.raises(ValueError, match="commit SHA or immutable tag"):
            imp.run_import(
                source=src,
                domain="community",
                slug="sample",
                upstream="org/repo-without-ref",
                license_spdx="CC-BY-4.0",
                sp_nnn="SP-099",
            )


def test_license_extra_allows_custom() -> None:
    """--license-extra augments the built-in allowlist."""
    with tempfile.TemporaryDirectory() as tmp:
        src = _write_source(Path(tmp))
        fake_target = Path(tmp) / "out" / "SKILL.md"
        _orig = imp.target_path
        try:
            imp.target_path = lambda d, s: fake_target
            imp.run_import(
                source=src,
                domain="community",
                slug="custom-ok",
                upstream="org/repo@v1",
                license_spdx="PROJECT-SPECIFIC-1.0",
                sp_nnn="SP-099",
                license_extra=["PROJECT-SPECIFIC-1.0"],
            )
        finally:
            imp.target_path = _orig
        assert fake_target.is_file()


def test_skip_rubric_without_owner_sha256_fails() -> None:
    # PLAN-045 Wave 1 F-01-08 new contract: skip-rubric without
    # --owner-sha256 is a hard fail with a stable reason.
    with tempfile.TemporaryDirectory() as tmp:
        src = _write_source(Path(tmp))
        with pytest.raises(ValueError, match="owner-sha256"):
            imp.run_import(
                source=src,
                domain="community",
                slug="sample",
                upstream="org/repo@v1",
                license_spdx="CC-BY-4.0",
                sp_nnn="SP-099",
                skip_rubric=True,
            )


def test_skip_rubric_with_invalid_owner_sha256_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        src = _write_source(Path(tmp))
        with pytest.raises(ValueError, match="64-hex"):
            imp.run_import(
                source=src,
                domain="community",
                slug="sample",
                upstream="org/repo@v1",
                license_spdx="CC-BY-4.0",
                sp_nnn="SP-099",
                owner_sha256="not-hex",
                skip_rubric=True,
            )


def test_skip_rubric_without_signature_fails() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        src = _write_source(Path(tmp))
        with pytest.raises(ValueError, match="detached GPG signature"):
            imp.run_import(
                source=src,
                domain="community",
                slug="sample",
                upstream="org/repo@v1",
                license_spdx="CC-BY-4.0",
                sp_nnn="SP-099",
                owner_sha256="a" * 64,
                skip_rubric=True,
            )


def test_run_import_missing_source_raises() -> None:
    fake = Path("/nonexistent/SKILL.md")
    with pytest.raises(FileNotFoundError):
        imp.run_import(
            source=fake,
            domain="community",
            slug="sample",
            upstream="org/repo@v1",
            license_spdx="CC-BY-4.0",
            sp_nnn="SP-099",
        )


# ===========================================================================
# D. NOTICE append
# ===========================================================================


def test_notice_append_creates_file_with_attribution_row() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        src = _write_source(Path(tmp))
        fake_target = Path(tmp) / "out" / "SKILL.md"
        notice = Path(tmp) / "NOTICE.md"
        _orig = imp.target_path
        try:
            imp.target_path = lambda d, s: fake_target
            imp.run_import(
                source=src,
                domain="community",
                slug="sample",
                upstream="org/repo@v1",
                license_spdx="CC-BY-4.0",
                sp_nnn="SP-099",
                notice_path=notice,
            )
        finally:
            imp.target_path = _orig
        text = notice.read_text(encoding="utf-8")
        assert "community/skills/sample/SKILL.md" in text
        assert "org/repo@v1" in text
        assert "CC-BY-4.0" in text
        assert "SP-099" in text


def test_notice_append_does_not_truncate_existing() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        src = _write_source(Path(tmp))
        fake_target = Path(tmp) / "out" / "SKILL.md"
        notice = Path(tmp) / "NOTICE.md"
        notice.write_text("# Existing header\n\nOld line.\n", encoding="utf-8")
        _orig = imp.target_path
        try:
            imp.target_path = lambda d, s: fake_target
            imp.run_import(
                source=src,
                domain="community",
                slug="sample",
                upstream="org/repo@v1",
                license_spdx="CC-BY-4.0",
                sp_nnn="SP-099",
                notice_path=notice,
            )
        finally:
            imp.target_path = _orig
        text = notice.read_text(encoding="utf-8")
        assert "Existing header" in text
        assert "Old line." in text
        assert "community/skills/sample/SKILL.md" in text


# ===========================================================================
# E. CLI
# ===========================================================================


def test_cli_round_trip_succeeds(tmp_path: Path, capsys: Any) -> None:
    src = _write_source(tmp_path)
    fake_target = tmp_path / "out" / "SKILL.md"
    _orig = imp.target_path
    try:
        imp.target_path = lambda d, s: fake_target
        rc = imp.main(
            [
                "--source",
                str(src),
                "--domain",
                "community",
                "--slug",
                "sample",
                "--upstream",
                "org/repo@v1.0",
                "--license",
                "CC-BY-4.0",
                "--sp-nnn",
                "SP-042",
            ]
        )
    finally:
        imp.target_path = _orig
    assert rc == 0
    assert fake_target.is_file()


def test_cli_exits_1_when_target_exists(tmp_path: Path) -> None:
    src = _write_source(tmp_path)
    fake_target = tmp_path / "out" / "SKILL.md"
    fake_target.parent.mkdir(parents=True)
    fake_target.write_text("exists", encoding="utf-8")
    _orig = imp.target_path
    try:
        imp.target_path = lambda d, s: fake_target
        rc = imp.main(
            [
                "--source",
                str(src),
                "--domain",
                "community",
                "--slug",
                "sample",
                "--upstream",
                "org/repo@v1.0",
                "--license",
                "CC-BY-4.0",
                "--sp-nnn",
                "SP-042",
            ]
        )
    finally:
        imp.target_path = _orig
    assert rc == 1


def test_cli_owner_sha256_flag_propagated(tmp_path: Path) -> None:
    src = _write_source(tmp_path)
    fake_target = tmp_path / "out" / "SKILL.md"
    _orig = imp.target_path
    owner_sha = "b" * 64
    try:
        imp.target_path = lambda d, s: fake_target
        rc = imp.main(
            [
                "--source",
                str(src),
                "--domain",
                "community",
                "--slug",
                "sample",
                "--upstream",
                "org/repo@v1.0",
                "--license",
                "CC-BY-4.0",
                "--sp-nnn",
                "SP-042",
                "--owner-sha256",
                owner_sha,
            ]
        )
    finally:
        imp.target_path = _orig
    assert rc == 0
    content = fake_target.read_text(encoding="utf-8")
    assert f"owner_sha256: {owner_sha}" in content


# ===========================================================================
# F. Module-level constants
# ===========================================================================


def test_provenance_keys_are_stable_list() -> None:
    assert "source" in imp._PROVENANCE_KEYS
    assert "license" in imp._PROVENANCE_KEYS
    assert "sp_chain" in imp._PROVENANCE_KEYS
    assert "imported_at" in imp._PROVENANCE_KEYS


def test_skills_domain_root_points_into_repo() -> None:
    assert imp.SKILLS_DOMAIN_ROOT.name == "domains"
    assert imp.SKILLS_DOMAIN_ROOT.parent.name == "skills"


# ===========================================================================
# G. Provenance value shape (additional parametrized coverage)
# ===========================================================================


@pytest.mark.parametrize(
    "upstream,license_spdx,sp",
    [
        ("org-one/repo-a@v1.0", "CC-BY-4.0", "SP-001"),
        ("owner2/pkg@2023.10", "MIT", "SP-042"),
        ("long-org-name-example/another-skill-repo@1.2.3", "Apache-2.0", "SP-100"),
    ],
)
def test_provenance_carries_args(upstream: str, license_spdx: str, sp: str) -> None:
    prov = imp.build_provenance(upstream, license_spdx, sp)
    assert upstream in prov["source"]
    assert license_spdx in prov["license"]
    assert prov["sp_chain"] == sp


# ===========================================================================
# H. _split_frontmatter helper — independent tests
# ===========================================================================


def test_split_frontmatter_handles_no_frontmatter() -> None:
    fm, rest = imp._split_frontmatter("# No frontmatter here\n\nBody.")
    assert fm == ""
    assert rest.startswith("# No frontmatter here")


def test_split_frontmatter_separates_fences_and_body() -> None:
    content = "---\nname: x\ndescription: y\n---\n\nBody text.\n"
    fm, rest = imp._split_frontmatter(content)
    assert "name: x" in fm
    assert "description: y" in fm
    assert rest.startswith("\nBody text.") or rest.startswith("Body text.")


def test_split_frontmatter_multiline_description() -> None:
    content = "---\nname: x\ndescription: |\n  multi\n  line\n---\nBody"
    fm, rest = imp._split_frontmatter(content)
    assert "multi" in fm
    assert rest.startswith("Body")


# ===========================================================================
# I. Sequential multi-import integration
# ===========================================================================


def test_import_three_skills_sequentially(tmp_path: Path) -> None:
    """Sanity: 3 imports in a row produce 3 distinct targets + 3 NOTICE rows."""
    notice = tmp_path / "NOTICE.md"
    notice.write_text("# Test NOTICE\n\n", encoding="utf-8")
    slugs = ["alpha", "beta", "gamma"]

    original_target_path = imp.target_path
    try:
        for slug in slugs:
            src_root = tmp_path / f"src-{slug}"
            src_root.mkdir(exist_ok=True)
            src = _write_source(src_root)
            fake_target = tmp_path / f"out-{slug}" / "SKILL.md"
            imp.target_path = lambda d, s, _ft=fake_target: _ft
            imp.run_import(
                source=src,
                domain="community",
                slug=slug,
                upstream=f"org/repo@v{slug}",
                license_spdx="CC-BY-4.0",
                sp_nnn=f"SP-{slug.upper()}",
                notice_path=notice,
            )
    finally:
        imp.target_path = original_target_path

    text = notice.read_text(encoding="utf-8")
    for slug in slugs:
        assert f"/skills/{slug}/SKILL.md" in text


# ===========================================================================
# J. Edge cases
# ===========================================================================


def test_source_with_windows_line_endings_still_parses(tmp_path: Path) -> None:
    # Source with CRLF should still parse frontmatter (regex DOTALL
    # accommodates the trailing \r).
    frontmatter = "---\r\nname: crlf\r\ndescription: crlf fixture\r\n---\r\n\r\n"
    body = (
        "## H\r\n"
        + ("word " * 200)
        + "\r\n- [ ] item\r\n"
    )
    src_dir = tmp_path / "crlf-src"
    src_dir.mkdir()
    src = src_dir / "SKILL.md"
    src.write_bytes((frontmatter + body).encode("utf-8"))
    # Even if CRLF breaks a rubric rule, skip-rubric should let us
    # import. (The rubric tests cover the CRLF-fail case separately.)
    # PLAN-045 Wave 1 F-01-08: skip_rubric requires auth; mock the
    # verifier for this CRLF-parsing edge case.
    fake_target = tmp_path / "out" / "SKILL.md"
    _orig_target = imp.target_path
    _orig_verify = imp._verify_skip_rubric_authorization
    try:
        imp.target_path = lambda d, s: fake_target
        imp._verify_skip_rubric_authorization = (
            lambda *a, **kw: "0000000000000000000000000000000000000000"
        )
        imp.run_import(
            source=src,
            domain="community",
            slug="crlf",
            upstream="org/repo@v1",
            license_spdx="CC-BY-4.0",
            sp_nnn="SP-CRLF",
            owner_sha256="b" * 64,
            skip_rubric=True,
        )
    finally:
        imp.target_path = _orig_target
        imp._verify_skip_rubric_authorization = _orig_verify
    assert fake_target.is_file()


# ===========================================================================
# J. PLAN-045 F-11-03 — strict 40-hex SHA + imported_sha: provenance field
# ===========================================================================


def test_upstream_short_sha_rejected() -> None:
    """Short SHAs (<40 hex) are rejected — collision-prone for supply chain."""
    with tempfile.TemporaryDirectory() as tmp:
        src = _write_source(Path(tmp))
        with pytest.raises(ValueError, match="short"):
            imp.run_import(
                source=src,
                domain="community",
                slug="sample",
                upstream="org/repo@abc1234",
                license_spdx="CC-BY-4.0",
                sp_nnn="SP-099",
            )


def test_upstream_full_40hex_sha_populates_imported_sha() -> None:
    """A 40-hex upstream ref writes `imported_sha:` into output frontmatter."""
    sha = "b" * 40
    with tempfile.TemporaryDirectory() as tmp:
        src = _write_source(Path(tmp))
        fake_target = Path(tmp) / "out" / "SKILL.md"
        _orig = imp.target_path
        try:
            imp.target_path = lambda d, s: fake_target
            imp.run_import(
                source=src,
                domain="community",
                slug="sample",
                upstream=f"org/repo@{sha}",
                license_spdx="CC-BY-4.0",
                sp_nnn="SP-099",
            )
        finally:
            imp.target_path = _orig
        text = fake_target.read_text(encoding="utf-8")
        assert f"imported_sha: {sha}" in text


def test_upstream_tag_does_not_populate_imported_sha() -> None:
    """Tag-based upstream does NOT emit imported_sha: (only SHAs do)."""
    with tempfile.TemporaryDirectory() as tmp:
        src = _write_source(Path(tmp))
        fake_target = Path(tmp) / "out" / "SKILL.md"
        _orig = imp.target_path
        try:
            imp.target_path = lambda d, s: fake_target
            imp.run_import(
                source=src,
                domain="community",
                slug="sample",
                upstream="org/repo@v1.2.3",
                license_spdx="CC-BY-4.0",
                sp_nnn="SP-099",
            )
        finally:
            imp.target_path = _orig
        text = fake_target.read_text(encoding="utf-8")
        assert "imported_sha:" not in text


def test_upstream_uppercase_sha_normalised_to_lowercase() -> None:
    """Mixed-case 40-hex SHA input canonicalises to lowercase."""
    sha_upper = "C" * 40
    with tempfile.TemporaryDirectory() as tmp:
        src = _write_source(Path(tmp))
        fake_target = Path(tmp) / "out" / "SKILL.md"
        _orig = imp.target_path
        try:
            imp.target_path = lambda d, s: fake_target
            imp.run_import(
                source=src,
                domain="community",
                slug="sample",
                upstream=f"org/repo@{sha_upper}",
                license_spdx="CC-BY-4.0",
                sp_nnn="SP-099",
            )
        finally:
            imp.target_path = _orig
        text = fake_target.read_text(encoding="utf-8")
        assert f"imported_sha: {'c' * 40}" in text
        assert f"imported_sha: {sha_upper}" not in text


def test_upstream_at_HEAD_rejected() -> None:
    """PLAN-045 F-11-03: @HEAD is mutable, reject."""
    with tempfile.TemporaryDirectory() as tmp:
        src = _write_source(Path(tmp))
        with pytest.raises(ValueError, match="mutable branch ref"):
            imp.run_import(
                source=src,
                domain="community",
                slug="sample",
                upstream="org/repo@HEAD",
                license_spdx="CC-BY-4.0",
                sp_nnn="SP-099",
            )


def test_allowed_licenses_alias_matches_spdx_set() -> None:
    """PLAN-045 F-14-03: _ALLOWED_LICENSES is alias for _ALLOWED_SPDX_LICENSES."""
    assert imp._ALLOWED_LICENSES is imp._ALLOWED_SPDX_LICENSES
    for spdx in ("MIT", "Apache-2.0", "BSD-2-Clause", "BSD-3-Clause",
                 "ISC", "CC-BY-4.0", "Unlicense", "MPL-2.0"):
        assert spdx in imp._ALLOWED_LICENSES


def test_imported_sha_round_trip_via_build_provenance() -> None:
    """PLAN-045 F-11-03: build_provenance emits imported_sha for 40-hex ref."""
    sha = "d" * 40
    prov = imp.build_provenance(
        upstream=f"org/repo@{sha}",
        license_spdx="CC-BY-4.0",
        sp_nnn="SP-042",
    )
    assert prov.get("imported_sha") == sha
    # Tag-based upstream: no imported_sha emitted.
    prov_tag = imp.build_provenance(
        upstream="org/repo@v1.0",
        license_spdx="CC-BY-4.0",
        sp_nnn="SP-042",
    )
    assert "imported_sha" not in prov_tag
