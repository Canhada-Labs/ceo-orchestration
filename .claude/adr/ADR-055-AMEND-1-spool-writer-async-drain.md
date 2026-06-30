---
id: ADR-055-AMEND-1
title: ADR-055 §Components amendment — multi-PID spool-writer with async drain + 4-tuple total order
status: ACCEPTED
proposed_at: 2026-05-14
proposed_by: CEO (S121 lineage correction; PLAN-094 §5 ceremony)
accepted_at: 2026-05-14
accepted_by: "Owner (post-Codex-Pair-Rail-iter-7-ACCEPT 2026-05-14; thread 019e2655-76e9-7591-8330-778a25a63053 gpt-5.5; canonical-promotion sentinel at .claude/plans/PLAN-094/architect/round-1/approved.md GPG-signed 0000000000000000000000000000000000000000)"
amendment_of: ADR-055 (Audit-log HMAC chain for tamper detection — 2026-04-18 via PLAN-023)
amends_section: §Components §3 (audit_emit FileLock-internal HMAC integration) + §Canonicalization contract (4-tuple total-order extension for spool-era entries)
veto_floor: ADR-052 (security-engineer VETO — audit-log integrity)
codex_pair_rail: required per ADR-107 §Pair-Rail mechanics; model=gpt-5.5 is advisory S120 process lesson, not load-bearing on ADR-107
related_plans: [PLAN-023, PLAN-094]
related_adrs: [ADR-055, ADR-053, ADR-052, ADR-107, ADR-108, ADR-115, ADR-124, ADR-125, ADR-043, ADR-005]
supersedes: []
amends:
  - target: ADR-055 §Components §3 (_lib/audit_emit.py kernel-guarded HMAC integration)
    original_clause: "integrates HMAC compute+write INSIDE the existing FileLock block. Read-modify-write sequence atomic against concurrent subprocess writes (chain-fork defect avoided)."
    amended_clause: "Writes go to a per-PID spool file fsync'd outside the canonical FileLock; a deferred _drain_spool() step under FileLock atomically renames each spool to a .draining suffix (race-free vs concurrent writers), reads + sorts entries by 4-tuple (wall_ns, pid, spool_uuid, ordinal_within_file), reconstructs prev_hmac from canonical-log TAIL (NOT sidecar — idempotent under partial-crash), computes HMAC chain, atomically appends + fsyncs to canonical log, updates sidecar as cache, releases lock. Chain-fork defect remains avoided (FileLock still serializes chain extension); per-emit critical path no longer pays canonical-log fsync."
  - target: ADR-055 §Canonicalization contract
    original_clause: "Any future field that participates in the HMAC MUST be: serializable by canonical_json.encode; NFC-normalized at emit time; introduced via SPEC/v1 audit-log.schema.md bump (additive)."
    amended_clause: "...AND for NEW spool-era entries only (pre-spool-era v1.6.0..v1.25.0 HMAC-bearing entries remain verifier-valid under ADR-055 §Backward compatibility transition rule): the 4-tuple total-order key (wall_ns int, pid int, spool_uuid str, ordinal_within_file int) MUST be present on every entry pre-HMAC-compute. The spool_uuid is a per-spool random nonce (16-hex from secrets.token_hex(8)) in the spool header line, matched by every body entry. Drain validates 4-tuple presence + monotonicity + uniqueness before chain extension."
tags: [governance, audit-log, perf, async-drain, spool-writer, amendment, anti-churn, s121-lineage-corrected]
authorization: PLAN-094 Wave A atomic ceremony (gated by this AMEND-1 ACCEPTED)
target_telemetry_window_days: 30
revert_trigger_hmac_break_rate: 0.001
---

# ADR-055-AMEND-1 — Multi-PID spool-writer with async drain

## §1. Status

PROPOSED at draft time (PLAN-094 §5 ceremony — S121 lineage correction).
Flips to ACCEPTED at the PLAN-094 Wave A atomic ceremony commit, gated by:

