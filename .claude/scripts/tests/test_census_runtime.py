#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for PLAN-186-FOLLOWUP-census-runtime W0 — ``census_runtime.py``.

The instrument under test derives the role->model table from the RUNTIME
(an import in the owner's real package context, the owner's own parsers
for the data owners, an ANCHORED detector for the shell owner) and never
from a text fingerprint. These tests prove:

* GREEN on the live tree — four surfaces, four rows, three owner classes.
* Check (a) RED in its three named forms (import fails / empty map / a
  pair on one side only).
* Check (b) RED per owner (missing key), plus alias leaking into the
  table, a fifth surface and a missing surface.
* The ``MODEL_HINT`` surface is read by EXECUTING the owner's WHOLE
  ``case`` block, verbatim, once per literal alternative, under the
  owner's own shell options, with the binding read through a
  nonce-framed channel; the anchored assignment detector survives only
  as a fail-CLOSED coverage guard over unmodelled forms.
* The data owners are reached through their PUBLIC runtime API
  (``load_routing_matrix``, ``parse_agent_file``), so a matrix the
  runtime rejects and a symlinked agent file are named REDs.
* No file under ``agents/`` is silently dropped: the output the repo
  generator declares (``_dispatch.md``) is a named, visible row.
* AC-F2 discriminant: the refuter's ``SUPPORT.md:88`` mutation (drop the
  ``[1m]`` token) moves NOTHING — the declared reading is "out of the
  runtime scope"; ``SUPPORT.md`` is normative prose, no module owns it,
  the census never reads it.
* The five findings of pair-rail round 1, each as a mutation probe.

