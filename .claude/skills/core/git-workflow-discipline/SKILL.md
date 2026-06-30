---
name: core-git-workflow-discipline
description: >
  Authoritative git workflow doctrine for {{PROJECT_NAME}}. Encodes the
  mandatory phase sequence (branch → draft-commits → PR-open → review-gate →
  merge → tag) that every multi-commit plan must follow; phases are not
  suggestions — out-of-order execution breaks release integrity and invalidates
  canonical-path governance. Use when authoring a branch strategy, writing
  commit messages, opening a PR, enforcing a review gate, merging to main, or
  cutting a release tag. Pairs with `task-chains.yaml:git-workflow-canonical`
  for machine-readable phase ordering; this skill carries the doctrinal WHY
  and WRONG/CORRECT patterns that animate the pipeline steps.
owner: Staff Code Reviewer (archetype)
inspired_by:
  - source: msitarzewski/agency-agents/engineering/engineering-git-workflow-master.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: pattern_reference
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-06
# --- smart-loading fields (PLAN-083 Wave 0a sub-agent 0.7a) ---
domain: core
priority: 5
risk_class: low
stack: [git]
context_budget_tokens: 900
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 5}
  engine: {active: true, priority: 5}
  fintech: {active: true, priority: 5}
  trading-readonly: {active: true, priority: 6}
  generic: {active: true, priority: 4}
activation_triggers:
  - {event: help-me-invoked, regex: "(?i)git|commit|rebase|branch"}
---

# Git Workflow Discipline

The git workflow phases are not suggestions. Each phase has a precondition
that the previous phase satisfies; skipping or reordering them breaks the
release integrity invariant and can silently corrupt the canonical-path
sentinel (ADR-051), invalidate PR review authority, or produce unsigned tags.

The CEO and every spawned agent executing multi-commit work MUST follow the
sequence encoded in `task-chains.yaml:git-workflow-canonical`. This SKILL
carries the doctrine — the rationale, the hard rules, the naming conventions,
and the anti-patterns — for agents executing each step.

---

## What This Skill Is (and isn't)

**IS:** Doctrinal content for agents executing the `git-workflow-canonical`
task-chain. The pipeline step names in `task-chains.yaml` point here for
semantic grounding. Reading this skill is mandatory before any agent authors a
branch, commit, PR, or release tag in {{PROJECT_NAME}}.

**IS NOT:** A hook, a CI check, or a mechanical enforcer. The mechanical
invariants live in:
- `check_canonical_edit.py` — guards canonical-path writes
- `check_plan_edit.py` — guards plan-frontmatter transitions
- `.github/workflows/validate.yml` — enforces test + governance gates
- Branch-protection rules (see `docs/BRANCH-PROTECTION.md`)

This skill explains WHY those mechanisms exist and what the agent must do
BETWEEN the mechanical gates.

---

## Phase Sequence (Mandatory)

The six phases form a directed acyclic graph with strict preconditions.
No phase may begin until its predecessor's verify condition is met.

### Phase 1: branch

**Precondition:** Main branch at HEAD, clean working tree (`git status` shows
nothing staged or modified).

**Action:**
```bash
git checkout main && git pull --ff-only origin main
git checkout -b <branch-name>
```

**Verify:** Branch exists locally. `git log --oneline -1` matches main HEAD.

**Rules:**
- Branch from `main` exclusively. Never branch from a stale branch or a
  feature branch (avoids merge-train collisions).
- Use the naming conventions in §Branch Naming below.
- If `git pull --ff-only` fails, STOP. Resolve main divergence before
  branching. Never force-push to resolve.

---

### Phase 2: draft-commits

**Precondition:** Branch created in Phase 1. Working tree clean at branch point.

**Action:** Make the minimum necessary changes. Stage specific files by name.
Commit with a compliant message (see §Commit Message Conventions).

