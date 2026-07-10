# Hook Adapter Layer — Harness Adapters

The ceo-orchestration framework's hooks communicate with the host harness
via the **Adapter Layer** (ADR-008). A hook reads a `NormalizedEvent` via
the resolved adapter's `read_event()` and emits a `Decision` via that same
adapter's `emit_decision()`. Hooks stay harness-agnostic; adapters
translate the wire.

> **Two different layers, do not conflate them.** This document is about
> the **host hook-dispatch adapters** — the modules that parse a harness's
> lifecycle-hook envelope (`PreToolUse`, `PostToolUse`, `Stop`, …) and emit
> the harness's decision shape. There is a **separate** LLM-invocation
> adapter layer under `.claude/hooks/_lib/adapters/live/` (used by the
> pair-rail reviewer and the batch path) that carries its own
> `gemini`/`openai`/`local` modules; that layer is described by
> [`provider_capability_matrix.md`](provider_capability_matrix.md), not by
> the registry below. The two share a directory name and nothing else.

## Available hook-dispatch adapters

The authoritative list is `KNOWN_ADAPTERS` in
`.claude/hooks/_lib/contract.py` (mirrored by `ADAPTER_REGISTRY` in
`.claude/hooks/_lib/adapters/__init__.py`). As of this writing it is
**exactly** `["claude", "codex"]` — those are the only two host-dispatch
adapter modules on disk (`.claude/hooks/_lib/adapters/claude.py`,
`.claude/hooks/_lib/adapters/codex.py`). There is no top-level
`gemini.py` / `openai.py` / `local.py` hook-dispatch adapter; earlier
editions of this page documented three that were never in the registry
and are not on disk — that prose is removed.

### `claude` (default) — PRODUCTION

- Module: `.claude/hooks/_lib/adapters/claude.py`
- Parity: FULL. Exercised by every enforcement hook + the golden/drift
  suites (`test_adapter_golden.py`, `test_adapter_drift_detector.py`).
- Wire shape: Claude Code `PreToolUse` / `PostToolUse` JSON envelope
  documented in `SPEC/v1/hook-io.schema.md`.
- Output shape: single-line
  `{"decision":"allow|block","reason":"...","systemMessage":"...","message":"..."}`
  on stdout; exit 0.

### `codex` (OpenAI Codex CLI) — per-rail; **verified against codex-cli 0.139.0**

- Module: `.claude/hooks/_lib/adapters/codex.py` (host mode added in
  PLAN-155 Wave 1). The same module also carries the pair-rail
  reviewer-egress helpers (`parse_verdict*`, `make_invoke_command*`,
  `parse_usage_from_codex_stdout`) — one module, two documented roles;
  the host-mode `read_event`/`write_decision` surface is the new work and
  the reviewer-egress helpers are untouched by it.
- Wire shape (host mode): Codex lifecycle-hook stdin JSON (snake_case:
  `hook_event_name`, `tool_name`, `tool_input`, `tool_response`,
  `session_id`, `cwd`, `turn_id`, …), deliberately Claude-compatible
  upstream. `apply_patch` tool calls are normalized to `Edit`/`Write`
  semantics and carry the **full path list** parsed from the patch body
  (the guard denies if ANY path in a multi-file patch is guarded).
- Output shape (host mode): `{"hookSpecificOutput": {"hookEventName": …,
  "permissionDecision": "deny"|"allow", "permissionDecisionReason": …}}`
  for PreToolUse; `{"decision":"block","reason":…}` for Stop;
  `{"hookSpecificOutput": {…, "additionalContext": …}}` for SubagentStart.
  Exit 2 + stderr is the deny alias for catastrophic paths.
- Selection: `CEO_HOOK_ADAPTER=codex`. The Codex-side registration
  (`.codex/hooks.json`, or a `[hooks]` table in `.codex/config.toml`)
  invokes the **same** Python hooks with `CEO_HOOK_ADAPTER=codex` set —
  one enforcement kernel, two harnesses, no hook forks.

#### Per-rail status under Codex (each row tied to the wave that made it true)

Vocabulary is the house capability-matrix doctrine (ENFORCED / ADVISORY /
ABSENT); the residual is part of the claim, not a footnote. Full normative
text is [`provider_capability_matrix.md`](provider_capability_matrix.md)
and ADR-161; the source of truth for each `deny` is the behavioral
positive-control replay, not the existence of a config file.

