#!/usr/bin/env bash
# =============================================================================
# PLAN-168 W2 (AC-6/AC-6b) — INV-4 as an executable assertion.
#
# INV-4: install and upgrade produce the SAME root PROTOCOL.md pointer.
# Byte identity alone is VACUOUS (codex rail r1 P1: a shared generator based
# on the broken template would make both sides identical AND wrong), so every
# leg also asserts CONTENT: the {{PROTOCOL_SOURCE}} token is ABSENT and the
# resolved source path is PRESENT.
#
# Legs (all with NORMALIZED inputs — pwd -P, fixed profile/stack):
#   L1  install -> upgrade         : pointer byte-identical, content sound
#   L2  upgrade -> upgrade         : idempotent, byte-identical
#   L3  degraded body -> upgrade   : CURED (refreshed with backup, sound)
#   L4  adopter-edited -> upgrade  : PRESERVED byte-identical (S238 guard —
#                                    the cure must never widen into clobber)
#
# Exit: 0 all legs pass · 1 failure · 2 harness error.
# =============================================================================
set -uo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# shellcheck source=/dev/null
. "$REPO_ROOT/scripts/_framework_manifest_set.sh" 2>/dev/null || {
  echo "ERROR: cannot source _framework_manifest_set.sh" >&2; exit 2; }
command -v _render_protocol_pointer_degraded >/dev/null 2>&1 || {
  echo "ERROR: generator missing (W2 not in tree)" >&2; exit 2; }

WORK="$( mktemp -d "${TMPDIR:-/tmp}/inv4.XXXXXX" )" || exit 2
WORK="$( cd "$WORK" && pwd -P )"
trap 'chmod -R u+w "$WORK" 2>/dev/null; rm -rf "$WORK" 2>/dev/null' EXIT

PROFILE=core
STACK=generic
FAILURES=0
fail() { echo "FAIL  $1"; FAILURES=$((FAILURES+1)); }

run_install() { # $1=target
  CEO_INSTALL_SKIP_SELF_SHA=1 CEO_RAG_INSTALL_PROMPT=0 \
    bash "$REPO_ROOT/scripts/install.sh" "$1" --profile "$PROFILE" --stack "$STACK" \
    > "$WORK/install.log" 2>&1
}
run_upgrade() { # $1=target $2=log
  CEO_INSTALL_SKIP_SELF_SHA=1 \
    bash "$REPO_ROOT/scripts/upgrade.sh" "$1" --profile "$PROFILE" --stack "$STACK" \
    > "$2" 2>&1
}
assert_sound() { # $1=file $2=label — token absent, resolved source present
  if grep -F -q '{{PROTOCOL_SOURCE}}' "$1"; then
    fail "$2: token {{PROTOCOL_SOURCE}} still present (degraded output)"
    return 1
  fi
  if ! grep -F -q "$REPO_ROOT/PROTOCOL.md" "$1"; then
    fail "$2: resolved source path missing from pointer"
    return 1
  fi
  return 0
}

T="$WORK/t"; mkdir -p "$T"; ( cd "$T" && git init -q )
T="$( cd "$T" && pwd -P )"

# --- L1: install -> upgrade ---------------------------------------------------
if ! run_install "$T"; then
  echo "ERROR: install failed"; sed -n '1,8p' "$WORK/install.log"; exit 2
fi
cp "$T/PROTOCOL.md" "$WORK/after-install.md"
assert_sound "$WORK/after-install.md" "L1 post-install" || true
if ! run_upgrade "$T" "$WORK/upgrade1.log"; then
  echo "ERROR: upgrade failed"; sed -n '1,12p' "$WORK/upgrade1.log"; exit 2
fi
if cmp -s "$WORK/after-install.md" "$T/PROTOCOL.md"; then
  assert_sound "$T/PROTOCOL.md" "L1 post-upgrade" && echo "PASS  L1 install->upgrade byte-identical + sound"
