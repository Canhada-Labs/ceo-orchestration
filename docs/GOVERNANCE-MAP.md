# Governance map

Two ledgers live in this doc:

1. **§1 — Anthropic safe-agent principles → framework controls**
   (PLAN-135 D9-lite): the citation table mapping Anthropic's
   published principles for safe agentic systems onto this
   framework's concrete, auditable controls. Audience: auditors,
   compliance reviewers, adopter CTOs who need to cite *which
   control implements which principle*.
2. **§2 — Grandfathered `validate-governance.sh` warnings**: the 2
   by-design warnings that look like issues but aren't.

---

## §1. Anthropic safe-agent principles → framework controls (PLAN-135 D9-lite)

Anthropic publishes a set of **five principles for safe and
trustworthy agents** (principle names below are paraphrased; cite the
current upstream text — Anthropic, "principles for safe agents",
2025 — alongside this table in any external audit response). The
table maps each principle to the framework controls that implement
it, with the citable artifact for each control.

| # | Anthropic principle (paraphrase) | Framework controls (citable artifacts) |
|---|----------------------------------|----------------------------------------|
| 1 | **Keep humans in control** — humans retain meaningful oversight and the ability to intervene | Owner approval gates in Plan→Debate→Execute (`PROTOCOL.md`); canonical files are Owner-GPG-ceremony-only — direct writes blocked by `check_canonical_edit.py` (staged-then-ceremony pattern, S223/S228); VETO floor on merge/security verdicts (ADR-052; `veto_floor: true` in `.claude/agents/*`); 3-strike agent policy (`team.md` §GOVERNANCE RULES); kill-switches for every autonomous surface (`CEO_MITIGATION_DISABLE`, `CEO_MODEL_DOWNSHIFT`, autonomous-loop default-OFF per ADR-133); flat spawn-depth doctrine + reserved `CEO_MAX_SPAWN_DEPTH` ceiling (`team.md` §ROUTING TABLE, PLAN-135 D6+H11) |
| 2 | **Transparency** — agent behavior is observable and explainable | HMAC-chained append-only audit log (`audit_log.py` PostToolUse observer; `AUDIT-LOG-SCHEMA.md`); closed-enum action vocabulary (no free-text actions — every audited event is one of the enumerated `audit_emit` actions); read-only loopback SSE dashboard (`audit-dashboard.py`); `audit-query.py` (9 sub-commands); on-disk debate ledger (`DEBATE-SCHEMA.md` §3) and ADR ledger (`.claude/adr/`); PLAN-SCHEMA §13 verification declaration (claims must declare how they were verified) |
| 3 | **Alignment with operator intent** — agents do what was actually asked | Plan schema with explicit acceptance criteria (`PLAN-SCHEMA.md`); mandatory spawn contract — PERSONA + SKILL CONTENT/REFERENCE + FILE ASSIGNMENT, enforced by `check_agent_spawn.py`; worker return-status contract `DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED` (`team.md` §Step 5); verify-don't-trust doctrine — controller re-runs checks before accepting `DONE` (`team.md` §Step 6; ADR-141 triage-reduce); pre-registered falsifiers for capability claims (PLAN-134 prereg discipline); **rule-enumeration checkpoint** on policy personas (see note below) |
| 4 | **Privacy protection** — agentic interactions do not leak personal data | Contamination guard — no personal handles/project names in template content (`check-contamination.sh`; CLAUDE.md §5); PII skill set `core/pii-data-flow` + `core/consent-lifecycle` + `core/dpo-reporting` (ADR-120) routed to the Compliance Specialist persona (`team.md` ROUTING TABLE); redact-before-logging rule (security-and-auth skill rule 7); audit telemetry is local-only (`~/.claude/projects/.../audit-log.jsonl`; no cloud export by default — meta-repo secrets never go cloud, `docs/MECHANISM-SELECTION.md` scheduling doctrine) |
| 5 | **Security** — agents are protected against misuse and injection | Governance hooks: `check_bash_safety.py`, `check_canonical_edit.py`, `check_agent_spawn.py`, `check_read_injection.py` (prompt-injection surface), git-hook-bypass guard (ADR-143); model-id allowlist (ADR-149) — no silent model substitution; cross-vendor pair-rail review (ADR-145 — Codex second opinion on security-relevant changes); threat models (`docs/threat-model.md`, `docs/CROSS-LLM-THREAT-MODEL.md`); branch-protection compensating controls — hooks + GPG sentinels + Codex pair-rail (ADR-003-AMEND-1); fail-open on infra bugs but fail-CLOSED on security checks (CLAUDE.md §5; security-and-auth rule 6) |

