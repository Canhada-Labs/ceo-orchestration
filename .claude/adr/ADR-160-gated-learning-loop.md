# ADR-160: Gated Learning Loop — metadata-only observation, fail-closed promotion, chain-anchored approval

**Status:** ACCEPTED (2026-07-10 — flipped at the SENT-F landing ceremony:
Owner GPG signature (AE9B…0335DC74) → scope==touched assert (∅, 42 files)
→ overlay apply → CI-equivalent gates green; the SENT-E precedent from
ADR-158/159. Drafted S265 2026-07-09 in the PLAN-154 Wave-0 run.)
**Date:** 2026-07-09
**Decision drivers:** the ecc comparative analysis (PLAN-153/artifacts)
identified a passive learning funnel (observe → distill → candidate →
recall) worth importing as a CLASS; the lesson store lives under `$HOME`
outside every repo guard while its content is injected into `/ceo-boot`
and every ranked spawn — an unguarded write surface feeding two prompt
channels; the HMAC audit chain makes any capture-time leak PERMANENT;
the S254 dead-rail lesson demands new surfaces be born with kill
switches, liveness, and fail-closed security boundaries. PLAN-154
round-1 debate (3× ADJUST_PROCEED → PROCEED, 2026-07-07) bound
adjustments A1–A13; this record carries their normative text.
**Related decisions:** ADR-158 (reserved this index; gate-side
no-op-allowlist + fail-open-rail liveness doctrine that Decision 7
extends), ADR-159 (fail-CLOSED citation-gate semantics that Decision 5
converges with; the Prompt Defense Baseline the distiller spawn must
carry), ADR-040 (credential-leak fail-closed precedent), PLAN-152
debate C4 (fail-open-on-infrastructure / fail-closed-on-input taxonomy,
`check_bash_safety.py` `_e3` precedent), PLAN-125 WS-1
(`tool_lifecycle.py` closed-schema rail this loop extends).
**Sources:** `PLAN-154-gated-learning-loop.md` (binding constraints
1–9), `PLAN-154/debate/round-1/consensus.md` (C1–C10, A1–A19),
`PLAN-154/wave-0-record.md` (pre-registered numbers, §Decision 5).

## Context

The learning loop adds four coupled surfaces: an observe rail extending
`tool_lifecycle.py`, an offline distiller writing PENDING candidates
into the `lessons.py` store, lesson rendering into `/ceo-boot` and the
`format_for_injection` spawn path, and a fact-forcing deny-once gate on
destructive-op retries. Each is individually small; together they form
a pipeline from **attacker-influenceable input** (tool traffic, audit
citations) to **prompt-channel output** (boot text, spawn context).
This ADR fixes the doctrine that makes that pipeline safe to operate,
so that every future widening proposal must argue against named
principles rather than prose.

The endorsed division of labor is kept verbatim from the plan: **"the
human filters for usefulness, the machine for injection."** The
`/lesson-review` human gate is explicitly NOT the injection defense —
mechanical scanning is (constraint 3, endorsed 3/3 in round-1).

## Decision

### 1. Injection-inertness by construction (named principle — A2)

Observation capture is **metadata-only**, defined normatively, not as
prose: a **deny-by-default closed-field allowlist enforced at
CAPTURE** — closed enums, booleans, bounded opaque IDs, and hashes
only. No free-text field may be added without an amendment to THIS
record.

"Redact at read" is **rejected as a posture**: the HMAC chain makes
capture-time leaks permanent, so read-side redaction defends the wrong
end. Capture-time denial is the only control that composes with an
append-only tamper-evident store.

Metadata-only is ALSO the injection control, not just the privacy
floor: **closed-enum input is injection-inert by construction** —
there is no byte sequence an attacker can place in a bounded enum that
survives as instructions. Any future rail-widening proposal must
account for losing BOTH properties (privacy floor AND injection
inertness) — this dual loss is the named cost of widening.

