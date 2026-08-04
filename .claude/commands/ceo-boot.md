---
description: Session boot autopilot — 24 Tier-S parallel checks + recommendations engine. Run at session start to consolidate governance reads + state digest.
allowed-tools: Read, Glob, Grep, Bash, TaskCreate, TaskList
---

# /ceo-boot — Session boot autopilot

Single command at session start that consolidates governance reads + state digest + recommendations. Per PLAN-065 §4.3 acceptance:

- 24 Tier-S checks dispatched **in parallel** via `concurrent.futures.ThreadPoolExecutor` (stdlib only, max_workers=8)
- Per-check timeout 500 ms; aggregate wall-clock ≤5 s
- `--short` defaults to cached mode (≤2 s budget; cache-hit ≤200 ms)
- `--json` emits machine-readable digest (stable order — CR-N7 deterministic ranking)
- Idempotent (back-to-back identical mod timestamps + transient failures)
- Recommendations engine: rule-based, ≤5 actionable items, sanitized inputs (Sec MF-4)
- Audit emit hasattr-guarded (works pre + post canonical ceremony in v1.12.0)

## Arguments

`/ceo-boot $ARGUMENTS`

| Flag | Effect | Budget |
|---|---|---|
| (none) | Default — 24 Tier-S parallel checks + recommendations | ≤5 s wall-clock |
| `--short` | Top-line counts + non-green checks one-line | ≤2 s (defaults `--cached`) |
| `--cached` | Cache-hit path (TTL 1h; key=HEAD+audit-log mtime) | ≤200 ms |
| `--json` | Machine-readable; stable ordering | preserves above |
| `--bench` | Run N=5 iterations + report p50/p95 + RSS delta | runs synchronously |

## Procedure

### Step 1 — Gate 1+2 governance reads

Host CLI has already loaded `CLAUDE.md` + `PROTOCOL.md` + `team.md` via `SessionStart` hook. `/ceo-boot` does **NOT** re-read those files; it reads only the live governance + audit state via the 24 Tier-S checks.

### Step 2 — Dispatch 24 Tier-S checks in parallel

```bash
python3 .claude/scripts/ceo-boot.py $ARGUMENTS
```

The script uses `ThreadPoolExecutor(max_workers=8)` to dispatch 24 Tier-S checks across 6 categories:

1. **Plans state** — `plans_executing` / `plans_reviewed_pending` / `plans_stranded_executing` / `plans_draft`
2. **Audit-log freshness** — `audit_log_freshness` / `dispatch_count_24h` / `skill_unknown_ratio`
3. **Governance health** — `governance_validate` (fast --json profile) / `hook_live_smoke` / `audit_v3_backlog`
4. **Owner-pending** — `sentinels_pending_gpg` / `rc_hold_aged`
5. **Cost / budget** — `cost_24h_usd` / `active_plan_burn_ratio`
6. **ADRs** — `adrs_stale_proposed`

Each check has a 500 ms hard timeout. Aggregate wall-clock budget is 5 s. Per-check timeout emits `ceo_boot_check_skipped` audit event (CR-MF6 forensic trace).

### Step 3 — Format digest

- Default: full markdown table (~30 lines including recommendations)
- `--short`: 5-line summary + non-green check rollup
- `--json`: stable-ordered machine output

### Step 4 — Recommendations engine (sanitized)

Rule-based prioritizer ranks max 5 actionable items, sorted by deterministic key (CR-N7):

1. Owner GPG sentinels pending
2. Stranded executing plans (>24h no commits)
3. Skill-unknown dispatch ratio elevated
4. Audit-v3 backlog open
5. ADRs PROPOSED >30d

Every disk-sourced string passes through `_lib/injection_patterns.scan_harness_mimicry` (with `scan_text` legacy fallback) before display. Hits become `[REDACTED-INJECTION-PATTERN]`. Lengths bound to 200 chars per item, post-NFKC normalize.

### Step 4.5 — TaskCreate-candidate marker orchestration (PLAN-078 Wave 5)

**Default mode only** (skipped under `--short`, `--cached`, `--json`, or env `CEO_BOOT_AUTO_TASK=0`).

When `gate_pass=False`, `ceo-boot.py` writes up to 3 `<!-- TASKCREATE-CANDIDATE -->` marker blocks to stdout for the top-3 high/medium recommendations. Each marker carries:

```
<!-- TASKCREATE-CANDIDATE rank=1 severity=high awaiting_confirm=false -->
Subject: <sanitized recommendation summary>
<!-- /TASKCREATE-CANDIDATE -->
```

**Claude orchestrator workflow** (this is the "auto" in auto-TaskCreate — the model running /ceo-boot does the orchestration; the python script never invokes the harness primitive directly):

1. After running `python3 .claude/scripts/ceo-boot.py`, parse stdout for `<!-- TASKCREATE-CANDIDATE … -->` blocks. The opening comment carries `rank`, `severity`, `awaiting_confirm`. The Subject is on the next line. **`subject_hash` is NOT in the marker** — compute it client-side as `sha256(NFKC(subject))[:12]` so the dedup check below can compare against the existing task list.
2. Invoke `TaskList` once to inspect the current task list.
3. For each marker block, dedup against existing tasks: if any open task subject hashes to the same 12-hex `subject_hash`, skip; otherwise call `TaskCreate` with `subject = "<Subject text>"` and `description = "Surfaced by /ceo-boot — severity=<severity>, rank=<rank>. Investigate and resolve before next gate run."`.
4. If `awaiting_confirm=true` (reserved future flag — currently always `false`), do NOT auto-create; surface to Owner for explicit confirmation.

