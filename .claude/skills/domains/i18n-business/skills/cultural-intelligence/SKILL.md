---
name: cultural-intelligence
description: |
  Cross-cultural business strategy discipline for international operations,
  partnerships, and multicultural teams. Covers Hofstede six-dimension model,
  Trompenaars seven-dimension model, and Lewis triangle — calibrated to
  business contexts (negotiation, leadership, team structure, conflict).
  Applies high-context vs. low-context communication frameworks to meeting
  design, written communication, and escalation paths. Enforces cultural-bias
  awareness: own-culture default is a failure mode, not a baseline. Use when:
  designing a cross-border negotiation strategy; onboarding a multicultural
  team; diagnosing communication breakdown across national cultures; selecting
  a mediator style for cross-cultural conflict; or reviewing business documents
  for implicit cultural norm projection.
owner: Cultural Intelligence Strategist (domain persona)
tier: domain:i18n-business
scope_tags: [cultural-intelligence, cross-cultural, hofstede, trompenaars, high-context, multicultural-teams]
inspired_by:
  - source: msitarzewski/agency-agents/specialized/specialized-cultural-intelligence-strategist.md@783f6a72bfd7f3135700ac273c619d92821b419a
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
  - "**/cross-cultural/**"
  - "**/negotiations/**"
  - "**/culture/**"
---

# Cultural Intelligence

## Cardinal Rule

No cross-cultural recommendation may assert that a specific behaviour,
communication pattern, or negotiation stance applies to a national or
regional culture without citing the dimensional model, primary source, or
empirical study that supports the claim. Cultural generalisations stated as
facts without evidentiary basis are rejected at the two-pass review gate
(ADR-058).

## Fail-Fast Rule

Stop and return a structured failure when any of the following is true:

- The target culture has been identified only at continental level (e.g.,
  "Asian culture", "Latin culture") without country or sub-group specification;
  continental generalisations produce noise, not actionable guidance.
- Dimensional model data for the relevant culture pair is unavailable or
  more than ten years out of date for a high-change context.
- The business context (negotiation type, team structure, conflict category)
  has not been specified; cultural frameworks applied without context produce
  undifferentiated output.
- The analyst's own cultural background has not been stated; positionality
  shapes interpretation in cross-cultural work as reliably as in ethnography.

Never project the low-context norm as the default and describe deviation from
it. Low-context communication is one pole of a dimension, not the reference
standard.

## When to Apply

Apply this skill when:

- Preparing a negotiation strategy for a counterpart from a national culture
  materially different from the analyst's own.
- Diagnosing communication or coordination friction in a multicultural team
  when standard root-cause analysis has not located the problem.
- Designing meeting cadence, decision protocols, or escalation paths for a
  cross-border team spanning three or more national cultures.
- Reviewing business correspondence, contracts, or presentations for implicit
  cultural assumptions that may alienate or confuse the intended audience.
- Selecting a conflict-resolution approach when parties hold divergent norms
  about directness, face, and third-party involvement.
- Evaluating whether a product's onboarding, support, or marketing copy
  projects one cultural norm onto a globally diverse user base.

Do not apply this skill as a substitute for language localisation or legal
jurisdiction analysis; route those to `domains/i18n-business/skills/french-consulting`,
`domains/i18n-business/skills/korean-business`, or the relevant jurisdiction
skill.

## Cultural Dimensions Frame

Three frameworks dominate practitioner use in business contexts. Selection
depends on the analysis depth and the availability of scored data for the
cultures under examination.

### Hofstede Six-Dimension Model

Geert Hofstede's model (original 1980; extended to six dimensions 2010 with
Minkov) provides country-level scores on six dimensions derived from large-N
survey data across IBM subsidiaries.

