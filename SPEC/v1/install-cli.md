# SPEC v1 — install-cli

> **Spec version:** 1.0.0-rc.1 (updated 2026-04-17 for PLAN-019 Wave 2A)
> **Status:** normative
> **Canonical source:** `scripts/install.sh` (v1.0.0-rc.1 tree)
> **Upstream implementation commit:** Wave 2A (PLAN-019 Phase 2)

The `install.sh` CLI is the framework's **distribution contract**.
Every flag below is part of the public API; removing or changing its
argument shape is a MAJOR bump.

## Commands

### Install

    install.sh <target-repo-path> [options]

Installs the framework into a fresh target repository. **Idempotent**:
re-running will not clobber user-edited files. **Atomic**: if any step
fails, the pre-install state of `$TARGET/.claude/` is restored from a
`mktemp`-protected snapshot. Success clears the snapshot silently.

### Upgrade

    upgrade.sh <target-repo-path> [options]

Updates an existing installed framework. See `--pin` below.

## Flags — stable contract within v1

### Core install-mode flags

| Flag                          | Argument       | Default                 | Purpose |
|-------------------------------|----------------|-------------------------|---------|
| `<target>`                    | path (pos.)    | —                       | Target project directory (must exist OR dry-run) |
| `--target <path>`             | path           | —                       | Alias for positional target (W2A acceptance form) |
| `--link`                      | none           | off                     | Use symlinks instead of file copies |
| `--profile`                   | comma-list     | `core,frontend`         | Which bundles to install (`core`, `frontend`, or domain names) |
| `--stack`                     | name           | `none`                  | Stack-specific hooks (`node`, `none`) — hard-fails rc=3 if EXPLICIT + jq missing |
| `--github-owner`              | handle         | unset → placeholder     | GitHub handle to substitute into CODEOWNERS.template |
| `--with-reference-personas`   | none           | off                     | Also install templates/team-personas-reference.md |
| `--dry-run`                   | none           | off                     | Print what would happen; no files written. Session 75 Codex Finding 5 closure: prior implementation `mkdir -p`'d the target dir despite the "no files modified" promise; now fully synthetic. |
| `--strict-placeholders`       | none           | off                     | Post-install validator. Fails install (exit 4) if any `{{X}}` placeholder remains unsubstituted in installed files. Equivalent to `CEO_INSTALL_STRICT_PH=1`. Recommended for CI / first install of a new adopter. (Session 75 Codex Finding 5 — wired in installer.) |
| `--verify`                    | none           | off                     | Re-checksum installed skill SHAs against the source manifest at `.claude/skill-manifest.sha256`. Advisory when manifest absent (don't break adopters who didn't ship one); fails install (exit 5) on checksum mismatch. Sigstore backend is OUT OF SCOPE per Owner D2 (Session 75 lock); use OS-level package signing if you need cryptographic provenance. |
| `-h`, `--help`                | none           | —                       | Show help text |

### Placeholder-substitution flags (Wave 2A P1-CR-3 / VP-F1)

`install.sh` applies a `sed` pass over freshly-installed template files
for each placeholder supplied via CLI flag or `$CEO_*` env var. Any
placeholder left unrendered is reported at the end with the count + file
list (warning, not error — adopter may want to fill in gradually).

