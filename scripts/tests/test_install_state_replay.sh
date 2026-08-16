#!/usr/bin/env bash
# scripts/tests/test_install_state_replay.sh
# PLAN-153 Wave B items B1+B2 — install-state persistence + upgrade replay.
#
# Exercises:
#   B1-a  fresh install writes .claude/.install-state.json (schema v1):
#         verbatim argv, parsed flags, resolved placeholder map (incl.
#         quote/backslash round-trip), non-empty operations journal
#   B1-b  re-run updates in place: run_count increments, first_recorded_at
#         preserved, history grows, file stays valid JSON (atomic write)
#   B1-c  --dry-run never creates the state file ("no files modified")
#   B2-a  upgrade with NO flags replays the recorded --profile (core-only
#         install does NOT grow a frontend tree); state (re)written by
#         upgrade.sh with last_upgrade.replay_source == "replay" and the
#         ORIGINAL install request (placeholders/argv/ceremony) preserved
#   B2-b  explicit --profile beats the replayed value and is re-recorded
#   B2-c  BACK-COMPAT (debate C must-fix): state file DELETED (pre-Wave-B
#         population) => upgrade rc=0, NOT a no-op (backup + refresh ran),
#         fallback NOTE emitted, state file ACQUIRED post-upgrade
#   B2-d  garbage state file => rc=0, invalid-state NOTE, fallback, state
#         rewritten valid
#   B2-e  hostile-but-valid-JSON state (shell metacharacters in profile)
#         => charset validation rejects, NO replay, rc=0
#   B2-f  --dry-run upgrade resolves replay for the preview but does NOT
#         modify the state file; --no-replay disables replay entirely
#
# bash 3.2-safe. mktemp -d only (xdist/parallel safe). Exits 0 on success,
# non-zero on any failed assertion.
#
# Run:  bash scripts/tests/test_install_state_replay.sh ; echo rc=$?

set -uo pipefail   # NOT -e: we assert on command failures explicitly.

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SOURCE_DIR="$( cd "$SCRIPT_DIR/../.." && pwd )"
# Override points so the test can be pointed at staged/candidate scripts
# while they still live in a plan-staging mirror (PLAN-153 discipline).
# NOTE: an override must point INTO a full framework checkout — install.sh /
# upgrade.sh derive their source tree from their own resolved location.
INSTALL="${CEO_INSTALL_UNDER_TEST:-$SOURCE_DIR/scripts/install.sh}"
UPGRADE="${CEO_UPGRADE_UNDER_TEST:-$SOURCE_DIR/scripts/upgrade.sh}"

# Source-checkout installs warn-and-proceed on the self-SHA placeholder; make
# it explicit so the test is deterministic regardless of release-fill state.
export CEO_INSTALL_SKIP_SELF_SHA=1
# Never prompt for the RAG sidecar in a non-interactive test.
export CEO_RAG_INSTALL_PROMPT=0

if ! command -v python3 >/dev/null 2>&1; then
  echo "==> SKIP: python3 not installed (B1/B2 state machinery is python3-backed)"
  exit 0
fi

FAIL=0
PASS=0
WORKROOT="$( mktemp -d -t ceo-b1b2-XXXXXX )"
cleanup() { [ -n "${WORKROOT:-}" ] && rm -rf "$WORKROOT" 2>/dev/null || true; }
trap cleanup EXIT

ok()   { PASS=$((PASS+1)); printf '  ok   %s\n' "$1"; }
bad()  { FAIL=$((FAIL+1)); printf '  FAIL %s\n' "$1" >&2; }

# git-index-lock-safe init: small retry around `git init` (parallel CI hosts).
_git_init_retry() {
  local d="$1" n=0
  while [ "$n" -lt 5 ]; do
    if ( cd "$d" && git init -q 2>/dev/null ); then return 0; fi
    n=$((n+1)); sleep 1
  done
  ( cd "$d" && git init -q )
}

run_install() {
  # $1 = target, rest passed through. Log is a SIBLING of the target
  # (never inside it — WS4 user-ceremony guard would trip otherwise).
  local t="$1"; shift
  bash "$INSTALL" "$t" "$@" >"$t.install.log" 2>&1
}

run_upgrade() {
  local t="$1"; shift
  bash "$UPGRADE" "$t" --no-deprecation-warn "$@" >"$t.upgrade.log" 2>&1
}

