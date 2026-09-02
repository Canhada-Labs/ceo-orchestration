# ADR-149 — VETO-floor model allowlist (generation-portable governance)

> **DRAFT staged for Owner ceremony** — to be moved to
> `.claude/adr/ADR-149-model-id-allowlist.md` (status: PROPOSED) by the
> W0 apply script after the Owner signs the kernel sentinel. Authored S226
> under PLAN-134 W0; cross-model rail: Codex thread `019eae3e` (S225 R1-R4
> lineage + the bundle review that gates this batch).

- **Status:** PROPOSED (becomes effective only with the W0 kernel batch)
- **Date:** 2026-06-10
- **Relates to:** ADR-052 (§Model-ID-bump recipe), ADR-142 (opus-4-8 bump,
  doc-parity precedent), ADR-144 (frontmatter is the sole tiering channel),
  REPORT-S225 findings E1-F1 (P0), E1-F2 (P0), E1-F3, E1-F8, E1-F9, E3-F10.

## Context

S225's audit proved the framework is **generation-locked by exact-equality
pins**: `VETO_FLOOR_MODEL = "claude-opus-4-8"` compared with `!=`
(`agent_frontmatter.py`), a 3-ID hardcoded case allowlist
(`validate-governance.sh`), an `_is_opus` prefix check
(`escalation_signals.py`), and a triple-pinned tier-policy constant with a
frozen SHA. A model UPGRADE is rejected identically to a downgrade; the
migration commit itself cannot pass governance (closed trap, two P0s).
Every generation bump under this design is a 4+-site synchronized kernel
edit — ADR-142 paid that cost once already.

## Decision

Replace every exact-equality model pin in the VETO-floor enforcement chain
with membership in ONE Owner-signed allowlist:

```python
VETO_FLOOR_ALLOWED: frozenset = frozenset({
    "claude-opus-4-8",   # ADR-142 generation — remains valid (additive)
    "claude-fable-5",    # S225/PLAN-134 W0 — the running generation (ceiling pin)
    "claude-opus-5",     # ADR-181 (PLAN-163 T1.3, OQ1=b) — Claude 5 Opus joins the floor
})
```

- `agent_frontmatter.py` owns the canonical constant; the spawn gate checks
  membership. `validate-governance.sh`, `escalation_signals.py` (family
  prefixes derived from the allowlist members), and `tier_policy_cli`
  mirror it per the existing defense-in-depth doctrine (independent
  literals + frozen SHA stay — they pin the ALLOWLIST now, not one ID).
- Tests assert membership, not equality (`test_veto_floor_bijection.py`
  variant-A companion patch).

## Consequences

- A future generation bump = add ONE id to the allowlist + mirrors + rerun
  the SHA regen — a data change inside the ADR-052 ceremony, not a
  redesign. Removal of an id remains an Owner-only act (never automatic).
- Downgrade protection is preserved: anything outside the allowlist
  (haiku/sonnet/unknown) still blocks the spawn loudly.
- The allowlist is the trust statement: its content is ratified at GPG
  ceremony; CI enforces consistency across the 4 mirror sites.
- Explicitly NOT decided here: which generation the 5 VETO agents pin
  (variant A vs B — an Owner choice recorded at the same ceremony, per
  E1-F3); routing economics (PLAN-134 W3); non-VETO tier tables (ADR-067).

## Amendment 1 (PLAN-135 W1 — availableModels working set + fallback discipline)

> Authored S231 under PLAN-135 W1 (unit s1); staged in
> `.claude/plans/PLAN-135/staged/w1/`; effective only when the Owner
> ceremony applies the W1 bundle. Harvest provenance: HARVEST-REPORT S1;
> debate R1 clauses (b)/(c) from `architect/round-1/security-engineer.md`.
> Settings-key reality verified against the published Claude Code docs
> (`settings` + `model-config` pages, fetched 2026-06-12): `availableModels`
> (array of model ids/aliases) and `fallbackModel` (array, chain capped at 3)
> are REAL harness keys; `enforceAvailableModels` is NOT a key (speculative
> name from debate R1 — do not ship it).

### A1.1 Two blocks, two meanings (machine-parseable)

The base Decision's `VETO_FLOOR_ALLOWED` block above is **unchanged** — it
remains the spawn-gate trust statement: the only models permitted to render
a VETO verdict. This amendment ADDS a **distinct, wider** block:

```python
AVAILABLE_MODELS_WORKING_SET: tuple = (
    # -- VETO floor (base ADR-149 Decision; both members, same order) --
    "claude-opus-4-8",    # ADR-142 generation — VETO-floor member
    "claude-fable-5",     # running generation — VETO-floor member
    # -- routing tiers (ADR-144 / _lib/model_routing.py _ROUTING_TABLE) --
    "claude-sonnet-4-6",  # code_gen / finops tier target
    "claude-haiku-4-5",   # file_read / line_audit / digest tier target
    # -- Claude 5 refresh (ADR-181; new ids APPENDED AT END — order is
    #    normative per the Semantics below; any other order needs an
    #    ADR-181 justification) --
    "claude-opus-5",      # debate/arch routing + fallback target + floor member
    "claude-sonnet-5",    # advisory tier target (ADR-157 member; OQ2 migrate-now)
    # -- Fable 5.1 -- ADR-149 Amendment 2, S338 2026-09-01; APPENDED AT END.
    #    Working-set ONLY: not a floor member, not the fallback, not the
    #    session pin. The legacy claude-fable-5 stays available. --
    "claude-fable-5-1",   # Mythos-class flagship 5.1; dateless id per the models overview
)
```

```python
FALLBACK_MODEL_CHAIN: tuple = (
    "claude-opus-5",      # VETO-floor member (ADR-181 refresh, OQ1=b) — degradation never leaves the floor
)
```

Semantics:

- `AVAILABLE_MODELS_WORKING_SET` is the **availability** statement: the set
  of model ids the harness may select on ANY surface (`/model`, `--model`,
  `ANTHROPIC_MODEL`, subagent `model:` frontmatter, the Agent tool `model`
  parameter, `CLAUDE_CODE_SUBAGENT_MODEL`, advisor, fallback chains). It is
  a tuple, not a set: **order is normative** — the generated settings array
  preserves it, so generation is byte-deterministic.
- Sonnet/Haiku being *available* (ADR-144 tier routing needs them
  selectable for subagent route-down) does **not** make them VETO-eligible.
  VETO eligibility is exclusively `VETO_FLOOR_ALLOWED` membership, enforced
  by the spawn gate. The two blocks intersect but are never merged.
- `FALLBACK_MODEL_CHAIN` is deliberately length 1 (cap is 3): the primary
  session model is `claude-fable-5` and the sole fallback is
  `claude-opus-5`, a fellow VETO-floor member (ADR-181 refresh; the
  pre-refresh chain pointed at `claude-opus-4-8`). Rationale: (i) an
  availability degradation therefore never drops a session below the VETO
  floor; (ii) it matches the harness's own content-classifier fallback
  target for Fable 5 (default Opus), so availability-fallback and
  refusal-fallback land on the same model; (iii) extending the chain into
  sonnet/haiku would let a governance session silently degrade below the
  floor mid-turn — exactly the clause (c) threat. A longer chain for
  non-governance contexts would require its own amendment.

### A1.2 Single source — settings are GENERATED from this ADR

The `availableModels` and `fallbackModel` keys in `.claude/settings.json`
AND `templates/settings/settings.base.json` (Doctrine 2 dual-surface) are
**generated mirrors of the two blocks above**, produced by
`.claude/scripts/generate-available-models.py` (stdlib, standalone):

- generate mode emits the JSON fragment from `AVAILABLE_MODELS_WORKING_SET`
  (falling back to `VETO_FLOOR_ALLOWED` members, with a loud stderr note,
  when run against a pre-amendment ADR — the script is live before this
  amendment is applied);
- `--check` mode diffs the resolved settings (project layer +
  `settings.local.json` overlay) against the ADR and exits non-zero on
  drift, including a `fallbackModel` chain that exceeds 3 members or
  escapes the working set.

Hand-editing the settings arrays without amending this ADR is drift;
`.claude/hooks/tests/test_available_models_mirror.py` (staged with this
amendment) reddens on it.

### A1.3 Fallback discipline — the three S1b clauses

