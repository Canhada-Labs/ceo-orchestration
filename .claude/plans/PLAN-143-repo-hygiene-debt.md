---
id: PLAN-143
title: Repo-hygiene debt — env-var inventory + audit-emit allowlists + tests-floor doc
status: done
created: 2026-06-20
reviewed_at: 2026-06-20
completed_at: 2026-06-21
related_commits:
  - 18ca476                        # item-4 tests-floor doc (INSTALL.md 12000+ -> 11000+) + docs/patches staging
  - 0236cef                        # item-2 spool_writer rotate-probe getattr guard (Group A, Owner-GPG)
  - dfdabab                        # item-3 audit_emit exit_code allowlist+clamp (Group B KERNEL, Owner-GPG)
  - 6615151                        # item-1 env-inventory census regen (data regen, Owner-GPG)
owner: CEO
depends_on: []
related_plans:
  - PLAN-142                       # surfaced audit-errors-04 (its restored callsite) at the nightly sweep
  - PLAN-140                       # same forbidden-field-drop class as audit-errors-04
related_adrs:
  - ADR-153                        # audit emit forbidden-field scrubbing (the drop mechanism)
  - ADR-136                        # nightly-hygiene confinement (this plan's provenance instrument)
  - ADR-143                        # kill-switch bypass governance (round-1 CF-1: switches already governed)
risk_tier: B                       # canonical-guarded edits (audit_emit.py); 1 item MAY touch kernel
context_risk: low
debate_round_1: done               # 3 critics, all ADJUST, 0 VETO → PROCEED (design-coherent)
provenance:
  source: "nightly-hygiene sweep 2026-06-20 (post-PLAN-142 merge 8a1fc68) — RED on audit-errors + counts-drift + env-var-drift. This plan collects the repo-debt items it exposed (most pre-date PLAN-142)."
---

# PLAN-143 — Repo-hygiene debt collected from the 2026-06-20 nightly sweep

> **One-line goal:** clear the four governable-debt items the post-PLAN-142
> nightly-hygiene sweep surfaced — env-var inventory drift, two audit-emit
> forbidden-field drops, and a stale tests-floor doc number. PLAN-142 itself is
> done and green; this is separate repo housekeeping (3 of 4 items pre-date it).

## 0. Provenance & honest framing

The `nightly-hygiene` workflow (ADR-136 read-only sweep) ran after the PLAN-142
merge (`8a1fc68`) and returned **RED**. The merge itself is clean — `ci-red`
green (20/20 main runs success), `staleness` green, derived-counts matched
(`lib=68` corrected in PLAN-142), substrate-watch carries the new `codex_cli`
component. The RED is **repo debt the general sweep exposed**, collected here so
it is governed rather than ad-hoc. Items 1-2-4 pre-date PLAN-142; item 3 is a
PLAN-142 follow-up (a pre-existing emit bug its restored rail made observable).

## 1. Diagnosis (4 items, by nightly dimension)

1. **env-var-drift (red) — inventory-accuracy reconciliation (NOT 25 unreviewed
   surfaces).** `env-inventory-check.py --json` = `drift`: 449 live refs vs 424
   inventoried (inventory generated 2026-06-13); 0 stale. `TOKEN_RE` is a
   documented SUPERSET scanner (any `CEO_*`/`CLAUDE_*`/`ANTHROPIC_*` token).
   **Round-1 debate correction (CF-1, verified by 3 critics):** the five named
   "governance kill-switches" (`CEO_TRUST_BYPASS`, `CEO_CANONICAL_GUARD_DISABLE`,
   `CEO_ALLOW_NO_VERIFY`, `CEO_HOOKS_DISABLE`, `CEO_SKIP_HOOKS`) have **ZERO live
   `getenv`/`environ` consumers** — they enter the inventory only as
   forbidden-family tokens inside `_lib/env_persist_allowlist.py` (the deny-list
   whose job is to EXCLUDE them), and the bypass class is already governed by
   **ADR-143**. So this item is **inventory-drift reconciliation**, NOT a review
   of unreviewed bypass surfaces and NOT a new ADR. The genuinely-new consumers
   to classify are the `ANTHROPIC_*` model-routing trio and `CLAUDE_ENV_FILE` (a
   file-path env surface — the one genuinely security-adjacent new name); the
   remaining lifecycle vars (`CEO_COMPACTION_CONTINUITY`, `CEO_SUBAGENT_LIFECYCLE*`)
   are census descriptors. NONE are from PLAN-142.

2. **audit-errors-02 (red) — rotation-probe AttributeError (live producer bug).**
   The phase-4 rotation probe at `spool_writer.py:1729/1967` calls
   `_rotate_if_needed_safe` (defined `audit_emit.py:2166`) but the runtime object
   is the `_EmitCapture` test/shim object, which lacks the attribute → rotation
   silently skipped (3 lines, 2026-06-18). Pre-dates PLAN-142.

