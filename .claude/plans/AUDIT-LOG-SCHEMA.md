---
id: AUDIT-LOG-SCHEMA
title: Agent Spawn Audit Log — Schema & Operational Contract
status: accepted
created: 2026-04-11
owner: CEO
depends_on: [PLAN-001]
---

# Agent Spawn Audit Log — Schema & Operational Contract

> This document is the source of truth for the `agent_spawn` event schema
> emitted by the PostToolUse hook at `.claude/hooks/audit_log.py` (Python
> single-file, migrated from `.claude/scripts/audit-log.sh` in Sprint 2
> A.3). The bash version lives at `.claude/hooks/legacy/audit-log.sh` as
> a fallback until Sprint 3 removes it. The schema is identical except
> for the new `hook_duration_ms` field added in Sprint 2.
>
> This is the contract between the hook (producer) and any downstream
> consumer (audit-query.py CLI, Reflexion in Sprint 3, dashboards,
> incident response).

## 1. Location and ownership

**Log path (out-of-repo by design):**

```
${CEO_AUDIT_LOG_PATH:-$HOME/.claude/projects/ceo-orchestration/audit-log.jsonl}
```

**Errors log:**

```
${CEO_AUDIT_LOG_ERR:-$HOME/.claude/projects/ceo-orchestration/audit-log.errors}
```

**Rationale for out-of-repo:**

Task descriptions routinely contain secrets, PII, and internal URLs. A
`.gitignore` entry would defend only against `git add` — not against
`git add -f`, `git stash -u`, `git archive`, developer backups, indexed
file search, or IDE workspace-save. Storing the log outside the repo tree
aligns with Claude Code's native memory location and eliminates the
entire class of accidental-commit leakage.

**File permissions:**

- Directory: `700` (owner read/write/exec only)
- Log file: `600` (owner read/write only)
- Both are set by the hook on first creation.

## 2. Schema (one JSON object per line — JSONL)

Every successful hook invocation appends exactly one line with the
following fields. Field order is stable; consumers should tolerate
additional fields (forward-compat).

```json
{
  "ts":                  "2026-04-11T13:15:47Z",
  "action":              "agent_spawn",
  "session_id":          "<Claude-Code-session-id>",
  "project":             "<canonical project path>",
  "tool":                "Agent",
  "subagent_type":       "<general-purpose | custom agent type | empty>",
  "desc_preview":        "<redacted, whitespace-collapsed, ≤120 chars>",
  "desc_hash":           "<hex SHA-256 of the raw description, pre-redaction>",
  "skill":               "<first SKILL: <name> match in the prompt, or 'unknown'>",
  "has_profile":         true,
  "has_file_assignment": true,
  "prompt_len_bucket":   "<256 | <1024 | <4096 | <16384 | <65536 | >=65536",
  "response_kind":       "text | object | string | absent",
  "hook_duration_ms":    12
}
```

**Sprint 2 addition:** `hook_duration_ms` (integer) — wallclock duration
of the hook itself in milliseconds. Set by the Python hook via
`time.monotonic()`. Enables `audit-query.py stats --latency` analysis
without re-instrumenting. Pre-Sprint-2 log entries (written by the bash
version) omit this field; consumers should tolerate its absence.

### Field definitions

