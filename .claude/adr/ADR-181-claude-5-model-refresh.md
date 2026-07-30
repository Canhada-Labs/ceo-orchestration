# ADR-181 — Claude 5 model refresh: full-fleet working set, floor +opus-5, fallback flip (OQ1=b)

- **Status:** Accepted (Owner tie-break W0b, S284 — 2026-07-28; effective when
  the PLAN-163 W3 staged pack lands at the GPG ceremony)
- **Date:** 2026-07-28
- **Plan:** PLAN-163 (T1.10; gap-matrix G1/G2/G3)
- **Blast radius:** L3+ kernel — VETO-floor constant
  (`agent_frontmatter.py:136`), routing table (`_lib/model_routing.py:59-65`),
  role→model map (`audit_log.py:890-917`), ADR-149 generated mirrors
  (`.claude/settings.json`, `templates/settings/settings.base.json`),
  independent validators (`validate-governance.sh:707-723`,
  `tier_policy_cli/_types.py:26-34`)
- **Debate:** PLAN-163 round-1 — 3 critics, 3×ADJUST → PROCEED, 14
  adjustments (`.claude/plans/PLAN-163/debate/round-1/consensus.md`)
- **Cross-vendor review:** codex r1–r5 (REJECT ×4 → APPROVE r5) + grok r1–r4
  (APPROVE r3 + delta-confirm) — 38 findings applied
  (`.claude/plans/PLAN-163/review/`)
- **Relates to:** ADR-149 + Amendment 1 (the two blocks this refresh updates),
  ADR-157 (Sonnet 5 enum member, flip deliberately deferred), ADR-142
  (generation-bump precedent), ADR-144 (tier routing), ADR-095
  (sunset/retraction pattern)

## Context

The Claude 5 family is complete upstream: **Fable 5** (2026-06-09, already
adopted for VETO roles per ADR-149 base Decision), **Sonnet 5** (2026-06-30 —
`MODEL_ID` member since ADR-157, which deliberately deferred any routing flip
to "its own plan"; new tokenizer ~+30% tokens for the same text; intro pricing
$2/$10 per MTok through 2026-08-31, then $3/$15), and **Opus 5** (2026-07-24,
`claude-opus-5` — drop-in at Opus 4.8 pricing $5/$25, 1M context default,
effort `xhigh`, and a **separate rate-limit bucket**, a quota-accounting
compatibility fact). Opus 4.1 retires 2026-08-05 (covered by the T1.8
`STALE_RE` sweep, not this ADR).

ADR-149 Amendment 1 made `AVAILABLE_MODELS_WORKING_SET` and
`FALLBACK_MODEL_CHAIN` the single machine-parseable source from which the
`availableModels`/`fallbackModel` settings are GENERATED
(`generate-available-models.py`; mirror test
`test_available_models_mirror.py`). A fleet change is therefore an ADR-149
block amendment first, and everything else is regeneration plus the
independent-mirror sweep (T1.2d). This ADR is the decision record for that
amendment; the amended ADR-149 copy ships in the same staged pack.

The Owner ratified the open questions at W0b (S284, structured tie-break):
**OQ1=(b) full refresh** — working set, VETO floor, debate/arch routing AND
`FALLBACK_MODEL_CHAIN` move to `claude-opus-5` immediately, **without a soak
window** (the CEO draft was b-soak; the Owner chose b); **OQ2 = migrate the
advisory tier now** to `claude-sonnet-5`, accepting the tokenizer risk (below).

## Decision — ratified literals (W0b; byte-normative)

