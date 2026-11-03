#!/bin/bash
# CEREMONY-LINT: handwritten-exception: PLAN-198 two-lane release re-pass runner, written by hand
# and kept small on purpose (the October kit came from a 12k-line derivator; see README.md).
#
# run_repass.sh - re-pass of the release candidate for ONE tag, by two vendors on the SAME
# redacted payloads: Codex (codex exec --sandbox read-only, user config ignored) and Claude Code
# (claude -p --restricted --safe-mode, read-only tools, subscription login; never --bare, which
# needs ANTHROPIC_API_KEY).
#
#   bash .claude/plans/PLAN-198/kit/run_repass.sh --tag vX.Y.Z[-rc.N] [--base TAG]
#        [--candidate SHA] [--conditions FILE] [--jobs N] [--resume] [--log FILE]
#
# The payload split, the custody checks and the redaction live in gen_envelope.py (prepare);
# this script runs the lanes and writes the evidence into .claude/plans/PLAN-198/repass-<sfx>/
# (sfx = rcN or ga). Progress goes to the log (default .claude/worktrees/repass-<sfx>.log, or
# repass-unknown.log when --tag is unreadable), whose last line is always "runner exit rc=N",
# so it can run in the background: nohup bash ... >/dev/null 2>&1 &
# Each lane runs in its own process group from a copy of the candidate OUTSIDE the repository,
# every file of which went through the same ADR-114 redactor before any lane started (the files
# it cannot keep are withheld and listed in withheld-<sfx>.txt); HUP, INT or TERM stop every
# lane's process group before that copy is removed. Every attempt (start; each lane's verdict,
# with nogo=1 for a NO-GO, as soon as it is complete; end with exit code, NO-GO count, manifest
# hash) is appended to the hash-chained .claude/worktrees/repass-attempts.log, which moving an
# attempt out of the repository keeps; a fresh start on a candidate with a NO-GO there is refused.
#
# Exit codes: 0 every lane answered GO or GO-WITH-CONDITIONS (evidence finalized)
#             1 a lane answered NO-GO or gave no valid VERDICT line (evidence finalized; the
#               generator refuses it - NO-GO from either lane blocks the candidate)
#             2 refused before any lane ran (nothing was sent anywhere)
#             3 a lane died (account limit, crash, time limit, signal), an instrument changed
#               during the run, or finalize refused: partial evidence and its run records kept,
#               re-run the same command with --resume
# Test seams (kit test only): CODEX_BIN and CLAUDE_BIN replace both lanes with stubs; the
# PROVENANCE then says "- instrument: STUB" and gen_envelope.py refuses that evidence.
# KIT_RETRY_UNIT_SECONDS shortens the Codex capacity back-off; KIT_LANE_TIMEOUT_SECONDS sets the
# per-lane wall-clock limit (default 7200).
set -uo pipefail

KIT_DIR="$(cd "$(dirname "$0")" && pwd -P)" || exit 2
REPO="$(git -C "$KIT_DIR" rev-parse --show-toplevel)" || exit 2
cd "$REPO" || exit 2
GEN="$KIT_DIR/gen_envelope.py"
PLAN_DIR="$(dirname "$KIT_DIR")"
WTROOT="$REPO/.claude/worktrees"
mkdir -p "$WTROOT" || exit 2
TAG="" BASE="" CAND="" COND="" JOBS=2 RESUME=0 LOG="" RUN="" TREEROOT="" EV="" STUB=0 ATTEMPT=0 HELD=0
LANE_TIMEOUT="${KIT_LANE_TIMEOUT_SECONDS:-7200}"

sfx_of() {  # rcN | ga | unknown
  if [[ "$1" =~ ^v[0-9]+\.[0-9]+\.[0-9]+(-rc\.([1-9][0-9]*))?$ ]]; then
    if [ -n "${BASH_REMATCH[2]}" ]; then echo "rc${BASH_REMATCH[2]}"; else echo ga; fi
  else
    echo unknown
  fi
}
# The log is known before any check, so a refused argument also ends it with "runner exit".
prev=""
for a in "$@"; do case "$prev" in --log) LOG="$a" ;; --tag) TAG="$a" ;; esac; prev="$a"; done
SFX="$(sfx_of "$TAG")"
[ -n "$LOG" ] || LOG="$WTROOT/repass-$SFX.log"

