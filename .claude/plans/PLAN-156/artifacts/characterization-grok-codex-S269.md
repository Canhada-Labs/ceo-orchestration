# PLAN-156 W0a — Empirical characterization: grok 0.2.93 + codex-cli 0.144.1 (S269, 2026-07-12)

> Produced by live probes on the Owner's authed machine (T2 tier). Every
> claim below is backed by a probe with a verifiable side effect (target
> file created / not created). Wire fixtures:
> `grok-wire-fixtures-0.2.93.ndjson` + `codex-wire-fixtures-0.144.1.ndjson`
> (same directory). Lab: scratchpad `grok-lab` (git repo, trusted via
> `--trust`, hooks the only barrier under `--yolo`).

## Binaries probed

| CLI | Version | Source |
|---|---|---|
| grok (Grok Build) | **0.2.93** (f00f96316d4b) | `~/.grok/bin/grok`, session login (no XAI_API_KEY) |
| codex-cli | **0.144.1** | `/opt/homebrew/bin/codex`, ChatGPT account |

Account models exposed by `grok models`: `grok-4.5` (default) +
`grok-composer-2.5-fast`. **No `grok-build-0.1`** → OQ3 grok lane =
`grok-4.5` (empirically forced, not a preference).

## Grok decision-semantics matrix (PreToolUse, the only blocking event)

| Probe | stdout | exit | Tool ran? | Verdict |
|---|---|---|---|---|
| P2 | `{"decision":"deny"}` | 0 | **NO** | deny honored from stdout JSON alone |
| P3 | `{"decision":"deny"}` | 2 | **NO** | deny (baseline) |
| P4 | `{"decision":"block"}` | 0 | **YES** | fail-open — `block` is not a recognized decision |
| P5 | `{"decision":"block"}` | **2** | **YES** | **fail-open — malformed stdout JSON ANNULS even exit 2** |
| P6 | (crash, stderr) | 1 | YES | fail-open (infra) — matches CLAUDE.md §4 infra half |
| P7 | (no JSON, stderr) | 2 | **NO** | bare exit-2 with clean stdout = deny |

**P5 is the load-bearing discovery.** The docs.x.ai claim recorded in the
S266 research ("deny REQUIRES exit 2") is wrong on 0.2.93 in BOTH
directions: stdout-deny alone blocks (P2), and exit-2 does NOT rescue a
hook whose stdout carries an unrecognized decision value (P5 — grok
treats it as "malformed output" = hook failure = fail-open, and the
failure disposition beats the exit code). Consequences for Wave 2:

1. The chokepoint MUST normalize the *stdout* (`block` → `deny`, emitting
   a clean `{"decision":"deny","reason":…}`), not merely map the exit
   code. An exit-2-only chokepoint would leave every `block`-emitting
   hook (e.g. `check_codex_filewrite.py` today) fail-open under grok —
   confirmed live by P4/P5.
2. Exit-2 mapping stays as belt-and-suspenders (P7 works; docs.x.ai
   semantics may return in a future 0.x release; SPEC amendment
   unchanged in intent).
3. Fail-open-on-crash (P6) is native grok behavior — the infra half of
   the CLAUDE.md §4 doctrine is preserved without any work on our side.

## Research-lacunae resolutions (a)–(h)

- **(a) toolName vocabulary — NATIVE, and the S266 name was wrong.**
  stdin `toolName` = `run_terminal_command` (NOT `run_terminal_cmd` as
  docs.x.ai/research said; the bundled headless doc still says
  `run_terminal_cmd` for `--tools` — the product is internally
  inconsistent, our fixtures pin the hooks truth). Matcher aliasing:
  `^Bash$` fires (Claude-name aliased) AND `^run_terminal_command$`
  fires; `^run_terminal_cmd$` does NOT fire. Alias table (bundled doc,
  0.2.93): `Bash`→`run_terminal_command`, `Read`→`read_file`,
  `Edit`/`Write`/`MultiEdit`→`search_replace`, `Grep`→`grep`,
  `Glob`/`ListDir`→`list_dir`, `WebSearch`→`web_search`,
  `Task`→`spawn_subagent`.
