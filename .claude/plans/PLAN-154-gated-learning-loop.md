---
id: PLAN-154
title: Gated Learning Loop
status: reviewed
reviewed_at: 2026-07-07
created: 2026-07-03
owner: CEO
depends_on: [PLAN-153]
budget_tokens: 400-700k
budget_sessions: 2
context_risk: medium
external_wait: none
tags: [learning-loop, security, governance, ecc-analysis]
---

# PLAN-154 — Gated Learning Loop

## Context

Carved out of PLAN-153 by its round-1 debate consensus (2026-07-03): the
learning-loop wave was "3-4 plans in a trenchcoat" bundling a new data
surface, a model-in-the-loop distiller, guard-behavior changes and a
canonical-guarded `lessons.py` edit — with near-zero coupling to the rest of
the uplift program. It inherits the ecc-analysis evidence
(`PLAN-153/artifacts/`) and BOTH critics' security requirements as design
constraints, not suggestions.

**Debated and reviewed.** This plan's own L3 round-1 debate ran (3×
ADJUST_PROCEED → PROCEED, see §Debate); binding adjustments A1–A13 are
applied into this text. Do not execute any item before ALL of:

1. **PLAN-153 Wave E is MERGED on main with positive-control fixtures
   green** — authored/staged does NOT satisfy this gate. (S261 status:
   Wave E infra is staged, not landed; execution of this plan remains
   blocked on that landing + SENT-F.)
2. **The LANDED Wave-E marker syntax + positive-control fixture API is
   pinned before item 1 is authored** (A11 — interface dependency, not
   just sequencing).
3. **ADR-160** is drafted and accepted, carrying the A2/A4/A6/A8/A10/A11
   normative text. (Was mis-cited as ADR-174 in the stub; corrected per
   the S261 index — the reserved learning-loop ADR is ADR-160.)
4. **SENT-F is signed with the full A13 scope**: `.claude/scripts/lessons.py`
   (canonical-guarded at `check_canonical_edit.py:129` — NOT unguarded),
   `prune-lessons.py`, `lesson-restore.py`, `lesson_ranker.py`, the
   `check_confidence_gate.py` interaction (`check_canonical_edit.py:127-132`),
   plus all new `.claude/hooks/**` paths. S258 `touched − SIGNED SCOPE = ∅`
   assert on every SENT-F commit.

## Goal

Import the CLASS of ecc's passive learning funnel (observe → distill →
candidate) under this framework's governance: nothing self-activates, the
human gate is explicitly NOT the injection defense (mechanical scanning is),
and no blocking guard ever loses legibility.

## Binding design constraints

Constraints 1–6 inherited from the PLAN-153 round-1 debate; 7–9 added and
1–6 hardened by this plan's round-1 debate (A-ids = consensus adjustment
index, `PLAN-154/debate/round-1/consensus.md`).

1. **Metadata-only v1** (Security VETO-floor condition, resolves PLAN-153
   OQ2): the observe rail extends the content-free PLAN-125 WS-1
   `tool_lifecycle.py` rail. Redacted-payload capture is a LATER opt-in gated
   behind a documented PII/PHI redaction pass (beyond `redact.py`'s
   secret-only scope) + per-install named opt-in. Healthcare/fintech installs
   must never gain an un-de-identified content store by default.
   **(A2) "Metadata" is normative, not prose:** deny-by-default field
   allowlist enforced at CAPTURE — closed enums, booleans, bounded opaque
   IDs, and hashes only; no free-text field may be added without an ADR-160
   amendment. "Redact at read" is rejected as a posture (the HMAC chain makes
   capture-time leaks permanent). Three CI assertions ship with the rail:
   (a) frozen schema-hash fixture that reds on ANY field addition until
   consciously updated in review; (b) closed-type emitter gate — no free-form
   string passes the emitter; (c) canary-exfiltration test — synthetic tool
   call carrying `CANARY_SECRET_...` in args/output → zero hits grepping the
   entire observation store — plus the kill-switch negative control: env
   unset → zero filesystem delta. Metadata-only is ALSO the injection
   control, not just the privacy floor (closed-enum input is injection-inert
   by construction) — named as such in ADR-160.
