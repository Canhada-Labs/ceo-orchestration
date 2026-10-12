#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests for PLAN-186-FOLLOWUP-census-runtime W0 + W1a — ``census_runtime.py``.

The instrument under test derives the role->model table from the RUNTIME
(an import in the owner's real package context, the owner's own parsers
for the data owners, an ANCHORED detector for the shell owner) and never
from a text fingerprint. These tests prove:

* GREEN on the live tree — one row per DECLARED surface (four W0 + three
  W1a), three owner classes, the label each family carries in the note.
* W1a (Owner decision 2026-10-12, the three lowest-risk reopened owners):
  ``task-route.py`` asked through ``_agents_for`` over a domain HARVESTED
  from the owner, with a fail-closed LINE-coverage guard; the ADR-052
  baseline asked through the tier-policy LOADER and cross-checked against
  the builder in a separate process; the delivered template read by the
  owner's own loader. One RED control (at least) per owner, each a
  mutation of a disposable COPY; the devops divergence is published.
* The census never writes the audit chain: the test env points HOME and
  ``CEO_AUDIT_LOG_PATH`` at the TestEnvContext tree and the tree is
  byte-for-byte unchanged after the run.
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
* AC-F2 discriminant: the refuter's ``SUPPORT.md`` mutation (drop the
  ``[1m]`` token from the model row that carries it — line 88 at the time
  of the refutation, located by CONTENT since the v1.4.0 re-read moved it)
  moves NOTHING — the declared reading is "out of the runtime scope";
  ``SUPPORT.md`` is normative prose, no module owns it, the census never
  reads it.
* The five findings of pair-rail round 1, each as a mutation probe.

Env-isolated via ``TestEnvContext`` (env-hygiene gate). Stdlib only.
Python >= 3.9 (no PEP 604 at runtime, no ``match``).
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock

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
    # W1a — task-route.py and the ``_lib`` modules its import pulls in.
    ".claude/scripts/task-route.py",
    ".claude/hooks/_lib/__init__.py",
    ".claude/hooks/_lib/injection_salt.py",
    ".claude/hooks/_lib/runtime_paths.py",
    ".claude/hooks/_lib/secret_patterns.py",
    ".claude/hooks/_lib/tier_policy",
    # W1a — the template ``install.sh`` delivers to every adopter.
    "templates/.claude/tier-policy.json",
)

_CONSTANTS_REL = ".claude/scripts/tier_policy_cli/_constants.py"
_MATRIX_REL = ".claude/dispatcher/routing-matrix.yaml"
_INJECT_REL = ".claude/scripts/inject-agent-context.sh"
_TASK_ROUTE_REL = ".claude/scripts/task-route.py"
_TIER_LOADER_REL = ".claude/scripts/tier_policy_cli/loader.py"
_TIER_TYPES_REL = ".claude/scripts/tier_policy_cli/_types.py"
_TIER_TEMPLATE_REL = "templates/.claude/tier-policy.json"


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
            # Other pytest workers can atomically replace bytecode while this
            # fixture is copied. Only source/configuration belongs in the census.
            shutil.copytree(
                str(src), str(dst),
                ignore=shutil.ignore_patterns("__pycache__", "*.py[co]", "*.py[co].*"),
            )
        else:
            shutil.copy2(str(src), str(dst))
    return dest



