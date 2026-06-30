---
status: PROPOSED
---

<!-- NUMBER-COLLISION RISK (PLAN-135 W4 unit d2, authored on branch plan-135-exec):
     ADR-150 is the highest ADR on disk at authoring time (2026-06-12). The
     PARALLEL PLAN-134 terminal holds a deferred, un-numbered routing ADR
     (PLAN-134-mission-completion-sota-arc.md "ROUTING ADR DIRECTION",
     Owner-confirmed S229) that is expected to take ADR-151. This file
     therefore takes ADR-152 and leaves ADR-153 as headroom. AT CEREMONY
     TIME: re-grep `.claude/adr/` for the highest allocated number BEFORE
     applying; if 152 is taken, allocate a fresh ID per the ADR-117
     collision policy (never reuse, never <base>a- except for amendments)
     and update this header + the d2 manifest. S229/S230 two-live-terminal
     precedent makes this risk real, not theoretical. -->

# ADR-152: CLAUDE.md decomposition — `@imports` vs `.claude/rules/` + `paths:` (D1-measurement-gated)

**Status:** PROPOSED — decision FRAMEWORK complete; the decision itself is
NOT taken. Status flips to ACCEPTED only per §Decision gate below (all
`MEASURED:<tbd>` slots filled from D1's PROBE-LOG.md and the §Decision rule
evaluated). Acceptance does NOT authorize execution — execution is its own
follow-up Owner ceremony (PLAN-135 W4 d2 plan text; §0 Gate-1 blast radius).
**Date:** 2026-06-12 (PLAN-135 W4 unit d2; harvest item D2)
**Enforcement commit:** n/a (documentation-only at acceptance; the follow-up
execution ceremony commit will be recorded here as an addendum when it lands)
**Decision drivers:**
- CLAUDE.md is 39,461 B against the 40,000 B CI cap (`validate-governance.sh:603`,
  `CLAUDE_MD_SIZE_LIMIT`; also `generate-ceremony.sh` post-size FAIL) — 539 B
  (~1.3%) headroom. S230 went CI-red on exactly this cap after a routine S229
  closeout and forced an emergency compaction.
- The volatile tail (§6 Current Work → EOF, i.e. §6-archived clusters +
  §CHANGELOG) is 28,231 B = **72% of the file** (~7,060 tokens est.) and is
  the ONLY part edited at every closeout; the stable doctrine head is ~28%.
- The §0 Gate-1 no-edit rule's cost premise (any mid-session edit
  invalidates the prompt cache; 5-min TTL) is under active falsification by
  D1 (PLAN-135 W4 d1) — this ADR must not bake in either premise before
  D1's numbers exist.
- Harvest D2 verdict: GAP · medium · "framework + every adopter with a fat
  CLAUDE.md"; harvest mandates picking ONE option after `/context`
  measurement and mirroring the choice into `templates/CLAUDE.md`.

## Context

`CLAUDE.md` is the Gate-1 master context: read at every session boot,
declared cache-stable, and guarded by the §0 cache-discipline rule
(closeout-ceremony-only edits). Three pressures now act on the monolith:

1. **Byte cap.** The 40,000 B governance cap leaves ~539 B of headroom.
   Every closeout grows the CHANGELOG; compaction ceremonies (S230's
   S159-S174 super-rollup is the latest) are recurring manual toil whose
   trigger is a CI red, not a plan.
2. **Blast radius of the §0 discipline.** Because the volatile tail lives
   in the same file as the stable doctrine head, a 1-line CHANGELOG entry
   carries the same Gate-1/canonical-ceremony weight as a doctrine change.
   72% of the file's bytes churn; ~28% are the actual rules.
