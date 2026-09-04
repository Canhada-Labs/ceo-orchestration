# AC-14 — the two Gate-1/Gate-2 sentences the CLOSEOUT must change

> **Nothing here is applied.** `PROTOCOL.md` is Gate-1 cache-stable and
> `.claude/commands/effort.md` is the effort surface; both are edited at an
> explicit closeout, never mid-wave (CLAUDE.md §0). This file is the written
> instruction for that closeout, produced with the classifier
> (`docs/task-classifier-2b.md`, AC-14) so the edit is derived and not recalled.

## 0. First correction, before any edit

PLAN-186 W5-US2 says "teto de effort documentado na skill `effort`". **There is
no `.claude/skills/core/effort/SKILL.md`** — the effort surface on disk is the
slash command `.claude/commands/effort.md` (99 lines). Any closeout that goes
looking for the skill path will find nothing and may create a second surface
for the same fact.

Derived, so the closeout does not hunt for a mirror that is not tracked:
at base `76578f33`, `git ls-files '*effort.md'` prints exactly ONE
path, `.claude/commands/effort.md` (99 lines), and there is no
`.claude/skills/core/effort/SKILL.md`. The instrument is `git ls-files` and not
`find`, because `find` answers differently depending on whether the maintainer
has built the plugin: in a fresh worktree it returns one hit, in a tree with
`dist/` built it returns two — the second under `dist/ceo-plugin/commands/`,
a BUILD OUTPUT that is gitignored (`.gitignore` line `dist/`) and
produced by `scripts/build-plugin.py`
(`copy_dir(".claude/commands", "commands", "*.md")`). Both readings were taken
at this base sha; `git ls-files` is the one that cannot drift with a build.
Nothing has to move in the same patch; a plugin rebuild propagates the edit.

## 1. `PROTOCOL.md` — one sentence ADDED, none rewritten

Anchor (`PROTOCOL.md`, the `### Debate` block, verbatim — located by text,
not by line, so this instruction survives an edit above it):

```
### Debate
For tasks of **blast radius L3+** the CEO spawns **2 or more agents in parallel**
with the same plan and asks each:
```

Proposed insertion, immediately after the `### Debate` paragraph:

> Blast radius decides **gating** — whether a debate, an ADR and an Owner
> signature are required (V0–V3 below). It does **not** decide routing: which
> model and which effort a task gets is decided by the artefact's
> **specification uncertainty** (`PLAN-186 §2b`), through the decision
> procedure in `docs/task-classifier-2b.md`. The two axes are independent by
> design — an L1 change to a gate is still R1 (`xhigh`), and an L3+ prose
> derivation is still R2. Fixing one axis with the other is the mistake the
> §2b round-1 correction (C3) was written to prevent.

Why an insertion and not a rewrite: `blast radius L3+` is the correct predicate
for the sentence it is in (debate is gating). The defect is the ABSENCE of the
routing axis, so the cure is additive; rewriting the gating sentence would
re-open a settled rule.

## 2. `.claude/commands/effort.md` — one paragraph ADDED after the guard table

Anchor (`.claude/commands/effort.md`, verbatim): `## Task-class guard table (Perf-2 fold)`
— the table immediately below it keys the default level by TASK CLASS
(`arch`, `code_gen`, `debate`, `finops`, `file_read`, `line_audit`, `digest`).

Proposed insertion, immediately after that table's kill-switch paragraph:

> **The ceiling scales with specification uncertainty, not with blast radius.**
> The level a task deserves is decided by which `PLAN-186 §2b` row it lands in
> (`docs/task-classifier-2b.md` is the decision procedure): a task that DEFINES
> a question — gate, oracle, acceptance criterion, refutation, or the DESIGN of
> a census predicate — takes `xhigh`; a task that EXECUTES a derivation whose
> question is already fixed takes `high`; synthesis and VETO take `max`. A
> large, well-specified change does not earn a higher tier by being large, and
> a one-line change to an oracle does not earn a lower one by being small.

