# ADR-019: Confidence gate enforcement lifecycle

**Status:** ACCEPTED
**Date:** 2026-04-14
**Sprint:** 9 (PLAN-009 Phase 1 C1.3)
**Related:** ADR-018 (claim grammar), ADR-014 (hook migration batch policy), ADR-010 (canonical-edit sentinel), ADR-011 (injection_flag precedent)

## Context

Sprint 8 shipped `confidence_gate.py` as an advisory CLI (ADR-018, PLAN-008
Phase 2). Sprint 9 Phase 1 C1.1 added `.claude/hooks/check_confidence_gate.py`
as a PostToolUse Agent hook that invokes the CLI and emits audit events —
still advisory-only: exit code is always `allow`, no matter what the
verifier reports.

The question ADR-019 answers: **how do we transition from advisory to
enforcement without breaking sessions?**

Sprint 9 is explicitly the *machinery* sprint, not the *activation*
sprint (PLAN-009 Approach Principle 1). This ADR documents the
lifecycle + exit-code contract + rollback protocol so Sprint 10 can
flip the switch based on measured FPR, not on intuition.

## Decision drivers

- **Machinery without activation.** The env gate must be off by default
  and never flip automatically. Sprint 10 decides state transition 2→3
  in a separate ADR, once FPR data accumulates.
- **Owner-only in Sprint 9.** PLAN-009 debate C6/A8: only the Owner
  may set `CEO_CONFIDENCE_ENFORCE=1` in their shell/settings. Employees
  who inherit the framework inherit advisory mode. `docs/FOR-EMPLOYEES.md`
  says "do not set this flag".
- **Escape hatch.** If enforcement wedges a legitimate session, the
  Owner must be able to unblock within seconds. `CEO_CONFIDENCE_BYPASS=1`
  is a session-scoped override that allows all spawns regardless of
  CLI exit — no settings.json edit required.
- **Fail-open on infrastructure.** The hook's fail-open contract
  (CLAUDE.md §Critical Rules) is not weakened by enforcement.
  Infrastructure errors still allow.
- **Rollback signal.** Document the empirical threshold that triggers
  state regression: ">1 legitimate spawn/day blocked" → revert.

## Decision

### 1. Three-state lifecycle

```
          Sprint 8            Sprint 9 C1.1        Sprint 10 (conditional)
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│  State 1         │───▶│  State 2         │───▶│  State 3         │
│  advisory-CLI    │    │  advisory-hook   │    │  enforcing-hook  │
│                  │    │                  │    │                  │
│  - confidence_   │    │  - CLI + hook    │    │  - CLI + hook    │
│    gate.py       │    │    both run      │    │    both run      │
│  - manual /      │    │  - hook always   │    │  - hook blocks   │
│    benchmark     │    │    allows        │    │    on fail IF    │
│    invocation    │    │  - env gate OFF  │    │    Owner sets    │
│  - FPR baseline  │    │  - FPR collected │    │    CEO_CONF_     │
│    collection    │    │    per spawn     │    │    ENFORCE=1     │
│                  │    │                  │    │  - bypass hatch  │
│                  │    │                  │    │    available     │
└──────────────────┘    └──────────────────┘    └──────────────────┘
```

**Sprint 9 ships state 2.** The env gate machinery is wired in
`check_confidence_gate.py` (`decide(enforce=...)` parameter), but the
default is `enforce=False`. Setting `CEO_CONFIDENCE_ENFORCE=1`
instantly promotes this repo to state 3 from the Owner's session.

**Sprint 10 (conditional)** writes the state-2→state-3 flip ADR
based on measured FPR data (PLAN-009 §Explicit non-goals). No inline
auto-promotion is embedded in Sprint 9 code or docs.

### 2. Owner-only scope in Sprint 9

`CEO_CONFIDENCE_ENFORCE=1` is documented in exactly two places:

1. **`RELEASE.md`** — under the v1.1.0-rc.1 release notes, in the
   "Owner-only knobs" section, with the rollback signal.
2. **`docs/FOR-EMPLOYEES.md`** — under "Flags not to touch", with
   one-line explanation of why.

The flag is NOT documented in `docs/QUICKSTART.md`, `TROUBLESHOOTING.md`,
or `README.md`. Sprint 10 may elevate it once the FPR proves acceptable.

### 3. Hook↔CLI exit-code translation table

This is the normative contract between `confidence_gate.py` CLI exit
codes and `check_confidence_gate.py` hook decisions:

| CLI exit | Meaning              | ENFORCE=0 | ENFORCE=1 | Effect                |
|----------|----------------------|-----------|-----------|-----------------------|
| 0        | all claims passed    | allow     | allow     | allow                 |
| 1        | ≥1 claim failed      | allow     | **block** | deny + stderr reason  |
| 2        | usage/arg error      | allow     | allow     | fail-open breadcrumb  |
| 3        | zero claims in input | allow     | allow     | no-op (no block sig)  |
| timeout  | 5s exceeded          | allow     | allow     | fail-open + event     |
| —        | any unknown          | allow     | allow     | fail-open             |
| BYPASS=1 | any state            | allow     | allow     | always allow          |

The table is asymmetric on exit 1: only `ENFORCE=1 AND exit=1 AND
not BYPASS` produces a block. Every other cell allows.

The block reason string template (enforced in `decide()`):

