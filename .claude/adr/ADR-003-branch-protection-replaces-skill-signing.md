# ADR-003: Branch protection replaces skill signing

**Status:** ACCEPTED-AMENDED (AMEND-1 PROPOSED 2026-05-24, S160 — see §AMEND-1)
**Date:** 2026-04-11 (PLAN-002 §3 Q5, Sprint 2 Item F)
**Decision drivers:** an actor with write access to a skill file also has write access to its signature; git already provides cryptographic integrity via commit hashes; the real threat is "skill was weakened without review", which is a social problem.

## Context

PLAN-001 §4 originally proposed, in the P2 section, cryptographic
signing of `SKILL.md` files as an integrity defense:

> "Self-signed SHA-256 hashes in `.claude/skills/INTEGRITY.sha256` so
> that a tamper would be detected."

The debate round 1 on PLAN-002 (VP Engineering + Architect R-VP9)
flagged this as a fix for the wrong problem.

**The threat model:** "what if someone modifies a skill to weaken
its checklist or remove a veto condition, and the CEO spawns an
agent that silently uses the weakened version?"

**The skill-signing proposal's flaw:** whoever can write `SKILL.md`
can also write `INTEGRITY.sha256`. Crypto doesn't defend against an
authorized author making a weakening change — that's a **review**
problem, not a **crypto** problem.

Git already provides cryptographic integrity via commit hashes. Every
commit touching `.claude/skills/**` is already trivially auditable.
What's missing is a **gate** that forces human review on those
commits before they land on `main`.

## Decision drivers

- **The real threat is social, not cryptographic.** "Skill was
  weakened without review" is the failure mode, and it's not solved by
  adding a second file that the same actor controls.
- **Git is already the integrity log.** Every skill change has a
  SHA-256 commit hash, an author, a timestamp, a diff. Adding a
  parallel hash file duplicates what git already does.
- **GPG-signed hashes with an external key** are a real mechanism but
  introduce key management, airgapped signing, and single-maintainer
  bus factor. Out of scope for a framework whose whole design target
  is "clone + install = working".
- **Branch protection is a one-click GitHub setting.** It costs
  nothing to enable, can't be bypassed by the configured users, and
  is the exact mechanism used by every mature project on GitHub.

## Options considered

### Option A: Self-signed SHA-256 in `INTEGRITY.sha256`

```
.claude/skills/INTEGRITY.sha256:
  aa7c34203cacad7ff53388f8d1a8ac4f  core/security-and-auth/SKILL.md
  bb1d23442bbdd3faa2b4c91...        core/architecture-decisions/SKILL.md
  ...
```

- (+) Airgapped-friendly (no GitHub dependency)
- (+) Simple to implement (one shell script, one CI check)
- (-) **The same actor who changes the SKILL also changes the hash.**
  This is not a defense against the threat model.
- (-) Doesn't catch the actual failure mode ("skill was weakened
  without review").
- (-) Adds a new file that must be kept in sync on every skill edit,
  creating its own regression surface.

**Rejected** — wrong problem.

### Option B: GPG-signed hashes with an external key

Maintainer signs `INTEGRITY.sha256` with their GPG key; CI verifies
the signature against a pinned public key.

- (+) Actually cryptographically strong
- (+) Catches unauthorized edits even on a compromised repo
- (-) Single-maintainer bus factor — lose the key, lose signing
- (-) Requires every contributor to set up GPG, or all changes flow
  through one person
- (-) Installation of the framework into a new project requires the
  target project to have its own signing key and CI setup
- (-) Airgapped signing workflow is a non-trivial operational burden
- (-) Still doesn't catch "the maintainer signed a bad change"

**Rejected** — complexity is wildly out of proportion to the threat.

### Option C: GitHub branch protection + CODEOWNERS (CHOSEN)

