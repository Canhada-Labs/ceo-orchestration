#!/bin/bash
# CEREMONY-LINT: handwritten-exception: harness do kit de corte do GA v1.4.1, DERIVADO por
# .claude/plans/PLAN-192/derive-ga-kit-141.py do harness da rc.1 (test-rc1-kit.sh, escrito
# contra o corpus PLAN-188/ceremony-defect-corpus-S348.md). NAO edite a mao.
#
# test-ga-kit.sh — prova a TUBULACAO inteira do kit sem gastar uma unica
# invocacao de codex e sem tocar na arvore viva.
#
#   bash .claude/plans/PLAN-192/test-ga-kit.sh
#   bash .claude/plans/PLAN-192/test-ga-kit.sh --evidence-only
#
# O que ele faz, em ordem:
#   A. lint estatico: `bash -n` + `shellcheck -S warning` em todo shell do kit,
#      compilacao EM MEMORIA (sem .pyc) nos tres pythons do kit, e
#      `check-ceremony-script.py` exigindo ZERO achado BLOCKING nos arquivos do kit.
#   B. runner ponta a ponta num CLONE descartavel, com um codex STUB
#      (`CODEX_BIN`): prova diff -> redator -> controles -> verdito ->
#      PROVENANCE -> MANIFEST sem gastar codex.
#   C. gerador de envelope: `--stage fields` e `--stage envelope` com uma chave
#      GPG DESCARTAVEL num homedir temporario.
#   D. UM CONTROLE VERMELHO por classe do corpus que este kit cura: cada um
#      planta o defeito e exige que o gate RECUSE. Um controle que fica verde
#      sobre o defeito e uma falha do harness, nao um sucesso.
#
# GA (derive-ga-kit-141.py): os controles da relmeta da rc.1 (D5, D8) sairam; entraram
#   B.  o kit do GA e copiado do DISCO para o upstream da fixture (lista FECHADA, antes
#       do commit do candidato): o ensaio exercita os arquivos derivados mesmo que
#       ainda NAO estejam commitados; a PROVENANCE declara as 3 pathspecs sem mudanca
#       desde o candidato da rc.1;
#   B4. controle vermelho da conferencia: um candidato que muda um arquivo da parte 1
#       e declarado MUDOU na parte 1 (e so nela), no prompt e na PROVENANCE;
#   G.  o congelamento da arvore da rc.1 (assert_rc_tree_frozen): CLAUDE.md + planos
#       numerados passam; um plano NAO numerado e um hook sao recusados pelo nome;
#   H.  o hold ADR-103 da rc.1 (assert_rc_hold) com uma tag assinada pela chave
#       descartavel, um remoto local e um `gh` stub: positivo + sete vermelhos;
#   W.  o aviso de carga antes do preflight (warn_load): alta pede Enter, baixa nao;
#   K.  o kit tem de estar commitado (assert_kit_committed): untracked e modificado
#       sao recusados pelo nome;
#   R.  o OWNER-GA-CUT.sh REAL (o script inteiro; `--g0-only` ou estados de retomada
#       plantados no .cut-state) contra as tags reais da rc.1, num clone com remoto
#       bare local e `gh` stub: G0 verde; hold de 1 h, argumentos invalidos
#       (--from abc/99, --until 0, --restamp), arquivo untracked no plano e hook
#       mudado depois da rc.1 sao recusados; as retomadas entre os passos 11 e 13 e
#       depois do 16 (Release em DRAFT do release.yml) passam, com os vermelhos de
#       cada uma; o banner de PUBLICADO so sai com o passo 20 concluido;
#   T.  o CUT REAL num PSEUDO-TERMINAL (`script`, Enter periodico): o G0 e o passo 2
#       inteiro (a leitura do Enter e o bump REAL no-op, com --from 2 --until 2), e o
#       aviso de carga alta lendo o Enter do terminal;
#   S.  o teto da espera de CI e 150 min por padrao e o vermelho nomeia o rerun;
#   C.  (acrescimo) tool_versions.claude_code MEDIDO: um `claude` STUB no PATH (o
#       claude real nunca roda) e o vermelho de `claude --version` ilegivel;
#   E3b a retomada do passo 11 com o .asc so no backup do HOME;
#   E4  o bump --stable TEM de ser no-op; E4r: --restamp nao e (a recusa nao e vacua);
#   E7  o passo 2 verbatim com driver STUB: commit ou arquivo novo => recusa antes de
#       qualquer fetch/merge/push, e o HEAD nao anda;
#   Y.  o recheck do passo 19 verbatim: push alheio depois da tag passa com AVISO,
#       main revertido para antes da tag e recusa;
#   V.  wait_ci_green verbatim: `gh run view` vazio ou ilegivel vira FAIL nomeado;
#   Z.  o passo 5 verbatim mantem byte a byte um CANDIDATE.sha que ja aponta o
#       candidato (o re-pass rodado antes da cerimonia).
# Rodada 2 do kit (achados de revisao, cada um com controle vermelho):
#   R3  --from/--until SEM valor e recusa nomeada (antes: rc 1 mudo);
#   R5c/R5d o .cut-state de tentativa anterior (passo 5 feito, HEAD != candidato);
#   R6d/R6d2/R6d3 push da tag sem o marcador do 16 (reconhecido so com o objeto local
#       no remoto) e tag local sem o 15 (a recusa nomeia `git tag -d`);
#   R6e/R6e2 retomada depois do 16 com main que andou (AVISO) x main revertido;
#   S   o conselho de rerun nos preflights 1 e 15 e o run AGENDADO declarado;
#   L   CLAUDE.md no limite do validate-governance.sh (a regra espelhada conferida);
#   P   o Scope assinado da tag cobre os planos e ADRs da faixa;
#   X   passo 17: toda conclusao terminal != success recusa na 1.a volta;
#   Q   passo 19: sem .tag-push-epoch o piso e a data da tag, nunca 0.
# Rodada 3 do kit:
#   R5e/R5f a tentativa parcial arquivada DENTRO do plano e recusada no G0; a rota
#       documentada (arquivo FORA do repositorio) deixa o G0 verde, o passo 6 como o
#       primeiro pendente e o runner sem evidencia anterior;
#   H7/H8 falha de transporte do gh no hold tem nome proprio; «release not found» e
#       ausencia;
#   Z3/Z4 o passo 5 recusa o candidato que nao e o commit que o passo 4 conferiu; sem o
#       registro, AVISO;
#   X   o vermelho do passo 17 nomeia o rerun do npm-publish.yml e o prazo do veredito;
#   S   o conselho dos preflights nomeia o run ainda rodando e a suite serial.
# A1 compila os pythons EM MEMORIA (nenhum __pycache__ escrito na arvore viva).
#
# GNUPGHOME: o runner verifica `git tag -v v1.4.0`. Se o chamador nao passar um
# GNUPGHOME isolado, o harness monta um SO-PUBLICO no scratch a partir de
# .claude/trust/owner.asc — nunca o chaveiro real. GA_KIT_SCRATCH_PARENT troca o pai
# do scratch (padrao /tmp).
#
# INVARIANTE 8 do PLAN-188 (classe CM-12): este harness NUNCA planta um
# veredito `APPROVE`/`GO` sintetico para destravar um caso verde. O stub do
# codex EMITE `VERDICT: GO` porque e um stub de REVISOR, e essa e a saida que
# um revisor produz; os casos que exercitam RECUSA plantam o defeito e
# esperam recusa.
set -uo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd -P )"
ROOT="$( cd "$SCRIPT_DIR" && git rev-parse --show-toplevel )"
cd "$ROOT" || exit 2

PLAN_DIR=".claude/plans/PLAN-192"
EV="$PLAN_DIR/repass-ga"
SHELLS="
$PLAN_DIR/OWNER-GA-CUT.sh
$PLAN_DIR/test-ga-kit.sh
$EV/run-ga-repass.sh
"
PYS="
$PLAN_DIR/gen-envelope-ga.py
$PLAN_DIR/derive-ga-kit-141.py
$PLAN_DIR/derive-kit-141.py
"

PASS=0; FAIL=0
ok()   { PASS=$((PASS+1)); printf '  PASS  %s\n' "$*"; }
bad()  { FAIL=$((FAIL+1)); printf '  FAIL  %s\n' "$*"; }
say()  { printf '\n===== %s\n' "$*"; }

# Scratch CURTO por padrao: o socket do gpg-agent estoura o limite de sun_path do
# macOS (~104 bytes) num caminho longo. Medido: "can't connect to the gpg-agent:
# File name too long". GA_KIT_SCRATCH_PARENT troca o pai (um ensaio confinado ao
# scratchpad de uma sessao, por exemplo); com um pai longo o homedir GPG da secao C
# ganha um ALIAS curto em /tmp (um symlink, removido na saida) — o chaveiro e os
# sockets ficam fisicamente DENTRO do scratch.
SCRATCH_PARENT="${GA_KIT_SCRATCH_PARENT:-/tmp}"
[ -d "$SCRATCH_PARENT" ] || { echo "GA_KIT_SCRATCH_PARENT nao e diretorio: $SCRATCH_PARENT" >&2; exit 2; }
SCRATCH="$(mktemp -d "$SCRATCH_PARENT/gakit.XXXXXX")" || { echo "mktemp falhou" >&2; exit 2; }
# O claude REAL nunca roda neste ensaio: um sentinela no inicio do PATH falha alto se
# algo o chamar sem o stub da secao C (o gerador MEDE `claude --version`).
mkdir -p "$SCRATCH/no-claude" \
  && printf '#!/bin/bash\necho "HARNESS: claude real chamado sem stub" >&2\nexit 97\n' > "$SCRATCH/no-claude/claude" \
  && chmod 0755 "$SCRATCH/no-claude/claude" || { echo "sentinela do claude falhou" >&2; exit 2; }
PATH="$SCRATCH/no-claude:$PATH"; export PATH
GH=""; GH_ALIAS=""; PUBGH=""
cleanup() {
  # Os gpg-agent dos homedirs descartaveis morrem SEMPRE (inclusive numa falha) e o
  # alias curto sai; o scratch so e preservado quando algo falhou.
  local _h
  for _h in "${GH:-}" "${PUBGH:-}"; do
    [ -n "$_h" ] || continue
    if ! gpgconf --homedir "$_h" --kill all >/dev/null 2>&1; then :; fi
  done
  if [ -n "${GH_ALIAS:-}" ] && [ -L "$GH_ALIAS" ]; then rm -f -- "$GH_ALIAS"; fi
  if [ "$FAIL" -ne 0 ]; then
    printf 'Harness incompleto/falho: fixtures e logs preservados em %s\n' "$SCRATCH" >&2
    return
  fi
  [ -n "${CLONE:-}" ] && [ -d "$CLONE" ] && chmod -R u+w "$CLONE" 2>/dev/null
  rm -rf -- "$SCRATCH" 2>/dev/null
}
trap cleanup EXIT

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
plan = root / ".claude/plans/PLAN-192"
spec = importlib.util.spec_from_file_location("rc1_generator", plan / "gen-envelope-ga.py")
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
        "CONDITIONS-ga.reviewed.md sha256 %s\nRUNNER-OVERALL: rc=0\n"
        % (candidate, pin["package_version"], digest, cond_hash), encoding="utf-8")
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
        (ev / "verdict-ga-3.txt").write_text(text)
        seal()
        refuses("veredito ambiguo/ilegivel", lambda: gen.build_fields(candidate, conditions), "VERDICT")
    prepare()
    (ev / "verdict-ga-3.txt").unlink()
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
    refuses("MANIFEST omite artefato", lambda: gen.build_fields(candidate, conditions), "exatamente os 19")
    prepare()
    prov = ev / "PROVENANCE-ga.md"
    prov.write_text(prov.read_text().replace("RUNNER-OVERALL: rc=0", "RUNNER-OVERALL: rc=1"))
    seal()
    refuses("runner incompleto com vereditos GO", lambda: gen.build_fields(candidate, conditions), "RUNNER-OVERALL")
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
for number, artifact in enumerate(("verdict-ga-1.txt", "transcript-ga-3.log", "payload-ga-2.raw.txt", "MANIFEST-ga.sha256.tmp", gen.REVIEWED_CONDITIONS)):
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
for f in $SHELLS; do
  [ -f "$f" ] || { bad "ausente: $f"; continue; }
  if bash -n "$f" 2>/dev/null; then ok "bash -n $(basename "$f")"; else bad "bash -n $(basename "$f")"; fi
  if command -v shellcheck >/dev/null 2>&1; then
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
_nb="$(python3 - "$_cl" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
mine = [f for f in d["files"]
        if "/PLAN-192/" in f["file"] or f["file"].startswith(".claude/plans/PLAN-192/")]
