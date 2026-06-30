---
id: ADR-055
title: Audit-log HMAC chain for tamper detection
status: ACCEPTED
decision_date: 2026-04-18
owner: security-engineer
plan: PLAN-023
related: [ADR-004-event-stream-v2, ADR-043-soc2-audit-trail-mapping, ADR-053-sentinel-hmac-deferred]
supersedes: []
---

# ADR-055 — Audit-log HMAC chain for tamper detection

## Context

Prior to v1.6.0 the audit log at
`~/.claude/projects/<slug>/audit-log.jsonl` carried no integrity mechanism.
`docs/threat-model.md §T-03` listed audit-tampering as a residual risk;
`docs/HONEST-LIMITATIONS.md §7` documented the gap as
"DYN-SEC3 deferred — HMAC chain + rotating key in Sprint 16".

PLAN-019 surfaced the gap; PLAN-020/021/022/024/025 did not close it.
ADR-053 considered an HMAC over the canonical-edit **sentinel** (a
different scope, different trust boundary) and deferred it. This ADR
ships a per-entry HMAC chain over the **audit log** — a complementary
control, not a supersession.

The Session 33 Phase E security-engineer design review
(`.claude/plans/PLAN-023/architect/round-1/approved.md`) required 7
specific hardenings before a bare chain could merge. This ADR captures
the result.

## Decision

Ship a per-entry HMAC chain:

```
hmac = hmac_sha256(key, prev_hmac || canonical_json(entry_sans_hmac))
```

### Components (all Python stdlib)

1. **`_lib/canonical_json.py`** — single-source canonical encoder.
   Pins `json.dumps(sort_keys=True, separators=(",", ":"),
   ensure_ascii=False, allow_nan=False)`; NFC-normalizes strings;
   rejects floats/NaN/Infinity + non-JSON-native types. All writers
   and the verifier MUST route through `encode()`.

2. **`_lib/audit_hmac.py`** — chain primitives:
   - `get_or_create_key()` — 32 random bytes at
     `~/.claude/projects/<slug>/audit-key`, 0600 perms, atomic
     create-via-tmpfile-rename, process-level cache.
   - `read_prev_hmac()` — sidecar `audit-log.last-hmac` under the
     audit-log FileLock. Missing/corrupt → genesis (fail-open).
   - `write_last_hmac()` — sidecar update, best-effort (no fsync;
     reconstructible from log tail).
   - `compute_entry_hmac()` — pure function over
     (key, prev_hmac, entry_sans_hmac).
   - `reset_chain_on_rotation()` — clears sidecar after rename.
   - `is_disabled()` — `CEO_AUDIT_HMAC_DISABLE=1` kill-switch.

3. **`_lib/audit_emit.py`** (kernel-guarded) — integrates HMAC
   compute+write INSIDE the existing `FileLock` block. Read-modify-
   write sequence atomic against concurrent subprocess writes
   (chain-fork defect avoided).

4. **`.claude/scripts/audit-verify-chain.py`** — CLI with exit codes
   0 (intact) / 1 (tamper) / 2 (key missing) / 3 (malformed) /
   4 (perm). Flags: `--log-file` / `--key-file` / `--since` / `--json`
   / `--verbose` / `--stdin`. No key path printed by default.

5. **SPEC/v1/audit-log.schema.md** and
   `.claude/plans/AUDIT-LOG-SCHEMA.md` v2.9 — `hmac` + `hmac_error`
   additive fields; transition-entry rule; chain reset semantics on
   rotation.

### Threat model

**Defends (detection-only):**

- **Forgery** — any bit flip in an HMAC-covered field breaks the chain.
- **Reorder** — swapping entries produces a different HMAC.
- **Deletion of interior entries** — next entry's HMAC fails to verify.
- **Transition-rule violation** — hmac-bearing entry followed by
  hmac-less entry flagged as tamper (one-way rule).

**Does NOT defend (documented residuals):**

- **Prevention** — HMAC is tamper-evident, not tamper-proof.
- **Tail truncation** — attacker deletes last N entries; head
  remains internally consistent. **Post-v1.6.0 mitigation:** external
  anchor via OTEL/remote append-only sink.
- **Key theft** — attacker with `$HOME` read access owns the chain.
  Adopter hardening: FS-level ACLs, encrypted home, separate service
  account for audit-key.
- **Rollback** — attacker restores an older (log, key) pair; chain
  verifies clean against the old key. Mitigation out of scope v1.6.0.
- **Log + key co-deletion** — deny-of-forensics. Mitigation requires
  external sink.
- **Non-framework processes that acquire the key** — no OS-level
  enforcement preventing other users or root from reading the key.
- **Canonicalization drift** — if a future schema adds a field with
  ambiguous encoding (Unicode key ordering, nested set), verifier-
  encoder mismatch creates false positives. Mitigation: single-source
  `canonical_json.encode` + ADR gate on its change + future
  `check-canonical-json-drift.py` lint.

### Key management

- **Initial creation** — atomic at first audit entry write; 32 bytes
  from `secrets.token_bytes`; 0600 perms; parent dir 0700.