class SkeletonCopyIsolationTest(TestEnvContext):
    """Fixture snapshots contain sources, never interpreter-owned caches."""

    def test_disappearing_bytecode_does_not_break_source_snapshot(self):
        with TemporaryDirectory() as scratch:
            source = Path(scratch) / "source"
            package = source / "package"
            cache = package / "__pycache__"
            cache.mkdir(parents=True)
            (package / "module.py").write_text("VALUE = 7\n")
            (package / "settings.yaml").write_text("enabled: true\n")
            (cache / "module.cpython-312.pyc.12345").write_bytes(b"temporary")
            (package / "legacy.pyc").write_bytes(b"compiled")
            (package / "legacy.pyo").write_bytes(b"optimized")
            (package / "legacy.pyc.12345").write_bytes(b"temporary")
            destination = Path(scratch) / "snapshot"
            copyfile = shutil.copyfile

            def copying_while_bytecode_is_renamed(src, dst, **kwargs):
                path = Path(src)
                if "__pycache__" in path.parts or ".pyc" in path.name:
                    path.unlink()
                return copyfile(src, dst, **kwargs)

            with mock.patch.dict(globals(), {"_REPO_ROOT": source, "_SKELETON": ("package",)}):
                with mock.patch.object(shutil, "copyfile", side_effect=copying_while_bytecode_is_renamed):
                    _make_root(destination)
            copied = destination / "package"
            self.assertEqual({p.name for p in copied.iterdir()}, {"module.py", "settings.yaml"})
            self.assertEqual((copied / "module.py").read_text(), "VALUE = 7\n")
            self.assertEqual((copied / "settings.yaml").read_text(), "enabled: true\n")

    def test_source_copy_errors_still_fail_the_snapshot(self):
        with TemporaryDirectory() as scratch:
            source = Path(scratch) / "source"
            (source / "package").mkdir(parents=True)
            (source / "package" / "module.py").write_text("VALUE = 7\n")
            with mock.patch.dict(globals(), {"_REPO_ROOT": source, "_SKELETON": ("package",)}):
                with mock.patch.object(shutil, "copyfile", side_effect=PermissionError("source unreadable")):
                    with self.assertRaises(shutil.Error):
                        _make_root(Path(scratch) / "snapshot")


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

    def test_live_tree_green_one_row_per_declared_surface(self):
        proc = _run(_REPO_ROOT)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stderr, "")
        census = _load_census()
        rows = census.build_table(str(_REPO_ROOT))
        self.assertEqual(len(census.W0_SURFACES), 4)
        self.assertEqual(len(census.W1A_SURFACES), 3)
        self.assertEqual(len(rows), len(census.EXPECTED_SURFACES))
        self.assertEqual(
            [r["surface"] for r in rows], list(census.EXPECTED_SURFACES)
        )

    def test_three_owner_classes_and_the_label_of_each_family(self):
        census = _load_census()
        rows = census.build_table(str(_REPO_ROOT))
        self.assertEqual(
            sorted({r["owner_class"] for r in rows}),
            sorted({census.OWNER_DATA, census.OWNER_IMPORTABLE, census.OWNER_SHELL}),
        )
        for row in rows:
            expected = (
                census.LOCAL_OWNER_LABEL
                if row["surface"] in census.W0_SURFACES
                else census.REOPENED_OWNER_LABEL
            )
            self.assertEqual(row["label"], expected, row["surface"])

    def test_no_alias_reaches_the_resolved_column(self):
        census = _load_census()
        rows = census.build_table(str(_REPO_ROOT))
        fleet = set(census.working_set(str(_REPO_ROOT)))
        for row in rows:
            self.assertTrue(row["resolved_model_ids"])
            owner_domain = row.get("_model_id_domain")
            allowed = set(owner_domain) if owner_domain is not None else fleet
            for mid in row["resolved_model_ids"]:
                self.assertIn(mid, allowed, row["surface"])
                if mid not in fleet:
                    # Outside the ADR-149 working set (the DATED haiku of the
                    # tier-policy owners): PUBLISHED, never normalized away.
                    self.assertIn(mid, row["resolution_step"], row["surface"])
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
        census = _load_census()
        lines = [ln for ln in proc.stdout.split("\n") if ln.startswith("|")]
        # header + separator + one row per declared surface (4 W0 + 3 W1a)
        self.assertEqual(len(lines), 2 + len(census.EXPECTED_SURFACES))
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


