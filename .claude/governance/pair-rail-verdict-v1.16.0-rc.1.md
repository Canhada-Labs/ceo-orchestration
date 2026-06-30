# Pair-Rail Verdict — v1.16.0-rc.1

**Verdict:** GO
**Generated:** 2026-05-11 by CEO Opus 4.7 (1M context)
**Plan:** PLAN-081 (Pair-Rail Multi-LLM Architecture — v1.16.0)
**Authoritative Codex MCP gate:** confirmation #37 (Phase 4-bis, 6 iters ACCEPT) + #38 (Phase 6-bis, 9 iters ACCEPT)

This verdict authorizes the v1.16.0-rc.1 release tag per ADR-103
(24h Codex re-pass mechanical window) + ADR-095 §gate-#6 (cross-LLM
review). The Codex MCP gate completed 2 confirmations across the two
ceremony bundles (Phase 4-bis locked corpus N=15 + Phase 6-bis pre-GA
bundle), with all P0/P1 findings closed inline.

## Verdict envelope (validator-parsed YAML frontmatter)

```yaml
verdict: GO
generated_at: 2026-05-11T17:15:00Z
ttl_hours: 24
commit_sha: d0af7e4ef8872ab0ea02807d16633bc96ad27fde
release_tag: v1.16.0-rc.1
inputs_hash: 589a057e7ac303dab09a944a9c8032aa101387246db3a33fd800ea8dc80f9dd1
inputs_hash_paths_manifest_sha: ad97e0116c80dae7fc980921e859a8d5b96f3659b842a14803aa6049b5708891
tool_versions:
  codex_cli: 0.130.0
  codex_cli_binary_sha256: baefc109b871e73a7bab298ee19b8bf73c8b647c4f8649a9794fc5db01db17b9
  claude_code: opus-4.7-1M
  python: 3.9.6
transcript_hash: pending-fill-at-tag-time
findings: []
gpg_signature: pending-fill-at-tag-time
```

## Notes on commit_sha self-reference

The `commit_sha` field above (`d0af7e4...`) refers to the Phase 6-bis
ceremony commit on top of which this verdict was generated. The
forthcoming verdict-commit (which adds this verdict file to the repo)
will have a NEW commit SHA `X`, and the rc.1 tag will point at SHA `X`.
release.yml step 15 passes `--commit-sha ${GITHUB_SHA}` (= SHA `X`)
which will NOT match `commit_sha: d0af7e4...` declared above.

**Resolution for rc.1 (transition mode):** Owner sets repository
variable `CEO_PAIR_RAIL_VERDICT_OPTIONAL=1` via:

```bash
gh variable set CEO_PAIR_RAIL_VERDICT_OPTIONAL --body 1
```

When set, release.yml step 15:
- `continue-on-error: true` (failures don't block release)
- The run script also passes `--commit-sha ""` (empty), causing the
  validator to skip the commit_sha equality check entirely

**Phase 7 follow-up:** the verdict-commit-SHA self-reference is
acknowledged as a transition-mode concern. Phase 7 plan will design a
post-commit verdict-amend or pre-commit-detached-verdict pattern that
removes the `CEO_PAIR_RAIL_VERDICT_OPTIONAL` escape hatch dependency.
For v1.16.0-rc.1 + v1.16.0 GA, transition mode is the operational
fallback per the documented Step A/B in
`.claude/plans/PLAN-081/architect/round-6-bis/approved.md`.

## Findings (P0/P1/P2/P3)

NONE. All findings from Codex MCP gates #37 + #38 closed inline before
verdict generation:

**Phase 4-bis (gate #37, 6 iters):**
- iter-1 P0: Unicode-digit regex bypass in adversarial PASS fixture (red-herring-comments-payment-flow.py — fixed via `[0-9]+` + `re.ASCII`)
- iter-1 P0: NaN/Inf fee bypass in adversarial PASS fixture (correct-but-risky-looking-refactor.py — fixed via `math.isfinite()` precheck)
- iter-1 P1: header `Scope:` drift adversarial fixture
- iter-2/3/4/5/6 atomicity findings: all closed (sentinel scope completeness, ceremony git add idempotency, etc.)

**Phase 6-bis (gate #38, 9 iters):**
- iter-1 P0: codex-cli-pin range did not include 0.130.0 → widened to `<0.131.0`
- iter-1 P0: VERSION 1.15.0 vs target v1.13.0 → bumped to v1.16.0-rc.1 (v1.13/v1.14/v1.15 already shipped)
- iter-1 P0: Cases C/E semantic drift between threat-model + verdict-matrix + SKILL → all 3 docs aligned with ADR-108 §Decision
- iter-1 P1: validator missing pin file → advisory skip (not INFRA error)
- iter-1 P1: doc cmd/path refs (case-summary, codex-writeguard-summary, etc.) → bulk corrected
- iter-1 P1: T-8 runtime claims (pair-rail-gate.sh + audit_emit) → marked Phase 7 follow-up with explicit ⏳ markers
- iter-2..9: progressive findings closed (CHANGELOG section, verdict-template version refs, sentinel scope governance/* additions, audit-query.py label semantics + Wilson bounds, ADR-108/111 --window-days, ceremony rerun idempotency, validator dict guards, verdict-commit timing, release.yml env-var sourcing)

## Inputs hash composition (forensic trail)

The `inputs_hash` field above is computed by hashing the canonical JSON
envelope of `{path: git-hash-object SHA}` for ALL paths declared in
`.claude/governance/pair-rail-inputs-hash-manifest.txt` (sorted).
Validator reproduces this calculation via
`.github/scripts/validate-pair-rail-verdict.py --recompute-inputs-hash`.

Current manifest (19 paths):

```
.claude/dispatcher/disable_predicate_eval.py
.claude/dispatcher/routing-matrix-loader.py
.claude/dispatcher/routing-matrix.yaml
.claude/governance/codex-cli-binary-sha256.txt
.claude/governance/codex-cli-pin.txt
.claude/hooks/_lib/adapters/_constants.py
.claude/hooks/_lib/adapters/__init__.py
.claude/hooks/_lib/adapters/codex.py
.claude/hooks/_lib/audit_emit.py
.claude/hooks/_lib/codex_egress_redact.py
.claude/hooks/check_canonical_edit.py
.claude/hooks/check_codex_filewrite.py
.claude/hooks/check_codex_response.py
.claude/hooks/check_pair_rail.py
.claude/plans/PLAN-081/corpus/locked/MANIFEST.md
.claude/policies/rubric-violation-catalogue.yaml
.claude/scripts/run-promotion-gate.py
.github/scripts/validate-pair-rail-verdict.py
SPEC/v1/audit-log.schema.md
```

## Authorization

Codex MCP cross-LLM gate confirmation #37 + #38 ACCEPT.
Phase 4-bis ceremony commit: `8490c85` (signed 00000000..., 2026-05-11)
Phase 6-bis ceremony commit: `d0af7e4` (signed 00000000..., 2026-05-11)
Owner GPG sign at tag time: pending.
