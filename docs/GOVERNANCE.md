# GOVERNANCE — what ceo-orchestration enforces, and what it doesn't

> **PLAN-059 Phase 3 D4 deliverable.** Documents what the framework's
> governance layer enforces by hook/sentinel discipline + what
> kill-switches adopters can flip + what cannot be turned off.

## Scope

ceo-orchestration is the most opinionated **Claude-only** orchestrator
available (per ADR-085). Governance is enforced via four mechanisms:

1. **Hooks** — Python scripts running PreToolUse/PostToolUse/
   SessionStart/SessionEnd/UserPromptSubmit; can decide=block.
2. **Sentinels** — Owner-signed `.asc` files that unlock canonical
   path edits.
3. **Audit log** — append-only JSONL with HMAC chain (ADR-055)
   capturing every governance event.
4. **Skill protocol** — every named-agent spawn carries
   `## SKILL CONTENT` or `## SKILL REFERENCE` per the spawn protocol.

This document enumerates what each mechanism does, what env-vars
revert each mechanism, and what is structurally NOT revertible.

## What CANNOT be turned off (frozen invariants)

These are **structural** — no env-var, no kill-switch, no setting
overrides them. To change behavior, the framework code itself must
change (via Owner-signed canonical edit).

### 1. VETO floor model assignment (ADR-052)

The Staff Code Reviewer + Principal Security Engineer archetypes
**always run on Opus 4.8** regardless of:

- `CEO_MODEL_DOWNSHIFT=1` setting
- `tier-policy.json` `default_model` field
- Per-call `--model=` flag
- Adopter project overrides

The pin lives in the spawn-protocol template + `team.md` SKILL MAP
(canonical-guarded). Bypass requires editing those files, which
requires Owner sentinel.

**Why frozen:** these archetypes hold merge VETO + auth/crypto VETO.
Downshifting them risks silently weakening the gate.

### 2. Canonical-edit sentinel discipline (ADR-031 / ADR-010)

Every edit to a canonical-guarded path requires an Owner-signed
`approved.md` sentinel with the path declared in `Scope:`. There
is **no env-var bypass**. The kernel-override path (`CEO_KERNEL_
OVERRIDE=<reason-slug> CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT`) emits
an unsuppressable `veto_triggered` audit event with
`reason_code=kernel_override_used` (event itself cannot be silenced).

**Why frozen:** if the gate could be silenced, a compromised hook
could edit itself out of the guard list.

### 3. Kernel-override audit emit (ADR-031 §kernel-override)

Even when `CEO_KERNEL_OVERRIDE` fires (legitimate emergency bypass),
the framework **emits an audit event** that cannot be suppressed.
This means every override leaves a forensic trail.

**Why frozen:** silent bypass = no accountability. The event is the
accountability.

### 4. Framework Claude-only positioning (ADR-085)

ceo-orchestration ships **only** the Claude (Anthropic SDK) adapter.
Multi-LLM expansion was REFUSED via ADR-084. There is no env-var
that switches the framework into multi-LLM mode.

**Why frozen:** strategic positioning decision. To run a non-Claude
LLM, use a different orchestrator (CrewAI, LangGraph, Portkey, etc.).

## What CAN be turned off (kill-switches)

Each entry: env-var → effect → why-and-when-to-use.

### Hook kill-switches