class SupportMdDiscriminantTest(TestEnvContext):
    """AC-F2 — the declared reading is OUT OF THE RUNTIME SCOPE.

    ``SUPPORT.md`` is normative prose: no module owns it, it is none of
    the four surfaces, and the census never opens it. The refuter's
    mutation (drop ``[1m]`` from the model row that carries it — line 88
    at the time of the refutation; located by CONTENT since the v1.4.0
    re-read of ``SUPPORT.md`` moved the row and renamed the model) must
    therefore move NOTHING — the table stays byte-identical and rc stays
    0. That is the DESIGN's declaration under test, not an assumption: if
    a future census learned to read prose, this test goes RED and the
    declaration must be rewritten.
    """

    _NEEDLE = "claude-opus-5[1m]"

    @classmethod
    def _needle_hits(cls, text):
        return [i for i, line in enumerate(text.split("\n")) if cls._NEEDLE in line]

    def test_support_md_still_carries_the_token(self):
        hits = self._needle_hits((_REPO_ROOT / "SUPPORT.md").read_text(encoding="utf-8"))
        self.assertEqual(
            len(hits), 1,
            "SUPPORT.md must carry the `[1m]` control token on exactly one line "
            "— re-anchor the control (_NEEDLE) to the row that carries it",
        )

    def test_mutation_moves_nothing(self):
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            before = _run(root)
            self.assertEqual(before.returncode, 0, before.stderr)

            support = Path(root) / "SUPPORT.md"
            text = support.read_text(encoding="utf-8")
            hits = self._needle_hits(text)
            self.assertEqual(len(hits), 1, "control token missing or duplicated in the copied SUPPORT.md")
            lines = text.split("\n")
            lines[hits[0]] = lines[hits[0]].replace(self._NEEDLE, "claude-opus-5")
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


#: The tail of ``_agents_for`` — anchor for planting a branch before it.
_TR_TAIL = "    return agents\n\n\ndef _context_strategy("