- **(b) `block` vs `deny` — `deny` ONLY.** `block` is unrecognized and
  fail-opens even with exit 2 (P4/P5). Adapter `write_decision()` must
  emit `deny`; the shim chokepoint must rewrite legacy `block` stdout.
- **(c) spawn tool name** — `Task`→`spawn_subagent` alias exists in the
  matcher layer; SubagentStart/Stop events exist (non-blocking). A
  spawn-governance matcher must cover `spawn_subagent|Task`.
- **(d) instructions file — YES, native + Claude-compat.** Grok loads
  `AGENTS.md`/`Agents.md`/`AGENT.md`/`CLAUDE.md`/`CLAUDE.local.md` per
  directory (confirmed live: lab `AGENTS.md` listed by `grok inspect`
  under Project Instructions), plus `.grok/rules/*.md` and
  `.claude/rules/` compat. Our repo's CLAUDE.md is picked up as-is.
- **(e) OS read-only containment — YES, first-class.** `--sandbox
  read-only` built-in profile (Seatbelt on macOS, Landlock on Linux,
  kernel-enforced, applied to the whole process incl. children). An
  explicitly requested custom/unknown profile **fails closed** ("refusing
  to start rather than run unsandboxed" — observed live). Residual: on
  macOS child-process *network* blocking is a no-op (write containment is
  what the council needs; egress is the redactor's job). Council grok
  lane is therefore VIABLE with `--sandbox read-only`.
- **(f) `--cwd` / `--permission-mode` — BOTH native** (in `--help`;
  `--permission-mode` parsed in both modes but headless honors only
  `bypassPermissions` per bundled doc §14). Not compat-layer artifacts.
- **(g) double-fire — CONFIRMED, and the kill switches are broken.**
  With native `.grok/hooks/` + legacy `.claude/settings.json` both
  present, the SAME `toolUseId` fires both surfaces (P8: legacy=1,
  native=1; legacy hook receives the GROK envelope — camelCase keys,
  native toolName — not a Claude-shaped one). `[compat.claude]
  hooks=false` in the PROJECT `.grok/config.toml` has NO effect (project
  config is not even listed as a Config Source). `GROK_CLAUDE_HOOKS_ENABLED=0`
  marks the hook `[disabled]` in `grok inspect` but the headless RUNTIME
  FIRES IT ANYWAY (P8c/P8d — disable is inspect-only; product bug class,
  0.x). **Resolution: single-surface by construction — do NOT ship
  `.grok/hooks/`; the grok surface is the legacy-compat
  `.claude/settings.json` the repo already carries.** Proven single-fire:
  P8e (legacy-only, count==1 total). This INVERTS the OQ1 draft
  recommendation (native) for 0.2.93 — Owner ratifies at signing.
- **(h) exit-2 on codex 0.144.1 — NOT inert, and safe in our direction.**
  PreToolUse hook exiting 2 (stderr, no JSON) = DENY (P9a: tool blocked,
  model replied BLOCKED). PostToolUse (passive) exiting 2 = harmless
  (P9c: tool ran, session completed; hook failure logged only). So the
  shim's decision-derived mapping (emitted-deny→2, allow→0,
  no-decision-crash→0) is UNCONDITIONAL-safe across Claude (exit-2 deny
  alias), Codex (exit-2 deny on Pre, ignored on passive), Grok (exit-2
  deny; stdout-deny also honored).

## Codex 0.144.1 wire + trust findings (Wave 1 inputs)

- **stdin `tool_name` = `Bash`** (Claude vocabulary!) with snake_case
  envelope keys: `cwd, hook_event_name, model, permission_mode,
  session_id, tool_input, tool_name, tool_use_id, transcript_path,
  turn_id`. Re-record of golden fixtures with `_meta.codex_cli_version:
  0.144.1` required (Wave 1) — envelope gained `model` + `turn_id`
  fields vs the 0.139 fixtures (drift-detector will flag; expected).
- **PLAN-155 A6 headless trust mechanics WORK UNCHANGED on 0.144.1**:
  `[projects."<path>"] trust_level = "trusted"` + `[hooks.state."<key>"]
  trusted_hash = "sha256:<currentHash>"` via `codex app-server` JSON-RPC
  (`initialize` → `hooks/list {"cwds":[…]}`). Untrusted/modified hooks
  remain SILENT NO-OPs. Trust is still keyed to the registration command
  line (editing the script body does not de-trust).
- `codex exec` reads additional input from stdin — close stdin
  (`</dev/null`) in every scripted invocation or it hangs (this is the
  S266 empty-stdout class seen from another angle).
- `--sandbox workspace-write` accepted on 0.144.1 (flag exists; the
  0.143 rename audit in Wave 1 must still grep all call sites).
- `-m gpt-5.6-luna` + `-c model_reasoning_effort=low` work headlessly
  (bug #31869/#31873 class not reproduced on macOS 0.144.1).

## Grok operational facts pinned for Waves 2-5

- Hook config JSON schema is Claude-shaped; `timeout` default **5s**
  (our shim + python cold start must fit or the hook TIMES OUT = fail-open
  → template sets explicit per-hook timeouts like the codex template).
- Envelope: camelCase keys, `hookEventName` VALUES are snake_case
  (`pre_tool_use`), always includes `toolUseId` + `toolInputTruncated`;
  `permissionMode` present on PreToolUse; `transcriptPath` present from
  UserPromptSubmit onward; PostToolUse carries `toolResult` +
  `toolResultTruncated` + `isBackgrounded`.
- Runner env: `GROK_HOOK_EVENT`, `GROK_HOOK_NAME`, `GROK_SESSION_ID`,
  `GROK_WORKSPACE_ROOT` and **`CLAUDE_PROJECT_DIR` (grok-injected alias,
  reserved)** — our hooks' `CLAUDE_PROJECT_DIR` dependency is satisfied
  natively; env-injection cannot override reserved keys.
- `SessionEnd`/`Notification`/`Subagent*` did not fire in a plain
  headless `-p` run; Stop fired with `reason`. Session-end accounting on
  grok should hang off `Stop`, not `SessionEnd` (completeness caveat).
- Headless: `-p` + `--output-format json` → single object with
  `text/stopReason/sessionId/requestId(/thought)`. `--max-turns`,
  `--tools`, `--disallowed-tools` (incl. `Agent` entries) headless-only.
- Trust: `--trust` at launch persists folder trust (MCP+LSP+hooks
  unified) in `~/.grok/trusted_folders.toml`; `~/.grok/hooks/` always
  trusted; project `.grok/` requires the grant.
- Leader mode exists (`[cli] use_leader`, `--no-leader`, `grok leader
  kill`) — scripted probes/lanes should pass `--no-leader` to avoid
  stale shared-backend state.
- `grok inspect` enumerates the resolved surfaces (hooks with source
  tags `[claude]`/`[disabled]`, compat cells, permissions source) —
  the arming check's observable.
- Permissions compat: grok loads `--allow/--deny` rules AND reads
  `~/.claude/settings.json` permissions (observed: "8 loaded"). Rule
  grammar `ToolPrefix(glob)` incl. Claude `Bash(cmd:*)` accepted.

## Design deltas vs the plan text (for the Owner's morning ratification)

1. **OQ1 INVERTED by evidence**: ship legacy-compat single-surface (no
   `.grok/hooks/` template with live hooks); `.grok/` template ships
   `config.toml` (leader off for lanes) + `sandbox.toml` (council
   profile) + docs. Rationale: (g) — double-fire is unavoidable with
   both surfaces and both kill switches are inert on 0.2.93.
2. **Chokepoint spec hardened**: decision-derived exit AND stdout
   normalization (`block`→`deny`, clean JSON re-emit). Unconditional
   across adapters (safe per (h)); scoped emit: deny-exit-2 only for
   blocking events (pre_tool_use), passive events keep exit 0.
3. **W7 positive control**: native-named call = `run_terminal_command`
   (NOT `run_terminal_cmd`).
4. Grok pin: **0.2.93** exact (installed binary), not 0.2.94 (drafting
   doc value) — pin what we characterized.
