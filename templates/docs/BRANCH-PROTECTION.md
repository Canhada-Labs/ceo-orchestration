# Branch protection + integrity policy

> This document replaces the PLAN-001 P2 proposal for cryptographic
> skill signing. The decision record is `.claude/adr/ADR-003-branch-
> protection-replaces-skill-signing.md`.

## Why branch protection instead of crypto

A SKILL.md hash file (`.claude/skills/INTEGRITY.sha256`) can be modified
by the same actor who modifies the SKILL itself. Crypto doesn't defend
against an authorized author making a weakening change — that's a
**review** problem, not a **crypto** problem.

Git commit hashes already provide cryptographic integrity. What's
missing is a **review gate** that forces human attention on every
change to protected paths. GitHub branch protection + CODEOWNERS is
that gate.

See `.claude/adr/ADR-003-branch-protection-replaces-skill-signing.md`
for the full rationale.

## When to enable

**AFTER** Sprint 2 ships and CI is verified green. Per PLAN-002 §11-bis
Q3, Sprint 2's 15–18 atomic commits push directly to `main` (same
pattern as Sprint 1). The solo Owner approving their own PRs on every
commit would add friction without buying security.

Sprint 3 onwards operates fully under branch protection.

## Setup: main branch rules

Go to **Settings → Branches → Add rule** for pattern `main`:

```
[x] Require a pull request before merging
    [x] Require approvals
        Number of approvals required: 1
    [x] Dismiss stale pull request approvals when new commits are pushed
    [x] Require review from Code Owners
[x] Require status checks to pass before merging
    [x] Require branches to be up to date before merging
    Select status checks:
      - validate / Governance, health, contamination, shellcheck
      (and "Skill benchmarks (advisory)" once the secret is configured)
[x] Require conversation resolution before merging
[x] Require signed commits                                 (optional)
[x] Require linear history                                 (optional)
[x] Do not allow bypassing the above settings
[x] Restrict who can push to matching branches             (solo repo: skip)
```

Leave the following **unchecked** unless you have a specific reason:

```
[ ] Allow force pushes
[ ] Allow deletions
```

## CODEOWNERS

The `.github/CODEOWNERS` file is already in the repo (shipped in
Sprint 2 C.3). It protects:

```
.claude/skills/**                       @<owner>
.claude/skills/**/benchmarks/**         @<owner>
.claude/hooks/**                        @<owner>
.claude/plans/PLAN-*.md                 @<owner>
.claude/adr/**                          @<owner>
PROTOCOL.md                             @<owner>
.claude/scripts/validate-governance.sh  @<owner>
.claude/scripts/check-contamination.sh  @<owner>
.github/workflows/validate.yml          @<owner>
.claude/settings.json                   @<owner>
templates/settings/**                   @<owner>
```

When you install this framework in a new project, **replace
`@<owner>` with the actual GitHub handle** of the human who will
review changes. The repo's live `.github/CODEOWNERS` already carries
the real handle; the `@<owner>` above is the template placeholder.

### Adding teammates

When you have a second reviewer:

1. Add their GitHub handle to the lines in `.github/CODEOWNERS` that
   they should also gate
2. In branch protection, bump "Number of approvals required" to 2 if
   you want two-reviewer review
3. Commit the CODEOWNERS change through a PR (which requires approval
   from the existing CODEOWNER — correct behavior, no paradox)

## What branch protection catches

- Unreviewed changes to skills (the weakening-without-review threat
  from ADR-003)
- Unreviewed changes to the governance layer (hooks, validate-governance,
  contamination check)
- Unreviewed changes to plans and ADRs
- Unreviewed changes to CI
- Force pushes to main that would rewrite history
- Direct pushes to main from someone who isn't configured

## What branch protection does NOT catch

- A Code Owner intentionally weakening a skill and approving their
  own PR. (Solution: second reviewer, or pre-commit CI that catches
  the specific weakening.)
- A compromised Code Owner account. (Solution: 2FA on the account,
  GitHub audit log review, key rotation.)
- Changes landed via direct git push from an admin. (Solution: do
  NOT check "Allow administrators to bypass" — leave the setting
  off.)

