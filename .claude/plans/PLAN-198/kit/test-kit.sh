#!/bin/bash
# CEREMONY-LINT: handwritten-exception: PLAN-198 kit harness, written by hand.
#
# test-kit.sh - offline, disposable test of the PLAN-198 verdict kit.
#   bash .claude/plans/PLAN-198/kit/test-kit.sh        (exit 0 = every check passed)
#
# It builds a throwaway repository in a temp directory: its own bare "origin", a throwaway GPG
# key, a signed base tag whose verdict passes the real tag guard. Into it go the kit and REAL
# copies of the step-15 validator, the tag guard, the ADR-114 redactor and cli_currency. Then
# it runs the runner with stub lanes and the generator end to end (rc tag, then GA tag), and
# a set of named negatives. It never touches the calling repository (HEAD, refs and status
# are compared before and after: caller_repo_guard) and never uses the network: the real
# codex, claude and gh are shadowed by sentinels that fail loudly (precut gets a gh stub).
# KIT_TEST_TMP sets the parent of the scratch directory (default: $TMPDIR); KIT_TEST_KEEP=1 keeps it.
set -uo pipefail

KIT_SRC="$(cd "$(dirname "$0")" && pwd -P)" || exit 2
REAL="$(git -C "$KIT_SRC" rev-parse --show-toplevel)" || exit 2
KIT_REL="${KIT_SRC#"$REAL"/}"
PLAN_REL="$(dirname "$KIT_REL")"
PARENT="${KIT_TEST_TMP:-${TMPDIR:-/tmp}}"
SCRATCH="$(mktemp -d "${PARENT%/}/kit-test.XXXXXX")" || exit 2
GH="$(mktemp -d "${TMPDIR:-/tmp}/kg.XXXXXX")" || exit 2  # short path: gpg-agent socket limit
export GNUPGHOME="$GH" PYTHONDONTWRITEBYTECODE=1 KIT_RETRY_UNIT_SECONDS=0
PASS=0 FAIL=0

cleanup() {
  gpgconf --homedir "$GH" --kill all >/dev/null 2>&1
  case "$GH" in */kg.*) rm -rf -- "$GH" ;; esac
  if [ "$FAIL" -ne 0 ] || [ "${KIT_TEST_KEEP:-0}" = 1 ]; then printf 'scratch kept: %s\n' "$SCRATCH"; return; fi
  case "$SCRATCH" in */kit-test.*) rm -rf -- "$SCRATCH" ;; esac
}
trap cleanup EXIT
ok() { PASS=$((PASS + 1)); printf 'ok   %s\n' "$*"; }
bad() { FAIL=$((FAIL + 1)); printf 'FAIL %s\n' "$*"; }
check() { if [ "$2" -eq 0 ]; then ok "$1"; else bad "$1"; fi; }
refused() {  # $1 label, $2 rc, $3 log, $4 expected text
  if [ "$2" -ne 0 ] && grep -q -- "$4" "$3"; then ok "$1"; else bad "$1 (rc=$2, wanted '$4')"; sed -n '1,15p' "$3"; fi
}

GUARD="$REAL/.claude/scripts/caller_repo_guard.py"
python3 "$GUARD" snapshot --repo "$REAL" --out "$SCRATCH/caller-before.json" || exit 2
CALLER_STATUS="$(git -C "$REAL" status --porcelain --untracked-files=all | shasum -a 256)"

# --- sentinels for the real tools, stub lanes ---------------------------------------------
mkdir -p "$SCRATCH/sentinel" "$SCRATCH/bin" "$SCRATCH/ghstub" || exit 2
for t in codex claude gh; do
  printf '#!/bin/bash\necho "kit test: the real %s was called" >&2\nexit 97\n' "$t" > "$SCRATCH/sentinel/$t"
  chmod 0755 "$SCRATCH/sentinel/$t"
done
PATH="$SCRATCH/sentinel:$PATH"; export PATH
cat > "$SCRATCH/bin/codex-stub" <<'STUB'
#!/bin/bash
# kit-test stub of `codex exec`: insists on the read-only, isolated invocation, answers from the payload.
out="" flags=""
while [ $# -gt 0 ]; do
  case "$1" in
    --output-last-message) out="$2"; shift 2 ;;
    --sandbox) [ "$2" = read-only ] && flags="${flags}r"; shift 2 ;;
    --ignore-user-config) flags="${flags}u"; shift ;;
    --ephemeral) flags="${flags}e"; shift ;;
    *) shift ;;
  esac
done
[ "$flags" = rue ] && [ -n "$out" ] || { echo "stub: not a read-only, isolated codex exec ($flags)" >&2; exit 9; }
[ -z "${OPENAI_API_KEY:-}" ] || { echo "stub: API key leaked into the lane" >&2; exit 9; }
[ ! -e AGENTS.md ] && [ ! -e CLAUDE.md ] && ! git rev-parse --git-dir >/dev/null 2>&1 \
  || { echo "stub: the lane's copy is inside a repository or keeps instruction files" >&2; exit 9; }
part="$(sed -n 's/^PAYLOAD \([0-9]*\)\/.*/\1/p' | head -n 1)"
echo "stub codex transcript for payload $part, cwd /Users/someone/work"
if [ "${STUB_HANG:-}" = "codex:$part" ]; then sleep 300 & echo $! > "$STUB_PIDS.child"; echo $$ > "$STUB_PIDS"; wait; fi
if [ "${STUB_QUOTA:-}" = "codex:$part" ]; then echo "ERROR: You've hit your usage limit. Try again later."; exit 1; fi
v=GO; [ "${STUB_NOGO:-}" != "codex:$part" ] || v=NO-GO
printf 'No findings.\nVERDICT: %s stub review of payload %s.\n' "$v" "$part" > "$out"
STUB
cat > "$SCRATCH/bin/claude-stub" <<'STUB'
#!/bin/bash
# kit-test stub of `claude -p`: refuses --bare, wants the restricted, safe-mode, read-only set.
case " $* " in *" --bare "*) echo "stub: --bare is forbidden (it needs ANTHROPIC_API_KEY)" >&2; exit 9 ;; esac
for w in "-p" "--restricted" "--safe-mode" "--strict-mcp-config" "--tools Read,Grep,Glob" "--permission-mode dontAsk"; do
  case " $* " in *" $w "*) ;; *) echo "stub: claude without $w" >&2; exit 9 ;; esac