Configure GitHub branch protection on `main`:
- Require a pull request before merging
- Require approvals (1 minimum)
- Dismiss stale approvals when new commits are pushed
- Require review from Code Owners
- Require status checks to pass before merging (the `validate` job)
- Require branches to be up to date before merging
- Require conversation resolution before merging
- Do not allow bypassing the above settings

Configure `.github/CODEOWNERS`:
```
.claude/skills/**         @<owner>
.claude/hooks/**          @<owner>
.claude/plans/PLAN-*.md   @<owner>
PROTOCOL.md               @<owner>
```

Any change to `.claude/skills/**` requires a PR + review by a Code
Owner before merging. The reviewer sees the diff, can reject it, and
the git history is the integrity log.

- (+) No new code
- (+) Leverages existing GitHub infra
- (+) Catches the actual threat (weakening changes get reviewed)
- (+) Bypass-proof for the configured users (admin-only override,
  and even that can be disabled)
- (+) One-click setup: document the settings in
  `docs/BRANCH-PROTECTION.md` (Sprint 2 Item F); Owner enables in the
  GitHub UI after Sprint 2 pushes
- (-) Depends on GitHub (airgapped clones have no integrity check —
  acceptable since they have git)
- (-) Bus factor: if the single reviewer becomes unavailable, PRs
  can't merge — mitigated by adding a second CODEOWNER when a team
  forms (out of Sprint 2 scope)

## Decision

**Option C.** No crypto. Use GitHub branch protection + CODEOWNERS
requiring PR review for `.claude/skills/**` (and `.claude/hooks/**`,
`.claude/plans/PLAN-*.md`, `PROTOCOL.md`) changes.

**Timing** — per PLAN-002 §11-bis Q3:

- **Sprint 2 (current):** ship the documentation
  (`docs/BRANCH-PROTECTION.md`, Item F) and the `.github/CODEOWNERS`
  catchall. Do NOT enable branch protection during Sprint 2 —
  15-18 atomic commits pushed directly to `main` would each be
  auto-approved by the solo Owner, adding friction without buying
  security.
- **After Sprint 2 pushes + CI verification:** Owner clicks through
  the branch protection setup in GitHub Settings → Branches. One-time
  configuration.
- **Sprint 3 onwards:** every change to protected paths goes through
  a PR review gate.

## Consequences

- (+) **No new code** — ship a doc, flip a GitHub setting, done
- (+) **Leverages existing infra** — every maintainer on GitHub
  already knows how branch protection works
- (+) **Catches the real threat** — weakening changes get reviewed
- (+) **Scales to teams** — adding a second CODEOWNER adds a second
  review requirement automatically
- (-) **Depends on GitHub** — airgapped clones have no review gate
  (acceptable; they still have git hashes)
- (-) **Single-reviewer bus factor** — solo Owner is the only Code
  Owner until a team forms
- (~) **Opt-in enablement** — branch protection is a setting, not
  code. If the Owner forgets to enable it post-Sprint-2, the gate
  doesn't exist. Mitigated by a single instruction block in
  `BRANCH-PROTECTION.md`.

## Blast radius

**L1** — config-only. One new documentation file
(`docs/BRANCH-PROTECTION.md`), one new `.github/CODEOWNERS`. No code
changes. The `.claude/skills/INTEGRITY.sha256` proposal from PLAN-001
P2 is **canceled** by this ADR — it will not be built.

## Related commits

- `bdf6570` (PLAN-002 expansion) — Q5 recorded the decision
- Sprint 2 Item F commit — ships `docs/BRANCH-PROTECTION.md` +
  `.github/CODEOWNERS`

## Alternatives for the future

If a future requirement emerges for **airgapped integrity** (e.g.
the framework is installed in a classified environment without
GitHub access), this ADR should be reopened and GPG-signed hashes
(Option B) reconsidered — the bus factor concern is solvable with
two maintainers and two keys, and the operational burden may be
acceptable when the threat model includes nation-state attackers.
As of Sprint 2, that requirement does not exist.