say() { printf '%s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" | tee -a "$LOG" >&2; }
die() { say "REFUSED: $*"; exit 2; }
need() { [ "$2" -ge 2 ] || die "$1 needs a value"; }
logged() {  # a main-shell helper call: its stderr (a REFUSED line) goes into the log and to stderr
  local rc=0
  "$@" 2> "$RUN/stderr" || rc=$?
  [ ! -s "$RUN/stderr" ] || tee -a "$LOG" < "$RUN/stderr" >&2
  return "$rc"
}
pg_signal() {  # $1 signal, then group files written by `gen_envelope.py spawn`; 0 = a group took it
  local s="$1" f g hit=1
  shift
  for f in "$@"; do
    [ -f "$f" ] || continue
    g="$(cat "$f" 2>/dev/null)"
    case "$g" in '' | *[!0-9]*) continue ;; esac
    [ "$g" -gt 1 ] && kill "-$s" -- "-$g" 2>/dev/null && hit=0
  done
  return "$hit"
}
cleanup() {
  local rc=$? f man="-"
  if [ "$HELD" -eq 1 ]; then  # finalize did not succeed: the attempt gets its run records back
    for f in "$RUN"/hold/.header "$RUN"/hold/.rc-*; do [ -e "$f" ] && mv -f "$f" "$EV/"; done
  fi
  if [ "$ATTEMPT" -eq 1 ]; then
    [ ! -f "$EV/MANIFEST-$SFX.sha256" ] || man="$(shasum -a 256 "$EV/MANIFEST-$SFX.sha256" | awk '{print $1}')"
    python3 "$GEN" ledger-add --tag "$TAG" --candidate "$CAND" --event "end rc=$rc nogo=$(cat "$EV"/*-"$SFX"-*.verdict.txt 2>/dev/null | grep -c '^VERDICT: NO-GO') manifest=$man" \
      || say "WARNING: the attempts ledger did not record the end of this attempt"
  fi
  case "$RUN" in "$WTROOT"/repass-*-run.*) rm -rf -- "$RUN" ;; esac
  case "$TREEROOT" in */kit-repass-tree.*) rm -rf -- "$TREEROOT" ;; esac
  say "runner exit rc=$rc"
}
stop_lanes() {
  local k=0
  say "signal received: stopping every lane's process group"
  pg_signal TERM "$RUN"/pg-*
  while [ "$k" -lt 30 ] && pg_signal 0 "$RUN"/pg-*; do sleep 1; k=$((k + 1)); done
  # shellcheck disable=SC2046
  kill $(jobs -p) 2>/dev/null  # the run_lane shells (a Codex capacity back-off sleeps there)
  sleep 1                      # a lane that was just starting has written its group file by now
  pg_signal KILL "$RUN"/pg-*
  wait
  exit 3
}
trap cleanup EXIT
trap stop_lanes HUP INT TERM

while [ $# -gt 0 ]; do
  case "$1" in
    --tag) need "$1" $#; TAG="$2"; shift 2 ;;
    --base) need "$1" $#; BASE="$2"; shift 2 ;;
    --candidate) need "$1" $#; CAND="$2"; shift 2 ;;
    --conditions) need "$1" $#; COND="$2"; shift 2 ;;
    --jobs) need "$1" $#; JOBS="$2"; shift 2 ;;
    --log) need "$1" $#; LOG="$2"; shift 2 ;;
    --resume) RESUME=1; shift ;;
    *) die "unknown argument: $1 (usage in the header of $0)" ;;
  esac
