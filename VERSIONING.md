# Versioning Policy

<!-- last-reviewed: 2026-08-04 v1.3.0 -->

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

**Historic examples (public series — `v1.0.0` is the public genesis;
pre-genesis history is condensed into CHANGELOG `[1.0.0]`):**

| Bump | What changed |
|------|--------------|
| `v1.0.0 → v1.1.0` | PLAN-153/155/156 — two new host harnesses (Codex CLI, Grok Build) = new trust boundaries an adopter must accept; cross-vendor audit council; gated learning loop. |
| `v1.1.0 → v1.2.0` | PLAN-160/161/163/164 — Claude 5 model registry (ADR-181, additive `model:` contract), Codex payload-pin enforcement (ADR-182), pair-rail timeout contract (ADR-110-AMEND-1), new typed audit actions. |
| `v1.2.0 → v1.3.0` | PLAN-162/165 — night-mode posture toggle (new trust boundary, ADR-185); sentinel-unlock provenance inside git worktrees (ADR-119 Invariant 5 — closes in-window self-authored-sentinel escalation); fail-CLOSED matcher deadline (ADR-186); pair-rail 180/210 + `timeout_ms` (ADR-110-AMEND-2). |

### PATCH — bug fixes, additive features within SPEC

Bumped for:

- Hook bug fixes (e.g. the Session 32 redaction-check fix)
- Additive optional fields without schema changes
- Performance improvements without behavioral changes
- Documentation that aligns with existing contract
- Test infrastructure expansion

**Historic example:** `v1.0.0 → v1.0.1` (2026-07-06) — the PLAN-152
hardening sweep: hook fixes and gate hardening with no SPEC or
trust-boundary change. PATCH is available when needed, not mandatory.

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

A pin is **one-shot, not durable**: `--pin` checks out exactly that tag
for that upgrade run, and nothing replays it afterwards — a later
`bash scripts/upgrade.sh` without `--pin` follows the current default
source, not the previously pinned tag. If you want to stay pinned,
pass `--pin vX.Y.Z` explicitly on every upgrade (your npm
`package.json` / lockfile records the version you installed and is a
good place to look it up).

See [`docs/UPGRADE-PROCEDURE.md`](docs/UPGRADE-PROCEDURE.md) for the
full step-by-step adopter playbook.

## Model ID bumps (Anthropic model family changes)

The framework names specific Claude model IDs in canonical-5 native
agent frontmatter (per ADR-052; current IDs set by the ADR-181
Claude 5 refresh, PLAN-163):

- `claude-fable-5` (code-reviewer + security-engineer)
- `claude-sonnet-4-6` (qa-architect + performance-engineer + devops)

When Anthropic releases the next model family, the IDs become stale.
The bump process is **not silent** — it was exercised in full for the
Claude 5 family (PLAN-163 / ADR-181, shipped in v1.2.0):

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
| Current MINOR (`v1.3.x`) | Full support — features + security + bug fixes |
| Previous MINOR (`v1.2.x`) | Security-only patches for **6 months** after the next MINOR ships |
| Older (`v1.0.x`, `v1.1.x`) | Best-effort — we describe the upgrade path; no back-ports |

Upgrade via `bash scripts/upgrade.sh --pin vX.Y.Z` (consult
CHANGELOG.md for the sequence). Skipping a MINOR is supported across
the v1 series but discouraged because each MINOR adds tests and
adopter-facing behavior worth dogfooding individually.

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

| Cadence | Real-world frequency observed in the public series (from 2026-07-01) |
|---------|---------------------------------------------|
| MINOR releases | ~ every 2–3 weeks so far (`v1.0.0` 07-01 → `v1.1.0` 07-13 → `v1.2.0` 07-30) |
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

Last reviewed: 2026-08-04 (v1.3.0 release train — EOL window shifted to
v1.3.x / v1.2.x; historic MINOR table gained the 1.2.0 -> 1.3.0 row naming
the night-mode trust boundary and the sentinel-unlock provenance
requirement).
