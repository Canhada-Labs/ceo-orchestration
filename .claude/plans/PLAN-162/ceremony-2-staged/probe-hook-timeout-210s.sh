#!/usr/bin/env bash
# probe-hook-timeout-210s.sh — ADR-110-AMEND-2 §6 pre-ceremony BLOCKING gate.
#
# QUESTION: does the Claude Code harness honor a PreToolUse hook registered
# with "timeout": 210 (seconds), or does it kill the hook at some lower,
# undocumented ceiling? If it kills earlier, raising the pair-rail to
# internal 180 / registration 210 creates fail-open WITH NO EVENT (a killed
# hook never emits pair_rail_case) — strictly worse than today's case F,
# invisible to the censoring-rate instrument in numerator AND denominator.
#
# DESIGN — three cases, run A -> C -> B (both controls BEFORE the paid
# 200-second treatment; a probe whose controls cannot fail is a dead probe):
#
#   A  POSITIVE control   hook sleeps   5s, registered timeout 210
#                         -> hook MUST complete (start + end markers).
#                         Proves hooks fire, complete, and markers work.
#   C  NEGATIVE control   hook sleeps  20s, registered timeout  10
#                         -> harness MUST kill it (start marker, NO end
#                         marker, heartbeat stops near 10s). Proves the
#                         kill mechanism exists AND the heartbeat
#                         measurement can observe a kill.
#   B  TREATMENT          hook sleeps 200s, registered timeout 210
#                         -> end marker present  = harness honored a
#                            ~200s block under a 210 registration (GO).
#                         -> start marker only   = harness killed early;
#                            measured ceiling = last heartbeat - start.
#
# NEUTRALIZATION (mandatory on this machine): the Owner's
# ~/.claude/settings.json carries global allows (Bash(*), Edit, Write,
# defaultMode auto). Any probe inheriting it measures his config, not the
# harness. CLAUDE_CONFIG_DIR (and HOME, unless PROBE_KEEP_HOME=1) point at
# a fresh workspace; the probe hook is registered in THAT user layer, so
# no project-trust prompt applies, and the project dir is empty.
#
# COST: ~4-5 min wall, 3 headless `claude -p` calls (default model haiku).
# DO NOT run from inside a governed session without the CEO's ack — it
# spawns live harness sessions.
#
# EXIT CODES:
#   0  HONRA      (GO — §6 bullet 1 satisfied)
#   1  NAO-HONRA  (NO-GO — measured ceiling printed; amendment must not
#                  land as written)
#   2  INVALID    (positive control A failed — do not interpret)
#   3  INVALID    (negative control C failed to kill — do not interpret)
#   4  environment/usage error, OR treatment B ended too early to prove
#      anything (end marker present but observed duration below the
#      treatment floor — INCONCLUSIVE, never a GO; codex r5 P2)
#
# bash 3.2 compatible (macOS): no mapfile, no ${var,,}, no coproc.

set -u

# ---------------------------------------------------------------- knobs --
PROBE_MODEL="${PROBE_MODEL:-haiku}"
PROBE_TREATMENT_SLEEP_S="${PROBE_TREATMENT_SLEEP_S:-200}"
PROBE_REGISTERED_TIMEOUT_S="${PROBE_REGISTERED_TIMEOUT_S:-210}"
PROBE_KEEP_HOME="${PROBE_KEEP_HOME:-0}"
PROBE_CLAUDE_BIN="${PROBE_CLAUDE_BIN:-}"

say() { printf '%s\n' "$*"; }
hr()  { say "----------------------------------------------------------------"; }

# ------------------------------------------------- resolve claude binary --
CLAUDE_BIN=""
if [ -n "$PROBE_CLAUDE_BIN" ]; then
  CLAUDE_BIN="$PROBE_CLAUDE_BIN"
else
  CLAUDE_BIN="$(command -v claude || true)"
fi
if [ -z "$CLAUDE_BIN" ] || [ ! -x "$CLAUDE_BIN" ]; then
  say "FATAL: claude binary not found on PATH (set PROBE_CLAUDE_BIN=/path/to/claude)"
  exit 4
fi

# ------------------------------------------------------------- workspace --
WORK="$(mktemp -d /tmp/hkprobe.XXXXXX)" || { say "FATAL: mktemp failed"; exit 4; }
CFG="$WORK/cfg"
PROJ="$WORK/proj"
HOME_NEUTRAL="$WORK/home"
mkdir -p "$CFG" "$PROJ" "$HOME_NEUTRAL"

