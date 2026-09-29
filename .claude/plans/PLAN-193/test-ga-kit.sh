#!/bin/bash
# CEREMONY-LINT: handwritten-exception: harness do kit de corte do GA v1.4.2, DERIVADO por
# .claude/plans/PLAN-193/derive-ga-kit-142.py do harness da v1.4.2-rc.1 (test-rc1-kit.sh,
# escrito contra o corpus PLAN-188/ceremony-defect-corpus-S348.md), com a moldura de GA
# que o kit do GA v1.4.1 deu ao harness dele. NAO edite a mao.
#
# test-ga-kit.sh — prova a TUBULACAO inteira do kit sem gastar uma unica
# invocacao de codex e sem tocar na arvore viva.
#
#   bash .claude/plans/PLAN-193/test-ga-kit.sh
#   bash .claude/plans/PLAN-193/test-ga-kit.sh --evidence-only
#
# Onde roda: na arvore do corte do GA — o main da v1.4.2-rc.1, onde entre o commit da tag
# da rc e o HEAD so mudam CLAUDE.md e planos numerados (o G0 do OWNER-GA-CUT.sh recusa o
# resto) —, com o kit do GA derivado no disco, commitado ou nao: a lista FECHADA do kit e
# copiada do DISCO para o upstream DESCARTAVEL da fixture antes do commit do candidato. A
# fixture recria a tag base v1.4.1 nesse upstream, assinada por uma chave descartavel, no
# commit GAKIT_BASE_REV (padrao: o commit da v1.4.1 real) — nada sai do scratch.
#   GAKIT_SCRATCH_PARENT  pai do scratch (padrao /tmp; com um pai longo, o homedir GPG
#                          ganha um ALIAS curto em /tmp, removido na saida).
#
# O que ele faz, em ordem:
#   F.  controles de EVIDENCIA do gerador do GA e dos guards do runner (sem GPG nem rede),
#       inclusive a recusa de evidencia sem a sonda das condicoes VERDE: a linha da
#       PROVENANCE na forma do runner e o RELATORIO probe-ga.txt, que tem de concordar com
#       ela e provar a sonda verde contra ESTE candidato — cada verificacao da lista CHECKS
#       da sonda do kit numa linha OK exatamente uma vez, e a linha MAPA com esses ids (cada
#       forma que nao prova, recusada: um run parcial, uma verificacao repetida ou de outro
#       id, a linha MAPA ausente ou de outros ids);
#   A.  lint estatico: `derive-ga-kit-142.py --check` (o kit do GA no disco e o derivado,
#       byte a byte), `/bin/bash -n` (3.2) + `shellcheck -S warning` nos shells do kit
#       (sem o shellcheck no PATH o A REPROVA: o lint nao roda calado), compilacao EM
#       MEMORIA (sem .pyc) nos pythons, e `check-ceremony-script.py`
#       exigindo ZERO achado BLOCKING nos arquivos do kit;
#   K0. a chave GPG DESCARTAVEL (antes do B: ela assina a tag base da fixture);
#   B.  runner ponta a ponta num CLONE descartavel, com um codex STUB (`CODEX_BIN`) e a
#       base resolvida em tempo de run, no modo do passo 6 do OWNER-GA-CUT.sh
#       (GA_CODEX_JOBS=4; o stub tem uma BARREIRA e prova as 4 partes numa onda so): as
#       4 partes, MANIFEST-ga com 25 entradas, e a conferencia de cada parte com o
#       candidato que a rc.1 revisou (9b5b1b40), na PROVENANCE e no prompt. A classe de
#       MORTE do codex sai SO das linhas `ERROR: ` da coluna 0 nas ultimas 40 linhas do
#       transcript (que ecoa o payload e a saida das ferramentas): cada stub planta as
#       frases das classes FORA dessa janela e no MEIO de uma linha dentro dela. B2: morte
#       por capacidade, re-tentada, com a linha do limite de uso da conta nessas posicoes.
#       B2u: o LIMITE DE USO da CONTA (a linha real do codex, depois de uma de capacidade
#       no fim — a conta vence): sem re-tentativa, recusa nomeada com a hora de reset e a
#       PROVENANCE declarando, em serie (as partes seguintes NAO lancadas) e numa onda so
#       (as 4 mortas, cada uma UMA vez). B2x: uma morte SEM classe no fim, nunca re-tentada
#       nem classificada. B4: um candidato que MUDA a parte 1 — a sonda recusa antes de
#       qualquer codex, e em REPORT-ONLY a conferencia do PROPRIO runner nomeia so a parte
#       mudada (recusa antes do codex dela, ou a declara MUDOU). B4c/B4d: a evidencia da
#       rc.1 no candidato (repass-rc1/diff-rc1-N.patch) com UMA linha mudada (B4c: a recusa
#       do CONTEUDO) ou ausente (B4d: a recusa da AUSENCIA, nunca a do conteudo no lugar
#       dela) — recusa nomeada do runner, antes de qualquer codex. B3 o modelo; B5/B6 a base
#       ausente e a base assinada fora do registro sao recusadas pelo nome;
#   P.  a SONDA das condicoes do GA contra o candidato da fixture (o P0, no B: o resultado
#       REAL de cada afirmacao) e os controles vermelhos. Os herdados da rc: o canario do
#       FN-04 contra o hook da v1.4.1 ACHA a copia (a sonda nao e vacua); um caminho fora
#       de toda parte, um template com ultracode, um plano sem a decisao que uma condicao
#       cita, um veredito pinado alterado, o piso, a re-execucao, o adapter e um arquivo
#       citado da v1.4.0 fora das classes sao recusados pelo nome. Os do GA (P11-P16), cada
#       um pela DIFERENCA entre a sonda INTEIRA sobre o defeito e sobre uma referencia — o
#       candidato sem mudanca, ou uma mudanca inocua dos mesmos arquivos — (sem depender do
#       id da checagem): a arvore de uma parte diferente da do candidato da rc.1; cada uma
#       das tres formas P1 do anexo assinado da rc CURADA (a condicao que as declara
#       abertas ficaria FALSA); o npm-publish.yml que deixa de publicar as tags sem -rc.
#       (o job invertido, e o gatilho que nao casa mais a tag do GA); o shim do npm sem o
#       install.sh; o npm/package.json fora da 1.4.2; o envelope da rc ausente;
#   C a D. o gerador do GA (C), a topologia do commit do veredito (E) e o corte do GA — os
#       gates novos do G0 (o hold ADR-103 da rc e a arvore congelada desde a tag dela), o
#       bump --stable NO-OP, a ordem npm/Release em DRAFT, gh_release_edit_idem e o
#       OWNER-GA-CUT.sh REAL num clone com remoto bare local e num PSEUDO-TERMINAL —, cada
#       controle declarado no `say` da sua secao, e D com UM CONTROLE VERMELHO por classe
#       que o kit cura. Sem controles da relmeta: o GA nao tem relmeta.
#
# Se a sonda das condicoes nao fica verde na fixture (a arvore saiu da rc.1, ou uma
# condicao do GA esta FALSA contra o codigo), o P0 REPROVA com as afirmacoes nomeadas, e
# B/C/E/R seguem em GA_PROBE_REPORT_ONLY=1 — so para exercitar a tubulacao; o C0 prova que
# o gerador RECUSA essa evidencia, e o que depende dela (o C2 em diante) REPROVA por
# construcao: a linha da sonda nunca e reescrita (o gerador a confere contra o probe-ga.txt).
#
# INVARIANTE 8 do PLAN-188 (classe CM-12): este harness NUNCA planta um
# veredito `APPROVE`/`GO` sintetico para destravar um caso verde. O stub do
# codex EMITE `VERDICT: GO-WITH-CONDITIONS` porque e um stub de REVISOR, e essa e a
# saida que um revisor produz; os casos que exercitam RECUSA plantam o defeito e
# esperam recusa.
set -uo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd -P )"
ROOT="$( cd "$SCRIPT_DIR" && git rev-parse --show-toplevel )"
cd "$ROOT" || exit 2

PLAN_DIR=".claude/plans/PLAN-193"
EV="$PLAN_DIR/repass-ga"
SHELLS="
$PLAN_DIR/OWNER-GA-CUT.sh
$PLAN_DIR/test-ga-kit.sh
$EV/run-ga-repass.sh
"
PYS="
$PLAN_DIR/gen-envelope-ga.py
$PLAN_DIR/derive-ga-kit-142.py
$EV/probe-conditions-ga.py
"
# O kit inteiro, lista FECHADA: copiado do DISCO para o upstream da fixture (o ensaio
# exercita os bytes que estao no disco, commitados ou nao).
KIT_FILES="
$PLAN_DIR/OWNER-GA-CUT.sh
$PLAN_DIR/gen-envelope-ga.py
$PLAN_DIR/test-ga-kit.sh
$PLAN_DIR/derive-ga-kit-142.py
$EV/run-ga-repass.sh
$EV/probe-conditions-ga.py
$EV/CONDITIONS-ga.md
$EV/README-ga.md
$EV/.gitignore
"

PASS=0; FAIL=0
ok()   { PASS=$((PASS+1)); printf '  PASS  %s\n' "$*"; }
bad()  { FAIL=$((FAIL+1)); printf '  FAIL  %s\n' "$*"; }
say()  { printf '\n===== %s\n' "$*"; }

# Scratch CURTO por padrao: o socket do gpg-agent estoura o limite de sun_path do
# macOS (~104 bytes) num caminho longo. Medido: "can't connect to the gpg-agent:
# File name too long". GAKIT_SCRATCH_PARENT troca o pai (um ensaio confinado ao
# scratchpad de uma sessao, por exemplo); com um pai longo o homedir GPG ganha um ALIAS
# curto em /tmp (um symlink, removido na saida) — o chaveiro e os sockets ficam
# fisicamente DENTRO do scratch.
SCRATCH_PARENT="${GAKIT_SCRATCH_PARENT:-/tmp}"
[ -d "$SCRATCH_PARENT" ] || { echo "GAKIT_SCRATCH_PARENT nao e diretorio: $SCRATCH_PARENT" >&2; exit 2; }
SCRATCH="$(mktemp -d "$SCRATCH_PARENT/gakit.XXXXXX")" || { echo "mktemp falhou" >&2; exit 2; }
SCRATCH="$(cd "$SCRATCH" && pwd -P)" || { echo "scratch ilegivel" >&2; exit 2; }
# O claude REAL nunca roda neste ensaio: um sentinela no inicio do PATH falha alto se
# algo o chamar sem o stub da secao C (o gerador MEDE `claude --version`).
mkdir -p "$SCRATCH/no-claude" \
  && printf '#!/bin/bash\necho "HARNESS: claude real chamado sem stub" >&2\nexit 97\n' > "$SCRATCH/no-claude/claude" \
  && chmod 0755 "$SCRATCH/no-claude/claude" || { echo "sentinela do claude falhou" >&2; exit 2; }
PATH="$SCRATCH/no-claude:$PATH"; export PATH
# Nenhum .pyc na arvore que o ensaio le (a arvore viva do corte do GA).
PYTHONDONTWRITEBYTECODE=1; export PYTHONDONTWRITEBYTECODE
GH=""; GH_ALIAS=""; FPR=""
cleanup() {
  # Os gpg-agent dos homedirs descartaveis morrem SEMPRE (inclusive numa falha) e o
  # alias curto sai; o scratch so e preservado quando algo falhou.
  local _h
  for _h in "${GH:-}" "${GH2:-}"; do
    [ -n "$_h" ] || continue
    if ! gpgconf --homedir "$_h" --kill all >/dev/null 2>&1; then :; fi
  done
  if [ -n "${GH_ALIAS:-}" ] && [ -L "$GH_ALIAS" ]; then rm -f -- "$GH_ALIAS"; fi
  if [ -n "${GH2_ALIAS:-}" ] && [ -L "$GH2_ALIAS" ]; then rm -f -- "$GH2_ALIAS"; fi
  if [ "$FAIL" -ne 0 ]; then
    printf 'Harness incompleto/falho: fixtures e logs preservados em %s\n' "$SCRATCH" >&2
    return
  fi
  [ -n "${CLONE:-}" ] && [ -d "$CLONE" ] && chmod -R u+w "$CLONE" 2>/dev/null
  rm -rf -- "$SCRATCH" 2>/dev/null
}
trap cleanup EXIT
# Um homedir GPG descartavel com uma chave sem senha; $1 = diretorio, $2 = nome.
# Imprime "<homedir-efetivo> <fpr>" (o homedir pode ser o ALIAS curto).
mk_gpg_home() {
  local _d="$1" _eff _alias="" _fpr
  mkdir -p "$_d" && chmod 700 "$_d" || return 1
  _eff="$_d"
  if [ "${#_d}" -gt 80 ]; then
    _alias="$(mktemp -u /tmp/rk.XXXXXX)" || return 1
    ln -s "$_d" "$_alias" || return 1
    _eff="$_alias"
  fi
  printf '%s\n' '%no-protection' 'Key-Type: eddsa' 'Key-Curve: Ed25519' \
    "Name-Real: $2" 'Expire-Date: 0' '%commit' > "$_d/params"
  GNUPGHOME="$_eff" gpg --batch --quiet --gen-key "$_d/params" > "$_d/keygen.log" 2>&1 || return 1
  _fpr="$(GNUPGHOME="$_eff" gpg --batch --with-colons --list-secret-keys 2>/dev/null \
    | awk -F: '$1=="fpr"{print $10; exit}')"
  [ -n "$_fpr" ] || return 1
  printf '%s %s %s\n' "$_eff" "$_fpr" "$_alias"
}

# F roda sem GPG, provedores ou rede. Importa o gerador real e exercita os
# guards reais do runner sobre fixtures locais; nenhuma aprovacao de teste
# pode sair deste scratch ou ser tratada como evidencia de release.
case "${1:-}" in
  ""|--evidence-only) : ;;
  *) echo "uso: $0 [--evidence-only]" >&2; exit 2 ;;
esac
say "F. partes estritas, condicoes congeladas e preservacao de tentativa"
if python3 - "$ROOT" "$SCRATCH" <<'PY_EVIDENCE'
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from types import ModuleType, SimpleNamespace
from unittest import mock

root, scratch = map(Path, sys.argv[1:])
plan = root / ".claude/plans/PLAN-193"
spec = importlib.util.spec_from_file_location("ga_generator", plan / "gen-envelope-ga.py")
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)
# tool_versions.claude_code e MEDIDO por `claude --version`; estes controles sao das
# guardas de EVIDENCIA e nunca rodam o claude real (a medicao tem a secao C).
gen.claude_code_version = lambda: "claude-code-cli-2.1.999"
ev = scratch / "evidence-controls"
ev.mkdir()
gen.EV = ev
runner = (plan / "repass-ga/run-ga-repass.sh").read_text(encoding="utf-8")
candidate = "0123456789abcdef0123456789abcdef01234567"
conditions = "- RESIDUAL e dado do stub; nunca autoriza NO-GO.\n"
pin = json.loads((root / ".claude/governance/codex-cli-pin-manifest.json").read_text())
digest = pin["payloads"]["aarch64-apple-darwin"]["sha256"]
validator = SimpleNamespace(
    compute_inputs_hash=lambda *args: "1" * 64,
    parse_pin_range=lambda *args: ("0.128.0", "0.148.0"),
    semver_in_range=lambda version, low, high: version == pin["package_version"],
)


def seal():
    names = sorted(set(gen.ARTIFACTS) - {"MANIFEST-ga.sha256"})
    (ev / "MANIFEST-ga.sha256").write_text("".join(
        "%s  %s\n" % (hashlib.sha256((ev / name).read_bytes()).hexdigest(), name)
        for name in names), encoding="ascii")


# Os ids das verificacoes da sonda: o gerador os pina (PROBE_IDS) e exige cada um numa
# linha OK exatamente uma vez. Conferidos aqui contra a lista CHECKS da sonda do kit no
# DISCO (pela AST), para a fixture verde nunca ser feita da mesma lista que ela testa.
import ast
_probe_src = (plan / "repass-ga/probe-conditions-ga.py").read_text(encoding="utf-8")
_checks = [n.value for n in ast.parse(_probe_src).body
           if isinstance(n, (ast.Assign, ast.AnnAssign))
           and any(getattr(t, "id", "") == "CHECKS"
                   for t in (n.targets if isinstance(n, ast.Assign) else [n.target]))]
if len(_checks) != 1 or not isinstance(_checks[0], ast.List):
    raise RuntimeError("sonda do kit sem UMA lista CHECKS literal")
_probe_ids = [e.elts[0].value for e in _checks[0].elts]
if not gen.PROBE_IDS or sorted(gen.PROBE_IDS) != sorted(_probe_ids) \
        or len(set(_probe_ids)) != len(_probe_ids) or "C0-tree" not in gen.PROBE_IDS:
    raise RuntimeError("PROBE_IDS do gerador %r != ids da lista CHECKS da sonda %r"
                       % (gen.PROBE_IDS, _probe_ids))
# A linha MAPA na forma que a sonda escreve (condition_map): os ids de cada condicao na
# ordem da lista CHECKS, SIZE na condicao 11, o cabecalho primeiro e as condicoes em ordem
# numerica — o parse de VARIOS itens do gerador roda no caminho verde.
_probe_by = {}
for _e in _checks[0].elts:
    for _c in _e.elts[2].elts:
        _probe_by.setdefault(_c.value, []).append(_e.elts[0].value)
_probe_by.setdefault("11", []).append("SIZE")
_probe_map = "MAPA condicao -> ids: " + "; ".join(
    "%s: %s" % (k, " ".join(_probe_by[k]))
    for k in sorted(_probe_by, key=lambda k: (-1 if k == "cabecalho" else int(k))))


# O relatorio VERDE da sonda (probe-ga.txt) na forma que a sonda do GA escreve — uma linha
# OK por verificacao de PROBE_IDS, as projecoes de tamanho, a linha MAPA e a linha SONDA —,
# e a linha da PROVENANCE na forma que o runner escreve com a sonda em rc 0 (fase 3b): o
# gerador confere os dois e exige que concordem.
def probe_rows(cand):
    return (["OK   C0-tree: arvore == %s; base ancestral" % cand[:12] if cid == "C0-tree"
             else "OK   %s: afirmacao da fixture conferida" % cid for cid in gen.PROBE_IDS]
            + ["OK   SIZE parte %d: ~100000 B (teto 245616 = MAX_RAW_BYTES - 16384), "
               "1 arquivo(s), 50 linhas de diff" % part for part in gen.PARTS]
            + [_probe_map, "SONDA: 0 FALSA(S), 0 sem medida"])


def probe_label(rows):
    return "verde (%d linhas OK, nenhuma FALSA; probe-ga.txt)" % sum(
        1 for r in rows if r.startswith("OK "))


def write_probe(rows, label=None):
    (ev / "probe-ga.txt").write_text("".join(r + "\n" for r in rows), encoding="utf-8")
    prov = ev / "PROVENANCE-ga.md"
    line = "- sonda das condicoes: " + (label if label is not None else probe_label(rows))
    prov.write_text(re.sub(r"(?m)^- sonda das condicoes: .*$", lambda m: line, prov.read_text()))


def prepare():
    for name in gen.ARTIFACTS:
        (ev / name).write_text("fixture\n", encoding="utf-8")
    (ev / "run-ga-repass.sh").write_text(runner, encoding="utf-8")
    (ev / "CANDIDATE.sha").write_text(candidate + "\n")
    (ev / gen.REVIEWED_CONDITIONS).write_text(conditions, encoding="utf-8")
    (ev / "CONDITIONS-ga.md").write_text(conditions, encoding="utf-8")
    cond_hash = hashlib.sha256(conditions.encode()).hexdigest()
    (ev / "PROVENANCE-ga.md").write_text(
        "Candidato: %s\n- codex: %s / aarch64-apple-darwin / payload %s\n"
        "- condicoes declaradas no prompt (DATA para o revisor): "
        "CONDITIONS-ga.reviewed.md sha256 %s\n"
        "- sonda das condicoes: %s\n"
        "RUNNER-OVERALL: rc=0\n"
        % (candidate, pin["package_version"], digest, cond_hash,
           probe_label(probe_rows(candidate))), encoding="utf-8")
    (ev / "probe-ga.txt").write_text("".join(r + "\n" for r in probe_rows(candidate)),
                                     encoding="utf-8")
    # Saida de um revisor stub local, nao de qualquer provedor.
    for part in gen.PARTS:
        (ev / ("verdict-ga-%d.txt" % part)).write_text(
            "STUB REVIEW\nVERDICT: %s explicacao do stub\n"
            % ("GO" if part % 2 else "GO-WITH-CONDITIONS"), encoding="utf-8")
    seal()


checks = 0


def refuses(label, action, reason):
    global checks
    error = io.StringIO()
    try:
        with contextlib.redirect_stderr(error):
            action()
    except SystemExit as exc:
        if exc.code != 2 or reason not in error.getvalue():
            raise RuntimeError("%s: recusa errada: %s" % (label, error.getvalue()))
        checks += 1
        print("  CONTROL PASS: " + label)
        return
    raise RuntimeError("ACEITOU: " + label)


with mock.patch.object(gen, "load_validator", return_value=validator):
    prepare()
    fields = gen.build_fields(candidate, conditions)
    gen.verify_fields_evidence(fields)
    if not fields.startswith("verdict: GO-WITH-CONDITIONS\n"):
        raise RuntimeError("os GO/GWC validos nao produziram GWC")
    checks += 1
    for part in gen.PARTS:
        prepare()
        (ev / ("verdict-ga-%d.txt" % part)).write_text("VERDICT: NO-GO\n")
        seal()
        refuses("NO-GO + RESIDUAL na parte %d" % part,
                lambda: gen.build_fields(candidate, conditions), "rail NO-GO")
    for text in ("VERDICT: GO\nVERDICT: GO\n", "VERDICT: GO-WITH-CONDITIONS-extra\n", "sem veredito\n"):
        prepare()
        (ev / "verdict-ga-4.txt").write_text(text)
        seal()
        refuses("veredito ambiguo/ilegivel", lambda: gen.build_fields(candidate, conditions), "VERDICT")
    prepare()
    (ev / "verdict-ga-4.txt").unlink()
    refuses("ultima parte ausente", lambda: gen.build_fields(candidate, conditions), "artefato ausente")
    prepare()
    refuses("condicoes fornecidas alteradas", lambda: gen.build_fields(candidate, conditions + "novo\n"), "diferem das revisadas")
    (ev / "CONDITIONS-ga.md").write_text(conditions + "novo\n")
    refuses("fonte alterada depois da revisao", lambda: gen.build_fields(candidate, conditions), "mudaram desde a revisao")
    prepare()
    (ev / gen.REVIEWED_CONDITIONS).write_text(conditions + "novo\n")
    seal()
    refuses("snapshot alterado com MANIFEST recalculado", lambda: gen.build_fields(candidate, conditions), "hash da PROVENANCE")
    prepare()
    fields = gen.build_fields(candidate, conditions)
    refuses("fields alterados apos assinatura", lambda: gen.verify_fields_evidence(fields.replace("verdict: GO-WITH-CONDITIONS", "verdict: GO", 1)), "fields assinados divergem")
    (ev / "diff-ga-1.patch").write_text("outro diff\n")
    seal()
    refuses("evidencia alterada apos fields", lambda: gen.verify_fields_evidence(fields), "fields assinados divergem")
    prepare()
    manifest = ev / "MANIFEST-ga.sha256"
    manifest.write_text("\n".join(manifest.read_text().splitlines()[1:]) + "\n")
    refuses("MANIFEST omite artefato", lambda: gen.build_fields(candidate, conditions), "exatamente os 25")
    prepare()
    prov = ev / "PROVENANCE-ga.md"
    prov.write_text(prov.read_text().replace("RUNNER-OVERALL: rc=0", "RUNNER-OVERALL: rc=1"))
    seal()
    refuses("runner incompleto com vereditos GO", lambda: gen.build_fields(candidate, conditions), "RUNNER-OVERALL")
    # A sonda das condicoes que NAO ficou verde no run (modo REPORT-ONLY do harness, ou
    # um runner trocado sem a linha) nunca vira fields.
    for bad_probe in ("- sonda das condicoes: VERMELHA (rc=1) em modo REPORT-ONLY do harness\n", ""):
        prepare()
        prov = ev / "PROVENANCE-ga.md"
        prov.write_text(re.sub(r"(?m)^- sonda das condicoes: .*\n", bad_probe, prov.read_text()))
        seal()
        refuses("sonda das condicoes nao verde (%s)" % ("vermelha" if bad_probe else "linha ausente"),
                lambda: gen.build_fields(candidate, conditions), "sonda das condicoes")
    # O RELATORIO da sonda (probe-ga.txt, pinado pelo MANIFEST) tem de provar a sonda
    # VERDE contra ESTE candidato e concordar com a linha da PROVENANCE: cada forma que
    # nao prova isso e recusada pelo nome, com o MANIFEST recalculado sobre ela.
    green = probe_rows(candidate)
    for label, rows, prov_label, reason in (
        ("linha da sonda fora da forma do runner", green,
         "verde (fixture dos controles de evidencia)", "nao tem a forma que o runner"),
        ("relatorio da sonda vazio", [], probe_label(green), "nao termina em"),
        ("relatorio da sonda com uma afirmacao FALSA",
         green[:-1] + ["FAIL C9-fixture: afirmacao FALSA plantada"] + green[-1:], None,
         "afirmacao FALSA ou sem medida"),
        ("relatorio da sonda com uma afirmacao sem medida",
         green[:-1] + ["INFRA C9-fixture: sem medida plantada"] + green[-1:], None,
         "afirmacao FALSA ou sem medida"),
        ("relatorio da sonda com duas linhas SONDA", green + green[-1:], None,
         "mais de uma linha SONDA"),
        ("PROVENANCE declara mais linhas OK que o relatorio", green,
         probe_label(green + ["OK   C2-fixture: a mais"]), "a PROVENANCE declara"),
        ("relatorio da sonda de OUTRO candidato",
         [r.replace(candidate[:12], "f" * 12) for r in green], None, "DESTE candidato"),
        ("relatorio da sonda sem a projecao de uma parte",
         [r for r in green if not r.startswith("OK   SIZE parte %d:" % gen.PARTS[-1])], None,
         "nao projeta o tamanho"),
        # Um run PARCIAL (verificacoes que nao rodaram), repetido ou forjado: cada forma
        # recusada pelo nome, com o rotulo da PROVENANCE contando o proprio relatorio.
        ("relatorio da sonda so com a arvore e as projecoes (nenhuma verificacao das condicoes)",
         [r for r in green if not r.startswith("OK   ") or r.startswith(("OK   C0-tree: ", "OK   SIZE"))],
         None, "nao tem a linha OK de %d verificacao" % (len(gen.PROBE_IDS) - 1)),
        ("relatorio da sonda sem UMA verificacao",
         [r for r in green if not r.startswith("OK   %s: " % gen.PROBE_IDS[-1])], None,
         "nao tem a linha OK de 1 verificacao(oes) da sonda do kit (%s)" % gen.PROBE_IDS[-1]),
        ("relatorio da sonda com uma verificacao repetida NO LUGAR de outra",
         [green[1] if r.startswith("OK   %s: " % gen.PROBE_IDS[-1]) else r for r in green], None,
         "(%s)" % gen.PROBE_IDS[-1]),
        ("relatorio da sonda com uma verificacao repetida", green[:-2] + [green[1]] + green[-2:],
         None, "repete a linha OK de"),
        ("relatorio da sonda com uma linha OK de outro id",
         green[:-2] + ["OK   C99-fixture: forjada"] + green[-2:], None,
         "nao e de verificacao da sonda do kit"),
        ("relatorio da sonda sem a linha MAPA", [r for r in green if not r.startswith("MAPA")],
         None, "linha(s) MAPA"),
        ("relatorio da sonda com a linha MAPA de outros ids",
         [r.replace(" SIZE", " C99-fixture SIZE") if r.startswith("MAPA") else r for r in green],
         None, "outros ids"),
    ):
        prepare()
        write_probe(rows, prov_label)
        seal()
        refuses(label, lambda: gen.build_fields(candidate, conditions), reason)
    prepare()
    for part in gen.PARTS:
        (ev / ("verdict-ga-%d.txt" % part)).write_text("VERDICT: GO explicacao do stub\n")
    seal()
    if not gen.build_fields(candidate, conditions).startswith("verdict: GO\n"):
        raise RuntimeError("os GO validos nao produziram GO")
    checks += 1

