"""PLAN-178 C1 / ADR-191 — FILE ASSIGNMENT grammar gate tests.

Covers the four classifier states (absent / concrete / readonly /
unparseable), the advisory-first emit (path_count=0 on omission — the
R-SEC1 cure), the measure-first enforce flag
(CEO_SPAWN_FILE_ASSIGNMENT_REQUIRED=1), and the TESTED recovery route
(CEO_SOTA_DISABLE=1 forces advisory — ADR-186 pattern).

These are the FIRST tests for the E3 Rail-3 surface (the rails shipped
in PLAN-133 without a dedicated test file); the positive controls here
are required by the Lote B runbook before the enforce flag may ever be
flipped (AC-2b gate).
"""

from __future__ import annotations

import re
from typing import List
from unittest import mock

from _lib.testing import TestEnvContext  # noqa: E402

import check_agent_spawn as cas  # noqa: E402


def _compile_names(*names):
    escaped = [re.escape(n) for n in names]
    return re.compile(r"\b(?:" + "|".join(escaped) + r")\b", re.IGNORECASE)


NAMES = _compile_names("Sofia")

# Skill body must clear the >=256 non-whitespace-bytes floor (P1-SEC-B).
_SKILL_BODY = "security-and-auth rule " * 20

_PROMPT_HEAD = (
    "## AGENT PROFILE\nPersona: Sofia Nakamura\n\n"
    "## SKILL CONTENT\n" + _SKILL_BODY + "\n\n"
)
_PROMPT_TAIL = "\n## TASK\nReview the auth middleware config loading.\n"


def _prompt(fa_block: str = "") -> str:
    return _PROMPT_HEAD + fa_block + _PROMPT_TAIL


class _AuditEmitSpy:
    """Captures emit_generic calls for assertion."""

    def __init__(self):
        self.calls: List[dict] = []

    def emit_generic(self, action, **fields):
        self.calls.append({"action": action, **fields})


class _FaBase(TestEnvContext):
    """Shared decide() driver with the audit-emit spy installed."""

    def _decide(self, prompt: str, env: dict):
        self.spy = _AuditEmitSpy()
        with mock.patch.object(cas, "_audit_emit", self.spy), \
                mock.patch.object(cas, "_AUDIT_EMIT_AVAILABLE", True):
            return cas.decide(
                description="Sofia: review auth middleware",
                prompt=prompt,
                names_regex=NAMES,
                env=env,
            )

    def _recorded(self):
        return [
            c for c in self.spy.calls
            if c["action"] == "spawn_file_assignment_recorded"
        ]


