"""test_veto_skill_map.py — PLAN-183 W3 P0 bidirectional lint.

The derived VETO-skill map (`.claude/scripts/veto_skill_map.py`) has to be
policed in BOTH directions, because either error is silent:

  direction 1  a VETO asserted in an organogram MUST reach the set
               (under-derivation demotes a skill a VETO holder depends on)
  direction 2  every entry in the set MUST have a `path:line` anchor in an
               organogram (over-derivation, or a memory-resident entry
               someone typed in, is not governance)

Every case below is an anchor MEASURED against the shipped tree, and no
test asserts a fixed COUNT of entries — the set has to be free to grow
when a domain is installed and to shrink when one is removed. What is
pinned is the derivation's behaviour on named lines, plus the vacuity
guards that would otherwise make the whole file green by accident.

Stdlib-only. Python >= 3.9.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))
sys.path.insert(0, str(REPO_ROOT / ".claude" / "scripts"))

from _lib.testing import TestEnvContext  # noqa: E402

from veto_skill_map import (  # noqa: E402
    bind_to_inventory,
    derive_veto_skills,
    is_veto_line,
    organogram_paths,
    personas_in,
    slugs_in_row,
)

_SBG_PATH = REPO_ROOT / ".claude" / "scripts" / "skill-budget-generator.py"


def _load_generator():
    spec = importlib.util.spec_from_file_location(
        "skill_budget_generator_veto_lint", _SBG_PATH
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


SBG = _load_generator()


class _LiveTreeBase(TestEnvContext):
    """Read-only derivation against the shipped organograms.

    Nothing here writes, but `TestEnvContext` is still the base: importing
    the generator can emit audit events, and a bare `unittest.TestCase`
    would let those land in the LIVE HMAC chain (the S321 finding — 19,344
    unattributable links written by a suite with no isolation). The
    derivation itself reads REPO_ROOT explicitly, so the sandboxed
    `CLAUDE_PROJECT_DIR` does not change what is measured.
    """

    @classmethod
    def setUpClass(cls):
        cls.derived, cls.anchors = derive_veto_skills(REPO_ROOT)
        cls.inventory = SBG.load_inventory(REPO_ROOT)
        cls.bound, cls.orphans = bind_to_inventory(cls.derived, cls.inventory)


class TestVacuityGuards(_LiveTreeBase):
    """Nothing below means anything if the census is empty.

    A broken glob or a moved organogram would make every other assertion
    in this file pass by vacuity — the "guard green because it cannot see
    its target" class.
    """

    def test_organogram_census_is_non_empty_and_includes_both_roots(self):
        paths = organogram_paths(REPO_ROOT)
        self.assertTrue(paths, "no organograms discovered")
        self.assertIn(REPO_ROOT / ".claude" / "team.md", paths)
        self.assertIn(REPO_ROOT / ".claude" / "frontend-team.md", paths)

    def test_domain_organograms_are_discovered(self):
        paths = organogram_paths(REPO_ROOT)
        domain_paths = [
            p for p in paths
            if ".claude/skills/domains/" in p.as_posix()
        ]
        self.assertTrue(
            domain_paths,
            "the domains/*/team-personas.md glob found nothing — the "
            "domain half of the derivation is dark",
        )

    def test_non_canonical_organogram_is_in_the_census(self):
        """`fintech/frontend-team-personas.md` is NOT canonical while its
        sibling `team-personas.md` IS. A derivation that only trusted
        canonical organograms would lose `financial-display` — the exact
        skill the A4 field defect names."""
        self.assertIn(
            REPO_ROOT / ".claude" / "skills" / "domains" / "fintech"
            / "frontend-team-personas.md",
            organogram_paths(REPO_ROOT),
        )

    def test_derived_set_and_inventory_are_non_empty(self):
        self.assertTrue(self.inventory, "empty skill inventory")
        self.assertTrue(self.derived, "empty derivation")


class TestDirection1AssertedVetoesAreDerived(_LiveTreeBase):
    """Direction 1: a VETO in an organogram reaches the set."""

    def test_direct_cell_veto_rows_are_derived(self):
        """R1-direct — the slug is backticked ON the VETO row.
        `.claude/team.md:93,207,208,277`; `.claude/frontend-team.md:164,171`.
        """
        for slug in (
            "code-review-checklist",
            "incident-management",
            "identity-and-trust-architecture",
            "security-and-auth",
            "financial-correctness-and-math",
            "accessibility-and-wcag",
        ):
            self.assertIn(slug, self.bound, "{0} lost".format(slug))

    def test_persona_join_derives_financial_display(self):
        """R1-join — the case that does NOT close on one line.
        `fintech/frontend-team-personas.md:372` states Mei's VETO in prose
        with no slug; the Mei -> `financial-display` binding is at `:96`
        and `:359`, lines without the word VETO. Only a join by persona
        name reaches it."""
        self.assertIn("financial-display", self.bound)
        self.assertTrue(
            any("frontend-team-personas.md" in a
                for a in self.anchors["financial-display"]),
            self.anchors["financial-display"],
        )

    def test_secondary_cell_veto_is_derived(self):
        """`fintech/team-personas.md:140` binds `trading-execution` in the
        SECONDARY skill column, annotated `(VETO on P&L)`. A parser reading
        only the primary column would miss it."""
        self.assertIn("trading-execution", self.bound)

    def test_domain_organograms_contribute(self):
        """At least one entry must be anchored in a domain organogram, not
        just in the two top-level ones."""
        domain_anchored = [
            slug for slug, sites in self.anchors.items()
            if any(".claude/skills/domains/" in s for s in sites)
        ]
        self.assertTrue(domain_anchored)


class TestDirection2EveryEntryHasAnAnchor(_LiveTreeBase):
    """Direction 2: nothing enters the set without governance backing."""

    def test_every_entry_has_a_path_line_anchor(self):
        for slug in sorted(self.bound):
            self.assertTrue(
                self.anchors.get(slug),
                "{0} has no path:line anchor".format(slug),
            )

    def test_no_orphans(self):
        """An orphan is a derived slug with no match in the inventory:
        either the organogram names an uninstalled skill, or the parser
        pulled noise out of prose. Both need a human, so both are red."""
        self.assertEqual(
            self.orphans, set(),
            "organogram VETO slugs with no inventory match: "
            "{0}".format(sorted(self.orphans)),
        )

    def test_explicitly_denied_veto_is_excluded(self):
        """Negative control on the live tree. `.claude/team.md:210` and
        `:552` read "Advisory, NO VETO per ADR-052 amendment" for the LLM
        FinOps Architect, whose skill is `llm-routing-and-finops`."""
        self.assertNotIn("llm-routing-and-finops", self.bound)

    def test_toolchain_names_in_prose_are_not_derived(self):
        """Over-derivation control. `.claude/team.md:832` is a prose line
        that contains the word VETO and the backticked tokens `tsc`,
        `mypy` and `go vet`."""
        for token in ("tsc", "mypy", "vet", "go vet"):
            self.assertNotIn(token, self.derived)

    def test_implementer_on_a_veto_row_does_not_donate_their_other_skills(
        self,
    ):
        """`fintech/team-personas.md:198` reads "**Luna** + **Viktor**
        VETO": the VETO is Viktor's and Luna is the implementer. Joining
        every persona cited on a row that already names its own skills
        dragged `ai-llm-orchestration`, `public-api-design` and
        `incremental-refactoring` in from `:142`/`:200` — measured. The
        join is a FALLBACK for slug-less lines, not an addition."""
        for slug in ("ai-llm-orchestration", "public-api-design",
                     "incremental-refactoring"):
            self.assertNotIn(slug, self.bound, self.anchors.get(slug))


class TestParserUnits(TestEnvContext):
    """Unit-level behaviour of the three extraction primitives."""

    def test_negation_forms_suppress_the_line(self):
        self.assertTrue(is_veto_line("| X | VETO on merge | `a-b` |"))
        for denial in (
            "| X | Advisory, NO VETO per ADR-052 | `a-b` |",
            "| X | advisory - no-veto | `a-b` |",
            "| X | sem VETO nenhum | `a-b` |",
            "CEO may adjust owner without VETO sign-off.",
        ):
            self.assertFalse(is_veto_line(denial), denial)

    def test_line_without_veto_is_not_a_veto_line(self):
        self.assertFalse(is_veto_line("| **Mei** | `financial-display` |"))

    def test_slug_extraction_rejects_paths_files_and_multiword(self):
        row = ("| see `.claude/skills/domains/fintech/team-personas.md` "
               "and `go vet` and `core/pii-data-flow` and `real-slug` |")
        self.assertEqual(slugs_in_row(row), {"pii-data-flow", "real-slug"})

    def test_slug_extraction_ignores_non_table_lines(self):
        self.assertEqual(slugs_in_row("prose with `real-slug` inline"), set())

    def test_role_titles_and_bare_cells_are_not_join_keys(self):
        """A join key names an INDIVIDUAL. Keying on the first word of a
        multi-word title made every `**Staff ...**` / `**Principal ...**`
        row collide, and a bare `CEO` cell appears in every reporting row —
        together they pulled 29 unrelated skills into the set (measured:
        56 entries before this narrowing, 27 after)."""
        keys = personas_in("| **Staff Code Reviewer** | CEO | VETO | `x` |")
        self.assertEqual(keys, set())

    def test_single_word_name_is_a_join_key(self):
        self.assertEqual(
            personas_in("| **Viktor** | `financial-correctness-and-math` |"),
            {"Viktor"},
        )

    def test_persona_key_from_bold_span_and_from_list_lead(self):
        self.assertIn("Mei", personas_in("| **Mei** | `financial-display` |"))
        self.assertIn(
            "Mei",
            personas_in("4. **Mei tem VETO** em qualquer codigo de preco."),
        )


class TestVetoSkillsShippedAsNameOnly(_LiveTreeBase):
    """Bridge to the GPG ceremony.

    `.claude/settings.json` and `templates/settings/settings.base.json` are
    canonical: removing the offending `name-only` entries requires an
    Owner-signed sentinel, so the invariant below cannot be green in the
    same commit that introduces it. It is written affirmatively anyway,
    marked expected-failure, so the ceremony has a machine-checkable
    definition of done instead of a prose to-do.

    The companion test keeps the marker from outliving its cause: the
    moment the ceremony lands, it goes RED and names the decorator to
    delete. A debt marker that cannot expire is how the previous stale
    invariant survived.
    """

    SETTINGS_TARGETS = (
        ".claude/settings.json",
        "templates/settings/settings.base.json",
    )

    def _offenders(self, rel):
        data = json.loads((REPO_ROOT / rel).read_text(encoding="utf-8"))
        overrides = data.get("skillOverrides") or {}
        self.assertTrue(
            overrides,
            "{0} has no skillOverrides map — this test would pass by "
            "vacuity".format(rel),
        )
        # rail 183-r5: o gerador grava overrides em DUAS grafias (frontmatter
        # `name` e `dir_name`); `bound` e sempre slug. Comparar a chave CRUA
        # contra slugs deixava "Kill Switches"/"Latency Budgets" invisiveis
        # — invariante falso-verde. Normaliza via o INVENTARIO (autoridade),
        # nunca por transformacao textual.
        alias = {}
        for skill in self.inventory:
            alias[str(skill["name"])] = str(skill["dir_name"])
            alias[str(skill["dir_name"])] = str(skill["dir_name"])
        return sorted(
            k for k in overrides if alias.get(k, k) in self.bound
        )

    def test_no_veto_skill_is_shipped_name_only(self):
        # wave-183batch (rail 183-r4 P1): o decorator @expectedFailure saiu e
        # o teste-companheiro foi deletado EXATAMENTE como este arquivo
        # instruia — a cerimonia landou o undemote das 7 chaves
        # (veto-undemote-s335.jq) e o invariante e permanente.
        for rel in self.SETTINGS_TARGETS:
            offenders = self._offenders(rel)
            self.assertEqual(
                offenders, [],
                "{0} demotes VETO-bearing skills to name-only: "
                "{1}".format(rel, offenders),
            )


if __name__ == "__main__":
    unittest.main()
