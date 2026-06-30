# HyDE Recipe — Hypothetical Document Embeddings for ceo-orchestration

> **Audience:** Tier 1+ adopters (see [`ADOPTER-SCALE-TIERS.md`](./ADOPTER-SCALE-TIERS.md))
> with informal queries against technical/formal codebases.
> **Companion:** [`CAG-VS-RAG.md`](./CAG-VS-RAG.md) (decision tree),
> [`CAG-PATTERNS.md`](./CAG-PATTERNS.md) (cache discipline).
> **PLAN:** PLAN-062 Phase 4.
> **Skip if:** Tier 0 (vibecoder solo), small KB, or queries are
> already technical/specific.

## TL;DR

HyDE (Gao et al, ACL 2023) is a 1-extra-LLM-call trick that boosts
retrieval recall on the BEIR benchmarks (paper Table 2: spread
ranges from ~0% to ~+15% per dataset; mean delta ~+5-7%). Useful
when your queries don't match your docs *semantically* — multi-skill
teams, cross-lingual repos, technical jargon vs casual phrasing.

Cost: ~$0.0001 + ~500ms per query with Claude Haiku. Free to ship
as a recipe; not part of framework core.

```
Query: "como evitar que sub-agent escreva em arquivo errado?"
                                    │
                          ┌─────────▼─────────┐
                          │ Claude Haiku gen  │
                          │ hypothetical doc  │
                          └─────────┬─────────┘
                                    │
                "Para evitar colisão de escritas entre sub-agents,
                 o framework impõe anti-collision: cada spawn
                 declara FILE ASSIGNMENT explícito listando..."
                                    │
                          ┌─────────▼─────────┐
                          │ Embed hypothetical│
                          │ (NOT the query)   │
                          └─────────┬─────────┘
                                    │
                          ┌─────────▼─────────┐
                          │ ANN search        │
                          │ against KB index  │
                          └─────────┬─────────┘
                                    │
                          Top-k real docs
                          (PROTOCOL.md §Step 0,
                           inject-agent-context.sh, etc.)
```

The hypothetical doc is **discarded after retrieval**. It exists
only to bridge the semantic gap between query and stored docs.

---

## 1. The problem HyDE solves

Vector similarity assumes query and doc live in the same semantic
space. They often don't:

| Dimension | Query | Doc | Similarity gap |
|---|---|---|---|
| Form | "como funciona X?" | "X is a Y that does Z..." | high |
| Vocab | informal/casual | technical/formal | high |
| Length | 5-10 words | 200-500 words | high |
| Language | mixed PT-EN ("processa transações") | pure EN ("ProcessTransaction") | high |

Even when the doc *contains the answer*, the embedding distance
between query and doc can be too large for naive top-k retrieval to
surface it.

HyDE fixes this by replacing the query with a "hypothetical answer"
that lives in the same space as the docs.

**Important:** The hypothetical answer can be factually wrong. It
doesn't matter. What matters is the *shape* — vocabulary, format,
terminology.

---

## 2. When HyDE wins (sweet spots)

| Scenario | Why HyDE helps |
|---|---|
| Multi-skill team queries technical codebase | Engineers + product + designers ask in their own dialect; HyDE normalizes to code-doc dialect |
| PT/ES query → EN codebase (cross-lingual) | Hypothetical answer lands in EN, matches doc embeddings |
| Casual query: "como pagar?" → formal doc: "settlement processing pipeline" | HyDE rephrases formally |
| Domain-specific jargon mismatch (account ↔ ledger ↔ posting) | LLM picks the canonical term during gen |
| Brand-new codebase, no fine-tuned retriever | Zero-shot win |
| Abstract query ("how do we handle fraud?") → concrete code (`detectAnomaly()`, `riskScore`) | Bridges abstract→concrete |

---

## 3. When HyDE loses (skip it)

| Scenario | Why naive retrieval is enough |
|---|---|
| Queries already technical: "ProcessOrder.Execute()" | symbol search nails it |
| KB small (< 200k tokens, fits inline) | retrieval is unnecessary at all |
| Latency critical (< 200ms total) | HyDE adds 500ms; not worth it |
| Cost critical (high QPS) | doubles per-query cost |
| Embedding model is weak | propagates HyDE errors instead of fixing them |
| Queries about *recent* changes | LLM doesn't know your latest edits; hypothetical doc is stale |

**Decision rule:** HyDE wins on the **abstraction gap** axis. If
your queries are already in the same shape as your docs, skip.

---

## 4. Cost-benefit table

| Metric | Naive retrieval | + HyDE |
|---|---|---|
| Latency per query (typical) | 50-200 ms | 600 ms - 2 s |
| Cost per query (with Claude Haiku gen) | ~$0.00001 (just embed) | ~$0.0001 - $0.0005 |
| Recall@10 (BEIR, paper Table 2) | baseline | spread 0% to +15% per dataset; mean +5-7% |
| Implementation complexity | trivial | +1 LLM call + 1 prompt template |
| Fail mode | silent miss when query/doc diverge | hypothetical can introduce bias if LLM hallucinates wrong jargon |

**Rule of thumb:** worth it if (recall_gain × value_per_correct_retrieval) > extra_cost. For ceo-orchestration adopters, usually true on multi-skill teams, usually false for solo expert.

---

## 5. Pipeline

### 5.1 At index time (one-time)

Same as your existing retrieval — embed your KB chunks with your
chosen embedding model, build ANN index. No HyDE-specific work.

### 5.2 At query time (per-query)

