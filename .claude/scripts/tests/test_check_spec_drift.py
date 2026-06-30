"""Paired tests for ``check-spec-drift.py`` (PLAN-066 Phase 2 + Round 1 C6).

Subclasses ``TestEnvContext`` from ``_lib/testing.py`` per CLAUDE.md §5
Critical Rules. Every test creates synthetic PLAN-SCHEMA / SPEC fixtures
in a tmp directory and invokes the script via subprocess (real-fs only,
no mocks — PLAN-063 round-1 invariant).

Per Round 1 C6 honest matrix: ~5 parameterized methods covering 30+
missing-invariant cases + 3 file errors + 4 adversarial classes + 1
positive baseline. Per U-DO1: explicit ``unittest.TestCase`` subclass
(via TestEnvContext) so validate.yml ``unittest discover`` picks them up.
"""
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

SCRIPT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(SCRIPT_ROOT / "hooks"))

from _lib.testing import TestEnvContext  # noqa: E402

SCRIPT = SCRIPT_ROOT / "scripts" / "check-spec-drift.py"
REPO_ROOT = SCRIPT_ROOT.parent

# Mirror of CANONICAL_INVARIANTS in the script under test. Kept here so
# tests fail loudly if the script's list drifts from this expectation.
EXPECTED_INVARIANTS = [
    ("frontmatter_required", "id"),
    ("frontmatter_required", "title"),
    ("frontmatter_required", "status"),
    ("frontmatter_required", "created"),
    ("frontmatter_required", "owner"),
    ("frontmatter_required", "depends_on"),
    ("lifecycle_state", "draft"),
    ("lifecycle_state", "reviewed"),
    ("lifecycle_state", "executing"),
    ("lifecycle_state", "done"),
    ("lifecycle_state", "abandoned"),
    ("lifecycle_state", "refused"),
    ("reopen_mechanism", "reopen_via"),
    ("reopen_mechanism", "reopen_trigger"),
    ("subdirectory_namespace", "examples"),
    ("subdirectory_namespace", "archive"),
]


def _build_complete_doc(extra: str = "") -> str:
    """Build a minimal markdown body that mentions every canonical token.

    Returns a string usable as either PLAN-SCHEMA or SPEC fixture for the
    positive baseline. The ``extra`` argument allows individual tests to
    inject adversarial content (HTML comment, fenced block, etc.).
    """
    tokens = " ".join(token for _, token in EXPECTED_INVARIANTS)
    return f"# Test fixture\n\nFrontmatter required fields: {tokens}\n\n{extra}\n"


def _run_script(plan_schema: Path, spec: Path) -> "subprocess.CompletedProcess[str]":
    """Invoke the script with explicit fixture paths."""
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--plan-schema",
            str(plan_schema),
            "--spec",
            str(spec),
        ],
        capture_output=True,
        text=True,
        timeout=10,
    )


class CanonicalInvariantsListSyncTest(TestEnvContext):
    """Detect drift between the script's invariants list and our expectation."""

    def test_invariants_list_in_sync(self) -> None:
        """If the script adds a new invariant, this test reminds the
        author to update EXPECTED_INVARIANTS above + add a fixture mention.
        """
        sys.path.insert(0, str(SCRIPT_ROOT / "scripts"))
        try:
            # Import via the `--check-spec-drift` module name (hyphenated
            # filename — load via importlib).
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "_check_spec_drift_under_test", SCRIPT
            )
            mod = importlib.util.module_from_spec(spec)
            assert spec.loader is not None
            spec.loader.exec_module(mod)
            actual = list(mod.CANONICAL_INVARIANTS)
        finally:
            try:
                sys.path.remove(str(SCRIPT_ROOT / "scripts"))
            except ValueError:
                pass
        self.assertEqual(
            actual,
            EXPECTED_INVARIANTS,
            "check-spec-drift.py CANONICAL_INVARIANTS drifted from "
            "test expectation — update EXPECTED_INVARIANTS in this test "
            "file AND ensure both PLAN-SCHEMA + SPEC mention the new "
            "token in production.",
        )


class PositiveBaselineTest(TestEnvContext):
    """Script returns 0 when both surfaces mention every invariant."""

    def test_complete_pair_passes(self) -> None:
        plan_schema = self.project_dir / "PLAN-SCHEMA.md"
        spec = self.project_dir / "plan.schema.md"
        plan_schema.write_text(_build_complete_doc(), encoding="utf-8")
        spec.write_text(_build_complete_doc(), encoding="utf-8")
        result = _run_script(plan_schema, spec)
        self.assertEqual(
            result.returncode,
            0,
            f"expected exit 0 for complete pair; got {result.returncode}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}",
        )

    def test_verbose_passes_with_summary(self) -> None:
        plan_schema = self.project_dir / "PLAN-SCHEMA.md"
        spec = self.project_dir / "plan.schema.md"
        plan_schema.write_text(_build_complete_doc(), encoding="utf-8")
        spec.write_text(_build_complete_doc(), encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--plan-schema",
                str(plan_schema),
                "--spec",
                str(spec),
                "--verbose",
            ],
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("OK: SPEC parity", result.stdout)