- **Rotation** — Owner-driven. Procedure:
  1. Copy current `audit-key` → `audit-key.rotated-<ts>` (0600).
  2. Force log rotation (append until size > 10MB or rename manually).
  3. Delete `audit-key` + `audit-log.last-hmac`; next write auto-
     generates fresh key and starts a new genesis chain.
  4. Archive `audit-key.rotated-<ts>` alongside the rotated log file
     for future forensic verification.
  5. Emit `key_rotation` audit event on the first new-key write
     (deferred — tracked as follow-up; v1.6.0 ships without this event
     but the rotation itself is operational today).
- **Compromise recovery** — `docs/INCIDENT-RESPONSE.md §Key
  compromise`:
  1. Preserve compromised log + key TOGETHER (forensics depend on
     the pair).
  2. Rotate key per above.
  3. File issue with preserved evidence attached (redacted).
  4. Review `audit-verify-chain.py --json` output on the
     compromised period.

### Canonicalization contract (frozen at v1.6.0)

Any future field that participates in the HMAC MUST be:

- Serializable by `canonical_json.encode` (no float, no NaN/Inf,
  no tuple/set/custom).
- NFC-normalized at emit time (already handled by the encoder).
- Introduced via a SPEC/v1 audit-log.schema.md bump (additive).

A field change that would re-hash existing entries requires an ADR,
a schema-version bump, and an Owner-signed flip (this is essentially
an ABI break for the chain).

### Backward compatibility (transition-entry rule)

Pre-v1.6.0 audit logs have NO `hmac` field. `audit-verify-chain.py`
implements the one-way transition rule:

```
state = CHAIN_START  (prev_hmac = genesis)
for each entry:
  if entry lacks 'hmac':
    if state == CHAIN_START: continue (pre-v2.9 zone)
    else: FAIL — transition_violation
  else:
    if state == CHAIN_START: state = CHAIN_ACTIVE
    verify hmac == hmac_sha256(key, prev_hmac || canonical(entry_sans))
    prev_hmac = entry.hmac
```

This lets adopters upgrade in place: their old pre-v1.6.0 entries stay
valid, the chain activates at the first v1.6.0 write, and any
regression back to no-hmac is tamper.

## Consequences

### Positive

- `docs/threat-model.md §T-03` audit-tampering residual CLOSED
  (detection; prevention documented as post-v1.6.0 via external
  anchor).
- `docs/HONEST-LIMITATIONS.md §7` updates from "DYN-SEC3 deferred" to
  "SHIPPED v1.6.0; detection via audit-verify-chain.py; prevention
  requires WORM".
- `docs/INCIDENT-RESPONSE.md §Scenario 2` gains actionable
  `audit-verify-chain.py` invocation.
- Adopter CI can run `audit-verify-chain.py` as a canary.

### Negative / cost

- **Per-entry latency** — ~15-25µs added (canonical_json dumps + HMAC
  compute + sidecar I/O) inside the FileLock. Measured delta < 1ms vs
  the existing single-process p99 of 61ms. No impact on the 337ms p95
  SLO. Measurement: `benchmarks/hmac-overhead.py` (follow-up).
- **Operator complexity** — new files (`audit-key`, `audit-log.last-
  hmac`); new incident-response step; new backup target for
  `ceo-backup.sh` (follow-up: wire into Phase 5 script).
- **Kill-switch** — `CEO_AUDIT_HMAC_DISABLE=1` provided for
  emergencies. ABORT criteria (for future ceo-health auto-trip):
  p95 hook_duration_ms >337ms for 20 consecutive samples, or
  FileLockTimeout rate >0.1%.

### Neutral

- **Additive to SPEC/v1** — `hmac` field is nullable string; old
  readers ignore it cleanly (forward-compat by the v2 contract).
- **ADR-053 relationship** — ADR-053 is the **sentinel** HMAC
  deferral (a different mechanism for a different trust boundary:
  canonical-edit approval). ADR-055 does NOT supersede it. Both may
  coexist; the sentinel HMAC may still land as a separate Sprint
  item.
- **Performance kill-switch path** — the `_HMAC_AVAILABLE` guard in
  `audit_emit.py` means the module loads even if `audit_hmac` is
  absent; runtime check `is_disabled()` provides the on/off flag.

## Validation

- Unit tests cover chain happy path, tamper (bit flip, reorder,
  deletion), transition-rule one-way, rotation reset, missing-key
  recovery, perm-wrong graceful fail, concurrent-write safety,
  malformed line, fallback entries, float-rejection, NFC round-trip,
  hmac-cache invariant, and `audit-verify-chain.py` exit-code
  contract. Target: 15+ tests added in PLAN-023 Phase B.
- `audit-verify-chain.py` validated on a dogfood-generated audit log
  (multi-thousand entries) as part of Phase B acceptance.

## Out of scope

Explicitly deferred (documented here so adopters know the gap):

- External anchor (OTEL / remote append-only) for tail-truncation
  defense.
