---
name: ai-llm-orchestration
description: AI system and LLM Council management for {{PROJECT_NAME}}. Covers the 3-model
  council architecture (Claude + Gemini + GPT), snapshot construction and minimization,
  prompt engineering for market analysis, usage throttling (100K tokens/day budget),
  input injection prevention, proprietary data protection, signal quality assessment,
  confidence thresholds, fallback chains, and cost optimization. Use when working on
  any code in src/ai/, reviewing AI prompts, implementing new AI features, debugging
  AI signal quality, managing LLM costs, or reviewing AI security (injection attacks,
  data leakage). 18 files, ~9.3K lines. Also use when the user mentions "AI council",
  "LLM", "market analysis AI", "AI signals", or "prediction confidence".
owner: Security Engineer (archetype)
secondary_owner: Staff Backend Engineer (API design, archetype)
---

# AI & LLM Orchestration

## Fail-Fast Rule

If an AI response cannot be parsed, validated, or is below confidence threshold,
**discard it entirely**. Never use an AI signal you cannot validate. Never
expose raw LLM output to users without sanitization. Never send proprietary
market data to LLMs without minimization.

## Architecture

```
Market Snapshot (engine state)
  → Snapshot Minimizer (reduce to essential data)
    → AI Council (3 models in parallel)
      ├── Claude (Anthropic)
      ├── Gemini (Google)
      └── GPT (OpenAI)
    → Response Aggregator (voting, confidence)
      → Signal (BUY/SELL/HOLD with confidence)
        → Usage Limiter (daily budget check)
```

### Key modules (archetype — adapt filenames to your stack)

Every project adopting the AI Council pattern should own these responsibilities, usually one module per responsibility:

- **AI orchestration service** — main entry point; receives a task, decides which model(s) to call, applies rate limits, returns the aggregated response.
- **AI council** — multi-model voting and aggregation logic; decides how to combine outputs from 2+ models (majority vote, confidence-weighted, quorum).
- **AI client adapters** — one per provider (Anthropic, OpenAI, Google, etc.). Wraps the SDK, handles retries, normalizes errors.
- **Snapshot builder** — constructs the minimized context payload the LLM will see. Strips PII, aggregates raw data, caps size.
- **Minimizer** — strategy layer on top of the snapshot builder. Implements data-reduction heuristics (drop low-signal fields, summarize, dedup).
- **Input guard** — injection prevention; runs every user-provided string through pattern matchers before it reaches the prompt.
- **Usage limiter** — token-budget enforcement; per-user, per-tier, per-day caps; short-circuits before expensive calls when over budget.
- **Prompt templates** — versioned, testable prompt bodies. Kept separate from code so prompt iteration doesn't require a deploy.

## Security Rules (CRITICAL)

### Data Minimization
- NEVER send full raw datasets to LLMs — only aggregated metrics
- NEVER send user credentials or API keys in prompts
- NEVER include PII (user emails, IPs) in snapshots
- Minimize to: the minimal aggregated signals the LLM actually needs for its task

### Injection Prevention
- ALL user-provided text must pass ai-input-guard before inclusion in prompts
- Guard checks for: prompt injection, jailbreak patterns, system prompt override
- If guard fails → reject input, log attempt, do NOT send to LLM

### Output Sanitization
- Parse LLM output as structured JSON, not raw text
- Validate schema before using
- Reject if confidence < threshold
- Never display raw LLM text to users (XSS risk)

## Usage Management

### Token Budget
- Daily budget: configurable via env (default 100K tokens/day)
- Per-request tracking: input tokens + output tokens
- Budget exhausted → graceful degradation (cached signals, no new queries)
- Cost allocation: track per-model costs for optimization

### Fallback Chain
1. Try primary model (Claude)
2. If timeout/error → try secondary (Gemini)
3. If both fail → try tertiary (GPT)
4. If all fail → return cached signal with staleness warning
5. Never retry same model more than 2x

## Council Voting

### Consensus Algorithm
- 3 models produce independent signals
- If 2/3 agree → use majority signal with averaged confidence
- If 3-way disagreement → return HOLD with low confidence
- Confidence = weighted average (weights per model based on historical accuracy)

## Prompt Engineering Rules

1. Prompts must be version-controlled (in ai-prompts.ts, not inline)
2. Every prompt must have: system instruction, data section, output format
3. Output format must be parseable JSON schema
4. Temperature should be low (0.1-0.3) for financial analysis
5. Never ask LLM to "be creative" with market data
## Adopter Note — Stale Metric + Domain Framing (PLAN-044 P0-12)

The frontmatter description names `src/ai/` and `18 files,
~9.3K lines` — both are originating-project metrics from the
`ceo-orchestration` dogfood corpus circa 2025-Q1 and should not
be treated as normative for your adopter codebase.

Likewise, the Fail-Fast Rule's mention of `proprietary market
data` and the final-section mention of `financial analysis` /
`market data` bias the rubric toward fintech. The **patterns**
(multi-model council, snapshot minimisation, injection guard,
usage-limiter short-circuit, prompt templates kept out of the
deploy path, confidence-threshold gating) apply to any LLM-in-
the-loop system regardless of domain.

If your project is not finance-adjacent, replace
"market data" / "signal" with your own domain nouns when
spawning an archetype that loads this skill. File-count and
line-count figures are nominal; what matters is that the seven
responsibilities in §Key modules each live in a dedicated
module, not the absolute count.
