---
id: PLAN-SCHEMA
title: Plan File Schema — Frontmatter, Lifecycle, Conventions
status: accepted
created: 2026-04-11
owner: CEO
depends_on: []
---

# Plan File Schema

> This document defines the **schema** that every file under `.claude/plans/`
> must conform to. Plans are first-class artifacts: they persist across
> sessions, survive reboots, outlive individual conversations, and serve
> as the CEO's durable memory when a task spans multiple Claude Code
> sessions.
>
> See `.claude/plans/README.md` for the operational workflow. This file
> is about the schema and its rationale.

## 1. File naming + directory layout

Plans live at `.claude/plans/<filename>.md`. Naming convention:

```
PLAN-<NNN>-<kebab-case-slug>.md
```

- `<NNN>` is a zero-padded 3-digit sequence number, monotonically
  increasing. First plan is `PLAN-001`, second is `PLAN-002`, etc.
- `<kebab-case-slug>` is a 2-5 word descriptor. Lowercase, hyphen-separated.
- Examples:
  - `PLAN-001-evolution.md` ← the framework evolution roadmap
  - `PLAN-002-sprint-2-hardening.md` ← next sprint's plan
  - `PLAN-007-migrate-hooks-to-python.md`

**Why sequence numbers?** They give us stable references in commits,
issues, and conversation (`see PLAN-003`). They also make directory
listing stable (lexicographic sort = chronological).

### Naming invariant (Sprint 2 addition)

**Files directly under `.claude/plans/` MUST match one of:**

1. `PLAN-<NNN>-<kebab-case-slug>.md` (a real plan), OR
2. `PLAN-<NNN>-FOLLOWUP-<kebab-case-slug>.md` (a followup plan; see §1.4), OR
3. One of the known governance files: `README.md`, `PLAN-SCHEMA.md`,
   `AUDIT-LOG-SCHEMA.md`, `DEBATE-SCHEMA.md`, OR
4. `SPRINT-<N>-<anything>.md` (sprint retrospective / planning doc; the
   validator accepts the pattern `^SPRINT-[0-9]+.*\.md$`).

No other filenames are allowed at the top level. A test fixture, an
in-progress note, or an experiment does NOT go directly under
`.claude/plans/` — it goes under `examples/` or `archive/` (see below).

**Subdirectories directly under `.claude/plans/` MUST match one of:**

1. `PLAN-<NNN>/` (matching an existing plan file, for debate
   transcripts and multi-file plan state — see DEBATE-SCHEMA.md §3)
2. `examples/` (non-plan fixtures — e.g. `examples/debate-round-1/`
   showing a debate fixture that does not correspond to any real plan)
3. `archive/` (retired plans that reached `status: done` or
   `status: abandoned` and are no longer actively referenced)
4. `WAR-ROOM/` (ad-hoc cross-plan incident coordination space; not
   plan-scoped, not plan-NNN-scoped)
5. `_templates/` (plan-template fragments used by scaffolding scripts;
   not plan files themselves)

**Why:** the plan namespace is the CEO's durable state. Mixing
example fixtures or experiments into that namespace erodes the
invariant that every `.claude/plans/PLAN-*.md` file is a real,
executable contract. Debate round 1 on PLAN-002 caught the original
fixture path (`PLAN-000-example/`) as a violation of this rule — it
looked like a plan but wasn't one. The fix was to move fixtures to
`.claude/plans/examples/` outside the `PLAN-<NNN>` namespace entirely.

**Enforcement:** mechanically enforced from **PLAN-019 VP-F4** (Sprint 14 /
Session 30). `validate-governance.sh` now refuses to pass if any
subdirectory or filename under `.claude/plans/` violates the rules above:

- subdirectories not matching `PLAN-<NNN>` / `examples` / `archive` /
  `WAR-ROOM` / `_templates` → FAIL
- files not matching `PLAN-<NNN>-<kebab-case-slug>.md` / `SPRINT-N-*.md`
  or one of the four known governance filenames (`README.md`,
  `PLAN-SCHEMA.md`, `AUDIT-LOG-SCHEMA.md`, `DEBATE-SCHEMA.md`) → FAIL

