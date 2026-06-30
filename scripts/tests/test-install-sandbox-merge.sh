#!/usr/bin/env bash
# PLAN-136 W4 / S4a — regression test for build_settings() sandbox composition.
#
# The bug (Codex/audit): build_settings() in scripts/install.sh merged ONLY
# .hooks.PreToolUse / .hooks.PostToolUse from the stack fragment and never
# read the stack's TOP-LEVEL `sandbox` / `autoAllowBashIfSandboxed` keys — so
# `install.sh --stack sandbox` produced a settings.json WITHOUT any sandbox
# config and the OS-sandbox template was inert.
#
# This test runs the REAL installer twice and asserts:
#   (A) --stack sandbox  -> settings.json HAS .sandbox (enabled) +
#                           .autoAllowBashIfSandboxed + the full
#                           allowedDomains list, AND the stack hooks merged.
#   (B) --stack none / base-only -> settings.json has NO sandbox key
#                           (byte-identity preservation: the key only
#                           materializes when a stack/base actually carries
#                           it — an additive `// (base default)` reducer).
#
# stdlib + bash-3.2-safe (no mapfile/associative arrays). Needs jq + python3
# (already required by the installer and the rest of the test suite).
#
# Usage:
#   bash scripts/tests/test-install-sandbox-merge.sh
# Exits 0 on success, non-zero on any failed assertion.

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SOURCE_DIR="$( cd "$SCRIPT_DIR/../.." && pwd )"
INSTALL="$SOURCE_DIR/scripts/install.sh"

if ! command -v jq >/dev/null 2>&1; then
  echo "==> SKIP: jq not installed (installer requires it for stack merges)"
  exit 0
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "==> SKIP: python3 not installed"
  exit 0
fi

fail=0

# --- Scratch targets, always cleaned up -------------------------------------
T_SANDBOX="$(mktemp -d -t ceo-s4a-sandbox-XXXXXX)"
T_BASE="$(mktemp -d -t ceo-s4a-base-XXXXXX)"
cleanup() { rm -rf "$T_SANDBOX" "$T_BASE"; }
trap cleanup EXIT

mkdir -p "$T_SANDBOX" "$T_BASE"
( cd "$T_SANDBOX" && git init -q )
( cd "$T_BASE" && git init -q )

# --- (A) --stack sandbox ----------------------------------------------------
echo "==> [A] install.sh --stack sandbox into $T_SANDBOX"
LOG_A="$T_SANDBOX/.install.log"
if ! bash "$INSTALL" "$T_SANDBOX" --profile core --stack sandbox >"$LOG_A" 2>&1; then
  echo "::error::install.sh --stack sandbox failed (see log)"
  tail -30 "$LOG_A" >&2
  exit 1
fi

SETTINGS_A="$T_SANDBOX/.claude/settings.json"
if [[ ! -f "$SETTINGS_A" ]]; then
  echo "::error::[A] settings.json not produced"
  exit 1
fi

python3 - "$SETTINGS_A" <<'PY' || fail=1
import json, sys
d = json.load(open(sys.argv[1]))
ok = True
def check(cond, msg):
    global ok
    if not cond:
        print("::error::[A] " + msg, file=sys.stderr); ok = False
    else:
        print("    [A] PASS: " + msg)

check("sandbox" in d, "settings.json HAS top-level .sandbox key (was missing pre-fix)")
sb = d.get("sandbox", {})
check(sb.get("enabled") is True, ".sandbox.enabled is true (adopter opt-in)")
check("autoAllowBashIfSandboxed" in d, "HAS .autoAllowBashIfSandboxed key")
check(d.get("autoAllowBashIfSandboxed") is False, ".autoAllowBashIfSandboxed shipped false")
domains = sb.get("network", {}).get("allowedDomains", [])
check(len(domains) == 15, "allowedDomains expanded to 15 (got %d)" % len(domains))
for must in ("api.openai.com", "anthropic.com", "api.github.com",
             "raw.githubusercontent.com", "codeload.github.com",
             "registry.npmjs.org", "pypi.org", "files.pythonhosted.org",
             "api.osv.dev"):
    check(must in domains, "allowedDomains includes workflow host %r" % must)
# the stack hooks must STILL have merged (the original behavior is preserved)
pre = d.get("hooks", {}).get("PreToolUse", [])
check(len(pre) > 0, "stack PreToolUse hooks still merged (hooks behavior intact)")
sys.exit(0 if ok else 1)
PY

# --- (B) base-only (--stack none) -------------------------------------------
# Proves byte-identity preservation: with no sandbox-bearing stack, the
# reducer must NOT introduce a .sandbox / .autoAllowBashIfSandboxed key.
echo "==> [B] install.sh --stack none (base only) into $T_BASE"
LOG_B="$T_BASE/.install.log"
if ! bash "$INSTALL" "$T_BASE" --profile core --stack none >"$LOG_B" 2>&1; then
  echo "::error::install.sh --stack none failed (see log)"
  tail -30 "$LOG_B" >&2
  exit 1
fi

SETTINGS_B="$T_BASE/.claude/settings.json"
if [[ ! -f "$SETTINGS_B" ]]; then
  echo "::error::[B] settings.json not produced"
  exit 1
fi

python3 - "$SETTINGS_B" <<'PY' || fail=1
import json, sys
d = json.load(open(sys.argv[1]))
ok = True
def check(cond, msg):
    global ok
    if not cond:
        print("::error::[B] " + msg, file=sys.stderr); ok = False
    else:
        print("    [B] PASS: " + msg)

check("sandbox" not in d,
      "base-only settings.json has NO .sandbox key (byte-identity preserved)")
check("autoAllowBashIfSandboxed" not in d,
      "base-only settings.json has NO .autoAllowBashIfSandboxed key")
sys.exit(0 if ok else 1)
PY

# --- verdict ----------------------------------------------------------------
if [[ "$fail" -ne 0 ]]; then
  echo "==> FAIL: install sandbox-merge regression test"
  exit 1
fi
echo "==> PASS: install.sh --stack sandbox composes sandbox config; base-only stays clean"