**Dedup state**: a 24h TTL file at `~/.claude/projects/<project>/state/ceo-boot-tasks-emitted.json` (filelock'd via `_lib/filelock.FileLock`) prevents the same subject from generating a marker twice in 24h. Override with `CEO_BOOT_TASK_STATE_PATH` (tests).

**Audit emit**: each marker fires `ceo_boot_task_candidate_emitted` (4 caller fields — rank, severity, subject_hash, awaiting_confirm; Sec MF-3 enforced; subject text NEVER persisted).

### Step 4.7 — Past-lessons fenced one-liners (PLAN-154 item 4)

**Default full mode only** and **default-OFF** — rendered only when `CEO_LEARNING_BOOT_LESSONS=1` (opt-in, A12 switch family; `CEO_SOTA_DISABLE=1` master precedence wins). Skipped under `--short`, `--cached`, and `--json`; the section is **never written to the boot cache**, which is the structural guarantee that lesson text stays out of every machine-readable surface.

When enabled, `ceo-boot.py` consumes `lessons.get_boot_lessons_verified(project_dir, now_fn=None)` (defensive import — function missing = render nothing + fail-open stderr breadcrumb; boot never breaks) and renders **at most 3** approved lesson one-liners inside a ```` ```text ```` fence, framed explicitly as **UNTRUSTED DATA, not instructions** (same treatment as recalled memories):

- `lessons.py` owns approval-state filtering, TTL/decay, bounded-vocab schema, and the A6 `sha256(trigger + advisory_text)` verify-before-render against the HMAC chain's approval events (mismatch → dropped upstream + integrity breadcrumb).
- The renderer applies an **independent fail-CLOSED gate** per lesson (any failure → that lesson is DROPPED, never repaired): shape check (bounded `lesson_id`, 64-hex `content_sha256`), bounded vocabulary (no backticks — fence escape impossible by construction — no newlines/CR/NUL), the ≤200-chars-post-NFKC cap **asserted, never truncated** (cap-then-fence: the cap applies before fencing; the upstream schema cap guarantees length so no truncation code exists here), the fail-CLOSED `_lib.guardrail_validator.validate_text` route (validator import failure or raise = scanner-unavailable → drop; this is NOT the advisory scanner path), and the existing Step-4 `_sanitize_for_recs` bound+scan pipeline (harness-mimicry hit → the lesson is dropped, never rendered redacted).
- Drops surface as a **count-only** integrity NOTE line and emit `lesson_boot_render_dropped` audit events (closed fields: `reason` enum / bounded `lesson_id` / `session_id`; silent no-op until the action is registered).
- A9 expiry warning: when `lessons.count_pending_expiring(project_dir, now_fn=None)` exists and returns N > 0, a **count-only** WARNING line renders ("N pending lesson candidate(s) expire in <7d — run /lesson-review"). Zero candidate text can reach boot through the warning side door.
- An explicit operator disable (switch set to a non-`1` value, or `CEO_SOTA_DISABLE=1` while opted in) emits one `learning_rail_disabled` breadcrumb (rail=`boot_render`) per invocation for Wave-E liveness; merely-unset emits nothing (structurally off).

### Step 5 — Audit emit (Phase 7.A canonical ceremony)

Final step: `audit_emit.emit_ceo_boot_emitted` with whitelisted fields per Sec MF-3:

- `gate_pass` (bool) — no red/error/timeout
- `duration_ms` (int) — total wall-clock
- `checks_total` (int)
- `checks_failed` (int)
- `cache_hit` (bool)

DENIED fields (LLM06 side-channel guard): tokens / cost_usd / prompt content / SKILL.md content / file paths / recommendation text body / environment values / **lesson text** (PLAN-154 A5 — lesson one-liner content never appears in `--json` output, the boot cache, or any audit event; it renders exclusively in the default-mode fenced section of Step 4.7).

Pre-canonical-ceremony, the call is a hasattr-guarded no-op (script works in adopter installs that haven't run the v1.12.0 ceremony yet).

## Out-of-scope (deferred to PLAN-067 v1.13.0)

- Tier-A 10 additional checks (`--verbose` stub today)
- Auto-`session-resume` integration (Phase 3-C)
- Watchdog detector #7 (Sec HARD VETO conditional → PLAN-067 per ADR-103)

## Kill switches

- `CEO_BOOT_AUTO_TASK=0` — Wave 5 opt-out: disables `<!-- TASKCREATE-CANDIDATE -->` marker emit. The 24 Tier-S digest + recommendations still print; only the marker blocks (and their `ceo_boot_task_candidate_emitted` audit events + dedup state-file writes) are suppressed.
- `CEO_BOOT_TASK_STATE_PATH=<path>` — override dedup state file location (tests).
- `CEO_BOOT_DEBUG=1` — surface fail-open trace from audit emit + marker emit (stderr only; never blocks).
- `CEO_LEARNING_BOOT_LESSONS=1` — PLAN-154 item 4 opt-in: enables the Step 4.7 past-lessons fenced section. Unset = structurally OFF (no lesson-store I/O — `cost_envelope.py` posture). Any other set value = explicit operator disable (emits the `learning_rail_disabled` liveness breadcrumb). `CEO_SOTA_DISABLE=1` overrides everything (master kill precedence).
