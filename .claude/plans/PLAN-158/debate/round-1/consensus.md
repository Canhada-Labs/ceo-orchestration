---
plan: PLAN-158
round: 1
created_at: 2026-07-13
verdicts: [ADJUST, ADJUST, ADJUST]
round_verdict: PROCEED
consensus_adjustments: 7
---

# PLAN-158 round-1 consensus

Three critiques, all ADJUST; the security VETO was explicitly NOT
exercised. Scope discipline held under attack (minimum-plus judged
honest; OIDC is proof-coupled to a publish, not C6 creep; semver 1.1.0
verified). Verdict **PROCEED** after applying the adjustments below
(design-coherent; shipping gated by the verification cascade).

## Consensus findings (2+ critics)

1. **RC verdict file is GA-named — red tag guaranteed as written**
   (A, C). release.yml keys the verdict filename on `GITHUB_REF_NAME`:
   the RC needs `pair-rail-verdict-v1.1.0-rc.1.md`, the GA its own
   `pair-rail-verdict-v1.1.0.md`. Precedent: no RC verdict has ever
   existed in history; v1.0.1-rc.1's gate run failed on this.
2. **OIDC flip under-specified** (A, B, C — all three): (a) trusted
   publishing needs npm CLI ≥11.5.1 and Node 20 bundles npm 10.x — add
   an explicit npm upgrade step or the token exchange never happens
   (ENEEDAUTH at GA); (b) "drop NODE_AUTH_TOKEN" must become explicit
   token REVOCATION after OIDC is proven; (c) first real proof is
   structurally at GA (RC tags skip npm-publish), so the rollback diff
   must be pre-staged in the same sentinel + a failure playbook is
   mandatory: npm-publish.yml has NO workflow_dispatch and tag runs pin
   the workflow to the tag's tree → a failed OIDC-only GA publish means
   delete/re-tag.
3. **Wave 1 sentinel scope incomplete** (A, B): must carry the
   kernel-guarded `SPEC/v1/npm-shim.md` doc cascade (PLAN-152 §Deferred
   assigned it to the OIDC successor = this plan), with exact two-file
   scope discipline + per-file pair-rail verdicts.
4. **Wave 2 coupling to Wave 1 breaks under OQ1-fallback** (A, B): if
   OQ1 resolves to regenerate-token, Wave 1 may carry no ceremony; the
   rider needs its own conditional sentinel vehicle.

## Single-critic insights kept

- **Rider upgraded to spec-conformance (B):** the E1 gate's own
  docstring scopes it to live credentials — `ALL_PATTERNS` exceeded the
  spec. FP class is wider than CPF: `br_rg` blocks ANY bare 8-9 digit
  run (validator=None, no context gate); the hook blocked the critic's
  own grep carrying the S270 run id mid-round. SECRETS-only verified to
  still catch npm/ghp/PEM/aws forms. Residual loss (PII via arbitrary
  curl) named and accepted — egress-redact + adversary network rules
  are the designed layers.
- **Security guardrails for W2 (B — veto lines, recorded verbatim):**
  no catalog PII deletion; no weakening of the unconditional credential
  fail-closed path; no RC dist-tag npm publish to "prove OIDC early".
- **Manifests via `scripts/build-plugin.py` (C):** validate.yml runs
  its `--check`; manual bumps drift.
- **Stale claims riders (C):** README "151 skills" ×4 + plugin.json
  description say 151 vs disk 166 — W0 riders (dedup note: PLAN-157 W1
  carries an overlapping README rider; whichever lands first takes it).
- **Broken expiry citation (C):** GOVERNANCE-MAP.md:56 does not carry
  the flag; real flags at docs/PLAN-152-deferred-status.md:28/:74 +
  npm-publish.yml header. Fix citation in-plan + W0.
- **Freshness live-check (C):** all 6 advisory workflows green/fresh
  today; doc-freshness passes at-limit for 1.1.0 WITHOUT restamp (plan
  had "probably mandatory" — corrected to verify-first). New risk
  named: a Monday scheduled cron can interpose a red between RC and GA
  (the gate evaluates twice) — re-dispatch advisory if so.
- **Runner precondition (C raised; A live-verified green):** the `Ceo`
  outage was resolved in S270; kept as a standing precondition line.

## Plan adjustments applied (§ index)

1. §W3: RC verdict file renamed (tag-bound); §W4 GA verdict named.
2. §W1: npm ≥11.5.1 step; token revocation; pre-staged rollback diff;
   failure playbook (delete/re-tag path); SPEC/v1/npm-shim.md cascade
   in sentinel scope.
3. §W2: own conditional sentinel vehicle; security guardrails recorded.
4. §W0: build-plugin.py for manifests; README/plugin.json stale-claim
   riders (dedup note vs PLAN-157); expiry-citation fix; doc-freshness
   verify-first.
5. §W3: RC→GA cron-interposition note.
6. §Context: expiry flag citation corrected.
7. §Waves: standing precondition line (Validate green — satisfied S270).
