# ADR-035: OpenTelemetry export (OTLP/HTTP JSON) with defense-in-depth

**Status:** ACCEPTED
**Date:** 2026-04-14
**Sprint:** 11 (PLAN-011 Phase 8, CRITICAL CR3 bundle)
**Blast radius:** L2 — one new CLI, one new `_lib` module, one new
workflow, one new ADR, one new doc. No existing hook or workflow
modified.
**Related:** ADR-002 (hooks package layout, stdlib-only), ADR-005
(event stream v2, fail-open), ADR-011 (injection_flag — audit-drop
event pattern), ADR-023 (docs-freshness lifecycle — 3-state precedent),
ADR-024 (perf baseline — advisory → gate pattern), ADR-027 (unified
state backend — audit redaction precedent), SPEC/v1/audit-log.schema.md
§otel_export_dropped.

## Context

Sprint 11's debate round 1 raised **CR3 (CRITICAL)**: "OTEL export is
an SSRF and secret-exfiltration surface." An attacker — or a buggy
caller — that can set the OTLP endpoint URL can reach cloud-metadata
services (`http://169.254.169.254/latest/meta-data/iam/`), local
filesystems (`file:///etc/passwd`), or protocol-smuggling gateways
(`gopher://`). Worse, the audit log we would export contains hook
inputs that may include Owner source code snippets — naively
serializing span attributes is a secret-exfil channel.

The consensus mitigation bundle (VPE + Security + Backend: all HIGH,
all REQUIRED) is:

1. Scheme allowlist: HTTPS-only.
2. Host allowlist: `CEO_OTEL_ALLOWED_HOSTS`, empty default rejects all.
3. Double redaction: every span attribute value passes through
   `redact_secrets` twice.
4. Drop `description_hash`: SHA-256 of plaintext is externally
   correlatable given a partial corpus.
5. Audit the drops: `otel_export_dropped` event on every drop,
   endpoint recorded host-only (no URL path or query).
6. Smoke receiver: stdlib `http.server` subclass; NO third-party
   GitHub Action.

ADR-035 documents these decisions and the Sprint 11 → Sprint 12
lifecycle.

## Decision drivers

- **Defense-in-depth over point defense.** Any one of the six
  mitigations could be bypassed by a subtle bug; all six together
  make bypass infeasible without dropping framework governance.
- **Fail-closed configuration.** Empty `CEO_OTEL_ALLOWED_HOSTS` ⇒
  every export rejected. There is no "default allowlist". Operators
  opt into each destination explicitly.
- **Stdlib-only.** ADR-002 constraint. `urllib.request` for POST;
  `http.server` for smoke. Zero new pip deps. Notably excludes the
  `opentelemetry` Python SDK — OTLP/HTTP JSON is a stable wire
  protocol we can emit directly.
- **Fail-open on audit.** ADR-005: the library path must never raise
  in hook context. `try_export_events` swallows; the CLI path raises
  because it's Owner-initiated.
- **Advisory now, gate later.** ADR-023/ADR-024 precedent: ship the
  machinery, measure, flip. Sprint 11 smoke never fails CI; the
  decision to gate blocks on signal quality.

## Options considered

### Option A — opentelemetry-sdk pip dependency

Use the official SDK with its JSON and gRPC exporters.

**Pros:** idiomatic, batched export, gRPC available.
**Cons:**
- Violates ADR-002 stdlib-only.
- Transitively pulls in `protobuf`, `grpcio`, `opentelemetry-api`, each
  with its own CVE surface and upgrade cadence.
- SDK defaults include resource detectors that probe environment
  (env-var bleed risk).
- No mechanism in the SDK to enforce host allowlist or scheme
  restriction without wrapping — at which point we've reinvented
  half of it.

**Rejected** — dep surface + weaker invariants than stdlib.

### Option B — defer to an external tool (Vector, OpenTelemetry Collector)

Ship the audit log; let operators point a sidecar at it.

**Pros:** the framework never originates the HTTP request.
**Cons:**
- Pushes the SSRF surface to the operator; we lose the redaction
  pipeline (no one else knows about `description_hash`).
- Requires the operator to deploy a sidecar just to get traces.
- No audit trail of what was exported from our side.

