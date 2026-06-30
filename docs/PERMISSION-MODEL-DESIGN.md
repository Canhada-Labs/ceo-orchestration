# Permission Model — Design Notes (v1.0 DRAFT)

> **STATUS: DRAFT — v1.0 design notes, no enforcement. Enforcement deferred to v1.1 per PLAN-083 §4.**
>
> **Exception:** §10 (*native-floor*, PLAN-135 W1 S2) documents a CONCRETE,
> shipping artifact — the harness-native `permissions` block staged for the
> W1 Owner ceremony. It is a different layer from the §§1–9 role model.
>
> This document defines the **conceptual** permission model for future
> multi-user operation of the framework. No code paths in v1.0 read
> `role` to gate behavior. Owner remains the sole effective principal
> until v1.1 lands the enforcement layer. See "Enforcement gap" + "Migration plan"
> below for the v1.1 work.

## 1. Why this exists in v1.0

PLAN-083 §1 pins the test surface to **a representative set of adopter
repositories** (adopter-1 front + adopter-1 engine + adopter-2 front +
adopter-2 engine + a trading-readonly fixture repo). Multi-user permission
enforcement is explicitly deferred to v1.1
(see PLAN-083 §4 row "Multi-user permissions enforcement (junior/senior)").

However, **the design must exist now** so that v1.1 can implement against a
stable contract — not invent the role model from scratch under deadline pressure
once a real second user (e.g. a junior engineer or contractor at an adopter org) needs
access. Codex pair-rail consensus (PLAN-083 thread `019e1803`) was explicit
that foundational docs ship in v1.0 even when the enforcement is v1.1.

## 2. Roles

Four conceptual roles, ordered by privilege (most → least):

### 2.1 `owner`

- **Who:** the human who owns the GPG sentinel key (currently the Owner,
  `00000000…`) and the GitHub repo admin seat.
- **Authority:** full kernel-override on `_CANONICAL_GUARDS` paths via the
  documented ceremony pattern (PLAN-080 / PLAN-081 precedent); sole signer of
  release sentinels (`approved.md.asc`); sole approver of plan transitions to
  `done`; sole pusher of git tags; sole flipper of branch protection rules.
- **Existing mechanism:** GPG key + git config `user.signingkey` + GitHub
  admin seat. Already enforced cryptographically — `owner` role is a label
  on this existing identity, not new infra.
- **In Owner's solo workflow (v1.0):** always the maintainer.

### 2.2 `senior`

- **Who:** trusted engineer with PR-merge authority; can co-author cross-LLM
  Pair-Rail debates as second voice; cannot self-approve sentinels.
- **Authority:** Edit/Write on canonical paths **via PR review process** —
  changes land through GitHub PR with at least one `owner` co-sign + passing
  `validate.yml`. Can invoke `/spawn` and `/debate` for L3+ tasks. Can read
  `audit-log.jsonl`. Can transition plans `draft → reviewed`. Cannot transition
  to `done` (sentinel signing required) and cannot push directly to main.
- **Existing mechanism (v1.1 target):** branch protection requires 1 review;
  `senior` is the role expected to give that review. Not yet enforced in v1.0.

### 2.3 `junior`

- **Who:** new engineer / contractor / vibecoder learning the framework on a
  protected playground; default for any unknown identity touching the framework.
- **Authority:** **read-only by default.** Edit/Write restricted to
  `non-canonical` paths (everything outside `_CANONICAL_GUARDS`) via the
  existing `check_canonical_edit.py` HARD-DENY. Can propose plan drafts in
  `.claude/plans/PLAN-<NNN>-<slug>.md` but cannot transition status from
  `draft → reviewed`. Cannot invoke `/debate` close (only `start`). Cannot
  install the framework into a new repo (`install.sh` requires `owner` or
  `senior` per v1.1 plan).
- **Why read-mostly:** vibecoder team-onboarding requires a "safe sandbox"
  where a new user can explore + propose without breaking the audit chain or
  signing surface. Existing `_CANONICAL_GUARDS` already gives 80% of this —
  v1.1 only needs to add plan-transition + sentinel checks.

### 2.4 `service`

- **Who:** automated agents — CI runners (`validate.yml`, `release.yml`,
  `benchmarks.yml`), scheduled jobs (cron via /loop or /schedule skills),
  webhook handlers, future MCP servers acting on framework's behalf.