| Field | Type | Notes |
|---|---|---|
| `ts` | string (ISO 8601 UTC) | `YYYY-MM-DDTHH:MM:SSZ`, second-precision. |
| `action` | string literal `"agent_spawn"` | Reserved for future action types (e.g. `skill_load`, `plan_transition`). |
| `session_id` | string | From `tool_input.session_id` via Claude Code. Empty if unavailable. |
| `project` | string | Canonicalized (`pwd -P`) project directory. |
| `tool` | string | Should always be `"Agent"` when this event fires; guarded with `"unknown"` fallback. |
| `subagent_type` | string | From `tool_input.subagent_type` (e.g. `general-purpose`, `Explore`, `Plan`). |
| `desc_preview` | string | Human description of the spawn, **after** secret redaction, truncated to 120 chars. Use this for at-a-glance scan of the log. |
| `desc_hash` | string | `sha256(raw_description)` in lowercase hex. Use this for dedup and correlation without storing plaintext. Will differ if the raw description changes in any way. |
| `skill` | string | Extracted from the prompt via `^SKILL:\s+<name>` regex. `"unknown"` if no skill marker found (governance warning — every named spawn should carry a skill). |
| `has_profile` | boolean | `true` if the prompt contains a `## AGENT PROFILE` / `## PERSONA` / `PERSONA:` header. Governance signal: compliant spawns set this to true. |
| `has_file_assignment` | boolean | `true` if the prompt contains a `## FILE ASSIGNMENT` section. Governance signal: mandatory for spawns that edit files. |
| `prompt_len_bucket` | string | Bucketed size of the full prompt. Buckets: `<256`, `<1024`, `<4096`, `<16384`, `<65536`, `>=65536`. Exact lengths are a side channel; buckets preserve the signal with less precision. |
| `response_kind` | string | Shape of `tool_response` in the hook payload. `text` / `object` / `string` / `absent`. Indicates whether the sub-agent returned anything. |

## 3. Secret redaction contract

The `desc_preview` field is passed through a Python regex pass **before**
truncation. The following patterns are redacted. If a new secret format
appears, add its pattern here AND to `audit-log.sh`'s `redact_secrets()`.

| Pattern | Placeholder |
|---|---|
| `eyJ<...>.<...>.<...>` (JWT) | `[JWT]` |
| `\bsk-[A-Za-z0-9]{20,}\b` (OpenAI-style) | `[API_KEY]` |
| `\bghp_[A-Za-z0-9]{20,}\b` (GitHub PAT) | `[GITHUB_PAT]` |
| `\bAKIA[0-9A-Z]{16}\b` (AWS access key) | `[AWS_KEY]` |
| `\b[Bb]earer\s+[A-Za-z0-9._-]+` | `Bearer [TOKEN]` |
| `\b[A-Fa-f0-9]{32,}\b` (hex ≥32) | `[HEX_SECRET]` |
| `[a-z]+://[^\s:@/]+:[^\s@]+@[^\s]+` (URL with creds) | `[URL_WITH_CREDS]` |
| `(?i)(password\|passwd\|pwd\|secret\|token\|api[_-]?key)\s*[=:]\s*\S+` | `\1=[REDACTED]` |

**Redaction is best-effort, not a guarantee.** The `desc_hash` lets you
correlate entries that may share the same unredacted text without storing
that text.

## 4. Concurrency and durability

- **Lock primitive (Sprint 2):** `fcntl.flock` exclusive lock on a sibling
  `audit-log.lock` file, via `.claude/hooks/_lib/filelock.py`. The lock is
  process-scoped (kernel releases on process exit, so no stale-directory
  cleanup is needed). The legacy bash version used `mkdir` directory locks
  as a POSIX-atomic primitive without `flock` dependency.
- **Lock acquisition:** up to 2.5s (50 × 50ms) retry before giving up.
- **Append:** single write under lock.
- **Failure mode:** fail-open. If the hook cannot write the entry, it writes
  a breadcrumb to `audit-log.errors` and exits 0 so the user's session
  continues. The hook MUST NOT block the session.
- **Sprint 2 rotation:** on each write, if `audit-log.jsonl` exceeds
  `CEO_AUDIT_LOG_ROTATE_BYTES` (default 10 MB), the file is renamed to
  `audit-log-YYYY-MM.jsonl` (UTC month). Collision handling adds `-1`,
  `-2`, etc. Rotation happens UNDER the lock so no writer races past a
  rename. Pre-Sprint-2 logs had no rotation.

## 5. Hook composition contract

The PostToolUse Agent matcher has **two hooks** (as of Sprint 2 A.4):

1. **`audit_log.py`** (this script) — silent observer. Exits 0, emits NOTHING to stdout. Writes to the JSONL file under lock. Invoked via `_python-hook.sh` shim.
2. **File-assignment reminder hook** — emits `{"decision":"allow","message":"POST-AGENT: Check git diff..."}`.