```
1. Receive user query: "como evitar colisão de sub-agents?"

2. Build HyDE prompt:
   "Write a 100-word technical paragraph that would answer this
    query in the style of project documentation: {query}"

3. Call Claude Haiku (cheap, fast) → returns hypothetical doc.

4. Embed hypothetical doc (NOT the query) with the same model
   used at index time.

5. ANN search top-k chunks using the hypothetical's embedding.

6. Inject top-k into spawn prompt for the actual answer LLM.
```

### 5.3 Discard the hypothetical

Important: do NOT include the hypothetical in the final prompt. It
served its purpose at retrieval time. Including it would:

- Inject unverified content the answer LLM might trust
- Waste tokens
- Confuse the model about what's authoritative

---

## 6. Implementation reference

A working ~80-line stdlib + Anthropic SDK + sentence-transformers
script lives at:

> [`examples/hyde-retrieve.py`](../examples/hyde-retrieve.py)

Smoke usage:

```bash
# In adopter's venv (NOT framework venv)
pip install anthropic sentence-transformers torch

# Index your KB once with bge-large-en (or whatever you use)
python3 examples/hyde-retrieve.py \
    --query "como funciona o ledger de double-entry?" \
    --kb-dir ./docs \
    --top 3 \
    --model claude-haiku-4-5
```

Output: top-3 docs in re-ranked order, hypothetical printed to
stderr for transparency.

The script is intentionally minimal:

- No vector DB integration (uses in-memory matrix for demo)
- No batch mode (single query)
- No cache (would conflict with HyDE's per-query gen)
- No production-grade error handling

For production, adopt the pattern:

1. Persistent index (chroma, pgvector, etc.)
2. Async LLM call for hypothetical
3. Connection pooling
4. Fallback to naive retrieval if HyDE LLM call fails

---

## 7. Variants worth knowing

| Variant | Difference | When better |
|---|---|---|
| **Multi-HyDE** | Generate N hypothetical docs (N=3-5), avg embeddings | High-stakes queries; reduces variance from one bad gen |
| **HyKE** (Hypothetical Knowledge Entities) | Generate entities not full doc, search by entity | Graph-shaped KB |
| **Query2Doc** (Microsoft, 2023) | Train dedicated query-expansion model | High QPS production |
| **Iterative HyDE** | Run HyDE, get top-k, refine hypothetical, run again | Precision-critical, cost-tolerant |
| **Step-back HyDE** | First gen abstract version of query, then concrete | Multi-hop reasoning queries |

For ceo-orchestration adopters, **plain HyDE is the right starting
point**. Don't over-engineer — measure recall improvement first,
then consider variants.

---

## 8. Wiring HyDE into the framework

The framework's spawn pipeline is:

```
inject-agent-context.sh <Agent> "<task>" → spawn prompt → Agent
```

To plug HyDE in:

```bash
TASK="audit how settlement integrates with kyc"

# Step 1: HyDE retrieve
HYDE_CTX=$(python3 examples/hyde-retrieve.py \
    --query "$TASK" \
    --kb-dir ./docs ./src \
    --top 3 \
    --model claude-haiku-4-5)

# Step 2: Inject into spawn
echo "$HYDE_CTX" > /tmp/spawn-ctx.txt
.claude/scripts/inject-agent-context.sh "Staff Backend Engineer" "$TASK" \
    --context-file /tmp/spawn-ctx.txt
```

Or more elegantly via a wrapper script in your project. Either way,
HyDE happens **before** the spawn — it's preparatory retrieval, not
a hook.

---

## 9. Anti-patterns

| Anti-pattern | Why it fails |
|---|---|
| Use HyDE for every spawn (autopilot) | 2× cost, often no gain on technical queries |
| Use Claude Opus for HyDE gen | Overkill — Haiku is sufficient and 10× cheaper for hypothetical gen |
| Include the hypothetical in the final answer prompt | Confuses provenance — answer LLM may trust hallucinated content |
| Generate huge hypothetical docs (1000+ words) | Diminishing returns vs 100-200 word; embeds noise |
| Embed query AND hypothetical, take max | Adds complexity, marginal gain over hypothetical-only |
| Cache the hypothetical | Per-query gen is the point — different queries get different hypotheticals |

---

## 10. Measurement

To validate HyDE is helping you:

```python
# Compare recall@10 over a held-out test set of (query, expected_doc) pairs

baseline_recall = evaluate_recall(
    queries=test_queries,
    expected=test_expected,
    retriever=naive_retriever,
)

hyde_recall = evaluate_recall(
    queries=test_queries,
    expected=test_expected,
    retriever=hyde_retriever,
)

print(f"Baseline recall@10: {baseline_recall:.3f}")
print(f"HyDE recall@10:     {hyde_recall:.3f}")
print(f"Delta: {(hyde_recall - baseline_recall) * 100:.1f}%")
```

If delta < 3%, HyDE isn't paying its cost. Disable it.
If delta > 10%, ship it.
Between 3-10%, depends on cost sensitivity.

---

## 11. Further reading

- **Original paper:** Gao et al, "Precise Zero-Shot Dense Retrieval
  without Relevance Labels" (ACL 2023). Read §3 for the algorithm
  and §4 for benchmarks.
- **Lost-in-the-middle:** Liu et al (TACL 2024) — why top-3 > top-10.
- **CAG-VS-RAG.md:** decision tree for when retrieval beats inline.
- **CAG-PATTERNS.md:** cache discipline (HyDE doesn't help if your
  cold prefix is invalidated every turn).
- **ADOPTER-SCALE-TIERS.md:** which tier you're in (HyDE applies
  Tier 1+).
