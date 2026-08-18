#!/bin/bash
# test-w3-vcures.sh - probes das 4 excecoes nomeadas do verdito rc.2
# (V1/V2/V4/V5, repass-r2 parte a) curadas pelo pack W3.
#
#   bash scripts/tests/test-w3-vcures.sh [ROOT]
#
# ROOT = raiz do repo a testar (default: cwd). Contra uma arvore PRE-pack
# os probes V1/V2/V4/V5 devem FALHAR (o defeito existe - controle
# positivo); contra a arvore POS-pack, tudo verde.
set -euo pipefail

ROOT="${1:-.}"
ROOT="$(cd "$ROOT" && pwd)"
UP="$ROOT/scripts/upgrade.sh"
GEN="$ROOT/scripts/_framework_manifest_set.sh"
HL="$ROOT/scripts/_hash_lib.sh"
INST="$ROOT/scripts/install.sh"
[ -f "$UP" ] || { echo "FAIL: $UP ausente"; exit 2; }
[ -f "$GEN" ] || { echo "FAIL: $GEN ausente"; exit 2; }
[ -f "$HL" ] || HL="$(cd "$(dirname "$GEN")/.." && pwd)/scripts/_hash_lib.sh"
[ -f "$HL" ] || { echo "FAIL: _hash_lib.sh ausente"; exit 2; }
[ -f "$INST" ] || { echo "FAIL: $INST ausente"; exit 2; }

PASS=0; FAILC=0
ok()  { PASS=$((PASS+1)); printf '  ok   %s\n' "$1"; }
bad() { FAILC=$((FAILC+1)); printf '  FAIL %s\n' "$1"; }

TMP="$(mktemp -d)"
trap 'rm -r "$TMP" 2>/dev/null || true' EXIT

# --- V1: _ov_obs_prior_record recusa relpath em _BASELINE_INVALID ----------
# Extrai a funcao e roda em subshell controlado. Manifesto com linha
# valida para PROTOCOL.md; com o relpath marcado invalido a resposta
# CURADA e 'none' (pre-cura: 'hash' - replace forcado sob ambiguidade).
FN="$(sed -n '/^_ov_obs_prior_record()/,/^}/p' "$UP")"
[ -n "$FN" ] || { bad "V1: funcao _ov_obs_prior_record nao extraida"; }
MAN="$TMP/baseline.manifest"
H="0123456789012345678901234567890123456789012345678901234567890123"
printf '%s  PROTOCOL.md\n%s  PROTOCOL.md\n' "$H" "$H" > "$MAN"
V1A="$(bash -c '
  set -u
  eval "$1"
  _BASELINE_MANIFEST_FILE="$2"
  TARGET="/nonexistent"
  _BASELINE_INVALID="
PROTOCOL.md
"
  _ov_obs_prior_record "PROTOCOL.md"
' _ "$FN" "$MAN")"
if [ "$V1A" = "none" ]; then ok "V1: relpath invalido responde none (sem replace forcado)"
else bad "V1: relpath invalido respondeu '$V1A' (esperado none)"; fi
V1B="$(bash -c '
  set -u
  eval "$1"
  _BASELINE_MANIFEST_FILE="$2"
  TARGET="/nonexistent"
  _BASELINE_INVALID=""
  _ov_obs_prior_record "PROTOCOL.md"
' _ "$FN" "$MAN")"
if [ "$V1B" = "hash" ]; then ok "V1-controle: relpath valido segue respondendo hash (guarda nao e overbroad)"
else bad "V1-controle: relpath valido respondeu '$V1B' (esperado hash)"; fi

# --- V1b (r18): descendente invalido contamina a superficie agregada -------
MAN2="$TMP/baseline2.manifest"
printf '%s  SPEC/v1/foo.md\n%s  SPEC/v1/foo.md\n' "$H" "$H" > "$MAN2"
V1C="$(bash -c '
  set -u
  eval "$1"
  _BASELINE_MANIFEST_FILE="$2"
  TARGET="/nonexistent"
  _BASELINE_INVALID="
SPEC/v1/foo.md
"
  _ov_obs_prior_record "SPEC/v1"