Only the reminder hook produces a JSON decision. `audit_log.py` is composable because it never speaks on stdout. If you add a third hook, it MUST either be silent or coordinate with the reminder on decision merging.

## 6. Log rotation

**Sprint 2 implementation (current):** rotate by size. When the active
`audit-log.jsonl` exceeds `CEO_AUDIT_LOG_ROTATE_BYTES` (default
`10485760` = 10 MB), it is renamed to `audit-log-YYYY-MM.jsonl` (UTC month)
inside the lock. A subsequent rotation in the same month becomes
`audit-log-YYYY-MM-1.jsonl`, `-2.jsonl`, etc. A fresh empty
`audit-log.jsonl` is created by the next append.

Consumers: the `audit-query.py` CLI accepts `--include-rotated` to
aggregate across all files matching `audit-log*.jsonl` in the audit dir.

## 7. Query examples (for operators)

```bash
# Count spawns today
jq -r 'select(.ts | startswith("2026-04-11"))' \
  ~/.claude/projects/ceo-orchestration/audit-log.jsonl | wc -l

# Most-used skills this week
jq -r '.skill' ~/.claude/projects/ceo-orchestration/audit-log.jsonl \
  | sort | uniq -c | sort -rn

# Spawns missing governance compliance (no persona OR no file assignment)
jq -c 'select(.has_profile == false or .has_file_assignment == false)' \
  ~/.claude/projects/ceo-orchestration/audit-log.jsonl

# Prompt-size distribution
jq -r '.prompt_len_bucket' ~/.claude/projects/ceo-orchestration/audit-log.jsonl \
  | sort | uniq -c

# Find a previous spawn by its description hash (without knowing plaintext)
jq -c 'select(.desc_hash == "aa7c34203cacad7ff53388f8d1a8ac4ffdf7b5352b02b9cdb561e846dc594c42")' \
  ~/.claude/projects/ceo-orchestration/audit-log.jsonl
```

## 8. Environment variable overrides

| Variable | Default | Purpose |
|---|---|---|
| `CEO_AUDIT_LOG_DIR` | `$HOME/.claude/projects/ceo-orchestration` | Parent directory. |
| `CEO_AUDIT_LOG_PATH` | `$CEO_AUDIT_LOG_DIR/audit-log.jsonl` | Log file. |
| `CEO_AUDIT_LOG_ERR` | `$CEO_AUDIT_LOG_DIR/audit-log.errors` | Errors log. |
| `CEO_AUDIT_LOG_LOCK` | `$CEO_AUDIT_LOG_DIR/audit-log.lock` | Lock file (Sprint 2: fcntl.flock). |
| `CEO_AUDIT_LOG_ROTATE_BYTES` | `10485760` (10 MB) | Rotation threshold. |
| `CLAUDE_PROJECT_DIR` | `pwd` (fallback) | Project path for the `project` field. |

## 9. What this log is NOT

- **Not a security audit trail.** Treat it as observability, not forensic evidence. It is best-effort, locally scoped, and unsigned.
- **Not session transcripts.** Only spawn events, not the full conversation.
- **Not a replacement for structured logging in target projects.** This log is about the framework meta-layer (which specialist did what), not about the target project's runtime.
- **Not synced between machines.** One developer → one log.

## 11. Event stream v2 (PLAN-004 Phase 1, ADR-005)

Sprint 4 promotes this log to a **typed event stream**. The existing
v1 `action: "agent_spawn"` schema (§2 above) is **unchanged and
preserved**. Five new `action` values are added, each with
`event_schema: "v2"` as discriminator:

