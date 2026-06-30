# ADR-057: Output-scan redaction — unicode / telemetry / OWASP LLM Top 10

**Status:** ACCEPTED
**Date:** 2026-04-19
**Proposer plan:** PLAN-029 (Wave A Fase 4)
**Target sprint:** 27 (PLAN-027 Wave A)
**Decision drivers:** 3 convergent audit sources — ultimate-guide BORROW-1 (unicode-injection scanner + prompt-injection detector + output-secrets scanner), n8n-mcp lesson (18.4k-star MIT repo ships default-ON telemetry with hardcoded 10-year JWT), awesome-plugins security-sweep (OWASP LLM Top 10 2024 rubrica not covered)
**Accepted-By:** @Canhada-Labs PLAN-029-WAVE-A-FASE-4-EXECUTION

---

## Context

ceo-orchestration performs **input-redaction** today via `_lib/redact.py`
(credential patterns in paths + parameters) and via
`check_read_injection.py` (advisory scan on file Reads). It does
**not** perform **output-redaction** — tool outputs flow from
shell / Agent / Read back into Claude's next turn without a
dedicated scanner.

PLAN-026 audit identified three convergent gaps:

1. **ultimate-guide BORROW-1:** popular Claude Code companion
   framework ships a "security hooks" bundle that includes
   unicode-injection scanner (zero-width chars, RTL overrides),
   prompt-injection detector on outputs, and output-secrets
   scanner. Ours has the input-side only.

2. **n8n-mcp lesson (18.4k ⭐ MIT):** a well-maintained, popular
   MCP server shipped **default-ON telemetry** with a **hardcoded
   JWT valid for 10 years**. Adopters who installed the server
   unknowingly leaked usage data to the vendor. Rubric we derived:
   **any adopter-installable tool must be grepped for telemetry
   strings before install** — but once installed, output-scan can
   flag residual telemetry traffic in tool outputs too.

3. **awesome-plugins security-sweep:** the OWASP LLM Top 10 (2024)
   defines 10 risk categories. Ours has partial defenses for 3
   (LLM01 via check_read_injection, LLM06 via _lib/redact,
   LLM08 via check_bash_safety). Not covered: LLM02 (insecure
   output handling), LLM10 (model theft / system-prompt exfil),
   and residue-in-output variants of LLM01.

Combined gap: **no output-side scanner that reviews tool responses
before they re-enter the model's context window.**

## Decision drivers

1. **Defense symmetry.** Input-scan + output-scan closes the loop.
   An adversary who gets past the input side (e.g., legitimate
   Read of a compromised file) should still be caught post-tool.
2. **Additive only.** Cannot break any existing hook; must fall
   through gracefully if `_lib/output_scan` is missing.
3. **Advisory at State 0.** First ship = log-and-banner; Sprint
   29+ FPR data drives per-family promotion to blocking.
4. **Performance discipline.** ADR-024 p99 budget preserved: scan
   overhead ≤5ms p99 on typical 1-10KB output (measured via
   test_output_scan.py perf class).
5. **Stdlib-only (ADR-002).** `unicodedata` + `re` + `typing`.
   No new runtime deps.
6. **Three independent kill-switches.** Adopters can disable
   the whole scanner OR any single sub-scanner (unicode /
   telemetry / LLM10) without uninstalling.

## Options considered

### Option A — Single scanner covering all 3 families (rejected)

One monolithic `output_scan()` that scans everything in one pass.

**Pros:** simpler.

**Cons:** no per-family kill-switches → operator can't disable
telemetry detection without also disabling unicode detection. FPR
debugging harder (single regex bundle vs per-family).

### Option B — Three sub-scanners + combined entry (CHOSEN)

`scan_unicode()`, `scan_telemetry()`, `scan_llm_top_10()` — each
independently kill-switchable, combined via `scan()` with aggregated
findings + per-family kill state.

**Pros:**
- Per-family FPR data drives independent promotion decisions.
- Per-family kill-switch (CEO_OUTPUT_SCAN_UNICODE=0, etc.).
- Each scanner is small + testable in isolation.

**Cons:**
- Three tests suites instead of one. Marginal complexity increase.

### Option C — Defer to Sprint 29 (rejected)

Wait for first adopter install before scanning outputs.

**Cons:** n8n-mcp lesson argues against "wait for incident" — the
adopter doesn't know to look. Ship with the scan advisory-on;
zero-cost to caller if no findings.

## Decision

**Option B.** Three sub-scanners + combined entry + three-tier
kill-switch (master + per-family).

## Implementation

### `_lib/output_scan.py` (~350 LOC)

Three sub-scanner functions:

```python
scan_unicode(text: str) -> List[Finding]
    # Bidi overrides (U+202A-202E, U+2066-2069)
    # Zero-width chars (U+200B-200F, U+2060, U+2063, U+FEFF)
    # Invisible separators (U+2063, U+2061, U+2062, U+2064)
    # Capped at 100 findings (pathological input guard)

scan_telemetry(text: str) -> List[Finding]
    # 12 known vendor string families (supabase, segment, mixpanel,
    # posthog, amplitude, sentry, datadog, rollbar, fullstory,
    # hotjar, heap, new_relic)
    # Per-vendor cap 10 hits
    # Case-insensitive; regex pre-compiled

scan_llm_top_10(text: str) -> List[Finding]
    # LLM01: "ignore previous instructions" + <system-reminder> forge
    # LLM02: <script> tag, javascript: URL, data:text/html, shell-subst
    # LLM06: sk-*, ghp_*, gho_*, AKIA*, JWT-shape
    # LLM08: rm -rf /HOME, git push --force (not --force-with-lease),
    #        --no-verify
    # LLM10: "reveal your instructions", "SYSTEM PROMPT:" leak

scan(text: str) -> Dict  # Combined + aggregated + kill-switch-aware
```

