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

The user invoked: `/council $ARGUMENTS`

**Parse `$ARGUMENTS` FIRST** as `<scope> [vendors=claude,codex,grok]
[budget=<n>]`. The scope is the FIRST token (or quoted phrase) of
`$ARGUMENTS` and it is **MANDATORY**:

- **`scope` is the egress boundary the Owner authorized.** It MUST be the
  operator's literal typed argument, threaded verbatim into `args.scope`
  below. If `$ARGUMENTS` is empty or yields no scope, **STOP and ask the
  operator for one — do NOT launch the workflow.** `council-audit.js`
  silently defaults a missing/non-string `args.scope` to `.` (the WHOLE
  repo), which widens what leaves the process beyond what was authorized
  (the S270 F7 failure: scope `.claude/hooks/` was requested, scope `.`
  was transmitted).
- `vendors=` (optional) — subset of `claude,codex,grok` (default: all
  three).
- `budget=` (optional) — per-lane token ceiling, clamped to
  [10000, 400000] (default 120000). This is a **hard kill**, not advisory.

`/council` runs the `council-audit` workflow. This is multi-agent
orchestration with live external egress, so it requires the user to have
opted into workflows (the "ultracode"/explicit-workflow gate) — do NOT
launch it silently.

Before launching, echo the parsed scope back to the operator on one line
(`council scope = <parsed scope>`) so a scope drop is visible BEFORE any
egress. Then launch with the parsed values — `scope` must never be a
placeholder, never omitted, never invented:

```
Workflow({ name: "council-audit", args: { scope: "<the scope parsed from $ARGUMENTS, verbatim>", vendors: [...], budget_tokens_per_lane: <n> } })
```

The workflow returns `{ verdict, quorum, report, lanes, stats,
confirmed_findings, verify_failed_findings, cross_vendor_disagreements }`.
**Post-run scope assertion:** check the returned `scope` field equals the
scope you parsed; on mismatch, flag it at the top of your rendering — the
run's egress did not match the authorization. Render the `report` markdown
and lead with the quorum line, any `verify_failed` count, and any
cross-vendor disagreements.

## Audit trail

Each available lane emits a `council_lane_invoked` audit action (who
asked what, when) so cross-vendor egress is itself auditable
(completeness-bounded — an absent row is not evidence of an absent
invocation).