Env-isolated via ``TestEnvContext`` (env-hygiene gate). Stdlib only.
Python >= 3.9 (no PEP 604 at runtime, no ``match``).
"""
from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

_REPO_ROOT = Path(__file__).resolve().parents[3]
_HOOKS_DIR = _REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

_CENSUS = (
    _REPO_ROOT
    / ".claude"
    / "plans"
    / "PLAN-186-FOLLOWUP-census-runtime"
    / "w0"
    / "census_runtime.py"
)

#: Everything the census reads, and nothing else. A skeleton root proves
#: the instrument's read-set is exactly this closed list.
_SKELETON = (
    ".claude/scripts/tier_policy_cli",
    ".claude/dispatcher",
    ".claude/agents",
    ".claude/hooks/_lib/frontmatter.py",
    ".claude/hooks/_lib/agent_frontmatter.py",
    ".claude/scripts/inject-agent-context.sh",
    ".claude/scripts/generate-available-models.py",
    ".claude/scripts/generate-dispatch.py",
    ".claude/scripts/build-canonical-models.py",
    ".claude/adr/ADR-149-model-id-allowlist.md",
    "SUPPORT.md",
)

_CONSTANTS_REL = ".claude/scripts/tier_policy_cli/_constants.py"
_MATRIX_REL = ".claude/dispatcher/routing-matrix.yaml"
_INJECT_REL = ".claude/scripts/inject-agent-context.sh"


def _load_census():
    spec = importlib.util.spec_from_file_location("_census_under_test", str(_CENSUS))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _make_root(dest):
    """Copy the closed read-set into a disposable root."""
    for rel in _SKELETON:
        src = _REPO_ROOT / rel
        dst = Path(dest) / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_dir():
            shutil.copytree(str(src), str(dst))
        else:
            shutil.copy2(str(src), str(dst))
    return dest


def _run(root):
    return subprocess.run(
        [sys.executable, str(_CENSUS), "--root", str(root)],
        capture_output=True,
        text=True,
        check=False,
        timeout=180,
    )


def _split_md_row(line):
    """Split a Markdown row on UNescaped pipes."""
    cells = []
    buf = []
    i = 0
    body = line.strip()
    if body.startswith("|"):
        body = body[1:]
    if body.endswith("|"):
        body = body[:-1]
    while i < len(body):
        ch = body[i]
        if ch == "\\" and i + 1 < len(body) and body[i + 1] == "|":
            buf.append("|")
            i += 2
            continue
        if ch == "|":
            cells.append("".join(buf))
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    cells.append("".join(buf))
    return cells


def _patch(root, rel, old, new, count=1):
    path = Path(root) / rel
    text = path.read_text(encoding="utf-8")
    assert text.count(old) >= count, "anchor absent in {0}: {1!r}".format(rel, old[:60])
    path.write_text(text.replace(old, new, count), encoding="utf-8")


class CensusRuntimeGreenTest(TestEnvContext):
    """The live tree must be GREEN and shaped as the AC declares."""

    def test_live_tree_green_four_rows(self):
        proc = _run(_REPO_ROOT)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        census = _load_census()
        rows = census.build_table(str(_REPO_ROOT))
        self.assertEqual(len(rows), 4)
        self.assertEqual(
            sorted(r["surface"] for r in rows), sorted(census.EXPECTED_SURFACES)
        )

    def test_three_owner_classes_and_one_label(self):
        census = _load_census()
        rows = census.build_table(str(_REPO_ROOT))
        self.assertEqual(
            sorted({r["owner_class"] for r in rows}),
            sorted({census.OWNER_DATA, census.OWNER_IMPORTABLE, census.OWNER_SHELL}),
        )
        for row in rows:
            self.assertEqual(row["label"], census.LOCAL_OWNER_LABEL)

    def test_no_alias_reaches_the_resolved_column(self):
        census = _load_census()
        rows = census.build_table(str(_REPO_ROOT))
        allowed = set(census.working_set(str(_REPO_ROOT)))
        for row in rows:
            self.assertTrue(row["resolved_model_ids"])
            for mid in row["resolved_model_ids"]:
                self.assertIn(mid, allowed, row["surface"])
            if row["raw_unit"] == census.UNIT_ALIAS:
                self.assertFalse(row["resolution_step"].startswith("nenhum"))

    def test_skeleton_root_is_the_whole_read_set(self):
        """The census reads ONLY the closed list — a skeleton root is GREEN."""
        with TemporaryDirectory() as tmp:
            proc = _run(_make_root(tmp))
            self.assertEqual(proc.returncode, 0, proc.stderr)


class CensusRuntimeCheckARedTest(TestEnvContext):
    """AC-F1 Check (a) — the three named RED forms."""

    def test_red_import_fails(self):
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            with open(os.path.join(root, _CONSTANTS_REL), "a", encoding="utf-8") as fh:
                fh.write("\nthis is not valid python(\n")
            proc = _run(root)
            self.assertEqual(proc.returncode, 1)
            self.assertIn("veto_import_failed", proc.stderr)

    def test_red_empty_map(self):
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            _patch(
                root,
                _CONSTANTS_REL,
                'VETO_HARDCODE: "Final[Dict[str, str]]" = {\n'
                '    "code-reviewer": "claude-fable-5",\n'
                '    "security-engineer": "claude-fable-5",\n'
                "}",
                'VETO_HARDCODE: "Final[Dict[str, str]]" = {}',
            )
            proc = _run(root)
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertIn("veto_map_empty", proc.stderr)

    def test_red_pair_on_one_side_only(self):
        census = _load_census()
        imported = {
            "code-reviewer": "claude-fable-5",
            "security-engineer": "claude-fable-5",
        }
        with self.assertRaises(census.Red) as ctx:
            census.check_a_compare({"code-reviewer": "claude-fable-5"}, imported)
        self.assertEqual(ctx.exception.name, "veto_pair_missing_in_table")
        with self.assertRaises(census.Red) as ctx2:
            census.check_a_compare(dict(imported, extra="claude-opus-5"), imported)
        self.assertEqual(ctx2.exception.name, "veto_pair_missing_in_import")
        with self.assertRaises(census.Red) as ctx3:
            census.check_a_compare(
                {"code-reviewer": "claude-opus-5", "security-engineer": "claude-fable-5"},
                imported,
            )
        self.assertEqual(ctx3.exception.name, "veto_pair_diverges")

    def test_check_a_two_independent_readings_agree(self):
        """Row = in-process package import; check (a) = the AC one-command."""
        census = _load_census()
        rows = census.build_table(str(_REPO_ROOT))
        census.check_a(str(_REPO_ROOT), rows)
        veto_row = [r for r in rows if r["surface"] == census.SURFACE_VETO][0]
        self.assertEqual(
            veto_row["_pairs"], census.read_veto_hardcode_one_command(str(_REPO_ROOT))
        )
        self.assertEqual(
            veto_row["_pairs"], census.read_veto_hardcode(str(_REPO_ROOT))
        )


class CensusRuntimeCheckBRedTest(TestEnvContext):
    """AC-F1 Check (b) — RED named PER OWNER, plus table-shape REDs."""

    def test_red_matrix_missing_key(self):
        """A missing key on a NON-veto archetype is the census RED."""
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            _patch(
                root,
                _MATRIX_REL,
                "  docs-writer:\n    coder: claude\n    coder_model: sonnet\n",
                "  docs-writer:\n    coder: claude\n",
            )
            proc = _run(root)
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertIn("matrix_key_missing", proc.stderr)

    def test_red_matrix_missing_key_on_a_veto_archetype_is_the_owner_red(self):
        """On a VETO-floor archetype the OWNER loader refuses first (r3 F5)."""
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            _patch(root, _MATRIX_REL, "    coder_model: opus  # ADR-052 VETO floor\n", "")
            proc = _run(root)
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertIn("matrix_rejected_by_owner_loader", proc.stderr)

    def test_red_agents_no_model_pin(self):
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            for md in (Path(root) / ".claude" / "agents").glob("*.md"):
                text = md.read_text(encoding="utf-8")
                md.write_text(
                    "\n".join(
                        ln for ln in text.split("\n") if not ln.startswith("model:")
                    ),
                    encoding="utf-8",
                )
            proc = _run(root)
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertIn("agents_no_frontmatter_model", proc.stderr)

    def test_red_model_hint_no_assignment(self):
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            path = Path(root) / _INJECT_REL
            path.write_text(
                path.read_text(encoding="utf-8").replace(
                    '    MODEL_HINT="', '    MODEL_HINT_OFF="'
                ),
                encoding="utf-8",
            )
            proc = _run(root)
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertIn("hint_no_assignment_match", proc.stderr)

    def test_red_alias_leaks_into_the_table(self):
        census = _load_census()
        rows = census.build_table(str(_REPO_ROOT))
        for row in rows:
            if row["surface"] == census.SURFACE_HINT:
                row["resolved_model_ids"] = ["opus"]
        with self.assertRaises(census.Red) as ctx:
            census.check_b(str(_REPO_ROOT), rows)
        self.assertEqual(ctx.exception.name, "alias_leaked_into_table")

    def test_red_alias_surface_without_resolution_step(self):
        census = _load_census()
        rows = census.build_table(str(_REPO_ROOT))
        for row in rows:
            if row["surface"] == census.SURFACE_MATRIX:
                row["resolution_step"] = "nenhum (valor ja e model_id)"
        with self.assertRaises(census.Red) as ctx:
            census.check_b(str(_REPO_ROOT), rows)
        self.assertEqual(ctx.exception.name, "resolution_step_absent")

    def test_red_fifth_surface(self):
        census = _load_census()
        rows = census.build_table(str(_REPO_ROOT))
        extra = dict(rows[0])
        extra["surface"] = "tier-policy.json"
        rows.append(extra)
        with self.assertRaises(census.Red) as ctx:
            census.check_b(str(_REPO_ROOT), rows)
        self.assertEqual(ctx.exception.name, "surface_unexpected")

    def test_red_missing_surface(self):
        census = _load_census()
        rows = [
            r
            for r in census.build_table(str(_REPO_ROOT))
            if r["surface"] != census.SURFACE_MATRIX
        ]
        with self.assertRaises(census.Red) as ctx:
            census.check_b(str(_REPO_ROOT), rows)
        self.assertEqual(ctx.exception.name, "surface_missing")

    def test_model_hint_line_is_published_non_exhaustive(self):
        """S348-r6 (opcao 2): a linha MODEL_HINT diz na TABELA que e
        uma observacao nao-exaustiva; as outras tres sao resposta do dono.
        """
        census = _load_census()
        rows = census.build_table(str(_REPO_ROOT))
        by = dict((r["surface"], r) for r in rows)
        self.assertEqual(
            by[census.SURFACE_HINT]["coverage"], census.COVERAGE_NONEXHAUSTIVE
        )
        for name in (census.SURFACE_VETO, census.SURFACE_MATRIX, census.SURFACE_AGENTS):
            self.assertEqual(by[name]["coverage"], census.COVERAGE_OWNER_ANSWER, name)
        table = census.render_table(rows)
        self.assertIn("cobertura", table.splitlines()[0])
        self.assertIn("NAO-EXAUSTIVA", table)
        census.check_b(str(_REPO_ROOT), rows)

    def test_red_coverage_marker_dropped(self):
        """Controle VERMELHO: MODEL_HINT que se declare resposta do dono."""
        census = _load_census()
        rows = census.build_table(str(_REPO_ROOT))
        for row in rows:
            if row["surface"] == census.SURFACE_HINT:
                row["coverage"] = census.COVERAGE_OWNER_ANSWER
        with self.assertRaises(census.Red) as ctx:
            census.check_b(str(_REPO_ROOT), rows)
        self.assertEqual(ctx.exception.name, "coverage_marker_missing")

    def test_red_coverage_marker_absent(self):
        """Controle VERMELHO: linha SEM marca de cobertura nenhuma."""
        census = _load_census()
        rows = census.build_table(str(_REPO_ROOT))
        for row in rows:
            row.pop("coverage", None)
        with self.assertRaises(census.Red) as ctx:
            census.check_b(str(_REPO_ROOT), rows)
        self.assertEqual(ctx.exception.name, "coverage_marker_missing")

    def test_red_wrong_label(self):
        census = _load_census()
        rows = census.build_table(str(_REPO_ROOT))
        rows[0]["label"] = "dona remota"
        with self.assertRaises(census.Red) as ctx:
            census.check_b(str(_REPO_ROOT), rows)
        self.assertEqual(ctx.exception.name, "label_wrong")


class ModelHintMatchersTest(TestEnvContext):
    """Duas coisas DISTINTAS, deliberadamente no mesmo lugar.

    Os quatro primeiros testes descrevem ``_ADVISORY_ASSIGN_LINE_RE``,
    um matcher ADVISORY que o censo NAO consulta: eles dizem como ele
    se comporta — inclusive onde ele NAO casa — e nada alem disso;
    nenhum resultado do censo depende deles.
    ``test_every_arm_is_bound`` roda o caminho REAL
    (``read_model_hint``), que e quem publica o vinculo e quem carrega
    a varredura por substring.
    """

    def test_heredoc_body_never_matches(self):
        census = _load_census()
        text = (_REPO_ROOT / _INJECT_REL).read_text(encoding="utf-8")
        spans = census._heredoc_spans(text)
        self.assertTrue(spans, "MODEL_HINT_HEADER heredoc not located")
        for match in census._ADVISORY_ASSIGN_LINE_RE.finditer(text):
            for lo, hi in spans:
                self.assertFalse(lo <= match.start() < hi)

    def test_interpolation_lines_do_not_match(self):
        census = _load_census()
        body = '    model="${MODEL_HINT}",\nRecommendation: **${MODEL_HINT}** for skill\n'
        self.assertEqual(census._ADVISORY_ASSIGN_LINE_RE.findall(body), [])

    def test_reason_assignment_does_not_match(self):
        census = _load_census()
        self.assertEqual(
            census._ADVISORY_ASSIGN_LINE_RE.findall(
                '    MODEL_HINT_REASON="VETO floor"\n'
            ),
            [],
        )

    def test_advisory_matcher_is_not_exhaustive(self):
        """O limite DECLARADO do matcher advisory e medido, nao afirmado.

        As duas formas abaixo contem o literal ``MODEL_HINT=`` e NAO
        casam com o matcher — e por isso que ele nao pode ser, e nao e,
        a guarda de cobertura do censo (essa e a varredura por substring
        em ``read_model_hint``, que enxerga as duas).
        """
        census = _load_census()
        compact = '  foo) MODEL_HINT="opus" ;;\n'
        inline = '  if true; then MODEL_HINT="z"; fi\n'
        for form in (compact, inline):
            self.assertEqual(census._ADVISORY_ASSIGN_LINE_RE.findall(form), [])
            self.assertIn("MODEL_HINT=", form)

    def test_every_arm_is_bound(self):
        census = _load_census()
        pairs = census.read_model_hint(str(_REPO_ROOT))
        self.assertEqual(len(pairs), 7)
        self.assertEqual(pairs[0][0], "code-review-checklist|security-and-auth")
        self.assertEqual(pairs[0][1], "opus")
        # O rotulo do curinga vem do PROPRIO instrumento (r4 P1 iii): uma
        # sonda sintetica e observacao, nao vinculo de todo o keyspace.
        self.assertEqual(pairs[-1], ("*" + census._WILDCARD_NOTE, "sonnet"))

    def test_positive_control_assignment_planted_in_heredoc_is_refused(self):
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            _patch(
                root,
                _INJECT_REL,
                "  cat <<MODEL_HINT_HEADER\n",
                '  cat <<MODEL_HINT_HEADER\nMODEL_HINT="haiku"\n',
            )
            proc = _run(root)
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertIn("hint_matched_heredoc", proc.stderr)

    def test_assignment_outside_the_case_block_is_refused(self):
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            _patch(
                root,
                _INJECT_REL,
                'case "$DETECTED_SKILL" in\n',
                'MODEL_HINT="haiku"\ncase "$DETECTED_SKILL" in\n',
            )
            proc = _run(root)
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertIn("hint_assignment_outside_case", proc.stderr)


class RailRound1ProbesTest(TestEnvContext):
    """Every finding of pair-rail round 1, re-run as a mutation probe."""

    def test_p1_changing_an_arm_alias_moves_the_table(self):
        """F1: collapsing to a set hid a real routing change."""
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            before = _run(root)
            self.assertEqual(before.returncode, 0, before.stderr)
            _patch(
                root,
                _INJECT_REL,
                '  code-review-checklist|security-and-auth)\n    MODEL_HINT="opus"',
                '  code-review-checklist|security-and-auth)\n    MODEL_HINT="sonnet"',
            )
            after = _run(root)
            self.assertEqual(after.returncode, 0, after.stderr)
            self.assertNotEqual(before.stdout, after.stdout)

    def test_p1_single_quoted_assignment_is_parsed_not_skipped(self):
        """F2a: a valid single-quoted assignment must be SEEN."""
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            before = _run(root)
            _patch(
                root,
                _INJECT_REL,
                '  code-review-checklist|security-and-auth)\n    MODEL_HINT="opus"',
                "  code-review-checklist|security-and-auth)\n    MODEL_HINT='sonnet'",
            )
            after = _run(root)
            self.assertEqual(after.returncode, 0, after.stderr)
            self.assertNotEqual(before.stdout, after.stdout)
            self.assertIn(
                "code-review-checklist\\|security-and-auth=sonnet", after.stdout
            )

    def test_p1_command_substitution_is_refused_by_name(self):
        """F2b: fail-CLOSED — a body outside the confinement is never run."""
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            _patch(
                root,
                _INJECT_REL,
                '  code-review-checklist|security-and-auth)\n    MODEL_HINT="opus"',
                "  code-review-checklist|security-and-auth)\n    MODEL_HINT=$(pick_model)",
            )
            proc = _run(root)
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertIn("hint_block_outside_confinement", proc.stderr)

    def test_p2_yaml_tag_that_the_owner_parser_rejects_is_red(self):
        """F3: the census must not change answer with the environment.

        Planted on a NON-veto archetype so the owner loader does not
        refuse for the ADR-052 VETO-floor reason first (r3 F5 made that
        rejection reachable), leaving the two parsers to disagree.
        """
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            _patch(
                root,
                _MATRIX_REL,
                "  docs-writer:\n    coder: claude\n    coder_model: sonnet\n",
                "  docs-writer:\n    coder: claude\n    coder_model: !!str sonnet\n",
            )
            proc = _run(root)
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertTrue(
                "matrix_parser_disagreement" in proc.stderr
                or "alias_unresolved" in proc.stderr,
                proc.stderr,
            )

    def test_p2_quoted_frontmatter_scalar_stays_green(self):
        """F4: quoting a pin preserves runtime behaviour — census must agree."""
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            before = _run(root)
            self.assertEqual(before.returncode, 0, before.stderr)
            _patch(
                root,
                ".claude/agents/code-reviewer.md",
                "model: claude-fable-5\n",
                'model: "claude-fable-5"\n',
            )
            after = _run(root)
            self.assertEqual(after.returncode, 0, after.stderr)
            self.assertEqual(before.stdout, after.stdout)

    def test_p2_relative_import_in_the_constants_owner_stays_green(self):
        """F5: the owner is imported in its REAL package context."""
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            _patch(
                root,
                _CONSTANTS_REL,
                "from typing import Dict\n",
                "from typing import Dict\n\nfrom ._types import MODEL_ID as _CENSUS_PROBE  # noqa: F401\n",
            )
            proc = _run(root)
            self.assertEqual(proc.returncode, 0, proc.stderr)


class RailRound2ProbesTest(TestEnvContext):
    """Every finding of pair-rail round 2, re-run as a mutation probe."""

    def test_p1_dead_control_flow_in_an_arm_is_refused(self):
        """F6: static association never proved the assignment EXECUTES."""
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            _patch(
                root,
                _INJECT_REL,
                '  code-review-checklist|security-and-auth)\n    MODEL_HINT="opus"',
                '  code-review-checklist|security-and-auth)\n'
                '    if false; then MODEL_HINT="opus"; fi',
            )
            proc = _run(root)
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertIn("hint_probe_yields_no_value", proc.stderr)

    def test_p1_renaming_an_agent_file_is_refused(self):
        """F7: the runtime resolves a role by FILENAME, not by frontmatter."""
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            adir = Path(root) / ".claude" / "agents"
            (adir / "code-reviewer.md").rename(adir / "renamed-reviewer.md")
            proc = _run(root)
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertIn("agents_name_slug_conflict", proc.stderr)

    def test_p2_agent_without_a_model_pin_is_visible(self):
        """F8: an individual malformed agent is never silently dropped."""
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            before = _run(root)
            self.assertEqual(before.returncode, 0, before.stderr)
            _patch(root, ".claude/agents/code-reviewer.md", "model: claude-fable-5\n", "")
            after = _run(root)
            self.assertEqual(after.returncode, 0, after.stderr)
            self.assertNotEqual(before.stdout, after.stdout)
            self.assertIn("code-reviewer=<sem-pin>", after.stdout)

    def test_p2_unclosed_frontmatter_is_red(self):
        """F8b: an open-but-unclosed frontmatter block is named, not skipped."""
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            md = Path(root) / ".claude" / "agents" / "code-reviewer.md"
            text = md.read_text(encoding="utf-8")
            head, _sep, tail = text.partition("\nveto_floor: true\n---\n")
            md.write_text(head + "\nveto_floor: true\n" + tail, encoding="utf-8")
            proc = _run(root)
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertIn("agents_frontmatter_unclosed", proc.stderr)

    def test_ceo_r2_generated_dispatch_is_a_visible_row(self):
        """CEO r2 (3): ``_dispatch.md`` is NAMED in the table, never skipped."""
        census = _load_census()
        proc = _run(_REPO_ROOT)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        basename = census.generated_dispatch_basename(str(_REPO_ROOT))
        slug = basename[: -len(".md")]
        self.assertIn(
            "{0}={1}".format(slug, census.AGENT_GENERATED_DISPATCH), proc.stdout
        )
        rows = census.build_table(str(_REPO_ROOT))
        agents = [r for r in rows if r["surface"] == census.SURFACE_AGENTS][0]
        for value in census.NON_PIN_VALUES:
            self.assertNotIn(value, agents["resolved_model_ids"])

    def test_ceo_r2_dispatch_basename_comes_from_the_generator(self):
        """The generated name is ASKED of the generator, never remembered."""
        census = _load_census()
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            _patch(
                root,
                ".claude/scripts/generate-dispatch.py",
                'DISPATCH_PATH = AGENTS_DIR / "_dispatch.md"',
                'DISPATCH_PATH = AGENTS_DIR / "_other_dispatch.md"',
            )
            self.assertEqual(
                census.generated_dispatch_basename(root), "_other_dispatch.md"
            )
            proc = _run(root)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertIn(
                "_dispatch={0}".format(census.AGENT_NO_FRONTMATTER), proc.stdout
            )

    def test_ceo_r2_a_new_frontmatterless_file_is_visible(self):
        """A markdown with no frontmatter moves the table (no silent skip)."""
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            before = _run(root)
            self.assertEqual(before.returncode, 0, before.stderr)
            (Path(root) / ".claude" / "agents" / "zz-note.md").write_text(
                "# just a note\n", encoding="utf-8"
            )
            after = _run(root)
            self.assertEqual(after.returncode, 0, after.stderr)
            self.assertNotEqual(before.stdout, after.stdout)
            self.assertIn("zz-note=<sem-pin: sem frontmatter>", after.stdout)

    def test_p2_markdown_cells_escape_pipes(self):
        """F9: case alternations must not blow up the six-column table."""
        proc = _run(_REPO_ROOT)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        lines = [ln for ln in proc.stdout.split("\n") if ln.startswith("|")]
        self.assertEqual(len(lines), 6)  # header + separator + four rows
        widths = {len(_split_md_row(ln)) for ln in lines}
        # 7 colunas desde a S348-r6: a coluna «cobertura» entrou com a
        # publicacao NAO-EXAUSTIVA da linha MODEL_HINT.
        self.assertEqual(widths, {7}, lines)
        self.assertIn("\\|", proc.stdout)


class RailRound3ProbesTest(TestEnvContext):
    """Every finding of pair-rail round 3, re-run as a mutation probe."""

    def test_p1_a_preceding_arm_that_matches_first_is_honored(self):
        """r3 F1: first-match semantics — a probe must run the WHOLE case."""
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            _patch(
                root,
                _INJECT_REL,
                '  code-review-checklist|security-and-auth)\n    MODEL_HINT="opus"',
                "  code-review-checklist)\n    :\n    ;;\n"
                '  code-review-checklist|security-and-auth)\n    MODEL_HINT="opus"',
            )
            proc = _run(root)
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertIn("hint_probe_yields_no_value", proc.stderr)

    def test_p1_every_alternative_of_an_arm_is_probed(self):
        """r3 F2: alternatives that bind differently are published apart."""
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            before = _run(root)
            self.assertEqual(before.returncode, 0, before.stderr)
            _patch(
                root,
                _INJECT_REL,
                '  code-review-checklist|security-and-auth)\n    MODEL_HINT="opus"',
                '  code-review-checklist|security-and-auth)\n    MODEL_HINT="opus"\n'
                '    if [ "$DETECTED_SKILL" = "security-and-auth" ]; then\n'
                '      MODEL_HINT="sonnet"\n'
                "    fi",
            )
            after = _run(root)
            self.assertEqual(after.returncode, 0, after.stderr)
            self.assertNotEqual(before.stdout, after.stdout)
            self.assertIn("[security-and-auth]=sonnet", after.stdout)
            self.assertIn("[code-review-checklist]=opus", after.stdout)

    def test_p2_arm_stdout_cannot_impersonate_the_binding(self):
        """r3 F3: the value travels in a nonce-framed channel."""
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            _patch(
                root,
                _INJECT_REL,
                '  code-review-checklist|security-and-auth)\n    MODEL_HINT="opus"',
                "  code-review-checklist|security-and-auth)\n"
                '    printf opus; MODEL_HINT=""',
            )
            proc = _run(root)
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertIn("hint_probe_yields_no_value", proc.stderr)

    def test_p2_owner_shell_options_abort_the_probe_too(self):
        """r3 F4: under the owner's `set -e` a failed command binds nothing."""
        census = _load_census()
        text = (_REPO_ROOT / _INJECT_REL).read_text(encoding="utf-8")
        self.assertEqual(census._owner_shell_options(text), "set -euo pipefail")
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            _patch(
                root,
                _INJECT_REL,
                '  code-review-checklist|security-and-auth)\n    MODEL_HINT="opus"',
                '  code-review-checklist|security-and-auth)\n    false\n    MODEL_HINT="opus"',
            )
            proc = _run(root)
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertIn("hint_probe_no_binding", proc.stderr)

    def test_p2_matrix_rejected_by_the_owner_loader_is_red(self):
        """r3 F5: a matrix the runtime REJECTS is never reported green."""
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            _patch(root, _MATRIX_REL, "reviewer_sandbox: read-only", "reviewer_sandbox: workspace-write")
            proc = _run(root)
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertIn("matrix_rejected_by_owner_loader", proc.stderr)

    def test_p2_symlinked_agent_file_is_red(self):
        """r3 F6: the owner LOADER refuses symlinks; so does the census."""
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            adir = Path(root) / ".claude" / "agents"
            real = adir / "code-reviewer.md"
            body = real.read_text(encoding="utf-8")
            (adir / "code-reviewer-real.txt").write_text(body, encoding="utf-8")
            real.unlink()
            real.symlink_to("code-reviewer-real.txt")
            proc = _run(root)
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertIn("agents_symlink_rejected", proc.stderr)


