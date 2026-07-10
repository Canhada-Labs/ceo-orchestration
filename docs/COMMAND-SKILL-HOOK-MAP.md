# COMMAND → SKILL → HOOK map

<!-- GENERATED FILE — do not edit by hand.
     Regenerate: python3 .claude/scripts/gen-command-skill-hook-map.py --write
     CI drift gate: python3 .claude/scripts/gen-command-skill-hook-map.py --check -->

Derived deterministically (sorted, no timestamps) from three committed sources:

1. `.claude/commands/*.md` — slash-command definitions
2. `.claude/skills/**/SKILL.md` — skill catalog (core / frontend / domains)
3. `.claude/settings.json` — governance hook registrations

**Scope honesty.** Every edge below is a *textual declaration derivable on disk*, not a runtime trace: a command “references” a skill iff the skill's directory slug appears in the command body (backticked, or as a `.claude/skills/` path segment). Hook guards are *path-class* guards — they protect whole file classes uniformly, so per-skill guard differentiation is not derivable from disk. This map documents the wiring of the EXISTING catalog and its discovery surface; it structurally cannot measure greenfield domains and is not a green-light for adding skills (PLAN-153 debate A must-fix 4). Cells carry identifier tokens only; free prose from scanned files is deliberately not embedded.

## 1. Commands → skills / scripts (`.claude/commands/*.md`)

| Command | Skills referenced | Backing scripts referenced |
|---|---|---|
| `/agent-budget` | — | `.claude/scripts/budget-summary.py`, `.claude/scripts/cc-analytics-pull.py` |
| `/architect` | `agent-architect` | `.claude/scripts/architect-bundle-validate.py`, `.claude/scripts/inject-agent-context.sh` |
| `/audit-page` | — | — |
| `/audit-tokens` | `terse-mode` | `.claude/scripts/audit-tokens.py` |
| `/ceo-boot` | — | `.claude/scripts/ceo-boot.py` |
| `/ceo-info` | — | `.claude/scripts/ceo-info.py` |
| `/context-budget` | `ceo-orchestration` | `.claude/scripts/context-budget.py` |
| `/debate` | `architecture-decisions`, `devops-ci-cd`, `financial-correctness-and-math`, `security-and-auth` | `.claude/scripts/debate-emit.py`, `.claude/scripts/inject-agent-context.sh` |
| `/effort` | — | — |
| `/fan-plan` | — | `.claude/scripts/fan-plan-parser.py` |
| `/goap` | — | `.claude/scripts/goap-planner.py` |
| `/lesson-evolve` | — | `.claude/scripts/lesson_evolve.py` |
| `/lesson-review` | — | `.claude/scripts/lessons.py` |
| `/memory-scratchpad` | — | `.claude/scripts/scratchpad.py` |
| `/onboard` | `codebase-onboarding` | — |
| `/pitfall` | — | `.claude/scripts/pitfall-query.py` |
| `/resume` | — | `.claude/scripts/session-graph-build.py`, `.claude/scripts/session-resume.py` |
| `/self-test` | — | `.claude/scripts/self_test.py` |
| `/skill-health` | — | `.claude/scripts/audit-query.py`, `.claude/scripts/audit-verify-chain.py`, `.claude/scripts/skill-health.py` |
| `/skill-review` | — | `.claude/scripts/skill-patch-apply.py` |
| `/spawn` | `ceo-orchestration` | `.claude/scripts/inject-agent-context.sh` |
| `/squad-install` | — | `.claude/scripts/squad-import.py` |
| `/status` | — | `.claude/scripts/audit-query.py`, `.claude/scripts/cc-analytics-pull.py` |
| `/terse` | `terse-mode` | `.claude/scripts/audit-tokens.py`, `.claude/scripts/ceo-cost.py` |
| `/veto-check` | — | `.claude/scripts/veto-check.py` |

## 2. Skills referenced by commands (reverse index)

| Skill | Tier(s) | Referenced by |
|---|---|---|
| `agent-architect` | core | `/architect` |
| `architecture-decisions` | core | `/debate` |
| `ceo-orchestration` | core | `/context-budget`, `/spawn` |
| `codebase-onboarding` | core | `/onboard` |
| `devops-ci-cd` | core | `/debate` |
| `financial-correctness-and-math` | domain:fintech | `/debate` |
| `security-and-auth` | core | `/debate` |
| `terse-mode` | core | `/audit-tokens`, `/terse` |

Skills with no command edge are cataloged in §5 totals; the full per-skill inventory lives in the generated block of `.claude/skills/core/ceo-orchestration/SKILL.md` (`generate-skill-inventory.sh`) and is not duplicated here.

## 3. Hook registrations (`.claude/settings.json`)

Events sorted alphabetically; within an event, rows keep registration order (= runtime chain order).