class TestClassifier(TestEnvContext):
    """Pure-function contract of _classify_file_assignment."""

    def test_absent(self):
        state, paths = cas._classify_file_assignment("no block here")
        self.assertEqual(state, "absent")
        self.assertEqual(paths, frozenset())

    def test_concrete(self):
        state, paths = cas._classify_file_assignment(
            "## FILE ASSIGNMENT\n- CAN edit: src/a.py, src/b.py\n"
        )
        self.assertEqual(state, "concrete")
        self.assertEqual(paths, frozenset({"src/a.py", "src/b.py"}))

    def test_readonly_explicit(self):
        state, paths = cas._classify_file_assignment(
            "## FILE ASSIGNMENT\n- CAN edit: NONE-READ-ONLY\n"
        )
        self.assertEqual(state, "readonly")
        self.assertEqual(paths, frozenset())

    def test_readonly_token_case_insensitive(self):
        state, _ = cas._classify_file_assignment(
            "## FILE ASSIGNMENT\n- CAN edit: none-read-only\n"
        )
        self.assertEqual(state, "readonly")

    def test_readonly_token_never_a_concrete_path(self):
        """The token must be unreachable as an overlap participant."""
        paths = cas._parse_file_assignment(
            "## FILE ASSIGNMENT\n- CAN edit: NONE-READ-ONLY\n"
        )
        self.assertEqual(paths, frozenset())

    def test_wildcard_only_is_unparseable(self):
        state, paths = cas._classify_file_assignment(
            "## FILE ASSIGNMENT\n- CAN edit: src/**, {file list}\n"
        )
        self.assertEqual(state, "unparseable")
        self.assertEqual(paths, frozenset())

    def test_empty_block_is_unparseable(self):
        state, _ = cas._classify_file_assignment(
            "## FILE ASSIGNMENT\nsome prose, no CAN edit line\n## NEXT\n"
        )
        self.assertEqual(state, "unparseable")

    def test_angle_bracket_placeholder_is_unparseable(self):
        """Codex r1 P2: the scaffold literal `<concrete paths>` (shown in
        the hook's own block message) must never classify concrete."""
        state, paths = cas._classify_file_assignment(
            "## FILE ASSIGNMENT\n- CAN edit: <concrete paths>\n"
        )
        self.assertEqual(state, "unparseable")
        self.assertEqual(paths, frozenset())

    def test_empty_normalized_path_is_unparseable(self):
        """Codex r3 P1: `...` and `./` normalize to "" — an empty path
        must never make the declaration concrete."""
        for val in ("...", "./", "., ./."):
            state, paths = cas._classify_file_assignment(
                "## FILE ASSIGNMENT\n- CAN edit: %s\n" % val
            )
            self.assertEqual(state, "unparseable", val)
            self.assertEqual(paths, frozenset(), val)

    def test_prose_line_with_write_synonym_suffix_taints(self):
        """Codex r41: MUST write/create no sufixo da prosa macula."""
        for suffix in ("MUST write hidden.py", "should create x.py",
                       "allowed to delete y.py"):
            state, _ = cas._classify_file_assignment(
                "## FILE ASSIGNMENT\n- CAN edit: safe.py\n"
                "- MAY read docs; %s\n" % suffix
            )
            self.assertEqual(state, "unparseable", suffix)

    def test_denied_path_with_authority_substring_passes(self):
        """Codex r42: `- CANNOT edit: src/write.py` é path negado
        legítimo — 'write' dentro de token-path não é autoridade."""
        state, paths = cas._classify_file_assignment(
            "## FILE ASSIGNMENT\n- CAN edit: safe.py\n"
            "- CANNOT edit: src/write.py, delete_old.py\n"
        )
        self.assertEqual((state, paths), ("concrete", frozenset({"safe.py"})))

    def test_canonical_prose_lines_still_pass(self):
        """As linhas prosa CANÔNICAS dos templates seguem válidas."""
        state, paths = cas._classify_file_assignment(
            "## FILE ASSIGNMENT\n"
            "- CAN edit: a.py\n"
            "- CANNOT edit: anything not listed above\n"
            "- CANNOT edit: files another agent is editing\n"
        )
        self.assertEqual((state, paths), ("concrete", frozenset({"a.py"})))

    def test_prose_line_with_any_edit_suffix_taints(self):
        """Codex r34: MUST edit escondido após prefixo prosa macula."""
        state, _ = cas._classify_file_assignment(
            "## FILE ASSIGNMENT\n- CAN edit: safe.py\n"
            "- MAY read docs; MUST edit hidden.py\n"
        )
        self.assertEqual(state, "unparseable")

    def test_prose_line_with_grant_suffix_taints(self):
        """Codex r33: forma prosa não contrabandeia grant no sufixo."""
        state, _ = cas._classify_file_assignment(
            "## FILE ASSIGNMENT\n"
            "- If you need permission: CAN edit: hidden.py\n"
        )
        self.assertEqual(state, "unparseable")

    def test_code_indented_can_edit_is_example_text(self):
        """Codex r33: 4+ espaços = code block CommonMark — exemplo, não
        grant; bloco sem grant real fica unparseable."""
        state, paths = cas._classify_file_assignment(
            "## FILE ASSIGNMENT\n    - CAN edit: fake.py\n"
        )
        self.assertEqual(state, "unparseable")
        self.assertEqual(paths, frozenset())

    def test_indented_task_heading_bounds_block(self):
        """Codex r33: `## TASK` indentado 1-3 fecha o bloco — bullets da
        task não vazam para o parser de assignment."""
        state, paths = cas._classify_file_assignment(
            "## FILE ASSIGNMENT\n- CAN edit: real.py\n"
            " ## TASK\n- do something unrelated\n"
        )
        self.assertEqual((state, paths), ("concrete", frozenset({"real.py"})))

    def test_header_case_and_indent_variants_recognized(self):
        """Codex r32: `## File Assignment` e header indentado 1-3 espaços
        são o MESMO heading para o agente — reconhecidos, não ignorados."""
        state, paths = cas._classify_file_assignment(
            "## File Assignment\n- CAN edit: x.py\n"
        )
        self.assertEqual((state, paths), ("concrete", frozenset({"x.py"})))
        state, paths = cas._classify_file_assignment(
            "  ## FILE ASSIGNMENT\n- CAN edit: y.py\n"
        )
        self.assertEqual((state, paths), ("concrete", frozenset({"y.py"})))

    def test_unrecognized_list_line_taints_structurally(self):
        """Regra estrutural (r25→r32): QUALQUER linha de lista não-
        reconhecida no bloco macula — MAY edit com +, numerada, prosa."""
        for line in ("+ MAY edit: hidden.py", "1. MAY edit: hidden.py",
                     "* worktree mode; merge after"):
            state, _ = cas._classify_file_assignment(
                "## FILE ASSIGNMENT\n- CAN edit: safe.py\n%s\n" % line
            )
            self.assertEqual(state, "unparseable", line)

    def test_unicode_whitespace_taints(self):
        """Codex r32: U+00A0 renderiza como espaço — 'all\u00a0files'
        nunca vira path concreto."""
        state, _ = cas._classify_file_assignment(
            "## FILE ASSIGNMENT\n- CAN edit: all\u00a0files\n"
        )
        self.assertEqual(state, "unparseable")

    def test_plus_bullet_is_parsed(self):
        """Codex r31: bullet `+` é CommonMark válido — PARSEADO (autoridade
        visível ao overlap), nunca invisível."""
        state, paths = cas._classify_file_assignment(
            "## FILE ASSIGNMENT\n+ CAN edit: plus.py\n"
        )
        self.assertEqual(state, "concrete")
        self.assertEqual(paths, frozenset({"plus.py"}))

    def test_numbered_grant_taints(self):
        state, _ = cas._classify_file_assignment(
            "## FILE ASSIGNMENT\n- CAN edit: safe.py\n1. CAN edit: hidden.py\n"
        )
        self.assertEqual(state, "unparseable")

    def test_broad_prose_and_expansion_taint(self):
        for val in ("all files", "any path", "$HOME/.ssh/config"):
            state, _ = cas._classify_file_assignment(
                "## FILE ASSIGNMENT\n- CAN edit: %s\n" % val
            )
            self.assertEqual(state, "unparseable", val)

    def test_over_cap_taints(self):
        paths_line = ", ".join("f%03d.py" % i for i in range(70))
        state, paths = cas._classify_file_assignment(
            "## FILE ASSIGNMENT\n- CAN edit: %s\n" % paths_line
        )
        self.assertEqual(state, "unparseable")
        self.assertEqual(len(paths), 64)

    def test_legacy_positive_grant_in_mixed_block_taints(self):
        """Codex r25 P2: `- MAY edit: src/**` ao lado de um CAN edit
        válido macula o bloco (grant positivo que o parser não valida)."""
        state, _ = cas._classify_file_assignment(
            "## FILE ASSIGNMENT\n"
            "- CAN edit: safe.py\n"
            "- MAY edit: src/other.py\n"
        )
        self.assertEqual(state, "unparseable")

    def test_template_prose_does_not_taint(self):
        """A prosa canônica do template (If you need to edit... /
        CANNOT edit) NÃO macula — regra fechada por verbo de grant."""
        state, paths = cas._classify_file_assignment(
            "## FILE ASSIGNMENT\n"
            "- CAN edit: safe.py\n"
            "- CANNOT edit: files another agent is editing\n"
            "- If you need to edit a forbidden file: STOP and report.\n"
        )
        self.assertEqual(state, "concrete")
        self.assertEqual(paths, frozenset({"safe.py"}))

    def test_appended_block_without_can_edit_line_taints(self):
        """Codex r23 P1: a generator read-only block followed by an
        appended block with ZERO parseable CAN-edit lines (MAY edit /
        misspelled) must taint the declaration — the agent reads a write
        grant the parser never saw."""
        state, paths = cas._classify_file_assignment(
            "## FILE ASSIGNMENT\n- CAN edit: NONE-READ-ONLY\n\n"
            "## TASK\nx\n\n"
            "## FILE ASSIGNMENT\n- MAY edit: src/a.py\n"
        )
        self.assertEqual(state, "unparseable")
        self.assertEqual(paths, frozenset())

    def test_mixed_concrete_plus_wildcard_is_unparseable(self):
        """Codex r15 P1: `safe.py, src/**` must NOT classify concrete —
        any dropped token taints the whole declaration (the agent still
        read the wildcard grant). Concrete paths still returned for
        overlap telemetry."""
        state, paths = cas._classify_file_assignment(
            "## FILE ASSIGNMENT\n- CAN edit: safe.py, src/**\n"
        )
        self.assertEqual(state, "unparseable")
        self.assertEqual(paths, frozenset({"safe.py"}))

    def test_readonly_plus_invalid_token_is_unparseable(self):
        """Codex r14 P1: an earlier NONE-READ-ONLY must not launder a
        later wildcard grant past the enforce gate — any dropped token
        taints the whole declaration."""
        state, paths = cas._classify_file_assignment(
            "## FILE ASSIGNMENT\n"
            "- CAN edit: NONE-READ-ONLY\n\n"
            "## TASK\nx\n\n"
            "## FILE ASSIGNMENT\n- CAN edit: src/**\n"
        )
        self.assertEqual(state, "unparseable")
        self.assertEqual(paths, frozenset())

    def test_unicode_line_separators_never_concrete(self):
        """Codex r28 P1: U+0085/U+2028/U+2029 injetam ESTRUTURA de prompt
        e nunca podem classificar como path concreto."""
        for sep in ("\u0085", "\u2028", "\u2029"):
            state, paths = cas._classify_file_assignment(
                "## FILE ASSIGNMENT\n- CAN edit: safe%s.py\n" % sep
            )
            self.assertEqual(state, "unparseable", repr(sep))
            self.assertEqual(paths, frozenset(), repr(sep))

    def test_nul_control_chars_never_concrete(self):
        """Codex r9 P2: a crafted NUL-bearing value must not classify
        concrete — filesystem paths cannot carry NUL, and the NUL-framed
        telemetry marker relies on that unreachability."""
        state, paths = cas._classify_file_assignment(
            "## FILE ASSIGNMENT\n- CAN edit: \x00fa-readonly-marker\x00\n"
        )
        self.assertEqual(state, "unparseable")
        self.assertEqual(paths, frozenset())

    def test_bare_none_stays_a_dropped_placeholder(self):
        """`none` is NOT the read-only form — that ambiguity is the cell
        ADR-191 cures. It classifies as unparseable, never readonly."""
        state, _ = cas._classify_file_assignment(
            "## FILE ASSIGNMENT\n- CAN edit: none\n"
        )
        self.assertEqual(state, "unparseable")

    def test_concrete_wins_over_readonly_token(self):
        state, paths = cas._classify_file_assignment(
            "## FILE ASSIGNMENT\n- CAN edit: NONE-READ-ONLY, src/a.py\n"
        )
        self.assertEqual(state, "concrete")
        self.assertEqual(paths, frozenset({"src/a.py"}))

    def test_generator_readonly_plus_caller_concrete_aggregates(self):
        """Codex r2 P1 positive control: the canonical generator emits an
        unconditional read-only block and /spawn-style callers APPEND a
        concrete block — the writer's paths must WIN and be visible to
        overlap telemetry (first-block-only parsing hid them)."""
        prompt = (
            "## FILE ASSIGNMENT\n- CAN edit: NONE-READ-ONLY\n\n"
            "## TASK\nintermediate section\n\n"
            "## FILE ASSIGNMENT\n- CAN edit: src/writer.py\n"
        )
        state, paths = cas._classify_file_assignment(prompt)
        self.assertEqual(state, "concrete")
        self.assertEqual(paths, frozenset({"src/writer.py"}))

    def test_two_concrete_blocks_union(self):
        prompt = (
            "## FILE ASSIGNMENT\n- CAN edit: a.py\n\n"
            "## FILE ASSIGNMENT\n- CAN edit: b.py\n"
        )
        state, paths = cas._classify_file_assignment(prompt)
        self.assertEqual(state, "concrete")
        self.assertEqual(paths, frozenset({"a.py", "b.py"}))

    def test_indented_fence_masked(self):
        """Codex r29 P1: fence CommonMark indentado 1-3 espaços também é
        mascarado — um exemplo assim nunca satisfaz o gate."""
        state, _ = cas._classify_file_assignment(
            "  ```\n  ## FILE ASSIGNMENT\n  - CAN edit: src/a.py\n  ```\n"
        )
        self.assertEqual(state, "absent")

    def test_length_and_type_mismatched_fences_stay_masked(self):
        """Codex r35: opener de 4 backticks "fechado" por 3, e ``` fechado
        por ~~~, continuam FENCED — o conteúdo nunca vira grant."""
        state, _ = cas._classify_file_assignment(
            "````\n## FILE ASSIGNMENT\n- CAN edit: fake.py\n```\nprose\n"
        )
        self.assertEqual(state, "absent")
        state, _ = cas._classify_file_assignment(
            "```\n## FILE ASSIGNMENT\n- CAN edit: fake2.py\n~~~\nprose\n"
        )
        self.assertEqual(state, "absent")

    def test_unclosed_html_comment_masked_to_eof(self):
        """Codex r39: <!-- sem --> se estende até EOF — conteúdo
        comentado nunca satisfaz o gate."""
        state, _ = cas._classify_file_assignment(
            "<!--\n## FILE ASSIGNMENT\n- CAN edit: fake.py\n"
        )
        self.assertEqual(state, "absent")

    def test_mixed_char_fence_close_stays_masked(self):
        """Codex r37: ``` "fechado" por ```~~~ (chars mistos) continua
        aberto em CommonMark — mascara até EOF (fail-closed)."""
        state, _ = cas._classify_file_assignment(
            "```\n```~~~\n## FILE ASSIGNMENT\n- CAN edit: fake.py\n"
        )
        self.assertEqual(state, "absent")

    def test_indented_fence_longer_close_and_unclosed(self):
        """Codex r30 P1: closing fence mais longo e fence não-fechado até
        EOF também são mascarados."""
        state, _ = cas._classify_file_assignment(
            "  ```\n  ## FILE ASSIGNMENT\n  - CAN edit: a.py\n  `````\n"
        )
        self.assertEqual(state, "absent")
        state, _ = cas._classify_file_assignment(
            " ```\n ## FILE ASSIGNMENT\n - CAN edit: b.py\n"
        )
        self.assertEqual(state, "absent")

    def test_fenced_block_masked(self):
        """A FILE ASSIGNMENT inside a code fence must not count."""
        state, _ = cas._classify_file_assignment(
            "```\n## FILE ASSIGNMENT\n- CAN edit: src/a.py\n```\n"
        )
        self.assertEqual(state, "absent")


