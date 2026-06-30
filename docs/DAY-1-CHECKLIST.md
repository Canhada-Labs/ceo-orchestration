# Day 1 Checklist — New Adopter Onboarding

> **For:** a new engineer joining a project that has just installed
> `ceo-orchestration`. Estimated time: **45–60 minutes** for the
> happy path. Each step lists the expected output and a pointer to
> troubleshooting if the output doesn't match.

This checklist assumes the framework has been installed in the
adopter project (someone ran `bash scripts/install.sh .` already).
If you are the **first** install for the project, read
[`docs/QUICKSTART.md`](QUICKSTART.md) first, then return here.

If anything below differs from your project, follow your project's
local CLAUDE.md / PROTOCOL.md — those are authoritative for your
team.

> **Next step after finishing this checklist:** run
> [`docs/ADOPTER-ASSESSMENT.md`](ADOPTER-ASSESSMENT.md) — a 40-question
> scenario-based validation that you actually **understand** how to
> operate the framework (vs just having installed it successfully).
> Install = green checklist. Understanding = green assessment.

---

## ⚠ Cost expectation (read before turn 1) — audit-v2 C3-P0-03

At default settings (v1.11.0), **4 of 5 canonical sub-agent
archetypes route via mitigated dispatch through `general-purpose`**
per ADR-082, which **inherits the CEO model (Opus 4.8, $5/$25 per
Mtok) by default** — NOT the Sonnet/Haiku rates ADR-052
§Role-to-model would suggest. Only `code-reviewer` runs at Opus by
*policy*; the other 4 (`qa-architect`, `performance-engineer`,
`security-engineer`, `devops`) inherit Opus by *default-CEO*.

**Implication:** the mitigated rail makes ~75% of the spawn
fan-out inherit the pricier CEO model, so sessions typically cost
more than the ADR-052 per-role table suggests. See
`docs/cost-of-operation.md` §Mitigated dispatch for the full breakdown,
historical examples, and `CEO_MITIGATION_DISABLE=1` override.
Use `ceo-cost.py` for current numbers.

If you have a fixed monthly Anthropic budget, account for the higher
mitigated-default cost OR set the override before starting.

## Pre-flight (5 min)

- [ ] You have `git`, a Python ≥ 3.9 in PATH, and `bash` ≥ 4.
- [ ] You have a working install of **Claude Code CLI ≥ 2.0**
      (`claude --version` runs).
- [ ] You have an `ANTHROPIC_API_KEY` exported in your shell.
- [ ] You have read the cost expectation block above and either
      accept the mitigated-default cost OR set
      `export CEO_MITIGATION_DISABLE=1` in your shell.
- [ ] The adopter project's repo is cloned locally.
- [ ] You have read access to the project's `CLAUDE.md`,
      `PROTOCOL.md`, and `.claude/team.md`.

---

## Step 1 — Open a fresh Claude Code session in the project

Run from the project root:

```bash
cd /path/to/your/project
claude
```

**Expected:** Claude Code launches, prints the working directory,
shows the model picker (default Opus 4.8).

**If it fails:** Claude Code not installed → see
https://claude.ai/code for install steps. Wrong directory → `cd` to
the actual project root (the one containing `CLAUDE.md`).

---

## Step 2 — Activate the CEO protocol

In the Claude Code chat, type **literally**:

```
Activate the CEO protocol and load all agents and skills
```

(Or in Portuguese: `Ativa protocolo CEO e carrega todos os agentes e skills`.)

**Expected:** Claude reads `CLAUDE.md`, `PROTOCOL.md`, the
`ceo-orchestration` skill, both team files, and reports:

```
✅ CEO protocol active — Gates 1-3 complete
Identity: CEO of <project>. Owner: <name>.
Loaded: CLAUDE.md + PROTOCOL.md + ceo-orchestration SKILL ✓
team.md + frontend-team.md ✓
Memory index ... ✓
Active plan: <PLAN-NNN>
Skill inventory (N skills): ...
```