| Event | Matcher | Hook | Timeout (s) |
|---|---|---|---|
| ConfigChange | `(all)` | `check_config_change.py` | 5 |
| PostCompact | `(all)` | `check_postcompact_reinject.py` | 5 |
| PostToolUse | `Agent` | `audit_log.py` | 5 |
| PostToolUse | `Agent` | `check_confidence_gate.py` | 10 |
| PostToolUse | `Agent` | `check_output_safety.py` | 10 |
| PostToolUse | `Agent` | `check_subagent_fabrication.py` | 5 |
| PostToolUse | `Agent` | `(inline)` | 5 |
| PostToolUse | `Read` | `check_skill_reference_read.py` | 3 |
| PostToolUse | `(all)` | `check_output_secrets.py` | 5 |
| PostToolUse | `Edit\|Write\|MultiEdit` | `check_skill_bootstrap_post.py` | 5 |
| PostToolUse | `WebFetch\|WebSearch` | `check_webfetch_injection.py` | 5 |
| PostToolUse | `mcp__.*` | `check_mcp_response.py` | 5 |
| PostToolUse | `mcp__codex__codex\|mcp__codex__codex-reply` | `check_codex_response.py` | 5 |
| PostToolUse | `Bash` | `check_bash_canonical_forensic.py` | 5 |
| PostToolUse | `Edit\|Write\|MultiEdit` | `accel_dispatch.py` | 20 |
| PostToolUseFailure | `(all)` | `check_output_secrets.py` | 5 |
| PreCompact | `(all)` | `check_precompact_continuity.py` | 5 |
| PreToolUse | `Agent` | `check_agent_spawn.py` | 5 |
| PreToolUse | `Bash` | `check_bash_safety.py` | 5 |
| PreToolUse | `Bash` | `check_adversary.py` | 5 |
| PreToolUse | `Edit\|Write\|MultiEdit` | `check_plan_edit.py` | 5 |
| PreToolUse | `Edit\|Write\|MultiEdit\|mcp__.*` | `check_canonical_edit.py` | 5 |
| PreToolUse | `Edit\|Write\|MultiEdit` | `check_protocol_semver_cascade.py` | 5 |
| PreToolUse | `Edit\|Write\|MultiEdit` | `check_skill_patch_sentinel.py` | 5 |
| PreToolUse | `Edit\|Write\|MultiEdit` | `check_tier_policy.py` | 5 |
| PreToolUse | `Edit\|Write\|MultiEdit\|mcp__.*` | `check_arbitration_kernel.py` | 5 |
| PreToolUse | `Bash` | `check_scratchpad_access.py` | 5 |
| PreToolUse | `Agent` | `check_budget.py` | 5 |
| PreToolUse | `Read` | `check_read_injection.py` | 5 |
| PreToolUse | `Edit\|Write\|MultiEdit` | `check_pair_rail.py` | 60 |
| PreToolUse | `mcp__codex__codex\|mcp__codex__codex-reply` | `check_codex_filewrite.py` | 30 |
| PreToolUse | `Agent\|Bash\|Edit\|Write\|MultiEdit\|Read\|Glob\|Grep\|WebFetch\|WebSearch\|NotebookEdit\|TodoWrite\|Task\|mcp__.*` | `check_anti_ceo_overhead.py` | 5 |
| PreToolUse | `Bash` | `check_cost_envelope.py` | 5 |
| PreToolUse | `Bash\|Edit\|Write\|MultiEdit` | `check_worktree_writer.py` | 5 |
| PreToolUse | `Edit\|Write\|MultiEdit` | `check_config_protection.py` | 5 |
| SessionEnd | `(all)` | `SessionEnd.py` | 5 |
| SessionStart | `(all)` | `SessionStart.py` | 5 |
| SessionStart | `(all)` | `turbo_sessionstart.py` | 5 |
| Setup | `init` | `check_setup_verification.py` | 15 |
| Stop | `(all)` | `Stop.py` | 5 |
| Stop | `(all)` | `codex_review_user_code.py` | 130 |
| Stop | `(all)` | `review_loop.py` | 15 |
| Stop | `(all)` | `check_closeout_guard.py` | 5 |
| SubagentStart | `(all)` | `check_subagent_start.py` | 5 |
| SubagentStop | `(all)` | `check_fluency_nudge.py` | 5 |
| UserPromptSubmit | `(all)` | `UserPromptSubmit.py` | 5 |

## 4. Surface guards (registered-hook source scan)

Derivation rule: a registered hook guards a surface iff its source file under `.claude/hooks/` contains the literal `.claude/skills` / `SKILL.md` (skill surface) or `.claude/commands` (command surface). This over-approximates — a textual mention is treated as guard involvement — and it applies to the whole surface, never to one skill or command.

| Surface | Guarding hooks (source references the surface) |
|---|---|
| Skill files (`.claude/skills/**`, `SKILL.md`) | `SessionStart.py`, `audit_log.py`, `check_agent_spawn.py`, `check_anti_ceo_overhead.py`, `check_canonical_edit.py`, `check_protocol_semver_cascade.py`, `check_skill_bootstrap_post.py`, `check_skill_patch_sentinel.py`, `check_skill_reference_read.py` |
| Command files (`.claude/commands/**`) | — |

## 5. Catalog totals

- Commands: 25
- Skills (SKILL.md-bearing dirs): 166 — core 42, frontend 8, domain 116 (across 36 domains)
- Skills with >=1 `activation_triggers` entry: 65
- Hook registrations: 46 across 13 events (45 unique hook labels)
