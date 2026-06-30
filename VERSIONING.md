# Versioning Policy

<!-- last-reviewed: 2026-06-20 v1.0.0 -->

> **TL;DR** — SemVer at the **Compliance SPEC level** (`SPEC/v1/`),
> not at every internal symbol. Tagged releases mark SPEC-level
> stability; untagged commits on `main` may include experimental
> additions behind kill switches.

## Scope of "the version"

`VERSION` at the repo root is the **single source of truth** for the
SPEC level the working tree complies with. It moves on:

- Any change to a file under `SPEC/v1/` (additive or breaking)
- Any change that introduces a **new trust boundary** an adopter must
  accept (e.g. ADR-051 added the SHA-pinned skill-by-reference path → MINOR bump)
- Any change to canonical-edit-guarded paths that alters governance
  semantics (mechanically gated by `check_canonical_edit.py`)

It does **not** move on:

- Doc improvements that don't change a contract
- New skills added under `.claude/skills/core/` or
  `.claude/skills/domains/<domain>/skills/` (skills are content, not contract)
- New plans, ADRs in PROPOSED state, or research notes
- Test additions, refactors that preserve byte-identity of fixtures
- New optional CLI tools (`ceo-cost`, `ceo-health`, etc.) — additive,
  no SPEC change

## SemVer semantics at SPEC level

Format: `MAJOR.MINOR.PATCH[-rc.N]`.

### MAJOR — breaking SPEC change

Bumped when a published `SPEC/v1/*.schema.md` removes or renames a
field, drops a required event type, or changes type semantics in a
way that breaks consumers.

**Historic example:** none yet within v1. The `v1` SPEC is intended
to remain stable through `v2.x`. A `v2/` SPEC would be created
alongside `v1/` for the transition window per ADR-005 §Migration.

### MINOR — additive SPEC change OR new trust boundary

Bumped when:

- A new field is added to an existing event (always additive — see
  `SPEC/v1/audit-log.schema.md` §Additivity)
- A new event type is added (e.g. `injection_flag` in v2.1)
- A new trust boundary is introduced that adopters must understand
  (e.g. ADR-051 skill-by-reference → `v1.5 → v1.6`)
- A new SPEC file is published under `SPEC/v1/`

**Historic examples:**

| Bump | What changed |
|------|--------------|
| `v1.0 → v1.4` | Sprint cadence, audit-log v2.1 → v2.5 (additive events) |
| `v1.4 → v1.5` | PLAN-014 — policy DSL, replay schema, predict-budget, memory-shared (4 new SPEC files) |
| `v1.5 → v1.6` | PLAN-020 ADR-051 — skill-by-reference expanded trust boundary; PLAN-021 ADR-052 — multi-model dispatch (additive `model:` frontmatter field + audit-log v2.8) |
| `v1.6 → v1.44` | Multiple MINOR bumps: federation, autonomous-loop, confidence-gate, coverage-doctrine, and security-event additions. See CHANGELOG.md for per-release detail. |
| `v1.44 → v1.45` | PLAN-113 Phase B remediation (framework-closure long-tail). See CHANGELOG.md `[1.45.0]`. |

### PATCH — bug fixes, additive features within SPEC

Bumped for:

- Hook bug fixes (e.g. the Session 32 redaction-check fix)
- Additive optional fields without schema changes
- Performance improvements without behavioral changes
- Documentation that aligns with existing contract
- Test infrastructure expansion

**Historic example:** between `v1.4.0` and `v1.5.0-rc.1` there were
no PATCH releases — Sprint 14 batched all changes into one MINOR.
This is fine. PATCH is available when needed, not mandatory.

### Pre-release (`-rc.N`) — release candidate

Every MAJOR or MINOR bump goes through a **mandatory RC-to-GA hold**
mechanically enforced by `.github/workflows/release.yml` (the
"Assert 24h Codex re-pass window" step). Per ADR-103 the window is
**24 hours**, not a calendar settle period: it bounds the maximum
turnaround for the external Codex re-pass (anti same-LLM-bias per
ADR-095 §gate-#6). The flow:

1. Cut `vMAJOR.MINOR.0-rc.1` tag on `main` HEAD.
2. RC hold begins; the Codex re-pass runs against the RC.
3. If a fix lands during the hold, cut `-rc.2`. The 24h clock
   restarts from the latest RC.
4. At least 24h after the latest RC, with green CI, the Owner cuts
   the GA tag (`vMAJOR.MINOR.0`). `release.yml` rejects a GA tag cut
   < 24h after its RC (creator-date delta < 86400 s), or with no
   prior RC tag at all.

**The 24h hold is mechanical, not a flag.** There is no
`--fail-if-delta-lt-7d`; the gate computes the creator-date delta
between the GA tag and its most-recent `-rc.*` tag. During the
pre-GA phase (`adopter_count=0`) the hold can be waived via an
Owner-signed entry in `.claude/governance/governance-waivers.yaml`.

PATCH releases use the same `-rc` flow and the same mechanical 24h
floor; a security fix per [`SECURITY.md`](SECURITY.md) may ship as
soon as the 24h re-pass window clears.

## What "tag" means

Three artifacts move together at a tag:

1. `VERSION` at repo root reflects the new version number.
2. `npm/package.json` `version` matches (npm publishes on tag via
   `.github/workflows/npm-publish.yml`).
3. `CHANGELOG.md` entry exists under `## [vN.N.N] - YYYY-MM-DD`.

The tag is the single event. If any of these three is out of sync at
tag time, `release.yml` fails.

## Adopter pinning

Adopters pin a specific framework version via:

```bash
# From the adopter project root (replace vX.Y.Z with the desired tag)
bash scripts/upgrade.sh --pin vX.Y.Z
```

Behavior of `--pin`:

- Refuses to upgrade if the adopter has uncommitted changes under
  `.claude/`. Resolve via commit, stash, or `git checkout`.
- Has no MAJOR-boundary guard and no `--allow-major` flag — it
  checks out exactly the tag you pass (pre-2.0, there is no MAJOR
  boundary to cross yet).
- Preserves adopter overrides per `upgrade.sh upgrade_agents_canonical_only`
  (per ADR-052 §Adopter override).
- Backs up the previous install to `.claude.bak/<timestamp>/` for
  manual recovery.

A pin is durable — the adopter's `package.json` (if using npm
distribution) and any project-level lockfile records the pinned
version. Subsequent `bash scripts/upgrade.sh` calls without `--pin`
honor the pinned version.