# t9 P2: prior-generation schema bytes for the B2-c3/c4/hasher legs.
# Commit 9777a8d may be absent on a depth-1 CI checkout, but the v1.2.0
# tag ships the SAME generation (sha 574bd22e...) and ownership-nightly
# fetches it — try both. Unavailable fixture provenance is a SCAFFOLD
# FAILURE (bad), never a green SKIP: the leg would silently stop running.
prior_schema_bytes() {
  # $1 = destination file. rc 0 on success.
  git -C "$SOURCE_DIR" show 9777a8d:.claude/plans/DEBATE-SCHEMA.md \
    > "$1" 2>/dev/null && return 0
  git -C "$SOURCE_DIR" show v1.2.0:.claude/plans/DEBATE-SCHEMA.md \
    > "$1" 2>/dev/null && return 0
  return 1
}

fresh_install() {
  # $1 = leg tag, rest = install args. Echoes the target path.
  local tag="$1"; shift
  local t
  t="$( mktemp -d "$WORKROOT/tgt-$tag-XXXXXX" )"
  _git_init_retry "$t"
  if ! run_install "$t" "$@"; then
    echo "INSTALL_FAILED ($tag)" >&2
    tail -30 "$t.install.log" >&2
    return 1
  fi
  printf '%s\n' "$t"
}

STATE_REL=".claude/.install-state.json"

# Shared python assert runner: python3 - <state> <label> [extra args] <<PY.
# The heredoc script exits non-zero on the first failed assert and prints
# the reason; the caller converts rc into ok/bad.
py_assert() {
  local state="$1" label="$2"; shift 2
  if python3 - "$state" "$@" <<'PY'
import json, sys
state_path = sys.argv[1]
mode = sys.argv[2]
with open(state_path, "r", encoding="utf-8") as f:
    d = json.load(f)

def die(msg):
    sys.stderr.write("assert failed: %s\n" % msg)
    sys.exit(1)

if d.get("schema") != "ceo.install-state/v1":
    die("schema field")
if d.get("schema_version") != 1:
    die("schema_version")
req = d.get("request")
if not isinstance(req, dict):
    die("request not a dict")

if mode == "fresh":
    exp_owner, exp_deploy = sys.argv[3], sys.argv[4]
    exp_argv = sys.argv[5:]
    if d.get("run_count") != 1: die("run_count != 1 (got %r)" % d.get("run_count"))
    if d.get("tool", {}).get("name") != "install.sh": die("tool.name")
    if req.get("profile") != "core": die("request.profile (got %r)" % req.get("profile"))
    if req.get("mode") != "copy": die("request.mode")
    if req.get("stack") != "none": die("request.stack")
    if req.get("stack_explicit") is not False: die("stack_explicit")
    if req.get("ceremony") != "maintainer": die("ceremony")
    if req.get("verify") is not False: die("verify")
    ph = req.get("placeholders")
    if not isinstance(ph, dict): die("placeholders not a dict")
    if ph.get("OWNER_NAME") != exp_owner: die("OWNER_NAME roundtrip (got %r)" % ph.get("OWNER_NAME"))
    if ph.get("DEPLOY_COMMAND") != exp_deploy: die("DEPLOY_COMMAND roundtrip")
    if "PROJECT_NAME" not in ph: die("deterministic-default PROJECT_NAME missing")
    if "CITY" in ph: die("empty placeholder CITY should be omitted")
    if req.get("argv") != exp_argv: die("argv verbatim (got %r)" % req.get("argv"))
    ops = [o.get("op") for o in d.get("operations", [])]
    for needed in ("install_team_rosters", "install_skills", "install_hooks",
                   "install_scripts", "build_settings", "write_install_manifest"):
        if needed not in ops: die("operation %s not journaled (ops=%r)" % (needed, ops))
    details = [o.get("detail") for o in d.get("operations", []) if o.get("op") == "install_skills"]
    if "core" not in details: die("install_skills core detail")
    if "frontend" in details: die("frontend skills journaled on a core-only install")
    if d.get("result", {}).get("install_succeeded") is not True: die("result.install_succeeded")
elif mode == "rerun":
    exp_first = sys.argv[3]
    if d.get("run_count") != 2: die("run_count != 2 (got %r)" % d.get("run_count"))
    if d.get("first_recorded_at") != exp_first: die("first_recorded_at not preserved")
    if not d.get("history"): die("history empty after rerun")
elif mode == "replayed-upgrade":
    if d.get("tool", {}).get("name") != "upgrade.sh": die("tool.name after upgrade")
    lu = d.get("last_upgrade")
    if not isinstance(lu, dict): die("last_upgrade missing")
    if lu.get("replay_source") != "replay": die("replay_source (got %r)" % lu.get("replay_source"))
    if req.get("profile") != "core": die("request.profile after replayed upgrade")
    ph = req.get("placeholders")
    if not isinstance(ph, dict) or "OWNER_NAME" not in ph:
        die("install placeholders NOT preserved through upgrade rewrite")
    if not req.get("argv"): die("original install argv NOT preserved through upgrade rewrite")
    ops = [o.get("op") for o in d.get("operations", [])]
    for needed in ("refresh_target", "refresh_protocol_pointer", "rewrite_baseline_manifest"):
        if needed not in ops: die("upgrade op %s not journaled (ops=%r)" % (needed, ops))
elif mode == "explicit-upgrade":
    if req.get("profile") != "core,frontend": die("explicit --profile not re-recorded")
elif mode == "acquired":
    if d.get("tool", {}).get("name") != "upgrade.sh": die("tool.name")
    if "synthesized" not in str(req.get("note", "")): die("synthesized note missing on acquired state")
    if req.get("profile") != "core,frontend": die("fallback default profile not recorded")
    lu = d.get("last_upgrade", {})
    if lu.get("replay_source") != "fallback-no-state": die("replay_source (got %r)" % lu.get("replay_source"))
elif mode == "valid":
    pass
else:
    die("unknown assert mode %s" % mode)
sys.exit(0)
PY
  then ok "$label"; else bad "$label"; fi
}

