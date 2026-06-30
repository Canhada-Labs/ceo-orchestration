# Mechanism Selection Guide

> **Purpose:** answer the adopter question *"do I use a skill, agent, hook,
> slash command, task-chain, MCP server, or ADR for X?"* with a single
> decision matrix + concrete worked examples.
> **Audience:** anyone extending `ceo-orchestration` — CEO (Claude), the
> Owner, and external adopters.
> **Status:** normative. Closes ultimate-guide audit BORROW-2 (PLAN-036).
>
> **See also:** [`docs/ADAPTIVE-EXECUTION-KERNEL.md`](ADAPTIVE-EXECUTION-KERNEL.md) — pre-task classifier that decides *which ceremony* (S/M/L/XL) to apply for a given task, complementing this guide's *which mechanism* question.

---

## 1. The seven mechanisms in 30 seconds

| Mechanism | Home directory | Runtime | Invocation | Primary role |
|-----------|----------------|---------|------------|--------------|
| **Skill** | `.claude/skills/<tier>/<slug>/SKILL.md` | Prompt context | Loaded into an agent's prompt at spawn time (Format A inline or Format B by-reference, ADR-051) | Reusable checklist, rules, patterns, vocabulary |
| **Agent / Archetype** | `.claude/team.md` (archetypes) + `.claude/agents/*.md` (canonical-5 native) | Sub-process via the `Task` tool | CEO calls `Agent(subagent_type=...)` or `/spawn <Name>` | Named persona with loaded skill(s) that executes a scoped job |
| **Hook** | `.claude/hooks/*.py` (Python, stdlib only) | OS sub-process on each tool call (`PreToolUse` / `PostToolUse` / `UserPromptSubmit` / etc.) | Automatic — fires on matching tool event | Mechanical enforcement, not a convention |
| **Slash command** | `.claude/commands/<name>.md` | Prompt injected into the conversation | User types `/<name>` in chat | User-invocable governance workflow (debate, spawn, audit-page, etc.) |
| **Task-chain** | `.claude/task-chains.yaml` (+ domain chains under `domains/<d>/task-chains.yaml`) | Declarative pipeline definition | CEO follows the chain as a script during multi-step work | Composed multi-step workflow with pipeline invariants |
| **MCP server** | External (sidecar binary) + `.mcp.json` registration | IPC to external process | Anthropic client auto-connects when registered | Integration with external services (RAG, tools, APIs) |
| **ADR** | `.claude/adr/ADR-<NNN>-<slug>.md` | Document | Read by reviewers + CEO during debate / audit | Architectural record for L3+ cross-cutting decisions |

None of these can substitute for another. Choosing the wrong mechanism
is the single most common cause of governance drift in adopter projects.

---

## 2. Decision matrix

> **Rule:** find your work type in the leftmost column. ✅ = correct
> mechanism; ❌ = wrong mechanism (even if technically possible); ⚠️ =
> conditional (read the note). *possibly* = often a secondary artifact.

