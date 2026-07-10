# Cheat Sheet — Daily Commands

> One-page reference for the operator. Designed to be opened in a
> second tab while you work. Each row shows what to type and what to
> expect. Skip the rest of `docs/` until something breaks.

> **New to the framework?** Read [`docs/DAY-1-CHECKLIST.md`](DAY-1-CHECKLIST.md)
> first (install verification) and then [`docs/ADOPTER-ASSESSMENT.md`](ADOPTER-ASSESSMENT.md)
> (40-question scenario-based understanding check). This cheat sheet
> assumes both are green.

## Slash commands (Claude Code chat)

Type these directly in the Claude Code chat window. They are
implemented as Markdown command files under `.claude/commands/`.

| Command | What it does | Typical use |
|---------|--------------|-------------|
| `/spawn <agent> "<task>"` | Spawn a named agent with persona + skill + file assignment via `inject-agent-context.sh` | `/spawn code-reviewer "review src/auth.ts"` |
| `/debate start <PLAN-NNN> "<proposal>"` | Round 1 of multi-agent debate on an L3+ plan | `/debate start PLAN-022 "split phase 3 into two commits"` |
| `/debate round2 <PLAN-NNN>` | Continue a debate to round 2 (consensus check) | After round 1 produces critiques |
| `/debate status <PLAN-NNN>` | Show round-by-round agent verdicts and convergence score | "Did we reach consensus?" |
| `/status` | Single-glance project state — plan, phase, vetoes, recent audit, ahead/behind | Start of every working session |
| `/audit-page` | Audit a frontend page across 16 UX + technical dimensions | Before shipping a UI change |
| `/skill-review` | List pending skill-patch proposals + approve/reject | Maintainer task |
| `/lesson-review` | List recent lessons; optionally undo a lesson outcome | Weekly hygiene |
| `/resume <PLAN-NNN>` | Resume a plan across sessions using its derived graph | Fresh terminal continuation |
| `/agent-budget` | Token usage + cost rollup for a plan or time window | Cost retrospective |
| `/memory-scratchpad` | Read/write plan-scoped shared memory for inter-agent handoff | Mid-debate |
| `/pitfall` | List pitfalls from the universal catalog (and optionally a domain) | Before a risky spawn |
| `/veto-check <file>` | Scan a file for veto-worthy code-review + security patterns | Pre-PR self-check |
| `/squad-install <tarball>` | Import a signed squad bundle into `.claude/skills/domains/` | New domain adoption |
| `/architect "<brief>"` | Draft a new squad bundle from a domain brief (meta-agent) | Building a new vertical |

## Bash scripts (terminal)

Run these from the project root, **not** from inside `.claude/`.
All scripts are stdlib-only Python ≥ 3.9 or Bash ≥ 4.

### Agent + spawn

| Command | What it does |
|---------|--------------|
| `bash .claude/scripts/inject-agent-context.sh <Agent> "<task>"` | Build the prompt the Agent tool needs (Format A inline). Add `--mode=reference` for Format B (ADR-051) |
| `bash .claude/scripts/generate-dispatch.py` | Regenerate `.claude/agents/_dispatch.md` from native agent frontmatter |

### Audit log

| Command | What it does |
|---------|--------------|
| `python3 .claude/scripts/audit-query.py recent --limit 10` | Last 10 audit entries |
| `python3 .claude/scripts/audit-query.py spawn-stats --since 7d` | Spawn count + skill distribution last 7 days |
| `python3 .claude/scripts/audit-query.py vetoes --since 30d` | All `veto_triggered` events (security forensic) |
| `python3 .claude/scripts/audit-query.py tokens --since 30d` | Token sums per skill / subagent_type / day |
| `python3 .claude/scripts/audit-query.py debates --plan PLAN-022` | Debate timeline for one plan |
| `python3 .claude/scripts/audit-query.py budget --plan PLAN-022` | Token totals for one plan |
| `python3 .claude/scripts/audit-query.py replay --session <id>` | Spawn ordering for replay |
| `python3 .claude/scripts/audit-query.py freshness` | Latest event timestamps per action (gap detection) |
| `python3 .claude/scripts/audit-query.py raw --action veto_triggered --limit 5` | Raw JSONL filtered by action |

### Cost + health (PLAN-022 §Phase 3)

| Command | What it does |
|---------|--------------|
| `python3 .claude/scripts/ceo-cost.py --since 30d` | Cost breakdown by model + day |
| `python3 .claude/scripts/ceo-cost.py --since 30d --by-model --format json` | Machine-readable rollup |
| `python3 .claude/scripts/ceo-health.py` | One-shot health check; exit 0 healthy, 1 issues, 2 fatal |
| `python3 .claude/scripts/ceo-health.py --format json` | Health output as JSON for monitoring |

