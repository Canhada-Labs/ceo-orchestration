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
    "claude-opus-5-5",   # ADR-149 Amendment 3 (S357, PLAN-193) — Opus 5.5 joins the floor
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
    # -- Opus 5.5 -- ADR-149 Amendment 3, S357 2026-09-22; APPENDED AT END.
    #    Working set AND VETO floor; the session-default pin. The
    #    fallback stays claude-opus-5, which stays available. --
    "claude-opus-5-5",    # Opus 5.5; dateless id per the models overview
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

## Amendment 3 (S357 — Opus 5.5 joins the working set and the VETO floor and becomes the session pin; fallback unchanged)

> Authored S357 (2026-09-22) under PLAN-193 (W3, `wave-opus55`). Ratified by
> the Owner via AskUserQuestion at S357, verbatim option «Padrão + piso
> VETO»; adopter effort verbatim «xhigh» (OQ-1, 2026-09-22), narrowed by
> «Instalação nova + opt-in (Recomendado)» (OQ-7, 2026-09-23); `ultracode`
> verbatim «Só no override local (Recomendado)» (OQ-6, 2026-09-23); the
> effort of a migrated pin verbatim «Migrar gravando 'high' (Recomendado)»
> (OQ-8, 2026-09-24); the Claude Code floor verbatim «Exigir CC ≥ 2.1.280
> (Recomendado)» (OQ-9, 2026-09-24). Lands
> through the `wave-opus55` sentinel ceremony
> (`.claude/plans/PLAN-193/wave-opus55-approved.md`) as ONE derived pack; the
> exception to the 8-path pack rule is declared in PLAN-193 (OQ-2).

### A3.1 Facts the amendment rests on (Anthropic docs fetched 2026-09-22; Claude Code 2.1.280)

- **API id = `claude-opus-5-5`** — dateless, a pinned snapshot; a date
  suffix must never be appended.
- $4 in / $20 out per MTok; cache writes 1.25x (5 min) and 2x (1 h);
  **cache hits 0.05x the base input price ($0.20/MTok)** — not the standard
  0.1x; batch $2 / $10; the 1M context window at standard price; 128K max
  output; knowledge cutoff June 2026. Fast mode (research preview, Claude
  API only) is $8 / $40 per MTok (pricing page, fetched 2026-09-23).
- Adaptive thinking is always on: a request with thinking disabled or with
  `budget_tokens` is an HTTP 400, and so is a forced `tool_choice`
  (`any` / `tool`).
- Thinking by model (thinking troubleshooting page, fetched 2026-09-23,
  re-read 2026-09-24): `{type: enabled}` with `budget_tokens` is rejected
  on Claude 4.7 and later — Claude Mythos Preview, which supports both
  modes, excepted — deprecated on the 4.6 models, and the only mode of
  Claude 4.5 and earlier; `{type: disabled}` is rejected on the models the page lists
  as always on (the Fable and Mythos 5 models, Mythos Preview, Opus 5.5)
  and accepted where thinking defaults on (Opus 5 at effort `high` or
  below, Sonnet 5) or off (Opus 4.6 to 4.8, Sonnet 4.6).
- Default effort is **medium** (Opus 5 and Fable 5 default to high); the
  model accepts `low` through `max`.
- Claude Code **2.1.280** is the minimum CLI for the id. The model catalog
  inside the 2.1.280 binary (measured S357) lists it with adaptive thinking,
  the `xhigh` effort level, the `[1m]` suffix and `medium` as its default
  effort.
- Older CLIs and settings values (Claude Code CHANGELOG, fetched
  2026-09-24): `xhigh` became an effort level in 2.1.111; 2.1.121 fixed
  invalid legacy enum values in `settings.json` invalidating the entire
  settings file; the 2.1.281 entry that adds `"attribution": false` says
  older CLI versions skip a settings file that holds it. A settings value
  a CLI does not accept can therefore make it skip the whole project
  settings file, every hook registration in it included. Whether a CLI
  before 2.1.111 treats `effortLevel: "xhigh"` that way is not measured
  here.
