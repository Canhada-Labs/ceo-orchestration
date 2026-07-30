# ADR-110-AMEND-1 — Pair-rail timeout contract (30 s default retired)

---
adr_id: ADR-110-AMEND-1
title: Pair-rail timeout contract — internal default 30→120 s, harness registration 60→150 s, invariant under test
status: ACCEPTED
amends: ADR-110
proposed_at: 2026-07-29
proposed_by: CEO (PLAN-164, GATE-V2 fresh-probe FAIL diagnosis)
session_origin: 2026-07-29 (post-S284; probe session 6de4f28e)
accepted_at: 2026-07-29
authorization: PLAN-164 W2 Owner-GPG ceremony commit tagged [SENT-PLAN164-RAIL] — this file reaches the canonical tree ONLY via that ceremony; a landed copy implies the gate fired
risk_tier: A
debate_required: true
debate_record: .claude/plans/PLAN-164/debate/round-1/consensus.md (3x ADJUST -> PROCEED; OQ1=120 / OQ2=150 ratified by Owner tie-break 2026-07-29)
related_plans: [PLAN-075, PLAN-081, PLAN-163, PLAN-164]
related_adrs: [ADR-106, ADR-110, ADR-182]
---

## §1 What this amendment changes

ADR-110 established the PreToolUse block mechanism for the pair-rail
(`check_pair_rail.py`). It never fixed an operative *timeout contract* — the
30 s internal default was an implementation literal, not a decided value.
Measurement (§2) shows 30 s is structurally below the latency of a real
Codex verdict, which made the rail 100% fail-open in production (12/12
`pair_rail_case` events in the entire life of the audit log are case F /
TIMEOUT — the rail NEVER completed a live in-hook review). This amendment
promotes the timeout pair to a decided, tested contract:

1. **Internal default `CEO_PAIR_RAIL_TIMEOUT_S`: 30 → 120.** Three literals
   in `check_pair_rail.py`: the env-read default string `"30"` → `"120"`
   (`os.environ.get("CEO_PAIR_RAIL_TIMEOUT_S", ...)`, ~L1717), the
   parse-error fallback float `30.0` → `120.0`, and the clamp-reset float
   `30.0` → `120.0` (plus the docstring at ~L51-52). Clamp bound `>600`
   unchanged.
2. **Harness registration timeout: 60 → 150** for the `check_pair_rail.py`
   PreToolUse entry in kernel `.claude/settings.json` AND template
   `templates/settings/settings.base.json` (parity enforced). Precedent for
   a >120 s registration already exists in the kernel:
   `codex_review_user_code.py` runs at `timeout: 130`.
3. **The layering invariant is now TESTED, not assumed**
   (`test_pair_rail_timeout_invariant.py`): parses `settings.json`,
   `settings.base.json`, and the hook's default literal, and asserts
   (a) kernel registration == template registration, and
   (b) `registration >= internal + 30` (absolute margin covering Python
   startup + redaction + verdict validation + observed load variance).
   A unilateral flip of any of the three literals goes red in the suite and
   in the pack-preflight overlay.
