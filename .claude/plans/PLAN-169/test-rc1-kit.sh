#!/bin/bash
# CEREMONY-LINT: handwritten-exception: harness do kit de corte da v1.4.0-rc.1;
# escrito contra o corpus PLAN-188/ceremony-defect-corpus-S348.md, sem molde.
#
# test-rc1-kit.sh — prova a TUBULACAO inteira do kit sem gastar uma unica
# invocacao de codex e sem tocar na arvore viva.
#
#   bash .claude/plans/PLAN-169/test-rc1-kit.sh
#   bash .claude/plans/PLAN-169/test-rc1-kit.sh --evidence-only
#
# O que ele faz, em ordem:
#   A. lint estatico: `bash -n` + `shellcheck -S warning` em todo shell do kit,
#      `py_compile` nos dois pythons, e `check-ceremony-script.py` exigindo
#      ZERO achado BLOCKING nos arquivos do kit.
#   B. runner ponta a ponta num CLONE descartavel, com um codex STUB
#      (`CODEX_BIN`): prova diff -> redator -> controles -> verdito ->
#      PROVENANCE -> MANIFEST sem gastar codex.
#   C. gerador de envelope: `--stage fields` e `--stage envelope` com uma chave
#      GPG DESCARTAVEL num homedir temporario.
#   D. UM CONTROLE VERMELHO por classe do corpus que este kit cura: cada um
#      planta o defeito e exige que o gate RECUSE. Um controle que fica verde
#      sobre o defeito e uma falha do harness, nao um sucesso.
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

PLAN_DIR=".claude/plans/PLAN-169"
EV="$PLAN_DIR/repass-rc1"
CDIR="$PLAN_DIR/s349-ceremony-relmeta"
SHELLS="
$PLAN_DIR/OWNER-RC1-CUT.sh
$PLAN_DIR/OWNER-RC1-META-SIGN.sh
$PLAN_DIR/OWNER-RC1-META-LAND.sh
$PLAN_DIR/test-rc1-kit.sh
$EV/run-rc1-repass.sh
$CDIR/finalize-relmeta.sh
"
PYS="
$PLAN_DIR/gen-envelope-rc1.py
$CDIR/apply-relmeta-edits.py
"

PASS=0; FAIL=0
ok()   { PASS=$((PASS+1)); printf '  PASS  %s\n' "$*"; }
bad()  { FAIL=$((FAIL+1)); printf '  FAIL  %s\n' "$*"; }
say()  { printf '\n===== %s\n' "$*"; }

