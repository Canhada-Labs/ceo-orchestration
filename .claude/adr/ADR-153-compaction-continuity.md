---
status: ACCEPTED
---

# ADR-153 — Compaction-continuity: PreCompact snapshot + PostCompact governance reinjection (H1)

- **Status:** ACCEPTED (S242, 2026-06-17 — both hooks registered in `.claude/settings.json` (`PreCompact`/`PostCompact`) with the two audit actions wired; Codex pair-rail satisfied at the PLAN-135 W2 merge `019ec0a1` + FOLLOWUP `019ec445`, re-confirmed Codex R-sweep thread `019ed788`)
- **Date:** 2026-06-13 (proposed) / 2026-06-17 (accepted, S242)
- **Enforcement commit:** `ab5114ab` (PLAN-135 W2 — `check_precompact_continuity.py` + `check_postcompact_reinject.py` + the `compaction_continuity_snapshot` / `compaction_context_reinjected` audit actions; hardened `26651bac`). Residual: live fires-proof (a real paid compaction emitting the events) remains PENDING-LIVE — an honest boundary, not a blocker.
- **Decision drivers:**
  - Harvest item **H1** (`HARVEST-REPORT.md` lines 48-49): "Compaction é a OUTRA forma de morte do estado de sessão (o closeout-guard cobre só Stop)." A 101-agent audit or any context-ceiling marathon collapses the transcript; the session-start governance reads (Gate-1: CLAUDE.md, PROTOCOL.md, team.md) and the active-PLAN/execution-unit position are summarized away, and the post-compaction model can silently drift off-protocol. This is a real class of protocol amnesia (Top-10 #5: "amnésia por compaction").
  - **The closeout-guard (S228) covers only `Stop`.** Compaction is a second, untracked death of session state. The fix mirrors the closeout-guard's shape — a fail-open advisory lifecycle hook — but on the compaction lifecycle pair.
  - **Doctrine 3** (PLAN-135 plan lines 73-78): "No setting, frontmatter field, or **hook event** is declared adopted until a live probe proves it changes behaviour / actually fires" (W0a `opts.model` was inert; S217: registered ≠ fires). `PreCompact`/`PostCompact` are NEW harness events — each ships with a fires-probe.

## Context

When the Claude Code harness compacts a long conversation it fires `PreCompact` (manual `/compact` or auto context-window threshold) and, after the summary lands, `PostCompact`. The post-compaction transcript no longer contains the literal Gate-1 reads or the running plan/execution-unit context — they were inputs to the summary, not preserved verbatim. For the ceo-orchestration meta-repo (where a single session can run a 101-agent audit), that means the CEO can resume after a compaction having "forgotten" which PLAN is active, where in the execution unit it was, and that an Owner-GPG ceremony was pending.

Two hooks close the gap:

1. **`PreCompact` — `check_precompact_continuity.py`** snapshots, BEFORE the transcript collapses, the governance state the summary would lose: the active `plan_id` (derived from the audit-log `plan_transition` events — never an env var, which is agent-spoofable: scratchpad_lib doctrine), the execution-unit position (the first unchecked `- [ ]` checkbox in the plan file — repo-relative path + line + label), the pending Owner-GPG ceremony flags (executable `finish-*.sh` newer than the last tag — the closeout-guard's own signal), and a READ-ONLY breadcrumb of the audit HMAC-chain anchor (last-hmac hex prefix + chain-length counter). The snapshot is written to the **plan-scoped scratchpad** (`_lib/scratchpad_lib` → `_lib/state_store`, ADR-027/ADR-034): plan-scoped, secrets-redacted, 64 KiB cap, `set`-overwrites.
2. **`PostCompact` — `check_postcompact_reinject.py`** reads that snapshot back and reinjects governance **POINTERS** via `hookSpecificOutput.additionalContext` so the model re-anchors on protocol.

## Decision drivers

- A compaction that erases protocol state is the same failure mode the closeout-guard addresses on `Stop`, on a different lifecycle edge — it earns the same fail-open advisory treatment.
- The snapshot must survive the compaction. The scratchpad is the only durable, plan-scoped, session-surviving state surface in the framework (the audit log is append-only and not keyed for retrieval; the transcript is exactly what compaction destroys).
- The reinjection payload is a prompt-injection surface: anything a `PostCompact` hook writes into `additionalContext` enters the model's context unconditionally. Disk-sourced strings (a plan label, a ceremony path) must never be injected as raw bodies.

## Options considered

- **Option A — PostCompact re-injects the FULL snapshot body (plan text, CLAUDE.md excerpt, ceremony script contents) into `additionalContext`.** Rejected: injecting raw file bodies into the model context is a prompt-injection surface (a malicious plan label or a crafted filename could carry instructions); it also bloats the just-compacted context, defeating the compaction. The hook should re-anchor, not re-inflate.
- **Option B — PreCompact snapshots to the plan scratchpad; PostCompact reinjects POINTERS ONLY (sanitized, clamped, bounded), telling the model WHERE to look, not WHAT the files say.** ADOPTED. The pointers-only doctrine below is the invariant.

## Decision

**The compaction-continuity pair.**

1. **PreCompact snapshots to the plan-scoped scratchpad.** `check_precompact_continuity.py` writes ONE JSON blob under the scratchpad key `compaction_continuity` (`set` overwrites the prior snapshot) containing: `plan_id`, `execution_unit` (`{plan_path, line, label}` — sanitized + clamped), `ceremony_flags` (sanitized repo-relative `finish-*.sh` paths, bounded to 5), and `hmac_chain` (`{chain_length, last_hmac_prefix}` — the HMAC anchor is READ-ONLY and only the first 12 hex chars of the last-hmac are kept: enough to detect a post-compaction chain divergence, not enough to be a forgery oracle). The plan-id is derived from the audit-log `plan_transition` events via `scratchpad_lib.resolve_plan_id` — NEVER from an env var (agent-spoofable, consensus M2). The HMAC-sidecar reads respect the audit filelock (best-effort; a one-event race on an advisory anchor is harmless).

2. **PostCompact reinjects POINTERS ONLY (pointers-only doctrine — NORMATIVE).** `check_postcompact_reinject.py` reads the snapshot and emits `hookSpecificOutput.additionalContext` carrying a bounded (≤9) list of governance POINTERS: a durable Gate-1 re-read reminder (always present), the active PLAN id, the execution-unit position, the pending-ceremony breadcrumbs, the HMAC anchor (integrity reference only), and the scratchpad address for the full detail. It NEVER injects file CONTENTS (plan body, CLAUDE.md text, a ceremony script's body) — that is the Option-A injection surface. Every value is sanitized to printable-ASCII + clamped (the closeout-guard `_sanitize_path` hardening, Codex S228 P0). The model is told WHERE to look, not WHAT the files say.

3. **Closed-enum audit, never the body.** PreCompact emits ONE `compaction_continuity_snapshot` (caller fields: `trigger` ∈ {manual, auto, other}, `plan_id` PLAN-NNN-or-`unknown`, `chain_length` clamped int, `snapshot_outcome` ∈ {written, scratchpad_unavailable, error, other}). PostCompact emits ONE `compaction_context_reinjected` (caller fields: `plan_id`, `snapshot_found` bool, `snapshot_age_s` clamped int, `pointer_count` 0..9). Both route through dedicated deny-by-default scrub branches + per-action allowlists (`_COMPACTION_CONTINUITY_SNAPSHOT_ALLOWLIST` / `_COMPACTION_CONTEXT_REINJECTED_ALLOWLIST`), NEVER `_EMIT_GENERIC_PASSTHROUGH`. The snapshot body and the reinjected pointer TEXT are NEVER on the audit wire — the wire carries closed enums + counters only.

**Fail-open §5 everywhere.** Both hooks are ADVISORY and fail-open: a parse error, a plan-id derivation failure, a missing scratchpad, or a budget-blown subprocess emits a stderr breadcrumb + `{}` and never blocks a compaction. A crashed snapshot must not stop the harness from compacting. **Kill-switch:** `CEO_COMPACTION_CONTINUITY=0` disables both halves.

## H2 coverage boundary

The H2 ConfigChange guard (`.claude/hooks/check_config_change.py`) audits and
advisory-blocks out-of-band `settings.json` tamper — the class S197 proved is
invisible to the rail (settings/config is not canonical-guarded; an edit to
`settings.local.json` left no trace). H2 resolves the multi-layer settings via
the shared `_lib/effective_config` resolver (the same FORBIDDEN-KEYS single
source W1 S3 uses) and, on a `ConfigChange` event, emits
`config_change_observed` on the benign path or `config_change_forbidden_key`
(one per tamper class) with a `{"decision":"block",...}` decision on the
forbidden-key path, so the operator sees the tamper at the moment of the edit
rather than only at the next boot.

**The honest limitation (debate R1 — stated here, not buried).** H2 is itself
a hook, and a governance hook has two structural blind spots that no amount of
hook logic can close:

1. **Self-disarm.** `disableAllHooks` is precisely one of the forbidden keys
   H2 polices — but once that key lands in any settings layer, *no* further
   `ConfigChange` hook runs. A single same-session edit that sets
   `disableAllHooks: true` can therefore slip past H2 if the harness applies
   the disarm before re-dispatching the event. H2 catches the *first* such
   edit it observes; it cannot catch the one that disarms it.
2. **Outside-harness blindness.** A text editor (or any non-Claude process)
   writing a settings file on disk fires no `ConfigChange` event at all. H2
   only ever sees changes that flow through the harness.

**This is by design, not a defect to fix in W2.** H2 is a near-real-time
*detector* of in-harness config tamper, not a *guarantee* of config
integrity. The named compensators are independent channels that close the
window H2 cannot:

- **S3 boot tripwires** (W1 — `/ceo-boot` `check_settings_tamper_tripwires`):
  on the NEXT boot, S3 re-scans the RESOLVED multi-layer settings (including
  the gitignored, sentinel-blind `settings.local.json`) plus the import-time
  env snapshot, using the same `_lib/effective_config` classifier. Anything
  H2's same-session window missed — including an edit that disarmed H2 itself
  — surfaces at the next session start. S3 is advisory and fires next boot, so
  there is a same-session lag, but the tamper does not stay hidden.
- **W5 O10 OTEL hook-execution witness** (PENDING — cut-2 risk): an
  out-of-band record that a hook actually ran, independent of the hook's own
  fail-open emit. O10 is the channel that detects the degraded-rail state
  (hooks present on disk but not executing) that the self-disarm produces.
  Until O10 lands, the same-session disarm window is real and documented.

**Surface scope (narrower than S3, deliberately).** H2 block-scopes only the
settings-FILE surfaces a `ConfigChange` event represents — the `user` /
`project` / `local` / `managed` layers. The process-`env` snapshot and the
on-disk hook census are S3's boot surfaces, not a settings-file change, so H2
treats env/census findings as observe-only and never blocks on them (a
settings layer's *own* `env` block IS a settings-file change and IS in scope,
classified under that layer's name). This keeps H2's block authority tied
exactly to what a `ConfigChange` event means, and avoids H2 and S3 fighting
over the same finding at different lifecycle moments.

**Audit faithfulness.** Both `config_change_observed` and
`config_change_forbidden_key` route through their dedicated deny-by-default
`_scrub_` branch + per-action allowlist in `audit_emit` (NEVER
`_EMIT_GENERIC_PASSTHROUGH`). The changed file's PATH and BODY, any settings
key or value (an attacker endpoint URL, an off-allowlist model id, an
`apiKeyHelper` path, a dangerously-flag value), and the `effective_config`
finding DETAIL string are NEVER persisted on the audit wire; only the
closed-enum `tamper_class` + `layer` + a clamped integer `finding_count`
travel. The block decision's `reason` likewise names the tamper CLASS and
LAYER only — never the finding detail — so the detail cannot leak through the
decision channel the operator's terminal echoes. The same no-value-echo
contract as `settings_tamper_detected`
([[feedback-closed-enum-breadcrumb-must-not-echo-rejected-value]]).

**Fail-open.** Every infra condition (resolver unavailable, classify failure,
malformed stdin, missing settings) fails toward `{}` (allow) with a stderr
breadcrumb — H2 NEVER manufactures a spurious block from an infra error. The
only non-empty decision H2 ever returns is the forbidden-key block on a real,
classified finding. Kill-switch: `CEO_CONFIG_CHANGE_GUARD=0`.

Recorded in `THREAT-MODEL-WORKSHEET.md` §2 and `HONEST-LIMITATIONS`.

## Consequences

- **(+)** Protocol amnesia by compaction closes: after any compaction the model is re-anchored on the active PLAN, the execution-unit position, the Gate-1 reads, and any pending Owner ceremony — without re-inflating the just-compacted context.
- **(+)** Native-under-rail (Doctrine 1): the compaction lifecycle (a harness-native event) becomes a governance surface UNDER the hook rail; no native control is retired.
- **(+)** Two NEW closed-enum actions (`compaction_continuity_snapshot` + `compaction_context_reinjected`) carry closed enums + counters only — the snapshot body and the reinjected pointers never reach the audit wire.
- **(−)** Two NEW hook files (`check_precompact_continuity.py`, `check_postcompact_reinject.py`) + two NEW harness events registered in BOTH settings surfaces (dual-merge parity, S228) + 2 new actions (count consolidation: shared W2 count/SHA pins) + the SPEC v2.43 rows. The CLAUDE.md hook-count doc gates move (`48 Python hook scripts` → +2; `39 registered hooks` → +2) at closeout.
- **(~)** `PreCompact`/`PostCompact` are now live governance surfaces. The `additionalContext` reinjection is bounded by the pointers-only doctrine; widening it to inject any file body requires amending this ADR.

## Residual risks

- **Fires-proof is PENDING-LIVE.** Auto-compaction is hard to force offline and a real `claude -p` compaction cycle is a paid action; the `$0` `probe_hook_events_fire.py` proves the breadcrumb-assert harness MECHANICS but not that the installed CLI actually emits `PreCompact`/`PostCompact`. The real per-event fire-assert is the W2 ceremony rehearsal (the printed recipe). This is the honest boundary of a $0 probe and is exactly the Doctrine 3 "registered ≠ fires" risk H1 flags but cannot itself retire at $0.
- **Snapshot staleness.** A snapshot from a prior session (same plan scope) could be read post-compaction in a new session. PostCompact records `snapshot_age_s` and flags a >12h snapshot as possibly-stale in the reinjected pointers; the operator verifies plan state before relying on the unit pointer. The durable Gate-1 reminder is always reinjected regardless.
- **Plan-id derivation can fail.** If the session has no `plan_transition` event yet, `plan_id` resolves to `unknown`, the scratchpad write is skipped (no plan scope to write into), and `snapshot_outcome=scratchpad_unavailable` / PostCompact `snapshot_found=False` — but the durable Gate-1 pointer is still reinjected. Fail-open by design.
- **§H2 disarm window** (shared, above): a hook is disarmed by `disableAllHooks`; compensators are the S3 boot tripwires + the W5 O10 OTEL witness.

## Blast radius

L3+ — introduces two NEW harness lifecycle events (`PreCompact`, `PostCompact`) to the governance rail, two NEW closed-enum audit actions, and a NEW prompt-injection-bearing output channel (`additionalContext` reinjection, bounded by the pointers-only doctrine). Codex pair-rail review is mandatory for this unit (PLAN-135 plan line 622: "V2 Codex pair-rail (mandatory for W2 hooks)").
