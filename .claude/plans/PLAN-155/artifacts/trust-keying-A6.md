# PLAN-155 Wave 1 — /hooks trust keying, empirically pinned (debate A6; OQ1 gate)

**Substrate:** codex-cli 0.139.0, all probes headless (`codex exec` +
`codex app-server` JSON-RPC `hooks/list`). Source-of-truth cross-check:
`codex-rs/hooks/src/engine/discovery.rs` and
`codex-rs/config/src/hook_config.rs` at tag `rust-v0.139.0`
(github.com/openai/codex) — read AFTER the behavior was observed live, to
name the mechanism; every claim below was reproduced live first.

## What the trust hash attests — the OQ1 answer

**The hash covers ONLY the registration entry, NOT the hook program.**
Mechanism (verified in source, `discovery.rs::command_hook_hash`): the
`sha256:<…>` `currentHash` is computed over a normalized TOML serialization
of `{event_name, matcher, hooks:[{type, command, timeout, statusMessage}]}` —
i.e. the JSON/TOML registration group. The hook COMMAND STRING is inside the
hash; the FILE the command executes is not.

Live proof:

- **Editing the registered script's contents after trust → still fires,
  no re-prompt, no status change** (probe `e5a-scriptedit-readonly`): with
  the hook trusted, `responder.py` was edited (new code path writing an
  extra probe file); the next session fired the hook and the new code ran.
  `hooks/list` still reported `trustStatus: "trusted"`.
- **Editing the registration (one byte of the command string) → status
  `modified`, hook silently does NOT fire** (probe `e5b-regedit-notrust`):
  changed one argv token in `hooks.json`; session ran, zero hook
  executions, no warning anywhere in `codex exec --json` output;
  `hooks/list` reported `trustStatus: "modified"`.

**Consequence for OQ1/ADR-161 (normative paragraph material):** `/hooks`
trust is consent to a COMMAND LINE, not to code. For our shim architecture
(`_python-hook.sh <hook>.py`), a framework upgrade that changes only hook
`.py` bodies does NOT re-prompt (low friction, near-zero re-key cost — the
S261 "every upgrade re-prompts" friction estimate was WRONG for body-only
upgrades); equally, an attacker who can write the hook `.py` files inherits
trusted execution without any re-prompt (the consent-security meaning
inverts exactly as debate A6 anticipated). Registration-file integrity
(`.codex/hooks.json`) is hash-keyed by codex itself; hook-BODY integrity is
OURS to defend — which is precisely the Wave 3b kill-switch/boot-re-hash
surface plus the existing canonical-edit guard over `.claude/hooks/**`.

## Untrusted / modified behavior

- An untrusted or modified hook is a **silent no-op**: no execution, no
  stderr, no `--json` event, exit 0 (probes `t1-untrusted`,
  `e5b-regedit-notrust`). "Installed but untrusted" is indistinguishable
  from healthy at runtime — this is the strongest argument for the Wave 5
  post-install arming check (debate A7) and the Wave 6 RED-on-absence
  assertions.

## Headless trust surfaces (what the installer can do without the TUI)

1. **`[hooks.state]` in `$CODEX_HOME/config.toml` — WORKS headlessly.**
   Trust is persisted as:

   ```toml
   [hooks.state."<sourcePath>:<snake_event>:<groupIdx>:<handlerIdx>"]
   trusted_hash = "sha256:<currentHash>"
   ```

   Keys + current hashes are enumerable headlessly via `codex app-server`
   JSON-RPC: `initialize` → `hooks/list` `{"cwds": ["<repo>"]}` → entries
   carry `key`, `currentHash`, `trustStatus`, `enabled`, `isManaged`,
   `source` (`user`/`project`), `sourcePath`. Writing the state entries and
   re-running makes `trustStatus: "trusted"` and hooks fire (probes
   `t9-trusted` onward all ran on this surface). NOTE: this makes
   "user-consented trust" scriptable — the installer MUST print what it is
   about to trust and get explicit operator confirmation (consent-first,
   OQ1), because codex itself will not re-ask.
2. **`--dangerously-bypass-hook-trust` (codex exec flag) — did NOT arm
   untrusted hooks in our probes.** The flag is acknowledged (a
   `--json` error-item warns "Enabled hooks may run without review for
   this invocation") but untrusted/modified hooks still did not run
   (probes `t2/t3/t7`, re-confirmed post-diagnosis in `e5c-bypass` with a
   modified-status hook and in-workspace writes). Do not build on this
   flag for 0.139; re-test at every pin bump (substrate-watch item).
3. **`requirements.toml` managed hooks — NOT live-tested** (needs an
   admin-scope requirements file; `hooks/list` schema + source show
   `isManaged: true` ⇒ `trustStatus: "managed"`, trusted-by-policy,
   `enabled` not user-toggleable). Left for the Owner's interactive
   morning check / Wave 2 if the managed posture is pursued.

## What remains for the Owner (interactive)

- The `/hooks` TUI flow itself (what the review screen shows, wording of
  the trust prompt) — cosmetic for us, since both the trust store it
  writes and the hash it keys on are now pinned headlessly.
- Managed (`requirements.toml`) posture live-fire, if OQ1 lands on
  offering `--managed-hooks`.

## Other trust-adjacent facts pinned in the same lab

- **Project-layer hooks require the project directory to be trusted**
  (`projects."<path>".trust_level = "trusted"` in the user config) before
  the `.codex/` layer is even loaded; hook trust is a SECOND, separate
  gate on top.
- Both `<repo>/.codex/hooks.json` and `[hooks]` tables in
  `<repo>/.codex/config.toml` register hooks; registering the same event
  in both yields a discovery warning ("prefer a single representation for
  this layer") and BOTH run. `$CODEX_HOME/hooks.json` (user scope) also
  works. Ship exactly ONE representation: `hooks.json`.
- Hook processes are NOT confined by the session sandbox: under
  `--sandbox read-only` a trusted hook wrote files inside and outside the
  workspace (probe `e5a`). Good for audit-chain writes; also means hook
  compromise = arbitrary user-privilege execution — consent-first trust
  flow is not optional.
- Hook subprocess env carries `CODEX_HOME`, `CODEX_MANAGED_BY_NPM`,
  `CODEX_MANAGED_PACKAGE_ROOT` only (plus inherited env) — no
  event-specific env vars; everything rides stdin JSON.
