# Pair-rail V2 verdict — PLAN-159 Wave 1 (SENT-PERFGATE bundle)

VERDICT: GO

- **Date:** 2026-07-15 (S274)
- **Reviewer:** Codex CLI (`codex exec`, cross-vendor truth gate per
  PROTOCOL.md §Verification cascade V2)
- **Rounds:** 5 (GO on round 5; rounds 1–4 returned NO-GO with findings,
  all accepted, fixed and re-verified — transcripts in the session
  scratchpad, summaries below)

## Anchor — the bytes this verdict approves

`staged/` is gitignored by design; this verdict anchors to the TRACKED
manifest `.claude/plans/PLAN-159/staged-wave1.sha256`, whose hashes the
land script re-verifies FAIL-CLOSED at preflight:

```
78c845f031bddddd1de44ed8261eb9cacb3369cf7ef3456c227cf7148508b283  .claude/plans/PLAN-159/staged/wave1/validate-yml.patch
af6ba24648ca0d30421ae31cfce285be547169ec50de5033870dd3938ca58181  .claude/plans/PLAN-159/staged/wave1/root/.claude/scripts/profile-opus-4-7.py
b69c7c4b6d568169d628436ed14265188ff56122043bf016d52ac4522a282ce4  .claude/plans/PLAN-159/staged/wave1/root/.claude/scripts/tests/test_profile_opus47_latency_gate.py
b75d423a472990e65cb398624c71a295727212fa4e627e4e63977aa158ef34ee  .claude/plans/PLAN-159/staged/wave1/root/.claude/adr/ADR-163-hook-latency-gate-percentile-stability.md
```

Any post-verdict mutation of a staged input trips the manifest gate; an
intentional change requires re-running the pair-rail AND regenerating
the manifest.

## Findings arc (10 real findings across rounds 1–4, all fixed)

| Round | Verdict | Findings → fixes |
|---|---|---|
| 1 | NO-GO | (1) `grep 'GO\|ACCEPT'` matched the "GO" inside "NO-GO" — V2 bypass → anchored NEGATIVE-first verdict parse; (2) wave2 proof could false-green on rc=127 (`timeout` absent on Darwin) → shim + anti-vacuity measured-breach gate + exact `(rc1=1 rc2=1)` marker; (3) ADR truth-table claim was a session anecdote + `publish()` silent on missing report → repeatable `wave1-wrapper-matrix-proof.sh` (4 cases, land gate) + explicit no-report note + honest ADR wording |
| 2 | NO-GO | Stale prose truth-drift (plan "ADR-071 wants N≥200", plan "ALWAYS published", land header "5→10min") → all three corrected |
| 3 | NO-GO | (1) matrix proof ran post-apply and re-applied the patch — spurious ceremony abort → helper reads `HEAD`, gate moved to preflight; (2) patch comment still said "ALWAYS" → regenerated |
| 4 | NO-GO | (1) staged inputs gitignored → untracked + mutable after review → tracked sha256 manifest + fail-closed preflight check (this file's anchor); (2) "percentiles always" survived in sentinel body / commit message / measurements §7 → corrected everywhere |
| 5 | **GO** | none — mechanical verification: manifest 4/4 (not gitignored), `git apply --check` clean, wrapper matrix 4/4, post-apply unit tests 9/9, `bash -n` + shellcheck `-S warning` clean; remaining "always" is the (true) timeout-sizing claim |

## Scope of the GO

The SENT-PERFGATE ceremony bundle exactly as pinned above, plus the
ceremony tooling reviewed with it (`land-plan159.sh`,
`wave1-wrapper-matrix-proof.sh`, `wave2-regression-proof.sh`) and the
two scripted edits (test_hook_latency.py citation ADR-071→ADR-163;
CLAUDE.md ADR count derived from disk). This verdict is V2 evidence
only — shipping is authorized by V3 (Owner GPG sentinel ceremony), per
PROTOCOL.md §Verification cascade.