- `claude-opus-5` stays Active: the change is ADDITIVE.
- Prompt caches are model-scoped (the Claude API reference bundled with
  Claude Code 2.1.280). Claude Opus 5 does not read thinking blocks
  produced by Opus 5.5 — on the Claude API only Fable 5.1 and Mythos 5.1
  read them — and the API drops, unbilled, a block the serving model
  cannot read (preserved-thinking page, fetched 2026-09-23).
- Subagent model and effort (Claude Code sub-agents page, fetched
  2026-09-23): a subagent runs on the per-invocation `model` parameter,
  else the `model` frontmatter of its agent file, else
  `CLAUDE_CODE_SUBAGENT_MODEL` when that names an alias or an id, else
  the main conversation's model; setting the variable to `inherit` is the
  same as leaving it unset (since Claude Code 2.1.196). An agent file's
  `effort` key defaults to inheriting the session effort level.
- Model fallback (Claude Code model-config page, fetched 2026-09-23): an
  availability fallback (the `fallbackModel` chain) lasts the current
  turn only — the next message tries the primary model again — and
  authentication, billing, rate-limit, request-size and transport errors
  never trigger it. A content-classifier fallback re-runs a request that
  Opus 5.5 flags on Opus 5 (biology) or Opus 4.8 (cybersecurity), and
  after it the session continues on the fallback model.
- Effort settings (Claude Code settings reference, fetched 2026-09-23):
  the `effortLevel` key takes `low`, `medium`, `high` or `xhigh`; `/effort`
  saves a level per model under `modelSettings` in user settings; across
  settings files the highest-precedence file that sets a level for a model
  decides (local over project over user), and a top-level `effortLevel` in
  project, local or managed settings applies to every model, while one in
  USER settings does not apply to Opus 5.5. A session resolves its level in
  this order (Claude Code model-config page, fetched 2026-09-23): an
  explicit choice (`CLAUDE_CODE_EFFORT_LEVEL`, `--effort`, `/effort` in
  the session), then the settings (a level saved for the model, or an
  `effortLevel` key), then the model default, which an organization's
  default effort replaces when the session runs the organization default
  model; `ultracode` runs the session at `xhigh` over `effortLevel` and
  `modelSettings`.
- API rate limits (rate-limits page, fetched 2026-09-23): Claude Opus 5.5
  and Claude Opus 5 each have a separate rate limit, outside the combined
  limit of the Opus 4.x ids. The prices above (input, output, both cache
  writes, the 0.05x cache hit, batch) were re-read on the pricing page the
  same day, unchanged.

### A3.2 Decision

1. `AVAILABLE_MODELS_WORKING_SET` gains `claude-opus-5-5` **at the end**
   (A1.1 order rule — no reorder, no removal). The generated
   `availableModels` mirrors follow via `generate-available-models.py`;
   every independent mirror bound by `test_adr149_validator_parity.py`
   carries the same append in the same patch.
2. `VETO_FLOOR_ALLOWED` — the base Decision block and
   `agent_frontmatter.VETO_FLOOR_ALLOWED`, set-equal by test — gains
   `claude-opus-5-5`. Membership makes the id ELIGIBLE to render a VETO; it
   migrates no agent file: every `veto_floor: true` agent file keeps its
   `model: claude-fable-5` pin. (A2.2 item 2 states a count of those files
   that does not match the tree it was written against; the count there is
   a known stale claim, and the class is named here by its shape instead.)
3. `FALLBACK_MODEL_CHAIN` is **unchanged** (`claude-opus-5`).
4. The session-default `model` pin moves from `claude-opus-5` to
   `claude-opus-5-5` in `.claude/settings.json`,
   `templates/settings/settings.base.json` and the GENERATED
   `templates/settings/settings.user.json`. A2.2 item 4 is superseded.
