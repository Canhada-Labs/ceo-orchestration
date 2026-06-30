"""Unit tests for `.claude/scripts/check-adr-chain.py` (PLAN-019 F-CHAOS-8).

Stdlib-only; Python >=3.9 compatible.
"""

from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path
from typing import Any


def _load_module():
    """Load the hyphenated script as a module (standard pattern in-repo)."""
    here = Path(__file__).resolve().parent.parent
    spec = importlib.util.spec_from_file_location(
        "check_adr_chain", here / "check-adr-chain.py"
    )
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


check_adr_chain = _load_module()


class TestADRChainParser(unittest.TestCase):
    def _write(self, d: Path, name: str, body: str) -> Path:
        p = d / name
        p.write_text(body, encoding="utf-8")
        return p

    def test_parses_double_asterisk_status(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            p = self._write(
                td_path,
                "ADR-001-foo.md",
                "# ADR-001: Foo\n\n**Status:** ACCEPTED (2026-04-17)\n",
            )
            d = check_adr_chain.parse_adr(p)
            self.assertEqual(d["status"], "ACCEPTED")

    def test_parses_hash_heading_status(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            p = self._write(
                td_path,
                "ADR-002-foo.md",
                "# ADR-002\n\n## Status: PROPOSED\n",
            )
            d = check_adr_chain.parse_adr(p)
            self.assertEqual(d["status"], "PROPOSED")

    def test_extracts_superseded_by_from_field(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            p = self._write(
                td_path,
                "ADR-003-foo.md",
                "# ADR-003\n\n**Status:** SUPERSEDED\n\nSuperseded-By: ADR-010 (2026-04-14)\n",
            )
            d = check_adr_chain.parse_adr(p)
            self.assertEqual(d["status"], "SUPERSEDED")
            self.assertIn("ADR-010", d["superseded_by"])  # type: ignore[arg-type]

    def test_extracts_inline_superseded_by_on_status_line(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            td_path = Path(td)
            p = self._write(
                td_path,
                "ADR-004-foo.md",
                "# ADR-004\n\n## Status: SUPERSEDED by ADR-020 (2026-04-14)\n\n> See ADR-020 §ADR-004 for details.\n",
            )
            d = check_adr_chain.parse_adr(p)
            # ADR-020 captured, ADR-004 (historical prose mention) NOT.
            self.assertIn("ADR-020", d["superseded_by"])  # type: ignore[arg-type]
            self.assertNotIn("ADR-004", d["superseded_by"])  # type: ignore[arg-type]


class TestADRChainValidation(unittest.TestCase):
    def _make_corpus(self, td: Path, files: dict) -> Path:
        for name, body in files.items():
            (td / name).write_text(body, encoding="utf-8")
        return td

    def test_clean_corpus_passes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = self._make_corpus(
                Path(td),
                {
                    "ADR-001-alpha.md": "# ADR-001\n\n**Status:** ACCEPTED (2026-04-17)\n",
                    "ADR-002-beta.md": "# ADR-002\n\n**Status:** PROPOSED\n",
                },
            )
            errors, warnings = check_adr_chain.validate_chain(d)
            self.assertEqual(errors, [])

    def test_missing_status_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = self._make_corpus(
                Path(td),
                {"ADR-001-alpha.md": "# ADR-001\n\nNo status here.\n"},
            )
            errors, _ = check_adr_chain.validate_chain(d)
            self.assertTrue(any("missing `Status:`" in e for e in errors))

    def test_superseded_without_successor_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = self._make_corpus(
                Path(td),
                {
                    "ADR-001-alpha.md": (
                        "# ADR-001\n\n**Status:** SUPERSEDED\n\n"
                        "This ADR is retired but does not name a replacement.\n"
                    ),
                },
            )
            errors, _ = check_adr_chain.validate_chain(d)
            self.assertTrue(
                any("SUPERSEDED but missing both" in e for e in errors),
                f"expected SUPERSEDED error, got {errors!r}",
            )

    def test_superseded_with_inline_retirement_note_passes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = self._make_corpus(
                Path(td),
                {
                    "ADR-001-alpha.md": (
                        "# ADR-001: Foo (SUPERSEDED — removed in PLAN-006 Phase 6b)\n\n"
                        "**Status:** SUPERSEDED (2026-04-13) — legacy/ removed in Sprint 6\n"
                    ),
                },
            )
            errors, _ = check_adr_chain.validate_chain(d)
            # Accepts either inline retirement note OR Superseded-By.
            self.assertEqual(
                [e for e in errors if "SUPERSEDED but missing" in e],
                [],
            )

    def test_invalid_filename_reports_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = self._make_corpus(
                Path(td),
                {"ADR-99-badnum.md": "# ADR-99\n\n**Status:** ACCEPTED\n"},
            )
            errors, _ = check_adr_chain.validate_chain(d)
            self.assertTrue(any("filename must match" in e for e in errors))

    def test_filename_with_dot_in_slug_accepted(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = self._make_corpus(
                Path(td),
                {
                    "ADR-011-event-stream-v2.1-flag.md": (
                        "# ADR-011\n\n**Status:** ACCEPTED\n"
                    ),
                },
            )
            errors, _ = check_adr_chain.validate_chain(d)
            self.assertEqual(
                [e for e in errors if "filename must match" in e],
                [],
            )

    def test_supersedes_points_at_non_superseded_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = self._make_corpus(
                Path(td),
                {
                    "ADR-001-old.md": "# ADR-001\n\n**Status:** ACCEPTED\n",
                    "ADR-002-new.md": (
                        "# ADR-002\n\n**Status:** ACCEPTED\n\n"
                        "Supersedes: ADR-001\n"
                    ),
                },
            )
            errors, _ = check_adr_chain.validate_chain(d)
            self.assertTrue(
                any("Supersedes=ADR-001" in e and "should be SUPERSEDED" in e for e in errors),
                f"expected Supersedes/status mismatch error, got {errors!r}",
            )

    def test_bidirectional_link_missing_is_warning(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = self._make_corpus(
                Path(td),
                {
                    "ADR-001-old.md": (
                        "# ADR-001\n\n**Status:** SUPERSEDED\n\n"
                        "Superseded-By: ADR-002\n"
                    ),
                    "ADR-002-new.md": (
                        "# ADR-002\n\n**Status:** ACCEPTED\n"
                    ),
                },
            )
            errors, warnings = check_adr_chain.validate_chain(d)
            self.assertTrue(
                any("missing bidirectional link" in w for w in warnings),
                f"expected bidirectional-link warning, got {warnings!r}",
            )
            self.assertEqual(errors, [])

    def test_main_exit_zero_on_clean(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = self._make_corpus(
                Path(td),
                {"ADR-001-alpha.md": "# ADR-001\n\n**Status:** ACCEPTED\n"},
            )
            rc = check_adr_chain.main(["--adr-dir", str(d)])
            self.assertEqual(rc, 0)

    def test_main_exit_one_on_broken_chain(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            d = self._make_corpus(
                Path(td),
                {"ADR-001-alpha.md": "# ADR-001\n\nno status\n"},
            )
            rc = check_adr_chain.main(["--adr-dir", str(d)])
            self.assertEqual(rc, 1)

    # ------------------------------------------------------------------
    # PLAN-113 Phase C CANON-ADR additions
    # ------------------------------------------------------------------

    def test_amend_filename_accepted(self) -> None:
        """ADR-NNN-AMEND-N-<slug>.md filenames must not trigger filename error."""
        with tempfile.TemporaryDirectory() as td:
            d = self._make_corpus(
                Path(td),
                {
                    "ADR-019-AMEND-1-confidence-gate.md": (
                        "# ADR-019-AMEND-1\n\n**Status:** ACCEPTED\n"
                    ),
                    "ADR-019-AMEND-2-CLASS-SHA_EXISTS.md": (
                        "# ADR-019-AMEND-2\n\n**Status:** ACCEPTED\n"
                    ),
                },
            )
            errors, _ = check_adr_chain.validate_chain(d)
            self.assertEqual(
                [e for e in errors if "filename must match" in e],
                [],
                f"AMEND filenames should not trigger filename error; got {errors!r}",
            )

    def test_049a_filename_accepted(self) -> None:
        """ADR-049a-<slug>.md (legacy 'a' suffix) must not trigger filename error."""
        with tempfile.TemporaryDirectory() as td:
            d = self._make_corpus(
                Path(td),
                {
                    "ADR-049a-worktree-policy.md": (
                        "# ADR-049a\n\n**Status:** ACCEPTED\n"
                    ),
                },
            )
            errors, _ = check_adr_chain.validate_chain(d)
            self.assertEqual(
                [e for e in errors if "filename must match" in e],
                [],
                f"049a variant should not trigger filename error; got {errors!r}",
            )

    def test_retracted_status_accepted(self) -> None:
        """RETRACTED must be a valid terminal status (not trigger 'must start with' error)."""
        with tempfile.TemporaryDirectory() as td:
            d = self._make_corpus(
                Path(td),
                {
                    "ADR-091-foo.md": (
                        "# ADR-091 (RETRACTED)\n\n**Status:** RETRACTED\n\n"
                        "RETRACTED — withdrawn before ACCEPTED. See audit-v2.\n"
                    ),
                },
            )
            errors, _ = check_adr_chain.validate_chain(d)
            self.assertEqual(
                [e for e in errors if "must start with" in e],
                [],
                f"RETRACTED status should be valid; got {errors!r}",
            )

    def test_h2_heading_blank_line_status(self) -> None:
        """## Status\\n\\n<VALUE> format (used by ADR-082..097) must be parsed."""
        with tempfile.TemporaryDirectory() as td:
            d = self._make_corpus(
                Path(td),
                {
                    "ADR-082-l7c.md": (
                        "# ADR-082 — L7c\n\n## Status\n\nACCEPTED — Wave A re-ceremony 2026-04-27\n"
                    ),
                },
            )
            errors, _ = check_adr_chain.validate_chain(d)
            self.assertEqual(
                [e for e in errors if "missing `Status:`" in e],
                [],
                f"H2+blank+value format should be parsed; got {errors!r}",
            )

    def test_superseded_by_deduplication(self) -> None:
        """A Superseded-By line that mentions the same ADR-NNN twice must not
        produce duplicate warnings."""
        with tempfile.TemporaryDirectory() as td:
            d = self._make_corpus(
                Path(td),
                {
                    "ADR-001-old.md": (
                        "# ADR-001\n\n**Status:** SUPERSEDED\n\n"
                        "**Superseded-By:** the Gate B criterion in [ADR-002](./ADR-002-foo.md) "
                        "§Sprint 6 Phase 6b — see ADR-002-foo §Gate-B-amendment.\n"
                    ),
                    "ADR-002-foo.md": (
                        "# ADR-002\n\n**Status:** ACCEPTED\n"
                    ),
                },
            )
            errors, warnings = check_adr_chain.validate_chain(d)
            # Should warn once about missing bidirectional link, NOT twice
            bidir_warnings = [w for w in warnings if "missing bidirectional link" in w]
            self.assertEqual(
                len(bidir_warnings),
                1,
                f"Expected exactly 1 bidirectional-link warning, got {warnings!r}",
            )

    def test_superseded_by_prefix_form_passes_check2(self) -> None:
        """Status: SUPERSEDED-BY-ADR-103 (with dashes, no spaces) must satisfy
        Check 2 (SUPERSEDED ADR must declare successor) since it starts with SUPERSEDED."""
        with tempfile.TemporaryDirectory() as td:
            d = self._make_corpus(
                Path(td),
                {
                    "ADR-093-moratorium.md": (
                        "# ADR-093\n\n## Status\n\n"
                        "SUPERSEDED-BY-ADR-103 (2026-05-03) — original ACCEPTED 2026-04-27\n\n"
                        "Superseded-By: ADR-103\n"
                    ),
                    "ADR-103-purge.md": (
                        "# ADR-103\n\n**Status:** ACCEPTED\n\n"
                        "Supersedes: ADR-093\n"
                    ),
                },
            )
            errors, _ = check_adr_chain.validate_chain(d)
            self.assertEqual(errors, [], f"SUPERSEDED-BY-NNN form should pass; got {errors!r}")

    def test_supersedes_parenthetical_qualifier_parsed(self) -> None:
        """**Supersedes (partial):** [ADR-004]... form (with parenthetical qualifier)
        must be parsed and produce a supersedes ref, so the bidirectional link
        check resolves correctly."""
        with tempfile.TemporaryDirectory() as td:
            d = self._make_corpus(
                Path(td),
                {
                    "ADR-004-old.md": (
                        "# ADR-004\n\n**Status:** SUPERSEDED (2026-04-13)\n\n"
                        "**Superseded-By:** Sprint 6 Phase 6b removal commit; "
                        "Gate B formalized in [ADR-014](./ADR-014-hook-migration.md).\n"
                    ),
                    "ADR-014-hook-migration.md": (
                        "# ADR-014\n\n## Status: ACCEPTED (2026-04-13)\n\n"
                        "**Supersedes (partial):** [ADR-004](./ADR-004-old.md) "
                        "§Sprint 6 Phase 6b — Gate B unlocked legacy/ removal.\n"
                    ),
                },
            )
            errors, warnings = check_adr_chain.validate_chain(d)
            # Both directions satisfied → no bidirectional warning.
            bidir = [w for w in warnings if "missing bidirectional link" in w]
            self.assertEqual(
                bidir,
                [],
                f"Parenthetical-qualifier Supersedes should satisfy bidirectional check; "
                f"warnings={warnings!r}",
            )

    def test_yaml_supersedes_block_sequence_primary_ref_only(self) -> None:
        """A YAML `supersedes:` block-sequence with `rename_source: ADR-111 (... via ADR-117 ...)`
        must extract only ADR-111 (the primary), NOT ADR-117 (the parenthetical policy ref)."""
        with tempfile.TemporaryDirectory() as td:
            d = self._make_corpus(
                Path(td),
                {
                    "ADR-111-old.md": (
                        "# ADR-111\n\n**Status:** SUPERSEDED\n\nSuperseded-By: ADR-120\n"
                    ),
                    "ADR-117-rename-policy.md": (
                        "# ADR-117\n\n**Status:** ACCEPTED\n"
                    ),
                    "ADR-120-new.md": (
                        "---\n"
                        "id: ADR-120\n"
                        "status: ACCEPTED\n"
                        "supersedes:\n"
                        "  - rename_source: ADR-111-old "
                        "(ID 111; same scope; renamed via ADR-117 doctrine)\n"
                        "superseded_by: []\n"
                        "---\n"
                        "# ADR-120\n\n## §1. Status\n\nACCEPTED\n"
                    ),
                },
            )
            errors, warnings = check_adr_chain.validate_chain(d)
            # ADR-111 superseded_by ADR-120 + ADR-120 supersedes ADR-111 → clean.
            self.assertEqual(errors, [], f"expected no errors; got {errors!r}")
            # No spurious ADR-117 error (it's ACCEPTED, not being superseded).
            self.assertFalse(
                any("ADR-117" in e for e in errors),
                f"ADR-117 should not be flagged; errors={errors!r}",
            )
            bidir = [w for w in warnings if "missing bidirectional link" in w]
            self.assertEqual(bidir, [], f"bidirectional link should be satisfied; warnings={warnings!r}")


class TestAmendLineageValidation(unittest.TestCase):
    """Check 5 — amends: lineage validation for AMEND files."""

    def _make_corpus(self, td: Path, files: dict) -> Path:
        for name, body in files.items():
            (td / name).write_text(body, encoding="utf-8")
        return td

    # ------------------------------------------------------------------
    # 5a: missing amends: target is an error
    # ------------------------------------------------------------------

    def test_amend_file_missing_amends_field_is_error(self) -> None:
        """An AMEND file with no amends: declaration must fail."""
        with tempfile.TemporaryDirectory() as td:
            d = self._make_corpus(
                Path(td),
                {
                    "ADR-010-base.md": "# ADR-010\n\n**Status:** ACCEPTED\n",
                    "ADR-010-AMEND-1-some-change.md": (
                        "# ADR-010-AMEND-1\n\n**Status:** ACCEPTED\n\n"
                        "Amends nothing declared here.\n"
                    ),
                },
            )
            errors, _ = check_adr_chain.validate_chain(d)
            self.assertTrue(
                any("declares no `amends:` target" in e for e in errors),
                f"expected missing-amends error; got {errors!r}",
            )

    # ------------------------------------------------------------------
    # 5b: broken amends: target (nonexistent ADR) is an error
    # ------------------------------------------------------------------

    def test_amend_file_with_nonexistent_amends_target_is_error(self) -> None:
        """amends: ADR-999 where ADR-999 does not exist must fail."""
        with tempfile.TemporaryDirectory() as td:
            d = self._make_corpus(
                Path(td),
                {
                    # No ADR-999 in corpus
                    "ADR-010-AMEND-1-some-change.md": (
                        "# ADR-010-AMEND-1\n\n**Status:** ACCEPTED\n\n"
                        "amends: ADR-999\n"
                    ),
                },
            )
            errors, _ = check_adr_chain.validate_chain(d)
            self.assertTrue(
                any("ADR-999" in e and "nonexistent" in e for e in errors),
                f"expected nonexistent-target error; got {errors!r}",
            )

    def test_amend_file_bold_markdown_nonexistent_target_is_error(self) -> None:
        """**Amends:** ADR-999 where ADR-999 does not exist must fail."""
        with tempfile.TemporaryDirectory() as td:
            d = self._make_corpus(
                Path(td),
                {
                    "ADR-010-AMEND-1-some-change.md": (
                        "# ADR-010-AMEND-1\n\n**Status:** ACCEPTED\n\n"
                        "**Amends:** ADR-999\n"
                    ),
                },
            )
            errors, _ = check_adr_chain.validate_chain(d)
            self.assertTrue(
                any("ADR-999" in e and "nonexistent" in e for e in errors),
                f"expected nonexistent-target error (bold form); got {errors!r}",
            )

    # ------------------------------------------------------------------
    # 5c: valid amend chains pass
    # ------------------------------------------------------------------

    def test_valid_amend_chain_passes(self) -> None:
        """Base + AMEND-1 with correct amends: field must pass."""
        with tempfile.TemporaryDirectory() as td:
            d = self._make_corpus(
                Path(td),
                {
                    "ADR-042-base.md": "# ADR-042\n\n**Status:** ACCEPTED\n",
                    "ADR-042-AMEND-1-expansion.md": (
                        "# ADR-042-AMEND-1\n\n**Status:** ACCEPTED\n\n"
                        "amends: ADR-042\n"
                    ),
                },
            )
            errors, _ = check_adr_chain.validate_chain(d)
            amend_errors = [e for e in errors if "amend" in e.lower() or "AMEND" in e]
            self.assertEqual(amend_errors, [], f"valid chain should pass; got {errors!r}")

    def test_valid_amend_chain_bold_markdown_passes(self) -> None:
        """Base + AMEND-1 using **Amends:** bold-markdown form must pass."""
        with tempfile.TemporaryDirectory() as td:
            d = self._make_corpus(
                Path(td),
                {
                    "ADR-019-base.md": "# ADR-019\n\n**Status:** ACCEPTED\n",
                    "ADR-019-AMEND-1-some-change.md": (
                        "# ADR-019-AMEND-1\n\n**Status:** ACCEPTED\n\n"
                        "**Amends:** ADR-019\n"
                    ),
                },
            )
            errors, _ = check_adr_chain.validate_chain(d)
            amend_errors = [e for e in errors if "amend" in e.lower() or "AMEND" in e]
            self.assertEqual(amend_errors, [], f"bold-markdown amends form should pass; got {errors!r}")

    def test_valid_amend_chain_two_levels_passes(self) -> None:
        """Base + AMEND-1 + AMEND-2 forming a complete chain must pass."""
        with tempfile.TemporaryDirectory() as td:
            d = self._make_corpus(
                Path(td),
                {
                    "ADR-055-base.md": "# ADR-055\n\n**Status:** ACCEPTED\n",
                    "ADR-055-AMEND-1-drain.md": (
                        "# ADR-055-AMEND-1\n\n**Status:** ACCEPTED\n\n"
                        "amends: ADR-055\n"
                    ),
                    "ADR-055-AMEND-2-marker.md": (
                        "# ADR-055-AMEND-2\n\n**Status:** ACCEPTED\n\n"
                        "amends: ADR-055\n"
                    ),
                },
            )
            errors, _ = check_adr_chain.validate_chain(d)
            amend_errors = [e for e in errors if "chain gap" in e]
            self.assertEqual(amend_errors, [], f"complete 2-level chain should pass; got {errors!r}")

    def test_amend_predecessor_missing_is_error(self) -> None:
        """AMEND-2 without AMEND-1 present (and no README gap doc) must fail."""
        with tempfile.TemporaryDirectory() as td:
            d = self._make_corpus(
                Path(td),
                {
                    # AMEND-1 is absent; no README documenting the gap
                    "ADR-020-base.md": "# ADR-020\n\n**Status:** ACCEPTED\n",
                    "ADR-020-AMEND-2-change.md": (
                        "# ADR-020-AMEND-2\n\n**Status:** ACCEPTED\n\n"
                        "amends: ADR-020\n"
                    ),
                },
            )
            errors, _ = check_adr_chain.validate_chain(d)
            self.assertTrue(
                any("chain gap" in e and "ADR-020-AMEND-1" in e for e in errors),
                f"expected chain-gap error for missing AMEND-1; got {errors!r}",
            )

    # ------------------------------------------------------------------
    # 5d: README-documented gaps are allowed
    # ------------------------------------------------------------------

    def test_readme_documented_gap_is_allowed(self) -> None:
        """An AMEND-2 with missing AMEND-1 is allowed when the README
        documents the gap under 'Known amendment chain gaps'."""
        with tempfile.TemporaryDirectory() as td:
            readme_body = (
                "# ADR README\n\n"
                "## Known amendment chain gaps (honest documentation)\n\n"
                "**ADR-040: base → AMEND-2 (no AMEND-1)**\n\n"
                "This gap is intentional per design.\n\n"
                "## When to write an ADR\n\nWrite it.\n"
            )
            d = self._make_corpus(
                Path(td),
                {
                    "README.md": readme_body,
                    "ADR-040-base.md": "# ADR-040\n\n**Status:** ACCEPTED\n",
                    # AMEND-1 is intentionally absent; documented in README
                    "ADR-040-AMEND-2-blocking.md": (
                        "# ADR-040-AMEND-2\n\n**Status:** ACCEPTED\n\n"
                        "amends: ADR-040\n"
                    ),
                },
            )
            errors, _ = check_adr_chain.validate_chain(d)
            gap_errors = [e for e in errors if "chain gap" in e]
            self.assertEqual(
                gap_errors,
                [],
                f"README-documented gap should be allowed; got {errors!r}",
            )

    # ------------------------------------------------------------------
    # 5e: YAML inline-list form [ADR-NNN] passes
    # ------------------------------------------------------------------

    def test_amend_yaml_inline_list_form_passes(self) -> None:
        """amends: [ADR-118] YAML inline-list form must be parsed correctly."""
        with tempfile.TemporaryDirectory() as td:
            d = self._make_corpus(
                Path(td),
                {
                    "ADR-118-base.md": "# ADR-118\n\n**Status:** ACCEPTED\n",
                    "ADR-118-AMEND-1-flip.md": (
                        "# ADR-118-AMEND-1\n\nstatus: ACCEPTED\n\n"
                        "amends: [ADR-118]\n"
                    ),
                },
            )
            errors, _ = check_adr_chain.validate_chain(d)
            amend_errors = [e for e in errors if "amend" in e.lower() or "nonexistent" in e]
            self.assertEqual(amend_errors, [], f"YAML inline-list form should pass; got {errors!r}")

    # ------------------------------------------------------------------
    # 5f: amends: ADR-NNN-AMEND-K predecessor reference
    # ------------------------------------------------------------------

    def test_amend_references_predecessor_amend_passes(self) -> None:
        """AMEND-2 that declares amends: ADR-NNN-AMEND-1 (predecessor ref)
        must resolve correctly and pass."""
        with tempfile.TemporaryDirectory() as td:
            d = self._make_corpus(
                Path(td),
                {
                    "ADR-135-base.md": "# ADR-135\n\n**Status:** ACCEPTED\n",
                    "ADR-135-AMEND-1-trust-boundary.md": (
                        "# ADR-135-AMEND-1\n\n**Status:** ACCEPTED\n\n"
                        "amends: ADR-135\n"
                    ),
                    "ADR-135-AMEND-2-activation.md": (
                        "# ADR-135-AMEND-2\n\n**Status:** ACCEPTED\n\n"
                        "amends: ADR-135-AMEND-1\n"
                    ),
                },
            )
            errors, _ = check_adr_chain.validate_chain(d)
            amend_errors = [
                e for e in errors
                if "nonexistent" in e or "chain gap" in e
            ]
            self.assertEqual(
                amend_errors,
                [],
                f"AMEND-2 referencing predecessor AMEND-1 should pass; got {errors!r}",
            )


if __name__ == "__main__":
    unittest.main()