| Env-var | Effect | When to use |
|---|---|---|
| `CEO_MITIGATION_DISABLE=1` | Forces native dispatch rail for ALL archetypes (reverts ADR-082 default-on for non-cr) | Emergency rollback if sub-agent fabrication observed in prod |
| `CEO_MCP_SCANNER_DISABLE=1` | Disables MCP injection scanner PostToolUse hook (ADR-083) | If false-positive blocks a legitimate MCP tool call (advisory mode currently — should not block, but emergency lever) |
| `CEO_OUTPUT_SAFETY_MODE=allow` | Switches output-safety from `redact` to `flag` mode (advisory only) | Forensic mode where redaction would obscure investigation |
| `CEO_OUTPUT_SCAN=0` | Master kill for ADR-057 output-scan family | Migration windows |
| `CEO_OUTPUT_SCAN_UNICODE=0` | Disables unicode-injection family only | If false-positive on legitimate bidi text |
| `CEO_OUTPUT_SCAN_TELEMETRY=0` | Disables telemetry-string family only | Adopters with internal telemetry strings |
| `CEO_OUTPUT_SCAN_LLM10=0` | Disables OWASP LLM10 family only | Migration windows |
| `CEO_WEBFETCH_INJECTION_SCAN=0` | Disables WebFetch/WebSearch hook (ADR-077) | Emergency only |
| `CEO_AUDIT_HMAC_DISABLE=1` | **Disables HMAC chain** | **NOT RECOMMENDED** — see SEC-P0-06 for forensic implications |
| `CEO_FLUENCY_NUDGE=0` | Disables Artifact Paradox SubagentStop advisory | Adopter doesn't want fluency advisories |
| `CEO_SKILL_READ_V2=0` | Disables PLAN-045 Wave 5 F-10-07 v2 TOCTOU detection | Migration windows |
| `CEO_LESSON_RANKING_MODE=effectiveness` | Switches lesson ranking from recency to effectiveness | Sprint 10+ default candidate (ADR-019) |
| `CEO_SOTA_DISABLE=1` | Master kill for SOTA features (skill retrieval, format-B reference, etc.) | Adopter migration |

### Behavioral kill-switches (ADR-082 / ADR-090)

