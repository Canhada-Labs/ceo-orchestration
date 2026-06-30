---
name: core-codebase-onboarding
description: >
  Structured codebase orientation workflow for {{PROJECT_NAME}}. Produces an
  actionable mental map — entry points, dependency graph, architectural layers,
  hot-path identification, and a recommended reading order — before any
  modification work begins. Invoked via the /onboard <path> slash command or
  directly by any agent that must reason about an unfamiliar codebase.
owner: Codebase Onboarding (no archetype yet — slash-spawned)
inspired_by:
  - source: msitarzewski/agency-agents/engineering/engineering-codebase-onboarding-engineer.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: pattern_reference
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-06
# --- smart-loading fields (PLAN-083 Wave 0a sub-agent 0.7a) ---
domain: core
priority: 5
risk_class: low
stack: []
context_budget_tokens: 900
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 5}
  engine: {active: true, priority: 5}
  fintech: {active: true, priority: 5}
  trading-readonly: {active: true, priority: 5}
  generic: {active: true, priority: 4}
activation_triggers:
  - {event: help-me-invoked, regex: "(?i)onboard|new.?repo|tour"}
---

# Codebase Onboarding

A structured orientation beats wandering. Every minute spent mapping the
codebase pays back ten minutes in informed editing. Without a map, agents
wander depth-first, accumulate false assumptions, and make changes that
ripple through layers they never read.

This skill gives you the map before the territory.

---

## What This Skill Is (and isn't)

**Is:** Doctrine for the orientation agent spawned by `/onboard <path>`. It
prescribes a phase-ordered workflow that produces a finite, actionable
orientation report. The agent follows the phases in order, applies the hard
rules throughout, and delivers the output contract at the end.

**Is not:**
- A debugging skill (see `core/observability-and-ops`)
- A code-review skill (see `core/code-review-checklist`)
- A refactoring plan — orientation produces a MAP, not a change list
- A substitute for reading the actual code — the report is a navigation aid,
  not a summary that absolves the agent from reading files it will edit

**Paired with:** `/onboard` slash command (`.claude/commands/onboard.md`),
which is the user-facing trigger. The slash command spawns this agent; this
skill loads the doctrine.

---

## Phase Sequence

Execute phases **in order**. Do not skip phases. Do not start Phase N+1 while
Phase N is incomplete. Each phase has a goal and produces a named output that
feeds the next phase.

### Phase 0 — Governance context (goal: know the project's own rules)

Before reading any source code, read the project's self-documentation:

1. `CLAUDE.md` (or equivalent session context file at the root)
2. `README.md` or `README.rst`
3. `CONTRIBUTING.md` if present
4. `.claude/team.md` and `.claude/frontend-team.md` if present

**Output:** A 3–5 bullet list of governance constraints discovered
(e.g. "Python >= 3.9 stdlib-only", "no hardcoded handles in templates",
"tests use TestEnvContext"). These constraints gate every subsequent phase.
**If no CLAUDE.md or README exists, that is itself a finding** — record it
as a GOTCHA in the final report.

### Phase 1 — Top-level structure scan (goal: understand the directory contract)

List and categorize every top-level directory and significant file:

```
<root>/
├── src/          → production source
├── tests/        → test suite (secondary citizens during orientation)
├── .claude/      → framework governance
├── scripts/      → tooling, not production
├── docs/         → documentation
├── .github/      → CI configuration
└── ...
```

For each directory, write one sentence: what is its role in the system?
Directories you cannot categorize in one sentence are investigation targets
(mark them, do not dive in yet).

**Output:** Annotated directory tree (max 2 levels deep). Uncategorized
directories listed as investigation targets.

### Phase 2 — Entry point identification (goal: find where execution starts)

Search for the system's execution entry points. Common patterns by language:

| Language | Entry point signals |
|----------|-------------------|
| Python   | `if __name__ == "__main__"`, `console_scripts` in `pyproject.toml`, `main()` function at module root |
| TypeScript/JS | `"main"` in `package.json`, `bin/` directory, `app.ts`, `server.ts`, `index.ts` at root |
| Go | `func main()` in `cmd/*/main.go` or `main.go` at root |
| Rust | `fn main()` in `src/main.rs` or `src/bin/*.rs` |
| Bash scripts | Top-level `.sh` files with `#!/usr/bin/env bash` |

