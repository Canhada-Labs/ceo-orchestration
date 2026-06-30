# ADR-007: Compliance SPEC v1, SemVer, and the release candidate policy

## Status: ACCEPTED (2026-04-12)

## Context

PLAN-004 Phase 3 consensus findings C1 (v1.0.0 needs RC gate) and C2
(install.sh is the real API, needs SPEC artifact) demand:

1. A published, versioned contract (`SPEC/v1/`) that third parties can
   implement against without reading our source.
2. SemVer applied at the SPEC level (not every commit).
3. A release candidate (`-rc.N`) policy so `v1.0.0` does not ship
   without a smoke hold.
4. `install.sh` flags treated as first-class public API.
5. `upgrade.sh --pin <ref>` to give adopters a stable pin.

VP Engineering (R-ARCH4), Growth (R-GROW1), DevOps (Unseen §2), and
Staff Backend (R-API1, R-API2) all flagged variations of "tagging
v1.0.0 with zero external adopters and no RC is risky".

## Decision Drivers

- **Public contract without leaking implementation.** A third-party
  Gemini CLI / Codex CLI runtime should be able to compile against
  `SPEC/v1/` alone.
- **SemVer discipline.** Rolling commits are fine for main; SPEC
  versions are the stability anchor.
- **Windows compatibility.** Symlinks break without Developer Mode
  (R-ARCH3). SPEC files are content (markdown), not symlinks.
- **Air-gapped adopters.** `--pin` must work with `git checkout`, no
  network dependency beyond the existing clone.
- **Reversibility.** A bad release must be revertable without losing
  work.

## Options Considered

### Option A: SPEC/v1/ mirrors authoritative schemas as content (chosen)

- **Pros:** Windows-safe (no symlinks); SPEC files are tight summaries
  pointing at authoritative source; mirror drift caught by CI; third
  parties can fork just `SPEC/v1/`.
- **Cons:** two places to keep in sync (mitigated: SPEC files are short
  and delegate to authoritative source).

### Option B: SPEC/v1/ as symlinks to .claude/plans/

- **Pros:** no drift possible.
- **Cons:** Windows without Developer Mode fails; adopters who `git
  archive` lose the link; consumers cloning shallow may miss target.

### Option C: Move schemas into SPEC/v1/ canonical, with symlink back

- **Pros:** SPEC is authoritative.
- **Cons:** disruptive rename; same Windows symlink issue reversed;
  every internal consumer needs path updates.

## Decision

**Option A.**

1. `SPEC/v1/` ships 6 markdown files (README + 5 schemas + 1 CLI contract)
   as content, pointing at authoritative sources.
2. `VERSION` file at repo root holds the current SPEC version as a single
   line (`1.0.0-rc.1\n`).
3. `CHANGELOG.md` (Keep-a-Changelog format) at repo root, one section
   per tag.
4. `.github/workflows/release.yml` gates any `v*` tag push with 7 checks:
   VERSION matches tag, CHANGELOG entry, registry validate, governance
   validate, hook tests, script tests, smoke install on scratch dir.

### Release candidate policy

Any MAJOR tag (`vX.0.0`) MUST ship first as `vX.0.0-rc.1` and be held
for **7 days minimum** before promotion to `vX.0.0`. During the hold:

- Owner performs smoke install on fresh macOS + Ubuntu
- CI must pass on every commit to main
- No schema-breaking changes permitted
- At least 1 external dry-run (lighthouse adopter if available)

MINOR and PATCH tags bypass RC.

### `upgrade.sh --pin` contract

When `--pin <ref>` is given:

1. Resolve `<ref>` via `git rev-parse --verify` in source repo (exit 2 if unknown)
2. Refuse if target has uncommitted `.claude/` changes (exit 2)
   unless `CEO_ORCH_FORCE=1`
3. `--dry-run` → print `git diff <ref>...HEAD -- .claude/ scripts/ templates/ SPEC/`
   and exit 0
4. Otherwise: checkout `<ref>` in source; run normal upgrade; restore
   original branch on any exit (bash `trap EXIT`)

### SemVer scope (applied to SPEC, not commits)

See `SPEC/v1/README.md` §"SemVer contract" for the normative rules.
Summary:

- **MAJOR** — remove/rename fields, hook I/O shape change, `install.sh`
  flag removal, min Python version bump, remove action literal
- **MINOR** — add optional field, new hook, new skill, new archetype,
  new flag, new action literal (needs ADR)
- **PATCH** — non-behavioral: docs, tests, shell portability

### Deprecation window

Deprecated items carry `deprecated_in: "X.Y.Z"` + `removed_in: "X.Y.Z"`.
Minimum 90 days between the two. `validate-governance.sh` warns on use.
Installer prints one-line deprecation notices (simulating `Sunset` +
`Deprecation` + `Link` HTTP headers).

## Consequences

### Positive

- Third parties have a single versioned entry point (`SPEC/v1/`) — no
  need to read Python source or chase file locations.
- Release candidate policy prevents "tag v1.0.0 → discover break"
  pattern that hit Sprint 2 install smoke test.
- `upgrade.sh --pin` gives adopters a rollback path without manual git.
- CI release.yml makes the 7 release gates mechanical.

### Negative

- Two markdown locations per schema (SPEC mirror + authoritative source).
  Mitigated by keeping SPEC files short and delegating; CI could add a
  drift check in Sprint 5.
- MAJOR tags now have a 7-day floor — slows "hot fix MAJOR" path. Correct
  trade-off (MAJOR should never be hot).

### Neutral

- `VERSION` + `CHANGELOG.md` are conventional artifacts; low cost to
  maintain.

## Blast Radius

- `SPEC/v1/` (NEW directory, 7 files)
- `VERSION` (NEW file)
- `CHANGELOG.md` (NEW file)
- `scripts/upgrade.sh` — added `--pin`, `--dry-run`, trap
- `.github/workflows/release.yml` (NEW)
- `SPEC/v1/install-cli.md` documents the upgrade.sh --pin contract

**Reversibility:** HIGH — remove SPEC/v1/, CHANGELOG.md, release.yml;
revert upgrade.sh. No consumer depends on SPEC in v1.0.0-rc.1 yet.

## References

- PLAN-004 §3 Phase 3
- PLAN-004/debate/round-1/consensus.md §C1, §C2
- ADR-005 (event stream v2 — `audit-log.schema.md` consumer)
- ADR-006 (registry — `skill-frontmatter.schema.md` consumer)

## Enforcement commit

`6a83a91f4189` (retrofit — PLAN-050 Phase 2 / PLAN-045 F-06-03; this anchors the file's introduction commit, not a runtime-behavior commit. For ADRs whose decision was wired into hooks/scripts in a later commit, amend this line manually.)
