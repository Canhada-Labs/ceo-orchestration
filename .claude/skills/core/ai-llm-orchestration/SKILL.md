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
inspired_by:
  - source: msitarzewski/agency-agents/specialized/specialized-model-qa.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-06
# --- smart-loading fields (PLAN-083 Wave 0a sub-agent 0.7a) ---
domain: core
priority: 5
risk_class: medium
stack: [python, typescript]
context_budget_tokens: 1150
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 6}
  engine: {active: true, priority: 4}
  fintech: {active: true, priority: 6}
  trading-readonly: {active: true, priority: 8}
  generic: {active: true, priority: 5}
activation_triggers:
  - {event: help-me-invoked, regex: "(?i)llm|orchestrat|agent.?graph"}
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

## Multi-SDK Matrix (official Anthropic SDKs — PLAN-135 K7)

The **AI client adapters** responsibility (§Key modules) is where the SDK
choice lands. Seven official SDKs cover the mainstream stacks, and the
same doctrine applies to all of them: **never hand-write the agentic
loop**. Every official SDK ships a tool runner that owns the
call→execute→feed-back loop; use it, with `max_iterations` as the
bounded-loop guard so a confused model cannot spin the adapter forever,
and tool-call interception as the verification gate (the API-side
equivalent of this framework's pre-tool hooks). Where the SDK exposes a
middleware layer, that layer is the SANCTIONED audit/cost/redaction
point — the API-side mirror of the hooks philosophy. Two SDKs (Ruby,
PHP) have NO middleware layer; they are flagged in the table and need
the adapter-layer wrap described below.

| SDK | Install (official package) | Streaming helper | Tool runner (beta — never hand-write the loop; bound it with `max_iterations`) | Middleware (sanctioned audit/cost/redaction point) |
|---|---|---|---|---|
| Python | `pip install anthropic` | `client.messages.stream()` → `.get_final_message()` | `@beta_tool` + `client.beta.messages.tool_runner()` | YES — registered on the client (e.g. `BetaRefusalFallbackMiddleware`) |
| TypeScript | `npm install @anthropic-ai/sdk` | `client.messages.stream()` → `.finalMessage()` | `betaZodTool` (Zod schemas) + tool runner | YES — client `middleware: [...]` array |
| Java | Maven/Gradle (`com.anthropic.*`) | YES — SDK streaming helper | YES — beta tool use with annotated classes | YES — see the SDK repo `examples/` for the exact binding |
| Go | `go get github.com/anthropics/anthropic-sdk-go` | YES — SDK streaming helper | `BetaToolRunner` (`toolrunner` package) | YES — `option.WithMiddleware(...)` |
| C# | NuGet — ⚠ the NuGet `Anthropic` package at ≤3.x is a COMMUNITY SDK, not the official one; verify before adopting | YES — SDK streaming helper | `BetaToolRunner` + raw JSON schema | YES — client `Handlers = [...]` |
| Ruby | `gem install anthropic` | YES — SDK streaming helper | `BaseTool` + `tool_runner` (beta) | **ABSENT** — no sanctioned interception point; wrap at the adapter layer |
| PHP | `composer require anthropic-ai/sdk` | ⚠ a PSR-18 client without Guzzle silently BUFFERS streaming — responses arrive all-at-once with no error | `BetaRunnableTool` + `toolRunner()` (beta) | **ABSENT** — no sanctioned interception point; wrap at the adapter layer |

### Doctrine around the matrix

- **Tool runner over hand-rolled loop.** The manual agentic loop is
  allowed ONLY when you need human-in-the-loop approval or conditional
  tool execution the runner cannot express — and then it must still
  carry an explicit iteration cap. An unbounded `while True:` around
  `messages.create()` fails code review.
- **Middleware is where governance lives API-side.** Token accounting
  (§Usage Management), per-call cost envelopes (§LLM FinOps Discipline),
  audit logging, and snapshot redaction belong in the SDK middleware
  layer, not scattered through call sites. The SDKs also ship a built-in
  refusal-fallback middleware — adopt it deliberately and log every
  fallback switch into the audit envelope, never silently.
- **Ruby/PHP gap.** With no middleware layer, the AI client adapter
  (§Key modules) is the compensating control: ALL calls go through one
  owned wrapper that enforces the usage limiter, budget envelope, and
  audit emit before/after the SDK call. Direct SDK calls from feature
  code are forbidden in these two stacks.
- **OpenAI-compat endpoint footgun.** The OpenAI-compatibility surface
  silently ignores parameters it does not support — a run that "works"
  may not be exercising the configuration you specified. That makes it
  UNFIT for governance-grade model comparison (§Replication discipline
  pins exact model + SDK + flags for a reason). Use the official SDK
  against the native API for any output that feeds an audit or a
  council vote.
- **Server-side tools map to local analogs.** Before adopting a
  server-side tool (code execution, web search/fetch), name its
  locally-governed analog and apply the same trust boundary: server-side
  execution happens outside the local hook rail, so its outputs enter
  the pipeline as untrusted input, like any LLM output.
- **Off-subscription overflow lanes.** Amazon Bedrock, Google Vertex AI,
  and Microsoft Foundry serve the same Messages API shape and act as
  overflow lanes when the weekly subscription quota saturates (feature
  subset differs — no Managed Agents or Anthropic server-side tools
  there). Routing policy and economics are owned by PLAN-134 W3; no
  cost claims are made here.
- **Community-package warnings (load-bearing).** The NuGet `Anthropic`
  ≤3.x community-SDK trap and the PHP no-Guzzle silent-buffering trap
  are flagged in the table above; community provider shims (e.g. the
  community Vercel-AI provider) are an unaudited subscription-drain
  vector — none of them carry the middleware/audit surface this skill
  requires. Catalog rows for these land in `pitfalls-catalog.yaml`
  (PLAN-135 W3 D10+K7/K8 batch).

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

## Independent LLM Output Audit

The Council pattern produces a signal. That signal is a claim. Auditing
that claim is a separate discipline from producing it, and the auditor
must NEVER be the same agent that authored the prompt or the aggregator.
Treat every model output as guilty until evidence shows otherwise.

> **REDUCE-side companion:** when this audit runs over many fan-out shards, follow the evidence-bound REDUCE protocol in `docs/triage-reduce-protocol.md` (ADR-141) — no evidence-free accept/drop; security/canonical findings get an independent cross-rail review.

### Replication discipline

Re-running the same prompt against the same model with `temperature=0`
and `top_p=1` should produce a deterministic-ish output within a small
edit-distance band. When it does not, the prompt is itself unstable and
the downstream signal cannot be trusted regardless of how confident the
model sounds.

- Pin the **exact** model identifier (e.g. `claude-opus-4-7`, not
  `claude-3-opus`); aliases drift silently across provider releases.
- Pin SDK version, base URL, and any provider-side feature flag (cache
  control, JSON mode, tool-use mode).
- Re-run a calibration set of N=20 representative prompts on every
  model-version bump. If output divergence on the calibration set
  exceeds the documented tolerance, FREEZE rollout until the prompt
  templates are re-tuned.
- Store every prompt-output pair with its run-id in a replay store; an
  output that cannot be replayed cannot be audited.

### Calibration testing — the "I don't know" requirement

A well-behaved LLM signal must abstain when the input is out of
distribution. Pre-bake at least three abstention probes into the
calibration set:

- **Empty-context probe**: send the prompt with the data section
  blanked. The model MUST refuse or return null-confidence; if it
  returns a confident signal, the prompt is leaking instructions that
  let the model fabricate.
- **Adversarial-noise probe**: feed deliberately corrupted snapshot
  data (NaN values, future dates, label noise). Expected output is
  abstain or low-confidence; a high-confidence signal here is a
  fabrication signal.
- **Consensus-disagreement probe**: feed the SAME prompt 3+ times with
  the same seed; high inter-run variance with high per-run confidence
  is the classic over-confident hallucination shape.

Track abstention rate as a first-class metric alongside accuracy.
A model that never abstains on the abstention probes is mis-calibrated
and ships unsafe.

### Interpretability checkpoints

A council vote that cannot be inspected by a human is not a vote, it is
a black box that happens to have three faces. Every signal that exits
the aggregator must carry:

- The redacted snapshot fingerprint (SHA256 of the minimized payload)
- The per-model raw outputs (hashed if size matters, raw if not)
- The aggregation rule applied (majority, weighted, quorum, override)
- The confidence math (which weights, which threshold, which floor)

CORRECT — auditable signal envelope:

```json
{
  "signal": "BUY",
  "confidence": 0.72,
  "snapshot_sha256": "9c1f...e0a2",
  "council_outputs": [
    {"model": "claude-opus-4-7", "verdict": "BUY", "raw_conf": 0.81},
    {"model": "gemini-1.5-pro",  "verdict": "BUY", "raw_conf": 0.68},
    {"model": "gpt-4-turbo",     "verdict": "HOLD", "raw_conf": 0.55}
  ],
  "aggregation_rule": "majority_with_weighted_avg",
  "weights": {"claude-opus-4-7": 0.45, "gemini-1.5-pro": 0.30, "gpt-4-turbo": 0.25},
  "threshold": 0.65,
  "run_id": "ai-run-2026-05-06-14-22-007"
}
```

WRONG — opaque signal:

```json
{ "signal": "BUY", "confidence": 0.72 }
```

The opaque form cannot be audited, replayed, or rolled back. NEVER ship
it to a downstream consumer.

### Audit-grade finding template

When the auditor flags a defect, the finding MUST be evidence-shaped, not
opinion-shaped. The four required fields:

| Field | Definition |
|---|---|
| **Observation** | What was measured (run_id, prompt hash, abstention rate, divergence pp). |
| **Evidence** | The replay artifact + the metric breach (e.g. "abstention rate 4% on noise probes; floor 30%"). |
| **Impact** | Quantified user-facing effect (e.g. "12% of /signals responses inherit the miscalibration"). |
| **Remediation** | The specific change required (prompt edit, weight rebalance, model swap, abstention floor raise) with an owner and a deadline. |

A finding without all four fields is a complaint, not an audit.
Complaints are not actionable; reject them at intake.

## LLM Output Reliability Patterns

The reliability layer is what stands between a fluent-sounding hallucination
and a production-grade signal. Five patterns are mandatory; the rest are
local optimizations.

### 1. Schema-pinned output

Use the provider's structured-output mode (JSON mode, tool-use mode, or
function-calling) to force the response into a known shape. Then validate
the parsed output against a JSON Schema before any consumer sees it.

