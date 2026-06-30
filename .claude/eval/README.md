# `.claude/eval/` — PLAN-133 C3 real-task reward benchmark

A NIGHTLY / on-demand benchmark of ~10 real software-engineering tasks, each
with a **deterministic verifier** emitting a scalar `reward` in `[0, 1]`. It
measures whether the CEO orchestration can actually *do* small real tasks, not
just pass synthetic skill scenarios (that is the C1 `run-skill-benchmark.py`
job).

## Why nightly / on-demand, never per-push

Each task drives a real CEO orchestration attempt — **this spends real
subscription quota** (cost == quota, not dollars; S220 / ADR-144). Running it on
every push would blow the S220 17→12min push budget and draw quota unbounded.
So it is wired as a nightly schedule (or manual dispatch), guarded by:

- `--skip-if-no-key` — no `ANTHROPIC_API_KEY` ⇒ exit 0 `SKIPPED` (no-op).
- a **quota cap** (`--quota-cap-attempts`, default 30) — refuses to start if
  `tasks × repetitions` exceeds the cap unless `--allow-expensive`.
- **serial** execution — tasks run one at a time (the orchestration fans out
  internally; whole-task parallelism would multiply peak quota and defeat the
  cap).
- **worst-of-N + flaky** — reuses the C1 aggregation (`CEO_BENCH_AGGREGATION`,
  default `worst`); a task whose repetitions disagree on pass/fail is `flaky`.

## Files

| File | Role |
|---|---|
| `runner.py` | discover tasks → per-task isolated workdir → orchestration attempt(s) → deterministic verify → worst-of-N aggregate → emit. |
| `reporter.py` | render the results dict as a harbor-style markdown table (reward + status + quota cost + turns + flaky). |
| `tasks/` | one module per task, each exposing a `TASK` dict with `setup` + `instruction` + `verify`. |

## Running it

```bash
# Nightly no-op when unconfigured:
python3 .claude/eval/runner.py --skip-if-no-key

# Real run (spends quota — configure the launcher first):
export ANTHROPIC_API_KEY=...                  # required (real quota)
export CEO_EVAL_EXEC_CMD='claude -p "$(cat {prompt_file})" --cwd {workdir}'
python3 .claude/eval/runner.py --repetitions 2 --output-json /tmp/eval.json

# Re-render a saved run:
python3 .claude/eval/reporter.py /tmp/eval.json
```

`CEO_EVAL_EXEC_CMD` is an operator-supplied shell template with `{workdir}`,
`{prompt_file}`, `{max_tokens}` placeholders. The runner NEVER hardcodes a
launcher and NEVER fetches a URL or runs any `aaif-goose` binary (PLAN-133 §2).

## Adding a task

Drop a `tasks/tNN_<slug>.py` module exposing a `TASK` dict (schema in
`tasks/__init__.py`). The verifier MUST be deterministic and fail-safe (return a
low reward on a missing/broken tree, never raise). Run the unit suite
(`.claude/scripts/tests/test_eval_c3.py`) to confirm discovery + verifier
behavior with a fake executor — **zero quota** in tests.

## Nightly CI

A scheduled workflow (`.github/workflows/eval-nightly.yml`, staged as a proposal
in `PLAN-133/staged/C3.proposal.md`) invokes `runner.py --skip-if-no-key` so the
job is a clean no-op on runners without a key and a real measurement where a key
is present. It is NOT part of `validate.yml` (per-push) by design.

## Audit telemetry

The runner emits one `eval_task_completed` event per task (int-only fields:
reward in basis points, attempts, flaky 0/1). That closed-enum action is a
canonical `_lib/audit_emit.py` edit, staged in `PLAN-133/staged/C3.proposal.md`.
Until it lands the emit is a silent no-op (unknown-action breadcrumb), so the
runner is correct both before and after the Owner-GPG ceremony.
