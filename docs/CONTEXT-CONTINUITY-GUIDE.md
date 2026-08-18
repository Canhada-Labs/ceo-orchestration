# Context-Continuity Guide — what actually survives a compaction

> **For adopters.** You installed this framework into your repo and want to
> know what happens to governance state when the harness compacts a long
> session. Short answer: **less than the design intended**, and this guide
> says exactly how much less. Every number here is either measured (with the
> raw field named) or explicitly labelled an estimate.
>
> Sources: `.claude/adr/ADR-153-compaction-continuity.md` (the design),
> `.claude/plans/PLAN-179-context-continuity-durable-state.md` §1 and §5 (the
> measured negative result and the honest boundaries).

## 1. What a compaction is, and when it fires

When a conversation approaches the context window, the Claude Code harness
**compacts** it: the transcript is replaced by a model-written summary. It
happens two ways — you type `/compact` (manual), or the harness crosses its
auto-compaction threshold (auto).

The harness fires two lifecycle events around it, and this framework registers
one hook on each (`.claude/settings.json`, the `PreCompact` and `PostCompact`
blocks):

| Event | Hook | Job |
|---|---|---|
| `PreCompact` | `.claude/hooks/check_precompact_continuity.py` | Snapshot governance state before the transcript collapses |
| `PostCompact` | `.claude/hooks/check_postcompact_reinject.py` | Read that snapshot back, reinject **pointers** into the model's context |

Both are ADVISORY and fail-open: any error is a stderr breadcrumb plus an
empty allow. **A compaction is never blocked by this framework.**

The thing to internalise: the summary is written by a model, from the
transcript, with no obligation to preserve your rules. Your Gate-1 reads were
*inputs* to that summary, not preserved text — after a compaction they are
gone unless something puts them back.

## 2. What survives today — and what does not

### Survives

**One thing reliably: a re-read reminder.** `check_postcompact_reinject.py`
always emits a first pointer telling the model that context was compacted and
that it should re-read CLAUDE.md §0 Gate-1 and the active plan. That line is
unconditional and does not depend on any snapshot.

Everything else is conditional on the snapshot existing. When it does, the
block can also carry the active `PLAN-NNN`, the execution-unit position as a
`path:line` **location only**, pending Owner-ceremony breadcrumbs (up to 5),
an audit HMAC-chain anchor, a staleness warning past 12 hours, and the
scratchpad address for the detail.

Hard caps in the shipped code, so you can size expectations:

- **at most 9 pointer lines** total (`_build_pointers` returns `pointers[:9]`);
- **200 characters per line**, non-printable-ASCII replaced with `?`
  (`_sanitize_line`);
- **64 KiB** for the whole snapshot blob (the scratchpad per-key cap);
- **pointers only — never file contents.** The plan body, the checkbox label,
  a ceremony script's text: none of it is injected. That is a deliberate
  anti-injection boundary (ADR-153 §Decision-2), not an oversight.

### Does not survive

**Be blunt about this: in the one live measurement that exists, nothing but
the generic reminder came back.** A real auto-compaction on 2026-08-16 fired
both hooks and delivered no governance state. The audit events, field for
field:

```
action=compaction_continuity_snapshot  trigger=auto  plan_id=unknown
    chain_length=11179  snapshot_outcome=scratchpad_unavailable
action=compaction_context_reinjected   plan_id=unknown
    snapshot_found=false  snapshot_age_s=0  pointer_count=1
```

`pointer_count=1` is the generic reminder and nothing else. The snapshot was
never written.

**Why, structurally.** The snapshot is written to a *plan-scoped* store, so it
needs a plan id. `scratchpad_lib.resolve_plan_id()` derives that id from
`plan_transition` audit events **belonging to the current session** — never
from an environment variable, because env vars are agent-spoofable. But a
`plan_transition` is only emitted when a plan *changes status*. A session that
works all day inside an already-executing plan never emits one. Census in this
repo's own log at the time of measurement: **2 `plan_transition` events in
12,515 lines**, both from an earlier session, both filtered out.

So plan-id resolution succeeds mainly in sessions that happen to flip a plan's
status — which are the **short** ones. The mechanism is anti-correlated with
its own use case. ADR-153 filed this as "residual risk #3, fail-open by
design"; the measurement shows it is the *default* path, not an edge.

**Also does not survive:** memory files. `.claude/hooks/SessionEnd.py` only
*checks* that the memory directory is writable — it writes nothing. Durable
memory is entirely the model's discretion at a closeout that a
context-exhausted session never reaches.

**And a pointer is not a rule.** Even a fully populated pointer block tells the
model *where to look*, not *what the rule is*. Published work measured
governance constraints surviving a summary at 0% violation versus 38% when
omitted (30% average, up to 59%). Those numbers were measured elsewhere, not
in this framework — motivation, not a property of your install.

## 3. The working-set floor — why a fat Gate-1 makes compaction worse

Compaction is not free. It resets you to a **floor** you re-pay in full: the
system prompt, tool definitions, and this framework's Gate-1/Gate-2 governance
reads. Call the floor `F`, the summary `S`, the compaction threshold `T`. Useful
work per cycle is `T − F − S`, so cycle efficiency is:

```
η = (T − F − S) / T
```