- **Authority:** restricted to a **specific Bash command allowlist** —
  read-only `gh`, `git log`, `pytest`, `validate-governance.sh`, `audit-query.py`.
  Cannot edit canonical, cannot edit `settings.json`, cannot push, cannot
  sign sentinels, cannot transition plans, cannot invoke `/spawn` or
  `/debate`. Can emit to `audit-log.jsonl` via documented `_lib/audit_emit.py`
  API but with `actor: service:<job-name>` (v1.1 schema extension — see
  Enforcement gap §5).
- **Why narrow:** service identity is the most dangerous misuse vector — a
  compromised GitHub Action with broad permissions becomes a supply-chain
  attack on every framework consumer. Principle of least privilege is
  non-negotiable here.

## 3. Capability matrix

Twelve representative capabilities × four roles. Cell values:

- `allow` — direct, no friction
- `deny` — hard block (existing or v1.1 enforcement)
- `via PR review` — landed through pull request with required reviews + CI
- `via Owner co-sign` — requires `owner` action in the same workflow step

| # | Capability                                                 | `owner`            | `senior`           | `junior`           | `service`          |
|---|------------------------------------------------------------|--------------------|--------------------|--------------------|--------------------|
| 1 | Edit core skill (`.claude/skills/core/**/SKILL.md`)        | allow              | via PR review      | deny               | deny               |
| 2 | Write Python hook (`.claude/hooks/**`)                     | allow              | via PR review      | deny               | deny               |
| 3 | Sign release sentinel (`approved.md.asc`)                  | allow              | deny               | deny               | deny               |
| 4 | Transition plan `reviewed → done`                          | allow              | via Owner co-sign  | deny               | deny               |
| 5 | Invoke `/spawn` (dispatch sub-agent)                       | allow              | allow              | deny               | deny               |
| 6 | Invoke `/debate start <PLAN-NNN>`                          | allow              | allow              | allow              | deny               |
| 7 | Read `audit-log.jsonl` + run `audit-query.py`              | allow              | allow              | allow              | allow              |
| 8 | Write to `audit-log.jsonl` (via `_lib/audit_emit.py`)      | allow              | allow              | allow              | allow              |
| 9 | Run `pytest` / `validate-governance.sh` (read-only checks) | allow              | allow              | allow              | allow              |
| 10 | Push to `main` (direct, bypassing PR)                     | allow              | deny               | deny               | deny               |
| 11 | Open a PR against `main`                                  | allow              | allow              | allow              | allow              |
| 12 | Run `install.sh` (install framework into a target repo)   | allow              | allow              | deny               | deny               |

**Reading the matrix:** rows 7-9 + 11 are intentionally open across all roles —
they are observability / proposal primitives that drive velocity. Rows 1-2 + 4
+ 10 are the high-blast-radius surfaces and follow least-privilege strictly.
Row 12 is gated to prevent a junior from accidentally bootstrapping the framework
into a production repo without supervision.

## 4. Identity propagation

How role identity travels from shell → Claude Code harness → hook → audit emit:

```
[1] shell (env var)          CEO_ROLE=owner|senior|junior|service
        ↓
[2] CC harness session start  read CEO_ROLE → store in session metadata
        ↓
[3] PreToolUse hook fires     hook reads session metadata via
                              os.environ["CEO_ROLE"] (or a future
                              .claude/state/identity.json file)
        ↓
[4] hook decision logic       compare role × capability table → allow/deny
        ↓
[5] PostToolUse audit emit    `_lib/audit_emit.py` writes JSONL row with
                              `actor: <role>` + `actor_repo: <repo-name>`
                              fields (v1.1 audit-schema extension)
```

**v1.0 status:** step [5] **does NOT yet write `actor` / `actor_repo`** to the
audit row. PLAN-083 §4 explicitly defers the audit-schema `actor`/`user`
extension to v1.1 because adding fields mid-flight to an HMAC-chained log
breaks canonical-JSON ordering + replay-test gate (R1 Sec finding). The role
**is documented here** so v1.1 lands the schema extension against a stable
target.

**Existing precedent for env-driven identity:** the framework already uses
`CLAUDE_PROJECT_DIR`, `CEO_OVERHEAD_ACK`, `CEO_PAIR_RAIL_VERDICT_OPTIONAL`
(PLAN-081 GA transition flag) and similar env vars as soft signals to hooks.
`CEO_ROLE` follows the same pattern.

## 5. Enforcement gap (what is NOT enforced in v1.0)

The following are **explicitly documented as non-enforced** in v1.0; do not
assume they are blocked by code.

