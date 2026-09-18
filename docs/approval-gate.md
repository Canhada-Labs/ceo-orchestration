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

Policy (`tests/fixtures/approval/policy-default.json` is the shipped default; the fields below are
validated, but an UNKNOWN key is ignored rather than rejected — see Limitations):

| field | meaning |
|---|---|
| `score.min` / `score.max` | minimum reviewer score and the scale; `"8/10"` is accepted, `"4/5"` (wrong scale) and prose are rejected |
| `severities.enum` | the ONLY severities accepted; anything else is ambiguous ⇒ REJECTED |
| `severities.blocking` | any finding with one of these ⇒ REJECTED |
| `severities.max_open` | per-severity cap on open findings (`{"P1": 0}` = no open P1) |
| `require_reviewed_equals_final` | the reviewer must have seen the FINAL revision (`review.reviewed_rev == final_rev`); a fix after the review needs a new review of the delta |
| `require_gate_green` | `gate[]` must be a non-empty list; every entry needs an int `rc == 0`, and a `failed` that is present must be an int that is not `> 0` (an entry with no `failed`, or no `cmd`, is accepted today — see Limitations) |
| `require_review_ran` | `review.ran` must be `true` |

Evidence (`ceo.approval-evidence/v1`): `final_rev`, `review{ran, reviewed_rev, score, findings[{severity, where, text}]}`,
`gate[{cmd, rc, failed, passed}]`. `findings` must be present even when empty — absence is not "none".

**Rules the decision follows:** every failed rule is named in `reasons`; the decision carries
`policy_sha256` and `evidence_sha256` so a later reader can bind it to the exact inputs. Under the
shipped default policy a missing score, findings list, reviewed revision or gate list, a prose
score, an out-of-enum severity, a wrong scale and a wrong revision ⇒ REJECTED. The inputs that
still come out APPROVED are listed under Limitations.

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
  methods in classes). Parametrised ids (`test_x[case]`) are NOT normalised: the suffix is compared
  literally and the reference comes back `node-not-found`.
- Known-open, found by the cross-review of the v1.4.1-rc.1 candidate (2026-09-18) and not cured in
  v1.4.1:
  - `approval_gate.py` still APPROVES a non-finite score (`"NaN"`, `"nan/10"`); a `gate[]` entry
    with no `failed` count or no `cmd`, or with a negative `failed`; and a policy whose restriction
    key is misspelled (`max_opne` for `max_open`): unknown keys are ignored, so the restriction
    silently disappears.
  - `test_refs.py`: a node id whose CLASS does not exist (`file.py::Missing::test_x`) resolves to
    the only test named `test_x` in that file instead of failing, so `match` can accept proof for
    a different class.
