# Substrate adoption record — Anthropic sweep 2026-08 (CC 2.1.220 + Claude 5 family)

> **Status: STAGED (PLAN-163 main-pack), not live.** Everything below ships
> only when the PLAN-163 gates land IN ORDER: **GATE-PIN (codex payload-pin
> ceremony) → GATE-V2 (fresh liveness proof under the new pin, post-pin
> anchored) → pack review (3-vendor pair-rail) → pack GPG ceremony.** Until
> then this document describes intent + staged artifacts, never live
> protection. **NO-SPEED-CLAIM:** nothing in this record claims framework
> throughput or speed; where the substrate CHANGELOG reports internal cost
> or latency changes, the only fact this framework inherits is "our own
> empirical baselines needed re-measurement" (and were re-measured — T4).

Substrate: Claude Code **2.1.220** (installed + probed 2026-07-28; ledger
was reconciled at 2.1.198). Model family: **Claude 5 complete** — Fable 5
(2026-06-09, already adopted for VETO roles), Sonnet 5 (2026-06-30, CC
default since 2.1.197), Opus 5 (2026-07-24). Companion CLIs: codex 0.144.6,
grok 0.2.106 (see T5 pin work).

## Ratified decisions (Owner tie-breaks, W0b S284 — literals)

| Key | Ratified literal |
|---|---|
| `availableModels` | `["claude-opus-4-8","claude-fable-5","claude-sonnet-4-6","claude-haiku-4-5","claude-opus-5","claude-sonnet-5"]` — new ids APPENDED at the end (order is byte-compared by the ADR-149 mirror test; first entry participates in default resolution) |
| `fallbackModel` | `["claude-opus-5"]` (OQ1=b — full refresh, no soak window) |
| `permissions.defaultMode` | `"manual"` |
| Routing | debate/arch → `claude-opus-5`; advisory tier → `claude-sonnet-5` (OQ2 = migrate now); `VETO_FLOOR_ALLOWED` += `claude-opus-5` — **`claude-fable-5` remains the VETO ceiling** |
| OQ3 | `CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH=1` pin (4 red-first probes recorded — see G5) |
| OQ4 | Agent teams **not adopted** — posture documented in §Agent teams below |
| OQ5 | (c) dogfood settings.json TURNS ON the fail-closed posture (`sandbox.network.strictAllowlist`, `disableAutoMode`, `defaultMode: "manual"`, `workflowSizeGuideline`; `sandbox.filesystem.disabled` evaluated against real flows with the decision documented); templates ship the same keys COMMENTED |
| OQ6 | Fast-mode guidance only (cost × latency trade-off, no speed numbers) — see `docs/ACCELERATORS.md` §Fast mode |

## Gap-matrix dispositions (G1–G17, executed/recorded state)

