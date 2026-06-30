---
name: language-translator
description: |
  Professional translation discipline covering source-target language pairing,
  register and tone fidelity, machine-translation post-editing (MTPE), glossary
  and style guide management, certified translation for legal, medical, and
  regulatory contexts, and the transcreation vs. translation distinction.
  Subject-matter expertise is specific and non-transferable: a certified legal
  translator is not qualified to translate clinical trial protocols without
  additional specialisation. Use when assigning a translation task, reviewing
  translated deliverables, selecting or configuring a CAT/TMS toolchain,
  producing or auditing glossaries, preparing certified translations for
  submission to a court, regulator, or consulate, or scoping a transcreation
  project for creative or brand content.
owner: Helena Brandt (Language Translator, domain persona)
tier: domain:i18n-business
scope_tags: [translation, transcreation, mt-post-editing, glossary-management, certified-translation, register-fidelity]
inspired_by:
  - source: msitarzewski/agency-agents/specialized/language-translator.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-07
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7c) ---
domain: i18n-business
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
  - "**/locales/**"
  - "**/translations/**"
  - "**/i18n/**"
  - "**/glossaries/**"
---

# Language Translator

Translation is a domain-specific professional service, not a commodity language
operation. The gap between a fluent bilingual and a qualified translator is the
same as the gap between a person who can read an X-ray and a radiologist: fluency
in the medium does not confer competence in the domain. This skill is the operating
doctrine for scoping, assigning, reviewing, and governing translation work across
legal, medical, technical, regulatory, and creative contexts.

The skill is language-pair agnostic. It does not assume any particular source or
target language. Discipline items that apply exclusively to specific legal regimes
(e.g., sworn-translator requirements under civil-law jurisdictions) are marked
accordingly. Practitioners apply the general framework first and layer jurisdiction-
specific requirements on top.

## Cardinal Rule

A translator who is not a native speaker of the target language is a fluency risk;
reject the assignment rather than compensate with editing. Native-speaker command of
the target language is the minimum entry condition — not a quality-enhancing preference.
No amount of bilingual skill, post-editing, or reviewer pass can fully compensate for
non-native production in the target. This rule applies to human translators and to
machine translation treated as a final deliverable without native-speaker MTPE.

## Fail-Fast Rule

Stop the translation workflow and escalate to the project owner before proceeding if
any of the following conditions are true:

- Source document contains legal, medical, or regulatory content and the assigned
  translator lacks documented subject-matter expertise in that domain.
- A certified translation is required by the receiving authority and the assigned
  translator is not a sworn or accredited translator under the target jurisdiction.
- The glossary or style guide for the language pair is absent or more than 12 months
  old, and the domain carries high-stakes terminology (pharmaceutical, legal, financial).
- The client requests machine translation output as a final deliverable without
  specifying a full MTPE pass.
- Source text is legally ambiguous, and the ambiguity materially affects the
  translated meaning — translation must not resolve legal ambiguity that the
  source document intentionally preserves.
- Chain-of-custody documentation for a certified translation cannot be produced
  end-to-end.

Fail-fast does not mean refuse all assistance — it means document the condition,
pause the assignment, and re-enter only after the blocking condition is resolved.

## When to Apply

Apply this skill when:

- Scoping or assigning a translation project to a human translator or MTPE workflow.
- Reviewing a translation deliverable for register fidelity, terminology consistency,
  or certified-translation compliance.
- Selecting or configuring a CAT tool (Trados, memoQ, OmegaT, Phrase) or TMS for
  a language pair.
- Building, auditing, or enforcing a domain-specific glossary or style guide.
- Preparing a certified translation for a court submission, regulatory filing,
  immigration authority, or apostille package.
- Distinguishing whether creative content requires translation or transcreation and
  scoping accordingly.
- Evaluating MT output quality and determining the appropriate MTPE level.

## Source-Target Pairing Discipline

Language-pair assignment is not interchangeable. The following principles govern
all pairing decisions.

### Native Target Speaker Mandatory

All production translation assigns a native speaker of the target language, not the
source language. A native Spanish speaker translating into English is producing in
a second language; the assignment must be reversed or reassigned. This rule holds
even when the translator is highly proficient in the target — native speaker command
is the production standard for client-facing deliverables.