class TestAdvisoryDefault(_FaBase):
    """Flag unset — grammar never blocks; omission becomes VISIBLE."""

    def test_absent_allows_and_emits_path_count_zero(self):
        d = self._decide(_prompt(), env={})
        self.assertTrue(d.allow)
        recs = self._recorded()
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["path_count"], 0)
        self.assertEqual(recs[0]["path_hashes"], "")

    def test_readonly_emits_marker_hash_with_path_count_zero(self):
        d = self._decide(
            _prompt("## FILE ASSIGNMENT\n- CAN edit: NONE-READ-ONLY\n"),
            env={},
        )
        self.assertTrue(d.allow)
        recs = self._recorded()
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["path_count"], 0)
        # Domain-separated marker (codex r1 P2): NUL-framed input is
        # unreachable from real declared-path space.
        self.assertEqual(
            recs[0]["path_hashes"],
            cas._path_hash("\x00fa-readonly-marker\x00"),
        )

    def test_marker_hash_never_collides_with_real_path(self):
        """Codex r1 P2 positive control: a legitimate concrete path
        `./none-read-only` must NOT hash to the telemetry marker — under
        CEO_SPAWN_OVERLAP_GUARD=1 that collision would false-block."""
        d = self._decide(
            _prompt("## FILE ASSIGNMENT\n- CAN edit: ./none-read-only\n"),
            env={},
        )
        self.assertTrue(d.allow)
        recs = self._recorded()
        self.assertEqual(len(recs), 1)
        # It parses as a CONCRETE path (token check runs pre-normalization
        # by design) and its hash differs from the readonly marker hash.
        self.assertEqual(recs[0]["path_count"], 1)
        self.assertNotEqual(
            recs[0]["path_hashes"],
            cas._path_hash("\x00fa-readonly-marker\x00"),
        )

    def test_concrete_emit_unchanged(self):
        d = self._decide(
            _prompt("## FILE ASSIGNMENT\n- CAN edit: src/a.py\n"),
            env={},
        )
        self.assertTrue(d.allow)
        recs = self._recorded()
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["path_count"], 1)
        self.assertEqual(recs[0]["path_hashes"], cas._path_hash("src/a.py"))


