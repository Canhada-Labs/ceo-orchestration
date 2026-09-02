#!/usr/bin/env python3
"""apply-179fu-flip.py — a DERIVACAO do patch da wave `179-followup-flip` (PLAN-179-FOLLOWUP, S338).

Este script E o material versionado da cerimonia: aplica TODAS as edicoes da
wave sobre uma arvore em HEAD (base dc72bf1 — nenhum dos hooks e tocado pelo
pack fable51, entao a base e o HEAD puro), com ancora EXATA por edicao e
contagem declarada. Ancora ausente, ambigua ou arvore ja patchada e RECUSA
nomeada, arvore intocada — nunca "best effort". O LAND prova que
`HEAD + este script == patch` BYTE A BYTE em cada path (molde
apply-fable51-edits.py / 183batch).

O que a wave faz (AC item 1 do PLAN-179-FOLLOWUP + emenda S337 + rail r1):
  * Os QUATRO produtores LEGADOS de ciclo de vida passam a resolver o id
    PAYLOAD-first (payload > CLAUDE_SESSION_ID > timestamp), no MESMO patch:
      - `SessionStart.py::main`      -> `session_start`   (AC item 1)
      - `SessionEnd.py::main`        -> `session_end`     (emenda S337: o
        consumidor US8 segmenta a janela pelo `session_end` lido pelo id do
        PAYLOAD em `_session_start_ts`; flipar so o start deixaria essa perna
        cega quando env != payload)
      - `UserPromptSubmit.py::main`  -> `prompt_submitted` (rail r1 P1 desta
      - `Stop.py::main`              -> `session_stop`     wave: um flip
        PARCIAL fragmenta o ciclo de vida de UMA sessao em dois ids para
        leitores que particionam por session_id, ex. ceo-escalation-detector;
        censo mecanico: a classe tem exatamente estes 4 membros)
    O `payload_sid` do rail novo fica INTOCADO (sem fallback, unico id que o
    delta aceita). Fallbacks env e timestamp PRESERVADOS.
  * `tests/test_session_end_memory_delta.py` — (a) testes de unidade: com env
    divergente, o evento GRAVADO na cadeia carrega o id do PAYLOAD, para as 4
    actions; fallbacks env e timestamp sobre os 4; trava ESTRUTURAL (AST) da
    precedencia nos 4 `main()` — INVERTE em-lugar o lock env-first da r12
    P2-b da wave-179close; (b) integracao produtor->consumidor: o
    `session_start` gravado payload-first E ancorado pelo consumidor
    payload-gated (`anchor_source=chain`) e o `session_end` gravado
    payload-first segmenta a janela do resume. A trava do consumidor
    (`test_divergent_env_id_never_anchors`) NAO e relaxada — so o docstring
    deixa de apontar para um futuro que virou passado.

Uso:
    python3 apply-179fu-flip.py --root <arvore-em-HEAD>
    python3 apply-179fu-flip.py --root <arvore> --check-only   (so ancoras)
    python3 apply-179fu-flip.py --list-paths                   (paths tocados)

Saidas: 0 = aplicado (ou, com --check-only, aplicavel); 1 = recusa nomeada;
2 = erro de uso. Stdlib-only, Python >= 3.9, sem PEP 604 em runtime.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Tuple

# Marcador de dupla aplicacao: aparece em TODO path tocado DEPOIS do patch e
# em NENHUM deles em HEAD (o teste em HEAD cita "PLAN-179-FOLLOWUP material",
# sem o "(S338)"; os hooks nao citam o followup).
MARKER = "PLAN-179-FOLLOWUP (S338)"

START_REL = ".claude/hooks/SessionStart.py"
END_REL = ".claude/hooks/SessionEnd.py"
PROMPT_REL = ".claude/hooks/UserPromptSubmit.py"
STOP_REL = ".claude/hooks/Stop.py"
TEST_REL = ".claude/hooks/tests/test_session_end_memory_delta.py"

# Comentario compartilhado pelos 3 produtores de forma identica (SessionStart,
# UserPromptSubmit, Stop); o SessionEnd reescreve o comentario r12 P2-b.
_QUARTET_COMMENT = (
    '    # PLAN-179-FOLLOWUP (S338): PAYLOAD-first — payload > env > timestamp.\n'
    '    # The SPEC threads the id "from the harness event" and CLAUDE_SESSION_ID\n'
    '    # is agent-spoofable; the US8 consumer (SessionEnd._session_start_ts)\n'
    '    # and every session-partitioning reader match rows by the PAYLOAD id, so\n'
    '    # an env-first producer stranded every divergent session in\n'
    '    # start_unknown (rail r6 P2-b of wave-179close) and split one lifecycle\n'
    '    # across two ids. The FOUR lifecycle producers (SessionStart /\n'
    '    # UserPromptSubmit / Stop / SessionEnd) flip in the SAME patch (S337 P2\n'
    '    # sweep + pair-rail r1 of this wave). Env stays the fallback for a\n'
    '    # payload without an id; the timestamp fallback is unchanged.\n'
)

# --------------------------------------------------------------------------
# Blocos de teste novos (texto-fonte; raw para preservar as barras).
# --------------------------------------------------------------------------
_TEST_HELPERS = r'''def _run_hook_main(module, payload, env):
    """Drive a lifecycle hook's ``main()`` exactly the way the harness does —
    the JSON event on stdin, ids in the environment — and return its rc.
    ``env`` maps var -> value; ``None`` means ABSENT for the call (popped
    inside the ``mock.patch.dict`` scope, restored with it). The adapter
    resolves ``sys.stdin`` at CALL time by design (adapters/claude.py), so
    the swap is the sanctioned test seam — the r12 P2-b claim that
    ``main()`` was "not honestly constructible here" is refuted by this
    helper (PLAN-179-FOLLOWUP (S338))."""
    present = {k: v for k, v in env.items() if v is not None}
    absent = [k for k, v in env.items() if v is None]
    with mock.patch.dict(os.environ, present, clear=False):
        for key in absent:
            os.environ.pop(key, None)
        with mock.patch.object(sys, "stdin", io.StringIO(json.dumps(payload))), \
                mock.patch.object(sys, "stdout", io.StringIO()):
            return module.main()


def _session_id_operands(func):
    """Ordered ``or``-operands of the FIRST ``session_id = a or b ...``
    assignment in ``func`` — the producer's precedence chain — as source
    strings (nested ``or`` groups flattened, so parentheses cannot hide an
    operand). Structural, not positional: a comment or a reflowed line
    cannot fake the order the way ``str.index`` could be fooled."""
    tree = ast.parse(inspect.getsource(func))
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "session_id"
            and isinstance(node.value, ast.BoolOp)
        ):
            flat: list = []

            def _flatten(value):
                if isinstance(value, ast.BoolOp) and isinstance(value.op, ast.Or):
                    for item in value.values:
                        _flatten(item)
                else:
                    flat.append(ast.unparse(value))

            _flatten(node.value)
            return flat
    raise AssertionError(
        "no `session_id = a or b ...` assignment in %s" % func.__qualname__
    )


'''

_CHAIN_ROWS_METHOD = r'''
    def _chain_rows(self, action: str) -> list:
        """Rows of ``action`` on the isolated chain, in file order — read
        from the SAME path the producer wrote and the consumer reads
        (``_anchor_log_path``), parsed leniently (a non-JSON line is skipped,
        never a test error: the assertion is about the rows that ARE there).
        PLAN-179-FOLLOWUP (S338)."""
        log_path = self._anchor_log_path()
        if not log_path.is_file():
            return []
        rows = []
        for line in log_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if isinstance(ev, dict) and ev.get("action") == action:
                rows.append(ev)
        return rows
'''

_STRUCTURAL_LOCK = r'''    def test_lifecycle_id_is_payload_first_in_all_four_producers(self) -> None:
        """PLAN-179-FOLLOWUP (S338) — INVERTS the rail r12 P2-b lock of the
        wave-179close (`test_lifecycle_id_mirrors_sessionstart_env_first`):
        the FOUR legacy lifecycle producers — `session_start`
        (SessionStart.py::main), `prompt_submitted` (UserPromptSubmit.py::main),
        `session_stop` (Stop.py::main) and `session_end` (SessionEnd.py::main)
        — resolve the id PAYLOAD-first: payload > CLAUDE_SESSION_ID >
        timestamp, the precedence the new rail's `payload_sid` already had.
        Rationale: the SPEC threads the id "from the harness event", env is
        agent-spoofable, the US8 consumer matches start/end by the payload id
        only (`:600`/`:618`), and session-partitioning readers
        (ceo-escalation-detector) split one lifecycle across two ids when
        any producer disagrees — so the four flip TOGETHER (S337 P2 sweep +
        this wave's pair-rail r1). Structural (AST operand order); the
        timestamp fallback stays; `payload_sid` still travels separately, no
        fallback. Behavioural halves: `TestProducerIdPrecedence` (recorded
        rows) and `TestProducerConsumerAlignment` (anchored by the consumer)."""
        cases = (
            (SessionStart.main, "getattr(event, 'session_id'"),
            (UserPromptSubmit.main, "getattr(event, 'session_id'"),
            (Stop.main, "getattr(event, 'session_id'"),
            (SessionEnd.main, "payload_sid"),
        )
        for hook_main, payload_token in cases:
            with self.subTest(hook=hook_main.__module__):
                ops = _session_id_operands(hook_main)
                payload_idx = next(
                    i for i, op in enumerate(ops) if payload_token in op
                )
                env_idx = next(
                    i for i, op in enumerate(ops) if "CLAUDE_SESSION_ID" in op
                )
                self.assertLess(payload_idx, env_idx, ops)
                self.assertIn(
                    '"%Y%m%dT%H%M%S"', inspect.getsource(hook_main),
                    "timestamp fallback must survive the flip",
                )
        self.assertIn(
            "payload_session_id=payload_sid", inspect.getsource(SessionEnd.main)
        )
'''

_NEW_CLASSES = r'''class TestProducerIdPrecedence(_DeltaBase):
    """PLAN-179-FOLLOWUP (S338) AC item 1 (+ rail r1) — the FOUR legacy
    lifecycle producers resolve the id PAYLOAD-first (payload > env >
    timestamp), mirroring the US8 rail's `payload_sid`. What is asserted is
    the RECORDED row on the isolated chain, never the variable the hook
    computed. Each producer runs through its real `main()` (stdin event +
    environment), the same code path the harness drives."""

    ENV_ID = "env-divergent-id"

    def _producers(self):
        """(module, payload-without-id, recorded action) for the four
        lifecycle hooks, in lifecycle order."""
        return (
            (SessionStart, {"hook_event_name": "SessionStart"}, "session_start"),
            (UserPromptSubmit,
             {"hook_event_name": "UserPromptSubmit",
              "prompt": "hello from the harness"},
             "prompt_submitted"),
            (Stop, {"hook_event_name": "Stop"}, "session_stop"),
            (SessionEnd, {"hook_event_name": "SessionEnd"}, "session_end"),
        )

    def _drive(self, module, payload: dict, env_session_id) -> None:
        # CEO_EXTENDED_LIFECYCLE "" = kill-switch inactive (a stray "0" in
        # the parent shell would silence all four hooks and vacuously pass a
        # "no row under the env id" assertion). CEO_SESSION_MEMORY_DELTA 0 /
        # CEO_OPTIMIZER 0: the delta rail and the prompt optimizer are not
        # the subject — only the LEGACY producer's row is.
        rc = _run_hook_main(module, payload, {
            "CLAUDE_SESSION_ID": env_session_id,
            "CEO_EXTENDED_LIFECYCLE": "",
            "CEO_SESSION_MEMORY_DELTA": "0",
            "CEO_OPTIMIZER": "0",
        })
        self.assertEqual(rc, 0)

    def _assert_recorded_payload_id(self, module, payload, action) -> None:
        self._drive(module, dict(payload, session_id=self.SESSION_ID), self.ENV_ID)
        rows = self._chain_rows(action)
        self.assertEqual([r.get("session_id") for r in rows], [self.SESSION_ID])
        self.assertNotEqual(rows[0].get("session_id"), self.ENV_ID)

    def test_session_start_records_payload_id_under_divergent_env(self) -> None:
        module, payload, action = self._producers()[0]
        self._assert_recorded_payload_id(module, payload, action)

    def test_prompt_submitted_records_payload_id_under_divergent_env(self) -> None:
        module, payload, action = self._producers()[1]
        self._assert_recorded_payload_id(module, payload, action)

    def test_session_stop_records_payload_id_under_divergent_env(self) -> None:
        module, payload, action = self._producers()[2]
        self._assert_recorded_payload_id(module, payload, action)

    def test_session_end_records_payload_id_under_divergent_env(self) -> None:
        module, payload, action = self._producers()[3]
        self._assert_recorded_payload_id(module, payload, action)

    def test_env_id_is_the_fallback_when_payload_has_no_id(self) -> None:
        """Precedence, not replacement: a payload WITHOUT an id still falls
        back to CLAUDE_SESSION_ID (the pre-flip behaviour for that case),
        for all four producers."""
        for module, payload, action in self._producers():
            with self.subTest(action=action):
                self._drive(module, dict(payload), "env-only-id")
                rows = self._chain_rows(action)
                self.assertEqual(
                    [r.get("session_id") for r in rows], ["env-only-id"]
                )

    def test_timestamp_fallback_when_neither_carries_an_id(self) -> None:
        """Neither payload nor env: the UTC timestamp id (`%Y%m%dT%H%M%S`)
        is kept as the terminal fallback for all four producers."""
        for module, payload, action in self._producers():
            with self.subTest(action=action):
                self._drive(module, dict(payload), None)
                rows = self._chain_rows(action)
                self.assertEqual(len(rows), 1, action)
                sid = rows[0].get("session_id")
                self.assertIsInstance(sid, str)
                self.assertRegex(sid, r"^\d{8}T\d{6}$")


class TestProducerConsumerAlignment(_DeltaBase):
    """PLAN-179-FOLLOWUP (S338) AC item 2 — producer -> consumer end to end on
    the isolated chain with CLAUDE_SESSION_ID DIVERGENT from the payload: the
    rows the real producers write now carry the id the payload-gated consumer
    reads. The consumer itself is unchanged — its lock
    `test_divergent_env_id_never_anchors` stays; this is the other side of
    the same coin (the case that degraded to start_unknown now resolves)."""

    ENV_ID = "env-divergent-id"

    def _env(self) -> dict:
        return {"CLAUDE_SESSION_ID": self.ENV_ID, "CEO_EXTENDED_LIFECYCLE": ""}

    def test_divergent_env_start_is_anchored_by_payload_gated_consumer(self) -> None:
        """The `session_start` written by the REAL producer under a divergent
        env is the chain anchor of THIS payload id (`anchor_source=chain`);
        the env id anchors nothing (consumer lock seen from the producer
        side). Pre-flip this exact flow was start_unknown / none."""
        rc = _run_hook_main(
            SessionStart,
            {"hook_event_name": "SessionStart", "session_id": self.SESSION_ID},
            self._env(),
        )
        self.assertEqual(rc, 0)
        starts = self._chain_rows("session_start")
        self.assertEqual([r.get("session_id") for r in starts], [self.SESSION_ID])
        start_ts = SessionEnd._parse_wire_ts(starts[0].get("ts"))
        self.assertIsNotNone(start_ts)
        # The wire ts is second-floor, so the consumer opens the window at
        # the NEXT whole second (`start_ts += 1.0`, SessionEnd.py — a write
        # inside the start's own second is never claimed). Wait for that
        # boundary on the REAL clock (bounded: < 1.1 s) instead of mocking
        # the ceiling: the contract under test is the production one.
        delay = (start_ts + 1.0 + 0.05) - time.time()
        if delay > 0:
            time.sleep(delay)
        self._mkmem("fresh.md", time.time())
        d = self._observe()
        self.assertEqual(d["anchor_source"], "chain")
        self.assertEqual(d["outcome"], "written")
        self.assertEqual(d["modified_count"], 1)
        ts, src = SessionEnd._session_start_ts(self.ENV_ID, self.repo_root)
        self.assertEqual((ts, src), (None, "none"))

    def test_divergent_env_end_segments_the_resume_window(self) -> None:
        """The S337 leg: the `session_end` written by the REAL legacy producer
        under a divergent env is the segmentation boundary the consumer reads
        by payload id (rail r22 P2-b): a native resume of the same id anchors
        AFTER it, so a topic written in the previous invocation is not
        reported as written in the resumed one. Pre-flip the end row carried
        the env id, the boundary was invisible, and this flow said `written`."""
        now = time.time()
        self._seed_session_start(now - 7200)      # previous invocation's start
        self._mkmem("older-topic.md", now - 6000)  # written back then
        self._age_dir(now - 6000)
        rc = _run_hook_main(
            SessionEnd,
            {"hook_event_name": "SessionEnd", "session_id": self.SESSION_ID},
            self._env(),
        )
        self.assertEqual(rc, 0)
        ends = self._chain_rows("session_end")
        self.assertEqual([r.get("session_id") for r in ends], [self.SESSION_ID])
        self._seed_session_start(now - 1800)      # the resume, same id
        d = self._observe()
        self.assertEqual(d["anchor_source"], "chain")
        self.assertEqual(d["outcome"], "absent")
        self.assertEqual(d["modified_count"], 0)


'''

# --------------------------------------------------------------------------
# (path, ancora EXATA, substituto, ocorrencias esperadas)
# A ordem e a ordem de aplicacao; cada ancora e contada ANTES de qualquer
# escrita (passo 1), entao um refuse deixa a arvore intocada.
# --------------------------------------------------------------------------
EDITS: List[Tuple[str, str, str, int]] = [
    # ------------------------------------------------ SessionStart.py::main
    (
        START_REL,
        '    session_id = (\n'
        '        os.environ.get("CLAUDE_SESSION_ID", "")\n'
        '        or getattr(event, "session_id", "") or ""\n'
        '    )\n'
        '    if not session_id:\n'
        '        session_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")\n',
        _QUARTET_COMMENT
        + '    session_id = (\n'
        '        (getattr(event, "session_id", "") or "")\n'
        '        or os.environ.get("CLAUDE_SESSION_ID", "")\n'
        '    )\n'
        '    if not session_id:\n'
        '        session_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")\n',
        1,
    ),
    # -------------------------------------------- UserPromptSubmit.py::main
    (
        PROMPT_REL,
        '    session_id = (\n'
        '        os.environ.get("CLAUDE_SESSION_ID", "")\n'
        '        or getattr(event, "session_id", "") or ""\n'
        '    ) or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")\n'
        '    repo_root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())\n',
        _QUARTET_COMMENT
        + '    session_id = (\n'
        '        (getattr(event, "session_id", "") or "")\n'
        '        or os.environ.get("CLAUDE_SESSION_ID", "")\n'
        '    ) or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")\n'
        '    repo_root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())\n',
        1,
    ),
    # -------------------------------------------------------- Stop.py::main
    (
        STOP_REL,
        '    session_id = (\n'
        '        os.environ.get("CLAUDE_SESSION_ID", "")\n'
        '        or getattr(event, "session_id", "") or ""\n'
        '    ) or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")\n'
        '    reason = os.environ.get("CLAUDE_STOP_REASON", "user_stop")\n',
        _QUARTET_COMMENT
        + '    session_id = (\n'
        '        (getattr(event, "session_id", "") or "")\n'
        '        or os.environ.get("CLAUDE_SESSION_ID", "")\n'
        '    ) or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")\n'
        '    reason = os.environ.get("CLAUDE_STOP_REASON", "user_stop")\n',
        1,
    ),
    # -------------------------------------------------- SessionEnd.py::main
    (
        END_REL,
        '    # Rail r12 P2-b (corrige a r3): o ciclo de vida LEGADO (session_end,\n'
        '    # closeout de dashboard/audit-tokens, cleanup) usa a MESMA precedencia\n'
        '    # env-first do SessionStart.py:559-561 — a v2.60 declara "NO change to\n'
        '    # any existing action", e um id divergente quebraria a correlacao\n'
        '    # start<->end das actions landadas. A doutrina payload-only da r3/r4\n'
        '    # (env e agent-spoofable, consensus M2) vale INTEIRA no rail NOVO:\n'
        '    # payload_sid viaja separado, sem fallback nenhum, e e o unico id que\n'
        '    # o memory-delta aceita (a trava de consumo esta testada).\n'
        '    payload_sid = getattr(event, "session_id", "") or ""\n'
        '    session_id = (\n'
        '        os.environ.get("CLAUDE_SESSION_ID", "")\n'
        '        or payload_sid\n'
        '    ) or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")\n',
        '    # Rail r12 P2-b (wave-179close) kept the LEGACY lifecycle (session_end,\n'
        '    # dashboard/audit-tokens closeout, cleanup) env-first to mirror the\n'
        '    # SessionStart producer of the day. PLAN-179-FOLLOWUP (S338) flips the\n'
        '    # FOUR lifecycle producers (SessionStart / UserPromptSubmit / Stop /\n'
        '    # SessionEnd) together to PAYLOAD-first — payload > env > timestamp —\n'
        '    # so start<->end correlation is preserved AND the ids are the ones the\n'
        '    # US8 consumer reads: `_session_start_ts` matches `session_start` and\n'
        '    # segments on `session_end` by the PAYLOAD id only (env is\n'
        '    # agent-spoofable and never anchors — rails r3/r4, consumer lock kept).\n'
        '    # An env-first `session_end` was invisible to that segmentation whenever\n'
        '    # env != payload (S337 P2 sweep); a PARTIAL flip would split one\n'
        '    # lifecycle across two ids (pair-rail r1 of this wave). `payload_sid`\n'
        '    # still travels separately, with NO fallback: it is the only id the\n'
        '    # memory-delta rail accepts.\n'
        '    payload_sid = getattr(event, "session_id", "") or ""\n'
        '    session_id = (\n'
        '        payload_sid\n'
        '        or os.environ.get("CLAUDE_SESSION_ID", "")\n'
        '    ) or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")\n',
        1,
    ),
    # ------------------------------------ test_session_end_memory_delta.py
    (
        TEST_REL,
        "import importlib\n"
        "import importlib.util\n"
        "import json\n"
        "import os\n"
        "import sys\n"
        "import time\n"
        "import types\n"
        "import unittest\n",
        "import ast\n"
        "import importlib\n"
        "import importlib.util\n"
        "import inspect\n"
        "import io\n"
        "import json\n"
        "import os\n"
        "import sys\n"
        "import time\n"
        "import types\n"
        "import unittest\n",
        1,
    ),
    (
        TEST_REL,
        "import SessionEnd  # type: ignore  # noqa: E402\n"
        "import _lib  # noqa: E402\n",
        "import SessionEnd  # type: ignore  # noqa: E402\n"
        "import SessionStart  # type: ignore  # noqa: E402\n"
        "import Stop  # type: ignore  # noqa: E402\n"
        "import UserPromptSubmit  # type: ignore  # noqa: E402\n"
        "import _lib  # noqa: E402\n",
        1,
    ),
    (
        TEST_REL,
        "class _DeltaBase(TestEnvContext):\n",
        _TEST_HELPERS + "class _DeltaBase(TestEnvContext):\n",
        1,
    ),
    (
        TEST_REL,
        "    def _observe(self):\n"
        "        return SessionEnd._memory_delta_observed(self.repo_root, self.SESSION_ID)\n",
        "    def _observe(self):\n"
        "        return SessionEnd._memory_delta_observed(self.repo_root, self.SESSION_ID)\n"
        + _CHAIN_ROWS_METHOD,
        1,
    ),
    (
        TEST_REL,
        '        """Rail r6 P2-b LOCK — a `session_start` recorded under a DIFFERENT\n'
        '        id (the SessionStart env-first producer, with CLAUDE_SESSION_ID\n'
        '        divergent from the payload) must NOT anchor this payload-id scan:\n'
        '        env is agent-spoofable and never anchors (rail r4 decision, KEPT —\n'
        '        weakening it re-enters the security VETO gate). Degradation is\n'
        '        start_unknown: safe, never a wrong window. Producer-side ID\n'
        '        alignment is PLAN-179-FOLLOWUP material, not a consumer change."""\n',
        '        """Rail r6 P2-b LOCK — a `session_start` recorded under a DIFFERENT\n'
        '        id (historically the env-first SessionStart producer with\n'
        '        CLAUDE_SESSION_ID divergent from the payload; today any writer\n'
        '        using another id) must NOT anchor this payload-id scan: env is\n'
        '        agent-spoofable and never anchors (rail r4 decision, KEPT —\n'
        '        weakening it re-enters the security VETO gate). Degradation is\n'
        '        start_unknown: safe, never a wrong window. PLAN-179-FOLLOWUP (S338)\n'
        '        aligned the PRODUCERS (payload-first — `TestProducerIdPrecedence`,\n'
        '        `TestProducerConsumerAlignment`); this consumer lock is unchanged."""\n',
        1,
    ),
    (
        TEST_REL,
        '    def test_lifecycle_id_mirrors_sessionstart_env_first(self) -> None:\n'
        '        """Rail r12 P2-b — the LEGACY lifecycle (session_end, closeouts)\n'
        "        keeps SessionStart's env-first precedence (v2.60 declares existing\n"
        '        actions unchanged; a divergent id would break start<->end\n'
        '        correlation). The payload-only doctrine lives ENTIRELY in the new\n'
        '        delta rail (payload_sid, no fallback — consumer lock tested).\n'
        '        Source-level: main() is driven by the stdin adapter and not\n'
        '        honestly constructible here; the delta half is behavioural above."""\n'
        '        import inspect\n'
        '        src = inspect.getsource(SessionEnd.main)\n'
        '        env_pos = src.index(\'os.environ.get("CLAUDE_SESSION_ID"\')\n'
        '        payload_pos = src.index("or payload_sid")\n'
        '        self.assertLess(env_pos, payload_pos,\n'
        '                        "legacy session_id must be env-first")\n'
        '        self.assertIn("payload_session_id=payload_sid", src)\n',
        _STRUCTURAL_LOCK,
        1,
    ),
    (
        TEST_REL,
        'if __name__ == "__main__":\n'
        '    unittest.main()\n',
        _NEW_CLASSES
        + 'if __name__ == "__main__":\n'
        '    unittest.main()\n',
        1,
    ),
]

