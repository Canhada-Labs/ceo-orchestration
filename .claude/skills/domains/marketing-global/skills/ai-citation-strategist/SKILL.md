---
name: ai-citation-strategist
description: >
  Answer Engine Optimisation (AEO) discipline covering citation-eligibility
  analysis, LLM-readable content structure, schema and entity discipline, per-
  platform citation tracking (Perplexity, ChatGPT-search, Google AI Overview,
  Bing Copilot), and cross-platform source authority enforcement. Treats citation-
  eligibility as the primary ranking primitive in the post-blue-link era — the
  ability of an LLM or retrieval system to extract, attribute, and surface a
  passage is a prerequisite for any recommendation outcome. Use when: auditing
  why a brand is absent from AI-overview results while competitors are cited;
  restructuring content for factual density and verifiability; implementing
  schema.org JSON-LD for AI-discoverability; designing a multi-platform citation
  tracking programme; or diagnosing entity-clarity failures that suppress LLM
  recommendation likelihood.
owner: Valentina Cruz (AI Citation Strategist, domain persona)
tier: domain:marketing-global
scope_tags: [aeo, ai-citation, llm-search, ai-overview, perplexity, citation-strategy]
inspired_by:
  - source: msitarzewski/agency-agents/marketing/marketing-ai-citation-strategist.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-07
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7c) ---
domain: marketing-global
priority: 8
risk_class: low
stack: []
context_budget_tokens: 500
inactive_but_retained: true
repo_profile_binding:
  frontend: {active: false, priority: 10}
  engine: {active: false, priority: 10}
  fintech: {active: false, priority: 10}
  trading-readonly: {active: false, priority: 10}
  generic: {active: false, priority: 10}
activation_triggers: []
# --- K1 paths: native file-touch activation (PLAN-135 W3 unit k1a) ---
paths:
  - "**/structured-data/**"
  - "**/*.jsonld"
  - "**/content/**"
---

# AI Citation Strategist

## Cardinal Rule

An LLM that cannot extract a self-contained, verifiable claim from a passage
cannot cite it. Citation-eligibility is the new ranking primitive: before a
brand can be recommended by any AI-assisted discovery surface, the content
representing that brand must be structured so that a retrieval system can
isolate the relevant passage, attribute it to a named source entity, and
confirm its factual basis from the passage itself. Page rank, domain authority,
and social proof are contributing signals; none of them substitute for
citation-eligible content structure. The entire discipline of AEO begins with
this constraint and works backward to every content and schema decision.

---

## Fail-Fast Rule

Citation optimisation MUST NOT begin without a baseline audit. Implementing
schema markup, restructuring content, or building new assets before establishing
per-platform citation rates produces unmeasurable outcomes — there is no before
state against which to measure improvement. The following gates MUST be
satisfied before any fix-pack work is started:

1. A prompt set of at least 20 queries (covering recommendation, comparison,
   how-to, and definitional intent) has been constructed from the target ICP's
   actual vocabulary, not from internal brand language.
2. Each prompt has been run against all four primary surfaces — Perplexity,
   ChatGPT-search, Google AI Overview, Bing Copilot — and results have been
   recorded with brand citation status, competitor citation status, and citation
   position (primary vs. supplementary).
3. The baseline citation rate per platform and the share-of-voice gap versus the
   most-cited competitor have been calculated and documented.

If any gate is unresolved, fix-pack generation is blocked until it is closed.
Fix packs authored without a baseline produce implementation activity, not
measurable citation improvement.

---

## When to Apply

Activate this skill when the work involves any of the following:

- Auditing why a brand does not appear in AI-overview results for queries where
  it should be a plausible answer.
- Restructuring existing content to improve factual density, entity clarity, or
  passage atomicity for LLM extraction.
- Implementing or auditing schema.org JSON-LD markup intended to improve AI
  discoverability (FAQ, HowTo, Article, Author, Organization, Product schemas).
- Designing a citation tracking programme across Perplexity, ChatGPT-search,
  Google AI Overview, and Bing Copilot.
