# ADR-162 — Grok Build harness: capability matrix + exit-2 discipline

- **Status:** ACCEPTED (PLAN-156, 2026-07-12)
- **Deciders:** CEO (dogfood), pair-rail (Codex R1–R14), debate L3 (3×ADJUST)
- **Supersedes / relates:** extends ADR-161 (Codex harness capability matrix);
  the two are sibling per-harness normative records under the shared
  SPEC/v1 adapter ABI. Neither supersedes the other.

## Context

PLAN-155 built the adapter seam (`_lib/adapters/resolve()` +
`KNOWN_ADAPTERS`) so a third host harness is a bounded increment. PLAN-156
adds xAI **Grok Build** (binary `grok`, proprietary, 0.x, 1–2 releases/day)
as that third harness, alongside Claude Code and OpenAI Codex. This ADR is
the normative capability record for the grok host — what each governance
rail actually ENFORCES under grok, with the residual in the claim — and it
codifies the one grok-specific enforcement discipline that has no analogue
on the other two hosts: the **decision→exit-2 + vocabulary discipline**.

All claims are certified by behavioral positive-control replay against the
pinned binary (grok 0.2.93, `.claude/governance/grok-cli-pin.txt`), not by
the existence of a config file. Empirical base:
`PLAN-156/artifacts/characterization-grok-codex-S269.md`.

## Decision

### 1. Capability matrix (grok host)

Vocabulary as in ADR-161: **ENFORCED** = grok blocks the action at the
stated time; **ADVISORY** = the hook fires and records/injects but cannot
block; **ABSENT** = no primitive. The residual is part of the claim.

| Rail | Grok Build | Residual + backstop |
|---|---|---|
| Canonical-edit guard | **ENFORCED** (edit-time, `pre_tool_use` on `search_replace`) | Shell-escape class (as on Claude/Codex). The grok wire carries Claude-shaped `file_path`/`old_string`/`new_string`, so the guard sees a familiar shape once the tool name is aliased. |
| Bash safety | **ENFORCED** (edit-time, native `run_terminal_command`) | The matcher MUST cover the native name — a Claude-only matcher relies on grok's aliasing. Positive control drives the NATIVE name. |
| Plan lifecycle | **ENFORCED** (edit-time) | Same shell-escape residual. |
| Arbitration kernel | **ENFORCED** (edit-time) | Same residual class; kernel paths also in CODEOWNERS. |
| Kill-switch protection (`.grok/hooks/**`, `.grok/config.toml`, `.grok/sandbox.toml`, `.grok/rules/*.md`) | **ENFORCED at edit-time** | Registration surface is in the canonical deny matcher + SessionStart boot re-hash tripwire. `.grok/hooks/**` is guarded even though the framework ships NO live hooks there (see §3). |
| Audit HMAC chain | **ENFORCED, completeness-bounded** | Grok's hook coverage is per-event and PostToolUse is passive there — absence of a row is not evidence of absence of activity. Per-tool (`grok_tool_recorded`) + turn-level (`grok_turn_ended`) appends countable separately. SessionEnd is unreliable headless, so turn accounting hangs off `Stop`. |
| Config protection | **ADVISORY between sessions** | No ConfigChange event; boot-time re-hash only (same as Codex). |
| Pair-rail review | **ADVISORY (Stop), ENFORCED (pre-push)** | `Stop` is NON-blocking on grok, so the Stop-review gate is advisory by construction; the **git pre-push gate is the teeth** (`templates/grok/pre-push-review-gate.sh`). Reviewer = `claude -p` (author=xAI, reviewer=Anthropic). |
| Spawn governance | **ADVISORY** | `SubagentStart` is passive on grok (`Task`→`spawn_subagent` alias exists for the matcher, but a deny cannot stop the subagent). Mitigation: `additionalContext` + the Bash-routed re-gate + the chain-scan backstop. |