else
  fail "L1 pointer changed across install->upgrade (INV-4 broken)"
  diff "$WORK/after-install.md" "$T/PROTOCOL.md" | head -8
fi

# --- L2: upgrade -> upgrade (idempotence) ------------------------------------
cp "$T/PROTOCOL.md" "$WORK/after-up1.md"
if ! run_upgrade "$T" "$WORK/upgrade2.log"; then
  echo "ERROR: second upgrade failed"; sed -n '1,12p' "$WORK/upgrade2.log"; exit 2
fi
if cmp -s "$WORK/after-up1.md" "$T/PROTOCOL.md"; then
  echo "PASS  L2 upgrade->upgrade idempotent"
else
  fail "L2 pointer churned across repeat upgrade"
  diff "$WORK/after-up1.md" "$T/PROTOCOL.md" | head -8
fi

# --- L3: degraded body is CURED ----------------------------------------------
_render_protocol_pointer_degraded "$T" "$PROFILE" "$STACK" > "$T/PROTOCOL.md"
cp "$T/PROTOCOL.md" "$WORK/planted-degraded.md"
if ! run_upgrade "$T" "$WORK/upgrade3.log"; then
  echo "ERROR: cure upgrade failed"; sed -n '1,12p' "$WORK/upgrade3.log"; exit 2
fi
if grep -F -q '{{PROTOCOL_SOURCE}}' "$T/PROTOCOL.md"; then
  fail "L3 degraded pointer NOT cured (token survived the upgrade — immortal defect)"
  sed -n '1,6p' "$T/PROTOCOL.md"
else
  assert_sound "$T/PROTOCOL.md" "L3 post-cure" || true
  if grep -q "CURED: PROTOCOL.md" "$WORK/upgrade3.log"; then
    echo "PASS  L3 degraded body cured (REFRESH route taken)"
  else
    fail "L3 pointer sound but the CURED route was not what ran (check upgrade3.log)"
    grep -n "PROTOCOL.md" "$WORK/upgrade3.log" | head -5
  fi
  # The log line is NOT evidence: upgrade.sh prints "BACKED UP" even when the
  # cp fails (|| true), and the real location is .claude.bak/<timestamp>, not
  # .claude/backup* (codex pack-review P2). Assert the BYTES: the newest
  # backup file must be exactly the degraded body we planted.
  BKP="$( ls -t "$T"/.claude.bak/*/PROTOCOL.md 2>/dev/null | head -1 )"
  if [ -n "$BKP" ] && cmp -s "$BKP" "$WORK/planted-degraded.md"; then
    echo "PASS  L3b cure kept a byte-exact backup of the degraded original"
  else
    fail "L3b backup missing or does not match the planted degraded bytes (BKP=${BKP:-<none>})"
  fi
fi

# --- L4: adopter-customized pointer is PRESERVED (S238 guard) ----------------
printf '\nAdopter note: we run upgrades on Fridays.\n' >> "$T/PROTOCOL.md"
cp "$T/PROTOCOL.md" "$WORK/customized.md"
if ! run_upgrade "$T" "$WORK/upgrade4.log"; then
  echo "ERROR: preserve-leg upgrade failed"; sed -n '1,12p' "$WORK/upgrade4.log"; exit 2
fi
if cmp -s "$WORK/customized.md" "$T/PROTOCOL.md"; then
  echo "PASS  L4 adopter-customized pointer preserved byte-identical"
else
  fail "L4 adopter-customized pointer was MODIFIED (the cure widened into clobber — S238)"
  diff "$WORK/customized.md" "$T/PROTOCOL.md" | head -8
fi

echo ""
if [[ "$FAILURES" -gt 0 ]]; then
  echo "INV-4 assertion: $FAILURES leg(s) FAILED"
  exit 1
fi
echo "INV-4 assertion: 4/4 legs pass (byte identity + content soundness + cure + preserve)"
exit 0
