---
name: agentic-search-optimizer
description: >
  Discipline for optimising content and interactive surfaces for agentic-search
  workflows — multi-step LLM-driven research, browsing-agent traversal, and
  computer-use pipelines (Anthropic computer-use, OpenAI deep-research, Perplexity
  browser, Edge Copilot). Pages are designed for agent traversal and task
  completion, not human eyeball scanning. Distinct from `ai-citation-strategist`
  (which targets answer-citation in LLM responses) — this skill targets content
  discoverability and transactional task-completion inside agent loops. Use when:
  auditing whether AI agents can complete high-value site tasks; implementing
  WebMCP declarative or imperative markup; designing semantic HTML for agent
  traversal; mapping agent friction across multi-step task flows; or establishing
  server-side telemetry for agent-cohort analytics.
owner: Renata Vasconcelos (Agentic Search Optimizer, domain persona)
tier: domain:marketing-global
scope_tags: [agentic-search, deep-research, browsing-agents, computer-use, agent-discoverability, llm-traversal]
inspired_by:
  - source: msitarzewski/agency-agents/marketing/marketing-agentic-search-optimizer.md@783f6a72bfd7f3135700ac273c619d92821b419a
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
  - "**/*.html"
  - "**/webmcp/**"
---

# Agentic Search Optimizer

## Cardinal Rule

Agent discoverability and task-completion are separate objectives from
traditional search ranking and AI citation. A page that ranks well in search
results and is cited by LLM assistants may still fail completely when a browsing
agent attempts to execute a task on it. The correct optimisation target is
task-completion rate across agent-driven flows — measured end-to-end from
discovery through extraction — not position in a results page or frequency of
citation. All audit, implementation, and telemetry decisions follow from this
framing.

---

## Fail-Fast Rule

Agent optimisation work MUST NOT begin without a baseline task-completion
measurement. The following gates MUST be satisfied before any implementation
change is made:

1. The task flows under audit are enumerated as user journeys — not pages — with
   defined entry points, step sequences, and success states (form submitted,
   booking confirmed, resource downloaded).
2. A baseline task-completion rate per flow has been recorded using at least one
   live browser agent. Self-assessment or developer walkthrough is not a valid
   substitute.
3. The target agent surface is identified — declarative WebMCP markup,
   imperative WebMCP registration, semantic HTML for general browsing agents,
   or `/mcp-actions.json` discovery endpoint — before work begins. Conflating
   surfaces produces uncoordinated implementations.

If any gate is unresolved, implementation is blocked until it is closed.

---

## When to Apply

Activate this skill when the work involves any of the following:

- Auditing whether AI browsing agents can discover, initiate, and complete
  high-value task flows on a site or web application.
- Implementing WebMCP declarative markup (`data-mcp-action`, `data-mcp-description`,
  `data-mcp-params`) on native HTML forms and interactive elements.
- Implementing WebMCP imperative registration (`navigator.mcpActions.register()`)
  for dynamic, state-dependent, or SPA-driven flows.
- Publishing or maintaining a `/mcp-actions.json` discovery endpoint with a
  corresponding `<link rel="mcp-actions">` head reference.
- Designing semantic HTML and ARIA landmark structure for general-purpose
  browsing-agent traversal where WebMCP is not yet deployed.
- Mapping agent friction points — where in a task flow agents drop, fail, or
  misinterpret intent — and classifying failures by root cause.
- Establishing server-side telemetry to detect and analyse agent-cohort traffic.

Skip when: the task is LLM citation frequency in answer-engine results — route
to `domains/marketing-global/skills/ai-citation-strategist`; the task is
traditional organic search ranking — route to
`domains/marketing-global/skills/seo-specialist`; the task is frontend
JavaScript framework implementation detail — route to the relevant frontend
skill.

---

## Agent Traversal Frame

An agent traverses pages, not search-results pages. The distinction matters
for optimisation scope: a browsing agent is dispatched with a task, navigates
to an entry URL, and then follows a chain of interactions to a defined success
state. The agent does not skim a results page and pick the most cited link —
it executes a plan across a site's actual interactive surface.

### What Agents Prioritise

