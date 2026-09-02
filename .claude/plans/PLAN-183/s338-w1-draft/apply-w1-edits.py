#!/usr/bin/env python3
"""apply-w1-edits.py — a DERIVACAO do patch da PLAN-183 W1 (ponteiro portatil e retroativo, A1).

DRAFT da S338 (night-run). Este script e o unico caminho pelo qual a sombra muda:
uma lista de (path, ancora EXATA, substituto, ocorrencias esperadas) aplicada
sobre uma arvore em BASE = HEAD + wave-fable51 (apply-fable51-edits.py
commitado dentro da sombra). Uma ancora ausente, ambigua ou ja aplicada e
RECUSA nomeada antes de qualquer escrita — nunca "best effort". Um LAND futuro
prova `BASE + este script == patch` byte a byte em cada path.

O que a W1 muda (mecanismo, nao narrativa — ver DESIGN-W1-S338.md):
  * scripts/_framework_manifest_set.sh — `_render_protocol_pointer` decide a
    relativizacao DENTRO (ramo fora-do-target: fonte ABSOLUTA vira relativa ao
    TARGET via `_rpp_relpath`, valor irrepresentavel fica VERBATIM); template
    portatil novo (`_render_protocol_pointer_portable`) que NOMEIA
    --protocol-source e nao carrega path de maquina; template legado CONGELADO
    (`_render_protocol_pointer_legacy` == degraded|sed, a identidade R2 pre-W1);
    reconhecedor de "absoluto legado" (`_protocol_pointer_legacy_source`) por
    reconstrucao byte-a-byte a partir dos valores do PROPRIO arquivo;
    `_ownership_verdict` passa a possuir `legacy_absolute` como possui `degraded`.
  * scripts/upgrade.sh — `--protocol-source`/`CEO_PROTOCOL_SOURCE` (o MESMO par
    do install.sh; precedencia 0, allowlist positiva, persistido no
    install-state SO quando explicito e aceito); cura retroativa (classe
    `legacy_absolute` => REFRESH com backup, mantendo a FONTE que o arquivo
    nomeia, so a FORMA migra); preservacao AVISADA (WARNING nomeado quando o
    ponteiro preservado/mantido carrega path absoluto ou nao resolve).
  * scripts/install.sh — UMA chamada ao gerador com a fonte resolvida (a
    identidade `degraded|sed == healthy` que o pass de placeholders explorava
    deixou de valer; sem esta edicao INV-4 L1 fica VERMELHO).
  * testes: render (R2 re-pinado no template legado + R10..R13), inv4
    (`assert_sound` exige RESOLUCAO, nao o path absoluto; L5 cura legada),
    NOVO e2e test-protocol-pointer-portable.sh (P1 juntos / P2 sozinho + reparo
    / P3 retroativo a partir da release anterior REAL / P4 preservacao avisada).
  * triade de ownership: 3 linhas novas no TSV (OWN-0095..0097), enum §2.4 +
    regra R-04c no doc, ramo `legacy_absolute)` no harness e2e (NAO executado
    aqui — 25 min nightly; o mapa-baseline e os expected-reds ficam para a
    corrida real, dito no EVIDENCE.md).
  * .claude/scripts/data/installer-write-safety-baseline.txt — RE-GERADO pelo
    proprio censo (`--write-baseline`) como pos-passo, nunca a mao: as linhas
    sao chaveadas por numero de linha e a W1 desloca install.sh/upgrade.sh.

Uso:
    python3 apply-w1-edits.py --root <arvore-em-BASE>
    python3 apply-w1-edits.py --root <arvore> --check-only   (so ancoras)
    python3 apply-w1-edits.py --list-paths

Saidas: 0 = aplicado (ou, com --check-only, aplicavel); 1 = recusa nomeada;
2 = erro de uso. Stdlib-only, Python >= 3.9, sem PEP 604 em runtime.
"""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

# Marcador de "ja aplicado": um identificador que a W1 introduz e que NAO pode
# existir em nenhum path tocado antes da aplicacao.
NEW_MARKER = "_render_protocol_pointer_portable"
BASELINE_REL = ".claude/scripts/data/installer-write-safety-baseline.txt"
CENSUS_REL = ".claude/scripts/check-installer-write-safety.py"
NEW_TEST_REL = "scripts/tests/test-protocol-pointer-portable.sh"

MANIFEST = "scripts/_framework_manifest_set.sh"
UPGRADE = "scripts/upgrade.sh"
INSTALL = "scripts/install.sh"
RENDER_T = "scripts/tests/test-protocol-pointer-render.sh"
INV4_T = "scripts/tests/test-protocol-pointer-inv4.sh"
TSV = "scripts/tests/ownership_table.tsv"
DOC = "docs/ownership-decision-table.md"
HARNESS = "scripts/tests/test-ownership-table.sh"
NIGHTLY_WF = ".github/workflows/ownership-nightly.yml"
SMOKE_WF = ".github/workflows/smoke-install.yml"