class MissingInvariantNegativeTest(TestEnvContext):
    """Each invariant individually missing from each surface (parameterized)."""

    def test_invariant_missing_from_plan_schema(self) -> None:
        """For each canonical invariant: removing it from PLAN-SCHEMA only."""
        for category, token in EXPECTED_INVARIANTS:
            with self.subTest(category=category, token=token, surface="PLAN-SCHEMA"):
                # Build PLAN-SCHEMA missing only this token.
                tokens_minus_one = [
                    t for _, t in EXPECTED_INVARIANTS if t != token
                ]
                plan_schema_body = (
                    "# Test fixture\n\nFields: " + " ".join(tokens_minus_one) + "\n"
                )
                plan_schema = self.project_dir / f"PS-no-{token}.md"
                spec = self.project_dir / f"SP-{token}.md"
                plan_schema.write_text(plan_schema_body, encoding="utf-8")
                spec.write_text(_build_complete_doc(), encoding="utf-8")
                result = _run_script(plan_schema, spec)
                self.assertEqual(
                    result.returncode,
                    1,
                    f"expected exit 1 for missing {token} in PLAN-SCHEMA; "
                    f"got {result.returncode}\n{result.stderr}",
                )
                self.assertIn(token, result.stderr)
                self.assertIn("PLAN-SCHEMA.md", result.stderr)

    def test_invariant_missing_from_spec(self) -> None:
        """For each canonical invariant: removing it from SPEC only."""
        for category, token in EXPECTED_INVARIANTS:
            with self.subTest(category=category, token=token, surface="SPEC"):
                tokens_minus_one = [
                    t for _, t in EXPECTED_INVARIANTS if t != token
                ]
                spec_body = (
                    "# Test fixture\n\nFields: " + " ".join(tokens_minus_one) + "\n"
                )
                plan_schema = self.project_dir / f"PS-{token}.md"
                spec = self.project_dir / f"SP-no-{token}.md"
                plan_schema.write_text(_build_complete_doc(), encoding="utf-8")
                spec.write_text(spec_body, encoding="utf-8")
                result = _run_script(plan_schema, spec)
                self.assertEqual(
                    result.returncode,
                    1,
                    f"expected exit 1 for missing {token} in SPEC; "
                    f"got {result.returncode}\n{result.stderr}",
                )
                self.assertIn(token, result.stderr)
                self.assertIn("SPEC", result.stderr)


class FileErrorTest(TestEnvContext):
    """File-missing / unreadable — propagate as Python traceback (Round 1 C5)."""

    def test_plan_schema_missing(self) -> None:
        spec = self.project_dir / "plan.schema.md"
        spec.write_text(_build_complete_doc(), encoding="utf-8")
        plan_schema = self.project_dir / "does-not-exist.md"
        result = _run_script(plan_schema, spec)
        # Non-zero exit (Python raises FileNotFoundError → returncode 1
        # from Python interpreter). Importantly, NOT a custom exit-2.
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FileNotFoundError", result.stderr)

    def test_spec_missing(self) -> None:
        plan_schema = self.project_dir / "PLAN-SCHEMA.md"
        plan_schema.write_text(_build_complete_doc(), encoding="utf-8")
        spec = self.project_dir / "does-not-exist.md"
        result = _run_script(plan_schema, spec)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FileNotFoundError", result.stderr)

    def test_both_missing(self) -> None:
        plan_schema = self.project_dir / "ps-missing.md"
        spec = self.project_dir / "sp-missing.md"
        result = _run_script(plan_schema, spec)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FileNotFoundError", result.stderr)


