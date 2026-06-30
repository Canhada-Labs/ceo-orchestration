---
status: experimental
spec_version: 1.0.0-rc.1
created: 2026-04-16
plan: PLAN-014
phase: F.1a
supersedes: none
---

# SPEC/v1/replay.schema.md — Deterministic Replay Contract

**Version:** 1.0.0-rc.1 (PLAN-014 Phase F.1a, Sprint 14)
**Status:** experimental (per ADJ-003 until Sprint 15 adopter signal)
**Authoritative source:** `.claude/scripts/replay/replay-session.py` — this SPEC is the grep-able CLI + audit contract the replay tool is tested against.

## 0. Purpose

ADR-046 §Decision establishes WHY deterministic replay exists (adopter-debugging primitive; re-run-safe post-incident). This document is the normative companion: invocation contract, audit event shape, safety rails, bounds, versioning.

**Scope:** replay of a single plan-id worth of spawns, consuming audit-log events + (optional) session graph, re-executing in exact spawn order.

**Non-scope:** multi-plan replay, cross-adopter replay, live-adapter replay as default, lossless reconstruction of non-deterministic agent output (agent outputs are stubbed by default — see §2).

Companion documents:
- ADR-046 — Deterministic Replay decision (options + decision + fail-mode)
- ADR-038 — Session-graph derived registry
- `audit-log.schema.md` v2.6 — 3 events registered (`replay_started`, `replay_completed`, `replay_diff_produced`)
- PLAN-014 §Phase F.1 / §F.1b

---

## 1. Version + Status

| Field | Value |
|---|---|
| Schema version | `1.0.0-rc.1` |
| Schema status | `experimental` (frontmatter) |
| Spec lifetime | v1.x.y — additive only per §8 Versioning |
| Authoritative source | `.claude/scripts/replay/replay-session.py` |
| Output directory | `$CLAUDE_PROJECT_DIR/state/replay-out/<replay_id>/` |
| Replay id format | `<original_session_id>-<utc-iso-second>` |

SemVer-shaped. Within v1 every CLI-arg addition is MINOR-bump additive only. Flag removal or semantic change is MAJOR bump (forbidden in v1 without new SPEC file).

---

## 2. Surface

The replay surface is **one executable**: `.claude/scripts/replay/replay-session.py`. Invoked via `_python-hook.sh` pattern (Python >= 3.9, stdlib only).

### 2.1 Modes

- **`dry-run` (DEFAULT):** parses the session, prints planned spawn order + payload hashes, emits audit events, but **invokes zero hooks and zero adapters**. The default mode per ADJ-022 (defense against "oops-I-replayed-prod").
- **`--execute`:** invokes each spawn via the real harness. REQUIRES:
  1. Clean git worktree (pre-flight `git status --porcelain` returns empty; otherwise exits with `dirty_worktree`)
  2. Stub adapters via `CEO_LIVE_ADAPTER_STUB=1` (set by replay tool, not honored if caller overrides)
  3. OTEL disabled (`CEO_OTEL_DISABLED=1`)
  4. `--i-understand-this-reexecutes` acknowledgment flag

### 2.2 Invariants

- **Replays never reach real providers by default.** `--execute` auto-sets `CEO_LIVE_ADAPTER_STUB=1`. Operator override requires TWO explicit flags: `--allow-live --owner-confirm`.
- **Dry-run emits audit events.** Every replay run (dry OR execute) emits `replay_started` + `replay_completed`; dry mode emits `mode=dry_run`, execute mode emits `mode=execute`. No silent replays.
- **Multi-user distinction.** `--as-user <original-owner>` match required; audit event distinguishes replayer via `session_id` (current) from `original_session_id` (replay target).
- **Live-adapter-touching spawns are advisory-only in execute mode.** If the original audit log shows `live_adapter_call_*` events for a spawn, that spawn is SKIPPED in `--execute` mode with a `replay_diff_produced(divergence_kind=live_adapter_skipped)` event.

---

## 3. Invocation (CLI args)