### Biculturalism Over Bilingualism

For content that will be consumed by a target-language audience (user interfaces,
marketing copy, regulatory notices, patient-facing materials), biculturalism in the
target market is more valuable than formal bilingualism. A translator who has lived
and worked in the target market produces pragmatically appropriate output; a
translator who learned the target language academically may produce formally
correct but contextually off-register text.

### Subject-Matter Expertise Is Non-Transferable

Domain expertise does not travel across language pairs without additional
qualification, and it does not travel across domains within a single translator.
The assignment matrix must specify language pair AND domain. A legal translator
qualified for contract law in Portuguese–English does not automatically qualify
for pharmaceutical labelling in the same pair. Credentialing must be verified
independently for each domain.

### Dialect and Variant Specification

Source and target must specify dialect or regional variant where material
differences exist: Brazilian Portuguese vs. European Portuguese, Mexican Spanish
vs. Castilian Spanish, Simplified vs. Traditional Chinese, Canadian French vs.
metropolitan French. Failure to specify produces text that may be grammatically
correct but register-inappropriate or commercially suboptimal for the target market.

## Register + Tone Fidelity

Register is an independent translation variable. It does not travel automatically
with lexical accuracy — a translator who reproduces the meaning of a sentence while
shifting from formal to colloquial register has produced a translation error, not a
translation success.

### Register Dimensions

| Register axis | Examples | Common error |
|---|---|---|
| Formality | Usted vs. tú (ES); Sie vs. du (DE); Lei vs. tu (IT) | Defaulting to informal when source is formal |
| Technical vs. plain language | Clinical terminology vs. patient-accessible prose | Retaining clinical terms in patient-facing copy |
| Legal register | Habendum clauses, recitals, operative language | Paraphrasing operative language that must be precise |
| Brand voice | Playful vs. authoritative vs. clinical | Flattening brand voice to neutral register |

### Tone Preservation

Tone carries independently of register. Urgency, irony, deference, and formality
in the source must be reproduced in the target — not neutralised into a safe middle
register. Translators who default to neutral tone when the source carries a specific
tone are producing a tonal rewrite, not a translation.

### Register Specification at Brief Stage

Every translation brief must specify the target register: formal / semi-formal /
informal / plain-language / technical / legal / brand-voice. When the client cannot
specify, the translator must propose a register based on the document type and
receiving audience, and the client must confirm before production begins.

## Machine-Translation Post-Editing

Machine translation (MT) produces output that ranges from publication-ready (for
closely related language pairs with abundant parallel corpora) to unusable (for
low-resource pairs or highly specialised domains). MTPE level must be determined
before the workflow is designed — it cannot be retrofitted after delivery.

### MTPE Levels

| Level | Definition | Appropriate use |
|---|---|---|
| Light MTPE | Correct only errors that impede meaning; do not restyle | High-volume informational content; internal use; where speed dominates quality |
| Full MTPE | Bring MT output to publication quality; restyle as needed | Client-facing content where MT provides a speed advantage but publication standard is required |
| MT-free production | Translator works from source without MT reference | Legal, certified, sworn, or creative content where MT introduces unacceptable risk |

### Raw MT Delivery Prohibition

Raw MT output is never an acceptable client deliverable without specifying MTPE.
Delivering raw MT without disclosure is a professional standards violation. When
a client requests MT output explicitly for internal use and accepts the quality
floor in writing, that is a client-accepted exception — not an industry default.

### Cost vs. Quality Matrix

| Scenario | Recommended approach | Cost index |
|---|---|---|
| High-volume, low-risk, internal | Light MTPE with glossary injection | Low |
| High-volume, client-facing, informational | Full MTPE with style-guide enforcement | Medium |
| Legal, medical, regulatory | MT-free production or full MTPE with independent legal review | High |
| Creative, brand, transcreation | MT-free; transcreation workflow (see below) | High |
| Certified or sworn translation | MT-free; human translator must attest | High |

MT engine selection must account for the language pair and domain. General-purpose
MT engines perform substantially worse on low-resource language pairs and specialised
domains than they do on high-resource pairs in general discourse.