- Diagnosing a competitor citation advantage — understanding which content
  structures, entity signals, or authority indicators the competitor holds that
  the brand does not.
- Building or reviewing content assets specifically structured for AI-overview
  inclusion (Q-A pages, definition-first articles, comparison matrices).

Skip when: the task is organic search ranking without AI-overview scope — route
to `domains/marketing-global/skills/seo-specialist`; the task is content
authorship and narrative architecture — route to
`domains/marketing-global/skills/content-creator`; the task is agentic search
campaign management — route to
`domains/marketing-global/skills/agentic-search-optimizer`.

---

## Citation-Eligibility Frame

Citation eligibility is determined by four structural properties of a content
passage. All four must be present; failure on any one reduces citation
probability across all surfaces.

**Factual density.** A citable passage makes at least one concrete, specific,
verifiable claim per 50-75 words. Generic observations, ambient framing, and
hedged summaries do not constitute factual density. The test: can the claim in
this passage be confirmed or refuted by checking a primary source? If the answer
is no, the passage is not citation-eligible regardless of its schema decoration.

**Verifiability.** Claims must be attributable: named sources, publication years,
and measurable figures. An LLM or retrieval system evaluating a passage for
citation will weight attributed claims over unattributed assertions. Claims that
cannot be traced to a named primary source are treated as low-confidence by
retrieval systems and will be superseded by competitor passages that cite
primary sources.

**Entity clarity.** The subject entity — the brand, product, concept, or actor
the passage is about — must be unambiguously named and contextualised within
the first two sentences of any citation-eligible passage. Pronominal reference
and assumed context break entity resolution at the passage level. Each passage
must stand alone as a retrievable unit; context from surrounding sections is
not available to a retrieval system extracting the passage in isolation.

**Citation-friendly format.** Passages are more likely to be extracted when they
are structured as: a direct answer to an implied question followed by
supporting evidence; a definition followed by distinguishing characteristics;
or a comparison followed by a concrete differentiator. Extended narrative prose
— even when factually correct — has lower extraction fidelity than these three
formats because the claim is distributed across multiple sentences, increasing
the risk of truncation artefacts.

---

## LLM-Readable Structure

Retrieval systems extract passages, not pages. Content structured for page-
level reading is not equivalent to content structured for passage-level
extraction. The gap between the two is the primary structural failure in AEO
implementation.

**Q-A pair blocks.** A question header followed immediately by a direct answer
— before any supporting context — is the highest-fidelity extraction format
across all four primary citation surfaces. The direct answer must be contained
in the first sentence of the response; elaboration follows. A Q-A block that
buries the answer in the third sentence is not citation-eligible at the passage
level.

**Bullet density.** Lists of three to seven discrete items are extracted as
citation units more reliably than equivalent prose. Each bullet must be a
self-contained claim or instruction; bullets that are continuations of the
preceding sentence are not discrete extraction units.

**Definition-first paragraphs.** When a section introduces a term, concept, or
entity, the definition must appear as the opening sentence, not as the
conclusion of an explanatory paragraph. Definitional content placed mid-
paragraph has reduced extraction fidelity because retrieval systems apply a
higher extraction confidence to passages where the subject is stated first.

**Passage atomicity.** No single citable claim should require reading two or
more non-adjacent sections to be fully understood. If a passage references
context established five sections earlier, it is not atomic. Atomic passages
allow a retrieval system to surface the claim without surfacing its neighbours.

---

## Schema and Entity Discipline

Schema markup does not substitute for citation-eligible content; it increases
the probability that correctly structured content is correctly attributed. In
the absence of citation-eligible content, schema markup produces correctly-
attributed uncitable content — it resolves the entity but does not provide a
passage worth extracting.

**Primary schema types for AEO:**