| Dimension | Low Score Implication | High Score Implication |
|---|---|---|
| Power Distance (PDI) | Flat hierarchies; subordinates expect consultation | Steep hierarchies; authority is respected without question |
| Individualism vs. Collectivism (IDV) | Group loyalty and in-group/out-group distinction are primary | Individual achievement and self-reliance are primary |
| Masculinity vs. Femininity (MAS) | Cooperation, care, and work-life balance are valued norms | Competition, assertiveness, and performance are valued norms |
| Uncertainty Avoidance (UAI) | Ambiguity is tolerable; improvisation is acceptable | Rules, structure, and predictability are required |
| Long-Term vs. Short-Term Orientation (LTO) | Respect for tradition; short-term results matter | Investment in future; thrift and persistence are virtues |
| Indulgence vs. Restraint (IVR) | Impulse control; social norms suppress gratification | Relatively free gratification of human drives |

When to use Hofstede: when country-level scored data is needed for a
large-N comparison; when the analysis concerns hierarchical authority,
individual vs. team incentive design, or rule vs. relationship orientation.
Primary limitation: data collected in corporate employment context; scores
may not generalise to all social strata or all business sectors.

### Trompenaars Seven-Dimension Model

Fons Trompenaars and Charles Hampden-Turner's model ("Riding the Waves of
Culture", 1993; updated 2012) focuses on how cultures resolve universal
dilemmas. Seven dimensions, five of which concern relationships between people.

| Dimension | Pole A | Pole B |
|---|---|---|
| Universalism vs. Particularism | Rules apply equally regardless of relationship | Relationships and context modify rule application |
| Individualism vs. Communitarianism | Individual rights and decisions are primary | Group rights and consensus are primary |
| Specific vs. Diffuse | Work and personal spheres are separate | Work and personal spheres overlap; whole person is engaged |
| Neutral vs. Affective | Emotions are not expressed in professional context | Emotions are openly expressed in professional context |
| Achievement vs. Ascription | Status derives from accomplishment | Status derives from position, age, connection, or birth |
| Sequential vs. Synchronic (Time) | Time is linear; one task at a time; punctuality is respect | Time is parallel; multiple threads; relationships override schedules |
| Internal vs. External Control | People control their environment and outcomes | Outcomes are shaped by external forces; adaptation is primary |

When to use Trompenaars: when the analysis concerns relationship-building
pace, the role of personal connection in contract enforcement, or emotional
expression norms in meetings. Primary limitation: smaller sample than
Hofstede; strong consulting-context bias.

### Lewis Triangle

Richard Lewis's CultureActive model ("When Cultures Collide", 1996; updated
2018) classifies cultures into three communication and behaviour types:
Linear-active, Multi-active, and Reactive — positioned on a triangle, with
most national cultures occupying intermediate positions.

| Type | Core Behaviour | Characteristic Communication |
|---|---|---|
| Linear-active | Planned, task-oriented, data-driven; completes one action before the next | Direct, concise, fact-first; written records preferred |
| Multi-active | Relationship-oriented, emotional, simultaneously manages multiple threads | Verbose, narrative, relationship-first; oral preference |
| Reactive | Listens before speaking; consensus and face-saving primary; indirect feedback | Understated, context-rich; silence carries meaning |

When to use Lewis: when rapid cultural orientation is needed for communication
style and meeting design, especially for cultures that occupy intermediate
positions not well-differentiated by Hofstede (e.g., Finland and Japan both
score low on MAS but differ substantially in communication style). Primary
limitation: less empirically anchored than Hofstede; practitioner model.

### Framework Selection Guidance

Use Hofstede when scored country data is available and the analysis concerns
structural factors (hierarchy, individualism, uncertainty tolerance). Use
Trompenaars when the analysis concerns relationship dilemmas and contract
vs. trust orientation. Use Lewis when the primary question is communication
style and meeting behaviour. Apply multiple frameworks when they converge;
document divergence explicitly when they conflict.

## High-Context vs. Low-Context Communication

Edward Hall's high-context / low-context distinction ("Beyond Culture", 1976)
describes how much meaning is embedded in context, relationship, and
non-verbal signal versus made explicit in the message itself.

