---
description: Spawn a named agent with full persona + skill context. Usage — /spawn "<Agent Name>" <task description>
argument-hint: "\"<Agent Name>\" <task description>"
---

# /spawn — Governance-compliant agent spawn

You are about to spawn a named agent from the team roster. The governance
protocol requires that every named-agent Agent-tool call carry:

1. **`## AGENT PROFILE`** — the persona block from `.claude/team.md`
   (or `frontend-team.md` / `domains/*/team-personas.md`)
2. **`## SKILL CONTENT`** — the full SKILL.md for the agent's primary skill
3. **`## FILE ASSIGNMENT`** — explicit files this agent may edit (or "read-only")
4. **`## TASK`** — the task description
5. **`## RELEVANT PITFALLS`** — any matching pitfalls from the catalog

The hook at `.claude/hooks/check_agent_spawn.py` (Python single-file,
invoked via `_python-hook.sh`) blocks any Agent spawn that matches a
team-member name in its description but is missing the `## SKILL CONTENT`
section. This slash command is the safest way to construct a compliant
prompt.

**Dispatch path (PLAN-061 / ADR-082):** the injector resolves the rail
per archetype default. `Staff Code Reviewer` runs on the **native**
`subagent_type=code-reviewer` rail (full tool grant + ADR-052 VETO floor).
Every other archetype defaults to **mitigated** dispatch — the injector
emits a `## DISPATCH MITIGATION` header instructing this slash-command
flow to call the Agent tool with `subagent_type="general-purpose"` plus
the persona injected via `## SKILL CONTENT`. This bypasses the H4 rail
anomaly per ADR-080 (custom subagent_types receive only Grep+Glob from
the runtime despite frontmatter declaring full tools).

Per-call override (diagnostic): pass `--dispatch=native` or
`--dispatch=mitigated` to the injector in Step 3. Operator-scope
override: `CEO_DISPATCHER_MODE=native|mitigated` env var; universal
kill-switch `CEO_MITIGATION_DISABLE=1` (forces native everywhere).

## Arguments received

The user invoked: `/spawn $ARGUMENTS`

## Argument parsing contract

The first token is the **AgentName**. If the name contains spaces, it
**must** be wrapped in double quotes. Everything after the AgentName is
the task description.

- `/spawn Sofia review src/gateway.ts` → AgentName=`Sofia`, task=`review src/gateway.ts`
- `/spawn "VP Engineering" design ADR for the audit pipeline` → AgentName=`VP Engineering`, task=`design ADR for the audit pipeline`
- `/spawn "Staff Security Engineer" audit src/auth.ts for timing oracles` → ditto

**Validation:** `AgentName` must match `^[A-Za-z][A-Za-z0-9 _-]{0,60}$`.
Shell metacharacters, regex metacharacters, and path traversal attempts
are rejected by `inject-agent-context.sh` with exit code 2.

## Procedure

Follow this exact sequence:

### Step 1 — Parse the arguments

Extract the AgentName (first token, or the quoted phrase if double-quoted)
and the remaining task description. If parsing is ambiguous (no clear
AgentName, or unbalanced quotes), STOP and ask the user to clarify.

### Step 2 — Verify the agent is on the roster

Read `.claude/team.md` (and `frontend-team.md` if it exists, and
`.claude/skills/domains/*/team-personas.md` if any domain profile is
installed). Confirm the AgentName appears there, either as a concrete
persona (e.g. `**Sofia Nakamura**` in a SKILL MAP row) or as an archetype
heading (e.g. `**VP Engineering**`). If the agent is NOT on the roster,
STOP — list the available archetypes/personas to the user and ask which
one they meant.

### Step 3 — Run the injector

Run the injection script to build the compliant prompt scaffold:

```bash
bash .claude/scripts/inject-agent-context.sh "<AgentName>" "<task description>"
```

Use the literal `"..."` around AgentName. Capture the stdout — that is
the persona + skill + pitfalls scaffold. If the script exits non-zero:

- **Exit 1** (usage) — you forgot the AgentName.
- **Exit 2** (invalid name) — whitelist rejection. Show the user the
  validation rule and ask for a cleaner name.

### Step 4 — Define the FILE ASSIGNMENT

The injector does NOT know which files the task touches. **YOU (the CEO)**
must determine this before calling the Agent tool. Possible modes:

- **Read-only research task:** `FILE ASSIGNMENT: read-only — all files`
- **Single-file edit:** `FILE ASSIGNMENT: may edit src/foo.ts; forbidden: everything else`
- **Multi-file edit:** list each allowed file; list any file another
  parallel agent is already editing as forbidden
- **Worktree mode:** `FILE ASSIGNMENT: isolated worktree; merge after`

Apply the anti-collision rule from `PROTOCOL.md`:
- 0 files in common with any other running spawn → parallel OK
- 1–3 files in common → run sequentially
- 4+ files in common → collapse into one spawn