| Schema type | Use case | Required fields for AEO |
|---|---|---|
| FAQPage | Q-A content blocks | `@type: FAQPage`, `mainEntity` array of `Question` with `acceptedAnswer` |
| HowTo | Step-by-step instruction content | `@type: HowTo`, `step` array with `name` and `text` per step |
| Article | Long-form content with authorship | `@type: Article`, `author` (Person entity), `datePublished`, `dateModified` |
| Organization | Brand entity declaration | `@type: Organization`, `name`, `url`, `sameAs` array |
| Product | Product-level entity signals | `@type: Product`, `name`, `description`, `brand`, `review` |
| Person | Author entity for authority signals | `@type: Person`, `name`, `url`, `sameAs` array pointing to authoritative profiles |

**sameAs disambiguation.** Every Organization and Person entity MUST include
a `sameAs` array with at least two external authoritative identifiers —
Wikidata, Wikipedia, Crunchbase, LinkedIn, or domain-authoritative profile
pages. Without `sameAs` links, the entity declaration is local and may not
resolve to the correct knowledge graph node. Entity confusion — where an LLM
conflates the brand with a similarly named entity — is almost always traceable
to missing `sameAs` references.

**Implementation constraint.** JSON-LD in `<script type="application/ld+json">`
is the required delivery mechanism. Microdata and RDFa are not reliably parsed
by all four citation surfaces. One schema block per page type; multiple
overlapping schema blocks on the same page reduce parsing confidence.

---

## Source Authority Signals

Citation surfaces weight source authority when selecting among multiple
citation-eligible passages on the same query. Authority signals operate at
three levels.

**Author entity.** An article with a named, entity-resolved author — Person
schema with `sameAs` links to an established professional profile — is treated
as higher authority than anonymous or byline-only content. The author entity
must exist in the knowledge graph, not merely be named on the page.

**Publication date.** Dated content is preferred to undated content on
factual queries. `datePublished` and `dateModified` in Article schema signal
both recency and maintenance discipline. Undated claims are treated as
low-confidence by retrieval systems for any query where recency is material.

**Primary source citation.** Passages that cite primary sources — linking to
original research, official data releases, or primary coverage — are weighted
over passages that summarise secondary sources. The citation must be
traceable: a link to the primary source, not a reference to "studies" or
"research." Unlinked citations reduce authority weight.

**Contrarian-but-correct framing.** Passages that make a specific, surprising,
empirically supported claim that contradicts a common assumption have
disproportionate citation probability. A claim that reframes a settled
assumption is memorable and extractable; a claim that restates consensus is
interchangeable with competing passages. This is not a recommendation to
manufacture controversy; it is a recognition that LLMs and retrieval systems
weight specificity and distinction over agreement with established summaries.

---

## Citation Tracking

Each citation surface has distinct retrieval mechanisms, knowledge cutoffs, and
citation formats. A tracking programme that conflates them produces misleading
aggregate rates.

| Surface | Retrieval type | Citation format | Tracking mechanism |
|---|---|---|---|
| Perplexity | Real-time search + LLM synthesis | Inline numbered citations + source panel | URL tracking on source panel; structured log of prompt set results per run |
| ChatGPT-search | Real-time search (where enabled) + training data | Inline citation links in Browse mode | Prompt set run in Browse mode only; training-data responses are untracked |
| Google AI Overview | Google index + LLM synthesis | Collapsible attribution panel above organic results | Manual prompt set audit; no programmatic access; screenshot + manual log |
| Bing Copilot | Real-time Bing index + LLM synthesis | Inline numbered citations + source cards | URL tracking on source cards; prompt set structured log |

**Tracking cadence.** Prompt set audits must be run at minimum every 14 days
during an active fix-pack cycle. Citation behaviour can shift with model updates,
index changes, and competitor content changes. A single audit at the start of
a programme and a single recheck at the end will miss mid-cycle shifts that
invalidate the fix-pack's assumptions.

**Non-determinism constraint.** AI responses are non-deterministic. A prompt
run five times on the same surface on the same day will produce citation
variation. A single-run audit is insufficient; each prompt in the prompt set
must be run a minimum of three times per surface, with citation status recorded
for each run and aggregated as a citation rate (citations observed / total runs),
not as a binary cited/not-cited result.

---

## Cross-Platform Optimisation