```
CONFIDENCE-GATE-BLOCKED: <N> claim(s) failed verification. Set
CEO_CONFIDENCE_ENFORCE=0 to revert to advisory mode, or
CEO_CONFIDENCE_BYPASS=1 to bypass a single wedged session. See ADR-019.
```

### 4. Rollback signal

The Owner should revert `CEO_CONFIDENCE_ENFORCE=0` immediately if:

- **>1 legitimate spawn per day blocked.** A single false positive is
  tolerable (the agent can retry with better claim hygiene). Recurring
  false positives = the verifier is stricter than reality warrants.
- **Any P0/P1 incident.** If enforcement blocks an emergency fix, the
  Owner unblocks via `CEO_CONFIDENCE_BYPASS=1` in that session and
  reverts enforce in parallel.

Post-rollback: open an issue tagged `confidence-gate-fp` with the
blocked agent output + `confidence_gate` audit event. Sprint 10 triage
adjusts the grammar or the verifier before re-flipping.

### 5. Known bypass (documented, not fixed)

The confidence gate is a **quality signal, not a security boundary**.
The following are known bypasses (they exist by design; do not file
issues):

- **Fail-open on verifier exception.** If any verifier raises an
  unexpected exception, the claim is treated as unverifiable (not fail)
  and the event records zero fails. An attacker who can construct an
  exception-triggering claim gets their spawn through. Mitigated by:
  (a) inputs are pre-sanitized via `_scoped_resolve` + strict regexes;
  (b) tests cover all known exception paths with explicit handlers.
- **Fail-open on timeout.** 5-second subprocess timeout → allow. An
  attacker who can make the CLI hang (unlikely — no network calls)
  gets through. Mitigated by: the CLI itself has a 15s inner pytest
  timeout + 5s git timeout.
- **Zero-claims.** An agent that emits no `CLAIM:` tokens cannot fail
  verification. This is a *feature* (encourages gradual adoption), not
  a vulnerability. The `claim_count` field in the audit event surfaces
  this for later analysis.
- **CEO_CONFIDENCE_BYPASS=1.** Intentional escape hatch. Not a bypass
  in the attacker-model sense — it's an Owner-side control.

### 6. Rollout plan

| Phase    | Date (target) | Action                                          |
|----------|---------------|-------------------------------------------------|
| Sprint 9 | 2026-04-14    | Ship advisory-hook; env gate wired + documented |
| Sprint 9 + 7d | 2026-04-21 | Owner reviews first week of FPR data       |
| Sprint 10 | TBD         | Write flip-ADR IFF FPR < 5% on 50+ spawns       |
| Sprint 10 | TBD         | `CEO_CONFIDENCE_ENFORCE=1` Owner-opt-in flip    |
| Sprint 11+ | TBD        | Elevate to default=1 IFF FPR stays <1% 30 days  |

No schedule is committed; all dates above are *earliest possible*.

## Consequences

### Positive

- Enforcement exists behind a single env var; no redeploy needed to
  flip on/off.
- Bypass hatch lets the Owner unstick a session in <1s without losing
  enforcement everywhere else.
- Three-state lifecycle is legible; ADR-020-future (Sprint 10) has a
  named predecessor to supersede.
- Rollback signal is empirical, not vibes.

### Negative

- Advisory-hook (state 2) adds subprocess cost per Agent spawn. Measured
  in C1.1 tests: typical <200ms for small outputs, <5s hard cap. If
  spawn volume grows, Sprint 10 may need to sample rather than scan
  every spawn (explicit non-goal for Sprint 9).
- Two env vars (`CEO_CONFIDENCE_ENFORCE`, `CEO_CONFIDENCE_BYPASS`) =
  two more Owner-facing knobs to remember. `RELEASE.md` documents both
  in the same section to minimize cognitive load.

### Neutral

- The `decide()` function takes `enforce` + `bypass` as parameters, not
  env reads — pure function preserved for testability. `main()` reads
  the env vars and passes them in.

## Blast radius

**L2** — one ADR, ~20 lines of code in `check_confidence_gate.py`
(already shipped in C1.1), env-var docs in `FOR-EMPLOYEES.md` +
`RELEASE.md` (C1.4).

**Reversibility:** HIGH. Removing the env vars requires one code
change + one doc change. The hook itself remains useful in state 2
even without the env gate.

## Transition Log

*This appendix follows ADR-041 Transition Log Convention. Each row records
a state transition triggered by a flip criterion in its window.*

| Date | From-State | To-State | Evidence-Link | PR-Ref | Signer |
|------|------------|----------|---------------|--------|--------|
| _(empty — first flip pending per PLAN-012)_ | | | | | |

## References

- PLAN-009 §Phase 1 C1.3 + §Phase 1 C1.1 + §Phase 1 C1.4
- PLAN-009/debate/round-1/security.md — R-SEC1/2/3 findings
- PLAN-009/debate/round-1/consensus.md §C6/A8 (Owner-only scope)
- ADR-018 v1.1 — claim grammar (frozen namespace, block-list)
- ADR-014 — hook migration batch policy (why hooks ship in serial commits)
- ADR-010 v1.1 — canonical-edit sentinel (why new hooks are pre-sentineled)
- CLAUDE.md §Critical Rules (fail-open contract)

## Enforcement commit

`e556b06e6f5e` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