bl = [(f["file"], x) for f in mine for x in f["findings"] if x["sev"] == "BLOCKING"]
for p, x in bl:
    print("BLOCKING %s %s L%s %s" % (p, x["rule"], x["line"], x["msg"]), file=sys.stderr)
print(len(bl))
PY
)" || _nb="ERRO"
if [ "$_nb" = "0" ]; then ok "ceremony-lint: 0 BLOCKING nos arquivos do kit"
else bad "ceremony-lint: $_nb achado(s) BLOCKING"; fi

# ===========================================================================
say "B. runner ponta a ponta num clone descartavel, com codex STUB"
fixture_git_identity() {
  git -C "$1" config --local user.name "rc1 kit fixture" \
    && git -C "$1" config --local user.email "rc1-kit@invalid" \
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
# O kit do GA pode estar UNTRACKED na arvore viva (derivado e ainda nao
# commitado): `git diff HEAD` nao o carrega e um clone de HEAD nao o ve. A lista
# FECHADA abaixo e copiada do DISCO para o upstream da fixture ANTES do commit do
# candidato — o ensaio exercita os bytes que estao no disco, commitados ou nao.
KIT_FILES="
$PLAN_DIR/OWNER-GA-CUT.sh
$PLAN_DIR/gen-envelope-ga.py
$PLAN_DIR/test-ga-kit.sh
$PLAN_DIR/derive-ga-kit-141.py
$EV/run-ga-repass.sh
$EV/CONDITIONS-ga.md
$EV/README-ga.md
$EV/.gitignore
"
if [ "$_fixture_ok" -eq 1 ]; then
  for _kf in $KIT_FILES; do
    if [ ! -f "$ROOT/$_kf" ] || [ -L "$ROOT/$_kf" ]; then
      bad "kit: $_kf ausente ou nao-regular no disco"; _fixture_ok=0; break
    fi
    mkdir -p "$UPSTREAM/$(dirname "$_kf")" && cp -- "$ROOT/$_kf" "$UPSTREAM/$_kf" \
      && git -C "$UPSTREAM" add -- "$_kf" || { _fixture_ok=0; break; }
  done
  [ "$_fixture_ok" -eq 1 ] && ok "kit do GA copiado do disco para o upstream da fixture (lista fechada de 8)"
fi
if [ "$_fixture_ok" -eq 1 ]; then
  git -C "$UPSTREAM" commit --quiet --allow-empty -m "TEST ONLY: prepared candidate before stub review" \
    || _fixture_ok=0
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
    # Stub do codex: le o payload da stdin, escreve o veredito no arquivo
    # apontado por --output-last-message. NAO e um plant de aprovacao: e o
    # que um revisor emite. Os casos de RECUSA estao no bloco D.
    STUB="$SCRATCH/codex-stub"
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
printf 'STUB REVIEW: li %s bytes de payload pela stdin.\n' "$bytes" > "$out"
printf 'VERDICT: GO-WITH-CONDITIONS cobertura declarada no README-ga.\n' >> "$out"
printf 'stub: payload de %s bytes\n' "$bytes"
STUBEOF
    chmod 0755 "$STUB"
    _run="$SCRATCH/runner.log"
    # O chamador fornece um GNUPGHOME ISOLADO com somente a chave PUBLICA
    # do Owner para `git tag -v v1.4.0`. Nunca ler o chaveiro real.
    # Sem GNUPGHOME do chamador, um SO-PUBLICO no scratch a partir do owner.asc
    # rastreado (o common.conf vazio impede o keyboxd). A importacao pode reclamar do
    # agente (caminho longo) e ainda assim importar: quem decide e o `git tag -v`.
    _test_gnupg="${GNUPGHOME:-}"
    if [ -z "$_test_gnupg" ]; then
      PUBGH="$SCRATCH/gnupg-pub"; mkdir -p "$PUBGH"; chmod 700 "$PUBGH"; : > "$PUBGH/common.conf"
      GNUPGHOME="$PUBGH" gpg --batch --quiet --import "$ROOT/.claude/trust/owner.asc" >/dev/null 2>&1
      if GNUPGHOME="$PUBGH" git -C "$ROOT" tag -v v1.4.0 >/dev/null 2>&1; then
        _test_gnupg="$PUBGH"; ok "GNUPGHOME so-publico montado no scratch (owner.asc)"
      else bad "o GNUPGHOME so-publico do scratch nao verifica a v1.4.0"; exit 1; fi
    fi
    if ( cd "$CLONE" && CODEX_BIN="$STUB" CODEX_MODEL=stub-model HOME="$SCRATCH/fakehome" \
         GNUPGHOME="$_test_gnupg" \
         bash "$EV/run-ga-repass.sh" ) > "$_run" 2>&1; then
      ok "runner completou as 3 partes (rc 0)"
    else
      bad "runner rc!=0"; sed -n '1,25p' "$_run"
    fi
    _ml="$(grep -c . "$CLONE/$EV/MANIFEST-ga.sha256" 2>/dev/null || echo 0)"
    if [ "$_ml" = "19" ]; then ok "MANIFEST-ga com 19 entradas"
    else bad "MANIFEST-ga com $_ml entradas (esperado 19)"; fi
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
    _same="$(grep -c '^  - diff-ga-[123].patch: sem mudanca na pathspec desde o candidato da rc.1 (7602fbe4)$' "$CLONE/$EV/PROVENANCE-ga.md" 2>/dev/null)" || _same=0
    if [ "$_same" = "3" ]; then ok "B: a PROVENANCE declara as 3 pathspecs sem mudanca desde o candidato da rc.1"
    else bad "B: a PROVENANCE declara $_same pathspec(s) sem mudanca desde a rc.1 (esperado 3)"; fi
    if grep -q "THIS part's pathspec against the rc.1 candidate: yes - no file of this part's pathspec differs between the rc.1 candidate 7602fbe4" "$CLONE/$EV/payload-ga-1.redacted.txt"; then
      ok "B: o prompt da parte 1 carrega a conferencia com a rc.1"
    else bad "B: o prompt da parte 1 nao carrega a conferencia com a rc.1"; fi
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
    cat > "$FLAKY" <<'FLAKYEOF'
#!/bin/bash
# stub de REVISOR com UMA morte por capacidade por parte: a 1.a chamada de cada
# payload imprime a assinatura do servidor e sai rc 1 SEM veredito; a 2.a revisa.
out=""; prev=""
for a in "$@"; do
  [ "$prev" = "--output-last-message" ] && out="$a"
  prev="$a"
done
bytes=$(wc -c)
[ -n "$out" ] || { echo "stub: sem --output-last-message" >&2; exit 3; }
mark="$out.flaky-seen"
if [ ! -e "$mark" ]; then
  : > "$mark"
  echo "ERROR: Selected model is at capacity. Please try a different model."
  exit 1
fi
rm -f "$mark"
printf 'STUB REVIEW: li %s bytes de payload pela stdin.\n' "$bytes" > "$out"
printf 'VERDICT: GO-WITH-CONDITIONS cobertura declarada no README-ga.\n' >> "$out"
printf 'stub: payload de %s bytes\n' "$bytes"
FLAKYEOF
    chmod 0755 "$FLAKY"
    if ( cd "$CLONE2" && CODEX_BIN="$FLAKY" CODEX_MODEL=stub-model HOME="$SCRATCH/fakehome2" \
         GA_RETRY_UNIT_SECONDS=0 GNUPGHOME="$_test_gnupg" \
         bash "$EV/run-ga-repass.sh" ) > "$SCRATCH/runner2.log" 2>&1; then
      ok "B2: o runner sobrevive a UMA morte por capacidade em cada parte (rc 0)"
    else bad "B2: runner rc!=0 com o stub instavel"; sed -n '1,25p' "$SCRATCH/runner2.log"; fi
    _b2="$(grep -c 'tentativa(s) MORTA(s) por capacidade' "$CLONE2/$EV/PROVENANCE-ga.md" 2>/dev/null)" || _b2=0
    if [ "$_b2" = "3" ]; then ok "B2: a PROVENANCE declara a morte por capacidade nas 3 partes"
    else bad "B2: a PROVENANCE declara $_b2 morte(s) (esperado 3)"; fi
    _b2_left="$(find "$CLONE2/$EV" -maxdepth 1 \( -name '.codex-dead-*' -o -name '*.flaky-seen' \) | grep -c . )" || _b2_left=0
    if [ "$_b2_left" = "0" ]; then ok "B2: nenhum marcador de tentativa sobrou na arvore"
    else bad "B2: sobraram $_b2_left marcador(es) de tentativa na arvore"; fi
  else bad "B2: clone local para o stub instavel falhou"; fi
fi

say "B4. controle vermelho da conferencia: candidato que MUDA a parte 1 e declarado MUDOU"
if [ -n "$CLONE" ] && [ -n "${CAND:-}" ] && [ -n "${_test_gnupg:-}" ]; then
  UP4="$SCRATCH/upstream4"; CLONE4="$SCRATCH/clone4"
  if git clone --quiet --local --shared "$UPSTREAM" "$UP4" 2>/dev/null \
     && fixture_git_identity "$UP4" \
     && printf '\n# TEST ONLY: mutacao do ensaio B4\n' >> "$UP4/.claude/hooks/_lib/launch_ledger.py" \
     && git -C "$UP4" commit --quiet -am "TEST ONLY: B4 mutates part 1" \
     && git clone --quiet --local --shared "$UP4" "$CLONE4" 2>/dev/null; then
    CAND4="$(git -C "$CLONE4" rev-parse HEAD)"
    git -C "$CLONE4" checkout --quiet --detach "$CAND4" 2>/dev/null
    printf '%s\n' "$CAND4" > "$CLONE4/$EV/CANDIDATE.sha"
    if ( cd "$CLONE4" && CODEX_BIN="$STUB" CODEX_MODEL=stub-model HOME="$SCRATCH/fakehome4" \
         GNUPGHOME="$_test_gnupg" bash "$EV/run-ga-repass.sh" ) > "$SCRATCH/runner4.log" 2>&1; then
      ok "B4: runner completou sobre o candidato mutado (rc 0)"
    else bad "B4: runner rc!=0 sobre o candidato mutado"; sed -n '1,20p' "$SCRATCH/runner4.log"; fi
    _p4="$CLONE4/$EV/PROVENANCE-ga.md"
    if grep -q '^  - diff-ga-1.patch: MUDOU desde o candidato da rc.1' "$_p4" 2>/dev/null \
       && grep -q '^  - diff-ga-2.patch: sem mudanca na pathspec' "$_p4" \
       && grep -q '^  - diff-ga-3.patch: sem mudanca na pathspec' "$_p4"; then
      ok "B4 (controle vermelho): a PROVENANCE declara MUDOU so na parte mutada"
    else bad "B4: a PROVENANCE nao separou a parte mutada"; grep -n 'diff-ga-' "$_p4" 2>/dev/null; fi
    if grep -q "NO - files of this part's pathspec DIFFER" "$CLONE4/$EV/payload-ga-1.redacted.txt" 2>/dev/null \
       && grep -q "yes - no file of this part's pathspec differs" "$CLONE4/$EV/payload-ga-2.redacted.txt" 2>/dev/null; then
      ok "B4: o prompt da parte mutada diz ao revisor que a pathspec MUDOU (e o da parte 2 nao)"
    else bad "B4: o prompt nao separou a parte mutada"; fi
  else bad "B4: preparacao do candidato mutado falhou"; fi
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
say "C. gerador de envelope com chave GPG DESCARTAVEL"
if [ -n "$CLONE" ] && [ -f "$CLONE/$EV/MANIFEST-ga.sha256" ]; then
  GH="$SCRATCH/gnupg"; mkdir -p "$GH"; chmod 700 "$GH"
  if [ "${#GH}" -gt 80 ]; then
    GH_ALIAS="$(mktemp -u /tmp/gk.XXXXXX)"
    if ln -s "$GH" "$GH_ALIAS"; then GH="$GH_ALIAS"
    else bad "alias curto do homedir GPG falhou ($GH_ALIAS)"; GH_ALIAS=""; fi
  fi
  printf '%s\n' '%no-protection' 'Key-Type: eddsa' 'Key-Curve: Ed25519' \
    'Name-Real: rc1 kit selftest' 'Expire-Date: 0' '%commit' > "$GH/params"
  if GNUPGHOME="$GH" gpg --batch --quiet --gen-key "$GH/params" > "$GH/keygen.log" 2>&1; then
    FPR="$(GNUPGHOME="$GH" gpg --batch --with-colons --list-secret-keys 2>/dev/null \
      | awk -F: '$1=="fpr"{print $10; exit}')"
    [ -n "$FPR" ] && ok "chave descartavel criada ($(printf '%s' "$FPR" | cut -c1-12))" \
      || bad "chave descartavel sem fingerprint"
  else
    FPR=""; bad "gpg --gen-key falhou no homedir temporario"
    sed -n '1,12p' "$GH/keygen.log"
  fi
  if [ -n "${FPR:-}" ]; then
    CLAUDE_STUB_DIR="$SCRATCH/claude-stub"; mkdir -p "$CLAUDE_STUB_DIR"
    printf '#!/bin/bash\necho "2.1.999 (Claude Code)"\n' > "$CLAUDE_STUB_DIR/claude"
    chmod 0755 "$CLAUDE_STUB_DIR/claude"
    VF="$CLONE/$PLAN_DIR/verdict-fields-v1.4.1.md"
    COND="$CLONE/$EV/CONDITIONS-ga.reviewed.md"
    _gen="$SCRATCH/gen.log"
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
    # e o MANIFEST e regenerado. Isto e PLUMBING: o veredito das 3 partes
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
p.write_text(t, encoding="utf-8")
PYPROV
    _mf=""
    for n in 1 2 3; do
      _mf="$_mf payload-ga-$n.redacted.txt diff-ga-$n.patch"
      _mf="$_mf paths-ga-$n.manifest.txt verdict-ga-$n.txt transcript-ga-$n.log"
    done
    # shellcheck disable=SC2086
    ( cd "$CLONE/$EV" && shasum -a 256 $_mf PROVENANCE-ga.md CANDIDATE.sha \
        run-ga-repass.sh CONDITIONS-ga.reviewed.md > MANIFEST-ga.sha256 ) || bad "C2: regeneracao do MANIFEST falhou"
    if ( cd "$CLONE" && GA_SELFTEST=1 GA_SELFTEST_SCRATCH="$SCRATCH" \
         GA_SELFTEST_SIGNER_FPR="$FPR" GNUPGHOME="$GH" PATH="$CLAUDE_STUB_DIR:$PATH" \
         python3 "$PLAN_DIR/gen-envelope-ga.py" --stage fields \
           --parent "$CAND" --conditions-file "$COND" ) > "$_gen" 2>&1; then
      ok "C2: gen --stage fields sobre evidencia com codex PINADO"
    else bad "C2: gen --stage fields"; sed -n '1,15p' "$_gen"; fi
    if [ -f "$VF" ]; then
      grep -q '^verdict: GO-WITH-CONDITIONS' "$VF" \
        && ok "veredito agregado DERIVADO dos 3 rails = GO-WITH-CONDITIONS" \
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
           GA_SELFTEST_SIGNER_FPR="$FPR" GNUPGHOME="$GH" \
           python3 "$PLAN_DIR/gen-envelope-ga.py" --stage envelope \
             --sig "$VF.asc" ) > "$SCRATCH/env.log" 2>&1; then
        ok "C3: gen --stage envelope com assinatura descartavel"
      else bad "C3: gen --stage envelope"; sed -n '1,12p' "$SCRATCH/env.log"; fi
      _envf="$CLONE/.claude/governance/pair-rail-verdict-v1.4.1.md"
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
_envf="${CLONE:+$CLONE/.claude/governance/pair-rail-verdict-v1.4.1.md}"
if [ -n "$CLONE" ] && [ -f "$_envf" ] && [ -f "$CLONE/$EV/MANIFEST-ga.sha256" ]; then
  _e_vd=".claude/governance/pair-rail-verdict-v1.4.1.md"
  _e_vf="$PLAN_DIR/verdict-fields-v1.4.1.md"
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
  _e_guard() { python3 "$ROOT/.claude/scripts/local/_release_tag_guard.py" delta --repo "$1" --tag v1.4.1; }
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
      printf 'PLAN_DIR=%s; EV=%s; TAG=v1.4.1\n' "$PLAN_DIR" "$EV"
      printf 'COND="$EV/CONDITIONS-ga.md"; VF="$PLAN_DIR/verdict-fields-$TAG.md"\n'
      printf 'VD=".claude/governance/pair-rail-verdict-$TAG.md"; CAND=%s\n' "$CAND"
      printf 'GEN=%s\n' "$PLAN_DIR/gen-envelope-ga.py"
      awk '/^evidence_list\(\) \{$/,/^\}$/' "$_cut"
      awk '/^if should 11; then$/{f=1; next} /^  mark_step 11$/{f=0} f' "$_cut"
    } > "$SCRATCH/e3.sh"
    _e3_n="$(grep -c 'git commit -q -F -' "$SCRATCH/e3.sh" || true)"
    [ "$_e3_n" = "1" ] || bad "E3: o bloco extraido nao contem exatamente 1 commit (tem $_e3_n)"
    if ( cd "$_e3" && HOME="$_e3home" GNUPGHOME="$GH" GA_SELFTEST=1 \
         GA_SELFTEST_SCRATCH="$SCRATCH" GA_SELFTEST_SIGNER_FPR="$FPR" \
         GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=commit.gpgsign \
         GIT_CONFIG_VALUE_0=false bash "$SCRATCH/e3.sh" ) > "$SCRATCH/e3.log" 2>&1; then
      ok "E3: o passo 11 verbatim corre limpo sobre o clone (rc 0)"
    else bad "E3: o passo 11 verbatim falhou"; sed -n '1,12p' "$SCRATCH/e3.log"; fi
    if [ "$(git -C "$_e3" rev-parse HEAD^ 2>/dev/null)" = "$CAND" ]; then
      ok "E3: o commit senta DIRETAMENTE sobre o candidato"
    else bad "E3: pai do commit != candidato"; fi
    if git -C "$_e3" log -1 --format=%s | grep -qF 'verdito pair-rail v1.4.1 assinado'; then
      ok "E3: assunto do commit sobreviveu (CM-07)"
    else bad "E3: assunto do commit inesperado: $(git -C "$_e3" log -1 --format=%s | cut -c1-80)"; fi
    _e3_files="$(git -C "$_e3" show --name-only --format= HEAD)"
    if printf '%s\n' "$_e3_files" | grep -qxF "$_e_vd" \
       && printf '%s\n' "$_e3_files" | grep -qxF "$_e_vf" \
       && printf '%s\n' "$_e3_files" | grep -qxF "$EV/MANIFEST-ga.sha256"; then
      ok "E3: o commit carrega veredito + fields + MANIFEST ($(printf '%s\n' "$_e3_files" | grep -c .) caminhos)"
    else bad "E3: o commit nao carrega veredito/fields/MANIFEST"; fi
    if [ -f "$_e3home/.rc2-backup/verdict-fields-v1.4.1.md.asc" ] && [ ! -e "$_e3/$_e_vf.asc" ]; then
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
     && cp "$CLONE/$_e_vf.asc" "$_e3bhome/.rc2-backup/verdict-fields-v1.4.1.md.asc"; then
    if ( cd "$_e3b" && HOME="$_e3bhome" GNUPGHOME="$GH" GA_SELFTEST=1 \
         GA_SELFTEST_SCRATCH="$SCRATCH" GA_SELFTEST_SIGNER_FPR="$FPR" \
         GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=commit.gpgsign \
         GIT_CONFIG_VALUE_0=false bash "$SCRATCH/e3.sh" ) > "$SCRATCH/e3b.log" 2>&1 \
       && grep -q 'assinatura restaurada do backup' "$SCRATCH/e3b.log" \
       && [ "$(git -C "$_e3b" rev-parse HEAD^ 2>/dev/null)" = "$CAND" ] \
       && [ ! -e "$_e3b/$_e_vf.asc" ]; then
      ok "E3b: retomada do passo 11 com o .asc so no backup: restaurado, verificado e commitado sobre o candidato"
    else bad "E3b: a retomada do passo 11 falhou"; sed -n '1,12p' "$SCRATCH/e3b.log"; fi
  else bad "E3b: preparacao falhou"; fi

  # E4 — o passo 2: `release.sh bump --stable` num clone local do candidato (a forma
  # que o CUT usa porque o driver recusa porcelain nao vazio e a arvore viva carrega a
  # evidencia untracked). No GA o bump TEM de ser no-op (VERSION ja em 1.4.1 e os
  # quatro oraculos limpos): um commit ou arquivo aqui e FALHA — o passo 2 recusaria.
  _e4="$SCRATCH/e4"
  if git clone --quiet --local --no-hardlinks "$UPSTREAM" "$_e4" 2>/dev/null \
     && fixture_git_identity "$_e4"; then
    _e4_head="$(git -C "$_e4" rev-parse HEAD)"
    _e4_rc=0
    ( cd "$_e4" && bash .claude/scripts/local/release.sh bump --stable \
        --today "$(date -u +%Y-%m-%d)" --npm-readme-reviewed ) > "$SCRATCH/e4.log" 2>&1 || _e4_rc=$?
    if [ "$_e4_rc" -ne 0 ]; then
      bad "E4: bump no clone rc=$_e4_rc"; grep -E 'oracle|FAIL|no-op' "$SCRATCH/e4.log" | head -6
    elif [ "$(git -C "$_e4" rev-parse HEAD)" = "$_e4_head" ] \
         && [ -z "$(git -C "$_e4" status --porcelain=v1 --untracked-files=all)" ] \
         && grep -q 'no-op' "$SCRATCH/e4.log"; then
      ok "E4: bump --stable no clone e NO-OP (nada escrito) — o que o GA exige"
    else
      bad "E4: bump --stable NAO foi no-op: $(git -C "$_e4" log -1 --format=%s | cut -c1-60)"
    fi
  else bad "E4: clone local para o bump falhou"; fi
  # E4r — o --restamp que o CUT do GA recusa: no MESMO candidato ele NAO e no-op (o
  # fast path e desligado por desenho) — a recusa nao e vacua.
  _e4r="$SCRATCH/e4r"
  if git clone --quiet --local --no-hardlinks "$UPSTREAM" "$_e4r" 2>/dev/null \
     && fixture_git_identity "$_e4r"; then
    _e4r_head="$(git -C "$_e4r" rev-parse HEAD)"
    _e4r_rc=0
    ( cd "$_e4r" && bash .claude/scripts/local/release.sh bump --stable --restamp \
        --today "$(date -u +%Y-%m-%d)" --npm-readme-reviewed ) > "$SCRATCH/e4r.log" 2>&1 || _e4r_rc=$?
    if [ "$(git -C "$_e4r" rev-parse HEAD)" != "$_e4r_head" ] \
       || [ -n "$(git -C "$_e4r" status --porcelain=v1 --untracked-files=all)" ]; then
      ok "E4r: bump --stable --restamp NAO e no-op (rc=$_e4r_rc; commit ou arquivo) — por isso o CUT do GA o recusa"
    else bad "E4r: --restamp foi no-op (rc=$_e4r_rc) — a recusa do CUT seria vacua?"; tail -5 "$SCRATCH/e4r.log"; fi
  else bad "E4r: clone local para o bump falhou"; fi

  # E7 — o passo 2 do OWNER-GA-CUT.sh VERBATIM (extraido entre os seus marcadores),
  # com um driver STUB no lugar do release.sh: no-op => segue; commit ou arquivo novo
  # no clone => recusa ANTES de qualquer fetch/merge/push, e o HEAD nao anda.
  _e7="$SCRATCH/e7"; mkdir -p "$_e7/tmp"
  {
    printf '#!/bin/bash\nset -euo pipefail\n'
    printf 'say() { :; }\n'
    printf 'die() { printf "FAIL: %%s\\n" "$*" >&2; exit 1; }\n'
    printf 'ROOT="$(pwd -P)"; RELEASE="$E7_DRIVER"; TODAY=2026-09-22; BASE=1.4.1\n'
    awk '/^if should 2; then$/{f=1; next} /^  mark_step 2$/{f=0} f' "$_cut"
    printf 'printf "E7-STEP-2-MARCADO\\n"\n'
  } > "$SCRATCH/e7.sh"
  printf '#!/bin/bash\necho "stub: no-op"\n' > "$_e7/noop.sh"
  printf '#!/bin/bash\ngit -c user.name=s -c user.email=s@invalid -c commit.gpgsign=false commit -q --allow-empty -m "release: v1.4.1"\n' > "$_e7/commit.sh"
  printf '#!/bin/bash\nprintf "x\\n" > stray-bump-output\n' > "$_e7/dirty.sh"
  _e7_run() {  # $1 = caso (noop|commit|dirty); ecoa o rc
    local d="$_e7/$1" rc=0
    git init --quiet "$d" 2>/dev/null && fixture_git_identity "$d" \
      && ( cd "$d" && printf 'a\n' > a && git add a && git commit -q -m a ) || return 90
    git -C "$d" rev-parse HEAD > "$_e7/$1.head0"
    ( cd "$d" && printf '\n' | TMPDIR="$_e7/tmp" E7_DRIVER="$_e7/$1.sh" bash "$SCRATCH/e7.sh" ) \
      > "$_e7/$1.log" 2>&1 || rc=$?
    return "$rc"
  }
  if _e7_run noop && grep -q 'bump e no-op' "$_e7/noop.log" && grep -q 'E7-STEP-2-MARCADO' "$_e7/noop.log"; then
    ok "E7: passo 2 verbatim com driver no-op segue e marca o passo"
  else bad "E7: passo 2 verbatim recusou o no-op"; sed -n '1,8p' "$_e7/noop.log"; fi
  for _c in commit dirty; do
    if _e7_run "$_c"; then bad "E7: driver '$_c' passou pelo passo 2"
    elif grep -q 'o bump do GA NAO foi no-op' "$_e7/$_c.log" && ! grep -q 'E7-STEP-2-MARCADO' "$_e7/$_c.log" \
         && [ "$(git -C "$_e7/$_c" rev-parse HEAD)" = "$(cat "$_e7/$_c.head0")" ]; then
      ok "E7 (controle vermelho): driver '$_c' e recusado no passo 2, antes de fetch/merge/push, e o HEAD nao anda"
    else bad "E7: driver '$_c' recusado sem o motivo (ou o HEAD andou)"; sed -n '1,8p' "$_e7/$_c.log"; fi
  done

  # E5 — evidence_complete_for() (passo 6): evidencia sintetica, um positivo e
  # quatro negativos (cada fonte de verdade mutada por vez).
  _e5="$SCRATCH/e5"
  _e5_run() {  # $1 = mutacao: none | manifest | rc | prov-sha | cand-sha
    local X=0123456789abcdef0123456789abcdef01234567 Y=fedcba9876543210fedcba9876543210fedcba98 d
    d="$_e5/$1"; mkdir -p "$d"
    printf 'a\n' > "$d/x.txt"; printf 'b\n' > "$d/y.txt"
    ( cd "$d" && shasum -a 256 x.txt y.txt > MANIFEST-ga.sha256 )
    printf -- '- Base: v1.4.0 (o) .. Candidato: %s (PRE-tag)\nRUNNER-OVERALL: rc=0\n' "$X" > "$d/PROVENANCE-ga.md"
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
          --verdict-file "$_e_vd" --parent-sha "$CAND" --release-tag v1.4.1 \
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
say "G. G0/passo 5: a arvore da rc.1 CONGELADA (assert_rc_tree_frozen)"
_cut="$ROOT/$PLAN_DIR/OWNER-GA-CUT.sh"
_g="$SCRATCH/g"
if git init --quiet "$_g" 2>/dev/null && fixture_git_identity "$_g" \
   && ( cd "$_g" && mkdir -p .claude/hooks .claude/plans/PLAN-192 \
        && printf 'x\n' > .claude/hooks/h.py && printf 'c\n' > CLAUDE.md \
        && printf 'r\n' > .claude/plans/README.md && git add -- CLAUDE.md .claude/hooks/h.py .claude/plans/README.md && git commit -q -m base \
        && git tag v1.4.1-rc.1 \
        && printf 'c2\n' >> CLAUDE.md && printf 'l\n' > .claude/plans/PLAN-192/LEDGER.md \
        && git add -- CLAUDE.md .claude/plans/PLAN-192/LEDGER.md && git commit -q -m ok && git branch g-ok \
        && printf 'r2\n' >> .claude/plans/README.md && git commit -q -am plans-readme && git branch g-readme \
        && git checkout -q --detach g-ok && printf 'y\n' >> .claude/hooks/h.py && git commit -q -am hook \
        && git branch g-hook ); then
  { printf '#!/bin/bash\nset -euo pipefail\n'
    printf 'die() { printf "FAIL: %%s\\n" "$*" >&2; exit 1; }\n'
    printf 'RC_TAG=v1.4.1-rc.1\n'
    awk '/^assert_rc_tree_frozen\(\) \{$/,/^\}$/' "$_cut"
    printf 'assert_rc_tree_frozen "$1"\n'; } > "$SCRATCH/g.sh"
  if ( cd "$_g" && bash "$SCRATCH/g.sh" g-ok ) > "$SCRATCH/g-ok.log" 2>&1; then
    ok "G: CLAUDE.md + plano numerado depois da tag passam"
  else bad "G: o caso bom foi recusado"; sed -n '1,6p' "$SCRATCH/g-ok.log"; fi
  if ( cd "$_g" && bash "$SCRATCH/g.sh" g-readme ) > "$SCRATCH/g-readme.log" 2>&1; then
    bad "G: um plano NAO numerado (.claude/plans/README.md, entregue pelo install) passou"
  elif grep -q '.claude/plans/README.md' "$SCRATCH/g-readme.log"; then
    ok "G (controle vermelho): plano NAO numerado e recusado pelo nome"
  else bad "G: recusa sem nomear .claude/plans/README.md"; fi
  if ( cd "$_g" && bash "$SCRATCH/g.sh" g-hook ) > "$SCRATCH/g-hook.log" 2>&1; then
    bad "G: um hook mudado depois da tag passou"
  elif grep -q '.claude/hooks/h.py' "$SCRATCH/g-hook.log"; then
    ok "G (controle vermelho): hook mudado depois da tag e recusado pelo nome"
  else bad "G: recusa sem nomear o hook"; fi
else bad "G: fixture do congelamento falhou"; fi

# ===========================================================================
say "H. G0: o hold ADR-103 da rc.1 (assert_rc_hold) — positivo e sete vermelhos"
if [ -n "${FPR:-}" ] && [ -n "${GH:-}" ]; then
  _h="$SCRATCH/h"; mkdir -p "$_h/bin"
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
     && ( cd "$_h/w" && printf 'a\n' > a && git add a && git commit -q -m a ) \
     && GNUPGHOME="$GH" git -C "$_h/w" -c user.signingkey="$FPR" tag -s -m "rc fixture" v1.4.1-rc.1 \
     && ( cd "$_h/w" && printf 'b\n' > b && git add b && git commit -q -m b ) \
     && git -C "$_h/w" remote add origin "$_h/origin.git" \
     && git -C "$_h/w" push -q origin HEAD:refs/heads/main refs/tags/v1.4.1-rc.1 2>/dev/null; then
    { printf '#!/bin/bash\nset -euo pipefail\n'
      printf 'die() { printf "FAIL: %%s\\n" "$*" >&2; exit 1; }\n'
      printf 'RC_TAG=v1.4.1-rc.1\n'
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
      ( cd "$_h/w" && PATH="$_h/bin:$PATH" GNUPGHOME="$GH" \
          H_RELEASE_JSON="{\"isPrerelease\": $2, \"isDraft\": $3, \"publishedAt\": \"$pub\"}" \
          H_RUN_ID=4242 H_AWAIT="$4" H_GH_FAIL="${6:-}" bash "$_h/hold.sh" ) > "$5" 2>&1
    }
    if _h_run 25 true false success "$SCRATCH/h1.log" && grep -q 'OK: hold ADR-103' "$SCRATCH/h1.log"; then
      ok "H1: 25 h, pre-release publico, gate success -> hold completo"
    else bad "H1: o caso bom foi recusado"; sed -n '1,6p' "$SCRATCH/h1.log"; fi
    if _h_run 1 true false success "$SCRATCH/h2.log"; then bad "H2: 1 h de hold passou"
    elif grep -q 'hold ADR-103 incompleto' "$SCRATCH/h2.log"; then ok "H2 (controle vermelho): 1 h < 24 h e recusado"
    else bad "H2: recusa sem o motivo do hold"; fi
    if _h_run 25 true true success "$SCRATCH/h3.log"; then bad "H3: pre-release em DRAFT passou"
    elif grep -q 'ausente, draft' "$SCRATCH/h3.log"; then ok "H3 (controle vermelho): pre-release em draft e recusado"
    else bad "H3: recusa sem o motivo do draft"; fi
    if _h_run 25 false false success "$SCRATCH/h4.log"; then bad "H4: release NAO pre-release passou"
    elif grep -q 'ausente, draft' "$SCRATCH/h4.log"; then ok "H4 (controle vermelho): release sem a flag pre-release e recusado"
    else bad "H4: recusa sem o motivo"; fi
    if _h_run 25 true false failure "$SCRATCH/h5.log"; then bad "H5: await-release-gate failure passou"
    elif grep -q 'NAO e success' "$SCRATCH/h5.log"; then ok "H5 (controle vermelho): gate da rc sem success e recusado"
    else bad "H5: recusa sem o motivo do gate"; fi
    # H7/H8 — MECH3-P2-4: falha de TRANSPORTE do gh tem nome proprio; «release not found»
    # e ausencia real (antes as duas viravam «ausente, draft»).
    if _h_run 25 true false success "$SCRATCH/h7.log" "error connecting to api.github.com"; then
      bad "H7: gh release view com falha de transporte passou"
    elif grep -q 'falhou (rc=1; transporte?): error connecting to api.github.com' "$SCRATCH/h7.log" \
         && grep -q 're-rode este script' "$SCRATCH/h7.log" && ! grep -q 'ausente' "$SCRATCH/h7.log"; then
      ok "H7 (controle vermelho): falha de transporte do gh no hold tem nome proprio e a rota (re-rodar)"
    else bad "H7: falha de transporte sem nome"; sed -n '1,6p' "$SCRATCH/h7.log"; fi
    if _h_run 25 true false success "$SCRATCH/h8.log" "release not found"; then
      bad "H8: pre-release ausente passou"
    elif grep -q 'ausente (gh: release not found)' "$SCRATCH/h8.log"; then
      ok "H8 (controle vermelho): «release not found» e ausencia do pre-release, nao transporte"
    else bad "H8: ausencia sem o motivo"; sed -n '1,6p' "$SCRATCH/h8.log"; fi
    # H6: o remoto passa a ter OUTRO objeto sob o mesmo nome (tag leve no mesmo commit).
    if git -C "$_h/w" push -q -f origin "v1.4.1-rc.1^{commit}:refs/tags/v1.4.1-rc.1" 2>/dev/null; then
      if _h_run 25 true false success "$SCRATCH/h6.log"; then bad "H6: tag remota trocada passou"
      elif grep -q 'mesmo OBJETO' "$SCRATCH/h6.log"; then ok "H6 (controle vermelho): tag remota que nao e o objeto assinado local e recusada"
      else bad "H6: recusa sem o motivo do objeto"; fi
    else bad "H6: nao consegui trocar a tag remota da fixture"; fi
  else bad "H: fixture da tag assinada/remoto falhou"; fi
else printf '  (H pulado: sem chave descartavel da secao C)\n'; fi

# ===========================================================================
say "W. aviso de carga antes do preflight (warn_load)"
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
say "K. G0: o kit do GA tem de estar COMMITADO (assert_kit_committed)"
_k="$SCRATCH/k"
if git init --quiet "$_k" 2>/dev/null && fixture_git_identity "$_k" \
   && ( cd "$_k" && mkdir -p ev && printf 'r\n' > ev/run.sh && printf 'g\n' > gen.py \
        && git add -- ev/run.sh gen.py && git commit -q -m kit ); then
  { printf '#!/bin/bash\nset -euo pipefail\n'
    printf 'die() { printf "FAIL: %%s\\n" "$*" >&2; exit 1; }\n'
    printf 'KIT_TRACKED="ev/run.sh gen.py ev/README-ga.md"\n'
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
say "R. o OWNER-GA-CUT.sh REAL (script inteiro) num clone com remoto bare local"
# O script inteiro roda contra as tags REAIS da rc.1 (assinatura do Owner verificada
# com o GNUPGHOME so-publico), com `gh` e `osascript` STUB e um remoto bare local.
# `--g0-only` roda so as pre-condicoes; os estados de retomada sao plantados no
# .cut-state da fixture. Nada sai para a rede.
# Pseudo-terminal (secao T): `script` aloca o pty; o alimentador manda Enter a cada
# segundo ate o comando sair (medido: num pty sem humano um Enter isolado pode ser
# engolido, e o EOF do alimentador vira ^D no terminal). O rc e o do comando.
_pty_feed() { local i=0; while [ "$i" -lt 900 ]; do sleep 1; printf '\n' 2>/dev/null || return 0; i=$((i+1)); done; }
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
if [ -n "${CLONE:-}" ] && [ -n "${_test_gnupg:-}" ]; then
  _r="$SCRATCH/r"; mkdir -p "$_r/bin" "$_r/tmp"
  cat > "$_r/bin/gh" <<'GHREOF'
#!/bin/bash
case "$1 $2" in
  "release view")
    if [ "$3" = "v1.4.1-rc.1" ]; then
      printf '{"isPrerelease": true, "isDraft": false, "publishedAt": "%s"}\n' "$R_PUBAT"
    elif [ "$3" = "v1.4.1" ] && [ -n "${R_GA_RELEASE:-}" ]; then
      printf '%s\n' "$R_GA_RELEASE"
    else echo "release not found" >&2; exit 1; fi ;;
  "run list") echo 424242 ;;
  "run view") echo success ;;
  *) echo "gh stub: chamada inesperada: $*" >&2; exit 9 ;;