HOME_DIR="$HOME_NEUTRAL"
if [ "$PROBE_KEEP_HOME" = "1" ]; then
  HOME_DIR="$HOME"
fi

# Seed harness state so a fresh config dir does not trip onboarding.
printf '{"hasCompletedOnboarding": true}\n' > "$CFG/.claude.json"

# ------------------------------------------------------------ dummy hook --
# Start marker, 1 Hz heartbeat for N seconds, end marker, schema-compliant
# `{}` allow. Idempotent: if the model issues a second Bash call in the same
# case, the hook no-ops instead of re-blocking the session.
HOOK="$WORK/hook.sh"
cat > "$HOOK" <<'HOOK_EOF'
#!/usr/bin/env bash
set -u
SLEEP_S="$1"
PREFIX="$2"
if [ -f "$PREFIX.start" ]; then
  printf '{}'
  exit 0
fi
date +%s > "$PREFIX.start"
i=0
while [ "$i" -lt "$SLEEP_S" ]; do
  date +%s >> "$PREFIX.hb"
  sleep 1
  i=$((i+1))
done
date +%s > "$PREFIX.end"
printf '{}'
exit 0
HOOK_EOF
chmod +x "$HOOK"

# --------------------------------------------------------------- helpers --
write_settings() {
  # $1 sleep_s   $2 registered timeout_s   $3 marker prefix
  # Written to the NEUTRAL user layer (CLAUDE_CONFIG_DIR), which both
  # replaces the Owner's global allows and registers the probe hook at a
  # layer that needs no project-trust approval.
  cat > "$CFG/settings.json" <<EOF
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "bash \"$HOOK\" $1 \"$3\"",
            "timeout": $2,
            "statusMessage": "probe hook: sleep ${1}s under registered timeout ${2}s"
          }
        ]
      }
    ]
  }
}
EOF
}

run_claude() {
  # $1 case tag   $2 prompt   $3 max wall secs   $4 out file
  local tag prompt max_wall out pid rc t0 t1 wall
  tag="$1"; prompt="$2"; max_wall="$3"; out="$4"
  t0="$(date +%s)"
  ( cd "$PROJ" && exec env CLAUDE_CONFIG_DIR="$CFG" HOME="$HOME_DIR" \
      "$CLAUDE_BIN" -p "$prompt" --model "$PROBE_MODEL" \
      --allowedTools "Bash" --max-turns 4 ) > "$out" 2>&1 &
  pid=$!
  while kill -0 "$pid" 2>/dev/null; do
    t1="$(date +%s)"
    if [ $((t1 - t0)) -ge "$max_wall" ]; then
      say "  [$tag] watchdog: wall budget ${max_wall}s exceeded — killing claude (pid $pid)"
      kill -TERM "$pid" 2>/dev/null
      sleep 5
      kill -KILL "$pid" 2>/dev/null
      break
    fi
    sleep 2
  done
  wait "$pid" 2>/dev/null
  rc=$?
  t1="$(date +%s)"
  wall=$((t1 - t0))
  say "  [$tag] claude exit=$rc wall=${wall}s (budget ${max_wall}s) transcript=$out"
}

run_case() {
  # $1 tag   $2 sleep_s   $3 timeout_s   $4 max wall secs
  local tag sleep_s timeout_s max_wall prefix prompt
  tag="$1"; sleep_s="$2"; timeout_s="$3"; max_wall="$4"
  prefix="$WORK/case_${tag}"
  write_settings "$sleep_s" "$timeout_s" "$prefix"
  hr
  say "CASE ${tag}: hook sleep=${sleep_s}s under registered timeout=${timeout_s}s"
  say "  settings.json used (INPUT):"
  sed 's/^/    /' "$CFG/settings.json"
  prompt="Use the Bash tool to run exactly this one command, then stop: date +%s > ${prefix}.tool_ran"
  run_claude "$tag" "$prompt" "$max_wall" "$WORK/claude_${tag}.out"
}

first_line() { if [ -s "$1" ]; then head -n 1 "$1"; else printf ''; fi; }
last_line()  { if [ -s "$1" ]; then tail -n 1 "$1"; else printf ''; fi; }

