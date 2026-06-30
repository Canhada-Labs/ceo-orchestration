---
name: help-me
description: Natural-language assistant that recommends <=3 contextual skills/commands for the Owner's current task. Activates on `/help me` slash command. Reads the active repo-profile + smart-loading resolver output, scores active skills against the redacted user description, returns top-3 with confidence labels and one-sentence rationales. Future canonical at .claude/skills/core/help-me/SKILL.md.
owner: CEO (vibecoder UX primitive)
domain: core
priority: 3
risk_class: low
context_budget_tokens: 1500
inactive_but_retained: false
repo_profile_binding:
  frontend: {active: true, priority: 3}
  engine: {active: true, priority: 3}
  fintech: {active: true, priority: 3}
  trading-readonly: {active: true, priority: 3}
  generic: {active: true, priority: 3}
activation_triggers:
  - {event: help-me-invoked, regex: "(?i)^/help.?me"}
audit_action: help_me_invoked
audit_volume_budget_per_hour: 30
---

# Help Me

> Block 2 vibecoder UX primitive. The Owner types `/help me <free-text>` and
> receives at most 3 contextual recommendations — short, ranked, each with a
> `[SAFE|NEEDS-CONFIRM|RISKY]` marker and a single-sentence rationale.

## Fail-Fast Rule

If the active repo-profile is missing or malformed, fall through to the
**fail-CLOSED default** (`trading-readonly`, per PLAN-083 §7.1) before any
recommendation is computed. Never serve recommendations against an unknown
profile silently — that path produces confident-but-wrong suggestions in
exactly the risk class (trading) that hurts Owner most.

If the active skill set returned by `smart-loading-resolver.py` is empty,
recommend the `/onboard` skill and stop. Do not synthesize recommendations
from skills the resolver suppressed.

## When to invoke

The Owner triggers this skill exclusively by the `/help me` slash command
(matched by `activation_triggers[0].regex = (?i)^/help.?me`). The trailing
text is the natural-language task description.

Examples that should activate:

- `/help me audit a Next.js page before launch`
- `/help me debug why the trade execution loop is stuck`
- `/help me draft a PR description for the consent migration`

Examples that should NOT activate (different skills handle them):

- `/spawn <Agent>` — that is the `spawn` skill
- `/onboard <path>` — that is the `codebase-onboarding` skill
- Plain prose with no slash — defer to the CEO Orchestration protocol

## Input handling — redact BEFORE any persistence (Sec P1)

The user's free-text description is treated as **untrusted, secret-bearing
input**. Before any audit emit, any debug log, any error message that quotes
the user's text, the description MUST pass through `_lib/redact.py`:

```python
from _lib.redact import redact_secrets
safe_description = redact_secrets(raw_description, max_chars=0)
```

The `max_chars=0` argument disables truncation so the matcher sees the
full redacted body; truncation, if any, is applied separately and only on
the redacted output. **Never** log, print, or persist the raw
`raw_description`. Even on internal exceptions, the error message MUST
reference the redacted form. This closes Sec P1 in PLAN-083 §6 row 1.11.

## Recommendation algorithm

The algorithm runs four steps, each deterministic and bounded:

1. **Resolve the active profile.** Read `.claude/repo-profile.yaml` via the
   resolver's `read_repo_profile()` helper (Wave 0a sub-agent 0.6 output).
   Fail-CLOSED to `trading-readonly` on any parse error.
2. **Load the active skill set.** Call the Wave 0b smart-loading resolver
   (`scripts/smart-loading-resolver.py:resolve()`) to produce the post-cap,
   post-arbitration list of active SKILL.md frontmatter dicts for the
   current profile. Dormant + suppressed skills are NEVER scored.
3. **Score each candidate skill** against the redacted description using
   two signals:
   - **Keyword match** — case-insensitive substring overlap between the
     skill's `description` field (frontmatter) and the redacted query
     tokens. Each overlap contributes 1 point.
   - **Activation-trigger match** — if any `activation_triggers[].regex`
     in the candidate's frontmatter `re.search`-matches the redacted
     query, that contributes 3 points (stronger signal than keyword).
   The score is a small integer; ties are broken by the smart-loading
   resolver's standard sort key (priority asc -> risk_class asc -> path
   lex), so the output is reproducible.