```
replay-session.py --plan <PLAN-NNN> [--original-session-id <SID>]
                  [--mode dry_run|execute]        # default: dry_run
                  [--execute]                     # alias for --mode=execute
                  [--as-user <owner>]             # required if replaying another user's session
                  [--audit-log <path>]            # default: CEO_AUDIT_LOG_PATH
                  [--graph <path>]                # default: derived from plan
                  [--out-dir <path>]              # default: state/replay-out/<replay_id>/
                  [--i-understand-this-reexecutes]
                  [--allow-live]                  # gate 1/2 for live
                  [--owner-confirm]               # gate 2/2 for live
                  [--max-spawns <N>]              # default 500; upper bound 5000
                  [--timeout-seconds <S>]         # default 600; upper bound 3600
                  [--quiet]                       # suppress progress to stderr
                  [--json]                        # JSON output instead of human
                  [--help]
```

### 3.1 Argument semantics

- **`--plan`** (REQUIRED). Canonical PLAN-NNN string. Validated against the audit log — unknown plan-id ⇒ `unknown_plan` exit.
- **`--mode`** / **`--execute`**. Closed enum. Default `dry_run`. `--execute` without `--i-understand-this-reexecutes` ⇒ `missing_ack` exit.
- **`--original-session-id`**. Optional; when absent, replay uses the MOST RECENT complete session for the plan (last `plan_transition` to `done` / `abandoned` / last spawn).
- **`--as-user`**. When the replayer OS-user does not match the original session's recorded owner, `--as-user` is REQUIRED (string match). Missing ⇒ `cross_user_replay_requires_flag`.
- **`--audit-log`** / **`--graph`**. Path overrides. Must exist; missing ⇒ `missing_input`.
- **`--out-dir`**. Created with mode 0o700. Existing dir OK (contents appended).

---

## 4. Error model (closed enum)

All replay errors exit with a specific code + print a single-line machine-readable error to stderr (JSON if `--json`) AND emit `replay_completed(mode=<mode>, diff_summary="error:<code>")`.

| Exit code | Name | Meaning |
|---|---|---|
| 0 | `ok` | Replay completed (dry or execute) |
| 2 | `dirty_worktree` | `--execute` refused because `git status --porcelain` non-empty |
| 3 | `missing_ack` | `--execute` invoked without `--i-understand-this-reexecutes` |
| 4 | `cross_user_replay_requires_flag` | Current OS-user doesn't match original + no `--as-user` |
| 5 | `as_user_mismatch` | `--as-user` value doesn't match original owner |
| 6 | `unknown_plan` | `--plan` value not present in audit log |
| 7 | `missing_input` | Audit log or graph path doesn't exist |
| 8 | `empty_session` | Plan has no spawn events to replay (warning not error; exit 0 unless `--strict`) |
| 9 | `max_spawns_exceeded` | Session has more spawns than `--max-spawns` |
| 10 | `timeout` | Execute mode exceeded `--timeout-seconds` |
| 11 | `live_disallowed` | Live-adapter spawn attempted without `--allow-live --owner-confirm` |
| 12 | `diff_detected` | Execute mode completed with ≥1 divergence (strict mode only) |
| 13 | `audit_parse_error` | Audit log line unparseable (fail-closed) |
| 14 | `graph_parse_error` | Session graph JSON malformed |
| 15 | `io_error` | Filesystem write failure |

**Fail-closed default:** parse errors exit with code 13/14 without partial replay (no "best effort"). This is a debugging tool; silent partial replay hides drift.

---

## 5. Bounds

Runtime bounds enforced pre-execution:

| Bound | Default | Max | Rationale |
|---|---|---|---|
| Max spawns per replay | 500 | 5000 | Upper bound against runaway plans |
| Plan file size | 1 MiB | 4 MiB | Defense against crafted plans |
| Audit log lines scanned | 1M | 10M | Stream-read; memory cap ~200 MB |
| Wallclock timeout | 600s | 3600s | `--timeout-seconds` flag |
| Divergence artifacts | 100 per replay | 1000 | `replay_diff_produced` per-spawn |
| Spawn depth | 1 (flat) | 1 | No recursive replay (prevents nested invocations) |

Exceeding a bound ⇒ exit code per §4.

---

## 6. Audit event shape

Three events registered in `audit-log.schema.md` v2.6:

### 6.1 `replay_started`
```json
{
  "action": "replay_started",
  "original_session_id": "<SID>",
  "mode": "dry_run" | "execute",
  "redacted_fragments_count": <int>,
  "as_user": "<owner-or-empty>",
  "session_id": "<current-session>",
  "project": "<project-slug>",
  "ts": "<utc-iso>"
}
```

