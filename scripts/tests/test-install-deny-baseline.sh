#!/usr/bin/env bash
# PLAN-153 Wave E item 3 — behavioral test for the install-time coarse
# credential-read deny baseline (install.sh section 6a).
#
# Doctrine: BEHAVIORAL OVER STATIC. This runs the REAL installer and
# asserts on the settings.json it actually produces — including the
# planted-violation angle we CAN replay without the Claude Code harness:
# the exclusion set (.env.example/.env.sample/.env.template) must NOT be
# denied, and the ratified sensitive set MUST be. What this test cannot
# certify (documented in docs/deny-baseline.md): that the live harness
# enforces the rules — deny-rule ENFORCEMENT belongs to Claude Code, not
# this repo; the baseline is a coarse backstop, never sold as coverage.
#
# Asserts:
#   (A) fresh install (maintainer, base) -> permissions.deny contains ALL
#       20 baseline entries, template deny entries preserved FIRST
#       (order-preserving append), no duplicates, .env.example NOT denied,
#       statusLine key survives the rewrite, file is valid JSON.
#   (B) re-running install.sh over the same target -> settings.json
#       byte-identical (EXISTS->SKIP idempotency; no duplicate entries).
#   (C) CEO_INSTALL_SKIP_DENY_BASELINE=1 -> baseline absent (opt-out).
#   (D) --ceremony user (settings.user.json has NO permissions block) ->
#       permissions.deny is CREATED with exactly the baseline.
#   (E) jq hidden from PATH -> python3 fallback still applies the baseline
#       (base-only install needs no jq; the injection must not either).
#
# stdlib + bash-3.2-safe. Needs python3 (assertions) and, for leg E,
# a python3 visible without jq.
#
# Usage:
#   bash scripts/tests/test-install-deny-baseline.sh
# Exits 0 on success, non-zero on any failed assertion.

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SOURCE_DIR="$( cd "$SCRIPT_DIR/../.." && pwd )"
# Override point so the test can be pointed at a staged/candidate installer
# while it still lives in a plan-staging mirror (PLAN-153 discipline).
INSTALL="${CEO_INSTALL_UNDER_TEST:-$SOURCE_DIR/scripts/install.sh}"

if ! command -v python3 >/dev/null 2>&1; then
  echo "==> SKIP: python3 not installed"
  exit 0
fi

fail=0

# NOTE: install logs/snapshots are SIBLINGS of the target dirs, never inside
# them — the --ceremony user leg of install.sh fails the run if anything
# outside .claude/ is touched in the target (WS4 guard).
T_A="$(mktemp -d -t ceo-denybase-a-XXXXXX)"
T_C="$(mktemp -d -t ceo-denybase-c-XXXXXX)"
T_D="$(mktemp -d -t ceo-denybase-d-XXXXXX)"
T_E="$(mktemp -d -t ceo-denybase-e-XXXXXX)"
FAKEBIN="$(mktemp -d -t ceo-denybase-nojq-XXXXXX)"
cleanup() {
  rm -rf "$T_A" "$T_C" "$T_D" "$T_E" "$FAKEBIN" \
    "$T_A.install.log" "$T_A.install-rerun.log" "$T_A.settings.snapshot" \
    "$T_C.install.log" "$T_D.install.log" "$T_E.install.log"
}
trap cleanup EXIT

for t in "$T_A" "$T_C" "$T_D" "$T_E"; do
  ( cd "$t" && git init -q )
done

run_install() {
  # $1 = target, remaining args passed through. Source-tree installs carry
  # the PLACEHOLDER self-SHA trailer; skip explicitly so a staged candidate
  # (whose body differs from any release trailer) also runs.
  local target="$1"; shift
  CEO_INSTALL_SKIP_SELF_SHA=1 CEO_RAG_INSTALL_PROMPT=0 \
    bash "$INSTALL" "$target" "$@"
}

