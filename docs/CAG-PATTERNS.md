# CAG Patterns — Cache-Augmented Generation in ceo-orchestration

> **Audience:** adopters operating ceo-orchestration in production
> repos who want to understand what the framework caches, what it
> doesn't, and how to keep cache hit rates high.
> **Companion docs:**
> - [`opus-4-7-operations.md`](./opus-4-7-operations.md) §2 — operational cache discipline
> - [`CAG-VS-RAG.md`](./CAG-VS-RAG.md) — when retrieval beats inline
> - [`INSTALL-RAG.md`](./INSTALL-RAG.md) — opt-in LightRAG sidecar (ADR-062)
> - [`TOKEN-ECONOMY-ADOPTER-GUIDE.md`](./TOKEN-ECONOMY-ADOPTER-GUIDE.md) — broader token cost surface
> **PLAN:** PLAN-062 Phase 1.

## TL;DR

The framework is **already SOTA in CAG for Claude-only adopters.**
You don't need to learn a new technique. You need to understand
what's already cached so you don't accidentally invalidate it.

Three rules:

1. **Maximize cold prefix.** Skills + governance files + persona
   blocks live at the front of every spawn prompt. The framework
   sizes this at ~27.300 tokens. That's pure cache-hit territory
   after the first turn of a session.
2. **Minimize hot tail churn.** Memory autoload, tool results, and
   user messages re-tokenize every turn. Keep them lean.
3. **Don't edit Gate-1 files mid-session.** A single edit to
   `CLAUDE.md` / `PROTOCOL.md` / `team.md` / `frontend-team.md` /
   `ceo-orchestration` SKILL.md invalidates the cold prefix and
   re-pays gate-boot the next turn. Owner ceremonies and explicit
   closeouts are the only legitimate windows.

That's the operational core. The rest of this document explains why.

---

## 1. The cold/hot partition (the only mental model you need)

Anthropic's prompt cache treats your prompt as two regions:

```
┌─────────────────────────────────────────────────────────┐
│  COLD prefix — cached server-side, ~10% cost on hit     │
│  - Gate-1 files (~27.300 tokens)                        │
│  - Format B SKILL REFERENCE blocks (sha256-pinned)      │
│  - System prompt + persona injection                    │
│  - TTL 5 min default (1 hour on paid extended cache)    │
├─────────────────────────────────────────────────────────┤
│  HOT tail — re-tokenized every turn, full cost          │
│  - Memory auto-loaded from ~/.claude/projects/...       │
│  - Tool call results (Read, Grep, Bash output)          │
│  - User message                                         │
│  - Sub-agent return values                              │
└─────────────────────────────────────────────────────────┘
```

Cost asymmetry on Anthropic's API:

| Region | Per-token cost relative to baseline |
|---|---|
| Cold prefix, **cache hit** | ~0.1× (10% of normal input) |
| Cold prefix, **cache miss** (first turn / TTL expired / mid-session edit) | ~1.25× (25% premium for cache write) |
| Hot tail | 1.0× (normal input rate) |
| Output | normal output rate |

If your cold prefix is 27.000 tokens and you have a 60-turn session
with cache hits, you pay ~1.25× × 27.000 once + ~0.1× × 27.000 × 59
turns ≈ 193.500 token-cost-equivalents. Without caching you'd pay
27.000 × 60 = 1.620.000. **~88% reduction on the cold portion.**

That's where the framework's cache discipline pays for itself.

---

## 2. What this framework already caches for you

You don't have to configure prompt caching manually. The framework
ships it as governance:

### 2.1 Gate-1 files as the cold prefix

`CLAUDE.md` §0 mandates reading 5 files at session start (Gate 1
+ Gate 2):

| File | Purpose | Approximate tokens |
|---|---|---|
| `CLAUDE.md` | Master context, current work, changelog | ~9.000 |
| `PROTOCOL.md` | Governance rules, vetoes, spawn protocol | ~6.500 |
| `.claude/team.md` | Backend roster + SKILL MAP + ROUTING TABLE | ~4.500 |
| `.claude/frontend-team.md` | Frontend roster (if installed) | ~3.000 |
| `.claude/skills/core/ceo-orchestration/SKILL.md` | CEO operating system | ~4.300 |

Total: **~27.300 tokens**. Anthropic's prompt cache pins this at
the front of every spawn prompt the CEO emits. After the first
turn of a session, all subsequent turns hit the cache for these
tokens.