done
[ -z "${ANTHROPIC_API_KEY:-}" ] && [ "${DISABLE_AUTOUPDATER:-}" = 1 ] || { echo "stub: API key or auto-updater" >&2; exit 9; }
[ ! -e CLAUDE.md ] && ! git rev-parse --git-dir >/dev/null 2>&1 || { echo "stub: repository or CLAUDE.md around" >&2; exit 9; }
model="" prev=""; for a in "$@"; do [ "$prev" = --model ] && model="$a"; prev="$a"; done
part="$(sed -n 's/^PAYLOAD \([0-9]*\)\/.*/\1/p' | head -n 1)"
printf '{"type":"system","subtype":"init","model":"%s"}\n' "$model"
if [ "${STUB_QUOTA:-}" = "claude:$part" ]; then
  printf '{"type":"result","subtype":"error_during_execution","is_error":true,"errors":["%s"]}\n' "You've hit your limit - resets 7pm"
  exit 1
fi
v=GO extra=""; [ "${STUB_NOGO:-}" != "claude:$part" ] || v=NO-GO
if [ "${STUB_GWC:-}" = "claude:$part" ]; then v=GO-WITH-CONDITIONS extra='P1 src/app.py:3 - stub annex finding.\n'; fi
printf '{"type":"result","subtype":"success","is_error":false,"result":"No findings.\\n%sVERDICT: %s stub review of payload %s."}\n' "$extra" "$v" "$part"
STUB
cat > "$SCRATCH/ghstub/gh" <<'STUB'
#!/bin/bash
# kit-test stub of `gh run list --commit SHA --json ...`: prints STUB_GH_JSON.
printf '%s\n' "$STUB_GH_JSON"
STUB
chmod 0755 "$SCRATCH/bin/codex-stub" "$SCRATCH/bin/claude-stub" "$SCRATCH/ghstub/gh"
STUBS="CODEX_BIN=$SCRATCH/bin/codex-stub CLAUDE_BIN=$SCRATCH/bin/claude-stub"

# --- throwaway key and fixture repository -------------------------------------------------
printf '%s\n' '%no-protection' 'Key-Type: eddsa' 'Key-Curve: Ed25519' 'Name-Real: Kit Test Signer' \
  'Name-Email: kit-test@example.invalid' 'Expire-Date: 0' '%commit' > "$SCRATCH/keyparams"
gpg --batch --quiet --gen-key "$SCRATCH/keyparams" > "$SCRATCH/keygen.log" 2>&1 || { bad "gpg key"; exit 1; }
FPR="$(gpg --batch --with-colons --list-secret-keys | awk -F: '$1 == "fpr" {print $10; exit}')"
[ -n "$FPR" ] || { bad "gpg fingerprint"; exit 1; }
sign() { gpg --batch --yes --quiet -u "$FPR" --armor --detach-sign -o "$2" "$1"; }

FIX0="$SCRATCH/fix0" ORIGIN="$SCRATCH/origin.git"
git init -q -b main "$FIX0" && git init -q --bare "$ORIGIN" || exit 2
for kv in "user.name=Kit Test" "user.email=kit-test@example.invalid" "user.signingkey=$FPR" \
          "commit.gpgsign=false" "tag.gpgSign=false" "core.hooksPath=/dev/null"; do
  git -C "$FIX0" config "${kv%%=*}" "${kv#*=}"
done
git -C "$FIX0" remote add origin "$ORIGIN"
COPIED=".github/scripts/validate-pair-rail-verdict.py .claude/hooks/_lib/__init__.py
.claude/hooks/_lib/cli_currency.py .claude/hooks/_lib/codex_egress_redact.py
.claude/hooks/_lib/secret_patterns.py .claude/scripts/local/_release_tag_guard.py
.claude/governance/codex-cli-pin.txt .claude/governance/codex-cli-pin-manifest.json"
for f in $COPIED; do mkdir -p "$FIX0/$(dirname "$f")" && cp "$REAL/$f" "$FIX0/$f" || exit 2; done
put() { mkdir -p "$FIX0/$(dirname "$1")" && printf '%s\n' "$2" > "$FIX0/$1"; }
relsh() { put .claude/scripts/local/release.sh "$(printf 'TARGET_BASE="%s"\nRELEASE_SCOPE="PLAN-198 (ADRs tocados: nenhum)"' "$1")"; }
put .gitignore "$(printf '.claude/worktrees/\n__pycache__/')"
put .claude/sentinel-signers.txt "$(printf '# throwaway kit-test signer\n%s kit-test' "$FPR")"
put .claude/governance/pair-rail-inputs-hash-manifest.txt "$(printf 'VERSION\n.claude/hooks/_lib/cli_currency.py')"
put VERSION 1.4.3
relsh 1.4.3
put src/app.py "$(printf 'def answer():\n    return 41')"
put tests/test_app.py "$(printf 'def test_answer():\n    pass')"
put CLAUDE.md "Fixture operating contract: obey me."
put AGENTS.md "Fixture reviewer contract: obey me."
BASEFILES="$COPIED .gitignore .claude/sentinel-signers.txt .claude/governance/pair-rail-inputs-hash-manifest.txt
VERSION .claude/scripts/local/release.sh src/app.py tests/test_app.py CLAUDE.md AGENTS.md"
# shellcheck disable=SC2086
git -C "$FIX0" add -- $BASEFILES && git -C "$FIX0" commit -q -m "release: base" && git -C "$FIX0" tag v1.4.2 || exit 2
PB="$(git -C "$FIX0" rev-parse HEAD)"
OLD=".claude/plans/PLAN-OLD" BV=".claude/governance/pair-rail-verdict-v1.4.3-rc.1.md"
BF="$OLD/verdict-fields-v1.4.3-rc.1.md"
put "$OLD/repass-rc1/note.txt" "reviewed base evidence"
( cd "$FIX0/$OLD/repass-rc1" && shasum -a 256 note.txt > MANIFEST-rc1.sha256 ) || exit 2
MSHA="$(shasum -a 256 "$FIX0/$OLD/repass-rc1/MANIFEST-rc1.sha256" | awk '{print $1}')"
printf '%s\n' "verdict: GO" "generated_at: 2026-01-01T00:00:00Z" "parent_sha: $PB" "release_tag: v1.4.3-rc.1" \
  "delta_allowlist:" "  - $BV" "  - $BF" "  - $OLD/repass-rc1/MANIFEST-rc1.sha256" "  - $OLD/repass-rc1/note.txt" \
  "delta_manifest: $OLD/repass-rc1/MANIFEST-rc1.sha256" "delta_manifest_sha256: $MSHA" > "$FIX0/$BF"