| Dimension | Low-Context | High-Context |
|---|---|---|
| Meaning location | In the words; explicit | In the context; implied |
| Communication style | Direct, specific, literal | Indirect, allusive, metaphorical |
| Written vs. oral | Written records are binding | Oral agreements carry weight; relationship confirms commitment |
| Ambiguity tolerance | Ambiguity is a problem to eliminate | Ambiguity can be a feature; preserves flexibility |
| Feedback style | Corrective feedback is given directly and specifically | Negative feedback is indirect; positive framing carries negative signal |

Critical operating rule: the analyst must never treat low-context as the
neutral default. Framing high-context communication as "indirect", "vague",
or "difficult" without specifying the reference frame imports a low-context
bias into the analysis.

### Implications for Business Communication Design

Meeting structure: in low-context cultures, an agenda distributed in advance
with explicit decision ownership and action-item capture is the expected form.
In high-context cultures, pre-meeting relationship-building and informal
consensus formation (nemawashi in Japanese business contexts; keirogi in
Korean) often precede the formal meeting, which confirms rather than forms
decisions. Designing meeting structure without accounting for this distinction
produces meetings that feel either brutally transactional or confusingly
inconclusive depending on the cultural frame.

Written communication: in low-context cultures, email is authoritative; lack
of response signals absence of objection only if explicitly agreed. In
high-context cultures, the absence of explicit objection in email may signal
discomfort that requires a separate oral channel to surface. Silence is not
consent; silence is a signal requiring interpretation.

Escalation paths: direct escalation over a peer's head is standard in
low-context cultures when a decision is blocked. In high-context cultures,
direct escalation constitutes a face-threatening act. Escalation should
route through a relationship intermediary or be preceded by a private
conversation with the peer.

## Negotiation Across Cultures

### Relationship-First vs. Deal-First

Cultures differ fundamentally on whether trust is a precondition for the
deal or a product of the deal.

Relationship-first cultures (common in high-context, particularist, and
multi-active clusters): the business relationship must be established before
commercial terms are seriously discussed. Investment in meals, visits, and
personal exchange is not a preamble to negotiation — it is the first stage
of negotiation. Attempting to accelerate to commercial terms before the
relationship is established signals untrustworthiness.

Deal-first cultures (common in low-context, universalist, and linear-active
clusters): credibility is established through the quality of the proposal
and the professionalism of the process. Prolonged relationship-building
investment before commercial terms can signal time-wasting or lack of
seriousness.

Misalignment pattern: deal-first party sends a detailed term sheet on
first contact; relationship-first party interprets this as presumptuous
and untrustworthy. Relationship-first party invests two meetings in
personal exchange before discussing commercial terms; deal-first party
interprets this as inefficiency or evasion.

### Signing vs. Handshake

In universalist cultures, the signed contract is the binding commitment.
Renegotiation after signing is bad faith.

In particularist cultures, the relationship is the commitment. The contract
records the current state of the relationship but is expected to be
renegotiated if circumstances change. Insisting on strict contract terms
when circumstances have changed is perceived as prioritising paper over
partnership.

The practical implication: when entering a long-term agreement with a
particularist counterpart, build a relationship management protocol into
the contract structure rather than assuming the written terms will govern
without ongoing relationship maintenance.

### Concession Patterns

Linear-active negotiators typically front-load concessions: make a
calculated initial offer with room to concede, reach agreement through
explicit positional bargaining.

Multi-active negotiators may make concessions as relationship signals,
not as positional trades. A concession offered early may signal desire
for a long-term relationship rather than willingness to concede further.
Interpreting it as a positional opening and pressing for additional
concessions damages the relationship signal.

Reactive negotiators (e.g., Japanese business contexts) may not
explicitly reject positions. Hesitation, extended silence, or redirecting
to a different topic signals disagreement. Failure to read these signals
produces impasse that is invisible to the deal-first party.

## Multicultural Team Dynamics

### Psychological Safety Across Cultures

Psychological safety (the belief that one can speak without fear of
punishment or humiliation — Edmondson 1999) is universally valuable but
is expressed and built differently across cultures.

