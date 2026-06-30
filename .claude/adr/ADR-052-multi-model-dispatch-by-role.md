# ADR-052: Multi-model dispatch by role

**Status:** ACCEPTED (flipped PLAN-025 Batch C — live per PLAN-021 commits 97b4c37+9340dc7 (model: field + audit v2.8 + validate lint) + PLAN-024 ADR-052 multi-model velocity validation (3.53x speedup measured))
**Date:** 2026-04-17 (Session 32; PLAN-021)
**Deciders:** CEO, VP Engineering, Principal Performance, Principal Security, VP Operations
**Blast radius:** L2 (per-agent metadata field + audit-log additive schema)
**Supersedes:** none
**Superseded by:** none
**Depends on:** ADR-050 (native subagents), ADR-051 (skill-by-reference)

## Context

PLAN-020 shipped 5 canonical-5 native subagents (code-reviewer,
security-engineer, qa-architect, performance-engineer, devops) as
`.claude/agents/<slug>.md` files. All 5 currently inherit the CEO's
model (Opus 4.7) when spawned via Claude Code native subagent path —
no per-agent model distinction.

Opus 4.7 is correct for orchestration (stateful, long context, L3+
decisions, debate synthesis), but it's over-provisioned for many
sub-agent workloads. Specifically:

- DevOps config edits + boilerplate scaffolding → Haiku handles in
  less time + lower cost + same quality
- Performance metric extraction + bounded analysis → Sonnet matches
  Opus quality at ~1/5 the cost
- Security auditing + code review → Opus remains correct (VETO
  authority demands strongest reasoning)
- QA edge-case enumeration → Sonnet handles well except for novel
  cross-cutting test design (Opus escalation via `/effort high`
  orchestrator turn still available)

**Industry SOTA (2025-2026):** model-per-role dispatch is the
dominant pattern in production multi-agent frameworks (CrewAI,
LangGraph, DSPy, Cursor, Aider, Cline, Anthropic's own Claude Agent
SDK examples). Pattern: **strongest model for orchestration + weakest
model for fan-out**, calibrated per role's accuracy requirement.

**Cost magnitude (Anthropic public pricing, tokens/M):**

| Model | Input | Output | vs Opus |
|-------|-------|--------|---------|
| Opus 4.7 | $15 | $75 | 1.0× |
| Sonnet 4.6 | $3 | $15 | 0.2× |
| Haiku 4.5 | $0.25 | $1.25 | 0.017× |

Typical ceo-orchestration session today (~500k total tokens, all Opus):
- Cost ≈ $7.50
- Distribution: ~200k Opus (CEO turns) + ~200k Opus × 2 (critical VETOs)
  + ~200k Opus × 3 (other workers)

Post-dispatch (proposed):
- ~200k Opus (CEO + critical) × $15/M = $3.00
- ~200k Sonnet (mid-complexity workers) × $3/M = $0.60
- ~100k Haiku (high-freq fan-out) × $0.25/M = $0.025
- **≈ $3.63 → 52% cost reduction** with zero regression on security
  + code review quality gates.

## Decision

Adopt **per-role model dispatch** for the 5 canonical-5 native
subagents via `model:` field in YAML frontmatter.

### Role-to-model distribution

| Agent | Model | Rationale |
|-------|-------|-----------|
| `code-reviewer` | `claude-opus-4-8` | Merge VETO — false negative here ships a bug. Strongest reasoning justified. |
| `security-engineer` | `claude-opus-4-8` | Auth/crypto VETO — attack surface missed here = incident. Strongest reasoning mandatory. |
| `qa-architect` | `claude-sonnet-4-6` | Edge-case enumeration + test design. Sonnet matches Opus on bounded work. Cost 0.2× |
| `performance-engineer` | `claude-sonnet-4-6` | Metric analysis + bottleneck identification. Deterministic; Sonnet excellent. Cost 0.2× |
| `devops` | `claude-haiku-4-5-20251001` | Config edits + boilerplate + lint fixes. High-frequency, low-novelty. Haiku 10× faster + 60× cheaper. |

### Kill switches (orthogonal to PLAN-020 existing toggles)