- HSM-backed keys.
- Remote-signed entries (multi-party signatures).
- WORM storage recommendation.
- Performance benchmarks harness wired into CI (`benchmarks/hmac-
  overhead.py` lands as a follow-up, not in this ADR's scope).
- `key_rotation` audit event registration (the event name is
  reserved; emission wiring is follow-up).

## Rollback

If the HMAC chain produces unacceptable runtime regression or a
verifier false-positive epidemic:

1. `export CEO_AUDIT_HMAC_DISABLE=1` — new entries ship without
   `hmac` field (falls into the pre-v2.9 zone on the next verify
   pass, which is tolerated until the chain resumes).
2. `git revert` the Phase B commit if the bug is in the module code.
3. The kernel-patched `audit_emit.py` integration is idempotent and
   has a matching `--dry-run` + byte-identity anchor; re-applying the
   inverse patch is mechanical.

## References

- Performance-engineer review: `.claude/plans/PLAN-023/architect/
  round-1/approved.md` (Owner-signed transcript 2026-04-18).
- Security-engineer review: same file, §7 mitigations.
- Measurement protocol: security-engineer review §Validation; cost
  budget: performance-engineer review §1.

## Enforcement commit

`ca98a274f9ca` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)

## Amended-by

- **[ADR-055-AMEND-1](ADR-055-AMEND-1-spool-writer-async-drain.md)** — `spool-writer-async-drain` (PROPOSED 2026-05-14, PLAN-094 §5 ceremony, S121 lineage correction). Amends:
  - §Components §3 (`_lib/audit_emit.py` kernel-guarded HMAC integration): FileLock-internal HMAC compute+write → 5-phase atomic drain protocol (per-PID spool file fsync'd outside canonical FileLock + deferred `_drain_spool()` step under FileLock with atomic-rename + canonical-tail `prev_hmac` reconstruction + bounded skip-guard + atomic split for partial consumption).
  - §Canonicalization contract: extended (NOT replaced) with 4-tuple total-order key `(wall_ns, pid, spool_uuid, ordinal_within_file)` requirement for NEW spool-era entries. Pre-spool-era v1.6.0..v1.25.0 entries remain verifier-valid under §Backward compatibility transition rule (extended with one-way v1.25.0 → spool-era rule).

  **Driver**: PLAN-090 AC9c spawn-hook +19.5ms p95 regression (vs `.claude/plans/PLAN-090/baseline-pre-wave-a-perf.json`). **Codex R2 ACCEPT**: 7-iter cycle (thread `019e2655-76e9-7591-8330-778a25a63053`, gpt-5.5 per S120 lesson) on editorial draft at `.claude/plans/PLAN-094/ADR-055-AMEND-1-draft.md` (981 LoC). **Canonical**: 168 LoC at `.claude/adr/ADR-055-AMEND-1-spool-writer-async-drain.md` (field-by-field equivalent per S120 compressed-canonical doctrine, NOT byte-identical). **Tier**: B per ADR-125 (behavioral change with rollback envelope `CEO_AUDIT_SYNC_MODE=1`). **Anti-churn scope**: ADR-124 §Part 2 mechanical scope test + R-037 roadmap mapping; NOT ADR-115 §exception #1 which is P0 security only. **Cryptographic primitives UNCHANGED**: `_lib/audit_hmac.py` + `_lib/canonical_json.py` preserved. **`audit-verify-chain.py`** exit-code contract UNCHANGED; internal logic extended in Wave A to recognize spool-era one-way transition rule.

- **[ADR-055-AMEND-3](ADR-055-AMEND-3-opportunistic-drain-nonblocking.md)** — `opportunistic-drain-nonblocking` (ACCEPTED 2026-06-21, S248 hygiene driver). Refines ADR-055-AMEND-1 §4 Phase 1: the OPPORTUNISTIC drain (`force=False`, per-emit hot path) acquires the canonical FileLock NON-BLOCKING (`timeout=0`) and yields silently on contention (`DrainStats.contended_skip=True`, `ok=True`, no error breadcrumb); the FORCED drain (`force=True`) keeps the blocking `SPOOL_LOCK_TIMEOUT` + breadcrumb. A distinct gated breadcrumb surfaces SUSTAINED starvation (own spool stale past `DRAIN_TRIGGER_MTIME_MS`) so a wedge stays observable to `ceo-diagnose.py`/`status.py`. Phases 2-5, HMAC chain order, `prev_hmac` reconstruction, and the Phase-4 skip-guard are UNCHANGED (Codex-confirmed). **Codex pair-rail ACCEPT** (codex-cli 0.139.0, 2026-06-21, patch + test/harness rounds). **Driver**: S248 `/nightly-hygiene` audit-errors-01 (120/129 benign breadcrumbs + up-to-2.5s hot-path block per loser). **Tier**: B (rollback `CEO_AUDIT_SYNC_MODE=1`). **Measured**: contended acquisition-failure p99 ~2535ms (timeout=2.5) → ~0.038ms (timeout=0); N=200 baseline recorded in the predecessor repo.
