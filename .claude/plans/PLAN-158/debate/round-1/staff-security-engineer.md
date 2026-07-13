---
round: 1
archetype: Staff Security Engineer
skill: security-and-auth
agent_persona: (staff tier — VETO on auth/crypto surfaces)
generated_at: 2026-07-13T00:00:00Z
---

## Verdict

ADJUST

VETO position, stated explicitly: **not exercised**. Both waves are inside
my acceptable envelope *conditional on the must-fixes below*. I WOULD veto
two specific implementations: (1) any version of the Wave 2 rider that
deletes PII families from `secret_patterns.py` itself or weakens the
unconditional credential fail-closed path in `check_adversary.py`
(main():222-233 — never rate-limited, never CEO_ADVERSARY-downgraded);
(2) any "prove OIDC early" variant that publishes an RC to npm under a
dist-tag (re-opens ratified anti-goals #3/#16, npm-publish.yml:45-54).
Neither is what the plan proposes.

## Summary (≤ 3 bullets)

- The plan ships v1.1.0 as a ceremony vehicle plus exactly one
  deadline-bound deferral (OIDC before the ~2026-09-28 `NPM_TOKEN` expiry,
  GOVERNANCE-MAP.md:56) and one optional hook rider (drop PII families
  from the check_adversary pre-exec Bash scan). Scope discipline is
  correct; both riders are genuinely release-coupled.
- Strong: the rider is a spec-conformance fix, not a security downgrade —
  check_adversary's own documented contract (module docstring §3, "E1 §4:
  live-credential pattern") never scoped PII into the pre-exec gate;
  scanning `ALL_PATTERNS` exceeded it from day one. Fail-closed for
  credentials is structurally retained.
- Weak: the OIDC flip's mechanics are under-specified for a path whose
  FIRST live proof is the GA publish itself (RC tags skip npm-publish.yml
  entirely, line 54) — npm CLI version, `.npmrc` interaction, and the
  difference between *removing the token reference* and *revoking the
  credential* are all unaddressed.

## Risks

1. **R-SEC1 — HIGH — OIDC fails at GA: npm CLI too old.** The workflow
   pins Node 20 (npm-publish.yml:65-70), which bundles npm 10.x; npm
   Trusted Publishing requires npm CLI ≥ 11.5.1. Without an explicit npm
   upgrade step in the flipped workflow, the GA publish fails ENEEDAUTH at
   the worst possible moment (signed tag pushed, production-npm approved).
   Mitigation: add a pinned `npm install -g npm@<pinned ≥11.5.1>` step to
   the same sentinel diff; document the expected failure mode and the
   recovery (re-run after fix — the `already_published` guard at :224-241
   makes re-runs idempotent-safe).
2. **R-SEC2 — HIGH — "drop NODE_AUTH_TOKEN once proven" conflates
   reference-removal with credential revocation.** Deleting the env line
   (:247-248) does not kill the token; the granular token remains a live
   standing credential on npmjs until revoked. Until then BOTH auth paths
   are live and the flip's stated benefit is not realized. Mitigation:
   add an explicit post-proof Owner step — revoke the token in the npm
   console (do not ride it to expiry), optionally set the package to
   trusted-publisher-only publishing — plus the doc updates in R-SEC6.
3. **R-SEC3 — MEDIUM — ambiguous dual-live / neither-live windows.**
   (a) Neither-live: tag pushed before the Owner's console prereq →
   ENEEDAUTH; recoverable via re-run post-config (safe, idempotent) but
   must be written down. (b) Dual-live: if the `NODE_AUTH_TOKEN` env line
   is retained "behind a comment" *on the publish step* during GA, npm's
   token-vs-OIDC precedence is version-dependent — OIDC may never actually
   be exercised, so "proven" would be false. Mitigation: the sentinel diff
   removes the env line outright (proof must be unambiguous), and
   pre-stages the rollback diff (re-add the env line) inside the SAME
   signed sentinel scope so a mid-release recovery does not require a
   fresh ceremony. Also note setup-node with `registry-url` writes
   `_authToken=${NODE_AUTH_TOKEN}` into `.npmrc`; npm's behavior on an
   unset env reference in config is a known failure mode — resolve this
   interaction in the diff, don't discover it at GA.
4. **R-SEC4 — MEDIUM — fallback token handling protocol unspecified
   (OQ1).** "Regenerate the granular token" says nothing about handling.
   Mitigation: Owner-only, npm console → GitHub secret UI directly; the
   token value never transits chat, terminal, plan files, or logs (this
   session must never see it); prefer an environment-scoped secret bound
   to `production-npm` over a repo-wide secret.
5. **R-SEC5 — MEDIUM — rider scope regression risk.** A hand-copied
   family list in `_command_carries_secret` silently re-admits PII when
   the catalog grows. Mitigation: implement as
   `scan(command, patterns=_secret_patterns.SECRETS)` (SECRETS is
   token+credential by construction; verified: categories are exactly
   `{token, credential}`) plus a pinning test asserting no
   `category == "pii"` pattern is ever in the pre-exec set.
6. **R-SEC6 — LOW — auth-doc drift in guarded surfaces.** The
   npm-publish.yml header comment (:3-8) hardcodes "trusted publishing …
   NOT configured yet"; GOVERNANCE-MAP.md rows :21 and :56 describe token
   auth as current state. Post-flip these mislead the next security
   review. Mitigation: update all three in the Wave 1 scope (the workflow
   header is inside the guarded file — same sentinel diff or it becomes
   permanent drift).
7. **R-SEC7 — LOW — bundled sentinel dilutes review focus.** One
   ceremony covering two unrelated guarded surfaces (npm-publish.yml +
   check_adversary.py) is acceptable ONLY with exact scope enumeration
   (touched − scope = ∅) and a pair-rail verdict that addresses each file
   separately, not one blended approval.

## Must-fix (blocking)

1. Add the pinned npm-CLI upgrade step (≥ 11.5.1) to the OIDC flip; Node
   20's bundled npm 10.x cannot do trusted publishing (R-SEC1).
2. Resolve the `.npmrc` / `NODE_AUTH_TOKEN` interaction explicitly in the
   flipped workflow: publish step runs with NO token env (unambiguous
   proof), rollback diff pre-staged inside the same signed sentinel scope
   (R-SEC3).
3. Add explicit post-proof token REVOCATION (Owner, npm console) as a
   Wave 4 checklist item — not merely env-line removal, and not
   ride-to-expiry (R-SEC2).
4. Specify the OQ1 fallback token-handling protocol: Owner-only,
   console → GitHub secret directly, never transits the session/plan/logs;
   environment-scoped secret preferred (R-SEC4).
5. Rider implementation and pins: use `patterns=_secret_patterns.SECRETS`
   (not a hand list); regression tests = (a) checksum-valid CPF-shaped run
   id ALLOWED, (b) bare 8-digit compact-date string ALLOWED (see Unseen
   #2 — the class is wider than CPF), (c) `npm_`/`ghp_`/PEM/
   `aws_secret_access_key` context-form still DENIED (token, token,
   credential, credential), (d) a structural pin that no pii-category
   family is in the pre-exec pattern set (R-SEC5).
6. Update the three stale auth descriptions (npm-publish.yml:3-8 header,
   GOVERNANCE-MAP.md:21,:56) in Wave 1 scope; sentinel scope enumerates
   BOTH guarded files exactly; pair-rail verdict per file (R-SEC6/7).

## Nice-to-have (advisory)

1. While inside check_adversary.py: fix the misleading deny-reason text
   (:246-249). "Set CEO_ADVERSARY=0 disables enforcement" is FALSE for the
   secret path — advisory mode still emits a blocking "ask", the gate is
   stateless so "re-issue deliberately" (:255-258) can never succeed
   either. No-env-escape is by design (docstring §3-4); the reason text
   should say so honestly instead of offering two escapes that don't work.
2. Preserve telemetry: an optional advisory-only audit emit for PII-family
   hits (no block) would keep a tuning signal for the egress rail; costs a
   second scan on hit-paths only. Defer if latency budget objects.
3. The `br_rg` catalog entry's comment claims "Context-gated on
   rg/identidade keyword" (secret_patterns.py:615-618) but the regex
   (:620) carries NO context gate and `validator=None`. Fixing the catalog
   itself is out of this plan's scope (egress-rail behavior change, own
   soak) — file it as a follow-up; the comment/behavior mismatch should
   not survive another catalog version bump.
4. Extend `test_release_workflow_asserts.py` (which already pins RC
   exclusion, `npm publish --provenance`, and `environment:
   production-npm`) with an OIDC-posture pin: publish step carries no
   `NODE_AUTH_TOKEN` reference post-flip.
5. If the OQ1 fallback path is taken, migrate `NPM_TOKEN` from repo-wide
   to a `production-npm` environment secret as part of the regeneration.

## Unseen by the original plan

1. **Live reproduction during this debate round.** My own
   evidence-gathering grep containing the literal S270 run id was BLOCKED
   by check_adversary mid-round ("matched an ASK rule…"). The incident is
   not historical color — it actively degrades governance work, and Waves
   3-4 of THIS plan run `gh run list` checks whose outputs/commands carry
   11-digit run ids. The release ceremony itself collides with the bug the
   rider fixes; that is an argument the plan does not make but should.
2. **The FP class is materially wider than "checksum collisions".**
   Verified by direct execution against the live catalog: `br_rg`
   (validator=None, no context gate) matches ANY bare 8-9 digit run — a
   compact date (`20260713`-shaped) and a bare 9-digit sequence both
   produce a pii finding → unconditional pre-exec block. The S270 run id
   fires TWO families (br_cpf + br_pis_pasep). The rider as scoped
   (SECRETS-only pre-exec) fixes the entire class — verified: SECRETS-only
   scan is clean on both FP shapes and still catches a real-shaped
   `npm_…` token. The consensus should record this so the fix is judged at
   its true severity, and so test (b) in Must-fix 5 exists.
3. **Documented-contract alignment.** check_adversary.py's docstring
   (§3: "if a live-credential pattern … matches") and the E1 §4 comment
   (:139-143: "A live credential in the command…") both scope the
   fail-closed gate to credentials. `_command_carries_secret` scanning the
   full catalog (:123, `scan(command)` → ALL_PATTERNS = SECRETS + PII)
   exceeded the documented contract from the start. Record the rider as a
   spec-conformance fix in the commit/ADR trail — it pre-empts future
   "why was PII protection removed" archaeology.
4. **Residual coverage loss, honestly stated.** Post-rider, PII exfil via
   arbitrary local network tools (`curl -d cpf=…`) is no longer blocked
   pre-exec. Egress-redact (`codex_egress_redact.py`, ALL_PATTERNS) covers
   only the model-egress lanes, not arbitrary curl; `adversary.md` network
   deny rules remain the designed control for destination policy. This
   residual was near-theater against a deliberate adversary (base64/hex
   trivially evades a plaintext checksum match; the gate only ever caught
   checksum-valid plaintext) while imposing real operator cost — but the
   consensus must NAME the loss rather than claim zero. I accept it.
5. **First-proof-at-GA is structural, not incidental.** Because RC tags
   are hard-excluded from npm-publish.yml (:54, load-bearing, test-pinned),
   no rehearsal short of GA exercises OIDC end-to-end. The plan's Wave 1
   "Check: none … mechanical proof lands in Wave 3 publish" actually lands
   in Wave 4 (Wave 3 is the RC, which never touches npm). Correct the
   wave annotation and treat Must-fix 1-3 as the compensating controls.

## What I would NOT change

- The RC-tag hard exclusion and the `production-npm` manual-approval
  environment gate (npm-publish.yml:45-57). Do not "prove OIDC early" via
  an RC dist-tag publish — that trade was ratified closed (PLAN-153
  Wave B item 5f) and stays closed.
- The unconditional credential fail-closed structure in check_adversary
  (secret path never rate-limited, never CEO_ADVERSARY-downgraded,
  main():222-233). The rider changes the PATTERN SET only; the structure
  is correct and must survive verbatim.
- Keeping all 11 PII families in the catalog and on the egress rail
  (ALL_PATTERNS for codex_egress_redact). Consumer-side pattern selection
  is the right fix; catalog deletion would be the wrong one.
- Binding the trusted publisher to workflow `npm-publish.yml` +
  environment `production-npm`. Correct tightening; keep it.
- Scope discipline: excluding the other six PLAN-152 deferrals. The C6
  lesson is correctly applied — and the Wave 2 rider is NOT the C6
  anti-pattern: check_adversary.py is canonical but not in the
  self-modification kernel class (settings.json / check_bash_safety /
  _python-hook), the fix is release-coupled (Unseen #1; v1.1.0 ships this
  hook to every adopter — shipping the known-FP version and fixing it in
  v1.1.1 is worse), and it carries its own tests. Bundling is acceptable
  under Must-fix 6.
- OQ3 full 24h RC-hold: agree, no waiver.
- `--provenance` retained explicitly on the publish line (`id-token:
  write` already present serves both OIDC auth and Sigstore).
