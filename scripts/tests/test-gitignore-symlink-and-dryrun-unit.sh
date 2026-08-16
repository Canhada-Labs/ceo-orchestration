#!/bin/bash
# Unit-shell controls for the .gitignore delivery helpers (re-pass rc.4 t2
# P1 #1 + #3). Sources scripts/_framework_manifest_set.sh directly — no
# install, milliseconds (pattern: test-ownership-verdict-unit.sh).
#
#   S1  .claude/.gitignore SYMLINK to a writable file -> apply REFUSES (rc 1)
#       and the external target is byte-identical after the call
#   S2  DANGLING symlink -> apply REFUSES; the dangling target is NOT created
#   S3  seeded file (/cache/ only) -> preview says "would APPEND"; real apply
#       appends both entries (dry-run twin honesty — the seeded regression)
#   S4  absent file -> preview says "would CREATE"
#   S5  complete file -> preview says "would PRESERVE"
#   S6  root .gitignore SYMLINK -> mcp-secrets helper REFUSES (rc 1)
set -uo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
# shellcheck source=/dev/null
. "$HERE/../_framework_manifest_set.sh"

FAILS=0
_t() { # name rc_expected rc_actual
  if [ "$2" = "$3" ]; then echo "PASS: $1"; else echo "FAIL: $1 (rc esperado $2, veio $3)"; FAILS=$((FAILS + 1)); fi
}

TMP="$(mktemp -d "${TMPDIR:-/tmp}/gitignore-unit.XXXXXX")"
trap 'rm -rf "$TMP"' EXIT

# --- S1: symlink para arquivo externo gravável ---
mkdir -p "$TMP/s1/.claude"
echo "external content" > "$TMP/s1/external.txt"
ln -s "$TMP/s1/external.txt" "$TMP/s1/.claude/.gitignore"
_before="$(cat "$TMP/s1/external.txt")"
_apply_claude_dir_gitignore "$TMP/s1/.claude" >/dev/null 2>&1; rc=$?
_t "S1 apply recusa symlink" 1 "$rc"
_after="$(cat "$TMP/s1/external.txt")"
[ "$_before" = "$_after" ] && echo "PASS: S1 target externo intocado" \
  || { echo "FAIL: S1 target externo MODIFICADO"; FAILS=$((FAILS + 1)); }

# --- S2: symlink dangling ---
mkdir -p "$TMP/s2/.claude"
ln -s "$TMP/s2/nonexistent-target" "$TMP/s2/.claude/.gitignore"
_apply_claude_dir_gitignore "$TMP/s2/.claude" >/dev/null 2>&1; rc=$?
_t "S2 apply recusa symlink dangling" 1 "$rc"
[ ! -e "$TMP/s2/nonexistent-target" ] && echo "PASS: S2 target dangling NAO criado" \
  || { echo "FAIL: S2 target dangling foi CRIADO"; FAILS=$((FAILS + 1)); }

# --- S3: seeded (/cache/ only) — preview APPEND + apply apenda de verdade ---
mkdir -p "$TMP/s3/.claude"
printf '/cache/\n' > "$TMP/s3/.claude/.gitignore"
out="$(_preview_claude_dir_gitignore "$TMP/s3/.claude")"; rc=$?
_t "S3 preview rc" 0 "$rc"
case "$out" in
  *"would APPEND"*) echo "PASS: S3 preview diz would APPEND" ;;
  *) echo "FAIL: S3 preview nao disse would APPEND: $out"; FAILS=$((FAILS + 1)) ;;
esac
_apply_claude_dir_gitignore "$TMP/s3/.claude" >/dev/null 2>&1; rc=$?
_t "S3 apply rc" 0 "$rc"
grep -Fxq "/state/" "$TMP/s3/.claude/.gitignore" \
  && grep -Fxq "/settings.local.json" "$TMP/s3/.claude/.gitignore" \
  && grep -Fxq "/cache/" "$TMP/s3/.claude/.gitignore" \
  && echo "PASS: S3 apply apendou preservando o seed" \
  || { echo "FAIL: S3 apply nao entregou as entries"; FAILS=$((FAILS + 1)); }

# --- S4: ausente — preview CREATE ---
mkdir -p "$TMP/s4/.claude"
out="$(_preview_claude_dir_gitignore "$TMP/s4/.claude")"; rc=$?
_t "S4 preview rc" 0 "$rc"
case "$out" in
  *"would CREATE"*) echo "PASS: S4 preview diz would CREATE" ;;
  *) echo "FAIL: S4 preview nao disse would CREATE: $out"; FAILS=$((FAILS + 1)) ;;