# ===========================================================================
echo "== B1-a: fresh install records the original request + operations =="
# ===========================================================================
OWNER_VAL='Ada "Quote" Backslash\ OMalley'
DEPLOY_VAL='make deploy && echo done'
T_A="$( fresh_install a --profile core --owner "$OWNER_VAL" --deploy-command "$DEPLOY_VAL" )" || exit 1
STATE_A="$T_A/$STATE_REL"

if [ -f "$STATE_A" ]; then ok "state file created"; else bad "state file created"; fi
# exp argv = exactly what run_install passed after the target path...
# (target itself IS part of argv — install.sh records the verbatim argv,
# which here is: <target> --profile core --owner <v> --deploy-command <v>)
py_assert "$STATE_A" "B1-a full state assertions" fresh "$OWNER_VAL" "$DEPLOY_VAL" \
  "$T_A" --profile core --owner "$OWNER_VAL" --deploy-command "$DEPLOY_VAL"
if [ ! -d "$T_A/.claude/skills/frontend" ]; then
  ok "core-only install has no frontend tree (precondition for B2-a)"
else
  bad "core-only install has no frontend tree (precondition for B2-a)"
fi

# ===========================================================================
echo "== B1-b: re-run updates in place (run_count, first_recorded_at) =="
# ===========================================================================
FIRST_AT="$( python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["first_recorded_at"])' "$STATE_A" )"
sleep 1  # ensure a written_at tick is possible; not asserted, just realistic
if run_install "$T_A" --profile core; then ok "re-run install rc=0"; else bad "re-run install rc=0"; fi
py_assert "$STATE_A" "B1-b rerun assertions" rerun "$FIRST_AT"

# ===========================================================================
echo "== B1-c: --dry-run writes NO state file =="
# ===========================================================================
T_C="$( mktemp -d "$WORKROOT/tgt-dry-XXXXXX" )"
_git_init_retry "$T_C"
if run_install "$T_C" --dry-run --profile core; then ok "dry-run rc=0"; else bad "dry-run rc=0"; fi
if [ ! -e "$T_C/$STATE_REL" ]; then ok "dry-run wrote no state file"; else bad "dry-run wrote no state file"; fi

# ===========================================================================
echo "== B2-a: upgrade with no flags REPLAYS the recorded profile =="
# ===========================================================================
if run_upgrade "$T_A"; then ok "replayed upgrade rc=0"; else bad "replayed upgrade rc=0"; fi
if grep -q 'REPLAY: --profile core' "$T_A.upgrade.log"; then
  ok "REPLAY note emitted for --profile core"
else
  bad "REPLAY note emitted for --profile core"; tail -20 "$T_A.upgrade.log" >&2
fi
if grep -q '^    Profile: core$' "$T_A.upgrade.log"; then
  ok "banner shows replayed Profile: core"
else
  bad "banner shows replayed Profile: core"
fi
if [ ! -d "$T_A/.claude/skills/frontend" ]; then
  ok "replay prevented the default core,frontend from installing frontend"
else
  bad "replay prevented the default core,frontend from installing frontend"
fi
py_assert "$STATE_A" "B2-a state rewritten by upgrade (replay + preservation)" replayed-upgrade