**Verify:** `git diff main...HEAD` shows only the files the plan authorized.
Each commit covers exactly one logical change.

**Rules:**
- Never `git add -A` or `git add .` — only add specific files.
- One logical change per commit. "Logical change" = a unit that can be
  reverted independently without breaking the system.
- Run the test suite and type-checker before the first commit. A failing
  suite is not a commit blocker — but the commit message MUST note the
  failure if committing intentionally broken state (e.g., mid-refactor).
- Never amend a commit that has been pushed for shared review (see Hard
  Rules §5).

---

### Phase 3: PR-open

**Precondition:** At least one commit on the branch. Tests passing (or
failure documented). Branch pushed to remote.

**Action:** Open the PR with a structured description:
```
## Summary
<1-3 bullet points>

## Test plan
[Bulleted checklist of what was tested and how]

## Risk / blast radius
[L1-L5 classification per code-review-checklist skill]
```

**Verify:** PR exists in remote. Title is ≤70 chars. Description contains
Summary + Test plan + Risk sections. At least one reviewer requested.

**Rules:**
- PR title is the squash-commit message. Write it as if it IS the commit.
- Scope is singular: one logical feature, one bug fix, one refactor. Kitchen-
  sink PRs trigger mandatory scope split before review proceeds.
- Reference the plan number in the PR body: `Plan: PLAN-NNN`.
- Never open a draft PR and immediately request review — draft means not ready.
  Flip to "ready for review" only when Phase 2 verify is complete.

---

### Phase 4: review-gate

**Precondition:** PR open (Phase 3). Reviewer assigned.

**Action:** The Staff Code Reviewer archetype (see `core/code-review-checklist`)
runs a full review pass. CEO waits for a VETO-clear verdict before proceeding.

**Verify:** Review verdict is one of: APPROVED / APPROVED WITH CONDITIONS /
BLOCKED. BLOCKED verdict → return to Phase 2 (re-commit to fix). APPROVED WITH
CONDITIONS → conditions documented and controls named before merge.

**Rules:**
- Review is not optional. "This is a small change" is not a reason to skip.
- The VETO floor (ADR-052) applies: changes touching auth, financial math,
  canonical-path writes, or VETO-protected domains require the Opus 4.8
  code-reviewer archetype.
- Reviewer cannot be the sole author of all changed lines. Self-review is
  permitted only for L1 changes (< 50 LoC, single file, no security path).
  For all other changes, a second archetype must review.
- A "LGTM" without findings is a review-quality failure (see
  `core/code-review-checklist §Anti-Patterns in Reviews`).

---

### Phase 5: merge

**Precondition:** Phase 4 verdict is APPROVED or APPROVED WITH CONDITIONS
(with conditions satisfied). **CI is GREEN on the test-merge commit
(`refs/pull/N/merge`), the merge-queue result, or the equivalent
test-merge artifact** — NOT only on the PR branch HEAD. Per
`core/evidence-based-qa` Hard Rule #8, PR-branch-only CI does not prove
the merged result is green; the target branch may have diverged.

**Action:**
- **Squash merge** (default): collapses all draft commits into one clean
  commit on main. The squash-commit message = the PR title + body summary.
- **Merge commit** (repo policy override): used when preserving commit
  history matters (e.g., a long-running feature branch with meaningful
  individual commits).
- **Rebase merge**: used when the branch has 2-3 clean, atomic commits
  that belong in main history individually.

**Verify:** `git log --oneline origin/main` shows the merged commit.
Working tree on main is clean. CI on main is GREEN post-merge.

**Rules:**
- Never merge a PR with a BLOCKED review verdict.
- Never merge if CI is RED. Fix CI before merging, even for "obviously
  correct" changes.
- Delete the branch after merge (remote + local). Stale branches are
  governance noise.
- If a merge conflict arises at merge time, return to branch, rebase from
  main (not the reverse), resolve conflicts, re-push, re-run review-gate
  if the conflict touched reviewed lines.

