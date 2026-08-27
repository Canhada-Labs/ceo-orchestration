#!/usr/bin/env bash
# scripts/tests/test-upgrade-lifecycle-hooks-derived.sh
# PLAN-169 W-E (S329) — upgrade.sh derives the hook roster it registers from
# templates/settings/settings.base.json instead of carrying a second copy of it.
#
# WHY THIS EXISTS
# ---------------
# `_merge_lifecycle_hooks_into_settings` used to hard-code SIX lifecycle
# registrations inside its jq program and repeat the same six in prose for the
# --dry-run announcement. Two measured consequences of that second declaration:
#
#   (1) check_ledger_checkpoint.py (PLAN-179 W2/W4) landed in .claude/settings.json
#       AND in the template mirror and in NEITHER list, so every adopter that
#       UPGRADED got the hook script with no registration. Fresh installs were
#       fine (the template covers them), which is exactly why
#       test_template_dogfood_parity never saw it: that oracle compares dogfood
#       to template, never dogfood to THE RESULT OF AN UPGRADE.
#       (S328, rail codex round 3 of the PLAN-179 pack D — see
#        .claude/plans/PLAN-179/s328-ceremony-D/FINDING-upgrade-lifecycle-hooks-S328.md)
#
#   (2) FIVE of the six hard-coded blocks had already drifted from the template
#       in their `_comment`, and the pre-cure merge RE-CANONICALIZED them on
#       every upgrade — so an adopter who installed correctly had the current
#       template text overwritten with a stale copy by their first upgrade.
#       E.9 below measures that drift directly against the pre-cure source.
#
# THE ASSERTIONS THAT ARE NOT ABOUT THE HAPPY PATH
#   E.1  the fixture is NOT vacuous: a fresh install already carries every
#        template registration, so "all present after upgrade" would pass for
#        free if the fixture were not deliberately stripped first.
#   E.3  the PRE-CURE upgrader, run against the same stripped adopter, LEAVES
#        check_ledger_checkpoint.py unregistered. Without this red control,
#        E.2 green is indistinguishable from "the hook was already there".
#   E.4  POSITIVE CONTROL — a SYNTHETIC hook added to a copy of the template is
#        registered by the upgrade, and its name appears nowhere in upgrade.sh.
#        This is what separates "derives from the template" from "carries a
#        longer list": a literal roster cannot know a name invented at runtime.
#   E.7  an adopter-EDITED registration survives byte-identical. The pre-cure
#        code re-canonicalized its six; additive semantics is the whole point.
#   E.8  a `.hooks` event whose value is NOT an array is PRESERVED and NAMED,
#        never coerced — an unparseable shape must fail safe, not get guessed.
#   E.10 the same rule for the shapes that LOOK empty: an EXPLICIT `null` or
#        `false` container is a decision the adopter made, not an absent key.
#        `x // []` cannot tell those apart, so the merge asks `has(...)`.
#   E.11 the TEMPLATE is held to a STRICTER standard than the adopter's file:
#        an event value that is not an array of blocks refuses the whole merge
#        and is named. Tolerating it per-event would ship a truncated roster,
#        which is this file's own bug class one layer up.
#   E.12 the same rule one level DOWN: a block the key-derivation cannot
#        identify refuses the merge instead of being skipped past while its
#        well-formed siblings land.
#   E.13 a PRESERVED event is never reported as "everything already present".
#        With everything else registered, a skip leaves the count at zero, and
#        calling that completeness is worse than printing nothing — it is the
#        line an adopter reads for reassurance. E.13d is the control that keeps
#        the fix from being "delete the sentence".
#   E.2i POSITIVE CONTROL for the duplicate assertion — it plants a duplicate
#        and requires E.2h's oracle to see it. The previous form counted keys
#        from a DEDUPLICATED stream and so could never fail (rail round 1, P2);
#        E.2i-b re-measures that blind spot on the same fixture, permanently.
#
# bash-3.2 safe (no associative arrays, no mapfile). Network-free. Writes only
# under mktemp -d. Requires: git, jq, python3.
#
# Run:  bash scripts/tests/test-upgrade-lifecycle-hooks-derived.sh ; echo rc=$?
set -uo pipefail   # NOT -e: every failure is asserted, never fatal-by-default.

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
INSTALL="$REPO_ROOT/scripts/install.sh"
UPGRADE="$REPO_ROOT/scripts/upgrade.sh"
TEMPLATE="$REPO_ROOT/templates/settings/settings.base.json"

# The synthetic hook E.4 plants. Asserted ABSENT from the upgrader (a literal
# roster could not register it) before it is asserted PRESENT after the run.
SYNTH="check_zz_synthetic_e4.py"

PASS=0
FAIL=0
ok()  { PASS=$((PASS+1)); printf '  ok   %s\n' "$1"; }
bad() { FAIL=$((FAIL+1)); printf '  FAIL %s\n' "$1" >&2; }

scaffold() { echo "" >&2; echo "SCAFFOLD-ERROR: $*" >&2; exit 9; }

command -v git     >/dev/null 2>&1 || scaffold "git not on PATH"
command -v jq      >/dev/null 2>&1 || scaffold "jq not on PATH (the merge engine under test)"
command -v python3 >/dev/null 2>&1 || scaffold "python3 not on PATH"
[ -f "$INSTALL" ]  || scaffold "installer missing: $INSTALL"
[ -f "$UPGRADE" ]  || scaffold "upgrader missing: $UPGRADE"
[ -f "$TEMPLATE" ] || scaffold "template missing: $TEMPLATE"

# E.3 replays the PRE-CURE upgrader out of git. A shallow/filtered checkout
# cannot produce it, and a red control that silently degrades to a skip is
# worse than no red control at all.
git -C "$REPO_ROOT" rev-parse --verify HEAD >/dev/null 2>&1 \
  || scaffold "no git HEAD in $REPO_ROOT — E.3 replays the pre-cure upgrader from history"

WORK="$( mktemp -d -t ceo-hooks-derived-XXXXXX )" || scaffold "mktemp -d failed"
cleanup() {
  [ "${CEO_HOOKS_KEEP_WORK:-0}" = "1" ] && return 0
  [ -n "${WORK:-}" ] || return 0
  chmod -R u+w "$WORK" 2>/dev/null || true
  rm -rf "$WORK" 2>/dev/null || true
}
trap cleanup EXIT

export CEO_INSTALL_SKIP_SELF_SHA=1
export CEO_RAG_INSTALL_PROMPT=0

echo "=============================================================="
echo " upgrade hook-roster derivation e2e   (PLAN-169 W-E — S329)"
echo "=============================================================="
echo "  repo   : $REPO_ROOT"
echo "  workdir: $WORK"
echo "--------------------------------------------------------------"

# --- helpers ---------------------------------------------------------------

_sha() { shasum -a 256 "$1" 2>/dev/null | cut -d' ' -f1; }

# The (event, registration-key) SET of a settings-like document, one "ev key"
# per line, sorted. This is the comparison every assertion below uses: the
# merge APPENDS, so array ORDER legitimately differs from the template and a
# literal diff would report a difference that is not a defect.
#
# The key derivation is INDEPENDENT of the upgrader's (python here, jq there)
# on purpose: an oracle that reuses the implementation's own extractor cannot
# catch that extractor being wrong.
_keys_raw() {  # $1=json file  $2="set"|"bag"
  python3 - "$1" "$2" <<'PY'
import json, re, sys
TOK = re.compile(r'(?<![A-Za-z0-9_.-])[A-Za-z0-9_][A-Za-z0-9_.-]*\.py(?![A-Za-z0-9_.-])')
try:
    doc = json.load(open(sys.argv[1], encoding="utf-8"))
except Exception:
    sys.exit(0)
out = []
hooks = doc.get("hooks")
if not isinstance(hooks, dict):
    sys.exit(0)
for ev in sorted(hooks):
    blocks = hooks[ev]
    if not isinstance(blocks, list):
        continue
    for b in blocks:
        if not isinstance(b, dict):
            continue
        cmds = [(h.get("command") or "") for h in (b.get("hooks") or []) if isinstance(h, dict)]
        for c in cmds:
            names = TOK.findall(c)
            for n in (names or [" ".join(c.split())]):
                out.append("%s %s" % (ev, n))
for line in sorted(set(out) if sys.argv[2] == "set" else out):
    print(line)
PY
}