class SupportMd88DiscriminantTest(TestEnvContext):
    """AC-F2 — the declared reading is OUT OF THE RUNTIME SCOPE.

    ``SUPPORT.md`` is normative prose: no module owns it, it is none of
    the four surfaces, and the census never opens it. The refuter's
    mutation (drop ``[1m]`` from line 88) must therefore move NOTHING —
    the table stays byte-identical and rc stays 0. That is the DESIGN's
    declaration under test, not an assumption: if a future census learned
    to read prose, this test goes RED and the declaration must be rewritten.
    """

    _NEEDLE = "claude-opus-4-8[1m]"

    def test_support_md_88_still_carries_the_token(self):
        line = (_REPO_ROOT / "SUPPORT.md").read_text(encoding="utf-8").split("\n")[87]
        self.assertIn(self._NEEDLE, line, "SUPPORT.md:88 moved — re-anchor the control")

    def test_mutation_moves_nothing(self):
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            before = _run(root)
            self.assertEqual(before.returncode, 0, before.stderr)

            support = Path(root) / "SUPPORT.md"
            lines = support.read_text(encoding="utf-8").split("\n")
            self.assertIn(self._NEEDLE, lines[87])
            lines[87] = lines[87].replace(self._NEEDLE, "claude-opus-4-8")
            support.write_text("\n".join(lines), encoding="utf-8")

            after = _run(root)
            self.assertEqual(after.returncode, 0, after.stderr)
            self.assertEqual(before.stdout, after.stdout)

    def test_support_md_is_not_a_surface(self):
        census = _load_census()
        for row in census.build_table(str(_REPO_ROOT)):
            self.assertNotIn("SUPPORT", row["surface"])