5. Effort (Owner OQ-1, verbatim «xhigh»; OQ-7, verbatim «Instalação nova +
   opt-in (Recomendado)»): the base template — and through its derivation
   the user template — carries top-level `effortLevel: "xhigh"`, so a NEW
   install ships it. In project scope the key applies to every model of
   the session and outranks a level a developer saved with `/effort` in
   user settings; a developer keeps a personal level in
   `.claude/settings.local.json`, which outranks the project file (A3.1).
   The key takes `low` through `xhigh`; `max` is not one of its values.
   The dogfood `.claude/settings.json` carries the same key — a decision
   of the authoring lane, not an Owner option: the dogfood takes the shape
   of a new maintainer install. No committed settings file carries `ultracode`
   (Owner OQ-6, verbatim «Só no override local (Recomendado)»): it stays in
   an operator's untracked local overlay, and a test keeps it out of the
   three committed files.
6. `scripts/upgrade.sh`, T5.4 table: the `availableModels` `superseded` list
   gains the 7-id array that every release from v1.4.0-rc.1 to the last one
   before this amendment shipped.
   TOP-LEVEL scalar leaves gain the same `superseded` semantics through ONE
   generic branch. This is the second occurrence of "a shipped baseline read as
   adopter-customized" (A2.2 item 5 was the array occurrence), so the cure
   is the branch, not an Opus special case: `model` declares
   `superseded: ["claude-opus-5"]` (the pin every release from v1.2.0-rc.1
   to the last one before this amendment shipped; a test walks the release
   tags a checkout holds and reads the shape each one shipped), and a leaf
   may declare `requires_member_of` — the C6 guard as
   data, generic over the array leaves of the table (the gate reads the
   value that array leaf resolved to earlier in the same pass): `model`
   migrates only when the new pin is an EXACT member of the
   effective `availableModels` — deliberately stricter than Claude Code,
   which admits an id by segment prefix (A3.3), so the warning names an
   inexact list, not a harness rejection. The new scalar leaf `effortLevel` is the
   first OPT-IN leaf (`opt_in: true` plus a `cost_note`): an existing
   install receives it only when the operator passes
   `--adopt-setting effortLevel`; without the flag the upgrade leaves the
   key absent and prints a named warning that carries the cost note and
   the flag. An adopter value is never overwritten, with or without it.
   An opt-in leaf may also declare `on_migrate_of`: a value it takes when
   another scalar leaf, walked earlier in the same pass, MIGRATEs away from
   a named value while this leaf is absent (or null) and the operator did
   not opt in. `effortLevel` declares `high` for a `model` that migrates off
   `claude-opus-5` (Owner OQ-8, verbatim «Migrar gravando 'high'
   (Recomendado)»): `high` is the Opus 5 default and medium the Opus 5.5
   one (A3.1), so a migrated install that set no level keeps the effort
   its pin ran at where no other source sets a level (A3.4). That write is
   a MIGRATE line followed by a REVERT line (delete the key) and a note
   that names the opt-in `xhigh`. A SET of the pin (a file without one)
   writes no `effortLevel`, and `xhigh` reaches an existing install only
   through the flag.
   A leaf may also carry a `notice`, printed whenever the leaf is written:
   `model` carries the Claude Code 2.1.280 floor of the new pin. Every
   MIGRATE line, in a dry run too, is followed by a `REVERT:` line — for
   a scalar value, the `.claude/settings.local.json` entry that keeps the
   previous value (local settings override the project file, and
   `upgrade.sh` never writes that file); for an array leaf or a hook
   registration, the pre-migration backup (`availableModels` and hook
   registrations merge across settings scopes, so a local entry cannot
   take a migrated value back out; `fallbackModel` is replaced wholesale
   by a higher scope, and the backup is what restores the project file
   itself). A dry run writes no backup, and its `REVERT:` line says so. An
   apply run writes the backup before anything else and treats it as a
   precondition: when the backup cannot be written the migration is
   skipped with a named note and the file is left as it was. Every exit
   of the migration that leaves the file unmigrated — the backup that
   cannot be written, `python3` missing, and the helper that fails (an
   unparseable file, an atomic write that fails, any other non-zero
   exit) — names the command that re-runs the migration alone, built by
   ONE routine that carries every operator flag deciding what the
   migration reads or writes, or whether it runs: `--adopt-setting`,
   `--allow-old-claude-code`, `--pin` and `--dry-run`, with the target
   and the `--pin` value quoted for the shell (rail round 3 of the wave;
   Owner OQ-10). The
   migration writes the file with `ensure_ascii=False`: characters outside
   ASCII stay as written instead of being escaped, so a file in the
   templates' own format keeps every line outside the migrated leaves
   byte-identical except the line just before a key the migration ADDS:
   a new key goes at the end of its object, and that line gains a
   trailing comma (tested on the base template that v1.4.1-rc.1 shipped, where the
   pin migration appends `effortLevel` after the last key, and on the
   current template); a file holding a value
   UTF-8 cannot encode (a lone surrogate) is written in the escaped form
   instead, so it still migrates. A file that an earlier release's
   migration wrote holds those characters escaped; its first migration
   under this writer rewrites every such line once, in the unescaped form.
