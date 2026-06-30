# Framework readiness status

> **Live document.** Tracks the framework's terminal positioning.
>
> Last updated: 2026-06-05 (Session S211 — PLAN-129 docs-parity sweep;
> verdict MAINTENANCE-MODE-VIBECODER preserved). PLAN-122 (the Brutal
> Optimizer) closed in S197; the 2.5-3× speedup target was empirically
> KILLED in S201 (E2: no parity, 2.69× cost) — speed is dead across 7
> experiments. Current direction is PLAN-128 (zero-config solo-coding
> accelerators, wired LIVE; throughput multiplier still UNMEASURED).

## Current verdict

**MAINTENANCE-MODE-VIBECODER** as of Session 73 (2026-04-29).

Was `TRIAL-PENDING-SOAK` at v1.11.2 (post Wave C-bis). Owner
directive 2026-04-29 ("não vou esperar calendário, quero resolver
tudo agora") + ADR-096 (vibecoder-only by design) made TRIAL
graduation no longer a goal. ADR-095 retracted the time-based
calendar gates (14d CI green + 30d no-retag) that were the longest
remaining blockers.

The framework is **declared done for vibecoder-only positioning**.
Adopters who wander in are governed by README §Risks + HONEST-
LIMITATIONS.md. External adopter recruitment, series-B fintech
positioning, multi-adapter portability, and SLA are all OUT OF SCOPE.

## Verdict ladder (terminal at MAINTENANCE-MODE-VIBECODER)

```
NOT-READY-FOR-EXTERNAL-USE
        │
        │  (Wave A + B + C close 18/27 P0)
        ▼
TRIAL-PENDING-SOAK
        │
        │  (Session 73 closes audit-v2 P1 #11 + retracts calendar gates;
        │   Owner adopts vibecoder-only positioning ADR-096)
        ▼
MAINTENANCE-MODE-VIBECODER   ◄─── YOU ARE HERE (terminal)
        │
        │  (would require ADR superseding ADR-096 + co-maintainer recruit
        │   + outside reviewer; OUT OF SCOPE under current Owner directive)
        ▼
TRIAL → READY (defined but not scheduled)
```

## Calendar gates — RETRACTED 2026-04-29

| Gate | Status |
|---|---|
| **14-day CI green streak on main** | **RETRACTED via ADR-095 (2026-04-29).** Was Day 2/14 at retraction. CHANGELOG cadence is the authoritative observable signal. |
| **30-day no-retag streak** | **RETRACTED via ADR-095 (2026-04-29).** Was Day 1/30. Re-tag cadence is informal under vibecoder positioning. |
| **Outside reviewer 1-page second opinion** | **NOT RETRACTED.** Remains structural (same-LLM bias check). Codex (GPT/OpenAI) ran 3 ad-hoc audits to date (audit-v2 wave gate, Session 75 closure, Session 76 audit-v3 + repass) — operationally validated as ad-hoc review, NOT a recurring scheduled gate. Owner-physical recruit; no calendar binding. |
| **60-day refused-ADR moratorium (ADR-093)** | **NOT RETRACTED.** Day 2/60, clears 2026-06-26. Aligns with Owner directive (moratorium prevents NEW refusal ADRs, not new code). |

## TRIAL → READY (defined but not scheduled)

Path remains defined for any future ADR superseding ADR-096:

1. Co-maintainer recruited (bus-factor 1 → 1.1).
2. At least one **external adopter** runs the framework ≥1 working day
   and reports back via GitHub issue or `<owner-email>`.
3. Outside reviewer 1-page second opinion (gate #6 above).
4. **Zero new audit-v2-equivalent P0** found in audit-v3 narrow scope.
5. Vibecoder-only positioning (ADR-096) explicitly retracted via new ADR.

None of these are scheduled. The framework operates in MAINTENANCE-MODE
indefinitely under the current Owner directive.

## TRIAL → READY

Not gated by calendar. Requires:

1. At least one **external adopter** (not the framework owner) installs
   `ceo-orchestration` in their own project, runs the framework for at
   least 1 working day, and reports back via GitHub issue or
   `<owner-email>` direct.
2. **Zero new audit-v2-equivalent P0** found in a follow-up audit
   (audit-v3 narrow scope) commissioned at TRIAL.
3. Co-maintainer recruited (bus-factor 1 → 1.1) — see
   [`docs/HONEST-LIMITATIONS.md`](HONEST-LIMITATIONS.md) §Risks.

## What's actively true post-Session 74

| Claim | Verifiable command | Last verified |
|---|---|---|
| 19 of 27 audit-v2 P0 closed (8 remaining = 6 calendar/positioning + 2 Owner-physical, all OUT OF SCOPE under ADR-096) | `cat .claude/plans/PLAN-044/audit-v2/action-plan/triage.md` | 2026-04-29 |
| 12 of 12 P1-critical items closed (P1 #11 grandfathered via ADR-097 + 344-function YAML) | `cat memory/project_session_73_close_everything_done.md` | 2026-04-29 |
| MCP scanner detection 100%/0%/100% across 100 fixtures (FN gap closed Session 73) | `python3 .claude/scripts/swarm/test_mcp_injection_repro.py` | 2026-04-29 |
| MCP scanner STRICT mode shipped (`CEO_MCP_SCANNER_MODE=strict`); default ADVISORY | `grep CEO_MCP_SCANNER_MODE .claude/hooks/check_mcp_response.py` | 2026-04-29 |
| Function-length grandfather list (344 entries) frozen per ADR-097 | `wc -l .claude/governance/function-length-grandfather.yaml` | 2026-04-29 |
| Hook + script tests ≥4786 passed / ≥7 skipped / 0 failed | `python3 -m pytest .claude/hooks/tests/ .claude/scripts/tests/ -q` | 2026-04-29 |
| Governance 0 errors / 6 warnings (advisory) | `bash .claude/scripts/validate-governance.sh` | 2026-04-29 |
| audit-v2 P1 doc-drift batch closed (24 items, Session 74) | `grep -c "0 P1" .claude/plans/PLAN-044/audit-v2/SESSION-74-HANDOFF.md` | 2026-04-29 |
| audit-v2 P2 cosmetic batch closed (~45 items, Session 74) | `cat memory/project_session_74_close_cosmetic_done.md` | 2026-04-29 |
| audit-v2 100% truly closed (was 73% post-`894e876`; Session 74 residual closes 16 funcs across 8 canonical/kernel-guarded files via round-8 sentinel) | `python3 -c "import ast,pathlib; gaps=[(str(p),n.lineno,n.name) for p in pathlib.Path('.claude').rglob('*.py') if not any(x in str(p) for x in ['staged','/tests/','__pycache__','/adapters/live/']) for n in ast.walk(ast.parse(p.read_text())) if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)) and not n.returns and not n.name.startswith('_test') and n.name not in ('__init__','__enter__','__exit__','setUp','tearDown')]; print(f'Remaining: {len(gaps)}')"` (Remaining: 0) | 2026-04-29 |
| 6 hook test stubs added — closes audit-v2 C-18-04 | `ls .claude/hooks/tests/test_{SessionEnd,SessionStart,UserPromptSubmit,check_subagent_fabrication,check_tier_policy,check_webfetch_injection}.py` | 2026-04-29 |
| HONEST-LIMITATIONS §10 documents emit_<name> 41/92 — closes C-18-06 | `grep "emit_<name>" docs/HONEST-LIMITATIONS.md` | 2026-04-29 |
| `_lib/policy.py` line+branch coverage 93.94% (target 86%) | `pytest --cov=.claude/hooks/_lib/policy --cov-branch` | 2026-04-29 |
| `_lib/audit_hmac.py` line+branch coverage 87.50% (target 86%) | `pytest --cov=.claude/hooks/_lib/audit_hmac --cov-branch` | 2026-04-29 |
| `_lib/escalation_signals.py` coverage 92.38% (was 0%) | `pytest --cov=.claude/hooks/_lib/escalation_signals` | 2026-04-28 |
| `check-function-length.py` honors `--grandfather=PATH` | `python3 .claude/scripts/check-function-length.py` (0 violations) | 2026-04-29 |
| ADR-092 honest-deferral framework live | `grep "Status: ACCEPTED" .claude/adr/ADR-092-*.md` | 2026-04-27 |
| ADR-093 60-day moratorium live (NOT retracted Session 73) | `grep "Status: ACCEPTED" .claude/adr/ADR-093-*.md` | 2026-04-27 |
| ADR-095 calendar gate retraction (14d/30d) | `grep "Status: ACCEPTED" .claude/adr/ADR-095-*.md` | 2026-04-29 |
| ADR-096 vibecoder-only by design | `grep "Status: ACCEPTED" .claude/adr/ADR-096-*.md` | 2026-04-29 |
| ADR-097 function-length advisory-permanent | `grep "Status: ACCEPTED" .claude/adr/ADR-097-*.md` | 2026-04-29 |
| PLAN-015 abandoned (no external adopter recruit) | `grep "^status: abandoned" .claude/plans/PLAN-015-*.md` | 2026-04-29 |
| PLAN-052 done (Day-2 closure via ADR-095) | `grep "^status: done" .claude/plans/PLAN-052-*.md` | 2026-04-29 |
| PLAN-059 abandoned (no dogfood ≥5-session evidence) | `grep "^status: abandoned" .claude/plans/PLAN-059-*.md` | 2026-04-29 |
| Adapter stubs deleted (Claude-only) | `ls .claude/hooks/_lib/adapters/*.py` (only `__init__.py` + `claude.py`) | 2026-04-27 |

## What's NOT true post-Session 74 (honest disclosure)

- **Outside reviewer second opinion** — not yet recruited.
  Bus-factor remains 1. Per ADR-096 vibecoder-only positioning,
  recruitment is OUT OF SCOPE.
- **P1 #5 SP-NNN re-sign (6 sampled SPs)** — still pending Owner
  GPG ceremony (Owner-physical only; staged in
  `OWNER-SESSION-73-FINAL-CEREMONY.sh`).
- **Empirical calendar evidence retracted** — 14d/30d streaks no
  longer measured per ADR-095. CHANGELOG cadence is the authoritative
  observable signal.
- **External adopter recruitment** — declared OUT OF SCOPE per
  ADR-096. The framework's TRIAL → ADOPT path remains defined
  but is no longer scheduled.

## How to evaluate this framework

1. Read [`docs/HONEST-LIMITATIONS.md`](HONEST-LIMITATIONS.md) **first**
   (10 structural limitations).
2. Read [`README.md`](../README.md) §Risks & Not-For for the
   vibecoder-only positioning (ADR-096) + bus-factor 1 disclosure.
3. Read this file (you are here) to understand the terminal verdict.
4. If your context requires bus-factor ≥2, multi-adapter, SLA, or
   external evaluator sign-off → **this framework is NOT the right
   fit**. Consider AutoGen / MetaGPT / OpenAI Agents SDK / LangGraph.
5. If your context is single-developer / vibecoder / personal
   automation: run `bash scripts/install.sh /tmp/ceo-test --owner Foo
   --strict-placeholders` to test a clean install.

## Update cadence

This file is updated at every:
- Audit cycle (audit-v3+, if commissioned)
- ADR superseding ADR-096 (would re-open the verdict ladder)
- Material framework state change (governance, hooks, plans)

The CEO is responsible for updating it; Owner reviews on demand.
