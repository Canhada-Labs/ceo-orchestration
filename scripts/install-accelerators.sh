#!/usr/bin/env bash
# install-accelerators.sh — PLAN-128 §7 minimal accelerator installer for a REAL APP repo.
#
# Why this exists: scripts/install.sh is idempotent and SKIPS an existing
# settings.json (install.sh:1125-1128), so a normal install drops the accelerator
# *files* into an app but never REGISTERS them → they never fire → §7 measures
# 0/0/0 (see .claude/plans/PLAN-128/AB-PROTOCOL.md + memory
# project_plan128_section7_run_in_existing_repo). This installer does ONLY the
# accelerator slice and performs the settings.json merge that install.sh skips —
# without the heavy GPG/canonical governance surface that would obstruct normal
# app development.
#
# What it installs into <app>/.claude/hooks/:
#   - _python-hook.sh (the Python>=3.9 shim)
#   - _lib/ (stdlib-only shared library; whole tree, replaced to avoid staleness)
#   - the 8 accelerator modules (accel_dispatch + its dispatch graph)
# and merges into <app>/.claude/settings.json (backup first, idempotent):
#   - PostToolUse Edit|Write|MultiEdit -> accel_dispatch.py  (verify-after-edit + adequacy)
#   - Stop                              -> codex_review_user_code.py
#   - SessionStart                      -> turbo_sessionstart.py  (turbo banner)
#   - env CLAUDE_CODE_SUBAGENT_MODEL=inherit (normal model resolution; per-agent
#     `model:` frontmatter governs). Since Claude Code 2.1.251 that var is only the
#     DEFAULT subagent model: an agent definition's `model:` and a per-spawn model
#     win over it. Before 2.1.251 it overrode both (the S218/PLAN-128-FOLLOWUP
#     incident). A global value is still never propagated: it would become the
#     model of every agent that declares none.
#   - a WARNING (never a write) when CLAUDE_CODE_SUBAGENT_MODEL_FORCE is on in this
#     shell, in the user settings env ($CLAUDE_CONFIG_DIR/settings.json when that is
#     set, and ~/.claude/settings.json), or in the app's project/local settings env.
#     Since Claude Code 2.1.257 it applies the subagent model (or the main model) to
#     EVERY subagent and ignores `model:` frontmatter and per-spawn models, which
#     flattens the tiering.
#   - env CEO_AUDIT_LOG_DIR=<audit-dir>     (CRITICAL: emit lands in the APP's log,
#         not the framework's per-project ~/.claude/projects/<native-slug> default)
#
# $0, reversible (settings.json is backed up; copied files are inert until the
# settings entries are present). Run it from the framework checkout.
#
# Usage:
#   bash scripts/install-accelerators.sh /path/to/app-repo [audit-dir]
# audit-dir defaults to ~/.claude/projects/<basename-of-app>
set -euo pipefail

