# CAG vs RAG — Decision Tree + Adopter Recipes

> **Audience:** adopters deciding when retrieval beats inline cache.
> **Companion:** [`CAG-PATTERNS.md`](./CAG-PATTERNS.md) covers
> what's already cached. This doc covers when caching alone isn't
> enough.
> **PLAN:** PLAN-062 Phase 2.

## TL;DR

Most adopters do not need RAG. CAG (cache-augmented generation —
what the framework already does) covers ~80% of cases:

```
KB fits inline?         → CAG only (most adopters)
KB > 200k tokens?       → CAG + retrieval
KB > 1M tokens?         → CAG + LightRAG sidecar (ADR-062)
Queries informal?       → consider HyDE recipe (HYDE-RECIPE.md)
```

This doc gives you the decision tree, two re-rank recipes you can
plug into spawn prompts without forking the framework, and a matrix
mapping the 8 RAG patterns from popular hype posts to what
ceo-orchestration actually ships.

---

## 1. Decision tree (when each wins)

### 1.1 Quick test

Run this against your repo:

```bash
# Approximate inline-able size of your knowledge base
find . -type f \
  \( -name "*.md" -o -name "*.py" -o -name "*.ts" -o -name "*.go" \) \
  -not -path "./.git/*" \
  -not -path "./node_modules/*" \
  -not -path "./vendor/*" \
  -exec wc -w {} + | tail -1
```

Words divided by ~0.75 ≈ token count. (1 word ≈ 1.33 tokens for
typical English/code mix.)

| Token count | Recommendation |
|---|---|
| < 200k | Inline-able. Use CAG only. Skip RAG. |
| 200k - 1M | Inline still possible but expensive. CAG + selective retrieval recommended. |
| 1M - 10M | LightRAG sidecar starts paying off. ADR-062 was sized for this band. |
| > 10M | Sidecar mandatory. Consider HyDE for query/doc semantic gap. |

### 1.2 Full decision tree

```
                        ┌──────────────────────────┐
                        │  Knowledge base size?    │
                        └────────────┬─────────────┘
                                     │
              ┌──────────────────────┼──────────────────────┐
              │ < 200k tokens        │ 200k - 1M tokens     │ > 1M tokens
              ▼                      ▼                      ▼
     ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
     │  CAG only       │    │ CAG + retrieval │    │ CAG + sidecar   │
     │  (this is the   │    │ (manual or      │    │ (ADR-062        │
     │   default)      │    │  custom hook)   │    │  LightRAG)      │
     └────────┬────────┘    └────────┬────────┘    └────────┬────────┘
              │                      │                      │
              ▼                      ▼                      ▼
     Skills + plans + ADRs   Add re-rank pre-filter   Install sidecar
     fit in cold prefix.     (Recipe 3.1 or 3.2).     per INSTALL-RAG.md.
                             Skip sidecar overhead.    Skip if smaller.

                        ┌──────────────────────────┐
                        │  Queries informal /      │
                        │  multi-skill team /      │
                        │  cross-lingual?          │
                        └────────────┬─────────────┘
                                     │
                              ┌──────┴──────┐
                              │ yes         │ no
                              ▼             ▼
                       ┌───────────┐  ┌───────────┐
                       │  Add HyDE │  │  Skip     │
                       │  recipe   │  │  HyDE     │
                       │ (HYDE-    │  │           │
                       │  RECIPE.md)│  │           │
                       └───────────┘  └───────────┘
```

---

## 2. Lost-in-the-middle is real

> "Most of what we retrieve in RAG setups never actually helps the
> LLM."

This is the real failure mode of naive top-k retrieval — documented
empirically by Liu et al, "Lost in the Middle" (TACL 2024; arXiv 2307
v1 2023). Findings:

- LLMs attend strongly to the **start** and **end** of long contexts.
- Information in the **middle** is largely ignored.
- More chunks ≠ better answers. Returning top-10 often performs
  *worse* than top-3 because the relevant chunk gets buried.

Practical implications for ceo-orchestration adopters:

| Heuristic | Why |
|---|---|
| **Top-3 > Top-10** | Less middle, less noise |
| **Re-rank before injecting** | Pull most-relevant to top of injected block |
| **Cite line ranges, not whole files** | The model focuses on cited lines |
| **Smaller chunks (200-400 tokens) > larger** | Less middle per chunk |
| **De-duplicate near-identical chunks** | Reduce repeated noise |

These are *retrieval-side* mitigations. They apply whether you use
LightRAG sidecar, custom retrieval, or grep-based context assembly.

---

## 3. Recipes — plug retrieval into the framework without forking

