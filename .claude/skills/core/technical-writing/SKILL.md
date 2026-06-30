---
name: core-technical-writing
description: Doctrine for authoring clear, precise technical documentation in
  {{PROJECT_NAME}}. Covers hard rules for structure, voice, and vocabulary; format
  conventions by doc type (README, ADR, plan, CHANGELOG, API reference, runbook);
  anti-patterns that degrade clarity; and WRONG/CORRECT examples across doc types.
  Use when authoring or reviewing any documentation artifact — from a one-sentence
  inline comment to a multi-section ADR or a public API reference.
owner: Technical Writer (archetype)
inspired_by:
  - source: msitarzewski/agency-agents/engineering/engineering-technical-writer.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: pattern_reference
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-06
# --- smart-loading fields (PLAN-083 Wave 0a sub-agent 0.7a) ---
domain: core
priority: 7
risk_class: low
stack: []
context_budget_tokens: 800
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 6}
  engine: {active: true, priority: 7}
  fintech: {active: true, priority: 7}
  trading-readonly: {active: true, priority: 8}
  generic: {active: true, priority: 6}
activation_triggers:
  - {event: help-me-invoked, regex: "(?i)docs|writing|readme|technical.?writing"}
---

# Technical Writing

Ambiguous prose breaks software just like ambiguous code. A README that says
"configure the server" without specifying which file, which field, or what
value is equivalent to a function that accepts `any` — it compiles, it silences
the linter, and it fails in production when a reader's mental model diverges
from the author's.

Technical writing is engineering applied to language. Every sentence carries a
load. Imprecise sentences shift that load onto the reader, who may not have the
context to recover.

## What This Skill Is (and isn't)

**Is:** Universal doctrine for authoring technical artifacts — docs that ship
alongside code, govern architecture decisions, describe operational procedures,
or define APIs. The rules here apply regardless of project domain.

**Is not:** A style guide for marketing, sales copy, blog posts, or
user-facing product text. Those artifacts have different success criteria
(engagement, persuasion, brand) that are outside this skill's scope.

**Is not:** A writing style enforcer that overrides the project's established
conventions. When a project's CLAUDE.md or PROTOCOL.md specifies a doc format,
that format wins. This skill fills the gaps.

## Hard Rules

These rules are non-negotiable for any technical doc artifact. Violations are
findings, not suggestions.

1. **Imperative mood for instructions.** Instructions tell the reader what to
   do. Use the imperative: "Run the migration." Not "You should run the
   migration." Not "The migration should be run." Not "Running the migration
   is recommended."

2. **Sentence length cap: 25 words.** If a sentence exceeds 25 words, split
   it. Complex ideas chain into short sentences. Long sentences hide
   ambiguity — readers reach the end and are uncertain what modified what.

3. **No passive voice when an actor exists.** "The token is validated by the
   middleware" → "The middleware validates the token." If the actor is genuinely
   unknown or irrelevant, passive is acceptable. If the actor exists, name it.

4. **Code samples must be runnable.** Every code sample in a doc must execute
   without modification in the stated environment. If it requires substitutions,
   mark them explicitly: `<YOUR_API_KEY>`. If it requires setup, state the
   setup. A code sample that silently fails is worse than no sample — it teaches
   the reader a broken mental model.

5. **API parameters are typed, required-or-optional stated, and default-value
   explicit.** Every parameter in an API reference carries: name, type,
   required/optional, default (if any), and a one-sentence description.
   Missing any of these is an incomplete entry, not a minimal one.

6. **CHANGELOG entries follow keepachangelog.com format.** Every entry lives
   under a version heading (`## [X.Y.Z] — YYYY-MM-DD`), under a category
   (`Added`, `Changed`, `Fixed`, `Deprecated`, `Removed`, `Security`).
   Entries are written in past tense for shipped changes. No entry says
   "various improvements" — every line names a specific change.

7. **No smart quotes or em-dashes in code blocks.** Editors and copy-paste
   paths replace ASCII straight quotes (`"` and `'`) with curly variants
   (U+201C `“`, U+201D `”`, U+2018 `‘`, U+2019 `’`) and ASCII hyphens (`-`)
   with em-dashes (U+2014 `—`). Code blocks must use ASCII-only punctuation.
   Verify before committing — invisible curly substitution is a common source
   of broken examples.

