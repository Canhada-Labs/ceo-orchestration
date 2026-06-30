# ceo-orchestration — 60-second pitch

<!-- last-reviewed: 2026-06-20 v1.0.0 -->

> Status: v1.0.0, public release.

## The 1-paragraph version (≤50 words, ≤25s read aloud)

A solo Owner running 100+ AI sessions on important repos needs governance
without a 50-person team. We wrap Claude Code with Plan → Debate → Execute,
a tamper-evident audit chain, and a Codex Pair-Rail that catches L3+ mistakes
before they ship. Install into your existing repo; reversible via uninstall.

## The AC3 checklist (5 elements Owner explains in 60s ± 10s)

1. **Problem** (≤10s) — "I'm running important AI work across multiple repos
   and 100+ sessions. I cannot audit what was decided, what was spent, or
   what was caught. I cannot scale this safely."

2. **Mechanism** (≤15s) — "Plan → Debate → Execute structure with a tamper-
   evident HMAC audit chain. A Pair-Rail with Codex MCP cross-LLM gate
   reviews every L3+ canonical edit. 151 skills auto-load by repo profile."

3. **Guardrails** (≤15s) — "Sentinel ceremonies for canonical files require
   detached GPG signatures. Trading-readonly profile fails CLOSED on
   missing config. Per-rule FPR ≤15% on exchange-key secret scanning."

4. **Proof artifact** (≤15s) — "What you actually get is governance-as-code:
   veto-floor + GPG-signed canonical edits + an HMAC audit chain + a
   cross-LLM Codex Pair-Rail you can inspect. Real dogfood catch: Pair-Rail
   flagged a live Gate-5 production bug in S159 (validate_scope_header
   rejecting an email.message.Message) — self-reported, not independently
   verified. On *speed / task-lift* we now have data and publish it as null:
   WS-0b (paired, objective SWE-bench-Lite) showed the framework did not
   out-resolve raw Claude Code, and **six independent experiments found no
   general speedup** (PLAN-122). We make **no speed claim** — the value is
   governance and auditability, which are orthogonal to velocity."

5. **When NOT to use** (≤5s) — "Throwaway scripts, one-file edits, or
   teams already locked into Cursor rules. Overhead beats velocity below
   ~$50/month spend."

## Tradeoffs (one slide for skeptics)

| Pro | Con |
|---|---|
| Tamper-evident audit chain HMAC | GPG sentinel ceremony is Owner-physical (~1.5min × ceremony) |
| Cross-LLM Pair-Rail catches solo-LLM blind spots | Codex MCP adds $30-50 per L3+ debate |
| 151 skills retained but smart-loaded | Initial install takes ~12s + first-run wizard ~30s |
| Reversible install (manifest-safe uninstall) | Not yet open-source (Owner-private, 5-repo test) |
| Fail-CLOSED trading-readonly profile | Generic profile reachable only via explicit `confirm-profile` |

## Practiced delivery notes

- Read sections 1+2 aloud once in 25s
- Pause briefly between Guardrails and Proof artifact
- End on "When NOT to use" — credibility from honest limits

## Related artifacts

- `docs/DECISION-LOG.md` — full why-this-exists narrative
- `docs/WHAT-WE-ARE.md` — 7 positive + 7 negative claims
- `docs/CASE-STUDY-<repo>.md` — Wave 3 deliverable