Each sub-scanner fail-opens to `[]` on any exception.

### `check_output_secrets.py` (~140 LOC)

PostToolUse wrapper hook:
1. Extract `tool_response` from PostToolUse payload.
2. Normalize dict/list → JSON string.
3. Call `output_scan.scan(text)`.
4. Emit `output_scan_finding` audit event if findings > 0.
5. Return `{"decision":"allow"}` with advisory banner
   systemMessage listing top-3 families.

Advisory-only at State 0; never blocks.

### Fixtures

28 scenarios in `.claude/hooks/tests/fixtures/output_scan/scenarios.jsonl`
cover: clean text, unicode injection single/multi, 4 telemetry
vendors, 5 LLM families, combined scenarios, false-positive
resistance (--force-with-lease, vendor in docs, normal code).
Parsed at test setup; test harness runs each fixture through
scan() and asserts expected family counts.

### `.claude/settings.json` registration

PostToolUse, matcher-free or `Agent|Bash|Edit|Write|Read`:

```json
{
  "matcher": "",
  "hooks": [{"type": "command",
    "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh\" check_output_secrets.py",
    "timeout": 5,
    "statusMessage": "Scanning tool output..."}]
}
```

Parallel registration in `templates/settings/settings.base.json`.

## Consequences

**Positive:**
- Symmetric input + output scanning closes OWASP LLM output-handling gap.
- Telemetry detection surfaces n8n-mcp-style incidents post-install.
- 5 LLM-Top-10 families covered in one hook.
- Per-family kill-switches allow operator customization.
- Fail-open + advisory-only means zero blast-radius at State 0.

**Negative:**
- PostToolUse adds ~2-5ms p99 per tool call (measured in
  test_output_scan.py::TestPerformance).
- Audit-log new event type `output_scan_finding` needs registry
  entry in `_KNOWN_ACTIONS` (staged with ADR-059 kernel batch).
- Potential FPR: legitimate telemetry-docs reference flagged as
  hit. Documented in fixtures as by-design advisory (not error).

**Neutral:**
- Kill-switch precedence documented:
  `CEO_OUTPUT_SCAN=0` (master) > per-family (CEO_OUTPUT_SCAN_UNICODE / _TELEMETRY / _LLM10)
- Master off → all sub-scanners disabled, hook returns allow
  without invoking any sub-scanner.
- `CEO_SOTA_DISABLE=1` does NOT disable this hook (parity with
  check_output_safety precedent).

## Blast radius

**Moderate.** 1 new `_lib/` scanner module + 1 new PostToolUse
hook + 2 test files + 1 fixtures file + 2 settings.json edits +
1 ADR. Zero impact on existing hooks. Zero SPEC change
(audit-log schema add new action `output_scan_finding` is
additive). Zero policy change.

## Reversibility

**High.** Unregister from settings.json + delete the hook +
delete `_lib/output_scan.py`. Audit-log entries already written
survive (forward-compat clause). Kill-switch provides bit-for-bit
opt-out without uninstalling.

## Fail-open invariant (ADR-005 parity)

- `_lib/output_scan` import fail → allow + stderr breadcrumb
- Any sub-scanner exception → empty findings for that family
- Combined `scan()` exception → returns empty result
  (`total_findings=0`)
- Hook-level exception → allow + stderr breadcrumb
- Kill-switch values recognized as "off": `0`, `false`, `off`,
  `no` (case-insensitive)

## Debate Round 1 — deferred per ADR-058 pattern

Following ADR-058 + ADR-056 precedent, Round 1 debate deferred.
Rationale:
- Blast radius moderate (1 scanner + 1 hook + fixtures).
- Reversibility high (kill-switch + revert).
- Pattern established (fail-open, per-family kill, advisory).
- Per-family kill-switches enable adopter-specific FPR tuning
  post-incident.
- If any family has > 5% FPR during State 0 observation, that
  family runs a debate with real evidence before State 1
  promotion decision.

## Revisit trigger

Re-open this ADR if any of:
1. Any sub-scanner FPR > 5% on dogfood audit-log in Sprint 28
   (indicates regex tuning needed or kill-switch pattern).
2. Adopter reports a legitimate telemetry integration
   consistently flagged (expand vendor allowlist to hostnames
   with port/path specificity).
3. OWASP LLM Top 10 2025 draft redefines any of LLM01/02/06/08/10
   (keep rubric current).
4. p99 scan budget > 5ms on 10KB (check_output_scan.py
   performance tests indicate regression).

## References

- PLAN-029 — output-scan redaction plan
- PLAN-027 — UltraFramework SOTA roadmap (Wave A parent)
- PLAN-026 — external audit that surfaced the 3 convergent sources
- ADR-005 — fail-open contract
- ADR-011 — check_read_injection (input-side sibling)
- ADR-024 — performance budget
- ADR-036 — check_output_safety (existing PostToolUse scanner;
  this ADR is complementary, focused on 3 new families)
- ADR-056 — hook lifecycle expansion (sibling Wave A ADR)
- ADR-058 — brainstorm gate + adversarial reviewer (sibling)
- ultimate-guide security-hooks bundle — pattern origin BORROW-1
- n8n-mcp incident lesson — telemetry default-ON concern
- awesome-plugins security-sweep — OWASP LLM Top 10 rubric

## Enforcement commit

`37912fc777c5` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
