# ADR-096 — Vibecoder-only by design (closes C7-DB-01 + C7-DB-02)

## Partial-supersession-notice (PLAN-103 FASE 0, 2026-05-13)

**§Part 3 (terminal-verdict claim `MAINTENANCE-MODE-VIBECODER`)** is
**PARTIALLY SUPERSEDED** by [ADR-124](ADR-124-post-audit-sota-execution-mode.md)
as of 2026-05-13. ADR-124 establishes
`post-audit-SOTA-execution-mode` as the framework's operational
mode for the duration of the PLAN-084 evolution-roadmap burn-down
(FASE 1-4, 12-18 sessions, 90-180 calendar days). At sunset (per
ADR-124 §Part 3), the operational mode returns to
`MAINTENANCE-MODE-VIBECODER` and ADR-096 §Part 3 fully governs
again.

**§Part 1 (vibecoder-only positioning declaration)** and **§Part 2
(README §Risks expansion)** REMAIN IN FORCE unchanged. ADR-096
remains the canonical source of positioning (bus-factor 1, no SLA,
single-Owner audience). Only the "terminal verdict" temporal claim
is superseded.

See ADR-124 §Part 5 for the full relationship spec.

## Status

ACCEPTED — Wave session 73 ceremony 2026-04-29 — Owner key 0000000000000000000000000000000000000000
(§Part 3 partially superseded by ADR-124 2026-05-13)

## Date

2026-04-29

## Enforcement commit

Documentation-only / no enforcement commit (positioning ADR; enforced via INSTALL.md banner + HONEST-LIMITATIONS doc updates landed in Phase 1).

## Context

PLAN-044 audit-v2 cluster-7 deal-breakers identified two structural
issues blocking external (series-B fintech) adoption:

- **C7-DB-01 — Bus factor 1.** The framework has a single maintainer
  (the Owner). For series-B/regulated adoption, recruiters expect
  bus-factor ≥2 with documented hand-off / overlap.
- **C7-DB-02 — Mid-pivot reframing.** Sessions 60-67 introduced
  Claude-only thesis (ADR-085), retracted multi-adapter (ADR-084),
  re-baselined the framework's positioning. Mid-pivot framing
  signals instability to external evaluators.