3. **audit-errors-04 (red) — `codex_invoke_dispatched` drops `exit_code`.**
   `check_pair_rail.py` emits `emit_generic("codex_invoke_dispatched",
   exit_code=...)` but `exit_code` is NOT in
   `_CODEX_INVOKE_DISPATCHED_ALLOWLIST` (audit_emit.py) → scrubbed (ADR-153),
   same class as PLAN-140's `hook_origin` drop. The emit pre-exists (PLAN-093)
   but only became observable now that PLAN-142 restored the rail (the pre-0.139
   rail returned CodexUnavailable before reaching the emit). Fail-open advisory
   telemetry — no functional impact, but the field is lost.

4. **counts-drift (red) — INSTALL.md tests-floor stale.**
   `verify-counts.sh` (full, no `--no-tests`) exits 1: INSTALL.md:227 cites
   `12000+` tests but the live-derived count is 11752 (floor-rule regression).
   Pre-dates PLAN-142 (main `1444caa` shows the same ~11.7k). NOT gated in CI
   (the Governance job runs `verify-counts.sh --no-tests`), so this is a
   doc-accuracy fix, not a CI blocker.

Out of scope (advisory-only, not a defect): `substrate-watch` yellow is
PENDING-OWNER `--refresh` (network, ADR-136 confinement); audit-errors-01 (84×
spool lock-timeout) is benign fail-open; audit-errors-03 is PLAN-140-fixed
pre-fix noise.

## 2. Governance — entanglements (round-1 debate folded)

- **Item 1 (env inventory):** the work is **inventory-drift reconciliation**,
  NOT a 25-surface review. Classify each of the 25 NEW tokens as one of
  {`consumed` | `forbidden-family-mention` | `descriptor`} BEFORE any regen; the
  five kill-switch names are `forbidden-family-mention` (deny-list tokens, ZERO
  consumers) and are NOT enrolled as intended surfaces. The regen
  (`env-inventory.json`, WRITE mode) is the LAST step. **Deny-list disjointness
  invariant (SK-1):** the regen must NOT land any override/escape-hatch name in
  any *persist allowlist*; `test_env_persist_allowlist.py` must still pass
  post-regen (the descriptive inventory census ≠ a persist allowlist).
- **Item 2 (spool_writer):** `_lib/spool_writer.py` is canonical-guarded →
  sentinel + GPG. **Default locus (SK-6):** hasattr/getattr-guard the probe
  (smallest blast radius; keeps `_EmitCapture` a pure test double; keeps the
  surrounding fail-open `try/except` intact per CLAUDE.md §4). The probe is
  ALREADY fail-open, so the AttributeError is cosmetic `audit-log.errors` noise,
  not a production rotation-correctness failure — but rotation must still be
  proven to run on the REAL writer (NH3).
- **Item 3 (allowlist):** fix = add `exit_code` to
  `_CODEX_INVOKE_DISPATCHED_ALLOWLIST` in `_lib/audit_emit.py`, type-clamped
  (bounded int, e.g. 0..255) with an inline provenance comment. **Manifest
  framing corrected (CF-2):** BOTH candidate loci re-touch
  `pair-rail-inputs-hash-manifest.txt` — `audit_emit.py` (line 22) AND the kernel
  `check_pair_rail.py` (line 27). The canonical path is preferred ONLY on
  ceremony-cost (canonical-GPG < KERNEL-HARD-DENY); the `inputs_hash`
  invalidation is identical either way. **Sequencing (CF-2/D4):** the edit
  mutates the recomputed `inputs_hash`, so item 3 MUST ship paired with verdict
  regeneration OR wait — it must NOT silently grow the coupling behind
  `CEO_PAIR_RAIL_VERDICT_OPTIONAL=1`.
- **Item 4 (INSTALL.md):** non-guarded doc edit. **Peel off + ship standalone
  now** (CF-4) — not behind the canonical ceremony. Set a **floor** `11000+`
  (live 11752 ≥ 11000, headroom for normal suite churn); do NOT pin the exact
  ~11.7k (defeats the floor rule, re-breaks the nightly).
- **npm/ mirror (SK-4):** every coupled file has an `npm/.claude/` twin
  (`audit_emit.py`, `check_pair_rail.py`, `env-inventory.json`, the manifest,
  `verify-counts.sh`). Execution must state whether the mirror is in scope (apply
  each edit to both trees, or run the sync step) so the next sweep does not flag
  fresh `.claude/` ↔ `npm/.claude/` drift.

## 3. Acceptance criteria (hardened in round 1)

- `[P1][env-inventory]` each of the 25 NEW tokens is classified
  {consumed | forbidden-family-mention | descriptor}; forbidden-family mentions
  recorded as such and NOT enrolled as intended surfaces; genuinely-consumed
  security-adjacent names (esp. `CLAUDE_ENV_FILE`) get the real review.
  `env-inventory-check.py --json` returns `status=current` (0 NEW, 0 stale) AND
  `test_env_persist_allowlist.py` still passes (disjointness preserved).