| action | producer | required fields |
|---|---|---|
| `debate_event` | `/debate` command / `_lib.audit_emit.emit_debate_event` | `plan_id`, `round`, `phase`, `agent` |
| `plan_transition` | `check_plan_edit.py` on legal status change | `plan_id`, `from_status`, `to_status`, `file_path`, `transition_legal` |
| `veto_triggered` | any governance hook on block path | `hook`, `reason_code`, `reason_preview` (redacted ≤120), `blocked_tool` |
| `benchmark_run` | `run-skill-benchmark.py` on completion | `benchmark_id`, `skill`, `pass_count`, `fail_count`, `pass_rate`, `median_score`, `floor` |
| `lesson_write` | `lessons.py` on corpus append | `lesson_id`, `archetype`, `scope_tags[]`, `trigger`, `source_event_id` |
| `injection_flag` (v2.1) | `check_read_injection.py` / `scan-injection.py` | `source`, `family_counts{}`, `match_count`, `bytes_scanned`, `truncated`, `triggered_by_tool` (ADR-011) |

All v2 events reserve nullable `tokens_in`, `tokens_out`, `tokens_total`
fields (AI specialist P5; writer deferred to Sprint 6). Consumers MUST
tolerate these being `null` in v2 entries.

### v1 detection

Absence of the `event_schema` field marks a v1 entry (always
`action: "agent_spawn"`). v2 entries always carry `event_schema: "v2"`.

### Rotation (ADR-005)

Unchanged from §6 above: 10 MB threshold or 30 days whichever first,
archived as `audit-log-YYYY-MM.jsonl`. Rotation shared across v1 and
v2 entries.

### Consumer API

```python
from _lib import audit_emit

# Iterate all events (or filter by action)
for event in audit_emit.iter_events(action_filter="veto_triggered"):
    ...
```

See ADR-005 for full additivity rules and the process for introducing
a 7th event family (requires a new ADR).

## 12. Sprint 1 debate input

This schema reflects the Sprint 1 debate findings:

- **Security (HIGH):** descriptions may contain secrets → redaction + hash + out-of-repo location
- **Architecture (R1):** existing PostToolUse Agent hook already emits JSON → this hook is silent
- **Architecture (R2):** Claude Code uses `tool_response`, not `tool_result` → fixed
- **Architecture (R3):** SKILL regex must match injector output → matched against the `SKILL: <name>` line emitted by `inject-agent-context.sh`
- **DevOps (nice-to-have):** bucket prompt_length → done
- **Security (MEDIUM):** concurrent writes → mkdir lock
- **Security (LOW):** fail-visible → errors log

See `.claude/plans/PLAN-001-evolution.md` for the full debate round 1.

## 13. v2.7-fields additions — cache-header capture + rail discriminator (PLAN-020 Phase 0, ADR-050)

> **Version-label disambiguation (P0-06 fix).** Sections 13/14/15
> below track **field** additions on the existing `agent_spawn`
> action. The SPEC file `SPEC/v1/audit-log.schema.md` uses v2.7/v2.8/
> v2.9/v2.10 labels to track **action** additions (session-lifecycle,
> rag, tier-policy, skill-reference-v2). Both dimensions are real;
> they evolve independently. When grepping for "v2.N" to understand
> a change, consult both files:
>
> - Internal (this file) = FIELDS on existing actions (suffix `-fields`)
> - SPEC v1 = new ACTIONS (suffix `-actions`)
>
> Cross-reference table:
>
> | Version bump | Internal (fields) | SPEC (actions) |
> |---|---|---|
> | v2.7 | cache-header + rail (§13 below) | session_start/session_end/prompt_submitted/session_stop/output_scan_finding |
> | v2.8 | model discriminator (§14 below) | rag_query_issued/returned/fallback/redacted + rag_index_redacted |
> | v2.9 | hmac chain (§15 below) | tier_policy_* (9 actions) |
> | v2.10 | *(no new fields)* | fluency_nudge + skill_reference_read_{mismatch,stale,never_read} (Session 43 round-8) |

Sprint 20 (Session 32, 2026-04-17) promotes the `agent_spawn` entry
with three **additive** fields captured from the Anthropic API
response. All fields are nullable so legacy / non-Anthropic adapters
can emit without them; older consumers MUST tolerate their absence.