**ABSENT on grok today** (WATCH: `docs.x.ai/build` + the grok release
feed; the substrate-watch owns the per-bump re-test): a blocking `Stop` /
`UserPromptSubmit` / `SubagentStart`; a ConfigChange lifecycle event; a
runtime-honored `[compat.claude] hooks=false` / `GROK_CLAUDE_HOOKS_ENABLED=0`
kill switch (both are inspect-only on 0.2.93 — see §3).

### 2. Exit-2 + vocabulary discipline (grok-scoped)

Grok's PreToolUse deny contract differs from both other hosts in a way that
makes a shared discipline mandatory:

- **`block` is not a word grok knows.** An unrecognized decision value is
  *malformed hook output* → hook failure → **fail-OPEN — and exit 2 does
  NOT rescue it** (probe P5: `{"decision":"block"}`+exit-2 ⇒ the tool ran).
  So the shim (`_python-hook.sh`) **rewrites `block`→`deny`** on stdout
  under `CEO_HOOK_ADAPTER=grok`, and `_lib/adapters/grok.py:write_decision`
  never emits `block`. This rewrite is the ENFORCEMENT mechanism on grok
  and is NOT disableable.
- **A clean stdout deny blocks on its own** (probe P2). The shim also maps
  an emitted deny to **exit 2** (belt-and-suspenders; `CEO_HOOK_EXIT_MAP=0`
  disables just this half). A crash with NO decision keeps the hook's own
  fail-open exit code — the INFRASTRUCTURE half of CLAUDE.md §4 preserved.

**Scoped to grok, not unconditional.** PLAN-156 Wave 2's conditional was:
"unconditional mapping SAFE iff lacuna (h) confirms exit 2 is INERT on
Codex; if not, adapter-aware." Lacuna (h) found exit 2 is an ACTIVE deny on
Codex PreToolUse (probe P9a) — NOT inert. So both halves fire only under
grok; Claude/Codex hooks stay byte-identical to the SPEC "exit 0 regardless
of decision" contract. Remapping them would change an observable with zero
enforcement gain. The hermetic CI meta-test
(`hooks/tests/test_exit2_chokepoint.py`) is RED-on-absence for both halves
and for the "every registration routes through the shim" invariant.

### 3. Single-surface registration (OQ1, inverted by evidence)

The framework arms exactly ONE hook surface under grok: the legacy-compat
`.claude/settings.json` it already ships. It does **not** ship
`.grok/hooks/`. Rationale (probe P8): with both surfaces present grok 0.2.93
fires every hook TWICE on the same tool call (HMAC double-count + filelock
race), and neither documented kill switch stops it at runtime
(`[compat.claude] hooks=false` in the project config is unread;
`GROK_CLAUDE_HOOKS_ENABLED=0` marks the hook `[disabled]` in `grok inspect`
while the runtime still fires it). `.grok/hooks/**` is canonical-guarded so
nothing re-creates the second surface. If a future release honors the kill
switch, the native surface becomes available again (substrate-watch item).

## Consequences

- A third proprietary daily-0.x harness adds a standing weekly
  substrate-watch + re-fixture obligation no CI can automate (no binary /
  secret on a runner). The Owner ratifies this RECURRING commitment at
  Wave-0 signing (CLAUDE.md §5 bus-factor).
- The decision→exit chokepoint is shared, so it also hardens the Codex
  fail-open residual (an emitted deny is now unambiguous on any host that
  keys on the exit code) — even though the exit-2 mapping itself is
  grok-gated.
- The cross-vendor council (Wave 6, `council_lane_invoked`) turns the
  third-vendor access into an audit instrument with vendor-attributed
  verdicts; its egress is redacted (ADR-114) but not eliminated — an
  operator-ratified privacy decision, never a CI job.

## Honest limitations

- Grok Build is proprietary, 0.x, daily-release: the pin + substrate watch
  are load-bearing, not decorative.
- `Stop` / `UserPromptSubmit` / `SubagentStart` are non-blocking: session-end
  review and spawn governance are ADVISORY; push-time is enforcement.
- The installer is an unpinned rolling script (fetch-hash-inspect-then
  -execute; the binary-SHA pin is the real supply-chain gate; the installer
  itself is trust-on-first-fetch).
- No speed claim.
