# `.claude/plans/` — How Plans Work

> **Plans are the framework's durable memory across sessions.** A plan is
> a Markdown file under `.claude/plans/` that describes a multi-session
> unit of work, carries its own state machine, and survives reboots. If a
> task spans more than one Claude Code session, it goes here.
>
> For the **schema** (frontmatter, lifecycle, field definitions), see
> `PLAN-SCHEMA.md`. This README is about the **workflow**.

## When to create a plan

Create a plan when ANY of these is true:

- The work will span more than one session.
- The work has 3+ distinct items, any of which is non-trivial.
- Execution blast radius is L3+ (3+ modules, per PROTOCOL.md).
- The Owner asked for "a roadmap" or "the plan" or "a proposal".
- You are about to run out of context and want to save state for the next session.

Do NOT create a plan for:

- Single-file fixes.
- Research tasks that produce a one-shot report.
- Decisions that fit inside a commit message.
- In-session work tracking (use `TaskCreate` instead).

## How to create a plan

1. **Pick the next free sequence number.** `ls .claude/plans/PLAN-*.md | tail -1` to see the last. Increment.
2. **Create `.claude/plans/PLAN-<NNN>-<slug>.md`** with frontmatter per `PLAN-SCHEMA.md`:
   ```yaml
   ---
   id: PLAN-<NNN>
   title: <short human title>
   status: draft
   created: <YYYY-MM-DD>
   owner: CEO
   depends_on: []
   ---
   ```
3. **Write the required body sections** (see PLAN-SCHEMA.md §5):
   - Context, Goal, Approach, Items, Open questions, How to continue, Success criteria.
4. **If the plan was created at high context fill** (>60%), end with an
   explicit "How to continue" section that contains the **literal first
   message** the next session should paste to resume execution.
5. **Commit the plan file** with message: `Save PLAN-<NNN>: <title>`.
6. **Report the plan ID + commit SHA to the Owner** so they can reference
   it in chat.

## Lifecycle workflow

```
[Create] → draft
         └──(Owner reads + accepts)──► reviewed
                                        └──(First commit references the plan)──► executing
                                                                                   └──(All success criteria met)──► done
                                                                                   │                                  └──(Later plan absorbs scope)──► superseded
                                                                                   └──(Plan proven wrong / scope cancelled)──► abandoned
                                                                                   └──(Owner-signed ADR rejects premise)──► refused
```

States `superseded` and `refused` are terminal; see PLAN-SCHEMA.md §11 for required frontmatter
(`superseded_by: PLAN-NNN` and `refused_at` + `refused_adr` respectively).

### Draft → reviewed

The Owner reads the plan (in chat, by opening the file, or by the CEO
summarizing it). If the Owner says "ok go", "approved", "execute", or
similar, the CEO MAY transition the plan to `status: reviewed` and set
`reviewed_at: <date>`. `reviewed_by: "<name>"` is optional until
Sprint 2 introduces formal enforcement.

Before this transition, **resolve every inline `[NEEDS CLARIFICATION: …]`
marker** the draft still carries (PLAN-SCHEMA §14). Decide the open
question (often via `/spawn spec-clarify <PLAN-NNN>`), fold the decision
into the AC/Approach text, record the answer under `## Clarifications`,
then delete the inline marker. The markers are ADVISORY — `check-staleness.py`,
`validate-governance.sh`, and `/coverage-audit` Pass #2 only WARN on a LIVE
marker; none blocks the transition.

### Reviewed → executing

At the moment the first commit landing code that implements the plan is
created, the CEO updates the plan to `status: executing`. Add the commit
SHA to `related_commits:` in frontmatter. Update on every subsequent
commit that touches the plan.

### Executing → done

When all items in `## Success criteria` are checked, the CEO:

1. Updates `status: done` and adds `completed_at: <date>`.
2. Commits the status change with message: `Complete PLAN-<NNN>: <title>`.
3. Optionally moves the file to `.claude/plans/archive/` if the plan is
   unlikely to be referenced again (Sprint 2+ convention).

### Any state → abandoned

