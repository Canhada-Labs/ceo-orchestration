# FOR-EMPLOYEES — You're new on the project

> **PT-BR:** [FOR-EMPLOYEES.pt-BR.md](FOR-EMPLOYEES.pt-BR.md) (mirror).

> Aimed at employees/collaborators who will use Claude Code on
> projects where the Owner has already installed the ceo-orchestration
> framework. If you are the Owner setting things up for the first
> time, read `QUICKSTART.md`.

## What changes for you

When you open Claude Code inside a project with `ceo-orchestration`
installed, Claude is **no longer the generic Claude**. He becomes the
**CEO of the project**. That changes how he answers your questions:

**Before:**
> You: "Add a `created_at` field to the users table"
> Claude: _edits the file, writes the migration, commits_

**Now:**
> You: "Add a `created_at` field to the users table"
> Claude (as CEO): "Got it. This touches the table + migration + RLS.
> Let me draft a plan first. Phase 0: what timestamp format is
> expected? Phase 1: Principal Data Engineer reviews the schema.
> Phase 2: implementation. Phase 3: tests. Approved?"

Looks bureaucratic. **It's intentional.** Three reasons:

1. **Avoids rework** — catching the wrong intent up front costs less
   than redoing it at the end
2. **Right experts in the loop** — a schema change without the Data
   Engineer's review turns into a production bug
3. **Audit trail** — the company needs to know what each person +
   each AI touched (LGPD, audit, postmortem)

## Rules of engagement (PROTOCOL.md in plain language)

### 1. Always ask for a plan before code

"Draft a plan for X" > "Write code for X"

If you ask to jump straight to code, the CEO will respond "I need to
plan first". It's not stubbornness, it's protocol.

### 2. L1-L2 doesn't need debate, L3+ does

- **L1** = single-file fix, typo, log message → CEO does it directly
- **L2** = 2-3 files, small feature → CEO plans + executes
- **L3** = 3+ modules, schema change, auth, financial → CEO
  **must run a debate** with 2-3 specialists first

If your task is L3+ and you say "just do it", the CEO refuses and
calls `/debate`. Respect the gate.

### 3. VETOs are mandatory, not a suggestion

There are 2 universal vetoers:
- **Staff Code Reviewer** — any merge
- **Staff Security Engineer** — any change touching auth/token/input

If the Security Engineer says "no", **don't do it**. This isn't an
opinion — it's a mechanical gate. If you insist, the CEO escalates
to the Owner.

### 4. Don't edit canonical files

These files have a mechanical hook blocking direct edits:

- `.claude/team.md`
- `.claude/frontend-team.md`
- `.claude/pitfalls-catalog.yaml`
- `.claude/skills/*/SKILL.md`

If you need to change one of these, use `/architect` — the Agent
Architect meta-creates the change through the correct process (with
a sentinel signed by the Owner).

### 5. Destructive commands are blocked

The `check_bash_safety` hook blocks:
- `rm -rf <anything>`
- `git reset --hard`
- `git push --force` (accepts `--force-with-lease`)

Use alternatives:
- `rm -rf /tmp/foo` → `mv /tmp/foo /tmp/foo.trash-$(date +%s)`
- `git reset --hard` → `git stash` + decide afterward
- `git push --force` → `git push --force-with-lease`

## Useful commands (slash commands)

Type into the Claude Code chat:

### `/spawn "Agent Name" <task>`
Spawns a specific specialist. Example:
```
/spawn "Principal Performance Engineer" avalia latência do endpoint /api/search
```

The CEO automatically loads persona + skill + file assignment.

### `/debate start PLAN-NNN "proposta"`
Starts a multi-specialist debate on a plan. Example:
```
/debate start PLAN-042 "Mudar de PostgreSQL para CockroachDB"
```

3 agents (VP Eng + Staff Security + DevOps by default) critique from
their respective angles. The CEO synthesizes consensus.

### `/architect "<brief>"`
Meta-command: asks the Agent Architect to assemble a new squad for a
specific domain. E.g. "create a squad for edtech compliance".

### `/status` (new in v1.0)
Quick overview:
- Which plan is executing
- Last 5 spawns
- Lessons learned in the last 24h
- Audit-log warnings

### `/audit-page <url>`
Audits a frontend page across 16 UX/accessibility dimensions.

## What to do when you don't know

1. **Read `CLAUDE.md`** — it's the project's master context
2. **Type `/status`** — see where the project stands
3. **Ask the CEO** — "Activate the CEO protocol. I need to do X.
   Which specialists should be involved?"
4. **Query the audit log** — `python3 .claude/scripts/audit-query.py summary`

## Privacy and security

- All logs live in `~/.claude/projects/<your-project>/audit-log.jsonl`
  — outside the repo, in your home directory
- Prompts sent to Claude Code are stored there (but redacted —
  secrets and PII are stripped before logging)
- Nothing is sent to the ceo-orchestration maintainer or any external
  party
- The project Owner can query with `audit-query.py`

## When to ask the Owner for help

- A hook is blocking you and you don't understand why
- The CEO refused a task and you disagree
- You want to add a new skill/squad that doesn't exist yet
- A veto fired and you think it's a false positive

## Flags you should NOT touch

Some environment variables control experimental framework modes.
**Don't set them in your session.** If a hook is blocking you and you
suspect these flags, call the Owner.

| Flag                        | Default | Who sets | Why                 |
|-----------------------------|---------|----------|---------------------|
| `CEO_CONFIDENCE_ENFORCE`    | 0       | Owner    | Activates blocking mode of the confidence gate (Sprint 9). Advisory by default. |
| `CEO_CONFIDENCE_BYPASS`     | 0       | Owner    | Escape hatch when enforce jams a legitimate session. |
| `CEO_PRUNE_EXECUTE`         | 0       | Owner    | Enables `--execute` on prune-lessons (Sprint 8). |
| `CEO_CONFIDENCE_MAX_CLAIMS` | 200     | Owner    | Overrides the CLAIM-tokens cap per output. |
| `CEO_ARCHITECT_ACTIVE`      | (auto)  | /architect | Set by the slash command. Don't touch. |

If you set one of these by accident, run `unset <VAR>` in your shell
or reopen the terminal.

## Anti-patterns (what NOT to do)

Don't say "Ignore the protocol, just write the code"
→ CEO will refuse. Protocol is not optional.

Don't copy numbers from stale docs without cross-checking source
→ The CEO corrects you and you take a "strike" (3 strikes = persona
rewritten, new name)

Don't spawn an agent and skip validating the output
→ CEO verifies with grep/read. If an agent invents a file that
doesn't exist, strike.

Don't say "I'll do it fast, skip the tests"
→ Hook + Staff Code Reviewer veto merge without tests. Won't fly.

Don't commit without the Owner asking for it
→ Anti-pattern #7 of PROTOCOL.md. Only commit when the Owner
explicitly says "commit it".

## Summary in one paragraph

You'll be interacting with a Claude that behaves like a **CEO**: asks
for a plan before acting, calls in specialists, respects vetoes, logs
everything, and occasionally blocks you when you're being careless.
Accept that it's intentional — the framework exists to prevent the
mistakes you'd make without it. When in doubt, `/status` or read
`TROUBLESHOOTING.md`.