| Work type / need | Skill | Agent | Hook | Slash cmd | Task-chain | MCP | ADR |
|---|---|---|---|---|---|---|---|
| Enforce a **mechanical rule** that must NEVER be bypassed (e.g. no floats in financial math, canonical-edit sentinel, spawn must carry skill content) | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | *possibly* |
| **Reusable checklist or mental model** an agent consults each time it does a task | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Named persona** that gets spawned for a specific role (code-reviewer, security-engineer, data-engineer, etc.) | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **User-invocable workflow** triggered by typing `/foo` in chat (debate, spawn-persona, audit-page, pitfall catalog) | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ |
| **Composed multi-step pipeline** with phase boundaries that must not shuffle (add-exchange, implement-feature, financial-code review) | ❌ | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| **External service integration** (LightRAG, external tools, API adapters with resource/latency concerns) | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | *possibly* |
| **Cross-cutting architectural decision** that touches 3+ modules OR that a future maintainer would re-debate (directory layout, runtime floor, replacement of one mechanism with another) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **New enforceable plan-lifecycle state** (e.g. `reviewed` → `done` must require `completed_at`) | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | *possibly* |
| **Domain-specific knowledge** (fintech, edtech, lgpd, trading-hft) not applicable to every adopter | ✅ | *possibly* | ❌ | ❌ | ✅ | ❌ | *possibly* |
| **Skill with L3+ lifecycle significance** (canonical SKILL.md amendment, new core skill) | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Threat model / residual risk disclosure** to external reviewers (CTO/VPEng) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **VETO-holder declaration** (who blocks merges on which domain) | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | *possibly* |
| **Adversarial code-review framing** that the reviewer agent must adopt | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **Debate orchestration** (Round 1 / Round 2 / convergence + Red Team) | ❌ | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ |
| **Memory / observability instrumentation** adopters can opt into | ❌ | ❌ | ⚠️ | ❌ | ❌ | ⚠️ | *possibly* |
| **Cross-model dispatch policy** (when Opus vs Sonnet vs Haiku) | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ |
| **Per-adopter runtime profile** (max-quality / balanced / max-speed) | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | *possibly* |
| **New canonical-path file type** that must not be edited without a signed proposal (e.g. new hook under `.claude/hooks/`) | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ✅ |
| **Cross-cutting auditable action type** (new entry in `_KNOWN_ACTIONS` for `audit_log.py`) | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | *possibly* |
| **Adopter-facing onboarding docs** (CHEAT-SHEET, QUICKSTART, GUIA-COMPLETO) | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ |
| **SLO / SLA / availability commitment** to adopters | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **CI/CD gate** (release gate, branch protection, governance validator) | ❌ | ❌ | ⚠️ | ❌ | ❌ | ❌ | ✅ |
| **Skill-patch proposal lifecycle** (SP-NNN chain, Owner signing) | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ | ✅ |
| **Inter-agent handoff shared memory** | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | *possibly* |
| **Recurring scheduled work** (cron, autonomous loops — surface selection in §6) | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ | *possibly* |

Legend recap: ✅ canonical choice · ❌ wrong mechanism · ⚠️ conditional (see
note in §4 Worked Examples) · *possibly* secondary artifact often paired
with the ✅ mechanism.

**Key observation:** many work types require **two** artifacts (e.g.
a hook that enforces AND an ADR that documents the decision). The ✅
column is the primary delivery mechanism; *possibly* columns name the
secondary artifacts that travel with it.

---

## 3. Quick flowchart

```
┌────────────────────────────────────────────────────────────────┐
│ Does the work NEED to be mechanically un-bypassable?           │
│   YES → HOOK (+ optional ADR documenting the rule)             │
│   NO  → continue                                               │
└────────────────────────────────────────────────────────────────┘
                                │
┌────────────────────────────────────────────────────────────────┐
│ Is it a cross-cutting architectural decision (L3+, 3+ modules, │
│ would future maintainer re-debate)?                            │
│   YES → ADR (+ plan + skill amendments as side effects)        │
│   NO  → continue                                               │
└────────────────────────────────────────────────────────────────┘
                                │
┌────────────────────────────────────────────────────────────────┐
│ Is it a user-invocable workflow (someone types /foo)?          │
│   YES → SLASH COMMAND                                          │
│   NO  → continue                                               │
└────────────────────────────────────────────────────────────────┘
                                │
┌────────────────────────────────────────────────────────────────┐
│ Is it a multi-step pipeline whose phases must not shuffle?     │
│   YES → TASK-CHAIN (+ optional skills for each phase)          │
│   NO  → continue                                               │
└────────────────────────────────────────────────────────────────┘
                                │
┌────────────────────────────────────────────────────────────────┐
│ Does it wrap an external service / process?                    │
│   YES → MCP SERVER (+ ADR on opt-in + install doc)             │
│   NO  → continue                                               │
└────────────────────────────────────────────────────────────────┘
                                │
┌────────────────────────────────────────────────────────────────┐
│ Is it a named persona who gets spawned?                        │
│   YES → AGENT / ARCHETYPE (team.md entry + optional native     │
│         file under .claude/agents/)                            │
│   NO  → continue                                               │
└────────────────────────────────────────────────────────────────┘
                                │
┌────────────────────────────────────────────────────────────────┐
│ Is it a checklist / rules / patterns / vocabulary an agent     │
│ consults each time it performs a task?                         │
│   YES → SKILL (under .claude/skills/<tier>/)                   │
│   NO  → you're probably writing docs; put it under docs/       │
└────────────────────────────────────────────────────────────────┘
```

