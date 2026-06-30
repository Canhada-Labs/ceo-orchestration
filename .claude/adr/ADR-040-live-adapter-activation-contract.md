# ADR-040: Live Adapter Activation Contract

**Status:** ACCEPTED
**Date:** 2026-04-14
**Sprint:** 12 (PLAN-012 Phase 1, promoted from bullet to CRITICAL
deliverable per debate Round 1 consensus §C1 — 5/5 agents)
**Related:** ADR-028 (multi-LLM canonical envelope parity), ADR-031
(self-improving skills — credential + signature-hygiene precedent),
ADR-033 (cost/budget — this ADR adds an adapter-layer hard floor
INDEPENDENT of the budget-hook state), ADR-035 (OTEL export —
credential-exfiltration precedent), ADR-036 (output safety — shares
the double-redaction boundary at audit export), ADR-037 (chaos
methodology — this ADR's contract is what `tests/chaos/
test_live_adapter_*.py` exercises), ADR-041 (Transition Log Convention)

## Context

Sprint 11 Phase 1 (ADR-028) shipped the canonical `NormalizedEvent`
envelope and four pure adapters (`claude`, `gemini`, `openai`, `local`)
that parse hook stdin without network I/O. Sprint 12 Phase 1
(PLAN-012 §Phase 1 D3) wires live invocations against provider REST
APIs under a new module tree `.claude/hooks/_lib/adapters/live/` —
the framework's first outbound public-internet boundary from the hook
/ script layer.

Three system-boundary failure surfaces, each CRITICAL per PLAN-012
debate Round 1 consensus §C1 (5/5 agents):

1. **Outbound credential surface** — `ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`,
   `OPENAI_API_KEY` become live; leak paths include `.env` git
   accident (CWE-798), audit-log echo (CWE-532), OTEL span attributes
   (CWE-201), shell history, tracebacks. (Security CRITICAL-2.)
2. **Cost runaway via adversarial injection** — D3 + Phase 5 N-round
   debate (Jaccard 0.7 may not converge) + retry storm = one malicious
   spawn multiplies 50× before `check_budget.py` (State 0 advisory)
   catches it. (Chaos CRITICAL-2.)
3. **Cascading failure modes** — provider 502 / hang 28s / mid-stream
   TCP drop → hook subprocess exceeds ADR-037's 5s budget → SIGTERM
   → no audit → retry storm. (Chaos CRITICAL-1 + CRITICAL-3.)

Without a formal contract, each downstream flip (#2 budget 0→1, #5
chaos 0→1, #10 real embeddings) would invent its own ad-hoc policy.
This ADR is the single source of truth all four live adapters MUST obey.

## Decision drivers

- **Credential hygiene** (Security CRITICAL-2 + CRITICAL-3): rotation,
  scope, leak detection, OpenAI data-retention header — each normative.
- **Cost containment** (Chaos CRITICAL-2): $0.50 per-spawn ceiling +
  MAX_ROUNDS=5 debate hard stop at **adapter layer**, independent of
  any hook's flip state.
- **Failure isolation** (Chaos CRITICAL-1 + CRITICAL-3): concrete
  timeout/retry/breaker numbers, not "reasonable" handwaving
  (`architecture-decisions` mantra).
- **Auditability**: every call emits at least one audit event; zero
  silent network activity.
- **Stdlib-only preservation** (ADR-002): `urllib.request` against
  provider REST APIs, no vendored SDKs.

## Options considered

**Option 1 — Vendored provider SDKs (rejected).** Each adapter on its
provider's official Python SDK. *Pros:* exhaustively tested; handles
retries/pagination/streaming. *Cons:* 4 SDKs × transitive deps ≈ 40+
packages; version-pin hell; weaker audit (no wire-byte visibility →
credential tests become SDK-implementation-dependent); breaks
stdlib-only invariant (ADR-002).

**Option 2 — Custom stdlib urllib wrapper with shared policy (CHOSEN).**
Hand-rolled `urllib.request` against provider REST endpoints, wrapped
in a frozen `LiveCallPolicy` dataclass enforcing
timeout/retry/breaker/cost. All four adapters inherit. *Pros:* zero
new deps; full wire-byte visibility; one tunable policy surface;
uniform audit; `CEO_SOTA_DISABLE=1` short-circuits via existing
kill-switch. *Cons:* hand-rolled parsing has bug surface (Chaos
MEDIUM-2 — truncated-body); manual rotation; opt-in per-provider
complicates CI matrix (mitigated by D3.4 chaos coverage and
`adapter-live.yml` split).

**Option 3 — Defer D3 to Sprint 13+ (rejected).** Fixture-only this
sprint. Blocks PLAN-012 flips #2 + #10 directly; pushes D4 shadow-CI
meaning to Sprint 13; carries risk forward indefinitely.

## Decision

### §1. Per-call policy (enforced at adapter layer, NOT hook layer)

| Knob | Value | Source |
|------|-------|--------|
| `connect_timeout_ms` | 2500 | Chaos CRITICAL-1 |
| `read_timeout_ms` | 8000 | Chaos CRITICAL-1 |
| `max_retries` | 1 | Chaos CRITICAL-1 |
| `backoff_initial_ms` | 250 | Chaos CRITICAL-1 |
| `backoff_max_ms` | 1000 | derived |
| `backoff_jitter_pct` | 100 (full jitter) | AWS Architecture Blog convention |
| `breaker_threshold` | 5 failures per 30s window | Chaos CRITICAL-1 |
| `breaker_half_open_s` | 60 | Chaos CRITICAL-1 |

Enforcement lives in `_lib/adapters/live/_policy.py` (frozen
`LiveCallPolicy`) and `_lib/adapters/live/_breaker.py` (per-provider
breaker). Hook callers consume a typed `Result`; they do NOT inspect
transport behaviour.

### §2. Failure semantics

| HTTP / transport | Classification | Retry? | Breaker effect | Audit event |
|------------------|----------------|--------|----------------|-------------|
| 401 / 403 | PERMANENT auth | No | Opens immediately | `auth_permanent_failure` |
| 429 | TRANSIENT | 1, full-jitter | Counts toward threshold | `live_adapter_call_failed` |
| 5xx | TRANSIENT | 1, full-jitter | Counts toward threshold | `live_adapter_call_failed` |
| Connect timeout | TRANSIENT | 1 | Counts | `live_adapter_call_failed` |
| Read timeout | TRANSIENT | 1 | Counts | `live_adapter_call_failed` |
| Connection refused | TRANSIENT | 1 | Counts | `live_adapter_call_failed` |
| Malformed JSON | PERMANENT (this call) | No | Does NOT count (prompt-triggered DoS risk) | `live_adapter_call_failed(failure_mode=parse_error)` |

Once the breaker opens, subsequent calls fail-fast in `<50ms` with
audit `breaker_opened` (first) or `breaker_open` (subsequent). After
`breaker_half_open_s=60` a single probe is permitted; success emits
`breaker_closed`, failure resets the 60s clock.

### §3. Cost ceiling

| Knob | Value | Enforcement |
|------|-------|-------------|
| `MAX_SPEND_USD_PER_SPAWN` | 0.50 | Adapter pre-flight (estimate `tokens × docs/provider-pricing.md` rate) |
| `MAX_SPEND_USD_PER_PLAN_5MIN` | 2.00 | Rolling 5-min window per `plan_id` |
| `MAX_ROUNDS` (debate) | 5 | `_lib/debate/convergence.py` regardless of Jaccard |

Exceeding any ceiling → fail-fast with `budget_hard_stop`
(`reason=per_spawn|per_plan_5min|debate_max_rounds`). Does NOT retry.
This floor is **independent of `check_budget.py` hook state (0/1/2)**
per consensus §S2 — the hook is advisory; the adapter is the
load-bearing ceiling.

### §4. Credential lifecycle

- **Storage:** env var only (`ANTHROPIC_API_KEY`, `GOOGLE_API_KEY`,
  `OPENAI_API_KEY`). No files. No keychain in Sprint 12.
- **Caching:** NONE. Re-read env on every call via `os.environ.get`
  at call-site, enabling mid-session rotation (Chaos MEDIUM-1).
- **Age:** 90-day hard maximum. `credential_rotation_due` audit event
  fires on every call once the key is >75 days old (per
  `docs/rotation-log.md`). At 90 days the event still fires but the
  adapter does not block — rotation is an operator workflow.
- **Leak detection patterns** (enforced by `check_bash_safety.py`
  extension — Agent C scope — and `.gitignore`):
  - `sk-ant-[a-zA-Z0-9_-]{8,}` (Anthropic)
  - `AIza[a-zA-Z0-9_-]{35}` (Google)
  - `sk-proj-[a-zA-Z0-9_-]{8,}` (OpenAI project keys)
  - `sk-[a-zA-Z0-9]{32,}` (legacy OpenAI)
  - `AKIA[A-Z0-9]{16}` (AWS — reserved for future providers)
- **Double redaction** at two boundaries per Security S1 precedent:
  (a) adapter response-parse before any dict hits downstream callers;
  (b) `_lib/audit_emit.py` at the audit-log export boundary
  (pre-existing from ADR-035). Either alone is sufficient; both yield
  defence-in-depth.

### §5. Scope minimization (provider-side)

- Keys MUST be provisioned with **chat-completions permission only**
  — no admin, no billing, no multi-account.
- **OpenAI:** embedding / retrieval calls MUST set header
  `OpenAI-Data-Retention: opt_out` (Security §S1); refusal to set →
  `live_adapter_call_failed(failure_mode=scope_misconfigured)`.
- **Anthropic / Google:** no equivalent REST header as of 2026-Q2;
  operator attests to dashboard retention setting in
  `docs/rotation-log.md` at key provision time.

### §6. Activation gate

- Global kill-switch: `CEO_SOTA_DISABLE=1` short-circuits every new
  Phase 1-12 surface including live adapters (PLAN-011 debate §S4).
- Per-provider flags: `CEO_LIVE_CLAUDE=1`, `CEO_LIVE_GEMINI=1`,
  `CEO_LIVE_OPENAI=1`, `CEO_LIVE_LOCAL=1`. Absent or `0` → adapter
  returns `Result(fixture=True)` without any network call.
- Enabling a provider requires three preconditions, checked at
  first-call time:
  1. Credential env var is present and non-empty.
  2. `docs/provider-pricing.md` row has `confidence: high | medium`
     (PLAN-012 Phase 0 D1 must complete before ANY provider flips).
  3. Provider name is in `.claude/settings.json` key
     `live_adapter_allowlist` (defaults to `[]` — empty = refuse).
- Default posture: **all four providers disabled**. Enabling is
  explicit operator action recorded in `docs/rotation-log.md`.

### §7. Audit events emitted per call

Every live call emits `live_adapter_call_started` on entry and exactly
one terminal event on exit; no silent calls.

| Event | When | Required fields |
|-------|------|-----------------|
| `live_adapter_call_started` | Pre-flight passes | `provider`, `model`, `estimated_tokens`, `plan_id` |
| `live_adapter_call_succeeded` | 2xx parsed | `provider`, `duration_ms`, `actual_tokens_in`, `actual_tokens_out`, `cost_usd` |
| `live_adapter_call_failed` | Terminal failure post-retry | `provider`, `failure_mode`, `retry_count`, `duration_ms` |
| `breaker_opened` / `breaker_closed` | State change | `provider`, `failure_count_in_window` |
| `budget_hard_stop` | §3 ceiling hit | `reason`, `ceiling_usd`, `observed_usd` |
| `auth_permanent_failure` | 401/403 | `provider` |
| `credential_rotation_due` | Key >75 days | `provider`, `age_days` |

Credential values MUST NOT appear in any field; double redaction per §4.

## Consequences

**Positive:** predictable cost (hard USD ceiling independent of
budget-hook state; adversarial injection cannot exceed $0.50/spawn);
bounded latency (`connect+read = 10.5s` worst-case, retry ≤~21s before
breaker intervention, fits hook budgets); clear audit trail (every
call has `_started` + terminal pair; silent network activity is a
contract violation detectable by `check-flip-criteria-drift.py` —
PLAN-012 Phase 2); no leak paths (double redaction + regex allowlist +
pre-commit grep + `.gitignore` = four scrub layers); stdlib-only
preserved, `install.sh` stays vanilla.

**Negative:** custom urllib has parse-edge bug surface vs mature SDK
(truncated body, chunked-transfer trailer garbage) — mitigated by
D3.4 chaos coverage (5 modes × 3 providers) running weekly on
`adapter-live.yml`; manual rotation (operator updates env + ledger;
`credential_rotation_due` surfaces in dashboard at day 75 but does not
block); opt-in per provider = up to 12 test-matrix combinations,
mitigated by `CEO_LIVE_ADAPTERS` umbrella flag for Owner smoke runs.

**Neutral:** flips #10 (real embeddings) and #2 (budget 0→1) both
depend on this contract per PLAN-012 Dependency Graph; Sprint 12 ships
D3 before their windows run. CI cost bounded — `adapter-live.yml`
runs weekly Monday 12:00 UTC (PLAN-012 §S6 cron stagger), not per-PR;
paths-filter scoped.

## Blast radius

**L2** — new module tree `.claude/hooks/_lib/adapters/live/` (~8 files,
~800 LOC target), extends `check_bash_safety.py` + `.gitignore`, adds
one SPEC schema + one workflow + this ADR. No existing hook behaviour
changes when all provider flags are `0`.

Files introduced (PLAN-012 D3.2/3/4/6): `_lib/adapters/live/{_policy,
_breaker,_transport,claude,gemini,openai,local,__init__}.py`;
`SPEC/v1/live-adapters-policy.schema.md`;
`tests/chaos/test_live_adapter_failure_injection.py`;
`tests/integration/test_live_adapter_smoke.py`;
`.github/workflows/adapter-live.yml` (Phase 2 D7).

Files modified: `check_bash_safety.py` (credential patterns — Agent C);
`.gitignore` (`.env` + API-key patterns — Agent C);
`_lib/debate/convergence.py` (`MAX_ROUNDS=5` — D3.5).

**Blocks:** Sprint 12 flips #2 + #10; Sprint 13+ D4 shadow-CI 7-day
window; future provider additions.

**Reversibility:** HIGH. `CEO_SOTA_DISABLE=1` short-circuits every live
call via existing kill-switch — no rollback code. Full revert =
delete the new module tree + SPEC + workflow + test files, revert the
three edited files; behaviour returns to Sprint 11.

## Transition Log

*This appendix follows ADR-041 Transition Log Convention. Each row
records a state transition triggered by a flip criterion in its window.*

| Date | From-State | To-State | Evidence-Link | PR-Ref | Signer |
|------|------------|----------|---------------|--------|--------|
| _(empty — first activation pending per PLAN-012 Phase 1)_ | | | | | |

## References

- PLAN-012 §Phase 1 D3 — this ADR's source.
- PLAN-012 debate Round 1 Consensus §C1 (5/5 agents CRITICAL).
- PLAN-012 debate Round 1 chaos-engineer.md §CRITICAL-1/-2/-3 — numeric
  values (timeouts, ceilings, breaker).
- PLAN-012 debate Round 1 security-engineer.md §CRITICAL-2/-3 —
  credential lifecycle, opt-out header.
- ADR-028 — canonical envelope (downstream return shape).
- ADR-031 — skill-patch credential hygiene precedent.
- ADR-033 §2 — budget table (this ADR adds hard floor below 0/1/2).
- ADR-035 — OTEL SSRF + exfil controls.
- ADR-036 — double-redaction boundary precedent.
- ADR-037 — chaos methodology (test harness for this contract).
- ADR-041 — Transition Log appendix format.
- `SPEC/v1/live-adapters-policy.schema.md` — companion schema.
- `docs/provider-pricing.md` — cost ceiling input.
- `docs/rotation-log.md` — credential lifecycle ledger.

## Enforcement commit

`477ed9a06a01` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