| Field | Type | Notes |
|---|---|---|
| `usage_metadata` | object\|null | Anthropic API `usage_metadata` passthrough. See sub-fields below. Null if the adapter did not surface usage data. |
| `cache_coverage_bps` | integer\|null | Derived metric in **integer basis-points** (ratio × 10000, clamped `[0, 10000]`): `cache_read_input_tokens / (cache_read + cache_creation + uncached)`. Null if denominator is zero or inputs missing. **PLAN-118 WS-E (S181):** replaced the legacy `cache_coverage` **float** field — floats are forbidden in the HMAC-covered payload (`canonical_json` no-float invariant); the float caused `CanonicalJsonError` → fail-open `hmac:null` → audit-chain one-way-rule break on every real spawn. |
| `rail` | string\|null | Spawn dispatch rail discriminator: `"native"` (ADR-050 canonical-5 native subagent file matched) \| `"custom"` (classic inline `## SKILL CONTENT` spawn) \| `null` (legacy / unknown emitter). |

### `usage_metadata` sub-fields

```json
{
  "usage_metadata": {
    "cache_creation_input_tokens": 1234,
    "cache_read_input_tokens": 27300,
    "uncached_input_tokens": 512,
    "output_tokens": 2048,
    "thinking_tokens": null
  }
}
```

Each sub-field is `integer|null`. Producer implementation at
`.claude/hooks/audit_log.py::_extract_usage_metadata` coerces via
`int` with a `_coerce_int` defensive helper (rejects booleans,
accepts digit-only strings). Shape is frozen by ADR-050; extending
the set (e.g. a new cache tier) requires a schema bump to v2.9.

### `cache_coverage_bps` semantics

Integer range `[0, 10000]` basis-points (i.e. the `[0.0, 1.0]` ratio
× 10000; divide by 10000 to recover the ratio). Higher is better —
proxy for how much of the prompt was served from cache rather than
recomputed. PLAN-020 §6 acceptance target: **P50 ≥ baseline + 10pp**
across a session of multi-agent spawns. Null value is distinct from
`0` (the first means "unknown", the second means "no cache hit").
The internal derivation helper `audit_log._compute_cache_coverage`
still returns the float ratio (rounded to 4 decimals); the producer
converts to integer basis-points **before** the value enters the
HMAC-covered entry dict (PLAN-118 WS-E). Readers that average coverage
(e.g. `ceo-boot.py::check_cache_discipline_alerted`) read
`cache_coverage_bps` and fall back to the legacy float `cache_coverage`
for events emitted before the S181 fix.

### `rail` semantics

- `"native"` — prompt matches `## SKILL REFERENCE` sentinel AND
  `subagent_type` is one of canonical-5 (`code-reviewer`,
  `security-engineer`, `qa-architect`, `performance-engineer`,
  `devops`). Populated by PLAN-020 Phase 1+ emitters (ADR-050 dual-
  rail A/B harness enablement).
- `"custom"` — prompt has classic `## SKILL CONTENT` header
  (inline PLAN-019 P1-SEC-B hardened path).
- `null` — pre-PLAN-020 emitters and any entry whose prompt content
  was unavailable at extraction time.

### Backward compatibility

- Pre-v2.7 consumers that iterate entries are unaffected — unknown
  keys are ignored.
- `audit-query.py` accepts entries with and without these fields.
- The read-API contract frozen by `check-audit-read-api-stable.py`
  continues to hold — the additive fields do NOT alter existing
  field types or names.

## 14. v2.8-fields addition — model discriminator (PLAN-021, ADR-052)

Sprint 21 (Session 32, 2026-04-17) adds a single **additive** field
capturing which Claude model produced the sub-agent's response.

| Field | Type | Notes |
|---|---|---|
| `model` | string\|null | Canonical Anthropic model ID for the spawn. VETO roles: any ADR-149 allowlist member (`"claude-opus-4-8"` \| `"claude-fable-5"`); non-VETO tiers: `"claude-sonnet-4-6"` \| `"claude-haiku-4-5-20251001"`; or null. |

### Extraction logic (`audit_log.py::_extract_model`)

The hook probes `tool_response` in this order (first non-empty
string wins):

