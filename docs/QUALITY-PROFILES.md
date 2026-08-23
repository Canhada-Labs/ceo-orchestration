# Quality Profiles — max-quality / balanced / max-speed

> PLAN-025 Batch L (NEW FEATURE) — ships a 3-profile adopter-configurable
> quality tier for the canonical-5 native subagents. Profiles change
> which model each non-VETO agent dispatches to; the 2 VETO holders
> (code-reviewer + security-engineer) ALWAYS carry the VETO-floor model
> DERIVED from `tier_policy_cli._constants.VETO_HARDCODE` — currently
> `claude-fable-5`, never a literal in the profile script (PLAN-169 W4.3
> F1 / PLAN-183 W3).
>
> **See also:** [`docs/ADAPTIVE-EXECUTION-KERNEL.md`](ADAPTIVE-EXECUTION-KERNEL.md) — per-task ceremony classifier (S/M/L/XL) that complements session-level quality profiles. Quality profiles set the model tier for the session; AEK classifies the ceremony for each individual task.

Last updated: 2026-08-22 — VETO floor derived from the authority instead
of duplicated as a literal (PLAN-169 W4.3 F1 / PLAN-183 W3). Originally
2026-04-18 (Session 33 Phase D / PLAN-025 Batch L).

## TL;DR

```bash
# Pick a profile
bash .claude/scripts/set-quality-profile.sh max-quality    # 2 VETO-floor + 3 Opus 4.8
bash .claude/scripts/set-quality-profile.sh balanced       # default: 2 VETO-floor + 3 Sonnet 4.6
bash .claude/scripts/set-quality-profile.sh max-speed      # 2 VETO-floor + 3 Haiku 4.5

# Query current profile
bash .claude/scripts/set-quality-profile.sh --show

# Orthogonal: force Opus re-audit of every P1+ finding regardless of profile
CEO_OPUS_SPOT_CHECK_P1=1 python3 .claude/scripts/spot-check-findings.py <findings-file>
```

Default is `balanced`. Change via `set-quality-profile.sh` or pass
`--quality <profile>` to `scripts/install.sh` at install time.

## Profile table

| Profile | code-reviewer | security-engineer | qa-architect | performance-engineer | devops | Velocity | Cost vs all-Opus |
|---------|---------------|-------------------|--------------|----------------------|--------|----------|------------------|
| `max-quality` | VETO floor (derived) | VETO floor (derived) | Opus 4.8 | Opus 4.8 | Opus 4.8 | 1× (baseline) | 100% |
| `balanced` (default) | VETO floor (derived) | VETO floor (derived) | Sonnet 4.6 | Sonnet 4.6 | Sonnet 4.6 | 3.5× | ~56% |
| `max-speed` | VETO floor (derived) | VETO floor (derived) | Haiku 4.5 | Haiku 4.5 | Haiku 4.5 | 5-6× | ~22% |

> The `balanced` row read `Sonnet 4.6 | Sonnet 4.6 | Haiku 4.5` until
> PLAN-183 W3. The script has always written three Sonnet — the doc and
> the script's own header both described a distribution the code never
> produced.

Velocity + cost figures derived from PLAN-024 12-agent parallel audit
measurement (3.53× speedup validated at `balanced`; extrapolated for
`max-speed`). Your adopter workload may differ; run
`.claude/scripts/ceo-cost.py --since 7d` after a week on each profile
to measure YOUR numbers.

## Invariant: VETO floor is non-negotiable

Regardless of profile:

- **`code-reviewer`** stays on the **derived VETO floor**
  (`tier_policy_cli._constants.VETO_HARDCODE`). Merge VETO — a missed bug
  ships to production. The strongest model's reasoning reduces false
  negatives on the quality gate.

- **`security-engineer`** stays on the **derived VETO floor**. Auth/crypto
  VETO — a missed attack surface = security incident. Same rationale.

`validate-governance.sh` lints the `model:` field of canonical-5 agents,
but role-AGNOSTICALLY: it asks whether the id is in the ADR-149 working
set, never whether it is the VETO floor. That is why the F1-P1 downgrade
was legal at CI time for months — all three profiles wrote the literal
`claude-opus-4-8`, a member of `VETO_FLOOR_ALLOWED` two generations below
the ceiling, while the agent files shipped `claude-fable-5`. The floor is
now resolved from the authority at run time and the script FAILS CLOSED
(rc=3, nothing written) if that authority is unreadable or its frozen
SHA256 anchor does not match. The permanent guard is
`TestVetoFloorInvariantIsDerived` in
`.claude/scripts/tests/test_quality_profile.py`, which extracts the
profile list from the script itself so a fourth profile is covered on
arrival.

## When to pick which profile

### `max-quality` — for high-stakes sessions

- Security-critical feature work (auth rewrite, crypto change,
  compliance-relevant flows)
