<!--
  compaction.md — editable nine-section conversation-compaction template
  (PLAN-133 / Wave D / item D4 — context management)

  PURPOSE
    When a session approaches its context budget and must be compacted
    (manually via the compaction flow, or proactively by the D1 auto-compact
    policy in scripts/context-budget.py), the model is asked to rewrite the
    transcript-so-far into a single dense summary. An UNSTRUCTURED summary
    drops load-bearing state (open blockers, env flags, staged canonical
    edits). This template fixes the OUTPUT SHAPE so nothing critical is lost.

  HOW IT IS USED
    This is an EDITABLE, NON-CANONICAL framework template. It is plain
    Markdown — copy it into a target repo (or keep it here for the meta-repo),
    then trim/extend the sections for your domain. Feed the rendered template
    as the compaction instruction; the model fills each of the nine sections
    from the live transcript. Empty sections must be emitted as the literal
    "(none)" so a reader can tell "nothing here" from "the model forgot".

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