The enforcement code + tests live at
`.claude/scripts/validate-governance.sh` (section "PLAN-SCHEMA §1
invariants") and `.claude/scripts/tests/test_plan_schema_enforcement.py`
(9 tests covering valid baseline + 7 violation classes +
real-repo sanity). CODEOWNERS on `.claude/plans/PLAN-*.md` remains the
merge-side backstop for the rare case where someone bypasses the
validator locally.

**Support files** for a plan (debate transcripts per DEBATE-SCHEMA.md,
per-plan notes) live under `.claude/plans/PLAN-<NNN>/` — the
subdirectory matches the plan file's NNN. The subdirectory is
created on demand when a plan needs on-disk state (typically for
multi-round debate).

**Archived plans:** when a plan reaches `status: done` or `status: abandoned`
and is no longer actively referenced, it MAY be moved to
`.claude/plans/archive/`. Deferred until the plans directory grows
large enough to need it (Sprint 3+).

### §1.3a — Artifact retention policy (PLAN-114 F-11.16)

`PLAN-NNN/` subdirectories accumulate ceremony artifacts, staging bundles,
and wave-level outputs indefinitely. This is **intentional and acceptable**
for plans that are still active (`status: draft|reviewed|executing`).

For **done** or **abandoned** plans, the following retention rules apply:

**Permanent (never delete):**
- `PLAN-NNN/` debate transcripts (per DEBATE-SCHEMA.md §3) — audit trail
- Signed sentinel files (`approved*.md.asc`) — provenance record
- Codex pair-rail verdict files — provenance record

**Eligible for archival** (when plan reaches `status: done` AND the
`.claude/plans/archive/` subdir convention is activated):
- `staging/`, `wave-N-bundle/`, `ceremony/` subdirectories — may be
  moved to `archive/PLAN-NNN/` once the plan is done and the Owner
  confirms no in-flight references remain
- `shards/`, `scripts/` subdirs generated during plan execution

**Deferred cleanup gate (no CI enforcement currently):**
A mechanical CI gate that reports plan-subdir size at `status: done`
transition is tracked as a future hardening item. Current policy is
advisory: the validate-governance.sh §1 invariants enforce directory
_naming_ (PLAN-NNN/ only) but do not enforce artifact pruning.

**False premise guard:** `archive/` migration is explicitly deferred until
the plans directory needs it (PLAN-SCHEMA.md §1 line ~103). The retention
policy above documents the intended state; it does NOT trigger any
automated archival.

### §1.4 — Followup plans: `PLAN-NNN-FOLLOWUP` suffix convention (S127 addition)

A **followup plan** addresses residual scope descoped from a parent plan
during honest-scope-reduction or AC follow-up after shipping. It preserves
the parent's `NNN` for visual linkage, mirroring the canonical ADR
amendment convention (`ADR-NNN-AMEND-M-<slug>.md`).

**Use when:**

- Parent shipped with explicit deferred AC items (e.g., PLAN-094 Wave A.7
  → PLAN-094-FOLLOWUP Wave A.7-rem 14 residual tests).
- HARD-BLOCKER scope reduction folded `N` surfaces honestly to `M < N`
  (e.g., PLAN-093 Wave 0 reduced 10→8 surfaces, deferred to PLAN-093-FOLLOWUP).
- AC items deferred per ADR-115 §exception #1 or ADR-124 §Part 2 hotfix
  scope (where issuing a new ADR would be churn for residual close-out).

**Do NOT use when:**

- The work is net-new scope unrelated to the parent's residuals → allocate
  a new monotonic `NNN` instead (e.g., PLAN-094 → PLAN-095, *not*
  PLAN-094-FOLLOWUP).
- Pure cleanup that ships as part of the parent → fold into parent's
  closeout ceremony rather than scaffolding a separate followup plan.

**Naming:**

```
.claude/plans/PLAN-NNN-FOLLOWUP-<kebab-case-slug>.md    # plan body
.claude/plans/PLAN-NNN-FOLLOWUP/                         # artifact subdir
```

Where:

- `NNN` is the **parent plan's** zero-padded 3-digit number — *not* a
  fresh monotonic ID. That preservation is what distinguishes a followup
  from a successor plan.
- `<kebab-case-slug>` is a 2-5 word descriptor of the residual scope
  (lowercase, hyphen-separated, matching parent slug style).
- `FOLLOWUP` is literal UPPERCASE, mirroring `AMEND` uppercase in
  `ADR-NNN-AMEND-M`.

**Currently active examples:**

- `PLAN-093-FOLLOWUP-deferred-callsite-surfaces.md` (S123) — residual
  production-surface callsite work descoped from PLAN-093 Wave 0 honest
  scope reduction.
- `PLAN-094-FOLLOWUP-residual-perf-burndown.md` (S125–S126) — closes 6
  residual waves from PLAN-094 (A.7-rem / C-rem / C-tier1 / D-full /
  A.3-fail-open / A.3-rotation). Shipped as `v1.27.1` patch on top of
  PLAN-094's `v1.27.0`.

**Frontmatter contract:**

```yaml
---
id: PLAN-NNN-FOLLOWUP-<slug>     # slug-bearing + unique (matches filename);
                                 # NOT bare PLAN-NNN-FOLLOWUP — see Multi-followup
parent: PLAN-NNN                 # explicit upward link (followup-only field)
title: ...
status: draft|reviewed|executing|done   # standard lifecycle
created: YYYY-MM-DD
owner: CEO
depends_on: [PLAN-NNN]           # MUST include parent (gates execution on
                                 # parent reaching `done`)
related_commits: [<sha>...]      # parent's ship commit + followup ship commit
---
```

**Lifecycle constraints:**

A followup inherits gates from its parent. It **cannot** enter
`status: executing` until its parent reaches `status: done`. The followup
ships with its own patch tag (e.g., PLAN-094 `v1.27.0` → PLAN-094-FOLLOWUP
`v1.27.1`), bumping the parent's tag by one patch increment when the
followup scope is purely residual close-out.

**Multi-followup (supported as of S152):**

When a parent plan needs multiple followups (PLAN-112 surfaced 18 in S152
post-audit), disambiguate via kebab-slug suffix rather than numeric suffix.
Both the file (`.md`) and its artifact subdir use the same naming:

```
.claude/plans/PLAN-NNN-FOLLOWUP-<slug>.md    # plan body
.claude/plans/PLAN-NNN-FOLLOWUP-<slug>/      # artifact subdir (when shipped)
```

Authoritative regexes (`validate_governance_fast.py`):

```python
_PLAN_FILENAME_RE = re.compile(
    r"^PLAN-[0-9]{3}(-FOLLOWUP)?-[a-z0-9]+(-[a-z0-9]+)*\.md$"
)
_VALID_PLAN_SUBDIR_RE = re.compile(
    r"^PLAN-[0-9]{3}(-FOLLOWUP(-[a-z0-9]+(-[a-z0-9]+)*)?)?$"
)
```

First multi-followup shipped: `PLAN-112-FOLLOWUP-hmac-tamper-fix` (v1.39.4,
S152 2026-05-21). 17 sibling followups queued at top-level as `.md` skeletons.

**Frontmatter `id:` MUST be slug-bearing + unique (S155 — PLAN-093-FOLLOWUP
dual-id fix).** Each followup's `id:` carries the same slug as its filename
(`id: PLAN-NNN-FOLLOWUP-<slug>`), NOT the bare `PLAN-NNN-FOLLOWUP`. Two
followups of one parent sharing a bare `id:` — the PLAN-093-FOLLOWUP collision
(`-cadence-amendment` + `-deferred-callsite-surfaces` both declared
`id: PLAN-093-FOLLOWUP`) — make every id reference ambiguous. This is now
mechanically enforced: `validate_governance_fast.py::_check_plan_id_uniqueness`
(+ the `validate-governance.sh` mirror) fail on any duplicate root-level
frontmatter `id:`. A single-followup parent MAY still use the bare form, but
slug-bearing is the recommended default to keep the id collision-proof.

**Historical exception:** `PLAN-076-plan-070-followup.md` (Apr 2026) used
an older convention — its own monotonic `NNN` with `plan-NNN-followup` in
the slug. This predates the `FOLLOWUP` suffix convention codified in S127
and is **grandfathered**, not recommended for new followups.

**Rationale:**

The suffix encoding (`PLAN-NNN-FOLLOWUP`) preserves the parent's identity
in commits, GPG-signed sentinels, and shipped tags. If the followup were
renumbered (e.g., `PLAN-105` for a followup of PLAN-094), every existing
sentinel and commit message referring to "PLAN-094-FOLLOWUP" would
reference a dead ID, creating permanent ID drift. The suffix mirrors the
canonical ADR amendment convention (`ADR-040-AMEND-2`, `ADR-055-AMEND-1`)
— the parent is the durable identity; the followup is a derivative record
of residual work.

**Enforcement:** `_PLAN_FILENAME_RE` and `_VALID_PLAN_SUBDIR_RE` in
`.claude/scripts/validate_governance_fast.py` accept both
`PLAN-NNN-<slug>.md` and `PLAN-NNN-FOLLOWUP-<slug>.md` (and the matching
subdirs). Other uppercase suffixes (e.g., `PLAN-NNN-AMEND`,
`PLAN-NNN-RANDOM`) remain rejected — `FOLLOWUP` is the only blessed
plan-level suffix; `AMEND` belongs to ADRs. Test coverage at
`.claude/scripts/tests/test_ceo_boot_plan_082.py::TestPlanSchemaCheck`
(7 tests: 4 pre-S127 + 3 followup-convention).

## 2. Required frontmatter fields

Every plan file begins with a YAML frontmatter block. Required fields:

```yaml
---
id: PLAN-001                     # must match the filename prefix
title: Short human title          # 3-10 words
status: draft                    # see lifecycle below
created: 2026-04-10              # ISO 8601 date
owner: CEO | "<Persona Name>"    # who is accountable for this plan
depends_on: [PLAN-001]           # list of other plan IDs, or []
---
```

## 3. Optional frontmatter fields

```yaml
---
reviewed_at: 2026-04-11          # date the owner reviewed / accepted
reviewed_by: "Example Owner"     # human reviewer name (if Owner-approved)
completed_at: 2026-04-11         # date the plan reached status: done
abandoned_at: 2026-04-12         # date the plan was abandoned (with reason in body)
related_commits:                 # commits that implemented parts of the plan
  - 07b8f8e
  - bedad24
  - c6e3c57
context_size_at_creation: 76%    # Claude Code context fill at save time
sprint: 1                        # optional: sprint number this plan belongs to
tags: [infrastructure, ci]       # optional: topic tags
spec_ref: .claude/plans/PLAN-001/spec.md   # ADR-058 optional: pre-plan-brainstorm spec artifact

# ADR-081 budget fields (recommended for new plans 2026-04-25+)
budget_tokens: 95-130k           # CEO-context tokens (range or single estimate)
budget_sessions: 1               # how many fresh-terminal sessions
context_risk: low | medium | high # autocompact probability mid-task
external_wait: none              # ONLY for genuine external state (deploy/soak/SLA)
---
```

### ADR-081 token-as-time budget fields (recommended for plans 2026-04-25+)

Per ADR-081, new plans express effort estimates in Claude tokens
(CEO context) and sessions, not in human dev-time units. Old plans
grandfathered — no mass migration.

- `budget_tokens` — CEO-context token range (e.g. `95-130k`,
  `1.3-2M`). Excludes sub-agent contexts (each sub-agent has its
  own 1M budget).
- `budget_sessions` — integer count of fresh-terminal sessions
  needed. Each new session pays gate-boot cost ~27k tokens
  (ADR-020 cache discipline).
- `context_risk` — `low` (<150k), `medium` (150-300k), `high`
  (>300k or split-session). Mid-task autocompact probability.
- `external_wait` — `none` for CEO-only work. Use only for
  genuine external state: deploy soak windows, ADR-057 FPR
  observation, third-party API SLAs.

Legacy fields (`estimated_effort`, `dev_days`, `human_hours`)
remain accepted in old plans but deprecated for new ones. See
ADR-081 §Cost reference table for per-operation token estimates.

### The `spec_ref:` field (ADR-058)

Optional pointer to the `spec.md` artifact emitted by the
`pre-plan-brainstorm` skill before the plan was drafted. Format:

- Repo-relative path to a `.md` file under the plan's own
  subdirectory (`.claude/plans/PLAN-<NNN>/spec.md`).
- Required for L3+ plans where `CEO_BRAINSTORM_GATE=0` is NOT set
  and the task had ambiguous requirements per the skill's
  smell-tests (see `.claude/skills/core/pre-plan-brainstorm/SKILL.md`
  §When to invoke).
- Optional for L1-L2 plans, well-precedented L3+ plans, hotfixes,
  and plans where `CEO_BRAINSTORM_GATE=0` was in effect at drafting.
- Absence on a matching-condition plan is a debate Round 1 signal
  (not a hook block) — debate prompts include `## BRAINSTORM GAP`
  section requiring CEO to explain.

The plan's debate Round 1 prompts inject the spec content (or
hash reference per ADR-051 pattern) into each agent prompt as
`## SPEC CONTEXT`. See `.claude/team.md` §Spawn Protocol Step 3.