class TestEnforceFlag(_FaBase):
    """CEO_SPAWN_FILE_ASSIGNMENT_REQUIRED=1 — fail-closed grammar."""

    ENV = {"CEO_SPAWN_FILE_ASSIGNMENT_REQUIRED": "1"}

    def test_absent_blocks(self):
        """POSITIVE CONTROL: the flag actually blocks (AC-2b gate)."""
        d = self._decide(_prompt(), env=dict(self.ENV))
        self.assertFalse(d.allow)
        self.assertIn("spawn_file_assignment_missing", d.reason)
        self.assertIn("NONE-READ-ONLY", d.reason)  # fix hint present

    def test_wildcard_only_blocks_as_unparseable(self):
        d = self._decide(
            _prompt("## FILE ASSIGNMENT\n- CAN edit: src/**\n"),
            env=dict(self.ENV),
        )
        self.assertFalse(d.allow)
        self.assertIn("spawn_file_assignment_unparseable", d.reason)

    def test_bare_none_blocks_as_unparseable(self):
        d = self._decide(
            _prompt("## FILE ASSIGNMENT\n- CAN edit: none\n"),
            env=dict(self.ENV),
        )
        self.assertFalse(d.allow)
        self.assertIn("spawn_file_assignment_unparseable", d.reason)

    def test_mixed_taint_blocks_under_enforce(self):
        """Codex r15 P1 rail-level positive control: the MIXED declaration
        must BLOCK under enforce (branching on `mine` instead of state
        would route it through the allow-path)."""
        d = self._decide(
            _prompt("## FILE ASSIGNMENT\n- CAN edit: safe.py, src/**\n"),
            env=dict(self.ENV),
        )
        self.assertFalse(d.allow)
        self.assertIn("spawn_file_assignment_unparseable", d.reason)

    def test_readonly_explicit_passes(self):
        d = self._decide(
            _prompt("## FILE ASSIGNMENT\n- CAN edit: NONE-READ-ONLY\n"),
            env=dict(self.ENV),
        )
        self.assertTrue(d.allow)

    def test_concrete_passes(self):
        d = self._decide(
            _prompt("## FILE ASSIGNMENT\n- CAN edit: src/a.py\n"),
            env=dict(self.ENV),
        )
        self.assertTrue(d.allow)

    def test_generic_spawn_untouched_by_enforce(self):
        """Non-named spawns never enter the grammar gate."""
        self.spy = _AuditEmitSpy()
        with mock.patch.object(cas, "_audit_emit", self.spy), \
                mock.patch.object(cas, "_AUDIT_EMIT_AVAILABLE", True):
            d = cas.decide(
                description="Summarize the README",
                prompt="Read README.md and summarize it",
                names_regex=NAMES,
                env=dict(self.ENV),
            )
        self.assertTrue(d.allow)
        self.assertEqual(self._recorded(), [])