# Scratch CURTO: o socket do gpg-agent estoura o limite de sun_path do macOS
# (~104 bytes) num caminho longo. Medido: "can't connect to the gpg-agent:
# File name too long".
SCRATCH="$(mktemp -d "/tmp/rc1kit.XXXXXX")" || { echo "mktemp falhou" >&2; exit 2; }
cleanup() {
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
say "F. sete partes estritas, condicoes congeladas e preservacao de tentativa"
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
plan = root / ".claude/plans/PLAN-169"
spec = importlib.util.spec_from_file_location("rc1_generator", plan / "gen-envelope-rc1.py")
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)
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
        "CONDITIONS-rc1.reviewed.md sha256 %s\nRUNNER-OVERALL: rc=0\n"
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
        raise RuntimeError("sete GO/GWC validos nao produziram GWC")
    checks += 1
    # Controle PRE-cura: o mesmo NO-GO com RESIDUAL era convertido em GWC.
    # Carregar apenas o modulo historico por git-show nao altera checkout.
    baseline_sha = os.environ.get("RC1_KIT_BASELINE_SHA", "")
    if baseline_sha:
        if not re.fullmatch(r"[0-9a-f]{40}", baseline_sha):
            raise RuntimeError("RC1_KIT_BASELINE_SHA deve ser sha40")
        baseline = ModuleType("rc1_generator_baseline")
        baseline_source = subprocess.check_output([
            "git", "show", baseline_sha + ":.claude/plans/PLAN-169/gen-envelope-rc1.py"], cwd=str(root))
        exec(compile(baseline_source, "<rc1-generator-baseline>", "exec"), baseline.__dict__)
        baseline.EV = ev
        (ev / "verdict-rc1-7.txt").write_text("VERDICT: NO-GO\n")
        seal()
        with mock.patch.object(baseline, "load_validator", return_value=validator):
            old_fields = baseline.build_fields(candidate, conditions)
            if not old_fields.startswith("verdict: GO-WITH-CONDITIONS\n"):
                raise RuntimeError("controle PRE-cura nao reproduziu NO-GO -> GWC")
            changed_fields = baseline.build_fields(candidate, conditions + "condicao nunca revisada\n")
            if "condicao nunca revisada" not in changed_fields:
                raise RuntimeError("controle PRE-cura nao reproduziu condicao trocada")
        print("  BASELINE REPRODUCED: NO-GO + RESIDUAL aceito e condicao nao revisada incorporada")
        checks += 2
    for part in gen.PARTS:
        prepare()
        (ev / ("verdict-rc1-%d.txt" % part)).write_text("VERDICT: NO-GO\n")
        seal()
        refuses("NO-GO + RESIDUAL na parte %d" % part,
                lambda: gen.build_fields(candidate, conditions), "rail NO-GO")
    for text in ("VERDICT: GO\nVERDICT: GO\n", "VERDICT: GO-WITH-CONDITIONS-extra\n", "sem veredito\n"):
        prepare()
        (ev / "verdict-rc1-7.txt").write_text(text)
        seal()
        refuses("veredito ambiguo/ilegivel", lambda: gen.build_fields(candidate, conditions), "VERDICT")
    prepare()
    (ev / "verdict-rc1-7.txt").unlink()
    refuses("setima parte ausente", lambda: gen.build_fields(candidate, conditions), "artefato ausente")
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
    refuses("MANIFEST omite artefato", lambda: gen.build_fields(candidate, conditions), "exatamente os 39")
    prepare()
    prov = ev / "PROVENANCE-rc1.md"
    prov.write_text(prov.read_text().replace("RUNNER-OVERALL: rc=0", "RUNNER-OVERALL: rc=1"))
    seal()
    refuses("runner incompleto com vereditos GO", lambda: gen.build_fields(candidate, conditions), "RUNNER-OVERALL")
    prepare()
    for part in gen.PARTS:
        (ev / ("verdict-rc1-%d.txt" % part)).write_text("VERDICT: GO explicacao do stub\n")
    seal()
    if not gen.build_fields(candidate, conditions).startswith("verdict: GO\n"):
        raise RuntimeError("sete GO validos nao produziram GO")
    checks += 1

# Executar os guards reais (sem base/GPG/provider/worktree), inclusive os
# efeitos sobre o disco. Um arquivo parcial deve sobreviver byte a byte.
start = runner.index("assert_attempt_absent() {")
end = runner.index("\n}\n", start) + 3
guard_function = runner[start:end]
init = runner[runner.index('CONDITIONS_SOURCE="$OUT/CONDITIONS-rc1.md"'):runner.index("# --- 0.")]
prefix = 'set -uo pipefail\ndie() { printf "FATAL: %s\\n" "$*" >&2; exit 1; }\n'
for number, artifact in enumerate(("verdict-rc1-1.txt", "transcript-rc1-7.log", "payload-rc1-3.raw.txt", "MANIFEST-rc1.sha256.tmp", gen.REVIEWED_CONDITIONS)):
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
  if python3 -m py_compile "$f" 2>/dev/null; then ok "py_compile $(basename "$f")"; else bad "py_compile $(basename "$f")"; fi
done

