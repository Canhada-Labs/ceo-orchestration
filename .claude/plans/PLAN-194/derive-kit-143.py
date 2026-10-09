#!/usr/bin/env python3
"""Deriva o kit de corte da v1.4.3-rc.1 (PLAN-194 W7) do kit que cortou a v1.4.2-rc.1.

  python3 .claude/plans/PLAN-194/derive-kit-143.py [--check] [--provisional]

Fontes (sha256 PINADO abaixo — uma fonte que mudou e recusa nomeada, nunca uma
derivacao silenciosa sobre outro texto), todas em .claude/plans/PLAN-193/: as saidas de
derive-kit-142.py que cortaram a v1.4.2-rc.1.

  repass-rc1/run-rc1-repass.sh   repass-rc1/probe-conditions-rc1.py
  repass-rc1/CONDITIONS-rc1.md   repass-rc1/README-rc1.md   repass-rc1/.gitignore
  gen-envelope-rc1.py            OWNER-RC1-CUT.sh            test-rc1-kit.sh

Conferidos, nunca executados (sha256 pinados): derive-kit-142.py (o derivador daquele kit:
tem de seguir derivando as fontes acima) e o kit do GA v1.4.2 — derive-ga-kit-142.py,
OWNER-GA-CUT.sh, repass-ga/run-ga-repass.sh, gen-envelope-ga.py e test-ga-kit.sh —, cujas
curas posteriores ao kit da rc.1 este carrega: a classe de morte do LIMITE DE USO da conta
Codex separada da capacidade do modelo (runner, passo 6 e harness), os `grep -c` com o rc
guardado, o relatorio da sonda conferido pelo gerador (PROBE_IDS, MAPA, `--only` com id
desconhecido recusado) e o envelope re-derivado dos fields assinados no passo 11. Cada
cura carregada e conferida por MARCADOR no texto do GA antes de derivar.

Saidas, todas em .claude/plans/PLAN-194/:

  repass-rc1/run-rc1-repass.sh      runner das 4 partes. Codex pela ROTA 1 SO (PLAN-194
                                    D-4): o binario global, quando o oraculo ADR-182 confere o
                                    payload e ele responde a versao do manifesto; a rota 2
                                    (npx num cache proprio, que EXECUTAVA antes de verificar) e
                                    RECUSA NOMEADA — nada e baixado nem executado
  repass-rc1/probe-conditions-rc1.py a sonda das condicoes da 1.4.3, contra um commit
  repass-rc1/CONDITIONS-rc1.md      as condicoes, pela FORMA, com a divida re-declarada
  repass-rc1/README-rc1.md          escopo, o que fica fora, criterio de parada
  repass-rc1/.gitignore             arquivos de trabalho do runner
  gen-envelope-rc1.py               gerador de fields + envelope (relatorio da sonda conferido)
  OWNER-RC1-CUT.sh                  corte em 20 passos; o passo 18 exige `success` no job do
                                    gate («Await release-gate») E no job da prova do toolchain
                                    da rc da W4 («RC toolchain proof (no publish)»), PELO NOME;
                                    o G0 recusa pelo nome um HEAD sem esse job e um `.gen-*.tmp`
                                    orfao de um gerador morto (com a rota)
  test-rc1-kit.sh                   harness com chave GPG descartavel e stubs. Numa arvore SEM
                                    as outras sete saidas (o estado do K1: o derivador landa
                                    antes delas) ele deriva o kit num CLONE descartavel e
                                    re-executa a si mesmo la — o derivado tem de ser byte a byte
                                    o arquivo que rodou

Ordem de cada derivacao: primeiro o DESLOCAMENTO de versao da fonte (`shift`: 1.4.2 -> 1.4.3,
1.4.1 -> 1.4.2, PLAN-193 -> PLAN-194, PLAN-192 -> PLAN-193, derive-kit-142 -> derive-kit-143,
relmeta-142 -> relmeta-143), numa passada so (nada desloca duas vezes), com os literais de
HISTORIA protegidos por arquivo (o que aconteceu num corte anterior continua dizendo o corte
anterior); depois as edicoes por ANCORA EXATA, escritas contra o texto JA deslocado (`sub` exige
a contagem declarada; `cut_region` exige o INICIO unico e o FIM e a primeira ocorrencia depois
dele). A sonda e as condicoes da 1.4.3 sao montadas: auxiliares VERBATIM da sonda da v1.4.2-rc.1
(por `region`) + as verificacoes desta release. Os blocos que o kit do GA v1.4.2 curou depois do
kit da rc.1 entram por marcador conferido (runner, corte, gerador) ou TRANSPLANTADOS do harness
do GA com o renome ga -> rc1 (secoes F e B2/B2u/B2x). Os `! grep` de ausencia do harness viram
`lacks` (R3H-01) na ultima passada.

Conteudo da release: as condicoes, o README, a particao, a cobertura e o CONTEXT do prompt da
1.4.3 sao PROVISORIOS nesta derivacao (RELEASE_CONTENT abaixo): verdadeiros contra o HEAD do K1
com a W4 projetada, e a derivacao final (KIT, PLAN-194 W7) os completa com o que landar ate la.
Escrever as saidas com o conteudo provisorio exige `--provisional` (o harness passa a flag no
clone descartavel); sem ela e recusa nomeada. `--check` re-deriva em memoria e compara byte a
byte com o disco (rc 1 em qualquer diferenca).

Fatos conferidos aqui, no HEAD, ao derivar (recusa nomeada se um nao vale): o job da rc da W4
(«RC toolchain proof (no publish)», id `rc-toolchain-proof`) existe no npm-publish.yml do HEAD
com `if: contains(github.ref, '-rc.')`; o manifesto ADR-182 pina o codex 0.160.0; a tag base
v1.4.2 existe; e as janelas de cron que o corte cita durante o freeze. stdlib only, Python >= 3.9.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys
from typing import Dict, List, Optional, Sequence, Tuple

REPO = pathlib.Path(subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"], universal_newlines=True).strip())
SRC_PLAN = ".claude/plans/PLAN-193"
DST_PLAN = ".claude/plans/PLAN-194"

SOURCES = {
    "runner": (SRC_PLAN + "/repass-rc1/run-rc1-repass.sh",
               "6c02b1a71b69943d08dcdbd4f8db3e3ddf0c289c3af1ddcea05198764362c5e0"),
    "probe": (SRC_PLAN + "/repass-rc1/probe-conditions-rc1.py",
              "4379de623eab25f305e5852c659ca5a57991af18cfe5610cb94117032a56c519"),
    "cond": (SRC_PLAN + "/repass-rc1/CONDITIONS-rc1.md",
             "939918694f1bc1495bd0953065fde18a208b446befaa1435410cbf0cc7fc2e2f"),
    "readme": (SRC_PLAN + "/repass-rc1/README-rc1.md",
               "f11dd88a44d1dc22c8c3ddec6740b924b36d62089ef3cf3a87e9fda46efae13d"),
    "gitignore": (SRC_PLAN + "/repass-rc1/.gitignore",
                  "0645b9a82ad7e6156e8a384c1bfa967264855427169a00e5ebef8212340290d6"),
    "gen": (SRC_PLAN + "/gen-envelope-rc1.py",
            "a85ba0436541292ead10d7cde6e2532a0fe961055fa3db424a16d5be3b91271c"),
    "cut": (SRC_PLAN + "/OWNER-RC1-CUT.sh",
            "772c3db4c028e01dbd361688b203dfc498b403918f4437b29d71fb255aff08c3"),
    "test": (SRC_PLAN + "/test-rc1-kit.sh",
             "210618bceb2da73368d667370a5b07cf69b1d63f0b6ca0c80678e7df115f2507"),
}
# Conferidas, nunca executadas: o derivador da v1.4.2-rc.1 (as fontes acima tem de ser as
# saidas dele) e o kit do GA v1.4.2 (as curas que este kit carrega, por marcador). Os dois
# cortaram releases publicadas e nao mudam mais.
DERIVE142 = (SRC_PLAN + "/derive-kit-142.py",
             "7ede76f66ca9cde30f6b1b171b88677f6b3be2f2b802a39135a1b827a3928f29")
GA142 = {
    "derive": (SRC_PLAN + "/derive-ga-kit-142.py",
               "27348f8001d8538036eab61d11c92d3b407add4758a13f5ea53a829352a69f49"),
    "cut": (SRC_PLAN + "/OWNER-GA-CUT.sh",
            "cbbe2f449e508354716a01a4b85b0837b19873f838d4234d38fad5fbaa2f7d81"),
    "runner": (SRC_PLAN + "/repass-ga/run-ga-repass.sh",
               "0b9b4703a766234a9ae9af61c29d95b5759f0c0c60dbe607d848426fe50802ec"),
    "gen": (SRC_PLAN + "/gen-envelope-ga.py",
            "f75212ce6a2e6c5c4584ac4d9515aec90db3bcbde42aa80c462b1c26d194f635"),
    "test": (SRC_PLAN + "/test-ga-kit.sh",
             "fd87a14dbcd8cb284c6584adfb3dabc8f4c1495238406e5ecc0083aa3c3601bd"),
}
OUTPUTS = {
    "runner": DST_PLAN + "/repass-rc1/run-rc1-repass.sh",
    "probe": DST_PLAN + "/repass-rc1/probe-conditions-rc1.py",
    "cond": DST_PLAN + "/repass-rc1/CONDITIONS-rc1.md",
    "readme": DST_PLAN + "/repass-rc1/README-rc1.md",
    "gitignore": DST_PLAN + "/repass-rc1/.gitignore",
    "gen": DST_PLAN + "/gen-envelope-rc1.py",
    "cut": DST_PLAN + "/OWNER-RC1-CUT.sh",
    "test": DST_PLAN + "/test-rc1-kit.sh",
}
ORDER = ("runner", "probe", "cond", "readme", "gitignore", "gen", "cut", "test")
MODES = {k: 0o644 for k in ORDER}

TAG = "v1.4.3-rc.1"
BASE = "1.4.3"
BASE_TAG = "v1.4.2"
NPARTS = 4
CODEX_PIN = "0.160.0"
PLAN_FILE = ".claude/plans/PLAN-194-maintenance-train-v1-4-3.md"
# O job da rc que a W4 do PLAN-194 acrescenta ao npm-publish.yml (medido na sombra da W4 em
# 2026-10-08: commits dbf2d7ef/4672153e). O passo 18 exige `success` nele PELO NOME (o `name:`
# que `gh run view --json jobs` devolve), e o derivador recusa pelo nome um HEAD sem ele.
RC_PROOF_JOB_ID = "rc-toolchain-proof"
RC_PROOF_JOB_NAME = "RC toolchain proof (no publish)"
NPM_PUBLISH_WF = ".github/workflows/npm-publish.yml"
# O conteudo da release (condicoes, README, particao, cobertura, CONTEXT do prompt): "provisorio-K1"
# ate a derivacao final do KIT, que o completa e troca este valor para "final".
RELEASE_CONTENT = "provisorio-K1"
PROVISIONAL_MARK = "CONTEÚDO PROVISÓRIO (derivação K1)"


def die(msg: str) -> None:
    sys.stderr.write("derive-kit-143: FATAL: %s\n" % msg)
    raise SystemExit(2)


def _load(rel: str, want: str) -> str:
    p = REPO / rel
    if p.is_symlink() or not p.is_file():
        die("fonte ausente ou nao-regular: %s" % rel)
    raw = p.read_bytes()
    got = hashlib.sha256(raw).hexdigest()
    if got != want:
        die("fonte %s mudou (sha256 %s, pinado %s) — revise as ancoras antes de re-pinar"
            % (rel, got, want))
    return raw.decode("utf-8")


def load(kind: str) -> str:
    return _load(*SOURCES[kind])


def ga(kind: str) -> str:
    return _load(*GA142[kind])


def sub(text: str, old: str, new: str, what: str, n: int = 1) -> str:
    c = text.count(old)
    if c != n:
        die("ancora %r casou %d vez(es) (exigido: %d)" % (what, c, n))
    return text.replace(old, new)


def cut_region(text: str, start: str, end: Optional[str], new: str, what: str) -> str:
    """Troca [start, end) por `new`; `end` e preservado. `end` = None: ate o fim.

    `start` tem de casar exatamente uma vez; `end` e a PRIMEIRA ocorrencia depois de
    `start` (ausente e FATAL), como nos moldes."""
    if text.count(start) != 1:
        die("ancora inicial %r casou %d vez(es)" % (what, text.count(start)))
    i = text.index(start)
    if end is None:
        return text[:i] + new
    j = text.find(end, i + len(start))
    if j < 0:
        die("ancora final de %r ausente" % what)
    return text[:i] + new + text[j:]


def region(text: str, start: str, end: str, what: str) -> str:
    """Devolve [start, end) sem editar (mesma contagem de cut_region)."""
    if text.count(start) != 1:
        die("ancora inicial %r casou %d vez(es)" % (what, text.count(start)))
    i = text.index(start)
    j = text.find(end, i + len(start))
    if j < 0:
        die("ancora final de %r ausente" % what)
    return text[i:j]


def forbid(text: str, what: str, needles: Sequence[str]) -> None:
    for s in needles:
        if s in text:
            die("%s derivado ainda carrega %r" % (what, s))


def need(text: str, what: str, needles: Sequence[str]) -> None:
    for s in needles:
        if s not in text:
            die("%s derivado sem %r" % (what, s))


def git(*args: str) -> str:
    return subprocess.check_output(["git", "-C", str(REPO)] + list(args),
                                   universal_newlines=True)


# Deslocamento de versao, numa passada so (alternancia, o mais longo primeiro): nada e
# deslocado duas vezes. `protect` = literais de HISTORIA da fonte, que nao se deslocam.
SHIFT = [
    ("derive-kit-142", "derive-kit-143"),
    ("relmeta-142", "relmeta-143"),
    ("PLAN-193", "PLAN-194"),
    ("PLAN-192", "PLAN-193"),
    ("1.4.2", "1.4.3"),
    ("1.4.1", "1.4.2"),
]
_SHIFT_RE = re.compile("|".join(re.escape(o) for o, _n in sorted(SHIFT, key=lambda p: -len(p[0]))))
_SHIFT_MAP = dict(SHIFT)
PROTECT_PH = "\x00K1PROTECT%d\x00"


def shift(text: str, what: str, protect: Sequence[Tuple[str, int]] = ()) -> str:
    """Desloca as versoes; cada literal de `protect` tem de casar a contagem declarada."""
    if "\x00" in text:
        die("%s: byte NUL na fonte (o placeholder de protecao colidiria)" % what)
    for i, (lit, n) in enumerate(protect):
        if text.count(lit) != n:
            die("%s: literal protegido %r casou %d vez(es) (exigido: %d)"
                % (what, lit, text.count(lit), n))
        text = text.replace(lit, PROTECT_PH % i)
    text = _SHIFT_RE.sub(lambda m: _SHIFT_MAP[m.group(0)], text)
    for i, (lit, _n) in enumerate(protect):
        text = text.replace(PROTECT_PH % i, lit)
    return text


# ===========================================================================
# proveniencia: o kit de origem e o kit do GA v1.4.2 cujas curas este carrega
# ===========================================================================
GA_CURE_MARKERS = {
    "runner": [
        "CODEX_ACCOUNT_LIMIT_RE='hit your usage limit|reached your usage limit|Usage limit reached|Quota exceeded|out of credits'",
        "codex_error_tail() {", "codex_account_limit() {", "codex_capacity_death() {",
        "codex_quota_seen() {", '"$OUT"/.codex-quota-*',
        "_rhrc=0; RH=$(grep -c '^@@' \"$RAW\") || _rhrc=$?",
        '_mnrc=0; _mn="$(grep -c . "$MAN")" || _mnrc=$?',
    ],
    "cut": [
        "(c) Caso particular de (b), com rota propria: a parte morreu pelo LIMITE DE USO DA",
        "unset OPENAI_API_KEY",
        "# O envelope RE-DERIVADO dos fields assinados, depois dos guards de HEAD e do index",
    ],
    "gen": [
        'PROBE_GREEN_TAIL = "SONDA: 0 FALSA(S), 0 sem medida"',
        "def probe_refuse(why: str) -> None:", "def probe_green(prov: str, cand: str) -> None:",
        'PROBE_MAP_PREFIX = "MAPA condicao -> ids: "',
    ],
    "test": [
        'say "B2u. LIMITE DE USO da CONTA codex',
        'say "B2x. morte SEM classe no fim do transcript',
        "# Os ids das verificacoes da sonda: o gerador os pina (PROBE_IDS)",
    ],
}


def verify_references() -> None:
    d142 = _load(*DERIVE142)
    for kind in ORDER:
        tail = SOURCES[kind][0].split(SRC_PLAN + "/", 1)[1]
        if ('DST_PLAN + "/%s"' % tail) not in d142:
            die("derive-kit-142.py nao deriva mais %s — a fonte nao e a saida dele" % tail)
    for kind, marks in GA_CURE_MARKERS.items():
        text = ga(kind)
        for m in marks:
            if m not in text:
                die("kit do GA v1.4.2 (%s) sem o marcador %r — a referencia das curas mudou"
                    % (GA142[kind][0], m))
    if "def verify_facts() -> None:" not in ga("derive"):
        die("derive-ga-kit-142.py sem verify_facts")


# ===========================================================================
# fatos do HEAD que o texto do kit afirma
# ===========================================================================
# As janelas de cron que o OWNER-RC1-CUT.sh cita durante o freeze (as mesmas da 1.4.2;
# re-medidas no HEAD a953a082 em 2026-10-08).
CRONS_DAILY = ["06:43", "07:00", "07:37", "11:00"]
CRONS_MONDAY_N = 10
CRONS_MONDAY_SPAN = ("03:00", "19:23")
CRONS_MONTH_DAY1 = ["04:00", "07:00"]


def probe_crons() -> None:
    daily, monday, day1, other = [], [], [], []
    for wf in sorted((REPO / ".github" / "workflows").glob("*.yml")):
        for m in re.finditer(r"""(?m)^\s*-\s*cron:\s*["']([^"']+)["']""", wf.read_text(encoding="utf-8")):
            f = m.group(1).split()
            if len(f) != 5 or not (f[0].isdigit() and f[1].isdigit()):
                other.append("%s:%s" % (wf.name, m.group(1)))
                continue
            hm = "%02d:%02d" % (int(f[1]), int(f[0]))
            tail = tuple(f[2:])
            if tail == ("*", "*", "*"):
                daily.append(hm)
            elif tail == ("*", "*", "1"):
                monday.append(hm)
            elif tail == ("1", "*", "*"):
                day1.append(hm)
            else:
                other.append("%s:%s" % (wf.name, m.group(1)))
    if other:
        die("sonda crons: cron fora das tres formas que o OWNER-RC1-CUT.sh descreve: %s" % ", ".join(other))
    if sorted(daily) != CRONS_DAILY or sorted(day1) != CRONS_MONTH_DAY1:
        die("sonda crons: diarios %s / dia 1 %s (o texto do corte diz %s / %s)"
            % (sorted(daily), sorted(day1), CRONS_DAILY, CRONS_MONTH_DAY1))
    if len(monday) != CRONS_MONDAY_N or (min(monday), max(monday)) != CRONS_MONDAY_SPAN:
        die("sonda crons: %d crons de segunda entre %s (o texto do corte diz %d entre %s)"
            % (len(monday), (min(monday), max(monday)) if monday else None, CRONS_MONDAY_N,
               CRONS_MONDAY_SPAN))


def _show_head(rel: str) -> Optional[str]:
    p = subprocess.run(["git", "-C", str(REPO), "show", "HEAD:%s" % rel],
                       stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    if p.returncode != 0:
        return None
    return p.stdout.decode("utf-8", "surrogateescape")


def rc_proof_job_block(wf: str) -> Optional[str]:
    """O bloco do job `rc-toolchain-proof:` (indentado 2 espacos sob `jobs:`), ou None."""
    m = re.search(r"(?m)^  %s:[ \t]*\n" % re.escape(RC_PROOF_JOB_ID), wf)
    if not m:
        return None
    rest = wf[m.end():]
    nxt = re.search(r"(?m)^  [A-Za-z0-9_-]+:[ \t]*$|^[^ \t\n#]", rest)
    return wf[m.start():m.end() + (nxt.start() if nxt else len(rest))]


def verify_head_facts() -> None:
    wf = _show_head(NPM_PUBLISH_WF)
    if wf is None:
        die("%s ausente no HEAD" % NPM_PUBLISH_WF)
    blk = rc_proof_job_block(wf)
    names = re.findall(r"(?m)^    name:[ \t]*(.+?)[ \t]*$", blk or "")
    ifs = re.findall(r"(?m)^    if:[ \t]*(.+?)[ \t]*$", blk or "")
    if blk is None or names != [RC_PROOF_JOB_NAME] or ifs != ["contains(github.ref, '-rc.')"]:
        die("o job «%s» (id %s, com if: contains(github.ref, '-rc.')) nao existe no %s do HEAD "
            "(%s): a W4 do PLAN-194 ainda nao landou, e o passo 18 do corte exige success nele "
            "pelo nome. Lande a W4 antes de derivar o kit (o harness do K1 a PROJETA num clone "
            "descartavel)." % (RC_PROOF_JOB_NAME, RC_PROOF_JOB_ID, NPM_PUBLISH_WF,
                               git("rev-parse", "--short", "HEAD").strip()))
    man = _show_head(".claude/governance/codex-cli-pin-manifest.json")
    try:
        ver = json.loads(man or "{}").get("package_version")
    except ValueError:
        ver = None
    if ver != CODEX_PIN:
        die("o manifesto ADR-182 do HEAD pina %r; este kit diz %s (re-pin sem re-derivar?)"
            % (ver, CODEX_PIN))
    tg = subprocess.run(["git", "-C", str(REPO), "rev-parse", "-q", "--verify",
                         "refs/tags/%s^{commit}" % BASE_TAG],
                        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    if tg.returncode != 0:
        die("a tag base %s nao existe neste repositorio (git fetch origin tag %s)" % (BASE_TAG, BASE_TAG))
    if _show_head(PLAN_FILE) is None:
        die("o plano %s nao existe no HEAD" % PLAN_FILE)


# ===========================================================================
# runner
# ===========================================================================
RUNNER_HEADER = r'''#!/bin/bash
# CEREMONY-LINT: handwritten-exception: DERIVADO por .claude/plans/PLAN-194/derive-kit-143.py
# do runner da v1.4.2-rc.1 (PLAN-193/repass-rc1/run-rc1-repass.sh; fonte e sha256 em
# SOURCES, no derivador), com as curas do runner do GA v1.4.2; nao ha gerador compartilhado
# para runners de re-pass. NAO edite a mao: edite o derivador e rode-o.
# Re-pass do CANDIDATO v1.4.3-rc.1 (PLAN-194) - 4 PARTES.
#
# Revisa o delta v1.4.2..CANDIDATO na ordem de RISCO PARA O ADOTANTE:
#   1 instalacao, upgrade, settings e o pipeline de release (templates, install/upgrade,
#     o pin e o piso VETO efetivos, .github/ - o validate.yml e o npm-publish.yml com o
#     job da prova do toolchain da rc -, o texto de release e os sitios de versao do bump)
#   2 os hooks que rodam na sessao do adopter (.claude/hooks/ fora dos testes e dos dois
#     arquivos da parte 1)
#   3 as CLIs do mantenedor e do operador, os comandos e as skills
#   4 a documentacao entregue (docs/ fora de docs/research/)
# Todo caminho que muda na faixa esta em exatamente uma parte ou numa classe declarada
# FORA (out_of_scope_pathspec); a sonda das condicoes confere isso antes do codex.
#
'''

RUNNER_CODEXDOC_START = "# CODEX PINADO SEM MEXER NA MAQUINA. A versao revisora e a que\n"
RUNNER_CODEXDOC_END = "# ---------------------------------------------------------------------------\nset -uo pipefail\n"
RUNNER_CODEXDOC = r'''# CODEX PINADO SEM MEXER NA MAQUINA. A versao revisora e a que
# `.claude/governance/codex-cli-pin-manifest.json` pina NO MOMENTO do run (os
# dois arquivos de pin sao canonicos e NAO sao editados aqui). UMA rota nesta release
# (PLAN-194 D-4): o binario GLOBAL, quando o oraculo do pair-rail-gate
# (`check_pair_rail.py --verify-codex-pin`, fail-CLOSED) confere o sha256 do payload nativo
# contra o manifesto SEM executa-lo, e so entao ele responde a versao pinada. A rota 2 da
# v1.4.2 (`npx` num cache PROPRIO) EXECUTAVA o pacote baixado antes de qualquer verificacao:
# aqui ela e RECUSA NOMEADA — nada e baixado nem executado, e a recusa diz a rota (o codex
# pinado instalado globalmente). Um diretorio-shim no inicio do PATH garante que qualquer
# `codex` invocado durante o run seja o verificado. A PROVENANCE registra a rota, o modelo
# (-m, com a origem) e as mortes do codex re-tentadas.
# MORTES do codex (cura do GA v1.4.2): classificadas SO pelas linhas ERROR: do proprio codex
# no fim do transcript. Capacidade do modelo: re-tentada ate 2 vezes. LIMITE DE USO/quota da
# CONTA Codex: NUNCA re-tentado, nenhuma parte nova lancada, declarado na PROVENANCE (com a
# hora de reset, se o codex a imprimir) e o run termina em recusa nomeada.
'''

RUNNER_BASE_OLD = ('# A tag base NAO e pinada por objeto neste runner: ela e cortada na mesma manha, depois\n'
                   '# da derivacao do kit. O passo 1 a RESOLVE (tag anotada; assinatura verificada, por um\n')
RUNNER_BASE_NEW = ('# A tag base NAO e pinada por objeto neste runner (o GA v1.4.2 foi cortado em 2026-09-30;\n'
                   '# vale o objeto do momento do run). O passo 1 a RESOLVE (tag anotada; assinatura verificada, por um\n')

RUNNER_ATTEMPT_OLD = '           "$OUT"/paths-rc1-*.manifest.txt.tmp "$OUT"/.codex-rc-* "$OUT"/.codex-dead-* \\\n'
RUNNER_ATTEMPT_NEW = '           "$OUT"/paths-rc1-*.manifest.txt.tmp "$OUT"/.codex-rc-* "$OUT"/.codex-dead-* "$OUT"/.codex-quota-* \\\n'

RUNNER_STEP1_OLD = "# A base e a tag do GA v1.4.2, cortada na manha do corte: resolvida aqui, recusada pelo\n"
RUNNER_STEP1_NEW = "# A base e a tag do GA v1.4.2 (cortado em 2026-09-30): resolvida aqui, recusada pelo\n"
RUNNER_BASEDIE_OLD = ('  || die "a tag base $BASE_TAG nao existe neste repositorio: o GA v1.4.2 ainda nao foi '
                      'cortado (.claude/plans/PLAN-193/OWNER-GA-CUT.sh), ou falta: git fetch origin tag $BASE_TAG"\n')
RUNNER_BASEDIE_NEW = ('  || die "a tag base $BASE_TAG nao existe neste repositorio: falta git fetch origin tag '
                      '$BASE_TAG (o GA v1.4.2 foi cortado em 2026-09-30)"\n')
RUNNER_REMOTEDIE_OLD = "(o push da tag do GA nao aconteceu?)"
RUNNER_REMOTEDIE_NEW = "(o push da tag do GA v1.4.2 nao aconteceu?)"

# A rota 1 SO; a rota 2 e recusa nomeada (D-4). Do comentario da rota 1 ate a verificacao
# fail-CLOSED, que fica (a 2.a passagem do oraculo devolve o sha e a tripla para a PROVENANCE).
RUNNER_ROUTES_START = "  # Rota 1 — o codex GLOBAL, quando ele E o pinado. O npx NAO materializa uma copia de\n"
RUNNER_ROUTES_END = "  # Verificacao fail-CLOSED pelo MESMO oraculo do pair-rail-gate (ADR-182).\n"
RUNNER_ROUTES = r'''  # Rota 1 — a UNICA nesta release (PLAN-194 D-4): o codex GLOBAL, quando ele E o pinado.
  # Ordem M4: o oraculo hasheia o payload SEM executa-lo; so um payload verificado chega a
  # rodar `--version`. O oraculo le o manifesto deste REPO_ROOT: CLAUDE_PROJECT_DIR e fixado
  # na chamada (um ambiente que aponte outro projeto nao troca o manifesto que confere).
  CODEX_LAUNCHER=""
  CODEX_ROUTE=""
  _r1_why=""
  _glob="$(command -v codex 2>/dev/null)" || _glob=""
  if [ -z "$_glob" ]; then
    _r1_why="nenhum codex no PATH"
  elif ! CLAUDE_PROJECT_DIR="$REPO_ROOT" python3 "$REPO_ROOT/.claude/hooks/check_pair_rail.py" \
         --verify-codex-pin "$_glob" >/dev/null 2>&1; then
    _r1_why="o payload do codex global ($_glob) NAO confere com o manifesto ADR-182 (que pina $CODEX_VER)"
  else
    _gv="$("$_glob" --version 2>/dev/null | awk '{print $NF}')"
    if [ "$_gv" = "$CODEX_VER" ]; then
      CODEX_LAUNCHER="$_glob"
      CODEX_CLI_VERSION="$_gv"
      CODEX_ROUTE="binario global (versao pinada, payload verificado)"
      printf 'o codex global e o pinado (%s) e o payload confere com o manifesto\n' "$_gv"
    else
      _r1_why="o codex global responde a versao '$_gv', e o manifesto pina $CODEX_VER"
    fi
  fi
  # Rota 2 (npx num cache proprio) — RECUSA NOMEADA nesta release (PLAN-194 D-4): na v1.4.2
  # ela EXECUTAVA o pacote baixado (`npx ... --version`) antes de qualquer verificacao. Nada
  # e baixado nem executado aqui; a rota e o codex pinado instalado globalmente.
  if [ -z "$CODEX_LAUNCHER" ]; then
    die "rota 1 indisponivel: $_r1_why. A rota 2 (npx num cache proprio) e RECUSA NOMEADA nesta release (PLAN-194 D-4): nada foi baixado nem executado. Instale globalmente a versao que o manifesto pina ($CODEX_VER, a do re-pin assinado; nunca npm update -g), confira com: python3 .claude/hooks/check_pair_rail.py --verify-codex-pin \"\$(command -v codex)\" — e re-rode."
  fi
'''
RUNNER_VERIFY_OLD = ('  _pin_json="$(python3 "$REPO_ROOT/.claude/hooks/check_pair_rail.py" \\\n'
                     '    --verify-codex-pin "$CODEX_LAUNCHER")"\n')
RUNNER_VERIFY_NEW = ('  _pin_json="$(CLAUDE_PROJECT_DIR="$REPO_ROOT" python3 "$REPO_ROOT/.claude/hooks/check_pair_rail.py" \\\n'
                     '    --verify-codex-pin "$CODEX_LAUNCHER")"\n')

RUNNER_PKG_OLD = 'CODEX_PKG="@openai/codex@$CODEX_VER"\n'

# A particao da 1.4.3 (CONTEUDO DA RELEASE — provisorio no K1; ver RELEASE_CONTENT).
RUNNER_PARTS_START = "part_pathspec() {\n"
RUNNER_PARTS_END = "prompt_header() {\n"
RUNNER_PARTS = r'''part_pathspec() {
  case "$1" in
    1) printf '%s\n' \
         "templates/" ".claude/settings.json" ".claude/agents/" \
         "scripts/" ":(exclude)scripts/local/" \
         ".claude/hooks/_lib/agent_frontmatter.py" ".claude/hooks/_lib/effective_config.py" \
         ".claude/scripts/env-inventory.json" ".github/" \
         "CHANGELOG.md" "INSTALL.md" "SUPPORT.md" "README.md" "README.pt-BR.md" "npm/" \
         "VERSION" ".claude/.framework-version" ".claude-plugin/" "pyproject.toml" \
         "SBOM.md" "SECURITY.md" "VERSIONING.md" ":(exclude,glob)**/tests/**" ;;
    2) printf '%s\n' \
         ".claude/hooks/" \
         ":(exclude).claude/hooks/_lib/agent_frontmatter.py" \
         ":(exclude).claude/hooks/_lib/effective_config.py" ":(exclude,glob)**/tests/**" ;;
    3) printf '%s\n' \
         ".claude/scripts/" ":(exclude).claude/scripts/local/" ":(exclude).claude/scripts/data/" \
         ":(exclude).claude/scripts/env-inventory.json" \
         ".claude/commands/" ".claude/skills/" ":(exclude,glob)**/tests/**" ;;
    4) printf '%s\n' "docs/" ":(exclude)docs/research/" ":(exclude,glob)**/tests/**" ;;
    *) return 1 ;;
  esac
}

# O que fica FORA do re-pass, por classe (README-rc1.md §4 diz o motivo de cada uma).
out_of_scope_pathspec() {
  printf '%s\n' \
    ":(glob)**/tests/**" ".claude/plans/" "docs/research/" "CLAUDE.md" \
    ".claude/governance/" ".claude/scripts/local/" ".claude/adr/" ".claude/data/" \
    ".claude/scripts/data/" "scripts/local/"
}

part_label() {
  case "$1" in
    1) echo "instalacao, upgrade, settings e o pipeline de release: templates/**, .claude/settings.json, .claude/agents/**, scripts/** (install.sh, upgrade.sh e o resto do instalador), o piso VETO e o pin efetivo (_lib/agent_frontmatter.py, _lib/effective_config.py), env-inventory, .github/** (o validate.yml e o npm-publish.yml, com o job da prova do toolchain da rc), CHANGELOG/INSTALL/SUPPORT/README, npm/ e os sitios de versao do bump" ;;
    2) echo "os hooks que rodam na sessao do adopter: .claude/hooks/** fora dos testes e dos dois arquivos da parte 1 (o audit_log e a cadeia de auditoria, os adapters e os auxiliares de _lib/)" ;;
    3) echo "as CLIs do mantenedor e do operador: .claude/scripts/** fora dos testes, de local/ e de data/ (boot, custo e telemetria, auditoria, deprecacoes de modelo, deriva de substrato), .claude/commands/** e .claude/skills/**" ;;
    4) echo "a documentacao entregue: docs/** fora de docs/research/" ;;
  esac
}
part_coverage() {
  # A revisao que ESTE conteudo ja teve antes da release. Isto entra no prompt para
  # que o revisor possa dar GO-WITH-CONDITIONS com a condicao NOMEANDO a
  # cobertura, em vez de tratar tudo como inedito. Pela FORMA: nenhuma lista de lands.
  case "$1" in
    1) echo "os arquivos desta parte que uma cerimonia assinada pelo Owner mudou nesta faixa landaram sob ela, com rail proprio; os demais landaram livres, com testes, e esta e a primeira revisao cruzada deles numa release; os sitios de versao sao escritos pelo release.sh bump e NAO passaram por rail proprio" ;;
    2) echo "os arquivos desta parte que uma cerimonia assinada pelo Owner mudou nesta faixa landaram sob ela, com rail proprio; os demais landaram livres, com testes, e esta e a primeira revisao cruzada deles numa release" ;;
    3) echo "os arquivos desta parte que uma cerimonia assinada pelo Owner mudou nesta faixa landaram sob ela, com rail proprio; os demais landaram livres, com testes - esta e a primeira revisao cruzada deles numa release" ;;
    4) echo "a documentacao desta faixa landou livre ou dentro de uma cerimonia assinada que a cita; esta e a primeira revisao cruzada dela numa release" ;;
  esac
}

'''

RUNNER_CONTEXT_START = "CONTEXT\n- Base is the v1.4.2 GA tag. v1.4.3 is an EXPRESS release: Claude Opus 5.5\n"
RUNNER_CONTEXT_END = "WHAT TO VERIFY\n"
RUNNER_CONTEXT = r'''CONTEXT
- Base is the v1.4.2 GA tag. v1.4.3 is a MAINTENANCE release (PLAN-194):
  the pair-rail pin moves to Codex 0.160.0 (its own signed ceremony), RC
  tags run a read-only npm toolchain proof job that never publishes (the
  publish job still skips RC tags), and the train's other lands ship:
  audit-log and hook changes, the CI workflow, maintainer CLIs and docs.
  What is outside the $NPARTS payloads is DECLARED out of scope, with the
  reason, in .claude/plans/PLAN-194/repass-rc1/README-rc1.md; every path
  changed in the range is in exactly one payload or in a declared
  out-of-scope class (checked mechanically before this review).
- THIS IS ROUND 1 of this release's re-pass.
- Carried debt is DECLARED, not new: the v1.4.0 P1 annex (no release
  assigned for its cure), what the signed v1.4.2 GA envelope declared
  known-open - the signed v1.4.2-rc.1 annex (three P1) among it - and the
  P2 follow-ups of the verdicts those envelopes pin. A finding that is one
  of those declared items is not a new finding: judge whether the
  declaration is HONEST.
- Every code claim in the conditions below was checked against this
  candidate by the kit's probe before this review (probe-rc1.txt in the
  evidence); the probe is evidence, not proof - judge the claims against
  the code.
- Prior cross-model coverage of THIS part (not a reason to skip; yours is
  the INTEGRATION view against the tag adopters will install): $3
- Python is stdlib-only and must stay Python >= 3.9 compatible (no runtime
  PEP 604 unions, no match statement). Hooks fail OPEN on infrastructure
  (missing file, import failure, timeout => a breadcrumb and {}), and fail
  CLOSED on input a security matcher cannot parse. Deliberate exception
  (ADR-186): the canonical-edit matcher's per-invocation wall deadline is
  fail-CLOSED - a timeout there is an incomplete verification, not
  infrastructure.
- RULE OF THIS CUT (ratified by the Owner for v1.4.0 and applied to v1.4.1
  and v1.4.2): NO-GO ONLY if a declared condition below is FALSE against
  the code, or you find a P0. An undeclared P1 is NOT a NO-GO: report it
  under "NEW FINDINGS (annex)" (FILE:LINE, scenario, minimal fix); verdict
  files are hashed into the signed material, so the annex is signed. Name
  the applicable declared conditions. Identify P2 follow-ups separately.

'''
RUNNER_VERIFY5_OLD = "5. What a reviewer would most plausibly miss in THIS diff.\n"
RUNNER_VERIFY5_NEW = ('5. Release pipeline: can the RC toolchain proof job mint or use a registry\n'
                      '   credential, write to the registry, or diverge from the publish job\n'
                      '   whose toolchain it claims to prove? Can the publish job now run on an\n'
                      '   RC tag?\n'
                      '6. What a reviewer would most plausibly miss in THIS diff.\n')

RUNNER_PROV_OLD = '  echo "- Data: $(date -u +%Y-%m-%dT%H:%M:%SZ)"\n} > "$OUT/PROVENANCE-rc1.md"'
RUNNER_PROV_NEW = ('  echo "- classes de morte do codex (so das linhas ERROR: do proprio codex nas ultimas 40 linhas do transcript): capacidade do modelo = re-tentada ate 2 vezes; LIMITE DE USO/quota da CONTA Codex = sem re-tentativa, nenhuma parte nova lancada, recusa nomeada"\n'
                   '  echo "- Data: $(date -u +%Y-%m-%dT%H:%M:%SZ)"\n} > "$OUT/PROVENANCE-rc1.md"')

RUNNER_MN_OLD = '  _mn="$(grep -c . "$MAN")"\n'
RUNNER_MN_NEW = ('  _mnrc=0; _mn="$(grep -c . "$MAN")" || _mnrc=$?\n'
                 '  [ "$_mnrc" -le 1 ] || die "grep do manifesto da parte $P rc=$_mnrc"\n')
RUNNER_CTL_OLD = "  # Controles: truncamento, hunks preservados, linhas preservadas.\n"
RUNNER_CTL_NEW = ("  # Controles: truncamento, hunks preservados, linhas preservadas. O `set -e` que o\n"
                  "  # controle de truncamento deixa ligado vale da 1.a parte em diante: cada `grep -c`\n"
                  "  # guarda o rc por `|| rc=$?`, nunca `; rc=$?` (sairia calado, sem a linha FAIL).\n")
RUNNER_RH_OLD = "  RH=$(grep -c '^@@' \"$RAW\"); _rhrc=$?\n"
RUNNER_RH_NEW = "  _rhrc=0; RH=$(grep -c '^@@' \"$RAW\") || _rhrc=$?\n"
RUNNER_DH_OLD = "  DH=$(grep -c '^@@' \"$RED\"); _dhrc=$?\n"
RUNNER_DH_NEW = "  _dhrc=0; DH=$(grep -c '^@@' \"$RED\") || _dhrc=$?\n"

# As classes de morte (cura do GA v1.4.2), antes da fase B. A forma das mensagens de limite
# de CONTA foi RE-MEDIDA no binario do codex 0.160.0 (o pinado; payload 112fae7a, `strings`
# em 2026-10-08, nenhuma chamada paga): os 4 textos medidos na 0.156.1 seguem la, e aparecem
# tambem «hit your spend cap» e «reached your workspace credit limit»; de capacidade, alem
# dos dois de antes, «experiencing high load». O prefixo `ERROR: ` segue um literal do binario.
RUNNER_CLASSES_ANCHOR = "# --- fase B: codex por parte. Serial por default (RC1_CODEX_JOBS=1, o comportamento\n"
RUNNER_CLASSES = r'''# --- classes de MORTE de uma tentativa do codex (cura do GA v1.4.2) ----------------------
# Uma tentativa MORTA (rc != 0 e nenhum veredito) e classificada SO pelas linhas de erro
# do PROPRIO codex: `ERROR: ...` na coluna 0, nas ultimas 40 linhas do transcript. Nunca
# pelo transcript inteiro: ele ECOA o payload (condicoes e diff) e a saida das
# ferramentas que o revisor rodou, e um trecho que cite "usage limit" ou "at capacity"
# classificaria a morte errada. Duas classes:
#   - LIMITE DE USO/quota da CONTA Codex: NUNCA re-tentado (a conta so volta na hora de
#     reset que o codex imprime), nenhuma parte nova e lancada depois dele, a PROVENANCE o
#     declara (com a hora de reset quando o codex a imprime) e o run termina em RECUSA
#     NOMEADA. Os textos sao os do binario do codex 0.160.0, o pinado (medidos por
#     `strings` em 2026-10-08): "You've hit your usage limit ...", "Usage limit reached",
#     "You've reached your usage limit", "Quota exceeded", "... out of credits", "You hit
#     your spend cap ..." e "You've reached your workspace credit limit" — os dois ultimos
#     nao foram medidos na 0.156.1.
#   - capacidade do modelo ("at capacity", "Review was interrupted", "experiencing high
#     load"): re-tentada ate 2 vezes; a fase C declara quantas.
CODEX_ACCOUNT_LIMIT_RE='hit your usage limit|reached your usage limit|Usage limit reached|Quota exceeded|out of credits|hit your spend cap|reached your workspace credit limit'
CODEX_CAPACITY_RE='at capacity|Review was interrupted|experiencing high load'
# As linhas `ERROR: ` do fim do transcript (vazio sem transcript). awk: rc 0 sem casamento.
codex_error_tail() {
  [ -f "$1" ] || return 0
  tail -n 40 "$1" | tr -d '\r' | awk '/^ERROR: /'
}
# rc 0 e a ULTIMA linha de conta (so ASCII imprimivel - o apostrofo curvo do codex some -,
# no maximo 240 caracteres) quando o fim do transcript traz o limite de uso da CONTA.
codex_account_limit() {
  local _cal
  _cal="$(codex_error_tail "$1" | awk -v re="$CODEX_ACCOUNT_LIMIT_RE" '$0 ~ re { l = $0 } END { if (l != "") print l }')" \
    || return 1
  [ -n "$_cal" ] || return 1
  printf '%s' "$_cal" | LC_ALL=C tr -cd '\40-\176' | cut -c1-240
}
# rc 0 quando o fim do transcript traz a assinatura de capacidade do modelo.
codex_capacity_death() {
  local _cap
  _cap="$(codex_error_tail "$1" | awk -v re="$CODEX_CAPACITY_RE" '$0 ~ re { n++ } END { print n + 0 }')" \
    || return 1
  [ "$_cap" -gt 0 ]
}
codex_quota_seen() {
  local _q
  for _q in "$OUT"/.codex-quota-*; do
    [ -e "$_q" ] && return 0
  done
  return 1
}

'''
RUNNER_LAUNCH_OLD = ('  RED="$OUT/payload-rc1-$P.redacted.txt"\n'
                     '  rm -f "$OUT/.codex-rc-$P"\n')
RUNNER_LAUNCH_NEW = ('  RED="$OUT/payload-rc1-$P.redacted.txt"\n'
                     '  # Depois de uma morte pelo LIMITE DE USO da CONTA nenhuma parte nova e lancada\n'
                     '  # (so pesa com RC1_CODEX_JOBS < 4: numa onda so as quatro ja foram lancadas).\n'
                     '  if codex_quota_seen; then\n'
                     "    printf 'parte %s/%s: NAO lancada - o LIMITE DE USO da CONTA Codex ja matou outra parte deste run\\n' \"$P\" \"$NPARTS\" >&2\n"
                     '    echo 96 > "$OUT/.codex-rc-$P"\n'
                     '    continue\n'
                     '  fi\n'
                     '  rm -f "$OUT/.codex-rc-$P"\n')
RUNNER_RETRYDOC_OLD = ("  # do modelo — rc != 0, NENHUM veredito e a assinatura do servidor no transcript —\n"
                       "  # no maximo 2 vezes; a fase C declara na PROVENANCE quantas houve.\n")
RUNNER_RETRYDOC_NEW = ("  # do modelo — rc != 0, NENHUM veredito e a assinatura do servidor numa linha ERROR: do\n"
                       "  # proprio codex no fim do transcript — no maximo 2 vezes; a fase C declara na\n"
                       "  # PROVENANCE quantas houve. O LIMITE DE USO da CONTA nunca e re-tentado (classes acima).\n")
RUNNER_RETRY_OLD = r'''      if [ "$_rc" -ne 0 ] && [ "$_try" -lt 3 ] && [ ! -s "$OUT/verdict-rc1-$P.txt" ] \
         && grep -qE 'at capacity|Review was interrupted' "$OUT/transcript-rc1-$P.log"; then
        _wait=$((_try * ${RC1_RETRY_UNIT_SECONDS:-90}))
        printf 'parte %s: tentativa %s MORTA por capacidade do modelo; nova tentativa em %ss\n' \
          "$P" "$_try" "$_wait" >&2
        printf '%s\n' "$_try" > "$OUT/.codex-dead-$P"
        sleep "$_wait"
        continue
      fi
'''
RUNNER_RETRY_NEW = r'''      if [ "$_rc" -ne 0 ] && [ ! -s "$OUT/verdict-rc1-$P.txt" ]; then
        if _acct="$(codex_account_limit "$OUT/transcript-rc1-$P.log")"; then
          printf '%s\n' "$_acct" > "$OUT/.codex-quota-$P"
          printf 'parte %s: tentativa %s MORTA pelo LIMITE DE USO da CONTA Codex (nao e capacidade do modelo) - sem re-tentativa\n' \
            "$P" "$_try" >&2
          break
        fi
        if [ "$_try" -lt 3 ] && codex_capacity_death "$OUT/transcript-rc1-$P.log"; then
          _wait=$((_try * ${RC1_RETRY_UNIT_SECONDS:-90}))
          printf 'parte %s: tentativa %s MORTA por capacidade do modelo; nova tentativa em %ss\n' \
            "$P" "$_try" "$_wait" >&2
          printf '%s\n' "$_try" > "$OUT/.codex-dead-$P"
          sleep "$_wait"
          continue
        fi
      fi
'''
RUNNER_PHASEC_OLD = ("# --- fase C: veredito, proveniencia, quarentena e integridade, na ORDEM das partes ---\n"
                     "for P in $PARTS; do\n")
RUNNER_PHASEC_NEW = ("# --- fase C: veredito, proveniencia, quarentena e integridade, na ORDEM das partes ---\n"
                     'QUOTA_PARTS=""\nQUOTA_RESET=""\n'
                     "for P in $PARTS; do\n")
RUNNER_QLINE_OLD = '  scrub_home_paths "$OUT/transcript-rc1-$P.log" || die "scrub do transcript da parte $P"\n'
RUNNER_QLINE_NEW = r'''  QLINE=""
  if [ -f "$OUT/.codex-quota-$P" ]; then
    QLINE="$(head -n 1 "$OUT/.codex-quota-$P")" || QLINE="(linha ilegivel)"
    [ -n "$QLINE" ] || QLINE="(linha vazia)"
    QUOTA_PARTS="$QUOTA_PARTS $P"
    if [ -z "$QUOTA_RESET" ]; then
      QUOTA_RESET="$(printf '%s\n' "$QLINE" | sed -n 's/.*[Tt]ry again at //p' | sed 's/[.[:space:]]*$//' | head -n 1)" \
        || QUOTA_RESET=""
    fi
  fi
  rm -f "$OUT/.codex-quota-$P"
  scrub_home_paths "$OUT/transcript-rc1-$P.log" || die "scrub do transcript da parte $P"
'''
RUNNER_PROVPART_OLD = ('      echo "  - $DEAD tentativa(s) MORTA(s) por capacidade do modelo antes desta (sem veredito; transcript sobrescrito pela tentativa valida)"\n'
                       '    fi\n'
                       '  } >> "$OUT/PROVENANCE-rc1.md" || die "proveniencia da parte $P"\n')
RUNNER_PROVPART_NEW = ('      echo "  - $DEAD tentativa(s) MORTA(s) por capacidade do modelo antes desta (sem veredito; transcript sobrescrito pela tentativa valida)"\n'
                       '    fi\n'
                       '    if [ -n "$QLINE" ]; then\n'
                       '      echo "  - MORTA pelo LIMITE DE USO da CONTA Codex (nao e capacidade do modelo; sem re-tentativa): $QLINE"\n'
                       '    fi\n'
                       '    if [ "$CRC" = "96" ]; then\n'
                       '      echo "  - NAO lancada: o LIMITE DE USO da CONTA Codex ja tinha matado outra parte deste run"\n'
                       '    fi\n'
                       '  } >> "$OUT/PROVENANCE-rc1.md" || die "proveniencia da parte $P"\n')
RUNNER_OVERALL_OLD = 'echo "RUNNER-OVERALL: rc=$OVERALL" >> "$OUT/PROVENANCE-rc1.md"\n'
RUNNER_OVERALL_NEW = r'''if [ -n "$QUOTA_PARTS" ]; then
  echo "- LIMITE DE USO da CONTA Codex: parte(s)$QUOTA_PARTS sem veredito${QUOTA_RESET:+ (o codex diz: try again at $QUOTA_RESET)}; o runner NAO re-tentou e recusa esta tentativa (nao e rodada)" \
    >> "$OUT/PROVENANCE-rc1.md" || die "proveniencia do limite de uso da conta"
fi
echo "RUNNER-OVERALL: rc=$OVERALL" >> "$OUT/PROVENANCE-rc1.md"
if [ -n "$QUOTA_PARTS" ]; then
  die "LIMITE DE USO da CONTA Codex (nao e capacidade do modelo): parte(s)$QUOTA_PARTS sem veredito${QUOTA_RESET:+; o codex diz para tentar de novo em $QUOTA_RESET}. O runner NAO re-tenta este caso e nao lanca parte nova depois dele. Nao e rodada: preserve a tentativa inteira FORA do repositorio (o passo 6 do OWNER-RC1-CUT.sh da a rota), mantenha o CANDIDATE.sha e re-rode depois do reset da conta."
fi
'''


def derive_runner(src: str) -> str:
    t = shift(src, "runner")
    t = cut_region(t, "#!/bin/bash\n", "# Pipeline por parte, identico ao do runner da v1.4.2-rc.1:\n",
                   RUNNER_HEADER, "cabecalho do runner")
    t = cut_region(t, RUNNER_CODEXDOC_START, RUNNER_CODEXDOC_END, RUNNER_CODEXDOC, "doc do codex")
    t = sub(t, RUNNER_BASE_OLD, RUNNER_BASE_NEW, "doc da base")
    t = sub(t, RUNNER_ATTEMPT_OLD, RUNNER_ATTEMPT_NEW, "marcadores de tentativa")
    t = sub(t, RUNNER_STEP1_OLD, RUNNER_STEP1_NEW, "passo 1")
    t = sub(t, RUNNER_BASEDIE_OLD, RUNNER_BASEDIE_NEW, "recusa da base ausente")
    t = sub(t, RUNNER_REMOTEDIE_OLD, RUNNER_REMOTEDIE_NEW, "recusa da base remota")
    t = cut_region(t, RUNNER_ROUTES_START, RUNNER_ROUTES_END, RUNNER_ROUTES, "rotas do codex")
    t = sub(t, RUNNER_VERIFY_OLD, RUNNER_VERIFY_NEW, "oraculo do pin")
    t = sub(t, RUNNER_PKG_OLD, "", "CODEX_PKG (so a rota 2 o usava)")
    t = cut_region(t, RUNNER_PARTS_START, RUNNER_PARTS_END, RUNNER_PARTS, "particao")
    t = cut_region(t, RUNNER_CONTEXT_START, RUNNER_CONTEXT_END, RUNNER_CONTEXT, "CONTEXT do prompt")
    t = sub(t, RUNNER_VERIFY5_OLD, RUNNER_VERIFY5_NEW, "WHAT TO VERIFY 5")
    t = sub(t, RUNNER_PROV_OLD, RUNNER_PROV_NEW, "PROVENANCE: classes de morte")
    t = sub(t, RUNNER_MN_OLD, RUNNER_MN_NEW, "grep -c do manifesto")
    t = sub(t, RUNNER_CTL_OLD, RUNNER_CTL_NEW, "comentario dos controles")
    t = sub(t, RUNNER_RH_OLD, RUNNER_RH_NEW, "grep -c dos hunks RAW")
    t = sub(t, RUNNER_DH_OLD, RUNNER_DH_NEW, "grep -c dos hunks RED")
    t = sub(t, RUNNER_CLASSES_ANCHOR, RUNNER_CLASSES + RUNNER_CLASSES_ANCHOR, "classes de morte")
    t = sub(t, RUNNER_LAUNCH_OLD, RUNNER_LAUNCH_NEW, "lancamento da parte")
    t = sub(t, RUNNER_RETRYDOC_OLD, RUNNER_RETRYDOC_NEW, "doc da re-tentativa")
    t = sub(t, RUNNER_RETRY_OLD, RUNNER_RETRY_NEW, "re-tentativa por classe")
    t = sub(t, RUNNER_PHASEC_OLD, RUNNER_PHASEC_NEW, "fase C")
    t = sub(t, RUNNER_QLINE_OLD, RUNNER_QLINE_NEW, "linha do limite de conta")
    t = sub(t, RUNNER_PROVPART_OLD, RUNNER_PROVPART_NEW, "PROVENANCE da parte")
    t = sub(t, RUNNER_OVERALL_OLD, RUNNER_OVERALL_NEW, "recusa do limite de conta")
    forbid(t, "runner", ["npx -y", "NPX_CACHE", "npm_config_cache", "CODEX_PKG",
                         "PLAN-193/repass-rc1/probe", "derive-kit-142", "Opus 5.5", "FN-04"])
    need(t, "runner", ['OUT="$REPO_ROOT/.claude/plans/PLAN-194/repass-rc1"', 'BASE_TAG="v1.4.2"',
                       "e RECUSA NOMEADA nesta release (PLAN-194 D-4): nada foi baixado nem executado",
                       '"$WT/.claude/plans/PLAN-194/repass-rc1/probe-conditions-rc1.py"',
                       "# Proveniencia do re-pass do CANDIDATO v1.4.3-rc.1 - PLAN-194 - $NPARTS partes",
                       "codex_account_limit() {", "upgrade.sh --pin v1.4.3-rc.1",
                       "# shim do runner rc.1 da 1.4.3"])
    return t


# ===========================================================================
# sonda das condicoes (CONTEUDO DA RELEASE — provisorio no K1)
# ===========================================================================
# A sonda da 1.4.3 = os auxiliares VERBATIM da sonda da v1.4.2-rc.1 (Infra, run, Tree, _norm,
# _env, c0_tree, c0_npm_rc, _sha_at, envelope_verdict_pins, _runner_fn, _bash_fn, runner_sets,
# sizes) + as verificacoes desta release + a lista CHECKS com o MAPA e o `--only` que recusa id
# desconhecido (curas da sonda do GA v1.4.2). As verificacoes das curas da 1.4.2 (FN-04,
# relaunch --out, pin, esforco, piso do Claude Code, adapter, CLIs novas) saem: as condicoes da
# 1.4.3 nao as afirmam.
PROBE_HEAD = r'''#!/usr/bin/env python3
"""Sonda das condicoes da v1.4.3-rc.1 (PLAN-194): cada afirmacao sobre CODIGO do
CONDITIONS-rc1.md e conferida aqui contra um commit, ANTES do re-pass.

  python3 probe-conditions-rc1.py --root DIR --base REV --head REV [--sizes] [--only ID,..]