class TestRecoveryRoute(_FaBase):
    """CEO_SOTA_DISABLE=1 forces advisory — the named recovery route."""

    def test_sota_disable_unlocks_enforced_absent(self):
        d = self._decide(
            _prompt(),
            env={
                "CEO_SPAWN_FILE_ASSIGNMENT_REQUIRED": "1",
                "CEO_SOTA_DISABLE": "1",
            },
        )
        self.assertTrue(d.allow)
        # Advisory telemetry still flows under the recovery route.
        recs = self._recorded()
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["path_count"], 0)


class TestFailOpenAndClassification(_FaBase):
    """Infra fail-open + audit reason_code mapping for the new codes."""

    def test_broken_emit_never_blocks(self):
        broken = mock.MagicMock()
        broken.emit_generic.side_effect = RuntimeError("boom")
        with mock.patch.object(cas, "_audit_emit", broken), \
                mock.patch.object(cas, "_AUDIT_EMIT_AVAILABLE", True):
            d = cas.decide(
                description="Sofia: review auth middleware",
                prompt=_prompt(),
                names_regex=NAMES,
                env={},
            )
        self.assertTrue(d.allow)

    def test_block_reason_classification(self):
        self.assertEqual(
            cas._classify_block_reason(
                "GOVERNANCE: spawn_file_assignment_missing: fa_state=absent."
            ),
            "spawn_file_assignment_missing",
        )
        self.assertEqual(
            cas._classify_block_reason(
                "GOVERNANCE: spawn_file_assignment_unparseable: "
                "fa_state=unparseable."
            ),
            "spawn_file_assignment_unparseable",
        )