If the plan's premise turns out to be wrong, or it's superseded by a
new plan:

1. Update `status: abandoned` and add `abandoned_at: <date>`.
2. Add an `## Abandonment reason` section to the body with 2-4 sentences
   explaining what changed.
3. Commit: `Abandon PLAN-<NNN>: <one-line-reason>`.

Abandonment is NOT failure. It's a valid outcome. Don't delete abandoned
plans — they're part of the project's audit trail.

## Resuming a plan in a fresh session

This is the killer feature of plans. To resume PLAN-007 in a new Claude
Code session:

1. Start a new session in the project directory.
2. Read `PLAN-007-xxx.md`. Specifically, read the `## How to continue`
   section — it contains the literal first message to paste.
3. Paste that message. The CEO will:
   - Re-read governance (`PROTOCOL.md`, `ceo-orchestration` skill, etc.)
   - Re-read the plan
   - Re-verify the state of the repo against `related_commits:`
   - Continue from where the last session left off

**If the plan is in `status: executing` but related_commits doesn't
reach HEAD**, some work was done in the interim that the plan doesn't
know about. The CEO should read `git log --oneline` to reconcile before
continuing.

## Referencing plans in commits

Every commit that implements part of a plan SHOULD mention the plan ID
in the commit message. Preferred format:

```
<one-line summary>

<body paragraph>

Refs: PLAN-<NNN> item <N>
```

Or inline in the title for small commits:

```
PLAN-001 item 3: add CI GitHub Action
```

This creates a bidirectional link: `git log --grep="PLAN-001"` shows
every commit that touched the plan, and the plan's `related_commits:`
frontmatter shows the same list from the plan's side.

## Directory layout

```
.claude/plans/
├── README.md                     # this file
├── PLAN-SCHEMA.md                # schema definition
├── AUDIT-LOG-SCHEMA.md           # subordinate doc (not a plan — explains the audit log hook schema)
├── DEBATE-SCHEMA.md              # debate round schema
├── PLAN-NNN-<slug>.md            # active and historical plans (flat; monotonic sequence numbers)
├── PLAN-NNN/                     # per-plan subdirs for artifacts (sentinels, verify/, batches/)
└── archive/                      # plans moved here when done/abandoned (optional; YAGNI until flat dir is unwieldy)
```

Plans stay in the flat root until the directory becomes too cluttered.
Historical plans are not deleted — they are part of the audit trail.

## Governance relationship

Plans are **not** the same as the governance protocol:

- **PROTOCOL.md** defines how the CEO operates (spawn protocol, debate rules, vetoes, 3-strike).
- **`ceo-orchestration/SKILL.md`** is the CEO's operating manual (how to run the team, how to phase work).
- **`team.md`** is the roster (who does what).
- **Plans** are the multi-session work artifacts that the CEO executes
  under the above rules.

A plan does NOT override PROTOCOL.md. If a plan seems to say "skip the
debate", it's wrong and the CEO should refuse. If a plan seems to say
"spawn without loading skills", the hook will block it.

## Quick operational commands

```bash
# List all plans
ls .claude/plans/PLAN-*.md

# Find plans that mention a commit
grep -l "07b8f8e" .claude/plans/PLAN-*.md

# Find all commits that reference a plan
git log --oneline --grep="PLAN-001"

# Check plan status
grep "^status:" .claude/plans/PLAN-*.md

# Find draft plans (not yet accepted)
grep -l "^status: draft$" .claude/plans/PLAN-*.md
```

## Anti-patterns (NEVER do)

1. **NEVER write code without a plan** if the work spans multiple sessions or modules. The "how to continue" contract is broken if the plan is invented retroactively.
2. **NEVER edit a `done` plan to add new items.** Create a follow-up plan instead.
3. **NEVER commit a plan with placeholder sections like "TBD" or "{{xxx}}".** Draft status is meant for incomplete plans; fill them out before `reviewed`.
4. **NEVER delete a plan.** Abandon it, but keep the file.
5. **NEVER write a plan that only Claude understands.** The Owner must be able to read and approve it.
