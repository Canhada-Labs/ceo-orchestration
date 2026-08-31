<!--
  compaction.md — editable nine-section conversation-compaction template
  (PLAN-133 / Wave D / item D4 — context management)

  PURPOSE
    When a session approaches its context budget and must be compacted, the
    model is asked to rewrite the transcript-so-far into a single dense
    summary. An UNSTRUCTURED summary drops load-bearing state (open blockers,
    env flags, staged canonical edits). This template fixes the OUTPUT SHAPE
    so nothing critical is lost.

  HOW IT IS USED
    This is an EDITABLE, NON-CANONICAL framework template. It is plain
    Markdown — copy it into a target repo (or keep it here for the meta-repo),
    then EXTEND the sections for your domain (extend, never trim — see the
    sharp edge in "How this template is actually used" below). Feed the
    rendered template as the compaction instruction; the model fills each of
    the nine sections from the live transcript. Empty sections must be emitted
    as the literal "(none)" so a reader can tell "nothing here" from "the
    model forgot".

  DELIVERY CHANNEL — USE DOCTRINE (PLAN-179 W3 US10, declared S334)
    The consumer of this template is the OPERATOR, through the interactive
    `/compact <instructions>` command of the CLI, in long sessions that are
    about to compact and carry load-bearing state. It is deliberately NOT
    wired to the API `instructions` parameter of `compact_20260112`: that
    parameter REPLACES the default compaction prompt wholesale
    (PLAN-179/research-S309.md §1), so an incomplete rendering there is
    strictly worse than the default — omission becomes recall loss. The
    mechanical half of continuity does not live here at all: constraint
    re-injection travels through its own channel (pinned constraints via
    SessionStart(matcher=compact) + PostCompact, PLAN-179 W1-b), which does
    not depend on the operator remembering this template.

    WHO FEEDS IT: an operator, manually. Nothing in this framework feeds this
    template automatically, and inside Claude Code nothing can — the routes
    and the local evidence are evaluated in the first section of the body
    (PLAN-179 W3 / US10). The earlier claim that the "D1 auto-compact policy
    in scripts/context-budget.py" drives this template was never true: that
    probe has no caller anywhere in the repo (see the same plan, US11).

  DESIGN RULES (so the summary survives a fresh session boot)
    1. Every section header below is STABLE — do not rename them; downstream
       readers and any future parser key off the exact "## N. <Title>" line.
    2. Preserve EXACT identifiers verbatim: file paths (absolute), commit
       SHAs, PLAN-/ADR- ids, env-flag names, closed-enum audit actions.
       Never paraphrase an identifier — a summary that says "the audit hook"
       instead of ".claude/hooks/audit_log.py" is lossy.
    3. NEVER echo a secret value. If a credential/token/key appeared in the
       transcript, record only that it appeared and was handled — never the
       value itself (mirrors the framework's no-value-echo audit doctrine).
    4. Prefer bullets over prose. Compaction is for density, not narrative.
    5. If a fact is uncertain, mark it "(unverified)" rather than asserting it.

  CONTAMINATION NOTE
    This template ships in the framework core (templates/). Do NOT hardcode
    personal handles, real names, employer names, or adopter project names
    here. Use the literal placeholder @OWNER for the maintainer and
    <project> for the target repo. The contamination scanner
    (.claude/scripts/check_contamination.py) gates this file.
-->

## How this template is actually used

> **Verdict (PLAN-179 W3 / US10, recorded 2026-08-18).** This template is
> **not** wired to anything automatically, and — inside Claude Code — it
> **cannot be**. It is fed by a human, on one route only. The two candidate
> routes were evaluated against what this repository can actually verify
> locally; the evidence for each is named below. Do not read this section as
> a promise of wiring: it is the honest boundary.

### Route (a) — `/compact <instructions>` in the CLI · **USABLE, MANUAL ONLY**

Typing `/compact` followed by instruction text hands that text to the
harness's summarizer. Local evidence that the harness carries such a field:
the pinned hook schema `.claude/data/hook-schema-2.1.220.json` declares

    "PreCompact": { "trigger": "enum[manual,auto]",
                    "custom_instructions": "string|null" }

so a manual compaction genuinely transports operator-authored instructions.

Two consequences follow from the SAME schema file, and both are load-bearing:

1. **No hook can supply this template.** The schema's `_absent_arms_note`
   lists `PreCompact` among the events with **no `hookSpecificOutput` arm** —
   there is no `additionalContext`, and no field a hook may return to SET
   `custom_instructions`. A `PreCompact` hook may observe the compaction, and
   may BLOCK it (exit 2), but it cannot author the instruction. Automation of
   this route is therefore not available; the operator pastes the template.
2. **Auto-compaction gets nothing.** On `trigger = auto`,
   `custom_instructions` is `null` — nobody typed anything. The auto path is
   the DOMINANT path for long sessions (the exact finding recorded against
   ADR-153), so this template covers the case that happens least often.

### Route (b) — the API `instructions` parameter · **ADOPTER-ONLY, UNVERIFIED HERE**

The server-side compaction tool takes an `instructions` string that replaces
the default summarization prompt. Inside this repository that route is
**documented but not exercised**: the only local description lives in
`.claude/plans/PLAN-179/research-S309.md §1.1` (a research note citing the
vendor docs — external content, recorded as DATA), and a repo-wide grep for
the tool identifier and for `context_management` finds **no caller** — only
plan and research prose. This framework installs into a Claude Code harness;
it does not own an API request loop, so it cannot exercise route (b) at all.

Route (b) is real for an **adopter** who owns their own API loop. For them,
rendering this template into `instructions` is the wiring. For this
repository, treat it as unverified-locally: mark any claim about it
`(unverified)` until a probe demonstrates it end-to-end.

### THE SHARP EDGE — `instructions` REPLACES, it does not append

On route (b) the `instructions` string **substitutes the default
summarization prompt in its entirety**. Nothing is merged and nothing warns
you. Any recall the default prompt would have produced, and that this
template does not explicitly ask for, is **silently lost** — the summary
looks complete and is not. The same hazard applies in spirit to route (a):
whatever you type steers the summarizer away from its default behaviour.

Therefore:

- Send the template **whole**. Trimming a section for brevity is deleting a
  recall requirement, not saving tokens.
- When you add a domain section, **add** it — never replace one of the nine.
- A section with nothing to report is emitted as the literal `(none)`. That
  is what distinguishes "nothing here" from "the instruction did not ask".
- After a compaction driven by this template, spot-check that all nine
  headers came back. A missing header is evidence of instruction loss, not
  of an empty session.

### Status of the automatic route

**BLOCKED ON A PROBE.** No automatic route exists today, and route (a) is
structurally closed to automation for the reason given above. Any future
claim that this template feeds compaction automatically must cite a probe
that (i) emits a unique canary through the chosen channel and (ii) FAILS when
the canary is withheld — a positive control. Until such a probe exists, the
honest description of this file is: *a manual instruction the operator
pastes, plus a shape contract the nine sections below define.*

---

# Session Compaction Summary — `<project>` @ `<session-id>`

> Compacted at: `<UTC timestamp>` · Trigger: `<manual | auto-compact>` ·
> Pre-compaction context: `<NN%>` of budget.
> Replace every `<...>` placeholder. Emit `(none)` for any section with no
> content — never delete a section header.

---

## 1. Mission & objective
<!-- The single goal this session is driving toward. One or two sentences.
     Include the plan/item reference if there is one (e.g. PLAN-133 item D4). -->

- Goal:
- Plan / item ref:
- Scope boundary (what is explicitly OUT of scope):

## 2. Key decisions & rationale
<!-- Decisions already MADE this session that future turns must honor.
     Each line: the decision + the one-line reason. These are commitments,
     not options. -->

- Decision · rationale:

## 3. Files & artifacts touched
<!-- Exact absolute paths. Group by disposition. Canonical edits that are
     STAGED (not applied) belong under "staged" with their staged path. -->

- Created:
- Edited (non-canonical):
- Staged for Owner-GPG (canonical proposals, path under .claude/plans/.../staged/):
- Deleted:

## 4. Current state — what works, what is pending
<!-- The ground truth right now. A reader booting fresh trusts THIS section
     to know where the work actually stands. -->

- Working / verified:
- Built but unverified:
- Pending / not started:

## 5. Open problems & blockers
<!-- Anything that stops forward progress, or a known defect not yet fixed.
     Mark the single highest-priority blocker first. If none, write (none). -->

- Blocker (priority order):

## 6. Next steps (ordered)
<!-- The concrete, ordered actions the NEXT turn should take. Be specific
     enough that a fresh session could execute step 1 without re-deriving it. -->

1.
2.
3.

## 7. Constraints & operating context
<!-- The rails that must not be violated: governance doctrine, default-OFF
     env flags in play, canonical-vs-non-canonical boundaries, latency/quota
     budgets, sequential-write collision constraints. Name env flags exactly. -->

- Governance / doctrine in force:
- Active env flags (name = value, default-OFF behavioral changes):
- Canonical boundary (files that need Owner-GPG, must NOT be edited directly):
- Budget limits (quota / latency / cost cap):

## 8. Test & verification status
<!-- What was run, and the honest result. Distinguish "ran and passed" from
     "assumed passing". Name the suite/command and the pass/fail count. -->

- Command(s) run:
- Result (pass / fail / partial / not-run):
- Coverage / gate notes:

## 9. References
<!-- Pointers a fresh session needs: plan files, ADRs, memory topic files,
     commit SHAs, relevant skill names. Verbatim ids only. -->

- Plans:
- ADRs:
- Memory topics:
- Commits / branches:
- Skills / tools:

---

<!--
  END OF TEMPLATE. The nine "## N." headers above are the contract; a valid
  compaction renders all nine, in order, with no header removed.
-->