--root  checkout onde os comportamentos rodam (o worktree do candidato no runner;
        a arvore viva no G0 do OWNER-RC1-CUT.sh). Os arquivos RASTREADOS da arvore
        tem de ser os de --head (conferido; a sonda recusa uma arvore que difere).
--base  a tag base resolvida (v1.4.2^{commit}); --head o commit sob revisao.
--sizes projeta o payload de cada parte com as funcoes do PROPRIO runner (pathspec,
        rotulo, cobertura, cabecalho do prompt) e recusa uma parte acima de
        MAX_RAW_BYTES - 16 KiB, sem arquivo, ou com menos de 50 linhas de diff.
--only  so os ids pedidos; um id desconhecido e recusa (rc 2), nunca verde vacuo.

Saida: uma linha `OK|FAIL <id>: <o que>` por afirmacao, a linha MAPA (que ids conferem cada
condicao) e a linha SONDA; rc 0 = todas OK, rc 1 = alguma FALSA (o re-pass NAO pode rodar
com este texto: corrija o codigo ou as condicoes), rc 2 = a sonda nao conseguiu medir
(infraestrutura; nunca vira OK). Nenhuma escrita fora de um diretorio temporario do
sistema, removido na saida; nenhum .pyc (PYTHONDONTWRITEBYTECODE).
DERIVADO por .claude/plans/PLAN-194/derive-kit-143.py — NAO edite a mao. stdlib, >= 3.9.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, Dict, List, Optional, Sequence, Tuple

sys.dont_write_bytecode = True

