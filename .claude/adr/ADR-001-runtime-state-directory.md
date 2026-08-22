# ADR-001: Runtime state directory convention

**Status:** ACCEPTED (retroactive — decision was made in Sprint 1)
**Date:** 2026-04-11 (documented retroactively during Sprint 2 A+G)
**Decision drivers:** prevent secret leakage via git, align with Claude Code native memory, single canonical location.

## Context

Sprint 1's PostToolUse audit log hook (`audit-log.sh`, now
`audit_log.py`) needs to write one JSONL row per Agent spawn. Task
descriptions from a Claude Code session routinely contain secrets
(API keys, JWTs, DB URLs with credentials, pasted PII). The hook also
needs a place to drop error breadcrumbs (`audit-log.errors`) and, in
Sprint 2+, a place for rotated log files and benchmark results.

The question was: **where should this state live?**

Sprint 2+ amplifies the stakes: several additional subsystems
(benchmarks, debate transcripts, Sprint 3 Reflexion lessons) will need
similar persistence. A single answer now avoids three divergent answers
later.

## Decision drivers

- **Secret exposure surface.** A `.gitignore` entry does not defend
  against `git add -f`, `git stash -u`, `git archive`, developer
  backups, indexed filesystem search, or IDE workspace-save files.
- **Alignment with Claude Code native memory.** Claude Code already
  uses `$HOME/.claude/projects/<project-slug>/` for its own memory
  persistence. Reusing this location avoids a second, orthogonal
  convention.
- **Per-developer isolation.** Different developers on the same repo
  should see different audit logs (one log per local session, not a
  shared log in the repo).
- **Onboarding cost.** The location must be discoverable from the
  code and documented in at most one place.

## Options considered

### Option A: In-repo under `.claude/runtime/` with `.gitignore`

- (-) `.gitignore` is insufficient against `-f` / `stash` / `archive`
- (-) Git-indexed search still finds the file
- (-) IDE workspace-save snapshots can capture it
- (+) Simple mental model ("everything is in the repo")
- (+) Easy cleanup (`rm -rf .claude/runtime/`)

**Rejected** — the secret exposure surface is too large. A single
accidentally-committed audit entry with a pasted API key is a
production incident, not a nuisance.

### Option B: System temp (`/tmp/ceo-orchestration/`)

- (+) Zero git exposure
- (-) Non-persistent (cleared on reboot on most systems)
- (-) Not discoverable — "where does the audit log live" requires a
  grep through shell scripts
- (-) Doesn't align with any existing Claude Code convention

**Rejected** — persistence is required for cross-session analytics.

### Option C: `$HOME/.claude/projects/<project>/` (CHOSEN)

- (+) Aligns with Claude Code's native memory location
- (+) Per-user, per-project isolation
- (+) Persistent across reboots
- (+) Overridable via `CEO_AUDIT_LOG_DIR` env var for tests and
  custom layouts
- (+) One canonical location for every runtime artifact
- (-) State is per-developer, not shared — a team setup would need
  an explicit sync mechanism
- (-) Onboarding doc must point at the out-of-repo location
- (-) `CLAUDE_PROJECT_DIR_NATIVE` semantics are implicit; we may
  need a formal env var in Sprint 3

## Decision

**All ephemeral runtime state lives under
`${CLAUDE_PROJECT_DIR_NATIVE:-$HOME/.claude/projects/<project-slug>}/`.**

Never under `.claude/` inside the repo tree. Env var overrides:

- `CEO_AUDIT_LOG_DIR` — parent directory (defaults to the above)
- `CEO_AUDIT_LOG_PATH` — log file path
- `CEO_AUDIT_LOG_ERR` — errors file path
- `CEO_AUDIT_LOG_LOCK` — lock file path (Sprint 2: `audit-log.lock`)
- `CEO_AUDIT_LOG_ROTATE_BYTES` — rotation threshold (Sprint 2)

Subdirectories (Sprint 2+):

- `audit-log.jsonl` + rotated `audit-log-YYYY-MM.jsonl` siblings
- `audit-log.errors`
- `benchmark-runs/` — Sprint 2 Item C
- `debate-transcripts/` — if Sprint 3 multi-round debates need disk state
- `lessons/` — Sprint 3 Reflexion loop

## Consequences

- (+) **No git-leak** — the class of accidental-commit secret leakage is
  eliminated at the file system level, not at the git level.
- (+) **Native alignment** — the location matches Claude Code's own
  memory convention, so the mental model extends naturally.
