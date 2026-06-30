# Ecosystem Parity · Cluster 1.3 — Bayesian memory prioritization

**Status:** **shipped** (Session 49 P04). CLI-only, stdlib, zero
install. Inspiration: token-savior Bayesian memory (clean-room).

## When to activate

Run this if you want to:

- Identify stale memory topics before they bloat context windows.
- Find the top-N most-referenced, most-recently-touched memory
  files for quick context bootstrap.
- Make prune decisions on long-lived memory dirs (dozens to
  hundreds of topic files).

**Skip** if:

- Your memory directory has < 10 topic files (prioritization is
  noise at that scale).
- You don't use the auto-memory system at all.

## How to use

```bash
python3 .claude/scripts/memory-prioritize.py
```

Default output is a markdown table sorted by priority descending:

```
# Memory prioritization report

| # | File                                   | Score  | Recency | Access | Centrality | Links |
|---|----------------------------------------|--------|---------|--------|------------|-------|
| 1 | `project_current_state.md`             | 0.7421 | 0.982   | 1.000  | 0.800      | 4     |
| 2 | `project_plan_045_p01_closeout.md`     | 0.7103 | 0.942   | 0.700  | 0.600      | 3     |
| … | …                                      | …      | …       | …      | …          | …     |
```

### JSONL for tooling

```bash
python3 .claude/scripts/memory-prioritize.py --format jsonl --limit 20
```

Each line is a JSON object with `name`, `score`, and a `signals`
subobject. Useful for feeding pipelines (e.g. `jq` selectors).

### Custom memory dir

The default points at this repo's own auto-memory location. Override:

```bash
python3 .claude/scripts/memory-prioritize.py \
  --memory-dir ~/.claude/projects/<your-slug>/memory
```

## The model, in 3 lines

- **Recency**: exponential decay with 168-hour half-life. New file
  ≈ 1.0, week-old ≈ 0.5, month-old ≈ 0.03.
- **Access**: git-log touches in the last 30 days, saturating at 10.
- **Centrality**: inbound markdown cross-links, saturating at 5.
- Posterior mean of `Beta(1, 1)` updated by the three signals as
  pseudo-successes. Empty history ⇒ 0.5 (prior), not 0.
  Star topic ⇒ ~0.8. Dead topic ⇒ ~0.2.

## Interpretation guide

| Score band | Meaning | Suggested action |
|---|---|---|
| > 0.60 | hot, recent + referenced | keep + always-load |
| 0.40 - 0.60 | warm | keep but don't auto-load |
| 0.20 - 0.40 | cool | archival candidate |
| < 0.20 | cold / orphan | prune after manual review |

## Example workflow — prune stale topics

```bash
# 1. Dry-run: see which files would be pruned at threshold 0.15
python3 .claude/scripts/memory-prioritize.py --format jsonl \
  | jq -r 'select(.score < 0.15) | .name'

# 2. Manually review the list. Some orphans are genuinely stale;
#    others are important low-link topics that deserve more inbound
#    links in MEMORY.md.

# 3. Execute prunes (example; adjust to your slug):
python3 .claude/scripts/memory-prioritize.py --format jsonl \
  | jq -r 'select(.score < 0.15) | .name' \
  | while read f; do
      rm "$HOME/.claude/projects/<slug>/memory/$f"
    done
```

## Read-only by design

The script never modifies the memory directory. All pruning is
explicit + adopter-owned.

## What's in the scaffold

- `.claude/scripts/memory-prioritize.py` — CLI + Python API.
- `.claude/scripts/tests/test_memory_prioritize.py` — 15 tests.
- `.claude/plans/PLAN-046/staged-code/cluster-1.3-bayesian-memory-spec.md`
  — architecture + clean-room declaration.

## Future upgrade (deferred)

Optional integration: wire the CLI into a SessionStart hook to emit
a top-N log line at session boot. SessionStart is canonical-guarded,
so this upgrade needs an Owner-signed sentinel round. Opt-in per
adopter.

## Clean-room note

The approach is inspired by the token-savior repo's Bayesian memory
concept. No code is lifted. The Beta posterior mean is textbook;
the rest is two regexes and a sort.