For this framework specifically, also check:
- CLI entry points in `scripts/`
- Hook entry points in `.claude/hooks/`
- Slash-command definitions in `.claude/commands/`

**Output:** Bulleted entry-point list. Each entry includes: file path,
language/runtime, and one-line description of what it starts.

### Phase 3 — Dependency graph (goal: understand what imports what)

Do NOT attempt to trace the entire import tree (that is infinite). Instead:

1. From each entry point identified in Phase 2, trace ONE level of imports.
2. Identify shared modules imported by 3 or more entry points — these are
   high-leverage files (changes ripple widely).
3. Identify external dependencies declared in `package.json`,
   `requirements.txt`, `pyproject.toml`, `Cargo.toml`, `go.mod`, or equivalent.
4. Flag any circular imports as a GOTCHA.

**Output:** Dependency summary table:

| Module | Imported by (count) | Leverage | External? |
|--------|---------------------|----------|-----------|
| `_lib/payload.py` | 6 entry points | HIGH | No |
| `anthropic` | 3 entry points | HIGH | Yes (SDK) |
| `_lib/testing.py` | tests only | LOW | No |

### Phase 4 — Architectural layers (goal: name the layers and their boundaries)

Map the codebase to one of the standard architectural patterns. Choose the
best fit — do not force-fit a pattern that does not apply:

**Layered (presentation / domain / data):**
- Presentation: what the user/caller sees (API handlers, CLI, hooks, commands)
- Domain: business logic (rules, computations, workflows)
- Data: persistence, external I/O, adapters

**Hexagonal / Ports-and-adapters:**
- Core (pure domain logic, no I/O)
- Ports (interfaces that the core defines)
- Adapters (implementations: HTTP, DB, file, MCP)

**Modular monolith:**
- Identify the module boundaries (by directory, by import discipline, or by
  namespace prefix)
- Name each module and its responsibility

**Pipeline / dataflow:**
- Identify the pipeline stages and what transforms between them

For this framework specifically, the layers are:
- Hook layer (`.claude/hooks/` — mechanical governance enforcement)
- Library layer (`.claude/hooks/_lib/` — shared stdlib-only utilities)
- Script layer (`.claude/scripts/` — tooling run by CI or users)
- Skill layer (`.claude/skills/` — doctrine loaded by agents)
- Command layer (`.claude/commands/` — slash-command definitions)
- Template layer (`templates/` — files installed into target repos)

**Output:** Layer map with one sentence per layer describing its role and its
boundary rules (what CAN and CANNOT cross the boundary).

### Phase 5 — Hot-path identification (goal: find files that matter most)

Hot paths are files where:
- Errors propagate widely (high fan-out in the dependency graph)
- Changes are frequent (high git churn)
- Performance is critical (executed in the critical path, not background)
- Security is critical (handles auth, secrets, external I/O, user input)

Identify hot paths via three signals:

**Signal A — Fan-out (from Phase 3):** Files imported by 3+ callers.

**Signal B — Git churn:** Run `git log --oneline --follow -- <file>` for
candidate files. Files with many recent commits are higher-stakes edit targets.
Do NOT conflate vendored dependency churn with application churn.

**Signal C — Security / criticality markers:** Files whose names or contents
suggest they touch auth, secrets, payments, external APIs, or hook enforcement.

**Rank the top 5** across all three signals. Ties broken by: security > fan-out > churn.

**Output:** Top-5 hot files table:

| Rank | File | Fan-out | Churn (commits, 90d) | Security? | Why it matters |
|------|------|---------|-----------------------|-----------|----------------|
| 1 | `.claude/hooks/check_agent_spawn.py` | 0 (enforcement hook) | 12 | Yes | Blocks non-compliant spawns — errors here block the entire session |
| ... | | | | | |

### Phase 6 — Test coverage sketch (goal: know which layers are tested)

Do NOT run the full test suite. Instead:

