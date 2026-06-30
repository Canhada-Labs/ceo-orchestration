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

## When to enable — tier constraint + chosen path (ADR-003-AMEND-1, S160)

> **Correction (PLAN-112-FOLLOWUP-branch-protection-feasible, 2026-05-24):**
> the earlier "enable after Sprint 2/3" timeline was **infeasible** and has
> been retracted. See `ADR-003-AMEND-1`.

Server-side branch protection on a **private** GitHub repo is a **GitHub
Pro-only** feature. Verified at HEAD: `gh api .../branches/main/protection`
returns **HTTP 403 — "Upgrade to GitHub Pro or make this repository public
to enable this feature."** The promised "Owner flips after Sprint 3" never
happened because it **could not** happen on the current (free-tier, private)
repo tier.

The framework adopts **Path C** (per the S160 Wave A debate, 0 VETO):

1. **Now — compensating controls are the interim primary mechanism.** The
   shipped hook + Owner-GPG-sentinel + Codex-pair-rail stack is the de-facto
   protection for governance paths (enumerated in the register below).
2. **Milestone-gated upgrade to real server-side protection (the setup
   below):** triggered by ANY of — **repo goes public**, OR **team size > 1**,
   OR **first production adopter**. Not a calendar date (ADR-095). At the
   trigger, the Owner makes the cost/visibility decision (GitHub Pro **or**
   public repo) and configures the rules in §"Setup: main branch rules".
3. **`team size > 1` also re-activates key custody** (GPG rotation +
   per-signer revocation) as a dedicated followup. Single Owner-key custody
   is an acceptable residual **only** at team-size-1.

The cost/visibility change (Path A) is an **explicit Owner decision**, not
auto-actioned by the framework.

### Compensating-controls residual-risk register (interim, until Path A)

These controls are an **authorization / authoring-time** layer — they
authenticate the author of each governance edit and block the agent rail.
They are **NOT** a merge / server-side ref control.

> **These hooks gate the agent tool-call rail only; they do NOT constrain a
> human operator (or a compromised local credential) running git directly.
> A client-side authoring-time control is not equivalent to a server-side
> ref guard.**

| Compensating control | Blocks (blast-radius coverage) |
|---|---|
| `check_canonical_edit.py` | Edit/Write/MultiEdit + write-shaped `mcp__*` on governance paths without an Owner-signed GPG sentinel (`Approved-By:` + `Scope:`) |
| `check_arbitration_kernel.py` | HARD-DENY on the hooks/_lib/policy that enforce governance — no sentinel escape, only `CEO_KERNEL_OVERRIDE`+`_ACK` (audited) |
| `check_bash_safety.py` | `rm -rf`, `git reset --hard`, `git push --force/-f` (allows `--force-with-lease`) |
| `check_plan_edit.py` | illegal plan status transitions |
| `check_agent_spawn.py` | spawns without `## SKILL CONTENT` |
| `check_pair_rail.py` | Codex read-only review on L3+ canonical edits; BLOCK on write-shaped Codex response |
| `check_skill_patch_sentinel.py` | SKILL.md edits without a GPG-signed `SP-NNN` proposal |
| GPG sentinel chain (`_lib/gpg_verify` + signer registry, ADR-121) | every canonical edit fails-CLOSED on missing/bad signature |

**Explicit residual gaps (until Path A enables server-side protection):**

- **Un-gated direct-push path:** a human operator (or compromised local
  credential) running `git push` directly is NOT gated — see the verbatim
  boundary statement above.
- **`--force-with-lease` allowed on the agent rail** (only `--force`/`-f`
  blocked) → lease-checked history rewrite is still possible.
- **Single Owner GPG key** — no rotation/revocation story; re-activated as a
  followup on `team > 1`.
- **No server-side pre-merge review.**
- **`.github/CODEOWNERS` is aspirational / inert** on a free-tier private
  repo — it is only enforced once server-side branch protection is active
  (Path A). The catch-all below documents intent, not a live gate today.

The setup instructions in the following sections describe **Path A** — apply
them when the milestone trigger fires.

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

## Commit-signing policy (ADR-150, S227)

Per-commit GPG signatures are **OPTIONAL** in this repo. The load-bearing
provenance controls are (1) the Owner-GPG **sentinel chain on canonical edits**
(`check_canonical_edit` + `_lib/gpg_verify`, ADR-121/ADR-003 Path C) and
(2) the HMAC audit chain. The tiered requirement:

- **MUST be signed (Owner GPG):** ceremony commits that apply canonical-guarded
  paths, release/tag commits, ADR promotions.
- **MAY be unsigned:** docs / plans / closeout commits, non-canonical code and
  tests, PR work commits.
- **Ratification tags:** at milestones the Owner pushes a signed
  `ratify-provenance-sNNN` tag — one signature Merkle-attests the entire
  history up to that commit. Latest: `ratify-provenance-s227`.

Audits evaluate signing discipline against THIS policy (see ADR-150), not
against a per-commit ideal.

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

