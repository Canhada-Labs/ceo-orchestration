# Solo-dev accelerators (PLAN-128) — what's on, what's opt-in, what's measured

<!-- last-reviewed: 2026-06-07 v1.0.0 (S218: removed the global CLAUDE_CODE_SUBAGENT_MODEL=haiku override) -->

> **Honest status up front:** the accelerators below are **wired and live**, but their
> throughput/cost **multiplier is UNMEASURED**. The framework is a META repo (it builds
> governance), so it is the *wrong lab* to measure coding speedup. The expected range —
> **~1.4–1.9× throughput + ~1.6–2.2× quota efficiency** — is a research-grounded
> projection, **not a measured result**. Do not read "live" as "proven 3×". The
> measurement protocol is in [`.claude/plans/PLAN-128/AB-PROTOCOL.md`](../.claude/plans/PLAN-128/AB-PROTOCOL.md);
> run it on a *real app project*, not on this framework.

## What auto-activates (zero-config, default-ON)

On session start you'll see a banner:

```
⚡ turbo: verify=✓ codex=a adequacy=- model=inherit  (opt out: .claude/turbo-off or CEO_TURBO=0)
```
(`verify=✓` on · `codex=a` advisory · `adequacy=-` off · `model=inherit` — subagents use
normal resolution: each agent's own `model:` frontmatter governs, omitted → main loop)

| Accelerator | Hook | Default | What it does | Kill-switch |
|---|---|---|---|---|
| After-edit verify + self-repair | `accel_dispatch.py` (PostToolUse Edit\|Write\|MultiEdit) | **ON, advisory** | runs fast syntax/lint on the changed file; feeds failures back so Claude self-repairs before you see them | `CEO_VERIFY_AFTER_EDIT=0` |
| Cross-model review detector | `codex_review_user_code.py` (Stop) | **ON, detect-only** | on a risky diff, advises `codex review --uncommitted`; only auto-runs Codex with `CEO_CODEX_USER_REVIEW_AUTO=1` | `CEO_CODEX_USER_REVIEW=0` |
| Per-agent model tiering | `CLAUDE_CODE_SUBAGENT_MODEL=inherit` (settings.env) + per-agent `model:` frontmatter | **inherit** | each subagent runs the model its definition declares (code-review/security = opus, qa/perf = sonnet, devops = haiku); cheap is **opt-in per helper**, never a global override | set `model:` on the agent, or pass `model` at spawn |
| Turbo banner / profile | `turbo_sessionstart.py` (SessionStart) | **ON** | surfaces what's active so it's never a black box | `.claude/turbo-off` or `CEO_TURBO=0` |

Hard-block modes (`CEO_VERIFY_AFTER_EDIT_BLOCK=1`, `CEO_CODEX_USER_REVIEW_BLOCK=1`) are **opt-in** —
by default nothing blocks your session on an accelerator.

> **Correction (S218):** earlier versions (S206→S217) shipped `CLAUDE_CODE_SUBAGENT_MODEL=haiku`
> as a *global* env default. Per the [Claude Code model-config docs](https://code.claude.com/docs/en/model-config)
> that env var **overrides** per-agent `model:` frontmatter and per-invocation `model` params — so it
> silently ran *every* subagent (including governance VETO rites declared as opus, and adopters'
> deliberately-declared sonnet/opus agents) on Haiku. It is now `inherit`. If you ran an older install,
> check your app's `.claude/settings.json` env and change any `CLAUDE_CODE_SUBAGENT_MODEL: "haiku"` to
> `"inherit"`. This also means any pre-S218 §7 A/B "ON" arm was confounded (cheap-model forcing was
> bundled with the accelerators, not isolated).

## What is opt-in (default-OFF — measure first)

| Accelerator | Env to enable | Why OFF by default |
|---|---|---|
| Adequacy gate (test-adequacy-for-spec) | manual in plan dir | needs the temp-copy/worktree refactor before it's safe default-on |
| Advisor executor (Haiku exec + Opus advisor, paid API) | `CEO_ADVISOR_EXEC=1` | only paid path; hard weekly cap `CEO_ADVISOR_MAX_WEEKLY_USD` (default $5) |
| Cascade router (cheap→strong escalation) | `CEO_WAVE3_CASCADE_ROUTER=1` | unmeasured; deterministic but needs an A/B week |
| Speculative draft (Haiku drafts, Opus verifies) | `CEO_SPECULATIVE=1` | stub; fails closed, no draft leak until measured |

## Prompt caching (1h TTL) — already optimal on a subscription, NOT a framework default

The SOTA-GAP map flagged "wire 1h prompt-cache TTL" as a cost win (the framework re-reads a
large, stable gate-boot prefix every turn). Verified against the [official Claude Code prompt-caching
doc](https://code.claude.com/docs/en/prompt-caching), the honest picture is:

- **On a Claude subscription (Pro/Max), the main conversation already requests the 1h TTL
  automatically — for free** (usage is included in the plan, so the longer TTL costs nothing). There
  is nothing to wire; the big gate-boot prefix already survives >5-min think/read gaps.
- **`ENABLE_PROMPT_CACHING_1H=1` is the *API-key / Bedrock / Vertex / Foundry* opt-in only** — there
  the default is the cheaper 5-min TTL and a 1h cache **write costs ~2× vs ~1.25×**, so it only pays
  off when a long, sparse session re-reads the prefix ≥3× within the hour. That is a per-token cost
  tradeoff the adopter should choose, **not** a safe framework default — so it is intentionally **not**
  set in `settings.json` or the install template. (It also needs Claude Code ≥2.1.132 to avoid a
  Bedrock/Vertex 400 that was fixed in that release.)
- **Subagents use the 5-min TTL even on a subscription** (the auto-1h applies to the main
  conversation). They are short single-task fan-outs with no >5-min internal gaps, so this is a
  non-issue in practice.

Bottom line: PLAN-131 C5-cache is a **no-op for this repo's subscription auth** and was deliberately
*not* shipped. API-key adopters who run long sparse sessions can opt in with the env var above.

## How to measure (before anyone claims a number)
After a real coding week with the defaults on: count edits, self-repairs triggered, bugs caught
pre-human-review, tokens spent, and human-review touches; compare to a control. See
[`.claude/plans/PLAN-128/AB-PROTOCOL.md`](../.claude/plans/PLAN-128/AB-PROTOCOL.md) and
[`.claude/plans/PLAN-128/measure-state.sh`](../.claude/plans/PLAN-128/measure-state.sh). New Claude-Code
GA helps here: `/usage` now breaks cost down per skill/subagent/MCP, and `OTEL_LOG_TOOL_DETAILS` exports
per-tool detail — that's the measurement substrate §7 was missing.

## Turn it all off
`echo > .claude/turbo-off` (or `export CEO_TURBO=0`) reverts to plain governed Claude Code. The governance
hooks (audit chain, canonical guards, spawn protocol) stay on — only the accelerators turn off.