1. Find the test root(s): `tests/`, `spec/`, `__tests__/`, `*.test.ts`, etc.
2. Count test files per layer (not per line — a headcount is sufficient).
3. Identify which layers have ZERO test files (coverage blindspot).
4. Check if there is a CI configuration (`.github/workflows/`) and whether
   tests run on every PR or only on main.

**Output:** Coverage sketch table:

| Layer | Test file count | CI-gated? | Blindspot? |
|-------|-----------------|-----------|-----------|
| Hook layer | 47 files | Yes | No |
| Skill layer | 0 files | — | YES |

### Phase 7 — Orientation report (goal: deliver the actionable map)

Produce the final orientation report following the Output Contract below.
The report is the deliverable — it must be complete before the agent returns.

---

## Hard Rules

1. **Read CLAUDE.md FIRST.** Always. No exceptions. CLAUDE.md contains the
   project's own operating rules — constraints on Python version, test helpers
   to use, files not to touch, naming conventions. Starting without CLAUDE.md
   is orientation blindfolded.

2. **Tests are second-class citizens during orientation.** Do not dive into
   test files to understand the production system. Tests exist to verify
   behaviour; the production source defines it. Read tests only to check
   coverage (Phase 6), not to understand domain logic.

3. **Never claim mastery from a single pass.** The orientation report is a
   map, not a guarantee. An agent that says "I fully understand this codebase"
   after one orientation pass is over-confident. The report says "here is what
   I found" — the agent updates the map as it edits.

4. **Do not embed gotchas as assumptions.** Anything unexpected — a directory
   you cannot categorize, an import cycle, a missing CLAUDE.md, a test suite
   with zero coverage — is a GOTCHA, not a thing to silently rationalize.
   Gotchas go in the report.

5. **Git churn ≠ importance.** Vendored dependencies often have high commit
   counts (upstream rebases, lockfile updates). Do not conflate vendored-file
   churn with application hot paths. Look for churn on *application* files only.

6. **Fan-out ≠ complexity.** A utility module imported by 20 callers may be
   trivially simple (a string formatter). Fan-out flags influence, not
   complexity. Record both and let the reader decide.

7. **Do not make changes during orientation.** The orientation agent is
   read-only. It does not fix bugs it encounters. It records them as gotchas
   and returns. Any finding that warrants a fix goes into the orientation
   report with a recommendation, then stops.

8. **Respect canonical-guarded paths.** Paths listed as canonical in
   `.claude/hooks/check_canonical_edit.py` or in framework governance
   documentation must not be touched — even to add a comment — during
   orientation. These paths require GPG-signed ceremonies. Record them as
   high-risk files in the hot-path section.

---

## Output Contract

The orientation agent produces one markdown document. Save it to:
`orientation/<path-slug>-orientation.md` where `<path-slug>` is the
argument passed to `/onboard` with slashes replaced by dashes.

If the target path is the repo root (`.` or `/`), save to
`orientation/root-orientation.md`.

### Document structure

