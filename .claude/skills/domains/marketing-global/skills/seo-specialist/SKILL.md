---
name: seo-specialist
description: Technical and content SEO for software products — covers Core Web Vitals, schema.org JSON-LD, sitemap/robots governance, entity-aware content structure, canonical deduplication, and EEAT hardening. Drops keyword stuffing, cloaking, redirect chains, and AI-slop patterns.
inspired_by:
  - source: msitarzewski/agency-agents/marketing/marketing-seo-specialist.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-06
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
  - "**/seo/**"
  - "**/sitemap*.xml"
  - "**/robots.txt"
---

# SEO Specialist

## Quando aplicar

Invoke this skill when the task involves any of:

- Auditing or authoring `sitemap.xml`, `robots.txt`, or canonical tags
- Implementing `schema.org` structured data (JSON-LD)
- Diagnosing Core Web Vitals regressions (LCP, INP, CLS)
- Designing URL taxonomy, internal linking, or site architecture
- Reviewing page-level on-page elements (title, H1, meta description, semantic HTML)
- Investigating crawl budget waste or indexation gaps
- Evaluating content strategy for topical authority or entity coverage
- Identifying and resolving keyword cannibalization across pages
- Auditing redirect chains, 4xx crawl errors, or orphaned pages

Skip this skill for paid-search (SEM/PPC), social media advertising, or email marketing — those have separate profiles.

## Hard rules

These rules are non-negotiable. Violation triggers an immediate BLOCK verdict regardless of other quality signals:

1. **White-hat only.** Never recommend cloaking, hidden text, link schemes, doorway pages, keyword stuffing, or any practice explicitly prohibited by the engine's quality guidelines (Google Search Essentials, Bing Webmaster Guidelines). If an optimization can only work by deceiving the crawler, drop it.

2. **Canonical before optimization.** Before proposing any title, H1, or content change, verify canonical tag correctness and confirm no page self-conflicts (`<link rel="canonical" href="...">` must resolve to the intended URL, not a redirect target). Fixing a broken canonical beats any on-page optimization.

3. **Crawl access before content.** A page blocked in `robots.txt` or marked `noindex` cannot rank. Verify crawl access exists before recommending content improvements.

4. **Never fabricate metrics.** Do not invent search volume, Domain Authority, or ranking data. If data is unavailable, say so. Present estimates as estimates with sourcing.

5. **EEAT is non-negotiable for YMYL topics.** Health, finance, legal, and safety content requires author entity markup (`schema.org/Person` with credentials), editorial policy link, and external citation density ≥ 1 per 500 words. Absence is a BLOCKER.

6. **Redirect chains ≤ 1 hop.** A redirect chain of ≥ 2 hops leaks PageRank and slows crawl. Always resolve to a single 301.

7. **Core Web Vitals thresholds are hard limits:**
   - LCP ≤ 2.5 s (field data, 75th percentile)
   - INP ≤ 200 ms (field data, 75th percentile)
   - CLS ≤ 0.1 (field data, 75th percentile)
   Exceeding these makes the page ineligible for the "page experience" ranking signals. Flag as CRITICAL if any threshold is missed.

## Technical SEO foundations

### Crawl infrastructure

**`robots.txt` governance:**
- One canonical `robots.txt` at `https://domain.com/robots.txt` (no redirects).
- `Sitemap:` directive present; resolves to a valid URL without redirect.
- Audit blocked paths quarterly — stale `Disallow` rules accumulate silently.
- Disallow parameter-only URLs (e.g. `?sort=`, `?color=`) that generate thin duplicates.

```txt
User-agent: *
Disallow: /admin/
Disallow: /search?
Disallow: /*?utm_*
Sitemap: https://example.com/sitemap.xml
```

