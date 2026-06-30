---
name: voice-ai-integration
description: >
  Production discipline for voice AI integration covering ASR provider
  selection (Whisper-large / AssemblyAI / Deepgram / Speechmatics /
  Google STT) by accuracy, latency, pricing, and language coverage; TTS
  provider selection (ElevenLabs / OpenAI / Cartesia / Azure Neural /
  Google Cloud TTS) with latency-to-first-byte and emotional control
  tradeoffs; real-time streaming via WebRTC and WebSocket with partial
  transcription and jitter buffer configuration; speaker diarization with
  error rate budgets; end-to-end latency budgets anchored to hard numbers;
  conversational state management with barge-in and VAD; fallback handling
  across provider degradation events; and PII redaction, consent recording,
  and LGPD/GDPR compliance per jurisdiction. Use when: designing or
  reviewing a voice pipeline, selecting ASR or TTS providers, defining
  latency SLAs, architecting real-time audio streaming, or auditing
  transcript privacy and retention controls.
owner: Rafael Drummond (Voice AI Integration Engineer, domain persona)
tier: domain:voice-ai
scope_tags: [voice-ai, asr, tts, diarization, real-time-audio, webrtc, latency-budget]
inspired_by:
  - source: msitarzewski/agency-agents/engineering/engineering-voice-ai-integration-engineer.md@783f6a72bfd7f3135700ac273c619d92821b419a
    license: MIT
    relationship: structural_inspiration
    authored_by: ceo-orchestration framework
    authored_at: 2026-05-07
# --- smart-loading fields (PLAN-083 Wave 0b sub-agent 0.7c) ---
domain: voice-ai
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
  - "**/voice/**"
  - "**/asr/**"
  - "**/tts/**"
  - "**/webrtc/**"
  - "**/diarization/**"
---

# Voice AI Integration

## Cardinal Rule

Latency and accuracy are measured, not assumed. Every voice pipeline
component carries a hard number — end-to-end conversational response
must remain below 800 ms, ASR partial results within 200 ms of speech
offset, synthesis time-to-first-byte within 200 ms of inference output.
Any component claiming acceptable latency without a benchmark run under
realistic load is not acceptable. "Feels fine" is not an SLA. Record
the measurement methodology alongside the number so regressions can be
detected in CI before reaching production.

---

## Fail-Fast Rule

A voice pipeline MUST NOT enter production without satisfying the
following four gates: (1) WER is measured against a domain-specific
holdout set — not the provider's published general-language benchmark;
(2) end-to-end latency has been measured at p95 under concurrent load,
not just median in isolation; (3) PII redaction runs as a named,
independently testable pipeline stage before any transcript is written
to persistent storage or delivered downstream; (4) provider failover
has been exercised by injecting a provider error and confirming
graceful degradation rather than silent failure. If any gate is
unverified, the pipeline is not production-ready.

---

## When to Apply

Activate this skill when the work involves any of the following:

- Selecting an ASR provider for a new or migrated voice pipeline.
- Selecting a TTS provider for speech synthesis in a conversational or
  broadcast context.
- Designing or reviewing real-time audio streaming architecture via
  WebRTC or WebSocket.
- Defining latency budgets or SLAs for a conversational AI product.
- Implementing or auditing speaker diarization in a multi-participant
  recording pipeline.
- Adding barge-in, interruption recovery, or full-duplex audio to a
  voice interface.
- Designing fallback and graceful degradation paths for provider
  outage or confidence-threshold failures.
- Reviewing transcript privacy controls, consent recording, or
  retention policies under LGPD, GDPR, or wiretap statutes.

Skip when: the task is pure NLP over pre-existing text transcripts
(no audio path); the integration is a single-call transcription batch
job with no latency requirement and no PII exposure; or the context
is media subtitle generation for a pre-recorded non-interactive asset
(use a batch transcription pattern instead).

---

## ASR Provider Selection

Provider selection is a function of four independent axes. Choose one
axis as the binding constraint before evaluating the others.

