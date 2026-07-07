# Substrate adoption record — Anthropic sweep 2026-07

> **Status: STAGED, not live.** The two ADOPTED items below are written to
> `.claude/plans/PLAN-153/staged/wave-backlog/.claude/settings.json` and provide
> **zero protection until the Owner ceremony lands them** into the canonical
> `.claude/settings.json`. The `sandbox.credentials` item additionally stays inert
> until `sandbox.enabled` is flipped `true` (a separate, deliberate Owner step —
> see the `_sandbox_comment` flip discipline). This document never claims a
> protection that only ships at landing.

Substrate: Claude Code **2.1.202** (verified locally; schema claims below were
extracted from the 2.1.202 binary's settings zod schema, not from memory or docs).

## Sweep findings and dispositions

| # | Finding (sweep, 2026-07) | Disposition | Detail |
|---|--------------------------|-------------|--------|
| 1 | Claude Code at 2.1.202 | context | Local install confirmed `2.1.202` (`~/.local/share/claude/versions/2.1.202`). All schema verification below ran against this binary. |
| 2 | New setting `sandbox.credentials` (>= 2.1.187): blocks sandboxed commands from reading credential files + secret env | **ADOPTED-STAGED** | Added to staged settings inside `sandbox` (staged file lines 47–126). Schema verified from the binary: `files[]` = `{path, mode:"deny"}` (deny is the only file mode; paths resolve like `sandbox.filesystem.*` — absolute, `~`-expanded, or relative to project root; **no glob support**); `envVars[]` = `{name, mode:"deny"\|"mask"}` (`deny` unsets the var for sandboxed commands; `mask` substitutes a sentinel in-sandbox and injects the real value at the egress proxy); `allowPlaintextInject` optional bool, default `false`. Values chosen: 13 file denies (credential-store class mirroring the Wave-E deny baseline: `~/.ssh`, `~/.aws`, `~/.npmrc`, `~/.config/gcloud`, `~/.kube`, `~/.docker/config.json`, `~/.git-credentials`, `~/.netrc`, `~/.pypirc`, plus `~/.gnupg`, `~/.claude/.credentials.json`, and root-level `.env` / `.env.local`); 5 env denies (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_SESSION_TOKEN`, `NPM_TOKEN`, `NODE_AUTH_TOKEN`); `allowPlaintextInject: false` explicit. |
| 3 | New setting `enforceAvailableModels`: `availableModels` allowlist also constrains the Default model | **ADOPTED-STAGED** | `availableModels` was already present with 4 pins, so the precondition holds. Added `"enforceAvailableModels": true` adjacent to it (staged file line 722). Binary-verified semantics: when true and `availableModels` is non-empty, a tier default outside the list resolves to the first allowed entry; no effect when the list is unset/empty. Valid as a project-settings boolean (cascade-trust mode). |
| 4 | `TodoWrite` deprecated → Task tools (`TaskCreate`/`TaskUpdate`/`TaskGet`/`TaskList`) | already-safe (settings) + **WATCH** (`_lib` telemetry) | Settings level: the wide PreToolUse matcher (`…\|NotebookEdit\|TodoWrite\|Task\|mcp__.*`) contains `.*`, so it is evaluated on the regex path, which is **unanchored** (`new RegExp(t).test(name)`, verified in the binary) — the `Task` alternative substring-matches all four Task tools, so hooks keep firing; the `TodoWrite` alternative simply goes inert. WATCH: the telemetry enums `_RECOGNIZED_TOOL_NAMES` (`.claude/hooks/_lib/tool_lifecycle.py:84`) and `_TOOL_CALL_LIFECYCLE_TOOL_NAME_ENUM` (`.claude/hooks/_lib/audit_emit.py:7676`) list `TodoWrite` but not the Task tools, so Task-tool lifecycle events coerce to `"other"` — a telemetry-granularity gap only (no governance/security impact), fixable by a one-line frozenset addition in canonical `_lib/**` at a future ceremony. Not staged here (outside this deliverable's file assignment). |
| 5 | Hyphenated hook matchers now exact-match (v2.1.195 change) | already-safe (verified) | Our only hyphenated matcher is `mcp__codex__codex\|mcp__codex__codex-reply` (PreToolUse + PostToolUse). Binary-verified matcher evaluation: a matcher passing the "simple" charset test is split on `\|`/`,` and compared as **exact segments** — both segments name real tools, so it fires; if routed down the regex path instead, the alternation also fires (hyphen is literal in a regex). Either path works. The v2.1.195 warning class ("matches no tool (it is compared as an exact string)") targets bare server-prefix matchers like `mcp__someserver`, which we do not use — our wildcard matcher is already `mcp__.*`. No change needed. |
| 6 | Model pins current (`claude-fable-5` / `claude-opus-4-8` / `claude-sonnet-4-6` / `claude-haiku-4-5`) | already-safe | All 4 `availableModels` pins and the `fallbackModel` entry are current ids. The array form of `fallbackModel` (`["claude-opus-4-8"]`) is schema-valid in 2.1.202 (`v.array(v.string())`, tried in order). No change. |

## WATCH register (deliberate non-adoptions — each with a reason)

| Item | Why not adopted now | Re-visit trigger |
|------|--------------------|------------------|
| `envVars` deny for `GH_TOKEN` / `GITHUB_TOKEN` / `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` | `gh`, the `claude -p` eval harnesses, and the codex pair-rail all run through sandboxed Bash and may legitimately consume these from env; denying them blind could break the pair-rail the day `sandbox.enabled` flips. | Owner-run probe of which auth paths those CLIs actually use on this machine (an automated env scan was correctly refused by the auto-mode classifier during authoring); tighten after. |
| `envVars` `mask` mode + `injectHosts` | Sentinel-in-sandbox + proxy injection rests on egress-proxy TLS assumptions we have not probed; `allowPlaintextInject` guards a plain-HTTP injection path we do not want open. Staged config uses `deny` only, `allowPlaintextInject: false` explicit. | Only if a workflow needs a real credential inside sandboxed Bash (none does today). |
| Recursive dotenv coverage in `credentials.files` | The binary schema has **no glob support** for `files[].path` — `.env` entries cover the repo root only. Subdirectory dotenv reads remain owned by the `permissions.deny` `Read()` rail (tool-level) + contamination CI; the subprocess-read gap for subdir dotenvs is a known residual. | If the harness adds glob/directory-recursive semantics for `files[].path`. |
| Task-tool names in `_lib` telemetry enums | Canonical `_lib/**` is outside this deliverable's file assignment; the gap is granularity-only (see finding 4). | Next `_lib` canonical ceremony. |

## Honest residuals of what WAS staged

1. **Harness-side fail-open.** The 2.1.202 loader drops an invalid `credentials`
   entry (warn: "This credential is NOT protected until the entry is fixed") and
   drops the whole block on schema failure ("no credential protection is applied
   until it is fixed"). This is why `sandbox.credentials` is defense-in-depth and
   the hook-side **fail-closed** credential-leak guard in `check_bash_safety.py`
   remains the primary rail. The staged block was validated against the binary's
   own schema to minimize this risk, but the failure mode is the harness's, not ours.
2. **Double inertness of item 2.** `sandbox.credentials` protects *sandboxed*
   commands only; the staged sandbox still ships `enabled: false` (Wave-E Codex R1
   P1 decision). Landing the staged file changes nothing at runtime until the
   Owner flips `enabled: true` after the documented egress probe.
3. **`enforceAvailableModels` policy caveat (from the binary).** If a managed-policy
   settings source exists but fails to load, the harness refuses cascade-trust mode
   and disables model enforcement from user/project settings with a warning —
   another harness-side fail-open. Acceptable: the `availableModels` pins still
   gate explicit model selection.
4. **`~/.gnupg` deny.** Included in the file-deny list (private keys are
   credentials). When the sandbox is enabled, GPG operations inside sandboxed Bash
   were already impossible (HOME is outside `readablePaths`/`writablePaths`); this
   entry keeps that true even if an adopter later widens `readablePaths`. The
   Owner's signing ceremony is unaffected (it runs outside sandboxed Bash today).

## Provenance

- Base for the staged file: `.claude/plans/PLAN-153/staged/wave-E/.claude/settings.json`
  (carries the Wave-E deny baseline; base existed, so no base=live fallback was needed).
- Staged output: `.claude/plans/PLAN-153/staged/wave-backlog/.claude/settings.json`
  (`python3 -m json.tool` PASS; diff vs wave-E base = 82 added lines, 0 removed/changed).
- Schema evidence: string-extracted zod definitions from the 2.1.202 binary
  (`sandbox.credentials` object, `files`/`envVars` sub-schemas, `enforceAvailableModels`
  describe text, matcher-evaluation function, `fallbackModel` array schema).
