"""The verbatim hook-latency contract extracted from its definition."""
from __future__ import annotations

HOOK_LATENCY_DOC = """Subprocess-profile the hook-latency corpus and gate p95/p99.

    ==== ADR-163 Amendment (PLAN-169 S328) — the SECOND KEY, phase 1 ====

    The gate has always had ONE key: ``hook_p95 <= p95_ceiling_ms``, an
    ABSOLUTE number. That key cannot tell "the hooks got slower" from "the
    runner got slower", and the ADR-163 contention pre-probe that was meant
    to separate them measures ``python3 -c pass`` — process CREATION, a few
    percent of a hook that imports the framework's ``_lib`` tree and takes a
    locked write. It is blind by construction to a runner that is slow but
    UNCONTENDED: 361/425/229 ms hook p95 against a 7.76 ms spawn probe, on
    hook bytes that measured 70-77 ms locally and PASSED 3.5 h earlier.

    This adds a SECOND, RELATIVE key measured in the same scheduler window:

    * ``--exec-reference`` samples ``ref_exec`` — a frozen, stdlib-only,
      3-term reference script (cold imports + fixed re.compile set; a fixed
      CPU hash loop; M x open/append/flock/fsync/rename on the same
      filesystem as the entry's audit dir) — ROUND-ROBIN interleaved inside
      each entry's own loop, ``_REF_SAMPLES_PER_ENTRY`` samples per entry.
      The reference imports NOTHING from the hook tree on purpose: the
      regression class this gate exists for IS an eager framework import,
      which would inflate numerator AND denominator.
    * ``--relative-advisory`` publishes ``R_e = hook_p50 / ref_p50`` and a
      ``verdict_label`` from the closed set ``_OUTCOME_LABELS``. p50 on BOTH
      sides — the ADR-163:258 median-on-shared-load doctrine.
    * ``--relative-k-source`` (PHASE 2, inert without the file) supplies
      ``K_e`` per entry and makes the relative key DECIDE the exit.

    **PHASE 1 IS WHAT SHIPS HERE: the exit codes are byte-identical to
    today.** Without a K there is no ``rel_ok``, so the label simply mirrors
    the absolute key (``pass`` / ``real_regression``), and even a broken
    reference (``infrastructure_contended``) leaves the exit alone. The
    labels exist to DERIVE K from >=10 green CI runs; K is not derivable
    today because zero paired (hook, reference) samples exist anywhere.

    Phase-2 truth table (only with a usable ``K_e`` for the entry):

    ======================  ========  =======  =========================
    abs_ok / rel_ok         p95<=600  label                       exit
    ======================  ========  =======  =========================
    True / True             -         pass                           0
    False / True            yes       advisory_slow_runner           0
    False / True            no        real_regression                1
    False / False           -         real_regression                1
    True / False            -         pass (strict_relative=False)    0
    reference invalid       -         infrastructure_contended       5
    ======================  ========  =======  =========================

    ``sampler(entry_name, kind, index) -> ms`` replaces ALL measurement when
    supplied (kind in ``{"cold", "warm", "ref"}``) and spawns no subprocess:
    the unit tests plant a +150 ms regression at the predicate level instead
    of betting on wall-clock luck.


    Addresses E12-F4 (profile-opus-4-7.py had zero latency thresholds) and
    PLAN-154 binding constraint 8 / SENT-F MANIFEST open-issue 3 (the observe
    rail's extended write path must join this corpus).

    Corpus (each entry: N+1 runs, first discarded as cold, warm p95/p99
    asserted against the shared ceilings):

    1. ``check_agent_spawn``                      — original E12-F4 entry.
    2. ``check_anti_ceo_overhead[observe=unset]`` — PreToolUse record_pre
       carrier, observe rail structurally OFF (baseline).
    3. ``check_anti_ceo_overhead[observe=1]``     — same, CEO_LEARNING_OBSERVE=1.
       record_pre is contractually byte-identical (MF-SEC-5), so this state
       must sit at baseline; the run doubles as an MF-SEC-5 tripwire (no
       observation store may appear on the Pre side).
    4. ``check_output_secrets[observe=unset]``    — PostToolUse record_post
       host, observe OFF. Negative control: the per-entry isolated audit dir
       must contain NO ``*.observe.jsonl`` after the runs (A12 zero-delta).
    5. ``check_output_secrets[observe=1]``        — THE extended write path.
       Each timed run is pre-seeded (unmeasured check_anti_ceo_overhead run,
       same tool_use_id) so record_post takes the real paired path: pairing
       pop + eviction save + lifecycle emit + observe append. Positive
       control (anti-vacuity, S254 class): when the repo's tool_lifecycle.py
       ships the observe rail, the store MUST hold >= iterations rows, all
       ``"paired": true`` — otherwise the entry measured a no-op boolean and
       the gate FAILS rather than passing vacuously. On a tree without the
       rail (pre-PLAN-154 landing) the control is reported not-required and
       both states measure baseline parity.

    Isolation: every corpus entry gets its own throwaway HOME +
    CEO_AUDIT_LOG_DIR (never the real ``~/.claude``); CEO_SOTA_DISABLE /
    CEO_TOOL_LIFECYCLE / CEO_ANTI_OVERHEAD / CLAUDE_SESSION_ID are scrubbed
    from the inherited env so the measured state is deterministic.

    Budget: p95 < 180ms hard per corpus entry (ADR-163 S318 amendment —
    recalibrated from the 2026-07 value of 120ms with the 2026-08-20
    evidence: an unloaded ubuntu-latest runner measured the heaviest entry
    at p95 110.6ms, an 8% margin, while the local baseline stayed at
    70.6ms — the runner shifted, not the hooks). p99 < 160ms is HARD by
    default for back-compat; under ``p99_advisory=True`` (the CI gate's
    mode) a p99 breach is REPORTED per entry (``p99_within``) and echoed
    as a WARN by the CLI but never fails the gate — on a shared runner the
    extreme tail prices the runner, not the code (same evidence class as
    the ADR-163 PLAN-169 W2.2 amendment's median-on-CI decision).

    Returns a dict with per-hook p50/p95/p99 (``hooks``), the two observe
    controls (``controls``), the legacy top-level ``check_agent_spawn``
    block (back-compat), and an aggregate ``passed`` boolean.
    """