| Rail | Codex primitive | Status | Wave | Residual + backstop |
|---|---|---|---|---|
| Canonical-edit guard | PreToolUse `apply_patch\|Edit\|Write\|mcp__.*` → deny | **ENFORCED** (edit-time) | 1 | Writes smuggled through complex shell (shell-escape class, same as Claude Code) and `apply_patch` **Update** hunks whose full new content is not reconstructable from the wire; path-level gates still apply to every path in the patch. Backstops: `^Bash$` rail sees the full command; CODEOWNERS + branch protection at push. |
| Bash safety | PreToolUse `^Bash$` running our hook + `.codex/rules/ceo.rules` `prefix_rule(decision=forbidden)` coarse backstop | **ENFORCED** | 1, 3 | Official Codex caveat: it "doesn't intercept all shell calls yet, only the simple ones". Our hook receives the full string on every event that fires and applies our own parser (`_e3` whole-command gate stays fail-closed on input). |
| Plan lifecycle | PreToolUse on `.claude/plans/**` writes; per-op reconstructed content for `apply_patch` Add ops | **ENFORCED** (edit-time) | 1 | Same shell-escape residual; Update-hunk content-gating gap (path gates still fire); CI plan-schema checks at push. |
| Arbitration kernel | PreToolUse unconditional deny on kernel paths (any kernel path in a multi-file patch) | **ENFORCED** (edit-time) | 1 | Same residual class; kernel paths also in CODEOWNERS. |
| Kill-switch protection (`.codex/hooks.json`, `.codex/config.toml`, `.codex/rules/ceo.rules`, `requirements.toml`, operator `AGENTS.md`) | Registration surface enters the canonical deny matcher + SessionStart boot re-hash tripwire | **ENFORCED at edit-time; ADVISORY (boot-time) between sessions** | 3b | The boot-tripwire baseline is agent-writable (per-project state dir); the edit-time canonical guard is the real protection, the boot re-hash is the backstop, CODEOWNERS/CI is the final backstop. |
| Audit HMAC chain | PostToolUse `*` per-tool append (`codex_tool_recorded`) + SessionStart boot + `codex_turn_ended` turn-level backstop | **ENFORCED, completeness-bounded** | 4 | Per-edit completeness is best-effort while shell interception is partial — absence of an entry is not evidence of absence of activity. `verify_chain()` is unchanged and green over what was written. |
| Config protection | Edit-time PreToolUse deny + `requirements.toml` MANAGED hooks (trusted-by-policy) | **ENFORCED at edit-time; ADVISORY between sessions** | 3b | Codex has **no ConfigChange event** — continuous tamper observation degrades to boot-time re-check (SessionStart). Backstop: boot re-hash + CI. |
| Inverted pair-rail | Codex operates, reviewer = `claude -p`; Stop hook `decision:block` auto-continues until the review ran; git pre-push backstop | **PARTIAL** (stop-time + push-time, not per-edit) | 6 | Killing the session or refusing twice abandons the Stop gate (pre-push gate is the teeth); reviewer-model pin is PROVISIONAL (OQ3, `claude-opus-4-8`, override `CEO_PAIR_RAIL_REVIEWER_MODEL`). |
| Spawn governance | SubagentStart hook | **ADVISORY** — real gap: `continue:false` is parsed but does NOT stop the subagent (verified 0.139) | 2, 6 | `additionalContext` injects the profile/skill/file-assignment requirement; spawns routed via `^Bash$` (`claude -p` / `codex exec`) re-gain the ENFORCED gate; Wave 6 pre-push/CI scan over the chain's spawn records. **Never documented as enforced.** |

**Failure semantics (recorded live, `failure-semantics-matrix.md`).**
codex-cli 0.139.0 is **fail-open on everything except an explicit deny**
(`permissionDecision: deny` or exit 2): a hook that times out, crashes,
emits malformed or foreign JSON, or is untrusted/modified waves the tool
call through with no model-visible signal. The PLAN-152 C4
fail-closed-on-INPUT invariant is therefore implemented **inside** our
hooks (parse failure at a security matcher → emit the deny envelope),
never delegated to the harness. Every ENFORCED row above carries the
residual "hook death or de-trust degrades to silent allow; backstops:
boot-time arming check (installer), RED-on-absence chain assertions
(Wave 6), CODEOWNERS/CI at push."

