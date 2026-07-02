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
#     `model:` frontmatter governs — NEVER a global override, which is documented to
#     beat the adopter's explicit model: declarations — S218/PLAN-128-FOLLOWUP)
#   - env CEO_AUDIT_LOG_DIR=<audit-dir>     (CRITICAL: emit lands in the APP's log,
#         not the framework's fixed ~/.claude/projects/ceo-orchestration default)
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
import json, os, shutil, time

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
# S218/PLAN-128-FOLLOWUP: NEVER propagate a global subagent-model override into an
# app. CLAUDE_CODE_SUBAGENT_MODEL is documented to BEAT per-agent `model:` frontmatter
# AND per-invocation model params, so a global "haiku" silently downgrades the
# adopter's deliberately-declared sonnet/opus subagents (confirmed in 3 lab repos).
# Force "inherit" (normal resolution) — this is also CORRECTIVE: re-running on a
# previously poisoned app resets it. Announce the reset so a deliberate adopter
# override is never clobbered silently.
prev = env.get("CLAUDE_CODE_SUBAGENT_MODEL")
env["CLAUDE_CODE_SUBAGENT_MODEL"] = "inherit"
if prev not in (None, "inherit"):
    print(f"   reset: CLAUDE_CODE_SUBAGENT_MODEL {prev!r} -> 'inherit' "
          f"(global override removed; per-agent model: frontmatter governs)")
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