2. **Injection-scanned pipeline**: the existing injection corpus runs over
   BOTH stored observations AND distiller output before anything becomes a
   candidate; the distiller spawn carries the ADR-175 Prompt Defense Baseline;
   audit-log content consumed by the distiller is untrusted data (it may
   contain verbatim attacker-influenced citations per ADR-175).
   **(A4) Promotion boundary is fail-CLOSED** per the C4/`_e3` precedent
   (the `lessons.py:174-177` scanner is advisory fail-open today — that
   posture is acceptable only for the raw observe-write/telemetry side):
   scanner unavailable OR scan hit → candidate QUARANTINED (terminal state,
   visible in `/lesson-review`, never rendered anywhere, never PENDING);
   fixture: broken scanner + promotion attempt → refusal.
3. **Bounded lesson schema**: candidates are `trigger → advisory-text` from a
   constrained vocabulary — never free-form prose concatenated into
   `/ceo-boot`. Boot one-liners are fenced as untrusted data (same treatment
   as recalled memories). `/lesson-review` gains a mechanical
   imperative-detector — the human filters for usefulness, the machine for
   injection. **(A5) Boot channel hardening:** the bounded vocabulary
   excludes backticks and newlines outright; the char cap applies to content
   BEFORE fencing (cap-then-fence; cap±1 multi-byte boundary tests — the
   PLAN-152 unicode lesson class); boot-channel lesson content routes through
   the fail-CLOSED `_lib.guardrail_validator` (`check_read_injection.py:40-49`
   path), NOT the advisory scanner path; the cap is formalized as ≤3 lessons
   × ≤200 chars each, enforced via the EXISTING ceo-boot bound+scan pipeline
   (`ceo-boot.md:69` + `lessons.py:105` schema cap — no new truncation code);
   lesson text joins the `/ceo-boot --json` DENIED fields; ships a
   fence-escape/directive-payload positive-control fixture.
   **(A7) The OLD spawn path is in scope:** `format_for_injection`
   (`lessons.py:632-637`) already injects UNFENCED imperatives into every
   ranked spawn at a 2K-token cap (`lessons.py:86`) — 8× the boot cap. It is
   retrofitted to the same fenced, data-not-imperative framing in the same
   SENT-F edit, and the decay/review/dampening lifecycle governs BOTH
   consumers (boot one-liners AND the `top_k` spawn injection) — or the spawn
   cap shrinks to match. (FinOps note: this recurring boot+spawn injection
   rent — not the distiller — is the dominant cost center; TTL+decay is also
   the economic garbage collector; any future cap/count raise is a FinOps
   change, not a UX tweak.)
4. **Denial dampening is advisory-only**: condensation applies to advisory
   output exclusively. A blocking guard's block reason NEVER loses legibility
   regardless of repeat count (attacker-probing anti-pattern otherwise).
   **(A10) Dampening contract:** dampening keys on a schema decision field
   (decision = deny/block vs advisory), never a text heuristic; CI positive
   control: block reason byte-identical (modulo timestamps) at N=1 vs N=100;
   a condensed advisory ALWAYS retains {advisory ID, ordinal count,
   pointer-to-full-text}; counters are session-scoped in the per-session 0600
   file (`tool_lifecycle.py` pattern), off the audit hot path, with ≤1
   condensation audit event per advisory ID per session; ADR-160 enumerates
   the dampenable channel as human-facing PROSE only — structured events,
   audit emissions, `additionalContext`, and all block reasons are exempt by
   name.
5. **Zero self-activation** (unchanged red line): PENDING → `/lesson-review`;
   instinct→skill via SP-NNN + `/skill-review` + soak. TTL 30d + 7d warning on
   pendings. **(A9) TTL/decay determinism:** expiry is terminal EXPIRED
   (+audit event) — never any default disposition touching activation; the 7d
   boot warning is count-only ("N pendings expire in <7d", ZERO candidate
   text — no pre-approval text reaches boot through the warning side door);
   `created_at` is verified against the chain's `lesson_write` event, not the
   `$HOME` file; EVERY time function (confidence decay, TTL expiry, warning,
   dampening windows) takes an injectable `now_fn` with the wall clock only
   as default; `_recency_decay` (`lessons.py:353`) is refactored under the
   same SENT-F; golden-value boundary (day 0, half-life, TTL±1s) +
   monotonicity + twice-run-identical tests.
