---
plan: PLAN-158
round: 1
created_at: 2026-07-13
---

# PLAN-158 round-1 proposal — Release v1.1.0

Full plan: `.claude/plans/PLAN-158-release-v1-1-0.md`

## Thesis

npm `latest` is v1.0.1 (2026-07-06); main has 55 shipped commits since
(PLAN-153 ecc uplift, PLAN-154 learning loop, PLAN-155 Codex harness,
PLAN-156 Grok harness + `/council`). New harnesses + a new command are
features → **semver minor → v1.1.0**. The release is a *vehicle*: no new
feature code, only the ceremony + exactly one deadline-bound deferral.

**Scope: minimum-plus.**
- The ceremony: version triple+marketplace bump, CHANGELOG §[1.1.0],
  doc-freshness stamp refresh, per-tag Codex pair-rail verdicts, signed
  RC → 24h RC-hold (ADR-103) → signed GA → `production-npm` approval →
  npm publish with provenance → npx smoke.
- **backlog-oidc** (PLAN-152 §Deferred): migrate npm auth to Trusted
  Publishing (OIDC). Deadline-bound: the granular `NPM_TOKEN` expires
  ~2026-09-28 and v1.1.0 is plausibly the last release before that.
  Owner prereq: configure the trusted publisher on the npmjs console.
  Fallback (OQ1): regenerate token + re-date the expiry flag.
- **Optional rider (OQ2, debate decides):** `check_adversary.py`
  secret-in-command scan currently swallows numeric BR-PII checksum
  collisions (S270 live incident: benign GitHub run id `29248385761` is
  a checksum-valid CPF → every command containing it is blocked, no env
  escape by design). Fix = restrict the pre-exec Bash scan to
  token/credential families; PII redaction stays on the egress rail.
  Canonical hook → rides the Wave 1 sentinel ceremony. Fail-closed for
  real credentials is RETAINED.

Explicitly NOT in scope: the other six open PLAN-152 deferrals
(governance-04/07 kernel work, `_lib/tests` env-hygiene burndown,
nested-subagent red-team corpus, canonical-models sonnet5 refresh,
PLAN-128 wave1 tooling) — they have their own successor tracks; pulling
kernel ceremonies into a release was the anti-pattern debate C6 rejected
for v1.0.1.

Verified premises (S270 dossier): the 2 latent release.yml bugs
(RC-version-mismatch, hardcoded release notes) are ALREADY FIXED
(PLAN-153 B5, `2094175`); the advisory-workflow freshness gate needs all
6 advisory workflows non-red AND ≤14d fresh BEFORE cutting the tag (the
v1.0.1 lesson: otel/adapter needed manual dispatch).

## Wave structure

- W0 debate + version prep (bump, CHANGELOG, stamps)
- W1 backlog-oidc (Owner console prereq; guarded npm-publish.yml edit →
  sentinel; NPM_TOKEN fallback documented)
- W2 optional check_adversary rider (OQ2-gated; canonical → same
  ceremony as W1)
- W3 RC ceremony (verdict, freshness gate, signed rc.1, 24h hold)
- W4 GA + publish (fresh verdict, signed tag, production-npm approval,
  npx smoke) + closeout

## Open questions for this round

- OQ1: OIDC now vs regenerate-token-and-defer. CEO default: OIDC now.
- OQ2: include the check_adversary PII-collision rider? CEO default:
  yes (small, ceremony already paid, fail-closed retained). Security
  VETO applies.
- OQ3: full 24h RC-hold or waiver? CEO default: full hold.

## What the critics should pressure-test

1. Is the OIDC flip inside a release the same anti-pattern C6 rejected
   (auth-mode migration holding the release hostage)? The counter: it
   is deadline-bound to THIS window. Verify npm-publish.yml mechanics.
2. Does the check_adversary rider weaken any real security posture
   (credential families still fail-closed)? Is a release plan the right
   ceremony vehicle for a kernel-adjacent hook edit?
3. Version/manifests/CHANGELOG/stamps: is the Wave 0 list complete
   against release.yml's actual gates (doc-freshness N=1 minor
   tolerance on a 1.0→1.1 bump)?
4. RC/GA verdict mechanics: per-tag verdicts, pin `<0.145.0`, binary
   sha256 — anything stale in the plan vs release.yml as landed?
5. Anything in the delta (PLAN-153..156) that makes the npm package
   itself wrong (packlist gate, staging rsync, plugin manifests)?