8. **Language tag on every code block.** ` ```python `, ` ```bash `,
   ` ```yaml `. A bare ` ``` ` block disables syntax highlighting and signals
   the author did not decide what language the example uses. Undecided =
   incomplete.

9. **Pronouns must have explicit antecedents within the same paragraph.**
   "It validates the input" is acceptable if the prior sentence names the
   subject. "It" spanning a paragraph boundary is a zombie pronoun — the
   reader must re-scan to resolve it. If in doubt, repeat the noun.

10. **"Should" is ambiguous — replace it with "must" or "can" based on intent.**
    "Should" means different things to different readers: obligation, recommendation,
    or possibility. Choose: "must" (required, failure to comply is a bug),
    "can" (optional, reader decides), or "avoid" (anti-pattern).

11. **No jargon without a definition on first use.** Acronyms and domain terms
    are spelled out on first use: "JSON Web Token (JWT)". After that, the short
    form is acceptable. A glossary section is required if a doc introduces five
    or more domain terms.

12. **Heading hierarchy is structural, not decorative.** H1 for the doc title.
    H2 for top-level sections. H3 for subsections. Never skip levels (H1 →
    H3) to get a smaller visual heading. Use H4+ only when nesting is genuinely
    required — three levels of hierarchy is usually the limit before the reader
    loses orientation.

## Voice and Tone

**Neutral.** Technical docs are not cheerful, apologetic, or enthusiastic.
"Exciting new feature!" is marketing. "This endpoint returns the user record."
is technical writing.

**Factual.** Every claim is either verifiable by the reader or sourced. "The
function is fast" — compared to what? — is not a factual claim. "The function
processes 10,000 events/s at p99 < 2ms (benchmark: `bench/event-loop.js`)"
is factual.