## 4. Lifecycle states (`status` field)

Plans move through a finite state machine:

```
draft ──────► reviewed ──────► executing ──────► done
  │              │                   │             ▲
  │              │                   │             │
  └──────────────┴───────────────────┴──► abandoned
```

### State definitions

| Status | Meaning | Next allowed transitions |
|---|---|---|
| `draft` | Plan is being written. Not yet ready for execution. No commits depend on it. | `reviewed`, `abandoned` |
| `reviewed` | Owner (human) has read and accepted the plan. Execution may begin. | `executing`, `abandoned` |
| `executing` | Work on this plan is in progress. At least one commit references the plan. | `done`, `abandoned` |
| `done` | All items in the plan are complete and verified. No further work. | (terminal; `executing` re-open per ADR-092, or `superseded`) |
| `abandoned` | Plan was scoped out or proven wrong. Body must contain an "Abandonment reason" section. | (terminal) |
| `refused` | An Owner-signed ADR documents that the plan's premise is rejected. Requires `refused_at` + `refused_adr`. See §11. | (terminal) |
| `superseded` | A later plan fully absorbed this plan's scope; the work was valid but is now tracked elsewhere. Requires `superseded_by: PLAN-NNN`. See §11. | (terminal) |

### Why state transitions matter

- **`draft` → `reviewed`** is the human-gate: the Owner must read the plan
  before execution begins. This is the closest the framework gets to a
  formal approval workflow without adding out-of-band tools.