- (+) **Testable** — every state-writing component can point at an
  isolated temp dir via the env vars (`TestEnvContext` in
  `_lib/testing.py` does exactly this).
- (-) **Per-developer** — no shared view across machines. Acceptable
  for Sprint 2 (single-owner framework). A team installation would
  add explicit sync (Sprint 4+ if ever).
- (-) **Onboarding doc cost** — every README must mention the location
  so new contributors can find their logs. Mitigated by a single
  sentence in `INSTALL.md` and the `AUDIT-LOG-SCHEMA.md` §1 section.
- (~) **The `<project-slug>` derivation is implicit** — Claude Code
  uses a path-based slug (e.g. `-Users-<user>-ceo-orchestration`).
  The audit log uses the bare project name. Both work; Sprint 3 may
  align them if it simplifies things.

## Blast radius

**L2** — touches every state-writing hook/script. In Sprint 1 that was
one file (`audit-log.sh`); in Sprint 2 it's three (`audit_log.py`,
`audit-query.py`, `run-skill-benchmark.py`); in Sprint 3 it will be
five. The decision scales.

## Related commits

- `e1cd24e` (Sprint 1 item 2) — hardened audit log with this location
- `22144c4` (Sprint 2 A.3) — Python port inherits the convention
- `dcaa94e` (Sprint 2 A.5) — E2E + latency tests use the convention
  via `TestEnvContext` env var isolation

## Amendment (2026-04-14) — Sprint 10 backup path

