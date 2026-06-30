#!/usr/bin/env python3
"""PLAN-128 Wave-1 #4 — single-process accelerator dispatcher (latency-tax reduction).

The framework's per-edit latency tax is ~0.3-1.0s from cold-starting 7-10 separate Python interpreters per
tool call (each hook = a fresh `bash + python3`). We cannot consolidate the kernel-guarded governance hooks
from here, but we CAN make the NEW accelerators share ONE process: this dispatcher runs the after-edit
verify (#1) and (opt-in) the adequacy gate (#5) in a SINGLE interpreter, merging their feedback. At wiring,
it registers as ONE PostToolUse hook instead of N — so the accelerator layer adds one cold-start, not three.

Merges `additionalContext` from each check; if any check returns `decision: block`, the block propagates
(with the combined reason). Fail-OPEN: any internal error → allow `{}`. Stdlib only, Python >= 3.9.
"""
from __future__ import annotations

import json
import os
import sys
import time
from typing import Dict, List

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import verify_after_edit  # noqa: E402
import adequacy_gate  # noqa: E402
import turbo_profile  # noqa: E402  # PLAN-128 W2 master opt-out
import latency_report  # noqa: E402  # PLAN-128 W2 doc fast-path

# #1 always runs. #5 (adequacy_gate) is now temp-copy-safe (S207 — it mutates an isolated sandbox copy,
# never the real file; Codex 019e8db2 fix #10 satisfied) and is wired here BUT remains OPT-IN.
#
# COST MODEL (rite FinOps P1 — disclosed so the default-on decision is informed):
#   • CEO_ADEQUACY_GATE unset (DEFAULT): gate() is a single env-var check returning `{}` — ~0 added cost.
#   • CEO_ADEQUACY_GATE=1: after a clean #1, #5 runs the project's test suite 1 baseline + 1 canary + up to
#     <=8 mutant runs per edited .py. Wall-clock ≈ (1 test-suite run) × ~10; on weak/slow suites expect tens
#     of seconds PER EDIT, on fast strong suites a few seconds. This latency is DELIBERATELY accepted by the
#     opt-in; the gate prints a one-line disclosure to stderr the first time it activates. Disable any time
#     with CEO_ADEQUACY_GATE=0.
# Order matters: verify first (cheap, catches syntax), adequacy second (expensive, only when opted in).
CHECKS = [verify_after_edit.verify, adequacy_gate.gate]


def dispatch(hook_input: Dict) -> Dict:
    # PLAN-128 Wave-2: master opt-out (.claude/turbo-off / CEO_TURBO=0) → whole accel layer no-ops.
    try:
        if turbo_profile.is_turbo_off(hook_input.get("cwd") or os.getcwd()):
            return {}
    except Exception:
        pass
    # PLAN-128 Wave-2: skip the expensive verify on doc-only edits.
    try:
        _fp = (hook_input.get("tool_input") or {}).get("file_path", "")
        if _fp and latency_report.should_fast_path(_fp):
            return {}
    except Exception:
        pass
    contexts: List[str] = []
    block_reasons: List[str] = []
    # PLAN-135 W2 H6: propagate `continueOnBlock` (Claude Code 2.1.139) through the merge.
    # `continue_votes` counts blocking checks that asked to keep the turn going (feed the
    # reason back, self-repair) vs. ones that demand a hard stop. We only emit
    # continueOnBlock when EVERY blocking check opted in — a single hard-block check must
    # never be silently downgraded into a continue (fail toward the stronger gate).
    block_count = 0
    continue_votes = 0
    for check in CHECKS:
        try:
            r = check(hook_input) or {}
        except Exception:
            continue                      # one check failing never wedges the others (fail-open)
        if r.get("decision") == "block" and r.get("reason"):
            block_reasons.append(r["reason"])
            block_count += 1
            if r.get("continueOnBlock") is True:
                continue_votes += 1
        ctx = (r.get("hookSpecificOutput") or {}).get("additionalContext")
        if ctx:
            contexts.append(ctx)
    if block_reasons:
        out = {"decision": "block", "reason": "\n\n".join(block_reasons)}
        if continue_votes == block_count:   # unanimous opt-in → keep the turn (self-repair)
            out["continueOnBlock"] = True
        return out
    if contexts:
        return {"hookSpecificOutput": {"hookEventName": "PostToolUse",
                                       "additionalContext": "\n\n".join(contexts)}}
    return {}


def main() -> None:
    try:
        hi = json.loads(sys.stdin.read() or "{}")
    except Exception:
        print("{}"); return
    try:
        print(json.dumps(dispatch(hi)))
    except Exception as exc:
        sys.stderr.write("# accel_dispatch fail-open: %s\n" % str(exc)[:120])
        print("{}")