- **`reviewed` → `executing`** is the self-gate: the CEO marks the plan
  as in-progress when the first commit lands. Before this, nothing
  should reference the plan except itself.
- **`executing` → `done`** is the quality gate: all success criteria
  must be met (see the plan's own `## Success criteria` section).
- **Any state → `abandoned`** is always allowed but must be documented
  with a reason. This is not failure — abandonment is a valid outcome
  when the plan's premise proves wrong.

### Sprint 2 enforcement

Sprint 1 ships the schema without automated enforcement. In Sprint 2,
a PreToolUse `Edit` hook will validate that:

1. The `status:` field is one of the legal states (`draft`, `reviewed`,
   `executing`, `done`, `abandoned`, `refused`, `superseded`).
2. Transitions follow the allowed graph (no `draft` → `done` skip).
3. Transitions to `done` require a `completed_at:` date.
4. Transitions to `abandoned` require an "Abandonment reason" section
   in the body.
5. Transitions to `superseded` require a `superseded_by: PLAN-NNN`
   frontmatter pointer (see §11).

Until then, the convention is documented and followed manually.

## 5. Required body sections

Plans of any non-trivial size SHOULD contain these sections. Trivial
plans (1-2 items, single session) MAY omit some. The section headers
are `## <name>` (level 2).

1. **`## Context`** — what led to this plan, the problem being solved, links to prior work.
2. **`## Goal`** — one sentence that defines "success" for this plan.
3. **`## Approach`** or **`## Thesis`** — the overall strategy, including alternatives considered.
4. **`## Items`** or **`## Sprint plan`** — the concrete list of work units, each with file assignment, acceptance criteria, and commit message hint.
5. **`## Open questions`** — things that need Owner input before / during execution.
6. **`## How to continue`** — the "first message" a future Claude Code session should use to pick up the plan. This is what makes plans session-durable.
7. **`## Success criteria`** — checklist the plan must satisfy to move to `status: done`.

Recommended additional sections (when applicable):

- `## Session history` — what sessions led up to this plan, what shipped, what was deferred.
- `## Debate` — critiques from spawned agents, with consensus and adjustments (Sprint 1 convention; Sprint 2 will introduce multi-round debate files).
- `## Abandonment reason` — mandatory if status is `abandoned`.
- `## Progress log` — dated checkboxes for multi-session plans. Updated each session.
- `## Reference links` — external docs, related plans, key files.

## 6. What NOT to put in a plan

- **Ephemeral task tracking.** Use `TaskCreate` / `TaskList` for in-session tasks. Plans are for things that MUST survive session boundaries.
- **Raw tool output.** A plan that pastes `git log --oneline` becomes stale the moment a new commit lands. Reference the command, not the output.
- **Secrets.** Plans are committed to the repo. `.gitignore` does not apply. Do not paste credentials, even masked.
- **Implementation details that belong in code comments.** If the detail is in the code, the plan should link to the file:line, not duplicate it.
- **Pure reports.** A "status update on what shipped" belongs in `CLAUDE.md` CHANGELOG or `MEMORY.md` handoff, not a plan file.

## 7. The `id` and `depends_on` graph

Plans form a directed graph. `depends_on: [PLAN-001]` means "this plan
assumes the work in PLAN-001 is complete (or at least `executing`)".

Allowed:
- Linear chains: `PLAN-002` depends on `PLAN-001`.
- Fan-out: `PLAN-003` depends on both `PLAN-001` and `PLAN-002`.
- Optional dependencies: `depends_on: []` for fresh plans with no priors.

Forbidden:
- Cycles. A plan cannot depend on a plan that depends on it (directly or transitively).
- Forward references. A plan cannot depend on a plan that hasn't been drafted.

Dependency satisfaction is not automatically enforced in Sprint 1; it's
a convention that Sprint 2's PreToolUse hook may check.

## 8. Relationship to other persistence layers

The framework has multiple persistence mechanisms. Pick the right one:

| Mechanism | Scope | Lifetime | When to use |
|---|---|---|---|
| **Tasks** (`TaskCreate`) | Current session | Until session ends or marked `completed` | In-session work tracking, no cross-session value |
| **Memory files** (`~/.claude/projects/<name>/memory/*.md`) | Cross-session | Permanent until manually removed | User preferences, feedback rules, project facts that every future session needs |
| **Plans** (`.claude/plans/PLAN-*.md`) | Cross-session, committed to repo | Permanent; state progresses through lifecycle | Multi-session work that needs an auditable record AND shared visibility |
| **Audit log** (`$HOME/.claude/projects/<name>/audit-log.jsonl`) | Cross-session, out of repo | Rolling (rotation in Sprint 2+) | Spawn events, governance compliance signals, debug |
| **CLAUDE.md CHANGELOG** | Cross-session, committed | Permanent; append-only | Human-readable session outcome summary |
| **Commit messages** | Permanent | Permanent | "Why this diff", with plan ID reference |

Rule of thumb: if it's "what I'm doing right now", use tasks. If it's
"what I learned", use memory. If it's "the multi-session roadmap",
use a plan. If it's "what shipped", use CLAUDE.md CHANGELOG + commit
messages.

## 9. Example frontmatters

**Fresh plan, no dependencies, in draft:**
```yaml
---
id: PLAN-007
title: Migrate Bash Hooks to Python Single-File
status: draft
created: 2026-04-15
owner: CEO
depends_on: []
---
```

**Plan in execution, with commit trail:**
```yaml
---
id: PLAN-001
title: CEO Orchestration Framework — Evolution Roadmap
status: executing
created: 2026-04-10
reviewed_at: 2026-04-11
reviewed_by: "Owner (implicit — via execution authorization)"
owner: CEO
depends_on: []
related_commits:
  - 78a1fc8  # Restructure skills into core/frontend/domains tiers
  - e617efd  # Modular settings.json + install.sh flags
  - 38ea243  # Update docs for tiered skills structure
  - ee32a70  # Purge project-specific references
  - 07b8f8e  # Fix scripts and hook for the new tiered skill structure
  - bedad24  # Save PLAN-001
context_size_at_creation: 76%
sprint: 1
tags: [framework, governance, evolution]
---
```

**Abandoned plan:**
```yaml
---
id: PLAN-005
title: Server-Side Plan Registry (Superseded)
status: abandoned
created: 2026-04-20
abandoned_at: 2026-04-22
owner: CEO
depends_on: []
---
```
…with an `## Abandonment reason` section in the body explaining what
superseded it (e.g. "merged into PLAN-006 which took a different approach").

## 10. Sprint 1 debate input (why this schema looks the way it does)

- **Architecture R9:** schema must be stable before plans start using field names, to avoid Sprint 2 migration pain. → All Sprint 1 plans use only the fields defined here.
- **Architecture U3:** flat `.claude/plans/` won't scale to 50+ plans. → `archive/` subdir convention documented, deferred to actual need.
- **Architecture U6:** cross-cutting decisions (like runtime state dir) deserve ADRs. → for now, tracked inline in plan sections rather than a separate ADR directory. May split out in Sprint 2.
- **Feedback:** avoid formalizing Owner approval too early. → `reviewed_by` / `reviewed_at` are optional. Informal chat-based review is the current contract.

---

## 11. audit-v2 ADR-092 honest-deferral framework (added 2026-04-27)

### `refused` status

Per ADR-092, `refused` is a sixth legal status (in addition to draft,
reviewed, executing, done, abandoned). Used when an Owner-signed ADR
documents that the plan's premise is rejected (e.g. PLAN-057
multi-adapter refused via ADR-084).