Select one axis as the binding constraint before evaluating the others.

WER claims from providers are measured on clean studio benchmarks. Every
deployment must benchmark WER on a domain-specific holdout set — at minimum
60 utterances representing actual speakers, vocabulary, accents, and
recording conditions of the target use case.

| Provider | WER (clean) | Streaming | Notes |
|---|---|---|---|
| Whisper large-v3 (local) | 3–7% | No native stream | GPU required; no network RTT |
| Deepgram Nova-2 | 5–9% | Yes, stable partials | Strong telephony tuning |
| AssemblyAI Universal-2 | 6–10% | Yes, partials revise | Diarization bundled |
| Speechmatics | 7–12% | Yes | Best multilingual coverage |
| Google STT v2 | 8–14% | Yes, interim results | Wide language coverage |

For accented, domain-specific, or noisy audio these rankings shift
materially. Benchmark on actual production audio before committing.

Pricing: all cloud providers charge per audio-minute; rates shift at volume
tiers. Hybrid routing (local Whisper for sensitive or high-volume workloads;
cloud for burst or language gaps) is valid when routing complexity is
justified by volume.

Language: Speechmatics provides the broadest certified multilingual coverage.
Whisper large-v3 supports 99 languages but quality degrades below the top 20
by training corpus size. Deepgram and AssemblyAI are strong in English and
Spanish; limited certification elsewhere. Benchmark WER per language
independently for multilingual deployments.

---

## TTS Provider Selection

TTS selection depends on voice identity requirements, latency budget,
and whether emotional or prosodic control is required.

| Provider | TTFB (ms) | Cloning | Notes |
|---|---|---|---|
| Cartesia | 80–200 | Yes | Lowest TTFB; streaming-first |
| ElevenLabs | 100–300 | Yes (custom voice) | Highest naturalness; consent required |
| Azure Neural TTS | 150–350 | Yes | Enterprise SLA; SSML emotional control |
| Google Cloud TTS | 150–400 | No | Wide language coverage |
| OpenAI TTS | 200–400 | No | Simple API; preset voices |

TTFB target: synthesized speech must begin playing within 200 ms of
inference completion. Providers with median TTFB above 400 ms under load
require buffering strategies that degrade conversational responsiveness.

Voice cloning requires explicit consent from the voice subject. Retain
consent artifacts for the lifetime of any cloned voice asset. Synthesizing
a recognizable voice without consent creates legal exposure in most
jurisdictions.

---

## Real-Time Streaming

### WebRTC vs WebSocket

WebRTC is the correct choice for browser-to-server audio when
sub-300 ms round-trip latency is required. It provides built-in
adaptive bitrate, jitter buffer management, and DTLS-SRTP encryption.
The operational cost is higher: STUN/TURN server infrastructure,
ICE negotiation latency on connection establishment, and complexity
in NAT traversal for mobile clients.

WebSocket is the correct choice when the audio source is a server-side
process, a mobile SDK with direct control over encoding, or any context
where WebRTC's ICE negotiation overhead is unacceptable for use-case
latency. WebSocket requires explicit jitter buffer implementation in
the application layer.

Do not choose based on familiarity. Choose based on whether the audio
source is a browser (WebRTC) or a server-side or native SDK (WebSocket).

### Chunked Transcription, Partials, and Jitter Buffer

Send audio in fixed-size chunks (100–250 ms). Below 80 ms, per-request
overhead grows without proportional latency reduction. Partial results are
not final — they may revise on the next final event. Do not commit a
partial result to a database record or downstream action; wait for the
final-result flag.

For WebSocket pipelines, implement a jitter buffer of 150–300 ms before
passing audio to the ASR engine. Target depth: two to three times the
observed p95 packet inter-arrival jitter, measured under load.
Undersized buffers produce gap artifacts that degrade WER silently.

---

## Speaker Diarization

### Online vs Offline

