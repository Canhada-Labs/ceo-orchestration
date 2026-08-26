---
id: ADR-144
title: Subagent model tiering via per-agent frontmatter — global CLAUDE_CODE_SUBAGENT_MODEL override prohibited
status: ACCEPTED
enforcement_commit: c2285999
decision_date: 2026-06-08
proposing_session: S218
authorization: "PLAN-128-FOLLOWUP — Codex pair-rail 019ea463 (design) + 019ea473 (applied diff) ACCEPT-WITH-FIXES + Wave-A debate (llm-finops/security/qa). Fix already SHIPPED Owner-GPG c2285999 + closeout 9c87dea5; this ADR is the not-silent, intent-level codification of the doctrine the fix enforces mechanically. Reinforces ADR-052 per-role dispatch."
owner: llm-finops-architect
plan: PLAN-128-sota-solo-accelerator
amends: none
related: [ADR-052, ADR-064, ADR-139]
---

# ADR-144 — Subagent model tiering via per-agent frontmatter

**Status:** ACCEPTED (S218, 2026-06-08) — the decision is live; settings/template/
installer already enforce it and the regression test guards it.
**Enforcement commit:** `c2285999` (fix) + `9c87dea5` (closeout) — `.claude/settings.json`
+ `templates/settings/settings.base.json` + `.claude/hooks/route.py` +
`scripts/install-accelerators.sh` + `.claude/hooks/tests/test_subagent_model_override_removed.py`
**Blast radius:** L3 (governance-rite integrity + cost doctrine; a settings/template
contract constraint enforced by a Tier-bypass regression test)
**Supersedes:** none
**Superseded by:** none
**Depends on:** ADR-052 (multi-model dispatch by role — the per-agent `model:`
frontmatter mechanism this ADR makes the *sole* tiering channel); ADR-064
(llm-routing/FinOps)

## Context

ADR-052 established per-role model dispatch: each agent definition in
`.claude/agents/*.md` declares its own `model:` frontmatter (code-reviewer /
security-engineer / identity-trust / incident-commander / threat-detection =
opus; llm-finops / performance / qa-architect = sonnet; devops = haiku).

At S206 (PLAN-128 Wave-1, Owner-GPG `c9504982`) the env var
`CLAUDE_CODE_SUBAGENT_MODEL=haiku` was wired **globally** into
`.claude/settings.json`, the adopter template `templates/settings/settings.base.json`,
`route.py`'s documented `SETTINGS_DELTA`, and propagated to app repos by
`scripts/install-accelerators.sh` — intending "cheap Explore/read helpers."

