# PLAN-183 AC-2 — the delivered CI executed inside Smoke Install

Second leg of the AC-2 evidence: the `run:` steps of the delivered CI template
are EXECUTED, in order, on a hosted Linux runner, by
`scripts/tests/run-activated-workflow.py` inside the `Run smoke install` step
of `.github/workflows/smoke-install.yml`. Two independent samples below.

Unlike the disposable-repository runs (see `github-run-33896213436.md`), these
two runs belong to `Canhada-Labs/ceo-orchestration` itself, so `gh run view
<id> --log` from a clone of this repository reaches them directly.

## Provenance and selection rule

```
gh run view 33874751633 --log --job=101028957620   # job `smoke`
gh run view 33809424817 --log --job=100827520483   # job `smoke`
```

Each raw log line has the shape `<job>\t<step>\t<timestamp> <message>`; the
quoted blocks keep only the part after the last TAB. The lines quoted are
exactly those whose message matches

```
^<timestamp> ==> (activated workflow|step \d+/11)
```

in log order — the banner, every one of the eleven per-step banners, and the
final verdict. The rule is a single regex, so no step can be silently
dropped from the quotation.

## LOG 33874751633 — commit `8003b65`, 2026-09-04

```
2026-09-04T12:56:40.3818551Z ==> activated workflow: .github/workflows/validate.yml (job 'validate', 11 steps: 10 run, 1 uses; timeout-minutes 15)
2026-09-04T12:56:40.3834438Z ==> step 1/11: Checkout — SKIPPED (runner-provided: uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2)
2026-09-04T12:56:40.3835252Z ==> step 2/11: Run validate-governance.sh
2026-09-04T12:56:42.7512104Z ==> step 3/11: Run check-skill-health.sh --ci
2026-09-04T12:56:43.0661136Z ==> step 4/11: Run check-pitfall-regression.sh
2026-09-04T12:56:43.0821762Z ==> step 5/11: Contamination check (no private-project/personal refs outside allowlist)
2026-09-04T12:56:43.3469148Z ==> step 6/11: Placeholder lint (core/frontend skills only)
2026-09-04T12:56:43.3630776Z ==> step 7/11: Validate settings.json and YAML catalogs
2026-09-04T12:56:43.3950667Z ==> step 8/11: Shellcheck hooks and scripts (excluding legacy/)
2026-09-04T12:56:49.5262382Z ==> step 9/11: Check tier boundaries (core/frontend must not reference domains)
2026-09-04T12:56:49.6410428Z ==> step 10/11: actionlint
2026-09-04T12:56:50.0566650Z ==> step 11/11: Hook and script executable bits
2026-09-04T12:56:50.0647134Z ==> activated workflow PASSED: 10 run step(s) executed, 1 runner-provided step(s) skipped by name
```

Execution window, first `run:` step to verdict: `2026-09-04T12:56:40.3835252Z` to `2026-09-04T12:56:50.0647134Z`.

## LOG 33809424817 — commit `35f33a8`, 2026-09-03

```
2026-09-03T21:49:56.2448379Z ==> activated workflow: .github/workflows/validate.yml (job 'validate', 11 steps: 10 run, 1 uses; timeout-minutes 15)
2026-09-03T21:49:56.2453475Z ==> step 1/11: Checkout — SKIPPED (runner-provided: uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd  # v6.0.2)
2026-09-03T21:49:56.2454870Z ==> step 2/11: Run validate-governance.sh
2026-09-03T21:49:58.5643092Z ==> step 3/11: Run check-skill-health.sh --ci
2026-09-03T21:49:58.8791556Z ==> step 4/11: Run check-pitfall-regression.sh
2026-09-03T21:49:58.8954277Z ==> step 5/11: Contamination check (no private-project/personal refs outside allowlist)
2026-09-03T21:49:59.1600377Z ==> step 6/11: Placeholder lint (core/frontend skills only)
2026-09-03T21:49:59.1763447Z ==> step 7/11: Validate settings.json and YAML catalogs
2026-09-03T21:49:59.2083421Z ==> step 8/11: Shellcheck hooks and scripts (excluding legacy/)
2026-09-03T21:50:03.2316000Z ==> step 9/11: Check tier boundaries (core/frontend must not reference domains)
2026-09-03T21:50:03.3461736Z ==> step 10/11: actionlint
2026-09-03T21:50:03.8136599Z ==> step 11/11: Hook and script executable bits
2026-09-03T21:50:03.8216380Z ==> activated workflow PASSED: 10 run step(s) executed, 1 runner-provided step(s) skipped by name
```

Execution window, first `run:` step to verdict: `2026-09-03T21:49:56.2454870Z` to `2026-09-03T21:50:03.8216380Z`.

## What this leg proves

The ten `run:` steps of the activated workflow execute verbatim and in order
on `ubuntu-latest`, twice, on two different commits about fifteen hours apart,
and the single `uses:` step is skipped BY NAME rather than silently. Because
this happens inside the `Smoke Install` workflow, it re-executes on every run
of that workflow — it is not a one-off.

What it does not prove: GitHub's own scheduler picking the workflow up from an
`on:` event in an adopter repository. That is the leg the disposable-repository
runs cover.

## Re-verification

Every quoted line is checked as a substring of the real log by the pack's
`verify-quotes.py`:

```
python3 verify-quotes.py smoke-install-runs.md \
        "LOG 33874751633" sources/job-run33874751633.log
python3 verify-quotes.py smoke-install-runs.md \
        "LOG 33809424817" sources/job-run33809424817.log
```