# The SET of registration keys. Right for "is anything missing / invented"
# (comm needs sorted, deduplicated input) and WRONG for "is anything
# duplicated" — see _keybag.
_keyset() { _keys_raw "$1" set; }

# The same keys WITH MULTIPLICITY. `sort | uniq -d` over _keyset can never
# report anything, because _keyset has already collapsed duplicates: the
# duplicate assertion that used it was structurally incapable of failing
# (rail round 1, P2). The two are kept as separate helpers, rather than one
# helper with a default, so a future caller has to CHOOSE which question it
# is asking. E.2i is the positive control that keeps this one honest.
_keybag() { _keys_raw "$1" bag; }

# Fresh maintainer install into $1 (cached — a real install is the most
# expensive thing here and every fixture below wants the same starting tree).
_INSTALL_CACHE=""
_install() {
  _i_dir="$1"
  if [ -n "$_INSTALL_CACHE" ] && [ -d "$_INSTALL_CACHE" ]; then
    mkdir -p "$( dirname "$_i_dir" )"
    cp -R "$_INSTALL_CACHE" "$_i_dir" || scaffold "could not copy the cached install into $_i_dir"
    return 0
  fi
  mkdir -p "$_i_dir"
  ( cd "$_i_dir" && git init -q ) || scaffold "git init failed in $_i_dir"
  bash "$INSTALL" "$_i_dir" --profile core --ceremony maintainer \
    > "$_i_dir.install.log" 2>&1 \
    || { tail -30 "$_i_dir.install.log" >&2; scaffold "install.sh failed for $_i_dir"; }
  _i_seed="$WORK/cache/adopter"
  mkdir -p "$( dirname "$_i_seed" )"
  cp -R "$_i_dir" "$_i_seed" || scaffold "could not seed the install cache"
  _INSTALL_CACHE="$_i_seed"
}

# Upgrade $1 from source tree $2 (default: the working tree). Sets _UP_LOG and
# _UP_RC in THIS shell — never echoes the path, because `LOG=$( _upgrade ... )`
# would run the whole thing in a subshell and _UP_RC would come back unbound.
_UP_LOG=""
_UP_RC=0
_UPGRADE_SEQ=0
_upgrade() {  # $1=target  $2=source-root  [extra upgrade flags...]
  _u_dir="$1"; _u_src="$2"; shift 2
  _UPGRADE_SEQ=$(( _UPGRADE_SEQ + 1 ))
  _UP_LOG="$_u_dir.upgrade.$_UPGRADE_SEQ.log"
  _UP_RC=0
  bash "$_u_src/scripts/upgrade.sh" "$_u_dir" --profile core --no-diff-warn --no-replay "$@" \
    > "$_UP_LOG" 2>&1 || _UP_RC=$?
}