# --------------------------------------------------------------------------
# Conteudo do NOVO e2e (arquivo criado, nao ancorado).
# --------------------------------------------------------------------------
NEW_TEST_BODY = r'''#!/usr/bin/env bash
# =============================================================================
# PLAN-183 W1 (A1) — the PORTABLE protocol pointer, end to end.
#
# What the relative pointer BUYS, and what it does not (plan §W1, pair-rail
# r8+r9): it survives moving the project and the framework checkout TOGETHER
# (another $HOME, another username — the field breakage class); moving the
# target ALONE cannot be encoded by any pointer, so the correct answer is a
# NAMED error that leads to the repair interface, never a magic resolution.
#
# Legs (NORMALIZED inputs: pwd -P, fixed profile/stack):
#   P1  move source+target TOGETHER (common prefix renamed) => the pointer
#       RESOLVES to the moved checkout; the body carries no absolute path.
#       Then an upgrade run from the MOVED checkout exits 0 and leaves the
#       pointer byte-identical (never a clobber), with no false warning.
#   P2  (installed from the MOVED copy of P1, so the repair value below differs
#       from the install-time value) move the target ALONE => the pointer does
#       NOT resolve; its body names --protocol-source; a plain upgrade PRESERVES
#       it byte-identical and prints the NAMED "does not resolve" warning; the
#       repair recipe the body gives (rm + upgrade.sh . --protocol-source THIS
#       tree) yields a pointer that resolves, and the value is persisted in
#       .claude/.install-state.json — provably CHANGED from the recorded one.
#   P3  RETROACTIVE: an install made by the PREVIOUS shipped release (git
#       archive of the newest non-rc v1.x tag) writes the absolute legacy body;
#       upgrading with THIS tree ends with a portable pointer naming the SAME
#       checkout, the legacy CURED route reported, backup byte-exact.
#   P4  WARNED preservation: an adopter-edited pointer that names an absolute
#       path survives byte-identical AND the upgrade prints the absolute-path
#       WARNING naming --protocol-source.
#
# Exit: 0 all pass · 1 failure · 2 harness error. Network-free; writes only
# under mktemp -d. Requires: git (with release tags), python3, tar.
# =============================================================================
set -uo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
REPO_ROOT_P="$( cd "$REPO_ROOT" && pwd -P )"

# shellcheck source=/dev/null
. "$REPO_ROOT/scripts/_framework_manifest_set.sh" 2>/dev/null || {
  echo "ERROR: cannot source _framework_manifest_set.sh" >&2; exit 2; }
for fn in _render_protocol_pointer _render_protocol_pointer_legacy _protocol_pointer_legacy_source; do
  command -v "$fn" >/dev/null 2>&1 || { echo "ERROR: $fn missing (W1 not in tree)" >&2; exit 2; }
done

WORK="$( mktemp -d "${TMPDIR:-/tmp}/ptr-portable.XXXXXX" )" || exit 2
WORK="$( cd "$WORK" && pwd -P )"
trap 'chmod -R u+w "$WORK" 2>/dev/null; rm -rf "$WORK" 2>/dev/null' EXIT

PROFILE=core
STACK=generic
FAILURES=0
PASSES=0
pass() { echo "PASS  $1"; PASSES=$((PASSES+1)); }
fail() { echo "FAIL  $1"; FAILURES=$((FAILURES+1)); }

# The checkout the pointer names, and whether it lands where expected when
# resolved from the target's directory (relative) or as given (absolute).
named_checkout() { sed -n 's|^\(..*\)/PROTOCOL\.md$|\1|p' "$1" | sed -n '1p'; }
resolves_to() { # $1=pointer file $2=target dir $3=expected checkout (physical)
  local named base
  named="$( named_checkout "$1" )"
  [ -n "$named" ] || return 1
  case "$named" in /*) base="$named" ;; *) base="$2/$named" ;; esac
  [ -f "$base/PROTOCOL.md" ] || return 1
  [ "$( cd "$base" 2>/dev/null && pwd -P )" = "$3" ]
}
has_abs_path() { grep -Eq '(^|[[:space:]])/[^[:space:]]' "$1"; }

# A MOVABLE copy of this checkout: the source must live under the prefix that
# gets renamed. .git and the framework-internal plans tree are not part of an
# install and are the bulk of the size; everything install.sh reads travels.
copy_checkout() { # $1=dest
  mkdir -p "$1"
  ( cd "$REPO_ROOT" && tar -cf - --exclude='./.git' --exclude='./.git/*' \
      --exclude='./.claude/plans' --exclude='./.claude/plans/*' \
      --exclude='./node_modules' --exclude='./node_modules/*' . ) \
    | ( cd "$1" && tar -xf - )
}
run_install() { # $1=source $2=target
  CEO_INSTALL_SKIP_SELF_SHA=1 CEO_RAG_INSTALL_PROMPT=0 \
    bash "$1/scripts/install.sh" "$2" --profile "$PROFILE" --stack "$STACK"
}
run_upgrade() { # $1=source $2=target $3=log
  CEO_INSTALL_SKIP_SELF_SHA=1 \
    bash "$1/scripts/upgrade.sh" "$2" --profile "$PROFILE" --stack "$STACK" > "$3" 2>&1
}

# ---------------------------------------------------------------------------
# P1 — move source AND target TOGETHER (common prefix renamed)
# ---------------------------------------------------------------------------
H1="$WORK/home-alice"; mkdir -p "$H1/src"
copy_checkout "$H1/src/ceo-orchestration" || { echo "ERROR: could not copy the checkout"; exit 2; }
A1="$H1/src/my-app"; mkdir -p "$A1"; ( cd "$A1" && git init -q )
if ! run_install "$H1/src/ceo-orchestration" "$A1" > "$WORK/p1-install.log" 2>&1; then
  echo "ERROR: P1 install failed"; sed -n '1,12p' "$WORK/p1-install.log"; exit 2
fi
P1_NAMED="$( named_checkout "$A1/PROTOCOL.md" )"
if [ "$P1_NAMED" = "../ceo-orchestration" ] && ! has_abs_path "$A1/PROTOCOL.md"; then
  pass "P1a fresh install names the sibling checkout relatively ('$P1_NAMED'); no absolute path in the body"
else
  fail "P1a pointer not portable at install (named='$P1_NAMED')"; sed -n '1,14p' "$A1/PROTOCOL.md"
fi
cp "$A1/PROTOCOL.md" "$WORK/p1-before-move.md"
H2="$WORK/home-bob"
mv "$H1" "$H2" || { echo "ERROR: cannot rename the common prefix"; exit 2; }
A2="$H2/src/my-app"; C2="$H2/src/ceo-orchestration"
C2_P="$( cd "$C2" && pwd -P )"
if resolves_to "$A2/PROTOCOL.md" "$A2" "$C2_P"; then
  pass "P1b after renaming the common prefix the pointer RESOLVES to the moved checkout"
else
  fail "P1b pointer does not resolve after moving source+target together"
fi
# The upgrade that runs from the MOVED checkout must not clobber a pointer that
# is already correct — whatever route it takes. rc and bytes are the evidence.
if run_upgrade "$C2" "$A2" "$WORK/p1-upgrade.log"; then
  if cmp -s "$WORK/p1-before-move.md" "$A2/PROTOCOL.md"; then
    pass "P1c upgrade from the moved checkout exits 0 and leaves the pointer byte-identical"
  else
    fail "P1c upgrade after the joint move changed the pointer"; diff "$WORK/p1-before-move.md" "$A2/PROTOCOL.md" | head -8
  fi
else
  fail "P1c upgrade from the moved checkout failed"; sed -n '1,12p' "$WORK/p1-upgrade.log"
fi
if grep -q "does not resolve" "$WORK/p1-upgrade.log"; then
  fail "P1d upgrade printed the 'does not resolve' warning on a pointer that resolves"
else
  pass "P1d no false 'does not resolve' warning after the joint move"
fi
echo "  (P1 route reported by the upgrade: $( grep -E 'SKIP: PROTOCOL|PRESERVED \(root PROTOCOL|REFRESHED: PROTOCOL|CURED: PROTOCOL' "$WORK/p1-upgrade.log" | head -1 | sed 's/^ *//' ))"

# ---------------------------------------------------------------------------
# P2 — move the target ALONE: named error + repair via --protocol-source
# ---------------------------------------------------------------------------
# The install source is the MOVED copy from P1 (a real, working checkout that is
# NOT this tree): the repair below re-points at THIS tree, so the persisted
# value provably CHANGES — a repair that names the install-time value would
# make the persistence assertion vacuous (the install already recorded it).
X1="$WORK/x/app"; mkdir -p "$X1"; ( cd "$X1" && git init -q )
if ! run_install "$C2" "$X1" > "$WORK/p2-install.log" 2>&1; then
  echo "ERROR: P2 install failed"; sed -n '1,12p' "$WORK/p2-install.log"; exit 2
fi
if resolves_to "$X1/PROTOCOL.md" "$X1" "$C2_P" && ! has_abs_path "$X1/PROTOCOL.md"; then
  pass "P2a install from a far-away checkout resolves in place, relative, absolute-free"
else
  fail "P2a fresh pointer does not resolve in place or carries an absolute path"; sed -n '1,14p' "$X1/PROTOCOL.md"
fi
read_state_source() { # $1=target -> request.placeholders.PROTOCOL_SOURCE or ""
  python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); print(((d.get("request") or {}).get("placeholders") or {}).get("PROTOCOL_SOURCE",""))' "$1/.claude/.install-state.json" 2>/dev/null
}
P2_STATE0="$( read_state_source "$X1" )"
if [ "$P2_STATE0" = "$C2" ]; then
  pass "P2a2 install recorded its own checkout in install-state (the value the repair must change)"
else
  fail "P2a2 install-state does not record the install checkout (got '$P2_STATE0')"
fi
cp "$X1/PROTOCOL.md" "$WORK/p2-before-move.md"
mkdir -p "$WORK/y/deeper"
X2="$WORK/y/deeper/app"
mv "$X1" "$X2" || { echo "ERROR: cannot move the target"; exit 2; }
if resolves_to "$X2/PROTOCOL.md" "$X2" "$C2_P"; then
  fail "P2b pointer still resolves after moving the target alone — it is not relative to the target (pre-W1 absolute form?)"
else
  pass "P2b after moving the target ALONE the pointer no longer resolves (no relative encoding survives this)"
fi
if grep -F -q -- '--protocol-source' "$X2/PROTOCOL.md"; then
  pass "P2c the broken pointer's own body names the repair interface (--protocol-source)"
else
  fail "P2c body does not name --protocol-source"; sed -n '1,14p' "$X2/PROTOCOL.md"
fi
# A plain upgrade: the framework will not guess where the checkout went —
# PRESERVE, byte-identical, and the NAMED warning that leads to the repair.
run_upgrade "$REPO_ROOT" "$X2" "$WORK/p2-upgrade.log"; P2_RC=$?
if [ "$P2_RC" -eq 0 ] && cmp -s "$WORK/p2-before-move.md" "$X2/PROTOCOL.md"; then
  pass "P2d plain upgrade after the lone move preserves the pointer byte-identical (rc=0)"
else
  fail "P2d plain upgrade changed the pointer or failed (rc=$P2_RC)"
  diff "$WORK/p2-before-move.md" "$X2/PROTOCOL.md" | head -8; sed -n '1,12p' "$WORK/p2-upgrade.log"
fi
if grep -q "does not resolve" "$WORK/p2-upgrade.log" && grep -F -q -- '--protocol-source' "$WORK/p2-upgrade.log"; then
  pass "P2e upgrade printed the NAMED 'does not resolve' warning with the repair interface"
else
  fail "P2e no named warning for the unresolvable pointer"; grep -n "PROTOCOL" "$WORK/p2-upgrade.log" | head -5
fi
# The repair the body prescribes, run FROM the target directory as written.
( cd "$X2" && rm PROTOCOL.md && CEO_INSTALL_SKIP_SELF_SHA=1 \
    bash "$REPO_ROOT/scripts/upgrade.sh" . --profile "$PROFILE" --stack "$STACK" --protocol-source "$REPO_ROOT" ) \
    > "$WORK/p2-repair.log" 2>&1; P2R_RC=$?
if [ "$P2R_RC" -eq 0 ] && resolves_to "$X2/PROTOCOL.md" "$X2" "$REPO_ROOT_P" && ! has_abs_path "$X2/PROTOCOL.md"; then
  pass "P2f the prescribed repair yields a pointer that resolves again, still absolute-free"
else
  fail "P2f repair recipe failed (rc=$P2R_RC)"; sed -n '1,12p' "$WORK/p2-repair.log"; sed -n '1,14p' "$X2/PROTOCOL.md" 2>/dev/null
fi
P2_STATE="$( read_state_source "$X2" )"
if [ "$P2_STATE" = "$REPO_ROOT" ] && [ "$P2_STATE" != "$P2_STATE0" ]; then
  pass "P2g --protocol-source persisted in install-state (request.placeholders.PROTOCOL_SOURCE CHANGED from the install-time value)"
else
  fail "P2g install-state placeholder not updated (before='$P2_STATE0' after='$P2_STATE')"
fi

# ---------------------------------------------------------------------------
# P3 — RETROACTIVE: install with the PREVIOUS shipped release, upgrade with HEAD
# ---------------------------------------------------------------------------
# The previous release is DERIVED, never hardcoded: the newest non-rc v1.x tag
# whose generator does NOT yet carry the portable template — after the W1
# release the newest tag is portable itself and would select a fixture the
# recognizer correctly rejects (rail r2 P2). A checkout without such a tag (CI
# depth-1, or every tag portable) is a harness error, never a green.
PREV_TAG=""
for _t in $( git -C "$REPO_ROOT" tag --list 'v[0-9]*.[0-9]*.[0-9]*' --sort=-v:refname 2>/dev/null | grep -Ev -- '-' ); do
  if ! git -C "$REPO_ROOT" show "$_t:scripts/_framework_manifest_set.sh" 2>/dev/null | grep -q '_render_protocol_pointer_portable'; then
    PREV_TAG="$_t"; break
  fi
done
if [ -z "$PREV_TAG" ]; then
  echo "ERROR: P3 needs a pre-W1 release tag in this checkout (none found — shallow clone? fetch tags first)"; exit 2
fi
OLD="$WORK/old-release"; mkdir -p "$OLD"
if ! git -C "$REPO_ROOT" archive "$PREV_TAG" 2>/dev/null | ( cd "$OLD" && tar -xf - ); then
  echo "ERROR: P3 could not extract $PREV_TAG"; exit 2
fi
OLD_P="$( cd "$OLD" && pwd -P )"
L1="$WORK/legacy/app"; mkdir -p "$L1"; ( cd "$L1" && git init -q )
if ! run_install "$OLD" "$L1" > "$WORK/p3-install.log" 2>&1; then
  echo "ERROR: P3 install from $PREV_TAG failed"; sed -n '1,12p' "$WORK/p3-install.log"; exit 2
fi
cp "$L1/PROTOCOL.md" "$WORK/p3-legacy.md"
if has_abs_path "$WORK/p3-legacy.md" && [ "$( named_checkout "$WORK/p3-legacy.md" )" = "$OLD" ]; then
  pass "P3a $PREV_TAG install wrote the ABSOLUTE legacy pointer (the population the cure targets)"
else
  fail "P3a the previous release did not write the expected absolute body"; sed -n '1,14p' "$WORK/p3-legacy.md"
fi
if P3_SRC="$( _protocol_pointer_legacy_source "$WORK/p3-legacy.md" )" && [ "$P3_SRC" = "$OLD" ]; then
  pass "P3b the legacy recognizer accepts the REAL $PREV_TAG output byte-exact (source extracted)"
else
  fail "P3b recognizer rejects the real previous-release body (got '${P3_SRC:-}')"
fi
if ! run_upgrade "$REPO_ROOT" "$L1" "$WORK/p3-upgrade.log"; then
  echo "ERROR: P3 upgrade failed"; sed -n '1,12p' "$WORK/p3-upgrade.log"; exit 2
fi
if resolves_to "$L1/PROTOCOL.md" "$L1" "$OLD_P" && ! has_abs_path "$L1/PROTOCOL.md"; then
  pass "P3c after the upgrade the pointer is PORTABLE and still names the SAME checkout (the $PREV_TAG tree)"
else
  fail "P3c upgrade did not produce a portable pointer to the same checkout"; sed -n '1,14p' "$L1/PROTOCOL.md"
fi
if grep -q "CURED: PROTOCOL.md pointer was the pre-PLAN-183" "$WORK/p3-upgrade.log"; then
  pass "P3d the legacy CURED route is what ran"
else
  fail "P3d legacy cure route not reported"; grep -n "PROTOCOL" "$WORK/p3-upgrade.log" | head -5
fi
BKP3="$( ls -t "$L1"/.claude.bak/*/PROTOCOL.md 2>/dev/null | head -1 )"
if [ -n "$BKP3" ] && cmp -s "$BKP3" "$WORK/p3-legacy.md"; then
  pass "P3e byte-exact backup of the legacy original in .claude.bak"
else
  fail "P3e backup missing or mismatched (BKP=${BKP3:-<none>})"
fi

# ---------------------------------------------------------------------------
# P4 — WARNED preservation: adopter-edited pointer that names an absolute path
# ---------------------------------------------------------------------------
# Reuse the P3 target: make the (now portable) pointer adopter-owned by
# re-pointing it at an ABSOLUTE path with an extra note — content the framework
# must keep byte-identical, and must now WARN about.
printf '%s\n' "# Protocol reference" "" "The full CEO orchestration protocol lives at:" \
  "$REPO_ROOT/PROTOCOL.md" "" "Adopter note: pinned to the maintainer checkout on purpose." > "$L1/PROTOCOL.md"
cp "$L1/PROTOCOL.md" "$WORK/p4-edited.md"
if ! run_upgrade "$REPO_ROOT" "$L1" "$WORK/p4-upgrade.log"; then
  echo "ERROR: P4 upgrade failed"; sed -n '1,12p' "$WORK/p4-upgrade.log"; exit 2
fi
if cmp -s "$WORK/p4-edited.md" "$L1/PROTOCOL.md"; then
  pass "P4a adopter-edited absolute pointer survives byte-identical"
else
  fail "P4a adopter edit was modified (S238 class)"; diff "$WORK/p4-edited.md" "$L1/PROTOCOL.md" | head -8
fi
if grep -q "names an ABSOLUTE path" "$WORK/p4-upgrade.log" && grep -F -q -- '--protocol-source' "$WORK/p4-upgrade.log"; then
  pass "P4b the preservation is WARNED: absolute-path warning naming --protocol-source"
else
  fail "P4b no absolute-path warning on the preserved pointer"; grep -n "PROTOCOL" "$WORK/p4-upgrade.log" | head -5
fi
if grep -q "PRESERVED (root PROTOCOL.md is adopter-customised" "$WORK/p4-upgrade.log"; then
  pass "P4c the PRESERVE route is what ran (edited body, not misread as legacy)"
else
  fail "P4c expected the PRESERVED route"; grep -n "PROTOCOL" "$WORK/p4-upgrade.log" | head -5
fi

echo ""
if [ "$FAILURES" -gt 0 ]; then
  echo "portable pointer e2e: $FAILURES FAILED ($PASSES passed)"
  exit 1
fi
echo "portable pointer e2e: $PASSES/$PASSES pass (moved together / moved alone + named repair / retroactive cure from $PREV_TAG / warned preservation)"
exit 0
'''

