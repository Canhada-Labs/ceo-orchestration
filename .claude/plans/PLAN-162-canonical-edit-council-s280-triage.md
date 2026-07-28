---
id: PLAN-162
title: check_canonical_edit.py — S280 council 3-lane findings triage (12 advisory defects)
status: draft
created: 2026-07-27
owner: CEO
depends_on: [PLAN-156-FOLLOWUP, PLAN-160]
budget_tokens: 120-180k
budget_sessions: 2
context_risk: medium
external_wait: none
tags: [canonical-edit, hooks, council, security, fail-open]
---

# PLAN-162 — check_canonical_edit.py council-S280 findings triage

## Context

S280 (2026-07-27) ran the first-ever **full 3-lane** `/council` over
`check_canonical_edit.py` (run `wf_ef98734e-7ec`, Owner-authorized egress;
closed PLAN-156-FOLLOWUP). Quorum FULL, `verify_failed=0`, and a strong
cross-vendor signal — 3/3 convergence on the top 3 defects, and each lane
independently caught 3 defects the other two missed (9/12 unique-catch).

The verdict was **FINDINGS**: 12 distinct ADVISORY defects against
`.claude/hooks/check_canonical_edit.py`. Per PROTOCOL V0–V3 the council
authorizes nothing — this plan is the intake that routes each finding to
FIX / ACCEPTED-BOUNDARY / DOCUMENTED-GAP, with real fixes going through
debate + (for kernel/canonical surfaces) the Owner GPG ceremony.

Full report: `.claude/plans/PLAN-156-FOLLOWUP/council-3lane-S280.md`.

**Dedup obligation (do FIRST):** several S280 findings may restate the
S276 W4 advisory set A/C/B/D on this same file (e.g. S280 #10 cache-key
staleness ≈ S276 B). Reconcile against
`PLAN-156-FOLLOWUP-council-livefire-findings.md` §W4 and against PLAN-160
(the prior canonical-edit hardening) BEFORE opening any fix — a finding
already fixed or already accepted is not re-litigated.

## The 12 findings (verbatim intake — classify, do not pre-judge)

| # | Raised by | Claim | First-read disposition (to VERIFY) |
|---|-----------|-------|-------------------------------------|
| 1 | claude+codex+grok | GPG `verify_detached(timeout=15.0)` L1011 > the hook's 5s registered timeout; block path verifies up to 12 sentinels/process → slow/deny-all GPG kills the hook → harness proceeds **fail-open** on canonical edits | LIKELY-FIX (fail-open on the block path is the worst class) |
| 2 | claude+codex+grok | `_find_sentinels` symlink-rejects only at depth ≤2 (L858-864) but discovery patterns are 4-5 deep → symlinked `PLAN-*`/audit-v2 dir routes an out-of-tree `approved.md` into discovery (F-01 bypass) | LIKELY-FIX (guard depth must cover the full pattern) |
| 3 | claude+codex+grok | ADR-121 signer registry `.claude/security/sentinel-signers-registry.yaml` is in neither `_CANONICAL_GUARDS` nor kernel deny; `.exists()`-gated (L1017) → an ordinary Edit/delete **silently disarms** the dual rail (asymmetric with the kernel-guarded legacy `.txt`) | LIKELY-FIX (trust-anchor; add guard + treat absence as fail-closed) |
| 4 | claude | Sentinel >64KiB falls Tier-1→Tier-2 (L1122/L1147); END marker is no scope terminator → Scope bullets OUTSIDE signed markers honored (containment loss, not fail-closed) | VERIFY (mitigant: .asc still signs whole file) |
| 5 | claude | `read_event`/`parse_error` both emit allow (L1450-1458) — INPUT-parse fail waved through, tension with PLAN-152 C4 fail-closed-on-input | CONTESTED (ADR-010 documents this as ENVELOPE/infra fail-open; the sibling kernel hook is fail-closed — reconcile the doctrine, may be ACCEPT) |
| 6 | claude | Layer-A MCP extraction reads only top-level str/list-of-str under 9 keys; nested `files:[{path,content}]` → 0 candidates → bypass | DOCUMENTED-GAP (v1 Layer-A; Layer B deferred — confirm still-intended) |
| 7 | codex | `uri` accepted (L355) but file URIs passed to `Path` with no scheme strip → `file://…/settings.json` classifies non-canonical even for a guarded file | VERIFY (oracle showed 0-vs-1 split) |
| 8 | codex | Policy hash-pin registry `.claude/policies/.drift-manifest.json` matches no guard pattern + not kernel → rewritable without the sentinel it pins | LIKELY-FIX (parallels #3 — pin the pinner) |
| 9 | codex | Veto audits hard-code `blocked_tool="Edit|Write|MultiEdit"` (L1186/L1308) vs `event.tool_name`; hook is registered for `mcp__.*` too → MCP/apply-patch blocks forensically misattributed | LIKELY-FIX (forensic fidelity, low blast) |
| 10 | grok | `_compute_sentinel_cache_key` hashes only sentinel bytes+stat+target (L903-916); .asc/allowlist/registry mutations don't bust the key (comment claims otherwise) | VERIFY vs S276 B — likely SAME defect, re-confirmed (mitigant: per-process cache) |
| 11 | grok | Invisible-unicode SKILL.md guard keys only on single `file_path` (L1556/L1649-1651); other GRANTED SKILL.md paths in a multi-candidate event unscanned under `CEO_UNICODE_HARDBLOCK=1` | VERIFY |
| 12 | grok | Dispatcher YAML guarded as `*.{yaml,yml}` while `**` applies only to `*.py` (L164-167) → nested `dispatcher/**/*.yaml` ungated | LOW (no nested YAML on disk; mitigant: kernel hard-deny covers `dispatcher/**/*`) |

## Waves (draft — finalize after debate)

- **W0 — debate + dedup.** L3+ → run `/debate start PLAN-162`. Reconcile the
  12 against S276 A/C/B/D + PLAN-160. Output: per-finding disposition
  (FIX / ACCEPT / DOC-GAP) with the convergent 3/3 trio (#1/#2/#3) as the
  priority spine.
- **W1 — red-first tests** for every FIX-classified finding (a failing test
  that encodes the defect before any code moves).
- **W2 — fixes** (canonical/kernel edits → staged pack + pair-rail to APPROVE
  + Owner GPG ceremony, PLAN-160/161 pattern).
- **W3 — council re-run** on the post-fix file (optional confirmation the
  convergent trio is closed).

## Open questions

- **OQ1** — Is #5 (parse-error fail-open) a defect or the intended ADR-010
  envelope contract? The sibling kernel hook is fail-closed on parse_error
  "UNLIKE the sentinel hook" — is that asymmetry deliberate or drift?
- **OQ2** — #3 and #8 both say "the guard registry guards everything except
  itself." Fold into one "guard-the-guardfiles" fix, or keep separate?
- **OQ3** — Council-instrument follow-ups from S280 (NOT about this file):
  (i) recalibrate the C3 wall-clock formula `180+2*N` (ignores scope depth,
  under-budgets low-file-count deep scopes); (ii) fold the `args`
  JSON-string transport-decode into canonical `council-audit.js`. Own plan
  or ride here as a separate wave?

## Success criteria

- [ ] Every one of the 12 findings has a recorded disposition (FIX / ACCEPT /
  DOC-GAP) with evidence, deduped against S276 + PLAN-160.
- [ ] Every FIX has a red-first test that fails before and passes after.
- [ ] Canonical/kernel fixes land via pair-rail-APPROVE + Owner GPG ceremony.
- [ ] Validate green on the closeout commit.