1. `tool_response["model"]` (top-level, most Anthropic SDK shapes)
2. `tool_response["response"]["model"]` (some adapter wrappers)
3. `tool_response["usage_metadata"]["model"]` (adapters that nest
   model alongside cost data)

Returns `None` if none of the probes yield a string — the field is
still emitted as `null` so consumers can distinguish post-v2.8
emitters (null = genuinely unknown) from pre-v2.8 emitters (absent).

### Canonical IDs per ADR-052 role distribution

| Role | Expected `model` value |
|---|---|
| `code-reviewer` | `"claude-fable-5"` (VETO — any ADR-149 allowlist member) |
| `security-engineer` | `"claude-fable-5"` (VETO — any ADR-149 allowlist member) |
| `qa-architect` | `"claude-sonnet-4-6"` |
| `performance-engineer` | `"claude-sonnet-4-6"` |
| `devops` | `"claude-sonnet-4-6"` (S220 ceremony `ff0a86a3`) |

The model-per-role mapping is configured in each canonical-5 agent
file's frontmatter (`.claude/agents/<slug>.md`). Adopters override
by editing the frontmatter; `upgrade.sh` preserves overrides
(`upgrade_agents_canonical_only`).

### Kill-switch precedence

```
CEO_SOTA_DISABLE=1       → all PLAN-020/021 features OFF
  (overrides everything; forces custom rail + inline + Opus only)

CEO_MULTIMODEL_ENABLE=0  → forces all canonical-5 to Opus
  (PLAN-020 still active; PLAN-021 only disabled)

CEO_MULTIMODEL_ENABLE=1  → default; per-role distribution active
  (audit-log `model` field records the actual model used)
```

When `CEO_SOTA_DISABLE=1` or `CEO_MULTIMODEL_ENABLE=0`, every spawn
reports the session's strong model (an ADR-149 allowlist member,
e.g. `"claude-fable-5"`; or null if the adapter does not surface it)
regardless of agent frontmatter.

### Forensic use case

If a Sonnet-routed code review misses a bug and the incident
report asks "which model decided this?", the `model` field in the
audit log is authoritative. Example query:

```bash
# Find all spawns outside the ADR-149 VETO allowlist that triggered
# a veto in the same session (candidate root-cause for quality-gate
# escape)
jq -c 'select((.model != "claude-fable-5" and .model != "claude-opus-4-8") and .action == "agent_spawn")' \
  ~/.claude/projects/ceo-orchestration/audit-log.jsonl
```

### Backward compatibility

- Pre-v2.8 consumers that iterate entries are unaffected — absent
  `model` key is ignored.
- Post-v2.8 emitters always emit the key (value `null` means
  "adapter did not surface model"); pre-v2.8 entries have no key at
  all.
- Future schema bumps for new Claude model families (e.g. Opus 5,
  Sonnet 5) follow the process in ADR-052 §Model ID bump recipe —
  re-benchmark canonical-5 rubrics, re-run replay benchmark, author
  a new ADR referencing ADR-052, then update frontmatter. No silent
  in-place upgrade.

## 15. v2.9-fields addition — HMAC chain integrity (PLAN-023, ADR-055)

Sprint 23 Phase B (Session 33 Phase E, 2026-04-18) adds a per-entry
HMAC chain for tamper detection. Two **additive** fields plus a new
sidecar and key file.

| Field | Type | Notes |
|---|---|---|
| `hmac` | string\|null | 64 hex chars (SHA-256). Null when the chain is disabled via `CEO_AUDIT_HMAC_DISABLE=1`, when the writer is pre-v2.9, or when key read failed (in which case `hmac_error` is populated). |
| `hmac_error` | string\|null | Non-null only when HMAC compute failed at write time (e.g. key-perm violation, sidecar I/O error). Value is the Python exception class name (redaction-safe). |

### Chain formula

```
hmac = hmac_sha256(key, prev_hmac || canonical_json(entry_sans_hmac))
```

- `key` — 32 random bytes at `~/.claude/projects/<slug>/audit-key`
  (0600 perms). Auto-generated atomically on first write if absent.