# Shared python assertion helper: args = settings.json path, leg label.
assert_baseline() {
  python3 - "$1" "$2" <<'PY'
import json
import sys

path, leg = sys.argv[1], sys.argv[2]
ok = True

def check(cond, msg):
    global ok
    if not cond:
        print("::error::[%s] %s" % (leg, msg), file=sys.stderr)
        ok = False
    else:
        print("    [%s] PASS: %s" % (leg, msg))

d = json.load(open(path))
deny = d.get("permissions", {}).get("deny", [])

BASELINE = [
    "Read(~/.ssh/**)",
    "Read(~/.aws/**)",
    "Read(~/.npmrc)",
    "Read(~/.config/gcloud/**)",
    "Read(~/.kube/config)",
    "Read(~/.docker/config.json)",
    "Read(~/.git-credentials)",
    "Read(~/.netrc)",
    "Read(~/.pypirc)",
    "Read(**/.env)",
    "Read(**/.env.local)",
    "Read(**/.env.*.local)",
    "Read(**/.env.development)",
    "Read(**/.env.dev)",
    "Read(**/.env.production)",
    "Read(**/.env.prod)",
    "Read(**/.env.staging)",
    "Read(**/.env.test)",
    "Read(**/.env.ci)",
    "Bash(curl * | bash)",
]

for entry in BASELINE:
    check(entry in deny, "deny contains %r" % entry)

# Planted-exclusion positive control: the example/sample/template variants
# must NOT be denied (deny-specific-patterns-only fallback: deny+allow
# precedence cannot express the exception, so they are simply not listed).
for excluded in ("Read(**/.env.example)", "Read(**/.env.sample)",
                 "Read(**/.env.template)"):
    check(excluded not in deny, "deny does NOT contain %r (exclusion honored)" % excluded)
check(not any(".env.example" in e or ".env.sample" in e or ".env.template" in e
              for e in deny),
      "no deny entry matches the example/sample/template exclusion set")

# No duplicates (idempotent merge).
check(len(deny) == len(set(deny)), "deny list has no duplicates")

sys.exit(0 if ok else 1)
PY
}

# --- (A) fresh maintainer install: baseline merged, template deny preserved --
echo "==> [A] fresh install into $T_A"
LOG_A="$T_A.install.log"
if ! run_install "$T_A" --profile core --stack none >"$LOG_A" 2>&1; then
  echo "::error::[A] install.sh failed (see log)"
  tail -30 "$LOG_A" >&2
  exit 1
fi
SETTINGS_A="$T_A/.claude/settings.json"
if [[ ! -f "$SETTINGS_A" ]]; then
  echo "::error::[A] settings.json not produced"
  exit 1
fi
assert_baseline "$SETTINGS_A" "A" || fail=1

python3 - "$SETTINGS_A" <<'PY' || fail=1
import json
import sys

d = json.load(open(sys.argv[1]))
ok = True

def check(cond, msg):
    global ok
    if not cond:
        print("::error::[A] " + msg, file=sys.stderr)
        ok = False
    else:
        print("    [A] PASS: " + msg)

deny = d.get("permissions", {}).get("deny", [])
# Template-shipped deny entries must survive, and must come FIRST
# (order-preserving append, not a rewrite).
template_head = [
    "Bash(git push --force*)",
    "Edit(PROTOCOL.md)",
    "Write(PROTOCOL.md)",
]
check(deny[:3] == template_head,
      "template deny entries preserved in original order at the head")
# The rewrite must not drop sibling keys (smoke-install.sh contract).
sl = d.get("statusLine") or {}
check("statusline-ceo.py" in (sl.get("command") or ""),
      "statusLine survived the deny-baseline rewrite")
check("allow" in d.get("permissions", {}),
      "permissions.allow survived the rewrite")
sys.exit(0 if ok else 1)
PY

# --- (B) re-run over same target: EXISTS->SKIP, byte-identical --------------
echo "==> [B] re-run install over $T_A (idempotency)"
SNAP_B="$T_A.settings.snapshot"
cp "$SETTINGS_A" "$SNAP_B"
LOG_B="$T_A.install-rerun.log"
if ! run_install "$T_A" --profile core --stack none >"$LOG_B" 2>&1; then
  echo "::error::[B] re-run install.sh failed (see log)"
  tail -30 "$LOG_B" >&2
  exit 1