**Trust keying (recorded live, `trust-keying-A6.md`).** Codex `/hooks`
trust is keyed to the hook **registration** hash (the command string),
**not** the hook program body. A framework upgrade that changes only hook
`.py` bodies does not re-prompt for trust; editing the registration
(`.codex/hooks.json` command string) flips the hook to `modified` and it
silently stops firing. Consequence: registration-file integrity is keyed
by Codex; hook-**body** integrity is ours to defend (the Wave 3b
kill-switch guard + boot re-hash and the existing canonical-edit guard
over `.claude/hooks/**`). "Installed but untrusted" is indistinguishable
from healthy at runtime — the installer's post-install arming check and
the Wave 6 RED-on-absence assertions are the only detection layer.

**Substrate boundary (binding).** CI certifies fixture-replay against a
recorded wire; only local live-fire certifies the real binary, per pinned
version. Local codex-cli is **0.139.0** (pin range
`.claude/governance/codex-cli-pin.txt` = `>=0.128.0,<0.140.0`); upstream
already ships 0.142.x, which is **outside** the pin — fixtures follow the
pin, never upstream. To record on a newer CLI, bump the pin via the
ADR-111 ceremony first, then re-record. A known 0.139 substrate gap: hook
discovery silently returns zero hooks inside a **git worktree** (plain
repo works) — the installer arming check detects-and-warns, and it is on
the substrate-watch per-bump re-test list.

## LLM-invocation adapters (`live/`) — a separate layer

`.claude/hooks/_lib/adapters/live/` holds `claude.py`, `claude_batch.py`,
`gemini.py`, `openai.py`, `local.py`. These are **not** hook-dispatch
adapters and are **not** in `KNOWN_ADAPTERS`. They are the reviewer /
batch LLM-invocation clients used by the pair-rail and related paths;
their protocol-level capability fields (`streaming_tool_use`, `json_mode`,
`function_calling`, …) are documented in
[`provider_capability_matrix.md`](provider_capability_matrix.md). Do not
select them with `CEO_HOOK_ADAPTER` — that variable resolves only against
`KNOWN_ADAPTERS`.

## Selecting a hook-dispatch adapter

At hook runtime the adapter is resolved via the **`CEO_HOOK_ADAPTER`**
environment variable. Precedence:

1. Explicit env-var (`CEO_HOOK_ADAPTER=<name>`) → if the name is in
   `KNOWN_ADAPTERS`, use it.
2. Absent or empty → `DEFAULT_ADAPTER` (`claude`).
3. Explicitly-set-but-unresolvable name, or a recognizably cross-harness
   envelope under the resolved adapter → this is an INPUT /
   mis-configuration failure per the PLAN-152 C4 taxonomy: **fail-CLOSED**
   (deny) with an audit breadcrumb, **not** a silent fallback to `claude`
   (the coherence gate, PLAN-155 debate A2).

### For Claude Code users (default path)

No env-var needed. Everything just works.

### For OpenAI Codex users

Install the Codex bundle with the installer:

```bash
./scripts/install.sh /path/to/your-app --harness codex
```

That emits `.codex/hooks.json`, `.codex/rules/ceo.rules`, and an operator
`AGENTS.md`, each registration invoking the shared hooks with
`CEO_HOOK_ADAPTER=codex`. **Nothing is enforced until you grant `/hooks`
trust** — the installer prints the exact trust steps and a
post-install arming check (`ARMED / NOT-ARMED-(untrusted) / BROKEN`) as
its final instruction. See [INSTALL.md](../INSTALL.md) `--harness codex`.

### In CI

`.github/workflows/validate.yml` runs the hook suite under BOTH
`CEO_HOOK_ADAPTER=claude` and `CEO_HOOK_ADAPTER=codex`, plus the codex
positive-control subprocess replay (planted violation on the shipped
`templates/codex/hooks.json` command line → assert `deny`). This is the T1
hermetic tier: recorded-wire replay, **no codex binary in CI**. The T2
local live-smoke tier is gated on `shutil.which("codex")` + the pin range
and is `pytest.mark`-skipped in CI with a reason string naming the local
runbook (visible, never silent). T3 is the release gate, which records the
fixture-set version certified against.