sign "$FIX0/$BF" "$SCRATCH/base.asc" || exit 2
{ printf '# Pair-Rail Verdict - v1.4.3-rc.1\n\n```yaml\n'; cat "$FIX0/$BF"
  printf 'gpg_signature: base64:%s\n```\n' "$(base64 < "$SCRATCH/base.asc" | tr -d '\n')"; } > "$FIX0/$BV"
git -C "$FIX0" add -- "$BV" "$BF" "$OLD/repass-rc1/note.txt" "$OLD/repass-rc1/MANIFEST-rc1.sha256" \
  && git -C "$FIX0" commit -q -m "verdict v1.4.3-rc.1" \
  && git -C "$FIX0" tag -s -u "$FPR" -m "v1.4.3-rc.1" v1.4.3-rc.1 || exit 2
# The train: the kit lands before the bump, plus code, docs, a test and the conditions.
for f in gen_envelope.py run_repass.sh test-kit.sh README.md; do
  mkdir -p "$FIX0/$KIT_REL" && cp "$KIT_SRC/$f" "$FIX0/$KIT_REL/$f" || exit 2
done
# A 40-character test secret behind a full-width "=" (U+FF1D), in the conditions (payload header)
# and in a reviewed file (payload diff); built from two halves so no file here holds it whole.
FW1="Q7mZ2xK9pL4vN8bR3tY6" FW2="wC1dF5gH0jS2aE4uI7oP"
put "$PLAN_REL/CONDITIONS-rc1.md" "$(printf '# Conditions (kit test)\n- 1. The stub lanes review nothing # by design.\n- 2. Header redaction probe: aws_secret_access_key\357\274\235%s%s' "$FW1" "$FW2")"
put src/app.py "$(printf 'def answer():\n    return 42\nKEY = "%s%s"' AKIA Z7Q2X9LMNB4KP3TW)"
put docs/guide.md "$(printf 'Notes live in /Users/someone/notes. More to come\342\200\246\naws_secret_access_key\357\274\235%s%s' "$FW1" "$FW2")"  # NFKC-changing chars
put tests/test_app.py "$(printf 'def test_answer():\n    assert True')"
awk 'BEGIN { for (i = 0; i < 6000; i++) printf "VALUE_%05d = \"abcdefghijklmnopqrstuvwxyz0123456789abcdefghij\"\n", i }' \
  > "$FIX0/src/big.py"
git -C "$FIX0" add -- "$KIT_REL/gen_envelope.py" "$KIT_REL/run_repass.sh" "$KIT_REL/test-kit.sh" \
  "$KIT_REL/README.md" "$PLAN_REL/CONDITIONS-rc1.md" src/app.py src/big.py docs/guide.md tests/test_app.py \
  && git -C "$FIX0" commit -q -m "train (PLAN-198)" || exit 2
put VERSION 1.4.4
relsh 1.4.4
git -C "$FIX0" add -- VERSION .claude/scripts/local/release.sh && git -C "$FIX0" commit -q -m "release: v1.4.4" \
  && git -C "$FIX0" push -q origin main refs/tags/v1.4.3-rc.1 || exit 2