## Enforcement commit

`b7aef7ede65d` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)

---

## AMEND-1 (PROPOSED) — Branch protection is infeasible on this repo tier; compensating controls are the interim primary mechanism

**Status:** PROPOSED
**Date:** 2026-05-24 (Session 160, PLAN-112-FOLLOWUP-branch-protection-feasible)
**Amends:** the §Decision "Timing" block + §Consequences "Opt-in enablement" note.

### Why this amendment

ADR-003 chose Option C (GitHub branch protection + CODEOWNERS) and called
it a "one-click GitHub setting" that the Owner would flip "after Sprint 2
pushes". That premise is **false on the current repository tier**, verified
at HEAD (2026-05-24):

- `gh repo view` → `{"isPrivate":true,"visibility":"PRIVATE"}` (free-tier,
  owner `Canhada-Labs`).
- `gh api repos/.../branches/main/protection` → **HTTP 403: "Upgrade to
  GitHub Pro or make this repository public to enable this feature."**

Branch protection on a **private** repository is a **GitHub Pro-only**
feature. The promised "flip after Sprint 3 Phase 0" therefore **never
occurred and cannot occur** on the current plan. PLAN-003 shipped ~2026-04-12;
"Sprint 3 Phase 0" ended ~107 sessions ago. **The original timing block is
retracted** — it described an action that was infeasible from the start.

### Chosen path — Path C (compensating controls now + milestone-gated upgrade)

Per the S160 Wave A debate (security-engineer + identity-trust-architect,
both ADJUST_PROCEED, **0 VETO**):

1. **Now (interim primary mechanism):** the shipped hook + GPG-sentinel +
   Codex-pair-rail stack is the de-facto protection for governance paths.
   It is enumerated, with its residual risks, in `docs/BRANCH-PROTECTION.md`.
2. **Milestone-gated upgrade to real server-side protection (Path A):** when
   ANY of these triggers fires (NOT a date — honors the no-calendar-gates
   doctrine, ADR-095): **repo goes public**, OR **team size > 1**, OR
   **first production adopter**. At that point the Owner makes the
   cost/visibility decision (GitHub Pro or public repo) and enables
   server-side branch protection.
3. **`team size > 1` ALSO re-activates key custody** as a dedicated
   followup: GPG key rotation + per-signer revocation. Single Owner-key
   custody is an acceptable residual **only** at team-size-1; the moment a
   second principal exists it flips from acceptable-residual to active red
   flag.

### Load-bearing scope correction (security + identity, verbatim)

The compensating-controls stack is an **authorization / authoring-time**
control: it authenticates the author of each governance edit (Owner GPG
sentinel) and blocks the **agent tool-call rail** (the canonical-edit,
arbitration-kernel, bash-safety, pair-rail hooks). **It is NOT a
merge / server-side ref control.** These hooks gate the agent tool-call
rail only; they do **NOT** constrain a human operator (or a compromised
local credential) running `git` directly. A client-side authoring-time
control is **not equivalent** to a server-side ref guard. The residual is
the **un-gated direct-push path** to `main`.

Do not inherit ADR-003's original "one-click setting, done" framing — that
framing conflated an authoring control with a ref guard.

### Named residuals (interim, until Path A)

- Agent rail permits `git push --force-with-lease` (only `--force`/`-f`
  blocked) → lease-checked history rewrite remains possible on the rail.
- Single Owner GPG key, no rotation/revocation story (re-activated on
  `team > 1`).
- No server-side pre-merge review.
- `.github/CODEOWNERS` is **aspirational / inert** until Path A — it is only
  enforced when server-side protection is active.

### Owner decision boundary

Path A's cost/visibility change (GitHub Pro spend OR making the repo public)
is an **explicit Owner decision**, not auto-actioned by this amendment.
This amendment records the constraint, retracts the impossible timeline,
and documents the interim posture; it does not spend money or change
visibility.
