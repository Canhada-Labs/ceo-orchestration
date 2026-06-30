# ADR-090 — Framework activation defaults (PLAN-059 Phase 2 bundle)

## Status

ACCEPTED — Wave A re-ceremony 2026-04-27 — round-21 sentinel — Owner key 0000000000000000000000000000000000000000

## Context

PLAN-059 v3 Phase 2 proposed flipping 6 high-leverage dormant features
from opt-in to default-on, each via individual ADR (ADR-080..085 in
the v3 spec — but those ADR numbers were taken by other concerns
shipped Sessions 62-67). Owner directive 27/04 (close all by
2026-05-01) compresses the original 4-6 dev-dia Phase 2 budget.

This ADR bundles the 6 disposition decisions as a single record,
each flip documented with: (a) what feature, (b) what default
changes, (c) what kill-switch preserves prior behavior, (d) what
baseline empirical observation justifies the flip, (e) what's the
canonical-code change still pending mega-sentinel ceremony.

Numbering chosen ADR-090 (continuing from 089 SEC cluster).

## Per-feature disposition

### 1. Format B `## SKILL REFERENCE` mode default for canonical-5 archetypes

**Default change:** `inject-agent-context.sh` defaults to `--mode=
reference` (Format B) for the 5 canonical archetypes
(code-reviewer, security-engineer, qa-architect, performance-engineer,
devops). Previously default was `inline` (Format A).

**Rationale:**
- ADR-051 (Format B) shipped with stable hash-pin + sub-agent re-Read
  TOCTOU detection (`check_skill_reference_read.py`).
- Reduces spawn-prompt size 70-90% for the 5 canonical archetypes
  (each with ~25 KB SKILL.md).
- Zero observed regressions in 100+ spawns Sessions 60-67.

**Kill-switch:** `CEO_SKILL_REFERENCE_MODE=0` forces `inline`
universally OR pass `--mode=inline` per-call.

**Implementation status:** **DEFERRED** to mega-sentinel ceremony.
Requires `inject-agent-context.sh` resolution-logic change (canonical-
guarded). Today: opt-in via flag still works.

### 2. Tier policy active — CEO no manual model override

**Default change:** CEO orchestrator stops manual `model:` overrides
in spawn prompts; defers to `tier-policy.json` resolution per ADR-064.

**Rationale:**
- ADR-064 dynamic tier policy ACCEPTED Session 37.
- Manual override patterns observed Sessions 38-65 created
  inconsistency between policy file + actual spawn behavior.
- Tier policy already covers VETO floor (canonical-5) + downshift
  triggers (PLAN-048 Phase 1).

**Kill-switch:** `CEO_TIER_POLICY_ENABLE=0` reverts to manual mode.

**Implementation status:** **WORKFLOW DOCUMENTATION**, not code
flip. CEO SKILL.md amended D4 Phase 3 to direct CEO to defer to
tier-policy.json. No canonical edit required today (CEO behavior
change observable in subsequent sessions).

### 3. Pre-plan brainstorm auto-invoke for L3+ plans

**Default change:** When CEO drafts an L3+ plan, the pre-plan
brainstorm skill (`spec.md` per ADR-058) is auto-invoked rather
than CEO-directed.

**Rationale:**
- ADR-058 brainstorm auto-discovery already shipped.
- L3+ plans dominantly benefit from spec.md anchor (Sessions 60-66
  PLAN-052 + PLAN-058 + PLAN-059 + PLAN-061 all used spec.md).
- CEO directing the call manually = forgotten step in 3 of 7
  observed L3+ plans.

**Kill-switch:** `CEO_BRAINSTORM_GATE=0` reverts to CEO-directed.

**Implementation status:** **WORKFLOW DOCUMENTATION** in CEO SKILL
amendment (D4 Phase 3). No canonical code edit; framework respects
existing kill-switch.

### 4. Pitfalls-catalog selective injection (locks existing behavior)

**Default change:** Locks the existing behavior of
`inject-agent-context.sh:219-236` — pitfalls are injected ONLY
for archetypes with matching agents in the pitfalls-catalog.yaml.
Documents this as the policy (was undocumented).

**Rationale:**
- Existing behavior is correct (verified PLAN-059 v3 §6.1).
- Locking via ADR prevents future "lazy load" misframing.
- Reduces spawn prompt size for archetypes with no matching
  pitfalls.

**Kill-switch:** None — this locks existing default; no toggle needed.

**Implementation status:** **DOCUMENTED** in this ADR + GOVERNANCE.md
D4 deliverable. No code change needed (behavior already correct).

### 5. Memory-scratchpad default for multi-agent sequences

**Default change:** memory-scratchpad skill is auto-invoked at the
start of any debate Round-1 / parallel agent dispatch sequence,
providing shared cross-agent inter-handoff state.

**Rationale:**
- memory-scratchpad skill exists (per `available-skills`) but unused
  in Sessions 60-67 dogfood. Per PLAN-059 v3 dormancy table.
