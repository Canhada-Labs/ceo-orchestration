# ADR-099 — `changesets` workflow adoption (closeout aggregator, soft co-existence with CLAUDE.md narrative)

**Status:** ACCEPTED
**Date:** 2026-05-02
**Enforcement commit:** `06b368db6309b09e3c34e5d3fd664e7ae1adcb91`
**Decision drivers:**
- Reduce CHANGELOG drift across closeouts (every session hand-edits root `CHANGELOG.md` ad-hoc; format inconsistent)
- Preserve CLAUDE.md narrative governance trail (NOT replaced — soft co-exists)
- Stdlib-only — no `@changesets/cli` Node dependency (PLAN-068 §0.4 anti-goal R1)
- Compatible with the existing `release.yml:133` inline grep contract — `grep -qE "^## \[${VERSION}\]" CHANGELOG.md` — without workflow changes
- LOCAL-ONLY at closeout (DevOps R1 P0-03 — not in CI)

## Context

Helmor analysis 2026-05-02 (PLAN-068 lesson L2) surfaced the per-PR
`.changeset/<random>.md` workflow as a low-cost ergonomic improvement
for tracking user-visible changes between release tags. Helmor adopts
the upstream `@changesets/cli` Node tool; ceo-orchestration is
stdlib-only (Python ≥ 3.9, no Node runtime — PLAN-068 §0.4 R1 + ADR-085
Claude-only positioning), so the upstream tool is rejected outright.

Today the project hand-edits root `CHANGELOG.md` at each closeout. The
file is 160 KB with 20+ tagged entries. Every session writes a `## [X.Y.Z] - <date>`
block plus prose, then the release pipeline at `release.yml:133`
verifies the block exists via inline grep. The format has drifted
over sessions (subheading style, bullet conventions, version-vs-tag
date alignment); each closeout re-derives the convention.

PLAN-068 v2 Track-1 (the corrected scope post-Round-1 split — see
PLAN-068 §11.2.1) proposes a stdlib aggregator that runs at closeout
to consume per-PR `.changeset/<slug>.md` files and emit a single
`## [VERSION] - <date>` block above the latest existing entry. Phase 0.5
PoC ran 9 acceptance probes (5 PoC tests + 4 regex contract probes) at
`.claude/plans/PLAN-068/phase-0-5-poc/`, all PASS — including
direct equivalence of the `release.yml:133` inline grep against the
sandbox CHANGELOG post-aggregation.

CLAUDE.md retains its session-narrative `## CHANGELOG` (governance
trail of why each session shipped what it did). Root CHANGELOG.md
becomes the user-visible-changes machine-aggregated record. Both
co-exist; this ADR documents the boundary.

## Decision drivers

- **Format drift is real.** Hand-edited CHANGELOG.md across 20+ tagged
  releases shows 3 distinct subheading patterns and inconsistent date
  formats. Aggregation enforces a single format.
- **Stdlib-only is non-negotiable** per ADR-085 Claude-only thesis +
  PLAN-068 §0.4 R1. No Node, no third-party Python deps.
- **`release.yml:133` is the authoritative validator.** PLAN-068 §11.2.1
  +  bench-results.md §2 confirmed: the contract is the inline grep
  `^## \[${VERSION}\]`, not a `.mjs` extractor (the previously-cited
  `extract-release-notes.mjs` does not exist — phantom reference closed
  by PLAN-068 doc patch). Aggregator output must satisfy this regex.
- **CLAUDE.md narrative trail is load-bearing** for governance audit
  (per CLAUDE.md §0 cache discipline + §6 Current Work pattern). It
  must NOT be replaced; soft co-existence is the only acceptable
  framing.
- **Closeout-LOCAL execution** preserves CI surface area (zero new
  `release.yml` steps). DevOps R1 P0-03 is satisfied by-design.
- **Empirical PoC GO verdict** at PLAN-068/phase-0-5-poc/bench-results.md
  §1 (9/9 PASS, no NO-GO conditions tripped) provides the evidence base
  for adoption.

## Options considered

### Option A — `@changesets/cli` Node tool (REJECTED)

Adopt the upstream `@changesets/cli` Node package as helmor does.