**Rejected** — abdicates the defense-in-depth requirement.

### Option C (CHOSEN) — stdlib OTLP/HTTP JSON exporter with mitigation bundle

Implement the OTLP JSON wire format directly on `urllib.request`,
with a mandatory validation pipeline.

**Pros:**
- Zero new deps.
- All six CR3 mitigations enforced at the only code path.
- Audit log captures drops + host-only breadcrumbs.
- Dry-run path proves payloads without network.

**Cons:**
- We maintain a small amount of OTLP JSON mapping code (event_to_span,
  batch_to_otlp).
- No gRPC. (Acceptable — every OTLP receiver supports HTTP/JSON.)
- No built-in batching. (Acceptable — `export_events` takes an iterable;
  caller chunks as needed.)

**Chosen** — aligns with ADR-002 and keeps defenses in one place.

## Decision

### 1. CR3 mitigations (point-by-point)

| # | Mitigation | Implementation locus | Test coverage |
|---|-----|-----|-----|
| 1 | **HTTPS-only scheme allowlist** | `otel_emit.validate_endpoint` — rejects non-`https`. Unit-tested for http/file/gopher/ws. | `TestSchemeAllowlist.*` (4 tests) |
| 2 | **Host allowlist via `CEO_OTEL_ALLOWED_HOSTS`** | `_parse_allowed_hosts` + case-insensitive match. Empty → empty list → reject-all. | `TestHostAllowlist.*` (4 tests) |
| 3 | **Double redaction** | `otel_emit.double_redact` applies `redact_secrets` twice. Called for every string span attr + every header value. | `TestDoubleRedact.*` (3), `TestDoubleRedaction.*` (2), `TestHeadersRedact.*` (3) |
| 4 | **`description_hash` drop** | `_EXPORT_FIELD_DENYLIST` in `otel_emit`. Applied in `_sanitize_attrs`. | `TestDescriptionHashDrop.*` (2) |
| 5 | **Audit the drops** | `emit_otel_export_dropped` fires on every redaction drop AND every scheme/host reject. Endpoint is host-only. | `TestDropEmission.*` (2) + CLI test validates host-only |
| 6 | **Stdlib smoke receiver** | `otel-smoke.yml` uses `http.server.BaseHTTPRequestHandler` subclass inline. No third-party action. | Workflow Test 4 + `TestMockReceiverRoundTrip` unit |

### 2. Three-state lifecycle (mirrors ADR-023/ADR-024)

```
    Sprint 11             Sprint 12 (conditional)     Sprint 13+ (optional)
┌────────────────┐    ┌────────────────┐    ┌────────────────┐
│  State 0       │───▶│  State 1       │───▶│  State 2       │
│  advisory      │    │  blocking      │    │  auto-export   │
│  smoke CI +    │    │  smoke CI      │    │  from          │
│  manual CLI    │    │                │    │  audit_log.py  │
│                │    │                │    │                │
│ Owner-invoked  │    │ workflow exits │    │ hook-side path │
│ exporter;      │    │ non-zero on    │    │ auto-POSTs via │
│ smoke workflow │    │ transport /    │    │ try_export_    │
│ never fails    │    │ validation     │    │ events() +     │
│ build          │    │ error          │    │ fail-open      │
└────────────────┘    └────────────────┘    └────────────────┘
```

**Sprint 11 ships State 0.** `.github/workflows/otel-smoke.yml` runs
advisory-only. Any failure is surfaced via `::notice::` but does not
block the build.

### 3. Flip criteria

| From | To | Criterion | Owner | Review cadence |
|---|---|---|---|---|
| State 0 | State 1 | `otel_export_dropped` event rate stable within ±20% across **two consecutive weeks** (via `audit-query.py`). No "surprise drop spike" lurking in recent merges. | DevOps lead | Weekly status review. |
| State 1 | State 2 | Post-enforcement, `try_export_events` is wired into `audit_log.py` at end-of-hook. Requires: (a) zero `ADR-005` fail-open breaches in 30 days; (b) Owner signs off on auto-export to at least one registered allowlist host. | Security + DevOps | One-shot. |

