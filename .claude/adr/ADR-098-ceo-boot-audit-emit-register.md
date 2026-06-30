# ADR-098 — `/ceo-boot` audit_emit lifecycle action register + v1.12.1 wiring extensions

**Status:** ACCEPTED
**Date:** 2026-05-04 (v1.12.0 partial; v1.12.1 100% close)
**Plan:** PLAN-065 §Phase 1 + §Phase 2 + §Phase 3 + §Phase 4-B + §Phase 5-D + §Phase 7-A + Layer A amendment
**Reserved slot:** ADR-098 (per CLAUDE.md §1 ADR list)
**Enforcement commit:** `41c4ae5` (PLAN-070-071 bundle, v1.13.0)

## Decision drivers

- **Reality-Ledger fixture #4 closure** (declared-but-not-wired pattern). Pre-S82, `.claude/scripts/ceo-boot.py` shipped two emit comments at `:644` (cached path) + `:676` (uncached path) saying ``# ceo_boot_emitted emit deferred to v1.12.0 ceremony.`` and one at `:414` for `ceo_boot_check_skipped`. The script ran in production with `--bench` / `--short` / `--json` / `--cached` modes for ~2 days but emitted **zero** lifecycle telemetry — every invocation closed silently. PLAN-071 (drafted Session 79) flagged this exact pattern as Reality-Ledger fixture #4. ADR-098 closes the gap.

- **Codex audit-v3 finding A precedent** (Session 76, 2026-04-29 — `skill_bootstrap_used` + `skill_bootstrap_post_hash` registration). The framework has a 1-year track record of "hooks emit but action is unregistered → `_write_event` silently drops → forensic reconstruction blocked." ADR-098 follows the same fix pattern (register first, emit second; SPEC schema row in same ceremony).

- **CR-MF6 closure** (PLAN-065 Round 1 debate, Session 77). `ceo_boot_check_skipped` per timed-out check is REQUIRED so a 30-day operator query like `audit-query.py --action ceo_boot_check_skipped` can detect adopter regressions (per-check timeout creep, single check stuck in network call).

- **Sec MF-3 enforcement boundary**. PLAN-065 Round 1 Security archetype flagged that an unregistered action with a free-form payload risks LLM06 side-channel (token-count leakage via custom kwargs). ADR-098 closes by encoding the field allowlist as a `frozenset` at module-load time + scrub-before-emit in the typed wrapper.

- **agent_spawn skill=unknown 24/24 baseline** (Session 78 baseline; current S83 = 19/23 = 83%). Pre-S82 audit-log analysis confirmed Phase 1 wire is overdue; ADR-082 mitigated dispatch + Format-B SKILL REFERENCE default flip rendered the Format-A inline regex obsolete.

- **Custom-MCP-tools governance gap** (S81-tris discovery, feedback `custom_mcp_tools_governance_gap.md`). `check_canonical_edit.py` was registered against `Edit|Write|MultiEdit` matcher in `.claude/settings.json`. Any tool name `mcp__*__*` — including `mcp__codex__apply_patch` — bypasses the gate entirely. Defense-in-depth ADR-001/002/051 was designed when MCP local stdio was not used for writes. Layer A amendment closes the gap before any MCP server is wired into the framework's governance rail.

- **Stdlib-only invariant** (PLAN-068 §0.4 R1 + ADR-085 Claude-only positioning). All allowlist enforcement is `frozenset` membership + dict-comprehension copy. Zero new dependencies.

## Context

PLAN-065 v1.12.0 wiring originally split into 14 phases across 7 phase groups, of which:

- **Shipped at v1.12.0 GA (S82 Track-A + Track-C):** Phase 0 baseline, Phase 2 audit_emit canonical register (`ceo_boot_emitted` + `ceo_boot_check_skipped`), Phase 3 MVP `/ceo-boot` (S81), Phase 7-B/C VERSION + tag.
- **Pending v1.12.1 (PLAN-065 100% close, S83):** Phase 1 audit_log.py 3-path matrix wire, Phase 3-rest `--cached` real cache + `--bench` + `--verbose`, Phase 4-B check_plan_edit.py stranded 2-mode, Phase 4-C UNTRUSTED-FORK doc, Phase 4-D PLAN-SCHEMA Liveness contract advisory, Phase 5-B OWNER-CEREMONY-CONTRACT v2, Phase 5-D check_budget.py max_tokens, Phase 5-E helper cleanup, Phase 7-A this ADR flip + enforcement, Phase 7-B/C v1.12.1 release.
- **Layer A amendment:** mcp__* matcher extension in `.claude/settings.json` PreToolUse (gap S81-tris closure).