3. **Falsified-or-not cost premise.** `docs/opus-4-7-operations.md` §2
   claims 5-min TTL and full-cache invalidation on any Gate-1 edit; the
   harvest (D1) asserts 1h subscription TTL and prefix preservation on
   mid-session CLAUDE.md edits. D1 built the measurement protocol
   (research/D1-CACHE-MEASUREMENT-PROTOCOL.md, sessions S-A..S-F, verdicts
   PRESERVED/PARTIAL/INVALIDATED → doctrine Variant A/B). Measurement is
   PENDING-LIVE. Two conflicting folklore boot numbers (~27,300 ops-doc vs
   ~44,786 CLAUDE.md §0) get re-baselined by D1 S-F.

The harness offers two decomposition mechanisms (harvest D2 mechanics):

- **`@imports`** — `@.claude/context/changelog.md` style inline imports
  resolved into context at session start. Content still loads every
  session; the FILE boundary moves.
- **`.claude/rules/*.md` with `paths:` frontmatter** — rule files loaded
  conditionally, only when the session touches matching paths (e.g. hooks
  conventions load only when `.claude/hooks/**` is touched). Content does
  NOT load in sessions that never match.

PLAN-135 W4 d2 deliverable is this measured ADR — a decision framework with
explicit measurement slots, NOT an executed decomposition.

## Decision drivers

- (see bullets in header; plus:)
- Determinism of governance context: PROTOCOL.md assumes the CEO has the
  governance rules in-context every session. Any mechanism that makes rule
  loading conditional must exclude load-bearing governance text.
- Adopter parity: whatever ships must be mirrored in `templates/CLAUDE.md`
  and survive `scripts/install.sh` / `scripts/upgrade.sh` (both canonical).
- Tooling coupling: `validate-governance.sh` CLAUDE.md size check,
  `generate-ceremony.sh` post-size gate, and any hook/script that greps
  CLAUDE.md must keep working against the decomposed layout.

## Options considered

### Option A: `@imports` — volatile-tail extraction

Move the volatile tail (§6-archived clusters + §CHANGELOG; optionally §6
Current Work) to `@.claude/context/changelog.md`; CLAUDE.md keeps the
stable doctrine head plus one import line. Closeout then touches ONLY the
imported file.

**Pros:**
- Defuses the 40,000 B cap structurally and permanently: the capped file
  drops to ~11,2 kB and stops growing; compaction ceremonies stop being
  CI-emergency-driven (the context file can rotate/archive on its own
  schedule).
- Closeout edits land in a non-doctrine file — the Gate-1 head becomes
  byte-stable across sessions, which is the strongest available prefix-
  stability posture under EITHER D1 variant.
- Deterministic: imported content loads every session exactly like today —
  zero change to what the CEO sees; no governance-text conditionality.
- Cheapest template mirror (one import line + one new file).

**Cons:**
- ZERO fixed-context shrink: imports are inlined at boot, so every session
  still pays the ~7,060-token tail (M1 unchanged).
- Cache benefit is unproven: editing the imported file changes the
  assembled prompt too. If the import sits at the prompt tail, only the
  suffix re-pays; if not, it may invalidate exactly like an in-file edit.
  This is measurement slot M4 — unknowable from doctrine.
- Adds a harness-behavior dependency (import resolution order/position) to
  the Gate-1 contract; §0 prose and GATE-1 reading list must enumerate the
  imported file.

### Option B: `.claude/rules/*.md` with `paths:` gating

Carve per-area conventions out of CLAUDE.md §5 Critical Rules (and team-doc
adjacents) into `paths:`-gated rule files: e.g. Python/hook-test
conventions load only when touching `.claude/hooks/**`, plan-naming rules
only under `.claude/plans/**`.

**Pros:**
- The ONLY option that shrinks the fixed per-session context: sessions
  that never touch a gated area never load its rules (slot M5).
- Per-area isolation additionally shrinks the §0 blast radius: editing a
  gated rule file mid-session perturbs only sessions that loaded it.
- Scales with domain growth (151 skills, domain profiles) better than a
  monolith ever can.