**Sprint 12 PR** that flips State 0 → State 1 MUST include a fresh
`audit-query.py otel-drops --since 14d` report showing the ±20%
stability. Without that data, the PR is not approved.

### 4. Non-goals

- **gRPC OTLP.** Explicitly excluded. Every production OTEL receiver
  supports OTLP/HTTP JSON; gRPC adds dep surface for no user benefit.
- **Metrics / logs export.** Sprint 11 covers traces only. Metrics
  (OTLP MetricsRequest) and Logs (LogsRequest) require separate
  mapping and separate ADR.
- **Batch sizing / backpressure.** `export_events` takes one batch;
  oversize batches raise. Chunking is the caller's responsibility.
  Sprint 12+ may add a paginator if needed.
- **Cert pinning.** `--no-tls-verify` is gated behind
  `CEO_OTEL_SMOKE=1`. No pin-on-first-use mechanism. Callers with
  stronger TLS requirements deploy their own sidecar.

### 5. Environment variables

| Var | Default | Effect | Scope |
|---|---|---|---|
| `CEO_OTEL_ALLOWED_HOSTS` | unset (empty) | Comma-separated hostnames allowed as export targets. Empty ⇒ reject all. | CLI + library |
| `CEO_OTEL_SMOKE` | unset | When `1`, `--no-tls-verify` is honored. Intended for CI smoke only. | CLI only |
| `CEO_SOTA_DISABLE` | unset | When `1`, all Sprint-11 surfaces (including otel-export) short-circuit. Matches H11/S4. | CLI + library |
| `CEO_OTEL_ENDPOINT` | unset | **Reserved** — Sprint 12 hook-side integration. Not read by CLI. | Reserved |

### 6. Consumers

- **Sprint 11**: CLI (`.claude/scripts/otel-export.py`) only. Owner
  runs it manually or on a cron the operator configures.
- **Sprint 12 (planned, not committed)**: `audit_log.py` end-of-hook
  path calls `otel_emit.try_export_events(os.environ.get("CEO_OTEL_ENDPOINT"), [event])`
  with full fail-open wrapping. ADR follow-up required; this ADR
  only reserves the env var.

## Consequences

### Positive

- One code path enforces six defenses; no way to opt out at runtime.
- Every rejected / dropped field becomes a queryable audit event.
- Smoke workflow validates the entire pipeline without third-party deps.
- Dry-run mode gives Owner a safe way to inspect the payload before
  enabling real POST.
- ADR-023/ADR-024 three-state pattern is now reusable — Phase 9
  (output-safety) and Phase 12 (squad marketplace) will inherit.

### Negative

- Empty-default allowlist means operators see a confusing "not in
  allowlist" error on first use. Mitigated by `docs/otel-integration.md`
  which leads every recipe with the `CEO_OTEL_ALLOWED_HOSTS` export.
- OTLP JSON (not protobuf) is slightly more verbose; batches may hit
  the 1 MB protective cap sooner. Mitigated by `--since` filter.
- Double-redaction adds ~1 ms per event on typical audit lines. Within
  the ADR-024 advisory budget; measured separately in Sprint 12.

### Neutral

- Adds one weekly + on-push + on-dispatch workflow. Minor CI cost.
- No existing hook or ADR is modified.

## Transition Log

*This appendix follows ADR-041 Transition Log Convention. Each row records
a state transition triggered by a flip criterion in its window.*

| Date | From-State | To-State | Evidence-Link | PR-Ref | Signer |
|------|------------|----------|---------------|--------|--------|
| _(empty — first flip pending per PLAN-012)_ | | | | | |

## References

- PLAN-011 Phase 8 (this commit).
- Debate round-1 consensus §CR3 (CRITICAL).
- ADR-002, ADR-005, ADR-023, ADR-024, ADR-027 (precedents).
- `SPEC/v1/audit-log.schema.md` §`otel_export_dropped`.
- `docs/otel-integration.md` — operator guide.
- `.claude/scripts/otel-export.py` — CLI.
- `.claude/hooks/_lib/otel_emit.py` — library.
- `.github/workflows/otel-smoke.yml` — advisory smoke CI.

## Enforcement commit

`0fc52c780996` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