- Pros: battle-tested, used by ~25k+ npm packages, active maintenance.
- Cons: introduces Node runtime dependency contradicting PLAN-068 §0.4
  R1 + ADR-085 Claude-only thesis. Adopters would need `node` + `npm`
  installed. Supply-chain blast radius widens (Node modules transitive).

**Rejected** — runtime/dependency cost incompatible with stdlib-only
posture.

### Option B — Hand-rolled stdlib aggregator at closeout (CHOSEN)

Author `.claude/scripts/aggregate-changesets.py` (~80-200 LoC stdlib),
invoked LOCAL-ONLY at closeout.

- Pros: zero new runtime; fully testable under existing `unittest`
  harness; output verified empirically against the
  `release.yml:133` inline grep contract; CLAUDE.md narrative
  preserved.
- Cons: framework owns the maintenance burden of the aggregator (≈80 LoC
  + tests). Mitigated by Phase 0.5 PoC validating the format spec
  before production code exists.

**Chosen.** Phase 0.5 PoC GO verdict + Phase 1 production code already
on disk make this concretely feasible.

### Option C — Hard cutover replacing CLAUDE.md narrative (REJECTED)

Migrate the CLAUDE.md `## CHANGELOG` session-narrative trail to root
CHANGELOG.md only; delete the CLAUDE.md narrative.

- Pros: single source of truth.
- Cons: destroys governance value of CLAUDE.md (per-session "why"
  context, archived via per-session memory files). The two records
  serve different audiences (auditors + future-Claude vs.
  end-user release-notes consumers).

**Rejected** — governance trail loss exceeds dedup benefit.

### Option D — Defer adoption (REJECTED)

Status quo: continue hand-editing CHANGELOG.md.

- Pros: zero net new code.
- Cons: format drift accumulates; lesson L2 from helmor analysis goes
  un-acted-upon; closeout cognitive overhead persists.

**Rejected** — measurable accumulating cost; PLAN-068 v2 Round 1 ADJUST
verdicts converged on adoption.

## Decision

**Option B.** Adopt the `.changeset/<random-slug>.md` per-PR convention
with frontmatter `type: <patch|minor|major>` plus a one-line user-visible
description in the body. The stdlib aggregator
`.claude/scripts/aggregate-changesets.py` runs LOCAL-ONLY at closeout,
mutates root `CHANGELOG.md` by inserting a `## [<X.Y.Z>] - <date>` block
above the latest existing tagged version block, then deletes the
consumed `.changeset/*.md` files.

Format spec (from Phase 0.5 PoC, validated empirically):

- Filename: `.changeset/<slug>.md` — slug arbitrary; `README.md` and
  `config.json` are skipped.
- Frontmatter required, fail-CLOSED on absence:
  - Open delimiter `---` on first line.
  - `type: <patch|minor|major>` (only these three values legal).
  - Close delimiter `---` on its own line.
- Body: one-line user-visible description (multi-line allowed; first
  line is what becomes the bullet).
- Multi-doc YAML rejected (fail-CLOSED).

Aggregator behavior contract:

- `--version <X.Y.Z>` + `--date <YYYY-MM-DD>` required.
- `--dry-run` mode emits the would-be block without mutation; sandbox
  SHA-256 unchanged.
- Idempotency: if CHANGELOG already contains `## [<version>]`, exit 0
  no-op (re-runs are safe).
- Insertion position: ABOVE the first `^## \[\d+\.\d+\.\d+(?:-rc\.\d+)?\]`
  match (i.e. above the latest existing tagged version block).