# Executar os guards reais (sem base/GPG/provider/worktree), inclusive os
# efeitos sobre o disco. Um arquivo parcial deve sobreviver byte a byte.
start = runner.index("assert_attempt_absent() {")
end = runner.index("\n}\n", start) + 3
guard_function = runner[start:end]
init = runner[runner.index('CONDITIONS_SOURCE="$OUT/CONDITIONS-ga.md"'):runner.index("# --- 0.")]
prefix = 'set -uo pipefail\ndie() { printf "FATAL: %s\\n" "$*" >&2; exit 1; }\n'
for number, artifact in enumerate(("verdict-ga-1.txt", "transcript-ga-4.log", "payload-ga-2.raw.txt", "MANIFEST-ga.sha256.tmp", "probe-ga.txt", gen.REVIEWED_CONDITIONS)):
    out = scratch / ("partial-%d" % number)
    out.mkdir()
    path = out / artifact
    path.write_bytes(b"partial evidence\x00preserve\n")
    result = subprocess.run(["bash", "-c", prefix + guard_function + "\nassert_attempt_absent\n"],
                            env=dict(os.environ, OUT=str(out)), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 1 or path.read_bytes() != b"partial evidence\x00preserve\n":
        raise RuntimeError("tentativa parcial nao preservada: " + artifact)
    checks += 1
for number, mutation in enumerate(("", 'printf novo >> "$CONDITIONS_SOURCE"', 'printf novo >> "$CONDITIONS_SNAPSHOT"', 'printf novo >> "$OUT/run-ga-repass.sh"')):
    out = scratch / ("freeze-%d" % number)
    out.mkdir()
    (out / "run-ga-repass.sh").write_text(runner)
    (out / "CONDITIONS-ga.md").write_text(conditions)
    result = subprocess.run(["bash", "-c", prefix + guard_function + init + "\n" + mutation + "\nassert_conditions_unchanged\n"],
                            env=dict(os.environ, OUT=str(out)), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    expected = 0 if not mutation else 1
    if result.returncode != expected:
        raise RuntimeError("guard de congelamento: %s: %s" % (mutation, result.stderr.decode()))
    checks += 1
start = runner.index("quarantine_raw() {")
end = runner.index("\n}\n", start) + 3
quarantine_function = runner[start:end]
quarantines = []
# Codex review of the cure: quarantine_raw writes under $HOME/.rc2-backup; without an
# isolated HOME this control left two fixture directories in the REAL home per run.
home = scratch / "home"
home.mkdir()
for number in (1, 2):
    out = scratch / ("quarantine-input-%d" % number)
    out.mkdir()
    raw = out / "payload-ga-1.raw.txt"
    raw.write_text("attempt %d\n" % number)
    result = subprocess.run(["bash", "-c", prefix + quarantine_function +
                             '\nRAW_QUARANTINE=""\nquarantine_raw "$RAW_INPUT"\nprintf "%s" "$RAW_QUARANTINE"\n'],
                            env=dict(os.environ, RAW_INPUT=str(raw), HOME=str(home)), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    dest = Path(result.stdout.decode()) / raw.name
    if result.returncode != 0 or dest.read_text() != "attempt %d\n" % number or raw.exists():
        raise RuntimeError("quarentena nao preservou a tentativa")
    if home not in dest.parents:
        raise RuntimeError("quarentena fora do HOME do ensaio: %s" % dest)
    quarantines.append(dest)
if quarantines[0] == quarantines[1] or quarantines[0].read_text() != "attempt 1\n":
    raise RuntimeError("nova quarentena sobrescreveu a anterior")
checks += 1
print("EVIDENCE CONTROLS: %d PASS, 0 FAIL (stubs locais; nenhuma assinatura/revisao real)" % checks)
PY_EVIDENCE
then ok "F: controles de evidencia passaram"
else bad "F: controles de evidencia falharam"; fi
if [ "${1:-}" = "--evidence-only" ]; then
  printf '\n===== RESULTADO: %s PASS, %s FAIL\n' "$PASS" "$FAIL"
  [ "$FAIL" -eq 0 ] || exit 1
  exit 0
fi

# ===========================================================================
say "A. lint estatico"
if python3 "$PLAN_DIR/derive-ga-kit-142.py" --check > "$SCRATCH/derive-check.log" 2>&1; then
  ok "A0: derive-ga-kit-142.py --check (o kit do GA no disco e o derivado, byte a byte)"
else bad "A0: derive-ga-kit-142.py --check FALHOU"; sed -n '1,14p' "$SCRATCH/derive-check.log"; fi
# O shellcheck AUSENTE nao e verde: o lint -S warning dos shells do kit e uma das provas
# do A (o cabecalho a declara); sem ele o A contaria so os outros itens, calado.
_sc=0
if command -v shellcheck >/dev/null 2>&1; then _sc=1
else bad "A: shellcheck AUSENTE do PATH — o lint -S warning dos shells do kit NAO rodou (instale o shellcheck e re-rode)"; fi
for f in $SHELLS; do
  [ -f "$f" ] || { bad "ausente: $f"; continue; }
  if /bin/bash -n "$f" 2>/dev/null; then ok "/bin/bash -n $(basename "$f") ($(/bin/bash -c 'echo $BASH_VERSION' | cut -c1-3))"; else bad "/bin/bash -n $(basename "$f")"; fi
  if [ "$_sc" -eq 1 ]; then
    if shellcheck -S warning "$f" >/dev/null 2>&1; then
      ok "shellcheck $(basename "$f")"
    else
      bad "shellcheck $(basename "$f")"; shellcheck -S warning "$f" 2>&1 | sed -n '1,12p'
    fi
  fi
done
for f in $PYS; do
  [ -f "$f" ] || { bad "ausente: $f"; continue; }
  if python3 - "$f" > /dev/null 2>&1 <<'PYC'
import sys
with open(sys.argv[1], "rb") as fh:
    compile(fh.read(), sys.argv[1], "exec")
PYC
  then ok "compile $(basename "$f") (em memoria, sem .pyc)"; else bad "compile $(basename "$f")"; fi
done

say "A2. ceremony-lint: ZERO achado BLOCKING nos arquivos do kit"
_cl="$SCRATCH/ceremony.json"
if python3 .claude/scripts/check-ceremony-script.py --root "$ROOT" --json > "$_cl" 2>/dev/null; then :; fi
# So os arquivos DESTE kit (a lista fechada): o plano abriga tambem as cerimonias das
# outras lanes, que tem os seus proprios ensaios. Os tres shells do kit TEM de estar entre
# os varridos — senao a conferencia seria vacua.
# shellcheck disable=SC2086
_nb="$(python3 - "$_cl" $KIT_FILES <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
kit = set(sys.argv[2:])
mine = [f for f in d["files"] if f["file"] in kit]
if len([f for f in mine if f["file"].endswith(".sh")]) < 3:
    print("os shells do kit nao foram varridos: %r" % sorted(f["file"] for f in mine), file=sys.stderr)
    print("VACUO")
    sys.exit(0)
bl = [(f["file"], x) for f in mine for x in f["findings"] if x["sev"] == "BLOCKING"]
for p, x in bl:
    print("BLOCKING %s %s L%s %s" % (p, x["rule"], x["line"], x["msg"]), file=sys.stderr)
print(len(bl))
PY
)" || _nb="ERRO"
if [ "$_nb" = "0" ]; then ok "ceremony-lint: 0 BLOCKING nos arquivos do kit"
else bad "ceremony-lint: $_nb achado(s) BLOCKING"; fi

# ===========================================================================
say "K0. chave GPG DESCARTAVEL (assina a tag base da fixture e os fields)"
_k0="$(mk_gpg_home "$SCRATCH/gnupg" "ga kit selftest")" || _k0=""
if [ -n "$_k0" ]; then
  GH="$(printf '%s' "$_k0" | awk '{print $1}')"; FPR="$(printf '%s' "$_k0" | awk '{print $2}')"
  GH_ALIAS="$(printf '%s' "$_k0" | awk '{print $3}')"
  ok "chave descartavel criada ($(printf '%s' "$FPR" | cut -c1-12)); homedir ${GH_ALIAS:+(alias curto) }$GH"
else bad "K0: gpg --gen-key falhou no homedir temporario"; sed -n '1,12p' "$SCRATCH/gnupg/keygen.log" 2>/dev/null; fi
# A mesma variavel que o runner, o G0 e o gerador leem: o seam de auto-teste, recusado
# fora deste scratch.
SELFTEST_ENV="GA_SELFTEST=1 GA_SELFTEST_SCRATCH=$SCRATCH GA_SELFTEST_SIGNER_FPR=$FPR"

# ===========================================================================
say "B. runner ponta a ponta num clone descartavel, com codex STUB"
fixture_git_identity() {
  git -C "$1" config --local user.name "ga kit fixture" \
    && git -C "$1" config --local user.email "ga-kit@invalid" \
    && git -C "$1" config --local commit.gpgsign false
}
# A autoria tem de estar ANTES do candidato revisado. Copiar README/kit do
# workingtree depois de fixar CAND fazia o ensaio publicar texto nao revisado
# junto da evidencia; o guard recusava corretamente esse delta. Materializar
# a delta rastreada inteira em um upstream LOCAL descartavel reproduz a
# topologia real: autoria -> candidato -> revisao -> evidencia + assinatura.
# ROOT e somente lido; nenhuma branch/index/config dele e alterada.
UPSTREAM="$SCRATCH/upstream"
_fixture_base="$(git rev-parse HEAD)"
_fixture_patch="$SCRATCH/prepared.patch"
_fixture_ok=1
git diff --binary HEAD -- > "$_fixture_patch" || _fixture_ok=0
git clone --quiet --local --shared --no-checkout "$ROOT" "$UPSTREAM" 2>/dev/null || _fixture_ok=0
if [ "$_fixture_ok" -eq 1 ]; then
  git -C "$UPSTREAM" checkout --quiet -B main "$_fixture_base" \
    && fixture_git_identity "$UPSTREAM" || _fixture_ok=0
fi
if [ "$_fixture_ok" -eq 1 ] && [ -s "$_fixture_patch" ]; then
  git -C "$UPSTREAM" apply --index --binary "$_fixture_patch" || _fixture_ok=0
fi
# O kit pode estar UNTRACKED na arvore (derivado e ainda nao commitado): `git diff
# HEAD` nao o carrega e um clone de HEAD nao o ve. A lista FECHADA e copiada do DISCO
# para o upstream da fixture ANTES do commit do candidato.
if [ "$_fixture_ok" -eq 1 ]; then
  for _kf in $KIT_FILES; do
    if [ ! -f "$ROOT/$_kf" ] || [ -L "$ROOT/$_kf" ]; then
      bad "kit: $_kf ausente ou nao-regular no disco"; _fixture_ok=0; break
    fi
    mkdir -p "$UPSTREAM/$(dirname "$_kf")" && cp -- "$ROOT/$_kf" "$UPSTREAM/$_kf" \
      && git -C "$UPSTREAM" add -- "$_kf" || { _fixture_ok=0; break; }
  done
  [ "$_fixture_ok" -eq 1 ] && ok "kit copiado do disco para o upstream da fixture (lista fechada de 9)"
fi
if [ "$_fixture_ok" -eq 1 ]; then
  git -C "$UPSTREAM" commit --quiet --allow-empty -m "TEST ONLY: prepared candidate before stub review" \
    || _fixture_ok=0
fi
# A BASE da fixture: a tag v1.4.1 RECRIADA no upstream descartavel, anotada e assinada
# pela chave descartavel, no commit GAKIT_BASE_REV (padrao: o commit da v1.4.1 real).
# Ela nunca sai do scratch; o runner, o G0 e o gerador a aceitam pelo seam de auto-teste.
BASE_REV=""
if [ "$_fixture_ok" -eq 1 ]; then
  BASE_REV="${GAKIT_BASE_REV:-}"
  if [ -z "$BASE_REV" ]; then
    BASE_REV="$(git rev-parse -q --verify 'refs/tags/v1.4.1^{commit}' 2>/dev/null)" || BASE_REV=""
  fi
  BASE_REV="$(git rev-parse -q --verify "${BASE_REV:-none}^{commit}" 2>/dev/null)" || BASE_REV=""
  if [ -z "$BASE_REV" ] || [ -z "$FPR" ]; then
    bad "B: sem base (a tag v1.4.1 nao existe aqui e GAKIT_BASE_REV nao foi passado) ou sem chave"
    _fixture_ok=0
  else
    git -C "$UPSTREAM" tag -d v1.4.1 >/dev/null 2>&1 || :
    if GNUPGHOME="$GH" git -C "$UPSTREAM" -c user.signingkey="$FPR" -c gpg.program=gpg \
         tag -s -m "TEST ONLY: base da fixture" v1.4.1 "$BASE_REV" 2>"$SCRATCH/basetag.log"; then
      ok "B: tag base v1.4.1 da fixture assinada pela chave descartavel em $(printf '%s' "$BASE_REV" | cut -c1-12)"
    else bad "B: nao consegui assinar a tag base da fixture"; sed -n '1,6p' "$SCRATCH/basetag.log"; _fixture_ok=0; fi
  fi
fi
CLONE="$SCRATCH/clone"
if [ "$_fixture_ok" -eq 1 ] \
   && git clone --quiet --local --shared "$UPSTREAM" "$CLONE" 2>/dev/null; then
  ok "candidato preparado em upstream local; clone de revisao criado"
else
  bad "preparacao do candidato/clone local falhou — pulando B e C"
  CLONE=""
fi

if [ -n "$CLONE" ]; then
  # O origin e exclusivamente o upstream da fixture, com a autoria ja
  # commitada. Nenhum acesso remoto aponta para o repositorio ativo.
  CAND="$(git -C "$CLONE" ls-remote origin refs/heads/main | awk '{print $1}')"
  if [ -z "$CAND" ]; then
    bad "ls-remote de main no clone falhou"
  else
    git -C "$CLONE" checkout --quiet --detach "$CAND" 2>/dev/null \
      || bad "checkout do candidato no clone falhou"
    printf '%s\n' "$CAND" > "$CLONE/$EV/CANDIDATE.sha"
    # P0 — a SONDA das condicoes contra o candidato da fixture: o resultado REAL de cada
    # afirmacao. Vermelha = FAIL nomeado aqui, e o runner segue em modo REPORT-ONLY so
    # para a tubulacao (o gerador recusa essa evidencia: C).
    PROBE_ENV=""
    if ( cd "$CLONE" && PYTHONDONTWRITEBYTECODE=1 python3 "$EV/probe-conditions-ga.py" \
           --root "$CLONE" --base refs/tags/v1.4.1 --head HEAD --sizes ) > "$SCRATCH/probe0.log" 2>&1; then
      ok "P0: sonda das condicoes VERDE contra o candidato da fixture ($(grep -c '^OK ' "$SCRATCH/probe0.log") linhas OK)"
    else
      bad "P0: sonda das condicoes NAO verde contra o candidato da fixture:"
      grep -E '^(FAIL|INFRA)' "$SCRATCH/probe0.log" | sed 's/^/        /'
      PROBE_ENV="GA_PROBE_REPORT_ONLY=1"
    fi
    grep -E '^OK +SIZE' "$SCRATCH/probe0.log" | sed 's/^/        /'
    # Stub do codex: le o payload da stdin, escreve o veredito no arquivo
    # apontado por --output-last-message. NAO e um plant de aprovacao: e o
    # que um revisor emite. Os casos de RECUSA estao no bloco D.
    # GA: o B roda como o passo 6 do OWNER-GA-CUT.sh (GA_CODEX_JOBS=4). O stub tem uma
    # BARREIRA: cada chamada registra a sua partida em bj/starts/ e espera (ate 60 s) ver
    # as 4, e grava quantas viu em bj/seen/ — o veredito sai de qualquer forma.
    mkdir -p "$SCRATCH/bj/starts" "$SCRATCH/bj/seen"
    STUB="$SCRATCH/bj/codex"
    cat > "$STUB" <<'STUBEOF'
#!/bin/bash
out=""
prev=""
for a in "$@"; do
  [ "$prev" = "--output-last-message" ] && out="$a"
  prev="$a"
done
bytes=$(wc -c)
[ -n "$out" ] || { echo "stub: sem --output-last-message" >&2; exit 3; }
d="$(dirname "$0")"; n="$(basename "$out")"
: > "$d/starts/$n.$$"; i=0
while [ "$(find "$d/starts" -type f | grep -c .)" -lt 4 ] && [ "$i" -lt 600 ]; do sleep 0.1; i=$((i + 1)); done
find "$d/starts" -type f | grep -c . >> "$d/seen/$n"
printf 'STUB REVIEW: li %s bytes de payload pela stdin.\n' "$bytes" > "$out"
printf 'VERDICT: GO-WITH-CONDITIONS cobertura declarada no README-ga.\n' >> "$out"
printf 'stub: payload de %s bytes\n' "$bytes"
STUBEOF
    chmod 0755 "$STUB"
    _run="$SCRATCH/runner.log"
    # O GNUPGHOME e o DESCARTAVEL (a tag base da fixture e dele); nunca o chaveiro real.
    _test_gnupg="$GH"
    # shellcheck disable=SC2086
    if ( cd "$CLONE" && env CODEX_BIN="$STUB" CODEX_MODEL=stub-model HOME="$SCRATCH/fakehome" \
         GA_CODEX_JOBS=4 GNUPGHOME="$_test_gnupg" $SELFTEST_ENV $PROBE_ENV \
         bash "$EV/run-ga-repass.sh" ) > "$_run" 2>&1; then
      ok "runner completou as 4 partes com GA_CODEX_JOBS=4, o modo do passo 6 do OWNER-GA-CUT.sh (rc 0)"
    else
      bad "runner rc!=0"; sed -n '1,25p' "$_run"
    fi
    _ml="$(grep -c . "$CLONE/$EV/MANIFEST-ga.sha256" 2>/dev/null || echo 0)"
    if [ "$_ml" = "25" ]; then ok "MANIFEST-ga com 25 entradas (4 partes x 5 + PROVENANCE, CANDIDATE, runner, condicoes, sonda)"
    else bad "MANIFEST-ga com $_ml entradas (esperado 25)"; fi
    if grep -q '^probe-ga.txt$' <<MANI
$(awk '{print $2}' "$CLONE/$EV/MANIFEST-ga.sha256" 2>/dev/null)
MANI
    then ok "B: a saida da sonda (probe-ga.txt) esta no MANIFEST"
    else bad "B: probe-ga.txt fora do MANIFEST"; fi
    if grep -q '^- sonda das condicoes: ' "$CLONE/$EV/PROVENANCE-ga.md" 2>/dev/null \
       && grep -q "^- base assinada por: $FPR$" "$CLONE/$EV/PROVENANCE-ga.md" 2>/dev/null; then
      ok "B: a PROVENANCE declara a sonda ($(grep '^- sonda das condicoes: ' "$CLONE/$EV/PROVENANCE-ga.md" | cut -c24-40)...) e o signatario da base resolvida"
    else bad "B: a PROVENANCE sem a linha da sonda ou do signatario da base"; fi
    if ( cd "$CLONE/$EV" && shasum -a 256 -c MANIFEST-ga.sha256 --status ); then
      ok "MANIFEST-ga verifica"
    else bad "MANIFEST-ga nao verifica"; fi
    if grep -q '^RUNNER-OVERALL: rc=0' "$CLONE/$EV/PROVENANCE-ga.md" 2>/dev/null; then
      ok "PROVENANCE com RUNNER-OVERALL rc=0"
    else bad "PROVENANCE sem RUNNER-OVERALL rc=0"; fi
    # Nenhum payload RAW pode ter sobrado na arvore (eles vao para quarentena).
    if ls "$CLONE/$EV"/payload-ga-*.raw.txt >/dev/null 2>&1; then
      bad "sobrou payload RAW na arvore do clone"
    else ok "nenhum payload RAW na arvore (quarentena funcionou)"; fi
    # GA: a conferencia de cada parte com o candidato que a rc.1 revisou (9b5b1b40). Na
    # fixture o candidato e o HEAD (desde aquele candidato so mudaram CLAUDE.md, planos e o
    # envelope da rc) mais o kit do GA, tudo FORA das pathspecs: as 4 partes saem SEM mudanca.
    _same="$(grep -c '^  - diff-ga-[1-4]\.patch: sem mudanca na pathspec desde o candidato da rc\.1 (9b5b1b40)$' "$CLONE/$EV/PROVENANCE-ga.md" 2>/dev/null)" || _same=0
    if [ "$_same" = "4" ]; then ok "B: a PROVENANCE declara as 4 pathspecs sem mudanca desde o candidato da rc.1 (9b5b1b40)"
    else bad "B: a PROVENANCE declara $_same pathspec(s) sem mudanca desde a rc.1 (esperado 4)"; grep -n 'diff-ga-' "$CLONE/$EV/PROVENANCE-ga.md" 2>/dev/null; fi
    _samep=0
    for _n in 1 2 3 4; do
      if grep -qF "no file of this part's pathspec differs between the rc.1 candidate 9b5b1b40" \
           "$CLONE/$EV/payload-ga-$_n.redacted.txt" 2>/dev/null; then _samep=$((_samep + 1)); fi
    done
    if [ "$_samep" = "4" ]; then ok "B: o prompt das 4 partes diz ao revisor que a pathspec nao mudou desde o candidato da rc.1"
    else bad "B: so $_samep de 4 prompts carregam a conferencia com o candidato da rc.1"; fi
    # GA_CODEX_JOBS=4 (o modo do passo 6 do CUT): cada chamada do stub registrou a sua
    # partida e esperou ver as 4 — numa onda so cada uma viu 4; em serie cada uma veria 1.
    _bj_n=0; _bj_bad=""
    for _f in "$SCRATCH/bj/seen"/*; do
      [ -f "$_f" ] || continue
      _bj_n=$((_bj_n + 1))
      [ "$(tr '\n' ' ' < "$_f")" = "4 " ] || _bj_bad="$_bj_bad ${_f##*/}:$(tr '\n' ',' < "$_f")"
    done
    if [ "$_bj_n" = "4" ] && [ -z "$_bj_bad" ]; then
      ok "B: GA_CODEX_JOBS=4 lancou as 4 partes numa onda so (cada chamada do codex viu as 4 partidas), cada parte UMA vez"
    else bad "B: GA_CODEX_JOBS=4 nao correu as 4 partes numa onda so: $_bj_n parte(s) chamada(s); fora da onda ou repetidas:${_bj_bad:- nenhuma}"; fi
    if grep -qE 'GA_CODEX_JOBS=("\$\{GA_CODEX_JOBS:-4\}"|4)[[:space:]]' "$PLAN_DIR/OWNER-GA-CUT.sh"; then
      ok "B: o passo 6 do OWNER-GA-CUT.sh passa GA_CODEX_JOBS=4 ao runner (o modo que este B exercita)"
    else bad "B: o OWNER-GA-CUT.sh nao passa mais GA_CODEX_JOBS=4 ao runner — este B exercitaria outro modo"; fi
  fi
fi

# ===========================================================================
say "B2. rodada MORTA por capacidade do modelo: re-tentada, e a PROVENANCE declara"
if [ -n "$CLONE" ] && [ -n "${CAND:-}" ]; then
  CLONE2="$SCRATCH/clone2"
  if git clone --quiet --local --shared "$UPSTREAM" "$CLONE2" 2>/dev/null \
     && git -C "$CLONE2" checkout --quiet --detach "$CAND" 2>/dev/null; then
    printf '%s\n' "$CAND" > "$CLONE2/$EV/CANDIDATE.sha"
    FLAKY="$SCRATCH/codex-flaky"
    # A transcricao REAL do codex ecoa o prompt (medido na tentativa do GA v1.4.1 de
    # 2026-09-25) e a saida das ferramentas que o revisor roda, e o diff desta release
    # CITA "usage limit" no meio de uma linha (a nota de substrato da parte 4). O runner
    # classifica a morte SO pelas linhas `ERROR: ` da coluna 0 nas ultimas 40 linhas. O
    # stub planta a linha REAL do limite de uso da conta nas duas posicoes que essa regra
    # exclui — na coluna 0 ANTES do payload ecoado (mais de 40 linhas antes do fim) e no
    # MEIO de uma linha dentro da janela —, e guarda cada transcricao morta FORA da arvore
    # (b2-dead/): a morte por capacidade segue capacidade (re-tentada), nunca a classe do
    # limite de uso da conta. Um classificador sobre o transcript inteiro, sem o filtro
    # `^ERROR: `, ou com o filtro sem ancora, ve a conta e NAO re-tenta: o B2 reprova.
    mkdir -p "$SCRATCH/b2-dead"
    cat > "$FLAKY" <<'FLAKYEOF'
#!/bin/bash
# stub de REVISOR com UMA morte por capacidade por parte: a 1.a chamada de cada payload
# imprime a saida de uma ferramenta com a linha do limite de uso da conta na coluna 0,
# ecoa o prompt (como o codex real), uma isca com a mesma linha no MEIO de uma linha, e a
# assinatura de capacidade do servidor por ultimo, e sai rc 1 SEM veredito; a 2.a revisa.
out=""; prev=""
for a in "$@"; do
  [ "$prev" = "--output-last-message" ] && out="$a"
  prev="$a"
done
[ -n "$out" ] || { echo "stub: sem --output-last-message" >&2; exit 3; }
payload="$(cat)"
bytes="$(printf '%s' "$payload" | wc -c | tr -d ' ')"
mark="$out.flaky-seen"
if [ ! -e "$mark" ]; then
  : > "$mark"
  {
    printf 'OpenAI Codex (stub)\n--------\nexec\n'
    printf 'ERROR: You\342\200\231ve hit your usage limit. Visit https://chatgpt.com/codex/settings/usage to purchase more credits or try again at 4:43 PM.\n'
    printf 'user\n%s\n' "$payload"
    printf '%s\n' "+| isca do ensaio B2 | ERROR: You've hit your usage limit ... try again at 4:43 PM | workflows pause at the usage limit (2.1.271) |"
    echo "ERROR: Selected model is at capacity. Please try a different model."
  } | tee "$(dirname "$0")/b2-dead/$(basename "$out").log"
  exit 1
fi
rm -f "$mark"
printf 'STUB REVIEW: li %s bytes de payload pela stdin.\n' "$bytes" > "$out"
printf 'VERDICT: GO-WITH-CONDITIONS cobertura declarada no README-ga.\n' >> "$out"
printf 'stub: payload de %s bytes\n' "$bytes"
FLAKYEOF
    chmod 0755 "$FLAKY"
    # shellcheck disable=SC2086
    if ( cd "$CLONE2" && env CODEX_BIN="$FLAKY" CODEX_MODEL=stub-model HOME="$SCRATCH/fakehome2" \
         GA_RETRY_UNIT_SECONDS=0 GNUPGHOME="$GH" $SELFTEST_ENV $PROBE_ENV \
         bash "$EV/run-ga-repass.sh" ) > "$SCRATCH/runner2.log" 2>&1; then
      ok "B2: o runner sobrevive a UMA morte por capacidade em cada parte (rc 0)"
    else bad "B2: runner rc!=0 com o stub instavel"; sed -n '1,25p' "$SCRATCH/runner2.log"; fi
    _b2="$(grep -c 'tentativa(s) MORTA(s) por capacidade' "$CLONE2/$EV/PROVENANCE-ga.md" 2>/dev/null)" || _b2=0
    if [ "$_b2" = "4" ]; then ok "B2: a PROVENANCE declara a morte por capacidade nas 4 partes"
    else bad "B2: a PROVENANCE declara $_b2 morte(s) (esperado 4)"; fi
    _b2_left="$(find "$CLONE2/$EV" -maxdepth 1 \( -name '.codex-dead-*' -o -name '*.flaky-seen' \) | grep -c . )" || _b2_left=0
    if [ "$_b2_left" = "0" ]; then ok "B2: nenhum marcador de tentativa sobrou na arvore"
    else bad "B2: sobraram $_b2_left marcador(es) de tentativa na arvore"; fi
    # O controle nao e vacuo: em cada transcricao morta a linha do limite de uso da conta
    # esta na coluna 0 FORA da janela (40 linhas do fim) e no MEIO de uma linha DENTRO
    # dela, e a ultima linha e a de capacidade.
    _b2d=0
    for _f in "$SCRATCH/b2-dead"/*.log; do
      [ -f "$_f" ] || continue
      _tot="$(wc -l < "$_f" | tr -d ' ')"
      _far="$(grep -n '^ERROR: .*hit your usage limit' "$_f" | head -n 1 | cut -d: -f1)"
      _near="$(grep -n '^+| isca do ensaio B2 | ERROR: .*hit your usage limit' "$_f" | tail -n 1 | cut -d: -f1)"
      if [ -n "$_far" ] && [ -n "$_near" ] && [ $((_tot - _far)) -ge 40 ] && [ $((_tot - _near)) -lt 40 ] \
         && [ "$(tail -n 1 "$_f")" = "ERROR: Selected model is at capacity. Please try a different model." ]; then
        _b2d=$((_b2d + 1))
      fi
    done
    if [ "$_b2d" = "4" ]; then ok "B2: as 4 transcricoes mortas trazem a linha do limite de uso da conta na coluna 0 FORA da janela de 40 linhas e no MEIO de uma linha DENTRO dela, e a capacidade por ultimo (o controle nao e vacuo)"
    else bad "B2: $_b2d de 4 transcricoes mortas com as iscas do limite de uso nas posicoes do controle"; fi
    if grep -qi 'limite de uso da conta' "$CLONE2/$EV/PROVENANCE-ga.md" 2>/dev/null; then
      bad "B2: uma morte por capacidade virou limite de uso da conta por uma linha fora da janela ou no meio de uma linha"
    else ok "B2 (controle vermelho): a linha do limite de uso da conta fora da janela de 40 linhas, ou no meio de uma linha, NAO classifica a morte (segue capacidade, re-tentada)"; fi
  else bad "B2: clone local para o stub instavel falhou"; fi
fi

# Stub de REVISOR que CONTA as chamadas em <dir>/calls/ (B4, B4c/B4d): a saida e a do
# stub do B, sem a barreira.
_mk_count_stub() {
  mkdir -p "$1/calls" || return 1
  cat > "$1/codex" <<'COUNTEOF' || return 1
#!/bin/bash
# stub de REVISOR que CONTA as chamadas em calls/; a saida e a do stub do B.
out=""; prev=""
for a in "$@"; do
  [ "$prev" = "--output-last-message" ] && out="$a"
  prev="$a"
done
[ -n "$out" ] || { echo "stub: sem --output-last-message" >&2; exit 3; }
printf 'x\n' >> "$(dirname "$0")/calls/$(basename "$out")"
bytes=$(wc -c)
printf 'STUB REVIEW: li %s bytes de payload pela stdin.\n' "$bytes" > "$out"
printf 'VERDICT: GO-WITH-CONDITIONS cobertura declarada no README-ga.\n' >> "$out"
printf 'stub: payload de %s bytes\n' "$bytes"
COUNTEOF
  chmod 0755 "$1/codex"
}
# Um clone do candidato da fixture com o CANDIDATE.sha escrito; $1 = destino.
_clone_cand() {
  git clone --quiet --local --shared "$UPSTREAM" "$1" 2>/dev/null \
    && git -C "$1" checkout --quiet --detach "$CAND" 2>/dev/null \
    && printf '%s\n' "$CAND" > "$1/$EV/CANDIDATE.sha"
}

# ===========================================================================
say "B2u. LIMITE DE USO da CONTA codex: sem re-tentativa (vence a capacidade no fim), recusa nomeada com a hora de reset, e a PROVENANCE declara — em serie e numa onda so (GA_CODEX_JOBS=4)"
if [ -n "$CLONE" ] && [ -n "${CAND:-}" ]; then
  # Um stub por caso (b2u em serie, b2uj numa onda so), cada um no seu diretorio: conta as
  # chamadas em calls/; com o arquivo `barrier`, espera (ate 60 s) as 4 partidas da onda
  # antes de morrer e grava quantas viu em seen/ — a onda fica deterministica (nenhuma
  # parte morre antes de as 4 serem lancadas).
  for _s in b2u b2uj; do
    mkdir -p "$SCRATCH/$_s/calls" "$SCRATCH/$_s/starts" "$SCRATCH/$_s/seen"
    cat > "$SCRATCH/$_s/codex" <<'USAGEEOF'
#!/bin/bash
# stub de REVISOR SEM COTA NA CONTA: toda chamada ecoa o prompt (como o codex real) e
# termina com uma linha ERROR: de CAPACIDADE seguida da linha REAL do limite de uso da
# conta — a forma medida na tentativa do GA v1.4.1 de 2026-09-25: apostrofo U+2019
# (octal 342 200 231) e a hora de reset no fim —, e sai rc 1 SEM veredito. As duas
# classes no fim do transcript: a da CONTA vence (nunca re-tentada). Cada chamada fica
# contada em calls/.
out=""; prev=""
for a in "$@"; do
  [ "$prev" = "--output-last-message" ] && out="$a"
  prev="$a"
done
[ -n "$out" ] || { echo "stub: sem --output-last-message" >&2; exit 3; }
d="$(dirname "$0")"; n="$(basename "$out")"
payload="$(cat)"
printf 'x\n' >> "$d/calls/$n"
if [ -f "$d/barrier" ]; then
  : > "$d/starts/$n.$$"; i=0
  while [ "$(find "$d/starts" -type f | grep -c .)" -lt 4 ] && [ "$i" -lt 600 ]; do sleep 0.1; i=$((i + 1)); done
  find "$d/starts" -type f | grep -c . >> "$d/seen/$n"
fi
printf 'OpenAI Codex (stub)\n--------\nuser\n%s\n' "$payload"
printf 'ERROR: Selected model is at capacity. Please try a different model.\n'
printf 'ERROR: You\342\200\231ve hit your usage limit. Visit https://chatgpt.com/codex/settings/usage to purchase more credits or try again at 4:43 PM.\n'
printf 'ERROR: You\342\200\231ve hit your usage limit. Visit https://chatgpt.com/codex/settings/usage to purchase more credits or try again at 4:43 PM.\n'
exit 1
USAGEEOF
    chmod 0755 "$SCRATCH/$_s/codex"
  done
  : > "$SCRATCH/b2uj/barrier"
  # $1 = caso (b2u|b2uj), $2 = GA_CODEX_JOBS. O rc do runner fica em $SCRATCH/<caso>/rc.
  _b2u_run() {
    local _k="$SCRATCH/clone-$1" _rc=0
    if ! _clone_cand "$_k"; then echo "clone" > "$SCRATCH/$1/rc"; return 1; fi
    # shellcheck disable=SC2086
    ( cd "$_k" && env CODEX_BIN="$SCRATCH/$1/codex" CODEX_MODEL=stub-model HOME="$SCRATCH/fakehome-$1" \
         GA_RETRY_UNIT_SECONDS=0 GA_CODEX_JOBS="$2" GNUPGHOME="$GH" $SELFTEST_ENV $PROBE_ENV \
         bash "$EV/run-ga-repass.sh" ) > "$SCRATCH/runner-$1.log" 2>&1 || _rc=$?
    echo "$_rc" > "$SCRATCH/$1/rc"
    # A recusa e do RUNNER (a transcricao do stub vai para transcript-ga-N.log, nunca para
    # a saida dele); as linhas da sonda ficam fora da conta.
    grep -v '^   sonda: ' "$SCRATCH/runner-$1.log" > "$SCRATCH/runner-$1.own" 2>/dev/null || :
  }
  # As chamadas por parte: "<partes chamadas> <partes chamadas mais de uma vez>".
  _b2u_calls() {
    local _f _n=0 _multi=""
    for _f in "$SCRATCH/$1/calls"/*; do
      [ -f "$_f" ] || continue
      _n=$((_n + 1))
      [ "$(grep -c . "$_f")" = "1" ] || _multi="$_multi ${_f##*/}"
    done
    printf '%s|%s\n' "$_n" "$_multi"
  }
  # --- em serie (o default): a parte 1 morre na conta e NENHUMA outra e lancada ---------
  if _b2u_run b2u 1; then
    _u_rc="$(cat "$SCRATCH/b2u/rc")"
    if [ "$_u_rc" -ne 0 ]; then ok "B2u: o runner sai rc!=0 (rc $_u_rc) quando a conta do codex esta sem cota"
    else bad "B2u: o runner saiu rc 0 com o limite de uso da conta em toda chamada"; fi
    _u_c="$(_b2u_calls b2u)"
    if [ "$_u_c" = "1|" ] && [ -f "$SCRATCH/b2u/calls/verdict-ga-1.txt" ]; then
      ok "B2u (controle vermelho): nenhuma re-tentativa sobre o limite de uso, nem com uma linha ERROR: de capacidade no fim (so a parte 1 chamada, UMA vez)"
    else bad "B2u: re-tentou sobre o limite de uso da conta, lancou parte nova depois dele, ou nao chamou o codex (partes|repetidas = $_u_c)"; fi
    if grep -qi 'limite de uso da conta' "$SCRATCH/runner-b2u.own" \
       && grep -qF '4:43 PM' "$SCRATCH/runner-b2u.own"; then
      ok "B2u: a recusa nomeia o limite de uso da CONTA e ecoa a hora de reset que o codex imprimiu (4:43 PM)"
    else bad "B2u: a saida do runner nao nomeia o limite de uso da conta com a hora de reset"; sed -n '1,25p' "$SCRATCH/runner-b2u.log"; fi
    _u_prov="$SCRATCH/clone-b2u/$EV/PROVENANCE-ga.md"
    _u_nl="$(grep -ci 'NAO lancada' "$_u_prov" 2>/dev/null)" || _u_nl=0
    if [ -f "$_u_prov" ] && grep -qi 'limite de uso da conta' "$_u_prov" \
       && ! grep -q 'MORTA(s) por capacidade' "$_u_prov" \
       && ! grep -q '^RUNNER-OVERALL: rc=0' "$_u_prov" && [ "$_u_nl" = "3" ]; then
      ok "B2u: a PROVENANCE declara o limite de uso da conta e as partes 2-4 NAO lancadas — nem capacidade, nem RUNNER-OVERALL rc=0"
    else bad "B2u: a PROVENANCE nao declara o limite de uso da conta com as 3 partes NAO lancadas (achei $_u_nl), ou declarou capacidade, ou rc=0"; grep -n 'parte\|limite\|LIMITE\|MORTA\|lancada\|RUNNER' "$_u_prov" 2>/dev/null | sed -n '1,14p'; fi
    # B2u — a rota (c) do passo 6 do OWNER-GA-CUT.sh: o comando que a tela manda o Owner
    # digitar, EXTRAIDO do corte no disco e rodado sobre ESTA evidencia (cwd no clone, EV do
    # corte). Tem de achar a linha do limite com a hora de reset. Controle vermelho da classe
    # do achado M1: nenhum marcador .codex-quota-* sobra (o runner o apaga antes de recusar).
    _u_cmd="$(awk '/^\(c\) Caso particular de \(b\)/{f=1; next} f && /^  grep -n /{print; exit}' \
      "$ROOT/$PLAN_DIR/OWNER-GA-CUT.sh" | sed 's/^  //')"
    _u_out=""; _u_crc=0
    if [ -n "$_u_cmd" ]; then
      _u_out="$( cd "$SCRATCH/clone-b2u" && EV="$EV" bash -c "$_u_cmd" 2>&1 )" || _u_crc=$?
    fi
    if [ -n "$_u_cmd" ] && [ "$_u_crc" -eq 0 ] && printf '%s\n' "$_u_out" | grep -qF 'try again at 4:43 PM'; then
      ok "B2u: a rota (c) do passo 6 do corte (o comando na tela) acha na PROVENANCE a linha do limite com a hora de reset"
    else bad "B2u: a rota (c) do passo 6 do corte (comando: ${_u_cmd:-AUSENTE}) rc=$_u_crc sem a hora de reset"; printf '%s\n' "$_u_out" | sed -n '1,6p'; fi
    _u_left="$(find "$SCRATCH/clone-b2u/$EV" -maxdepth 1 -name '.codex-quota-*' | grep -c . )" || _u_left=0
    if [ "$_u_left" = "0" ]; then
      ok "B2u (controle vermelho): o marcador .codex-quota-* do runner nao sobrevive a recusa — a rota da tela le a PROVENANCE, nunca ele"
    else bad "B2u: $_u_left marcador(es) .codex-quota-* sobreviveram ao runner (a rota da tela nao pode depender deles)"; fi
  else bad "B2u: clone local para o stub sem cota falhou"; fi
  # --- numa onda so (GA_CODEX_JOBS=4, o modo do passo 6 do CUT): as 4 morrem na conta ----
  if _b2u_run b2uj 4; then
    _j_rc="$(cat "$SCRATCH/b2uj/rc")"
    _j_c="$(_b2u_calls b2uj)"
    _j_bad=""
    for _f in "$SCRATCH/b2uj/seen"/*; do
      [ -f "$_f" ] || continue
      [ "$(tr '\n' ' ' < "$_f")" = "4 " ] || _j_bad="$_j_bad ${_f##*/}:$(tr '\n' ',' < "$_f")"
    done
    if [ "$_j_rc" -ne 0 ] && [ "$_j_c" = "4|" ] && [ -z "$_j_bad" ]; then
      ok "B2u (onda, controle vermelho): GA_CODEX_JOBS=4 lanca as 4 partes numa onda so e cada uma morre na conta UMA vez, sem re-tentativa (rc $_j_rc)"
    else bad "B2u (onda): rc=$_j_rc, partes|repetidas = $_j_c, fora da onda:${_j_bad:- nenhuma}"; fi
    _j_prov="$SCRATCH/clone-b2uj/$EV/PROVENANCE-ga.md"
    _j_m="$(grep -ci 'MORTA pelo LIMITE DE USO da CONTA' "$_j_prov" 2>/dev/null)" || _j_m=0
    if [ -f "$_j_prov" ] && [ "$_j_m" = "4" ] \
       && grep -qE 'parte\(s\) 1 2 3 4 sem veredito' "$_j_prov" \
       && ! grep -qi 'NAO lancada' "$_j_prov" \
       && ! grep -q 'MORTA(s) por capacidade' "$_j_prov" \
       && ! grep -q '^RUNNER-OVERALL: rc=0' "$_j_prov" \
       && grep -qi 'limite de uso da conta' "$SCRATCH/runner-b2uj.own" \
       && grep -qF '4:43 PM' "$SCRATCH/runner-b2uj.own"; then
      ok "B2u (onda): a PROVENANCE declara as 4 partes mortas na conta (parte(s) 1 2 3 4, nenhuma NAO lancada) e a recusa ecoa a hora de reset"
    else bad "B2u (onda): a PROVENANCE/recusa nao declara as 4 partes mortas na conta (MORTA na conta: $_j_m)"; grep -n 'parte\|limite\|LIMITE\|MORTA\|lancada\|RUNNER' "$_j_prov" 2>/dev/null | sed -n '1,14p'; fi
  else bad "B2u (onda): clone local para o stub sem cota falhou"; fi
fi

# ===========================================================================
say "B2x. morte SEM classe no fim do transcript: as linhas das duas classes FORA da janela de 40 linhas, ou no MEIO de uma linha, nao re-tentam nem classificam"
if [ -n "$CLONE" ] && [ -n "${CAND:-}" ]; then
  _x="$SCRATCH/b2x"; _kx="$SCRATCH/clone-b2x"
  mkdir -p "$_x/calls"
  cat > "$_x/codex" <<'B2XEOF'
#!/bin/bash
# stub de REVISOR que morre SEM classe: a saida de uma ferramenta ecoada no INICIO (as
# linhas ERROR: de capacidade e do limite de uso da conta na coluna 0, mais de 40 linhas
# antes do fim), o prompt ecoado, uma isca com as frases das duas classes no MEIO de uma
# linha, e por ultimo um erro de transporte do codex que nao e de nenhuma das duas; rc 1
# SEM veredito. Cada chamada fica contada em calls/.
out=""; prev=""
for a in "$@"; do
  [ "$prev" = "--output-last-message" ] && out="$a"
  prev="$a"
done
[ -n "$out" ] || { echo "stub: sem --output-last-message" >&2; exit 3; }
payload="$(cat)"
printf 'x\n' >> "$(dirname "$0")/calls/$(basename "$out")"
printf 'OpenAI Codex (stub)\n--------\nexec\n'
printf 'ERROR: Selected model is at capacity. Please try a different model.\n'
printf 'ERROR: You\342\200\231ve hit your usage limit. Visit https://chatgpt.com/codex/settings/usage to purchase more credits or try again at 4:43 PM.\n'
printf 'user\n%s\n' "$payload"
printf '%s\n' "+| isca do ensaio B2x | ERROR: Selected model is at capacity | Review was interrupted | ERROR: You've hit your usage limit |"
printf 'ERROR: stream disconnected before completion: error sending request\n'
exit 1
B2XEOF
  chmod 0755 "$_x/codex"
  if _clone_cand "$_kx"; then
    _x_rc=0
    # shellcheck disable=SC2086
    ( cd "$_kx" && env CODEX_BIN="$_x/codex" CODEX_MODEL=stub-model HOME="$SCRATCH/fakehome-b2x" \
         GA_RETRY_UNIT_SECONDS=0 GNUPGHOME="$GH" $SELFTEST_ENV $PROBE_ENV \
         bash "$EV/run-ga-repass.sh" ) > "$SCRATCH/runner-b2x.log" 2>&1 || _x_rc=$?
    # O controle nao e vacuo: nas 4 transcricoes as linhas das duas classes estao na coluna
    # 0 FORA da janela e a isca no MEIO de uma linha DENTRO dela.
    _xv=0
    for _n in 1 2 3 4; do
      _t="$_kx/$EV/transcript-ga-$_n.log"
      [ -f "$_t" ] || continue
      _tot="$(wc -l < "$_t" | tr -d ' ')"
      _fc="$(grep -n '^ERROR: Selected model is at capacity' "$_t" | head -n 1 | cut -d: -f1)"
      _fa="$(grep -n '^ERROR: .*hit your usage limit' "$_t" | head -n 1 | cut -d: -f1)"
      _nb="$(grep -n '^+| isca do ensaio B2x |' "$_t" | tail -n 1 | cut -d: -f1)"
      if [ -n "$_fc" ] && [ -n "$_fa" ] && [ -n "$_nb" ] && [ $((_tot - _fc)) -ge 40 ] \
         && [ $((_tot - _fa)) -ge 40 ] && [ $((_tot - _nb)) -lt 40 ]; then _xv=$((_xv + 1)); fi
    done
    if [ "$_xv" = "4" ]; then ok "B2x: as 4 transcricoes trazem as duas classes na coluna 0 FORA da janela de 40 linhas e no MEIO de uma linha DENTRO dela (o controle nao e vacuo)"
    else bad "B2x: $_xv de 4 transcricoes com as linhas das classes nas posicoes do controle"; fi
    _x_n=0; _x_multi=""
    for _f in "$_x/calls"/*; do
      [ -f "$_f" ] || continue
      _x_n=$((_x_n + 1))
      [ "$(grep -c . "$_f")" = "1" ] || _x_multi="$_x_multi ${_f##*/}"
    done
    _x_prov="$_kx/$EV/PROVENANCE-ga.md"
    _x_died="$(grep -cE '^- parte [1-4] .*\[codex rc=1\]$' "$_x_prov" 2>/dev/null)" || _x_died=0
    if [ "$_x_rc" -ne 0 ] && [ "$_x_n" = "4" ] && [ -z "$_x_multi" ] && [ "$_x_died" = "4" ] \
       && ! grep -q 'MORTA(s) por capacidade' "$_x_prov" \
       && ! grep -qi 'limite de uso da conta' "$_x_prov" \
       && ! grep -qi 'NAO lancada' "$_x_prov" \
       && ! grep -q '^RUNNER-OVERALL: rc=0' "$_x_prov"; then
      ok "B2x (controle vermelho): a morte sem classe no fim nao e re-tentada nem vira capacidade ou limite de uso da conta (4 partes, cada uma UMA vez, codex rc=1; runner rc $_x_rc)"
    else bad "B2x: rc=$_x_rc, partes=$_x_n, repetidas:${_x_multi:- nenhuma}, linhas 'codex rc=1'=$_x_died, ou a PROVENANCE classificou a morte"; grep -n 'parte\|limite\|LIMITE\|MORTA\|lancada\|RUNNER' "$_x_prov" 2>/dev/null | sed -n '1,14p'; fi
  else bad "B2x: clone local para o stub sem classe falhou"; fi
fi