### WIF — keyless CI via GitHub OIDC (first-party; PLAN-135 W5 O9)

Anthropic ships first-party **Workload Identity Federation (WIF)**:
the CI run exchanges its **GitHub Actions OIDC token** directly for a
short-lived, scoped Anthropic access token — **no standing
`ANTHROPIC_API_KEY` repo secret at all**. This retires the long-lived
CI credential class that already leaked once (S206,
`docs/rotation-log.md` 2026-06-03 row) and supersedes the self-run
broker below for the Anthropic key specifically (the broker recipe
remains useful for providers without first-party federation, e.g. the
Codex `OPENAI_API_KEY`).

How it fits together (Console → **Settings → Workload identity →
Connect workload**, GitHub Actions tile):

1. **Federation issuer** (`fdis_…`) — registers
   `https://token.actions.githubusercontent.com` (JWKS via OIDC
   discovery) as a trusted signer.
2. **Service account** (`svac_…`) — the non-human principal the CI
   run acts as; member of the workspace whose rate limits and usage
   attribution apply.
3. **Federation rule** (`fdrl_…`) — "JWTs from issuer X whose claims
   look like Y may act as service account Z with scope S". **Pin the
   `sub` match to this repo + protected ref** (e.g.
   `repo:@OWNER/<repo>:ref:refs/heads/main`) so a forked or
   re-targeted workflow cannot mint tokens. Default scope
   `workspace:developer` (= what a workspace API key could do);
   `token_lifetime_seconds` 60–86400 (default 3600; the Console wizard
   prefills 600 — keep it short for CI).

At run time the job sets `permissions: id-token: write`, obtains the
Actions OIDC JWT, and the SDK (or a raw
`POST /v1/oauth/token`, RFC 7523 `jwt-bearer` grant, with
`assertion` + `federation_rule_id` + `organization_id` +
`service_account_id` [+ `workspace_id`]) returns a short-lived
`sk-ant-oat01-…` token. Minted-token lifetime is the lesser of the
rule's lifetime and 2× the remaining JWT lifetime (floor 60s); the
SDKs cache + refresh automatically. Zero-argument clients pick the
exchange up from `ANTHROPIC_FEDERATION_RULE_ID`,
`ANTHROPIC_ORGANIZATION_ID`, `ANTHROPIC_SERVICE_ACCOUNT_ID`,
`ANTHROPIC_WORKSPACE_ID`, `ANTHROPIC_IDENTITY_TOKEN_FILE`.

**Precedence trap:** `ANTHROPIC_API_KEY` sits *above* the federation
tiers in every SDK's credential chain — a leftover repo secret
silently shadows WIF. Migration (no downtime):

1. Configure issuer + service account + rule in parallel (key stays).
2. Smoke-test which credential wins (`ant auth status` from the job).
3. Delete the `ANTHROPIC_API_KEY` repo secret (Settings → Secrets).
4. Revoke the key in the Console; append a `docs/rotation-log.md` row
   (`reason: scheduled`, note "retired by WIF").