show_markers() {
  # $1 tag
  local p n
  p="$WORK/case_$1"
  if [ -f "$p.start" ]; then
    say "  case_$1.start    : $(tr '\n' ' ' < "$p.start")"
  else
    say "  case_$1.start    : ABSENT"
  fi
  if [ -f "$p.hb" ]; then
    n="$(wc -l < "$p.hb" | tr -d ' ')"
    say "  case_$1.hb       : $n beats, first=$(first_line "$p.hb") last=$(last_line "$p.hb")"
  else
    say "  case_$1.hb       : ABSENT"
  fi
  if [ -f "$p.end" ]; then
    say "  case_$1.end      : $(tr '\n' ' ' < "$p.end")"
  else
    say "  case_$1.end      : ABSENT"
  fi
  if [ -f "$p.tool_ran" ]; then
    say "  case_$1.tool_ran : $(tr '\n' ' ' < "$p.tool_ran")"
  else
    say "  case_$1.tool_ran : ABSENT"
  fi
}

# ---------------------------------------------------------------- inputs --
hr
say "PROBE INPUTS (a measurement that hides its inputs is not a measurement)"
say "  date            : $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
say "  uname           : $(uname -sr)"
say "  claude binary   : $CLAUDE_BIN"
say "  claude version  : $("$CLAUDE_BIN" --version 2>&1 | head -n 1)"
say "  model           : $PROBE_MODEL"
say "  workspace       : $WORK"
say "  config layer    : $CFG (CLAUDE_CONFIG_DIR — neutralizes ~/.claude)"
say "  HOME during run : $HOME_DIR (PROBE_KEEP_HOME=$PROBE_KEEP_HOME)"
say "  treatment sleep : ${PROBE_TREATMENT_SLEEP_S}s under registered ${PROBE_REGISTERED_TIMEOUT_S}s"

# ------------------------------------------------------------- run cases --
# A first (cheap validity), C second (cheap kill proof), B last (the paid
# 200s treatment only runs once the instrument is known to be alive).
# Codex S292 P2 fold: each CONTROL is EVALUATED immediately after it runs —
# a dead control aborts BEFORE the paid 200s treatment (control-first for
# real, not just in execution order). A probe whose control cannot fail is
# a dead probe; a probe that pays the treatment after a dead control is an
# uninterpretable spend.
run_case a 5   "$PROBE_REGISTERED_TIMEOUT_S" 180
if ! { [ -f "$WORK/case_a.start" ] && [ -f "$WORK/case_a.end" ]; }; then
  hr
  say "ABORT: positive control A failed (hook never ran or never finished"
  say "under a ${PROBE_REGISTERED_TIMEOUT_S}s registration with a 5s sleep)."
  say "The instrument is DEAD — auth/hook-registration problem. The paid"
  say "case B was NOT run. Workspace kept at $WORK for diagnosis."
  # exit 2 == failed POSITIVE control (matches the header/README table and
  # the late-verdict branch below); 3 is reserved for a failed NEGATIVE
  # control. Codex S292 r2 P3.
  exit 2
fi
run_case c 20  10                            180
# Codex r3 P2: exigir que C tenha COMEÇADO. Sem start-marker o caso não
# rodou (auth falhou / o modelo nunca chamou Bash) e a ausência de end não
# prova kill nenhum — seguir para o B pago seria interpretar silêncio como
# sucesso, a classe que este probe existe para não repetir.
if [ ! -f "$WORK/case_c.start" ]; then
  hr
  say "ABORT: negative control C never STARTED (no start marker) — the run"
  say "did not exercise the kill path at all (auth failure, or the model"
  say "never called Bash). The paid case B was NOT run. Workspace: $WORK"
  exit 3
fi
if [ -f "$WORK/case_c.end" ]; then
  hr
  say "ABORT: negative control C failed (a 20s hook under a 10s registered"
  say "timeout RAN TO COMPLETION — the harness did not kill it, so the kill"
  say "mechanism this probe measures is not observable here). The paid"
  say "case B was NOT run. Workspace kept at $WORK for diagnosis."
  exit 3
fi
run_case b "$PROBE_TREATMENT_SLEEP_S" "$PROBE_REGISTERED_TIMEOUT_S" 360

# ---------------------------------------------------------------- verdict --
hr
say "MARKERS (raw evidence — workspace kept at $WORK)"
show_markers a
show_markers c
show_markers b

A_OK=0
if [ -f "$WORK/case_a.start" ] && [ -f "$WORK/case_a.end" ]; then
  A_OK=1
fi

C_KILLED=0
C_DELTA=""
if [ -f "$WORK/case_c.start" ] && [ ! -f "$WORK/case_c.end" ]; then
  C_KILLED=1
  if [ -s "$WORK/case_c.hb" ]; then
    C_DELTA=$(( $(last_line "$WORK/case_c.hb") - $(first_line "$WORK/case_c.start") ))
  fi