CODEX_PIN = "0.160.0"
MAX_RAW_BYTES = 262000
SIZE_MARGIN = 16384
MIN_DIFF_LINES = 50
EV_REL = ".claude/plans/PLAN-194/repass-rc1"
RUNNER_REL = EV_REL + "/run-rc1-repass.sh"
CONDITIONS_REL = EV_REL + "/CONDITIONS-rc1.md"
PLAN_FILE_REL = ".claude/plans/PLAN-194-maintenance-train-v1-4-3.md"
PLAN_DECISIONS_HEAD = "## Decisões do Owner — S362 (2026-10-02)"
GA_ENVELOPE = ".claude/governance/pair-rail-verdict-v1.4.2.md"
RC_ENVELOPE = ".claude/governance/pair-rail-verdict-v1.4.2-rc.1.md"
GA_CONDITIONS = ".claude/plans/PLAN-193/repass-ga/CONDITIONS-ga.md"
PIN_SENTINEL = ".claude/plans/PLAN-194/codex-pin-0160/pin-0160-approved.md"
NPM_PUBLISH_WF = ".github/workflows/npm-publish.yml"
RC_PROOF_JOB_ID = "rc-toolchain-proof"
RC_PROOF_JOB_NAME = "RC toolchain proof (no publish)"
# Os arquivos que os vereditos da v1.4.0 (PLAN-169) citam e que mudam nesta faixa: a
# condicao 1 os declara pela FORMA. As classes sao enumeradas AQUI (codigo), nunca no
# texto assinado.
V140_VERDICT_DIRS = (".claude/plans/PLAN-169/repass-rc1", ".claude/plans/PLAN-169/repass-ga")
V140_VERSION_SITES = frozenset([
    "VERSION", "pyproject.toml", "npm/package.json", ".claude/.framework-version",
    ".claude-plugin/plugin.json", ".claude-plugin/marketplace.json"])
V140_TEXT_RE = re.compile(
    r"^(?:CHANGELOG|README(?:\.[A-Za-z-]+)?|INSTALL|SECURITY|VERSIONING|SBOM|SUPPORT)\.md$"
    r"|^npm/README\.md$|^docs/(?!research/)[^/]+\.md$")
V140_SETTINGS_RE = re.compile(r"^templates/settings/[^/]+\.json$")
V140_SCRIPTS = frozenset(["scripts/upgrade.sh", "scripts/install.sh"])
V140_WORKFLOWS_RE = re.compile(r"^\.github/workflows/[^/]+\.yml$")
V140_HOOKS_RE = re.compile(r"^\.claude/hooks/(?!tests/).+\.py$")
V140_TESTS_RE = re.compile(r"(?:^|/)tests/")
GOV_ALLOWED = frozenset([".claude/governance/codex-cli-pin.txt",
                         ".claude/governance/codex-cli-pin-manifest.json",
                         ".claude/governance/gate-scripts-manifest.txt"])
LOCAL_ALLOWED = frozenset([".claude/scripts/local/release.sh"])


'''

PROBE_AFFIRM_HEAD = ("# ---------------------------------------------------------------------------\n"
                     "# afirmacoes\n"
                     "# ---------------------------------------------------------------------------\n")

PROBE_CHECKS_A = r'''def _job_block(wf: str, job_id: str) -> Optional[str]:
    """O bloco do job `<job_id>:` (indentado 2 espacos sob `jobs:`), ou None."""
    m = re.search(r"(?m)^  %s:[ \t]*\n" % re.escape(job_id), wf)
    if not m:
        return None
    rest = wf[m.end():]
    nxt = re.search(r"(?m)^  [A-Za-z0-9_-]+:[ \t]*$|^[^ \t\n#]", rest)
    return wf[m.start():m.end() + (nxt.start() if nxt else len(rest))]


def _code_lines(block: str) -> List[str]:
    """As linhas do bloco fora de comentario (YAML: `#` no inicio, depois de espacos)."""
    return [ln for ln in block.splitlines() if ln.strip() and not ln.strip().startswith("#")]


def c0_rc_proof(t: Tree) -> str:
    """Condicao 4: o job da prova do toolchain da rc (W4) — nome, gatilho, permissoes, e
    nenhum caminho de credencial ou de escrita no registry."""
    wf = t.show(t.head, NPM_PUBLISH_WF)
    if wf is None:
        raise AssertionError("%s ausente" % NPM_PUBLISH_WF)
    blk = _job_block(wf, RC_PROOF_JOB_ID)
    if blk is None:
        raise AssertionError("%s sem o job %s (a W4 nao landou?)" % (NPM_PUBLISH_WF, RC_PROOF_JOB_ID))
    code = _code_lines(blk)
    names = [ln.split(":", 1)[1].strip() for ln in code if re.match(r"^    name:", ln)]
    if names != [RC_PROOF_JOB_NAME]:
        raise AssertionError("o job %s se chama %r (o passo 18 exige %r)" % (RC_PROOF_JOB_ID, names, RC_PROOF_JOB_NAME))
    ifs = [ln.split(":", 1)[1].strip() for ln in code if re.match(r"^    if:", ln)]
    if ifs != ["contains(github.ref, '-rc.')"]:
        raise AssertionError("o job %s nao roda so nas tags -rc. (if: %r)" % (RC_PROOF_JOB_ID, ifs))
    perm = re.search(r"(?m)^    permissions:[ \t]*\n((?:      [^\n]*\n|[ \t]*#[^\n]*\n)+)", blk)
    plines = _code_lines(perm.group(1)) if perm else []
    if [ln.strip() for ln in plines] != ["contents: read"]:
        raise AssertionError("o job %s tem permissions %r (a condicao 4 diz: so contents: read)"
                             % (RC_PROOF_JOB_ID, [ln.strip() for ln in plines]))
    joined = "\n".join(code)
    for bad, why in (("id-token", "uma permissao de token OIDC"), ("secrets.", "um segredo"),
                     ("\n    environment:", "um environment")):
        if bad in "\n" + joined:
            raise AssertionError("o job %s cita %s (%r)" % (RC_PROOF_JOB_ID, why, bad))
    if re.search(r"\bnpm\s+publish\b", joined):
        raise AssertionError("um passo do job %s chama npm publish" % RC_PROOF_JOB_ID)
    return "job %s «%s»: so nas tags -rc., permissions contents: read, sem id-token/environment/secrets, sem npm publish" % (
        RC_PROOF_JOB_ID, RC_PROOF_JOB_NAME)


def c1_annex(t: Tree) -> str:
    env = _norm(t.show(t.head, GA_ENVELOPE) or "")
    for need in ("release_tag: v1.4.2 ", "O anexo P1 da v1.4.0 segue ABERTO", "nenhuma versão está prometida"):
        if need not in env + " ":
            raise AssertionError("o envelope do GA (%s) nao carrega %r" % (GA_ENVELOPE, need))
    if t.show(t.head, ".claude/governance/pair-rail-verdict-v1.4.0.md") is None:
        raise AssertionError("envelope da v1.4.0 ausente")
    # arquivos citados pelos vereditos da v1.4.0 que mudam na faixa: todos numa classe
    texts: List[str] = []
    for d in V140_VERDICT_DIRS:
        for name in t.git("ls-tree", "--name-only", t.head, d + "/").splitlines():
            if re.search(r"/verdict-[^/]*\.txt$", name):
                texts.append(t.show(t.head, name) or "")
    if len(texts) != 14:
        raise AssertionError("%d vereditos da v1.4.0 (esperado 14)" % len(texts))
    hits = []
    for p in t.changed():
        pat = re.compile(r"(?<![\w./-])" + re.escape(p) + r"(?![\w-])")
        if any(pat.search(x) for x in texts):
            hits.append(p)
    stray = [p for p in hits if not (p in V140_VERSION_SITES or V140_TEXT_RE.match(p)
                                     or V140_SETTINGS_RE.match(p) or p in V140_SCRIPTS
                                     or V140_WORKFLOWS_RE.match(p) or V140_HOOKS_RE.match(p)
                                     or V140_TESTS_RE.search(p) or p == "CLAUDE.md")]
    if stray:
        raise AssertionError("arquivo citado pelos vereditos da v1.4.0 muda fora das classes "
                             "declaradas: %s" % ", ".join(stray))
    if not hits:
        raise AssertionError("nenhum arquivo citado pelos vereditos da v1.4.0 muda na faixa — "
                             "a condicao 1 diz que mudam")
    return "anexo da v1.4.0 re-declarado (envelope do GA v1.4.2); %d citado(s) mudam, todos nas classes" % len(hits)


'''

PROBE_CHECKS_B = r'''def c2_carried(t: Tree) -> str:
    seen: Dict[str, str] = {}
    counts = []
    for rel in (GA_ENVELOPE, RC_ENVELOPE):
        man, cond = envelope_verdict_pins(t, rel)
        if not man:
            raise AssertionError("%s: o MANIFEST pinado nao lista veredito nenhum" % rel)
        for path, want in man + cond:
            got = _sha_at(t, path)
            if got is None:
                raise AssertionError("veredito pinado por %s ausente: %s" % (rel, path))
            if got != want:
                raise AssertionError("veredito pinado por %s nao tem o sha256 pinado: %s" % (rel, path))
            seen[path] = want
        for path, _w in man:
            lines = [ln for ln in (t.show(t.head, path) or "").splitlines() if ln.startswith("VERDICT:")]
            if len(lines) != 1 or not re.match(r"VERDICT: (GO|GO-WITH-CONDITIONS)(\s|$)", lines[0]):
                raise AssertionError("%s (no MANIFEST de %s) sem um VERDICT GO/GWC unico" % (path, rel))
        counts.append("%s: %d pelo MANIFEST + %d por condicao" % (rel.rsplit("/", 1)[1], len(man), len(cond)))
    gc = _norm(t.show(t.head, GA_CONDITIONS) or "")
    for need in ("13. **Os três P1 do anexo assinado da rc.1 seguem ABERTOS no GA",
                 "14. **Os P2 dos quatro vereditos da rc.1 seguem ABERTOS no GA"):
        if need not in gc:
            raise AssertionError("%s nao numera mais %r (a condicao 2 cita as condicoes 13 e 14 dele)"
                                 % (GA_CONDITIONS, need[:40]))
    return "%d veredito(s) pinado(s), todos presentes com o sha256 pinado (%s); GA: 13 e 14" % (
        len(seen), "; ".join(counts))


def c9_codex(t: Tree) -> str:
    man = json.loads(t.show(t.head, ".claude/governance/codex-cli-pin-manifest.json") or "{}")
    if man.get("package_version") != CODEX_PIN:
        raise AssertionError("o manifesto ADR-182 pina %r (esperado %s: o re-pin landou?)"
                             % (man.get("package_version"), CODEX_PIN))
    for rel in (PIN_SENTINEL, PIN_SENTINEL + ".asc"):
        if t.show(t.head, rel) is None:
            raise AssertionError("%s ausente (a cerimonia do re-pin nao landou)" % rel)
    return "manifesto ADR-182 pina %s; cerimonia do re-pin landada" % CODEX_PIN


def c13_route1(t: Tree) -> str:
    """Condicao 3: o runner do candidato resolve o codex SO pela rota 1 (D-4)."""
    runner = t.show(t.head, RUNNER_REL)
    if runner is None:
        raise AssertionError("%s ausente" % RUNNER_REL)
    code = "\n".join(ln for ln in runner.splitlines() if not ln.lstrip().startswith("#"))
    if re.search(r"\bnpx\s+(?:-y\b|--yes\b|-p\b|--package\b|@|\"?\$)|command -v npx\b", code):
        raise AssertionError("o runner do candidato ainda invoca npx (a rota 2 viva)")
    for need in ("e RECUSA NOMEADA nesta release (PLAN-194 D-4): nada foi baixado nem executado",
                 '--verify-codex-pin "$_glob"', 'CODEX_ROUTE="binario global (versao pinada, payload verificado)"'):
        if need not in runner:
            raise AssertionError("o runner do candidato sem %r" % need)
    i_or = runner.find('--verify-codex-pin "$_glob"')
    i_ex = runner.find('"$_glob" --version')
    if i_ex < 0 or i_or < 0 or i_ex < i_or:
        raise AssertionError("no runner do candidato o `--version` do codex global nao vem DEPOIS do oraculo")
    return "o runner do candidato: rota 1 so (oraculo antes de executar), rota 2 recusa nomeada, nenhum npx"


def _plan_decision(plan: str, n: str) -> Optional[str]:
    """A linha `| D-<n> | ... |` da tabela de decisoes do Owner do plano."""
    i = plan.find(PLAN_DECISIONS_HEAD)
    if i < 0:
        return None
    m = re.search(r"(?m)^\| D-%s \|[^\n]*\|$" % re.escape(n), plan[i:])
    return m.group(0) if m else None


def c12_plan_decisions(t: Tree) -> str:
    """Toda decisao D-N que as condicoes citam esta na tabela de decisoes do Owner do plano
    commitado; e a D-4 diz o que a condicao 3 diz dela (rota 1 so, rota 2 recusa nomeada)."""
    plan = t.show(t.head, PLAN_FILE_REL)
    cond = t.show(t.head, CONDITIONS_REL)
    if plan is None or cond is None:
        raise AssertionError("%s ou %s ausente em %s" % (PLAN_FILE_REL, CONDITIONS_REL, t.head[:12]))
    cited = sorted(set(re.findall(r"\bD-(\d+)\b", cond)), key=int)
    if not cited:
        raise AssertionError("as condicoes nao citam decisao D-N nenhuma (a sonda seria vacua)")
    miss = [("D-%s" % n) for n in cited if _plan_decision(plan, n) is None]
    if miss:
        raise AssertionError("as condicoes citam %s, que a tabela de decisoes do plano commitado (%s) nao traz"
                             % (", ".join(miss), PLAN_FILE_REL))
    d4 = _norm(_plan_decision(plan, "4") or "")
    if "4" in cited and not ("rota 1" in d4 and "recusa nomeada" in d4):
        raise AssertionError("a D-4 do plano commitado nao diz «rota 1» e «recusa nomeada» (a condicao 3 diz)")
    return "as condicoes citam %s; todas na tabela de decisoes do plano commitado" % (
        ", ".join("D-%s" % n for n in cited))


def c11_scope(t: Tree) -> str:
    gov = set(t.changed(".claude/governance/"))
    if not gov <= GOV_ALLOWED:
        raise AssertionError("muda em .claude/governance/ fora do declarado: %s" % ", ".join(sorted(gov - GOV_ALLOWED)))
    loc = set(t.changed(".claude/scripts/local/"))
    if not loc <= LOCAL_ALLOWED:
        raise AssertionError("em .claude/scripts/local/ muda %s (a condicao 6 diz: no maximo o release.sh)"
                             % ", ".join(sorted(loc - LOCAL_ALLOWED)))
    parts, out = runner_sets(t)
    every = set(t.changed())
    seen: Dict[str, str] = {}
    for n, s in parts.items():
        for p in s:
            if p in seen:
                raise AssertionError("%s esta nas partes %s e %s" % (p, seen[p], n))
            seen[p] = str(n)
    both = sorted(set(seen) & out)
    if both:
        raise AssertionError("caminho numa parte E fora do escopo: %s" % ", ".join(both[:5]))
    orphan = sorted(every - set(seen) - out)
    if orphan:
        raise AssertionError("caminho da faixa fora de toda parte e do escopo declarado: %s" % ", ".join(orphan[:8]))
    return "%d caminhos: %s dentro das partes, %d fora (declarado); governance e local no declarado" % (
        len(every), "+".join(str(len(parts[k])) for k in sorted(parts)), len(out & every))


'''

PROBE_TAIL = r'''CHECKS: List[Tuple[str, Callable[[Tree], str], Tuple[str, ...]]] = [
    ("C0-tree", c0_tree, ("cabecalho",)), ("C0-npm", c0_npm_rc, ("cabecalho", "4")),
    ("C0-rc-proof", c0_rc_proof, ("4",)),
    ("C1-annex-v1.4.0", c1_annex, ("1",)), ("C2-carried-1.4.2", c2_carried, ("2",)),
    ("C9-codex-pin", c9_codex, ("3",)), ("C13-route1", c13_route1, ("3",)),
    ("C11-scope", c11_scope, ("5", "6")), ("C12-plan-decisions", c12_plan_decisions, ("3",)),
]


def condition_map() -> str:
    """A linha MAPA: que ids conferem cada condicao (SIZE = --sizes, condicao 5)."""
    by: Dict[str, List[str]] = {}
    for cid, _fn, conds in CHECKS:
        for c in conds:
            by.setdefault(c, []).append(cid)
    by.setdefault("5", []).append("SIZE")
    keys = sorted(by, key=lambda k: (-1 if k == "cabecalho" else int(k)))
    return "MAPA condicao -> ids: " + "; ".join("%s: %s" % (k, " ".join(by[k])) for k in keys)


