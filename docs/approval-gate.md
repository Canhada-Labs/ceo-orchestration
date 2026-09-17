# Approval by code — `approval_gate.py` and `test_refs.py` (PLAN-190 W3)

> Audience: authors of Workflow scripts and autonomous pipelines in a consumer repository. Both
> tools are stdlib Python ≥ 3.9, read-only, and ship with the framework under `.claude/scripts/`.

## The loss this closes

Measured on one consumer (2026-09-15→17): three slices were declared green by the pipeline script
while the cross-model reviewer had scored them below the bar (the script only looked at P0/P1
findings); a severity written in prose fabricated a wrong verdict; nine false "proofs incomplete"
came from comparing function NAMES with file PATHS. The order of 2026-09-17: *"O estado de aprovação
deve ser calculado por código conforme a política vigente […]. Resposta ausente, ambígua ou inválida
não pode virar verde."*

## `approval_gate.py decide`

```
python3 .claude/scripts/approval_gate.py decide --policy policy.json --evidence evidence.json [--json]
  rc 0 APPROVED · rc 3 REJECTED (reasons listed) · rc 2 unreadable input (a rejection)
```

Policy (closed schema, `tests/fixtures/approval/policy-default.json` is the shipped default):

| field | meaning |
|---|---|
| `score.min` / `score.max` | minimum reviewer score and the scale; `"8/10"` is accepted, `"4/5"` (wrong scale) and prose are rejected |
| `severities.enum` | the ONLY severities accepted; anything else is ambiguous ⇒ REJECTED |
| `severities.blocking` | any finding with one of these ⇒ REJECTED |
| `severities.max_open` | per-severity cap on open findings (`{"P1": 0}` = no open P1) |
| `require_reviewed_equals_final` | the reviewer must have seen the FINAL revision (`review.reviewed_rev == final_rev`); a fix after the review needs a new review of the delta |
| `require_gate_green` | every `gate[]` command must have `rc == 0` and `failed == 0` |
| `require_review_ran` | `review.ran` must be `true` |

Evidence (`ceo.approval-evidence/v1`): `final_rev`, `review{ran, reviewed_rev, score, findings[{severity, where, text}]}`,
`gate[{cmd, rc, failed, passed}]`. `findings` must be present even when empty — absence is not "none".

**Rules that make the decision safe:** there is no default-green path; every failed rule is named
in `reasons`; the decision carries `policy_sha256` and `evidence_sha256` so a later reader can bind
it to the exact inputs. Missing, prose, out-of-enum, wrong-scale, wrong-revision ⇒ REJECTED.

### COMMON block for Workflow scripts

Paste this into a workflow script and never declare green without it. The gate agent (or the
script, if it can shell out) produces `evidence.json`; the decision is the ONLY thing the script
reads to decide `VERDE`:

```js
// COMMON: approval by code (PLAN-190 W3). `decision` comes from
//   python3 .claude/scripts/approval_gate.py decide --policy <policy> --evidence <evidence> --json
// run by the gate agent and returned VERBATIM in its result under `approval`.
function approved(result) {
  const a = result && result.approval
  if (!a || a.decision !== 'APPROVED') return false            // absent or ambiguous ⇒ not green
  if (!Array.isArray(a.reasons) || a.reasons.length !== 0) return false
  if (typeof a.evidence_sha256 !== 'string' || a.evidence_sha256.length !== 64) return false
  return true
}
// usage: if (!approved(gate)) { log('[' + ID + '] NÃO VERDE: ' + JSON.stringify((gate.approval || {}).reasons || 'sem decisão')); return {ok:false, ...} }
```

The gate agent's prompt must say: *write `evidence.json` with the FINAL revision sha, the reviewer's
score and findings as returned (no paraphrase), and the gate commands' `rc`/`failed`; run
`approval_gate.py decide --json`; return its output verbatim under `approval`.*

## `test_refs.py`

```
python3 .claude/scripts/test_refs.py normalize --repo . REF [REF ...]
python3 .claude/scripts/test_refs.py match --repo . --declared declared.txt --proved proved.json
  rc 0 all resolved / all declared proved · rc 3 any ambiguous, unknown or missing proof
```

Accepts file paths, pytest node ids, bare function names and `Class.test_x`; resolves them by a
static AST scan of `test_*.py` / `*_test.py` (never executes tests). A bare name defined in two
files is **ambiguous** (candidates listed); an unknown name or path is an **error**. `match`
compares two lists AFTER normalisation, so "the implementer wrote function names and the matcher
compared paths" cannot happen again: both sides become node ids first.

## Limitations (declared)

- `approval_gate.py` decides on evidence it is GIVEN; it cannot verify that the reviewer really ran
  or that `final_rev` is the revision on disk. The gate agent's prompt (above) and the launch ledger
  (W1) bind the evidence to the run; W2's checkpoint binds phases to revisions.
- `test_refs.py` recognises pytest/unittest shapes (module-level `test*` functions, `test*`
  methods in classes); parametrised ids (`test_x[case]`) are matched by their base name.