**If it fails:**
- "Permission denied reading .claude/..." → re-run from a directory
  with read access.
- "Plan not found" → fine for a fresh project; continue to Step 3.
- Claude does not load `team.md` → your CLAUDE.md may not include
  the Gates 1-3 ritual. Compare with
  [`templates/CLAUDE.md`](../templates/CLAUDE.md) and update.
- See [`docs/TROUBLESHOOTING.md`](TROUBLESHOOTING.md) §Gate 1 fails.

---

## Step 3 — Verify governance state

Open a second terminal (keep Claude Code running) and run:

```bash
bash .claude/scripts/validate-governance.sh
```

**Expected:** the script enumerates skills, hooks, plans, and prints

```
✅ Governance validation PASSED
```

**If it fails:** read the error line carefully. Common causes:

| Error | Fix |
|-------|-----|
| "Skill X referenced in team.md but missing on disk" | Run `bash scripts/install.sh . --profile <profiles>` to re-sync skills, or edit `team.md` to remove the stale reference |
| "Hook not executable" | `chmod +x .claude/hooks/_python-hook.sh` and `.claude/hooks/check_*.py` |
| "team.md missing required section" | Restore from `templates/team.md` and re-add your personas |

For more failures, see [`docs/TROUBLESHOOTING.md`](TROUBLESHOOTING.md).

---

## Step 4 — Skim the team and skill map

In Claude Code:

```
Show the ROUTING TABLE from team.md and list the 5 most-used skills in the project.
```

**Expected:** Claude prints the routing table (work type → agent →
skill → approver) and identifies the 5 most-spawned skills from the
audit log if it exists.

**Why this matters:** the routing table is **the** map. When you
later say "review this PR", Claude doesn't pick a random reviewer —
it consults the table and spawns the matching role.

---

## Step 5 — Look at the active plan (if any)

In Claude Code:

```
/status
```

**Expected:** a single-glance overview of:

- Current plan + status (`reviewed` / `executing` / `done`)
- Phase progress
- Open vetoes
- Last commit + ahead/behind origin
- Recent audit-log activity (last 10 spawns)

**If `/status` errors:** run `python3 .claude/scripts/audit-query.py
recent --limit 10` directly to see if the audit log is healthy.

---

## Step 6 — Try a low-risk spawn

Pick a small file in the codebase. In Claude Code:

```
/spawn code-reviewer "review <path/to/some-file>"
```

**Expected:**

1. Claude calls `inject-agent-context.sh code-reviewer "..."` to
   build the spawn prompt with the persona + skill + file
   assignment.
2. The `check_agent_spawn.py` hook approves the spawn (you see no
   `GOVERNANCE: missing_skill_content` block).
3. The native `code-reviewer` agent runs (per ADR-050 it is one of
   the 5 canonical-5 native agents).
4. Output: a structured review with citations to specific lines.
5. After the spawn, run `python3 .claude/scripts/audit-query.py
   recent --limit 1` — you should see a fresh `agent_spawn` entry
   with `subagent_type: "code-reviewer"`.

**If the hook blocks the spawn:** read the `reason_code` field in
the block message. The most common reasons are:

| Reason code | Meaning | Fix |
|-------------|---------|-----|
| `missing_skill_content` | The prompt lacks `## SKILL CONTENT` or `## SKILL REFERENCE` | Use `/spawn` instead of calling Agent directly |
| `missing_file_assignment` | The prompt lacks `## FILE ASSIGNMENT` | Same — `/spawn` builds it for you |
| `effort_token_in_prompt` | A `/effort` token leaked into the spawn (CEO-only per Phase 3 of ADR-051) | Remove the `/effort` token; the CEO sets effort on the orchestrator turn, not in spawn prompts |

---

## Step 7 — Verify the audit log captured your spawn

```bash
python3 .claude/scripts/audit-query.py recent --limit 5
```

**Expected:** at least one `agent_spawn` entry from Step 6 with
fields including:

- `ts` (ISO-8601 timestamp)
- `subagent_type: "code-reviewer"`
- `skill: "code-review-checklist"`
- `has_profile: true`
- `has_file_assignment: true`
- `model: "claude-opus-4-8"` (per ADR-052 multi-model dispatch)
- `rail: "native"` (per ADR-050; or `"custom"` if your project still
  uses inline prompts)
- `hook_duration_ms: <typically 20-30 ms>`
- `usage_metadata: {...}` (if your Claude Code version exposes
  token-cache headers per ADR-051 audit-log v2.7)

**If the audit log is empty:** check
`$HOME/.claude/projects/<your-project-slug>/audit-log.jsonl` exists.
If not, the `audit_log.py` PostToolUse hook is not wired —
re-install via `bash scripts/install.sh .` and check `settings.json`
for the PostToolUse → Agent matcher.

---

## Step 8 — Check your cost so far

```bash
python3 .claude/scripts/ceo-cost.py --since 1h
```

**Expected:** an aggregated breakdown by model showing the spawn
from Step 6 (likely ≤ $0.05 for one small review).

If your audit log is missing the `tokens_*` or `model` fields, the
script warns "audit log incomplete, cost estimate unreliable" — that
is honest (per ADR-016 + ADR-052). Older spawns from before the
upgrade won't have these fields; new spawns will.

---

## Step 9 — Make a real change with the CEO orchestrating

Pick a tiny change you can describe in one sentence (typo, log
message, comment). In Claude Code:

```
Use the CEO protocol to fix the typo at <path>:<line>. I want it
PR-ready with a governance-compliant commit message.
```

**Expected workflow:**

1. CEO classifies the task as L1 (single file, no debate needed).
2. CEO spawns the appropriate IC archetype (likely a backend
   engineer or refactoring lead) per the routing table.
3. The agent edits exactly one file (verified by the file
   assignment).
4. CEO runs the test suite (per the `implement-feature` task chain)
   if your project has a stack hook for testing.
5. CEO drafts a commit message including the persona involved.
6. CEO **does not** commit unless you explicitly say "commit it".
7. After your "commit it", CEO runs `git add <specific files>` and
   `git commit` with the drafted message.

**If the CEO commits without asking:** that is a governance
violation — your project's CLAUDE.md may have explicitly authorized
auto-commit. Verify the §Anti-patterns section forbids it.

---

## Step 10 — Open a PR and verify branch protection

```bash
git push origin HEAD:my-day-1-typo-fix
gh pr create --title "fix: typo in <path>" --body "Day-1 onboarding test fix"
```

**Expected:** the PR triggers the project's required CI checks:

- `validate.yml` (governance)
- `coverage.yml` (test coverage gate, if configured)
- Stack-specific checks (e.g. `tsc --noEmit`, `pytest`, etc.)

**If branch protection isn't set up yet:** see
[`docs/BRANCH-PROTECTION.md`](BRANCH-PROTECTION.md) and ask the
project's Owner to enable required checks. The framework provides
the workflows; the Owner flips the GitHub setting.

---

## Step 11 — Bookmark the key kill-switches (5 min)

Before turn 1 in production, know which env vars give you an emergency
exit. Full catalog in [`docs/GOVERNANCE.md`](GOVERNANCE.md). The
absolute minimum to remember:

| Env var | What it does | When to flip |
|---|---|---|
| `CEO_MITIGATION_DISABLE=1` | Forces native dispatch for ALL archetypes (reverts ADR-082 default-on for non-cr) | Cost emergency / sub-agent fabrication observed |
| `CEO_MCP_SCANNER_DISABLE=1` | Disables MCP injection scanner PostToolUse hook (ADR-083) | False-positive blocks legitimate MCP call |
| `CEO_OUTPUT_SCAN=0` | Master kill for ADR-057 output-scan family | Migration windows |
| `CEO_AUDIT_HMAC_DISABLE=1` | **Disables HMAC chain** — NOT RECOMMENDED | Forensic emergency only |
| `CEO_FLUENCY_NUDGE=0` | Disables Artifact Paradox SubagentStop advisory | Adopter doesn't want fluency advisories |
| `CEO_KERNEL_OVERRIDE=<slug> CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT` | Bypasses kernel hard-deny on hook self-edit | Owner-only emergency edit of governance hooks |
| `CEO_DEBUG=1` | Verbose hook breadcrumb output to stderr | Debug only |