done
SFX="$(sfx_of "$TAG")"
[ "$SFX" != unknown ] || die "--tag must be vX.Y.Z or vX.Y.Z-rc.N (got '$TAG')"
case "$JOBS" in [1-8]) ;; *) die "--jobs must be 1..8" ;; esac
EV="$PLAN_DIR/repass-$SFX"
EV_REL="${EV#"$REPO"/}"
KEEP="$WTROOT/repass-$SFX-kept"
say "re-pass $TAG ($SFX) starts; log: $LOG"

# --- G0: the tree that will be tagged, nothing else ---------------------------------------
[ "$(git symbolic-ref -q --short HEAD)" = main ] || die "not on branch main"
HEAD_SHA="$(git rev-parse HEAD)" || die "git rev-parse HEAD failed"
if [ -n "$CAND" ]; then
  [ "$(git rev-parse -q --verify "$CAND^{commit}")" = "$HEAD_SHA" ] || die "--candidate $CAND is not HEAD ($HEAD_SHA)"
fi
CAND="$HEAD_SHA"
if [ -e "$EV" ] || [ -L "$EV" ]; then
  [ "$RESUME" -eq 1 ] || die "$EV_REL exists: this runner never deletes an attempt - move it out of the repository, or pass --resume"
  [ -d "$EV" ] && [ ! -L "$EV" ] || die "$EV_REL is not a plain directory"
  [ ! -e "$EV/MANIFEST-$SFX.sha256" ] || die "$EV_REL is already finalized: nothing to resume"
  [ -f "$EV/.header" ] || die "$EV_REL has no .header: cannot prove it is the same run"
else
  [ "$RESUME" -eq 0 ] || die "--resume given but $EV_REL does not exist"
fi
DIRTY="$(git status --porcelain --untracked-files=all | awk -v p="?? $EV_REL/" 'index($0, p) != 1')" \
  || die "git status failed"
[ -z "$DIRTY" ] || die "the working tree has changes outside $EV_REL/: commit or remove them first"
REMOTE_MAIN="$(git ls-remote origin refs/heads/main | awk '{print $1}')" \
  || die "git ls-remote origin failed (transport): not assuming anything"
[ "$REMOTE_MAIN" = "$CAND" ] || die "origin/main ($REMOTE_MAIN) is not the candidate ($CAND): push or pull first"
FREE_KB="$(df -Pk "$REPO" | awk 'NR == 2 {print $4}')"
[ "${FREE_KB:-0}" -ge 2097152 ] 2>/dev/null || die "less than 2 GiB free on the repository's disk"

RUN="$(mktemp -d "$WTROOT/repass-$SFX-run.XXXXXX")" || die "mktemp failed"
# The lanes' copy of the candidate lives OUTSIDE the repository: walking up from it reaches no
# CLAUDE.md, no auto-memory of this project and no evidence directory (the other lane's answers).
TREEROOT="$(mktemp -d "${TMPDIR:-/tmp}/kit-repass-tree.XXXXXX")" || die "mktemp of the lanes' copy failed"
TREEROOT="$(cd "$TREEROOT" && pwd -P)" || die "the lanes' copy directory vanished"
! git -C "$TREEROOT" rev-parse --git-dir >/dev/null 2>&1 || die "$TREEROOT is inside a git repository: point TMPDIR elsewhere"
FREE_KB="$(df -Pk "$TREEROOT" | awk 'NR == 2 {print $4}')"
[ "${FREE_KB:-0}" -ge 2097152 ] 2>/dev/null || die "less than 2 GiB free under $TREEROOT"
if [ "$RESUME" -eq 0 ]; then  # moving a NO-GO attempt aside never clears the candidate
  logged python3 "$GEN" nogo-check --candidate "$CAND" \
    || die "the attempts ledger has a NO-GO for this candidate (the REFUSED line above): a restart is refused"
fi