# A source tree that is the repo everywhere except scripts/ + templates/, which
# are real copies so a fixture can edit them. Same idiom as
# test-upgrade-historical-adopter.sh:_mk_source_copy.
_mk_source_copy() {  # $1=dir
  mkdir -p "$1" || return 1
  for _msc_e in "$REPO_ROOT"/* "$REPO_ROOT"/.[!.]*; do
    [ -e "$_msc_e" ] || continue
    _msc_b="$( basename "$_msc_e" )"
    case "$_msc_b" in scripts|templates) continue ;; esac
    ln -s "$_msc_e" "$1/$_msc_b" 2>/dev/null || true
  done
  cp -R "$REPO_ROOT/scripts"   "$1/scripts"   || return 1
  cp -R "$REPO_ROOT/templates" "$1/templates" || return 1
  return 0
}

# Strip four registrations from $1's settings.json, covering four DIFFERENT
# shapes so a cure that only handles one of them cannot pass:
#   - a .py block in a crowded event          (PreToolUse check_ledger_checkpoint.py — THE finding)
#   - a .py block in an event with siblings   (SessionStart check_compact_pinning.py)
#   - a whole EVENT key                       (PreCompact — absent, not empty)
#   - an INLINE block with no .py at all      (PostToolUse|Agent file-assignment echo)
_strip_four() {  # $1=adopter dir
  jq 'del(.hooks.PreToolUse[]  | select((.hooks[0].command // "") | test("check_ledger_checkpoint")))
    | del(.hooks.SessionStart[] | select((.hooks[0].command // "") | test("check_compact_pinning")))
    | del(.hooks.PreCompact)
    | del(.hooks.PostToolUse[] | select((.hooks[0].command // "") | test("file assignment compliance")))' \
    "$1/.claude/settings.json" > "$1/.claude/settings.json.stripped" \
    && mv "$1/.claude/settings.json.stripped" "$1/.claude/settings.json"
}

# ---------------------------------------------------------------------------
# E.1  the fixture is not vacuous
# ---------------------------------------------------------------------------
echo ""
echo "==> E.1 — a fresh install already carries every template registration"
BASE="$WORK/base/adopter"
_install "$BASE"
_keyset "$TEMPLATE"                     > "$WORK/tpl.keys"
_keyset "$BASE/.claude/settings.json"   > "$WORK/base.keys"
TPL_N="$( wc -l < "$WORK/tpl.keys" | tr -d ' ' )"

[ "${TPL_N:-0}" -ge 20 ] \
  && ok "E.1a the template enumerates $TPL_N registrations (a near-empty template would make every assertion below vacuous)" \
  || bad "E.1a the template yielded only ${TPL_N:-0} registrations — the oracle is not reading it"

if diff -q "$WORK/tpl.keys" "$WORK/base.keys" >/dev/null 2>&1; then
  ok "E.1b a fresh install's registration set EQUALS the template's — so 'all present' after an upgrade is only evidence once the fixture is stripped"
else
  bad "E.1b fresh install != template registration set (see diff below); the fixture's starting point is not what this file assumes"
  diff "$WORK/tpl.keys" "$WORK/base.keys" | head -10 >&2
fi

# ---------------------------------------------------------------------------
# E.2  the historical adopter gets EVERY missing registration back
# ---------------------------------------------------------------------------
echo ""
echo "==> E.2 — a stripped adopter is fully re-registered by a real upgrade"
A="$WORK/hist/adopter"
_install "$A"

# E.7's fixture rides the same adopter: edit a timeout on a registration that
# is PRESENT, and it must survive. 4242 is not a value any template carries.
jq '(.hooks.PreToolUse[] | select((.hooks[0].command // "") | test("check_bash_safety")) | .hooks[0].timeout) = 4242' \
   "$A/.claude/settings.json" > "$A/.claude/s.tmp" && mv "$A/.claude/s.tmp" "$A/.claude/settings.json"

_strip_four "$A" || scaffold "could not strip the fixture registrations"
_keyset "$A/.claude/settings.json" > "$WORK/hist.pre.keys"
STRIPPED_N=$(( TPL_N - $( wc -l < "$WORK/hist.pre.keys" | tr -d ' ' ) ))

[ "$STRIPPED_N" -eq 4 ] \
  && ok "E.2a the fixture really is missing 4 registrations before the upgrade" \
  || bad "E.2a expected 4 stripped registrations, got $STRIPPED_N — the strip did not bite, so E.2c proves nothing"

grep -q 'check_ledger_checkpoint.py' "$WORK/hist.pre.keys" \
  && bad "E.2b check_ledger_checkpoint.py is still registered before the upgrade — the strip missed THE finding" \
  || ok "E.2b check_ledger_checkpoint.py (the S328 finding) is absent before the upgrade"

# --- E.6 rides here: --dry-run must announce, and must not write ------------
DRY_SHA_BEFORE="$( _sha "$A/.claude/settings.json" )"
_upgrade "$A" "$REPO_ROOT" --dry-run
DRY_SHA_AFTER="$( _sha "$A/.claude/settings.json" )"

grep -q "would REGISTER PreToolUse check_ledger_checkpoint.py" "$_UP_LOG" \
  && ok "E.6a --dry-run names the missing hook (a migration silent in dry-run is one the adopter cannot review)" \
  || bad "E.6a --dry-run did not announce check_ledger_checkpoint.py (see $_UP_LOG)"

grep -q "would REGISTER PreCompact check_precompact_continuity.py" "$_UP_LOG" \
  && ok "E.6b --dry-run also names a registration under an ABSENT event key" \
  || bad "E.6b --dry-run did not announce the PreCompact registration (see $_UP_LOG)"

[ "$DRY_SHA_BEFORE" = "$DRY_SHA_AFTER" ] \
  && ok "E.6c --dry-run left settings.json byte-identical" \
  || bad "E.6c --dry-run MODIFIED settings.json ($DRY_SHA_BEFORE -> $DRY_SHA_AFTER)"

# --- the real upgrade ------------------------------------------------------
_upgrade "$A" "$REPO_ROOT"
[ "$_UP_RC" -eq 0 ] \
  && ok "E.2c the upgrade succeeded" \
  || bad "E.2c the upgrade exited $_UP_RC (see $_UP_LOG)"

_keyset "$A/.claude/settings.json" > "$WORK/hist.post.keys"
MISSING="$( comm -23 "$WORK/tpl.keys" "$WORK/hist.post.keys" )"
if [ -z "$MISSING" ]; then
  ok "E.2d EVERY registration in the template is present in the upgraded adopter — all $TPL_N, not a curated six"
else
  bad "E.2d registrations still missing after the upgrade:"
  printf '%s\n' "$MISSING" | sed 's/^/         /' >&2
fi

grep -q "^PreToolUse check_ledger_checkpoint.py$" "$WORK/hist.post.keys" \
  && ok "E.2e check_ledger_checkpoint.py — the S328 finding — is registered by the upgrade" \
  || bad "E.2e check_ledger_checkpoint.py is STILL unregistered after the upgrade; the finding is not cured"

grep -q "file assignment compliance" "$WORK/hist.post.keys" \
  && ok "E.2f the INLINE block that carries no .py at all was re-registered too (keyed by its full command)" \
  || bad "E.2f the inline no-.py registration was not restored — the identity key does not cover that shape"

# The upgrade must not INVENT registrations the template does not have.
EXTRA="$( comm -13 "$WORK/tpl.keys" "$WORK/hist.post.keys" )"
[ -z "$EXTRA" ] \
  && ok "E.2g the upgrade added nothing the template does not declare" \
  || { bad "E.2g the upgrade registered names absent from the template:"; printf '%s\n' "$EXTRA" | sed 's/^/         /' >&2; }

# MULTIPLICITY, not the set: hist.post.keys is deduplicated by construction, so
# `uniq -d` over it is always empty and the assertion could never fail.
_keybag "$A/.claude/settings.json" > "$WORK/hist.post.bag"
DUPES="$( uniq -d < "$WORK/hist.post.bag" )"
[ -z "$DUPES" ] \
  && ok "E.2h no registration is duplicated (counted with multiplicity — $( wc -l < "$WORK/hist.post.bag" | tr -d ' ' ) keys)" \
  || { bad "E.2h duplicated registrations after the merge:"; printf '%s\n' "$DUPES" | sed 's/^/         /' >&2; }

# --- E.2i  POSITIVE CONTROL for E.2h ---------------------------------------
# E.2h passing is only evidence if it CAN fail. Plant a duplicate in a sandbox
# copy and require the bag oracle to see it — and require the set oracle NOT
# to, which is the same measurement that condemns the previous form.
#
# The plant duplicates PreToolUse[0], NOT a block picked by name: an earlier
# draft duplicated the check_ledger_checkpoint block, which made this control
# depend on the MERGE having worked. Run against an upgrader that never
# registers that hook, the selector matched nothing, no duplicate was planted,
# and E.2i reported "the oracle is still vacuous" — blaming the oracle for a
# fixture that never fired. The key-count guard below turns that class of
# miss into a SCAFFOLD error, which is a different sentence on purpose.
DUP_FIX="$WORK/dupctl.json"
if jq '.hooks.PreToolUse += [ .hooks.PreToolUse[0] ]' \
     "$A/.claude/settings.json" > "$DUP_FIX" 2>/dev/null && [ -s "$DUP_FIX" ]; then
  _keybag "$DUP_FIX" > "$WORK/dupctl.bag"
  BAG_N="$( wc -l < "$WORK/hist.post.bag" | tr -d ' ' )"
  DUP_N="$( wc -l < "$WORK/dupctl.bag" | tr -d ' ' )"
  if [ "${DUP_N:-0}" -le "${BAG_N:-0}" ]; then
    bad "E.2i-SCAFFOLD the plant added no registration key ($BAG_N -> $DUP_N) — this control cannot measure the oracle, and its silence is NOT evidence about E.2h"
  else
    DUP_BAG="$( uniq -d < "$WORK/dupctl.bag" )"
    DUP_SET="$( _keyset "$DUP_FIX" | uniq -d )"
    [ -n "$DUP_BAG" ] \
      && ok "E.2i a planted duplicate registration IS reported by the multiplicity oracle ($BAG_N -> $DUP_N keys) — E.2h can fail" \
      || bad "E.2i a planted duplicate was NOT reported — E.2h is still vacuous and its green means nothing"
    [ -z "$DUP_SET" ] \
      && ok "E.2i-b the SET oracle stays silent on the very same planted duplicate — which is why E.2h could never fail before (rail round 1, P2)" \
      || bad "E.2i-b the set oracle reported a duplicate; this control no longer demonstrates the blind spot"
  fi
else
  bad "E.2i-SCAFFOLD could not plant the duplicate — E.2h has no positive control"
fi

# ---------------------------------------------------------------------------
# E.7  the adopter's own edit survived the merge
# ---------------------------------------------------------------------------
echo ""
echo "==> E.7 — an adopter-edited registration is PRESERVED, not re-canonicalized"
EDIT_TO="$( jq -r '[.hooks.PreToolUse[] | select((.hooks[0].command // "") | test("check_bash_safety")) | .hooks[0].timeout] | join(",")' "$A/.claude/settings.json" )"
[ "$EDIT_TO" = "4242" ] \
  && ok "E.7a the adopter's timeout=4242 on check_bash_safety.py survived the upgrade" \
  || bad "E.7a the adopter's edited timeout became '$EDIT_TO' (expected 4242) — the merge re-canonicalized a present registration"

BS_N="$( jq '[.hooks.PreToolUse[] | select((.hooks[0].command // "") | test("check_bash_safety"))] | length' "$A/.claude/settings.json" )"
[ "$BS_N" = "1" ] \
  && ok "E.7b and it was not duplicated by a second, canonical copy" \
  || bad "E.7b check_bash_safety.py now appears $BS_N times under PreToolUse"

# ---------------------------------------------------------------------------
# E.5  idempotency — a second upgrade changes nothing, byte for byte
# ---------------------------------------------------------------------------
echo ""
echo "==> E.5 — re-running the upgrade is a byte-level no-op"
SHA1="$( _sha "$A/.claude/settings.json" )"
_upgrade "$A" "$REPO_ROOT"
SHA2="$( _sha "$A/.claude/settings.json" )"
[ "$SHA1" = "$SHA2" ] \
  && ok "E.5a settings.json is byte-identical across two consecutive upgrades" \
  || bad "E.5a the second upgrade rewrote settings.json ($SHA1 -> $SHA2)"

grep -q "already present — settings.json untouched" "$_UP_LOG" \
  && ok "E.5b and the second run says so explicitly (it never opened the file for writing)" \
  || bad "E.5b the second run did not report the no-op (see $_UP_LOG)"

# ---------------------------------------------------------------------------
# E.3  RED CONTROL — the PRE-CURE upgrader leaves the finding uncured
# ---------------------------------------------------------------------------
echo ""
echo "==> E.3 — the pre-cure upgrader (git HEAD) does NOT register the hook"
RED_SRC="$WORK/red/src"
if _mk_source_copy "$RED_SRC" \
   && git -C "$REPO_ROOT" show HEAD:scripts/upgrade.sh > "$RED_SRC/scripts/upgrade.sh" 2>/dev/null \
   && [ -s "$RED_SRC/scripts/upgrade.sh" ] \
   && bash -n "$RED_SRC/scripts/upgrade.sh" 2>/dev/null; then

  # The plant is only a plant if HEAD really is the pre-cure text. If this
  # file is being run AFTER the cure landed, say so instead of asserting a
  # falsehood: the control has expired, it has not failed.
  if grep -q 'settings.base.json' "$RED_SRC/scripts/upgrade.sh" \
     && grep -q 'slurpfile tpl' "$RED_SRC/scripts/upgrade.sh"; then
    ok "E.3-SKIP git HEAD already contains the cure — the red control has expired (re-point it at the pre-cure commit to re-arm)"
  else
    RED="$WORK/red/adopter"
    _install "$RED"
    _strip_four "$RED" || scaffold "could not strip the red fixture"
    _upgrade "$RED" "$RED_SRC"
    _keyset "$RED/.claude/settings.json" > "$WORK/red.post.keys"

    grep -q "^PreToolUse check_ledger_checkpoint.py$" "$WORK/red.post.keys" \
      && bad "E.3a the PRE-CURE upgrader registered check_ledger_checkpoint.py — the finding does not reproduce, so E.2e is not evidence" \
      || ok "E.3a the pre-cure upgrader leaves check_ledger_checkpoint.py UNREGISTERED — the S328 finding reproduces"

    RED_MISSING_N="$( comm -23 "$WORK/tpl.keys" "$WORK/red.post.keys" | wc -l | tr -d ' ' )"
    [ "${RED_MISSING_N:-0}" -ge 1 ] \
      && ok "E.3b the pre-cure upgrader leaves $RED_MISSING_N template registration(s) missing (the cured one leaves 0)" \
      || bad "E.3b the pre-cure upgrader left nothing missing — the two upgraders are indistinguishable here"
  fi
else
  bad "E.3-SCAFFOLD could not build the pre-cure source copy — the red control did not run"
fi

# ---------------------------------------------------------------------------
# E.4  POSITIVE CONTROL — a name invented at runtime is registered
# ---------------------------------------------------------------------------
echo ""
echo "==> E.4 — a SYNTHETIC hook added to the template is registered (and removing it un-registers it)"
grep -q "$SYNTH" "$UPGRADE" \
  && bad "E.4a '$SYNTH' appears in upgrade.sh — pick another name; this control assumes the upgrader cannot know it" \
  || ok "E.4a '$SYNTH' appears nowhere in upgrade.sh, so only a template-derived roster can register it"

SYN_SRC="$WORK/synth/src"
if _mk_source_copy "$SYN_SRC"; then
  jq --arg cmd "bash \"\$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh\" $SYNTH" '
      .hooks.PreToolUse += [ { "_comment": "E.4 positive control — synthetic, template-only.",
                               "matcher": "Bash",
                               "hooks": [ { "type": "command", "command": $cmd, "timeout": 5 } ] } ]' \
     "$TEMPLATE" > "$SYN_SRC/templates/settings/settings.base.json.tmp" \
     && mv "$SYN_SRC/templates/settings/settings.base.json.tmp" "$SYN_SRC/templates/settings/settings.base.json"

  if jq -e --arg n "$SYNTH" '[.hooks.PreToolUse[] | select((.hooks[0].command // "") | test($n))] | length == 1' \
       "$SYN_SRC/templates/settings/settings.base.json" >/dev/null 2>&1; then
    ok "E.4b the synthetic registration was planted exactly once in the source copy's template"

    SYN="$WORK/synth/adopter"
    _install "$SYN"
    _upgrade "$SYN" "$SYN_SRC"
    _keyset "$SYN/.claude/settings.json" > "$WORK/syn.post.keys"

    grep -q "^PreToolUse $SYNTH$" "$WORK/syn.post.keys" \
      && ok "E.4c the upgrade registered the synthetic hook — the roster is READ from the template, not recalled" \
      || bad "E.4c the synthetic hook was NOT registered (see $_UP_LOG) — the derivation is not reading the template"

    grep -q "$SYNTH" "$_UP_LOG" \
      && ok "E.4d and the upgrade log names it" \
      || bad "E.4d the upgrade log never mentions $SYNTH (see $_UP_LOG)"

    # The NEGATIVE half: the SAME adopter upgraded from the UNMODIFIED tree
    # must not gain the synthetic name. Without this, E.4c could be satisfied
    # by an upgrader that registers everything it can think of.
    SYN2="$WORK/synth2/adopter"
    _install "$SYN2"
    _upgrade "$SYN2" "$REPO_ROOT"
    _keyset "$SYN2/.claude/settings.json" > "$WORK/syn2.post.keys"
    grep -q "$SYNTH" "$WORK/syn2.post.keys" \
      && bad "E.4e the UNMODIFIED source also registered $SYNTH — E.4c proves nothing" \
      || ok "E.4e the unmodified source does not register it — the template is what changed the outcome"
  else
    bad "E.4b the synthetic plant did not land in the copied template — E.4c would prove nothing"
  fi
else
  bad "E.4-SCAFFOLD could not build the synthetic source copy"
fi

# ---------------------------------------------------------------------------
# E.8  an unparseable shape is PRESERVED and NAMED, never coerced
# ---------------------------------------------------------------------------
echo ""
echo "==> E.8 — a non-array event value fails safe"
ODD="$WORK/odd/adopter"
_install "$ODD"
jq '.hooks.SubagentStart = {"not":"an array"}' "$ODD/.claude/settings.json" > "$ODD/.claude/s.tmp" \
  && mv "$ODD/.claude/s.tmp" "$ODD/.claude/settings.json"
_strip_four "$ODD" || scaffold "could not strip the odd fixture"
_upgrade "$ODD" "$REPO_ROOT"

jq -e '.hooks.SubagentStart == {"not":"an array"}' "$ODD/.claude/settings.json" >/dev/null 2>&1 \
  && ok "E.8a the non-array event value was PRESERVED exactly, not coerced into a list" \
  || bad "E.8a the merge rewrote .hooks.SubagentStart — an unparseable shape must fail safe"

grep -q "is not an array" "$_UP_LOG" \
  && ok "E.8b and the skip was NAMED in the log (a silent skip is how a surprise becomes permanent)" \
  || bad "E.8b the upgrade did not name the skipped event (see $_UP_LOG)"

_keyset "$ODD/.claude/settings.json" > "$WORK/odd.post.keys"
grep -q "^PreToolUse check_ledger_checkpoint.py$" "$WORK/odd.post.keys" \
  && ok "E.8c the OTHER events were still merged — one odd event does not disable the whole step" \
  || bad "E.8c the odd event aborted the entire merge"

# ---------------------------------------------------------------------------
# E.10  an EXPLICIT falsy container is a decision, not an absence
# ---------------------------------------------------------------------------
# `x // []` reads null and false as "empty", which is right for a key that was
# never written and WRONG for one the adopter set on purpose. E.8 covers the
# shape that is obviously foreign ({"not":"an array"}); these two are the
# shapes that LOOK like emptiness, and before the round-1 cure both were
# silently overwritten with the full template roster.
echo ""
echo "==> E.10 — an explicit null/false container is PRESERVED, not read as 'absent'"

# (a) one EVENT set to null, with a --dry-run leg: the preserved event must be
#     named there too, or the adopter cannot review the decision before it runs.
NUL="$WORK/nullev/adopter"
_install "$NUL"
# ORDER MATTERS: _strip_four contains `del(.hooks.PreCompact)`, so planting the
# null first would have it deleted right back out and the fixture would test
# the ABSENT case under the name of the explicit one. Strip, THEN plant.
_strip_four "$NUL" || scaffold "could not strip the null-event fixture"
jq '.hooks.PreCompact = null' "$NUL/.claude/settings.json" > "$NUL/.claude/s.tmp" \
  && mv "$NUL/.claude/s.tmp" "$NUL/.claude/settings.json"
jq -e '.hooks | has("PreCompact") and (.PreCompact == null)' "$NUL/.claude/settings.json" >/dev/null 2>&1 \
  || scaffold "the null-event fixture is not what E.10 assumes (.hooks.PreCompact must be PRESENT and null)"

_upgrade "$NUL" "$REPO_ROOT" --dry-run
grep -q "event 'PreCompact' in settings.json is not an array (found: null)" "$_UP_LOG" \
  && ok "E.10a --dry-run NAMES the explicitly-null event it will leave alone (with its type)" \
  || bad "E.10a --dry-run did not name the null event (see $_UP_LOG)"

_upgrade "$NUL" "$REPO_ROOT"
jq -e '.hooks.PreCompact == null' "$NUL/.claude/settings.json" >/dev/null 2>&1 \
  && ok "E.10b an event explicitly set to null survived the upgrade — it was NOT read as an absent key and refilled" \
  || bad "E.10b .hooks.PreCompact was overwritten; an explicit null is a decision, not an absence"

_keyset "$NUL/.claude/settings.json" > "$WORK/nullev.post.keys"
grep -q "^PreToolUse check_ledger_checkpoint.py$" "$WORK/nullev.post.keys" \
  && ok "E.10c the other events still merged — one preserved container does not disable the step" \
  || bad "E.10c the null event aborted the rest of the merge"

# (b) the whole .hooks container set to null: nothing may be written at all.
NULR="$WORK/nullroot/adopter"
_install "$NULR"
jq '.hooks = null' "$NULR/.claude/settings.json" > "$NULR/.claude/s.tmp" \
  && mv "$NULR/.claude/s.tmp" "$NULR/.claude/settings.json"
# Without this, a failed plant leaves a COMPLETE fresh install, whose merge is
# legitimately a no-op — and E.10d's byte-identity assertion would pass while
# measuring nothing.
jq -e '(.hooks == null) and (. | has("hooks"))' "$NULR/.claude/settings.json" >/dev/null 2>&1 \
  || scaffold "the null-root fixture is not what E.10 assumes (.hooks must be PRESENT and null)"
NULR_SHA="$( _sha "$NULR/.claude/settings.json" )"
_upgrade "$NULR" "$REPO_ROOT"

[ "$NULR_SHA" = "$( _sha "$NULR/.claude/settings.json" )" ] \
  && ok "E.10d an explicit \"hooks\": null left settings.json byte-identical — the merge wrote nothing into it" \
  || bad "E.10d the merge REWROTE a settings.json whose .hooks was explicitly null"

grep -q "a .hooks that is not an object (found: null)" "$_UP_LOG" \
  && ok "E.10e and the skip was NAMED with the type it found" \
  || bad "E.10e the upgrade did not name the explicitly-null .hooks (see $_UP_LOG)"

# ---------------------------------------------------------------------------
# E.11  a structurally invalid TEMPLATE refuses the whole merge
# ---------------------------------------------------------------------------
# The adopter's file gets per-event tolerance (E.8/E.10). The template does not:
# it is the artifact that DEFINES the roster, so an event value that is not an
# array of blocks means we do not know the right answer. Both ways the old
# guard let that through were silent — an OBJECT value has its inner values
# iterated by `.[]?` and can APPEND something never declared as a block, and a
# SCALAR value makes `.[]?` yield nothing so the event is DROPPED.
echo ""
echo "==> E.11 — a template whose event value is not an array is refused, and named"
SMUGGLED="check_zz_smuggled_e11.py"
BAD_SRC="$WORK/badtpl/src"
if _mk_source_copy "$BAD_SRC"; then
  jq --arg cmd "bash \"\$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh\" $SMUGGLED" '
      .hooks.PreCompact   = { "smuggled": { "matcher": "",
                              "hooks": [ { "type": "command", "command": $cmd, "timeout": 5 } ] } }
    | .hooks.ConfigChange = 42' \
     "$TEMPLATE" > "$BAD_SRC/templates/settings/settings.base.json.tmp" \
     && mv "$BAD_SRC/templates/settings/settings.base.json.tmp" "$BAD_SRC/templates/settings/settings.base.json"

  if jq -e '(.hooks.PreCompact | type) == "object" and (.hooks.ConfigChange | type) == "number"' \
       "$BAD_SRC/templates/settings/settings.base.json" >/dev/null 2>&1; then
    ok "E.11a the malformed template was planted (one object-valued event, one scalar-valued)"

    BAD="$WORK/badtpl/adopter"
    _install "$BAD"
    _strip_four "$BAD" || scaffold "could not strip the bad-template fixture"
    BAD_SHA="$( _sha "$BAD/.claude/settings.json" )"
    _upgrade "$BAD" "$BAD_SRC"

    [ "$BAD_SHA" = "$( _sha "$BAD/.claude/settings.json" )" ] \
      && ok "E.11b the upgrade wrote NOTHING to settings.json — a malformed roster is refused whole, not merged in part" \
      || bad "E.11b settings.json was modified from a template with a non-array event value"

    grep -q "PreCompact (object)" "$_UP_LOG" \
      && ok "E.11c the object-valued event is NAMED with the type found" \
      || bad "E.11c the object-valued event was not named (see $_UP_LOG)"

    grep -q "ConfigChange (number)" "$_UP_LOG" \
      && ok "E.11d the scalar-valued event is named too — every offender, not just the first" \
      || bad "E.11d the scalar-valued event was not named (see $_UP_LOG)"

    # E.11e is only a statement about SMUGGLING if the name could not have
    # arrived any other way — same reasoning as E.4a.
    grep -q "$SMUGGLED" "$UPGRADE" \
      && bad "E.11e-pre '$SMUGGLED' appears in upgrade.sh — pick another name; the smuggling check assumes the upgrader cannot know it" \
      || ok "E.11e-pre '$SMUGGLED' appears nowhere in upgrade.sh, so only the malformed template could introduce it"

    _keyset "$BAD/.claude/settings.json" > "$WORK/badtpl.post.keys"
    grep -q "$SMUGGLED" "$WORK/badtpl.post.keys" \
      && bad "E.11e '$SMUGGLED' was REGISTERED — the object's VALUE was consumed as if it were a hooks block" \
      || ok "E.11e nothing was smuggled in through the object's values"

    # ANTI-VACUITY. E.11b would pass for free if this fixture had nothing left
    # to register. Upgrading the SAME adopter from the UNMODIFIED tree must
    # change the file — that is what makes 'unchanged' evidence.
    _upgrade "$BAD" "$REPO_ROOT"
    [ "$BAD_SHA" != "$( _sha "$BAD/.claude/settings.json" )" ] \
      && ok "E.11f the same adopter DOES get written when the template is well-formed — so E.11b measured a refusal, not an empty workload" \
      || bad "E.11f the adopter was unchanged even with a valid template; E.11b proves nothing"
  else
    bad "E.11a the malformed template did not land in the copied template — E.11b would prove nothing"
  fi
else
  bad "E.11-SCAFFOLD could not build the malformed-template source copy"
fi

# ---------------------------------------------------------------------------
# E.12  a MALFORMED BLOCK inside a valid event array is refused too
# ---------------------------------------------------------------------------
# E.11 closes the event level; this is the same rule one level down. A block
# the key-derivation cannot identify (null, {}, {"hooks": []}, an entry with no
# command) yields zero keys, and the reduction used to SKIP it while merging
# its well-formed siblings — a partial roster arriving through a second door.
echo ""
echo "==> E.12 — an unidentifiable block refuses the merge instead of being skipped"
BLK_SRC="$WORK/badblk/src"
if _mk_source_copy "$BLK_SRC"; then
  # PreCompact keeps its real (valid) block and gains a null one, so the
  # all-or-nothing claim below is about a REAL sibling, not a synthetic pair.
  jq '.hooks.PreCompact += [null]' "$TEMPLATE" > "$BLK_SRC/templates/settings/settings.base.json.tmp" \
    && mv "$BLK_SRC/templates/settings/settings.base.json.tmp" "$BLK_SRC/templates/settings/settings.base.json"

  if jq -e '(.hooks.PreCompact | length) == 2 and (.hooks.PreCompact[1] == null)' \
       "$BLK_SRC/templates/settings/settings.base.json" >/dev/null 2>&1; then
    ok "E.12a the malformed block was planted next to a real one (PreCompact = [valid, null])"

    BLK="$WORK/badblk/adopter"
    _install "$BLK"
    _strip_four "$BLK" || scaffold "could not strip the bad-block fixture"
    BLK_SHA="$( _sha "$BLK/.claude/settings.json" )"
    _upgrade "$BLK" "$BLK_SRC"

    [ "$BLK_SHA" = "$( _sha "$BLK/.claude/settings.json" )" ] \
      && ok "E.12b the upgrade wrote NOTHING — an unidentifiable block is refused, not skipped past" \
      || bad "E.12b settings.json was modified despite an unidentifiable block in the template"

    grep -q "PreCompact\[1\]" "$_UP_LOG" \
      && ok "E.12c the offending block is named by event AND index" \
      || bad "E.12c the malformed block was not named with its index (see $_UP_LOG)"

    # The sharp claim: a bad block under PreCompact must also stop PreToolUse's
    # registration. Anything less is the partial roster this wave exists to end.
    _keyset "$BLK/.claude/settings.json" > "$WORK/badblk.post.keys"
    grep -q "^PreToolUse check_ledger_checkpoint.py$" "$WORK/badblk.post.keys" \
      && bad "E.12d an UNRELATED event was merged while a block elsewhere was unidentifiable — the template rule is all-or-nothing" \
      || ok "E.12d no other event was merged either — the refusal is whole-template, not per-block"
  else
    bad "E.12a the malformed block did not land in the copied template — E.12b would prove nothing"
  fi
else
  bad "E.12-SCAFFOLD could not build the malformed-block source copy"
fi

# ---------------------------------------------------------------------------
# E.13  a PRESERVED event is never reported as "everything already present"
# ---------------------------------------------------------------------------
# The adopter here is COMPLETE except that one event is an explicit null. That
# makes _adds == 0, and the summary used to read that as completeness — while
# the hook the template declares under the preserved event is exactly the one
# missing. That sentence is the line an adopter reads for reassurance, so
# getting it wrong is worse than printing nothing.
echo ""
echo "==> E.13 — a preserved event makes the result PARTIAL, and the summary says so"
PRT="$WORK/partial/adopter"
_install "$PRT"
jq '.hooks.PreCompact = null' "$PRT/.claude/settings.json" > "$PRT/.claude/s.tmp" \
  && mv "$PRT/.claude/s.tmp" "$PRT/.claude/settings.json"
jq -e '(.hooks | has("PreCompact")) and (.hooks.PreCompact == null)' "$PRT/.claude/settings.json" >/dev/null 2>&1 \
  || scaffold "the partial fixture is not what E.13 assumes (.hooks.PreCompact PRESENT and null)"
_upgrade "$PRT" "$REPO_ROOT"

grep -q "every framework hook registration in the template is already present" "$_UP_LOG" \
  && bad "E.13a the run claimed COMPLETENESS while a preserved event left a template hook unregistered" \
  || ok "E.13a the completeness sentence was NOT printed — the result is not complete and does not say it is"

grep -q "check_precompact_continuity.py" "$_UP_LOG" \
  && ok "E.13b the hook the preserved event leaves UNREGISTERED is named" \
  || bad "E.13b the absent hook was never named (see $_UP_LOG)"

grep -q "PRESERVED:" "$_UP_LOG" \
  && ok "E.13c and the outcome is labelled PRESERVED/PARTIAL rather than reported as a no-op" \
  || bad "E.13c the partial outcome was not labelled (see $_UP_LOG)"

# CONTROL: the completeness sentence must survive where it is TRUE. Without
# this, E.13a would also pass for a build that simply deleted the sentence.
_upgrade "$A" "$REPO_ROOT"
grep -q "every framework hook registration in the template is already present" "$_UP_LOG" \
  && ok "E.13d a genuinely complete adopter DOES still get the completeness sentence — E.13a is about accuracy, not about deleting the line" \
  || bad "E.13d the completeness sentence no longer prints even when it is true"

# ---------------------------------------------------------------------------
# E.14  the CEREMONY selects the template (rail round 6, P1)
# ---------------------------------------------------------------------------
# install.sh builds a `--ceremony user` adopter from settings.user.json — a
# profile that deliberately omits the governance hooks that block edits or
# need GPG/sentinel infrastructure. An upgrade that derives from
# settings.base.json regardless would re-register exactly those, turning the
# advisory profile into the maintainer profile in the one population that
# chose not to have it. The fixture is a REAL user-ceremony install (the cached
# fixture is maintainer, so it cannot be reused), and the ceremony reaches the
# upgrade the way it does in the field: RECORDED in .claude/.install-state.json,
# no flag on the upgrade call. E.14i is the positive control that keeps E.14f
# honest: the same adopter with its record rewritten to maintainer MUST
# receive the base-only registrations.
echo ""
echo "==> E.14 — a --ceremony user adopter is upgraded from settings.user.json, never from settings.base.json"
TEMPLATE_USER="$REPO_ROOT/templates/settings/settings.user.json"
_keyset "$TEMPLATE_USER" > "$WORK/tpl.user.keys"
comm -23 "$WORK/tpl.keys" "$WORK/tpl.user.keys" > "$WORK/tpl.base-only.keys"
BASE_ONLY_N="$( wc -l < "$WORK/tpl.base-only.keys" | tr -d ' ' )"
[ "${BASE_ONLY_N:-0}" -ge 10 ] \
  && ok "E.14a settings.user.json omits $BASE_ONLY_N of the base template's registrations — the profile this case protects exists, so E.14f can fail" \
  || bad "E.14a settings.user.json omits only ${BASE_ONLY_N:-0} base registrations — the user profile no longer differs enough for this case to mean anything"

UA="$WORK/user/adopter"
mkdir -p "$UA"
( cd "$UA" && git init -q ) || scaffold "git init failed in $UA"
bash "$INSTALL" "$UA" --profile core --ceremony user > "$UA.install.log" 2>&1 \
  || { tail -30 "$UA.install.log" >&2; scaffold "install.sh --ceremony user failed for $UA"; }

jq -e '.request.ceremony == "user"' "$UA/.claude/.install-state.json" >/dev/null 2>&1 \
  && ok "E.14b the install RECORDED ceremony=user in .claude/.install-state.json — the path the upgrade resolves, no flag needed" \
  || bad "E.14b .claude/.install-state.json does not record ceremony=user; the fixture is not a user-ceremony install"

_keyset "$UA/.claude/settings.json" > "$WORK/user.pre.keys"
if diff -q "$WORK/tpl.user.keys" "$WORK/user.pre.keys" >/dev/null 2>&1; then
  ok "E.14c a fresh user install's registration set EQUALS settings.user.json's"
else
  bad "E.14c fresh user install != settings.user.json registration set"
  diff "$WORK/tpl.user.keys" "$WORK/user.pre.keys" | head -10 >&2
fi

# ... and strip the env key the user template ships WITH its hooks (rail
# round 7, P1): a pre-PLAN-124 user adopter has neither the registration nor
# the key, and the hook without the key is the BLOCKING variant. The key is
# DERIVED — the user template's env keys minus the base template's — so this
# case protects whatever the user profile declares for itself, by name.
USER_ONLY_ENV="$( comm -23 <( jq -r '.env | keys[]' "$TEMPLATE_USER" | sort ) <( jq -r '.env | keys[]' "$TEMPLATE" | sort ) )"
ENV_KEY="$( printf '%s\n' "$USER_ONLY_ENV" | head -1 )"
[ -n "$ENV_KEY" ] || scaffold "settings.user.json declares no env key of its own — E.14j has nothing to protect"
ENV_VAL="$( jq -r --arg k "$ENV_KEY" '.env[$k]' "$TEMPLATE_USER" )"
jq --arg k "$ENV_KEY" 'del(.env[$k])' "$UA/.claude/settings.json" > "$UA/.claude/settings.json.stripped" \
  && mv "$UA/.claude/settings.json.stripped" "$UA/.claude/settings.json" \
  || scaffold "could not strip env.$ENV_KEY from the user adopter"
jq -e --arg k "$ENV_KEY" '.env | has($k) | not' "$UA/.claude/settings.json" >/dev/null 2>&1 \
  || scaffold "the strip of env.$ENV_KEY did not bite"

# Strip a registration the USER template DOES declare, so the merge has real
# work to do — otherwise E.14f could pass for a build that skipped the merge
# entirely under ceremony=user.
STRIP_LINE="$( grep '^PreToolUse ' "$WORK/tpl.user.keys" | grep '\.py$' | head -1 )"
STRIP_NAME="${STRIP_LINE#PreToolUse }"
[ -n "$STRIP_NAME" ] || scaffold "settings.user.json declares no PreToolUse .py registration to strip"
jq --arg n "$STRIP_NAME" 'del(.hooks.PreToolUse[] | select((.hooks[0].command // "") | test($n)))' \
  "$UA/.claude/settings.json" > "$UA/.claude/settings.json.stripped" \
  && mv "$UA/.claude/settings.json.stripped" "$UA/.claude/settings.json" \
  || scaffold "could not strip $STRIP_NAME from the user adopter"
if _keyset "$UA/.claude/settings.json" | grep -q "^PreToolUse $STRIP_NAME\$"; then
  scaffold "the strip of $STRIP_NAME did not bite"
fi

_upgrade "$UA" "$REPO_ROOT"
[ "$_UP_RC" -eq 0 ] \
  && ok "E.14d the upgrade of the user adopter succeeded" \
  || bad "E.14d the upgrade exited $_UP_RC (see $_UP_LOG)"

_keyset "$UA/.claude/settings.json" > "$WORK/user.post.keys"
grep -q "^PreToolUse $STRIP_NAME\$" "$WORK/user.post.keys" \
  && ok "E.14e the stripped registration ($STRIP_NAME) was re-registered — the merge is LIVE under ceremony=user, not skipped" \
  || bad "E.14e $STRIP_NAME is still missing after the upgrade — the user-ceremony merge did nothing (see $_UP_LOG)"

LEAKED="$( comm -12 "$WORK/tpl.base-only.keys" "$WORK/user.post.keys" )"
if [ -z "$LEAKED" ]; then
  ok "E.14f none of the $BASE_ONLY_N base-only registrations reached the user adopter — the advisory profile stayed advisory"
else
  bad "E.14f the upgrade registered base-only hooks into a user-ceremony adopter (rail round 6, P1):"
  printf '%s\n' "$LEAKED" | sed 's/^/         /' >&2
fi

if diff -q "$WORK/tpl.user.keys" "$WORK/user.post.keys" >/dev/null 2>&1; then
  ok "E.14g after the upgrade the user adopter's set EQUALS settings.user.json's again — restored, and nothing invented"
else
  bad "E.14g user adopter != settings.user.json after the upgrade"
  diff "$WORK/tpl.user.keys" "$WORK/user.post.keys" | head -10 >&2
fi

grep -q "settings.user.json" "$_UP_LOG" \
  && ok "E.14h the upgrade NAMED the template it derived from (settings.user.json)" \
  || bad "E.14h the upgrade log never names settings.user.json (see $_UP_LOG)"

if [ "$( jq -r --arg k "$ENV_KEY" '.env[$k] // "ABSENT"' "$UA/.claude/settings.json" )" = "$ENV_VAL" ]; then
  ok "E.14j env.$ENV_KEY=$ENV_VAL came back WITH the hooks — the setting that keeps the user profile advisory travels with the roster (rail round 7, P1)"
else
  bad "E.14j env.$ENV_KEY is not '$ENV_VAL' after the upgrade — the hooks arrived without the setting they read (see $_UP_LOG)"
fi

UM="$WORK/user/adopter-as-maintainer"
cp -R "$UA" "$UM" || scaffold "could not copy the user adopter for the E.14 control"
jq '.request.ceremony = "maintainer"' "$UM/.claude/.install-state.json" > "$UM/.claude/.install-state.json.tmp" \
  && mv "$UM/.claude/.install-state.json.tmp" "$UM/.claude/.install-state.json" \
  || scaffold "could not rewrite the ceremony record for the E.14 control"
jq --arg k "$ENV_KEY" 'del(.env[$k])' "$UM/.claude/settings.json" > "$UM/.claude/settings.json.stripped" \
  && mv "$UM/.claude/settings.json.stripped" "$UM/.claude/settings.json" \
  || scaffold "could not strip env.$ENV_KEY from the E.14 control"
_upgrade "$UM" "$REPO_ROOT"
_keyset "$UM/.claude/settings.json" > "$WORK/user-as-maint.post.keys"
if jq -e --arg k "$ENV_KEY" '.env | has($k) | not' "$UM/.claude/settings.json" >/dev/null 2>&1; then
  ok "E.14k CONTROL — under a maintainer record env.$ENV_KEY is NOT re-applied (settings.base.json does not declare it): the env merge is template-driven, not a literal"
else
  bad "E.14k CONTROL — env.$ENV_KEY appeared under a maintainer record; something other than the selected template wrote it"
fi
CTRL_N="$( comm -12 "$WORK/tpl.base-only.keys" "$WORK/user-as-maint.post.keys" | wc -l | tr -d ' ' )"
[ "${CTRL_N:-0}" -eq "$BASE_ONLY_N" ] \
  && ok "E.14i CONTROL — with the record rewritten to maintainer the same adopter DOES receive all $BASE_ONLY_N base-only registrations: the choice is driven by the recorded ceremony, and E.14f can fail" \
  || bad "E.14i CONTROL — expected $BASE_ONLY_N base-only registrations under a maintainer record, got ${CTRL_N:-0} (upgrade rc=$_UP_RC, see $_UP_LOG)"

# ---------------------------------------------------------------------------
# E.15  an INFERRED ceremony is not a recorded one (rail round 8, P1)
# ---------------------------------------------------------------------------
# No install-state, no flag: the resolver answers `user` only as a root-write
# fail-safe. That adopter is the pre-Wave-B historical install, ceremony
# unknown — it must get NO hook registration at all (round 9: a shared hook's
# behaviour can depend on a setting the profiles disagree on, through code the
# upgrader cannot read), only the settings both profiles declare with the same
# value, and a NOTE with the opt-in; and its --dry-run must write nothing.
# The fixture is the cached MAINTAINER install with its install-state removed
# and one shared hook, one base-only hook and one shared setting stripped;
# E.15f/E.15g are the controls: the same fixture WITH --ceremony gets each
# profile in full.
echo ""
echo "==> E.15 — with no recorded ceremony the upgrade registers NO hooks, applies only the shared settings, and says so"
BO_LINE="$( grep '^PreToolUse ' "$WORK/tpl.base-only.keys" | grep '\.py$' | head -1 )"
BO_NAME="${BO_LINE#PreToolUse }"
[ -n "$BO_NAME" ] || scaffold "no base-only PreToolUse registration to withhold in E.15"
SHARED_ENV_KEY="$( jq -r --slurpfile u "$TEMPLATE_USER" '.env | to_entries[] | select(.value == $u[0].env[.key]) | .key' "$TEMPLATE" | sort | head -1 )"
[ -n "$SHARED_ENV_KEY" ] || scaffold "the two templates share no env key with the same value — E.15d has nothing to restore"
SHARED_ENV_VAL="$( jq -r --arg k "$SHARED_ENV_KEY" '.env[$k]' "$TEMPLATE" )"

_mk_unknown() {  # $1=dir  — cached maintainer install, ceremony record removed, three strips
  _install "$1"
  rm -f "$1/.claude/.install-state.json"
  jq --arg a "$STRIP_NAME" --arg b "$BO_NAME" --arg k "$SHARED_ENV_KEY" '
      del(.hooks.PreToolUse[] | select((.hooks[0].command // "") | test($a)))
    | del(.hooks.PreToolUse[] | select((.hooks[0].command // "") | test($b)))
    | del(.env[$k])' "$1/.claude/settings.json" > "$1/.claude/settings.json.stripped" \
    && mv "$1/.claude/settings.json.stripped" "$1/.claude/settings.json" \
    || scaffold "could not build the unknown-ceremony fixture in $1"
  [ ! -e "$1/.claude/.install-state.json" ] || scaffold "install-state still present in $1"
}

UK="$WORK/unknown/adopter"
_mk_unknown "$UK"
_keyset "$UK/.claude/settings.json" | grep -q "^PreToolUse $BO_NAME\$" && scaffold "the base-only strip did not bite"
_upgrade "$UK" "$REPO_ROOT"

grep -q "ceremony UNKNOWN" "$_UP_LOG" \
  && ok "E.15a the upgrade NAMED the unknown ceremony and the opt-in ($( grep -o 'WITHHELD: [^.]*' "$_UP_LOG" | head -1 ))" \
  || bad "E.15a the upgrade never said the ceremony was unknown (see $_UP_LOG)"

_keyset "$UK/.claude/settings.json" > "$WORK/unknown.post.keys"
grep -q "^PreToolUse $STRIP_NAME\$" "$WORK/unknown.post.keys" \
  && bad "E.15b the stripped registration ($STRIP_NAME) was RE-REGISTERED for an unknown ceremony — a hook the profiles share can still block under one of them (rail round 9)" \
  || ok "E.15b the stripped registration ($STRIP_NAME) stays WITHHELD — no hook is registered until the ceremony is stated"

grep -q "^PreToolUse $BO_NAME\$" "$WORK/unknown.post.keys" \
  && bad "E.15c the BASE-ONLY registration ($BO_NAME) reached an adopter whose ceremony is unknown" \
  || ok "E.15c the base-only registration ($BO_NAME) was WITHHELD — a possible user profile is not handed a blocker"

if [ "$( jq -r --arg k "$SHARED_ENV_KEY" '.env[$k] // "ABSENT"' "$UK/.claude/settings.json" )" = "$SHARED_ENV_VAL" ]; then
  ok "E.15d the SHARED setting env.$SHARED_ENV_KEY=$SHARED_ENV_VAL was restored"
else
  bad "E.15d env.$SHARED_ENV_KEY was not restored to '$SHARED_ENV_VAL' (see $_UP_LOG)"
fi

if jq -e --arg k "$ENV_KEY" '.env | has($k) | not' "$UK/.claude/settings.json" >/dev/null 2>&1; then
  ok "E.15e the USER-ONLY setting env.$ENV_KEY was NOT applied — a possible maintainer profile keeps its blocking matcher"
else
  bad "E.15e env.$ENV_KEY reached an adopter whose ceremony is unknown — a blocking matcher was turned into an allow"
fi

if grep -q "PARTIAL (ceremony unknown)" "$_UP_LOG" && ! grep -q "already present" "$_UP_LOG"; then
  ok "E.15h the summary says PARTIAL (ceremony unknown) and never claims completeness"
else
  bad "E.15h the unknown-ceremony summary is wrong (missing PARTIAL, or claims 'already present') — see $_UP_LOG"
fi

UKD="$WORK/unknown/adopter-dry"
_mk_unknown "$UKD"
DRY_UK_SHA="$( _sha "$UKD/.claude/settings.json" )"
_upgrade "$UKD" "$REPO_ROOT" --dry-run
if [ "$( _sha "$UKD/.claude/settings.json" )" = "$DRY_UK_SHA" ] && [ ! -e "$UKD/.claude.bak" ] \
   && ! find "$UKD/.claude" -name 'settings.template-shared.json' | grep -q .; then
  ok "E.15i --dry-run on an unknown-ceremony adopter wrote NOTHING (no .claude.bak, no derived file, settings.json byte-identical) — the no-write guarantee holds on this path too (rail round 9, P1)"
else
  bad "E.15i --dry-run on an unknown-ceremony adopter WROTE under the adopter (see $_UP_LOG)"
fi

UKM="$WORK/unknown/adopter-maintainer"
_mk_unknown "$UKM"
_upgrade "$UKM" "$REPO_ROOT" --ceremony maintainer
if _keyset "$UKM/.claude/settings.json" | grep -q "^PreToolUse $BO_NAME\$" \
   && jq -e --arg k "$ENV_KEY" '.env | has($k) | not' "$UKM/.claude/settings.json" >/dev/null 2>&1; then
  ok "E.15f CONTROL — the same fixture WITH --ceremony maintainer gets the base-only registration and NOT the user-only setting: the withholding is about provenance, not about the value"
else
  bad "E.15f CONTROL — with --ceremony maintainer the base-only registration is missing or the user-only setting appeared (see $_UP_LOG)"
fi

UKU="$WORK/unknown/adopter-user"
_mk_unknown "$UKU"
_upgrade "$UKU" "$REPO_ROOT" --ceremony user
if ! _keyset "$UKU/.claude/settings.json" | grep -q "^PreToolUse $BO_NAME\$" \
   && [ "$( jq -r --arg k "$ENV_KEY" '.env[$k] // "ABSENT"' "$UKU/.claude/settings.json" )" = "$ENV_VAL" ]; then
  ok "E.15g CONTROL — the same fixture WITH --ceremony user gets the user-only setting and NOT the base-only registration"
else
  bad "E.15g CONTROL — with --ceremony user the base-only registration appeared or the user-only setting is missing (see $_UP_LOG)"
fi

# ---------------------------------------------------------------------------
# E.9  the drift the second copy had already accumulated
# ---------------------------------------------------------------------------
echo ""
echo "==> E.9 — the pre-cure literal blocks had drifted from the template"
# The pre-cure text goes to a FILE, never down a pipe: `git show | python3 - `
# with a heredoc would have the heredoc shadow the pipe on stdin and python
# would read an empty program input, printing "0 0" forever green.
git -C "$REPO_ROOT" show HEAD:scripts/upgrade.sh > "$WORK/head-upgrade.sh" 2>/dev/null || true
DRIFT="$( python3 - "$TEMPLATE" "$WORK/head-upgrade.sh" <<'PY'
import json, re, sys
try:
    old = open(sys.argv[2], encoding="utf-8").read()
except OSError:
    print("0 0"); sys.exit(0)
tpl = json.load(open(sys.argv[1], encoding="utf-8"))
pairs = [("PreCompact","check_precompact_continuity"),("PostCompact","check_postcompact_reinject"),
         ("ConfigChange","check_config_change"),("SubagentStart","check_subagent_start"),
         ("Setup","check_setup_verification"),("SessionStart","check_compact_pinning")]
drift = found = 0
for ev, name in pairs:
    m = re.search(r'_reg\("%s"; "%s\\\\\.py"; (\{.*?\n  \})\)' % (ev, name), old, re.S)
    if not m:
        continue
    try:
        blk = json.loads(m.group(1))
    except ValueError:
        continue
    cand = [b for b in tpl["hooks"].get(ev, [])
            if any(name in (h.get("command") or "") for h in b.get("hooks", []))]
    if not cand:
        continue
    found += 1
    if json.dumps(blk, sort_keys=True) != json.dumps(cand[0], sort_keys=True):
        drift += 1
print("%d %d" % (found, drift))
PY
)" || DRIFT=""
DRIFT_FOUND="${DRIFT%% *}"; DRIFT_N="${DRIFT##* }"
if [ -n "$DRIFT" ] && [ "${DRIFT_FOUND:-0}" -ge 5 ]; then
  ok "E.9a extracted ${DRIFT_FOUND}/6 pre-cure literal blocks out of git HEAD"
  [ "${DRIFT_N:-0}" -ge 1 ] \
    && ok "E.9b ${DRIFT_N} of them had already DRIFTED from the template — the second copy was not merely redundant, it was rewriting adopters with stale text on every upgrade" \
    || ok "E.9b none had drifted at this commit (the class is still what the cure removes)"
else
  ok "E.9-SKIP could not extract the pre-cure literals (HEAD is past the cure) — informational only"
fi

echo ""
echo "=============================================================="
echo "RESULT: $PASS passed, $FAIL failed"
echo "=============================================================="
[ "$FAIL" -eq 0 ] || exit 1
exit 0
