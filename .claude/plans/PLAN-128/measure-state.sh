#!/usr/bin/env bash
# PLAN-128 §7 — measure-state: on-demand 4-axis snapshot of the accelerator stack's CURRENT state.
# $0, READ-ONLY. Reads the audit log + git history via measure_multiplier.py. Touches NO git / no
# canonical files / no network. Safe to run any time, as often as you like.
#
# Usage:
#   bash .claude/plans/PLAN-128/measure-state.sh [DAYS]                 # default 7, the current repo
#   bash .claude/plans/PLAN-128/measure-state.sh 14 /path/to/app        # a different repo (e.g. your app)
#   CLAUDE_AUDIT_LOG=~/.claude/projects/<app-slug>/audit-log.jsonl \
#     bash .claude/plans/PLAN-128/measure-state.sh 7 /path/to/app       # + that app's audit log
#
# The honest point (PLAN-128 §7): a single window is a SNAPSHOT, not a multiplier. To get the real
# throughput/cost gain you need a paired OFF-vs-ON week — see AB-PROTOCOL.md (run on a real APP, not this
# framework). If the QUALITY catch-rate below is 0/0/0, the accelerators are live-but-unexercised: the work
# was meta (editing the framework), not real app code that trips verify/codex/adequacy.
set -uo pipefail

SELF="$(cd "$(dirname "$0")" && pwd)"
MM="$SELF/wave1/measure_multiplier.py"
[ -f "$MM" ] || { echo "FATAL: measure_multiplier.py not found at $MM"; exit 1; }
DAYS="${1:-7}"
REPO="${2:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"

python3 - "$MM" "$DAYS" "$REPO" <<'PY'
import sys, json, subprocess, os

mm, days, repo = sys.argv[1], sys.argv[2], sys.argv[3]
cmd = [sys.executable, mm, "--days", days, "--repo", repo, "--json"]
audit = os.environ.get("CLAUDE_AUDIT_LOG")
if audit:
    cmd += ["--audit", audit]
p = subprocess.run(cmd, capture_output=True, text=True)
try:
    d = json.loads(p.stdout)
except Exception:
    sys.stderr.write("measure_multiplier.py failed:\n" + (p.stdout or "")[:600] + (p.stderr or "")[:600] + "\n")
    sys.exit(1)

w = d.get("window", {})
a = w.get("audit", {}) or {}
g = w.get("git", {}) or {}
dv = w.get("derived", {}) or {}
win = w.get("window", {}) or {}


def n(x, default=0):
    return x if isinstance(x, (int, float)) and not isinstance(x, bool) else default


def s(x):
    return "—" if x is None else x


print("════════ PLAN-128 measure-state — %sh window (last %sd) — $0, read-only ════════"
      % (win.get("hours", "?"), days))
print("repo: %s" % repo)
if not a.get("available"):
    print("\n  audit log unavailable (%s) — only git metrics below." % a.get("reason", "?"))
print()

print("── 1. THROUGHPUT  (velocidade + autonomia) ──")
if g.get("available"):
    print("   commits: %d    net lines: %d (+%d/−%d)    files: %d"
          % (n(g.get("commits")), n(g.get("net_lines")), n(g.get("insertions")),
             n(g.get("deletions")), n(g.get("files_touched"))))
    print("   tokens/commit: %s    human-touches/commit: %s    net-lines/human-touch: %s"
          % (s(dv.get("tokens_per_commit")), s(dv.get("human_touches_per_commit")),
             s(dv.get("net_lines_per_human_touch"))))
else:
    print("   (git unavailable: %s)" % g.get("reason", "?"))
lat = (a.get("latency") or {}).get("buckets")
if lat:
    print("   tool-latency: " + ", ".join("%s=%d" % (k, v) for k, v in lat.items()))
print()

vf, cr, af = n(a.get("verify_findings")), n(a.get("codex_reviews")), n(a.get("adequacy_flags"))
print("── 2. QUALITY  (catch-rate — defeitos pegos ANTES de você ver) ──")
print("   verify-after-edit findings: %d    codex reviews: %d    adequacy flags: %d" % (vf, cr, af))
if (vf + cr + af) == 0:
    print("   ⚠ ZERO catches — os aceleradores de qualidade estão LIGADOS mas NÃO foram EXERCITADOS.")
    print("     Esperado em meta-trabalho (editar o framework). Rode num PROJETO DE APP real")
    print("     (auth / dados / dinheiro) pra esses números ganharem vida. Ver AB-PROTOCOL.md.")
print()

print("── 3. COST  (custo) ──")
print("   total: $%.4f (de %d amostras)    tokens: %d"
      % (n(a.get("cost_usd")), n(a.get("cost_samples")), n(a.get("tokens_total"))))
print("   $/commit: %s    tokens/commit: %s"
      % (s(dv.get("cost_per_commit_usd")), s(dv.get("tokens_per_commit"))))
print()

print("── 4. SECURITY / GOVERNANCE ──")
print("   audit events: %d    routing advised/enforced: %d/%d    agent spawns: %d"
      % (n(a.get("events")), n(a.get("routing_advised")), n(a.get("routing_enforced")), n(a.get("agent_spawns"))))
print()

print("── LEITURA HONESTA ──")
print("   Multiplicador de throughput: UNMEASURED — UMA janela é um retrato, não um multiplicador.")
print("   Pro número honesto: uma semana OFF + uma ON, depois compare (AB-PROTOCOL.md →")
print("   measure_multiplier.py --ab). E meça num APP real, não neste framework (o lab certo).")
PY