class W1aTaskRouteTest(TestEnvContext):
    """Owner 2 — ``task-route.py``, asked through ``_agents_for``."""

    def test_row_equals_an_independent_enumeration_of_the_owner(self):
        """The harvested domain loses no route the owner can return.

        The oracle here is INDEPENDENT of the census harvest: the owner's
        own ``CLASSIFICATION_MODES`` x every value ``_detect_workflow_signal``
        documents x truthy/falsy veto domain x both booleans.
        """
        census = _load_census()
        module = census._import_task_route(str(_REPO_ROOT))
        expected = set()
        for cls in module.CLASSIFICATION_MODES:
            for veto in (None, "auth"):
                for wf in (None, "release", "ci", "rag", "test-infra"):
                    for schema in (False, True):
                        for agent in module._agents_for(cls, veto, wf, schema):
                            expected.add((agent["role"], agent["model"]))
        reading = census.read_task_route(str(_REPO_ROOT))
        got = set((r, m) for r, ms in reading["routes"].items() for m in ms)
        self.assertTrue(expected)
        self.assertEqual(expected, got)
        # The harvest found every classification the owner's enum declares.
        for cls in module.CLASSIFICATION_MODES:
            self.assertIn(cls, reading["domain"]["classification"])

    def test_check_a_two_readings_agree(self):
        """Row (harvest + trace, in process) == the ONE command (no harvest)."""
        census = _load_census()
        rows = census.build_table(str(_REPO_ROOT))
        row = [r for r in rows if r["surface"] == census.SURFACE_TASK_ROUTE][0]
        second = census.read_task_route_one_command(str(_REPO_ROOT), row["_raw_domain"])
        self.assertEqual(row["_pairs"], second)
        self.assertEqual(row["coverage"], census.COVERAGE_PROBED)
        census.check_a(str(_REPO_ROOT), rows)

    def test_red_check_a_row_that_drops_a_route(self):
        """RED: a row that lost a (role, model) pair disagrees with the import."""
        census = _load_census()
        rows = census.build_table(str(_REPO_ROOT))
        for row in rows:
            if row["surface"] == census.SURFACE_TASK_ROUTE:
                row["_pairs"].pop(sorted(row["_pairs"])[0])
        with self.assertRaises(census.Red) as ctx:
            census.check_a(str(_REPO_ROOT), rows)
        self.assertEqual(ctx.exception.name, "task_route_pair_missing_in_table")

    def test_green_control_a_new_literal_branch_is_derived_not_remembered(self):
        """A route behind a NEW literal shows up with no census change."""
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            before = _run(root)
            self.assertEqual(before.returncode, 0, before.stderr)
            _patch(
                root,
                _TASK_ROUTE_REL,
                _TR_TAIL,
                '    if workflow_change == "census-deploy":\n'
                '        agents.append({"role": "devops", "model": "claude-haiku-4-5"})\n'
                + _TR_TAIL,
            )
            after = _run(root)
            self.assertEqual(after.returncode, 0, after.stderr)
            self.assertNotEqual(before.stdout, after.stdout)
            self.assertIn("devops=claude-haiku-4-5[em ", after.stdout)
            self.assertIn("devops=claude-opus-4-8[em ", after.stdout)

    def test_red_control_branch_the_probe_cannot_reach_is_refused(self):
        """RED: a route behind ``startswith`` would vanish — it is refused."""
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            _patch(
                root,
                _TASK_ROUTE_REL,
                _TR_TAIL,
                '    if workflow_change is not None and workflow_change.startswith("dep"):\n'
                '        agents.append({"role": "devops", "model": "claude-haiku-4-5"})\n'
                + _TR_TAIL,
            )
            proc = _run(root)
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertIn("task_route_branch_unreached", proc.stderr)

    def test_red_control_owner_sys_exit_on_import_is_a_named_red(self):
        """RED: the owner calls ``sys.exit(2)`` when an import fails."""
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            _patch(
                root,
                _TASK_ROUTE_REL,
                "    from _lib.agent_frontmatter import VETO_FLOOR_ROLES\n",
                "    from _lib.agent_frontmatter import VETO_FLOOR_ROLES\n"
                "    from _lib.census_absent_module import NOTHING  # noqa: F401\n",
            )
            proc = _run(root)
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertIn("task_route_import_failed", proc.stderr)
            self.assertNotIn("Traceback", proc.stderr)

    def test_red_control_alias_in_the_owner_is_refused(self):
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            _patch(
                root,
                _TASK_ROUTE_REL,
                '"model": "claude-sonnet-4-6",',
                '"model": "sonnet",',
            )
            proc = _run(root)
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertIn("alias_leaked_into_table", proc.stderr)

    def test_errata_r6_the_veto_homonym_is_not_a_model_surface(self):
        """By IMPORT: what task-route reads as VETO_HARDCODE maps to task types."""
        census = _load_census()
        homonym = census.task_route_veto_homonym(str(_REPO_ROOT))
        self.assertTrue(homonym)
        fleet = set(census.working_set(str(_REPO_ROOT)))
        for role, value in homonym.items():
            self.assertIsInstance(value, frozenset, role)
            self.assertFalse(set(value) & fleet, role)

    def test_red_coverage_claim_stronger_than_the_probe(self):
        census = _load_census()
        rows = census.build_table(str(_REPO_ROOT))
        for row in rows:
            if row["surface"] == census.SURFACE_TASK_ROUTE:
                row["coverage"] = census.COVERAGE_OWNER_ANSWER
        with self.assertRaises(census.Red) as ctx:
            census.check_b(str(_REPO_ROOT), rows)
        self.assertEqual(ctx.exception.name, "coverage_marker_missing")

    def test_red_reopened_owner_labelled_as_a_w0_surface(self):
        census = _load_census()
        rows = census.build_table(str(_REPO_ROOT))
        for row in rows:
            if row["surface"] == census.SURFACE_TIER_TEMPLATE:
                row["label"] = census.LOCAL_OWNER_LABEL
        with self.assertRaises(census.Red) as ctx:
            census.check_b(str(_REPO_ROOT), rows)
        self.assertEqual(ctx.exception.name, "label_wrong")

    def test_compare_pairs_names_the_owner(self):
        census = _load_census()
        with self.assertRaises(census.Red) as ctx:
            census.compare_pairs({}, {"devops->x": "1"}, "task_route")
        self.assertEqual(ctx.exception.name, "task_route_pair_missing_in_table")
        with self.assertRaises(census.Red) as ctx2:
            census.compare_pairs({"devops->x": "2"}, {"devops->x": "1"}, "tier_baseline")
        self.assertEqual(ctx2.exception.name, "tier_baseline_pair_diverges")