# ===========================================================================
echo "== B2-b: explicit --profile beats replay and is re-recorded =="
# ===========================================================================
if run_upgrade "$T_A" --profile core,frontend; then ok "explicit upgrade rc=0"; else bad "explicit upgrade rc=0"; fi
if grep -q 'REPLAY: --profile' "$T_A.upgrade.log"; then
  bad "no profile REPLAY note when --profile explicit"
else
  ok "no profile REPLAY note when --profile explicit"
fi
if [ -d "$T_A/.claude/skills/frontend" ]; then
  ok "explicit core,frontend installed the frontend tree"
else
  bad "explicit core,frontend installed the frontend tree"
fi
py_assert "$STATE_A" "B2-b explicit profile re-recorded" explicit-upgrade

# ===========================================================================
echo "== B2-c: BACK-COMPAT — missing state (pre-Wave-B) never errors/no-ops =="
# ===========================================================================
T_F="$( fresh_install f --profile core )" || exit 1
rm -f "$T_F/$STATE_REL"
if run_upgrade "$T_F"; then ok "pre-Wave-B upgrade rc=0 (never error)"; else bad "pre-Wave-B upgrade rc=0 (never error)"; tail -20 "$T_F.upgrade.log" >&2; fi
if grep -q 'pre-Wave-B install' "$T_F.upgrade.log"; then
  ok "fallback NOTE emitted"
else
  bad "fallback NOTE emitted"
fi
if grep -q '==> Upgrade complete.' "$T_F.upgrade.log" && grep -q 'BACKED UP' "$T_F.upgrade.log"; then
  ok "upgrade actually ran (never no-op): backup + completion present"
else
  bad "upgrade actually ran (never no-op): backup + completion present"
fi
if [ -f "$T_F/$STATE_REL" ]; then
  ok "state file ACQUIRED after first post-Wave-B upgrade (ADR-155 iv mirror)"
else
  bad "state file ACQUIRED after first post-Wave-B upgrade (ADR-155 iv mirror)"
fi
py_assert "$T_F/$STATE_REL" "B2-c acquired-state shape (synthesized request)" acquired
# Honest lock of TODAY's fallback behavior: default profile core,frontend
# installs the frontend tree into a core-only target (pre-existing behavior,
# unchanged by B2 — the replay path is what FIXES it going forward).
if [ -d "$T_F/.claude/skills/frontend" ]; then
  ok "fallback used default core,frontend (today's documented behavior)"
else
  bad "fallback used default core,frontend (today's documented behavior)"
fi

# ===========================================================================
echo "== B2-c2: pre-state ceremony migration (re-pass rc.4 t3 P1) =="
# ===========================================================================
# Default = fail-SAFE user; --ceremony maintainer opts back in; the
# EFFECTIVE ceremony persists into the synthesized state so upgrade #2
# recovers it from the record instead of re-running the migration branch.
T_C="$( fresh_install c2 --profile core )" || exit 1
rm -f "$T_C/$STATE_REL"
if run_upgrade "$T_C"; then ok "pre-state upgrade rc=0"; else bad "pre-state upgrade rc=0"; fi
if grep -q 'Ceremony: user' "$T_C.upgrade.log"; then
  ok "pre-state default resolved to USER (fail-safe)"
else
  bad "pre-state default resolved to USER (fail-safe)"; grep 'Ceremony:' "$T_C.upgrade.log" >&2 || true
fi
if PYTHONNOUSERSITE=1 python3 -I -c '
import json, sys
st = json.load(open(sys.argv[1]))
sys.exit(0 if "ceremony" not in st.get("request", {}) else 1)
' "$T_C/$STATE_REL"; then
  ok "fail-safe INFERENCE not persisted (request.ceremony absent — t5 P1)"
else
  bad "fail-safe INFERENCE not persisted (request.ceremony absent — t5 P1)"
fi
if run_upgrade "$T_C"; then ok "upgrade #2 rc=0"; else bad "upgrade #2 rc=0"; fi
if grep -q 'Ceremony: user' "$T_C.upgrade.log"; then
  ok "upgrade #2 still fail-safe user (inference stays recoverable)"
else
  bad "upgrade #2 still fail-safe user (inference stays recoverable)"; grep 'Ceremony:' "$T_C.upgrade.log" >&2 || true
fi
# RECOVERY after a mistaken inference (t5 P1): the explicit flag must win
# on run #3 (nothing was persisted) and root delivery must resume.
if run_upgrade "$T_C" --ceremony maintainer; then ok "recovery upgrade rc=0"; else bad "recovery upgrade rc=0"; fi
if grep -q 'Ceremony: maintainer' "$T_C.upgrade.log"; then
  ok "recovery: explicit maintainer WINS after prior inference"