### Step 5 — Define ACCEPTANCE CRITERIA and OUTPUT FORMAT

State how you will verify the agent is done. Examples:
- "Return a structured critique with sections 1-5 (see PROTOCOL.md debate)"
- "Produce an ADR following the architecture-decisions template"
- "Return a diff of src/foo.ts with the fix + a short changelog"

### Step 6 — Assemble the final Agent-tool prompt

The final prompt structure is:

```
<scaffold from inject-agent-context.sh — contains ## AGENT PROFILE,
 ## SKILL CONTENT, ## RELEVANT PITFALLS, ## TASK placeholder>

## FILE ASSIGNMENT
<your explicit assignment from Step 4>

## TASK
<the task description, expanded into the format you want>

## ACCEPTANCE CRITERIA
<from Step 5>

## OUTPUT FORMAT
<structured format: sections, max-length, citations required, etc.>

## RESTRICTIONS
- Do NOT edit files outside your assignment.
- Do NOT spawn sub-agents of your own (only the CEO does that).
- If you hit a blocker, STOP and report to the CEO instead of
  improvising around it.
```

### Step 7 — Call the Agent tool

Use the Agent tool with:
- `description`: a short phrase INCLUDING the agent name so the governance
  hook can detect the named spawn (e.g. `"VP Engineering ADR draft"`)
- `subagent_type`: per the dispatch path (PLAN-061 / ADR-082) —
  - If the injector emitted a `## DISPATCH MITIGATION` header (default
    for non-`code-reviewer` archetypes): use `general-purpose`. The
    persona is already injected via `## SKILL CONTENT` in the prompt.
  - If no mitigation header (default for `code-reviewer`, or operator
    forced native): use the matching custom subagent type
    (`code-reviewer`, etc.) or fall back to `general-purpose` for
    research-only / `Explore`.
- `prompt`: the full assembled prompt from Step 6

The PostToolUse hook (`audit_log.py`) will automatically record this
spawn to `$HOME/.claude/projects/<project>/audit-log.jsonl` with the
skill extracted from the prompt's `SKILL:` line, plus `hook_duration_ms`
and rotation at 10 MB. You do not need to do anything additional for audit.

### Step 8 — Validate the agent's output

When the agent returns:

- [ ] Did the agent edit **only** files from its file assignment?
  (`git diff --name-only` — the existing PostToolUse reminder surfaces
  this prompt.)
- [ ] Does the output follow the requested format?
- [ ] Does the output cite files/lines when making factual claims?
- [ ] Are the claims verifiable against code? (grep / Read)

If any check fails, this is a **strike** for the agent. See the
3-Strike Policy in `.claude/skills/core/ceo-orchestration/SKILL.md`.

## Examples

### Example 1 — Research (read-only) spawn

```
/spawn "Principal Security Engineer" audit the audit-log hook for secret leakage
```

CEO procedure:
1. Parse: AgentName=`Principal Security Engineer`, task=`audit the audit-log hook for secret leakage`
2. Verify in team.md → archetype present (`**Principal Security Engineer**` is in the ROUTING TABLE)
3. `bash .claude/scripts/inject-agent-context.sh "Principal Security Engineer" "audit the audit-log hook for secret leakage"`
4. FILE ASSIGNMENT: read-only — may read any file; may NOT edit anything
5. Acceptance: structured vuln list with severity, file:line citations, MUST-FIX / NICE-TO-HAVE, VERDICT
6. Assemble + call Agent tool with description `"Security audit of audit-log hook"`

### Example 2 — Single-file edit spawn

```
/spawn "Staff Backend Engineer" fix the timing oracle in src/auth.ts:94
```

CEO procedure:
1. Parse: AgentName=`Staff Backend Engineer`, task=`fix the timing oracle in src/auth.ts:94`
2. Verify on roster
3. `bash .claude/scripts/inject-agent-context.sh "Staff Backend Engineer" "..."`
4. FILE ASSIGNMENT: may edit `src/auth.ts`; forbidden: everything else
5. Acceptance: `timingSafeEqual` used, tests still pass, no new dependencies
6. Call Agent tool with description `"Backend engineer auth.ts fix"`

## Anti-patterns (NEVER do)

1. **NEVER call the Agent tool directly with just a one-line task.** The hook will block it if the description contains a team member name and the prompt lacks `## SKILL CONTENT`. Even if the hook allows it (generic description), you are bypassing governance.
2. **NEVER skip Step 2 (roster verification).** Inventing persona names = cosmetic spawn = forbidden.
3. **NEVER skip Step 4 (file assignment).** Even for research tasks, write "read-only" explicitly.
4. **NEVER use `$ARGUMENTS` without parsing.** If the user sent a malformed argument set, stop and ask.
5. **NEVER edit `inject-agent-context.sh` to relax the name validation.** The whitelist is a security boundary, not a convention.