Required frontmatter when `status: refused`:
```yaml
status: refused
refused_at: 2026-04-27       # ISO date
refused_adr: ADR-NNN         # ADR documenting the refusal
```

### `superseded` status (added PLAN-113 W2)

`superseded` is a seventh legal terminal status. Used when a later plan
fully absorbs this plan's scope — the work itself was valid (so it is NOT
`abandoned`, which signals a wrong premise) but is now tracked elsewhere.
A plan may be superseded from any prior state, including `done` (e.g.
`PLAN-093-FOLLOWUP` and `PLAN-095-FOLLOWUP` were `done` and then folded
into `PLAN-106`).

Required frontmatter when `status: superseded`:
```yaml
status: superseded
superseded_by: PLAN-NNN      # the plan that absorbed this plan's scope
```

The `superseded_by` value MUST be a plan identifier of the form
`PLAN-NNN`. This points future maintainers forward to where the live
work now lives.

### `done → executing` re-open transition

Per ADR-092, a `done` plan can be re-opened to `executing` when the
plan was sandbagged or work was deferred. Required frontmatter:
```yaml
status: executing
reopened_at: 2026-04-27
reopen_via: ADR-NNN          # authorizing ADR (typically ADR-092)
reopen_trigger: "<concrete external signal>"
```