One canonical source is the required foundation. Duplicating citation-eligible
content across multiple domains, subdomains, or owned media properties splits
citation signal and creates entity confusion. All canonical citation-eligible
content must resolve to a single authoritative URL per claim. Syndication and
republication require canonical tags pointing to the primary URL.

**Per-platform format variants.** While canonical content must reside at a
single URL, the structure of that content can include format variants that
serve each surface's extraction preferences:

- For Perplexity and Bing Copilot: Q-A blocks and bullet-dense lists perform
  best. Both surfaces prefer short direct answers followed by elaboration.
- For ChatGPT-search: comparison tables and feature-focused content perform
  best on commercial queries. FAQ schema on Q-A content improves extraction
  fidelity.
- For Google AI Overview: content that already ranks in positions 1-5 for
  the target query is overwhelmingly more likely to appear in AI Overviews.
  Schema markup and entity clarity are secondary signals to organic rank for
  this surface.

**Platform-specific entity cards.** Google Knowledge Panel (controlled via
Google Business Profile + entity markup), Bing Entity (controlled via Bing
Places + Organization schema), and Perplexity source panel entries are all
distinct. Optimising one does not propagate to the others. Each requires
dedicated entity verification and maintenance.

---

## Anti-Patterns

| Anti-pattern | Description | Correction |
|---|---|---|
| AI-slop content | LLM-generated prose that produces hedged, generic, claim-light passages — high word count, low factual density — that retrieval systems consistently deprioritise | Re-author for factual density: one concrete verifiable claim per 50-75 words minimum; generic framing struck |
| Keyword-stuffed schema | FAQPage or HowTo markup that injects keyword-dense questions not matching actual ICP query patterns | Map schema questions directly to prompt set; FAQPage questions must match the exact query phrasing the target audience uses |
| Schema-without-content | Schema.org markup applied to pages whose body content is not citation-eligible — entity-resolved but passage-uncitable | Content citation-eligibility gates (factual density, verifiability, entity clarity, format) must be met before schema is added |
| Fake authority | Author entity schema referencing a persona without an external knowledge graph presence, or `sameAs` links pointing to owned-domain profiles only | Author entities require at least two external authoritative identifiers; owned-domain links alone do not resolve entity authority |
| Contradictory passages | Multiple passages on the same domain making competing or inconsistent claims about the same entity or product attribute — retrieval systems reduce citation confidence on inconsistent sources | Canonical claim inventory: every factual claim about the brand or product must be consistent across all pages; contradictions identified in baseline audit must be resolved before fix-pack deployment |
| Single-surface optimisation | Restructuring content for one citation surface without testing on all four — improvements on one surface can reduce citation rate on others due to format preference differences | All structural changes must be validated against the full four-surface prompt set before rollout |

---

## Cross-References

- `domains/marketing-global/skills/seo-specialist` — technical SEO depth,
  crawl optimisation, backlink strategy, canonical tagging. Route when the
  work is organic search ranking without AI-overview scope or when technical
  implementation of structured data requires crawl-level analysis.
- `domains/marketing-global/skills/agentic-search-optimizer` — agentic search
  campaign design, AI-assisted discovery at the campaign level. Route when the
  task is campaign architecture rather than content and entity optimisation.
- `domains/marketing-global/skills/content-creator` — narrative architecture,
  voice consistency, repurposing matrix design. Route when the task is content
  authorship rather than citation-eligibility audit or schema implementation.

---

## ADR Anchors

- **ADR-058** (Brainstorm gate pre-Plan + two-pass adversarial review): the
  baseline audit gate in this skill — establishing per-platform citation rates
  before any fix-pack is authored — is a direct application of ADR-058's
  requirement that a spec artefact be produced before execution begins. The
  prompt set and baseline citation scorecard serve as the spec artefact for AEO
  work. The two-pass adversarial review pattern applies to fix-pack validation:
  the first pass audits content citation-eligibility; the second pass
  specifically audits entity clarity and schema correctness against the four-
  surface citation tracking results.