7. `_lib/adapters/live/claude.py` inverts its thinking default. Class cure,
   second occurrence: the adaptive-only prefix list never gained
   `claude-opus-5` or `claude-sonnet-5`, so `CEO_EFFORT_OVERRIDE` sent them
   the legacy `budget_tokens` shape, which Claude 4.7 and later reject with
   an HTTP 400 (A3.1). A CLOSED list now names the pre-4.6 ids, whose only
   thinking mode is the legacy `{type: enabled, budget_tokens}` shape; they
   keep that path as before, in their first-party, Bedrock and Vertex
   (`@YYYYMMDD`) spellings. An entry of the list matches its exact id, and
   that id followed by ONE dated snapshot segment (`-YYYYMMDD`, or the
   Vertex `@YYYYMMDD`) and then a Bedrock version suffix (`-vN`, `-vN:M`),
   each optional; an id that extends an entry by any other `-` segment is
   a different id. One entry is a family: every id that starts with
   `claude-3-` (the Claude 3 generation); the bare dated ids of the 4.0
   generation (`claude-opus-4-YYYYMMDD`, `claude-sonnet-4-YYYYMMDD`) match
   only with their date. Every other id is adaptive-only,
   so the next model id is safe by default. The same list decided a caller's
   `{type: disabled}`: the adapter dropped it on every adaptive-only id,
   which on a model whose thinking defaults ON (Opus 5, Sonnet 5) would
   now turn thinking on in silence. It now drops it only on the ids it
   lists as always on (Fable 5 and 5.1, Mythos 5 and 5.1, Mythos Preview
   and Opus 5.5 — the models the thinking page lists as always on),
   matched by the same rule, where the API rejects it, and sends it as
   given everywhere else; an always-on id it does not list answers with
   an HTTP 400, never with silent thinking.
8. `tier_policy_cli/learn.py` `_tier_rank` places `claude-opus-5-5` strictly
   above `claude-opus-5` and strictly below `claude-fable-5`. The ladder is
   tier-major; the ranks are renumbered, never tied, so a move from Fable 5
   to Opus 5.5 is a `demote`. `ceo-tier-policy owner-sign` records in the
   sigchain the action `learn._direction` computes over this ladder. It
   used to read the order of `VALID_MODEL_IDS`, an allowlist in ADR order
   that is not a tier order (`claude-fable-5` is its first entry): a move
   from Fable 5 to Opus 5 already signed as `promote`, and appending
   `claude-opus-5-5` would have signed a move from Fable 5.1 to Opus 5.5
   as `promote` too. A model id the ladder does not rank, or the same
   model on both sides, is refused (exit 2) before anything is signed; a
   test requires a rank for every `VALID_MODEL_IDS` entry, no two equal.
