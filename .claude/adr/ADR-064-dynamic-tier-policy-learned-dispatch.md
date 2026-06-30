---
id: ADR-064
title: Dynamic tier policy — learned dispatch with VETO floor hardcode
status: ACCEPTED
date: 2026-04-19
proposed_date: 2026-04-19
accepted_date: 2026-04-19
amended_date: 2026-04-19
deciders: CEO + Owner
related_plans: [PLAN-043, PLAN-032, PLAN-027]
related_adrs: [ADR-052, ADR-055, ADR-063, ADR-002, ADR-005, ADR-058]
blast_radius: L3+
round_1_verdict: 4 ADJUST + 1 SOFT REJECT from security-engineer lifted after 14 P0 + 8 P1 convergent closures landed in Phases 1-5
---

# ADR-064 — Dynamic tier policy — learned dispatch with VETO floor hardcode

> **STAGED — Phase 5 Owner promotion target.** Final canonical path:
> `.claude/adr/ADR-064-dynamic-tier-policy-learned-dispatch.md`.
> Promoted via kernel batch
> `/tmp/plan_043_phase_5_promote_canonical.py` (Owner physical shell;
> see `OWNER-LOCAL-ACTIONS.md` §Phase 5).
>
> This ACCEPTED-flip supersedes the DRAFT at
> `.claude/plans/PLAN-043/adr-drafts/ADR-064-dynamic-tier-policy-DRAFT.md`.
> Content is the union of the DRAFT body + all Round 1 Phase 0
> amendments (14 P0 + 8 P1 convergent closures), verified green
> across PLAN-043 Phases 1–4 (191 new tests, 100% VETO-floor mutation
> kill, fail-open fallback demonstrated via test_apply integration).

## Status

**ACCEPTED** — all 14 C-P0 + 8 C-P1 closures landed via
`.claude/scripts/tier_policy_cli/` package + tests. Accepted
2026-04-19. (Renamed from `tier_policy/` to `tier_policy_cli/` per
PLAN-076 fork (f) for Python-importable underscore form, S89.)

