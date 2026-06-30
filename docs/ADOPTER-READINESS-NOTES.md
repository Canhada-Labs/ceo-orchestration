# Adopter readiness notes — telemetry-only subsystems (honesty statement)

> **Purpose (E10-F6 / AC10.11):** two framework subsystems *look* enforcing
> but are, by design, **telemetry-only** in the current release. This doc is
> the adopter-facing honesty statement so you do not over-rely on them as
> hard guards. The engineering-internal detail lives in
> `.claude/hooks/_lib/EXECUTION-CONTEXT-DEFERRED.md` and in the (closed)
> `PLAN-112-FOLLOWUP-*` plans; this file restates it where adopters read.

## 1. `execution_context` — intra-process only

**Claim it does NOT make:** cross-process tamper-evidence for the spawn
handoff.

`execution_context` provides tamper-evidence **within a single process**.
It does **not** replay-protect or cryptographically bind a hand-off across a
process boundary (e.g. parent session → spawned sub-agent in a separate
process). A cross-process HMAC binding was evaluated and **DEFERRED**
(Owner-ratified, S154 — `PLAN-112-FOLLOWUP-execution-context-wire`, decision
RESCOPE-DEFER; see `ADR-133` + `.claude/hooks/_lib/EXECUTION-CONTEXT-DEFERRED.md`).

**Adopter takeaway:** treat the spawn-handoff context as *forensic / advisory*
at the process boundary, not as a replay-protected security control.

## 2. persona-routing — consult + audit only (no BLOCK)

**Claim it does NOT make:** blocking a routing/model-tier violation.

Persona-routing records a routing decision and emits a forensic audit event.
It runs in **consult + audit** mode: a routing violation is **recorded**, not
**blocked**. Block-mode was deferred because the hook I/O payload does not
carry the `requested-model` signal block-mode would need
(`SPEC/v1/hook-io.schema.md`); the decision is acknowledged in
`PLAN-112-FOLLOWUP-persona-routing-wire` (a closed plan).

**Adopter takeaway:** persona-routing gives you a routing **audit trail**, not
an enforcement gate. If you need hard routing enforcement, add it at your own
orchestration layer; do not assume the framework rejects an off-policy route.

## 3. Taxonomy normalisation

The PLAN-120 audit flagged that one subsystem can be labelled three ways —
ACTIVE-DEFAULT-OFF, looks-wired-but-not-enforcing, and telemetry-only —
across different axes. For an adopter the operative label for **both**
subsystems above is **telemetry-only**: wired, observable, and useful for
forensics, but **not a blocking control** in this release.