CAND="$(git -C "$FIX0" rev-parse HEAD)"
# shellcheck disable=SC2046
set -- $(python3 -c 'import json,sys; m = json.load(open(sys.argv[1])); t = sorted(m["payloads"])[0]
print(m["package_version"], t, m["payloads"][t]["sha256"])' "$FIX0/.claude/governance/codex-cli-pin-manifest.json")
PKG="$1" TRIPLE="$2" PSHA="$3"
CSHA="$(printf 'ab%.0s' $(seq 32))"  # a "compatible" Codex: a version above the manifest, another payload
ok "fixture built (base v1.4.3-rc.1 signed by a throwaway key, candidate ${CAND:0:12})"

# --- helpers over a fixture copy ----------------------------------------------------------
clone_fix() { rm -rf -- "$2"; cp -R "$1" "$2"; }
runner() {  # $1 repo, $2 log, rest: runner args (stub lanes, API keys set to prove they are removed)
  local r="$1" l="$2"; shift 2
  ( cd "$r" && env $STUBS OPENAI_API_KEY=kit-test-not-a-key ANTHROPIC_API_KEY=kit-test-not-a-key \
      bash "$KIT_REL/run_repass.sh" --log "$l.runlog" "$@" ) > "$l" 2>&1
}
gen() { local r="$1" l="$2"; shift 2; ( cd "$r" && python3 "$KIT_REL/gen_envelope.py" "$@" ) > "$l" 2>&1; }
precut() {  # $1 repo, $2 log, $3 the JSON the gh stub prints, rest: precut args
  local r="$1" l="$2" j="$3"; shift 3
  ( cd "$r" && env PATH="$SCRATCH/ghstub:$PATH" STUB_GH_JSON="$j" python3 "$KIT_REL/gen_envelope.py" precut "$@" ) > "$l" 2>&1
}
simulate_real() {  # $1 repo, $2 sfx, $3 version, $4 sha, $5 status: a stub run dressed as a real one
  python3 - "$1/$PLAN_REL/repass-$2" "$3" "$4" "$5" "$TRIPLE" <<'PY'
import hashlib, os, re, sys
ev, ver, sha, status, triple = sys.argv[1:6]
p = os.path.join(ev, [n for n in os.listdir(ev) if n.startswith("PROVENANCE-")][0])
t = open(p, encoding="utf-8").read()
t = re.sub(r"(?m)^- codex: .*$", "- codex: %s / %s / payload %s / status %s" % (ver, triple, sha, status), t)
t = re.sub(r"(?m)^- codex-model: .*$", "- codex-model: gpt-test / effort xhigh (source: kit test)", t)
t = re.sub(r"(?m)^- claude: claude-code-cli-stub ", "- claude: claude-code-cli-9.9.9 ", t)
t = re.sub(r"(?m)^- instrument: STUB.*\n", "", t)
open(p, "w", encoding="utf-8").write(t)
m = os.path.join(ev, [n for n in os.listdir(ev) if n.startswith("MANIFEST-")][0])
names = [ln.split("  ", 1)[1] for ln in open(m, encoding="utf-8").read().splitlines()]
with open(m, "w", encoding="utf-8") as fh:
    for n in names:
        fh.write("%s  %s\n" % (hashlib.sha256(open(os.path.join(ev, n), "rb").read()).hexdigest(), n))
PY
}
step15() {  # $1 repo, $2 tag, $3 parent: the release.yml step-15 validator, standalone
  ( cd "$1" && python3 .github/scripts/validate-pair-rail-verdict.py \
      --verdict-file ".claude/governance/pair-rail-verdict-$2.md" --parent-sha "$3" --release-tag "$2" \
      --max-age-hours 24 --recompute-inputs-hash --codex-cli-pin-file .claude/governance/codex-cli-pin.txt \
      --codex-pin-manifest-file .claude/governance/codex-cli-pin-manifest.json \
      --inputs-hash-paths-file .claude/governance/pair-rail-inputs-hash-manifest.txt ) > "$4" 2>&1
}
commit_verdict() {  # $1 repo, $2 tag
  ( cd "$1" && git --literal-pathspecs add --pathspec-from-file=".claude/worktrees/commit-list-$2.txt" \
      && git commit -q -m "governance(PLAN-198): pair-rail verdict $2 + re-pass evidence" )
}
EVRC="$PLAN_REL/repass-rc1" L="$SCRATCH/logs"
mkdir -p "$L" || exit 2
GREEN='[{"workflowName":"Validate","event":"push","status":"completed","conclusion":"success","databaseId":1},
{"workflowName":"Validate","event":"schedule","status":"completed","conclusion":"success","databaseId":2}]'

# === positive control, rc tag (one lane answers GO-WITH-CONDITIONS with an annex P1) ========
POS="$SCRATCH/pos"
clone_fix "$FIX0" "$POS"
cp -R "$ORIGIN" "$SCRATCH/origin-pos.git" && git -C "$POS" remote set-url origin "$SCRATCH/origin-pos.git"
( export STUB_GWC=claude:1; runner "$POS" "$L/pos-run.log" --tag v1.4.4-rc.1 --conditions "$PLAN_REL/CONDITIONS-rc1.md" ); rc=$?
check "runner, stub lanes, rc tag: exit 0" "$rc"
[ "$rc" -eq 0 ] || sed -n '1,30p' "$L/pos-run.log"
NPARTS="$(sed -n 's/^- parts: //p' "$POS/$EVRC/PROVENANCE-rc1.md")"
[ "${NPARTS:-0}" -ge 2 ] && grep -q 'piece 1/2' "$POS/$EVRC"/paths-rc1-*.txt
check "the big diff is split into pieces across ${NPARTS:-?} payloads under the redactor cap" $?
grep -q '^tests	tests/test_app.py$' "$POS/$EVRC/scope-rc1.txt" \
  && grep -q '^plans	'"$PLAN_REL"'/CONDITIONS-rc1.md$' "$POS/$EVRC/scope-rc1.txt" \
  && grep -q '^in-scope	src/app.py$' "$POS/$EVRC/scope-rc1.txt"
check "scope census: tests and plans out of scope, code in scope" $?
grep -q 'KEY = "\[REDACTED:aws_access_key\]"$' "$POS/$EVRC"/payload-rc1-*.redacted.txt \
  && ! grep -q 'AKIAZ7Q2' "$POS/$EVRC"/payload-rc1-*.redacted.txt && grep -q 'come<U+2026>' "$POS/$EVRC"/payload-rc1-*.redacted.txt
check "payloads went through the ADR-114 redactor, aligned after an NFKC-changing character (<U+2026>)" $?
! grep -q -e "$FW1" -e "$FW2" "$POS/$EVRC"/payload-rc1-*.redacted.txt \
  && [ "$(grep -l '^- 2\. Header redaction probe: \[REDACTED:aws_secret\]$' "$POS/$EVRC"/payload-rc1-*.redacted.txt | wc -l | tr -d ' ')" = "${NPARTS:-0}" ] \
  && grep -q '^+\[REDACTED:aws_secret\]$' "$POS/$EVRC"/payload-rc1-*.redacted.txt
check "a secret after a full-width '=' (U+FF1D) is redacted before the <U+XXXX> escape: diff and every payload header" $?
! grep -rq '/Users/someone' "$POS/$EVRC" && grep -q '/Users/<user>/work' "$POS/$EVRC/codex-rc1-01.log"
check "personal home paths scrubbed from diffs and transcripts" $?
[ -f "$POS/$EVRC/MANIFEST-rc1.sha256" ] && [ -z "$(cd "$POS/$EVRC" && ls -A | grep '^\.')" ] \
  && grep -q '^- instrument: STUB' "$POS/$EVRC/PROVENANCE-rc1.md" && grep -q -- '--safe-mode' "$POS/$EVRC/PROVENANCE-rc1.md"
