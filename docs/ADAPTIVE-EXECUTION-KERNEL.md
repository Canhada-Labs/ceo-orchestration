# Adaptive Execution Kernel (AEK)

> **See also:** [`docs/REALITY-LEDGER.md`](REALITY-LEDGER.md) — companion drift-detection tool.

`task-route.py` is a **pre-task classifier** that reads a task description and
optional file hints, then emits a **Task Execution Contract** (S/M/L/XL) covering
ceremony mode, recommended agents, context strategy, and review gates. It is
advisory-only: the CEO (Claude orchestrator) always retains override authority.
The script composes existing framework primitives — `team.md` routing table,
`tier_policy/_constants.py::VETO_HARDCODE`, `agent_frontmatter.py::VETO_FLOOR_ROLES` —
without reimplementing them.

---

## When the CEO uses it

Invoke `task-route.py` **once per Owner-task**, not once per spawn. A single
contract covers all agents for one task; the CEO dispatches all `/spawn` calls
from that contract without re-running the classifier.

```
Owner gives task to CEO
        |
CEO runs (one invocation per task):
   python3 .claude/scripts/task-route.py --task "..." --format markdown
        |
CEO reads contract digest (≤30 lines)
        |
CEO accepts, edits, or overrides
        |
   S → CEO operates directly (no /spawn)
   M → CEO runs /spawn for each agent listed in contract
   L → CEO runs /spawn for multi-agent parallel dispatch
  XL → CEO runs /debate start PLAN-NNN, then spawns after consensus
        |
Post-execution: audit-log captures reality
        |
Weekly (optional): python3 .claude/scripts/reality-ledger.py
```

---

## Tiers at a glance

| Tier | Ceremony mode | Agents | Debate | Typical signal |
|------|---------------|--------|--------|----------------|
| **S** | `direct` | None — CEO operates directly | No | Single file, no VETO domain, no canonical path |
| **M** | `1-agent-with-veto` | Specialist + VETO holders (Opus always) | No | VETO-keyword in task OR ≤4 files with no escalating signal |
| **L** | `multi-agent` | Parallel squad | No | ≥3 distinct module roots OR test-infra workflow signal |
| **XL** | `debate` | Full squad | Yes | Canonical-guarded path, schema/migration, release/CI/RAG workflow |

---

## Decision tree (explicit predicates)

The classifier applies predicates in this priority order. First match wins; if
no predicate fires, the safe default is **M**.

```
1. canonical_path_match?         → XL  (edit touches a _CANONICAL_GUARDS path)
2. veto_domain == auth/financial/PHI?  → XL  (+ schema or workflow)
   veto_domain == auth/financial/PHI?  → M   (without schema/workflow)
3. schema_signal?                → XL  (\bschema\b, \bmigrat\b, \bSPEC/v1\b)
4. workflow_signal == release/ci?→ XL  (.github/workflows/)
5. workflow_signal == rag?       → XL  (.claude/rag/)
6. multi_module + (test_infra OR tier_policy)?  → XL
7. multi_module?                 → L   (≥3 distinct directory roots)
8. workflow_signal == test-infra?→ L   (tests/, pytest.ini, Makefile)
9. veto_domain OR ≤4 files?      → M
10. ≤2 files AND no veto AND no canonical?  → S
(default)                        → M
```

NFKC normalization is applied to both `task_description` and `file_hints`
before any predicate runs, defeating ZWJ, RTL override, and fullwidth
homoglyph attacks.

---

## Worked example — T03: fix timing oracle

**Input:**

```bash
python3 .claude/scripts/task-route.py \
  --task "fix timing oracle in authentication module src/auth/login.ts:94" \
  --files "src/auth/login.ts" \
  --format json
```

**Classification walkthrough:**

| Step | Check | Result |
|------|-------|--------|
| 1 | `src/auth/login.ts` in `_CANONICAL_GUARDS`? | No (not a hook/plan/ADR path) |
| 2 | Veto domain? `timing.oracle` + `auth` → YES | — |
| 3 | Schema signal? No | — |
| 4-6 | Release/CI/RAG/tier_policy? No | — |
| 9 | veto_domain → M | **MATCH** |

**Expected JSON contract (abbreviated):**

```json
{
  "schema_version": "task-execution-contract.v1",
  "contract_id": "<uuid4>",
  "issued_at": "2026-05-05T...",
  "task_description_hmac": "<hex>",
  "classification": "M",
  "classification_rationale": [
    "Single file (src/auth/login.ts) — tier S signal",
    "VETO-protected domain (auth/timing-oracle) → upgrade S → M",
    "No schema/workflow/canonical signal"
  ],
  "ceremony": {
    "mode": "1-agent-with-veto",
    "debate": false,
    "brainstorm": false,
    "veto_holders": ["security-engineer", "code-reviewer"]
  },
  "agents": [
    {
      "archetype": "Staff Backend Engineer",
      "skill": "security-and-auth",
      "model": "opus-4-7",
      "veto_floor": true,
      "consumption_class": "advisory-actionable"
    },
    {
      "archetype": "Staff Code Reviewer",
      "skill": "code-review-checklist",
      "model": "opus-4-7",
      "veto_floor": true,
      "consumption_class": "advisory-actionable"
    }
  ],
  "context_strategy": {
    "primary": "grep+read",
    "rerank": false,
    "rag_sidecar": false,
    "consumption_class": "advisory-readonly"
  },
  "file_assignment": {
    "may_edit": ["src/auth/login.ts"],
    "parallelism": "single-agent-sequential",
    "consumption_class": "advisory-actionable"
  },
  "review_gates": ["security-engineer VETO", "code-reviewer VETO"],
  "residual_risks": [
    "Same-LLM bias on security review (mitigated by Opus floor + grep verify)"
  ]
}
```