## Implementing a new hook-dispatch adapter

To add a new adapter `foo`:

1. **Create module** — `.claude/hooks/_lib/adapters/foo.py` implementing:
   - `ADAPTER_VERSION: str` (SemVer, e.g. `"1.0.0-rc.1"`)
   - `CAPABILITIES: dict` with the required keys per
     `SPEC/v1/adapters.schema.md §2.2`
   - `read_event(stream=None, phase="PreToolUse") -> NormalizedEvent`
   - `read_post_event(stream=None) -> NormalizedEvent` (convenience)
   - `write_decision(decision: Decision) -> str`
   - `emit_decision(decision: Decision, stream=None) -> None`
2. **Register** in `_lib/contract.py` and `_lib/adapters/__init__.py`:
   ```python
   KNOWN_ADAPTERS: List[str] = ["claude", "codex", "foo"]
   ADAPTER_REGISTRY: List[str] = ["claude", "codex", "foo"]
   ```
   Both `.claude/hooks/_lib/contract.py` and
   `.claude/hooks/check_arbitration_kernel.py` treat the adapter modules
   as kernel — extending the registry is a KERNEL-class edit requiring a
   plan-specific `CEO_KERNEL_OVERRIDE` + ACK on top of a sentinel.
3. **Ship fixtures** — capture **real** `foo` hook payloads to
   `.claude/hooks/tests/fixtures/adapters/foo/in/*.json` (at least 2,
   recorded from the live CLI, not hand-written from docs; each carries
   `_meta.<cli>_version`) + matching normalized expectations under
   `fixtures/adapters/foo/normalized/`.
4. **Write tests** — at minimum: parameterize the golden round-trip in
   `test_adapter_golden.py` over the new adapter (with a **minimum-fixture
   count** assertion — a `.gitkeep`-only dir must FAIL), extend
   `test_adapter_drift_detector.py` to scan the new call-sites, and add
   subprocess positive/negative/malformed controls on the **shipped**
   registration command line (in-process import-and-call replay is
   insufficient — it stays green through a dead gate).
5. **Document** — extend this file + add a row to
   `docs/provider_capability_matrix.md`. Write an ADR for material
   trade-offs (e.g. an output shape that deviates from Claude's
   single-line JSON convention — as the codex host-mode shape does,
   recorded in ADR-161).
6. **Credential hygiene check** — cover `sk-...`, `AKIA...`, JWT, Bearer,
   and env-var-leak shapes per SPEC §4.1.

## Contract invariants (all adapters must uphold)

- **Fail-open on infrastructure, fail-CLOSED on input at security
  matchers.** Malformed stdin from an infrastructure bug →
  `NormalizedEvent` with `parse_error` set; hook emits `allow` (or
  nothing, for PostToolUse observers). But unparseable input **at a
  security matcher** fails closed (deny), never waved through — the
  PLAN-152 C4 split. No hook exits non-zero on infrastructure bugs.
- **Phase is authoritative.** Hooks declare phase via
  `read_event(..., phase=...)` or `read_post_event()`. Adapters MUST
  preserve the declared phase even when payload shape is ambiguous.
- **Per-harness output contracts.** Each adapter emits its host harness's
  decision shape (Claude single-line JSON; Codex
  `hookSpecificOutput.permissionDecision`). "Parity" means strict
  normalized-**input** equality, not identical output bytes — the output
  contract is per-harness (ADR-161 A25).

## References

- ADR-008 — Hook Adapter Layer foundation
- ADR-012 — Cross-adapter golden fixtures
- ADR-028 — Multi-LLM canonical envelope parity
- ADR-161 — Codex harness capability matrix + host-adapter doctrine
- PLAN-155 — Codex harness compatibility (host-mode adapter, per-rail matrix)
- SPEC/v1/hook-io.schema.md — Claude wire format
- SPEC/v1/normalized_envelope.schema.md — canonical envelope
- SPEC/v1/adapters.schema.md — adapter ABI
- docs/provider_capability_matrix.md — per-provider capability gaps
- docs/degradation-outside-claude-code.md — enforcement boundary by harness
