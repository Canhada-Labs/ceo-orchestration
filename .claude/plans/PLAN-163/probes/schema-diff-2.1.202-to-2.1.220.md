# Hook-schema diff — Claude Code 2.1.202 → 2.1.220 (PLAN-163 T2.2)

Date: 2026-07-28. Method: both binaries' embedded minified-JS bundles carved and
compared (zod source text, not docs). Full recipe + hashes in
`hook-schema-2.1.220.json` `_meta` (2.1.220 local install sha256 `8addc857…`;
2.1.202 baseline re-fetched from npm `@anthropic-ai/claude-code-darwin-arm64@2.1.202`,
binary sha256 `7414f707…`, `--version` verified).

## Headline deltas (complete set found)

| # | Surface | 2.1.202 | 2.1.220 | Disposition for PLAN-163 |
|---|---------|---------|---------|--------------------------|
| 1 | Hook event enum | 30 events | 31 events: **+`DirectoryAdded`** | T3.1 target confirmed to exist only ≥2.1.2xx (absent in 202) |
| 2 | `UserPromptSubmit` input | no `source` | **+`source?` enum `[user,sdk,system,loop_wakeup,schedule_wakeup]`** (describe: only set for Anthropic-internal sessions while trialed) | Hooks must tolerate the extra key (ours parse dict-get, safe); do NOT depend on it yet |
| 3 | `SessionStart.source` enum | `[startup,resume,clear,compact]` | **+`fork`** | `check_session_start`-family fixtures should include `fork` as a valid literal |
| 4 | Model enforcement | allowlist only | **`model_access` entitlement joins `availableModels`** as second restriction source; plan-mode upgrade models (opusplan/haiku-plan) checked and downgraded to "newest permitted Opus/Sonnet"; default pick carries settings-vs-entitlement attribution | Neutral for dogfood (no managed entitlements), but T1.1 wording should say "allowlist or entitlement" |
| 5 | Everything else probed | — | **IDENTICAL** (see per-field tables) | No hook rewrite needed for 2.1.220 conformance beyond T3 additions |

No event was REMOVED; no input field was removed or re-typed; the common output
schema and the full `hookSpecificOutput` union (20 arms) are byte-equivalent
after minifier-rename normalization.

## Per-field disposition — the 8 schema-dense wired hooks

Legend: **=** identical 202→220 (field present in both, same type/optionality);
**+** added in 220. Base fields (`session_id`, `transcript_path`, `cwd`,
`prompt_id?`, `permission_mode?`, `agent_id?`, `agent_type?`, `effort?{level}`)
are **=** for all events (base object verbatim-identical).

### 1. PreToolUse
| Field | 202→220 |
|---|---|
| `tool_name: string` | = |
| `tool_input: unknown` | = |
| `tool_use_id: string` | = |
| out `hookSpecificOutput{permissionDecision[allow,deny,ask,defer]?, permissionDecisionReason?, updatedInput?, additionalContext?}` | = |

### 2. PostToolUse
| Field | 202→220 |
|---|---|
| `tool_name`, `tool_input`, `tool_response`, `tool_use_id` | = |
| `duration_ms?` | = (already in 202) |
| out `{additionalContext?, updatedToolOutput?, updatedMCPToolOutput?}` | = |

### 3. PostToolUseFailure
| Field | 202→220 |
|---|---|
| `tool_name`, `tool_input`, `tool_use_id`, `error: string` | = |
| `is_interrupt?`, `duration_ms?` | = |
| out `{additionalContext?}` | = |

### 4. UserPromptSubmit
| Field | 202→220 |
|---|---|
| `prompt: string` | = |
| `session_title?` | = |
| `source?: enum[user,sdk,system,loop_wakeup,schedule_wakeup]` | **+220** (optional; internal-trial per describe) |
| out `{additionalContext?, sessionTitle?, suppressOriginalPrompt?}` | = |

### 5. Stop
| Field | 202→220 |
|---|---|
| `stop_hook_active: boolean` | = |
| `last_assistant_message?` | = |
| `background_tasks?: TaskSummary[]` | = |
| `session_crons?: CronSummary[]` | = |
| out `{additionalContext?}` (+ common `decision:[approve,block]`) | = |

### 6. SubagentStop
| Field | 202→220 |
|---|---|
| `stop_hook_active`, `agent_id`, `agent_transcript_path`, `agent_type` | = |
| `last_assistant_message?`, `background_tasks?`, `session_crons?` | = |
| out `{additionalContext?}` | = |

### 7. SessionStart
| Field | 202→220 |
|---|---|
| `source: enum` | **enum widened**: `+fork` (`[startup,resume,clear,compact,fork]`) |
| `agent_type?`, `model?`, `session_title?` | = |
| out `{additionalContext?, initialUserMessage?, sessionTitle?, watchPaths?, reloadSkills?}` | = |

### 8. SessionEnd
| Field | 202→220 |
|---|---|
| `reason: enum[clear,resume,logout,prompt_input_exit,other,bypass_permissions_disabled]` | = |
| out: no event-specific arm (common fields only) | = |

