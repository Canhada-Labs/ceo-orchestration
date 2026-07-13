---
description: Cross-Vendor Audit Council (PLAN-156) — run a read-only, three-vendor (Claude/Codex/Grok) audit of a scope and render a vendor-attributed verdict table. ADVISORY evidence only; transmits the audited scope to xAI + OpenAI (redacted). Operator/local only — never CI.
argument-hint: "<scope> [vendors=claude,codex,grok] [budget=120000]"
---

# /council — Cross-Vendor Audit Council

The Owner's "conselho": three independent vendor lanes audit the same
scope, every finding is adversarially re-verified in-harness, and the
result is REDUCED with **vendor attribution** — who confirmed, who
refuted, and (the headline signal) where the vendors **disagree**.

> **Read before your first run.** A council transmits the audited repo
> scope to **xAI** (grok lane, under your paid X account) and **OpenAI**
> (codex lane). Egress is redacted through the ADR-114 pair-rail redactor
> but not eliminated — third-party training/retention applies. This is
> the OQ5 privacy decision: run `/council` only on scopes you are willing
> to send to two external vendors. The Claude lane stays in-harness.

## What it is / is not

- **Is:** an ADVISORY audit instrument. Its verdict authorizes nothing on
  its own — the PROTOCOL.md verification cascade (V0–V3) is unchanged.
  Cross-vendor DISAGREEMENT is its reason to exist: a finding one vendor
  caught and the others missed is surfaced as the headline.
- **Is not:** a CI gate. No CI job invokes a live lane (three vendor
  secrets on a runner + unbounded burn + egress on every trigger are all
  forbidden). CI exercises only the shard-parse + fail-loud logic against
  fixture lane outputs.

## Containment (how each lane is proven read-only)

| Lane | Containment | Egress |
|---|---|---|
| Claude | ADR-136-AMEND-1 workflow read-only confinement (writes no files) | in-harness, no external egress |
| Codex | `codex exec --sandbox read-only` (Seatbelt/Landlock) | prompt redacted via ADR-114 first |
| Grok | `grok --sandbox council` (kernel profile, `.grok/sandbox.toml`) | prompt redacted via ADR-114 first |

A lane that cannot establish its containment, is missing its binary, has
lapsed auth, or exceeds its token/time budget reports **`STATUS:
unavailable`** — never a silent substitution. Quorum degrades explicitly
(3-lane → 2-lane, labeled).

## Execution

`/council` runs the `council-audit` workflow. This is multi-agent
orchestration with live external egress, so it requires the user to have
opted into workflows (the "ultracode"/explicit-workflow gate) — do NOT
launch it silently.

```
Workflow({ name: "council-audit", args: { scope: "<scope>", vendors: [...], budget_tokens_per_lane: <n> } })
```

Arguments:
- `scope` (required) — a subtree, file set, or topic to audit.
- `vendors` (optional) — subset of `claude,codex,grok` (default: all three).
- `budget` (optional) — per-lane token ceiling, clamped to [10000, 400000]
  (default 120000). This is a **hard kill**, not advisory.

The workflow returns `{ verdict, quorum, report, lanes, stats,
confirmed_findings, cross_vendor_disagreements }`. Render the `report`
markdown and lead with the quorum line + any cross-vendor disagreements.

## Audit trail

Each available lane emits a `council_lane_invoked` audit action (who
asked what, when) so cross-vendor egress is itself auditable
(completeness-bounded — an absent row is not evidence of an absent
invocation).
