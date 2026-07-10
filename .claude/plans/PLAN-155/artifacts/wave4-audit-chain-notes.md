# PLAN-155 Wave 4 — Codex audit-chain notes (SENT-CX-B / ADR-161 material)

Companion to the staged Wave-4 files under
`.claude/plans/PLAN-155/staged/wave-4/`. Records the live recording, the two
new actions, the empirical proof, and the honestly-impossible rows that go to
ADR-161's failure-semantics matrix + the plan §Deferred (NOT faked).

## Substrate + live recording (reused Wave-1 technique)

- **codex-cli 0.139.0** (verbatim `codex --version`), macOS arm64.
- Recorded a real end-to-end headless session:
  `codex exec --sandbox workspace-write --skip-git-repo-check "<prompt>"` in a
  throwaway scratch lab, with a project `.codex/hooks.json` registering a
  tee-recorder on `SessionStart` / `PostToolUse *` / `Stop`, trusted
  headlessly via `[hooks.state."<key>"] trusted_hash = "<currentHash>"` in a
  lab `$CODEX_HOME/config.toml` (hashes enumerated via
  `codex app-server` JSON-RPC `hooks/list`, exactly the Wave-1
  `trust-keying-A6.md` mechanism).
- **Result (rc 0):** 1 `SessionStart` + 5 `PostToolUse` (4 `Bash echo` + 1
  `apply_patch` Add-file) + 1 `Stop` (`stop_hook_active=false`), one coherent
  codex `session_id`. Captured verbatim; lab absolute paths rewritten to
  `/tmp/codex-lab` (contamination policy), all other bytes verbatim.
- Fixture:
  `staged/wave-4/.claude/hooks/tests/fixtures/adapters/codex/session/codex_session_e2e.json`
  (`_meta` carries the version pin + provenance).

## The two NEW actions (deny-by-default, metadata-only; `_KNOWN_ACTIONS` 314→316)

| action | rail | fields (all closed-enum / bool; NO body) |
|---|---|---|
| `codex_tool_recorded` (Wave 4-A) | per-tool PostToolUse append | `harness`=codex, `hook_event_name`∈{PostToolUse}, `tool_name_enum`∈{Bash,Edit,Write,Task,Read,MultiEdit,NotebookEdit,Glob,Grep,WebFetch,WebSearch,mcp_other,other} |
| `codex_turn_ended` (Wave 4-B) | turn-level backstop | `harness`=codex, `source`∈{stop,subagent_stop,notify,wrapper,other}, `stop_hook_active`(bool) |

Both DISTINCT from the claude-only `agent_spawn` AND from
`tool_call_lifecycle_recorded`, so the completeness query counts the per-tool
rail separately from the turn-level backstop. Emitted by `audit_log.py` under
`CEO_HOOK_ADAPTER=codex` (claude path byte-identical when the env var is
unset). Both route through dedicated `emit_generic` scrub branches +
per-action allowlists, NEVER `_EMIT_GENERIC_PASSTHROUGH`. Chain shape +
`verify_chain()` UNTOUCHED (append-only).

## Wrapper (Wave 4-C): `scripts/codex-exec-wrapper.sh`

Brackets a headless `codex exec` with a `session_start` boot row + a
`codex_turn_ended` (`source=wrapper`) row, so a run whose `.codex` hooks are
untrusted/unwired (the silent no-op class, `trust-keying-A6.md`) still lands a
2-row chain segment. Wrapper-bypass residual documented in the script header.

## Proof (all reproduced this pass, py 3.9.6 = repo floor)

- **End-to-end replay** (`test_codex_audit_chain.py`): the recorded fixture
  replayed through the REAL `audit_log.py` as SUBPROCESSES under
  `CEO_HOOK_ADAPTER=codex` → log with 1 `session_start` + 5
  `codex_tool_recorded` + 1 `codex_turn_ended`, all HMAC-bearing;
  `audit-verify-chain.py` **exit 0**. The completeness query IS the test:
  per-tool (5) vs turn-level (1) countable separately by action name.
