---
plan: PLAN-154
round: 1
round_verdict: PROCEED
critiques: 3
verdicts: [ADJUST_PROCEED, ADJUST_PROCEED, ADJUST_PROCEED]
adjustments: 19
adjustments_binding: 13
created_at: 2026-07-06
synthesized_by: CEO (consensus-synthesizer)
---

# PLAN-154 — round-1 consensus

## Verdict tally

| Critic | Verdict |
|---|---|
| Critic-A | ADJUST_PROCEED |
| Critic-B | ADJUST_PROCEED |
| Critic-C | ADJUST_PROCEED |

Three critiques, three ADJUST_PROCEED, **zero VETO / zero REJECT**. The
consensus is NOT blocked; the amender may run. All must-fixes across the
three papers were accepted and merged below; the round verdict is
**ADJUST_PROCEED → PROCEED** (design-coherent once binding adjustments
A1–A13 are applied to the plan file). Per PLAN-134 W1: this certifies
internal coherence across forced perspectives — shipping authority remains
with the verification cascade (V2 Codex pair-rail + V3 Owner GPG), and
execution remains gated on the stub's own preconditions (Wave E shipped
**merged + positive-control fixtures green**, not merely authored/staged;
ADR-160 accepted; SENT-F signed).

## Anonymization map note (DEBATE-SCHEMA §13.2)

Synthesis consumed the three position papers as anonymized critiques.
Audit record of the label ↔ archetype mapping used at synthesis time
(recorded here in lieu of a separate `anonymization-map.md` — this file is
the single round-1 synthesis artifact):

| Label | Archetype file |
|---|---|
| Critic-A | security-engineer.md |
| Critic-B | qa-architect.md |
| Critic-C | finops-dx.md |

## Consensus findings (2+ critics flagged)

1. **C1 — The stub cites a dead ADR number** (3/3: R-SEC-10b, QA must-fix 8,
   R-FX-08). Severity HIGH for paper-trail integrity, trivial to fix: the
   plan gates execution on "ADR-174" (stub lines 30–31, 85) but the reserved
   learning-loop ADR is **ADR-160** (S261 index correction). Must be fixed
   before any ceremony/sentinel text inherits the wrong number. → A1.