In low power-distance cultures, psychological safety is built through
explicit invitation: asking for dissenting views, modeling vulnerability
from leaders, and publicly acknowledging when a senior person was wrong.

In high power-distance cultures, the same explicit behaviors can be
perceived as theatrically performative or as a trap. Safety is built
through predictability: consistent, non-punitive responses to disclosed
problems over time, not a single meeting exercise.

Diagnostic: if team members from high power-distance cultures consistently
under-contribute in group settings but surface detailed concerns in
one-on-one conversations, the psychological safety gap is the likely cause.
The fix is structural (smaller groups, written input channels, pre-circulated
questions) not motivational.

### Linguistic Accommodation

In multilingual teams, the dominant-language speaker has an obligation to
reduce their speaking pace, avoid idiomatic expressions, and allow longer
pauses before assuming silence means assent. This is not a courtesy; it
is a validity requirement for the team's decision process.

Idioms from any national culture (sports metaphors, food metaphors,
political references) should be replaced with literal equivalents in
cross-cultural communication. Exclusion of team members through
in-group linguistic signals is a team-process failure, not a social
preference.

### Meeting Cadence Variance

Punctuality norms, acceptable meeting duration, the role of small talk,
and expected follow-up cadence vary across national cultures in ways
that produce friction on multicultural teams even when task alignment
is high.

Explicit team agreements on these operational norms — not assumed
convergence on the dominant culture's defaults — are required for
multicultural team functioning. The agreement itself is the artifact,
not the specific norms chosen.

## Conflict Resolution

### Face-Saving Cultures vs. Direct Cultures

Face (mianzi in Chinese contexts; kibun in Korean contexts; tatemae/honne
in Japanese contexts) is not vanity. Face is a social resource that
enables the holder to function effectively in their community. An act
that causes face loss impairs the other party's operational capacity.

In face-sensitive cultures, direct confrontation in group settings is
a face-threatening act regardless of content. The appropriate channel
for substantive disagreement is a private conversation, not a public
meeting. Delivering criticism in a group meeting does not demonstrate
decisiveness; it produces an opponent.

In direct cultures, private diplomacy before a group meeting can be
perceived as backroom maneuvering, coalition-building, or lack of
transparency. Conflict raised for the first time in a private channel
may feel manipulative rather than considerate.

### Written vs. Verbal Resolution

In low-context cultures, written communication is the preferred channel
for conflict resolution: it creates a record, forces precision, and
allows both parties to compose responses without time pressure.

In high-context cultures, written confrontation is a face-threatening
escalation. Verbal resolution — in the right relational context —
preserves flexibility and does not create a permanent record of the
conflict.

The conflict resolution channel should match the cultural preference of
the party who holds the larger face-loss exposure in the conflict.
Default to verbal unless the parties share a low-context operating norm.

### Mediator Role

In cultures with high uncertainty avoidance and high collectivism, a
trusted third party as mediator is not a sign of impasse — it is the
preferred first step. The mediator's role is not to adjudicate but to
allow both parties to surface positions without direct confrontation.

The mediator should be selected from a relationship network trusted by
both parties, not appointed unilaterally by one. Unilateral mediator
appointment is perceived as a power move, not a facilitation offer.

## Cultural Bias Awareness

### Own-Culture Default Detection

The own-culture default failure mode: the analyst assumes their own
cultural norms are the neutral reference and describes the counterpart
culture in terms of deviation from that norm. Manifestations:

- Describing a culture as "indirect" (implicit reference: the analyst's
  culture is direct, and directness is the standard).
- Describing a culture as "hierarchical" (implicit reference: the analyst's
  culture is flat, and flatness is the standard).
