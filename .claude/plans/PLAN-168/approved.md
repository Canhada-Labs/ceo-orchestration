# PLAN-168 — approved.md (DRAFT, deliberately unsignable)

> **`Anchor-SHA` is a PLACEHOLDER on purpose.** This file cannot be signed as
> it stands. The Owner pins the anchor to the real HEAD at signing time — that
> is what binds the approval to a specific tree state instead of to a moving
> target. **Precondition: the PLAN-166 ceremony must be LANDED first** — the
> staged copies of the shared files carry that content underneath this pack's
> edits, and `OWNER-LAND.sh` aborts if the live tree disagrees.

```
Anchor-SHA: 9d3f21d0caa8252f84410b9ff10c146a8004e805
Plan: PLAN-168
Wave: W1+W2+W3 (one pack, one ceremony — §3 of the plan)
Ceremony: canonical-edit (Owner GPG)
```

## Scope — the exact paths this approval authorizes

Group **A — canonical (`_CANONICAL_GUARDS`), the reason this ceremony exists**:

```
.github/workflows/smoke-install.yml
.github/workflows/ownership-nightly.yml
scripts/install.sh
scripts/upgrade.sh
scripts/_framework_manifest_set.sh
.claude/adr/ADR-190-ownership-decision-table-contract.md
```

Group **B — free surface, landed by the same pack, listed for completeness**:

```
scripts/tests/test-ownership-table.sh
scripts/tests/test-ownership-verdict-unit.sh        (unchanged — filter target only)
scripts/tests/ownership_table.tsv
scripts/tests/ownership-expected-reds.txt           (new)
scripts/tests/ownership-nightly-gate.sh             (new)
scripts/tests/test-ownership-nightly-gate.sh        (new)
scripts/tests/test-protocol-pointer-render.sh       (new)
scripts/tests/test-protocol-pointer-inv4.sh         (new)
scripts/tests/ownership-baseline-map.txt            (re-recorded, stable header)
.claude/scripts/tests/test_release_workflow_asserts.py
docs/ownership-decision-table.md
CLAUDE.md                                           (§1 count + §4 rule — ceremony-grade closeout edit)
README.md · README.pt-BR.md · docs/README.md · docs/FAQ.md
docs/CTO-GUIDE.md · docs/ARCHITECTURE.md · npm/README.md   (derived counts: 190 ADRs, 22 workflows)
```

## What this changes

**W1 — the ownership oracles get a CI that actually runs them.** Four filter
paths + the unit oracle per-PR in `smoke-install.yml`; a NEW
`ownership-nightly.yml` runs the ~25-min e2e nightly behind
`ownership-nightly-gate.sh`, which compares the exact RED id set against
`ownership-expected-reds.txt` (any difference fails — shrinkage included; any
TIMEOUT/ESCAPE/AMBIG fails outright; never `--map`). The gate itself is
proven by a 12-scenario fake-harness control that also runs per-PR.

**W2 — INV-4 closed at the class.** The pointer body is rendered by ONE
shared generator inside `_framework_manifest_set.sh`; install and upgrade
both call it (byte-identical output, proven against a real install).
`PROTOCOL_SOURCE` is read from `request.placeholders` (it was ALWAYS
persisted — the debate's contrary claim checked the wrong key). A
`{{PROTOCOL_SOURCE}}`-literal pointer is recognized by exact template
reconstruction (never substring) and CURED with backup; adopter-customized
pointers stay preserved (S238). TSV gains OWN-0092/0093/0094; OWN-0074 goes
GREEN; expected reds shrink to `{OWN-0016, OWN-0024, OWN-0027}`.

Also in `upgrade.sh`: the literal `ADOPTER-FORK` token is RESTORED in the
preserved-fork WARNING — a PLAN-167 rewrite regression caught by the
PLAN-166 land's F3 e2e (44/45; back to 45/45 with this pack, proven in the
overlay).

**W3 — ADR-190.** The decision-table contract on the record: 10 dimensions,
the 4-verdict enum (`ABORT_SURFACE` is an execution failure, not a verdict),
INV-1..4, the deliberate SPEC/PROTOCOL asymmetry, `degraded` + hash-name
aliasing, ADR-155-AMEND-1 amended-not-revoked, 3 open cells + OWN-0074 as
closed history.

## D2 scope nuance the Owner ratifies by signing

D2 said "rows are only ADDED". Two verified consequences of the cure required
more, both recorded in the plan §7 and ADR-190:
- `OWN-0074`'s expected pair stays `PRESERVE_OWNED HASH_CANONICAL_POINTER`
  (verdict column untouched), and the harness resolves the
  PRIOR/CANONICAL naming ONLY when the two digests are byte-equal (post-fix
  aliasing) — the observation cannot distinguish names for equal bytes.
- `live_content` gained the value `degraded` (docs §2.4 + R-04b).

## Evidence (recorded in plan §7 + rail/)

Rail: r1 7 accepted, r2 6 accepted, r3 3 accepted + 1 refuted-with-evidence;
closed at the AC-8 cap of 3 with the reason recorded. Proofs: render control
8/8 (byte parity vs real install) · INV-4 e2e 4/4 legs · unit oracle 63/63 ·
gate control 12/12 · full-table e2e via the real gate (see §7) ·
claims + verify-counts rc=0.
