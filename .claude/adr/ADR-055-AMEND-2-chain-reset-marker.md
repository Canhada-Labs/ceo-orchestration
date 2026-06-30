---
id: ADR-055-AMEND-2
title: HMAC chain rotation chain_reset_marker + rotation manifest sidecar
status: ACCEPTED
decision_date: 2026-05-21
accepted_at: 2026-05-28
accepting_session: S181
authorization: "PLAN-118 WS-D Wave-A debate 0 VETO (security-engineer PROCEED + identity-trust-architect PROCEED + qa-architect ADJUST→satisfied) + Codex promotion review thread 019e70af-9565-7742-9c54-c398be202bc5 (BLOCK on session test-pollution → resolved by final ceremonial rotation → ACCEPT-WITH-FIXES → ACCEPT zero-residual after 3 doc fixes) + Owner GPG 0000000000000000000000000000000000000000 on the commit bearing this change (signed at commit time). AC-D0 organic-soak prerequisite Owner-overridden per ADR-095 doctrine (vote-trigger leg-b independently MET — 8 rotation markers strictly post-v1.39.4-ship-commit 2026-05-21T15:19:54Z, ≥ the required 5; live chain verifies intact post-WS-E+rotation; both historical root causes fixed + class-guarded; precedent S179 AC-C0)."
owner: security-engineer
plan: PLAN-112-FOLLOWUP-hmac-tamper-fix
amends: ADR-055
related: [ADR-055, ADR-055-AMEND-1, ADR-010]
vote_trigger_data_volume: "post-v1.39.4 ship + 30 days production rotation traffic OR 5 rotation events post-ship (whichever first)"
---

# ADR-055-AMEND-2 — chain_reset_marker + rotation-manifest sidecar

**Status:** ACCEPTED (S181, 2026-05-28)
**Enforcement commit:** `8952915` (PLAN-112-FOLLOWUP-hmac-tamper-fix Wave B.3 — `_emit_chain_reset_marker_under_lock` + rotation-manifest sidecar + verifier marker-required mode; shipped v1.39.4 `3e27c1d`). PLAN-118 hardening: AC-B4 producer-pollution chokepoints (`d89ec76`, S179) + WS-E float-leak class-closure (`09e9c51`, S181).

## Context

PLAN-112-FOLLOWUP-hmac-tamper-fix Wave A R1 debate (4 archetypes ADJUST_PROCEED) + Codex pair-rail R2 iter-4 ACCEPT identified that ADR-055 §2 ("Chain resets ONLY on file boundary") combined with spool drain Phase 4↔Phase 5 intra-lock ordering created an integrity gap: producer chained line 1 of new file from rotated archive's last_hmac while verifier (per ADR-055 §2) treated line 1 as genesis-anchored. Result: STATUS_TAMPER on live audit-log.jsonl after every spool-drain-triggered rotation. F-7.7 (PLAN-112).

Wave B.1 (hoist rotation probe to Phase 4 start in spool_writer.py) closes the immediate bug. This amendment introduces defense-in-depth:

1. **chain_reset_marker synthetic genesis entry** as line 1 of every rotation-created fresh audit-log.jsonl
2. **audit-log.rotation-manifest.json sidecar** as local boundary scoping verifier marker enforcement

## Decision

### Producer requirement

When `_rotate_if_needed_safe(log_path)` returns non-None `rotated_to`, producer MUST emit chain_reset_marker as line 1 of new audit-log.jsonl, atomically under canonical FileLock, BEFORE releasing lock.

Marker fields:
- `action: "chain_reset_marker"`
- `previous_archive_path: <relative path>`
- `previous_archive_last_hmac: <hex; "" if unrecoverable>`
- `rotation_ts: <ISO-8601 UTC>`
- `rotation_trigger: "size_threshold" | "manual" | "owner_rotation" | "quarantine_pre_fix"`
- Standard event_schema v2 fields

HMAC anchored at GENESIS_PREV (marker IS new chain genesis).

Post-marker under same FileLock:
1. `audit-log.last-hmac` ← marker HMAC
2. `audit-log.chain-length` ← 1
3. `audit-log.rotation-manifest.json` ← `{schema_version, rotated_at, previous_archive_filename, marker_line_count: 1}`

### Verifier behavior

`audit-verify-chain.py` MUST:
1. Read `audit-log.rotation-manifest.json` from SAME directory as audit-log being verified (NOT _audit_dir_from_env — avoids test envs inheriting production state)
2. Absent sidecar → legacy mode (ADR-055 §2 unchanged; first-install logs work as before)
3. Present sidecar → marker-required: line 1 MUST have `action == "chain_reset_marker"`; else STATUS_TAMPER

