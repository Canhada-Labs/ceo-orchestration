#!/usr/bin/env python3
"""Derivador do kit de corte do GA v1.4.3 (PLAN-194 W7) — ESTAGIO K1.

  python3 .claude/plans/PLAN-194/derive-ga-kit-143.py --check-cures
  python3 .claude/plans/PLAN-194/derive-ga-kit-143.py --emit-cured DIR
  python3 .claude/plans/PLAN-194/derive-ga-kit-143.py            # o kit: recusa nomeada (K1)

O kit do GA v1.4.3 sai do kit do GA v1.4.2 (PLAN-194 W7: «o kit derivado do kit do GA
1.4.2»), cujas oito saidas sao as FONTES deste derivador, com sha256 PINADO (cortaram uma
release publicada e nao mudam mais). Ele so pode ser derivado INTEIRO depois do corte da
v1.4.3-rc.1, porque depende de FATOS daquele corte — a tag e o commit do veredito da rc.1,
o candidato que ela revisou, o commit-base, o publishedAt do pre-release, o anexo assinado
dos quatro vereditos dela — e do CONTEUDO da 1.4.3 (as condicoes do GA, que carregam as da
rc.1 e o anexo dela, a sonda do GA, o README, a particao e o prompt). No K1 esses fatos e
esse conteudo estao PENDENTES (FACTS_PENDING e CONTENT_PENDING abaixo), e escrever o kit e
RECUSA NOMEADA, que os lista.

O que este estagio entrega e prova:

  CURES — as curas dos P2 do GA herdados do PLAN-193 (rodada 3 da revisao do kit do GA
  v1.4.2) e da rota unica do codex (D-4), cada uma uma EDICAO POR ANCORA EXATA sobre o
  texto do kit do GA v1.4.2, com contagem exigida (zero ou mais de uma e FATAL):

    R3-CLAIMS-01  passo 2: o bump do GA e NO-OP e a arvore da rc.1 esta congelada; o passo
                  nao pede mais que o Owner «releia» o npm/README.md (ele e o da rc.1)
    M3-01 corte   a janela de retomada do G0 entre os passos do envelope e do commit
                  comeca no passo 9 (o passo 10 escreve o envelope ANTES de se marcar)
    M3-02         o banner de PUBLICADO so com os 20 passos concluidos (um --from 19 que
                  pulou o 18 — o publish — nao imprime o banner)
    REGISTRY      a espera do registry no passo 18: GA_NPM_VIEW_TRIES x
                  GA_NPM_VIEW_WAIT_SECONDS (padrao 20 x 30 s; era 5 x 30 s, curta para o
                  CDN do npm no GA v1.4.2), validados
    M3-01 tools   o comentario das classes de morte do runner cita as mensagens MEDIDAS
    R3S-02        no binario do codex 0.160.0, e a historia do pre-run do GA v1.4.1 como o
                  corte a registra (uma tentativa; duas das tres partes); a regex do
                  limite de conta ganha as formas medidas na 0.160.0
    R3S-01        o review record do gerador deixa de caracterizar um P2 especifico do
                  anexo (as condicoes os declaram, pela forma)
    R3H-04        o indice D do harness do GA passa a cobrir B4c/B4d e R2v/R4c/R4d
    D-4           a rota 1 SO no runner do GA (a rota 2, que executava o npx antes de
                  verificar, e recusa nomeada), no passo 6 do corte (o oraculo antes do
                  runner) e no review record do gerador

  A ORDEM do estagio final: estas curas sobre o texto do kit do GA v1.4.2, depois o
  deslocamento de versao (1.4.2 -> 1.4.3, como derive-kit-143.py faz), depois o conteudo e
  os fatos da 1.4.3. Uma cura que cita um corte ANTERIOR (historia) declara o literal em
  CURE_PROTECT, e o --check-cures roda o deslocamento a seco para provar que ele sobrevive.

  --check-cures   aplica as curas em memoria (todas as ancoras), confere cada uma pelo
                  resultado e lista; rc 0 so com todas aplicadas.
  --emit-cured D  escreve em D os quatro arquivos curados (corte, runner, gerador,
                  harness), com o nome de ENSAIO <arquivo>.cured-1.4.2 — material de
                  ensaio do test-ga-kit.sh do K1, nunca um kit.

stdlib only, Python >= 3.9.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import pathlib
import re
import subprocess
import sys
from typing import Dict, List, Optional, Sequence, Tuple

# O derivador da rc.1 e lido como modulo: nenhum .pyc na arvore.
sys.dont_write_bytecode = True

REPO = pathlib.Path(subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"], universal_newlines=True).strip())
MOLD_PLAN = ".claude/plans/PLAN-193"
PLAN = ".claude/plans/PLAN-194"

# O kit do GA v1.4.2 (saidas de derive-ga-kit-142.py, que cortaram o GA publicado).
MOLD = {
    "runner": (MOLD_PLAN + "/repass-ga/run-ga-repass.sh",
               "0b9b4703a766234a9ae9af61c29d95b5759f0c0c60dbe607d848426fe50802ec"),
    "probe": (MOLD_PLAN + "/repass-ga/probe-conditions-ga.py",
              "e46909de69157def1c64b1dc076530839b846bc7148516b19b7639bcfa491407"),
    "cond": (MOLD_PLAN + "/repass-ga/CONDITIONS-ga.md",
             "d439ce46b8025e95207f9e384b083113016089ef4df88093a52fc072313ce76e"),
    "readme": (MOLD_PLAN + "/repass-ga/README-ga.md",
               "ddbcffcf25760faea57ae4c8404d43bb1b1aa24ba5116eee4088237d80f7eb52"),
    "gitignore": (MOLD_PLAN + "/repass-ga/.gitignore",
                  "5ebb406701ece1006960052b161068d9a242388386fd3030bd8ff96216b6b17f"),
    "gen": (MOLD_PLAN + "/gen-envelope-ga.py",
            "f75212ce6a2e6c5c4584ac4d9515aec90db3bcbde42aa80c462b1c26d194f635"),
    "cut": (MOLD_PLAN + "/OWNER-GA-CUT.sh",
            "cbbe2f449e508354716a01a4b85b0837b19873f838d4234d38fad5fbaa2f7d81"),
    "test": (MOLD_PLAN + "/test-ga-kit.sh",
             "fd87a14dbcd8cb284c6584adfb3dabc8f4c1495238406e5ecc0083aa3c3601bd"),
}
DERIVE_GA142 = (MOLD_PLAN + "/derive-ga-kit-142.py",
                "27348f8001d8538036eab61d11c92d3b407add4758a13f5ea53a829352a69f49")
# O derivador do kit da rc.1 da 1.4.3: a rota unica do runner (o MESMO texto nos dois kits)
# vem dele, lido como modulo (nunca executado como script).
DERIVE_RC143 = PLAN + "/derive-kit-143.py"
CURED_KINDS = ("cut", "runner", "gen", "test")
EMIT_NAMES = {"cut": "OWNER-GA-CUT.sh", "runner": "run-ga-repass.sh",
              "gen": "gen-envelope-ga.py", "test": "test-ga-kit.sh"}
EMIT_SUFFIX = ".cured-1.4.2"

# O que so existe depois do corte da v1.4.3-rc.1 (preenchido no estagio final).
FACTS_PENDING = [
    ("RC_TAG_OBJ", "o objeto da tag v1.4.3-rc.1"),
    ("RC_TAG_COMMIT", "o commit do veredito da rc.1 (o commit da tag)"),
    ("RC_CAND", "o candidato que o re-pass da rc.1 revisou (o pai do commit da tag)"),
    ("RC_BASE_COMMIT", "o commit-base contra o qual a rc.1 fez o diff (v1.4.2^{commit})"),
    ("RC_PUBLISHED_AT", "o publishedAt do pre-release da rc.1 (o hold ADR-103 conta dele)"),
    ("RC_ANNEX", "o anexo assinado dos quatro vereditos da rc.1 (P0/P1/P2, pela forma)"),
    ("RC_MAX_PAYLOAD", "o maior payload redigido da rc.1 (o orcamento de bytes do GA)"),
]
CONTENT_PENDING = [
    "as condicoes do GA (as da rc.1 sob o cabecalho do GA, mais o anexo dela aberto)",
    "a sonda do GA (as verificacoes da rc.1 e as do GA sobre a arvore congelada)",
    "o README do GA, a particao, a cobertura e o prompt (a moldura do GA sobre os da rc.1)",
    "o review record do gerador (a rodada da rc.1 e o anexo dela)",
]


def die(msg: str) -> None:
    sys.stderr.write("derive-ga-kit-143: FATAL: %s\n" % msg)
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


def mold(kind: str) -> str:
    return _load(*MOLD[kind])


def sub(text: str, old: str, new: str, what: str, n: int = 1) -> str:
    c = text.count(old)
    if c != n:
        die("ancora %r casou %d vez(es) (exigido: %d)" % (what, c, n))
    return text.replace(old, new)


def cut_region(text: str, start: str, end: str, new: str, what: str) -> str:
    """Troca [start, end) por `new`; `end` preservado; `start` exatamente uma vez."""
    if text.count(start) != 1:
        die("ancora inicial %r casou %d vez(es)" % (what, text.count(start)))
    i = text.index(start)
    j = text.find(end, i + len(start))
    if j < 0:
        die("ancora final de %r ausente" % what)
    return text[:i] + new + text[j:]


def need(text: str, what: str, needles: Sequence[str]) -> None:
    for s in needles:
        if s not in text:
            die("%s curado sem %r" % (what, s))


def forbid(text: str, what: str, needles: Sequence[str]) -> None:
    for s in needles:
        if s in text:
            die("%s curado ainda carrega %r" % (what, s))


def rc143():
    """O derivador da rc.1 da 1.4.3, como MODULO (as constantes da rota unica)."""
    p = REPO / DERIVE_RC143
    if p.is_symlink() or not p.is_file():
        die("%s ausente — a rota unica do runner vem dele" % DERIVE_RC143)
    spec = importlib.util.spec_from_file_location("derive_kit_143", str(p))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    for name in ("RUNNER_ROUTES_START", "RUNNER_ROUTES_END", "RUNNER_ROUTES", "RUNNER_VERIFY_OLD",
                 "RUNNER_VERIFY_NEW", "RUNNER_PKG_OLD"):
        if not isinstance(getattr(m, name, None), str):
            die("%s sem a constante %s" % (DERIVE_RC143, name))
    if "e RECUSA NOMEADA nesta release (PLAN-194 D-4)" not in m.RUNNER_ROUTES:
        die("%s: a rota unica nao recusa a rota 2 pelo nome" % DERIVE_RC143)
    return m


def verify_references() -> None:
    d = _load(*DERIVE_GA142)
    for kind, (rel, _sha) in MOLD.items():
        tail = rel.split(MOLD_PLAN + "/", 1)[1]
        if ('PLAN + "/%s"' % tail) not in d:
            die("derive-ga-kit-142.py nao deriva mais %s — a fonte nao e a saida dele" % tail)


# ===========================================================================
# CURAS — corte (OWNER-GA-CUT.sh)
# ===========================================================================
CUT_DOC2_OLD = "#   Enter       passo 2   confirmar que releu npm/README.md\n"
CUT_DOC2_NEW = ("#   Enter       passo 2   seguir com o bump NO-OP (o npm/README.md e o da rc.1, que a\n"
                "#                         arvore congelada desde a tag dela preserva)\n")
CUT_S2_OLD = ("  printf 'O bump exige que voce tenha RELIDO npm/README.md para esta release.\\n'\n"
              "  printf 'Enter para confirmar que releu (ctrl-C aborta): '\n")
CUT_S2_NEW = ("  # R3-CLAIMS-01: o bump do GA e NO-OP e a arvore da rc.1 esta congelada desde a tag\n"
              "  # dela (o G0 conferiu): o npm/README.md e o MESMO que o passo 2 da rc.1 pediu para\n"
              "  # reler. O driver exige a flag --npm-readme-reviewed mesmo assim; nada a reler aqui.\n"
              "  printf 'O bump do GA e NO-OP: o npm/README.md e o mesmo da rc.1 (a arvore dela esta\\n'\n"
              "  printf 'congelada desde a tag, e o G0 conferiu); o driver exige a flag\\n'\n"
              "  printf '--npm-readme-reviewed, que este passo passa por isso.\\n'\n"
              "  printf 'Enter para seguir com o bump no-op (ctrl-C aborta): '\n")

CUT_WINDOW_DOC_OLD = ("# e recusado pelo nome. Depois do passo 10 o envelope existe NAO rastreado em\n"
                      "# .claude/governance/ (fora do plano), e um passo 11 que morreu entre o `git add` e o\n"
                      "# `git commit` deixa o index com caminhos da lista literal dele: SO nesse intervalo\n"
                      "# (passo 10 concluido, 11 nao, HEAD == candidato) o G0 admite o envelope exato e esse\n"
                      "# staging; o passo 11 entao desfaz o staging (nada foi commitado) e o refaz.\n")
CUT_WINDOW_DOC_NEW = ("# e recusado pelo nome. O passo 10 escreve o envelope NAO rastreado em\n"
                      "# .claude/governance/ (fora do plano) ANTES de se marcar, e um passo 11 que morreu entre\n"
                      "# o `git add` e o `git commit` deixa o index com caminhos da lista literal dele: SO nesse\n"
                      "# intervalo (passo 9 concluido, 11 nao, HEAD == candidato — M3-01: a janela comeca no 9,\n"
                      "# senao uma morte entre a escrita do envelope e o marcador do 10 ficaria sem rota) o G0\n"
                      "# admite o envelope exato e esse staging; o passo 11 entao desfaz o staging (nada foi\n"
                      "# commitado) e o refaz.\n")
CUT_WINDOW_FN_OLD = ("# os dois antes de o passo 11 poder retomar. So neste intervalo (o G0 chama esta funcao\n"
                     "# com o passo 10 concluido e o 11 nao) e com o HEAD no candidato gravado, admite:\n")
CUT_WINDOW_FN_NEW = ("# os dois antes de o passo 11 poder retomar. So neste intervalo (o G0 chama esta funcao\n"
                     "# com o passo 9 concluido e o 11 nao: o passo 10 escreve o envelope ANTES de se marcar,\n"
                     "# M3-01) e com o HEAD no candidato gravado, admite:\n")
CUT_WINDOW_SEL_OLD = "if done_step 10 && ! done_step 11; then\n  tree_clean_resume_11\n"
CUT_WINDOW_SEL_NEW = ("# M3-01: a janela comeca no passo 9 (o 10 escreve o envelope ANTES de se marcar).\n"
                      "if done_step 9 && ! done_step 11; then\n  tree_clean_resume_11\n")

CUT_BANNER_START = "# O banner de PUBLICADO so com o passo 20 concluido. Sem ele: --until parou antes\n"
CUT_BANNER_END = 'bell "$TAG cortada"\n'
CUT_BANNER = r'''# O banner de PUBLICADO so com os 20 passos concluidos (M3-02: um --from que PULOU um
# passo — o 18, o publish, por exemplo — nunca imprime o banner com ele pendente). Sem
# isso: --until parou antes (rc 0, pendentes listados) ou algum passo ficou pendente (rc 3,
# nunca o banner).
_pend="$(pending_steps)"
if [ -n "$_pend" ]; then
  if [ "$UNTIL" -lt 20 ] && ! done_step 20; then
    printf '\nPARADO depois do passo %s (--until). Passos pendentes:%s\n' "$UNTIL" "$_pend"
    printf 'Re-rode este script (sem --until) para seguir de onde parou.\n'
    exit 0
  fi
  printf '\nFAIL: o corte NAO terminou — passos pendentes:%s\n' "$_pend" >&2
  printf '(um --from pulou passo nao concluido? Re-rode sem --from para retomar.)\n' >&2
  exit 3
fi
'''
CUT_BANNER_DOC_OLD = ("# O banner de PUBLICADO so sai com o passo 20 concluido; sem ele o script lista os\n"
                      "# passos pendentes.\n")
CUT_BANNER_DOC_NEW = ("# O banner de PUBLICADO so sai com os 20 passos concluidos (M3-02); sem isso o script\n"
                      "# lista os passos pendentes.\n")

CUT_REGVARS_ANCHOR = ("  ''|*[!0-9]*|0) printf 'FAIL: GA_CI_WAIT_MAX_MIN invalido: %s\\n' \"$CI_WAIT_MAX_MIN\" >&2; exit 1 ;;\n"
                      "esac\n")
CUT_REGVARS = r'''# A espera do registry no passo 18 (o publish do GA): GA_NPM_VIEW_TRIES tentativas de
# `npm view`, GA_NPM_VIEW_WAIT_SECONDS entre elas. No corte do GA v1.4.2 o CDN do npm levou
# MAIS que 5 x 30 s para mostrar a 1.4.2 (o publish ja tinha acontecido) e o corte parou ali
# (LEDGER do PLAN-193); a retomada pelo mesmo comando bastou. Padrao 20 x 30 s (10 min, uma
# estimativa: o atraso so foi medido como «mais que 2,5 min»).
NPM_VIEW_TRIES="${GA_NPM_VIEW_TRIES:-20}"
case "$NPM_VIEW_TRIES" in
  ''|*[!0-9]*|0) printf 'FAIL: GA_NPM_VIEW_TRIES invalido: %s\n' "$NPM_VIEW_TRIES" >&2; exit 1 ;;
esac
NPM_VIEW_WAIT_S="${GA_NPM_VIEW_WAIT_SECONDS:-30}"
case "$NPM_VIEW_WAIT_S" in
  ''|*[!0-9]*) printf 'FAIL: GA_NPM_VIEW_WAIT_SECONDS invalido: %s\n' "$NPM_VIEW_WAIT_S" >&2; exit 1 ;;
esac
'''
CUT_REG_LOOP_OLD = ('  while [ "$_nv" -lt 5 ]; do\n')
CUT_REG_LOOP_NEW = ('  while [ "$_nv" -lt "$NPM_VIEW_TRIES" ]; do\n')
CUT_REG_PRINT_OLD = ("    printf '  ... npm view tentativa %s/5: %s@%s=\"%s\", latest=\"%s\"; aguardando 30s\\n' "
                     "\"$_nv\" \"$NPM_PKG\" \"$BASE\" \"$NPMV\" \"$NPML\"\n"
                     "    sleep 30\n")
CUT_REG_PRINT_NEW = ("    printf '  ... npm view tentativa %s/%s: %s@%s=\"%s\", latest=\"%s\"; aguardando %ss\\n' "
                     "\"$_nv\" \"$NPM_VIEW_TRIES\" \"$NPM_PKG\" \"$BASE\" \"$NPMV\" \"$NPML\" \"$NPM_VIEW_WAIT_S\"\n"
                     "    sleep \"$NPM_VIEW_WAIT_S\"\n")
CUT_REG_DIE_OLD = 'como latest apos 5 tentativas ($BASE='
CUT_REG_DIE_NEW = 'como latest apos $NPM_VIEW_TRIES tentativas de ${NPM_VIEW_WAIT_S}s ($BASE='

CUT_S6_OLD = ("    printf 'O codex roda na versao que o manifesto ADR-182 pina: o binario global, se for\\n'\n"
              "    printf 'o pinado e o payload conferir; senao por npx num cache proprio. Nada e instalado.\\n'\n")
CUT_S6_NEW = ("    printf 'O codex roda na versao que o manifesto ADR-182 pina, SO pela rota 1 (PLAN-194 D-4):\\n'\n"
              "    printf 'o binario global, com o payload conferido pelo oraculo antes de executar. Nada e instalado.\\n'\n"
              "    assert_route1_available\n")
CUT_S6_INFRA_OLD = "(rede, npx, git, gpg, a\nsonda sem medida)"
CUT_S6_INFRA_NEW = "(rede, git, gpg, a\nsonda sem medida)"
CUT_S6_D_OLD = ("conta) e re-rode este script, com  unset OPENAI_API_KEY : ele retoma do passo 6.\n"
                "Qualquer outro caso (veredito ambiguo, main que andou, sonda com afirmacao FALSA): me\n")
CUT_S6_D_NEW = ("conta) e re-rode este script, com  unset OPENAI_API_KEY : ele retoma do passo 6.\n"
                "(d) Caso particular de (b): o runner recusou «rota 1 indisponivel» (o codex global deixou\n"
                "de ser o pinado entre a conferencia deste passo e o runner). Diretorio -infra/ como em (b);\n"
                "instale globalmente a versao que o manifesto pina e re-rode: ele retoma do passo 6.\n"
                "Qualquer outro caso (veredito ambiguo, main que andou, sonda com afirmacao FALSA): me\n")
CUT_ROUTE1_ANCHOR = "# --- a SONDA das condicoes contra um commit ----------------------------------\n"
CUT_ROUTE1 = r'''# --- a rota 1 do codex, antes do runner (PLAN-194 D-4) --------------------------
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


def cure_cut(t: str) -> str:
    t = sub(t, CUT_DOC2_OLD, CUT_DOC2_NEW, "R3-CLAIMS-01: o Enter do passo 2 no cabecalho")
    t = sub(t, CUT_S2_OLD, CUT_S2_NEW, "R3-CLAIMS-01: o passo 2")
    t = sub(t, CUT_WINDOW_DOC_OLD, CUT_WINDOW_DOC_NEW, "M3-01: a janela no cabecalho")
    t = sub(t, CUT_WINDOW_FN_OLD, CUT_WINDOW_FN_NEW, "M3-01: a janela na funcao")
    t = sub(t, CUT_WINDOW_SEL_OLD, CUT_WINDOW_SEL_NEW, "M3-01: o seletor do G0")
    t = sub(t, CUT_BANNER_DOC_OLD, CUT_BANNER_DOC_NEW, "M3-02: o banner no cabecalho")
    t = cut_region(t, CUT_BANNER_START, CUT_BANNER_END, CUT_BANNER, "M3-02: o banner")
    t = sub(t, CUT_REGVARS_ANCHOR, CUT_REGVARS_ANCHOR + CUT_REGVARS, "REGISTRY: as variaveis")
    t = sub(t, CUT_REG_LOOP_OLD, CUT_REG_LOOP_NEW, "REGISTRY: o laco")
    t = sub(t, CUT_REG_PRINT_OLD, CUT_REG_PRINT_NEW, "REGISTRY: a espera")
    t = sub(t, CUT_REG_DIE_OLD, CUT_REG_DIE_NEW, "REGISTRY: a recusa")
    t = sub(t, CUT_ROUTE1_ANCHOR, CUT_ROUTE1 + CUT_ROUTE1_ANCHOR, "D-4: o guard da rota 1")
    t = sub(t, CUT_S6_OLD, CUT_S6_NEW, "D-4: o passo 6")
    t = sub(t, CUT_S6_INFRA_OLD, CUT_S6_INFRA_NEW, "D-4: a rota (b) do passo 6")
    t = sub(t, CUT_S6_D_OLD, CUT_S6_D_NEW, "D-4: a rota (d) do passo 6")
    forbid(t, "corte", ["RELIDO npm/README.md", "done_step 10 && ! done_step 11", "-lt 5 ]",
                        "apos 5 tentativas", "senao por npx", "rede, npx"])
    need(t, "corte", ["if done_step 9 && ! done_step 11; then", '_pend="$(pending_steps)"',
                      'NPM_VIEW_TRIES="${GA_NPM_VIEW_TRIES:-20}"', "    assert_route1_available\n",
                      "Enter para seguir com o bump no-op"])
    return t


# ===========================================================================
# CURAS — runner (run-ga-repass.sh)
# ===========================================================================
RUN_DOC_OLD = ("# dois arquivos de pin sao canonicos e NAO sao editados aqui). Duas rotas: o binario\n"
               "# GLOBAL, quando ele e a versao pinada E o payload confere; senao `npx` num cache\n"
               "# PROPRIO (o npx NAO materializa copia de uma versao ja instalada globalmente). Nas\n"
               "# duas o sha256 do payload nativo e VERIFICADO contra o manifesto (fail-CLOSED, pelo\n"
               "# mesmo oraculo do pair-rail-gate) e um diretorio-shim no inicio do PATH garante que\n"
               "# qualquer `codex` invocado durante o run seja o verificado. A PROVENANCE registra a\n"
               "# rota, o modelo (-m, com a origem) e as mortes por capacidade re-tentadas.\n")
RUN_DOC_NEW = ("# dois arquivos de pin sao canonicos e NAO sao editados aqui). UMA rota (PLAN-194 D-4):\n"
               "# o binario GLOBAL, quando o oraculo do pair-rail-gate (`check_pair_rail.py\n"
               "# --verify-codex-pin`, fail-CLOSED) confere o sha256 do payload nativo contra o manifesto\n"
               "# SEM executa-lo, e so entao ele responde a versao pinada. A rota 2 (`npx` num cache\n"
               "# PROPRIO) executava o pacote baixado antes de verificar: aqui ela e RECUSA NOMEADA. Um\n"
               "# diretorio-shim no inicio do PATH garante que qualquer `codex` invocado durante o run\n"
               "# seja o verificado. A PROVENANCE registra a rota, o modelo (-m, com a origem) e as\n"
               "# mortes do codex re-tentadas.\n")
RUN_CLASSES_START = "#   - LIMITE DE USO/quota da CONTA Codex (mensagens do codex 0.156.1: \"You've hit your\n"
RUN_CLASSES_END = "# As linhas `ERROR: ` do fim do transcript (vazio sem transcript). awk: rc 0 sem casamento.\n"
RUN_CLASSES = r'''#   - LIMITE DE USO/quota da CONTA Codex: NUNCA re-tentado (a conta so volta na hora de
#     reset que o codex imprime), nenhuma parte nova e lancada depois dele, a PROVENANCE o
#     declara (com a hora de reset quando o codex a imprime) e o run termina em RECUSA
#     NOMEADA. Os textos sao os do binario do codex 0.160.0, o pinado (medidos por `strings`
#     em 2026-10-08, nenhuma chamada paga): "You've hit your usage limit ...", "Usage limit
#     reached", "You've reached your usage limit", "Quota exceeded", "... out of credits",
#     "You hit your spend cap ..." e "You've reached your workspace credit limit" — os dois
#     ultimos nao foram medidos na 0.156.1. Numa tentativa do pre-run do re-pass do GA v1.4.1
#     (2026-09-25; LEDGER do PLAN-192) o limite de uso da CONTA matou duas das tres partes, e
#     a PROVENANCE daquela tentativa as contou como mortes "por capacidade".
#   - capacidade do modelo ("at capacity", "Review was interrupted", "experiencing high
#     load"): re-tentada ate 2 vezes, como na rc.1; a fase C declara quantas.
CODEX_ACCOUNT_LIMIT_RE='hit your usage limit|reached your usage limit|Usage limit reached|Quota exceeded|out of credits|hit your spend cap|reached your workspace credit limit'
CODEX_CAPACITY_RE='at capacity|Review was interrupted|experiencing high load'
'''


def cure_runner(t: str, rc) -> str:
    t = sub(t, RUN_DOC_OLD, RUN_DOC_NEW, "D-4: o cabecalho do runner")
    t = cut_region(t, RUN_CLASSES_START, RUN_CLASSES_END, RUN_CLASSES, "M3-01/R3S-02: as classes de morte")
    t = cut_region(t, rc.RUNNER_ROUTES_START, rc.RUNNER_ROUTES_END, rc.RUNNER_ROUTES, "D-4: as rotas do codex")
    t = sub(t, rc.RUNNER_VERIFY_OLD, rc.RUNNER_VERIFY_NEW, "D-4: o oraculo com CLAUDE_PROJECT_DIR")
    t = sub(t, rc.RUNNER_PKG_OLD, "", "D-4: CODEX_PKG (so a rota 2 o usava)")
    forbid(t, "runner", ["npx -y", "NPX_CACHE", "npm_config_cache", "CODEX_PKG", "mensagens do codex 0.156.1",
                         "terminou no limite de uso da conta com a PROVENANCE"])
    need(t, "runner", ["e RECUSA NOMEADA nesta release (PLAN-194 D-4)", "hit your spend cap",
                       "experiencing high load", '_r1_why="nenhum codex no PATH"'])
    return t


# ===========================================================================
# CURAS — gerador (gen-envelope-ga.py)
# ===========================================================================
GEN_R3S01_OLD = ('        "  daqueles vereditos e curado no GA (o da documentacao que pede",\n'
                 '        "  --pin v1.4.2 descrevia a falha enquanto a tag do GA nao existe).",\n')
GEN_R3S01_NEW = ('        "  daqueles vereditos e curado no GA: as condicoes os declaram abertos pela",\n'
                 '        "  forma, e este registro nao caracteriza nenhum deles.",\n')
GEN_REVIEWER_OLD = ('        "- Reviewer: codex-cli na versao que o manifesto ADR-182 pina — o binario",\n'
                    '        "  global quando ele e o pinado, senao npx num cache proprio (a rota esta",\n'
                    '        "  na PROVENANCE) — com o payload nativo VERIFICADO contra o manifesto",\n'
                    '        "  antes de qualquer revisao; versao, triple e sha256 do payload estao em",\n'
                    '        "  tool_versions e sao re-validados por este gerador.",\n')
GEN_REVIEWER_NEW = ('        "- Reviewer: codex-cli na versao que o manifesto ADR-182 pina — so pela",\n'
                    '        "  rota 1 (PLAN-194 D-4): o binario global, com o payload nativo VERIFICADO",\n'
                    '        "  contra o manifesto antes de executar; a rota do npx e recusa nomeada —;",\n'
                    '        "  versao, triple e sha256 do payload estao em tool_versions e sao",\n'
                    '        "  re-validados por este gerador.",\n')


def cure_gen(t: str) -> str:
    t = sub(t, GEN_R3S01_OLD, GEN_R3S01_NEW, "R3S-01: o P2 caracterizado no review record")
    t = sub(t, GEN_REVIEWER_OLD, GEN_REVIEWER_NEW, "D-4: o reviewer no review record")
    forbid(t, "gerador", ["descrevia a falha enquanto a tag do GA nao existe", "senao npx"])
    return t


# ===========================================================================
# CURAS — harness do GA (test-ga-kit.sh)
# ===========================================================================
# R3H-04: os controles vermelhos B4c/B4d (a evidencia da rc.1 no candidato) e R2v/R4c/R4d
# (o G0 real numa corrida fresca) passam a se anotar em _red, e o indice D os exige.
TEST_RED_LINES = [
    ("B4c", '          ok "B4c (controle vermelho): UMA linha do diff-rc1-2.patch mudada no candidato'),
    ("B4d", '          ok "B4d (controle vermelho): o diff-rc1-3.patch AUSENTE do candidato'),
    ("R2v", '      ok "R2v (controle vermelho): o gh release view do v1.4.2 que falha por transporte'),
    ("R4c", '      ok "R4c (controle vermelho): um untracked na RAIZ (fora do plano), numa corrida fresca'),
    ("R4d", '      ok "R4d (controle vermelho): um arquivo RASTREADO modificado e nao commitado, numa corrida fresca'),
]
TEST_D_OLD = ('_d_need "D14 passo 18: registry, latest e recibo do publish" PUB5 PUB6 PUB7-skipped PUB8 PUB9\n')
TEST_D_NEW = ('_d_need "D14 passo 18: registry, latest e recibo do publish" PUB5 PUB6 PUB7-skipped PUB8 PUB9\n'
              '# D15 (R3H-04) — os controles vermelhos que o indice nao cobria: a evidencia da rc.1 no\n'
              '# candidato (B4c conteudo, B4d ausencia) e o G0 real numa corrida fresca (R2v transporte\n'
              '# no gh release view, R4c untracked na raiz, R4d rastreado modificado).\n'
              '_d_need "D15 evidencia da rc.1 no candidato e G0 numa corrida fresca" B4c B4d R2v R4c R4d\n')
TEST_T2_OLD = "         && grep -q 'Enter para confirmar que releu' \"$_r/t2.log\" \\\n"
TEST_T2_NEW = "         && grep -q 'Enter para seguir com o bump no-op' \"$_r/t2.log\" \\\n"
# REGISTRY: os PUB do harness exercitam a recusa depois de 5 tentativas ('tentativa 5/5');
# com o padrao novo (20 x 30 s) o corte real do R passa a receber 5 x 0 s.
TEST_RCUT_OLD = '    ( cd "$_r/wt" && env PATH="$_r/bin:$PATH" GNUPGHOME="$GH" HOME="$SCRATCH/rhome" \\\n'
TEST_RCUT_NEW = ('    ( cd "$_r/wt" && env GA_NPM_VIEW_TRIES=5 GA_NPM_VIEW_WAIT_SECONDS=0 PATH="$_r/bin:$PATH" '
                 'GNUPGHOME="$GH" HOME="$SCRATCH/rhome" \\\n')


def cure_test(t: str) -> str:
    for cid, prefix in TEST_RED_LINES:
        rows = [i for i, ln in enumerate(t.split("\n")) if ln.startswith(prefix)]
        if len(rows) != 1:
            die("R3H-04: a linha do %s casou %d vez(es)" % (cid, len(rows)))
        lines = t.split("\n")
        ln = lines[rows[0]]
        if not ln.endswith('"'):
            die("R3H-04: a linha do %s nao termina no `ok \"...\"`" % cid)
        lines[rows[0]] = ln + '; _red="$_red %s"' % cid
        t = "\n".join(lines)
    t = sub(t, TEST_D_OLD, TEST_D_NEW, "R3H-04: o indice D15")
    t = sub(t, TEST_T2_OLD, TEST_T2_NEW, "R3-CLAIMS-01: o T2 do harness")
    n = t.count(TEST_RCUT_OLD)
    if n < 1:
        die("REGISTRY: o corte real do R (_r_cut) nao achado no harness")
    t = t.replace(TEST_RCUT_OLD, TEST_RCUT_NEW)
    need(t, "harness", ['_d_need "D15 ', '_red="$_red B4c"', '_red="$_red R4d"'])
    return t


# ===========================================================================
def nonascii_vars(kind: str, text: str) -> None:
    """Um `$NOME` colado a um caractere nao-ASCII: o bash de um locale que nao e UTF-8 le o
    1.o byte do caractere como parte do NOME (medido no ensaio do kit da rc.1)."""
    if kind == "gen":
        return
    bad = sorted(set(m.group(0) for m in re.finditer(r"\$[A-Za-z_][A-Za-z0-9_]*(?=[^\x00-\x7f])", text)))
    new = [b for b in bad if b not in NONASCII_MOLD.get(kind, ())]
    if new:
        die("%s curado: variavel colada a caractere nao-ASCII (use ${NOME}): %s" % (kind, ", ".join(new)))


# As que o molde ja trazia (fora do escopo destas curas; o estagio final as corrige no
# deslocamento). Preenchido pelo proprio molde em derive_cured.
NONASCII_MOLD: Dict[str, Tuple[str, ...]] = {}


def derive_cured():
    rc = rc143()
    src = {k: mold(k) for k in CURED_KINDS}
    for k, t in src.items():
        NONASCII_MOLD[k] = tuple(sorted(set(
            m.group(0) for m in re.finditer(r"\$[A-Za-z_][A-Za-z0-9_]*(?=[^\x00-\x7f])", t))))
    out = {
        "cut": cure_cut(src["cut"]),
        "runner": cure_runner(src["runner"], rc),
        "gen": cure_gen(src["gen"]),
        "test": cure_test(src["test"]),
    }
    for k, t in out.items():
        nonascii_vars(k, t)
    return out, rc


# Literais de HISTORIA que as curas trazem (o que aconteceu num corte anterior): o
# deslocamento de versao do estagio final (o `shift` de derive-kit-143.py: 1.4.2 -> 1.4.3,
# 1.4.1 -> 1.4.2, PLAN-192 -> PLAN-193, PLAN-193 -> PLAN-194) tem de os PROTEGER. O
# --check-cures roda esse deslocamento a seco com esta lista e confere que eles sobrevivem.
CURE_PROTECT = {
    "runner": ["): na v1.4.2\n  # ela EXECUTAVA",
               "Numa tentativa do pre-run do re-pass do GA v1.4.1\n#     (2026-09-25; LEDGER do PLAN-192)"],
    "cut": ["No corte do GA v1.4.2 o CDN do npm levou\n# MAIS que 5 x 30 s para mostrar a 1.4.2 (o publish ja "
            "tinha acontecido) e o corte parou ali\n# (LEDGER do PLAN-193)"],
    "gen": [],
    "test": [],
}


def check_protect(out: Dict[str, str], rc) -> List[str]:
    rows = []
    for k in CURED_KINDS:
        lits = CURE_PROTECT[k]
        for lit in lits:
            if out[k].count(lit) != 1:
                die("CURE_PROTECT de %s: %r casou %d vez(es) no curado" % (k, lit[:40], out[k].count(lit)))
        shifted = rc.shift(out[k], k, [(lit, 1) for lit in lits])
        for lit in lits:
            if lit not in shifted:
                die("o deslocamento a seco de %s mudou o literal protegido %r" % (k, lit[:40]))
        bare = [lit for lit in lits if rc.shift(lit, k) == lit]
        if bare:
            die("CURE_PROTECT de %s lista literal que o deslocamento nem tocaria: %r" % (k, bare[0][:40]))
        rows.append("%s: %d literal(is) de historia protegido(s) no deslocamento a seco" % (k, len(lits)))
    return rows


def pending_message() -> str:
    return ("o kit do GA v1.4.3 so deriva INTEIRO depois do corte da v1.4.3-rc.1 — estagio K1: "
            "fatos pendentes: %s; conteudo pendente: %s. Hoje: --check-cures (as curas sobre o kit "
            "do GA v1.4.2, por ancora) e --emit-cured DIR (o material de ensaio)."
            % ("; ".join("%s (%s)" % f for f in FACTS_PENDING), "; ".join(CONTENT_PENDING)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check-cures", action="store_true")
    ap.add_argument("--emit-cured", metavar="DIR")
    a = ap.parse_args()
    verify_references()
    if not a.check_cures and not a.emit_cured:
        die(pending_message())
    out, rc = derive_cured()
    if a.check_cures:
        for row in check_protect(out, rc):
            print("protect %s" % row)
        for k in CURED_KINDS:
            print("%-7s OK  %s (%d linhas curadas; molde sha256 %s)"
                  % (k, MOLD[k][0], out[k].count("\n"), MOLD[k][1][:12]))
        print("--check-cures OK (todas as ancoras aplicadas)")
    if a.emit_cured:
        d = pathlib.Path(a.emit_cured)
        if d.is_symlink() or not d.is_dir():
            die("--emit-cured exige um diretorio existente (nao symlink): %s" % d)
        try:
            d.resolve().relative_to(REPO.resolve())
            die("--emit-cured recusa um diretorio DENTRO do repositorio: o curado e material de ensaio")
        except ValueError:
            pass
        for k in CURED_KINDS:
            p = d / (EMIT_NAMES[k] + EMIT_SUFFIX)
            if p.is_symlink() or (p.exists() and not p.is_file()):
                die("destino nao e arquivo regular: %s" % p)
            p.write_bytes(out[k].encode("utf-8"))
            print("emitido %s (sha256 %s)" % (p, hashlib.sha256(out[k].encode("utf-8")).hexdigest()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
