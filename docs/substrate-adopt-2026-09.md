# Substrate adoption record — sweep 2026-09 (CC 2.1.221 → 2.1.280, API/SDK, Codex 0.145 → 0.155)

> **Status: RECORD (S357, 2026-09-22).** Every row below carries a
> disposition. §Routing names the items this change set carries and the
> ones it leaves to later work. A disposition that says only "later"
> names no plan, follow-up id or owner. The change set that carries this
> record also carries the free cures that §Routing marks **yes** under "In
> this change set", plus the ledger bump in `.claude/scripts/substrate-watch.json`
> (§Ledger). Nothing canonical travels with it. **Land order:** after the
> v1.4.1 GA tag. Until then the GA cut keeps the tree frozen since the rc
> tag: only `CLAUDE.md` and numbered plan files may change. The GA cut
> script that enforces this is not in the tree at `19771fa1`.
> **NO-SPEED-CLAIM:** nothing here claims framework throughput or speed;
> fast-mode rows carry prices only.

**Evidence convention.** Repo pointers are at tree `19771fa1` (main at record
time). "Bundle" means the Claude Code 2.1.280 install (npm publish
2026-09-22T15:44Z), read as bytes, not as docs. Rows marked **[sweep]** repeat
a fact the verified S357 sweep measured that this record did not re-probe;
everything else was re-checked on 2026-09-22 (UTC 2026-09-23) against the
bundle, the upstream pages, or the tree. Every row describes the tree
`19771fa1`, before any cure. §Routing says which cures this change set
carries. "The v1.4.2 plan" below means the v1.4.2 release plan drafted on
2026-09-22, which is not in the tree at `19771fa1`; its waves are named by
purpose (Codex re-pin wave, Opus 5.5 wave, adaptive-only wave). Facts
corrected or re-checked after review on 2026-09-23 carry that date.

Substrate at record time:

| Component | State (2026-09-22) |
|---|---|
| Claude Code | 2.1.280 installed (`claude --version`); npm dist-tags `latest` = 2.1.280, `stable` = 2.1.267 |
| Codex CLI | 0.155.0 installed and pinned (`codex-cli-pin-manifest.json` `package_version`); npm `latest` = 0.156.0 (2026-09-22T19:55Z) — the re-pin belongs to the v1.4.2 plan's Codex re-pin wave, not this record |
| Agent SDK | TypeScript 0.3.280 (npm, 2026-09-22T15:51Z); Python 0.2.158 (PyPI `latest`, uploaded 2026-09-23T01:39Z; also the changelog head) |
| Grok Build CLI | 1.0.13 `[stable]` installed against the exact pin 0.2.93 — not reconciled here |
| Ledger | `claude_code` still read 2.1.198: the 2026-08 G17 refresh (sdk-ts 0.3.220, sdk-py 0.2.128, claude_code 2.1.220) never reached the file |

**Codex moved after the record (re-checked 2026-09-23).** npm `latest`
became 0.156.1 (published 2026-09-23T02:45Z), and this machine's global
Codex was replaced by 0.156.1: the installed package's files carry mtime
2026-09-23T04:01Z (01:01 at -03). What ran the upgrade is not recorded.
That binary is outside both pins, the semver range `>=0.128.0,<0.156.0`
and the 0.155.0 payload manifest. `check_pair_rail.py --verify-codex-pin`
returns `mismatch` / `payload_sha256_mismatch` (exit 1), and
`check-substrate-watch.py --probe-installed` reports `codex_cli` and
`codex_harness` as drift. Until the Codex re-pin wave lands or 0.155.0 is
reinstalled, the pair-rail hook blocks every edit it would send to review
(ADR-182, fail-closed).

## Operator action: rotated audit archives vs the transcript sweep

**Mechanism (bundle 2.1.280).** The transcript-retention sweep walks
`<config dir>/projects`, visits **every** project subdirectory, treats any
top-level file whose name ends in `.jsonl` as a candidate (no name filter —
the UUID check only gates sidecar cleanup), and unlinks it when its mtime is
older than `now − cleanupPeriodDays`. The cutoff comes from the merged
settings of the session that **runs** the sweep (schema default 30), so a
session launched in any directory without a larger value sweeps this
project's state dir at 30 days. The 2.1.228 fix covered only the memory
folder. Rotated audit archives are `audit-log-YYYY-MM[-N].jsonl` in that same
top level (`.claude/hooks/_lib/audit_rotation.py`) — exactly the candidate
shape. The dogfood `.claude/settings.json` sets 90, which binds only sessions
launched in this repo; `templates/settings/settings.user.json` deliberately
does not ship the key.