This is what `opus-4-7-operations.md` §2 calls "gate-boot cost" —
~27.300 tokens you pay once per session. Not per turn. Per session.

### 2.2 Format B SKILL REFERENCE (ADR-051)

When the CEO spawns a sub-agent (e.g., `code-reviewer`,
`security-engineer`), the spawn prompt has two formats for skill
content:

**Format A — inline (legacy):**

```
## SKILL CONTENT
SKILL LOADED: code-review-checklist
{full SKILL.md content embedded — ~5.000-15.000 tokens}
```

**Format B — by-reference (cache-friendly, ADR-051):**

```
## SKILL REFERENCE
@.claude/skills/core/code-review-checklist/SKILL.md sha256={64-hex}
{optional 256-byte summary}
```

Format B is **~95% smaller** in the spawn prompt. The sub-agent
reads the SKILL.md file directly via `Read` tool post-spawn and
re-hashes for forensic verification (handled by
`check_skill_reference_read.py` PostToolUse hook).

**Why Format B helps caching:**

The inline `## SKILL CONTENT` of Format A is *part of the spawn
prompt* — it's a hot tail unique to each spawn. Format B keeps the
spawn prompt small (~256-512 bytes), so the cold prefix dominates.
Result: spawn prompts under 2 KB, cold prefix dominates totally,
cache hits maximize.

### 2.3 Persona injection from team.md

The CEO doesn't re-read `team.md` for every spawn — it reads once
at Gate 2 and reuses the in-context roster. Each spawn just
references the persona name (e.g., "Staff Code Reviewer") and the
sub-agent prompt is built from the cached roster.

This is invisible to you. The framework just does it.

---

## 3. The 5-minute TTL trap

### 3.1 What expires

Anthropic's default prompt cache has a **5-minute TTL** measured
from last cache hit. If 5 minutes pass between turns, the next
turn hits a cache miss and re-pays the gate-boot cost (~25%
premium).

### 3.2 When this matters

- **Long deliberation between turns.** If you read a doc, think
  for 6 minutes, then ask a follow-up — cache miss.
- **Slow sub-agent dispatch.** If a sub-agent takes 7 minutes to
  return — cache miss when you process its result.
- **Owner-physical ceremony interrupts.** A `OWNER-*.sh` script
  that takes 6 minutes to authorize — cache miss when CEO resumes.

### 3.3 What does NOT expire it

- Tool calls within the same turn (Read, Bash, Grep, etc.)
- Sub-agent dispatches that complete in < 5 minutes
- Multi-step `/spawn` cadences within 5-minute windows

### 3.4 Mitigations

- **Batch your /spawn cadences.** If you need to spawn 3 sub-agents
  in sequence, do it within 5 minutes total wall-clock.
- **Use the 1-hour cache tier** if you're billed for it (`cache_control:
  ephemeral` with `ttl: "1h"`). 6× the TTL window for ~2× the
  cache-write premium. Math: worth it if your session has ≥10 cache
  hits per cold-prefix-write.
- **Don't mix CEO sessions with long manual work.** If you're going
  to spend 30 minutes outside the terminal, end the session and
  re-boot.

---

## 4. Format A vs Format B decision tree

The framework supports both. When to use which:

```
                        ┌─────────────────────────┐
                        │  Spawning a sub-agent?  │
                        └────────────┬────────────┘
                                     │
                  ┌──────────────────┴──────────────────┐
                  │                                     │
                  ▼                                     ▼
     ┌────────────────────────┐          ┌────────────────────────┐
     │  Canonical-5 archetype? │          │  Custom / ad-hoc?      │
     │  (code-reviewer,        │          │  (one-off task,        │
     │   security-engineer,    │          │   diagnostic spawn,    │
     │   qa-architect,         │          │   experiment)          │
     │   performance-engineer, │          └──────────┬─────────────┘
     │   devops)              │                     │
     └────────────┬────────────┘                     │
                  │                                  │
                  ▼                                  ▼
        ┌────────────────────┐              ┌────────────────────┐
        │  Format B          │              │  Format A inline   │
        │  (SKILL REFERENCE) │              │  (SKILL CONTENT)   │
        │                    │              │                    │
        │  cache-friendly +  │              │  cache-neutral but │
        │  sha256 forensic   │              │  faster to author  │
        │  verification      │              │  one-shot prompts  │
        └────────────────────┘              └────────────────────┘