The framework's spawn prompt is built by `inject-agent-context.sh`
+ optional pre-spawn hooks. The cleanest place to plug retrieval +
re-rank is **before** the inject step: build the context block,
then inject.

### 3.1 Recipe — bge-reranker (local, no cloud cost)

[`bge-reranker-v2`](https://huggingface.co/BAAI/bge-reranker-v2-m3)
is a free local cross-encoder. Pair it with whatever retrieval you
have (grep, vector DB, sidecar) to bump retrieval quality.

**Setup (adopter's venv, NOT framework venv):**

```bash
# In your project's venv (not .claude/rag/venv)
python3 -m venv .my-rerank-venv
source .my-rerank-venv/bin/activate
pip install sentence-transformers torch
```

**Wrapper script:** `examples/rerank-spawn-context.py` (shipped with
this PLAN). Read top-k chunks from any source, re-rank against the
spawn task, write top-3 to a context block.

**Wire into spawn:**

```bash
# In your custom spawn wrapper:
SPAWN_TASK="audit src/auth.ts for timing oracles"

# Step 1: get top-10 candidates from your retrieval (grep, sidecar, etc.)
grep -rn "auth\|token\|crypto" src/ > /tmp/candidates.txt

# Step 2: re-rank with bge
python3 examples/rerank-spawn-context.py \
    --task "$SPAWN_TASK" \
    --candidates /tmp/candidates.txt \
    --top 3 > /tmp/context.txt

# Step 3: inject into spawn prompt
.claude/scripts/inject-agent-context.sh "Staff Code Reviewer" "$SPAWN_TASK" \
    --context-file /tmp/context.txt
```

Cost: free (local). Latency: ~50-200ms per query depending on
candidate count + GPU/CPU.

### 3.2 Recipe — Cohere rerank (cloud)

For adopters preferring managed:

```python
import cohere

co = cohere.Client(api_key=os.environ["COHERE_API_KEY"])

candidates = [
    "src/auth.ts:45 — async function validateToken(token: string) {...}",
    "src/auth.ts:88 — function timingSafeCompare(a, b) {...}",
    # ... up to 100 candidates
]

response = co.rerank(
    model="rerank-english-v3.0",
    query="audit auth.ts for timing oracles",
    documents=candidates,
    top_n=3,
)

# response.results[i].document, response.results[i].relevance_score
```

Cost: ~$0.001 per query (~100 candidates). Latency: ~50ms cloud
round-trip.

When to use cohere over bge:

- Multi-language repos (cohere supports more languages)
- No local GPU/CPU budget
- Already paying for cohere infra elsewhere

When to stay local with bge:

- Privacy-sensitive code (don't send to third party)
- Air-gapped deployments
- Cost predictability (no per-query billing)

### 3.3 Recipe — grep + manual ranking (no model)

For repos under ~100k LoC, this is often *enough*:

```bash
# Sort by line-density of query terms
grep -rn -c "auth\|token\|crypto" src/ \
    | sort -t: -k2 -rn \
    | head -3
```

Limitations: no semantic match, false positives on common words.
Works fine for:

- Symbol resolution ("where is `ProcessOrder`?")
- Filename patterns ("show me migration files")
- Recent-edit ranking (`git log --oneline | head`)

This is what `inject-agent-context.sh` does today by default.
Sufficient for vibecoder-solo Tier 0 adopters. See
[`ADOPTER-SCALE-TIERS.md`](./ADOPTER-SCALE-TIERS.md).

---

## 4. The 8 RAG patterns mapped to ceo-orchestration

Hype posts often list "8 RAG architectures" or similar. Here's the
honest map of where each applies (or doesn't) for a Claude-only
adopter:

| # | Pattern | Coverage in framework | Notes |
|---|---|---|---|
| 1 | **Naive RAG** (vector similarity) | LightRAG sidecar dense layer | opt-in via ADR-062; off-by-default |
| 2 | **Multimodal RAG** (text+image+audio) | not applicable | code repos are text only; out of scope |
| 3 | **HyDE** (hypothetical doc embeddings) | recipe shipped | see [`HYDE-RECIPE.md`](./HYDE-RECIPE.md) |
| 4 | **Corrective RAG** (validate vs trusted source) | conceptually present | `inject-agent-context.sh` validates files exist + grep verifies claims |
| 5 | **Graph RAG** (knowledge graph) | LightRAG graph layer | LightRAG is hybrid graph+vector by design (EMNLP 2025) |
| 6 | **Hybrid RAG** (dense + graph) | LightRAG | exactly what LightRAG does |
| 7 | **Adaptive RAG** (query classifier) | not shipped | low ROI for Claude-only; out of scope |
| 8 | **Agentic RAG** (ReAct + CoT + memory) | **the framework itself** | CEO + spawn protocol + memory + plans = this |

Honest takeaway:

- 4 of 8 already covered (1, 5, 6, 8) via existing capability + ADR-062 sidecar
- 1 conceptually covered (4 — corrective)
- 1 ships as a recipe (3 — HyDE)
- 2 are inapplicable (2 — multimodal, 7 — adaptive)

A Claude-only adopter does **not** lag behind any of these patterns
in capability. The framework either does it (1, 5, 6, 8), gives you
the recipe (3), or it's not relevant for code repos (2, 7).

The reverse is also true: the framework's strongest pattern —
**Agentic RAG** — is what hype posts list as "the most advanced"
form. The framework is the production-shape implementation of it
for Claude.

---

## 5. Why we don't ship retrieval pipelines in core

ADR-002 enforces stdlib-only for the framework core. ADR-096
enforces vibecoder-only-by-design. Adding bge-reranker /
sentence-transformers / cohere SDK to the core would:

1. Break ADR-002 (deps explosion)
2. Bloat install footprint (+2 GiB venv for things 80% of adopters
   don't need)
3. Increase maintenance debt (model versions, security audits,
   upgrade paths)
4. Force adopters to install heavy tooling for a feature they don't
   use

Instead:

- The framework core stays stdlib-only.
- LightRAG sidecar (ADR-062) is **opt-in via separate venv**.
- Re-rank recipes (this doc) are **adopter-side patterns**, not
  framework code. You install in your venv, you wire it.
- HyDE is a **recipe** not a feature.

This is the same philosophy as `INSTALL-RAG.md`: heavy stuff lives
in adopter-controlled territory, framework core stays small.

---

## 6. When CAG isn't enough — escalation order

If you've followed CAG-PATTERNS.md and still hit retrieval problems:

1. **First, verify cache discipline.** Check cache hit rate (see
   [`CAG-PATTERNS.md`](./CAG-PATTERNS.md) §6). If <85%, fix that
   first. Most "RAG problems" are actually "cache invalidation"
   problems.

2. **Then, add re-rank** (Recipe 3.1 or 3.2). Cheapest improvement.
   Often resolves "wrong chunks injected" complaints.

3. **Then, add HyDE** if queries are abstract / cross-skill /
   cross-lingual. See [`HYDE-RECIPE.md`](./HYDE-RECIPE.md).

4. **Then, install LightRAG sidecar** if KB > 1M tokens or you
   need cross-file graph reasoning. See [`INSTALL-RAG.md`](./INSTALL-RAG.md).

5. **Last, custom retrieval pipeline.** Vector DB choice
   (chroma, pgvector, weaviate, etc.), custom chunking, embedding
   model selection. The framework gets out of your way at this
   point — wire whatever you need into your spawn pre-hooks.

Don't skip steps. Each step is ~10× the complexity of the previous.

---

## 7. Anti-patterns

Things adopters try and shouldn't:

| Anti-pattern | Why it's bad | Do this instead |
|---|---|---|
| Embed everything in the cold prefix to "cache it forever" | Cold prefix is bounded by Anthropic context window; you'll exceed it | Use sidecar (ADR-062) for >1M tokens KB |
| Use HyDE for every query | 2× cost, 500ms latency tax for negligible gain on technical queries | Use HyDE only for informal/cross-skill queries |
| Run cohere rerank + bge rerank stacked | No additional gain over best of either; just more cost | Pick one |
| Custom vector DB without sidecar | Maintenance nightmare; sidecar handles install / venv / model versions | Use sidecar |
| Cache the retrieved chunks in cold prefix | Chunks change per query; cold prefix should be query-invariant | Keep retrieved chunks in hot tail |

---

## 8. Further reading

- **Cache patterns:** [`CAG-PATTERNS.md`](./CAG-PATTERNS.md) — what
  the framework already caches.
- **HyDE recipe:** [`HYDE-RECIPE.md`](./HYDE-RECIPE.md) — when to
  use it, copy-paste implementation.
- **Sidecar install:** [`INSTALL-RAG.md`](./INSTALL-RAG.md) —
  LightRAG opt-in via MCP.
- **Adopter scale tiers:** [`ADOPTER-SCALE-TIERS.md`](./ADOPTER-SCALE-TIERS.md)
  — which tier you're in, what to enable.
- **Lost in the middle:** Liu et al, "Lost in the Middle: How
  Language Models Use Long Contexts" (TACL 2024) — empirical
  basis for top-3 > top-10.
- **ADR-062:** rationale for opt-in LightRAG sidecar instead of
  embedded retrieval.