esac
GHREOF
  printf '#!/bin/bash\nexit 0\n' > "$_r/bin/osascript"
  chmod 0755 "$_r/bin/gh" "$_r/bin/osascript"
  R_GA_RELEASE=""
  _r_pub() {  # $1 = horas atras
    python3 - "$1" <<'PYR'
import sys, datetime
t = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=float(sys.argv[1]))
print(t.strftime("%Y-%m-%dT%H:%M:%SZ"))
PYR
  }
  _r_cut() {  # $1 = horas desde o publishedAt, $2 = log, $3.. = argumentos do CUT
    local _hrs="$1" _log="$2"; shift 2
    ( cd "$_r/wt" && PATH="$_r/bin:$PATH" GNUPGHOME="$_test_gnupg" HOME="$SCRATCH/rhome" \
        TMPDIR="$_r/tmp" R_PUBAT="$(_r_pub "$_hrs")" R_GA_RELEASE="$R_GA_RELEASE" \
        bash "$PLAN_DIR/OWNER-GA-CUT.sh" "$@" ) < /dev/null > "$_log" 2>&1
  }
  _r_pty() {  # $1 = log, $2.. = argumentos do CUT — o mesmo ambiente, num pty
    local _log="$1" _pub; shift
    _pub="$(_r_pub 30)"
    ( cd "$_r/wt" && _pty "$_log" env PATH="$_r/bin:$PATH" GNUPGHOME="$_test_gnupg" \
        HOME="$SCRATCH/rhome" TMPDIR="$_r/tmp" R_PUBAT="$_pub" R_GA_RELEASE="" \
        bash "$PLAN_DIR/OWNER-GA-CUT.sh" "$@" )
  }
  _r_state() {  # $1 = ultimo passo concluido (0 = nenhum)
    local _s=1
    : > "$_r/wt/$EV/.cut-state"
    while [ "$_s" -le "$1" ]; do printf 'STEP-%s\n' "$_s" >> "$_r/wt/$EV/.cut-state"; _s=$((_s+1)); done
  }
  mkdir -p "$SCRATCH/rhome"
  if git clone --quiet --bare "$UPSTREAM" "$_r/origin.git" 2>/dev/null \
     && git clone --quiet "$_r/origin.git" "$_r/wt" 2>/dev/null && fixture_git_identity "$_r/wt"; then
    # R1 — G0 verde.
    if _r_cut 30 "$_r/pos.log" --g0-only && grep -q 'OK: kit do GA commitado' "$_r/pos.log" \
       && grep -q 'OK: no plano, so a evidencia deste corte esta fora do git' "$_r/pos.log" \
       && grep -q 'OK: hold ADR-103 da v1.4.1-rc.1 completo' "$_r/pos.log" \
       && grep -q 'OK: desde a v1.4.1-rc.1 so mudaram CLAUDE.md e planos numerados' "$_r/pos.log" \
       && grep -q 'OK: main, HEAD==origin/main, tag v1.4.1 livre' "$_r/pos.log" \
       && grep -q 'OK: o Scope assinado da tag cobre os planos e ADRs de v1.4.0..HEAD' "$_r/pos.log" \
       && grep -q 'OK: CLAUDE.md com [0-9]* bytes' "$_r/pos.log" \
       && grep -q 'FREEZE: do G0 ate o push da tag' "$_r/pos.log" \
       && grep -q 'G0 verde (--g0-only)' "$_r/pos.log"; then
      ok "R1: G0 real verde (kit commitado, plano sem untracked alheio, hold da rc.1 real, arvore congelada, Scope assinado e CLAUDE.md conferidos no repo real, tag livre, FREEZE anunciado)"
    else bad "R1: G0 real recusou o caso bom"; sed -n '1,24p' "$_r/pos.log"; fi
    # R2 — hold curto.
    if _r_cut 1 "$_r/hold.log" --g0-only; then bad "R2: G0 real aceitou 1 h de hold"
    elif grep -q 'hold ADR-103 incompleto' "$_r/hold.log"; then ok "R2 (controle vermelho): G0 real recusa 1 h de hold"
    else bad "R2: G0 real recusou o hold curto sem o motivo"; fi
    # R3 — argumentos: recusa nomeada ANTES do G0, rc 2 e nunca o banner.
    _r_arg() {  # $1 = rotulo, $2 = motivo esperado, $3.. = argumentos
      local _l="$1" _pat="$2" _rc=0; shift 2
      _r_cut 30 "$_r/arg.log" "$@" || _rc=$?
      if [ "$_rc" -eq 2 ] && grep -qF -- "$_pat" "$_r/arg.log" && ! grep -q 'PUBLICADO' "$_r/arg.log"; then
        ok "R3 (controle vermelho): $_l e recusado (rc 2, sem banner)"
      else bad "R3: $_l nao foi recusado como devia (rc=$_rc)"; sed -n '1,4p' "$_r/arg.log"; fi
    }
    _r_arg "--from abc" "exige um passo de 1 a 20" --from abc
    _r_arg "--from 99" "exige um passo de 1 a 20" --from 99
    _r_arg "--until 0" "exige um passo de 1 a 20" --until 0
    _r_arg "--restamp" "nao existe no corte do GA" --restamp
    # M4: valor AUSENTE (o `shift` do fim do laco saia rc 1 mudo sob set -e).
    _r_arg "--from sem valor" "--from exige um passo de 1 a 20 (veio: nada)" --from
    _r_arg "--until 5 --from sem valor" "--from exige um passo de 1 a 20 (veio: nada)" --until 5 --from
    _r_arg "--until sem valor" "--until exige um passo de 1 a 20 (veio: nada)" --until
    # R4 — arquivo NAO rastreado no plano, fora da evidencia: o passo 15 o recusaria
    # depois do push do veredito; o G0 o recusa antes, pelo nome.
    printf 'x\n' > "$_r/wt/$PLAN_DIR/stray-leftover.txt"
    if _r_cut 30 "$_r/stray.log" --g0-only; then bad "R4: G0 aceitou untracked no plano fora da evidencia"
    elif grep -q "$PLAN_DIR/stray-leftover.txt" "$_r/stray.log"; then
      ok "R4 (controle vermelho): untracked no plano fora da evidencia e recusado no G0, pelo nome"
    else bad "R4: recusa sem nomear o arquivo"; sed -n '1,6p' "$_r/stray.log"; fi
    rm -f -- "$_r/wt/$PLAN_DIR/stray-leftover.txt"

    # =======================================================================
    say "T. o CUT REAL num PSEUDO-TERMINAL (script + Enter periodico)"
    if ! command -v script >/dev/null 2>&1; then
      bad "T: o comando script esta ausente — o ensaio com pseudo-terminal nao rodou"
    else
      _r_state 0
      if _r_pty "$_r/t1.log" --g0-only && grep -q 'G0 verde (--g0-only)' "$_r/t1.log"; then
        ok "T1: G0 real verde num pseudo-terminal"
      else bad "T1: G0 real no pty falhou"; tr -d '\r' < "$_r/t1.log" | sed -n '1,20p'; fi
      _r_state 0
      if _r_pty "$_r/t2.log" --from 2 --until 2 \
         && grep -q 'AVISO: --from 2 PULA passo(s) NAO concluido(s): 1' "$_r/t2.log" \
         && grep -q 'Enter para confirmar que releu' "$_r/t2.log" \
         && grep -q 'bump e no-op' "$_r/t2.log" \
         && grep -q 'PARADO depois do passo 2' "$_r/t2.log" \
         && grep -qx 'STEP-2' "$_r/wt/$EV/.cut-state" && ! grep -qx 'STEP-1' "$_r/wt/$EV/.cut-state"; then
        ok "T2: passo 2 REAL num pty: o pulo do 1 e nomeado, o Enter e lido do terminal, o bump REAL e no-op e o --until para"
      else bad "T2: passo 2 real no pty falhou"; tr -d '\r' < "$_r/t2.log" | sed -n '1,40p'; fi
      if [ -f "$SCRATCH/w.sh" ]; then
        if ( _pty "$SCRATCH/t3.log" env W_LOAD="9.50 4" bash "$SCRATCH/w.sh" ) \
           && grep -q 'AVISO: a maquina esta CARREGADA' "$SCRATCH/t3.log"; then
          ok "T3: aviso de carga alta num pty: avisa e le o Enter do terminal"
        else bad "T3: aviso de carga no pty falhou"; tr -d '\r' < "$SCRATCH/t3.log" | sed -n '1,10p'; fi
      else bad "T3: $SCRATCH/w.sh ausente (a secao W nao rodou)"; fi
    fi

    # R5c — M5: entre os passos 5 e 11 o HEAD e o candidato gravado. Um .cut-state de
    # tentativa anterior (passo 5 feito, CANDIDATE.sha de outro commit) e recusado com a
    # rota (arquivar o .cut-state), antes de o runner rodar sobre o candidato velho.
    git -C "$_r/wt" rev-parse HEAD > "$_r/wt/$EV/CANDIDATE.sha"
    _r_state 5
    if _r_cut 30 "$_r/r5c.log" --g0-only \
       && grep -q 'OK: o .cut-state (passo 5 feito) e o HEAD apontam o mesmo candidato' "$_r/r5c.log"; then
      ok "R5c: passo 5 feito e HEAD == CANDIDATE.sha: G0 verde"
    else bad "R5c: G0 recusou o .cut-state coerente"; sed -n '1,10p' "$_r/r5c.log"; fi
    git -C "$_r/wt" rev-parse 'HEAD^' > "$_r/wt/$EV/CANDIDATE.sha"
    if _r_cut 30 "$_r/r5d.log" --g0-only; then bad "R5d: .cut-state de tentativa anterior (HEAD != candidato gravado) passou"
    elif grep -q 'o .cut-state diz que o passo 5 gravou o candidato' "$_r/r5d.log" \
         && grep -q 'README-ga §0' "$_r/r5d.log"; then
      ok "R5d (controle vermelho): passo 5 feito com HEAD != CANDIDATE.sha e recusado, com a rota de arquivar o .cut-state"
    else bad "R5d: recusa sem o motivo/rota"; sed -n '1,8p' "$_r/r5d.log"; fi

    # R5e/R5f — MECH3-P1-1: uma tentativa PARCIAL do re-pass (morte por capacidade ou por
    # infraestrutura depois do snapshot das condicoes) com o passo 5 feito. Arquivada
    # DENTRO do plano (a rota antiga), o G0 a recusa; pela rota documentada no passo 6
    # (FORA do repositorio, CANDIDATE.sha e .cut-state mantidos) o G0 fica verde, o passo
    # 6 e o primeiro pendente e o assert_attempt_absent do runner nao acha nada.
    git -C "$_r/wt" rev-parse HEAD > "$_r/wt/$EV/CANDIDATE.sha"
    _r_state 5
    for _pf in CONDITIONS-ga.reviewed.md PROVENANCE-ga.md verdict-ga-1.txt transcript-ga-1.log paths-ga-1.manifest.txt; do
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
    _inrepo="$_r/wt/$PLAN_DIR/repass-ga-20260923-NOGO-r1-capacidade"
    mkdir -p "$_inrepo" && cp -- "$_r/wt/$EV/PROVENANCE-ga.md" "$_inrepo/"
    if _r_cut 30 "$_r/r5e.log" --g0-only; then bad "R5e: tentativa arquivada DENTRO do plano passou no G0"
    elif grep -q "repass-ga-20260923-NOGO-r1-capacidade/PROVENANCE-ga.md" "$_r/r5e.log"; then
      ok "R5e (controle vermelho): tentativa arquivada DENTRO do plano e recusada no G0, pelo nome"
    else bad "R5e: recusa sem nomear o arquivo"; sed -n '1,8p' "$_r/r5e.log"; fi
    rm -rf -- "$_inrepo"
    # A rota documentada, com o comando que o passo 6 imprime.
    _arch="$SCRATCH/rhome/.ceo-ga-archive/repass-ga-TEST-capacidade"
    mkdir -p "$_arch"
    ( cd "$_r/wt" && git status --porcelain --untracked-files=all -- "$EV/" ) > "$_r/r5f.list" \
      || bad "R5f: git status da evidencia falhou"
    while IFS= read -r _l; do
      case "$_l" in '??'*) _p="${_l#???}" ;; *) continue ;; esac
      [ "$_p" = "$EV/CANDIDATE.sha" ] && continue
      mv -- "$_r/wt/$_p" "$_arch/" || bad "R5f: mv de $_p falhou"
    done < "$_r/r5f.list"
    if _r_cut 30 "$_r/r5f.log" --g0-only && grep -q 'G0 verde (--g0-only)' "$_r/r5f.log" \
       && grep -q 'Pendentes: 6 7 8 ' "$_r/r5f.log" && [ -s "$_r/wt/$EV/CANDIDATE.sha" ] \
       && [ -f "$_arch/CONDITIONS-ga.reviewed.md" ] && [ -f "$_arch/paths-ga-1.manifest.txt" ]; then
      ok "R5f: rota documentada (FORA do repositorio; CANDIDATE.sha e .cut-state mantidos): G0 verde e o passo 6 e o primeiro pendente"
    else bad "R5f: a rota documentada nao deixou o G0 verde retomando do passo 6"; sed -n '1,14p' "$_r/r5f.log"; fi
    if bash "$SCRATCH/r5f-aa.sh" "$_r/wt/$EV" > "$_r/r5f-aa.log" 2>&1 && grep -q R5F-ATTEMPT-ABSENT "$_r/r5f-aa.log"; then
      ok "R5f: depois da rota, o assert_attempt_absent do runner (verbatim) nao acha tentativa anterior"
    else bad "R5f: o runner ainda veria tentativa anterior"; sed -n '1,4p' "$_r/r5f-aa.log"; fi
    rm -f -- "$_r/wt/$EV/CANDIDATE.sha"
    _r_state 0

    # R5 — retomada entre os passos 11 e 13: HEAD um commit a frente de origin/main,
    # sobre o candidato gravado. Verde com o passo 11 marcado; vermelho sem ele.
    git -C "$_r/wt" rev-parse HEAD > "$_r/wt/$EV/CANDIDATE.sha"
    if git -C "$_r/wt" commit -q --allow-empty -m "TEST ONLY: veredito local nao pushado"; then
      _r_state 11
      if _r_cut 30 "$_r/r5.log" --g0-only && grep -q 'retomada entre os passos 11 e 13' "$_r/r5.log"; then
        ok "R5: G0 reconhece a retomada entre os passos 11 e 13 (veredito commitado, nao pushado)"
      else bad "R5: G0 recusou a retomada 11-13"; sed -n '1,12p' "$_r/r5.log"; fi
      _r_state 10
      if _r_cut 30 "$_r/r5b.log" --g0-only; then bad "R5b: HEAD a frente de origin/main sem o passo 11 passou"
      elif grep -q 'fora de uma retomada conhecida' "$_r/r5b.log" && grep -q 'NAO pushe as cegas' "$_r/r5b.log"; then
        ok "R5b (controle vermelho): HEAD a frente sem o passo 11 e recusado, e o conselho NAO e pushar"
      else bad "R5b: recusa sem o estado nomeado"; sed -n '1,8p' "$_r/r5b.log"; fi
      git -C "$_r/wt" push -q origin HEAD:refs/heads/main 2>/dev/null || bad "R5: push de limpeza da fixture falhou"
    else bad "R5: commit local da fixture falhou"; fi

    # R6 — retomada depois do passo 16: a tag no remoto e o Release que o release.yml
    # cria em DRAFT. O G0 aceita; vermelhos: Release pre-release, tag remota trocada,
    # tag no remoto sem o passo 16.
    git -C "$_r/wt" rev-parse HEAD > "$_r/wt/$EV/CANDIDATE.sha"
    if git -C "$_r/wt" -c tag.gpgSign=false tag -a -m "TEST ONLY: GA fixture" v1.4.1 \
       && git -C "$_r/wt" push -q origin refs/tags/v1.4.1 2>/dev/null; then
      _r_state 16
      R_GA_RELEASE='{"isDraft": true, "isPrerelease": false}'
      if _r_cut 30 "$_r/r6.log" --g0-only && grep -q 'retomada pos-tag: o Release do v1.4.1 existe' "$_r/r6.log" \
         && grep -q 'OK: main; retomada pos-tag' "$_r/r6.log"; then
        ok "R6: G0 aceita, depois do passo 16, o Release em DRAFT que o release.yml cria"
      else bad "R6: G0 recusou a retomada pos-tag"; sed -n '1,12p' "$_r/r6.log"; fi
      R_GA_RELEASE='{"isDraft": true, "isPrerelease": true}'
      if _r_cut 30 "$_r/r6b.log" --g0-only; then bad "R6b: Release pre-release passou na retomada pos-tag"
      elif grep -q "isPrerelease='True'" "$_r/r6b.log"; then ok "R6b (controle vermelho): Release marcado pre-release e recusado na retomada"
      else bad "R6b: recusa sem o motivo"; sed -n '1,6p' "$_r/r6b.log"; fi
      R_GA_RELEASE='{"isDraft": true, "isPrerelease": false}'
      if git -C "$_r/wt" push -q -f origin "v1.4.1^{commit}:refs/tags/v1.4.1" 2>/dev/null; then
        if _r_cut 30 "$_r/r6c.log" --g0-only; then bad "R6c: tag remota trocada passou na retomada pos-tag"
        elif grep -q 'nao e o objeto assinado local' "$_r/r6c.log"; then ok "R6c (controle vermelho): tag remota que nao e o objeto local e recusada na retomada"
        else bad "R6c: recusa sem o motivo"; sed -n '1,6p' "$_r/r6c.log"; fi
        git -C "$_r/wt" push -q -f origin refs/tags/v1.4.1 2>/dev/null || bad "R6c: restaurar a tag remota falhou"
      else bad "R6c: nao consegui trocar a tag remota"; fi
      # R6d — M2: push da tag feito e o passo 16 SEM marcador (o 15 marcado): o G0
      # reconhece o objeto assinado local no remoto, registra o 16 e, sem o epoch que o
      # passo 16 grava antes do push, usa a data do objeto da tag como piso do passo 19.
      _r_state 15
      rm -f -- "$_r/wt/$EV/.tag-push-epoch"
      if _r_cut 30 "$_r/r6d.log" --g0-only && grep -q 'passo 16 registrado agora' "$_r/r6d.log" \
         && grep -qx 'STEP-16' "$_r/wt/$EV/.cut-state" \
         && [ "$(tr -d ' \n' < "$_r/wt/$EV/.tag-push-epoch")" = "$(git -C "$_r/wt" for-each-ref --format='%(taggerdate:unix)' refs/tags/v1.4.1)" ] \
         && grep -q 'OK: main; retomada pos-tag' "$_r/r6d.log"; then
        ok "R6d: push da tag sem o marcador do 16 e reconhecido (remoto == objeto local): o 16 e registrado e o piso do passo 19 e a data da tag"
      else bad "R6d: o G0 nao reconheceu o push da tag sem marcador"; sed -n '1,12p' "$_r/r6d.log"; fi
      # R6d2 — vermelho: o remoto tem OUTRO objeto sob o nome da tag.
      _r_state 15
      if git -C "$_r/wt" push -q -f origin "v1.4.1^{commit}:refs/tags/v1.4.1" 2>/dev/null; then
        if _r_cut 30 "$_r/r6d2.log" --g0-only; then bad "R6d2: tag remota de OUTRO objeto, sem o passo 16, passou"
        elif grep -q 'ja existe no REMOTO' "$_r/r6d2.log" && ! grep -qx 'STEP-16' "$_r/wt/$EV/.cut-state"; then
          ok "R6d2 (controle vermelho): tag remota que nao e o objeto local NAO registra o 16 e e recusada"
        else bad "R6d2: recusa sem o motivo (ou o 16 foi registrado)"; sed -n '1,6p' "$_r/r6d2.log"; fi
        git -C "$_r/wt" push -q -f origin refs/tags/v1.4.1 2>/dev/null || bad "R6d2: restaurar a tag remota falhou"
      else bad "R6d2: nao consegui trocar a tag remota"; fi
      # R6d3 — M2: tag LOCAL sem o marcador do 15: a recusa nomeia a rota (git tag -d).
      _r_state 14
      if _r_cut 30 "$_r/r6d3.log" --g0-only; then bad "R6d3: tag local sem o passo 15 passou"
      elif grep -q 'ja existe (local)' "$_r/r6d3.log" && grep -q 'git tag -d v1.4.1' "$_r/r6d3.log"; then
        ok "R6d3 (controle vermelho): tag local sem o passo 15 e recusada, e a recusa nomeia a rota (git tag -d)"
      else bad "R6d3: recusa sem a rota"; sed -n '1,8p' "$_r/r6d3.log"; fi
      # R6e — M1: retomada depois do 16 com main que ANDOU (push de outra sessao depois
      # da tag): o G0 passa com AVISO. R6e2: main REVERTIDO para antes da tag e recusado.
      _r_state 16
      if git clone -q "$_r/origin.git" "$_r/other" 2>/dev/null && fixture_git_identity "$_r/other" \
         && git -C "$_r/other" commit -q --allow-empty -m "TEST ONLY: push alheio depois da tag" \
         && git -C "$_r/other" push -q origin HEAD:refs/heads/main 2>/dev/null; then
        if _r_cut 30 "$_r/r6e.log" --g0-only \
           && grep -q 'AVISO: main andou depois do push da tag (1 commit' "$_r/r6e.log" \
           && grep -q 'G0 verde (--g0-only)' "$_r/r6e.log"; then
          ok "R6e: retomada pos-tag com main que andou (push alheio depois da tag) passa com AVISO"
        else bad "R6e: o G0 recusou a retomada pos-tag com main que andou"; sed -n '1,12p' "$_r/r6e.log"; fi
        if git -C "$_r/wt" push -q -f origin "v1.4.1^{commit}^:refs/heads/main" 2>/dev/null; then
          if _r_cut 30 "$_r/r6e2.log" --g0-only; then bad "R6e2: main revertido para antes da tag passou na retomada"
          elif grep -q 'fora de uma retomada conhecida' "$_r/r6e2.log"; then
            ok "R6e2 (controle vermelho): main revertido para antes da tag e recusado na retomada pos-tag"
          else bad "R6e2: recusa sem o motivo"; sed -n '1,8p' "$_r/r6e2.log"; fi
        else bad "R6e2: nao consegui reverter o main da fixture"; fi
        git -C "$_r/wt" push -q -f origin HEAD:refs/heads/main 2>/dev/null || bad "R6e: restaurar o main da fixture falhou"
      else bad "R6e: push alheio na fixture falhou"; fi
      # R7 — o banner de PUBLICADO so com o passo 20 concluido.
      R_GA_RELEASE='{"isDraft": false, "isPrerelease": false}'
      _r_state 19
      if _r_cut 30 "$_r/r7.log" --until 19 && grep -q 'PARADO depois do passo 19' "$_r/r7.log" \
         && grep -q 'pendentes: 20' "$_r/r7.log" && ! grep -q 'PUBLICADO' "$_r/r7.log"; then
        ok "R7: --until 19 para, lista o 20 pendente e NAO imprime o banner de PUBLICADO"
      else bad "R7: --until nao parou como devia"; sed -n '1,12p' "$_r/r7.log"; fi
      _r_state 20
      if _r_cut 30 "$_r/r7b.log" && grep -q 'GA v1.4.1 PUBLICADO' "$_r/r7b.log"; then
        ok "R7b: com o passo 20 concluido, o banner sai"
      else bad "R7b: banner ausente com os 20 passos concluidos"; sed -n '1,12p' "$_r/r7b.log"; fi
      R_GA_RELEASE=""
      git -C "$_r/wt" tag -d v1.4.1 >/dev/null 2>&1 || bad "R: limpeza da tag local falhou"
      git -C "$_r/wt" push -q origin :refs/tags/v1.4.1 2>/dev/null || bad "R: limpeza da tag remota falhou"
    else bad "R6: tag/push da fixture falhou"; fi
    rm -f -- "$_r/wt/$EV/CANDIDATE.sha" "$_r/wt/$EV/.tag-push-epoch"
    _r_state 0

    # R8 — hook mudado depois da tag da rc.1 (por ultimo: muda o main da fixture).
    printf '\n# TEST ONLY: ensaio R\n' >> "$_r/wt/.claude/hooks/check_workflow_launch.py"
    if git -C "$_r/wt" commit -q -am "TEST ONLY: hook muda depois da rc" \
       && git -C "$_r/wt" push -q origin HEAD:refs/heads/main 2>/dev/null; then
      if _r_cut 30 "$_r/frozen.log" --g0-only; then bad "R8: G0 real aceitou hook mudado depois da rc"
      elif grep -q '.claude/hooks/check_workflow_launch.py' "$_r/frozen.log"; then
        ok "R8 (controle vermelho): G0 real recusa hook mudado depois da tag da rc.1, pelo nome"
      else bad "R8: G0 real recusou sem nomear o hook"; fi
    else bad "R8: commit/push da mutacao no clone falhou"; fi
  else bad "R: clone bare/remoto local falhou"; fi