esac
[ ! -e "$TMP/s4/.claude/.gitignore" ] && echo "PASS: S4 preview nao escreveu nada" \
  || { echo "FAIL: S4 preview ESCREVEU"; FAILS=$((FAILS + 1)); }

# --- S5: completo — preview PRESERVE ---
mkdir -p "$TMP/s5/.claude"
_claude_dir_gitignore_body > "$TMP/s5/.claude/.gitignore"
out="$(_preview_claude_dir_gitignore "$TMP/s5/.claude")"; rc=$?
_t "S5 preview rc" 0 "$rc"
case "$out" in
  *"would PRESERVE"*) echo "PASS: S5 preview diz would PRESERVE" ;;
  *) echo "FAIL: S5 preview nao disse would PRESERVE: $out"; FAILS=$((FAILS + 1)) ;;
esac

# --- S6: root .gitignore symlink — helper mcp recusa ---
mkdir -p "$TMP/s6"
echo "external root" > "$TMP/s6/external-root.txt"
ln -s "$TMP/s6/external-root.txt" "$TMP/s6/.gitignore"
_apply_mcp_secrets_ignore "$TMP/s6/.gitignore" >/dev/null 2>&1; rc=$?
_t "S6 root helper recusa symlink" 1 "$rc"
_after="$(cat "$TMP/s6/external-root.txt")"
[ "$_after" = "external root" ] && echo "PASS: S6 root target intocado" \
  || { echo "FAIL: S6 root target modificado"; FAILS=$((FAILS + 1)); }

# --- S7: posture writer (3o writer do root) recusa symlink ---
mkdir -p "$TMP/s7"
echo "external root 7" > "$TMP/s7/external-root.txt"
ln -s "$TMP/s7/external-root.txt" "$TMP/s7/.gitignore"
_apply_posture_state_ignores "$TMP/s7/.gitignore" >/dev/null 2>&1; rc=$?
_t "S7 posture writer recusa symlink" 1 "$rc"
_after="$(cat "$TMP/s7/external-root.txt")"
[ "$_after" = "external root 7" ] && echo "PASS: S7 target intocado" \
  || { echo "FAIL: S7 target modificado"; FAILS=$((FAILS + 1)); }

# --- S8: predicado compartilhado de preview ---
_root_gitignore_symlink_guard "$TMP/s7/.gitignore" >/dev/null 2>&1; rc=$?
_t "S8 preview guard detecta symlink" 1 "$rc"
mkdir -p "$TMP/s8"; printf 'x\n' > "$TMP/s8/.gitignore"
_root_gitignore_symlink_guard "$TMP/s8/.gitignore" >/dev/null 2>&1; rc=$?
_t "S8 preview guard passa arquivo regular" 0 "$rc"

# --- S9 (t8 P1): presenca textual != exclusao EFETIVA — negacao `!*.json`
# apos a linha exata vence no git; o applier deve RE-ASSERTAR (append apos a
# negacao) ate o probe ficar ignorado, no NESTED e no ROOT.
mkdir -p "$TMP/s9/.claude"
( cd "$TMP/s9" && git init -q )
printf '/settings.local.json\n/state/\n!*.json\n' > "$TMP/s9/.claude/.gitignore"
_apply_claude_dir_gitignore "$TMP/s9/.claude" >/dev/null 2>&1; rc=$?
_t "S9 nested apply rc=0" 0 "$rc"
if ( cd "$TMP/s9" && git check-ignore -q -- .claude/settings.local.json ); then
  echo "PASS: S9 settings.local.json EFETIVAMENTE ignorado apos re-assercao"
else
  echo "FAIL: S9 negacao !*.json continua vencendo"; FAILS=$((FAILS + 1))
fi
if ( cd "$TMP/s9" && git check-ignore -q -- .claude/state/probe ); then
  echo "PASS: S9 state/ segue efetivo"
else
  echo "FAIL: S9 state/ nao efetivo"; FAILS=$((FAILS + 1))
fi
# ROOT: mesma classe no .gitignore da raiz
mkdir -p "$TMP/s9r"
( cd "$TMP/s9r" && git init -q )
printf '.claude/settings.local.json\n!*.json\n' > "$TMP/s9r/.gitignore"
_apply_posture_state_ignores "$TMP/s9r/.gitignore" >/dev/null 2>&1; rc=$?
_t "S9 root apply rc=0" 0 "$rc"
if ( cd "$TMP/s9r" && git check-ignore -q -- .claude/settings.local.json ); then
  echo "PASS: S9 root settings.local.json efetivo apos re-assercao"
else
  echo "FAIL: S9 root negacao continua vencendo"; FAILS=$((FAILS + 1))
fi

echo
if [ "$FAILS" -eq 0 ]; then echo "ALL GREEN"; exit 0; else echo "$FAILS FAIL(s)"; exit 1; fi