---

## 4. Worked examples from ceo-orchestration history

Each example traces a real decision and the mechanism chosen, so adopters
can calibrate their own judgment against framework precedent.

### Example 1 — "No floats in financial math"

**Wrong answer (naive):** write an ADR saying "use Decimal". That's
advisory — it'll drift.

**Right answer (framework):**

- **HOOK** — `check_canonical_edit.py` + dedicated `financial-*` skill
  rules flag `float` usage in `domains/fintech/` paths. Mechanically
  un-bypassable; `check_bash_safety.py` + finance-specific patterns in
  `code-review-checklist` reinforce at the reviewer level.
- **SKILL** — `domains/fintech/skills/financial-correctness-and-math/`
  loads the full rule set + reasoning into any agent that touches
  financial code.
- **ADR** — documented rationale in `ADR-013` (squad trading-hft) +
  fintech-domain pitfalls.

**Why not just a skill?** An agent can forget or rationalize around a
skill entry. The hook + canonical sentinel is the un-bypassable floor.

### Example 2 — "Integrate LightRAG for 500k-LoC codebases"

**Wrong answer:** write a hook that imports LightRAG and scans everything.

**Right answer:**

- **MCP SERVER** — `rag_bridge.py` sidecar registered via `.mcp.json`.
  Opt-in, resource-isolated, crash-isolated.
- **ADR-062** — documents the opt-in stance, threat model (the
  call-site-not-hook invariant), install procedure, dead-cache semantics.
- **Skill** — none dedicated. The CEO protocol consults the MCP via
  deferred tools when relevant.

**Why not a hook?** Hooks run synchronously on every tool call and
block until they return. A 500k-LoC index touch would tank interactive
latency and expand the hook blast radius beyond its defensible scope.

### Example 3 — "Brainstorm phase before drafting L3+ plans"

**Wrong answer:** make it a hook that blocks plan creation without a
spec.md.

**Right answer:**

- **SKILL** — `core/pre-plan-brainstorm/SKILL.md` describes the 9-step
  spec procedure + when to skip (L1-L2 or precedented L3+).
- **PROTOCOL.md amendment** — Gate 3 step 8 references the skill.
- **Plan frontmatter field** — optional `spec_ref:` pointer declares
  the output location (ADR-058).
- **ADR-058** — captures the decision.
- Kill-switch `CEO_BRAINSTORM_GATE=0` for adopter escape hatch.

**Why not a hook?** Brainstorming is a cognitive phase, not a mechanical
gate — forcing every plan through a hook would create false friction
on L1-L2 work where the phase adds no value.

### Example 4 — "Audit frontend pages across 16 UX dimensions"

**Wrong answer:** write a task-chain and hope adopters find it.

**Right answer:**

- **SLASH COMMAND** — `/audit-page` (`.claude/commands/audit-page.md`).
  User-invocable, discoverable, self-documenting.
- **SKILL(s)** — `frontend/accessibility-and-wcag`, `frontend/ux-and-user-journeys`,
  `frontend/code-quality-and-typescript` are loaded into the spawned
  agents.
- **TASK-CHAIN** — optional chain definition for the multi-phase review
  sequence.

**Why slash command + not just agent spawning?** Adopters need a single
invocation they can teach juniors + wire into PR automation. `/audit-page`
encapsulates the multi-agent fan-out. The underlying agents still come
from `team.md` / `frontend-team.md`.

### Example 5 — "Dynamic tier-policy selector (Opus / Sonnet / Haiku)"

**Wrong answer:** hardcode a table in a slash command.

**Right answer (PLAN-043 / ADR-064):**

- **ADR-064** — captures the decision, VETO-floor invariant, statistical
  gates (n ≥ 30 per cell + gap ≥ 25 pp), cost-envelope gate, cooldown
  semantics, threat model T9-T11.
- **HOOK** — `check_tier_policy.py` PreToolUse fires a third-layer VETO
  block (defense in depth beyond the hardcoded `VETO_HARDCODE` literals
  in `learn.py` and `apply.py`).
