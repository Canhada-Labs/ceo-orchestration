# ADR-008: Hook Adapter Layer (neutral event/decision contract)

## Status: ACCEPTED (2026-04-12)

## Context

PLAN-004 Phase 4 consensus finding C4 (VP Engineering R-ARCH1, AI-Security
implicit): every hook currently depends on Claude Code's specific JSON
payload shape (`_lib.payload.parse_stdin` returns a `HookPayload` that
maps to Claude's fields). If the only adopter's IDE changes its contract
or a second IDE (Gemini CLI, Codex CLI) must be supported, every hook
needs a rewrite.

VP Engineering P1 warned against premature abstraction: "Building an
adapter for a hypothetical Gemini user spends complexity budget now."
Consensus C4 reclassified Phase 4 as **refactor-only**: ship the
contract + Claude adapter, behavior-identical; defer Gemini/Codex.

## Decision Drivers

- **Portability optionality.** A stable, IDE-agnostic contract lets a
  non-Claude adapter plug in later without forking hooks.
- **Zero behavioral regression.** 168 existing hook tests MUST continue
  to pass without modification. The Claude adapter is a near-identity
  map over the existing `_lib.payload` + stdout format.
- **Incremental migration.** Hooks do NOT have to adopt the adapter
  immediately. The contract is available; each hook migrates on its
  own schedule.
- **Stdlib-only.** No new deps. Dataclasses + json only.

## Options Considered

### Option A: Ship contract + Claude adapter, don't rewire hooks yet (chosen)

- **Pros:** zero regression risk; adapter is purely additive; existing
  hooks untouched; future hooks can adopt natively; Gemini/Codex can
  plug in by adding one module.
- **Cons:** `_lib.payload` + adapter coexist temporarily — some hooks
  use old path, future hooks use new path. Sprint 5 can migrate each
  hook behind its own PR.

### Option B: Ship contract + rewire all 4 hooks in one commit

- **Pros:** single-SoT sooner; no dual path.
- **Cons:** ~400 LOC across 4 hooks; high regression risk; 168 tests
  must all verify behavior preserved under a refactor that's hidden
  inside decide() rewrites. Consensus C4 explicitly rejected this
  scope for Sprint 4.

### Option C: Defer HAL entirely to Sprint 5

- **Pros:** zero cost now.
- **Cons:** no contract forces itself on the ecosystem; future
  adapters have nothing to align against; the neutral-event debate
  happens in Sprint 5 instead of being settled.

## Decision

**Option A.**

### The contract: `_lib/contract.py`

- `NormalizedEvent` dataclass — neutral payload representation with
  field names that already match Claude Code exactly (session_id,
  tool_name, tool_input, tool_response, description, prompt,
  subagent_type, file_path, old_string, new_string, replace_all,
  command). Optional `parse_error` for fail-open propagation.
- `Decision` dataclass — allow/block + reason + optional system_message
  / message. Builder helpers: `allow()`, `block(reason)`,
  `.with_reason()`, `.as_allow()`.
- `KNOWN_ADAPTERS = ["claude"]`, `DEFAULT_ADAPTER = "claude"`.

### The Claude adapter: `_lib/adapters/claude.py`

- `read_event(stream=sys.stdin) -> NormalizedEvent` — wraps existing
  `_lib.payload.parse_stdin`; preserves fail-open semantics.
- `write_decision(decision: Decision) -> str` — serializes to Claude
  Code's expected one-line JSON (decision + reason + optional
  systemMessage + message), ensure_ascii=False.
- `emit_decision(decision, stream=sys.stdout)` — convenience +\n.

### What the contract does NOT ship (per C4)

- Gemini CLI adapter (deferred to Sprint 5 — pending real user)
- Codex CLI adapter (deferred indefinitely)
- Hook rewiring (deferred to Sprint 5; each hook migrates independently)
- `CEO_HOOK_ADAPTER` env-var selection (implemented as constant today;
  env-var wiring lands when the second adapter does)

> **Sprint 6 update (2026-04-13):** PLAN-006 reverses the "each hook
> migrates independently" deferral and ships all 6 hook migrations in
> Sprint 6 Phase 1. See **ADR-014 — Hook Adapter Migration Batch
> Policy** for the batch-policy decision (1-per-commit, mixed-mode
> support, byte-identity fixture gating). Gemini adapter ships as
> **stub + fixture capture** in Sprint 6 Phase 2a; real parity
> remains deferred to Sprint 7.

### Future migration path (documented but not executed)

When Sprint 5 migrates hook X to the adapter:

```python
# before
from _lib import payload as _payload
def main():
    p = _payload.parse_stdin()
    decision = decide(description=p.description, prompt=p.prompt, ...)
    print(decision.to_json())

# after
from _lib.adapters import claude as claude_adapter
from _lib import contract
def main():
    event = claude_adapter.read_event()
    decision = decide_normalized(event)   # takes NormalizedEvent
    claude_adapter.emit_decision(decision)
```

Observable output MUST remain byte-identical (verified against the
hook's existing fixture suite).

## Consequences

### Positive

- A second IDE can plug in by adding `_lib/adapters/<name>.py` with
  `read_event` + `write_decision`. No hook changes required to gain
  multi-IDE support (once hooks migrate).
- The neutral contract is locked before a second consumer forces a
  compromise. Dataclass field names mirror Claude Code so the adapter
  is boring today; future adapters carry the translation burden.
- 168 existing hook tests untouched. 21 new tests lock the contract.

### Negative

- Temporary duality: some hooks continue to import `_lib.payload`
  directly (v1 path), while `contract.py` is available but unused.
  Acceptable for one sprint; fully migrated in Sprint 5.
- `HookPayload` and `NormalizedEvent` overlap in fields. Until
  migration, there is duplication. `NormalizedEvent` is the canonical
  forward path; `HookPayload` is internal to `_lib.payload`.

### Neutral

- Adapter package layout (`_lib/adapters/`) is new but lightweight
  (2 files today, stdlib-only).

## Blast Radius

- `.claude/hooks/_lib/contract.py` (NEW, ~110 LOC)
- `.claude/hooks/_lib/adapters/__init__.py` (NEW, package marker)
- `.claude/hooks/_lib/adapters/claude.py` (NEW, ~90 LOC)
- `.claude/hooks/tests/test_contract.py` (NEW, 21 tests)
- Existing hooks (`check_agent_spawn.py`, `check_plan_edit.py`,
  `check_bash_safety.py`, `audit_log.py`) — **UNCHANGED**

**Reversibility:** HIGH — additive files only. Rollback = delete
`contract.py`, `adapters/`, `test_contract.py`.

## References

- PLAN-004 §3 Phase 4
- PLAN-004/debate/round-1/vp-engineering.md §R-ARCH1
- PLAN-004/debate/round-1/consensus.md §C4
- ADR-002 (hooks package layout — `_lib/` placement rule)

## Enforcement commit

`e83570766079` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