The re-opened plan's body MUST contain a `## Reopen criteria` section
listing the EXACT signals that move it back to `done`. Vague triggers
("when ready") are a debate Round 1 signal but currently not enforced.

### Why distinct from `abandoned`

- **`abandoned`**: operational ("the premise proved wrong mid-execution")
- **`refused`**: principled ("an ADR documents we will not pursue this")
- **`superseded`**: redirective ("the work was valid but a later plan,
  named in `superseded_by`, now owns the scope")

All three are terminal but encode different signals to future maintainers.

## 12. Liveness contract (advisory — added PLAN-065 §4.4.D)

A plan is **healthy** when the framework can answer "what moves this
forward next?" without human reconstruction of intent. Action-path
primitives a healthy plan exposes:

- **Active commit** — the most recent commit that materially advanced
  this plan (frontmatter `last_commit_sha:` populated when the plan is
  in `executing`; advisory in `reviewed`).
- **Queued continuation** — the next concrete action, named
  (e.g. "Phase 3-B unit tests" not "next step"). Lives in plan body
  §"Next" or in the most recent `## STATE-` ledger file.
- **Typed participant** — owner role from `team.md` (e.g.
  "VP Engineering", "Security Engineer"). Plan body `## Owners` block.
- **Human owner** — Owner override required field
  (e.g. "Owner 00000000"). Frontmatter `owner:` is the canonical hook.
- **Blocker chain leaf** — the actual blocking condition, not a status
  word. "PLAN-064 status:reviewed gate" is a leaf; "blocked" is not.
  Lives in plan body `## Blockers` block when status is `executing`.
- **Explicit recovery issue** — if the blocker is external, link to the
  GitHub issue, ADR, or external dependency tracker.

This contract is **advisory-only** in v1.12.0 (PLAN-065). Enforcement
via `validate-governance.sh` is scheduled for v1.13.0 (PLAN-067) once
PLAN-SCHEMA.md is added to `_CANONICAL_GUARDS` (otherwise an attacker
could weaken the contract via PR edit per Sec 3.7).

### Why advisory-only first

Audit-v3 DIM-08 finding (PLAN-066): plans accumulate metadata that
*looks* descriptive but doesn't actually move execution forward.
Authors are encouraged to populate the 6 primitives during plan
authoring; reviewers may reject plans that fail this contract during
the `draft → reviewed` transition (manual gate). Mechanical
enforcement (`validate-governance.sh` parsing the section + emitting
warnings on missing primitives) ships in PLAN-067 / v1.13.0.

### Examples

**Healthy executing plan (PLAN-065 itself):**
```yaml
status: executing
executing_at: 2026-05-04
executing_by: CEO (Session 83)
last_commit_sha: <pending>      # populated post-ceremony
owner: CEO
```
Body has `## Next` block referencing Phase 6 sweep + Owner ceremony lote.

**Healthy reviewed plan with explicit blocker leaf:**
```yaml
status: reviewed
external_wait: PLAN-064-status-reviewed
```
Body `## Blockers`: "PLAN-064 status:reviewed gate (external_wait
satisfied 2026-05-02)".