| # | Substrate change | Disposition | Evidence / record |
|---|------------------|-------------|-------------------|
| G1 | `claude-opus-5` default Opus in CC (2.1.219); $5/$25 drop-in; **separate rate-limit bucket** | ADOPT via ADR-149 amendment + generator regen + independent mirrors (T1) | Staged ADR-149/ADR-181; the separate quota bucket is recorded as a **compatibility/accounting fact only** — not a performance claim |
| G2 | `claude-sonnet-5` CC default (2.1.197); new tokenizer ~+30% tokens; intro pricing $2/$10 through 2026-08-31 (then $3/$15) | ADOPT, advisory tier migrates now (OQ2), T1.1 contingency held | See §Tokenizer note; rollup surfaces price the intro rate with the flip date in-row (audit-telemetry/ceo-cost/budget-summary, landed T1.5) |
| G3 | Opus 4.1 retires **2026-08-05**; fast mode removed from Opus 4.7 | FIX landed (T1.5 presence fix + T1.8 STALE_RE) | `test_model_fleet_presence.py` born-RED→GREEN; `scripts/tests/test-parity-stale-planted.sh` proves the `claude-opus-4-1` red path; live parity run PASS 2026-07-28 |
| G4 | Hook exit-2 blocks even with invalid stdout JSON (2.1.214) | ORACLE (T2) | `hook-stdout-schema-check` over the WIRED set derived from settings.json |
| G5 | Async subagents default (2.1.198); native caps 20 concurrent / 200 per session / nesting depth 3 | ADOPT+VERIFY (T4) | Depth probes verdict: `env-verbatim=sim; negação=funciona; hook-depth2=cobre` (`PLAN-163/probes/depth-probes.md`); pin=1 staged |
| G6 | Task tool `mode` ignored (2.1.212) | VERIFY — dead assumption DISCARDED with proof | `PLAN-163/probes/misc-probes.md` §1: spawn guard never read the param (0 hits) |
| G7 | New hook events `Notification` (2.1.198), `DirectoryAdded` (2.1.219) | ADOPT gated (T3; CF-9) | Blockability probe is a HARD GATE; see §Honest residuals (post-facto semantics, read gap) |
| G8 | New settings (`sandbox.network.strictAllowlist`, `sandbox.filesystem.disabled`, `workflowSizeGuideline`, `disableAutoMode`, `defaultMode: manual`) | ADOPT per OQ5(c) | Dogfood ON (fail-closed posture), templates commented; rollback documented in the pack |
| G9 | MCP tool calls >2min auto-background (2.1.212) | VERIFY — dormant, recorded | `PLAN-163/probes/misc-probes.md` §2: pair-rail invokes codex as subprocess CLI, never MCP; matchers stay as Layer-A defense; re-triage trigger noted if the rail ever migrates to MCP |
| G10 | `/code-review` runs as a background subagent (2.1.218) | DOC (doctrine) | See §/code-review doctrine below |
| G11 | Plugin shell-form `${user_config.*}` rejected (2.1.207) | SKIP (verified — no plugins) | Round-1 verification |
| G12 | CLI-internal cost changes (2.1.210/216/217) | RE-MEASURE own baselines — no changelog numbers inherited | `PLAN-163/probes/flock-2.1.220.md`: pre-registered protocol, ≥200 samples per level; decision = read-only fan-outs may run at 8, **staging fan-outs keep 6** (skill edit rides its own canonical rail) |
| G13 | codex 0.144.1→0.144.6; grok 0.2.93→0.2.106; launcher-sha ≠ payload-sha | FIX mechanism + enforcement + ceremony (T5.2, GATE-PIN) | `PLAN-163/probes/payload-sha-evidence.md`: native payload `80a3933d…` vs launcher `134063e1…`; manifest schema + verify-then-invoke staged |
| G14 | Agent teams / SendMessage native | EVALUATE → **NOT ADOPTED** (OQ4) | §Agent teams below |
| G15 | Fast mode Opus 5 / 4.8 ($10/$50) | DOC guidance (OQ6) | `docs/ACCELERATORS.md` §Fast mode; rollup rows landed so any spend is visible (`claude-opus-5-fast`) |
| G16 | Workflow `opts.model` was INERT (PLAN-134 W0a) | RE-VERIFY on 2.1.220 → **still INERT** | `PLAN-163/probes/g16-model-probe.md` (DEFINITIVE: meta.json records the requested override, journal shows all 29 turns on the session model); subprocess `claude -p --model <id>` remains the only working override; "if fixed → simplification" branch is MOOT |
| G17 | Agent SDK drift | REFRESH (T5.1) | `PLAN-163/probes/ledger-refresh-draft.md`: sdk-ts 0.3.220, sdk-py 0.2.128, claude_code 2.1.220, codex 0.144.6, grok 0.2.106 (+ grok `_PROBE_ARGV` registration); model-deprecations refresh recipe PENDING-OWNER (network-gated) |

## Settings-schema diff 2.1.202 → 2.1.220 (T2.2 artifact)

Artifacts: `.claude/plans/PLAN-163/probes/schema-diff-2.1.202-to-2.1.220.md`
(per-field diff, zod source carved from both binaries — not docs) +
`hook-schema-2.1.220.json` (full extraction, recipe + hashes in `_meta`;
staged data copy ships at `.claude/data/hook-schema-2.1.220.json`).
Provenance: 2.1.220 local install sha256 **`8addc857…`**; 2.1.202 baseline
re-fetched from npm (`@anthropic-ai/claude-code-darwin-arm64@2.1.202`,
binary sha256 `7414f707…`, `--version` verified).

**Dispositions of the 8 schema-dense wired hooks — ALL `IDENTICAL` 202→220**
except two additive input-field deltas:

| Hook event | 202→220 disposition |
|---|---|
| PreToolUse | identical (input + full `hookSpecificOutput` arm) |
| PostToolUse | identical (`duration_ms?` already in 202) |
| PostToolUseFailure | identical |
| UserPromptSubmit | **+`source?` enum** `[user,sdk,system,loop_wakeup,schedule_wakeup]` (optional, Anthropic-internal trial) — tolerate, do NOT depend on |
| Stop | identical |
| SubagentStop | identical |
| SessionStart | **`source` enum widened +`fork`** (`[startup,resume,clear,compact,fork]`) — fixtures updated to include `fork` |
| SessionEnd | identical |

No event removed; no field removed or re-typed; the common output schema and
the 20-arm `hookSpecificOutput` union are byte-equivalent after
minifier-rename normalization. PreCompact/PostCompact (wired, thin) identical.

**`enforceAvailableModels` (feeds the T1.1 contingency — CONFIRMED,
contingency TRIGGERED):** describe text verbatim-identical to 2.1.202;
runtime iterates `availableModels` in list order and the FIRST
allowed-AND-server-available entry wins default resolution (T5.4 pin-list
ordering is load-bearing); a no-survivor list warns and keeps the
unconstrained tier default (fail-open); the managed-policy fail-open
("refusing cascade-trust mode") exists UNCHANGED in 2.1.220. New in
2.1.220: the `model_access` entitlement joins as a second restriction
source (neutral for dogfood). ⇒ the session default model is pinned
explicitly in the SAME commit as the sonnet-5 working-set entry (ADR-181
§Contingency).

**Unknown-event-key tolerance (feeds T3.4 version-floor):** BOTH 2.1.202
and 2.1.220 ignore unknown hook-event keys — the loader deletes the key
with a warning (`Unknown hook event "<k>" was ignored…`) and all other
events/settings keep loading; invalidity is per-entry, never whole-file.
An adopter on 2.1.202–2.1.219 receiving a `DirectoryAdded` template key
gets a warning + no-op, not a failure. **Residual: the SUPPORT.md floor is
`>=2.0` and no 2.0.x binary was probed** — template emission of the new
events stays FEATURE-GATED per T3.4 (default OFF) until that probe or an
explicit floor bump.

**New-event shapes (T3):** `DirectoryAdded` (NEW in 2.1.220, absent in
202): base + `directory: string` (absolute path) + `source:
enum["slash_command","register_repo_root"]`; matcher matches `source`;
**blockability NO** — no `hookSpecificOutput` arm, `decision:"block"`
parses but no call site consumes it, and both call sites fire the hook
fire-and-forget AFTER the directory is registered ⇒ T3.1 takes the
notification-only branch (observer-writer + PreToolUse write-guard); the
hardblock-floor branch is dead on this substrate. `Notification`: present
and identical in BOTH versions (base + `message`, `title?`,
`notification_type`; matcher on `notification_type`; only output arm
`additionalContext?`) — safe to wire on any version ≥2.1.202.

## Tokenizer note (Sonnet 5 — budgets are NOT re-baselined here)

Sonnet 5 ships a new tokenizer measuring **~+30% tokens** on identical text
vs Sonnet 4.6. OQ2 migrated the advisory tier NOW, accepting that risk
explicitly: every shipped token budget (plan token bands, thinking-budget
cap tables, estimator outputs calibrated on the 4.6 tokenizer) is now
conservative-by-error on sonnet-5 surfaces. **Re-baselining shipped budgets
(`count_tokens` pass over the budget tables) is a FOLLOW-UP PLAN, not part
of PLAN-163.** Until it lands, treat sonnet-5 token-budget breaches within
~30% of a limit as suspected tokenizer drift, not behavior drift.

## /code-review doctrine (G10)

Since CC 2.1.218 the native `/code-review` command executes as a
**background subagent** inside the harness. Doctrine:

- The **cross-vendor pair-rail is unaffected**: it invokes codex as a
  subprocess CLI (`codex exec`), never through `/code-review`, never
  through MCP (G9 probe). Nothing about the V2 review rail changed.
- `/code-review` output is **same-vendor advisory** — the ADR-145 rule
  stands: a Claude reviewing a Claude never discharges the cross-model
  VETO. It may inform; it may not gate.
- Because it is a subagent, its spawns are subject to the same spawn
  governance (depth pin OQ3, audit emit) as any other Task dispatch.

## Agent teams / SendMessage — posture (G14, OQ4: NOT ADOPTED)

