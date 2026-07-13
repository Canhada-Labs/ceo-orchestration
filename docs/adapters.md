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
**exactly** `["claude", "codex", "grok"]` — those are the only three
host-dispatch adapter modules on disk (`.claude/hooks/_lib/adapters/claude.py`,
`.claude/hooks/_lib/adapters/codex.py`,
`.claude/hooks/_lib/adapters/grok.py`). There is no top-level
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

### `grok` (xAI Grok Build CLI) — per-rail; **verified against grok 0.2.93**

- Module: `.claude/hooks/_lib/adapters/grok.py`. Grok Build reads the
  framework's legacy-compat `.claude/settings.json` as a Claude-compatible
  hook registration, so the **single registration surface is the
  `.claude/settings.json` the framework already ships**. The grok path
  deliberately does **not** emit a `.grok/hooks/` bundle: arming both
  surfaces makes grok 0.2.93 fire every hook **twice** on the same tool
  call (an HMAC double-count), with no documented runtime kill switch for
  the duplication. (This inverts the original single-vs-dual-surface design
  question, OQ1.)
- Wire shape: grok lifecycle-hook stdin JSON with **camelCase** keys
  (`hookEventName`, `toolName`, `toolInput`, `workspaceRoot`, `sessionId`,
  `toolUseId`) and **snake_case** event values (`pre_tool_use`). Tool names
  arrive under grok's **native** vocabulary and the adapter aliases them at
  both the matcher and the wire: `Bash`→`run_terminal_command`,
  `Read`→`read_file`, `Edit`/`Write`/`MultiEdit`→`search_replace`,
  `Grep`→`grep`, `Glob`/`ListDir`→`list_dir`, `WebSearch`→`web_search`,
  `Task`→`spawn_subagent`.
- Blocking surface: **`pre_tool_use` is the only blocking event.** Stop,
  UserPromptSubmit, and SubagentStart are **passive** (non-blocking) under
  grok — they can observe and inject context but cannot deny.
- Vocabulary / exit discipline (grok-scoped): grok does **not** understand
  `{"decision":"block"}` — it treats that shape as malformed output and
  **fail-OPENs, even with exit 2** (probe P5). So the `_python-hook.sh`
  shim rewrites `block`→`deny` whenever `CEO_HOOK_ADAPTER=grok` (this is the
  enforcement mechanism, not a convenience — it is not disableable) and
  maps `deny`→exit 2 as a belt-and-suspenders second channel
  (`CEO_HOOK_EXIT_MAP=0` disables only the exit-code mapping). The rewrite
  is grok-gated: exit 2 is already an **active** deny in Codex PreToolUse
  (not inert), so Claude and Codex output stay byte-identical and only grok
  gets the translation.
- Output shape (host mode): a single-line `deny`/`allow` decision the shim
  translates for grok as above; on the enforced `pre_tool_use` path a deny
  surfaces as exit 2 + stderr.
- Selection: `CEO_HOOK_ADAPTER=grok`, set on the hook invocations inside the
  shipped `.claude/settings.json` when the grok bundle is installed — one
  enforcement kernel, now three harnesses, no hook forks.

#### Per-rail status under Grok (each row tied to its mechanism)

Same house vocabulary (ENFORCED / ADVISORY / ABSENT); the residual is part
of the claim, not a footnote. Full normative text is ADR-162 and
[`provider_capability_matrix.md`](provider_capability_matrix.md); the source
of truth for each `deny` is the behavioral positive-control replay, not the
existence of a config file.

