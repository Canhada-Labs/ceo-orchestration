# ADR-136-AMEND-1 — Workflow-primitive adoption (ADOPT-CONFINED)

---
adr_id: ADR-136-AMEND-1
title: Workflow-primitive adoption — harness-native agent()/parallel()/pipeline() confined to read-only investigation
status: ACCEPTED
amends: ADR-136
proposed_at: 2026-05-29
proposed_by: CEO (PLAN-120-FOLLOWUP, finding E6-F1)
session_origin: S185
accepted_at: 2026-06-11
accepting_session: S228
authorization: Owner directive (PLAN-134 §OQ3 ratified as-is, confinement unchanged; W1 Owner-GPG ceremony commit)
promotion_note: Promoted S228 by Owner directive (PLAN-134 W1, finding E6-F7) — production Workflows S185/S223/S225/S227 already ran under this confinement.
risk_tier: A
debate_required: true
related_plans: [PLAN-120, PLAN-115, PLAN-110, PLAN-098, PLAN-134]
related_adrs: [ADR-126, ADR-132, ADR-136, ADR-141]
---

## §1 Scope

This amendment narrows ADR-136's blanket **SKIP** verdict. ADR-136 SKIPped
porting GitHub `spec-kit`'s YAML-driven *workflow engine* (the +2000-LoC
`EXECUTE_COMMAND` state machine with `state.json` / per-run `log.jsonl`). That
verdict stands for the engine.

It does **not**, however, govern the **harness-native** `agent()` /
`parallel()` / `pipeline()` primitives — these are properties of the Claude
Code CLI runtime, not framework code we would author or port. PLAN-120 §audit
(L769-783) confirms they are *not implemented anywhere in the
ceo-orchestration framework code*: `grep -rnE '(agent|parallel|pipeline)\(' .claude/hooks/ .claude/scripts/`
over non-test code returns ZERO matches to the bare harness API.

The doctrinal question this amendment adjudicates: **may we USE the
harness-native fan-out primitives, and under what confinement?**

## §2 Decision

**ACCEPTED: ADOPT-CONFINED.**

The harness-native `agent()` / `parallel()` / `pipeline()` primitives MAY be
used, **confined to read-only investigation / audit fan-out** (the exact shape
this PLAN-120 audit itself ran on — recon Workflow `wf_fa782ffb-8e5`, which
survived an internet outage via journal replay, and the main 101-sub-agent
audit Workflow `wf_dd23da15-f8a`).

They MUST NOT be used to drive canonical-edit dispatch, ceremony execution, or
any write/Owner-GPG/audit-emit path. Those remain strictly sequential, behind
the existing physical gates.

## §3 Why the ADR-136 SKIP objections do NOT apply to the harness primitives

Each ADR-136 objection maps to **applies-to-harness-native = NO**:

1. **"Auto-execution conflicts with VETO"** (ADR-136 §Decision.1, L44-50).
   That objection is about spec-kit `EXECUTE_COMMAND` *command chaining* across
   phases without human intervention. The harness primitive does not chain
   across the Owner-GPG gate: every canonical edit still requires the sentinel
   at `check_canonical_edit.py` and `/debate`-VETO per `PROTOCOL.md:119`.
   Read-only fan-out emits no canonical edits, so there is nothing for the VETO
   moat to defend against.
2. **"State persistence adds attack surface"** (ADR-136 §Decision.2, L51-55).
   That objection is about spec-kit's per-run `state.json` + `log.jsonl`
   forgery vectors. The harness primitive ships NO new in-repo state files; the
   canonical `audit-log.jsonl` remains the single source of truth behind
   `spool_writer.py`'s per-PID flock. Zero new forgery surface.
3. **"+2000 LoC + 30+ tests"** (ADR-136 §Decision.3, L56-58). That objection
   is about porting the engine. ADOPT-CONFINED ports ZERO LoC — the engine IS
   the CLI harness; we author nothing.

## §4 Confinement (the load-bearing invariants)

ADOPT-CONFINED is conditional on ALL of the following remaining in force:

- **§4.1 Read-only only.** `agent()` / `parallel()` / `pipeline()` are used
  ONLY for investigation / audit / recon fan-out. Any write, canonical-path
  edit, Owner-GPG ceremony, or `audit_emit` write path runs sequentially
  through the Owner-GPG sentinel (`check_canonical_edit.py`) and `/debate`-VETO
  (`PROTOCOL.md:119`). These gates are NOT bypassable by a fan-out child.
- **§4.2 Per-PID spool + ordered drain (HARD prerequisite).** Every fan-out
  child inherits a subprocess-isolated `CEO_AUDIT_LOG_DIR` and writes only to
  its own per-PID spool. The ordered drain (`spool_writer.py drain_now()`) is
  the single serialization point; no concurrent writer ever contends on the
  canonical chain. The S183 WS-D1 `_origin` test-spool quarantine stamp keeps
  fan-out children from polluting the live chain. (Note: S185 observed that a
  large Workflow run *inside the dev session* still pollutes the live chain via
  the parent session's PreToolUse/PostToolUse hook rail — see
  [[feedback-workflow-subagents-share-parent-session-live-hooks]]. Audits run
  under this doctrine MUST use a throwaway clone or a session-level audit-dir
  redirect, and re-verify the chain LAST.)
- **§4.3 Structured returns (ADR-141 8-field schema).** `parallel()` returns
  MUST conform to ADR-141's 8-field shard schema (`finding_id`, `map_key`,
  `disposition`, `evidence_kind`, `evidence_pointer`, `confidence`,
  `risk_tags`, `author` — `docs/triage-reduce-protocol.md:24-37`). A reducer
  that merges free-prose shards is a governance violation (the precise
  prose-laundering gap ADR-141 was accepted to close, S177). Wiring this schema
  into fan-out returns is what unlocks the Tier-2 REDUCE metrics that
  `docs/triage-reduce-protocol.md:80-86` currently flags as not-yet-measured.

## §5 Falsifiability (mechanical P0 violations)

This verdict is refutable, not aspirational. ANY of the following is a P0
breach of ADOPT-CONFINED:

1. A write / canonical-edit / ceremony path driven through harness
   `parallel()` / `pipeline()` (instead of the sequential Owner-GPG sentinel).
2. A fan-out child writing into the parent's canonical audit chain (bypassing
   per-process spool isolation).
3. A `parallel()` structured return that does not carry the ADR-141 8-field
   shard schema (enabling prose-laundering at the REDUCE step).

## §6 Rationale — scale the PROOF surface, not the agent count

ADOPT-CONFINED + schema-bound returns satisfies the doctrine slogan
(PLAN-115 L271; ADR-141; `docs/triage-reduce-protocol.md:18`). REJECT would
forfeit proven resumability + critical-path orchestration this audit
demonstrates; DEFER would leave two production-grade harness Workflow uses
(PLAN-115 superpowers-v5.1.0 ship + this PLAN-120 audit) un-doctrined.

## §7 Promotion gates (per ADR-126 Tier-A doctrine class)

- Wave-A debate with >=6 archetypes, 0 VETO.
- Codex pair-rail >=R2 ACCEPT.
- Owner-GPG sentinel at
  `.claude/plans/PLAN-120/promotion-adr-136-amend-1/approved.md.asc`.

Until all three land, this amendment stays PROPOSED. *(Disposition S228:
gate satisfied by Owner ratification — see Promotion record below.)*

**Promotion record (S228, PLAN-134 W1, finding E6-F7):** Owner ratified
as-is via PLAN-134 §OQ3 (confinement §4 unchanged) — production already runs
on this confinement: S185 audit Workflows `wf_fa782ffb-8e5` +
`wf_dd23da15-f8a`, S223 PLAN-133 read-only build Workflows (write path via
materialize + Owner `finish` script, outside fan-out), S225 audit import
(REPORT-S225 finding E6-F7 flagged the doctrine lag), S227 PLAN-134 W0
6-model baseline Workflows. The Owner directive + the W1 Owner-GPG ceremony
commit serve as the signing artifact in place of the PLAN-120 sentinel path
above (that path was never created; PLAN-120 closed S186).
