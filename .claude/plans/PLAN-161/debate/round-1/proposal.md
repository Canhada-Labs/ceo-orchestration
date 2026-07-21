---
plan: PLAN-161
round: 1
created_at: 2026-07-21
---

# PLAN-161 round-1 proposal — consolidated maintenance sweep

Full plan: `.claude/plans/PLAN-161-maintenance-sweep.md` (read it).

## Thesis

Seven small pending threads (S276-S278) are cheaper closed in ONE
consolidated sweep than as per-thread plans: group by GATING COST, not
topic — one ungated wave (W1), one canonical ceremony batching every
guarded file under a single sentinel (W2), live-fire validation + the
Owner-gated 3-lane council run (W3), closeout (W4).

## The seven threads

1. **Startup lint (substrate drift):** CLI ≥2.1.216 no longer consults
   `Write(path)` permission rules (`Edit(path)` now covers all editing
   tools). Our 3 redundant `Write(X)` deny twins (settings.json:729-735)
   print 3 warnings every session, ship to every adopter via
   `templates/settings/settings.base.json`, and are pinned in the
   `check_harness_config.py` DENY_BASELINE floor (invariant: floor ⊆
   live deny → floor + live must change in the SAME commit). No
   protection lost (Edit twins + canonical-edit hook independent).
2. **upgrade.sh dry-run gap:** `canonical-5` step wrote agent sha256
   pins to the target during `--dry-run` (observed live 2026-07-21).
   Fix + byte-identity dry-run test; sweep the whole step family.
3. **upgrade.sh exclusion parity:** the ADR-155 classified walk ignores
   install.sh's framework-internal exclusions → installed ~967 dogfood
   test files into an adopter (re-armed PLAN-119 root-conftest gate;
   fake exchange-key fixtures = secret-scanner bait), and the manifest
   recorded them → next upgrade RE-ADDS after manual deletion.
   Fix: single-source the exclusion list (3 consumers: install walk,
   upgrade walk, manifest writer) + hash-gated purge of previously
   mis-installed trees (only provably framework-shipped bytes; adopter-
   modified → keep + warn; backup first). Destructive half = OQ1.
4. **Council grok-lane arg-contract (canonical → ceremony):** grok
   0.2.93 `-p` takes the prompt as argv, never stdin → ADR-114 one-pipe
   redacted egress is uncomposable → grok lane structurally unsendable
   → clean 3-lane council impossible → PLAN-156-FOLLOWUP stuck at
   `reviewed`. Fix: redactor writes a 0600 private artifact; grok argv
   references THAT; redactor stays the single chokepoint; redaction
   failure → lane unavailable (grok must never run unredacted). Plus
   codex-lane scope-aware wall-clock budget (its 180s cap dies on large
   scopes). Then run `/council` on `check_canonical_edit.py` (Owner
   egress auth) → close the FOLLOWUP.
5. **perf-gate D3 backoff (validate.yml → ceremony):** two doc-only
   commits defeated the 2-attempt retry inside one runner-load window.
   Add inter-attempt backoff + bounded 3rd attempt (OQ4). N=200
   percentile semantics (PLAN-159/ADR-163) untouched.
6. **pair-rail liveness telemetry:** boot check watches
   `pair_rail_case` events emitted by `check_pair_rail.py` /dead
   `codex_invoke.py` — but real rounds run via `codex exec` + the
   `check_codex_stop_review.py` Stop hook, which emits nothing the
   check sees → boot yellow "no signal in 168h" while the rail
   demonstrably caught a real fail-open 4 days ago. Fix: Stop hook
   emits a registered liveness action (or a new classifier appends to
   the `FAILOPEN_RAIL_CLASSIFIERS` registry). Acceptance is behavioral:
   boot green after a real review round.
7. **verify-counts blind spot + housekeeping:** extend verify-counts.sh
   to ARCHITECTURE/GUIA-COMPLETO/FAQ/npm-README incl. markdown-table
   cells (the twice-bitten S275 drift class); `git rm` the consumed
   `HANDOFF-S277-PLAN160.md`.

## Key decisions to critique

- **D1 consolidation:** one plan + ONE sentinel ceremony for all
  canonical touches (settings.json, check_harness_config.py,
  council-audit.js, _grok_harness.sh, validate.yml,
  check_codex_stop_review.py) vs per-thread plans/ceremonies.
- **D2 atomicity:** C1 requires floor+live deny in one commit; kernel
  hunks (if any file is `_KERNEL_PATHS`) segment out under
  `CEO_KERNEL_OVERRIDE` (PLAN-160 pattern).
- **D3 purge trust boundary (OQ1):** hash-gated deletion in adopter
  repos (framework-hash only, backup, warn-keep otherwise).
- **D4 egress composition (OQ2):** 0600 temp-file + trap cleanup vs
  FIFO for the redactor→grok handoff.
- **D5 FOLLOWUP closure path (OQ3):** clean 3-lane required; NEW-cause
  degradation → hold at `reviewed` + escalate, never silently accept.
- **D6 liveness semantics:** reuse `pair_rail_case` enum from a second
  producer vs a distinct action + new registry classifier.

## Open questions

OQ1 purge semantics · OQ2 artifact mechanism · OQ3 FOLLOWUP closure
fallback · OQ4 backoff shape — CEO defaults in the plan file.

## Verdict requested

ACCEPT / ADJUST / REJECT + the 7-section critique format
(DEBATE-SCHEMA.md §4): Verdict, Summary, Risks, Must-fix,
Nice-to-have, Unseen, What I would NOT change.