1. Codex MCP Pair-Rail review per ADR-107 §Pair-Rail mechanics (audit-log durability is veto-floor; ACCEPT before status flip)
2. ADR-052 security-engineer VETO consensus on spool durability + 4-tuple total-order design
3. ADR-055 canonical edit `## Amended-by` cross-ref appendix in the SAME commit (sentinel `.claude/plans/PLAN-094/architect/round-1/approved.md` + `.asc` GPG by Owner 00000000)

Wave A implementation lands AFTER ACCEPTED + PLAN-092/093 `status: done`.

## §2. Context

**Driver**: PLAN-090 AC9c spawn-hook +19.5ms p95 regression (vs `.claude/plans/PLAN-090/baseline-pre-wave-a-perf.json` p95=53.73ms / p99=55.46ms) blocking PLAN-090 close. ADR-055 §Components §3's "~15-25µs added inside the FileLock" cost (single-writer assumption) compounds to +19.5ms p95 under 6 concurrent hook subprocesses contending on canonical-log FileLock + per-emit fsync.

PLAN-094 Wave A redesigned writer as durable spool + drain-on-next-invoke. Original ADR-055 §Components §3 wording ("HMAC compute+write INSIDE the existing FileLock block") directly contradicts this redesign; ADR-115 maintenance-mode requires explicit amendment over silent override.

**Lineage correction (S121 2026-05-14)**: S119 R2 iter-5 ACCEPT approved this proposal under wrong predecessor (`ADR-040-AMEND-3-async-flush-semantics`). ADR-040 governs Live Adapter (credential/cost/cascading) — orthogonal to audit-log writer durability. Codex gpt-5.5 caught the error during S120 ADR-127 R2 (thread `019e23c0`). ADR-055-AMEND-1 is the corrected predecessor. AMEND-1 is correct numbering (no prior ADR-055 amendments exist on disk).

## §3. Decision drivers

- **Per-emit critical path budget**: original design's 1 fsync per emit × 18 concurrent emits = 18 fsyncs/cycle. Spool-writer amortizes to 1 canonical-log fsync per drain (every ≥100ms or ≥50 events).
- **Anti-churn (ADR-115)**: original Components §3 single-writer FileLock design was deliberate. Structural change requires explicit amendment.
- **HMAC chain integrity preservation**: 4-tuple `(wall_ns, pid, spool_uuid, ordinal_within_file)` replaces FileLock-serialization-of-chain. PID + spool_uuid (16-hex nonce per spool, distinct across PID-recycle) + ordinal_within_file break wall-clock collisions (NTP slew acknowledged, not pretended-away).
- **Reversibility**: `CEO_AUDIT_SYNC_MODE=1` reverts WRITER to sync-fsync-per-call (behavioral, NOT byte-identical — spool-era canonical entries persist on disk; Tier-B per ADR-125).
- **VETO-floor mandate (ADR-052)**: audit-log integrity changes are security-engineer VETO; Codex Pair-Rail ACCEPT required.

## §4. Decision (the amendment)

### §Components §3-amended

> **`_lib/audit_emit.py`** (kernel-guarded) writes to a per-PID spool file `~/.claude/projects/<slug>/state/audit-spool.<pid>.jsonl` (sequential append + fsync; ~0.2-1ms p99 SSD). A deferred `_drain_spool()` step — triggered on emit when `spool_tail_mtime > 100ms ago` OR `spool_size > 50 events` — runs a **5-phase atomic protocol**:

**Phase 1 — Lock acquisition** (deadlock-free): drain acquires canonical `audit-log.jsonl` FileLock. Writers acquire only their own spool's flock + journal's flock. No writer holds canonical FileLock; no AB-BA cycle.