def main(argv: Optional[Sequence[str]] = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", required=True)
    ap.add_argument("--base", required=True)
    ap.add_argument("--head", required=True)
    ap.add_argument("--sizes", action="store_true")
    ap.add_argument("--only", default="")
    a = ap.parse_args(argv)
    try:
        t = Tree(a.root, "", "")
        t.base = t.git("rev-parse", "--verify", a.base + "^{commit}").strip()
        t.head = t.git("rev-parse", "--verify", a.head + "^{commit}").strip()
    except Infra as exc:
        print("INFRA sonda: %s" % exc)
        return 2
    only = set(x for x in a.only.split(",") if x)
    unknown = sorted(only - set(cid for cid, _fn, _conds in CHECKS))
    if unknown:
        # um id desconhecido rodaria NADA e sairia rc 0: nunca verde vacuo.
        print("INFRA sonda: id(s) de --only desconhecido(s): %s (ids: %s)"
              % (", ".join(unknown), " ".join(cid for cid, _fn, _conds in CHECKS)))
        return 2
    fails = infra = 0
    for cid, fn, _conds in CHECKS:
        if only and cid not in only:
            continue
        try:
            print("OK   %s: %s" % (cid, fn(t)))
        except AssertionError as exc:
            fails += 1
            print("FAIL %s: %s" % (cid, exc))
        except Infra as exc:
            infra += 1
            print("INFRA %s: %s" % (cid, exc))
        except Exception as exc:  # noqa: BLE001 — uma afirmacao que nao mede nunca vira OK
            infra += 1
            print("INFRA %s: %s: %s" % (cid, type(exc).__name__, str(exc)[:200]))
    if a.sizes:
        try:
            for ok, msg in sizes(t):
                print("%s %s" % ("OK  " if ok else "FAIL", msg))
                fails += 0 if ok else 1
        except Infra as exc:
            infra += 1
            print("INFRA SIZE: %s" % exc)
    print(condition_map())
    print("SONDA: %d FALSA(S), %d sem medida" % (fails, infra))
    if infra:
        return 2
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
'''

# Os ids da lista CHECKS (o gerador os pina em PROBE_IDS; probe_ids() confere os dois).
PROBE_IDS = ("C0-tree", "C0-npm", "C0-rc-proof", "C1-annex-v1.4.0", "C2-carried-1.4.2",
             "C9-codex-pin", "C13-route1", "C11-scope", "C12-plan-decisions")


def probe_ids(text: str) -> Tuple[str, ...]:
    """Os ids da lista CHECKS da sonda derivada, pela AST (nunca por regex sobre o texto)."""
    import ast
    lists = [n.value for n in ast.parse(text).body
             if isinstance(n, (ast.Assign, ast.AnnAssign))
             and any(getattr(tg, "id", "") == "CHECKS"
                     for tg in (n.targets if isinstance(n, ast.Assign) else [n.target]))]
    if len(lists) != 1 or not isinstance(lists[0], ast.List):
        die("sonda derivada sem UMA lista CHECKS literal")
    return tuple(e.elts[0].value for e in lists[0].elts)


def probe_conditions(text: str) -> List[str]:
    """As condicoes que a lista CHECKS da sonda derivada mapeia (o 3.o elemento de cada item)."""
    import ast
    lists = [n.value for n in ast.parse(text).body
             if isinstance(n, (ast.Assign, ast.AnnAssign))
             and any(getattr(tg, "id", "") == "CHECKS"
                     for tg in (n.targets if isinstance(n, ast.Assign) else [n.target]))]
    if len(lists) != 1 or not isinstance(lists[0], ast.List):
        die("sonda derivada sem UMA lista CHECKS literal")
    return [c.value for e in lists[0].elts for c in e.elts[2].elts]


def derive_probe(src: str) -> str:
    helpers = region(src, "class Infra(Exception):\n", PROBE_AFFIRM_HEAD, "auxiliares da sonda")
    c0 = region(src, "def c0_tree(t: Tree) -> str:\n", "def c1_annex(t: Tree) -> str:\n", "c0 da sonda")
    pins = region(src, "def _sha_at(t: Tree, rel: str) -> Optional[str]:\n",
                  "def c2_carried(t: Tree) -> str:\n", "pins de envelope")
    tail = region(src, "def _runner_fn(runner: str, name: str) -> str:\n",
                  "CHECKS: List[Tuple[str, Callable[[Tree], str]]] = [\n", "funcoes do runner")
    tail = sub(tail, '"BASE_TAG": "v1.4.1"', '"BASE_TAG": "v1.4.2"', "base da projecao de tamanho")
    t = (PROBE_HEAD + helpers + PROBE_AFFIRM_HEAD + c0 + PROBE_CHECKS_A + pins + PROBE_CHECKS_B
         + tail + PROBE_TAIL)
    if probe_ids(t) != PROBE_IDS:
        die("PROBE_IDS %r != ids da lista CHECKS da sonda derivada %r" % (PROBE_IDS, probe_ids(t)))
    forbid(t, "sonda", ["PLAN-193/repass-rc1", "canary_pre", "c7_cc_floor", '"BASE_TAG": "v1.4.1"'])
    need(t, "sonda", ['EV_REL = ".claude/plans/PLAN-194/repass-rc1"', 'CODEX_PIN = "0.160.0"',
                      "def runner_sets(t: Tree)", "def envelope_verdict_pins(", "self.root = os.path.abspath(root)",
                      "def c0_npm_rc(t: Tree) -> str:"])
    return t


# ===========================================================================
# condicoes, README e .gitignore (CONTEUDO DA RELEASE — provisorio no K1)
# ===========================================================================
COND_SRC_FIRST = ("# Condições do envelope — v1.4.2-rc.1 (release expressa: Opus 5.5, Codex 0.156.1, "
                  "curas do FN-04 e do `relaunch --out`)\n")
COND_SRC_ANCHORS = ("## A. Dívida carregada (re-declarada)", "## D. Escopo deste re-pass",
                    "\n12. **Fora do re-pass, pela forma**")

COND_TITLE = ("# Condições do envelope — v1.4.3-rc.1 (trem de manutenção: Codex 0.160.0 e a prova do "
              "toolchain do npm na rc)")
COND_PROVISIONAL_NOTE = '''
> **%s.** Estas condições são verdadeiras contra o HEAD em que o kit foi derivado no K1
> (PLAN-194 W7), com a W4 projetada; a derivação final (KIT) as completa com o que landar até a
> linha de corte (decisão D-14 do PLAN-194) e retira esta nota. Nenhum corte usa este texto.
''' % PROVISIONAL_MARK

COND_BODY = '''
Este arquivo propõe condições; não é aprovação nem assinatura. O envelope vincula o snapshot
bruto e os payloads redigidos das quatro partes; um `NO-GO` exige triagem e novo re-pass.
Regra do corte (a que o Owner ratificou para a v1.4.0 e aplicou à v1.4.1 e à v1.4.2): `NO-GO` só
por condição declarada FALSA contra o código ou por P0; um P1 não declarado vai ao veredito sob
«NEW FINDINGS (annex)» como ANEXO assinado. Este texto não promete versão para a cura de nada
que ele declara aberto.
Base: a tag assinada `v1.4.2` (o GA). Adopters: quem SOBE da v1.4.2, ou de uma versão
anterior, por `upgrade.sh --pin v1.4.3-rc.1`, e quem instala a partir de um checkout da tag pelo
`install.sh`; a rc não publica no npm (o job do publish do `npm-publish.yml` pula as tags `-rc.`).
Esta é a rodada 1 do re-pass desta release. Antes do codex, cada afirmação sobre código deste
arquivo é conferida contra o candidato por `.claude/plans/PLAN-194/repass-rc1/probe-conditions-rc1.py`,
e a saída entra na evidência (`probe-rc1.txt`); com uma afirmação que deixou de valer o runner
recusa o re-pass antes do codex (o modo de ensaio REPORT-ONLY do harness segue, e o gerador do
envelope recusa a evidência dele).

## A. Dívida carregada (re-declarada)

1. **O anexo P1 da v1.4.0 segue ABERTO, e nenhuma versão está prometida para a cura dele.** Os
   itens são as seções «NEW FINDINGS (annex)» dos vereditos em
   `.claude/plans/PLAN-169/repass-rc1/` e `.claude/plans/PLAN-169/repass-ga/`, mais as condições
   do envelope assinado `.claude/governance/pair-rail-verdict-v1.4.0.md`. O envelope assinado do
   GA v1.4.2 (`.claude/governance/pair-rail-verdict-v1.4.2.md`) já o declarou aberto, e esta
   release não declara curado nenhum daqueles itens. Arquivos citados por aqueles vereditos
   mudam nesta faixa (`v1.4.2..candidato`); pela forma, estão entre os sítios de versão que o
   bump reescreve, o texto de release e de documentação, os templates de settings,
   `scripts/upgrade.sh` e `scripts/install.sh`, os workflows de CI e de release
   (`.github/workflows/`), o código de hooks (`.claude/hooks/`, fora dos testes), os testes e
   harnesses de teste (`**/tests/**`, fora deste re-pass) e o contrato deste repositório
   (`CLAUDE.md`, não entregue). Esta condição não afirma que cada achado siga reproduzível linha a
   linha: afirma que nenhum é declarado curado.
2. **O que o envelope assinado do GA v1.4.2 declarou aberto segue sem cura declarada.** Aquele
   envelope declarou abertos os itens das condições dele — que carregam as da `v1.4.2-rc.1` e,
   pelas condições 13 e 14 dele, os três P1 do anexo assinado da `v1.4.2-rc.1` e os P2 dos quatro
   vereditos daquela rc — e, de todo veredito que ele ou o envelope da `v1.4.2-rc.1` pina pelo
   MANIFEST da evidência (cujo sha256 o envelope carrega), os achados sob «NEW FINDINGS (annex)»
   e os P2. Esta release não declara curado nenhum deles. Esta condição não afirma que nada mudou
   na faixa: afirma que esta release não os declara curados.

## B. O que muda para o adopter

3. **O pair-rail roda no Codex que o manifesto ADR-182 pina: 0.160.0 nesta release.** Os dois
   arquivos de pin (`.claude/governance/codex-cli-pin.txt` e `codex-cli-pin-manifest.json`)
   mudaram sob cerimônia assinada própria (`.claude/plans/PLAN-194/codex-pin-0160/`) e ficam fora
   deste re-pass (condição 6). O revisor deste re-pass é a versão que o manifesto pina no momento
   do run, e só pela rota 1 do runner (decisão D-4 do PLAN-194): o binário global, depois de o
   oráculo do pair-rail-gate conferir o sha256 do payload nativo contra o manifesto sem
   executá-lo; a rota 2 (`npx` num cache próprio) é recusa nomeada, sem download nem execução.
   A PROVENANCE registra a versão, a rota e o sha256 do payload verificado.
4. **A rc prova o toolchain do publish sem publicar.** No `.github/workflows/npm-publish.yml`, o
   job `rc-toolchain-proof` («RC toolchain proof (no publish)») roda só nas tags `-rc.` (`if:
   contains(github.ref, '-rc.')`), com `permissions` só `contents: read` — sem `id-token`, sem
   `environment` e sem `secrets.` — e nenhum passo dele chama `npm publish`; o job do publish
   segue pulando as tags `-rc.`. O passo 18 do `OWNER-RC1-CUT.sh` exige `success` nesse job, pelo
   nome, além do job do gate. O que ele NÃO prova: a troca do token OIDC e a escrita no registry,
   que só acontecem no GA.

## C. Escopo deste re-pass

5. **Quatro partes, por raio de dano ao adopter, sobre o delta `v1.4.2..candidato`.** Todo
   caminho que muda nessa faixa está em exatamente uma parte ou numa classe declarada fora
   (condição 6); a sonda confere isso antes do codex, com as pathspecs do próprio runner, e
   confere que cada parte cabe no teto do redator com folga de 16 KiB.
6. **Fora do re-pass, pela forma**, com o motivo em
   `.claude/plans/PLAN-194/repass-rc1/README-rc1.md`: testes, fixtures e harnesses de teste
   (`**/tests/**`); `.claude/plans/**` e `docs/research/**`; `CLAUDE.md`;
   `.claude/governance/**` — nesta faixa, no máximo os dois arquivos de pin do Codex (condição 3)
   e o manifesto ADR-192 dos gates; `.claude/scripts/local/**` — nesta faixa, no máximo o
   `release.sh`; `.claude/adr/**`, texto de decisão; dados de oráculo (`.claude/data/**`,
   `.claude/scripts/data/**`); e `scripts/local/**`, harness de smoke do mantenedor.
'''


def derive_cond(src: str) -> str:
    if not src.startswith(COND_SRC_FIRST):
        die("as condicoes de origem nao sao as da v1.4.2-rc.1 (primeira linha)")
    for a in COND_SRC_ANCHORS:
        if src.count(a) != 1:
            die("as condicoes de origem sem a ancora %r" % a)
    title = COND_TITLE
    note = ""
    if RELEASE_CONTENT != "final":
        title += " — " + PROVISIONAL_MARK
        note = COND_PROVISIONAL_NOTE
    t = title + "\n" + note + COND_BODY
    forbid(t, "condicoes", ["OQ-", "Opus 5.5", "FN-04", "PLAN-193/repass-rc1/probe"])
    need(t, "condicoes", ["`v1.4.2..candidato`", "decisão D-4 do PLAN-194", RC_PROOF_JOB_NAME,
                          "`.claude/plans/PLAN-194/repass-rc1/probe-conditions-rc1.py`"])
    return t


README_SRC_FIRST = "<!-- Material do kit de corte da v1.4.2-rc.1 (PLAN-193)."
README_SRC_ANCHORS = ("## 2. As quatro partes, na ordem de risco para o adopter",
                      "## 5. Critério de parada (proposto por este kit, fixado ANTES da 1.ª rodada)",
                      "## 7. Codex pinado, sem tocar na máquina")

README_BODY = '''<!-- Material do kit de corte da v1.4.3-rc.1 (PLAN-194). Este arquivo é rastreado ANTES do
     candidato e não muda no commit do veredito: o guard de delta o recusaria por nome. -->

# Re-pass do candidato v1.4.3-rc.1 — escopo, o que fica de fora e critério de parada
%(note)s
## 1. O que é esta release

Release de MANUTENÇÃO sobre o GA v1.4.2 (PLAN-194): o pair-rail no Codex 0.160.0 (re-pin
assinado), a prova do toolchain do npm nas tags `-rc.` (um job que nunca publica) e os demais
lands do trem — o `audit_log` e os hooks, o workflow de CI, CLIs do mantenedor e documentação.
O candidato é o commit do bump, sobre os lands do trem (a ordem está no LEDGER do PLAN-194).

Nenhum tamanho é digitado aqui: a sonda das condições (`--sizes`) projeta cada parte com as
funções do PRÓPRIO runner — pathspec, rótulo, cobertura e cabeçalho do prompt — e recusa, no G0
do `OWNER-RC1-CUT.sh`, no passo 5 e no runner, uma parte acima de `MAX_RAW_BYTES - 16 KiB`
(o teto do redator é 262.144 bytes sobre o INPUT; o runner recusa a partir de 262.000).

## 2. As quatro partes, na ordem de risco para o adopter

| parte | o que é | por que nesta ordem |
|---|---|---|
| 1 | `templates/**`, `.claude/settings.json`, `.claude/agents/**`, `scripts/**` fora de `scripts/local/`, `.claude/hooks/_lib/agent_frontmatter.py`, `.claude/hooks/_lib/effective_config.py`, `.claude/scripts/env-inventory.json`, `.github/**` (o `validate.yml` e o `npm-publish.yml`, com o job da prova do toolchain da rc), o texto de release (`CHANGELOG.md`, `INSTALL.md`, `SUPPORT.md`, `README*.md`, `npm/**`) e os sítios de versão do bump — sempre fora de `**/tests/**` | é o que decide com que modelo, esforço e hooks a sessão do adopter abre, por onde a instalação e o upgrade chegam lá, e o pipeline que publica o pacote que ele instala |
| 2 | `.claude/hooks/**` fora dos testes e dos dois arquivos da parte 1 | é o código que RODA na sessão do adopter (o `audit_log` e a cadeia de auditoria, os adapters, os auxiliares de `_lib/`) |
| 3 | `.claude/scripts/**` fora dos testes, de `local/`, de `data/` e do `env-inventory.json`; `.claude/commands/**` e `.claude/skills/**` | ferramentas e comandos: a maior parte roda quando o operador a chama, e algumas rodam também chamadas por um hook ou pelo CI entregue ao adopter; nenhum destes arquivos é hook, instalação, upgrade ou settings (partes 1 e 2) |
| 4 | `docs/**` fora de `docs/research/` | a documentação entregue; separada da parte 3 pelo tamanho |

### O manifesto de cada parte é DERIVADO, nunca uma lista fixa

A pathspec acima é a INTENÇÃO; `paths-rc1-N.manifest.txt` é derivado dela contra o candidato no
momento do run (`git diff --name-only --no-renames v1.4.2..candidato -- <pathspec>`, com as
exclusões da própria pathspec). Os sítios de versão só mudam no commit do bump, que é o candidato:
uma lista medida antes esqueceria exatamente eles. As partes são disjuntas, e todo caminho da
faixa fora delas cai numa classe da §4 — a sonda confere as duas coisas com as funções do runner
(`part_pathspec` e `out_of_scope_pathspec`).

## 3. Cobertura anterior, citada dentro do próprio prompt

Pela forma, sem lista de lands: em cada parte, os arquivos que uma cerimônia assinada pelo Owner
mudou nesta faixa landaram sob ela, com rail próprio; os demais landaram livres, com testes, e
esta é a primeira revisão cruzada deles numa release. Os sítios de versão (parte 1) são escritos
pelo `release.sh bump` e não têm rail próprio.

## 4. O que fica FORA, e por quê

| fora | motivo |
|---|---|
| testes, fixtures e harnesses de teste (`**/tests/**`) | não são entregues como produto; são o oráculo, e o oráculo roda no CI do candidato |
| `.claude/plans/**`, `docs/research/**` | registro de trabalho; não são entregues |
| `CLAUDE.md` | contrato de operação DESTE repositório; o adopter recebe `templates/CLAUDE.md` (parte 1, se mudar) |
| `.claude/governance/**` | nesta faixa, no máximo os dois arquivos de pin do Codex (re-pin 0.160.0, cerimônia assinada própria em `PLAN-194/codex-pin-0160/`) e o manifesto ADR-192 dos gates (muda com os gates que as cerimônias tocam) |
| `.claude/scripts/local/**` | nesta faixa, no máximo o `release.sh` (o bloco por-release, na cerimônia própria da relmeta); engenharia de release |
| `.claude/adr/**` | texto de decisão |
| `.claude/data/**`, `.claude/scripts/data/**` | dados de oráculo (reds esperados, baseline do censo do instalador) |
| `scripts/local/**` | harness de smoke do mantenedor |

## 5. Critério de parada (proposto por este kit, fixado ANTES da 1.ª rodada)

- `NO-GO` só por condição declarada FALSA contra o código ou por P0. Um P1 não declarado vai para
  «NEW FINDINGS (annex)» e entra no material assinado.
- No máximo DUAS rodadas de re-pass. Se a 2.ª ainda der `NO-GO`, PARAR e levar as duas ao Owner.
  Não há 3.ª rodada por conta própria.
- Uma condição FALSA contra o código não chega ao codex: a sonda a recusa no G0, no passo 5 e no
  runner. A cura é no código ou no texto (`derive-kit-143.py`), com um candidato novo.
- Uma parte morta por capacidade do modelo (sem veredito, com a assinatura do servidor numa linha
  `ERROR:` do próprio codex no fim do transcript) NÃO é uma rodada: o runner a re-tenta até 2
  vezes e a PROVENANCE declara quantas mortes houve. Uma parte morta pelo LIMITE DE USO da CONTA
  Codex também não é rodada: o runner não a re-tenta, não lança parte nova, a PROVENANCE a declara
  (com a hora de reset, quando o codex a imprime) e o passo 6 dá a rota. Um runner morto por
  infraestrutura também não é rodada.
- Toda tentativa, completa ou parcial, é preservada — e FORA do repositório: o G0 recusa arquivo
  não rastreado no plano fora da evidência deste corte, e o runner recusa rodar sobre evidência
  anterior. O passo 6 do `OWNER-RC1-CUT.sh` diz a rota: um diretório novo em
  `$HOME/.ceo-rc1-archive/` (`repass-rc1-<data>-NOGO-rN/`, ou `-capacidade/` / `-cota/` /
  `-infra/`), com o `.cut-state` junto só no NO-GO. O diretório arquivado entra no plano no
  closeout, depois do corte.
- O passo 16 grava `repass-rc1/.tag-push-epoch` (o piso do passo 19), que o git não ignora: ele
  entra no plano no mesmo closeout (como o do corte da v1.4.2-rc.1). Até lá, o G0 de um corte
  seguinte o recusa pelo nome, com a rota.

## 6. As condições declaradas

`CONDITIONS-rc1.md`, neste diretório. Elas viajam em TODAS as partes como DADO para o revisor, e o
snapshot bruto que ele viu (`CONDITIONS-rc1.reviewed.md`) é o que entra nos fields assinados —
mudar uma vírgula depois da revisão exige novo re-pass. A dívida carregada (o anexo P1 da v1.4.0
e o que o GA v1.4.2 declarou aberto) está re-declarada nas condições 1 e 2.

## 7. Codex pinado, sem tocar na máquina

O runner lê a versão de `.claude/governance/codex-cli-pin-manifest.json` no momento do run (a
0.160.0, depois do re-pin) e tem UMA rota nesta release (decisão D-4 do PLAN-194): o binário
global, quando o oráculo do pair-rail-gate (`check_pair_rail.py --verify-codex-pin`, fail-CLOSED)
confere o sha256 do payload nativo contra o manifesto SEM executá-lo — e só então ele responde a
versão pinada. A rota 2 da v1.4.2 (`npx` num cache próprio) executava o pacote baixado antes de
verificar; aqui ela é recusa nomeada, sem download nem execução, e a recusa diz a rota: o codex
pinado instalado globalmente. Um shim vai no início do PATH. A PROVENANCE registra a rota usada.
O modelo vai por `-m`, lido da tabela raiz de `~/.codex/config.toml` ou de `CODEX_MODEL`, e a
PROVENANCE registra o valor e a origem.

## 8. A base e o candidato

A base é a tag `v1.4.2` (o GA, cortado em 2026-09-30): o runner e o G0 a RESOLVEM (tag anotada;
assinatura verificada, com o signatário em `.claude/sentinel-signers.txt`; o mesmo objeto no
remoto; ancestral do candidato) e recusam pelo nome quando ela não existe. O candidato é o HEAD de
`origin/main` gravado em `CANDIDATE.sha` depois do CI verde — o commit do bump (`release: v1.4.3`),
pelo passo 5 do `OWNER-RC1-CUT.sh`, ou pelo CEO quando ele roda o re-pass antes da cerimônia (o
passo 6 reconhece a evidência completa e não re-roda). O runner nunca lê o candidato de uma
constante, e o commit do veredito senta DIRETAMENTE sobre o candidato: `parent_sha` == pai do
commit que introduz o veredito.

## 9. A sonda das condições

`probe-conditions-rc1.py` confere cada afirmação sobre código das condições contra um commit,
pelo conteúdo do commit (`git show`): a dívida carregada pelos envelopes assinados da v1.4.2 e
pelos vereditos que eles pinam (condições 1 e 2), o pin do Codex e a rota única do runner
(condição 3), o job da prova do toolchain da rc no `npm-publish.yml` (condição 4), e a partição,
com as funções do próprio runner (condições 5 e 6). Roda no G0 (contra o HEAD), no passo 5 e no
runner (contra o candidato), e a saída do runner entra no MANIFEST (`probe-rc1.txt`), com a linha
MAPA que diz que ids conferem cada condição. `RC1_PROBE_REPORT_ONLY=1` existe só para o harness:
o corte e o runner seguem, a PROVENANCE declara a sonda vermelha e o gerador do envelope recusa
essa evidência.
'''

README_PROVISIONAL_NOTE = '''
> **%s.** O texto desta release (§1, §3 e a partição) é verdadeiro contra o HEAD em que o
> kit foi derivado no K1 (PLAN-194 W7), com a W4 projetada; a derivação final (KIT) o completa e
> retira esta nota.
''' % PROVISIONAL_MARK


def derive_readme(src: str) -> str:
    if not src.startswith(README_SRC_FIRST):
        die("o README de origem nao e o da v1.4.2-rc.1 (primeira linha)")
    for a in README_SRC_ANCHORS:
        if src.count(a) != 1:
            die("o README de origem sem a ancora %r" % a)
    note = README_PROVISIONAL_NOTE if RELEASE_CONTENT != "final" else ""
    t = README_BODY % {"note": note}
    forbid(t, "README", ["npx num cache próprio (`.npx-cache/`", "derive-kit-142", "Opus 5.5"])
    need(t, "README", ["`derive-kit-143.py`", "`v1.4.2`", "decisão D-4 do PLAN-194"])
    return t


GITIGNORE_OLD = ("# Arquivos de TRABALHO do runner do re-pass (nunca evidencia): o passo 11 do\n"
                 "# OWNER-RC1-CUT.sh stageia so uma lista literal (o MANIFEST-rc1.sha256 e o que\n"
                 "# ele lista, o README, as condicoes, os fields e o envelope), mas um\n"
                 "# `git add -A` de qualquer outra mao levaria o cache do npx junto.\n"
                 ".npx-cache/\n")
GITIGNORE_NEW = ("# Arquivos de TRABALHO do runner do re-pass (nunca evidencia): o passo 11 do\n"
                 "# OWNER-RC1-CUT.sh stageia so uma lista literal (o MANIFEST-rc1.sha256 e o que\n"
                 "# ele lista, o README, as condicoes, os fields e o envelope), mas um\n"
                 "# `git add -A` de qualquer outra mao levaria o shim, o estado do corte e os\n"
                 "# payloads raw junto. (Sem a rota 2 do codex nao ha mais cache do npx.)\n")


def derive_gitignore(src: str) -> str:
    t = sub(src, GITIGNORE_OLD, GITIGNORE_NEW, ".gitignore")
    need(t, ".gitignore", [".codex-shim/\n", ".cut-state\n", "*.raw.txt\n"])
    forbid(t, ".gitignore", [".npx-cache/"])
    return t


# ===========================================================================
# gerador de fields + envelope
# ===========================================================================
GEN_DOC_START = '"""Gera verdict-fields + envelope pair-rail-verdict para a v1.4.3-rc.1 a\n'
GEN_DOC_END = '"""\nfrom __future__ import annotations\n'
GEN_DOC = r'''"""Gera verdict-fields + envelope pair-rail-verdict para a v1.4.3-rc.1 a
partir da evidencia CORRENTE em repass-rc1/. Fail-CLOSED em toda checagem
(nunca `assert`: PYTHONOPTIMIZE apagaria o gate). Uso:

  python3 gen-envelope-rc1.py --stage fields --parent <sha40> \\
      --conditions-file <md>          # OBRIGATORIO se algum rail = GWC
  # -> Owner: gpg --detach-sign --armor verdict-fields-v1.4.3-rc.1.md
  python3 gen-envelope-rc1.py --stage envelope --sig <.asc>
  python3 gen-envelope-rc1.py --stage verify --sig <.asc>  # retomada, sem escrita

DERIVADO por .claude/plans/PLAN-194/derive-kit-143.py do gerador da v1.4.2-rc.1
(PLAN-193/gen-envelope-rc1.py; fonte e sha256 em SOURCES, no derivador), com a cura do
gerador do GA v1.4.2 (o relatorio da sonda conferido): TAG, diretorio de plano, envelope
precedente (o GA v1.4.2) e a prosa do review record sao os da v1.4.3-rc.1. NAO edite a
mao. Duas propriedades herdadas:

  1. `codex_cli` NAO vem de `codex --version`. A versao vem da linha
     `- codex:` da PROVENANCE, que o runner escreve a partir do pin que ele
     proprio VERIFICOU, e este gerador re-valida contra a faixa do
     `codex-cli-pin.txt` e contra o manifesto ADR-182 antes de escrever — a
     MESMA checagem que o step 15 do release.yml faz sobre o envelope.
  2. `SIGNER_FPR` nao e uma constante digitada. Ele e DERIVADO de duas
     fontes independentes — o fingerprint dentro da assinatura do envelope
     PRECEDENTE e o registro `.claude/sentinel-signers.txt` — e as duas
     TEM de concordar.

E duas que a v1.4.2 ja carregava (a segunda, completada no GA v1.4.2):

  3. `tool_versions.claude_code` e MEDIDO no --stage fields (`claude --version`
     da maquina que gera os fields, rodado fora do repo; recusa nomeada se ausente
     ou ilegivel) — a VERSAO do Claude Code CLI, nao o modelo. Na verificacao
     (envelope e verify) o valor ASSINADO e conservado, como o generated_at: um
     auto-update do Claude Code entre o --stage fields e o --stage verify nao
     invalida a assinatura.
  4. A sonda das condicoes VERDE contra o candidato. O gerador le a linha da
     PROVENANCE e o RELATORIO (probe-rc1.txt, pinado pelo MANIFEST), e as duas
     fontes TEM de concordar: a linha na forma exata que o runner escreve com a
     sonda em rc 0; o relatorio sem linha FAIL/INFRA, terminando na unica linha
     `SONDA: 0 FALSA(S), 0 sem medida`, com cada verificacao da sonda do kit
     (PROBE_IDS: os ids da lista CHECKS da sonda, pinados ao derivar e conferidos
     contra a sonda derivada) numa linha OK exatamente uma vez e nenhuma linha OK
     de outro id, a arvore (C0-tree) DESTE candidato, a projecao de tamanho de
     exatamente as partes do re-pass, a unica linha MAPA com esses mesmos ids e o
     numero de linhas OK que a PROVENANCE declara. Evidencia de um run em modo
     REPORT-ONLY do harness, ou relatorio vazio, vermelho, de outro candidato ou
     parcial, e recusa nomeada — nunca vira fields.

Demais derivacoes, todas dos artefatos REAIS e nunca digitadas: inputs_hash
pela funcao do proprio validador; MANIFEST-rc1 verificado; transcript_hash =
sha256 da concatenacao ordenada dos transcripts; parent VINCULADO ao
candidato do runner/PROVENANCE; a DECISAO agregada e DERIVADA dos rails;
as CONDICOES entram nos FIELDS (material assinado); assinatura VERIFICADA
antes de embutir; escrita atomica sem seguir symlink. stdlib only, >= 3.9.
'''

GEN_PROBE_START = 'PROBE_LINE_RE = r"^- sonda das condicoes: (.*)$"\n'
GEN_PROBE_END = "def build_fields(parent: str, conditions_text: str, generated_at: Optional[str] = None,\n"
GEN_PROBE = r'''PROBE_LINE_RE = r"^- sonda das condicoes: (.*)$"
# A linha que o runner (fase 3b) escreve quando a sonda sai rc 0; o numero vem de
# `grep -c '^OK '` sobre o PROPRIO relatorio.
PROBE_LABEL_RE = r"verde \(([1-9][0-9]*) linhas OK, nenhuma FALSA; probe-rc1\.txt\)"
PROBE_REPORT = "probe-rc1.txt"
PROBE_GREEN_TAIL = "SONDA: 0 FALSA(S), 0 sem medida"
PROBE_TREE_RE = r"OK   C0-tree: arvore == ([0-9a-f]{12}); "
PROBE_SIZE_RE = r"OK   SIZE parte ([0-9]+): "
PROBE_ID_RE = r"OK   ([^\s:]+): "
PROBE_MAP_PREFIX = "MAPA condicao -> ids: "
PROBE_MAP_ITEM_RE = r"(cabecalho|[0-9]+): ([^\s:;]+(?: [^\s:;]+)*)"
# Os ids das verificacoes da sonda do kit (a lista CHECKS de probe-conditions-rc1.py),
# PINADOS pelo derivador, que recusa derivar se nao forem exatamente os ids da sonda
# derivada. Num relatorio verde, cada um esta numa linha OK exatamente uma vez.
PROBE_IDS = (
    %(probe_ids)s
)


def probe_refuse(why: str) -> None:
    die("o relatorio da sonda das condicoes (%%s, no MANIFEST) %%s — evidencia que nao prova "
        "a sonda VERDE contra o candidato, nunca de release" %% (PROBE_REPORT, why))


def probe_green(prov: str, cand: str) -> None:
    """A sonda das condicoes ficou VERDE contra ESTE candidato (runner, fase 3b).

    Duas fontes, que TEM de concordar: a linha da PROVENANCE, na forma exata que o
    runner escreve com a sonda em rc 0, e o PROPRIO relatorio probe-rc1.txt, pinado
    pelo MANIFEST (verify_manifest ja conferiu os bytes). Do relatorio, lido pelas
    linhas como o `grep -c` do runner as conta: nenhuma linha FAIL/INFRA (as formas de
    afirmacao FALSA e de sem medida); a ultima linha e `SONDA: 0 FALSA(S), 0 sem
    medida` e e a unica linha SONDA; o numero de linhas OK e o que a PROVENANCE
    declara; toda linha OK e de uma verificacao de PROBE_IDS ou de projecao de
    tamanho, e cada verificacao de PROBE_IDS esta numa linha OK exatamente uma vez
    (nenhuma ausente, repetida ou de outro id); a linha OK da arvore (C0-tree) nomeia
    ESTE candidato; ha uma linha OK de projecao de tamanho para cada parte do re-pass,
    e so para elas; e a unica linha MAPA mapeia exatamente os ids de PROBE_IDS e SIZE.
    Relatorio ausente, vazio, vermelho, de outro candidato ou de um run parcial (uma
    verificacao que nao rodou, ou repetida no lugar de outra): recusa nomeada."""
    lines = re.findall(PROBE_LINE_RE, prov, re.M)
    if len(lines) != 1 or not lines[0].startswith("verde ("):
        die("a PROVENANCE nao diz que a sonda das condicoes ficou verde contra o candidato "
            "(%%r) — evidencia de ensaio (REPORT-ONLY) ou de um runner trocado, nunca de release"
            %% (lines[0] if lines else None))
    label = re.fullmatch(PROBE_LABEL_RE, lines[0])
    if not label:
        die("a linha da sonda das condicoes na PROVENANCE (%%r) nao tem a forma que o runner "
            "escreve com a sonda em rc 0 — runner trocado ou linha editada, nunca de release"
            %% lines[0])
    path = EV / PROBE_REPORT
    if path.is_symlink() or not path.is_file():
        probe_refuse("esta ausente ou nao e arquivo regular")
    try:
        text = path.read_bytes().decode("utf-8")
    except UnicodeError:
        probe_refuse("nao e UTF-8 valido")
    rows = text.split("\n")
    if rows and rows[-1] == "":
        rows.pop()
    bad = [r for r in rows if r.startswith(("FAIL", "INFRA"))]
    if bad:
        probe_refuse("tem %%d linha(s) de afirmacao FALSA ou sem medida, a primeira: %%r"
                     %% (len(bad), bad[0][:160]))
    if not rows or rows[-1] != PROBE_GREEN_TAIL:
        probe_refuse("nao termina em %%r (ultima linha: %%r)"
                     %% (PROBE_GREEN_TAIL, rows[-1][:160] if rows else None))
    if [r for r in rows if r.startswith("SONDA")] != [PROBE_GREEN_TAIL]:
        probe_refuse("tem mais de uma linha SONDA")
    oks = [r for r in rows if r.startswith("OK ")]
    if len(oks) != int(label.group(1)):
        probe_refuse("tem %%d linha(s) OK e a PROVENANCE declara %%s"
                     %% (len(oks), label.group(1)))
    seen = {}  # type: Dict[str, int]
    sizes = []  # type: List[int]
    for r in oks:
        size = re.match(PROBE_SIZE_RE, r)
        if size:
            sizes.append(int(size.group(1)))
            continue
        cid = re.match(PROBE_ID_RE, r)
        if not cid or cid.group(1) not in PROBE_IDS:
            probe_refuse("tem uma linha OK que nao e de verificacao da sonda do kit nem de "
                         "projecao de tamanho (%%r)" %% r[:160])
        seen[cid.group(1)] = seen.get(cid.group(1), 0) + 1
    missing = [i for i in PROBE_IDS if i not in seen]
    if missing:
        probe_refuse("nao tem a linha OK de %%d verificacao(oes) da sonda do kit (%%s): run "
                     "parcial ou sonda trocada" %% (len(missing), ", ".join(missing)))
    repeated = [i for i in PROBE_IDS if seen[i] != 1]
    if repeated:
        probe_refuse("repete a linha OK de %%s: cada verificacao da sonda conta UMA vez"
                     %% ", ".join(repeated))
    trees = [re.match(PROBE_TREE_RE, r) for r in oks if r.startswith("OK   C0-tree: ")]
    if len(trees) != 1 or trees[0] is None or trees[0].group(1) != cand[:12]:
        probe_refuse("nao confere a arvore DESTE candidato (%%s): linha OK C0-tree ausente, "
                     "repetida ou de outro commit" %% cand[:12])
    if sorted(sizes) != PARTS:
        probe_refuse("nao projeta o tamanho de exatamente as partes %%r (linhas OK SIZE das "
                     "partes %%r)" %% (PARTS, sorted(sizes)))
    maps = [r for r in rows if r.startswith("MAPA")]
    if len(maps) != 1 or not maps[0].startswith(PROBE_MAP_PREFIX):
        probe_refuse("nao tem exatamente uma linha %%r (tem %%d linha(s) MAPA)"
                     %% (PROBE_MAP_PREFIX.rstrip(), len(maps)))
    mapped = set()
    for item in maps[0][len(PROBE_MAP_PREFIX):].split("; "):
        pair = re.fullmatch(PROBE_MAP_ITEM_RE, item)
        if not pair:
            probe_refuse("tem a linha MAPA fora da forma que a sonda escreve (item %%r)"
                         %% item[:80])
        mapped.update(pair.group(2).split(" "))
    want = set(PROBE_IDS) | {"SIZE"}
    if mapped != want:
        probe_refuse("tem a linha MAPA com outros ids que os da sonda do kit (a mais: %%s; "
                     "ausentes: %%s)" %% (sorted(mapped - want), sorted(want - mapped)))


'''
GEN_PROBE_CALL_OLD = "    probe_green(prov)\n"
GEN_PROBE_CALL_NEW = "    probe_green(prov, cand)\n"

GEN_RECORD_START = '        "- Contexto: release expressa sobre o GA v1.4.2 (PLAN-194): Claude Opus 5.5",\n'
GEN_RECORD_END = '        "- Pipeline: prompt + diff atraves do redator ADR-114 como UM pipeline;",\n'
GEN_RECORD = r'''        "- Contexto: release de manutencao sobre o GA v1.4.2 (PLAN-194): o",
        "  pair-rail no Codex 0.160.0, a prova do toolchain do npm nas tags -rc.",
        "  (um job que nunca publica) e os demais lands do trem. O re-pass cobre o",
        "  delta em %d partes por raio de dano ao adotante; o que fica de fora" % NPARTS,
        "  esta DECLARADO em %s/repass-rc1/README-rc1.md — nao omitido." % PLAN,
        "- Divida carregada, RE-DECLARADA nas condicoes (material assinado): o anexo",
        "  P1 do envelope da v1.4.0 segue aberto, sem versao prometida para a cura;",
        "  o que o envelope do GA v1.4.2 declarou aberto (o anexo assinado da",
        "  v1.4.2-rc.1 e os P2 dos vereditos que os envelopes pinam entre eles) segue",
        "  sem cura declarada.",
        "- Antes do codex, cada afirmacao sobre codigo das condicoes foi conferida",
        "  contra o candidato pela sonda do kit (probe-rc1.txt, no MANIFEST); este",
        "  gerador recusa evidencia sem a sonda VERDE na PROVENANCE e no relatorio.",
        "- tool_versions.claude_code e a versao do Claude Code CLI MEDIDA por",
        "  `claude --version` na maquina que gerou os fields; nao e o modelo.",
        "- Cada parte cita, dentro do proprio prompt, a revisao que aquele conteudo",
        "  ja teve, para que uma condicao possa nomear a cobertura em vez de tratar",
        "  o conteudo como inedito.",
        "- Reviewer: codex-cli na versao que o manifesto ADR-182 pina — so pela",
        "  rota 1 (PLAN-194 D-4): o binario global, com o payload nativo VERIFICADO",
        "  contra o manifesto antes de executar; a rota do npx e recusa nomeada —;",
        "  versao, triple e sha256 do payload estao em tool_versions e sao",
        "  re-validados por este gerador.",
'''


def derive_gen(src: str) -> str:
    t = shift(src, "gerador")
    t = cut_region(t, GEN_DOC_START, GEN_DOC_END, GEN_DOC, "docstring do gerador")
    ids = ",\n    ".join(", ".join('"%s"' % i for i in PROBE_IDS[k:k + 5]) for k in range(0, len(PROBE_IDS), 5))
    t = cut_region(t, GEN_PROBE_START, GEN_PROBE_END, GEN_PROBE % {"probe_ids": ids + ","}, "sonda no gerador")
    t = sub(t, GEN_PROBE_CALL_OLD, GEN_PROBE_CALL_NEW, "chamada da sonda")
    t = cut_region(t, GEN_RECORD_START, GEN_RECORD_END, GEN_RECORD, "review record")
    forbid(t, "gerador", ["Opus 5.5", "FN-04", "OQ-3", "senao npx", "derive-kit-142"])
    need(t, "gerador", ['PLAN = ".claude/plans/PLAN-194"', 'TAG = "v1.4.3-rc.1"',
                        'PRECEDENT = GOV / "pair-rail-verdict-v1.4.2.md"', "def probe_green(prov: str, cand: str)",
                        "## Review record - re-pass do CANDIDATO v1.4.3-rc.1 (advisory input)"])
    return t


# ===========================================================================
# corte (OWNER-RC1-CUT.sh)
# ===========================================================================
# Literais de HISTORIA na fonte (o que aconteceu num corte anterior): nao se deslocam.
CUT_PROTECT = [
    ("matou a 1.a tentativa da v1.4.1-rc.1", 2),
    ("(licao da 1.a tentativa da v1.4.1-rc.1)", 1),
    ("candidato da v1.4.1-rc.1 e matou a 3.a tentativa", 1),
    ("v1.4.1-rc.1 entrou em 4606c3df", 1),
    ("Desde a relmeta-142 a sonda chama o gpg com", 1),
    ("A relmeta-142 poe `--yes` no gpg", 1),
]

CUT_HEAD_START = "# OWNER-RC1-CUT.sh — corte da v1.4.3-rc.1 em UM comando (PLAN-194).\n"
CUT_HEAD_END = "#  (c) a SONDA das condicoes verde contra o HEAD:"
CUT_HEAD = r'''# OWNER-RC1-CUT.sh — corte da v1.4.3-rc.1 em UM comando (PLAN-194).
#
#   bash .claude/plans/PLAN-194/OWNER-RC1-CUT.sh [--restamp] [--from <1-20>] [--until <1-20>] [--g0-only]
#
# CEREMONY-LINT: handwritten-exception: DERIVADO por
# .claude/plans/PLAN-194/derive-kit-143.py do script de corte da v1.4.2-rc.1 (fonte e
# sha256 em SOURCES, no derivador; o molde foi escrito contra o corpus
# `.claude/plans/PLAN-188/ceremony-defect-corpus-S348.md`), com as curas que o kit do
# GA v1.4.2 acrescentou depois do kit da rc.1 dele. NAO edite a mao. Ensaiado por
# test-rc1-kit.sh.
#
# PRE-REQUISITOS (a ordem do trem, PLAN-194):
#  (a) o GA v1.4.2 CORTADO (2026-09-30): a tag v1.4.2 existe, anotada e assinada, local e
#      no remoto — ela e a BASE deste re-pass. O G0 confere e recusa pelo nome se ela nao
#      existe.
#  (b) os lands da 1.4.3 em main, pushados e com CI verde: os livres (entre eles ESTE
#      kit, commitado — o G0 confere), o re-pin do Codex 0.160.0, a W4 (o job da prova do
#      toolchain da rc no npm-publish.yml; sem ele o G0 recusa nomeando o job) e a
#      relmeta-143, que poe o driver na 1.4.3 (sem ela o G0 recusa nomeando o pack).
'''

CUT_ENTER6_OLD = "#   Enter       passo 7   ler as condicoes que entram no material assinado\n"
CUT_ENTER6_NEW = ("#   Enter       passo 6   SO se o re-pass tiver de rodar com OPENAI_API_KEY no ambiente (o\n"
                  "#                         aviso diz; rode este script com  unset OPENAI_API_KEY)\n"
                  "#   Enter       passo 7   ler as condicoes que entram no material assinado\n")
CUT_NPMDOC_OLD = ("# A rc NAO publica no npm: o npm-publish.yml pula tags com `-rc.`; o passo 18 confere\n"
                  "# so o controle positivo do gate (o job «Await release-gate» = success).\n")
CUT_NPMDOC_NEW = ("# A rc NAO publica no npm: o job do publish do npm-publish.yml pula tags com `-rc.`; o\n"
                  "# passo 18 confere, PELO NOME, o controle positivo do gate (o job «Await release-gate» =\n"
                  "# success) e a prova do toolchain da rc (o job «RC toolchain proof (no publish)» =\n"
                  "# success), que a W4 do PLAN-194 acrescentou e que nunca publica.\n")

CUT_VARS_OLD = 'KEY="CFCFACF00335DC74"\n'
CUT_VARS_NEW = ('KEY="CFCFACF00335DC74"\n'
                '# O job da rc que a W4 acrescentou ao npm-publish.yml: o passo 18 exige success nele PELO\n'
                '# NOME (o `name:` que `gh run view --json jobs` devolve), e o G0 recusa um HEAD sem ele.\n'
                'RC_PROOF_JOB="RC toolchain proof (no publish)"\n')

CUT_BASEDOC_OLD = "# --- a BASE: a tag do GA v1.4.2, resolvida (nunca pinada: ela nasce na manha) ----\n"
CUT_BASEDOC_NEW = "# --- a BASE: a tag do GA v1.4.2, resolvida (nunca pinada: vale o objeto do momento) ----\n"
CUT_BASEDIE_OLD = ('    || die "a tag base $BASE_TAG nao existe neste repositorio: o GA v1.4.2 ainda nao foi cortado\n'
                   '(.claude/plans/PLAN-193/OWNER-GA-CUT.sh), ou falta: git fetch origin tag $BASE_TAG"\n')
CUT_BASEDIE_NEW = ('    || die "a tag base $BASE_TAG nao existe neste repositorio: falta git fetch origin tag $BASE_TAG\n'
                   '(o GA v1.4.2 foi cortado em 2026-09-30)"\n')

# Dois guards novos do G0, antes da conferencia do kit: o job da W4 (o passo 18 exige success
# nele pelo nome) e o `.gen-*.tmp` orfao de um gerador morto (R3C-01, com a rota).
CUT_NEWFUNCS_ANCHOR = "# --- a SONDA das condicoes contra um commit ----------------------------------\n"
CUT_NEWFUNCS = r'''# --- o job da prova do toolchain da rc (W4) no npm-publish.yml -------------------
# O passo 18 exige `success` nele PELO NOME, e ele so roda depois do push da tag: sem ele
# na arvore que a tag vai levar, o corte morreria no passo 18 com a tag ja publica. Antes do
# passo 15 a arvore e o HEAD; depois, a da tag.
assert_rc_proof_job() {
  local _ref _wf _v
  _ref="HEAD"
  if done_step 15; then _ref="$TAG^{commit}"; fi
  _wf="$(mktemp)" || die "mktemp falhou"
  git show "$_ref:.github/workflows/npm-publish.yml" > "$_wf" 2>/dev/null \
    || { rm -f "$_wf"; die "o npm-publish.yml nao existe em $_ref (git show falhou)"; }
  _v="$(python3 - "$_wf" "$RC_PROOF_JOB" <<'PYRCJ'
import re, sys
wf = open(sys.argv[1], encoding="utf-8").read()
m = re.search(r"(?m)^  rc-toolchain-proof:[ \t]*\n", wf)
if not m:
    print("o job rc-toolchain-proof nao existe")
    sys.exit(0)
rest = wf[m.end():]
nxt = re.search(r"(?m)^  [A-Za-z0-9_-]+:[ \t]*$|^[^ \t\n#]", rest)
blk = wf[m.start():m.end() + (nxt.start() if nxt else len(rest))]
names = re.findall(r"(?m)^    name:[ \t]*(.+?)[ \t]*$", blk)
ifs = re.findall(r"(?m)^    if:[ \t]*(.+?)[ \t]*$", blk)
if names != [sys.argv[2]]:
    print("o job rc-toolchain-proof se chama %r" % names)
elif ifs != ["contains(github.ref, '-rc.')"]:
    print("o job rc-toolchain-proof nao roda so nas tags -rc. (if: %r)" % ifs)
else:
    print("OK")
PYRCJ
)" || { rm -f "$_wf"; die "conferencia do job da prova do toolchain da rc falhou"; }
  rm -f "$_wf"
  [ "$_v" = "OK" ] || die "o npm-publish.yml de $_ref nao tem o job «${RC_PROOF_JOB}» (id rc-toolchain-proof, if: contains(github.ref, '-rc.')): $_v.
O passo 18 exige success nele PELO NOME, e ele so roda depois do push da tag. A W4 do
PLAN-194 ainda nao landou (ou o job mudou de nome: re-derive o kit com o nome novo):
lande-a, pushe, espere o CI verde e re-rode este script."
  printf '   OK: o npm-publish.yml de %s tem o job «%s» (so nas tags -rc.)\n' "$_ref" "$RC_PROOF_JOB"
}

# --- o `.gen-*.tmp` orfao de um gerador do envelope MORTO (R3C-01) ---------------
# O gerador escreve os fields (no plano) e o envelope (em .claude/governance/) por um
# temporario `.gen-*.tmp` no MESMO diretorio, e o apaga em todo erro que ele trata; morto
# por sinal (kill -9, a janela fechada no meio da escrita) ele o deixa para tras, e ali ele
# e um arquivo NAO rastreado que o G0 e o `release.sh tag` recusam — sem rota. Aqui ele e
# nomeado, com a rota: nunca e evidencia (o gerador re-escreve os fields e o envelope do
# zero no passo que os gera), e sai do repositorio SEM ser apagado.
assert_no_gen_orphans() {
  local _o _l=""
  for _o in "$PLAN_DIR"/.gen-*.tmp .claude/governance/.gen-*.tmp; do
    if [ -e "$_o" ] || [ -L "$_o" ]; then _l="$_l $_o"; fi
  done
  [ -z "$_l" ] || die "temporario de um gerador do envelope MORTO no meio da escrita:$_l
Nao e evidencia: o gerador re-escreve os fields e o envelope do zero no passo que os gera.
Tire-o do repositorio (sem apagar) e re-rode este script (ele retoma do passo em que parou):
  mkdir -p $ARCHIVE_ROOT/gen-orfaos && mv --$_l $ARCHIVE_ROOT/gen-orfaos/"
  printf '   OK: nenhum .gen-*.tmp orfao de um gerador morto\n'
}

# --- a rota 1 do codex, antes do runner (PLAN-194 D-4) --------------------------
# O runner so resolve o codex pela rota 1 (o binario global com o payload que o oraculo
# ADR-182 confere) e recusa a rota 2 pelo nome. Conferir o ORACULO aqui — sem executar o
# codex — evita uma tentativa parcial a arquivar so porque o codex global nao e o pinado.
assert_route1_available() {
  local _g
  _g="$(command -v codex 2>/dev/null)" || _g=""
  [ -n "$_g" ] || die "rota 1 indisponivel: nenhum codex no PATH. A rota 2 (npx) e recusa nomeada nesta release
(PLAN-194 D-4). Instale globalmente a versao que o manifesto ADR-182 pina (a do re-pin
assinado; nunca npm update -g) e re-rode este script (ele retoma do passo 6). Nada foi rodado."
  CLAUDE_PROJECT_DIR="$ROOT" python3 "$ROOT/.claude/hooks/check_pair_rail.py" --verify-codex-pin "$_g" >/dev/null 2>&1 \
    || die "rota 1 indisponivel: o payload do codex global ($_g) NAO confere com o manifesto ADR-182.
A rota 2 (npx) e recusa nomeada nesta release (PLAN-194 D-4). Instale globalmente a versao
que o manifesto pina (a do re-pin assinado; nunca npm update -g), confira com
  python3 .claude/hooks/check_pair_rail.py --verify-codex-pin \"\$(command -v codex)\"
e re-rode este script (ele retoma do passo 6). Nada foi rodado: nenhuma tentativa a arquivar."
  printf '   rota 1: o payload do codex global confere com o manifesto ADR-182 (conferido sem executa-lo)\n'
}

'''

CUT_G0CALLS_OLD = "assert_kit_committed\nassert_no_foreign_cut_residue\n"
CUT_G0CALLS_NEW = "assert_no_gen_orphans\nassert_kit_committed\nassert_no_foreign_cut_residue\n"
CUT_G0RC_OLD = ("if ! done_step 15; then\n"
                "  assert_release_scope_covers_log\n"
                "  assert_claude_md_fits\n"
                "fi\n")
CUT_G0RC_NEW = ("if ! done_step 15; then\n"
                "  assert_release_scope_covers_log\n"
                "  assert_claude_md_fits\n"
                "fi\n"
                "# O job da W4 na arvore que a tag leva (o HEAD antes do 15; a tag depois): o passo 18\n"
                "# exige success nele pelo nome. Ate o passo 18 concluido.\n"
                "if ! done_step 18; then\n"
                "  assert_rc_proof_job\n"
                "fi\n")

CUT_STEP6_START = "    printf 'O codex roda na versao que o manifesto ADR-182 pina: o binario global, se for\\n'\n"
CUT_STEP6_END = "  fi\n  bell \"re-pass GO nas 4 partes\"\n"
CUT_STEP6 = r'''    printf 'O codex roda na versao que o manifesto ADR-182 pina, SO pela rota 1 (PLAN-194 D-4):\n'
    printf 'o binario global, com o payload conferido pelo oraculo antes de executar. Nada e instalado.\n'
    assert_route1_available
    # A cota da CONTA Codex: foi o limite de uso DA CONTA (nao a capacidade do modelo)
    # que matou duas das tres partes de uma tentativa do pre-run do re-pass do GA v1.4.1
    # (2026-09-25; LEDGER do PLAN-192); o re-pass que serviu ao corte foi outro.
    printf '\nAVISO — a COTA DA CONTA Codex: o re-pass roda as 4 partes ao mesmo tempo e GASTA a\n'
    printf 'cota da conta do codex. Com ela esgotada, a parte morre sem veredito com uma\n'
    printf 'linha do codex que comeca com «ERROR:» (numa tentativa do pre-run do GA v1.4.1,\n'
    printf 'em 2026-09-25, ela dizia «hit your usage limit ... try again at 4:43 PM»): e\n'
    printf 'LIMITE DE USO DA CONTA, nao capacidade do modelo; o runner a separa e nao a\n'
    printf 're-tenta (a rota esta na recusa deste passo). O re-pass deve autenticar o codex\n'
    printf 'pela CONTA (o login em ~/.codex/auth.json), sem a chave: rode este script\n'
    printf 'com  unset OPENAI_API_KEY.\n'
    if [ -n "${OPENAI_API_KEY:-}" ]; then
      bell "OPENAI_API_KEY no ambiente antes do re-pass"
      printf '\nOPENAI_API_KEY ESTA neste ambiente. ctrl-C, rode  unset OPENAI_API_KEY  e re-rode\n'
      printf 'este script (ele retoma do passo 6). Enter segue COM ela: '
      read -r _ || die "sem terminal para o Enter do passo 6 (OPENAI_API_KEY no ambiente): rode  unset OPENAI_API_KEY  e re-rode este script (ele retoma do passo 6)"
    fi
    RC1_CODEX_JOBS="${RC1_CODEX_JOBS:-4}" bash "$RUNNER" || die "o re-pass NAO terminou GO nas 4 partes. Leia $EV/PROVENANCE-rc1.md (se existir).
Preserve a tentativa, inclusive parcial, FORA do repositorio: o G0 recusa arquivo nao
rastreado no plano fora da evidencia deste corte, e o runner recusa rodar sobre evidencia
anterior. Crie um diretorio NOVO em $ARCHIVE_ROOT/ e mova para ele os arquivos NAO
rastreados de $EV/, menos o CANDIDATE.sha (fica; copie-o). Liste-os com:
  git status --porcelain --untracked-files=all -- $EV/
O runner, a sonda, as condicoes, o README e o .gitignore sao rastreados e FICAM. O
diretorio arquivado entra no plano no closeout, depois do corte (nunca durante o freeze)
e sem o $STATE.
(a) NO-GO (a linha VERDICT: NO-GO em algum $EV/verdict-rc1-N.txt): PARE — nao ha 2.a
rodada por conta propria. Diretorio: $ARCHIVE_ROOT/repass-rc1-$(date +%Y%m%d)-NOGO-r1/
Mova para la TAMBEM o $STATE (ignorado pelo git, por isso fora da lista): sem ele a
proxima tentativa recomeca do passo 1. Leve ao Owner (me chame no Claude).
(b) Sem NO-GO e com parte SEM veredito, ou o runner morto antes do codex: morte por
CAPACIDADE do modelo (a PROVENANCE diz) ou por INFRAESTRUTURA (rede, git, gpg, a sonda
sem medida). Nao e rodada. Diretorio:
  $ARCHIVE_ROOT/repass-rc1-$(date +%Y%m%dT%H%M%S)-capacidade/  (ou -infra/)
MANTENHA o $STATE e o CANDIDATE.sha e re-rode este script: ele retoma do passo 6.
(c) Caso particular de (b), com rota propria: a parte morreu pelo LIMITE DE USO DA
CONTA Codex. O runner o declara na PROVENANCE, com a linha de erro do codex (ela traz
a hora do reset quando o codex a imprime):
  grep -n 'LIMITE DE USO' $EV/PROVENANCE-rc1.md
Nao e rodada nem capacidade do modelo. Diretorio:
  $ARCHIVE_ROOT/repass-rc1-$(date +%Y%m%dT%H%M%S)-cota/
MANTENHA o $STATE e o CANDIDATE.sha, espere a hora do reset (ou recarregue a cota da
conta) e re-rode este script, com  unset OPENAI_API_KEY : ele retoma do passo 6.
(d) Caso particular de (b): o runner recusou «rota 1 indisponivel» (o codex global deixou
de ser o pinado entre a conferencia deste passo e o runner). Diretorio -infra/ como em (b);
instale globalmente a versao que o manifesto pina e re-rode: ele retoma do passo 6.
Qualquer outro caso (veredito ambiguo, main que andou, sonda com afirmacao FALSA): me
chame no Claude."
'''

CUT_S11DOC_OLD = ("  # das releases anteriores. O que autoriza o\n"
                  "  # conteudo e a assinatura GPG DENTRO dele, verificada pelo step 15 do\n"
                  "  # release.yml e pelo guard local do passo 12.\n")
CUT_S11DOC_NEW = ("  # das releases anteriores. O que liga os BYTES dele a assinatura GPG e so o\n"
                  "  # gerador (passos 10 e 11): ele verifica a assinatura contra os fields e monta\n"
                  "  # o envelope como funcao pura dos fields, da assinatura e do fingerprint. Nada\n"
                  "  # a jusante refaz essa ligacao: o step 15 do release.yml confere que\n"
                  "  # gpg_signature EXISTE (nao que ela assina estes bytes), o guard local do\n"
                  "  # passo 12 confere o delta, e a assinatura da tag (passo 15; git tag --verify\n"
                  "  # no release.yml) cobre a arvore commitada, nao a origem dela. Por isso o\n"
                  "  # envelope que este passo commita e RE-DERIVADO logo antes do staging (abaixo),\n"
                  "  # nunca tomado da arvore.\n")
CUT_S11_ANCHOR = "  # O .asc sai da arvore (o passo 15 recusa arquivo nao rastreado) SO agora, depois\n"
CUT_S11_BLOCK = r'''  # O envelope RE-DERIVADO dos fields assinados, depois dos guards de HEAD e do index
  # e antes de o .asc sair da arvore: numa retomada entre os passos 10 e 11 o $VD da
  # arvore e um untracked que nada liga a assinatura. Se ele diferia do derivado, e
  # substituido — e e o derivado que o staging abaixo leva ao commit.
  _vd_prev=""
  if [ -f "$VD" ] && [ ! -L "$VD" ]; then
    _vd_prev="$(mktemp)" || die "mktemp falhou"
    cp -- "$VD" "$_vd_prev" || die "copiar o envelope da arvore ($VD) falhou"
  fi
  python3 "$GEN" --stage envelope --sig "$VF.asc" \
    || die "re-derivar o envelope dos fields assinados falhou (nada foi commitado; o .asc segue na arvore) — me chame no Claude"
  [ -f "$VD" ] && [ ! -L "$VD" ] || die "o envelope re-derivado nao e arquivo regular: $VD"
  if [ -n "$_vd_prev" ]; then
    if ! cmp -s -- "$_vd_prev" "$VD"; then
      printf '   AVISO: o envelope da arvore (%s) DIFERIA do derivado dos fields assinados: substituido pelo derivado, que e o que entra no commit\n' "$VD"
    fi
    rm -f "$_vd_prev"
  fi
  printf '   envelope re-derivado dos fields assinados (a assinatura re-verificada): %s\n' "$VD"
'''

CUT_MSG_START = "governance(PLAN-194): verdito pair-rail $TAG assinado + evidencia do re-pass\n"
CUT_MSG_END = "MSG\n"
CUT_MSG = r'''governance(PLAN-194): verdito pair-rail $TAG assinado + evidencia do re-pass

Decisao agregada DERIVADA dos 4 rails; as condicoes, quando existem, fazem
parte do material assinado (sub-mapa conditions: dos fields) — entre elas a
re-declaracao da divida carregada: o anexo P1 do envelope da v1.4.0 segue
aberto, sem versao prometida para a cura, e o que o envelope do GA v1.4.2
declarou aberto (o anexo assinado da v1.4.2-rc.1 e os P2 dos vereditos que
os envelopes pinam entre eles) segue sem cura declarada.
Antes do codex, cada afirmacao sobre codigo das condicoes foi conferida
contra o candidato pela sonda do kit (probe-rc1.txt, no MANIFEST).
tool_versions.codex_cli vem da PROVENANCE do run PINADO e e re-validado
contra codex-cli-pin.txt e contra o manifesto ADR-182 pela funcao do proprio
validador — nunca de 'codex --version' desta maquina; tool_versions.claude_code
e MEDIDO por 'claude --version' ao gerar os fields.

Evidencia do re-pass no MESMO commit: quatro partes, ordenadas por raio de
dano ao adotante, sobre o delta v1.4.2..$CAND. Reviewer: codex-cli na versao
que o manifesto ADR-182 pina, so pela rota 1 (PLAN-194 D-4): o binario
global, com o payload nativo verificado contra o manifesto antes de executar
(a rota esta na PROVENANCE). Escopo coberto e o que ficou de fora:
repass-rc1/README-rc1.md. Payloads raw NAO commitados; pins em
PROVENANCE-rc1.md. O release.yml exige parent_sha == pai do commit que
introduz o veredito, e o guard local exige o veredito dentro do delta
candidato..tag: um commit so satisfaz os dois.
'''

CUT_S16_OLD = ("  printf 'npm-publish.yml, que PULA tags -rc.: nada vai ao npm; so o job do gate roda la\\n'\n"
               "  printf '(o controle positivo do passo 18). O comando que sera executado:\\n\\n'\n")
CUT_S16_NEW = ("  printf 'npm-publish.yml, cujo job do publish PULA tags -rc.: nada vai ao npm; rodam la o\\n'\n"
               "  printf 'job do gate e o da prova do toolchain da rc (os controles positivos do passo 18).\\n'\n"
               "  printf 'O comando que sera executado:\\n\\n'\n")

CUT_S18_START = "if should 18; then\n"
CUT_S18_END = "if should 19; then\n"
CUT_S18 = r'''if should 18; then
  say "18/20 npm-publish: o gate e a prova do toolchain da rc, pelo nome (a rc nao publica)"
  _repo="$(gh repo view --json nameWithOwner --jq .nameWithOwner 2>/dev/null || echo "")"
  printf '   Numa tag -rc. o npm-publish.yml roda o job do gate («Await release-gate») e o da prova\n'
  printf '   do toolchain («%s»); o publish e pulado. Painel dos runs:\n' "$RC_PROOF_JOB"
  [ -n "$_repo" ] && printf '     https://github.com/%s/actions/workflows/npm-publish.yml\n' "$_repo"
  TAGSHA="$(git rev-parse "$TAG^{commit}")"
  i=0
  while :; do
    i=$((i+1)); [ "$i" -le 60 ] \
      || die "os jobs do npm-publish.yml (o gate e a prova do toolchain) nao concluiram em 60 min — re-rode este script (ele retoma do passo 18)"
    sleep 60
    NID="$(gh run list --workflow npm-publish.yml --limit 10 \
      --json headSha,databaseId,headBranch,event \
      --jq "[.[]|select(.headSha==\"$TAGSHA\" and .headBranch==\"$TAG\" and .event==\"push\")][0].databaseId" 2>/dev/null || echo "")"
    if [ -z "$NID" ] || [ "$NID" = "null" ]; then
      printf '  ... o run do npm-publish ainda nao apareceu (ou o gh falhou; tentando de novo)\n'; continue
    fi
    # Separador `|`: o estado do run, a conclusao do gate, quantos jobs tem o NOME da prova
    # do toolchain e a conclusao dela — uma conclusao VAZIA (em andamento) nao desloca os
    # campos. O nome e comparado EXATO (o `name:` do job), nunca por prefixo.
    _j18="$(gh run view "$NID" --json status,jobs \
      --jq '(.status // "") + "|" + ([.jobs[]|select(.name|startswith("Await release-gate"))][0].conclusion // "") + "|" + ([.jobs[]|select(.name == "'"$RC_PROOF_JOB"'")]|length|tostring) + "|" + ([.jobs[]|select(.name == "'"$RC_PROOF_JOB"'")][0].conclusion // "")' 2>/dev/null || echo "")"
    if [ -z "$_j18" ]; then
      printf '  ... gh run view %s falhou (tentando de novo)\n' "$NID"; continue
    fi
    _rs="$(printf '%s' "$_j18" | awk -F'|' '{print $1}')"
    AC="$(printf '%s' "$_j18" | awk -F'|' '{print $2}')"
    PN="$(printf '%s' "$_j18" | awk -F'|' '{print $3}')"
    PC="$(printf '%s' "$_j18" | awk -F'|' '{print $4}')"
    printf '  ... await-release-gate: %s; prova do toolchain: %s\n' "${AC:-pendente}" "${PC:-pendente}"
    if [ -n "$AC" ] && [ "$AC" != "null" ] && [ "$AC" != "success" ]; then
      die "await-release-gate terminou '$AC' (run $NID do npm-publish.yml).
Se o release.yml da tag foi re-rodado ate o verde (passo 17), esta recusa e a do run
anterior e nao volta sozinha: rode gh run rerun $NID --failed, espere, e re-rode este
script (ele retoma do passo 18). Senao: me chame no Claude."
    fi
    if [ "$_rs" = "completed" ] && [ "$PN" = "0" ]; then
      die "o run $NID do npm-publish.yml terminou SEM o job «${RC_PROOF_JOB}» — o passo 18 exige
success nele PELO NOME. O npm-publish.yml da tag nao tem o job da W4 (o G0 o conferiu antes
da tag: o nome mudou?). A tag ja esta publica: me chame no Claude."
    fi
    if [ -n "$PC" ] && [ "$PC" != "null" ] && [ "$PC" != "success" ]; then
      die "a prova do toolchain da rc («${RC_PROOF_JOB}») terminou '$PC' (run $NID do npm-publish.yml).
Ela nao espera o gate e nunca publica: leia o run com gh run view $NID --log-failed.
Vermelho de infraestrutura (runner, rede): gh run rerun $NID --failed, espere e re-rode
este script (ele retoma do passo 18). Vermelho no toolchain (versao do node ou do npm,
staging, packlist, npm pack --dry-run): o GA publicaria com o MESMO toolchain — me chame
no Claude ANTES do GA."
    fi
    [ "$AC" = "success" ] && [ "$PC" = "success" ] && break
  done
  printf '   controle positivo do gate do npm e prova do toolchain da rc: verdes\n'
  mark_step 18
fi

'''


def derive_cut(src: str) -> str:
    t = shift(src, "corte", CUT_PROTECT)
    t = cut_region(t, CUT_HEAD_START, CUT_HEAD_END, CUT_HEAD, "cabecalho do corte")
    t = sub(t, CUT_ENTER6_OLD, CUT_ENTER6_NEW, "Enter do passo 6")
    t = sub(t, CUT_NPMDOC_OLD, CUT_NPMDOC_NEW, "doc do npm")
    t = sub(t, CUT_VARS_OLD, CUT_VARS_NEW, "RC_PROOF_JOB")
    t = sub(t, CUT_BASEDOC_OLD, CUT_BASEDOC_NEW, "doc da base")
    t = sub(t, CUT_BASEDIE_OLD, CUT_BASEDIE_NEW, "recusa da base ausente")
    t = sub(t, CUT_NEWFUNCS_ANCHOR, CUT_NEWFUNCS + CUT_NEWFUNCS_ANCHOR, "guards novos do G0")
    t = sub(t, CUT_G0CALLS_OLD, CUT_G0CALLS_NEW, "chamada do guard de orfaos")
    t = sub(t, CUT_G0RC_OLD, CUT_G0RC_NEW, "chamada do guard do job da W4")
    t = cut_region(t, CUT_STEP6_START, CUT_STEP6_END, CUT_STEP6, "passo 6")
    t = sub(t, CUT_S11DOC_OLD, CUT_S11DOC_NEW, "doc do passo 11")
    t = sub(t, CUT_S11_ANCHOR, CUT_S11_BLOCK + CUT_S11_ANCHOR, "envelope re-derivado no passo 11")
    t = cut_region(t, CUT_MSG_START, CUT_MSG_END, CUT_MSG, "mensagem do commit do veredito")
    t = sub(t, CUT_S16_OLD, CUT_S16_NEW, "texto do passo 16")
    t = cut_region(t, CUT_S18_START, CUT_S18_END, CUT_S18, "passo 18")
    forbid(t, "corte", ["derive-kit-142", "Opus 5.5", "FN-04", "OQ-3", "senao por npx",
                        "so o job do gate roda la", "rede, npx, git"])
    need(t, "corte", ['PLAN_DIR=".claude/plans/PLAN-194"', 'TAG="v1.4.3-rc.1"', 'BASE="1.4.3"',
                      'BASE_TAG="v1.4.2"', "$PLAN_DIR/derive-kit-143.py $PLAN_DIR/test-rc1-kit.sh",
                      "A relmeta-143 ainda nao landou: assine e lande o pack .claude/plans/PLAN-194/relmeta/",
                      "matou a 1.a tentativa da v1.4.1-rc.1", "A relmeta-142 poe `--yes` no gpg",
                      "release: v1.4.3", "assert_rc_proof_job\n", "assert_no_gen_orphans\n",
                      "  assert_route1_available\n", 'RC_PROOF_JOB="%s"' % RC_PROOF_JOB_NAME])
    return t


# ===========================================================================
# harness (test-rc1-kit.sh)
# ===========================================================================
# Literais de HISTORIA (a relmeta-142 pos o --yes) e o Scope SINTETICO da secao SC (o plano
# "novo" da fixture e o PLAN-194: o RELEASE_SCOPE da fixture tem de seguir sem ele).
TEST_PROTECT = [
    ("como antes da relmeta-142", 1),
    ("(a relmeta-142 landou, ou a projecao a simula)", 1),
    ("a relmeta-142 nao esta aqui", 1),
    ('RELEASE_SCOPE="PLAN-190 / PLAN-193 (ADRs tocados: nenhum)"', 1),
    ('"plan(PLAN-193): kit"', 1),
    ('"plan(PLAN-193): adr"', 1),
]

# Renome GA -> rc1 dos blocos TRANSPLANTADOS do harness do GA v1.4.2 (curas do GA).
GA_TO_RC1 = [
    ("probe-conditions-ga.py", "probe-conditions-rc1.py"),
    ("gen-envelope-ga.py", "gen-envelope-rc1.py"),
    ("run-ga-repass.sh", "run-rc1-repass.sh"),
    ("OWNER-GA-CUT.sh", "OWNER-RC1-CUT.sh"),
    ("repass-ga", "repass-rc1"),
    ("MANIFEST-ga", "MANIFEST-rc1"),
    ("PROVENANCE-ga", "PROVENANCE-rc1"),
    ("CONDITIONS-ga", "CONDITIONS-rc1"),
    ("README-ga", "README-rc1"),
    ("probe-ga.txt", "probe-rc1.txt"),
    ("ga_generator", "rc1_generator"),
    (".ceo-ga-archive", ".ceo-rc1-archive"),
    ("-ga-", "-rc1-"),
    ("GAKIT_", "RC1KIT_"),
    ("PLAN-193", "PLAN-194"),
]


def ga_block(start: str, end: str, what: str) -> str:
    t = region(ga("test"), start, end, what)
    for old, new in GA_TO_RC1:
        t = t.replace(old, new)
    t = re.sub(r"(?<![A-Za-z0-9])GA_", "RC1_", t)
    forbid(t, what, ["-ga.", "-ga-", "repass-ga", "GA_CODEX", "OWNER-GA"])
    return t


TEST_HEADER = r'''#!/bin/bash
# CEREMONY-LINT: handwritten-exception: harness do kit de corte da v1.4.3-rc.1, DERIVADO por
# .claude/plans/PLAN-194/derive-kit-143.py do harness da v1.4.2-rc.1 (escrito contra o
# corpus PLAN-188/ceremony-defect-corpus-S348.md), com os controles que o kit do GA v1.4.2
# acrescentou e os da rota 1 so, do passo 18 e dos P2 herdados. NAO edite a mao.
#
# test-rc1-kit.sh — prova a TUBULACAO inteira do kit sem gastar uma unica
# invocacao de codex e sem tocar na arvore viva.
#
#   bash .claude/plans/PLAN-194/test-rc1-kit.sh
#   bash .claude/plans/PLAN-194/test-rc1-kit.sh --evidence-only
#
# Dois modos, decididos pelo DISCO:
#   K1  — a arvore tem o derivador e este harness, e NENHUMA das outras sete saidas do kit
#         (o estado do K1 do PLAN-194 W7: os derivadores landam antes das saidas). O harness
#         NAO roda contra ela: clona-a (HEAD + derivador e harness do disco) num diretorio
#         DESCARTAVEL do scratch, prova que o derivador recusa pelo nome um HEAD sem o job
#         da W4 e uma escrita do conteudo provisorio sem --provisional, projeta a W4 no clone
#         (o npm-publish.yml de RC1KIT_W4_NPM_PUBLISH, se posto; senao um job MINIMO com o
#         nome, o gatilho e as permissoes que a condicao 4 afirma), deriva o kit la, confere
#         que o harness derivado e byte a byte ESTE arquivo e re-executa o harness derivado
#         no clone. Um kit PARCIAL no disco e recusa.
#   kit — a arvore tem o kit derivado (commitado ou nao): o ensaio completo, abaixo.
#
# Onde roda o modo kit: numa arvore em que os lands da 1.4.3 JA estao (a da manha, depois da
# relmeta-143; ou, antes dela, uma arvore PROJETADA com eles — a do K1). A fixture recria a
# tag base v1.4.2 no upstream DESCARTAVEL, assinada por uma chave descartavel, no commit
# RC1KIT_BASE_REV (padrao: o commit da v1.4.2 real) — nada sai do scratch.
#   RC1KIT_SCRATCH_PARENT  pai do scratch (padrao /tmp; com um pai longo, o homedir GPG
#                          ganha um ALIAS curto em /tmp, removido na saida).
#
# O que ele faz, em ordem:
#   F.  controles de EVIDENCIA do gerador e dos guards do runner (sem GPG nem rede),
#       inclusive o relatorio da sonda conferido pelo gerador (as formas que nao provam a
#       sonda VERDE deste candidato sao recusadas pelo nome — cura do GA v1.4.2);
#   A.  lint estatico: `derive-kit-143.py --check`, `/bin/bash -n` (3.2) + `shellcheck -S
#       warning` nos shells do kit, compilacao EM MEMORIA (sem .pyc) nos pythons, e
#       `check-ceremony-script.py` exigindo ZERO achado BLOCKING nos arquivos do kit; A3 o
#       CENSO deste harness: nenhum controle por AUSENCIA de texto sem pre-condicao de
#       existencia, e nenhuma "recusa nomeada" conferida so pelo codigo de saida (R3H-01 e
#       R3H-02, com controle positivo do proprio censo);
#   K0. a chave GPG DESCARTAVEL (antes do B: ela assina a tag base da fixture);
#   B.  runner ponta a ponta num CLONE descartavel, com um codex STUB (`CODEX_BIN`) e a
#       base resolvida em tempo de run; B2 morte por capacidade (com as iscas do limite de
#       conta fora da janela), B2u o LIMITE DE USO da conta (em serie e numa onda), B2x a
#       morte sem classe; B3 o modelo; B5/B6 a base ausente e a base assinada fora do
#       registro; B7 a ROTA 1 SO (D-4): o lancador plantado nunca executa e a rota 2 e
#       recusa nomeada (contra o runner da v1.4.2, o npx plantado EXECUTA: o controle nao e
#       vacuo), e o ESPIAO prova zero execucao do codex antes do oraculo (contra uma
#       mutacao que executa antes, ele acusa);
#   P.  a SONDA das condicoes contra o candidato da fixture e os controles vermelhos de
#       cada verificacao, pelo NOME;
#   C.  gerador de envelope: fields -> assinatura descartavel -> envelope, com o
#       `claude --version` MEDIDO por um stub;
#   E.  topologia do commit do veredito x os dois gates; o passo 11 verbatim (e as
#       retomadas dele; E3e o envelope adulterado na arvore RE-DERIVADO dos fields
#       assinados, cura do GA v1.4.2, e E3f o mesmo estado contra o passo 11 da v1.4.2-rc.1,
#       que o commita); o bump REAL da rc; o passo 2 verbatim com driver stub;
#   W G K S V Z X Q Y L SC  as curas herdadas, cada uma VERBATIM do OWNER-RC1-CUT.sh com
#       stubs, com o controle vermelho de cada uma; X2-X4 o passo 18 (o gate E a prova do
#       toolchain da rc, pelo nome);
#   R.  o OWNER-RC1-CUT.sh REAL (`--g0-only` e estados de retomada plantados no
#       .cut-state) num clone com remoto bare local e `gh` stub — com um controle de CORTE
#       INTEIRO para cada recusa do G0 que so tinha controle verbatim (R3H-03); T. o mesmo
#       num PSEUDO-TERMINAL;
#   D.  UM CONTROLE VERMELHO por classe do corpus que este kit cura, e o INDICE dos
#       controles vermelhos dos gates novos (cada um tem de ter rodado e ficado verde).
#
# Se a sonda das condicoes nao fica verde na fixture (uma lane ainda nao landou), o P
# REPROVA com as afirmacoes nomeadas, e B/E/R seguem em RC1_PROBE_REPORT_ONLY=1 — so
# para exercitar a tubulacao; o C REPROVA por construcao (o gerador confere o relatorio).
#
# INVARIANTE 8 do PLAN-188 (classe CM-12): este harness NUNCA planta um
# veredito `APPROVE`/`GO` sintetico para destravar um caso verde. O stub do
# codex EMITE `VERDICT: GO-WITH-CONDITIONS` porque e um stub de REVISOR, e essa e a
# saida que um revisor produz; os casos que exercitam RECUSA plantam o defeito e
# esperam recusa.
'''

TEST_HELPERS_OLD = r"""say()  { printf '\n===== %s\n' "$*"; }
"""
TEST_HELPERS_NEW = r"""say()  { printf '\n===== %s\n' "$*"; }
# Controle por AUSENCIA de texto (R3H-01): o arquivo TEM de existir, regular e nao vazio —
# senao a ausencia seria vacua (um log que nem foi escrito "nao tem" nada). rc 0 = presente
# e SEM o padrao; 1 = o padrao esta la; 2 = o arquivo nao existe (ou esta vazio).
lacks() {  # $1 = arquivo; o resto = os argumentos do grep (flags e padrao)
  local _lf="$1"; shift
  [ -f "$_lf" ] && [ ! -L "$_lf" ] && [ -s "$_lf" ] || return 2
  if grep -q "$@" "$_lf"; then return 1; fi
  return 0
}
# Recusa NOMEADA (R3H-02): rc != 0 E o texto da recusa no log; o id vai para o indice _red.
_red=""
refused() {  # $1 = id, $2 = rc, $3 = log, $4 = texto FIXO esperado, $5 = o caso
  if [ "$2" -ne 0 ] && [ -f "$3" ] && grep -qF -- "$4" "$3"; then
    ok "$1 (controle vermelho): $5 — recusa nomeada (rc $2; «$4»)"; _red="$_red $1"
  elif [ "$2" -eq 0 ]; then bad "$1: $5 PASSOU (rc 0)"; sed -n '1,8p' "$3" 2>/dev/null
  else bad "$1: $5 recusado (rc $2) SEM o texto «$4»"; sed -n '1,10p' "$3" 2>/dev/null; fi
}
"""

TEST_K1_ANCHOR = 'say "F. partes estritas, condicoes congeladas e preservacao de tentativa"\n'
TEST_K1 = r'''# ===========================================================================
# MODO K1 — os derivadores sem as saidas (ver o cabecalho).
K1_OUTPUTS="
$PLAN_DIR/OWNER-RC1-CUT.sh
$PLAN_DIR/gen-envelope-rc1.py
$EV/run-rc1-repass.sh
$EV/probe-conditions-rc1.py
$EV/CONDITIONS-rc1.md
$EV/README-rc1.md
$EV/.gitignore
"
_k1_have=0; _k1_miss=0
for _kf in $K1_OUTPUTS; do
  if [ -e "$_kf" ] || [ -L "$_kf" ]; then _k1_have=$((_k1_have + 1)); else _k1_miss=$((_k1_miss + 1)); fi
done
if [ "$_k1_have" -gt 0 ] && [ "$_k1_miss" -gt 0 ]; then
  printf 'kit PARCIAL no disco (%s de 7 saidas): rode derive-kit-143.py (ou tire as saidas) e re-rode\n' "$_k1_have" >&2
  exit 2
fi
if [ "$_k1_have" -eq 0 ]; then
  if [ -n "${RC1KIT_K1_INNER:-}" ]; then
    echo "K1: o harness interno nao achou o kit derivado no clone — recusado (nunca recursao)" >&2
    exit 2
  fi
  say "K1. derivadores sem as saidas: o kit e derivado num CLONE descartavel e este harness re-roda la"
  K1D="$SCRATCH/k1"; K1WT="$K1D/wt"
  _k1_wf=".github/workflows/npm-publish.yml"
  _k1_ok=1
  mkdir -p "$K1D" && git clone --quiet --local --no-hardlinks "$ROOT" "$K1WT" 2>/dev/null \
    && git -C "$K1WT" config --local user.name "rc1 kit K1" \
    && git -C "$K1WT" config --local user.email "rc1-kit-k1@invalid" \
    && git -C "$K1WT" config --local commit.gpgsign false || _k1_ok=0
  # O derivador e este harness vem do DISCO (podem estar nao commitados).
  for _kf in "$PLAN_DIR/derive-kit-143.py" "$PLAN_DIR/test-rc1-kit.sh"; do
    [ "$_k1_ok" -eq 1 ] || break
    if [ ! -f "$ROOT/$_kf" ] || [ -L "$ROOT/$_kf" ]; then bad "K1: $_kf ausente no disco"; _k1_ok=0; break; fi
    mkdir -p "$K1WT/$(dirname "$_kf")" && cp -- "$ROOT/$_kf" "$K1WT/$_kf" || _k1_ok=0
  done
  if [ "$_k1_ok" -eq 1 ]; then ok "K1: clone descartavel de HEAD ($(git -C "$K1WT" rev-parse --short HEAD)) com o derivador e o harness do disco"
  else bad "K1: preparacao do clone descartavel falhou"; fi
  _k1_head="$(git -C "$K1WT" rev-parse HEAD 2>/dev/null)" || _k1_head=""
  _k1_outs_absent() {
    local _o
    for _o in $K1_OUTPUTS; do [ -e "$K1WT/$_o" ] && return 1; done
    return 0
  }
  # K1a — o derivador recusa PELO NOME um HEAD sem o job da W4 (o passo 18 exige success
  # nele). Se o HEAD ja tem o job (a W4 landou), um commit descartavel o tira.
  if [ "$_k1_ok" -eq 1 ]; then
    if python3 - "$K1WT/$_k1_wf" <<'PYK1A' && git -C "$K1WT" commit -q -am "TEST ONLY (K1a): sem o job da W4" 2>/dev/null; then
import re, sys
p = sys.argv[1]
t = open(p, encoding="utf-8").read()
m = re.search(r"(?m)^  rc-toolchain-proof:[ \t]*\n", t)
if not m:
    raise SystemExit(1)
rest = t[m.end():]
nxt = re.search(r"(?m)^  [A-Za-z0-9_-]+:[ \t]*$|^[^ \t\n#]", rest)
open(p, "w", encoding="utf-8").write(t[:m.start()] + (rest[nxt.start():] if nxt else ""))
PYK1A
      :
    fi
    _k1a_rc=0
    ( cd "$K1WT" && python3 "$PLAN_DIR/derive-kit-143.py" --provisional ) > "$K1D/k1a.log" 2>&1 || _k1a_rc=$?
    if _k1_outs_absent; then
      refused K1a "$_k1a_rc" "$K1D/k1a.log" "nao existe no .github/workflows/npm-publish.yml do HEAD" \
        "o derivador sobre um HEAD sem o job da W4 (nenhuma saida escrita)"
    else bad "K1a: o derivador escreveu saidas sobre um HEAD sem o job da W4"; fi
    git -C "$K1WT" reset -q --hard "$_k1_head" || { bad "K1a: reset do clone falhou"; _k1_ok=0; }
  fi
  # A projecao da W4: o npm-publish.yml que RC1KIT_W4_NPM_PUBLISH aponta (o da sombra da W4),
  # ou um job MINIMO com o nome, o gatilho e as permissoes que a condicao 4 afirma.
  if [ "$_k1_ok" -eq 1 ] && ! grep -q '^  rc-toolchain-proof:' "$K1WT/$_k1_wf"; then
    if [ -n "${RC1KIT_W4_NPM_PUBLISH:-}" ]; then
      if [ -f "$RC1KIT_W4_NPM_PUBLISH" ] && [ ! -L "$RC1KIT_W4_NPM_PUBLISH" ] \
         && cp -- "$RC1KIT_W4_NPM_PUBLISH" "$K1WT/$_k1_wf"; then
        _k1_proj="o npm-publish.yml de RC1KIT_W4_NPM_PUBLISH ($(shasum -a 256 "$RC1KIT_W4_NPM_PUBLISH" | cut -c1-12))"
      else bad "K1: RC1KIT_W4_NPM_PUBLISH nao e arquivo regular: $RC1KIT_W4_NPM_PUBLISH"; _k1_ok=0; fi
    else
      printf '%s\n' '' \
        '  # TEST ONLY (K1): projecao MINIMA da W4 do PLAN-194 — o job da prova do toolchain da rc.' \
        '  rc-toolchain-proof:' \
        '    name: RC toolchain proof (no publish)' \
        "    if: contains(github.ref, '-rc.')" \
        '    runs-on: ubuntu-latest' \
        '    permissions:' \
        '      contents: read' \
        '    steps:' \
        '      - name: projecao do ensaio K1 (nunca roda)' \
        '        run: "true"' >> "$K1WT/$_k1_wf" || _k1_ok=0
      _k1_proj="o job MINIMO (nome, gatilho -rc. e contents: read)"
    fi
    if [ "$_k1_ok" -eq 1 ] && git -C "$K1WT" commit -q -am "TEST ONLY (K1): projecao da W4 do PLAN-194" 2>/dev/null; then
      ok "K1: W4 projetada no clone: $_k1_proj"
    else bad "K1: commit da projecao da W4 falhou"; _k1_ok=0; fi
  elif [ "$_k1_ok" -eq 1 ]; then
    ok "K1: o HEAD ja tem o job da W4 (nenhuma projecao)"
  fi
  # A projecao da relmeta-143 (o driver na 1.4.3): TARGET_BASE, o RELEASE_SCOPE DERIVADO dos
  # planos citados nos assuntos de v1.4.2..HEAD e dos ADRs tocados (a mesma regra do G0), e o
  # sha novo do release.sh no manifesto ADR-192 — so se o HEAD ainda nao a tem.
  if [ "$_k1_ok" -eq 1 ] && ! grep -q '^TARGET_BASE="1.4.3"$' "$K1WT/.claude/scripts/local/release.sh"; then
    if ( cd "$K1WT" && python3 - <<'PYK1R'
import hashlib, re, subprocess
def g(*a):
    return subprocess.check_output(["git"] + list(a), universal_newlines=True)
rel = ".claude/scripts/local/release.sh"
man = ".claude/governance/gate-scripts-manifest.txt"
plans = sorted(set(re.findall(r"PLAN-\d{3}", g("log", "--format=%s", "v1.4.2..HEAD"))))
adrs = sorted(set(re.findall(r"ADR-\d{3}", g("diff", "--name-only", "v1.4.2", "HEAD", "--", ".claude/adr/"))))
scope = "%s (ADRs tocados: %s)" % (" / ".join(plans), ", ".join(adrs) or "nenhum")
t = open(rel, encoding="utf-8").read()
t2 = re.sub(r'(?m)^TARGET_BASE="[^"]*"$', 'TARGET_BASE="1.4.3"', t, count=1)
t2 = re.sub(r'(?m)^RELEASE_SCOPE="[^"\n]*"$', lambda m: 'RELEASE_SCOPE="%s"' % scope, t2, count=1)
if t2 == t:
    raise SystemExit(3)
open(rel, "w", encoding="utf-8").write(t2)
sha = hashlib.sha256(t2.encode("utf-8")).hexdigest()
m = open(man, encoding="utf-8").read()
m2 = re.sub(r"(?m)^[0-9a-f]{64}(  \.claude/scripts/local/release\.sh)$", lambda x: sha + x.group(1), m, count=1)
if m2 == m:
    raise SystemExit(4)
open(man, "w", encoding="utf-8").write(m2)
print(scope)
PYK1R
    ) > "$K1D/relmeta.log" 2>&1 && git -C "$K1WT" commit -q -am "TEST ONLY (K1): projecao da relmeta-143 (driver na 1.4.3)" 2>/dev/null; then
      ok "K1: relmeta-143 projetada no clone (TARGET_BASE 1.4.3; Scope $(head -n 1 "$K1D/relmeta.log"))"
    else bad "K1: projecao da relmeta-143 falhou"; sed -n '1,6p' "$K1D/relmeta.log"; _k1_ok=0; fi
  fi
  # K1b — sem --provisional, o conteudo provisorio da release nao e escrito.
  if [ "$_k1_ok" -eq 1 ]; then
    _k1b_rc=0
    ( cd "$K1WT" && python3 "$PLAN_DIR/derive-kit-143.py" ) > "$K1D/k1b.log" 2>&1 || _k1b_rc=$?
    if _k1_outs_absent; then
      refused K1b "$_k1b_rc" "$K1D/k1b.log" "conteudo da release e PROVISORIO" \
        "a escrita do conteudo provisorio sem --provisional (nenhuma saida escrita)"
    else bad "K1b: o derivador escreveu o conteudo provisorio sem --provisional"; fi
  fi
  # K1c — a derivacao no clone; --check; e o harness derivado e ESTE arquivo, byte a byte.
  if [ "$_k1_ok" -eq 1 ]; then
    if ( cd "$K1WT" && python3 "$PLAN_DIR/derive-kit-143.py" --provisional ) > "$K1D/k1c.log" 2>&1 \
       && ( cd "$K1WT" && python3 "$PLAN_DIR/derive-kit-143.py" --check ) > "$K1D/k1c-check.log" 2>&1 \
       && grep -q -- '--check OK (disco == derivado)' "$K1D/k1c-check.log"; then
      ok "K1c: o kit derivado no clone; --check OK (8 saidas)"
    else bad "K1c: derivacao/--check no clone falhou"; sed -n '1,16p' "$K1D/k1c.log" "$K1D/k1c-check.log"; _k1_ok=0; fi
  fi
  if [ "$_k1_ok" -eq 1 ]; then
    if cmp -s -- "$K1WT/$PLAN_DIR/test-rc1-kit.sh" "$ROOT/$PLAN_DIR/test-rc1-kit.sh"; then
      ok "K1c: o harness derivado e byte a byte este arquivo ($(shasum -a 256 "$ROOT/$PLAN_DIR/test-rc1-kit.sh" | cut -c1-12))"
    else bad "K1c: o harness derivado DIFERE deste arquivo — re-derive e copie o test-rc1-kit.sh"; _k1_ok=0; fi
  fi
  # K1d — o harness derivado, no clone (o modo kit).
  _k1_inner_rc=99
  if [ "$_k1_ok" -eq 1 ]; then
    _k1_inner_rc=0
    ( cd "$K1WT" && env RC1KIT_K1_INNER=1 RC1KIT_SCRATCH_PARENT="$SCRATCH_PARENT" \
        bash "$PLAN_DIR/test-rc1-kit.sh" "$@" ) > "$K1D/inner.log" 2>&1 || _k1_inner_rc=$?
    sed 's/^/  | /' "$K1D/inner.log"
    _k1_res="$(awk '/^===== RESULTADO: [0-9]+ PASS, [0-9]+ FAIL$/ { l = $0 } END { print l }' "$K1D/inner.log")"
    if [ "$_k1_inner_rc" -eq 0 ] && [ -n "$_k1_res" ] && printf '%s\n' "$_k1_res" | grep -q ', 0 FAIL$'; then
      ok "K1d: o harness derivado no clone: ${_k1_res#===== }"
    else bad "K1d: o harness derivado no clone saiu rc=$_k1_inner_rc (${_k1_res:-sem a linha RESULTADO})"; fi
  fi
  printf '\n===== RESULTADO K1: %s PASS, %s FAIL\n' "$PASS" "$FAIL"
  [ "$FAIL" -eq 0 ] || exit 1
  exit 0
fi

'''

# A secao F do GA v1.4.2 (o relatorio da sonda conferido pelo gerador), renomeada para a rc.1.
TEST_F_START = 'say "F. partes estritas, condicoes congeladas e preservacao de tentativa"\n'
TEST_F_END = '# ===========================================================================\nsay "A. lint estatico"\n'

# A3 — o censo deste harness (R3H-01/R3H-02 pela FORMA, com controle positivo).
TEST_A3_ANCHOR = '# ===========================================================================\nsay "K0. chave GPG DESCARTAVEL'
TEST_A3 = r'''# >>> censo-A3 (esta secao fica FORA do proprio censo: ela cita as formas que procura)
say "A3. censo deste harness: ausencia sem pre-condicao e recusa nomeada so pelo rc (R3H-01/R3H-02)"
cat > "$SCRATCH/a3.py" <<'PYA3'
import re, sys
CLASSES = {
    # `! grep` cru: a ausencia num arquivo que pode nem existir. O auxiliar `lacks` exige o
    # arquivo; ele mesmo usa `if grep ...; then return 1`.
    "ausencia-sem-pre-condicao": re.compile(r"!\s*grep\s+-q"),
    # `if grep -q ...; then bad`: a PRESENCA reprova, entao a ausencia aprova — a mesma
    # classe pela outra forma.
    "presenca-reprova": re.compile(r"\bif\s+grep\s+-q[A-Za-z]*\s[^\n]*;\s*then\s*\n?\s*bad\b"),
    # um `ok` que promete recusa NOMEADA num `else` direto de `then bad` (so o rc decidiu).
    "nomeada-so-pelo-rc": re.compile(
        r"then\s+bad\s+\"[^\"\n]*\"\s*(?:\n\s*|;\s*)else\s+ok\s+\"[^\"\n]*(?:nomead|NOMEAD|pelo nome)"),
}
rows = open(sys.argv[1], encoding="utf-8").read().split("\n")
keep, skip = [], False
for row in rows:
    # A secao do censo e as linhas de comentario ficam vazias (os numeros de linha seguem).
    if row.startswith("# >>> censo-A3"):
        skip = True
    hide = skip or row.lstrip().startswith("#")
    if row.startswith("# <<< censo-A3"):
        skip = False
    keep.append("" if hide else row)
text = "\n".join(keep)
for name, rx in CLASSES.items():
    hits = [text.count("\n", 0, m.start()) + 1 for m in rx.finditer(text)]
    print("%s %d %s" % (name, len(hits), " ".join(str(h) for h in hits[:8])))
PYA3
_a3="$(python3 "$SCRATCH/a3.py" "$ROOT/$PLAN_DIR/test-rc1-kit.sh" 2>&1)" || _a3="ERRO $_a3"
if printf '%s\n' "$_a3" | awk '$2 != "0" { bad = 1 } END { exit bad }' && [ "$(printf '%s\n' "$_a3" | grep -c ' 0')" = "3" ]; then
  ok "A3: o censo deste harness acha ZERO controle por ausencia sem pre-condicao e ZERO recusa nomeada so pelo rc"
else bad "A3: o censo deste harness achou forma(s) vacua(s): $(printf '%s' "$_a3" | tr '\n' ';')"; fi
{ printf 'if grep -q X "$f" 2>/dev/null; then\n  bad "x"\nelse ok "y"; fi\n'
  printf 'if cmd; then bad "a"\nelse ok "b (controle vermelho): recusa nomeada"; fi\n'
  printf 'x && ! grep -q Y "$g"\n'; } > "$SCRATCH/a3-plant.sh"
_a3p="$(python3 "$SCRATCH/a3.py" "$SCRATCH/a3-plant.sh" 2>&1)" || _a3p="ERRO"
if [ "$(printf '%s\n' "$_a3p" | awk '{print $2}' | tr '\n' ' ')" = "1 1 1 " ]; then
  ok "A3 (controle positivo): o censo acha cada forma plantada (uma de cada classe)"; _red="$_red A3"
else bad "A3: o censo nao achou as formas plantadas ($(printf '%s' "$_a3p" | tr '\n' ';'))"; fi
# <<< censo-A3

'''

TEST_BRAW_OLD = r'''    if ls "$CLONE/$EV"/payload-rc1-*.raw.txt >/dev/null 2>&1; then
      bad "sobrou payload RAW na arvore do clone"
    else ok "nenhum payload RAW na arvore (quarentena funcionou)"; fi
'''
TEST_BRAW_NEW = r'''    if [ ! -d "$CLONE/$EV" ]; then bad "pre-condicao: $CLONE/$EV ausente (a ausencia do RAW seria vacua)"
    elif ls "$CLONE/$EV"/payload-rc1-*.raw.txt >/dev/null 2>&1; then
      bad "sobrou payload RAW na arvore do clone"
    else ok "nenhum payload RAW na arvore (quarentena funcionou)"; fi
'''

TEST_B2_START = 'say "B2. rodada MORTA por capacidade do modelo: re-tentada, e a PROVENANCE declara"\n'
TEST_B2_END = 'say "B3. o modelo vem da tabela RAIZ de ~/.codex/config.toml, ou de CODEX_MODEL, ou e recusa"\n'
TEST_B2_GA_END = ('# ===========================================================================\n'
                  'say "B4. candidato que MUDA a parte 1')
# A ausencia da classe da conta na PROVENANCE do B2 (R3H-01: o arquivo tem de existir).
TEST_B2_ABS_OLD = r'''    if grep -qi 'limite de uso da conta' "$CLONE2/$EV/PROVENANCE-rc1.md" 2>/dev/null; then
      bad "B2: uma morte por capacidade virou limite de uso da conta por uma linha fora da janela ou no meio de uma linha"
    else ok "B2 (controle vermelho): a linha do limite de uso da conta fora da janela de 40 linhas, ou no meio de uma linha, NAO classifica a morte (segue capacidade, re-tentada)"; fi
'''
TEST_B2_ABS_NEW = r'''    if lacks "$CLONE2/$EV/PROVENANCE-rc1.md" -i 'limite de uso da conta'; then
      ok "B2 (controle vermelho): a linha do limite de uso da conta fora da janela de 40 linhas, ou no meio de uma linha, NAO classifica a morte (segue capacidade, re-tentada)"
    else bad "B2: uma morte por capacidade virou limite de uso da conta (ou a PROVENANCE nao existe: lacks rc=$?)"; fi
'''

TEST_B3_OLD = r'''if env -u CODEX_MODEL HOME="$_b3/empty" bash "$_b3/model.sh" >/dev/null 2>&1; then
  bad "B3: sem config e sem ambiente o runner SEGUIU com modelo indefinido"
else ok "B3 (controle vermelho): sem config e sem ambiente e recusa nomeada"; fi
'''
TEST_B3_NEW = r'''_b3c_rc=0
env -u CODEX_MODEL HOME="$_b3/empty" bash "$_b3/model.sh" > "$SCRATCH/b3c.log" 2>&1 || _b3c_rc=$?
refused B3c "$_b3c_rc" "$SCRATCH/b3c.log" "modelo do codex indefinido: exporte CODEX_MODEL=" \
  "sem config e sem ambiente, o modelo indefinido"
'''

# B7 — a rota 1 SO (D-4), antes do P.
TEST_B7_ANCHOR = ('# ===========================================================================\n'
                  'say "P. a sonda das condicoes nao e vacua: os controles VERMELHOS"\n')
TEST_B7 = r'''# ===========================================================================
say "B7. ROTA 1 SO (PLAN-194 D-4): lancador plantado nunca executa, rota 2 recusa nomeada, e o espiao"
# A secao 2 do runner (resolver e VERIFICAR o codex) roda VERBATIM — extraida do runner no
# disco — com um preludio minimo (REPO_ROOT, OUT, CODEX_VER, die). PATH controlado: um
# `codex` plantado e um `npx` ESPIAO que gravam um marcador se executados.
_b7="$SCRATCH/b7"; mkdir -p "$_b7/bin" "$_b7/out" "$_b7/py"
_b7_realpy="$(command -v python3)" || _b7_realpy=""
_b7_realgit="$(command -v git)" || _b7_realgit=""
_b7_sect() {  # $1 = runner, $2 = destino
  { printf '#!/bin/bash\nset -uo pipefail\n'
    printf 'die() { printf "FATAL: %%s\\n" "$*" >&2; exit 1; }\n'
    printf 'REPO_ROOT="$B7_REPO"; OUT="$B7_OUT"\n'
    printf 'PIN_MANIFEST="$REPO_ROOT/.claude/governance/codex-cli-pin-manifest.json"\n'
    printf 'CODEX_VER="$(python3 -c '"'"'import json,sys; print(json.load(open(sys.argv[1]))["package_version"])'"'"' "$PIN_MANIFEST")"\n'
    printf 'CODEX_PKG="@openai/codex@$CODEX_VER"\n'
    awk '/^# --- 2\. resolver e VERIFICAR o codex pinado/{f=1} /^# --- 3\. worktree DETACHED/{f=0} f' "$1"
    printf 'printf "B7-ROTA %%s\\n" "$CODEX_ROUTE"\n'; } > "$2"
}
# O codex PLANTADO: um lancador que, se executado, grava o marcador (nunca deve).
printf '#!/bin/bash\nprintf "EXEC planted %%s\\n" "$*" >> "%s/planted.log"\necho "codex-cli 0.160.0"\n' "$_b7" > "$_b7/bin/codex"
# O npx ESPIAO: se executado (a rota 2 viva), grava o marcador e responde a versao.
printf '#!/bin/bash\nprintf "EXEC npx %%s\\n" "$*" >> "%s/npx.log"\necho "codex-cli 0.160.0"\n' "$_b7" > "$_b7/bin/npx"
chmod 0755 "$_b7/bin/codex" "$_b7/bin/npx"
# Um PATH sem o codex REAL: so os utilitarios do sistema, o python3 e o git (por symlink).
mkdir -p "$_b7/sys"
[ -n "$_b7_realpy" ] && ln -sf "$_b7_realpy" "$_b7/sys/python3"
[ -n "$_b7_realgit" ] && ln -sf "$_b7_realgit" "$_b7/sys/git"
# O gpg tambem: o passo 1 do runner INTEIRO (B7f) verifica a tag base com `git verify-tag`.
_b7_realgpg="$(command -v gpg)" && ln -sf "$_b7_realgpg" "$_b7/sys/gpg"
_b7_path="$_b7/bin:$_b7/sys:/usr/bin:/bin:/usr/sbin:/sbin"
_b7_repo=""
if [ -n "${CLONE:-}" ] && [ -n "${CAND:-}" ] && _clone_cand "$_b7/repo"; then _b7_repo="$_b7/repo"; fi
if [ -n "$_b7_repo" ] && [ -n "$_b7_realpy" ]; then
  _b7_sect "$ROOT/$EV/run-rc1-repass.sh" "$_b7/sect.sh"
  # B7a — o lancador plantado (o payload nao confere com o manifesto): recusa nomeada, e
  # NADA executa — nem o lancador nem o npx.
  rm -f "$_b7/planted.log" "$_b7/npx.log"; _b7a_rc=0
  ( cd "$_b7_repo" && env -u CODEX_BIN -u CLAUDE_PROJECT_DIR PATH="$_b7_path" B7_REPO="$_b7_repo" \
      B7_OUT="$_b7/out" bash "$_b7/sect.sh" ) > "$_b7/b7a.log" 2>&1 || _b7a_rc=$?
  if [ ! -e "$_b7/planted.log" ] && [ ! -e "$_b7/npx.log" ]; then
    refused B7a "$_b7a_rc" "$_b7/b7a.log" "e RECUSA NOMEADA nesta release (PLAN-194 D-4): nada foi baixado nem executado" \
      "o codex global plantado (payload fora do manifesto), sem executar o lancador nem o npx"
    if grep -qF 'rota 1 indisponivel: o payload do codex global' "$_b7/b7a.log"; then
      ok "B7a: a recusa nomeia a causa (o payload do codex global nao confere com o manifesto)"
    else bad "B7a: a recusa nao nomeia a causa"; fi
  else bad "B7a: o lancador plantado ou o npx EXECUTOU ($(cat "$_b7/planted.log" "$_b7/npx.log" 2>/dev/null | tr '\n' ';'))"; fi
  # B7b — o controle nao e vacuo: a secao 2 do runner da v1.4.2 (a rota 2 viva) contra o
  # MESMO PATH executa o npx plantado antes de qualquer verificacao.
  _b7_old="$ROOT/.claude/plans/PLAN-193/repass-rc1/run-rc1-repass.sh"
  if [ -f "$_b7_old" ]; then
    _b7_sect "$_b7_old" "$_b7/sect-old.sh"
    rm -f "$_b7/planted.log" "$_b7/npx.log"
    ( cd "$_b7_repo" && env -u CODEX_BIN -u CLAUDE_PROJECT_DIR PATH="$_b7_path" B7_REPO="$_b7_repo" \
        B7_OUT="$_b7/out-old" bash "$_b7/sect-old.sh" ) > "$_b7/b7b.log" 2>&1 || :
    if [ -s "$_b7/npx.log" ] && [ ! -e "$_b7/planted.log" ]; then
      ok "B7b (controle positivo): contra o runner da v1.4.2 o npx plantado EXECUTA ($(head -n 1 "$_b7/npx.log")) — o espiao do B7a ve a execucao"; _red="$_red B7b"
    else bad "B7b: o npx plantado nao executou contra a rota 2 da v1.4.2 — o B7a seria vacuo"; sed -n '1,6p' "$_b7/b7b.log"; fi
  else bad "B7b: o runner da v1.4.2 ($_b7_old) ausente"; fi
  # B7c — nenhum codex no PATH: recusa nomeada.
  rm -f "$_b7/npx.log"; mkdir -p "$_b7/bin-nocodex"; cp -p "$_b7/bin/npx" "$_b7/bin-nocodex/npx"; _b7c_rc=0
  ( cd "$_b7_repo" && env -u CODEX_BIN -u CLAUDE_PROJECT_DIR PATH="$_b7/bin-nocodex:$_b7/sys:/usr/bin:/bin:/usr/sbin:/sbin" \
      B7_REPO="$_b7_repo" B7_OUT="$_b7/out" bash "$_b7/sect.sh" ) > "$_b7/b7c.log" 2>&1 || _b7c_rc=$?
  if [ ! -e "$_b7/npx.log" ]; then
    refused B7c "$_b7c_rc" "$_b7/b7c.log" "rota 1 indisponivel: nenhum codex no PATH" "sem codex no PATH (o npx espiao nao executa)"
  else bad "B7c: o npx executou sem codex no PATH"; fi
  # B7d — o ESPIAO: um codex com o layout do npm cujo payload o manifesto da fixture pina.
  # O `python3` do PATH registra cada chamada; o lancador registra cada execucao. Zero
  # execucao do codex antes de o oraculo conferir o payload; e ele executa depois (rota 1).
  _b7f="$_b7/npm"; _b7tr="$(PYTHONDONTWRITEBYTECODE=1 "$_b7_realpy" -c 'import sys; sys.path.insert(0, sys.argv[1]); import check_pair_rail as c; print(c._codex_target_triple() or "")' "$_b7_repo/.claude/hooks" 2>/dev/null)" || _b7tr=""
  if [ -n "$_b7tr" ]; then
    _b7rel="@openai/codex-fixture/vendor/$_b7tr/bin/codex"
    mkdir -p "$_b7f/lib/node_modules/@openai/codex/bin" "$_b7f/lib/node_modules/$(dirname "$_b7rel")" "$_b7f/bin" "$_b7/spy"
    printf '#!/bin/bash\nprintf "EXEC codex %%s\\n" "$*" >> "%s/spy.log"\necho "codex-cli 0.160.0"\n' "$_b7" > "$_b7f/lib/node_modules/@openai/codex/bin/codex.js"
    printf 'payload de fixture do B7d (nunca executado)\n' > "$_b7f/lib/node_modules/$_b7rel"
    chmod 0755 "$_b7f/lib/node_modules/@openai/codex/bin/codex.js"
    ln -sf ../lib/node_modules/@openai/codex/bin/codex.js "$_b7f/bin/codex"
    printf '#!/bin/bash\nprintf "PY %%s\\n" "$*" >> "%s/spy.log"\nexec "%s" "$@"\n' "$_b7" "$_b7_realpy" > "$_b7/spy/python3"
    chmod 0755 "$_b7/spy/python3"
    _b7_spy_repo="$_b7/repo-spy"
    if _clone_cand "$_b7_spy_repo" && "$_b7_realpy" - "$_b7_spy_repo/.claude/governance/codex-cli-pin-manifest.json" \
         "$_b7tr" "$_b7rel" "$(shasum -a 256 "$_b7f/lib/node_modules/$_b7rel" | awk '{print $1}')" <<'PYB7D'
import json, sys
p, triple, rel, sha = sys.argv[1:]
d = json.load(open(p, encoding="utf-8"))
d["payloads"] = {triple: {"path": rel, "sha256": sha}}
open(p, "w", encoding="utf-8").write(json.dumps(d, indent=2) + "\n")
PYB7D
    then
      _b7_spycheck() {  # $1 = log do espiao: "ok" se o oraculo vem antes da 1.a execucao
        awk '/^PY .*--verify-codex-pin /{ if (!o) o = NR } /^EXEC codex/{ if (!e) e = NR; n++ }
             END { if (o && e && o < e && n >= 1) print "ok"; else printf "violacao (oraculo=%d exec=%d n=%d)\n", o, e, n }' "$1"
      }
      rm -f "$_b7/spy.log"; _b7d_rc=0
      ( cd "$_b7_spy_repo" && env -u CODEX_BIN -u CLAUDE_PROJECT_DIR PATH="$_b7/spy:$_b7f/bin:$_b7/sys:/usr/bin:/bin:/usr/sbin:/sbin" \
          B7_REPO="$_b7_spy_repo" B7_OUT="$_b7/out-spy" bash "$_b7/sect.sh" ) > "$_b7/b7d.log" 2>&1 || _b7d_rc=$?
      _b7d_v="$(_b7_spycheck "$_b7/spy.log" 2>/dev/null)" || _b7d_v=""
      if [ "$_b7d_rc" -eq 0 ] && [ "$_b7d_v" = "ok" ] \
         && grep -qF 'B7-ROTA binario global (versao pinada, payload verificado)' "$_b7/b7d.log" \
         && grep -qF 'pin VERIFICADO: 0.160.0' "$_b7/b7d.log"; then
        ok "B7d: o espiao prova ZERO execucao do codex antes do oraculo, e a rota 1 executa DEPOIS ($(grep -c '^EXEC codex' "$_b7/spy.log") execucao(oes), todas depois da 1.a conferencia do payload)"; _red="$_red B7d"
      else bad "B7d: rc=$_b7d_rc, espiao: ${_b7d_v:-sem log}"; sed -n '1,12p' "$_b7/b7d.log"; sed -n '1,8p' "$_b7/spy.log" 2>/dev/null; fi
      # B7e — o espiao nao e vacuo: uma mutacao que executa o codex ANTES do oraculo e acusada.
      awk '{ print } /^  _glob="\$\(command -v codex 2>\/dev\/null\)" \|\| _glob=""$/ { print "  \"$_glob\" --version >/dev/null 2>&1 || :" }' \
        "$_b7/sect.sh" > "$_b7/sect-mut.sh"
      rm -f "$_b7/spy.log"
      ( cd "$_b7_spy_repo" && env -u CODEX_BIN -u CLAUDE_PROJECT_DIR PATH="$_b7/spy:$_b7f/bin:$_b7/sys:/usr/bin:/bin:/usr/sbin:/sbin" \
          B7_REPO="$_b7_spy_repo" B7_OUT="$_b7/out-mut" bash "$_b7/sect-mut.sh" ) > "$_b7/b7e.log" 2>&1 || :
      _b7e_v="$(_b7_spycheck "$_b7/spy.log" 2>/dev/null)" || _b7e_v=""
      if ! cmp -s "$_b7/sect.sh" "$_b7/sect-mut.sh" && [ -n "$_b7e_v" ] && [ "$_b7e_v" != "ok" ]; then
        ok "B7e (controle positivo): a mutacao que executa o codex ANTES do oraculo e acusada pelo espiao ($_b7e_v)"; _red="$_red B7e"
      else bad "B7e: o espiao nao acusou a execucao antes do oraculo (mutacao aplicada: $(cmp -s "$_b7/sect.sh" "$_b7/sect-mut.sh" && echo nao || echo sim); espiao: ${_b7e_v:-sem log})"; fi
    else bad "B7d: preparacao do manifesto da fixture do espiao falhou"; fi
  else bad "B7d: a tripla do host nao foi derivada pelo oraculo"; fi
  # B7f — o RUNNER INTEIRO (nao a secao extraida), sem CODEX_BIN, com o codex plantado: a
  # recusa nomeada vem antes de qualquer payload, e nada executa.
  _b7fr="$_b7/repo-full"
  if _clone_cand "$_b7fr"; then
    rm -f "$_b7/planted.log" "$_b7/npx.log"; _b7f_rc=0
    # shellcheck disable=SC2086
    ( cd "$_b7fr" && env -u CODEX_BIN -u CLAUDE_PROJECT_DIR PATH="$_b7_path" CODEX_MODEL=stub-model \
        HOME="$SCRATCH/fakehome-b7f" GNUPGHOME="$GH" $SELFTEST_ENV $PROBE_ENV bash "$EV/run-rc1-repass.sh" ) \
      > "$_b7/b7f.log" 2>&1 || _b7f_rc=$?
    if [ ! -e "$_b7/planted.log" ] && [ ! -e "$_b7/npx.log" ] \
       && ! ls "$_b7fr/$EV"/payload-rc1-* >/dev/null 2>&1 && [ -d "$_b7fr/$EV" ]; then
      refused B7f "$_b7f_rc" "$_b7/b7f.log" "rota 1 indisponivel: o payload do codex global" \
        "o runner INTEIRO com o codex plantado (antes de qualquer payload, nada executado)"
    else bad "B7f: o runner inteiro executou o plantado/npx ou montou payload"; sed -n '1,10p' "$_b7/b7f.log"; fi
  else bad "B7f: clone do candidato falhou"; fi
else printf '  (B7 pulado: sem clone/candidato ou sem python3)\n'; bad "B7: pre-condicao (clone do candidato) ausente"; fi

'''

# P — a sonda da 1.4.3: os controles vermelhos de cada verificacao, pelo NOME.
TEST_P_START = 'say "P. a sonda das condicoes nao e vacua: os controles VERMELHOS"\n'
TEST_P_END = '# ===========================================================================\nsay "C. gerador de envelope com chave GPG DESCARTAVEL"\n'
TEST_P = r'''say "P. a sonda das condicoes nao e vacua: os controles VERMELHOS"
if [ -n "${UPSTREAM:-}" ] && [ -n "$BASE_REV" ]; then
  # Um clone do upstream com UMA mutacao commitada; $1 = dir, $2 = mensagem, $3 = mutacao
  # (comando de shell rodado no clone). rc 0 = pronto.
  _p_mut() {
    git clone --quiet --local --shared "$UPSTREAM" "$1" 2>/dev/null && fixture_git_identity "$1" \
      && ( cd "$1" && eval "$3" ) && git -C "$1" add -A && git -C "$1" commit -q -m "TEST ONLY: $2"
  }
  # $1 = id, $2 = dir, $3 = ids da sonda, $4 = texto da linha FAIL, $5 = o caso
  _p_red() {
    local _rc=0
    ( cd "$2" && PYTHONDONTWRITEBYTECODE=1 python3 "$EV/probe-conditions-rc1.py" --root "$2" \
        --base refs/tags/v1.4.2 --head HEAD --only "$3" ) > "$SCRATCH/$1.log" 2>&1 || _rc=$?
    refused "$1" "$_rc" "$SCRATCH/$1.log" "$4" "$5"
  }
  # P2 — um caminho da faixa fora de toda parte e do escopo declarado (.github/ e da parte 1:
  # o orfao vai para a raiz).
  if _p_mut "$SCRATCH/p2" "orfao na raiz" 'printf "x\n" > TEST-ONLY-orfao.txt'; then
    _p_red P2 "$SCRATCH/p2" C11-scope "FAIL C11-scope: caminho da faixa fora de toda parte e do escopo declarado: TEST-ONLY-orfao.txt" \
      "caminho fora de toda parte e do escopo declarado"
  else bad "P2: fixture do orfao falhou"; fi
  # P4 — as condicoes citam a D-4; o plano commitado SEM a linha dela e recusado.
  if _p_mut "$SCRATCH/p4" "plano sem a D-4" "python3 -c 'import re,sys; p=sys.argv[1]; t=open(p,encoding=\"utf-8\").read(); n=re.sub(r\"(?m)^\\| D-4 \\|[^\\n]*\\n\", \"\", t, count=1); open(p,\"w\",encoding=\"utf-8\").write(n); sys.exit(0 if n!=t else 3)' .claude/plans/PLAN-194-maintenance-train-v1-4-3.md"; then
    _p_red P4 "$SCRATCH/p4" C12-plan-decisions "FAIL C12-plan-decisions: as condicoes citam D-4" \
      "condicao que cita uma decisao ausente do plano commitado"
  else bad "P4: fixture do plano sem a D-4 falhou (o plano da fixture tem a D-4?)"; fi
  # P5 — um veredito que o envelope do GA v1.4.2 pina pelo MANIFEST, com um byte a mais.
  _p5v=".claude/plans/PLAN-193/repass-ga/verdict-ga-1.txt"
  if _p_mut "$SCRATCH/p5" "veredito pinado alterado" "[ -f $_p5v ] && printf 'TEST ONLY\n' >> $_p5v"; then
    _p_red P5 "$SCRATCH/p5" C2-carried-1.4.2 "nao tem o sha256 pinado: $_p5v" \
      "veredito que o envelope do GA v1.4.2 pina, alterado"
  else bad "P5: fixture do veredito pinado falhou"; fi
  # P10 — um arquivo citado pelos vereditos da v1.4.0, fora das classes da condicao 1.
  if _p_mut "$SCRATCH/p10" "AGENTS.md muda na faixa" "[ -f AGENTS.md ] && printf '\n<!-- TEST ONLY -->\n' >> AGENTS.md"; then
    _p_red P10 "$SCRATCH/p10" C1-annex-v1.4.0 "FAIL C1-annex-v1.4.0: arquivo citado pelos vereditos da v1.4.0 muda fora das classes declaradas: AGENTS.md" \
      "arquivo citado da v1.4.0 fora das classes declaradas (condicao 1)"
  else bad "P10: fixture do AGENTS.md falhou"; fi
  # P11 — o job da W4 com uma permissao de token OIDC (condicao 4).
  if _p_mut "$SCRATCH/p11" "id-token no job da rc" "python3 -c 'import sys; p=sys.argv[1]; t=open(p,encoding=\"utf-8\").read(); i=t.index(\"  rc-toolchain-proof:\"); j=t.index(\"      contents: read\", i); open(p,\"w\",encoding=\"utf-8\").write(t[:j]+\"      id-token: write\n\"+t[j:])' .github/workflows/npm-publish.yml"; then
    _p_red P11 "$SCRATCH/p11" C0-rc-proof "FAIL C0-rc-proof: o job rc-toolchain-proof tem permissions" \
      "o job da prova do toolchain com id-token: write (condicao 4)"
  else bad "P11: fixture do id-token falhou"; fi
  # P11b — o job da W4 com outro nome (o passo 18 o exige pelo nome).
  if _p_mut "$SCRATCH/p11b" "job da rc renomeado" "python3 -c 'import sys; p=sys.argv[1]; t=open(p,encoding=\"utf-8\").read(); n=t.replace(\"    name: RC toolchain proof (no publish)\", \"    name: RC proof\", 1); open(p,\"w\",encoding=\"utf-8\").write(n); sys.exit(0 if n!=t else 3)' .github/workflows/npm-publish.yml"; then
    _p_red P11b "$SCRATCH/p11b" C0-rc-proof "FAIL C0-rc-proof: o job rc-toolchain-proof se chama ['RC proof']" \
      "o job da prova do toolchain com outro nome"
  else bad "P11b: fixture do job renomeado falhou"; fi
  # P12 — o manifesto ADR-182 pinando outra versao (condicao 3).
  if _p_mut "$SCRATCH/p12" "manifesto em outra versao" "python3 -c 'import json,sys; p=sys.argv[1]; d=json.load(open(p)); d[\"package_version\"]=\"0.159.0\"; open(p,\"w\").write(json.dumps(d,indent=2)+\"\n\")' .claude/governance/codex-cli-pin-manifest.json"; then
    _p_red P12 "$SCRATCH/p12" C9-codex-pin "FAIL C9-codex-pin: o manifesto ADR-182 pina '0.159.0' (esperado 0.160.0" \
      "o manifesto pinando outra versao do codex"
  else bad "P12: fixture do manifesto falhou"; fi
  # P13 — o runner do candidato com a rota 2 viva (condicao 3).
  if _p_mut "$SCRATCH/p13" "rota 2 viva no runner" "printf '_nv=\"\$(npx -y \"@openai/codex@x\" --version)\"\n' >> $EV/run-rc1-repass.sh"; then
    _p_red P13 "$SCRATCH/p13" C13-route1 "FAIL C13-route1: o runner do candidato ainda invoca npx (a rota 2 viva)" \
      "o runner do candidato que invoca npx"
  else bad "P13: fixture da rota 2 viva falhou"; fi
  # P14 — um id desconhecido em --only nunca vira verde vacuo (cura da sonda do GA).
  _p14_rc=0
  ( cd "$CLONE" && PYTHONDONTWRITEBYTECODE=1 python3 "$EV/probe-conditions-rc1.py" --root "$CLONE" \
      --base refs/tags/v1.4.2 --head HEAD --only C99-nao-existe ) > "$SCRATCH/P14.log" 2>&1 || _p14_rc=$?
  refused P14 "$_p14_rc" "$SCRATCH/P14.log" "INFRA sonda: id(s) de --only desconhecido(s): C99-nao-existe" \
    "um id desconhecido em --only"
else printf '  (P pulado: sem upstream ou sem base)\n'; bad "P: pre-condicao (upstream e base) ausente"; fi

'''

# C — sem PLUMBING da linha da sonda (o gerador confere o relatorio: cura do GA).
TEST_C_RESEAL_START = "    _c_reseal() {\n"
TEST_C_RESEAL_END = "    # C0 — a sonda das condicoes: a evidencia de um run cuja sonda NAO ficou verde (o\n"
TEST_C0DOC_OLD = ("    # P0 ficou vermelho; depois, PLUMBING declarado: a linha vira verde para o resto da\n"
                  "    # tubulacao (o F prova a recusa da linha vermelha em qualquer caso).\n")
TEST_C0DOC_NEW = ("    # P0 ficou vermelho. Sem PLUMBING da linha da sonda: o gerador le o probe-rc1.txt e\n"
                  "    # confere a linha da PROVENANCE contra ele, entao o C2 em diante REPROVAM por\n"
                  "    # construcao sobre essa evidencia (a falha ja esta anotada no P0); o F prova a recusa\n"
                  "    # de cada forma de linha e de relatorio que nao prova a sonda verde.\n")
TEST_C0PLUMB_START = "      python3 - \"$CLONE/$EV/PROVENANCE-rc1.md\" <<'PYC0'\n"
TEST_C0PLUMB_END = "    fi\n    # C1 — CONTROLE VERMELHO: evidencia de um run com STUB nao pode virar\n"
TEST_C2PLUMB_OLD = r'''# PLUMBING declarado: se o P0 deixou a sonda vermelha (lane ainda nao landada), a linha
# dela vira verde AQUI para que o resto da tubulacao do gerador rode; o F prova que o
# gerador recusa a linha vermelha.
t = re.sub(r"^- sonda das condicoes: .*$",
           "- sonda das condicoes: verde (PLUMBING do harness: C2)", t, count=1, flags=re.M)
'''
TEST_C2PLUMB_NEW = "# A linha da sonda NAO e tocada: o gerador a confere contra o probe-rc1.txt (C0).\n"

TEST_W3_OLD = r'''if W_LOAD="0.10 8" bash "$SCRATCH/w.sh" < /dev/null > "$SCRATCH/w3.log" 2>&1 \
   && ! grep -q 'AVISO' "$SCRATCH/w3.log"; then
'''
TEST_W3_NEW = r'''if W_LOAD="0.10 8" bash "$SCRATCH/w.sh" < /dev/null > "$SCRATCH/w3.log" 2>&1 \
   && grep -q 'carga baixa' "$SCRATCH/w3.log" && lacks "$SCRATCH/w3.log" 'AVISO'; then
'''

# X2-X4 — o passo 18 novo: o gate E a prova do toolchain da rc, pelo nome.
TEST_X2_START = ("  # X2 — passo 18: o await-release-gate que terminou sem success (o de antes de um rerun\n")
TEST_X2_END = 'else bad "X: fixture do passo 17 falhou"; fi\n'
TEST_X2 = r'''  # X2-X4 — passo 18: o gate E a prova do toolchain da rc, PELO NOME. O stub do gh devolve,
  # por chamada: o repo, o id do run e "<status do run>|<gate>|<quantos jobs com o nome da
  # prova>|<prova>".
  { printf '#!/bin/bash\nset -euo pipefail\n'
    printf 'die() { printf "FAIL: %%s\\n" "$*" >&2; exit 1; }\n'
    printf 'say() { :; }; bell() { :; }; sleep() { :; }; should() { return 0; }\n'
    printf 'mark_step() { printf "X-STEP-%%s-MARCADO\\n" "$1"; }\n'
    printf 'TAG=v1.4.3-rc.1\n'
    grep -m 1 '^RC_PROOF_JOB=' "$_cut"
    awk '/^if should 18; then$/,/^fi$/' "$_cut"; } > "$SCRATCH/x2.sh"
  _x2_run() {
    rm -f -- "$_x/cnt"
    ( cd "$_x/w" && PATH="$_x/bin:$PATH" X_CNT="$_x/cnt" X_SEQ="$1" bash "$SCRATCH/x2.sh" ) > "$2" 2>&1
  }
  _x2_rc=0; _x2_run "$(printf 'owner/repo\n4343\ncompleted|failure|1|success')" "$SCRATCH/x2-fail.log" || _x2_rc=$?
  refused X2 "$_x2_rc" "$SCRATCH/x2-fail.log" "await-release-gate terminou 'failure' (run 4343" \
    "o await-release-gate sem success no passo 18"
  if grep -q 'gh run rerun 4343 --failed' "$SCRATCH/x2-fail.log"; then ok "X2: a recusa traz a rota do rerun do npm-publish.yml"
  else bad "X2: a recusa sem a rota do rerun"; fi
  _x3_rc=0; _x2_run "$(printf 'owner/repo\n4343\nin_progress|success|1|failure')" "$SCRATCH/x3.log" || _x3_rc=$?
  refused X3 "$_x3_rc" "$SCRATCH/x3.log" "a prova do toolchain da rc («RC toolchain proof (no publish)») terminou 'failure' (run 4343" \
    "a prova do toolchain da rc sem success no passo 18"
  _x4_rc=0; _x2_run "$(printf 'owner/repo\n4343\ncompleted|success|0|')" "$SCRATCH/x4.log" || _x4_rc=$?
  refused X4 "$_x4_rc" "$SCRATCH/x4.log" "terminou SEM o job «RC toolchain proof (no publish)»" \
    "o run concluido sem o job da prova do toolchain (pelo NOME)"
  if _x2_run "$(printf 'owner/repo\n4343\nin_progress||1|\n4343\nin_progress|success|1|\n4343\ncompleted|success|1|success')" "$SCRATCH/x2-ok.log" \
     && grep -q 'X-STEP-18-MARCADO' "$SCRATCH/x2-ok.log" && grep -q 'prova do toolchain: pendente' "$SCRATCH/x2-ok.log"; then
    ok "X2: gate e prova pendentes, depois o gate verde e a prova pendente, e por fim os dois verdes marcam o passo 18"
  else bad "X2: o caminho verde do passo 18 falhou"; sed -n '1,8p' "$SCRATCH/x2-ok.log"; fi
'''

# R — o estado bom do clone (antes do R1) e os controles de CORTE INTEIRO das recusas do G0
# que so tinham controle verbatim (R3H-03), antes do R8 (que muta o main da fixture).
TEST_RGOOD_OLD = ("  if git clone --quiet --bare \"$UPSTREAM\" \"$_r/origin.git\" 2>/dev/null \\\n"
                  "     && git clone --quiet \"$_r/origin.git\" \"$_r/wt\" 2>/dev/null && fixture_git_identity \"$_r/wt\"; then\n")
TEST_RGOOD_NEW = TEST_RGOOD_OLD + "    _r_good=\"$(git -C \"$_r/wt\" rev-parse HEAD)\"\n"
TEST_R2_OLD = ("    elif grep -q 'a tag base v1.4.2 nao existe neste repositorio' \"$_r/r2.log\" \\\n"
               "         && grep -q 'OWNER-GA-CUT.sh' \"$_r/r2.log\"; then\n"
               "      ok \"R2 (controle vermelho): tag base ausente e recusa NOMEADA (a rota: cortar o GA ou buscar a tag)\"\n")
TEST_R2_NEW = ("    elif grep -q 'a tag base v1.4.2 nao existe neste repositorio' \"$_r/r2.log\" \\\n"
               "         && grep -q 'falta git fetch origin tag v1.4.2' \"$_r/r2.log\"; then\n"
               "      ok \"R2 (controle vermelho): tag base ausente e recusa NOMEADA (a rota: buscar a tag)\"; _red=\"$_red R2\"\n")
TEST_RNEW_ANCHOR = ("    # R8 — a sonda das condicoes no G0 recusa uma condicao FALSA pelo nome (um template\n")
TEST_RNEW = r'''    # R10-R18 — cada recusa do G0 que so tinha controle VERBATIM (ou nenhum), agora pelo
    # CORTE INTEIRO (`--g0-only`), pelo NOME (R3H-03). Cada caso parte do estado bom do clone
    # (o HEAD do R1, com o remoto igual) e volta a ele.
    _r_restore() {
      git -C "$_r/wt" reset -q --hard "$_r_good" 2>/dev/null \
        && git -C "$_r/wt" push -q -f origin "$_r_good:refs/heads/main" 2>/dev/null \
        && git -C "$_r/wt" clean -q -fdx -e "$EV/.cut-state" 2>/dev/null || bad "R: restaurar o estado bom do clone falhou"
      R_RC_RELEASE=""; _r_state 0
    }
    _r_whole() {  # $1 = id, $2 = texto fixo da recusa, $3 = o caso; o clone ja mutado
      local _rc=0
      _r_cut "$_r/$1.log" --g0-only || _rc=$?
      refused "$1" "$_rc" "$_r/$1.log" "$2" "G0 real (corte inteiro): $3"
      _r_restore
    }
    _r_commit_push() {  # $1 = mensagem: commita o que esta na arvore e pusha (o main da fixture)
      git -C "$_r/wt" add -A && git -C "$_r/wt" commit -q -m "TEST ONLY: $1" \
        && git -C "$_r/wt" push -q origin HEAD:refs/heads/main 2>/dev/null
    }
    _r_restore
    # R10 — o release.sh com sha fora do manifesto ADR-192 (a relmeta pela metade).
    printf '\n# TEST ONLY: R10\n' >> "$_r/wt/.claude/scripts/local/release.sh"
    if _r_commit_push "release.sh fora do manifesto"; then
      _r_whole R10 "sha do release.sh nao bate com o manifesto ADR-192" "o release.sh fora do manifesto ADR-192"
    else bad "R10: commit/push da mutacao falhou"; _r_restore; fi
    # R11 — um arquivo do kit modificado e nao commitado.
    printf '\n# TEST ONLY: R11\n' >> "$_r/wt/$EV/README-rc1.md"
    _r_whole R11 "$EV/README-rc1.md (diferente do HEAD)" "o kit modificado e nao commitado"
    # R12 — um arquivo RASTREADO modificado fora do plano.
    printf '\nTEST ONLY: R12\n' >> "$_r/wt/SUPPORT.md"
    _r_whole R12 "SUPPORT.md (RASTREADO, modificado)" "um arquivo rastreado modificado fora do plano"
    # R13 — o GitHub Release da tag ja existe antes do push (corte anterior abortado).
    R_RC_RELEASE='{"isPrerelease":true,"isDraft":false}'
    _r_whole R13 "GitHub Release do v1.4.3-rc.1 JA EXISTE antes do push da tag" "o Release fantasma antes do passo 16"
    # R14 — o .gen-*.tmp orfao de um gerador morto (R3C-01): recusa NOMEADA, com a rota.
    printf 'fields pela metade\n' > "$_r/wt/$PLAN_DIR/.gen-R14abc.tmp"
    printf 'envelope pela metade\n' > "$_r/wt/.claude/governance/.gen-R14def.tmp"
    _r_cut "$_r/R14.log" --g0-only; _r14_rc=$?
    refused R14 "$_r14_rc" "$_r/R14.log" "temporario de um gerador do envelope MORTO no meio da escrita" \
      "G0 real (corte inteiro): o .gen-*.tmp orfao no plano e em .claude/governance/"
    if grep -qF "$PLAN_DIR/.gen-R14abc.tmp" "$_r/R14.log" && grep -qF ".claude/governance/.gen-R14def.tmp" "$_r/R14.log" \
       && grep -qF "mkdir -p $SCRATCH/rhome/.ceo-rc1-archive/gen-orfaos && mv --" "$_r/R14.log"; then
      ok "R14: a recusa nomeia os dois orfaos e da a rota (mover para o arquivo FORA do repositorio, sem apagar)"
    else bad "R14: a recusa sem os nomes ou sem a rota"; sed -n '1,8p' "$_r/R14.log"; fi
    # R14b — pela rota da tela (mover, nao apagar), o G0 fica verde.
    mkdir -p "$SCRATCH/rhome/.ceo-rc1-archive/gen-orfaos" \
      && mv -- "$_r/wt/$PLAN_DIR/.gen-R14abc.tmp" "$_r/wt/.claude/governance/.gen-R14def.tmp" "$SCRATCH/rhome/.ceo-rc1-archive/gen-orfaos/"
    if _r_cut "$_r/R14b.log" --g0-only && grep -q 'G0 verde (--g0-only)' "$_r/R14b.log" \
       && [ -f "$SCRATCH/rhome/.ceo-rc1-archive/gen-orfaos/.gen-R14abc.tmp" ]; then
      ok "R14b: pela rota da recusa (os orfaos FORA do repositorio, preservados) o G0 fica verde"
    else bad "R14b: a rota da recusa nao deixou o G0 verde"; sed -n '1,12p' "$_r/R14b.log"; fi
    _r_restore
    # R15 — o HEAD sem o job da W4 (o passo 18 o exige pelo nome).
    if python3 - "$_r/wt/.github/workflows/npm-publish.yml" <<'PYR15' && _r_commit_push "sem o job da W4"
import re, sys
p = sys.argv[1]
t = open(p, encoding="utf-8").read()
m = re.search(r"(?m)^  rc-toolchain-proof:[ \t]*\n", t)
if not m:
    raise SystemExit(1)
rest = t[m.end():]
nxt = re.search(r"(?m)^  [A-Za-z0-9_-]+:[ \t]*$|^[^ \t\n#]", rest)
open(p, "w", encoding="utf-8").write(t[:m.start()] + (rest[nxt.start():] if nxt else ""))
PYR15
    then
      _r_whole R15 "nao tem o job «RC toolchain proof (no publish)»" "o HEAD sem o job da prova do toolchain da W4"
    else bad "R15: commit/push sem o job da W4 falhou"; _r_restore; fi
    # R16 — CLAUDE.md acima do limite do validate-governance.sh completo.
    python3 -c 'import sys; open(sys.argv[1], "a").write("\n" + "x" * 40000 + "\n")' "$_r/wt/CLAUDE.md"
    if _r_commit_push "CLAUDE.md grande"; then
      _r_whole R16 "bytes; o validate-governance.sh completo (que o preflight" "o CLAUDE.md acima do limite"
    else bad "R16: commit/push do CLAUDE.md falhou"; _r_restore; fi
    # R17 — um commit da faixa que cita plano fora do RELEASE_SCOPE.
    if git -C "$_r/wt" commit -q --allow-empty -m "plan(PLAN-998): TEST ONLY fora do Scope" \
       && git -C "$_r/wt" push -q origin HEAD:refs/heads/main 2>/dev/null; then
      _r_whole R17 "nao lista: PLAN-998" "um commit que cita plano fora do RELEASE_SCOPE"
    else bad "R17: commit/push do plano fora do Scope falhou"; _r_restore; fi
    # R18 — o runner do kit ausente da arvore.
    rm -f -- "$_r/wt/$EV/run-rc1-repass.sh"
    _r_whole R18 "runner ausente: $EV/run-rc1-repass.sh" "o runner do kit ausente"

'''
TEST_R8_START = "    # R8 — a sonda das condicoes no G0 recusa uma condicao FALSA pelo nome (um template\n"
TEST_R8_END = "    # R9 — a relmeta-143 nao landou (o driver ainda mira 1.4.2): recusa nomeando o pack.\n"
TEST_R8 = r'''    # R8 — a sonda das condicoes no G0 recusa uma condicao FALSA pelo nome (o job da W4 com
    # uma permissao de token OIDC: condicao 4). Sem o REPORT-ONLY: o que se confere e a linha
    # da condicao 4. O job segue com o nome e o gatilho (o guard do job no G0 passa).
    if python3 - "$_r/wt/.github/workflows/npm-publish.yml" <<'PYR8' \
       && git -C "$_r/wt" commit -q -am "TEST ONLY: id-token no job da rc" \
       && git -C "$_r/wt" push -q origin HEAD:refs/heads/main 2>/dev/null
import sys
p = sys.argv[1]
t = open(p, encoding="utf-8").read()
i = t.index("  rc-toolchain-proof:")
j = t.index("      contents: read", i)
open(p, "w", encoding="utf-8").write(t[:j] + "      id-token: write\n" + t[j:])
PYR8
    then
      _r8_rc=0
      ( cd "$_r/wt" && env PATH="$_r/bin:$PATH" GNUPGHOME="$GH" HOME="$SCRATCH/rhome" \
             TMPDIR="$_r/tmp" RC1_SELFTEST=1 RC1_SELFTEST_SCRATCH="$SCRATCH" RC1_SELFTEST_SIGNER_FPR="$FPR" \
             bash "$PLAN_DIR/OWNER-RC1-CUT.sh" --g0-only ) < /dev/null > "$_r/r8.log" 2>&1 || _r8_rc=$?
      refused R8 "$_r8_rc" "$_r/r8.log" "a sonda das condicoes achou afirmacao FALSA" \
        "G0 real (corte inteiro): uma condicao FALSA (condicao 4)"
      if grep -q 'FAIL C0-rc-proof: o job rc-toolchain-proof tem permissions' "$_r/r8.log"; then
        ok "R8: a recusa nomeia a afirmacao (C0-rc-proof)"
      else bad "R8: G0 real recusou sem nomear a condicao"; grep -E 'FAIL|sonda' "$_r/r8.log" | sed -n '1,8p'; fi
    else bad "R8: commit/push da mutacao no clone falhou"; fi
'''

TEST_D_ANCHOR = ("# ===========================================================================\n"
                 "printf '\\n===== RESULTADO: %s PASS, %s FAIL\\n' \"$PASS\" \"$FAIL\"\n")
TEST_D_INDEX = r'''# D8-D12 — o INDICE dos controles vermelhos dos gates novos e das curas desta derivacao
# (R3H-04 pela forma): cada um tem de ter rodado e ficado verde NESTE ensaio (o auxiliar
# `refused` e os controles positivos anotam o id em _red); uma secao pulada nao prova nada.
_d_need() {  # $1 = rotulo do gate, $2.. = controles que tem de ter passado
  local _g="$1" _m="" _c; shift
  for _c in "$@"; do
    case " $_red " in *" $_c "*) : ;; *) _m="$_m $_c" ;; esac
  done
  if [ -z "$_m" ]; then ok "$_g: controles vermelhos exercitados e verdes ($*)"
  else bad "$_g: controle(s) vermelho(s) que NAO rodaram ou NAO ficaram verdes:$_m"; fi
}
_d_need "D8 rota 1 so (PLAN-194 D-4): lancador plantado, npx espiao e espiao do oraculo" B7a B7b B7c B7d B7e B7f
_d_need "D9 passo 18: o gate e a prova do toolchain da rc, pelo nome" X2 X3 X4
_d_need "D10 recusas do G0 pelo corte inteiro (R3H-03)" R2 R8 R10 R11 R12 R13 R14 R15 R16 R17 R18
_d_need "D11 sonda: os controles vermelhos das condicoes da 1.4.3" P2 P4 P5 P10 P11 P11b P12 P13 P14
_d_need "D12 censo do harness (R3H-01/R3H-02) e o modelo recusado pelo nome" A3 B3c
_d_need "D13 passo 11: o envelope re-derivado dos fields assinados (cura do GA v1.4.2)" E3e E3f

'''

# E3e — o envelope adulterado na arvore e substituido pelo RE-DERIVADO no passo 11.
TEST_E3E_ANCHOR = "  # E4 — o passo 2: `release.sh bump` num clone local do candidato (a forma que o\n"
TEST_E3E = r'''  # E3e (controle vermelho; cura do GA v1.4.2): um envelope ADULTERADO na arvore (um byte a
  # mais, numa retomada entre os passos 10 e 11) e substituido pelo RE-DERIVADO dos fields
  # assinados: a tela avisa que diferia, e e o derivado que entra no commit.
  _e3e="$SCRATCH/e3e"; _e3ehome="$SCRATCH/e3ehome"; mkdir -p "$_e3ehome"
  if [ -f "$SCRATCH/e3.sh" ] && _e_prep "$_e3e" && cp "$CLONE/$_e_vf.asc" "$_e3e/$_e_vf.asc" \
     && cp -- "$_e3e/$_e_vd" "$SCRATCH/e3e-derived.md" && printf 'TEST ONLY: adulterado\n' >> "$_e3e/$_e_vd"; then
    if _e3_env "$_e3e" "$_e3ehome" "$SCRATCH/e3e.log" \
       && grep -q 'DIFERIA do derivado dos fields assinados' "$SCRATCH/e3e.log" \
       && [ "$(git -C "$_e3e" rev-parse HEAD^ 2>/dev/null)" = "$CAND" ] \
       && git -C "$_e3e" show "HEAD:$_e_vd" | cmp -s - "$SCRATCH/e3e-derived.md"; then
      ok "E3e (controle vermelho): o envelope adulterado na arvore e substituido pelo re-derivado dos fields assinados; o commit leva o derivado"; _red="$_red E3e"
    else bad "E3e: o passo 11 nao re-derivou o envelope adulterado (ou o commit leva outro)"; sed -n '1,12p' "$SCRATCH/e3e.log"; fi
  else bad "E3e: preparacao falhou"; fi
  # E3f (controle positivo): o E3e nao e vacuo — o passo 11 da v1.4.2-rc.1 (sem a cura),
  # verbatim sobre o MESMO estado, commita o envelope adulterado.
  _e3f_cut="$ROOT/.claude/plans/PLAN-193/OWNER-RC1-CUT.sh"
  _e3f="$SCRATCH/e3f"; _e3fhome="$SCRATCH/e3fhome"; mkdir -p "$_e3fhome"
  if [ -f "$_e3f_cut" ] && _e_prep "$_e3f" && cp "$CLONE/$_e_vf.asc" "$_e3f/$_e_vf.asc" \
     && printf 'TEST ONLY: adulterado\n' >> "$_e3f/$_e_vd"; then
    {
      printf '#!/bin/bash\nset -euo pipefail\n'
      printf 'say() { :; }; bell() { :; }; mark_step() { :; }\n'
      printf 'die() { printf "FAIL: %%s\\n" "$*" >&2; exit 1; }\n'
      printf 'PLAN_DIR=%s; EV=%s; TAG=v1.4.3-rc.1\n' "$PLAN_DIR" "$EV"
      printf 'COND="$EV/CONDITIONS-rc1.md"; VF="$PLAN_DIR/verdict-fields-$TAG.md"\n'
      printf 'VD=".claude/governance/pair-rail-verdict-$TAG.md"; CAND=%s\n' "$CAND"
      printf 'GEN=%s\n' "$PLAN_DIR/gen-envelope-rc1.py"
      awk '/^evidence_list\(\) \{$/,/^\}$/' "$_e3f_cut"
      awk '/^if should 11; then$/{f=1; next} /^  mark_step 11$/{f=0} f' "$_e3f_cut"
    } > "$SCRATCH/e3f.sh"
    ( cd "$_e3f" && HOME="$_e3fhome" GNUPGHOME="$GH" RC1_SELFTEST=1 \
         RC1_SELFTEST_SCRATCH="$SCRATCH" RC1_SELFTEST_SIGNER_FPR="$FPR" PATH="$CLAUDE_STUB_DIR:$PATH" \
         GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=commit.gpgsign \
         GIT_CONFIG_VALUE_0=false bash "$SCRATCH/e3f.sh" ) > "$SCRATCH/e3f.log" 2>&1 || :
    if [ "$(git -C "$_e3f" rev-parse HEAD^ 2>/dev/null)" = "$CAND" ] \
       && git -C "$_e3f" show "HEAD:$_e_vd" | grep -q 'TEST ONLY: adulterado'; then
      ok "E3f (controle positivo): o passo 11 da v1.4.2-rc.1 commita o envelope ADULTERADO — o E3e ve a classe"; _red="$_red E3f"
    else bad "E3f: o passo 11 da v1.4.2-rc.1 nao commitou o envelope adulterado — o E3e seria vacuo"; sed -n '1,10p' "$SCRATCH/e3f.log"; fi
  else bad "E3f: preparacao falhou"; fi

'''


def derive_test(src: str) -> str:
    t = shift(src, "harness", TEST_PROTECT)
    # O cabecalho e o INICIO do arquivo ate o primeiro `set -uo pipefail` (os stubs do corpo
    # tambem comecam com `#!/bin/bash`).
    if not t.startswith("#!/bin/bash\n# CEREMONY-LINT: handwritten-exception: harness do kit de corte"):
        die("o harness de origem nao comeca com o cabecalho esperado")
    t = TEST_HEADER + t[t.index("set -uo pipefail\n"):]
    t = sub(t, TEST_HELPERS_OLD, TEST_HELPERS_NEW, "auxiliares lacks/refused")
    f_ga = ga_block('say "F. partes estritas, condicoes congeladas e preservacao de tentativa"\n',
                    '# ===========================================================================\nsay "A. lint estatico"\n',
                    "secao F do GA")
    f_ga = sub(f_ga, "na forma que a sonda do GA escreve", "na forma que a sonda do kit escreve", "F: sonda do kit")
    t = cut_region(t, TEST_F_START, TEST_F_END, f_ga, "secao F")
    t = sub(t, TEST_K1_ANCHOR, TEST_K1 + TEST_K1_ANCHOR, "modo K1")
    t = sub(t, TEST_A3_ANCHOR, TEST_A3 + TEST_A3_ANCHOR, "censo A3")
    t = sub(t, TEST_BRAW_OLD, TEST_BRAW_NEW, "ausencia do RAW")
    b2_ga = ga_block('say "B2. rodada MORTA por capacidade do modelo: re-tentada, e a PROVENANCE declara"\n',
                     TEST_B2_GA_END, "secoes B2/B2u/B2x do GA")
    b2_ga = sub(b2_ga, TEST_B2_ABS_OLD, TEST_B2_ABS_NEW, "B2: ausencia da classe da conta")
    t = cut_region(t, TEST_B2_START, TEST_B2_END, b2_ga, "secao B2")
    t = sub(t, TEST_B3_OLD, TEST_B3_NEW, "B3: recusa nomeada")
    t = sub(t, TEST_B7_ANCHOR, TEST_B7 + TEST_B7_ANCHOR, "secao B7")
    t = cut_region(t, TEST_P_START, TEST_P_END, TEST_P, "secao P")
    t = cut_region(t, TEST_C_RESEAL_START, TEST_C_RESEAL_END, "", "C: _c_reseal")
    t = sub(t, TEST_C0DOC_OLD, TEST_C0DOC_NEW, "C0: sem plumbing")
    t = cut_region(t, TEST_C0PLUMB_START, TEST_C0PLUMB_END, "", "C0: plumbing")
    t = sub(t, TEST_C2PLUMB_OLD, TEST_C2PLUMB_NEW, "C2: plumbing")
    t = sub(t, TEST_W3_OLD, TEST_W3_NEW, "W3: ausencia com pre-condicao")
    t = cut_region(t, TEST_X2_START, TEST_X2_END, TEST_X2, "X2-X4")
    t = sub(t, TEST_RGOOD_OLD, TEST_RGOOD_NEW, "R: estado bom")
    t = sub(t, TEST_R2_OLD, TEST_R2_NEW, "R2: rota da base")
    t = sub(t, TEST_RNEW_ANCHOR, TEST_RNEW + TEST_RNEW_ANCHOR, "R10-R18")
    t = cut_region(t, TEST_R8_START, TEST_R8_END, TEST_R8, "R8")
    t = sub(t, TEST_E3E_ANCHOR, TEST_E3E + TEST_E3E_ANCHOR, "E3e")
    t = sub(t, TEST_D_ANCHOR, TEST_D_INDEX + TEST_D_ANCHOR, "indice D8-D13")
    t = lacks_rewrite(t)
    forbid(t, "harness", ["derive-kit-142", "C5-pin", "canary_pre", "PLUMBING do harness",
                          "OWNER-GA-CUT.sh", "-ga."])
    need(t, "harness", ['PLAN_DIR=".claude/plans/PLAN-194"', "derive-kit-143.py --check",
                        "refs/tags/v1.4.2^{commit}", 'say "B7. ROTA 1 SO', 'say "K1. derivadores sem as saidas',
                        "como antes da relmeta-142", 'grep -q \'nao lista: PLAN-194$\''])
    return t


# `! grep -q[flags] 'padrao' "arquivo"` -> `lacks "arquivo" [-flags] 'padrao'` (R3H-01): a
# ausencia passa a exigir o arquivo. O censo A3 confere que nenhuma forma crua sobrou.
_LACKS_RE = re.compile(r"!\s*grep\s+-q([A-Za-z]*)\s+('[^'\n]*'|\"[^\"\n]*\")\s+(\"[^\"\n]*\")")


def lacks_rewrite(text: str) -> str:
    def _r(m: "re.Match[str]") -> str:
        flags = m.group(1)
        return "lacks %s %s%s" % (m.group(3), ("-%s " % flags) if flags else "", m.group(2))
    return _LACKS_RE.sub(_r, text)


# ===========================================================================
# conferencias entre saidas e escrita
# ===========================================================================
def cross_checks(out: Dict[str, str]) -> None:
    """O que uma saida afirma sobre outra (recusa nomeada)."""
    # Um `$NOME` colado a um caractere nao-ASCII (`«$JOB»`): o bash de um locale que nao e
    # UTF-8 le o primeiro byte do caractere como parte do NOME ("JOB\xc2: unbound variable",
    # medido no ensaio). Nos shells do kit a variavel vai entre chaves.
    for kind in ("runner", "cut", "test"):
        bad = sorted(set(m.group(0) for m in re.finditer(r"\$[A-Za-z_][A-Za-z0-9_]*(?=[^\x00-\x7f])", out[kind])))
        if bad:
            die("%s: variavel colada a caractere nao-ASCII (use ${NOME}): %s" % (kind, ", ".join(bad[:8])))
    # o gerador pina exatamente os ids da lista CHECKS da sonda derivada
    m = re.search(r"(?ms)^PROBE_IDS = \(\n(.*?)^\)\n", out["gen"])
    gen_ids = tuple(re.findall(r'"([^"]+)"', m.group(1))) if m else ()
    if gen_ids != probe_ids(out["probe"]):
        die("PROBE_IDS do gerador %r != ids da sonda %r" % (gen_ids, probe_ids(out["probe"])))
    # o corte exige pelo nome o job que o derivador conferiu, e a condicao 4 o nomeia
    for kind in ("cut", "cond", "probe"):
        if RC_PROOF_JOB_NAME not in out[kind]:
            die("%s sem o nome do job da prova do toolchain (%r)" % (kind, RC_PROOF_JOB_NAME))
    # o kit que o corte exige commitado e o que o harness copia: as 8 saidas e este derivador
    kit = sorted(OUTPUTS[k] for k in ORDER) + [DST_PLAN + "/derive-kit-143.py"]
    kit_files = region(out["test"], 'KIT_FILES="\n', '"\n', "KIT_FILES do harness")
    kit_tracked = region(out["cut"], 'KIT_TRACKED="$RUNNER', "\nRESTAMP=", "KIT_TRACKED do corte")
    for rel in kit:
        tail = rel.split(DST_PLAN + "/", 1)[1]
        cite = ("$EV/" + tail.split("/", 1)[1]) if tail.startswith("repass-rc1/") else ("$PLAN_DIR/" + tail)
        if cite + "\n" not in kit_files:
            die("o harness nao copia %s (KIT_FILES sem %r)" % (rel, cite))
        names = {"runner": "$RUNNER", "probe": "$PROBE", "gen": "$GEN", "cond": "$COND"}
        word = next((v for k, v in names.items() if OUTPUTS[k] == rel), cite)
        if word not in kit_tracked:
            die("o corte nao exige %s commitado (KIT_TRACKED sem %r)" % (rel, word))
    # o MAPA da sonda mapeia so condicoes que existem no texto das condicoes
    nums = set(re.findall(r"(?m)^([0-9]+)\. \*\*", out["cond"]))
    mapped = set(c for c in probe_conditions(out["probe"]) if c != "cabecalho")
    if not mapped or not mapped <= nums:
        die("a sonda mapeia condicoes %s que o texto nao numera (%s)" % (sorted(mapped - nums), sorted(nums)))
    # os textos que o harness exige dos outros (recusas nomeadas), presentes na saida dona
    for kind, lit in (
            ("runner", "e RECUSA NOMEADA nesta release (PLAN-194 D-4): nada foi baixado nem executado"),
            ("runner", '_r1_why="nenhum codex no PATH"'),
            ("runner", '_r1_why="o payload do codex global ($_glob) NAO confere'),
            ("runner", "rota 1 indisponivel: $_r1_why"),
            ("cut", "temporario de um gerador do envelope MORTO no meio da escrita"),
            ("cut", "terminou SEM o job «${RC_PROOF_JOB}»"),
            ("cut", "a prova do toolchain da rc («${RC_PROOF_JOB}») terminou '$PC'"),
            ("probe", "INFRA sonda: id(s) de --only desconhecido(s): "),
            ("probe", "o runner do candidato ainda invoca npx (a rota 2 viva)")):
        if lit not in out[kind]:
            die("%s sem o texto que o harness confere: %r" % (kind, lit))


def derive_all() -> Dict[str, str]:
    out = {
        "runner": derive_runner(load("runner")),
        "probe": derive_probe(load("probe")),
        "cond": derive_cond(load("cond")),
        "readme": derive_readme(load("readme")),
        "gitignore": derive_gitignore(load("gitignore")),
        "gen": derive_gen(load("gen")),
        "cut": derive_cut(load("cut")),
        "test": derive_test(load("test")),
    }
    cross_checks(out)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--provisional", action="store_true",
                    help="escreve as saidas com o conteudo da release PROVISORIO (K1)")
    a = ap.parse_args()
    verify_references()
    probe_crons()
    verify_head_facts()
    out = derive_all()
    if not a.check and RELEASE_CONTENT != "final" and not a.provisional:
        die("o conteudo da release e PROVISORIO (RELEASE_CONTENT=%r): as condicoes, o README, a "
            "particao e o CONTEXT do prompt da 1.4.3 so ficam finais na derivacao do KIT (PLAN-194 "
            "W7). Para escrever o kit provisorio (o ensaio do K1, num clone descartavel), passe "
            "--provisional; para o kit do corte, complete o conteudo e troque RELEASE_CONTENT "
            "para \"final\"." % RELEASE_CONTENT)
    rc = 0
    for kind in ORDER:
        text = out[kind]
        dst = REPO / OUTPUTS[kind]
        if a.check:
            cur = dst.read_bytes().decode("utf-8") if (dst.is_file() and not dst.is_symlink()) else None
            same = cur == text
            print("%-9s %s  %s" % (kind, "OK " if same else "DIF", OUTPUTS[kind]))
            rc = rc or (0 if same else 1)
            continue
        if dst.is_symlink() or (dst.exists() and not dst.is_file()):
            die("destino nao e arquivo regular: %s" % OUTPUTS[kind])
        dst.parent.mkdir(parents=True, exist_ok=True)
        tmp = dst.with_name(dst.name + ".derive-tmp")
        tmp.write_bytes(text.encode("utf-8"))
        tmp.chmod(MODES[kind])
        tmp.replace(dst)
        print("wrote %s (%d linhas, sha256 %s)"
              % (OUTPUTS[kind], text.count("\n"), hashlib.sha256(text.encode("utf-8")).hexdigest()))
    if a.check:
        print("--check %s" % ("OK (disco == derivado)" if rc == 0 else "FALHOU (disco != derivado)"))
    elif RELEASE_CONTENT != "final":
        print("AVISO: kit escrito com o conteudo da release PROVISORIO (%s) — nunca para um corte"
              % RELEASE_CONTENT)
    return rc


if __name__ == "__main__":
    sys.exit(main())