Audit-v2 verdict.md offered a "vibecoder-mode path" as a face-saving
compromise but rejected it as not honestly executed (no
`--profile=vibecoder` flag, no different `settings.base.json` per
profile, no CI matrix). Owner directive 2026-04-29 ("código tudo,
nada pendente, vibecoder-only é OK"): adopt vibecoder-only
positioning honestly + close C7-DB-01 + C7-DB-02 via documentation.

## Decision drivers

- **Honest framing > face-saving compromise.** The framework was
  built for the Owner's personal use ("dogfood mode" since Sprint 1).
  External adopter recruitment was an aspiration, not a delivered
  capability. Audit-v2 caught the gap; closure-honesty (ADR-092)
  requires we OWN the gap rather than pretend it's narrowing.
- **Bus-factor 1 is not fixable in tokens.** Recruiting a
  co-maintainer requires a HUMAN action (Owner-physical), trust
  building, and time. None of this fits "código tudo agora".
- **Re-positioning is the close, not refactoring.** The framework's
  identity was already vibecoder-shaped (per CLAUDE.md, ADR-085
  Claude-only thesis, single-Owner GPG governance). Documenting
  this explicitly closes the deal-breaker without changing code.
- **README §Risks expansion is the deliverable.** Adopters who wander
  in must read the limitations clearly. Promoting HONEST-LIMITATIONS.md
  link from README + adding §Risks/§Not-for paragraph closes
  C7-DB-02 (mid-pivot reframing → "we know what this is").
- **No `--profile=vibecoder` flag.** Audit-v2 explicitly rejected
  the half-measure. Either the framework IS vibecoder-only OR it
  has a real profile system. We adopt the former — single profile,
  no ambiguity.

## Options considered

### Option A — Recruit co-maintainer + delete vibecoder framing

Original "external adopter" path. Owner-physical, calendar-bound,
external-dependent. Out of scope for "código tudo agora".

### Option B — `--profile=vibecoder | team | enterprise` flag system

Audit-v2 rejected this as ~5 dev-day extra work without proven
demand. Three real `settings.base.json` variants + CI matrix +
README §Risks per profile. Rejected — not aligned with Owner's
"code tudo agora" given the adopter audience already isn't there.

### Option C — Vibecoder-only by design + README §Risks (CHOSEN)

Single positioning. README §Risks expansion documents:
- bus-factor 1 (Owner only)
- not for series-B/fintech adoption
- Claude-only by design (ADR-085)
- no SLA / no support
- HONEST-LIMITATIONS.md is required reading

This closes C7-DB-01 + C7-DB-02 in tokens. NOT a sandbag-flip;
the framework genuinely IS what it claims, the docs catch up.

### Option D — Status quo

Rejected — leaves the audit-v2 P0s open without closure. The
"engineering by aspiration" pattern audit-v2 caught was: claim
external readiness while not being externally ready. Closure here
is "stop claiming external readiness".

## Decision

**Option C.** Three-part rule:

### Part 1 — Vibecoder-only positioning declaration

This ADR is the canonical statement: the framework is built for the
Owner's personal use ("vibecoder mode") and is NOT positioned for
series-B / regulated / multi-tenant adoption. Adopters who run
`scripts/install.sh` are doing so at their own risk; HONEST-
LIMITATIONS.md governs.

### Part 2 — README §Risks expansion

`README.md` adds (or expands) §Risks section with:

```markdown
## Risks & Not-For

- **Bus factor 1.** Single maintainer (Owner). No SLA, no support
  channel, no hand-off plan. (ADR-096)
- **Vibecoder-only positioning.** Built for personal use. Not
  positioned for series-B / fintech / regulated / multi-tenant.
  (ADR-096)
- **Claude-only by design.** No multi-adapter (Gemini, OpenAI,
  local) support. (ADR-085 / ADR-084)
- **Same-LLM problem.** Code review, debate, security review all
  use the same model family (Claude). External human review is
  the only LLM-bias-free check. (PROTOCOL.md §Honest limitation)
- **Required reading before adoption:** [HONEST-LIMITATIONS.md](
  docs/HONEST-LIMITATIONS.md), [CTO-GUIDE.md](docs/CTO-GUIDE.md),
  ADR-096 (this), ADR-085 (Claude-only thesis).
```

This is a documentation-only change. No CI gate, no code change.

### Part 3 — `docs/READINESS-STATUS.md` verdict reflects positioning

Verdict transitions from `TRIAL-PENDING-SOAK` to
`MAINTENANCE-MODE-VIBECODER` (via ADR-095). MAINTENANCE-MODE-VIBECODER
is the terminal verdict for this framework's identity. TRIAL → ADOPT
remains a defined path but is NOT scheduled.

## Consequences

**Positive (+):**
- Closes C7-DB-01 + C7-DB-02 in tokens, today.
- README §Risks is honest with adopters at the front door.
- Removes ambiguity for the Owner ("am I selling this to series-B?
  no.").
- Aligns with PLAN-051 §3 (TeX/qmail-style "done + reactive
  maintenance") declared Session 67.

**Negative (-):**
- The framework's external-adopter recruitment story is closed.
  Future series-B interest requires Owner-physical recruitment
  + ADR-096 supersession.
- Removes implicit upside ("maybe this'll grow") in exchange for
  explicit positioning ("this is what it is").

**Neutral (~):**
- HONEST-LIMITATIONS.md remains the canonical detailed limitation
  doc (was already correct; just promoted to required reading).
- ADR-085 Claude-only thesis remains valid.
- ADR-093 60d moratorium remains active.
- Gates #3 + #4 + #5 (code-correctness audit-v2 gates) remain DONE.
- Gate #6 (outside reviewer) remains AVAILABLE.

## Blast radius

L3+. Touches:
- This ADR
- `README.md` (§Risks expansion — non-canonical, no sentinel needed)
- `docs/READINESS-STATUS.md` (verdict update — non-canonical)
- `CHANGELOG.md` (entry referencing this ADR — non-canonical)
- `CLAUDE.md` §6 (handoff state — non-canonical)

No `.claude/adr/`, no `SPEC/`, no `.claude/policies/`, no
workflow file changes — purely positioning + doc work.

## Compliance checklist

| Item | Verification |
|---|---|
| README §Risks section present | grep `## Risks` in `README.md` |
| §Risks names bus-factor 1 | grep `Bus factor 1` |
| §Risks names vibecoder-only | grep `Vibecoder-only` |
| §Risks names Claude-only by design | grep `Claude-only by design` |
| §Risks names same-LLM problem | grep `Same-LLM problem` |
| §Risks links HONEST-LIMITATIONS.md | grep `docs/HONEST-LIMITATIONS.md` |
| docs/READINESS-STATUS.md verdict updated | grep `MAINTENANCE-MODE-VIBECODER` |
| CHANGELOG entry references this ADR | grep `ADR-096` in 2026-04-29 entry |
| ADR file landed via Owner sentinel ceremony | round-5 sentinel includes this path |

## Related decisions

- ADR-093 — 60-day refused-ADR moratorium (companion, NOT retracted)
- ADR-095 — Calendar gate retraction (companion)
- ADR-097 — Function-length advisory-permanent (companion)
- ADR-085 — Claude-only thesis (Session 67) — VALIDATED by this ADR
- ADR-084 — Multi-adapter REFUSED (Session 67) — VALIDATED
- audit-v2 verdict.md C7-DB-01 / C7-DB-02 (closed by this ADR)
- PLAN-051 §3 (TeX/qmail-style maintenance) — fully aligned
- HONEST-LIMITATIONS.md — promoted to required-reading-before-adoption