# ===========================================================================
say "B4. candidato que MUDA a parte 1 desde o candidato da rc.1: a sonda recusa antes do codex; o runner separa so a parte mudada"
if [ -n "$CLONE" ] && [ -n "${CAND:-}" ]; then
  UP4="$SCRATCH/upstream4"; CLONE4="$SCRATCH/clone4"; CLONE4B="$SCRATCH/clone4b"
  if git clone --quiet --local --shared "$UPSTREAM" "$UP4" 2>/dev/null \
     && fixture_git_identity "$UP4" \
     && printf '\n<!-- TEST ONLY: mutacao do ensaio B4 (parte 1) -->\n' >> "$UP4/SUPPORT.md" \
     && git -C "$UP4" commit --quiet -am "TEST ONLY: B4 mutates part 1" \
     && git clone --quiet --local --shared "$UP4" "$CLONE4" 2>/dev/null \
     && git clone --quiet --local --shared "$UP4" "$CLONE4B" 2>/dev/null; then
    CAND4="$(git -C "$UP4" rev-parse HEAD)"
    for _c in "$CLONE4" "$CLONE4B"; do
      git -C "$_c" checkout --quiet --detach "$CAND4" 2>/dev/null
      printf '%s\n' "$CAND4" > "$_c/$EV/CANDIDATE.sha"
    done
    # Stubs que CONTAM as chamadas (um diretorio por caso): a mesma saida do stub do B.
    if ! _mk_count_stub "$SCRATCH/b4a" || ! _mk_count_stub "$SCRATCH/b4b"; then bad "B4: stubs que contam falharam"; fi
    # B4a — SEM o modo REPORT-ONLY: a sonda do GA ve a parte 1 diferente da do candidato da
    # rc.1 e o runner recusa ANTES de qualquer codex.
    _b4a_rc=0
    # shellcheck disable=SC2086
    ( cd "$CLONE4" && env CODEX_BIN="$SCRATCH/b4a/codex" CODEX_MODEL=stub-model HOME="$SCRATCH/fakehome4" \
         GNUPGHOME="$GH" $SELFTEST_ENV bash "$EV/run-ga-repass.sh" ) > "$SCRATCH/runner4a.log" 2>&1 || _b4a_rc=$?
    _b4a_calls="$(find "$SCRATCH/b4a/calls" -type f | grep -c .)" || _b4a_calls=0
    if [ "$_b4a_rc" -ne 0 ] && [ "$_b4a_calls" = "0" ] \
       && grep -qE 'FAIL [^:]+: .*SUPPORT\.md' "$SCRATCH/runner4a.log"; then
      ok "B4a (controle vermelho): parte 1 mudada desde o candidato da rc.1 e recusada pela sonda, com o caminho nomeado, antes de qualquer codex"
    else bad "B4a: rc=$_b4a_rc, chamadas ao codex=$_b4a_calls, ou a sonda nao nomeou SUPPORT.md"; grep -E 'FAIL|FATAL' "$SCRATCH/runner4a.log" | sed -n '1,8p'; fi
    # B4b — em REPORT-ONLY a sonda nao para o runner: a conferencia DELE tem de separar a
    # parte mudada. Duas formas honestas: declarar MUDOU so na parte 1 (PROVENANCE e prompt)
    # e revisar, ou recusar pelo nome antes do codex daquela parte.
    _b4b_rc=0
    # shellcheck disable=SC2086
    ( cd "$CLONE4B" && env CODEX_BIN="$SCRATCH/b4b/codex" CODEX_MODEL=stub-model HOME="$SCRATCH/fakehome4b" \
         GNUPGHOME="$GH" $SELFTEST_ENV GA_PROBE_REPORT_ONLY=1 bash "$EV/run-ga-repass.sh" ) \
      > "$SCRATCH/runner4b.log" 2>&1 || _b4b_rc=$?
    _p4="$CLONE4B/$EV/PROVENANCE-ga.md"
    if [ "$_b4b_rc" -eq 0 ] \
       && grep -q '^  - diff-ga-1\.patch: MUDOU desde o candidato da rc\.1' "$_p4" 2>/dev/null \
       && grep -q '^  - diff-ga-2\.patch: sem mudanca na pathspec' "$_p4" \
       && grep -q '^  - diff-ga-3\.patch: sem mudanca na pathspec' "$_p4" \
       && grep -q '^  - diff-ga-4\.patch: sem mudanca na pathspec' "$_p4" \
       && grep -qF "files of this part's pathspec DIFFER" "$CLONE4B/$EV/payload-ga-1.redacted.txt" 2>/dev/null \
       && grep -qF "no file of this part's pathspec differs" "$CLONE4B/$EV/payload-ga-2.redacted.txt" 2>/dev/null; then
      ok "B4b (controle vermelho): o runner declara MUDOU so na parte 1, na PROVENANCE e no prompt (as partes 2-4 sem mudanca)"
    elif [ "$_b4b_rc" -ne 0 ] && [ ! -e "$SCRATCH/b4b/calls/verdict-ga-1.txt" ] \
         && grep -E '^FATAL: ' "$SCRATCH/runner4b.log" | grep -E 'parte 1' | grep -qE 'MUDOU|mudou|DIFFER|differ'; then
      ok "B4b (controle vermelho): o runner recusa pelo nome a parte 1 mudada, antes do codex dela"
    else bad "B4b: o runner nao separou a parte 1 mudada (rc=$_b4b_rc)"; grep -n 'diff-ga-' "$_p4" 2>/dev/null; grep -E '^FATAL' "$SCRATCH/runner4b.log" | sed -n '1,4p'; fi
  else bad "B4: preparacao do candidato mutado falhou"; fi
fi

# ===========================================================================
say "B4c. a evidencia da rc.1 no candidato (repass-rc1/diff-rc1-N.patch) com UMA linha mudada (B4c: recusa do CONTEUDO), ou AUSENTE (B4d: recusa da AUSENCIA): recusa nomeada do runner, antes de qualquer codex"
if [ -n "$CLONE" ] && [ -n "${CAND:-}" ]; then
  # A frase $4 do prompt diz ao revisor que o diff de cada parte e, em conteudo, o que a
  # rc.1 revisou; o runner o confere em bytes (fora as linhas index) contra o
  # repass-rc1/diff-rc1-N.patch que o CANDIDATO carrega. B4c muda UMA linha de conteudo no
  # MEIO do diff-rc1-2.patch (o numero de linhas fica igual); B4d apaga o diff-rc1-3.patch (parte 3).
  # As arvores das partes nao mudam (so um plano numerado muda) e a sonda fica em
  # REPORT-ONLY: a recusa tem de ser a do PROPRIO runner, nomeando a parte e o arquivo, com a
  # parte anterior montada e nenhum codex chamado.
  cat > "$SCRATCH/b4c-mutate.py" <<'PYB4C'
import sys
p = sys.argv[1]
with open(p, "rb") as fh:
    lines = fh.read().split(b"\n")
idx = [i for i, ln in enumerate(lines) if ln.startswith(b"+") and not ln.startswith(b"+++")]
if not idx:
    raise SystemExit("B4c: nenhuma linha + em %s" % p)
