---
plan: PLAN-153
round: 1
archetype: vp-engineering
skill: architecture-decisions
verdict: ADJUST_PROCEED
created_at: 2026-07-03
---

## Verdict

ADJUST_PROCEED — the thesis, the restraint ("NO to ~100"), and the
governance ethos are architecturally sound, but the plan's wave
L-classifications and Wave-0 ceremony allocations are materially
inconsistent with this framework's own canonical-guard surface. As
written, Waves B/C/D/F would hit `CANONICAL-EDIT-BLOCKED` at execution.
These are fixable in the plan file; none require a redesign. Fix the
five must-fix items and this moves to `reviewed`.

## Summary (≤ 3 bullets)

- **What it does:** close the 5 CONFIRMED / 6 PARTIAL verified ecc gaps
  (installer lifecycle, skill format+telemetry, 6 catalog lacunae, static
  harness-config gate, gated learning loop) via clean-room stdlib ports,
  MIT-attributed, human-gated — without importing ecc's weaknesses.
- **Strong:** class-not-implementation discipline; human-gated learning
  red line; the "NO to ~100 skills" triage; C-before-D *intent*; docs-first.
- **Weak:** the plan costs work in tokens/sessions but the real cost is
  **ceremony + wall-clock soak**. It labels canonical-guard-touching waves
  "L2, proceed directly," under-allocates sentinels, misstates one guard's
  status, and rests the load-bearing C→D gate on telemetry that structurally
  cannot measure the domains D adds.

## Risks

