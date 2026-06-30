#!/usr/bin/env bash
# PLAN-071 Phase 0.5 — convenience wrapper for import_floor_bench.py.
#
# Usage:
#   bash run_bench.sh            # advisory mode: JSON + parsed summary,
#                                  exit 0 even if gates breach
#   bash run_bench.sh --report   # markdown pass-through (advisory)
#
# Gate-mode usage (P1-08 closure, 2026-05-04+):
#   BASELINE_JSON=fixtures/baseline.json bash run_bench.sh --mode=gate
#                                # only enables gate-mode when BASELINE_JSON
#                                  env var is set AND points at a present file
#
# To record a baseline:
#   bash run_bench.sh --write-baseline=fixtures/baseline.json
#
# Exit codes:
#   0 — advisory mode (always) OR gate mode + all acceptance gates pass
#   1 — gate mode + at least one gate failed
#   2 — CLI / setup error

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC2034  # kept for context; not referenced by this bench
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../../.." && pwd)"
BENCH="${SCRIPT_DIR}/import_floor_bench.py"

if [[ ! -f "${BENCH}" ]]; then
    echo "error: import_floor_bench.py not found at ${BENCH}" >&2
    exit 2
fi

# P1-08 closure (Codex 2026-05-04): default to advisory mode unless an
# explicit BASELINE_JSON env var is set AND points to a present file. The
# user can still pass --mode=gate explicitly via "$@" for ad-hoc CI runs
# but the default behavior is recording, not gating.
DEFAULT_MODE_ARGS=()
if [[ -n "${BASELINE_JSON:-}" && -f "${BASELINE_JSON}" ]]; then
    DEFAULT_MODE_ARGS=("--mode=gate" "--baseline=${BASELINE_JSON}")
    echo "info: BASELINE_JSON=${BASELINE_JSON} present; running --mode=gate" >&2
else
    DEFAULT_MODE_ARGS=("--mode=advisory")
    if [[ -n "${BASELINE_JSON:-}" ]]; then
        echo "warning: BASELINE_JSON=${BASELINE_JSON} set but file missing; "\
             "falling back to --mode=advisory" >&2
    fi
fi

# --- markdown pass-through ---------------------------------------------------
if [[ "${1:-}" == "--report" ]]; then
    shift
    exec python3 "${BENCH}" "${DEFAULT_MODE_ARGS[@]}" --report "$@"
fi

# --- JSON capture + parse ----------------------------------------------------
TMPFILE="$(mktemp -t plan071_bench.XXXXXX.json)"
cleanup() { rm -f "${TMPFILE}"; }
trap cleanup EXIT INT TERM

# Capture stdout to TMPFILE, allow non-zero exit (parsed below).
# User-supplied "$@" args go LAST so they can override DEFAULT_MODE_ARGS
# (e.g. explicit --mode=gate overriding the env-var-based default).
RC=0
python3 "${BENCH}" "${DEFAULT_MODE_ARGS[@]}" "$@" >"${TMPFILE}" || RC=$?

# Parse JSON via inline Python — keep wrapper stdlib-only.
# R3-03 closure (Codex 2026-05-04): exit semantics now driven by
# `mode` field in the JSON envelope, NOT by acceptance_gates.overall:
#   - mode == "advisory" → ALWAYS exit 0 (print verdict, never block)
#   - mode == "gate"     → exit 0 on PASS, 1 on FAIL
#   - benchmark_rc not in (0,1) → exit 2 (CLI/setup error)
python3 - "${TMPFILE}" "${RC}" <<'PY'
import json
import sys

path = sys.argv[1]
benchmark_rc = int(sys.argv[2])

try:
    with open(path, "r", encoding="utf-8") as fh:
        payload = json.load(fh)
except (OSError, json.JSONDecodeError) as exc:
    print("error: could not parse benchmark JSON: {}".format(exc),
          file=sys.stderr)
    sys.exit(2)