- Prefer schema-validated structured output over `regex`-then-parse.
- The schema is checked into version control next to the prompt.
- Validation failure → discard the response, increment a metric, and
  fall through the fallback chain. NEVER patch the response with
  defaults.

CORRECT — schema-pinned with strict mode:

```python
schema = {
    "type": "object",
    "properties": {
        "signal":     {"type": "string", "enum": ["BUY", "SELL", "HOLD"]},
        "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "rationale":  {"type": "string", "maxLength": 280},
    },
    "required": ["signal", "confidence", "rationale"],
    "additionalProperties": False,
}
```

WRONG — best-effort string parse:

```python
verdict = re.search(r"(BUY|SELL|HOLD)", llm_text).group(1)  # bad
conf    = float(re.search(r"(\d\.\d+)", llm_text).group(1))  # worse
```

The bad form silently picks up the first regex match, even if the model
emitted a paragraph contradicting itself; the worse form blows up on any
output the regex-author did not anticipate.

### 2. Verifiable-claim discipline

Any factual claim in the LLM output must come with a citation back to
the snapshot it consumed. The aggregator drops claims with no citation;
the consumer drops outputs with no claims.

- Require an array of `{claim, snapshot_field, snapshot_value}` triples
  in the response schema.
- Cross-check each `snapshot_value` against the actual minimized
  snapshot before accepting the signal. Mismatch = fabrication = drop.
