# PLAN-158 Wave 1 — OIDC GA-publish failure playbook

> **Why this exists (mandatory per the wave):** `npm-publish.yml` has **no
> `workflow_dispatch`**, and a tag run pins the workflow to the tag's tree.
> A failed OIDC-only GA publish therefore CANNOT be fixed by a re-run with
> different auth — the only path is: apply the pre-staged rollback diff on
> main, then **delete and re-tag** so the new run executes the rolled-back
> tree. There is also **no earlier proof point**: RC tags skip
> `npm-publish.yml` entirely (`!contains(github.ref, '-rc.')`), so the GA
> publish is the first end-to-end OIDC exercise by design (debate: no RC
> dist-tag publish to "prove OIDC early" — security guardrail, recorded).

## Failure signatures at the Publish step

| Signature | Meaning | Likely cause |
|---|---|---|
| `ENEEDAUTH` | npm found no usable credential | npm CLI < 11.5.1 (upgrade step failed/skipped) OR trusted publisher not registered on npmjs.com OR repo/workflow/environment mismatch in the registration |
| `E403` / `E404` on publish | Exchange happened but registry refused | Trusted-publisher registration fields don't match (`Canhada-Labs/ceo-orchestration` + `npm-publish.yml` + env `production-npm` — the workflow FILENAME must match, not the display name) |
| OIDC token fetch error | JWT never minted | `id-token: write` permission missing (should be impossible — it's in the workflow) or GitHub OIDC outage |

**First move on any failure:** check the registration on
npmjs.com → package `ceo-orchestration` → Settings → Trusted Publisher.
Field mismatch is the dominant failure class; fixing the registration and
re-running the SAME failed run (re-run executes the same tag tree — the
OIDC tree — which is fine when the registration was the problem) is the
cheapest recovery and needs **no rollback**.

## Recovery A — registration fix (preferred; no rollback)

1. Owner fixes the trusted-publisher fields on npmjs.com.
2. Re-run the failed `NPM Publish` run (GitHub UI → Re-run failed jobs).
3. The `already_published` guard keeps this idempotent.

## Recovery B — rollback to token auth (last resort)

Run from a clean main checkout, Owner terminal:

```bash
# 0. Regenerate a granular token FIRST (npmjs.com console — the old one
#    may already be revoked/expired): scope = ceo-orchestration,
#    publish permission. Store it as the repo secret NPM_TOKEN.

# 1. Apply the pre-staged rollback diff (restores env: NODE_AUTH_TOKEN
#    on the Publish step; nothing else changes):
git apply .claude/plans/PLAN-158/staged/wave1/rollback-oidc-to-token.patch

# 2. This edits a guarded workflow: land it under the SENT-OIDC sentinel's
#    pre-authorized rollback clause (the sentinel Scope carries
#    npm-publish.yml; the rollback diff is named IN the signed body), or
#    sign a fresh sentinel if the original has been superseded.
git add .github/workflows/npm-publish.yml
git commit -m "revert(PLAN-158): rollback npm-publish to token auth (OIDC GA failure — playbook Recovery B)"
git push origin main

# 3. Delete the GA tag + release, re-tag on the rolled-back tree:
gh release delete v1.1.0 --yes            # if the release was created
git tag -d v1.1.0
git push origin :refs/tags/v1.1.0
git tag -s v1.1.0 -m "v1.1.0"             # signed, on the rolled-back HEAD
git push origin v1.1.0

# 4. Approve production-npm when prompted; publish runs with token auth.

# 5. Re-date the expiry flags (the fallback obligation from OQ1):
#    docs/PLAN-152-deferred-status.md + npm-publish.yml header +
#    .github/workflows/GOVERNANCE-MAP.md:56 — new token expiry date.
```

> **Note:** deleting + re-creating a GA tag is itself a release-hygiene
> event — record it in the plan §Clarifications with the reason. The
> release.yml gates re-run on the new tag (pair-rail verdict is keyed on
> the tag NAME, so the existing `pair-rail-verdict-v1.1.0.md` stays valid
> if ≤24h old and the parent sha unchanged; otherwise regenerate).

## Success path (what "done" means)

1. `NPM Publish` green on the v1.1.0 GA tag; `npm view ceo-orchestration@1.1.0 version` prints `1.1.0`.
2. Provenance visible on the npm package page (Sigstore, now attesting via trusted publishing).
3. **Owner REVOKES the old granular NPM_TOKEN on npmjs.com** (not just stops using it) and deletes the `NPM_TOKEN` repo secret; revocation recorded in `docs/rotation-log.md`.
4. `npx ceo-orchestration@latest --help` exits 0 (Wave 4 smoke).
