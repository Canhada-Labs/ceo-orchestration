"""Extracted implementation: latency."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

def run_hook_latency(
    repo_root: Path,
    iterations: int = 200,
    p95_ceiling_ms: float = 180.0,
    p99_ceiling_ms: float = 160.0,
    p99_advisory: bool = False,
    exec_reference: bool = False,
    relative_advisory: bool = False,
    relative_k_source: Optional[str] = None,
    wall_budget_seconds: float = 420.0,
    strict_relative: bool = False,
    sampler: Optional[Callable[[str, str, int], float]] = None,
) -> Dict[str, Any]:
    """Profile hook latency; full contract in hook_latency_docs."""
    hooks_dir = repo_root / ".claude" / "hooks"
    agent_spawn = hooks_dir / "check_agent_spawn.py"
    anti_overhead = hooks_dir / "check_anti_ceo_overhead.py"
    output_secrets = hooks_dir / "check_output_secrets.py"
    measured_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    # ADR-163 percentile precondition (PLAN-159 debate round-1 must-fix):
    # with the nearest-rank truncation in _pct_of_sorted (int((n-1)*p/100)),
    # p95 and p99 collapse onto the SAME order statistic for n < 22 — the
    # p99 ceiling becomes dead code and the gate keys on the 2nd-largest
    # sample (the S272/S273 load-flake class). A gate run on a collapsed
    # index is a defect state: fail LOUDLY instead of measuring.
    idx_p95 = int((iterations - 1) * 95 / 100.0)
    idx_p99 = int((iterations - 1) * 99 / 100.0)
    if idx_p95 == idx_p99:
        return {
            "schema": "profile-opus-4-7.v1",
            "mode": "hook_latency",
            "measured_at": measured_at,
            "error": (
                "percentile_indices_collapsed: iterations=%d puts p95 and "
                "p99 on the same order statistic (index %d); minimum is 22, "
                "gate standard is 200 (ADR-163)" % (iterations, idx_p95)
            ),
            "p95_ceiling_ms": p95_ceiling_ms,
            "p99_ceiling_ms": p99_ceiling_ms,
            "passed": False,
        }
    for required in (agent_spawn, anti_overhead, output_secrets):
        if not required.is_file():
            return {
                "schema": "profile-opus-4-7.v1",
                "mode": "hook_latency",
                "measured_at": measured_at,
                "error": f"hook not found: {required}",
                "passed": False,
            }
    # --- second-key wiring (ADR-163 Amendment PLAN-169 S328) ---------------
    # The whole relative machinery — reference sampling AND the wall self-cap
    # — is gated on the new flags, so a run without them is byte-identical to
    # today (report keys AND exit code), which is the back-compat contract.
    second_key = bool(exec_reference or relative_advisory or relative_k_source)
    relative_warnings: List[str] = []
    k_by_entry: Dict[str, float] = {}
    if relative_k_source:
        k_by_entry, relative_warnings = _load_relative_k_source(relative_k_source)
        if not exec_reference and k_by_entry:
            relative_warnings.append(
                "relative_k_source_ignored: --relative-k-source needs "
                "--exec-reference (no reference measured, so rel_ok is "
                "undefined); every entry stays on phase 1"
            )
            k_by_entry = {}
    ref_plan = _ref_schedule(iterations, _REF_SAMPLES_PER_ENTRY) if exec_reference else []
    t_gate_start = time.perf_counter()
    wall_deadline_s = _WALL_BUDGET_SAFETY_FRACTION * float(wall_budget_seconds)
    wall_exceeded = False
    def _wall_blown() -> bool:
        if not second_key:
            return False
        return (time.perf_counter() - t_gate_start) > wall_deadline_s
    # Static rail detection: does this tree's tool_lifecycle ship the PLAN-154
    # observe rail? Drives whether the positive control is REQUIRED (post-
    # landing) or informational (pre-landing baseline-parity run).
    observe_rail_present = False
    try:
        observe_rail_present = "observation_store_path" in (
            hooks_dir / "_lib" / "tool_lifecycle.py"
        ).read_text(encoding="utf-8")
    except OSError:
        observe_rail_present = False
    base_env = {k: v for k, v in os.environ.items()}
    base_env["PYTHONPATH"] = str(hooks_dir)
    base_env["CLAUDE_PROJECT_DIR"] = str(repo_root)
    # Disable all advisory emitters so we measure governance logic only
    base_env["CEO_MODEL_ROUTING"] = "0"
    base_env["CEO_PROMOTION_HEURISTIC"] = "0"
    base_env["CEO_COOKBOOK_ADVISOR_ENABLED"] = "0"
    base_env["CEO_SPEC_CTX_SANITIZER_ENABLED"] = "0"
    base_env["CEO_SPAWN_CONFIDENCE_ENABLED"] = "0"
    # Deterministic corpus state: no inherited kill-switches / session id.
    # CLAUDE_PROJECT_DIR_NATIVE is the HIGHEST-PRECEDENCE runtime-state
    # carrier (runtime_paths): left in the inherited env it overrides both
    # HOME and CEO_AUDIT_LOG_DIR below, and every measured hook would append
    # to the LIVE HMAC chain instead of the per-entry throwaway dir — the
    # S321/S326 non-attributable-elos class. Scrubbing it is unconditional:
    # it is an isolation fix, not part of the second key, and it changes no
    # report key and no exit code.
    for scrubbed in (
        "CEO_LEARNING_OBSERVE",
        "CEO_SOTA_DISABLE",
        "CEO_TOOL_LIFECYCLE",
        "CEO_ANTI_OVERHEAD",
        "CLAUDE_SESSION_ID",
        "CLAUDE_PROJECT_DIR_NATIVE",
    ):
        base_env.pop(scrubbed, None)
    def _spawn_payload(tool_use_id: str) -> bytes:  # noqa: ARG001 — uniform sig
        return json.dumps({
            "session_id": _LATENCY_SESSION_ID,
            "tool_name": "Agent",
            "tool_input": {"description": "latency probe", "prompt": "bench"},
        }).encode()
    corpus: List[Dict[str, Any]] = [
        {
            "name": "check_agent_spawn",
            "hook": agent_spawn,
            "payload": _spawn_payload,
            "env_set": {},
            "seed": False,
        },
        {
            "name": "check_anti_ceo_overhead[observe=unset]",
            "hook": anti_overhead,
            "payload": _latency_pre_payload,
            "env_set": {},
            "seed": False,
        },
        {
            "name": "check_anti_ceo_overhead[observe=1]",
            "hook": anti_overhead,
            "payload": _latency_pre_payload,
            "env_set": {"CEO_LEARNING_OBSERVE": "1"},
            "seed": False,
        },
        {
            "name": "check_output_secrets[observe=unset]",
            "hook": output_secrets,
            "payload": _latency_post_payload,
            "env_set": {},
            "seed": True,
        },
        {
            "name": "check_output_secrets[observe=1]",
            "hook": output_secrets,
            "payload": _latency_post_payload,
            "env_set": {"CEO_LEARNING_OBSERVE": "1"},
            "seed": True,
        },
    ]
    observe_store_name = _LATENCY_SESSION_ID + ".observe.jsonl"
    hooks_out: Dict[str, Dict[str, Any]] = {}
    all_within_budget = True
    # rail round-1 P2 — a K file may only name entries that EXIST. Without
    # this, one typo armed phase 2 for the whole run while applying K to
    # nothing: `any_enforced` keys on `bool(k_by_entry)`, so every entry
    # classified with `k_e=None` (label "pass" whenever the absolute key was
    # met, and — the actual hole — a run that phase 1 would exit 1 on could
    # aggregate to "pass" and exit 0). Rejecting the name keeps the loader's
    # stated contract: a rejection is NAMED and degrades to PHASE 1, never
    # to a silently wider gate.
    if k_by_entry:
        _known_names = {e["name"] for e in corpus}
        for _unknown in sorted(set(k_by_entry) - _known_names):
            relative_warnings.append(
                "relative_k_unknown_entry[%s]: not a corpus entry name; "
                "dropped (the run stays on phase 1 unless another K "
                "applies)" % _unknown
            )
            k_by_entry.pop(_unknown)
    for entry in corpus:
        if _wall_blown():
            wall_exceeded = True
            break
        entry_tmp = Path(tempfile.mkdtemp(prefix="ceo-hook-latency-"))
        try:
            env = dict(base_env)
            env["HOME"] = str(entry_tmp / "home")
            env["CEO_AUDIT_LOG_DIR"] = str(entry_tmp / "audit")
            env.update(entry["env_set"])
            (entry_tmp / "home").mkdir(parents=True, exist_ok=True)
            (entry_tmp / "audit").mkdir(parents=True, exist_ok=True)
            # Reference lane: its own dir, SIBLING of the audit dir (same
            # filesystem, which is the whole point of term 3) and never
            # inside it — the observe-rail positive control must keep
            # counting exactly the rows the hooks wrote. PYTHONPATH is
            # dropped so the reference cannot import the hook tree even by
            # accident (anti-coupling contract).
            ref_env = dict(env)
            ref_env.pop("PYTHONPATH", None)
            ref_dir = entry_tmp / "ref"
            ref_script = entry_tmp / "ref_exec.py"
            if exec_reference and sampler is None:
                ref_dir.mkdir(parents=True, exist_ok=True)
                ref_script.write_text(_REF_EXEC_SOURCE, encoding="utf-8")
            # Codex pair-rail S265 P2: a hook that exits non-zero (import
            # or runtime error) must FAIL the gate, not silently record a
            # small latency sample. Hooks always exit 0 by contract, so any
            # non-zero return is a real failure — capture it for seed AND
            # timed runs and fold it into entry_passed (the S254 vacuous-
            # green class this profiler exists to prevent).
            entry_hook_failed = False
            # rail round-1 P1 — the SAME rule as the line above, for the lane
            # that did not have it. The reference is a MEASUREMENT of how
            # fast this runner executes; a process that died on an import,
            # a missing dir or a permission is not a slow reference, it is
            # NO reference. Discarding its return code let a fast, repeatable
            # failure (~15ms, low split-half drift) present as a perfectly
            # healthy `ref_valid=true` — and a tiny ref_p50 is the worst
            # possible poison for phase 2, where K_e is pinned from
            # max(hook_p50/ref_p50): one broken run pins K enormous and buys
            # blanket amnesty forever after.
            entry_ref_failed = False
            def _run_once(tag: str, kind: str = "warm", index: int = 0) -> float:
                nonlocal entry_hook_failed
                if sampler is not None:
                    # Injected measurement: no subprocess at all (seed
                    # included). Unit tests plant regressions at the
                    # predicate level instead of via time.sleep.
                    return float(sampler(entry["name"], kind, index))
                tool_use_id = "profile-tu-" + tag
                if entry["seed"]:
                    # Unmeasured Pre stamp via the REAL record_pre carrier so
                    # the timed record_post run takes the paired path.
                    # ADR-163: a >10s stall is folded into the fail-closed
                    # sink instead of raising an opaque TimeoutExpired
                    # traceback (more subprocess calls at N=200 raise the
                    # cumulative odds of one stall on a contended runner).
                    try:
                        seed_res = subprocess.run(
                            [sys.executable, str(anti_overhead)],
                            input=_latency_pre_payload(tool_use_id),
                            capture_output=True,
                            env=env,
                            cwd=str(repo_root),
                            timeout=10,
                        )
                        if seed_res.returncode != 0:
                            entry_hook_failed = True
                    except subprocess.TimeoutExpired:
                        entry_hook_failed = True
                payload = entry["payload"](tool_use_id)
                t0 = time.perf_counter_ns()
                try:
                    res = subprocess.run(
                        [sys.executable, str(entry["hook"])],
                        input=payload,
                        capture_output=True,
                        env=env,
                        cwd=str(repo_root),
                        timeout=10,
                    )
                    if res.returncode != 0:
                        entry_hook_failed = True
                except subprocess.TimeoutExpired:
                    # ADR-163: stall == hook failure (fail-closed, clean
                    # report instead of an uncaught traceback); the ~10s
                    # elapsed sample also breaches the ceiling by itself.
                    entry_hook_failed = True
                return (time.perf_counter_ns() - t0) / 1_000_000.0
            def _run_ref(index: int) -> float:
                nonlocal entry_ref_failed
                if sampler is not None:
                    return float(sampler(entry["name"], "ref", index))
                t0 = time.perf_counter_ns()
                # INVERTED predicate. The rail found this same class twice —
                # round-1 P1 (return code discarded) and round-2 P2 (timeout
                # left unmarked) — which per the repo's own rule means the
                # ARCHITECTURE of the cure is wrong, not the round. So the
                # reference is DISTRUSTED by default and earns trust on
                # exactly one path: the process ran to completion and exited
                # 0. A branch added later that forgets to mark failure cannot
                # reintroduce the hole, because failure is what the variable
                # already says.
                #
                # Why neither shape check can stand in for this: a fast crash
                # is a small, finite, low-drift sample, and a MINORITY of 10s
                # stalls does not move a median — measured, 3 timeouts among
                # the 40 samples give ref_p50=50.0 and split-half drift=1.000
                # against a 1.5 ceiling, so the classifier answered `pass`
                # with `ref_valid=True` over three processes that never
                # completed. The median is what makes this gate robust to
                # runner noise (ADR-163:258); that robustness is exactly what
                # blinds it here. Statistics cannot answer "did the process
                # finish".
                completed_ok = False
                try:
                    res = subprocess.run(
                        [sys.executable, str(ref_script), str(ref_dir)],
                        capture_output=True,
                        env=ref_env,
                        cwd=str(entry_tmp),
                        timeout=10,
                    )
                    completed_ok = res.returncode == 0
                except subprocess.TimeoutExpired:
                    # A stalled reference is a contention signal, not a hook
                    # verdict; it reads as infrastructure_contended.
                    pass
                if not completed_ok:
                    entry_ref_failed = True
                return (time.perf_counter_ns() - t0) / 1_000_000.0
            cold_ms = _run_once("cold", "cold", 0)
            warm: List[float] = []
            ref_samples: List[float] = []
            # ROUND-ROBIN: the reference is sampled INSIDE the hook loop, so
            # both keys price the same scheduler window. The S318 defect was
            # a probe measured once, outside the window that degraded.
            for i in range(iterations):
                # rail round-1 P2 — checked EVERY iteration, not every tenth.
                # The self-cap exists to guarantee a structured wall-capped
                # result instead of the outer 420s timeout's rc124, and the
                # stride broke that guarantee on exactly the runner it was
                # written for: one iteration can spend 10s in the seed, 10s
                # in the hook and 10s in the reference, so a check passing
                # just under the 378s deadline could be followed by ~300s
                # unchecked. `_wall_blown()` is one perf_counter subtraction;
                # paying it 200 times instead of 20 costs microseconds and is
                # not measurable against a 180ms budget.
                if second_key and i and _wall_blown():
                    wall_exceeded = True
                    break
                warm.append(_run_once("%04d" % i, "warm", i))
                # Re-checked BEFORE the reference lane: with the hook sample
                # already paid, the remaining reference runs of this same
                # iteration are the last place the overshoot can still grow.
                if second_key and _wall_blown():
                    wall_exceeded = True
                    break
                for _ in range(ref_plan[i] if i < len(ref_plan) else 0):
                    ref_samples.append(_run_ref(len(ref_samples)))
            warm_sorted = sorted(warm)
            p50 = _pct_of_sorted(warm_sorted, 50)
            p95 = _pct_of_sorted(warm_sorted, 95)
            p99 = _pct_of_sorted(warm_sorted, 99)
            p99_within = p99 <= p99_ceiling_ms
            entry_passed = (
                p95 <= p95_ceiling_ms
                and (p99_advisory or p99_within)
                and not entry_hook_failed
            )
            all_within_budget = all_within_budget and entry_passed
            hooks_out[entry["name"]] = {
                "cold_ms": round(cold_ms, 1),
                "p50_ms": round(p50, 1),
                "p95_ms": round(p95, 1),
                "p99_ms": round(p99, 1),
                "max_ms": round(max(warm_sorted) if warm_sorted else 0.0, 1),
                "hook_failed": entry_hook_failed,
                "p99_within": p99_within,
                "passed": entry_passed,
            }
            if second_key:
                ref_sorted = sorted(ref_samples)
                ref_p50 = _pct_of_sorted(ref_sorted, 50) if ref_sorted else 0.0
                ref_p95 = _pct_of_sorted(ref_sorted, 95) if ref_sorted else 0.0
                ref_drift = (
                    _split_half_drift(ref_samples)
                    if exec_reference
                    else float("inf")
                )
                k_e = k_by_entry.get(entry["name"])
                label, rel_ok, ref_valid = _classify_entry(
                    hook_p50=p50,
                    hook_p95=p95,
                    ref_p50=ref_p50,
                    ref_drift=ref_drift,
                    p95_ceiling_ms=p95_ceiling_ms,
                    k_e=k_e,
                    ref_measured=exec_reference,
                    wall_exceeded=wall_exceeded,
                    strict_relative=strict_relative,
                    ref_failed=entry_ref_failed,
                )
                stats = hooks_out[entry["name"]]
                if exec_reference:
                    stats["ref_p50_ms"] = round(ref_p50, 1)
                    stats["ref_p95_ms"] = round(ref_p95, 1)
                    stats["ref_samples"] = len(ref_samples)
                    stats["ref_split_half_drift"] = (
                        round(ref_drift, 3) if math.isfinite(ref_drift) else None
                    )
                    stats["ref_valid"] = ref_valid
                    # Published so the exit-5 has a NAME: `ref_valid=false`
                    # alone cannot tell an operator whether the reference was
                    # mis-shaped, drifting, or simply never ran.
                    stats["ref_failed"] = entry_ref_failed
                if relative_advisory or relative_k_source:
                    stats["R_e"] = (
                        round(p50 / ref_p50, 3)
                        if (exec_reference and ref_valid and ref_p50 > 0)
                        else None
                    )
                    stats["K_e"] = k_e
                    stats["rel_ok"] = rel_ok
                    stats["verdict_label"] = label
                    # Phase is a property of the ENTRY's K, not of the
                    # outcome: an entry with a usable K whose reference came
                    # back broken is still phase 2 (its verdict is exit 5),
                    # while an entry absent from the K file is phase 1.
                    stats["phase"] = (
                        "2-enforcing" if k_e is not None else "1-advisory"
                    )
                    if k_e is None and relative_k_source:
                        relative_warnings.append(
                            "relative_k_missing[%s]: no usable K in the "
                            "source file; this entry stays on phase 1 (its "
                            "label follows the absolute key alone)"
                            % entry["name"]
                        )
            # Snapshot the entry's observation store BEFORE the tmpdir is
            # deleted (the controls below consume these snapshots).
            store = entry_tmp / "audit" / "tool-lifecycle" / observe_store_name
            if store.is_file():
                try:
                    rows = [
                        json.loads(line)
                        for line in store.read_text(
                            encoding="utf-8"
                        ).splitlines()
                        if line.strip()
                    ]
                except (OSError, json.JSONDecodeError):
                    rows = []
                hooks_out[entry["name"]]["observe_rows"] = len(rows)
                hooks_out[entry["name"]]["observe_paired_rows"] = sum(
                    1 for r in rows
                    if isinstance(r, dict) and r.get("paired") is True
                )
            else:
                hooks_out[entry["name"]]["observe_rows"] = 0
                hooks_out[entry["name"]]["observe_paired_rows"] = 0
        finally:
            shutil.rmtree(entry_tmp, ignore_errors=True)
        if wall_exceeded:
            # The self-cap fired mid-entry: stop measuring rather than run
            # into the workflow's `timeout 420` (rc 124, an opaque kill).
            break
    def _entry_field(name: str, key: str, default: Any = 0) -> Any:
        """Read a per-entry field, tolerating a WALL-CAP-truncated corpus."""
        block = hooks_out.get(name)
        if not isinstance(block, dict):
            return default
        return block.get(key, default)
    # ---- Observe-rail controls (anti-vacuity, S254 class) -------------------
    on_rows = _entry_field("check_output_secrets[observe=1]", "observe_rows")
    on_paired = _entry_field(
        "check_output_secrets[observe=1]", "observe_paired_rows"
    )
    # Codex pair-rail S265 P3: every seeded run (cold + all warm) takes the
    # paired path, so EVERY observed row must be paired — requiring only
    # `on_paired >= iterations` let one unpaired warm row hide behind the
    # cold row's paired count (cold + 19 paired + 1 unpaired = 20). The
    # robust invariant is: no unpaired rows at all, and at least `iterations`
    # of them.
    positive_ok = (not observe_rail_present) or (
        on_rows >= iterations and on_paired == on_rows
    )
    positive_control = {
        "required": observe_rail_present,
        "rows": on_rows,
        "paired_rows": on_paired,
        "passed": positive_ok,
        "note": (
            "observe rail present: store must hold >= iterations paired rows "
            "or the observe=1 timing is a vacuous no-op measurement"
            if observe_rail_present
            else "observe rail not in this tree; both states are baseline "
            "parity runs (control arms automatically at PLAN-154 landing)"
        ),
    }
    off_rows = _entry_field("check_output_secrets[observe=unset]", "observe_rows")
    pre_rows = _entry_field("check_anti_ceo_overhead[observe=1]", "observe_rows")
    negative_ok = off_rows == 0 and pre_rows == 0
    negative_control = {
        "unset_store_rows": off_rows,
        "pre_side_store_rows": pre_rows,
        "passed": negative_ok,
        "note": (
            "A12 zero-delta: unset state writes nothing; MF-SEC-5: the "
            "record_pre carrier never writes the store even with observe=1"
        ),
    }
    passed = (
        all_within_budget
        and positive_ok
        and negative_ok
        and not wall_exceeded
    )
    report: Dict[str, Any] = {
        "schema": "profile-opus-4-7.v1",
        "mode": "hook_latency",
        "measured_at": measured_at,
        "python": sys.version.split()[0],
        "iterations": iterations,
        "p95_ceiling_ms": p95_ceiling_ms,
        "p99_ceiling_ms": p99_ceiling_ms,
        "p99_advisory": p99_advisory,
        "observe_rail_present": observe_rail_present,
        "hooks": hooks_out,
        # Back-compat: legacy consumers read this top-level block.
        "check_agent_spawn": hooks_out.get("check_agent_spawn", {}),
        "controls": {
            "observe_positive_control": positive_control,
            "observe_negative_control": negative_control,
        },
        "passed": passed,
        "note": (
            "Advisory emitters disabled (CEO_MODEL_ROUTING=0 etc.); "
            "measures governance hot-path only. Budget ADR-163 S318 "
            "amendment: p95<%.0fms hard per corpus entry; p99<%.0fms %s. "
            "PLAN-154 constraint 8: observe-rail extended write path "
            "profiled in both states with anti-vacuity controls."
            % (
                p95_ceiling_ms,
                p99_ceiling_ms,
                "ADVISORY (reported, never gates)" if p99_advisory
                else "hard (back-compat default)",
            )
        ),
    }
    # ---- second key (ADR-163 Amendment PLAN-169 S328) ----------------------
    # Every key below is ADDITIVE and appears ONLY under the new flags: a run
    # without them returns the dict above verbatim, which is the back-compat
    # contract test (e) asserts byte-for-byte.
    if second_key:
        entry_labels = [
            hooks_out[name]["verdict_label"]
            for name in hooks_out
            if isinstance(hooks_out[name], dict)
            and "verdict_label" in hooks_out[name]
        ]
        # PHASE 2 is armed by the K FILE, not by the outcome: a run whose
        # reference came back broken must still exit 5, and a wall-capped run
        # with an EMPTY corpus must never aggregate to "pass".
        any_enforced = bool(k_by_entry)
        # rail round-4 P2 — the no-labels fallback follows the ABSOLUTE key
        # instead of asserting "pass".
        #
        # `--exec-reference` without `--relative-advisory` is a supported CLI
        # combination that stores no per-entry `verdict_label`, so this list
        # is empty. Hardcoding "pass" then published a document that
        # contradicted itself — measured, with every entry over p95:
        # `passed=false`, `exit_class=1`, `verdict_label="pass"`. A JSON
        # consumer reading the label got the opposite of the exit code.
        #
        # With no labels the absolute key is the only key that ran, which is
        # exactly what phase 1 means, so the label reports what it decided.
        aggregate = (
            _aggregate_label(entry_labels)
            if entry_labels
            else ("pass" if passed else "real_regression")
        )
        if wall_exceeded:
            aggregate = "infrastructure_contended"
        any_hook_failed = any(
            isinstance(block, dict) and block.get("hook_failed")
            for block in hooks_out.values()
        )
        # rail round-2 P2 — the HARD p99 ceiling survives phase 2, scoped to
        # the entries that are NOT under amnesty.
        #
        # `_classify_entry` keys the absolute half on p95 ALONE, so an entry
        # can meet p95 and the relative key while breaching p99 and still be
        # labelled "pass". Under phase 1 that run exits 1 (`entry_passed`
        # carries `p99_advisory or p99_within`); arming phase 2 silently
        # dropped the ceiling. That "pass" cell is the hole, and it is the
        # ONLY cell that closes here.
        #
        # The `advisory_slow_runner` cell is deliberately EXEMPT, and the
        # ordering of the two ceilings is why: p99 >= p95 always, while the
        # p99 ceiling (160ms) sits BELOW the p95 one (180ms). So every entry
        # that breaches p95 breaches p99 too — a blanket p99 term makes
        # amnesty unreachable and cancels this amendment outright. (Written
        # blanket first; the pre-existing amnesty test caught it.) On an
        # entry whose slowness the relative key has already attributed to
        # the runner, the p99 breach is the same runner, not a second
        # finding.
        hard_p99_breach = (not p99_advisory) and any(
            isinstance(block, dict)
            and block.get("p99_within") is False
            and block.get("verdict_label") == "pass"
            for block in hooks_out.values()
        )
        if any_enforced:
            # PHASE 2: the relative key DECIDES. Hook failures, the two
            # observe controls and a hard p99 breach stay hard failures
            # regardless of any label.
            if (
                (not positive_ok)
                or (not negative_ok)
                or any_hook_failed
                or hard_p99_breach
            ):
                exit_class = 1
            else:
                exit_class = _LABEL_EXIT_CLASS[aggregate]
        else:
            # PHASE 1: byte-identical to today's exit contract.
            exit_class = 0 if passed else 1
        report["phase"] = "2-enforcing" if any_enforced else "1-advisory"
        report["verdict_label"] = aggregate
        report["exit_class"] = exit_class
        report["outcome_labels"] = list(_OUTCOME_LABELS)
        report["exec_reference"] = exec_reference
        report["relative_advisory"] = relative_advisory
        report["strict_relative"] = strict_relative
        report["abs_backstop_ms"] = _ABS_BACKSTOP_MS
        report["ref_drift_max"] = _REF_DRIFT_MAX
        report["wall_budget_seconds"] = float(wall_budget_seconds)
        report["wall_deadline_seconds"] = round(wall_deadline_s, 1)
        report["wall_exceeded"] = wall_exceeded
        report["elapsed_seconds"] = round(time.perf_counter() - t_gate_start, 1)
        report["relative_warnings"] = relative_warnings
        if exec_reference:
            report["ref_source_sha256"] = ref_source_sha256()
            report["ref_samples_per_entry"] = _REF_SAMPLES_PER_ENTRY
        report["relative_note"] = (
            "ADR-163 Amendment (PLAN-169 S328) second key. PHASE 1: labels "
            "are PUBLISHED and the exit code is byte-identical to the "
            "absolute-key contract — K_e is not derivable until an advisory "
            "window supplies paired (hook, reference) samples. R_e = "
            "hook_p50/ref_p50; do NOT read a single run's R_e as K."
            if not any_enforced
            else "ADR-163 Amendment (PLAN-169 S328) second key. PHASE 2: "
            "rel_ok = hook_p50 <= K_e * ref_p50 DECIDES the exit "
            "(pass/advisory_slow_runner 0, real_regression 1, "
            "infrastructure_contended 5)."
        )
    return report