check "evidence finalized: MANIFEST written, no hidden run files, STUB and lane isolation declared" $?
grep -q ' v1\.4\.4-rc\.1 [0-9a-f]* start resume=0 ' "$POS/.claude/worktrees/repass-attempts.log" \
  && grep -q ' v1\.4\.4-rc\.1 [0-9a-f]* end rc=0 nogo=0 manifest=[0-9a-f]' "$POS/.claude/worktrees/repass-attempts.log"
check "attempts ledger: start and end of the attempt recorded outside the evidence directory" $?
STUBRUN="$SCRATCH/stubrun"
clone_fix "$POS" "$STUBRUN"
gen "$STUBRUN" "$L/stub-fields.log" fields --tag v1.4.4-rc.1; rc=$?
refused "generator refuses stub-lane evidence" "$rc" "$L/stub-fields.log" "STUB"
simulate_real "$POS" rc1 "$PKG" "$PSHA" verified
RUNOK="$SCRATCH/runok"
clone_fix "$POS" "$RUNOK"
gen "$POS" "$L/pos-fields.log" fields --tag v1.4.4-rc.1; rc=$?
check "fields stage (validator self-check inside): exit 0" "$rc"
[ "$rc" -eq 0 ] || sed -n '1,20p' "$L/pos-fields.log"
VF="$POS/$PLAN_REL/verdict-fields-v1.4.4-rc.1.md"
grep -q '^verdict: GO-WITH-CONDITIONS$' "$VF" \
  && grep -q '^  - claude-p01 VERDICT: GO-WITH-CONDITIONS stub review of payload 1\.$' "$VF" \
  && grep -q '^  - claude-p01 P1 src/app.py:3 - stub annex finding\.$' "$VF" \
  && grep -q '^  - [^ ]* v1\.4\.4-rc\.1 [0-9a-f]* end rc=0 nogo=0 manifest=' "$VF" \
  && grep -q '^attempts_ledger_sha256: [0-9a-f]\{64\}$' "$VF" && grep -q 'release-scope-covers-v1.4.2' "$VF"
check "fields carry the lane's conditional verdict, its annex P1, every attempt and the scope check" $?
sign "$VF" "$SCRATCH/pos.asc"
SIGNED="$SCRATCH/signed"
clone_fix "$POS" "$SIGNED"
gen "$POS" "$L/pos-env.log" envelope --tag v1.4.4-rc.1 --sig "$SCRATCH/pos.asc"; rc=$?
check "envelope stage (signature, re-derivation, validator self-check): exit 0" "$rc"
[ "$rc" -eq 0 ] || sed -n '1,20p' "$L/pos-env.log"
gen "$POS" "$L/pos-verify.log" verify --tag v1.4.4-rc.1 --sig "$SCRATCH/pos.asc"
check "verify stage agrees with the written envelope" $?
commit_verdict "$POS" v1.4.4-rc.1
check "commit of exactly the listed files" $?
( cd "$POS" && python3 .claude/scripts/local/_release_tag_guard.py delta --tag v1.4.4-rc.1 ) > "$L/pos-guard.log" 2>&1
check "the REAL tag guard accepts the rc verdict commit (delta, manifest, allowlist)" $?
step15 "$POS" v1.4.4-rc.1 "$CAND" "$L/pos-step15.log"
check "the REAL step-15 validator accepts the rc envelope (GO-WITH-CONDITIONS, lane notes, attempts)" $?
( cd "$POS" && python3 .github/scripts/validate-pair-rail-verdict.py --verdict-file \
    .claude/governance/pair-rail-verdict-v1.4.4-rc.1.md --release-tag v1.4.4 ) > "$L/wrongtag-step15.log" 2>&1
[ $? -eq 3 ] && grep -q 'release_tag mismatch' "$L/wrongtag-step15.log"
check "wrong tag: the rc envelope is INVALID for v1.4.4 at step 15 (exit 3)" $?
precut "$POS" "$L/precut.log" "$GREEN" --tag v1.4.4-rc.1 --require-schedule
check "precut: the signed Scope line holds and every run on HEAD is green, a scheduled one included" $?
precut "$POS" "$L/precut-red.log" '[{"workflowName":"Validate","event":"push","status":"completed","conclusion":"success","databaseId":1},{"workflowName":"Ownership Nightly","event":"schedule","status":"completed","conclusion":"failure","databaseId":3}]' --tag v1.4.4-rc.1; rc=$?
refused "precut: a red scheduled run on the frozen HEAD refuses the cut" "$rc" "$L/precut-red.log" "not completed green"
precut "$POS" "$L/precut-nosched.log" '[{"workflowName":"Validate","event":"push","status":"completed","conclusion":"success","databaseId":1}]' --tag v1.4.4-rc.1 --require-schedule; rc=$?
refused "precut --require-schedule: no scheduled Validate on HEAD yet" "$rc" "$L/precut-nosched.log" "SCHEDULED"
precut "$POS" "$L/precut-cionly.log" "$GREEN" --tag v1.4.5-rc.1 --ci-only --require-schedule
check "precut --ci-only (before the release metadata and the bump): the CI part alone" $?

# === positive control, rc tag with a "compatible" Codex through the real validator =========
N="$SCRATCH/n-compat"; clone_fix "$STUBRUN" "$N"
simulate_real "$N" rc1 0.999.0 "$CSHA" compatible
gen "$N" "$L/compat-fields.log" fields --tag v1.4.4-rc.1 && sign "$N/$PLAN_REL/verdict-fields-v1.4.4-rc.1.md" "$SCRATCH/compat.asc" \
  && gen "$N" "$L/compat-env.log" envelope --tag v1.4.4-rc.1 --sig "$SCRATCH/compat.asc" && commit_verdict "$N" v1.4.4-rc.1 \
  && ( cd "$N" && python3 .claude/scripts/local/_release_tag_guard.py delta --tag v1.4.4-rc.1 ) > "$L/compat-guard.log" 2>&1 \
  && step15 "$N" v1.4.4-rc.1 "$CAND" "$L/compat-step15.log" && grep -q 'INFO: codex_cli 0.999.0 is newer' "$L/compat-step15.log"
