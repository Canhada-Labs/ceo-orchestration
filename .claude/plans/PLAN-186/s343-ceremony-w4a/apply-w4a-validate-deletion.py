#!/usr/bin/env python3
"""apply-w4a-validate-deletion.py — a DERIVACAO do patch da wave-s343-w4a (PLAN-186).

Este script E o material versionado da cerimonia W4a. Ele aplica TODAS as
edicoes da wave sobre uma arvore em HEAD, com ancora EXATA por edicao e
contagem declarada — uma ancora ausente, ambigua ou ja aplicada e RECUSA
nomeada, nunca um "best effort". O `finalize-w4a.sh` (passo 4a) e o
`OWNER-S343-W4A-LAND.sh` (V3) provam que `HEAD + este script == patch`
BYTE A BYTE em cada path.

O QUE A WAVE ENTREGA (dois paths, ambos CANONICOS):

1. `.github/workflows/validate.yml` — a DELECAO medida pela W4a:
   os dois steps mais caros do job `validate` saem, porque o job
   `hook-tests-python-matrix` ja roda a UNIAO EXATA deles em 3.9 e 3.12 no
   mesmo evento `push`. Dez edicoes:
     E1        a nota de double-collection deixa de citar um step que a
               mesma edicao remove (um arquivo nao pode se contradizer);
     E2        o step «Run Python hook unit tests (CEO_HOOK_ADAPTER=claude default)»;
     E3        o step «Run Python script unit tests» e o banner DELE (o `# ---`
               de cima sobrevive e abre o banner do step seguinte);
     E4        o `env:` da matriz ganha a DECLARACAO da perda aceita de
               `CEO_HOOK_ADAPTER` — ela nao e herdada, e o motivo fica escrito
               onde o proximo leitor procura;
     E6..E11   os OUTROS SEIS comentarios que apontavam para os steps
               deletados («step below», o BANNER do step de hooks,
               «dir-collected above», «split above» e as duas ocorrencias de
               «directory pins in the pytest steps above»). O rail codex r2
               achou a CLASSE que o E1 abriu e nao fechou; o censo mecanico
               esta nas POS-CONDICOES abaixo e no V6c do LAND.
   O delta de ambiente e DUPLO e os dois lados sao perdas ACEITAS e
   DECLARADAS (AC-16, S341): `PYTHONPATH: "."` so existe na matriz — a
   suite passava a rodar so COM ele; `CEO_HOOK_ADAPTER: claude` so existia
   no step A e NAO e adicionado a matriz, porque a matriz roda
   hooks+scripts+optimizer num unico pytest e sata-la ALTERARIA o ambiente
   de scripts/optimizer.

2. `.github/workflows/smoke-install.yml` — o bump diferido do
   `timeout-minutes` (126 -> 150) com a derivacao REESCRITA: o bloco de
   historia aditiva fica (e ledger), e um bloco novo registra as SETE
   amostras medidas de wall do job. Uma edicao (E5).

O que este script NAO faz, por desenho: nada de `fail-fast`, matriz,
composite action ou split de jobs — isso e a W4b.

Uso:
    python3 apply-w4a-validate-deletion.py --root <arvore-em-HEAD>
    python3 apply-w4a-validate-deletion.py --root <arvore> --check-only
    python3 apply-w4a-validate-deletion.py --list-paths

Saidas: 0 = aplicado (ou, com --check-only, aplicavel); 1 = recusa nomeada;
2 = erro de uso. Stdlib-only, Python >= 3.9, sem PEP 604 em runtime.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Tuple

VALIDATE_REL = ".github/workflows/validate.yml"
SMOKE_REL = ".github/workflows/smoke-install.yml"

# --------------------------------------------------------------------------
# (path, ancora EXATA, substituto, ocorrencias esperadas)
# A ordem e a ordem de aplicacao; cada ancora e contada ANTES de qualquer
# escrita (passo 1), entao um refuse deixa a arvore intocada.
# --------------------------------------------------------------------------
EDITS: List[Tuple[str, str, str, int]] = [
    # ------------------------------------------------------------------ E1
    # A nota de double-collection cita, pelo NOME, um step que E2/E3 apagam.
    # Trocar so o numero e deixar a prosa velha e a classe
    # `feedback-reconcile-the-conclusions-not-just-the-table`.
    (
        VALIDATE_REL,
        '      # is ALREADY collected by "Run Python script unit tests" below and\n'
        "      # by hook-tests-python-matrix — do NOT re-list them as paths.\n",
        "      # is ALREADY collected by the hook-tests-python-matrix job\n"
        "      # (PLAN-186 W4a) — do NOT re-list them as paths.\n",
        1,
    ),
    # ------------------------------------------------------------------ E2
    # Step A. A ancora inclui a linha em branco que o SEPARA do banner
    # seguinte: sem ela a delecao deixaria duas linhas em branco seguidas.
    (
        VALIDATE_REL,
        "      - name: Run Python hook unit tests (CEO_HOOK_ADAPTER=claude default)\n"
        "        env:\n"
        "          CEO_HOOK_ADAPTER: claude\n"
        "        run: |\n"
        "          set -euo pipefail\n"
        '          echo "Python version: $(python3 --version)"\n'
        '          cd "$GITHUB_WORKSPACE"\n'
        "          python3 -m pytest .claude/hooks/tests/ -n auto -m 'not serial' --strict-markers --tb=no -q\n"
        "          python3 -m pytest .claude/hooks/tests/ -m 'serial' --strict-markers --tb=no -q\n"
        "\n",
        "",
        1,
    ),
    # ------------------------------------------------------------------ E3
    # Step B mais o CORPO do banner dele e a regua de FECHAMENTO. A regua de
    # ABERTURA (a linha `# ---` imediatamente acima) fica e passa a abrir o
    # banner do step PLAN-152 seguinte — e por isso que a ancora comeca na
    # linha de titulo, e nao na regua.
    (
        VALIDATE_REL,
        "      # Step: Python script unit tests (audit-query, run-skill-benchmark,\n"
        "      # check-tier-boundaries)\n"
        "      # -----------------------------------------------------------------\n"
        "      - name: Run Python script unit tests\n"
        "        run: |\n"
        "          set -euo pipefail\n"
        '          cd "$GITHUB_WORKSPACE"\n'
        "          # PLAN-122 WS12 — optimizer (WS-1/WS-2) unit suite CI-gated.\n"
        "          python3 -m pytest .claude/scripts/tests/ .claude/scripts/optimizer/tests/ -n auto -m 'not serial' --strict-markers --tb=no -q\n"
        "          python3 -m pytest .claude/scripts/tests/ .claude/scripts/optimizer/tests/ -m 'serial' --strict-markers --tb=no -q\n"
        "\n"
        "      # -----------------------------------------------------------------\n",
        "",
        1,
    ),
    # ------------------------------------------------------------------ E4
    # A perda aceita de CEO_HOOK_ADAPTER escrita ONDE o proximo leitor
    # procura: no `env:` da matriz que passa a ser o unico consumidor.
    (
        VALIDATE_REL,
        "        env:\n"
        '          PYTHONPATH: "."\n'
        "        run: |\n",
        "        env:\n"
        '          PYTHONPATH: "."\n'
        "          # PLAN-186 W4a — NOT inherited (rail r17 P2): the deleted step A set\n"
        "          # CEO_HOOK_ADAPTER=claude for .claude/hooks/tests ONLY, while this matrix\n"
        "          # step runs hooks + scripts + optimizer in ONE pytest. Setting it here would\n"
        "          # ALTER the scripts/optimizer environment (they ran with it ABSENT in both\n"
        "          # the deleted step B and this matrix). The variable is the documented default\n"
        "          # of the adapter, so its absence exercises the default path — the same path\n"
        "          # step A exercised explicitly. Declared as the second ACCEPTED env delta.\n"
        "        run: |\n",
        1,
    ),
    # ------------------------------------------------------------- E6..E11
    # O rail codex r2 (P2) achou a CLASSE que o E1 abriu e nao fechou: o E1
    # reconciliou UM comentario, e o arquivo tinha SEIS que apontavam para os
    # steps deletados ("step below", "dir-collected above", "split above",
    # "directory pins in the pytest steps above", e o BANNER do step de hooks).
    # Rail acha a classe, censo MECANICO a fecha — o censo esta no EVIDENCE e
    # o gate esta no V6c do LAND, que reprova qualquer sobra.
    (
        VALIDATE_REL,
        '      # The instrument\'s own unit suite needs no step here: the "Run Python\n'
        '      # script unit tests" step below runs the whole `.claude/scripts/tests/`\n'
        "      # directory, so it is wired by membership — the same rule `:291-295`\n"
        '      # states for the Wave C tests ("do NOT re-list them as paths").\n',
        "      # The instrument's own unit suite needs no step here: the\n"
        "      # `hook-tests-python-matrix` job runs the whole `.claude/scripts/tests/`\n"
        "      # directory (PLAN-186 W4a), so it is wired by membership — the same\n"
        '      # rule the double-collection note above states for the Wave C tests\n'
        '      # ("do NOT re-list them as paths").\n',
        1,
    ),
    (
        VALIDATE_REL,
        "      # Step: Python hook unit tests (Sprint 2 A.4)\n"
        "      # Runs every test under .claude/hooks/tests/. Uses Python 3.12\n"
        "      # from setup-python (audit-v2 hot-fix: ubuntu-24.04 runner's\n"
        "      # default python3 ships without pytest; set up explicitly).\n",
        "      # Step: Python toolchain for the steps below (Sprint 2 A.4)\n"
        "      # PLAN-186 W4a deleted the hook/script unit-test steps this banner\n"
        "      # used to introduce; `hook-tests-python-matrix` runs those suites\n"
        "      # now, in 3.9 AND 3.12. What stays is the toolchain later steps of\n"
        "      # this job still use — MEASURED, not assumed: TWO of them INVOKE\n"
        "      # pytest (the PLAN-155 Wave 6 teeth and the PLAN-152 tests-01\n"
        "      # roots); the npm packlist gate uses the selected python3\n"
        "      # interpreter but NOT pytest. So: Python 3.12 from setup-python\n"
        "      # (audit-v2 hot-fix: the ubuntu-24.04 default python3 ships\n"
        "      # without pytest) plus pytest itself.\n"
        "      # NOT verified by this wave: whether anything still standing in\n"
        "      # this job needs PyYAML. The install below keeps bringing it, and\n"
        "      # its own comment names two tests that now run in the matrix; no\n"
        "      # later pytest ROOT imports yaml, and the two `import yaml`\n"
        "      # one-liners in this job run BEFORE this step. Dropping it is a\n"
        "      # functional change, so it is FLAGGED here, not guessed at.\n",
        1,
    ),
    (
        VALIDATE_REL,
        "      # Explicit positive-control paths (the plan asks for them even though\n"
        "      # hooks/tests/ is dir-collected above): the Stop-review gate + the\n"
        "      # advisory-teeth chain-scan, pinned green under BOTH adapters. Plus a\n",
        "      # Explicit positive-control paths (the plan asks for them even though\n"
        "      # hooks/tests/ is dir-collected by the hook-tests-python-matrix job —\n"
        "      # PLAN-186 W4a): the Stop-review gate + the advisory-teeth chain-scan,\n"
        "      # pinned green under BOTH adapters. Plus a\n",
        1,
    ),
    (
        VALIDATE_REL,
        "      # replicating the two-pass `not serial`/`serial` split above.\n",
        "      # replicating the two-pass `not serial`/`serial` split that the\n"
        "      # hook-tests-python-matrix job runs (PLAN-186 W4a).\n",
        1,
    ),
    (
        VALIDATE_REL,
        "      # collected by the EXISTING directory pins in the pytest steps\n"
        "      # above — deliberately NOT re-listed as explicit paths (debate C1\n",
        "      # collected by the EXISTING directory pins of the\n"
        "      # hook-tests-python-matrix job (PLAN-186 W4a) — deliberately NOT\n"
        "      # re-listed as explicit paths (debate C1\n",
        1,
    ),
    (
        VALIDATE_REL,
        "      # by the EXISTING directory pins in the pytest steps above —\n"
        "      # deliberately NOT re-listed as explicit paths (debate C1 in the\n",
        "      # by the EXISTING directory pins of the hook-tests-python-matrix job\n"
        "      # (PLAN-186 W4a) — deliberately NOT re-listed as explicit paths\n"
        "      # (debate C1 in the\n",
        1,
    ),
    # ------------------------------------------------------------------ E5
    # O bump diferido (Owner, 2026-09-01). O bloco de historia aditiva NAO e
    # tocado — ele e o ledger de como se chegou a 126. O bloco novo diz o que
    # a aritmetica nao dizia: as amostras MEDIDAS.
    (
        SMOKE_REL,
        "    # by exactly the PLAN-185 step — the `cancelled`-on-an-innocent-step\n"
        "    # class the doctrine above exists to prevent.\n"
        "    timeout-minutes: 126\n",
        "    # by exactly the PLAN-185 step — the `cancelled`-on-an-innocent-step\n"
        "    # class the doctrine above exists to prevent.\n"
        "    # PLAN-186 W4a (S343): 126 -> 150 — the first number in this block\n"
        "    # sized on MEASURED wall instead of on additive step arithmetic. Every\n"
        "    # block above composes per-step estimates; the samples below give an\n"
        "    # observed RANGE for this job, which the arithmetic never had. They do\n"
        "    # NOT say what causes the spread — see the note under the table.\n"
        "    # Instrument: wall of the JOB `smoke` (startedAt -> completedAt), which\n"
        "    # is what `timeout-minutes` gates. The RUN wall is 1-5 min longer and is\n"
        "    # NOT the right instrument — an earlier note in the project memory read\n"
        "    # `1h32` off a RUN, which is the same run measured as 92m32s here.\n"
        "    # Read with `gh run view <id> --json jobs`, seven most recent GREEN runs\n"
        "    # of this workflow, newest first (2026-09-03):\n"
        "    #   33809424817  92m32s   35f33a8\n"
        "    #   33743649231  90m40s   ba15c71\n"
        "    #   33630753302  77m53s   8efe09b\n"
        "    #   33582381725  87m50s   f0e98de\n"
        "    #   33503515412  86m52s   b7dad83\n"
        "    #   33388608651  86m44s   826688f\n"
        "    #   33364620284  73m18s   f348ee9\n"
        "    # min 73m18s, max 92m32s. What that establishes is the observed RANGE\n"
        "    # and nothing more: the seven runs share this workflow definition but\n"
        "    # NOT the executed workload — 826688f changed\n"
        "    # scripts/tests/smoke-install.sh; ba15c71 changed scripts/doctor.sh and\n"
        "    # the installer write-safety e2e; this job invokes all of them.\n"
        "    # Attributing the spread to the RUNNER would need repeated runs at ONE\n"
        "    # sha, which nobody has done. So this block sizes on the observed\n"
        "    # maximum and claims no cause. (The runner-variance class is real in\n"
        "    # this repo — S327: the hook-latency gate measured 77 ms locally and\n"
        "    # 209-435 ms in CI on the SAME sha — but that is a precedent, not\n"
        "    # evidence about these seven numbers.)\n"
        "    # 126 leaves 33m28s over the observed max (1.36x); 150 leaves 57m28s\n"
        "    # (1.62x). The house rule fires below 20% headroom and 126 was still\n"
        "    # ABOVE it at 26.6% — so the trigger that fired is not that one. The\n"
        "    # S336 deferral (Owner, 2026-09-01) named three, and this is the third:\n"
        "    # the next wave that already touches `.github/workflows/` takes the bump\n"
        "    # along at ~zero marginal cost. That wave is PLAN-186 W4a.\n"
        "    # What is deliberately NOT claimed: this is not a prediction that the\n"
        "    # job will take 150 minutes, and the W4a deletion riding in the same\n"
        "    # patch touches `validate.yml`, not this job — no number here is\n"
        "    # adjusted for it. Re-tighten on a real CI p95 with >= 3 further\n"
        "    # samples, never on arithmetic (AGENTS.md:9-11: this file records\n"
        "    # measurements and subtractions, never speed claims).\n"
        "    timeout-minutes: 150\n",
        1,
    ),
]

# Contagens DECLARADAS. Um numero aqui e uma afirmacao sobre a arvore
# POS-patch, verificada por `_postconditions` — nao um comentario.
POST_ABSENT = [
    (VALIDATE_REL, "- name: Run Python hook unit tests", 0),
    (VALIDATE_REL, "- name: Run Python script unit tests", 0),
    (VALIDATE_REL, "CEO_HOOK_ADAPTER: claude\n", 0),
    (SMOKE_REL, "timeout-minutes: 126", 0),
    # A CLASSE que o rail codex r2 achou: nenhum comentario pode continuar
    # apontando para os steps deletados. Estes literais sao o CENSO fechado —
    # `grep -icE` sobre o arquivo pos-patch devolve 0 para cada um.
    (VALIDATE_REL, "step below runs the whole", 0),
    (VALIDATE_REL, "is dir-collected above", 0),
    (VALIDATE_REL, "`serial` split above", 0),
    (VALIDATE_REL, "directory pins in the pytest steps", 0),
    (VALIDATE_REL, "Step: Python hook unit tests", 0),
]
POST_PRESENT = [
    (VALIDATE_REL, "hook-tests-python-matrix:", 1),
    (VALIDATE_REL, '          PYTHONPATH: "."\n', 1),
    (VALIDATE_REL, "PLAN-186 W4a — NOT inherited", 1),
    (SMOKE_REL, "    timeout-minutes: 150\n", 1),
    (SMOKE_REL, "PLAN-186 W4a (S343): 126 -> 150", 1),
    # E o contrapositivo: cada sitio reconciliado NOMEIA o job que passou a ser
    # o dono da cobertura. 8 = a linha que DEFINE o job + os 7 comentarios
    # (E1 + E6..E11). O numero foi MEDIDO, nao somado de cabeca: a primeira
    # redacao dizia 7 — esqueceu a propria definicao do job — e foi a
    # pos-condicao que reprovou. Em HEAD sao 2 (definicao + a mencao original
    # da nota de double-collection).
    (VALIDATE_REL, "hook-tests-python-matrix", 8),
]


def paths() -> List[str]:
    seen = []
    for rel, _a, _b, _n in EDITS:
        if rel not in seen:
            seen.append(rel)
    return sorted(seen)


def _postconditions(root: Path) -> List[str]:
    problems = []
    for rel, needle, want in POST_ABSENT + POST_PRESENT:
        text = (root / rel).read_text(encoding="utf-8")
        got = text.count(needle)
        if got != want:
            problems.append(
                "pos-condicao FALHOU em %s: %r aparece %d vez(es), esperado %d"
                % (rel, needle[:60], got, want))
    return problems


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", help="raiz da arvore em HEAD a patchar")
    ap.add_argument("--check-only", action="store_true",
                    help="so conta as ancoras; nao escreve nada")
    ap.add_argument("--list-paths", action="store_true",
                    help="lista os paths tocados, um por linha, e sai")
    args = ap.parse_args(argv)

    if args.list_paths:
        for rel in paths():
            print(rel)
        return 0
    if not args.root:
        sys.stderr.write("--root e obrigatorio (ou use --list-paths)\n")
        return 2

    root = Path(args.root).resolve()
    if not (root / ".git").exists():
        sys.stderr.write("RECUSA: %s nao parece uma arvore git\n" % root)
        return 1

    # ---------------- passo 1: contar TODAS as ancoras, sem escrever -------
    cache = {}
    for rel in paths():
        p = root / rel
        if not p.is_file():
            sys.stderr.write("RECUSA: path ausente na arvore: %s\n" % rel)
            return 1
        cache[rel] = p.read_text(encoding="utf-8")

    for idx, (rel, anchor, _new, want) in enumerate(EDITS, start=1):
        got = cache[rel].count(anchor)
        if got != want:
            sys.stderr.write(
                "RECUSA na edicao E%d (%s): a ancora aparece %d vez(es), "
                "esperado %d.\n" % (idx, rel, got, want))
            sys.stderr.write("  Primeira linha da ancora: %r\n"
                             % anchor.splitlines()[0][:100])
            sys.stderr.write(
                "  0 pode significar HEAD JA patchado, ou HEAD andou e a\n"
                "  ancora envelheceu; >1 significa ancora ambigua. Nos dois\n"
                "  casos a decisao e do CEO — este script nao adivinha.\n")
            return 1

    if args.check_only:
        print("check-only: %d edicao(oes) aplicaveis em %d path(s)"
              % (len(EDITS), len(paths())))
        return 0

    # ---------------- passo 2: aplicar em memoria --------------------------
    original = dict(cache)
    for rel, anchor, new, want in EDITS:
        cache[rel] = cache[rel].replace(anchor, new, want)

    # ---------------- passo 3: escrever ------------------------------------
    # O conteudo ORIGINAL fica guardado: uma pos-condicao que reprova DEPOIS
    # da escrita deixaria a arvore mutada por um script que RECUSOU — e a
    # proxima execucao veria as ancoras ja aplicadas e recusaria por outro
    # motivo. Refuse tem de ser transacional.
    # Rail codex do land (r2, P2): a garantia transacional so vale se a
    # EXCECAO tambem for coberta. Sem este `try`, uma falha ao escrever o
    # SEGUNDO path (permissao, disco cheio, arquivo somente-leitura) deixaria o
    # PRIMEIRO ja sobrescrito, e nem as pos-condicoes nem o rollback abaixo
    # seriam alcancados: a arvore ficaria meio-aplicada, exatamente o estado
    # que este bloco existe para impedir. `written` guarda o que ja foi
    # escrito, para restaurar so o que mudou.
    #
    # r3, P2: o path entra em `written` ANTES da escrita, nao depois. Uma
    # `write_text` que TRUNCA e so entao levanta (disco cheio e o caso classico)
    # deixaria o arquivo mutilado FORA da lista, e o handler restauraria so os
    # anteriores enquanto anunciava "a arvore foi RESTAURADA" — uma mentira pior
    # que o defeito. Restaurar um path que nao chegou a mudar e inofensivo:
    # reescreve os mesmos bytes.
    written = []
    try:
        for rel in paths():
            written.append(rel)
            (root / rel).write_text(cache[rel], encoding="utf-8")
    except OSError as exc:
        for rel in written:
            try:
                (root / rel).write_text(original[rel], encoding="utf-8")
            except OSError as rexc:
                # Restaurar falhou. Isso ainda NAO e um desastre: o path pode
                # ser justamente aquele cuja ABERTURA falhou (somente-leitura),
                # e nesse caso ele nunca mudou. A diferenca e observavel — leia
                # os bytes e compare. So se eles DIVERGIREM a arvore esta
                # mesmo meio-aplicada; anunciar isso sem olhar seria um alarme
                # falso, e nao anunciar seria a mentira que o r3 apontou.
                try:
                    still = (root / rel).read_text(encoding="utf-8")
                except OSError:
                    still = None
                if still == original[rel]:
                    continue
                sys.stderr.write(
                    "FALHA AO RESTAURAR %s: %s\n"
                    "  Os bytes deste arquivo DIVERGEM do original: a arvore ficou\n"
                    "  MEIO-APLICADA. Restaure com:\n"
                    "    git -C <root> restore --staged --worktree -- %s\n"
                    % (rel, rexc, " ".join(paths())))
                return 2
        sys.stderr.write("RECUSA: falha ao escrever: %s\n" % exc)
        sys.stderr.write("  (a arvore foi RESTAURADA ao estado pre-escrita)\n")
        return 1

    # ---------------- passo 4: pos-condicoes -------------------------------
    problems = _postconditions(root)
    if problems:
        for rel in paths():
            (root / rel).write_text(original[rel], encoding="utf-8")
        for p in problems:
            sys.stderr.write("RECUSA: %s\n" % p)
        sys.stderr.write("  (a arvore foi RESTAURADA ao estado pre-escrita)\n")
        return 1

    print("aplicado: %d edicao(oes) em %d path(s)" % (len(EDITS), len(paths())))
    for rel in paths():
        print("  %s" % rel)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
