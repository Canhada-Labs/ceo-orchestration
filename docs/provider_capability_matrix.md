# Provider Capability Matrix

This page has **two** matrices, for two different layers that must not be
conflated:

1. **Governance capability by harness** — what each *host harness* actually
   ENFORCES, per rail, with the residual in the claim. This is the matrix
   an operator deciding "is my governance rail live under harness X" needs.
2. **LLM-invocation protocol capability** — the wire-level features of the
   *reviewer / batch* LLM clients under `.claude/hooks/_lib/adapters/live/`
   (`streaming_tool_use`, `json_mode`, …). This is the older PLAN-011
   matrix, drift-corrected.

---

## 1. Governance capability by harness (ENFORCED / ADVISORY / ABSENT)

**Source of truth:** PLAN-155 §Capability matrix + ADR-161 (normative). The
label for each `deny` is certified by a behavioral positive-control replay,
not by the existence of a config file. Vocabulary: **ENFORCED** = the
harness blocks the action at the stated time; **ADVISORY** = the hook fires
and injects/records but does not block; **ABSENT** = no primitive.
"Residual" is part of the claim, not a footnote.

Codex rows are **verified against codex-cli 0.139.0** (pin
`.claude/governance/codex-cli-pin.txt` = `>=0.128.0,<0.140.0`).

| Rail | Claude Code | Codex CLI (installed + trusted) | Residual + backstop (Codex) |
|---|---|---|---|
| Canonical-edit guard | ENFORCED (edit-time) | **ENFORCED** (edit-time) | Writes smuggled through complex shell (shell-escape class, as on Claude Code) and `apply_patch` **Update** hunks whose full new content the wire does not carry; path-level gates fire on every path in a multi-file patch. Backstops: the `^Bash$` rail sees the full command string; CODEOWNERS + branch protection at push. |
| Bash safety | ENFORCED | **ENFORCED** | Official caveat: Codex "doesn't intercept all shell calls yet, only the simple ones"; it splits `bash -lc` on plain words + `&&`/`\|\|`/`;`/`\|` only. Our hook receives the full string on every event that fires and applies our own parser (`_e3` whole-command gate fail-closed on input). `.codex/rules/ceo.rules` `prefix_rule(decision=forbidden)` is a COARSE prefix backstop, not coverage. |
| Plan lifecycle | ENFORCED (edit-time) | **ENFORCED** (edit-time) | Same shell-escape residual; Add-file ops content-gated via per-op reconstructed content, Update hunks path-gated only; CI plan-schema checks at push. |
| Arbitration kernel | ENFORCED (edit-time) | **ENFORCED** (edit-time) | Same residual class; kernel paths also in CODEOWNERS. Any kernel path in a multi-file patch trips the deny. |
| Kill-switch protection (`.codex/hooks.json`, `.codex/config.toml`, `.codex/rules/ceo.rules`, `requirements.toml`, operator `AGENTS.md`) | N/A (Claude uses `.claude/settings.json` guard) | **ENFORCED at edit-time; ADVISORY between sessions** | Registration surface is in the canonical deny matcher + SessionStart boot re-hash tripwire (Wave 3b). The boot-tripwire baseline is agent-writable (per-project state dir) — the edit-time canonical guard is the real protection; the boot re-hash is the backstop; CODEOWNERS/CI at push is the final backstop. |
| Audit HMAC chain | ENFORCED | **ENFORCED, completeness-bounded** | Per-edit completeness is best-effort while shell interception is partial — **absence of an entry is not evidence of absence of activity**. `verify_chain()` is unchanged and green over what was written. Per-tool (`codex_tool_recorded`) and turn-level (`codex_turn_ended`) appends are countable separately so completeness analysis can tell the rails apart. |
| Config protection | ENFORCED (edit-time) + continuous `ConfigChange` tripwire | **ENFORCED at edit-time; ADVISORY between sessions** | Codex has **no ConfigChange event** — the continuous tamper tripwire degrades to boot-time-only re-check (SessionStart). Backstop: boot-time hash re-check + CI. |
| Pair-rail review | ENFORCED (Claude operates, Codex reviews) | **PARTIAL, INVERTED** (Codex operates, `claude -p` reviews) | Stop-time + push-time, not per-edit mid-turn. Residual: killing the session or refusing twice abandons the Stop gate (the pre-push gate is the teeth); reviewer-model pin is PROVISIONAL (OQ3: `claude-opus-4-8`, per-review ceiling 100k tokens, overrides `CEO_PAIR_RAIL_REVIEWER_MODEL` / `CEO_PAIR_RAIL_REVIEWER_MAX_TOKENS`). |
| **Spawn governance** (honest ADVISORY) | ENFORCED (`check_agent_spawn.py` blocks) | **ADVISORY** — real gap: `continue:false` is parsed but does NOT stop the subagent (verified 0.139) | Mitigations, never enforcement: `additionalContext` injects the `## AGENT PROFILE` / `## SKILL CONTENT` / `## FILE ASSIGNMENT` requirement; spawns routed via Bash (`claude -p` / `codex exec`) re-gain the ENFORCED gate through the `^Bash$` matcher; Wave 6 pre-push/CI scan over the chain's spawn records. |
| **Config tripwire, continuous** (honest ADVISORY) | ENFORCED-ish (out-of-band `ConfigChange` observation) | **ADVISORY** — boot-time-only re-check, no continuous event | Backstop: the SessionStart settings-hash re-check breadcrumb is asserted present per session window (Wave 6 RED-on-absence); CI at push. A silent absence is defined RED, not green. |

