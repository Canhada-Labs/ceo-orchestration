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

## Enforcement commit

`b7aef7ede65d` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