9. `audit_log._ADR_052_ROLE_TO_MODEL["general-purpose"]` follows the session
   pin (`claude-opus-5-5`): that row states that the mitigated rail inherits
   the CEO model. It stays a POLICY value, not an observation.
10. `_lib/effective_config.py` folds ONE trailing `[1m]` tag before the env
    tamper check compares a model value with the allowlist: the tag selects
    the 1M context window, so `claude-opus-5-5[1m]` in `ANTHROPIC_MODEL` or
    in an `ANTHROPIC_DEFAULT_*` key is the floor member `claude-opus-5-5`.
    Only that exact tag folds; any other suffix is compared as written, so
    a value the check cannot classify stays flagged.
11. Claude Code floor (Owner OQ-9, verbatim «Exigir CC ≥ 2.1.280
    (Recomendado)»): this release declares Claude Code 2.1.280 as its
    minimum (`SUPPORT.md`). The settings it ships carry values an older CLI
    may not accept — the `claude-opus-5-5` pin, whose documented minimum is
    2.1.280, and `effortLevel: "xhigh"`, not an effort level before
    2.1.111 — and a
    settings value a CLI does not accept can make it skip the whole project
    settings file, hook registrations included (A3.1). `scripts/install.sh`
    and `scripts/upgrade.sh` therefore read `claude --version` before an
    install or an upgrade writes anything. What exits before the check is
    not gated, by shape: every mode that delivers no framework file —
    `--help` in both scripts, the table print `--print-settings-baselines`
    of `upgrade.sh`, and the reviewer-harness lifecycle modes of
    `install.sh` (`--arming-check`, which reads an existing wiring, and
    `--uninstall`, which removes one, for whichever harness they name,
    `codex` or `grok`) — and every refusal of an argument, a missing target
    or a failed preflight. A CLI below the floor is refused (exit 6) unless
    the operator passes `--allow-old-claude-code`, which continues with a
    named warning; no `claude` on PATH (CI, a headless host) or a version
    the scripts cannot read is a named warning and the run continues; a dry
    run names the refusal and goes on previewing. The probe runs with stdin
    from `/dev/null`, in the background, polled against a wall limit of 10
    seconds; at the limit it stops the probe's process group and the
    version is unreadable (a named warning, as above). The version is read
    only from the first output line that names `(Claude Code)`, so another
    program's version printed first is never read, and a version with
    anything after its three numbers (a pre-release such as
    `2.1.280-beta.1`) counts as below the floor. The check is one shell
    block, byte-identical in the two scripts; a test holds the two copies
    equal and ties their floor to the `notice` of the `model` leaf and to
    the `SUPPORT.md` row.

### A3.3 Earlier text, amended by shape

- A1.1 calls the floor "the only models permitted to render a VETO
  verdict". On agent-definition (native) dispatch `check_agent_spawn`
  checks the `model:` of a VETO-role agent file only when the role's slug
  (such as `security-engineer`) appears in the spawn's description or
  prompt — it does not read `subagent_type` (A3.4) — and a per-invocation
  `model` parameter outranks that file (A3.1) with no gate observing it:
  the file pin binds only an invocation that passes no model. Mitigated
  dispatch (`subagent_type: general-purpose`, the default route of some VETO
  archetypes in `.claude/team.md`) and Workflow agents, when passed no
  model, run on the model the session runs at that moment: the pin
  `claude-opus-5-5`, a floor member, by default — or whatever a `/model`,
  `--model` or `ANTHROPIC_MODEL` choice, or a content fallback that
  persists for the session, selected, which may be a model outside the
  floor. `CLAUDE_CODE_SUBAGENT_MODEL=inherit`, which the shipped settings
  carry, is the same as leaving that variable unset (A3.1); it is not what
  makes those spawns inherit. Which model actually served a given
  mitigated spawn is not measured here.