This consolidated ADR-098 ratifies the entire PLAN-065 v1.12.0+v1.12.1 wiring under a single ADR slot per ADR-093 §per-plan-cap (≤2 ADRs/plan; only ADR-098 consumed for PLAN-065 — ADR-101 was PLAN-069 specifically).

## Decision

### Phase 2 audit_emit register (shipped v1.12.0)

Adopt 2 new audit-log actions: `ceo_boot_emitted` + `ceo_boot_check_skipped`. Register at all 5 surfaces in a single v1.12.0 kernel ceremony (`CEO_KERNEL_OVERRIDE=1` + `CEO_KERNEL_OVERRIDE_ACK=PLAN-065-Phase-2-audit-actions`).

#### `ceo_boot_emitted` payload (Sec MF-3 allowlist)

| Field | Type | Notes |
|---|---|---|
| `action` | `"ceo_boot_emitted"` literal | Discriminator |
| `ts` | ISO-8601 UTC | Set by `_write_event` |
| `event_schema` | `"v2"` | Set by `_write_event` |
| `session_id` | string ≤64 chars | From `$CLAUDE_SESSION_ID` / `$CEO_SESSION_ID` / pid+log-mtime fallback |
| `project` | string | Caller passes `""` if unset |
| `gate_pass` | bool | `true` if all 15 Tier-S checks passed |
| `duration_ms` | int | Total wall-clock |
| `checks_total` | int | 15 (Tier-S) or 25 (with Tier-A) |
| `checks_failed` | int | Count of red/error/timeout |
| `cache_hit` | bool | True iff `--cached` mode AND cache valid |
| `tokens_in` / `tokens_out` / `tokens_total` | null | Reserved nullable per v2 contract |
| `hmac` / `hmac_error` | string/null | ADR-055 chain fields |

#### `ceo_boot_check_skipped` payload (Sec MF-3 allowlist)

| Field | Type | Notes |
|---|---|---|
| `action` | `"ceo_boot_check_skipped"` literal | |
| `ts` / `event_schema` / `session_id` / `project` | as above | |
| `check_name` | string ≤64 chars | E.g. `"plans_executing"` |
| `timeout_ms` | int | The budget that was breached (default 500) |
| `tokens_in/out/total` / `hmac` / `hmac_error` | reserved | |

#### Forbidden fields (denied; stripped + breadcrumbed if leaked)

`tokens_in_total` (custom, vs reserved `tokens_in`), `tokens_out_total`, `cost_usd`, `cost_cents`, `prompt`, `skill_content`, `env`, `paths`, `recommendation_text`, `stack_trace`, `error_message`, `detail`, `exception` — see PLAN-065 §4.3.4.

### Phase 1 audit_log.py 3-path matrix (v1.12.1 wiring)

Replace `_SKILL_LINE_RE` + `extract_skill()` in `.claude/hooks/audit_log.py` with a 3-path matrix porting validated logic from `.claude/scripts/extract-skill.py` (430 LoC / 58 tests, S82 Track-C).

| Path | Pattern | Extraction |
|---|---|---|
| (a) Format-A inline | `^SKILL:[ \t]+([a-z0-9][a-z0-9\-]{0,255})\s*$` line-anchored MULTILINE | match[1] |
| (b) Format-B reference | `^@\.claude/skills/(?:core|frontend|domains/[\w-]+/skills)/([\w-]+)/SKILL\.md sha256=[0-9a-f]{64}$` | match[1] (path segment) |
| (c) `## SKILL CONTENT` block | block heading present + `SKILL LOADED: <name>` line within block | conservative parse |

**Sec MF-7 hardening:** NFKC normalize + length cap 256 chars + ReDoS-safe bounded quantifiers + path-traversal denied + Unicode homoglyph denied + NUL byte injection denied.

**Acceptance metric:** `agent_spawn skill=unknown` ratio ≤10% in 30d post-merge (current S83 baseline 19/23 = 83%).

### Phase 4-B check_plan_edit.py stranded 2-mode (v1.12.1 wiring)

Add 2-mode stranded detection in `.claude/hooks/check_plan_edit.py`:

- **Mode 8.2 Paperclip** ("in_progress sem run vivo"): `status: executing` AND no commits touching plan file in >24h → block + visible breadcrumb
- **Mode 8.1** ("todo dispatch falhou"): `status: reviewed` AND no transition to executing for >7d → wake automático for Owner

Hook itself does NOT auto-block on stranded plans — it ADDs breadcrumb to systemMessage when an unrelated plan-edit happens AND a stranded plan exists. Fail-open invariant preserved.

### Phase 5-D check_budget.py max_tokens (v1.12.1 wiring)

Extend ADR-033 to allow plan-level cap. `check_budget.py` reads frontmatter `max_tokens:` with strict int-only schema:

- Accept: positive integer literal `max_tokens: 500000` (1 ≤ N ≤ 10_000_000)
- Reject (fall back to env/default + breadcrumb): string values, scientific notation overflow, negative ints, alias references, type-confused strings
- Cap at 10M tokens absolute ceiling (defense-in-depth)

Cap precedence: plan frontmatter > env `CEO_MAX_PLAN_TOKENS` > 1_000_000 default.

### Layer A — `.claude/settings.json` mcp__* matcher (v1.12.1 amendment)

Extend PreToolUse matcher in `.claude/settings.json` from `"matcher": "Edit|Write|MultiEdit"` to also intercept `mcp__.*`:

```json
{
  "matcher": "Edit|Write|MultiEdit|mcp__.*",
  "hooks": [
    {
      "type": "command",
      "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh\" check_canonical_edit.py",
      "timeout": 5
    }
  ]
}
```

`check_canonical_edit.py` extends to inspect `tool_input` for write-shaped parameters when `tool_name.startswith("mcp__")`: `path`, `file_path`, `content`, `patch`, `diff`, `source`, `text`. If path resolves to a canonical-guarded path → block unless sentinel covers.

**Layer B (server-side `_lib/mcp/canonical_guard.py` middleware) DEFERRED** to PLAN-070 R3 patches (depends on Round 2 Security CONDITIONAL-VETO 6 conditions).

### Owner authorization for kernel + sentinel ceremony (Sec MF-5 enumeration table)

| Phase | Path edit | Override mechanism | Reason slug | Sentinel scope |
|---|---|---|---|---|
| 2 (audit_emit) — SHIPPED v1.12.0 | `.claude/hooks/_lib/audit_emit.py:_KNOWN_ACTIONS` add 2 entries | `CEO_KERNEL_OVERRIDE=1` + `CEO_KERNEL_OVERRIDE_ACK=PLAN-065-Phase-2-audit-actions` | `PLAN-065-Phase-2-audit-actions` | n/a (kernel) |
| 1 (audit_log.py canonical) — v1.12.1 | `.claude/hooks/audit_log.py` | sentinel | `PLAN-065-Phase-1-skill-extraction` | declared in approved.md |
| 3-rest (ceo-boot.py + audit emit wire) — v1.12.1 | `.claude/scripts/ceo-boot.py` (non-canonical) | none — direct edit | `PLAN-065-Phase-3-rest-wire` | n/a |
| 4-B (check_plan_edit.py canonical) — v1.12.1 | `.claude/hooks/check_plan_edit.py` | sentinel | `PLAN-065-Phase-4-B-stranded-modes` | declared in approved.md |
| 5-D (check_budget.py canonical) — v1.12.1 | `.claude/hooks/check_budget.py` | sentinel | `PLAN-065-Phase-5-D-max-tokens` | declared in approved.md |
| 7-A (this ADR flip) — v1.12.1 | `.claude/adr/ADR-098-*.md` | sentinel | `PLAN-065-Phase-7-A-adr-098-flip` | declared in approved.md |
| Layer A (settings.json mcp__* matcher) — v1.12.1 | `.claude/settings.json` | sentinel | `PLAN-065-Layer-A-mcp-matcher` | declared in approved.md |
| 7-C (CLAUDE.md canonical closeout — by design NOT in `_CANONICAL_GUARDS`) | `CLAUDE.md` | n/a (closeout convention) | `PLAN-065-Phase-7-closeout` | n/a |

**v1.12.1 Owner ceremony lote:** SINGLE sentinel `approved.md` covering 5 canonical paths (audit_log.py + check_plan_edit.py + check_budget.py + ADR-098 + settings.json) + ONE Owner GPG sign + ONE apply transaction. Per OWNER-CEREMONY-CONTRACT.md v2 single-batch sentinel sign discipline (S81 Phase 2 R6).