Agents parse interactive surfaces looking for declared available actions,
navigable links, form fields with machine-interpretable labels, and structured
data that maps to task parameters. In the absence of explicit declarations,
agents attempt DOM inference — reading visible text, following links that match
task semantics, and filling inputs based on placeholder or label text. DOM
inference is fragile; explicit declaration is required for reliable task
completion.

Priority order for agent action discovery:

1. `navigator.mcpActions` registry (imperative WebMCP — highest fidelity,
   browser-support-gated as of the 2026 draft spec).
2. `data-mcp-action` / `data-mcp-description` / `data-mcp-params` declarative
   attributes on native HTML forms (stable, broad compatibility, zero JS required).
3. `/mcp-actions.json` discovery endpoint linked from `<head>` (site-level
   enumeration for agents that pre-fetch the action catalogue).
4. Semantic HTML with ARIA landmarks and explicit `<label for="…">` bindings
   (fallback for agents that do not yet implement WebMCP).
5. Visible text and link anchor heuristics (least reliable; acceptable only as
   a last resort for non-interactive discovery steps).

### Per-Agent Crawler Signatures

Agent traffic is identifiable server-side via user-agent strings and request
pattern signatures. Current signatures (as of the 2026 draft ecosystem):

| Agent surface | User-agent signal | Notes |
|---|---|---|
| Claude in Chrome | Chromium base + `claude` token | Reference implementation; declarative + imperative |
| Edge Copilot | Chromium base + `Edg/` + Copilot task context header | Declarative full support; imperative partial |
| Perplexity browser | `PerplexityBot` or in-browser variant | Primarily declarative via DOM; no imperative |
| OpenAI deep-research | `OAI-SearchBot` derivative | Multi-step fetch chain; no WebMCP as of Q1 2026 |
| General Chromium agents | Varies | Test per-agent; log and classify |

Signatures change as browser versions update. Server-side logging is the only
durable detection mechanism — do not rely solely on static lists.

---

## Agent-Readable Structure

Agents parse interactive surfaces the way screen readers do: they traverse the
DOM tree, read text nodes, resolve ARIA roles and labels, follow logical focus
order, and activate interactive elements by role. A page that is inaccessible
to a screen reader is inaccessible to a browsing agent.

### Semantic HTML Requirements

- Use `<form>`, `<input>`, `<select>`, `<textarea>`, and `<button>` elements
  for all interactive flows. Custom-built widget replacements that do not emit
  standard semantic roles break agent interaction.
- Every form control MUST have an associated `<label for="…">` binding. The
  label text is the primary signal agents use to map task parameters to form
  inputs. Placeholder-only inputs are invisible to label-dependent traversal.
- Table headers (`<th>`) MUST be present on data tables. Agents use header
  cells to understand column semantics when extracting tabular data.
- ARIA landmarks (`<main>`, `<nav>`, `<header>`, `<footer>`, `role="form"`)
  allow agents to navigate to the relevant page region without full DOM traversal.
- Accessible names on interactive elements (`aria-label`, `aria-labelledby`,
  or linked `<label>`) MUST be present on all controls that do not have visible
  text labels.

### Keyboard-Only Operability

Agents interact with forms via keyboard-equivalent actions. A form that requires
mouse hover, drag, or click-hold to progress is blocked for agent traversal.
All interactive steps must be reachable and activatable via `Tab`, `Enter`,
`Space`, and arrow keys.

---

## Anti-Bot Compatibility

Not all automated traffic is hostile. Legitimate AI browsing agents — dispatched
by users to complete tasks on their behalf — must not be blocked by anti-bot
infrastructure designed for scraping or credential-stuffing.

### Opt-In vs Opt-Out

The correct default posture for AI browsing agents is to allow access and apply
rate limiting appropriate to the use case. Blanket blocking of AI user-agents
is an opt-out posture that breaks user-requested task completion. Operators
wishing to block specific agents should use `robots.txt` declarations targeting
the specific bot user-agent, not broad `ai` or `llm` wildcard rules that
capture legitimate browsing agents.

### robots.txt Declarations