```markdown
# Codebase Orientation: <path>

**Generated:** YYYY-MM-DD
**Agent:** Codebase Onboarding (core-codebase-onboarding)
**Scope:** <what was covered>

## Executive Summary

3–5 bullets answering, in this order:
1. **What is this codebase?** (1 sentence — domain + primary language stack)
2. **Architecture pattern.** (Layered / Hexagonal / Modular monolith / Pipeline + 1 sentence why)
3. **Top risk surface.** (the single hottest file or boundary by fan-out × churn × security)
4. **Test coverage shape.** (where tests are dense vs sparse — 1 sentence)
5. **First file a new agent should read.** (citation from Recommended Reading Order)

The Executive Summary is the **only** section guaranteed to be read by every
downstream consumer (CEO, reviewer, adopter). Make it the most precise piece
of the report — no hedging, no "TBD," no aspirations.

## Governance Constraints (Phase 0)

<3–5 bullets from Phase 0>

## Directory Map (Phase 1)

<annotated tree — max 2 levels>

## Entry Points (Phase 2)

| File | Runtime | What it starts |
|------|---------|----------------|
| ... | ... | ... |

## Dependency Summary (Phase 3)

<table: module, imported-by count, leverage, external>
<external dependencies list>
<circular imports list — empty is fine>

## Architectural Layer Map (Phase 4)

**Pattern:** <Layered / Hexagonal / Modular monolith / Pipeline>

| Layer | Directory / Namespace | Role | Boundary rule |
|-------|-----------------------|------|--------------|
| ... | ... | ... | ... |

## Top-5 Hot Files (Phase 5)

| Rank | File | Fan-out | Churn (90d) | Security? | Why |
|------|------|---------|-------------|-----------|-----|
| 1 | ... | ... | ... | ... | ... |

## Test Coverage Sketch (Phase 6)

| Layer | Test files | CI-gated? | Blindspot? |
|-------|-----------|-----------|-----------|
| ... | ... | ... | ... |

## Recommended Reading Order

1. CLAUDE.md — governance rules (already read in Phase 0)
2. <entry point file> — start of execution
3. <highest fan-out module> — shared logic you will touch everywhere
4. <hot file #1> — highest-risk file for side effects
5. <test file for hot file #1> — to understand expected behaviour
6. ... (cap at 10 files)

## Gotchas

- <anything unexpected — missing files, circular imports, undocumented
  conventions, tests that don't run in CI, directories with no clear owner>

## Recommended Next Actions

- <1–3 concrete next steps for the agent or human who reads this report>
```

---

## WRONG / CORRECT Examples

### Orientation summary (Hot-path section)

```markdown
# WRONG
The codebase looks pretty well-organized. I identified a few core modules and
the entry point seems to be main.py. There are some tests. Should be fine to
start editing.

# CORRECT

## Top-5 Hot Files (Phase 5)

| Rank | File | Fan-out | Churn (90d) | Security? | Why |
|------|------|---------|-------------|-----------|-----|
| 1 | `.claude/hooks/check_agent_spawn.py` | 0 callers (it is called by the harness) | 12 commits | Yes — blocks non-compliant spawns | Any error here kills the session silently |
| 2 | `.claude/hooks/_lib/payload.py` | 6 modules import it | 9 commits | No | Central payload parsing — wrong type here propagates to all hooks |
| 3 | `.claude/hooks/audit_log.py` | 0 callers (PostToolUse) | 7 commits | Yes — writes audit trail | Errors silently drop audit events |
| 4 | `scripts/install.sh` | 0 callers (user-invoked) | 5 commits | Partial — sets up hook paths | Wrong paths here silently break all hooks in target repo |
| 5 | `.claude/hooks/_lib/testing.py` | 47 test files | 3 commits | No | TestEnvContext isolation — if broken, all hook tests pollute $HOME |
```

The WRONG example is a vague prose summary with no structured data. It
asserts "should be fine" without evidence. The CORRECT example follows the
output contract exactly — structured table, explicit evidence (fan-out counts,
commit counts, security flag), one-line rationale per file.

### Gotchas section

```markdown
# WRONG
I didn't notice any major issues.

# CORRECT

## Gotchas

- `templates/CLAUDE.md` and `.claude/skills/core/ceo-orchestration/SKILL.md`
  are canonical-guarded. Any edit requires a GPG-signed ceremony
  (see `.claude/hooks/check_canonical_edit.py` lines 12–18). Do not edit
  these files during routine work.

- The `_lib/testing.py` `TestEnvContext` must be used in ALL hook tests.
  Tests that import `os.environ` directly pollute the real `$HOME`.
  Pre-existing tests that do not use TestEnvContext are known debt
  (flagged in PLAN-019 audit); do not add new ones in the same style.

- No `CLAUDE.md` was found in the `templates/` subdirectory.
  The directory contains installation templates but no self-documentation.
  If you are modifying install templates, consult `INSTALL.md` at the root
  and `scripts/install.sh` for context.

- `scripts/upgrade.sh` exists but has no associated tests. Changes here
  are manually verified only. Any modification warrants manual smoke-test
  on a clean target repo.
```

The WRONG example is an empty assertion. The CORRECT example names specific
files, explains WHY each gotcha matters, and tells the reader what to do.