**Decision (Owner-ratified, S284): not adopted — peer-message governance is
not modeled.** The framework's control surfaces assume **hub-and-spoke CEO
dispatch**: every delegation crosses the spawn protocol (`## AGENT
PROFILE`/`## SKILL CONTENT`/`## FILE ASSIGNMENT`, `check_agent_spawn.py`),
and every agent boundary is an audit-emit point on the HMAC chain. Native
agent teams introduce **peer-to-peer SendMessage lanes** that cross no
spawn gate and no audit-emit point: an agent could receive instructions
from a peer that were never classified, never veto-checked, and never
recorded — an ungoverned instruction channel inside the governed perimeter.

Adopting would require, at minimum: a message-classification guard on the
SendMessage boundary, HMAC audit-emit per peer message, veto-floor
semantics for instruction-bearing messages, and a teams-aware fabrication
detector. None of that exists; until a plan builds it, teams stay off.

- **Enforcement status:** posture only (this document). No hook blocks
  SendMessage today — honest residual, matching the "document" disposition
  the Owner chose over "gate".
- **Re-visit trigger:** a concrete workload that needs peer messaging, OR
  the substrate making teams a default path for existing flows (either
  re-opens this as a plan with the guard list above as scope).

## OUT-OF-SCOPE (explicit, do not "fix" in review)

- **`opus-4-7-profiler-smoke` (validate.yml:1178) and
  `profile-opus-4-7.py` are NOT renamed.** They are required checks wired
  to branch protection by NAME; renaming them without coordinating the
  branch-protection rule breaks every PR. Rename is a coordinated
  follow-up, deliberately outside PLAN-163. (The stale-literal scan does
  not flag them: the file NAMES contain `opus-4-7` but not the
  `claude-opus-4-7` id pattern.)
- **model-deprecations.json content refresh** — PENDING-OWNER network
  recipe (`PLAN-163/probes/ledger-refresh-draft.md`); agents are
  no-network for canonical ledgers under ADR-136-AMEND-1.
- **Sonnet-5 budget re-baseline** — follow-up plan (§Tokenizer note).
- **Read-guard for added directory roots** — named residual of T3 (CF-9):
  the observer-writer + write-guard covers Edit|Write|MultiEdit only;
  Read/Grep/Glob under a foreign added root stays uncovered until the
  read-guard follow-up (recorded in the T3 ADR, not silenced).

## Honest residuals

1. **GATE-V2 evidence is post-pin anchored.** The liveness proof window is
   exclusively events timestamped AFTER the GATE-PIN signed commit — never
   the trailing 168h window (which would let pre-pin fail-opens block
   forever, or let natural expiry ≈2026-08-03 satisfy vacuously).
2. **DirectoryAdded is post-facto.** The event fires AFTER the root is
   added; even on the blockable branch there is a window where reads can
   occur before the deny. The T3 probe measures and records that window;
   the control is containment, **not** total exposure prevention.
3. **`enforceAvailableModels` harness fail-open.** The 2.1.202 record
   already noted managed-policy load failure disables model enforcement
   with a warning; the T2.2 diff RE-CONFIRMED it unchanged in 2.1.220
   (§Settings-schema diff above: fail-open on managed-policy load failure
   AND on a no-survivor `availableModels` list; `model_access` entitlement
   added as a second restriction source). The T1.1 contingency (explicit
   session default pin in the same commit) is therefore EXECUTED in this
   pack, not merely held.
4. **Fast-mode spend is API-billed.** The `claude-opus-5-fast` rollup rows
   make spend visible after the fact; nothing prevents the spend
   ex-ante — fast mode remains operator-deliberate (ACCELERATORS.md).

## Provenance

- Plan: `.claude/plans/PLAN-163-substrate-uplift.md` (debate 3×ADJUST→PROCEED;
  cross-vendor review to double APPROVE — codex 5 rounds, grok 4 rounds; W0b
  Owner tie-breaks S284).
- Probes: `.claude/plans/PLAN-163/probes/` (depth, flock, g16, misc G6/G9,
  payload-sha, ledger-refresh, pin-manifest draft).
- Live fixes already on the tree (non-canonical, red-first):
  `audit-telemetry.py` / `ceo-cost.py` / `budget-summary.py` /
  `cost-table.yaml` / detectors (T1.5) + `smoke-install-parity.sh` STALE_RE
  with planted positive control (T1.8).
- Staged (this pack): ADR-149 amendment, ADR-181, upgrade.sh migration,
  settings/templates, this document, ACCELERATORS.md §Fast mode,
  CEO-MODEL-ROUTING.md fleet update.