- **`CEO_MULTIMODEL_ENABLE`** (RESERVED — not wired in v1.6.0-rc.1;
  PLAN-024 F-chaos-001). The intent was default `=1`; `=0` would force
  all canonical-5 spawns into Opus (PLAN-020 baseline). **Current
  reality:** setting the env var has NO runtime effect because the
  model-per-role binding lives in the `.claude/agents/*.md` `model:`
  frontmatter field, which Claude Code's native subagent dispatcher
  reads directly — there is no user-land interception point.
  **Workaround:** to force all-Opus today, override each
  `.claude/agents/*.md model:` field to `claude-opus-4-8` (preserved
  across `./scripts/upgrade.sh` runs per PLAN-021 adopter-override
  contract). Wiring this as a real kill switch requires either a
  Claude Code Task-tool PreToolUse hook that rewrites `model:` at
  dispatch, or a manifest-rewrite step in `install.sh` — both deferred
  to a future sprint.
- **`CEO_SOTA_DISABLE=1`** (existing master) — overrides every other
  PLAN-020 + PLAN-021 toggle. Custom rail + inline + all-Opus.
  (Does NOT force all-Opus via the same mechanism as
  `CEO_MULTIMODEL_ENABLE`; it disables the native rail entirely, so
  spawns fall back to the inline Format A path where CEO-authored
  prompt specifies the model.)

### Frontmatter format (additive to ADR-050)

```yaml
---
name: <slug>
description: <description>
version: anthropic-subagent-v1
tools: [Read, Grep, Glob, Bash]
model: claude-opus-4-8     # NEW — one of: claude-opus-4-8 |
                           # claude-sonnet-4-6 |
                           # claude-haiku-4-5-20251001
                           # OR omit/empty = inherit CEO model
---
```

### Validation

`validate-governance.sh` lints:
- Native agent frontmatter should have `model:` field (warning if
  missing — backward compat with pre-ADR-052 agents)
- If `model:` present, value must match one of 3 known Claude 4.x
  IDs OR be explicitly empty (`model:` with no value = inherit)

### Audit-log v2.8 additive schema bump

`audit_log.py::build_entry` captures `model` field per spawn (from
`tool_response` or frontmatter resolution). Enables forensic
correlation: if a Sonnet-routed review misses a bug, audit log
proves which model was used for the decision.

### Adopter override

Adopter edits `.claude/agents/<slug>.md` `model:` field. Framework
upgrade via `upgrade.sh` preserves adopter customizations (already
tested via `upgrade_agents_canonical_only` — diff-detect on each
canonical file, preserve if adopter modified).

### Model ID bump process (future Opus 5 / Sonnet 5)

When Anthropic releases next-gen models, frontmatter IDs are stale.
Recipe:

1. Benchmark new model on canonical-5 rubrics (`.claude/plans/PLAN-020/
   rubrics/<archetype>.yaml`) — pass rate must be ≥ current baseline.
2. Run `benchmarks/replay.py` on `plan-019-wave-2a.jsonl` fixture —
   spawn-prompt delta must not regress.
3. Author ADR-NNN referencing this ADR-052 + benchmark evidence.
4. Update frontmatter `model:` fields per agent.
5. Bump audit-log schema (v2.9) if new model has additional
   `usage_metadata` fields.

This process gates every future model-family bump — no silent
in-place upgrade.

### CEO orchestrator tier (PLAN-048 amendment, 2026-04-22)

Previously the CEO orchestrator was hardcoded Opus 4.7. Empirical
experiment (PLAN-048 Phase 2 simulated A/B) measured 25.3% session
cost reduction on N=8 baseline sessions (3 of 8 eligible for downshift,
49 of 145 turns). CTO Round-3 arithmetic aligned (24–32%).

**Adopted rule (CONDITIONAL):** CEO defaults to Sonnet 4.6; upgrades to
Opus 4.7 upfront on any of 5 conditions:

| # | Condition | Why |
|---|---|---|
| a | Plan frontmatter `level: L3` or higher | L3+ blast radius requires deep protocol compliance |
| b | Session tag ∈ `{L3+-plan-execution, debate-round, brainstorm, ceremony}` | Empirically spawn-heavy class |
| c | Canonical-edit path declared in session scope | Governance-critical paths need protocol rigor |
| d | VETO-protected domain touched | auth / financial-math / token handling |
| e | Expected `spawn_count` >= 3 by session-tag heuristic | Multi-phase plan-execution pattern |

**Kill-switch:** `CEO_MODEL_DOWNSHIFT=0` restores Opus-always.

**Invariants preserved:**
- VETO roles remain Opus 4.7 regardless of CEO tier. The dispatcher
  checks role first, then CEO context — VETO hardcode takes priority.
