---
id: ADR-146
title: Adversary local-rules review hook — deterministic deny/ask gate, no model on the hot path
status: ACCEPTED
enforcement_commit: 94694d5f
accepted_at: 2026-06-17
accepting_session: S242
decision_date: 2026-06-09
proposing_session: S223
authorization: "PLAN-133 (Goose-harvest SOTA evolution) item E1 [P1]. 7-archetype Wave-A debate 0-VETO + Codex pair-rail. HARD PREREQUISITE per PLAN-133 §3 + E1 §0: this ADR is REQUIRED ACCEPTED before the E1 hook builds."
owner: security-engineer
plan: PLAN-133-goose-harvest-sota-evolution
amends: none
related: [ADR-052, ADR-106, ADR-107, ADR-125, ADR-143]
---

# ADR-146 — Adversary local-rules review hook

**Status:** ACCEPTED (S242, 2026-06-17 — the E1 hook is built, registered in
`.claude/settings.json` as a PreToolUse Bash gate, and firing in production).
Promotion gate: 7-archetype Wave-A debate 0-VETO + Codex pair-rail (PLAN-133 E1) +
Codex R-sweep ACCEPT (thread `019ed788`, S242).
**Enforcement commit:** `94694d5f` — the enforcing artifacts are
`.claude/hooks/check_adversary.py` + `.claude/hooks/_lib/adversary_rules.py` +
the `adversary_review_flagged` closed-enum action in `.claude/hooks/_lib/audit_emit.py`
(SPEC v2.41). Measure-first (publish p50/p95/p99 + FP review before flipping
`CEO_ADVERSARY` default-on) remains a SEPARATE future gate.
**Blast radius:** L3 (a new PreToolUse Bash governance gate + a new audit action +
a new untrusted-DATA channel `.claude/adversary.md`)
**Cites:** PLAN-133 item E1 [P1].

## Context

The Goose `ToolInspector` runs an adversary-reviewer over a proposed tool call
before it executes. PLAN-133 E1 harvests that *mechanism* (a from-scratch stdlib
re-implementation — nothing was fetched or executed from the `aaif-goose/goose`
fork) as a per-Bash-command deny/ask gate.

The naive port would call a model synchronously to judge each command. The
governance rite REJECTED that: a measured 40×–600× p99 latency regression versus
the ~5ms warm-hook floor, on the Bash hot path, for marginal added depth — the
real adversarial depth already lives in the canonical/L3 Codex pair-rail
(ADR-106/107). A per-op model call here would also reactivate the retired
`pair_rail` Phase-C, which doctrine forbids.

## Decision drivers

- Adversarial review of risky Bash commands is valuable, but NOT at the cost of a
  per-op model round-trip on the hot path.
- A trusted, author-controlled ruleset (`.claude/adversary.md`) lets the Owner
  encode standard offensive-security patterns (reverse shell `/dev/tcp`,
  `curl | sh`, setuid bits) deterministically.
- A live-credential in a command must never be transmitted anywhere, independent
  of the ruleset.
- New capability must be measure-first / default-OFF per the risk-tiered
  defaulting doctrine (ADR-125).

## Options considered

### Option A: Sync model call per Bash op (the naive Goose port)
Highest depth, but a 40×–600× p99 regression on the hot path and a `pair_rail`
Phase-C reactivation. Rejected.

### Option B: Deterministic local-rules engine, no model on the hot path (chosen)
A pure stdlib regex/substring engine reads deny/ask rules from
`.claude/adversary.md` and evaluates the command. No network, no model. Real
adversarial depth stays in the L3 Codex pair-rail.

### Option C: Do nothing
The Bash safety hook already blocks `rm -rf` / force-push, but it is a fixed
substring parser, not an Owner-extensible ruleset. Rejected — leaves the
harvested value on the table.

## Decision

Adopt **Option B**. Ship a NEW PreToolUse Bash hook `check_adversary.py` backed by
a pure `_lib/adversary_rules.py` engine, with these invariants:

1. **Local-rules-only — NO model call on the hot path.** No `codex_invoke` send;
   E1 transmits nothing (local-only).
2. **Default-OFF.** `CEO_ADVERSARY` (read from the import-time `trusted_env`
   snapshot, not live `os.environ`) gates ENFORCEMENT. Unset/≠"1" → advisory
   (emit + ALLOW). "1" → a `deny` rule BLOCKS, an `ask` rule BLOCKS with an
   ask-style reason.
3. **NOT a `pair_rail` Phase-C reactivation.** This is a new, independent hook.
4. **Secret-in-command → fail-CLOSED, never transmit.** A live-credential pattern
   (`_lib.secret_patterns`) match inside the command DENIES (enforce) / flags
   (advisory) BEFORE the `.md` rules. The command bytes never leave the process
   (structural never-transmit).
5. **`.claude/adversary.md` is UNTRUSTED DATA**, read only from inside
   `CLAUDE_PROJECT_DIR`, with a hard 64 KiB size cap. Missing/oversize/unreadable
   → fail-OPEN (allow).
6. **No-value-echo.** The `adversary_review_flagged` audit action carries only a
   closed-enum `decision` + closed-enum `rule_class` + author-controlled `rule_id`.
   The command bytes, the matched substring, and the rule source are NEVER
   persisted. Routes through a dedicated scrub branch, NEVER `_EMIT_GENERIC_PASSTHROUGH`.
7. **Fail-OPEN on any infra error** (a returned `deny` IS honored).

## Consequences

- (+) Owner-extensible adversarial Bash review with zero per-op model latency; the
  secret-fail-CLOSED path is independent of the ruleset.
- (+) Default-OFF + advisory-from-day-one gives a real measure-first denominator
  (avoids the PLAN-128 §7 0/0/0 trap) before any default-on flip.
- (−) The ruleset is a new untrusted-DATA surface; mitigated by the size cap,
  the inside-`CLAUDE_PROJECT_DIR` containment check, and per-rule regex budgets.
- (−) +1 registered hook on the Bash hot path; bounded by the ~5ms warm floor +
  a per-session call cap; promotion-measure publishes p50/p95/p99 at `/ceo-boot`.
- (~) Adds a closed-enum audit action (`_KNOWN_ACTIONS` +1) — gated by the
  api-contract SHA + count + no-value-echo property tests.

## Promotion criteria (measure-first per ADR-125)

Before any proposal to flip `CEO_ADVERSARY` default-on: publish p50/p95/p99 hook
latency + per-session hit count + the advisory deny/ask mix at `/ceo-boot`, plus a
false-positive review of the advisory-mode hits.

## Blast radius

L3 — a new PreToolUse Bash hook, a new untrusted-DATA channel, and a new audit
action; touches `settings.json` + `settings.base.json` (parity), `audit_emit.py`
(closed-enum), and the api-contract test SHA/count.