else
  bad "recovery: explicit maintainer WINS after prior inference"; grep 'Ceremony:' "$T_C.upgrade.log" >&2 || true
fi

T_M="$( fresh_install m2 --profile core )" || exit 1
rm -f "$T_M/$STATE_REL"
if run_upgrade "$T_M" --ceremony maintainer; then ok "pre-state --ceremony maintainer rc=0"; else bad "pre-state --ceremony maintainer rc=0"; fi
if grep -q 'Ceremony: maintainer' "$T_M.upgrade.log" && grep -q 'explicit --ceremony flag' "$T_M.upgrade.log"; then
  ok "explicit maintainer honored + source named"
else
  bad "explicit maintainer honored + source named"; grep 'Ceremony:' "$T_M.upgrade.log" >&2 || true
fi
if PYTHONNOUSERSITE=1 python3 -I -c '
import json, sys
st = json.load(open(sys.argv[1]))
sys.exit(0 if st.get("request", {}).get("ceremony") == "maintainer" else 1)
' "$T_M/$STATE_REL"; then
  ok "maintainer PERSISTED (request.ceremony=maintainer)"
else
  bad "maintainer PERSISTED (request.ceremony=maintainer)"
fi
if run_upgrade "$T_M"; then ok "maintainer upgrade #2 rc=0"; else bad "maintainer upgrade #2 rc=0"; fi
if grep -q 'Ceremony: maintainer' "$T_M.upgrade.log" && grep -q 'recorded install request' "$T_M.upgrade.log"; then
  ok "upgrade #2 recovered maintainer from the RECORD"
else
  bad "upgrade #2 recovered maintainer from the RECORD"; grep 'Ceremony:' "$T_M.upgrade.log" >&2 || true
fi

# ===========================================================================
echo "== B2-c3: schema docs — hash-gated refresh (t5 P1) =="
# ===========================================================================
# adopter-MODIFIED schema is PRESERVED; a byte-pristine PRIOR generation is
# REFRESHED to the current source.
T_S="$( fresh_install s3 --profile core )" || exit 1
printf 'ADOPTER CUSTOM SCHEMA\n' > "$T_S/.claude/plans/DEBATE-SCHEMA.md"
if run_upgrade "$T_S"; then ok "schema upgrade rc=0"; else bad "schema upgrade rc=0"; fi
if grep -q 'PRESERVED adopter-modified .claude/plans/DEBATE-SCHEMA.md' "$T_S.upgrade.log"; then
  ok "adopter-modified schema PRESERVED (loud warning)"
else
  bad "adopter-modified schema PRESERVED (loud warning)"
fi
if grep -q 'ADOPTER CUSTOM SCHEMA' "$T_S/.claude/plans/DEBATE-SCHEMA.md"; then
  ok "adopter bytes intact after upgrade"
else
  bad "adopter bytes intact after upgrade"
fi
# pristine PRIOR generation → refreshed to current source bytes
if prior_schema_bytes "$T_S/.claude/plans/DEBATE-SCHEMA.md"; then
  if run_upgrade "$T_S"; then ok "schema upgrade #2 rc=0"; else bad "schema upgrade #2 rc=0"; fi
  if grep -q 'REFRESHED (pristine prior generation): .claude/plans/DEBATE-SCHEMA.md' "$T_S.upgrade.log"; then
    ok "pristine prior generation REFRESHED"
  else
    bad "pristine prior generation REFRESHED"
  fi
  if cmp -s "$T_S/.claude/plans/DEBATE-SCHEMA.md" "$SOURCE_DIR/.claude/plans/DEBATE-SCHEMA.md"; then
    ok "schema now byte-identical to current source"
  else
    bad "schema now byte-identical to current source"
  fi
else
  bad "SCAFFOLD: prior-generation schema bytes unavailable (neither 9777a8d nor v1.2.0)"
fi

# ===========================================================================
echo "== B2-c4: schema refresh — symlink refusal + --skip + hasher fallback (t7 P1) =="
# ===========================================================================
# (1) symlinked LEAF: refresh must refuse and never write the REFERENT.
T_Y="$( fresh_install s4 --profile core )" || exit 1
REFERENT_DIR="$( mktemp -d "$WORKROOT/referent-XXXXXX" )"
prior_schema_bytes "$REFERENT_DIR/old-gen.md" \
  || cp "$SOURCE_DIR/.claude/plans/DEBATE-SCHEMA.md" "$REFERENT_DIR/old-gen.md"
