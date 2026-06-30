# Anthropic Cookbook patterns — framework consumption catalogue

<!--
pattern_ids:
  - COOK-P1   # Structured output / JSON mode
  - COOK-P2   # Chain-of-Verification (CoVe)
  - COOK-P3   # Citations API
  - COOK-P4   # Message Batches API

Wave A.0 / AC1b bijection (PLAN-092 S121): these stable IDs are the
canonical reference across 3 surfaces — this file, .claude/data/
cookbook_patterns.json, and .claude/skills/core/cookbook-advisor/
SKILL.md. Bijection AC1b enforced by tests/test_cookbook_advisor_hook.py.
-->

> **Status:** docs-only foundation (PLAN-087 Wave G).
> **Pattern IDs:** `COOK-P1` (Structured output) / `COOK-P2` (CoVe) /
> `COOK-P3` (Citations API) / `COOK-P4` (Message Batches API).
> **Purpose:** inventory the 4 Anthropic Cookbook 2026 patterns that
> the framework intends to consume, with forward-links to the plans
> that will wire them. **No SDK code lands in PLAN-087** — this file
> is a pattern catalogue so PLAN-088+ has a stable foundation to
> implement against.
>
> Each pattern follows the same template:
>
> 1. **Intent** — one paragraph: what problem the pattern solves +
>    when to reach for it.
> 2. **Canonical Anthropic SDK invocation** — minimal code snippet
>    taken from the upstream Cookbook (not framework code).
> 3. **Framework consumption** — one paragraph: how the framework
>    intends to wire this in, with the implementing plan link.

Inventoried in `PLAN-084` Wave B.8 (`findings-master.jsonl` cluster
R-021..R-025). All four are docs-only foundations until the linked
plans land.

---

## Pattern 1 — Structured output / JSON mode (COOK-P1)

### Intent

