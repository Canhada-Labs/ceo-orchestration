#!/bin/bash
# CEREMONY-LINT: handwritten-exception: harness do kit de corte da v1.4.0-rc.1;
# escrito contra o corpus PLAN-188/ceremony-defect-corpus-S348.md, sem molde.
#
# test-rc1-kit.sh — prova a TUBULACAO inteira do kit sem gastar uma unica
# invocacao de codex e sem tocar na arvore viva.
#
#   bash .claude/plans/PLAN-169/test-rc1-kit.sh
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
  [ -n "${CLONE:-}" ] && [ -d "$CLONE" ] && chmod -R u+w "$CLONE" 2>/dev/null
  rm -rf -- "$SCRATCH" 2>/dev/null
}
trap cleanup EXIT

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
CLONE="$SCRATCH/clone"
if git clone --quiet --local --shared "$ROOT" "$CLONE" 2>/dev/null; then
  ok "clone local criado"
else
  bad "git clone --local --shared falhou — pulando B e C"
  CLONE=""
fi

if [ -n "$CLONE" ]; then
  # O `origin` do clone e o repo VIVO; `origin/main` e o main vivo. O runner
  # exige CANDIDATE.sha == origin/main, entao e esse o candidato do teste.
  CAND="$(git -C "$CLONE" ls-remote origin refs/heads/main | awk '{print $1}')"
  if [ -z "$CAND" ]; then
    bad "ls-remote de main no clone falhou"
  else
    git -C "$CLONE" checkout --quiet --detach "$CAND" 2>/dev/null \
      || bad "checkout do candidato no clone falhou"
    mkdir -p "$CLONE/$EV" "$CLONE/$CDIR"
    for f in $SHELLS $PYS "$EV/README-rc1.md"; do
      [ -f "$f" ] && cp "$f" "$CLONE/$f"
    done
    for n in 1 2 3 4 5 6; do
      cp "$EV/paths-rc1-$n.manifest.txt" "$CLONE/$EV/" 2>/dev/null \
        || bad "manifesto da parte $n ausente"
    done
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
    # HOME desviado so para a quarentena dos payloads RAW. O GNUPGHOME
    # segue o REAL: `git tag -v v1.3.0` precisa do chaveiro do Owner, e
    # sem ele o runner recusaria por assinatura — um vermelho falso.
    _real_gnupg="${GNUPGHOME:-$HOME/.gnupg}"
    if ( cd "$CLONE" && CODEX_BIN="$STUB" HOME="$SCRATCH/fakehome" \
         GNUPGHOME="$_real_gnupg" \
         bash "$EV/run-rc1-repass.sh" ) > "$_run" 2>&1; then
      ok "runner completou as 6 partes (rc 0)"
    else
      bad "runner rc!=0"; sed -n '1,25p' "$_run"
    fi
    _ml="$(grep -c . "$CLONE/$EV/MANIFEST-rc1.sha256" 2>/dev/null || echo 0)"
    if [ "$_ml" = "33" ]; then ok "MANIFEST-rc1 com 33 entradas"
    else bad "MANIFEST-rc1 com $_ml entradas (esperado 33)"; fi
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
  if GNUPGHOME="$GH" gpg --batch --quiet --gen-key "$GH/params" >/dev/null 2>&1; then
    FPR="$(GNUPGHOME="$GH" gpg --batch --with-colons --list-secret-keys 2>/dev/null \
      | awk -F: '$1=="fpr"{print $10; exit}')"
    [ -n "$FPR" ] && ok "chave descartavel criada ($(printf '%s' "$FPR" | cut -c1-12))" \
      || bad "chave descartavel sem fingerprint"
  else
    FPR=""; bad "gpg --gen-key falhou no homedir temporario"
  fi
  if [ -n "${FPR:-}" ]; then
    VF="$CLONE/$PLAN_DIR/verdict-fields-v1.4.0-rc.1.md"
    COND="$SCRATCH/CONDITIONS.md"
    printf -- '- Cobertura declarada: 6 partes, o resto fora por orcamento.\n' > "$COND"
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
    # C2 — caminho REAL. A linha do codex na PROVENANCE e reescrita para os
    # valores PINADOS (0.147.0 / aarch64-apple-darwin / payload do manifesto)
    # e o MANIFEST e regenerado. Isto e PLUMBING: o veredito das 6 partes
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
    for n in 1 2 3 4 5 6; do
      _mf="$_mf payload-rc1-$n.redacted.txt diff-rc1-$n.patch"
      _mf="$_mf paths-rc1-$n.manifest.txt verdict-rc1-$n.txt transcript-rc1-$n.log"
    done
    # shellcheck disable=SC2086
    ( cd "$CLONE/$EV" && shasum -a 256 $_mf PROVENANCE-rc1.md CANDIDATE.sha \
        run-rc1-repass.sh > MANIFEST-rc1.sha256 ) || bad "C2: regeneracao do MANIFEST falhou"
    if ( cd "$CLONE" && RC1_SELFTEST=1 RC1_SELFTEST_SCRATCH="$SCRATCH" \
         RC1_SELFTEST_SIGNER_FPR="$FPR" GNUPGHOME="$GH" \
         python3 "$PLAN_DIR/gen-envelope-rc1.py" --stage fields \
           --parent "$CAND" --conditions-file "$COND" ) > "$_gen" 2>&1; then
      ok "C2: gen --stage fields sobre evidencia com codex PINADO"
    else bad "C2: gen --stage fields"; sed -n '1,15p' "$_gen"; fi
    if [ -f "$VF" ]; then
      grep -q '^verdict: GO-WITH-CONDITIONS' "$VF" \
        && ok "veredito agregado DERIVADO dos 6 rails = GO-WITH-CONDITIONS" \
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