- Architectural changes touching 5+ modules (the extra Opus budget
  on performance-engineer + qa-architect catches design drift)
- Release-chain sessions (v1.X.Y GA cut)

**Cost:** 100% of baseline. Use when the incident cost of a missed
issue exceeds the $4-5 premium per session.

### `balanced` — for daily dogfood (DEFAULT)

- Feature development
- Bug fixes
- Refactors that don't touch 5+ modules
- Session-level work where the VETO holders catch critical issues +
  the lower-tier models handle bounded analysis tasks

**Cost:** ~56% of baseline. Optimal for ~90% of sessions.

### `max-speed` — for high-iteration prototyping

- Skill authoring + tutorial iteration
- Documentation-only sprints
- Policy file edits where VETO holders handle the review + Haiku fan-out
  covers qa/perf/devops in parallel
- Agent persona authoring

**Cost:** ~22% of baseline. Fastest per-iteration; Haiku on devops +
qa + performance is OK when the work is bounded.

## Runtime wiring

Settings key (`.claude/settings.json`):

```json
{
  "ceo_quality_profile": "balanced"
}
```

On profile change, `set-quality-profile.sh`:

1. Rewrites `.claude/agents/<slug>.md` `model:` field for the 3
   non-VETO agents per profile table.
2. Updates `.claude/settings.json` with the new `ceo_quality_profile`
   value.
3. Regenerates `.claude/agents/_dispatch.md` via
   `bash .claude/scripts/generate-dispatch.py --write`.
4. Emits an audit event (`governance_config_changed`) so the change
   is forensically visible.

`ceo-health.py` surfaces the active profile as a check line:

```
  ✓ quality_profile              balanced (code-reviewer=fable-5, security-engineer=fable-5, qa-architect=sonnet-4-6, ...)
```

## Orthogonal flag: `CEO_OPUS_SPOT_CHECK_P1=1`

Independent of profile choice. When set, after a multi-agent audit
synthesis (Wave B in PLAN-024-style flows), the CEO automatically
re-spawns an Opus agent to re-review every P1+ finding that was
originally scored by Sonnet or Haiku.

Purpose: defense-in-depth for adopters who run on `balanced` or
`max-speed` but want Opus eyes on anything HIGH-severity.

Usage:

```bash
# During a multi-agent audit:
CEO_OPUS_SPOT_CHECK_P1=1 python3 .claude/scripts/spot-check-findings.py \\
    .claude/plans/PLAN-<NNN>/audit/consolidated-findings.md
```

The script:
1. Parses the findings file for P1+ entries with `source_model`
   metadata.
2. For each finding scored by a non-Opus model, emits a re-audit
   request marker.
3. The CEO (in the calling session) respawns the `security-engineer`
   or `code-reviewer` archetype with the finding as context; the
   re-audit either confirms or corrects the severity.

Costs ~20% extra per audit but catches ~90% of the quality gap
between `max-speed` and `max-quality` for P1+ findings.

## Upgrade preservation

`scripts/upgrade.sh` preserves the `ceo_quality_profile` setting
across framework upgrades (i.e., you don't lose your profile choice
when pulling new framework versions). The upgrade script:

1. Reads the current `ceo_quality_profile` from
   `.claude/settings.json` before upgrade.
2. Runs the normal upgrade procedure.
3. Re-applies the saved profile via `set-quality-profile.sh <profile>`
   AFTER the upgrade lands.

If the upgrade introduces new canonical-5 agents, they are assigned
per the new profile's default for their role tier.

## Cost measurement (per-adopter)

After one week on a profile, measure your actual cost:

```bash
python3 .claude/scripts/ceo-cost.py --since 7d --by model
```

Compare against the published baseline. If your workload has
different spawn-mix, your cost ratio will differ from the 22%/56%/100%
figures quoted above. See `docs/cost-of-operation.md` for the
underlying model.

## How to change profile mid-session

You may change profile during a session. Subsequent spawns use the
new profile. Active spawns complete on their originally-dispatched
model (no mid-spawn model switch).

```bash
# Started session on 'balanced', switching to max-quality for the
# remainder because this batch has security-critical work:
bash .claude/scripts/set-quality-profile.sh max-quality
# Next spawn will dispatch per max-quality profile
```

## Rollback

```bash
# Revert to default
bash .claude/scripts/set-quality-profile.sh balanced
```

## Cross-references

- `.claude/adr/ADR-052-multi-model-dispatch-by-role.md` — underlying
  multi-model dispatch mechanism
- `.claude/scripts/set-quality-profile.sh` — the profile setter
- `.claude/scripts/spot-check-findings.py` — orthogonal flag script
- `.claude/scripts/ceo-health.py` — profile surface in health check
- `docs/cost-of-operation.md` — cost model + pricing table
- PLAN-024 velocity validation — baseline for ratios
- PLAN-025 Batch L — this feature