TOUCHED_BY_EDITS: List[str] = []
for _rel, _old, _new, _n in EDITS:
    if _rel not in TOUCHED_BY_EDITS:
        TOUCHED_BY_EDITS.append(_rel)


class Refuse(Exception):
    pass


def _plan(root: Path) -> None:
    """Passo 1 — conta TODAS as ancoras e recusa antes de qualquer escrita."""
    problems = []
    for rel, old, _new, count in EDITS:
        p = root / rel
        if not p.is_file():
            problems.append("%s: arquivo ausente" % rel)
            continue
        text = p.read_text(encoding="utf-8")
        n = text.count(old)
        if n != count:
            problems.append("%s: ancora encontrada %dx, esperado %d — %r"
                            % (rel, n, count, old[:70]))
    # Ja aplicado? O marcador da wave nao pode existir em NENHUM path tocado:
    # as insercoes puras (helpers, classes novas) deixam a ancora viva e so
    # este guard impede a duplicacao silenciosa numa 2a aplicacao.
    for rel in TOUCHED_BY_EDITS:
        p = root / rel
        if p.is_file() and MARKER in p.read_text(encoding="utf-8"):
            problems.append("%s: ja contem %r — arvore ja patchada?" % (rel, MARKER))
    # Cada substituto de cada path carrega o marcador (o guard acima so vale
    # se isto for verdade — auto-verificado, nao presumido).
    for rel in TOUCHED_BY_EDITS:
        joined = "".join(new for r, _o, new, _c in EDITS if r == rel)
        if MARKER not in joined:
            problems.append("%s: nenhum substituto carrega o marcador %r" % (rel, MARKER))
    if problems:
        raise Refuse("\n".join("  - " + x for x in problems))


