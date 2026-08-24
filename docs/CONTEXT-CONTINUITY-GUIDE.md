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

> **PLAN-179 changed the failure mode here, not the measurement.** The
> measurement above is what a pre-PLAN-179 build did and is kept verbatim as
> history. A session-scoped fallback now ships, so an unresolved plan id no
> longer costs you the snapshot — see §7 for exactly what changed and what
> remains unproven.

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
in an **interpolated** 45–55k band.

> **That band is REFUTED by measurement — do not plan against it.** `F` was
> measured at a real compaction boundary at **97,292 tokens** (`TOTAL_IN`
> 112,638 − `postTokens` 15,346 = `cache_read` 68,980 + `cache_creation`
> 28,310), with an independent cold-`F` control at **97,097** in the same
> session (delta 0.20%). The interpolated band was built from a chars/4
> estimate of the DOCUMENTS only; it omitted the system prompt, the tool
> definitions and `cache_creation`.
>
> `F` is also **not a constant**. A cold-`F` series of n=41 (censoring
> declared) gives min **84,101** / median **98,636** / max **138,552**,
> pstdev **16,148** — a spread of 51.7% of the mean. Reporting only the mean
> misleads; size your threshold against the upper end.

Taking `F = 97k` (the measured median ≈ 98.6k) and `S = 10k`:

| `T` | η | Reading |
|---|---:|---|
| 184k | 42% | mediocre |
| 150k | 29% | thrashing |
| 120k | 11% | thrashing |
| 80k | negative — the working set does not fit | broken |
| 60k | negative | broken |

The practical consequence for an adopter: the thrashing floor is `T ≈ 107k`
(`F + S`), **above** the API's own minimum (`trigger.value = 50000`). So on a
repo with a governance surface this size, continuity works in SHORT sessions
and degrades exactly where you would want it most. Measure your own `F` before
trusting any figure here — the instrument is
`.claude/plans/PLAN-179/w0/gateboot_repay.py`.

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
- **`CEO_CONSTRAINT_PINNING=0`** — disarms constraint pinning (§7) on both its
  channels, and nothing else. It is deliberately **separate** from
  `CEO_COMPACTION_CONTINUITY=0`: that switch is documented as turning off the
  continuity *snapshot*, and letting it also silently drop the governance
  floor would make one operational decision quietly into another.
- **`CEO_CONTEXT_PROGRESS_FLOOR_TOKENS`** — not an off switch but an arming
  one, and **unset by default**: the progress observer (§7) is a no-op until
  you give it a floor. There is no built-in default, because a floor that was
  never measured against your install is a magic number.
- **`CEO_SOTA_DISABLE=1`** — the framework-wide master switch that forces
  advisory behaviour and disables the SOTA-side machinery (advisory dampening,
  OTel export, the learning loop, and the blocking guards' enforcement).
  **It does not disable the compaction pair**: neither
  `check_precompact_continuity.py` nor `check_postcompact_reinject.py` reads
  it, because both are already advisory and fail-open. Do not set it expecting
  compaction hooks to stop; set `CEO_COMPACTION_CONTINUITY=0` for that.

None of these switches can block a compaction, and none is a recovery route
for a lost session — they only reduce what the framework does around the event.

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
   default path above. Post-PLAN-179 (§7) two more fields are worth reading:
   `snapshot_outcome=written_session_scope` says the fallback caught an
   unresolved plan id, and `constraint_count` counts pinned constraints —
   read an **absent** `constraint_count` as a producer that predates pinning,
   never as "zero constraints pinned".

## 6. Known limitations (the honest list)

- **The design's own fires-proof came back negative.** ADR-153 shipped with the
  live proof marked PENDING; the proof now exists and shows the events firing
  while delivering nothing (§2).
- **Plan-id resolution is still anti-correlated with long sessions.** The
  snapshot write no longer depends on it (§7's session-scoped fallback), but
  plan-*scoped* continuity does: an unresolved id gets you a snapshot, not a
  plan-scoped one.
- **Nothing writes memory automatically.** `SessionEnd.py` verifies
  writability only.
- **A pointer is not a preserved constraint.** The *pointer* block is a
  reminder, not the rules. Constraint pinning (§7) now re-states a small set
  of rules themselves, but only that set — everything outside it is still a
  pointer at best.
- **Nothing halts compaction thrashing.** A progress *observer* ships (§7) and
  will tell you a compaction failed to free headroom; it cannot stop the next
  one. No hook on this path has a deny channel.
- **The `η` table is a chars/4 estimate** with an interpolated floor.
- **Governance-decay percentages come from external published measurement**,
  not from this framework.
- **Two blind spots inherited from being a hook**: a settings change that
  disables hooks disarms these too, and any file written outside the harness
  fires no event at all (ADR-153 §H2).

## 7. What PLAN-179 W0/W1 changed — and what it deliberately did not

The W0/W1 cure for §2 **landed** through an Owner-signed ceremony. It is
installed, registered in `.claude/settings.json`, and running. Three things
changed:

- a **session-scoped fallback** — the snapshot is written even when no plan id
  resolves, reported as the new `snapshot_outcome=written_session_scope` and
  leaving `scratchpad_unavailable` to mean a real I/O failure. This is the
  direct answer to the §2 measurement, where an unresolved plan id cost the
  snapshot entirely;
- **constraint pinning** — a small, closed set of invariants held as a *code
  constant* (`.claude/hooks/_lib/pinned_constraints.py`, never read from a
  document at runtime, so a summarizer cannot evict it) and re-stated after a
  compaction. The **primary** channel is `check_compact_pinning.py` on
  `SessionStart(source="compact")`, newly registered; the PostCompact block
  re-emits the same set as **reinforcement**. Count on the wire:
  `constraint_count`. Switch: `CEO_CONSTRAINT_PINNING=0` (§4);
- a **progress observer** on the PreCompact path, arming on
  `CEO_CONTEXT_PROGRESS_FLOOR_TOKENS` and emitting the new edge-triggered
  `context_pressure_observed` audit action.

### Read this before you rely on any of it

**The progress observer observes and notifies. It cannot halt a compaction.**
Two independent reasons, and neither is an implementation gap to be fixed
later on this surface: a `PreCompact` hook **has no deny channel** — there is
no value it can return that stops the event — and by the time it fires **the
harness has already decided to compact**. What you get is a stderr breadcrumb
for the operator plus one closed-enum audit event. If you set a floor
expecting back-pressure, you will not get it. An actual valve would have to
live on a surface that owns a decision, and no such surface ships today.

**The PostCompact channel verdict is still unproven.** Whether
`PostCompact`'s `additionalContext` is genuinely *consumed* by the model
remains open — the W0-1 probe has not returned a verdict. The S309 fires-proof
established only that the hook fires and delivers nothing useful, which is not
the same question: proving a hook ran does not prove its output was read. This
is exactly why pinning treats `SessionStart` as primary (that channel has a
positive local precedent) and PostCompact as reinforcement. Do not read the
pinning block's existence as evidence that the PostCompact channel works.

Sections 2 through 6 still describe the surrounding behaviour; §2's
measurement is retained as pre-PLAN-179 history, not as current output. Track
the remaining waves in
`.claude/plans/PLAN-179-context-continuity-durable-state.md` (W2–W4) and the
amendment to `.claude/adr/ADR-153-compaction-continuity.md`.