### 6.2 `replay_completed`
```json
{
  "action": "replay_completed",
  "original_session_id": "<SID>",
  "mode": "dry_run" | "execute",
  "duration_ms": <int>,
  "spawn_count": <int>,
  "diff_summary": "<free-text-short>",
  "session_id": "<current-session>",
  "project": "<project-slug>",
  "ts": "<utc-iso>"
}
```

### 6.3 `replay_diff_produced`
```json
{
  "action": "replay_diff_produced",
  "original_session_id": "<SID>",
  "spawn_ordinal": <int>,
  "divergence_kind": "output_mismatch" | "spawn_missing" | "extra_spawn" | "env_mismatch" | "audit_payload_mismatch" | "live_adapter_skipped",
  "artifact_path": "<relative-path>",
  "session_id": "<current-session>",
  "project": "<project-slug>",
  "ts": "<utc-iso>"
}
```

**Redaction:** `diff_summary` + artifact-path strings pass through `redact_secrets` in the emitter.

---

## 7. Revocation

### 7.1 Runtime revocation

A running replay is terminated by:
- SIGTERM → emits `replay_completed(diff_summary="error:sigterm")` and exits 0
- Timeout (§5) → exits 10
- Ctrl-C (SIGINT) → exits 0 with `diff_summary="error:user_interrupt"`

### 7.2 Output revocation

Replay output directory under `state/replay-out/<replay_id>/` is retained by default. Callers may:
- Manually remove (operator action)
- Future: add `--auto-cleanup-on-exit` flag (MINOR-bump; additive)

No automatic pruning — the framework does not garbage-collect replay artifacts.

### 7.3 Audit event revocation

Audit events are append-only (audit-log.schema.md §2 invariant). A replay-event is never "un-emitted". Dry-run provides dry-run-specific `mode` so consumers can filter.

---

## 8. Deprecation + versioning

Within v1 (1.0.0-rc.1 through 1.x.y):

- **CLI flag additions** are MINOR bump, additive only.
- **CLI flag removals** are MAJOR (forbidden in v1).
- **Audit event additions** are MINOR (new divergence_kind values additive).
- **Audit event removals** are MAJOR (forbidden in v1).
- **Default mode change** (e.g. dry_run → execute) would be MAJOR (explicitly forbidden — the "dry-run default" is a safety invariant per ADJ-022).

Unknown flag ⇒ exit `argparse.error` (exit 2 per argparse convention). Callers wanting forward-compat should probe with `--help` before piping new flags.

---

## 9. History

| Version | Released | Summary |
|---|---|---|
| 1.0.0-rc.1 | 2026-04-16 | Initial experimental release. Dry-run default, stub adapters on execute, multi-user `--as-user`, 6 divergence kinds. Status: experimental pending Sprint 15 adopter signal. |

---

## 10. Backward compatibility

- **Old replay outputs:** replay artifacts from v1.0.0-rc.1 remain readable by future tool versions (additive-only).
- **Unknown event fields** in audit log: replay tolerates + skips. Extra fields never block.
- **Old session graphs** from ADR-038 v1: accepted as-is (no graph version bump required).
- **Consumer contract:** tooling that reads `replay_started` / `replay_completed` / `replay_diff_produced` events MUST tolerate unknown fields + unknown `divergence_kind` values (treat unknown as `unknown_divergence`, advisory).

---

## 11. Deprecation window

2 MINOR releases minimum for any CLI flag or event payload field. No deprecation window for advisory output fields (may drop on MINOR).

**Frozen in v1:**
- Dry-run is the default mode (§2.1)
- `--execute` requires clean worktree (§2.1)
- Stub adapters default under execute (§2.2)
- 3 audit event types (§6)

These invariants ARE the point of the replay tool; changing them is a new tool, not a version bump.

---

## References

- ADR-046 — Deterministic Replay decision
- ADR-038 — Session-graph derived registry
- `audit-log.schema.md` v2.6 — event registration
- PLAN-014 §Phase F.1 / §F.1a / §F.1b / §F.2
- `.claude/scripts/replay/replay-session.py` (authoritative)

---

**End of SPEC/v1/replay.schema.md v1.0.0-rc.1 (experimental).**
