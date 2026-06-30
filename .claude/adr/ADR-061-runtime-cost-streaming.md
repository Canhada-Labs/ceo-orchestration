# ADR-061 — Runtime cost streaming + OTLP export

**Status:** ACCEPTED
**Date:** 2026-04-18 (drafted) / 2026-04-19 (post-implementation update) / 2026-04-20 (ACCEPTED by Owner)
**Proposer plan:** PLAN-040 (Wave C polish, Sprint 27)
**Supersedes:** none
**Superseded by:** none

## Context

`ceo-cost.py` (PLAN-022 Phase 3) is a static-pricing × batch-aggregation
tool — it reads `audit-log.jsonl` + rotated siblings, sums tokens per
model, and prints a rollup. Adequate for weekly / monthly cost reviews.

**Gap:** no runtime observability. An adopter at adopter-1-scale
(500k LoC, multiple concurrent sessions, daily load) cannot see the
cost curve as it happens — only post-hoc. PLAN-026 external audit of
the `awesome-plugins` ecosystem surfaced Manifest plugin's real-time
OTLP streaming pattern as a state-of-the-art benchmark.

## Decision drivers

- **Adopter need (adopter-1):** real-time cost dashboard, not post-
  session report.
- **Industry standard:** OTLP over HTTP is the canonical
  observability protocol. Grafana, Datadog, Prometheus, and most
  cloud vendors accept it natively.
- **Stdlib-only constraint (ADR-002):** no new runtime dependencies.
  urllib.request can emit OTLP/HTTP JSON without the OTLP SDK.
- **Fail-open discipline (ADR-005):** cost observability must never
  block or crash the audit / spawn path — endpoint down → log locally
  and continue.

## Options considered

### Option A — Expand `ceo-cost.py` with `--stream` + `--otlp-endpoint` (CHOSEN)

Additive flags to the existing CLI. Kill-switch opt-in via
`CEO_COST_STREAMING=0`. Same process, same dependencies.

**Pros:**
- stdlib-only; zero dependency churn
- opt-in; existing batch users pay nothing
- single-file implementation; easy to review
- kill-switch granular

**Cons:**
- +~500 LoC to `ceo-cost.py` (from 504 → ~1000). Mitigated by section
  comments + test harness parity with batch path.
- Streaming process blocks in a tail loop when run interactively;
  adopters must wrap in nohup / systemd / equivalent.

### Option B — Dedicated streaming daemon process

Separate binary `.claude/scripts/ceo-cost-stream.py` with its own
lifecycle.

**Pros:**
- Decoupled from batch path.

**Cons:**
- Two processes to document, monitor, and kill-switch.
- Duplicated audit-log parsing + pricing code.
- No gain over Option A's single-file extension.

**Rejected.**

### Option C — Defer until adopter explicit request

**Pros:** YAGNI.

**Cons:** the adopter (Owner / adopter-1 install) has requested this
implicitly by scoping PLAN-040. Deferring further postpones the
adopter-1 Sprint 15 install gating.

**Rejected.**

## Decision

**Option A.** Additive `--stream` and `--otlp-endpoint` flags on
`ceo-cost.py`, with:

- **Inode-tracked tailing** (DevOps P0-1 closure, Round-1 debate)
  for log-rotation recovery.
- **`_http_post` DI seam** (QA P0-2 closure, Round-1 debate) to make
  the network boundary testable without a live collector.
- **Auth-token + endpoint-path redaction** in failure breadcrumbs
  (DevOps P0-2 closure).
- **Bounded in-memory queue + JSONL fallback on failure** (DevOps P0-2
  closure).
- **Periodic heartbeat emit** (DevOps P0-3 closure) for external
  zombie-process detection.
- **Injectable `tick_fn`** (QA P0-1 closure) so tests drive iterations
  synchronously with zero real `time.sleep`.
- **Injectable `time_fn`** — deterministic clock for alert-threshold
  and heartbeat tests.
- **6-row decision-table env-var matrix** (QA P0-3 closure) covering
  kill-switch, explicit opt-in, path override, missing OTLP env,
  custom fallback path, custom alert thresholds.

## Threat model

- **T1: Auth-token leak via logs.** Mitigated: failure breadcrumbs
  emit only `scheme://host[:port]` via `_redact_endpoint()`. Tests
  assert the bearer token never appears in stdout or fallback.
- **T2: Silent drop on endpoint failure.** Mitigated: local-fallback
  JSONL + `cost.stream.post_failure` breadcrumb on every non-2xx /
  timeout / DNS-failure / TLS-failure. External monitors can alert on
  breadcrumb rate.
- **T3: Zombie streamer.** Mitigated: periodic heartbeat event
  carries `last_event_ts_unix_ms` + `post_failures_total`. Monitor
  for "no heartbeat for 5 min" → process is stuck.
- **T4: Log rotation loss.** Mitigated: inode tracking — after every
  empty read we compare `stat(path).st_ino` to the open fd's ino; on
  mismatch we close and re-open at offset 0.
- **T5: Budget blow-out via bear-stearns-style cascade.** Mitigated:
  alert thresholds + running totals per session + per day fire
  `cost.alert.*_threshold` events once per boundary crossing. Adopter
  pipes these to paging infra.
- **T6: Two-factor disablement mis-config.** Accepted residual:
  `CEO_COST_STREAMING=0` is a single-factor kill-switch — the feature
  is not VETO-governed. This is by design (cost observability is
  adopter-owned, not framework-governed).

## Consequences

**Positive:**
- Runtime cost observability adopter-ready.
- OTLP compat = Grafana / Datadog / Prometheus out of the box.
- Fail-open semantics preserve existing audit-log discipline.
- 69 tests (13 batch + 56 streaming) cover debate-convergent closures.

**Negative:**
- `ceo-cost.py` size increases from 504 → ~1000 LoC. Section comments
  keep the streaming block navigable.
- HTTP POST in the hot path adds CPU; measured overhead < 5 ms p95
  per event (stdlib only).
- New operational artifact: `cost-stream-fallback.jsonl` requires
  log-rotation ownership (adopter).

**Neutral:**
- Batch mode unchanged; default remains batch.

## Blast radius

**Moderate.** `ceo-cost.py` expansion, new stdout JSON event shapes,
new optional HTTP boundary, new docs (`docs/OTLP-DASHBOARD-SAMPLES.md`),
new test file (`test_ceo_cost_stream.py`). No change to hooks, to
audit-log schema, to spawn protocol, or to governance surface.

## Reversibility

**High.** Delete the streaming block from `ceo-cost.py` + remove
`--stream` + `--otlp-endpoint` + related tests. Batch path is
structurally unchanged.

**Kill-switch today:** `CEO_COST_STREAMING=0` disables without code
removal. CI continues to exercise the batch path as before.

## Follow-up

- Adopter-side dashboard curation under `docs/OTLP-DASHBOARD-SAMPLES.md`
  as new stacks are validated.
- If OTLP post-failures become a sustained signal, escalate to
  PLAN-NNN for queue-with-retry (currently single-attempt + fallback).
- Consider extracting the streaming state machine to a `_lib` module
  if a second consumer appears (e.g. tier-policy cost-envelope gate).

## Enforcement commit

`982fd658ee67` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
