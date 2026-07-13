# PLAN-158 W1+W2 — pair-rail per-file verdicts (staged diffs, pre-ceremony)

- **Reviewer:** codex-cli 0.144.1 (`codex exec --sandbox read-only`, diff pipe
  — `codex_invoke.py` route unavailable per substrate drift note)
- **Date:** 2026-07-13 (S271)
- **Input:** unified diff bundle of the 6 staged files (wave1: npm-publish.yml,
  GOVERNANCE-MAP.md, install-npm.sh, SPEC/v1/npm-shim.md via patcher; wave2:
  check_adversary.py, test_adversary_pii_collision.py)
- **Advisory only** — decision is the CEO's; Owner signs the sentinels
  ([[feedback-pair-rail-clean-round-not-proof]]: stopping criterion = every
  file APPROVE, single-issue REJECTs folded and re-reviewed once).

## Round 1 (verbatim)

```text
FILE: `.github/workflows/npm-publish.yml` — APPROVE — RC exclusion, `production-npm` gate, and `--provenance` are preserved; token auth is removed for OIDC.
FILE: `.github/workflows/GOVERNANCE-MAP.md` — REJECT — `.github/workflows/GOVERNANCE-MAP.md:21` still claims "opt-in via workflow_dispatch", but `npm-publish.yml` is tag-push only and the diff explicitly says there is no `workflow_dispatch`.
FILE: `scripts/install-npm.sh` — APPROVE — doc-only update matches OIDC publishing while preserving the no-publish local script boundary.
FILE: `SPEC/v1/npm-shim.md` — APPROVE — publishing docs retain RC exclusion, `production-npm`, and provenance while updating auth mechanism.
FILE: `.claude/hooks/check_adversary.py` — APPROVE — pre-exec scan is scoped to `SECRETS` with current-catalog credential forms still matched.
FILE: `.claude/hooks/tests/test_adversary_pii_collision.py` — APPROVE — regression tests cover PII collision allow, credential blocking, catalog integrity, and fallback behavior.

OVERALL: REJECT
```

**Fold:** the REJECT was a real pre-existing false claim (the kill-switch
column of the npm-publish row asserted an `workflow_dispatch` opt-in that
does not exist — same false-claim class PLAN-152 tarball-01 fixed in the
header). Staged GOVERNANCE-MAP.md corrected to "none; GA-tag push only —
no `workflow_dispatch` by design (PLAN-013 anti-goal #16)".

## Round 2 — corrected file only (verbatim)

```text
FILE: .github/workflows/GOVERNANCE-MAP.md — APPROVE — r2 removes the false workflow_dispatch claim; the OIDC/no-long-lived-secret wording matches the staged npm-publish.yml and PLAN-158 playbook.
OVERALL: APPROVE
```

## Net result

| File | Verdict |
|---|---|
| `.github/workflows/npm-publish.yml` | APPROVE (r1) |
| `.github/workflows/GOVERNANCE-MAP.md` | APPROVE (r2, after fold) |
| `scripts/install-npm.sh` | APPROVE (r1) |
| `SPEC/v1/npm-shim.md` | APPROVE (r1) |
| `.claude/hooks/check_adversary.py` | APPROVE (r1) |
| `.claude/hooks/tests/test_adversary_pii_collision.py` | APPROVE (r1) |

6/6 APPROVE. Ceremony may proceed (`land-plan158.sh`). Note: these are the
SENTINEL-scope advisory verdicts; the RC/GA tag verdicts
(`pair-rail-verdict-v1.1.0-rc.1.md` / `-v1.1.0.md`) are separate Wave 3/4
artifacts with their own ≤24h freshness gate.