**`sitemap.xml` health:**
- Every URL in the sitemap must return HTTP 200 and must be canonical (no 301 targets).
- `<lastmod>` must reflect actual last-modified date — never use today's date as a blanket value; crawlers detect and stop trusting it.
- Split sitemaps at ≤ 50,000 URLs or ≤ 50 MB uncompressed. Use a sitemap index.
- Video, image, and news sitemaps are separate extensions — do not mix into the main URL sitemap.
- Ratio of indexed URLs (Search Console) ÷ sitemap URL count is the crawl efficiency signal. Below 0.7 → investigate indexation blockers.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://example.com/blog/technical-seo-guide/</loc>
    <lastmod>2026-04-15</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.8</priority>
  </url>
</urlset>
```

### Canonical deduplication

The canonical tag declares the single authoritative URL for a piece of content. Rules:

- Self-referencing canonical on every indexable page without exception.
- Canonical must point to the final destination URL — not to a redirect.
- Paginated content: each page is self-canonical (`/page/2/` → `rel="canonical" href="/page/2/"`). Do **not** point all pages to page 1 (that prevents indexation of valid deep links).
- WWW vs non-WWW: pick one, enforce via 301 at the server/CDN level, self-canonical to the winner.
- HTTP vs HTTPS: enforce HTTPS; canonical must use HTTPS scheme.
- Trailing slash: pick one scheme per URL pattern and enforce consistently.

### Structured data (schema.org JSON-LD)

JSON-LD is preferred over Microdata — it is decoupled from HTML structure and easier to maintain.

Required for most publishing contexts:
```json
{
  "@context": "https://schema.org",
  "@type": "Article",
  "headline": "Technical SEO Foundations for Software Products",
  "datePublished": "2026-04-01",
  "dateModified": "2026-05-06",
  "author": {
    "@type": "Person",
    "name": "Author Name",
    "url": "https://example.com/authors/author-name/"
  },
  "publisher": {
    "@type": "Organization",
    "name": "Example Co",
    "logo": {
      "@type": "ImageObject",
      "url": "https://example.com/logo.png"
    }
  },
  "mainEntityOfPage": {
    "@type": "WebPage",
    "@id": "https://example.com/blog/technical-seo-guide/"
  }
}
```

Validate with Google's Rich Results Test before deploying. Structured data errors do not surface in `<head>` parsing — only in the validator.

Additional schema types by content:
- `FAQPage` — for Q&A sections targeting People Also Ask
- `HowTo` — step-by-step instructional content
- `Product` + `Offer` — e-commerce product pages
- `BreadcrumbList` — site hierarchy navigation

### Core Web Vitals — engineering controls

**LCP (Largest Contentful Paint):**
- Preload the LCP resource: `<link rel="preload" as="image" href="hero.webp">`.
- Eliminate render-blocking CSS above the fold. Inline critical CSS.
- Serve images in WebP/AVIF with proper `srcset` and `sizes`.
- Use CDN with edge caching for static assets.

**INP (Interaction to Next Paint):**
- Move heavy computation off the main thread with `scheduler.postTask()` or `requestIdleCallback`.
- Avoid synchronous `XMLHttpRequest` on user interaction paths.
- Debounce/throttle rapid-fire event listeners.

**CLS (Cumulative Layout Shift):**
- Always set `width` + `height` attributes on `<img>` and `<video>` elements.
- Reserve space for late-loading embeds (ads, iframes) with `aspect-ratio` in CSS.
- Avoid injecting content above the fold after page load.

### URL taxonomy

- Descriptive keywords in URL slugs; no stop words, no URL-encoded characters.
- Depth ≤ 4 levels from root (`/category/subcategory/page/` is maximum for most sites).
- No underscores — use hyphens as word separators.
- Stable URLs. Do not change slugs after indexation without redirecting.

## Content SEO foundations

### Entity-aware content structure

Modern search engines model topics as entities (people, places, organizations, concepts) not keywords. Content targeting requires:

- Primary entity declaration in H1 + first paragraph.
- Supporting entity mentions distributed naturally — co-occurrence signals topical authority.
- Internal links use descriptive anchor text matching the target page's primary entity.
- External citations to high-authority entity sources (Wikipedia, gov sites, academic publishers) reinforce EEAT.

### Keyword cannibalization prevention

**Run a cannibalization audit before any title, H1, or content change.** Procedure:
1. Query Search Console (Dimensions: page + query) for the target keyword cluster.
2. Identify pages ranking in positions 1-30 for overlapping queries.
3. Assign one "owner" page per query — defined as the page with the highest click share for that query.
4. For each non-owner page ranking for an owned query:
   - Remove or rewrite the competing title/H1 to differentiate.
   - Add an explicit internal link from the non-owner to the owner.
   - Consolidate thin non-owner pages into the owner via 301 redirect if the overlap is total.

Skipping this step before optimization routinely splits click share and depresses both pages. This is a pre-optimization BLOCKER.

### Semantic HTML and accessibility-SEO intersection

Search engines use DOM structure to infer document hierarchy. Use semantic elements:

- `<article>`, `<section>`, `<nav>`, `<aside>`, `<header>`, `<footer>` — not `<div>` for structural meaning.
- Single `<h1>` per page; `<h2>`→`<h3>` hierarchy follows logical outline, not visual design.
- `<img alt="...">` — descriptive alt text serves both accessibility and image indexation.
- `<a href>` — every important page must be reachable via crawlable anchor link. JavaScript-only navigation that requires events to trigger navigation is invisible to crawlers.

### Internal linking architecture

- Every page must have ≥ 1 internal link from another indexed page (orphan = uncrawlable in practice).
- Pillar/cluster model: a pillar page covers a broad topic; cluster pages cover subtopics and link back to the pillar.
- Anchor text must be descriptive and match the target page's primary keyword — avoid "click here," "read more," "learn more" as anchor text.
- Maximum link depth from homepage: 3 clicks for strategic pages; 4 clicks for long-tail pages.

### Search-engine-specific considerations

**Google:**
- EEAT (Experience, Expertise, Authoritativeness, Trustworthiness) is a documented quality rater dimension that correlates with ranking for YMYL. Mechanically: structured author markup, external links to authoritative sources, editorial policies, review dates.
- Google crawls mobile-first. Desktop-only content on non-responsive pages may not be indexed. Verify via `?m=0` vs `?m=1` user-agent switching.
- Helpful Content System: single-purpose affiliate pages, thin AI-generated articles, and mass-produced templates are devalued. Evidence-based original research is rewarded.

**Bing:**
- Freshness signal is stronger than Google's. `<lastmod>` in sitemap and `Last-Modified` HTTP header directly influence crawl prioritization.
- Bing Webmaster Tools provides a keyword research tool unavailable in Search Console — use it for validation.
- IndexNow protocol (`https://www.bing.com/indexnow`) notifies Bing within minutes of URL changes. Implement for dynamic sites.

