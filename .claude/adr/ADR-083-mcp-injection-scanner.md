# ADR-083 — MCP injection scanner — close C-P0-01 G4 + advisory observability

## Status

ACCEPTED — Wave A re-ceremony 2026-04-27 — round-21 sentinel — Owner key 0000000000000000000000000000000000000000

## Context

PLAN-058 C-P0-01 (Round-23 audit, Session 60) identified 3 MCP-related
injection gates as OPEN pre-adopter:

- **G4** — MCP tool results carry attacker-controlled text the model
  may interpret as harness directives (`<system-reminder>`,
  `<important>`, role-preamble, directive-prose).
- **G5** — MCP server `instructions` field is concatenated into the
  system prompt without provenance scanning at server-load time.
- **G6** — MCP resource fetches return attacker-controlled content
  into the model context with same surface as G4.

ADR-077 (WebFetch injection precedent, Session 58 incident) shipped a
PostToolUse scanner over `WebFetch|WebSearch` tool responses reusing
`_lib/injection_patterns.py` (4 families: harness-mimicry, role-
preamble, directive-prose, synthetic-tool-call). Same threat model;
broader attack surface for MCP because:

1. Multiple MCP servers can be loaded simultaneously.
2. Server identity is the trust boundary, but content provenance is
   opaque inside the tool result body.
3. Anthropic harness does not enforce provenance markers.

Owner directive (Session 67, 2026-04-27): "close everything by
2026-05-01" + "foco SOTA Claude only — be the best Claude
orchestrator". MCP scanner is the last `Close` blocker before
`Optimize → Dogfood → Benchmark → External` per the activation
order directive.

## Decision

Ship a PostToolUse PLAN-052 MVP scanner with the **smallest viable
surface that closes G4** and provides a forensic trail for G6
(resource-fetch is structurally indistinguishable from tool_result
once Claude Code surfaces it). G5 (instructions-at-load-time) is
deferred to Phase 2 per cost-vs-benefit analysis below.

### What ships (Phase 1, this ADR)

1. **`.claude/hooks/_lib/mcp_injection_scan.py`** — wraps
   `injection_patterns.scan_harness_mimicry`. Provides `McpSource`
   provenance + `McpFinding` outcome tagging + severity classifier
   per pattern family (`high` for directive_prose / synthetic_tool_call;
   `medium` for role_preamble / harness_mimicry).

2. **`.claude/hooks/check_mcp_response.py`** — PostToolUse hook
   matched on `mcp__.*` (Claude Code MCP namespace). Coerces tool
   response text from common MCP shapes (string / bytes / list of
   `{"type":"text","text":"..."}` / dict). Always returns
   `{"decision":"allow"}`. Kill-switch `CEO_MCP_SCANNER_DISABLE=1`.

3. **`emit_mcp_injection_finding`** action in
   `.claude/hooks/_lib/audit_emit.py` (schema v2.13). Counts-only +
   capped 200-char snippet preview routed through `_preview` redaction.
   Total payload < 2 KiB.

4. **`SPEC/v1/audit-log.schema.md`** — register `mcp_injection_finding`
   in v2.13 row + version-history entry.

5. **`.claude/settings.json`** — register PostToolUse hook for matcher
   `mcp__.*` with timeout 5s + advisory statusMessage.

6. **Tests** — unit tests for scanner lib + hook integration tests
   (positive fixtures for 4 families; negative controls for benign
   markdown / quoted text; coercion edge cases).

### What does NOT ship in Phase 1 (refused / deferred)

| Item | Disposition | Reason |
|---|---|---|
| **STRICT mode** (block on match) | Deferred to Phase 2 | Per ADR-057 FPR observation discipline, advisory-only until 14d soak data justifies promotion. Production rollback path: `CEO_MCP_SCANNER_DISABLE=1` env-var. |
| **Strip mode** (modify tool response) | **REFUSED** (cost-exceeds-benefit) | Strip-mode requires destructive content edit pre-model-visibility. Risk of breaking legitimate MCP responses (e.g. server returns markdown that legitimately contains the `<important>` tag) outweighs marginal benefit beyond detection + audit trail. STRICT mode covers blocking when needed. |
| **G5 instructions-at-load-time scan** | Deferred to Phase 2 | Settings.json change-detection scan is a separate hook surface (PreToolUse / external watcher). Lower frequency event; G4 is the load-bearing daily-traffic surface. |
| **Anthropic harness-side provenance enforcement** | Out of scope | Upstream territory; surface as External-track issue per Owner directive ordering. |
| **Multi-LLM adapter MCP scanning** | **REFUSED permanent** | Owner directive 2026-04-27: ceo-orchestration is Claude-only orchestrator by design (PLAN-057 refused via separate ADR). MCP scanner is Anthropic-stack-only. |

### Severity escalation policy

```
high     directive_prose | synthetic_tool_call    →  immediate audit log + future block candidate
medium   role_preamble | harness_mimicry          →  audit log; FPR-tracked for STRICT promotion
low      no match OR weak signal                  →  no audit emission
```

## Consequences

### Positive

- C-P0-01 G4 closed (PLAN-058 ledger). G6 covered by same scanner
  (structurally indistinguishable from G4 once Claude Code surfaces
  the response).
- Forensic audit trail every time MCP server attempts to inject
  harness directives. Operators can grep `mcp_injection_finding`
  events to find compromised servers + measure base rate.
- ADR-077 pattern reuse — `injection_patterns.py` is single source of
  truth for harness-mimicry detection across WebFetch + MCP. Any
  future pattern addition lands once + propagates.