| Surface | Ratified literal |
|---|---|
| `availableModels` (generated, both mirrors) | `["claude-opus-4-8","claude-fable-5","claude-sonnet-4-6","claude-haiku-4-5","claude-opus-5","claude-sonnet-5"]` |
| `fallbackModel` (explicit edit, both mirrors) | `["claude-opus-5"]` |
| `model` (session-default pin, explicit edit, both mirrors) | `"claude-opus-5"` (top-level settings key; T1.1 contingency — see §Contingency) |
| `permissions.defaultMode` | `"manual"` (contract: `effective_config.py:178-180,534-542`) |
| `VETO_FLOOR_ALLOWED` | += `claude-opus-5` (fable-5 remains the ceiling) |
| Routing: debate/arch tier | `claude-opus-5` |
| Routing: advisory tier | `claude-sonnet-5` |

1. **Working set** — `AVAILABLE_MODELS_WORKING_SET` (ADR-149 A1.1) gains
   `claude-opus-5` and `claude-sonnet-5`, **appended at the end** in that
   order. The generated `availableModels` arrays in `.claude/settings.json`
   and `templates/settings/settings.base.json` are regenerated via
   `generate-available-models.py` — direct edits of the arrays remain
   PROHIBITED (A1.2).
2. **Fallback flip (OQ1=b, no soak)** — `FALLBACK_MODEL_CHAIN` becomes
   `("claude-opus-5",)`; the `fallbackModel` mirrors become
   `["claude-opus-5"]` as an explicit edit step in both surfaces (the
   generator emits only `availableModels`). Chain stays length 1 (cap 3).
3. **VETO floor** — `VETO_FLOOR_ALLOWED` (base ADR-149 Decision;
   `agent_frontmatter.py:136`) gains `claude-opus-5` in the SAME ceremony
   batch as item 2, so ADR-149 A1.3 clause (a) (chain ⊆ floor for governance
   sessions) never transiently breaks. **`claude-fable-5` remains the
   ceiling**: VETO personas keep their fable-5 pin; opus-5 floor membership
   exists so debate/arch verdicts and the fallback chain stay inside the
   floor — it is NOT a VETO re-pin.
4. **Routing** — `_lib/model_routing.py:59-65`: debate/arch →
   `claude-opus-5`; advisory tier → `claude-sonnet-5` (OQ2). The
   `audit_log.py:890-917` role→model map moves identically (it is routing,
   not pricing — grok r1 F11).
5. **Independent mirrors** — `validate-governance.sh:707-723` and
   `tier_policy_cli/_types.py:26-34` (plus any further validators the T1.2d
   inventory finds) accept the new ids, with the non-vacuous parity test
   tying their accepted sets to this ADR's blocks (ADR-149 contract, lines
   39-43 pre-refresh).
6. **`permissions.defaultMode: "manual"`** rides the same settings refresh
   (OQ5 posture; the wider OQ5 fail-closed keys are recorded in PLAN-163
   T5.3, not here).

### Normative order rule (byte-compared)

New ids are **APPENDED AT THE END** of the working set — never prepended,
never interleaved. Two reasons, both load-bearing:

- **Order is normative and byte-compared.** ADR-149 §A1.1 Semantics (lines
  95-102, pre-refresh numbering): the working set is a tuple, generation is
  byte-deterministic, and `test_available_models_mirror.py` compares the
  generated arrays byte-for-byte (fixtures byte-compare the ratified arrays
  above, never "+=").
- **The FIRST entry participates in default-resolution.** Appending at the
  end keeps `claude-opus-4-8` as the first entry, so the refresh cannot
  silently change which model a default-resolving surface lands on (this is
  the same property the T1.1 contingency below guards from the other side).

Any deviation from append-at-end requires an explicit justification recorded
in this ADR (per the PLAN-163 T5.4 normative rule). The upgrade migration
(T5.4) byte-compares against the ratified literals in the table above.

## Advisory tier → Sonnet 5 (OQ2) — rationale and accepted risk

- The advisory tier renders non-binding review/advice; it is not
  VETO-eligible (VETO eligibility remains exclusively `VETO_FLOOR_ALLOWED`
  membership — the two blocks intersect but are never merged, A1.1).