Supplementary (wired, thin): **PreCompact** `{trigger:[manual,auto], custom_instructions: string|null}` = ; **PostCompact** `{trigger, compact_summary}` =.

## T3 events (new registrations planned)

### DirectoryAdded — NEW event in 2.1.220 (did not exist in 2.1.202)
- Input: base + `directory: string` ("Absolute path of the directory that was
  added."), `source: enum["slash_command","register_repo_root"]`.
- Matcher matches against `source` (literal-matcher set membership verified).
- **Blockability: NO.** No `hookSpecificOutput` arm exists for DirectoryAdded.
  `decision:"block"` would parse (it is a common field) but is consumed by no
  call site: the executor collects only `systemMessage`s, and both call sites
  (/add-dir, SDK `register_repo_root`) fire the hook **fire-and-forget AFTER
  the directory is already registered** (permission-context mutation and
  local-settings save happen first; hook failures are only logged). The SDK
  tool description states duplicates "are denied with an error; the
  registration pipeline and DirectoryAdded hooks do not re-run".
- ⇒ **T3.1 must take the notification-only branch (observer-WRITER +
  PreToolUse write-guard consumers). The hardblock-floor branch is dead** on
  this substrate. The plan's CF-9 hard gate resolves to: post-facto; the block
  window is "whole remainder of session" (root is never removed by hook output).

### Notification — present and identical in BOTH versions
- Input: base + `message: string`, `title?: string`, `notification_type: string`.
- Matcher matches `notification_type`. Output arm: `{additionalContext?}`.
- Safe to wire on any version ≥2.1.202 (also present in the 202 enum).

## Answers to the three plan questions

### (i) `enforceAvailableModels` default-resolution in 2.1.220 (T1.1 / CF-6)
- Schema describe text **verbatim-identical** to 2.1.202 ("…Default resolves to
  the first allowed availableModels entry…").
- Runtime (both versions, same function; verified in 220): iterates
  `availableModels` **in list order**; the first entry that expands to an
  allowed AND server-available model becomes the effective Default when the
  tier default is not in the list ⇒ **YES, the 1st availableModels entry
  participates in (wins) default resolution**; ordering of the T5.4 pin list is
  load-bearing.
- If no entry survives (all allowed-but-server-unavailable, or none expands):
  warns and **keeps the tier default** (fail-open to the unconstrained
  default), except under user steering (pins env-free tier builtin).
- **The documented managed-policy fail-open EXISTS UNCHANGED in 2.1.220**:
  "a policy source exists but failed to load; refusing cascade-trust mode
  (model enforcement from user/project settings is disabled until the policy
  source is fixed)". Plus (both versions): partial admin-source failure
  enforces the surviving admin tier only if it carries model policy; the
  enforce flag in a policy view without a policy-owned allowlist disables
  enforcement. Loader coercions are fail-closed (invalid flag → `true`;
  invalid array → empty allowlist).
- ⇒ **Contingency T1.1 stands**: pin the session default explicitly in the
  same commit that appends sonnet-5, because enforcement from project settings
  can be silently disabled by a broken policy source, and a no-survivor list
  falls back to the tier default.

### (ii) Unknown event-keys in `settings.json` (T3.4 version-floor)
- **Both 2.1.202 and 2.1.220 IGNORE unknown hook-event keys**: the loader
  `delete`s the key and records a **warning** — `Unknown hook event "<k>" was
  ignored. Valid events: <enum>` — all other hook events and all other
  settings keep loading. A second parse-path marks the entry invalid
  per-entry (never whole-file). Only `hooks` itself being a non-object drops
  the (whole) hooks block — still with the rest of settings intact.
- Practical consequence: an adopter on 2.1.202–2.1.219 receiving a template
  with a `DirectoryAdded` key gets a warning and a no-op, not a failure.
- **Residual**: the SUPPORT.md floor is `>=2.0`; no 2.0.x binary was probed
  (recipe in the JSON works for any npm-published version — one 70 MB fetch +
  one grep). Until that probe or an explicit floor bump, template emission of
  new events stays FEATURE-GATED per T3.4.

### (iii) DirectoryAdded / Notification shapes and block decision
- Shapes: above. **`DirectoryAdded` does NOT accept an effective block** —
  schema-tolerated, runtime-ignored, event fires post-registration.
- `Notification` is observe/annotate-only (`additionalContext`) — matches the
  planned audit-emit wiring (T3.2), no enforcement semantics to claim.

## Settings/hook-adjacent keys checked for drift (no delta)
`allowManagedHooksOnly`, `allowedHttpHookUrls`, `httpHookAllowedEnvVars`,
hook types (`command`/`prompt`/`agent`/`http`/`mcp_tool`/callback/function),
`sandbox.credentials` loader (drop-with-warning fail-open wording), and the
common output field `terminalSequence` (OSC allowlist) are present and
identical in both versions.