- Track citation-coverage as a metric. A council whose citation coverage
  trends down is a council that is increasingly fabricating.

### 3. Self-consistency check (sample-and-vote)

For any high-stakes signal, sample N independent runs from the same
model with non-zero temperature and take the majority verdict. Keep the
sample size proportional to stake:

| Stake | Sample size | Decision rule |
|---|---|---|
| Tier-1 (irreversible writes / paying tenant)   | N=5  | 4-of-5 agree, else abstain |
| Tier-2 (reversible writes / suggestion UI)     | N=3  | 2-of-3 agree, else abstain |
| Tier-3 (read-only / advisory)                  | N=1  | accept if schema-valid |

Sample-and-vote is independent of the cross-model council; both layers
combine multiplicatively to suppress hallucinations.

### 4. Edge-case fixture suite

The reliability suite is a **regression test suite for the prompt**, not
the application. Pin three families of fixtures and run them on every
prompt edit, every model bump, and on a daily cron:

- **OWASP LLM01 — prompt-injection probes**: classic ignore-prior-
  instruction strings, indirect injection via embedded user content,
  payload hidden inside fields the snapshot builder forwards.
- **OWASP LLM06 — sensitive-info-disclosure probes**: dummy "secret"
  strings seeded into the snapshot's redaction-allowlist negative
  cases. The prompt MUST NOT leak them in the rationale.