- Cost surface: Sonnet 5's sticker per-token pricing matches Sonnet 4.6
  ($3/$15), with intro pricing $2/$10 through 2026-08-31. The **new
  tokenizer emits ~+30% tokens for the same text** (ADR-157 envelope), so
  token-denominated budgets and estimates calibrated on the 4.6 tokenizer
  UNDER-estimate on Sonnet 5 by roughly that factor, and after 2026-08-31 an
  equivalent request costs ~+30% more than on 4.6 at identical per-token
  rates.
- **The Owner explicitly accepted the tokenizer +30% risk** (W0b): the
  migration does NOT wait for a re-baseline. The `count_tokens` re-baseline
  of advisory-tier surfaces is a **pack item** (not a precondition); the
  re-baseline of shipped budget envelopes is a named **follow-up plan**
  (PLAN-163 T6.1 tokenizer note).
- ADR-157's OQ1 resolution ("member now, routing flip later, with soak")
  is superseded for scope and soak by this Owner ratification: this ADR is
  the dedicated flip record ADR-157 demanded, and the no-soak deviation is
  Owner-ratified, not drift. The ADR-157 §Decision-4 mechanism works as
  designed: pinned regression tests that byte-pin old routing are
  consciously edited in this pack, never silently. The tier-policy
  `FROZEN_BASELINE` defaults (ADR-157 §4 pins) are **out of scope** of this
  ADR and unchanged.

## Sunset of `claude-opus-4-8` in the floor — POST-migration event (ADR-095 pattern)

This refresh is **additive**: `claude-opus-4-8` REMAINS in the working set
and in `VETO_FLOOR_ALLOWED`. Removing it from the floor is a **separate,
post-migration event**, following the ADR-095 pattern: a published
commitment is retracted only by its own Owner-signed formal record, never
bundled into the change that makes it retirable, and never automatic
(ADR-149 base Decision: "Removal of an id remains an Owner-only act").
Preconditions for that future sunset ADR: the fleet has soaked on the
refreshed routing, no instrument still pins opus-4-8, and the
deprecation-watch surfaces (T1.8/T1.9) are green on it. Until then,
opus-4-8's presence preserves ADR-142 replay (historical transcripts and
fixtures referencing it keep classifying).

## Note — runtime-fallback gap vs floor bijection

The floor is enforced at **spawn time** (membership check in the spawn gate;
the bijection tests assert floor/mirror agreement). The two **runtime**
switch mechanisms — the availability `fallbackModel` chain and the Fable-5
content-classifier fallback — change which model renders output mid-turn
WITHOUT passing through the spawn gate; no hook observes the switch
synchronously. The guarantee that degradation never leaves the floor is
therefore **by construction** (the chain is AUTHORED inside the floor,
A1.3(a); the harness drop of out-of-`availableModels` chain elements is the
backstop, not the policy), plus the A1.4 honest boundary that a local
settings layer can replace the chain wholesale. This gap is why:

- item 3 above lands the floor addition and the chain flip in the SAME
  ceremony batch (a chain member outside the floor is exactly the A1.3
  clause (c) threat);
- A1.3(c) discipline is unchanged and re-affirmed: instruments and
  VETO/ceremony sessions pin `--model` explicitly and declare any fallback
  switch as a confound;
- the alignment property of A1.3 rationale (ii) is PRESERVED by this flip:
  on CC ≥2.1.219 the harness default Opus is `claude-opus-5` — verified in
  the 2.1.220 binary model table (T2.2 extraction, binary sha256
  `8addc857…`): `aliases.opus.default = "claude-opus-5"` and
  `latest_per_family.opus = "claude-opus-5"` (first-party provider;
  the version threshold 2.1.219 is the changelog recon fact, G1), and
  consistent with the schema-diff row 4 note that plan-mode upgrade models
  downgrade to the "newest permitted Opus" — so availability-fallback and
  content-classifier refusal-fallback land on the same model, as they did
  in the opus-4-8 generation.