- **Anti-vacuity mutation control:** blinding the Stop/SubagentStop branch
  (so Stop mis-routes to `codex_tool_recorded`) turns the partition test RED
  (`0 codex_turn_ended != 1`). Running WITHOUT the Wave-1 host adapter
  mis-classifies all 7 events as PostToolUse → also RED. The certifying test
  has teeth.
- **Wrapper bracket:** running the wrapper with codex stubbed emits exactly
  `session_start` + `codex_turn_ended(source=wrapper)` under one wrapper
  session id; chain verifies exit 0.
- **Sec MF-3 scrub:** `emit_generic("codex_tool_recorded", command=..., tool_response=..., file_path=...)` and
  `emit_generic("codex_turn_ended", last_assistant_message=..., transcript_path=...)`
  drop every forbidden key before the wire (zero leakage); enum coercion
  (`bogus-source`→`other`, off-enum tool→`other`, `harness`→`codex`) verified.
- **Registry gate:** `check-audit-registry-coverage.py --verbose` →
  `OK: audit registry in sync (known=316, schema=316, …)`.
- **Pins rebaselined 314→316** (four unguarded count-companions, all based on
  the PLAN-154 sent-f overlay): `test_audit_emit_api_contract.py`
  (count + SHA `bcb1afc7…49ee` + 2 public emitters),
  `test_codex_egress_proof_telemetry.py`, `test_w5_scrub_enforcement.py`,
  `test_git_bypass_guard.py`. (MANIFEST-A open issue #1 was STALE — sent-f
  already moved all four to 314; wave-4 moves them to 316.)

## §Deferred — honestly impossible today (NOT faked)

- **TOTAL per-edit / per-tool completeness.** codex-cli 0.139 "doesn't
  intercept all shell calls yet, only the simple ones" — PostToolUse may not
  fire for every tool call, so a `codex_tool_recorded` row may be ABSENT.
  Absence of a row is NOT evidence of absence of activity (the same honest
  line as the degradation page). Recorded on the `codex_tool_recorded` SPEC
  row and in the emitter docstring. Backstops: the turn-level backstop +
  wrapper bracket, the Wave-6 RED-on-absence chain assertions, CI at push.
- **Continuous config-tamper observation from the chain.** codex has no
  ConfigChange event; the audit path cannot witness a between-sessions config
  mutation. Stays boot-time-only (SessionStart re-hash, Wave 3b). No audit
  action pretends to cover it.
- **mcp__\* PostToolUse fixture** still unrecorded (no MCP server in the lab,
  MANIFEST open issue #5): `codex_tool_recorded` folds `mcp__*`→`mcp_other`
  by construction, but the live wire shape is verified during Wave-6
  live-fire, not here.

## Coupling flagged to the orchestrator (landing order)

- `audit_log.py` + `_lib/audit_emit.py` are `_KERNEL_PATHS` → Wave-4 ceremony
  needs `CEO_KERNEL_OVERRIDE=PLAN-155-CODEX-AUDIT-ACTIONS` +
  `CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT` on top of SENT-CX-B (pair-rail S265 F3).
- Base rule used: `audit_log.py` = repo file (no wave/sent-f base);
  `audit_emit.py` + SPEC + `test_audit_emit_api_contract.py` +
  the three extra count-companions = PLAN-154 sent-f overlay (314 baseline).
- Wave-4 depends on Wave-1 host adapter being landed first (host-mode
  `codex.py`); the test fails LOUD (not skip) if it is absent.
- No `validate.yml` edit needed: `.claude/hooks/tests/` is dir-collected by
  validate.yml (`pytest .claude/hooks/tests/ -n auto`), so
  `test_codex_audit_chain.py` runs implicitly. An EXPLICIT path is a
  SENT-CX-D / Wave-6 decision (MANIFEST open issue #7).