REF_SHA_BEFORE="$( shasum -a 256 "$REFERENT_DIR/old-gen.md" | awk '{print $1}' )"
rm -f "$T_Y/.claude/plans/DEBATE-SCHEMA.md"
ln -s "$REFERENT_DIR/old-gen.md" "$T_Y/.claude/plans/DEBATE-SCHEMA.md"
if run_upgrade "$T_Y"; then ok "symlink-leaf upgrade rc=0"; else bad "symlink-leaf upgrade rc=0"; fi
if grep -q 'PRESERVED .claude/plans/DEBATE-SCHEMA.md (destination is a symlink' "$T_Y.upgrade.log"; then
  ok "symlinked leaf REFUSED with named warning"
else
  bad "symlinked leaf REFUSED with named warning"
fi
REF_SHA_AFTER="$( shasum -a 256 "$REFERENT_DIR/old-gen.md" | awk '{print $1}' )"
if [ "$REF_SHA_BEFORE" = "$REF_SHA_AFTER" ] && [ -L "$T_Y/.claude/plans/DEBATE-SCHEMA.md" ]; then
  ok "referent untouched, link intact (no write-through)"
else
  bad "referent untouched, link intact (no write-through)"
fi
# (2) symlinked ANCESTOR (hostile .claude/plans link): same refusal.
T_A="$( fresh_install s5 --profile core )" || exit 1
PLANS_REAL="$( mktemp -d "$WORKROOT/plans-real-XXXXXX" )"
cp -R "$T_A/.claude/plans/." "$PLANS_REAL/"
rm -rf "$T_A/.claude/plans"
ln -s "$PLANS_REAL" "$T_A/.claude/plans"
ANC_SHA_BEFORE="$( shasum -a 256 "$PLANS_REAL/DEBATE-SCHEMA.md" | awk '{print $1}' )"
if run_upgrade "$T_A"; then ok "symlink-ancestor upgrade rc=0"; else bad "symlink-ancestor upgrade rc=0"; fi
if grep -q 'PRESERVED .claude/plans/DEBATE-SCHEMA.md (ancestor .claude/plans is a symlink' "$T_A.upgrade.log"; then
  ok "symlinked ancestor REFUSED with named warning"
else
  bad "symlinked ancestor REFUSED with named warning"
fi
ANC_SHA_AFTER="$( shasum -a 256 "$PLANS_REAL/DEBATE-SCHEMA.md" | awk '{print $1}' )"
if [ "$ANC_SHA_BEFORE" = "$ANC_SHA_AFTER" ]; then
  ok "ancestor referent untouched"
else
  bad "ancestor referent untouched"
fi
# (3) --skip excludes the schema from inspection AND write (byte-preservation
# even for a pristine PRIOR generation that would otherwise refresh).
T_K="$( fresh_install s6 --profile core )" || exit 1
if prior_schema_bytes "$T_K/.claude/plans/DEBATE-SCHEMA.md"; then
  SKIP_SHA_BEFORE="$( shasum -a 256 "$T_K/.claude/plans/DEBATE-SCHEMA.md" | awk '{print $1}' )"
  if run_upgrade "$T_K" --skip='.claude/plans/DEBATE-SCHEMA.md'; then
    ok "--skip upgrade rc=0"
  else
    bad "--skip upgrade rc=0"
  fi
  if grep -q 'SKIPPED (--skip): .claude/plans/DEBATE-SCHEMA.md' "$T_K.upgrade.log"; then
    ok "--skip verdict named in the log"
  else
    bad "--skip verdict named in the log"
  fi
  SKIP_SHA_AFTER="$( shasum -a 256 "$T_K/.claude/plans/DEBATE-SCHEMA.md" | awk '{print $1}' )"
  if [ "$SKIP_SHA_BEFORE" = "$SKIP_SHA_AFTER" ]; then
    ok "--skip byte-preservation (prior generation NOT refreshed)"
  else
    bad "--skip byte-preservation (prior generation NOT refreshed)"
  fi
  # accurate dry-run message for the same skip
  if run_upgrade "$T_K" --dry-run --skip='.claude/plans/DEBATE-SCHEMA.md' \
     && grep -q '(dry-run) schema doc SKIPPED (--skip): .claude/plans/DEBATE-SCHEMA.md' "$T_K.upgrade.log"; then
    ok "dry-run reports the per-path --skip verdict"
  else
    bad "dry-run reports the per-path --skip verdict"
  fi