- A1.1 (the rationale of `FALLBACK_MODEL_CHAIN`) and A1.3 clause (c)
  describe the content-classifier fallback as Fable 5 falling back to the
  default Opus model. Since Claude Code 2.1.219 that fallback goes by
  category, and the session pin is itself a source (A3.1): a request Opus
  5.5 flags re-runs on Opus 5 or Opus 4.8 — both floor members — and the
  session then STAYS on that model, while an availability fallback lasts
  one turn. Clause (c) covers both switches. Rationale (ii) of A1.1 — that
  the availability fallback and the refusal fallback land on the same
  model — no longer holds for the pin: a cybersecurity flag re-runs on
  Opus 4.8 while `fallbackModel` is `claude-opus-5`, so the two can land
  on different floor members.
- A2.1 says every model but Fable 5.1 keeps the standard 0.1x cache-read
  rate and that `budget-summary.py` is the ONE cost surface that prices
  cache reads. The pricing page (re-read 2026-09-24) prices Mythos 5.1
  cache hits at 0.025x too, a model outside the working set that no cost
  surface here prices; Opus 5.5 is a further exception (0.05x, A3.1), and
  `ceo-cost-transcripts.py` prices cache reads too, with its own per-model
  multiplier table, which `test_model_fleet_presence.py` holds equal to
  the one in `budget-summary.py`.
- A1.1 calls the working set "the set of model ids the harness may select
  on ANY surface". Claude Code 2.1.280 matches `availableModels` entries by
  segment PREFIX (measured S357): an entry admits every id that extends it
  by a `-` segment (`claude-opus-5` already admitted `claude-opus-5-5`;
  `claude-fable-5` admits `claude-fable-5-1`). Where the framework DECIDES
  admission — the spawn gate, the env tamper check (after the one `[1m]`
  fold of A3.2 item 10) and the generator `--check` — it compares EXACT
  ids; advisory telemetry classifiers may match by model-family prefix
  (A3.4). The working set is therefore the exact list
  the framework ratifies and, where no managed settings define
  `availableModels`, a lower bound of what the harness admits (a managed
  list alone applies, and project, local or user entries cannot extend it);
  `enforceAvailableModels` does not redirect a harness default that extends
  an allowed entry, and the explicit `model` pin is what fixes the session
  default.
- A1.4 names the env tamper tripwires as compensating visibility. They read
  the FIRST `frozenset` block of this file — the VETO floor — so adding a
  floor member also widens the set of accepted `ANTHROPIC_MODEL` /
  `ANTHROPIC_DEFAULT_*` values. `install.sh` delivers only
  `.claude/adr/README.md` from this directory, so in an adopter the check
  finds no allowlist and runs degraded (breadcrumb, no finding).

### A3.4 Declared residuals (not cured here)

- **Subagent effort is not pinned.** The spawn gate blocks `/effort` tokens
  in spawn prompts and no agent file carries an `effort` key, so a
  subagent inherits the session effort level — documented (A3.1), not
  measured on Claude Code 2.1.280, and not measured for Workflow agents. A
  VETO verdict served by `claude-opus-5-5` therefore runs at the session
  level, which is the model default MEDIUM wherever no level is set. The
  Owner kept the id in the floor; a measurement, or an effort floor in the
  agent frontmatter, is a FOLLOW-UP.
