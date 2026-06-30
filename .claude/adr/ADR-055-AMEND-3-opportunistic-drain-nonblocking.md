---
id: ADR-055-AMEND-3
title: ADR-055 §Components amendment — opportunistic drain non-blocking canonical-lock acquisition
status: ACCEPTED
proposed_at: 2026-06-21
proposed_by: CEO (S248 nightly-hygiene audit-errors-01 driver)
accepted_at: 2026-06-21
accepted_by: "Owner GPG — accepted in the private predecessor; ships in the v1.0.0 genesis commit"
amendment_of: ADR-055 (Audit-log HMAC chain for tamper detection — 2026-04-18 via PLAN-023)
amends_section: §Components §3 drain Phase 1 (canonical-lock acquisition) — refines ADR-055-AMEND-1 §4 Phase 1
veto_floor: ADR-052 (security-engineer VETO — audit-log integrity)
codex_pair_rail: required per ADR-107; VERDICT ACCEPT (codex-cli 0.139.0 / gpt-5.5, 2026-06-21)
related_plans: []
related_adrs: [ADR-055, ADR-055-AMEND-1, ADR-052, ADR-107, ADR-115, ADR-124, ADR-125]
supersedes: []
amends:
  - target: ADR-055-AMEND-1 §4 Phase 1 (Lock acquisition — drain acquires canonical FileLock)
    original_clause: "Phase 1 — Lock acquisition (deadlock-free): drain acquires canonical audit-log.jsonl FileLock. Writers acquire only their own spool's flock + journal's flock."
    amended_clause: "Drain acquires the canonical FileLock with a force-dependent timeout: a FORCED drain (force=True — recovery / exit-handler / session-start) blocks up to SPOOL_LOCK_TIMEOUT (a timeout there is anomalous: ok=False + error='canonical_lock_timeout' + breadcrumb, unchanged). An OPPORTUNISTIC drain (force=False — the per-emit hot path) acquires NON-BLOCKING (timeout=0, a single flock(LOCK_NB) with no sleep) and on contention YIELDS: sets DrainStats.contended_skip=True, keeps ok=True, emits no error. Yielding is correct because the lock holder's drain plus the yielding process's own later recovery cover its events. A DISTINCT, gated breadcrumb fires on the force=False path ONLY when the caller's own spool is already stale past DRAIN_TRIGGER_MTIME_MS at yield time (sustained starvation), preserving wedge observability without the benign-contention volume."
tags: [governance, audit-log, perf, async-drain, spool-writer, amendment, hot-path, anti-noise, s248-hygiene]
authorization: predecessor atomic ceremony (AMEND-3 ACCEPTED + Codex ACCEPT + Owner GPG); ships in v1.0.0 genesis
target_telemetry_window_days: 30
revert_trigger_truly_lost_7d: 1
---

# ADR-055-AMEND-3 — Opportunistic drain non-blocking canonical-lock acquisition

## §1. Status

ACCEPTED in the private predecessor; ships in the v1.0.0 genesis commit. Originally gated by:

1. Codex MCP Pair-Rail review per ADR-107 — **VERDICT ACCEPT recorded**
   (recorded in the private predecessor repo).
2. ADR-052 security-engineer VETO-floor consensus on the gated-starvation
   resolution (debate round-1 `consensus.md`, verdict design-coherent /
   PROCEED).
3. ADR-055 canonical edit `## Amended-by` cross-ref appendix in the SAME
   genesis commit (Owner GPG).

## §2. Context

**Driver**: S248 `/nightly-hygiene` returned yellow with `audit-log.errors` 93%
(120/129 lines) dominated by `spool_writer: drain canonical lock timeout`
(`spool_writer.py:2313`). Root cause: ADR-055-AMEND-1 moved the per-emit write
off the canonical lock onto a per-PID spool to kill PLAN-090 AC9c's +19.5ms p95
contention — but left the **drain** acquiring the canonical lock with a
*blocking* 2.5s timeout. Because the drain's Phase-2 sweep is global +
idempotent and the lock is held only by the active drainer (ADR-055-AMEND-1 §4
Phase 1), concurrent short-lived hook subprocesses that cross the drain trigger
together produce one winner (drains everything) and N losers that each busy-poll
2.5s, raise FileLockTimeout, breadcrumb, and return ok=False. The losers had no
work to do — contention was being treated as failure, at a cost of up-to-2.5s
hot-path latency per loser plus a forensic-noise inversion of the errors sidecar.