class W1aTierPolicyTest(TestEnvContext):
    """Owners 4 and 5 — the ADR-052 baseline and the delivered template."""

    def test_baseline_row_is_the_loader_fallback_and_matches_the_builder(self):
        census = _load_census()
        pairs, domain = census.read_tier_baseline(str(_REPO_ROOT))
        self.assertEqual(pairs, census.read_tier_baseline_one_command(str(_REPO_ROOT)))
        self.assertIn(pairs["devops"], domain)

    def test_red_control_loader_fallback_diverging_from_the_builder(self):
        """RED: the loader stops falling back to ``build_adr052_baseline``."""
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            _patch(
                root,
                _TIER_LOADER_REL,
                "_FROZEN_BASELINE = build_adr052_baseline()\n",
                "_FROZEN_BASELINE = dict(build_adr052_baseline(), devops=Assignment("
                'tier="claude-sonnet-4-6", locked_by=None, evidence=None))\n',
            )
            proc = _run(root)
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertIn("tier_baseline_pair_diverges", proc.stderr)

    def test_red_control_alias_in_the_baseline_is_refused(self):
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            _patch(
                root,
                _TIER_TYPES_REL,
                'tier="claude-haiku-4-5-20251001",',
                'tier="haiku",',
            )
            proc = _run(root)
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertIn("alias_leaked_into_table", proc.stderr)

    def test_template_row_is_what_the_owner_loader_returns(self):
        """Oracle independent of the loader: plain ``json`` over the file."""
        census = _load_census()
        pairs, _domain, status = census.read_tier_template(str(_REPO_ROOT))
        self.assertEqual(status, "ok")
        raw = json.loads((_REPO_ROOT / _TIER_TEMPLATE_REL).read_text(encoding="utf-8"))
        self.assertEqual(
            pairs, dict((k, v["tier"]) for k, v in raw["assignments"].items())
        )

    def test_red_control_template_the_owner_loader_rejects(self):
        """RED: the adopter would fall back — the census says so by name."""
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            _patch(
                root,
                _TIER_TEMPLATE_REL,
                '"tier": "claude-haiku-4-5-20251001"',
                '"tier": "haiku"',
            )
            proc = _run(root)
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertIn("tier_template_rejected_by_owner_loader", proc.stderr)
            self.assertIn("invalid_model_id", proc.stderr)

    def test_green_control_a_template_change_moves_the_table(self):
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            before = _run(root)
            self.assertEqual(before.returncode, 0, before.stderr)
            _patch(
                root,
                _TIER_TEMPLATE_REL,
                '"tier": "claude-haiku-4-5-20251001"',
                '"tier": "claude-sonnet-4-6"',
            )
            after = _run(root)
            self.assertEqual(after.returncode, 0, after.stderr)
            self.assertNotEqual(before.stdout, after.stdout)
            self.assertIn(
                "templates/.claude/tier-policy.json=claude-sonnet-4-6", after.stdout
            )

    def test_devops_divergence_is_published_not_reconciled(self):
        census = _load_census()
        rows = census.build_table(str(_REPO_ROOT))
        found = dict(census.role_divergences(rows))
        self.assertIn("devops", found)
        devops = dict(found["devops"])
        self.assertEqual(devops[census.SURFACE_AGENTS], ["claude-sonnet-4-6"])
        self.assertEqual(
            devops[census.SURFACE_TIER_BASELINE], ["claude-haiku-4-5-20251001"]
        )
        # A role every role-keyed surface agrees on is NOT a divergence.
        self.assertNotIn("qa-architect", found)
        # Alias / skill-keyed surfaces never enter the comparison.
        for entries in found.values():
            surfaces = set(s for s, _m in entries)
            self.assertNotIn(census.SURFACE_HINT, surfaces)
            self.assertNotIn(census.SURFACE_MATRIX, surfaces)
        proc = _run(_REPO_ROOT)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        line = [ln for ln in proc.stdout.split("\n") if ln.startswith("- devops:")]
        self.assertEqual(len(line), 1, proc.stdout)
        self.assertIn("agents/*.md=claude-sonnet-4-6", line[0])
        self.assertIn(
            census.SURFACE_TIER_BASELINE + "=claude-haiku-4-5-20251001", line[0]
        )