**Where to find more:**

- [`docs/GOVERNANCE.md`](GOVERNANCE.md) — full **55+ env-vars catalog**
  organized in 6 categories (Hook + Behavioral + Diagnostic kill-switches,
  Activation opt-ins, Budget/Cost controls, Path/Storage overrides) +
  4 frozen invariants (these CANNOT be flipped — auditable security floor).
- [`docs/CHEAT-SHEET.md`](CHEAT-SHEET.md) — single-page command +
  env-var reference (open in a second tab).
- **Budget controls (recommended for production-like adopters):**
  `CEO_BUDGET_ENFORCE=1` + `CEO_BUDGET_PER_SPAWN=0.25` blocks accidental
  Opus mega-spawns. See `docs/GOVERNANCE.md` §"Budget / Cost controls".

If you find yourself flipping a kill-switch repeatedly, that's a
governance signal — open an issue with the workflow, the framework
default may need adjustment.

---

## You're done — what to read next

| If you want to... | Read this |
|-------------------|-----------|
| Understand every slash command | [`docs/CHEAT-SHEET.md`](CHEAT-SHEET.md) |
| Predict your monthly token cost | [`docs/cost-of-operation.md`](cost-of-operation.md) |
| Author your own skill | [`docs/SKILL-AUTHORING-TUTORIAL.md`](SKILL-AUTHORING-TUTORIAL.md) |
| Respond to an incident | [`docs/INCIDENT-RESPONSE.md`](INCIDENT-RESPONSE.md) |
| Recover from corruption | [`docs/DISASTER-RECOVERY.md`](DISASTER-RECOVERY.md) |
| Resume after interruption | [`docs/STATE-RECOVERY.md`](STATE-RECOVERY.md) |
| Understand audit-log emit + queries | [`docs/OBSERVABILITY.md`](OBSERVABILITY.md) |
| Upgrade the framework | [`docs/UPGRADE-PROCEDURE.md`](UPGRADE-PROCEDURE.md) |
| Understand SLOs | [`docs/SLO-SLA.md`](SLO-SLA.md) |
| See structural limitations honestly | [`docs/HONEST-LIMITATIONS.md`](HONEST-LIMITATIONS.md) |
| Track verdict ladder + soak gates | [`docs/READINESS-STATUS.md`](READINESS-STATUS.md) |
| Map STRIDE threats to defenses | [`docs/threat-model.md`](threat-model.md) |
| Find the kill-switch I need | [`docs/GOVERNANCE.md`](GOVERNANCE.md) |
| Walk a complete first session | [`examples/first-session.md`](../examples/first-session.md) |

If a step above did not match the expected output, file an issue
with the step number and the actual output. Day-1 documentation
drift is a high-priority bug (an adopter who can't onboard is an
adopter who never adopts).

---

## Optional Day-2 actions

If everything above worked, a few small habits compound quickly:

- Run `python3 .claude/scripts/ceo-health.py` at the start of every
  session — exit 0 means governance is intact.
- Set up `bash .claude/scripts/check-framework-updates.sh` as a
  weekly check (cron or just a calendar reminder) so you learn about
  upgrades when they ship, not when they break.
- Create your first lesson via `/lesson-review` after a real
  outcome — lessons are the framework's continuous-improvement loop.
- Run `python3 .claude/scripts/audit-query.py spawn-stats --since 7d`
  weekly to see which skills are active and which are dormant. A
  dormant skill is a candidate for retirement.

Last reviewed: 2026-06-05 (Session 211 / PLAN-129 docs-parity sweep — cost note refreshed to Opus 4.8 $5/$25).
