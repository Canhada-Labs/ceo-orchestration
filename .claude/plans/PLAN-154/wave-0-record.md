# PLAN-154 — Wave 0 record (S265, 2026-07-09, autonomous overnight run)

**STATUS: PENDING-CLOSEOUT** — the staged overlay and the SENT-F draft
referenced below DO NOT EXIST YET at first writing (workflow
`wf_9071cc3c-6e4` in flight). This line flips to VERIFIED-AT-CLOSEOUT
with a file listing only after they are present on disk. Until then this
record is a statement of intent, not ceremony evidence (pair-rail
diff-review P2, twice).

Owner authorization: overnight autonomous execution (2026-07-09 evening
directive); GPG ceremonies deferred to the morning wake-up. Guarded work is
being staged under `PLAN-154/staged/sent-f/` (mirror layout) by workflow
run `wf_9071cc3c-6e4` (IN FLIGHT at the time this record was first
written — pair-rail diff-review P2 fix: these artifacts are PENDING until
the workflow completes; this record is finalized at closeout, when the
overlay + the SENT-F draft at `PLAN-154/architect/round-1/approved.md`
are verified present on disk). SENT-F stays inert until Owner signature.

## Precondition verification

1. **PLAN-153 Wave E MERGED on main** — VERIFIED: commit `24d2a27`
   ("feat(PLAN-153 wave-E): land security gates") is in main history;
   `/ceo-boot` S265 shows `harness_config_gate: green` and
   `failopen_rail_liveness_7d` reporting — the Wave E surfaces are LIVE,
   not staged. Positive-control fixtures (`test_check_harness_config.py`,
   `test_bash_citation_gate.py`, `test_prompt_defense_baseline.py`) landed
   in the same commit; Validate green on main as of `9096813`.
2. **LANDED Wave-E marker syntax + positive-control fixture API pinned
   (A11):** gate-side allowlist file = `.claude/hooks/harness-noop-allowlist.txt`
   (`check_harness_config.py:136`, `NOOP_ALLOWLIST_REL`); in-file marker
   `[harness-noop-ok]` (`:128`) is honored ONLY via the matcher entry's
   `_comment` (`is_noop_allowlisted`, `:418-424`) — the gate-side list is
   authoritative, per A11 an in-file marker alone is insufficient for new
   opt-in no-op hooks; runtime-resolution waiver marker
   `[harness-resolution-ok]` (`:132`). Fixture API: see
   `.claude/hooks/tests/test_check_harness_config.py` (landed Wave E).
3. **ADR-160** — reserved; draft authored this run (staged, rides SENT-F
   ceremony batch), carrying A2/A4/A6/A8/A10/A11 normative text.
4. **SENT-F** — drafted this run with the full A13 scope; signature =
   morning ceremony.

## Wave-0 decisions (pre-registered, per A8/A13)

### Item-6 numeric flip criteria (A8 — pre-registered into ADR-160)

The fact-forcing deny-once gate flips ADVISORY→ENFORCE only when ALL hold,
measured from the HMAC audit log (never from mutable side files):

- **FP rate < 2% over ≥ 50 gate-candidate events** in shadow (a
  gate-candidate event = the already-matched rare path where the gate
  WOULD deny; an FP = a shadow-deny event whose subsequent retry carried a
  valid citation unchanged — i.e. the deny would have blocked a correct
  command);
- **≥ 14 calendar days** of shadow telemetry elapsed since the first
  shadow event;
- **zero unresolved integrity flags** (hash-mismatch drops, A6) in the
  same window.

The flip itself is a governed event: settings-backed, sentinel-scoped,
HMAC-chain governance event on every activation change (item 6 text).

### Test-placement decision (A13)

- **No new test directories.** All new tests land in EXISTING
  validate.yml-wired dirs: `.claude/hooks/tests/` (unguarded — hook and
  `_lib` surfaces, precedent `test_tool_lifecycle*.py`) and the existing
  lessons/scripts test home (recon task of the build workflow confirms the
  exact dir currently wired for `.claude/scripts/lessons.py` tests and
  places new files alongside).
- Consequence: `validate.yml` needs NO test-path change for PLAN-154 →
  the A13 same-commit rule is satisfied by construction; `_lib/tests/`
  (guarded) is NOT used, keeping SENT-F scope minimal.
- Env vars: every new var registers in `.claude/scripts/env-inventory.json`
  + CHEAT-SHEET env table + autouse reset fixture IN THE SAME staged
  overlay (single landing commit family) — S218 class.

### Kill-switch naming (constraint 9 / A12)

- `CEO_LEARNING_OBSERVE=1` — observe rail opt-in (unset = structurally
  off, `cost_envelope.py` posture).
- `CEO_LEARNING_DISTILL_MODEL` — distiller model override (default pinned
  haiku-tier explicitly in the distiller, NOT via stub `model_routing.py`).
- Enforce-side switch for item 6 is SEPARATE from observe (disabling
  observe never touches the deny-once gate) — name decided in build:
  `CEO_FACT_GATE_ENFORCE` (settings-backed flip artifact, env only as
  documented emergency off), with `CEO_SOTA_DISABLE=1` master precedence
  documented for all of the above.

## Interface contracts fixed for the build (anti-integration-drift)

- `lessons.get_boot_lessons_verified(project_dir, now_fn=None) -> list`
  of ≤3 dicts `{lesson_id, text (≤200 chars, bounded vocab: no backticks,
  no newlines), content_sha256}` — ALL validation inside lessons.py
  (bounded-vocab check, TTL/decay, hash verify against chain approval
  events; mismatch → drop + integrity breadcrumb). Renderers (ceo-boot)
  do cap-then-fence + `_lib.guardrail_validator` routing + DENIED-fields.
- `lessons.add_candidate(trigger, advisory_text, scope_tags, now_fn=None)
  -> (lesson_id, status)` — status ∈ {PENDING, QUARANTINED}; injection
  scan fail-CLOSED at this promotion boundary (scanner unavailable OR hit
  → QUARANTINED terminal, A4).
- `format_for_injection` retrofit (A7): same fenced data-not-imperative
  framing as boot; decay/review/dampening lifecycle governs both consumers.
- Dampening helper: `_lib/advisory_dampen.py` — keys on schema decision
  field; advisory-only; ≤1 condensation audit event per advisory ID per
  session; session-scoped 0600 state file (tool_lifecycle pattern).

## OQs

None pending for this plan (the round-1 debate left no Owner OQs; the
item-6 numeric criteria were the one Wave-0 decision, fixed above and
pre-registered in the ADR-160 draft — Owner reviews them at the morning
ceremony before signing SENT-F).

**Owner ratification — 2026-07-10 (S265 ceremony, verbatim):** item-6
flip criteria **CONFIRMED as pre-registered** — flip only when FP < 2%
over ≥ 50 gate-candidate events AND ≥ 14 calendar days of shadow AND zero
unresolved integrity flags; `CEO_FACT_GATE_SHADOW` ships **default-ON**;
the flip is a governed settings-backed + HMAC-chain event. No number
changes. SENT-F is clear to sign on this point.