class AdversarialPatternsTest(TestEnvContext):
    """Round 1 C6 adversarial classes — detection vs false-positive trade-offs."""

    def test_token_only_in_html_comment_still_detected(self) -> None:
        """Word-boundary regex matches inside HTML comments — by design.
        Documentation tokens in `<!-- ... -->` count as mentioned.
        """
        plan_schema = self.project_dir / "ps.md"
        spec = self.project_dir / "sp.md"
        # PLAN-SCHEMA has all tokens; SPEC has all-but-archive in body
        # plus archive only inside HTML comment.
        plan_schema.write_text(_build_complete_doc(), encoding="utf-8")
        spec_body = "# SPEC\n\nFields: " + " ".join(
            t for _, t in EXPECTED_INVARIANTS if t != "archive"
        ) + "\n\n<!-- archive note: stub for retired plans -->\n"
        spec.write_text(spec_body, encoding="utf-8")
        result = _run_script(plan_schema, spec)
        self.assertEqual(
            result.returncode,
            0,
            "token in HTML comment counts as mention; expected exit 0",
        )

    def test_token_only_in_fenced_code_block_still_detected(self) -> None:
        """Tokens in fenced code blocks count as mentioned (intentional —
        SPEC and PLAN-SCHEMA legitimately use code blocks for examples)."""
        plan_schema = self.project_dir / "ps.md"
        spec = self.project_dir / "sp.md"
        plan_schema.write_text(_build_complete_doc(), encoding="utf-8")
        spec_body = "# SPEC\n\nFields: " + " ".join(
            t for _, t in EXPECTED_INVARIANTS if t != "examples"
        ) + "\n\n```\nlayout: examples\n```\n"
        spec.write_text(spec_body, encoding="utf-8")
        result = _run_script(plan_schema, spec)
        self.assertEqual(result.returncode, 0)

    def test_substring_does_not_falsely_pass(self) -> None:
        """Word-boundary regex must NOT match `draft` inside `draftee`.
        If only the substring form is present, drift IS detected."""
        plan_schema = self.project_dir / "ps.md"
        spec = self.project_dir / "sp.md"
        plan_schema.write_text(_build_complete_doc(), encoding="utf-8")
        # SPEC has every token EXCEPT `draft` substituted with `draftee`.
        spec_body = "# SPEC\n\nFields: " + " ".join(
            "draftee" if t == "draft" else t
            for _, t in EXPECTED_INVARIANTS
        ) + "\n"
        spec.write_text(spec_body, encoding="utf-8")
        result = _run_script(plan_schema, spec)
        self.assertEqual(
            result.returncode,
            1,
            "substring 'draftee' must not satisfy word-boundary 'draft'",
        )
        self.assertIn("draft", result.stderr)
        self.assertIn("SPEC", result.stderr)

    def test_nfkc_homoglyph_not_detected_by_design(self) -> None:
        """NFKC homoglyph (fullwidth `ｄｒａｆｔ`) is NOT detected — the
        ASCII word-boundary regex deliberately does not normalize.
        This documents a known limitation: SPEC + PLAN-SCHEMA are
        internal repo docs, not adversarial input from external sources;
        normalization adds parser complexity for a low-realistic threat.
        """
        plan_schema = self.project_dir / "ps.md"
        spec = self.project_dir / "sp.md"
        plan_schema.write_text(_build_complete_doc(), encoding="utf-8")
        # SPEC replaces `draft` with fullwidth homoglyph.
        spec_body = "# SPEC\n\nFields: " + " ".join(
            "ｄｒａｆｔ" if t == "draft" else t
            for _, t in EXPECTED_INVARIANTS
        ) + "\n"
        spec.write_text(spec_body, encoding="utf-8")
        result = _run_script(plan_schema, spec)
        # Drift IS detected because ASCII regex doesn't match fullwidth.
        # If this test starts failing, the script gained NFKC support —
        # update the documentation accordingly.
        self.assertEqual(result.returncode, 1)
        self.assertIn("draft", result.stderr)


class LiveRepoTest(TestEnvContext):
    """Sanity check against the actual repo state.

    PRE Phase 3 (current): expects exit 1 (examples + archive missing in SPEC).
    POST Phase 3 (after ceremony): expects exit 0.

    This test asserts the exit code matches whichever state is current,
    derived from the live SPEC content. It documents the live repo as
    additional integration coverage beyond the synthetic fixtures.
    """

    def test_live_repo_drift_state_consistent(self) -> None:
        result = subprocess.run(
            [sys.executable, str(SCRIPT)],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(REPO_ROOT),
        )
        spec_body = (REPO_ROOT / "SPEC" / "v1" / "plan.schema.md").read_text(
            encoding="utf-8"
        )
        import re
        examples_present = bool(re.search(r"\bexamples\b", spec_body))
        archive_present = bool(re.search(r"\barchive\b", spec_body))
        if examples_present and archive_present:
            # Phase 3 ceremony has landed.
            self.assertEqual(
                result.returncode,
                0,
                f"SPEC has examples+archive; expected exit 0, got "
                f"{result.returncode}\n{result.stderr}",
            )
        else:
            # Phase 3 ceremony not yet landed (PRE state).
            self.assertEqual(
                result.returncode,
                1,
                f"SPEC missing examples/archive (PRE-Phase-3); expected "
                f"exit 1, got {result.returncode}\n{result.stderr}",
            )


if __name__ == "__main__":
    unittest.main()
