---
id: PLAN-140
title: Drop forbidden hook_origin kwarg from the two compaction emit callsites
status: done
created: 2026-06-18
reviewed_at: 2026-06-18
completed_at: 2026-06-18
related_commits: ["771194bc497796606cbdfae12dc2dad936bccde1"]
created_by: "CEO (S244 — breadcrumb triage, investigation workflow wf_fe80fb13-6f9)"
completed_by: "CEO (S245 — status closeout; implementation landed S244)"
owner: CEO
depends_on: []
related_adrs:
  - ADR-010                        # canonical-edit sentinel ceremony — gates this change
  - ADR-153                        # compaction-continuity events route through dedicated deny-by-default allowlists (closed enums + counters only)
risk_tier: A                       # behaviour-preserving kwarg deletion; no wire change; no kernel path
target_tag: v1.47.0                # tentative — confirm at execution
budget_tokens: 5-10k               # two one-line Edits + re-run of the compaction-continuity test
budget_sessions: 1
context_risk: low
---

# PLAN-140 — Drop forbidden `hook_origin` kwarg from the two compaction emit callsites

> **One-line goal:** stop two compaction hooks from passing a `hook_origin`
> kwarg that the audit-emit deny-by-default allowlist drops on every call,
> which spams `audit-log.errors` with a benign-but-recurring breadcrumb.

## 0. Provenance & honest framing

Surfaced by `/ceo-boot` (S244): `audit-log.errors` carried the recurring line
`audit_emit: emit_generic <event> dropped forbidden field(s): ['hook_origin']`
for `compaction_continuity_snapshot` and `compaction_context_reinjected`.
A read-only investigation workflow (`wf_fe80fb13-6f9`) located the exact
callsite/policy mismatch. The guard is **working correctly** — it strips a
non-allowlisted field; the defect is purely that two callsites pass a field
the policy forbids. This is a fail-open hygiene fix, NOT a security gap.

## 1. Root cause

Both callsites pass `hook_origin=` into `emit_generic`, but these two events
are **not** passthrough — per ADR-153 they route through dedicated per-action
allowlists (`_COMPACTION_CONTINUITY_SNAPSHOT_ALLOWLIST` /
`_COMPACTION_CONTEXT_REINJECTED_ALLOWLIST`, audit_emit.py:7206 / :7214), and
neither lists `hook_origin`. The scrub branch drops it and logs the breadcrumb
on every emit. The hooks borrowed the emit idiom from
`check_protocol_semver_cascade` (a *passthrough* action whose `hook_origin`
flows through un-dropped) — the borrowed kwarg is a mismatch for scrub-branch
events.

## 2. Fix (behaviour-preserving)

Remove the single `hook_origin=...` kwarg from each callsite. The action name
already uniquely identifies the producing hook, and ADR-153 mandates the wire
carry only closed enums + counters. `hook_origin` was **never persisted** (it
was always stripped), so the emitted/persisted event and the HMAC chain are
byte-identical after the change. **Do NOT** widen the allowlists — that would
persist a producer-identity string on a wire ADR-153 restricts to closed enums
+ counters, weakening the Sec MF-3 / LLM06 side-channel defense.

### Edit 1 — `.claude/hooks/check_precompact_continuity.py` (~line 285)
Remove the line `hook_origin="check_precompact_continuity",` from the
`audit_emit.emit_generic(action="compaction_continuity_snapshot", ...)` call.

### Edit 2 — `.claude/hooks/check_postcompact_reinject.py` (~line 208)
Remove the line `hook_origin="check_postcompact_reinject",` from the
`audit_emit.emit_generic(action="compaction_context_reinjected", ...)` call.

## 3. Why a canonical ceremony

Both files match `.claude/hooks/*.py` in `check_canonical_edit.py`'s
`_CANONICAL_GUARDS`, so edits require an Owner-signed sentinel (ADR-010).
Neither file is in `check_arbitration_kernel.py`'s `_KERNEL_PATHS`, so **no**
`CEO_KERNEL_OVERRIDE` is needed — the sentinel alone authorizes the edit.

## 4. Validation

`python -m pytest .claude/hooks/tests/test_check_compaction_continuity.py -v`
— existing assertions verify the closed-enum wire shape and that body fields
are absent; they pass unchanged (hook_origin was never on the wire). After the
edit the recurring breadcrumb stops; historical `audit-log.errors` lines are
read-only and need no cleanup.

## 5. Authorization (Owner action required)

The sentinel `.claude/plans/PLAN-140/architect/round-1/approved.md` declares
both paths in its Scope block. To authorize, the Owner picks ONE:
  - **GPG**: fill the anchor commit sha on the `Approved-By:` line, then sign
    the sentinel — `gpg --armor --detach-sign approved.md` — producing
    `approved.md.asc` (signer must be in `.claude/sentinel-signers.txt`).
  - **Env-override (interim, ADR-010 amendment)**: export
    `CEO_SENTINEL_UNLOCK=PLAN-140-compaction-hook-origin-dropfix` and
    `CEO_SENTINEL_UNLOCK_ACK=I-ACCEPT` in the Claude Code shell; the `.asc`
    requirement is bypassed (the env vars are the second auth factor a
    sub-agent cannot forge).