class RailRound4CuresTest(TestEnvContext):
    """Every r4 finding replanted: the fail-OPEN directions are now RED.

    Each test below plants EXACTLY the mutation the pair-rail round 4
    described. Before the cure each plant left the census byte-identical
    and rc 0 (that is what made them P1); after it, the census either
    COVERS the route or REFUSES BY NAME.
    """

    _ARM = '  code-review-checklist|security-and-auth)\n    MODEL_HINT="opus"'

    def test_r4_p1_compact_one_line_arm_is_probed(self):
        """r4 P1 (i): `skill) MODEL_HINT="opus" ;;` was omitted in silence."""
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            before = _run(root)
            self.assertEqual(before.returncode, 0, before.stderr)
            self.assertNotIn("census-probe-compact", before.stdout)
            _patch(
                root,
                _INJECT_REL,
                self._ARM,
                '  census-probe-compact) MODEL_HINT="opus" ;;\n' + self._ARM,
            )
            after = _run(root)
            self.assertEqual(after.returncode, 0, after.stderr)
            self.assertIn("census-probe-compact=opus", after.stdout)
            self.assertNotEqual(before.stdout, after.stdout)

    def test_r4_p1_unmodelled_arm_form_is_refused_not_omitted(self):
        """r4 P1 (i), the general form: unmodelled grammar is RED."""
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            _patch(
                root,
                _INJECT_REL,
                self._ARM,
                '  census-probe-weird) # nota que o regex nao modela\n'
                '    MODEL_HINT="opus"\n'
                '    ;;\n' + self._ARM,
            )
            proc = _run(root)
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertIn("hint_arm_coverage_incomplete", proc.stderr)

    def test_r4_p1_quoted_pattern_is_refused_by_name(self):
        """r4 P1 (ii): a quoted literal probe would publish a WRONG value."""
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            _patch(
                root,
                _INJECT_REL,
                "  code-review-checklist|security-and-auth)",
                "  'code-review-checklist'|'security-and-auth')",
            )
            proc = _run(root)
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertIn("hint_pattern_probe_underivable", proc.stderr)

    def test_r4_p1_wildcard_row_declares_that_it_does_not_generalize(self):
        """r4 P1 (iii): one synthetic probe is an OBSERVATION, and says so."""
        proc = _run(_REPO_ROOT)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("*[sonda sintetica; nao generaliza]=sonnet", proc.stdout)
        self.assertNotIn("; *=", proc.stdout)

    def test_r4_p2_inline_comment_keeps_the_owner_options(self):
        """r4 P2 (iv): a commented `set -` line collapsed the options."""
        census = _load_census()
        text = (_REPO_ROOT / _INJECT_REL).read_text(encoding="utf-8")
        planted = text.replace(
            "set -euo pipefail", "set -euo pipefail  # strict", 1
        )
        self.assertEqual(census._owner_shell_options(planted), "set -euo pipefail")
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            _patch(
                root, _INJECT_REL, "set -euo pipefail", "set -euo pipefail  # strict"
            )
            _patch(
                root,
                _INJECT_REL,
                self._ARM,
                '  code-review-checklist|security-and-auth)\n'
                '    false\n    MODEL_HINT="opus"',
            )
            proc = _run(root)
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertIn("hint_probe_no_binding", proc.stderr)

    def test_r4_p2_uninterpretable_set_line_is_refused(self):
        """r4 P2 (iv), the general form: a declaration we cannot read is RED."""
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            _patch(
                root, _INJECT_REL, "set -euo pipefail", "set -${CENSUS_OPTS:-euo}"
            )
            proc = _run(root)
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertIn("hint_shell_options_uninterpretable", proc.stderr)

    def test_r4_p2_binding_with_surrounding_spaces_is_refused(self):
        """r4 P2 (v): the framed binding is validated EXACT, never trimmed."""
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            _patch(
                root,
                _INJECT_REL,
                self._ARM,
                '  code-review-checklist|security-and-auth)\n'
                '    MODEL_HINT=" opus "',
            )
            proc = _run(root)
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertIn("hint_probe_value_unsupported", proc.stderr)