- `/effort` tokens remain CEO-only (PROTOCOL.md §Step 3).
- Sub-agent tier mapping (non-VETO roles) unchanged.

### VETO_FLOOR_ROLES expansion (PLAN-074 Wave 1c amendment, 2026-05-06)

`_lib/agent_frontmatter.VETO_FLOOR_ROLES` (current frozen baseline:
`{code-reviewer, security-engineer}`) is expanded to register three NEW
VETO-floor archetypes whose decisions are operationally equivalent in
blast radius to the original two:

| Archetype | Backing skill | Why VETO-floor |
|-----------|---------------|----------------|
| `identity-trust-architect` | `core/identity-and-trust-architecture` (PLAN-074 Wave 1b) | Identity is the perimeter — once trust is granted (token issued, role assigned, S2S call trusted) every downstream component inherits transitively. Bad identity decisions cannot be caught by general code review; the ramifications span auth flows, S2S trust, RLS, audit-log integrity, and incident-response revocation latency. Sub-domain depth justifies a dedicated VETO authority distinct from `security-engineer`. |
| `incident-commander` | `core/incident-management` | Severity assignment, declared-vs-actual scope drift, premature all-clear, and revocation-latency miscalls during active incidents have unbounded blast radius — the wrong call during a sev-1 multiplies by orders of magnitude. |
| `threat-detection-engineer` | (SIEM/ATT&CK doctrine; cross-references `core/security-and-auth` §Detection-as-Code) | Detection coverage gaps and false-positive-rate drift are both VETO-magnitude: a missed detection means breaches go undetected for the rule's full lifetime; a noisy rule trains the SOC to ignore the channel. |

`llm-finops-architect` is **explicitly excluded** from this expansion.
Cost governance is operational doctrine, not a VETO-floor authority
under ADR-052 — budget decisions can be reversed; identity, incident,
and detection decisions cannot.

#### Mechanical change (Wave 1c ceremony, atomic)

```python
# .claude/hooks/_lib/agent_frontmatter.py — current
VETO_FLOOR_ROLES: FrozenSet[str] = frozenset({
    "code-reviewer",
    "security-engineer",
})

# .claude/hooks/_lib/agent_frontmatter.py — Wave 1c (atomic)
VETO_FLOOR_ROLES: FrozenSet[str] = frozenset({
    "code-reviewer",
    "security-engineer",
    "incident-commander",          # PLAN-074 Wave 1c
    "identity-trust-architect",    # PLAN-074 Wave 1c
    "threat-detection-engineer",   # PLAN-074 Wave 1c
})
```

#### Atomic-add invariant (S90 P0-01 lesson)

The frozenset entry and the corresponding `.claude/agents/<slug>.md`
file MUST land in the same GPG sentinel commit. A frozenset entry
without its agent file causes `check_agent_spawn.py` to fail-CLOSE on
every dispatch mentioning that archetype, blocking legitimate work.
The Wave 1c sentinel scope is documented at
`.claude/plans/PLAN-074/staging/wave-1c-veto-floor-matrix.md`.

#### Test contract (Wave 1c-staged — NOT runnable in Wave 1b)

The bidirectional test below ships in the **Wave 1c ceremony**, not Wave 1b.
Wave 1b lands the **architectural contract** (this ADR amendment + the
Wave 1b SKILL doctrines + the matrix at
`.claude/plans/PLAN-074/staging/wave-1c-veto-floor-matrix.md`). Wave 1c
lands the **mechanical enforcement** atomically:

1. Add `veto_floor: true` frontmatter to `.claude/agents/code-reviewer.md`
   and `.claude/agents/security-engineer.md` (existing VETO archetypes)
2. Create the 4 new agent files (`incident-commander.md`,
   `identity-trust-architect.md`, `threat-detection-engineer.md`,
   `llm-finops-architect.md` — only the first three carry
   `veto_floor: true`; `llm-finops-architect` does NOT, per the matrix)
3. Update `_lib/agent_frontmatter.VETO_FLOOR_ROLES` frozenset (3 additions)
4. Land this test file at `.claude/hooks/tests/test_veto_floor_bijection.py`

All four artifacts MUST land in the **same GPG sentinel commit** (atomic-
add invariant per S90 P0-01 lesson). The test below will FAIL pre-Wave-1c
because deployed agents lack the `veto_floor: true` frontmatter — this
is intentional; the test's purpose is to enforce the post-Wave-1c
invariant and detect any silent drift afterward.