**Persona checkpoint (the control behind row 3, also published per
PLAN-135 D9-lite):** the security / compliance / code-review personas
carry a mandatory **rule-enumeration checkpoint** — *between tool
calls, enumerate the rules applicable to the next action and check
the planned action against each; cite the rule when raising a finding
or VETO*. This is the tau-bench-supported pattern (explicit rule
rehearsal between tool calls materially improves policy adherence).
Canonical text: `team.md` §Policy-persona rule-enumeration checkpoint;
mirrored in `.claude/agents/security-engineer.md` and
`.claude/agents/code-reviewer.md`.

**Two independent ledgers (forward pointer, full D9):** the local
HMAC-chained audit log (row 2) can be corroborated by the
**Compliance API Activity Feed** — a server-side ledger the local
chain cannot retroactively alter, giving auditors two independent
evidence streams. The wiring/citation detail belongs to
`docs/soc2-audit-mapping.md` (harvest D9 full scope, not D9-lite).

**Independent rail-tamper witness — "who watches the hooks"
(PLAN-135 W5 O10, ADR-087-AMEND-1):** the audit log (row 2) is
written *by* the hook rail, so a silently-disarmed hook (exec-bit
stripped — S228; settings-merge skipped — S217) emits no event to
flag its own absence — the same blind spot the threat-model records
for the H2/ConfigChange hook (`THREAT-MODEL-WORKSHEET.md` §2:
"H2 is itself a hook … blind to outside-harness edits"). The opt-in
OTel profile (`templates/settings/settings.stack.otel.json`,
`CLAUDE_CODE_ENABLE_TELEMETRY=1` → loopback sink at
`.claude/scripts/otel-local-sink.py`, **no egress**) adds a
*second, independent* channel: Claude-Code-native
`OTEL_LOGS_EXPORTER` `hook_execution` events, produced by the harness
outside the framework's emit surface, so a disarmed hook still leaves
a trace an external diff against the registered-hook set can catch.
Positioned per ADR-087-AMEND-1: **audit-log = tamper-evident truth;
OTel = dashboard** — the sink is a lossy, non-canonical mirror that no
governance hook ever reads as a decision input. ADR-087's refusal to
*emit* framework-native spans stands; this only *consumes* the
telemetry the harness already produces (consume-native ≠ emit-native).

---

## §2. Grandfathered warnings — they look like issues but aren't

This section explains the **2 grandfathered warnings** that `validate-
governance.sh` emits on every clean run. Both are by-design carve-outs
for the reference `fintech` squad that predates ADR-009 bundle
requirements. Neither blocks CI, neither blocks v1.6.0 GA, neither
bloquea adopter installs. They are **advisory** signals that a future
sprint can harden if the Owner decides to backfill fintech to the full
ADR-009 contract.

### Current output

```
$ bash .claude/scripts/validate-governance.sh
...
--- Summary ---
  Skills referenced: 46 / 48 installed
  Errors:   0
  Warnings: 2

PASS: Governance files validated.
```

The 2 warnings are:

1. `WARN (grandfathered): task-chains=0 (<2)` on the `fintech` squad.
2. `WARN (grandfathered): examples=0 (<1 — need examples/PLAN-*.md)` on the `fintech` squad.

### Why they exist — historical context

