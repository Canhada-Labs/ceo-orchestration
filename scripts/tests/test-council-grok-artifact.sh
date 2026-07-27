#!/usr/bin/env bash
# scripts/tests/test-council-grok-artifact.sh
# PLAN-161 W1a (C2 oracle, staged — exercised by land-plan161.sh --dry-run) —
# behavioral fixture for the grok-lane ARTIFACT transport (debate CF-3 +
# codex r1 F9): grok 0.2.93 `-p` cannot read stdin, so the lane composes
#   redactor stdout -> 0600 artifact in a fresh 0700 mkdtemp dir ->
#   rename-into-place (&&-chained) -> grok argv = FIXED pointer instruction
# and the four invariants are:
#   I1  artifact bytes == redactor stdout (attestable)
#   I2  grok argv contains NO repo/brief-derived bytes (fixed pointer only)
#   I3  induced redactor failure  => final artifact path DOES NOT EXIST
#                                    and grok NEVER runs (structural fail-closed)
#   I4  artifact mode 0600, parent dir 0700 — VERIFIED before grok runs
#
# The composition snippet lives INSIDE the lane-agent prompt template of
# .claude/workflows/council-audit.js between the markers
#   # --- GROK-ARTIFACT-COMPOSE BEGIN ---
#   # --- GROK-ARTIFACT-COMPOSE END ---
# This fixture extracts the snippet SOURCE text (JS `${cli}` interpolation
# doubles as a bash env expansion here), swaps the redactor invocation for a
# controllable command, and executes it. EXPECTED-RED on HEAD (markers absent
# until the W2 pack lands): exits 2 with a clear message.
#
# Staged-oracle hook: COUNCIL_JS points at the staged council-audit.js.
# Runs entirely in mktemp; the ONLY external command exercised is the local
# stdlib redactor (a pure stdin->stdout filter; nothing leaves the process).
#
# Run: bash scripts/tests/test-council-grok-artifact.sh; echo rc=$?

set -uo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO="$( cd "$SCRIPT_DIR/../.." && pwd )"
COUNCIL_JS="${COUNCIL_JS:-$REPO/.claude/workflows/council-audit.js}"

FAIL=0
PASS=0
TMP="$( mktemp -d -t ceo-p161-c2-XXXXXX )" || { echo "SCAFFOLD-ERROR: mktemp failed" >&2; exit 2; }
cleanup() { rm -rf "$TMP" 2>/dev/null || true; }
trap cleanup EXIT

ok()  { PASS=$((PASS+1)); printf '  ok   %s\n' "$1"; }
bad() { FAIL=$((FAIL+1)); printf '  FAIL %s\n' "$1" >&2; }

echo "==> C2.0 — extract the compose snippet from $COUNCIL_JS"
[ -f "$COUNCIL_JS" ] || { echo "SCAFFOLD-ERROR: $COUNCIL_JS missing" >&2; exit 2; }
sed -n '/# --- GROK-ARTIFACT-COMPOSE BEGIN ---/,/# --- GROK-ARTIFACT-COMPOSE END ---/p' \
  "$COUNCIL_JS" > "$TMP/compose-raw.sh"
if ! [ -s "$TMP/compose-raw.sh" ]; then
  echo "EXPECTED-RED (HEAD): council-audit.js carries no GROK-ARTIFACT-COMPOSE markers yet (PLAN-161 C2 lands them in W2)" >&2
  exit 2
fi

echo "==> C2.1 — source-text invariants on the snippet"
grep -q 'umask 077' "$TMP/compose-raw.sh" \
  && ok "C2.1 umask 077 present" || bad "C2.1 umask 077 missing"
grep -q 'mktemp -d' "$TMP/compose-raw.sh" \
  && ok "C2.1 fresh mkdtemp artifact dir" || bad "C2.1 mktemp -d missing"
grep -q 'codex_egress_redact\.py --outgoing' "$TMP/compose-raw.sh" \
  && ok "C2.1 redactor is the source of the artifact" || bad "C2.1 redactor invocation missing"
if grep -q '\$(cat' "$TMP/compose-raw.sh"; then
  bad "C2.1 FORBIDDEN \$(cat …) argv-content transport present"
else
  ok "C2.1 no \$(cat …) argv-content transport"
fi

# Swap the redactor invocation for a controllable command; feed a canary brief.
sed 's|python3 [^|]*codex_egress_redact\.py --outgoing|$REDACTOR_CMD|' \
  "$TMP/compose-raw.sh" > "$TMP/compose.sh"
grep -q 'REDACTOR_CMD' "$TMP/compose.sh" \
  || { echo "SCAFFOLD-ERROR: redactor substitution failed (snippet shape drifted)" >&2; exit 2; }

CANARY="p161-brief-canary-7f3a"
BRIEF="council audit brief body — $CANARY — scope: fixture"