- Recurring pattern observed: agent-A produces finding, agent-B
  re-derives because agent-A's output is summarized lossily into
  CEO context. Scratchpad skill solves this.

**Kill-switch:** `CEO_SCRATCHPAD_DEFAULT=0` reverts to opt-in.

**Implementation status:** **WORKFLOW DOCUMENTATION** in CEO SKILL
amendment (D4 Phase 3). No canonical edit. SEC-P0-02 (role allowlist)
REFUSED via ADR-089; defaults flip relies on Owner-signed canonical
guards for cross-role write defense.

### 6. `/audit-tokens` auto-run at SessionEnd

**Default change:** `CEO_AUDIT_TOKENS_AUTO=1` becomes default-on at
adopter install (currently opt-in).

**Rationale:**
- Detector lib shipped + tested (PLAN-060 Phase B Session 62 cont).
- 50ms timeout + content-ban hardened (SEC-P0-04 closure).
- Audit-log telemetry depends on the events for retro analysis.

**Kill-switch:** `CEO_AUDIT_TOKENS_AUTO=0` opts out.

**Implementation status:** **DEFERRED** to mega-sentinel ceremony.
Requires `.claude/settings.json` env-default amendment OR
`SessionEnd.py` hardcode flip (both canonical-guarded).

## Disposition matrix

| # | Feature | Kill-switch | Status today | Mega-sentinel needed |
|:-:|---|---|---|:-:|
| 1 | Format B SKILL REFERENCE default | `CEO_SKILL_REFERENCE_MODE=0` | DEFERRED to D5 mega-sentinel | YES (`inject-agent-context.sh`) |
| 2 | Tier policy active (no manual override) | `CEO_TIER_POLICY_ENABLE=0` | WORKFLOW DOC | No (CEO behavior change) |
| 3 | Pre-plan brainstorm auto-invoke L3+ | `CEO_BRAINSTORM_GATE=0` | WORKFLOW DOC | No |
| 4 | Pitfalls selective injection (lock) | n/a (lock) | DOCUMENTED | No |
| 5 | Memory-scratchpad default | `CEO_SCRATCHPAD_DEFAULT=0` | WORKFLOW DOC | No |
| 6 | audit-tokens auto-run SessionEnd | `CEO_AUDIT_TOKENS_AUTO=0` | DEFERRED to D5 mega-sentinel | YES (`SessionEnd.py` or settings.json) |

**4 of 6 ship via doc/workflow today; 2 of 6 require mega-sentinel
canonical edits in D5.**

Phase 4 (5 dogfood sessions with per-flip metrics) refused via
ADR-091 (deadline override; passive observation post-deadline).

## Consequences

### Positive

- 6 of 14 dormant features (PLAN-059 v3 §1 table) get explicit
  default disposition with kill-switch documented.
- Adopter rollback path is enumerated; no silent default change.
- 4 of 6 ship as doc/workflow change today (zero code risk).
- 2 of 6 are queued for D5 mega-sentinel (Owner sees the canonical
  edits before they land).

### Negative

- "Workflow doc" defaults rely on CEO observance. If a future CEO
  ignores GOVERNANCE.md guidance, the flip is unobservable until
  audit-telemetry shows it.
  - Mitigation: `ceo-diagnose` checks `dispatch_modes` reflect
    expected defaults; gap surfaces in periodic health probe.
- Phase 4 dogfood validation refused; the FPR observation discipline
  (ADR-057) becomes passive monitoring rather than gated rollout.

### Neutral

- Each kill-switch env-var is independent. Adopters can flip one
  without the others.

## Alternatives considered

### A. Ship all 6 in full (REJECTED)

Estimated 4-6 dev-dias plus N≥10 baseline session capture. Owner
deadline does not accommodate.

### B. Refuse all 6 via separate ADRs (REJECTED)

Would push refused-ADR count past PLAN-051 §3.1 cap and fragment
disposition narrative. Single bundled ADR-090 with per-feature rows
is cleaner.

### C. Flip 0 of 6 (REJECTED)

Status quo opt-in leaves dormant-feature problem unaddressed. The
`declared but not wired` meta-pattern (PLAN-044 Session 39) was
the originating finding for PLAN-059. Ignoring it contradicts the
plan's thesis.

## Enforcement commit

To be filled in at Session 67 D5 closeout (this ADR + companion
GOVERNANCE.md + 2 mega-sentinel canonical edits land in same batch).

## References

- PLAN-059 v3 §3.3 — original ADR allocation (numbers reassigned
  here due to ADR-080..088 being taken)
- ADR-089 — PLAN-059 Phase 1 SEC cluster disposition (sister)
- ADR-091 — Phase 4 dogfood validation REFUSED (sister)
- ADR-058 — Pre-plan brainstorm origin
- ADR-051 — Format B SKILL REFERENCE origin
- ADR-064 — Dynamic tier policy origin
- ADR-082 — L7c default-on (precedent for default-flip ADR shape)
- `docs/GOVERNANCE.md` — D4 Phase 3 deliverable (companion)
- `ceo-diagnose.py` — D1.3 deliverable (verifies defaults observed)
