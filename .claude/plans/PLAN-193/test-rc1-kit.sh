#!/bin/bash
# CEREMONY-LINT: handwritten-exception: harness do kit de corte da v1.4.2-rc.1, DERIVADO por
# .claude/plans/PLAN-193/derive-kit-142.py do harness da v1.4.2-rc.1 (escrito contra o
# corpus PLAN-188/ceremony-defect-corpus-S348.md), com os controles que o kit do GA v1.4.1
# acrescentou. NAO edite a mao.
#
# test-rc1-kit.sh — prova a TUBULACAO inteira do kit sem gastar uma unica
# invocacao de codex e sem tocar na arvore viva.
#
#   bash .claude/plans/PLAN-193/test-rc1-kit.sh
#   bash .claude/plans/PLAN-193/test-rc1-kit.sh --evidence-only
#
# Onde roda: numa arvore em que os lands da 1.4.2 JA estao (a da manha, depois da
# relmeta-142; ou, antes dela, uma arvore PROJETADA com eles). A fixture recria a tag base
# v1.4.1 no upstream DESCARTAVEL, assinada por uma chave descartavel, no commit
# RC1KIT_BASE_REV (padrao: o commit da v1.4.1 real) — nada sai do scratch.
#   RC1KIT_SCRATCH_PARENT  pai do scratch (padrao /tmp; com um pai longo, o homedir GPG
#                          ganha um ALIAS curto em /tmp, removido na saida).
#
# O que ele faz, em ordem:
#   F.  controles de EVIDENCIA do gerador e dos guards do runner (sem GPG nem rede),
#       inclusive a recusa de evidencia sem a sonda das condicoes VERDE;
#   A.  lint estatico: `derive-kit-142.py --check`, `/bin/bash -n` (3.2) + `shellcheck -S
#       warning` nos shells do kit, compilacao EM MEMORIA (sem .pyc) nos pythons, e
#       `check-ceremony-script.py` exigindo ZERO achado BLOCKING nos arquivos do kit;
#   K0. a chave GPG DESCARTAVEL (antes do B: ela assina a tag base da fixture);
#   P.  a SONDA das condicoes contra o candidato da fixture (o resultado REAL de cada
#       afirmacao), e os controles vermelhos: o canario do FN-04 contra o hook da
#       v1.4.1 ACHA a copia (a sonda nao e vacua); um caminho fora de toda parte, um
#       template com ultracode, um plano sem a decisao que uma condicao cita e um
#       veredito pinado alterado sao recusados pelo nome;
#   B.  runner ponta a ponta num CLONE descartavel, com um codex STUB (`CODEX_BIN`) e a
#       base resolvida em tempo de run; B2 morte por capacidade; B3 o modelo; B5/B6 a base
#       ausente e a base assinada fora do registro sao recusadas pelo nome;
#   C.  gerador de envelope: fields -> assinatura descartavel -> envelope, com o
#       `claude --version` MEDIDO por um stub;
#   E.  topologia do commit do veredito x os dois gates; o passo 11 verbatim (e as
#       retomadas dele: o .asc so no backup; o staging que nao virou commit); o bump
#       REAL da rc (um commit ou no-op, e a 2.a corrida no-op); o passo 2 verbatim com
#       driver stub (commit, no-op e as formas recusadas);
#   W G K S V Z X Q Y L SC  as curas do kit do GA (e o aviso da sonda GPG), cada uma
#       VERBATIM do OWNER-RC1-CUT.sh com stubs, com o controle vermelho de cada uma;
#   R.  o OWNER-RC1-CUT.sh REAL (`--g0-only` e estados de retomada plantados no
#       .cut-state) num clone com remoto bare local e `gh` stub; T. o mesmo num
#       PSEUDO-TERMINAL (o G0 e o passo 2 inteiro, com o Enter e o bump REAIS, e a
#       retomada entre os passos 2 e 3 que pusha aquele bump);
#   D.  UM CONTROLE VERMELHO por classe do corpus que este kit cura.
#
# Se a sonda das condicoes nao fica verde na fixture (uma lane ainda nao landou), o P
# REPROVA com as afirmacoes nomeadas, e B/C/E/R seguem em RC1_PROBE_REPORT_ONLY=1 — so
# para exercitar a tubulacao; o C prova que o gerador RECUSA essa evidencia.
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
EV="$PLAN_DIR/repass-rc1"
SHELLS="
$PLAN_DIR/OWNER-RC1-CUT.sh
$PLAN_DIR/test-rc1-kit.sh
$EV/run-rc1-repass.sh
"
PYS="
$PLAN_DIR/gen-envelope-rc1.py
$PLAN_DIR/derive-kit-142.py
$EV/probe-conditions-rc1.py
"
# O kit inteiro, lista FECHADA: copiado do DISCO para o upstream da fixture (o ensaio
# exercita os bytes que estao no disco, commitados ou nao).
KIT_FILES="
$PLAN_DIR/OWNER-RC1-CUT.sh
$PLAN_DIR/gen-envelope-rc1.py
$PLAN_DIR/test-rc1-kit.sh
$PLAN_DIR/derive-kit-142.py
$EV/run-rc1-repass.sh
$EV/probe-conditions-rc1.py
$EV/CONDITIONS-rc1.md
$EV/README-rc1.md
$EV/.gitignore
"

PASS=0; FAIL=0
ok()   { PASS=$((PASS+1)); printf '  PASS  %s\n' "$*"; }
bad()  { FAIL=$((FAIL+1)); printf '  FAIL  %s\n' "$*"; }
say()  { printf '\n===== %s\n' "$*"; }

# Scratch CURTO por padrao: o socket do gpg-agent estoura o limite de sun_path do
# macOS (~104 bytes) num caminho longo. Medido: "can't connect to the gpg-agent:
# File name too long". RC1KIT_SCRATCH_PARENT troca o pai (um ensaio confinado ao
# scratchpad de uma sessao, por exemplo); com um pai longo o homedir GPG ganha um ALIAS
# curto em /tmp (um symlink, removido na saida) — o chaveiro e os sockets ficam
# fisicamente DENTRO do scratch.
SCRATCH_PARENT="${RC1KIT_SCRATCH_PARENT:-/tmp}"
[ -d "$SCRATCH_PARENT" ] || { echo "RC1KIT_SCRATCH_PARENT nao e diretorio: $SCRATCH_PARENT" >&2; exit 2; }
SCRATCH="$(mktemp -d "$SCRATCH_PARENT/rc1kit.XXXXXX")" || { echo "mktemp falhou" >&2; exit 2; }
SCRATCH="$(cd "$SCRATCH" && pwd -P)" || { echo "scratch ilegivel" >&2; exit 2; }
# O claude REAL nunca roda neste ensaio: um sentinela no inicio do PATH falha alto se
# algo o chamar sem o stub da secao C (o gerador MEDE `claude --version`).
mkdir -p "$SCRATCH/no-claude" \
  && printf '#!/bin/bash\necho "HARNESS: claude real chamado sem stub" >&2\nexit 97\n' > "$SCRATCH/no-claude/claude" \
  && chmod 0755 "$SCRATCH/no-claude/claude" || { echo "sentinela do claude falhou" >&2; exit 2; }
PATH="$SCRATCH/no-claude:$PATH"; export PATH
# Nenhum .pyc na arvore que o ensaio le (a arvore viva, de manha).
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
spec = importlib.util.spec_from_file_location("rc1_generator", plan / "gen-envelope-rc1.py")
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)
# tool_versions.claude_code e MEDIDO por `claude --version`; estes controles sao das
# guardas de EVIDENCIA e nunca rodam o claude real (a medicao tem a secao C).
gen.claude_code_version = lambda: "claude-code-cli-2.1.999"
ev = scratch / "evidence-controls"
ev.mkdir()
gen.EV = ev
runner = (plan / "repass-rc1/run-rc1-repass.sh").read_text(encoding="utf-8")
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
    names = sorted(set(gen.ARTIFACTS) - {"MANIFEST-rc1.sha256"})
    (ev / "MANIFEST-rc1.sha256").write_text("".join(
        "%s  %s\n" % (hashlib.sha256((ev / name).read_bytes()).hexdigest(), name)
        for name in names), encoding="ascii")