## API Key Hygiene (ANTHROPIC_API_KEY)

The benchmarks workflow (`.github/workflows/benchmarks.yml`) uses
`${{ secrets.ANTHROPIC_API_KEY }}` to call the Anthropic API during
skill benchmarks. Per PLAN-002 §11-bis Q6:

### Rotation policy

- **When:** rotate on suspicion of compromise (log leak, fork PR
  exfiltration attempt, Anthropic Console anomaly alert). **NOT** on
  a calendar rotation — calendar rotation of a low-privilege
  read-only API key adds human-error surface without proportional
  benefit.
- **Who:** Owner, manually.
- **Rotation procedure:**
  1. Generate a new key at Anthropic Console (console.anthropic.com)
  2. Update the `ANTHROPIC_API_KEY` secret at
     **GitHub Settings → Secrets and variables → Actions**
  3. Revoke the old key at the Anthropic Console
  4. Record the rotation (date + reason, NOT the key) at
     `docs/rotation-log.md`
  5. Monitor the next CI run to confirm the new key works

### Defense in depth

- `run-skill-benchmark.py` imports `_lib.redact.redact_secrets()` and
  runs every API response through it before writing
  `benchmark-results.json`. If a prompt-inject scenario asks the model
  to echo its own credentials, the echo is redacted before it lands
  in a CI artifact.
- The workflow refuses to run on fork PRs
  (`github.event.pull_request.head.repo.full_name == github.repository`
  guard). `pull_request_target` is EXPLICITLY FORBIDDEN — it would let
  a fork PR inject code that runs with the secret.
- The workflow uses a narrow `paths:` filter so docs/hooks/plans PRs
  never pay API cost (and never trigger the secret-gated job).

### Scope

The Anthropic API key used here should be a **project-scoped** key
with read-only usage (no admin, no write). A compromise bounds the
damage to "attacker burns some of your quota", mitigated by Anthropic
Console's own spend alerts.

## CI gates (Sprint 3 Item B)

The framework ships with two distinct floor gates on benchmark scores:

| Gate | Threshold | Source | Effect |
|------|-----------|--------|--------|
| **CRITICAL floor** | overall score < 0.4 | `scoring.health_thresholds.critical` in benchmark YAML | `run-skill-benchmark.py` exits 1. CI fails. Always enforced — no opt-out. |
| **Absolute floor** | overall score < 0.6 | `--floor 0.6` CLI flag (passed by `benchmarks.yml`) | Same exit code (rc=1). CI fails. Can be tuned per-environment. |

Both gates share exit code 1 by design (debate round 1 consensus
R-DEV1): having separate exit codes for "CRITICAL" vs "absolute floor"
fragments CI error handling without buying clarity. Distinguish via
the `$GITHUB_STEP_SUMMARY` table rendered by
`.github/scripts/summarize-benchmarks.py`.

### Escalation path

- CRITICAL floor breach → the benchmark scenario scoring is broken, or
  the skill has regressed catastrophically. Owner debugs the skill's
  prompt or the scenario expectations.
- Absolute floor breach (but above CRITICAL) → the skill has soft
  regressed. Look at the step summary to see which scenarios failed.
  For each failure, a **Reflexion lesson** is written to
  `$HOME/.claude/projects/<slug>/lessons/` (Sprint 3 Item A) — next
  spawn of a relevant agent will see that lesson under
  `## PAST LESSONS`.

### Sprint 4 planned

- **Regression gate** — any drop vs `main` last-known-good fails CI.
  Requires historical benchmark storage. Deferred per PLAN-002 §11-bis
  Q6.

## Quick checklist

- [ ] `.github/CODEOWNERS` is in the repo (shipped Sprint 2 C.3)
- [ ] Branch protection rule for `main` is configured per this doc
- [ ] "Allow administrators to bypass" is **unchecked**
- [ ] `ANTHROPIC_API_KEY` secret is set under **Settings → Secrets**
- [ ] `docs/rotation-log.md` exists (even if empty) so rotations have
      a place to land
- [ ] Absolute floor `0.6` is appropriate for the project (lower it if
      scenarios are noisy; higher only after stability established)
