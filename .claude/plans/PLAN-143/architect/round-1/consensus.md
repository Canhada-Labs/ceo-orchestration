---
plan: PLAN-143
round: 1
round_verdict: PROCEED
created_at: 2026-06-20
critics: 3
verdicts: [ADJUST, ADJUST, ADJUST]
vetoes: 0
consensus_adjustments: 7
---

# PLAN-143 — Round-1 consensus

Three critics, **all ADJUST, zero VETO/REJECT**. The design is coherent; every
finding is a framing/sequencing improvement, not a mutually-exclusive design
conflict. Folded into the plan in this round → **PROCEED** (design-coherent).
Synthesis consumed the anonymized critique text only (Critic-A/B/C); mapping in
`anonymization-map.md`.

## Consensus findings (2+ critics)

- **CF-1 — Item-1 framing is factually wrong; reframe to inventory-accuracy
  reconciliation (A+B+C).** The five named "governance kill-switches"
  (`CEO_TRUST_BYPASS`, `CEO_CANONICAL_GUARD_DISABLE`, `CEO_ALLOW_NO_VERIFY`,
  `CEO_HOOKS_DISABLE`, `CEO_SKIP_HOOKS`) have **zero live `getenv`/`environ`
  consumers** — they appear in the inventory only as forbidden-family tokens
  inside `_lib/env_persist_allowlist.py` (the deny-list whose job is to exclude
  them), and the bypass class is already governed by **ADR-143**. So item 1 is
  *reconcile inventory drift* (cross-check each of the 25 against the existing
  governed allowlists, classify, regen), NOT "review 25 unreviewed surfaces"
  and NOT a new ADR. The `env-inventory-check.py` `TOKEN_RE` is a documented
  *superset* scanner doing exactly its job.

- **CF-2 — Item-3 release-coupling needs explicit sequencing against verdict
  regeneration (A+B+C).** `audit_emit.py` is manifest line 22; editing it mutates
  the recomputed `inputs_hash`, invalidating every existing verdict — masked
  today only by `CEO_PAIR_RAIL_VERDICT_OPTIONAL=1`. Shipping item 3 as a bare
  allowlist edit *hides a fresh increment* of the coupling behind the flag
  PLAN-142 set to drain the OLD coupling; when the flag flips to `0`, the first
  release hard-fails. Item 3 MUST ship **paired with** verdict regeneration
  (recompute inputs_hash, GPG-sign, within the 24h TTL of the next tag) OR
  **wait** — split it out (D1) so the other 3 items are not held hostage.

- **CF-3 — Test ACs are vacuous; require positive survival-assertions (B+C).**
  "a test asserts … / no exception" passes even with the bug present (item 2's
  probe is inside a fail-open `try/except`). The tests must assert the *positive*
  contract: item 2 → the shim path takes the intended branch AND emits no
  AttributeError breadcrumb; item 3 → the event RETAINS `exit_code` AND no OTHER
  field newly survives (allowlist did not widen) AND the scrub drop-counter stops
  logging the forbidden-field warning.

- **CF-4 — Peel item 4 off + keep it a FLOOR (A+C).** Item 4 (INSTALL.md
  tests-floor) is non-guarded + not CI-gated (`verify-counts.sh --no-tests`) →
  ship it standalone NOW, not behind the canonical ceremony. And set a robust
  **floor** (`11000+`, live 11752 ≥ 11000) — do NOT pin the exact ~11.7k (that
  defeats the floor rule and re-breaks on normal suite churn).

## Single-critic insights — KEPT

- **SK-1 (B) — Inventory regen must preserve the deny-list disjointness
  invariant.** The regen must not enroll any override/escape-hatch name into a
  *persist allowlist* (only into the descriptive inventory census);
  `test_env_persist_allowlist.py` must still pass post-regen.
- **SK-2 (B) — Clamp/coerce `exit_code`** (bounded int, e.g. 0..255) when adding
  it to the allowlist; inline provenance comment at the edit site.
- **SK-3 (C) — Two-channel emit divergence.** The typed `emit_codex_invoke_dispatched()`
  does not accept `exit_code` while the generic `emit_generic(...)` callsite does.
  Reconcile (route through the typed emitter OR document the asymmetry).
- **SK-4 (C) — npm/ mirror scope.** Every coupled file has an `npm/.claude/`
  twin. The plan must state whether the npm mirror is in scope (apply edits to
  both, or a sync step regenerates it).
- **SK-5 (C) — verdict 24h TTL.** Verdict regen + release tag must fall in the
  same 24h window (ADR-103), else item 3's hash fix still can't ship.
- **SK-6 (A) — item-2 default locus = hasattr/getattr-guard** (smallest blast
  radius; keeps `_EmitCapture` a pure test double).
- **SK-7 (A/C) — durability/recurrence gap.** Item-1 + item-4 drift recur because
  neither is CI-gated. Name the structural gap (a periodic `--check` assertion);
  deferring the gate itself is acceptable.

## Single-critic insights — REJECTED / DEFERRED

- **D3 "kill-switch ADR" (REJECTED).** Critic-B: an ADR here would be actively
  harmful (it would imply the bypasses exist + are governed when they are not,
  and could be cited to launder override-family names). The existing inline
  governance + ADR-143 + the classification note suffice.
- **Pin INSTALL.md to exact ~11.7k (REJECTED).** Defeats the floor rule.
- **OPTIONAL→0 closure in this plan (DEFERRED, but named).** Critic-C U4: the
  plan should explicitly decide scope; folded as a §4 note that closing the
  transition is OUT of scope but item 3's verdict-regen is its prerequisite.

## Plan adjustments (applied to PLAN-143 this round) — 7

1. §1 item-1 reframed to inventory-accuracy reconciliation (CF-1).
2. §2 D2 framing corrected: BOTH loci re-touch the manifest (Critic-C R2/NH4).
3. §3 AC-1 rewritten: classify {consumed | forbidden-family-mention | descriptor};
   preserve deny-list disjointness; per-name review BEFORE regen (CF-1/SK-1/MF5).
4. §3 AC-2/AC-3 hardened with positive survival-assertions + clamp + nothing-else-leaked (CF-3/SK-2).
5. §3 AC-3 gains a hard sequencing clause: pair with verdict regen OR wait (CF-2/SK-5).
6. §3 AC-4 set to floor `11000+`, documented as floor-by-design (CF-4).
7. §4 D1/D2/D3 ratified + new D4 (item-3 sequencing) + D5 (durability gap) + npm-scope + OPTIONAL→0 scope note.

## Round verdict

**PROCEED — design-coherent.** No further round needed (no REJECT, no design
deadlock; all folds are additive). Reminder (DEBATE-SCHEMA §13): this certifies
internal design coherence ONLY — it does NOT authorize shipping. PLAN-143
execution still requires V1 (deterministic tests/gates) → V2 (Codex pair-rail,
now restored) → V3 (Owner GPG). Plan moves to `status: reviewed`.
