# ceo-orchestration under Grok Build (xAI `grok` CLI)

> Verified against **grok 0.2.93** (`f00f96316d4b`). Grok Build ships
> **1–2 releases per DAY** on a proprietary 0.x channel: everything below
> is pinned to that exact version (`.claude/governance/grok-cli-pin.txt`
> + the binary SHA), and the substrate watch re-runs the characterization
> probes on every bump. Treat any claim here as stale the moment the pin
> moves.

## TL;DR — what is armed, and what is not

| Rail | Under Grok | Why |
|---|---|---|
| Canonical-edit deny (edit time) | **ENFORCED** | `PreToolUse` is grok's only blocking event; the guard denies `search_replace` before the write |
| Bash-safety deny | **ENFORCED** | same event; matcher covers the native `run_terminal_command` |
| Arbitration-kernel deny | **ENFORCED** | same event |
| Plan-lifecycle deny | **ENFORCED** | same event |
| Audit-chain append | **ENFORCED, completeness-bounded** | `PostToolUse` fires per tool call; absence of an entry is not evidence of absence of activity |
| Spawn-protocol governance | **ADVISORY** | `SubagentStart` is passive on grok — a deny cannot stop the subagent |
| Stop-review (inverted pair-rail) | **ADVISORY** | `Stop` is passive on grok — **the git pre-push gate is the teeth** |
| Config-tamper detection | **ADVISORY between sessions** | no ConfigChange event; boot-time re-hash only |

## The one thing that will bite you: hooks fail OPEN

Every hook failure on grok — a crash, a timeout, a malformed line of
stdout, an unrecognized decision word — lets the tool call **proceed**.
Only an explicit, well-formed `{"decision":"deny"}` blocks. Three
consequences that shaped this integration:

1. **`block` is not a word grok knows.** Our Claude-vocabulary hooks emit
   `{"decision":"block"}`; grok reads that as malformed output and
   fail-OPENs — **even when the hook also exits 2** (measured: the tool
   ran). The shim (`.claude/hooks/_python-hook.sh`) rewrites `block` →
   `deny` under `CEO_HOOK_ADAPTER=grok`, and `_lib/adapters/grok.py`
   never emits the word at all. Do not "helpfully" restore Claude
   compatibility in that egress path — you would silently disarm every
   ENFORCED row above.
2. **Timeouts are fail-open, and the default timeout is 5 s.** The
   registration below sets explicit per-hook timeouts. A cold Python
   start on a slow box that exceeds them is an ALLOW, not a deny.
3. **An untrusted project is a silent no-op.** Project hooks do not run
   until the folder is trusted (`/hooks-trust`, or launch with
   `--trust`). "Installed but untrusted" looks exactly like "healthy" at
   runtime. Run the arming check after install (`scripts/install.sh
   --harness grok` prints it).

## Registration: ONE surface, and it is `.claude/settings.json`

Grok reads Claude Code's `.claude/settings.json` as a legacy-compat hook
source, and it reads its own `.grok/hooks/*.json`. **Do not arm both.**

With both present, grok 0.2.93 fires every hook **twice** on the same
`toolUseId` (measured). Neither documented kill switch stops it:

- `[compat.claude] hooks = false` in a project `.grok/config.toml` — the
  project config is not read as a config source at all;
- `GROK_CLAUDE_HOOKS_ENABLED=0` — marks the hook `[disabled]` in
  `grok inspect` while the runtime **still fires it**.

A double-fired deny is idempotent (harmless), but a double-fired
audit-chain append is an HMAC double-count and a filelock race. So the
framework arms exactly one surface: **the `.claude/settings.json` it
already ships**. `.grok/hooks/**` is added to the canonical guard-list
precisely so nothing re-creates the second surface behind your back.

This means: **there is no `.grok/hooks/ceo.json` in this template on
purpose.** If a future grok release fixes the kill switches (watch item
in `substrate-watch.json`), the native surface becomes an option again —
re-run the double-fire probe before flipping.

## What this template ships

| File | Purpose |
|---|---|
| `config.toml.example` | user-level `~/.grok/config.toml` snippet — leader off for scripted lanes, model pin |
| `sandbox.toml.example` | the `council` custom profile: kernel-enforced read-only + a `deny` list for credential paths |
| `AGENTS.md` | the operator instructions file grok loads (it also loads your `CLAUDE.md` natively) |
| `pre-push-review-gate.sh` | **the teeth** — Stop is advisory on grok, so review enforcement lives at push time |

## Install

```sh
scripts/install.sh --harness grok
# then, in the repo:
grok            # first run prompts for folder trust, or:
grok --trust    # grants it non-interactively
```

Then verify the rails are actually armed (never assume — "untrusted" is
indistinguishable from "healthy"):

```sh
grok inspect | sed -n '/Hooks/,/Config Sources/p'   # hooks listed + no [disabled]
scripts/_grok_harness.sh --check                    # pin + binary SHA + arming
```

## Trust semantics

Folder trust is unified across MCP, LSP and hooks: `/hooks-trust` (or
`--trust`) trusts the whole folder for all three and cascades to
subdirectories. It is recorded in `~/.grok/trusted_folders.toml`. Global
hooks in `~/.grok/hooks/` are always trusted — which is also why the
framework never installs there.

## Honest limitations (carried from PLAN-156)

- Grok Build is **proprietary, 0.x, and ships daily**. The pin +
  substrate watch are load-bearing, not decorative.
- The installer is an unpinned rolling script. Fetch, hash, inspect, and
  only then execute — never `curl … | bash`. The binary-SHA pin is the
  real supply-chain gate; the installer itself is trust-on-first-fetch
  (no publisher signature verified).
- `Stop` / `UserPromptSubmit` / `SubagentStart` are non-blocking: session-end
  review and spawn governance are ADVISORY there. Push-time is the
  enforcement point.
- Fail-open-on-crash is not grok-specific (codex shares it), but grok's
  malformed-output-beats-exit-code rule is stricter than either other
  host — which is why the vocabulary normalization, not the exit code, is
  the enforcement mechanism here.