```

Default for canonical-5: **Format B**. The dispatcher
`inject-agent-context.sh` emits Format B by default for these
archetypes (it's been the default since PLAN-020 Phase 2).

Default for non-canonical: **Format A inline**. Faster to write a
one-off prompt; cache penalty is negligible if you only spawn
once.

Operator override:

```bash
# Force Format A inline even on canonical-5:
.claude/scripts/inject-agent-context.sh --mode=inline <Agent> "<task>"

# Force Format B even on non-canonical:
.claude/scripts/inject-agent-context.sh --mode=reference <Agent> "<task>"
```

See `PROTOCOL.md` §Spawn Protocol for the full Format A/B specs.

---

## 5. Cache invalidation playbook

### 5.1 What invalidates the cold prefix

Any byte-change to a Gate-1 file invalidates the cache prefix
*from that byte onward*. Practical impact:

| Edit | Cache invalidation scope |
|---|---|
| Add line to `CLAUDE.md` §6 (Current Work) | full prefix re-paid |
| Bump ADR count in `CLAUDE.md` §1 list | full prefix re-paid |
| Edit `PROTOCOL.md` §Spawn Protocol | full prefix re-paid (PROTOCOL.md is in cold) |
| Edit `team.md` ROUTING TABLE | full prefix re-paid |
| Edit a SKILL.md file | only that skill's Format B SHA changes; spawn prompts referencing it cache-miss the next time |
| Edit a doc in `docs/` | NO impact (docs are not in cold prefix) |
| Edit `examples/` script | NO impact |

### 5.2 When invalidation is acceptable

- **End-of-session closeout.** `CLAUDE.md` §6 + CHANGELOG entry
  edited at session end. Next session pays gate-boot once. Normal.
- **Ratifying an ADR.** ADR file is in `.claude/adr/` not in cold
  prefix; only `CLAUDE.md` §1 ADR list changes. Pay-once normal.
- **Skill update.** Edit SKILL.md, bump frontmatter version, regen
  Format B SHA. Sub-agents using that skill pay re-cache cost on
  their first invocation post-update. Normal.

### 5.3 When invalidation is a bug

- **Mid-session edit to fix a typo.** You re-pay gate-boot on every
  subsequent turn for the rest of the session. Save the fix for
  closeout.
- **Editing CLAUDE.md every turn to track progress.** Use memory
  files instead — they're hot tail, expected to churn.
- **Reverting `team.md` after an experiment.** You pay for the
  first edit AND the revert.

### 5.4 The hard rule

**`CLAUDE.md` §0 makes this a governance rule, not a recommendation:**

> Cache discipline (PLAN-020 Phase 4): Gate-1 files are
> cache-stable across sessions. Do NOT edit `CLAUDE.md`,
> `PROTOCOL.md`, `.claude/team.md`, `.claude/frontend-team.md`, or
> `.claude/skills/core/ceo-orchestration/SKILL.md` during a working
> session — only at the explicit closeout ceremony at session end.

If a sub-agent or experiment requires a Gate-1 edit mid-session,
that's a signal to:

1. Pause the session
2. Run the closeout ceremony
3. Start a fresh session with the new cold prefix

The penalty for ignoring this is real, measurable, and pays out
every turn after the violation.

---

## 6. Cache hit rate measurement (advanced)

If you're using the Anthropic SDK directly (not just Claude Code),
you can measure cache hit rate from the API response.

### 6.1 What the API returns

Every `messages.create()` call returns `response.usage`:

```python
response.usage.input_tokens             # uncached input
response.usage.cache_read_input_tokens  # cache hit (cheap)
response.usage.cache_creation_input_tokens  # cache write (premium)
response.usage.output_tokens
```

### 6.2 Computing hit rate

```python
total_input = (
    response.usage.input_tokens
    + response.usage.cache_read_input_tokens
    + response.usage.cache_creation_input_tokens
)
hit_rate = response.usage.cache_read_input_tokens / total_input
```

Per-call hit rate of **0.85+** indicates healthy cache discipline.
Per-call hit rate of **0.30 or lower** in the middle of a session
indicates a Gate-1 invalidation event — investigate.

### 6.3 Rolling-window measurement

Track hit rate over the last N calls (recommend N=10). Trends:

- **Steady ≥0.85:** healthy. Cold prefix is doing its job.
- **Sudden drop (0.85 → 0.20):** cold prefix invalidated. Bug or
  ceremony.
- **Slow drift (0.85 → 0.65 over 30 calls):** TTL expirations.
  Sessions are too slow between turns; consider 1-hour cache tier.
- **Stuck at <0.30:** something is wrong with `cache_control`
  config. Review your Anthropic SDK call.

### 6.4 Reference pattern (no script shipped)

A measurement script is not part of the framework's adopter recipes
(PLAN-062 repurposed Phase 4 to HyDE — see [`HYDE-RECIPE.md`](./HYDE-RECIPE.md)).
Adopters writing their own SDK integration should adapt the pattern
shown in §6.2 + §6.3 directly:

```python
# Per-call hit rate
hit_rate = response.usage.cache_read_input_tokens / total_input