# --------------------------------------------------------------------------
# (path, ancora EXATA, substituto, ocorrencias esperadas)
# A ordem e a ordem de aplicacao; cada ancora e contada ANTES de qualquer
# escrita. Uma entrada com ancora "" e count 0 CRIA o arquivo (que nao pode
# existir).
# --------------------------------------------------------------------------
EDITS: List[Tuple[str, str, str, int]] = [
    # ---------------- scripts/_framework_manifest_set.sh ------------------
    (
        MANIFEST,
        "#   _render_protocol_pointer SOURCE_DIR TARGET PROFILE STACK PROTOCOL_SOURCE\n"
        "#       Emit the COMPLETE healthy file content (\"# Protocol reference\" header\n"
        "#       included, trailing newline included). Inside-target checkouts get the\n"
        "#       relative form; everything else gets the PROTOCOL_SOURCE-resolved form\n"
        "#       (never the literal token — the caller passes the resolved value).\n",
        "#   _render_protocol_pointer SOURCE_DIR TARGET PROFILE STACK PROTOCOL_SOURCE\n"
        "#       Emit the COMPLETE healthy file content (\"# Protocol reference\" header\n"
        "#       included, trailing newline included). Inside-target checkouts get the\n"
        "#       relative form; everything else gets the PORTABLE form (PLAN-183 W1,\n"
        "#       A1): an ABSOLUTE PROTOCOL_SOURCE is rewritten RELATIVE to TARGET, so\n"
        "#       the pointer survives moving project and checkout TOGETHER (another\n"
        "#       $HOME, another username — the field breakage class). Both ends are\n"
        "#       taken PHYSICAL (cd && pwd -P) first — the kernel resolves `..` from\n"
        "#       the pointer's real directory, so a logically-normalized target\n"
        "#       behind a symlink must not feed the arithmetic; a value that cannot\n"
        "#       be made safe (relative or ~-prefixed values the adopter chose, an\n"
        "#       end that does not exist, lexically unclean paths) is kept VERBATIM.\n"
        "#       Never the literal token — the caller passes the resolved value. The\n"
        "#       body names the repair interface (--protocol-source) and carries no\n"
        "#       machine-specific path.\n"
        "#   _render_protocol_pointer_portable REL PROFILE STACK\n"
        "#       The W1 outside-target template: REL is what _render_protocol_pointer\n"
        "#       decided (relative path or verbatim value). ONE template for the\n"
        "#       healthy outside-target body, as _render_protocol_pointer_degraded is\n"
        "#       for the degraded one.\n"
        "#   _render_protocol_pointer_legacy PROTOCOL_SOURCE TARGET PROFILE STACK\n"
        "#       FROZEN pre-W1 healthy outside-target body: the degraded template with\n"
        "#       the token substituted everywhere — byte-for-byte what install.sh's\n"
        "#       placeholder pass wrote from v1.0.1 through v1.3.0 (the R2 identity of\n"
        "#       the render control). Recognition target of the retroactive cure; it\n"
        "#       must never change again.\n"
        "#   _protocol_pointer_legacy_source FILE\n"
        "#       rc=0 (and prints the checkout the file names) iff FILE is EXACTLY a\n"
        "#       legacy body: PROTOCOL_SOURCE from its own 4th line, TARGET/PROFILE/\n"
        "#       STACK from its own upgrade line, re-rendered through\n"
        "#       _render_protocol_pointer_legacy and byte-identical (streamed into\n"
        "#       cmp — no scratch file, so a TMPDIR inside the target is never written\n"
        "#       to). Checkout and TARGET may contain spaces (right-anchored split).\n"
        "#       Any parse failure, any edit => rc=1, nothing printed (fail toward\n"
        "#       PRESERVATION — the degraded recognizer's discipline). A token-literal\n"
        "#       body is NOT this class: that is `degraded`, and the caller checks it\n"
        "#       first.\n"
        "#   _rpp_relpath FROM TO\n"
        "#       Pure LEXICAL relative path from directory FROM to path TO. Both must\n"
        "#       be absolute and clean (no `.`/`..` components, no `//`); otherwise\n"
        "#       rc=1 and the caller keeps the value verbatim. No filesystem access.\n",
        1,
    ),
    (
        MANIFEST,
        "    *)\n"
        "      # The healthy outside-target form: the degraded template with the token\n"
        "      # substituted EVERYWHERE — exactly what install.sh's placeholder pass\n"
        "      # has always produced, so existing healthy pointers keep their digest.\n"
        "      # PLAN-169 W3.1: `sed s|…|VALUE|` cannot carry a NEWLINE in VALUE\n"
        "      # (unterminated s-command aborts under set -e — mid-upgrade). The\n"
        "      # upgrade path rejects such values upstream (charset allowlist);\n"
        "      # this guard covers every other caller: a value the substitution\n"
        "      # cannot represent leaves the token LITERAL (degraded body — the\n"
        "      # recognized cure target), never a corrupt render, never an abort.\n"
        "      case \"$_rpp_psource\" in\n"
        "        *\"$_RPP_NL\"*)\n"
        "          _render_protocol_pointer_degraded \"$_rpp_target\" \"$_rpp_profile\" \"$_rpp_stack\"\n"
        "          ;;\n"
        "        *)\n"
        "          _render_protocol_pointer_degraded \"$_rpp_target\" \"$_rpp_profile\" \"$_rpp_stack\" \\\n"
        "            | sed \"s|{{PROTOCOL_SOURCE}}|$( printf '%s' \"$_rpp_psource\" | sed 's/[|&\\\\]/\\\\&/g' )|g\"\n"
        "          ;;\n"
        "      esac\n"
        "      ;;\n"
        "  esac\n"
        "}\n",
        "    *)\n"
        "      # PLAN-183 W1 (A1): the PORTABLE outside-target form. An ABSOLUTE\n"
        "      # source is rewritten RELATIVE to the pointer's own directory (TARGET),\n"
        "      # so the pointer survives moving project and checkout TOGETHER; a value\n"
        "      # _rpp_relpath refuses (relative or ~-prefixed values the adopter chose,\n"
        "      # lexically unclean paths) is kept VERBATIM — the old, always-correct\n"
        "      # form. The body carries no machine-specific path and names the repair\n"
        "      # interface. Pre-W1 this branch was `degraded | sed`; that body is now\n"
        "      # the FROZEN _render_protocol_pointer_legacy, the retroactive cure's\n"
        "      # recognition target.\n"
        "      # PLAN-169 W3.1 guard kept: a NEWLINE in the value leaves the token\n"
        "      # LITERAL (degraded body — the recognized cure target), never a corrupt\n"
        "      # render, never an abort. The portable render uses printf, never sed,\n"
        "      # so a newline is the ONE value it cannot represent as a single line.\n"
        "      case \"$_rpp_psource\" in\n"
        "        *\"$_RPP_NL\"*)\n"
        "          _render_protocol_pointer_degraded \"$_rpp_target\" \"$_rpp_profile\" \"$_rpp_stack\"\n"
        "          ;;\n"
        "        *)\n"
        "          # rail r2 P1: the `..` components emitted here are resolved\n"
        "          # PHYSICALLY by the kernel from the pointer's REAL directory, while\n"
        "          # the callers normalize TARGET with a LOGICAL pwd — a target reached\n"
        "          # through a symlink (macOS /tmp -> /private/tmp is the everyday case)\n"
        "          # would get a relative path that is dead on arrival. Both ends are\n"
        "          # therefore taken PHYSICAL (cd && pwd -P) — only for an ABSOLUTE\n"
        "          # source (a relative or ~ value is the adopter's own and stays\n"
        "          # verbatim; `cd` would resolve it against the wrong directory). An\n"
        "          # end that does not exist cannot be made safe and keeps the source\n"
        "          # VERBATIM: absolute, always correct in place.\n"
        "          _rpp_from_p=\"\"; _rpp_to_p=\"\"\n"
        "          case \"$_rpp_psource\" in\n"
        "            /*)\n"
        "              _rpp_from_p=\"$( cd \"$_rpp_target\" 2>/dev/null && pwd -P )\" || _rpp_from_p=\"\"\n"
        "              _rpp_to_p=\"$( cd \"$_rpp_psource\" 2>/dev/null && pwd -P )\" || _rpp_to_p=\"\"\n"
        "              ;;\n"
        "          esac\n"
        "          if [ -n \"$_rpp_from_p\" ] && [ -n \"$_rpp_to_p\" ] \\\n"
        "             && _rpp_rel=\"$( _rpp_relpath \"$_rpp_from_p\" \"$_rpp_to_p\" )\"; then\n"
        "            _render_protocol_pointer_portable \"$_rpp_rel\" \"$_rpp_profile\" \"$_rpp_stack\"\n"
        "          else\n"
        "            _render_protocol_pointer_portable \"$_rpp_psource\" \"$_rpp_profile\" \"$_rpp_stack\"\n"
        "          fi\n"
        "          ;;\n"
        "      esac\n"
        "      ;;\n"
        "  esac\n"
        "}\n",
        1,
    ),
    (
        MANIFEST,
        "  _ppid_tmp=\"$( mktemp \"${TMPDIR:-/tmp}/ceo-ptr-recon.XXXXXX\" )\" || return 1\n"
        "  _render_protocol_pointer_degraded \"$_ppid_target\" \"$_ppid_profile\" \"$_ppid_stack\" > \"$_ppid_tmp\"\n"
        "  if cmp -s \"$_ppid_tmp\" \"$_ppid_file\"; then\n"
        "    rm -f \"$_ppid_tmp\" 2>/dev/null\n"
        "    return 0\n"
        "  fi\n"
        "  rm -f \"$_ppid_tmp\" 2>/dev/null\n"
        "  return 1\n"
        "}\n",
        "  _ppid_tmp=\"$( mktemp \"${TMPDIR:-/tmp}/ceo-ptr-recon.XXXXXX\" )\" || return 1\n"
        "  _render_protocol_pointer_degraded \"$_ppid_target\" \"$_ppid_profile\" \"$_ppid_stack\" > \"$_ppid_tmp\"\n"
        "  if cmp -s \"$_ppid_tmp\" \"$_ppid_file\"; then\n"
        "    rm -f \"$_ppid_tmp\" 2>/dev/null\n"
        "    return 0\n"
        "  fi\n"
        "  rm -f \"$_ppid_tmp\" 2>/dev/null\n"
        "  return 1\n"
        "}\n"
        "\n"
        "# =============================================================================\n"
        "# PLAN-183 W1 (A1) — the PORTABLE pointer: relativization decided INSIDE the\n"
        "# generator, a frozen legacy template, and the retroactive recognizer.\n"
        "#\n"
        "# THE FIELD BREAKAGE (A1). The outside-target pointer named the checkout by\n"
        "# ABSOLUTE path (install.sh substituted $SOURCE_DIR). Move the project to\n"
        "# another machine, another $HOME, another username — the common case of\n"
        "# \"clone my repo elsewhere\" — and the pointer is dead; worse, it carries the\n"
        "# maintainer's home directory into every adopter tree (the contamination\n"
        "# check was RIGHT to fire). The cure is the ONE property a pointer can carry:\n"
        "# the RELATION between the two trees. A relative path survives moving both\n"
        "# TOGETHER. Moving the target ALONE breaks any encoding, so the correct\n"
        "# answer there is a NAMED error leading to the repair (--protocol-source),\n"
        "# never a magic re-resolution (PLAN-183 W1, pair-rail r8+r9).\n"
        "# =============================================================================\n"
        "\n"
        "_rpp_relpath() {\n"
        "  # $1=FROM (absolute directory the result is relative to) $2=TO (absolute).\n"
        "  # Pure and lexical: no filesystem access, so the render stays a function of\n"
        "  # its inputs. A single trailing slash is tolerated; anything else that is\n"
        "  # not already clean (`.`/`..` components, `//`, a relative or ~ value, the\n"
        "  # root itself) is REFUSED — the caller then keeps the value verbatim, which\n"
        "  # is the old, always-correct form.\n"
        "  _rrp_from=\"${1%/}\"; _rrp_to=\"${2%/}\"\n"
        "  case \"$_rrp_from\" in /?*) : ;; *) return 1 ;; esac\n"
        "  case \"$_rrp_to\"   in /?*) : ;; *) return 1 ;; esac\n"
        "  case \"$_rrp_from/\" in *//*|*/./*|*/../*) return 1 ;; esac\n"
        "  case \"$_rrp_to/\"   in *//*|*/./*|*/../*) return 1 ;; esac\n"
        "  _rrp_common=\"$_rrp_from\"; _rrp_up=\"\"\n"
        "  # Walk FROM upward until it is TO itself or a proper ancestor of TO (the\n"
        "  # trailing slash keeps /a/app from matching /a/app2). An empty common means\n"
        "  # the root.\n"
        "  until [ -z \"$_rrp_common\" ] || [ \"$_rrp_to\" = \"$_rrp_common\" ] \\\n"
        "        || [ \"${_rrp_to#\"$_rrp_common\"/}\" != \"$_rrp_to\" ]; do\n"
        "    _rrp_common=\"${_rrp_common%/*}\"\n"
        "    _rrp_up=\"${_rrp_up}../\"\n"
        "  done\n"
        "  if [ \"$_rrp_to\" = \"$_rrp_common\" ]; then\n"
        "    _rrp_rest=\"\"\n"
        "  else\n"
        "    _rrp_rest=\"${_rrp_to#\"$_rrp_common\"/}\"\n"
        "  fi\n"
        "  if [ -z \"$_rrp_up\" ]; then\n"
        "    if [ -z \"$_rrp_rest\" ]; then printf '.'; else printf './%s' \"$_rrp_rest\"; fi\n"
        "  elif [ -z \"$_rrp_rest\" ]; then\n"
        "    printf '%s' \"${_rrp_up%/}\"\n"
        "  else\n"
        "    printf '%s%s' \"$_rrp_up\" \"$_rrp_rest\"\n"
        "  fi\n"
        "}\n"
        "\n"
        "_render_protocol_pointer_portable() {\n"
        "  # $1=REL $2=PROFILE $3=STACK. REL is relative to this file's directory when\n"
        "  # _render_protocol_pointer could make it so, else the adopter's own value.\n"
        "  # printf only — no sed, so no replacement-escaping class. ASCII only: this\n"
        "  # lands in an adopter file. The repair line is the ONE recipe that works\n"
        "  # when the relation broke: the framework re-delivers an ABSENT pointer, and\n"
        "  # --protocol-source is the same flag/env install.sh has always taken.\n"
        "  _rppp_rel=\"$1\"; _rppp_profile=\"$2\"; _rppp_stack=\"$3\"\n"
        "  printf '%s\\n' \\\n"
        "    \"# Protocol reference\" \\\n"
        "    \"\" \\\n"
        "    \"The full CEO orchestration protocol lives at:\" \\\n"
        "    \"${_rppp_rel}/PROTOCOL.md\" \\\n"
        "    \"\" \\\n"
        "    \"If that path stops resolving (this project or the framework checkout\" \\\n"
        "    \"moved), re-point it from this directory; the flag is the one install.sh\" \\\n"
        "    \"takes:\" \\\n"
        "    \"  rm PROTOCOL.md && <ceo-orchestration>/scripts/upgrade.sh . --protocol-source <ceo-orchestration>\" \\\n"
        "    \"\" \\\n"
        "    \"To pull updates:\" \\\n"
        "    \"  ( cd ${_rppp_rel} && git pull )\" \\\n"
        "    \"  ${_rppp_rel}/scripts/upgrade.sh . --profile $_rppp_profile --stack $_rppp_stack\"\n"
        "}\n"
        "\n"
        "_render_protocol_pointer_legacy() {\n"
        "  # $1=PROTOCOL_SOURCE(resolved) $2=TARGET $3=PROFILE $4=STACK — FROZEN.\n"
        "  # Byte-for-byte the pre-W1 outside-target body: the degraded template with\n"
        "  # the token substituted everywhere (install.sh's placeholder pass, and the\n"
        "  # pre-W1 `*)` branch of _render_protocol_pointer). It exists so the\n"
        "  # retroactive recognizer has an exact target; it must never be edited.\n"
        "  _rppl_psource=\"$1\"; _rppl_target=\"$2\"; _rppl_profile=\"$3\"; _rppl_stack=\"$4\"\n"
        "  case \"$_rppl_psource\" in\n"
        "    *\"$_RPP_NL\"*)\n"
        "      _render_protocol_pointer_degraded \"$_rppl_target\" \"$_rppl_profile\" \"$_rppl_stack\"\n"
        "      ;;\n"
        "    *)\n"
        "      _render_protocol_pointer_degraded \"$_rppl_target\" \"$_rppl_profile\" \"$_rppl_stack\" \\\n"
        "        | sed \"s|{{PROTOCOL_SOURCE}}|$( printf '%s' \"$_rppl_psource\" | sed 's/[|&\\\\]/\\\\&/g' )|g\"\n"
        "      ;;\n"
        "  esac\n"
        "}\n"
        "\n"
        "_protocol_pointer_legacy_source() {\n"
        "  # $1=FILE. rc=0 and prints the checkout the file names iff FILE is\n"
        "  # byte-identical to a legacy render whose values ALL come from the file\n"
        "  # itself: the checkout from its 4th line, TARGET/PROFILE/STACK from its\n"
        "  # upgrade line. Everything else (missing file, token still literal, any\n"
        "  # parse failure, any edit) => rc=1, nothing printed. Same reconstruction\n"
        "  # discipline as _protocol_pointer_is_degraded: substring matching would\n"
        "  # destroy an adopter file that merely LOOKS like a pointer; a static hash\n"
        "  # cannot match invocation-specific bodies.\n"
        "  _ppls_file=\"$1\"\n"
        "  [ -f \"$_ppls_file\" ] || return 1\n"
        "  if grep -F -q '{{PROTOCOL_SOURCE}}' \"$_ppls_file\" 2>/dev/null; then return 1; fi\n"
        "  _ppls_psource=\"$( sed -n '4p' \"$_ppls_file\" 2>/dev/null | sed -n 's|^\\(..*\\)/PROTOCOL\\.md$|\\1|p' )\"\n"
        "  [ -n \"$_ppls_psource\" ] || return 1\n"
        "  _ppls_line=\"$( grep -F -- \"$_ppls_psource/scripts/upgrade.sh \" \"$_ppls_file\" 2>/dev/null | head -1 )\"\n"
        "  [ -n \"$_ppls_line\" ] || return 1\n"
        "  # Right-anchored field extraction (rail r1 P2): the checkout is KNOWN from\n"
        "  # line 4, so the upgrade line splits as <checkout>/scripts/upgrade.sh\n"
        "  # <TARGET> --profile <P> --stack <S> with TARGET (and the checkout) free to\n"
        "  # contain spaces — the pre-W1 install wrote them verbatim. Parameter\n"
        "  # expansion only; the byte-exact cmp below is the real gate, so any\n"
        "  # mis-split is a mismatch, i.e. preservation.\n"
        "  _ppls_tail=\"${_ppls_line#*\"$_ppls_psource\"/scripts/upgrade.sh }\"\n"
        "  _ppls_stack=\"${_ppls_tail##* --stack }\"\n"
        "  [ \"$_ppls_stack\" != \"$_ppls_tail\" ] && [ -n \"$_ppls_stack\" ] || return 1\n"
        "  _ppls_rest=\"${_ppls_tail% --stack *}\"\n"
        "  _ppls_profile=\"${_ppls_rest##* --profile }\"\n"
        "  [ \"$_ppls_profile\" != \"$_ppls_rest\" ] && [ -n \"$_ppls_profile\" ] || return 1\n"
        "  _ppls_target=\"${_ppls_rest% --profile *}\"\n"
        "  [ -n \"$_ppls_target\" ] || return 1\n"
        "  # No scratch file (rail r1 P2: a TMPDIR under $TARGET would put it inside\n"
        "  # the adopter tree, --dry-run included): the reconstruction streams into\n"
        "  # cmp, the same way _refresh_protocol_pointer already verifies a sound\n"
        "  # pointer.\n"
        "  if _render_protocol_pointer_legacy \"$_ppls_psource\" \"$_ppls_target\" \"$_ppls_profile\" \"$_ppls_stack\" \\\n"
        "       | cmp -s - \"$_ppls_file\" 2>/dev/null; then\n"
        "    printf '%s' \"$_ppls_psource\"\n"
        "    return 0\n"
        "  fi\n"
        "  return 1\n"
        "}\n",
        1,
    ),
    (
        MANIFEST,
        "  elif [ \"$_ov_lcontent\" = \"degraded\" ]; then\n"
        "    # PLAN-168 W2 (AC-6b, Owner decision D2): a DEGRADED body — byte-exact\n",
        "  elif [ \"$_ov_lcontent\" = \"degraded\" ] || [ \"$_ov_lcontent\" = \"legacy_absolute\" ]; then\n"
        "    # PLAN-183 W1 (A1): `legacy_absolute` — the pre-W1 HEALTHY body (token\n"
        "    # substituted, absolute TARGET in its upgrade line), reconstructed\n"
        "    # byte-exact from the file's own values by _protocol_pointer_legacy_source\n"
        "    # — is an older generator's output, owned on the same content-proven\n"
        "    # doctrine as `degraded` below, and routed to the same REFRESH cure\n"
        "    # (portable re-render of the SAME checkout, backup kept). R-04c.\n"
        "    # PLAN-168 W2 (AC-6b, Owner decision D2): a DEGRADED body — byte-exact\n",
        1,
    ),
    # ---------------- scripts/upgrade.sh ----------------------------------
    (
        UPGRADE,
        "STACK_EXPLICIT=0        # PLAN-153 B2: explicit --stack always beats a replayed value\n"
        "SKIP_GLOBS=()\n",
        "STACK_EXPLICIT=0        # PLAN-153 B2: explicit --stack always beats a replayed value\n"
        "SKIP_GLOBS=()\n"
        "# PLAN-183 W1 (A1): the pointer's repair interface — the SAME pair install.sh\n"
        "# accepts (CLI beats env). Persisted into request.placeholders.PROTOCOL_SOURCE\n"
        "# only when explicit AND accepted by the charset allowlist (see\n"
        "# _refresh_protocol_pointer); never the inferred/recorded value.\n"
        "PROTOCOL_SOURCE_FLAG=\"${CEO_PROTOCOL_SOURCE:-}\"\n"
        "_PTR_SOURCE_PERSIST=\"\"\n",
        1,
    ),
    (
        UPGRADE,
        "    --pin)\n"
        "      PIN_REF=\"${2:-}\"\n"
        "      shift 2\n"
        "      ;;\n",
        "    --protocol-source)\n"
        "      # PLAN-183 W1 (A1): same flag as install.sh; the repair route for a\n"
        "      # pointer whose relation broke (project or checkout moved ALONE).\n"
        "      PROTOCOL_SOURCE_FLAG=\"${2:-}\"\n"
        "      shift 2\n"
        "      ;;\n"
        "    --pin)\n"
        "      PIN_REF=\"${2:-}\"\n"
        "      shift 2\n"
        "      ;;\n",
        1,
    ),
    (
        UPGRADE,
        "  --pin <tag>           Pin source to specific tag/SHA (SPEC v1 install-cli.md).\n",
        "  --protocol-source <path>\n"
        "                        PLAN-183 W1: the checkout the root PROTOCOL.md pointer\n"
        "                        names (same flag/env as install.sh: CEO_PROTOCOL_SOURCE).\n"
        "                        Rendered RELATIVE to the target when absolute, so the\n"
        "                        pointer survives moving project and checkout together;\n"
        "                        recorded in .claude/.install-state.json for later\n"
        "                        upgrades. The repair route when the pointer stopped\n"
        "                        resolving (one of the two moved alone):\n"
        "                          rm PROTOCOL.md && <ceo>/scripts/upgrade.sh . --protocol-source <ceo>\n"
        "  --pin <tag>           Pin source to specific tag/SHA (SPEC v1 install-cli.md).\n",
        1,
    ),
    (
        UPGRADE,
        "_refresh_protocol_pointer() {\n"
        "  local pointer=\"$TARGET/PROTOCOL.md\"\n",
        "# PLAN-183 W1 (A1) — POSITIVE charset allowlist for a pointer source value: the\n"
        "# bash twin of the install-state filter inside _refresh_protocol_pointer\n"
        "# (PLAN-169 W3.1 R-SEC8). Printable path characters only, no braces (the\n"
        "# token), no newline or control chars, at most 512 bytes. rc=0 accept.\n"
        "_ptr_source_value_ok() {\n"
        "  _psvo_v=\"$1\"\n"
        "  _psvo_nl='\n"
        "'\n"
        "  case \"$_psvo_v\" in\n"
        "    ''|*'{{'*|*\"$_psvo_nl\"*|*[!A-Za-z0-9._/~' '-]*) return 1 ;;\n"
        "  esac\n"
        "  [ \"${#_psvo_v}\" -le 512 ]\n"
        "}\n"
        "\n"
        "# PLAN-183 W1 (A1) — ADVISORY portability check on a pointer this run leaves\n"
        "# in place (preserved, carried forward, or just written). Read-only; never\n"
        "# changes a verdict. Two NAMED conditions, each with the repair interface:\n"
        "#   (a) the body names an ABSOLUTE path => it will not survive moving this\n"
        "#       project to another home/user (the field breakage class, A1) —\n"
        "#       \"preservation is WARNED, never silent\";\n"
        "#   (b) the checkout the body names does not resolve from the target => the\n"
        "#       project or the checkout moved ALONE. The framework cannot know where\n"
        "#       the checkout went, so this is a NAMED error, never a magic\n"
        "#       re-resolution (PLAN-183 W1, pair-rail r9 #1).\n"
        "# ~-prefixed values are the adopter's shell convention: not probed (no false\n"
        "# positive, no expansion of untrusted text). The named value is never echoed.\n"
        "_ptr_warn_portability() {\n"
        "  _pwp_file=\"$1\"\n"
        "  # A symlinked pointer is adopter-owned and never read THROUGH (PLAN-185\n"
        "  # posture: no follow, even for a read); anything not a regular file has\n"
        "  # nothing to warn about.\n"
        "  if [ -L \"$_pwp_file\" ] || [ ! -f \"$_pwp_file\" ]; then return 0; fi\n"
        "  _pwp_fix=\"rm PROTOCOL.md && <ceo-orchestration>/scripts/upgrade.sh . --protocol-source <ceo-orchestration>\"\n"
        "  if grep -Eq '(^|[[:space:]])/[^[:space:]]' \"$_pwp_file\" 2>/dev/null; then\n"
        "    echo \"    WARNING: PROTOCOL.md pointer names an ABSOLUTE path — it will not survive moving this project to another home or user. Re-point it from $TARGET with: $_pwp_fix\" >&2\n"
        "  fi\n"
        "  _pwp_named=\"$( sed -n 's|^\\(..*\\)/PROTOCOL\\.md$|\\1|p' \"$_pwp_file\" 2>/dev/null | sed -n '1p' )\"\n"
        "  case \"$_pwp_named\" in\n"
        "    ''|'~'*|*'{{'*) return 0 ;;\n"
        "    /*) _pwp_probe=\"$_pwp_named/PROTOCOL.md\" ;;\n"
        "    *)  _pwp_probe=\"$TARGET/$_pwp_named/PROTOCOL.md\" ;;\n"
        "  esac\n"
        "  if [ ! -f \"$_pwp_probe\" ]; then\n"
        "    echo \"    WARNING: PROTOCOL.md pointer names a checkout that does not resolve from $TARGET (this project or the framework checkout moved alone). Re-point it with: $_pwp_fix\" >&2\n"
        "  fi\n"
        "  return 0\n"
        "}\n"
        "\n"
        "_refresh_protocol_pointer() {\n"
        "  local pointer=\"$TARGET/PROTOCOL.md\"\n",
        1,
    ),
    (
        UPGRADE,
        "  local _ptr_psource=\"\"\n"
        "  if [ -f \"$_INSTALL_STATE_FILE\" ] && command -v python3 >/dev/null 2>&1; then\n",
        "  local _ptr_psource=\"\" _ptr_leg=\"\" _ptr_leg_ok=\"\" _ptr_explicit_ok=\"\"\n"
        "  # PLAN-183 W1 (A1), precedence 0: an EXPLICIT --protocol-source /\n"
        "  # CEO_PROTOCOL_SOURCE — the repair interface, the same pair install.sh has\n"
        "  # always taken. Same POSITIVE charset allowlist as the recorded value; a\n"
        "  # rejected value is LOUD and falls through to the recorded precedence.\n"
        "  if [ -n \"${PROTOCOL_SOURCE_FLAG:-}\" ]; then\n"
        "    if _ptr_source_value_ok \"$PROTOCOL_SOURCE_FLAG\"; then\n"
        "      _ptr_psource=\"$PROTOCOL_SOURCE_FLAG\"\n"
        "      _PTR_SOURCE_PERSIST=\"$PROTOCOL_SOURCE_FLAG\"\n"
        "      _ptr_explicit_ok=1\n"
        "    else\n"
        "      echo \"    WARNING: --protocol-source / CEO_PROTOCOL_SOURCE value REJECTED by the charset allowlist (control chars, newline, braces, non-ASCII or >512 bytes) — ignored; the recorded precedence applies.\" >&2\n"
        "    fi\n"
        "  fi\n"
        "  # W1 retroactive cure — recognize a LEGACY body ONCE (the OBSERVE phase\n"
        "  # below reuses the result): the pre-W1 healthy form, byte-exact from its\n"
        "  # own values. A symlinked pointer is never read through (PLAN-185 posture).\n"
        "  if [ ! -L \"$pointer\" ] && [ -f \"$pointer\" ] \\\n"
        "     && _ptr_leg=\"$( _protocol_pointer_legacy_source \"$pointer\" 2>/dev/null )\"; then\n"
        "    if _ptr_source_value_ok \"$_ptr_leg\"; then _ptr_leg_ok=1; fi\n"
        "  else\n"
        "    _ptr_leg=\"\"\n"
        "  fi\n"
        "  # Precedence 0.5: the legacy body keeps the checkout it NAMES; only the\n"
        "  # SHAPE migrates. Re-rendering it from the recorded value instead would\n"
        "  # turn a shape migration into a silent re-point (the S238 class). A named\n"
        "  # value the allowlist cannot take is NOT cured from another value either\n"
        "  # (rail r1 P1): without an explicit --protocol-source such a body is left\n"
        "  # `edited` — preserved and WARNED — never re-pointed to $SOURCE_DIR.\n"
        "  if [ -z \"$_ptr_psource\" ] && [ -n \"$_ptr_leg_ok\" ]; then\n"
        "    _ptr_psource=\"$_ptr_leg\"\n"
        "  fi\n"
        "  if [ -z \"$_ptr_psource\" ] && [ -f \"$_INSTALL_STATE_FILE\" ] && command -v python3 >/dev/null 2>&1; then\n",
        1,
    ),
    (
        UPGRADE,
        "    _lc=\"degraded\"\n"
        "  elif [ -n \"$_REFRESH_PROTOCOL_CANON_HASH\" ] \\\n",
        "    _lc=\"degraded\"\n"
        "  elif [ -n \"$_ptr_leg\" ] && { [ -n \"$_ptr_explicit_ok\" ] || [ -n \"$_ptr_leg_ok\" ]; }; then\n"
        "    # PLAN-183 W1 (A1, retroactive): the pre-W1 HEALTHY body — token\n"
        "    # substituted, absolute TARGET in its upgrade line — reconstructed\n"
        "    # byte-exact from the file's own values (above). An older generator's\n"
        "    # output, not adopter content: owned, routed to the REFRESH cure\n"
        "    # (portable re-render of the checkout that WILL be rendered: the\n"
        "    # file's own, or the explicitly asserted one — never $SOURCE_DIR by\n"
        "    # fallback, rail r1 P1). Any edit, or a named value the render cannot\n"
        "    # take => `edited` below, i.e. preserved — and WARNED (absolute path).\n"
        "    _lc=\"legacy_absolute\"\n"
        "  elif [ -n \"$_REFRESH_PROTOCOL_CANON_HASH\" ] \\\n",
        1,
    ),
    (
        UPGRADE,
        "        echo \"    PRESERVED (root PROTOCOL.md is adopter-customised — pointer NOT refreshed; backup in $BAK_DIR/PROTOCOL.md)\" >&2\n"
        "      else\n"
        "        echo \"    SKIP: PROTOCOL.md pointer (ownership carried forward)\"\n"
        "      fi\n"
        "      return 0\n"
        "      ;;\n",
        "        echo \"    PRESERVED (root PROTOCOL.md is adopter-customised — pointer NOT refreshed; backup in $BAK_DIR/PROTOCOL.md)\" >&2\n"
        "      else\n"
        "        echo \"    SKIP: PROTOCOL.md pointer (ownership carried forward)\"\n"
        "      fi\n"
        "      # PLAN-183 W1 (A1): preservation is WARNED, never silent.\n"
        "      _ptr_warn_portability \"$pointer\"\n"
        "      return 0\n"
        "      ;;\n",
        1,
    ),
    (
        UPGRADE,
        "      if [ \"$_lc\" = \"degraded\" ]; then\n"
        "        echo \"    CURED: PROTOCOL.md pointer was framework-degraded ({{PROTOCOL_SOURCE}} left literal by an old upgrade) — refreshed; original in $BAK_DIR/PROTOCOL.md\"\n"
        "      else\n"
        "        echo \"    REFRESHED: PROTOCOL.md pointer\"\n"
        "      fi\n"
        "      return 0\n",
        "      if [ \"$_lc\" = \"degraded\" ]; then\n"
        "        echo \"    CURED: PROTOCOL.md pointer was framework-degraded ({{PROTOCOL_SOURCE}} left literal by an old upgrade) — refreshed; original in $BAK_DIR/PROTOCOL.md\"\n"
        "      elif [ \"$_lc\" = \"legacy_absolute\" ]; then\n"
        "        echo \"    CURED: PROTOCOL.md pointer was the pre-PLAN-183 absolute form — re-rendered in the portable form (relative to this project); original in $BAK_DIR/PROTOCOL.md\"\n"
        "      else\n"
        "        echo \"    REFRESHED: PROTOCOL.md pointer\"\n"
        "      fi\n"
        "      _ptr_warn_portability \"$pointer\"\n"
        "      return 0\n",
        1,
    ),
    (
        UPGRADE,
        "    \"ceremony_persist\" \"$_CEREMONY_PERSIST\"\n",
        "    \"ceremony_persist\" \"$_CEREMONY_PERSIST\"\n"
        "    \"protocol_source\" \"${_PTR_SOURCE_PERSIST:-}\"\n",
        1,
    ),
    (
        UPGRADE,
        "req[\"profile\"] = vals.get(\"profile\", \"\")\n"
        "req[\"stack\"] = vals.get(\"stack\", \"\")\n",
        "req[\"profile\"] = vals.get(\"profile\", \"\")\n"
        "req[\"stack\"] = vals.get(\"stack\", \"\")\n"
        "# PLAN-183 W1 (A1): an EXPLICIT, allowlist-accepted --protocol-source /\n"
        "# CEO_PROTOCOL_SOURCE is recorded where install.sh records it, so the next\n"
        "# upgrade renders the pointer from it (precedence 1). Empty => untouched.\n"
        "_ps = vals.get(\"protocol_source\", \"\")\n"
        "if _ps:\n"
        "    _ph = req.get(\"placeholders\")\n"
        "    if not isinstance(_ph, dict):\n"
        "        _ph = {}\n"
        "    _ph[\"PROTOCOL_SOURCE\"] = _ps\n"
        "    req[\"placeholders\"] = _ph\n",
        1,
    ),
    # ---------------- scripts/install.sh ----------------------------------
    (
        INSTALL,
        "  # Relative-path heuristic (unchanged): if $SOURCE_DIR starts with $TARGET,\n"
        "  # the framework was copied INTO the target — relative pointer. In ALL other\n"
        "  # cases the body is written with the user-editable {{PROTOCOL_SOURCE}}\n"
        "  # marker and the placeholder substitution pass below resolves it.\n",
        "  # PLAN-183 W1 (A1): ONE call, the generator decides inside — a checkout\n"
        "  # INSIDE the target renders relative to $SOURCE_DIR; any other checkout\n"
        "  # renders the resolved PROTOCOL_SOURCE (CLI > env > $SOURCE_DIR) RELATIVE\n"
        "  # to $TARGET when it can, verbatim when it cannot. The placeholder pass\n"
        "  # below finds no token left in this file. These bytes are exactly what\n"
        "  # upgrade.sh renders for the same inputs (INV-4) — the pre-W1 identity\n"
        "  # `degraded | substitute == healthy` that let a later pass do the work is\n"
        "  # gone on purpose, so the substitution must not happen in a later pass.\n",
        1,
    ),
    (
        INSTALL,
        "  case \"$SOURCE_DIR\" in\n"
        "    \"$TARGET\"/*)\n"
        "      _render_protocol_pointer \"$SOURCE_DIR\" \"$TARGET\" \"$PROFILE\" \"$STACK\" \"\" > \"$TARGET/PROTOCOL.md\"\n"
        "      ;;\n"
        "    *)\n"
        "      _render_protocol_pointer_degraded \"$TARGET\" \"$PROFILE\" \"$STACK\" > \"$TARGET/PROTOCOL.md\"\n"
        "      ;;\n"
        "  esac\n"
        "  echo \"    CREATED: PROTOCOL.md (pointer)\"\n",
        "  _render_protocol_pointer \"$SOURCE_DIR\" \"$TARGET\" \"$PROFILE\" \"$STACK\" \"$PH_PROTOCOL_SOURCE\" > \"$TARGET/PROTOCOL.md\"\n"
        "  echo \"    CREATED: PROTOCOL.md (pointer)\"\n",
        1,
    ),
    # ---------------- scripts/tests/test-protocol-pointer-render.sh -------
    (
        RENDER_T,
        "#   R2  degraded render | substitute-token == healthy render (one template)\n",
        "#   R2  degraded render | substitute-token == LEGACY render (one FROZEN pre-W1\n"
        "#       template — the retroactive cure's recognition target, PLAN-183 W1);\n"
        "#       R2b the healthy render DIFFERS from it (portable form in effect)\n",
        1,
    ),
    (
        RENDER_T,
        "#   R9  psource carrying a NEWLINE => degraded render (token literal), the\n"
        "#       generator never aborts and never leaks the value (PLAN-169 W3.1)\n",
        "#   R9  psource carrying a NEWLINE => degraded render (token literal), the\n"
        "#       generator never aborts and never leaks the value (PLAN-169 W3.1)\n"
        "#   R10 outside-target healthy render is PORTABLE (PLAN-183 W1): relative\n"
        "#       path that RESOLVES to this checkout, no absolute path anywhere, names\n"
        "#       --protocol-source, no token\n"
        "#   R11 legacy recognizer: exact pre-W1 body => rc=0 + its source; healthy\n"
        "#       portable body => rc=1; degraded body => rc=1 (classes disjoint);\n"
        "#       checkout/target WITH SPACES => still recognized (no single-token rule)\n"
        "#   R12 legacy recognizer: 1-char adopter edit => rc=1 (preserved)\n"
        "#   R13 _rpp_relpath: sibling / nested / unrelated / trailing slash / same\n"
        "#       dir, and five inputs it must REFUSE (relative, ~, `..`, `//`, empty)\n"
        "#   R15 target reached through a depth-changing SYMLINK => the render still\n"
        "#       resolves from the physical directory (rail r2 P1)\n",
        1,
    ),
    (
        RENDER_T,
        "for fn in _render_protocol_pointer _render_protocol_pointer_degraded _protocol_pointer_is_degraded; do\n",
        "for fn in _render_protocol_pointer _render_protocol_pointer_degraded _protocol_pointer_is_degraded \\\n"
        "          _render_protocol_pointer_portable _render_protocol_pointer_legacy _protocol_pointer_legacy_source _rpp_relpath; do\n",
        1,
    ),
    (
        RENDER_T,
        "say() { echo \"$1\"; }\n",
        "PASSES=0\n"
        "say() { echo \"$1\"; PASSES=$((PASSES+1)); }\n",
        1,
    ),
    (
        RENDER_T,
        "# --- R2: one template — degraded | substitution == healthy --------------------\n"
        "_render_protocol_pointer_degraded \"$U\" core generic \\\n"
        "  | sed \"s|{{PROTOCOL_SOURCE}}|$( printf '%s' \"$REPO_ROOT\" | sed 's/[|&\\\\]/\\\\&/g' )|g\" \\\n"
        "  > \"$WORK/deg-subst.txt\"\n"
        "if diff -q \"$WORK/deg-subst.txt\" \"$WORK/render.txt\" >/dev/null 2>&1; then\n"
        "  say \"PASS  R2 degraded+substitute == healthy (single template)\"\n"
        "else\n"
        "  fail \"R2 template split\"; diff \"$WORK/deg-subst.txt\" \"$WORK/render.txt\" | head -5\n"
        "fi\n",
        "# --- R2: one FROZEN legacy template — degraded | substitution == legacy -------\n"
        "# PLAN-183 W1 broke the pre-W1 identity `degraded | sed == healthy` ON PURPOSE\n"
        "# (the healthy outside-target body is now portable). The identity survives as\n"
        "# the DEFINITION of the legacy body — the retroactive cure's recognition\n"
        "# target — so this control now pins THAT: the frozen generator must equal the\n"
        "# pre-W1 install output byte for byte, forever. R2b pins the other half: the\n"
        "# healthy render must no longer BE the legacy body.\n"
        "_render_protocol_pointer_degraded \"$U\" core generic \\\n"
        "  | sed \"s|{{PROTOCOL_SOURCE}}|$( printf '%s' \"$REPO_ROOT\" | sed 's/[|&\\\\]/\\\\&/g' )|g\" \\\n"
        "  > \"$WORK/deg-subst.txt\"\n"
        "_render_protocol_pointer_legacy \"$REPO_ROOT\" \"$U\" core generic > \"$WORK/legacy.txt\"\n"
        "if diff -q \"$WORK/deg-subst.txt\" \"$WORK/legacy.txt\" >/dev/null 2>&1; then\n"
        "  say \"PASS  R2 degraded+substitute == legacy render (frozen pre-W1 template)\"\n"
        "else\n"
        "  fail \"R2 legacy template drifted from degraded|sed\"; diff \"$WORK/deg-subst.txt\" \"$WORK/legacy.txt\" | head -5\n"
        "fi\n"
        "if diff -q \"$WORK/legacy.txt\" \"$WORK/render.txt\" >/dev/null 2>&1; then\n"
        "  fail \"R2b healthy render still equals the legacy (absolute) body — W1 relativization absent\"\n"
        "else\n"
        "  say \"PASS  R2b healthy render differs from the legacy body (portable form in effect)\"\n"
        "fi\n",
        1,
    ),
    (
        RENDER_T,
        "echo \"\"\n"
        "if [[ \"$FAILURES\" -gt 0 ]]; then\n"
        "  echo \"protocol-pointer render control: $FAILURES FAILED\"\n"
        "  exit 1\n"
        "fi\n"
        "echo \"protocol-pointer render control: 9/9 pass\"\n",
        "# --- R10: outside-target healthy render is PORTABLE (PLAN-183 W1, A1) --------\n"
        "# The install of R1 ran from $REPO_ROOT (outside $U): the render must name\n"
        "# the checkout RELATIVE to the target, resolve to the real PROTOCOL.md, carry\n"
        "# no absolute path anywhere, name the repair interface, and hold no token.\n"
        "R10_NAMED=\"$( sed -n 's|^\\(..*\\)/PROTOCOL\\.md$|\\1|p' \"$WORK/render.txt\" | sed -n '1p' )\"\n"
        "R10_REL=1\n"
        "case \"$R10_NAMED\" in /*|'') R10_REL=0 ;; esac\n"
        "if [[ \"$R10_REL\" -eq 1 ]] && [[ -f \"$U/$R10_NAMED/PROTOCOL.md\" ]] \\\n"
        "   && [[ \"$( cd \"$U/$R10_NAMED\" && pwd -P )\" == \"$( cd \"$REPO_ROOT\" && pwd -P )\" ]] \\\n"
        "   && ! grep -Eq '(^|[[:space:]])/[^[:space:]]' \"$WORK/render.txt\" \\\n"
        "   && grep -F -q -- '--protocol-source' \"$WORK/render.txt\" \\\n"
        "   && ! grep -q '{{PROTOCOL_SOURCE}}' \"$WORK/render.txt\"; then\n"
        "  say \"PASS  R10 outside-target render is relative, resolves, absolute-free, names --protocol-source\"\n"
        "else\n"
        "  fail \"R10 outside-target render not portable (named='$R10_NAMED')\"; sed -n '1,14p' \"$WORK/render.txt\"\n"
        "fi\n"
        "\n"
        "# --- R11: legacy recognizer — exact pre-W1 body, healthy body, degraded body --\n"
        "if R11_SRC=\"$( _protocol_pointer_legacy_source \"$WORK/legacy.txt\" )\" && [[ \"$R11_SRC\" == \"$REPO_ROOT\" ]]; then\n"
        "  say \"PASS  R11a exact legacy body recognized, source extracted verbatim\"\n"
        "else\n"
        "  fail \"R11a exact legacy body NOT recognized (rc or source mismatch: '${R11_SRC:-}')\"\n"
        "fi\n"
        "if _protocol_pointer_legacy_source \"$WORK/render.txt\" >/dev/null; then\n"
        "  fail \"R11b healthy portable body misclassified as legacy (would be re-rendered forever)\"\n"
        "else\n"
        "  say \"PASS  R11b healthy portable body is not legacy\"\n"
        "fi\n"
        "if _protocol_pointer_legacy_source \"$WORK/degraded.md\" >/dev/null; then\n"
        "  fail \"R11c degraded body misclassified as legacy (two recognizers claiming one file)\"\n"
        "else\n"
        "  say \"PASS  R11c degraded body is not legacy (classes disjoint)\"\n"
        "fi\n"
        "# rail r1 P2: the pre-W1 install wrote checkout and target VERBATIM, spaces\n"
        "# included — such a body is framework output and must be recognized (the\n"
        "# degraded recognizer's single-token residual, R7, does not carry over).\n"
        "_render_protocol_pointer_legacy \"/tmp/my checkout\" \"/tmp/my app\" core generic > \"$WORK/legacy-spaced.txt\"\n"
        "if R11_SP=\"$( _protocol_pointer_legacy_source \"$WORK/legacy-spaced.txt\" )\" && [[ \"$R11_SP\" == \"/tmp/my checkout\" ]]; then\n"
        "  say \"PASS  R11d legacy body with SPACES in checkout and target recognized, source verbatim\"\n"
        "else\n"
        "  fail \"R11d spaced legacy body not recognized (got '${R11_SP:-}')\"\n"
        "fi\n"
        "\n"
        "# --- R12: legacy body + one adopter edit => preserved ------------------------\n"
        "sed 's/git pull/git fetch/' \"$WORK/legacy.txt\" > \"$WORK/legacy-edited.txt\"\n"
        "if _protocol_pointer_legacy_source \"$WORK/legacy-edited.txt\" >/dev/null; then\n"
        "  fail \"R12 edited legacy body still classified curable (DATA LOSS route)\"\n"
        "else\n"
        "  say \"PASS  R12 edited legacy body preserved\"\n"
        "fi\n"
        "\n"
        "# --- R13: _rpp_relpath — pure, lexical, refuses what it cannot take ---------\n"
        "R13_FAIL=0\n"
        "r13() { # $1=from $2=to $3=expected (\"\" => must be refused)\n"
        "  local got rc=0\n"
        "  got=\"$( _rpp_relpath \"$1\" \"$2\" )\" || rc=$?\n"
        "  if [[ -z \"$3\" ]]; then\n"
        "    [[ $rc -ne 0 ]] || { echo \"  r13: expected refusal for '$1' -> '$2', got '$got'\"; R13_FAIL=1; }\n"
        "  else\n"
        "    [[ $rc -eq 0 && \"$got\" == \"$3\" ]] || { echo \"  r13: '$1' -> '$2': expected '$3', got '$got' (rc=$rc)\"; R13_FAIL=1; }\n"
        "  fi\n"
        "}\n"
        "r13 /home/a/src/app /home/a/src/ceo            ../ceo\n"
        "r13 /home/a/src/app /home/a/src/app/vendor/ceo ./vendor/ceo\n"
        "r13 /home/a/src/app /home/a/src/app2           ../app2\n"
        "r13 /home/a/src/app /opt/ceo                   ../../../../opt/ceo\n"
        "r13 /home/a/src/app /home/a/src/ceo/           ../ceo\n"
        "r13 /home/a/src/app /home/a/src/app            .\n"
        "r13 /home/a/src/app ../ceo                     \"\"\n"
        "# shellcheck disable=SC2088  # the LITERAL tilde is the input under test\n"
        "r13 /home/a/src/app '~/src/ceo'                \"\"\n"
        "r13 /home/a/src/app /home/a/src/../src/ceo     \"\"\n"
        "r13 /home/a/src/app /home/a//src/ceo           \"\"\n"
        "r13 /home/a/src/app \"\"                         \"\"\n"
        "if [[ \"$R13_FAIL\" -eq 0 ]]; then\n"
        "  say \"PASS  R13 _rpp_relpath sibling/nested/unrelated/trailing-slash/same + 5 refusals\"\n"
        "else\n"
        "  fail \"R13 _rpp_relpath\"\n"
        "fi\n"
        "\n"
        "# --- R15: target reached THROUGH a depth-changing symlink (rail r2 P1) --------\n"
        "# `s -> deep/root`: the logical target $SYM/s/app is physically\n"
        "# $SYM/deep/root/app. A lexical relpath from the LOGICAL target emits\n"
        "# ../../deep/root/ceo, which the kernel resolves from the PHYSICAL directory\n"
        "# to deep/deep/root/ceo — dead on arrival. The render must resolve from where\n"
        "# the file really lives (measured RED on the pre-fix tree).\n"
        "# The base is taken PHYSICAL and clean on purpose (macOS TMPDIR ends in `/`,\n"
        "# so \"$WORK\" carries a `//` that the lexical hygiene would refuse — and the\n"
        "# verbatim fallback would make this control pass for the wrong reason). The\n"
        "# symlink is then the ONLY logical component in the target path.\n"
        "SYM=\"$( cd \"$WORK\" && pwd -P )/sym\"; mkdir -p \"$SYM/deep/root/app\" \"$SYM/deep/root/ceo\"\n"
        "printf 'x\\n' > \"$SYM/deep/root/ceo/PROTOCOL.md\"\n"
        "ln -s \"$SYM/deep/root\" \"$SYM/s\"\n"
        "_render_protocol_pointer \"$SYM/deep/root/ceo\" \"$SYM/s/app\" core generic \"$SYM/deep/root/ceo\" > \"$WORK/sym.txt\"\n"
        "R15_NAMED=\"$( sed -n 's|^\\(..*\\)/PROTOCOL\\.md$|\\1|p' \"$WORK/sym.txt\" | sed -n '1p' )\"\n"
        "if [[ -n \"$R15_NAMED\" ]] && [[ -f \"$SYM/s/app/$R15_NAMED/PROTOCOL.md\" ]] \\\n"
        "   && [[ \"$( cd \"$SYM/s/app/$R15_NAMED\" && pwd -P )\" == \"$( cd \"$SYM/deep/root/ceo\" && pwd -P )\" ]]; then\n"
        "  say \"PASS  R15 target behind a depth-changing symlink still resolves (named='$R15_NAMED')\"\n"
        "else\n"
        "  fail \"R15 symlinked target => dead relative path (named='$R15_NAMED')\"\n"
        "fi\n"
        "\n"
        "echo \"\"\n"
        "if [[ \"$FAILURES\" -gt 0 ]]; then\n"
        "  echo \"protocol-pointer render control: $FAILURES FAILED ($PASSES passed)\"\n"
        "  exit 1\n"
        "fi\n"
        "echo \"protocol-pointer render control: $PASSES/$PASSES pass\"\n",
        1,
    ),
    # ---------------- scripts/tests/test-protocol-pointer-inv4.sh ---------
    (
        INV4_T,
        "# Byte identity alone is VACUOUS (codex rail r1 P1: a shared generator based\n"
        "# on the broken template would make both sides identical AND wrong), so every\n"
        "# leg also asserts CONTENT: the {{PROTOCOL_SOURCE}} token is ABSENT and the\n"
        "# resolved source path is PRESENT.\n",
        "# Byte identity alone is VACUOUS (codex rail r1 P1: a shared generator based\n"
        "# on the broken template would make both sides identical AND wrong), so every\n"
        "# leg also asserts CONTENT: the {{PROTOCOL_SOURCE}} token is ABSENT and the\n"
        "# checkout the pointer names RESOLVES (from the target's directory) to THIS\n"
        "# checkout's PROTOCOL.md, by a RELATIVE path. PLAN-183 W1 made the pointer\n"
        "# PORTABLE, so the pre-W1 assertion \"the absolute source path is present\"\n"
        "# would now certify the regression it was written against — resolution is\n"
        "# the invariant, absoluteness is the defect.\n",
        1,
    ),
    (
        INV4_T,
        "#   L4  adopter-edited -> upgrade  : PRESERVED byte-identical (S238 guard —\n"
        "#                                    the cure must never widen into clobber)\n",
        "#   L4  adopter-edited -> upgrade  : PRESERVED byte-identical (S238 guard —\n"
        "#                                    the cure must never widen into clobber)\n"
        "#   L5  legacy (pre-W1 absolute) body -> upgrade : CURED to the portable form\n"
        "#                                    (same checkout, backup byte-exact) — PLAN-183 W1\n",
        1,
    ),
    (
        INV4_T,
        "command -v _render_protocol_pointer_degraded >/dev/null 2>&1 || {\n"
        "  echo \"ERROR: generator missing (W2 not in tree)\" >&2; exit 2; }\n",
        "command -v _render_protocol_pointer_degraded >/dev/null 2>&1 || {\n"
        "  echo \"ERROR: generator missing (W2 not in tree)\" >&2; exit 2; }\n"
        "command -v _render_protocol_pointer_legacy >/dev/null 2>&1 || {\n"
        "  echo \"ERROR: legacy generator missing (PLAN-183 W1 not in tree)\" >&2; exit 2; }\n",
        1,
    ),
    (
        INV4_T,
        "assert_sound() { # $1=file $2=label — token absent, resolved source present\n"
        "  if grep -F -q '{{PROTOCOL_SOURCE}}' \"$1\"; then\n"
        "    fail \"$2: token {{PROTOCOL_SOURCE}} still present (degraded output)\"\n"
        "    return 1\n"
        "  fi\n"
        "  if ! grep -F -q \"$REPO_ROOT/PROTOCOL.md\" \"$1\"; then\n"
        "    fail \"$2: resolved source path missing from pointer\"\n"
        "    return 1\n"
        "  fi\n"
        "  return 0\n"
        "}\n",
        "REPO_ROOT_P=\"$( cd \"$REPO_ROOT\" && pwd -P )\"\n"
        "assert_sound() { # $1=file $2=label — token absent, named checkout RESOLVES to this one, relatively\n"
        "  local named base\n"
        "  if grep -F -q '{{PROTOCOL_SOURCE}}' \"$1\"; then\n"
        "    fail \"$2: token {{PROTOCOL_SOURCE}} still present (degraded output)\"\n"
        "    return 1\n"
        "  fi\n"
        "  named=\"$( sed -n 's|^\\(..*\\)/PROTOCOL\\.md$|\\1|p' \"$1\" | sed -n '1p' )\"\n"
        "  if [ -z \"$named\" ]; then\n"
        "    fail \"$2: no '<checkout>/PROTOCOL.md' line in pointer\"\n"
        "    return 1\n"
        "  fi\n"
        "  # PLAN-183 W1: the named checkout is relative to the pointer's own directory\n"
        "  # (the target) and must land on THIS checkout; an absolute value is the\n"
        "  # pre-W1 form — sound in place, dead after a move — and fails here.\n"
        "  case \"$named\" in\n"
        "    /*) fail \"$2: pointer names an ABSOLUTE checkout path (pre-W1 form — not portable)\"; return 1 ;;\n"
        "  esac\n"
        "  base=\"$T/$named\"\n"
        "  if [ ! -f \"$base/PROTOCOL.md\" ] || [ \"$( cd \"$base\" 2>/dev/null && pwd -P )\" != \"$REPO_ROOT_P\" ]; then\n"
        "    fail \"$2: pointer names '$named', which does not resolve to this checkout from $T\"\n"
        "    return 1\n"
        "  fi\n"
        "  return 0\n"
        "}\n",
        1,
    ),
    (
        INV4_T,
        "echo \"\"\n"
        "if [[ \"$FAILURES\" -gt 0 ]]; then\n"
        "  echo \"INV-4 assertion: $FAILURES leg(s) FAILED\"\n"
        "  exit 1\n"
        "fi\n"
        "echo \"INV-4 assertion: 4/4 legs pass (byte identity + content soundness + cure + preserve)\"\n",
        "# --- L5: LEGACY (pre-PLAN-183, absolute) body is CURED to the portable form --\n"
        "# The planted bytes are the FROZEN legacy generator's output for THIS checkout\n"
        "# — identical to what a pre-W1 install.sh wrote (render control R2 pins that\n"
        "# identity; the portable e2e proves it against the real previous release).\n"
        "# The cure must keep the SAME checkout (only the shape migrates), resolve,\n"
        "# carry no absolute path, report its own route, and leave a byte-exact backup.\n"
        "_render_protocol_pointer_legacy \"$REPO_ROOT\" \"$T\" \"$PROFILE\" \"$STACK\" > \"$T/PROTOCOL.md\"\n"
        "cp \"$T/PROTOCOL.md\" \"$WORK/planted-legacy.md\"\n"
        "if ! run_upgrade \"$T\" \"$WORK/upgrade5.log\"; then\n"
        "  echo \"ERROR: legacy-cure upgrade failed\"; sed -n '1,12p' \"$WORK/upgrade5.log\"; exit 2\n"
        "fi\n"
        "if cmp -s \"$WORK/planted-legacy.md\" \"$T/PROTOCOL.md\"; then\n"
        "  fail \"L5 legacy absolute pointer NOT cured (survived the upgrade unchanged)\"\n"
        "elif assert_sound \"$T/PROTOCOL.md\" \"L5 post-cure\"; then\n"
        "  if grep -q \"CURED: PROTOCOL.md pointer was the pre-PLAN-183\" \"$WORK/upgrade5.log\"; then\n"
        "    echo \"PASS  L5 legacy body cured to the portable form (legacy REFRESH route, same checkout)\"\n"
        "  else\n"
        "    fail \"L5 pointer sound but the legacy CURED route was not what ran (check upgrade5.log)\"\n"
        "    grep -n \"PROTOCOL.md\" \"$WORK/upgrade5.log\" | head -5\n"
        "  fi\n"
        "  BKP5=\"$( ls -t \"$T\"/.claude.bak/*/PROTOCOL.md 2>/dev/null | head -1 )\"\n"
        "  if [ -n \"$BKP5\" ] && cmp -s \"$BKP5\" \"$WORK/planted-legacy.md\"; then\n"
        "    echo \"PASS  L5b cure kept a byte-exact backup of the legacy original\"\n"
        "  else\n"
        "    fail \"L5b backup missing or does not match the planted legacy bytes (BKP=${BKP5:-<none>})\"\n"
        "  fi\n"
        "fi\n"
        "\n"
        "echo \"\"\n"
        "if [[ \"$FAILURES\" -gt 0 ]]; then\n"
        "  echo \"INV-4 assertion: $FAILURES leg(s) FAILED\"\n"
        "  exit 1\n"
        "fi\n"
        "echo \"INV-4 assertion: 5/5 legs pass (byte identity + relative soundness + cure + preserve + legacy cure)\"\n",
        1,
    ),
    # ---------------- ownership triad --------------------------------------
    (
        TSV,
        "OWN-0094\tprotocol\thash\tregular\tdegraded\tyes\tcopy\tuser\tupgrade\tnone\tnone\tPRESERVE_OWNED\tHASH_PRIOR_RECORD\tplan-168\tuser ceremony cannot cure - WS4: a user ceremony never writes root surfaces; the A2 carry preserves and the degraded body waits for a maintainer upgrade\n",
        "OWN-0094\tprotocol\thash\tregular\tdegraded\tyes\tcopy\tuser\tupgrade\tnone\tnone\tPRESERVE_OWNED\tHASH_PRIOR_RECORD\tplan-168\tuser ceremony cannot cure - WS4: a user ceremony never writes root surfaces; the A2 carry preserves and the degraded body waits for a maintainer upgrade\n"
        "OWN-0095\tprotocol\thash\tregular\tlegacy_absolute\tyes\tcopy\tmaintainer\tupgrade\tnone\tnone\tREFRESH\tHASH_CANONICAL_POINTER\tplan-183\tthe RETROACTIVE cure (W1 A1): the pre-W1 healthy body (token substituted, absolute TARGET in its own upgrade line, byte-exact reconstruction from the file own values) is the framework own output of an older generator - REFRESH to the portable form with backup, never preserved; the checkout the file names is kept, only the shape migrates\n"
        "OWN-0096\tprotocol\tnone\tregular\tlegacy_absolute\tyes\tcopy\tmaintainer\tupgrade\tnone\tnone\tREFRESH\tHASH_CANONICAL_POINTER\tplan-183\trecordless legacy takeover - content-proven framework origin, same doctrine as degraded (OWN-0093) and legacy_pristine (r20)\n"
        "OWN-0097\tprotocol\thash\tregular\tlegacy_absolute\tyes\tcopy\tuser\tupgrade\tnone\tnone\tPRESERVE_OWNED\tHASH_PRIOR_RECORD\tplan-183\tuser ceremony cannot cure - WS4 (mirrors OWN-0094): the A2 carry preserves and the legacy body waits for a maintainer upgrade\n",
        1,
    ),
    (
        DOC,
        "| `degraded` | (protocol only, PLAN-168 W2) byte-exact reconstruction of the `{{PROTOCOL_SOURCE}}`-literal pointer template a pre-PLAN-168 `upgrade.sh` wrote — the framework's OWN output, never adopter content |\n",
        "| `degraded` | (protocol only, PLAN-168 W2) byte-exact reconstruction of the `{{PROTOCOL_SOURCE}}`-literal pointer template a pre-PLAN-168 `upgrade.sh` wrote — the framework's OWN output, never adopter content |\n"
        "| `legacy_absolute` | (protocol only, PLAN-183 W1) byte-exact reconstruction of the pre-W1 HEALTHY outside-target body — the token substituted with the checkout path the file itself names (absolute in the whole shipped population), the absolute `TARGET` in its own upgrade line — i.e. an OLDER generator's output, never adopter content. Recognizer: `_protocol_pointer_legacy_source` |\n",
        1,
    ),
    (
        DOC,
        "preserved. Recognizer: `_protocol_pointer_is_degraded` in\n"
        "`scripts/_framework_manifest_set.sh`.\n",
        "preserved. Recognizer: `_protocol_pointer_is_degraded` in\n"
        "`scripts/_framework_manifest_set.sh`.\n"
        "\n"
        "`legacy_absolute` (PLAN-183 W1, A1) is the third application of the same\n"
        "doctrine, to the pointer's **previous healthy generation**: from v1.0.1 to\n"
        "v1.3.0 the outside-target body named the checkout by ABSOLUTE path and put\n"
        "the absolute target in its upgrade line — dead after a move, and carrying the\n"
        "maintainer's home into adopter trees. Recognition is again by template\n"
        "reconstruction: the checkout from the file's own 4th line, `TARGET`/`PROFILE`/\n"
        "`STACK` from its own upgrade line, re-rendered through the FROZEN\n"
        "`_render_protocol_pointer_legacy` and required byte-identical. The cure is the\n"
        "protocol `REFRESH` route with the standard backup, and it keeps the checkout\n"
        "the file names (only the SHAPE migrates — re-rendering from the recorded value\n"
        "instead would turn a shape migration into a silent re-point, the S238 class).\n"
        "Any edit ⇒ `edited` ⇒ preserved — and WARNED, because the body names an\n"
        "absolute path (W1 turned silent preservation into warned preservation).\n",
        1,
    ),
    (
        DOC,
        "| **R-04b** | `live_content=degraded` ⇒ `surface=protocol` (PLAN-168 W2) | The degraded template is a pointer construct: only the generated `PROTOCOL.md` ever carried the `{{PROTOCOL_SOURCE}}`-literal body. `SPEC/v1` legacy recognition already has `legacy_pristine`; the marker is a one-line version string with no template to degrade. |\n",
        "| **R-04b** | `live_content=degraded` ⇒ `surface=protocol` (PLAN-168 W2) | The degraded template is a pointer construct: only the generated `PROTOCOL.md` ever carried the `{{PROTOCOL_SOURCE}}`-literal body. `SPEC/v1` legacy recognition already has `legacy_pristine`; the marker is a one-line version string with no template to degrade. |\n"
        "| **R-04c** | `live_content=legacy_absolute` ⇒ `surface=protocol` (PLAN-183 W1) | The pre-W1 healthy body is a pointer construct too: only the generated `PROTOCOL.md` ever carried the absolute-source template. `SPEC/v1` has `legacy_pristine`, the marker has nothing to be legacy about. Sibling of R-04b, same reason. |\n",
        1,
    ),
    (
        HARNESS,
        "command -v _render_protocol_pointer_degraded >/dev/null 2>&1 || {\n"
        "  echo \"ERROR: _render_protocol_pointer_degraded missing (W2 not in tree)\" >&2; exit 2; }\n",
        "command -v _render_protocol_pointer_degraded >/dev/null 2>&1 || {\n"
        "  echo \"ERROR: _render_protocol_pointer_degraded missing (W2 not in tree)\" >&2; exit 2; }\n"
        "command -v _render_protocol_pointer_legacy >/dev/null 2>&1 || {\n"
        "  echo \"ERROR: _render_protocol_pointer_legacy missing (PLAN-183 W1 not in tree)\" >&2; exit 2; }\n",
        1,
    ),
    (
        HARNESS,
        "      if [[ \"$surface\" == \"protocol\" && ! -L \"$p\" && ! -d \"$p\" ]]; then\n"
        "        _render_protocol_pointer_degraded \"$T\" core generic > \"$p\"\n"
        "      fi\n"
        "      ;;\n"
        "    legacy_pristine)\n",
        "      if [[ \"$surface\" == \"protocol\" && ! -L \"$p\" && ! -d \"$p\" ]]; then\n"
        "        _render_protocol_pointer_degraded \"$T\" core generic > \"$p\"\n"
        "      fi\n"
        "      ;;\n"
        "    legacy_absolute)\n"
        "      # PLAN-183 W1 (A1): the pre-W1 HEALTHY outside-target body — the token\n"
        "      # substituted with the ABSOLUTE checkout path every v1.0.1..v1.3.0\n"
        "      # install wrote (the shipped population the retroactive cure targets).\n"
        "      # Rendered by the FROZEN legacy generator, never hand-built; the value\n"
        "      # is this run's source root, exactly what such an install recorded.\n"
        "      if [[ \"$surface\" == \"protocol\" && ! -L \"$p\" && ! -d \"$p\" ]]; then\n"
        "        _render_protocol_pointer_legacy \"$src_root\" \"$T\" core generic > \"$p\"\n"
        "      fi\n"
        "      ;;\n"
        "    legacy_pristine)\n",
        1,
    ),
    # ---------------- CI wiring (rail r1/r2: an unwired scripts/tests/*.sh is
    # no test — smoke-install.yml:30-34). Nightly, next to its sibling INV-4
    # (same budget class: real installs + upgrades + a git archive); the path
    # filters mirror the inv4 lines (2 occurrences: push + pull_request).
    (
        NIGHTLY_WF,
        "      - name: Protocol pointer INV-4 e2e (4 legs)\n"
        "        run: |\n"
        "          set -euo pipefail\n"
        "          bash scripts/tests/test-protocol-pointer-inv4.sh\n",
        "      - name: Protocol pointer INV-4 e2e (5 legs)\n"
        "        run: |\n"
        "          set -euo pipefail\n"
        "          bash scripts/tests/test-protocol-pointer-inv4.sh\n"
        "\n"
        "      # PLAN-183 W1 (A1): the PORTABLE pointer e2e — moving project and\n"
        "      # checkout TOGETHER keeps the pointer resolving; moving the target ALONE\n"
        "      # yields the NAMED repair (and the repair works, persisted); the REAL\n"
        "      # previous release's absolute pointer is cured; a preserved absolute is\n"
        "      # WARNED. ~5.5 min local (4 installs + 5 upgrades + one git archive of\n"
        "      # the pre-W1 release tag — the tag fetch above makes it reachable).\n"
        "      - name: Protocol pointer portable e2e (PLAN-183 W1)\n"
        "        run: |\n"
        "          set -euo pipefail\n"
        "          bash scripts/tests/test-protocol-pointer-portable.sh\n",
        1,
    ),
    (
        SMOKE_WF,
        "      - \"scripts/tests/test-protocol-pointer-inv4.sh\"\n",
        "      - \"scripts/tests/test-protocol-pointer-inv4.sh\"\n"
        "      - \"scripts/tests/test-protocol-pointer-portable.sh\"\n",
        2,
    ),
    # ---------------- NEW file ----------------------------------------------
    (NEW_TEST_REL, "", NEW_TEST_BODY, 0),
]

