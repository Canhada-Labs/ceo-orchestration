---
description: Draft a new squad bundle from a domain brief — /architect "<brief>"
allowed-tools: Read, Write, Glob, Grep, Bash, Agent
---

# /architect — Draft a candidate squad bundle

You are the CEO. The Owner has supplied a domain brief and wants a
draft of a candidate squad. Spawn the **Agent Architect** with the
`agent-architect` skill loaded; the meta-agent emits a 5-file bundle
into a sandboxed plan subdirectory.

## Arguments received

`/architect $ARGUMENTS`

Parse `$ARGUMENTS` as a single domain brief (a quoted string). If the
brief is empty or whitespace-only, STOP and ask the Owner for a brief.

## Procedure

### Step 1 — Pick or create the plan ID

The bundle lands under `.claude/plans/PLAN-NNN/architect/round-1/`.
Prefer the most recent active plan ID (status: `executing` or
`reviewed`); if none, create a new placeholder plan stub.

If creating a new placeholder:
- Pick the next available `PLAN-NNN` (zero-padded 3-digit).
- Write a minimal stub at `.claude/plans/PLAN-NNN-architect-<slug>.md`
  with frontmatter `status: draft` and a thesis paragraph
  describing the brief.
- Use that PLAN-NNN for the bundle directory.

### Step 2 — Set the recursion guard env var

Before spawning the Architect, set `CEO_ARCHITECT_ACTIVE=1` in the
spawn's environment. This activates the recursion guard in
`check_agent_spawn.py` — any nested Architect spawn is blocked with
reason code `architect_recursion`.

If your spawn tool doesn't support per-spawn env, use:

```bash
CEO_ARCHITECT_ACTIVE=1 bash .claude/scripts/inject-agent-context.sh \
    "Agent Architect" "<brief>"
```

### Step 3 — Spawn the Agent Architect

Use the standard spawn protocol:

1. Run `bash .claude/scripts/inject-agent-context.sh "Agent Architect" "<brief>"`
   to assemble the persona + skill + pitfalls + **top-K past lessons**
   scaffold. PLAN-008 Phase 3: when `CEO_ARCHITECT_ACTIVE=1` is in the
   environment, the script tags injected lessons with `consumer=architect`
   and emits a `lesson_read` audit event with the brief's ≥4-char words
   merged into ranking keywords. Loop closes via benchmark outcome
   tracking; `/architect`-specific hit/miss classification is deferred
   to Sprint 9 (see PLAN-008 Non-goals).
2. Add the file assignment:
   ```
   ## FILE ASSIGNMENT
   - MAY edit (write only): .claude/plans/PLAN-NNN/architect/round-1/*.md, *.yaml, *.template
   - MAY read: any path in the repo
   - FORBIDDEN: any canonical path (.claude/team.md, .claude/frontend-team.md,
                .claude/pitfalls-catalog.yaml, .claude/skills/**/SKILL.md,
                .claude/skills/domains/**/team-personas.md,
                .claude/skills/domains/**/pitfalls.yaml)
   ```
3. Add the task description: "Draft a 5-file squad bundle for the
   following brief: '<brief>'. Output every file under
   `.claude/plans/PLAN-NNN/architect/round-1/`. Follow the
   agent-architect SKILL §What the meta-agent emits exactly.
   Every proposed skill's frontmatter sketch in
   `skill-selection.draft.md` MUST include a `paths:` activation-glob
   list BY DEFAULT (PLAN-135 K1 — non-empty glob strings matching the
   files whose edit should surface the skill), and heavy
   analytic/audit-class skills MUST declare `context: fork`. Contract:
   `SPEC/v1/skill-frontmatter.schema.md`; lint: LINT-FM-40/41."
4. Add acceptance criteria: "Bundle passes
   `.claude/scripts/architect-bundle-validate.py
   .claude/plans/PLAN-NNN/architect/round-1/`."

### Step 4 — Run the bundle validator

After the Architect returns, run:

```bash
python3 .claude/scripts/architect-bundle-validate.py \
    .claude/plans/PLAN-NNN/architect/round-1/
```

If validator exits non-zero, the bundle is incomplete or violates a
positioning invariant. Report the failure to the Owner; the Owner
decides whether to (a) re-spawn with additional guidance, (b) edit
the bundle manually, or (c) abandon.

### Step 5 — Surface the bundle to the Owner

Report:

- Bundle directory path
- File-by-file summary (1 line per file)
- Validator outcome (pass/fail)
- Next step: "Owner reviews the bundle. To adopt: copy
  `approved.md.template` to `approved.md`, fill in `Approved-By: @<handle>`,
  then migrate the drafts into canonical paths. The
  `check_canonical_edit.py` hook will allow the canonical edits
  once the sentinel is valid."

## Anti-patterns

1. **NEVER spawn the Architect without `CEO_ARCHITECT_ACTIVE=1`.** The
   recursion guard relies on it.
2. **NEVER edit canonical paths in the same session as the Architect.**
   Wait for the sentinel; if the brief is small enough to do
   inline, it doesn't need the Architect.
3. **NEVER skip Step 4.** The validator catches structural issues
   before the Owner wastes time on review.
4. **NEVER use the Architect to generate squads with real-person
   names.** Validator rejects them; if the Owner asks to override,
   STOP and explain ADR-009 §positioning.

## References

- `agent-architect` skill in `.claude/skills/core/agent-architect/`
- `architect-bundle-validate.py` in `.claude/scripts/`
- `check_canonical_edit.py` hook in `.claude/hooks/`
- ADR-009 (squad contract) + ADR-010 (canonical-edit sentinel)