PLAN-010 Phase 6 (debate C9 + VPE #6) adds one reserved subdirectory
under the runtime state directory:

- `backups/` — gzipped daily snapshots of `audit-log.jsonl`.
  Filenames: `audit-YYYY-MM-DD.jsonl.gz` (UTC date; DST-safe).

### Defaults

- `--keep-days` = 30 — delete snapshots older than 30 days.
- `--max-total-bytes` = 500_000_000 (500 MB) — size cap on the backup
  directory; when exceeded, evict oldest snapshots first. The single
  newest snapshot is always preserved.

### Why

The audit log grows monotonically and already contains
redaction-scrubbed descriptions. Having dated snapshots separate from
the live log enables (a) cheap rollback of a corrupt write,
(b) offline analytics without risking the live file,
(c) predictable bounded disk use. Debate C9 flagged race with live
`audit_log.py` writers as HIGH — resolved by using the same
`_lib/filelock.py` primitive the writer uses.

### Env overrides

- `--audit-dir` and `--backup-dir` flags on `backup-audit.py` override
  the defaults for tests and multi-project setups. No new env vars
  are introduced — we stay at the set defined in the original ADR.

## Amendment (2026-08-20, S318 — PLAN-182 AC-7) — the slug becomes normative; the family moves together

**Trigger (measured, not hypothetical — PLAN-182 W0, S315..S317):** this
ADR was ACCEPTED on 2026-04-11 specifying `<project-slug>`, and for four
months the runtime resolved, absent env overrides, to the LITERAL
`$HOME/.claude/projects/ceo-orchestration` instead. The behaviorally
derived family is **587 files** (562 in cure scope; 102 runtime modules
BUILD the literal rather than loading it — `derive-audit-family.py`,
PLAN-182 W0-US1). The env var this ADR's Decision names,
`CLAUDE_PROJECT_DIR_NATIVE`, is consumed by **zero** files. Measured
consequence: this repo's audit log carries events from **two** foreign
projects (2,136 + 1,706 rows) under **one** shared HMAC key, and the
single per-`$HOME` `.salt` makes `prompt_sha256` correlate across
projects — the ADR-079 guarantee is already false at the tenancy
boundary. The W0 artifact×env matrix (19 anchors × 14 columns, 266
cells; env domain = 21 code-derived vars) additionally measured that
`CEO_AUDIT_LOG_PATH` moves the log AND the `audit-key` but leaves the
**lock** and **errors** behind — two projects with distinct logs still
serialize on one lock.

**Decision (amends the Decision section; implemented by PLAN-182 W1):**

1. **`<project-slug>` derivation becomes NORMATIVE and native-aligned:**
   the slug is the Claude Code path-based slug of the project's absolute
   path (`/` replaced by `-`, e.g. `-Users-<user>-<path>-<repo>`) — the
   SAME derivation Claude Code uses for `~/.claude/projects/<slug>/`
   memory. The original "(~) derivation is implicit … Sprint 3 may align
   them" note is hereby resolved in favor of the native slug: the bare
   project name (the literal the code grew) COLLIDES for two checkouts
   sharing a basename and is what produced the measured cross-tenant
   mixing; the path-based slug cannot collide without the paths
   colliding.
2. **One resolver, imported by the whole family.** A single module owns
   the derivation; no file in the family may re-derive the directory
   locally (the ownership-verdict lesson: a locally-deciding branch
   re-opens the class this closes). `CLAUDE_PROJECT_DIR_NATIVE` stays
   the documented whole-directory override and MUST be consumed by that
   resolver — an override with zero consumers is a spec fiction, which
   is what this amendment repairs.
3. **Family-atomicity invariant:** `audit-log.jsonl`, `audit-key`,
   `audit-log.lock`, `audit-log.errors`, `.salt`, rotation siblings,
   `backups/` and every sidecar resolve from the SAME base directory in
   every configuration. Per-file env overrides (`CEO_AUDIT_LOG_PATH`,
   `_ERR`, `_LOCK`) keep working for tests, but no supported
   configuration may split the lock or errors from the log they guard
   (the measured `CEO_AUDIT_LOG_PATH` split above is a DEFECT, cured in
   W1, not a feature).
4. **Blast radius reclassified L2 → L3.** The migration of live state
   (historical log, HMAC key, salt) is a ceremony of its own (PLAN-182
   W1/W2, Owner-signed), with the historical-log custody decision made
   BEFORE writers move (W2 precedes the W1 re-emission).

**Honest limit (unchanged by this amendment):** per-project directories
and keys end ACCIDENTAL mixing — chains that do not interleave, correct
attribution, `verify_chain()` meaningful per project. They do NOT
restore tamper-evidence between tenants of the same UID: a process on
the same UID reads the other project's `0700` dir and `0600` key. That
boundary would require a separate UID or keys outside process reach —
out of scope, declared PERMANENT under same-UID in `CLAUDE.md` §5.

**Authorization:** direction ratified by the Owner via AskUserQuestion
(S318, 2026-08-20): "Ratificar direção (Recomendado) — ADR-001:
derivação por slug como escrito". This amendment UNBLOCKS PLAN-182 W1
(frontmatter `blocked_on_adr`); the implementation lands under the W1
ceremony, not under this text.

## Amendment 2 (2026-08-22, S321 — PLAN-182 AC-7, a peça que faltava)

**Decision: amend `SPEC/v1` IN PLACE; do NOT cut a `SPEC/v2`.**

The AC-7 of PLAN-182 named this decision explicitly ("with the SPEC v1
vs v2 decision"), and Amendment 1 covered the other three quarters —
normative slug, single resolver, family-atomicity, blast radius L2→L3 —
but never recorded this one. Meanwhile the decision had already been
*taken in practice*: `SPEC/v1/audit-log.schema.md` and
`SPEC/v1/state-stores.schema.md` were edited in place under the W1
ceremony (`v2.58`), and `SPEC/` still holds a single `v1/` directory.
An unrecorded decision is one a future maintainer re-litigates from
scratch, which is what an ADR exists to prevent.

**Why in-place is not a v1 contract break.** The published contract is
about the *shape and integrity* of the audit record — event schema,
HMAC chaining, field allowlists — not about which filesystem path the
implementation writes to. `SPEC/v1` already expressed the location as a
**parameterized** expression
(`${CEO_AUDIT_LOG_PATH:-$HOME/.claude/projects/<slug>/audit-log.jsonl}`),
and the W1 change replaced the *default value* of that parameter, not
the parameter. No consumer field changed name, type, or meaning; no
event was added or removed by the move itself; `verify_chain()` keeps
the same semantics and becomes MORE meaningful, not less, because the
chain it verifies is now single-tenant.

**What WOULD have required a v2**, recorded so the line is testable and
not a matter of taste: renaming or retyping a consumer-visible field;
changing the HMAC construction or the chain-link rule; removing an
action from the closed set; or altering the meaning of an existing
field. The one field whose *meaning* is adjacent to this change,
`project`, was already specified as the absolute project path — and the
S321 work fixed emitters that were leaving it EMPTY, which moves the
implementation toward the spec rather than away from it.

**Consequence for adopters.** An adopter upgrading across this change
sees runtime state resolve to a new per-project directory. That is a
migration concern (PLAN-182 W3), not a contract-version concern: the
schema an adopter validates against is unchanged, so their conformance
tooling keeps passing. Custody of the pre-W1 chain is the W2 decision
(ARCHIVE), recorded in the W1 sentinel.

**Scope of this amendment:** it records a decision already executed. It
authorizes nothing new and changes no file.

## Enforcement commit

`b7aef7ede65d` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