---

## Anti-Patterns

1. **Depth-first wandering without a map.** Starting with a random file and
   following imports wherever they lead. This produces an arbitrary partial
   picture, not a systematic map. Always complete Phase 1 (top-level scan)
   before diving into any single file.

2. **Ignoring CLAUDE.md / README.** Reading source code before reading the
   project's self-documentation. The project's own rules may change what "good
   code" means here — stdlib-only constraints, special test helpers, forbidden
   patterns. Reading code first means absorbing the wrong mental model.

3. **Treating tests as production code.** Diving into test fixtures to
   understand the domain. Tests verify behaviour; they do not define it.
   Production source is authoritative. Use tests only for coverage assessment
   (Phase 6).

4. **Conflating "many commits" with "important."** Vendored dependencies,
   auto-generated files, lockfile updates, and changelog entries all generate
   high commit counts. Hot-path identification requires filtering to application
   code only.

5. **Producing a prose summary instead of structured output.** "The codebase
   is well-organized with a clear separation of concerns" is not an orientation
   report. The report format is a contract — tables, bullet lists, file paths,
   commit counts. Prose summaries cannot be acted on.

6. **Making changes during orientation.** The orientation agent is read-only.
   Finding a bug during Phase 3 does not authorize a fix. Record it as a
   GOTCHA and return. Mixing orientation with editing produces reports that are
   partially invalid by the time they are read.

7. **Over-scoping the dependency trace.** Attempting to trace the full import
   graph leads to infinite recursion (A imports B imports C imports A). Phase 3
   traces ONE level from each entry point. Depth is capped by design.

8. **Skipping the reading-order section.** The recommended reading order is the
   primary deliverable for a human reader starting on the codebase. Orientation
   without a reading order produces a map with no route.

---

## Acceptance Criteria

A complete orientation run satisfies ALL of the following:

- [ ] Phase 0: CLAUDE.md (or its absence) is documented. At least 3 governance
  constraints are recorded.
- [ ] Phase 1: Annotated directory tree covering all top-level directories.
  No directory left without a one-sentence description or an explicit
  "investigation target" flag.
- [ ] Phase 2: At least 1 entry point identified (if none exist, that is a
  GOTCHA — record it). Each entry point has file path + runtime + description.
- [ ] Phase 3: Dependency summary table present. External dependencies listed.
  Circular imports checked (empty is fine; not-checked is a fail).
- [ ] Phase 4: Layer map present. Pattern named. Each layer has a boundary rule.
- [ ] Phase 5: Top-5 hot files table present. All three signals (fan-out, churn,
  security) were evaluated. Ranking rationale is visible.
- [ ] Phase 6: Coverage sketch table present. Blindspots explicitly named.
- [ ] Phase 7: Orientation report saved to `orientation/<slug>-orientation.md`.
  Report follows the output contract structure. All output-contract sections
  present (8 phases + executive summary + recommended reading order +
  gotchas).
- [ ] Gotchas section: At least 1 gotcha recorded (if truly zero gotchas, write
  "None found — this is unusual for a first orientation pass. Verify
  Phase 0–7 were completed without shortcuts.").
- [ ] No changes were made to any source file during orientation.
- [ ] No canonical-guarded files were touched.

---

## Related Skills

- `core/code-review-checklist` — after orientation, use this when reviewing
  changes to the hot files identified here
- `core/architecture-decisions` — when Phase 4 reveals a layer boundary
  violation or missing ADR, use this to draft one
- `core/observability-and-ops` — when orientation reveals missing monitoring
  in a critical layer, use this to design the gap closure
- `core/security-and-auth` — when a hot file is security-critical (Phase 5
  security flag), load this skill alongside orientation before editing
- `core/minimal-change-discipline` — after orientation, use this to scope
  changes to the minimum footprint consistent with the plan
- `ceo-orchestration` (root skill) — orientation is typically the first act
  of a CEO session on an unfamiliar repo; the session protocol in CLAUDE.md
  covers Gate 1 (read CLAUDE.md) which overlaps with Phase 0 of this skill