- `prev_hmac` — 32 raw bytes (hex-decoded from prior entry's `hmac`).
  Genesis = `b"\x00" * 32`.
- `canonical_json(entry_sans_hmac)` — serialization routed through
  `_lib/canonical_json.py::encode` which pins
  `sort_keys=True, separators=(",", ":"), ensure_ascii=False,
  allow_nan=False` and NFC-normalizes strings. Floats/NaN/Inf
  forbidden. `hmac` and `hmac_error` fields are stripped BEFORE
  canonicalization (you cannot HMAC the HMAC you are about to
  produce).

### Sidecar files

| File | Purpose | Perms |
|---|---|---|
| `~/.claude/projects/<slug>/audit-key` | 32-byte HMAC key | 0600 |
| `~/.claude/projects/<slug>/audit-log.last-hmac` | 64-hex-char last HMAC (best-effort; reconstructible from log tail) | 0600 |

Both files are auto-created by the hook on first use. Both are
preserved by `ceo-backup.sh` (follow-up) and excluded from
`.gitignore` of any adopter repo (the audit log itself is already
excluded).

### Transition-entry rule (one-way)

`audit-verify-chain.py` treats an audit log as a 2-state machine:

- **CHAIN_START** — no `hmac` field seen yet. Entries without `hmac`
  are tolerated (pre-v2.9 zone). `prev_hmac = genesis`.
- **CHAIN_ACTIVE** — at least one `hmac` field seen. Subsequent
  entries MUST carry `hmac`. An entry WITHOUT `hmac` in this state
  is a `transition_violation` → tamper.

Operationally, an adopter upgrading from pre-v2.9 sees their existing
audit log stay valid: pre-v2.9 entries live in CHAIN_START zone; the
first v2.9 write activates the chain; any regression back to
hmac-less entries is surfaced as tamper.

### Chain reset on log rotation

`_lib/audit_emit.py::_write_event` calls
`audit_hmac.reset_chain_on_rotation()` after the log rename but
before the first write to the new file. The sidecar is cleared so
the new file starts from genesis. `audit-verify-chain.py` processes
each file independently; there is no cross-file HMAC dependency.

### What the chain does NOT defend

Per ADR-055 §Threat Model §Out-of-scope:

- Prevention of tamper (only detection post-facto).
- Tail truncation (attacker deletes last N entries; head remains
  internally consistent). Post-v1.6.0: external OTEL anchor.
- Key theft (attacker with `$HOME` read access can forge).
- Rollback (attacker restores an older log+key pair; chain verifies
  against the old key).
- Log+key co-deletion (deny-of-forensics).
- Canonicalization drift on a schema change (mitigated by
  `canonical_json.encode` single-source + ADR gate on changes).

### Kill-switch precedence

```
CEO_SOTA_DISABLE=1         → all SOTA features OFF (overrides all)
  also disables HMAC chain (entries emit hmac=null)

CEO_AUDIT_HMAC_DISABLE=1   → HMAC path skipped; new entries ship
                             hmac=null (verify treats as pre-v2.9
                             zone if it precedes the first
                             hmac-bearing entry; otherwise
                             transition_violation tamper)
```

### Verification

```bash
python3 .claude/scripts/audit-verify-chain.py \
  --log-file ~/.claude/projects/<slug>/audit-log.jsonl
# exit 0 → intact
# exit 1 → tamper (line report on stderr)
# exit 2 → key missing
# exit 3 → malformed JSONL
# exit 4 → perm error on key or log
```

Flags: `--key-file` / `--since N` / `--json` / `--verbose` / `--stdin`.

### Backward compatibility

- Pre-v2.9 consumers that iterate entries are unaffected — absent
  `hmac` key is ignored.
- Post-v2.9 emitters always emit `hmac` (value null when disabled or
  on key-failure).
- Future schema additions that want to participate in the HMAC MUST
  be introduced via a new v2.N SPEC bump. Adding a field that is NOT
  in the HMAC is safe today (the HMAC is computed over the emitted
  entry-sans-hmac, so any additive field is automatically covered).