def _bench(n: int = 20) -> None:
    """Make the cold-start tax visible: time N separate `python -c pass` cold starts vs the in-process run."""
    import subprocess
    t0 = time.perf_counter()
    for _ in range(n):
        subprocess.run([sys.executable, "-c", "pass"], capture_output=True)
    cold = (time.perf_counter() - t0) / n * 1000
    # in-process dispatch over a trivial input
    import tempfile
    d = tempfile.mkdtemp(); f = os.path.join(d, "ok.py"); open(f, "w").write("x = 1\n")
    hi = {"tool_input": {"file_path": f}, "cwd": d}
    t1 = time.perf_counter()
    for _ in range(n):
        dispatch(hi)
    warm = (time.perf_counter() - t1) / n * 1000
    import shutil; shutil.rmtree(d, ignore_errors=True)
    print("HOOK LATENCY (per call, n=%d):" % n)
    print("  one python cold-start:        %.1f ms" % cold)
    print("  in-process dispatch (1 proc): %.1f ms" % warm)
    print("  → the framework runs ~7-10 separate cold-starts/edit (~%.0f-%.0f ms of pure interpreter tax);"
          % (cold * 7, cold * 10))
    print("    this dispatcher collapses the NEW accelerators (#1+#5) into ONE of those.")


def _selftest() -> None:
    import tempfile, shutil
    prev = os.environ.pop("CEO_ADEQUACY_GATE", None)        # default path: #5 opt-in OFF
    try:
        d = tempfile.mkdtemp()
        bad = os.path.join(d, "bad.py"); open(bad, "w").write("def f(:\n")
        out = dispatch({"tool_input": {"file_path": bad}, "cwd": d})
        assert "AFTER-EDIT VERIFY" in json.dumps(out), out          # #1 fires through the dispatcher
        # H6: when #1 hard-blocks (CEO_VERIFY_AFTER_EDIT_BLOCK=1) with continueOnBlock, the
        # dispatcher propagates it through the merge (sole blocking check ⇒ unanimous opt-in).
        os.environ["CEO_VERIFY_AFTER_EDIT_BLOCK"] = "1"
        try:
            out_blk = dispatch({"tool_input": {"file_path": bad}, "cwd": d})
            assert out_blk.get("decision") == "block", out_blk
            assert out_blk.get("continueOnBlock") is True, ("#1 continueOnBlock must propagate", out_blk)
            # revert switch: legacy hard stop (no continueOnBlock) still flows through
            os.environ["CEO_VERIFY_AFTER_EDIT_NO_CONTINUE"] = "1"
            out_legacy = dispatch({"tool_input": {"file_path": bad}, "cwd": d})
            assert out_legacy.get("decision") == "block" and "continueOnBlock" not in out_legacy, out_legacy
            os.environ.pop("CEO_VERIFY_AFTER_EDIT_NO_CONTINUE")
        finally:
            os.environ.pop("CEO_VERIFY_AFTER_EDIT_BLOCK", None)
            os.environ.pop("CEO_VERIFY_AFTER_EDIT_NO_CONTINUE", None)
        good = os.path.join(d, "ok.py"); open(good, "w").write("x = 1\n")
        assert dispatch({"tool_input": {"file_path": good}, "cwd": d}) == {}   # clean + #5 off → silent
        assert adequacy_gate.gate in CHECKS, "#5 adequacy gate must be wired into CHECKS"
        # opt-in ON: a real weak test → #5 fires, merged through the dispatcher.
        os.environ["CEO_ADEQUACY_GATE"] = "1"
        src = os.path.join(d, "calc.py"); open(src, "w").write("def price(x):\n    return x * 9 // 10\n")
        open(os.path.join(d, "test_calc.py"), "w").write(
            "from calc import price\ndef test_int():\n    assert isinstance(price(100), int)\n")
        out2 = dispatch({"tool_input": {"file_path": src}, "cwd": d})
        assert "ADEQUACY" in json.dumps(out2), ("#5 must fire through the dispatcher when opted in", out2)
        shutil.rmtree(d, ignore_errors=True)
    finally:
        os.environ.pop("CEO_ADEQUACY_GATE", None)
        if prev is not None:
            os.environ["CEO_ADEQUACY_GATE"] = prev
    print("accel_dispatch.py selftest PASS (single-process #1+#5 merge, clean-silent, opt-in-#5, "
          "H6-continueOnBlock-propagation, fail-open)")


if __name__ == "__main__":
    if "--bench" in sys.argv:
        _bench()
    elif "--selftest" in sys.argv:
        _selftest()
    else:
        main()