else printf '  (R e T pulados: sem clone ou sem GNUPGHOME so-publico)\n'; fi

# ===========================================================================
say "S. o teto da espera de CI e o conselho do vermelho (estatico sobre o CUT)"
if grep -qF 'CI_WAIT_MAX_MIN="${GA_CI_WAIT_MAX_MIN:-150}"' "$_cut" \
   && grep -qF '[ "$i" -le "$CI_WAIT_MAX_MIN" ]' "$_cut" \
   && ! grep -qF '"CI nao terminou em 90 min"' "$_cut"; then
  ok "S: wait_ci_green espera ate 150 min por padrao (o teto de 90 saiu)"
else bad "S: o teto da espera de CI nao e o do GA"; fi
if grep -qF 'gh run rerun <run> --failed' "$_cut"; then
  ok "S: o vermelho de CI nomeia o rerun do drift de runner"
else bad "S: o vermelho de CI nao nomeia o rerun"; fi
# M3: os preflights 1 e 15 (cujo driver conta QUALQUER run do commit, agendado
# inclusive) dao a mesma rota; e o vermelho do wait_ci_green diz que o agendado conta.
if [ "$(grep -c '^\$PREFLIGHT_RED_HINT"$' "$_cut")" = "2" ] \
   && grep -qF 'O preflight conta QUALQUER workflow sobre este commit, agendado (cron) inclusive.' "$_cut" \
   && grep -qF 'inclusive um run AGENDADO (cron) durante o freeze' "$_cut" \
   && grep -qF 'Se o motivo e «a workflow for HEAD is still running»' "$_cut" \
   && grep -qF 'Se o motivo e «hooks test suite failed (serial)»' "$_cut"; then
  ok "S: os vermelhos dos preflights 1 e 15 nomeiam o rerun, o run ainda rodando e a suite serial; o run AGENDADO de qualquer workflow e declarado"
else bad "S: o conselho do vermelho dos preflights (ou do run agendado) falta"; fi
if grep -qF '"a workflow for HEAD is not green"' "$ROOT/.claude/scripts/local/release.sh" \
   && grep -qF '"a workflow for HEAD is still running — wait for it"' "$ROOT/.claude/scripts/local/release.sh" \
   && grep -qF '"hooks test suite failed (serial)"' "$ROOT/.claude/scripts/local/release.sh" \
   && grep -qF '"validate-governance.sh nonzero"' "$ROOT/.claude/scripts/local/release.sh"; then
  ok "S: as quatro frases do driver que o conselho cita existem no release.sh"
else bad "S: o conselho cita frase que o release.sh nao emite mais"; fi

# ===========================================================================
say "Y. passo 19: a tag do GA na cadeia first-parent de origin/main (push alheio x rollback)"
# O recheck do passo 19, VERBATIM (extraido entre os seus marcadores), num clone com
# remoto bare local: main igual a tag passa calado; main que andou depois da tag passa
# com AVISO (o npm ja publicou; morrer aqui deixaria o Release em DRAFT a toa);
# main revertido para antes da tag e recusa.
_y="$SCRATCH/y"
if git init --quiet --bare "$_y/origin.git" 2>/dev/null \
   && git init --quiet "$_y/w" 2>/dev/null && fixture_git_identity "$_y/w" \
   && ( cd "$_y/w" && printf 'a\n' > a && git add a && git commit -q -m a \
        && printf 'b\n' > b && git add b && git commit -q -m b \
        && git -c tag.gpgSign=false tag -a -m "TEST ONLY" v1.4.1 ) \
   && git -C "$_y/w" remote add origin "$_y/origin.git" \
   && git -C "$_y/w" push -q origin HEAD:refs/heads/main 2>/dev/null; then
  { printf '#!/bin/bash\nset -euo pipefail\n'
    printf 'die() { printf "FAIL: %%s\\n" "$*" >&2; exit 1; }\n'
    printf 'TAG=v1.4.1\n'
    awk '/^  # main nao pode ter sido REVERTIDO/{f=1} /^  _prj="\$\(gh release view/{f=0} f' "$_cut"
    printf 'printf "Y-OK\\n"\n'; } > "$SCRATCH/y.sh"
  if ( cd "$_y/w" && bash "$SCRATCH/y.sh" ) > "$SCRATCH/y1.log" 2>&1 && grep -q 'Y-OK' "$SCRATCH/y1.log" \
     && ! grep -q 'AVISO' "$SCRATCH/y1.log"; then ok "Y1: origin/main == commit da tag passa"
  else bad "Y1: o caso igual foi recusado"; sed -n '1,6p' "$SCRATCH/y1.log"; fi
  if ( cd "$_y/w" && printf 'c\n' > c && git add c && git commit -q -m c ) \
     && git -C "$_y/w" push -q origin HEAD:refs/heads/main 2>/dev/null \
     && git -C "$_y/w" checkout -q --detach v1.4.1 2>/dev/null; then
    if ( cd "$_y/w" && bash "$SCRATCH/y.sh" ) > "$SCRATCH/y2.log" 2>&1 && grep -q 'Y-OK' "$SCRATCH/y2.log" \
       && grep -q 'AVISO: main andou depois da tag (1 commit' "$SCRATCH/y2.log"; then
      ok "Y2: push alheio DEPOIS da tag passa com AVISO (a tag segue na cadeia first-parent)"
    else bad "Y2: push alheio depois da tag foi recusado"; sed -n '1,6p' "$SCRATCH/y2.log"; fi
  else bad "Y2: preparacao do push alheio falhou"; fi
  if git -C "$_y/w" push -q -f origin "v1.4.1^{commit}^:refs/heads/main" 2>/dev/null; then
    if ( cd "$_y/w" && bash "$SCRATCH/y.sh" ) > "$SCRATCH/y3.log" 2>&1; then bad "Y3: main revertido para antes da tag passou"
    elif grep -q 'NAO esta na cadeia first-parent' "$SCRATCH/y3.log"; then
      ok "Y3 (controle vermelho): main revertido para antes da tag e recusado"
    else bad "Y3: recusa sem o motivo"; sed -n '1,6p' "$SCRATCH/y3.log"; fi
  else bad "Y3: nao consegui reverter o main da fixture"; fi
else bad "Y: fixture do passo 19 falhou"; fi

# ===========================================================================
say "V. wait_ci_green: um gh run view transitorio tem NOME (nunca um traceback)"
# A funcao VERBATIM, com `sleep` neutralizado e um `gh` stub: o validate.yml achado,
# e o `gh run view` do job devolvendo vazio (falha transitoria), lixo, ou o JSON bom.
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
  printf 'sleep() { :; }\nCI_WAIT_MAX_MIN=3; RC_TAG=v1.4.1-rc.1\n'
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
say "Z. passo 5: um CANDIDATE.sha que ja aponta o candidato e mantido byte a byte"
# O passo 5 VERBATIM (o congelamento neutralizado: ele tem a sua secao, G) num clone
# com remoto bare local. O re-pass rodado antes da cerimonia pina o CANDIDATE.sha no
# MANIFEST: reescreve-lo noutro formato poria a evidencia fora do MANIFEST.
_z="$SCRATCH/z"
if git init --quiet --bare "$_z/origin.git" 2>/dev/null \
   && git init --quiet "$_z/w" 2>/dev/null && fixture_git_identity "$_z/w" \
   && ( cd "$_z/w" && printf 'a\n' > a && git add a && git commit -q -m a ) \
   && git -C "$_z/w" remote add origin "$_z/origin.git" \
   && git -C "$_z/w" push -q origin HEAD:refs/heads/main 2>/dev/null; then
  _zc="$(git -C "$_z/w" rev-parse HEAD)"; mkdir -p "$_z/w/ev"
  { printf '#!/bin/bash\nset -euo pipefail\n'
    printf 'say() { :; }; mark_step() { :; }; assert_rc_tree_frozen() { :; }\n'
    printf 'die() { printf "FAIL: %%s\\n" "$*" >&2; exit 1; }\n'
    printf 'EV=ev; STATE=ev/.cut-state; CAND=%s\n' "$_zc"
    awk '/^assert_steps_saw_cand\(\) \{$/,/^\}$/' "$_cut"
    awk '/^if should 5; then$/{f=1; next} /^  mark_step 5$/{f=0} f' "$_cut"; } > "$SCRATCH/z.sh"
  printf 'STEP-1\nSHA-1 %s\nSTEP-4\nSHA-4 %s\n' "$_zc" "$_zc" > "$_z/w/ev/.cut-state"
  printf '%s' "$_zc" > "$_z/w/ev/CANDIDATE.sha"
  _z0="$(shasum -a 256 "$_z/w/ev/CANDIDATE.sha" | awk '{print $1}')"
  if ( cd "$_z/w" && bash "$SCRATCH/z.sh" ) > "$SCRATCH/z1.log" 2>&1 \
     && grep -q 'mantido byte a byte' "$SCRATCH/z1.log" \
     && [ "$(shasum -a 256 "$_z/w/ev/CANDIDATE.sha" | awk '{print $1}')" = "$_z0" ]; then
    ok "Z1: CANDIDATE.sha sem newline final, mesmo commit: mantido byte a byte"
  else bad "Z1: o CANDIDATE.sha do re-pass antecipado foi reescrito"; sed -n '1,6p' "$SCRATCH/z1.log"; fi
  printf '%s\n' fedcba9876543210fedcba9876543210fedcba98 > "$_z/w/ev/CANDIDATE.sha"
  if ( cd "$_z/w" && bash "$SCRATCH/z.sh" ) > "$SCRATCH/z2.log" 2>&1 \
     && [ "$(cat "$_z/w/ev/CANDIDATE.sha")" = "$_zc" ]; then
    ok "Z2: CANDIDATE.sha de OUTRO commit e reescrito com o candidato"
  else bad "Z2: CANDIDATE.sha de outro commit nao foi reescrito"; sed -n '1,6p' "$SCRATCH/z2.log"; fi
  if grep -q 'OK: os passos 1 e 4 conferiram o candidato' "$SCRATCH/z1.log"; then
    ok "Z1b: os passos 1 e 4 registraram o proprio candidato: o passo 5 segue"
  else bad "Z1b: o passo 5 nao conferiu os commits dos passos 1 e 4"; sed -n '1,6p' "$SCRATCH/z1.log"; fi
  # Z3 — MECH3-P2-5: o passo 4 conferiu OUTRO commit (o HEAD mudou depois dele).
  printf 'STEP-1\nSHA-1 %s\nSTEP-4\nSHA-4 %s\n' "$_zc" fedcba9876543210fedcba9876543210fedcba98 > "$_z/w/ev/.cut-state"
  if ( cd "$_z/w" && bash "$SCRATCH/z.sh" ) > "$SCRATCH/z3.log" 2>&1; then
    bad "Z3: passo 4 feito sobre OUTRO commit passou pelo passo 5"
  elif grep -q 'passo 4: conferiu fedcba9876543210fedcba9876543210fedcba98 (linhas STEP-4 e SHA-4)' "$SCRATCH/z3.log" \
       && ! grep -q 'passo 1: conferiu' "$SCRATCH/z3.log"; then
    ok "Z3 (controle vermelho): o passo 4 que conferiu OUTRO commit e recusado no passo 5, com as linhas a tirar"
  else bad "Z3: recusa sem o motivo"; sed -n '1,8p' "$SCRATCH/z3.log"; fi
  # Z4 — sem o registro do commit (passo feito a mao): AVISO nomeado, e o passo segue.
  printf 'STEP-1\nSTEP-4\n' > "$_z/w/ev/.cut-state"
  if ( cd "$_z/w" && bash "$SCRATCH/z.sh" ) > "$SCRATCH/z4.log" 2>&1 \
     && grep -q 'nao registra o commit que o passo 4 conferiu' "$SCRATCH/z4.log"; then
    ok "Z4: sem o registro do commit dos passos 1/4, AVISO nomeado e o passo 5 segue"
  else bad "Z4: o passo 5 sem registro nao avisou (ou recusou)"; sed -n '1,8p' "$SCRATCH/z4.log"; fi
else bad "Z: fixture do passo 5 falhou"; fi

# ===========================================================================
say "L. G0: CLAUDE.md abaixo do limite do validate-governance.sh (assert_claude_md_fits)"
# O preflight roda o validate-governance.sh COMPLETO com a saida suprimida. A funcao
# VERBATIM, e o gate que ela espelha conferido no proprio validate-governance.sh.
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
_l_mk 200
if ( cd "$_l" && CLAUDE_MD_SIZE_LIMIT=100 bash "$SCRATCH/l.sh" ) > "$SCRATCH/l3.log" 2>&1; then
  bad "L3: CLAUDE_MD_SIZE_LIMIT ignorado"
elif grep -q 'reprova a partir de 100' "$SCRATCH/l3.log"; then
  ok "L3 (controle vermelho): o limite segue CLAUDE_MD_SIZE_LIMIT, como no validate-governance.sh"
else bad "L3: recusa sem o limite do ambiente"; sed -n '1,4p' "$SCRATCH/l3.log"; fi

# ===========================================================================
say "P. G0: o Scope ASSINADO da tag cobre a faixa (assert_release_scope_covers_log)"
# A funcao VERBATIM num repo de fixture: RELEASE_SCOPE com PLAN-190/192 e nenhum ADR;
# commits que citam so esses planos passam; um plano novo ou um ADR tocado sao recusados.
_p="$SCRATCH/p"
if git init --quiet "$_p" 2>/dev/null && fixture_git_identity "$_p" \
   && ( cd "$_p" && printf 'RELEASE_SCOPE="PLAN-190 / PLAN-192 (ADRs tocados: nenhum)"\n' > rel.sh \
        && git add rel.sh && git commit -q -m base && git tag v1.4.0 \
        && git commit -q --allow-empty -m "plan(PLAN-192): kit do GA" \
        && git commit -q --allow-empty -m "plan(PLAN-190): nota" && git branch p-ok \
        && git commit -q --allow-empty -m "plan(PLAN-193): plano novo" && git branch p-plan \
        && git checkout -q --detach p-ok && mkdir -p .claude/adr \
        && printf 'a\n' > .claude/adr/ADR-200-x.md && git add .claude/adr/ADR-200-x.md \
        && git commit -q -m "plan(PLAN-192): adr" && git branch p-adr ); then
  { printf '#!/bin/bash\nset -euo pipefail\n'
    printf 'die() { printf "FAIL: %%s\\n" "$*" >&2; exit 1; }\n'
    printf 'RELEASE=rel.sh; PREV_TAG=v1.4.0\n'
    awk '/^assert_release_scope_covers_log\(\) \{$/,/^\}$/' "$_cut"
    printf 'assert_release_scope_covers_log\n'; } > "$SCRATCH/p.sh"
  _p_run() {  # $1 = branch, $2 = log
    git -C "$_p" checkout -q --detach "$1" 2>/dev/null || return 90
    ( cd "$_p" && bash "$SCRATCH/p.sh" ) > "$2" 2>&1
  }
  if _p_run p-ok "$SCRATCH/p1.log" && grep -q 'OK: o Scope assinado da tag cobre' "$SCRATCH/p1.log"; then
    ok "P1: commits que citam so planos do RELEASE_SCOPE passam"
  else bad "P1: o caso bom foi recusado"; sed -n '1,6p' "$SCRATCH/p1.log"; fi
  if _p_run p-plan "$SCRATCH/p2.log"; then bad "P2: commit que cita plano NOVO passou"
  elif grep -q 'nao lista: PLAN-193$' "$SCRATCH/p2.log"; then
    ok "P2 (controle vermelho): commit que cita plano fora do RELEASE_SCOPE e recusado pelo nome"
  else bad "P2: recusa sem nomear o plano"; sed -n '1,6p' "$SCRATCH/p2.log"; fi
  if _p_run p-adr "$SCRATCH/p3.log"; then bad "P3: ADR tocado fora do RELEASE_SCOPE passou"
  elif grep -q 'nao lista: ADR-200$' "$SCRATCH/p3.log"; then
    ok "P3 (controle vermelho): ADR tocado na faixa, fora do RELEASE_SCOPE, e recusado pelo nome"
  else bad "P3: recusa sem nomear o ADR"; sed -n '1,6p' "$SCRATCH/p3.log"; fi
else bad "P: fixture do Scope falhou"; fi

# ===========================================================================
say "X. passo 17: conclusao terminal diferente de success e recusa na hora (nunca 120 min)"
# O passo 17 VERBATIM com `gh` STUB que devolve, chamada a chamada, o valor final do
# --jq (status|conclusion|run). Antes so `failure` era terminal.
_x="$SCRATCH/x"; mkdir -p "$_x/bin"
cat > "$_x/bin/gh" <<'GHXEOF'
#!/bin/bash
n="$(cat "$X_CNT" 2>/dev/null || echo 0)"; n=$((n+1)); printf '%s' "$n" > "$X_CNT"
printf '%s\n' "$X_SEQ" | sed -n "${n}p"
GHXEOF
chmod 0755 "$_x/bin/gh"
if git init --quiet "$_x/w" 2>/dev/null && fixture_git_identity "$_x/w" \
   && ( cd "$_x/w" && git commit -q --allow-empty -m a && git -c tag.gpgSign=false tag -a -m t v1.4.1 ); then
  { printf '#!/bin/bash\nset -euo pipefail\n'
    printf 'die() { printf "FAIL: %%s\\n" "$*" >&2; exit 1; }\n'
    printf 'say() { :; }; bell() { :; }; sleep() { :; }; should() { return 0; }\n'
    printf 'mark_step() { printf "X-STEP-%%s-MARCADO\\n" "$1"; }\n'
    printf 'verdict_deadline() { printf "PRAZO-STUB"; }\n'
    printf 'TAG=v1.4.1\n'
    awk '/^if should 17; then$/,/^fi$/' "$_cut"; } > "$SCRATCH/x.sh"
  _x_run() {  # $1 = sequencia (uma linha por chamada do gh), $2 = log
    rm -f -- "$_x/cnt"
    ( cd "$_x/w" && PATH="$_x/bin:$PATH" X_CNT="$_x/cnt" X_SEQ="$1" bash "$SCRATCH/x.sh" ) > "$2" 2>&1
  }
  for _xc in cancelled timed_out startup_failure failure; do
    if _x_run "completed|$_xc|4242" "$SCRATCH/x-$_xc.log"; then bad "X: release.yml '$_xc' passou pelo passo 17"
    elif grep -q "release.yml terminou '$_xc' para a tag v1.4.1 (run 4242)" "$SCRATCH/x-$_xc.log" \
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
# O trecho VERBATIM do passo 19. Antes, sem o arquivo, o piso era 0 e a conferencia
# «publishedAt desta cerimonia» ficava vacua.
_q="$SCRATCH/q"
if git init --quiet "$_q" 2>/dev/null && fixture_git_identity "$_q" \
   && ( cd "$_q" && git commit -q --allow-empty -m a && git -c tag.gpgSign=false tag -a -m t v1.4.1 && mkdir -p ev ); then
  { printf '#!/bin/bash\nset -euo pipefail\n'
    printf 'die() { printf "FAIL: %%s\\n" "$*" >&2; exit 1; }\n'
    printf 'EV=ev; TAG="${Q_TAG:-v1.4.1}"; _pe="$Q_PE"\n'
    awk '/^  # O piso e o epoch que o passo 16 grava/{f=1} /^  printf .   GA publicado NAO-draft/{f=0} f' "$_cut"
    printf 'printf "Q-OK\\n"\n'; } > "$SCRATCH/q.sh"
  _qt="$(git -C "$_q" for-each-ref --format='%(taggerdate:unix)' refs/tags/v1.4.1)"
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

# ===========================================================================
printf '\n===== RESULTADO: %s PASS, %s FAIL\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