| # | Item                                                       | v1.0 status        | v1.1 target                          |
|---|------------------------------------------------------------|--------------------|--------------------------------------|
| E1 | Actual capability checks against role (matrix §3)         | not wired          | `check_role_capability.py` PreToolUse hook reading `CEO_ROLE` env |
| E2 | Audit row `actor` / `actor_repo` fields                   | not present in schema | SPEC v2.24 + HMAC chain replay-test gate proven |
| E3 | PR review automation enforcing `senior` co-sign           | not configured     | GitHub branch protection rule + CODEOWNERS additions |
| E4 | Plan transition gating (`junior` cannot flip status)      | not gated          | `check_plan_edit.py` extension reading role |
| E5 | Sentinel signing gated to `owner`                         | gated by GPG key possession (de facto) | label this in audit emit (no new gate needed) |
| E6 | Cross-repo identity (same `senior` across 5 Owner repos)  | n/a — Owner solo   | shared `~/.claude/identity.json` lookup |
| E7 | `service` Bash allowlist enforcement                      | partial — `check_bash_safety.py` blocks dangerous commands but not by role | extend hook to read role + apply per-role allowlist |
| E8 | `install.sh` role gate (only `owner`/`senior` can install)| not enforced       | `install.sh` reads `CEO_ROLE`, refuses if `junior`/`service`/unset |

**Implication:** in v1.0, **any user with shell access has effective `owner`
capability** (GPG key possession aside). The model is documentary, not
enforced. Treat any non-Owner principal touching the framework in v1.0 as a
manual trust decision.

## 6. Migration plan (v1.0 → v1.1 without breaking Owner's solo workflow)

The risk: turning on enforcement breaks Owner's existing workflow (Owner has
no `CEO_ROLE` env var set today).

**Migration design:**

1. **Default fail-OPEN to `senior` (NOT `owner`) when `CEO_ROLE` is unset.**
   Rationale: `owner` is the most privileged role; defaulting unknown
   identity to `owner` is a security regression. Defaulting to `senior`
   keeps PR review enforcement working for new users while letting Owner
   continue to operate freely (Owner can either set `export CEO_ROLE=owner`
   in `~/.zshrc` or rely on GPG-key-possession as the de-facto `owner`
   signal for sentinel-signing operations only).

2. **Sentinel signing remains gated by GPG-key possession**, not by
   `CEO_ROLE`. This means Owner workflow does not change for the
   release-ceremony path even if `CEO_ROLE` is unset — GPG key matters,
   role label is supplementary.

3. **Capability checks ship dark first** — v1.1 lands the hook code but
   in `audit-only mode` for ≥1 week, emitting `role_capability_would_deny`
   without actually blocking. Owner observes for false positives in his
   own 5 repos before flipping to `enforce` mode.

4. **`CEO_ROLE` env var is opt-in for Owner**; **required for any new
   non-Owner user** before they touch the framework (gated by
   `install.sh` printing setup instructions or a first-run wizard
   prompt — sub-agent 1.5 territory).

5. **Rollback proof:** every v1.1 enforcement change shipped with explicit
   `CEO_ROLE_ENFORCEMENT=off` kill-switch env var (same precedent as
   `CEO_OVERHEAD_ACK=1` in PLAN-083 sub-agent 0.5). If enforcement
   misbehaves, Owner sets the kill-switch and continues working while
   the bug is fixed.

## 7. Threat model excerpt (representative misuse mitigated by this model)

Five scenarios this model would catch once v1.1 enforcement is live:

| # | Scenario                                                                 | Mitigated by                                |
|---|--------------------------------------------------------------------------|---------------------------------------------|
| T1 | Junior pastes an API key into a SKILL.md "examples" section while editing | `junior` denied Edit on `core/**/SKILL.md` (row 1); change forced through PR where secret-scanning gate catches it |
| T2 | Service account (compromised CI) tries to push a tag to bypass release ceremony | `service` denied sentinel signing (row 3); GPG key is on Owner's machine, not in CI; tag push requires owner |
| T3 | Senior engineer self-approves their own PR and lands a hook regression   | `senior` cannot self-approve (PR review enforces 1 required reviewer different from author); `owner` co-sign required for plan transitions |
| T4 | Junior runs `install.sh` against a production Acme repo without supervision | `junior` denied `install.sh` invocation (row 12); script refuses with instructions to escalate to senior/owner |
| T5 | Service account writes a malicious audit emit forging an `owner` action  | audit row includes signed `actor` field (v1.1 schema); HMAC chain + replay-test catches forgery; role label is descriptive, not authoritative |

## 8. Open design questions (resolved deliberately ambiguous for v1.0)