class RailRound5CuresTest(TestEnvContext):
    """The three r5 findings, replanted. Each was rc 0 before the cure.

    The r5 class is the one the followup pre-registered as its stop rule:
    «mesma pergunta, gramatica nova» on the ONE surface without an owner
    API. The cures answer it by ARCHITECTURE, not by a longer blacklist:
    the arm census became a PARTITION (two counts could miss the same
    form; a partition cannot), and the probe derivation became a
    WHITELIST of literal alternatives (glob, quotes and parameter
    expansion are three grammars of the same fail-OPEN).
    """

    _ARM = '  code-review-checklist|security-and-auth)\n    MODEL_HINT="opus"'

    def test_r5_p1_compact_arm_with_trailing_comment_is_probed(self):
        """r5 P1: both regexes missed `pattern) body ;; # note`."""
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            before = _run(root)
            self.assertEqual(before.returncode, 0, before.stderr)
            _patch(
                root,
                _INJECT_REL,
                self._ARM,
                '  census-probe-comment) MODEL_HINT="opus" ;; # nota\n' + self._ARM,
            )
            after = _run(root)
            self.assertEqual(after.returncode, 0, after.stderr)
            self.assertIn("census-probe-comment=opus", after.stdout)

    def test_r5_p1_arm_form_outside_the_partition_is_refused(self):
        """r5 P1, general form: the span is PARTITIONED, not counted.

        `(pattern)` is legal bash and is NOT a form this census models.
        Under the old count it sat between two equal totals; under the
        partition it is a line inside the span and outside every
        recognized arm, so the census refuses to answer.
        """
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            _patch(
                root,
                _INJECT_REL,
                self._ARM,
                '  (census-probe-paren) MODEL_HINT="opus" ;;\n' + self._ARM,
            )
            proc = _run(root)
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertIn("hint_arm_coverage_incomplete", proc.stderr)

    def test_r5_p1_parameter_expansion_pattern_is_refused(self):
        """r5 P1: an expansion probed VERBATIM published the WRONG alias."""
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            _patch(
                root,
                _INJECT_REL,
                "  code-review-checklist|security-and-auth)",
                "  ${VETO_SKILL:-code-review-checklist}|security-and-auth)",
            )
            proc = _run(root)
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertIn("hint_pattern_probe_underivable", proc.stderr)

    def test_r5_p1_whitelist_accepts_only_literal_alternatives(self):
        """The rule is a WHITELIST: three grammars, one refusal."""
        census = _load_census()
        for good in ("code-review-checklist", "devops-ci-cd", "a.b_x"[:3]):
            self.assertIsNotNone(census._LITERAL_ALT_RE.match(good), good)
        for bad in (
            "sec*",
            "'quoted'",
            "${X:-y}",
            "$(cmd)",
            "with space",
            "back`tick`",
        ):
            self.assertIsNone(census._LITERAL_ALT_RE.match(bad), bad)

    def test_r5_p2_every_option_declaration_before_the_case_is_replayed(self):
        """r5 P2: only the FIRST `set -` was replayed."""
        census = _load_census()
        text = (_REPO_ROOT / _INJECT_REL).read_text(encoding="utf-8")
        planted = text.replace("set -euo pipefail", "set -u\nset -euo pipefail", 1)
        blk = planted.index('case "$DETECTED_SKILL" in')
        self.assertEqual(
            census._owner_shell_options(planted, blk),
            "set -u\nset -euo pipefail",
        )
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            _patch(root, _INJECT_REL, "set -euo pipefail", "set -u\nset -euo pipefail")
            _patch(
                root,
                _INJECT_REL,
                self._ARM,
                '  code-review-checklist|security-and-auth)\n'
                '    false\n    MODEL_HINT="opus"',
            )
            proc = _run(root)
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertIn("hint_probe_no_binding", proc.stderr)

    def test_r5_p2_options_declared_after_the_case_do_not_enter(self):
        """The block already travels verbatim: only PRECEDING options count."""
        census = _load_census()
        text = (_REPO_ROOT / _INJECT_REL).read_text(encoding="utf-8")
        blk = text.index('case "$DETECTED_SKILL" in')
        self.assertEqual(census._owner_shell_options(text, blk), "set -euo pipefail")


if __name__ == "__main__":
    unittest.main()