check "compatible Codex (newer than the manifest, other payload): fields, envelope, tag guard and step 15 accept it" $?

# === positive control, GA tag ===============================================================
( cd "$POS" && git tag -s -u "$FPR" -m "v1.4.4-rc.1" v1.4.4-rc.1 && git push -q origin main refs/tags/v1.4.4-rc.1 ) \
  > "$L/ga-tag.log" 2>&1 || bad "rc tag and push in the positive fixture"
runner "$POS" "$L/ga-nocond.log" --tag v1.4.4; rc=$?
refused "GA without the carried rc conditions: refused before any lane" "$rc" "$L/ga-nocond.log" "carry-conditions"
gen "$POS" "$L/carry.log" carry-conditions --tag v1.4.4; rc=$?
grep -q '^- 1. The stub lanes review nothing' "$POS/$PLAN_REL/CONDITIONS-ga.md" \
  && grep -q '^- claude-p01 P1 src/app.py:3' "$POS/$PLAN_REL/CONDITIONS-ga.md"
check "carry-conditions writes CONDITIONS-ga.md from the signed rc conditions and lane notes" $(( rc + $? ))
( cd "$POS" && git add -- "$PLAN_REL/CONDITIONS-ga.md" && git commit -q -m "plan(PLAN-198): conditions of v1.4.4" \
    && git push -q origin main ) > "$L/ga-cond.log" 2>&1 || bad "GA conditions commit in the positive fixture"
runner "$POS" "$L/ga-run.log" --tag v1.4.4 --conditions "$PLAN_REL/CONDITIONS-ga.md"; rc=$?
check "runner, GA tag (base derived, rc custody, carried conditions): exit 0" "$rc"
[ "$rc" -eq 0 ] || sed -n '1,30p' "$L/ga-run.log"
grep -q '^- base: v1.4.3-rc.1 ' "$POS/$PLAN_REL/repass-ga/PROVENANCE-ga.md" \
  && grep -q '^- rc-tag: v1.4.4-rc.1$' "$POS/$PLAN_REL/repass-ga/PROVENANCE-ga.md"
check "GA base defaults to v1.4.3-rc.1, not to the rc of the same version" $?
FREEZE="$SCRATCH/freeze"
clone_fix "$POS" "$FREEZE"
simulate_real "$POS" ga "$PKG" "$PSHA" verified
gen "$POS" "$L/ga-fields.log" fields --tag v1.4.4; rc=$?
check "GA fields stage: exit 0" "$rc"
[ "$rc" -eq 0 ] || sed -n '1,20p' "$L/ga-fields.log"
sign "$POS/$PLAN_REL/verdict-fields-v1.4.4.md" "$SCRATCH/ga.asc"
gen "$POS" "$L/ga-env.log" envelope --tag v1.4.4 --sig "$SCRATCH/ga.asc"
check "GA envelope stage: exit 0" $?
GA_CAND="$(git -C "$POS" rev-parse HEAD)"
commit_verdict "$POS" v1.4.4 \
  && ( cd "$POS" && python3 .claude/scripts/local/_release_tag_guard.py delta --tag v1.4.4 ) > "$L/ga-guard.log" 2>&1
check "the REAL tag guard accepts the GA verdict commit" $?
step15 "$POS" v1.4.4 "$GA_CAND" "$L/ga-step15.log"
check "the REAL step-15 validator accepts the GA envelope" $?
simulate_real "$FREEZE" ga 0.999.0 "$CSHA" compatible
gen "$FREEZE" "$L/freeze.log" fields --tag v1.4.4; rc=$?
refused "GA refuses a Codex instrument that changed since the rc" "$rc" "$L/freeze.log" "instrument changed since"

# === named negatives ========================================================================
N="$SCRATCH/n-tag"; clone_fix "$RUNOK" "$N"
gen "$N" "$L/n-tag.log" fields --tag v1.4.5-rc.1; rc=$?
refused "wrong tag: fields for a tag the candidate was not bumped to" "$rc" "$L/n-tag.log" "does not match the candidate"

resign_fields() {  # $1 stale|missing|future: edit generated_at in the signed copy's fields, sign again
  python3 - "$SIGNED/$PLAN_REL/verdict-fields-v1.4.4-rc.1.md" "$1" <<'PY'
import re, sys
from datetime import datetime, timedelta, timezone
p, mode = sys.argv[1], sys.argv[2]
when = datetime.now(timezone.utc) + timedelta(hours=2 if mode == "future" else -25)
t = re.sub(r"(?m)^generated_at: .*\n",
           "" if mode == "missing" else "generated_at: %s\n" % when.strftime("%Y-%m-%dT%H:%M:%SZ"),
           open(p, encoding="utf-8").read())
open(p, "w", encoding="utf-8").write(t)
PY
  sign "$SIGNED/$PLAN_REL/verdict-fields-v1.4.4-rc.1.md" "$SCRATCH/$1.asc"
}
resign_fields stale
gen "$SIGNED" "$L/n-stale.log" envelope --tag v1.4.4-rc.1 --sig "$SCRATCH/stale.asc"; rc=$?
refused "stale generated_at (25 h): envelope refused" "$rc" "$L/n-stale.log" "EXPIRED"
[ ! -e "$SIGNED/.claude/governance/pair-rail-verdict-v1.4.4-rc.1.md" ]
check "nothing written for the stale envelope" $?
resign_fields future
gen "$SIGNED" "$L/n-future.log" envelope --tag v1.4.4-rc.1 --sig "$SCRATCH/future.asc"; rc=$?
refused "generated_at in the future: envelope refused" "$rc" "$L/n-future.log" "in the future"
resign_fields missing
gen "$SIGNED" "$L/n-missing.log" envelope --tag v1.4.4-rc.1 --sig "$SCRATCH/missing.asc"; rc=$?
refused "missing generated_at: envelope refused" "$rc" "$L/n-missing.log" "exactly one 'generated_at"