## Alternatives considered + rejected

### Alt 1 — Generic `audit_event` action with free-form payload

REJECTED. Breaks the v2 typed-stream contract (`_KNOWN_ACTIONS` discriminator) and reproduces the same LLM06 side-channel risk that PLAN-059 SEC-P0-04 closed for `audit_tokens_emitted` via the 12-key allowlist.

### Alt 2 — Reuse `session_start` / `session_stop` (ADR-056)

REJECTED. `session_start` fires on harness boot (SessionStart hook); `/ceo-boot` is a downstream user-invoked command that may run multiple times within one harness session. Conflating the two breaks `audit-query.py session-stats`.

### Alt 3 — Defer Phase 1 to v1.13.0 / PLAN-067

REJECTED. PLAN-065 §Phase 1 explicitly schedules audit_log.py 3-path matrix wire for v1.12.0. Deferring to v1.13.0 means shipping v1.12.0 GA with the bug `agent_spawn skill=unknown` 24/24 STILL active. CEO-boot recommendations engine flagged 83% ratio in S83 — already user-visible regression. Closes in v1.12.1 train.

### Alt 4 — In-memory metric (Prometheus-style counter, no audit-log)

REJECTED. Breaks Claude-only thesis (ADR-085).

### Alt 5 — Layer A as separate ADR (ADR-104+)

REJECTED. PLAN-065 already consumes ADR-098 slot per ADR-093 §per-plan-cap. Adding a new ADR for Layer A would consume slot 104 unnecessarily; the matcher extension is integral to PLAN-065 governance reach. Documented as Layer A amendment within ADR-098 instead.

### Alt 6 — Layer B (server-side `_lib/mcp/canonical_guard.py` middleware) shipped concurrently

REJECTED for v1.12.1. Layer B depends on PLAN-070 Round 2 (Security CONDITIONAL-VETO 6 conditions: allowlist codified, JSON-RPC parser caps, stdio-only enforcement test, governance_check subprocess frozen, replay-fixture redaction, --allow-prompts GPG-signed lease). PLAN-070 R2 is its own debate gate. Layer B ships separately when PLAN-070 lands.

## Consequences

### Positive

