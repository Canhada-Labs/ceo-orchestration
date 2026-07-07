# Supply-chain incident playbook

> **Scope.** What to do when `.github/workflows/supply-chain-watch.yml`
> (PLAN-153 Wave E item 4 — **lands with the SENT-E ceremony**; until that
> staged overlay is applied the watch does not exist and only the offline
> `check-action-sha-drift.py` sweep runs) goes red, or when you otherwise
> suspect a supply-chain problem in this repo's action pins or its npm
> package (`ceo-orchestration`). General incident procedure (severity ladder,
> post-mortem template) lives in [`INCIDENT-RESPONSE.md`](INCIDENT-RESPONSE.md);
> disclosure timelines live in [`../SECURITY.md`](../SECURITY.md). This
> playbook is the supply-chain-specific leg: **verify → classify →
> contain → comms**.

Sober framing up front: this repo is stdlib-only at runtime (zero npm
runtime dependencies, zero third-party Python packages — see `SBOM.md`),
so the supply-chain surface is narrow and concrete: **(1)** the GitHub
Actions our workflows execute, and **(2)** the `ceo-orchestration`
package we publish to npm. The weekly watch covers exactly those two.
It is a tripwire, not a guarantee — its own honest limits are listed at
the end.

---

## 0. What the watch actually checked

| Axis | Check | Red means |
|---|---|---|
| (a) | `check-action-sha-drift.py --policy --strict` over `.github/workflows/` | A `uses:` is not a 40-hex SHA pin; OR a `pull_request_target` trigger / unguarded fork-reachable secret appeared; OR a pinned SHA no longer matches the upstream tag named in its `# tag` comment; OR transient network failure (exit 2 — check the log before escalating) |
| (b) | npm registry: `dist-tags.latest` → attestations endpoint → tag correspondence → `npm audit signatures` | The latest published version lost its SLSA provenance attestation; OR it has no matching `v<version>` tag in this repo; OR registry signature verification failed |

---

## 1. Verify (before treating it as an incident)

Do this first. Roughly half of scheduled-watch reds are transient.

1. **Open the failing run log** (link is in the pinned
   `supply-chain-watch` issue). Identify which axis redded and the
   exact rc.
2. **Axis (a), rc=2:** distinguish drift from network. Re-run locally:

   ```bash
   GITHUB_TOKEN=<a-read-only-token> \
     python3 .claude/scripts/check-action-sha-drift.py --policy --strict
   ```

   - `skipped (network/unknown)` lines with zero `DRIFT` lines →
     transient network. Re-run the workflow (`workflow_dispatch`). Not
     an incident unless it repeats across runs.
   - One or more `DRIFT` lines → go to §2, class **action-compromise
     (suspected)**. A moved upstream tag is exactly how a compromised
     action re-points existing consumers.
3. **Axis (a), rc=1:** read the violation list. If the offending line
   was introduced by a recent commit in *this* repo → class
   **our-drift** (someone merged an unpinned/unsafe workflow change).
4. **Axis (b):** re-check by hand from a clean machine:

   ```bash
   curl -fsS https://registry.npmjs.org/ceo-orchestration \
     | python3 -c 'import json,sys; print(json.load(sys.stdin)["dist-tags"]["latest"])'
   curl -fsS "https://registry.npmjs.org/-/npm/v1/attestations/ceo-orchestration@<latest>" \
     | python3 -m json.tool
   git ls-remote --tags https://github.com/Canhada-Labs/ceo-orchestration.git "v<latest>"
   ```

   - Attestation present + tag exists → the CI red was transient;
     re-run the workflow.
   - Latest version has **no matching tag in this repo** → treat as
     **npm-regression (suspected account compromise)** immediately.
     Do not wait for a second signal.

## 2. Classify

Pick one primary class; it determines the containment path.

| Class | Signals | Typical root cause |
|---|---|---|
| **action-compromise** | Upstream tag now dereferences to a different SHA than our pin's `# tag` comment claims; or public advisory about the action | Upstream action repo/tag hijacked. NOTE: our SHA pin means we are NOT executing the new code — the drift is a signal about the upstream ecosystem, and a prompt to re-review before any future bump |
| **npm-regression** | Provenance attestation missing on latest; `npm audit signatures` fails; a published version with no matching repo tag | Worst case: npm account/token compromise and an out-of-band publish. Milder: a publish pipeline change dropped `--provenance` |
| **our-drift** | Policy/format violation introduced by a commit in this repo | A workflow merged without SHA pin, with `pull_request_target`, or with an unguarded fork-reachable secret |

Severity mapping (ladder defined in `INCIDENT-RESPONSE.md`): a published
rogue npm version is SEV-1; action-compromise where our pin predates the
hijack is SEV-3 (we are pinned; no exposure) unless a workflow already
bumped to the hijacked SHA; our-drift is SEV-3 unless a secret was
actually reachable from a fork PR, then treat as SEV-2 and rotate.

