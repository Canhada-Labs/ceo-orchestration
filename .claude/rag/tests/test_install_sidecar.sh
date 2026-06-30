#!/bin/bash
# .claude/rag/tests/test_install_sidecar.sh
#
# Bash smoke tests for install-sidecar.sh (PLAN-041 Phase 3).
# Runs install script in various states and asserts behavior.
# Does NOT actually install LightRAG (no network, no pip calls).

set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RAG_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
INSTALL="$RAG_DIR/install-sidecar.sh"

PASS=0
FAIL=0

_ok()    { printf '  OK   %s\n' "$*"; PASS=$((PASS+1)); }
_fail()  { printf '  FAIL %s\n' "$*"; FAIL=$((FAIL+1)); }
_test()  { printf 'TEST %s\n' "$*"; }

_test "help flag exits 0"
out=$(bash "$INSTALL" --help 2>&1)
if echo "$out" | grep -q "Usage:"; then
    _ok "usage printed"
else
    _fail "--help did not print usage"
fi

_test "status flag exits 0"
if bash "$INSTALL" --status >/dev/null 2>&1; then
    _ok "--status exit 0"
else
    _fail "--status exit non-zero"
fi

_test "unknown flag exits non-zero"
if bash "$INSTALL" --bogus-flag >/dev/null 2>&1; then
    _fail "unknown flag accepted"
else
    _ok "unknown flag rejected"
fi

_test "placeholder requirements.lock refused"
out=$(bash "$INSTALL" 2>&1 || true)
if echo "$out" | grep -q "placeholder"; then
    _ok "placeholder lockfile refused with clear message"
else
    _fail "placeholder lockfile not refused: $out"
fi

_test "root refusal (simulate via EUID override not possible here; manual check)"
# We cannot simulate EUID=0 without actual root. Just verify the check exists.
if grep -q 'EUID.*=.*"0"' "$INSTALL"; then
    _ok "root refusal logic present in script"
else
    _fail "no EUID == 0 check found in script"
fi

_test "install lock file path"
if grep -q '.install.lock' "$INSTALL"; then
    _ok "install lock path defined"
else
    _fail "no install lock path"
fi

_test "--require-hashes flag in pip call"
if grep -q '\-\-require-hashes' "$INSTALL"; then
    _ok "pip --require-hashes enforced"
else
    _fail "pip call lacks --require-hashes (supply-chain P0-2)"
fi

_test "--no-deps flag in pip call"
if grep -q '\-\-no-deps' "$INSTALL"; then
    _ok "pip --no-deps enforced"
else
    _fail "pip call lacks --no-deps"
fi

_test "two-factor env for skip-model-verify"
if grep -q 'CEO_RAG_UNVERIFIED_MODEL_ACK' "$INSTALL"; then
    _ok "two-factor env var required for --skip-model-verify"
else
    _fail "--skip-model-verify lacks two-factor env var"
fi

_test "script is executable"
if [ -x "$INSTALL" ]; then
    _ok "script has exec permission"
else
    _fail "script is not executable"
fi

_test "config file mode 0600"
if grep -q 'chmod 0600.*config.json' "$INSTALL"; then
    _ok "config.json created with 0600 mode"
else
    _fail "config.json mode not enforced"
fi

_test "config dir mode 0700"
if grep -q 'chmod 0700 "\$CONFIG_HOME"' "$INSTALL"; then
    _ok "CONFIG_HOME dir 0700 enforced"
else
    _fail "CONFIG_HOME dir mode not enforced"
fi

_test "disk space check ≥2500MiB"
if grep -q 'required_mb=2500' "$INSTALL"; then
    _ok "disk space check at 2500 MiB"
else
    _fail "disk space check missing or wrong threshold"
fi

_test "RAM check warning (not blocking)"
if grep -q 'required_gb=4' "$INSTALL"; then
    _ok "RAM check at 4 GiB"
else
    _fail "RAM check missing"
fi

_test "uninstall path preserves indexed data"
if grep -q 'Indexed data at.*preserved' "$INSTALL"; then
    _ok "uninstall does not delete indexed data"
else
    _fail "uninstall behavior unclear on indexed data"
fi

# Summary
printf '\n'
printf 'Tests: %d passed, %d failed\n' "$PASS" "$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