This refines the same Phase-1 mechanism AMEND-1 established → AMEND-3 (no prior
ADR-055-AMEND-3 on disk; AMEND-1 and AMEND-2 exist).

## §3. Decision drivers

- **Hot-path tail latency**: a contended opportunistic drain blocked up to 2.5s
  in a short-lived hook. Measured (predecessor benchmark, N=200): contended
  acquisition-failure p99 collapses from **~2535ms (timeout=2.5) to ~0.037ms
  (timeout=0)**. The rejected 0.05s "tiny budget" costs ~60ms p99 (~1662x
  timeout=0) because `filelock.py:147-164` sleeps a full poll_interval before
  the deadline check — Open-Q2 closed with data: `timeout=0`.
- **Forensic signal/noise**: `audit-log.errors` is the bug channel; 93% benign
  contention buries real errors and reddens hygiene/boot.
- **No-loss invariant (corrected by debate R-QA1)**: the winner does NOT sweep a
  live loser's spool — `_phase2_sweep_and_rename` skips
  `pid != our_pid and _is_alive_pid(pid)` (`spool_writer.py:1252`). No-loss is
  the UNION of (loser's own size/staleness re-drain) ∪ (loser's atexit/signal
  force-drain) ∪ (next drainer's dead-PID orphan sweep once `_is_alive_pid`
  flips False). Yielding only defers; it never drops.
- **VETO-floor mandate (ADR-052)**: audit-log integrity change → Codex ACCEPT +
  security consensus required (both obtained).
- **Anti-churn (ADR-115/124)**: refines the AMEND-1 drain mechanism via explicit
  amendment, not silent override; ~6 lines core + a gated forensic, zero new
  state, no new spool ABI.

## §4. Decision (the amendment)

### §Components §3 drain Phase 1-amended

`drain_now(force=False)` (opportunistic, per-emit hot path) acquires the
canonical `FileLock` with **timeout=0** — a clean one-shot try-lock
(`flock(LOCK_EX|LOCK_NB)`, no sleep). On contention it **yields**:
`DrainStats.contended_skip=True`, `ok` stays True, no error. `drain_now(force=True)`
(recovery / exit-handler / session-start) keeps **timeout=SPOOL_LOCK_TIMEOUT**;
a timeout there stays anomalous (`ok=False` + `error="canonical_lock_timeout"` +
`_breadcrumb("drain canonical lock timeout")`) — byte-equivalent to pre-AMEND-3.

Phases 2-5 (sweep, header-validate, sort, prev_hmac-from-canonical-tail
reconstruction, `_drain_sha256` skip-guard, append) run ONLY for the lock
winner, entirely inside the held lock — **unchanged**. A yielding `force=False`
contender never enters that block, so HMAC chain order, prev_hmac
reconstruction, and the Phase-4 skip-guard are untouched (Codex-confirmed).

New field: `DrainStats.contended_skip: bool = False` — in-process only, never
serialized, never reaches `canonical_json.encode` or the HMAC input (no Sec MF-3
surface).

### §Threat-model-delta (SEC veto-floor MF-1 — gated starvation breadcrumb)

Dropping the breadcrumb wholesale on `force=False` would blind the live health
detectors (`ceo-diagnose.py:408-411`, `status.py:277-281`), which page on
`audit-log.errors` line-count, to a genuinely wedged/malicious canonical-lock
holder — because the hot path is *unconditionally* `force=False`
(`audit_emit.py:2488`). ADR-055-AMEND-1 §6 makes "drain lock contention caused
production tool-call timeout" an explicit revert trigger; its telemetry must
stay observable.

Resolution: the `force=False` path emits a **distinct, gated** breadcrumb
(`drain canonical lock STARVED: own spool stale past trigger ...`) ONLY when the
caller's own spool mtime age already exceeds `DRAIN_TRIGGER_MTIME_MS` at yield
time (`_own_spool_stale_past_trigger`, OSError-safe, non-recursive). This means:

- Benign single-winner contention (fresh spool — the 120/129 case) stays
  **silent**: the winner is keeping up, so no spool goes stale.
- A sustained wedge (holder not draining → own spool ages past the trigger)
  surfaces a **distinct** breadcrumb the existing line-count detectors catch
  with **no detector change** — the distinction expected-contention vs
  pathological-starvation now lives at this gate rather than on every yield.

A *registered structured forensic* (`audit_spool_drain_starved`) was the
security archetype's first preference but was ADAPTED, not taken: registering a
new `_KNOWN_ACTIONS` entry lives in the KERNEL `audit_emit.py`
(CEO_KERNEL_OVERRIDE + relaunch — disproportionate). The gated breadcrumb
follows the established "breadcrumb-only, no new audit action" precedent at
`spool_writer.py:1377` and satisfies the veto's intent (wedge observable; benign
contention silent; detectors unchanged). A structured rate metric remains a
possible Owner-approved follow-up.

## §5. Revert path

`export CEO_AUDIT_SYNC_MODE=1` reverts the WRITER to sync-fsync-per-call
(`drain_now` short-circuits on `is_sync_mode() and not force` at the top, before
any new try-lock logic — clean revert, Codex-confirmed). Or `git revert` the
the v1.0.0 genesis commit (module-only change; status → SUPERSEDED-BY-REVERT;
Owner GPG-signed; no new ADR). Revert triggers: `truly_lost > 0` over 7-day
window; HMAC chain-break rate > 0.1% over 30 days; Owner directive.

## §6. Consequences

**Positive**: contended opportunistic-drain p99/max collapses ~2535ms → ~0.04ms
(N=200 baseline); benign breadcrumb volume removed from `audit-log.errors`;
genuine wedge still observable via the gated breadcrumb; HMAC chain integrity
preserved; behavioral reversibility retained.

**Negative**: a yielding loser defers its tail spool to its own later
drain / exit-handler / dead-PID orphan sweep (no loss, but the forced-path tail
becomes load-bearing for a class of last-emit events under sustained
contention). `DrainStats` gains one in-process field.

**Neutral**: the win is a **p99/max story on the contended subset** — uncontended
drains (the majority) are byte-identical, so p50 does not move; reviewers must
target the contended-subset tail. `_lib/audit_hmac.py`, `canonical_json.py`,
`audit-verify-chain.py` UNCHANGED.

## §7. Authorization + anti-churn scope

Doctrine ADR (refinement of AMEND-1 Phase 1); runtime artifact is the genesis
patch to `_lib/spool_writer.py` (canonical-guarded, non-kernel → standard
sentinel; NO CEO_KERNEL_OVERRIDE — spool_writer.py is not in `_KERNEL_PATHS`).
The kernel-guarded `audit_emit.py` caller already passes `force=False`
implicitly and is NOT touched. Acceptance ceremony = atomic commit + Owner GPG.
ADR-055 `## Amended-by` appendix lands in the SAME commit.

## §8. Related work

- **ADR-055** / **ADR-055-AMEND-1** — original HMAC chain + async-drain Phase 1 (refined here)
- **ADR-052** — VETO floor (security-engineer authority; consensus obtained)
- **ADR-107** — Pair-Rail (Codex ACCEPT recorded)
- **ADR-115 / ADR-124** — maintenance-mode / anti-churn scope discipline
- **ADR-125** — risk-tiered defaulting (this amendment = Tier-B behavioral)
- **v1.0.0 genesis** — implementation + tests
- `_lib/spool_writer.py` — drain_now Phase 1 (amendment site); `:1252` live-peer skip (no-loss lynchpin); `:1377` breadcrumb-only precedent
- `_lib/filelock.py` — timeout=0 try-lock semantics (`:146-164`)

## §9. Enforcement commit

Documentation + behavioral refinement. Runtime enforcement ships at the v1.0.0
genesis commit (patch + tests). ADR-055 `## Amended-by` appendix lands in the
same commit.