`robots.txt` AI-bot directives are the standard mechanism for communicating
access policy. Specific known-harmful crawlers should be listed with `Disallow`
rules. Browsing agents completing user-delegated tasks should not be blocked
unless the site has a legal or contractual reason to prevent automated access.
Verify `robots.txt` rules against the agent user-agent signatures listed in the
Agent Traversal Frame section above before deployment.

### Legal Posture

Access control policies for AI agents vary by jurisdiction and are evolving.
In the EU, blocking agents acting on behalf of a user who has authorised the
session may conflict with emerging user-autonomy regulations. In the US, the
Computer Fraud and Abuse Act analysis applies differently to user-delegated
agents than to autonomous scrapers. Legal review is required before implementing
blanket AI-agent blocks. Consult `core/architecture-decisions` for
risk-posture framing.

---

## Reasoning-Path Optimisation

Multi-step agent tasks follow a chain: discovery → entry → traversal →
extraction. Optimising only the landing page is insufficient — each link in
the chain must support agent progression.

### Discovery

The agent must be able to reach the task entry point. This requires either:

- A `/mcp-actions.json` endpoint that enumerates available actions site-wide,
  allowing agents to identify the correct entry URL without crawling.
- Clear semantic link text on navigation elements so that DOM-traversal agents
  can route to the correct page based on task semantics.

Redirect chains, JavaScript-only navigation, and session-gated URLs all block
the discovery step.

### Entry

The entry page must confirm to the agent that the correct task surface has been
reached. WebMCP declarative markup on the primary form or `navigator.mcpActions`
registration on page load provides this confirmation. Without declaration, agents
rely on heuristic matching — fragile and unverifiable.

### Traversal

Multi-step flows — booking a slot, submitting a multi-page form, completing a
checkout — must maintain navigable state across steps. State loss between steps
causes agents to restart from the beginning or abandon the flow. Server-side
session management is more reliable than client-side state for agent traversal;
SPAs must ensure that each logical step has a stable URL or a declared WebMCP
state transition.

### Extraction

At the success state, the agent must be able to extract a confirmation artefact:
a booking reference, confirmation number, download link, or success message. The
confirmation element MUST be machine-readable — a visible text node in the DOM,
not a canvas render or a notification toast that disappears after 3 seconds.

---

## Provenance Signals

When agents traverse informational content rather than transactional flows, they
construct attributable answers from page content. Provenance signals are the
structural cues that allow agents to attribute claims correctly.

Required provenance structure for informational pages:

- Author name and role in a machine-readable element (not an image, not inline
  in a byline sentence without semantic tagging).
- Publication date in a `<time datetime="YYYY-MM-DD">` element. Relative dates
  ("3 days ago") are not machine-parseable for citation.
- Organisation or publication name in visible text — not only in `<title>` or
  `<meta>` tags that agents may deprioritise.
- Source citations for data claims with author, publication, and year — the same
  three fields a retrieval system requires to construct an attributable citation.

Contradictory claims within a page — a headline that states one figure and a
body paragraph that states a different figure — cause agent extraction failures.
The agent either returns the wrong figure or flags the source as unreliable.
Content must be internally consistent before publication.

---

## Tool-Use Compatibility

Agents complete tasks by interacting with the same form controls a keyboard user
would operate. Tool-use compatibility requirements apply to every interactive
element in a high-priority task flow.

### Forms

- Native `<form>` elements with standard HTTP submission or a declared
  `data-mcp-action` attribute are the most compatible form implementation.
- Custom React, Vue, or Angular form components must emit correct ARIA roles and
  accept keyboard-triggered events. Components that only respond to synthetic
  mouse events are agent-incompatible.
- Multi-step wizard forms must provide clear forward and backward navigation
  via keyboard-activatable buttons with accessible labels — not icon-only
  navigation.

### Search and Filter Controls

- Site search must be reachable via a standard `<input type="search">` or a
  field with `role="searchbox"`. Search-as-you-type implementations that rely
  on `keydown` events are compatible; click-only trigger implementations are not.
- Filter panels that use custom toggle components must expose `role="checkbox"`
  or `role="radio"` with matching `aria-checked` state attributes.

### Date and Time Inputs

Custom JavaScript date pickers are the most common agent-blocking widget. The
required pattern: provide a native `<input type="date">` (or `type="datetime-local"`)
as either the primary input or a hidden fallback. The native input is
interactable by all keyboard-capable agents regardless of WebMCP support level.