But that env var is **documented** (https://code.claude.com/docs/en/model-config)
to *override* the per-invocation `model` parameter **and** the subagent
definition's `model:` frontmatter; `inherit` restores normal resolution. So the
global `haiku` **flattened the entire ADR-052 tier to haiku** for ~11 sessions
(S206→S217): the framework's own VETO rites (code-review, security) ran on a
weaker model than declared, and in 3 adopter lab repos the Owner's deliberately
sonnet/opus subagents ran haiku too — silent degradation discovered at S218 only
via the turbo banner showing `model=haiku`. (Codex, an external GPT-5-codex CLI,
was unaffected — which mechanically explains why the cross-model pair-rail kept
catching what the [haiku] debate missed.) No test asserted the env value, which
is why it shipped and ran unnoticed; the existing template/dogfood parity test
diffs only HOOK tuples, not `env`.

## Decision

**Subagent model tier is declared EXCLUSIVELY via per-agent `model:` frontmatter
(the ADR-052 mechanism). A global `CLAUDE_CODE_SUBAGENT_MODEL` model-pin is
PROHIBITED in framework `settings.json`, the adopter template, and anything the
installers write.** The key, where present, MUST be `inherit` (normal resolution:
explicit `model:` honored; omitted → main-loop model).

- "Cheap" is **opt-in per helper** — set `model:` in the agent's frontmatter
  (e.g. `devops`, or an Explore/search agent), or pass `model` at spawn time —
  never a global override.
- `scripts/install-accelerators.sh` FORCES `inherit` into an adopter's env
  (corrective: re-running repairs a previously poisoned app) and announces the
  reset rather than silently propagating the framework's value.
- Enforcement is mechanical: `.claude/hooks/tests/test_subagent_model_override_removed.py`
  asserts both settings files are `inherit` (+ env-parity, since the hook-parity
  test does not cover `env`), the `route.py` doctrine, that strong rites' frontmatter
  is not haiku, and that the installer forces `inherit` and never propagates/hardcodes
  a global value.

## Consequences

- Governance VETO rites run their declared opus/sonnet models again; adopter model
  intent is honored. Cost rises modestly (~$1–3/session of restored opus/sonnet
  subagent spend) — accepted: a VETO rite's correctness dominates its token cost,
  and the FinOps lever stays available per-agent.
- Any pre-S218 §7 A/B "ON" arm is confounded (cheap-model forcing was bundled with
  the accelerators, not isolated) — a clean multiplier needs a re-run.
- The doctrine is intent-level: a future contributor (or a future session's Claude)
  cannot re-introduce the global override without explicitly **superseding** this
  ADR, and the regression test blocks it at CI. Two-layer guard (test + ADR).
- **S220 nuance — per-call override is inert for Workflow subagents:** with the env
  at `inherit`, a Workflow-tool `agent({model:'haiku'})` per-call override ALSO does
  not take effect — `inherit` dominates and `opts.model` is silently ignored. So
  model tiering for WORKFLOW subagents is NOT achievable today: the only levers that
  change a subagent's tier are env/settings (`CLAUDE_CODE_SUBAGENT_MODEL`, which this
  ADR pins to `inherit`) and the per-AGENT-definition `model:` frontmatter. This
  qualifies the Decision's "or pass `model` at spawn time" — that path works for
  agent-definition dispatch but is a no-op via the Workflow `agent()` tool. No
  re-pin is warranted (it would re-introduce the prohibited global flatten); the
  per-agent `model:` frontmatter remains the sole working tiering channel.
  *(Refuted in part — see the S328 amendment at the end of this ADR.)*

## Alternatives considered

- **Keep the global `haiku` override (status quo pre-S218):** rejected — it is
  documented to beat explicit `model:` and silently degrades governance rites +
  adopter work; the whole defect.
- **Swap the global pin to a `sonnet` minimum:** rejected — still a *global*
  override that beats explicit `model:`; same class of bug, just a different
  silent value. Per-agent frontmatter is the only channel that respects intent.
- **Rely on the regression test alone, no ADR:** rejected — the test blocks the
  mechanism but not the *intent*; the ADR is the not-silent decision record so the
  constraint survives a refactor that rewrites the test.
- **Set `CLAUDE_CODE_SUBAGENT_MODEL=inherit` explicitly vs delete the key:**
  chose `inherit` — it is self-documenting and corrective (re-running the installer
  overwrites a poisoned `haiku` back to `inherit`), whereas an absent key is silent.

## Amendment (PLAN-169 W4.3 / S328, 2026-08-25) — `opts.model` is NOT inert: the Workflow rail ROUTES the model

**What this refutes.** The §S220 nuance above rests on a SUBSTRATE claim that
has since been measured FALSE. Three of its assertions no longer hold:

- `:89` — "`inherit` dominates and `opts.model` is silently ignored";
- `:90-91` — "model tiering for WORKFLOW subagents is NOT achievable today";
- `:96` — "the per-agent `model:` frontmatter remains the sole working tiering
  channel".

**The measurement** (`.claude/plans/PLAN-169-closure-and-cross-session-evolution.md:704-715`
— the W4.3 probe-first slice, closed in S316, 2026-08-20). Harness **2.1.237**,
probe `wf_9ddadaab-12f`, **2 agents**:

- dispatched with `opts.model='haiku'`, the model **SERVED** in the transcript
  turns was `claude-haiku-4-5-20251001`;
- the control agent, dispatched with **no** override, inherited `claude-fable-5`.

Evidence: `agent-a3fbe640*.jsonl` / `agent-a8dea319*.jsonl` and their
`.meta.json` — read from the `model` field of the **RESPONSE** envelope, i.e.
what the substrate *served*, not what the caller *asked for* ("servido, não
pedido"). The plan's verdict, quoted: "**`agent(...,{model})` NÃO é mais inerte
— o rail Workflow ROTEIA modelo na versão corrente.**"

**Scope — deliberately narrow.** This is an observation about a SUBSTRATE at a
pinned version: harness **2.1.237**, **n=2**, one model pair. It is not a
timeless property and carries no forward guarantee — the Workflow rail routed
`opts.model` on the version measured, and a later harness may stop doing so
without announcing it. Anything that depends on the routing should VERIFY it
(the `model` field of the response envelope is the check) rather than assume it.

**What does NOT change.** The Decision is untouched: `CLAUDE_CODE_SUBAGENT_MODEL`
stays pinned to `inherit` and the global override stays prohibited. The defect
this ADR codifies was the *global flatten* beating explicit per-agent intent,
and that reasoning is independent of whether the per-call override works. What
changes is only §S220's claim that Workflow subagents have NO working tiering
lever: they have one on this harness, so the Decision's "or pass `model` at
spawn time" reads literally for the Workflow `agent()` path too — and tier
routing in Workflow becomes claimable, which §S220 forbade.

**Named, not silently left.** Two further sites still carry the refuted claim
and are NOT edited by this amendment (they are the inheritors flagged at
`PLAN-169:713-714`):

1. `.claude/plans/PLAN-178-mast-audit-substrate-adoption.md:402-403` (AC-3) —
   "opts.model é INERTE no Workflow, as economics diferem por caminho";
2. `.claude/workflows/eval-baseline-n20.js:3` — the workflow `description`
   ("Because Workflow opts.model is INERT (W0a verdict,
   PLAN-134/W0a-VERDICT.md)"), echoed at `:284` and `:547`.

Whether they travel in this package or in a follow-up is **PLAN-169 §Open
questions OQ-11** — an Owner call, not decided here. The second site's
*mechanism* is unaffected either way: running the subject model in a
`claude -p --model` subprocess remains correct, it is simply belt-and-braces
now rather than the only option.