| Flag                       | Placeholder token     | Env var                |
|----------------------------|-----------------------|------------------------|
| `--owner`                  | `{{OWNER_NAME}}`      | `CEO_OWNER`            |
| `--project`                | `{{PROJECT_NAME}}`    | `CEO_PROJECT`          |
| `--project-path`           | `{{PROJECT_PATH}}`    | `CEO_PROJECT_PATH`     |
| `--stack-name`             | `{{STACK}}`           | `CEO_STACK`            |
| `--deploy-command`         | `{{DEPLOY_COMMAND}}`  | `CEO_DEPLOY_COMMAND`   |
| `--deploy-platform`        | `{{DEPLOY_PLATFORM}}` | `CEO_DEPLOY_PLATFORM`  |
| `--deploy-target`          | `{{DEPLOY_TARGET}}`   | `CEO_DEPLOY_TARGET`    |
| `--runtime-notes`          | `{{RUNTIME_NOTES}}`   | `CEO_RUNTIME_NOTES`    |
| `--database`               | `{{DATABASE}}`        | `CEO_DATABASE`         |
| `--n-backend`              | `{{N_BACKEND}}`       | `CEO_N_BACKEND`        |
| `--n-frontend`             | `{{N_FRONTEND}}`      | `CEO_N_FRONTEND`       |
| `--frontend-stack`         | `{{FRONTEND_STACK}}`  | `CEO_FRONTEND_STACK`   |
| `--frontend-path`          | `{{FRONTEND_PATH}}`   | `CEO_FRONTEND_PATH`    |
| `--frontend-repo-path`     | `{{FRONTEND_REPO_PATH}}` | `CEO_FRONTEND_REPO_PATH` |
| `--ui-library`             | `{{UI_LIBRARY}}`      | `CEO_UI_LIBRARY`       |
| `--state-management`       | `{{STATE_MANAGEMENT}}`| `CEO_STATE_MANAGEMENT` |
| `--realtime-transport`     | `{{REALTIME_TRANSPORT}}` | `CEO_REALTIME_TRANSPORT` |
| `--charting-library`       | `{{CHARTING_LIBRARY}}`| `CEO_CHARTING_LIBRARY` |
| `--auth-provider`          | `{{AUTH_PROVIDER}}`   | `CEO_AUTH_PROVIDER`    |
| `--i18n-framework`         | `{{I18N_FRAMEWORK}}`  | `CEO_I18N_FRAMEWORK`   |
| `--test-framework`         | `{{TEST_FRAMEWORK}}`  | `CEO_TEST_FRAMEWORK`   |
| `--test-tool`              | `{{TEST_TOOL}}`       | `CEO_TEST_TOOL`        |
| `--test-count`             | `{{TEST_COUNT}}`      | `CEO_TEST_COUNT`       |
| `--lint-tool`              | `{{LINT_TOOL}}`       | `CEO_LINT_TOOL`        |
| `--ci-tool`                | `{{CI_TOOL}}`         | `CEO_CI_TOOL`          |
| `--app-name`               | `{{APP_NAME}}`        | `CEO_APP_NAME`         |
| `--source-file-count`      | `{{SOURCE_FILE_COUNT}}` | `CEO_SOURCE_FILE_COUNT` |
| `--line-count`             | `{{LINE_COUNT}}`      | `CEO_LINE_COUNT`       |
| `--lines`                  | `{{LINES}}`           | `CEO_LINES`            |
| `--file-count`             | `{{FILE_COUNT}}`      | `CEO_FILE_COUNT`       |
| `--page-count`             | `{{PAGE_COUNT}}`      | `CEO_PAGE_COUNT`       |
| `--component-count`        | `{{COMPONENT_COUNT}}` | `CEO_COMPONENT_COUNT`  |
| `--hook-count`             | `{{HOOK_COUNT}}`      | `CEO_HOOK_COUNT`       |
| `--bundle-size`            | `{{BUNDLE_SIZE}}`     | `CEO_BUNDLE_SIZE`      |
| `--city`                   | `{{CITY}}`            | `CEO_CITY`             |
| `--country`                | `{{COUNTRY}}`         | `CEO_COUNTRY`          |
| `--domain`                 | `{{DOMAIN}}`          | `CEO_DOMAIN`           |
| `--founder-name`           | `{{FOUNDER_NAME}}`    | `CEO_FOUNDER_NAME`     |
| `--legal-id`               | `{{LEGAL_ID}}`        | `CEO_LEGAL_ID`         |
| `--production-url`         | `{{PRODUCTION_URL}}`  | `CEO_PRODUCTION_URL`   |

**Resolution precedence:** CLI flag > env var > deterministic default
(only `PROJECT_NAME` = `basename($TARGET)`, `PROJECT_PATH` = `$TARGET`,
and `STACK` = value of `--stack` have defaults) > left unrendered.

**Substitution files:** skills tree (`SKILL.md`, `SKILL-*.md`,
`team-personas.md`, `pitfalls.yaml`) + CLAUDE.md + docs/ + PROTOCOL.md
copies. Idempotent: re-running `install.sh` against an already-installed
target does NOT re-apply sed (files are EXISTS-skipped, sed only runs on
freshly-installed files).

### Upgrade-mode flags

| Flag       | Argument | Default | Purpose |
|------------|----------|---------|---------|
| `--pin`    | tag ref  | latest  | (upgrade.sh only) Pin to a specific SPEC version tag |
| `--dry-run`| none     | off     | (upgrade.sh only) Print per-file diff-q warning; no changes |
| `--no-diff-warn` | none | off | (upgrade.sh only) Silence the "customization will be replaced" warnings for files that differ from the framework source |
| `--skip <glob>` | glob pattern | — | (upgrade.sh only) Exclude files matching the glob from overwrite; repeat for multiple patterns. Example: `--skip='.claude/scripts/local/*'` |
| `--purge-misinstalled` | none | off | (upgrade.sh only, PLAN-161 U3) Opt-in, hash-gated purge of mis-installed framework-internal files found inside the excluded test/legacy trees. NEVER default-on; see §`upgrade.sh --purge-misinstalled` semantics below |