---

## Telemetry

Server-side telemetry is the primary observability mechanism for agent-cohort
analytics. Client-side analytics are unreliable for agents — session scripts
may not execute, consent banners may not be dismissed, and agent sessions may
not trigger standard event tracking.

### User-Agent Pattern Detection

Log the full user-agent string for every request. Implement a pattern-matching
classifier that assigns incoming requests to cohorts: known-agent, suspected-agent,
human-browser, or crawl-bot. Known-agent cohorts are defined by the signatures
in the Agent Traversal Frame section. Suspected-agent cohorts are identified by
headless browser patterns (absence of certain headers, atypical timing patterns,
non-human scroll behaviour reported by session tools).

### Agent-Specific Cohort Analytics

Track per agent-cohort:

- Entry URL distribution — which pages agents reach first.
- Step-completion rates per task flow — at which step agents drop or fail.
- Task-completion rate — ratio of sessions that reach a defined success state.
- Session duration distribution — agent sessions completing the same task should
  cluster; high variance indicates traversal uncertainty.
- Error response rates — 4xx and 5xx rates for agent-cohort sessions may differ
  from human-cohort rates due to different request patterns.

Report these metrics on a weekly cadence. Task-completion rate below 80% on
any priority flow is a remediation trigger. Completion rate improvement after
WebMCP implementation is the primary evidence of ROI.

---

## Anti-Patterns

| Anti-pattern | Description | Correction |
|---|---|---|
| Cloaking for agents | Serving different content to detected AI user-agents than to human browsers to game citation frequency | Serve identical content to agents and humans; differential content is detectable and penalised by search and LLM pipelines |
| Agent-targeted SEO spam | Inserting agent-specific text injections — hidden divs, CSS display:none content, `data-mcp-description` values that contradict visible content — to inflate discoverability | WebMCP descriptions MUST match visible page content; mismatches break agent trust and trigger policy violations |
| Breaking accessibility for modern UI | Replacing native form controls with visually rich custom widgets (canvas pickers, drag-and-drop reorder, gesture-only inputs) without accessible fallbacks | Every custom interactive widget requires a keyboard-operable native HTML equivalent; audit at the same time as WebMCP implementation |
| Anti-scrape on legitimate AI bots | Blocking browsing agents via CAPTCHA, IP range blocks, or `robots.txt` wildcard rules targeting all AI crawlers | Apply targeted `robots.txt` `Disallow` rules to known-harmful scrapers; do not block browsing agents completing user-delegated tasks |
| Imperative-first implementation | Deploying `navigator.mcpActions.register()` before native HTML forms have declarative `data-mcp-*` attributes, treating the more-complex path as the baseline | Declarative markup is lower risk, broader-compatible, and requires no JS; implement declarative first on all existing native forms before adding imperative registration |
| Completion-unmeasured launch | Shipping WebMCP implementation without recording a before-baseline task-completion rate, making improvement undemonstrable | Record baseline completion rate with a live browser agent before the first implementation commit; retest after each implementation phase |
| Placeholder-only form labels | Using `placeholder` text as the sole description of form field purpose — placeholder text disappears on input and is not reliably exposed as an accessible name | Every form control requires a `<label for="…">` binding or an `aria-label` attribute; placeholder text is supplementary, never the sole label |

---

## Cross-References

- `domains/marketing-global/skills/ai-citation-strategist` — optimising for
  LLM citation frequency in answer-engine responses. Route when the goal is
  appearing in ChatGPT, Perplexity, or Claude answer outputs, not task
  completion inside agent loops.
- `domains/marketing-global/skills/seo-specialist` — traditional organic search
  ranking, structured data implementation, crawl optimisation, backlink strategy.
  Route when the task is search-results position rather than agent task-completion.
- `core/architecture-decisions` — risk-posture framing for legal and governance
  decisions around AI-agent access policy.

---

## ADR Anchors

- **ADR-058** — governs skill authoring standards for domain skill files,
  including house-voice requirements, provenance attribution, and anti-contamination
  rules that apply to all `domains/marketing-global/` skill content.