```python
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]  # adjust per test location
sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))

from _lib.agent_frontmatter import VETO_FLOOR_ROLES, parse_agent_file  # noqa: E402


def _is_truthy(value) -> bool:
    """Coerce frontmatter value to bool. parse_agent_file returns Dict[str, str],
    so YAML `veto_floor: true` arrives as the string "true" — direct
    `is True` comparison would always be False. Wave 1c may add a typed
    accessor to _lib/agent_frontmatter; until then, normalize here."""
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in ("true", "yes", "1")


def _agents_with_veto_frontmatter() -> set[str]:
    """Derive the deployed VETO-marked agent set from .claude/agents/*.md frontmatter.

    Collects every agent that declares `veto_floor: true` REGARDLESS of model.
    Caller separately asserts these agents use the expected Opus model — that
    way a non-Opus agent incorrectly declaring veto_floor:true is detected as
    BOTH an orphan-from-frozenset (if absent from VETO_FLOOR_ROLES) AND a
    model-floor violation, instead of being silently ignored.
    """
    agents_dir = REPO_ROOT / ".claude" / "agents"
    deployed = set()
    for agent_file in sorted(agents_dir.glob("*.md")):
        try:
            fm = parse_agent_file(agent_file)
        except Exception:
            continue
        if fm.get("__symlink_rejected__"):
            continue
        if _is_truthy(fm.get("veto_floor")):     # NOTE: model check removed
            deployed.add(agent_file.stem)
    return deployed


def _veto_agents_with_wrong_model() -> set[str]:
    """Find agents that declare veto_floor:true but do NOT use the canonical Opus model."""
    agents_dir = REPO_ROOT / ".claude" / "agents"
    wrong = set()
    for agent_file in sorted(agents_dir.glob("*.md")):
        try:
            fm = parse_agent_file(agent_file)
        except Exception:
            continue
        if fm.get("__symlink_rejected__"):
            continue
        if _is_truthy(fm.get("veto_floor")) and fm.get("model") != "claude-opus-4-8":
            wrong.add(agent_file.stem)
    return wrong


def test_veto_floor_roles_bijection_with_deployed_agents():
    """Bidirectional invariant: VETO_FLOOR_ROLES == deployed-VETO-frontmatter agents.

    Closes both half-states:
    (a) frozenset role without agent file → fail-CLOSE on dispatch (S90 P0-01),
    (b) deployed VETO-marked agent file NOT in frozenset → silent under-enforcement.
    """
    agents_dir = REPO_ROOT / ".claude" / "agents"

    # Forward: every frozenset role has its agent file
    missing_files = {
        role for role in VETO_FLOOR_ROLES
        if not (agents_dir / f"{role}.md").exists()
    }
    assert not missing_files, f"VETO-floor roles missing agent files: {missing_files}"

    # Reverse: every VETO-marked deployed agent is in the frozenset
    deployed = _agents_with_veto_frontmatter()
    orphans = deployed - VETO_FLOOR_ROLES
    assert not orphans, (
        f"Agents declare veto_floor:true but absent from VETO_FLOOR_ROLES: {orphans} "
        "— atomic-add invariant violated; rerun the Wave 1c-style sentinel "
        "ceremony to land both halves."
    )

    # Equality (the strong invariant the matrix demands)
    assert VETO_FLOOR_ROLES == deployed, (
        f"Set-equality invariant broken: frozenset={set(VETO_FLOOR_ROLES)} "
        f"deployed={deployed}"
    )

    # Model floor: every veto_floor:true agent uses the canonical Opus model.
    # An agent declaring veto_floor:true with model=claude-sonnet-4-6 (etc.)
    # would silently downgrade VETO authority — must fail loudly.
    wrong_model = _veto_agents_with_wrong_model()
    assert not wrong_model, (
        f"Agents declare veto_floor:true but use non-Opus model: {wrong_model} "
        f"— VETO_FLOOR_MODEL is `claude-opus-4-8` per ADR-052."
    )
```

Note 1: `.claude` is not a Python package — it has no `__init__.py` and the
leading dot would be parsed as a relative import. Tests must extend
`sys.path` to include `.claude/hooks/` and import `_lib.agent_frontmatter`
without the `.claude.hooks.` prefix.

Note 2: The bidirectional check is mandatory. A unidirectional check (forward
only) would let an Owner-merged agent file slip past the frozenset and silently
under-enforce VETO authority — exactly the half-state the S90 P0-01 atomic-add
lesson was designed to prevent.

