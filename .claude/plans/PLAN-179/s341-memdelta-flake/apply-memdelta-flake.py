#!/usr/bin/env python3
"""apply-memdelta-flake.py — DERIVACAO do pack `memdelta-flake` (S340).

Cura DUAS falhas do INSTRUMENTO que deixaram o main VERMELHO em ba15c71
(job `hook-tests-dual-rail (0)`, 1 falha em 6942):

  .../test_session_end_memory_delta.py::TestWireContract::
      test_no_paths_on_the_wire
  AssertionError: 'zz-canary-topic.md' not found in []

(1) O controle positivo herdava os budgets WALL-CLOCK de producao
    (`_MEMORY_DELTA_SCAN_BUDGET_MS` = 50, `_MEMORY_DELTA_ANCHOR_BUDGET_MS`
    = 100, ambos por `time.monotonic()`), que um runner carregado estoura
    sobre um diretorio de 2 entradas. O `_observe` compartilhado passa a
    injetar um budget generoso, com opt-out explicito para os DOIS testes
    (DERIVADOS, nao recordados) que exercitam o budget.
(2) A mensagem de falha nomeava so `names`; DUAS rotas distintas produzem
    `names == []` (medido: scan esfomeado => outcome="error"/anchor="chain";
    anchor esfomeado => outcome="start_unknown"/anchor="none"). As
    asercoes ganham `msg=` com outcome + anchor_source.

Nao mexe em NENHUM path de producao: `.claude/hooks/SessionEnd.py` e
KERNEL e o pack e 100% FREE pelo oraculo `--is-canonical`.

Uso:
    python3 apply-memdelta-flake.py --root <arvore-em-HEAD>
    python3 apply-memdelta-flake.py --root <arvore> --check-only
    python3 apply-memdelta-flake.py --list-paths

Saidas: 0 = aplicado (ou aplicavel); 1 = recusa nomeada; 2 = erro de uso.
Stdlib-only, Python >= 3.9, sem PEP 604 em runtime.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Tuple

TEST_REL = ".claude/hooks/tests/test_session_end_memory_delta.py"

# --------------------------------------------------------------------------
# (path, ancora EXATA, substituto, ocorrencias esperadas)
# Todas as ancoras sao contadas ANTES de qualquer escrita: uma ancora
# ausente, ambigua ou ja aplicada e RECUSA, nunca "best effort".
# --------------------------------------------------------------------------
EDITS: List[Tuple[str, str, str, int]] = [
    # -------------------------------------------------------------- imports
    (
        TEST_REL,
        "from pathlib import Path\n"
        "from unittest import mock\n",
        "from pathlib import Path\n"
        "from typing import Optional\n"
        "from unittest import mock\n",
        1,
    ),
    # ------------------------------------------- budget injetado pelos testes
    (
        TEST_REL,
        "_SENTINEL = object()\n",
        "_SENTINEL = object()\n"
        "\n"
        "#: Budget WALL-CLOCK que ``_DeltaBase._observe`` injeta na observacao.\n"
        "#: Producao capa a passada de stat em 50 ms e o reverse-scan da ancora\n"
        "#: em 100 ms, os dois medidos com ``time.monotonic()`` — WALL clock,\n"
        "#: nao CPU. Um runner carregado estoura QUALQUER um dos dois sobre um\n"
        "#: diretorio de 2 entradas, e as duas exaustoes degradam para\n"
        "#: ``names == []`` (foi assim que o main ficou VERMELHO em ba15c71).\n"
        "#:\n"
        "#: O valor e CALIBRADO, nao chutado. Uma observacao completa (2 topicos\n"
        "#: + ancora assinada) foi MEDIDA em n=30 nesta maquina: p50 0,331 ms,\n"
        "#: max 7,932 ms. Logo os 50 ms de producao sobrevivem a um runner so\n"
        "#: ~6x mais lento que o pior caso local — DENTRO do envelope de drift\n"
        "#: ja documentado para este repo (hook p50 local 77 ms vs 209-435 ms na\n"
        "#: CI). 1 h de budget da ~450.000x de margem, e o primeiro chute de 60 s\n"
        "#: (~7.500x) ja foi REPROVADO pelo controle positivo de relogio x20000.\n"
        "#: O teto e o sentinela de relogio dos testes que mockam\n"
        "#: ``time.monotonic`` (1e9 s), DERIVADO por ast em\n"
        "#: ``test_injected_budget_cannot_outrun_the_mocked_clock`` — 3600 s fica\n"
        "#: 6 ordens de grandeza abaixo dele.\n"
        "#:\n"
        "#: Isto NAO enfraquece asercao nenhuma: remove uma variavel de ambiente\n"
        "#: que nenhum teste aqui pretende exercitar (o budget e um CAP, nao um\n"
        "#: sleep — um budget maior nao alonga run nenhum). O valor de PRODUCAO\n"
        "#: fica intocado: este pack nao edita ``SessionEnd.py`` (KERNEL).\n"
        "#: FALSO-NEGATIVO DECLARADO: um runner >450.000x mais lento ainda\n"
        "#: esfomearia a passada — nesse caso a mensagem NOMEIA o outcome (item\n"
        "#: 2 desta cura), entao o modo de falha e diagnosticavel, nao mudo.\n"
        "_TEST_WALL_BUDGET_MS = 3600000\n",
        1,
    ),
    # ------------------------------------------------- _observe + _delta_diag
    (
        TEST_REL,
        "    def _observe(self):\n"
        "        return SessionEnd._memory_delta_observed("
        "self.repo_root, self.SESSION_ID)\n",
        '    def _observe(self, budget_ms: Optional[int] = _TEST_WALL_BUDGET_MS):\n'
        '        """A observacao sob teste, com os budgets WALL-CLOCK injetados.\n'
        "\n"
        "        Este e o UNICO call site de ``_memory_delta_observed`` neste\n"
        "        arquivo (DERIVADO, nao recordado: ``grep -c\n"
        "        '_memory_delta_observed('`` == 1), logo a costura de relogio\n"
        "        pertence AQUI e nao ao helper de uma classe — flake por carga\n"
        "        de runner e propriedade de toda observacao, nao dos testes de\n"
        "        wire. As duas rotas de degradacao foram MEDIDAS: scan\n"
        "        esfomeado => ``outcome=\"error\"``, ``anchor_source=\"chain\"``;\n"
        "        ancora esfomeada => ``outcome=\"start_unknown\"``,\n"
        "        ``anchor_source=\"none\"``. As duas devolvem ``names == []`` —\n"
        "        o sintoma exato de ba15c71 (``'zz-canary-topic.md' not found\n"
        "        in []``), e por isso os DOIS budgets sao injetados.\n"
        "\n"
        '        ``budget_ms=None`` significa "quem chama e dono do relogio", e\n'
        "        e reservado aos DOIS testes que exercitam o budget de verdade.\n"
        "        O conjunto foi DERIVADO, nao recordado: aplicando o patch\n"
        "        interno da cura sobre TODAS as chamadas do arquivo, falharam\n"
        "        exatamente ``test_slow_final_stat_is_error`` (dorme 80 ms\n"
        "        acima do cap real de 50 ms) e\n"
        "        ``test_budget_exhaustion_is_not_written`` (patcha a constante\n"
        "        para -1); os outros 58 passaram sem mudanca. Os tres testes\n"
        "        que mockam ``time.monotonic`` mantem os dentes de qualquer\n"
        '        forma — eles esfomeiam o RELOGIO, nao a constante."""\n'
        "        if budget_ms is None:\n"
        "            return SessionEnd._memory_delta_observed(\n"
        "                self.repo_root, self.SESSION_ID\n"
        "            )\n"
        "        with mock.patch.object(\n"
        '            SessionEnd, "_MEMORY_DELTA_SCAN_BUDGET_MS", budget_ms\n'
        "        ), mock.patch.object(\n"
        '            SessionEnd, "_MEMORY_DELTA_ANCHOR_BUDGET_MS", budget_ms\n'
        "        ):\n"
        "            return SessionEnd._memory_delta_observed(\n"
        "                self.repo_root, self.SESSION_ID\n"
        "            )\n"
        "\n"
        "    @staticmethod\n"
        "    def _delta_diag(delta) -> str:\n"
        '        """Digest de UMA linha de uma observacao, para ``msg=``.\n'
        "\n"
        "        O log de CI da canaria reprovada mostrava so ``[]``, que nao\n"
        "        distingue uma passada de stat esfomeada (``outcome=\"error\"``)\n"
        "        de uma ancora irresoluvel (``outcome=\"start_unknown\"``) — duas\n"
        "        causas, uma mensagem, e nenhuma triagem sem re-rodar. O digest\n"
        "        nomeia OUTCOME e ANCHOR_SOURCE, que sao exatamente o\n"
        "        discriminante medido. Sem path e sem slug: esses dois sao\n"
        "        asseridos AUSENTES do wire neste mesmo arquivo, e uma\n"
        '        mensagem de falha nao e lugar de reintroduzi-los."""\n'
        '        return (\n'
        '            "outcome=%r anchor_source=%r files_count=%r "\n'
        '            "modified_count=%r index_modified=%r names=%r"\n'
        '            % (delta.get("outcome"), delta.get("anchor_source"),\n'
        '               delta.get("files_count"), delta.get("modified_count"),\n'
        '               delta.get("index_modified"), delta.get("names"))\n'
        "        )\n",
        1,
    ),
    # ----------------------------------- opt-out 1/2: stat final lento (real)
    (
        TEST_REL,
        '        with mock.patch.object(Path, "lstat", _slow_lstat):\n'
        "            d = self._observe()\n"
        '        self.assertEqual(d["outcome"], "error")\n',
        '        with mock.patch.object(Path, "lstat", _slow_lstat):\n'
        "            # budget_ms=None: ESTE teste e dono do relogio — dorme 80 ms\n"
        "            # acima do cap REAL de 50 ms, entao precisa do valor de\n"
        "            # producao. Um runner carregado so torna a premissa MAIS\n"
        "            # verdadeira (sleep > budget), nunca menos.\n"
        "            d = self._observe(budget_ms=None)\n"
        '        self.assertEqual(\n'
        '            d["outcome"], "error",\n'
        '            "stat final acima do budget nao pode virar written/absent; "\n'
        '            + self._delta_diag(d),\n'
        "        )\n",
        1,
    ),
    # ------------------------------ opt-out 2/2: constante patchada para -1
    (
        TEST_REL,
        '        with mock.patch.object(SessionEnd, "_MEMORY_DELTA_SCAN_BUDGET_MS", -1):\n'
        "            d = self._observe()\n"
        '        self.assertEqual(d["outcome"], "error")\n'
        '        self.assertNotEqual(d["outcome"], "written")\n',
        '        with mock.patch.object(SessionEnd, "_MEMORY_DELTA_SCAN_BUDGET_MS", -1):\n'
        "            # budget_ms=None: o patch de FORA e o sujeito do teste; sem\n"
        "            # o opt-out a injecao interna do `_observe` o sobrescreveria\n"
        "            # e o teste morreria em silencio (mediria producao).\n"
        "            d = self._observe(budget_ms=None)\n"
        '        self.assertEqual(\n'
        '            d["outcome"], "error", self._delta_diag(d)\n'
        "        )\n"
        '        self.assertNotEqual(d["outcome"], "written", self._delta_diag(d))\n',
        1,
    ),
    # ------------------------------- novos testes (contrato + auto-teste)
    (
        TEST_REL,
        '        self.assertEqual(d["outcome"], "error")\n'
        '        self.assertEqual(d["files_count"], 1)\n'
        '        self.assertEqual(d["modified_count"], 1)\n'
        "\n"
        "    def test_name_scan_respects_wall_deadline(self) -> None:\n",
        '        self.assertEqual(d["outcome"], "error")\n'
        '        self.assertEqual(d["files_count"], 1)\n'
        '        self.assertEqual(d["modified_count"], 1)\n'
        "\n"
        "    def test_budget_exhaustion_leaves_names_empty_not_raw(self) -> None:\n"
        '        """DECISAO (S340): o retorno de timeout do loop de entradas\n'
        "        copiar apenas os COUNTS e deixar ``names == []`` e\n"
        "        INTENCIONAL, nao uma omissao.\n"
        "\n"
        "        ``names`` nao e uma vista de ``modified``: e a projecao\n"
        "        SANITIZADA construida por um loop POSTERIOR\n"
        "        (``_sanitize_memory_basename`` derruba basenames\n"
        "        hostis/injection-shaped — varios testes desta classe\n"
        "        exercitam esse gate). No deadline do loop de entradas aquele\n"
        "        loop ainda nao rodou, entao ``[]`` e o conjunto sanitizado\n"
        '        VERDADEIRO; "consertar" producao copiando ``modified`` para\n'
        "        ``names`` poria basenames NAO sanitizados num campo cujo\n"
        '        contrato e "sanitizado" — regressao de seguranca, nao cura. O\n'
        '        docstring de producao diz "partial COUNTS, plural" de\n'
        "        proposito. Este teste PINA a invariante para que um conserto\n"
        "        bem-intencionado futuro fique VERMELHO: os counts sobrevivem,\n"
        '        os names nao, e a chave esta sempre PRESENTE."""\n'
        "        now = time.time()\n"
        '        self._mkmem("t1.md", now)\n'
        '        self._mkmem("t2.md", now)\n'
        "        # mesma escada do teste acima: o 4o read do relogio estoura,\n"
        "        # ja com uma entrada contada como modificada.\n"
        "        seq = iter([0.0, 0.0, 0.0])\n"
        "\n"
        "        def _mono():\n"
        "            try:\n"
        "                return next(seq)\n"
        "            except StopIteration:\n"
        "                return 1e9\n"
        "\n"
        "        with mock.patch.object(\n"
        '            SessionEnd, "_session_start_ts",\n'
        '            return_value=(now - 3600.0, "chain"),\n'
        '        ), mock.patch.object(SessionEnd.time, "monotonic", _mono):\n'
        "            d = self._observe()\n"
        '        self.assertIn("names", d, self._delta_diag(d))\n'
        "        self.assertGreaterEqual(\n"
        '            d["modified_count"], 1,\n'
        '            "controle anti-vacuo: sem uma entrada modificada COLETADA "\n'
        '            "a asercao de names vazio seria trivial; "\n'
        "            + self._delta_diag(d),\n"
        "        )\n"
        "        self.assertEqual(\n"
        '            d["names"], [],\n'
        '            "names e a projecao SANITIZADA, nunca uma copia de "\n'
        '            "modified: no deadline do loop de entradas o sanitizador "\n'
        '            "ainda nao rodou; "\n'
        "            + self._delta_diag(d),\n"
        "        )\n"
        "\n"
        "    def test_injected_budget_cannot_outrun_the_mocked_clock(self) -> None:\n"
        '        """Auto-teste do INSTRUMENTO: o budget generoso que ``_observe``\n'
        "        injeta tem de ficar ABAIXO do sentinela que os testes de\n"
        "        relogio mockado devolvem depois da escada — senao eles param\n"
        "        de esgotar e perdem os dentes. O sentinela e DERIVADO da\n"
        "        FONTE deles por ast, nunca recordado: um valor digitado de\n"
        '        memoria envelhece em silencio."""\n'
        "        sentinels = []\n"
        "        for meth in (\n"
        "            TestSpecSurface.test_budget_exhaustion_preserves_partial_counts,\n"
        "            TestSpecSurface.test_name_scan_respects_wall_deadline,\n"
        "            TestSpecSurface.test_final_sanitize_exhaustion_is_error,\n"
        "        ):\n"
        "            tree = ast.parse(textwrap.dedent(inspect.getsource(meth)))\n"
        "            for node in ast.walk(tree):\n"
        "                if (\n"
        "                    isinstance(node, ast.Constant)\n"
        "                    and isinstance(node.value, (int, float))\n"
        "                    and not isinstance(node.value, bool)\n"
        "                    and node.value >= 1e6\n"
        "                ):\n"
        "                    sentinels.append(float(node.value))\n"
        "        self.assertTrue(\n"
        "            sentinels,\n"
        '            "nenhum sentinela de relogio encontrado — a derivacao "\n'
        '            "envelheceu (teste renomeado?) e o bound abaixo seria "\n'
        '            "VACUO",\n'
        "        )\n"
        "        self.assertLess(\n"
        "            _TEST_WALL_BUDGET_MS / 1000.0, min(sentinels),\n"
        '            "budget injetado (%d ms) alcancaria o sentinela %r: os "\n'
        '            "testes de exaustao deixariam de esgotar"\n'
        "            % (_TEST_WALL_BUDGET_MS, min(sentinels)),\n"
        "        )\n"
        "\n"
        "    def test_name_scan_respects_wall_deadline(self) -> None:\n",
        1,
    ),
    # ----------------------------------------- import usado pelo auto-teste
    (
        TEST_REL,
        "import sys\n"
        "import time\n"
        "import types\n",
        "import sys\n"
        "import textwrap\n"
        "import time\n"
        "import types\n",
        1,
    ),
    # ------------------------- guarda anti-vacuo dentro do _emit_captured
    (
        TEST_REL,
        "    def _emit_captured(self):\n"
        "        now = time.time()\n"
        '        self._mkmem("zz-canary-topic.md", now)\n'
        '        self._mkmem("MEMORY.md", now)\n'
        "        self._seed_session_start(now - 3600)\n"
        "        d = self._observe()\n"
        "        captured: list = []\n"
        "        with _stub_audit_emit(captured):\n"
        "            SessionEnd._emit_session_memory_delta(\n"
        "                session_id=self.SESSION_ID, repo_root=self.repo_root, delta=d,\n"
        "            )\n"
        "        self.assertEqual(len(captured), 1)\n"
        "        return d, captured[0]\n",
        "    def _emit_captured(self):\n"
        '        """Planta a canaria + o indice, observa, e captura o UNICO evento\n'
        "        emitido. A observacao e GUARDADA antes de ir para as asercoes de\n"
        "        wire: uma observacao degradada (relogio esfomeado, ancora\n"
        "        irresoluvel) faz todo ``assertNotIn`` a jusante passar\n"
        "        VACUAMENTE, entao a guarda dispara AQUI, nomeando a rota, em vez\n"
        '        de aparecer tres callers depois como ``not found in []``."""\n'
        "        now = time.time()\n"
        '        self._mkmem("zz-canary-topic.md", now)\n'
        '        self._mkmem("MEMORY.md", now)\n'
        "        self._seed_session_start(now - 3600)\n"
        "        d = self._observe()\n"
        "        self.assertEqual(\n"
        '            d["outcome"], "written",\n'
        '            "observacao DEGRADADA — as asercoes de wire abaixo "\n'
        '            "passariam vacuamente; "\n'
        "            + self._delta_diag(d),\n"
        "        )\n"
        "        captured: list = []\n"
        "        with _stub_audit_emit(captured):\n"
        "            SessionEnd._emit_session_memory_delta(\n"
        "                session_id=self.SESSION_ID, repo_root=self.repo_root, delta=d,\n"
        "            )\n"
        "        self.assertEqual(\n"
        "            len(captured), 1,\n"
        '            "esperado EXATAMENTE um evento emitido; "\n'
        "            + self._delta_diag(d),\n"
        "        )\n"
        "        return d, captured[0]\n",
        1,
    ),
    # --------------------------- mensagens do teste que ficou VERMELHO na CI
    (
        TEST_REL,
        "        d, kw = self._emit_captured()\n"
        "        self.assertEqual(set(kw), self._EXPECTED_KWARGS)\n"
        '        self.assertIn("zz-canary-topic.md", d["names"])\n'
        "        serialized = json.dumps(kw)\n"
        '        self.assertNotIn("zz-canary-topic", serialized)\n'
        "        self.assertNotIn(str(self.memory_dir), serialized)\n"
        "        self.assertNotIn(self.slug, serialized)\n",
        "        d, kw = self._emit_captured()\n"
        "        self.assertEqual(\n"
        "            set(kw), self._EXPECTED_KWARGS,\n"
        '            "kwargs set != a lista de caller do §4; %r" % (sorted(kw),),\n'
        "        )\n"
        "        self.assertIn(\n"
        '            "zz-canary-topic.md", d["names"],\n'
        '            "canaria anti-vacuo AUSENTE dos names OBSERVADOS — os "\n'
        '            "assertNotIn abaixo passariam vacuamente; "\n'
        "            + self._delta_diag(d),\n"
        "        )\n"
        "        serialized = json.dumps(kw)\n"
        "        self.assertNotIn(\n"
        '            "zz-canary-topic", serialized,\n'
        '            "basename plantado chegou ao wire: %s" % serialized,\n'
        "        )\n"
        "        self.assertNotIn(\n"
        "            str(self.memory_dir), serialized,\n"
        '            "o path do dir de memoria chegou ao wire: %s" % serialized,\n'
        "        )\n"
        "        self.assertNotIn(\n"
        "            self.slug, serialized,\n"
        '            "o slug do projeto chegou ao wire: %s" % serialized,\n'
        "        )\n",
        1,
    ),
    # ------------------- refutacao do CEO (S341): o seam da ANCORA em setUp
    # O seam `_observe` cobre o UNICO call site de `_memory_delta_observed`,
    # mas `_session_start_ts` — dono de `_MEMORY_DELTA_ANCHOR_BUDGET_MS` — e
    # chamado DIRETAMENTE de 13 sitios deste arquivo, que ficaram no relogio
    # de producao. MEDIDO com os dois budgets zerados: 23 falhas antes do
    # pack, 3 depois dele, 0 depois desta edicao. Patchar o modulo em setUp
    # cobre todos os call sites, presentes e futuros, sem tocar 13 deles.
    # SO a ancora: patchar tambem o scan quebrou `test_slow_final_stat_is_error`,
    # que dorme 80 ms de proposito e PRECISA dos 50 ms reais (opta por sair
    # via `_observe(budget_ms=None)` — opt-out que um patch de setUp atropela).
    (
        TEST_REL,
        "        self.memory_dir = (\n"
        '            Path.home() / ".claude" / "projects" / self.slug / "memory"\n'
        "        )\n"
        "        self.memory_dir.mkdir(parents=True, exist_ok=True)\n"
        "\n"
        "    # -- helpers ----------------------------------------------------------\n",
        "        self.memory_dir = (\n"
        '            Path.home() / ".claude" / "projects" / self.slug / "memory"\n'
        "        )\n"
        "        self.memory_dir.mkdir(parents=True, exist_ok=True)\n"
        "        # CEO refutation of pack `memdelta-flake` (S341): the `_observe` seam\n"
        "        # covers the ONE call site of `_memory_delta_observed`, but\n"
        "        # `_session_start_ts` — which owns `_MEMORY_DELTA_ANCHOR_BUDGET_MS` —\n"
        "        # is called DIRECTLY from 13 sites in this file, and those stayed on\n"
        "        # production's wall clock. MEASURED with both budgets starved to 0:\n"
        "        # 23 failures before the pack, 3 after it, 0 after this. Patching the\n"
        "        # module here covers every call site, present and future, without\n"
        "        # touching 13 of them — a per-site edit would leave the 14th blind.\n"
        "        # SCOPE, narrowed by measurement (not by taste): ONLY the anchor\n"
        "        # budget is patched here. Patching the SCAN budget too broke\n"
        "        # `test_slow_final_stat_is_error`, which sleeps 80 ms to prove a slow\n"
        "        # final stat yields outcome=\"error\" and therefore NEEDS production's\n"
        "        # 50 ms — it opts out via `_observe(budget_ms=None)`, an opt-out a\n"
        "        # setUp-level patch silently overrides. The scan budget already has\n"
        "        # its seam in `_observe`; the anchor budget had none, which is exactly\n"
        "        # the gap. A test that deliberately starves the anchor must patch it\n"
        "        # itself, inside the test, where the intent is visible.\n"
        "        _b = mock.patch.object(\n"
        '            SessionEnd, "_MEMORY_DELTA_ANCHOR_BUDGET_MS", _TEST_WALL_BUDGET_MS\n'
        "        )\n"
        "        _b.start()\n"
        "        self.addCleanup(_b.stop)\n"
        "\n"
        "    # -- helpers ----------------------------------------------------------\n",
        1,
    ),
]

