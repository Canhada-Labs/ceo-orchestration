#!/usr/bin/env bash
# =============================================================================
# PLAN-168 W2 — unit control for the shared protocol-pointer generator
# (_render_protocol_pointer / _render_protocol_pointer_degraded /
# _protocol_pointer_is_degraded in scripts/_framework_manifest_set.sh).
#
# Scenarios:
#   R1  healthy render == REAL install.sh output, byte for byte (the parity
#       that IS INV-4's fix — normalized inputs, as the plan requires)
#   R2  degraded render | substitute-token == healthy render (one template)
#   R3  recognizer: exact degraded file => rc=0 (curable)
#   R4  recognizer: healthy (substituted) file => rc=1 (never curable)
#   R5  recognizer: degraded file + 1-char adopter edit => rc=1 (preserved)
#   R6  recognizer: adopter file that merely CONTAINS the token => rc=1
#       (the codex r1 P1 substring-destruction case)
#   R7  recognizer: unparseable upgrade line (space in target) => rc=1
#   R8  inside-target checkout => relative render (no token, no source path)
#
# Exit: 0 all pass · 1 failure · 2 harness error.
# =============================================================================
set -uo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# shellcheck source=/dev/null
. "$REPO_ROOT/scripts/_framework_manifest_set.sh" 2>/dev/null || {
  echo "ERROR: cannot source _framework_manifest_set.sh" >&2; exit 2; }
for fn in _render_protocol_pointer _render_protocol_pointer_degraded _protocol_pointer_is_degraded; do
  command -v "$fn" >/dev/null 2>&1 || { echo "ERROR: $fn missing" >&2; exit 2; }
done

WORK="$( mktemp -d "${TMPDIR:-/tmp}/ptr-render.XXXXXX" )" || exit 2
trap 'chmod -R u+w "$WORK" 2>/dev/null; rm -rf "$WORK" 2>/dev/null' EXIT

FAILURES=0
say() { echo "$1"; }
fail() { echo "FAIL  $1"; FAILURES=$((FAILURES+1)); }

# --- R1: byte parity with a REAL install --------------------------------------
# Normalized target (physical path, no trailing/double slashes) — install.sh
# normalizes its TARGET, and the plan requires normalized inputs for exactly
# this reason.
U="$WORK/t"; mkdir -p "$U"
U="$( cd "$U" && pwd -P )"
( cd "$U" && git init -q )
if CEO_INSTALL_SKIP_SELF_SHA=1 CEO_RAG_INSTALL_PROMPT=0 \
     bash "$REPO_ROOT/scripts/install.sh" "$U" --profile core --stack generic \
     > "$WORK/install.log" 2>&1; then
  _render_protocol_pointer "$REPO_ROOT" "$U" core generic "$REPO_ROOT" > "$WORK/render.txt"
  if diff -u "$U/PROTOCOL.md" "$WORK/render.txt" > "$WORK/r1.diff" 2>&1; then
    say "PASS  R1 healthy render == real install output"
  else
    fail "R1 parity with real install"; sed -n '1,10p' "$WORK/r1.diff"
  fi
else
  fail "R1 install.sh itself failed (see $WORK/install.log)"; sed -n '1,5p' "$WORK/install.log"
fi

# --- R2: one template — degraded | substitution == healthy --------------------
_render_protocol_pointer_degraded "$U" core generic \
  | sed "s|{{PROTOCOL_SOURCE}}|$( printf '%s' "$REPO_ROOT" | sed 's/[|&\\]/\\&/g' )|g" \
  > "$WORK/deg-subst.txt"
if diff -q "$WORK/deg-subst.txt" "$WORK/render.txt" >/dev/null 2>&1; then
  say "PASS  R2 degraded+substitute == healthy (single template)"
else
  fail "R2 template split"; diff "$WORK/deg-subst.txt" "$WORK/render.txt" | head -5
fi

# --- R3: recognizer accepts an exact degraded body ----------------------------
_render_protocol_pointer_degraded "$U" core generic > "$WORK/degraded.md"
if _protocol_pointer_is_degraded "$WORK/degraded.md"; then
  say "PASS  R3 exact degraded body recognized (curable)"
else
  fail "R3 exact degraded body NOT recognized"
fi

# --- R4: healthy file is never "degraded" -------------------------------------
if _protocol_pointer_is_degraded "$WORK/render.txt"; then
  fail "R4 healthy file misclassified as degraded"
else
  say "PASS  R4 healthy file not curable (preserved)"
fi

# --- R5: one adopter edit anywhere => preserved -------------------------------
sed 's/git pull/git fetch/' "$WORK/degraded.md" > "$WORK/degraded-edited.md"
if _protocol_pointer_is_degraded "$WORK/degraded-edited.md"; then
  fail "R5 edited degraded body still classified curable (DATA LOSS route)"
else
  say "PASS  R5 edited degraded body preserved"
fi

# --- R6: adopter file that merely CONTAINS the token --------------------------
printf '%s\n' "# My protocol notes" "" \
  "We keep the marker {{PROTOCOL_SOURCE}} here on purpose." \
  "  {{PROTOCOL_SOURCE}}/scripts/upgrade.sh $U --profile core --stack generic" \
  > "$WORK/adopter.md"
if _protocol_pointer_is_degraded "$WORK/adopter.md"; then
  fail "R6 adopter file containing the token misclassified (substring trap)"
else
  say "PASS  R6 token-containing adopter file preserved"
fi

# --- R7: unparseable upgrade line (space in target) => preserved --------------
_render_protocol_pointer_degraded "/tmp/has space" core generic > "$WORK/spacey.md"
if _protocol_pointer_is_degraded "$WORK/spacey.md"; then
  fail "R7 ambiguous (spaced) target treated as parseable"
else
  say "PASS  R7 ambiguous target preserved (documented residual)"
fi

# --- R8: inside-target checkout renders the relative form ---------------------
IN="$WORK/inside"; mkdir -p "$IN/vendor/ceo"
IN="$( cd "$IN" && pwd -P )"
_render_protocol_pointer "$IN/vendor/ceo" "$IN" core generic "$IN/vendor/ceo" > "$WORK/rel.txt"
if grep -q '\./vendor/ceo/PROTOCOL.md' "$WORK/rel.txt" \
   && ! grep -q '{{PROTOCOL_SOURCE}}' "$WORK/rel.txt" \
   && ! grep -F -q "$IN/vendor" "$WORK/rel.txt"; then
  say "PASS  R8 inside-target => relative render"
else
  fail "R8 inside-target render wrong"; sed -n '1,8p' "$WORK/rel.txt"
fi

echo ""
if [[ "$FAILURES" -gt 0 ]]; then
  echo "protocol-pointer render control: $FAILURES FAILED"
  exit 1
fi
echo "protocol-pointer render control: 8/8 pass"
exit 0