Online diarization (streaming, low-latency) operates on a rolling
window and produces approximate speaker boundaries. It degrades on
cross-talk and requires a speaker-count assumption for best results.
Use for near-real-time applications where latency matters more than
boundary precision.

Offline diarization (batch, post-transcription) runs on the full
recording and produces higher-accuracy boundaries. Use for call
analytics, meeting transcripts, and compliance recordings where
precision matters more than latency.

### Speaker Count Assumption

Provide the expected speaker count when known. Diarization models
that estimate speaker count from audio produce materially higher
diarization error rates (DER) when the audio contains more than
four speakers or any cross-talk. If speaker count is unknown and
cross-talk is expected, budget for a DER of 15–25% and route
low-confidence segments for human review.

### Cross-Talk and DER Budget

Segments with two or more overlapping speakers cannot be reliably
attributed. Flag them explicitly in the output schema — do not silently
assign to whichever speaker model heuristics select.

DER targets (measured on a domain-representative holdout set, not
provider benchmark corpora):

- Clean single-microphone, low overlap: DER < 5%.
- Telephony or multi-participant: DER < 12%.
- High-overlap or noisy: DER < 20%, with manual review routing for
  flagged segments.

---

## Latency Budgets

End-to-end conversational latency (speech-offset to synthesized-audio
play-start) must remain below 800 ms for natural conversational feel.
Allocate the budget across pipeline components:

| Component | Budget | Notes |
|---|---|---|
| ASR partial first result | ≤ 200 ms | From speech onset; streaming required |
| ASR final result | ≤ 400 ms | From end of utterance |
| Inference / LLM call | ≤ 300 ms | First token; streaming generation |
| TTS time-to-first-byte | ≤ 200 ms | From inference first-token |
| Audio delivery to client | ≤ 50 ms | Network; WebRTC/WebSocket buffer |
| **Total end-to-end** | **≤ 800 ms** | **p95 target under load** |

Budgets are measured at p95 under concurrent load, not median in
isolation. Overage in any single component must be compensated by
reducing budget in an adjacent component — the total envelope does
not flex. If the 800 ms target cannot be met, document the actual
p95 measurement and the technical constraint preventing compliance.
Never accept "feels fine."

---

## Conversational State Management

### Turn-Taking and Barge-In

Maintain explicit turn state: LISTENING, PROCESSING, SPEAKING.
Transition logic must be deterministic — combine VAD silence threshold
with a configurable end-of-utterance timeout (300–500 ms typical;
tune to domain speech patterns). Do not rely on silence alone.

Barge-in: the system must stop synthesis and return to LISTENING when
VAD detects speech onset during a synthesized response. Implement by
(1) keeping the ASR streaming session active during synthesis, (2)
triggering synthesis cancellation on VAD onset above threshold, (3)
discarding buffered TTS audio beyond the cancellation point. Barge-in
without synthesis cancellation produces overlapping audio — users
interpret this as a broken product. Do not ship without it.

### Interruption Recovery

When barge-in fires, preserve the generation state (partial LLM response
at the interruption point, turn context). Log the cut point; resumption
logic determines whether to continue the interrupted response or discard
it based on the new user utterance.

---

## Fallback Handling

### Provider Degradation and ASR Confidence

Monitor ASR and TTS provider health via p95 latency and error rate.
Circuit-breaker: if ASR error rate exceeds 5% in a 60-second rolling
window, switch to secondary; return to primary after 120 s of
below-threshold operation. Route provider-switch events to the
observability pipeline — silent failover is acceptable UX but
unacceptable operationally.

When ASR returns confidence below threshold (starting point: 0.7 on
0–1 scale), trigger a clarification prompt rather than proceeding on
uncertain input. In high-stakes contexts (medical, financial, legal),
do not silently proceed on low-confidence segments. Configure the
threshold per domain.

### TTS Failover and Offline Impossibility

Pre-configure a failover voice and validate it is intelligible in the
deployment language before it is needed. Do not dynamically select an
untested voice on failover.