**ABSENT on Codex today** (WATCH: `developers.openai.com/codex/hooks` +
the codex-cli release feed; substrate-watch owns the per-bump re-test):
total shell-call interception; a `ConfigChange` lifecycle event; a
`SubagentStart` that hard-blocks (`continue:false` is parsed-but-not-
enforced upstream).

**The CI-green ≠ current-Codex boundary (binding).** CI certifies
fixture-replay against a recorded wire; **only local live-fire certifies
the real binary, per pinned version.** CI replays FROZEN fixtures recorded
from codex-cli 0.139.0; it does not run the Codex binary. A CLI bump
without a fixture re-record is the drift class PLAN-142 already paid for
once — the substrate-watch item alerts on it, and fixtures follow the pin
via the ADR-111 ceremony, never upstream automatically.

**Trust and fail-open bound every ENFORCED Codex cell.** Nothing is
enforced until `/hooks` trust is granted (an untrusted hook is a silent
no-op); and codex-cli 0.139 fail-opens on hook timeout/crash/malformed
output. The installer arming check + Wave 6 RED-on-absence breadcrumbs are
the detection layer. Details: [adapters.md](adapters.md),
[degradation-outside-claude-code.md](degradation-outside-claude-code.md).

---

## 2. LLM-invocation protocol capability (reviewer / batch `live/` layer)

**Source:** PLAN-011 Phase 1, consensus §H2 / §H9.
**Layer:** `.claude/hooks/_lib/adapters/live/<name>.py` — the reviewer /
batch LLM clients, **not** the host hook-dispatch adapters. These are not
in `KNOWN_ADAPTERS` and are not selectable with `CEO_HOOK_ADAPTER`.
**Last refreshed:** 2026-06-15 (claude `max_context` 200k→1M per PLAN-137
A4 gate; see `docs/provider-pricing.md`). The `max_context` column is an
informational approximation — not a structured `CAPABILITIES` field.

> **Provenance rule.** `N/A` = the provider does not document or expose the
> capability. `advisory` = supported on paper but reliability varies by
> model/version. `Y` / `N` are hard guarantees.

| Adapter (`live/`) | `streaming_tool_use` | `json_mode` | `function_calling` | `system_prompt_slot` | `max_context` (tokens, approx) |
|---|---|---|---|---|---|
| **claude** | Y | Y | Y | Y | 1M (Opus 4.6+/Sonnet 4.6/Fable 5); 200k (Haiku 4.5) |
| **openai** | Y | Y | Y | Y | 128k (GPT-4o) / 200k (o1) |
| **gemini** | N | advisory | Y | Y | 1M (2.0 Pro) |
| **local** | N | N | Y | Y | varies by model (Llama 3.1: 128k) |

### Notes per column

- **`streaming_tool_use`** — provider streams partial tool-call deltas.
  Claude and OpenAI stream; Gemini and local runtimes typically do not.
- **`json_mode`** — strict JSON output guarantee. Claude and OpenAI
  guarantee; Gemini `advisory` (flag exists, older models ignore it);
  local `N` (JSON mode on Ollama / llama.cpp is model-dependent and not
  enforceable).
- **`function_calling`** — native structured tool-call API. All four
  support a function-calling surface; wire shapes differ.
- **`system_prompt_slot`** — provider accepts a dedicated system role.
- **`max_context`** — informational, not tested.

### Known gaps (per `live/` adapter)

- **claude** — reference client; no gaps.
- **openai** — assumes a gateway synthesizes the payload from OpenAI Chat
  Completions or Responses API traffic; there is no OpenAI-published hook
  protocol. Note: this is the **reviewer/batch** direction (invoking
  OpenAI as an LLM), distinct from the `codex` host hook-dispatch adapter
  in matrix 1 above (Codex CLI as the operating harness).
- **gemini** — real wire shape not captured; ships as a shape-probing
  stub, live-payload capture pending adopter feedback.
- **local** — assumes Ollama chat-API tool-call shape or a minimal
  `{tool, tool_input}` envelope; `json_mode: False`.

---

## Drift invariant

`test_adapter_drift_detector.py` parses:

1. The `NormalizedEvent` dataclass in `.claude/hooks/_lib/contract.py`.
2. The `§1.1 field inventory` table in
   `SPEC/v1/normalized_envelope.schema.md`.
3. Every `NormalizedEvent(...)` call site in the host-dispatch adapters
   (`claude.py`, `codex.py` host-mode).

Any field populated by any adapter that is not documented in SPEC §1.1
fails CI, and vice versa.

## Updating this page

When adding or extending a **host hook-dispatch** adapter: register it in
`contract.KNOWN_ADAPTERS` + `adapters.__init__.ADAPTER_REGISTRY` (a
KERNEL-class edit — sentinel + `CEO_KERNEL_OVERRIDE` + ACK), ship ≥2 real
recorded fixtures, extend the golden + drift + subprocess-control suites,
and add a governance-matrix row here + a section in
[adapters.md](adapters.md). When extending a **`live/` LLM-invocation**
adapter, add an honest `N/A` / `advisory` / `Y` / `N` row to matrix 2 (do
not guess) and keep its `CAPABILITIES` dict authoritative.

## References

- PLAN-155 — Codex harness capability matrix (governance rows above).
- ADR-161 — Codex harness capability matrix + host-adapter doctrine.
- `SPEC/v1/normalized_envelope.schema.md` — the canonical envelope.
- `SPEC/v1/adapters.schema.md` — ABI contract.
- `docs/adapters.md` — adapter layer + per-rail Codex matrix.
- `docs/degradation-outside-claude-code.md` — enforcement boundary by harness.
- ADR-008 / ADR-012 / ADR-028 — adapter foundation, golden fixtures, envelope parity.
- PLAN-011 consensus.md §H2 / §H9 / §H17 — the `live/` capability matrix source.
