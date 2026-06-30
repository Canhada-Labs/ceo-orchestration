# ADR-087 — OpenTelemetry span emit REFUSED — audit-log JSONL is canonical observability

## Status

ACCEPTED — Wave A re-ceremony 2026-04-27 — round-21 sentinel — Owner key 0000000000000000000000000000000000000000

## Context

PLAN-056 Phase 5 originally proposed 1-2 dev-dias to add
OpenTelemetry-native span emission alongside the existing
`audit-log.jsonl` event stream. Trigger was Session 60 landscape
audit identifying OTel as 1 of 3 real gaps (Phoenix has it).

Owner directive Session 67 (Claude-only depth-over-breadth) reframes:
audit-log JSONL is the canonical observability format and adding OTel
adds vendor coupling without proven uplift.

## Existing observability stack

| Artifact | Format | Coverage | Adopter access |
|---|---|---|---|
| `audit-log.jsonl` | JSONL append-only | Every tool call + agent spawn + governance event + 30+ action types | `audit-query.py` (9 sub-commands), `grep`, `jq` |
| `audit-telemetry.py` | CLI aggregator | Per-archetype dispatch counts, mode breakdown, p50/p95 latency, fabrication rate | `python3 .claude/scripts/audit-telemetry.py --window 7d` |
| `ceo-diagnose.py` | CLI health-check | 7 probes: open plans, governance, audit-log freshness, dispatch modes, ADR-082 status, install mode, hook tests | `python3 .claude/scripts/ceo-diagnose.py` |
| HMAC chain (ADR-055) | per-event field | Tamper detection across the audit log | `audit-verify-chain.py` |
| `validate-governance.sh` | shell script | Governance health (errors + warnings + skill inventory) | `.claude/scripts/validate-governance.sh` |

OpenTelemetry's value proposition is **vendor-agnostic export**
to a tracing backend (Jaeger / Datadog / Honeycomb / Tempo / etc).
This requires:

1. OTel SDK dependency (or stdlib OTLP-protocol implementation).
2. Span model mapping from event-based audit-log to span-tree.
3. Configuration surface for trace exporter endpoint + auth.
4. Test coverage for span emission + sampling + buffering.
5. Documentation for adopter setup.

For ceo-orchestration's use case (governed agentic engineering work
with adopter teams running locally or in CI), the audit-log JSONL
already provides:

- Append-only durability (FileLock per write).
- HMAC chain tamper detection.
- Action taxonomy (30+ actions registered in `_KNOWN_ACTIONS`).
- Time-series via `ts` field on every event.
- Aggregation tooling (`audit-telemetry.py`).

## Decision

**REFUSE PLAN-056 Phase 5 (OpenTelemetry emit)** with reason
`(b) cost-exceeds-benefit` per refused-ADR taxonomy.

Specifically:

1. No OTel SDK dependency added.
2. No span-emission alongside audit-log writes.
3. Reaffirm `audit-log.jsonl` as canonical observability.
4. Document `audit-telemetry.py` + `ceo-diagnose.py` as the
   recommended observability surface for adopter teams.
5. Update `docs/OBSERVABILITY.md` (new shipped under PLAN-056
   Phase 6 closeout) explaining the audit-log-first approach +
   how to integrate with external systems via tail+parse pattern
   (no native push, but standard JSONL ingestion is universally
   supported).

## Consequences

### Positive

- 1-2 dev-dias removed from roadmap permanently.
- No new dependency surface (OTel SDK or OTLP protocol stdlib impl).
- No vendor coupling to specific tracing backends.
- Adopter teams already familiar with `grep`/`jq` for JSONL get a
  zero-tooling-cost observability story.

### Negative

- Adopter teams running OTel-native observability stacks (Jaeger,
  Datadog, Honeycomb, Phoenix) must run an external tail-and-export
  process to bridge `audit-log.jsonl` → OTel. This is a documented
  pattern but adds friction.
  - Mitigation: `docs/OBSERVABILITY.md` includes a recipe using
    `tail -F` + `jq` + `curl` to a chosen OTel collector.
- Phoenix users specifically may expect rich-trace span tree;
  audit-log is event-based not span-based.
  - Mitigation: span-tree can be reconstructed post-hoc from
    audit-log via `session_id` correlation field. Acceptable for
    forensic + soak-window analysis use cases.

### Neutral

- Existing audit-log machinery (`audit_emit.py`, `audit-log.jsonl`,
  HMAC chain) is unchanged.
- Future Anthropic or Claude Code harness updates that emit OTel
  natively may make this ADR obsolete.
  - Mitigation: ADRs revisable.

## Alternatives considered

### A. Add OTel emit alongside audit-log (REJECTED)

Cost ~1-2 dev-dias. Rejected because:
- Doubles emit surface area (every emitter needs OTel call too).
- OTel SDK adds dependency burden.
- No concrete adopter request.

### B. OTel-only, retire audit-log (REJECTED)

Massive blast radius (HMAC chain + 30+ actions + audit-query.py
all rebuilt). Audit-log is canonical for governance reasons (HMAC,
canonical-edit sentinel verification). OTel-only is non-starter.

### C. Stdlib OTLP-protocol implementation (REJECTED)

Adds maintenance burden equivalent to bringing in OTel SDK without
the SDK's testing/maturity.

### D. Document tail+export pattern (CHOSEN — see Decision)

Ship `docs/OBSERVABILITY.md` showing recipe to integrate with OTel
collectors via JSONL tail. No new code.

## Enforcement commit

To be filled in at Session 67 D5 closeout (this ADR's promotion +
`docs/OBSERVABILITY.md` land in same commit batch).

## References

- ADR-085 — Framework landscape Claude-only (this ADR is part of
  the closeout)
- ADR-055 — Audit-log HMAC chain (canonical observability is the
  governance source of truth)
- PLAN-056 Phase 5 — original proposal (refused via this ADR)
- `docs/OBSERVABILITY.md` — companion documentation deliverable
- `audit-log.jsonl` schema (`SPEC/v1/audit-log.schema.md`)