**(a) Fallback NEVER escapes the allowlist.** Every member of
`FALLBACK_MODEL_CHAIN` MUST be a member of `AVAILABLE_MODELS_WORKING_SET`
(and, while the chain serves governance sessions, of `VETO_FLOOR_ALLOWED`).
Defense in depth: the harness itself documents that chain elements outside
`availableModels` are dropped when the chain is read and never tried — but
the normative rule is that the chain is AUTHORED inside the floor in the
first place; the harness drop is the backstop, not the policy.

**(b) All-fallbacks-exhausted = session halts, never silently un-modeled.**
When the primary model and every chain member are unavailable, the turn
MUST fail loudly with an error — the session must never proceed on an
unspecified substitute model or outside the allowlist. The published
harness behavior (unavailable chain elements are skipped; fallback exists
"instead of failing the request", implying failure when no element
remains) is consistent with this, but per Doctrine 3 the knob is not
declared adopted until the path is probed:
`.claude/plans/PLAN-135/research/probe_available_models.md` §Probe 3,
status PENDING-LIVE (opportunistically executed at the next real
overload/outage window — the path cannot be deterministically triggered
from a healthy client).

**(c) Measurement instruments AND VETO/ceremony sessions pin `--model`
explicitly and declare fallback as a confound.** Two distinct switch
mechanisms can change which model renders output mid-turn: the
availability-based `fallbackModel` chain, and the Fable-5
content-classifier fallback to default Opus. Either one occurring inside a
measurement run or a VETO/ceremony session silently changes which model
produced the evidence or rendered the verdict (debate R1). Therefore:
instruments (eval-baseline runs, pilots, ledger-grade harnesses) MUST
launch with an explicit `--model` pin and record any fallback switch notice
in the run ledger as a confound; VETO/ceremony transcripts MUST state the
pinned model and declare the configured chain — a verdict produced after an
undeclared mid-turn switch is evidence-degraded and must say so.

### A1.4 Honest boundaries

- `availableModels` **merges and deduplicates across settings layers** —
  a user-level or `settings.local.json` layer can ADD ids beyond this
  ADR's working set. Strict, tamper-proof enforcement requires managed
  policy settings, which a repo cannot ship (same class as ADR-003 Path C).
  Compensating visibility: the generator's `--check` resolves the local
  overlay, and the S3 tamper tripwires (`ANTHROPIC_MODEL` /
  `ANTHROPIC_DEFAULT_*` remap detection) cover the env channel that
  bypasses the allowlist file entirely.
- `fallbackModel` does **not** merge: the highest-precedence settings file
  that defines it supplies the entire chain — a local layer can silently
  REPLACE the chain. Same compensating visibility as above.
- The model picker's **Default** entry is not governed by
  `availableModels` (it always resolves to the account-tier default). On
  this account class that default is currently inside the working set; the
  picker surface is recorded here so the probe checks it rather than
  assuming it.
- A blocked subagent `model:` override **falls back silently** to the
  inherited/default model (documented 2.1.172 semantics) rather than
  failing the spawn — fine for the routing floor, but it means frontmatter
  pins are not self-verifying; the spawn gate (`check_agent_spawn` /
  `VETO_FLOOR_ALLOWED`) remains the enforcement layer for VETO personas.

## Amendment 2 (S338 — Fable 5.1 joins the working set; floor, fallback and pin unchanged)

> Authored S338 (2026-09-01) under PLAN-169 (fleet-currency remit, W2.10
> class cure: functional surfaces DERIVE from this ADR). Ratified by the
> Owner via AskUserQuestion at the S338 opening — **route (c) of three**:
> working-set append only. Lands through the `wave-fable51` sentinel ceremony
> (`.claude/plans/PLAN-169/wave-fable51-approved.md`).

### A2.1 Facts the amendment rests on (models overview, fetched 2026-09-01)

- Claude Fable 5.1 launched 2026-09-01 alongside Mythos 5.1 (same
  underlying model; Fable carries the additional dual-use safety
  measures and is the generally available one).
- **API id = alias = `claude-fable-5-1`** — dateless. Every id from the
  4.6 generation on is a pinned snapshot, so a date suffix must NEVER be
  appended (the S337 recon measured 233 files citing `claude-fable-5`
  and 0 citing the 5.1 id; the cure is this data change, not a hunt).
- $10 in / $50 out per MTok (equal to Fable 5); 1M context; 128K max
  output; knowledge cutoff June 2026; adaptive always-on thinking;
  retirement no earlier than 2027-09-01.