else
  bad "SCAFFOLD: prior-generation schema bytes unavailable (--skip leg)"
fi
# (4) hasher portability: shasum ABSENT from PATH, sha256sum present — the
# refresh must go through _hash_file's fallback instead of aborting the
# whole upgrade under set -e (t7 P1: bare `shasum` on a Perl-less host).
T_H="$( fresh_install s7 --profile core )" || exit 1
if prior_schema_bytes "$T_H/.claude/plans/DEBATE-SCHEMA.md"; then
  HASH_BIN="$( mktemp -d "$WORKROOT/hashbin-XXXXXX" )"
  _real_shasum="$( command -v shasum )"
  for _b in bash sh git awk sed grep cut tr sort uniq head tail dirname \
            basename mktemp cp mv rm mkdir rmdir ln chmod cat date wc find \
            diff cmp printf env python3 uname readlink stat touch tee od \
            xargs ls sleep true false expr comm join fold paste; do
    _p="$( command -v "$_b" 2>/dev/null )" || continue
    ln -s "$_p" "$HASH_BIN/$_b" 2>/dev/null || true
  done
  printf '#!/bin/sh\nexec %s -a 256 "$@"\n' "$_real_shasum" > "$HASH_BIN/sha256sum"
  chmod +x "$HASH_BIN/sha256sum"
  if PATH="$HASH_BIN" bash "$UPGRADE" "$T_H" --no-deprecation-warn \
       >"$T_H.upgrade.log" 2>&1; then
    ok "sha256sum-only upgrade rc=0 (no set -e abort)"
  else
    bad "sha256sum-only upgrade rc=0 (no set -e abort)"; tail -5 "$T_H.upgrade.log" >&2 || true
  fi
  if grep -q 'REFRESHED (pristine prior generation): .claude/plans/DEBATE-SCHEMA.md' "$T_H.upgrade.log"; then
    ok "schema refreshed via the sha256sum fallback"
  else
    bad "schema refreshed via the sha256sum fallback"; grep 'DEBATE-SCHEMA' "$T_H.upgrade.log" >&2 || true
  fi
else
  bad "SCAFFOLD: prior-generation schema bytes unavailable (hasher leg)"
fi

# ===========================================================================
echo "== B2-c5: schema ownership follows DELIVERY, not presence (t8 P1) =="
# ===========================================================================
# A fresh install over an adopter-customized schema must NOT record the
# adopter bytes as framework-owned — otherwise uninstall hash-matches the
# manifest entry and DELETES the adopter file.
T_O="$( mktemp -d "$WORKROOT/tgt-s8-XXXXXX" )"
_git_init_retry "$T_O"
mkdir -p "$T_O/.claude/plans"
printf 'ADOPTER PRE-INSTALL SCHEMA\n' > "$T_O/.claude/plans/DEBATE-SCHEMA.md"
if run_install "$T_O" --profile core; then ok "seeded install rc=0"; else bad "seeded install rc=0"; fi
MANIFEST_O="$T_O/.claude/.install-manifest.sha256"
if [ -f "$MANIFEST_O" ]; then
  if grep -q 'DEBATE-SCHEMA.md' "$MANIFEST_O"; then
    bad "EXISTS-skipped schema stays OUT of the baseline manifest"
  else
    ok "EXISTS-skipped schema stays OUT of the baseline manifest"
  fi
  # contrast: the schema the install DID deliver is recorded
  if grep -q 'plans/PLAN-SCHEMA.md' "$MANIFEST_O"; then
    ok "delivered schema IS recorded (contrast leg)"
  else
    bad "delivered schema IS recorded (contrast leg)"
  fi
else
  bad "manifest exists after install"
fi
if bash "$SOURCE_DIR/scripts/uninstall.sh" "$T_O" >"$T_O.uninstall.log" 2>&1; then
  ok "uninstall rc=0"
else
  # rc=5 (mismatches without --force) is also a PRESERVING outcome
  ok "uninstall exited non-zero WITHOUT deleting (preserving posture)"
fi
if grep -q 'ADOPTER PRE-INSTALL SCHEMA' "$T_O/.claude/plans/DEBATE-SCHEMA.md" 2>/dev/null; then
  ok "adopter schema SURVIVED uninstall (bytes intact)"
else
  bad "adopter schema SURVIVED uninstall (bytes intact)"
fi