## 3. The disagreement the classifier surfaced — a DECISION for the closeout, not a fact

Running the classifier against the guard table produces three concrete
mismatches. They are stated as an open decision because the two tables may be
measuring different mechanisms (the guard table governs the live adapter's
thinking budget; §2b governs which model/effort a dispatched agent gets), and
that question is not settled on disk:

| §2b row | §2b effort | nearest guard-table class | its default | delta |
|---|---|---|---|---|
| R1 DEFINE a question | `xhigh` | `arch` | `high` | one tier low |
| R3 code/config derivation | `high` | `code_gen` | `med` | one tier low |
| R4 research under a fixed question | `high` | `file_read` / `line_audit` / `digest` | thinking **forced off** | contradiction, not a delta |

The R4 row is the sharp one: a research task classified as `file_read` has
thinking forced OFF by the guard table while §2b puts it at `high`. Either
(a) the guard table's classes are a different axis and the closeout says so in
one sentence, or (b) they are the same axis and three defaults change. **The
classifier does not decide this** — it only proves the two surfaces disagree
and names where.

## 4. What must NOT be changed at the closeout

- `PLAN-186 §2b` itself. The classifier refines it; if a case in
  `.claude/plans/PLAN-186/w5/classifier-cases.json` cannot be walked to its row,
  the defect is in the procedure, not in the matrix.
- The `_SLASH_EFFORT_TABLE` / `_SLASH_BUDGET_TABLE` value tables in
  `_lib/model_routing.py`: `effort.md` mirrors them and the code is the source of
  truth. This closeout adds doctrine, not values.

## 5. A constraint the closeout MUST resolve: the adopter cannot see the doc

**Both** insertions above point a reader at `docs/task-classifier-2b.md`, and
**both** of them land in a file the installer SHIPS. Measured at this base:

- `scripts/install-npm.sh` stages `scripts templates .claude SPEC VERSION
  LICENSE README.md PROTOCOL.md` -- **no `docs/`** -- and the npm package's own
  `files` whitelist in `npm/package.json` names that same set, also without
  `docs/`; the staging loop further excludes `.claude/plans/PLAN-[0-9]*`, so
  neither `docs/task-classifier-2b.md` nor `.claude/plans/PLAN-186/w5/`
  reaches an npm/adopter install;
- `scripts/install.sh` DOES install `.claude/commands`, so the `effort.md`
  paragraph travels -- and would arrive carrying a pointer to a file that is
  not there (v2 rail r7 [P2]);
- and `PROTOCOL.md` is on BOTH of those shipped lists, so the section 1
  insertion travels too -- in fact it is the MORE widely installed of the two
  surfaces.

That last bullet is what this section had wrong before the land rail
(r1 [P2]): it said only ONE insertion landed in a shipped file, and it offered
as an option "keep the pointer only in `PROTOCOL.md`, which is staged". That
option did not remove the dangling reference, it RELOCATED it -- into the more
widely installed of the two surfaces -- while the paragraph below forbids
exactly that. An option that violates the invariant stated three lines under it
is not an option.

So the closeout has exactly **two** honest options, and must pick one in
writing:

(a) **ship the classifier** -- add `docs/task-classifier-2b.md` to the
`install-npm.sh` staged list AND to the `files` whitelist in
`npm/package.json` AND to whatever `install.sh` copies; and, if the machine
check is meant to travel too, the `w5/` artefacts, which today are dropped by
the `.claude/plans/PLAN-[0-9]*` exclusion; or

(b) **make BOTH references framework-internal in words** -- phrase the
`PROTOCOL.md` sentence and the `effort.md` paragraph so that each names the
framework repository explicitly ("in the framework repo: ..."), so an adopter
reading an installed file is never sent to a path they did not receive.

The one thing the closeout may not do is leave an installed file pointing at a
path adopters do not receive -- and that test has to be applied to `PROTOCOL.md`
and `.claude/commands/effort.md` alike, not to one of them.