See [`docs/UPGRADE-PROCEDURE.md`](docs/UPGRADE-PROCEDURE.md) for the
full step-by-step adopter playbook.

## Model ID bumps (Anthropic model family changes)

The framework names specific Claude model IDs in canonical-5 native
agent frontmatter (per ADR-052):

- `claude-opus-4-8` (code-reviewer + security-engineer)
- `claude-sonnet-4-6` (qa-architect + performance-engineer)
- `claude-haiku-4-5-20251001` (devops)

When Anthropic releases the next model family (Opus 5, Sonnet 5,
etc.), the IDs become stale. The bump process is **not silent**:

1. Benchmark the new model against canonical-5 rubrics
   (`.claude/plans/PLAN-020/rubrics/<archetype>.yaml`). Pass-rate
   must be ≥ current baseline.
2. Run `benchmarks/replay.py` on
   `replay-fixtures/plan-019-wave-2a.jsonl`. Spawn-prompt token
   delta must not regress.
3. Author an `ADR-NNN` referencing ADR-052 + benchmark evidence.
4. Update frontmatter `model:` fields in `.claude/agents/<slug>.md`.
5. Bump the audit-log schema (e.g. `v2.9`) if the new model exposes
   additional `usage_metadata` fields.
6. The bump is a MINOR version (additive contract for adopters who
   read `model:` from the audit log).

Adopters who want a different model split override the `model:` field
in their copy of `.claude/agents/<slug>.md`. Framework upgrades
preserve overrides via the diff-detect pattern (`upgrade.sh
upgrade_agents_canonical_only`).

## End-of-life policy

| Window | Status |
|--------|--------|
| Current MINOR (`v1.46.x`) | Full support — features + security + bug fixes |
| Previous MINOR (`v1.45.x`) | Security-only patches for **6 months** after the next MINOR ships |
| Older MINORs (`v1.0–v1.44`) | Best-effort — we describe the upgrade path; no back-ports |

If you are still on a pre-`v1.6.0` install, upgrade incrementally via
`bash scripts/upgrade.sh --pin vX.Y.Z` (consult CHANGELOG.md for the
sequence). Skipping a MINOR is supported across the v1 series but
discouraged because each MINOR adds tests and adopter-facing behavior
worth dogfooding individually. Adopters on `v1.6.x` can upgrade
directly to the current tag.

## Backward compatibility within a MINOR

A `vX.Y.Z` install always understands an audit-log written by an
older `vX.Y.W` install. The reverse is **not** guaranteed —
forward-rolling consumers (audit-query.py, replay/replay-session.py,
ceo-cost.py) are designed to ignore unknown fields per
`SPEC/v1/audit-log.schema.md` §Consumer contract, but a downgraded
install may not know about new event types.

When in doubt, run a fresh `validate-governance.sh` after every
upgrade to catch drift.

## Cadence (best-effort)

| Cadence | Real-world frequency observed Sprints 1-22 |
|---------|---------------------------------------------|
| MINOR releases | ~ every 6 weeks (Sprint cadence) |
| PATCH releases | as needed (rarely batched) |
| RC tags | one per intended MINOR/MAJOR (re-cut on fix during hold) |
| GA tags | one per intended MINOR/MAJOR (after ≥ 24h RC hold per ADR-103) |
| SPEC version (`SPEC/v1/...`) | stable through v1.x; expected v2/ at the v2.0.0 horizon |

This cadence is documented for transparency, not contractual. The
Owner is one person. Sprints can compress or stretch.

## Where the contract really lives

If a doc and the code disagree, **the SPEC files under `SPEC/v1/`
win**. SPEC schemas are normative. CHANGELOG, release notes, and
adopter docs are descriptive — they aim to mirror the SPEC, but the
SPEC is authoritative.

If you find a SPEC file that contradicts behavior, that is a bug:
file via [`SECURITY.md`](SECURITY.md) if it has security implications,
or open a GitHub issue otherwise.

Last reviewed: 2026-06-29 (v1.0.0 genesis).
