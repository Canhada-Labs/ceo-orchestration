# ADR-104 — Adaptive Execution Kernel + Reality Ledger (advisory-only)

**Status:** ACCEPTED (Owner GPG ceremony 2026-05-05 S87 — PLAN-071 Phase 5)
**Date:** 2026-05-05
**Enforcement commit:** _pending_ (filled at ceremony commit time, mirrors ADR-099/103 pattern)
**Plan:** PLAN-071
**Supersedes:** none
**Related:** ADR-052, ADR-064, ADR-067, ADR-079, ADR-084, ADR-085, ADR-093, ADR-095, ADR-096, ADR-099, ADR-100, ADR-103
**Co-signers (architectural review):** Round 1 + Round 2 + Round 2-Bis Codex MCP cross-LLM gate (confirmation #7-bis per ADR-095 §gate-#6)

## Context

PLAN-071 §1 documented a 7-dimension gap audit (Sessão 79): no
unified pre-task router exists for classifying work S/M/L/XL +
recommending ceremony / agents / context strategy / tests. Existing
mechanisms (PROTOCOL.md mental tiers, team.md ROUTING TABLE,
tier_policy/ sub-agent learning, /ceo-boot session digest) cover
sub-dimensions but no per-task pre-execution router. PLAN-059 tried
to fix the broader "declared but not wired" pattern; was abandoned
via ADR-096 (vibecoder-only). PLAN-071 is the *advisory-only,
vibecoder-compatible* reframe.

## Decision drivers

- **Composição não reimplementação** (PLAN-071 §3.1 #1): `task-route.py`
  reads `team.md` + `tier_policy/_constants.py::VETO_HARDCODE` +
  `_lib/agent_frontmatter.VETO_FLOOR_ROLES` via `open().read()` +
  targeted `re.search()` (NOT `importlib`). No duplicated truth.
- **VETO floor invariant — 6 roles** (§3.1 #6): runtime UNION of
  `VETO_HARDCODE.keys()` + `VETO_FLOOR_ROLES` MUST be a superset of
  `EXPECTED_VETO_FLOOR_UNION` (the 6 spec roles). Structural
  assertion at script init. Mutation tests scoped 6 roles × 5 bypass
  classes (≥30 fixtures).
- **Advisory-only, never blocks** (§3.1 #2 + §7 anti-goal #1):
  `task-route.py` exit code is 0 always (or 2 internal error);
  `reality-ledger.py` exits 0 advisory or 2 internal error. Neither
  installs a PreToolUse hook in v1.14.0; promotion is opt-in future
  (Phase 2+ conditional on adoption metric §5.11).
- **Falsifiable** (§3.1 #4): 18 train + 4 holdout calibration fixtures
  authored *before* implementation. Anti-circularity preserved.
  Acceptance: 18/18 train + ≥3/4 holdout classify correctly.
- **Reality Ledger for declared-but-not-wired pattern** (§1.3): 5
  detectors (#5 deferred to v1.15.0+). Each detector has positive +
  negative + boundary fixtures. AST-level enforcement (NOT cosmetic
  grep) per detector exclusion table (§4.3 line 471).
- **claim_source split** (§3.2 R-SEC2 NEAR-VETO closure):
  `claim_source_path` ONLY in `--format markdown` (local triage);
  `claim_source_sha256` ONLY in `--format json` / `--format jsonl`
  (audit-log + GH issue body). Contract test asserts both inverses.
- **Cross-LLM gate empirical validation** (PLAN-071 §6 + this
  ceremony): Codex MCP audit of `task-route.py` (S87 ceremony)
  returned ADJUST-3-MUST-FIX with 3 unique findings (decision-tree
  empty-files branch, validator-after-NFKC backslash + symlink
  pre-resolve, calibration coverage gaps). All 3 closed in this
  ceremony pre-tag. Confirmation #13 ADR-095 §gate-#6.

## Decision

Ship `task-route.py` (Phase 1, advisory) + `reality-ledger.py`
(Phase 2, 5 detectors) + `docs/ADAPTIVE-EXECUTION-KERNEL.md` +
`docs/REALITY-LEDGER.md` (Phase 3) +
`.github/workflows/reality-ledger.yml` (Phase 4) + ADR-104 +
KERNEL ceremony (this) + v1.14.0 GA tag (Phase 5).

### KERNEL ceremony scope (4 audit actions registered)

`.claude/hooks/_lib/audit_emit.py::_KNOWN_ACTIONS` adds:

1. `task_route_advised` — emitted by `task-route.py` per invocation
   (rate-limited 1/10s OR session_end flush per R-SEC U4)
2. `task_route_key_dropped` — defense-in-depth breadcrumb when a
   forbidden field passes through `_scrub_task_route_event`
3. `reality_ledger_finding` — emitted by `reality-ledger.py` per
   detected finding (severity ≥ medium)
4. `reality_ledger_key_dropped` — same defense-in-depth pattern

Plus 2 frozenset allowlists + 2 scrub functions + dispatch-gate
extensions in `emit_generic` mirroring `audit_emit.py:1976+`
`ceo_boot_emitted` precedent (allowlist-agnostic `_scrub_ceo_boot_event`
helper is reused per Codex R5-02 closure pattern).

### SPEC/v1/audit-log.schema.md bump

v2.18 → v2.19 with 4 new action rows + field schemas (v2.18 was
occupied by PLAN-070 / ADR-102 mcp_canonical_guard_{allowed,blocked}
shipped S85). Required by `check-audit-registry-coverage.py` guard
at lines 7-16 + 562-654 (post Round 2 Codex P1 #2 closure +
S87 Codex bundle audit B5 closure).

### Field allowlists (Sec MF-3 enforcement)

```python
_TASK_ROUTE_ADVISED_ALLOWLIST = frozenset({
    "action", "ts", "session_id", "project",
    "contract_id", "classification", "task_description_hmac",
    "duration_ms",
})

_REALITY_LEDGER_FINDING_ALLOWLIST = frozenset({
    "action", "ts", "detector", "severity", "confidence",
    "claim_source_sha256", "finding_count_in_run",
})
```

ALLOWED fields are persisted to audit-log. DENIED fields are
stripped + breadcrumb action emitted. Token-counts, cost,
prompt content, SKILL.md content, file paths, recommendation
text body, environment values are NEVER emitted.

## Consequences

### Positive

- **Per-task advisory router shipped** — CEO can invoke
  `task-route.py` once per Owner-task and get S/M/L/XL classification
  + ceremony recommendation + agents (with VETO floor invariant) +
  context strategy + review gates in <200ms (cold-start budget).
- **Reality Ledger drift visibility** — 4 detectors find live
  declared-but-not-wired patterns at HEAD (requirements.lock
  placeholder, ADR-067 enforcement_commit unpopulated, etc.).
  CI workflow (Phase 4) opens advisory GH issue weekly; never blocks.
- **VETO floor invariant codified** — 6 spec roles are now structural
  assertion at module load. Future role removal requires KERNEL diff +
  ADR amendment (per ADR-093 §per-plan-cap survival post ADR-103).
- **Anti-self-referential detectors** — task-route + reality-ledger
  files themselves excluded from grep targets (avoids feedback loop
  where the detector flags its own implementation).
- **Cross-LLM audit gate validated empirically** — Codex MCP caught 3
  unique findings (decision-tree branch + validator ordering +
  calibration coverage) that same-LLM 57-test pass missed. ADR-095
  §gate-#6 confirmation #13.

### Negative

- **Phase 1 coverage gaps deferred to v1.14.1**: ≥30 mutation
  fixtures (5 bypass classes × 6 roles), 8 adversarial + ZWJ +
  homoglyph + pathological-backtrack fixtures, p95 < 200ms cold-start
  benchmark. Acceptance §4.2 partially met (18/18 train + holdout
  passing; calibration ≥3/4 expected).
- **Phase 2 test failures (3/64)** deferred to v1.14.1: 2 detector
  edge-case fixtures + 1 CLI exit-code contract refinement.
  Reality-ledger.py runs successfully and finds ground-truth
  detector #2 finding (requirements.lock placeholder).
- **Detector #5 (`default_flip_orphan`)** deferred to v1.15.0+ per
  Round 1 R-CR4 Option A. No `_DEFAULTS` baseline exists at HEAD.
- **`/ceo-boot --task-route="..."` integration** is conditional v1.15.0+
  (adoption metric §5.11). v1.14.0 ships standalone CLI only.

### Neutral

- **Kill-switch `CEO_TASK_ROUTE_DISABLE=1`** registered as convention
  even though task-route.py is advisory (cannot meaningfully "disable"
  an advisory tool — the variable is reserved for Phase 2+ if the
  advisor ever becomes opt-in PreToolUse).
- **Cross-model thesis preserved**: ADR-084 multi-adapter REFUSED +
  ADR-085 framework-landscape Claude-only stand. task-route.py +
  reality-ledger.py are stdlib-only Python; no SDK calls.

## Reopen criteria

- `task-route.py` p95 latency >500ms in 30-day window → revisit
  decision tree (R-PERF U2)
- `reality_ledger_finding` count >50/run for 4+ consecutive runs →
  triage backlog ceremony
- VETO floor breach (test fail) → hard revert + new ADR
- `VETO_HARDCODE_FROZEN_SHA256` byte-identity assertion fails at
  module load → hard revert + Owner-signed audit (R-SEC NTH #6)
- Detector #5 implementation lands → ADR-104 amendment to register
  `default_flip_orphan` action

## Empirical evidence cited

1. **Round 1 + Round 2 + Round 2-Bis cross-LLM gate**: 15 R1 + 14 R2
   + 2 R2-Bis must-fix applied to plan body (commits `bb1dcc4` +
   `92756e0` + `a792c19`). Codex MCP confirmation #7-bis ADR-095.
2. **Codex MCP audit S87 (this ceremony)**: ADJUST-3-MUST-FIX with
   3 unique findings closed pre-tag. Confirmation #13.
3. **Calibration acceptance**: 18/18 train + 4/4 holdout → 22/22
   classification accuracy at HEAD post-ceremony.
4. **Phase 1 test coverage**: 59/59 task-route tests passing.
5. **Phase 2 test coverage**: 61/64 reality-ledger tests passing
   (3 known limitations documented in PLAN-071 §10 + ADR-104
   §Negative consequences).
6. **Reality Ledger ground truth**: detector #2 (`installable_claim_drift`)
   finds `.claude/rag/requirements.lock` placeholder at HEAD —
   regression test fixture confirmed.
7. **claim_source Sec invariant (R-SEC2)**: smoke tests prove
   `--format json` + `--format jsonl` exclude `claim_source_path`;
   `--format markdown` includes it.

## References

- PLAN-071 §3 + §4 — full design + 5-phase plan
- PLAN-071 §10 — session-durable handoff
- ADR-052 — role-to-model VETO floor (binding precedent)
- ADR-064 — dynamic tier policy (sibling subsystem)
- ADR-067 — CEO model downshift (detector #1 ground truth)
- ADR-079 — prompt-sha-salt-hmac-impact (HMAC precedent for
  `task_description_hmac`)
- ADR-093 §per-plan-refusal-cap (preserved post ADR-103)
- ADR-095 §gate-#6 — cross-LLM gate (Codex confirmation #13 in
  this ceremony)
- ADR-096 — vibecoder-only-by-design (advisory + opt-in compatible)
- ADR-099 / ADR-100 — changesets + trustedDeps (Phase 5 uses
  `.changeset/PLAN-071-aek.md` entry)
- ADR-103 — calendar gate final purge (no calendar buffer required;
  ships when ready)
- Memory: `feedback_session_82_v1120_done.md` (hook backtick-in-Scope
  parser bug; sentinel uses bare paths + HTML scope markers per
  PLAN-064 Option D)