## Contingency (T1.1) — `enforceAvailableModels` default-resolution

ADR-149 A1 recorded (2026-06-12 verification) that `enforceAvailableModels`
was NOT a real settings key. The PLAN-163 T2.2 schema extraction from the
2.1.220 binary re-verifies this, including the documented managed-policy
fail-open semantics, BEFORE the W3 ceremony. Normative contingency, ratified
at W0b: **if the fail-open default-resolution semantics is confirmed** in
the T2.2 schema diff, then the session default model is **pinned explicitly
in the SAME commit** that adds `claude-sonnet-5` to the working set — so
making sonnet-5 *available* can never silently make it the session
*default* for governance work.

- T2.2 schema-diff verdict on `enforceAvailableModels` (key exists? fail-open
  confirmed?): **CONFIRMED — the contingency is TRIGGERED and the explicit
  session-default pin ships in this pack.** Per
  `PLAN-163/probes/schema-diff-2.1.202-to-2.1.220.md` §(i) (2.1.220 binary
  sha256 `8addc857…`): the key exists with describe text verbatim-identical
  to 2.1.202; runtime default-resolution iterates `availableModels` **in
  list order** and the FIRST allowed-AND-server-available entry wins the
  effective Default when the tier default is not in the list (ordering of
  the T5.4 pin list is load-bearing); if NO entry survives, the harness
  warns and **keeps the unconstrained tier default (fail-open)**; the
  documented managed-policy fail-open ("refusing cascade-trust mode" —
  model enforcement from user/project settings disabled until the policy
  source is fixed) **exists unchanged in 2.1.220**. New in 2.1.220 only:
  the `model_access` entitlement joins `availableModels` as a second
  restriction source (neutral for dogfood — no managed entitlements).
  Therefore the normative branch above applies: the session default model
  is pinned explicitly in the SAME commit that adds `claude-sonnet-5`.

### The concrete pin that ships (key, value, why)

- **Key.** CC 2.1.220 honors the top-level settings key **`model`** (a
  string) as the session-default override. Binary evidence (T2.2, 2.1.220
  sha256 `8addc857…`): the settings zod schema declares
  `model:E.string().optional().describe("Override the default model used by
  Claude Code")` at binary byte offset **226819212**, positioned between the
  `permissions` and `fallbackModel` keys of the same settings object. This is
  the settings-native pin — *not* the internal workflow property
  `defaultModel` (a Workflow run field, not a settings key) and *not* the
  env var `ANTHROPIC_MODEL` (a runtime override, not a file-persisted
  setting). A settings file cannot pin the default with anything else.
- **Value.** `"model": "claude-opus-5"` — coherent with OQ1=b (opus-5 is the
  ratified primary and the sole `fallbackModel` chain member). The value is a
  member of `availableModels` (appended in item 1), which
  `enforceAvailableModels` requires — a pin outside the allowlist is rejected.
- **Why it is load-bearing.** Before this refresh, `claude-opus-4-8` was
  `availableModels[0]`; because the 2.1.220 tier default (`claude-sonnet-5`,
  T2.2 model table) was NOT in the allowlist, `enforceAvailableModels`
  redirected the effective session default to the first allowed entry
  (opus-4-8). The moment `claude-sonnet-5` is APPENDED to `availableModels`,
  the tier default becomes an allowed model, `enforceAvailableModels` stops
  redirecting, and the session default would **silently flip to sonnet-5**
  for governance work. The explicit `model` pin forecloses that flip
  independently of allowlist ordering.
- **Both mirrors.** The key ships identically in `.claude/settings.json`
  (dogfood) and `templates/settings/settings.base.json` (adopters).
  **Adopter cost note:** a fresh install therefore inherits
  `claude-opus-5` as its session default (Opus pricing $5/$25 per MTok). If
  that default is undesirable for an adopter's workload, the documented
  alternative is to override the `model` value in their own settings (e.g.
  a lighter tier default) or per-session via `ANTHROPIC_MODEL` / CLI
  `--model`; the template comment states this inline. Runtime overrides are
  unaffected by the pin.