**Cons:**
- Nondeterministic governance context: the same session type can see
  different rule sets — weakens the "the CEO always saw rule X" audit
  assumption; load-bearing governance (spawn protocol, canonical-edit
  discipline, Gate ordering) is INELIGIBLE for gating, so only a subset of
  CLAUDE.md (mostly §5 conventions) qualifies. The volatile tail —
  the actual byte-cap driver — is NOT rules-shaped and does not fit this
  mechanism (the CHANGELOG can't be `paths:`-gated meaningfully).
- Does NOT defuse the byte cap by itself (the tail stays in CLAUDE.md).
- Heavier template/adopter mirror (a rules directory + frontmatter
  semantics that adopters must understand); `paths:` matching semantics
  are harness-version-dependent and need a smoke test in
  `smoke-install-parity.sh`.

### Option C: status quo (null option)

Keep the monolith; manage the cap by scheduled compaction (super-rollups).

**Pros:** zero migration risk; zero new harness dependencies; current
practice demonstrably works (S230 compaction took one session).
**Cons:** recurring manual toil with a CI-red failure mode; 72% volatile
byte share keeps the Gate-1 discipline's blast radius maximal; headroom is
~539 B so the NEXT normal closeout likely goes red again.

## Decision

**NOT YET TAKEN.** The decision is produced by the rule below the moment
the measurement slots are filled from D1's PROBE-LOG.md. The chosen option
will be recorded here, in place, with the numbers.

### Measurement slots (source: D1 campaign, PLAN-135/research/D1-CACHE-MEASUREMENT-PROTOCOL.md)

| Slot | Definition | Source | Value |
|------|------------|--------|-------|
| M1 | Gate-boot tokens, live re-baseline (replaces the ~27,300 / ~44,786 folklore pair) | D1 S-F (`/context`, live read-only) | MEASURED:<tbd> |
| M2 | Mid-session CLAUDE.md-edit cache verdict ∈ {PRESERVED, PARTIAL, INVALIDATED} | D1 S-B (cache_read(T_p) vs cache_read(T3) rule) | MEASURED:<tbd> |
| M3 | If M2=PARTIAL: re-pay tokens = cache_creation(T_p) − baseline | D1 S-B | MEASURED:<tbd> |
| M4 | Tail-import-edit cache verdict: same S-B probe shape but the edit targets an `@import`-ed tail file (1 extra rep; extension of S-B — add to PROBE-LOG before the campaign runs) | D1 S-B extension | MEASURED:<tbd> |
| M5 | Option-B conditional-load saving: tokens of `paths:`-eligible rule text NOT loaded in a representative non-matching session | post-carve `/context` delta (estimable statically from §5 byte share before the campaign) | MEASURED:<tbd> |

Static facts (measured at authoring, 2026-06-12, NOT slots): CLAUDE.md
39,461 B / cap 40,000 B (headroom 539 B); volatile tail §6→EOF 28,231 B =
72% (~7,060 tok est.; CHANGELOG alone 24,079 B); `templates/CLAUDE.md`
4,504 B (no cap pressure on the adopter side yet).

### Decision rule (D1-gated; materiality threshold = 10% of M1, matching D1's own cost-immateriality bar)

- **R1 — M2 = INVALIDATED (D1 doctrine Variant A; cost premise TRUE).**
  The §0 rule survives; cache cost is real. Choose **Option A** iff M4
  shows the tail-import edit is PRESERVED or re-pays < 10% of M1 (suffix-
  only re-pay) — Option A then converts every closeout from "invalidate
  the gate-boot" to "cost-immaterial tail re-pay" AND defuses the byte
  cap. If M4 is also INVALIDATED end-to-end, Option A still wins on the
  byte cap + closeout ergonomics alone, but §0 cost language is RETAINED
  and closeout stays ceremony-end-only. Option B is taken INSTEAD only if
  M5 ≥ 10% of M1 (rare under Variant A: the eligible §5 subset is small).
- **R2 — M2 = PRESERVED, or PARTIAL with M3 < 10% of M1 (Variant B; cost
  premise FALSE/immaterial).** Cache protection is no longer a driver;
  decide on fixed-context shrink vs byte cap. Choose **Option B** iff
  M5 ≥ 10% of M1 AND the gated subset contains zero load-bearing
  governance text (reviewer-checkable list in the execution plan);
  otherwise choose **Option A** purely for the structural byte-cap defuse
  + closeout isolation. If, with numbers in hand, A's gains are judged
  not worth a Gate-1 migration ceremony, record **Option C** and close
  this ADR as the honest null (the cap then needs a standing compaction
  routine instead — e.g. a nightly-hygiene staleness line).
- **R3 — pick ONE.** Hybrid (A+B together) is explicitly OUT at this
  decision point per harvest D2 ("Escolher UM após medir"); revisiting a
  hybrid requires a fresh ADR with the first option's post-execution
  numbers as its baseline.
- **Mirror clause (applies to A and B).** The chosen mechanism ships to
  `templates/CLAUDE.md` in the SAME execution ceremony, with
  `smoke-install-parity.sh` extended to assert the decomposed layout
  installs cleanly (S228 E8-gate precedent).

## Decision gate (status-flip rule — explicit)

This ADR remains **PROPOSED** until ALL of:

1. Every `MEASURED:<tbd>` slot above is replaced with a value from D1's
   filled PROBE-LOG.md (scratch-worktree campaign S-A..S-F + the M4
   extension rep);
2. The §Decision rule is evaluated against those values and the resulting
   option (A, B, or C) is written into §Decision with the numbers inline;
3. The companion D1 doctrine fix (research/D1-PROPOSED-DOC-FIX.md →
   `docs/opus-4-7-operations.md` §2 Variant A or B) has landed or lands in
   the same promotion, so this ADR and §2 never assert different premises.

Only then: PROPOSED → ACCEPTED. **ACCEPTED still does NOT execute the
decomposition.** Execution (moving CLAUDE.md content, §0/GATE-1 prose swap,
templates mirror, tooling updates) is a separate follow-up **Owner
ceremony** — CLAUDE.md is Gate-1 (closeout-ceremony-only edit per §0) and
`templates/`-adjacent install scripts are canonical-guarded. If D1's
campaign is abandoned, the terminal state is RETRACTED, not silent decay.

## Consequences

- (+) The decision cannot be taken on folklore: both the 5-min-TTL premise
  and its falsification are excluded until measured (the exact failure
  mode D1 exists to kill).
- (+) Whatever lands, the 40,000 B cap stops being an ambush: Option A
  removes it structurally; Options B/C force an explicit standing
  mitigation into the record.
- (+) Adopters inherit a measured pattern via the templates mirror, not a
  meta-repo idiosyncrasy.
- (−) The byte-cap exposure persists until the follow-up ceremony executes
  — at 539 B headroom the next closeout may red CI again; interim
  mitigation stays manual compaction.
- (−) Two-ceremony latency (accept, then execute) on a change whose Option-A
  form is mechanically trivial; accepted deliberately because the §0 blast
  radius is the whole reason this is an ADR.
- (~) M4/M5 add one rep + one static estimate to the D1 campaign scope;
  scope-cut already flagged in the d1 manifest open items.

## Blast radius

**L3+.** Touches the Gate-1 contract itself: `CLAUDE.md` (§0 discipline +
GATE-1 reading list + physical layout), `templates/CLAUDE.md`,
`docs/opus-4-7-operations.md` §2 cascade (cost-of-operation.md,
opus-4-7-baseline.md per D1's ledger), `validate-governance.sh` CLAUDE.md
size-check semantics, `generate-ceremony.sh` post-size gate,
`smoke-install-parity.sh`, `scripts/install.sh`/`upgrade.sh` parity, and —
via the templates mirror — every adopter repo with a fat CLAUDE.md. Hence:
debate-eligible, Codex pair-rail on the execution plan, Owner GPG ceremony
for execution.