- **Sec MF-3 enforcement** at the canonical boundary. Drift is mechanical — a future-CEO mistake passes a forbidden kwarg, the scrub fn drops it, the breadcrumb in `audit-log.errors` surfaces the drift on next operator review. **Defense-in-depth (Codex S82 P1#1 closure):** `emit_generic` ALSO routes `ceo_boot_emitted` + `ceo_boot_check_skipped` through `_scrub_ceo_boot_event` so a future direct caller (`emit_generic("ceo_boot_emitted", prompt=...)`) cannot bypass the typed-wrapper boundary.
- **Telemetry observability for `/ceo-boot`**. Operators can run `audit-query.py --action ceo_boot_emitted --since 7d` to verify adoption + identify cache-miss rates. Per-check timeout queries surface adopter-side performance regressions.
- **`agent_spawn skill=unknown` ratio collapse**. Phase 1 wire alone is expected to drop the ratio from 83% to <10% in 30d, restoring forensic observability across all spawn rails (native + mitigated + Format-A + Format-B).
- **Stranded-plan visibility**. Phase 4-B 2-mode detection surfaces in-flight plans that have lost momentum (stale executing) AND plans that are stuck pre-execution (stale reviewed). Operator sees both classes of stuck work.
- **Plan-frontmatter cap**. Phase 5-D enables per-plan token budget without touching env vars, which is the right shape for adopter-facing budget governance.
- **MCP custom-tools defense-in-depth**. Layer A closes the S81-tris gap. `check_canonical_edit` now intercepts not just Edit/Write/MultiEdit but any `mcp__*__*` tool with write-shaped params. Codex MCP local stdio + Supabase MCP + any future custom MCP server is covered.
- **Reality-Ledger fixture #4 closed**. PLAN-071 declared-but-not-wired pattern detector loses one of its 6 baseline fixtures. Health: framework's reality matches its declared behavior on this specific surface.
- **CR-MF6 acceptance criterion satisfied**. Round 1 debate consensus required `ceo_boot_check_skipped` for forensic reconstruction.

### Negative

- **+2 entries in `_KNOWN_ACTIONS`** (97 → 99). Crosses the `test_known_actions_count_fixed` pin; bumping required (mechanical, 1-line edit).
- **+1 ADR slot consumed** (ADR-098). ADR-093 §per-plan-cap stipulates ≤2 ADRs per plan; PLAN-065 v1.12.0+v1.12.1 ships only this ADR.
- **+~150 LoC in `_lib/audit_emit.py`** + ~200 LoC across audit_log.py + check_plan_edit.py + check_budget.py. Module sizes still within the function-length-policy advisory threshold per ADR-097.
- **Settings.json matcher regex broadens scope.** Previously `Edit|Write|MultiEdit` matched 4 tool names; now `Edit|Write|MultiEdit|mcp__.*` matches an unbounded set. Each MCP tool invocation pays the hook overhead (~5-10ms). For Codex MCP heavy use, this is up to ~5s/100 calls — acceptable.
- **5 tests skipped pre-canonical-ceremony** in `test_ceo_boot_audit_emit.py::TestAdversarialDeniedField`. Activated automatically post-merge.

### Neutral

- **HMAC chain extension**. ADR-055 v2 chain fields (`hmac`, `hmac_error`) are populated automatically by `_write_event`.
- **No SPEC v1 break**. SPEC version bumps minor (v2.16 → v2.17) — additive. Adopter consumers tolerate unknown fields per AUDIT-LOG-SCHEMA.md §2 forward-compat.
- **`extract-skill.py` standalone preserved**. The S82 Track-C standalone module remains for CLI use + as the validated reference implementation; Phase 1 wire ports its logic into the hook without removing the script.

## Reopen criteria (per ADR-092 + CR-U5 + ADR-071 methodology)

- **Phase 3:** `/ceo-boot` p95 latency >5 s in 30d window OR `ceo_boot_check_skipped` ratio >20% in 30d → reduce per-check timeout OR drop slow checks
- **Phase 1:** `agent_spawn skill=unknown` ratio >10% in 30d post-merge → re-investigate extraction matrix
- **Phase 4-B:** false-positive stranded detection >5% in 30d → tune thresholds OR add allowlist
- **Phase 5-D:** YAML-attack pattern bypass detected → tighten int-only schema + add fixtures
- **Layer A:** any `mcp__*` tool successfully writes a canonical path WITHOUT sentinel → governance gap; investigate matcher regex + write-shape param detection
- Field allowlist drift detected via `_breadcrumb` count >0 in 30d → audit caller-side discipline
- Operator demand for `tokens_in` / `cost_usd` per-invocation → open new ADR (do NOT amend ADR-098 in place); proper venue is PLAN-067 §Phase 4 token-economy extensions

**Measurement protocol (ADR-071):** median-of-3 + p95 over N≥10 invocations + warm/cold marker; FPR over 30d window with denominator + labeling rule.

## Coordination with sibling ADRs

- **ADR-101 §Audit-action registration** (`replay_capture_started` + `replay_capture_completed`, S81 Wave D, count 95 → 97). ADR-098 ships at v1.12.0 + v1.12.1 (count 97 → 99). No collision.
- **ADR-099 / ADR-100** (PLAN-068 changesets + trusted-deps, S79 v1.11.6 GA at HEAD `c1a1ab1`). Already ACCEPTED; no audit-action surface impact.
- **ADR-051** (skill-reference threat model). Layer A extends the threat-model section to include MCP custom-tool write-shape params. ADR-051 amendment is part of this ceremony — NOT a separate ADR.
- **ADR-102 reserved** (PLAN-070 v1.12.x MCP introspection tools). Layer B ships there.
- **PLAN-067 v1.13.0 canonical extensions** (silent_execution detector #7, version-drift hook). Both will introduce new actions — but their ADRs (slots reserved 102+) cite ADR-098 as registration-pattern precedent.

## Test surface

- `.claude/hooks/tests/test_audit_emit.py::TestAuditEmit::test_known_actions_set_contract` — expected set updated +2 entries.
- `.claude/hooks/tests/test_audit_emit_api_contract.py::test_known_actions_count_fixed` — count 97 → 99.
- `.claude/hooks/tests/test_audit_emit_api_contract.py::_EXPECTED_PUBLIC_SYMBOLS` — +`emit_ceo_boot_emitted` + `emit_ceo_boot_check_skipped`.
- `.claude/hooks/tests/test_audit_emit_api_contract.py::_EXPECTED_KNOWN_ACTIONS_SHA256` — recomputed.
- `.claude/hooks/tests/test_audit_log_phase1.py` (NEW, Phase 1) — 3-path matrix + 6 security hardening fixtures + ≥10 positive cases ≈ ≥16 tests.
- `.claude/hooks/tests/test_check_plan_edit_stranded.py` (NEW, Phase 4-B) — ≥8 tests (4 mode-8.1 + 4 mode-8.2).
- `.claude/hooks/tests/test_check_budget_max_tokens.py` (NEW, Phase 5-D) — ≥6 tests (4 YAML-attack + 2 happy-path).
- `.claude/hooks/tests/test_check_canonical_edit_mcp.py` (NEW, Layer A) — mcp__* tool write-shape params + non-canonical allow + canonical block.
- `.claude/scripts/tests/test_ceo_boot_enhanced.py` (NEW, Phase 3-rest) — `--cached` real cache + `--bench` + `--verbose` + sanitization + audit emit telemetry ≈ ≥45 tests.
- `.claude/scripts/tests/test_plan_tokens.py` (NEW, Phase 2) — ≥20 tests covering parse + estimate + inject + DoS cap + calibration.

**Cumulative target:** baseline 5038 → ~5188-5218 (+150-180 new tests) per PLAN-065 §10.1.

## Blast radius

- **Files touched (canonical):** `.claude/hooks/_lib/audit_emit.py` (Phase 2, shipped v1.12.0), `.claude/hooks/audit_log.py` (Phase 1), `.claude/hooks/check_plan_edit.py` (Phase 4-B), `.claude/hooks/check_budget.py` (Phase 5-D), `.claude/settings.json` (Layer A), `.claude/adr/ADR-098-ceo-boot-audit-emit-register.md` (this file), `.claude/adr/ADR-051-*.md` (Layer A amendment), SPEC/v1/audit-log.schema.md.
- **Files touched (non-canonical):** `.claude/scripts/ceo-boot.py` (Phase 3-rest wire), `.claude/scripts/plan-tokens.py` (Phase 2 NEW), `.claude/plans/PLAN-SCHEMA.md` (Phase 4-D advisory), `docs/UNTRUSTED-FORK-REVIEW.md` (Phase 4-C NEW), `docs/OWNER-CEREMONY-CONTRACT.md` (Phase 5-B v2), helper scripts moved to `scripts/local/historical/` (Phase 5-E), tests + fixtures.
- **Adopter-facing:** zero breaking. SPEC additive; settings matcher regex broadening adds intercept of mcp__* with no-op for non-canonical paths. Existing Edit/Write/MultiEdit tool calls unchanged.
- **Migration cost:** zero. Action discovery is at consumer side via `_KNOWN_ACTIONS`; existing consumers (`audit-query.py`, `audit-tokens.py`) are pattern-agnostic over the `action` discriminator.

## References

- PLAN-065 §Phase 1 / §Phase 2 / §Phase 3 / §Phase 4-B / §Phase 5-D / §Phase 7-A
- ADR-005 (event-stream v2 typed actions) — registration pattern precedent
- ADR-051 (skill-reference threat model) — Layer A amendment target
- ADR-055 (HMAC chain) — automatic per-event chain fields
- ADR-080 / SEC-P0-04 (audit-tokens content-ban allowlist) — Sec MF-3 enforcement pattern precedent
- ADR-082 (mitigated dispatch) — explains Format-A inline regex obsolescence (Phase 1 motivation)
- ADR-093 (per-plan ADR cap) — verifying ≤2 ADRs/plan compliance
- ADR-095 (calendar-gate retraction) — supersedes ADR-093 §moratorium
- ADR-097 (function-length-policy advisory permanent) — guard rails for ~+200 LoC additions
- ADR-101 (replay_redact + replay_capture_*) — most recent registration ceremony precedent (S81)
- ADR-103 (calendar-gate final purge) — supersedes ADR-093 §60-day-moratorium
- PLAN-070 (MCP introspection tools) — Layer B coordination
- PLAN-071 §Reality Ledger fixture #4 (declared-but-not-wired) — closure target
- feedback `custom_mcp_tools_governance_gap.md` (S81-tris) — Layer A motivation