| Rail | Grok primitive | Status | Residual + backstop |
|---|---|---|---|
| Canonical-edit guard | `pre_tool_use` `search_replace\|run_terminal_command\|mcp__.*` → deny (grok's native tool names) | **ENFORCED** (edit-time) | Writes smuggled through complex shell (shell-escape class, same as Claude/Codex); every path in a multi-file edit is still gated. Backstops: the `run_terminal_command` rail sees the full command; CODEOWNERS + branch protection at push. |
| Bash safety | `pre_tool_use` on `run_terminal_command` (grok's native name for `Bash`) running our parser | **ENFORCED** | The hook fires only on the events grok surfaces; the `_e3` whole-command gate stays fail-closed on input. |
| Plan lifecycle | `pre_tool_use` on `.claude/plans/**` writes | **ENFORCED** (edit-time) | Same shell-escape residual; CI plan-schema checks at push. |
| Arbitration kernel | `pre_tool_use` unconditional deny on kernel paths (any kernel path in a multi-file edit) | **ENFORCED** (edit-time) | Same residual class; kernel paths also in CODEOWNERS. |
| Kill-switch protection (`.grok/hooks/**`, `.grok/config.toml`, `.grok/sandbox.toml`, `.grok/rules/*.md`) | The `.grok` config/registration surface enters the canonical deny matcher | **ENFORCED at edit-time; ADVISORY between sessions** | Grok has no continuous config-change event, so between-session config protection degrades to advisory; the edit-time canonical guard is the real protection, CODEOWNERS/CI is the backstop. |
| Audit HMAC chain | Post-tool per-tool append (`grok_tool_recorded`) + `grok_turn_ended` turn-level backstop (turn accounting rides the passive Stop event) | **ENFORCED, completeness-bounded** | Headless `SessionEnd` is not reliable, so completeness is bounded by turn accounting; `verify_chain()` is unchanged and green over what was written — absence of an entry is not evidence of absence of activity. |
| Config protection | Edit-time `pre_tool_use` deny; between-session re-check only | **ENFORCED at edit-time; ADVISORY between sessions** | No continuous config-change event; backstop is CI. |
| Inverted pair-rail | Grok operates, reviewer = `claude -p`; grok's **Stop is passive** and cannot force the review, so the **git pre-push gate is the teeth** (`templates/grok/pre-push-review-gate.sh`) | **ADVISORY at Stop; ENFORCED at push (pre-push gate)** | An operator who never pushes never triggers the gate; reviewer-model pin PROVISIONAL (override `CEO_PAIR_RAIL_REVIEWER_MODEL`). |
| Spawn governance | `Task`→`spawn_subagent` alias exists, but SubagentStart is **passive** | **ADVISORY** — the spawn event cannot deny under grok | `additionalContext` injects the profile/skill/file-assignment requirement; spawns routed via `run_terminal_command` (`claude -p` / `codex exec` / `grok`) re-gain the ENFORCED gate; pre-push/CI scan over the chain's spawn records is the backstop. **Never documented as enforced.** |

**Failure semantics.** Grok hooks **fail open**: a hook that crashes, times
out (5s default), or emits malformed output waves the tool call through
with no model-visible signal — and, per the vocabulary note above, a raw
`{"decision":"block"}` is itself "malformed" to grok, which is exactly why
the shim rewrites it to `deny`. The PLAN-152 C4 fail-closed-on-INPUT
invariant is therefore implemented **inside** our hooks (parse failure at a
security matcher → emit the deny envelope), never delegated to the harness.
Every ENFORCED row above carries the residual "hook death or an un-trusted
folder degrades to silent allow; backstops: boot-time arming check
(installer), RED-on-absence chain assertions, CODEOWNERS/CI at push."

**Trust keying.** Grok uses a **unified folder-trust** model — one grant
covers MCP, LSP, and hooks — granted via `/hooks-trust` or `grok --trust`
and persisted to `~/.grok/trusted_folders.toml`. **Nothing is enforced
until the folder is trusted**; until then hooks are silently skipped, and
"installed but untrusted" is indistinguishable from healthy at runtime. The
installer's arming check (`grok inspect` + refuse-on-drift) is the only
local detector.

**Substrate boundary (binding).** Grok Build is a rolling 0.x CLI shipping
**1–2 releases per day**, so the pin is an **exact version**, not a range:
`.claude/governance/grok-cli-pin.txt` = `grok 0.2.93` (a range would be
meaningless at that cadence). The installer is itself a rolling, non-pinned
script — it is fetched, hashed, `grok inspect`-ed, and only **then**
executed (never `curl | bash`); the binary-SHA pin is the real supply-chain
gate. `grok login` requires a SuperGrok / X Premium+ account; that account
exposes `grok-4.5` (default) and `grok-composer-2.5-fast` — **not**
`grok-build-0.1` — and the cross-vendor council's grok lane uses `grok-4.5`.

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

### For Grok Build users

Install the Grok bundle with the installer:

```bash
./scripts/install.sh /path/to/your-app --harness grok
```

Grok reads the framework's legacy-compat `.claude/settings.json` as a
Claude-compatible registration, so this arms a **single** hook surface (no
`.grok/hooks/` — a second surface would double-fire every hook on grok
0.2.93). The installer also emits an operator `AGENTS.md`,
`.grok/config.toml.example` + `.grok/sandbox.toml.example`, and the pre-push
review gate, then runs an arming check (`grok inspect` + refuse-on-drift).
**Nothing is enforced until you grant folder trust** (`grok --trust`,
unified across MCP/LSP/hooks). See [INSTALL.md](../INSTALL.md)
`--harness grok`.

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
- ADR-162 — Grok Build harness capability matrix + cross-vendor council
- PLAN-155 — Codex harness compatibility (host-mode adapter, per-rail matrix)
- PLAN-156 — Grok third harness + GPT-5.6 refresh + cross-vendor council
- SPEC/v1/hook-io.schema.md — Claude wire format
- SPEC/v1/normalized_envelope.schema.md — canonical envelope
- SPEC/v1/adapters.schema.md — adapter ABI
- docs/provider_capability_matrix.md — per-provider capability gaps
- docs/degradation-outside-claude-code.md — enforcement boundary by harness