> **Namespace qualification (PLAN-076 fork (f), S89):** the symbol
> `VETO_HARDCODE` exists at TWO different layers with DIFFERENT
> shapes and DIFFERENT semantics — both are intentional:
>
> - `_lib/tier_policy/_constants.VETO_HARDCODE` :
>   `Mapping[str, FrozenSet[str]]` (role → task_types). Advisory
>   floor consumed by PLAN-071 `task-route.py` for role-task-type
>   coherence. **6 spec-named roles** via `EXPECTED_VETO_FLOOR_UNION`
>   (union with `_lib/agent_frontmatter.VETO_FLOOR_ROLES`).
>
> - `tier_policy_cli/_constants.VETO_HARDCODE` (this ADR's binding) :
>   `Final[Dict[str, str]]` (role → model_id). Hard binding floor
>   consumed by `learn.py` + `apply.py` for ADR-052 VETO-class agent
>   model-tier protection. **2 hardcode roles** (`code-reviewer`,
>   `security-engineer` → `claude-opus-4-7`).
>
> The two concepts are NOT duplicates and MUST NOT be unified
> without an Owner-signed ADR amendment. Codex MCP cross-LLM gate
> review (PLAN-076 fork (f) call #1) confirmed the semantic split
> is the correct fork; premature unification would erase one of
> the two distinct floors.

## Context (summary)

ADR-052 established static three-tier dispatch. ADR-063 introduced the
tournament framework that produces empirical win-rate-per-task-type ×
model data. Prior to ADR-064, no mechanism translated tournament
signals into policy updates.

**ADR-064 closes the loop** with a policy artifact at
`.claude/tier-policy.json`, an HMAC-chained Owner-signature log at
`.claude/tier-policy.json.sigchain`, a statistical power gate
(n≥30/cell + gap_pp≥25pp), asymmetric promote-auto/demote-signed with
cost-envelope gate, cooldown (≤1 change per role per quarter), and
VETO floor hardcoded outside policy reach.

**Implementation:**
- `.claude/scripts/tier_policy_cli/` package (renamed from
  `tier_policy/` per PLAN-076 fork (f), S89; underscore form is
  Python-importable via `from tier_policy_cli import ...`):
  - `_constants.py` — `VETO_HARDCODE` (role → model_id binding floor;
    distinct from `_lib/tier_policy/_constants.VETO_HARDCODE` which
    is role → task_types advisory floor) + frozen SHA256
  - `_types.py` — dataclasses + `MODEL_ID` Literal + `VALID_MODEL_IDS`
    tuple + `ROLE_TO_TASK_TYPES`
  - `_agent_frontmatter.py` — adopter override helper
  - `loader.py` — schema-validated artifact load + fail-open fallback
  - `learn.py` — tournament aggregator + statistical gate + VETO check
  - `apply.py` — dispatcher with filelock + cost gate + sigchain
  - `cli.py` — `ceo-tier-policy` with 9 subcommands
  - `check_tier_policy_staged.py` — PreToolUse VETO hook (Phase 5
    promotion to `.claude/hooks/check_tier_policy.py`)
- `.claude/hooks/_lib/audit_hmac.py` — `verify_chain` library function
  (Phase 0.5 extraction)
- `SPEC/v1/tier-policy.schema.md` — canonical schema contract
- `.github/workflows/tier-policy.yml` — monthly notify-only CI
- 191 tests (loader 29 + types 45 + agent_frontmatter 1 + constants 7 +
  learn 37 + learn_mutation 14 + apply 24 + cli 21 + adversarial 11 +
  hook 10 + other 2)

## Decision (canonical)

Adopt Option D — asymmetric gate architecture:

1. **Policy artifact** at `.claude/tier-policy.json` with schema
   published at `SPEC/v1/tier-policy.schema.md`.
2. **Hardcoded VETO floor** via `VETO_HARDCODE` single-source constant
   in `_constants.py` + `VETO_HARDCODE_APPLY` independent literal
   inside `apply.py` + structural PreToolUse hook
   `check_tier_policy.py` — three-layer defense per C-P0-3.
3. **Statistical power gate** — n≥30 per (role × task-type) cell AND
   gap_pp≥25pp MIN across cells (C-P0-1 amended from 15pp undersized).
4. **3-way asymmetric gate** per C-P0-4:
   - promote + small delta → auto-apply
   - promote + large delta → Owner-signature-required (cost-gated)
   - demote → Owner-signature-required
5. **Cooldown** — 90 days per role via `last_change_by_role` O(1)
   index (F-PERF-P1-1).
6. **HMAC verification** on input reports via
   `_lib/audit_hmac.verify_chain()` (Phase 0.5 library API per C-P0-7);
   separate tier-policy key (F-SEC-P0-2).
7. **Two-factor kill-switch** — env `CEO_TIER_POLICY_ENABLE=1` +
   Owner-signed sentinel (C-P0-12 supply-chain hardened); both factors
   required; CI flag `CEO_TIER_POLICY_CI=1` substitutes sentinel with
   fork-safety assertion; master override `CEO_SOTA_DISABLE=1`.
8. **Owner-signature chain** with git-commit-signature attribution
   binding via `.claude/tier-policy.owners.txt` allowlist +
   `git commit -S` same-transaction (C-P0-11). Sigchain entries carry
   `chain_length` + `prior_commit_sha` (C-P0-5 anti-truncation +
   anti-rollback).
9. **Adopter override preservation** via `_agent_frontmatter.py` helper
   (C-P0-10 Python API, replaces Bash upgrade.sh re-use claim).
10. **ADR amendment scaffold emitter** in apply.py emits draft
    `.claude/plans/PLAN-043/adr-drafts/ADR-NNN-tier-demotion-<role>.md`
    on demote with role allowlist + NNN monotonic + html.escape
    (F-SEC-P1-1).
11. **Sigchain schema** — each entry has chain_length + prior_commit_sha;
    artifact carries sigchain_tip_length; verify subcommand
    cross-checks (C-P0-5).
12. **Audit event count canonical 8** (C-P0-8) + cost-gated 9th;
    staged via emit_generic fail-open drop until Owner kernel batch
    `/tmp/plan_043_audit_emit_batch.py` applies.
13. **Full model IDs throughout** (C-P0-9); `MODEL_ID` Literal type +
    `VALID_MODEL_IDS` tuple for runtime checks.
14. **Schema versioning** — `policy_schema_version` field (C-P1-6) +
    `cli migrate` subcommand.
15. **CI notify-only Option B** (C-P0-14) + `0 7 1 * *` 2h-buffer
    schedule (C-P0-13).
16. **Sentinel supply-chain hardening** (C-P0-12) — Owner-signed
    content `sha256(nonce) + git_commit_sha`, 0600 perms, 0700 parent,
    symlink detection, owner UID check.

## Kill-switch matrix

| Flag | Effect | Default |
|---|---|---|
| `CEO_SOTA_DISABLE=1` | Master disable all SOTA features | unset |
| `CEO_TIER_POLICY_ENABLE` | Factor 1 — apply path | `0` |
| `~/.ceo-orchestration/tier-policy/.enabled` | Factor 2 — sentinel | absent |
| `CEO_TIER_POLICY_CI=1` | Sentinel substitute (fork-safety gated) | unset |
| `CEO_TIER_POLICY_DRY_RUN=1` | No-writes derive + diff | unset |
| `CEO_TIER_POLICY_MAX_PROMOTE_DELTA_USD` | Cost-gate threshold | `20` |
| `CEO_TIER_POLICY_MAX_RUNS` | Rolling window | `12` |
| `CEO_TIER_POLICY_REPORT_MAX_AGE_DAYS` | Freshness filter | `365` |
| `CEO_TIER_POLICY_COOLDOWN_DAYS` | Cooldown override | `90` |
| `CEO_TIER_POLICY_COOLDOWN_OVERRIDE` | SP-chain-id bypass | unset |

## Audit event registry (via Owner kernel batch)

9 new action types — registered via
`/tmp/plan_043_audit_emit_batch.py` Owner-signed kernel execution:

- `tier_policy_derived`
- `tier_policy_promote_applied`
- `tier_policy_demote_requested`
- `tier_policy_rejected`
- `tier_policy_hmac_verify_failed`
- `tier_policy_adopter_override_respected`
- `tier_policy_killswitch_triggered`
- `tier_policy_dry_run_complete`
- `tier_policy_promote_cost_gated` (C-P0-4 3-way gate signal)

## Consequences

### Positive (+)

- Closes tournament → dispatch feedback loop with statistical honesty.
- 3-layer VETO floor defense (hardcode + independent literal + hook).
- PLAN-021 adopter override contract preserved end-to-end.
- Sigchain + git-signed commits make every tier change forensically
  reconstructable.
- Cost-envelope gate prevents silent DoS-by-budget-exhaustion (C-P0-4).
- Fail-open fallback to ADR-052 baseline on any corruption (ADR-005).
- ADR-064 is the framework's single empirical self-calibration
  differentiator — tournament produces evidence, tier-policy
  translates it into runtime dispatch via auditable chain.

### Negative (−)

- 9 audit event strings + 1 new PreToolUse hook + 2 canonical-edit
  guard additions (`.claude/tier-policy.json` + `.sigchain`) = larger
  governance surface.
- Adopter must populate `.claude/tier-policy.owners.txt` + generate
  SSH/GPG key for git commit signing before demote path unlocks.
- Policy learning requires ≥3 tournament runs accumulated (≈3 months
  at monthly cadence) before first recommendation fires.

### Neutral / Mitigated (~)

- Two-factor kill-switch defaults OFF; adopters opt-in per
  `install.sh --with-tier-policy`.
- Dry-run mode covers preview-before-commit workflow.
- CI is notify-only (Option B) — no auto-commit surprise; Owner
  applies locally.

## Threat model

Threats T1–T11 (fully enumerated in DRAFT; preserved in ACCEPTED):

- T1 Learned policy silently revokes VETO floor → 3-layer defense
- T2 Forged tournament report → HMAC verify on input
- T3 Adopter customization overwritten → diff-detect helper
- T4 Oscillation from noisy runs → cooldown + power floor
- T5 Direct policy JSON edit → canonical-edit guard + sigchain
- T6 Kill-switch bypass → two-factor + fork-safety + low-level recheck
- T7 Cost runaway via promote-auto → cost-envelope gate (C-P0-4)
- T8 Sigchain second-preimage → HMAC-SHA256 128-bit resistance
- T9 Sigchain tail-truncation → `sigchain_tip_length` in artifact
- T10 Tournament report replay → `REPORT_MAX_AGE_DAYS` freshness filter
- T11 Supply-chain sentinel attack → Owner-signed content + symlink
      detection + owner UID check + 0700 parent

## Cost-envelope rules

The mechanical artifacts in this ADR (`tier-policy.json` + sigchain +
`check_tier_policy.py` PreToolUse hook + 9 audit events + statistical
power gate) define WHAT the framework enforces. The cognitive layer
that teaches agents HOW to reason about tier choices, per-plan token
budgets, burn-rate monitoring, and cost-envelope escalation lives in
the companion skill **`core/llm-routing-and-finops`** (shipped in
PLAN-074 Wave 1b, 2026-05-06+).

The skill is the canonical operator manual for:

- The full role-to-model floor table (HARDCODE and advisory tiers,
  including Wave 1c VETO-adjacent expansion candidates such as
  `incident-commander` and `identity-trust-architect`).
- The plan-frontmatter `budget_tokens:` + `tier_mix_estimate:` +
  `calendar_buffer_days:` contract that the LLM FinOps Architect
  reviews at Phase 0.
- Burn-rate math adapted from Google SRE Handbook ch. 5 §Multi-Window,
  Multi-Burn-Rate Alerts (14.4× / 6× / 1.5× escalation thresholds
  applied to per-plan token consumption).
- The Routing Decision Protocol Q1-Q5 flowchart and the Sonnet-
  downgrade carve-out three-condition gate for advisory-floor roles.
- WRONG / CORRECT dispatch examples and six recurring anti-patterns
  (parent-inheritance trap, all-Opus default, speculative Haiku,
  future-proofing creep, missing-budget plan, advisory-floor drift).

Any future amendment to ADR-064 §Decisions or the kill-switch matrix
that introduces new cost-envelope rules requires a parallel amendment
to the skill body so the mechanical and cognitive layers stay in sync.

## Open items (post-ACCEPTED; tracked for future ADRs)

- **ADR-??? Ed25519 asymmetric signing** — deferred until Owner
  hardware key infra stood up (C-P0-11 §future).
- **ADR-??? Sigchain rotation policy** — cli `sigchain-rotate` stub
  ships in MVP; full flow (archive + reseed + rekey sequence)
  deferred to operational emergency.
- **ADR-??? Policy schema v1.1** — reserved for
  `cooldown_override: {role: sp_chain_id}` + governance_diff_hash
  once empirical signals are observed.

## Related

- ADR-052 (static baseline); ADR-055 (HMAC chain); ADR-063
  (tournament producer); ADR-002 (stdlib-only); ADR-005 (fail-open);
  ADR-058 (brainstorm gate — SKIPPED per L3 well-precedented).
- PLAN-043 (implementation plan); PLAN-032 (tournament); PLAN-027
  (Wave B parent).
- **`core/llm-routing-and-finops` SKILL** (PLAN-074 Wave 1b) — the
  cognitive-layer doctrine that complements this ADR's mechanical
  artifacts. The skill is the operator manual for plan-authoring
  cost decisions; this ADR is the runtime-enforcement contract.
- PLAN-074 (skill / agent expansion umbrella; Wave 1b ships the
  cognitive layer for cost governance).

## Enforcement commit

`a82e36f48eb8` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