#### Doctrinal backing

Each new VETO-floor archetype is backed by a canonical SKILL.md that
codifies the doctrine the archetype enforces. The archetype's VETO
authority is mechanical (it can block merge); the SKILL.md is
substantive (it tells reviewers and authors what "right" looks like).
VETO without SKILL.md = unjustifiable authority; SKILL.md without VETO
= unenforceable doctrine. Both halves required.

**Status:** ACCEPTED-WITH-LIVE-TRAFFIC-FOLLOWUP (ADR-067). Promote to
unconditional once adopter-1 completes >=10 Sonnet-default +
>=5 Opus observe-only control sessions and verdict re-renders with
quality regression observed = 0.

## Consequences

**Positive:**

- ~52% cost reduction per typical session on canonical-5 spawns
  (measured against 500k-token Opus-only baseline).
- 2-3× speed improvement on devops + performance spawns (Haiku +
  Sonnet latency < Opus).
- VETO quality gates PRESERVED (code-reviewer + security-engineer
  stay Opus).
- Audit-log provides forensic trail of model choice per decision —
  superior to black-box routing frameworks.
- Kill switch `CEO_MULTIMODEL_ENABLE=0` (RESERVED — see above; not wired in v1.6.0-rc.1) would give adopters single-line
  rollback to all-Opus for high-assurance contexts.
- Adopter override is trivial: edit 1 line of frontmatter.

**Negative:**

- 5 frontmatter fields to maintain as Claude model family evolves.
  Mitigated by model-bump process (ADR-052 §Model ID bump recipe).
- Slight observability complexity: audit log now has 3 possible
  model values per spawn. Mitigated by v2.8 schema documentation
  + `audit-query.py` model filter (future enhancement).
- Anthropic API rate limits are per-key across all models; heavy
  Haiku fan-out doesn't save rate-limit headroom even if cost drops.
  Out of scope for this ADR.

**Trade-offs explicitly accepted:**

- We do NOT implement model-cascading (try Haiku → retry in Sonnet
  on low confidence → retry in Opus on still-low). Added complexity
  not justified until cost/benefit data from production.
- We do NOT support non-Anthropic models here. HAL adapter path
  exists (`_lib/adapters/`) for future Sprint 22+.
- We do NOT migrate non-canonical archetypes (frontend leads, domain
  specialists). Scope-bounded to 5 canonical-5.

## Acceptance for ADR-052 closure

(Tracked in PLAN-021 §10 Success criteria.)

- [ ] 5 canonical-5 native agent files have explicit `model:` frontmatter
- [x] `CEO_MULTIMODEL_ENABLE` env var documented (PLAN-024 F-chaos-001: clarified RESERVED status, not wired in v1.6.0-rc.1)
- [ ] audit_log v2.8 captures model field
- [ ] validate-governance.sh lints model field
- [ ] upgrade.sh preserves adopter model overrides
- [ ] docs/opus-4-7-operations.md §Model distribution published
- [ ] Kill-switch matrix updated
- [ ] ≥5 new tests (model field + dispatch + audit + toggle)
- [ ] Replay benchmark still shows A4 acceptance (97.14% spawn-prompt
      savings — orthogonal to model dispatch; model choice affects
      per-token cost but not prompt-size delta)
- [ ] (Wave 1c amendment) `VETO_FLOOR_ROLES` expanded atomically with
      agent files for `incident-commander`, `identity-trust-architect`,
      `threat-detection-engineer`
- [ ] (Wave 1c amendment) `test_veto_floor_roles_match_deployed_agents`
      shipped + green
- [ ] (Wave 1c amendment) Each new VETO-floor archetype has its backing
      SKILL.md staged-to-canonical

## References

- PLAN-021 §Multi-model dispatch by role
- ADR-050 (native subagents; this ADR extends with model field)
- ADR-051 (skill-by-reference; model-orthogonal)
- PLAN-020 Phase 6 §replay benchmark (spawn-prompt cost baseline)
- Anthropic Claude Agent SDK docs — "Model selection for subagents"
- Owner directive Session 32 (verbatim in PLAN-021 §Context)
- PLAN-074 Wave 1b — `core/identity-and-trust-architecture` SKILL.md
- PLAN-074 Wave 1c VETO-floor matrix (Owner-ratified atomic-add)
- S90 P0-01 lesson — frozenset/agent-file atomic-add invariant

## Enforcement commit

`97b4c37afe1f` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