fi
if cmp -s "$SNAP_B" "$SETTINGS_A"; then
  echo "    [B] PASS: settings.json byte-identical after re-run (no duplicate entries)"
else
  echo "::error::[B] settings.json changed on re-run (idempotency broken)"
  fail=1
fi
rm -f "$SNAP_B"

# --- (C) opt-out env var ------------------------------------------------------
# NOTE: call bash directly (not run_install) — an env-assignment prefix on a
# shell FUNCTION persists in the caller's environment (POSIX quirk) and would
# leak the opt-out into legs D/E.
echo "==> [C] CEO_INSTALL_SKIP_DENY_BASELINE=1 into $T_C"
LOG_C="$T_C.install.log"
if ! env CEO_INSTALL_SKIP_DENY_BASELINE=1 CEO_INSTALL_SKIP_SELF_SHA=1 \
     CEO_RAG_INSTALL_PROMPT=0 \
     bash "$INSTALL" "$T_C" --profile core --stack none >"$LOG_C" 2>&1; then
  echo "::error::[C] opt-out install.sh failed (see log)"
  tail -30 "$LOG_C" >&2
  exit 1
fi
python3 - "$T_C/.claude/settings.json" <<'PY' || fail=1
import json
import sys

d = json.load(open(sys.argv[1]))
deny = d.get("permissions", {}).get("deny", [])
bad = [e for e in deny if e.startswith("Read(~/.ssh") or e == "Bash(curl * | bash)"]
if bad:
    print("::error::[C] opt-out ignored — baseline entries present: %r" % bad,
          file=sys.stderr)
    sys.exit(1)
print("    [C] PASS: CEO_INSTALL_SKIP_DENY_BASELINE=1 leaves the template deny list untouched")
PY

# --- (D) user ceremony: permissions block created from nothing ---------------
echo "==> [D] --ceremony user into $T_D"
LOG_D="$T_D.install.log"
if ! run_install "$T_D" --ceremony user >"$LOG_D" 2>&1; then
  echo "::error::[D] --ceremony user install.sh failed (see log)"
  tail -30 "$LOG_D" >&2
  exit 1
fi
assert_baseline "$T_D/.claude/settings.json" "D" || fail=1

# --- (E) jq hidden: python3 fallback path ------------------------------------
echo "==> [E] jq hidden from PATH (python3 fallback) into $T_E"
# Mirror EVERY executable on the current PATH into FAKEBIN except jq, then
# run the installer with PATH=$FAKEBIN. Robust against install.sh growing
# new tool dependencies (vs. hand-enumerating a command list).
IFS=':' read -r -a _path_dirs <<< "$PATH"
for _d in "${_path_dirs[@]}"; do
  [ -d "$_d" ] || continue
  for _f in "$_d"/*; do
    [ -x "$_f" ] || continue
    [ -d "$_f" ] && continue
    _b="$(basename "$_f")"
    [ "$_b" = "jq" ] && continue
    [ -e "$FAKEBIN/$_b" ] || ln -s "$_f" "$FAKEBIN/$_b" 2>/dev/null || true
  done
done
LOG_E="$T_E.install.log"
if ! env PATH="$FAKEBIN" \
     CEO_INSTALL_SKIP_SELF_SHA=1 CEO_RAG_INSTALL_PROMPT=0 \
     bash "$INSTALL" "$T_E" --profile core >"$LOG_E" 2>&1; then
  echo "::error::[E] no-jq install.sh failed (see log)"
  tail -30 "$LOG_E" >&2
  exit 1
fi
assert_baseline "$T_E/.claude/settings.json" "E" || fail=1
if grep -q "python3; docs/deny-baseline.md" "$LOG_E"; then
  echo "    [E] PASS: python3 fallback path was the one taken (jq absent)"
else
  echo "::error::[E] expected the python3 fallback merge message in the install log"
  fail=1
fi

# --- verdict ------------------------------------------------------------------
if [[ "$fail" -ne 0 ]]; then
  echo "==> FAIL: install deny-baseline test"
  exit 1
fi
echo "==> PASS: deny baseline merged, ordered, deduplicated, opt-out honored, exclusions honored, no-jq fallback works"