# fake grok: records argv, snapshots the artifact + modes at invocation time.
cat > "$TMP/fake-grok" <<'FAKE'
#!/usr/bin/env bash
printf '%s\n' "$*" > "$FAKE_OUT/argv.txt"
for a in "$@"; do
  case "$a" in
    *brief.txt*)
      p="$( printf '%s' "$a" | grep -oE '/[^ ]*brief\.txt' | head -1 )"
      if [ -n "$p" ] && [ -f "$p" ]; then
        cp "$p" "$FAKE_OUT/seen-brief.txt"
        if stat -f '%Lp' "$p" >/dev/null 2>&1; then
          stat -f '%Lp' "$p" > "$FAKE_OUT/artifact-mode.txt"
          stat -f '%Lp' "$( dirname "$p" )" > "$FAKE_OUT/parent-mode.txt"
        else
          stat -c '%a' "$p" > "$FAKE_OUT/artifact-mode.txt"
          stat -c '%a' "$( dirname "$p" )" > "$FAKE_OUT/parent-mode.txt"
        fi
      fi
      ;;
  esac
done
echo '{"vendor":"grok","status":"ok","findings":[]}'
FAKE
chmod +x "$TMP/fake-grok"

run_compose() { # $1 = redactor cmd; returns compose rc; records via FAKE_OUT
  rm -rf "$TMP/fakeout"; mkdir -p "$TMP/fakeout"
  ( cd "$REPO" \
    && BRIEF="$BRIEF" cli="$TMP/fake-grok -p --sandbox council" \
       REDACTOR_CMD="$1" FAKE_OUT="$TMP/fakeout" \
       ARTIFACT_KEEP_DIR="$TMP/keep" \
       bash "$TMP/compose.sh" > "$TMP/compose-run.log" 2>&1 )
}

echo "==> C2.2 — SUCCESS path (real redactor): bytes, argv, modes"
EXPECTED="$TMP/expected-redacted.txt"
if ! printf '%s' "$BRIEF" \
     | ( cd "$REPO" && python3 .claude/hooks/_lib/codex_egress_redact.py --outgoing ) \
     > "$EXPECTED" 2>/dev/null; then
  echo "SCAFFOLD-ERROR: real redactor failed on the canary brief" >&2
  exit 2
fi
if run_compose "python3 $REPO/.claude/hooks/_lib/codex_egress_redact.py --outgoing"; then
  ok "C2.2 compose pipeline exited 0"
else
  bad "C2.2 compose pipeline failed on the success path (see $TMP/compose-run.log)"
  sed -n '1,10p' "$TMP/compose-run.log" >&2
fi
if [ -f "$TMP/fakeout/seen-brief.txt" ] \
   && cmp -s "$TMP/fakeout/seen-brief.txt" "$EXPECTED"; then
  ok "C2.2 I1: artifact bytes == redactor stdout"
else
  bad "C2.2 I1: artifact bytes differ from redactor stdout (or artifact never reached grok)"
fi
if [ -f "$TMP/fakeout/argv.txt" ] && ! grep -q "$CANARY" "$TMP/fakeout/argv.txt"; then
  ok "C2.2 I2: grok argv carries NO brief-derived bytes (fixed pointer only)"
else
  bad "C2.2 I2: brief canary leaked into grok argv (or grok never ran)"
fi
if [ "$( cat "$TMP/fakeout/artifact-mode.txt" 2>/dev/null )" = "600" ]; then
  ok "C2.2 I4: artifact mode 0600 at grok hand-off"
else
  bad "C2.2 I4: artifact mode is '$( cat "$TMP/fakeout/artifact-mode.txt" 2>/dev/null )', want 600"
fi
if [ "$( cat "$TMP/fakeout/parent-mode.txt" 2>/dev/null )" = "700" ]; then
  ok "C2.2 I4: artifact parent dir mode 0700"
else
  bad "C2.2 I4: parent dir mode is '$( cat "$TMP/fakeout/parent-mode.txt" 2>/dev/null )', want 700"
fi

echo "==> C2.3 — FAILURE path (redactor exits 3): fail-closed"
cat > "$TMP/fail-redactor" <<'FR'
#!/usr/bin/env bash
cat >/dev/null
exit 3
FR
chmod +x "$TMP/fail-redactor"
if run_compose "$TMP/fail-redactor"; then
  bad "C2.3 compose pipeline exited 0 despite a redactor failure"
else
  ok "C2.3 compose pipeline failed loudly on redactor failure"
fi
if [ -f "$TMP/fakeout/argv.txt" ]; then
  bad "C2.3 I3: grok RAN after a redactor failure"
else
  ok "C2.3 I3: grok never ran after the redactor failure"
fi
if [ -e "$TMP/keep/brief.txt" ] || [ -f "$TMP/fakeout/seen-brief.txt" ]; then
  bad "C2.3 I3: a final artifact exists despite the redactor failure"
else
  ok "C2.3 I3: final artifact path does not exist (structural fail-closed)"
fi

echo ""
echo "==> RESULT: $PASS passed, $FAIL failed"
if [ "$FAIL" -ne 0 ]; then
  exit 1
fi
exit 0