- **R-VP1 — Wave L-level ↔ canonical-guard surface mismatch**
  Severity: **CRITICAL**
  Description: Waves B/C/D/G edit or create canonical-guarded files —
  `scripts/install.sh` (`check_canonical_edit.py:187`), `scripts/upgrade.sh`
  (`:189`), `.github/workflows/release.yml` (`:182` glob), all `SKILL.md`
  (`:118-122`), `lessons.py` (`:129`) — yet are classed **L2 "proceed
  directly to execution"** with **no** sentinel/SP ceremony allocated. Wave 0
  mints only SENT-E and SENT-F. At execution these edits are blocked by the
  canonical guard.
  Mitigation: re-derive each wave's L-level from the guard surface it
  touches (B/C/D/G are L3 by the framework's own blast-radius rule) and
  allocate every ceremony in Wave 0 (see Must-fix 1-3).

- **R-VP2 — 7-day SKILL.md soak is wall-clock, not token budget**
  Severity: **CRITICAL**
  Description: Wave G's ~25 merges into existing `SKILL.md` go through the
  ADR-031 shadow→**7-day soak**→promote flow (`skill-patch-apply.py:664`,
  `_SEVEN_DAYS_SECS`). Wave C restructures 2 skills and adds `version:` to
  all 151 — all canonical `SKILL.md` edits. The soak is calendar time; the
  plan's "5 sessions" budget measures only tokens. You cannot clear a 7-day
  gate for 25+ skills in 5 sessions unless the Owner pre-authorizes
  `skip_soak` (`--force-recover`, §D1) per skill or all shadows are started
  in parallel up front. The plan is silent on both.
  Mitigation: decide the soak posture in Wave 0 and separate the wall-clock
  schedule from the token budget explicitly.

- **R-VP3 — C→D gate produces non-decision-relevant telemetry**
  Severity: **HIGH**
  Description: `/skill-health` derives usage from *this* repo's dogfood HMAC
  audit log. A framework repo never exercises `network-ops`, `healthcare`,
  `jvm`, `angular`, `pytorch` skills — so the telemetry shows ~zero for
  exactly the domains Wave D adds. The gate the plan calls "load-bearing,
  not optional" cannot inform the D decision it gates. The ordering is real;
  the *signal* is theater for greenfield domains.
  Mitigation: redefine what `/skill-health` authorizes about D — measure
  discovery-failure / mis-selection on the **existing** 151, plus a
  "plausible consumer repo exists" test per new domain — not raw usage.

- **R-VP4 — Budget optimism (~35% under)**
  Severity: **HIGH**
  Description: Bottom-up, Wave D alone (32 ADOPT; several upstreams are
  600-900L — `cpp-coding-standards` 724L, `windows-desktop-e2e` 888L,
  `motion-advanced` 596L — each a clean-room stdlib rewrite + line-by-line
  injection review + lint + counts) is ≈1.3M tokens. G ≈0.5M; the two L3
  waves ≈0.3M each; plus debate rounds, per-wave pair-rail, and CI-retry
  overhead → ~3M, over the 2.2M ceiling. The 1.4-2.2M range (57% spread) is
  itself a signal the estimate was not decomposed.
  Mitigation: bottom-up estimate per wave; split or per-batch-timebox D with
  defer-pointers; re-budget to ~3M / 7-9 sessions.

- **R-VP5 — Wave F is 3-4 plans in a trenchcoat and dampens security guards**
  Severity: **HIGH**
  Description: F bundles an observe-rail (new data surface), a cheap-model
  distiller, confidence/decay in `lessons.py`, ceo-boot injection,
  **denial-dampening across canonical-edit/bash-safety/spawn guards**, a
  fact-forcing ADVISORY→enforce flip, and `/lesson-evolve`. Item 5 makes a
  *blocking security guard get quieter under repeated blocks* — an attacker
  probing bash-safety sees the guard go silent. That is an anti-pattern for a
  security surface, and it is buried in the most governance-sensitive wave.
  Mitigation: split F into its own plan (PLAN-154); redesign dampening to
  condense **advisory** output only — a blocking guard's block reason must
  never lose legibility, regardless of repeat count.

- **R-VP6 — E's harness-config gate self-collides with F's opt-in hooks**
  Severity: **MEDIUM**
  Description: `check-harness-config.py` (E) flags "fail-open shims." F's
  opt-in observe hook is a no-op when `CEO_OBSERVE` is unset — structurally
  indistinguishable from a fail-open shim. F will red the gate E built.
  Mitigation: design an explicit annotation/allowlist for intentional opt-in
  no-op hooks while building E, with a fixture proving both directions.

- **R-VP7 — Wave E scope creep under a single ADR**
  Severity: **MEDIUM**
  Description: ADR-173 is titled "static harness-config gate" but Wave E also
  ships a destructive-Bash citation gate (changes bash-safety *semantics*)
  and a prompt-defense-baseline (changes the `check_agent_spawn.py` spawn
  *contract*). Those are different invariants, each ADR-worthy on its own.
  Mitigation: narrow E/ADR-173 to the harness-config gate + deny baseline
  (the actual S254 lesson); split items 4 and 6 to their own ADR or a later
  plan.

- **R-VP8 — Third-party import has no quarantine/exit path + per-file license gap**
  Severity: **MEDIUM**
  Description: ~57 imported pieces (32 ADOPT + 25 merge) are "Embedded"
  dependencies by the tool-eval rubric, which requires an exit strategy. The
  plan has pre-merge injection review (it caught 13 flags) but **no** path to
  pull a skill back out if an injection is found post-merge. Separately, the
  plan asserts MIT from ecc's *repo-level* license; several skills are
  themselves derivative (`react-performance` = "base Vercel MIT"),
  vendor-wrapped, or non-English — repo-level MIT does not clear per-file
  provenance for a PUBLIC repo.
  Mitigation: define a skill-quarantine path (disable + audit event) and
  per-FILE license verification before catalog entry.

## Must-fix (blocking)

1. **Reconcile Wave-0 sentinels with the canonical-guard list.**
   - Add **SENT-B** covering `scripts/install.sh` (`check_canonical_edit.py:187`),
     `scripts/upgrade.sh` (`:189`), `.github/workflows/release.yml` (`:182`).
     Wave B is currently "L2, no ceremony" but edits three guarded files.
   - Add `scripts/install.sh` to **SENT-E** scope: Wave E item 2 writes the
     deny baseline into `install.sh`, which is guarded, but the SENT-E scope
     list omits it (touched − scope ≠ ∅ → sentinel-scope check fails).
   - **Correct SENT-F.** The plan states "`lessons.py` is not
     canonical-guarded" — this is **false**: `lessons.py` is guarded at
     `check_canonical_edit.py:129`, and Wave F items 2-3 edit it. SENT-F must
     cover `.claude/scripts/lessons.py` or Wave F is blocked.

2. **Allocate the SKILL.md-authoring ceremony for Waves C/D/G and state the
   soak posture.** All of C (restructure 2 + `version:` on 151), D (32 new),
   and G (25 merges) live in the canonical `SKILL.md` namespace
   (`:118-122`); G's merges run the 7-day shadow soak (`skill-patch-apply.py:664`).
   Wave 0 must name the ceremony path (SP-NNN + `/skill-review`) **and** the
   soak decision (Owner `skip_soak` pre-auth vs parallel-shadow-early), or
   these waves cannot land in the stated schedule.

3. **Re-classify B/C/D/G off "L2, proceed directly."** By this framework's
   own rule (touches a canonical/sentinel/SP surface → L3), each requires
   debate + ceremony. Update the L-labels and the "How to continue" note so
   the executor does not attempt direct execution and hit the guard wall.

4. **Resolve the C→D gate rationale.** State precisely what `/skill-health`
   output authorizes about D, given single-repo dogfood telemetry cannot
   measure the new domains (R-VP3). Either re-gate D on a discovery /
   consumer-exists test, or drop the "load-bearing, not optional" framing and
   keep C→D as sequencing hygiene only.

5. **Split Wave F into its own plan and redesign denial-dampening.** F has
   near-zero coupling to A/B/C/D/G (shared provenance only), is L3, already
   needs its own SENT-F + ADR-174, and carries the security-legibility risk
   (R-VP5). Carve it to PLAN-154; ensure no blocking guard's block reason is
   ever suppressed.

## Nice-to-have (advisory)

1. Re-budget bottom-up per wave; publish the token budget and the wall-clock
   (soak) schedule as two separate numbers.
2. Prioritize the 32 ADOPTs by "has a plausible consumer repo today." The
   framework has no healthcare/manufacturing/network-ops target; several
   ADOPTs are version-pinned and will rot (`motion-*` iOS-26 APIs,
   `angular-developer` 35 versioned refs, `nuxt4-patterns`). Defer speculative
   inventory rather than build-on-spec.
3. Record the 72 un-merged ADAPTs (97 in the matrix − 25 chosen for G) as
   explicit defer-pointers — the success criterion says nothing is silently
   dropped.
4. Sequence G's `security-and-auth` and `testing-strategy` merges against the
   **post-C** `references/` layout; C restructures both skills before G
   enriches them (hidden C→G coupling on those two files).
5. Budget the CI delta on the `Ceo` runner: E adds a scheduled
   `supply-chain-watch.yml` + a per-push harness-config parse over every hook;
   B adds release/version-sync/manifest validators; C adds counts checks.
6. Front-load the Wave A skill-chooser table and Wave C `/context-budget` and
   prove the catalog is navigable at 151 **before** D grows it by 21%.

## Unseen by the original plan

1. **The plan never maps wave L-level to the canonical-guard list.** It treats
   "installer" and "skill format/version" as mechanical L2 work when the
   framework's own guards make them L3 ceremony work. This is the plan's
   central blind spot and the root of Must-fix 1-3.
2. **The 7-day soak as a schedule constraint.** Cost is measured only in
   tokens/sessions; the calendar days the soak imposes on 25+ SKILL.md
   changes are invisible in the plan.
3. **Per-file licensing.** MIT is asserted from ecc's top-level license; the
   matrix itself shows derivative/vendor-wrapped/non-English skills — a
   public-repo exposure the plan books as one line in Risks.
4. **No post-merge quarantine.** Only pre-merge injection review exists; the
   plan's own "13 flags recorded" proves residual risk is nonzero and needs a
   pull-back mechanism.
5. **E's gate flags F's opt-in no-op hooks** (self-collision, R-VP6) — the two
   L3 waves interact and neither wave's checklist anticipates it.
6. **Discovery is unproven at 151.** Wave A's chooser table and C's
   `/context-budget` are the navigability fix, yet D adds volume before either
   is shown to work — volume ahead of demonstrated discovery.

## What I would NOT change

- **"Import the CLASS, never the implementation"** stdlib rewrite discipline —
  architecturally correct; it keeps the lock-in axis of the tool-eval rubric
  green (no node runtime dependency). Keep exactly.
- **The human-gated learning red line** — nothing self-activates; PENDING →
  `/lesson-review`; instinct→skill via SP-NNN + `/skill-review` + soak. This is
  the single most important invariant in the program; preserve verbatim.
- **"NO to ~100 skills"** and the 32/97/39/109 triage — the restraint is right;
  adding volume without telemetry would worsen discovery.
- **The no-vendor-numbers rule** (never cite AgentShield "102 rules / 98%") —
  correct handling of unverified cross-repo claims.
- **The C-before-D *intent*** (measure before mass-create) — keep the ordering;
  only fix the signal (R-VP3), do not drop the sequencing.
- **Docs-first Wave A at L1** — lowest blast radius, highest adopter value;
  correct to front-load.
- **Promoting security (E) early** — even after re-classification to L3, the
  S254-lesson-value argument for running the security gates second is sound.