usage() { echo "usage: bash scripts/install-accelerators.sh /path/to/app-repo [audit-dir]" >&2; exit 2; }
[ $# -ge 1 ] || usage

FRAMEWORK="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP="$(cd "$1" 2>/dev/null && pwd)" || { echo "FATAL: app dir not found: $1" >&2; exit 1; }
[ -d "$APP/.claude" ] || { echo "FATAL: $APP/.claude not found — install the framework/skills there first." >&2; exit 1; }
[ "$APP" != "$FRAMEWORK" ] || { echo "FATAL: refusing to run against the framework itself — that is the WRONG lab (AB-PROTOCOL.md §Regra de ouro)." >&2; exit 1; }

AUDIT_DIR="${2:-$HOME/.claude/projects/$(basename "$APP")}"

SRC="$FRAMEWORK/.claude/hooks"
DST="$APP/.claude/hooks"
mkdir -p "$DST" "$AUDIT_DIR"

echo "→ framework: $FRAMEWORK"
echo "→ app:       $APP"
echo "→ audit dir: $AUDIT_DIR"
echo

echo "→ copying shim + _lib + accelerator modules into $DST"
cp "$SRC/_python-hook.sh" "$DST/"
rm -rf "$DST/_lib"
cp -R "$SRC/_lib" "$DST/_lib"
# Prune build/cache cruft so it never lands (let alone gets committed) in the app
# repo — cp -R drags __pycache__/*.pyc/.mutmut-cache (lesson: git-add-dir-drags-pycache).
find "$DST/_lib" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
find "$DST/_lib" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete 2>/dev/null || true
rm -f "$DST/_lib/.mutmut-cache" 2>/dev/null || true
for f in accel_dispatch verify_after_edit adequacy_gate turbo_profile latency_report route codex_review_user_code turbo_sessionstart; do
  cp "$SRC/$f.py" "$DST/$f.py"
done
# Measurement producers (NOT turbo-gated — they run BOTH A/B weeks, so they
# cancel out of the multiplier). Without them the app's audit log stays empty
# and measure_multiplier has nothing but git commit counts:
#   UserPromptSubmit.py -> prompt_submitted  (autonomy denominator = human touches)
#   audit_log.py        -> agent_spawn + subagent-spawn token capture (PostToolUse matcher=Agent)
for f in UserPromptSubmit audit_log; do
  cp "$SRC/$f.py" "$DST/$f.py"
done

echo "→ import smoke (from $DST)"
( cd "$DST" && python3 -c "import accel_dispatch, verify_after_edit, adequacy_gate, turbo_profile, latency_report, route, codex_review_user_code, turbo_sessionstart, UserPromptSubmit, audit_log; print('   ok — all 10 modules import')" )

echo "→ merging accelerator entries into $APP/.claude/settings.json"
FRAMEWORK="$FRAMEWORK" APP="$APP" AUDIT_DIR="$AUDIT_DIR" python3 - <<'PY'
import json, os, shutil, sys, time

fw = os.environ["FRAMEWORK"]; app = os.environ["APP"]; audit = os.environ["AUDIT_DIR"]
fw_s = json.load(open(os.path.join(fw, ".claude", "settings.json")))
app_path = os.path.join(app, ".claude", "settings.json")
app_s = json.load(open(app_path)) if os.path.exists(app_path) else {}

if os.path.exists(app_path):
    bak = app_path + ".bak." + time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
    shutil.copy2(app_path, bak)
    print("   backup:", bak)

# Accelerators (accel_dispatch / codex_review_user_code / turbo_sessionstart) AND
# measurement producers (audit_log.py / UserPromptSubmit.py). Blocks are copied
# verbatim from the framework settings (keeping $CLAUDE_PROJECT_DIR, which resolves
# to the app root at runtime), idempotently.
MARK = ("accel_dispatch", "codex_review_user_code", "turbo_sessionstart",
        "audit_log.py", "UserPromptSubmit.py")

def is_accel(block):
    return any(any(m in h.get("command", "") for m in MARK) for h in block.get("hooks", []))

hooks = app_s.setdefault("hooks", {})
added = 0
for evt in ("PostToolUse", "Stop", "SessionStart", "UserPromptSubmit"):
    fw_blocks = [b for b in fw_s.get("hooks", {}).get(evt, []) if is_accel(b)]
    if not fw_blocks:
        continue
    lst = hooks.setdefault(evt, [])
    existing_cmds = set()
    for b in lst:
        if is_accel(b):
            for h in b.get("hooks", []):
                existing_cmds.add(h.get("command", ""))
    for b in fw_blocks:
        cmds = [h.get("command", "") for h in b.get("hooks", [])]
        if all(c in existing_cmds for c in cmds):
            print(f"   {evt}: already present — skip")
            continue
        lst.append(b)
        added += 1
        print(f"   {evt}: + {cmds}")

env = app_s.setdefault("env", {})
# S218/PLAN-128-FOLLOWUP: NEVER propagate a global subagent model into an app.
# Before Claude Code 2.1.251, CLAUDE_CODE_SUBAGENT_MODEL overrode per-agent `model:`
# frontmatter AND per-invocation model params, so a global "haiku" silently
# downgraded the adopter's deliberately-declared sonnet/opus subagents (confirmed in
# 3 lab repos). Since 2.1.251 it is only the DEFAULT, but a global "haiku" still
# becomes the model of every agent that declares none. Force "inherit" (normal
# resolution) — this is also CORRECTIVE: re-running on a previously poisoned app
# resets it. Announce the reset so a deliberate adopter value is never clobbered
# silently.
prev = env.get("CLAUDE_CODE_SUBAGENT_MODEL")
env["CLAUDE_CODE_SUBAGENT_MODEL"] = "inherit"
if prev not in (None, "inherit"):
    print(f"   reset: CLAUDE_CODE_SUBAGENT_MODEL {prev!r} -> 'inherit' "
          f"(global subagent-model default removed; per-agent model: frontmatter governs)")

# The override role moved to CLAUDE_CODE_SUBAGENT_MODEL_FORCE (Claude Code 2.1.257+):
# when on, EVERY subagent runs on CLAUDE_CODE_SUBAGENT_MODEL (or the main model) and
# agent `model:` frontmatter and per-spawn models are ignored (the 2.1.280 binary
# also ignores a Workflow agent() model under it), which flattens the tiering in
# either direction. This installer WARNS and never writes it: the realistic carriers
# are the operator's shell and user settings, outside the reviewed settings files,
# and an adopter's own settings value is theirs to keep. Checked: this shell's
# environment, the user settings file, and the app's project and local settings.
# Not read: managed/policy settings. Claude Code reads user settings from its config
# home, which is $CLAUDE_CONFIG_DIR when that variable is set and ~/.claude
# otherwise (read from the 2.1.280 binary on 2026-09-22). A session started from
# another shell can resolve the other one, so both settings.json files are checked
# when this shell sets a non-empty CLAUDE_CONFIG_DIR. An unreadable or malformed
# file is skipped, never fatal: the check is advisory. "On" mirrors Claude Code's
# env boolean parser (value in 1/true/yes/on after strip + lower; read from the
# 2.1.280 binary on 2026-09-22).
FORCE = "CLAUDE_CODE_SUBAGENT_MODEL_FORCE"

def _force_on(value):
    return value is not None and str(value).strip().lower() in ("1", "true", "yes", "on")

def _settings_env(path):
    try:
        with open(path) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    block = data.get("env") if isinstance(data, dict) else None
    return block if isinstance(block, dict) else {}

user_paths = []
for home_dir in (os.environ.get("CLAUDE_CONFIG_DIR"),
                 os.path.join(os.path.expanduser("~"), ".claude")):
    if home_dir:
        candidate = os.path.normpath(os.path.join(home_dir, "settings.json"))
        if candidate not in user_paths:
            user_paths.append(candidate)
local_path = os.path.join(app, ".claude", "settings.local.json")
carriers = (
    (("this shell's environment", os.environ.get(FORCE)),)
    + tuple((p + " env", _settings_env(p).get(FORCE)) for p in user_paths)
    + ((app_path + " env", env.get(FORCE)),
       (local_path + " env", _settings_env(local_path).get(FORCE)))
)
for where, value in carriers:
    if _force_on(value):
        print(f"   WARNING: {FORCE}={value!r} is ON in {where}.\n"
              f"            Claude Code then runs EVERY subagent on CLAUDE_CODE_SUBAGENT_MODEL\n"
              f"            (or the main model) and ignores agent model: frontmatter and\n"
              f"            per-spawn models: the tiering is flattened (a VETO rite can fall\n"
              f"            below its floor tier, and a cheap rite can run on the main model).\n"
              f"            This installer does not change it. Unset it unless that is deliberate.",
              file=sys.stderr)
env["CEO_AUDIT_LOG_DIR"] = audit

with open(app_path, "w") as f:
    json.dump(app_s, f, indent=2)
    f.write("\n")

print(f"   env: CLAUDE_CODE_SUBAGENT_MODEL={env.get('CLAUDE_CODE_SUBAGENT_MODEL')}  CEO_AUDIT_LOG_DIR={audit}")
print(f"   blocks added: {added}")
PY

echo
echo "✓ accelerators + producers installed into $APP (settings.json merged; backup kept)"
echo "  audit log (emit + measure): $AUDIT_DIR/audit-log.jsonl"
echo
echo "NEXT — start Week A (BASELINE, accelerators OFF; producers stay on both weeks):"
echo "    touch \"$APP/.claude/turbo-off\""
echo "    export CEO_VERIFY_AFTER_EDIT=0 CEO_CODEX_USER_REVIEW=0   # belt-and-suspenders"
echo "    rm -f \"$APP/.git/.ceo_codex_review_state.json\" \"$APP/.ceo_codex_review_state.json\"  # clean dedup"
echo "    date -u +%Y-%m-%dT%H:%M:%SZ        # record this as baseline-since"
echo "  Work the week in $APP normally; at week end record baseline-until. Then Week B (ON):"
echo "    rm -f \"$APP/.claude/turbo-off\""
echo "    unset CEO_VERIFY_AFTER_EDIT CEO_CODEX_USER_REVIEW"
echo "    # to also exercise the opt-in/detect-only axes (cost: test-suite per change / codex calls):"
echo "    #   export CEO_ADEQUACY_GATE=1 CEO_CODEX_USER_REVIEW_AUTO=1"
echo "  Daily snapshot:"
echo "    CLAUDE_AUDIT_LOG=$AUDIT_DIR/audit-log.jsonl \\"
echo "      bash $FRAMEWORK/.claude/plans/PLAN-128/measure-state.sh 1 \"$APP\""
echo "  Full protocol (read this — the switch list + caveats matter): $FRAMEWORK/.claude/plans/PLAN-128/AB-PROTOCOL.md"
echo
echo "NOTE: the PLAN-128 catch-emit wiring is LIVE (audit actions verify_after_edit_finding +"
echo "      adequacy_gate_flag, registered in .claude/hooks/_lib/audit_emit.py; tests:"
echo "      .claude/hooks/tests/test_plan128_emit_wiring.py). Catch-rate 0 = live-but-unexercised."
