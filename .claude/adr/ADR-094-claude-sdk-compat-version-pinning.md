# ADR-094 — Claude Agent SDK compat matrix + version-pinning policy

## Status

PROPOSED-STAGED · drafted 2026-04-28 (Session 71 / Wave D-3) ·
awaits Owner sentinel for promotion to `.claude/adr/ADR-094-*.md`
under round-5 ceremony.

## Context

Session 60 (2026-04-24) audited the framework landscape and identified
**Claude Agent SDK** (Anthropic upstream — the `claude` binary the
framework runs against) as a **bit-rot risk** without a contract. Today
the framework consumes the CLI at runtime with no version pin. A
breaking change in upstream Claude Code CLI could silently break:

- Hook lifecycle contract (PreToolUse / PostToolUse / SessionStart /
  SessionEnd / UserPromptSubmit invocation order or signature)
- MCP server contract (tool name namespacing, response shape, transport)
- `permission_mode` signature (env var, CLI flag, settings.json field)
- Tool universe (new tools changing matcher patterns)
- Settings.json schema (top-level field renames)

PLAN-056 Phase 2 ships a 3-deliverable answer:

1. `SPEC/v1/claude-sdk-compat.md` — published matrix (tested-against
   GREEN + known-incompatible RED).
2. `.claude/scripts/check-sdk-compat.sh` — advisory CI gate that reads
   `claude --version` (or `$CLAUDE_VERSION` override), looks up the
   matrix, and reports INFO / WARN / ERROR per band.
3. `validate.yml` step (advisory, `continue-on-error: true`) wiring the
   gate into the framework's own CI.

PLAN-056 was reopened 2026-04-27 per ADR-092 with an explicit trigger
("Phase 2 SDK compat empirical validation against current Claude Agent
SDK release"). This ADR closes that trigger.

## Decision

Adopt the SDK compat matrix + advisory CI gate as the framework's
contract with upstream. The matrix is **fail-open by default**:

- Listed-GREEN version → exit 0 INFO line.
- Listed-RED version → exit 1 ERROR line (fail-closed for known-
  incompatible only).
- Unlisted version → exit 0 WARN line (fail-open — adopter may be on
  a brand-new upstream that we haven't tested against; do not break
  their build).
- Malformed / unparseable version output → exit 0 WARN line.
- `claude` binary not in PATH → exit 0 silent skip.

Adopters who want **strict** SDK pinning (block on unlisted versions)
can override the script's exit semantics in their own CI by using
`bash check-sdk-compat.sh && [ ! -z "$LISTED_GREEN" ]` or by piping
through `grep -v WARN`.

The matrix is **append-only** (additive within v1, per `SPEC/v1/`
contract). New GREEN versions are added when they pass the framework's
hook-lifecycle conformance harness against the new CLI. RED versions
are added when a maintainer confirms a breaking change in upstream
that the framework has not yet adapted to.

## Consequences

**Positive:**

- Adopter gets a documented compat horizon — no silent breakage.
- Framework gets an explicit signal when upstream ships a breaking
  change (CI WARN escalates to maintainer attention).
- Matrix file is auditable artifact that can be cited in
  conversations with adopters (`SPEC/v1/claude-sdk-compat.md` is
  the answer to "which Claude Code versions does this work with?").

**Negative:**

- Maintainer burden: someone has to keep the matrix current (estimated
  10 min per Anthropic minor release; quarterly).
- False sense of safety risk: a GREEN listing only means we
  didn't observe breakage in our test runs — it does not prove
  semantic equivalence. Mitigation: §Test coverage requires the
  conformance harness to pass before adding a GREEN row.
- Empty RED list initially: until we observe a breaking change in
  the wild, no upstream version is RED. The script's fail-closed
  branch is exercised only by tests.

**Neutral:**

- `CLAUDE_VERSION` env override is a deliberate seam for adopter
  testing + CI mock — adopters can pin a specific version
  programmatically without touching the matrix.

## Test coverage

`scripts/tests/test_check_sdk_compat.py` ships 8 tests (the original
PLAN-056 spec called for 4; doubled during draft to cover edge cases):

1. `test_listed_green` — version in GREEN matrix → exit 0 + INFO line.
2. `test_listed_red` — version in RED matrix → exit 1 + ERROR line.
3. `test_unlisted_fail_open` — version not in either matrix → exit 0
   + WARN line.
4. `test_malformed_version` — `claude --version` returns garbage →
   exit 0 + WARN line.
5. `test_no_binary` — `claude` not in PATH → exit 0 + silent skip.
6. `test_env_override_beats_binary` — `$CLAUDE_VERSION` overrides
   binary output.
7. `test_major_minor_extraction` — only major.minor compared; patch
   irrelevant for matrix lookup.
8. `test_red_beats_green` — if a version is in BOTH RED and GREEN
   (impossible in practice but defensive), RED wins.

All 8 pass on script ship at HEAD `c713651` (verified Session 71
Wave D-3 2026-04-28).

## Wiring (Phase 2 acceptance)

`.github/workflows/validate.yml` MUST include an advisory step:

```yaml
- name: SDK compat advisory (PLAN-056 Phase 2 / ADR-094)
  continue-on-error: true
  run: |
    bash .claude/scripts/check-sdk-compat.sh
```

The step is advisory (`continue-on-error: true`) so a WARN does not
break the framework's own CI. A future ADR may flip to strict for
the framework's own dogfood after a 14-day soak with zero WARN
spikes — analogous to `FUNCTION-LENGTH-POLICY.md` §Path to strict-
gate.

## Owner ceremony (round-5)

Promotion from `.claude/plans/PLAN-056/adr-drafts/ADR-094-*.md` to
`.claude/adr/ADR-094-*.md` requires:

- `round-5/approved.md` sentinel listing this ADR path under `Scope:`
- Owner GPG signature on the sentinel
- One-line edit to `validate.yml` adding the advisory step
- One-line edit to `.claude/adr/README.md` index appending ADR-094

All four edits in a single ceremony script
(`OWNER-WAVE-D-3PLUS-CEREMONY.sh` — staged at
`.claude/plans/PLAN-044/audit-v2/staged-wave-d-3plus/`).

## References

- PLAN-056 Phase 2 spec: lines 207-242 of
  `.claude/plans/PLAN-056-framework-landscape-closeout.md`
- SPEC: `SPEC/v1/claude-sdk-compat.md`
- Script: `.claude/scripts/check-sdk-compat.sh`
- Tests: `.claude/scripts/tests/test_check_sdk_compat.py`
- Companion: ADR-085 (framework-landscape-claude-only) — establishes
  why this matrix is single-vendor (Claude only) and not multi-SDK.

## Closure

This ADR + the wiring above close PLAN-056 Phase 2's reopen trigger
("Phase 2 SDK compat empirical validation against current Claude
Agent SDK release"). Phases 1, 3, 4, 5 of PLAN-056 are tracked
separately under their own ADRs (085, 086, 087, 088).