2. **C2 — "Metadata-only" is prose, not a mechanism** (3/3: R-SEC-01,
   R-QA-04, Critic-C unseen #2). The rail it extends is safe because its
   schema is CLOSED (`tool_lifecycle.py` MF-SEC-1/MF-SEC-3); the plan never
   freezes that property, and the HMAC chain makes any capture-time leak
   permanent — "redact at read" is the wrong end. Agreed mitigation:
   deny-by-default field allowlist enforced at CAPTURE + three CI assertions
   (frozen schema-hash fixture, closed-type emitter gate, canary-exfiltration
   grep with kill-switch zero-delta negative control). → A2.
3. **C3 — The distiller is under-specified on every axis** (3/3: R-SEC-02 +
   R-SEC-05, R-QA-02, R-FX-02 + R-FX-03). Read surface unnamed (v1 must be
   the injection-inert closed-enum rail + closed vocabularies ONLY); the
   promotion boundary must be fail-CLOSED per C4/`_e3` (the scanner in
   `lessons.py:174-177` is advisory fail-open today); no hermetic-CI story
   (`--from-fixture` recorded-output mode, CI never calls a live model); no
   economics (cadence, delta cursor, per-run token ceiling, explicit
   haiku-tier pin — NOT the stub `model_routing.py` — and `/agent-budget`
   visibility). Reconciliation note: Critic-C's audit-log cursor and
   Critic-A's narrowed read surface are compatible — the cursor walks the
   rail's event stream; only closed-enum fields are consumed in v1. → A4.
4. **C4 — Boot-channel hardening has named edges, and the OLD spawn path is
   in scope whether the plan says so or not** (3/3: R-SEC-03/04, R-QA-09,
   R-FX-05). Fence-escape via backticks/newlines; cap must apply before
   fencing (multi-byte boundaries tested); the cap must reconcile with the
   pre-existing bounds (`ceo-boot.md:69` 200-char scan pipeline,
   `lessons.py:105` schema cap) instead of new truncation code; lesson text
   joins `/ceo-boot --json` DENIED fields; and `format_for_injection`
   (`lessons.py:632-637`) already injects UNFENCED imperatives into every
   ranked spawn at an 8× larger cap (`lessons.py:86`) — retrofit it in the
   same SENT-F edit. → A5, A7.
5. **C5 — The deny-once ADVISORY→enforce flip is itself a governance
   surface** (3/3: R-SEC-06, R-QA-05, R-FX-09). The flip must be a governed,
   audited event with pre-registered numeric criteria (FP threshold + minimum
   events + minimum shadow days, fixed at Wave 0); deny-once state binds to
   exact command hash, session-scoped; release-side verification failure =
   BLOCK (fail-open only on audit-emit); verification runs only on the rare
   already-matched path; the deny message states the citation format that
   unlocks retry. → A8.
6. **C6 — The E↔F allowlist marker is an interface dependency AND an abuse
   primitive** (3/3: R-SEC-09, R-QA-06, Critic-C unseen #3). An in-file
   marker string is a self-exemption bypass — the allowlist must live
   GATE-SIDE (canonical-guarded path list); the LANDED Wave-E marker/fixture
   API must be pinned before item 1 is authored (Wave E is staged tonight,
   not on main); fixtures extend to three directions (marked no-op passes /
   unmarked shim reds / marked-but-blocking hook still liveness-tracked,
   plus copied-marker-still-reddens); and liveness must not standing-yellow
   a rail that is off by recorded operator choice. → A11.
7. **C7 — The kill-switch is a word, not a design** (3/3: R-SEC-08, R-FX-04,
   R-QA-07 env facet). Named opt-in ENABLE flag with unset=off polarity
   (`cost_envelope.py` posture), `CEO_SOTA_DISABLE=1` master precedence,
   observe and enforce surfaces on SEPARATE switches (disabling telemetry
   never touches the deny-once gate), disabled-this-session audit breadcrumb
   for Wave-E liveness, and S218-class registration (`env-inventory.json` +
   CHEAT-SHEET table + autouse reset fixture, same commit). → A12.
8. **C8 — Dampening needs a tested classifier and a DX contract, with
   channels enumerated** (3/3: R-QA-03, R-FX-06, R-SEC-11). Dampening keys
   on a schema decision field, never a text heuristic; property test:
   block reason byte-identical at N=1 vs N=100; condensed advisories always
   retain {advisory ID, ordinal, pointer-to-full-text}; counters
   session-scoped in the per-session 0600 file, off the audit hot path;
   ADR-160 enumerates the dampenable channel as human-facing prose only —
   structured events, audit emissions, `additionalContext`, and all block
   reasons exempt by name. → A10.
9. **C9 — TTL semantics have silent fail-open edges and a nondeterministic
   substrate** (2/3: R-SEC-07, R-QA-01 + R-QA-10). Expiry must be terminal
   EXPIRED (+audit event); the 7d boot warning is count-only (no candidate
   text — otherwise pre-approval text reaches boot through the warning side
   door); `created_at` verified against the chain, not the `$HOME` file;
   every time function (decay, TTL, warning, dampening windows) takes an
   injectable `now_fn` — `_recency_decay` (`lessons.py:353`) refactored
   under the same SENT-F; TTL/`prune-lessons.py` interaction fixed. → A9.
10. **C10 — SENT-F scope is under-enumerated and new surfaces risk shipping
    CI-dark** (2/3 scope: R-SEC-10a + R-QA-07; 3/3 on same-commit env/CI
    wiring). The guarded lesson family is wider than the stub's scope line
    (`prune-lessons.py`, `lesson-restore.py`, `lesson_ranker.py`,
    `check_confidence_gate.py` interaction per `check_canonical_edit.py:127-132`);
    S258 `touched − SIGNED SCOPE = ∅` assert per commit; test-placement
    decision (guarded `_lib/tests/` vs unguarded `hooks/tests/`) and
    validate.yml path wiring resolved at this plan's Wave 0. → A13.

## Single-critic insights kept (all accepted)

- **Critic-A: hash-pinned approvals as THE integrity anchor** (R-SEC-04 +
  unseen #1). The lesson store lives under `$HOME`, outside every repo
  guard; approval is a TOCTOU into `/ceo-boot` unless the HMAC chain carries
  `sha256(trigger + advisory_text)` and both render paths verify-before-render.
  Elevated to a named design principle in ADR-160. → A6.
- **Critic-A: injection-inertness as a design lever** (unseen #3): metadata-only
  is the injection control, not just the privacy floor — name it in ADR-160
  so future rail-widening proposals must account for losing both properties.
  → folded into A2/A4 ADR text.
- **Critic-B: injectable clock seam as a blanket rule** (R-QA-01) — the house
  pattern already exists in the rail being extended (MF-QA-B). → A9.
- **Critic-B: per-item positive-control map** (Wave-E doctrine table:
  item → planted violation → expected RED) — adopted as the fixtures README
  shape. → A18.
- **Critic-C: zero-new-registration invariant** (R-FX-01): no new
  PostToolUse/PreToolUse registrations; extension rides
  `record_pre`/`record_post` in-place (MF-PERF-1/MF-SEC-5) and joins the
  hook-latency profiler corpus under the existing p95<120ms/p99<160ms CI
  gate. → A3.
- **Critic-C: the dominant cost is the rent, not the distiller** (unseen #1):
  boot + spawn injection is the recurring cost center; TTL+decay is also the
  economic garbage collector; future cap/count raises are FinOps changes.
  → plan prose under A5/A7.
- **Critic-C: score legibility** (R-FX-07): three stacked scoring mechanisms
  need per-component display in `/lesson-review`; fix the `exp(-days/90)`
  "90-day half-life" docstring bug (actual half-life ≈62d) in the same
  SENT-F. → A14 (advisory).

## Single-critic insights rejected / deferred

- **None rejected.** Zero cross-critic contradictions found; the one apparent
  tension (Critic-A's narrowed distiller read surface vs Critic-C's audit-log
  delta cursor) is reconciled in C3 — cursor mechanics over the rail's event
  stream, closed-enum fields only.
- Nothing deferred to a future plan. A14–A19 are accepted as ADVISORY
  (non-blocking for `draft → reviewed`; expected to land during execution or
  be consciously waived in the wave record).

## ADJUSTMENT INDEX (merged, deduped)

Binding = the amender applies it to `PLAN-154-gated-learning-loop.md` (and it
flows into ADR-160/SENT-F text) before `status: reviewed`. Advisory = recorded
here, non-blocking.

| ID | Adjustment (condensed) | Sources | Force |
|---|---|---|---|
| A1 | s/ADR-174/ADR-160/ everywhere in the stub (gate list + "How to continue") | R-SEC-10b, R-QA-MF8, R-FX-08 | BINDING |
| A2 | Metadata defined normatively: capture-time deny-by-default closed field allowlist (enums/bools/bounded IDs/hashes; no free-text without ADR amendment); three CI assertions: frozen schema-hash fixture, closed-type emitter gate, canary-exfiltration grep + kill-switch zero-filesystem-delta; "redact at read" rejected as posture | R-SEC-01, R-QA-04 | BINDING |
| A3 | Observe rail: ZERO new hook registrations — rides `record_pre`/`record_post` in-place per MF-PERF-1/MF-SEC-5; extended path joins hook-latency profiler corpus under the p95/p99 CI gate | R-FX-01 | BINDING |
| A4 | Distiller contract: v1 read surface = metadata rail + closed vocabularies ONLY (widening = its own reviewed change); promotion boundary fail-CLOSED (scanner unavailable/hit → QUARANTINED terminal + fixture); hermetic `--from-fixture` mode, CI never calls a live model, fail-CLOSED output schema, hostile-rejected + benign-survives fixtures; cadence Owner-invoked or nightly-hygiene piggyback (never per-session), persisted delta cursor, hard per-run input-token ceiling, model pinned explicitly haiku-tier (not stub `model_routing.py`), token usage emitted for `/agent-budget` + pricing row same commit | R-SEC-02, R-SEC-05, R-QA-02, R-FX-02, R-FX-03 | BINDING |
| A5 | Boot channel: bounded vocabulary excludes backticks/newlines; cap-then-fence ordering with cap±1 multi-byte boundary tests; route through fail-CLOSED `_lib.guardrail_validator` (not the advisory path); cap formalized as ≤3 × ≤200 chars via the EXISTING ceo-boot bound+scan pipeline; lesson text added to `/ceo-boot --json` DENIED fields; fence-escape/directive-payload positive-control fixture | R-SEC-03, R-QA-09, R-FX-05 | BINDING |
| A6 | Integrity anchor: approval events in the HMAC chain carry `sha256(trigger+advisory_text)`; `/ceo-boot` + spawn path verify-before-render, mismatch → drop + integrity flag; named design principle in ADR-160 | R-SEC-04 | BINDING |
| A7 | Retrofit the existing spawn path in the same SENT-F: `format_for_injection` re-rendered fenced/data-not-imperative; plan states the decay/review/dampening lifecycle governs BOTH consumers (boot one-liners AND the 2K-token `top_k` spawn injection) or shrinks the spawn cap to match | R-SEC-03b, R-FX-05 | BINDING |
| A8 | Deny-once gate: governed + audited ADVISORY→enforce flip (settings-backed, sentinel-scoped, HMAC governance event); pre-registered numeric flip criteria (FP < X% over ≥N events + ≥M shadow days, fixed at Wave 0); state = `sha256(normalized command)`, session-scoped, exact-match release only; release-side verification failure = BLOCK (C4/`_e3`), fail-open only on audit-emit; fixtures: transcript-read-failure → BLOCK, fabricated-citation → BLOCK; verification only on the rare already-matched path; deny message states the citation format that unlocks retry | R-SEC-06, R-QA-05, R-FX-09 | BINDING |
| A9 | TTL/decay determinism: expiry → terminal EXPIRED + audit event; 7d boot warning count-only (zero candidate text); `created_at` verified against the chain's `lesson_write` event; ALL time functions take injectable `now_fn` with wall clock only as default; `_recency_decay` refactored under the same SENT-F; golden-value boundary + monotonicity + twice-run-identical tests | R-SEC-07, R-QA-01 | BINDING |
| A10 | Dampening contract: keyed on schema decision field (deny/block vs advisory), never text heuristics; block reason byte-identical N=1 vs N=100 as a CI positive control; condensed advisory always retains {ID, ordinal, pointer-to-full-text}; counters session-scoped in per-session 0600 file, ≤1 condensation audit event per advisory ID per session; ADR-160 enumerates dampenable channel = human-facing prose ONLY (structured events, audit emissions, `additionalContext`, block reasons exempt by name) | R-QA-03, R-FX-06, R-SEC-11 | BINDING |
| A11 | E↔F marker: hard precondition — pin the LANDED Wave-E marker syntax + positive-control fixture API before item 1 is authored; allowlist lives GATE-SIDE (canonical-guarded path list; in-file marker insufficient); fixtures in three directions (marked no-op passes / unmarked shim reds / marked-but-blocking hook still liveness-tracked) + copied-marker-still-reddens; liveness suppressed for rails off by recorded operator choice (no standing-yellow fatigue) | R-SEC-09, R-QA-06, R-FX-U3 | BINDING |
| A12 | Kill-switch story: named opt-in ENABLE flag (suggest `CEO_LEARNING_OBSERVE=1`; unset = structurally off, `cost_envelope.py` posture); `CEO_SOTA_DISABLE=1` master precedence documented; observe and enforce on SEPARATE switches (observe-off never touches the deny-once gate); disabled-this-session audit breadcrumb wired to Wave-E liveness; every new env registered in `env-inventory.json` + CHEAT-SHEET env table + autouse reset fixture in the consuming commit | R-FX-04, R-SEC-08, R-QA-07 | BINDING |
| A13 | SENT-F scope + CI wiring: sentinel pre-enumerates the full guarded lesson family (`lessons.py`, `prune-lessons.py`, `lesson-restore.py`, `lesson_ranker.py`, `check_confidence_gate.py` interaction) + all new `.claude/hooks/**` paths; S258 `touched − SIGNED SCOPE = ∅` assert on every SENT-F commit; test-placement decision (guarded `_lib/tests/` vs `hooks/tests/`) and validate.yml test-path wiring resolved at Wave 0, same-commit rule in success criteria | R-SEC-10a, R-QA-07 | BINDING |
| A14 | `/lesson-review` prints score COMPONENTS (relevance, hit-rate, confidence, decay age); fix the `exp(-days/90)` "90-day half-life" docstring (≈62d) under the same SENT-F | R-FX-07 | advisory |
| A15 | `/lesson-evolve`: seeded-store e2e fixture through `skill-patch-propose/apply` shadow mode (both soak branches via the existing injectable-age seam); twice-run determinism assert; clustering deterministic v1 (Jaccard over `scope_tags`, $0) | R-QA-08, R-FX-09 | advisory |
| A16 | TTL vs `prune-lessons.py` interaction fixture: warning fires once (idempotent), expired pending cannot be approved, both mechanisms agree on clock + field | R-QA-10 | advisory |
| A17 | Boot-cache staleness: fold lessons-dir mtime into the `/ceo-boot --cached` key or document the ≤1h staleness as accepted | R-FX (nice-to-have 2) | advisory |
| A18 | Item 4 ships default-OFF behind the A12 switch family for one dogfood session before default-on; `PLAN-154/fixtures/` README maps item → planted violation → expected RED (survives the 2-session budget); per-event byte ceiling named for the widened rail event | R-QA (adv 4/5), R-FX (adv 4) | advisory |
| A19 | `/lesson-review` imperative-detector reuses the existing `scan-injection.py` corpus families (one corpus, two consumers); quarantined/expired lesson files pruned on schedule by `prune-lessons.py` | R-SEC (adv 3/4) | advisory |

## Binding vs advisory (explicit)

- **BINDING on the plan text (amender applies before `status: reviewed`):**
  A1, A2, A3, A4, A5, A6, A7, A8, A9, A10, A11, A12, A13.
- **Advisory (recorded, non-blocking; execute-or-waive during waves):**
  A14, A15, A16, A17, A18, A19.

## What all three critics endorsed unchanged (do not touch)

- The six binding constraints as a package — especially constraint 3's
  "the human filters for usefulness, the machine for injection" (keep
  verbatim in ADR-160).
- Zero self-activation + PENDING → `/lesson-review` + SP-NNN/soak; the
  success criterion "zero writes outside pending stores without an approval
  event in the HMAC chain" is the assertable oracle (extend it with A6's
  hash verification, same fixture family).
- Extending the PLAN-125 WS-1 `tool_lifecycle.py` rail rather than any new
  observe surface.
- Advisory-only dampening with blocking reasons untouchable.
- The stub's execution gate ordering: Wave E ships (merged + fixtures
  green) → debate → ADR-160 → SENT-F → code.

## Round verdict

**PROCEED** — apply A1–A13 to the plan file, then `status: draft → reviewed`.
No round 2 needed: zero cross-critic contradictions; every must-fix is
additive; the one surface-level tension (C3 read-surface vs cursor) is
reconciled above. Execution start remains gated on the stub's preconditions
(Wave E merged with positive-control fixtures green, ADR-160 drafted and
accepted carrying A2/A4/A6/A8/A10/A11 normative text, SENT-F signed with the
A13 scope).