**Instructive, not narrative.** A README does not tell the story of how the
code was built. It tells the reader how to use it. Narrative ("We started
this project because...") belongs in a blog post or an ADR's context section,
not in a reference doc.

**Show, then tell.** When possible, lead with the example, then explain it.
A reader who sees working code first can map the explanation onto concrete
evidence. A reader who reads explanation first must hold an abstract model
and retrofit it onto the example. Show first is faster and reduces
misinterpretation.

**Author is absent.** Avoid "we," "I," "our team," "you'll find." The doc
speaks for the system, not for a person. "The middleware validates the token"
not "We validate the token in the middleware." Exception: ADR Context sections
where attributing a decision to the team is explicit and intentional.

## Doc-Type Conventions

| Doc type | Required sections | Length expectation | Voice notes |
|---|---|---|---|
| **README** | What it does / Install / Quick start / Configuration / Contributing | 300–800 words for library-scale; 50–200 words for internal utility | Imperative for steps; declarative for descriptions |
| **ADR** | Status / Context / Decision / Consequences / (optional) Alternatives | 400–1200 words | Past tense for context; present tense for decision; factual throughout |
| **Plan** | Status / Objective / Scope / Phases / Acceptance criteria | 600–2000 words | Present tense for current state; future tense only for phases not yet executed |
| **CHANGELOG** | Version heading / Category sub-headings / Bullet entries | One bullet per discrete change; no prose paragraphs | Past tense for shipped; present tense only for "Deprecated" warnings |
| **API reference** | Endpoint / Method / Auth / Parameters / Request example / Response example / Error codes | Complete table for every parameter; no truncation | Declarative; no "you can call"; say "Returns the user record." |
| **Runbook** | Trigger condition / Symptoms / Diagnosis steps / Resolution steps / Escalation path | Step-by-step numbered lists; no prose paragraphs in action sections | Imperative throughout; terse |

### README

Start with a one-sentence description that a reader encountering the project
for the first time can use to decide whether to keep reading. Not the project
name. Not a tagline. A sentence: what the thing does. Example: "Parses
keepachangelog.com-format CHANGELOG files and emits structured JSON."

The Quick Start section must work on a clean machine with only the stated
prerequisites. Test it. A Quick Start that requires unwritten context is a
broken onboarding gate.

### ADR

The Context section describes the situation that made a decision necessary.
It is written in past tense: "The team needed a way to..." The Decision
section is present tense: "The framework uses X because Y." Consequences
lists trade-offs the team accepted — both positive and negative. An ADR
with no negative consequences is incomplete.

The Status field is a single word from a fixed vocabulary: `PROPOSED`,
`ACCEPTED`, `SUPERSEDED`, `RETRACTED`. Status changes are tracked in
`enforcement_commit` — not in free-form notes.

### CHANGELOG

Every version that ships gets an entry. No version is skipped. Pre-release
versions (`1.0.0-rc.1`) appear above their GA release. The Unreleased section
accumulates entries between releases and moves down when the version is tagged.

Category order within a version: `Added` → `Changed` → `Fixed` →
`Deprecated` → `Removed` → `Security`. Not all categories are required per
release, but the order is fixed when they appear.

### API Reference

Parameter tables include every parameter. Optional parameters include their
default value. When a parameter is an enum, list all valid values. Error codes
include the HTTP status, the error code string, and the condition that produces
it. A reference that documents only the happy path is half a reference.

### Runbook

Numbered steps in Diagnosis and Resolution sections. Each step is a single
action or check. If a step has a decision branch ("if X, go to step 5; if
Y, continue"), state the branch explicitly — never assume the reader knows
which path applies. The Escalation section names a person or on-call rotation,
not a team. "Contact the platform team" is unresolvable at 3 AM.

## Anti-Patterns

### Zombie Pronouns

Pronouns that reference a subject more than one paragraph away. The reader
must scroll to resolve the antecedent. Replace with the noun.

Trigger phrases: "it handles", "this manages", "they process" at the start
of a paragraph after a context switch.

### Future-Tense for Current Behavior

Describing existing behavior as if it were planned. "The function will
validate the input." If it already validates, use present tense: "The
function validates the input." Future tense in docs signals that the behavior
is aspirational, which is accurate only when describing unreleased planned
work.

### Ambiguous-Should

"Should" in a technical instruction means the reader must guess whether
non-compliance is a bug, a recommendation, or an option. Every "should" in
an instruction section is a latent ambiguity.

Replace with:
- "must" — non-negotiable requirement
- "avoid" — anti-pattern, deviation produces known problems
- "can" — optional, reader decides based on their use case

### Marketing-Prose-in-Docs

Superlatives and enthusiasm signals that belong in a product pitch, not a
reference doc: "blazing fast", "best-in-class", "powerful and flexible",
"seamlessly integrates." These phrases do not inform the reader. They signal
that the author is advocating, not describing.

Any comparative claim ("faster than X") requires a benchmark citation.
Any capability claim ("supports Y") requires an example or a link to one.

### Code-Without-Context

A code block dropped into a doc without:
- A statement of what it demonstrates
- A statement of its prerequisites
- The expected output when relevant

A code block with no prose around it is a puzzle. The reader must reverse-
engineer the author's intent. State the intent before the code.

### Unexplained-Omission

Documenting five of six configuration fields and silently omitting the sixth.
The reader does not know whether the omission is intentional ("not needed in
most cases"), an error, or a placeholder. When a field, step, or concept is
intentionally out of scope, say so: "The `debug_mode` field is internal to the
framework and not configurable in user-facing installs."

### We-Without-Antecedent

"We recommend...", "We designed...", "We do not support..." in a reference
doc where "we" is undefined. The reader does not know whether "we" means the
current project, an upstream library, or the company. Use the subject noun:
"The framework does not support...", "This endpoint returns..."

## WRONG / CORRECT Examples

### Example 1 — Instruction voice (README / runbook)

```markdown
# WRONG
You should probably run the migration before deploying. It will ensure
that the database schema is correct and things work properly.

# CORRECT
Run the database migration before deploying:

    python3 manage.py migrate

Expected output: `Applying all migrations: OK`
If the command exits non-zero, stop deployment and check logs at
`logs/migrate.log`.
```

### Example 2 — Parameter documentation (API reference)

```markdown
# WRONG
timeout — optional timeout setting

# CORRECT
| Parameter | Type    | Required | Default | Description                                           |
|-----------|---------|----------|---------|-------------------------------------------------------|
| timeout   | integer | no       | 30      | Request timeout in seconds. Range: 1–300. Requests that exceed this value return HTTP 408. |
```

### Example 3 — CHANGELOG entry

```markdown
# WRONG
## [1.4.0] — 2026-03-01
- Various bug fixes and improvements
- Performance improvements
- New feature added

# CORRECT
## [1.4.0] — 2026-03-01
### Added
- `audit_emit.register()` — registers a new audit action with schema validation.
  Caller must supply `action`, `schema_version`, and `required_fields`.

### Fixed
- `check_agent_spawn.py` now correctly rejects spawns where `AGENT PROFILE`
  section is missing the `model` field (previously allowed and caused silent
  model inheritance from parent).

### Security
- Redacted `api_key` from all audit log payloads. Previously logged as
  plaintext when `log_level=DEBUG` was set.
```

### Example 4 — ADR Decision section

```markdown
# WRONG
We decided to use HMAC instead of RSA because HMAC is better for our use case
and easier to implement. RSA seemed overkill. This should work well.

# CORRECT
The framework uses HMAC-SHA256 with a 32-byte secret per ADR-049a because:

1. The verifier and signer share the same process boundary — asymmetric
   crypto's key distribution benefit does not apply.
2. HMAC verification is constant-time via `hmac.compare_digest()`; RSA
   verification in Python stdlib requires an explicit timing-safe wrapper
   that the team assessed as error-prone (see Context §3).
3. Key rotation is a secret rotation, not a keypair rotation — simpler
   operational procedure for the target adopter profile (single-operator
   installs per ADR-096).

Consequence accepted: HMAC does not provide non-repudiation. If the secret
is compromised, an attacker can forge valid signatures. Mitigation: secret
stored in environment variable, never in source control (enforced by
`check_contamination.sh`).
```

### Example 5 — Runbook escalation

```markdown
# WRONG
If the issue persists, contact the team.

# CORRECT
If resolution steps 1–4 do not clear the alert within 10 minutes:

Escalate to: `@oncall-platform` in `#incidents` Slack channel.
Include in escalation:
- Output of `python3 audit-query.py tail --last=50` (paste verbatim)
- Current alert state from the dashboard URL in step 1
- Steps already attempted (list by number)
```

### Example 6 — Prose around code (README)

```markdown
# WRONG
```python
result = audit_query(action="spawn", since="2026-01-01")
```

# CORRECT
Query the audit log for all agent spawn events since a date:

```python
result = audit_query(action="spawn", since="2026-01-01")
# result is a list of AuditEntry objects
# each entry has: timestamp, agent_name, model, plan_id
```

Returns an empty list if no events match. Raises `AuditLogNotFoundError`
if the log file does not exist (see §Error Handling).
```

## Acceptance Criteria

A doc artifact passes technical writing review when:

- [ ] All instructions use imperative mood.
- [ ] No sentence exceeds 25 words.
- [ ] Passive voice replaced with active voice wherever an actor exists.
- [ ] Every code block has a language tag.
- [ ] Every code block is runnable or explicitly annotated with substitution
  markers.
- [ ] Every API parameter entry has: name, type, required/optional, default,
  description.
- [ ] CHANGELOG entries follow keepachangelog.com category structure.
- [ ] No "should" in instruction sections — replaced with "must", "can",
  or "avoid".
- [ ] No zombie pronouns spanning paragraph boundaries.
- [ ] No marketing superlatives in reference sections.
- [ ] Jargon defined on first use; glossary present if five or more new terms.
- [ ] Heading hierarchy is sequential (no level-skipping).
- [ ] Doc type matches the required-sections table in §Doc-Type Conventions.

## Related Skills

- `core/code-review-checklist` — Documentation-only changes (no code, no
  config, no schema) may bypass two-pass review per §When to SKIP two-pass.
  This skill defines what "documentation quality" means for that bypass gate.
- `core/architecture-decisions` — ADR authoring follows conventions in
  §Doc-Type Conventions §ADR above. This skill supplements, does not supersede,
  the ADR lifecycle and status vocabulary defined there.
- `core/pre-plan-brainstorm` — Plans authored during brainstorm follow the
  Plan row in §Doc-Type Conventions. The `spec.md` artifact produced by
  brainstorm is a technical doc subject to these rules.
- `core/observability-and-ops` — Runbooks produced for operational procedures
  follow §Doc-Type Conventions §Runbook and the Escalation anti-pattern rules
  above.
- `core/public-api-design` — API reference documentation follows §Doc-Type
  Conventions §API Reference. Parameter table completeness in this skill
  complements the interface-design rules in public-api-design.