# Rolling N=10 window
from collections import deque
window = deque(maxlen=10)
window.append(hit_rate)
rolling = sum(window) / len(window)
```

That is the entire useful content of a measurement script. ~10 LoC
in your adopter codebase — the framework's stdlib-only invariant
(ADR-002) + ADR-096 vibecoder-only-by-design make it inappropriate
to ship as a recipe.

---

## 7. What this framework deliberately does NOT do

For honesty:

| Technique | Why we don't ship it |
|---|---|
| Auto-flush cache on skill update | adds API surface, adopter can do manually |
| Multi-tier cache (cold + warm + hot) | Anthropic only exposes single-TTL ephemeral |
| Per-request `cache_control` placement | Claude Code handles this; explicit knob unnecessary |
| Cache hit metrics in `audit-log.jsonl` | privacy concern (could reveal session timing); optional via SDK direct |
| Auto-detect mid-session Gate-1 edits | the canonical-edit hook approximates this (`check_canonical_edit.py`); explicit cache discipline is governance |

These are conscious omissions, not gaps.

---

## 8. Summary checklist

Before opening a CEO session:

- [ ] Gate-1 files (`CLAUDE.md`, `PROTOCOL.md`, etc.) are in
      stable state. No half-finished edits.
- [ ] Memory files in `~/.claude/projects/<slug>/memory/` are
      reasonably small (under ~50 KB total, under 200 LoC for
      `MEMORY.md` index).
- [ ] You're not planning a /spawn cadence longer than 5 minutes
      total wall-clock (or you have 1-hour cache tier billed).
- [ ] You know what closeout means: it's the *only* legitimate
      window to edit Gate-1 files this session.

During the session:

- [ ] All edits go to docs/, examples/, plans/, .claude/scripts/,
      .claude/hooks/ (NEW files OK, edits to canonical hooks
      go through ceremony).
- [ ] No edits to CLAUDE.md / PROTOCOL.md / team.md /
      frontend-team.md / ceo-orchestration SKILL.md.
- [ ] Memory writes are fine (cache-neutral region).

At session end:

- [ ] Closeout ceremony writes Gate-1 changes (`CLAUDE.md` §6
      + CHANGELOG, possibly team.md if roster changed).
- [ ] Memory `project_*.md` files updated.
- [ ] MEMORY.md index entry added (one line, ≤150 chars).

This is the operational discipline. The framework enforces parts
of it via hooks (cache discipline is observed, not blocked); the
rest is your discipline.

---

## 9. Further reading

- **Cache discipline operational details:** `opus-4-7-operations.md`
  §2 — TTL math, gate-boot cost derivation, cache pricing reference.
- **When to add retrieval:** `CAG-VS-RAG.md` §1 — decision tree for
  inline vs sidecar retrieval.
- **Adopter scale tiers:** `ADOPTER-SCALE-TIERS.md` — when CAG alone
  is enough, when sidecar starts paying off.
- **Token cost surface:** `TOKEN-ECONOMY-ADOPTER-GUIDE.md` — broader
  cost analysis including non-cache concerns (model tier routing,
  retry churn, etc.).
- **Anthropic prompt caching reference:** see Anthropic's API
  documentation for cache_control, TTL options, and pricing.
- **ADR-051:** rationale for Format B SKILL REFERENCE (cache-friendly
  spawn prompts).
- **PLAN-020 Phase 4:** the ratification of cache discipline as
  governance.