| Env-var | Effect | When to use |
|---|---|---|
| `CEO_DISPATCHER_MODE=native\|mitigated` | Per-session override of ADR-082 archetype default | Diagnostic mode for sub-agent comparison |
| `CEO_SKILL_REFERENCE_MODE=0` | Forces Format A inline (reverts ADR-090 #1 Format B default) | Adopter migration |
| `CEO_TIER_POLICY_ENABLE=0` | Reverts to manual model override mode (reverts ADR-090 #2) | Debug |
| `CEO_BRAINSTORM_GATE=0` | Reverts to CEO-directed brainstorm (reverts ADR-090 #3) | Debug |
| `CEO_SCRATCHPAD_DEFAULT=0` | Reverts to opt-in scratchpad (reverts ADR-090 #5) | Debug |
| `CEO_AUDIT_TOKENS_AUTO=0` | Disables auto-run audit-tokens at SessionEnd (reverts ADR-090 #6) | Performance-sensitive workflows |
| `CEO_MODEL_DOWNSHIFT=0` | **STATUS DEFERRED** (audit-v2 C3-P0-04). Documented as a kill-switch for the candidate Sonnet-default-with-Opus-upgrade routing rule (`docs/CEO-MODEL-ROUTING.md`), but **no runtime read of this env-var ships at v1.11.0**. Enforcement awaits PLAN-048 Phase 2. Setting it has **no effect** today. Treat the doc as pre-implementation design intent, not active governance | When PLAN-048 Phase 2 lands, this will revert that experiment to Opus-always for the CEO orchestrator |
| `CEO_CONFIDENCE_BYPASS=1` | Session-scoped escape hatch for confidence gate (ADR-019) | Owner-only emergency |
| `CEO_CONFIDENCE_ENFORCE=1` | Switches confidence gate from advisory to blocking | Owner-only adoption |

### Diagnostic kill-switches

| Env-var | Effect | When to use |
|---|---|---|
| `CEO_KERNEL_OVERRIDE=<slug> CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT` | Bypasses kernel hard-deny on hook self-edit; **emits audit event** | Owner-only emergency edit of governance hooks themselves |
| `CEO_EXTENDED_LIFECYCLE=0` | Disables PLAN-028 lifecycle hooks (SessionStart/SessionEnd) | Migration windows |
| `CEO_DEBUG=1` | Verbose hook breadcrumb output to stderr | Debug only |
| `CEO_HOOK_PYTHON_FAIL_OPEN=1` | Forces hooks to fail-open (allow tool call) on Python infrastructure errors instead of fail-closed (block) | Last-resort recovery if a hook bug breaks every session; never use in security-sensitive paths |
| `CEO_HOOKS_DISABLE=1` | **Master kill** — turns off all PreToolUse/PostToolUse hooks | Migration windows only — strips ALL governance |
| `CEO_CANONICAL_GUARD_DISABLE=1` | Disables `check_canonical_edit.py` sentinel guard | Owner-only emergency; sentinel is the defense-in-depth layer above CODEOWNERS |
| `CEO_FORMAL_VERIFY_DISABLE=1` | Disables formal-verification guards (TLA+ conformance harness paths) | Disabled by default in adopter installs |
| `CEO_PROMPT_INJECTION_SCAN=0` | Disables UserPromptSubmit injection-prefix hash check (PLAN-058 C-P0-06) | Migration if false positives bite |
| `CEO_READ_INJECTION_SCAN=0` | Disables `check_read_injection.py` PostToolUse Read scan (ADR-077) | Forensic-only; blocks WebFetch/Read injection vectors |
| `CEO_SUBAGENT_FABRICATION=0` | Disables fabrication-detection forensic emit (PLAN-059) | Removes ledger entries; not recommended |
| `CEO_SUBAGENT_FABRICATION_BLOCK=1` | **Switches fabrication detection from observe-only to BLOCK mode** (ADR-080 not yet activated by default) | Only after Layer 4 root-cause matrix completes; would block dispatches with fabricated tool-call artifacts |

### Activation switches (off-by-default opt-in features)

These features are **OFF by default** and require explicit activation by the Owner. Once activated they should remain on for the session — toggling mid-session can leave artifacts in inconsistent state.

| Env-var | Effect | When to use |
|---|---|---|
| `CEO_SWARM=1` | Activates autonomous-loop swarm coordinator (`.claude/scripts/swarm/coordinator.py`) | Explorable solution-space tasks (test speed, bundle size, prompt iteration). See `docs/AUTONOMOUS-LOOP-GUIDE.md`. Off-by-default per `ceo-orchestration` skill §Autonomous-loop parallelism |
| `CEO_TOURNAMENT_ENABLE=1` | Activates best-of-N tournament scorer for swarm outputs (`.claude/scripts/swarm/tournament.py`) | Pair with `CEO_SWARM=1` when promoting one of N variants |
| `CEO_AUTONOMOUS_LOOPS_DISABLE=1` | Hard-disables autonomous-loop scheduling regardless of `CEO_SWARM` | Emergency stop / safe-mode |
| `CEO_RAG_BRIDGE_ENABLE=1` | Activates LightRAG sidecar bridge (ADR-062) | Adopter has installed RAG sidecar (`docs/INSTALL-RAG.md`); off otherwise |
| `CEO_RAG_SIDECAR=1` | Internal: marks process as RAG sidecar instance | Set automatically by `scripts/rag/start-sidecar.sh`; do not set manually |
| `CEO_OTEL_EMIT=1` | Activates OTLP cost-stream emit (ADR-061) | Adopter has OTLP collector ready and `CEO_OTEL_ENDPOINT` set |
| `CEO_TWO_PASS_REVIEW=1` | Activates 2-pass code-review (Sonnet first, Opus second) | Cost-sensitive code review; off-by-default. See `docs/CEO-MODEL-ROUTING.md` |
| `CEO_RED_TEAM_DISABLE=1` | Inverse activation — disables Red-Team archetype contingent spawn (M1 anti-groupthink gate) | Migration if Red-Team output is unwanted noise; on-by-default |
| `CEO_OPUS_SPOT_CHECK_P1=1` | Activates opt-in Opus spot-check on Sonnet code-review verdicts | Cost-sensitive but quality-conscious adopters |
| `CEO_MODEL_ROUTING=0` | **PLAN-078 Wave 1.** Disables model-routing telemetry advisory emit in `check_agent_spawn.py`. Default ON (telemetry-only; never blocks). The hook still enforces the VETO floor regardless | Adopter wants to silence the `model_routing_advised` audit-log channel during a migration window |
| `CEO_REALITY_LEDGER_DETECTOR_07=0` | **PLAN-078 Wave 2.** Disables Reality Ledger detector #7 (estimate-drift). Default ON. Detector emits `estimate_drift_detected` events on plan close-outs; never blocks | Migration windows when calibration CSV is being rebuilt or detector is misfiring |
| `CEO_BOOT_AUTO_TASK=0` | **PLAN-078 Wave 5.** Disables `<!-- TASKCREATE-CANDIDATE -->` marker emit in `.claude/scripts/ceo-boot.py`. Default ON (markers print only when `gate_pass=False` AND severity≥medium AND not `--short`/`--cached`/`--json`). The 15 Tier-S digest + recommendations engine still print; only the marker blocks (and `ceo_boot_task_candidate_emitted` audit events + dedup state-file writes) are suppressed | Adopter wants /ceo-boot output without auto-task orchestration; or a noisy run is filling the task list during a migration |
| `CEO_BOOT_TASK_STATE_PATH=<path>` | **PLAN-078 Wave 5.** Override dedup state-file location (default: `~/.claude/projects/<project>/state/ceo-boot-tasks-emitted.json`). 24h TTL, filelock-guarded, bounded ≤256 entries (LRU evict) | Tests + adopter installs that want the state file under a custom XDG dir |

### Budget / Cost controls

These envs control how the framework spends API tokens and dollars. **Adopter-critical**: misconfigured budgets can let an autonomous session burn unbounded tokens.

| Env-var | Default | Effect | When to override |
|---|---|---|---|
| `CEO_BUDGET_ENFORCE=1` | off | Activates budget enforcement at spawn-time (blocks spawn if projected cost > cap) | After establishing baseline session cost (~50k for short, ~500k for long) |
| `CEO_BUDGET_BYPASS=1` | off | Per-session escape hatch when budget enforcement blocks legitimate work | Emergency only; logged in audit |
| `CEO_BUDGET_BYPASS_MAX_PER_DAY=N` | 3 | Cap on bypasses per UTC day | Tighten to 1 in production-like adopter installs |
| `CEO_BUDGET_PER_SPAWN=<USD>` | unset | Hard cap per individual spawn | Set to e.g. `0.25` to block accidental Opus mega-spawns |
| `CEO_DISPATCH_COST_CAP=<USD>` | unset | Cap per dispatch chain (CEO + 1 sub-agent) | Set to e.g. `2.00` for typical L3 task |
| `CEO_TOURNAMENT_BUDGET_USD=<USD>` | unset | Total tournament cost cap (sum across N variants) | Required when activating `CEO_TOURNAMENT_ENABLE` |
| `CEO_TOURNAMENT_ABORT_MULTIPLIER=N` | 2 | Abort tournament if running cost exceeds budget × N | Tighten to 1.5 for risk-averse adopters |
| `CEO_TOURNAMENT_CUMULATIVE_MULTIPLIER=N` | 5 | Total cumulative tournament-cost cap (across all tournaments in session) | Tighten if running many short tournaments |
| `CEO_MAX_PLAN_TOKENS=N` | unset | Cap on plan size before warning | Set to e.g. `200000` to surface excessively-large plans |
| `CEO_MAX_SPAWN_TOKENS=N` | unset | Cap on spawn prompt size | Set to e.g. `100000` to surface bloated prompts |
| `CEO_MAX_PROMOTE_DELTA_USD=<USD>` | unset | Cap on tier-policy promotion delta | Owner-physical signoff workflow |

### Path / Storage overrides

These envs let adopters relocate state away from default `~/.claude/projects/<slug>/` for compliance, multi-tenancy, or testing.

| Env-var | Default | Effect | When to override |
|---|---|---|---|
| `CEO_PROJECT_STATE_DIR=<path>` | `~/.claude/projects/<slug>/` | Root state dir for session graphs, audit log, lessons | Adopter wants per-tenant isolation OR ephemeral test runs |
| `CEO_AUDIT_LOG_DIR=<path>` | `<state>/audit/` | Audit log directory | Compliance requires separate retention path |
| `CEO_AUDIT_LOG_PATH=<file>` | `<audit-dir>/audit-log.jsonl` | Direct file path override | Useful for `tail -f` from a fixed location |
| `CEO_AUDIT_LOG_ROTATE_BYTES=N` | 10000000 (10 MB) | Triggers rotation when log exceeds size | Tighten in low-disk environments |
| `CEO_AUDIT_KEY_PATH=<file>` | `<state>/audit_hmac.key` | HMAC chain signing key location | Hardware security module / vault integration |
| `CEO_AUDIT_LAST_HMAC_PATH=<file>` | `<state>/audit_last.hmac` | Persists last chain HMAC (verify_chain anchor) | Move to read-only mount during audit |
| `CEO_PLANS_DIR=<path>` | `.claude/plans/` | Plans directory override | Multi-repo plan reuse |
| `CEO_LESSONS_DIR=<path>` | `<state>/lessons/` | Lessons directory override | Cross-project lesson-sharing experiments |
| `CEO_SESSION_GRAPH_DIR=<path>` | `<state>/sessions/` | Session graph dir override | Long-term forensic archive separation |
| `CEO_PRICING_PATH=<file>` | `.claude/pricing.json` | Override of model pricing JSON | Test economy with experimental pricing |
| `CEO_MEMORY_SHARED_PATH=<path>` | `<state>/memory_shared/` | Inter-agent shared scratchpad path | Multi-orchestrator setups |

## Per-feature governance map

### Spawn governance (PreToolUse Agent)

- **Hook:** `check_agent_spawn.py`
- **What it blocks:** Agent tool calls with named-agent description
  but missing `## SKILL CONTENT` (or `## SKILL REFERENCE` per ADR-051).
- **Audit emit:** `agent_spawn` (PostToolUse) with archetype +
  skill_slug + model + tier_id + cost projection.
- **Kill-switch:** None (frozen — would defeat the purpose).
- **Override:** `inject-agent-context.sh` is the canonical builder;
  `/spawn` slash command is the safe entry point.

### Bash safety (PreToolUse Bash)

- **Hook:** `check_bash_safety.py`
- **What it blocks:** Destructive commands (`rm -rf`, `git reset
  --hard`, `git push --force`) without `dangerouslyDisableSandbox`
  override.
- **Audit emit:** `veto_triggered` with reason_code on block.
- **Kill-switch:** Per-call `dangerouslyDisableSandbox: true` in
  Bash tool input (Owner-only convention).

### Plan-edit guard (PreToolUse Edit/Write/MultiEdit)

- **Hook:** `check_plan_edit.py`
- **What it blocks:** Edits to plans in `done` or `refused` state
  without explicit re-open marker.
- **Audit emit:** `plan_transition` events on every status flip.
- **Kill-switch:** None (frozen — preserves plan lifecycle integrity).

### Canonical-edit guard (PreToolUse Edit/Write/MultiEdit)

- **Hook:** `check_canonical_edit.py`
- **What it blocks:** Edits to canonical-guarded paths without
  matching Owner-signed sentinel.
- **Audit emit:** `veto_triggered` on block.
- **Kill-switch:** None (frozen — see §1 above).

### Read-injection guard (PreToolUse Read)

- **Hook:** `check_read_injection.py`
- **What it blocks:** Read calls returning content with detected
  injection patterns (per `_lib/injection_patterns.py` 4 families).
- **Audit emit:** `injection_flag` event.
- **Kill-switch:** Per-family kill via `CEO_OUTPUT_SCAN_*=0`.

### Audit log (PostToolUse all tools)

- **Hook:** `audit_log.py`
- **What it does:** Records every tool call (post-redaction) to
  `audit-log.jsonl` with HMAC chain.
- **Kill-switch:** `CEO_AUDIT_HMAC_DISABLE=1` disables chain (not
  recommended — forensic gap).

### Output safety (PostToolUse all tools)

- **Hook:** `output_scan.py` + `secret_patterns.py`
- **What it does:** Scans tool responses for PII / secrets / OWASP
  LLM Top 10 patterns; redacts inline when `CEO_OUTPUT_SAFETY_MODE=
  redact`, flags only when `flag`.
- **Kill-switch:** `CEO_OUTPUT_SAFETY_MODE=allow` (forensic mode);
  `CEO_OUTPUT_SCAN=0` (master kill).

### MCP injection scanner (PostToolUse mcp__.*)

- **Hook:** `check_mcp_response.py` (PLAN-052 / ADR-083)
- **What it does:** Scans MCP tool responses for harness-mimicry +
  directive-prose patterns; emits `mcp_injection_finding` event.
- **Kill-switch:** `CEO_MCP_SCANNER_DISABLE=1`.
- **Mode:** ADVISORY only in v1; STRICT mode deferred to Phase 2.

### Skill bootstrap TOCTOU (PostToolUse Read)

- **Hook:** `check_skill_bootstrap_post.py` + `check_skill_reference_read.py`
- **What it does:** Detects mismatch between spawn-time SKILL.md
  hash pin + sub-agent post-spawn Read content.
- **Audit emit:** `skill_reference_read_*` events.
- **Kill-switch:** `CEO_SKILL_READ_V2=0`.

### Lifecycle hooks (SessionStart / SessionEnd)

- **Hook:** `SessionStart.py`, `SessionEnd.py`
- **What they do:** Audit init + Gate-1 cache warmup at start;
  audit-tokens stub run + closeout breadcrumb at end (per ADR-085).
- **Kill-switch:** `CEO_EXTENDED_LIFECYCLE=0`.

## How to verify your install

```bash
# Health check
python3 .claude/scripts/ceo-diagnose.py

# Verify governance state
bash .claude/scripts/validate-governance.sh

# Verify HMAC chain integrity
python3 .claude/scripts/audit-verify-chain.py

# Audit log telemetry
python3 .claude/scripts/audit-telemetry.py --window 7d

# Claude SDK compat
bash .claude/scripts/check-sdk-compat.sh
```

## What changes during the soak window

When ADR-082 / ADR-083 / ADR-090 are PROPOSED (not yet ACCEPTED):

- Audit-telemetry monitors fabrication rate per archetype.
- Owner reviews `audit-telemetry.py --window 7d` data weekly.
- If `fabrication_rate_pct > 5%` for any archetype, the corresponding
  kill-switch is flipped instantly via env-var (no code change).
- After 7 days clean (per ADR-082) or 14 days clean (per ADR-083 /
  ADR-090), the ADR is amended PROPOSED → ACCEPTED with empirical
  data appended.

Per ADR-091, dogfood validation Phase 4 is deferred to passive
observation; kill-switch envs remain the rollback path.

## References

- ADR-010 — Sentinel discipline canonical
- ADR-031 — Canonical-edit sentinel + kernel-override
- ADR-052 — VETO floor model assignment
- ADR-055 — Audit-log HMAC chain
- ADR-077 — WebFetch injection precedent
- ADR-082 — L7c mitigation default-on
- ADR-083 — MCP injection scanner
- ADR-084 — Multi-adapter REFUSED (Claude-only)
- ADR-085 — Framework landscape Claude-only
- ADR-086 — Checkpointing REFUSED
- ADR-087 — OTel emit REFUSED
- ADR-088 — Guardrails-library REFUSED
- ADR-089 — PLAN-059 SEC-P0 cluster disposition
- ADR-090 — Framework activation defaults
- ADR-091 — Dogfood validation deferred
- `docs/STATE-RECOVERY.md` — companion (resume patterns)
- `docs/OBSERVABILITY.md` — companion (audit-log canonical)
- `docs/ceo-debt-grammar.md` — companion (the advisory `# CEO-DEBT:` inline-debt ledger grammar)