- **Oracle.** `test_session_default_pin` (staged) asserts both mirrors carry
  `model == "claude-opus-5"` AND that the pinned value is a member of each
  file's `availableModels` — so a future allowlist edit that drops opus-5
  without updating the pin reddens rather than silently disabling
  enforcement.

## Consequences

- A generation bump is once again a data change inside the established
  ceremony shape (ADR-149 consequence, exercised for the second time after
  ADR-142): amend the blocks, regenerate mirrors, sweep independent
  validators, re-run the frozen-SHA regen.
- Capability uplift on debate/arch and VETO-adjacent surfaces; Opus 5's
  separate rate-limit bucket is a quota-accounting fact recorded for
  operators. **No speed/throughput claim is made or implied** (AGENTS.md
  no-speed-claim; PLAN-163 Addendum item 4).
- Cost visibility: the presence-based pricing fix (PLAN-163 T1.5) adds the
  new ids additively to `_PRICING_PER_MTOK`, detectors, `cost-table.yaml`,
  `ceo-cost.py`, `budget-summary.py` — historical ids are never removed.
- The ADR-149 Amendment-1 PROSE in §A1.1 Semantics still narrates the
  opus-4-8 generation ("the sole fallback is claude-opus-4-8") — the staged
  amendment updates ONLY the two machine-parseable blocks, which are the
  normative source (A1.2); this ADR is the authoritative refresh record for
  the prose delta. A future editorial pass may reconcile the prose at a
  closeout (cache discipline), citing this ADR.
- Regression surfaces consciously edited in this pack:
  `test_available_models_mirror.py` expectations (fallback equality,
  :193-200 pre-refresh), floor-bijection companions, routing-pin tests,
  smoke-install parity assertion (fleet + fallback order, T1.7).

## Alternatives considered

- **(a) Minimal adoption** — opus-5 available only, floor/fallback/routing
  unchanged. Rejected by the Owner tie-break (OQ1=b): leaves debate/arch on
  the prior generation and the fallback below the capability of the fleet.
- **(b-soak) Full refresh behind a soak window** (the CEO draft). The Owner
  chose immediate (b): the flip is Owner-ratified with rollback via the
  same ADR-149 amendment path; a soak window would gate the whole pack on
  calendar time (the ADR-095 lesson: calendar gates that are not
  structurally protective do not change what is true about the change).
- **Prepend or reorder ids** — rejected: order is byte-compared and the
  first entry participates in default-resolution; reordering is a behavior
  change masquerading as a list edit (see Normative order rule).
- **Migrate advisory only after re-baseline** — rejected at W0b: the risk is
  bounded (advisory is non-binding; intro pricing overlaps the migration),
  and the re-baseline lands as a pack item regardless.
- **Retire opus-4-8 from the floor in this ADR** — rejected: sunset is a
  post-migration event per the ADR-095 pattern (own record, Owner-signed).

## References

- PLAN-163 — `.claude/plans/PLAN-163-substrate-uplift.md` (gap-matrix
  G1/G2/G3; T1; T5.4 literal table; Addendum S283; OQ ratifications W0b).
- Debate: `.claude/plans/PLAN-163/debate/round-1/consensus.md`
  (3×ADJUST → PROCEED, 14 adjustments).
- Cross-vendor review: `.claude/plans/PLAN-163/review/codex-r1..r5.md`,
  `grok-r1..r4.md` (codex APPROVE r5; grok APPROVE r3 + delta-confirm).
- ADR-149 + Amendment 1 (blocks amended by the staged copy in this pack);
  ADR-157; ADR-142; ADR-144; ADR-095.