---

### Phase 6: tag

**Precondition:** Merge complete (Phase 5). CHANGELOG, `VERSION` file, and NPM
`package.json` version are ALREADY in the merged commit on main — release-meta
sync happens during draft-commits (Phase 2) on the release branch, NOT after
merge. Tagging is a verification + signing step, not a metadata-bump step.
**Never commit directly to main.** If release metadata is missing from the
merged commit, return to draft-commits in a new release branch + PR; do not
amend-commit on main and do not "quick fix" via `git commit -am`.

**Action:**
```bash
# Verify release metadata is present in the merged commit before tagging:
git log -1 --name-only origin/main | grep -E "CHANGELOG|VERSION|package.json"
# Tag the verified commit (signed):
git tag -s v<MAJOR>.<MINOR>.<PATCH> -m "v<MAJOR>.<MINOR>.<PATCH>"
git push origin v<MAJOR>.<MINOR>.<PATCH>
```

**Verify:** `git describe --tags --abbrev=0` returns the new tag. GitHub
release workflow (`.github/workflows/release.yml`) triggers on the tag push
and passes all 14 gates.

**Rules:**
- Tags follow semver: `MAJOR.MINOR.PATCH`. No `v1.2` short tags. No
  `v1.2.3-hotfix`. Use `-rc.N` for release candidates.
- Tags on canonical releases MUST be GPG-signed (`-s`). A tag without a
  signature on a release is a governance failure.
- Never re-tag. If the tag is wrong, the release is wrong. Cut a patch
  release. Moving a tag breaks reproducibility for every consumer.
- CHANGELOG entry must precede the tag. The format is
  `## [VERSION] — YYYY-MM-DD — <one-line summary>`.

---

## Hard Rules

1. **Never force-push to main.** `git push --force origin main` is a
   history-rewrite that invalidates all open PRs, corrupts audit trails, and
   loses commits for collaborators. There is no valid use case.

2. **Never force-push to a shared branch.** A branch is "shared" as soon as
   it exists on the remote AND another agent or human has pulled it or opened
   a PR from it. Force-pushing to a shared branch causes divergence for every
   downstream pull.

3. **Never amend after pushing for shared review.** Once a commit is pushed
   and a PR is open, amending that commit rewrites history on the remote branch.
   Instead: make a new commit with the fix. The PR review history stays coherent.

4. **Never bundle unrelated changes in one commit.** One commit = one logical
   change. "While I'm here" additions are scope creep disguised as efficiency.
   They make blame harder, rollback more dangerous, and review harder. The
   `core/minimal-change-discipline` skill governs this invariant.

5. **Never skip the review gate.** The review gate exists because "small"
   and "safe" are not synonyms. The most catastrophic production incidents
   originate in one-line changes. If repo policy provides a documented
   lightweight or docs-only review path (e.g., one-reviewer-with-CODEOWNERS
   for `docs/**` paths), USE that documented path — do not invent ad-hoc
   skips. Every change goes through SOME review path; "I documented why I
   skipped" is not a substitute for review and is not permitted.

6. **Never commit to main directly.** The only commits that land on main are
   merge commits (or squash-merge commits from PRs). Direct commits to main
   bypass the review gate.

7. **Always add specific files, never `git add -A` or `git add .`.** Wildcard
   staging can accidentally include `.env`, credentials, binary blobs, or
   generated files that should not be versioned. Stage by explicit path.

8. **Canonical-guarded paths require a GPG-signed sentinel before merge.**
   `check_canonical_edit.py` enforces this mechanically. A merge attempt that
   bypasses the sentinel hook is a governance failure, not a shortcut.

9. **A failing CI gate is NEVER merged with "we'll fix in follow-up."** Fix
   the CI gate before merging. If the failure is a known infrastructure flake
   (not code-related), document the specific flake with a tracking issue and
   Owner explicit approval before merging.