### Backup + update (PLAN-022 §Phase 5)

| Command | What it does |
|---------|--------------|
| `bash .claude/scripts/ceo-backup.sh` | Snapshot audit-log + memory + agent-metrics to `~/.ceo-backups/<slug>/` |
| `bash .claude/scripts/ceo-restore.sh <tarball>` | Verify SHA + dry-run restore (then `--apply` to commit) |
| `bash .claude/scripts/check-framework-updates.sh` | Compare local VERSION to upstream tag list |

### Governance + maintenance

| Command | What it does |
|---------|--------------|
| `bash .claude/scripts/validate-governance.sh` | Structure check — skills, hooks, plans, settings.json |
| `bash .claude/scripts/check-skill-health.sh` | Detect stale `src/...` references in SKILL.md files |
| `bash .claude/scripts/check-contamination.sh` | Allowlist enforcement (no personal handles in templates) |
| `bash .claude/scripts/check-pitfall-regression.sh` | Universal pitfall regression scan |
| `python3 .claude/scripts/check-staleness.py` | Plans / ADRs / benchmarks staleness CLI |
| `python3 .claude/scripts/check-tier-boundaries.py` | core/frontend → domains layer-boundary check |
| `bash .claude/scripts/generate-skill-inventory.sh` | Regenerate the skill inventory in the ceo-orchestration SKILL.md |

### Benchmarks + replay

| Command | What it does |
|---------|--------------|
| `python3 .claude/scripts/run-skill-benchmark.py <skill>` | Async runner, temp=0, median-of-3 |
| `python3 benchmarks/replay.py replay-fixtures/plan-019-wave-2a.jsonl` | Spawn-prompt cost replay (PLAN-020 Phase 6) |
| `python3 .claude/scripts/budget-summary.py --plan PLAN-NNN` | Predict-budget rollup |

### Dashboard + observability

| Command | What it does |
|---------|--------------|
| `python3 .claude/scripts/audit-dashboard.py` | Local SSE dashboard on `127.0.0.1:8765` (read-only) |
| `python3 .claude/scripts/hook-profiler.py` | Profile hook latency with `--smoke` / `--floor` modes |

## Environment variables (kill switches + tuning)

| Variable | Default | Effect |
|----------|---------|--------|
| `CEO_SOTA_DISABLE` | unset | `=1` disables ALL PLAN-020/021 SOTA features (master kill) |
| `CEO_NATIVE_SUBAGENTS` | `1` | `=0` forces inline prompt rail (custom), disables native subagent dispatch |
| `CEO_SKILL_REFERENCE_MODE` | `1` | `=0` forces inline `## SKILL CONTENT` everywhere; disables `## SKILL REFERENCE` Format B |
| `CEO_MULTIMODEL_ENABLE` | `(reserved/unwired)` | Setting this has **no runtime effect today** (documented kill switch, never wired). To force all-Opus, manually set each `.claude/agents/*.md` `model:` field to `claude-opus-4-8`. |
| `CEO_GATE_TRIM` | unset | `=1` trims gate-1 boot ceremony (advanced; PLAN-020 Phase 5) |
| `CEO_POLICY_ENGINE_DISABLE` | unset | `=1` disables YAML policy engine; falls back to legacy `.py` hook path |
| `CEO_POLICY_FILE` | unset | Override default `.claude/policies/<name>.yaml` |
| `CEO_POLICY_LEGACY_HOOK_PATH` | unset | Path to legacy `.py` hook for policy fallback |
| `CEO_BUDGET_BYPASS` | unset | Owner-only bypass for `check_budget.py` blocking |
| `CEO_OUTPUT_SAFETY_MODE` | `flag` | `block` to enforce, `flag` to advisory-log only |
| `CEO_AUDIT_LOG_DIR` | `~/.claude/projects/<slug>/` | Override audit log directory |
| `CEO_AUDIT_LOG_PATH` | `<DIR>/audit-log.jsonl` | Override exact path |
| `CEO_AUDIT_LOG_ROTATE_BYTES` | `10485760` (10 MB) | Rotate threshold |
| `CEO_LIVE_ADAPTERS` | unset | `=1` enables live HTTP adapters (default off — stub mode) |
| `CEO_LIVE_TIMEOUT` | `30` | Seconds per live API call |
| `CEO_LIVE_PROVIDER` | `anthropic` | Default live adapter provider |
| `CEO_REAL_EMBEDDINGS` | unset | `=1` uses real embeddings; default uses deterministic fallback |
| `CEO_OTEL_ENDPOINT` | unset | OTLP endpoint for export; off when unset |
| `CEO_OTEL_ALLOWED_HOSTS` | unset | Allowlist of OTLP host destinations |
| `CEO_PRICING_PATH` | bundled | Path to alternative model pricing JSON |
| `CEO_PROJECT_NAME` | `ceo-orchestration` | Used for state/audit dir slug |
| `CEO_STATE_ROOT` | `~/.claude/projects/<slug>/state` | State store root |
| `CEO_HOOK_ADAPTER` | `claude` | Hook adapter (`claude` or `gemini` stub) |
| `CEO_KERNEL_OVERRIDE` | unset | Owner-only — required to apply kernel patches via `.claude/plans/PLAN-NNN/.../apply-*.py` |
| `CEO_KERNEL_OVERRIDE_ACK` | unset | Must be set to `I-ACCEPT` together with the override |
| `CLAUDE_PROJECT_DIR` | cwd | Set by Claude Code; framework respects it |
| `CI` | unset | Set by CI runners; framework relaxes some perf budgets when set |

