---


id: SP-016
skill_slug: code-review-checklist
archetype: code-reviewer
proposed_at: 2026-04-28T00:00:00Z
source_lessons:
  - plan-045-session-46-f-10-09
scan_injection_pass: true
diff_size_added: 46
diff_size_removed: 0
sha256_of_diff: PENDING_ON_OWNER_SIGN
claims_declared: false
status: promoted
approved_by: 0000000000000000000000000000000000000000
applied_at: 2026-04-21T12:41:05Z
promoted_at: 2026-04-21T13:37:10Z
shadow_mode: false
---
# SP-016 — fluency-bias detection rubric for code-review-checklist

**Target:** `.claude/skills/core/code-review-checklist/SKILL.md`
**Archetype:** code-reviewer
**Kind:** behavioral rubric amendment (addition — no rewrites)
**Depends-on:** SP-001..015 promote (2026-04-27); enables SP-016
signing 2026-04-28+

## Rationale

PLAN-044 F-10-09 flagged a gap: PROTOCOL.md and docs/HONEST-
LIMITATIONS.md describe the Artifact Paradox conceptually, but the
code-review-checklist skill body carries the *general* cross-link
(SP-001 added 2026-04-20) without a concrete, procedural rubric that
a code-reviewer agent can actually *execute* when reviewing an
output.

This SP adds a 7-step concrete rubric the reviewer runs mentally on
every output with prose ≥200 chars. It turns the "treat fluency as
red flag" principle into a repeatable procedure.

Dependency note: SP-016 targets the SAME file as SP-001 (which
shipped 2026-04-20 and promotes 2026-04-27 after the 7-day ADR-031
soak). This SP is drafted for 2026-04-28+ signing to avoid
chain-overlap; SP-001 promote MUST land first.

## Provenance note

Draft authored Session 46 by CEO autonomously per PLAN-045
NEXT-TERMINAL-PROMPT-100.md Fase 2.2. Unsigned (Owner signs at
Session 47 ceremony 2026-04-28+ after SP-001..015 promote). Diff is
a pure addition (append-only) and applies via
`skill-patch-apply.py` which collects `+`-prefixed lines from the
fenced block below.

## Proposed diff

```diff
--- a/.claude/skills/core/code-review-checklist/SKILL.md
+++ b/.claude/skills/core/code-review-checklist/SKILL.md
@@ -310,0 +310,46 @@
+
+### Fluency-bias detection rubric (PLAN-045 F-10-09)
+
+Use this 7-step rubric on every agent output ≥200 chars of prose.
+The rubric is explicit because the Artifact Paradox is not a
+feeling — it is a measurable bias that lowers scrutiny by ~5.2 pp
+(Anthropic fluency research). Counter it with procedure, not vibes.
+
+**Step 1 — Score fluency first.** Before reading content, count:
+  - Complete-sentence density (≥80% complete sentences = HIGH)
+  - Confident language ("all tests pass", "fully handled", "all
+    edge cases", "complete", "done") ≥3 occurrences = HIGH
+  - Structure signals (bullets, headers, code-fenced diffs) ≥3
+    types = HIGH
+  HIGH fluency → mark this output for **deeper scrutiny**, not less.
+
+**Step 2 — Pick 1 random confident claim.** "All tests pass" → run
+  the test suite yourself. "No regression" → diff the test output
+  line-by-line. "Refactor preserves behavior" → spot-check 3
+  random call sites against new signature.
+
+**Step 3 — Scan for missing content.** Ask: what edge case is
+  NOT mentioned? For every `if X` the output lists, is there a
+  `not-X` branch path? For every happy-path test, is there a
+  failure-path test? Absence of negative cases is the #1
+  fluency-hidden gap.
+
+**Step 4 — Read the diff, not the summary.** Confident summaries
+  compress 500-line diffs into one sentence. That compression is
+  the same mechanism hiding the bug. Read every `+` line.
+
+**Step 5 — Count silent error paths.** `try/except: pass`,
+  `if err: return None`, `// ignore` comments. Fluent agents
+  produce clean-looking code around these. A code-reviewer who
+  skips them loses the defense.
+
+**Step 6 — Rerun adversarial inputs.** If the output asserts the
+  handler is robust, try: empty string, `null`, max-length, unicode
+  NFC/NFD, reserved words, adjacent-key collision. Fluent
+  refactors rarely re-add adversarial tests.
+
+**Step 7 — Record evidence.** When rejecting or flagging, cite the
+  exact file:line. Cite the exact test output. "I'm not sure this
+  is covered" is fluency-credulous language; "Line X has no case
+  for Y" is evidence.
+
+Cross-ref: `PROTOCOL.md` §Artifact Paradox + `docs/HONEST-
+LIMITATIONS.md` §4 + SP-001 cross-link seed (shadow-applied
+2026-04-20).
```
