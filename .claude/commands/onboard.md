---
description: Orient to an unfamiliar codebase — entry points, dependency graph, layer map, hot-path list, reading order. Usage — /onboard <path>
argument-hint: "<path>"
# --- K1 context fork: heavy analytic skill runs in a forked context (PLAN-135 W3 unit k1a) ---
context: fork
---

# /onboard — Codebase Orientation

You have been invoked to orient an agent (or a human reader) to the codebase
at the path provided. The backing doctrine is
`.claude/skills/core/codebase-onboarding/SKILL.md`.

**Argument received:** `/onboard $ARGUMENTS`

If no argument was provided, default to `.` (the repository root).

---

## What this command does

`/onboard` triggers a structured, phased orientation of the target codebase
scope. It does NOT make any code changes. It produces a single orientation
report saved to `orientation/<path-slug>-orientation.md`.

The 8-phase workflow (Phase 0–7):
1. **Phase 0** — Read governance context (CLAUDE.md, README, CONTRIBUTING)
2. **Phase 1** — Scan top-level directory structure
3. **Phase 2** — Identify execution entry points
4. **Phase 3** — Trace one-level dependency graph
5. **Phase 4** — Map architectural layers
6. **Phase 5** — Identify top-5 hot files (fan-out + churn + security)
7. **Phase 6** — Sketch test coverage per layer
8. **Phase 7** — Produce the orientation report (output contract)

---

## Procedure

### Step 1 — Parse the argument

The argument is a file-system path relative to the repository root.
Examples:
- `/onboard .` → orient to the full repository root
- `/onboard src/` → orient to the `src/` subtree
- `/onboard .claude/hooks/` → orient to the hooks subsystem only

If the argument contains shell metacharacters, leading `/` (absolute path),
path traversal sequences (`..`, `~`, `//`), or any character outside
`[A-Za-z0-9._/-]`, STOP and ask the user to supply a safe path.

Normalize the argument:
- Strip leading `./` if present
- Replace slashes with dashes for the output filename slug
- Root `.` or empty → slug `root`

After normalization, canonicalize the path using `Path(arg).resolve()` and
verify `target.relative_to(repo_root)` succeeds (raises `ValueError` on
escape). If verification fails, STOP — never proceed to Step 2 with a
target outside the repository root. Absolute paths like `/etc` MUST be
rejected at this gate.

### Step 2 — Load the backing skill

Read the full content of:
`.claude/skills/core/codebase-onboarding/SKILL.md`

This is the doctrine you will follow. Do not proceed to Step 3 until you
have read it. The skill defines the phase sequence, hard rules, output
contract, and acceptance criteria you must satisfy.

### Step 3 — Execute the 8-phase orientation (Phase 0–7)

Follow the Phase Sequence in the skill exactly, in order:

**Phase 0 — Governance context**
- Read `CLAUDE.md` at the repository root
- Read `README.md` (or `README.rst`)
- Read `CONTRIBUTING.md` if present
- Read `.claude/team.md` and `.claude/frontend-team.md` if present
- Record 3–5 governance constraints discovered

**Phase 1 — Top-level structure scan**
- List all top-level directories and significant root files
- Annotate each with a one-sentence role description
- Mark uncategorized directories as investigation targets

**Phase 2 — Entry point identification**
- Search for execution entry points per the language patterns in the skill
- Produce the entry-point table (file, runtime, description)

**Phase 3 — Dependency graph**
- From each entry point, trace ONE level of imports
- Identify high-leverage shared modules (imported by 3+ callers)
- List external dependencies from package manifests
- Flag circular imports as gotchas

**Phase 4 — Architectural layers**
- Select the best-fit pattern (layered / hexagonal / modular monolith / pipeline)
- Produce the layer map table (layer, directory, role, boundary rule)

**Phase 5 — Hot-path identification**
- Evaluate all three signals: fan-out (Phase 3), git churn, security markers
- Rank top-5 files across all signals
- Produce the hot-file table

**Phase 6 — Test coverage sketch**
- Find test roots; count test files per layer
- Identify layers with zero test files
- Check CI configuration for test gating
- Produce the coverage sketch table

**Phase 7 — Orientation report**
- Assemble all phase outputs into the report following the output contract
  defined in the skill's "Output Contract" section
- Save the report to `orientation/<slug>-orientation.md`

### Step 4 — Verify acceptance criteria

Before returning, check EVERY item in the skill's "Acceptance Criteria"
section. If any item is not satisfied, complete it before returning.

Do not return until:
- [ ] All 8 phases (Phase 0–7) complete
- [ ] Report saved to the correct path
- [ ] Gotchas section has at least 1 entry (or explicit explanation of why
  none were found)
- [ ] No source files were modified during orientation

### Step 5 — Return the orientation summary

Reply with:

1. The full path to the saved report
2. A 5-bullet executive summary covering:
   - Architectural pattern identified
   - Entry point count
   - Top hot file (rank 1) and why
   - Biggest test coverage blindspot
   - Most important gotcha
3. The recommended reading order (top 5 files only)

---

## Output location

```
orientation/<slug>-orientation.md
```

Where `<slug>` is derived from the argument:
- `.` or empty → `root`
- `src/` → `src`
- `.claude/hooks/` → `.claude-hooks`

Create the `orientation/` directory if it does not exist. Do not commit
the orientation report unless the user explicitly asks — it is a working
artifact, not a permanent record.

---

## Hard constraints (enforced by the backing skill)

- **Read-only.** The orientation agent makes no edits to any source file.
- **CLAUDE.md first.** Phase 0 is mandatory before Phase 1.
- **No mastery claims.** The report is a map, not a guarantee.
- **No canonical-guarded file edits.** Files protected by
  `check_canonical_edit.py` are read-only during orientation.

If any constraint is violated, STOP and report the violation instead of
proceeding.

---

## Example invocations

```
/onboard .
```
Orients to the full repository root. Report saved to
`orientation/root-orientation.md`.

```
/onboard .claude/hooks/
```
Orients to the hooks subsystem only. Phases 2–5 scope to that directory.
Report saved to `orientation/.claude-hooks-orientation.md`.

```
/onboard src/payments/
```
Orients to the payments module. Useful when onboarding a domain specialist
who only needs to work on payments. Report saved to
`orientation/src-payments-orientation.md`.

---

## Skill reference

Backing skill: `.claude/skills/core/codebase-onboarding/SKILL.md`

The slash command is the user-facing trigger. The SKILL.md carries the
doctrine — phase definitions, hard rules, output contract, anti-patterns,
and acceptance criteria. Always load the skill in Step 2.
