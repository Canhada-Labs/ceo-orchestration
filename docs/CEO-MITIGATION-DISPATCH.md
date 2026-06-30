# CEO Mitigation Dispatch (PLAN-060 Layer 7c)

> **Status:** Phase 1 wrapper landed. ADR-082 PLAN-061 default-on
> shipped 2026-04-27 (re-ratified Wave A 2026-04-27).
>
> **⚠ Cost expectation (audit-v2 C3-P0-03 disclosure, Wave B):**
> mitigated dispatch routes 4 of 5 canonical archetypes
> (`qa-architect`, `performance-engineer`, `security-engineer`,
> `devops`) through `general-purpose`, which **inherits the CEO
> model (Opus 4.8 by default at $5/$25 per Mtok)**. NOT the
> Sonnet/Haiku rates ADR-052 §Role-to-model would suggest. Only
> `code-reviewer` runs at Opus by *policy* (ADR-052 VETO floor);
> the other 4 inherit Opus by *default-CEO*. See
> `docs/cost-of-operation.md` §Mitigated dispatch for cost impact
> and `CEO_MITIGATION_DISABLE=1` override.
>
> **Reference:**
> - ADR-080 §Layer 7c
> - ADR-082 (PLAN-061 default-on routing decision)
> - PLAN-044 audit-v2 C3-P0-03 (cost disclosure remediation)
> - `.claude/plans/PLAN-060/audit/round-2/h4-layer7c-mitigation-via-general-purpose.md`
> - `.claude/plans/PLAN-060/audit/round-2/h4-layer7-tools-list-discrepancy.md`

## What this is

A workaround for the **H4 rail anomaly** observed empirically across
PLAN-059 + PLAN-060: when the CEO dispatches a sub-agent via a
custom `subagent_type` defined in `.claude/agents/*.md` (e.g.
`qa-architect`, `performance-engineer`, `security-engineer`,
`devops`), the Claude Code runtime grants a tools list of
**only `Grep, Glob`** — even when the agent's frontmatter declares
`tools: [Read, Grep, Glob, Bash]`.

`code-reviewer` is the only custom subagent_type that correctly
receives all 4 declared tools.

The resulting failure mode: the sub-agent persona is told it has
Bash; user asks it to invoke Bash; runtime hasn't actually granted
Bash → some sub-agents fabricate fake tool-call syntax in text;
others (with framing applied) honestly refuse with "I do not have
a Bash tool". Either way, the dispatch produces no fixture on disk.

## The mitigation

Built-in subagent types (`Explore`, `general-purpose`) receive a
much larger tool universe. Specifically `general-purpose` reports:

```
Bash, Edit, Glob, Grep, Read, ScheduleWakeup, Skill, ToolSearch, Write
```

By dispatching via `subagent_type=general-purpose` and injecting
the role-specific persona (PERSONA + SKILL) into the prompt body
via `## SKILL CONTENT` section, the sub-agent inherits the full
tool surface AND adheres to the role-specific framing.

Empirically validated: **13/13 dispatches succeeded** across qa /
cr / pe / se / devops persona variations, including a realistic
full-body qa simulation.

## How to use

### Generating a mitigated prompt

Pass `--dispatch=mitigated` to `inject-agent-context.sh`:

```bash
bash .claude/scripts/inject-agent-context.sh \
  --dispatch=mitigated \
  "Principal QA Architect" \
  "Run the test suite and report any flaky tests"
```

The script emits a header at the top of the prompt:

```
## DISPATCH MITIGATION — PLAN-060 Layer 7c (ADR-080)

This prompt is constructed for dispatch via the BUILT-IN subagent_type
"general-purpose" to bypass the H4 rail anomaly...

CALLER MUST DISPATCH AS:
  Task(subagent_type="general-purpose", prompt=<this entire block>)

NOT AS:
  Task(subagent_type="<original-archetype>", prompt=<this entire block>)
```

followed by the standard `## AGENT PROFILE` + `## SKILL CONTENT`
+ `## RELEVANT PITFALLS` + `## TASK` sections.

### Caller-side dispatch (CEO)

When the CEO invokes the Task tool with a mitigation-prepared prompt:

```python
# WRONG — would route via custom subagent_type and hit the rail anomaly
Task(subagent_type="qa-architect", prompt=prompt)

# RIGHT — routes via built-in general-purpose with persona injected
Task(subagent_type="general-purpose", prompt=prompt)
```

The mitigation header in the prompt body itself reminds the CEO of
the correct dispatch.

### Activation modes

Three ways to enable mitigation:

1. **Per-call flag (preferred for explicit selection):**
   ```bash
   bash .claude/scripts/inject-agent-context.sh \
     --dispatch=mitigated "..." "..."
   ```

2. **Session-level env var (for slash commands or batch operations):**
   ```bash
   export CEO_DISPATCHER_MODE=mitigated
   # Subsequent inject-agent-context.sh invocations emit mitigation header
   ```

3. **Default (native):** No flag, no env var → header is NOT emitted;
   prompts are constructed for native dispatch (which fails for
   qa/pe/se/devops but works for cr).

### Kill-switch

Force native dispatch regardless of flag or env var:

```bash
export CEO_MITIGATION_DISABLE=1
```

This overrides both `--dispatch=mitigated` flag and
`CEO_DISPATCHER_MODE=mitigated` env var. Useful when:

- You want to verify the rail anomaly is still present in your env.
- You're troubleshooting whether mitigation is masking a different bug.
- Anthropic ships an upstream fix and you want native back.

## Risks

### 1. Persona drift

`general-purpose` has its own training disposition. Even with explicit
persona injection, it may add unexpected creativity (one validation
dispatch added a haiku to the response). Tasks completed correctly,
but tone/style varied.

**Mitigation:** include explicit "Do not summarize, do not analyze,
do not output the [output template]. Just execute the task."
constraints in the TASK section.

### 2. Tool over-grant

`general-purpose` has Edit + Write + Skill + ToolSearch — tools that
most archetype roles don't need. A poorly-crafted persona injection
could allow unwanted writes.

**Mitigation:** Constrain via TASK + RESTRICTIONS section. Audit
output via `git diff` after dispatch (existing CEO discipline).

### 3. Anthropic could ship a role-mismatch heuristic

If Anthropic adds a check "subagent_type matches injected persona"
to detect role impersonation, the mitigation could be denied.
Currently NOT observed.

**Mitigation:** Monitor Claude Code release notes; have native
fallback ready (kill-switch above).

### 4. ADR-052 VETO floor erosion

`code-reviewer` and `security-engineer` require Opus 4.8 per ADR-052.
`general-purpose` inherits the CEO's model unless explicitly overridden
in the persona. May weaken the VETO floor if mitigation default model
is sonnet-4-6.

**Mitigation:** ADR-052 enforcement at sentinel layer
(`check_tier_policy.py` blocks model changes to `code-reviewer.md` /
`security-engineer.md` frontmatter). When mitigation is used, CEO must
explicitly verify the dispatch carries Opus 4.8 instructions in the
persona body.

## Testing

14 unit tests in `.claude/scripts/tests/test_inject_agent_context_mitigated_dispatch.py`
cover:

- Default native (no header)
- Mitigated flag emits header
- Header position (before AGENT PROFILE)
- Explicit native flag
- Env var activation
- Kill-switch overrides flag + env var
- Combination with `--mode=inline|reference`
- Flag order independence
- Header references PLAN-060 + ADR-080
- Header documents kill-switch
- Header appears only once
- Unrecognized `--dispatch=` value handling

Run:

```bash
python3 -m pytest \
  .claude/scripts/tests/test_inject_agent_context_mitigated_dispatch.py -v
```

Empirical validation reference:
`.claude/plans/PLAN-060/audit/round-2/h4-layer7c-mitigation-via-general-purpose.md`

## Production wiring TODO

The following CEO-side artifacts should be updated to make mitigation
the default for affected archetypes:

- [ ] **Update `.claude/team.md` ROUTING TABLE** — add note that all
  spawn instructions for `qa-architect`, `performance-engineer`,
  `security-engineer`, `devops` should pass `--dispatch=mitigated`
  to `inject-agent-context.sh`.
- [ ] **Update `PROTOCOL.md` Spawn Protocol §Step 3** — document the
  `general-purpose` dispatch fallback for non-cr archetypes.
- [ ] **Update `.claude/commands/spawn.md` slash command** — emit
  `--dispatch=mitigated` by default; instruct user to set
  `CEO_MITIGATION_DISABLE=1` to disable.
- [ ] **Update `docs/MECHANISM-SELECTION.md`** — note that the
  Anthropic-side `code-reviewer` recognition is a known constraint
  when picking subagent_types.

These updates touch canonical-guarded files and require **Owner
ceremony** (sentinel `approved.md` + GPG signature). They are
deferred until:

1. Cross-session Cell A + B test confirms substring-vs-exact
   discrimination (lower priority — mitigation works regardless).
2. Validation breadth N=10+ each archetype confirms no edge cases.
3. Owner schedules a single ceremony covering all 4 canonical paths.

## Cross-session falsification (optional)

Cell A (`.claude/agents/code-reviewer-qa.md`, qa-body + name=
`code-reviewer-qa` + opus-4-7) and Cell B (`.claude/agents/senior-engineer.md`,
cr-body + name=`senior-engineer` + opus-4-7) are **staged on disk**
from PLAN-060 Layer 7b. Run them in a fresh session to discriminate:

- Cell A 5/5 → name substring `code-reviewer-` is the discriminator
- Cell B 5/5 → cr-body content is the discriminator
- Both 0/5 → exact match `code-reviewer` is privileged (Anthropic-
  side hardcode)

See `.claude/plans/PLAN-060/audit/round-2/NEXT-FRESH-SESSION-PROMPT.md`
for the 6-step protocol.

The mitigation works regardless of which outcome we get; the
falsification refines our understanding of the root cause but does
not change the production wiring decision.

## Empirical record

| Wave | Dispatches | Persona | Success | Mode |
|---|---|---|---|---|
| Layer 7c initial | 6 | qa×5 + cr×1 | 6/6 | persona-via-skill-content |
| Layer 7c breadth | 7 | qa+pe×2+se×2+devops+qa-fullbody | 7/7 | persona-via-skill-content |
| **Total** | **13** | 5 distinct archetypes | **13/13 = 100%** | — |

Median wall time: ~7-8s/dispatch (similar to native code-reviewer).

All fixtures verified on disk at `/tmp/h4-layer7-fixtures/exp8_*.txt`.