When WIF is adopted, the [Quick checklist](#quick-checklist) item for
the `ANTHROPIC_API_KEY` secret becomes "federation rule pinned to
repo+ref + `id-token: write` granted to CI". Caveat: WIF requires an
org (Console → Settings → Organization) — individual accounts cannot
register issuers; the compensating control until then remains the
narrow project-scoped key above. Org **Admin API** keys
(`sk-ant-admin…`) are a separate, *larger-blast-radius* tier — never
in CI, custody + incident response via `.claude/scripts/key-hygiene.py`
and the ADR-054 admin-key amendment (PLAN-135 W5 O9).

### OIDC → key-broker for CI credentials (advanced; PLAN-133 E7)

A standing `ANTHROPIC_API_KEY` repo secret is the simplest setup but it
is **long-lived** and readable by every workflow run. A stronger posture
removes the standing secret entirely and mints **short-lived, scoped**
provider credentials per CI run, gated by the run's **OIDC identity
token**:

1. The CI job requests an **OIDC id-token** from a trusted issuer it
   already has — e.g. GitHub Actions OIDC
   (`permissions: id-token: write`, `token.actions.githubusercontent.com`),
   a Kubernetes projected ServiceAccount token, or a cloud
   workload-identity token. This token is **short-lived and
   audience-bound** and carries **no provider key**.
2. The job presents it to a **key broker** you run. The broker
   **verifies** the token, then **mints** a short-lived, narrowly-scoped
   provider credential and returns it. Your standing provider key lives
   **only inside the broker** and never enters a workflow run.

The repo ships an **editable reference recipe** for the broker's verify
step at [`templates/oidc-proxy/`](../templates/oidc-proxy/) — copy it
into your own broker service and adapt. It is a from-scratch stdlib
re-implementation (PLAN-133 rite §2: nothing fetched or executed from the
`aaif-goose/goose` fork) and it re-uses the bearer/DPoP hardening already
ratified for MCP in **ADR-122**:

- **alg allowlist** — asymmetric algorithms ONLY; `alg=none` and every
  `alg=HS*` are rejected **at parser precedence, BEFORE signature
  verification** (ADR-122 §A.1 / §A.3 clause 2). Closes JWT
  alg-confusion / key-confusion downgrades.
- **per-jti nonce cache** — each `jti` is **single-use within its TTL**
  (TTL ≤ 5 min, RFC 9449 §11.1); key is the `(jti, iat)` tuple; eviction
  is **LRU + TTL only** (no count-based eviction → no cache-flush DoS).
  A replayed token is denied (ADR-122 §A.4).

The recipe is **fail-CLOSED** on every trust decision (a broker that
fails open would mint a credential for an attacker) and its
`VerificationError.reason` is a **closed enum that never echoes the token
or any claim value**. It does **no network I/O** and constructs **no LLM
or provider client**; the asymmetric signature check is an
adopter-injected seam (the stdlib has no public-key crypto), and the
shipped default `RejectAllVerifier` **denies every token** until you wire
a real verifier — so an unconfigured broker mints nothing.

Tests for the recipe live at `templates/oidc-proxy/tests/` and are run on
demand (`python -m pytest templates/oidc-proxy/tests/ -q`); they are
intentionally outside the framework's pinned `pytest.ini :: testpaths`
because `templates/` ships adopter artifacts, not framework CI surface.

When you adopt the broker, the
[Quick checklist](#quick-checklist) item for the
`ANTHROPIC_API_KEY` secret can be replaced by "broker reachable + OIDC
`id-token` permission granted to CI".

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

## Supply-chain hardening (Sprint 5 Phase 2)

All third-party tools used in CI are pinned and verified to defend
against upstream tampering or accidental breakage.

### GitHub Actions

Every `uses:` reference in `.github/workflows/*.yml` resolves to a
**commit SHA**, not a tag or branch. Tag references are mutable and
can be retargeted post-publication; SHA references cannot. SHA
references carry a trailing comment with the human-readable version
(e.g. `# SHA-pinned: actions/checkout@v4.2.2`).

Dependabot (`.github/dependabot.yml`) is configured to open PRs that
bump these references when upstream releases ship.

### actionlint binary

`validate.yml` previously installed `actionlint` via
`bash <(curl -sSL ...)` against `main`. As of Sprint 5 Phase 2, the
binary is downloaded as a **versioned release asset** and verified
against an expected SHA-256 before execution. The version + SHA pair
lives inline in `validate.yml`; bumping requires updating both.

Current pin:

| Tool | Version | Asset | SHA-256 |
|---|---|---|---|
| actionlint | 1.7.7 | `actionlint_1.7.7_linux_amd64.tar.gz` | `023070a287cd8cccd71515fedc843f1985bf96c436b7effaecce67290e7e0757` |

Bump procedure:

```bash
VERSION=<new-version>
URL="https://github.com/rhysd/actionlint/releases/download/v${VERSION}/actionlint_${VERSION}_linux_amd64.tar.gz"
curl -fsSL -O "$URL"
shasum -a 256 "actionlint_${VERSION}_linux_amd64.tar.gz"
# Cross-check against the rhysd/actionlint release notes before committing
```

Then update both `VERSION` and `EXPECTED_SHA256` in
`.github/workflows/validate.yml` and the table above.

### Node 24 deprecation tracking

`actions/checkout@v4`, `actions/setup-python@v5`, and
`actions/upload-artifact@v4` currently declare `runs.using: node20`.
GitHub's deprecation timeline targets **2026-05-15** for Node 20 in
runners, after which the actions must declare `node24` or be replaced.

**Sprint 6 Phase 6a status** (2026-04-13):

- ✅ Pinned versions documented in `docs/actions-versions.md`
  (freeze-doc)
- ✅ `npm-publish.yml` bumped to `node-version: 24` runtime
- **DEFERRED to Sprint 7** (per R-DEV3 consensus — each action bumps
  in its own PR to isolate schema-break risk):
  - `actions/checkout@v4 → v5`
  - `actions/setup-node@v4 → v5`
  - `actions/setup-python@v5.4 → v5.5+` if required
  - `actions/upload-artifact@v4 → v5` (with input-schema audit)

Dependabot is configured to open these PRs individually. The
freeze-doc at `docs/actions-versions.md` tracks the upgrade procedure.

## Quick checklist

- [ ] `.github/CODEOWNERS` is in the repo (shipped Sprint 2 C.3)
- [ ] Branch protection rule for `main` is configured per this doc
- [ ] "Allow administrators to bypass" is **unchecked**
- [ ] `ANTHROPIC_API_KEY` secret is set under **Settings → Secrets**
- [ ] `docs/rotation-log.md` exists (even if empty) so rotations have
      a place to land
- [ ] Absolute floor `0.6` is appropriate for the project (lower it if
      scenarios are noisy; higher only after stability established)