N="$SCRATCH/n-floor"; clone_fix "$RUNOK" "$N"
simulate_real "$N" rc1 0.159.0 "$PSHA" verified
gen "$N" "$L/n-floor.log" fields --tag v1.4.4-rc.1; rc=$?
refused "codex 0.159.0 with the manifest's sha: refused by the generator" "$rc" "$L/n-floor.log" "below the ADR-182 floor"
sed 's/^  codex_cli: .*/  codex_cli: 0.159.0/' "$POS/.claude/governance/pair-rail-verdict-v1.4.4-rc.1.md" > "$SCRATCH/floor.md"
( cd "$POS" && python3 .github/scripts/validate-pair-rail-verdict.py --verdict-file "$SCRATCH/floor.md" \
    --release-tag v1.4.4-rc.1 --codex-cli-pin-file .claude/governance/codex-cli-pin.txt \
    --codex-pin-manifest-file .claude/governance/codex-cli-pin-manifest.json ) > "$L/n-floor-step15.log" 2>&1
printf 'info the step-15 validator ALONE returns rc=%s for codex_cli 0.159.0 with the manifest sha\n' "$?"

N="$SCRATCH/n-nogo"; clone_fix "$FIX0" "$N"
( export STUB_NOGO=claude:1; runner "$N" "$L/n-nogo-run.log" --tag v1.4.4-rc.1 ); rc=$?
[ "$rc" -eq 1 ] && grep -q '^RUNNER-OVERALL: rc=1$' "$N/$EVRC/PROVENANCE-rc1.md"
check "lane NO-GO: runner exits 1 and records RUNNER-OVERALL rc=1" $?
simulate_real "$N" rc1 "$PKG" "$PSHA" verified
gen "$N" "$L/n-nogo.log" fields --tag v1.4.4-rc.1; rc=$?
refused "lane NO-GO: generator refuses" "$rc" "$L/n-nogo.log" "says NO-GO"
mv "$N/$EVRC" "$SCRATCH/nogo-moved-out" || bad "moving the NO-GO attempt out"
runner "$N" "$L/n-reroll-run.log" --tag v1.4.4-rc.1; rc=$?
simulate_real "$N" rc1 "$PKG" "$PSHA" verified
gen "$N" "$L/n-reroll.log" fields --tag v1.4.4-rc.1; rc2=$?
[ "$rc" -eq 0 ] || bad "the re-roll run itself (rc=$rc)"
refused "NO-GO re-roll (attempt moved out, same candidate run again, all GO): refused by the ledger" "$rc2" "$L/n-reroll.log" "recorded a NO-GO"
mv "$N/$EVRC" "$SCRATCH/reroll-moved-out" || bad "moving the re-roll attempt out"
runner "$N" "$L/n-rc2-run.log" --tag v1.4.4-rc.2; rc=$?
simulate_real "$N" rc2 "$PKG" "$PSHA" verified
gen "$N" "$L/n-rc2.log" fields --tag v1.4.4-rc.2; rc2=$?
[ "$rc" -eq 0 ] || bad "the v1.4.4-rc.2 run itself (rc=$rc)"
refused "NO-GO recorded under v1.4.4-rc.1 blocks v1.4.4-rc.2 on the same candidate (ledger, any tag)" "$rc2" "$L/n-rc2.log" "recorded a NO-GO"

N="$SCRATCH/n-drift"; clone_fix "$RUNOK" "$N"
put_n() { mkdir -p "$N/$(dirname "$1")" && printf '%s\n' "$2" > "$N/$1"; }
put_n src/late.py "LATE = 1"
( cd "$N" && git add -- src/late.py && git commit -q -m "late change" ) || bad "drift commit"
gen "$N" "$L/n-drift.log" fields --tag v1.4.4-rc.1; rc=$?
refused "candidate drift: a commit after the re-pass" "$rc" "$L/n-drift.log" "but HEAD is"

N="$SCRATCH/n-scope"; clone_fix "$RUNOK" "$N"
put_n src/late2.py "LATE = 2"
( cd "$N" && git add -- src/late2.py && git commit -q -m "late fix (PLAN-999)" ) || bad "scope commit"
precut "$N" "$L/n-scope.log" "$GREEN" --tag v1.4.4-rc.1; rc=$?
refused "RELEASE_SCOPE: a commit citing a plan the signed Scope line omits refuses the cut" "$rc" "$L/n-scope.log" "does not list: PLAN-999"

N="$SCRATCH/n-tamper"; clone_fix "$RUNOK" "$N"
printf ' ' >> "$N/$EVRC/payload-rc1-01.redacted.txt"
simulate_real "$N" rc1 "$PKG" "$PSHA" verified
gen "$N" "$L/n-tamper.log" fields --tag v1.4.4-rc.1; rc=$?
refused "evidence tamper (MANIFEST rewritten to match): payload re-derivation refuses" "$rc" "$L/n-tamper.log" "differs from its re-derivation"

N="$SCRATCH/n-again"; clone_fix "$RUNOK" "$N"
runner "$N" "$L/n-again.log" --tag v1.4.4-rc.1; rc=$?
[ "$rc" -eq 2 ] && grep -q 'never deletes an attempt' "$L/n-again.log" && tail -n 1 "$L/n-again.log.runlog" | grep -q 'runner exit rc=2$'
check "a second run never overwrites a previous attempt (exit 2, the log ends with 'runner exit rc=2')" $?
( cd "$N" && env $STUBS bash "$KIT_REL/run_repass.sh" --tag v1.4.4-rcX ) > /dev/null 2>&1; rc=$?
[ "$rc" -eq 2 ] && grep -q 'REFUSED: --tag must be' "$N/.claude/worktrees/repass-unknown.log" \
  && tail -n 1 "$N/.claude/worktrees/repass-unknown.log" | grep -q 'runner exit rc=2$'
