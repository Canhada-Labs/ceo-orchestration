# {{PROJECT_NAME}} — ceo-orchestration operator contract (OpenAI Codex)

> **Template provenance:** `templates/codex/AGENTS.md` from the
> ceo-orchestration framework, installed by `install.sh --harness codex`
> (PLAN-155). Verified against **codex-cli 0.139.0** — re-verify at every
> CLI bump (the framework's substrate-watch owns the alert).
> This file is the OPERATOR contract for a target repository running the
> framework under Codex. It makes **no speed claim**: the framework's
> value is governance and auditability, not throughput.

## Read this first — two loud facts

1. **NOTHING is enforced until `/hooks` trust is granted.** On codex
   0.139 an untrusted or modified hook is a **silent no-op** — no
   execution, no warning, exit 0. "Installed but untrusted" is
   indistinguishable from healthy at runtime. After install or ANY change
   to `.codex/hooks.json`, re-grant trust and run the post-install arming
   check (`ARMED / NOT-ARMED-(untrusted) / BROKEN` — shipped with the
   installer, PLAN-155 Wave 5).
2. **Kill-switch surface protection is ABSENT until PLAN-155 Wave 3b
   lands.** The rail's own registration surface — `.codex/hooks.json`,
   `.codex/config.toml`, `.codex/rules/ceo.rules`, `requirements.toml`,
   and this `AGENTS.md` — is emitted by the installer but not yet covered
   by the edit-time deny matcher or the boot-time hash tripwire. Until
   Wave 3b is on main, an agent running under Codex could rewrite these
   files and disarm every rail below while the tripwire stays silent.
   Backstop until then: CODEOWNERS + branch protection at push time.

## What runs here

The same governance hooks that run under Claude Code, registered for
Codex in `.codex/hooks.json` and invoked with `CEO_HOOK_ADAPTER=codex`
through the framework's Python shim (`.claude/hooks/_python-hook.sh`).
One enforcement kernel, two harnesses — no hook forks.

## Capability matrix (binding vocabulary: ENFORCED / ADVISORY / ABSENT)

Every ENFORCED claim carries its residual in the same breath. This table
is the operator summary of the normative matrix in the framework's
PLAN-155 / ADR-161.

| Rail | Status under Codex | Residual + backstop |
|---|---|---|
| Canonical-edit guard | **ENFORCED** at edit time (PreToolUse `apply_patch\|Edit\|Write\|mcp__.*` → deny) | Residual: writes smuggled through complex shell commands (shell-escape class) and MCP arg shapes the guard cannot parse (fails closed on security matchers). Backstops: the `^Bash$` rail sees the full command string; CODEOWNERS + branch protection. |
| Bash safety | **ENFORCED** (PreToolUse `^Bash$`) + `.codex/rules/ceo.rules` coarse prefix backstop | Residual: codex "doesn't intercept all shell calls yet, only the simple ones". Our hook applies its own parser to the full string on every event that fires; unparseable input at the security matcher fails CLOSED. |
| Plan lifecycle | **ENFORCED** at edit time | Same shell-escape residual; CI plan-schema checks at push. |
| Arbitration kernel | **ENFORCED** at edit time (unconditional deny on kernel paths) | Same residual class; kernel paths also in CODEOWNERS. |
| Spawn governance | **ADVISORY** — codex 0.139 parses `continue:false` on SubagentStart but the subagent runs anyway | Mitigations: the SubagentStart hook injects the spawn-protocol requirement as `additionalContext` (verified working); spawns routed via Bash re-gain the ENFORCED `^Bash$` gate; pre-push/CI chain scan (PLAN-155 Wave 6). Never documented as enforced. |
| Pair-rail review (inverted: Codex operates, Claude reviews) | **PARTIAL** — Stop-hook `decision:block` is enforced by codex 0.139 (verified auto-continue); the review gate that uses it lands with PLAN-155 Wave 6 | Residual: nothing forces per-edit review mid-turn; a killed session abandons the Stop gate (git pre-push backstop still holds once Wave 6 lands). |
| Audit HMAC chain | **ENFORCED, completeness-bounded** (PostToolUse `*` append; per-tool-call action lands with PLAN-155 Wave 4) | Residual: absence of an entry is not evidence of absence of activity while shell interception is partial. `verify_chain()` unchanged and green over what was written. |
| Config protection | **ENFORCED at edit time; ADVISORY between sessions** | Codex has no ConfigChange event — continuous tamper observation degrades to the SessionStart boot-time re-check. Backstop: CI. |
| Kill-switch protection | **ABSENT until PLAN-155 Wave 3b lands** | See loud fact #2 above. |

## Trust model (what `/hooks` trust does and does not attest)

- Two gates must BOTH hold before a project hook fires:
  `projects."<absolute project path>".trust_level = "trusted"` in
  `$CODEX_HOME/config.toml`, **and** per-hook trust.
- The trust hash covers **only the registration entry** (event, matcher,
  command line, timeout, statusMessage) — **not the hook program's
  code**. Editing a hook `.py` body does not re-prompt trust; editing one
  byte of a registered command string flips the hook to `modified` and it
  silently stops firing. Registration integrity is codex's;
  hook-BODY integrity is the framework's (canonical-edit guard over
  `.claude/hooks/**` + the Wave 3b boot re-hash once landed).
- Headless trust (`[hooks.state]` entries) is scriptable. Any tool that
  writes trust entries for you MUST print them and get your confirmation
  first — trust is consent, not a config bit.

## Registration doctrine

- **Ship exactly one registration surface: `.codex/hooks.json`.** A
  `[hooks]` table in `.codex/config.toml` also works on 0.139, but dual
  registration warns and runs BOTH. The commented reference variant is
  `templates/codex/config.toml.hooks-example` in the framework repo.
- The `notify` turn-ended audit backstop is a `config.toml`-only surface
  (it is not a hook event) and activates with PLAN-155 Wave 4.
- `.codex/rules/ceo.rules` is a COARSE prefix backstop under the bash
  hook rail — it forbids the classic destructive spellings (`rm -rf`
  variants, `git reset --hard`, force-push, eval-string installers) and
  is never coverage. The hook owns the real parser.

## Spawn protocol (injected as ADVISORY context on SubagentStart)

Every named agent spawn must carry `## AGENT PROFILE`,
`## SKILL CONTENT`, and `## FILE ASSIGNMENT`. Under Codex this
requirement is INJECTED (additionalContext) but not enforced at spawn
time — see the matrix row. Route spawns through Bash
(`claude -p` / `codex exec`) to put them back under the ENFORCED gate.

## Placement doctrine (this file)

Codex discovers `AGENTS.md` from the git root down to the cwd,
**nearest wins**, capped by `project_doc_max_bytes` (32 KiB). This file
belongs at the target repository root. A deeper `AGENTS.md` in a
subdirectory SHADOWS this contract for sessions started there — do not
place nested `AGENTS.md` files unless you intend to replace the operator
contract for that subtree.

## Honest limitations (unchanged from the framework's doctrine)

- No speed claim: internal experiments found no general speedup over an
  optimized solo workflow. The value here is governance and audit.
- CI certifies fixture-replay against a recorded wire; only local
  live-fire certifies the real binary, per pinned version.
- Same-vendor caveat, direction-neutral: no single model is both author
  and sole reviewer — under this rail the operating model is OpenAI and
  the reviewer is Anthropic.