- `[P1][audit-errors-02]` rotation probe no longer raises AttributeError on a
  capture-shim object (hasattr/getattr-guard). **Positive-contract test (CF-3):**
  given a shim lacking `_rotate_if_needed_safe`, the probe takes the intended
  branch AND emits NO AttributeError breadcrumb to `audit-log.errors`; AND a
  second assertion proves rotation IS invoked on the real `audit_emit` object
  (not just "no exception" — that passes with the bug present).
- `[P2][audit-errors-04]` `codex_invoke_dispatched` retains `exit_code`
  (allowlist extended, type-clamped). **Test (CF-3/SK-2):** asserts the field
  survives AND no OTHER field newly survives (allowlist did not widen) AND the
  `_scrub` drop-counter no longer logs the forbidden-field warning. New tests go
  in `hooks/tests/` (not the canonical-guarded `_lib/tests/`), subclass
  `TestEnvContext`, use `mock.patch.dict`. **Sequencing (D4):** ship paired with
  verdict regeneration (recompute `inputs_hash`, GPG-sign, within the 24h TTL of
  the next tag) OR split item 3 out to wait. Reconcile the two-channel emit
  (the typed `emit_codex_invoke_dispatched()` does not accept `exit_code`).
- `[P2][counts-drift]` INSTALL.md tests-floor set to `11000+` (floor-by-design,
  cross-ref the verify-counts.sh header rule); `verify-counts.sh` (full) exits 0.
- `[P2][regression]` a follow-up `nightly-hygiene` run is GREEN on exactly
  {audit-errors, counts-drift, env-var-drift}; substrate-watch MAY stay yellow
  (pending Owner `--refresh`). Provide the 3 reproducible verification commands
  (`env-inventory-check.py --check`, `verify-counts.sh` full, a `codex_invoke_dispatched`
  re-emit) so the closeout is mechanical, not narrative.

## 4. Design decisions (ratified round 1)

- **D1 — batch vs split: RATIFIED.** Items 2+3 batch under one canonical ceremony
  (both edit canonical `_lib/*.py`; the sentinel scope spans BOTH
  `spool_writer.py` and `audit_emit.py` — one sentinel, two files). Items 1 and 4
  are independent; **item 4 ships first, immediately, standalone**; item 1 is an
  independent data-regen.
- **D2 — item-3 locus: RATIFIED canonical, framing corrected.** Canonical
  `audit_emit.py` over kernel `check_pair_rail.py` on ceremony-cost grounds —
  but BOTH re-touch the manifest, so the choice does NOT avoid the release
  coupling (only the heavier kernel ceremony).
- **D3 — env-var policy: RATIFIED — NO new ADR.** The kill-switch premise was
  false (CF-1): the five names are deny-list mentions with zero consumers,
  already governed by ADR-143 + the inline `env_persist_allowlist.py`
  documentation. An ADR "documenting the kill-switch surface" would be actively
  harmful (it would imply the bypasses exist + are blessed). Inventory
  reconciliation + the classification note suffice.
- **D4 — item-3 sequencing (NEW, the most consequential decision):** item 3 MUST
  ship paired with a fresh `pair-rail-verdict-<tag>.md` (post-edit `inputs_hash`,
  GPG-signed, within the 24h TTL of the next tag) OR be split out to wait.
  Shipping a bare allowlist edit under `CEO_PAIR_RAIL_VERDICT_OPTIONAL=1` converts
  a transition bridge into a permanent crutch. Closing the transition
  (OPTIONAL→0) is OUT of scope here, but item-3's verdict regen is its
  prerequisite — flag, do not silently defer.
- **D5 — durability/recurrence (NEW, flag-only):** item-1 + item-4 drift recur
  because neither is CI-gated. Name the structural gap (a periodic
  `env-inventory-check.py --check` / full `verify-counts.sh` assertion); the gate
  itself is DEFERRED (out of scope) but recorded so this is not an infinite
  manual-reconciliation chore.

## 5. Status

**REVIEWED — execution-ready (design).** Round-1 debate complete: 3 critics, all
ADJUST, **zero VETO/REJECT**, verdict PROCEED (design-coherent); 7 adjustments
folded into §1-§4 (see `architect/round-1/consensus.md`). Per DEBATE-SCHEMA §13
this certifies design coherence ONLY — shipping still needs V1 (tests/gates) → V2
(Codex pair-rail, now restored) → V3 (Owner GPG). Execution graph: **item 4
first** (trivial standalone) → **item 1** (independent regen) → **items 2+3
batched** (one canonical-GPG ceremony; item 3 gated on verdict regen per D4).
PLAN-142 is unaffected and remains `done`.