- **OWASP LLM07 — jailbreak probes**: persona-swap, role-confusion,
  policy-override, base64-laundered instruction strings.

Fixture failures are CRITICAL by default. Treat the suite the way you
treat the application's test suite: red = no deploy.

### 5. Output-grounding floor

A grounding floor is the minimum citation count, the minimum schema
field count, and the maximum "free prose" length the consumer accepts
from the LLM. Outputs that fall below the floor are dropped before they
reach a user.

- Default floors: ≥1 citation per claim; ≥3 schema fields populated;
  ≤280 chars of free prose per response.
- Floors are configurable per surface; they are NEVER configurable to
  zero. A surface with a zero-floor configuration FAILS validation.

## LLM FinOps Discipline

Cost is part of the contract. A council that is technically correct and
financially unbounded is broken. The FinOps layer enforces budgets at
the call site, routes spend to the cheapest sufficient model, and surfaces
leakage early.

### Per-task budget envelope

Every dispatch sits inside a budget envelope before the first token is
sent. The envelope encodes:

- `max_input_tokens` (cap the snapshot size)
- `max_output_tokens` (cap the response)
- `max_usd_per_call` (computed from per-model rate cards)
- `max_calls_per_request` (cap retries + sample-and-vote size)

A call that would breach any of the four caps short-circuits BEFORE
invoking the provider. The short-circuit returns the cached fallback
signal with a `budget_exhausted` flag set on the envelope.

CORRECT — envelope check at the dispatch boundary:

```python
def dispatch(task: Task) -> Signal:
    env = build_envelope(task)              # caps + projected cost
    if env.projected_usd > env.max_usd_per_call:
        return fallback_signal(reason="budget_envelope_breach")
    return _call_provider(task, env)
```

WRONG — best-effort cost accounting AFTER the call:

```python
result = _call_provider(task)               # already paid for it
spent  = result.tokens * RATE
log.info(f"spent {spent}")                  # post-hoc accounting only
```

The wrong form learns about cost overruns by reading the bill at the
end of the month.

### Model-size routing rules

Different tasks deserve different price points. Route mechanically by
task class, NEVER by author preference:

| Task class | Default model | Escalation trigger |
|---|---|---|
| Classify / extract / format-coerce          | small (e.g. Haiku tier)  | escalate to mid only on schema-validation miss |
| Reasoning / multi-step / with tool-use      | mid (e.g. Sonnet tier)   | escalate to large only on confidence-floor miss |
| Adversarial / VETO-floor / financial / PHI  | large (e.g. Opus tier)   | NEVER de-escalate; ADR-052 floor |
| Inter-model adversarial review              | large + cross-vendor     | NEVER same-vendor only; ADR-058 floor |

Escalation is one-directional during a single dispatch (small → mid →
large). De-escalation across dispatches is allowed only when the smaller
model has been benchmarked at parity on the relevant fixture suite.

### Cache hit-rate as a first-class metric

Provider-side prompt caching is the single biggest cost lever in
production. Treat cache hit rate as an SLO:

- **Target**: ≥70% cache hit rate on the prompt prefix across a 24h
  window for steady-state traffic.
- **Reality check**: hit rate <40% means the prompt is being rebuilt
  every call; the snapshot builder is probably non-deterministic on
  field ordering, timestamps, or whitespace. Audit the builder, not
  the prompt.
