# Gemini Adapter — Shape Gaps (Sprint 6)

PLAN-006 Phase 2a shipped the `adapters/gemini.py` stub. Sprint 7
Phase 2b closes these gaps with captured real-world payloads.

## Known unknowns

1. **Top-level field name for tool identifier.** Stub probes `tool`,
   `tool_name`, `toolName`, `operation`, `op` in that order. Real
   shape TBD.
2. **Top-level field name for tool input.** Stub probes `tool_input`,
   `args`, `parameters`, `input`, `params`. Real shape TBD.
3. **Session ID field.** Stub probes `session_id`, `sessionId`,
   `session`. Real shape TBD.
4. **PostToolUse response block.** Stub probes `tool_response`,
   `response`, `result`, `output`. Real shape TBD.
5. **Phase distinction.** Claude CLI uses separate `hook_event_name`
   values; Gemini may use endpoint URL / command-line flag / nothing.
   Stub defaults to PreToolUse; hooks declare phase explicitly via
   `read_event(..., phase=...)` or `read_post_event()`.
6. **Decision output shape.** Stub emits Claude-compatible
   `{"decision":"allow|block","reason":"..."}` JSON line. Gemini may
   expect a different shape (e.g. exit code only, stdout structured
   differently). Real shape TBD.
7. **Fail-open semantics.** Stub follows Claude's fail-open contract
   (exit 0 + allow). Gemini's expected behavior TBD.

## How to close a gap

1. Capture a real Gemini CLI hook invocation (any tool):
   ```
   # Placeholder — exact capture mechanism Sprint-7-work
   CEO_CAPTURE_HOOK_PAYLOAD=/tmp/gemini-hook-capture.json \
     <gemini-cli-hook-trigger>
   ```
2. Save as `in/<scenario>.json` in this directory
3. Update `adapters/gemini.py` probes/aliases as needed
4. Add normalized expectation to `fixtures/normalized/<scenario>.json`
   if the scenario is cross-adapter reusable
5. Add targeted unit tests to `tests/test_adapter_gemini.py`

## Placeholder fixtures (Sprint 6)

The `in/` directory contains placeholder fixtures that match the
stub's probe order. They are NOT captured from real Gemini CLI.
Sprint 7 replaces them.