Measured on this repo with the documented **chars/4 heuristic** (`1 token ≈ 4
chars`, `.claude/scripts/context-budget.py`) — **these are estimates, not
tokenizer counts**: Gate 1+2 ≈ **40,116 estimated tokens**, the memory index ≈
**4,413 estimated tokens**. Adding system prompt and tool definitions puts `F`
in an **interpolated** 45–55k band. Taking `F = 50k`, `S = 10k`:

| `T` | η | Reading |
|---|---:|---|
| 184k | 67% | healthy |
| 150k | 60% | healthy |
| 120k | 42% | mediocre |
| 80k | 25% | thrashing |
| 60k | 0% | never progresses |

Three consequences for an adopter:

1. **The thrashing floor is roughly `T ≈ F + S`.** For this framework's own
   surface that is ≈60k — *below* it you re-pay more than you produce.
2. **The lever is `F`, not `T`.** Lowering the compaction threshold without
   shrinking your governance surface only picks a worse point on the same
   curve.
3. **The shape of the curve is robust; the absolute numbers are not** until
   `F` and `T` are measured with a real tokenizer. PLAN-179 W0 owes that
   measurement.

If your install carries a large CLAUDE.md, a large team file, and an eagerly
loaded skill catalog, your `F` is bigger than this repo's and your η is worse.
Trimming what Gate-1 loads is the highest-leverage change available to you.

## 4. Kill switches — and what turning them off costs

- **`CEO_COMPACTION_CONTINUITY=0`** — the real switch for this pair. Both
  hooks check it and return an empty result immediately. Cost: you lose the
  snapshot and the reinjected pointer block, including the unconditional
  Gate-1 reminder. Given §2, what you are giving up today is mostly that one
  reminder — but it is the only automatic re-anchor you have.
- **`CEO_SOTA_DISABLE=1`** — the framework-wide master switch that forces
  advisory behaviour and disables the SOTA-side machinery (advisory dampening,
  OTel export, the learning loop, and the blocking guards' enforcement).
  **It does not disable the compaction pair**: neither
  `check_precompact_continuity.py` nor `check_postcompact_reinject.py` reads
  it, because both are already advisory and fail-open. Do not set it expecting
  compaction hooks to stop; set `CEO_COMPACTION_CONTINUITY=0` for that.

Neither switch can block a compaction, and neither is a recovery route for a
lost session — they only reduce what the framework does around the event.

## 5. What to do operationally, today

Given §2, do not rely on the machinery. Rely on habits:

1. **Keep sessions scoped to one unit of work.** A session that never
   approaches the threshold never tests any of this.
2. **Write durable state at work boundaries, not at session end.** When a unit
   finishes — a commit, a decision, a ceremony — write it to a file *then*.
   The measured failure is that state writes are attached to terminal events a
   dying session does not reach.
3. **Record identifiers, not prose.** Absolute paths, commit SHAs, plan and
   ADR ids. A summary paraphrases prose; it cannot paraphrase a SHA on disk.
4. **After any compaction, re-read your governance files explicitly.** Assume
   the model holds a summary of them, not the text.
5. **Prefer manual `/compact` at a boundary you choose** over an auto-compact
   mid-unit — you control what was just written down.
6. **Check the two audit actions** (`compaction_continuity_snapshot`,
   `compaction_context_reinjected`) against your own install. Seeing
   `snapshot_found=false` with `pointer_count=1` means you are on the measured
   default path above.

## 6. Known limitations (the honest list)

- **The design's own fires-proof came back negative.** ADR-153 shipped with the
  live proof marked PENDING; the proof now exists and shows the events firing
  while delivering nothing (§2).
- **Plan-id resolution is anti-correlated with long sessions**, and the
  snapshot write depends on it.
- **Nothing writes memory automatically.** `SessionEnd.py` verifies
  writability only.
- **A pointer is not a preserved constraint.** The reinjected block is a
  reminder, not the rules.
- **No guard against compaction thrashing ships today.** If a compaction fails
  to free useful headroom, nothing halts the next one.
- **The `η` table is a chars/4 estimate** with an interpolated floor.
- **Governance-decay percentages come from external published measurement**,
  not from this framework.
- **Two blind spots inherited from being a hook**: a settings change that
  disables hooks disarms these too, and any file written outside the harness
  fires no event at all (ADR-153 §H2).

## 7. Staged, not shipped — do not plan around it

A cure for §2 exists as **staged work awaiting an Owner-signed ceremony**
(`.claude/plans/PLAN-179/staged-w01/`) — **not installed, not registered in
`.claude/settings.json`, not running.** None of the following is in your tree
today:

- a **session-scoped fallback** so a snapshot would be written even when no
  plan id resolves, adding a `written_session_scope` outcome and reserving
  `scratchpad_unavailable` for real I/O failure;
- **constraint pinning** — a small, closed set of invariants held as a *code
  constant* (never read from a document at runtime) and re-stated after a
  compaction, with `SessionStart(source="compact")` as the primary channel and
  the PostCompact block as reinforcement, under its own proposed
  `CEO_CONSTRAINT_PINNING=0` switch;
- a **progress guard** that would halt repeated compactions that fail to free
  a named token floor.

Until an Owner ceremony lands those files, treat sections 2 through 6 as the
complete description of behaviour. Track the work in
`.claude/plans/PLAN-179-context-continuity-durable-state.md` (waves W0–W4) and
the amendment it will make to `.claude/adr/ADR-153-compaction-continuity.md`.