- **Cache invalidation discipline**: bumping the prompt template or
  the snapshot schema invalidates the cache; budget for the cold-cache
  call surge during the rollout window of any prompt change.

### Token-leakage diagnostics

Token leakage is the FinOps equivalent of a memory leak: the bill grows
without the user-visible workload growing. The four classic shapes:

| Leak shape | Symptom | Fix |
|---|---|---|
| **Snapshot bloat**     | input_tokens trending up week-over-week with flat user count        | re-tune the minimizer; add a `max_payload_kb` invariant test |
| **Retry storm**        | call count >> request count; same prompt-hash repeated within ms     | exponential backoff with jitter; cap retries at 2; circuit-break on provider 429s |
| **Verbose response**   | output_tokens variance is high; rationale field hits the prose cap   | tighten the schema's `maxLength`; reject responses over the floor |
| **Sampling overshoot** | sample-and-vote N exceeds the tier table for low-stakes calls        | route by stake (Tier-1/2/3); audit any caller passing N manually |

Run a weekly FinOps review that diffs `input_tokens` / `output_tokens` /
`call_count` / `usd_spend` per route against the previous 4-week
trailing baseline. Drift exceeding 25% on any axis is a P2; drift
exceeding 100% is a P0 leak investigation.

### Anti-patterns to reject

- **"Premium model for everything because quality"** — collapses the
  routing table; turns the bill into a step function on every traffic
  spike. Route by stake, not by sentiment.
- **"We'll add caching later"** — caching is the difference between
  steady-state economics and a one-shot demo. Build it on day one.
- **"The provider gave us free credits, ship without budgets"** — free
  credits expire; the codebase that ignored budgets does not.
- **"The cost dashboard is for finance, not engineering"** — DO NOT
  hand off the bill to a non-engineer. Cost is a code-review item
  alongside correctness and security.

## Council Output Findings & Reporting

When the auditor produces a verdict on a council run, the verdict goes
into a structured artifact. Free-form prose is not a verdict. The
artifact is consumed by the post-incident review process when a signal
turns out to be wrong, and by the change-review process when a prompt
or model is being rolled out.

### Verdict bands

Every council audit closes on one of four verdicts. The band is set by
the most severe finding present, not by the count of findings.

| Verdict | Meaning | Rollout effect |
|---|---|---|
| **SOUND**            | All checks pass; calibration on-floor; no fabrications. | Approved for the target surface tier. |
| **SOUND-WITH-NOTES** | Minor findings; remediation tracked but non-blocking.   | Approved with watch-items in the next review. |
| **CONDITIONAL**      | Material weakness on at least one mandatory check.      | Restricted to lower-stakes surface tiers until remediated. |
| **UNSOUND**          | Calibration breach OR fabrication OR injection escape.  | DO NOT ship; revert to last SOUND configuration. |

A CONDITIONAL verdict is NOT a downgrade-this-run pathway; it is a
hard gate against the higher-stakes surface tiers until the remediation
ships and a fresh audit re-rates the configuration.

### Required report sections

The audit artifact lives at `.claude/plans/<PLAN-NNN>/llm-audit-<YYYY-MM-DD>.md`
or the equivalent path in your adopter project. Every section is
mandatory; missing sections fail intake.

```markdown
# LLM Council Audit — <surface> — <YYYY-MM-DD>

- **Verdict:** SOUND / SOUND-WITH-NOTES / CONDITIONAL / UNSOUND
- **Council configuration:** <model-ids + weights + aggregation rule>
- **Calibration set:** <N prompts, abstention rate, divergence pp>
- **Run window:** <start UTC> → <end UTC>
- **Run count:** <total dispatches audited>

## Findings
| # | Severity | Domain         | Observation | Evidence | Impact | Remediation | Owner | Due |
|---|----------|----------------|-------------|----------|--------|-------------|-------|-----|
| 1 | …        | calibration    | …           | …        | …      | …           | …     | …   |
| 2 | …        | injection      | …           | …        | …      | …           | …     | …   |
| 3 | …        | finops         | …           | …        | …      | …           | …     | …   |

## Replay coverage
<which percentage of the audited runs are replayable from the replay store>

## Citation coverage
<percentage of signals carrying ≥1 citation per claim>

## Cache hit rate
<observed hit rate on the audited window vs. the SLO target>

## Cost envelope
<observed USD per 1K dispatches vs. the budget envelope>

## What we got right
<the patterns to keep — recorded for the next audit's baseline>
```