TOUCHED_BY_EDITS = sorted({e[0] for e in EDITS} | {BASELINE_REL})


def _is_cure(rel: str, old: str) -> bool:
    """CURA (o comportamento) vs INSTRUMENTO (testes, funcoes novas, triade).

    Serve ao CONTROLE POSITIVO: `--control-no-cure` aplica so os instrumentos
    sobre a arvore em BASE, e a bateria tem de sair VERMELHA nela — prova de
    que os testes mordem o mecanismo e nao a si mesmos. A cerimonia usa o modo
    default (tudo). Cura = ramo `*)` de _render_protocol_pointer, o `elif` de
    _ownership_verdict, e TODAS as edicoes de upgrade.sh e install.sh.
    """
    if rel in (UPGRADE, INSTALL):
        return True
    if rel == MANIFEST:
        return old.startswith("    *)\n") or old.startswith("  elif [ \"$_ov_lcontent\" = \"degraded\" ]")
    return False


class Refuse(Exception):
    pass


def _selected(no_cure: bool) -> List[Tuple[str, str, str, int]]:
    if not no_cure:
        return list(EDITS)
    return [e for e in EDITS if not _is_cure(e[0], e[1])]


def _plan(root: Path, no_cure: bool = False) -> None:
    """Passo 1 — conta TODAS as ancoras e recusa antes de qualquer escrita."""
    problems = []
    for rel, old, _new, count in _selected(no_cure):
        p = root / rel
        if count == 0 and old == "":
            if p.exists():
                problems.append("%s: ja existe (arquivo NOVO da wave)" % rel)
            continue
        if not p.is_file():
            problems.append("%s: arquivo ausente" % rel)
            continue
        text = p.read_text(encoding="utf-8")
        n = text.count(old)
        if n != count:
            problems.append("%s: ancora encontrada %dx, esperado %d — %r"
                            % (rel, n, count, old[:70]))
    # Ja aplicado? O marcador da W1 nao pode existir em NENHUM path tocado.
    for rel in TOUCHED_BY_EDITS:
        p = root / rel
        if rel == BASELINE_REL:
            continue
        if p.is_file() and NEW_MARKER in p.read_text(encoding="utf-8"):
            problems.append("%s: ja contem %s — arvore ja patchada?" % (rel, NEW_MARKER))
    for rel in (BASELINE_REL, CENSUS_REL):
        if not (root / rel).is_file():
            problems.append("%s: ausente (o pos-passo do ratchet precisa dele)" % rel)
    if problems:
        raise Refuse("\n".join("  - " + x for x in problems))