i = idx[len(idx) // 2]
lines[i] = lines[i] + b" TEST-ONLY-B4c"
with open(p, "wb") as fh:
    fh.write(b"\n".join(lines))
PYB4C
  # Cada caso exige a recusa da SUA classe e nunca a da outra: B4c a do CONTEUDO (o diff da
  # parte NAO e, em conteudo, o que a rc.1 revisou); B4d a da AUSENCIA (o diff-rc1-N.patch
  # ausente no candidato). Sem a checagem de ausencia do runner, o `git cat-file blob` do
  # caminho ausente falha, o cmp acusa diferenca e a recusa do CONTEUDO nomearia o mesmo
  # arquivo no lugar dela — por isso o B4d exige a frase da ausencia, recusa a do conteudo
  # e recusa o `fatal: path ... does not exist` do git no log do runner.
  for _c in b4c b4d; do
    if [ "$_c" = "b4c" ]; then
      _cp=2; _cwant="^FATAL: parte $_cp: o diff NAO e, em conteudo, o [^ ]*repass-rc1/diff-rc1-$_cp\.patch que a rc\.1 revisou"
      _cother="ausente no candidato"
    else
      _cp=3; _cwant="^FATAL: parte $_cp: [^ ]*repass-rc1/diff-rc1-$_cp\.patch ausente no candidato"
      _cother="NAO e, em conteudo"
    fi
    _cprev=$((_cp - 1))
    _rcp="$PLAN_DIR/repass-rc1/diff-rc1-$_cp.patch"
    _up="$SCRATCH/up-$_c"; _kc="$SCRATCH/clone-$_c"; _mut=0
    if git clone --quiet --local --shared "$UPSTREAM" "$_up" 2>/dev/null \
       && fixture_git_identity "$_up" && [ -f "$_up/$_rcp" ]; then
      if [ "$_c" = "b4c" ]; then
        python3 "$SCRATCH/b4c-mutate.py" "$_up/$_rcp" \
          && git -C "$_up" commit --quiet -am "TEST ONLY: B4c muda uma linha do diff da rc.1 da parte 2" && _mut=1
      else
        git -C "$_up" rm --quiet -- "$_rcp" \
          && git -C "$_up" commit --quiet -m "TEST ONLY: B4d apaga o diff da rc.1 da parte 3" && _mut=1
      fi
    fi
    if [ "$_mut" = "1" ] && git clone --quiet --local --shared "$_up" "$_kc" 2>/dev/null \
       && _mk_count_stub "$SCRATCH/$_c"; then
      _cc="$(git -C "$_up" rev-parse HEAD)"
      git -C "$_kc" checkout --quiet --detach "$_cc" 2>/dev/null
      printf '%s\n' "$_cc" > "$_kc/$EV/CANDIDATE.sha"
      _cr=0
      # shellcheck disable=SC2086
      ( cd "$_kc" && env CODEX_BIN="$SCRATCH/$_c/codex" CODEX_MODEL=stub-model HOME="$SCRATCH/fakehome-$_c" \
           GNUPGHOME="$GH" $SELFTEST_ENV GA_PROBE_REPORT_ONLY=1 bash "$EV/run-ga-repass.sh" ) \
        > "$SCRATCH/runner-$_c.log" 2>&1 || _cr=$?
      _cn="$(find "$SCRATCH/$_c/calls" -type f | grep -c .)" || _cn=0
      if [ "$_cr" -ne 0 ] && [ "$_cn" = "0" ] \
         && grep -qE "$_cwant" "$SCRATCH/runner-$_c.log" \
         && ! grep -qE "^FATAL: .*$_cother" "$SCRATCH/runner-$_c.log" \
         && ! grep -qE '^fatal: path .* does not exist' "$SCRATCH/runner-$_c.log" \
         && grep -q "^parte $_cprev/4 OK " "$SCRATCH/runner-$_c.log" \
         && ! grep -q "^parte $_cp/4 OK " "$SCRATCH/runner-$_c.log"; then
        if [ "$_c" = "b4c" ]; then
          ok "B4c (controle vermelho): UMA linha do diff-rc1-2.patch mudada no candidato e recusa NOMEADA do CONTEUDO pelo runner na parte 2 (a 1 montada), antes de qualquer codex — a frase \$4 nunca fala de outro diff"
        else
          ok "B4d (controle vermelho): o diff-rc1-3.patch AUSENTE do candidato e recusa NOMEADA da AUSENCIA pelo runner na parte 3 (a 2 montada; nunca a do conteudo no lugar dela), antes de qualquer codex"
        fi
      else bad "$_c: rc=$_cr, chamadas ao codex=$_cn, ou o runner nao recusou a parte $_cp com a recusa da classe do caso (${_cwant}), ou deu a da outra classe (${_cother}) ou o fatal do git sobre o caminho, com a parte $_cprev montada"; grep -E '^FATAL|^fatal|^parte [1-4]/4 OK' "$SCRATCH/runner-$_c.log" | sed -n '1,6p'; fi
    else bad "$_c: preparacao da evidencia da rc.1 mutada falhou"; fi
  done
fi

say "B3. o modelo vem da tabela RAIZ de ~/.codex/config.toml, ou de CODEX_MODEL, ou e recusa"
_b3="$SCRATCH/b3"; mkdir -p "$_b3/home/.codex" "$_b3/empty"
printf '%s\n' '# config de fixture' 'model = "fixture-root-model"' 'model_reasoning_effort = "max"' \
  '' '[profiles.other]' 'model = "fixture-PROFILE-model"' > "$_b3/home/.codex/config.toml"
{
  printf 'set -uo pipefail\ndie() { printf "FATAL: %%s\\n" "$*" >&2; exit 1; }\n'
  awk '/^# --- 1b\. MODELO explicito/{f=1} /^OVERALL=0$/{f=0} f' "$ROOT/$EV/run-ga-repass.sh"
  printf 'printf "%%s|%%s\\n" "$CODEX_MODEL" "$CODEX_MODEL_SRC"\n'
} > "$_b3/model.sh"
_b3a="$(env -u CODEX_MODEL HOME="$_b3/home" bash "$_b3/model.sh" 2>/dev/null)" || _b3a="rc!=0"
if [ "$_b3a" = "fixture-root-model|config.toml do codex (tabela raiz)" ]; then ok "B3: modelo lido da tabela raiz (o de um perfil NAO e o default)"
else bad "B3: leitura do config devolveu '$_b3a'"; fi
_b3b="$(CODEX_MODEL=env-model HOME="$_b3/home" bash "$_b3/model.sh" 2>/dev/null)" || _b3b="rc!=0"
if [ "$_b3b" = "env-model|ambiente (CODEX_MODEL)" ]; then ok "B3: CODEX_MODEL no ambiente manda"
else bad "B3: o ambiente nao mandou: '$_b3b'"; fi
if env -u CODEX_MODEL HOME="$_b3/empty" bash "$_b3/model.sh" >/dev/null 2>&1; then
  bad "B3: sem config e sem ambiente o runner SEGUIU com modelo indefinido"
else ok "B3 (controle vermelho): sem config e sem ambiente e recusa nomeada"; fi

# ===========================================================================
say "B5/B6. a BASE resolvida em tempo de run: ausente e assinada fora do registro sao recusas nomeadas"
if [ -n "${CLONE:-}" ] && [ -n "${CAND:-}" ] && [ -n "$FPR" ]; then
  _b5_run() {  # $1 = dir do clone, $2 = log, $3 = com seam (1) ou sem (0)
    if [ "$3" = "1" ]; then
      # shellcheck disable=SC2086
      ( cd "$1" && env CODEX_BIN="$STUB" CODEX_MODEL=stub-model HOME="$SCRATCH/fakehome5" \
          GNUPGHOME="$GH" $SELFTEST_ENV GA_PROBE_REPORT_ONLY=1 bash "$EV/run-ga-repass.sh" ) > "$2" 2>&1
    else
      ( cd "$1" && env CODEX_BIN="$STUB" CODEX_MODEL=stub-model HOME="$SCRATCH/fakehome5" \
          GNUPGHOME="$GH" GA_PROBE_REPORT_ONLY=1 bash "$EV/run-ga-repass.sh" ) > "$2" 2>&1
    fi
  }
  _b5="$SCRATCH/clone5"
  if git clone --quiet --local --shared "$UPSTREAM" "$_b5" 2>/dev/null \
     && git -C "$_b5" checkout --quiet --detach "$CAND" 2>/dev/null \
     && printf '%s\n' "$CAND" > "$_b5/$EV/CANDIDATE.sha" && git -C "$_b5" tag -d v1.4.1 >/dev/null 2>&1; then
    if _b5_run "$_b5" "$SCRATCH/b5.log" 1; then bad "B5: o runner seguiu SEM a tag base local"
    elif grep -q 'a tag base v1.4.1 nao existe neste repositorio' "$SCRATCH/b5.log" \
         && ! ls "$_b5/$EV"/payload-ga-* >/dev/null 2>&1; then
      ok "B5 (controle vermelho): tag base ausente e recusa NOMEADA, antes de qualquer payload"
    else bad "B5: recusa sem o nome da base"; sed -n '1,8p' "$SCRATCH/b5.log"; fi
  else bad "B5: preparacao do clone sem a tag base falhou"; fi
  _b6="$SCRATCH/clone6"
  if git clone --quiet --local --shared "$UPSTREAM" "$_b6" 2>/dev/null \
     && git -C "$_b6" checkout --quiet --detach "$CAND" 2>/dev/null \
     && printf '%s\n' "$CAND" > "$_b6/$EV/CANDIDATE.sha"; then
    if _b5_run "$_b6" "$SCRATCH/b6.log" 0; then bad "B6: o runner aceitou uma base assinada fora de .claude/sentinel-signers.txt"
    elif grep -q "a v1.4.1 foi assinada por $FPR, que NAO esta em .claude/sentinel-signers.txt" "$SCRATCH/b6.log"; then
      ok "B6 (controle vermelho): sem o seam, a base assinada pela chave descartavel e recusada pelo registro de signatarios"
    else bad "B6: recusa sem o motivo do registro"; sed -n '1,8p' "$SCRATCH/b6.log"; fi
  else bad "B6: preparacao do clone falhou"; fi
else printf '  (B5/B6 pulados: sem clone ou sem chave)\n'; fi

# ===========================================================================
say "P. a sonda das condicoes nao e vacua: os controles VERMELHOS"
if [ -n "${UPSTREAM:-}" ] && [ -n "$BASE_REV" ]; then
  # P1 — o canario do FN-04 contra o hook da BASE (a v1.4.1 copiava os bytes do
  # scriptPath no PreToolUse): a mesma funcao da sonda tem de ACHAR a copia la.
  _p1="$SCRATCH/p1-base"; mkdir -p "$_p1"
  if git -C "$UPSTREAM" archive "$BASE_REV" .claude/hooks | tar -x -C "$_p1" 2>/dev/null; then
    if PYTHONDONTWRITEBYTECODE=1 python3 - "$ROOT/$EV/probe-conditions-ga.py" "$_p1" > "$SCRATCH/p1.log" 2>&1 <<'PYP1'
import importlib.util, sys
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("probe", sys.argv[1])
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
hits = m.canary_pre(sys.argv[2])
print("copias achadas: %s" % hits)
raise SystemExit(0 if hits else 1)
PYP1
    then ok "P1 (controle positivo): o canario ACHA a copia dos bytes do scriptPath no hook da base ($(tail -1 "$SCRATCH/p1.log" | cut -c1-90))"
    else bad "P1: o canario nao achou a copia no hook da base — a sonda do FN-04 seria vacua"; sed -n '1,6p' "$SCRATCH/p1.log"; fi
  else bad "P1: git archive do hook da base falhou"; fi
  # P2 — um caminho da faixa fora de toda parte e do escopo declarado e recusado pelo nome.
  _p2="$SCRATCH/p2"
  if git clone --quiet --local --shared "$UPSTREAM" "$_p2" 2>/dev/null && fixture_git_identity "$_p2" \
     && mkdir -p "$_p2/.github" && printf 'x\n' > "$_p2/.github/TEST-ONLY-orfao.txt" \
     && git -C "$_p2" add .github/TEST-ONLY-orfao.txt && git -C "$_p2" commit -q -m "TEST ONLY: orfao"; then
    if ( cd "$_p2" && PYTHONDONTWRITEBYTECODE=1 python3 "$EV/probe-conditions-ga.py" --root "$_p2" \
           --base refs/tags/v1.4.1 --head HEAD --only C11-scope ) > "$SCRATCH/p2.log" 2>&1; then
      bad "P2: um caminho orfao passou pela sonda de escopo"
    elif grep -q '^FAIL C11-scope: caminho da faixa fora de toda parte e do escopo declarado: .github/TEST-ONLY-orfao.txt' "$SCRATCH/p2.log"; then
      ok "P2 (controle vermelho): caminho fora de toda parte e do escopo declarado e recusado pelo nome"
    else bad "P2: recusa sem o nome do caminho"; sed -n '1,6p' "$SCRATCH/p2.log"; fi
  else bad "P2: fixture do caminho orfao falhou"; fi
  # P3 — um template com ultracode e recusado (condicao 5).
  _p3="$SCRATCH/p3"
  if git clone --quiet --local --shared "$UPSTREAM" "$_p3" 2>/dev/null && fixture_git_identity "$_p3" \
     && python3 - "$_p3/templates/settings/settings.base.json" <<'PYP3' && git -C "$_p3" commit -q -am "TEST ONLY: ultracode"
import json, sys
p = sys.argv[1]
d = json.load(open(p, encoding="utf-8"))
d["ultracode"] = True
open(p, "w", encoding="utf-8").write(json.dumps(d, indent=2) + "\n")
PYP3
  then
    if ( cd "$_p3" && PYTHONDONTWRITEBYTECODE=1 python3 "$EV/probe-conditions-ga.py" --root "$_p3" \
           --base refs/tags/v1.4.1 --head HEAD --only C5-pin ) > "$SCRATCH/p3.log" 2>&1; then
      bad "P3: template com ultracode passou pela sonda"
    elif grep -q '^FAIL C5-pin: templates/settings/settings.base.json carrega ultracode' "$SCRATCH/p3.log"; then
      ok "P3 (controle vermelho): template com ultracode e recusado pelo nome (condicao 5)"
    else bad "P3: recusa sem o motivo"; sed -n '1,6p' "$SCRATCH/p3.log"; fi
  else bad "P3: fixture do ultracode falhou"; fi
  # P4 — as condicoes citam OQ-8 (condicao 6); o plano commitado SEM ela e recusado.
  _p4="$SCRATCH/p4"
  if git clone --quiet --local --shared "$UPSTREAM" "$_p4" 2>/dev/null && fixture_git_identity "$_p4" \
     && python3 - "$_p4/.claude/plans/PLAN-193-release-v1-4-2-opus55-fasttrack.md" <<'PYP4' && git -C "$_p4" commit -q -am "TEST ONLY: plano sem a OQ-8"
import re, sys
p = sys.argv[1]
t = open(p, encoding="utf-8").read()
n = re.sub(r"(?ms)^- OQ-8\b.*?(?=^- )", "", t, count=1)
if n == t:
    raise SystemExit("o plano da fixture nao tem a OQ-8 (a sonda ja recusaria)")
open(p, "w", encoding="utf-8").write(n)
PYP4
  then
    if ( cd "$_p4" && PYTHONDONTWRITEBYTECODE=1 python3 "$EV/probe-conditions-ga.py" --root "$_p4" \
           --base refs/tags/v1.4.1 --head HEAD --only C12-plan-decisions ) > "$SCRATCH/p4.log" 2>&1; then
      bad "P4: plano sem a OQ-8 que as condicoes citam passou pela sonda"
    elif grep -q '^FAIL C12-plan-decisions: as condicoes citam OQ-8' "$SCRATCH/p4.log"; then
      ok "P4 (controle vermelho): condicao que cita uma decisao ausente do plano commitado e recusada pelo nome"
    else bad "P4: recusa sem o motivo"; sed -n '1,6p' "$SCRATCH/p4.log"; fi
  else bad "P4: fixture do plano sem a OQ-8 falhou (o plano da fixture tem a OQ-8?)"; fi
  # P5 — um veredito que um envelope pina pelo sha256 numa condicao, com um byte a mais.
  _p5="$SCRATCH/p5"; _p5v=".claude/plans/PLAN-192/repass-rc1-20260918-NOGO-r1/verdict-rc1-1.txt"
  if git clone --quiet --local --shared "$UPSTREAM" "$_p5" 2>/dev/null && fixture_git_identity "$_p5" \
     && [ -f "$_p5/$_p5v" ] && printf 'TEST ONLY\n' >> "$_p5/$_p5v" \
     && git -C "$_p5" commit -q -am "TEST ONLY: veredito pinado alterado"; then
    if ( cd "$_p5" && PYTHONDONTWRITEBYTECODE=1 python3 "$EV/probe-conditions-ga.py" --root "$_p5" \
           --base refs/tags/v1.4.1 --head HEAD --only C2-carried-1.4.1 ) > "$SCRATCH/p5.log" 2>&1; then
      bad "P5: veredito pinado alterado passou pela sonda"
    elif grep -q "^FAIL C2-carried-1.4.1: veredito pinado por .* nao tem o sha256 pinado: $_p5v" "$SCRATCH/p5.log"; then
      ok "P5 (controle vermelho): veredito que um envelope pina por condicao, alterado, e recusado pelo nome"
    else bad "P5: recusa sem o motivo"; sed -n '1,6p' "$SCRATCH/p5.log"; fi
  else bad "P5: fixture do veredito pinado falhou"; fi
  # P6 — o registro do ledger (PreToolUse + PostToolUse) contra o hook da BASE: la o
  # PreToolUse ja grava o snapshot, e a mesma funcao da sonda (condicao 3) tem de RECUSAR.
  if [ -d "$_p1/.claude/hooks" ]; then
    if PYTHONDONTWRITEBYTECODE=1 python3 - "$ROOT/$EV/probe-conditions-ga.py" "$_p1" > "$SCRATCH/p6.log" 2>&1 <<'PYP6'
import importlib.util, sys
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("probe", sys.argv[1])
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
try:
    print("aceito: %s" % m.canary_record(sys.argv[2]))
except AssertionError as exc:
    print("recusado: %s" % exc)
    raise SystemExit(0)
raise SystemExit(1)
PYP6
    then ok "P6 (controle vermelho): o registro do ledger no hook da base e recusado ($(tail -1 "$SCRATCH/p6.log" | cut -c1-90))"
    else bad "P6: o registro do hook da base passou pela sonda da condicao 3 — ela seria vacua"; sed -n '1,6p' "$SCRATCH/p6.log"; fi
  else bad "P6: sem o hook da base (o P1 nao o extraiu)"; fi
  # P7 — o piso: um upgrade.sh que SEGUE abaixo do piso e recusado pelo nome (condicao 7).
  _p7="$SCRATCH/p7"
  if git clone --quiet --local --shared "$UPSTREAM" "$_p7" 2>/dev/null && fixture_git_identity "$_p7" \
     && python3 - "$_p7/scripts/upgrade.sh" <<'PYP7' && git -C "$_p7" commit -q -am "TEST ONLY: upgrade.sh sem a recusa do piso"
import sys
p = sys.argv[1]
t = open(p, encoding="utf-8").read()
old = 'if ! _claude_code_floor_check "$ALLOW_OLD_CLAUDE_CODE" "$DRY_RUN"; then\n  exit 6\nfi\n'
if t.count(old) != 1:
    raise SystemExit("a fixture nao tem a recusa do piso no upgrade.sh")
open(p, "w", encoding="utf-8").write(t.replace(old, old.replace("exit 6", "true")))
PYP7
  then
    if ( cd "$_p7" && PYTHONDONTWRITEBYTECODE=1 python3 "$EV/probe-conditions-ga.py" --root "$_p7" \
           --base refs/tags/v1.4.1 --head HEAD --only C7-cc-floor ) > "$SCRATCH/p7.log" 2>&1; then
      bad "P7: um upgrade.sh que segue abaixo do piso passou pela sonda"
    elif grep -qF 'FAIL C7-cc-floor: upgrade.sh (old --settings-migrate-only): rc 0 (esperado 6)' "$SCRATCH/p7.log"; then
      ok "P7 (controle vermelho): upgrade.sh que segue abaixo do piso e recusado pelo nome (condicao 7)"
    else bad "P7: recusa sem o motivo"; sed -n '1,6p' "$SCRATCH/p7.log"; fi
  else bad "P7: fixture do upgrade.sh sem a recusa do piso falhou"; fi
  # P8 — a re-execucao: a rotina unica que perde uma flag do operador e recusada (condicao 6).
  _p8="$SCRATCH/p8"
  if git clone --quiet --local --shared "$UPSTREAM" "$_p8" 2>/dev/null && fixture_git_identity "$_p8" \
     && python3 - "$_p8/scripts/upgrade.sh" <<'PYP8' && git -C "$_p8" commit -q -am "TEST ONLY: re-execucao sem --allow-old-claude-code"
import sys
p = sys.argv[1]
t = open(p, encoding="utf-8").read()
old = '    _rr_cmd="$_rr_cmd --allow-old-claude-code"\n'
if t.count(old) != 1:
    raise SystemExit("a fixture nao tem a rotina _t54_rerun_cmd com --allow-old-claude-code")
open(p, "w", encoding="utf-8").write(t.replace(old, "    :\n"))
PYP8
  then
    if ( cd "$_p8" && PYTHONDONTWRITEBYTECODE=1 python3 "$EV/probe-conditions-ga.py" --root "$_p8" \
           --base refs/tags/v1.4.1 --head HEAD --only C6-effort ) > "$SCRATCH/p8.log" 2>&1; then
      bad "P8: a re-execucao sem uma flag do operador passou pela sonda"
    elif grep -qF 'FAIL C6-effort: a saida do helper que falha nao da o comando de re-execucao' "$SCRATCH/p8.log"; then
      ok "P8 (controle vermelho): re-execucao que perde uma flag do operador e recusada pelo nome (condicao 6)"
    else bad "P8: recusa sem o motivo"; sed -n '1,6p' "$SCRATCH/p8.log"; fi
  else bad "P8: fixture da rotina de re-execucao falhou"; fi
  # P9 — o adapter: um id novo posto na lista de legados e recusado (condicao 8).
  _p9="$SCRATCH/p9"
  if git clone --quiet --local --shared "$UPSTREAM" "$_p9" 2>/dev/null && fixture_git_identity "$_p9" \
     && python3 - "$_p9/.claude/hooks/_lib/adapters/live/claude.py" <<'PYP9' && git -C "$_p9" commit -q -am "TEST ONLY: id novo na lista de legados"
import sys
p = sys.argv[1]
t = open(p, encoding="utf-8").read()
old = "_LEGACY_BUDGET_MODELS = (\n"
if t.count(old) != 1:
    raise SystemExit("a fixture nao tem a lista de legados do adapter")
open(p, "w", encoding="utf-8").write(t.replace(old, old + '    "claude-opus-5-5",\n'))
PYP9
  then
    if ( cd "$_p9" && PYTHONDONTWRITEBYTECODE=1 python3 "$EV/probe-conditions-ga.py" --root "$_p9" \
           --base refs/tags/v1.4.1 --head HEAD --only C8-adapter ) > "$SCRATCH/p9.log" 2>&1; then
      bad "P9: um id novo na lista de legados passou pela sonda"
    elif grep -qF 'FAIL C8-adapter: adapter: classificacao errada: BAD:claude-opus-5-5' "$SCRATCH/p9.log"; then
      ok "P9 (controle vermelho): id novo na lista de legados do adapter e recusado pelo nome (condicao 8)"
    else bad "P9: recusa sem o motivo"; sed -n '1,6p' "$SCRATCH/p9.log"; fi
  else bad "P9: fixture da lista de legados falhou"; fi
  # P10 — um arquivo citado pelos vereditos da v1.4.0, fora das classes da condicao 1, que
  # muda na faixa, e recusado pelo nome.
  _p10="$SCRATCH/p10"
  if git clone --quiet --local --shared "$UPSTREAM" "$_p10" 2>/dev/null && fixture_git_identity "$_p10" \
     && [ -f "$_p10/AGENTS.md" ] && printf '\n<!-- TEST ONLY -->\n' >> "$_p10/AGENTS.md" \
     && git -C "$_p10" commit -q -am "TEST ONLY: AGENTS.md muda na faixa"; then
    if ( cd "$_p10" && PYTHONDONTWRITEBYTECODE=1 python3 "$EV/probe-conditions-ga.py" --root "$_p10" \
           --base refs/tags/v1.4.1 --head HEAD --only C1-annex-v1.4.0 ) > "$SCRATCH/p10.log" 2>&1; then
      bad "P10: um arquivo citado da v1.4.0 fora das classes passou pela sonda"
    elif grep -qF 'FAIL C1-annex-v1.4.0: arquivo citado pelos vereditos da v1.4.0 muda fora das classes declaradas: AGENTS.md' "$SCRATCH/p10.log"; then
      ok "P10 (controle vermelho): arquivo citado da v1.4.0 fora das classes declaradas e recusado pelo nome (condicao 1)"
    else bad "P10: recusa sem o motivo"; sed -n '1,6p' "$SCRATCH/p10.log"; fi
  else bad "P10: fixture do AGENTS.md falhou"; fi
  # --- os controles do GA (P11-P16) ------------------------------------------------
  # Cada checagem NOVA da sonda do GA e provada NAO vacua pela DIFERENCA: a sonda INTEIRA
  # roda sobre um defeito plantado e sobre uma mudanca INOCUA dos mesmos arquivos (um
  # comentario no FIM de um arquivo de cada parte e de cada arquivo que um defeito toca; no
  # package.json, uma linha em branco no fim); um id que so falha no defeito e a checagem
  # do GA — sem depender do id que a sonda da a ela. A referencia do P11 e do P16 e o
  # candidato da fixture sem mudanca. As 10 sondas correm em paralelo (cada uma no seu
  # clone e nos seus temporarios).
  cat > "$SCRATCH/pg-mutate.py" <<'PYPG'
import os, sys
kind, root = sys.argv[1], sys.argv[2]
DRIFT = ".claude/scripts/check-substrate-drift.py"
REPIN = ".claude/scripts/re-pin-codex.py"


def edit(rel, old, new):
    p = os.path.join(root, rel)
    t = open(p, encoding="utf-8").read()
    if t.count(old) != 1:
        raise SystemExit("%s: ancora casou %d vez(es) em %s" % (kind, t.count(old), rel))
    open(p, "w", encoding="utf-8").write(t.replace(old, new))


def append(rel, text):
    with open(os.path.join(root, rel), "a", encoding="utf-8") as fh:
        fh.write(text)


if kind == "inocua":
    # um arquivo de cada parte (1 npm/bin, 2 docs/workflow-recovery.md, 3 o detector de
    # drift, 4 o re-pin-codex), o npm/package.json (parte 1) e o npm-publish.yml (fora das
    # partes): so um comentario, ou uma linha em branco, no fim.
    append("npm/bin/ceo-orch-init.js", "\n// TEST ONLY: PG inocua\n")
    append("docs/workflow-recovery.md", "\n<!-- TEST ONLY: PG inocua -->\n")
    append(DRIFT, "\n# TEST ONLY: PG inocua\n")
    append(REPIN, "\n# TEST ONLY: PG inocua\n")
    append(".github/workflows/npm-publish.yml", "\n# TEST ONLY: PG inocua\n")
    append("npm/package.json", "\n")
elif kind == "anexo-a":
    # a cura da forma (a): o resolvedor so da biblioteca irma do script; --repo-root e dado.
    edit(DRIFT, '    hooks = repo / ".claude" / "hooks"\n    candidates = [hooks, SCRIPT_DIR.parent / "hooks"]\n',
         '    candidates = [SCRIPT_DIR.parent / "hooks"]\n')
elif kind == "anexo-b":
    # a cura da forma (b): todo caminho gerado num comando recomendado vai entre aspas.
    edit(DRIFT, "import shutil\n", "import shlex\nimport shutil\n")
    edit(DRIFT, "posixpath.dirname(existing), version, existing))\n",
         "posixpath.dirname(existing), version, shlex.quote(existing)))\n")
    edit(DRIFT, '"(ADR-182)".format(version, mold["rel"], ga, ga_note))\n',
         '"(ADR-182)".format(version, shlex.quote(mold["rel"]), ga, ga_note))\n')
elif kind == "anexo-c":
    # a cura da forma (c): prefixo de drive e barra invertida recusados no nome do membro.
    edit(REPIN, '    return name.startswith("/") or ".." in name.split("/")\n',
         '    return (name.startswith("/") or ".." in name.split("/") or "\\\\" in name\n'
         '            or any(len(s) >= 2 and s[1] == ":" and s[0].isalpha() for s in name.split("/")))\n')
elif kind == "npm":
    # o npm-publish.yml INVERTIDO: publica so as tags -rc. e deixa de publicar o GA.
    edit(".github/workflows/npm-publish.yml", "if: \"!contains(github.ref, '-rc.')\"",
         "if: \"contains(github.ref, '-rc.')\"")
elif kind == "npm-gatilho":
    # o gatilho que nao casa mais a tag do GA (v1.4.2): o job segue intacto, e nada publica.
    edit(".github/workflows/npm-publish.yml", '      - "v*"\n', '      - "v*-rc.*"\n')
elif kind == "shim":
    edit("npm/bin/ceo-orch-init.js", "path.join(ROOT, 'scripts', 'install.sh')",
         "path.join(ROOT, 'scripts', 'upgrade.sh')")
elif kind == "versao":
    edit("npm/package.json", '"version": "1.4.2",', '"version": "1.4.3",')
elif kind == "envelope":
    os.unlink(os.path.join(root, ".claude/governance/pair-rail-verdict-v1.4.2-rc.1.md"))
else:
    raise SystemExit("tipo de mutacao desconhecido: %s" % kind)
PYPG
  _pg_all="base inocua anexo-a anexo-b anexo-c npm npm-gatilho shim versao envelope"
  for _l in $_pg_all; do
    _d="$SCRATCH/pg-$_l"
    if ! git clone --quiet --local --shared "$UPSTREAM" "$_d" 2>/dev/null || ! fixture_git_identity "$_d"; then
      bad "P-GA: clone da fixture '$_l' falhou"; continue
    fi
    if [ "$_l" != "base" ]; then
      if python3 "$SCRATCH/pg-mutate.py" "$_l" "$_d" > "$SCRATCH/pg-$_l.mut" 2>&1 \
         && git -C "$_d" commit -q -am "TEST ONLY: PG $_l"; then :
      else bad "P-GA: a mutacao '$_l' falhou: $(head -1 "$SCRATCH/pg-$_l.mut")"; continue; fi
    fi
    : > "$SCRATCH/pg-$_l.ready"
  done
  _pg_pids=""
  for _l in $_pg_all; do
    [ -f "$SCRATCH/pg-$_l.ready" ] || continue
    ( cd "$SCRATCH/pg-$_l" && PYTHONDONTWRITEBYTECODE=1 python3 "$EV/probe-conditions-ga.py" \
        --root "$SCRATCH/pg-$_l" --base refs/tags/v1.4.1 --head HEAD ) > "$SCRATCH/pg-$_l.log" 2>&1 &
    _pg_pids="$_pg_pids $!"
  done
  for _pid in $_pg_pids; do wait "$_pid" || :; done
  _pg_ids() { sed -n 's/^FAIL \([^:]*\): .*/\1/p' "$1" | sort -u; }
  _pg_new() {  # as linhas FAIL de $1 cujo id NAO falha em $2
    _pg_ids "$1" > "$SCRATCH/pg-ids.a"; _pg_ids "$2" > "$SCRATCH/pg-ids.b"
    comm -23 "$SCRATCH/pg-ids.a" "$SCRATCH/pg-ids.b" | while IFS= read -r _id; do
      awk -v p="FAIL $_id: " 'index($0, p) == 1' "$1"
    done
  }
  _pg_check() {  # $1 = defeito, $2 = referencia, $3 = ERE que a linha nova cita, $4 = rotulo
    local _new
    if [ ! -f "$SCRATCH/pg-$1.ready" ] || [ ! -f "$SCRATCH/pg-$2.ready" ]; then
      bad "$4: sem a fixture do defeito '$1' ou da referencia '$2'"; return
    fi
    _new="$(_pg_new "$SCRATCH/pg-$1.log" "$SCRATCH/pg-$2.log")"
    if [ -n "$_new" ] && printf '%s\n' "$_new" | grep -qE "$3"; then
      ok "$4 ($(printf '%s\n' "$_new" | head -1 | cut -c1-110))"
    else
      bad "$4: nenhuma checagem falha SO no defeito citando /$3/ (a sonda do GA seria vacua)"
      grep -E '^(FAIL|INFRA)' "$SCRATCH/pg-$1.log" | sed -n '1,6p' | sed 's/^/        /'
    fi
  }
  # P11 — a arvore de cada parte identica a do candidato da rc.1: a mudanca inocua de um
  # arquivo de CADA parte tem de ser recusada, com cada caminho nomeado.
  if [ -f "$SCRATCH/pg-inocua.ready" ] && [ -f "$SCRATCH/pg-base.ready" ]; then
    _pg_new "$SCRATCH/pg-inocua.log" "$SCRATCH/pg-base.log" > "$SCRATCH/pg-new-inocua.txt"
    _miss=""
    for _pp in npm/bin/ceo-orch-init.js docs/workflow-recovery.md \
               .claude/scripts/check-substrate-drift.py .claude/scripts/re-pin-codex.py; do
      grep -qF "$_pp" "$SCRATCH/pg-new-inocua.txt" || _miss="$_miss $_pp"
    done
    if [ -s "$SCRATCH/pg-new-inocua.txt" ] && [ -z "$_miss" ]; then
      ok "P11 (controle vermelho): arquivo de cada parte diferente do candidato da rc.1 e recusado, com o caminho nomeado (partes 1-4)"
    else bad "P11: a sonda nao recusa pelo caminho a parte mudada desde o candidato da rc.1:${_miss:- nada novo falhou}"
      grep -E '^(FAIL|INFRA)' "$SCRATCH/pg-inocua.log" | sed -n '1,8p' | sed 's/^/        /'; fi
  else bad "P11: sem a sonda da referencia ou da mudanca inocua"; fi
  _pg_check anexo-a inocua 'check-substrate-drift' \
    "P12a (controle vermelho): a forma (a) do anexo da rc CURADA (--repo-root so como dado) torna a condicao FALSA e e recusada"
  _pg_check anexo-b inocua 'check-substrate-drift' \
    "P12b (controle vermelho): a forma (b) do anexo da rc CURADA (caminhos entre aspas) torna a condicao FALSA e e recusada"
  _pg_check anexo-c inocua 're-pin-codex' \
    "P12c (controle vermelho): a forma (c) do anexo da rc CURADA (drive e barra invertida recusados) torna a condicao FALSA e e recusada"
  _pg_check npm inocua 'npm-publish' \
    "P13 (controle vermelho): npm-publish.yml com o job invertido (publica so -rc.) e recusado"
  _pg_check npm-gatilho inocua 'npm-publish' \
    "P13b (controle vermelho): npm-publish.yml cujo gatilho nao casa mais a tag do GA e recusado"
  _pg_check shim inocua 'ceo-orch-init|install\.sh|shim' \
    "P14 (controle vermelho): o shim do npm que nao roda mais o install.sh e recusado"
  _pg_check versao inocua 'package\.json' \
    "P15 (controle vermelho): npm/package.json fora da 1.4.2 e recusado"
  _pg_check envelope base 'pair-rail-verdict-v1\.4\.2-rc\.1' \
    "P16 (controle vermelho): o envelope assinado da rc ausente do HEAD e recusado"
else printf '  (P pulado: sem upstream ou sem base)\n'; fi

# ===========================================================================
say "C. gerador de envelope com chave GPG DESCARTAVEL"
# Os gates NOVOS do GA (hold da rc.1, arvore congelada, bump no-op, gh_release_edit_idem,
# registry/latest/recibo do passo 18) e a retomada do passo 11 pelo corte inteiro tem o
# INDICE dos seus controles vermelhos no fim (D9-D14): cada controle vermelho que fica
# verde se anota em _red, e uma secao pulada (sem chave, sem clone) nao conta.
_red=""
if [ -n "$CLONE" ] && [ -f "$CLONE/$EV/MANIFEST-ga.sha256" ]; then
  # A chave descartavel e a da secao K0.
  CLAUDE_STUB_DIR="$SCRATCH/claude-stub"; mkdir -p "$CLAUDE_STUB_DIR"
  printf '#!/bin/bash\necho "2.1.999 (Claude Code)"\n' > "$CLAUDE_STUB_DIR/claude"
  chmod 0755 "$CLAUDE_STUB_DIR/claude"
  if [ -n "${FPR:-}" ]; then
    VF="$CLONE/$PLAN_DIR/verdict-fields-v1.4.2.md"
    COND="$CLONE/$EV/CONDITIONS-ga.reviewed.md"
    _gen="$SCRATCH/gen.log"
    # C0 — a sonda das condicoes: a evidencia de um run cuja sonda NAO ficou verde (o
    # modo REPORT-ONLY do harness) e recusada pelo gerador, nomeando a sonda. So quando o
    # P0 ficou vermelho. Sem PLUMBING da linha da sonda: o gerador le o probe-ga.txt e
    # confere a linha da PROVENANCE contra ele, entao o C2 em diante REPROVAM por
    # construcao sobre essa evidencia (a falha ja esta anotada no P0); o F prova a recusa
    # de cada forma de linha e de relatorio que nao prova a sonda verde.
    if [ -n "$PROBE_ENV" ]; then
      if ( cd "$CLONE" && GA_SELFTEST=1 GA_SELFTEST_SCRATCH="$SCRATCH" \
           GA_SELFTEST_SIGNER_FPR="$FPR" GNUPGHOME="$GH" PATH="$CLAUDE_STUB_DIR:$PATH" \
           python3 "$PLAN_DIR/gen-envelope-ga.py" --stage fields \
             --parent "$CAND" --conditions-file "$COND" ) > "$SCRATCH/gen-c0.log" 2>&1; then
        bad "C0: o gerador ACEITOU a evidencia de um run com a sonda vermelha"
      elif grep -q 'sonda das condicoes' "$SCRATCH/gen-c0.log"; then
        ok "C0 (controle vermelho): a evidencia REAL do run com a sonda vermelha e recusada pelo gerador, nomeando a sonda"
      else bad "C0: recusa sem nomear a sonda"; sed -n '1,6p' "$SCRATCH/gen-c0.log"; fi
    fi
    # C1 — CONTROLE VERMELHO: evidencia de um run com STUB nao pode virar
    # envelope de release. O gerador tem de RECUSAR, nomeando o motivo.
    if ( cd "$CLONE" && GA_SELFTEST=1 GA_SELFTEST_SCRATCH="$SCRATCH" \
         GA_SELFTEST_SIGNER_FPR="$FPR" GNUPGHOME="$GH" PATH="$CLAUDE_STUB_DIR:$PATH" \
         python3 "$PLAN_DIR/gen-envelope-ga.py" --stage fields \
           --parent "$CAND" --conditions-file "$COND" ) > "$_gen" 2>&1; then
      bad "C1: o gerador ACEITOU evidencia de um run com stub"
    else
      if grep -qi stub "$_gen"; then
        ok "C1: o gerador recusa evidencia de run com stub, nomeando o motivo"
      else
        bad "C1: recusou, mas sem nomear o stub"
      fi
    fi
    # C2 — fixture da verificacao de pins, ainda com revisores STUB. A linha
    # do codex na PROVENANCE e reescrita para os
    # valores PINADOS (versao / aarch64-apple-darwin / payload do manifesto)
    # e o MANIFEST e regenerado. Isto e PLUMBING: o veredito das 4 partes
    # continua vindo do stub-revisor; nenhuma aprovacao e plantada.
    _pinman="$ROOT/.claude/governance/codex-cli-pin-manifest.json"
    _real_sha="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["payloads"]["aarch64-apple-darwin"]["sha256"])' "$_pinman")"
    _real_ver="$(python3 -c 'import json,sys;print(json.load(open(sys.argv[1]))["package_version"])' "$_pinman")"
    python3 - "$CLONE/$EV/PROVENANCE-ga.md" "$_real_ver" "$_real_sha" <<'PYPROV'
import sys, pathlib, re
p = pathlib.Path(sys.argv[1])
t = p.read_text(encoding="utf-8")
t = re.sub(r"^- codex: .*$",
           "- codex: %s / aarch64-apple-darwin / payload %s" % (sys.argv[2], sys.argv[3]),
           t, count=1, flags=re.M)
# A linha da sonda NAO e tocada: o gerador a confere contra o probe-ga.txt (C0).
p.write_text(t, encoding="utf-8")
PYPROV
    _mf=""
    for n in 1 2 3 4; do
      _mf="$_mf payload-ga-$n.redacted.txt diff-ga-$n.patch"
      _mf="$_mf paths-ga-$n.manifest.txt verdict-ga-$n.txt transcript-ga-$n.log"
    done
    # shellcheck disable=SC2086
    ( cd "$CLONE/$EV" && shasum -a 256 $_mf PROVENANCE-ga.md CANDIDATE.sha \
        run-ga-repass.sh CONDITIONS-ga.reviewed.md probe-ga.txt > MANIFEST-ga.sha256 ) || bad "C2: regeneracao do MANIFEST falhou"
    if ( cd "$CLONE" && GA_SELFTEST=1 GA_SELFTEST_SCRATCH="$SCRATCH" \
         GA_SELFTEST_SIGNER_FPR="$FPR" GNUPGHOME="$GH" PATH="$CLAUDE_STUB_DIR:$PATH" \
         python3 "$PLAN_DIR/gen-envelope-ga.py" --stage fields \
           --parent "$CAND" --conditions-file "$COND" ) > "$_gen" 2>&1; then
      ok "C2: gen --stage fields sobre evidencia com codex PINADO"
    else bad "C2: gen --stage fields"; sed -n '1,15p' "$_gen"; fi
    if [ -f "$VF" ]; then
      grep -q '^verdict: GO-WITH-CONDITIONS' "$VF" \
        && ok "veredito agregado DERIVADO dos 4 rails = GO-WITH-CONDITIONS" \
        || bad "veredito agregado inesperado: $(head -1 "$VF")"
      if grep -qF "  codex_cli: $_real_ver" "$VF"; then
        ok "C2: fields declaram codex_cli $_real_ver (a versao que o manifesto pina)"
      else
        bad "C2: fields sem codex_cli $_real_ver"
      fi
      if grep -qxF '  claude_code: claude-code-cli-2.1.999' "$VF"; then
        ok "C2: fields declaram claude_code MEDIDO (claude --version do stub = 2.1.999), nao digitado"
      else bad "C2: fields sem o claude_code medido: $(grep -m1 claude_code "$VF")"; fi
      # C2b — CONTROLE VERMELHO: `claude --version` ilegivel => recusa nomeada; os
      # fields do C2 ficam intactos (a escrita e atomica e so no sucesso).
      _cbad="$SCRATCH/claude-bad"; mkdir -p "$_cbad"
      printf '#!/bin/bash\necho "versao desconhecida"\n' > "$_cbad/claude"; chmod 0755 "$_cbad/claude"
      _vf_sha="$(shasum -a 256 "$VF" | awk '{print $1}')"
      if ( cd "$CLONE" && GA_SELFTEST=1 GA_SELFTEST_SCRATCH="$SCRATCH" \
           GA_SELFTEST_SIGNER_FPR="$FPR" GNUPGHOME="$GH" PATH="$_cbad:$PATH" \
           python3 "$PLAN_DIR/gen-envelope-ga.py" --stage fields \
             --parent "$CAND" --conditions-file "$COND" ) > "$SCRATCH/gen-cbad.log" 2>&1; then
        bad "C2b: o gerador ACEITOU um claude --version ilegivel"
      elif grep -q 'claude --version' "$SCRATCH/gen-cbad.log" \
           && [ "$(shasum -a 256 "$VF" | awk '{print $1}')" = "$_vf_sha" ]; then
        ok "C2b (controle vermelho): claude --version ilegivel e recusa nomeada; os fields do C2 ficaram intactos"
      else bad "C2b: recusa sem nomear o claude --version (ou os fields mudaram)"; sed -n '1,6p' "$SCRATCH/gen-cbad.log"; fi
      # C3 — assinatura descartavel + montagem do envelope.
      GNUPGHOME="$GH" gpg --batch --quiet --armor --detach-sign -u "$FPR" "$VF" 2>/dev/null
      if ( cd "$CLONE" && GA_SELFTEST=1 GA_SELFTEST_SCRATCH="$SCRATCH" \
           GA_SELFTEST_SIGNER_FPR="$FPR" GNUPGHOME="$GH" PATH="$CLAUDE_STUB_DIR:$PATH" \
           python3 "$PLAN_DIR/gen-envelope-ga.py" --stage envelope \
             --sig "$VF.asc" ) > "$SCRATCH/env.log" 2>&1; then
        ok "C3: gen --stage envelope com assinatura descartavel"
      else bad "C3: gen --stage envelope"; sed -n '1,12p' "$SCRATCH/env.log"; fi
      _envf="$CLONE/.claude/governance/pair-rail-verdict-v1.4.2.md"
      if [ -f "$_envf" ]; then
        if grep -q "^gpg_signature: base64:" "$_envf"; then
          ok "C3: envelope carrega a assinatura em base64 de linha unica"
        else
          bad "C3: envelope sem gpg_signature base64"
        fi
        if python3 - "$_envf" "$ROOT" <<'PYGRAM'
import importlib.util, pathlib, sys
spec = importlib.util.spec_from_file_location(
    "v", str(pathlib.Path(sys.argv[2]) / ".github/scripts/validate-pair-rail-verdict.py"))
v = importlib.util.module_from_spec(spec)
spec.loader.exec_module(v)
bad = v.noncanonical_top_level_lines(pathlib.Path(sys.argv[1]).read_text(encoding="utf-8"))
print(bad)
raise SystemExit(0 if not bad else 1)
PYGRAM
        then ok "C3: envelope passa na gramatica canonica dos twins"
        else bad "C3: envelope REPROVA na gramatica canonica"; fi
        # C4 — o material e do GA: release_tag v1.4.2 nos fields e no envelope (nunca a
        # tag da rc.1), e o registro de revisao e o do re-pass do CANDIDATO v1.4.2.
        if grep -qx 'release_tag: v1.4.2' "$VF" && grep -qx 'release_tag: v1.4.2' "$_envf" \
           && grep -qx '# Pair-Rail Verdict - v1.4.2' "$_envf" \
           && grep -q '^## Review record - re-pass do CANDIDATO v1\.4\.2 (' "$_envf"; then
          ok "C4: fields e envelope do GA: release_tag v1.4.2 e o registro do re-pass do CANDIDATO v1.4.2"
        else bad "C4: fields/envelope sem a moldura do GA ($(grep -m1 '^release_tag:' "$VF"))"; fi
      else bad "C3: envelope nao foi escrito"; fi
    fi
  fi
else
  printf '  (C pulado: sem evidencia do runner)\n'
fi

# ===========================================================================
say "E. topologia do commit do veredito x os DOIS gates (guard local + bind do release.yml)"
# O release.yml (step 15 e o gate delta+ancestry) exige parent_sha == PAI do
# commit que INTRODUZ o veredito; o guard local exige parent_sha == arvore
# revisada, com o veredito DENTRO do delta. As duas so fecham quando evidencia,
# fields e veredito sentam num commit SO sobre o candidato — e o guard local
# SOZINHO nao enxerga a topologia errada (E2 e o controle vermelho disso). Foi
# assim que os cortes anteriores landaram; o molde original do script de corte
# fazia dois commits e reprovaria DEPOIS da tag empurrada (ensaio S349).
_envf="${CLONE:+$CLONE/.claude/governance/pair-rail-verdict-v1.4.2.md}"
if [ -n "$CLONE" ] && [ -f "$_envf" ] && [ -f "$CLONE/$EV/MANIFEST-ga.sha256" ]; then
  _e_vd=".claude/governance/pair-rail-verdict-v1.4.2.md"
  _e_vf="$PLAN_DIR/verdict-fields-v1.4.2.md"
  _e_list="$SCRATCH/e.list"
  { awk '{print $2}' "$CLONE/$EV/MANIFEST-ga.sha256" | sed "s|^|$EV/|"
    printf '%s\n' "$EV/MANIFEST-ga.sha256" "$EV/README-ga.md"
    [ -f "$CLONE/$EV/CONDITIONS-ga.md" ] && printf '%s\n' "$EV/CONDITIONS-ga.md"
    printf '%s\n' "$_e_vf" "$_e_vd"; } > "$_e_list"
  _e_parent="$(awk '/^parent_sha:/{print $2; exit}' "$_envf")"
  if [ "$_e_parent" = "$CAND" ]; then ok "E0: o envelope declara parent_sha == candidato revisado"
  else bad "E0: parent_sha ($_e_parent) != candidato ($CAND)"; fi
  # Replica da derivacao do release.yml: pai do commit que introduziu o veredito.
  _e_bind() {
    local _c _p
    _c="$(git -C "$1" log -n1 --format=%H -- "$_e_vd")"; [ -n "$_c" ] || return 2
    _p="$(git -C "$1" rev-parse "${_c}^" 2>/dev/null)"; [ -n "$_p" ] || return 2
    [ "$_p" = "$_e_parent" ]
  }
  _e_prep() {  # $1 = dir: clone do CLONE no candidato, com a evidencia e o veredito copiados (untracked)
    git clone --quiet --local --shared --no-checkout "$CLONE" "$1" 2>/dev/null || return 1
    git -C "$1" checkout --quiet --detach "$CAND" 2>/dev/null || return 1
    fixture_git_identity "$1" || return 1
    ( cd "$CLONE" && tar -cf - -T "$_e_list" ) | ( cd "$1" && tar -xf - ) || return 1
    return 0
  }
  _e_guard() { python3 "$ROOT/.claude/scripts/local/_release_tag_guard.py" delta --repo "$1" --tag v1.4.2; }
  _e_commit() { git -C "$1" -c user.name=kit -c user.email=kit@invalid -c commit.gpgsign=false commit -q -m "$2"; }

  # E1 — topologia CURADA: um commit so (evidencia + fields + veredito) sobre o candidato.
  _e1="$SCRATCH/e1"
  if _e_prep "$_e1"; then
    if ( cd "$_e1" && xargs git add -- < "$_e_list" ) && _e_commit "$_e1" "kit: evidencia + fields + veredito num commit so"; then
      ok "E1: commit unico (evidencia + fields + veredito) sobre o candidato"
    else bad "E1: commit unico falhou"; fi
    if _e_guard "$_e1" > "$SCRATCH/e1.guard" 2>&1; then
      ok "E1: guard local delta rc 0 ($(grep -c '  ok' "$SCRATCH/e1.guard") asserts)"
    else bad "E1: guard local delta recusou"; sed -n '1,12p' "$SCRATCH/e1.guard"; fi
    if _e_bind "$_e1"; then ok "E1: bind do release.yml fecha (pai do commit do veredito == parent_sha)"
    else bad "E1: bind do release.yml NAO fecha"; fi
  else bad "E1: preparacao do clone falhou"; fi

  # E1b — manter a recusa que revelou o erro do harness: README alterado
  # DEPOIS do candidato revisado nunca entra pela allowlist de evidencia.
  _e1b="$SCRATCH/e1b"
  if _e_prep "$_e1b"; then
    printf '\nTEST ONLY: texto nao revisado depois do candidato.\n' >> "$_e1b/$EV/README-ga.md"
    if ( cd "$_e1b" && xargs git add -- < "$_e_list" ) \
       && _e_commit "$_e1b" "TEST ONLY: evidence plus unreviewed README"; then
      if _e_guard "$_e1b" > "$SCRATCH/e1b.guard" 2>&1; then
        bad "E1b: README nao revisado foi aceito pela allowlist"
      elif grep -qF 'README-ga.md' "$SCRATCH/e1b.guard"; then
        ok "E1b: README alterado apos a revisao continua recusado por nome"
      else bad "E1b: recusa sem identificar README-ga.md"; fi
    else bad "E1b: commit da fixture negativa falhou"; fi
  else bad "E1b: preparacao do clone falhou"; fi

  # E2 — CONTROLE VERMELHO: a topologia do molde (evidencia num commit, veredito
  # no seguinte). O guard local passa; o bind do servidor tem de FALHAR.
  _e2="$SCRATCH/e2"
  if _e_prep "$_e2"; then
    grep -vxF -e "$_e_vf" -e "$_e_vd" "$_e_list" > "$SCRATCH/e2.ev"
    if ( cd "$_e2" && xargs git add -- < "$SCRATCH/e2.ev" ) && _e_commit "$_e2" "kit: evidencia" \
       && git -C "$_e2" add -- "$_e_vf" "$_e_vd" && _e_commit "$_e2" "kit: veredito"; then
      ok "E2: topologia do molde reproduzida (2 commits)"
    else bad "E2: nao consegui reproduzir os 2 commits"; fi
    if _e_guard "$_e2" > "$SCRATCH/e2.guard" 2>&1; then
      ok "E2: o guard local PASSA sobre os 2 commits — ele e cego a topologia (por isso o E2 existe)"
    else bad "E2: o guard local recusou os 2 commits (inesperado: $(grep -m1 FAIL "$SCRATCH/e2.guard"))"; fi
    if _e_bind "$_e2"; then bad "E2: o bind do release.yml FECHOU sobre 2 commits — o controle nao reproduz a classe"
    else ok "E2 (controle vermelho): o bind do release.yml FALHA com o veredito num 2.o commit"; fi
  else bad "E2: preparacao do clone falhou"; fi

  # E3 — o passo 11 do OWNER-GA-CUT.sh, VERBATIM (extraido entre os seus
  # marcadores, com say/bell/mark_step/die shimados), sobre um clone com a
  # evidencia + fields + envelope + .asc untracked. Esperado: UM commit sobre o
  # candidato, com veredito + fields + evidencia, o .asc movido para o backup
  # do HOME (desviado), guard local e bind do servidor fechando.
  _cut="$ROOT/$PLAN_DIR/OWNER-GA-CUT.sh"
  _e3="$SCRATCH/e3"; _e3home="$SCRATCH/e3home"; mkdir -p "$_e3home"
  if _e_prep "$_e3" && cp "$CLONE/$_e_vf.asc" "$_e3/$_e_vf.asc"; then
    {
      printf '#!/bin/bash\nset -euo pipefail\n'
      printf 'say() { :; }; bell() { :; }; mark_step() { :; }\n'
      printf 'die() { printf "FAIL: %%s\\n" "$*" >&2; exit 1; }\n'
      printf 'PLAN_DIR=%s; EV=%s; TAG=v1.4.2; RC_TAG=v1.4.2-rc.1; BASE_TAG=v1.4.1; BASE=1.4.2\n' "$PLAN_DIR" "$EV"
      printf 'COND="$EV/CONDITIONS-ga.md"; VF="$PLAN_DIR/verdict-fields-$TAG.md"\n'
      printf 'VD=".claude/governance/pair-rail-verdict-$TAG.md"; CAND=%s\n' "$CAND"
      printf 'GEN=%s\n' "$PLAN_DIR/gen-envelope-ga.py"
      awk '/^evidence_list\(\) \{$/,/^\}$/' "$_cut"
      awk '/^if should 11; then$/{f=1; next} /^  mark_step 11$/{f=0} f' "$_cut"
    } > "$SCRATCH/e3.sh"
    _e3_n="$(grep -c 'git commit -q -F -' "$SCRATCH/e3.sh" || true)"
    [ "$_e3_n" = "1" ] || bad "E3: o bloco extraido nao contem exatamente 1 commit (tem $_e3_n)"
    if ( cd "$_e3" && HOME="$_e3home" GNUPGHOME="$GH" GA_SELFTEST=1 \
         GA_SELFTEST_SCRATCH="$SCRATCH" GA_SELFTEST_SIGNER_FPR="$FPR" PATH="$CLAUDE_STUB_DIR:$PATH" \
         GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=commit.gpgsign \
         GIT_CONFIG_VALUE_0=false bash "$SCRATCH/e3.sh" ) > "$SCRATCH/e3.log" 2>&1; then
      ok "E3: o passo 11 verbatim corre limpo sobre o clone (rc 0)"
    else bad "E3: o passo 11 verbatim falhou"; sed -n '1,12p' "$SCRATCH/e3.log"; fi
    if grep -qF 'envelope re-derivado dos fields assinados' "$SCRATCH/e3.log" \
       && ! grep -qF 'AVISO: o envelope da arvore' "$SCRATCH/e3.log"; then
      ok "E3: o passo 11 re-deriva o envelope dos fields assinados antes do staging; sobre o envelope intacto do passo 10, sem AVISO de troca (idempotente)"
    else bad "E3: o passo 11 nao re-derivou o envelope, ou trocou o envelope intacto do passo 10"; grep -E 'envelope|AVISO' "$SCRATCH/e3.log" | sed -n '1,4p'; fi
    if [ "$(git -C "$_e3" rev-parse HEAD^ 2>/dev/null)" = "$CAND" ]; then
      ok "E3: o commit senta DIRETAMENTE sobre o candidato"
    else bad "E3: pai do commit != candidato"; fi
    if git -C "$_e3" log -1 --format=%s | grep -qF 'verdito pair-rail v1.4.2 assinado'; then
      ok "E3: assunto do commit sobreviveu (CM-07)"
    else bad "E3: assunto do commit inesperado: $(git -C "$_e3" log -1 --format=%s | cut -c1-80)"; fi
    _e3_files="$(git -C "$_e3" show --name-only --format= HEAD)"
    if printf '%s\n' "$_e3_files" | grep -qxF "$_e_vd" \
       && printf '%s\n' "$_e3_files" | grep -qxF "$_e_vf" \
       && printf '%s\n' "$_e3_files" | grep -qxF "$EV/MANIFEST-ga.sha256"; then
      ok "E3: o commit carrega veredito + fields + MANIFEST ($(printf '%s\n' "$_e3_files" | grep -c .) caminhos)"
    else bad "E3: o commit nao carrega veredito/fields/MANIFEST"; fi
    if [ -f "$_e3home/.rc2-backup/verdict-fields-v1.4.2.md.asc" ] && [ ! -e "$_e3/$_e_vf.asc" ]; then
      ok "E3: o .asc foi movido para o backup do HOME e nao ficou na arvore"
    else bad "E3: o .asc nao foi movido como o passo 11 promete"; fi
    if _e_guard "$_e3" > "$SCRATCH/e3.guard" 2>&1; then ok "E3: guard local delta rc 0 sobre o commit do passo 11"
    else bad "E3: guard local recusou o commit do passo 11"; sed -n '1,10p' "$SCRATCH/e3.guard"; fi
    if _e_bind "$_e3"; then ok "E3: bind do release.yml fecha sobre o commit do passo 11"
    else bad "E3: bind do release.yml NAO fecha"; fi
  else bad "E3: preparacao do clone (ou copia do .asc) falhou"; fi

  # E3b — a RETOMADA do passo 11: o .asc ja esta no backup do HOME (uma tentativa
  # anterior morreu depois de move-lo) e NAO na arvore. O passo 11 verbatim tem de o
  # restaurar, verificar e commitar do mesmo jeito.
  _e3b="$SCRATCH/e3b"; _e3bhome="$SCRATCH/e3bhome"; mkdir -p "$_e3bhome/.rc2-backup"
  if [ -f "$SCRATCH/e3.sh" ] && _e_prep "$_e3b" \
     && cp "$CLONE/$_e_vf.asc" "$_e3bhome/.rc2-backup/verdict-fields-v1.4.2.md.asc"; then
    if ( cd "$_e3b" && HOME="$_e3bhome" GNUPGHOME="$GH" GA_SELFTEST=1 \
         GA_SELFTEST_SCRATCH="$SCRATCH" GA_SELFTEST_SIGNER_FPR="$FPR" PATH="$CLAUDE_STUB_DIR:$PATH" \
         GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=commit.gpgsign \
         GIT_CONFIG_VALUE_0=false bash "$SCRATCH/e3.sh" ) > "$SCRATCH/e3b.log" 2>&1 \
       && grep -q 'assinatura restaurada do backup' "$SCRATCH/e3b.log" \
       && [ "$(git -C "$_e3b" rev-parse HEAD^ 2>/dev/null)" = "$CAND" ] \
       && [ ! -e "$_e3b/$_e_vf.asc" ]; then
      ok "E3b: retomada do passo 11 (so o bloco do passo, sem o G0; o corte inteiro e o E3r) com o .asc so no backup: restaurado, verificado e commitado sobre o candidato"
    else bad "E3b: a retomada do passo 11 falhou"; sed -n '1,12p' "$SCRATCH/e3b.log"; fi
  else bad "E3b: preparacao falhou"; fi
  # E3c — a RETOMADA do passo 11 que morreu entre o `git add` e o `git commit`: o .asc no
  # backup e parte da lista literal JA staged. O passo 11 verbatim desfaz o staging (so
  # caminhos da lista; nada foi commitado), refaz e commita sobre o candidato.
  _e3_env() {  # $1 = clone, $2 = HOME, $3 = log
    ( cd "$1" && HOME="$2" GNUPGHOME="$GH" GA_SELFTEST=1 \
         GA_SELFTEST_SCRATCH="$SCRATCH" GA_SELFTEST_SIGNER_FPR="$FPR" PATH="$CLAUDE_STUB_DIR:$PATH" \
         GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=commit.gpgsign \
         GIT_CONFIG_VALUE_0=false bash "$SCRATCH/e3.sh" ) > "$3" 2>&1
  }
  _e3c="$SCRATCH/e3c"; _e3chome="$SCRATCH/e3chome"; mkdir -p "$_e3chome/.rc2-backup"
  if [ -f "$SCRATCH/e3.sh" ] && _e_prep "$_e3c" \
     && cp "$CLONE/$_e_vf.asc" "$_e3chome/.rc2-backup/verdict-fields-v1.4.2.md.asc" \
     && git -C "$_e3c" add -- "$_e_vf" "$_e_vd" "$EV/MANIFEST-ga.sha256"; then
    if _e3_env "$_e3c" "$_e3chome" "$SCRATCH/e3c.log" \
       && grep -q 'staging de uma tentativa anterior deste passo desfeito' "$SCRATCH/e3c.log" \
       && [ "$(git -C "$_e3c" rev-parse HEAD^ 2>/dev/null)" = "$CAND" ] \
       && git -C "$_e3c" diff --cached --quiet \
       && git -C "$_e3c" show --name-only --format= HEAD | grep -qxF "$_e_vd"; then
      ok "E3c: retomada do passo 11 (so o bloco do passo, sem o G0; o corte inteiro e o E3r) com a lista literal ja staged: o staging e desfeito e refeito, e o commit senta sobre o candidato"
    else bad "E3c: a retomada do passo 11 com staging anterior falhou"; sed -n '1,12p' "$SCRATCH/e3c.log"; fi
  else bad "E3c: preparacao falhou"; fi
  # E3d (controle vermelho): um caminho FORA da lista literal staged — recusa, nada commitado.
  _e3d="$SCRATCH/e3d"; _e3dhome="$SCRATCH/e3dhome"; mkdir -p "$_e3dhome/.rc2-backup"
  if [ -f "$SCRATCH/e3.sh" ] && _e_prep "$_e3d" \
     && cp "$CLONE/$_e_vf.asc" "$_e3dhome/.rc2-backup/verdict-fields-v1.4.2.md.asc" \
     && printf 'x\n' > "$_e3d/TEST-ONLY-stray.txt" \
     && git -C "$_e3d" add -- TEST-ONLY-stray.txt "$_e_vf"; then
    if _e3_env "$_e3d" "$_e3dhome" "$SCRATCH/e3d.log"; then bad "E3d: staging com caminho fora da lista passou pelo passo 11"
    elif grep -q 'com caminho FORA da lista' "$SCRATCH/e3d.log" && grep -q 'TEST-ONLY-stray.txt' "$SCRATCH/e3d.log" \
         && [ "$(git -C "$_e3d" rev-parse HEAD)" = "$CAND" ]; then
      ok "E3d (controle vermelho): um caminho fora da lista literal staged e recusado pelo nome, e nada e commitado"
    else bad "E3d: recusa sem o nome (ou houve commit)"; sed -n '1,10p' "$SCRATCH/e3d.log"; fi
  else bad "E3d: preparacao falhou"; fi

  # E4 — o passo 2: `release.sh bump --stable` num clone local do candidato (a forma que o
  # CUT usa porque o driver recusa porcelain nao vazio e a arvore viva carrega a evidencia
  # untracked). No GA o bump TEM de ser no-op: a arvore da rc.1 ja esta em 1.4.2 e os
  # quatro oraculos estao limpos. Um commit ou arquivo aqui e FALHA — o passo 2 recusaria.
  _e4="$SCRATCH/e4"
  if git clone --quiet --local --no-hardlinks "$UPSTREAM" "$_e4" 2>/dev/null \
     && fixture_git_identity "$_e4"; then
    _e4_head="$(git -C "$_e4" rev-parse HEAD)"
    _e4_rc=0
    ( cd "$_e4" && bash .claude/scripts/local/release.sh bump --stable \
        --today "$(date -u +%Y-%m-%d)" --npm-readme-reviewed ) > "$SCRATCH/e4.log" 2>&1 || _e4_rc=$?
    if [ "$_e4_rc" -ne 0 ]; then
      bad "E4: bump --stable no clone rc=$_e4_rc"; grep -E 'oracle|FAIL|no-op' "$SCRATCH/e4.log" | head -6
    elif [ "$(git -C "$_e4" rev-parse HEAD)" = "$_e4_head" ] \
         && [ -z "$(git -C "$_e4" status --porcelain=v1 --untracked-files=all)" ] \
         && grep -q 'no-op' "$SCRATCH/e4.log"; then
      ok "E4: bump --stable no clone e NO-OP (nada escrito) — o que o GA exige"
    else
      bad "E4: bump --stable NAO foi no-op: $(git -C "$_e4" log -1 --format=%s | cut -c1-60)"
    fi
  else bad "E4: clone local para o bump falhou"; fi
  # E4r — o --restamp que o CUT do GA recusa: no MESMO candidato ele NAO e no-op — a recusa
  # nao e vacua. A data e a de AMANHA (UTC): os carimbos last-reviewed da 1.4.2 tem a data
  # do dia em que foram escritos, e com --today nessa data o --restamp nao escreve nada
  # (medido em 2026-09-29: com --today 2026-09-29 nada; com 2026-09-30, quatro carimbos
  # reescritos e um commit). Amanha e sempre depois de qualquer carimbo ja escrito.
  _e4r_day="$(python3 - <<'PYE4R'
import datetime
print((datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=1)).strftime("%Y-%m-%d"))
PYE4R
)" || _e4r_day=""
  _e4r="$SCRATCH/e4r"
  if [ -n "$_e4r_day" ] && git clone --quiet --local --no-hardlinks "$UPSTREAM" "$_e4r" 2>/dev/null \
     && fixture_git_identity "$_e4r"; then
    _e4r_head="$(git -C "$_e4r" rev-parse HEAD)"
    _e4r_rc=0
    ( cd "$_e4r" && bash .claude/scripts/local/release.sh bump --stable --restamp \
        --today "$_e4r_day" --npm-readme-reviewed ) > "$SCRATCH/e4r.log" 2>&1 || _e4r_rc=$?
    if [ "$(git -C "$_e4r" rev-parse HEAD)" != "$_e4r_head" ] \
       || [ -n "$(git -C "$_e4r" status --porcelain=v1 --untracked-files=all)" ]; then
      ok "E4r: bump --stable --restamp --today $_e4r_day NAO e no-op (rc=$_e4r_rc; commit ou arquivo) — por isso o CUT do GA o recusa"
    else bad "E4r: --restamp foi no-op (rc=$_e4r_rc) — a recusa do CUT seria vacua?"; tail -5 "$SCRATCH/e4r.log"; fi
  else bad "E4r: clone local (ou a data de amanha) para o bump falhou"; fi

  # E7 — o passo 2 do OWNER-GA-CUT.sh VERBATIM (extraido entre os seus marcadores), com um
  # driver STUB no lugar do release.sh: o no-op segue e grava SHA-2P = SHA-2 = HEAD; UM
  # commit `release: v1.4.2` (a forma que a rc aceitava), arquivo nao commitado, dois
  # commits ou outro assunto sao TODOS recusados no GA, ANTES de qualquer fetch/merge/push:
  # o HEAD nao anda e o .cut-state nao ganha linha.
  _e7="$SCRATCH/e7"; mkdir -p "$_e7/tmp"
  {
    printf '#!/bin/bash\nset -euo pipefail\n'
    printf 'say() { :; }; bell() { :; }\nmark_step() { printf "E7-STEP-%%s-MARCADO\\n" "$1"; }\n'
    printf 'die() { printf "FAIL: %%s\\n" "$*" >&2; exit 1; }\n'
    printf 'ROOT="$(pwd -P)"; RELEASE="$E7_DRIVER"; TODAY=2026-09-30; BASE=1.4.2; TAG=v1.4.2; RC_TAG=v1.4.2-rc.1\n'
    printf 'STATE="$E7_STATE"\n'
    awk '/^if should 2; then$/{f=1; next} /^  mark_step 2$/{print; f=0} f' "$ROOT/$PLAN_DIR/OWNER-GA-CUT.sh"
  } > "$SCRATCH/e7.sh"
  printf '#!/bin/bash\necho "stub: no-op"\n' > "$_e7/noop.sh"
  printf '#!/bin/bash\ngit -c user.name=s -c user.email=s@invalid -c commit.gpgsign=false commit -q --allow-empty -m "release: v1.4.2"\n' > "$_e7/commit.sh"
  printf '#!/bin/bash\nprintf "x\\n" > stray-bump-output\n' > "$_e7/dirty.sh"
  printf '#!/bin/bash\nfor m in a "release: v1.4.2"; do git -c user.name=s -c user.email=s@invalid -c commit.gpgsign=false commit -q --allow-empty -m "$m"; done\n' > "$_e7/two.sh"
  printf '#!/bin/bash\ngit -c user.name=s -c user.email=s@invalid -c commit.gpgsign=false commit -q --allow-empty -m "release: v9.9.9"\n' > "$_e7/subject.sh"
  _e7_run() {  # $1 = caso
    local d="$_e7/$1" rc=0
    git init --quiet "$d" 2>/dev/null && fixture_git_identity "$d" \
      && ( cd "$d" && printf 'a\n' > a && git add a && git commit -q -m a ) || return 90
    git -C "$d" rev-parse HEAD > "$_e7/$1.head0"
    : > "$_e7/$1.state"
    ( cd "$d" && printf '\n' | TMPDIR="$_e7/tmp" E7_DRIVER="$_e7/$1.sh" E7_STATE="$_e7/$1.state" bash "$SCRATCH/e7.sh" ) \
      > "$_e7/$1.log" 2>&1 || rc=$?
    return "$rc"
  }
  if _e7_run noop && grep -q 'bump e no-op' "$_e7/noop.log" && grep -q 'E7-STEP-2-MARCADO' "$_e7/noop.log" \
     && [ "$(awk '$1=="SHA-2P"{print $2}' "$_e7/noop.state")" = "$(cat "$_e7/noop.head0")" ] \
     && [ "$(awk '$1=="SHA-2"{print $2}' "$_e7/noop.state")" = "$(cat "$_e7/noop.head0")" ]; then
    ok "E7: passo 2 verbatim com driver no-op segue, grava SHA-2P = SHA-2 = HEAD e marca o passo"
  else bad "E7: passo 2 verbatim recusou o no-op (ou nao gravou SHA-2P/SHA-2)"; sed -n '1,8p' "$_e7/noop.log"; fi
  for _c in commit dirty two subject; do
    if _e7_run "$_c"; then bad "E7: driver '$_c' passou pelo passo 2 do GA"
    elif grep -q 'NAO foi no-op' "$_e7/$_c.log" && grep -q 'NADA foi trazido para main' "$_e7/$_c.log" \
         && ! grep -q 'E7-STEP-2-MARCADO' "$_e7/$_c.log" \
         && [ "$(git -C "$_e7/$_c" rev-parse HEAD)" = "$(cat "$_e7/$_c.head0")" ] \
         && [ ! -s "$_e7/$_c.state" ]; then
      ok "E7 (controle vermelho): driver '$_c' e recusado no passo 2 do GA (NAO foi no-op), antes de fetch/merge/push; o HEAD nao anda e nada e gravado"
      _red="$_red E7-$_c"
    else bad "E7: driver '$_c' recusado sem o motivo do GA (ou o HEAD andou, ou o .cut-state ganhou linha)"; sed -n '1,8p' "$_e7/$_c.log"; fi
  done

  # E5 — evidence_complete_for() (passo 6): evidencia sintetica, um positivo e
  # quatro negativos (cada fonte de verdade mutada por vez).
  _e5="$SCRATCH/e5"
  _e5_run() {  # $1 = mutacao: none | manifest | rc | prov-sha | cand-sha
    local X=0123456789abcdef0123456789abcdef01234567 Y=fedcba9876543210fedcba9876543210fedcba98 d
    d="$_e5/$1"; mkdir -p "$d"
    printf 'a\n' > "$d/x.txt"; printf 'b\n' > "$d/y.txt"
    ( cd "$d" && shasum -a 256 x.txt y.txt > MANIFEST-ga.sha256 )
    printf -- '- Base: v1.4.1 (o) .. Candidato: %s (PRE-tag; base resolvida no run)\nRUNNER-OVERALL: rc=0\n' "$X" > "$d/PROVENANCE-ga.md"
    printf '%s\n' "$X" > "$d/CANDIDATE.sha"
    case "$1" in
      manifest) printf 'z\n' >> "$d/x.txt" ;;
      rc)       sed -i '' 's/rc=0/rc=1/' "$d/PROVENANCE-ga.md" ;;
      prov-sha) sed -i '' "s/$X/$Y/" "$d/PROVENANCE-ga.md" ;;
      cand-sha) printf '%s\n' "$Y" > "$d/CANDIDATE.sha" ;;
    esac
    ( EV="$d"; eval "$(awk '/^evidence_complete_for\(\) \{$/,/^\}$/' "$_cut")"; evidence_complete_for "$X" )
  }
  if _e5_run none; then ok "E5: evidencia completa rc=0 do MESMO candidato e reconhecida"
  else bad "E5: o positivo foi recusado"; fi
  for _m in manifest rc prov-sha cand-sha; do
    if _e5_run "$_m"; then bad "E5: mutacao '$_m' passou como evidencia completa"
    else ok "E5 (controle vermelho): mutacao '$_m' e recusada"; fi
  done

  # E6 — o validador do SERVIDOR (step 15 do release.yml, argv literal) sobre
  # o commit do passo 11. So a presenca da assinatura e verificada aqui (a
  # verificacao GPG do servidor e do `git verify-tag`), entao a chave
  # descartavel serve.
  if [ -d "$_e3" ] && [ "$(git -C "$_e3" rev-parse HEAD^ 2>/dev/null)" = "$CAND" ]; then
    if ( cd "$_e3" && GNUPGHOME="$GH" python3 .github/scripts/validate-pair-rail-verdict.py \
          --verdict-file "$_e_vd" --parent-sha "$CAND" --release-tag v1.4.2 \
          --max-age-hours 24 --recompute-inputs-hash \
          --codex-cli-pin-file .claude/governance/codex-cli-pin.txt \
          --codex-cli-binary-sha256-file .claude/governance/codex-cli-binary-sha256.txt \
          --codex-pin-manifest-file .claude/governance/codex-cli-pin-manifest.json \
          --inputs-hash-paths-file .claude/governance/pair-rail-inputs-hash-manifest.txt ) > "$SCRATCH/e6.log" 2>&1; then
      ok "E6: validador do servidor (argv do step 15) aceita o envelope sobre o commit unico"
    else bad "E6: validador do servidor RECUSOU"; grep -E 'INVALID|FAIL|Error|error' "$SCRATCH/e6.log" | head -6; fi
  else printf '  (E6 pulado: sem commit do E3)\n'; fi