class W1aAuditIsolationTest(TestEnvContext):
    """The census and the W1a readers write NOTHING to the audit chain."""

    @staticmethod
    def _snapshot(base):
        out = {}
        for dirpath, dirnames, filenames in os.walk(str(base)):
            for name in dirnames:
                out[os.path.relpath(os.path.join(dirpath, name), str(base))] = "dir"
            for name in filenames:
                path = os.path.join(dirpath, name)
                st = os.stat(path)
                out[os.path.relpath(path, str(base))] = (st.st_size, st.st_mtime_ns)
        return out

    def test_census_never_writes_the_audit_chain(self):
        tmp_root = os.path.realpath(str(self._tmp_root))
        log_path = os.environ["CEO_AUDIT_LOG_PATH"]
        self.assertTrue(os.path.realpath(log_path).startswith(tmp_root), log_path)
        self.assertTrue(os.path.realpath(os.environ["HOME"]).startswith(tmp_root))
        # The resolver every emitter uses lands under the ISOLATED home.
        resolved = subprocess.run(
            [
                sys.executable,
                str(_REPO_ROOT / ".claude" / "hooks" / "_lib" / "runtime_paths.py"),
                "--state-dir",
                "--project",
                str(_REPO_ROOT),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=60,
        )
        self.assertEqual(resolved.returncode, 0, resolved.stderr)
        self.assertTrue(
            os.path.realpath(resolved.stdout.strip()).startswith(tmp_root),
            resolved.stdout,
        )
        watched = self.home_dir / ".claude"
        before = self._snapshot(watched)
        census = _load_census()
        census.read_task_route(str(_REPO_ROOT))
        census.read_tier_baseline(str(_REPO_ROOT))
        census.read_tier_template(str(_REPO_ROOT))
        proc = _run(_REPO_ROOT)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(before, self._snapshot(watched))
        self.assertFalse(os.path.exists(log_path))
        # Positive control: the snapshot DOES see a write to the audit path.
        Path(log_path).write_text("probe\n", encoding="utf-8")
        self.assertNotEqual(before, self._snapshot(watched))


#: The devops guard + route head inside ``_agents_for`` (anchor for the
#: same-line hash-lookup plants of the W1a correction round).
_TR_DEVOPS_HEAD = (
    '    if workflow_change == "release" or workflow_change == "ci":\n'
    "        agents.append({\n"
    '            "archetype": "DevOps & Platform Engineer",\n'
    '            "role": "devops",\n'
    '            "skill": "devops-ci-cd",\n'
    '            "model": "claude-opus-4-8",\n'
)
_TR_DEVOPS_DICT_GET = (
    '    _devops_model = {"release": "claude-opus-4-8", "ci": "claude-opus-4-8"}\n'
    "    if workflow_change is not None:\n"
    "        agents.append({\n"
    '            "archetype": "DevOps & Platform Engineer",\n'
    '            "role": "devops",\n'
    '            "skill": "devops-ci-cd",\n'
    '            "model": _devops_model.get(workflow_change, "claude-sonnet-4-6"),\n'
)
_TR_DEVOPS_SET_IFEXP = (
    "    if workflow_change is not None:\n"
    "        agents.append({\n"
    '            "archetype": "DevOps & Platform Engineer",\n'
    '            "role": "devops",\n'
    '            "skill": "devops-ci-cd",\n'
    '            "model": "claude-opus-4-8" if workflow_change in {"release", "ci"}'
    ' else "claude-sonnet-4-6",\n'
)

#: One function per form. ``ok_*`` use only the forms the probe harvests;
#: every ``bad_*`` is a form it does not, and must be refused BY FORM.
_FORM_TABLE_SRC = '''
from typing import Optional

TABLE = {"a": 1}
SENTINEL = object()


def ok_harvested(p: str, q: Optional[str], b: bool):
    if p == "a" or q != "b" or "c" == p:
        return 1
    if p in ("a", "b") and q not in ["c"]:
        return 2
    if q is None or q is not None:
        return 3
    if q and not q:
        return 4
    x = 5 if q else 6
    return [b, x, [1 for _ in range(1) if q]]


def bad_method(p: str):
    return p.startswith("a")


def bad_dict_get(p: str):
    return {"a": 1}.get(p, 0)


def bad_subscript(p: str):
    return TABLE[p]


def bad_in_set(p: str):
    return 1 if p in {"a", "b"} else 2


def bad_in_name(p: str):
    return 1 if p in TABLE else 2


def bad_substring(p: str):
    return "a" in p


def bad_is_other(p: str):
    return p is SENTINEL


def bad_truth_on_str(p: str):
    return 1 if p else 2


def bad_value_through_or(q: Optional[str]):
    x = q or "default"
    return x


def bad_rebind(p: str):
    p = "x"
    return p


def bad_call_argument(p: str):
    return len(p)


def bad_fstring(p: str):
    return f"{p}"


def bad_chained(p: str):
    return "a" == p == "b"


def bad_reflection(p: str):
    return locals()
'''


class W1aFormGuardTest(TestEnvContext):
    """Refuter P2 (correction round): a same-line hash lookup is refused."""

    def test_red_control_dict_get_on_the_route_line_is_refused(self):
        """The refuter's repro: the route vanished at rc 0 before the cure."""
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            _patch(root, _TASK_ROUTE_REL, _TR_DEVOPS_HEAD, _TR_DEVOPS_DICT_GET)
            census = _load_census()
            owner = census._import_task_route(str(root))
            # Independent oracle: the mutated owner STILL routes devops to
            # Opus for release/ci — the route the census must not lose.
            for wf in ("release", "ci"):
                got = [(a["role"], a["model"]) for a in owner._agents_for("M", None, wf, False)]
                self.assertIn(("devops", "claude-opus-4-8"), got)
            proc = _run(root)
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertIn("task_route_form_unprobeable", proc.stderr)
            self.assertNotIn("Traceback", proc.stderr)

    def test_red_control_set_membership_in_a_conditional_on_the_route_line(self):
        with TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            _patch(root, _TASK_ROUTE_REL, _TR_DEVOPS_HEAD, _TR_DEVOPS_SET_IFEXP)
            proc = _run(root)
            self.assertEqual(proc.returncode, 1, proc.stdout)
            self.assertIn("task_route_form_unprobeable", proc.stderr)

    def test_form_table_accepts_only_harvested_forms(self):
        census = _load_census()
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "census_form_table.py"
            path.write_text(_FORM_TABLE_SRC, encoding="utf-8")
            saved = sys.dont_write_bytecode
            sys.dont_write_bytecode = True
            try:
                spec = importlib.util.spec_from_file_location("_census_form_table", str(path))
                table = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(table)
            finally:
                sys.dont_write_bytecode = saved
            census._assert_probe_forms(table.ok_harvested)
            refused = sorted(n for n in vars(table) if n.startswith("bad_"))
            self.assertEqual(len(refused), 14)
            for name in refused:
                with self.assertRaises(census.Red, msg=name) as ctx:
                    census._assert_probe_forms(getattr(table, name))
                self.assertEqual(ctx.exception.name, "task_route_form_unprobeable", name)

    def test_red_control_duplicate_def_is_refused(self):
        census = _load_census()
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "census_dup_def.py"
            path.write_text(
                "def f(p: str):\n    return p == 'a'\n\n\ndef f(p: str):\n    return p == 'b'\n",
                encoding="utf-8",
            )
            saved = sys.dont_write_bytecode
            sys.dont_write_bytecode = True
            try:
                spec = importlib.util.spec_from_file_location("_census_dup_def", str(path))
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
            finally:
                sys.dont_write_bytecode = saved
            with self.assertRaises(census.Red) as ctx:
                census._assert_probe_forms(mod.f)
            self.assertEqual(ctx.exception.name, "task_route_form_unprobeable")


if __name__ == "__main__":
    unittest.main()