# ===========================================================================
echo "== B2-c6: TRACKED posture artifact => upgrade FALHA com migracao (t10 P1) =="
# ===========================================================================
T_T="$( fresh_install s9 --profile core )" || exit 1
printf '{}\n' > "$T_T/.claude/settings.local.json"
( cd "$T_T" \
  && git add -f .claude/settings.local.json \
  && git -c user.email=t@t -c user.name=t commit -qm tracked-seed )
if run_upgrade "$T_T"; then
  bad "tracked posture artifact => upgrade FALHA (rc!=0)"
else
  ok "tracked posture artifact => upgrade FALHA (rc!=0)"
fi
if grep -q 'git rm --cached' "$T_T.upgrade.log"; then
  ok "mensagem de migracao acionavel (git rm --cached)"
else
  bad "mensagem de migracao acionavel (git rm --cached)"; tail -8 "$T_T.upgrade.log" >&2
fi
# migracao explicita => upgrade volta a passar; 2 upgrades seguidos SEM
# re-assercao em loop (idempotencia do probe --no-index)
( cd "$T_T" && git rm -q --cached .claude/settings.local.json \
  && git -c user.email=t@t -c user.name=t commit -qm migrate )
if run_upgrade "$T_T"; then ok "pos-migracao upgrade rc=0"; else bad "pos-migracao upgrade rc=0"; tail -5 "$T_T.upgrade.log" >&2; fi
if run_upgrade "$T_T" && ! grep -q 'RE-ASSERTED' "$T_T.upgrade.log"; then
  ok "upgrade repetido idempotente (sem RE-ASSERT em loop)"
else
  bad "upgrade repetido idempotente (sem RE-ASSERT em loop)"
fi

# ===========================================================================
echo "== B2-d: garbage state => NOTE + fallback + rewritten valid =="
# ===========================================================================
printf 'this is not json{{{' > "$T_F/$STATE_REL"
if run_upgrade "$T_F"; then ok "garbage-state upgrade rc=0"; else bad "garbage-state upgrade rc=0"; fi
if grep -q 'unreadable/invalid' "$T_F.upgrade.log"; then
  ok "invalid-state NOTE emitted"
else
  bad "invalid-state NOTE emitted"
fi
py_assert "$T_F/$STATE_REL" "B2-d state rewritten as valid JSON" valid

# ===========================================================================
echo "== B2-e: hostile profile value fails charset validation => no replay =="
# ===========================================================================
python3 - "$T_F/$STATE_REL" <<'PY'
import json, sys
d = {
    "schema": "ceo.install-state/v1",
    "schema_version": 1,
    "request": {"profile": "core,frontend; rm -rf ~", "stack": "$(touch /tmp/pwned)"},
}
with open(sys.argv[1], "w", encoding="utf-8") as f:
    json.dump(d, f)
PY
if run_upgrade "$T_F"; then ok "hostile-state upgrade rc=0"; else bad "hostile-state upgrade rc=0"; fi
if grep -q 'REPLAY:' "$T_F.upgrade.log"; then
  bad "hostile values NOT replayed"
else
  ok "hostile values NOT replayed"
fi
if grep -q 'unreadable/invalid' "$T_F.upgrade.log"; then
  ok "hostile state treated as invalid (charset fence)"
else
  bad "hostile state treated as invalid (charset fence)"
fi
if grep -q '^    Profile: core,frontend$' "$T_F.upgrade.log"; then
  ok "default profile used instead of hostile value"
else
  bad "default profile used instead of hostile value"
fi

# ===========================================================================
echo "== B2-f: --dry-run replays for preview but never writes; --no-replay opts out =="
# ===========================================================================
SNAP="$WORKROOT/state.snapshot"
cp "$STATE_A" "$SNAP"
if run_upgrade "$T_A" --dry-run; then ok "dry-run upgrade rc=0"; else bad "dry-run upgrade rc=0"; fi
if grep -q 'REPLAY:' "$T_A.upgrade.log"; then
  ok "dry-run resolves replay for the preview"
else
  bad "dry-run resolves replay for the preview"
fi
if cmp -s "$STATE_A" "$SNAP"; then
  ok "dry-run did not modify the state file"
else
  bad "dry-run did not modify the state file"
fi
if run_upgrade "$T_A" --dry-run --no-replay; then ok "--no-replay dry-run rc=0"; else bad "--no-replay dry-run rc=0"; fi
if grep -q 'REPLAY:' "$T_A.upgrade.log"; then
  bad "--no-replay suppresses replay"
else
  ok "--no-replay suppresses replay"
fi

echo ""
echo "== RESULT: PASS=$PASS FAIL=$FAIL =="
[ "$FAIL" -eq 0 ]
