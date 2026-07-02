---
plan: PLAN-152
round: 1
created_at: 2026-07-01
author: CEO
---

# PLAN-152 round-1 proposal — v1.0.1 Hardening Sweep

> Full plan: `.claude/plans/PLAN-152-v1-0-1-hardening-sweep.md` (REVISED S255 —
> read that file, not this distillation, for item-level detail).

## Thesis

Ship `ceo-orchestration@1.0.1` resolving **all 41 confirmed findings** of the
S254 audit fan-out (run `wf_071ef6c5`: 32 fix / 6 accept / 3 defer) **plus** the
pre-existing v1.0.1 backlog, in **one next-terminal Fable run**, wave-ordered by
blast radius. Zero silently-dropped findings: every `fix` is a wave item, every
`accept`/`defer` has an on-disk pointer.

## Scope (7 waves)

| Wave | Content | Ceremony? |
|------|---------|-----------|
| 0 | Owner prerequisites: 3 pending GPG sentinels + fresh PLAN-152 sentinel | Owner-only |
| A | P0 security fail-opens SHIPPED-BROKEN in v1.0.0: pair-rail registration dead (settings.json:201 relative-path arg → shim fail-open), bash-safety `shlex.ValueError` → fail-open, `_python-hook.sh` cache TOCTOU/symlink, parity-test regex vacuous, template missing pair-rail | KERNEL → ceremony |
| B | CI-dark tests: root `tests/` never collected (112 tests incl. 3 security), 8 roots ~1377 tests absent from CI, env-hygiene 183 NEW violations, coverage-floor doc drift (67 vs 78) | no |
| C | Hot-path economics (double HMAC emit, uncapped 2nd read, project-wide P4 window) + workflow null-guards (crashed run `wf_071ef6c5`) + pii snippet contract | hooks → ceremony |
| D | npm tarball hygiene: `files:` whitelist voids `.npmignore` → tests/fixtures/eval/red-team/PLAN-* ship in the tarball; packlist CI gate; OIDC Trusted Publishing (NPM_TOKEN expires ~2026-09-28) | KERNEL → ceremony |
| E | Docs-drift + dead-code minors (all verified live S255); orphan PLAN-128; NOTE: issue-template item was REFUTED (already shipped v1.0.0) | no |
| F | Model modernization: fast-mode deprecation ledger entries; Sonnet 5 `MODEL_ID` KERNEL edit + ADR; substrate-refresh ALREADY DONE (`37867c2`) | KERNEL → ceremony |
| G | Closeout: check-claude-md-claims (tolerance=0), VERSION 1.0.1, CHANGELOG, full CI gate set local | no |

## Key decisions to attack

1. **Wave order** = blast radius (security → tests → economics → packaging →
   docs → models → closeout). Is anything ordered wrong (e.g. should B run
   before A to widen the safety net first)?
2. **Single next-terminal run** (budget 400-700k tokens, 1 session,
   context_risk: high). Is the scope per session realistic? Where would YOU
   cut if the session degrades?
3. **Ceremony boundary**: kernel/canonical edits (settings.json, hooks/**,
   npm-publish.yml, install*.sh, MODEL_ID enum) via GPG sentinel + Codex
   pair-rail; everything else lands direct. Any path misclassified?
4. **The pair-rail gate itself is broken until Wave A lands** — interim
   mitigation is manual `codex exec review --uncommitted`. Is that
   sequencing sound (fix-the-gate-first), or does it need a harder guard?
5. **Fail-closed conversions** (bash-safety on parse error). Any
   fail-open→fail-closed flip that could brick a legitimate session
   (CLAUDE.md §4 fail-open-on-infrastructure doctrine tension)?

## Verification status (S255 — this session)

62 factual claims of the draft were re-verified read-only against the repo
(workflow `wf_9a1dd57e`, 7 verifiers): 51 CONFIRMED, 11 divergences ALREADY
FOLDED into the revised plan (issue-template refuted; substrate-refresh already
committed as `37867c2`; env-hygiene 211→183; 3 non-discriminating Check lines
rewritten; count/path fixes). The plan you are reading post-dates these fixes.

## Open questions — answer all 3 with a recommendation

- **OQ1**: Sonnet-5 — reconcile the stale `OPUS47 = "claude-opus-4-8"` label +
  add the enum member only, or ALSO flip M-tier routing to Sonnet 5 in v1.0.1?
  CEO leaning: label+member+ADR now; routing flip deferred (cost decision with
  its own soak).
- **OQ2**: ceremony batching — ONE PLAN-152 sentinel with enumerated Scope
  covering all kernel paths in A/C/D/F, or per-wave sentinels? CEO leaning:
  one sentinel (Owner wants a single run; touched−scope=∅ check before commit
  mitigates drift).
- **OQ3**: single v1.0.1, or split A+B as v1.0.1 hotfix + C-F as v1.0.2?
  CEO leaning: single v1.0.1 (tiny adopter base, non-remote-exploitable P0s,
  release ceremony cost ×2 not justified); split stays as mid-run fallback.

## What a critique must do

From YOUR skill's forced perspective: list risks the CEO did not see, where
this plan can fail, and what is missing. Evidence-based — verify any factual
claim you dispute with grep/read before asserting. 2+ critics converging on a
risk forces a plan adjustment (PROTOCOL §Debate rule 2).