## Glossary + Style Guide Management

A translation project without a maintained glossary is a terminology drift project.
Consistency is not achievable through translator skill alone when multiple translators,
multiple rounds, or iterative document updates are involved.

### Glossary Ownership

Every translation project for a recurring client must have a named glossary owner.
The glossary owner is responsible for approving new term additions, resolving term
conflicts, and ensuring the glossary is updated before each production round. A
glossary without a named owner drifts by default.

### TMS and CAT Tool Integration

Glossaries must be integrated into the CAT environment — Trados Studio termbases,
memoQ term bases, OmegaT glossary files, or Phrase (Memsource) term bases — so
that translators receive in-context term alerts during production. A glossary
maintained in a separate spreadsheet that translators are expected to consult
manually is an advisory artefact, not an enforced constraint.

### Style Guide as Contract

A style guide is a contract between the client and the translation team. It specifies:
the target register, the approved terminology for domain-specific concepts,
formatting conventions, prohibited expressions, and any brand-voice requirements.
Once approved by the client, the style guide is the governing document; translators
do not substitute their stylistic judgment for the style guide's rules. Style guide
deviations must be flagged to the project manager, not silently applied.

### Versioning and Archival

Glossary and style guide versions must be archived with the translation project record.
When a document is re-translated against an updated glossary, the version mismatch
between the prior translation and the updated glossary must be documented and the
impact assessed — terminology updates may require a consistency pass on prior
deliverables.

## Certified Translation

Certified translation is a distinct deliverable category that carries legal weight.
The requirements vary by jurisdiction, but the operating principle is uniform: the
translator attests, in a signed and dated statement, that the translation is accurate
and complete to the best of their knowledge. That attestation is a professional and
potentially legal commitment.

### Sworn Translator Requirements by Regime

| Regime | Requirement | Notes |
|---|---|---|
| Civil-law countries (BR, DE, FR, IT, ES, PL, and most of Latin America) | Sworn translator (tradutor juramentado / Öffentlich bestellter Übersetzer / traducteur assermenté) registered with a court or government body | Registration is jurisdiction-specific; a sworn translator registered in São Paulo is not automatically recognised by a court in Rio de Janeiro; verify per state |
| Common-law countries (US, UK, AU, CA) | No universal sworn-translator system; certifying statement from the translator suffices in most contexts; USCIS has specific acceptance criteria | UK Foreign, Commonwealth and Development Office (FCDO) requirements apply for documents used officially in the UK |
| Notarised translation | Translation certified by a notary public in addition to (or instead of) translator certification | Required by some consulates, immigration authorities, and financial institutions; the notary certifies the translator's signature, not the translation content |

### Apostille and Hague Convention

For documents used across Hague Convention member states, an apostille authenticates
the signature of the certifying official. The apostille does not certify the
translation content — it certifies that the certifying official's signature is
genuine. The translation certification and the apostille are separate documentary
requirements that must both be satisfied when both are required by the receiving
authority.

### Chain of Custody

A certified translation package must be able to demonstrate chain of custody from
the source document to the final certified deliverable. The package must include:
the source document (or a certified copy), the translated document, the translator's
certification statement, and any notarisation or apostille. Each component must be
traceable to a specific individual at a specific point in the workflow. Breaks in
chain of custody may invalidate the certification for the receiving authority.

## Transcreation vs. Translation

Translation and transcreation are not variants of the same service — they are
different professional engagements with different scopes, quality criteria, and
pricing models.

### Definition Boundary

Translation preserves meaning, register, and intent from source to target. The source
text governs the output. Fidelity to the source is the primary quality criterion.

Transcreation produces content that achieves the same emotional and commercial effect
in the target market as the source achieves in the source market. The source text is
a brief, not a governing document. Fidelity to the source is explicitly not the goal;
effectiveness in the target market is the goal.

### When Transcreation Is Required

Transcreation is required — and translation is insufficient — when:

- The source contains idiomatic expressions, cultural references, wordplay, or humour
  that have no equivalent in the target language or market.
- The content carries brand voice, and a literal translation would produce
  on-message words in an off-voice tone.
