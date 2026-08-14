---
command: /agent-budget
alias: /agent budget
description: Rollup token usage and cost for a plan or time window — /agent budget
usage: "/agent budget [PLAN-NNN] [--since 24h] [--json]"
idempotent: true
allowed-tools: Bash
---

# /agent budget — Token + cost rollup from audit-log

Reports running token + cost totals (via
``.claude/scripts/budget-summary.py``) for a specific plan or the last
24h (or other window). Snapshot-only: the command does NOT touch the
audit-log, so running it twice on the same state returns the same
numbers.

Pricing source: ``docs/provider-pricing.md``. When that table contains
``TBD`` rows (no confirmed prices for the model), the cost column
falls back to ``"TBD"`` and only token counts are shown. See
ADR-033 §3 for the pricing policy.

## Arguments received

`/agent-budget $ARGUMENTS`

- no args → rollup across all plans, all time
- first positional `PLAN-NNN` → plan filter
- `--since <expr>` anywhere → time window (Nm / Nh / Nd, e.g. `24h`)
- `--json` anywhere → JSON output (default: human table)

## Idempotency contract (M7)

This command is a **read-only snapshot** over the audit log at call
time. Running it twice with identical args produces identical output
modulo any new events the audit-log writer has appended in between.
It does NOT mutate state, emit audit events, or invoke remote APIs.
Safe for scripts / loops / dashboards.

## Procedure

### Step 1 — Parse flags

Extract:

- `PLAN` = first positional token matching `PLAN-\d{3}`
- `SINCE` = value following `--since`
- `FORMAT` = `json` if `--json` appears, else unset

### Step 2 — Run backing script

```bash
python3 .claude/scripts/budget-summary.py \
  ${PLAN:+--plan "$PLAN"} \
  ${SINCE:+--since "$SINCE"} \
  ${FORMAT:+--json}
```

### Step 3 — Interpret exit code

- 0 → print stdout verbatim (human table or JSON)
- 2 → usage error. Surface stderr; do not retry.

### Step 3b — Official Analytics cross-check (O3, fail-soft)

`budget-summary.py` derives cost from the **audit-log + shadow pricing**
(what the work *would* cost on metered API). The Claude Code Analytics
Admin API carries Anthropic's **own** `estimated_cost` per user/day —
an independent witness. Surface it as a separate cross-check section,
**snapshot-read only (never network)**:

```bash
python3 .claude/scripts/cc-analytics-pull.py --summary --json 2>/dev/null
```

- `{"available": false, "dormant": true, ...}` → print
  **"Analytics cross-check: dormant"** (built-but-dormant per OQ4 — no
  Admin key / no snapshot). The default; never an error.
- otherwise → print the official `estimated_cost` column **next to** the
  audit-log-derived rollup so a drift between the two is visible (the
  S227 reconciliation pattern). The key custody is the Owner's:
  `THREAT-MODEL-WORKSHEET.md §3` + `docs/rotation-log.md`. This command
  spends nothing and `cc-analytics-pull.py` is **fail-soft exit 0**.

Treat the two numbers as cross-check, not authority-swap: the audit-log
is the tamper-evident truth; analytics `estimated_cost` is Anthropic's
estimate at user-day granularity. Never silently replace one with the
other — show both, label the source.

### Step 3c — cross-check com a fonte nativa

The Claude Code harness also writes a **native on-disk usage source**
per spawned agent: session transcripts under
`~/.claude/projects/<cwd-slug>/<SESSION-UUID>/subagents/` carry
per-turn `message.usage` token blocks (fingerprint + live-fire census:
`.claude/plans/PLAN-178/w12-native-cost-probe.md`). Surface it as a
second cross-check section, **snapshot-read only (never network)**:

```bash
python3 .claude/scripts/cc-native-usage-pull.py --compact 2>/dev/null
```

(The puller accepts only `--root` and `--compact`; output is always
JSON on stdout.)

- dormant (no session has `subagents/`, or the Owner set
  `CEO_NATIVE_COST_DISABLE=1`) → print
  **"Native cross-check: dormant"**. Never an error — the puller is
  **fail-soft exit 0**, same doctrine as Step 3b.
- fingerprint drift (any startup drift probe fires) → the puller
  degrades to the audit-log source and SAYS so (reversibility per
  PLAN-178 W1.2 AC-2c; the fingerprint it validates is the
  `cc_native_usage` component in `.claude/scripts/substrate-watch.json`).
- otherwise → print the native token totals per spawn and per category
  (Task vs Workflow, categorized by **path shape**, never by
  `taskKind`) **next to** the audit-log-derived rollup so a drift
  between the two is visible.

Treat the two numbers as cross-check, not authority-swap: the audit-log
is the tamper-evident truth; the native source is the harness's own
per-turn accounting at spawn granularity. Never silently replace one
with the other — show both, label the source.

### Step 4 — Guidance

After printing, if this was a plan-filtered rollup, remind the user:

- "Budget hook advisory in Sprint 11 (ADR-033). Set
  `CEO_MAX_PLAN_TOKENS=<N>` to change the cap, `CEO_BUDGET_BYPASS=1`
  for emergency overrides (rate-limited 10/24h per plan)."
- "If `cost_source` is `TBD`, fill in confirmed 2026 prices in
  `docs/provider-pricing.md` to surface USD costs."

Never pretend a TBD cost is `$0` — always show the source tag.

## Exit codes

- 0 — summary printed
- 2 — bad argument