- **Cache hits on Fable 5.1 are 0.025x the base input price ($0.25/MTok)**
  — the pricing page (fetched 2026-09-01) resolves the conflict the S337
  recon recorded between the models overview (0.1x) and the launch note;
  every other model keeps the standard 0.1x. `budget-summary.py` is the
  ONE cost surface that prices cache reads (input-equivalents), so it
  gains a per-model multiplier instead of the flat 0.10x that would have
  overstated Fable 5.1 cache reads 4x (codex rail r1 P2).
- `claude-fable-5` remains available as LEGACY: the change is ADDITIVE.

### A2.2 Decision

1. `AVAILABLE_MODELS_WORKING_SET` gains `claude-fable-5-1` **at the end**
   (A1.1 order rule — no reorder, no removal). The generated
   `availableModels` mirrors (`.claude/settings.json`,
   `templates/settings/settings.base.json`) follow byte-for-byte via
   `generate-available-models.py`; every INDEPENDENT mirror bound by
   `test_adr149_validator_parity.py` (validate-governance case-arm,
   `tier_policy_cli.VALID_MODEL_IDS`, `smoke-install-parity.sh`
   `ALLOWED_MODELS`) carries the same append in the same patch.
2. `VETO_FLOOR_ALLOWED` is **unchanged**: Fable 5.1 is selectable, not
   VETO-eligible. Routes (a)/(b) — floor membership with or without
   migrating the six `agents/*.md` pins — stay open as a FUTURE amendment
   that the Owner may ratify after measuring the 5.1 verdict quality;
   nothing here pre-empts it.
3. `FALLBACK_MODEL_CHAIN` is **unchanged** (`claude-opus-5`).
4. The session-default `model` pin stays `claude-opus-5` in all three
   adopter-facing mirrors. Flipping it is a SEPARATE decision with its own
   blast radius (adopter default cost x2; `upgrade.sh` pin migration;
   `test_template_dogfood_parity.py` EXPECTED_PIN) and is not made here.
   A maintainer who wants 5.1 as the session default on ONE machine sets
   it in `.claude/settings.local.json` (highest-precedence project layer;
   the generator `--check` resolves that overlay, A1.2).
5. `scripts/upgrade.sh` learns a **`superseded`** list for the
   `availableModels` leaf: the 6-id array that v1.2.0 and v1.3.0 SHIPPED
   is a frozen historical literal (same doctrine as the pair-rail
   `OLD_PAIR_RAIL_CAPS`). Without it the 3-state migration would read
   every v1.2.0/v1.3.0 adopter as ADOPTER-CUSTOMIZED and never deliver
   the seventh id — SILENTLY: the install/upgrade parity e2e declares
   `.claude/settings.json` an ACCEPTED divergence (the two routes
   converge on keys, not bytes), so CI would not have noticed. The match
   stays byte-exact (values AND order), so a genuinely customized array
   is still PRESERVED.
6. `tier_policy_cli/learn.py` `_tier_rank` ranks the new id ABOVE
   `claude-fable-5` (codex rail r1 P1): an id admitted to
   `VALID_MODEL_IDS` but unknown to the ladder ranks -1, so a move away
   from it would sign as `promote` and bypass the signed-demote gate.
   A parity test now requires every allowlisted id to carry a rank.

### A2.3 What this amendment does NOT decide

- Cost/quality routing for 5.1 (`_lib/model_routing.py` `_ROUTING_TABLE`
  is untouched; debate/arch stay on `claude-opus-5`).
- The `hooks/_lib/tier_policy` `MODEL_ID` enum (AEK tier targets, a
  different contract from availability — it never carried Fable 5 either).
- Automatic model currency (PLAN-176): this amendment is the manual
  ceremony that plan would only DETECT the need for, never perform.
- Sonnet 5 pricing: the same pricing page states the $2/$10 intro rate
  became the STANDARD price (the 2026-09-01 increase to $3/$15 will not
  occur). The dated flip in `audit-telemetry.py`, `ceo-cost.py`,
  `budget-summary.py` and the sticker rows in `cost-table.yaml` /
  `docs/cost-of-operation.md` are therefore stale from today — a
  FOLLOW-UP on free surfaces, deliberately outside this amendment.

The A1.1 prose sentence *"the primary session model is `claude-fable-5`"*
is historical (it predates the ADR-181 pin); the pin above is the truth.