def _apply(root: Path, no_cure: bool = False) -> List[str]:
    written: List[str] = []
    for rel, old, new, count in _selected(no_cure):
        p = root / rel
        if count == 0 and old == "":
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(new, encoding="utf-8")
            os.chmod(p, 0o755)   # como os irmaos executaveis de scripts/tests/
        else:
            text = p.read_text(encoding="utf-8")
            assert text.count(old) == count  # _plan ja garantiu
            p.write_text(text.replace(old, new), encoding="utf-8")
        if rel not in written:
            written.append(rel)
    # Ratchet PLAN-185 W0: as linhas do baseline sao chaveadas por numero de
    # linha; a W1 desloca install.sh e upgrade.sh e remove um sitio de escrita
    # em install.sh (2 -> 1). Re-gerado pelo PROPRIO censo, deterministico a
    # partir da arvore, nunca a mao. Primeiro o censo tem de FALHAR (baseline
    # velho) — se passar, o pos-passo e desnecessario e o baseline fica intacto.
    census = root / CENSUS_REL
    rc = subprocess.run([sys.executable, str(census), "--repo-root", str(root)],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
    if rc != 0:
        out = subprocess.run([sys.executable, str(census), "--repo-root", str(root),
                              "--write-baseline"], capture_output=True, text=True)
        if out.returncode != 0:
            raise Refuse("%s --write-baseline falhou (rc=%d):\n%s"
                         % (CENSUS_REL, out.returncode, (out.stderr or out.stdout)[-2000:]))
        rc2 = subprocess.run([sys.executable, str(census), "--repo-root", str(root)],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode
        if rc2 != 0:
            raise Refuse("%s ainda falha (rc=%d) depois de re-gerar o baseline" % (CENSUS_REL, rc2))
        written.append(BASELINE_REL)
    return sorted(set(written))


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", help="arvore em BASE (HEAD + wave-fable51) a patchar")
    ap.add_argument("--check-only", action="store_true",
                    help="so verifica as ancoras; nao escreve nada")
    ap.add_argument("--list-paths", action="store_true",
                    help="imprime os paths tocados (um por linha) e sai")
    ap.add_argument("--control-no-cure", action="store_true",
                    help="CONTROLE POSITIVO: aplica so os instrumentos (testes, funcoes "
                         "novas, triade), NUNCA a cura — a bateria deve sair vermelha")
    args = ap.parse_args(argv)
    if args.list_paths:
        for rel in TOUCHED_BY_EDITS:
            print(rel)
        return 0
    if not args.root:
        sys.stderr.write("apply-w1-edits: --root e obrigatorio\n")
        return 2
    root = Path(args.root).resolve()
    if not (root / ".claude").is_dir():
        sys.stderr.write("apply-w1-edits: --root nao parece um checkout: %s\n" % root)
        return 2
    sel = _selected(args.control_no_cure)
    mode = " [CONTROLE: sem cura]" if args.control_no_cure else ""
    try:
        _plan(root, args.control_no_cure)
        if args.check_only:
            print("apply-w1-edits%s: %d edicao(oes) aplicaveis em %d path(s); nada escrito"
                  % (mode, len(sel), len(TOUCHED_BY_EDITS)))
            return 0
        written = _apply(root, args.control_no_cure)
    except Refuse as exc:
        sys.stderr.write("apply-w1-edits: RECUSADO\n%s\n" % exc)
        return 1
    print("apply-w1-edits%s: %d edicao(oes) aplicadas em %d path(s):"
          % (mode, len(sel), len(written)))
    for rel in written:
        print("  " + rel)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