**Phase 2 — Stale `.draining.*` sweep + atomic rename + header validation**:
- Step 2a: scan state dir for pre-existing `audit-spool.*.draining.*` files from previous crashed drains; merge into current batch preserving each entry's original `_drain_epoch`
- Step 2b: assign `drain_epoch = secrets.token_hex(4)`; atomically rename each `audit-spool.<pid>.jsonl` → `audit-spool.<pid>.draining.<drain_epoch>` (POSIX rename atomic; concurrent writers miss the file and create fresh spool with new `_spool_uuid`)
- Header validation: read first line, verify well-formed JSON with `_spool_uuid` / `_pid` / `_created_wall_ns` / `_created_monotonic_ns`; validate `header._spool_uuid == body[0].spool_uuid` (cheap sentinel; full-body invariant enforced transitively via HMAC input); mismatch → quarantine that file only (`.malformed.<drain_epoch>` + `audit_spool_tamper_detected` forensic)

**Phase 3 — Sort + 4-tuple uniqueness**:
- Read body lines (skip header)
- Sort by `(wall_ns, pid, spool_uuid, ordinal_within_file)`
- Reject duplicate full 4-tuples (`audit_spool_duplicate_tuple_rejected`)

**Phase 4 — Idempotent chain reconstruction**:
- **Reconstruct `prev_hmac` from canonical-log TAIL**, NOT sidecar — sidecar is a CACHE; canonical log is source of truth
- Hard batch cap K_MAX=100 entries; skip-guard search window K_TAIL_WINDOW=200
- **Skip-already-drained guard**: for each entry's `sha256_of_canonical_json_bytes`, check against last K_TAIL_WINDOW `_drain_sha256` values of canonical tail; hit → already drained (idempotent retry)
- **Unexpected-skip forensic**: in steady-state, skip should NEVER fire. Emit `audit_spool_unexpected_skip` with severity branching: `drain_in_recovery_mode=True` → INFORMATIONAL; `False` → CORRECTNESS ALARM (drain bug or canonical-tail tamper; ≥3 alarm-severity in 24h → Wave A rollback)
- Compute HMAC chain via `_lib/audit_hmac.compute_entry_hmac()` (UNCHANGED primitive)
- Each canonical entry carries 2 additional fields: `_drain_sha256` + `_drain_epoch` (idempotence marker + crash-cycle traceability)
- **Trust boundary for `_drain_sha256`**: deterministic idempotence marker, NOT authenticity proof. Fake-injection requires audit-key compromise (same envelope as forgery); skip-guard correctness depends on canonical-tail integrity = same trust envelope as HMAC chain. NO new trust surface.

**Phase 5 — Atomic append + atomic split + cleanup**:
- Atomically append remaining entries + single canonical fsync
- Update `audit-log.last-hmac` sidecar via `write_last_hmac()` (CACHE only) + increment `audit-log.chain-length` canary
- For each `.draining.<drain_epoch>` file: if fully consumed → unlink; if partially consumed → **atomic split** (preserves original header verbatim + writes unconsumed remainder to `.tmp` → fsync → atomic rename to `.draining.<new_epoch>` → unlink original; preserves `header._spool_uuid == body[i].spool_uuid` invariant; preserves `_drain_sha256` reproducibility)
- Single-cycle invariant: each Phase 5 completion leaves AT MOST ONE valid `.draining.*` per spool with ONLY unconsumed entries. Under N-consecutive partial crashes, no entry appears twice in K_TAIL_WINDOW.
- Drain bounded ≤5ms p99 for ≤50 entries (PLAN-094 AC9); ≤20ms p99 for ≤K_MAX=100

**Quarantine recovery (non-wedging)**: per-spool-file quarantine; one bad spool isolated, others continue drain. Owner-driven inspection + replay or archive. Chain extension never blocked by quarantine; affected events counted in `truly_lost`.

### Loss accounting (best-effort journal — NOT load-bearing on correctness)

Per-PID journal `state/audit-pending.<pid>.journal` with buffered appends (Python `buffering=8192`); journal fsync every 100ms OR 10 emits (amortized via drain trigger). Envelopes: `{record_id, spool_uuid, ordinal_within_file, sha256_of_line, op, drain_epoch_at_commit}` (NO `journal_hmac` chain — file perms 0600 + audit-key co-location SAME trust as ADR-055 §Threat model). Two-phase begin/commit per emit; drain Phase 5 appends `op:"drained"`. Session-start "forensic aggregation" sweep (aggregation lock; winner-takes-all + idempotent rename). 6-counter session report: `audit_flush_dropped_count(begin_no_commit, commit_no_drained, recovered, truly_lost, tamper_rejected, intentionally_deleted)`.