### Cross-validation with other disciplines

- **Code review** — prompt edits and aggregator changes follow
  `core/code-review-checklist`; the LLM audit sits AFTER code review,
  not instead of it. A code-review pass that lands a prompt change
  triggers a fresh calibration run before the change is rolled to the
  higher-stakes surface tiers.
- **Incident management** — an UNSOUND verdict on a live surface is a
  SEV-band trigger via `core/incident-management`; the IC owns the
  rollback decision, the auditor owns the verdict.
- **Security review** — injection and sensitive-info findings escalate
  to the security archetype per `core/security-and-auth` (ADR-052
  VETO floor); the LLM auditor does not unilaterally close those
  findings.
- **Release gate (planned, not yet wired)** — once PLAN-074 Wave 12
  ships, the release.yml pipeline WILL read the most recent audit
  verdict for the affected surface before tagging GA, and an
  UNSOUND verdict WILL require re-audit before re-tagging. Until
  Wave 12 lands, the audit verdict is consulted manually by the
  auditor + release reviewer at GA time. The framework's general
  24h Codex re-pass window per ADR-103 is orthogonal to the LLM
  audit gate.

### Anti-patterns to reject

- **"It worked on the demo, ship it"** — demo runs are not audited
  runs; the demo's prompt was hand-tuned on three inputs. The audit
  exists because the demo is not the population.
- **"The model is creative, audit findings are subjective"** — the
  audit checks calibration, citation coverage, schema validity, and
  injection resistance. None of those are subjective.
- **"We'll audit after launch"** — launching an unaudited LLM surface
  is launching with the safeguards intentionally removed. The audit
  predicates the launch, never trails it.
- **"The bill is fine, no need for the FinOps section"** — FinOps
  drift is the leading indicator for a regressed prompt. Skipping the
  section is skipping the leading indicator.

## Ranking/Feed Pipeline Shape — folded from `recsys-pipeline-architect` (PLAN-157 W1)

When the task is "pick the top K items for a (user, context)" — RAG retrieval
reranking, notification/task prioritisation, feed or search ranking — the
plumbing around the scoring function follows six composable stages, in fixed
order (distilled from the sunset architecture squad's
`recsys-pipeline-architect` skill; full text in git history):

| # | Stage | Job | Concurrency |
|---|---|---|---|
| 1 | Source | retrieve candidates from one or more origins | parallel fan-out |
| 2 | Hydrator | attach the metadata later stages need | parallel |
| 3 | Filter | drop what must never be shown | sequential |
| 4 | Scorer | score survivors — a chain, not one scorer | sequential |
| 5 | Selector | sort by final score, take top K | single op |
| 6 | SideEffect | cache served ids, log, emit events | async — never blocks |

Why the order is fixed: source before hydrate (know the candidates before
paying to enrich them); hydrate before filter (filters need attributes the
source did not return); filter before score (scoring is the expensive stage);
select after score (keeps scoring deterministic and cacheable); side effects
last and async (bookkeeping never sits in the latency path).

Trade-offs to surface explicitly — never default silently: **single relevance
score vs multi-action prediction** (predict P(action) per action and combine
with serving-time weights — re-tune without retraining; weights can be
negative); **candidate isolation vs joint scoring** (isolated = deterministic
and cacheable, the default; joint only with a specific reason such as
batch-aware diversity); **online vs offline vs hybrid serving** (online
~100-300 ms budget is the default; hybrid = retrieve offline, rank online).

Hard rules: never invent benchmark numbers ("it depends; measure it");
filter order is load-bearing — cheap/universal before expensive/personal;
side effects are fire-and-forget; scaffolds must actually run, no pseudocode.
Attribute the pattern honestly: the six-stage shape was popularised by the
open-sourced "For You" ranking algorithm (Apache-2.0); no trademark or brand
borrowing — use neutral names ("candidate pipeline", "ranking pipeline").