## `upgrade.sh --purge-misinstalled` semantics (PLAN-161 U3, ADR-155 Amendment)

Earlier upgrade builds could mis-install the framework's own internal
test/legacy trees (`.claude/hooks/tests/`, `.claude/hooks/legacy/`,
`.claude/scripts/tests/`, `.claude/hooks/_lib/tests/`, plus
`.claude/hooks/_lib/test_isolation.py` and `.claude/hooks/_lib/testing.py`)
into adopter targets. `--purge-misinstalled` is the opt-in cleanup for
that residue:

1. **Opt-in, preview by default.** With the flag ABSENT (including under
   `--dry-run`), the upgrade only PREVIEWS: it prints one
   `would PURGE (mis-installed framework-internal): <rel>` line per
   authorized candidate plus a hint naming `--purge-misinstalled`.
   Nothing is deleted. With the flag present AND `--dry-run`, it is
   still preview-only.
2. **Nomination is structural, never manifest-driven.** Candidates come
   ONLY from a hardcoded walk of the excluded trees + the two excluded
   `_lib` files above, under `$TARGET`. The walk is lstat/no-follow:
   symlinks are reported and skipped, never followed; relpaths that fail
   the manifest-grade sanitizer (absolute, `..`, control chars, a
   symlinked path component) are kept with a warning.
3. **Hash authorization, same relpath only.** A candidate is deleted
   only when its SHA-256 equals the CURRENT framework source bytes at
   the SAME relpath, OR equals the target manifest's recorded baseline
   digest for that relpath. A byte-identical copy at a DIFFERENT relpath
   is NEVER authorized. Anything else prints
   `KEPT (excluded-tree file outside provenance rails — not purged)` and
   survives.
4. **Backup-always.** With the flag present and not `--dry-run`, every
   purged file is first copied (`cp -P`) to
   `.claude.bak/<timestamp>/<rel>` and then deleted; now-empty excluded
   directories are removed with `rmdir` (never `rm -rf`). A second run
   finds nothing authorized remaining and purges nothing (no new backup
   content).
5. **Exit behavior.** The scan never changes the upgrade's exit status:
   kept/unauthorized candidates are advisory output, not errors. Infra
   problems (missing hash helpers) degrade to a stderr NOTE and the scan
   is skipped (fail-open per CLAUDE.md §5).

## `upgrade.sh --pin` contract (ADR-007)

When `--pin <ref>` is given:

1. `upgrade.sh` resolves `<ref>` via `git rev-parse --verify` in the
   source framework repo.
2. Refuses to proceed if the target has uncommitted changes under
   `.claude/` (exit 2 with explanation).
3. If `--dry-run`: prints `git diff` between current and target SPEC
   version and exits 0.
4. Otherwise: `git checkout <ref>` in the source; runs normal upgrade
   logic against the pinned version; restores the previous branch at
   end.
5. On any error, attempts to restore the original branch before exiting.

## Exit codes

| Code | Meaning                                                                        |
|------|--------------------------------------------------------------------------------|
| 0    | Success                                                                        |
| 1    | User error (unknown flag, missing target, non-target positional, etc.)         |
| 2    | Precondition failure (uncommitted target changes, invalid pin ref)             |
| 3    | Governance check failure post-install — OR — explicit `--stack` without `jq` — OR — missing system dep (`sed`/`git`) from preflight |

## Environment variables

- `CEO_ORCH_DRY_RUN=1` — equivalent to `--dry-run` (for CI use)
- `CEO_ORCH_FORCE=1` — bypass uncommitted-changes check (explicit opt-in)
- `CEO_*` — see placeholder-substitution table above

## Atomic rollback contract (F-CHAOS-2)

If `$TARGET/.claude/` exists before install:

1. `install.sh` snapshots it to `$(mktemp -d)/.claude` before any
   mutation.
2. Installs into `$TARGET/.claude`.
3. On ANY failure (non-zero exit from any step), the `trap
   cleanup_on_failure EXIT` handler:
   - removes the partial `$TARGET/.claude/`
   - restores the snapshot via `mv`
   - emits `::error::rollback complete — target restored to pre-install state`