plat = payload.get("platform", {})
n = payload.get("n", "?")
# R4-03 closure (Codex S85): `mode` MUST be present in the JSON envelope.
# Pre-revision-5 we defaulted missing-mode to "advisory", which silently
# masked gate intent for older/malformed envelopes (e.g. an out-of-date
# import_floor_bench.py shipped via partial upgrade). Treat absence as
# a setup error (exit 2) so CI surfaces version skew immediately rather
# than allowing a gate-mode invocation to pass silently in advisory.
if "mode" not in payload:
    print(
        "error: harness JSON envelope missing required 'mode' key — "
        "likely older harness version OR corrupt JSON. Re-run with the "
        "current import_floor_bench.py.",
        file=sys.stderr,
    )
    sys.exit(2)
mode = payload["mode"]
if mode not in ("advisory", "gate"):
    print(
        "error: harness JSON envelope `mode` must be 'advisory' or "
        "'gate'; got {!r}.".format(mode),
        file=sys.stderr,
    )
    sys.exit(2)
full = payload.get("full", {}).get("summary", {})
full_block = payload.get("full", {})
delta = payload.get("delta", {})
gates = payload.get("acceptance_gates", {})
checks = gates.get("checks", {})
overall = gates.get("overall", False)

print("=" * 64)
print("PLAN-071 Phase 0.5 — import-floor benchmark")
print("=" * 64)
print("platform : {} {} / Python {}".format(
    plat.get("system", "?"), plat.get("machine", "?"),
    plat.get("python_version", "?")))
print("N (per condition): {}".format(n))
print("mode     : {}".format(mode))
print("")
print("Full probe (baseline + tier_policy):")
print("  p50  : {:.3f} ms".format(full.get("p50_ms", 0.0)))
print("  p95  : {:.3f} ms".format(full.get("p95_ms", 0.0)))
print("  p99  : {:.3f} ms".format(full.get("p99_ms", 0.0)))
print("  p99.9: {:.3f} ms".format(full.get("p99_9_ms", 0.0)))
print("")
print("RSS (full probe, child-side, KiB):")
print("  interpreter_startup : {:.1f}".format(
    full_block.get("interpreter_startup_rss_kib", 0.0)))
print("  rss_after           : {:.1f}".format(
    full_block.get("rss_after_kib", 0.0)))
print("  rss_delta (median)  : {:.1f}".format(
    full_block.get("rss_kib_delta", 0.0)))
print("")
print("Delta (full - baseline):")
print("  p50  : {:+.3f} ms".format(delta.get("p50_ms", 0.0)))
print("  p95  : {:+.3f} ms".format(delta.get("p95_ms", 0.0)))
print("  p99  : {:+.3f} ms".format(delta.get("p99_ms", 0.0)))
print("  rss  : {:+.1f} KiB".format(delta.get("rss_kib_delta", 0.0)))
print("")
print("Acceptance gates:")
for name in sorted(checks):
    chk = checks[name]
    mark = "PASS" if chk.get("pass") else "FAIL"
    actual = chk.get("actual")
    threshold = chk.get("threshold")
    if isinstance(actual, float):
        actual_s = "{:.3f}".format(actual)
    else:
        actual_s = str(actual)
    if isinstance(threshold, float):
        thr_s = "{:.3f}".format(threshold)
    else:
        thr_s = str(threshold)
    print("  [{}] {:<32} actual={} threshold={}".format(
        mark, name, actual_s, thr_s))
print("")
verdict = "PASS" if overall else "FAIL"
print("OVERALL: {}".format(verdict))
print("MODE   : {}".format(mode))
if mode == "advisory":
    print("(advisory mode — exit 0 regardless of verdict)")
print("=" * 64)

# R3-03 closure: CLI/setup error always trumps mode.
if benchmark_rc not in (0, 1):
    sys.exit(2)
# R3-03 closure: advisory mode ALWAYS exits 0 regardless of overall.
if mode == "advisory":
    sys.exit(0)
# Gate mode: 0 on PASS, 1 on FAIL.
sys.exit(0 if overall else 1)
PY