10. **Release tags are GPG-signed and never moved.** Signed tags are an
    integrity guarantee. Moving a tag destroys that guarantee. A wrong tag
    → cut a patch release.

11. **Every merge to main has a tracking ticket or plan reference.** The PR
    description cites `Plan: PLAN-NNN` or an issue number. Anonymous merges
    with no plan reference are governance gaps.

12. **Rebase from main before requesting review if branch diverged.** A PR
    from a stale branch may have merge conflicts that the reviewer cannot
    evaluate. Rebase first; request review second.

---

## Commit Message Conventions

The framework uses **Conventional Commits** (https://www.conventionalcommits.org/).

### Format

```
<type>(<scope>): <imperative-mood-summary-≤72-chars>

[optional body — explain WHY, not WHAT; WHAT is in the diff]

[optional footers]
```

### Types

| Type | When |
|------|------|
| `feat` | New feature visible to users or framework consumers |
| `fix` | Bug fix — corrects incorrect behavior |
| `chore` | Maintenance — version bumps, dependency updates, tooling |
| `docs` | Documentation-only changes (no code, no config) |
| `test` | Test additions or fixes with no production code change |
| `refactor` | Code restructuring with no behavior change |
| `perf` | Performance improvement (measurable, not speculative) |
| `ci` | CI/CD config changes |
| `style` | Formatting-only (whitespace, linting) — not style opinions |
| `revert` | Reverts a previous commit (reference the reverted SHA) |

### Breaking changes

```
feat(api)!: change response schema for /orders endpoint

BREAKING CHANGE: `total_price` renamed to `total_amount_cents`. Clients
consuming `/orders` must update field references. Migration guide in INSTALL.md §3.
```

The `!` after the scope signals a breaking change. The `BREAKING CHANGE:` footer
is mandatory for MAJOR version bumps.

### Body note pattern

When a commit deviates from a plan or fixes a pre-existing bug discovered
in the course of authoring, document it in the body:

```
fix(security-and-auth): remove phantom --skill/--benchmark flags from CLI invocation

Pre-existing canonical bug discovered during Wave 1a augmentation. The CLI
invocation in the SKILL.md referenced flags that do not exist in the
run-skill-benchmark.py interface. Removed to match actual interface.

NOTE: pre-existing bug fix-forward; deviation from plan scope documented
per Wave 1a pattern (see project_session_91_wave_1a_done.md §exceptions).
```

### Co-Authored-By footer

Every commit authored by a spawned sub-agent must include the footer:

```
Co-Authored-By: Claude <model-name> <noreply@anthropic.com>
```

For example:
```
Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
```

Use a HEREDOC when setting the message in bash to preserve newlines:

```bash
git commit -m "$(cat <<'EOF'
feat(plan-074): add git-workflow-discipline SKILL.md

Wave 1b COMPOSITE candidate. Task-chain entry paired at
task-chains.yaml:git-workflow-canonical.

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Branch Naming

```
<type>/<slug>          (for feature/fix/chore/docs/hotfix branches)
plan-NNN-<slug>        (explicit exception for plan-driven branches)
```

| Prefix | Form | When |
|--------|------|------|
| `feat/` | `feat/<slug>` | New feature or SKILL.md authoring |
| `fix/` | `fix/<slug>` | Bug fix |
| `chore/` | `chore/<slug>` | Maintenance, version bumps, dependency updates |
| `docs/` | `docs/<slug>` | Documentation-only |
| `plan-NNN-<slug>` | `plan-NNN-<slug>` | Work tied to a specific plan — explicit exception to the `<type>/<slug>` rule because the plan number IS the type signal |
| `hotfix/` | `hotfix/<slug>` | Emergency production fix — goes directly to review-gate |

### Rules

- Lowercase, hyphen-separated. No underscores, no camelCase.
- Max 50 characters including the prefix.
- Plan-driven branches use the `plan-NNN-<slug>` form (no slash) — the plan
  number itself encodes the type signal, so the `<type>/<slug>` form does
  not apply. Example: `plan-074-wave-1b-git-workflow`, not
  `plan/074-wave-1b-git-workflow`.
- Never name a branch `main`, `master`, `HEAD`, or any ref name.
- Never reuse a deleted branch name. If `feat/order-history` was deleted
  after merge, the next branch touching order history is `feat/order-history-v2`.

### Examples

```
feat/order-history-pagination
fix/session-token-expiry
chore/bump-anthropic-sdk-0.52.0
plan-074-wave-1b-skill-authoring
hotfix/xss-in-report-renderer
docs/adr-105-accepted
```

---

## WRONG / CORRECT Examples

### 1. Amending a pushed commit

```bash
# WRONG — rewrites history on a shared branch
git commit --amend -m "feat: fix the thing (for real this time)"
git push --force origin feat/my-feature

# CORRECT — new commit, PR history stays coherent
git add src/the-file.ts
git commit -m "fix: correct edge case in the thing (missed in previous commit)"
git push origin feat/my-feature
```

### 2. Force-pushing to main

```bash
# WRONG — rewrites main, invalidates all open PRs
git rebase -i HEAD~3
git push --force origin main

# CORRECT — if history cleanup is needed, do it on the feature branch
# BEFORE the PR is merged, then squash-merge
git checkout feat/my-feature
git rebase -i HEAD~3   # interactive rebase on feature branch only
git push --force-with-lease origin feat/my-feature  # safe: only YOU have this branch
# then open PR and squash-merge
```

### 3. Kitchen-sink PR

```
# WRONG — PR title: "Misc improvements"
# PR contains:
#   - Adds pagination to order list
#   - Fixes typo in README
#   - Refactors auth middleware
#   - Bumps lodash from 4.17.20 to 4.17.21
#   - Adds dark mode support

# CORRECT — four separate PRs:
#   PR 1: feat(orders): add pagination to order list  (Plan: PLAN-045)
#   PR 2: docs: fix README typo in install section
#   PR 3: refactor(auth): extract session-token validation to dedicated middleware
#   PR 4: chore: bump lodash to 4.17.21 (CVE-2021-23337)
```

### 4. Commit-and-pray (no test plan)

```markdown
# WRONG — PR description:
> "Fixes the thing. Should work now."

# CORRECT — PR description:
> ## Summary
> - Fix off-by-one in order pagination cursor that caused page 2 to skip the
>   last item of page 1 when pageSize was not a multiple of 10.
>
> ## Test plan
> - [x] `test_order_pagination_cursor_boundary` now passes (was failing)
> - [x] Full test suite: `pytest .claude/hooks/tests/ -q` — 3261 passed / 0 failed
> - [x] Manually verified pages 1-3 in staging with pageSize=7, 10, 13
>
> ## Risk / blast radius
> L2 — Adjacent. Touches only `src/orders/paginator.ts` and its test file.
> Rollback: revert the squash-commit. No migration needed.
```

### 5. Tag without signature

```bash
# WRONG — lightweight tag, no signature, no GPG verification
git tag v1.14.0
git push origin v1.14.0

# CORRECT — signed tag with message
git tag -s v1.14.0 -m "v1.14.0"
git push origin v1.14.0
# Verify: git tag -v v1.14.0
```

---

## Anti-Patterns

1. **Commit-and-pray:** committing without running tests, relying on CI to
   catch failures. CI is a safety net, not the primary quality gate. The
   agent is responsible for test passage before the first push.

2. **Reviewers-as-rubberstamp:** requesting review as a formality, merging
   immediately after the reviewer approves without reading findings. Every
   finding, even NIT, must be acknowledged or disputed before merge.

3. **VETO-floor bypass:** routing a security or canonical-path change to a
   Sonnet reviewer to save cost. ADR-052 mandates Opus 4.8 for all
   VETO-adjacent reviews. Cost is not a valid override.

4. **Format-logic bundling:** mixing whitespace/formatting changes with
   logic changes in the same commit or PR. Reviewers cannot distinguish
   intentional logic changes from formatting noise. Format-only commits
   are chore/style type; logic commits are feat/fix/refactor.

5. **"Cleaning up while here":** adding unrelated improvements to a branch
   opened for a specific fix. Every addition expands blast radius, adds
   review burden, and risks the primary fix. The minimum-change-discipline
   skill (see §Related Skills) governs this.

6. **Stale branch reuse:** re-opening a merged branch for new work instead
   of creating a fresh branch from main. The merged branch may have diverged
   from main; working from it introduces drift.

7. **Moving tags:** re-tagging a commit after a release to "fix" a mistake.
   The right action is a patch release. Moving tags breaks git's object-
   identity guarantee.

8. **CHANGELOG-after-tag:** writing the CHANGELOG entry or bumping VERSION
   after the tag is pushed. The release workflow validates CHANGELOG content
   at tag push time. Order: CHANGELOG → VERSION bump → npm sync → commit →
   tag → push tag.

9. **Merging with red CI:** "it's just a flake" is never a sufficient
   justification for merging with a failing CI gate. Flakes are tracked
   issues with compensating controls; they are not blanket permission to
   ignore CI output.

10. **Branch-name collision reuse:** naming a new branch identically to a
    recently deleted branch. Git may resurrect refs. Use version suffixes.

---

## Acceptance Criteria

Before any multi-commit plan execution is marked "done," verify:

- [ ] All work occurred on a named branch (never directly on main)
- [ ] Each commit message follows Conventional Commits format
- [ ] Each commit covers exactly one logical change
- [ ] PR opened with Summary + Test plan + Risk sections populated
- [ ] Review gate completed (verdict documented in PR or plan directory)
- [ ] **CI GREEN on the test-merge commit (`refs/pull/N/merge`),
      merge-queue result, OR equivalent test-merge artifact** before merge —
      PR-branch-only CI is insufficient (per `core/evidence-based-qa` Hard
      Rule #8; the target may have diverged)
- [ ] Squash (or merge) commit on main references the plan number
- [ ] Feature branch deleted post-merge (local + remote)
- [ ] CHANGELOG updated before the release tag (if this plan produces a release)
- [ ] Release tag is GPG-signed (if applicable)
- [ ] Each commit's staged files match the plan-authorized scope (process
      requirement — `git log --stat` shows COMMITTED diffs but does NOT
      record which staging command was used; auditability comes from
      reviewer enforcing scope on the diff itself, not from history)
- [ ] No force-push to main (verify with `git reflog origin/main`)

---

## Related Skills

- `core/code-review-checklist` — Review-gate doctrine (Phase 4 preconditions
  and VETO floor). The Staff Code Reviewer archetype loads this skill for the
  review-gate phase.
- `core/minimal-change-discipline` — Governs what goes into each commit (Phase
  2). Prevents scope creep and "while I'm here" additions.
- `core/devops-ci-cd` — CI/CD pipeline configuration that the merge gate
  (Phase 5) depends on. Read before authoring new GitHub Actions jobs that
  must pass before merge.
- `core/pre-plan-brainstorm` — Spec artifact that the review-gate (Phase 4
  Pass 1) validates against. Authors the `spec.md` that the reviewer reads.
- ADR-051 — Canonical-path sentinel discipline; gates canonical-guarded file
  writes that occur during Phase 2 (draft-commits).
- ADR-064 — Release-gate alignment and model routing; governs which archetype
  the review-gate (Phase 4) must dispatch.
- `docs/BRANCH-PROTECTION.md` — GitHub branch protection setup that enforces
  the merge gate (Phase 5) at the remote level.