fi

B_COMPLETED=0
B_STARTED=0
B_DELTA=""
if [ -f "$WORK/case_b.start" ]; then
  B_STARTED=1
  if [ -f "$WORK/case_b.end" ]; then
    B_COMPLETED=1
    B_DELTA=$(( $(first_line "$WORK/case_b.end") - $(first_line "$WORK/case_b.start") ))
  elif [ -s "$WORK/case_b.hb" ]; then
    B_DELTA=$(( $(last_line "$WORK/case_b.hb") - $(first_line "$WORK/case_b.start") ))
  fi
fi

hr
say "VEREDITO"

if [ "$A_OK" -ne 1 ]; then
  say "  INVALID — positive control (case A) failed: a 5s hook under a"
  say "  ${PROBE_REGISTERED_TIMEOUT_S}s registration did not complete. The probe is DEAD; nothing"
  say "  below is interpretable."
  if [ -f "$WORK/case_a.tool_ran" ]; then
    say "  Disambiguation: tool_ran EXISTS -> Bash executed but the hook never"
    say "  fired -> hook registration/layer problem (inspect $CFG/settings.json"
    say "  and $WORK/claude_a.out)."
  else
    say "  Disambiguation: tool_ran ABSENT -> the model never called Bash, or"
    say "  auth/startup failed under the neutral HOME. Inspect $WORK/claude_a.out;"
    say "  if it shows an auth error, re-run with PROBE_KEEP_HOME=1."
  fi
  exit 2
fi
say "  [A] positive control OK — hooks fire and complete under neutral layers."

if [ "$C_KILLED" -ne 1 ]; then
  say "  INVALID — negative control (case C) did NOT observe a kill: a 20s hook"
  say "  under a 10s registration produced an end marker (or no start marker)."
  say "  A control that cannot fail means the instrument cannot see a kill, so"
  say "  case B is uninterpretable either way. Possible cause: the harness"
  say "  ignores the per-hook timeout field entirely (substrate drift — worth"
  say "  its own finding). Do NOT read a GO out of this run."
  exit 3
fi
if [ -n "$C_DELTA" ]; then
  say "  [C] negative control OK — kill observed at ~${C_DELTA}s after start"
  say "      (registered 10s; slack up to a few seconds is normal)."
else
  say "  [C] negative control OK — kill observed within the first heartbeat (<=1s data)."
fi

if [ "$B_COMPLETED" -eq 1 ]; then
  # Codex r5 P2: um end-marker SOZINHO não prova que o hook bloqueou o
  # tempo pretendido — um sleep que não dormiu (seam quebrado, script
  # trocado) também termina e escreveria "HONRA". O GO exige que a
  # duração OBSERVADA cubra o tratamento: sem isso o veredito é
  # inconclusivo, não positivo.
  _MIN_OK=$(( PROBE_TREATMENT_SLEEP_S - 15 ))
  if [ -z "${B_DELTA:-}" ] || [ "$B_DELTA" -lt "$_MIN_OK" ]; then
    say "  [B] INCONCLUSIVO — end marker presente, mas a duração observada"
    say "      (${B_DELTA:-desconhecida}s) não cobre o tratamento de"
    say "      ${PROBE_TREATMENT_SLEEP_S}s (piso ${_MIN_OK}s). O hook terminou"
    say "      cedo demais para provar que o harness honra"
    say "      ${PROBE_REGISTERED_TIMEOUT_S}s. NÃO leia um GO daqui."
    exit 4
  fi
  say "  [B] HONRA — the harness let a PreToolUse hook registered at"
  say "      ${PROBE_REGISTERED_TIMEOUT_S}s block for ~${B_DELTA}s and RETURN (end marker written)."
  say "      ADR-110-AMEND-2 §6 bullet 1: SATISFIED -> GO."
  exit 0
fi

if [ "$B_STARTED" -eq 1 ]; then
  say "  [B] NAO-HONRA — hook killed before completing ${PROBE_TREATMENT_SLEEP_S}s under a"
  say "      ${PROBE_REGISTERED_TIMEOUT_S}s registration."
  say "      TETO REAL MEDIDO ~= ${B_DELTA:-desconhecido}s (last heartbeat - start)."
  say "      ADR-110-AMEND-2 §6: NO-GO — the amendment does not land as written."
  exit 1
fi

say "  INVALID — case B produced no start marker although case A fired."
say "  Inconsistent instrument state (inspect $WORK/claude_b.out). Do not interpret."
exit 2