**DuckDuckGo:**
- No user tracking; privacy signal cannot be gamed. Rankings draw heavily from Bing's index.
- DuckDuckGo Instant Answers pull from Wikidata — maintaining brand entity on Wikidata improves branded knowledge panel coverage.
- Optimizing for Bing covers ~90% of DuckDuckGo surface area.

**General (engine-agnostic) principle:** Build for users first. Every major algorithm change since 2012 (Panda, Penguin, Hummingbird, BERT, MUM, Helpful Content) has moved rankings toward genuine quality and away from mechanical keyword manipulation.

## Anti-patterns

These patterns must be caught during review and flagged BLOCKED:

| Anti-pattern | Why it fails | Correct approach |
|---|---|---|
| **Keyword stuffing** | Triggers spam filters; degrades readability; penalized since 2011 Panda | Natural keyword density ~1-2%; semantic variation |
| **Cloaking** | Shows crawlers different content than users; manual action (de-indexation) penalty | Single source of truth; same HTML for all user-agents |
| **Hidden text** | `color:white` on white background, `display:none` keyword lists | Only display content users can see |
| **Redirect chains (≥2 hops)** | PageRank leak; crawl budget waste; latency | 301 directly to canonical destination |
| **Parasitic backlinks** | Link spam (comment spam, PBNs, paid links) triggers Penguin; disavow overhead | Earn links via content quality and digital PR |
| **AI-generated content with no human review** | Factual errors, entity confusion, EEAT failure; devalued by Helpful Content System | Human author reviews + adds empirical data + adds citation |
| **Title tag keyword repetition across pages** | Cannibalization; search engines can't distinguish ownership | One unique primary keyword per title; differentiated intent per page |
| **Orphaned pages** | Zero internal links = not discoverable by crawler even if in sitemap | Every page reachable via at least one `<a href>` from an indexed page |
| **`noindex` + sitemap inclusion** | Contradictory signals; crawl budget consumed for no indexation gain | Remove `noindex` pages from sitemap |
| **JavaScript-rendered critical content with no SSR/SSG** | Crawlers may not execute JS; content invisible | Use SSR or SSG for SEO-critical content; verify with `fetch as Googlebot` |