- **The pin and the fallback now differ — a new failure mode.** Until this
  amendment they were the same model; now an availability fallback
  CHANGES the serving model (`claude-opus-5-5` to `claude-opus-5`) for the
  turn in which it fires, and the next message returns to the pin (A3.1).
  Both are floor members, so A1.3 clause (a) holds; clause (c) now
  describes a switch that can actually happen, and no hook records it.
  Each switch can have a price: prompt caches are model-scoped, so the
  `claude-opus-5` turn writes to its own cache the part of the context
  that Opus 5 holds no live cache for — the whole context when it holds
  none — at its cache-write price ($6.25/MTok for the 5-minute cache,
  1.25x its $5 input; a cache entry lives five minutes, or an hour with
  the 1-hour cache, counted from the start of the last request that read
  or wrote it, per the prompt-caching page fetched 2026-09-23), and the
  return to the pin
  writes again, at the Opus 5.5 price, what the pin's cache lost
  meanwhile. Opus 5 does not read the Opus 5.5 thinking blocks, so that
  turn runs without them, and a dropped block changes the cached prefix
  from its position onward (same page). A rate-limit error never
  triggers the switch (A3.1), so the fallback does not relieve an Opus 5.5
  rate limit. On the API the two models have separate rate limits; how a
  Claude Code subscription quota counts the two models is not stated in
  those sources and is not measured here.
- **The effort level the pin migration writes is a project setting.**
  When the upgrade migrates the shipped pin `claude-opus-5` to
  `claude-opus-5-5` in a project file that sets no level, it writes
  `effortLevel: "high"` (A3.2 item 6, Owner OQ-8). Like any top-level
  `effortLevel` in project settings, that key applies to every model of
  the session and outranks the model default, an organization's default
  effort, and a level a developer saves with `/effort` in user settings
  (A3.1); a personal level belongs in `.claude/settings.local.json`. A
  top-level `effortLevel` in a developer's user settings, which applied to
  Opus 5, does not apply to Opus 5.5 (A3.1); there the project `high` now
  decides. An explicit choice (`CLAUDE_CODE_EFFORT_LEVEL`, `--effort`,
  `/effort` in the session), `ultracode` and a `maxEffortLevel` cap still
  act over it. An `effortLevel` already in the project file is preserved,
  and it keeps applying to Opus 5.5. An install whose file had no pin (the
  pin is SET, not migrated) receives no `effortLevel`: where no other
  source sets a level it runs Opus 5.5 at its default, medium. An install
  whose pin is custom, or whose allowlist withholds the new pin, keeps its
  pin and receives no `effortLevel`.
- **User-ceremony installs.** The settings migration does not read the
  install ceremony, a known-open condition that
  `docs/UPGRADE-PROCEDURE.md` routes through `--no-settings-migrate`. An
  operator who follows that route receives neither the new pin nor
  `effortLevel` and sets them by hand; an `--adopt-setting` passed with
  it is named in a warning and ignored.
- **A downgrade does not migrate back.** No earlier release lists
  `claude-opus-5-5` or the 8-id `availableModels` in its T5.4 table, so an
  earlier release's `upgrade.sh` preserves both as adopter-customized
  (a release before this amendment cannot name them; checked S357 on the
  table of v1.4.1-rc.1, the last tag then). What undoes the migration is the
  pre-migration backup or a revert of the committed upgrade; the
  `.claude/settings.local.json` entry a `REVERT:` line names does not
  change the project file, it overrides the migrated scalar value.
  `upgrade.sh --pin <earlier release>`, run from a newer framework
  checkout, applies the T5.4 table of the RUNNING script, not the pinned
  release's: the revert-then-`--pin` rollback that
  `docs/UPGRADE-PROCEDURE.md` documents migrates the reverted settings
  forward again unless that run passes `--no-settings-migrate`. That
  behaviour predates this amendment.
- **The floor check reads one CLI.** `install.sh` and `upgrade.sh` read
  the `claude` found on PATH when they run (A3.2 item 11); the CLI that
  later opens the project can be another one. With no `claude` on PATH
  they warn and continue, and `--allow-old-claude-code` continues below
  the floor: then the shipped pin and `effortLevel` are the operator's to
  edit (`SUPPORT.md`). What a CLI older than 2.1.280 does with the pin is
  not measured here; the upgrade also prints the floor as the `notice` of
  the `model` leaf whenever it writes the pin. The probe's stop reaches
  its own process group only: a process the CLI moves out of that group
  that keeps the output open still holds the probe.
