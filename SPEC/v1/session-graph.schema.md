# SPEC v1 — session-graph.schema

> **Normative sources:**
> - `.claude/scripts/session-graph-build.py` (build entry point)
> - `.claude/scripts/session-resume.py` (projection entry point)
>
> **Spec version:** 1.0.0-rc.1 (PLAN-011 Phase 11, 2026-04-14)
> **Related ADR:** ADR-038 — Session-graph continuity
> **Kill-switch:** `CEO_SOTA_DISABLE=1` disables session-graph surfaces
> entirely.

## Summary (normative)

A per-plan derived view over `audit-log.jsonl` + `git log --follow
.claude/plans/PLAN-NNN-*.md` + plan markdown. Used to reconstruct
"where the CEO left off" when a session ends mid-plan.

The graph is **strictly derived**. Every field maps to a source event
via the reverse map below. The graph is NOT a new source of truth —
rebuilding from scratch at any time MUST produce an equivalent graph
(modulo the `generated_at` timestamp).

### Graph schema version

`schema_version: "1.0.0"` — bumped on any field addition/removal.

- Adding fields → MINOR bump (forward-compat; consumers tolerate
  unknown).
- Removing/renaming fields → MAJOR bump (forbidden within v1).

## Envelope

```
${CEO_SESSION_GRAPH_DIR:-$HOME/.claude/projects/<proj>/session-graphs}/
    <PLAN-NNN>-<YYYYMMDDTHHMMSSZ>.json.age   # default (age-encrypted)
    <PLAN-NNN>-<YYYYMMDDTHHMMSSZ>.json.gpg   # gpg alternative
    <PLAN-NNN>-<YYYYMMDDTHHMMSSZ>.json       # explicit --no-encrypt
    <PLAN-NNN>-<YYYYMMDDTHHMMSSZ>.plain.json # no key available fallback
```

Directory permissions: 0o700 (owner-only). File permissions: 0o600.

## Identifiers

| Field | Type | Rules |
|---|---|---|
| `plan_id` | string | matches `^PLAN-\d{3}$` |
| `session_id` | string | opaque; copied from `audit-log.jsonl` as-is |
| `schema_version` | string | semver, e.g. `"1.0.0"` |

## Top-level fields

```json
{
  "schema_version": "1.0.0",
  "plan_id": "PLAN-010",
  "generated_at": "2026-04-14T17:30:00Z",
  "window": {
    "since": "2026-03-15T17:30:00Z",
    "until": "2026-04-14T17:30:00Z"
  },
  "plan_status": "done",
  "plan_title": "Sprint 10 Polish",
  "last_phase_status": "Phase 8: done",
  "sessions": [ ... ],
  "session_count": 2,
  "event_count": 5,
  "commits": [ ... ],
  "commit_count": 9,
  "deferred": [ "Flip docs-freshness state 1→2", "..." ],
  "owner_actions": [ "Tag v1.0.0-rc.1" ],
  "source_plan_file": ".claude/plans/PLAN-010-sprint-9-10-quality-polish.md"
}
```

### Session record

```json
{
  "session_id": "sess-A",
  "start_ts": "2026-04-14T15:00:00Z",
  "end_ts":   "2026-04-14T16:30:00Z",
  "spawn_count": 3,
  "debate_rounds": [1],
  "event_count": 5,
  "action_counts": {
    "agent_spawn": 3,
    "debate_event": 2
  },
  "source_event_refs": [
    {"action": "agent_spawn",  "ts": "2026-04-14T15:00:00Z"},
    {"action": "debate_event", "ts": "2026-04-14T15:15:00Z"}
  ]
}
```

### Commit record

```json
{
  "sha": "abc1234567890",
  "author_ts": 1713115200,
  "subject": "PLAN-010 Phase 8 closeout"
}
```

## Reverse map (normative)

Every graph field SHALL have a traceable derivation. Consumers MAY
check compliance programmatically: no value in the graph is accepted
unless its derivation step is listed below.

| Graph field | Source |
|---|---|
| `schema_version` | static constant in `session-graph-build.py` |
| `plan_id` | CLI arg |
| `generated_at` | `datetime.now(UTC)` at build time |
| `window.since` / `window.until` | `generated_at - since` / `generated_at` |
| `plan_status` | plan markdown frontmatter `status:` |
| `plan_title` | plan markdown frontmatter `title:` |
| `last_phase_status` | plan markdown — scan of `## Phases` checkboxes |
| `sessions[].session_id` | distinct `session_id` across audit-log events for the plan |
| `sessions[].start_ts` | min `ts` per session |
| `sessions[].end_ts` | max `ts` per session |
| `sessions[].event_count` | count of events per session |
| `sessions[].action_counts` | grouping count per action within the session |
| `sessions[].spawn_count` | count of `action == "agent_spawn"` within the session |
| `sessions[].debate_rounds` | distinct `round` values across `action == "debate_event"` within the session |
| `sessions[].source_event_refs` | `{action, ts}` tuple for every event in the session (integrity check — enables auditing that the graph did not synthesize) |
| `session_count` | `len(sessions)` |
| `event_count` | sum of per-session event counts |
| `commits[]` | `git log --follow --pretty=... -- .claude/plans/PLAN-NNN-*.md`, newest first |
| `commit_count` | `len(commits)` |
| `deferred[]` | plan markdown `## Deferred...` section bullets |
| `owner_actions[]` | plan markdown `## Owner action items` section bullets |
| `source_plan_file` | relative path of the plan file (or absolute if outside repo) |