else
  printf '  (E pulado: sem envelope da seccao C)\n'
fi

# ===========================================================================
say "W. aviso de carga antes do preflight (warn_load)"
_cut="$ROOT/$PLAN_DIR/OWNER-GA-CUT.sh"
{ printf '#!/bin/bash\nset -euo pipefail\n'
  printf 'bell() { :; }\n'
  awk '/^warn_load\(\) \{$/,/^\}$/' "$_cut"
  printf '_load_pair() { printf "%%s\\n" "$W_LOAD"; }\n'
  printf 'warn_load 1\n'; } > "$SCRATCH/w.sh"
if printf '\n' | W_LOAD="9.50 4" bash "$SCRATCH/w.sh" > "$SCRATCH/w1.log" 2>&1 \
   && grep -q 'AVISO: a maquina esta CARREGADA' "$SCRATCH/w1.log" \
   && grep -q 'TestOutputScanPerfRigorous' "$SCRATCH/w1.log"; then
  ok "W: carga alta (9.50 em 4 CPUs) avisa, nomeia os testes de p99 e pede Enter"
else bad "W: carga alta nao avisou como devia"; sed -n '1,8p' "$SCRATCH/w1.log"; fi
if W_LOAD="9.50 4" bash "$SCRATCH/w.sh" < /dev/null > "$SCRATCH/w2.log" 2>&1; then
  bad "W: carga alta seguiu SEM ler o Enter"
else ok "W (controle vermelho): carga alta sem Enter (EOF) aborta, como o ctrl-D"; fi
if W_LOAD="0.10 8" bash "$SCRATCH/w.sh" < /dev/null > "$SCRATCH/w3.log" 2>&1 \
   && ! grep -q 'AVISO' "$SCRATCH/w3.log"; then
  ok "W: carga baixa (0.10 em 8) segue sem pedir Enter"
else bad "W: carga baixa pediu Enter ou avisou"; fi
if W_LOAD="" bash "$SCRATCH/w.sh" < /dev/null > "$SCRATCH/w4.log" 2>&1 \
   && grep -q 'ilegivel' "$SCRATCH/w4.log"; then
  ok "W: carga ilegivel vira aviso textual, sem bloquear"
else bad "W: carga ilegivel nao foi tratada"; fi

# ===========================================================================
say "G. o aviso da sonda GPG do preflight segue o driver (gpg_probe_hint)"
{ printf '#!/bin/bash\nset -euo pipefail\nRELEASE="$1"\n'
  awk '/^gpg_probe_hint\(\) \{$/,/^\}$/' "$_cut"
  printf 'gpg_probe_hint\n'; } > "$SCRATCH/g.sh"
printf '      | gpg --yes --local-user "$SIGN_KEY" --armor --detach-sign --output "$sig_probe" \\\n' > "$SCRATCH/g-yes.sh"
printf '      | gpg --local-user "$SIGN_KEY" --armor --detach-sign --output "$sig_probe" \\\n' > "$SCRATCH/g-no.sh"
if bash "$SCRATCH/g.sh" "$SCRATCH/g-yes.sh" > "$SCRATCH/g1.log" 2>&1 \
   && grep -q 'chama o gpg com --yes' "$SCRATCH/g1.log" && ! grep -q 'File exists' "$SCRATCH/g1.log"; then
  ok "G: driver com --yes na sonda: o aviso nao pede o y"
else bad "G: o aviso pediu o y com o --yes no driver"; sed -n '1,6p' "$SCRATCH/g1.log"; fi
if bash "$SCRATCH/g.sh" "$SCRATCH/g-no.sh" > "$SCRATCH/g2.log" 2>&1 && grep -q 'File exists. Overwrite?' "$SCRATCH/g2.log"; then
  ok "G (controle vermelho): driver SEM o --yes: o aviso pede o y, como antes da relmeta-142"
else bad "G: sem o --yes o aviso nao pediu o y"; sed -n '1,6p' "$SCRATCH/g2.log"; fi
if grep -qE 'gpg --yes[^#]*--detach-sign' "$ROOT/.claude/scripts/local/release.sh"; then
  ok "G: o release.sh desta arvore chama o gpg da sonda com --yes (a relmeta-142 landou antes da rc.1)"
else bad "G: o release.sh desta arvore NAO tem o --yes na sonda — esta arvore nao e a da rc.1"; fi

# ===========================================================================
say "FZ. G0: a arvore da rc.1 CONGELADA (assert_rc_tree_frozen)"
# A funcao VERBATIM num repo de fixture com a tag v1.4.2-rc.1: CLAUDE.md e planos
# NUMERADOS (o diretorio PLAN-<N>/ e o arquivo PLAN-<N>-*.md) mudados depois da tag passam;
# um plano NAO numerado, um hook, o sitio de versao de um bump e um RENAME de hook para
# dentro de um plano numerado (conta pelo nome VELHO: --no-renames) sao recusados pelo nome.
_cut="$ROOT/$PLAN_DIR/OWNER-GA-CUT.sh"
_fz="$SCRATCH/fz"
if git init --quiet "$_fz" 2>/dev/null && fixture_git_identity "$_fz" \
   && ( cd "$_fz" && mkdir -p .claude/hooks .claude/plans/PLAN-193 \
        && printf 'x\n' > .claude/hooks/h.py && printf 'c\n' > CLAUDE.md \
        && printf 'r\n' > .claude/plans/README.md && printf '1.4.2\n' > .claude/.framework-version \
        && git add -- CLAUDE.md .claude/hooks/h.py .claude/plans/README.md .claude/.framework-version \
        && git commit -q -m base && git tag v1.4.2-rc.1 \
        && printf 'c2\n' >> CLAUDE.md && printf 'l\n' > .claude/plans/PLAN-193/LEDGER.md \
        && printf 'p\n' > .claude/plans/PLAN-193-x.md \
        && git add -- CLAUDE.md .claude/plans/PLAN-193/LEDGER.md .claude/plans/PLAN-193-x.md \
        && git commit -q -m ok && git branch fz-ok \
        && printf 'r2\n' >> .claude/plans/README.md && git commit -q -am plans-readme && git branch fz-readme \
        && git checkout -q --detach fz-ok && printf 'y\n' >> .claude/hooks/h.py && git commit -q -am hook \
        && git branch fz-hook \
        && git checkout -q --detach fz-ok && printf '1.4.3\n' > .claude/.framework-version \
        && git commit -q -am bump && git branch fz-bump \
        && git checkout -q --detach fz-ok && git mv .claude/hooks/h.py .claude/plans/PLAN-193/h.py \
        && git commit -q -m rename && git branch fz-rename ); then
  # O CUT confere a partir do commit PINADO da tag da rc (RC_TAG_COMMIT): aqui, o da fixture.
  { printf '#!/bin/bash\nset -euo pipefail\n'
    printf 'die() { printf "FAIL: %%s\\n" "$*" >&2; exit 1; }\n'
    printf 'TAG=v1.4.2; RC_TAG=v1.4.2-rc.1; BASE_TAG=v1.4.1; RC_TAG_COMMIT=%s\n' \
      "$(git -C "$_fz" rev-parse 'refs/tags/v1.4.2-rc.1^{commit}')"
    awk '/^assert_rc_tree_frozen\(\) \{$/,/^\}$/' "$_cut"
    printf 'assert_rc_tree_frozen "$1"\n'; } > "$SCRATCH/fz.sh"
  if ( cd "$_fz" && bash "$SCRATCH/fz.sh" fz-ok ) > "$SCRATCH/fz-ok.log" 2>&1 \
     && grep -q 'OK: desde a v1.4.2-rc.1 so mudaram CLAUDE.md e planos numerados' "$SCRATCH/fz-ok.log"; then
    ok "FZ: CLAUDE.md + plano numerado (diretorio e arquivo) depois da tag passam"
  else bad "FZ: o caso bom foi recusado"; sed -n '1,6p' "$SCRATCH/fz-ok.log"; fi
  _fz_red() {  # $1 = branch, $2 = caminho que a recusa tem de nomear, $3 = rotulo
    if ( cd "$_fz" && bash "$SCRATCH/fz.sh" "$1" ) > "$SCRATCH/$1.log" 2>&1; then
      bad "FZ: $3 passou"
    elif grep -qF -- "$2" "$SCRATCH/$1.log" \
         && grep -q 'desde a v1.4.2-rc.1 mudou caminho FORA de CLAUDE.md' "$SCRATCH/$1.log"; then
      ok "FZ (controle vermelho): $3 e recusado pelo nome ($2)"; _red="$_red $1"
    else bad "FZ: $3 recusado sem nomear $2"; sed -n '1,6p' "$SCRATCH/$1.log"; fi
  }
  _fz_red fz-readme .claude/plans/README.md "plano NAO numerado (entregue pelo install)"
  _fz_red fz-hook .claude/hooks/h.py "hook mudado depois da tag"
  _fz_red fz-bump .claude/.framework-version "sitio de versao de um bump (o GA nao bumpa)"
  _fz_red fz-rename .claude/hooks/h.py "rename de hook para dentro de um plano numerado"
else bad "FZ: fixture do congelamento falhou"; fi

# ===========================================================================
say "H. G0: o hold ADR-103 da rc.1 (assert_rc_hold) — positivo e onze vermelhos"
# A funcao VERBATIM num repo de fixture com uma tag v1.4.2-rc.1 assinada pela chave
# DESCARTAVEL (sobre um commit de veredito cujo pai e o candidato), um remoto bare local e
# um `gh` STUB que devolve o valor FINAL do --jq. O objeto da tag, o commit dela e o
# candidato PINADOS no CUT (RC_TAG_OBJ, RC_TAG_COMMIT, RC_CAND) sao, aqui, os da fixture.
# H11/H12: a assinatura da tag num chaveiro SEM a chave (o `git tag -v`) e um HEAD fora
# da linha da rc (o `merge-base --is-ancestor`) — o objeto pinado (H9) nao cobre nenhum.
if [ -n "${FPR:-}" ] && [ -n "${GH:-}" ]; then
  _h="$SCRATCH/h"; mkdir -p "$_h/bin" "$_h/gnupg-empty"; chmod 0700 "$_h/gnupg-empty"
  cat > "$_h/bin/gh" <<'GHEOF'
#!/bin/bash
# gh STUB: devolve o valor FINAL que o CUT extrairia com --jq (o jq real nao roda).
case "$1 $2" in
  "release view")
    if [ -n "${H_GH_FAIL:-}" ]; then printf '%s\n' "$H_GH_FAIL" >&2; exit 1; fi
    printf '%s\n' "$H_RELEASE_JSON" ;;
  "run list") printf '%s\n' "$H_RUN_ID" ;;
  "run view") printf '%s\n' "$H_AWAIT" ;;
  *) echo "gh stub: chamada inesperada: $*" >&2; exit 9 ;;
esac
GHEOF
  chmod 0755 "$_h/bin/gh"
  if git init --quiet --bare "$_h/origin.git" 2>/dev/null \
     && git init --quiet "$_h/w" 2>/dev/null && fixture_git_identity "$_h/w" \
     && ( cd "$_h/w" && printf 'a\n' > a && git add a && git commit -q -m "candidato" \
          && printf 'v\n' > v && git add v && git commit -q -m "veredito da rc" ) \
     && GNUPGHOME="$GH" git -C "$_h/w" -c user.signingkey="$FPR" -c gpg.program=gpg \
          tag -s -m "TEST ONLY: rc fixture" v1.4.2-rc.1 2>"$SCRATCH/h-tag.log" \
     && ( cd "$_h/w" && printf 'b\n' > b && git add b && git commit -q -m b ) \
     && git -C "$_h/w" remote add origin "$_h/origin.git" \
     && git -C "$_h/w" push -q origin HEAD:refs/heads/main refs/tags/v1.4.2-rc.1 2>/dev/null; then
    _h_obj="$(git -C "$_h/w" rev-parse refs/tags/v1.4.2-rc.1)"
    _h_com="$(git -C "$_h/w" rev-parse 'refs/tags/v1.4.2-rc.1^{commit}')"
    _h_cand="$(git -C "$_h/w" rev-parse 'refs/tags/v1.4.2-rc.1^{commit}^')"
    { printf '#!/bin/bash\nset -euo pipefail\n'
      printf 'die() { printf "FAIL: %%s\\n" "$*" >&2; exit 1; }\n'
      printf 'TAG=v1.4.2; BASE=1.4.2; RC_TAG=v1.4.2-rc.1; BASE_TAG=v1.4.1\n'
      printf 'RC_TAG_OBJ="${H_RC_OBJ:-%s}"; RC_TAG_COMMIT="${H_RC_COMMIT:-%s}"; RC_CAND="${H_RC_CAND:-%s}"\n' \
        "$_h_obj" "$_h_com" "$_h_cand"
      awk '/^assert_rc_hold\(\) \{$/,/^\}$/' "$_cut"
      printf 'assert_rc_hold\n'; } > "$_h/hold.sh"
    _h_run() {  # $1 = horas atras, $2 = isPrerelease, $3 = isDraft, $4 = await, $5 = log, $6 = stderr de um gh que FALHA
      local pub
      pub="$(python3 - "$1" <<'PYH'
import sys, datetime
t = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=float(sys.argv[1]))
print(t.strftime("%Y-%m-%dT%H:%M:%SZ"))
PYH
)"
      ( cd "$_h/w" && PATH="$_h/bin:$PATH" GNUPGHOME="${H_GNUPGHOME:-$GH}" \
          H_RELEASE_JSON="{\"isPrerelease\": $2, \"isDraft\": $3, \"publishedAt\": \"$pub\"}" \
          H_RUN_ID=4242 H_AWAIT="$4" H_GH_FAIL="${6:-}" bash "$_h/hold.sh" ) > "$5" 2>&1
    }
    if _h_run 25 true false success "$SCRATCH/h1.log" \
       && grep -q 'OK: hold ADR-103 da v1.4.2-rc.1 completo' "$SCRATCH/h1.log"; then
      ok "H1: 25 h, pre-release publico, gate da rc success -> hold completo"
    else bad "H1: o caso bom foi recusado"; sed -n '1,6p' "$SCRATCH/h1.log"; fi
    if _h_run 23.5 true false success "$SCRATCH/h2.log"; then bad "H2: 23,5 h de hold passou"
    elif grep -q 'hold ADR-103 incompleto' "$SCRATCH/h2.log" \
         && grep -q 'O GA pode ser cortado a partir de' "$SCRATCH/h2.log"; then
      ok "H2 (controle vermelho): 23,5 h < 24 h e recusado (o hold ainda nao passou), com a hora mais cedo do corte"
      _red="$_red H2"
    else bad "H2: recusa sem o motivo do hold (ou sem a hora mais cedo do corte)"; sed -n '1,6p' "$SCRATCH/h2.log"; fi
    # H9/H10 — a tag da rc que o G0 aceita e a PINADA: um objeto recriado (outro objeto
    # sob o mesmo nome) e um commit cujo pai nao e o candidato revisado sao recusados.
    if H_RC_OBJ="$_h_com" _h_run 25 true false success "$SCRATCH/h9.log"; then
      bad "H9: tag da rc com objeto diferente do pinado passou"
    elif grep -q 'este kit promove o objeto' "$SCRATCH/h9.log"; then
      ok "H9 (controle vermelho): tag da rc que nao e o objeto PINADO (recriada ou movida) e recusada"
    else bad "H9: recusa sem o motivo do objeto pinado"; sed -n '1,6p' "$SCRATCH/h9.log"; fi
    if H_RC_CAND="$_h_com" _h_run 25 true false success "$SCRATCH/h10.log"; then
      bad "H10: commit da rc cujo pai nao e o candidato pinado passou"
    elif grep -q 'nao e o candidato que o re-pass da rc revisou' "$SCRATCH/h10.log"; then
      ok "H10 (controle vermelho): o pai do commit da tag da rc tem de ser o candidato revisado (RC_CAND)"
    else bad "H10: recusa sem o motivo do candidato"; sed -n '1,6p' "$SCRATCH/h10.log"; fi
    if _h_run 25 true true success "$SCRATCH/h3.log"; then bad "H3: pre-release em DRAFT passou"
    elif grep -q 'ausente, draft' "$SCRATCH/h3.log"; then ok "H3 (controle vermelho): pre-release em draft e recusado"
    else bad "H3: recusa sem o motivo do draft"; sed -n '1,6p' "$SCRATCH/h3.log"; fi
    if _h_run 25 false false success "$SCRATCH/h4.log"; then bad "H4: release NAO pre-release passou"
    elif grep -q 'ausente, draft' "$SCRATCH/h4.log"; then ok "H4 (controle vermelho): release sem a flag pre-release e recusado"
    else bad "H4: recusa sem o motivo"; sed -n '1,6p' "$SCRATCH/h4.log"; fi
    if _h_run 25 true false failure "$SCRATCH/h5.log"; then bad "H5: await-release-gate failure passou"
    elif grep -q 'NAO e success' "$SCRATCH/h5.log"; then ok "H5 (controle vermelho): o gate da rc sem success e recusado (controle positivo do publish)"
    else bad "H5: recusa sem o motivo do gate"; sed -n '1,6p' "$SCRATCH/h5.log"; fi
    # H7/H8 — uma falha de TRANSPORTE do gh tem nome proprio e a rota (re-rodar);
    # «release not found» e ausencia real.
    if _h_run 25 true false success "$SCRATCH/h7.log" "error connecting to api.github.com"; then
      bad "H7: gh release view com falha de transporte passou"
    elif grep -q 'falhou (rc=1; transporte?): error connecting to api.github.com' "$SCRATCH/h7.log" \
         && grep -q 're-rode este script' "$SCRATCH/h7.log" && ! grep -q 'ausente' "$SCRATCH/h7.log"; then
      ok "H7 (controle vermelho): falha de transporte do gh no hold tem nome proprio e a rota (re-rodar)"; _red="$_red H7"
    else bad "H7: falha de transporte sem nome"; sed -n '1,6p' "$SCRATCH/h7.log"; fi
    if _h_run 25 true false success "$SCRATCH/h8.log" "release not found"; then
      bad "H8: pre-release ausente passou"
    elif grep -q 'ausente (gh: release not found)' "$SCRATCH/h8.log"; then
      ok "H8 (controle vermelho): «release not found» e ausencia do pre-release, nao transporte"
    else bad "H8: ausencia sem o motivo"; sed -n '1,6p' "$SCRATCH/h8.log"; fi
    # H11 — a tag e o objeto pinado, mas a assinatura NAO verifica: um chaveiro vazio (sem
    # a chave publica do signatario). O H1 e o gemeo positivo (o mesmo tudo, com a chave).
    if H_GNUPGHOME="$_h/gnupg-empty" _h_run 25 true false success "$SCRATCH/h11.log"; then
      bad "H11: tag da rc cuja assinatura nao verifica passou"
    elif grep -q 'assinatura da tag v1.4.2-rc.1 local nao verifica' "$SCRATCH/h11.log"; then
      ok "H11 (controle vermelho): a tag da rc pinada com a assinatura que NAO verifica (chaveiro sem a chave) e recusada pelo nome"
      _red="$_red H11"
    else bad "H11: recusa sem o motivo da assinatura"; sed -n '1,6p' "$SCRATCH/h11.log"; fi
    # H12 — o HEAD FORA da linha da rc: o candidato (o pai do commit da tag) no lugar do
    # topo. Tag, remoto e gh sao os do H1; so o HEAD nao descende do commit da tag.
    _h_top="$(git -C "$_h/w" rev-parse HEAD)"
    if git -C "$_h/w" checkout -q --detach "$_h_cand" 2>/dev/null; then
      if _h_run 25 true false success "$SCRATCH/h12.log"; then
        bad "H12: HEAD que nao descende da tag da rc passou"
      elif grep -q 'HEAD nao descende da v1.4.2-rc.1' "$SCRATCH/h12.log"; then
        ok "H12 (controle vermelho): HEAD fora da linha da rc (nao descende do commit da tag) e recusado pelo nome"
        _red="$_red H12"
      else bad "H12: recusa sem o motivo da ancestralidade"; sed -n '1,6p' "$SCRATCH/h12.log"; fi
      git -C "$_h/w" checkout -q --detach "$_h_top" 2>/dev/null || bad "H12: voltar ao topo da fixture falhou"
    else bad "H12: checkout do candidato da fixture falhou"; fi
    # H6 (por ultimo: muda o remoto): OUTRO objeto sob o nome da tag (uma tag leve no commit).
    if git -C "$_h/w" push -q -f origin "v1.4.2-rc.1^{commit}:refs/tags/v1.4.2-rc.1" 2>/dev/null; then
      if _h_run 25 true false success "$SCRATCH/h6.log"; then bad "H6: tag remota trocada passou"
      elif grep -q 'mesmo OBJETO' "$SCRATCH/h6.log"; then ok "H6 (controle vermelho): tag remota que nao e o objeto assinado local e recusada"
      else bad "H6: recusa sem o motivo do objeto"; sed -n '1,6p' "$SCRATCH/h6.log"; fi
    else bad "H6: nao consegui trocar a tag remota"; fi
  else bad "H: fixture da tag assinada/remoto falhou"; sed -n '1,6p' "$SCRATCH/h-tag.log" 2>/dev/null; fi
else printf '  (H pulado: sem chave descartavel da secao K0)\n'; fi

# ===========================================================================
say "K. G0: o kit tem de estar COMMITADO (assert_kit_committed)"
_k="$SCRATCH/k"
if git init --quiet "$_k" 2>/dev/null && fixture_git_identity "$_k" \
   && ( cd "$_k" && mkdir -p ev && printf 'r\n' > ev/run.sh && printf 'g\n' > gen.py \
        && git add -- ev/run.sh gen.py && git commit -q -m kit ); then
  { printf '#!/bin/bash\nset -euo pipefail\n'
    printf 'die() { printf "FAIL: %%s\\n" "$*" >&2; exit 1; }\n'
    printf 'TAG=v1.4.2; KIT_TRACKED="ev/run.sh gen.py ev/README-ga.md"\n'
    awk '/^assert_kit_committed\(\) \{$/,/^\}$/' "$_cut"
    printf 'assert_kit_committed\n'; } > "$SCRATCH/k.sh"
  printf 'readme\n' > "$_k/ev/README-ga.md"
  if ( cd "$_k" && bash "$SCRATCH/k.sh" ) > "$SCRATCH/k1.log" 2>&1; then bad "K: README untracked passou"
  elif grep -q 'ev/README-ga.md (NAO rastreado)' "$SCRATCH/k1.log"; then ok "K (controle vermelho): kit untracked e recusado pelo nome"
  else bad "K: recusa sem nomear o untracked"; fi
  ( cd "$_k" && git add ev/README-ga.md && git commit -q -m readme )
  if ( cd "$_k" && bash "$SCRATCH/k.sh" ) > "$SCRATCH/k2.log" 2>&1; then ok "K: kit commitado e identico ao HEAD passa"
  else bad "K: o caso bom foi recusado"; sed -n '1,6p' "$SCRATCH/k2.log"; fi
  printf 'editado\n' >> "$_k/gen.py"
  if ( cd "$_k" && bash "$SCRATCH/k.sh" ) > "$SCRATCH/k3.log" 2>&1; then bad "K: kit modificado passou"
  elif grep -q 'gen.py (diferente do HEAD)' "$SCRATCH/k3.log"; then ok "K (controle vermelho): kit modificado e recusado pelo nome"
  else bad "K: recusa sem nomear o modificado"; fi
else bad "K: fixture do kit falhou"; fi

# ===========================================================================
say "S. o teto da espera de CI e o conselho do vermelho (estatico sobre o CUT)"
if grep -qF 'CI_WAIT_MAX_MIN="${GA_CI_WAIT_MAX_MIN:-150}"' "$_cut" \
   && grep -qF '[ "$i" -le "$CI_WAIT_MAX_MIN" ]' "$_cut" \
   && ! grep -qF '"CI nao terminou em 90 min"' "$_cut"; then
  ok "S: wait_ci_green espera ate 150 min por padrao (o teto de 90 saiu)"
else bad "S: o teto da espera de CI nao e o de 150 min"; fi
if grep -qF 'gh run rerun <run> --failed' "$_cut" && grep -qF 'gh run rerun <run dele> --failed' "$_cut"; then
  ok "S: os vermelhos de CI e do release.yml nomeiam o rerun (e o do npm-publish.yml)"
else bad "S: o vermelho nao nomeia o rerun"; fi
if [ "$(grep -c '^\$PREFLIGHT_RED_HINT"$' "$_cut")" = "2" ] \
   && grep -qF 'O preflight conta QUALQUER workflow sobre este commit, agendado (cron) inclusive.' "$_cut" \
   && grep -qF 'inclusive um run AGENDADO (cron) durante o freeze' "$_cut" \
   && grep -qF 'Se o motivo e «a workflow for HEAD is still running»' "$_cut" \
   && grep -qF 'Se o motivo e «hooks test suite failed (serial)»' "$_cut" \
   && grep -qF 'Inicio dos crons (UTC): todo dia 06:43, 07:00, 07:37 e 11:00;' "$_cut"; then
  ok "S: os preflights 1 e 15 nomeiam o rerun, o run ainda rodando e a suite serial; o run AGENDADO e as janelas de cron sao declarados"
else bad "S: o conselho do vermelho dos preflights (ou as janelas de cron) falta"; fi
# O vermelho de uma suite de testes do preflight (a saida do pytest e suprimida pelo
# driver): a rota e o MESMO pytest sem a supressao, no clone que o passo 1 nomeia, e a
# classe dos testes que so rodam com as TAGS (o checkout do CI e raso) e declarada.
if grep -qF 'Se o motivo e outro «... test suite failed (...)»' "$_cut" \
   && grep -qF "python3 -m pytest .claude/scripts/tests/ .claude/scripts/optimizer/tests/ -m 'not serial' --strict-markers" "$_cut" \
   && grep -qF 'o checkout do CI e raso' "$_cut" \
   && grep -qF '(e ali que o pytest abaixo roda; apague-o depois).' "$_cut" \
   && grep -qF '"scripts test suite failed (not serial)"' "$ROOT/.claude/scripts/local/release.sh" \
   && grep -qF '"hooks test suite failed (not serial)"' "$ROOT/.claude/scripts/local/release.sh"; then
  ok "S: o vermelho de uma suite do preflight tem rota (o mesmo pytest sem a supressao, no clone nomeado), e as frases do driver batem"
else bad "S: o vermelho de uma suite do preflight nao tem rota (ou o driver mudou as frases)"; fi
if grep -qF '"a workflow for HEAD is not green"' "$ROOT/.claude/scripts/local/release.sh" \
   && grep -qF '"a workflow for HEAD is still running — wait for it"' "$ROOT/.claude/scripts/local/release.sh" \
   && grep -qF '"hooks test suite failed (serial)"' "$ROOT/.claude/scripts/local/release.sh" \
   && grep -qF '"validate-governance.sh nonzero"' "$ROOT/.claude/scripts/local/release.sh"; then
  ok "S: as quatro frases do driver que o conselho cita existem no release.sh"
else bad "S: o conselho cita frase que o release.sh nao emite mais"; fi
if grep -qF 'ARCHIVE_ROOT="$HOME/.ceo-ga-archive"' "$_cut" \
   && grep -qF 'Preserve a tentativa, inclusive parcial, FORA do repositorio' "$_cut"; then
  ok "S: a tentativa do re-pass e arquivada FORA do repositorio ($HOME/.ceo-ga-archive/)"
else bad "S: a rota de arquivo da tentativa nao e FORA do repositorio"; fi
# GA: toda chamada `gh release edit` do corte passa por gh_release_edit_idem (o unico abort
# do corte do GA v1.4.1 foi um `connection reset` no `gh release edit --draft` do passo 18,
# com o PATCH ja aplicado). Uma INVOCACAO e a forma `gh release edit "` — a rota impressa
# dentro de uma mensagem nao tem a aspa.
_ge_def="$(grep -c '^gh_release_edit_idem() {$' "$_cut")" || _ge_def=0
_ge_raw="$(awk '
  /^gh_release_edit_idem\(\) \{$/ { inf = 1; next }
  inf && /^\}$/ { inf = 0; next }
  !inf && /gh release edit "/ { print NR ": " $0 }' "$_cut")" || _ge_raw="(awk falhou)"
_ge_calls="$(awk '/^[[:space:]]*#/ { next } /gh_release_edit_idem [^(]/ { n++ } END { print n + 0 }' "$_cut")" || _ge_calls=0
if [ "$_ge_def" = "1" ] && [ -z "$_ge_raw" ] && [ "$_ge_calls" -ge 2 ]; then
  ok "S: gh_release_edit_idem definida uma vez; nenhuma chamada crua de gh release edit fora dela ($_ge_calls chamada(s) pela funcao)"
else bad "S: gh release edit fora de gh_release_edit_idem (definicoes=$_ge_def, chamadas pela funcao=$_ge_calls):
$_ge_raw"; fi
# GA: o driver roda com --stable (preflight nos passos 1 e 15, bump no 2, tag no 15); nada
# de --rc nem do banner da rc.
if [ "$(grep -cE 'bash "\$RELEASE" (preflight|bump|tag) --stable' "$_cut")" -ge 4 ] \
   && ! grep -qE '"\$RELEASE" [a-z]+ --rc' "$_cut" && ! grep -q 'CORTADA' "$_cut"; then
  ok "S: o driver roda com --stable nos passos 1, 2 e 15; nenhum --rc nem o banner da rc"
else bad "S: o CUT do GA ainda chama o driver com --rc (ou carrega o banner da rc)"; fi
# GA: o G0 chama o hold da rc.1 e o congelamento contra o HEAD (as funcoes tem as secoes
# H e FZ; o R prova o efeito no script inteiro).
awk '/^say "G0 pre-condicoes"$/{f=1} /^if should 1; then$/{f=0} f' "$_cut" > "$SCRATCH/s-g0.txt" \
  || bad "S: extracao do G0 falhou"
if grep -qE '^[[:space:]]*assert_rc_hold$' "$SCRATCH/s-g0.txt" \
   && grep -qE '^[[:space:]]*assert_rc_tree_frozen HEAD$' "$SCRATCH/s-g0.txt"; then
  ok "S: o G0 chama assert_rc_hold e assert_rc_tree_frozen HEAD"
else bad "S: o G0 nao chama assert_rc_hold e/ou assert_rc_tree_frozen HEAD"; fi

# ===========================================================================
say "V. wait_ci_green: um gh run view transitorio tem NOME (nunca um traceback)"
_v="$SCRATCH/v"; mkdir -p "$_v/bin"
cat > "$_v/bin/gh" <<'GHVEOF'
#!/bin/bash
case "$1 $2" in
  "run list")
    for _a in "$@"; do [ "$_a" = "--workflow" ] && { echo 4242; exit 0; }; done
    echo '{"n": 1, "p": 0, "b": 0}' ;;
  "run view") [ -n "${V_VIEW:-}" ] || exit 1; printf '%s\n' "$V_VIEW" ;;
  *) echo "gh stub: chamada inesperada: $*" >&2; exit 9 ;;
esac
GHVEOF
chmod 0755 "$_v/bin/gh"
{ printf '#!/bin/bash\nset -euo pipefail\n'
  printf 'die() { printf "FAIL: %%s\\n" "$*" >&2; exit 1; }\n'
  printf 'sleep() { :; }\nCI_WAIT_MAX_MIN=3; TAG=v1.4.2; RC_TAG=v1.4.2-rc.1; BASE_TAG=v1.4.1\n'
  awk '/^wait_ci_green\(\) \{$/,/^\}$/' "$_cut"
  printf 'wait_ci_green 0123456789abcdef0123456789abcdef01234567\n'; } > "$SCRATCH/v.sh"
if PATH="$_v/bin:$PATH" V_VIEW="" bash "$SCRATCH/v.sh" > "$SCRATCH/v1.log" 2>&1; then
  bad "V1: gh run view vazio passou"
elif grep -q 'FAIL: gh run view 4242 falhou' "$SCRATCH/v1.log" && ! grep -q 'Traceback' "$SCRATCH/v1.log"; then
  ok "V1 (controle vermelho): gh run view que falha vira FAIL nomeado, sem traceback"
else bad "V1: falha sem nome"; sed -n '1,8p' "$SCRATCH/v1.log"; fi
if PATH="$_v/bin:$PATH" V_VIEW="oops" bash "$SCRATCH/v.sh" > "$SCRATCH/v2.log" 2>&1; then
  bad "V2: resposta ilegivel do gh run view passou"
elif grep -q 'FAIL: resposta do gh run view 4242 ilegivel' "$SCRATCH/v2.log"; then
  ok "V2 (controle vermelho): resposta ilegivel do gh run view vira FAIL nomeado"
else bad "V2: falha sem nome"; sed -n '1,8p' "$SCRATCH/v2.log"; fi
if PATH="$_v/bin:$PATH" V_VIEW='{"s": 3, "f": 0, "p": 0, "o": 0}' bash "$SCRATCH/v.sh" > "$SCRATCH/v3.log" 2>&1 \
   && grep -q 'validate.yml: 3 job(s) success' "$SCRATCH/v3.log"; then
  ok "V3: resposta boa do gh run view passa"
else bad "V3: o caso bom foi recusado"; sed -n '1,8p' "$SCRATCH/v3.log"; fi