- Describing a negotiation as "taking too long" (implicit reference: the
  analyst's timeline preference is the valid one).

Correction procedure: restate every cultural characterisation in both
directions. If one culture is "direct", the other is not "indirect" —
it is "high-context". If one culture is "hierarchical", the other is not
"flat" — it is "low power-distance". Neither pole is the neutral standard.

### Ethnocentrism vs. Cultural Relativism

Ethnocentrism (evaluating other cultures by one's own standards) is a
validity threat in cross-cultural analysis, not a moral failing. The
corrective is the cultural-relativism discipline: describe practices as
solutions to problems before evaluating them as superior or inferior.

Cultural relativism is a methodological stance during the analysis phase.
It does not require suspension of judgment on practices that cause
substantive harm. The discipline is: describe accurately first; evaluate
informed by that description second.

### Ethics Floor

Cultural relativism has an ethics floor: practices that cause substantive
harm to persons — regardless of cultural normalisation — are not exempted
from evaluation by the relativism discipline. The ethics floor is not
determined by the analyst's national culture; it is determined by
internationally recognised human rights standards (UDHR, ILO conventions)
and the applicable legal jurisdiction.

## Anti-patterns

| Anti-pattern | Description | Correct Approach |
|---|---|---|
| Stereotyping individuals | Applying group-level dimensional scores to an individual counterpart without observation ("She is Japanese so she will be indirect") | Use dimensional models to generate hypotheses for observation; confirm or disconfirm against the individual's actual behaviour |
| Assumed-norm imposition | Designing processes, communications, or conflict resolution around the analyst's own cultural defaults without acknowledgement | Identify the cultural baseline being assumed; make it explicit; check whether it is shared by all parties |
| Single-dimension reduction | Characterising a culture's entire business orientation from one dimension score (e.g., "High PDI, so they are hierarchical, so authority must be invoked") | National cultures are multi-dimensional; multiple dimensions interact; document which dimensions are most salient for the specific context |
| Cultural-fluency theater | Performing cultural knowledge (citing Hofstede scores, using local greetings) without adapting substantive behaviour | Fluency is in structural adaptation — meeting design, escalation paths, communication channels — not in surface-level vocabulary or etiquette |
| Continent-level generalisation | "In Asia, relationships come first" — treating a continent as a culture | Specify the country, business sector, and organisational generation; intra-continental variance is as large as inter-continental variance in many dimensions |
| Treating cultural dimensions as static | Applying Hofstede 1980 data to contemporary business practice without checking for generational or sector-level drift | Note the data vintage; for high-change contexts (rapid urbanisation, generational shift, post-merger integration), treat dimensional scores as hypotheses requiring field validation |
| Assuming convergence to Western norms | Predicting that globalisation or English-medium business will homogenise behaviour toward low-context, low-PDI, individualist defaults | Convergence is partial and selective; many high-context and high-PDI norms persist in global business contexts even among English-fluent counterparts |

## Cross-References

- `domains/i18n-business/skills/french-consulting` — for France-specific
  business culture, communication norms, and negotiation patterns;
  the general dimensional model in this skill contextualises but does not
  replace country-specific guidance.
- `domains/i18n-business/skills/korean-business` — for Korean business
  culture, hierarchical norms, pali-pali urgency culture, and nunchi
  reading; dimensional frameworks in this skill provide the structural
  framing; country skill provides operational specifics.
- `domains/academic-humanities/skills/anthropologist` — for ethnographic
  fieldwork methods when cross-cultural business analysis requires
  primary research; this skill provides dimensional frameworks; the
  anthropologist skill provides observation and reflexivity discipline.

## ADR Anchors

- **ADR-058 (Brainstorm gate + two-pass adversarial review):** cross-cultural
  strategy documents, negotiation briefs, and team-design recommendations
  produced under this skill are analytical artifacts requiring the two-pass
  review defined in ADR-058 §BORROW-2. The first pass reviews completeness:
  are all relevant cultural dimensions identified, are sources cited, has the
  analyst's own cultural positionality been stated? The second pass reviews
  from an adversarial frame: specifically challenging whether own-culture
  defaults have been imported, whether dimensional model limitations have been
  acknowledged, and whether the recommendation is actionable in the specific
  operational context. The deliverable must not be circulated until both passes
  are complete and any blocker findings are resolved.
