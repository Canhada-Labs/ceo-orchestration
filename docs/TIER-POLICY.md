# Tier Policy — Adopter Guide

> **PLAN-043 / ADR-064.** `ceo-orchestration` includes an **opt-in
> dynamic tier selector** that consumes HMAC-verified tournament
> reports (PLAN-032 / ADR-063) and emits per-role tier recommendations
> (`model:` field updates in `.claude/agents/<slug>.md`) under strict
> VETO-floor + statistical-power + cost-envelope gates.
>
> The feature is **OFF by default**. No policy mutations happen until
> you (a) populate an owners allowlist, (b) generate a signed sentinel,
> and (c) run `ceo-tier-policy apply`.

## TL;DR

```bash
# 1. One-time setup (per adopter repo).
echo "your-git@email.com" > .claude/tier-policy.owners.txt
ceo-tier-policy enable                      # writes signed sentinel

# 2. Optionally enable env factor in settings.json.
# "env": { "CEO_TIER_POLICY_ENABLE": "1" }

# 3. Monthly loop (manual or via .github/workflows/tier-policy.yml).
ceo-tier-policy derive > recommendations.json
cat recommendations.json                    # human review
ceo-tier-policy apply --dry-run             # preview diff
ceo-tier-policy apply                       # promote-auto fires;
                                            # demotes emit
                                            # "owner-sign needed"

# 4. For demotes + cost-gated promotes:
ceo-tier-policy owner-sign \
  --agent performance-engineer \
  --from-tier claude-sonnet-4-6 \
  --to-tier claude-haiku-4-5-20251001 \
  --sp-chain-id SP-NNN-$(openssl rand -hex 4)
```

## When does policy engage?

- **Minimum 3 tournament runs accumulated** in `benchmarks/tournament-*.jsonl`
  (HMAC-verified). Below this floor, `derive` short-circuits with an
  empty recommendation set + `tier_policy_insufficient_fresh_reports`
  audit event.
- **Statistical power floor** — each (role × task-type) cell must have
  **n ≥ 30** non-errored samples AND **gap_pp ≥ 25** percentage points
  vs the current tier's win-rate. Matches what `n=30` actually detects
  at 80% power per the SE analysis in ADR-063 Round 1.
- **Cooldown** — one tier change per role per quarter (90 days
  default; override via `CEO_TIER_POLICY_COOLDOWN_DAYS`).

## Owner-signature workflow (demotions + cost-gated promotes)

Two flows require Owner signature:

1. **Demote** — Opus → Sonnet / Sonnet → Haiku (any magnitude). Cost
   goes down; quality goes down. Owner reviews evidence + signs.
2. **Cost-gated promote** — Haiku → Sonnet / Sonnet → Opus where
   projected monthly cost delta **exceeds
   `CEO_TIER_POLICY_MAX_PROMOTE_DELTA_USD`** (default $20). Cost
   goes up faster than the cap allows; Owner reviews + signs.

Both flows emit `tier_policy_demote_requested` with CLI instructions;
no frontmatter is written. Once signed via `ceo-tier-policy owner-sign`,
the sigchain entry lands + the next `ceo-tier-policy apply` promotes
the agent.

**Owner signature gate** (C-P0-11):

- `git config user.email` MUST be present in
  `.claude/tier-policy.owners.txt` (one email per line, lines starting
  with `#` are comments).
- `owner-sign` wraps the sigchain append in a `git commit -S` (signed
  commit). If your key is not loaded (no gpg-agent / ssh-agent), the
  sign aborts with a non-zero exit; fix your signing config + retry.
- `sp_chain_id` format: `^SP-\d{3}-[a-f0-9]{8}$` (convention: `NNN` =
  monotonic `.claude/plans/SP-NNN-*.md`; 8 hex chars = random suffix).

## Adopter override (PLAN-021 contract preserved)

If you have manually edited `.claude/agents/<slug>.md model:` for your
specific workflow, `tier_policy.apply` detects the divergence vs the
framework baseline at `templates/agents/<slug>.md` and **SKIPS** that
agent. The skip emits `tier_policy_adopter_override_respected` +
leaves your customization untouched.

This is the same diff-detect discipline as `scripts/upgrade.sh`.
Learned policy never clobbers your intentional tier choices.