**Critical kill-switches added in v1.11.x (Wave A-D):**

| Variable | Default | Effect |
|----------|---------|--------|
| `CEO_MITIGATION_DISABLE` | unset | `=1` forces native dispatch rail for ALL archetypes (reverts ADR-082); emergency rollback if sub-agent fabrication observed |
| `CEO_MCP_SCANNER_DISABLE` | unset | `=1` disables MCP injection scanner (ADR-083); emergency only |
| `CEO_AUDIT_HMAC_DISABLE` | unset | `=1` disables HMAC chain — **NOT RECOMMENDED**; forensic emergency only |
| `CEO_WEBFETCH_INJECTION_SCAN` | `1` | `=0` disables WebFetch/Read injection scan (ADR-077); emergency only |
| `CEO_FLUENCY_NUDGE` | `1` | `=0` disables Artifact Paradox SubagentStop advisory |
| `CEO_BRAINSTORM_GATE` | `1` | `=0` reverts to CEO-directed brainstorm (reverts ADR-090 #3) |
| `CEO_AUDIT_TOKENS_AUTO` | `1` | `=0` disables auto-run audit-tokens at SessionEnd (reverts ADR-090 #6) |

**Activation (off-by-default opt-ins):**

| Variable | Default | Effect |
|----------|---------|--------|
| `CEO_SWARM` | unset | `=1` activates autonomous-loop swarm coordinator (`docs/AUTONOMOUS-LOOP-GUIDE.md`) |
| `CEO_TOURNAMENT_ENABLE` | unset | `=1` activates best-of-N tournament scorer (pair with `CEO_SWARM=1`) |
| `CEO_RAG_BRIDGE_ENABLE` | unset | `=1` activates LightRAG sidecar bridge (ADR-062, requires sidecar install) |
| `CEO_OTEL_EMIT` | unset | `=1` activates OTLP cost-stream emit (ADR-061, requires `CEO_OTEL_ENDPOINT`) |
| `CEO_TWO_PASS_REVIEW` | unset | `=1` activates 2-pass code-review (Sonnet→Opus) |
| `CEO_AUTONOMOUS_LOOPS_DISABLE` | unset | `=1` hard-disables autonomous-loop scheduling (overrides `CEO_SWARM`) |
| `CEO_LEARNING_OBSERVE` | unset | `=1` activates the PLAN-154 metadata observe rail (per-session closed-schema `.observe.jsonl` store). Unset = structurally off (zero delta); any other set value = explicit off → one `learning_rail_disabled` breadcrumb/session |
| `CEO_LEARNING_BOOT_LESSONS` | unset | `=1` activates the `/ceo-boot` "Past lessons" fenced section (PLAN-154 item 4; default full-markdown mode only — never `--short`/`--cached`/`--json`). Unset = structurally off; other set value = explicit off (breadcrumb) |
| `CEO_FACT_GATE_ENFORCE` | unset | Fact-forcing deny-once gate flip (PLAN-154 item 6 / ADR-160 D5). ENABLE is SETTINGS-BACKED only (`{"env":{"CEO_FACT_GATE_ENFORCE":"1"}}` in a settings layer); as an ENV var it is EMERGENCY OFF only (`=0` forces advisory — env can never enable) |
| `CEO_LEARNING_DISTILL_MODEL` | unset | Overrides the offline distiller model id (`distill-lessons.py`; default = explicit pin `claude-haiku-4-5-20251001`) |

**PLAN-154 learning-loop kill-switches (default-ON telemetry rails):**

| Variable | Default | Effect |
|----------|---------|--------|
| `CEO_FACT_GATE_SHADOW` | `1` (shadow on) | `=0` disables item-6 shadow telemetry (zero filesystem delta; separate from the enforce flip — disabling shadow never touches an armed deny-once gate). Shadow produces the ADR-160 D5 flip-criteria telemetry |
| `CEO_ADVISORY_DAMPEN` | `1` (dampening on) | `=0` disables advisory condensation (`_lib/advisory_dampen.py` — full text on every repeat). Display-only rail; block reasons are EXEMPT BY NAME and never dampened |

**Budget controls (recommended for production-like adopters):**

| Variable | Default | Effect |
|----------|---------|--------|
| `CEO_BUDGET_ENFORCE` | unset | `=1` activates budget enforcement at spawn-time |
| `CEO_BUDGET_PER_SPAWN` | unset | USD cap per individual spawn (e.g. `0.25`) |
| `CEO_BUDGET_BYPASS_MAX_PER_DAY` | `3` | Cap on budget bypasses per UTC day |
| `CEO_DISPATCH_COST_CAP` | unset | USD cap per dispatch chain |
| `CEO_TOURNAMENT_BUDGET_USD` | unset | USD total cap on tournament cost (required when `CEO_TOURNAMENT_ENABLE=1`) |

**Precedence:** `CEO_SOTA_DISABLE=1` is the master switch — if set,
all other CEO_* feature toggles are forced OFF regardless of value.

**Full reference:** [`docs/GOVERNANCE.md`](GOVERNANCE.md) §"What CAN be
turned off" — 6 categories, 55+ env-vars, with frozen invariants
(VETO floor, sentinel discipline, kernel emit, Claude-only) that
no env-var can bypass.

## Common task recipes

### "Spawn a code-reviewer on the current diff"

```
/spawn code-reviewer "review the staged diff in this repo (git diff --cached)"
```

### "Show the last 5 vetoes from the audit log"

```bash
python3 .claude/scripts/audit-query.py vetoes --since 30d --limit 5
```

### "Disable the framework for one session"

```bash
CEO_SOTA_DISABLE=1 claude
```

(All PLAN-020/021 features OFF for that session only. Hooks still
run as fail-open observers.)

### "Check my cost today"

```bash
python3 .claude/scripts/ceo-cost.py --since 1d
```

### "Find the latest debate consensus for a plan"

```bash
ls .claude/plans/PLAN-NNN/debate/round-*/consensus.md | tail -1
```

### "Reset everything for a fresh demo"

```bash
# Backup first
bash .claude/scripts/ceo-backup.sh

# Then prune your audit log
mv ~/.claude/projects/<slug>/audit-log.jsonl ~/.claude/projects/<slug>/audit-log.jsonl.archive
```

### "Install in a new project"

```bash
cd /path/to/new-project
~/ceo-orchestration/scripts/install.sh . --profile core,frontend --stack node
```

### "Pin to a specific framework version"

```bash
bash scripts/upgrade.sh --pin v1.7.0-rc.1
```

### "Run governance gates locally before pushing"

```bash
bash .claude/scripts/validate-governance.sh && \
  bash .claude/scripts/check-contamination.sh && \
  bash .claude/scripts/check-pitfall-regression.sh
```

## Session continuity (post-crash + side investigations)

> Doctrine added by PLAN-135 W4 D4. Four primitives that restore or
> branch DIFFERENT things — post-crash you usually need TWO of them.

| Primitive | Restores / creates | When to use |
|-----------|--------------------|-------------|
| `claude --continue` | The **CONVERSATION** — most recent session transcript in this directory | First move after a crash or closed terminal: get the dialogue back |
| `/resume <PLAN-NNN>` | The **PLAN** — re-derives work state from the plan file + audit log + scratchpad | After `--continue`, or in a fresh terminal: get the WORK state back |
| `/fork` (in-session) | A context-rich **side branch** of the LIVE session | Side investigation that needs the current reasoning in flight (e.g. reviewing a chain of logic mid-task) — avoids paying a cold spawn's full gate-boot + plan-context re-brief |
| `claude --fork-session` | A **new session** pre-loaded with an existing session's exact context | A/B comparisons: both arms start from byte-identical briefing, killing briefing variance — the canonical instrument shape (see PLAN-134 W3 pilot instruments) |

**Post-crash recipe:** `claude --continue` to restore the conversation,
then `/resume PLAN-NNN` to restore the plan. They are NOT substitutes —
`--continue` knows what was SAID; `/resume` knows what is DONE.
(Disambiguation: native `claude --resume` is the harness session picker
— conversation-level; the framework's `/resume PLAN-NNN` slash command
is plan-level.)

**Fork vs cold spawn rule of thumb:** if the side task needs the
session's accumulated context (reasoning so far, loaded files,
mid-debate state) → `/fork`. If it needs ISOLATION from that context
(independent verification, fresh adversarial eyes, cross-rail review)
→ cold spawn. Never pay a cold spawn's re-brief just to ask a question
the live context already answers — and never `/fork` an independent
verifier, because the fork inherits the parent's blind spots.

**Named sessions + agent resumption:** start long-running units as
named sessions (`claude --bg --name PLAN-NNN-<unit>`) so the resume
handle is self-describing. Record `persona → agentId` for named spawns
in the plan scratchpad (`/memory-scratchpad`); resume a named spawn via
`SendMessage` instead of re-spawning + re-briefing it — re-briefing is
the dominant cost driver of multi-wave plans.

## Less-used but useful

| Command | Use case |
|---------|----------|
| `python3 .claude/scripts/lessons.py top-k --k 10` | Last 10 lessons |
| `python3 .claude/scripts/debate-emit.py <plan> <round> <agent>` | Manual debate event emission |
| `python3 .claude/scripts/calibration-kappa.py` | Inter-rater reliability for benchmark labelling |
| `python3 .claude/scripts/budget-summary.py --plan PLAN-NNN` | Predict-budget rollup |
| `python3 .claude/scripts/skill-patch-propose.py` | Propose a skill patch (SP-NNN chain) |
| `bash .claude/scripts/check-pitfall-regression.sh` | Pre-commit pitfall scan |
| `python3 .claude/scripts/check-function-length.py` | Function-length advisory (50 LoC default; --strict to gate) |
| `python3 .claude/scripts/audit-tokens.py --window 30 --format markdown` | 6-detector ghost-token-waste audit (PLAN-047) |
| `python3 .claude/scripts/audit-telemetry.py` | Per-archetype dispatch + fabrication rate (PLAN-059) |
| `python3 .claude/scripts/ceo-diagnose.py` | Vibecoder one-shot health-check (PLAN-059) |

## What NOT to do

| Anti-pattern | Why |
|--------------|-----|
| Edit `CLAUDE.md` / `PROTOCOL.md` / `team.md` / `frontend-team.md` / `ceo-orchestration` SKILL.md mid-session | Invalidates the prompt cache; re-pays ~44,786-token gate-boot per turn (PLAN-020 §cache discipline) |
| Run hooks directly (`python3 .claude/hooks/check_*.py`) outside Claude Code | They expect Claude Code's PreToolUse/PostToolUse JSON envelope on stdin |
| Use `CEO_SOTA_DISABLE=1` as a debugging shortcut | It hides bugs you would otherwise see; use only for emergency fallback |
| Edit `.claude/agents/<archetype>.md` `model:` field without reading ADR-052 | The model split is calibrated against rubrics; arbitrary changes regress quality |
| Commit without running validate-governance | CI will catch it, but local feedback is faster |
| Cold re-spawn an agent just to continue its OWN earlier task | Re-briefing is the dominant cost driver of multi-wave plans; resume via the persona→agentId scratchpad ledger / `SendMessage` to the named spawn (see §Session continuity) |
| `/fork` an independent verifier from the working session | The fork inherits the parent's blind spots; independent verification requires a cold, cross-rail start (see §Session continuity) |

## Companion docs (open in another tab)

- [`docs/READINESS-STATUS.md`](READINESS-STATUS.md) — current verdict + calendar-soak gates
- [`docs/STATE-RECOVERY.md`](STATE-RECOVERY.md) — resume after interrupt
- [`docs/OBSERVABILITY.md`](OBSERVABILITY.md) — audit-log emit + queries
- [`docs/GOVERNANCE.md`](GOVERNANCE.md) — 35+ kill-switches catalog
- [`docs/FUNCTION-LENGTH-POLICY.md`](FUNCTION-LENGTH-POLICY.md) — 50-LoC convention + `# justified:` syntax
- [`docs/UPGRADE-PROCEDURE.md`](UPGRADE-PROCEDURE.md) — version-bump playbook

Last reviewed: 2026-06-12 (PLAN-135 W4 D4 — session-continuity doctrine added; prior full review 2026-04-29, Session 74 / v1.11.2).
