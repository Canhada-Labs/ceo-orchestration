# Upgrade Procedure

> Step-by-step playbook for adopters bumping their framework version
> (e.g. `v1.10.0` → `v1.11.2`). Designed for predictability —
> no `bash scripts/upgrade.sh && hope`.

## When to upgrade

| Your install | Recommended action |
|--------------|---------------------|
| `vX.Y.Z` (latest current MINOR) | Stay; track PATCH releases |
| `vX.Y-1.Z` (previous MINOR) | Plan upgrade within the **6-month** support window per `SUPPORT.md` |
| `vX.Y-2.Z` or older | Upgrade soon — best-effort support; missing security patches |
| Pre-`v1.0` | Upgrade required; v1 SPEC is the contract horizon |

Run `bash .claude/scripts/check-framework-updates.sh` weekly to
learn about new releases at the moment they ship, not when CI
breaks.

## Pre-upgrade (10 min)

### 1. Read what changed

```bash
# Latest CHANGELOG
cat /path/to/ceo-orchestration/CHANGELOG.md | head -100

# Or via git
git log v<your-current> ..v<target> --oneline -- CHANGELOG.md
```

Look specifically for:

- **Breaking changes** (`### Changed` entries that mention
  removed fields or behavior)
- **New env vars** that change defaults
- **New CI gates** you may need to wire
- **New trust boundaries** (any ADR-NNN with "expanded trust
  boundary" in the title)
- **Schema bumps** (audit-log v2.X → v2.Y additions you may want to
  capture)

### 2. Verify your local state is committed

```bash
cd /path/to/your/project
git status
```

If anything in `.claude/` is uncommitted, commit it first or stash.
The `--pin` mode of `upgrade.sh` refuses to proceed otherwise (this
is intentional — uncommitted local edits + framework upgrade =
hard-to-debug merge conflicts).

### 3. Snapshot framework state

```bash
bash .claude/scripts/ceo-backup.sh
```

This snapshots audit log + memory + agent-metrics so you can
recover if the upgrade misbehaves.

### 4. Verify CI is green pre-upgrade

```bash
gh run list --limit 5
```

If your project's CI is currently failing, fix that first. Mixing
framework-upgrade-induced regressions with pre-existing failures
makes triage painful.

### 5. Verify the framework's own CI is green at the target tag

The framework dogfoods its own CI. If `v<target>` was tagged,
`release.yml`'s 24h Codex re-pass window (per ADR-103) has passed.
Check:

```bash
gh run list --repo Canhada-Labs/ceo-orchestration \
  --workflow validate.yml --branch main --limit 3
```

All three should be green. If not, the tag may be from an unstable
window — wait for the next tag.

## Upgrade (5–15 min depending on size)

### Standard path: `bash scripts/upgrade.sh`

From your **adopter project root**:

```bash
cd /path/to/your/project
bash scripts/upgrade.sh --pin v1.11.2
```

What `upgrade.sh` does:

1. Backs up your current `.claude/` to `.claude.bak/<timestamp>/`.
2. Pulls the target framework version (`git fetch && git checkout`
   on the framework clone).
3. Re-runs `install.sh` with your existing profile + stack flags
   (preserved in `.claude/.install-config`).
4. Diff-detects per-canonical-5 native agent file. Preserves
   adopter overrides on each (per ADR-052 §Adopter override). The
   `model:` field in particular is preserved if you customized it.
5. Updates skills + hooks + scripts to the target version.
6. Reports any conflicts requiring manual resolution.

### Pin to a specific version

```bash
bash scripts/upgrade.sh --pin v1.11.2
```

The `--pin` mode:

- Refuses to upgrade if `.claude/` has uncommitted changes.
- Records the pinned version in your project (durable across
  subsequent `upgrade.sh` calls without `--pin`).
- Has no MAJOR-boundary guard and no `--allow-major` flag — it
  checks out exactly the tag you pass. Consult `CHANGELOG.md`
  before crossing a MAJOR.

### npm-based install

If you installed via npm:

```bash
cd /path/to/your/project
npm update -g ceo-orchestration
ceo-orchestration upgrade --pin v1.11.2
```

The npm package wraps `bash scripts/upgrade.sh` with the same flags.

### Skipping a MINOR (allowed within v1)

You can jump from `v1.9.x` directly to `v1.11.x` without the
intermediate `v1.10.x`:

```bash
bash scripts/upgrade.sh --pin v1.11.2
```

The framework guarantees forward compatibility within v1 (per
`VERSIONING.md` §End-of-life policy): the audit-log schema is
**additive** (new fields only, never removed or renamed), so there
is no migration to run when you skip a MINOR. `upgrade.sh` has no
`--from` flag and no migration runner — it only refreshes the
framework files to the pinned tag.

**Discouraged but supported:** skipping more than one MINOR. Each
MINOR added tests and behaviors worth dogfooding individually.
Skipping multiple at once means any regression is harder to
attribute.

### Skipping a MAJOR (not yet possible)

There is no MAJOR after `v1.x` as of v1.11.2. When `v2.0` ships, the
upgrade procedure will be amended with a §v1 → v2 migration guide.
Until then, all upgrades are within-v1.

## Post-upgrade (10 min)

### Repair: restore custom hooks the overwrite removed

`upgrade.sh` replaces `.claude/hooks/` wholesale, which deletes any
custom hook files your `settings.json` still references (the legacy
upgrade path does not preserve them). Immediately after the upgrade,
run:

```bash
bash scripts/finish-app-upgrade.sh /path/to/your/project
```

It restores any `settings.json`-referenced hook that exists in the
latest `.claude.bak/` but is missing on disk, gitignores + removes
the `.claude.bak/` backup, and makes a local (un-pushed) commit for
you to review. Skip this only if you have no custom hooks beyond the
framework set.

### 1. Validate governance

```bash
bash .claude/scripts/validate-governance.sh
```

Expect: `PASS: Governance files validated.`

If errors, the most common cause is a skill referenced in
`team.md` that no longer exists in the new version (renamed or
removed). Edit `team.md` to match.

### 2. Run the test suite

```bash
# Stack-specific — example for Python
python3 -m pytest .claude/

# Or for Node
npm test
```

Both the framework's hook tests AND your adopter project's tests
should still pass. If only the adopter tests fail, the
framework upgrade is fine; the failure is in your code (likely a
new lint/type-check rule).

### 3. Spot-check `/status`

In a fresh Claude Code session:

```
/status
```

Expect: clean output, recent audit-log activity present, no
governance errors.

### 4. Verify native agents intact

```bash
ls -la .claude/agents/
```

Expect: `code-reviewer.md`, `security-engineer.md`,
`qa-architect.md`, `performance-engineer.md`, `devops.md`,
`_dispatch.md`. The 5 canonical-5 + auto-generated dispatch.

If you customized any (e.g. changed `model:` field), open and
verify your override survived.

### 5. Verify hook integration

Run a small spawn to verify the hook chain is intact:

```
/spawn devops "list the env vars defined in our .env.example"
```

Expect:
- `check_agent_spawn.py` allows the spawn (you see no
  `GOVERNANCE: missing_skill_content` block).
- `audit_log.py` writes a fresh entry (verify with
  `python3 .claude/scripts/audit-query.py recent --limit 1`).
- The audit entry has `model: "claude-haiku-4-5-20251001"` (or
  your override).

### 6. Verify cost tooling

```bash
python3 .claude/scripts/ceo-cost.py --since 1h
```

Expect: a row for the spawn from step 5 with cost > 0.

### 7. Verify health check

```bash
python3 .claude/scripts/ceo-health.py
```

Expect: exit 0. If exit 1, read the listed issues.

## Rollback procedures

Two paths depending on what failed.

### Rollback A — restore the previous install

`upgrade.sh` backed up your previous install to
`.claude.bak/<timestamp>/`. Restore via:

```bash
TIMESTAMP=$(ls -t .claude.bak/ | head -1)
rm -rf .claude
cp -r .claude.bak/$TIMESTAMP .claude
```

This restores the **framework files**. Your `team.md`, `CLAUDE.md`,
plans, and skills under `domains/<your-domain>/` were never touched
by the upgrade.

### Rollback B — git revert + re-install

If you committed any framework files (e.g. a settings.json change),
revert the commit and re-install:

```bash
git log --oneline -- .claude/ | head -5
git revert <upgrade-commit-sha>
bash scripts/upgrade.sh --pin <previous-version>
```

### After rollback

Run validate-governance + ceo-health to confirm:

```bash
bash .claude/scripts/validate-governance.sh
python3 .claude/scripts/ceo-health.py
```

Then file an issue against the framework with the failure mode
that forced the rollback.

## Adopter override preservation

Per ADR-052 §Adopter override, `upgrade.sh` preserves your
customizations to:

- `.claude/agents/<canonical-5>.md` — `model:` field, additional
  `tools:` entries, prompt body customizations
- `.claude/team.md`, `.claude/frontend-team.md` — your concrete
  personas, project-specific routing, custom approvers
- `.claude/skills/domains/<your-domain>/` — your domain content
- `.claude/CLAUDE.md` — your project context
- `.claude/settings.json` — only the parts you've customized; new
  base hooks added during upgrade

What `upgrade.sh` will overwrite:

- `.claude/skills/core/` — universal skills shipped by framework
- `.claude/skills/frontend/` — universal frontend skills
- `.claude/hooks/` — all hooks
- `.claude/scripts/` — framework-shipped scripts
- `.claude/commands/` — universal slash commands

If you have customized anything in the "will overwrite" list,
either:

1. Move your customization to `domains/<your-domain>/` (preserved)
2. Maintain a fork of the framework
3. Submit your customization upstream as a PR

## Schema migrations (audit log etc.)

The audit log is **additive within v1** — new versions add fields
but never remove or rename. Your existing audit-log.jsonl reads
fine after an upgrade. Specifically:

| Audit-log SPEC version | Added in framework version | What's new |
|-------------------------|------------------------------|------------|
| v2.0 | `v1.0.0-rc.1` | Five typed events: agent_spawn, debate_event, plan_transition, veto_triggered, benchmark_run |
| v2.1 | Sprint 5 | injection_flag |
| v2.2 | Sprint 8 | confidence_gate, lesson_read/archived/restored, lesson_outcome |
| v2.3 | Sprint 9 | lesson_outcome_undone |
| v2.4 | Sprint 11 | state_store_*, budget_*, otel_export_dropped, output_safety_flag, skill_patch_applied, squad_imported |
| v2.5 | Sprint 13 | live_adapter_*, breaker_*, credential_rotation_due, mcp_handler_* |
| v2.6 | Sprint 14 | policy_*, replay_*, prediction_queried, pattern_*, threat_model_* |
| v2.7 | Sprint 32 (PLAN-020) | usage_metadata, cache_coverage, rail (additive on agent_spawn) |
| v2.8 | Sprint 32 (PLAN-021) | model (additive on agent_spawn) |

Per `SPEC/v1/audit-log.schema.md` §Consumer contract, consumers
tolerate unknown fields. Your `audit-query.py` from a newer install
reads logs from older installs without issue. The reverse may
ignore fields silently.

## Upgrade examples (real)

### `v1.10.0` → `v1.11.x` (Claude-only refocus, audit-v2 readiness ladder)

The v1.10.0 → v1.11.x line is **mid-pivot** (audit-v2 verdict
`TRIAL-PENDING-SOAK`). v1.11.0 reframed the framework from
multi-adapter (Gemini + OpenAI + local) to **Claude-only** (ADR-084
+ ADR-085). Adopters who installed against `v1.10.0` should expect:

- Adapter stubs deleted (`gemini.py`, `openai.py`, `local.py`)
- `validate.yml::adapter-matrix` job removed
- 5 plans re-opened `done → executing` per ADR-092 honest-deferral
- New ADRs (092 honest-deferral, 093 60-day refused-ADR moratorium)
- Calendar-soak gates active — 14-day CI green + 30-day no-retag
  + 60-day refused-ADR moratorium (gates earliest TRIAL 2026-06-26)

```bash
cd /path/to/adopter-project

# Pre
bash .claude/scripts/ceo-backup.sh
git status   # clean

# Verify framework's own CI is green at the target tag
gh run list --repo Canhada-Labs/ceo-orchestration \
  --workflow validate.yml --branch main --limit 3
# All three should be green. v1.11.1 had a known release.yml red
# (VERSION/tag mismatch); v1.11.2 is the first clean tag in the
# v1.11 line.

# Upgrade
bash scripts/upgrade.sh --pin v1.11.2

# Post
bash .claude/scripts/validate-governance.sh   # PASS
ls .claude/hooks/_lib/adapters/
# expect ONLY: __init__.py, claude.py
# (gemini.py, openai.py, local.py DELETED per ADR-084)

python3 .claude/scripts/audit-query.py recent --limit 1
# expect 'model' + 'rail' + 'usage_metadata' fields

python3 .claude/scripts/ceo-health.py   # exit 0
```

If your project had any references to the deleted adapter stubs
(unlikely — they were stubs for parity tests, not user-facing),
remove them. Otherwise the upgrade is non-breaking.

### `v1.5.0-rc.1` → `v1.6.0-rc.1` (legacy reference)

```bash
cd /path/to/adopter-project

# Pre
bash .claude/scripts/ceo-backup.sh
git status   # clean

# Upgrade
bash scripts/upgrade.sh --pin v1.6.0-rc.1

# Post
bash .claude/scripts/validate-governance.sh   # PASS
ls .claude/agents/   # 5 canonical-5 + _dispatch.md (NEW from PLAN-020)
python3 .claude/scripts/audit-query.py recent --limit 1
# expect 'model' + 'rail' + 'usage_metadata' fields
python3 .claude/scripts/ceo-health.py   # exit 0
```

If your project hadn't installed the canonical-5 native agents
before (because your existing install predates `v1.6.0-rc.1`),
the upgrade adds them. Customize via the `.claude/agents/<slug>.md`
frontmatter as needed.

### Custom: pin to a specific RC during evaluation

```bash
bash scripts/upgrade.sh --pin v1.11.2

# Run for a week against your real workload
# If happy and 14-day CI green streak holds:
bash scripts/upgrade.sh --pin v1.11.x    # promote to GA when audit-v3 + soak windows clear
```

The `--pin` flag is durable; subsequent `bash scripts/upgrade.sh`
calls (without `--pin`) honor the pinned version.

## Coordinating an upgrade across a team

If multiple engineers share the framework install:

1. **Notify the team** before upgrading: "I'm bumping framework
   from `v1.10.0` to `v1.11.2` on Tuesday."
2. **Upgrade in a feature branch**:
   ```bash
   git checkout -b chore/framework-v1.11.2
   bash scripts/upgrade.sh --pin v1.11.2
   git add .claude/
   git commit -m "chore: upgrade framework to v1.11.2"
   git push origin chore/framework-v1.11.2
   ```
3. **Merge with full CI green** — the framework upgrade may
   surface previously-quiet test issues.
4. **Communicate the merge**: "Framework upgraded; rebase your
   feature branches; new env vars in `docs/CHEAT-SHEET.md`."

## When NOT to upgrade

- During an active sprint deadline (delay until post-ship)
- When you have an open SEV-2+ incident (upgrade adds variables)
- During a freeze period your team has agreed on
- When the target is a GA tag cut < 24h after its RC (the ADR-103
  Codex re-pass window isn't done)
- When the framework's own CI is currently red on the target tag
  (wait for the fix-up RC)

## References

- `VERSIONING.md` — what each version digit means
- `SUPPORT.md` — what versions are supported
- `SECURITY.md` — security-driven upgrade triggers
- `docs/DISASTER-RECOVERY.md` — recovery if upgrade goes wrong
- `docs/CHEAT-SHEET.md` — env vars + commands referenced above
- `docs/READINESS-STATUS.md` — current verdict + calendar-soak gates
- `docs/STATE-RECOVERY.md` — resume-from-state patterns
- `docs/OBSERVABILITY.md` — audit-log structure + queries
- `docs/GOVERNANCE.md` — 35+ kill-switches catalog
- `bash scripts/upgrade.sh --help` — full flag reference

Last reviewed: 2026-04-28 (Session 71 / Wave D-3 — PLAN-052 Phase 6
soak window started, audit-v2 19/27 P0 closed; v1.11.2 stable, in
14-day CI green streak Day 1). Adopters on v1.10.x should plan
upgrade within the 6-month
support window; the v1.11 line clarifies the Claude-only thesis +
introduces the audit-v2 honest-deferral framework (ADR-092).