Cloud-dependent voice pipelines cannot degrade to a fully offline mode —
the capability disappears with the provider. Design for graceful
degradation: surface a clear message when no provider is reachable;
preserve conversation context so the session can resume when connectivity
returns.

---

## Privacy and Compliance

### PII Redaction

PII redaction must run as a named, independently testable pipeline
stage before any transcript is written to persistent storage or
delivered to a downstream consumer. Redaction must be configured, not
assumed. Test the redaction stage independently with known PII fixtures:
phone numbers, CPF/CNPJ (Brazil), SSN patterns, credit card numbers,
names in context.

Do not treat redaction as an output filter. Run it as an intermediate
stage so that confidence scores on redacted segments are preserved for
audit — the model output is immutable, the stored transcript is redacted.

### Consent Recording per Jurisdiction

- Brazil (LGPD): informed consent required; purpose specified at collection;
  consent artifact retained for the lifetime of the recording.
- EU/EEA (GDPR): lawful basis required; data subject right to erasure;
  cross-border transfer requires adequacy decision or SCCs.
- United States: wiretap law varies by state; California, Connecticut, and
  Maryland require all-party consent; federal one-party consent does not
  supersede stricter state law.

Consent capture and artifact storage are first-class pipeline components.

### Storage Retention

Define retention windows per data class: raw audio (30-day default unless
a specific requirement extends), redacted transcript (longer acceptable,
linked to consent artifact), speaker embeddings (biometric data under LGPD
and GDPR; explicit consent required; shorter windows). Automated deletion
must be implemented and tested — transcripts beyond policy window create
compliance liability regardless of access history.

---

## Anti-Patterns

| Anti-Pattern | Why It Fails |
|---|---|
| Skipping jitter buffer configuration | Network variability creates audio gaps that degrade ASR WER without any error signal; failure is silent |
| Accepting provider WER claim without domain benchmark | Published benchmarks use clean studio audio; production WER on telephony or multi-accent audio is typically 2–4× higher |
| Single-provider dependency with no failover | Provider outages are not rare; a voice pipeline with no secondary provider has zero availability during provider incidents |
| Missing barge-in implementation | Users interpret overlapping synthesized speech as a broken product; full-duplex without barge-in is not shippable |
| PII redaction as output filter only | If redaction fails silently, unredacted PII reaches persistent storage; redaction must be a verifiable intermediate stage with test coverage |
| Treating silence as end-of-utterance sole signal | VAD false positives on pauses inside long utterances cause premature turn switches; combine with configurable timeout |
| Using partial ASR results as committed output | Partials revise on finalization; committing a partial to a downstream action or database record produces incorrect or duplicate data |

---

## Cross-References

- `core/security-and-auth` — authentication patterns for API key management
  to ASR and TTS provider endpoints; credential rotation discipline.
- `core/compliance-lgpd` — LGPD data subject rights implementation, consent
  artifact storage, and purpose limitation for audio and transcript data.
- `core/architecture-decisions` — ADR lifecycle for provider selection
  decisions and latency budget commitments that cross architectural
  boundaries.

---

## ADR Anchors

Decisions affecting provider selection, latency SLAs, PII handling, or
consent architecture MUST be recorded as ADRs.

- **ADR-058** (Brainstorm Gate and Two-Pass Review) — provider-selection
  decisions, latency-budget changes, and adapter-pattern code are all
  subject to two-pass adversarial review before deployment.
- **Adapter layer pattern (project-internal):** voice provider clients
  wrapped behind an adapter interface to enable failover and
  substitution without upstream code changes (project-specific ADR
  authored at adoption time).
- **Provider selection ADR:** evaluated alternatives, WER benchmark
  methodology, binding constraint, decision. Updated on every provider
  change.
- **Latency budget ADR:** 800 ms target, per-component allocation,
  measurement methodology, approved exceptions with stated constraint.
- **PII and consent ADR:** redaction stage design, retention windows per
  data class, consent capture mechanism, jurisdiction scope.