6. **E↔F interaction**: opt-in no-op hooks must pass `check_harness_config.py`
   without being flaggable — **(A11)** the allowlist lives GATE-SIDE (an
   explicit canonical-guarded path list in Wave E's config/fixture surface);
   an in-file marker string is INSUFFICIENT (self-exemption bypass primitive
   otherwise — a marker may exist for human readability but never suffices).
   Hard precondition: pin the LANDED Wave-E marker syntax + positive-control
   fixture API before item 1 is authored. Fixtures prove three directions:
   (a) allowlisted/marked no-op passes; (b) unmarked fail-open shim reds;
   (c) a marked-but-BLOCKING hook is still liveness-tracked (the allowlist
   cannot hide a dead rail) — plus copied-marker-still-reddens. Liveness must
   not standing-yellow a rail that is off by recorded operator choice (no
   yellow-fatigue).
7. **(A6) Integrity anchor — hash-pinned approvals.** The lesson store lives
   under `$HOME`, outside every repo guard; approval is otherwise a TOCTOU
   into `/ceo-boot`. Approval events written to the HMAC chain carry
   `sha256(trigger + advisory_text)` of the approved candidate; `/ceo-boot`
   AND the spawn path recompute and verify-before-render — mismatch → drop
   the lesson + surface an integrity flag. The chain, not the mutable file,
   is the integrity anchor. Named design principle in ADR-160.
8. **(A3) Zero new hook registrations.** No new PostToolUse/PreToolUse
   registrations; the observe extension rides `record_pre`/`record_post`
   in-place per MF-PERF-1/MF-SEC-5 (no new subprocess, no PreToolUse
   audit-chain traffic); the extended write path joins the hook-latency
   profiler corpus under the existing p95<120ms/p99<160ms CI gate.
9. **(A12) Kill-switch story.** Named opt-in ENABLE flag (suggest
   `CEO_LEARNING_OBSERVE=1`; unset = structurally off — `cost_envelope.py`
   posture), with `CEO_SOTA_DISABLE=1` master precedence documented. Observe
   and enforce surfaces sit on SEPARATE switches: disabling observe/telemetry
   never touches the deny-once gate. Each rail audit-emits a
   disabled-this-session breadcrumb once, wired to Wave-E liveness. Every new
   env var is registered in `env-inventory.json` + the CHEAT-SHEET env table
   + the autouse reset fixture in the same commit that consumes it (S218
   class).

## Wave 0 (execution start — fix before any code)

- Pre-register the item-6 numeric flip criteria into ADR-160: FP rate < X%
  over ≥ N events AND ≥ M calendar days of dogfood shadow telemetry
  (measured from the HMAC audit log) — numbers chosen here, not mid-wave (A8).
- Test-placement decision: guarded `_lib/tests/` (→ inside SENT-F scope) vs
  unguarded `hooks/tests/`; plus validate.yml test-path wiring for any new
  test directory — same-commit rule (A13).
- Verify precondition 2: LANDED Wave-E marker/fixture API pinned (A11).

## Items

1. **Opt-in metadata rail extension** (stdlib). Zero new hook registrations
   (constraint 8); capture-time closed-field allowlist + three CI assertions
   (constraint 1/A2); enable flag + kill-switch per constraint 9 (A12);
   gate-side E↔F allowlist + three-direction fixtures (constraint 6/A11).
2. **Offline distiller** proposing PENDING lesson-candidates into the
   existing `lessons.py` store (SENT-F ceremony — file is guarded). **(A4)
   Contract:** v1 read surface = metadata rail + closed vocabularies ONLY —
   any widening is its own reviewed change (the delta cursor walks the rail's
   event stream; only closed-enum fields are consumed in v1). Hermetic
   `--from-fixture` recorded-output mode is a first-class contract — CI never
   calls a live model; output schema validation is fail-CLOSED
   (unparseable/over-schema → no candidate written + breadcrumb); mandatory
   fixtures: planted hostile observation rejected pre-candidate + benign
   observation survives to PENDING. **Economics:** cadence is Owner-invoked
   or nightly-hygiene piggyback — never per-session automatic; persisted
   delta cursor/watermark; hard per-run input-token ceiling; model pinned
   EXPLICITLY haiku-tier with a named env override (NOT via the stub
   `model_routing.py`/staged `tier-policy.yml`); token usage emitted as audit
   events so `/agent-budget` shows the distiller as a line item, with the
   `docs/provider-pricing.md` row added in the same commit that pins the
   model.
3. **Confidence score with deterministic decay** in `lessons.py` (hit/miss
   exist). Injectable `now_fn` throughout; golden-value + monotonicity +
   twice-run-identical tests; `_recency_decay` refactor under the same SENT-F
   (constraint 5/A9).
4. **Top-3 lessons as fenced one-liners in `/ceo-boot`** — cap ≤3 × ≤200
   chars via the existing bound+scan pipeline, cap-then-fence,
   `_lib.guardrail_validator` route, `--json` DENIED fields, hash
   verify-before-render (constraints 3/7; A5, A6). Same-SENT-F retrofit of
   `format_for_injection` for the spawn consumer (A7).
5. **Advisory-output dampening with ordinal** (blocking reasons untouched)
   per the constraint 4/A10 contract.
6. **Fact-forcing deny-once gate ADVISORY→enforce path** with fail-CLOSED
   citation verification (converges with ADR-175 semantics). **(A8)** The
   flip is a governed, audited event: settings-backed, sentinel-scoped,
   HMAC-chain governance event on every activation change, gated on the
   Wave-0 pre-registered numeric criteria. Deny-once state binds to
   `sha256(normalized command)`, session-scoped, expires with the session; a
   retry releases ONLY an exact-hash match. Release-side verification failure
   = BLOCK (C4/`_e3`); fail-open is permitted only on the audit-emit side.
   Verification runs only on the rare already-matched path (post-matcher,
   never the common path — profiled against the p95 budget). Fixtures:
   transcript-read-failure → BLOCK; fabricated-citation → BLOCK. The deny
   message states the exact citation format that unlocks retry.
7. **`/lesson-evolve`**: trigger-clustering → SP-NNN candidates →
   `/skill-review`. Clustering deterministic v1 (Jaccard over `scope_tags`,
   $0 model spend) — advisory fixtures A15 apply during execution.

## Success criteria

- Zero writes outside pending stores without an approval event in the HMAC
  chain — extended per A6: approval events hash-pinned, and the
  verify-before-render mismatch → drop path is fixture-tested in the same
  family.
- Kill-switch flags named, documented (polarity + precedence), and registered
  (constraint 9).
- Liveness/positive-control fixtures green, including the three-direction
  E↔F set + copied-marker-still-reddens (constraint 6).
- Same-commit rule (A13): new test directories wired into validate.yml, new
  env vars into `env-inventory.json` + CHEAT-SHEET + autouse reset fixture,
  in the commit that introduces them — no CI-dark surfaces.
- Every SENT-F commit passes the S258 `touched − SIGNED SCOPE = ∅` assert.

## Advisories (non-blocking)

A14–A19 recorded in `PLAN-154/debate/round-1/consensus.md` (score-component
display + half-life docstring fix, `/lesson-evolve` e2e fixture, TTL/prune
interaction fixture, boot-cache staleness, item-4 default-OFF dogfood session
+ fixtures README + per-event byte ceiling, shared imperative-detector corpus
+ quarantine pruning). Execute or consciously waive in the wave record.

## Debate

### Round 1 — 2026-07-07 — PROCEED

- 3 archetypes: security-engineer, qa-architect, finops-dx (anonymized at
  synthesis; label↔archetype map recorded in `consensus.md` §Anonymization).
- Tally: 3× ADJUST_PROCEED, 0 VETO, 0 REJECT → round verdict
  **ADJUST_PROCEED → PROCEED**. No round 2: zero cross-critic
  contradictions; the one surface tension (distiller read surface vs
  audit-log cursor) reconciled in consensus C3.
- 19 adjustments merged/deduped: **A1–A13 BINDING — all applied into this
  file 2026-07-07** (A1 = ADR-174→ADR-160 correction); A14–A19 advisory.
- Record: `PLAN-154/debate/round-1/` (3 positions + consensus, synthesized
  2026-07-06).
- Status transition: `draft → reviewed`, reviewed_at 2026-07-07. Per
  PLAN-134 W1 doctrine the debate certifies internal coherence only —
  shipping authority remains with the verification cascade (V2 Codex
  pair-rail + V3 Owner GPG), and execution start remains gated on the
  §Context preconditions (Wave E MERGED + fixtures green — staged does not
  count; ADR-160 accepted; SENT-F signed with the A13 scope).

## How to continue

> Land PLAN-153 Wave E on main (staged as of S261 — this plan stays blocked
> until it is merged with positive-control fixtures green) → pin the landed
> marker/fixture API → draft ADR-160 from the round-1 consensus (carrying
> the A2/A4/A6/A8/A10/A11 normative text) → run Wave 0 above → get SENT-F
> signed with the A13 scope → execute items. Success criteria as above.