- **What if a single human plays two roles in different repos** (e.g. `owner`
  on adopter-1 + `senior` on a friend's repo where they help part-time)?
  → Deferred. v1.0 assumes one role per identity. v1.1 will support
  per-repo role via `actor_repo` field, but the mapping infrastructure
  (e.g. `~/.claude/identity.json`) is out of scope.

- **Should `senior` be able to read another user's memory directory** (e.g.
  `~/.claude/projects/<other-user>/memory/`)? → Deferred. Memory namespacing
  is its own v1.1 deferral (PLAN-083 §4 row "Memory namespacing schema").
  Until then, memory is single-user.

- **What is the audit semantics of an action taken with `CEO_ROLE` unset**
  (after v1.1 enforcement is live)? → Documented above: defaults to `senior`,
  emits `role_inferred: true` flag in audit row so post-hoc analysis can
  distinguish explicit-claim from default-inferred role.

## 9. References

- PLAN-083 §4 (deferrals) + §5.3 row 1.4 (this sub-agent's mandate)
- PROTOCOL.md §Identity + §Spawn Protocol (existing CEO/Owner/Agent vocabulary)
- `.claude/team.md` §Roles & Responsibilities (archetype-level role concepts —
  CEO / VP / Staff / IC; this document is the **human-principal** layer above
  those archetypes)
- `_CANONICAL_GUARDS` list in `.claude/hooks/check_canonical_edit.py` (existing
  path-based enforcement that the role model layers on top of)
- `_lib/audit_emit.py` (target site for `actor` / `actor_repo` schema extension
  in v1.1)
- ADR-052 (VETO floor — orthogonal: VETO is about technical archetypes;
  role is about human principals)
- PLAN-081 GA `CEO_PAIR_RAIL_VERDICT_OPTIONAL` transition flag (precedent
  for the `CEO_ROLE_ENFORCEMENT=off` kill-switch in §6 step 5)

---

## 10. §native-floor — harness-native static permissions floor (PLAN-135 W1 S2)

> **STATUS: STAGED for the PLAN-135 W1 Owner ceremony** (`.claude/settings.json`
> is canonical-guarded; the change ships as idempotent jq merge fragments at
> `.claude/plans/PLAN-135/staged/w1/merges/20-s2-permissions.{jq,target}`
> (dogfood) and `21-s2-permissions-template.{jq,target}` (template
> `templates/settings/settings.base.json`) per Doctrine 2 dual-surface parity).
> Static verification runs TODAY:
> `python3 .claude/plans/PLAN-135/research/probe_permissions_floor.py` (exit 0).
> Native-deny RUNTIME behavior is **PENDING-LIVE** per Doctrine 3
> (verify-the-knob-routes) — the headless probe procedure is documented in
> that script's docstring (`--live`).

This section is a **different layer** from §§1–9: those design the future
human-principal role model (documentary, v1.1). This section documents the
**harness-native `permissions` block** adopted under PLAN-135 Doctrine 1 —
*native-under-rail, never native-instead-of-rail*. Today the entire
governance surface is the 39-hook rail (a single point of failure: one
`disableAllHooks` line, one hook crash, one fail-open infra bug). The native
floor is the static layer that survives those failure modes.

**Division of labor (rules = static, hooks = stateful):**

- **Rules = static.** Declarative deny/allow matched by the harness itself
  before any code runs. They survive `disableAllHooks`, hook crashes, the
  framework's deliberate fail-open infra posture, and `bypassPermissions`-class
  modes. They cannot reason about intent, plan state, sentinels, or sessions.
- **Hooks = stateful.** The 39-hook rail keeps owning intent: sentinel
  ceremonies, kill-switches, plan/debate state, HMAC audit chain, spawn
  governance. The floor never replaces a hook; any hook retirement requires
  the Doctrine-1 H4-style mapping table + Codex review + coverage evidence.

### 10.1 The S2 baseline rule set

`permissions.deny` (7 rules — Tool(specifier) syntax exactly as recorded in
the harvest pack: `Edit(PROTOCOL.md)`, `Bash(git push --force*)` glob-`*`
suffix):

| Rule | Why |
|---|---|
| `Bash(git push --force*)` | History destruction; pairs with the hook-side git-bypass guard (ADR-143 family). Matches `--force` and `--force-with-lease`. |
| `Edit(PROTOCOL.md)` / `Write(PROTOCOL.md)` | Governance contract — canonical-guarded; floor backs `check_canonical_edit.py`. |
| `Edit(.claude/settings.json)` / `Write(.claude/settings.json)` | The rail's own arming state (hook registry + this very floor) — self-protection. |
| `Edit(SPEC/**)` / `Write(SPEC/**)` | Published Compliance contract (28 schema files) — canonical-guarded. |

`permissions.allow` (9 rules — conservative read-only set, shape from the
`fewer-permission-prompts` scan): `Bash(git status*)`, `Bash(git log*)`,
`Bash(git diff*)`, `Bash(ls)`, `Bash(ls *)`, `Bash(grep *)`, `Bash(head *)`,
`Bash(tail *)`, `Bash(wc *)`. Per-entry justification lives in
`.claude/plans/PLAN-135/staged/w1/manifests/s2.md`. **Native `allow` only
suppresses the human permission prompt — it does NOT bypass the hook rail:**
PreToolUse hooks (`check_bash_safety.py` et al.) still evaluate every allowed
command, which is the compensating control for glob over-match (e.g. an
allowed prefix followed by `; rm -rf /` or a `> file` redirect is still
hook-gated).

The merge fragments are **idempotent array-unions**: existing
`permissions.deny`/`permissions.allow` entries (and any other `permissions`
keys) are preserved first in original order; only absent rules are appended;
a second application is a no-op.

### 10.2 Mandated coverage enumeration (normative — PLAN-135 W1 S2, debate R1)

The floor MUST be understood with these three limits, quoted from the plan
verbatim:

> (a) **coverage limits** — an Edit-deny does NOT cover Bash writes to the
> same path (those stay hook-owned, fail-open);
>
> (b) **observability** — native DENY decisions short-circuit BEFORE
> PreToolUse hooks, so the floor blocks WITHOUT an audit_log event; S3's
> resolved-settings check is the compensating visibility;
>
> (c) **`settings.local.json` is a tamper layer the git sentinels never see —
> the floor must be asserted on RESOLVED settings.**

Operational consequences:

- **(a)** `Edit(PROTOCOL.md)` does not stop `bash -c 'echo x >> PROTOCOL.md'`,
  `sed -i`, `tee`, heredocs, or `python3 -c` writers. Those channels remain
  owned by `check_bash_safety.py` / `check_bash_canonical_forensic.py` —
  which are deliberately **fail-open** on infra error (PLAN-091-followup
  S116). The floor narrows the SPOF; it does not eliminate the Bash write
  channel. The same applies to `MultiEdit`/`NotebookEdit`-class tools not
  enumerated in the deny rules — hook-owned.
- **(b)** A blocked `git push --force` leaves **no trace in
  `audit-log.jsonl`** because the deny fires before the PreToolUse rail.
  Forensics cannot rely on the audit chain to see floor activity. The
  compensating visibility is S3's resolved-settings tripwire (`/ceo-boot`
  Tier-S via `_lib/effective_config.py`): it asserts at every boot that the
  floor is present and intact in the RESOLVED config, so a missing/tampered
  floor is surfaced even though individual denials are silent.