## 3. Contain

### 3a. action-compromise

1. **Freeze bumps:** do not merge any Dependabot/manual bump of the
   affected action until upstream publishes a post-mortem.
2. **Confirm exposure window:** `git log -S '<pinned-sha>'` on the
   workflow file — verify the SHA we pin predates the compromise window
   from the upstream advisory. If any workflow ran the compromised SHA,
   escalate to SEV-2: rotate every secret that job could read
   (`gh secret list` per environment; then rotate at the provider).
3. **Pin rollback:** if a recent bump landed the bad SHA, revert the
   commit (`git revert`), push, and confirm `validate.yml` +
   `check-action-sha-drift.py` green.
4. If the action is unsalvageable, replace or vendor the step
   (`_README.md` SHA-pinning section governs any replacement).

### 3b. npm-regression

1. **Kill the pipeline first:** set repo variable `CEO_SOTA_DISABLE=1`
   (Settings → Actions → Variables) — every workflow, including
   `npm-publish.yml`, short-circuits on next trigger (`_README.md` §R8).
2. **Revoke credentials:** npmjs.com → Access Tokens → revoke all
   automation tokens for the package; rotate the Owner account password
   + 2FA recovery codes. On the GitHub side, check
   Settings → Environments → `production-npm` required-reviewer list is
   intact (that manual gate is the last line before any publish).
3. **Deprecate/unpublish path** for a rogue version:

   ```bash
   npm deprecate ceo-orchestration@<bad-version> \
     "SECURITY: do not install — see GHSA advisory"
   ```

   Deprecation is immediate and always available. Full `npm unpublish`
   of a version is subject to npm's unpublish policy (roughly: within
   72 hours, or later only if the version has no dependents and low
   traffic — otherwise it requires npm support). Do both: deprecate
   now, request unpublish/security takedown via npm support in
   parallel. Do not rely on unpublish being possible.
4. **Verify the good state:** after cleanup, `npm view ceo-orchestration
   versions` and confirm `dist-tags.latest` points at a version whose
   tag + attestation verify (§1.4 commands).

### 3c. our-drift

1. Revert or fix the offending workflow commit (SHA-pin it, remove the
   forbidden trigger, add the head-repo fork guard per `_README.md` §R9).
2. If a secret was exposed to fork PRs: rotate it at the provider and
   in repo/environment secrets; note that fork-PR runs of
   `pull_request`-triggered workflows get a read-only `GITHUB_TOKEN`
   and no secrets by default — actual exposure requires the guard to
   have been missing on a `pull_request_target` or self-hosted path, so
   check the run logs for fork-origin runs before assuming exfiltration.
3. Add the missed pattern to the policy validator if it was a class,
   not an instance (`.claude/scripts/check-action-sha-drift.py`,
   `_policy_violations`), with a planted-violation test in
   `.claude/scripts/tests/test_check_action_sha_drift.py`.

## 4. Comms

Follow the disclosure table in `SECURITY.md` (§coordinated disclosure);
supply-chain specifics:

1. **Pinned issue:** the watch already maintains one issue labeled
   `supply-chain-watch`. Post triage status there first — it is the
   coordination point (class, severity, containment steps taken).
2. **If users could have installed a bad artifact** (npm-regression
   SEV-1): publish a GitHub Security Advisory naming the exact bad
   version(s), add a `### Security` entry to `CHANGELOG.md`, and update
   the README install section if `latest` moved. `SECURITY.md` timelines
   apply (notify ≤ 24h after fix).
3. **If no user exposure** (pinned action drift, our-drift caught by
   the watch before merge to a release): a closing comment on the
   pinned issue + post-mortem file `docs/incidents/YYYY-MM-DD-<slug>.md`
   (template in `INCIDENT-RESPONSE.md`) is sufficient. No advisory for
   non-exposures — do not inflate.
4. Close the pinned issue only when the watch runs green again
   (re-trigger via `workflow_dispatch` — do not wait for Monday).

---

## Honest limits of the watch

- **Axis (a)** proves our pins are SHAs and our workflow policy holds;
  the drift leg only fires for pins that carry a `# tag` comment, and
  it compares refs, not code. It cannot detect a compromised action
  whose tag was hijacked *before* we first pinned it.
- **Axis (b)** proves the registry still serves a provenance
  attestation and signatures verify. It does NOT rebuild the package or
  diff the tarball against this repo, and it cannot stop a compromised
  account publishing a *new* version with valid provenance from a
  compromised workflow — the tag-correspondence check is only a partial
  tripwire for that. `npm audit signatures` on a zero-dependency
  package verifies exactly one package; it adds no dependency-tree
  coverage because there is no tree.
- The watch runs weekly. The exposure window between incident and
  detection can be up to 7 days; for anything time-critical, trigger it
  manually (`workflow_dispatch`).