check "an unreadable --tag under nohup still leaves a log ending with 'runner exit rc=2'" $?

N="$SCRATCH/n-quota"; clone_fix "$FIX0" "$N"
( export STUB_QUOTA=codex:1; runner "$N" "$L/n-quota-run.log" --tag v1.4.4-rc.1 --jobs 1 ); rc=$?
[ "$rc" -eq 3 ] && [ ! -e "$N/$EVRC/MANIFEST-rc1.sha256" ] && [ -f "$N/$EVRC/.rc-codex-01" ] \
  && ! grep -q 'payload 02' "$L/n-quota-run.log.runlog"
check "account limit (Codex): exit 3, evidence kept unfinalized, no new payload launched" $?
printf 'stray\n' > "$N/$EVRC/stray.txt"
runner "$N" "$L/n-resume.log" --tag v1.4.4-rc.1 --resume; rc=$?
[ "$rc" -eq 3 ] && grep -q 'payload 01 claude: kept from the previous attempt' "$L/n-resume.log" \
  && grep -q 'finalize refused' "$L/n-resume.log" && [ -f "$N/$EVRC/.header" ] && [ -f "$N/$EVRC/.rc-codex-01" ] \
  && ls "$N/.claude/worktrees/repass-rc1-kept/" | grep -q '^codex-rc1-01.log\.'
check "--resume re-runs only the dead lane; a finalize refusal gives back .header and the lane records" $?
rm -f "$N/$EVRC/stray.txt"
runner "$N" "$L/n-resume2.log" --tag v1.4.4-rc.1 --resume; rc=$?
[ "$rc" -eq 0 ] && grep -q 'payload 01 codex: kept from the previous attempt' "$L/n-resume2.log" \
  && [ -f "$N/$EVRC/MANIFEST-rc1.sha256" ]
check "--resume after the finalize refusal finalizes without re-running a lane" $?

N="$SCRATCH/n-cquota"; clone_fix "$FIX0" "$N"
( export STUB_QUOTA=claude:1; runner "$N" "$L/n-cquota.log" --tag v1.4.4-rc.1 --jobs 1 ); rc=$?
[ "$rc" -eq 3 ] && grep -q '^claude 01$' "$N/$EVRC/.quota" && ! grep -q 'payload 02' "$L/n-cquota.log.runlog"
check "account limit (Claude, message in the errors field): .quota written, dispatch stops (exit 3)" $?
CR="$SCRATCH/claude-results"; mkdir -p "$CR"
python3 - "$CR" <<'PY'
import json, os, sys
d, init = sys.argv[1], {"type": "system", "subtype": "init", "model": "claude-opus-5-5"}
def w(name, *objs):
    with open(os.path.join(d, name), "w", encoding="utf-8") as fh:
        fh.write("".join(json.dumps(o) + "\n" for o in objs))
w("a", init, {"type": "result", "subtype": "success", "is_error": True,
              "result": "You've hit your session limit · resets 7pm (America/Sao_Paulo)"})
w("b", init, {"type": "assistant", "error": "rate_limit", "message": {"content": []}})
w("c", init, {"type": "result", "subtype": "success", "is_error": False,
              "result": "You've hit your weekly limit · resets Oct 12 at 8am"})
w("d", init, {"type": "result", "subtype": "success", "is_error": False,
              "result": "The rate limit code is fine.\nVERDICT: GO nothing found."})
w("e", dict(init, model="claude-sonnet-5"), {"type": "result", "subtype": "success", "is_error": False,
                                              "result": "VERDICT: GO nothing found."})
PY
got=""
for f in a b c d e; do
  ( cd "$POS" && python3 "$KIT_REL/gen_envelope.py" claude-result --model claude-opus-5-5 "$CR/$f" "$CR/$f.out" ) 2>/dev/null
  got="$got$?"
done
[ "$got" = 44406 ]
check "claude-result: 3 measured limit forms -> 4, a review that mentions rate limits -> 0, another model -> 6 (got $got)" $?

N="$SCRATCH/n-signal"; clone_fix "$FIX0" "$N"
PIDS="$SCRATCH/stub-pids"
( cd "$N" && exec env $STUBS STUB_HANG=codex:1 STUB_PIDS="$PIDS" bash "$KIT_REL/run_repass.sh" \
    --log "$L/n-signal.runlog" --tag v1.4.4-rc.1 --jobs 1 ) > "$L/n-signal.log" 2>&1 &
RP=$!
k=0; while [ ! -s "$PIDS" ] && [ "$k" -lt 300 ]; do sleep 0.1; k=$((k + 1)); done
kill -TERM "$RP"; wait "$RP"; rc=$?
sleep 0.5
[ "$rc" -eq 3 ] && [ -s "$PIDS" ] && ! kill -0 "$(cat "$PIDS")" 2>/dev/null && ! kill -0 "$(cat "$PIDS.child")" 2>/dev/null \
  && [ -z "$(ls -d "$N"/.claude/worktrees/repass-rc1-run.* 2>/dev/null)" ] \
  && tail -n 1 "$L/n-signal.runlog" | grep -q 'runner exit rc=3$'
check "TERM: the reviewer process tree (and its child) is stopped and reaped before cleanup (exit 3)" $?
[ "$rc" -eq 3 ] || sed -n '1,20p' "$L/n-signal.log"

# === the calling repository is untouched ====================================================
python3 "$GUARD" verify --repo "$REAL" --from "$SCRATCH/caller-before.json"
check "caller repository: HEAD, symbolic-ref and refs unchanged" $?
[ "$(git -C "$REAL" status --porcelain --untracked-files=all | shasum -a 256)" = "$CALLER_STATUS" ]
check "caller repository: working tree status unchanged" $?
printf '\n%d passed, %d failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ]