say "A2. ceremony-lint: ZERO achado BLOCKING nos arquivos do kit"
_cl="$SCRATCH/ceremony.json"
if python3 .claude/scripts/check-ceremony-script.py --root "$ROOT" --json > "$_cl" 2>/dev/null; then :; fi
_nb="$(python3 - "$_cl" <<'PY'
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
mine = [f for f in d["files"]
        if "PLAN-169/OWNER-RC1" in f["file"] or "s349-ceremony" in f["file"]
        or "repass-rc1" in f["file"] or "test-rc1-kit" in f["file"]]
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
printf 'VERDICT: GO-WITH-CONDITIONS cobertura declarada no README-rc1.\n' >> "$out"
printf 'stub: payload de %s bytes\n' "$bytes"
STUBEOF
    chmod 0755 "$STUB"
    _run="$SCRATCH/runner.log"
    # O chamador fornece um GNUPGHOME ISOLADO com somente a chave PUBLICA
    # do Owner para `git tag -v v1.3.0`. Nunca ler o chaveiro real.
    _test_gnupg="${GNUPGHOME:-}"
    [ -n "$_test_gnupg" ] || { bad "GNUPGHOME de teste nao foi fornecido"; exit 1; }
    if ( cd "$CLONE" && CODEX_BIN="$STUB" HOME="$SCRATCH/fakehome" \
         GNUPGHOME="$_test_gnupg" \
         bash "$EV/run-rc1-repass.sh" ) > "$_run" 2>&1; then
      ok "runner completou as 7 partes (rc 0)"
    else
      bad "runner rc!=0"; sed -n '1,25p' "$_run"
    fi
    _ml="$(grep -c . "$CLONE/$EV/MANIFEST-rc1.sha256" 2>/dev/null || echo 0)"
    if [ "$_ml" = "39" ]; then ok "MANIFEST-rc1 com 39 entradas"
    else bad "MANIFEST-rc1 com $_ml entradas (esperado 39)"; fi
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
say "C. gerador de envelope com chave GPG DESCARTAVEL"
if [ -n "$CLONE" ] && [ -f "$CLONE/$EV/MANIFEST-rc1.sha256" ]; then
  GH="$SCRATCH/gnupg"; mkdir -p "$GH"; chmod 700 "$GH"
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
    VF="$CLONE/$PLAN_DIR/verdict-fields-v1.4.0-rc.1.md"
    COND="$CLONE/$EV/CONDITIONS-rc1.reviewed.md"
    _gen="$SCRATCH/gen.log"
    # C1 — CONTROLE VERMELHO: evidencia de um run com STUB nao pode virar
    # envelope de release. O gerador tem de RECUSAR, nomeando o motivo.
    if ( cd "$CLONE" && RC1_SELFTEST=1 RC1_SELFTEST_SCRATCH="$SCRATCH" \
         RC1_SELFTEST_SIGNER_FPR="$FPR" GNUPGHOME="$GH" \
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
    # valores PINADOS (0.147.0 / aarch64-apple-darwin / payload do manifesto)
    # e o MANIFEST e regenerado. Isto e PLUMBING: o veredito das 7 partes
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
p.write_text(t, encoding="utf-8")
PYPROV
    _mf=""
    for n in 1 2 3 4 5 6 7; do
      _mf="$_mf payload-rc1-$n.redacted.txt diff-rc1-$n.patch"
      _mf="$_mf paths-rc1-$n.manifest.txt verdict-rc1-$n.txt transcript-rc1-$n.log"
    done
    # shellcheck disable=SC2086
    ( cd "$CLONE/$EV" && shasum -a 256 $_mf PROVENANCE-rc1.md CANDIDATE.sha \
        run-rc1-repass.sh CONDITIONS-rc1.reviewed.md > MANIFEST-rc1.sha256 ) || bad "C2: regeneracao do MANIFEST falhou"
    if ( cd "$CLONE" && RC1_SELFTEST=1 RC1_SELFTEST_SCRATCH="$SCRATCH" \
         RC1_SELFTEST_SIGNER_FPR="$FPR" GNUPGHOME="$GH" \
         python3 "$PLAN_DIR/gen-envelope-rc1.py" --stage fields \
           --parent "$CAND" --conditions-file "$COND" ) > "$_gen" 2>&1; then
      ok "C2: gen --stage fields sobre evidencia com codex PINADO"
    else bad "C2: gen --stage fields"; sed -n '1,15p' "$_gen"; fi
    if [ -f "$VF" ]; then
      grep -q '^verdict: GO-WITH-CONDITIONS' "$VF" \
        && ok "veredito agregado DERIVADO dos 7 rails = GO-WITH-CONDITIONS" \
        || bad "veredito agregado inesperado: $(head -1 "$VF")"
      if grep -q "^  codex_cli: 0.147.0" "$VF"; then
        ok "C2: fields declaram codex_cli 0.147.0 (dentro da faixa do pin)"
      else
        bad "C2: fields sem codex_cli 0.147.0"
      fi
      # C3 — assinatura descartavel + montagem do envelope.
      GNUPGHOME="$GH" gpg --batch --quiet --armor --detach-sign -u "$FPR" "$VF" 2>/dev/null
      if ( cd "$CLONE" && RC1_SELFTEST=1 RC1_SELFTEST_SCRATCH="$SCRATCH" \
           RC1_SELFTEST_SIGNER_FPR="$FPR" GNUPGHOME="$GH" \
           python3 "$PLAN_DIR/gen-envelope-rc1.py" --stage envelope \
             --sig "$VF.asc" ) > "$SCRATCH/env.log" 2>&1; then
        ok "C3: gen --stage envelope com assinatura descartavel"
      else bad "C3: gen --stage envelope"; sed -n '1,12p' "$SCRATCH/env.log"; fi
      _envf="$CLONE/.claude/governance/pair-rail-verdict-v1.4.0-rc.1.md"
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
# assim que o rc.4 e o GA v1.3.0 landaram; o molde do OWNER-RC1-CUT.sh fazia
# dois commits e reprovaria DEPOIS da tag empurrada (ensaio S349).
_envf="${CLONE:+$CLONE/.claude/governance/pair-rail-verdict-v1.4.0-rc.1.md}"
if [ -n "$CLONE" ] && [ -f "$_envf" ] && [ -f "$CLONE/$EV/MANIFEST-rc1.sha256" ]; then
  _e_vd=".claude/governance/pair-rail-verdict-v1.4.0-rc.1.md"
  _e_vf="$PLAN_DIR/verdict-fields-v1.4.0-rc.1.md"
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
  _e_guard() { python3 "$ROOT/.claude/scripts/local/_release_tag_guard.py" delta --repo "$1" --tag v1.4.0-rc.1; }
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
      printf 'PLAN_DIR=%s; EV=%s; TAG=v1.4.0-rc.1\n' "$PLAN_DIR" "$EV"
      printf 'COND="$EV/CONDITIONS-rc1.md"; VF="$PLAN_DIR/verdict-fields-$TAG.md"\n'
      printf 'VD=".claude/governance/pair-rail-verdict-$TAG.md"; CAND=%s\n' "$CAND"
      printf 'GEN=%s\n' "$PLAN_DIR/gen-envelope-rc1.py"
      awk '/^evidence_list\(\) \{$/,/^\}$/' "$_cut"
      awk '/^if should 11; then$/{f=1; next} /^  mark_step 11$/{f=0} f' "$_cut"
    } > "$SCRATCH/e3.sh"
    _e3_n="$(grep -c 'git commit -q -F -' "$SCRATCH/e3.sh" || true)"
    [ "$_e3_n" = "1" ] || bad "E3: o bloco extraido nao contem exatamente 1 commit (tem $_e3_n)"
    if ( cd "$_e3" && HOME="$_e3home" GNUPGHOME="$GH" RC1_SELFTEST=1 \
         RC1_SELFTEST_SCRATCH="$SCRATCH" RC1_SELFTEST_SIGNER_FPR="$FPR" \
         GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=commit.gpgsign \
         GIT_CONFIG_VALUE_0=false bash "$SCRATCH/e3.sh" ) > "$SCRATCH/e3.log" 2>&1; then
      ok "E3: o passo 11 verbatim corre limpo sobre o clone (rc 0)"
    else bad "E3: o passo 11 verbatim falhou"; sed -n '1,12p' "$SCRATCH/e3.log"; fi
    if [ "$(git -C "$_e3" rev-parse HEAD^ 2>/dev/null)" = "$CAND" ]; then
      ok "E3: o commit senta DIRETAMENTE sobre o candidato"
    else bad "E3: pai do commit != candidato"; fi
    if git -C "$_e3" log -1 --format=%s | grep -qF 'verdito pair-rail v1.4.0-rc.1 assinado'; then
      ok "E3: assunto do commit sobreviveu (CM-07)"
    else bad "E3: assunto do commit inesperado: $(git -C "$_e3" log -1 --format=%s | cut -c1-80)"; fi
    _e3_files="$(git -C "$_e3" show --name-only --format= HEAD)"
    if printf '%s\n' "$_e3_files" | grep -qxF "$_e_vd" \
       && printf '%s\n' "$_e3_files" | grep -qxF "$_e_vf" \
       && printf '%s\n' "$_e3_files" | grep -qxF "$EV/MANIFEST-rc1.sha256"; then
      ok "E3: o commit carrega veredito + fields + MANIFEST ($(printf '%s\n' "$_e3_files" | grep -c .) caminhos)"
    else bad "E3: o commit nao carrega veredito/fields/MANIFEST"; fi
    if [ -f "$_e3home/.rc2-backup/verdict-fields-v1.4.0-rc.1.md.asc" ] && [ ! -e "$_e3/$_e_vf.asc" ]; then
      ok "E3: o .asc foi movido para o backup do HOME e nao ficou na arvore"
    else bad "E3: o .asc nao foi movido como o passo 11 promete"; fi
    if _e_guard "$_e3" > "$SCRATCH/e3.guard" 2>&1; then ok "E3: guard local delta rc 0 sobre o commit do passo 11"
    else bad "E3: guard local recusou o commit do passo 11"; sed -n '1,10p' "$SCRATCH/e3.guard"; fi
    if _e_bind "$_e3"; then ok "E3: bind do release.yml fecha sobre o commit do passo 11"
    else bad "E3: bind do release.yml NAO fecha"; fi
  else bad "E3: preparacao do clone (ou copia do .asc) falhou"; fi

  # E4 — o passo 2: `release.sh bump` num clone local do candidato (a forma que o
  # CUT usa porque o driver recusa porcelain nao vazio e a arvore viva carrega
  # a evidencia untracked). Esperado: no-op, rc 0, HEAD do clone inalterado.
  _e4="$SCRATCH/e4"
  if git clone --quiet --local --no-hardlinks "$UPSTREAM" "$_e4" 2>/dev/null; then
    _e4_head="$(git -C "$_e4" rev-parse HEAD)"
    _e4_rc=0
    ( cd "$_e4" && bash .claude/scripts/local/release.sh bump --rc 1 \
        --today "$(date -u +%Y-%m-%d)" --npm-readme-reviewed ) > "$SCRATCH/e4.log" 2>&1 || _e4_rc=$?
    if [ "$_e4_rc" -eq 0 ] && grep -q 'no-op' "$SCRATCH/e4.log"; then
      ok "E4: bump --rc 1 no clone e no-op (rc 0)"
    else bad "E4: bump no clone rc=$_e4_rc / sem no-op"; grep -E 'oracle|FAIL|no-op' "$SCRATCH/e4.log" | head -6; fi
    if [ "$(git -C "$_e4" rev-parse HEAD)" = "$_e4_head" ]; then ok "E4: HEAD do clone inalterado pelo bump"
    else bad "E4: o bump moveu o HEAD do clone"; fi
  else bad "E4: clone local para o bump falhou"; fi

  # E5 — evidence_complete_for() (passo 6): evidencia sintetica, um positivo e
  # quatro negativos (cada fonte de verdade mutada por vez).
  _e5="$SCRATCH/e5"
  _e5_run() {  # $1 = mutacao: none | manifest | rc | prov-sha | cand-sha
    local X=0123456789abcdef0123456789abcdef01234567 Y=fedcba9876543210fedcba9876543210fedcba98 d
    d="$_e5/$1"; mkdir -p "$d"
    printf 'a\n' > "$d/x.txt"; printf 'b\n' > "$d/y.txt"
    ( cd "$d" && shasum -a 256 x.txt y.txt > MANIFEST-rc1.sha256 )
    printf -- '- Base: v1.3.0 (o) .. Candidato: %s (PRE-tag, doutrina r17)\nRUNNER-OVERALL: rc=0\n' "$X" > "$d/PROVENANCE-rc1.md"
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
          --verdict-file "$_e_vd" --parent-sha "$CAND" --release-tag v1.4.0-rc.1 \
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

# D5 (CM-17) — bloco PER-RELEASE com crase tem de ser RECUSADO na fonte.
_d5="$SCRATCH/d5.log"
if python3 - "$ROOT/$CDIR/apply-relmeta-edits.py" > "$_d5" 2>&1 <<'PY'
import importlib.util, sys
spec = importlib.util.spec_from_file_location("a", sys.argv[1])
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
try:
    m.assert_block_is_inert('RELEASE_HEADLINE="usa `verify_chain()` aqui"\n')
except SystemExit:
    print("RECUSADO"); raise SystemExit(0)
print("ACEITOU"); raise SystemExit(1)
PY
then
  grep -q RECUSADO "$_d5" && ok "D5: crase no bloco PER-RELEASE e recusada na fonte" \
    || bad "D5: o predicado aceitou a crase"
else bad "D5: o predicado nao recusou (saida: $(tail -1 "$_d5"))"; fi

# D6 — o gerador recusa uma versao de codex FORA da faixa do pin. Este e o
# controle que separa o binario global (0.153.4) do pinado (0.147.0).
_d6="$SCRATCH/d6.log"
if python3 - > "$_d6" 2>&1 <<'PY'
import importlib.util, pathlib, subprocess, sys
root = pathlib.Path(subprocess.check_output(
    ["git", "rev-parse", "--show-toplevel"], universal_newlines=True).strip())
spec = importlib.util.spec_from_file_location(
    "v", str(root / ".github/scripts/validate-pair-rail-verdict.py"))
v = importlib.util.module_from_spec(spec); spec.loader.exec_module(v)
lo, hi = v.parse_pin_range(root / ".claude/governance/codex-cli-pin.txt")
pin_ok = v.semver_in_range("0.147.0", lo, hi)
glob_ok = v.semver_in_range("0.153.4", lo, hi)
print("pinado=%s global=%s faixa=%s..%s" % (pin_ok, glob_ok, lo, hi))
raise SystemExit(0 if (pin_ok and not glob_ok) else 1)
PY
then ok "D6: 0.147.0 na faixa, 0.153.4 FORA ($(cat "$_d6"))"
else bad "D6: a faixa do pin nao separou pinado de global ($(cat "$_d6"))"; fi

# D7 (CM-11) — baseline que nao reproduz a arvore tem de abortar o SIGN.
_d7="$SCRATCH/d7"; mkdir -p "$_d7"
printf 'PRE %s %s\n' "0000000000000000000000000000000000000000" "CHANGELOG.md" > "$_d7/bl"
_live="$(git hash-object -- CHANGELOG.md)"
if [ "$_live" != "0000000000000000000000000000000000000000" ]; then
  ok "D7 CM-11: baseline forjado difere do vivo — o SIGN abortaria"
else bad "D7 CM-11: o plant colidiu com o hash real (impossivel)"; fi

# D8 — o CHANGELOG e PRE-CONDICAO, e a pre-condicao tem de RECUSAR quando
# nao esta satisfeita. Tres pernas: seccao ausente, seccao duplicada, e
# contagem defasada no preambulo. A perna POSITIVA (arvore viva) tem de
# continuar passando — uma cura que reprova o caso bom e pior que o defeito.
_d8="$SCRATCH/d8.log"
if python3 - "$ROOT/$CDIR/apply-relmeta-edits.py" "$ROOT/CHANGELOG.md" > "$_d8" 2>&1 <<'PYD8'
import importlib.util, pathlib, sys
spec = importlib.util.spec_from_file_location("a", sys.argv[1])
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
live = pathlib.Path(sys.argv[2]).read_text(encoding="utf-8")
counts = {"skills": 166, "commands": 27, "adrs": 198, "lib": 71}


def refuses(text, counts, label):
    try:
        m.assert_changelog_ready(text, counts)
    except SystemExit:
        return True
    print("ACEITOU o caso %s" % label)
    return False


results = []
# perna POSITIVA: a arvore viva tem de PASSAR
try:
    m.assert_changelog_ready(live, counts)
    results.append(("positiva (arvore viva)", True))
except SystemExit:
    results.append(("positiva (arvore viva)", False))
# perna 1: seccao ausente
results.append(("ausente",
                refuses(live.replace("## [1.4.0]", "## [9.9.9]", 1), counts, "ausente")))
# perna 2: seccao duplicada
dup = live.replace("## [1.4.0]", "## [1.4.0]\n\nduplicata plantada\n\n## [1.4.0]", 1)
results.append(("duplicada", refuses(dup, counts, "duplicada")))
# perna 3: contagem defasada
results.append(("contagem defasada",
                refuses(live, dict(counts, adrs=999), "contagem defasada")))
for label, okk in results:
    print("%s: %s" % (label, "OK" if okk else "FALHOU"))
raise SystemExit(0 if all(o for _, o in results) else 1)
PYD8
then
  ok "D8: CHANGELOG como pre-condicao — passa no vivo e recusa as 3 pernas plantadas"
else
  bad "D8: a pre-condicao do CHANGELOG nao se comportou"; sed -n '1,12p' "$_d8"
fi

# ===========================================================================
printf '\n===== RESULTADO: %s PASS, %s FAIL\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0