## CORRECT vs WRONG

### Title tag construction

**WRONG** — duplicate primary keyword across pages:
```html
<!-- /blog/ page -->
<title>Technical SEO Guide | Example</title>

<!-- /technical-seo/ pillar page -->
<title>Technical SEO Guide — Complete Reference | Example</title>
```
Both pages compete for "Technical SEO Guide". The engine assigns it arbitrarily.

**CORRECT** — differentiated intent per page:
```html
<!-- /blog/ index page -->
<title>SEO Blog — Latest Guides and Case Studies | Example</title>

<!-- /technical-seo/ pillar page -->
<title>Technical SEO Guide — Crawl, Index, and Performance | Example</title>
```

---

### Robots.txt — blocking assets that need to be crawlable

**WRONG** — blocking CSS and JS files used by SEO-critical pages:
```txt
User-agent: Googlebot
Disallow: /static/
```
Google cannot render the page without CSS/JS. Mobile-friendly test fails.

**CORRECT** — block only thin-content parameter URLs:
```txt
User-agent: *
Disallow: /search?
Disallow: /*?session_id=
```

---

### Internal link anchor text

**WRONG** — generic anchor:
```html
For more information about schema markup, <a href="/schema-guide/">click here</a>.
```

**CORRECT** — descriptive anchor matching target page's primary keyword:
```html
See the <a href="/schema-guide/">schema.org JSON-LD implementation guide</a> for full examples.
```

---

### Image alt text — SEO + accessibility

**WRONG** — keyword stuffing in alt text:
```html
<img src="hero.webp" alt="SEO technical SEO SEO specialist SEO guide SEO expert">
```

**CORRECT** — descriptive text matching image content:
```html
<img src="hero.webp" alt="Diagram showing crawl budget flow from Googlebot to sitemap to indexed pages">
```

---

### Canonical on paginated series

**WRONG** — all paginated pages point to page 1:
```html
<!-- /blog/page/2/ -->
<link rel="canonical" href="https://example.com/blog/">
```
Pages 2+ are de-indexed. Deep-linked blog posts on those pages lose discovery.

**CORRECT** — self-canonical on each pagination:
```html
<!-- /blog/page/2/ -->
<link rel="canonical" href="https://example.com/blog/page/2/">
```

## Cross-refs

- ADR-060 — `inspired_by:` schema and bulk creative-authoring licensing rules
- ADR-058 — adversarial review framing (applies to SEO audits: treat all existing page claims skeptically; verify against Search Console, not self-reports)
- ADR-052 — multi-model dispatch: SEO audits involving EEAT compliance for YMYL content require Opus (security-adjacent); content structure tasks may use Sonnet
- PLAN-074 — bulk rewrite wave this skill ships under; quality bar §59-67
- External references (non-framework): Google Search Essentials (search.google.com/search-console/about), schema.org, Core Web Vitals thresholds (web.dev/vitals/), Bing Webmaster Guidelines