- File ordering: stable secondary sort by `p.name` after primary sort
  by `Path.stat().st_mtime` ascending (guarantees determinism on
  coarse-mtime filesystems — bench-results.md §4 risk #3).
- `--check` mode (Phase 1 hardening): exit non-zero if `.changeset/*.md`
  present without `--version` (guards against orphaned changesets at
  closeout).

Co-existence boundary:

- Root `CHANGELOG.md` — user-visible changes per tagged release;
  machine-aggregated; governs `release.yml:133` validation.
- CLAUDE.md `## CHANGELOG` — session narrative, governance "why",
  per-session archive-to-memory pattern. Hand-curated; load-bearing
  for cache discipline (CLAUDE.md §0 Gate-1 closeout-only edits).

`release.yml` is not modified. Line 133's inline grep
`grep -qE "^## \[${VERSION}\]" CHANGELOG.md` remains the validator;
aggregator output is shaped to satisfy it (Phase 0.5 PoC §2 probes
R-A through R-D verified equivalence).

## Consequences

**Positive (+):**
- Reduced format drift; auto-generated tagged blocks with single
  template (`render_block` in aggregator).
- Stdlib-only; no third-party deps; no Node runtime.
- Compatible with existing `release.yml:133` grep contract — empirically
  validated by Phase 0.5 PoC R-A/R-B/R-C/R-D probes (all PASS).
- LOCAL-ONLY: zero CI surface change; DevOps R1 P0-03 satisfied
  by-design.
- CLAUDE.md governance narrative preserved (soft co-existence).
- Closeout cognitive overhead reduced — author writes one
  `.changeset/<slug>.md` per PR rather than re-deriving a CHANGELOG
  block format.

**Negative (-):**
- Authors must remember to write `.changeset/<slug>.md` per PR.
  Mitigation: `--check` mode + `.changeset/README.md` discoverable +
  PR-template enforcement reserved for a future ADR (out of scope here).
- Aggregator file mtime sort is FS-dependent. Mitigation: stable
  secondary sort by `p.name` already in production code (Phase 1
  hardening per bench-results.md §5 recommendation 2).
- Two CHANGELOG-shaped artifacts now exist (root + CLAUDE.md). The
  boundary is documented in §Decision; auditors must read both for
  full governance picture.
- Multi-doc YAML detection is regex-based (Phase 0.5 PoC §4 risk #4).
  Pathological inputs with `---` inside fenced code blocks would
  fail-CLOSED — the safe default.

**Neutral (~):**
- Output format is enforced; reviewers cannot freestyle changelog
  prose — by-design (the goal is reduced drift).
- Aggregator deletes consumed `.changeset/*.md` files post-aggregation
  — git history preserves them for audit.

## Blast radius

**L3** — touches release pipeline (indirectly, via CHANGELOG.md
content), repo convention (new `.changeset/` directory), adopter UX
(authors write `.changeset/*.md` per PR), and the framework's stdlib
script library. Adopters need `.changeset/README.md` discoverable to
learn the convention.

## Compliance checklist

| Item | Verification |
|---|---|
| `.claude/scripts/aggregate-changesets.py` exists with stdlib-only imports | grep `^import\|^from` in production file |
| ≥ 10 paired tests under `.claude/scripts/tests/test_aggregate_changesets.py` | unittest discover count |
| `--dry-run` does not modify CHANGELOG.md | test asserts SHA-256 unchanged |
| `--version` + `--date` both required | argparse fails when missing |
| Idempotency: re-run on already-aggregated → no-op | test asserts hash unchanged on second invocation |
| Fail-CLOSED on missing/malformed frontmatter | tests assert non-zero rc + stderr `::error::` prefix |
| `release.yml:133` grep matches aggregated block | regex contract test against post-aggregation CHANGELOG |
| `.changeset/README.md` exists at repo root | file presence check |
| LOCAL-ONLY (no `release.yml` changes) | git diff `.github/workflows/` empty for this ADR ceremony |
| CLAUDE.md narrative preserved | grep `## CHANGELOG` in `CLAUDE.md` still present |

## Cross-references

- PLAN-068 §11.2.1 (Track-1 scope — changesets workflow corrected)
- PLAN-068 §11.4 acceptance criteria 1-10
- `.claude/plans/PLAN-068/phase-0-5-poc/bench-results.md` (Phase 0.5 GO
  verdict, 9/9 PASS)
- `.claude/plans/PLAN-068/phase-0-5-poc/aggregate-changesets.py` (PoC
  source, validated)
- `.claude/scripts/aggregate-changesets.py` (Phase 1 production target,
  promoted from PoC)
- `.claude/scripts/tests/test_aggregate_changesets.py` (test floor)
- `.github/workflows/release.yml:133` (the `grep -qE "^## \[${VERSION}\]" CHANGELOG.md`
  inline contract this aggregator satisfies)
- ADR-085 (Claude-only thesis — basis for stdlib-only constraint)
- ADR-093 (60-day refused-ADR moratorium — ADR-099 is ADDITIVE
  convention NOT a new default OR a refusal; moratorium NA per
  PLAN-068 §0.4 R11)
- Helmor analysis 2026-05-02 (lesson L2 — origin of the convention)