4. **Take top-3.** Strictly cap at 3 even when more candidates score >0.
   Attach a `[SAFE|NEEDS-CONFIRM|RISKY]` marker from `_lib/confidence_labels.py`
   (sub-agent 1.10 deliverable) using the candidate's `risk_class`:
   `low -> SAFE`, `medium -> NEEDS-CONFIRM`, `high -> RISKY`. Generate one
   sentence of rationale by extracting the first 120 chars of the skill's
   frontmatter `description`.

## Output format

Three numbered lines, plain text. No markdown headings, no code fences —
this output is meant to read fluidly inside a Claude Code session:

```
1. [SAFE] audit-page — Audit a frontend page across 16 UX/technical dimensions.
2. [NEEDS-CONFIRM] incremental-refactoring — Safely evolving existing prod codebases through incremental refactoring.
3. [SAFE] code-review-checklist — Cardinal rule code review using objective evidence.
```

If zero candidates score >0, emit exactly one fallback line:

```
1. [SAFE] codebase-onboarding — Orient to an unfamiliar codebase (entry points, dependency graph, layer map). Run /onboard <path>.
```

## Edge cases

- **NLP query produces 0 matches** -> recommend `codebase-onboarding`
  (`/onboard`) as the universal "I don't know where to start" answer.
- **>3 candidates score equally** -> strict cap at 3 via the sort key
  above; never break the cap with a "see also" appendix.
- **Smart-loading resolver returns an empty active set** (degenerate
  repo with no skills bound to its profile) -> same fallback as the
  0-match case: `/onboard`.
- **Profile is `trading-readonly` and the query implies a write action**
  (heuristic: redacted query contains substrings `deploy`, `place order`,
  `submit`, `mutate`) -> downgrade all SAFE markers to NEEDS-CONFIRM for
  this invocation. The trading kill-switch (sub-agent 2.7) still enforces
  the actual hard block; this is UX-layer hinting only.

## Audit emit — Sec MF-3 whitelist

After each invocation (success OR fallback), emit a single audit event:

```
action = "help_me_invoked"
fields = {
  "recommendation_count": int (0..3),
  "profile": str (one of frontend|engine|fintech|trading-readonly|generic),
  "top_skill_name": str (frontmatter `name` field of the #1 result, or empty)
}
```

**Whitelist invariant (Sec MF-3):** the audit emit MUST contain ONLY the
3 fields above. The user query text (raw OR redacted) MUST NEVER appear
in the audit log. This is a stricter rule than `_lib/redact.py` provides;
redaction protects content, the whitelist protects the field-name surface.

Volume budget: **<=30/hr** per the frontmatter `audit_volume_budget_per_hour`.
Beyond that, the emit becomes a no-op breadcrumb (fail-open per ADR-049a).

Registration: `help_me_invoked` lives in `_lib/audit_emit.py` `_KNOWN_ACTIONS`
+ a SPEC row + a `test_emit_help_me_invoked_basic` test. Wave 1 ceremony
folds all 4 sources atomically per the S100 lesson L6.

## When NOT to invoke

- The Owner is debugging a hook itself (the recommendation surface is part
  of the framework; recursive recommendations would loop).
- The Owner is inside the `cross-llm-pair-review` flow (Codex MCP gate)
  where suggestions would interleave with adversarial review output.
- The CEO is mid-ceremony (sentinel signing, GPG flow). Defer.

## Reference

- PLAN-083 §5.3 Wave 1 row 1.11 (this skill's authorship lineage)
- PLAN-083 §6 row Sec P1 (redaction mandate)
- Wave 0a sub-agent 0.6 `detect-repo-profile.py` (profile source)
- Wave 0b sub-agent 0.7d `smart-loading-resolver.py` (active skill set)
- Wave 1 sub-agent 1.10 `_lib/confidence_labels.py` (marker emitter)
- Wave 2 sub-agent 2.2 3-actions recommender (consumes this skill's
  recommendation library — see `integration-with-wave-2.md`)