NEW_FILES: List[Tuple[str, str]] = []


def _fail(msg: str) -> None:
    sys.stderr.write("REFUSE: %s\n" % msg)
    raise SystemExit(1)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", help="arvore alvo (worktree em HEAD)")
    ap.add_argument("--check-only", action="store_true")
    ap.add_argument("--list-paths", action="store_true")
    args = ap.parse_args()

    if args.list_paths:
        seen = []
        for rel, _a, _b, _n in EDITS:
            if rel not in seen:
                seen.append(rel)
        for rel, _c in NEW_FILES:
            if rel not in seen:
                seen.append(rel)
        for rel in seen:
            print(rel)
        return 0

    if not args.root:
        sys.stderr.write("usage: --root <tree> | --list-paths\n")
        return 2
    root = Path(args.root).resolve()
    if not root.is_dir():
        _fail("root nao e diretorio: %s" % root)

    # ---- passo 1: PLANEJAR tudo (nenhuma escrita antes de tudo validar) --
    texts = {}
    for rel, anchor, repl, count in EDITS:
        target = root / rel
        if rel not in texts:
            if not target.is_file():
                _fail("path ausente: %s" % rel)
            texts[rel] = target.read_text(encoding="utf-8")
        body = texts[rel]
        seen = body.count(anchor)
        if seen != count:
            if seen == 0 and repl and repl in body:
                _fail(
                    "ancora JA APLICADA em %s (substituto presente): %r"
                    % (rel, anchor[:70])
                )
            _fail(
                "ancora com %d ocorrencia(s), esperado %d em %s: %r"
                % (seen, count, rel, anchor[:70])
            )
        texts[rel] = body.replace(anchor, repl, count)

    for rel, content in NEW_FILES:
        target = root / rel
        if target.exists():
            _fail("arquivo a CRIAR ja existe: %s" % rel)
        texts[rel] = content

    if args.check_only:
        print("OK check-only: %d edicoes aplicaveis, %d arquivo(s) novo(s)"
              % (len(EDITS), len(NEW_FILES)))
        return 0

    # ---- passo 2: escrever ------------------------------------------------
    for rel, body in texts.items():
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(body, encoding="utf-8")
        print("wrote %s" % rel)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