def prepare():
    for name in gen.ARTIFACTS:
        (ev / name).write_text("fixture\n", encoding="utf-8")
    (ev / "run-rc1-repass.sh").write_text(runner, encoding="utf-8")
    (ev / "CANDIDATE.sha").write_text(candidate + "\n")
    (ev / gen.REVIEWED_CONDITIONS).write_text(conditions, encoding="utf-8")
    (ev / "CONDITIONS-rc1.md").write_text(conditions, encoding="utf-8")
    cond_hash = hashlib.sha256(conditions.encode()).hexdigest()
    (ev / "PROVENANCE-rc1.md").write_text(
        "Candidato: %s\n- codex: %s / aarch64-apple-darwin / payload %s\n"
        "- condicoes declaradas no prompt (DATA para o revisor): "
        "CONDITIONS-rc1.reviewed.md sha256 %s\n"
        "- sonda das condicoes: verde (fixture dos controles de evidencia)\n"
        "RUNNER-OVERALL: rc=0\n"
        % (candidate, pin["package_version"], digest, cond_hash), encoding="utf-8")
    # Saida de um revisor stub local, nao de qualquer provedor.
    for part in gen.PARTS:
        (ev / ("verdict-rc1-%d.txt" % part)).write_text(
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
        (ev / ("verdict-rc1-%d.txt" % part)).write_text("VERDICT: NO-GO\n")
        seal()
        refuses("NO-GO + RESIDUAL na parte %d" % part,
                lambda: gen.build_fields(candidate, conditions), "rail NO-GO")
    for text in ("VERDICT: GO\nVERDICT: GO\n", "VERDICT: GO-WITH-CONDITIONS-extra\n", "sem veredito\n"):
        prepare()
        (ev / "verdict-rc1-4.txt").write_text(text)
        seal()
        refuses("veredito ambiguo/ilegivel", lambda: gen.build_fields(candidate, conditions), "VERDICT")
    prepare()
    (ev / "verdict-rc1-4.txt").unlink()
    refuses("ultima parte ausente", lambda: gen.build_fields(candidate, conditions), "artefato ausente")
    prepare()
    refuses("condicoes fornecidas alteradas", lambda: gen.build_fields(candidate, conditions + "novo\n"), "diferem das revisadas")
    (ev / "CONDITIONS-rc1.md").write_text(conditions + "novo\n")
    refuses("fonte alterada depois da revisao", lambda: gen.build_fields(candidate, conditions), "mudaram desde a revisao")
    prepare()
    (ev / gen.REVIEWED_CONDITIONS).write_text(conditions + "novo\n")
    seal()
    refuses("snapshot alterado com MANIFEST recalculado", lambda: gen.build_fields(candidate, conditions), "hash da PROVENANCE")
    prepare()
    fields = gen.build_fields(candidate, conditions)
    refuses("fields alterados apos assinatura", lambda: gen.verify_fields_evidence(fields.replace("verdict: GO-WITH-CONDITIONS", "verdict: GO", 1)), "fields assinados divergem")
    (ev / "diff-rc1-1.patch").write_text("outro diff\n")
    seal()
    refuses("evidencia alterada apos fields", lambda: gen.verify_fields_evidence(fields), "fields assinados divergem")
    prepare()
    manifest = ev / "MANIFEST-rc1.sha256"
    manifest.write_text("\n".join(manifest.read_text().splitlines()[1:]) + "\n")
    refuses("MANIFEST omite artefato", lambda: gen.build_fields(candidate, conditions), "exatamente os 25")
    prepare()
    prov = ev / "PROVENANCE-rc1.md"
    prov.write_text(prov.read_text().replace("RUNNER-OVERALL: rc=0", "RUNNER-OVERALL: rc=1"))
    seal()
    refuses("runner incompleto com vereditos GO", lambda: gen.build_fields(candidate, conditions), "RUNNER-OVERALL")
    # A sonda das condicoes que NAO ficou verde no run (modo REPORT-ONLY do harness, ou
    # um runner trocado sem a linha) nunca vira fields.
    for bad_probe in ("- sonda das condicoes: VERMELHA (rc=1) em modo REPORT-ONLY do harness\n", ""):
        prepare()
        prov = ev / "PROVENANCE-rc1.md"
        prov.write_text(re.sub(r"(?m)^- sonda das condicoes: .*\n", bad_probe, prov.read_text()))
        seal()
        refuses("sonda das condicoes nao verde (%s)" % ("vermelha" if bad_probe else "linha ausente"),
                lambda: gen.build_fields(candidate, conditions), "sonda das condicoes")
    prepare()
    for part in gen.PARTS:
        (ev / ("verdict-rc1-%d.txt" % part)).write_text("VERDICT: GO explicacao do stub\n")
    seal()
    if not gen.build_fields(candidate, conditions).startswith("verdict: GO\n"):
        raise RuntimeError("os GO validos nao produziram GO")
    checks += 1

# Executar os guards reais (sem base/GPG/provider/worktree), inclusive os
# efeitos sobre o disco. Um arquivo parcial deve sobreviver byte a byte.
start = runner.index("assert_attempt_absent() {")
end = runner.index("\n}\n", start) + 3
guard_function = runner[start:end]
init = runner[runner.index('CONDITIONS_SOURCE="$OUT/CONDITIONS-rc1.md"'):runner.index("# --- 0.")]
prefix = 'set -uo pipefail\ndie() { printf "FATAL: %s\\n" "$*" >&2; exit 1; }\n'
for number, artifact in enumerate(("verdict-rc1-1.txt", "transcript-rc1-4.log", "payload-rc1-2.raw.txt", "MANIFEST-rc1.sha256.tmp", "probe-rc1.txt", gen.REVIEWED_CONDITIONS)):
    out = scratch / ("partial-%d" % number)
    out.mkdir()
    path = out / artifact
    path.write_bytes(b"partial evidence\x00preserve\n")
    result = subprocess.run(["bash", "-c", prefix + guard_function + "\nassert_attempt_absent\n"],
                            env=dict(os.environ, OUT=str(out)), stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if result.returncode != 1 or path.read_bytes() != b"partial evidence\x00preserve\n":
        raise RuntimeError("tentativa parcial nao preservada: " + artifact)
    checks += 1
for number, mutation in enumerate(("", 'printf novo >> "$CONDITIONS_SOURCE"', 'printf novo >> "$CONDITIONS_SNAPSHOT"', 'printf novo >> "$OUT/run-rc1-repass.sh"')):
    out = scratch / ("freeze-%d" % number)
    out.mkdir()
    (out / "run-rc1-repass.sh").write_text(runner)
    (out / "CONDITIONS-rc1.md").write_text(conditions)
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
    raw = out / "payload-rc1-1.raw.txt"
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
if python3 "$PLAN_DIR/derive-kit-142.py" --check > "$SCRATCH/derive-check.log" 2>&1; then
  ok "A0: derive-kit-142.py --check (o kit no disco e o derivado, byte a byte)"
else bad "A0: derive-kit-142.py --check FALHOU"; sed -n '1,14p' "$SCRATCH/derive-check.log"; fi
for f in $SHELLS; do
  [ -f "$f" ] || { bad "ausente: $f"; continue; }
  if /bin/bash -n "$f" 2>/dev/null; then ok "/bin/bash -n $(basename "$f") ($(/bin/bash -c 'echo $BASH_VERSION' | cut -c1-3))"; else bad "/bin/bash -n $(basename "$f")"; fi
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
_k0="$(mk_gpg_home "$SCRATCH/gnupg" "rc1 kit selftest")" || _k0=""
if [ -n "$_k0" ]; then
  GH="$(printf '%s' "$_k0" | awk '{print $1}')"; FPR="$(printf '%s' "$_k0" | awk '{print $2}')"
  GH_ALIAS="$(printf '%s' "$_k0" | awk '{print $3}')"
  ok "chave descartavel criada ($(printf '%s' "$FPR" | cut -c1-12)); homedir ${GH_ALIAS:+(alias curto) }$GH"
else bad "K0: gpg --gen-key falhou no homedir temporario"; sed -n '1,12p' "$SCRATCH/gnupg/keygen.log" 2>/dev/null; fi
# A mesma variavel que o runner, o G0 e o gerador leem: o seam de auto-teste, recusado
# fora deste scratch.
SELFTEST_ENV="RC1_SELFTEST=1 RC1_SELFTEST_SCRATCH=$SCRATCH RC1_SELFTEST_SIGNER_FPR=$FPR"

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
# pela chave descartavel, no commit RC1KIT_BASE_REV (padrao: o commit da v1.4.1 real).
# Ela nunca sai do scratch; o runner, o G0 e o gerador a aceitam pelo seam de auto-teste.
BASE_REV=""
if [ "$_fixture_ok" -eq 1 ]; then
  BASE_REV="${RC1KIT_BASE_REV:-}"
  if [ -z "$BASE_REV" ]; then
    BASE_REV="$(git rev-parse -q --verify 'refs/tags/v1.4.1^{commit}' 2>/dev/null)" || BASE_REV=""
  fi
  BASE_REV="$(git rev-parse -q --verify "${BASE_REV:-none}^{commit}" 2>/dev/null)" || BASE_REV=""
  if [ -z "$BASE_REV" ] || [ -z "$FPR" ]; then
    bad "B: sem base (a tag v1.4.1 nao existe aqui e RC1KIT_BASE_REV nao foi passado) ou sem chave"
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
    if ( cd "$CLONE" && PYTHONDONTWRITEBYTECODE=1 python3 "$EV/probe-conditions-rc1.py" \
           --root "$CLONE" --base refs/tags/v1.4.1 --head HEAD --sizes ) > "$SCRATCH/probe0.log" 2>&1; then
      ok "P0: sonda das condicoes VERDE contra o candidato da fixture ($(grep -c '^OK ' "$SCRATCH/probe0.log") linhas OK)"
    else
      bad "P0: sonda das condicoes NAO verde contra o candidato da fixture:"
      grep -E '^(FAIL|INFRA)' "$SCRATCH/probe0.log" | sed 's/^/        /'
      PROBE_ENV="RC1_PROBE_REPORT_ONLY=1"
    fi
    grep -E '^OK +SIZE' "$SCRATCH/probe0.log" | sed 's/^/        /'
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
printf 'VERDICT: GO-WITH-CONDITIONS cobertura declarada no README-rc1.\n' >> "$out"
printf 'stub: payload de %s bytes\n' "$bytes"
STUBEOF
    chmod 0755 "$STUB"
    _run="$SCRATCH/runner.log"
    # O GNUPGHOME e o DESCARTAVEL (a tag base da fixture e dele); nunca o chaveiro real.
    _test_gnupg="$GH"
    # shellcheck disable=SC2086
    if ( cd "$CLONE" && env CODEX_BIN="$STUB" CODEX_MODEL=stub-model HOME="$SCRATCH/fakehome" \
         GNUPGHOME="$_test_gnupg" $SELFTEST_ENV $PROBE_ENV \
         bash "$EV/run-rc1-repass.sh" ) > "$_run" 2>&1; then
      ok "runner completou as 4 partes (rc 0)"
    else
      bad "runner rc!=0"; sed -n '1,25p' "$_run"
    fi
    _ml="$(grep -c . "$CLONE/$EV/MANIFEST-rc1.sha256" 2>/dev/null || echo 0)"
    if [ "$_ml" = "25" ]; then ok "MANIFEST-rc1 com 25 entradas (4 partes x 5 + PROVENANCE, CANDIDATE, runner, condicoes, sonda)"
    else bad "MANIFEST-rc1 com $_ml entradas (esperado 25)"; fi
    if grep -q '^probe-rc1.txt$' <<MANI
$(awk '{print $2}' "$CLONE/$EV/MANIFEST-rc1.sha256" 2>/dev/null)
MANI
    then ok "B: a saida da sonda (probe-rc1.txt) esta no MANIFEST"
    else bad "B: probe-rc1.txt fora do MANIFEST"; fi
    if grep -q '^- sonda das condicoes: ' "$CLONE/$EV/PROVENANCE-rc1.md" 2>/dev/null \
       && grep -q "^- base assinada por: $FPR$" "$CLONE/$EV/PROVENANCE-rc1.md" 2>/dev/null; then
      ok "B: a PROVENANCE declara a sonda ($(grep '^- sonda das condicoes: ' "$CLONE/$EV/PROVENANCE-rc1.md" | cut -c24-40)...) e o signatario da base resolvida"
    else bad "B: a PROVENANCE sem a linha da sonda ou do signatario da base"; fi
    if ( cd "$CLONE/$EV" && shasum -a 256 -c MANIFEST-rc1.sha256 --status ); then
      ok "MANIFEST-rc1 verifica"
    else bad "MANIFEST-rc1 nao verifica"; fi
    if grep -q '^RUNNER-OVERALL: rc=0' "$CLONE/$EV/PROVENANCE-rc1.md" 2>/dev/null; then
      ok "PROVENANCE com RUNNER-OVERALL rc=0"
    else bad "PROVENANCE sem RUNNER-OVERALL rc=0"; fi
    # Nenhum payload RAW pode ter sobrado na arvore (eles vao para quarentena).
    if ls "$CLONE/$EV"/payload-rc1-*.raw.txt >/dev/null 2>&1; then
      bad "sobrou payload RAW na arvore do clone"
    else ok "nenhum payload RAW na arvore (quarentena funcionou)"; fi
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
printf 'VERDICT: GO-WITH-CONDITIONS cobertura declarada no README-rc1.\n' >> "$out"
printf 'stub: payload de %s bytes\n' "$bytes"
FLAKYEOF
    chmod 0755 "$FLAKY"
    # shellcheck disable=SC2086
    if ( cd "$CLONE2" && env CODEX_BIN="$FLAKY" CODEX_MODEL=stub-model HOME="$SCRATCH/fakehome2" \
         RC1_RETRY_UNIT_SECONDS=0 GNUPGHOME="$GH" $SELFTEST_ENV $PROBE_ENV \
         bash "$EV/run-rc1-repass.sh" ) > "$SCRATCH/runner2.log" 2>&1; then
      ok "B2: o runner sobrevive a UMA morte por capacidade em cada parte (rc 0)"
    else bad "B2: runner rc!=0 com o stub instavel"; sed -n '1,25p' "$SCRATCH/runner2.log"; fi
    _b2="$(grep -c 'tentativa(s) MORTA(s) por capacidade' "$CLONE2/$EV/PROVENANCE-rc1.md" 2>/dev/null)" || _b2=0
    if [ "$_b2" = "4" ]; then ok "B2: a PROVENANCE declara a morte por capacidade nas 4 partes"
    else bad "B2: a PROVENANCE declara $_b2 morte(s) (esperado 4)"; fi
    _b2_left="$(find "$CLONE2/$EV" -maxdepth 1 \( -name '.codex-dead-*' -o -name '*.flaky-seen' \) | grep -c . )" || _b2_left=0
    if [ "$_b2_left" = "0" ]; then ok "B2: nenhum marcador de tentativa sobrou na arvore"
    else bad "B2: sobraram $_b2_left marcador(es) de tentativa na arvore"; fi
  else bad "B2: clone local para o stub instavel falhou"; fi
fi

say "B3. o modelo vem da tabela RAIZ de ~/.codex/config.toml, ou de CODEX_MODEL, ou e recusa"
_b3="$SCRATCH/b3"; mkdir -p "$_b3/home/.codex" "$_b3/empty"
printf '%s\n' '# config de fixture' 'model = "fixture-root-model"' 'model_reasoning_effort = "max"' \
  '' '[profiles.other]' 'model = "fixture-PROFILE-model"' > "$_b3/home/.codex/config.toml"
{
  printf 'set -uo pipefail\ndie() { printf "FATAL: %%s\\n" "$*" >&2; exit 1; }\n'
  awk '/^# --- 1b\. MODELO explicito/{f=1} /^OVERALL=0$/{f=0} f' "$ROOT/$EV/run-rc1-repass.sh"
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
          GNUPGHOME="$GH" $SELFTEST_ENV RC1_PROBE_REPORT_ONLY=1 bash "$EV/run-rc1-repass.sh" ) > "$2" 2>&1
    else
      ( cd "$1" && env CODEX_BIN="$STUB" CODEX_MODEL=stub-model HOME="$SCRATCH/fakehome5" \
          GNUPGHOME="$GH" RC1_PROBE_REPORT_ONLY=1 bash "$EV/run-rc1-repass.sh" ) > "$2" 2>&1
    fi
  }
  _b5="$SCRATCH/clone5"
  if git clone --quiet --local --shared "$UPSTREAM" "$_b5" 2>/dev/null \
     && git -C "$_b5" checkout --quiet --detach "$CAND" 2>/dev/null \
     && printf '%s\n' "$CAND" > "$_b5/$EV/CANDIDATE.sha" && git -C "$_b5" tag -d v1.4.1 >/dev/null 2>&1; then
    if _b5_run "$_b5" "$SCRATCH/b5.log" 1; then bad "B5: o runner seguiu SEM a tag base local"
    elif grep -q 'a tag base v1.4.1 nao existe neste repositorio' "$SCRATCH/b5.log" \
         && ! ls "$_b5/$EV"/payload-rc1-* >/dev/null 2>&1; then
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
    if PYTHONDONTWRITEBYTECODE=1 python3 - "$ROOT/$EV/probe-conditions-rc1.py" "$_p1" > "$SCRATCH/p1.log" 2>&1 <<'PYP1'
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
    if ( cd "$_p2" && PYTHONDONTWRITEBYTECODE=1 python3 "$EV/probe-conditions-rc1.py" --root "$_p2" \
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
    if ( cd "$_p3" && PYTHONDONTWRITEBYTECODE=1 python3 "$EV/probe-conditions-rc1.py" --root "$_p3" \
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
    if ( cd "$_p4" && PYTHONDONTWRITEBYTECODE=1 python3 "$EV/probe-conditions-rc1.py" --root "$_p4" \
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
    if ( cd "$_p5" && PYTHONDONTWRITEBYTECODE=1 python3 "$EV/probe-conditions-rc1.py" --root "$_p5" \
           --base refs/tags/v1.4.1 --head HEAD --only C2-carried-1.4.1 ) > "$SCRATCH/p5.log" 2>&1; then
      bad "P5: veredito pinado alterado passou pela sonda"
    elif grep -q "^FAIL C2-carried-1.4.1: veredito pinado por .* nao tem o sha256 pinado: $_p5v" "$SCRATCH/p5.log"; then
      ok "P5 (controle vermelho): veredito que um envelope pina por condicao, alterado, e recusado pelo nome"
    else bad "P5: recusa sem o motivo"; sed -n '1,6p' "$SCRATCH/p5.log"; fi
  else bad "P5: fixture do veredito pinado falhou"; fi
  # P6 — o registro do ledger (PreToolUse + PostToolUse) contra o hook da BASE: la o
  # PreToolUse ja grava o snapshot, e a mesma funcao da sonda (condicao 3) tem de RECUSAR.
  if [ -d "$_p1/.claude/hooks" ]; then
    if PYTHONDONTWRITEBYTECODE=1 python3 - "$ROOT/$EV/probe-conditions-rc1.py" "$_p1" > "$SCRATCH/p6.log" 2>&1 <<'PYP6'
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
    if ( cd "$_p7" && PYTHONDONTWRITEBYTECODE=1 python3 "$EV/probe-conditions-rc1.py" --root "$_p7" \
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
    if ( cd "$_p8" && PYTHONDONTWRITEBYTECODE=1 python3 "$EV/probe-conditions-rc1.py" --root "$_p8" \
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
    if ( cd "$_p9" && PYTHONDONTWRITEBYTECODE=1 python3 "$EV/probe-conditions-rc1.py" --root "$_p9" \
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
    if ( cd "$_p10" && PYTHONDONTWRITEBYTECODE=1 python3 "$EV/probe-conditions-rc1.py" --root "$_p10" \
           --base refs/tags/v1.4.1 --head HEAD --only C1-annex-v1.4.0 ) > "$SCRATCH/p10.log" 2>&1; then
      bad "P10: um arquivo citado da v1.4.0 fora das classes passou pela sonda"
    elif grep -qF 'FAIL C1-annex-v1.4.0: arquivo citado pelos vereditos da v1.4.0 muda fora das classes declaradas: AGENTS.md' "$SCRATCH/p10.log"; then
      ok "P10 (controle vermelho): arquivo citado da v1.4.0 fora das classes declaradas e recusado pelo nome (condicao 1)"
    else bad "P10: recusa sem o motivo"; sed -n '1,6p' "$SCRATCH/p10.log"; fi
  else bad "P10: fixture do AGENTS.md falhou"; fi
else printf '  (P pulado: sem upstream ou sem base)\n'; fi

# ===========================================================================
say "C. gerador de envelope com chave GPG DESCARTAVEL"
if [ -n "$CLONE" ] && [ -f "$CLONE/$EV/MANIFEST-rc1.sha256" ]; then
  # A chave descartavel e a da secao K0.
  CLAUDE_STUB_DIR="$SCRATCH/claude-stub"; mkdir -p "$CLAUDE_STUB_DIR"
  printf '#!/bin/bash\necho "2.1.999 (Claude Code)"\n' > "$CLAUDE_STUB_DIR/claude"
  chmod 0755 "$CLAUDE_STUB_DIR/claude"
  if [ -n "${FPR:-}" ]; then
    VF="$CLONE/$PLAN_DIR/verdict-fields-v1.4.2-rc.1.md"
    COND="$CLONE/$EV/CONDITIONS-rc1.reviewed.md"
    _gen="$SCRATCH/gen.log"
    _c_reseal() {
      local _mf="" n
      for n in 1 2 3 4; do
        _mf="$_mf payload-rc1-$n.redacted.txt diff-rc1-$n.patch"
        _mf="$_mf paths-rc1-$n.manifest.txt verdict-rc1-$n.txt transcript-rc1-$n.log"
      done
      # shellcheck disable=SC2086
      ( cd "$CLONE/$EV" && shasum -a 256 $_mf PROVENANCE-rc1.md CANDIDATE.sha \
          run-rc1-repass.sh CONDITIONS-rc1.reviewed.md probe-rc1.txt > MANIFEST-rc1.sha256 )
    }
    # C0 — a sonda das condicoes: a evidencia de um run cuja sonda NAO ficou verde (o
    # modo REPORT-ONLY do harness) e recusada pelo gerador, nomeando a sonda. So quando o
    # P0 ficou vermelho; depois, PLUMBING declarado: a linha vira verde para o resto da
    # tubulacao (o F prova a recusa da linha vermelha em qualquer caso).
    if [ -n "$PROBE_ENV" ]; then
      if ( cd "$CLONE" && RC1_SELFTEST=1 RC1_SELFTEST_SCRATCH="$SCRATCH" \
           RC1_SELFTEST_SIGNER_FPR="$FPR" GNUPGHOME="$GH" PATH="$CLAUDE_STUB_DIR:$PATH" \
           python3 "$PLAN_DIR/gen-envelope-rc1.py" --stage fields \
             --parent "$CAND" --conditions-file "$COND" ) > "$SCRATCH/gen-c0.log" 2>&1; then
        bad "C0: o gerador ACEITOU a evidencia de um run com a sonda vermelha"
      elif grep -q 'sonda das condicoes' "$SCRATCH/gen-c0.log"; then
        ok "C0 (controle vermelho): a evidencia REAL do run com a sonda vermelha e recusada pelo gerador, nomeando a sonda"
      else bad "C0: recusa sem nomear a sonda"; sed -n '1,6p' "$SCRATCH/gen-c0.log"; fi
      python3 - "$CLONE/$EV/PROVENANCE-rc1.md" <<'PYC0'
import pathlib, re, sys
p = pathlib.Path(sys.argv[1])
t = p.read_text(encoding="utf-8")
p.write_text(re.sub(r"(?m)^- sonda das condicoes: .*$",
                    "- sonda das condicoes: verde (PLUMBING do harness: C0)", t, count=1),
             encoding="utf-8")
PYC0
      _c_reseal || bad "C0: regeneracao do MANIFEST falhou"
    fi
    # C1 — CONTROLE VERMELHO: evidencia de um run com STUB nao pode virar
    # envelope de release. O gerador tem de RECUSAR, nomeando o motivo.
    if ( cd "$CLONE" && RC1_SELFTEST=1 RC1_SELFTEST_SCRATCH="$SCRATCH" \
         RC1_SELFTEST_SIGNER_FPR="$FPR" GNUPGHOME="$GH" PATH="$CLAUDE_STUB_DIR:$PATH" \
         python3 "$PLAN_DIR/gen-envelope-rc1.py" --stage fields \
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
    python3 - "$CLONE/$EV/PROVENANCE-rc1.md" "$_real_ver" "$_real_sha" <<'PYPROV'
import sys, pathlib, re
p = pathlib.Path(sys.argv[1])
t = p.read_text(encoding="utf-8")
t = re.sub(r"^- codex: .*$",
           "- codex: %s / aarch64-apple-darwin / payload %s" % (sys.argv[2], sys.argv[3]),
           t, count=1, flags=re.M)
# PLUMBING declarado: se o P0 deixou a sonda vermelha (lane ainda nao landada), a linha
# dela vira verde AQUI para que o resto da tubulacao do gerador rode; o F prova que o
# gerador recusa a linha vermelha.
t = re.sub(r"^- sonda das condicoes: .*$",
           "- sonda das condicoes: verde (PLUMBING do harness: C2)", t, count=1, flags=re.M)
p.write_text(t, encoding="utf-8")
PYPROV
    _mf=""
    for n in 1 2 3 4; do
      _mf="$_mf payload-rc1-$n.redacted.txt diff-rc1-$n.patch"
      _mf="$_mf paths-rc1-$n.manifest.txt verdict-rc1-$n.txt transcript-rc1-$n.log"
    done
    # shellcheck disable=SC2086
    ( cd "$CLONE/$EV" && shasum -a 256 $_mf PROVENANCE-rc1.md CANDIDATE.sha \
        run-rc1-repass.sh CONDITIONS-rc1.reviewed.md probe-rc1.txt > MANIFEST-rc1.sha256 ) || bad "C2: regeneracao do MANIFEST falhou"
    if ( cd "$CLONE" && RC1_SELFTEST=1 RC1_SELFTEST_SCRATCH="$SCRATCH" \
         RC1_SELFTEST_SIGNER_FPR="$FPR" GNUPGHOME="$GH" PATH="$CLAUDE_STUB_DIR:$PATH" \
         python3 "$PLAN_DIR/gen-envelope-rc1.py" --stage fields \
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
      if ( cd "$CLONE" && RC1_SELFTEST=1 RC1_SELFTEST_SCRATCH="$SCRATCH" \
           RC1_SELFTEST_SIGNER_FPR="$FPR" GNUPGHOME="$GH" PATH="$_cbad:$PATH" \
           python3 "$PLAN_DIR/gen-envelope-rc1.py" --stage fields \
             --parent "$CAND" --conditions-file "$COND" ) > "$SCRATCH/gen-cbad.log" 2>&1; then
        bad "C2b: o gerador ACEITOU um claude --version ilegivel"
      elif grep -q 'claude --version' "$SCRATCH/gen-cbad.log" \
           && [ "$(shasum -a 256 "$VF" | awk '{print $1}')" = "$_vf_sha" ]; then
        ok "C2b (controle vermelho): claude --version ilegivel e recusa nomeada; os fields do C2 ficaram intactos"
      else bad "C2b: recusa sem nomear o claude --version (ou os fields mudaram)"; sed -n '1,6p' "$SCRATCH/gen-cbad.log"; fi
      # C3 — assinatura descartavel + montagem do envelope.
      GNUPGHOME="$GH" gpg --batch --quiet --armor --detach-sign -u "$FPR" "$VF" 2>/dev/null
      if ( cd "$CLONE" && RC1_SELFTEST=1 RC1_SELFTEST_SCRATCH="$SCRATCH" \
           RC1_SELFTEST_SIGNER_FPR="$FPR" GNUPGHOME="$GH" PATH="$CLAUDE_STUB_DIR:$PATH" \
           python3 "$PLAN_DIR/gen-envelope-rc1.py" --stage envelope \
             --sig "$VF.asc" ) > "$SCRATCH/env.log" 2>&1; then
        ok "C3: gen --stage envelope com assinatura descartavel"
      else bad "C3: gen --stage envelope"; sed -n '1,12p' "$SCRATCH/env.log"; fi
      _envf="$CLONE/.claude/governance/pair-rail-verdict-v1.4.2-rc.1.md"
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
_envf="${CLONE:+$CLONE/.claude/governance/pair-rail-verdict-v1.4.2-rc.1.md}"
if [ -n "$CLONE" ] && [ -f "$_envf" ] && [ -f "$CLONE/$EV/MANIFEST-rc1.sha256" ]; then
  _e_vd=".claude/governance/pair-rail-verdict-v1.4.2-rc.1.md"
  _e_vf="$PLAN_DIR/verdict-fields-v1.4.2-rc.1.md"
  _e_list="$SCRATCH/e.list"
  { awk '{print $2}' "$CLONE/$EV/MANIFEST-rc1.sha256" | sed "s|^|$EV/|"
    printf '%s\n' "$EV/MANIFEST-rc1.sha256" "$EV/README-rc1.md"
    [ -f "$CLONE/$EV/CONDITIONS-rc1.md" ] && printf '%s\n' "$EV/CONDITIONS-rc1.md"
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
  _e_guard() { python3 "$ROOT/.claude/scripts/local/_release_tag_guard.py" delta --repo "$1" --tag v1.4.2-rc.1; }
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
    printf '\nTEST ONLY: texto nao revisado depois do candidato.\n' >> "$_e1b/$EV/README-rc1.md"
    if ( cd "$_e1b" && xargs git add -- < "$_e_list" ) \
       && _e_commit "$_e1b" "TEST ONLY: evidence plus unreviewed README"; then
      if _e_guard "$_e1b" > "$SCRATCH/e1b.guard" 2>&1; then
        bad "E1b: README nao revisado foi aceito pela allowlist"
      elif grep -qF 'README-rc1.md' "$SCRATCH/e1b.guard"; then
        ok "E1b: README alterado apos a revisao continua recusado por nome"
      else bad "E1b: recusa sem identificar README-rc1.md"; fi
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

  # E3 — o passo 11 do OWNER-RC1-CUT.sh, VERBATIM (extraido entre os seus
  # marcadores, com say/bell/mark_step/die shimados), sobre um clone com a
  # evidencia + fields + envelope + .asc untracked. Esperado: UM commit sobre o
  # candidato, com veredito + fields + evidencia, o .asc movido para o backup
  # do HOME (desviado), guard local e bind do servidor fechando.
  _cut="$ROOT/$PLAN_DIR/OWNER-RC1-CUT.sh"
  _e3="$SCRATCH/e3"; _e3home="$SCRATCH/e3home"; mkdir -p "$_e3home"
  if _e_prep "$_e3" && cp "$CLONE/$_e_vf.asc" "$_e3/$_e_vf.asc"; then
    {
      printf '#!/bin/bash\nset -euo pipefail\n'
      printf 'say() { :; }; bell() { :; }; mark_step() { :; }\n'
      printf 'die() { printf "FAIL: %%s\\n" "$*" >&2; exit 1; }\n'
      printf 'PLAN_DIR=%s; EV=%s; TAG=v1.4.2-rc.1\n' "$PLAN_DIR" "$EV"
      printf 'COND="$EV/CONDITIONS-rc1.md"; VF="$PLAN_DIR/verdict-fields-$TAG.md"\n'
      printf 'VD=".claude/governance/pair-rail-verdict-$TAG.md"; CAND=%s\n' "$CAND"
      printf 'GEN=%s\n' "$PLAN_DIR/gen-envelope-rc1.py"
      awk '/^evidence_list\(\) \{$/,/^\}$/' "$_cut"
      awk '/^if should 11; then$/{f=1; next} /^  mark_step 11$/{f=0} f' "$_cut"
    } > "$SCRATCH/e3.sh"
    _e3_n="$(grep -c 'git commit -q -F -' "$SCRATCH/e3.sh" || true)"
    [ "$_e3_n" = "1" ] || bad "E3: o bloco extraido nao contem exatamente 1 commit (tem $_e3_n)"
    if ( cd "$_e3" && HOME="$_e3home" GNUPGHOME="$GH" RC1_SELFTEST=1 \
         RC1_SELFTEST_SCRATCH="$SCRATCH" RC1_SELFTEST_SIGNER_FPR="$FPR" PATH="$CLAUDE_STUB_DIR:$PATH" \
         GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=commit.gpgsign \
         GIT_CONFIG_VALUE_0=false bash "$SCRATCH/e3.sh" ) > "$SCRATCH/e3.log" 2>&1; then
      ok "E3: o passo 11 verbatim corre limpo sobre o clone (rc 0)"
    else bad "E3: o passo 11 verbatim falhou"; sed -n '1,12p' "$SCRATCH/e3.log"; fi
    if [ "$(git -C "$_e3" rev-parse HEAD^ 2>/dev/null)" = "$CAND" ]; then
      ok "E3: o commit senta DIRETAMENTE sobre o candidato"
    else bad "E3: pai do commit != candidato"; fi
    if git -C "$_e3" log -1 --format=%s | grep -qF 'verdito pair-rail v1.4.2-rc.1 assinado'; then
      ok "E3: assunto do commit sobreviveu (CM-07)"
    else bad "E3: assunto do commit inesperado: $(git -C "$_e3" log -1 --format=%s | cut -c1-80)"; fi
    _e3_files="$(git -C "$_e3" show --name-only --format= HEAD)"
    if printf '%s\n' "$_e3_files" | grep -qxF "$_e_vd" \
       && printf '%s\n' "$_e3_files" | grep -qxF "$_e_vf" \
       && printf '%s\n' "$_e3_files" | grep -qxF "$EV/MANIFEST-rc1.sha256"; then
      ok "E3: o commit carrega veredito + fields + MANIFEST ($(printf '%s\n' "$_e3_files" | grep -c .) caminhos)"
    else bad "E3: o commit nao carrega veredito/fields/MANIFEST"; fi
    if [ -f "$_e3home/.rc2-backup/verdict-fields-v1.4.2-rc.1.md.asc" ] && [ ! -e "$_e3/$_e_vf.asc" ]; then
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
     && cp "$CLONE/$_e_vf.asc" "$_e3bhome/.rc2-backup/verdict-fields-v1.4.2-rc.1.md.asc"; then
    if ( cd "$_e3b" && HOME="$_e3bhome" GNUPGHOME="$GH" RC1_SELFTEST=1 \
         RC1_SELFTEST_SCRATCH="$SCRATCH" RC1_SELFTEST_SIGNER_FPR="$FPR" PATH="$CLAUDE_STUB_DIR:$PATH" \
         GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=commit.gpgsign \
         GIT_CONFIG_VALUE_0=false bash "$SCRATCH/e3.sh" ) > "$SCRATCH/e3b.log" 2>&1 \
       && grep -q 'assinatura restaurada do backup' "$SCRATCH/e3b.log" \
       && [ "$(git -C "$_e3b" rev-parse HEAD^ 2>/dev/null)" = "$CAND" ] \
       && [ ! -e "$_e3b/$_e_vf.asc" ]; then
      ok "E3b: retomada do passo 11 com o .asc so no backup: restaurado, verificado e commitado sobre o candidato"
    else bad "E3b: a retomada do passo 11 falhou"; sed -n '1,12p' "$SCRATCH/e3b.log"; fi
  else bad "E3b: preparacao falhou"; fi
  # E3c — a RETOMADA do passo 11 que morreu entre o `git add` e o `git commit`: o .asc no
  # backup e parte da lista literal JA staged. O passo 11 verbatim desfaz o staging (so
  # caminhos da lista; nada foi commitado), refaz e commita sobre o candidato.
  _e3_env() {  # $1 = clone, $2 = HOME, $3 = log
    ( cd "$1" && HOME="$2" GNUPGHOME="$GH" RC1_SELFTEST=1 \
         RC1_SELFTEST_SCRATCH="$SCRATCH" RC1_SELFTEST_SIGNER_FPR="$FPR" PATH="$CLAUDE_STUB_DIR:$PATH" \
         GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=commit.gpgsign \
         GIT_CONFIG_VALUE_0=false bash "$SCRATCH/e3.sh" ) > "$3" 2>&1
  }
  _e3c="$SCRATCH/e3c"; _e3chome="$SCRATCH/e3chome"; mkdir -p "$_e3chome/.rc2-backup"
  if [ -f "$SCRATCH/e3.sh" ] && _e_prep "$_e3c" \
     && cp "$CLONE/$_e_vf.asc" "$_e3chome/.rc2-backup/verdict-fields-v1.4.2-rc.1.md.asc" \
     && git -C "$_e3c" add -- "$_e_vf" "$_e_vd" "$EV/MANIFEST-rc1.sha256"; then
    if _e3_env "$_e3c" "$_e3chome" "$SCRATCH/e3c.log" \
       && grep -q 'staging de uma tentativa anterior deste passo desfeito' "$SCRATCH/e3c.log" \
       && [ "$(git -C "$_e3c" rev-parse HEAD^ 2>/dev/null)" = "$CAND" ] \
       && git -C "$_e3c" diff --cached --quiet \
       && git -C "$_e3c" show --name-only --format= HEAD | grep -qxF "$_e_vd"; then
      ok "E3c: retomada do passo 11 com a lista literal ja staged: o staging e desfeito e refeito, e o commit senta sobre o candidato"
    else bad "E3c: a retomada do passo 11 com staging anterior falhou"; sed -n '1,12p' "$SCRATCH/e3c.log"; fi
  else bad "E3c: preparacao falhou"; fi
  # E3d (controle vermelho): um caminho FORA da lista literal staged — recusa, nada commitado.
  _e3d="$SCRATCH/e3d"; _e3dhome="$SCRATCH/e3dhome"; mkdir -p "$_e3dhome/.rc2-backup"
  if [ -f "$SCRATCH/e3.sh" ] && _e_prep "$_e3d" \
     && cp "$CLONE/$_e_vf.asc" "$_e3dhome/.rc2-backup/verdict-fields-v1.4.2-rc.1.md.asc" \
     && printf 'x\n' > "$_e3d/TEST-ONLY-stray.txt" \
     && git -C "$_e3d" add -- TEST-ONLY-stray.txt "$_e_vf"; then
    if _e3_env "$_e3d" "$_e3dhome" "$SCRATCH/e3d.log"; then bad "E3d: staging com caminho fora da lista passou pelo passo 11"
    elif grep -q 'com caminho FORA da lista' "$SCRATCH/e3d.log" && grep -q 'TEST-ONLY-stray.txt' "$SCRATCH/e3d.log" \
         && [ "$(git -C "$_e3d" rev-parse HEAD)" = "$CAND" ]; then
      ok "E3d (controle vermelho): um caminho fora da lista literal staged e recusado pelo nome, e nada e commitado"
    else bad "E3d: recusa sem o nome (ou houve commit)"; sed -n '1,10p' "$SCRATCH/e3d.log"; fi
  else bad "E3d: preparacao falhou"; fi

  # E4 — o passo 2: `release.sh bump` num clone local do candidato (a forma que o
  # CUT usa porque o driver recusa porcelain nao vazio e a arvore viva carrega
  # a evidencia untracked). Numa release de PATCH o bump e REAL enquanto a relmeta
  # ja landou e o bump ainda nao: aceita-se (a) no-op com HEAD inalterado ou (b) UM
  # commit `release: v<alvo>` direto sobre o candidato — e nos dois casos a SEGUNDA
  # corrida tem de ser no-op (a idempotencia que o passo 2 do CUT pressupoe).
  _e4="$SCRATCH/e4"
  if git clone --quiet --local --no-hardlinks "$UPSTREAM" "$_e4" 2>/dev/null \
     && fixture_git_identity "$_e4"; then
    _e4_head="$(git -C "$_e4" rev-parse HEAD)"
    _e4_tb="$(awk -F'"' '/^TARGET_BASE=/{print $2; exit}' "$_e4/.claude/scripts/local/release.sh")"
    _e4_rc=0
    ( cd "$_e4" && bash .claude/scripts/local/release.sh bump --rc 1 \
        --today "$(date -u +%Y-%m-%d)" --npm-readme-reviewed ) > "$SCRATCH/e4.log" 2>&1 || _e4_rc=$?
    _e4_new="$(git -C "$_e4" rev-parse HEAD)"
    if [ "$_e4_rc" -ne 0 ]; then
      bad "E4: bump no clone rc=$_e4_rc"; grep -E 'oracle|FAIL|no-op' "$SCRATCH/e4.log" | head -6
    elif [ "$_e4_new" = "$_e4_head" ] && grep -q 'no-op' "$SCRATCH/e4.log"; then
      ok "E4: bump --rc 1 no clone e no-op (a arvore ja esta em $_e4_tb)"
    elif [ "$(git -C "$_e4" rev-parse 'HEAD^')" = "$_e4_head" ] \
         && [ "$(git -C "$_e4" log -1 --format=%s)" = "release: v$_e4_tb" ]; then
      ok "E4: bump --rc 1 produziu UM commit 'release: v$_e4_tb' direto sobre o candidato"
    else
      bad "E4: o bump moveu o HEAD de forma inesperada: $(git -C "$_e4" log -1 --format=%s | cut -c1-60)"
    fi
    _e4_rc2=0
    ( cd "$_e4" && bash .claude/scripts/local/release.sh bump --rc 1 \
        --today "$(date -u +%Y-%m-%d)" --npm-readme-reviewed ) > "$SCRATCH/e4b.log" 2>&1 || _e4_rc2=$?
    if [ "$_e4_rc2" -eq 0 ] && grep -q 'no-op' "$SCRATCH/e4b.log" \
       && [ "$(git -C "$_e4" rev-parse HEAD)" = "$_e4_new" ]; then
      ok "E4: a SEGUNDA corrida do bump e no-op (idempotente)"
    else bad "E4: a segunda corrida do bump NAO foi no-op (rc=$_e4_rc2)"; fi
  else bad "E4: clone local para o bump falhou"; fi

  # E4p — o candidato REAL e o commit do bump: a sonda que o passo 5 roda contra ele
  # (escopo das partes e tamanhos, a classe dos arquivos citados da v1.4.0) tem de passar
  # DEPOIS do bump, com os sitios de versao na faixa.
  if [ -n "${_e4_new:-}" ] && [ "$_e4_new" != "${_e4_head:-}" ]; then
    if ( cd "$_e4" && PYTHONDONTWRITEBYTECODE=1 python3 "$EV/probe-conditions-rc1.py" --root "$_e4" \
           --base refs/tags/v1.4.1 --head HEAD --only C1-annex-v1.4.0,C11-scope --sizes ) > "$SCRATCH/e4p.log" 2>&1; then
      ok "E4p: a sonda do passo 5 passa sobre o commit do bump (escopo, tamanhos e a classe dos citados da v1.4.0)"
    else bad "E4p: a sonda do passo 5 reprova sobre o commit do bump"; grep -E '^(FAIL|INFRA)' "$SCRATCH/e4p.log" | sed -n '1,8p'; fi
  else printf '  (E4p pulado: o bump foi no-op)\n'; fi

  # E7 — o passo 2 do OWNER-RC1-CUT.sh VERBATIM (extraido entre os seus marcadores),
  # com um driver STUB no lugar do release.sh: UM commit `release: v1.4.2` direto sobre
  # o HEAD e trazido por fast-forward; no-op segue; arquivo nao commitado, dois commits
  # ou outro assunto sao recusados ANTES de qualquer fetch/merge, e o HEAD nao anda.
  _e7="$SCRATCH/e7"; mkdir -p "$_e7/tmp"
  {
    printf '#!/bin/bash\nset -euo pipefail\n'
    printf 'say() { :; }\nmark_step() { printf "E7-STEP-%%s-MARCADO\\n" "$1"; }\n'
    printf 'die() { printf "FAIL: %%s\\n" "$*" >&2; exit 1; }\n'
    printf 'ROOT="$(pwd -P)"; RELEASE="$E7_DRIVER"; TODAY=2026-09-24; BASE=1.4.2; RCN=1; RESTAMP=""\n'
    printf 'STATE="$E7_STATE"\n'
    awk '/^if should 2; then$/{f=1; next} /^  mark_step 2$/{print; f=0} f' "$ROOT/$PLAN_DIR/OWNER-RC1-CUT.sh"
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
     && [ "$(awk '$1=="SHA-2"{print $2}' "$_e7/noop.state")" = "$(cat "$_e7/noop.head0")" ]; then
    ok "E7: passo 2 verbatim com driver no-op segue, grava SHA-2P/SHA-2 e marca o passo"
  else bad "E7: passo 2 verbatim recusou o no-op"; sed -n '1,8p' "$_e7/noop.log"; fi
  if _e7_run commit && grep -q 'bump commitado' "$_e7/commit.log" \
     && [ "$(git -C "$_e7/commit" rev-parse HEAD^)" = "$(cat "$_e7/commit.head0")" ] \
     && [ "$(git -C "$_e7/commit" log -1 --format=%s)" = "release: v1.4.2" ] \
     && [ "$(awk '$1=="SHA-2P"{print $2}' "$_e7/commit.state")" = "$(cat "$_e7/commit.head0")" ] \
     && [ "$(awk '$1=="SHA-2"{print $2}' "$_e7/commit.state")" = "$(git -C "$_e7/commit" rev-parse HEAD)" ]; then
    ok "E7: UM commit 'release: v1.4.2' sobre o HEAD e trazido por fast-forward; SHA-2P = de onde partiu, SHA-2 = onde terminou"
  else bad "E7: o commit do bump nao foi trazido como devia"; sed -n '1,8p' "$_e7/commit.log"; fi
  for _c in dirty two subject; do
    if _e7_run "$_c"; then bad "E7: driver '$_c' passou pelo passo 2"
    elif grep -q 'NADA foi trazido para main' "$_e7/$_c.log" && ! grep -q 'E7-STEP-2-MARCADO' "$_e7/$_c.log" \
         && [ "$(git -C "$_e7/$_c" rev-parse HEAD)" = "$(cat "$_e7/$_c.head0")" ]; then
      ok "E7 (controle vermelho): driver '$_c' e recusado no passo 2, antes de fetch/merge, e o HEAD nao anda"
    else bad "E7: driver '$_c' recusado sem o motivo (ou o HEAD andou)"; sed -n '1,8p' "$_e7/$_c.log"; fi
  done

  # E5 — evidence_complete_for() (passo 6): evidencia sintetica, um positivo e
  # quatro negativos (cada fonte de verdade mutada por vez).
  _e5="$SCRATCH/e5"
  _e5_run() {  # $1 = mutacao: none | manifest | rc | prov-sha | cand-sha
    local X=0123456789abcdef0123456789abcdef01234567 Y=fedcba9876543210fedcba9876543210fedcba98 d
    d="$_e5/$1"; mkdir -p "$d"
    printf 'a\n' > "$d/x.txt"; printf 'b\n' > "$d/y.txt"
    ( cd "$d" && shasum -a 256 x.txt y.txt > MANIFEST-rc1.sha256 )
    printf -- '- Base: v1.4.1 (o) .. Candidato: %s (PRE-tag; base resolvida no run)\nRUNNER-OVERALL: rc=0\n' "$X" > "$d/PROVENANCE-rc1.md"
    printf '%s\n' "$X" > "$d/CANDIDATE.sha"
    case "$1" in
      manifest) printf 'z\n' >> "$d/x.txt" ;;
      rc)       sed -i '' 's/rc=0/rc=1/' "$d/PROVENANCE-rc1.md" ;;
      prov-sha) sed -i '' "s/$X/$Y/" "$d/PROVENANCE-rc1.md" ;;
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
          --verdict-file "$_e_vd" --parent-sha "$CAND" --release-tag v1.4.2-rc.1 \
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
_cut="$ROOT/$PLAN_DIR/OWNER-RC1-CUT.sh"
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
  ok "G: o release.sh desta arvore chama o gpg da sonda com --yes (a relmeta-142 landou, ou a projecao a simula)"
else bad "G: o release.sh desta arvore NAO tem o --yes na sonda — a relmeta-142 nao esta aqui"; fi

# ===========================================================================
say "K. G0: o kit tem de estar COMMITADO (assert_kit_committed)"
_k="$SCRATCH/k"
if git init --quiet "$_k" 2>/dev/null && fixture_git_identity "$_k" \
   && ( cd "$_k" && mkdir -p ev && printf 'r\n' > ev/run.sh && printf 'g\n' > gen.py \
        && git add -- ev/run.sh gen.py && git commit -q -m kit ); then
  { printf '#!/bin/bash\nset -euo pipefail\n'
    printf 'die() { printf "FAIL: %%s\\n" "$*" >&2; exit 1; }\n'
    printf 'TAG=v1.4.2-rc.1; KIT_TRACKED="ev/run.sh gen.py ev/README-rc1.md"\n'
    awk '/^assert_kit_committed\(\) \{$/,/^\}$/' "$_cut"
    printf 'assert_kit_committed\n'; } > "$SCRATCH/k.sh"
  printf 'readme\n' > "$_k/ev/README-rc1.md"
  if ( cd "$_k" && bash "$SCRATCH/k.sh" ) > "$SCRATCH/k1.log" 2>&1; then bad "K: README untracked passou"
  elif grep -q 'ev/README-rc1.md (NAO rastreado)' "$SCRATCH/k1.log"; then ok "K (controle vermelho): kit untracked e recusado pelo nome"
  else bad "K: recusa sem nomear o untracked"; fi
  ( cd "$_k" && git add ev/README-rc1.md && git commit -q -m readme )
  if ( cd "$_k" && bash "$SCRATCH/k.sh" ) > "$SCRATCH/k2.log" 2>&1; then ok "K: kit commitado e identico ao HEAD passa"
  else bad "K: o caso bom foi recusado"; sed -n '1,6p' "$SCRATCH/k2.log"; fi
  printf 'editado\n' >> "$_k/gen.py"
  if ( cd "$_k" && bash "$SCRATCH/k.sh" ) > "$SCRATCH/k3.log" 2>&1; then bad "K: kit modificado passou"
  elif grep -q 'gen.py (diferente do HEAD)' "$SCRATCH/k3.log"; then ok "K (controle vermelho): kit modificado e recusado pelo nome"
  else bad "K: recusa sem nomear o modificado"; fi
else bad "K: fixture do kit falhou"; fi

# ===========================================================================
say "S. o teto da espera de CI e o conselho do vermelho (estatico sobre o CUT)"
if grep -qF 'CI_WAIT_MAX_MIN="${RC1_CI_WAIT_MAX_MIN:-150}"' "$_cut" \
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
if grep -qF 'ARCHIVE_ROOT="$HOME/.ceo-rc1-archive"' "$_cut" \
   && grep -qF 'Preserve a tentativa, inclusive parcial, FORA do repositorio' "$_cut"; then
  ok "S: a tentativa do re-pass e arquivada FORA do repositorio ($HOME/.ceo-rc1-archive/)"
else bad "S: a rota de arquivo da tentativa nao e FORA do repositorio"; fi

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
  printf 'sleep() { :; }\nCI_WAIT_MAX_MIN=3\n'
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
# O passo 5 VERBATIM (a sonda das condicoes neutralizada: ela tem a secao P) num clone
# com remoto bare local.
_z="$SCRATCH/z"
if git init --quiet --bare "$_z/origin.git" 2>/dev/null \
   && git init --quiet "$_z/w" 2>/dev/null && fixture_git_identity "$_z/w" \
   && ( cd "$_z/w" && printf 'a\n' > a && git add a && git commit -q -m a ) \
   && git -C "$_z/w" remote add origin "$_z/origin.git" \
   && git -C "$_z/w" push -q origin HEAD:refs/heads/main 2>/dev/null; then
  _zc="$(git -C "$_z/w" rev-parse HEAD)"; _zo=fedcba9876543210fedcba9876543210fedcba98; mkdir -p "$_z/w/ev"
  { printf '#!/bin/bash\nset -euo pipefail\n'
    printf 'say() { :; }; mark_step() { :; }; assert_conditions_probe() { :; }\n'
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
  _z_state "$_zo" "$_zo" "$_zc" "$_zc"
  printf '%s' "$_zc" > "$_z/w/ev/CANDIDATE.sha"
  _z0="$(shasum -a 256 "$_z/w/ev/CANDIDATE.sha" | awk '{print $1}')"
  if ( cd "$_z/w" && bash "$SCRATCH/z.sh" ) > "$SCRATCH/z1.log" 2>&1 \
     && grep -q 'mantido byte a byte' "$SCRATCH/z1.log" \
     && [ "$(shasum -a 256 "$_z/w/ev/CANDIDATE.sha" | awk '{print $1}')" = "$_z0" ] \
     && grep -q 'OK: os passos 1, 2 e 4 conferiram o candidato' "$SCRATCH/z1.log"; then
    ok "Z1: o preflight viu o HEAD de onde o bump partiu, o bump e o CI terminaram no candidato; CANDIDATE.sha mantido byte a byte"
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
   && ( cd "$_x/w" && git commit -q --allow-empty -m a && git -c tag.gpgSign=false tag -a -m t v1.4.2-rc.1 ); then
  { printf '#!/bin/bash\nset -euo pipefail\n'
    printf 'die() { printf "FAIL: %%s\\n" "$*" >&2; exit 1; }\n'
    printf 'say() { :; }; bell() { :; }; sleep() { :; }; should() { return 0; }\n'
    printf 'mark_step() { printf "X-STEP-%%s-MARCADO\\n" "$1"; }\n'
    printf 'verdict_deadline() { printf "PRAZO-STUB"; }\n'
    printf 'TAG=v1.4.2-rc.1\n'
    awk '/^if should 17; then$/,/^fi$/' "$_cut"; } > "$SCRATCH/x.sh"
  _x_run() {  # $1 = sequencia (uma linha por chamada do gh), $2 = log
    rm -f -- "$_x/cnt"
    ( cd "$_x/w" && PATH="$_x/bin:$PATH" X_CNT="$_x/cnt" X_SEQ="$1" bash "$SCRATCH/x.sh" ) > "$2" 2>&1
  }
  for _xc in cancelled timed_out startup_failure failure; do
    if _x_run "completed|$_xc|4242" "$SCRATCH/x-$_xc.log"; then bad "X: release.yml '$_xc' passou pelo passo 17"
    elif grep -q "release.yml terminou '$_xc' para a tag v1.4.2-rc.1 (run 4242)" "$SCRATCH/x-$_xc.log" \
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
  # X2 — passo 18: o await-release-gate que terminou sem success (o de antes de um rerun
  # do release.yml) e recusa com a rota do rerun do npm-publish.yml.
  { printf '#!/bin/bash\nset -euo pipefail\n'
    printf 'die() { printf "FAIL: %%s\\n" "$*" >&2; exit 1; }\n'
    printf 'say() { :; }; bell() { :; }; sleep() { :; }; should() { return 0; }\n'
    printf 'mark_step() { printf "X-STEP-%%s-MARCADO\\n" "$1"; }\n'
    printf 'TAG=v1.4.2-rc.1\n'
    awk '/^if should 18; then$/,/^fi$/' "$_cut"; } > "$SCRATCH/x2.sh"
  _x2_run() {
    rm -f -- "$_x/cnt"
    ( cd "$_x/w" && PATH="$_x/bin:$PATH" X_CNT="$_x/cnt" X_SEQ="$1" bash "$SCRATCH/x2.sh" ) > "$2" 2>&1
  }
  if _x2_run "$(printf 'owner/repo\n4343\nfailure')" "$SCRATCH/x2-fail.log"; then bad "X2: await-release-gate failure passou pelo passo 18"
  elif grep -q "await-release-gate terminou 'failure' (run 4343" "$SCRATCH/x2-fail.log" \
       && grep -q 'gh run rerun 4343 --failed' "$SCRATCH/x2-fail.log"; then
    ok "X2 (controle vermelho): await-release-gate sem success e recusa nomeada, com a rota do rerun do npm-publish.yml"
  else bad "X2: recusa sem a rota"; sed -n '1,6p' "$SCRATCH/x2-fail.log"; fi
  if _x2_run "$(printf 'owner/repo\n4343\n\n4343\nsuccess')" "$SCRATCH/x2-ok.log" \
     && grep -q 'X-STEP-18-MARCADO' "$SCRATCH/x2-ok.log"; then
    ok "X2: gate pendente e depois success marca o passo 18"
  else bad "X2: o caminho verde do passo 18 falhou"; sed -n '1,8p' "$SCRATCH/x2-ok.log"; fi
else bad "X: fixture do passo 17 falhou"; fi

# ===========================================================================
say "Q. passo 19: o piso do publishedAt nunca e 0 (sem .tag-push-epoch, a data da tag)"
_q="$SCRATCH/q"
if git init --quiet "$_q" 2>/dev/null && fixture_git_identity "$_q" \
   && ( cd "$_q" && git commit -q --allow-empty -m a && git -c tag.gpgSign=false tag -a -m t v1.4.2-rc.1 && mkdir -p ev ); then
  { printf '#!/bin/bash\nset -euo pipefail\n'
    printf 'die() { printf "FAIL: %%s\\n" "$*" >&2; exit 1; }\n'
    printf 'EV=ev; TAG="${Q_TAG:-v1.4.2-rc.1}"; _pe="$Q_PE"\n'
    awk '/^  # O piso e o epoch que o passo 16 grava/{f=1} /^  printf .   pre-release confirmado NAO-draft/{f=0} f' "$_cut"
    printf 'printf "Q-OK\\n"\n'; } > "$SCRATCH/q.sh"
  _qt="$(git -C "$_q" for-each-ref --format='%(taggerdate:unix)' refs/tags/v1.4.2-rc.1)"
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
        && git -c tag.gpgSign=false tag -a -m "TEST ONLY" v1.4.2-rc.1 ) \
   && git -C "$_y/w" remote add origin "$_y/origin.git" \
   && git -C "$_y/w" push -q origin HEAD:refs/heads/main 2>/dev/null; then
  { printf '#!/bin/bash\nset -euo pipefail\n'
    printf 'die() { printf "FAIL: %%s\\n" "$*" >&2; exit 1; }\n'
    printf 'TAG=v1.4.2-rc.1\n'
    awk '/^  # main nao pode ter sido REVERTIDO/{f=1} /^  _prerr="\$\(mktemp\)"/{f=0} f' "$_cut"
    printf 'printf "Y-OK\\n"\n'; } > "$SCRATCH/y.sh"
  if ( cd "$_y/w" && bash "$SCRATCH/y.sh" ) > "$SCRATCH/y1.log" 2>&1 && grep -q 'Y-OK' "$SCRATCH/y1.log" \
     && ! grep -q 'AVISO' "$SCRATCH/y1.log"; then ok "Y1: origin/main == commit da tag passa"
  else bad "Y1: o caso igual foi recusado"; sed -n '1,6p' "$SCRATCH/y1.log"; fi
  if ( cd "$_y/w" && printf 'c\n' > c && git add c && git commit -q -m c ) \
     && git -C "$_y/w" push -q origin HEAD:refs/heads/main 2>/dev/null \
     && git -C "$_y/w" checkout -q --detach v1.4.2-rc.1 2>/dev/null; then
    if ( cd "$_y/w" && bash "$SCRATCH/y.sh" ) > "$SCRATCH/y2.log" 2>&1 && grep -q 'Y-OK' "$SCRATCH/y2.log" \
       && grep -q 'AVISO: main andou depois da tag (1 commit' "$SCRATCH/y2.log"; then
      ok "Y2: push alheio DEPOIS da tag passa com AVISO (a tag segue na cadeia first-parent)"
    else bad "Y2: push alheio depois da tag foi recusado"; sed -n '1,6p' "$SCRATCH/y2.log"; fi
  else bad "Y2: preparacao do push alheio falhou"; fi
  if git -C "$_y/w" push -q -f origin "v1.4.2-rc.1^{commit}^:refs/heads/main" 2>/dev/null; then
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
    printf 'RELEASE=rel.sh; BASE_TAG=v1.4.1\n'
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
say "R. o OWNER-RC1-CUT.sh REAL (script inteiro) num clone com remoto bare local"
# O script inteiro roda contra a tag base da fixture (assinada pela chave descartavel,
# aceita pelo seam de auto-teste), com `gh` e `osascript` STUB e um remoto bare local.
# `--g0-only` roda so as pre-condicoes; os estados de retomada sao plantados no
# .cut-state da fixture. Nada sai para a rede.
# Pseudo-terminal (secao T): `script` aloca o pty; o alimentador manda Enter a cada
# segundo ate o comando sair. O rc e o do comando.
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
if [ -n "${CLONE:-}" ] && [ -n "$FPR" ] && [ -n "$BASE_REV" ]; then
  _r="$SCRATCH/r"; mkdir -p "$_r/bin" "$_r/tmp" "$SCRATCH/rhome"
  cat > "$_r/bin/gh" <<'GHREOF'
#!/bin/bash
case "$1 $2" in
  "release view")
    if [ "$3" = "v1.4.2-rc.1" ] && [ -n "${R_RC_RELEASE:-}" ]; then
      printf '%s\n' "$R_RC_RELEASE"
    else echo "release not found" >&2; exit 1; fi ;;
  *) echo "gh stub: chamada inesperada: $*" >&2; exit 9 ;;
esac
GHREOF
  printf '#!/bin/bash\nexit 0\n' > "$_r/bin/osascript"
  chmod 0755 "$_r/bin/gh" "$_r/bin/osascript"
  R_RC_RELEASE=""
  _r_cut() {  # $1 = log, $2.. = argumentos do CUT
    local _log="$1"; shift
    # shellcheck disable=SC2086
    ( cd "$_r/wt" && env PATH="$_r/bin:$PATH" GNUPGHOME="$GH" HOME="$SCRATCH/rhome" \
        TMPDIR="$_r/tmp" R_RC_RELEASE="$R_RC_RELEASE" $SELFTEST_ENV $PROBE_ENV \
        bash "$PLAN_DIR/OWNER-RC1-CUT.sh" "$@" ) < /dev/null > "$_log" 2>&1
  }
  _r_pty() {  # $1 = log, $2.. = argumentos do CUT — o mesmo ambiente, num pty
    local _log="$1"; shift
    # shellcheck disable=SC2086
    ( cd "$_r/wt" && _pty "$_log" env PATH="$_r/bin:$PATH" GNUPGHOME="$GH" \
        HOME="$SCRATCH/rhome" TMPDIR="$_r/tmp" R_RC_RELEASE="" $SELFTEST_ENV $PROBE_ENV \
        bash "$PLAN_DIR/OWNER-RC1-CUT.sh" "$@" )
  }
  _r_state() {  # $1 = ultimo passo concluido (0 = nenhum)
    local _s=1
    : > "$_r/wt/$EV/.cut-state"
    while [ "$_s" -le "$1" ]; do printf 'STEP-%s\n' "$_s" >> "$_r/wt/$EV/.cut-state"; _s=$((_s+1)); done
  }
  if git clone --quiet --bare "$UPSTREAM" "$_r/origin.git" 2>/dev/null \
     && git clone --quiet "$_r/origin.git" "$_r/wt" 2>/dev/null && fixture_git_identity "$_r/wt"; then
    # R1 — G0 verde.
    _r_cut "$_r/pos.log" --g0-only; _r1rc=$?
    if [ "$_r1rc" -eq 0 ] && grep -q 'OK: kit da v1.4.2-rc.1 commitado' "$_r/pos.log" \
       && grep -q 'OK: no plano, so a evidencia deste corte esta fora do git' "$_r/pos.log" \
       && grep -q 'OK: base v1.4.1 (tag anotada, assinada por' "$_r/pos.log" \
       && grep -q 'OK: main, HEAD==origin/main, tag v1.4.2-rc.1 livre' "$_r/pos.log" \
       && grep -q 'OK: o Scope assinado da tag cobre os planos e ADRs de v1.4.1..HEAD' "$_r/pos.log" \
       && grep -q 'OK: CLAUDE.md com [0-9]* bytes' "$_r/pos.log" \
       && grep -q 'FREEZE: do G0 ate o push da tag' "$_r/pos.log" \
       && { grep -q 'OK: sonda das condicoes verde contra' "$_r/pos.log" \
            || { [ -n "$PROBE_ENV" ] && grep -q 'AVISO: sonda rc=1 e RC1_PROBE_REPORT_ONLY=1' "$_r/pos.log"; }; } \
       && grep -q 'G0 verde (--g0-only)' "$_r/pos.log"; then
      ok "R1: G0 real verde (kit commitado, plano sem untracked alheio, base v1.4.1 resolvida, Scope, CLAUDE.md, sonda ${PROBE_ENV:+em REPORT-ONLY }e FREEZE anunciado)"
    else bad "R1: G0 real recusou o caso bom (rc=$_r1rc)"; sed -n '1,40p' "$_r/pos.log"; fi
    # R2 — a tag base ausente (local) e ausente no REMOTO: recusas nomeadas.
    git -C "$_r/wt" tag -d v1.4.1 >/dev/null 2>&1
    if _r_cut "$_r/r2.log" --g0-only; then bad "R2: G0 real seguiu sem a tag base local"
    elif grep -q 'a tag base v1.4.1 nao existe neste repositorio' "$_r/r2.log" \
         && grep -q 'OWNER-GA-CUT.sh' "$_r/r2.log"; then
      ok "R2 (controle vermelho): tag base ausente e recusa NOMEADA (a rota: cortar o GA ou buscar a tag)"
    else bad "R2: recusa sem o nome da base"; sed -n '1,8p' "$_r/r2.log"; fi
    git -C "$_r/wt" fetch -q origin tag v1.4.1 2>/dev/null || bad "R2: restaurar a tag base local falhou"
    git -C "$_r/origin.git" tag -d v1.4.1 >/dev/null 2>&1
    if _r_cut "$_r/r2b.log" --g0-only; then bad "R2b: G0 real seguiu com a tag base ausente no remoto"
    elif grep -q 'v1.4.1 ausente no REMOTO' "$_r/r2b.log"; then
      ok "R2b (controle vermelho): tag base ausente no REMOTO e recusa nomeada"
    else bad "R2b: recusa sem o motivo"; sed -n '1,8p' "$_r/r2b.log"; fi
    git -C "$_r/wt" push -q origin refs/tags/v1.4.1 2>/dev/null || bad "R2b: restaurar a tag base remota falhou"
    # R3 — argumentos: recusa nomeada ANTES do G0, rc 2 e nunca o banner.
    _r_arg() {  # $1 = rotulo, $2 = motivo esperado, $3.. = argumentos
      local _l="$1" _pat="$2" _rc=0; shift 2
      _r_cut "$_r/arg.log" "$@" || _rc=$?
      if [ "$_rc" -eq 2 ] && grep -qF -- "$_pat" "$_r/arg.log" && ! grep -q 'CORTADA' "$_r/arg.log"; then
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
    # R4 — arquivo NAO rastreado no plano, fora da evidencia.
    printf 'x\n' > "$_r/wt/$PLAN_DIR/stray-leftover.txt"
    if _r_cut "$_r/stray.log" --g0-only; then bad "R4: G0 aceitou untracked no plano fora da evidencia"
    elif grep -q "$PLAN_DIR/stray-leftover.txt" "$_r/stray.log"; then
      ok "R4 (controle vermelho): untracked no plano fora da evidencia e recusado no G0, pelo nome"
    else bad "R4: recusa sem nomear o arquivo"; sed -n '1,6p' "$_r/stray.log"; fi
    rm -f -- "$_r/wt/$PLAN_DIR/stray-leftover.txt"
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
         && grep -q '.ceo-rc1-archive' "$_r/r5d.log"; then
      ok "R5d (controle vermelho): passo 5 feito com HEAD != CANDIDATE.sha e recusado, com a rota de arquivar FORA do repositorio"
    else bad "R5d: recusa sem o motivo/rota"; sed -n '1,8p' "$_r/r5d.log"; fi
    # R5e/R5f — tentativa PARCIAL: arquivada DENTRO do plano e recusada; pela rota
    # documentada (FORA do repositorio, CANDIDATE.sha e .cut-state mantidos) o G0 fica
    # verde, o passo 6 e o primeiro pendente e o runner nao ve evidencia anterior.
    git -C "$_r/wt" rev-parse HEAD > "$_r/wt/$EV/CANDIDATE.sha"
    _r_state 5
    for _pf in CONDITIONS-rc1.reviewed.md PROVENANCE-rc1.md verdict-rc1-1.txt transcript-rc1-1.log paths-rc1-1.manifest.txt probe-rc1.txt; do
      printf 'TEST ONLY: tentativa parcial\n' > "$_r/wt/$EV/$_pf"
    done
    { printf '#!/bin/bash\nset -uo pipefail\n'
      printf 'die() { printf "FATAL: %%s\\n" "$*" >&2; exit 1; }\n'
      printf 'OUT="$1"\n'
      awk '/^assert_attempt_absent\(\) \{$/,/^\}$/' "$_r/wt/$EV/run-rc1-repass.sh"
      printf 'assert_attempt_absent && printf "R5F-ATTEMPT-ABSENT\\n"\n'; } > "$SCRATCH/r5f-aa.sh"
    if bash "$SCRATCH/r5f-aa.sh" "$_r/wt/$EV" > "$_r/r5f-aa0.log" 2>&1; then
      bad "R5f0: o assert_attempt_absent do runner nao viu a tentativa parcial plantada"
    elif grep -q 'evidencia de tentativa anterior presente' "$_r/r5f-aa0.log"; then
      ok "R5f0 (controle vermelho): o runner (verbatim) recusa rodar sobre a tentativa parcial plantada"
    else bad "R5f0: recusa sem o motivo"; sed -n '1,4p' "$_r/r5f-aa0.log"; fi
    _inrepo="$_r/wt/$PLAN_DIR/repass-rc1-20260924-NOGO-r1-capacidade"
    mkdir -p "$_inrepo" && cp -- "$_r/wt/$EV/PROVENANCE-rc1.md" "$_inrepo/"
    if _r_cut "$_r/r5e.log" --g0-only; then bad "R5e: tentativa arquivada DENTRO do plano passou no G0"
    elif grep -q "repass-rc1-20260924-NOGO-r1-capacidade/PROVENANCE-rc1.md" "$_r/r5e.log"; then
      ok "R5e (controle vermelho): tentativa arquivada DENTRO do plano e recusada no G0, pelo nome"
    else bad "R5e: recusa sem nomear o arquivo"; sed -n '1,8p' "$_r/r5e.log"; fi
    rm -f -- "$_inrepo/PROVENANCE-rc1.md"; rmdir -- "$_inrepo" 2>/dev/null
    _arch="$SCRATCH/rhome/.ceo-rc1-archive/repass-rc1-TEST-capacidade"
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
       && [ -f "$_arch/CONDITIONS-rc1.reviewed.md" ] && [ -f "$_arch/probe-rc1.txt" ]; then
      ok "R5f: rota documentada (FORA do repositorio; CANDIDATE.sha e .cut-state mantidos): G0 verde e o passo 6 e o primeiro pendente"
    else bad "R5f: a rota documentada nao deixou o G0 verde retomando do passo 6"; sed -n '1,14p' "$_r/r5f.log"; fi
    if bash "$SCRATCH/r5f-aa.sh" "$_r/wt/$EV" > "$_r/r5f-aa.log" 2>&1 && grep -q R5F-ATTEMPT-ABSENT "$_r/r5f-aa.log"; then
      ok "R5f: depois da rota, o assert_attempt_absent do runner (verbatim) nao acha tentativa anterior"
    else bad "R5f: o runner ainda veria tentativa anterior"; sed -n '1,4p' "$_r/r5f-aa.log"; fi
    rm -f -- "$_r/wt/$EV/CANDIDATE.sha"
    _r_state 0
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
    else bad "R5: commit local da fixture falhou"; fi
    # R6 — retomada depois do passo 16: a tag no remoto e o pre-release que o release.yml
    # cria. O G0 aceita; vermelhos: Release sem a flag, tag remota trocada, registro do 16,
    # tag local sem o 15, main que andou x main revertido.
    git -C "$_r/wt" rev-parse HEAD > "$_r/wt/$EV/CANDIDATE.sha"
    if git -C "$_r/wt" -c tag.gpgSign=false tag -a -m "TEST ONLY: rc fixture" v1.4.2-rc.1 \
       && git -C "$_r/wt" push -q origin refs/tags/v1.4.2-rc.1 2>/dev/null; then
      _r_state 16
      R_RC_RELEASE='{"isDraft": false, "isPrerelease": true}'
      if _r_cut "$_r/r6.log" --g0-only && grep -q 'retomada pos-tag: o pre-release do v1.4.2-rc.1 existe' "$_r/r6.log" \
         && grep -q 'OK: main; retomada pos-tag' "$_r/r6.log"; then
        ok "R6: G0 aceita, depois do passo 16, o pre-release que o release.yml cria"
      else bad "R6: G0 recusou a retomada pos-tag"; sed -n '1,12p' "$_r/r6.log"; fi
      R_RC_RELEASE='{"isDraft": false, "isPrerelease": false}'
      if _r_cut "$_r/r6b.log" --g0-only; then bad "R6b: Release sem a flag pre-release passou na retomada"
      elif grep -q "isPrerelease='False'" "$_r/r6b.log"; then ok "R6b (controle vermelho): Release sem a flag pre-release e recusado na retomada"
      else bad "R6b: recusa sem o motivo"; sed -n '1,6p' "$_r/r6b.log"; fi
      R_RC_RELEASE='{"isDraft": false, "isPrerelease": true}'
      if git -C "$_r/wt" push -q -f origin "v1.4.2-rc.1^{commit}:refs/tags/v1.4.2-rc.1" 2>/dev/null; then
        if _r_cut "$_r/r6c.log" --g0-only; then bad "R6c: tag remota trocada passou na retomada pos-tag"
        elif grep -q 'nao e o objeto assinado local' "$_r/r6c.log"; then ok "R6c (controle vermelho): tag remota que nao e o objeto local e recusada na retomada"
        else bad "R6c: recusa sem o motivo"; sed -n '1,6p' "$_r/r6c.log"; fi
        git -C "$_r/wt" push -q -f origin refs/tags/v1.4.2-rc.1 2>/dev/null || bad "R6c: restaurar a tag remota falhou"
      else bad "R6c: nao consegui trocar a tag remota"; fi
      _r_state 15
      rm -f -- "$_r/wt/$EV/.tag-push-epoch"
      if _r_cut "$_r/r6d.log" --g0-only && grep -q 'passo 16 registrado agora' "$_r/r6d.log" \
         && grep -qx 'STEP-16' "$_r/wt/$EV/.cut-state" \
         && [ "$(tr -d ' \n' < "$_r/wt/$EV/.tag-push-epoch")" = "$(git -C "$_r/wt" for-each-ref --format='%(taggerdate:unix)' refs/tags/v1.4.2-rc.1)" ] \
         && grep -q 'OK: main; retomada pos-tag' "$_r/r6d.log"; then
        ok "R6d: push da tag sem o marcador do 16 e reconhecido (remoto == objeto local): o 16 e registrado e o piso do passo 19 e a data da tag"
      else bad "R6d: o G0 nao reconheceu o push da tag sem marcador"; sed -n '1,12p' "$_r/r6d.log"; fi
      _r_state 15
      if git -C "$_r/wt" push -q -f origin "v1.4.2-rc.1^{commit}:refs/tags/v1.4.2-rc.1" 2>/dev/null; then
        if _r_cut "$_r/r6d2.log" --g0-only; then bad "R6d2: tag remota de OUTRO objeto, sem o passo 16, passou"
        elif grep -q 'ja existe no REMOTO' "$_r/r6d2.log" && ! grep -qx 'STEP-16' "$_r/wt/$EV/.cut-state"; then
          ok "R6d2 (controle vermelho): tag remota que nao e o objeto local NAO registra o 16 e e recusada"
        else bad "R6d2: recusa sem o motivo (ou o 16 foi registrado)"; sed -n '1,6p' "$_r/r6d2.log"; fi
        git -C "$_r/wt" push -q -f origin refs/tags/v1.4.2-rc.1 2>/dev/null || bad "R6d2: restaurar a tag remota falhou"
      else bad "R6d2: nao consegui trocar a tag remota"; fi
      _r_state 14
      if _r_cut "$_r/r6d3.log" --g0-only; then bad "R6d3: tag local sem o passo 15 passou"
      elif grep -q 'ja existe (local)' "$_r/r6d3.log" && grep -q 'git tag -d v1.4.2-rc.1' "$_r/r6d3.log"; then
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
        if git -C "$_r/wt" push -q -f origin "v1.4.2-rc.1^{commit}^:refs/heads/main" 2>/dev/null; then
          if _r_cut "$_r/r6e2.log" --g0-only; then bad "R6e2: main revertido para antes da tag passou na retomada"
          elif grep -q 'fora de uma retomada conhecida' "$_r/r6e2.log"; then
            ok "R6e2 (controle vermelho): main revertido para antes da tag e recusado na retomada pos-tag"
          else bad "R6e2: recusa sem o motivo"; sed -n '1,8p' "$_r/r6e2.log"; fi
        else bad "R6e2: nao consegui reverter o main da fixture"; fi
        git -C "$_r/wt" push -q -f origin HEAD:refs/heads/main 2>/dev/null || bad "R6e: restaurar o main da fixture falhou"
      else bad "R6e: push alheio na fixture falhou"; fi
      # R7 — o banner de CORTADA so com o passo 20 concluido.
      _r_state 19
      if _r_cut "$_r/r7.log" --until 19 && grep -q 'PARADO depois do passo 19' "$_r/r7.log" \
         && grep -q 'pendentes: 20' "$_r/r7.log" && ! grep -q 'CORTADA' "$_r/r7.log"; then
        ok "R7: --until 19 para, lista o 20 pendente e NAO imprime o banner de CORTADA"
      else bad "R7: --until nao parou como devia"; sed -n '1,12p' "$_r/r7.log"; fi
      _r_state 20
      if _r_cut "$_r/r7b.log" && grep -q 'v1.4.2-rc.1 CORTADA' "$_r/r7b.log"; then
        ok "R7b: com o passo 20 concluido, o banner sai"
      else bad "R7b: banner ausente com os 20 passos concluidos"; sed -n '1,12p' "$_r/r7b.log"; fi
      R_RC_RELEASE=""
      git -C "$_r/wt" tag -d v1.4.2-rc.1 >/dev/null 2>&1 || bad "R: limpeza da tag local falhou"
      git -C "$_r/wt" push -q origin :refs/tags/v1.4.2-rc.1 2>/dev/null || bad "R: limpeza da tag remota falhou"
    else bad "R6: tag/push da fixture falhou"; fi
    rm -f -- "$_r/wt/$EV/CANDIDATE.sha" "$_r/wt/$EV/.tag-push-epoch"
    _r_state 0

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
      _t2_from="$(git -C "$_r/wt" rev-parse HEAD)"
      if _r_pty "$_r/t2.log" --from 2 --until 2 \
         && grep -q 'AVISO: --from 2 PULA passo(s) NAO concluido(s): 1' "$_r/t2.log" \
         && grep -q 'Enter para confirmar que releu' "$_r/t2.log" \
         && grep -qE 'bump commitado|bump e no-op' "$_r/t2.log" \
         && grep -q 'PARADO depois do passo 2' "$_r/t2.log" \
         && grep -qx 'STEP-2' "$_r/wt/$EV/.cut-state" && ! grep -qx 'STEP-1' "$_r/wt/$EV/.cut-state" \
         && grep -qx "SHA-2P $_t2_from" "$_r/wt/$EV/.cut-state" \
         && grep -qx "SHA-2 $(git -C "$_r/wt" rev-parse HEAD)" "$_r/wt/$EV/.cut-state"; then
        ok "T2: passo 2 REAL num pty: o pulo do 1 e nomeado, o Enter e lido do terminal, o bump REAL ($(grep -oE 'bump commitado|bump e no-op' "$_r/t2.log" | head -1)) grava SHA-2P/SHA-2 e o --until para"
      else bad "T2: passo 2 real no pty falhou"; tr -d '\r' < "$_r/t2.log" | sed -n '1,40p'; fi
      # T2b/T2c/T2d — a retomada entre os passos 2 e 3: o commit do bump REAL do T2 esta em
      # main LOCAL e o push do 3 nao rodou. Com o passo 1 registrado (a manha real), o re-run
      # SEM --from passa no G0 e o passo 3 pusha; o mesmo estado com outro assunto no commit,
      # ou com o SHA-2P que nao e o pai, e recusado.
      _t2_head="$(git -C "$_r/wt" rev-parse HEAD)"
      if [ "$_t2_head" != "$_t2_from" ]; then
        printf 'STEP-1\nSHA-1 %s\n' "$_t2_from" >> "$_r/wt/$EV/.cut-state"
        cp -p "$_r/wt/$EV/.cut-state" "$_r/t2.state"
        if git -C "$_r/wt" -c commit.gpgsign=false commit -q --amend -m "TEST ONLY: outro assunto" 2>/dev/null; then
          sed "s/^SHA-2 .*/SHA-2 $(git -C "$_r/wt" rev-parse HEAD)/" "$_r/t2.state" > "$_r/wt/$EV/.cut-state"
          if _r_cut "$_r/t2c.log" --g0-only; then bad "T2c: commit a frente com outro assunto passou no G0"
          elif grep -q 'fora de uma retomada conhecida' "$_r/t2c.log" && grep -q 'NAO pushe as cegas' "$_r/t2c.log"; then
            ok "T2c (controle vermelho): o commit a frente com outro assunto (o SHA-2 apontando-o, o mesmo pai) e recusado"
          else bad "T2c: recusa sem o motivo"; sed -n '1,8p' "$_r/t2c.log"; fi
        else bad "T2c: o amend da fixture falhou"; fi
        git -C "$_r/wt" reset -q --hard "$_t2_head" || bad "T2c: voltar ao commit do bump falhou"
        sed "s/^SHA-2P .*/SHA-2P $(git -C "$_r/wt" rev-parse "$_t2_from^")/" "$_r/t2.state" > "$_r/wt/$EV/.cut-state"
        if _r_cut "$_r/t2d.log" --g0-only; then bad "T2d: SHA-2P que nao e o pai do bump passou no G0"
        elif grep -q 'fora de uma retomada conhecida' "$_r/t2d.log"; then
          ok "T2d (controle vermelho): o .cut-state cujo SHA-2P nao e o pai do commit do bump e recusado"
        else bad "T2d: recusa sem o motivo"; sed -n '1,8p' "$_r/t2d.log"; fi
        cp -p "$_r/t2.state" "$_r/wt/$EV/.cut-state"
        if _r_cut "$_r/t2b.log" --until 3 && grep -q 'retomada entre os passos 2 e 3' "$_r/t2b.log" \
           && grep -q 'PARADO depois do passo 3' "$_r/t2b.log" && grep -qx 'STEP-3' "$_r/wt/$EV/.cut-state" \
           && [ "$(git -C "$_r/origin.git" rev-parse refs/heads/main)" = "$_t2_head" ]; then
          ok "T2b: retomada entre os passos 2 e 3 (bump em main local, nao pushado): o re-run passa no G0 e o passo 3 pusha o commit do bump"
        else bad "T2b: a retomada entre os passos 2 e 3 falhou"; sed -n '1,30p' "$_r/t2b.log"; fi
        git -C "$_r/wt" push -q -f origin "$_t2_from:refs/heads/main" 2>/dev/null || bad "T2b: restaurar o main da fixture falhou"
      else bad "T2b: o bump do T2 foi no-op — a retomada entre os passos 2 e 3 nao foi exercitada"; fi
      if [ -f "$SCRATCH/w.sh" ]; then
        if ( _pty "$SCRATCH/t3.log" env W_LOAD="9.50 4" bash "$SCRATCH/w.sh" ) \
           && grep -q 'AVISO: a maquina esta CARREGADA' "$SCRATCH/t3.log"; then
          ok "T3: aviso de carga alta num pty: avisa e le o Enter do terminal"
        else bad "T3: aviso de carga no pty falhou"; tr -d '\r' < "$SCRATCH/t3.log" | sed -n '1,10p'; fi
      else bad "T3: $SCRATCH/w.sh ausente (a secao W nao rodou)"; fi
      git -C "$_r/wt" reset -q --hard origin/main 2>/dev/null || bad "T: reset do clone depois do bump falhou"
      _r_state 0
    fi

    # R8 — a sonda das condicoes no G0 recusa uma condicao FALSA pelo nome (um template
    # com ultracode: condicao 5). Sem o REPORT-ONLY, mesmo com a sonda vermelha por outra
    # razao: o que se confere e a linha da condicao 5.
    if python3 - "$_r/wt/templates/settings/settings.base.json" <<'PYR8' \
       && git -C "$_r/wt" commit -q -am "TEST ONLY: ultracode no template" \
       && git -C "$_r/wt" push -q origin HEAD:refs/heads/main 2>/dev/null
import json, sys
p = sys.argv[1]
d = json.load(open(p, encoding="utf-8"))
d["ultracode"] = True
open(p, "w", encoding="utf-8").write(json.dumps(d, indent=2) + "\n")
PYR8
    then
      if ( cd "$_r/wt" && env PATH="$_r/bin:$PATH" GNUPGHOME="$GH" HOME="$SCRATCH/rhome" \
             TMPDIR="$_r/tmp" RC1_SELFTEST=1 RC1_SELFTEST_SCRATCH="$SCRATCH" RC1_SELFTEST_SIGNER_FPR="$FPR" \
             bash "$PLAN_DIR/OWNER-RC1-CUT.sh" --g0-only ) < /dev/null > "$_r/r8.log" 2>&1; then
        bad "R8: G0 real aceitou um template com ultracode"
      elif grep -q 'FAIL C5-pin: templates/settings/settings.base.json carrega ultracode' "$_r/r8.log" \
           && grep -q 'a sonda das condicoes achou afirmacao FALSA' "$_r/r8.log"; then
        ok "R8 (controle vermelho): G0 real recusa uma condicao FALSA (condicao 5), nomeando a afirmacao"
      else bad "R8: G0 real recusou sem nomear a condicao"; grep -E 'FAIL|sonda' "$_r/r8.log" | sed -n '1,8p'; fi
    else bad "R8: commit/push da mutacao no clone falhou"; fi
    # R9 — a relmeta-142 nao landou (o driver ainda mira 1.4.1): recusa nomeando o pack.
    if python3 - "$_r/wt/.claude/scripts/local/release.sh" <<'PYR9' \
       && git -C "$_r/wt" commit -q -am "TEST ONLY: driver na 1.4.1" \
       && git -C "$_r/wt" push -q origin HEAD:refs/heads/main 2>/dev/null
import re, sys
p = sys.argv[1]
t = open(p, encoding="utf-8").read()
open(p, "w", encoding="utf-8").write(re.sub(r'(?m)^TARGET_BASE="[^"]*"$', 'TARGET_BASE="1.4.1"', t, count=1))
PYR9
    then
      if _r_cut "$_r/r9.log" --g0-only; then bad "R9: G0 real aceitou o driver fora da 1.4.2"
      elif grep -q "TARGET_BASE do release.sh e '1.4.1', esperado 1.4.2" "$_r/r9.log" \
           && grep -q 'PLAN-193/relmeta/' "$_r/r9.log"; then
        ok "R9 (controle vermelho): G0 real recusa o driver fora da 1.4.2, nomeando o pack da relmeta-142"
      else bad "R9: recusa sem nomear o pack"; sed -n '1,6p' "$_r/r9.log"; fi
    else bad "R9: commit/push da mutacao no clone falhou"; fi
  else bad "R: clone bare/remoto local falhou"; fi
else printf '  (R e T pulados: sem clone, sem chave ou sem base)\n'; fi

# ===========================================================================
say "D. controles VERMELHOS — cada gate tem de RECUSAR o defeito plantado"

# D1 (CM-03) — dois vereditos no mesmo arquivo e ambiguidade, nao aprovacao.
if [ -n "$CLONE" ] && [ -f "$CLONE/$EV/verdict-rc1-1.txt" ]; then
  _d1="$SCRATCH/d1"; mkdir -p "$_d1"; cp "$CLONE/$EV/verdict-rc1-1.txt" "$_d1/v.txt"
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