4. On success, removes the snapshot.

Dry-run mode (`--dry-run`) never touches `$TARGET` and therefore never
snapshots. Rollback is a no-op in dry-run.

## Preflight (W2A P2-SEC-F)

`install.sh` checks for `sed` and `git` on PATH before any mutation.
Missing either one → exits 3 with a `package-manager` hint. `jq` is
soft-warned at preflight and hard-enforced only when `--stack` is
explicitly supplied (rc=3 if missing and explicit).

## `bash` version guard (DevOps-P1-3)

`install.sh` requires bash >= 3.2 (macOS default shipping with OS).
Non-bash shell or older bash → fail fast with `Run: bash install.sh
<target>` hint. No bash-4-only features are used anywhere in the
script (verified portability contract).

## Deprecation

Deprecation policy: any flag removal MUST ship with a deprecated alias
(one minor version minimum), a stdout/stderr warning when invoked, a
`deprecated_in:` field in this file, a `removed_in:` field, and a 90-day
minimum window before MAJOR removal.

### `--verify-sigstore` — deprecated alias for `--verify`

- `deprecated_in: "1.11.4"`
- `removed_in: "2.0.0"`
- Emits a stderr warning on use; behaves identically to `--verify`.
- The sigstore transparency-log backend is **NOT reintroduced** by this
  alias (Session 75 Owner D2 lock remains in force). The alias exists
  solely to honor SemVer policy after Session 75 removed the flag in a
  patch release without an alias (Codex audit-v3 / DIM-19 closure).
- Adopters with wrappers using `--verify-sigstore` see the warning and
  receive the standard `--verify` re-checksum behavior. To remove the
  warning, switch to `--verify`.

## Release verification

Adopters pinning to a tagged version MAY verify the downloaded tarball
via OFFLINE GPG verification of the release tag (the Owner-signed
ed25519 key is published at `.claude/trust/owner.asc`).

```bash
# 1. Import Owner public key (one-time)
gpg --import .claude/trust/owner.asc

# 2. Verify the tag signature
git tag --verify v1.X.Y
```

For installed-skill integrity checking after extraction, use the
`--verify` install flag (re-checksums skill SHAs against the source
manifest at `.claude/skill-manifest.sha256`). See the flag table in
§Flags above.

**Sigstore backend is OUT OF SCOPE** (Session 75 Owner D2 lock).
The transparency-log verification path was removed because (a) the
`.sigstore` envelope was never wired in `release.yml` (the step is
gated `if: false` STAGED); (b) adding it would import a multi-package
runtime dep tree (sigstore-python + cryptography + pyOpenSSL) that
adopters then carry forever; (c) the GPG-tag path above provides a
strictly stronger trust anchor (Owner key directly, no third-party CA).
Adopters needing cryptographic provenance attestations beyond GPG-tag
verification SHOULD use OS-level package signing (deb / rpm / brew).

## Version history

| SPEC version | Changes |
|--------------|---------|
| 1.0.0-rc.1 (2026-04-17) | Wave 2A landing: 41 placeholder flags + env-var fallbacks + atomic rollback + preflight deps + bash version guard |
| 1.0.0-rc.1 (initial) | Initial formal contract; 7 core flags preserved |
| 1.7.0-rc.2 (2026-04-21) | PLAN-045 F-14 supply-chain: `--verify` / `--verify-sigstore` advisory flags + §Release verification procedure |
| 1.11.3 (2026-04-29 Session 75) | Codex Finding 5 closure: `--verify-sigstore` REMOVED per Owner D2; `--strict-placeholders` documented (was wired but undocumented); `--verify` reframed as installed-skill checksum verification (sigstore out of scope); `--dry-run` no longer creates target dir |
| 1.11.4 (2026-04-29 Session 76) | Codex audit-v3 Finding D / DIM-19 closure: `--verify-sigstore` RESTORED as deprecated alias for `--verify` per SemVer policy. Alias emits stderr warning and delegates to `--verify`; sigstore backend remains out of scope (Owner D2 unchanged). `deprecated_in: 1.11.4` / `removed_in: 2.0.0`. |
| (2026-07-27 PLAN-161) | U3: `--purge-misinstalled` added (opt-in, hash-gated, backup-always purge of mis-installed framework-internal excluded trees; preview default). Upgrade `--dry-run` hardened to write NOTHING in the target (U1); the install.sh framework-internal exclusion set is now honored by upgrade.sh via the shared `_framework_path_excluded` predicate (U2). See ADR-155 Amendment. |