# ===========================================================================
say "Z. passo 5: os passos 1, 2 e 4 conferiram ESTE candidato; CANDIDATE.sha byte a byte"
# O passo 5 VERBATIM (a sonda das condicoes e o congelamento neutralizados: eles tem as
# secoes P e FZ) num clone com remoto bare local. No GA o bump e no-op: o caso bom tem
# SHA-1 = SHA-2P = SHA-2 = SHA-4 = o candidato.
_z="$SCRATCH/z"
if git init --quiet --bare "$_z/origin.git" 2>/dev/null \
   && git init --quiet "$_z/w" 2>/dev/null && fixture_git_identity "$_z/w" \
   && ( cd "$_z/w" && printf 'a\n' > a && git add a && git commit -q -m a ) \
   && git -C "$_z/w" remote add origin "$_z/origin.git" \
   && git -C "$_z/w" push -q origin HEAD:refs/heads/main 2>/dev/null; then
  _zc="$(git -C "$_z/w" rev-parse HEAD)"; _zo=fedcba9876543210fedcba9876543210fedcba98; mkdir -p "$_z/w/ev"
  { printf '#!/bin/bash\nset -euo pipefail\n'
    printf 'say() { :; }; mark_step() { :; }; assert_conditions_probe() { :; }; assert_rc_tree_frozen() { :; }\n'
    printf 'die() { printf "FAIL: %%s\\n" "$*" >&2; exit 1; }\n'
    printf 'EV=ev; STATE=ev/.cut-state; CAND=%s\n' "$_zc"
    awk '/^state_sha\(\) \{$/,/^\}$/' "$_cut"
    awk '/^assert_steps_saw_cand\(\) \{$/,/^\}$/' "$_cut"
    awk '/^if should 5; then$/{f=1; next} /^  mark_step 5$/{f=0} f' "$_cut"; } > "$SCRATCH/z.sh"
  _z_state() {  # $1 SHA-1, $2 SHA-2P, $3 SHA-2, $4 SHA-4 ("-" = linha ausente)
    : > "$_z/w/ev/.cut-state"
    printf 'STEP-1\n' >> "$_z/w/ev/.cut-state"; [ "$1" = "-" ] || printf 'SHA-1 %s\n' "$1" >> "$_z/w/ev/.cut-state"
    printf 'STEP-2\n' >> "$_z/w/ev/.cut-state"; [ "$2" = "-" ] || printf 'SHA-2P %s\n' "$2" >> "$_z/w/ev/.cut-state"
    [ "$3" = "-" ] || printf 'SHA-2 %s\n' "$3" >> "$_z/w/ev/.cut-state"
    printf 'STEP-4\n' >> "$_z/w/ev/.cut-state"; [ "$4" = "-" ] || printf 'SHA-4 %s\n' "$4" >> "$_z/w/ev/.cut-state"
  }
  _z_state "$_zc" "$_zc" "$_zc" "$_zc"
  printf '%s' "$_zc" > "$_z/w/ev/CANDIDATE.sha"
  _z0="$(shasum -a 256 "$_z/w/ev/CANDIDATE.sha" | awk '{print $1}')"
  if ( cd "$_z/w" && bash "$SCRATCH/z.sh" ) > "$SCRATCH/z1.log" 2>&1 \
     && grep -q 'mantido byte a byte' "$SCRATCH/z1.log" \
     && [ "$(shasum -a 256 "$_z/w/ev/CANDIDATE.sha" | awk '{print $1}')" = "$_z0" ] \
     && grep -q 'OK: os passos 1, 2 e 4 conferiram o candidato' "$SCRATCH/z1.log"; then
    ok "Z1: o preflight, o bump NO-OP e o CI conferiram o candidato; CANDIDATE.sha mantido byte a byte"
  else bad "Z1: o caso bom falhou"; sed -n '1,6p' "$SCRATCH/z1.log"; fi
  printf '%s\n' "$_zo" > "$_z/w/ev/CANDIDATE.sha"
  if ( cd "$_z/w" && bash "$SCRATCH/z.sh" ) > "$SCRATCH/z2.log" 2>&1 \
     && [ "$(cat "$_z/w/ev/CANDIDATE.sha")" = "$_zc" ]; then
    ok "Z2: CANDIDATE.sha de OUTRO commit e reescrito com o candidato"
  else bad "Z2: CANDIDATE.sha de outro commit nao foi reescrito"; sed -n '1,6p' "$SCRATCH/z2.log"; fi
  _z_state "$_zo" "$_zo" "$_zc" "$_zo"
  if ( cd "$_z/w" && bash "$SCRATCH/z.sh" ) > "$SCRATCH/z3.log" 2>&1; then bad "Z3: passo 4 sobre OUTRO commit passou"
  elif grep -q "passo 4: conferiu $_zo (linhas STEP-4 e SHA-4)" "$SCRATCH/z3.log"; then
    ok "Z3 (controle vermelho): o passo 4 que conferiu OUTRO commit e recusado, com as linhas a tirar"
  else bad "Z3: recusa sem o motivo"; sed -n '1,8p' "$SCRATCH/z3.log"; fi
  _z_state "$_zo" "$_zo" "$_zo" "$_zc"
  if ( cd "$_z/w" && bash "$SCRATCH/z.sh" ) > "$SCRATCH/z3b.log" 2>&1; then bad "Z3b: bump terminado em OUTRO commit passou"
  elif grep -q "passo 2: terminou em $_zo" "$SCRATCH/z3b.log"; then
    ok "Z3b (controle vermelho): o bump que terminou em OUTRO commit e recusado"
  else bad "Z3b: recusa sem o motivo"; sed -n '1,8p' "$SCRATCH/z3b.log"; fi
  _z_state "$_zc" "$_zo" "$_zc" "$_zc"
  if ( cd "$_z/w" && bash "$SCRATCH/z.sh" ) > "$SCRATCH/z3c.log" 2>&1; then bad "Z3c: preflight de OUTRO commit passou"
  elif grep -q "passo 1: conferiu $_zc, e o bump partiu de $_zo" "$SCRATCH/z3c.log"; then
    ok "Z3c (controle vermelho): o preflight que conferiu um commit diferente daquele de onde o bump partiu e recusado"
  else bad "Z3c: recusa sem o motivo"; sed -n '1,8p' "$SCRATCH/z3c.log"; fi
  _z_state - - - -
  if ( cd "$_z/w" && bash "$SCRATCH/z.sh" ) > "$SCRATCH/z4.log" 2>&1 \
     && grep -q 'nao registra o commit que o passo 4 conferiu' "$SCRATCH/z4.log"; then
    ok "Z4: sem os registros (passos feitos a mao), AVISO nomeado e o passo 5 segue"
  else bad "Z4: o passo 5 sem registro nao avisou (ou recusou)"; sed -n '1,8p' "$SCRATCH/z4.log"; fi
else bad "Z: fixture do passo 5 falhou"; fi

# ===========================================================================
say "X. passo 17: conclusao terminal diferente de success e recusa na hora (nunca 120 min)"
_x="$SCRATCH/x"; mkdir -p "$_x/bin"
cat > "$_x/bin/gh" <<'GHXEOF'
#!/bin/bash
n="$(cat "$X_CNT" 2>/dev/null || echo 0)"; n=$((n+1)); printf '%s' "$n" > "$X_CNT"
printf '%s\n' "$X_SEQ" | sed -n "${n}p"
GHXEOF
chmod 0755 "$_x/bin/gh"
if git init --quiet "$_x/w" 2>/dev/null && fixture_git_identity "$_x/w" \
   && ( cd "$_x/w" && git commit -q --allow-empty -m a && git -c tag.gpgSign=false tag -a -m t v1.4.2 ); then
  { printf '#!/bin/bash\nset -euo pipefail\n'
    printf 'die() { printf "FAIL: %%s\\n" "$*" >&2; exit 1; }\n'
    printf 'say() { :; }; bell() { :; }; sleep() { :; }; should() { return 0; }\n'
    printf 'mark_step() { printf "X-STEP-%%s-MARCADO\\n" "$1"; }\n'
    printf 'verdict_deadline() { printf "PRAZO-STUB"; }\n'
    printf 'TAG=v1.4.2\n'
    awk '/^if should 17; then$/,/^fi$/' "$_cut"; } > "$SCRATCH/x.sh"
  _x_run() {  # $1 = sequencia (uma linha por chamada do gh), $2 = log
    rm -f -- "$_x/cnt"
    ( cd "$_x/w" && PATH="$_x/bin:$PATH" X_CNT="$_x/cnt" X_SEQ="$1" bash "$SCRATCH/x.sh" ) > "$2" 2>&1
  }
  for _xc in cancelled timed_out startup_failure failure; do
    if _x_run "completed|$_xc|4242" "$SCRATCH/x-$_xc.log"; then bad "X: release.yml '$_xc' passou pelo passo 17"
    elif grep -q "release.yml terminou '$_xc' para a tag v1.4.2 (run 4242)" "$SCRATCH/x-$_xc.log" \
         && grep -q 'retoma do passo 17' "$SCRATCH/x-$_xc.log" && [ "$(cat "$_x/cnt")" = "1" ] \
         && grep -q 'gh run rerun <run dele> --failed' "$SCRATCH/x-$_xc.log" \
         && grep -q 'rerun so ate PRAZO-STUB' "$SCRATCH/x-$_xc.log"; then
      ok "X (controle vermelho): release.yml '$_xc' e recusa nomeada na 1.a volta, com o run, a rota (npm-publish incluido) e o prazo"
    else bad "X: '$_xc' sem recusa nomeada imediata"; sed -n '1,6p' "$SCRATCH/x-$_xc.log"; fi
  done
  if _x_run "$(printf 'in_progress||4242\nqueued||4242\ncompleted|success|4242')" "$SCRATCH/x-ok.log" \
     && grep -q 'X-STEP-17-MARCADO' "$SCRATCH/x-ok.log" \
     && grep -q 'release.yml: in_progress/?' "$SCRATCH/x-ok.log"; then
    ok "X: em andamento (conclusao vazia nao desloca os campos) e depois success marca o passo 17"
  else bad "X: o caminho verde do passo 17 falhou"; sed -n '1,8p' "$SCRATCH/x-ok.log"; fi
else bad "X: fixture do passo 17 falhou"; fi

# ===========================================================================
say "Q. passo 19: o piso do publishedAt nunca e 0 (sem .tag-push-epoch, a data da tag)"
_q="$SCRATCH/q"
if git init --quiet "$_q" 2>/dev/null && fixture_git_identity "$_q" \
   && ( cd "$_q" && git commit -q --allow-empty -m a && git -c tag.gpgSign=false tag -a -m t v1.4.2 && mkdir -p ev ); then
  { printf '#!/bin/bash\nset -euo pipefail\n'
    printf 'die() { printf "FAIL: %%s\\n" "$*" >&2; exit 1; }\n'
    printf 'EV=ev; TAG="${Q_TAG:-v1.4.2}"; _pe="$Q_PE"; _pub=Q-PUB\n'
    awk '/^  # O piso e o epoch que o passo 16 grava/{f=1} /^  mark_step 19$/{f=0} f' "$_cut"
    printf 'printf "Q-OK\\n"\n'; } > "$SCRATCH/q.sh"
  _qt="$(git -C "$_q" for-each-ref --format='%(taggerdate:unix)' refs/tags/v1.4.2)"
  rm -f -- "$_q/ev/.tag-push-epoch"
  if ( cd "$_q" && Q_PE="$((_qt + 60))" bash "$SCRATCH/q.sh" ) > "$SCRATCH/q1.log" 2>&1 \
     && grep -q 'Q-OK' "$SCRATCH/q1.log" && grep -q 'o piso e a data do objeto da tag' "$SCRATCH/q1.log"; then
    ok "Q1: sem .tag-push-epoch, o piso e a data da tag, e um publishedAt depois dela passa"
  else bad "Q1: o caso bom sem o arquivo falhou"; sed -n '1,6p' "$SCRATCH/q1.log"; fi
  if ( cd "$_q" && Q_PE="$((_qt - 3600))" bash "$SCRATCH/q.sh" ) > "$SCRATCH/q2.log" 2>&1; then
    bad "Q2: sem .tag-push-epoch, um publishedAt 1 h ANTES da tag passou (piso 0)"
  elif grep -q 'ANTERIOR a esta cerimonia' "$SCRATCH/q2.log"; then
    ok "Q2 (controle vermelho): sem .tag-push-epoch, publishedAt anterior a tag e recusado (o piso nao e 0)"
  else bad "Q2: recusa sem o motivo"; sed -n '1,6p' "$SCRATCH/q2.log"; fi
  printf '%s\n' "$((_qt + 7200))" > "$_q/ev/.tag-push-epoch"
  if ( cd "$_q" && Q_PE="$((_qt + 60))" bash "$SCRATCH/q.sh" ) > "$SCRATCH/q3.log" 2>&1; then
    bad "Q3: publishedAt anterior ao epoch gravado passou"
  elif grep -q 'ANTERIOR a esta cerimonia' "$SCRATCH/q3.log"; then
    ok "Q3 (controle vermelho): com .tag-push-epoch, o piso e o epoch gravado pelo passo 16"
  else bad "Q3: recusa sem o motivo"; sed -n '1,6p' "$SCRATCH/q3.log"; fi
  rm -f -- "$_q/ev/.tag-push-epoch"
  if ( cd "$_q" && Q_PE="$((_qt + 60))" Q_TAG=v9.9.9 bash "$SCRATCH/q.sh" ) > "$SCRATCH/q4.log" 2>&1; then
    bad "Q4: sem .tag-push-epoch e sem tag local, passou"
  elif grep -q 'sem .tag-push-epoch e sem a data da tag local' "$SCRATCH/q4.log"; then
    ok "Q4 (controle vermelho): sem .tag-push-epoch e sem a tag local, recusa nomeada"
  else bad "Q4: recusa sem o motivo"; sed -n '1,6p' "$SCRATCH/q4.log"; fi
else bad "Q: fixture do passo 19 falhou"; fi

# ===========================================================================
say "Y. passo 19: a tag na cadeia first-parent de origin/main (push alheio x rollback)"
_y="$SCRATCH/y"
if git init --quiet --bare "$_y/origin.git" 2>/dev/null \
   && git init --quiet "$_y/w" 2>/dev/null && fixture_git_identity "$_y/w" \
   && ( cd "$_y/w" && printf 'a\n' > a && git add a && git commit -q -m a \
        && printf 'b\n' > b && git add b && git commit -q -m b \
        && git -c tag.gpgSign=false tag -a -m "TEST ONLY" v1.4.2 ) \
   && git -C "$_y/w" remote add origin "$_y/origin.git" \
   && git -C "$_y/w" push -q origin HEAD:refs/heads/main 2>/dev/null; then
  { printf '#!/bin/bash\nset -euo pipefail\n'
    printf 'die() { printf "FAIL: %%s\\n" "$*" >&2; exit 1; }\n'
    printf 'TAG=v1.4.2\n'
    awk '/^  # main nao pode ter sido REVERTIDO/{f=1} f{print} f && /^  fi$/{exit}' "$_cut"
    printf 'printf "Y-OK\\n"\n'; } > "$SCRATCH/y.sh"
  if ( cd "$_y/w" && bash "$SCRATCH/y.sh" ) > "$SCRATCH/y1.log" 2>&1 && grep -q 'Y-OK' "$SCRATCH/y1.log" \
     && ! grep -q 'AVISO' "$SCRATCH/y1.log"; then ok "Y1: origin/main == commit da tag passa"
  else bad "Y1: o caso igual foi recusado"; sed -n '1,6p' "$SCRATCH/y1.log"; fi
  if ( cd "$_y/w" && printf 'c\n' > c && git add c && git commit -q -m c ) \
     && git -C "$_y/w" push -q origin HEAD:refs/heads/main 2>/dev/null \
     && git -C "$_y/w" checkout -q --detach v1.4.2 2>/dev/null; then
    if ( cd "$_y/w" && bash "$SCRATCH/y.sh" ) > "$SCRATCH/y2.log" 2>&1 && grep -q 'Y-OK' "$SCRATCH/y2.log" \
       && grep -q 'AVISO: main andou depois da tag (1 commit' "$SCRATCH/y2.log"; then
      ok "Y2: push alheio DEPOIS da tag passa com AVISO (a tag segue na cadeia first-parent)"
    else bad "Y2: push alheio depois da tag foi recusado"; sed -n '1,6p' "$SCRATCH/y2.log"; fi
  else bad "Y2: preparacao do push alheio falhou"; fi
  if git -C "$_y/w" push -q -f origin "v1.4.2^{commit}^:refs/heads/main" 2>/dev/null; then
    if ( cd "$_y/w" && bash "$SCRATCH/y.sh" ) > "$SCRATCH/y3.log" 2>&1; then bad "Y3: main revertido para antes da tag passou"
    elif grep -q 'NAO esta na cadeia first-parent' "$SCRATCH/y3.log"; then
      ok "Y3 (controle vermelho): main revertido para antes da tag e recusado"
    else bad "Y3: recusa sem o motivo"; sed -n '1,6p' "$SCRATCH/y3.log"; fi
  else bad "Y3: nao consegui reverter o main da fixture"; fi
else bad "Y: fixture do passo 19 falhou"; fi

# ===========================================================================
say "L. G0: CLAUDE.md abaixo do limite do validate-governance.sh (assert_claude_md_fits)"
if grep -qF 'CLAUDE_MD_LIMIT="${CLAUDE_MD_SIZE_LIMIT:-40000}"' "$ROOT/.claude/scripts/validate-governance.sh" \
   && grep -qF '[ "$CLAUDE_MD_BYTES" -ge "$CLAUDE_MD_LIMIT" ]' "$ROOT/.claude/scripts/validate-governance.sh"; then
  ok "L0: o gate do validate-governance.sh e o que o G0 espelha (reprova a partir de 40000, CLAUDE_MD_SIZE_LIMIT)"
else bad "L0: o gate do validate-governance.sh mudou — o G0 espelha outra regra"; fi
_l="$SCRATCH/l"; mkdir -p "$_l"
{ printf '#!/bin/bash\nset -euo pipefail\n'
  printf 'die() { printf "FAIL: %%s\\n" "$*" >&2; exit 1; }\n'
  awk '/^assert_claude_md_fits\(\) \{$/,/^\}$/' "$_cut"
  printf 'assert_claude_md_fits\n'; } > "$SCRATCH/l.sh"
_l_mk() {  # $1 = bytes
  python3 - "$_l/CLAUDE.md" "$1" <<'PYL'
import sys
with open(sys.argv[1], "wb") as fh:
    fh.write(b"x" * int(sys.argv[2]))
PYL
}
_l_mk 39999
if ( cd "$_l" && env -u CLAUDE_MD_SIZE_LIMIT bash "$SCRATCH/l.sh" ) > "$SCRATCH/l1.log" 2>&1 \
   && grep -q 'OK: CLAUDE.md com 39999 bytes' "$SCRATCH/l1.log"; then
  ok "L1: CLAUDE.md com 39999 bytes passa"
else bad "L1: 39999 bytes foi recusado"; sed -n '1,4p' "$SCRATCH/l1.log"; fi
_l_mk 40000
if ( cd "$_l" && env -u CLAUDE_MD_SIZE_LIMIT bash "$SCRATCH/l.sh" ) > "$SCRATCH/l2.log" 2>&1; then
  bad "L2: CLAUDE.md com 40000 bytes passou"
elif grep -q 'CLAUDE.md tem 40000 bytes' "$SCRATCH/l2.log"; then
  ok "L2 (controle vermelho): CLAUDE.md com 40000 bytes e recusado pelo nome no G0, antes do preflight"
else bad "L2: recusa sem o motivo"; sed -n '1,4p' "$SCRATCH/l2.log"; fi

# ===========================================================================
say "SC. G0: o Scope ASSINADO da tag cobre a faixa (assert_release_scope_covers_log)"
_p="$SCRATCH/sc"
if git init --quiet "$_p" 2>/dev/null && fixture_git_identity "$_p" \
   && ( cd "$_p" && printf 'RELEASE_SCOPE="PLAN-190 / PLAN-193 (ADRs tocados: nenhum)"\n' > rel.sh \
        && git add rel.sh && git commit -q -m base && git tag v1.4.1 \
        && git commit -q --allow-empty -m "plan(PLAN-193): kit" \
        && git commit -q --allow-empty -m "plan(PLAN-190): nota" && git branch p-ok \
        && git commit -q --allow-empty -m "plan(PLAN-194): plano novo" && git branch p-plan \
        && git checkout -q --detach p-ok && mkdir -p .claude/adr \
        && printf 'a\n' > .claude/adr/ADR-200-x.md && git add .claude/adr/ADR-200-x.md \
        && git commit -q -m "plan(PLAN-193): adr" && git branch p-adr ); then
  { printf '#!/bin/bash\nset -euo pipefail\n'
    printf 'die() { printf "FAIL: %%s\\n" "$*" >&2; exit 1; }\n'
    printf 'RELEASE=rel.sh; BASE_TAG=v1.4.1; PREV_TAG=v1.4.1\n'
    awk '/^assert_release_scope_covers_log\(\) \{$/,/^\}$/' "$_cut"
    printf 'assert_release_scope_covers_log\n'; } > "$SCRATCH/sc.sh"
  _p_run() {  # $1 = branch, $2 = log
    git -C "$_p" checkout -q --detach "$1" 2>/dev/null || return 90
    ( cd "$_p" && bash "$SCRATCH/sc.sh" ) > "$2" 2>&1
  }
  if _p_run p-ok "$SCRATCH/sc1.log" && grep -q 'OK: o Scope assinado da tag cobre' "$SCRATCH/sc1.log"; then
    ok "SC1: commits que citam so planos do RELEASE_SCOPE passam"
  else bad "SC1: o caso bom foi recusado"; sed -n '1,6p' "$SCRATCH/sc1.log"; fi
  if _p_run p-plan "$SCRATCH/sc2.log"; then bad "SC2: commit que cita plano NOVO passou"
  elif grep -q 'nao lista: PLAN-194$' "$SCRATCH/sc2.log"; then
    ok "SC2 (controle vermelho): commit que cita plano fora do RELEASE_SCOPE e recusado pelo nome"
  else bad "SC2: recusa sem nomear o plano"; sed -n '1,6p' "$SCRATCH/sc2.log"; fi
  if _p_run p-adr "$SCRATCH/sc3.log"; then bad "SC3: ADR tocado fora do RELEASE_SCOPE passou"
  elif grep -q 'nao lista: ADR-200$' "$SCRATCH/sc3.log"; then
    ok "SC3 (controle vermelho): ADR tocado na faixa, fora do RELEASE_SCOPE, e recusado pelo nome"
  else bad "SC3: recusa sem nomear o ADR"; sed -n '1,6p' "$SCRATCH/sc3.log"; fi
else bad "SC: fixture do Scope falhou"; fi

# ===========================================================================
say "R. o OWNER-GA-CUT.sh REAL (script inteiro) num clone com remoto bare local"
# O script inteiro roda contra a tag base da fixture (a v1.4.1 assinada pela chave
# descartavel, aceita pelo seam de auto-teste) e contra a tag REAL da v1.4.2-rc.1 (o objeto
# assinado pelo Owner: a chave PUBLICA de .claude/trust/owner.asc e importada no homedir
# DESCARTAVEL da secao K0 — nunca o chaveiro real), com `gh`, `npm`, `sleep` e `osascript`
# STUB e um remoto bare local. `--g0-only` roda so as pre-condicoes; os estados de retomada
# sao plantados no .cut-state da fixture; os passos 17-20 rodam DE VERDADE contra os stubs
# (secoes PUB e GE). O `gh` stub guarda o Release do GA num diretorio de estado e registra
# cada chamada, em ordem; o `npm` stub so conhece `npm view`. Nada sai para a rede.
# Pseudo-terminal (secao T): `script` aloca o pty; o alimentador manda uma linha
# ($_PTY_LINE; vazia = Enter) a cada segundo ate o comando sair. O rc e o do comando.
_pty_feed() { local i=0; while [ "$i" -lt 900 ]; do sleep 1; printf '%s\n' "${_PTY_LINE:-}" 2>/dev/null || return 0; i=$((i+1)); done; }
_pty() {  # $1 = log; $2.. = comando
  local _log="$1" _prc=0 _sv; shift
  _sv="$(script --version 2>&1)" || _sv=""
  case "$_sv" in
    *util-linux*)
      _pty_feed | script -q -e -c "$(printf '%q ' "$@")" "$_log" > /dev/null 2>&1; _prc="${PIPESTATUS[1]}" ;;
    *)
      _pty_feed | script -q "$_log" "$@" > /dev/null 2>&1; _prc="${PIPESTATUS[1]}" ;;
  esac
  return "$_prc"
}
if [ -n "${CLONE:-}" ] && [ -n "$FPR" ] && [ -n "$BASE_REV" ]; then
  _r="$SCRATCH/r"; mkdir -p "$_r/bin" "$_r/tmp" "$_r/gh" "$SCRATCH/rhome"
  # R0 — a tag REAL da rc.1 verifica no homedir DESCARTAVEL com a chave publica do Owner
  # (o assert_rc_hold roda `git tag -v`). A importacao pode reclamar do agente (caminho
  # longo) e ainda assim importar: quem decide e o `git tag -v`.
  GNUPGHOME="$GH" gpg --batch --quiet --import "$ROOT/.claude/trust/owner.asc" >/dev/null 2>&1 || :
  if GNUPGHOME="$GH" git -C "$ROOT" tag -v v1.4.2-rc.1 >/dev/null 2>&1; then
    ok "R0: a tag REAL v1.4.2-rc.1 verifica no homedir descartavel (chave publica do owner.asc)"
  else bad "R0: a tag v1.4.2-rc.1 nao verifica com a chave publica do owner.asc no homedir descartavel"; fi
  cat > "$_r/bin/gh" <<'GHREOF'
#!/bin/bash
# gh STUB do ensaio R/PUB/GE: devolve o valor FINAL que o CUT extrairia com --jq (o jq
# real nao roda). O Release do GA vive em $R_GH/ (ga-release, ga-draft, ga-pre,
# ga-pubat); cada chamada fica, em ordem, em $R_GH/calls.log.
S="${R_GH:?}"
printf 'gh %s\n' "$*" >> "$S/calls.log"
_jq=""; _prev=""
for _a in "$@"; do [ "$_prev" = "--jq" ] && _jq="$_a"; _prev="$_a"; done
_cnt() { local n; n="$(cat "$S/$1" 2>/dev/null || echo 0)"; n=$((n+1)); printf '%s' "$n" > "$S/$1"; printf '%s' "$n"; }
_reset() { echo 'Patch "https://api.github.com/repos/o/r/releases/1": read tcp 10.0.0.2:50000->140.82.112.6:443: read: connection reset by peer' >&2; exit 1; }
case "$1 $2" in
  "release view")
    if [ "$3" = "v1.4.2-rc.1" ]; then
      printf '{"isPrerelease": true, "isDraft": false, "publishedAt": "%s"}\n' "$R_PUBAT"; exit 0
    fi
    # R_VIEW_MODE=transport: a leitura do Release do GA falha por TRANSPORTE (nem estado,
    # nem «release not found»).
    if [ "$3" = "v1.4.2" ] && [ "${R_VIEW_MODE:-ok}" = "transport" ]; then
      printf 'error connecting to api.github.com\ncheck your internet connection or https://githubstatus.com\n' >&2; exit 1
    fi
    if [ "$3" != "v1.4.2" ] || [ ! -f "$S/ga-release" ]; then echo "release not found" >&2; exit 1; fi
    _d="$(cat "$S/ga-draft")"; _p="$(cat "$S/ga-pre")"; _pa=""
    if [ -f "$S/ga-pubat" ]; then _pa="$(cat "$S/ga-pubat")"; fi
    case "$_jq" in
      "") if [ -n "$_pa" ]; then _pa="\"$_pa\""; else _pa=null; fi
          printf '{"isDraft": %s, "isPrerelease": %s, "publishedAt": %s, "url": "https://example.invalid/releases/v1.4.2"}\n' "$_d" "$_p" "$_pa" ;;
      .isDraft) printf '%s\n' "$_d" ;;
      .isPrerelease) printf '%s\n' "$_p" ;;
      .url) echo "https://example.invalid/releases/v1.4.2" ;;
      *) echo "gh stub: --jq nao previsto em release view: $_jq" >&2; exit 9 ;;
    esac ;;
  "release edit")
    _want=""
    for _a in "$@"; do
      case "$_a" in --draft|--draft=true) _want=true ;; --draft=false) _want=false ;; esac
    done
    { [ "$3" = "v1.4.2" ] && [ -n "$_want" ]; } || { echo "gh stub: release edit nao previsto: $*" >&2; exit 9; }
    _n="$(_cnt edit-count)"
    # Um laco SEM teto seria infinito com o sleep stub: passado o limite, o stub o corta.
    if [ "$_n" -gt 40 ]; then : > "$S/runaway"; echo "release not found" >&2; exit 1; fi
    case "${R_EDIT_MODE:-ok}" in
      notfound) echo "release not found" >&2; exit 1 ;;
      reset-never) _reset ;;
      # other: um erro da API que NAO e transporte nem ausencia (nada muda no servidor).
      other) echo 'HTTP 422: Validation Failed (https://api.github.com/repos/o/r/releases/1)' >&2; exit 1 ;;
    esac
    [ -f "$S/ga-release" ] || { echo "release not found" >&2; exit 1; }
    printf '%s' "$_want" > "$S/ga-draft"
    if [ "$_want" = "false" ]; then date -u +%Y-%m-%dT%H:%M:%SZ > "$S/ga-pubat"; fi
    # reset-after: o PATCH CHEGOU (o estado mudou) e a resposta se perdeu.
    if [ "${R_EDIT_MODE:-ok}" = "reset-after" ] && [ "$_n" = "1" ]; then _reset; fi
    printf 'https://example.invalid/releases/v1.4.2\n' ;;
  "run list")
    case "$*" in
      *release.yml*) printf '%s\n' "${R_R17:-completed|success|4242}" ;;
      *npm-publish.yml*)
        case "$_jq" in
          *'"v1.4.2-rc.1"'*) echo 4141 ;;
          *'"v1.4.2"'*) echo 4343 ;;
          *) echo "gh stub: run list do npm-publish sem tag conhecida" >&2; exit 9 ;;
        esac ;;
      *) echo "gh stub: run list nao previsto: $*" >&2; exit 9 ;;
    esac ;;
  "run view")
    case "$_jq" in
      *'Await release-gate'*)
        # O gate do npm-publish da rc (o controle positivo do hold) e success; o do GA e o
        # que R_NPM_AWAIT pedir (failure = o run anterior a um rerun do release.yml).
        if [ "$3" = "4343" ]; then echo "${R_NPM_AWAIT:-success}"; else echo success; fi ;;
      *'Publish (Trusted Publishing'*)
        # O recibo do step de publish: R_NPM_RECEIPT = success (padrao) | skipped |
        # failure | null (o step nao achado) | error (a LEITURA falha: transporte).
        case "${R_NPM_RECEIPT:-success}" in
          error) echo "error connecting to api.github.com" >&2; exit 1 ;;
          *) echo "${R_NPM_RECEIPT:-success}" ;;
        esac ;;
      .url) echo "https://example.invalid/actions/runs/$3" ;;
      "")
        # O run do npm-publish: 1.a leitura = esperando a aprovacao do ambiente; depois o
        # desfecho pedido. Success publica (o registry passa a ter a 1.4.2), salvo
        # R_NPM_NEVER=1 (o registry nunca confirma).
        _v="$(_cnt runview-count)"
        if [ "$_v" = "1" ]; then printf '{"status": "waiting", "conclusion": ""}\n'
        else
          if [ "${R_NPM_RUN:-success}" = "success" ] && [ "${R_NPM_NEVER:-0}" != "1" ]; then : > "$S/npm-published"; fi
          printf '{"status": "completed", "conclusion": "%s"}\n' "${R_NPM_RUN:-success}"
        fi ;;
      *) echo "gh stub: run view nao previsto: $*" >&2; exit 9 ;;
    esac ;;
  "repo view") echo "owner/repo" ;;
  *) echo "gh stub: chamada inesperada: $*" >&2; exit 9 ;;
esac
GHREOF
  cat > "$_r/bin/npm" <<'NPMREOF'
#!/bin/bash
# npm STUB: so `npm view`. <pacote>@1.4.2 existe depois do publish do stub do gh;
# o `latest` e 1.4.1 ate la e depois SEGUE a 1.4.2, salvo R_NPM_LATEST (o dist-tag
# independente: a 1.4.2 publicada com o latest ainda em outra versao). Qualquer outra
# chamada (publish incluido) e recusada.
S="${R_GH:?}"
if [ "$1" != "view" ]; then
  printf 'npm %s => RECUSADO\n' "$*" >> "$S/calls.log"; echo "npm stub: so npm view: $*" >&2; exit 9
fi
_v=""; [ -f "$S/npm-published" ] && _v=1.4.2
_lat="${R_NPM_LATEST:-${_v:-1.4.1}}"
case "$2" in
  *@1.4.2)
    if [ -n "$_v" ]; then printf 'npm %s => 1.4.2\n' "$*" >> "$S/calls.log"; echo 1.4.2
    else printf 'npm %s => E404\n' "$*" >> "$S/calls.log"; echo "npm error code E404" >&2; exit 1; fi ;;
  *) printf 'npm %s => %s\n' "$*" "$_lat" >> "$S/calls.log"; echo "$_lat" ;;