Verifier explicitly does NOT walk rotation archives (preserves ADR-055 §Non-goals "log = source of truth").

## Backwards compatibility

| Log shape | Manifest | Verifier mode |
|---|---|---|
| Pre-v1.39.4 | absent | legacy |
| v1.39.4+ first-install (no rotation yet) | absent | legacy |
| v1.39.4+ post-rotation | present | marker-required |
| Quarantine ceremony | present | marker-required (rotation_trigger=quarantine_pre_fix) |
| Manual rename without ceremony | absent | legacy (intentional gap) |

## Vote trigger (ADR-095 no-calendar-gates)

Data-volume gate. PROPOSED → ACCEPTED after:
- (a) 30 days production rotation traffic post-v1.39.4 ship, OR
- (b) 5 rotation events post-ship (whichever first)

## Implementation refs

- `_lib.audit_emit._emit_chain_reset_marker_under_lock()` — marker write + manifest + sidecars
- `_lib.audit_emit.emit_chain_reset_marker()` — public typed wrapper
- `_lib.audit_hmac.write_rotation_manifest()` / `read_rotation_manifest()` / `delete_rotation_manifest()` + `ROTATION_MANIFEST_FILENAME` constant
- `audit-verify-chain.py::verify(enforce_marker_if_manifest, log_dir)` extension
- `.claude/plans/PLAN-112-FOLLOWUP-hmac-tamper-fix/scripts/quarantine_pre_fix_log.py` — Wave B.2 ceremony

## Threat-model delta vs ADR-055

**Defends additionally**: silent rotation-during-tamper (attacker can no longer silently rotate to "clean" chain — marker absence = TAMPER under marker-required mode)

**Does NOT defend**:
- Manifest deletion: attacker with FS write deletes manifest → verifier falls back to legacy mode. Mitigation: external anchor per ADR-055 §Out-of-scope
- Marker forgery: attacker with key access can forge valid marker. Same residual as ADR-055 §Threat model "Key theft"

## Residual-monitoring (PLAN-118 WS-D, S181 — identity-trust-architect ADJUST)

- **Manifest-deletion is detectable by a sidecar-divergence check.** If
  `audit-log.last-hmac` is non-zero AND `audit-log.chain-length` ≥ 1 AND
  the rotation-manifest is absent, that is a forensic inconsistency: a
  clean genesis would have zeroed both sidecars. A future observability
  follow-up SHOULD surface this divergence as a tamper signal (the
  manifest-deletion → legacy-mode fallback is otherwise silent). Documented
  here for honesty about a detection vector the §Threat-model delta left
  implicit.
- **`previous_archive_last_hmac` is attestation-only, not re-verified.** Per
  §Verifier behavior the verifier does NOT walk archives (preserves ADR-055
  §Non-goals "log = source of truth"); the same audit key signs both the
  archive tail and the new marker, so the key-lifecycle anchor is preserved
  across rotations, but the bridge field is producer attestation. An OPTIONAL
  `--verify-archive-bridge` verifier flag (default-off; opt-in forensic
  deep-verify) is a candidate future amendment — out of scope here.

## Soak-substitution doctrine (PLAN-118 WS-D AC-D0 Owner-override, S181)

The PLAN-118 AC-D0 prerequisite (≥2 ORGANIC rotations soak per ADR-095) was
Owner-overridden for this promotion. The override is a legitimate evidence
substitution, not erosion, because the WS-A/B/C chokepoint architecture
changed the proof model from **probabilistic** ("watch the producer not break
under organic load") to **mechanical** ("the producer-pollution failure mode
raises `AuditProducerPathPollutionError` at the emit chokepoints — structurally
impossible to emit a polluted marker"), and WS-E added a class-closure guard
(`BuildEntryCanonicalEncodeGuardTest`) for the float-in-HMAC root cause that
the S164 closure missed. Combined with: the ADR's own vote-trigger leg-b
independently MET (8 rotation markers strictly post-v1.39.4-ship-commit
2026-05-21T15:19:54Z, ≥ the required 5); the live chain
verifying `intact` under `--strict-against-counter` post-fix+rotation; and the
forensic archives preserving every pre-fix byte verbatim — the substitution is
auditable and reusable. Precedent: S179 AC-C0 override
([[feedback-owner-override-ac-c0-stale-producer-evidence]]).