**CEO action from this contract:**

```
/spawn "Staff Backend Engineer" fix timing oracle in src/auth/login.ts:94 using constant-time compare
→ wait for output
/spawn "Staff Code Reviewer" review the constant-time fix — VETO authority active
→ merge if both approve
```

---

## CLI reference

```bash
# Human-readable markdown digest (default for CEO review)
python3 .claude/scripts/task-route.py \
  --task "TASK DESCRIPTION HERE"

# With file hints (improves classification accuracy)
python3 .claude/scripts/task-route.py \
  --task "TASK DESCRIPTION HERE" \
  --files "path/to/file1.ts" "path/to/file2.ts"

# Machine-readable JSON contract
python3 .claude/scripts/task-route.py \
  --task "..." \
  --files "..." \
  --format json

# Verbose explanation of each predicate decision
python3 .claude/scripts/task-route.py \
  --task "..." \
  --explain
```

**Exit codes:** `0` = success (contract emitted); `2` = internal error (import
failure or unrecoverable classification error).

**Input limits:** task description capped at 8 KiB; `--files` accepts up to 50
paths. Each path is validated through an 8-step checker (no NUL, no backslash,
no absolute paths, no traversal outside repo root, no symlink escape).

---

## VETO floor invariant

`task-route.py` **never** recommends a non-Opus model for any of the 6 VETO
floor roles. The floor is computed as the union of two sources at script
startup:

- `tier_policy/_constants.py::VETO_HARDCODE` — 2-role compile-time floor
- `_lib/agent_frontmatter.py::VETO_FLOOR_ROLES` — runtime 6-role canonical

A structural assertion fires at init: `task_route_floor >= VETO_HARDCODE.keys() | VETO_FLOOR_ROLES`.
If the assertion fails the script exits with code 2 and does not emit a
contract.

The 6 protected roles are: `code-reviewer`, `security-engineer`,
`threat-detection-engineer`, `identity-trust-architect`,
`incident-commander`, `llm-finops-architect`.

---

## Override mechanism

The CEO can always override the advisory contract:

1. **Accept as-is:** use the emitted ceremony mode and agent list verbatim.
2. **Edit the tier:** if context makes a tier obviously wrong, promote or
   demote before dispatching (document the override reason in the session).
3. **Ignore entirely:** for trivial S tasks where running the script costs more
   than the classification saves, skip it. The script is advisory, not a gate.
4. **Kill-switch:** set `CEO_TASK_ROUTE_DISABLE=1` in the environment to
   suppress the script framework-wide without modifying any file.

---

## Future integration

`v1.14.0` ships `task-route.py` as a standalone advisory CLI.

`/ceo-boot` integration (wiring `--task-route="..."` as a session-start hint)
is **conditional** on the adoption metric: if `task_route_advised` audit events
appear in ≥3 of the first 5 consecutive sessions post-v1.14.0 GA, the
`/ceo-boot` integration will be proposed in a follow-up plan. If ≤2 of 5
sessions emit the event, the `CEO_TASK_ROUTE_DISABLE=1` kill-switch path
remains the documented outcome.

Hook integration (PreToolUse enforcement) is explicitly **not planned for
v1.14.0** and requires a separate ADR + empirical evidence from Phases 1-4.

---

## Known limitations (v1.14.0 skeleton scope)

- **No audit emit yet.** The `task_route_advised` audit action is declared in
  `audit_emit._KNOWN_ACTIONS` only after the Phase 5 KERNEL ceremony ships.
  Until then, audit emission is best-effort/no-op. CLI output still works.
- **Mutation fixtures pending.** The ≥30 mutation fixtures (6 VETO roles × 5
  bypass classes) are acceptance criteria for Phase 1; the S87 skeleton
  delivered the core decision tree but the full mutation suite ships in the
  next session.
- **No ReDoS benchmark.** The 200ms ITIMER budget is implemented via
  `_lib.secret_patterns._install_itimer_guard()`. The p95 < 200ms cold-start
  benchmark (Phase 0.5) is pending.
- **`--serve` REPL mode deferred to v1.15.0+.** One invocation per task is the
  current model; subprocess startup is amortized across all spawns for that
  task.
- **Audit-log emission gated on Phase 5 KERNEL.** `task_route_key_dropped`
  breadcrumbs require the KERNEL ceremony to register the action in
  `_KNOWN_ACTIONS` + `SPEC/v1/audit-log.schema.md` v2.18.