esac
NPMREOF
  printf '#!/bin/bash\nexit 0\n' > "$_r/bin/osascript"
  printf '#!/bin/bash\nexit 0\n' > "$_r/bin/sleep"
  chmod 0755 "$_r/bin/gh" "$_r/bin/npm" "$_r/bin/osascript" "$_r/bin/sleep"
  _r_pub() {  # $1 = horas atras -> ISO-8601 UTC
    python3 - "$1" <<'PYR'
import sys, datetime
t = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=float(sys.argv[1]))
print(t.strftime("%Y-%m-%dT%H:%M:%SZ"))
PYR
  }
  # O estado do `gh` stub: $1 = o Release do GA existe (0|1), $2 = isDraft, $3 = isPrerelease.
  _r_gh() {
    local _f
    for _f in calls.log ga-release ga-draft ga-pre ga-pubat edit-count runview-count npm-published runaway; do
      rm -f -- "$_r/gh/$_f"
    done
    : > "$_r/gh/calls.log"
    if [ "$1" = "1" ]; then
      : > "$_r/gh/ga-release"; printf '%s' "$2" > "$_r/gh/ga-draft"; printf '%s' "$3" > "$_r/gh/ga-pre"
    fi
  }
  # A 1.a linha do registro de chamadas que casa a ERE $1 (vazio se nenhuma).
  _r_line() { awk -v re="$1" '$0 ~ re { print NR; exit }' "$_r/gh/calls.log"; }
  _r_gh 0 true false
  R_PUBAT_H=30; R_EDIT_MODE=ok; R_NPM_RUN=success; R_NPM_NEVER=0; R_NPM_AWAIT=success
  R_NPM_RECEIPT=success; R_NPM_LATEST=""; R_VIEW_MODE=ok
  _r_cut() {  # $1 = log, $2.. = argumentos do CUT
    local _log="$1"; shift
    # shellcheck disable=SC2086
    ( cd "$_r/wt" && env PATH="$_r/bin:$PATH" GNUPGHOME="$GH" HOME="$SCRATCH/rhome" \
        TMPDIR="$_r/tmp" R_GH="$_r/gh" R_PUBAT="$(_r_pub "$R_PUBAT_H")" R_EDIT_MODE="$R_EDIT_MODE" \
        R_VIEW_MODE="$R_VIEW_MODE" \
        R_NPM_RUN="$R_NPM_RUN" R_NPM_NEVER="$R_NPM_NEVER" R_NPM_AWAIT="$R_NPM_AWAIT" \
        R_NPM_RECEIPT="$R_NPM_RECEIPT" R_NPM_LATEST="$R_NPM_LATEST" \
        $SELFTEST_ENV $PROBE_ENV \
        bash "$PLAN_DIR/OWNER-GA-CUT.sh" "$@" ) < /dev/null > "$_log" 2>&1
  }
  _r_pty() {  # $1 = log, $2.. = argumentos do CUT — o mesmo ambiente, num pty
    local _log="$1" _pub; shift
    _pub="$(_r_pub "$R_PUBAT_H")"
    # shellcheck disable=SC2086
    ( cd "$_r/wt" && _pty "$_log" env PATH="$_r/bin:$PATH" GNUPGHOME="$GH" \
        HOME="$SCRATCH/rhome" TMPDIR="$_r/tmp" R_GH="$_r/gh" R_PUBAT="$_pub" R_EDIT_MODE=ok \
        R_NPM_RUN=success R_NPM_NEVER=0 R_NPM_RECEIPT=success R_NPM_LATEST= $SELFTEST_ENV $PROBE_ENV \
        bash "$PLAN_DIR/OWNER-GA-CUT.sh" "$@" )
  }
  _r_state() {  # $1 = ultimo passo concluido (0 = nenhum)
    local _s=1
    : > "$_r/wt/$EV/.cut-state"
    while [ "$_s" -le "$1" ]; do printf 'STEP-%s\n' "$_s" >> "$_r/wt/$EV/.cut-state"; _s=$((_s+1)); done
  }
  if git clone --quiet --bare "$UPSTREAM" "$_r/origin.git" 2>/dev/null \
     && git clone --quiet "$_r/origin.git" "$_r/wt" 2>/dev/null && fixture_git_identity "$_r/wt"; then
    _r_base="$(git -C "$_r/wt" rev-parse HEAD)"
    _r_restore() {  # main da fixture (local e remoto) de volta ao commit de partida
      git -C "$_r/wt" reset -q --hard "$_r_base" \
        && git -C "$_r/wt" push -q -f origin "$_r_base:refs/heads/main" 2>/dev/null \
        || bad "R: restaurar o main da fixture falhou"
    }
    # R1 — G0 verde: o pre-release da rc.1 publicado ha 30 h (o hold passou).
    _r_cut "$_r/pos.log" --g0-only; _r1rc=$?
    if [ "$_r1rc" -eq 0 ] && grep -q 'OK: kit .*commitado e identico ao HEAD' "$_r/pos.log" \
       && grep -q 'OK: no plano, so a evidencia deste corte esta fora do git' "$_r/pos.log" \
       && grep -q 'OK: base v1.4.1 (tag anotada, assinada por' "$_r/pos.log" \
       && grep -q 'OK: hold ADR-103 da v1.4.2-rc.1 completo' "$_r/pos.log" \
       && grep -q 'OK: desde a v1.4.2-rc.1 so mudaram CLAUDE.md e planos numerados' "$_r/pos.log" \
       && grep -q 'OK: main, HEAD==origin/main, tag v1.4.2 livre' "$_r/pos.log" \
       && grep -q 'OK: o Scope assinado da tag cobre os planos e ADRs de v1.4.1..HEAD' "$_r/pos.log" \
       && grep -q 'OK: CLAUDE.md com [0-9]* bytes' "$_r/pos.log" \
       && grep -q 'FREEZE: do G0 ate o push da tag' "$_r/pos.log" \
       && { grep -q 'OK: sonda das condicoes verde contra' "$_r/pos.log" \
            || { [ -n "$PROBE_ENV" ] && grep -q 'AVISO: sonda rc=1 e GA_PROBE_REPORT_ONLY=1' "$_r/pos.log"; }; } \
       && grep -q 'G0 verde (--g0-only)' "$_r/pos.log"; then
      ok "R1: G0 real verde (kit, plano, base v1.4.1, hold da rc.1 REAL, arvore congelada, Scope, CLAUDE.md, sonda ${PROBE_ENV:+em REPORT-ONLY }e FREEZE)"
    else bad "R1: G0 real recusou o caso bom (rc=$_r1rc)"; sed -n '1,40p' "$_r/pos.log"; fi
    # R2 — a tag base ausente (local) e ausente no REMOTO: recusas nomeadas.
    git -C "$_r/wt" tag -d v1.4.1 >/dev/null 2>&1
    if _r_cut "$_r/r2.log" --g0-only; then bad "R2: G0 real seguiu sem a tag base local"
    elif grep -q 'a tag base v1.4.1 nao existe neste repositorio' "$_r/r2.log" \
         && grep -q 'OWNER-GA-CUT.sh' "$_r/r2.log"; then
      ok "R2 (controle vermelho): tag base ausente e recusa NOMEADA (a rota: o corte do GA v1.4.1 ou buscar a tag)"
    else bad "R2: recusa sem o nome da base"; sed -n '1,8p' "$_r/r2.log"; fi
    git -C "$_r/wt" fetch -q origin tag v1.4.1 2>/dev/null || bad "R2: restaurar a tag base local falhou"
    git -C "$_r/origin.git" tag -d v1.4.1 >/dev/null 2>&1
    if _r_cut "$_r/r2b.log" --g0-only; then bad "R2b: G0 real seguiu com a tag base ausente no remoto"
    elif grep -q 'v1.4.1 ausente no REMOTO' "$_r/r2b.log"; then
      ok "R2b (controle vermelho): tag base ausente no REMOTO e recusa nomeada"
    else bad "R2b: recusa sem o motivo"; sed -n '1,8p' "$_r/r2b.log"; fi
    git -C "$_r/wt" push -q origin refs/tags/v1.4.1 2>/dev/null || bad "R2b: restaurar a tag base remota falhou"
    # R2h — o hold ADR-103 da rc.1 NAO passou (o pre-release publicado ha 1 h): o G0 real
    # recusa pelo nome.
    R_PUBAT_H=1
    if _r_cut "$_r/r2h.log" --g0-only; then bad "R2h: G0 real aceitou 1 h de hold da v1.4.2-rc.1"
    elif grep -q 'hold ADR-103 incompleto' "$_r/r2h.log" && ! grep -q 'G0 verde' "$_r/r2h.log"; then
      ok "R2h (controle vermelho): G0 real recusa o hold da v1.4.2-rc.1 com 1 h (< 24 h)"; _red="$_red R2h"
    else bad "R2h: G0 real recusou sem o motivo do hold"; sed -n '1,10p' "$_r/r2h.log"; fi
    R_PUBAT_H=30
    # R2r — numa corrida FRESCA (o passo 16 nao feito) o GitHub Release do v1.4.2 JA
    # existe: um corte anterior abortado. O G0 real recusa pelo nome; o R1 e o gemeo (o
    # mesmo tudo, sem o Release).
    _r_gh 1 true false
    if _r_cut "$_r/r2r.log" --g0-only; then bad "R2r: G0 real aceitou um Release do v1.4.2 antes do push da tag"
    elif grep -q 'GitHub Release do v1.4.2 JA EXISTE antes do push da tag' "$_r/r2r.log" \
         && ! grep -q 'G0 verde' "$_r/r2r.log"; then
      ok "R2r (controle vermelho): um Release do v1.4.2 que ja existe numa corrida fresca e recusado no G0 real, pelo nome"
    else bad "R2r: recusa sem o motivo do Release"; sed -n '1,8p' "$_r/r2r.log"; fi
    _r_gh 0 true false
    # R2v — numa corrida FRESCA a leitura do Release do GA (`gh release view v1.4.2`)
    # falha por TRANSPORTE: nem «existe» nem «release not found». O G0 real recusa pelo
    # nome (fail-closed: so le, re-rodar), nunca trata a falha como ausencia. O R1 e o
    # gemeo (o mesmo tudo, com o gh respondendo «release not found»).
    R_VIEW_MODE=transport
    if _r_cut "$_r/r2v.log" --g0-only; then bad "R2v: G0 real seguiu com o gh release view do v1.4.2 falhando por transporte"
    elif grep -qF 'gh release view falhou sem ser NOT-FOUND (transporte ou API)' "$_r/r2v.log" \
         && grep -qF 'error connecting to api.github.com' "$_r/r2v.log" \
         && ! grep -q 'G0 verde' "$_r/r2v.log"; then
      ok "R2v (controle vermelho): o gh release view do v1.4.2 que falha por transporte e recusado no G0 real, pelo nome (nunca lido como ausencia)"
    else bad "R2v: o transporte no gh release view do GA nao deu a recusa nomeada"; sed -n '1,10p' "$_r/r2v.log"; fi
    R_VIEW_MODE=ok
    # R3 — argumentos: recusa nomeada ANTES do G0, rc 2 e nunca o banner.
    _r_arg() {  # $1 = rotulo, $2 = motivo esperado, $3.. = argumentos
      local _l="$1" _pat="$2" _rc=0; shift 2
      _r_cut "$_r/arg.log" "$@" || _rc=$?
      if [ "$_rc" -eq 2 ] && grep -qF -- "$_pat" "$_r/arg.log" && ! grep -q 'PUBLICADO' "$_r/arg.log"; then
        ok "R3 (controle vermelho): $_l e recusado (rc 2, sem banner)"
      else bad "R3: $_l nao foi recusado como devia (rc=$_rc)"; sed -n '1,4p' "$_r/arg.log"; fi
    }
    _r_arg "--from abc" "exige um passo de 1 a 20" --from abc
    _r_arg "--from 99" "exige um passo de 1 a 20" --from 99
    _r_arg "--until 0" "exige um passo de 1 a 20" --until 0
    _r_arg "--from sem valor" "--from exige um passo de 1 a 20 (veio: nada)" --from
    _r_arg "--until 5 --from sem valor" "--from exige um passo de 1 a 20 (veio: nada)" --until 5 --from
    _r_arg "--until sem valor" "--until exige um passo de 1 a 20 (veio: nada)" --until
    _r_arg "--from 5 --until 3" "--from 5 depois de --until 3" --from 5 --until 3
    _r_arg "--restamp" "nao existe no corte do GA" --restamp
    # R4 — arquivo NAO rastreado no plano, fora da evidencia.
    printf 'x\n' > "$_r/wt/$PLAN_DIR/stray-leftover.txt"
    if _r_cut "$_r/stray.log" --g0-only; then bad "R4: G0 aceitou untracked no plano fora da evidencia"
    elif grep -q "$PLAN_DIR/stray-leftover.txt" "$_r/stray.log"; then
      ok "R4 (controle vermelho): untracked no plano fora da evidencia e recusado no G0, pelo nome"
    else bad "R4: recusa sem nomear o arquivo"; sed -n '1,6p' "$_r/stray.log"; fi
    rm -f -- "$_r/wt/$PLAN_DIR/stray-leftover.txt"
    # R4c/R4d — numa corrida FRESCA (nenhum passo feito) a arvore limpa do G0
    # (tree_clean_except): um arquivo NAO rastreado na RAIZ do repositorio (fora do plano)
    # e um arquivo RASTREADO modificado e nao commitado sao recusados pelo nome, com a
    # classe de cada um. O R1 e o gemeo (a mesma arvore sem o intruso).
    _r4c="TEST-ONLY-r4c-stray.txt"
    _r_state 0
    printf 'x\n' > "$_r/wt/$_r4c"
    if _r_cut "$_r/r4c.log" --g0-only; then bad "R4c: G0 real aceitou um untracked na raiz numa corrida fresca"
    elif grep -qF 'arvore nao esta limpa:' "$_r/r4c.log" && grep -qF "$_r4c (untracked)" "$_r/r4c.log" \
         && ! grep -q 'G0 verde' "$_r/r4c.log"; then
      ok "R4c (controle vermelho): um untracked na RAIZ (fora do plano), numa corrida fresca, e recusado no G0 real pelo nome, como untracked"
    else bad "R4c: recusa sem o nome/classe do untracked na raiz"; sed -n '1,10p' "$_r/r4c.log"; fi
    rm -f -- "$_r/wt/$_r4c"
    cp -p -- "$_r/wt/SBOM.md" "$_r/r4d-sbom.bak"
    printf 'x' >> "$_r/wt/SBOM.md"
    if _r_cut "$_r/r4d.log" --g0-only; then bad "R4d: G0 real aceitou um arquivo rastreado modificado numa corrida fresca"
    elif grep -qF 'arvore nao esta limpa:' "$_r/r4d.log" && grep -qF 'SBOM.md (RASTREADO, modificado)' "$_r/r4d.log" \
         && ! grep -q 'G0 verde' "$_r/r4d.log"; then
      ok "R4d (controle vermelho): um arquivo RASTREADO modificado e nao commitado, numa corrida fresca, e recusado no G0 real pelo nome, como rastreado modificado"
    else bad "R4d: recusa sem o nome/classe do rastreado modificado"; sed -n '1,10p' "$_r/r4d.log"; fi
    cp -p -- "$_r/r4d-sbom.bak" "$_r/wt/SBOM.md"
    git -C "$_r/wt" diff --quiet -- SBOM.md || bad "R4d: restaurar o SBOM.md da fixture falhou"
    # R4b — o .tag-push-epoch de um corte ANTERIOR fora do git (o passo 16 dele o grava, e so
    # o closeout o commita): recusa NOMEADA, com a rota do commit sem PLAN-NNN no assunto.
    _r4b=".claude/plans/PLAN-192/repass-TESTONLY"
    mkdir -p "$_r/wt/$_r4b" && printf '1700000000\n' > "$_r/wt/$_r4b/.tag-push-epoch"
    if _r_cut "$_r/r4b.log" --g0-only; then bad "R4b: G0 aceitou o .tag-push-epoch de um corte anterior fora do git"
    elif grep -q 'o .tag-push-epoch de um corte ANTERIOR esta fora do git' "$_r/r4b.log" \
         && grep -q "$_r4b/.tag-push-epoch" "$_r/r4b.log" \
         && grep -q "git commit -m 'closeout do corte anterior" "$_r/r4b.log"; then
      ok "R4b (controle vermelho): o .tag-push-epoch de um corte anterior fora do git e recusado pelo nome, com a rota"
    else bad "R4b: recusa sem o nome ou sem a rota"; sed -n '1,10p' "$_r/r4b.log"; fi
    rm -f -- "$_r/wt/$_r4b/.tag-push-epoch"; rmdir -- "$_r/wt/$_r4b" 2>/dev/null
    # R5c/R5d — entre os passos 5 e 11 o HEAD e o candidato gravado.
    git -C "$_r/wt" rev-parse HEAD > "$_r/wt/$EV/CANDIDATE.sha"
    _r_state 5
    if _r_cut "$_r/r5c.log" --g0-only \
       && grep -q 'OK: o .cut-state (passo 5 feito) e o HEAD apontam o mesmo candidato' "$_r/r5c.log"; then
      ok "R5c: passo 5 feito e HEAD == CANDIDATE.sha: G0 verde (sem a sonda, que o passo 5 ja rodou)"
    else bad "R5c: G0 recusou o .cut-state coerente"; sed -n '1,10p' "$_r/r5c.log"; fi
    git -C "$_r/wt" rev-parse 'HEAD^' > "$_r/wt/$EV/CANDIDATE.sha"
    if _r_cut "$_r/r5d.log" --g0-only; then bad "R5d: .cut-state de tentativa anterior passou"
    elif grep -q 'o .cut-state diz que o passo 5 gravou o candidato' "$_r/r5d.log" \
         && grep -q '.ceo-ga-archive' "$_r/r5d.log"; then
      ok "R5d (controle vermelho): passo 5 feito com HEAD != CANDIDATE.sha e recusado, com a rota de arquivar FORA do repositorio"
    else bad "R5d: recusa sem o motivo/rota"; sed -n '1,8p' "$_r/r5d.log"; fi
    # R5e/R5f — tentativa PARCIAL: arquivada DENTRO do plano e recusada; pela rota
    # documentada (FORA do repositorio, CANDIDATE.sha e .cut-state mantidos) o G0 fica
    # verde, o passo 6 e o primeiro pendente e o runner nao ve evidencia anterior.
    git -C "$_r/wt" rev-parse HEAD > "$_r/wt/$EV/CANDIDATE.sha"
    _r_state 5
    for _pf in CONDITIONS-ga.reviewed.md PROVENANCE-ga.md verdict-ga-1.txt transcript-ga-1.log paths-ga-1.manifest.txt probe-ga.txt; do
      printf 'TEST ONLY: tentativa parcial\n' > "$_r/wt/$EV/$_pf"
    done
    { printf '#!/bin/bash\nset -uo pipefail\n'
      printf 'die() { printf "FATAL: %%s\\n" "$*" >&2; exit 1; }\n'
      printf 'OUT="$1"\n'
      awk '/^assert_attempt_absent\(\) \{$/,/^\}$/' "$_r/wt/$EV/run-ga-repass.sh"
      printf 'assert_attempt_absent && printf "R5F-ATTEMPT-ABSENT\\n"\n'; } > "$SCRATCH/r5f-aa.sh"
    if bash "$SCRATCH/r5f-aa.sh" "$_r/wt/$EV" > "$_r/r5f-aa0.log" 2>&1; then
      bad "R5f0: o assert_attempt_absent do runner nao viu a tentativa parcial plantada"
    elif grep -q 'evidencia de tentativa anterior presente' "$_r/r5f-aa0.log"; then
      ok "R5f0 (controle vermelho): o runner (verbatim) recusa rodar sobre a tentativa parcial plantada"
    else bad "R5f0: recusa sem o motivo"; sed -n '1,4p' "$_r/r5f-aa0.log"; fi
    _inrepo="$_r/wt/$PLAN_DIR/repass-ga-20260930-NOGO-r1-capacidade"
    mkdir -p "$_inrepo" && cp -- "$_r/wt/$EV/PROVENANCE-ga.md" "$_inrepo/"
    if _r_cut "$_r/r5e.log" --g0-only; then bad "R5e: tentativa arquivada DENTRO do plano passou no G0"
    elif grep -q "repass-ga-20260930-NOGO-r1-capacidade/PROVENANCE-ga.md" "$_r/r5e.log"; then
      ok "R5e (controle vermelho): tentativa arquivada DENTRO do plano e recusada no G0, pelo nome"
    else bad "R5e: recusa sem nomear o arquivo"; sed -n '1,8p' "$_r/r5e.log"; fi
    rm -f -- "$_inrepo/PROVENANCE-ga.md"; rmdir -- "$_inrepo" 2>/dev/null
    _arch="$SCRATCH/rhome/.ceo-ga-archive/repass-ga-TEST-capacidade"
    mkdir -p "$_arch"
    ( cd "$_r/wt" && git status --porcelain --untracked-files=all -- "$EV/" ) > "$_r/r5f.list" \
      || bad "R5f: git status da evidencia falhou"
    while IFS= read -r _l; do
      case "$_l" in '??'*) _p="${_l#???}" ;; *) continue ;; esac
      [ "$_p" = "$EV/CANDIDATE.sha" ] && continue
      mv -- "$_r/wt/$_p" "$_arch/" || bad "R5f: mv de $_p falhou"
    done < "$_r/r5f.list"
    if _r_cut "$_r/r5f.log" --g0-only && grep -q 'G0 verde (--g0-only)' "$_r/r5f.log" \
       && grep -q 'Pendentes: 6 7 8 ' "$_r/r5f.log" && [ -s "$_r/wt/$EV/CANDIDATE.sha" ] \
       && [ -f "$_arch/CONDITIONS-ga.reviewed.md" ] && [ -f "$_arch/probe-ga.txt" ]; then
      ok "R5f: rota documentada (FORA do repositorio; CANDIDATE.sha e .cut-state mantidos): G0 verde e o passo 6 e o primeiro pendente"
    else bad "R5f: a rota documentada nao deixou o G0 verde retomando do passo 6"; sed -n '1,14p' "$_r/r5f.log"; fi
    if bash "$SCRATCH/r5f-aa.sh" "$_r/wt/$EV" > "$_r/r5f-aa.log" 2>&1 && grep -q R5F-ATTEMPT-ABSENT "$_r/r5f-aa.log"; then
      ok "R5f: depois da rota, o assert_attempt_absent do runner (verbatim) nao acha tentativa anterior"
    else bad "R5f: o runner ainda veria tentativa anterior"; sed -n '1,4p' "$_r/r5f-aa.log"; fi
    rm -f -- "$_r/wt/$EV/CANDIDATE.sha"
    _r_state 0
    # E3r — a RETOMADA do passo 11 pelo CORTE INTEIRO (o G0 real incluido). O E3/E3b/E3c
    # rodam so o bloco do passo 11 e nao provam que o G0 admite a arvore de uma retomada.
    # Estado: passos 1-10 feitos, HEAD == CANDIDATE.sha == origin/main == o candidato da
    # secao E, e a evidencia + os fields + o envelope (o $VD, FORA do plano) da secao E
    # untracked, como o passo 10 os deixa.
    #   E3r1 o passo 10 terminou (o .asc na arvore): o G0 admite e o 11 commita;
    #   E3r2 o 11 morreu entre o `git add` e o `git commit` (a lista literal staged, o .asc
    #        so no backup): o G0 admite, e o 11 restaura o .asc, desfaz o staging e commita;
    #   vermelhos: um untracked FORA da lista (ao lado do envelope) e um caminho staged
    #   fora da lista sao recusados pelo nome, sem commit, e a recusa e a do G0
    #   (tree_clean_resume_11, com a classe do intruso) — nao a do staging do passo 11,
    #   que o E3d prova no bloco. Cada vermelho so conta com o seu gemeo positivo verde
    #   neste ensaio (a mesma arvore sem o intruso e admitida): a recusa e a do intruso,
    #   nunca a de uma arvore de retomada que o G0 recusa inteira;
    #   E3r3 o envelope ($VD) ADULTERADO depois do passo 10 (verdict: GO no lugar do
    #   GO-WITH-CONDITIONS assinado): o passo 11 o re-deriva dos fields assinados, avisa
    #   pelo nome e commita os bytes derivados (== os do passo 10), nunca os adulterados.
    #   Gemeo: o E3r1 (o envelope intacto: commit sem AVISO).
    _e3r_asc="$SCRATCH/rhome/.rc2-backup/verdict-fields-v1.4.2.md.asc"
    _e3r_stray=".claude/governance/TEST-ONLY-e3r-stray.md"
    _e3r_staged="TEST-ONLY-e3r-staged.txt"
    _e3r_clean() {  # a fixture de volta: HEAD e index no ponto de partida, nada da secao E
      local _p
      git -C "$_r/wt" reset -q --hard "$_r_base" || return 1
      while IFS= read -r _p; do
        [ -n "$_p" ] || continue
        git -C "$_r/wt" cat-file -e "$_r_base:$_p" 2>/dev/null && continue
        rm -f -- "$_r/wt/$_p"
      done < "$_e_list"
      rm -f -- "$_r/wt/$_e_vf.asc" "$_r/wt/$EV/CANDIDATE.sha" "$_e3r_asc" \
        "$_r/wt/$_e3r_stray" "$_r/wt/$_e3r_staged"
      _r_state 0
    }
    _e3r_prep() {  # $1 = 1 (o .asc na arvore) | 2 (a lista literal staged, o .asc no backup)
      _e3r_clean || return 1
      ( cd "$CLONE" && tar -cf - -T "$_e_list" ) | ( cd "$_r/wt" && tar -xf - ) || return 1
      [ -f "$_r/wt/$EV/CANDIDATE.sha" ] || printf '%s\n' "$CAND" > "$_r/wt/$EV/CANDIDATE.sha" || return 1
      if [ "$1" = "1" ]; then
        cp -p -- "$CLONE/$_e_vf.asc" "$_r/wt/$_e_vf.asc" || return 1
      else
        mkdir -p "$SCRATCH/rhome/.rc2-backup" && cp -p -- "$CLONE/$_e_vf.asc" "$_e3r_asc" || return 1
        ( cd "$_r/wt" && xargs git add -- < "$_e_list" ) || return 1
      fi
      _r_state 10
    }
    # O efeito comum de uma recusa: nada commitado nem pushado, o passo 11 nao marcado.
    _e3r_held() {
      [ "$(git -C "$_r/wt" rev-parse HEAD)" = "$CAND" ] \
        && [ "$(git -C "$_r/origin.git" rev-parse refs/heads/main)" = "$CAND" ] \
        && ! grep -qx 'STEP-11' "$_r/wt/$EV/.cut-state"
    }
    # O efeito de um passo 11 que commitou: UM commit sobre o candidato, com o envelope e
    # os fields, index vazio, nada pushado, o .asc no backup e fora da arvore.
    _e3r_committed() {  # $1 = log
      grep -qx 'STEP-11' "$_r/wt/$EV/.cut-state" && grep -q 'PARADO depois do passo 11' "$1" \
        && [ "$(git -C "$_r/wt" rev-parse 'HEAD^' 2>/dev/null)" = "$CAND" ] \
        && git -C "$_r/wt" log -1 --format=%s | grep -qF 'verdito pair-rail v1.4.2 assinado' \
        && git -C "$_r/wt" show --name-only --format= HEAD | grep -qxF "$_e_vd" \
        && git -C "$_r/wt" show --name-only --format= HEAD | grep -qxF "$_e_vf" \
        && git -C "$_r/wt" diff --cached --quiet \
        && [ "$(git -C "$_r/origin.git" rev-parse refs/heads/main)" = "$CAND" ] \
        && [ -f "$_e3r_asc" ] && [ ! -e "$_r/wt/$_e_vf.asc" ]
    }
    if [ -n "${_e_list:-}" ] && [ -f "${_e_list:-}" ] && [ -f "$CLONE/$_e_vf.asc" ] \
       && [ -n "${CAND:-}" ] && [ "$_r_base" = "$CAND" ]; then
      _e3r_pos1=0; _e3r_pos2=0
      if _e3r_prep 1; then
        _e3r1c=0; _r_cut "$_r/e3r1.log" --until 11 || _e3r1c=$?
        if [ "$_e3r1c" -eq 0 ] && _e3r_committed "$_r/e3r1.log" \
           && grep -qF 'envelope re-derivado dos fields assinados' "$_r/e3r1.log" \
           && ! grep -qF 'AVISO: o envelope da arvore' "$_r/e3r1.log"; then
          ok "E3r1: corte inteiro, passos 1-10 feitos e o envelope untracked FORA do plano: o G0 real admite a retomada e o passo 11 re-deriva o envelope (intacto: sem AVISO) e commita sobre o candidato"
          _e3r_pos1=1
        else bad "E3r1: o corte inteiro nao retomou o passo 11 depois do passo 10 (rc=$_e3r1c)"; grep -E 'FAIL|untracked|RASTREADO' "$_r/e3r1.log" | sed -n '1,8p'; fi
      else bad "E3r1: preparacao da fixture falhou"; fi
      if _e3r_prep 2; then
        _e3r2c=0; _r_cut "$_r/e3r2.log" --until 11 || _e3r2c=$?
        if [ "$_e3r2c" -eq 0 ] && _e3r_committed "$_r/e3r2.log" \
           && grep -q 'assinatura restaurada do backup' "$_r/e3r2.log" \
           && grep -q 'staging de uma tentativa anterior deste passo desfeito' "$_r/e3r2.log"; then
          ok "E3r2: corte inteiro com a lista literal JA staged e o .asc so no backup: o G0 real admite, o passo 11 restaura o .asc, refaz o staging e commita sobre o candidato"
          _e3r_pos2=1
        else bad "E3r2: o corte inteiro nao retomou o passo 11 que morreu entre o git add e o git commit (rc=$_e3r2c)"; grep -E 'FAIL|untracked|RASTREADO' "$_r/e3r2.log" | sed -n '1,8p'; fi
      else bad "E3r2: preparacao da fixture falhou"; fi
      if _e3r_prep 1 && printf 'x\n' > "$_r/wt/$_e3r_stray"; then
        if _r_cut "$_r/e3r-stray.log" --until 11; then bad "E3r: untracked fora da lista passou pelo corte inteiro"
        elif grep -qF 'arvore nao esta limpa (retomada entre os passos 10 e 11' "$_r/e3r-stray.log" \
             && grep -qF "$_e3r_stray (untracked)" "$_r/e3r-stray.log" \
             && _e3r_held && [ "$_e3r_pos1" = "1" ]; then
          ok "E3r (controle vermelho): um untracked FORA da lista ao lado do envelope e recusado pelo G0 real (a arvore da retomada 10-11), pelo nome e como untracked, e nada e commitado (a mesma arvore sem ele e admitida: E3r1)"
          _red="$_red E3r-stray"
        else bad "E3r: untracked fora da lista nao recusado PELO G0 (tree_clean_resume_11) com o nome, com commit, ou sem o gemeo E3r1 verde"; grep -E 'FAIL|untracked' "$_r/e3r-stray.log" | sed -n '1,6p'; fi
      else bad "E3r: preparacao do untracked fora da lista falhou"; fi
      if _e3r_prep 2 && printf 'x\n' > "$_r/wt/$_e3r_staged" && git -C "$_r/wt" add -- "$_e3r_staged"; then
        if _r_cut "$_r/e3r-staged.log" --until 11; then bad "E3r: caminho staged fora da lista passou pelo corte inteiro"
        elif grep -qF 'arvore nao esta limpa (retomada entre os passos 10 e 11' "$_r/e3r-staged.log" \
             && grep -qF "$_e3r_staged (staged FORA da lista literal do passo 11)" "$_r/e3r-staged.log" \
             && _e3r_held && [ "$_e3r_pos2" = "1" ]; then
          ok "E3r (controle vermelho): um caminho staged FORA da lista literal e recusado pelo G0 real (a arvore da retomada 10-11), pelo nome e como staged fora da lista, e nada e commitado (a mesma arvore sem ele e admitida: E3r2)"
          _red="$_red E3r-staged"
        else bad "E3r: staged fora da lista nao recusado PELO G0 (tree_clean_resume_11) com o nome, com commit, ou sem o gemeo E3r2 verde"; grep -E 'FAIL|RASTREADO|FORA' "$_r/e3r-staged.log" | sed -n '1,6p'; fi
      else bad "E3r: preparacao do staged fora da lista falhou"; fi
      # E3r3 — o envelope adulterado DEPOIS do passo 10 (o $VD untracked da arvore com
      # «verdict: GO» no lugar do GO-WITH-CONDITIONS que os fields assinados derivam):
      # o passo 11 do corte inteiro o re-deriva, avisa pelo nome, e o commit leva os
      # bytes DERIVADOS (iguais aos que o passo 10 escreveu), nunca os adulterados.
      _e3r3_s10="$_r/e3r3-step10.md"; _e3r3_hd="$_r/e3r3-head.md"
      rm -f -- "$_e3r3_s10" "$_e3r3_hd"
      if _e3r_prep 1 && cp -p -- "$_r/wt/$_e_vd" "$_e3r3_s10" \
         && python3 - "$_r/wt/$_e_vd" <<'PYE3R3' && ! cmp -s -- "$_e3r3_s10" "$_r/wt/$_e_vd"
import re, sys
p = sys.argv[1]
t = open(p, encoding="utf-8").read()
n, k = re.subn(r"(?m)^verdict: GO-WITH-CONDITIONS$", "verdict: GO", t)
if k != 1:
    raise SystemExit("o envelope do passo 10 tem %d linha(s) verdict: GO-WITH-CONDITIONS (esperado 1)" % k)