- PLAN-058 closeable; PLAN-015 42-ledger gate one blocker decremented.
- Hook overhead bounded (5s timeout per settings registration; scan
  function is O(n) in content size with 1 MiB cap).

### Negative

- Advisory-only in v1 means a sophisticated attacker can still inject
  harness-mimicry into MCP responses; the scanner emits an audit event
  but the model still sees the original content. Mitigation: STRICT
  mode promotion gated on FPR data per ADR-057.
- Pattern catalog reuse means false-positives propagate from ADR-077
  WebFetch scanner. If WebFetch FPR is high, MCP FPR will be too. So
  far ADR-077 has not reported FPR pain in soak data (Session 58+).
- Hook adds ~5-15ms p50 to every MCP tool call. Acceptable per
  performance budget (<50ms p95 PreToolUse target).

### Neutral

- Adopter projects with no MCP servers configured see zero overhead
  (matcher `mcp__.*` only fires for actual MCP tool calls).
- G5 deferral is documented; if a real attack on MCP server
  instructions emerges in the wild, Phase 2 promotion is unblocked
  by this ADR's design.

## Alternatives considered

### A. Strip-mode v1 (REJECTED)

Pre-model-visibility content edit. Rejected because:
- Risk of breaking legitimate responses with quoted markup.
- Detection + STRICT mode covers the same threat with lower blast radius.
- Adopter trust: better to flag than to silently edit.

### B. Custom MCP-specific pattern catalog (REJECTED)

Build patterns from scratch. Rejected because:
- ADR-077 catalog has been validated empirically (Session 58+ soak).
- Single source of truth principle (DRY across WebFetch + MCP).
- Custom catalog would be a maintenance liability with no proven uplift.

### C. Block on first match (REJECTED — premature)

Promote to STRICT default in v1. Rejected per ADR-057 FPR observation
discipline. Need 14d soak data first. Promotion is one ADR amendment
post-soak.

### D. Provenance-marker injection at MCP server boundary (REJECTED — out of scope)

Have ceo-orchestration prepend `[FROM MCP SERVER X]` to responses.
Rejected: Anthropic harness controls server-context concatenation;
framework cannot reliably inject markers outside the response body.
Surface as External-track issue if upstream requires it.

## Owner ceremony — implementation procedure

This ADR's edits land via Owner sentinel ceremony at
`.claude/plans/PLAN-052/architect/round-1/approved.md` GPG-signed by
Owner Ed25519 0000000000000000000000000000000000000000.

Scope:
- `.claude/hooks/_lib/mcp_injection_scan.py` (new, canonical)
- `.claude/hooks/check_mcp_response.py` (new, canonical)
- `.claude/hooks/_lib/audit_emit.py` (extend with `emit_mcp_injection_finding`, canonical)
- `.claude/settings.json` (register PostToolUse matcher `mcp__.*`, canonical)
- `SPEC/v1/audit-log.schema.md` (add v2.13 row, canonical)
- `.claude/adr/ADR-083-mcp-injection-scanner.md` (this file, canonical)

After GPG signature lands, CEO autonomous flow:

1. `git mv` staged-code into canonical paths.
2. Append `emit_mcp_injection_finding` to `audit_emit.py` per
   `staged-code/audit_emit_patch.md`.
3. Patch `settings.json` per `staged-code/settings_patch.md`.
4. Append schema row to `SPEC/v1/audit-log.schema.md`.
5. Promote this ADR draft to canonical.
6. Run pytest + governance + smoke MCP scanner end-to-end.
7. Commit + push.

## Acceptance + soak

### Acceptance criteria (Phase 1)

- ADR-083 ACCEPTED post-Owner-sentinel + post-tests-green.
- `pytest .claude/hooks/tests` remains green (≥2610 expected).
- `validate-governance.sh` 0 errors.
- `python3 .claude/scripts/audit-registry-coverage.py` green
  (mcp_injection_finding registered + schema row matches).
- Smoke test: `check_mcp_response.py` invoked with synthetic positive
  + negative fixtures emits expected audit events.
- ceo-diagnose `--quick` exits ≤1 (yellow OK; red NOT OK).

### Soak window (advisory)

- 14d advisory observation post-merge.
- Telemetry via `audit-telemetry.py --window 14d` filtering on
  `action=mcp_injection_finding` (planned extension Phase 2).
- Promotion to STRICT requires:
  - FPR ≤1% across ≥100 MCP tool calls in soak window.
  - Zero false-blocks on synthetic STRICT-mode dry-run fixtures.

### Rollback path

- `CEO_MCP_SCANNER_DISABLE=1` env-var → hook short-circuits to allow.
- Single-commit revert at the canonical path level (no breaking
  semantics; advisory only).

## Enforcement commit

To be filled at Session 67 closeout (this ADR's promotion to canonical
path lands in the same commit as the hook + lib + audit_emit + settings
+ schema bundle).

## References

- ADR-077 — WebFetch injection scanner (precedent + pattern catalog)
- ADR-079 — Phantom rejection (audit findings discipline; informs FPR gate)
- ADR-080 — Rail anomaly H4 defense-in-depth
- ADR-082 — L7c mitigation default-on (sister deliverable Session 67)
- PLAN-052 — MCP scanner plan (this ADR's parent)
- PLAN-058 — C-P0-01 origin (G4/G5/G6 ledger)
- `.claude/hooks/_lib/injection_patterns.py` — pattern catalog source of truth