- **SKILL** — code-review-checklist + security-and-auth loaded during
  review of tier-policy changes.
- **CLI** — `.claude/scripts/tier_policy_cli/cli.py` (9 subcommands) for
  Owner operations.
- **SPEC** — `SPEC/v1/tier-policy.schema.md` for the on-disk policy
  format.
- **Slash command profile-picker** — `.claude/scripts/set-quality-profile.sh`
  for the three-profile adopter configurator (orthogonal to dynamic
  tier selection).

**Why so many mechanisms?** Because dispatch policy spans a rule
(hook + hardcoded literals), a data format (SPEC), an API (CLI), a
runtime behavior (profile picker), a threat model (ADR), and a skill
(review checklist). Trying to collapse it into one mechanism would
break the defense-in-depth posture — each mechanism compensates for
failure modes the others can't catch.

---

## 5. Anti-patterns (common mistakes)

### "I'll just write a skill for it"

**Symptom:** every new rule becomes a skill entry.
**Problem:** skills are consulted probabilistically (the agent reads
them, reasons about them, and may rationalize around them). A rule
that MUST hold needs a hook.
**Fix:** ask "what happens if the agent ignores this?" If the answer
is "the invariant breaks silently in production", it's a hook, not a
skill.

### "I'll just write an ADR"

**Symptom:** architectural decisions are recorded but not enforced.
**Problem:** ADRs document *why*, not *how it stays true*. Without a
hook or SKILL amendment, the decision decays within 2-3 sprints.
**Fix:** every ADR should spawn at least one enforcement artifact
(hook, skill update, task-chain change, SPEC entry).

### "Let's make it a slash command so adopters can run it"

**Symptom:** turning mechanical enforcement into user-invocable
commands.
**Problem:** slash commands are opt-in — they fire only when the user
remembers to type them. A canonical-edit sentinel hidden behind
`/check-canonical-edit` is a sentinel that fires 0% of the time.
**Fix:** enforcement belongs in hooks. Slash commands are for adopter
workflows (debate, spawn, audit), not for rules.

### "An MCP server will make us more powerful"

**Symptom:** reaching for MCP whenever external integration tempts.
**Problem:** MCP servers expand the trust surface and create dependency
churn. They're right for sidecars that handle resources hooks shouldn't
(large indices, external APIs, IPC to long-running processes). Using
MCP for a rule that could be a local hook inflates the attack surface.
**Fix:** prefer hooks unless the workload's resource / crash / latency
profile justifies out-of-process execution. ADR-062 §Threat Model has
the rubric.

### "Let's embed the persona directly in a slash command"

**Symptom:** `/review-pr` with hardcoded prompt.
**Problem:** loses the persona / skill-loading discipline. The agent
spawned this way has no loaded skill → generic agent → forbidden.
**Fix:** slash commands call out to agents (via `/spawn <Name>`),
which load their persona + skill. The slash command is the trigger,
the agent is the executor.

---

## 6. Scheduling surface selection — local vs cloud vs Desktop (PLAN-135 W4 D3)

Recurring and background autonomy now has three native execution
surfaces. Pick by **secret exposure first**, convenience second.

> **Hard rule: meta-repo secrets never go cloud.** Any job that needs
> the Owner's GPG key, `ANTHROPIC_API_KEY`, the audit-chain HMAC key,
> or push rights to this repo runs LOCALLY. Cloud scheduling is for
> read-only / reporting shapes only.

| Surface | Primitive | Secrets posture | Use for | Kill / stop |
|---|---|---|---|---|
| **Local — foreground recurrence** | `/loop <interval> /<command>` (e.g. `/loop 24h /nightly-hygiene`) | Full local env — OK for secret-touching jobs | Recurring hygiene sweeps + read-only routines against the live checkout | `CLAUDE_CODE_DISABLE_CRON` |
| **Local — background session** | `claude --bg --name PLAN-NNN-<unit>` in an isolated worktree | Full local env | Long plan units that shouldn't hold the foreground session. Naming convention is MANDATORY (`PLAN-NNN-<unit>`) for triage attribution; worktree isolation is MANDATORY | stop the named session |
| **Local — event vigil** | Monitor armed on `gh run watch` | n/a (read-only `gh`) | PRESCRIBED post-ceremony CI vigil — kills the red-discovered-next-session class (the S228 exec-bit red would have been auto-triaged) | stop the Monitor |
| **Cloud — scheduled agents (routines)** | cloud-side schedule | **NO meta-repo secrets — ever** | Read-only reporting shapes; jobs that must fire while the local machine is off | disable the routine |
| **Desktop / attended — Owner approval** | PushNotification on Owner-GPG-pending + Remote Control | Owner present; local env stays local | Ceremony gates awaiting Owner GPG — notify the Owner instead of idling; Remote Control lets the Owner approve from the phone | n/a (Owner-driven) |