LLM responses for downstream automation must be parseable. Free-form
text introduces a parsing risk and a non-trivial failure mode (model
emits a sentence prefix before the JSON, or wraps the JSON in
Markdown fences, etc.). Structured-output / JSON mode tells the
model to emit *only* well-formed JSON conforming to a caller-supplied
shape. The Anthropic SDK exposes this via the
[`tool_choice` strict-JSON pattern](https://docs.anthropic.com/claude/docs/tool-use)
and the newer `response_format` parameter.

### Canonical Anthropic SDK invocation

```python
import anthropic

client = anthropic.Anthropic()
response = client.messages.create(
    model="claude-opus-4-7",
    max_tokens=1024,
    tools=[{
        "name": "emit_verdict",
        "description": "Emit the review verdict in structured form.",
        "input_schema": {
            "type": "object",
            "properties": {
                "verdict": {"type": "string", "enum": ["ACCEPT", "REJECT", "ADJUST"]},
                "must_fix": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["verdict", "must_fix"],
        },
    }],
    tool_choice={"type": "tool", "name": "emit_verdict"},
    messages=[{"role": "user", "content": "Review this diff..."}],
)
# response.content[0].input is the parsed dict
```

### Framework consumption

The Pair-Rail dispatcher (`.claude/hooks/check_pair_rail.py`) and the
debate-round orchestrator (`/debate` slash command) both parse
free-form Claude/Codex responses today with regex + heuristic
post-processing. PLAN-086 Wave A.3 introduces a `codex_strict_json_*`
audit action for the Codex side; the Claude side is wired by
**PLAN-088 (Adaptive Execution Kernel + Reality Ledger)** — see
PLAN-088 §Wave 2.2 `_lib/model_routing.py resolve()` and §Wave 4
adapter promotions. Strict-JSON adoption is a load-bearing
prerequisite for the AC10 auto-activation matrix (PLAN-088 AC10),
since auto-activation requires deterministic verdict parsing.

**Forward-links:** `PLAN-086` (Codex side, Wave A), `PLAN-088`
(Claude side + framework-wide adoption).

---

## Pattern 2 — Chain-of-Verification (CoVe) (COOK-P2)

### Intent

A single model pass can hallucinate confidently, especially on
multi-step reasoning. Chain-of-Verification (CoVe) prompts the model
to (a) emit a draft answer, (b) decompose the draft into atomic
factual claims, (c) verify each claim independently, (d) emit a
revised answer that drops the unverified claims. Net effect: the
model "audits its own draft" before the caller sees it. The pattern
is especially well-suited to debate rounds, audit-finding adjudication,
and review verdicts where premature confidence is the dominant
failure mode.

### Canonical Anthropic SDK invocation

```python
import anthropic

client = anthropic.Anthropic()

def cove_review(diff: str) -> str:
    # Pass 1 — draft
    draft = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=2048,
        messages=[{"role": "user", "content": f"Review this diff:\n{diff}"}],
    ).content[0].text

    # Pass 2 — extract atomic claims
    claims = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=1024,
        messages=[
            {"role": "user", "content": f"Diff:\n{diff}"},
            {"role": "assistant", "content": draft},
            {"role": "user", "content": "List every atomic factual claim above, one per line."},
        ],
    ).content[0].text

    # Pass 3 — verify each claim
    verified = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=2048,
        messages=[
            {"role": "user", "content": f"Diff:\n{diff}\n\nClaims:\n{claims}\n\n"
                                        "For each claim emit VERIFIED / REFUTED / UNCERTAIN."},
        ],
    ).content[0].text

    # Pass 4 — revised answer dropping non-VERIFIED claims
    return client.messages.create(
        model="claude-opus-4-7",
        max_tokens=2048,
        messages=[
            {"role": "user", "content": f"Diff:\n{diff}"},
            {"role": "assistant", "content": draft},
            {"role": "user", "content": f"Verification:\n{verified}\n\n"
                                        "Rewrite your review dropping non-VERIFIED claims."},
        ],
    ).content[0].text
```

### Framework consumption

The /debate orchestrator currently runs single-pass-per-archetype
reviews. PLAN-088 §Wave 3 introduces an `automated_verification_pass`
audit action that wraps the existing review hot path with a CoVe
gate when the verdict is `ADJUST_HARD` (the highest-stakes verdict
class). The trade-off is ~3-4x token cost per CoVe-gated review,
which is why CoVe is conditional on verdict severity rather than
always-on. Reality Ledger (PLAN-088 §Wave 4) consumes the per-claim
verification trace as evidence.

**Forward-links:** `PLAN-088` (CoVe gate on ADJUST_HARD verdicts),
`PLAN-092` (CoVe expansion to /audit-page and /security-review).

---

## Pattern 3 — Citations API (COOK-P3)

### Intent

When a model cites a source file or document in its response, the
caller needs to verify the citation actually exists at the claimed
location (the canonical "model hallucinated a function name" failure
mode). The Citations API returns structured citation spans alongside
the prose response: each citation carries `{document_id, page,
char_start, char_end}` so the caller can mechanically confirm the
referenced bytes match. This is load-bearing for any
audit/review/PR-comment workflow where false-positive citations
would erode operator trust.

### Canonical Anthropic SDK invocation

```python
import anthropic

client = anthropic.Anthropic()
response = client.messages.create(
    model="claude-opus-4-7",
    max_tokens=2048,
    messages=[{
        "role": "user",
        "content": [
            {
                "type": "document",
                "source": {"type": "text", "media_type": "text/plain",
                           "data": open("CLAUDE.md").read()},
                "citations": {"enabled": True},
            },
            {"type": "text",
             "text": "What governance gates does the CEO protocol require?"},
        ],
    }],
)
# Each response.content[i].citations is a list of {cited_text, document_index, ...}
```

### Framework consumption

The `code-reviewer` sub-agent (`.claude/agents/code-reviewer.md` +
`code-review-checklist` skill) currently emits findings as free-text
that may reference line numbers; line-number drift between review
time and merge time produces phantom findings (the PLAN-058 phantom
rejection rate analysis surfaced this). Citations API adoption
**(PLAN-092 §Phase 1)** replaces line-number references with
verifiable citation spans so the audit log can mechanically detect
when a citation is stale.

**Forward-links:** `PLAN-092` (Citations-backed review surface),
`PLAN-093` (Citations in `/audit-page` HTML output).

---

## Pattern 4 — Message Batches API (COOK-P4)

### Intent

The Anthropic Message Batches API processes large request volumes
asynchronously at ~50% the cost of synchronous calls, with a 24h
SLA. The trade-off is wall-clock latency: a batch returns in
minutes-to-hours rather than seconds. The pattern fits **bulk
read-only workloads** where the operator is willing to amortize
latency for cost: nightly audit sweeps, eval suites, historical-log
re-classification, finding-set adjudication across an entire
corpus. It does NOT fit interactive workloads (the /spawn dispatch
hot path stays synchronous).

### Canonical Anthropic SDK invocation

```python
import anthropic

client = anthropic.Anthropic()

batch = client.messages.batches.create(
    requests=[
        {
            "custom_id": f"finding-{i}",
            "params": {
                "model": "claude-opus-4-7",
                "max_tokens": 1024,
                "messages": [{"role": "user", "content": prompt}],
            },
        }
        for i, prompt in enumerate(prompts)
    ],
)

# Poll until ended; retrieve results
while batch.processing_status != "ended":
    time.sleep(60)
    batch = client.messages.batches.retrieve(batch.id)

for result in client.messages.batches.results(batch.id):
    print(result.custom_id, result.result.message.content[0].text)
```

### Framework consumption

PLAN-088 §Wave 4.2 introduces `_lib/adapters/live/claude_batch.py`
(`BatchClaudeLiveAdapter`) per handoff §3 file-ownership matrix.
The adapter is consumed by:

- `audit-finding-adjudication` flow — when a PLAN-NNN-audit
  produces ≥100 raw findings (e.g. the 236-finding PLAN-084
  output), the Wave D adjudication pass switches from synchronous
  per-finding dispatch to batched dispatch with 50% cost savings.
- Nightly eval-suite reruns — read-only.
- Historical audit-log re-classification when a new SKILL.md
  promotion (e.g. PLAN-080 v2.5 PII core promotion) requires
  retroactively re-tagging spans.

The synchronous `_lib/adapters/live/claude.py` adapter is **NOT**
replaced; it remains the default for interactive /spawn dispatch.
The batch adapter is invoked only via the `--batch` flag on
specific top-level commands (`/audit-page --batch`, `/debate
finalize --batch`).

**Forward-links:** `PLAN-088` Wave 4.2 (`BatchClaudeLiveAdapter`
implementation), `PLAN-093` (`--batch` flag plumbing in
slash commands).

---

## What's NOT in this catalogue

This file inventories 4 patterns that PLAN-084 Wave B.8 specifically
flagged as **load-bearing for the framework's SOTA closure**. The
broader Anthropic Cookbook contains additional patterns (prompt
caching, embeddings, vision, computer use, agent SDK harness, etc.)
that the framework either already consumes (prompt caching is
Gate-1 discipline per `docs/opus-4-7-operations.md`) or has
explicitly out-of-scoped (vision is not a framework concern).

When a new Cookbook pattern lands upstream, the PLAN-08x audit cycle
re-inventories — adding rows here when the pattern fits the
framework's "SOTA-velocity" thesis ([[feedback-owner-velocity-thesis]]).

---

## Source finding IDs

- R-021 (Citations API) — PLAN-084 `findings-master.jsonl`
  `F-A-CR-D[redacted]` cluster.
- R-022 (Chain-of-Verification) — PLAN-084 TIER 3 SOTA enrichment
  category.
- R-023 (Message Batches API) — PLAN-084 capability-gap-report axis
  B.7 (Cookbook adoption).
- R-025 (Structured output / JSON mode) — PLAN-084 TIER 3 enrichment
  (load-bearing for AC10 auto-activation).