open(p, "w", encoding="utf-8").write(n)
PYE3R3
      then
        _e3r3c=0; _r_cut "$_r/e3r3.log" --until 11 || _e3r3c=$?
        # O envelope que o commit do HEAD carrega (vazio se nao ha commit dele).
        git -C "$_r/wt" show "HEAD:$_e_vd" > "$_e3r3_hd" 2>/dev/null || : > "$_e3r3_hd"
        if [ "$_e3r3c" -eq 0 ] && _e3r_committed "$_r/e3r3.log" \
           && grep -qF 'AVISO: o envelope da arvore (' "$_r/e3r3.log" \
           && grep -qF 'envelope re-derivado dos fields assinados' "$_r/e3r3.log" \
           && [ -s "$_e3r3_hd" ] && cmp -s -- "$_e3r3_s10" "$_e3r3_hd" \
           && ! grep -qx 'verdict: GO' "$_e3r3_hd" && [ "$_e3r_pos1" = "1" ]; then
          ok "E3r3 (controle vermelho): o envelope adulterado depois do passo 10 (verdict: GO) e re-derivado dos fields assinados pelo passo 11 do corte inteiro, com AVISO nomeado; o commit leva os bytes do passo 10, nunca os adulterados (o envelope intacto: E3r1, sem AVISO)"
          _red="$_red E3r3"
        else bad "E3r3: o envelope adulterado depois do passo 10 nao foi re-derivado com AVISO, ou o commit nao leva os bytes do passo 10 (rc=$_e3r3c; no HEAD: $(grep -m1 '^verdict:' "$_e3r3_hd" || echo 'sem envelope'))"; grep -E 'FAIL|AVISO: o envelope|envelope re-derivado' "$_r/e3r3.log" | sed -n '1,8p'; fi
      else bad "E3r3: preparacao do envelope adulterado falhou"; fi
      _e3r_clean || bad "E3r: restaurar a fixture falhou"
    else bad "E3r: sem a evidencia/assinatura da secao E, ou o HEAD do R nao e o candidato dela"; fi
    # R5/R5b — retomada entre os passos 11 e 13.
    git -C "$_r/wt" rev-parse HEAD > "$_r/wt/$EV/CANDIDATE.sha"
    if git -C "$_r/wt" commit -q --allow-empty -m "TEST ONLY: veredito local nao pushado"; then
      _r_state 11
      if _r_cut "$_r/r5.log" --g0-only && grep -q 'retomada entre os passos 11 e 13' "$_r/r5.log"; then
        ok "R5: G0 reconhece a retomada entre os passos 11 e 13 (veredito commitado, nao pushado)"
      else bad "R5: G0 recusou a retomada 11-13"; sed -n '1,12p' "$_r/r5.log"; fi
      _r_state 10
      if _r_cut "$_r/r5b.log" --g0-only; then bad "R5b: HEAD a frente de origin/main sem o passo 11 passou"
      elif grep -q 'fora de uma retomada conhecida' "$_r/r5b.log" && grep -q 'NAO pushe as cegas' "$_r/r5b.log"; then
        ok "R5b (controle vermelho): HEAD a frente sem o passo 11 e recusado, e o conselho NAO e pushar"
      else bad "R5b: recusa sem o estado nomeado"; sed -n '1,8p' "$_r/r5b.log"; fi
      git -C "$_r/wt" push -q origin HEAD:refs/heads/main 2>/dev/null || bad "R5: push de limpeza da fixture falhou"
      _r_base="$(git -C "$_r/wt" rev-parse HEAD)"
    else bad "R5: commit local da fixture falhou"; fi
    # R6 — retomada depois do passo 16: a tag do GA no remoto e o Release que o release.yml
    # cria em DRAFT. O G0 aceita; vermelhos: Release marcado pre-release, tag remota trocada,
    # registro do 16, tag local sem o 15, main que andou x main revertido.
    git -C "$_r/wt" rev-parse HEAD > "$_r/wt/$EV/CANDIDATE.sha"
    if git -C "$_r/wt" -c tag.gpgSign=false tag -a -m "TEST ONLY: GA fixture" v1.4.2 \
       && git -C "$_r/wt" push -q origin refs/tags/v1.4.2 2>/dev/null; then
      _r_state 16
      _r_gh 1 true false
      if _r_cut "$_r/r6.log" --g0-only && grep -q 'retomada pos-tag: o Release do v1.4.2 existe' "$_r/r6.log" \
         && grep -q 'OK: main; retomada pos-tag' "$_r/r6.log"; then
        ok "R6: G0 aceita, depois do passo 16, o Release em DRAFT que o release.yml cria"
      else bad "R6: G0 recusou a retomada pos-tag"; sed -n '1,12p' "$_r/r6.log"; fi
      _r_gh 1 true true
      if _r_cut "$_r/r6b.log" --g0-only; then bad "R6b: Release marcado pre-release passou na retomada pos-tag do GA"
      elif grep -q "isPrerelease='True'" "$_r/r6b.log"; then ok "R6b (controle vermelho): Release marcado pre-release e recusado na retomada do GA"
      else bad "R6b: recusa sem o motivo"; sed -n '1,6p' "$_r/r6b.log"; fi
      _r_gh 1 true false
      if git -C "$_r/wt" push -q -f origin "v1.4.2^{commit}:refs/tags/v1.4.2" 2>/dev/null; then
        if _r_cut "$_r/r6c.log" --g0-only; then bad "R6c: tag remota trocada passou na retomada pos-tag"
        elif grep -q 'nao e o objeto assinado local' "$_r/r6c.log"; then ok "R6c (controle vermelho): tag remota que nao e o objeto local e recusada na retomada"
        else bad "R6c: recusa sem o motivo"; sed -n '1,6p' "$_r/r6c.log"; fi
        git -C "$_r/wt" push -q -f origin refs/tags/v1.4.2 2>/dev/null || bad "R6c: restaurar a tag remota falhou"
      else bad "R6c: nao consegui trocar a tag remota"; fi
      _r_state 15
      rm -f -- "$_r/wt/$EV/.tag-push-epoch"
      if _r_cut "$_r/r6d.log" --g0-only && grep -q 'passo 16 registrado agora' "$_r/r6d.log" \
         && grep -qx 'STEP-16' "$_r/wt/$EV/.cut-state" \
         && [ "$(tr -d ' \n' < "$_r/wt/$EV/.tag-push-epoch")" = "$(git -C "$_r/wt" for-each-ref --format='%(taggerdate:unix)' refs/tags/v1.4.2)" ] \
         && grep -q 'OK: main; retomada pos-tag' "$_r/r6d.log"; then
        ok "R6d: push da tag sem o marcador do 16 e reconhecido (remoto == objeto local): o 16 e registrado e o piso do passo 19 e a data da tag"
      else bad "R6d: o G0 nao reconheceu o push da tag sem marcador"; sed -n '1,12p' "$_r/r6d.log"; fi
      _r_state 15
      if git -C "$_r/wt" push -q -f origin "v1.4.2^{commit}:refs/tags/v1.4.2" 2>/dev/null; then
        if _r_cut "$_r/r6d2.log" --g0-only; then bad "R6d2: tag remota de OUTRO objeto, sem o passo 16, passou"
        elif grep -q 'ja existe no REMOTO' "$_r/r6d2.log" && ! grep -qx 'STEP-16' "$_r/wt/$EV/.cut-state"; then
          ok "R6d2 (controle vermelho): tag remota que nao e o objeto local NAO registra o 16 e e recusada"
        else bad "R6d2: recusa sem o motivo (ou o 16 foi registrado)"; sed -n '1,6p' "$_r/r6d2.log"; fi
        git -C "$_r/wt" push -q -f origin refs/tags/v1.4.2 2>/dev/null || bad "R6d2: restaurar a tag remota falhou"
      else bad "R6d2: nao consegui trocar a tag remota"; fi
      _r_state 14
      if _r_cut "$_r/r6d3.log" --g0-only; then bad "R6d3: tag local sem o passo 15 passou"
      elif grep -q 'ja existe (local)' "$_r/r6d3.log" && grep -q 'git tag -d v1.4.2' "$_r/r6d3.log"; then
        ok "R6d3 (controle vermelho): tag local sem o passo 15 e recusada, e a recusa nomeia a rota (git tag -d)"
      else bad "R6d3: recusa sem a rota"; sed -n '1,8p' "$_r/r6d3.log"; fi
      _r_state 16
      if git clone -q "$_r/origin.git" "$_r/other" 2>/dev/null && fixture_git_identity "$_r/other" \
         && git -C "$_r/other" commit -q --allow-empty -m "TEST ONLY: push alheio depois da tag" \
         && git -C "$_r/other" push -q origin HEAD:refs/heads/main 2>/dev/null; then
        if _r_cut "$_r/r6e.log" --g0-only \
           && grep -q 'AVISO: main andou depois do push da tag (1 commit' "$_r/r6e.log" \
           && grep -q 'G0 verde (--g0-only)' "$_r/r6e.log"; then
          ok "R6e: retomada pos-tag com main que andou (push alheio depois da tag) passa com AVISO"
        else bad "R6e: o G0 recusou a retomada pos-tag com main que andou"; sed -n '1,12p' "$_r/r6e.log"; fi
        if git -C "$_r/wt" push -q -f origin "v1.4.2^{commit}^:refs/heads/main" 2>/dev/null; then
          if _r_cut "$_r/r6e2.log" --g0-only; then bad "R6e2: main revertido para antes da tag passou na retomada"
          elif grep -q 'fora de uma retomada conhecida' "$_r/r6e2.log"; then
            ok "R6e2 (controle vermelho): main revertido para antes da tag e recusado na retomada pos-tag"
          else bad "R6e2: recusa sem o motivo"; sed -n '1,8p' "$_r/r6e2.log"; fi
        else bad "R6e2: nao consegui reverter o main da fixture"; fi
        git -C "$_r/wt" push -q -f origin HEAD:refs/heads/main 2>/dev/null || bad "R6e: restaurar o main da fixture falhou"
      else bad "R6e: push alheio na fixture falhou"; fi
      # R7 — o banner de PUBLICADO so com o passo 20 concluido.
      _r_state 19
      if _r_cut "$_r/r7.log" --until 19 && grep -q 'PARADO depois do passo 19' "$_r/r7.log" \
         && grep -q 'pendentes: 20' "$_r/r7.log" && ! grep -q 'PUBLICADO' "$_r/r7.log"; then
        ok "R7: --until 19 para, lista o 20 pendente e NAO imprime o banner de PUBLICADO"
      else bad "R7: --until nao parou como devia"; sed -n '1,12p' "$_r/r7.log"; fi
      _r_state 20
      if _r_cut "$_r/r7b.log" && grep -q 'v1.4.2 PUBLICADO' "$_r/r7b.log"; then
        ok "R7b: com o passo 20 concluido, o banner de PUBLICADO sai"
      else bad "R7b: banner ausente com os 20 passos concluidos"; sed -n '1,12p' "$_r/r7b.log"; fi

      # =====================================================================
      say "PUB. passos 17-20 REAIS contra os stubs: o Release so sai do DRAFT depois do npm"
      # O release.yml verde; o npm-publish ESPERANDO a aprovacao do ambiente production-npm
      # (a do Owner, no navegador) e depois success; o registry confirmando a 1.4.2. O
      # Release (que o release.yml cria em DRAFT) e re-afirmado DRAFT ANTES de o registry
      # confirmar, o recibo do step de publish e conferido, e o UNDRAFT vem depois dos dois.
      # A ordem e a do registro de chamadas dos stubs; o CUT nunca chama `npm publish`.
      _r_pubrun() {  # $1 = log, $2 = isDraft inicial do Release do GA; ecoa nada, rc = o do CUT
        _r_state 16
        printf '%s\n' "$(( $(date +%s) - 60 ))" > "$_r/wt/$EV/.tag-push-epoch"
        _r_gh 1 "$2" false
        _r_cut "$1"
      }
      _pubrc=0; _r_pubrun "$_r/pub.log" true || _pubrc=$?
      _l_draft="$(_r_line '^gh release edit v1[.]4[.]2 .*--draft(=true)?( |$)')"
      _l_npm="$(_r_line '^npm view .*@1[.]4[.]2 version => 1[.]4[.]2$')"
      _l_rcpt="$(_r_line '^gh run view 4343 .*Publish [(]Trusted Publishing')"
      _l_undraft="$(_r_line '^gh release edit v1[.]4[.]2 .*--draft=false')"
      if [ "$_pubrc" -eq 0 ] && grep -q 'v1.4.2 PUBLICADO' "$_r/pub.log" \
         && grep -qx 'STEP-17' "$_r/wt/$EV/.cut-state" && grep -qx 'STEP-18' "$_r/wt/$EV/.cut-state" \
         && grep -qx 'STEP-19' "$_r/wt/$EV/.cut-state" && grep -qx 'STEP-20' "$_r/wt/$EV/.cut-state" \
         && [ "$(cat "$_r/gh/ga-draft")" = "false" ]; then
        ok "PUB1: passos 17-20 reais contra os stubs: o corte termina com o Release publico e o banner de PUBLICADO"
      else bad "PUB1: os passos 17-20 nao terminaram (rc=$_pubrc)"; sed -n '1,40p' "$_r/pub.log"; fi
      if [ -n "$_l_draft" ] && [ -n "$_l_npm" ] && [ -n "$_l_undraft" ] \
         && [ "$_l_draft" -lt "$_l_npm" ] && [ "$_l_npm" -lt "$_l_undraft" ]; then
        ok "PUB2: ordem: DRAFT re-afirmado (chamada $_l_draft) antes de o registry confirmar a 1.4.2 ($_l_npm); UNDRAFT depois ($_l_undraft)"
      else bad "PUB2: a ordem DRAFT -> npm -> UNDRAFT nao se verificou (draft=$_l_draft npm=$_l_npm undraft=$_l_undraft)"; sed -n '1,60p' "$_r/gh/calls.log"; fi
      if [ -n "$_l_rcpt" ] && [ -n "$_l_undraft" ] && [ "$_l_rcpt" -lt "$_l_undraft" ]; then
        ok "PUB3: o recibo do step de publish (Publish (Trusted Publishing ...) = success) e conferido antes do UNDRAFT"
      else bad "PUB3: sem o recibo do step de publish antes do UNDRAFT (recibo=$_l_rcpt undraft=$_l_undraft)"; fi
      if grep -q 'production-npm' "$_r/pub.log" && grep -qF 'example.invalid/actions/runs/4343' "$_r/pub.log" \
         && ! grep -q '^npm .* => RECUSADO$' "$_r/gh/calls.log"; then
        ok "PUB4: com o npm-publish esperando, o passo 18 aponta ao Owner o run da aprovacao do production-npm; o CUT nunca chama npm publish"
      else bad "PUB4: o passo 18 nao apontou o run da aprovacao (ou o CUT chamou o npm fora do npm view)"; grep -n 'production-npm\|RECUSADO' "$_r/pub.log" "$_r/gh/calls.log" | sed -n '1,6p'; fi
      # O EFEITO comum das recusas do passo 18: rc != 0, o 18 nao marcado, o Release em
      # DRAFT, nenhum undraft, nenhum banner. So o efeito nao prova a recusa DO GATE — uma
      # queda cedo (antes do passo 18) o produz igual, porque o Release ja comeca em DRAFT:
      # cada controle abaixo exige TAMBEM a recusa NOMEADA dele, e o PUBX prova que uma
      # queda cedo satisfaz o efeito e nenhuma das recusas nomeadas.
      _pub_held() {  # $1 = rc do CUT, $2 = log
        [ "$1" -ne 0 ] && ! grep -qx 'STEP-18' "$_r/wt/$EV/.cut-state" \
          && [ "$(cat "$_r/gh/ga-draft")" = "true" ] \
          && [ -z "$(_r_line '^gh release edit v1[.]4[.]2 .*--draft=false')" ] \
          && ! grep -q 'PUBLICADO' "$2"
      }
      # As recusas NOMEADAS (texto do die do passo 18, nunca a linha de progresso
      # «... npm-publish: completed/failure», que qualquer desfecho imprime).
      _pub5_named() { grep -qF "npm-publish terminou 'failure' (run 4343)" "$1"; }
      _pub6_named() { grep -qF 'o registry nao confirmou' "$1" && grep -qF 'tentativa 5/5' "$1"; }
      _pub7_named() { grep -qF "step de publish concluiu '$2'" "$1"; }  # $2 = recibo
      _pub8_named() { grep -qF 'falhou ao ler o recibo' "$1"; }
      # PUB5 — o npm-publish termina failure: o passo 18 recusa, o Release FICA em DRAFT e
      # nunca e undraftado.
      R_NPM_RUN=failure
      _p5rc=0; _r_pubrun "$_r/pub5.log" true || _p5rc=$?
      R_NPM_RUN=success
      if _pub_held "$_p5rc" "$_r/pub5.log" && _pub5_named "$_r/pub5.log"; then
        ok "PUB5 (controle vermelho): npm-publish 'failure' => o passo 18 recusa pelo nome (npm-publish terminou 'failure'), o Release fica em DRAFT e nunca e undraftado"
        _red="$_red PUB5"
      else bad "PUB5: npm-publish vermelho nao deu a recusa nomeada com o Release em DRAFT (rc=$_p5rc)"; sed -n '1,30p' "$_r/pub5.log"; fi
      # PUB5b — o npm-publish vermelho porque o job await-release-gate dele terminou sem
      # success (o run anterior a um rerun do release.yml): a recusa nomeia o rerun DELE.
      R_NPM_RUN=failure; R_NPM_AWAIT=failure
      _p5brc=0; _r_pubrun "$_r/pub5b.log" true || _p5brc=$?
      R_NPM_RUN=success; R_NPM_AWAIT=success
      if [ "$_p5brc" -ne 0 ] && grep -q 'gh run rerun 4343 --failed' "$_r/pub5b.log" \
         && [ "$(cat "$_r/gh/ga-draft")" = "true" ] && ! grep -qx 'STEP-18' "$_r/wt/$EV/.cut-state"; then
        ok "PUB5b (controle vermelho): o await-release-gate do npm-publish sem success e recusa com a rota do rerun do run DELE; o Release fica em DRAFT"
      else bad "PUB5b: o gate vermelho do npm-publish nao deu a rota do rerun (rc=$_p5brc)"; sed -n '1,30p' "$_r/pub5b.log"; fi
      # PUB6 — o run termina success mas o registry NUNCA confirma a 1.4.2: recusa depois das
      # tentativas, o Release fica em DRAFT e nunca e undraftado.
      R_NPM_NEVER=1
      _p6rc=0; _r_pubrun "$_r/pub6.log" true || _p6rc=$?
      R_NPM_NEVER=0
      if _pub_held "$_p6rc" "$_r/pub6.log" && _pub6_named "$_r/pub6.log"; then
        ok "PUB6 (controle vermelho): registry que nao confirma a 1.4.2 => recusa nomeada depois da tentativa 5/5, o Release fica em DRAFT e nunca e undraftado"
        _red="$_red PUB6"
      else bad "PUB6: o registry mudo nao deu a recusa nomeada (5/5) com o Release em DRAFT (rc=$_p6rc)"; sed -n '1,30p' "$_r/pub6.log"; fi
      # PUB7 — o run success e o registry com a 1.4.2 COMO latest, mas o recibo do step de
      # publish NAO e success (skipped: a versao ja estava no registry antes desta
      # tentativa; failure; null: o step nao achado): recusa pelo nome, o Release em DRAFT.
      for _pv in skipped failure null; do
        R_NPM_RECEIPT="$_pv"
        _p7rc=0; _r_pubrun "$_r/pub7-$_pv.log" true || _p7rc=$?
        R_NPM_RECEIPT=success
        if _pub_held "$_p7rc" "$_r/pub7-$_pv.log" && _pub7_named "$_r/pub7-$_pv.log" "$_pv" \
           && [ -n "$(_r_line '^gh run view 4343 .*Publish [(]Trusted Publishing')" ] \
           && [ -n "$(_r_line '^npm view .* => 1[.]4[.]2$')" ]; then
          ok "PUB7 (controle vermelho): recibo '$_pv' do step de publish, com o registry ja confirmando a 1.4.2 => recusa nomeada; o Release fica em DRAFT e nunca e undraftado"
          _red="$_red PUB7-$_pv"
        else bad "PUB7: recibo '$_pv' nao deu a recusa nomeada com o Release em DRAFT (rc=$_p7rc)"; sed -n '1,30p' "$_r/pub7-$_pv.log"; fi
      done
      # PUB8 — a LEITURA do recibo falha (transporte): recusa nomeada, nunca «recibo
      # ausente» nem success; o Release fica em DRAFT.
      R_NPM_RECEIPT=error
      _p8rc=0; _r_pubrun "$_r/pub8.log" true || _p8rc=$?
      R_NPM_RECEIPT=success
      if _pub_held "$_p8rc" "$_r/pub8.log" && _pub8_named "$_r/pub8.log" \
         && grep -qF 'error connecting to api.github.com' "$_r/pub8.log"; then
        ok "PUB8 (controle vermelho): a leitura do recibo que FALHA (transporte) e recusa nomeada com o erro do gh; o Release fica em DRAFT e nunca e undraftado"
        _red="$_red PUB8"
      else bad "PUB8: a leitura do recibo que falha nao deu a recusa nomeada (rc=$_p8rc)"; sed -n '1,30p' "$_r/pub8.log"; fi
      # PUB9 — a 1.4.2 existe no registry mas o latest SEGUE 1.4.1: o passo 18 exige as
      # duas coisas (a instalacao nova pelo npm pega o latest) — recusa nomeada depois das
      # 5 tentativas, o Release em DRAFT.
      R_NPM_LATEST=1.4.1
      _p9rc=0; _r_pubrun "$_r/pub9.log" true || _p9rc=$?
      R_NPM_LATEST=""
      if _pub_held "$_p9rc" "$_r/pub9.log" && _pub6_named "$_r/pub9.log" \
         && grep -qF "(1.4.2='1.4.2', latest='1.4.1')" "$_r/pub9.log"; then
        ok "PUB9 (controle vermelho): a 1.4.2 no registry com o latest ainda 1.4.1 => recusa nomeada (nao confirmou como latest) depois de 5 tentativas; o Release fica em DRAFT"
        _red="$_red PUB9"
      else bad "PUB9: a 1.4.2 sem o latest nao deu a recusa nomeada com o Release em DRAFT (rc=$_p9rc)"; sed -n '1,30p' "$_r/pub9.log"; fi
      # PUBX — o contra-exemplo: uma queda CEDO (o hold da rc.1 incompleto recusa no G0,
      # antes do passo 17) com o mesmo estado dos PUB. Ela satisfaz o EFEITO e nenhuma
      # recusa nomeada; e o texto do caminho de TIMEOUT (a linha de progresso com
      # 'failure' + o die dos 90 min) nao satisfaz a recusa nomeada do PUB5.
      R_PUBAT_H=1
      _pxrc=0; _r_pubrun "$_r/pubx.log" true || _pxrc=$?
      R_PUBAT_H=30
      printf '  ... npm-publish: completed/failure\n\nFAIL: npm-publish nao concluiu em 90 min — GA em DRAFT (invisivel)\n' \
        > "$_r/pubx-timeout.log"
      if _pub_held "$_pxrc" "$_r/pubx.log" && grep -q 'hold ADR-103 incompleto' "$_r/pubx.log" \
         && ! _pub5_named "$_r/pubx.log" && ! _pub6_named "$_r/pubx.log" \
         && ! _pub7_named "$_r/pubx.log" skipped && ! _pub8_named "$_r/pubx.log" \
         && ! _pub5_named "$_r/pubx-timeout.log"; then
        ok "PUBX: uma queda cedo (G0) satisfaz o efeito DRAFT e NENHUMA recusa nomeada, e o texto do timeout nao passa pelo PUB5 — PUB5-PUB9 nao ficam verdes por queda cedo nem por timeout"
      else bad "PUBX: o contra-exemplo passaria por um controle do passo 18 (rc=$_pxrc) — o controle e vacuo"; sed -n '1,12p' "$_r/pubx.log"; fi

      # =====================================================================
      say "GE. gh_release_edit_idem: transporte x estado pedido x ausencia (passos 17-20 REAIS)"
      # O unico abort do corte do GA v1.4.1 foi um `connection reset` no `gh release edit
      # --draft` do passo 18, com o PATCH ja aplicado. Aqui o Release comeca PUBLICO (isDraft
      # false): o estado que o passo 18 pede (DRAFT) so vale se o edit o aplicou.
      #   GE1 o edit APLICA e a resposta se perde (connection reset) => a funcao rele o
      #       Release, ve o estado pedido e segue — o corte chega ao banner;
      #   GE2 o edit responde «release not found» => recusa NOMEADA na 1.a chamada;
      #   GE3 o edit responde connection reset e NUNCA aplica => re-tenta e recusa no TETO
      #       (o stub corta em 40 chamadas: passar disso e laco sem teto);
      #   GE4 o edit responde um erro que NAO e transporte (HTTP 422) => recusa NOMEADA
      #       na 1.a chamada, sem re-tentativa.
      R_EDIT_MODE=reset-after
      _ge1rc=0; _r_pubrun "$_r/ge1.log" false || _ge1rc=$?
      _l_e1="$(_r_line '^gh release edit v1[.]4[.]2 ')"
      _ge1_next="$(awk -v n="${_l_e1:-0}" 'NR == n + 1 { print; exit }' "$_r/gh/calls.log")"
      if [ "$_ge1rc" -eq 0 ] && [ -n "$_l_e1" ] && grep -q 'v1.4.2 PUBLICADO' "$_r/ge1.log" \
         && grep -qx 'STEP-20' "$_r/wt/$EV/.cut-state" && [ "$(cat "$_r/gh/ga-draft")" = "false" ] \
         && case "$_ge1_next" in "gh release view v1.4.2 "*) true ;; *) false ;; esac; then
        ok "GE1: connection reset DEPOIS de o PATCH chegar: a funcao rele o Release (o estado pedido ja vale) e o corte segue ate o banner"
        _red="$_red GE1"
      else bad "GE1: o reset com o estado ja aplicado nao seguiu pela releitura (rc=$_ge1rc; depois do edit: '$_ge1_next')"; sed -n '1,30p' "$_r/ge1.log"; sed -n '1,40p' "$_r/gh/calls.log"; fi
      R_EDIT_MODE=notfound
      _ge2rc=0; _r_pubrun "$_r/ge2.log" false || _ge2rc=$?
      if [ "$_ge2rc" -ne 0 ] && grep -qiE 'not found|ausente' "$_r/ge2.log" && grep -q 'FAIL' "$_r/ge2.log" \
         && [ "$(cat "$_r/gh/edit-count" 2>/dev/null)" = "1" ] \
         && ! grep -qx 'STEP-18' "$_r/wt/$EV/.cut-state" && ! grep -q 'PUBLICADO' "$_r/ge2.log"; then
        ok "GE2 (controle vermelho): «release not found» no edit e recusa NOMEADA na 1.a chamada (ausencia nao e transporte: sem re-tentativa)"
        _red="$_red GE2"
      else bad "GE2: a ausencia no edit nao virou recusa nomeada imediata (rc=$_ge2rc; edits=$(cat "$_r/gh/edit-count" 2>/dev/null))"; sed -n '1,20p' "$_r/ge2.log"; fi
      R_EDIT_MODE=reset-never
      _ge3rc=0; _r_pubrun "$_r/ge3.log" false || _ge3rc=$?
      _ge3n="$(cat "$_r/gh/edit-count" 2>/dev/null || echo 0)"
      if [ -f "$_r/gh/runaway" ]; then bad "GE3: gh_release_edit_idem passou de 40 chamadas — laco SEM teto"
      elif [ "$_ge3rc" -ne 0 ] && [ "$_ge3n" -ge 2 ] && grep -q 'FAIL' "$_r/ge3.log" \
           && grep -q 'gh release edit' "$_r/ge3.log" \
           && ! grep -qx 'STEP-18' "$_r/wt/$EV/.cut-state" && ! grep -q 'PUBLICADO' "$_r/ge3.log" \
           && [ "$(cat "$_r/gh/ga-draft")" = "false" ]; then
        ok "GE3 (controle vermelho): transporte com o estado pedido NUNCA alcancado: $_ge3n tentativa(s), recusa no teto com a rota (gh release edit) e o passo 18 nao marca"
        _red="$_red GE3"
      else bad "GE3: transporte sem o estado pedido nao re-tentou/recusou no teto (rc=$_ge3rc; edits=$_ge3n)"; sed -n '1,20p' "$_r/ge3.log"; fi
      # GE4 — o edit responde um erro da API que NAO e transporte nem ausencia (HTTP 422):
      # recusa NOMEADA na 1.a chamada, sem re-tentativa; o passo 18 nao marca e o Release
      # fica como estava.
      R_EDIT_MODE=other
      _ge4rc=0; _r_pubrun "$_r/ge4.log" false || _ge4rc=$?
      _ge4n="$(cat "$_r/gh/edit-count" 2>/dev/null || echo 0)"
      if [ "$_ge4rc" -ne 0 ] && [ "$_ge4n" = "1" ] && grep -qF 'NAO e transporte' "$_r/ge4.log" \
         && grep -qF 'HTTP 422: Validation Failed' "$_r/ge4.log" && grep -q 'FAIL' "$_r/ge4.log" \
         && ! grep -qx 'STEP-18' "$_r/wt/$EV/.cut-state" && ! grep -q 'PUBLICADO' "$_r/ge4.log" \
         && [ "$(cat "$_r/gh/ga-draft")" = "false" ]; then
        ok "GE4 (controle vermelho): um erro do edit que NAO e transporte (HTTP 422) e recusa NOMEADA na 1.a chamada, sem re-tentativa; o passo 18 nao marca"
        _red="$_red GE4"
      else bad "GE4: o erro que nao e transporte nao virou recusa nomeada imediata (rc=$_ge4rc; edits=$_ge4n)"; sed -n '1,20p' "$_r/ge4.log"; fi
      R_EDIT_MODE=ok; _r_gh 0 true false
      git -C "$_r/wt" tag -d v1.4.2 >/dev/null 2>&1 || bad "R: limpeza da tag local falhou"
      git -C "$_r/wt" push -q origin :refs/tags/v1.4.2 2>/dev/null || bad "R: limpeza da tag remota falhou"
    else bad "R6: tag/push da fixture falhou"; fi
    rm -f -- "$_r/wt/$EV/CANDIDATE.sha" "$_r/wt/$EV/.tag-push-epoch"
    _r_state 0

    # =======================================================================
    say "T. o CUT REAL num PSEUDO-TERMINAL (script + uma linha por segundo)"
    if ! command -v script >/dev/null 2>&1; then
      bad "T: o comando script esta ausente — o ensaio com pseudo-terminal nao rodou"
    else
      _r_state 0
      if _r_pty "$_r/t1.log" --g0-only && grep -q 'G0 verde (--g0-only)' "$_r/t1.log"; then
        ok "T1: G0 real verde num pseudo-terminal"
      else bad "T1: G0 real no pty falhou"; tr -d '\r' < "$_r/t1.log" | sed -n '1,20p'; fi
      _r_state 0
      _t2_from="$(git -C "$_r/wt" rev-parse HEAD)"
      if _r_pty "$_r/t2.log" --from 2 --until 2 \
         && grep -q 'AVISO: --from 2 PULA passo(s) NAO concluido(s): 1' "$_r/t2.log" \
         && grep -q 'Enter para confirmar que releu' "$_r/t2.log" \
         && grep -q 'bump e no-op' "$_r/t2.log" \
         && grep -q 'PARADO depois do passo 2' "$_r/t2.log" \
         && grep -qx 'STEP-2' "$_r/wt/$EV/.cut-state" && ! grep -qx 'STEP-1' "$_r/wt/$EV/.cut-state" \
         && grep -qx "SHA-2P $_t2_from" "$_r/wt/$EV/.cut-state" \
         && grep -qx "SHA-2 $_t2_from" "$_r/wt/$EV/.cut-state" \
         && [ "$(git -C "$_r/wt" rev-parse HEAD)" = "$_t2_from" ] \
         && [ "$(git -C "$_r/origin.git" rev-parse refs/heads/main)" = "$_t2_from" ]; then
        ok "T2: passo 2 REAL num pty: o pulo do 1 e nomeado, o Enter e lido do terminal, o bump --stable REAL e no-op (SHA-2P = SHA-2 = HEAD; main parado) e o --until para"
      else bad "T2: passo 2 real no pty falhou"; tr -d '\r' < "$_r/t2.log" | sed -n '1,40p'; fi
      # T2x — um commit de bump em main LOCAL, com o .cut-state da retomada entre os passos
      # 2 e 3 (a forma que a rc aceitava e pushava no 3): no GA o G0 recusa, e nada sobe.
      printf 'STEP-1\nSHA-1 %s\nSTEP-2\nSHA-2P %s\n' "$_t2_from" "$_t2_from" > "$_r/wt/$EV/.cut-state"
      if printf '\n<!-- TEST ONLY: carimbo de bump -->\n' >> "$_r/wt/SBOM.md" \
         && git -C "$_r/wt" -c commit.gpgsign=false commit -q -am "release: v1.4.2"; then
        printf 'SHA-2 %s\n' "$(git -C "$_r/wt" rev-parse HEAD)" >> "$_r/wt/$EV/.cut-state"
        if _r_cut "$_r/t2x.log" --until 3; then bad "T2x: um commit de bump em main local passou pelo G0 do GA"
        elif grep -qE 'registra um commit de bump|SBOM[.]md|fora de uma retomada conhecida' "$_r/t2x.log" \
             && ! grep -qx 'STEP-3' "$_r/wt/$EV/.cut-state" \
             && [ "$(git -C "$_r/origin.git" rev-parse refs/heads/main)" = "$_t2_from" ]; then
          ok "T2x (controle vermelho): um commit de bump em main local e recusado no G0 do GA, e nada sobe para o remoto"
          _red="$_red T2x"
        else bad "T2x: recusa sem o motivo (ou main subiu)"; sed -n '1,12p' "$_r/t2x.log"; fi
        git -C "$_r/wt" reset -q --hard "$_t2_from" || bad "T2x: voltar ao HEAD da fixture falhou"
      else bad "T2x: o commit de bump da fixture falhou"; fi
      _r_state 0
      if [ -f "$SCRATCH/w.sh" ]; then
        if ( _pty "$SCRATCH/t3.log" env W_LOAD="9.50 4" bash "$SCRATCH/w.sh" ) \
           && grep -q 'AVISO: a maquina esta CARREGADA' "$SCRATCH/t3.log"; then
          ok "T3: aviso de carga alta num pty: avisa e le o Enter do terminal"
        else bad "T3: aviso de carga no pty falhou"; tr -d '\r' < "$SCRATCH/t3.log" | sed -n '1,10p'; fi
      else bad "T3: $SCRATCH/w.sh ausente (a secao W nao rodou)"; fi
      # T4 — o passo 16 (o irreversivel) le o SIM do TERMINAL: um Enter, ou «sim» minusculo,
      # abortam, e a tag NAO sobe. Estado: passos 1-15 feitos, a tag do GA so local.
      _r_state 15
      git -C "$_r/wt" rev-parse HEAD > "$_r/wt/$EV/CANDIDATE.sha"
      if git -C "$_r/wt" -c tag.gpgSign=false tag -a -m "TEST ONLY: GA fixture" v1.4.2; then
        _r_gh 0 true false
        for _t4 in "" sim; do
          _t4l="$_r/t4-${_t4:-enter}.log"
          if _PTY_LINE="$_t4" _r_pty "$_t4l" --until 16; then bad "T4: '${_t4:-Enter}' no passo 16 seguiu"
          elif grep -q 'digite SIM (MAIUSCULO) para confirmar' "$_t4l" && grep -q 'abortado por voce' "$_t4l" \
               && [ -z "$(git -C "$_r/origin.git" for-each-ref refs/tags/v1.4.2)" ] \
               && ! grep -qx 'STEP-16' "$_r/wt/$EV/.cut-state"; then
            ok "T4 (controle vermelho): '${_t4:-Enter}' no prompt do passo 16, num pty, aborta e a tag NAO sobe"
          else bad "T4: o passo 16 no pty nao abortou como devia com '${_t4:-Enter}'"; tr -d '\r' < "$_t4l" | sed -n '1,30p'; fi
        done
        # T4c — o SIM digitado no terminal PASSA do prompt (a leitura e do pty, nao de um
        # EOF): o pre-push confere a assinatura da tag, e a tag NAO assinada da fixture e
        # recusada ali — nada sobe.
        if _PTY_LINE=SIM _r_pty "$_r/t4-sim.log" --until 16; then bad "T4c: tag NAO assinada passou pelo pre-push do passo 16"
        elif grep -q 'digite SIM (MAIUSCULO) para confirmar' "$_r/t4-sim.log" \
             && grep -q 'pre-push: assinatura da tag nao verifica' "$_r/t4-sim.log" \
             && ! grep -q 'abortado por voce' "$_r/t4-sim.log" \
             && [ -z "$(git -C "$_r/origin.git" for-each-ref refs/tags/v1.4.2)" ] \
             && ! grep -qx 'STEP-16' "$_r/wt/$EV/.cut-state"; then
          ok "T4c: o SIM digitado no pty passa do prompt; o pre-push recusa a tag nao assinada e nada sobe"
        else bad "T4c: o SIM no pty nao chegou ao pre-push como devia"; tr -d '\r' < "$_r/t4-sim.log" | sed -n '1,30p'; fi
        git -C "$_r/wt" tag -d v1.4.2 >/dev/null 2>&1 || bad "T4: limpeza da tag local falhou"
      else bad "T4: a tag local da fixture falhou"; fi
      rm -f -- "$_r/wt/$EV/CANDIDATE.sha"
      _r_state 0
    fi

    # R8f — a arvore da rc.1 CONGELADA no G0 real: um hook mudado depois da tag da rc.1 e
    # recusado pelo nome, antes do passo 1.
    printf '\n# TEST ONLY: ensaio R8f\n' >> "$_r/wt/.claude/hooks/check_workflow_launch.py"
    if git -C "$_r/wt" -c commit.gpgsign=false commit -q -am "TEST ONLY: hook muda depois da rc" \
       && git -C "$_r/wt" push -q origin HEAD:refs/heads/main 2>/dev/null; then
      if _r_cut "$_r/r8f.log" --g0-only; then bad "R8f: G0 real aceitou hook mudado depois da rc.1"
      elif grep -q '.claude/hooks/check_workflow_launch.py' "$_r/r8f.log" \
           && grep -q 'mudou caminho FORA de CLAUDE.md' "$_r/r8f.log"; then
        ok "R8f (controle vermelho): G0 real recusa hook mudado depois da tag da v1.4.2-rc.1, pelo nome"
        _red="$_red R8f"
      else bad "R8f: G0 real recusou sem nomear o hook"; sed -n '1,10p' "$_r/r8f.log"; fi
    else bad "R8f: commit/push da mutacao no clone falhou"; fi
    _r_restore
    # R8p — a sonda das condicoes no G0 real recusa uma condicao FALSA pelo nome, com a
    # arvore ainda congelada (o plano NUMERADO perde a decisao OQ-8 que as condicoes citam).
    # Sem o REPORT-ONLY: o que se confere e a linha da condicao.
    if python3 - "$_r/wt/.claude/plans/PLAN-193-release-v1-4-2-opus55-fasttrack.md" <<'PYR8' \
       && git -C "$_r/wt" -c commit.gpgsign=false commit -q -am "TEST ONLY: plano sem a OQ-8" \
       && git -C "$_r/wt" push -q origin HEAD:refs/heads/main 2>/dev/null
import re, sys
p = sys.argv[1]
t = open(p, encoding="utf-8").read()
n = re.sub(r"(?ms)^- OQ-8\b.*?(?=^- )", "", t, count=1)
if n == t:
    raise SystemExit("o plano da fixture nao tem a OQ-8")
open(p, "w", encoding="utf-8").write(n)
PYR8
    then
      if ( cd "$_r/wt" && env PATH="$_r/bin:$PATH" GNUPGHOME="$GH" HOME="$SCRATCH/rhome" \
             TMPDIR="$_r/tmp" R_GH="$_r/gh" R_PUBAT="$(_r_pub 30)" \
             GA_SELFTEST=1 GA_SELFTEST_SCRATCH="$SCRATCH" GA_SELFTEST_SIGNER_FPR="$FPR" \
             bash "$PLAN_DIR/OWNER-GA-CUT.sh" --g0-only ) < /dev/null > "$_r/r8p.log" 2>&1; then
        bad "R8p: G0 real aceitou o plano sem a decisao que as condicoes citam"
      elif grep -qF 'FAIL C12-plan-decisions: as condicoes citam OQ-8' "$_r/r8p.log" \
           && grep -q 'a sonda das condicoes achou afirmacao FALSA' "$_r/r8p.log"; then
        ok "R8p (controle vermelho): G0 real recusa uma condicao FALSA contra o candidato (a OQ-8), nomeando a afirmacao"
      else bad "R8p: G0 real recusou sem nomear a condicao"; grep -E 'FAIL|sonda' "$_r/r8p.log" | sed -n '1,8p'; fi
    else bad "R8p: commit/push da mutacao no clone falhou"; fi
    _r_restore
    # R9 — o driver fora da 1.4.2 (o release.sh mudou depois da rc.1): recusa nomeada, e a
    # rota NAO e a da rc (assinar a relmeta): no GA a arvore da rc.1 e CONGELADA.
    if python3 - "$_r/wt/.claude/scripts/local/release.sh" <<'PYR9' \
       && git -C "$_r/wt" -c commit.gpgsign=false commit -q -am "TEST ONLY: driver na 1.4.1" \
       && git -C "$_r/wt" push -q origin HEAD:refs/heads/main 2>/dev/null
import re, sys
p = sys.argv[1]
t = open(p, encoding="utf-8").read()
open(p, "w", encoding="utf-8").write(re.sub(r'(?m)^TARGET_BASE="[^"]*"$', 'TARGET_BASE="1.4.1"', t, count=1))
PYR9
    then
      if _r_cut "$_r/r9.log" --g0-only; then bad "R9: G0 real aceitou o driver fora da 1.4.2"
      elif grep -q "TARGET_BASE do release.sh e '1.4.1', esperado 1.4.2" "$_r/r9.log" \
           && ! grep -q 'relmeta/' "$_r/r9.log"; then
        ok "R9 (controle vermelho): G0 real recusa o driver fora da 1.4.2, sem a rota da rc (a arvore da rc.1 e congelada)"
      else bad "R9: recusa sem o motivo (ou com a rota da relmeta da rc)"; sed -n '1,8p' "$_r/r9.log"; fi
    else bad "R9: commit/push da mutacao no clone falhou"; fi
    _r_restore
    # R9b — o release.sh mudou depois da rc.1 com o TARGET_BASE INTACTO (um comentario a
    # mais): o manifesto ADR-192 recusa pelo nome. O R9 nao chega a esta recusa (o
    # TARGET_BASE e conferido antes dela); o R1 e o gemeo (o release.sh da arvore).
    if printf '\n# TEST ONLY: ensaio R9b (o sha do driver muda, o TARGET_BASE nao)\n' \
         >> "$_r/wt/.claude/scripts/local/release.sh" \
       && git -C "$_r/wt" -c commit.gpgsign=false commit -q -am "TEST ONLY: driver com um comentario a mais" \
       && git -C "$_r/wt" push -q origin HEAD:refs/heads/main 2>/dev/null; then
      if _r_cut "$_r/r9b.log" --g0-only; then bad "R9b: G0 real aceitou o release.sh fora do manifesto ADR-192"
      elif grep -q 'sha do release.sh nao bate com o manifesto ADR-192' "$_r/r9b.log" \
           && ! grep -q 'TARGET_BASE do release.sh' "$_r/r9b.log"; then
        ok "R9b (controle vermelho): G0 real recusa o release.sh que nao bate com o manifesto ADR-192 (TARGET_BASE intacto), pelo nome"
      else bad "R9b: recusa sem o motivo do manifesto"; sed -n '1,8p' "$_r/r9b.log"; fi
    else bad "R9b: commit/push da mutacao no clone falhou"; fi
    _r_restore
  else bad "R: clone bare/remoto local falhou"; fi
else printf '  (R, PUB, GE e T pulados: sem clone, sem chave ou sem base)\n'; fi

# ===========================================================================
say "D. controles VERMELHOS — cada gate tem de RECUSAR o defeito plantado"

# D1 (CM-03) — dois vereditos no mesmo arquivo e ambiguidade, nao aprovacao.
if [ -n "$CLONE" ] && [ -f "$CLONE/$EV/verdict-ga-1.txt" ]; then
  _d1="$SCRATCH/d1"; mkdir -p "$_d1"; cp "$CLONE/$EV/verdict-ga-1.txt" "$_d1/v.txt"
  printf 'VERDICT: NO-GO segunda linha plantada\n' >> "$_d1/v.txt"
  _n="$(grep -cE '^VERDICT:' "$_d1/v.txt")"
  if [ "$_n" -gt 1 ]; then ok "D1 CM-03: dois VERDICT sao detectados ($_n linhas)"
  else bad "D1 CM-03: o plant nao produziu duas linhas"; fi
fi

# D2 (CM-15) — caminho pessoal absoluto no material assinado tem de abortar.
_d2="$SCRATCH/d2"; mkdir -p "$_d2"
printf '#!/bin/bash\necho %s/algum/lugar\n' "$(printf '/%s/vitima' Users)" > "$_d2/planted.sh"
_hp="$(printf '/%s/' Users)"
if grep -q -- "$_hp" "$_d2/planted.sh"; then
  ok "D2 CM-15: o matcher de home absoluto dispara no plant"
else bad "D2 CM-15: o matcher NAO viu o plant"; fi

# D3 (CM-04) — `git status` que MORRE nao pode virar "arvore limpa".
_d3="$SCRATCH/d3"; mkdir -p "$_d3/bin"
printf '#!/bin/bash\nexit 42\n' > "$_d3/bin/git"; chmod 0755 "$_d3/bin/git"
_out="$SCRATCH/d3.out"
if PATH="$_d3/bin:$PATH" bash -c '
  f=$(mktemp)
  if ! git status --porcelain > "$f"; then echo "RECUSADO"; exit 1; fi
  echo "ACEITOU-VACUO"' > "$_out" 2>&1; then
  bad "D3 CM-04: um git quebrado passou como arvore limpa"
else
  grep -q RECUSADO "$_out" && ok "D3 CM-04: produtor com rc!=0 vira recusa nomeada" \
    || bad "D3 CM-04: recusa sem a mensagem esperada"
fi

# D4 (CM-05) — `| head` sob pipefail mata o produtor; a leitura para arquivo nao.
_d4="$SCRATCH/d4.txt"
python3 -c "
import sys
with open('$_d4','w') as f:
    f.write('MARCADOR\n')
    f.write('x'*1024*1024)
    f.write('\n')
"
# Forma DOENTE 1: produtor grande canalizado para `head`.
_r1=0; ( set -o pipefail; cat "$_d4" | head -2 | grep -q MARCADOR ) || _r1=$?
# Forma DOENTE 2: trocar `head` por `sed` NAO cura — quem fecha o pipe cedo
# e o proprio `grep -q`. Este e o ponto do controle: a cura nao e o comando,
# e parar de canalizar.
_r2=0; ( set -o pipefail; sed -n '1,2p' "$_d4" | grep -q MARCADOR ) || _r2=$?
# Forma CURADA: ler para arquivo com rc conferido, e so entao filtrar.
_r3=0
( set -o pipefail
  sed -n '1,2p' "$_d4" > "$_d4.head" || exit 9
  grep -q MARCADOR "$_d4.head" ) || _r3=$?
if [ "$_r3" -eq 0 ] && [ "$_r1" -ne 0 ] && [ "$_r2" -ne 0 ]; then
  ok "D4 CM-05: as duas formas canalizadas morrem (rc $_r1 / $_r2) e a leitura para arquivo sobrevive (rc $_r3)"
elif [ "$_r3" -ne 0 ]; then
  bad "D4 CM-05: a forma CURADA falhou (rc $_r3) — a cura esta errada"
else
  bad "D4 CM-05: nenhuma forma canalizada falhou (rc $_r1 / $_r2) — o controle nao reproduz a classe"
fi

# D6 — a faixa do pin separa a versao PINADA de uma versao fora dela. O limite
# superior e EXCLUSIVO: a versao que o manifesto pina tem de estar DENTRO e o
# proprio limite superior tem de estar FORA (e o que um `npm update -g` produz).
_d6="$SCRATCH/d6.log"
if python3 - > "$_d6" 2>&1 <<'PY'
import importlib.util, json, pathlib, subprocess, sys
root = pathlib.Path(subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"], universal_newlines=True).strip())
spec = importlib.util.spec_from_file_location(
    "v", str(root / ".github/scripts/validate-pair-rail-verdict.py"))
v = importlib.util.module_from_spec(spec); spec.loader.exec_module(v)
lo, hi = v.parse_pin_range(root / ".claude/governance/codex-cli-pin.txt")
pinned = json.loads((root / ".claude/governance/codex-cli-pin-manifest.json")
                    .read_text(encoding="utf-8"))["package_version"]
pin_ok = v.semver_in_range(pinned, lo, hi)
edge_ok = v.semver_in_range(hi, lo, hi)
print("pinado=%s:%s limite-superior=%s:%s faixa=%s..%s" % (pinned, pin_ok, hi, edge_ok, lo, hi))
raise SystemExit(0 if (pin_ok and not edge_ok) else 1)
PY
then ok "D6: a versao pinada esta na faixa e o limite superior esta FORA ($(cat "$_d6"))"
else bad "D6: a faixa do pin nao separou pinado de fora-da-faixa ($(cat "$_d6"))"; fi

# D7 (CM-11) — baseline que nao reproduz a arvore tem de abortar o SIGN.
_d7="$SCRATCH/d7"; mkdir -p "$_d7"
printf 'PRE %s %s\n' "0000000000000000000000000000000000000000" "CHANGELOG.md" > "$_d7/bl"
_live="$(git hash-object -- CHANGELOG.md)"
if [ "$_live" != "0000000000000000000000000000000000000000" ]; then
  ok "D7 CM-11: baseline forjado difere do vivo — o SIGN abortaria"
else bad "D7 CM-11: o plant colidiu com o hash real (impossivel)"; fi

# D9-D14 — os gates NOVOS do GA: cada um tem de ter tido os seus controles VERMELHOS
# exercitados e verdes NESTE ensaio (uma secao pulada — sem chave, sem clone — nao prova
# nada). Onde cada um roda: H/R2h, FZ/R8f, E7/T2x, GE. D13-D14: a retomada do passo 11
# pelo corte inteiro (E3r: cada vermelho so conta com o gemeo positivo verde; os
# intrusos recusados PELO G0; o E3r3, o envelope adulterado re-derivado pelo passo 11) e
# o registry/latest/recibo do passo 18 (PUB, com o contra-exemplo PUBX).
_d_need() {  # $1 = rotulo do gate, $2.. = controles que tem de ter passado
  local _g="$1" _m="" _c; shift
  for _c in "$@"; do
    case " $_red " in *" $_c "*) : ;; *) _m="$_m $_c" ;; esac
  done
  if [ -z "$_m" ]; then ok "$_g: controles vermelhos exercitados e verdes ($*)"
  else bad "$_g: controle(s) vermelho(s) que NAO rodaram ou NAO ficaram verdes:$_m"; fi
}
_d_need "D9 hold ADR-103 da rc.1 (assert_rc_hold)" H2 H7 H11 H12 R2h
_d_need "D10 arvore da rc.1 congelada (assert_rc_tree_frozen)" fz-bump fz-rename R8f
_d_need "D11 bump do GA no-op (passo 2)" E7-commit E7-dirty T2x
_d_need "D12 gh_release_edit_idem (passos 18-19)" GE1 GE2 GE3 GE4
_d_need "D13 retomada do passo 11 pelo corte inteiro (G0 real; envelope re-derivado)" E3r-stray E3r-staged E3r3
_d_need "D14 passo 18: registry, latest e recibo do publish" PUB5 PUB6 PUB7-skipped PUB8 PUB9

# ===========================================================================
printf '\n===== RESULTADO: %s PASS, %s FAIL\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