# --- the two instruments --------------------------------------------------------------------
# Codex without the user's config.toml (plugins, MCP servers, notify, approvals reviewer), rules
# or session files; model and effort are passed explicitly. Flags read on codex-cli 0.166.0.
CODEX_ISO=(--ignore-user-config --ephemeral --ignore-rules)
for f in apps plugins hooks browser_use computer_use in_app_browser image_generation memories; do
  CODEX_ISO+=(-c "features.$f=false")
done
if [ -n "${CODEX_BIN:-}" ] || [ -n "${CLAUDE_BIN:-}" ]; then
  [ -x "${CODEX_BIN:-}" ] && [ -x "${CLAUDE_BIN:-}" ] || die "CODEX_BIN and CLAUDE_BIN must both name executables (kit-test seam)"
  STUB=1 CODEX_CMD="$CODEX_BIN" CLAUDE_CMD="$CLAUDE_BIN"
  CODEX_ID="stub / stub / payload stub / status stub" C_SHA="stub"
  CODEX_MODEL="stub" CODEX_EFFORT="stub" CODEX_SRC="stub" CLAUDE_VER="claude-code-cli-stub"
  say "WARNING: stub lanes (CODEX_BIN/CLAUDE_BIN): this evidence can never become a verdict"
else
  CODEX_CMD="$(command -v codex)" || die "codex is not on PATH"
  PIN_JSON="$(CLAUDE_PROJECT_DIR="$REPO" python3 "$REPO/.claude/hooks/check_pair_rail.py" --verify-codex-pin "$CODEX_CMD")" \
    || die "the ADR-182 pin oracle refused $CODEX_CMD: $PIN_JSON"
  # shellcheck disable=SC2046
  set -- $(printf '%s' "$PIN_JSON" | python3 -c 'import json,sys
d = json.load(sys.stdin)
print(*[str(d.get(k) or "-") for k in ("status", "sha256", "target_triple", "installed_version")])')
  [ $# -eq 4 ] || die "the pin oracle printed something unreadable: $PIN_JSON"
  C_STATUS="$1" C_SHA="$2" C_TRIPLE="$3" C_INST="$4"
  # Order M4: the oracle hashed the payload without running it; only now does it run.
  C_VER="$("$CODEX_CMD" --version 2>/dev/null | awk 'NR == 1 {print $NF}')"
  [ "$C_STATUS" != compatible ] || [ "$C_INST" = "$C_VER" ] \
    || die "codex package.json says $C_INST but the binary says $C_VER"
  python3 "$GEN" instrument --version "$C_VER" --triple "$C_TRIPLE" --sha "$C_SHA" --status "$C_STATUS" \
    || die "the Codex instrument is not admitted (see above)"
  "$CODEX_CMD" exec "${CODEX_ISO[@]}" --help >/dev/null 2>&1 \
    || die "codex $C_VER refuses --ignore-user-config/--ephemeral/--ignore-rules: its lane would load the user's config.toml, plugins and MCP servers"
  CODEX_ID="$C_VER / $C_TRIPLE / payload $C_SHA / status $C_STATUS"
  # shellcheck disable=SC2046
  set -- $(python3 "$GEN" codex-config) || die "Codex model/effort unknown"
  [ $# -eq 3 ] || die "Codex model/effort unreadable"
  CODEX_MODEL="$1" CODEX_EFFORT="$2" CODEX_SRC="$3"
  # The versioned binary, not the auto-updated symlink: the version recorded is the one that runs.
  CLAUDE_CMD="$(command -v claude)" || die "claude is not on PATH"
  CLAUDE_CMD="$(python3 -c 'import os, sys; print(os.path.realpath(sys.argv[1]))' "$CLAUDE_CMD")" || die "realpath of claude failed"
  CLAUDE_VER="claude-code-cli-$(cd "$RUN" && "$CLAUDE_CMD" --version 2>/dev/null | awk 'NR == 1 {print $1}')"
  [[ "$CLAUDE_VER" =~ ^claude-code-cli-[0-9]+\.[0-9]+\.[0-9]+$ ]] || die "claude --version is unreadable ($CLAUDE_VER)"
  "$CLAUDE_CMD" --help 2>/dev/null | grep -q -e '--safe-mode' \
    || die "$CLAUDE_VER has no --safe-mode: its lane would load CLAUDE.md, skills, hooks and MCP servers"
fi
CLAUDE_MODEL="${CLAUDE_MODEL:-claude-opus-5-5}"
CLAUDE_EFFORT="${CLAUDE_EFFORT:-xhigh}"
# --restricted: no command-running tools, settings files ignored, file tools confined to the
# working directory; --safe-mode: no CLAUDE.md, skills, plugins, hooks or MCP (auth kept).
CLAUDE_ARGS=(-p --restricted --safe-mode --strict-mcp-config --tools "Read,Grep,Glob" --allowedTools "Read,Grep,Glob"
  --permission-mode dontAsk --no-session-persistence --model "$CLAUDE_MODEL" --effort "$CLAUDE_EFFORT"
  --output-format stream-json --verbose)

# --- the lanes' read-only copy of the candidate, outside the repository, redacted -----------
TREE="$TREEROOT/tree"
GIT_INDEX_FILE="$RUN/index" git read-tree "$CAND" || die "git read-tree failed"
GIT_INDEX_FILE="$RUN/index" git checkout-index -a --prefix="$TREE/" || die "git checkout-index failed"
# The files each CLI loads as instructions on its own: in the diff they are data, never orders.
find "$TREE" -type f \( -name CLAUDE.md -o -name CLAUDE.local.md -o -name AGENTS.md -o -name AGENTS.override.md \) \
  -delete || die "could not remove the instruction files from the lanes' copy"
# Every file through the same redactor as the payloads, before any lane starts; what it cannot
# keep line for line (and every symlink) leaves the copy and goes into the withheld list.
logged python3 "$GEN" redact-tree --tree "$TREE" --out "$RUN/withheld.txt" > "$RUN/redact-tree.out" \
  || die "the lanes' copy could not be redacted (the REFUSED line above); nothing was sent"
say "lanes' copy redacted: $(sed -n 's/^WITHHELD_N=//p' "$RUN/redact-tree.out") files withheld"

# --- payloads: custody, scope, split, redaction (gen_envelope.py prepare) -------------------
STAGE="$RUN/ev"
mkdir "$STAGE" || die "mkdir failed"
PREP=(prepare --tag "$TAG" --candidate "$CAND" --out "$STAGE" --withheld "$RUN/withheld.txt")
[ -z "$BASE" ] || PREP+=(--base "$BASE")
[ -z "$COND" ] || PREP+=(--conditions "$COND")
logged python3 "$GEN" "${PREP[@]}" > "$RUN/prepare.out" || die "prepare refused (the REFUSED line above); nothing was sent"
P_BASE="" P_BASE_OBJ="" P_BASE_COMMIT="" P_SIGNER="" P_KIT_TREE="" P_PARTS="" P_COND_SHA="" P_RC_TAG=""
P_WITHHELD_SHA="" P_WITHHELD_N=""
while IFS='=' read -r k v; do
  case "$k" in
    BASE|BASE_OBJ|BASE_COMMIT|SIGNER|KIT_TREE|PARTS|COND_SHA|RC_TAG|WITHHELD_SHA|WITHHELD_N) printf -v "P_$k" '%s' "$v" ;;
  esac
done < "$RUN/prepare.out"
[ -n "$P_PARTS" ] && [ -n "$P_KIT_TREE" ] && [ -n "$P_WITHHELD_SHA" ] || die "prepare printed no plan"
{
  echo "- tag: $TAG"
  echo "- base: $P_BASE tag-object $P_BASE_OBJ commit $P_BASE_COMMIT"
  echo "- base-signer: $P_SIGNER"
  [ -z "$P_RC_TAG" ] || echo "- rc-tag: $P_RC_TAG"
  echo "- candidate: $CAND"
  echo "- kit-tree: $P_KIT_TREE"
  echo "- parts: $P_PARTS"
  echo "- codex: $CODEX_ID"
  echo "- codex-model: $CODEX_MODEL / effort $CODEX_EFFORT (source: $CODEX_SRC)"
  echo "- claude: $CLAUDE_VER / model $CLAUDE_MODEL / effort $CLAUDE_EFFORT"
  echo "- conditions: CONDITIONS-$SFX.reviewed.md sha256 $P_COND_SHA"
  echo "- withheld: withheld-$SFX.txt sha256 $P_WITHHELD_SHA files $P_WITHHELD_N"
  [ "$STUB" -eq 0 ] || echo "- instrument: STUB (CODEX_BIN/CLAUDE_BIN set): kit-test evidence, never a verdict"
} > "$RUN/header" || die "header write failed"
if [ "$RESUME" -eq 1 ]; then
  cmp -s "$RUN/header" "$EV/.header" || die "--resume: base, candidate, kit, conditions or an instrument differ from the first attempt"
  for f in "$STAGE"/*; do
    cmp -s "$f" "$EV/$(basename "$f")" || die "--resume: $(basename "$f") differs from its re-derivation"
  done
  rm -f "$EV/.quota"  # the account-limit stop belonged to the previous attempt
  say "resuming $EV_REL ($P_PARTS payloads)"
else
  mv "$STAGE" "$EV" || die "could not move the payloads into $EV_REL"
  [ ! -L "$EV/.header" ] || die "$EV_REL/.header is a symlink"
  cp "$RUN/header" "$EV/.header" || die "could not record the run header"
  say "$P_PARTS payloads prepared in $EV_REL (base $P_BASE)"
fi
logged python3 "$GEN" ledger-add --tag "$TAG" --candidate "$CAND" --event "start resume=$RESUME parts=$P_PARTS ev=$EV_REL" \
  || die "the attempts ledger refused this attempt (the REFUSED line above)"
ATTEMPT=1

# --- the lanes ------------------------------------------------------------------------------
LIMIT_RE='hit your usage limit|reached your usage limit|Usage limit reached|Quota exceeded|out of credits|hit your spend cap|reached your workspace credit limit'
CAPACITY_RE='at capacity|Review was interrupted|experiencing high load'

verdict_of() {  # GO | GO-WITH-CONDITIONS | NO-GO when the file has exactly ONE valid VERDICT line
  [ -f "$1" ] || return 0
  [ "$(grep -c '^VERDICT:' "$1")" = 1 ] || return 0
  grep '^VERDICT:' "$1" | sed -n -E 's/^VERDICT: (GO-WITH-CONDITIONS|GO|NO-GO)([[:blank:]].*)?$/\1/p'
}
lane_done() {  # a completed review: rc 0 and exactly one valid VERDICT line
  [ -f "$EV/.rc-$1-$2" ] && grep -q '^rc=0 ' "$EV/.rc-$1-$2" \
    && [ -n "$(verdict_of "$EV/$1-$SFX-$2.verdict.txt")" ]
}
lane_exec() {  # $1 group file, $2 stdin, $3 log, then the vendor command: own process group,
  local pgf="$1" in="$2" lg="$3" pid rc=0  # the copy outside the repository, no API keys
  shift 3
  ( cd "$TREE" && exec env -u OPENAI_API_KEY -u ANTHROPIC_API_KEY DISABLE_AUTOUPDATER=1 \
      GIT_CEILING_DIRECTORIES="$TREEROOT" python3 "$GEN" spawn --pg-file "$pgf" --timeout "$LANE_TIMEOUT" -- "$@" ) \
    < "$in" > "$lg" 2>&1 &
  pid=$!
  wait "$pid" || rc=$?
  pg_signal KILL "$pgf"  # anything the reviewer left behind in its group
  rm -f "$pgf"
  return "$rc"
}
run_lane() {  # $1 lane, $2 NN - runs in the background and writes only its own files
  local lane="$1" n="$2" red="$EV/payload-$SFX-$2.redacted.txt" try=0 rc cls
  local out="$EV/$1-$SFX-$2.verdict.txt" log="$EV/$1-$SFX-$2.log" pgf="$RUN/pg-$1-$2"
  local stamp f v nogo
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  for f in "$log" "$out"; do  # an earlier attempt of this lane is kept, never deleted
    if [ -e "$f" ]; then mkdir -p "$KEEP" && mv -f "$f" "$KEEP/$(basename "$f").$stamp"; fi
  done
  while :; do
    try=$((try + 1)) rc=0 cls=ok
    if [ "$lane" = codex ]; then
      lane_exec "$pgf" "$red" "$log" "$CODEX_CMD" exec --skip-git-repo-check --sandbox read-only "${CODEX_ISO[@]}" \
        --color never -m "$CODEX_MODEL" -c "model_reasoning_effort=\"$CODEX_EFFORT\"" --output-last-message "$out" - \
        || rc=$?
      if [ ! -s "$out" ]; then
        cls=dead
        if tail -n 40 "$log" | grep '^ERROR: ' | grep -Eq "$LIMIT_RE"; then
          cls=quota
        elif [ "$try" -lt 3 ] && tail -n 40 "$log" | grep '^ERROR: ' | grep -Eq "$CAPACITY_RE"; then
          say "payload $n codex: model at capacity (try $try), retrying"
          sleep $((try * ${KIT_RETRY_UNIT_SECONDS:-90}))
          continue
        fi
      fi
    else
      lane_exec "$pgf" "$red" "$log" "$CLAUDE_CMD" "${CLAUDE_ARGS[@]}" || rc=$?
      python3 "$GEN" claude-result --model "$CLAUDE_MODEL" "$log" "$out" 2>> "$LOG"
      case $? in 0) ;; 4) cls=quota ;; *) cls=dead ;; esac
    fi
    break
  done
  v="$(verdict_of "$out")"
  if [ -n "$v" ]; then  # a complete verdict reaches the ledger before this lane's shell returns
    nogo=0
    [ "$v" != NO-GO ] || nogo=1
    python3 "$GEN" ledger-add --tag "$TAG" --candidate "$CAND" --event "lane $lane part $n verdict $v nogo=$nogo" 2>> "$LOG" \
      || { cls=ledger; say "payload $n $lane: the attempts ledger did not take this verdict (the REFUSED line above): this attempt cannot finalize; stop and call Claude"; }
  fi
  printf 'rc=%s try=%s class=%s\n' "$rc" "$try" "$cls" > "$EV/.rc-$lane-$n"
  [ "$cls" != quota ] || printf '%s %s\n' "$lane" "$n" >> "$EV/.quota"
  say "payload $n $lane: rc=$rc class=$cls verdict=$(verdict_of "$out")"
}

i=1 running=0
while [ "$i" -le "$P_PARTS" ]; do
  n="$(printf '%02d' "$i")"; i=$((i + 1))
  if [ -e "$EV/.quota" ]; then say "an account limit was hit: no new payload is launched"; break; fi
  for lane in codex claude; do
    if lane_done "$lane" "$n"; then say "payload $n $lane: kept from the previous attempt"; continue; fi
    say "payload $n/$P_PARTS $lane: started"
    run_lane "$lane" "$n" &
    running=$((running + 1))
  done
  if [ "$running" -ge $((JOBS * 2)) ]; then wait; running=0; fi
done
wait

# --- classify -----------------------------------------------------------------------------
INFRA=0 OVERALL=0
if [ "$STUB" -eq 0 ]; then
  PIN2="$(CLAUDE_PROJECT_DIR="$REPO" python3 "$REPO/.claude/hooks/check_pair_rail.py" --verify-codex-pin "$CODEX_CMD")"
  case "$PIN2" in *"\"sha256\": \"$C_SHA\""*) ;; *) say "the Codex payload changed during the run"; INFRA=1 ;; esac
  CV2="claude-code-cli-$(cd "$RUN" && "$CLAUDE_CMD" --version 2>/dev/null | awk 'NR == 1 {print $1}')"
  [ "$CV2" = "$CLAUDE_VER" ] || { say "Claude Code changed during the run ($CLAUDE_VER -> $CV2)"; INFRA=1; }
fi
i=1
while [ "$i" -le "$P_PARTS" ]; do
  n="$(printf '%02d' "$i")"; i=$((i + 1))
  for lane in codex claude; do
    if [ ! -f "$EV/.rc-$lane-$n" ] || ! grep -q ' class=ok$' "$EV/.rc-$lane-$n"; then
      INFRA=1
    elif ! lane_done "$lane" "$n" || [ "$(verdict_of "$EV/$lane-$SFX-$n.verdict.txt")" = NO-GO ]; then
      OVERALL=1
    fi
  done
done
if [ "$INFRA" -ne 0 ]; then
  say "a lane died or never ran, or an instrument changed: evidence kept unfinalized in $EV_REL; after the reset run the same command with --resume"
  exit 3
fi

# --- finalize: scrub, PROVENANCE, MANIFEST --------------------------------------------------
SCRUB=()
i=1
while [ "$i" -le "$P_PARTS" ]; do
  n="$(printf '%02d' "$i")"; i=$((i + 1))
  for lane in codex claude; do SCRUB+=("$EV/$lane-$SFX-$n.verdict.txt" "$EV/$lane-$SFX-$n.log"); done
done
python3 "$GEN" scrub "${SCRUB[@]}" || { say "scrub failed"; exit 3; }
{
  echo "# Provenance - pair-rail re-pass of $TAG ($SFX), PLAN-198 kit"
  cat "$EV/.header"
  echo "- lanes: codex exec --sandbox read-only ${CODEX_ISO[*]} and claude ${CLAUDE_ARGS[*]}; each lane in its own process group with a ${LANE_TIMEOUT} s limit, from a read-only copy of the candidate outside the repository without CLAUDE.md/AGENTS.md files, every other file redacted by the same redactor or withheld (withheld-$SFX.txt), both reading the SAME redacted payload on stdin; API keys removed from both lanes' environment"
  echo "- codex death classes, from the codex ERROR: lines among the last 40 transcript lines (texts measured on codex 0.160.0 only): model capacity = retried up to 2 times; account limit = no retry and no new payload"
  echo "- personal home paths replaced by <user> in the diffs, transcripts and verdicts"
  echo "- finished: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
  i=1
  while [ "$i" -le "$P_PARTS" ]; do
    n="$(printf '%02d' "$i")"; i=$((i + 1))
    for lane in codex claude; do
      v="$(grep '^VERDICT:' "$EV/$lane-$SFX-$n.verdict.txt" | head -n 1)"
      echo "- part $n $lane: $(cat "$EV/.rc-$lane-$n") ${v:-(no VERDICT line)}"
    done
  done
  echo "RUNNER-OVERALL: rc=$OVERALL"
} > "$RUN/provenance" || { say "provenance write failed"; exit 3; }
mv -f "$RUN/provenance" "$EV/PROVENANCE-$SFX.md" || { say "provenance move failed"; exit 3; }
# The run records leave the evidence set only for finalize; cleanup puts them back unless it succeeds.
mkdir "$RUN/hold" || { say "mkdir failed"; exit 3; }
HELD=1
mv "$EV"/.rc-* "$EV/.header" "$RUN/hold/" || { say "could not set the run records aside"; exit 3; }
rm -f "$EV/.quota"
logged python3 "$GEN" finalize --tag "$TAG" \
  || { say "finalize refused (the REFUSED line above): run records restored; fix the cause, then run the same command with --resume"; exit 3; }
HELD=0
if [ "$OVERALL" -eq 0 ]; then
  say "every lane answered GO or GO-WITH-CONDITIONS; next: python3 $GEN fields --tag $TAG"
else
  say "a lane answered NO-GO or gave no valid VERDICT line: this evidence cannot become a verdict (triage it)"
fi
exit "$OVERALL"
