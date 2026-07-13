# {{PROJECT_NAME}} — ceo-orchestration operator contract (xAI Grok Build)

> **Template provenance:** `templates/grok/AGENTS.md` from the
> ceo-orchestration framework, installed by `install.sh --harness grok`
> (PLAN-156). Verified against **grok 0.2.93** — re-verify at every CLI
> bump (Grok Build ships 1–2 releases per DAY; the framework's
> substrate-watch owns the staleness alert). This file is the OPERATOR
> contract for a target repository running the framework under Grok. It
> makes **no speed claim**: the value is governance and auditability, not
> throughput.
>
> Grok loads this file natively (it reads `AGENTS.md` and your
> `CLAUDE.md` per directory), so its content is in-context every session.

## Read this first — three loud facts

1. **NOTHING is enforced until the project folder is TRUSTED.** Project
   hooks are silently skipped until you run `/hooks-trust` (or launch
   with `--trust`). "Installed but untrusted" is indistinguishable from
   healthy at runtime. Trust is unified (MCP + LSP + hooks) and recorded
   in `~/.grok/trusted_folders.toml`. Verify with `grok inspect`.
2. **Hooks FAIL OPEN.** A crash, a timeout (default 5 s!), malformed
   stdout, or an unrecognized decision word all let the tool call
   **proceed**. Only a well-formed `{"decision":"deny"}` blocks. The
   framework's registration sets explicit timeouts and the shim
   guarantees the deny vocabulary — do not route hooks around it.
3. **`PreToolUse` is the ONLY blocking event.** Everything else —
   `Stop`, `UserPromptSubmit`, `SubagentStart`, `PostToolUse` — is
   passive on grok. Enforcement that needs those events (session-end
   review, spawn governance) is ADVISORY here; the **git pre-push gate is
   the teeth**.

## What runs here

The same governance hooks that run under Claude Code, registered through
the **legacy-compat `.claude/settings.json`** surface (grok reads it as a
Claude Code compatibility source) and invoked with `CEO_HOOK_ADAPTER=grok`
through the framework's Python shim (`.claude/hooks/_python-hook.sh`).
One enforcement kernel, three harnesses — no hook forks.

**There is deliberately no `.grok/hooks/ceo.json`.** Arming both the
native `.grok/hooks/` surface and the legacy `.claude/settings.json`
makes grok 0.2.93 fire every hook TWICE on the same tool call (measured),
and neither documented kill switch stops it at runtime. The framework
arms exactly one surface. `.grok/hooks/**` is on the canonical
guard-list so nothing re-creates the second one.

## Capability matrix (binding vocabulary: ENFORCED / ADVISORY / ABSENT)

Every ENFORCED claim carries its residual in the same breath (the
normative matrix lives in the framework's PLAN-156 / ADR-162).

| Rail | Grok | Residual |
|---|---|---|
| Canonical-edit deny | **ENFORCED** (PreToolUse, `search_replace`) | shell-escape class; the wire carries Claude-shaped edit keys so the guard sees a familiar shape |
| Bash-safety deny | **ENFORCED** (PreToolUse, native `run_terminal_command`) | matcher must cover the native name — a Claude-only matcher relies on grok's aliasing |
| Arbitration-kernel deny | **ENFORCED** | shell-escape class |
| Plan-lifecycle deny | **ENFORCED** | apply-shape class |
| Audit-chain append | **ENFORCED, completeness-bounded** | absence of an entry ≠ absence of activity; grok's per-event coverage means SessionEnd may not fire — accounting hangs off `Stop` |
| Spawn-protocol governance | **ADVISORY** | `SubagentStart` is passive; the chain-scan backstop is the teeth |
| Stop-review (inverted pair-rail) | **ADVISORY** | `Stop` is passive; **the git pre-push gate blocks** |
| Config-tamper detection | **ADVISORY between sessions** | no ConfigChange event; boot-time re-hash only |

## The vocabulary rule you must not break

Grok does not understand `{"decision":"block"}` — it reads that as
malformed output and **fail-OPENs, even if the hook also exits 2**
(measured). The shim rewrites `block` → `deny` under
`CEO_HOOK_ADAPTER=grok`, and `_lib/adapters/grok.py` never emits `block`.
If you write a new hook, emit your decision through the adapter seam
(`_lib.adapters.resolve()`), never a hardcoded `{"decision":"block"}`.

## Operator escape hatches

- `CEO_HOOK_EXIT_MAP=0` — disable the decision→exit-2 mapping in the shim
  (only if a future grok release turns exit-2-hostile; the arming check
  surfaces it).
- `CEO_GROK_PUSH_GATE=0` / `CEO_GROK_PUSH_GATE_ADVISORY=1` — disable /
  soften the pre-push review gate.
- `grok --sandbox council` — the read-only audit profile (see
  `.grok/sandbox.toml`); required for the cross-vendor council's grok lane.

## Honest limitations

- Grok Build is proprietary, 0.x, daily-release. The pin + substrate
  watch are load-bearing.
- The installer is an unpinned rolling script: fetch-hash-inspect-THEN
  -execute (never `curl … | bash`); the binary-SHA pin is the real
  supply-chain gate, and the installer itself is trust-on-first-fetch.
- A lapsed SuperGrok / X Premium+ subscription makes `grok login` fail;
  every grok rail then degrades to unavailable (the framework treats that
  as `unavailable`, never a red build).
