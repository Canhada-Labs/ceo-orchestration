# ADR-038: Session-graph continuity (derived-only, encrypted-at-rest)

**Status:** ACCEPTED
**Date:** 2026-04-14
**Sprint:** 11 (PLAN-011 Phase 11)
**Related:** ADR-001 (runtime state directory), ADR-005 (event stream v2),
ADR-015 (Reflexion v2 outcome loop), ADR-027 (unified state backend)

## Context

PLAN-011 phases execute over multiple Claude Code sessions. When a
session ends mid-plan, the next session lacks any compact, authoritative
reconstruction of "where we were": the CEO can `ls .claude/plans/` and
read the markdown, but an unstructured markdown read is expensive
(hundreds of lines per plan), brittle (plans drift while executing),
and leaves each session re-deriving the same state from raw audit
events.

Four designs considered before this ADR:

1. **Session graph as a primary source of truth** — a hand-authored
   JSON under `.claude/state/sessions.json` that each session updates
   with what it did. Rejected: consensus **M3** ("the graph projects;
   the audit log owns"). A session-written source of truth *always*
   drifts from the audit log over time and becomes a stale oracle.
2. **Audit-log-only scan at resume time** — no graph at all; each
   resume scans the full audit log from scratch. Rejected: O(N) over
   all history × every plan restart. Becomes painful once the log
   crosses ~100k events. A derived cache is the obvious optimization.
3. **Git-only reconstruction** — use `git log --follow` on the plan
   file as the sole recovery signal. Rejected: commit history doesn't
   capture debate rounds, veto triggers, or lesson outcomes. Half the
   signal lives in the audit log, not git.
4. **Derived graph = audit-log + git + plan-markdown projection**
   (chosen). Source-of-truth invariance preserved; caching makes
   retrieval cheap; encryption makes the cache safe to store.

PLAN-011 consensus **M3 (HIGH)**: "session graph strictly derived from
audit-log and git; no new source of truth; encrypted at rest with
30-day default retention". This ADR documents that contract.

## Decision drivers

- **Derived-only (M3)** — every field in the graph maps back to an
  audit-log action OR a git commit. No field is invented by the
  graph-building script.
- **Cheap resume** — reading a cached graph must be O(1) file reads,
  not O(N) audit-log scan. Fresh-graph rebuild runs on cache miss or
  `--rebuild`.
- **Plan-scoping** — one graph per `PLAN-NNN`. No cross-plan view
  (that's a different surface).
- **Encryption at rest (M3)** — graph contains plan-internal decision
  timelines (useful signal if breached: which sessions spawned which
  archetypes, when debate consensus landed). Encrypt with Owner key;
  fall back to plaintext with loud WARNING only when no key is
  available.
- **Short default retention (M3)** — 30 days. Long-window analytics
  ride on the raw audit log; the graph is not an archival tool.
- **Additive SPEC (S1/H10)** — v1.3.0-rc.1 minor bump. No contract
  breaks to any existing consumer.
- **Kill-switch (S4)** — `CEO_SOTA_DISABLE=1` disables `session-*`
  surfaces entirely.

## Options considered (summary)

| Option | Source of truth | Cache? | Encrypted? | Verdict |
|---|---|---|---|---|
| A — Hand-authored JSON | graph file | yes | no | rejected (M3 drift risk) |
| B — Audit-log only | audit log | no | n/a | rejected (scan cost) |
| C — Git only | git | no | n/a | rejected (half the signal) |
| D — Derived graph | audit log + git + plan md | yes | yes | **chosen** |

## Decision

### 1. Graph scope

One derived graph per `PLAN-NNN`. The graph is a JSON document whose
top-level fields are enumerated in `SPEC/v1/session-graph.schema.md`
and whose **reverse map** (field → audit-log action OR git artifact)
is normative in that SPEC.

### 2. Build entry point

`.claude/scripts/session-graph-build.py`

- `--plan PLAN-NNN` — build one graph.
- `--all-active` — iterate every plan whose frontmatter
  `status != done`.
- `--since <N>[s|m|h|d] | forever` — event window. Default 30d (M3).
- `--output <path>` — explicit destination; defaults to
  `$HOME/.claude/projects/<proj>/session-graphs/<plan>-<ts>.json.age`.
- `--encrypt` / `--no-encrypt` — encrypt default ON. Tool priority:
  `age` (with `~/.claude/age-recipient.txt`) > `gpg` (with
  `$CEO_GPG_FINGERPRINT`) > plaintext (WARNING to stderr).
- `CEO_SOTA_DISABLE=1` → no-op exit 0.

### 3. Resume entry point

`.claude/scripts/session-resume.py`

- `--plan PLAN-NNN` — required.
- `--json` — machine-readable mode.
- `--rebuild` — bypass cache.
- Cache lookup: pick the newest matching file; if mtime < 24h, attempt
  decryption; else rebuild in-memory via `build_graph()`.
- Decryption: `.age` via `age -d -i ~/.claude/age-identity.txt`;
  `.gpg` via `gpg --decrypt`. Plaintext passthrough. Failure to
  decrypt = fall back to rebuild.

### 4. Encryption

- **age** when `age` is on PATH AND
  `$CEO_AGE_RECIPIENT_FILE` (or `~/.claude/age-recipient.txt`) exists.
- **gpg** when `gpg` is on PATH AND `$CEO_GPG_FINGERPRINT` is set.
  Command: `gpg --batch --yes --trust-model always --encrypt
  --recipient "$CEO_GPG_FINGERPRINT" --output <path>`.
- Plaintext fallback: emit `WARNING: session-graph-build: no
  encryption key available (set CEO_GPG_FINGERPRINT or
  ~/.claude/age-recipient.txt); writing PLAINTEXT` and write the
  file as `.plain.json` (keeps extension discoverable).
- Key rotation: rotating the Owner's age/gpg key invalidates all
  existing graphs; run `session-graph-build --all-active` after
  rotation to repopulate, then `rm` the old files (retention
  policy will sweep them anyway).

### 5. Retention (30-day default, M3)

- `--since` defaults to 30d at build time (window is bounded).
- The graph files themselves are **not** auto-pruned by
  `session-graph-build.py`; they accumulate under
  `session-graphs/`. A future phase may add a companion
  `--prune-older-than` flag; for PLAN-011 that's out of scope.
  Owner-level cleanup is `rm $HOME/.claude/projects/<proj>/session-graphs/*`.
- `--keep <plan-id>` override: not implemented in Phase 11 (the
  `--since forever` flag covers the rare "keep everything for this
  plan" case by re-running the build without a window).

### 6. Reverse map (normative)

Every surfaced field maps to a source event. Excerpt (full table in
SPEC §Reverse map):

| Graph field | Source |
|---|---|
| `sessions[].session_id` | distinct `session_id` across any action |
| `sessions[].start_ts` / `end_ts` | min/max `ts` per `session_id` |
| `sessions[].spawn_count` | count of `action == "agent_spawn"` per session |
| `sessions[].debate_rounds` | distinct `round` across `action == "debate_event"` |
| `sessions[].source_event_refs` | `{action, ts}` tuple per event in the session (integrity check — reverse map is machine-verifiable) |
| `commits[]` | `git log --follow .claude/plans/PLAN-NNN-*.md` |
| `plan_status` | plan markdown frontmatter `status` |
| `plan_title` | plan markdown frontmatter `title` |
| `last_phase_status` | derived from plan markdown `## Phases` checkbox scan |
| `deferred[]` | plan markdown `## Deferred...` section bullets |
| `owner_actions[]` | plan markdown `## Owner action items` section bullets |

Consumers MUST NOT rely on fields outside this map (additive additions
are permitted under MINOR SPEC bumps).

### 7. Non-goals

- **Not a lesson-replay tool.** Lesson timelines belong to
  `lessons.py` + `emit_lesson_outcome`. The graph surfaces whether
  `lesson_*` events happened, not their content.
- **Not a cross-plan analytics tool.** Aggregations across plans ride
  on `audit-query.py`. The graph is per-plan only.
- **Not an audit replacement.** Deleting the graph is always safe;
  the audit log is the authority.
- **Not a writeback channel.** `/resume` never writes state; it only
  projects.

## Consequences

### Positive

- Session continuity is cheap (O(1) disk read when cached).
- Graph stale-ness is visually obvious (generated_at stamp in output).
- Encryption means the cache is safe to leave on disk indefinitely.
- Additive contract — no break to existing scripts, hooks, or
  schemas.
- Clear kill-switch for SotA surfaces.

### Negative

- **Derivation drift risk.** If audit-log events gain new semantic
  fields, the graph builder may miss them until updated. Mitigation:
  source_event_refs preserves the action set per session so a future
  `validate-graph-coverage.py` can detect gaps.
- **Encryption availability varies.** CI hosts may lack both `age`
  and `gpg`; the plaintext-fallback WARNING is loud but not fatal.
  CI jobs scanning session graphs SHOULD pass `--no-encrypt` to avoid
  the WARNING.
- **Retention is build-time only.** Old graph files accumulate on
  disk until Owner removes them. Acceptable at Phase 11 scope;
  follow-up phase may add periodic `--prune-older-than`.

### Neutral

- New env vars: `CEO_SESSION_GRAPH_DIR`, `CEO_PLANS_DIR`,
  `CEO_AGE_RECIPIENT_FILE`, `CEO_GPG_FINGERPRINT`. All optional;
  sensible defaults apply.

## Blast radius

**L2** — two new scripts (~550 + ~280 LOC), one new slash command,
one new SPEC file, one ADR. +24 tests. No existing hook modified. No
new env reading in existing modules.

**Reversibility:** HIGH. Every artifact is net-new. Rolling back = `rm
.claude/scripts/session-*.py .claude/scripts/tests/test_session_*.py
.claude/commands/resume.md .claude/adr/ADR-038*
SPEC/v1/session-graph.schema.md`.

## Transition timeline

| Milestone | When | Source |
|---|---|---|
| ADR accepted | 2026-04-14 (this commit) | ADR-038 |
| Phase 11 shipped | PLAN-011 Phase 11 | session-graph-build + resume |
| Cross-plan summary (future) | Sprint 12 if demand | TBD |
| Auto-prune on build (future) | Sprint 12 if backlog grows | TBD |

## References

- PLAN-011 §Phase 11
- PLAN-011 consensus §M3 (HIGH) — "derived-only, encrypted, 30d retention"
- PLAN-011 consensus §S1 / §H10 — additive v1.3.0-rc.1
- PLAN-011 consensus §S4 — `CEO_SOTA_DISABLE=1` kill-switch
- PLAN-011 consensus §M8 — `/resume` top-level exception
- ADR-001 — runtime state directory convention
- ADR-005 — event stream v2 (iter_events contract)
- ADR-015 — Reflexion v2 outcome loop (related derivation pattern)
- ADR-027 — unified state backend (complementary; session graph is
  derived while state_store is primary for scratchpad / proposals /
  index)
- SPEC/v1/session-graph.schema.md — normative schema
- `.claude/scripts/session-graph-build.py` — build entry point
- `.claude/scripts/session-resume.py` — resume projection
- `.claude/commands/resume.md` — slash command spec

## Enforcement commit

`1633231749f6` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