**How a loss shows.** A rotation normally writes a `chain_reset_marker` as
the first line of the new live log, and its `previous_archive_path` names
the archive it closed (`_lib/audit_emit.py`; when a sidecar write fails,
the rotation proceeds without a marker). An archive that the sweep deleted
leaves that marker pointing at a file that no longer exists. The marker
proves the file existed; it does not prove what deleted it, so attribute a
loss to the sweep from mechanism and age, not from an observed deletion
event.

**Mitigation (operator, outside the tree):** run `.claude/scripts/ceo-backup.sh`
(it tars `audit-log-*.jsonl` to `~/.ceo-backups/<slug>/`), once more with
`--audit-dir` for any pre-PLAN-182 basename-slug state dir; set a large
user-scope `cleanupPeriodDays`; never `touch` archives to postpone deletion —
it falsifies the mtime evidence. The structural cure (rotate out of the
swept top level) is canonical and cross-cutting — G1. The retention row
"90 days live on disk" in `docs/soc2-audit-mapping.md` does not hold for
archives under this mechanism; this change set replaces it with the bound
above and the same mitigation (`docs/soc2-audit-mapping.md`, `INSTALL.md`
§Audit-log retention).

## Gap-matrix dispositions (G1–G33)

| # | Substrate change | Disposition | Evidence / record |
|---|---|---|---|
| G1 | Transcript sweep deletes aged top-level `*.jsonl` in every project dir (above) | ADAPT — structural cure later (canonical: `audit_rotation.py`, `runtime_paths.py`, ADR-001, archive readers, `verify_chain` across the move, red-first test) + operator mitigation NOW | §Operator action |
| G2 | Harness slug maps every `[^A-Za-z0-9]` to `-`, caps at 200 chars and appends a base36 hash (CHANGELOG 2.1.224 long-path fix, 2.1.239 paths differing only by `_`/`-`/`.`) | ADAPT later (canonical resolver + ADR-001 amendment) | Bundle sanitizer `replace(/[^a-zA-Z0-9]/g,"-")` + 200 cap. `runtime_paths.project_slug` maps only `/`, `test_runtime_paths.py` pins dots/underscores as preserved, and the ADR-001 amendment calls the derivation the harness's own. Broken shape: readers of HARNESS-owned dirs (`cc-native-usage-pull.py`, `memory-prioritize.py`) for project paths holding `.`, `_` or spaces. The dogfood path holds none, so both derivations agree there. The framework's own state slug must not change (adopter dir migration) |
| G3 | `CLAUDE_CODE_PROJECT_DIR_NAME` (2.1.234) | DOC | Bundle: honoured only when `CLAUDE_CONFIG_DIR` is set, which project `env` can no longer set (2.1.251, §No impact). No code reader (`git grep`: research docs and plan files only). Answers open probe 5 of `docs/research/orchestrator-operating-model-S339.md`: host-level carrier, not a repo-settable one |
| G4 | Task-tracking tools withheld from Opus 4.8, Sonnet 5, Fable 5, Mythos 5 and newer (2.1.233), then offered only to an older-model allowlist (2.1.268; opt-in `CLAUDE_CODE_ENABLE_TODO_TOOLS=1`); TaskOutput removed (2.1.277) | ADAPT (text, free land) | `.claude/commands/ceo-boot.md` and `debate.md` still list TaskCreate/TaskList in `allowed-tools`, and `/ceo-boot` assumes the tools exist; the dogfood session model (`claude-opus-5`) and the new Opus default are outside the 2.1.268 allowlist. Bundle: the gate also opens for background/job sessions, a launch-option opt-in, model ids it cannot resolve and Bedrock application inference profiles, and none of the task tools carries a permission check of its own, so the `allowed-tools` entries pre-approved nothing |
| G5 | Workflow stops reading an out-of-scope `scriptPath` before the permission check (2.1.251) | ADAPT (canonical; v1.4.2 candidate with its own rail round; the tracked `CHANGELOG.md` at `19771fa1` does not list it under Known-open) | Our PreToolUse launch ledger (`_lib/launch_ledger.py` `script_record`) reads and snapshots any regular file named by `scriptPath` — size-capped, no path confinement — before the harness permission check, and `ceo-launches.py` can write the snapshot out again: the shape the harness closed, re-opened by our hook. Canary probe reproduced twice **[sweep]** |
| G6 | Thinking modes: Opus 5.5 returns 400 for `thinking` `disabled` and manual `enabled`; Fable 5 / Mythos 5 are adaptive-only; Opus 5 allows `disabled` only at effort ≤ `high` | ADAPT → v1.4.2 plan, adaptive-only wave | API release notes (2026-09-22, 2026-07-24, Fable 5 launch). `_ADAPTIVE_ONLY_MODELS` in `adapters/live/claude.py` has no Opus 5.5 entry. Latent: the live adapter is opt-in with no production instance **[sweep]** |
| G7 | `CLAUDE_CODE_SUBAGENT_MODEL` becomes a default that definition `model:` and per-spawn models beat (2.1.251); `CLAUDE_CODE_SUBAGENT_MODEL_FORCE` overrides both (2.1.257) | ADAPT (free guard) + DOC (ADR-144 amendment, canonical); re-verify the Workflow leg at each bump | `git grep SUBAGENT_MODEL_FORCE` = 0. FORCE reaches Workflow `agent()` model pins: the 2.1.280 bundle (read 2026-09-22) drops an `agent()` model under it with the warning `Workflow agent model "…" ignored: CLAUDE_CODE_SUBAGENT_MODEL_FORCE is set`. Existing guards key only on the old variable (`test_subagent_model_override_removed.py`, `scripts/install-accelerators.sh`); the rationale "documented to beat per-agent `model:`" in that script and in ADR-144 is false since 2.1.251. The prohibited carrier moves to `_FORCE`: FORCE + a cheap model drops VETO roles below the floor. Class, by shape: text stating that `CLAUDE_CODE_SUBAGENT_MODEL` overrides per-agent `model:` (true only before 2.1.251). This change set rewords it in the installer and its test; free docs and generated text outside this change set, and canonical doctrine text (the routing hook's settings doctrine, ADR-144), still carry it. One reword by shape: the variable is the default for agents that declare no `model:`, and FORCE is the carrier that overrides |
| G8 | `PreModelSwitch` / `PostModelSwitch` hook events (2.1.251) | ADOPT as observer later (canonical hook + settings + T3.4 feature gate; emit `{}` on infra error, since a failing switch hook can block switching) | Bundle enum = 33, diffed against `.claude/data/hook-schema-2.1.220.json` (31): exactly these two added, none removed. Unregistered today; already flagged in `docs/research/s339-orchestrator-study/03-claude-code-substrate.md`. Trips the `cc_workflow_rail` enum drift probe (§Ledger) |
| G9 | Claude Opus 5.5 (`claude-opus-5-5`), default Opus since CC 2.1.280: $4/$20 per MTok, cache hits 0.05× ($0.20), fast mode $8/$40, batch $2/$10 | ADAPT — price mirrors ride the v1.4.2 Opus 5.5 wave | Pricing page (fetched 2026-09-22). `git grep claude-opus-5-5` = 0: no price row, and the per-model cache-read override holds only `claude-fable-5-1` (`budget-summary.py`, `ceo-cost-transcripts.py`), so the 0.10× default prices Opus 5.5 cache reads at 2×. Class, by shape: every per-model mirror keyed by model id (price, alias, tier order, fleet oracle, model-currency expected reds) — one census, one patch |
| G10 | `availableModels` accepts family aliases, version prefixes and full ids | VERIFY (recorded in the v1.4.2 plan draft) | The dogfood list holds `claude-opus-5`, not `claude-opus-5-5`. The schema text does not settle whether that entry admits `claude-opus-5-5`; segment-prefix admission was read from the minified matcher **[sweep]**. Settle with a `/model claude-opus-5-5` probe under the dogfood settings before the Opus 5.5 wave relies on it |
| G11 | Effort per model (2.1.251); a level saved before that no longer applies to newly released models such as Opus 5.5 (2.1.280); `maxEffortLevel`/`modelSettings` (2.1.267); `effort:` frontmatter honoured on pinned-default models (2.1.267); Opus 4.7/4.8/Fable 5 stop holding launch-default effort over explicit levels (2.1.280) | ADAPT — operator setting now; `effort:` frontmatter on Owner-signed agents later (measure first) | Bundle: a top-level user `effortLevel` resolves as `legacyUserEffort`, which the 2.1.280 CHANGELOG limits to models that predate per-model effort; a newer model with no `modelSettings[<id>].effortLevel` (Opus 5.5) starts at its default. Operator action: a per-model entry for `claude-opus-5-5` |
| G12 | A PreToolUse/PermissionRequest hook entry the loader cannot read is `severity: fatal`, and a fatal error loads that whole settings file as `null` (every registration and deny rule in it dropped) | ADOPT (free test; land before the v1.4.2 Opus 5.5 wave edits settings; pin CC version + bundle sha, since the replica derives from minified text) | `unloadableGuard` present in the 2.1.277/2.1.278/2.1.280 bundles; absent from 2.1.220 **[sweep]** (no 2.1.220 build on the record machine); fatal → `{settings: null}` read in the 2.1.280 loader. Runtime spot-check on 2026-09-23 (UTC), `claude doctor` on 2.1.280 in a scratch project with scratch `HOME` and `CLAUDE_CONFIG_DIR`, no model call: a PreToolUse entry of unknown `type` printed the fatal reason ("…so nothing it sits in is applied until the entry is fixed or removed"), and the same entry under PostToolUse printed "entry ignored". 0 findings in today's settings; planted controls go FATAL while `check_harness_config.py --static` stays green **[sweep]**. The test ties its pin to the ledger: moving `claude_code.last_seen` turns it red until the rule is re-derived from the new bundle |
| G13 | Hook input `mcp_server {name, source}` on PreToolUse, PermissionRequest, PostToolUse, PostToolUseFailure (first version 2.1.274 **[sweep]**) | ADAPT later (canonical guards; fallback below the first version) | Bundle schema; `source` is an open set (sdk, plugin, user, project, local, dynamic, managed, enterprise, claudeai, agent). The Codex MCP guards identify the server by the `mcp__codex__` name prefix (`check_codex_filewrite.py`, `check_mcp_response.py`, settings matchers). Limited value: a project-scoped impostor also reports `source=project`, as our own template does **[sweep]** |
| G14 | SessionStart on resume receives staleness and estimated re-cache cost (2.1.251) | ADOPT later (free measured data for PLAN-190/191/179; canonical SessionStart + SPEC action) | Bundle fields `seconds_since_last_response`, `context_tokens`, `prompt_cache_likely_expired`, `estimated_cache_write_usd`; `git grep seconds_since_last_response` = 0 |
| G15 | API: forced `tool_choice` (`any`/`tool`) returns 400 on Opus 5.5, Fable 5.1 and Mythos 5.1 | ADAPT later (ride the v1.4.2 adaptive-only wave only if the live adapter is already in that pack) | Release notes. `adapters/live/claude.py` documents and forwards forced `tool_choice`, `claude_batch.py` forwards it, and `docs/cookbook-patterns.md` teaches `{"type": "tool"}`. Latent: no production caller **[sweep]** |
| G16 | Python `anthropic` 1.0 (2026-08-20) removes `temperature`/`top_p`/`top_k` from Messages methods; the API already rejects non-default sampling values on Opus 4.7 and later | ADOPT (free land, independent of the v1.4.2 ceremony) | `.claude/scripts/run-skill-benchmark.py` passes `temperature=0, top_p=1` on every call, and its per-scenario `except Exception` turns the failure into a silent `score: 0.0, skipped: true` — the run does not abort. `benchmarks.yml` and its template install `anthropic` unpinned. Class, by shape: text that states the benchmark runner's sampling settings ("at temperature 0", "temp=0") or passes the runner a `--temperature` flag, which its argument parser does not define. This cure makes that text false. The class has free and canonical members, and this change set edits none of them. No test pins the absence of sampling parameters yet |
| G17 | Fast mode: Opus 5.5 $8/$40; Opus 5 and 4.8 $10/$50; Opus 4.7 fast returns an error; Opus 4.6 fast runs at standard rates | DOC (free; the doctrine test pin changes consciously with the doc) | Pricing page (2026-09-22). `docs/provider-pricing.md` still quotes Opus 4.6/4.7 fast at $30/$150 and `test_a4_pricing_doctrine.py` asserts that string; `docs/ACCELERATORS.md` §Fast mode names only Opus 5/4.8 |
| G18 | Model-deprecations page: newest history entry still 2026-06-05; the page moved (the old URL 307-redirects) | DOC (Owner-run refresh recipe) | Page fetched 2026-09-22. `.claude/scripts/model-deprecations.json` `_meta`: `fetched` 2026-06-12, `source` still the old `/docs/en/docs/…` URL; its entries already hold `claude-mythos-preview` |
| G19 | Codex 0.154.0 removed the deprecated `codex mcp-server` entry point (#42993) | ADAPT — template now (free), matchers later (canonical) | Pinned 0.155.0: `codex --help` lists no `mcp-server` and the string is absent from the native binary. The pin's semver range still admits the older versions that carried it. At `19771fa1`, `templates/.mcp.json` registers `codex` with `args: ["mcp-server"]`, `scripts/install.sh` ships it in the maintainer ceremony, `INSTALL.md` documents it, and the dogfood matchers `mcp__codex__codex\|…-reply` guard a tool family the pinned Codex can no longer serve. The pair-rail gate does not use the server: `check_pair_rail.py` runs `codex exec` as a subprocess. The `mcp__codex__*` hooks do (`check_codex_filewrite.py`, and `check_codex_response.py`, whose review-shaped branch emits the ADR-145 `codex_review_invoked` event); they stay idle on Codex ≥ 0.154.0 and wherever no `codex` server is registered. Classes left after the template cure, by shape: Codex-harness installer output that says a Claude-host `.mcp.json` registers the codex reviewer (free, not in this change set); comments and docstrings that call the Codex MCP server the pair-rail transport, and the `mcp__codex__*` matchers (canonical) |
| G20 | Codex per-hook trust hash changed between 0.139 and 0.155 | DOC now; ADR-161 §6a amendment later | Probe: 9 of the 12 shipped entries match an entry of the 0.139 recording on the five fields, and all 9 hash differently under 0.155; the 0.139 hashes read `modified` **[sweep]**. Codex hooks docs (2026-09-22): trust is recorded against the hook's current hash; new or changed hooks are skipped until trusted. Upstream `hook_hash()` in `codex-rs/hooks/src/engine/discovery.rs` at `rust-v0.155.0` hashes the whole normalized entry, more than the five 0.139 fields (a test asserts that `additionalContextLimit` changes the hash). The command string is part of it, and every shipped command embeds the install's absolute path, so an install at another path hashes separately. `INSTALL.md` and `templates/codex/AGENTS.md` describe what the hash covers — re-check after the re-pin. Class, by shape: Codex-harness installer output that still says trust is keyed to the command line and omits the upgrade re-key (free, not in this change set) |
| G21 | `codex app-server` exposes `hooks/list` with per-hook `currentHash`/`trustStatus` | ADAPT later | Strings present in the 0.155.0 native binary. The arming check in `scripts/_codex_harness.sh` declares ARMED from project trust only, with a reminder about per-hook trust |
| G22 | Codex PreToolUse: `permissionDecision: "ask"` is parsed but unsupported — the hook run is marked failed and the tool call continues; `updatedInput` is honoured only with `allow` | ADAPT (canonical) later + DOC now | Codex hooks docs (2026-09-22). `_write_decision_host` in `_lib/adapters/codex.py` emits only allow/deny and never forwards `updatedInput`, so the opt-in force-push rewrite (`CEO_BASH_FORCE_PUSH_REWRITE=1`, default off; `ask` + `updatedInput` on Claude Code) degrades to a plain allow on the Codex host. Re-measured 2026-09-22 from the worktree hooks on a recorded Codex PreToolUse payload for `git push origin main --force` under `CEO_HOOK_ADAPTER=codex`: flag unset, `deny`; flag `1`, a plain `allow` with no rewritten command. Documentation in this change set warns; it does not cure the gap, and nothing may call it mitigated. Canonical follow-up: when the active adapter cannot express `ask` with `updatedInput`, the rewrite branch returns `deny` (fail closed), with a red-first test under `CEO_HOOK_ADAPTER=codex` that fails when the flag yields `allow` |
| G23 | Codex hook events: SessionEnd (0.145.0, #33895), Interrupt (0.150.0, #40511), SessionStart tells forked sessions apart (0.155.0, #44349) | ADOPT later | Codex release notes. `templates/codex/hooks.json` registers 6 events (PreToolUse, PostToolUse, SessionStart, Stop, SubagentStart, UserPromptSubmit) |
| G24 | "Function hooks" (plugin hook modules), early access | SKIP (watch) | The 2.1.277, 2.1.278 and 2.1.280 bundles carry `CLAUDE_CODE_ENABLE_FUNCTION_HOOKS`, `$.model.classify`, `$.session.usage`, `session.compact`; the 2.1.220 bundle carries none **[sweep]**; no CHANGELOG line through 2.1.280. The 2.1.276 CHANGELOG is one advisor-tag fix, so an earlier attribution of the feature to 2.1.276 is refuted; `claude plugin eval` is 2.1.269 |
| G25 | 200-subagent-per-session spawn cap removed (2.1.224); concurrency and depth limits still apply | DOC | The 2026-08 record's G5 row ("200 per session") is stale |
| G26 | `/code-review` runs in a background agent at every level (2.1.232); leaner inline prompts instead of many review subagents on models without tuned settings (2.1.274) | DOC | The 2026-08 G10 doctrine stands: same-vendor advisory, never discharges the cross-vendor VETO |
| G27 | Workflow size guideline `medium` now means fewer than 10 agents (was 15); Pro plans default to `small` (2.1.271); advisory only | VERIFY | Dogfood sets `workflowSizeGuideline: "medium"` and its `_posture_comment` still says "fewer than 15"; the audit-fanout workflow runs 8 finders plus per-finding refuters |
| G28 | Subagent results reach the main agent under a header marking them as subagent output (2.1.277) | DOC | Reinforces PROMPT DEFENSE — subagent text cannot pass as the session's own instructions; nothing to change |
| G29 | Token-cost knobs: `/skill-doctor` (2.1.261), `bashOutputMaxChars` (2.1.261), `promptCacheTtl`/`subagentPromptCacheTtl` (2.1.243), agent `experimental.cacheTtl` (2.1.248), agent `omitClaudeMd` (2.1.271), `CLAUDE_CODE_WORKFLOW_MAX_CONCURRENT_AGENTS` (2.1.269), same-prefix sibling stagger (2.1.229), workflows pause at the usage limit (2.1.271) | DOC → PLAN-190/191 | `docs/research/s354-token-consumption-study/` covers `bashOutputMaxChars`, the prompt-cache TTL settings and `omitClaudeMd`; the other five are not in it (`git grep`) |
| G30 | Without `CLAUDE.md`, Claude Code reads `AGENTS.md` as project instructions (2.1.277; not yet on Bedrock/Vertex/Foundry) | VERIFY | `scripts/install.sh` ships `CLAUDE.md` only in the maintainer ceremony, while the Codex and Grok harness installers emit an operator `AGENTS.md` at the target root: a user-ceremony adopter with either harness and no `CLAUDE.md` of its own now loads that file into Claude Code sessions |
| G31 | Agent SDK: TypeScript to 0.3.280 (type removals `MonitorInput.persistent` and the never-emitted `ExitReason` `bypass_permissions_disabled`); Python to changelog head 0.2.158 (only breaking change since 0.2.128 is skill-name validation, 0.2.129; 0.2.158 adds `verbatim_prompts`) | SKIP + ledger | No repo consumer: `git grep claude-agent-sdk` hits only the ledger and its checker |
| G32 | Grok 1.0.13 `[stable]` installed against the exact pin 0.2.93 | VERIFY (PLAN-156 re-characterization + pin ceremony) | `grok --version` (2026-09-22); `.claude/governance/grok-cli-pin.txt` |
| G33 | npm `stable` is 2.1.267 (2026-09-09), below 2.1.280, the first release with Opus 5.5 | DOC / gate → v1.4.2 Opus 5.5 wave | `npm view @anthropic-ai/claude-code dist-tags` (2026-09-22). `SUPPORT.md` still says "Claude Code ≥ 2.0" and the repo sets no `autoUpdatesChannel`/`minimumVersion`. A 2.1.267 client handed `claude-opus-5-5` is UNMEASURED (2.1.223 holds unrecognized ids to an assumed context window; 2.1.233 logs `unrecognized_model` in print mode) |

## No impact (with evidence)

| Change | Evidence (tree `19771fa1`) |
|---|---|
| PermissionRequest no longer runs agent-type hooks (2.1.280) | No PermissionRequest hook in the dogfood, base or user settings |
| `CLAUDE_CODE_SESSIONEND_HOOKS_TIMEOUT_MS` now also extends SessionEnd hooks that have no per-hook `timeout`, whose default cut is 1.5 s (2.1.268 fix) | `timeout: 5` on the SessionEnd hook in all three settings files |
| Project `env` can no longer set `CLAUDE_CONFIG_DIR`, `CLAUDE_CODE_TMPDIR`, `TMPDIR`/`TMP`/`TEMP` (2.1.251) | None of them in any settings `env` |
| `defaultMode: "bypassPermissions"` in project settings is ignored (2.1.257) | Dogfood and base use `manual`; the user template sets none |
| Permission rules with text after the closing parenthesis become invalid settings (2.1.260) | 0 of 52 rules across the three files |
| Frontmatter `model:` on commands and skills now takes effect (2.1.259) | 0 occurrences |
| Deny/ask rules starting with `!` apply only within their own source (2.1.269) | 0 such rules |
| Monitor loses the `persistent` option (2.1.271) | 0 uses |
| `.md` files starting with a UTF-8 BOM were silently ignored (2.1.239) | 0 tracked `.md` files with a BOM |
| `statusLine.refreshInterval` | Confirmed in the 2.1.280 schema (seconds, minimum 1) — the ledger's "unverified" note is dropped |

## Routing (all after the v1.4.1 GA tag)

"In this change set" is **yes** when the cure ships with this record,
**no** when it is routed to later work.

| Item | Rows | Class | Size | In this change set |
|---|---|---|---|---|
| Audit-archive mitigation + retention caveat | G1 | operator + free doc | XS | **yes** for the docs (`INSTALL.md`, `docs/soc2-audit-mapping.md`); the operator steps run outside the tree |
| Settings guard-loadability test | G12 | free test (before the Opus 5.5 wave) | S | **yes** |
| Opus 5.5 price-mirror census | G9 | rides the v1.4.2 Opus 5.5 wave | S | no |
| `scriptPath` snapshot confinement | G5 | canonical, own rail round | S | no |
| Opus 5.5 effort at user scope | G11 | operator | XS | no |
| Adaptive-only class | G6, G15 | v1.4.2 adaptive-only wave | — | no |
| `.mcp.json` template + INSTALL note | G19 | free | S | **yes**; the installer-output class in G19 is not |
| `/ceo-boot` and `/debate` tool lists | G4 | free | XS | **yes** |
| `SUBAGENT_MODEL_FORCE` guard + stale wording | G7 | free (ADR-144 text is canonical, later) | XS | **yes** for the installer and its test; the wording class in G7 is not |
| Codex host docs (trust re-check, no rewrite under `--harness codex`) | G20, G22 | free | XS | **yes**; the installer-output class in G20 and the G22 code cure are not |
| Pricing docs (fast-mode rows, cache exceptions) | G17 | free | S | no |
| `run-skill-benchmark.py` sampling params | G16 | free | XS | **yes** for the code; the docs class and a test are not |
| Adopter client floor (`SUPPORT.md`/`INSTALL.md`; optional version gate in `upgrade.sh`) | G33 | free / Opus 5.5 wave | XS | no |
| Machine signal for the `cc_workflow_rail` trip (§Ledger) | G8 | free (checker code) | XS | no |
| This record + ledger bump | all | free | S | **yes** |

Canonical and later: G1 cure, G2, G8, G13, G14, G21, the G22 fail-closed
rewrite branch and its red-first test, G22 matcher/serializer work, G23,
the canonical halves of the G7, G16 and G19 classes, and the ADR-144 and
ADR-161 §6a amendments.

## Ledger (`.claude/scripts/substrate-watch.json`)

**Bumped in the same change as this record** (`_meta.fetched` =
2026-09-23, the UTC date of the last fetch; the PyPI read below is from
2026-09-23T01:39Z or later). Dates are UTC: the release date for a
released component, the probe date for `cc_native_usage`.

| Key | last_seen | Basis |
|---|---|---|
| `claude_code` | 2.1.280 (2026-09-22) | Installed; CHANGELOG 2.1.221–2.1.280 read in full (11 version numbers in the range carry no entry). `watch_for` drops the `refreshInterval` "unverified" note and adds the items of G1, G4, G7, G8, G11, G12, G13, G24 and G30, the `syncClaudeAiSkills`/`syncClaudeAiPlugins` settings, and the `stable` dist-tag |
| `cc_native_usage` | 2.1.280 (2026-09-23) | Re-fingerprint on 2.1.280 by the recipe in `.claude/plans/PLAN-178/w12-native-cost-probe.md` §2, read-only, 2026-09-23T01:53Z: both hard meta invariants (`agentType`, `spawnDepth`) held on every workflow meta, no `message.usage` row lacked `input_tokens`/`output_tokens`, and no new path level appeared; additive meta keys `requestNonInteractive`, `requestShape`, `workflowPhase` (absent from the 2.1.232 census). The session probed dispatched through Workflow only, so the task-glob leg was not re-exercised |
| `agent_sdk_ts` | 0.3.280 (2026-09-22) | npm `latest`, publish 2026-09-22T15:51Z; changelog head 0.3.280 |
| `agent_sdk_py` | 0.2.158 (2026-09-23) | PyPI `latest`, uploaded 2026-09-23T01:39Z; also the changelog head. 0.2.157 (PyPI 2026-09-18) has no changelog entry of its own |
| `codex_cli` | 0.155.0 (2026-09-17) | Pinned; installed on 2026-09-22 (the machine moved to 0.156.1 on 2026-09-23, above). Release 0.155.0 published 2026-09-17. `last_seen` is the version the framework was reconciled against, so it stays 0.155.0 until the v1.4.2 Codex re-pin wave, which bumps it to the Codex head at re-pin time after reading every release note from 0.155.1 on (npm: 0.155.1, 0.156.0 and 0.156.1 by 2026-09-23) |

**Held:**

- `cc_workflow_rail` stays 2.1.237 (2026-08-20). Its "hook-event enum
  changed" drift probe is **tripped** (31 → 33, G8). The only evidence on
  2.1.280 is observational: in one session that dispatched through Workflow
  only, the audit log recorded subagent lifecycle events and no spawn-gate
  events, while earlier Agent-tool spawns did record them. No Agent-tool
  spawn fell inside the 2.1.280 window as a same-substrate control, so this
  is weaker than the planted live-fire the ledger asks for: re-run
  `wf_d7af49d9`, or have the Owner accept the observation, before bumping.
  The ADR-191 red branch stands either way. **No machine signal carries
  the trip: a declared prose-only residual.** `check-substrate-watch.py`
  registers no version probe for this key, so it reports the component
  `ok`, and the JSON that nightly-hygiene dimension vii reads (it runs
  `--json --probe-installed`) shows `drift: false`. The trip lives only in
  this record and in the component's `watch_for` text. The cure is checker
  code (register a probe for this key, like `cc_native_usage`): the
  §Routing item "Machine signal for the `cc_workflow_rail` trip", not in
  this change set.
- `codex_harness` stays 0.139.0: the drift runbook requires the ADR-182 pin
  ceremony first, then the Wave-1 fixture re-record; G20 means ADR-161 §6a is
  stale.
- `grok_cli` stays 0.2.93: 1.0.13 is installed but uncharacterized (G32).
  The checker registers no probe for this key either, so it too reports
  `ok` in every mode.

**What the checker shows for the held rows (run 2026-09-23 from the
change-set tree).** Without `--probe-installed` (how `validate.yml` runs
it, as `--check`), the checker compares no installed version, yet prints
`current — substrate reconciled — installed matches last_seen for all
components` and exits 0. With `--probe-installed`, `codex_harness` (and,
since the 2026-09-23 upgrade, `codex_cli`) shows `DRIFT`, while `grok_cli`
and `cc_workflow_rail` show `ok` with "no probe registered". The summary
line's wording is checker code, not in this change set.

## Limits of this record

- The six sweep lanes reached the synthesis truncated at the ingest cap; the
  synthesis compensated by reading the Claude Code CHANGELOG 2.1.221–2.1.280
  in full and checking the critical points in the bundle and on disk. This
  record re-verified every row not marked **[sweep]**, including the Codex
  release notes 0.145–0.155 and hooks docs, which the synthesis had not
  re-read.
- Bundle reads are of minified code: the loader, sweep and effort claims are
  pinned to 2.1.280 and must be re-derived at the next sweep, never carried
  forward by text. For the loader rule (G12) a runtime oracle exists that
  makes no model call: `claude doctor`, run in a scratch project, prints
  the loader's verdict for each settings file. This record ran it on three
  planted documents (G12: the two bad entries, and a clean control that
  printed no settings finding); the other loader shapes in the test rest on the
  text read.
- The API facts come from the platform release notes, pricing and
  deprecations pages as fetched on 2026-09-22; none was exercised with a paid
  request.

## Provenance

- Plan: the v1.4.2 release plan (drafted 2026-09-22, not in the tree at
  `19771fa1`) — Codex re-pin wave, Opus 5.5 wave, adaptive-only wave.
- Previous records: `docs/substrate-adopt-2026-07.md`,
  `docs/substrate-adopt-2026-08.md`.
- Sweep lanes S1–S6 (CC 2.1.221–2.1.280 in three ranges, schema diff
  2.1.220 → 2.1.280, API/SDK, Codex/host) and their verifiers ran in session
  scratch space; their artifacts are not retained in the tree.
