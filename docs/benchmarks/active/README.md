# docs/benchmarks/active/ — live benchmark result artifacts

This directory holds the JSONL result artifacts emitted by authorized benchmark
runs. **It was absent at HEAD `081502e8`** (PLAN-121 audit E-finding; WS-0b prep
creates it). It is **empty of real data until the Owner authorizes a paid run.**

## Naming

```
PLAN-122-3arm-<run_id>.jsonl     # one result_row per (arm × task × run)
PLAN-122-3arm-<run_id>.report.json   # the stats.summarize_run() output
```

Each row conforms to `.claude/plans/PLAN-122/ws0b/result_row.schema.json` and
carries the `manifest_sha256` of the frozen pre-registration it adhered to.

## Provenance / integrity rules (inherited from 3-arm-protocol.md)

- A run is publishable ONLY with the independent-verifier column (protocol §5).
- No best-of-3, no post-hoc subset, no LLM judge (see the RUNBOOK §3 forbidden list).
- The synthetic dry-run output lives in `.claude/plans/PLAN-122/ws0b/_dryrun_output.jsonl`
  (clearly marked `run_id=DRYRUN-SYNTHETIC`) — it is NOT data and never lands here.

See `.claude/plans/PLAN-122/WS-0b-RUNBOOK.md` for the full execution protocol.