- **(c)** `settings.local.json` (gitignored) can override or neutralize what
  the checked-in `.claude/settings.json` declares — and no GPG sentinel or
  git-side control ever sees it. Therefore neither CI nor a git diff can
  prove the floor is armed: **only a resolved-settings assertion (all layers
  merged, exactly what the harness will obey) counts as evidence.** This is
  the same honesty boundary recorded in
  `.claude/plans/PLAN-135/research/THREAT-MODEL-WORKSHEET.md` §2.

### 10.3 Verification status (Doctrine 3)

| Claim | Status | Evidence |
|---|---|---|
| Fragments valid, floor rules present, merge idempotent + preserving | **PASS (static)** | `probe_permissions_floor.py` (plain run; W1 Check line) |
| Native deny actually fires (and with which glob semantics: bare `*` vs `:*`) | **PENDING-LIVE** | `probe_permissions_floor.py --live` documented procedure; runs against a scratch install at/after the ceremony |
| Deny short-circuits before PreToolUse (claim b) | **PENDING-LIVE** | same procedure, step 3 (absence of hook traffic for denied call) |
| Floor asserted on RESOLVED settings (claim c) | Lands with **S3** (`_lib/effective_config.py` + `/ceo-boot` tripwire) | `test_ceo_boot_tamper_tripwires.py` (S3 unit) |

If the live probe shows the runtime requires the `Bash(cmd:*)` colon form
instead of the harvest-pack bare-glob form, BOTH fragments are amended in the
same ceremony and the probe re-run — the rule INTENT (this section) is the
contract; the matcher spelling is implementation.