- **The floor only grows.** Removal stays an Owner-only act (base
  Consequences); this amendment adds no retirement trigger.
- **Advisory classifiers match by family prefix.** A telemetry detector
  of VETO-role spawns served by a non-floor model classifies the logged
  model by its family prefix (`claude-opus-`, `claude-fable-`), so an id
  of a floor family that the floor does not list raises no finding there.
  It decides nothing; the spawn gate, which decides, compares exact ids.
- **A nested scalar leaf has no `superseded` branch.** The generic branch
  of A3.2 item 6 walks top-level keys only. `permissions.defaultMode`
  keeps its own code, which migrates only its old baseline: a value that
  a later table moves to `superseded` there would be read as
  adopter-customized until that leaf joins a generic branch.
- **The native VETO-floor check reads text.** `check_agent_spawn` runs the
  floor check for a VETO role only when the role's slug appears in the
  spawn's description or prompt; a native spawn whose `subagent_type`
  names a VETO agent while its text names no VETO role is not checked
  (A3.3). The gate predates this amendment, which does not change it.
- **`/effort off` does not turn thinking off where it defaults on.**
  When the caller passes no thinking value, `CEO_EFFORT_OVERRIDE=off`
  makes the live adapter omit the thinking parameter, as it did before
  this amendment; on an id whose thinking
  defaults on (A3.1), omitting it leaves thinking on. Turning it off there
  would take an explicit `{type: disabled}` where A3.1 says the model
  accepts one; not changed here.
- **The opt-in native batch path forwards the caller's thinking.** With
  `CEO_NATIVE_BATCH_LIFECYCLE=1`, `_lib/adapters/live/claude_batch.py`
  builds each native batch request with the caller's `thinking` value as
  given; the thinking handling of A3.2 item 7 covers the single-call path
  and the sequential batch fallback, which goes through it. Off by
  default; not changed here.
- **A forced `tool_choice` is passed through.** A3.1 records that a forced
  `tool_choice` (`any` / `tool`) is an HTTP 400 on `claude-opus-5-5`; the
  live adapter's structured-output path sends a caller's `tool_choice` as
  given, and no caller outside the tests passes one (checked S357,
  2026-09-24). A caller that forces one on `claude-opus-5-5` gets that
  400; not changed here.

### A3.5 What this amendment does NOT decide

- Migrating any `veto_floor: true` agent file off `claude-fable-5`.
- `_lib/model_routing.py` `_ROUTING_TABLE` (debate/arch stay on
  `claude-opus-5`), the reviewer default in `check_codex_stop_review.py`,
  and the `hooks/_lib/tier_policy` `MODEL_ID` enum.
- Prices beyond the rate card (A3.1). The same derived patch gives the
  $4/$20 row to `cost-table.yaml` and to every cost-rollup table that
  `test_model_fleet_presence.py` binds to this ADR's working set, and
  0.05x to the two per-model cache-read tables that test holds equal.
  Per-model price tables outside that oracle (Owner-provenance snapshots,
  drift fixtures, research and tournament instruments, the tier-policy
  cost gate) are not changed. The rollups that look a model up by its
  exact spelling do not price the `[1m]`-tagged spelling of
  `claude-opus-5-5`.
- The `upgrade.sh` T3.4 gate that withholds the DirectoryAdded /
  Notification registrations from adopter settings: A3.2 item 11 raises
  the adopter floor to Claude Code 2.1.280 but leaves that gate OFF.
- `SPEC/v1/install-cli.md`: it lists neither `--allow-old-claude-code`,
  nor `--adopt-setting`, nor exit 6. Its exit-code table already lags the
  scripts (it stops at 3, while its own flag table names exits 4 and 5);
  the SPEC is not changed here.
- `CLAUDE.md`, `.claude/team.md` and the CHANGELOG (closeout and release
  surfaces).

The A1.1 sentence on the primary session model and A2.2 item 4 are
historical; the session pin is `claude-opus-5-5` (A3.2 item 4).