ADR-009 (2026-03, Sprint 5) formalized the **squad bundle contract**:

- ≥5 persona sections in `team-personas.md`
- ≥3 SKILL.md under `skills/`
- ≥10 entries in `pitfalls.yaml`
- ≥2 entries in `task-chains.yaml`
- ≥1 example plan under `examples/`

The `fintech` squad was built BEFORE ADR-009 (Sprint 2-4 era, ~2026-02).
It was the **prototype squad** whose layout shaped the ADR. Retrofitting
ADR-009 onto an already-referenced production fixture would either:

- Force a breaking change to the squad's shipped artifacts (task-chains
  file that changes the recommended work flow), OR
- Auto-generate synthetic content to tick the boxes (which adopter would
  then inherit as "official" guidance — worse than no content).

The ADR-009 hardening process for `fintech` specifically is a Sprint 26+
deliverable, NOT a pre-GA blocker.

### What the grandfather list means

File: `.claude/scripts/validate-governance.sh` line 219-221.

```bash
# Grandfather list — these squads predate ADR-009 and have open backlog
# items to bring them into conformance. Failures emit WARNINGS only.
SQUAD_GRANDFATHER="fintech"
```

Behavior:

- For squads in `SQUAD_GRANDFATHER`: contract violations count as
  **WARNINGS**, NOT errors. The script exits 0.
- For NEW squads (trading-hft, lgpd-heavy-saas, edtech, government —
  all post-ADR-009): contract violations count as **ERRORS**. The
  script exits 1.

This is the "soft-fail for legacy / hard-fail for new" pattern
standard in governance tooling (RuboCop, ESLint, pylint, etc.
use the same "grandfather by commit timestamp" convention).

### Path to close the warnings

If a future sprint decides to backfill `fintech` to full ADR-009:

1. **Author `task-chains.yaml`** for fintech. Minimum 2 entries per
   ADR-009 §3.4. The fintech squad already ships `task-chains.yaml`
   at the repo root (universal chains); the gap is a **squad-scoped**
   chain file. A reasonable starter:
   - `chain_exchange_onboarding` — using exchange-onboarding-playbook
     skill end-to-end.
   - `chain_financial_display_hardening` — financial-display +
     financial-correctness-and-math end-to-end.

2. **Author `examples/PLAN-*.md`** for fintech. Minimum 1 per
   ADR-009 §3.5. A reasonable starter:
   - `examples/PLAN-EXAMPLE-add-new-exchange.md` — walks an adopter
     through adding a new crypto exchange to their trading platform.

3. **Remove `fintech` from `SQUAD_GRANDFATHER`** in
   `validate-governance.sh`. The warnings become errors; CI enforces
   from that commit forward.

**Estimated effort:** ~2-4h for a dedicated Sprint-26+ commit.

**Why not done now:** none of the 3 items above affects runtime,
security, or correctness. They are **pedagogical artifacts** to help
adopters install+use the fintech squad. The existing
`team-personas.md`, `pitfalls.yaml`, and 9 SKILL.md under
`skills/fintech/skills/` already provide the install-ready surface.
The missing task-chains + example would be additive adopter onboarding
polish.

### Related

- **ADR-009** — squad bundle contract (the origin of the 5
  requirements).
- **PLAN-019 Phase J** — trading-hft team-personas SKILL MAP extension
  (closed 3 OTHER warnings; this leaves the 2 grandfathered).
- **PLAN-023 Phase J** — final confirmation that the 2 remaining
  warnings are by-design with this doc as the rationale (2026-04-18).

### What §2 is NOT

- NOT a claim that fintech is deficient. Fintech is the most complete
  squad in the framework; it just predates one of its own contract's
  requirements.
- NOT a blocking item for v1.6.0 GA. `validate-governance.sh` PASSES
  with these warnings; release gate is green.
- NOT a stale TODO. Backfilling fintech is a scoped Sprint-26+ item
  with explicit effort estimate and closure path above.