4. **`statusMessage` added to the registration** (kernel + template + the
   frozen-pack staged copies; e.g. "Pair-rail cross-model review — may take
   1-2 min"), so a session held by a synchronous review shows feedback
   instead of appearing frozen.

## §2 Evidence — measured, not inferred

Root-cause probe (2026-07-29, GATE-V2 fresh probe, anchor `a4371c7`;
diagnosis at `.claude/plans/PLAN-163/probes/GATE-V2-2026-07-29-FAIL-diagnosis.md`):
`codex exec` startup overhead is ~8 s and a realistic review prompt under
`reasoning effort: xhigh` returns in ~36 s — always >30 s.

Calibration dataset (consensus C5 protocol, EXECUTED in-debate, N=9, same
machine, verbatim):

| Condition | Latencies (s) |
|---|---|
| small prompt, idle machine | 25.8 / 33.3 / 34.9 / 36.3 / 38.8 / 68.8 |
| big prompt (15.4 KB), idle | 58.4 / 51.3 |
| small prompt, UNDER LOAD (test suite in parallel) | 75.1 |

p95 ≈ 75 s **> 70 s escalation threshold** of the measurement protocol
(consensus C5 / Critic-C MF5) → the protocol's own escalation rule selects
**internal 120 / registration 150** (not the 100/120 first draft).
150 − 120 = 30 s absolute margin. History: 12/12 `pair_rail_case` = F
(TIMEOUT); the 11 case-F events in the 168 h window pre-dating PLAN-163's
pin were latency, not integrity — ADR-182's pin fixed payload integrity and
could not have fixed this.

## §3 Recalibration trigger

After **≥10 healthy cases** (case A–E) accumulate post-uplift, the p95 of
verdict latency — `pair_rail_case.ts − pair_rail_review_expected.ts`, joined
on `(session_id, review_id)` — is recomputed from the audit log and the
120/150 pair is revisited (downward if p95 leaves generous headroom, upward
escalation if p95 approaches the internal budget). Any change is a new
amendment via ceremony, not a literal edit.

Documented query (stdlib-only; field names per the audit-log schema as
consumed by `land-plan163-pin.sh --gate-v2`: `action`, `ts`/`timestamp`,
`review_id`, `session_id`, `case`):

```python
import json, statistics
from datetime import datetime, timezone

def _dt(ts):
    d = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)

expected, lat = {}, []
for line in open(LOG, encoding="utf-8", errors="replace"):
    line = line.strip()
    if not line:
        continue
    try:
        ev = json.loads(line)
    except json.JSONDecodeError:
        continue
    key = (str(ev.get("session_id") or ""), str(ev.get("review_id") or ""))
    ts = ev.get("ts") or ev.get("timestamp")
    if not key[1] or not ts:
        continue
    if ev.get("action") == "pair_rail_review_expected":
        expected[key] = _dt(ts)
    elif (ev.get("action") == "pair_rail_case"
          and ev.get("case") in ("A", "B", "C", "D", "E")
          and key in expected):
        lat.append((_dt(ts) - expected.pop(key)).total_seconds())
if len(lat) >= 10:
    print("n=%d p95=%.1fs" % (len(lat), statistics.quantiles(lat, n=20)[18]))
else:
    print("n=%d — trigger not met (need >=10 healthy cases)" % len(lat))
```

(`jq -r 'select(.action=="pair_rail_case") | [.ts,.case,.review_id] | @tsv'`
is fine for eyeballing, but the join on `(session_id, review_id)` makes the
Python form normative.)

## §4 Named residuals (accepted, on the record)

- **(i) Env-knob sub-floor = universal fail-open.** Any session exporting
  `CEO_PAIR_RAIL_TIMEOUT_S` below real verdict latency re-creates 100%
  case-F fail-open by env alone. ACCEPTED because env-control over the
  session is already a high privilege (superset of this threat) and every
  such miss is auditable as a case-F event in the HMAC chain. A minimum
  floor on the knob (e.g. `<10 → default`) was DEFERRED — changing the
  semantics of a documented knob is a new contract (consensus
  rejected/deferred item 2).
- **(ii) Clamp overflow semantics — known wart.** A value `>600` or a
  parse error does not clamp-to-bound: it RESETS to the default (now 120).
  An operator setting `9999` silently gets 120, not 600. Documented here as
  a known wart; clamp-to-bound was a nice-to-have only if it fit the same
  diff (consensus deferred item 3).
- **(iii) The next hidden "default 30".** `check_codex_filewrite.py`'s
  registration runs at `timeout: 30` (kernel settings). Safe today (that
  hook does not hold a synchronous Codex verdict), but IF the live review
  path ever migrates to MCP dispatch through it, it becomes the same class
  of structurally-sub-latency default this amendment retires. Out of scope
  here; named so the migration reviewer trips over it.

## §5 Alternatives rejected

- **(a) Asynchronous post-facto review** (let the edit land, review after).
  REJECTED: the rail's entire value is the PRE-write veto — cases B/C
  REJECT block the write before it exists (ADR-110's reason to be). An
  async lane already exists (`stop_review`); duplicating it here would
  retire the only pre-write cross-model gate.
- **(b) Per-invocation reasoning-effort downgrade** (drop Codex below
  `xhigh` inside the hook to fit 30 s). REJECTED: verdict quality at lower
  effort is non-validated for this rail, and effort is deliberately
  external config (the harness pin, ADR-182) — the hook silently overriding
  it would be a second, hidden config surface.

## §6 Declared cost

- A canonical, non-sentineled edit that triggers a live review now holds
  the session synchronously for up to ~120 s. Mitigated by `statusMessage`
  (§1.4); the hold also pushes heavy canonical work toward staged
  copies + ceremony — which is the desired flow, not a regression.
- Reviews that actually COMPLETE are recurring Codex spend the 30 s-timeout
  era never paid (every prior invocation died before billing a verdict).
  Tracked in the finops lane.

## §7 Semantics of the re-anchored GATE-V2

The audit log is append-only (HMAC chain): the 2026-07-29 case-F probe is
permanent in the post-`a4371c7` set, so `failopen==0` is unsatisfiable
against the old anchor. The PLAN-164 ceremony re-anchors at the
`[SENT-PLAN164-RAIL]` commit. A GATE-V2 PASS against the new anchor proves
**"liveness under ADR-182 pin + new timeout contract"** — strictly STRONGER
than the original claim, since the payload pin and verify-then-invoke path
are untouched by this amendment (the frozen PLAN-163 packs contain no
staged copy of ADR-110, so this amendment survives the pack apply and does
not disturb the double-APPROVEd byte set).