' _ "$FN" "$MAN2")"
if [ "$V1C" = "none" ]; then ok "V1b: descendente invalido nega evidencia do agregado SPEC/v1"
else bad "V1b: agregado respondeu '$V1C' com descendente ambiguo (esperado none)"; fi
V1D="$(bash -c '
  set -u
  eval "$1"
  _BASELINE_MANIFEST_FILE="$2"
  TARGET="/nonexistent"
  _BASELINE_INVALID=""
  _ov_obs_prior_record "SPEC/v1"
' _ "$FN" "$MAN2")"
if [ "$V1D" = "hash" ]; then ok "V1b-controle: agregado sem ambiguidade segue respondendo hash"
else bad "V1b-controle: respondeu '$V1D' (esperado hash)"; fi

# --- V2: NOTE do --pin nao mente sobre VERSION ------------------------------
if grep -q "which reflects the pinned source" "$UP"; then
  bad "V2: NOTE ainda promete que VERSION reflete o pin"
else ok "V2: claim falsa removida"; fi
if grep -q "over-report" "$UP"; then
  ok "V2: NOTE avisa que VERSION over-reporta ate o proximo install"
else bad "V2: aviso honesto ausente"; fi

# --- V4: symlink rejeitado NAO vira hash record -----------------------------
# Gerador sourceado; marker = symlink para arquivo do adotante;
# FMS_LINK_PATHS = newline (deny-all explicito). Curado: NENHUM registro.
RT="$TMP/target"; mkdir -p "$RT/.claude"
echo "conteudo do adotante" > "$TMP/adopter.txt"
ln -s "$TMP/adopter.txt" "$RT/.claude/.framework-version"
OUT="$TMP/m1"
bash -c '
  set -u
  . "$4" 2>/dev/null
  . "$1" 2>/dev/null
  export FMS_ROOT="$2" FMS_MODE=link FMS_DELIVERED_MARKER=1
  export FMS_PROFILE_PARTS="" FMS_HASH_SOURCE_MARKER="HASH_TARGET"
  FMS_LINK_PATHS="$(printf "\n ")"; FMS_LINK_PATHS="${FMS_LINK_PATHS% }"
  export FMS_LINK_PATHS
  _write_baseline_manifest "$3"
' _ "$GEN" "$RT" "$OUT" "$HL" 2>"$TMP/v4.err" || true
if [ -f "$OUT" ] && grep -q "framework-version" "$OUT"; then
  bad "V4: symlink rejeitado gerou registro ($(grep framework-version "$OUT" | head -1 | cut -c1-40)...)"
else ok "V4: symlink sem autorizacao LINK nao gera registro algum"; fi
# Controle: unset FMS_LINK_PATHS (default allow-all do caminho install
# legado) segue produzindo o LINK record - a cura nao quebrou o default.
OUT2="$TMP/m2"
bash -c '
  set -u
  . "$4" 2>/dev/null
  . "$1" 2>/dev/null
  export FMS_ROOT="$2" FMS_MODE=link FMS_DELIVERED_MARKER=1
  export FMS_PROFILE_PARTS="" FMS_HASH_SOURCE_MARKER="HASH_TARGET"
  unset FMS_LINK_PATHS 2>/dev/null || true
  _write_baseline_manifest "$3"
' _ "$GEN" "$RT" "$OUT2" "$HL" 2>/dev/null || true
if [ -f "$OUT2" ] && grep -q "^LINK  .claude/.framework-version  " "$OUT2"; then
  ok "V4-controle: allow-all legado (unset) ainda serializa LINK record"
else bad "V4-controle: default unset deixou de gerar LINK record (quebra do caminho install legado)"; fi

# --- V5: install.sh exporta FMS_LINK_PATHS ----------------------------------
if grep -q "_CREATED_LINK_RELPATHS" "$INST" \
   && grep -q "export FMS_LINK_PATHS" "$INST"; then
  ok "V5: install.sh acumula links criados e exporta FMS_LINK_PATHS"
else bad "V5: caller do install nao passa a lista (allow-all continua)"; fi
bash -n "$INST" && ok "V5: install.sh sintaxe OK" || bad "V5: install.sh sintaxe"

# --- V5b (r11): substituicao nunca escreve atraves de symlink ------------
if grep -q "symlink — not substituting through it" "$INST"; then
  ok "V5b: apply_placeholder_substitutions pula symlinks"
else bad "V5b: substituicao ainda escreve atraves de symlink"; fi

printf '\n%d ok / %d fail\n' "$PASS" "$FAILC"
[ "$FAILC" -eq 0 ]