Hot-path cost reduces from iter-2's 3 fsyncs to 1 fsync per emit (spool only).

### New audit events (registered via Wave 0 `_KNOWN_ACTIONS`; Sec MF-3 whitelisted fields)

`audit_flush_dropped_count` (6-counter) · `audit_spool_stale_recovered` · `audit_spool_partial_line_discarded` · `audit_spool_tamper_detected` (`mismatch_kind ∈ {sha256_mismatch, missing_commit_envelope, malformed_spool_header, header_body_uuid_mismatch}`) · `audit_spool_duplicate_tuple_rejected` · `audit_spool_intentionally_deleted` · `audit_spool_unexpected_skip` (severity-branched)

### §Canonicalization contract-amended

EXTENDED (not replaced) — scoped strictly to NEW spool-era entries; pre-spool-era v1.6.0..v1.25.0 entries remain verifier-valid under ADR-055 §Backward compatibility transition rule. New requirement: 4-tuple `(wall_ns, pid, spool_uuid, ordinal_within_file)` present pre-HMAC-compute on every spool-era entry.

**Verifier transition contract**: `audit-verify-chain.py` is EXTENDED in Wave A (exit-code contract UNCHANGED 0/1/2/3/4; new sub-code under exit 1 for spool-era transition violation). One-way rule: first `spool_uuid` entry locks subsequent entries to full 4-tuple + `_drain_sha256`. A v1.25.0-era entry (no 4-tuple) appearing AFTER a spool-era entry is `transition_violation`. Wave A test delta enumerated in editorial draft (22 tests T1..T22).

## §5. Revert path

**Behavioral rollback (NOT byte-identical — Tier-B per ADR-125)**:

- `export CEO_AUDIT_SYNC_MODE=1` reverts WRITER to pre-Wave-A sync-fsync-per-call (matches original ADR-055 §Components §3 byte-for-byte).
- **Clean rollback requires log rotation** immediately after env flip: spool-era 4-tuple entries on canonical log create transition-rule violation forensic signal if a non-4-tuple entry appears AFTER. Old-verifier (pre-Wave-A) ignores additive fields cleanly; chain still verifies internally; transition rule not enforced.
- `git revert` Wave A commit if module-code bug; status flip → `SUPERSEDED-BY-REVERT`; Owner GPG-signed commit; no new ADR.

**Revert triggers (any one)**:
1. HMAC chain break rate > 0.1% over 30-day window (auto-revert via `ceo-health`)
2. Single critical-severity incident: drain lock contention caused production tool-call timeout
3. `truly_lost > 0` over 7-day window (disk fault; forensic alarm)
4. Owner explicit revert directive

## §6. Consequences

**Positive**: PLAN-090 AC9c +19.5ms p95 regression closed; HMAC chain integrity preserved (FileLock-serialized extension); multi-PID concurrent writer support explicit; new forensic events; behavioral reversibility; new tamper-detection forensics extending ADR-055 §Threat model.

**Negative**: additional filesystem objects (`audit-spool.<pid>.jsonl` + per-PID journals; gitignored; 7d stale TTL); drain bounded ≤5ms p99 adds latency to every Nth emit; spool format is new ABI surface (JSON; forward+backward compatible).

