# PLAN-155 Wave 1 — Dispatch seam (debate A1, option b): contract + control evidence

Produced 2026-07-10 by the Wave-1 dispatch-seam agent. Staged files:

- `staged/wave-1/.claude/hooks/check_canonical_edit.py`
- `staged/wave-1/.claude/hooks/check_bash_safety.py` (base = **PLAN-154
  `staged/sent-f` copy** per the special base rule — PLAN-154 lands first;
  the seam diff was measured against that base, not repo `main`)
- `staged/wave-1/.claude/hooks/check_plan_edit.py`
- `staged/wave-1/.claude/hooks/check_arbitration_kernel.py`
- `staged/wave-1/.claude/hooks/tests/test_adapter_seam_dispatch.py`

Diff shape per hook (surgical, downstream decide() logic untouched):

- import seam (`from _lib import adapters as _adapters`), resolve ONCE per
  invocation (`_adapter = _adapters.resolve()`), all
  `read_event`/`emit_decision` call sites now go through `_adapter`.
- `check_canonical_edit.py` / `check_arbitration_kernel.py` additionally
  gained a module-level `_emit_legacy_decision_json(out, adapter)` helper:
  their `decide()` returns pre-built Claude-shaped JSON strings that were
  written RAW to stdout — under the claude adapter the raw write is kept
  (byte identity), under any other adapter the string is parsed back into
  a neutral `Decision` and re-emitted via `adapter.emit_decision` (a raw
  Claude-shaped line is foreign JSON on the codex wire → verified silent
  fail-open → S254 dead-gate class). This covers the fail-CLOSED
  `_emit_block` paths too (canonical hook-fault; kernel parse-error and
  decide()-raise paths).
- `check_bash_safety.py` RETAINS `from _lib.adapters import claude as
  _claude_adapter` as a back-compat alias ONLY (in-process surface used by
  `tests/test_check_bash_safety_h5_rewrite.py:350,366`); no dispatch path
  uses it. Marked in-source for removal when that test migrates.
- `check_arbitration_kernel.py` resolves INSIDE its existing
  infrastructure fail-open try (import-failure still → raw allow), so the
  C4 infra contract is preserved; plan/bash resolve BEFORE their fail-open
  try so a seam failure is never swallowed into an allow.

## Seam contract the staged hooks + test PIN (for the host-adapter agent's `_lib/adapters/__init__.py`)

`_lib.adapters.resolve() -> module` (once per hook invocation):

1. `CEO_HOOK_ADAPTER` unset or `""`/whitespace → the **claude** adapter
   module. Downstream hook behavior must be BYTE-IDENTICAL to pre-seam
   (control below proves the staged hooks hold their side).
2. `CEO_HOOK_ADAPTER` = registered name → that adapter module, exposing at
   least `read_event(stream=None, phase="PreToolUse")` (bash-safety also
   passes `stream=`) and `emit_decision(decision)`.
3. **Debate A2 (INPUT class, PLAN-152 C4)** — explicitly-set-but-
   unresolvable value → fail-CLOSED **inside resolve()**: write the reason
   to stderr **naming `CEO_HOOK_ADAPTER`**, leave an audit breadcrumb
   under the `CEO_AUDIT_LOG_*` area whose text contains `adapter`
   (reference used `emit_veto_triggered(hook="adapter_seam",
   reason_code="adapter_resolution_failed", ...)` + an
   `audit-log.errors` line), then `raise SystemExit(2)`. Exit 2 + stderr
   is the deny alias on BOTH harness wires (codex: `e2-exit2` transcript;
   claude: blocking error). `SystemExit` is a `BaseException`, so it
   propagates through every `except Exception` fail-open path in the
   hooks — the hooks deliberately contain NO copy of the gate.
   NEVER fall back to claude for a non-empty unknown value (mutation
   control below proves the test catches that anti-pattern).
4. Infrastructure failure inside resolve() (broken import with a
   valid/unset env) → ordinary exception; the hooks preserve their
   pre-seam infra behavior (kernel: raw allow; bash/plan: uncaught →
   exit 1, the same class as the old module-level import crash;
   canonical: uncaught → exit 1).

Codex host-mode normalization the seam TEST additionally pins (from the
recorded 0.139 fixtures; consistent with `normalization-notes.md`):

- `Bash` → command string passthrough (`tool_input.command`).
- `apply_patch` `*** Update File: <p>` → Edit-semantics with
  `event.file_path = <p>`; `*** Add File: <p>` → Write-semantics with
  `tool_input.content` synthesized from the `+` body lines (check_plan_edit's
  Write path reads `tool_input["content"]`).
- deny egress = `{"hookSpecificOutput": {"hookEventName": "PreToolUse",
  "permissionDecision": "deny", "permissionDecisionReason": ...}}`, rc 0;
  allow egress = `{}` (or an explicit non-deny envelope); NEVER a
  top-level Claude `decision` key.

## Control evidence (scratch lab, 2026-07-10; lab = repo hooks + staged overlay + THROWAWAY reference seam/codex-host adapter — reference code lives in the lab only, at `scratchpad/seamlab/`, and is NOT shipped)

1. **Seam suite green**: `tests/test_adapter_seam_dispatch.py` → 8 passed
   (codex deny per hook incl. deny-reason class; codex benign non-deny;
   claude violation/benign legacy shapes; unset vs `=claude` vs `=""`
   byte-identical; A2 rc-2 fail-closed + breadcrumb + no-silent-fallback).
2. **Byte-identity control** (`seamlab/byte_identity_control.py`): 12
   payloads (violation + benign + malformed-stdin per hook) × {unset,
   `claude`} — staged vs pre-seam stdout+rc **24/24 identical, 0
   mismatches**. Pre-seam baseline for bash-safety = the PLAN-154 sent-f
   base.
3. **Dead-gate mutation** (suite run against PRE-seam hooks): 4 failed /
   4 passed — `test_codex_violation_denied_per_hook` and all three
   `SeamCoherenceGateTest` tests go RED, i.e. the suite detects the S254
   dead-gate class; the claude-regression tests stay green against the
   pre-seam baseline as expected.
4. **Silent-fallback mutation** (resolve() mutated to fall back to claude
   on a bogus value): all 3 coherence tests RED.
5. **Existing per-hook suites vs staged hooks** (lab, `.claude` layout):
   canonical/kernel/plan suites (10 files) → 269 passed, 11 skipped;
   bash-safety suites (4 files incl. `h5_rewrite` alias consumer) → 205
   passed, 3 xfailed; `test_adapter_seam_dispatch.py` +
   `test_hook_byte_fidelity.py` → 15 passed.

## Open coupling notes

- Multi-file apply_patch: one patch can touch MANY files; the four hooks'
  downstream logic was deliberately NOT changed (assignment bar), so a
  guarded path in the SECOND header of a multi-file patch is gated only if
  the host adapter surfaces it (e.g. picks the guarded path as
  `file_path`, or expands to per-file events). Adapter-side decision —
  named residual until the host-adapter agent lands its normalization
  (`normalization-notes.md` requires the full path list on the normalized
  event).
- `mcp__*` PreToolUse under codex: no recorded fixture yet (known gap);
  the canonical hook's mcp candidate-path logic is untouched.
- The A2 "recognizably cross-harness envelope" half of the coherence gate
  is adapter/seam-side and not exercised by this suite — it belongs to the
  host-adapter agent's golden/coherence tests.