## Kill-switch + dry-run

Two-factor kill-switch (BOTH required):

1. `CEO_TIER_POLICY_ENABLE=1` env flag
2. `~/.ceo-orchestration/tier-policy/.enabled` sentinel file (mode
   0600, parent dir 0700, Owner-signed content per C-P0-12)

Missing either factor → `tier_policy_killswitch_triggered` audit event
+ abort. `CEO_SOTA_DISABLE=1` master-overrides regardless.

Dry-run mode (`CEO_TIER_POLICY_DRY_RUN=1` or `--dry-run` flag on
`apply`): writes nothing; emits `tier_policy_dry_run_complete`; full
recommendation printed to stdout (ephemeral — not audit-log-persisted).

## Statistical-power interpretation

At n = 30 samples per (role × task-type), standard error of a
proportion near p=0.5 is ≈ 0.091, which makes the minimum detectable
effect at 80% power ≈ 25 percentage points. The gate is calibrated to
this: below 25pp gap, we treat the signal as sampling noise and
reject.

If you want *tighter* gates (e.g., 15pp at n≥90), PLAN-043 §Round 1
debate documented the alternative **Option A** calibration. Override
via local fork + rebuild — not supported as an adopter env-var in
v1.7.

## CLI reference

```text
ceo-tier-policy derive [--policy PATH] [--reports DIR]
    Read tournament-*.jsonl + current policy → emit Recommendation
    JSON to stdout. Read-only.

ceo-tier-policy apply [--dry-run] [--policy PATH] [--sigchain PATH]
                       [--reports DIR] [--agents DIR] [--baseline DIR]
    Dispatch recommendations. Kill-switch gated. Promote-auto fires
    subject to cost gate. Demote path emits owner-sign instructions.

ceo-tier-policy owner-sign --agent SLUG --from-tier MODEL --to-tier MODEL
                            --sp-chain-id SP-NNN-XXXXXXXX [--evidence-hmac HEX]
                            [--sigchain PATH] [--owners-file PATH]
                            [--skip-commit]
    Owner signs a demote or cost-gated promote. Requires git user.email
    in allowlist + git commit -S (unless --skip-commit).

ceo-tier-policy verify [--sigchain PATH] [--policy PATH]
    Walk sigchain, verify HMAC chain + sigchain_tip_length cross-check
    against policy artifact (C-P0-5 truncation detection).

ceo-tier-policy show [--policy PATH]
    Pretty-print current assignments; falls back to ADR-052 baseline
    if artifact absent/corrupt.

ceo-tier-policy enable [--sentinel PATH] [--owners-file PATH]
                       [--skip-commit]
    Write Owner-signed sentinel file (factor-2 kill-switch).

ceo-tier-policy migrate [--policy PATH]
    Forward-migrate schema_version via loader.

ceo-tier-policy rotate-key --confirm [--owners-file PATH]
    Rotate tier-policy HMAC key (MVP stub; manual procedure documented
    in-output).

ceo-tier-policy sigchain-rotate [--force] [--sigchain PATH]
                                 [--owners-file PATH]
    Archive sigchain > 1000 entries + reseed. --force bypasses the
    threshold check (for key-rotation companion flow).
```

## Observability

Every CLI invocation emits audit events (logged to
`~/.claude/projects/<slug>/audit-log.jsonl` via the standard
framework `audit_emit.py` path). 9 new action strings:

- `tier_policy_derived` — every derive run (includes
  input_reports_sha256 + recommendation_count)
- `tier_policy_promote_applied` — after successful frontmatter write
- `tier_policy_demote_requested` — demote or cost-gated-promote;
  carries the exact CLI command Owner needs to run
- `tier_policy_rejected` — gate rejected a candidate (VETO / stat
  power / cooldown)
- `tier_policy_hmac_verify_failed` — forged / corrupt tournament
  report
- `tier_policy_adopter_override_respected` — customized agent file
  preserved
- `tier_policy_killswitch_triggered` — apply aborted on missing factor
- `tier_policy_dry_run_complete` — dry-run exited cleanly
- `tier_policy_promote_cost_gated` — promote downgraded to signed due
  to cost envelope

