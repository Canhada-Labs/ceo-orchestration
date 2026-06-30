---
command: /resume
description: Resume a plan across sessions using its derived graph
usage: "/resume PLAN-NNN [--json]"
idempotent: true
allowed-tools: Bash
---

# /resume — Continue a plan across sessions

Projects a "how to continue this plan" prompt for a given `PLAN-NNN`.
The output is **strictly derived** from:

- `audit-log.jsonl` (typed events per `_lib/audit_emit.py`)
- `git log --follow .claude/plans/PLAN-NNN-*.md`
- Plan markdown frontmatter + `## Deferred` / `## Owner action items`
  sections

No new state is written. No audit events are emitted by this command.
See **ADR-038** and **SPEC/v1/session-graph.schema.md**.

## Arguments received

`/resume $ARGUMENTS`

- first positional token → `--plan PLAN-NNN` (required)
- `--json` anywhere → machine-readable output
- `--rebuild` anywhere → bypass cached graph, rebuild in-memory

## Procedure

### Step 1 — Kill-switch check

Respect `CEO_SOTA_DISABLE`:

```bash
if [ "${CEO_SOTA_DISABLE:-0}" = "1" ]; then
  echo "SotA features disabled (CEO_SOTA_DISABLE=1). /resume is a no-op." >&2
  exit 0
fi
```

### Step 2 — Parse args

Extract the plan id (must match `PLAN-NNN`) and flags.

### Step 3 — Run the backing script

```bash
python3 .claude/scripts/session-resume.py --plan "$PLAN_ID" ${JSON:+--json} ${REBUILD:+--rebuild}
```

Interpret exit codes:

- `0` → print stdout verbatim.
- `2` → invalid args. Print stderr to the user (already user-friendly).
- `3` → plan not found. Surface stderr and suggest `ls .claude/plans/`.
- other → surface stderr; do not silently succeed.

### Step 4 — Guidance after printing

After the projection, remind the user (human mode only — skip on `--json`):

- "This projection is derived from audit-log + git + plan markdown. Nothing was written."
- "If the graph is stale, rerun with `--rebuild`."
- "To materialize an encrypted snapshot, run `python3 .claude/scripts/session-graph-build.py --plan $PLAN_ID`."

## Freshness model

- `session-resume.py` reuses a cached graph from
  `$HOME/.claude/projects/<proj>/session-graphs/<plan>-<ts>.json*` IF
  its mtime is < 24h. Otherwise it rebuilds in-memory.
- `--rebuild` forces a fresh derivation.

## Idempotency

Running `/resume PLAN-NNN` twice in a row **must** produce identical
output modulo the `generated_at` timestamp. The command does not
mutate the audit log, plan files, or any state store.

## Fail-open

If `session-resume.py` is missing (old install), surface the gap and
stop — do not pretend the plan has no state.

## Exit codes

- 0 — projection emitted (or kill-switch short-circuit)
- 2 — usage error
- 3 — plan not found