**Anti-pattern (advisory warning):**
```yaml
status: executing
# no last_commit_sha; no last_revised; no owner
```
Body has only `## Goals` — no `## Next` or `## Blockers`.
Reviewer should reject in v1.12.0; v1.13.0 mechanical gate emits
`plan_liveness_warning` advisory event.

## §AC format addendum (PLAN-110 Wave B)

> **Port source**: github/spec-kit `templates/commands/tasks.md:L378-L404`
> **ADR**: ADR-138-ac-format-priority-and-story-anchor (ACCEPTED).
> **Status**: TEXT-ONLY DOCTRINE — no parser ships in v1.39.0.

### Optional AC line format extension

New plans MAY (but need not) adopt the spec-kit AC line convention:

```
- [P0] [US1] [.claude/skills/core/<name>/SKILL.md] Description ...
```

Where:

- **`[P0]/[P1]/[P2]/[P3]`** — optional priority prefix. Defaults to `[P1]`
  if absent. Higher P = more urgent.
- **`[US1]/[US2]/...`** — optional user-story group. Wave-level if absent.
- **`[path]`** — RECOMMENDED file-anchor; already de-facto practice.

### Backward compatibility

PLANs 001-109 remain valid without modification:

- ACs without `[P?]` prefix default to `[P1]`.
- ACs without `[USn]` are wave-level (no story grouping).
- ACs without `[path]` are still valid (anchor inferable from context).

### Enforcement boundary (TEXT-ONLY)

- PLAN-SCHEMA is currently consumed by `validate-governance.sh` for
  filename/subdir invariants and by `.claude/hooks/_lib/plan_frontmatter.py`
  for YAML frontmatter parsing. **Neither parses AC-line syntax today.**
- Adding an AC-line parser is **OUT OF SCOPE** for v1.39.0.
- ADR-138 §Future Work reserves a follow-up PLAN-NNN for parser
  implementation if Owner approves at separate ceremony.

### Reference plan

PLAN-110 itself uses the new AC format in its body — eat own dog food.
See PLAN-110-spec-kit-adoption-sweep.md §4 Waves for live examples.

## 13. Verification declaration per execution unit (`Check:` lines — added PLAN-134 W1)

> **Source**: PLAN-134 W1 item 1 (VeriMAP steal, R3) — doctrine V0 of the
> deterministic-first verification cascade (V0 plan-time check declaration →
> V1 deterministic gate → V2 Codex → V3 Owner GPG).
> **Status**: MECHANICALLY ENFORCED, **prospective-only** (§13.4). The ~155
> plans created before 2026-06-12 are grandfathered and never redden.

### 13.1 The rule

Every **execution unit** — a markdown checkbox line (`- [ ]`, `- [x]`,
`- [X]`, `- [~]`) inside an enforced section (§13.3) — MUST declare its
**mechanical check** upfront: a `Check:` line naming the deterministic
command or gate (V1) that proves the unit done (tests / lint / grep /
script). Units with no mechanical proof must opt out explicitly:

```
Check: none (doc-only)
```

Declaring the check at plan-time forces the author to know, before
execution starts, what deterministic evidence will close the unit — the
V0 rung of the verification cascade. "It looks done" is not a check.

### 13.2 Machine-checkable convention (exact)