Three CI assertions ship with the rail and are part of this decision:
(a) a frozen schema-hash fixture that reds on ANY field addition until
consciously updated in review; (b) a closed-type emitter gate — no
free-form string passes the emitter; (c) a canary-exfiltration test
(synthetic tool call carrying `CANARY_SECRET_...` in args/output →
zero hits grepping the entire observation store) plus the kill-switch
negative control (env unset → zero filesystem delta).

### 2. The C4 taxonomy applied: promotion fail-CLOSED, telemetry fail-open (A4)

The loop has exactly two postures, assigned by boundary class per
PLAN-152 debate C4:

- **Promotion boundary (security matcher) — fail-CLOSED.** The
  candidate-promotion path (`lessons.add_candidate`) treats scanner
  unavailability the same as a scan hit: the candidate is
  **QUARANTINED** — a TERMINAL state, visible in `/lesson-review`,
  never rendered anywhere, never eligible for PENDING or approval.
  Fixture: broken scanner + promotion attempt → refusal.
- **Observe-write / telemetry side — fail-open.** The advisory
  write-time scan posture (today's `lessons.py` scanner) remains
  acceptable ONLY here, and an audit-emit failure never flips any
  decision anywhere in the loop.

Content the promotion scanner cannot evaluate is blocked, not waved
through — the `_e3` / `_check_credential_leak` precedent applied to a
new boundary.

### 3. The chain is the integrity anchor; the `$HOME` store is untrusted (named principle — A6)

The lesson store lives under `$HOME`, outside every repo guard; a
store-file approval bit alone is a TOCTOU into `/ceo-boot`. Therefore:

- Approval events written to the HMAC chain carry
  `sha256(trigger + advisory_text)` of the approved candidate.
- BOTH render paths — the `/ceo-boot` one-liners AND the
  `format_for_injection` spawn path — recompute the hash and
  **verify-before-render**; a mismatch → drop the lesson + surface an
  integrity flag. Unresolved integrity flags block the Decision-5 flip.
- `created_at` for TTL/decay is verified against the chain's
  `lesson_write` event, never trusted from the `$HOME` file.

The chain, not the mutable file, is the integrity anchor.

### 4. Zero self-activation; deterministic lifecycle (constraint 5 — A9)

Nothing self-activates: candidates are PENDING until `/lesson-review`
human approval; instinct→skill promotion goes only via SP-NNN +
`/skill-review` + soak. TTL 30d on pendings ends in a TERMINAL
**EXPIRED** state (+audit event) — expiry never carries a default
disposition touching activation. The 7-day boot warning is COUNT-ONLY
("N pendings expire in <7d") — zero candidate text, so no pre-approval
text reaches boot through the warning side door. Every time function in
the loop (confidence decay, TTL expiry, warning, dampening windows)
takes an injectable `now_fn` with the wall clock only as default.

### 5. The ADVISORY→ENFORCE flip is a governed event with pre-registered criteria (A8)

The fact-forcing deny-once gate ships shadow-first. The flip to enforce
happens only when ALL of the following hold, **measured from the HMAC
audit log (never from mutable side files)** — pre-registered at PLAN-154
Wave 0 (2026-07-09), verbatim:

- **FP rate < 2% over ≥ 50 gate-candidate events** in shadow (a
  gate-candidate event = the already-matched rare path where the gate
  WOULD deny; an FP = a shadow-deny event whose subsequent retry
  carried a valid citation unchanged — i.e. the deny would have blocked
  a correct command);
- **≥ 14 calendar days** of shadow telemetry elapsed since the first
  shadow event;
- **zero unresolved integrity flags** (hash-mismatch drops, Decision 3)
  in the same window.

These numbers were chosen at Wave 0, not mid-wave; changing them is an
amendment to this record, not a code edit. The flip itself is a
**governed event**: settings-backed, sentinel-scoped, and every
activation change (either direction) emits an HMAC-chain governance
event. Deny-once state binds to `sha256(normalized command)`,
session-scoped, expiring with the session; a retry releases ONLY an
exact-hash match. Release-side verification failure = BLOCK (C4);
fail-open is permitted only on the audit-emit side. Verification runs
only on the rare already-matched path (post-matcher, never the common
path). The deny message states the exact citation format that unlocks
retry (ADR-159 messaging precedent).

### 6. Dampening contract — advisory prose only; exempt channels by name (A10)

Denial dampening (condensing repeated advisories) keys on a **schema
decision field** (decision = deny/block vs advisory), never a text
heuristic. The ONLY dampenable channel is **human-facing prose**.
Exempt **by name**: **structured events**, **audit emissions**,
**`additionalContext`**, and **all block reasons**. A blocking guard's
block reason NEVER loses legibility regardless of repeat count —
CI positive control: byte-identical (modulo timestamps) at N=1 vs
N=100. A condensed advisory ALWAYS retains {advisory ID, ordinal count,
pointer-to-full-text}. Counters are session-scoped in the per-session
0600 state file (`tool_lifecycle.py` pattern), off the audit hot path,
with ≤1 condensation audit event per advisory ID per session.

### 7. Gate-side allowlist doctrine for opt-in no-op hooks (E↔F — A11)

Any learning-loop hook that legitimately no-ops (opt-in rail with its
switch unset) is exempted from `check_harness_config.py`'s no-op
detector ONLY via the **gate-side, canonical-guarded allowlist**
(`harness-noop-allowlist.txt`, the landed Wave-E surface). An in-file
marker string **never suffices**: a self-declared marker is a
self-exemption bypass primitive — any fail-open shim could copy it. A
marker may exist for human readability but carries no authority.
Fixtures prove three directions: (a) an allowlisted no-op passes; (b)
an unmarked fail-open shim reds; (c) a marked-but-BLOCKING hook is
still liveness-tracked (the allowlist cannot hide a dead rail) — plus
copied-marker-still-reddens. Liveness must not standing-yellow a rail
that is off by recorded operator choice (no yellow-fatigue).

### 8. Kill-switch story (A12)

- **`CEO_LEARNING_OBSERVE=1`** — observe-rail opt-in; unset =
  structurally off (`cost_envelope.py` posture: no code path runs, zero
  filesystem delta — the Decision-1(c) negative control).
- **`CEO_FACT_GATE_ENFORCE`** — the enforce surface, on a SEPARATE
  switch: the authoritative flip artifact is settings-backed and
  sentinel-scoped (Decision 5); the env form exists only as a
  documented emergency OFF. Disabling observe/telemetry never touches
  the deny-once gate, and vice versa.
- **`CEO_LEARNING_DISTILL_MODEL`** — distiller model override; the
  default is an explicit haiku-tier pin in the distiller itself.
- **`CEO_LEARNING_BOOT_LESSONS=1`** — boot_render-rail opt-in (the
  `/ceo-boot` fenced lessons section); unset = structurally off, same
  posture as the observe switch.
- **`CEO_FACT_GATE_SHADOW=0`** — emergency off for the item-6 SHADOW
  telemetry rail (default ON: shadow IS the gate's advisory default and
  produces the Decision-5 flip-criteria telemetry). A separate switch
  from the enforce flip — disabling shadow never touches an armed
  deny-once gate.
- **`CEO_ADVISORY_DAMPEN=0`** — emergency off for advisory condensation
  (Decision 6); display-only, never affects blocks.
- **`CEO_SOTA_DISABLE=1`** has master precedence over all of the above.

Each rail audit-emits a disabled-this-session breadcrumb once, wired to
the ADR-158 fail-open-rail liveness check (an off-by-choice rail is
recorded, not silent). Every new env var registers in
`env-inventory.json` + the CHEAT-SHEET env table + the autouse reset
fixture in the same commit family that consumes it (S218 class).

### 9. FinOps invariant — the rent is the cost center

The dominant cost of this loop is NOT the distiller (Owner-invoked or
nightly-piggyback, delta-cursored, token-ceilinged, haiku-tier,
`/agent-budget`-visible). It is the **recurring boot+spawn injection
rent**: ≤3 lessons × ≤200 chars in `/ceo-boot` on every session, plus
the 2K-token `format_for_injection` cap on every ranked spawn.
TTL+decay is therefore ALSO the economic garbage collector, not just a
staleness control. **Any raise of the boot cap, the spawn cap, or the
lesson count is a FinOps change requiring its own review — never a UX
tweak.**

### 10. Audit-event semantics (naming via the `_KNOWN_ACTIONS` ceremony)

The chain events this record requires — hash-pinned approval
(Decision 3), quarantine and terminal expiry (Decisions 2/4), the
activation-change governance event (Decision 5), the ≤1-per-advisory
condensation event (Decision 6), and the disabled-this-session
breadcrumbs (Decision 8) — are normative as SEMANTICS. Exact action
names land via the `_lib/audit_emit.py` `_KNOWN_ACTIONS` 4-file
coupling in the same landing series (the ADR-159 Decision-1d
precedent); all lesson-family events carry closed, bounded fields only,
per Decision 1.

## Consequences

- No lesson text reaches a rendered surface without passing FOUR
  independent controls: capture-time closed schema (Decision 1) →
  fail-closed injection scan at promotion (Decision 2) → human approval
  hash-pinned in the chain (Decisions 3/4) → verify-before-render
  (Decision 3). The human gate is deliberately NOT counted among the
  injection controls.
- With the Decision-8 switches unset, behavior is byte-identical to
  today: no observation, no candidates, no boot/spawn lesson delta —
  regression-pinned by the kill-switch zero-delta fixture.
- Any schema widening, cap raise, flip-criteria change, or new
  dampenable channel is an AMENDMENT to this record — reviewable
  decisions, not code drift; the frozen schema-hash fixture and the
  N=1-vs-N=100 block-reason control make silent drift red CI.
- The `$HOME` lesson store can be tampered with at will and the worst
  outcome is a dropped lesson plus an integrity flag — never an
  unapproved render, never a blocked-guard legibility loss.
- The deny-once gate cannot reach enforce without ≥14 days of
  chain-measured shadow evidence meeting the pre-registered numbers,
  and every flip is itself chain-auditable.

## Alternatives considered

- **Redact at read** — rejected (Decision 1): the HMAC chain makes
  capture-time leaks permanent; read-side redaction defends the wrong
  end.
- **Redacted-payload (free-text) capture in v1** — rejected; a LATER
  opt-in gated behind a documented PII/PHI redaction pass (beyond
  `redact.py`'s secret-only scope) + per-install named opt-in.
  Healthcare/fintech installs must never gain an un-de-identified
  content store by default (constraint 1).
- **Human review as the injection defense** — rejected: reviewer
  fatigue is an attack surface; the machine filters for injection, the
  human for usefulness (constraint 3, verbatim red line).
- **Auto-activation above a confidence threshold** — rejected: zero
  self-activation is the unchanged red line; confidence orders review,
  it never activates.
- **In-file marker as no-op exemption** — rejected (Decision 7):
  self-exemption bypass primitive; the allowlist lives gate-side.
- **Text-heuristic dampening classifier** — rejected (Decision 6):
  classification keys on the schema decision field; a heuristic that
  misreads a block as advisory silently degrades a guard.
- **Enforce-on-launch for the deny-once gate** — rejected: shadow-first
  with pre-registered numeric criteria (the ADR-159 Decision-1e
  default-OFF pilot posture / H5 precedent).
- **A new PostToolUse/PreToolUse registration for the observe rail** —
  rejected (A3): the extension rides `record_pre`/`record_post`
  in-place (MF-PERF-1/MF-SEC-5) and joins the hook-latency profiler
  corpus under the existing p95<120ms/p99<160ms CI gate.
- **One shared kill-switch for observe + enforce** — rejected
  (Decision 8): disabling telemetry must never silently disable (or
  enable) an enforcement gate; separate switches, master
  `CEO_SOTA_DISABLE` precedence.
