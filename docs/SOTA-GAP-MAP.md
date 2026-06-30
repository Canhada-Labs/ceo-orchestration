# ceo-orchestration → SOTA Autonomous Coding Framework: Gap Map, Maturity Stage & Roadmap

> **SUPERSEDED 2026-06-20.** The headline gap this document describes —
> the coding accelerators sitting **unwired** ("0/3 wired", "~30% of the
> way to SOTA") — is no longer current. Those accelerators have since
> been wired; the body below is preserved only as a historical snapshot
> of the gap analysis, not the present state.
>
> **For the current state, do NOT trust the numbers in this file.** Read
> instead:
>
> - `docs/READINESS-STATUS.md` — current adoption verdict.
> - `docs/ACCELERATORS.md` — what is actually wired today, with the
>   `settings.json` registrations that prove it.
>
> The diagnosis (what SOTA looks like, which levers matter, the dead
> ends) remains useful reading; the **status column is stale.**

> Goal (Owner S205): a **zero-config, default-on** framework that turbocharges a vibe coder 2-10× —
> quality + velocity + governance + security — extracting the maximum from **Claude + Codex** WITHOUT
> inflating cost (ideally **cheaper via intelligence**). The novice toggles nothing; the expert can opt out.

## 0. Where we are — the honest stage

| Dimension | Stage | Reality |
|---|---|---|
| Governance / security / audit | **Mature (2-3/3)** | 33 hooks, tamper-evident audit, canonical guards, spawn protocol — over-built |
| **Cost / intelligence routing** | **0/3 — absent** | No model routing exists. Doctrine prose only (`llm-routing-and-finops` is an *operating manual*, no code). Vibe coder pays Opus price for everything. |
| **Autonomous quality (your code)** | **0-1/3** | NO hook runs the project's tests/lint after edits. Codex pair-rail only guards the *framework's own files*, fail-opens without the `codex` CLI. Zero review value on adopter app code. |
| **Zero-config autonomy** | **0-1/3** | Plan mode / effort / caching: none configured. RAG: unreachable (needs 200K-LoC + a hand-started daemon). Swarm + autonomous-loop: default-OFF, no live entrypoint. Everything smart is human-invoked (`/ceo-boot`, `/spawn`, `/debate`). |
| **Latency / overhead** | **Negative** | ~0.3-1.0s added per edit cold-starting 7-10 Python interpreters, mostly to write audit breadcrumbs. |

**Net:** ~30% of the way to SOTA. We maxed the hard-to-copy half (governance) and left the GA, cheap,
high-impact half (the coding accelerators) **unwired**. The remaining 70% is mostly **wiring GA features**,
not research — which is the good news.

## 1. The SOTA reference (12 capabilities, almost all GA today on Max + Codex + API key)

| # | SOTA capability | Mechanism | Status | We have it? |
|---|---|---|---|---|
| 1 | **Prompt-caching discipline** | stable prefix, ≤4 breakpoints, **1h TTL** (5-min default silently +30-60%); $168→$21 on long sessions | GA | ⚠ auto-on, **no 1h-TTL policy / no discipline** |
| 2 | **Effort routing** | `low` subagents/bulk, `xhigh` hard coding — dominant cost knob on a subscription | GA | ❌ none (only `/effort` manual) |
| 3 | **Model routing / cascade** | Haiku/Sonnet bulk → Opus hard; RouteLLM/FrugalGPT = **85% cut at 95% quality** | GA / OSS | ❌ none |
| 4 | **Advisor tool** | Haiku executor + Opus advisor, 1 call — ~11% under all-Opus *with equal/better quality* | GA (API) | ❌ not wired; **untested if your key is enabled** |
| 5 | **Plan mode default** | tool-enforced read-before-write; spec→plan→implement→validate | GA | ❌ not defaulted |
| 6 | **Test-gated edits + self-repair** | PostToolUse hook runs tests/lint after every edit; failures self-correct, **deterministic, $0** | GA | ❌ **missing** (the single biggest quality gap) |
| 7 | **Cross-model Codex review** | Claude writes, **Codex (GPT-5.5) reviews** — official `codex-plugin-cc` `/codex:review` | GA | ⚠ pair-rail exists but only on framework files, not your code |
| 8 | **Auto review-loop until APPROVED** | Stop-hook auto-launches Codex review on session exit (can't forget); loop to APPROVED | GA (plugin) | ❌ none |
| 9 | **Isolated Haiku subagents** | Explore/Plan read-only on Haiku — parallel READS, context isolation (the *real* multi-agent) | GA | ⚠ subagents used, **not routed to Haiku** |
| 10 | **Checkpoints / rewind** | auto file-snapshot before edits; Esc-Esc rewind; plans survive compaction | GA | ⚠ native, not leveraged in doctrine |
| 11 | **Persistent memory + CLAUDE.md** | facts across sessions | GA | ✅ have it |
| 12 | **Tamper-evident audit** | auditable agent actions (the one durable differentiator) | — | ✅ **over-built — our moat** |

**Cost truth:** wiring #1-#4 + #6 + #9 makes the framework MORE capable AND **cheaper** (caching 60-90% +
Haiku-for-bulk + effort routing + advisor). That IS "economizar pela inteligência." Today: 0% wired.

**Dead ends (confirmed, do NOT build):** parallel multi-agent *writer* swarms (DPI proof arXiv 2604.02460:
single ≥ multi at equal budget; 58-285% token overhead) · speed as the value prop · self-review by the
writer · `budget_tokens` (deprecated) · the L2 review-loop default `--dangerously-bypass-...` flag.

## 2. The top gaps (current → SOTA), prioritized by leverage

1. **No cost routing** → wire Haiku-for-bulk/subagents + effort routing + caching 1h-TTL discipline. *Biggest cost win, $0 risk.*
2. **No test/lint-after-edit** → add a PostToolUse hook that auto-detects + runs the project's tests/linter; failures self-repair. *Biggest quality win.*
3. **Codex review doesn't see your code** → re-scope the pair-rail (or add the official `codex-plugin-cc`) to review the adopter's diff, default-on, with a graceful no-Codex fallback. *Biggest "no bugs" win.*
4. **Nothing is default-on / autonomous** → a zero-config profile that turns the loop ON; a first-run that needs no flags.
5. **Plan-mode / effort / thinking not defaulted** → ship SOTA defaults.
6. **RAG unreachable** → either make it actually work for normal repos (retrieval over the codebase) or stop claiming it.
7. **Latency tax** → consolidate the 7-10 per-edit interpreter spawns into one warm dispatcher (or trim advisory hooks for the vibe-coder profile).
8. **The advisor tool untested** → verify your API key has it; if yes, it's the marquee cost-quality lever.

## 3. Roadmap (3 waves; Wave 1 is mostly config = days, not research)

**WAVE 1 — "Turn the engine on" (zero-config cost + quality, low risk, highest impact):**
- Caching 1h-TTL + prefix discipline (settings/doctrine).
- Model routing: per-agent `model:` frontmatter (code-review/security = opus, qa/perf = sonnet,
  devops = haiku) + effort defaults (low subagents / high coding). **NOT** a global
  `CLAUDE_CODE_SUBAGENT_MODEL=haiku` — that env var overrides explicit `model:` and silently
  downgrades governance rites + adopter work (removed S218; see ACCELERATORS.md §Correction).
- **PostToolUse test+lint hook** (auto-detect stack: pytest/vitest/go test/cargo; self-repair on fail).
- **Codex review on the adopter diff** (re-scope pair-rail or install `codex-plugin-cc`), default-on + no-Codex fallback.
- Plan-mode default for non-trivial tasks.
- A `vibe`/turbo profile that bundles all of the above ON.

**WAVE 2 — "Make it autonomous & novice-proof":**
- Zero-config default-on profile (governance stays, accelerators ON, expert opt-out via one flag).
- Kill the latency tax (warm hook dispatcher / consolidate).
- Auto review-loop (Stop-hook → Codex until APPROVED, sandboxed read-only).
- First-run that needs no commands; `/ceo-boot` auto-runs.

**WAVE 3 — "Frontier cost-via-intelligence":**
- Advisor tool wired (if key enabled).
- Cascade routing (RouteLLM/FrugalGPT) — cheap-first, escalate-on-low-confidence.
- RAG-for-real (codebase retrieval on normal repos) or honest deprecation.
- Agent-level speculative draft-then-verify (Haiku drafts the edit, Opus verifies the diff).

## 4. The reframe that makes this SOTA
Sell **governance + auto-quality + cost-via-intelligence, default-on, zero-config** — NOT speed-by-
orchestration (dead, proven 9×). The orchestration that helps = **parallel reads + driver/worker (Claude
writes, Codex reviews) + test-gated self-repair**. Everything load-bearing is GA. The framework's net-new
value = wiring these into a zero-config, governed, auditable default that a non-expert gets for free.