**Neutral**:
- ADR-055 §Components §2 (`_lib/audit_hmac.py`) UNCHANGED. Cryptographic primitive preserved. Sidecar reduced to CACHE (canonical-tail reconstruction handles staleness).
- ADR-055 §Threat model defenses PRESERVED. Spool-level tamper detected via Phase 4 sha256 skip-guard reconciliation + Phase 2 header validation (NOT journal HMAC envelope; iter-3 dropped journal chain after compaction race + perf budget findings).
- ADR-055 §Backward compatibility EXTENDED: existing v1.6.0 transition rule unchanged; NEW v1.25.0 → spool-era one-way transition rule applies.
- **Forensic ordering change**: HMAC chain order shifts from FileLock-acquisition-order (original §3) to 4-tuple drain-sort-order (this amendment). `audit-verify-chain.py` exit-code contract UNCHANGED; internal logic EXTENDED. OTEL anchor follow-up (ADR-055 §Out of scope) MUST anchor drained entries in drain-order. INCIDENT-RESPONSE forensics: emit-time order recoverable from spool BEFORE drain truncates (7d TTL window).

## §7. Authorization + anti-churn scope

ADR-055-AMEND-1 is a doctrine ADR (documentation + ABI extension); runtime artifact is PLAN-094 Wave A. Acceptance ceremony = atomic commit + Owner GPG (`feedback_sentinel_signing_discipline.md`).

**Anti-churn scope justification**: this amendment is in-scope via **ADR-124 §Part 2 mechanical scope test** — maps to canonical roadmap item R-037 (audit_emit fsync chain-decoupling at `.claude/plans/PLAN-084/canonical/PLAN-084-evolution-roadmap.md:214`). Driver is PLAN-090 AC9c regression evidence linking to R-037 burn-down. **ADR-115 §exception #1 is NOT the scope path** — that exception is P0 security only.

NO `CEO_KERNEL_OVERRIDE` required (ADR-055 file not in `_KERNEL_PATHS`). PLAN-094 Wave A's ADR-055 `## Amended-by` appendix IS canonical-guard path (sentinel-signed via standard `approved.md` + `.asc` pattern).

## §8. Related work

- **ADR-055** — Audit-log HMAC chain (original 2026-04-18); §Components §3 extended; §Canonicalization gains 4-tuple
- **ADR-053** — Sentinel HMAC (deferred; complementary trust boundary; this amendment does NOT touch sentinel scope)
- **ADR-052** — VETO floor (security-engineer authority)
- **ADR-107** — Pair-Rail asymmetric VETO matrix (ACCEPT verdict required; gpt-5.5 model is S120 advisory)
- **ADR-108** — Pair-Rail dispatcher protocol
- **ADR-115** — maintenance-mode doctrine (NOT scope path — see §7)
- **ADR-124** — post-audit-SOTA-execution-mode (§Part 2 mechanical scope test = scope path)
- **ADR-125** — risk-tiered defaulting (this amendment = Tier-B)
- **ADR-043** — SOC2 audit-trail mapping (SPEC/v1 schema bump review)
- **ADR-005** — Event-stream v2 (new `audit_spool_*` actions; schema alignment review)
- **PLAN-094** — Wave A implementation (gated by this AMEND-1 ACCEPTED); editorial draft at `.claude/plans/PLAN-094/ADR-055-AMEND-1-draft.md` (981 LoC, Codex R2 thread `019e2655-...` 7-iter ACCEPT)
- **PLAN-090 AC9c** — spawn-hook +19.5ms p95 regression (driver)
- **PLAN-023** — original ADR-055 plan of record
- `_lib/audit_emit.py` — Wave A implementation site
- `_lib/audit_hmac.py` — UNCHANGED (cryptographic primitive preserved)
- `_lib/canonical_json.py` — UNCHANGED
- `audit-verify-chain.py` — exit-code contract UNCHANGED; internal logic EXTENDED in Wave A

## §9. Enforcement commit

This amendment ADR is documentation + ABI specification. Runtime enforcement ships at PLAN-094 Wave A ceremony commit. ADR-055 `## Amended-by` appendix lands in the SAME commit. Both SHAs recorded in PLAN-094 progress log §11.

---

**Editorial reference**: `.claude/plans/PLAN-094/ADR-055-AMEND-1-draft.md` (981 LoC; full design rationale, fold logs across 7 Codex R2 iterations, expanded 22-test Wave A delta). This canonical is field-by-field equivalent (S120 doctrine), NOT byte-identical.