Consumers:

- **MAY** build derived views (e.g. "spawn rate per session") from
  these fields.
- **MUST** tolerate unknown fields (forward-compat).
- **MUST NOT** expect any field beyond those in this table to exist
  until a MINOR spec bump adds it explicitly.

## Retention

- **Build-window default:** 30 days (M3 consensus — session graph is
  not an archival tool; long-window analytics ride on raw audit log).
  Override via `--since forever` or `--since <N>[s|m|h|d]`.
- **On-disk retention:** unbounded at this SPEC version. Graph files
  accumulate under `session-graphs/` until Owner cleanup. A follow-up
  spec MAY add `--prune-older-than`; not in scope for 1.0.0-rc.1.

## Encryption

- **Tool priority:** `age` > `gpg` > plaintext WARNING fallback.
- **age** — `age -r <recipient> -o <out>` where recipient is the
  first line of `${CEO_AGE_RECIPIENT_FILE:-$HOME/.claude/age-recipient.txt}`.
- **gpg** — `gpg --batch --yes --trust-model always --encrypt
  --recipient "$CEO_GPG_FINGERPRINT" --output <out>`.
- **Plaintext fallback** — emit `WARNING: session-graph-build: no
  encryption key available (set CEO_GPG_FINGERPRINT or
  ~/.claude/age-recipient.txt); writing PLAINTEXT` on stderr and
  write to `<out>.plain.json`. Never block.
- **Decryption (session-resume):** `age -d -i
  ~/.claude/age-identity.txt <file>` or `gpg --decrypt <file>`.
  Plaintext passes through. Decryption failure → fall through to
  in-memory rebuild.
- **Key rotation:** rotating the Owner key invalidates existing
  graphs. Run `session-graph-build --all-active` after rotation
  (build is cheap) and `rm` the old files manually.

## Freshness window (session-resume)

- `session-resume.py` reuses a cached graph when its mtime is < 24h.
- Older than 24h → rebuild in-memory before projecting.
- `--rebuild` forces rebuild regardless of mtime.

## Idempotency

Running `session-resume.py --plan PLAN-NNN` twice back-to-back MUST
produce output that is byte-identical modulo:

- `generated_at` in the underlying graph
- `source` label (`disk:<name>` vs `live`)

No audit events are emitted by `session-resume.py`. No state is
written by `session-resume.py`. Both conditions are asserted by the
unit test suite.

## Kill-switch

If `CEO_SOTA_DISABLE=1` is set, both `session-graph-build.py` and
`session-resume.py` short-circuit at `main()` entry and exit 0 with no
output (no file writes, no stderr).

This matches the SotA-feature disable pattern used across PLAN-011
Phase-gated features and is enforced by unit tests.

## Fail mode

- Invalid `--plan` (regex mismatch) → exit 2 + stderr.
- Missing plan file in `session-resume.py` → exit 3 + user-friendly
  message (no traceback).
- Missing audit log → graph has `event_count: 0` and
  `sessions: []`; exit 0 (no error).
- git not on PATH → `commits: []`, `commit_count: 0`; exit 0.
- Encryption tool missing + no fallback key → plaintext with WARNING.
- Decryption failure in resume → fall through to in-memory rebuild.

## Consumer contract

Consumers (admin tools, future dashboards) SHOULD:

- Check `schema_version` before parsing; ignore graphs with a MAJOR
  version beyond what they support.
- Treat `sessions[].source_event_refs` as an integrity manifest — a
  well-formed graph has at least one ref per session.
- Tolerate missing optional fields (forward-compat); hard-code only on
  the reverse-map fields.
- Treat any field NOT in the reverse map as opaque unless a later
  MINOR bump adds it.

Consumers MUST NOT:

- Rely on the graph for fields the reverse map doesn't cover.
- Treat the graph as primary (audit-log is authority).
- Distribute graphs across users — they are keyed to one Owner's
  encryption material.

## Version history

| SPEC version | Source commit | Notes |
|---|---|---|
| 1.0.0-rc.1 | PLAN-011 Phase 11 | Initial envelope + reverse map + encryption policy |