def _apply(root: Path) -> List[str]:
    written: List[str] = []
    for rel, old, new, count in EDITS:
        p = root / rel
        text = p.read_text(encoding="utf-8")
        assert text.count(old) == count  # _plan ja garantiu
        p.write_text(text.replace(old, new), encoding="utf-8")
        if rel not in written:
            written.append(rel)
    return sorted(set(written))


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", help="arvore em HEAD a patchar")
    ap.add_argument("--check-only", action="store_true",
                    help="so verifica as ancoras; nao escreve nada")
    ap.add_argument("--list-paths", action="store_true",
                    help="imprime os paths tocados (um por linha) e sai")
    args = ap.parse_args(argv)
    if args.list_paths:
        for rel in TOUCHED_BY_EDITS:
            print(rel)
        return 0
    if not args.root:
        ap.error("--root e obrigatorio (salvo com --list-paths)")
    root = Path(args.root).resolve()
    if not (root / ".claude").is_dir():
        sys.stderr.write("apply-179fu-flip: --root nao parece um checkout: %s\n" % root)
        return 2
    try:
        _plan(root)
        if args.check_only:
            print("apply-179fu-flip: %d edicao(oes) aplicaveis em %d path(s); nada escrito"
                  % (len(EDITS), len(TOUCHED_BY_EDITS)))
            return 0
        written = _apply(root)
    except Refuse as exc:
        sys.stderr.write("apply-179fu-flip: RECUSADO\n%s\n" % exc)
        return 1
    print("apply-179fu-flip: %d edicao(oes) aplicadas em %d path(s):"
          % (len(EDITS), len(written)))
    for rel in written:
        print("  " + rel)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