**Bounded objectives are not scheduling.** "Make CI green on this PR"
is a `/goal` (independent verifier, zero config) — not a loop, not a
schedule, and not the ADR-133 autonomous loop. Full native-autonomy
decision rule: `docs/AUTONOMOUS-LOOP-GUIDE.md` §0.

---

## 7. Cross-references

This guide cross-links every major governance doc:

- `PROTOCOL.md` §Spawn Protocol — how an agent gets instantiated
  (Format A inline / Format B by-reference).
- `PROTOCOL.md` §Plan → Debate → Execute — the flow that decides
  whether you need ADR + debate at all.
- `.claude/team.md` — archetype roster + skill map + routing table
  (the "which archetype for which work" decision).
- `.claude/adr/ADR-051-*` — hook skill-reference mode (the Format B
  contract with `check_skill_reference_read.py`).
- `.claude/adr/ADR-031-*` — canonical-edit sentinel & SP-NNN chain
  (why editing SKILL.md directly is forbidden).
- `.claude/adr/ADR-052-*` + `ADR-064-*` — multi-model dispatch + dynamic
  tier selector.
- `docs/SKILL-AUTHORING-TUTORIAL.md` — how to write a new skill once
  you've decided skill is the right mechanism.
- `docs/HONEST-LIMITATIONS.md` — the structural limits that shape
  mechanism-selection trade-offs (bus factor, same-LLM, platform).
- `docs/AUTONOMOUS-LOOP-GUIDE.md` §0 — native-autonomy doctrine
  (`/goal` / `claude --bg` / `/loop` / Monitor before framework loop
  machinery), pairing with the §6 scheduling-surface table above.

---

## 8. FAQ

**Q: Can a single artifact be more than one mechanism?**
A: No. Each file lives in exactly one directory under `.claude/` and
plays exactly one role. You *compose* mechanisms (hook + ADR + skill),
you don't merge them.

**Q: What if my work type isn't in the matrix?**
A: Run the flowchart in §3. If still unclear, follow the debate
protocol (spawn the code-reviewer + security-engineer + relevant
archetype, ask "which mechanism should own this rule?"). If 2+ agents
converge on the same mechanism → that's your answer.

**Q: When do I need an ADR vs just a plan?**
A: If the decision is reversible (you can undo it within a sprint
without breaking contracts) + blast radius is 1-2 modules, a plan
suffices. If reversal would require coordinating adopters, touch 3+
modules, or involve a change to a SPEC, it's an ADR.

**Q: My adopter wants a custom rule in their fork. Hook or skill?**
A: Hooks under `.claude/hooks/` are canonical-edit-guarded — adopters
shouldn't edit them without SP-NNN. For adopter-specific rules, prefer
a **domain skill** under `domains/<adopter-domain>/skills/` (adopter-
editable). Reserve hooks for framework-level invariants.

**Q: Does adding a hook require an ADR?**
A: Yes, for any new hook file. The canonical-edit sentinel + branch
protection ensure this is hard to bypass. Document in `ADR-<NNN>`
with the threat model the hook defends against.

---

*Last updated: 2026-06-12 — §6 scheduling-surface table added; old
§6/§7 renumbered to §7/§8 (PLAN-135 W4 D3). Originally 2026-04-19,
closes PLAN-036 (ultimate-guide audit BORROW-2). Maintainer: CEO
(Claude). Amendments go through SP-NNN + Owner signature if this doc
itself ever becomes canonical; today it lives under `docs/` and is
adopter-editable.*