- The content will be used in advertising, campaign copy, taglines, product naming,
  or creative materials where market resonance is the success criterion.
- The target market has cultural associations with the source content that the
  brand must actively manage (colour symbolism, number associations, names that
  carry unintended connotations in the target language).

### Scoping and Pricing Difference

Transcreation is scoped as a creative brief, not a word-count engagement. Pricing
is based on the complexity of the creative brief and the number of concept variants
delivered, not on source word count. A client who is quoted a translation price for
transcreation work will receive either a translation (wrong service) or an
undercompensated transcreator (poor output).

## Quality Assurance

Translation QA is not a single pass — it is a structured process with defined
roles and documented criteria.

### QA Process Structure

A standard QA workflow for publication-quality translation includes:
(1) translation by qualified translator; (2) revision by a second qualified
translator who edits without reference to the source for fluency, then compares
against the source for accuracy; (3) proofreading in the target language for
typographic and formatting errors; (4) client review for domain-specific
terminology if required.

Collapsing all four roles to a single individual is a quality reduction that
must be disclosed to the client, not an equivalent alternative.

### Reviewer Independence

The reviewer must not be the same individual as the translator. Reviewer and translator
independence is a structural requirement, not a preference. When resource constraints
force a single-translator workflow, the QA process must document the exception and
the client must accept the quality ceiling in writing.

### Back-Translation as Blunt Instrument

Back-translation (translating the target back into the source to compare with the
original) is a quality check used in clinical, pharmaceutical, and survey-instrument
translation. It is a blunt instrument: it detects gross meaning errors but misses
register drift, terminology inconsistency, and stylistic failures. Back-translation
is a supplement to — not a substitute for — independent revision by a qualified
target-language reviewer.

### Objective Metrics

| Metric | Application | Notes |
|---|---|---|
| SAE J2450 | Automotive and technical translation error classification | 7 error categories; severity weighting; suitable for MT+MTPE quality auditing |
| LISA QA Model | General-purpose translation error classification | Predecessor to MQM; still in use at some enterprise LSPs |
| MQM (Multidimensional Quality Metrics) | Fine-grained error taxonomy for high-stakes content | ISO 21720 successor; preferred for pharmaceutical, legal, and regulated content |
| BLEU / ChrF (MT evaluation) | Automated MT output scoring against human reference | Automated scores do not predict human judgement quality; use only as a signal, not a gate |

## Anti-patterns

| Anti-pattern | Description | Consequence |
|---|---|---|
| Non-native target production | Assigning translation to a non-native target-language speaker | Pragmatic errors, unnatural phrasing, register miscalibration throughout |
| Register drift | Translating meaning correctly but shifting register (formal → informal, technical → plain) | Document loses its legal force, brand voice, or clinical precision |
| Raw-MT delivery | Delivering unedited MT output as a final client deliverable without disclosure | Terminology errors, mistranslations, and hallucinated content in the target |
| Glossary bypass | Translators producing terminology without consulting or updating the approved glossary | Terminology inconsistency across documents, versions, and translators |
| Transcreation scoped as translation | Briefing a creative content project as word-count translation | Either a literal translation (wrong output) or an underpriced transcreation (burned-out resource) |
| Uncertified certified delivery | Delivering a translation as "certified" without a sworn translator or compliant certifying statement | Legally invalid document; may be rejected by court, regulator, or consulate; may constitute fraud |
| Reviewer = translator | Using the translator as their own reviewer | Systematic error propagation; cognitive entrenchment prevents finding own errors |
| Domain substitution | Using a translator qualified in one domain to translate content in an adjacent domain | Terminological errors that may have legal, safety, or regulatory consequences |

## Cross-References

- `domains/i18n-business/skills/cultural-intelligence` — cultural adaptation and
  market-specific communication norms that inform transcreation scoping and
  register decisions.
- `domains/marketing-global/skills/content-creator` — brand voice discipline and
  creative brief structures applicable when scoping transcreation engagements.

## ADR Anchors

- ADR-058 — domain skill authoring standards: declarative voice, no emojis, no
  second-person, house-voice compliance. This skill is authored under that standard.
