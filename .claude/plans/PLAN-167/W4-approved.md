# PLAN-167 W4 — approved.md (DRAFT, deliberately unsignable)

> **`Anchor-SHA` is a PLACEHOLDER on purpose.** This file cannot be signed as
> it stands. The Owner pins the anchor to the real HEAD at signing time — that
> is what binds the approval to a specific tree state instead of to a moving
> target.

```
Anchor-SHA: 08feef1a83d724eb3201518c3dbf12ddc2864d92
Plan: PLAN-167
Wave: W4
Ceremony: canonical-edit (Owner GPG)
```

## Scope — the exact paths this approval authorizes

Group **A — the ownership decision** (all three are `_CANONICAL_GUARDS`):

```
scripts/_framework_manifest_set.sh
scripts/install.sh
scripts/upgrade.sh
```

Group **B — free surface, already committed, listed for completeness**:

```
.claude/scripts/check-model-deprecations.py     (the FIFO hang fix)
scripts/tests/test-ownership-verdict-unit.sh    (new unit oracle)
```

Nothing else. `.github/workflows/*` is deliberately **out of scope** — see
Deferred below.

## What this changes

`install.sh` and `upgrade.sh` stop deciding ownership and start executing a
decision. One pure function, `_ownership_verdict()`, answers every cell of the
nine-dimension space; the callers observe the dimensions, call it, and carry
out the verdict. The branch cascades they used to run are removed.

Evidence, all reproducible from the repo:

| Instrument | Result |
|---|---|
| unit oracle (`test-ownership-verdict-unit.sh`) | **60/60**, milliseconds |
| e2e decision table (62 real installs/upgrades) | **58 green / 4 red** |
| cross-model rail | **4 rounds, ~14 findings, 6 applied** |
| regression diff vs the pre-refactor baseline | **0 cells changed status** |

## Defects this closes

1. **An out-of-tree write (S238 class).** The root pointer was written with
   `cat >`, which follows an adopter's leaf symlink and modifies a file
   OUTSIDE the target. Proven in live fire, now closed — the suite's escape
   tripwire reports zero escapes.
2. **An adopter's own `PROTOCOL.md` recorded as framework-owned.** The caller
   computed `PRESERVE_UNOWNED` and an unconditional assignment overrode it.
3. **A failed backup advancing the record.** `hash_source` stayed at
   `HASH_SOURCE` after a REFRESH that never executed — INV-3.
4. **r11-F1** (open since S296): absence of a LINK record counted as a match,
   so a `--link` rerun serialized an arbitrary symlink as a trusted delivery.
5. **A directory replacing a single-file surface** kept ownership, and the
   continuity branch then recorded the adopter's own children by their live
   hashes — which a later uninstall could delete.
6. **A tree-walking scanner hanging forever on an adopter FIFO**, killing the
   upgrade mid-run. It also MASKED the existing special-file guards: no e2e
   could reach them, so green there proved nothing about them.

## Known-open, with named cause (4 cells)

Recorded rather than hidden — this is the §6.10 posture.

| Cell | Cause | Class |
|---|---|---|
| `OWN-0016` | manifest enumerates live files only, so an emptied managed tree emits zero records and loses ownership | product, cause named by rail r2 |
| `OWN-0024` `OWN-0027` | the fault-injection fixture cannot distinguish "backup failed" from "the chmod never blocked the copy" | **instrument** |
| `OWN-0074` | fixture never customises the pointer, so the cell asserts nothing | **instrument** |

Two of the three are defects in the TEST, not the product. None blocks the
decision function; all four are reproducible with `--only <id>`.

## Rail termination (AC-8) — by CAP, not by silence

Four rounds ran. Round 4 still returned P1 findings, so the rail **did not
converge**; the hard cap in §W3 stopped it. Terminating by silence is
forbidden, so the reason is recorded here explicitly.

Trajectory: `50/12 → 55/7 → 57/5 → 58/4`, no regressions accumulated.

Unapplied round-4 findings, deliberately deferred:

- *Run the ownership oracles in CI* — requires editing
  `.github/workflows/smoke-install.yml`, which is a canonical surface outside
  this Scope. **Deferred to its own ceremony** (see below).
- *Route install ownership through the shared decision* — install's continuity
  path still decides locally. Real, and larger than a cap-round patch.
- *Preserve prior SPEC rows outside live enumeration* — the `OWN-0016` cause.

## Deferred — needs its own plan, do NOT fold in here

- **INV-4:** every upgrade degrades the root pointer to a literal
  `{{PROTOCOL_SOURCE}}`. Install substitutes its placeholders; upgrade does
  not. **Pre-existing and unrelated to this plan.** Reproducible probe:
  `evidence/probe-INV4-pointer-substitution.sh`.
- **CI wiring** (path filters + the `v1.2.0` tag fetch + running both oracles).
  Three separate rail rounds and the devops critique all raised it. It is a
  canonical-workflow edit and belongs in a ceremony whose Scope says so.

## Owner checklist

1. Read this file and `W2-STATUS-REPORT.md`.
2. `shasum -c .claude/plans/PLAN-167/staged-manifest.sha256` **from the repo
   root** — must be rc=0 (paths are repo-relative).
3. Pin `Anchor-SHA` to `git rev-parse HEAD`, then sign.
4. Follow `W4-land-runbook.md`.