On installations where `_KNOWN_ACTIONS` has not been extended via the
Owner kernel batch, events silently drop with a breadcrumb (fail-open
per PLAN-041 precedent). The tier-policy feature is fully functional
without the audit registration — only the per-run trail is quiet.

## Troubleshooting

### "apply: no valid policy artifact"

`.claude/tier-policy.json` does not exist or failed schema validation.
Run `ceo-tier-policy show` to see the load status + reason. If
`fallback` + `reason=file_not_found`, run `enable` to install the
baseline artifact from `templates/`.

### "owner-sign: git user.email unset"

Set your git identity:

```bash
git config user.email "you@example.com"
git config user.signingkey <your-key-id>    # GPG
# OR for SSH signing:
git config gpg.format ssh
git config user.signingkey ~/.ssh/id_ed25519.pub
```

### "verify: TRUNCATION DETECTED"

Policy artifact claims N sigchain entries but actual line count is
M < N. Most likely an editor ate the tail; restore from git:

```bash
git checkout -- .claude/tier-policy.json.sigchain
```

If genuinely corrupt, you may need to `sigchain-rotate --force`
followed by a fresh `owner-sign` for the current assignments — this
breaks the historical chain, so only do it if the content is
truly lost.

### "apply: killswitch (reason=sentinel_wrong_perms)"

Tighten the sentinel:

```bash
chmod 0700 ~/.ceo-orchestration/tier-policy
chmod 0600 ~/.ceo-orchestration/tier-policy/.enabled
```

Sentinel parent must be 0700 and file must be 0600. Non-owner-UID or
symlink sentinels reject per C-P0-12 supply-chain hardening.

### "killswitch (reason=sentinel_is_symlink)"

Someone replaced the sentinel with a symlink. **Delete + recreate:**

```bash
rm ~/.ceo-orchestration/tier-policy/.enabled
ceo-tier-policy enable
```

If you did not create the symlink yourself, audit your user account
for compromise — supply-chain attackers frequently use this vector.

## Adopter threat model (summary)

The threats ADR-064 §Threat-model enumerates:

- **T1 VETO revocation** — 3-layer defense (hardcode + literal + hook)
- **T2 Forged reports** — HMAC verify on input
- **T3 Adopter override clobber** — diff-detect preserves
- **T4 Oscillation** — cooldown + power floor
- **T5 Direct JSON edit** — canonical-edit guard + sigchain
- **T6 Kill-switch bypass** — two-factor + fork-safety + low-level recheck
- **T7 Cost runaway** — cost-envelope gate
- **T8 Sigchain collision** — HMAC-SHA256 128-bit resistance
- **T9 Tail truncation** — sigchain_tip_length in artifact HMAC anchor
- **T10 Report replay** — REPORT_MAX_AGE_DAYS freshness filter
- **T11 Supply-chain sentinel** — Owner-signed content + symlink guard

For the full formal spec, see `SPEC/v1/tier-policy.schema.md` + ADR-064.

## Cost envelope

- Derivation + apply are **local-only** ($0 per invocation).
- Tournament runs are the cost driver (PLAN-032 / ADR-063 §Cost-
  bounded — $40–120 per full run; monthly cadence ≈ $480–1440/year).
- Apply path is file edits only ($0 per apply).
- Promote cost delta example (per-task basis):
  - Haiku → Sonnet ≈ 3.5× per-token cost
  - Sonnet → Opus ≈ 4.3× per-token cost
- The cost-envelope gate computes the **projected monthly delta**
  from audit-log aggregation of recent 30-day token volumes for the
  agent. Above `CEO_TIER_POLICY_MAX_PROMOTE_DELTA_USD` ($20 default) →
  downgrade to signed path.

## Related

- `SPEC/v1/tier-policy.schema.md` — formal artifact schema
- `.claude/adr/ADR-064-dynamic-tier-policy-learned-dispatch.md`
- `.claude/adr/ADR-052-multi-model-dispatch-by-role.md` — static baseline
- `.claude/adr/ADR-063-agent-eval-empirical-dispatch-validation.md`
- `.claude/adr/ADR-055-audit-log-hmac-chain.md`
- `.claude/plans/PLAN-043-dynamic-tier-selector.md`
- `docs/TOURNAMENT.md` (ADR-063 producer-side docs)