A **`Check:` declaration** is any line matching the case-sensitive regex
`(?:^|[^\w])Check:\s*\S` — the token `Check:` preceded by start-of-line or
a non-word character (so `PreCheck:` never matches), followed by a
non-empty value. Lines inside fenced code blocks (``` fences) are ignored.

A declaration **covers** checkbox items by position, in one of three ways:

1. **Inline** — the checkbox line itself contains `Check:`:

   ```
   - [ ] amend the schema — Check: pytest .claude/scripts/tests/test_x.py
   ```

2. **Continuation** — a non-heading line after a checkbox and before the
   next checkbox or heading covers the most recent preceding checkbox:

   ```
   - [ ] wire the gate
     Check: python3 .claude/scripts/validate_governance_fast.py
   ```

3. **Block-level** — a `Check:` line appearing after a heading and before
   the FIRST checkbox of that block covers EVERY checkbox in the block
   (the per-wave form). ANY heading (any level) resets block-level
   coverage:

   ```
   ### Wave 1 — schema amend
   Check: python3 -m pytest .claude/scripts/tests/ -q
   - [ ] item one
   - [ ] item two
   ```

Every enforced checkbox must be covered by at least one of the three.

### 13.3 Enforced sections

A checkbox is enforced when **any enclosing heading** (at any level — the
nearest open heading per level above the line) has a title that starts,
case-insensitively, with one of:

- `wave` (covers `Waves`, `Wave 1`, `Wave A — …`, `## Waves` + nested `### W0 …`)
- `progress log`
- `items`
- `sprint plan`

Checkboxes in other sections (e.g. `## Success criteria`, `## Open
questions`) are NOT enforced — those are outcome declarations, not
execution units. An enforced region ends at the next heading of the same
or shallower level whose title does not itself match.

### 13.4 Prospective enforcement

The gate applies ONLY to plans whose frontmatter satisfies **both**:

- `created:` is an ISO date `>= 2026-06-12` (lexicographic compare; a
  missing or non-ISO `created:` is grandfathered, fail-soft), AND
- `status:` is one of `draft` / `reviewed` / `executing` (terminal states
  — `done`, `abandoned`, `refused`, `superseded` — are exempt).

Existing plans must NOT redden: the enforcement date is strictly after the
newest pre-amendment plan (2026-06-09).

### 13.5 Enforcement location + error format

`validate_governance_fast.py::_check_plan_vcheck_declarations`, registered
in the fast profile's `run()` (so `validate-governance.sh --fast` — which
execs the python validator wholesale per the S213 bash→python delegation —
enforces it). Root-level plan files only. Violation format:

```
plan_vcheck_missing:<filename>:L<lineno>:<first 60 chars of the item text>
```

Tests: `.claude/scripts/tests/test_plan_vcheck_gate.py`. The full-profile
`validate-governance.sh` plan-frontmatter heredoc also calls
`vgf._check_plan_vcheck_declarations(repo, errors)` (wired S228 alongside
the three S213 gate functions), so BOTH profiles enforce this gate.
Quoted YAML dates (`created: "2026-06-12"`) are unquoted before the
prospective-date comparison — quoting does not dodge the gate.

## 14. Unresolved-clarification inline markers (`[NEEDS CLARIFICATION]` — added PLAN-138)

> **Source**: PLAN-138 Wave A (spec-kit round-2 residual harvest, v0.11.0) —
> the inline-marker half of spec-kit's `/clarify` loop. Complements §12's
> liveness contract and the `/spec-clarify` + `/coverage-audit` skills.
> **Status**: **ADVISORY ONLY** — a debate Round-1 signal, and explicitly
> **not a hook block**. No gate emits `permissionDecision` for a marker;
> the advisory detectors are fail-open and never increment `ERRORS`.

### 14.1 The rule

An author MAY drop an inline marker mid-text wherever an acceptance
criterion, approach paragraph, or open question still hides an
undecided choice. The canonical form is the literal token:

```
[NEEDS CLARIFICATION: <the specific question>]
```

A **LIVE** marker is one written in the actionable colon-question-bracket
form above that appears **outside** fenced code blocks **and** outside
inline-backtick spans. Definitional and illustrative uses — like the
backtick-wrapped token in this sentence, or any token inside a ```` ``` ````
fenced code block — are **EXEMPT**: they are documentation, not an open
question. The detectors below therefore skip fenced code and backtick
spans, and skip this file (`PLAN-SCHEMA.md`) entirely, because it is the
definition file and would otherwise self-trip (the S239 self-trip class).

### 14.2 Resolution lifecycle (MUST resolve before `draft → reviewed`)

A LIVE marker is permitted only while a plan is in `draft`. It MUST be
resolved before the `draft → reviewed` transition. To resolve a marker:

1. Decide the open question (typically via `/spawn spec-clarify <PLAN-NNN>`).
2. Fold the decision into the AC / Approach text it qualified.
3. Record the answer under the plan's `## Clarifications` section
   (the dated write-back format in the spec-clarify skill).
4. **Delete the inline marker** — leaving the resolved decision in prose.

A `reviewed`/`executing`/`done` plan carrying a LIVE marker is an
inconsistency: the advisory detectors flag it as `degraded` so the author
notices before relying on the plan.

### 14.3 Advisory detectors (fail-open, never block)

Three advisory surfaces report a LIVE marker; none ever blocks a session:

- `check-staleness.py` `_check_plans` emits a `plan_unresolved_clarification`
  finding (`status: degraded`, remediation `/spawn spec-clarify`) per plan
  that carries a LIVE marker (excluding this definition file).
- `validate-governance.sh` (full profile) increments `WARNINGS` (never
  `ERRORS`) once per LIVE marker, fail-open on binary/garbage plan files.
- `/coverage-audit` Pass #2 (Ambiguity) flags a LIVE marker at **HIGH**
  severity (read-only; the skill never edits a plan).

All three share the same code-span + `PLAN-SCHEMA.md` exclusion, so a
backticked example (like every token in this section) and this definition
file yield **zero** findings.

