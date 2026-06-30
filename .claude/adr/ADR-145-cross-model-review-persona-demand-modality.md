# ADR-145 — Cross-model Codex review as a recognized persona-demand satisfaction modality

- **Status:** PROPOSED (PLAN-132, S221)
- **Date:** 2026-06-08
- **Deciders:** CEO + Wave-A debate (security-engineer / identity-trust-architect / qa-architect / code-reviewer / llm-finops-architect, 0 VETO) + Codex pair-rail
- **Supersedes / Amends:** none (PLAN-104 shipped with no ADR under ADR-124 §Part 2 hotfix scope; this is the first ADR over the persona-demand ledger doctrine)

## Context

The `/ceo-boot` 19th Tier-S check `persona_atrophy_7d` (PLAN-104 demand ledger)
opens a `branch_ahead -> code-reviewer` demand whenever a non-trunk branch is
ahead of `origin/main`, and marks it satisfied only when a NATIVE
`code-reviewer` `agent_spawn` fires within 24h. On the meta-repo the canonical
review path is a Codex pair-rail call (`mcp__codex__codex`, an MCP tool that
emits NO `agent_spawn`), so a genuine cross-model review can never satisfy the
demand by construction — a STRUCTURAL false-RED that recurs on every PR-branch
session (S210/S211/S214/S218/S219). A detector that cries wolf trains the
operator to ignore the channel.

## Decision

Recognize a branch-bound, in-window cross-model Codex review as a satisfaction
modality for `code-reviewer` demands **ONLY**, recorded as a distinct
closed-enum `match_modality = "codex_review"` on `persona_demand_matched`.

1. **Observability (Component A).** The existing `check_codex_response.py`
   PostToolUse hook (matcher `mcp__codex__codex|mcp__codex__codex-reply`) is
   extended to emit `codex_review_invoked` when the call is REVIEW-shaped. The
   review-intent gate requires BOTH a review verb AND a diff/code artifact, and
   suppresses generation-shaped prompts (R2). It is biased to under-emission: a
   missed real review only preserves the advisory false-RED (status quo, safe),
   whereas a false match would silently GREEN the detector (unsafe). No new hook
   file is added (no hook-count / settings / parity cascade).

2. **Branch-binding (R1).** The emitted event carries `target_ref_hash =
   sha256(NFKC("branch:" + current_branch))[:12]`, IDENTICAL to
   `persona_demand_scan._target_ref_hash`. The resolver match requires
   `review.target_ref_hash == demand.target_ref_hash`, so a review of branch A
   cannot satisfy branch B's demand. An unresolvable branch (detached HEAD,
   trunk, git failure) yields an empty hash and the resolver FAILS CLOSED (no
   match). This keeps the match path no weaker than the ledger's own waive path,
   which already enforces branch reachability.

3. **Provenance / anti-blur (Component B).** The resolver emits
   `persona_demand_matched` with `match_modality = "codex_review"` and
   `actual_persona = "code-reviewer"`, so the published SPEC v1 invariant
   `actual_persona == expected_persona` STILL HOLDS — we do NOT poison
   `actual_persona` with a non-persona sentinel. The modality is a dedicated
   closed enum `{native_spawn, codex_review}` (default `native_spawn` for the
   legacy path, byte-stable for existing chains).

4. **Source discrimination.** Only `review_source` in
   `{adhoc_mcp, user_code_auto}` with a non-empty `target_ref_hash` can satisfy
   a demand. A `phase_gate` review (per-plan-phase review from
   `check_pair_rail`) is EXCLUDED — it belongs to a different workflow and
   carries no branch binding.

## Scope (NON-EXTENSIBLE)

The `codex_review` modality is recognized for `code-reviewer` demands ONLY. The
other three demand types — `security-engineer`, `qa-architect`,
`threat-detection-engineer` — keep strict native-spawn match: a generalist
cross-model code review is a legitimate substitute for code REVIEW but NOT for a
security VETO, a QA test-adequacy gate, or SIEM detection coverage. The
relaxation is a single hard-coded literal guard (`expected_persona ==
"code-reviewer"`) in `persona_demand_resolver.py`, NOT a config toggle, so
widening to any other persona requires a CODE change AND a fresh ADR (R3
doctrine-creep closure).

## Consequences

- The recurrent structural false-RED is fixed prospectively: a branch reviewed
  via Codex within its 24h window now reads as matched (modality=codex_review),
  green. A review arriving AFTER the window legitimately stays unmet (the demand
  really was unreviewed for 24h — doctrine-consistent with the native path).
- The check stays advisory / never-blocks; kill-switches
  `CEO_PERSONA_DEMAND_LEDGER_DISABLED=1` (whole ledger) and
  `CEO_CODEX_REVIEW_OBSERVE=0` (Component A emit) remain authoritative.
- SPEC v1 audit-log schema bumped to v2.40 (no new actions; new fields
  `review_source` + `target_ref_hash` on `codex_review_invoked`, `match_modality`
  on `persona_demand_matched`).

## Residual risks (accepted; surfaced by the Codex pair-rail review)

- **Branch checkout assumption (Codex P1 #2):** branch-binding uses the
  CURRENTLY-CHECKED-OUT branch, not the artifact actually reviewed. Two sub-cases:
  (a) reviewing a branch from a `main` checkout yields an empty hash ->
  fail-closed -> false-RED preserved (safe); (b) while on branch A (with an open
  demand) pasting a diff for branch B emits branch A's hash and can mark A
  "reviewed" though B was the artifact -> a false-GREEN for A. Case (b) requires
  a deliberate, anomalous operator action on a single-operator advisory signal,
  and there is no trustworthy signal in the event to recover the reviewed
  branch from a pasted diff. Accepted; the normal flow (review the checked-out
  branch) is correct. Re-open if multi-branch pasted-diff review becomes common.
- **Review completing just after the window (Codex P2 #1):** the event `ts` is
  stamped at write time (PostToolUse, after Codex returns). A review STARTED
  in-window but completing just after `window_end` is missed -> false-RED
  preserved. This is the SAFE direction (under-emission), consistent with the
  plan's high-precision bias; not fixed.
- **A3 (user_code_auto) inert until bound:** `codex_review_user_code.py` still
  emits `codex_review_invoked` for its own §7 telemetry but WITHOUT a
  `target_ref_hash`, so it cannot satisfy a demand (fail-closed). Wiring A3
  branch-binding is a tracked follow-up, not required for this fix.
