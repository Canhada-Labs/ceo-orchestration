#!/usr/bin/env bash
# install.sh — install ceo-orchestration into a target repo
#
# Usage:
#   ./install.sh <target-repo-path> [options]
#
# Options:
#   --link                         Use symlinks instead of copies (for submodule mode)
#   --ceremony <m|u>               Ceremony mode (WS4-ceremony-help):
#                                    maintainer (default, full governance) OR
#                                    user (no-GPG; advisory hooks only; writes .claude/ only)
#   --profile <list>               Comma-separated profiles to install (default: core,frontend)
#                                    Available: core, frontend, <domain-name>
#                                    Example: --profile core,fintech
#                                             --profile core,frontend,fintech
#   --stack <name>                 Stack-specific hooks to merge into settings.json
#                                    Available: node, none
#                                    Example: --stack node  (adds tsc + vitest pre-commit gate)
#                                    Default: none
#   --github-owner <handle>        GitHub handle to substitute into CODEOWNERS.template
#                                    and {{OWNER_HANDLE}} placeholders (e.g. --github-owner alice).
#                                    If omitted, the placeholder is left in place
#                                    for manual editing (with a stderr warning).
#   --with-reference-personas      Also install templates/team-personas-reference.md
#                                    into target (opt-in; 8 fictional personas as
#                                    concrete examples of the archetype-based team).
#                                    Default: off (archetype templates only).
#
#   --dry-run                      Print what WOULD be done (mkdir, cp, sed) without
#                                    touching $TARGET. Exit 0 after preview.
#
#   Placeholder substitution flags (override env + default values):
#     --owner <name>               -> {{OWNER_NAME}}                 (env: CEO_OWNER)
#     --project <name>             -> {{PROJECT_NAME}}               (env: CEO_PROJECT; default: target basename)
#     --project-path <path>        -> {{PROJECT_PATH}}               (env: CEO_PROJECT_PATH; default: $TARGET)
#     --stack-name <str>           -> {{STACK}}                      (env: CEO_STACK; default: --stack value)
#     --deploy-command <cmd>       -> {{DEPLOY_COMMAND}}             (env: CEO_DEPLOY_COMMAND)
#     --deploy-platform <str>      -> {{DEPLOY_PLATFORM}}            (env: CEO_DEPLOY_PLATFORM)
#     --deploy-target <str>        -> {{DEPLOY_TARGET}}              (env: CEO_DEPLOY_TARGET)
#     --runtime-notes <str>        -> {{RUNTIME_NOTES}}              (env: CEO_RUNTIME_NOTES)
#     --database <str>             -> {{DATABASE}}                   (env: CEO_DATABASE)
#     --n-backend <int>            -> {{N_BACKEND}}                  (env: CEO_N_BACKEND)
#     --n-frontend <int>           -> {{N_FRONTEND}}                 (env: CEO_N_FRONTEND)
#     --frontend-stack <str>       -> {{FRONTEND_STACK}}             (env: CEO_FRONTEND_STACK)
#     --frontend-path <str>        -> {{FRONTEND_PATH}}              (env: CEO_FRONTEND_PATH)
#     --frontend-repo-path <str>   -> {{FRONTEND_REPO_PATH}}         (env: CEO_FRONTEND_REPO_PATH)
#     --ui-library <str>           -> {{UI_LIBRARY}}                 (env: CEO_UI_LIBRARY)
#     --state-management <str>     -> {{STATE_MANAGEMENT}}           (env: CEO_STATE_MANAGEMENT)
#     --realtime-transport <str>   -> {{REALTIME_TRANSPORT}}         (env: CEO_REALTIME_TRANSPORT)
#     --charting-library <str>     -> {{CHARTING_LIBRARY}}           (env: CEO_CHARTING_LIBRARY)
#     --auth-provider <str>        -> {{AUTH_PROVIDER}}              (env: CEO_AUTH_PROVIDER)
#     --i18n-framework <str>       -> {{I18N_FRAMEWORK}}             (env: CEO_I18N_FRAMEWORK)
#     --test-framework <str>       -> {{TEST_FRAMEWORK}}             (env: CEO_TEST_FRAMEWORK)
#     --test-tool <str>            -> {{TEST_TOOL}}                  (env: CEO_TEST_TOOL)
#     --test-count <int>           -> {{TEST_COUNT}}                 (env: CEO_TEST_COUNT)
#     --lint-tool <str>            -> {{LINT_TOOL}}                  (env: CEO_LINT_TOOL)
#     --ci-tool <str>              -> {{CI_TOOL}}                    (env: CEO_CI_TOOL)
#     --app-name <str>             -> {{APP_NAME}}                   (env: CEO_APP_NAME)
#     --source-file-count <int>    -> {{SOURCE_FILE_COUNT}}          (env: CEO_SOURCE_FILE_COUNT)
#     --line-count <int>           -> {{LINE_COUNT}}                 (env: CEO_LINE_COUNT)
#     --lines <int>                -> {{LINES}}                      (env: CEO_LINES)
#     --file-count <int>           -> {{FILE_COUNT}}                 (env: CEO_FILE_COUNT)
#     --page-count <int>           -> {{PAGE_COUNT}}                 (env: CEO_PAGE_COUNT)
#     --component-count <int>      -> {{COMPONENT_COUNT}}            (env: CEO_COMPONENT_COUNT)
#     --hook-count <int>           -> {{HOOK_COUNT}}                 (env: CEO_HOOK_COUNT)
#     --bundle-size <str>          -> {{BUNDLE_SIZE}}                (env: CEO_BUNDLE_SIZE)
#
#   -h, --help                     Show this help
#
#   --strict-placeholders          Post-install validator: fail install if any
#                                  `{{X}}` placeholder remains unsubstituted in
#                                  installed files. Recommended for CI / first
#                                  install of a new adopter. Equivalent to
#                                  exporting `CEO_INSTALL_STRICT_PH=1`.
#                                  (Session 75 Codex Finding 5 — wired here.)
#
#   --verify                       Re-checksum installed skill SHAs against the
#                                  source manifest (.claude/skill-manifest.sha256
#                                  if shipped). Basic integrity check. Sigstore
#                                  backend is OUT OF SCOPE per Owner D2 (Session
#                                  75 lock); use OS-level package signing if you
#                                  need cryptographic provenance.
#
#   --verify-sigstore              DEPRECATED alias for --verify (Session 76
#                                  audit-v3 / Codex DIM-19 closure). Emits a
#                                  stderr deprecation warning and behaves
#                                  identically to --verify. The sigstore
#                                  backend is NOT reintroduced (Owner D2).
#                                  deprecated_in 1.11.4 / removed_in 2.0.0.
#
# What it does:
#   1. (NEW — F-CHAOS-2) Snapshots existing $TARGET/.claude/ to a backup
#      tempdir and restores it atomically on any failure. Cleans the
#      backup on success. trap cleanup_on_failure EXIT.
#   2. Always installs:
#      - .claude/team.md, .claude/frontend-team.md (template with placeholders)
#      - .claude/skills/core/ (universal skills)
#      - .claude/skills/frontend/ (if frontend profile selected)
#      - .claude/hooks/, .claude/scripts/, .claude/commands/
#      - .claude/pitfalls-catalog.yaml, .claude/task-chains.yaml, .claude/agent-metrics.md
#   3. If --profile includes a domain name (e.g. fintech):
#      - Installs .claude/skills/domains/<domain>/ with its skills, pitfalls, task-chains,
#        team-personas, commands, scripts.
#   4. Produces .claude/settings.json from templates/settings/settings.base.json
#      (+ settings.stack.<stack>.json if --stack is set), using jq to merge.
#      Hard-fails (rc=3) if --stack is EXPLICITLY supplied and jq is missing.
#   4b. (PLAN-153 Wave E item 3) Injects a coarse credential-read deny
#      baseline into the permissions.deny of a settings.json THIS run
#      created (SSH/AWS/npm/gcloud/kube/docker/git-credentials/netrc/
#      pypirc reads, common .env variants, curl-pipe-bash tripwire).
#      HONEST FRAMING: a coarse harness backstop, deliberately NOT sold
#      as coverage — the pipe-to-shell class is owned by
#      check_bash_safety.py's parse gate. Skipped when settings.json
#      pre-existed (re-runs never re-add removed entries) or when
#      CEO_INSTALL_SKIP_DENY_BASELINE=1. See docs/deny-baseline.md.
#   5. Copies templates/CLAUDE.md to target as CLAUDE.md (only if missing)
#   6. Copies templates/MEMORY.md to target as MEMORY.md (only if missing)
#   6b. (PLAN-135 W1 S5-lite) Copies templates/.mcp.json to target as
#      .mcp.json (only if missing — project-scope MCP registration for
#      the Codex pair-rail; maintainer ceremony only, same EXISTS->SKIP
#      idempotency as CLAUDE.md/MEMORY.md).
#   7. (NEW — P1-CR-3) Runs a sed substitution pass over freshly-installed
#      template files for the placeholders supplied via CLI / env. Any
#      placeholder left unrendered is reported with a stderr warning and
#      listed at the end.
#   8. Lists placeholders the user must fill in.
#   9. (PLAN-153 Wave B item B1) Records the install-state at
#      .claude/.install-state.json (schema ceo.install-state/v1, atomic
#      same-directory tmpfile + rename): the ORIGINAL request (verbatim
#      argv + every parsed flag + the RESOLVED placeholder map) and each
#      operation performed, updated on every run. Target-side, UNSIGNED,
#      advisory — same trust class as the ADR-155 baseline manifest.
#      upgrade.sh (item B2) replays request.profile / request.stack as
#      DEFAULTS when its own flags are omitted.
#
# Idempotent: re-running won't clobber edited files.
#
# Portability: this script targets bash >= 3.2 (macOS default). It uses
#   no bash-4-only features (no associative arrays, no `mapfile`, no
#   `read -d ''`, no `${var^^}`). Tested on Darwin bash-3.2 and Linux
#   bash-5.x.

# ----------------------------------------------------------------------
# DevOps-P1-3: bash version guard (must appear BEFORE `set -euo pipefail`
# so an old shell that doesn't understand newer constructs errors out
# with a friendly message, not a syntax error)
# ----------------------------------------------------------------------
if [ -z "${BASH_VERSINFO:-}" ]; then
  echo "ERROR: install.sh requires bash (detected non-bash shell)" >&2
  echo "       Run:   bash scripts/install.sh <target>" >&2
  exit 1
fi

if [ "${BASH_VERSINFO[0]}" -lt 3 ] || \
   { [ "${BASH_VERSINFO[0]}" -eq 3 ] && [ "${BASH_VERSINFO[1]}" -lt 2 ]; }; then
  echo "ERROR: install.sh requires bash >= 3.2 (detected ${BASH_VERSION})" >&2
  exit 1
fi

# ----------------------------------------------------------------------
# P2-SEC-F (PLAN-019 Phase 3 Wave 3B): required-deps preflight.
# Defense-in-depth: if any of jq, sed, git is missing, fail early with
# a clear error pointing to the package manager. Upstream hardened
# bootstrap (checksum-verified deps) is documented in docs/INSTALL.md
# under "Hardened bootstrap".
# ----------------------------------------------------------------------
_missing_deps=""
for _cmd in sed git; do
  if ! command -v "$_cmd" >/dev/null 2>&1; then
    _missing_deps="${_missing_deps:+$_missing_deps }$_cmd"
  fi
done
# jq is conditionally required (only when --stack is explicit). We warn
# softly here; the hard-fail lives in build_settings() below.
if [ -n "$_missing_deps" ]; then
  echo "ERROR: install.sh requires: $_missing_deps" >&2
  echo "       Install via your package manager (apt/brew/dnf) and retry." >&2
  exit 3
fi
unset _missing_deps _cmd

set -euo pipefail

# Resolve SCRIPT_DIR with a readlink-with-fallback so the script works
# when invoked via a symlink (e.g. from /usr/local/bin/install-ceo).
_resolve_script_path() {
  local src="$1"
  # If GNU/BSD readlink is available, prefer it; fall back to $src as-is.
  if command -v readlink >/dev/null 2>&1; then
    # Try `readlink -f` (GNU) first; on macOS this may not exist, so
    # fall through to plain readlink which follows one symlink level.
    local resolved
    if resolved="$(readlink -f "$src" 2>/dev/null)" && [ -n "$resolved" ]; then
      printf '%s\n' "$resolved"
      return 0
    fi
    # Manual one-level dereference loop for macOS bash 3.2 without -f.
    while [ -L "$src" ]; do
      local link_target
      link_target="$(readlink "$src")"
      case "$link_target" in
        /*) src="$link_target" ;;
        *)  src="$(cd "$(dirname "$src")" && pwd)/$link_target" ;;
      esac
    done
  fi
  printf '%s\n' "$src"
}

SCRIPT_SRC="$(_resolve_script_path "${BASH_SOURCE[0]}")"
SCRIPT_DIR="$( cd "$( dirname "$SCRIPT_SRC" )" && pwd )"
SOURCE_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

# PLAN-138 Wave C (ADR-155) — portable SHA-256 helpers + the single shared
# framework-owned enumeration. Sourced (not executed). Fail-open: if the
# helper is somehow absent (partial checkout), the baseline-manifest step is
# simply skipped later — the install itself never depends on it.
if [ -f "$SCRIPT_DIR/_hash_lib.sh" ]; then
  # shellcheck source=scripts/_hash_lib.sh
  . "$SCRIPT_DIR/_hash_lib.sh"
fi
if [ -f "$SCRIPT_DIR/_framework_manifest_set.sh" ]; then
  # shellcheck source=scripts/_framework_manifest_set.sh
  . "$SCRIPT_DIR/_framework_manifest_set.sh"
fi

# ----------------------------------------------------------------------
# P0-15 (PLAN-045 Session 41 / PLAN-044 F-15R2-01, 2026-04-20;
#        narrative clarified PLAN-063 DIM-01 P1, 2026-04-30):
# supply-chain self-verification.
#
# The LAST line of this script is a `# CEO-INSTALL-SHA256: <hex>` trailer
# populated at release-tag cut by .github/workflows/release.yml. At
# install time the script sha256-hashes its own body (everything except
# the trailer line) and compares. Fail-CLOSED (rc=5) on mismatch,
# missing trailer, or malformed trailer.
#
# Source-tag = GPG-only; the placeholder is INTENTIONAL for source
# installs. Specifically:
#   - The NPM-shim path (npm/install.sh, see scripts/install-npm.sh)
#     anchors version verification on package.json, not on this trailer.
#     Source-tree clones therefore never see a populated trailer and
#     that is by design.
#   - The PLACEHOLDER_RELEASE_FILL trailer applies ONLY to release-tag
#     cuts where .github/workflows/release.yml rewrites the last line
#     with the canonical hex.
#   - Tampering-detection still works for release-tag installs: any
#     post-cut byte change to install.sh trips the SHA mismatch.
#
# Bypass: CEO_INSTALL_SKIP_SELF_SHA=1 (for local dev / tests). Emits a
#         stderr warning so adopters are aware.
# Placeholder: the literal value `PLACEHOLDER_RELEASE_FILL` indicates
#         a source checkout not processed by release.yml; skipped with
#         a stderr warning. Set by the release workflow to the real hex
#         at tag cut. This is the intended behavior for source-tree
#         clones — see notes above.
# ----------------------------------------------------------------------
_self_sha_compute() {
  # SHA256 of everything in the script EXCEPT the last line.
  # Portable across macOS (shasum) and Linux (sha256sum). Reads file
  # twice via awk so it works without GNU-only `head -n -1`.
  local script_path="$1"
  local hasher=""
  if command -v shasum >/dev/null 2>&1; then
    hasher="shasum -a 256"
  elif command -v sha256sum >/dev/null 2>&1; then
    hasher="sha256sum"
  else
    return 1
  fi
  awk 'NR==FNR{n++; next} FNR < n' "$script_path" "$script_path" \
    | eval "$hasher" | awk '{print $1}'
}

_verify_self_sha() {
  local script_path="$1"
  if [ "${CEO_INSTALL_SKIP_SELF_SHA:-0}" = "1" ]; then
    echo "WARN: install.sh self-SHA verification skipped (CEO_INSTALL_SKIP_SELF_SHA=1)" >&2
    return 0
  fi
  local trailer
  trailer="$(tail -n 1 "$script_path" 2>/dev/null || true)"
  case "$trailer" in
    "# CEO-INSTALL-SHA256: "*)
      local expected="${trailer##"# CEO-INSTALL-SHA256: "}"
      if [ "$expected" = "PLACEHOLDER_RELEASE_FILL" ]; then
        echo "WARN: install.sh self-SHA trailer is the unpopulated placeholder." >&2
        echo "      (Source checkout, not a release tarball. Proceeding.)" >&2
        return 0
      fi
      local actual
      if ! actual="$(_self_sha_compute "$script_path")"; then
        echo "ERROR: install.sh self-SHA cannot compute — shasum/sha256sum missing." >&2
        exit 5
      fi
      if [ "$actual" != "$expected" ]; then
        echo "ERROR: install.sh self-SHA MISMATCH (supply-chain tampering suspected)." >&2
        echo "       expected: $expected" >&2
        echo "       actual:   $actual" >&2
        echo "       The install.sh file has been modified since release cut." >&2
        echo "       If this is intentional (local dev), set" >&2
        echo "       CEO_INSTALL_SKIP_SELF_SHA=1 to bypass." >&2
        exit 5
      fi
      ;;
    *)
      echo "ERROR: install.sh missing/malformed CEO-INSTALL-SHA256 trailer." >&2
      echo "       Expected last line: '# CEO-INSTALL-SHA256: <hex>'" >&2
      echo "       Got:                '$trailer'" >&2
      exit 5
      ;;
  esac
}

_verify_self_sha "$SCRIPT_SRC"

# ---- Arg parsing ----

# PLAN-153 Wave B item B1 — capture the ORIGINAL request argv verbatim BEFORE
# the parser consumes it, so the post-install state record persists exactly
# what the Owner asked for. Data only: recorded, never eval-ed or re-expanded.
ORIG_ARGV=( "$@" )

TARGET=""
MODE="copy"
PROFILE="core,frontend"
STACK="none"
STACK_EXPLICIT=0
GITHUB_OWNER=""
WITH_REFERENCE_PERSONAS=0
DRY_RUN=0
STRICT_PLACEHOLDERS=0
# Session 75 Codex Finding 5 closure: post-install integrity check.
CEREMONY="maintainer"  # WS4-ceremony-var
_WS4_PRESNAP=""        # WS4-ceremony-var (set under -u; populated in non-dry-run)
# Re-checksums installed skill SHAs against the source manifest.
VERIFY=0

# Placeholder values — resolved from CLI > env > "" (report-only).
# Default values for values we can derive deterministically are set later
# (after $TARGET is known).
PH_OWNER_NAME="${CEO_OWNER:-}"
PH_PROJECT_NAME="${CEO_PROJECT:-}"
PH_PROJECT_PATH="${CEO_PROJECT_PATH:-}"
PH_STACK="${CEO_STACK:-}"
# PLAN-085 Wave A.5 (F-A-CR-0005): PROTOCOL.md pointer placeholder
# {{PROTOCOL_SOURCE}} substitution. Resolved (CLI > env > $SOURCE_DIR
# default) so freshly installed PROTOCOL.md pointers don't leak the
# literal `{{PROTOCOL_SOURCE}}` marker.
PH_PROTOCOL_SOURCE="${CEO_PROTOCOL_SOURCE:-}"
PH_DEPLOY_COMMAND="${CEO_DEPLOY_COMMAND:-}"
PH_DEPLOY_PLATFORM="${CEO_DEPLOY_PLATFORM:-}"
PH_DEPLOY_TARGET="${CEO_DEPLOY_TARGET:-}"
PH_RUNTIME_NOTES="${CEO_RUNTIME_NOTES:-}"
PH_DATABASE="${CEO_DATABASE:-}"
PH_N_BACKEND="${CEO_N_BACKEND:-}"
PH_N_FRONTEND="${CEO_N_FRONTEND:-}"
PH_FRONTEND_STACK="${CEO_FRONTEND_STACK:-}"
PH_FRONTEND_PATH="${CEO_FRONTEND_PATH:-}"
PH_FRONTEND_REPO_PATH="${CEO_FRONTEND_REPO_PATH:-}"
PH_UI_LIBRARY="${CEO_UI_LIBRARY:-}"
PH_STATE_MANAGEMENT="${CEO_STATE_MANAGEMENT:-}"
PH_REALTIME_TRANSPORT="${CEO_REALTIME_TRANSPORT:-}"
PH_CHARTING_LIBRARY="${CEO_CHARTING_LIBRARY:-}"
PH_AUTH_PROVIDER="${CEO_AUTH_PROVIDER:-}"
PH_I18N_FRAMEWORK="${CEO_I18N_FRAMEWORK:-}"
PH_TEST_FRAMEWORK="${CEO_TEST_FRAMEWORK:-}"
PH_TEST_TOOL="${CEO_TEST_TOOL:-}"
PH_TEST_COUNT="${CEO_TEST_COUNT:-}"
PH_LINT_TOOL="${CEO_LINT_TOOL:-}"
PH_CI_TOOL="${CEO_CI_TOOL:-}"
PH_APP_NAME="${CEO_APP_NAME:-}"
PH_SOURCE_FILE_COUNT="${CEO_SOURCE_FILE_COUNT:-}"
PH_LINE_COUNT="${CEO_LINE_COUNT:-}"
PH_LINES="${CEO_LINES:-}"
PH_FILE_COUNT="${CEO_FILE_COUNT:-}"
PH_PAGE_COUNT="${CEO_PAGE_COUNT:-}"
PH_COMPONENT_COUNT="${CEO_COMPONENT_COUNT:-}"
PH_HOOK_COUNT="${CEO_HOOK_COUNT:-}"
PH_BUNDLE_SIZE="${CEO_BUNDLE_SIZE:-}"
PH_CITY="${CEO_CITY:-}"
PH_COUNTRY="${CEO_COUNTRY:-}"
PH_DOMAIN="${CEO_DOMAIN:-}"
PH_FOUNDER_NAME="${CEO_FOUNDER_NAME:-}"
PH_LEGAL_ID="${CEO_LEGAL_ID:-}"
PH_PRODUCTION_URL="${CEO_PRODUCTION_URL:-}"

print_help() {
  # PLAN-087 B.6: print the full help block (was truncating at line 80
  # which silently dropped the --verify-sigstore deprecation notice and
  # the LGPD/fintech placeholder flags --city/--country/--domain/
  # --founder-name/--legal-id/--production-url). Range bounded by the
  # "Portability:" trailer to stay drift-stable.
  sed -n '3,136p' "$0"
  exit 0
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --link)
      MODE="link"; shift ;;
    --profile)
      PROFILE="${2:-}"; shift 2 ;;
    --ceremony)  # WS4-ceremony-case
      CEREMONY="${2:-}"
      case "$CEREMONY" in
        maintainer|user) ;;
        *)
          echo "ERROR: --ceremony must be 'maintainer' or 'user' (got: $CEREMONY)" >&2
          exit 2
          ;;
      esac
      shift 2 ;;
    --stack)
      STACK="${2:-}"; STACK_EXPLICIT=1; shift 2 ;;
    --github-owner)
      GITHUB_OWNER="${2:-}"; shift 2 ;;
    --with-reference-personas)
      WITH_REFERENCE_PERSONAS=1; shift ;;
    --dry-run)
      DRY_RUN=1; shift ;;
    --strict-placeholders)
      # Session 75 Codex Finding 5: was advertised in docs/READINESS-STATUS.md
      # but the parser rejected it. Now wired — mirrors CEO_INSTALL_STRICT_PH=1
      # post-install validator (fails install if any `{{X}}` placeholder
      # remains unsubstituted in installed files).
      STRICT_PLACEHOLDERS=1; shift ;;
    --verify)
      # Session 75 Codex Finding 5: re-checksum installed skill SHAs vs
      # source manifest. Basic integrity check; sigstore backend OUT OF
      # SCOPE per Owner D2 lock.
      VERIFY=1; shift ;;
    --verify-sigstore)
      # Session 76 audit-v3 Finding D / Codex DIM-19 closure: deprecated
      # alias for `--verify`. Owner D2 (Session 75) ruled the sigstore
      # backend out of scope, but SemVer policy in SPEC/v1/install-cli.md
      # §Deprecation requires alias retention with stdout warning + 90-day
      # window before MAJOR removal. This emits the warning and behaves
      # identically to --verify; the sigstore transparency-log path is
      # NOT reintroduced (per D2). deprecated_in 1.11.4 / removed_in 2.0.0.
      printf 'WARNING: --verify-sigstore is deprecated since v1.11.4 (sigstore backend removed per Session 75 Owner D2 lock); use --verify instead. Will be removed in v2.0.0 — see SPEC/v1/install-cli.md §Deprecation.\n' >&2
      VERIFY=1; shift ;;

    --target)
      # Accept --target <dir> as alias for the positional form, to match
      # the PLAN-019 Wave 2A acceptance invocation.
      if [[ -z "$TARGET" ]]; then
        TARGET="${2:-}"
      else
        echo "ERROR: --target conflicts with positional target: $TARGET" >&2
        exit 1
      fi
      shift 2 ;;

    # Placeholder substitution flags
    --owner)               PH_OWNER_NAME="${2:-}";         shift 2 ;;
    --project)             PH_PROJECT_NAME="${2:-}";       shift 2 ;;
    --project-path)        PH_PROJECT_PATH="${2:-}";       shift 2 ;;
    --stack-name)          PH_STACK="${2:-}";              shift 2 ;;
    --protocol-source)     PH_PROTOCOL_SOURCE="${2:-}";    shift 2 ;;
    --deploy-command)      PH_DEPLOY_COMMAND="${2:-}";     shift 2 ;;
    --deploy-platform)     PH_DEPLOY_PLATFORM="${2:-}";    shift 2 ;;
    --deploy-target)       PH_DEPLOY_TARGET="${2:-}";      shift 2 ;;
    --runtime-notes)       PH_RUNTIME_NOTES="${2:-}";      shift 2 ;;
    --database)            PH_DATABASE="${2:-}";           shift 2 ;;
    --n-backend)           PH_N_BACKEND="${2:-}";          shift 2 ;;
    --n-frontend)          PH_N_FRONTEND="${2:-}";         shift 2 ;;
    --frontend-stack)      PH_FRONTEND_STACK="${2:-}";     shift 2 ;;
    --frontend-path)       PH_FRONTEND_PATH="${2:-}";      shift 2 ;;
    --frontend-repo-path)  PH_FRONTEND_REPO_PATH="${2:-}"; shift 2 ;;
    --ui-library)          PH_UI_LIBRARY="${2:-}";         shift 2 ;;
    --state-management)    PH_STATE_MANAGEMENT="${2:-}";   shift 2 ;;
    --realtime-transport)  PH_REALTIME_TRANSPORT="${2:-}"; shift 2 ;;
    --charting-library)    PH_CHARTING_LIBRARY="${2:-}";   shift 2 ;;
    --auth-provider)       PH_AUTH_PROVIDER="${2:-}";      shift 2 ;;
    --i18n-framework)      PH_I18N_FRAMEWORK="${2:-}";     shift 2 ;;
    --test-framework)      PH_TEST_FRAMEWORK="${2:-}";     shift 2 ;;
    --test-tool)           PH_TEST_TOOL="${2:-}";          shift 2 ;;
    --test-count)          PH_TEST_COUNT="${2:-}";         shift 2 ;;
    --lint-tool)           PH_LINT_TOOL="${2:-}";          shift 2 ;;
    --ci-tool)             PH_CI_TOOL="${2:-}";            shift 2 ;;
    --app-name)            PH_APP_NAME="${2:-}";           shift 2 ;;
    --source-file-count)   PH_SOURCE_FILE_COUNT="${2:-}";  shift 2 ;;
    --line-count)          PH_LINE_COUNT="${2:-}";         shift 2 ;;
    --lines)               PH_LINES="${2:-}";              shift 2 ;;
    --file-count)          PH_FILE_COUNT="${2:-}";         shift 2 ;;
    --page-count)          PH_PAGE_COUNT="${2:-}";         shift 2 ;;
    --component-count)     PH_COMPONENT_COUNT="${2:-}";    shift 2 ;;
    --hook-count)          PH_HOOK_COUNT="${2:-}";         shift 2 ;;
    --bundle-size)         PH_BUNDLE_SIZE="${2:-}";        shift 2 ;;
    --city)                PH_CITY="${2:-}";               shift 2 ;;
    --country)             PH_COUNTRY="${2:-}";            shift 2 ;;
    --domain)              PH_DOMAIN="${2:-}";             shift 2 ;;
    --founder-name)        PH_FOUNDER_NAME="${2:-}";       shift 2 ;;
    --legal-id)            PH_LEGAL_ID="${2:-}";           shift 2 ;;
    --production-url)      PH_PRODUCTION_URL="${2:-}";     shift 2 ;;

    -h|--help)
      print_help ;;
    -*)
      # PLAN-044 audit-v2 C4-P0-01 fix (Wave B): exit 2 (CLI usage error
      # convention per LSB) so adopter wrappers can distinguish "user
      # passed an unknown flag" from "install operation failed mid-flight"
      # (which uses exit 1 elsewhere in the script).
      echo "ERROR: unknown option: $1" >&2
      echo "Run '$0 --help' for usage." >&2
      exit 2 ;;
    *)
      if [[ -z "$TARGET" ]]; then
        TARGET="$1"
      else
        echo "ERROR: unexpected positional arg: $1" >&2
        exit 1
      fi
      shift ;;
  esac
done

# Dry-run mode also tolerates `--target /tmp/foo` as a convenience, even
# though positional is the canonical form — this is what ACCEPTANCE-1
# expects (`install.sh --dry-run --target /tmp/smoke-dry`).
if [[ -z "$TARGET" ]]; then
  # No target — in dry-run mode we fabricate a synthetic path for preview
  # output. Session 75 Codex Finding 5 closure: prior code created the
  # tmp dir on disk despite "no files modified" promise; now we keep
  # the path purely synthetic.
  if [[ "$DRY_RUN" -eq 1 ]]; then
    TARGET="${TMPDIR:-/tmp}/ceo-dry-run-preview"
  else
    echo "Usage: $0 <target-repo-path> [--link] [--profile <list>] [--stack <name>] [--dry-run]" >&2
    echo "Run '$0 --help' for full options." >&2
    exit 1
  fi
fi

if [[ ! -d "$TARGET" ]]; then
  if [[ "$DRY_RUN" -eq 1 ]]; then
    # Preview only — let the user see what WOULD happen if the dir existed.
    # Session 75 Codex Finding 5 closure: do NOT mkdir in dry-run; the
    # promise is "no files modified". Synthesize an absolute-path string
    # via realpath -m (no-existence flag) for the rest of the script.
    echo "(dry-run) NOTE: target directory does not exist: $TARGET" >&2
  else
    echo "ERROR: target directory does not exist: $TARGET" >&2
    exit 1
  fi
fi

# Resolve TARGET to absolute form. Real installs cd into the dir;
# dry-runs use realpath -m (path may not exist on disk yet).
if [[ "$DRY_RUN" -eq 1 && ! -d "$TARGET" ]]; then
  if command -v realpath >/dev/null 2>&1; then
    TARGET="$( realpath -m "$TARGET" 2>/dev/null || realpath "$TARGET" 2>/dev/null || echo "$TARGET" )"
  fi
else
  TARGET="$( cd "$TARGET" && pwd )"
fi

# Fill in deterministic defaults for placeholders now that $TARGET is known.
if [[ -z "$PH_PROJECT_NAME" ]]; then
  PH_PROJECT_NAME="$( basename "$TARGET" )"
fi
if [[ -z "$PH_PROJECT_PATH" ]]; then
  PH_PROJECT_PATH="$TARGET"
fi
if [[ -z "$PH_STACK" ]]; then
  PH_STACK="$STACK"
fi
# PLAN-085 Wave A.5 deterministic default — point PROTOCOL_SOURCE at
# the framework checkout we are installing FROM. Adopters override via
# --protocol-source / CEO_PROTOCOL_SOURCE if their framework lives
# elsewhere post-install. Falling back to $SOURCE_DIR keeps the
# resulting PROTOCOL.md pointer working out-of-the-box (cd into it
# and `git pull` works on day 1).
if [[ -z "$PH_PROTOCOL_SOURCE" ]]; then
  PH_PROTOCOL_SOURCE="$SOURCE_DIR"
fi

# Split PROFILE into array (e.g. "core,fintech" -> [core, fintech])
IFS=',' read -r -a PROFILE_PARTS <<< "$PROFILE"

echo "==> Installing ceo-orchestration"
echo "    Source:       $SOURCE_DIR"
echo "    Target:       $TARGET"
echo "    Mode:         $MODE"
echo "    Profile:      $PROFILE"
echo "    Ceremony:     $CEREMONY"  # WS4-ceremony-banner
echo "    Stack:        $STACK"
echo "    GitHub owner: ${GITHUB_OWNER:-<unset — placeholder kept>}"
if [[ "$DRY_RUN" -eq 1 ]]; then
  echo "    Dry-run:      YES (no files will be written)"
fi
echo ""

# ---------------------------------------------------------------------
# F-CHAOS-2/DevOps-P1-1: atomic install + rollback-on-failure
# ---------------------------------------------------------------------
# Strategy:
#   - If $TARGET/.claude/ already exists, snapshot it to $BACKUP_DIR.
#   - On ANY failure (trap EXIT rc != 0), remove the partial
#     $TARGET/.claude/ and move the backup back into place.
#   - On success, remove the backup in an explicit cleanup step.
# The backup is placed in a unique mktemp tempdir so it cannot collide
# with user data.

BACKUP_DIR=""
INSTALL_SUCCEEDED=0

# WS4-mtime-helper: portable file mtime (epoch seconds) — GNU + BSD stat.
detect_mtime() {
  stat -c %Y "$1" 2>/dev/null || stat -f %m "$1" 2>/dev/null || echo 0
}

cleanup_on_failure() {
  local rc=$?
  # PLAN-153 Wave B item B1 — the ops journal lives OUTSIDE $TARGET; drop it
  # on every exit path (fail-open, never affects rc).
  if [[ -n "${_STATE_OPS_FILE:-}" ]]; then rm -f "$_STATE_OPS_FILE" 2>/dev/null || true; fi
  if [[ "$DRY_RUN" -eq 1 ]]; then
    # Dry-run never touches $TARGET, so never restore.
    exit "$rc"
  fi
  if [[ "$INSTALL_SUCCEEDED" -eq 1 ]]; then
    # Success — clean the backup silently.
    if [[ -n "$BACKUP_DIR" && -d "$BACKUP_DIR" ]]; then
      rm -rf "$BACKUP_DIR" 2>/dev/null || true
    fi
    exit "$rc"
  fi
  if [[ $rc -ne 0 && -n "$BACKUP_DIR" && -d "$BACKUP_DIR/.claude" ]]; then
    echo "::error::install failed (rc=$rc) — restoring $TARGET/.claude from $BACKUP_DIR" >&2
    if [[ -d "$TARGET/.claude" ]]; then
      rm -rf "$TARGET/.claude" 2>/dev/null || true
    fi
    mv "$BACKUP_DIR/.claude" "$TARGET/.claude" 2>/dev/null || true
    rm -rf "$BACKUP_DIR" 2>/dev/null || true
    echo "::error::rollback complete — target restored to pre-install state" >&2
  fi
  exit "$rc"
}
trap cleanup_on_failure EXIT

# ---------------------------------------------------------------------
# PLAN-153 Wave B item B1 — install-state operation journal.
# Each major install operation appends one TAB-separated line
# (op<TAB>detail) to a tempfile OUTSIDE $TARGET; _write_install_state
# folds the journal into .claude/.install-state.json at the end of a
# successful run. Dry-run never creates the journal (the "no files
# modified" promise). Fail-open: journal problems never abort anything.
# ---------------------------------------------------------------------
_STATE_OPS_FILE=""
if [[ "$DRY_RUN" -eq 0 ]]; then
  _STATE_OPS_FILE="$(mktemp "${TMPDIR:-/tmp}/ceo-install-ops.XXXXXX" 2>/dev/null || true)"
fi
_state_record_op() {
  if [[ -n "${_STATE_OPS_FILE:-}" && -f "${_STATE_OPS_FILE:-}" ]]; then
    printf '%s\t%s\n' "$1" "${2:-}" >> "$_STATE_OPS_FILE" 2>/dev/null || true
  fi
  return 0
}

if [[ "$DRY_RUN" -eq 0 ]]; then
  if [[ -d "$TARGET/.claude" ]]; then
    BACKUP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/ceo-install-backup.XXXXXX")"
    cp -R "$TARGET/.claude" "$BACKUP_DIR/.claude"
    echo "    SNAPSHOT: $TARGET/.claude -> $BACKUP_DIR/.claude (for rollback)"
  fi
  mkdir -p "$TARGET/.claude"
  # WS4-presnapshot: record pre-existing non-.claude top-level entries so
  # the post-install guard (user ceremony) can detect any CREATE or MODIFY
  # outside .claude/. Snapshot = "name<TAB>size<TAB>mtime" per entry.
  _WS4_PRESNAP=""
  if [[ "$CEREMONY" == "user" ]]; then
    _WS4_PRESNAP="$(mktemp -t ceo-ws4-presnap-XXXXXX)"
    for _ws4_e in "$TARGET"/* "$TARGET"/.[!.]* "$TARGET"/..?*; do
      [[ -e "$_ws4_e" ]] || continue
      _ws4_b="$(basename "$_ws4_e")"
      case "$_ws4_b" in
        .claude|.git) continue ;;
      esac
      if [[ -f "$_ws4_e" ]]; then
        _ws4_sz="$(wc -c < "$_ws4_e" 2>/dev/null | tr -d ' ')"
        _ws4_mt="$(detect_mtime "$_ws4_e" 2>/dev/null || echo 0)"
        printf '%s\t%s\t%s\n' "$_ws4_b" "$_ws4_sz" "$_ws4_mt" >> "$_WS4_PRESNAP"
      else
        printf '%s\tDIR\t0\n' "$_ws4_b" >> "$_WS4_PRESNAP"
      fi
    done
  fi
else
  echo "    (dry-run) would snapshot $TARGET/.claude if present"
  echo "    (dry-run) would mkdir -p $TARGET/.claude"
fi

# ---- Helpers ----

# PLAN-120-FOLLOWUP WS-D (E10-F4) — refuse to write through a pre-existing
# symlinked INTERMEDIATE path component under $TARGET. The leaf $dst is
# already guarded by the `-L "$dst"` skip below; this closes the gap where
# e.g. $TARGET/.claude -> /etc would make `mkdir -p` + `cp -R` write under
# /etc. Walks every component strictly between $TARGET and dirname($dst)
# and hard-fails (exit 1, picked up by the rollback trap) if any existing
# component is a symlink. Legitimate `--mode link` installs symlink only
# the LEAF, never a parent, so this never trips them.
_assert_no_symlink_parents() {
  local rel_path="$1"
  # Only validate paths we write under $TARGET.
  local parent_rel
  parent_rel="$( dirname "$rel_path" )"
  [[ "$parent_rel" == "." ]] && return 0
  local cur="$TARGET"
  local IFS='/'
  local comp
  for comp in $parent_rel; do
    [[ -z "$comp" || "$comp" == "." ]] && continue
    cur="$cur/$comp"
    if [[ -L "$cur" ]]; then
      echo "::error::refusing install — symlinked path component under target: $cur" >&2
      echo "::error::an intermediate component of '$rel_path' is a symlink; aborting to avoid write-through escape" >&2
      exit 1
    fi
  done
  return 0
}

install_one() {
  local rel_path="$1"
  local src="$SOURCE_DIR/$rel_path"
  local dst="$TARGET/$rel_path"

  if [[ ! -e "$src" ]]; then
    echo "    SKIP (source missing): $rel_path"
    return
  fi

  if [[ "$DRY_RUN" -eq 1 ]]; then
    if [[ -e "$dst" || -L "$dst" ]]; then
      echo "    (dry-run) EXISTS (would skip): $rel_path"
    elif [[ "$MODE" == "link" ]]; then
      echo "    (dry-run) would LINK: $rel_path"
    else
      echo "    (dry-run) would COPY: $rel_path"
    fi
    return
  fi

  _assert_no_symlink_parents "$rel_path"
  mkdir -p "$( dirname "$dst" )"

  if [[ -e "$dst" || -L "$dst" ]]; then
    echo "    EXISTS (skipping): $rel_path"
    return
  fi

  if [[ "$MODE" == "link" ]]; then
    ln -s "$src" "$dst"
    echo "    LINKED: $rel_path"
  else
    if [[ -d "$src" ]]; then
      cp -R "$src" "$dst"
    else
      cp "$src" "$dst"
    fi
    echo "    COPIED: $rel_path"
  fi
}

install_template() {
  local src_rel="$1"
  local dst_rel="$2"
  local src="$SOURCE_DIR/$src_rel"
  local dst="$TARGET/$dst_rel"

  if [[ ! -f "$src" ]]; then
    echo "    SKIP (template missing): $src_rel"
    return
  fi

  if [[ "$DRY_RUN" -eq 1 ]]; then
    if [[ -e "$dst" ]]; then
      echo "    (dry-run) EXISTS (would skip template): $dst_rel"
    else
      echo "    (dry-run) would COPY template: $src_rel -> $dst_rel"
    fi
    return
  fi

  if [[ -e "$dst" ]]; then
    echo "    EXISTS (skipping template): $dst_rel"
    return
  fi

  mkdir -p "$( dirname "$dst" )"
  cp "$src" "$dst"
  echo "    COPIED template: $src_rel -> $dst_rel"
}

has_profile() {
  local p="$1"
  for part in "${PROFILE_PARTS[@]}"; do
    if [[ "$part" == "$p" ]]; then
      return 0
    fi
  done
  return 1
}

# ---- 1. Team rosters (always installed — these are templates with placeholders) ----

_state_record_op "install_team_rosters" ".claude/team.md + .claude/frontend-team.md"
install_one ".claude/team.md"
install_one ".claude/frontend-team.md"

# ---- 2. Core skills (always installed if 'core' in profile) ----

if has_profile "core"; then
  echo ""
  echo "==> Installing core skills"
  _state_record_op "install_skills" "core"
  install_one ".claude/skills/core"
fi

# ---- 3. Frontend skills (installed if 'frontend' in profile) ----

if has_profile "frontend"; then
  echo ""
  echo "==> Installing frontend skills"
  _state_record_op "install_skills" "frontend"
  install_one ".claude/skills/frontend"
fi

# ---- 4. Domain skills (installed per domain name in profile) ----

for part in "${PROFILE_PARTS[@]}"; do
  if [[ "$part" != "core" && "$part" != "frontend" ]]; then
    DOMAIN_SRC="$SOURCE_DIR/.claude/skills/domains/$part"
    if [[ ! -d "$DOMAIN_SRC" ]]; then
      echo ""
      echo "    WARNING: domain '$part' not found at $DOMAIN_SRC — skipping"
      continue
    fi
    echo ""
    echo "==> Installing domain: $part"
    _state_record_op "install_skills" "domain:$part"
    install_one ".claude/skills/domains/$part"
  fi
done

# ---- 5. Protocol enforcement (hooks, scripts, catalogs — always installed) ----
#
# NOTE (PLAN-003 Phase 0 I-4): hooks/ and scripts/ are installed
# SELECTIVELY — only top-level files + hooks/_lib/ are shipped to
# targets. Framework-internal directories excluded:
#
#   .claude/hooks/tests/      — 89 unit tests for the framework itself
#   .claude/hooks/legacy/     — Sprint 1 bash fallbacks (removed in
#                                Sprint 3 Item C once invariants met)
#   .claude/scripts/tests/    — 74 unit tests for audit-query,
#                                run-skill-benchmark, check-tier-boundaries
#
# Rationale: targets don't need our tests or fallbacks — they add ~100
# files of bloat. Target installs should only carry the ACTIVE runtime
# surface: _lib/, _python-hook.sh, active Python hooks, and active
# scripts. New hooks added at the top level (e.g. check_bash_safety.py
# in I-5a) are picked up automatically by the *.py/*.sh glob below.

# PLAN-120-FOLLOWUP WS-D (E4-F1/E4-F2) — install _lib/ SELECTIVELY. A flat
# `install_one .claude/hooks/_lib` does cp -R (or a whole-tree symlink),
# which drags the framework's OWN test harness into the adopter runtime:
# _lib/tests/ (emits real audit events with no session redirect — no
# conftest ships) + test_isolation.py / testing.py (both `import pytest`
# at module top). We iterate the top-level _lib entries and skip exactly
# those three names; everything else (all runtime *.py + the runtime
# subdirs adapters/ estimation/ federation/ mcp/ otel/ tier_policy/ +
# __init__.py) ships. New runtime modules are picked up automatically by
# the glob, matching the install_scripts_selective convention.
install_lib_selective() {
  echo ""
  echo "==> Installing hooks/_lib (runtime only — tests/, test_isolation.py, testing.py excluded)"
  local e base
  for e in "$SOURCE_DIR/.claude/hooks/_lib/"*; do
    [[ -e "$e" ]] || continue
    base="$( basename "$e" )"
    case "$base" in
      tests|test_isolation.py|testing.py|__pycache__) continue ;;
    esac
    install_one ".claude/hooks/_lib/$base"
  done
}

install_hooks_selective() {
  echo ""
  echo "==> Installing hooks (top-level + _lib/, tests/ + legacy/ excluded)"
  _state_record_op "install_hooks" "selective (top-level + _lib)"
  install_lib_selective
  local f base
  for f in "$SOURCE_DIR/.claude/hooks/"*.sh "$SOURCE_DIR/.claude/hooks/"*.py; do
    [[ -f "$f" ]] || continue
    base="$( basename "$f" )"
    install_one ".claude/hooks/$base"
  done
}

# WS4-dispatcher-fn: E6-F5 fix — copy .claude/dispatcher/ (validate-governance.sh REQUIRES it)
install_dispatcher() {
  local src="$SOURCE_DIR/.claude/dispatcher"
  local dst="$TARGET/.claude/dispatcher"
  if [[ ! -d "$src" ]]; then
    echo "    SKIP: .claude/dispatcher/ absent in source" >&2
    return 0
  fi
  echo ""
  echo "==> Installing dispatcher (.claude/dispatcher/ — E6-F5 validate-governance gate)"
  _state_record_op "install_dispatcher" ".claude/dispatcher"
  local f
  if [[ "$DRY_RUN" -eq 1 ]]; then
    for f in routing-matrix.yaml routing-matrix-loader.py disable_predicate_eval.py; do
      [[ -f "$src/$f" ]] && echo "    (dry-run) would COPY: .claude/dispatcher/$f"
    done
    return 0
  fi
  mkdir -p "$dst"
  for f in routing-matrix.yaml routing-matrix-loader.py disable_predicate_eval.py; do
    if [[ -f "$src/$f" ]]; then
      cp "$src/$f" "$dst/$f"
      echo "    COPIED: .claude/dispatcher/$f"
    fi
  done
}

install_scripts_selective() {
  echo ""
  echo "==> Installing scripts (top-level only, tests/ excluded)"
  _state_record_op "install_scripts" "selective"
  # PLAN-085 Wave A.1 (F-A-QA-0001-c7f21a3e): *.yaml extension added to
  # the glob so policy/config YAMLs co-located with scripts/ ship to
  # adopters. Without this, files like smart-loading-cap-table.yaml
  # (pre-Wave-A.2 location) were silently dropped, breaking the
  # first-run-wizard.py crash chain documented in PLAN-084 Wave C.4.
  # Post-A.2 the cap-table lives in .claude/policies/, but keeping
  # *.yaml in the script glob is the right default for any future
  # YAML siblings in .claude/scripts/ (and is the install convention
  # we should have shipped from day 1).
  local f base
  for f in "$SOURCE_DIR/.claude/scripts/"*.sh \
           "$SOURCE_DIR/.claude/scripts/"*.py \
           "$SOURCE_DIR/.claude/scripts/"*.yaml; do
    [[ -f "$f" ]] || continue
    base="$( basename "$f" )"
    install_one ".claude/scripts/$base"
  done
}

# PLAN-085 Wave A.3 — install tier-policy.json + .sigchain from
# templates/.claude/ to adopter .claude/. Files exist in templates/
# (TLA+ ADJ-007 ledger) but were never installed because no install_one
# call referenced them. They are required for canonical-guard tier
# enforcement at adopter sites.
install_tier_policy() {
  echo ""
  echo "==> Installing tier-policy (templates/.claude/tier-policy.json + .sigchain)"
  _state_record_op "install_tier_policy" ".claude/tier-policy.json"
  install_template "templates/.claude/tier-policy.json"          ".claude/tier-policy.json"
  install_template "templates/.claude/tier-policy.json.sigchain" ".claude/tier-policy.json.sigchain"
}

# PLAN-133 E2 — OSV.dev / OSSF malicious-packages supply-chain advisory.
#
# OPT-IN + DEFAULT-OFF + NEVER-HANG. With CEO_OSV_GATE unset this is a no-op
# (we never add latency or network egress to a default install). When an
# adopter / CI opts in (CEO_OSV_GATE=advisory or =block), this scans the
# install commands the framework ships (the squad-install / accelerator npx/
# uvx/pip lines) against OSV.dev for MAL-* advisories via .claude/scripts/
# osv_check.py.
#
# Hard-timeout + offline-safe + fail-OPEN contract:
#   * A hard `timeout` ceiling (CEO_OSV_TIMEOUT_S, default 4s) wraps the call
#     so the gate can NEVER out-live or hang a fast install step.
#   * If neither `timeout`/`gtimeout` nor python3 is present, we SKIP (advisory)
#     and print a breadcrumb — we never block on missing infra.
#   * `advisory` mode never changes the install exit status (rc=0 always).
#   * `block` mode fails the install (rc=4 from this function → caller may halt)
#     ONLY on a concrete MAL advisory hit. A timeout / unknown / malformed
#     response is fail-OPEN by contract and never blocks.
osv_supply_chain_advisory() {
  local mode="${CEO_OSV_GATE:-}"
  case "$mode" in
    advisory|block) ;;
    *) return 0 ;;  # default-OFF: opted out, no-op
  esac

  local checker="$SOURCE_DIR/.claude/scripts/osv_check.py"
  if [[ ! -f "$checker" ]]; then
    echo "    SKIP: osv_check.py absent — supply-chain advisory not run" >&2
    return 0
  fi
  if ! command -v python3 >/dev/null 2>&1; then
    echo "    SKIP: python3 absent — supply-chain advisory not run" >&2
    return 0
  fi

  # Hard-timeout wrapper. Prefer GNU `timeout`, fall back to macOS `gtimeout`,
  # else run bare (osv_check.py has its own per-request hard ceiling, so even
  # without an outer `timeout` the call is bounded).
  local timeout_s="${CEO_OSV_TIMEOUT_S:-4}"
  local outer_budget=$(( ${timeout_s%.*} + 6 ))   # request budget + slack
  local TO=()
  if command -v timeout >/dev/null 2>&1; then
    TO=(timeout -k 2 "${outer_budget}s")
  elif command -v gtimeout >/dev/null 2>&1; then
    TO=(gtimeout -k 2 "${outer_budget}s")
  fi

  echo ""
  echo "==> Supply-chain advisory (OSV.dev / OSSF malicious-packages) — mode=$mode"
  _state_record_op "supply_chain_advisory" "mode=$mode"

  # The framework ships no third-party runtime installs of its own (stdlib
  # only). The surface this gate guards is the set of install commands an
  # adopter/squad may run; we feed those that are statically known. For the
  # framework install itself there is nothing to query, so this is a wired,
  # exercised, never-hang code path with an empty default target list.
  local cmd rc
  local -a OSV_TARGET_COMMANDS=()
  # Adopters / squad-install pass commands via CEO_OSV_COMMANDS (newline-sep).
  if [[ -n "${CEO_OSV_COMMANDS:-}" ]]; then
    while IFS= read -r cmd; do
      [[ -n "$cmd" ]] && OSV_TARGET_COMMANDS+=("$cmd")
    done <<< "${CEO_OSV_COMMANDS}"
  fi

  if [[ ${#OSV_TARGET_COMMANDS[@]} -eq 0 ]]; then
    echo "    (no install commands to scan — framework runtime is stdlib-only)"
    return 0
  fi

  local blocked=0
  for cmd in "${OSV_TARGET_COMMANDS[@]}"; do
    rc=0
    if [[ ${#TO[@]} -gt 0 ]]; then
      CEO_OSV_GATE="$mode" "${TO[@]}" python3 "$checker" --command "$cmd" || rc=$?
    else
      CEO_OSV_GATE="$mode" python3 "$checker" --command "$cmd" || rc=$?
    fi
    # rc=124 → outer `timeout` fired (hung request) → fail-OPEN (advisory-skip).
    if [[ "$rc" -eq 124 ]]; then
      echo "    TIMEOUT: OSV query exceeded ${outer_budget}s — fail-open (advisory-skip)" >&2
    elif [[ "$rc" -eq 3 ]]; then
      # block-mode MAL hit (osv_check returns 3).
      echo "    BLOCKED: malicious-package advisory for an install target" >&2
      blocked=1
    fi
  done

  if [[ "$mode" == "block" && "$blocked" -eq 1 ]]; then
    return 4
  fi
  return 0
}

# PLAN-014 Phase A.8 (ADJ-042) — policy-as-code bundle. Ships the YAML
# policy files + fixtures + drift-manifest. settings.json keeps pointing
# to the legacy .py hooks (ADJ-014 dual-path); adopters opt-in to the
# YAML path by editing settings.json post-install after reviewing the
# shadow-mode guide in docs/.
install_policies_bundle() {
  if [[ ! -d "$SOURCE_DIR/.claude/policies" ]]; then
    return 0
  fi
  echo ""
  echo "==> Installing policy-as-code bundle (PLAN-014 Phase A)"
  _state_record_op "install_policy_bundle" ".claude/policies"
  install_one ".claude/policies"
}

echo ""
echo "==> Installing protocol enforcement"
install_hooks_selective
install_scripts_selective
install_dispatcher  # WS4-dispatcher-call
install_tier_policy
install_policies_bundle
# PLAN-133 E2 — opt-in supply-chain advisory (default-OFF, never-hang).
# In block mode a MAL hit returns rc=4; we surface it but never `exit` here so
# the install of stdlib framework files (already on disk) is not half-rolled-
# back. Adopters running squad/accelerator installs honor the rc themselves.
osv_supply_chain_advisory || {
  _osv_rc=$?
  if [[ "$_osv_rc" -eq 4 ]]; then
    echo "    WARNING: supply-chain advisory BLOCKED a target (CEO_OSV_GATE=block)." >&2
    echo "             Review the breadcrumb above before running that install." >&2
  fi
}
_state_record_op "install_commands_and_catalogs" ".claude/commands + pitfalls-catalog + task-chains + agent-metrics"
install_one ".claude/commands"
install_one ".claude/pitfalls-catalog.yaml"
install_one ".claude/task-chains.yaml"
install_one ".claude/agent-metrics.md"

# ---- 5b. Plan schemas + debate fixture (PLAN-003 Phase 0 I-1) ----

install_plan_schemas() {
  echo ""
  echo "==> Installing plan schemas + debate fixture"
  _state_record_op "install_plan_schemas" ""
  install_one ".claude/plans/README.md"
  install_one ".claude/plans/PLAN-SCHEMA.md"
  install_one ".claude/plans/AUDIT-LOG-SCHEMA.md"
  install_one ".claude/plans/DEBATE-SCHEMA.md"
  install_one ".claude/plans/examples/debate-round-1"
}

install_plan_schemas

# ---- 5c. ADR template (PLAN-003 Phase 0 I-2) ----

install_adr_template() {
  echo ""
  echo "==> Installing ADR template"
  _state_record_op "install_adr_template" ".claude/adr/README.md"
  install_one ".claude/adr/README.md"
}

install_adr_template

# ---- 5c-bis-1 SPEC v1 schemas (PLAN-087 B.1 — closes R-042 cluster) ----

install_spec_v1() {
  if [[ ! -d "$SOURCE_DIR/SPEC/v1" ]]; then
    echo "    SKIP: SPEC/v1/ absent in source"
    return 0
  fi
  echo ""
  echo "==> Installing SPEC v1 schemas (~$(ls "$SOURCE_DIR"/SPEC/v1/*.md 2>/dev/null | wc -l | tr -d ' ') files)"
  _state_record_op "install_spec_v1" "SPEC/v1"
  install_one "SPEC/v1"
}

if [[ "$CEREMONY" != "user" ]]; then install_spec_v1; fi  # WS4-guard-spec

# ---- 5c-bis-2 VERSION manifest (PLAN-087 B.2 — closes R-042 cluster) ----

install_version() {
  if [[ ! -f "$SOURCE_DIR/VERSION" ]]; then
    echo "    SKIP: VERSION file absent in source"
    return 0
  fi
  echo ""
  echo "==> Installing VERSION manifest ($(tr -d '\n' < "$SOURCE_DIR/VERSION"))"
  _state_record_op "install_version_manifest" "VERSION"
  install_one "VERSION"
}

if [[ "$CEREMONY" != "user" ]]; then install_version; fi  # WS4-guard-version

# ---- 5c.bis Reference personas (PLAN-004 Phase 10) ----

install_reference_personas() {
  if [[ "$WITH_REFERENCE_PERSONAS" -eq 1 ]]; then
    echo ""
    echo "==> Installing reference personas (opt-in)"
    _state_record_op "install_reference_personas" "opt-in"
    local src="$SOURCE_DIR/templates/team-personas-reference.md"
    local dst="$TARGET/.claude/team-personas-reference.md"
    if [[ "$DRY_RUN" -eq 1 ]]; then
      if [[ -e "$dst" ]]; then
        echo "    (dry-run) KEEP (would exist): .claude/team-personas-reference.md"
      else
        echo "    (dry-run) would COPY: .claude/team-personas-reference.md"
      fi
      return
    fi
    if [[ -f "$src" ]]; then
      if [[ -e "$dst" ]]; then
        echo "    KEEP (exists): .claude/team-personas-reference.md"
      else
        mkdir -p "$( dirname "$dst" )"
        cp "$src" "$dst"
        echo "    COPIED: .claude/team-personas-reference.md"
      fi
    fi
  fi
}

install_reference_personas

# ---- 5d. docs/ templates (PLAN-003 Phase 0 I-3) ----

install_docs_template() {
  local src_rel="$1"
  local dst_rel="$2"
  local src="$SOURCE_DIR/$src_rel"
  local dst="$TARGET/$dst_rel"

  if [[ ! -f "$src" ]]; then
    echo "    SKIP (template missing): $src_rel"
    return
  fi

  if [[ "$DRY_RUN" -eq 1 ]]; then
    if [[ -e "$dst" ]]; then
      echo "    (dry-run) EXISTS (would skip): $dst_rel"
    else
      echo "    (dry-run) would COPY: $src_rel -> $dst_rel"
    fi
    return
  fi

  if [[ -e "$dst" ]]; then
    echo "    EXISTS (skipping): $dst_rel"
    return
  fi

  mkdir -p "$( dirname "$dst" )"
  cp "$src" "$dst"
  echo "    COPIED: $src_rel -> $dst_rel"
}

install_docs_templates() {
  echo ""
  echo "==> Installing docs/ templates"
  _state_record_op "install_docs_templates" "BRANCH-PROTECTION.md + rotation-log.md"
  install_docs_template "templates/docs/BRANCH-PROTECTION.md" "docs/BRANCH-PROTECTION.md"
  install_docs_template "templates/docs/rotation-log.md" "docs/rotation-log.md"
}

if [[ "$CEREMONY" != "user" ]]; then install_docs_templates; fi  # WS4-guard-docs

# ---- 5e. .github/ templates (PLAN-003 Phase 0 I-3) ----

install_github_templates() {
  echo ""
  echo "==> Installing .github/ templates"
  _state_record_op "install_github_templates" ""

  local codeowners_src="$SOURCE_DIR/templates/.github/CODEOWNERS.template"
  if [[ ! -f "$codeowners_src" ]]; then
    echo "    SKIP (CODEOWNERS.template missing at $codeowners_src)"
  elif [[ -n "$GITHUB_OWNER" ]]; then
    local dst="$TARGET/.github/CODEOWNERS"
    if [[ "$DRY_RUN" -eq 1 ]]; then
      if [[ -e "$dst" ]]; then
        echo "    (dry-run) EXISTS (would skip): .github/CODEOWNERS"
      else
        echo "    (dry-run) would SUBSTITUTE + write: .github/CODEOWNERS (@$GITHUB_OWNER)"
      fi
    elif [[ -e "$dst" ]]; then
      echo "    EXISTS (skipping): .github/CODEOWNERS"
    else
      mkdir -p "$TARGET/.github"
      sed "s/{{OWNER_HANDLE}}/$GITHUB_OWNER/g" "$codeowners_src" > "$dst"
      echo "    SUBSTITUTED: .github/CODEOWNERS (@$GITHUB_OWNER)"
    fi
  else
    install_docs_template \
      "templates/.github/CODEOWNERS.template" \
      ".github/CODEOWNERS.template"
  fi

  install_docs_template \
    "templates/.github/workflows/validate.yml.template" \
    ".github/workflows/validate.yml.template"
  install_docs_template \
    "templates/.github/workflows/benchmarks.yml.template" \
    ".github/workflows/benchmarks.yml.template"
}

if [[ "$CEREMONY" != "user" ]]; then install_github_templates; fi  # WS4-guard-github

# ---- 6. Settings.json from templates (base + optional stack merge) ----

echo ""
echo "==> Building settings.json"
_state_record_op "build_settings" "stack=$STACK"

SETTINGS_DST="$TARGET/.claude/settings.json"
BASE_SRC="$SOURCE_DIR/templates/settings/settings.base.json"
if [[ "$CEREMONY" == "user" ]]; then  # WS4-ceremony-settings
  BASE_SRC="$SOURCE_DIR/templates/settings/settings.user.json"
fi

# PLAN-153 Wave E item 3: remember whether settings.json pre-existed so the
# deny-baseline injection (section 6a below) only ever touches a file THIS
# run created. Re-runs hit build_settings' EXISTS->SKIP path, so entries an
# adopter deliberately removed are never re-added.
SETTINGS_PRE_EXISTING=0
if [[ -e "$SETTINGS_DST" ]]; then
  SETTINGS_PRE_EXISTING=1
fi

build_settings() {
  if [[ "$DRY_RUN" -eq 1 ]]; then
    if [[ -e "$SETTINGS_DST" ]]; then
      echo "    (dry-run) EXISTS (would skip settings.json)"
      return 0
    fi
    if [[ "$STACK" == "none" ]]; then
      echo "    (dry-run) would COPY settings.base.json -> .claude/settings.json (base only)"
      return 0
    fi
    local stack_src="$SOURCE_DIR/templates/settings/settings.stack.$STACK.json"
    if [[ ! -f "$stack_src" ]]; then
      echo "    (dry-run) stack '$STACK' not found at $stack_src — would fall back to base only"
      return 0
    fi
    if command -v jq >/dev/null 2>&1; then
      echo "    (dry-run) would MERGE settings.base.json + settings.stack.$STACK.json -> .claude/settings.json"
    else
      if [[ "$STACK_EXPLICIT" -eq 1 ]]; then
        echo "    (dry-run) FATAL: jq not found and --stack $STACK was explicit — would exit rc=3"
      else
        echo "    (dry-run) jq not found — would warn + base only"
      fi
    fi
    return 0
  fi

  if [[ -e "$SETTINGS_DST" ]]; then
    echo "    EXISTS (skipping settings.json — edit manually if you want to re-build)"
    return 0
  fi
  if [[ ! -f "$BASE_SRC" ]]; then
    echo "    ERROR: base settings template missing at $BASE_SRC" >&2
    return 1
  fi
  if [[ "$STACK" == "none" ]]; then
    cp "$BASE_SRC" "$SETTINGS_DST"
    echo "    COPIED: settings.base.json -> .claude/settings.json (base only, no stack hooks)"
    return 0
  fi

  local stack_src="$SOURCE_DIR/templates/settings/settings.stack.$STACK.json"
  if [[ ! -f "$stack_src" ]]; then
    echo "    WARNING: stack '$STACK' not found at $stack_src — falling back to base only" >&2
    cp "$BASE_SRC" "$SETTINGS_DST"
    return 0
  fi

  if command -v jq >/dev/null 2>&1; then
    # S4a (PLAN-136 W4): the reducer must also pull the stack's TOP-LEVEL
    # sandbox keys, not just its hooks — otherwise `--stack sandbox` ships a
    # settings.json with the hook fragment but NO `.sandbox` /
    # `.autoAllowBashIfSandboxed`, leaving the OS-sandbox template inert.
    # Additive `// (base default)` precedence mirrors the hooks lines: the
    # key only materializes when the stack (or base) actually carries it, so
    # a base-only install (e.g. --stack node) stays byte-identical.
    jq -s '
      .[0] as $base | .[1] as $stack |
      $base
      | .hooks.PreToolUse = (($base.hooks.PreToolUse // []) + ($stack.hooks.PreToolUse // []))
      | .hooks.PostToolUse = (($base.hooks.PostToolUse // []) + ($stack.hooks.PostToolUse // []))
      | if ($stack.sandbox // $base.sandbox) != null
        then .sandbox = ($stack.sandbox // $base.sandbox) else . end
      | if ($stack.autoAllowBashIfSandboxed != null)
        then .autoAllowBashIfSandboxed = $stack.autoAllowBashIfSandboxed
        elif ($base.autoAllowBashIfSandboxed != null)
        then .autoAllowBashIfSandboxed = $base.autoAllowBashIfSandboxed
        else . end
    ' "$BASE_SRC" "$stack_src" > "$SETTINGS_DST"
    echo "    MERGED: settings.base.json + settings.stack.$STACK.json -> .claude/settings.json"
    return 0
  fi

  # jq missing: P2-2 — hard-fail when --stack was explicit; soft-warn otherwise.
  if [[ "$STACK_EXPLICIT" -eq 1 ]]; then
    echo "ERROR: jq is required to merge stack hooks for --stack $STACK, but jq was not found." >&2
    echo "       Install jq (brew install jq / apt-get install jq) and re-run." >&2
    echo "       Aborting install (rc=3) because the --stack flag was explicitly supplied." >&2
    return 3
  else
    echo "    WARNING: jq not found — using base only. Install jq and re-run to merge stack hooks." >&2
    cp "$BASE_SRC" "$SETTINGS_DST"
    return 0
  fi
}

# Capture build_settings rc correctly. `if ! cmd` negates $? to 0 when
# the command failed, so we stash the original rc inside build_settings
# via a dedicated variable. Running under `set -e`, a non-zero return
# from a function would abort the shell mid-execution before we can
# report; guard with `|| build_rc=$?`.
build_rc=0
build_settings || build_rc=$?
if [[ "$build_rc" -ne 0 ]]; then
  exit "$build_rc"
fi

# ---- 6a. PLAN-153 Wave E item 3: coarse credential-read deny baseline ----
#
# Injects a small permissions.deny baseline into the settings.json THIS
# install run just produced.
#
# HONEST FRAMING (never sold as coverage): this is a coarse harness
# backstop. Claude Code Read deny rules cover the built-in file tools and
# the file commands the harness recognizes inside Bash (cat/head/tail/sed),
# but NOT arbitrary subprocesses that open files themselves; Bash pattern
# rules are trivially bypassable by rephrasing. The pipe-to-shell class is
# OWNED by check_bash_safety.py's parse gate — the single
# "Bash(curl * | bash)" entry here is a tripwire, not the rail.
# Scope, residuals, and opt-out: docs/deny-baseline.md.
#
# Exclusion note (ratified fallback): Claude Code evaluates deny before
# allow and "a deny rule can't carry allowlist exceptions", so
# "deny **/.env.* except .env.example" is NOT expressible via deny+allow.
# We therefore deny SPECIFIC sensitive .env variants only; .env.example /
# .env.sample / .env.template stay readable because they are simply not
# listed. Residual: unlisted variants (e.g. .env.secret) pass the backstop.
#
# Idempotency: runs ONLY when this run created settings.json
# (SETTINGS_PRE_EXISTING=0). Re-running install skips settings.json
# entirely, so removed entries are never re-added. The merge itself is
# also order-preserving + deduplicating, so even a forced re-apply cannot
# duplicate entries.
#
# Fail-open on infrastructure (house rule): if neither jq nor python3 is
# available, or the merge fails, WARN with manual instructions and leave
# the just-copied settings.json untouched.
#
# Opt-out: CEO_INSTALL_SKIP_DENY_BASELINE=1 (mirrors CEO_INSTALL_SKIP_SELF_SHA).

DENY_BASELINE_ENTRIES=(
  "Read(~/.ssh/**)"
  "Read(~/.aws/**)"
  "Read(~/.npmrc)"
  "Read(~/.config/gcloud/**)"
  "Read(~/.kube/config)"
  "Read(~/.docker/config.json)"
  "Read(~/.git-credentials)"
  "Read(~/.netrc)"
  "Read(~/.pypirc)"
  "Read(**/.env)"
  "Read(**/.env.local)"
  "Read(**/.env.*.local)"
  "Read(**/.env.development)"
  "Read(**/.env.dev)"
  "Read(**/.env.production)"
  "Read(**/.env.prod)"
  "Read(**/.env.staging)"
  "Read(**/.env.test)"
  "Read(**/.env.ci)"
  "Bash(curl * | bash)"
)

apply_deny_baseline() {
  if [[ "${CEO_INSTALL_SKIP_DENY_BASELINE:-0}" = "1" ]]; then
    echo "    SKIP: deny baseline (CEO_INSTALL_SKIP_DENY_BASELINE=1)"
    return 0
  fi

  if [[ "$DRY_RUN" -eq 1 ]]; then
    if [[ "$SETTINGS_PRE_EXISTING" -eq 1 ]]; then
      echo "    (dry-run) settings.json pre-existed — would NOT touch deny baseline"
    else
      echo "    (dry-run) would MERGE ${#DENY_BASELINE_ENTRIES[@]} deny-baseline entries into .claude/settings.json"
    fi
    return 0
  fi

  if [[ "$SETTINGS_PRE_EXISTING" -eq 1 ]]; then
    echo "    SKIP: settings.json pre-existed this run (add entries manually if wanted — docs/deny-baseline.md)"
    return 0
  fi
  if [[ ! -f "$SETTINGS_DST" ]]; then
    # build_settings decided not to produce one; nothing to inject into.
    return 0
  fi

  # Build a JSON array literal from the entries. All entries are static
  # literals controlled above (no embedded double quotes or backslashes),
  # so direct interpolation is safe.
  local entries_json="[" e first=1
  for e in "${DENY_BASELINE_ENTRIES[@]}"; do
    if [[ "$first" -eq 1 ]]; then first=0; else entries_json+=","; fi
    entries_json+="\"$e\""
  done
  entries_json+="]"

  local tmp="$SETTINGS_DST.deny-baseline.$$"

  if command -v jq >/dev/null 2>&1; then
    # Order-preserving dedup: keep existing deny list as-is, append only
    # baseline entries not already present (jq array subtraction).
    if jq --argjson newdeny "$entries_json" '
         (.permissions.deny // []) as $cur
         | .permissions.deny = ($cur + ($newdeny - $cur))
       ' "$SETTINGS_DST" > "$tmp" 2>/dev/null; then
      mv "$tmp" "$SETTINGS_DST"
      echo "    MERGED: ${#DENY_BASELINE_ENTRIES[@]}-entry coarse deny baseline -> .claude/settings.json (docs/deny-baseline.md)"
      return 0
    fi
    rm -f "$tmp"
    echo "    WARNING: jq merge of the deny baseline failed — settings.json left untouched." >&2
    echo "             Add the permissions.deny entries manually: docs/deny-baseline.md." >&2
    return 0
  fi

  if command -v python3 >/dev/null 2>&1; then
    if python3 - "$SETTINGS_DST" "$entries_json" > "$tmp" <<'PY'
import json
import sys

with open(sys.argv[1], "r", encoding="utf-8") as fh:
    settings = json.load(fh)
new = json.loads(sys.argv[2])
perms = settings.setdefault("permissions", {})
cur = perms.get("deny") or []
perms["deny"] = cur + [e for e in new if e not in cur]
sys.stdout.write(json.dumps(settings, indent=2) + "\n")
PY
    then
      mv "$tmp" "$SETTINGS_DST"
      echo "    MERGED: ${#DENY_BASELINE_ENTRIES[@]}-entry coarse deny baseline -> .claude/settings.json (python3; docs/deny-baseline.md)"
      return 0
    fi
    rm -f "$tmp"
    echo "    WARNING: python3 merge of the deny baseline failed — settings.json left untouched." >&2
    echo "             Add the permissions.deny entries manually: docs/deny-baseline.md." >&2
    return 0
  fi

  echo "    WARNING: neither jq nor python3 found — deny baseline NOT applied." >&2
  echo "             Add the permissions.deny entries manually: docs/deny-baseline.md." >&2
  return 0
}

echo ""
echo "==> Deny baseline (coarse backstop — PLAN-153 Wave E; docs/deny-baseline.md)"
_state_record_op "apply_deny_baseline" "install.sh section 6a"
apply_deny_baseline

# ---- 6b. P2-SEC-H (PLAN-019 Phase 3 Wave 3B): MCP secrets directory ----
#
# The MCP server authenticates clients via HMAC shared secrets stored at
# $TARGET/state/mcp_client_secrets/<client_id>.key. auth.load_secret()
# rejects any file whose perms are not exactly 0o600. If the containing
# directory is world-traversable (0o755 default umask), it's possible
# for a coexisting process to enumerate client_ids. Force 0o700 at
# install time and emit a banner. Additionally, ensure target/.gitignore
# excludes the secrets dir so keys never end up in VCS.
install_mcp_secrets_dir() {
  local secrets_dir="$TARGET/state/mcp_client_secrets"
  local gitignore="$TARGET/.gitignore"

  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo ""
    echo "==> MCP secrets directory (P2-SEC-H)"
    if [[ -d "$secrets_dir" ]]; then
      echo "    (dry-run) EXISTS: state/mcp_client_secrets (would chmod 700)"
    else
      echo "    (dry-run) would CREATE: state/mcp_client_secrets (chmod 700)"
    fi
    echo "    (dry-run) would ENSURE .gitignore excludes state/mcp_client_secrets/"
    return 0
  fi

  echo ""
  echo "==> MCP secrets directory (P2-SEC-H)"
  _state_record_op "ensure_mcp_secrets_dir" "state/mcp_client_secrets 0700"
  mkdir -p "$secrets_dir"
  chmod 700 "$secrets_dir"
  echo "    ENSURED: $secrets_dir (mode 0700)"
  echo ""
  echo "    NOTE: this directory stores HMAC shared secrets for MCP clients."
  echo "          File perms MUST be 0600; auth.load_secret() fail-closes otherwise."
  echo "          DO NOT commit its contents to VCS."

  # .gitignore entry — additive, idempotent.
  local ignore_line="state/mcp_client_secrets/"
  if [[ -f "$gitignore" ]]; then
    if ! grep -Fxq "$ignore_line" "$gitignore" 2>/dev/null; then
      {
        echo ""
        echo "# PLAN-019 P2-SEC-H: MCP shared-secret store (never commit)"
        echo "$ignore_line"
      } >> "$gitignore"
      echo "    APPENDED to .gitignore: $ignore_line"
    else
      echo "    .gitignore already excludes $ignore_line"
    fi
  else
    {
      echo "# PLAN-019 P2-SEC-H: MCP shared-secret store (never commit)"
      echo "$ignore_line"
    } > "$gitignore"
    echo "    CREATED .gitignore with: $ignore_line"
  fi
}

if [[ "$CEREMONY" != "user" ]]; then install_mcp_secrets_dir; fi  # WS4-guard-mcp

# ---- 7. Project-local templates (CLAUDE.md, MEMORY.md, .mcp.json — never overwrite) ----

echo ""
echo "==> Installing project templates"
_state_record_op "install_project_templates" "ceremony=$CEREMONY"
if [[ "$CEREMONY" != "user" ]]; then  # WS4-guard-projtmpl
install_template "templates/CLAUDE.md" "CLAUDE.md"
install_template "templates/MEMORY.md" "MEMORY.md"
# PLAN-135 W1 S5-lite: project-scope MCP registration for the Codex
# pair-rail (the 'codex' server backs the mcp__codex__codex |
# mcp__codex__codex-reply matchers in settings.json). install_template
# is idempotent EXISTS->SKIP — an adopter's own .mcp.json is never
# clobbered. Credentials via ${ENV} expansion only; no secrets on disk.
# Root-level file => stays inside the WS4-guard-projtmpl maintainer
# guard (user ceremony writes .claude/ only).
install_template "templates/.mcp.json" ".mcp.json"
fi  # WS4-guard-projtmpl

# ---- 8. Drop a pointer to PROTOCOL.md (DevOps-P1-4: relative, not absolute) ----

install_protocol_pointer() {
  if [[ -e "$TARGET/PROTOCOL.md" ]]; then
    return 0
  fi

  # Compute a relative path from $TARGET to $SOURCE_DIR when possible.
  # If the framework repo lives outside the target repo (common case),
  # we fall back to {{PROTOCOL_SOURCE}} which the user substitutes
  # manually. Absolute paths are NOT hardcoded — they break portability
  # across dev machines and CI runners.
  #
  # Relative-path heuristic: if $SOURCE_DIR starts with $TARGET, the
  # framework was copied INTO the target — use a relative pointer. In
  # ALL other cases (e.g. adopter clones framework elsewhere), we emit
  # the user-editable {{PROTOCOL_SOURCE}} marker and document next steps.
  local pointer_body
  case "$SOURCE_DIR" in
    "$TARGET"/*)
      local rel="${SOURCE_DIR#$TARGET/}"
      pointer_body="The full CEO orchestration protocol lives at:
./${rel}/PROTOCOL.md

To pull updates:
  ( cd ./${rel} && git pull )
  ./${rel}/scripts/upgrade.sh . --profile $PROFILE --stack $STACK"
      ;;
    *)
      pointer_body="The full CEO orchestration protocol lives at:
{{PROTOCOL_SOURCE}}/PROTOCOL.md

Edit {{PROTOCOL_SOURCE}} to point at your ceo-orchestration checkout
(e.g. ../ceo-orchestration or \$HOME/src/ceo-orchestration).

To pull updates:
  ( cd {{PROTOCOL_SOURCE}} && git pull )
  {{PROTOCOL_SOURCE}}/scripts/upgrade.sh $TARGET --profile $PROFILE --stack $STACK"
      ;;
  esac

  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "    (dry-run) would CREATE: PROTOCOL.md (pointer)"
    return 0
  fi

  cat > "$TARGET/PROTOCOL.md" <<EOF
# Protocol reference

$pointer_body
EOF
  echo "    CREATED: PROTOCOL.md (pointer)"
  _state_record_op "install_protocol_pointer" "PROTOCOL.md"
}

if [[ "$CEREMONY" != "user" ]]; then install_protocol_pointer; fi  # WS4-guard-proto

# ----------------------------------------------------------------------
# P1-CR-3 / VP-F1: placeholder substitution pass
# ----------------------------------------------------------------------
# Iterate over a deterministic list of placeholder files (the ones
# templates/ writes out) and apply `sed -i` substitutions for every
# PH_* variable that is non-empty. Anything left as `{{...}}` after the
# pass is reported with a stderr warning.
#
# We restrict the pass to files install.sh actually placed (the
# templates/* files) to avoid touching user-authored content. If
# CLAUDE.md / MEMORY.md already existed at target, we leave them alone
# (install.sh never overwrites them).

# Portable sed -i for GNU + BSD (macOS): write to .tmp and mv.
portable_sed_inplace() {
  # $1 = sed script, $2 = file
  local script="$1" file="$2"
  local tmp="${file}.ceo-sed-tmp"
  sed "$script" "$file" > "$tmp" && mv "$tmp" "$file"
}

# Build the sed script iteratively. Each non-empty placeholder adds an
# expression. We use `|` as the delimiter so slashes in values (paths)
# don't break. Values with `|` are escaped.
build_sed_script() {
  local script=""
  _add_sub() {
    local key="$1" val="$2"
    if [[ -n "$val" ]]; then
      # Escape | & \ in the replacement
      local esc
      esc="$(printf '%s' "$val" | sed 's/[|&\\]/\\&/g')"
      script="${script}s|{{${key}}}|${esc}|g;"
    fi
  }
  _add_sub "OWNER_NAME"          "$PH_OWNER_NAME"
  _add_sub "OWNER_HANDLE"        "$GITHUB_OWNER"
  _add_sub "PROJECT_NAME"        "$PH_PROJECT_NAME"
  _add_sub "PROJECT_PATH"        "$PH_PROJECT_PATH"
  _add_sub "STACK"               "$PH_STACK"
  _add_sub "PROTOCOL_SOURCE"     "$PH_PROTOCOL_SOURCE"
  _add_sub "DEPLOY_COMMAND"      "$PH_DEPLOY_COMMAND"
  _add_sub "DEPLOY_PLATFORM"     "$PH_DEPLOY_PLATFORM"
  _add_sub "DEPLOY_TARGET"       "$PH_DEPLOY_TARGET"
  _add_sub "RUNTIME_NOTES"       "$PH_RUNTIME_NOTES"
  _add_sub "DATABASE"            "$PH_DATABASE"
  _add_sub "N_BACKEND"           "$PH_N_BACKEND"
  _add_sub "N_FRONTEND"          "$PH_N_FRONTEND"
  _add_sub "FRONTEND_STACK"      "$PH_FRONTEND_STACK"
  _add_sub "FRONTEND_PATH"       "$PH_FRONTEND_PATH"
  _add_sub "FRONTEND_REPO_PATH"  "$PH_FRONTEND_REPO_PATH"
  _add_sub "UI_LIBRARY"          "$PH_UI_LIBRARY"
  _add_sub "STATE_MANAGEMENT"    "$PH_STATE_MANAGEMENT"
  _add_sub "REALTIME_TRANSPORT"  "$PH_REALTIME_TRANSPORT"
  _add_sub "CHARTING_LIBRARY"    "$PH_CHARTING_LIBRARY"
  _add_sub "AUTH_PROVIDER"       "$PH_AUTH_PROVIDER"
  _add_sub "I18N_FRAMEWORK"      "$PH_I18N_FRAMEWORK"
  _add_sub "TEST_FRAMEWORK"      "$PH_TEST_FRAMEWORK"
  _add_sub "TEST_TOOL"           "$PH_TEST_TOOL"
  _add_sub "TEST_COUNT"          "$PH_TEST_COUNT"
  _add_sub "LINT_TOOL"           "$PH_LINT_TOOL"
  _add_sub "CI_TOOL"             "$PH_CI_TOOL"
  _add_sub "APP_NAME"            "$PH_APP_NAME"
  _add_sub "SOURCE_FILE_COUNT"   "$PH_SOURCE_FILE_COUNT"
  _add_sub "LINE_COUNT"          "$PH_LINE_COUNT"
  _add_sub "LINES"               "$PH_LINES"
  _add_sub "FILE_COUNT"          "$PH_FILE_COUNT"
  _add_sub "PAGE_COUNT"          "$PH_PAGE_COUNT"
  _add_sub "COMPONENT_COUNT"     "$PH_COMPONENT_COUNT"
  _add_sub "HOOK_COUNT"          "$PH_HOOK_COUNT"
  _add_sub "BUNDLE_SIZE"         "$PH_BUNDLE_SIZE"
  _add_sub "CITY"                "$PH_CITY"
  _add_sub "COUNTRY"             "$PH_COUNTRY"
  _add_sub "DOMAIN"              "$PH_DOMAIN"
  _add_sub "FOUNDER_NAME"        "${PH_FOUNDER_NAME:-$PH_OWNER_NAME}"
  _add_sub "LEGAL_ID"            "$PH_LEGAL_ID"
  _add_sub "PRODUCTION_URL"      "$PH_PRODUCTION_URL"
  printf '%s' "$script"
}

apply_placeholder_substitutions() {
  local sed_script
  sed_script="$(build_sed_script)"

  if [[ -z "$sed_script" ]]; then
    echo ""
    echo "==> Placeholder substitution: no values supplied (use --owner / --project / env vars)"
    echo "    Template files ship as-is. Edit them manually or re-run install.sh with flags."
    return 0
  fi

  echo ""
  echo "==> Applying placeholder substitutions"
  _state_record_op "apply_placeholder_substitutions" ""

  # Files we are allowed to rewrite — strictly the template-sourced files
  # that install.sh just placed. We check existence first.
  #
  # We intentionally do NOT touch:
  #   - .claude/settings.json          (user-edited hook registry)
  #   - .claude/plans/PLAN-*.md        (user's own plans)
  #   - .claude/adr/ADR-*.md           (user's own ADRs)
  #   - .claude/scripts/*              (executable code; placeholders
  #     inside .py docstrings are instructional, not install-time)
  #   - .claude/hooks/*                (same reason)
  # WS4-explicit-files-partition: maintainer rewrites root + docs/ +
  # .claude/ template files; user ceremony rewrites ONLY .claude/ files so
  # a real adopter repo's own root/docs files are never touched.
  local explicit_files=(
    "$TARGET/.claude/team.md"
    "$TARGET/.claude/frontend-team.md"
    "$TARGET/.claude/agent-metrics.md"
  )
  if [[ "$CEREMONY" != "user" ]]; then
    explicit_files=(
      "$TARGET/CLAUDE.md"
      "$TARGET/MEMORY.md"
      "$TARGET/PROTOCOL.md"
      "$TARGET/docs/BRANCH-PROTECTION.md"
      "$TARGET/docs/rotation-log.md"
      "$TARGET/.claude/team.md"
      "$TARGET/.claude/frontend-team.md"
      "$TARGET/.claude/agent-metrics.md"
    )
  fi

  local f
  for f in "${explicit_files[@]}"; do
    [[ -f "$f" ]] || continue
    if [[ "$DRY_RUN" -eq 1 ]]; then
      echo "    (dry-run) would SUBSTITUTE placeholders in: ${f#$TARGET/}"
      continue
    fi
    portable_sed_inplace "$sed_script" "$f"
    echo "    SUBSTITUTED: ${f#$TARGET/}"
  done

  # Skills/**/SKILL*.md, skills/**/team-personas.md + pitfalls.yaml, and
  # progressive-disclosure references/*.md (PLAN-153 Wave C splits) —
  # these are canonical content that ships {{PROJECT_NAME}}, {{OWNER_NAME}},
  # {{DEPLOY_COMMAND}}, {{FRONTEND_REPO_PATH}}, {{APP_NAME}},
  # {{PRODUCTION_URL}}, etc. as installer-time substitutions (not
  # instructional placeholders). Recurse into the skills tree.
  local skills_root="$TARGET/.claude/skills"
  if [[ -d "$skills_root" ]]; then
    while IFS= read -r f; do
      [[ -n "$f" && -f "$f" ]] || continue
      if [[ "$DRY_RUN" -eq 1 ]]; then
        echo "    (dry-run) would SUBSTITUTE placeholders in: ${f#$TARGET/}"
        continue
      fi
      portable_sed_inplace "$sed_script" "$f"
      echo "    SUBSTITUTED: ${f#$TARGET/}"
    done < <(find "$skills_root" \
      \( -name 'SKILL.md' -o -name 'SKILL-*.md' \
         -o -name 'team-personas.md' -o -name 'pitfalls.yaml' \
         -o -path '*/references/*.md' -o -path '*/reference/*.md' \) \
      -type f 2>/dev/null)
  fi
}

apply_placeholder_substitutions

# ----------------------------------------------------------------------
# Done — mark success so trap doesn't roll back, then print summary
# ----------------------------------------------------------------------


# ----------------------------------------------------------------------
# audit-v2 C4-P0-03: post-install placeholder validator
# ----------------------------------------------------------------------
# Scan installed `.py` and `.md` files for unrendered {{X}} patterns.
# Default: warn + continue. --strict-placeholders (or
# CEO_INSTALL_STRICT_PH=1) → exit 4 if any found.
# ----------------------------------------------------------------------

validate_no_unrendered_placeholders() {
  local strict="${STRICT_PLACEHOLDERS:-${CEO_INSTALL_STRICT_PH:-0}}"
  local found=0
  local report_file
  report_file="$(mktemp -t ceo-install-ph-report-XXXXXX)"

  echo ""
  echo "==> Scanning for unrendered placeholders ({{X}} patterns)"
  _state_record_op "scan_unrendered_placeholders" "strict=$strict"

  local scan_roots=(
    "$TARGET/CLAUDE.md"
    "$TARGET/PROTOCOL.md"
    "$TARGET/MEMORY.md"
    "$TARGET/.claude/team.md"
    "$TARGET/.claude/frontend-team.md"
    "$TARGET/.claude/agent-metrics.md"
    "$TARGET/.claude/skills"
    "$TARGET/.claude/scripts"
    "$TARGET/.claude/hooks"
    "$TARGET/docs"
  )

  local root
  for root in "${scan_roots[@]}"; do
    [[ -e "$root" ]] || continue
    if [[ -d "$root" ]]; then
      while IFS= read -r f; do
        [[ -n "$f" && -f "$f" ]] || continue
        if grep -E -n '\{\{[A-Z_]+\}\}' "$f" >/dev/null 2>&1; then
          grep -E -Hn '\{\{[A-Z_]+\}\}' "$f" >> "$report_file"
        fi
      done < <(find "$root" \( -name '*.md' -o -name '*.py' \) -type f 2>/dev/null)
    elif [[ -f "$root" ]]; then
      if grep -E -n '\{\{[A-Z_]+\}\}' "$root" >/dev/null 2>&1; then
        grep -E -Hn '\{\{[A-Z_]+\}\}' "$root" >> "$report_file"
      fi
    fi
  done

  if [[ -s "$report_file" ]]; then
    found=$(wc -l < "$report_file" | tr -d ' ')
    echo ""
    echo "    UNRENDERED placeholders found ($found occurrences):"
    head -25 "$report_file" | sed 's|^|      |'
    if [[ "$found" -gt 25 ]]; then
      echo "      ... (and $((found - 25)) more — see $report_file)"
    fi
    echo ""
    if [[ "$strict" == "1" ]]; then
      echo "    STRICT mode (--strict-placeholders) — failing install." >&2
      rm -f "$report_file"
      exit 4
    else
      echo "    WARN: install continues. Re-run with --strict-placeholders" >&2
      echo "          to fail-closed on unrendered placeholders." >&2
    fi
  else
    echo "    OK: no unrendered placeholders detected."
  fi

  rm -f "$report_file"
}

validate_no_unrendered_placeholders

# ----------------------------------------------------------------------
# Session 75 Codex Finding 5 closure: --verify post-install integrity.
# Re-checksums installed skill SHAs against the source manifest if one
# is shipped at .claude/skill-manifest.sha256. Advisory-only when the
# manifest is absent (don't break adopters who didn't ship it).
# Sigstore backend is OUT OF SCOPE per Owner D2 lock.
# ----------------------------------------------------------------------
if [[ "${VERIFY:-0}" -eq 1 ]]; then
  echo ""
  echo "==> Verifying installed skill checksums (--verify)"
  _state_record_op "verify_skill_checksums" ""
  manifest="$TARGET/.claude/skill-manifest.sha256"
  if [[ ! -f "$manifest" ]]; then
    echo "    NOTE: no skill-manifest.sha256 present — skipping verify"
    echo "          (advisory only; manifest is shipped by tarball releases)"
  else
    # PLAN-138 Wave C (ADR-155): portable verify via _hash_lib.sh
    # (shasum||sha256sum probe) instead of a bare `shasum -a 256 -c` — Linux
    # hosts may ship only sha256sum. Falls back to the legacy bare form if the
    # helper was not sourced (partial checkout), preserving today's behavior.
    if ( cd "$TARGET" && { if command -v _hash_verify_c >/dev/null 2>&1; then _hash_verify_c "$manifest"; else shasum -a 256 -c "$manifest"; fi; } >/dev/null 2>&1 ); then
      echo "    OK: all installed skills match source manifest"
    else
      echo "    ERROR: skill checksums do not match manifest" >&2
      ( cd "$TARGET" && { if command -v _hash_verify_c >/dev/null 2>&1; then _hash_verify_c "$manifest"; else shasum -a 256 -c "$manifest"; fi; } 2>&1 | grep -v ': OK$' | head -20 ) >&2
      exit 5
    fi
  fi
fi

# WS4-postinstall-guard: user ceremony must not CREATE or MODIFY anything
# outside $TARGET/.claude/. Pre-existing adopter files (package.json,
# README.md, the adopter's own CLAUDE.md, docs/, ...) must be byte-stable.
if [[ "$CEREMONY" == "user" ]]; then
  _ws4_bad=""
  for _ws4_e in "$TARGET"/* "$TARGET"/.[!.]* "$TARGET"/..?*; do
    [[ -e "$_ws4_e" ]] || continue
    _ws4_b="$(basename "$_ws4_e")"
    case "$_ws4_b" in
      .claude|.git) continue ;;
    esac
    # Look up this entry in the pre-snapshot (match on leading "name<TAB>").
    _ws4_pre=""
    if [[ -f "$_WS4_PRESNAP" ]]; then
      _ws4_pre="$(grep -F -- "$(printf '%s\t' "$_ws4_b")" "$_WS4_PRESNAP" 2>/dev/null | head -1 || true)"
    fi
    if [[ -z "$_ws4_pre" ]]; then
      # No pre-snapshot row => this entry was CREATED by install.
      _ws4_bad="$_ws4_bad created:$_ws4_b"
      continue
    fi
    # Pre-existed. If it is a file, compare size + mtime.
    if [[ -f "$_ws4_e" ]]; then
      _ws4_now_sz="$(wc -c < "$_ws4_e" 2>/dev/null | tr -d ' ')"
      _ws4_now_mt="$(detect_mtime "$_ws4_e" 2>/dev/null || echo 0)"
      _ws4_pre_sz="$(printf '%s' "$_ws4_pre" | cut -f2)"
      _ws4_pre_mt="$(printf '%s' "$_ws4_pre" | cut -f3)"
      if [[ "$_ws4_now_sz" != "$_ws4_pre_sz" || "$_ws4_now_mt" != "$_ws4_pre_mt" ]]; then
        _ws4_bad="$_ws4_bad modified:$_ws4_b"
      fi
    fi
  done
  if [[ -n "$_ws4_bad" ]]; then
    echo "ERROR: --ceremony user touched paths outside .claude/:$_ws4_bad" >&2
    rm -f "$_WS4_PRESNAP"
    exit 3
  fi
  rm -f "$_WS4_PRESNAP"
fi

# ----------------------------------------------------------------------
# PLAN-138 Wave C (ADR-155) — write the baseline SHA-256 manifest.
#
# Records, per framework-owned file, a baseline digest so a later upgrade can
# tell "the framework changed this" apart from "the adopter changed this" and
# PRESERVE/REFUSE customizations instead of clobbering them (incl. the root
# PROTOCOL.md — the verified S238 driver). The enumeration is the SINGLE shared
# set from _framework_manifest_set.sh, so the manifest writer (here) and the
# upgrade classifier walk an identical list.
#
# Manifest grammar (two record kinds):
#   <64hex>  <relpath>            — content hash of a copied file
#   LINK  <relpath>  <target>     — a --mode link symlink (content == source,
#                                   so a content hash is meaningless; the
#                                   upgrade classifier short-circuits LINK)
#
# Written to $TARGET/.claude/.install-manifest.sha256 (distinct from the
# release skill-manifest.sha256). EXCLUDES the manifest itself + .claude.bak/.
# Fail-open: any missing helper / unreadable file is skipped with a NOTE; the
# install never fails because the manifest could not be fully written.
# ----------------------------------------------------------------------
write_install_manifest() {
  # Guarded by the caller for DRY_RUN; defensive re-check here.
  [[ "${DRY_RUN:-0}" -eq 0 ]] || return 0

  if ! command -v _write_baseline_manifest >/dev/null 2>&1; then
    echo "    NOTE: baseline manifest skipped — generator helper not sourced" >&2
    return 0
  fi

  local manifest="$TARGET/.claude/.install-manifest.sha256"
  echo ""
  echo "==> Writing install baseline manifest (.claude/.install-manifest.sha256)"
  _state_record_op "write_install_manifest" ".claude/.install-manifest.sha256"

  # Profile-aware enumeration rooted at the installed target; the SINGLE shared
  # generator in _framework_manifest_set.sh does the walk + hashing + LINK
  # records (the SAME generator upgrade.sh calls after a successful upgrade).
  export FMS_ROOT="$TARGET"
  export FMS_PROFILE_PARTS="${PROFILE_PARTS[*]}"
  export FMS_MODE="$MODE"
  _write_baseline_manifest "$manifest"
  unset FMS_ROOT FMS_PROFILE_PARTS FMS_MODE
  return 0
}


# ----------------------------------------------------------------------
# PLAN-153 Wave B item B1 — persist the install-state.
# ----------------------------------------------------------------------
# Writes $TARGET/.claude/.install-state.json (next to the ADR-155 baseline
# manifest): the ORIGINAL request — verbatim argv + every parsed flag + the
# RESOLVED placeholder map (CLI > env > deterministic default; empty values
# omitted) — plus the operation journal for THIS run.
#
#   * Atomic: python writes a same-directory tempfile, then os.replace().
#   * Updated on every run: first_recorded_at + run_count + a bounded
#     history (last 20 runs) survive re-installs; request/operations
#     reflect the LATEST run.
#   * Schema-versioned: schema ceo.install-state/v1, schema_version 1.
#   * Consumed by upgrade.sh (PLAN-153 B2): request.profile/request.stack
#     become upgrade DEFAULTS when its own flags are omitted. A missing or
#     invalid state file degrades upgrade.sh to the ADR-155 drift-classifier
#     path — never an error, never a no-op (debate C back-compat must-fix).
#   * TRUST: target-side, UNSIGNED, advisory — the same trust class as the
#     ADR-155 baseline manifest (whoever can write the target tree can
#     rewrite it). upgrade.sh charset-validates every replayed value and
#     falls back on anything suspect; values are data, never eval-ed.
#   * Fail-open: no python3 / write error => stderr NOTE, install still
#     succeeds. Dry-run never writes (the "no files modified" promise).
#   * NOT covered by the baseline-manifest enumeration (like the manifest
#     dotfile itself), so the upgrade classifier never touches it.
_write_install_state() {
  [[ "${DRY_RUN:-0}" -eq 0 ]] || return 0
  if ! command -v python3 >/dev/null 2>&1; then
    echo "    NOTE: install-state skipped (python3 not found) — upgrade.sh will use the ADR-155 fallback path" >&2
    return 0
  fi
  local state_file="$TARGET/.claude/.install-state.json"
  local fw_version=""
  if [[ -f "$SOURCE_DIR/VERSION" ]]; then
    fw_version="$(tr -d '[:space:]' < "$SOURCE_DIR/VERSION" 2>/dev/null || true)"
  fi

  echo ""
  echo "==> Writing install-state (.claude/.install-state.json — PLAN-153 Wave B)"

  # Flat key/value pairs, argv-passed (PLAN-106 G.2.b house pattern: never
  # source-string interpolation; python3 -I + PYTHONNOUSERSITE=1). Keys with
  # a "ph." prefix land in request.placeholders; empty ph values are omitted.
  local pairs=(
    "target" "$TARGET"
    "mode" "$MODE"
    "profile" "$PROFILE"
    "stack" "$STACK"
    "stack_explicit" "$STACK_EXPLICIT"
    "ceremony" "$CEREMONY"
    "github_owner" "$GITHUB_OWNER"
    "with_reference_personas" "$WITH_REFERENCE_PERSONAS"
    "strict_placeholders" "$STRICT_PLACEHOLDERS"
    "verify" "$VERIFY"
    "ph.OWNER_NAME" "$PH_OWNER_NAME"
    "ph.PROJECT_NAME" "$PH_PROJECT_NAME"
    "ph.PROJECT_PATH" "$PH_PROJECT_PATH"
    "ph.STACK" "$PH_STACK"
    "ph.PROTOCOL_SOURCE" "$PH_PROTOCOL_SOURCE"
    "ph.DEPLOY_COMMAND" "$PH_DEPLOY_COMMAND"
    "ph.DEPLOY_PLATFORM" "$PH_DEPLOY_PLATFORM"
    "ph.DEPLOY_TARGET" "$PH_DEPLOY_TARGET"
    "ph.RUNTIME_NOTES" "$PH_RUNTIME_NOTES"
    "ph.DATABASE" "$PH_DATABASE"
    "ph.N_BACKEND" "$PH_N_BACKEND"
    "ph.N_FRONTEND" "$PH_N_FRONTEND"
    "ph.FRONTEND_STACK" "$PH_FRONTEND_STACK"
    "ph.FRONTEND_PATH" "$PH_FRONTEND_PATH"
    "ph.FRONTEND_REPO_PATH" "$PH_FRONTEND_REPO_PATH"
    "ph.UI_LIBRARY" "$PH_UI_LIBRARY"
    "ph.STATE_MANAGEMENT" "$PH_STATE_MANAGEMENT"
    "ph.REALTIME_TRANSPORT" "$PH_REALTIME_TRANSPORT"
    "ph.CHARTING_LIBRARY" "$PH_CHARTING_LIBRARY"
    "ph.AUTH_PROVIDER" "$PH_AUTH_PROVIDER"
    "ph.I18N_FRAMEWORK" "$PH_I18N_FRAMEWORK"
    "ph.TEST_FRAMEWORK" "$PH_TEST_FRAMEWORK"
    "ph.TEST_TOOL" "$PH_TEST_TOOL"
    "ph.TEST_COUNT" "$PH_TEST_COUNT"
    "ph.LINT_TOOL" "$PH_LINT_TOOL"
    "ph.CI_TOOL" "$PH_CI_TOOL"
    "ph.APP_NAME" "$PH_APP_NAME"
    "ph.SOURCE_FILE_COUNT" "$PH_SOURCE_FILE_COUNT"
    "ph.LINE_COUNT" "$PH_LINE_COUNT"
    "ph.LINES" "$PH_LINES"
    "ph.FILE_COUNT" "$PH_FILE_COUNT"
    "ph.PAGE_COUNT" "$PH_PAGE_COUNT"
    "ph.COMPONENT_COUNT" "$PH_COMPONENT_COUNT"
    "ph.HOOK_COUNT" "$PH_HOOK_COUNT"
    "ph.BUNDLE_SIZE" "$PH_BUNDLE_SIZE"
    "ph.CITY" "$PH_CITY"
    "ph.COUNTRY" "$PH_COUNTRY"
    "ph.DOMAIN" "$PH_DOMAIN"
    "ph.FOUNDER_NAME" "$PH_FOUNDER_NAME"
    "ph.LEGAL_ID" "$PH_LEGAL_ID"
    "ph.PRODUCTION_URL" "$PH_PRODUCTION_URL"
  )

  if ! PYTHONNOUSERSITE=1 python3 -I -c '
import json, os, sys, tempfile, time
args = sys.argv[1:]
state_path, ops_path, fw_version = args[0], args[1], args[2]
n = int(args[3]); kv = args[4:4 + n]; orig_argv = list(args[4 + n:])
vals = {}; ph = {}
i = 0
while i + 1 < len(kv):
    k, v = kv[i], kv[i + 1]
    if k.startswith("ph."):
        if v != "":
            ph[k[3:]] = v
    else:
        vals[k] = v
    i += 2
ops = []
if ops_path and os.path.isfile(ops_path):
    try:
        with open(ops_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.rstrip("\n")
                if not line:
                    continue
                parts = line.split("\t", 1)
                ops.append({"op": parts[0], "detail": parts[1] if len(parts) > 1 else ""})
    except OSError:
        pass
now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
prev = None
try:
    with open(state_path, "r", encoding="utf-8") as f:
        prev = json.load(f)
    if not isinstance(prev, dict):
        prev = None
except (OSError, ValueError):
    prev = None
first, run_count, history = now, 1, []
if prev is not None:
    v = prev.get("first_recorded_at")
    if isinstance(v, str) and v:
        first = v
    rc = prev.get("run_count")
    if isinstance(rc, int) and rc > 0:
        run_count = rc + 1
    h = prev.get("history")
    if isinstance(h, list):
        history = [e for e in h if isinstance(e, dict)][-19:]
    pr = prev.get("request"); pt = prev.get("tool"); pw = prev.get("written_at")
    history.append({
        "at": pw if isinstance(pw, str) else "",
        "tool": (pt.get("name", "") if isinstance(pt, dict) else ""),
        "profile": (pr.get("profile", "") if isinstance(pr, dict) else ""),
        "stack": (pr.get("stack", "") if isinstance(pr, dict) else ""),
    })
    history = history[-20:]
    # Placeholder map is a UNION across runs: install.sh is EXISTS-SKIP
    # idempotent and never un-substitutes, so a value recorded by an earlier
    # run remains in effect on disk even when a later run omits the flag.
    # New non-empty values override recorded ones.
    if isinstance(pr, dict):
        oph = pr.get("placeholders")
        if isinstance(oph, dict):
            merged = {}
            for k in oph:
                if isinstance(k, str) and isinstance(oph[k], str):
                    merged[k] = oph[k]
            merged.update(ph)
            ph = merged
req = {
    "argv": orig_argv,
    "target": vals.get("target", ""),
    "mode": vals.get("mode", ""),
    "profile": vals.get("profile", ""),
    "stack": vals.get("stack", ""),
    "stack_explicit": vals.get("stack_explicit", "0") == "1",
    "ceremony": vals.get("ceremony", ""),
    "github_owner": vals.get("github_owner", ""),
    "with_reference_personas": vals.get("with_reference_personas", "0") == "1",
    "strict_placeholders": vals.get("strict_placeholders", "0") == "1",
    "verify": vals.get("verify", "0") == "1",
    "placeholders": ph,
}
state = {
    "schema": "ceo.install-state/v1",
    "schema_version": 1,
    "written_at": now,
    "first_recorded_at": first,
    "run_count": run_count,
    "tool": {"name": "install.sh", "framework_version": fw_version},
    "request": req,
    "operations": ops,
    "result": {"install_succeeded": True,
               "baseline_manifest": ".claude/.install-manifest.sha256"},
    "history": history,
    "_comment": "Target-side, UNSIGNED, advisory record (same trust class as the ADR-155 baseline manifest). upgrade.sh replays request.profile/request.stack as DEFAULTS only; explicit flags always win. Not a trust anchor.",
}
d = os.path.dirname(state_path) or "."
if not os.path.isdir(d):
    sys.exit(3)
fd, tmp = tempfile.mkstemp(prefix=".install-state.", suffix=".tmp", dir=d)
try:
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)
        f.write("\n")
    os.replace(tmp, state_path)
except BaseException:
    try:
        os.unlink(tmp)
    except OSError:
        pass
    raise
' "$state_file" "${_STATE_OPS_FILE:-}" "$fw_version" "${#pairs[@]}" "${pairs[@]}" \
    ${ORIG_ARGV[@]+"${ORIG_ARGV[@]}"} 2>/dev/null; then
    echo "    NOTE: install-state write failed — upgrade.sh will use the ADR-155 fallback path (fail-open)" >&2
    return 0
  fi
  echo "    WROTE: .claude/.install-state.json (schema ceo.install-state/v1, atomic)"
  return 0
}

if [[ "$DRY_RUN" -eq 0 ]]; then
  write_install_manifest
  _write_install_state
fi
INSTALL_SUCCEEDED=1

# ----------------------------------------------------------------------
# PLAN-097 Wave C.2 — LARGE-profile RAG sidecar install prompt
# ----------------------------------------------------------------------
# After core install succeeds, detect target repo size class. If LARGE
# (>= 200k LoC) AND interactive AND C2 sidecar not already installed,
# offer the optional Tier-C RAG sidecar install.
#
# Skipped silently when:
#   - not a TTY (non-interactive)
#   - CEO_RAG_INSTALL_PROMPT=0 explicitly set
#   - $TARGET/.claude/rag/.install.lock already present (already installed)

if [[ "${DRY_RUN:-0}" -ne 1 ]] && [[ -t 0 ]] && [[ "${CEO_RAG_INSTALL_PROMPT:-1}" != "0" ]]; then
  RAG_LOCK="$TARGET/.claude/rag/.install.lock"
  if [[ ! -f "$RAG_LOCK" ]]; then
    DETECT_SCRIPT="$TARGET/.claude/scripts/detect-repo-profile.py"
    if [[ -f "$DETECT_SCRIPT" ]]; then
      SIZE_JSON="$(python3 "$DETECT_SCRIPT" detect --target "$TARGET" --json 2>/dev/null || true)"
      SIZE_CLASS="$(printf '%s' "$SIZE_JSON" | python3 -c "import sys,json; d=json.loads(sys.stdin.read() or '{}'); print(d.get('size_class','SMALL'))" 2>/dev/null || echo SMALL)"
      if [[ "$SIZE_CLASS" = "LARGE" ]]; then
        echo ""
        echo "==> LARGE repo detected (>= 200k LoC)."
        echo "    The optional RAG sidecar (Tier-C — Owner consent required) can route"
        echo "    retrieval queries to a local LightRAG instance."
        echo ""
        echo "    Install footprint: ~90 MiB model + 500 MiB-1 GiB disk + 1-2 GiB RAM peak"
        echo "    See .claude/sidecars/c2-vector-memory/lightrag-mvp/README.md"
        echo ""
        printf "    Install RAG sidecar now? [y/N] (10s timeout) "
        REPLY=""
        if read -r -t 10 REPLY 2>/dev/null; then :; else REPLY="N"; fi
        case "${REPLY}" in
          [Yy]|[Yy][Ee][Ss])
            echo "==> Invoking sidecar installer..."
            (cd "$TARGET" && bash .claude/rag/install-sidecar.sh) || {
              echo "==> Sidecar install failed (exit $?). Retry manually:" >&2
              echo "    bash $TARGET/.claude/rag/install-sidecar.sh" >&2
            }
            ;;
          *)
            echo "==> Skipped sidecar install. Routing uses CAG fallback when LARGE."
            ;;
        esac
      fi
    fi
  fi
fi


if [[ "$DRY_RUN" -eq 1 ]]; then
  echo ""
  echo "==> Dry-run complete. No files were modified."
  echo "    To install for real: drop --dry-run and re-run."
  exit 0
fi

echo ""
echo "==> Install complete."
echo ""
echo "==> Placeholders remaining (fill in manually):"
echo ""

# Grep for unsubstituted placeholders. Count + list files, then list
# the unique placeholder names per file. Emit a top-level warning if
# any remain (not an error — adopter may want to fill in gradually).
PLACEHOLDER_COUNT=0
PLACEHOLDER_ROOTS=(
  "$TARGET/.claude"
  "$TARGET/CLAUDE.md"
  "$TARGET/MEMORY.md"
  "$TARGET/PROTOCOL.md"
  "$TARGET/docs"
)
REMAINING_FILES=""
for root in "${PLACEHOLDER_ROOTS[@]}"; do
  [[ -e "$root" ]] || continue
  # Portable approach: use grep -l; harmless if no matches.
  while IFS= read -r f; do
    [[ -n "$f" ]] || continue
    REMAINING_FILES="${REMAINING_FILES}${f}"$'\n'
    PLACEHOLDER_COUNT=$((PLACEHOLDER_COUNT + 1))
  done < <(grep -RIl '{{[A-Z_][A-Z0-9_]*}}' "$root" 2>/dev/null || true)
done

if [[ $PLACEHOLDER_COUNT -eq 0 ]]; then
  echo "    (none — all substituted)"
else
  printf '%s' "$REMAINING_FILES" | sort -u | while IFS= read -r f; do
    [[ -n "$f" ]] || continue
    echo "    $f"
    grep -ho '{{[A-Z_][A-Z0-9_]*}}' "$f" 2>/dev/null | sort -u | sed 's/^/        /'
  done
  echo ""
  echo "    WARNING: $PLACEHOLDER_COUNT file(s) still contain {{PLACEHOLDER}} markers." >&2
  echo "             Re-run install.sh with more flags (e.g. --deploy-command ..)" >&2
  echo "             or edit the files manually." >&2
fi

echo ""
echo "==> Next steps:"
echo "    1. Edit CLAUDE.md to fill in your project context."
echo "    2. Edit .claude/team.md to add your personas (or start with archetypes)."
echo "    3. Start a Claude Code session and ask: 'Activate the CEO protocol and load the team.'"
# PLAN-135 W5 O12: close the install ceremony with a harness-native sanity
# check. /doctor validates settings.json / hooks / MCP wiring from inside the
# real Claude Code harness — it catches a malformed settings file BEFORE the
# framework's own gates run against it (the S217/S228 silent-hook class, where
# a settings-skip or exec-bit left a governance rail silently disengaged).
# Advisory + harness-side; install.sh prints it, it does not run claude.
echo "    4. Run \`claude\` and type \`/doctor\` once: confirm settings.json parses,"
echo "       hooks are registered, and no rail is silently skipped before you rely"
echo "       on the governance gates (catches malformed settings the framework"
echo "       would otherwise fail-open past). Then optionally run"
echo "       \`python3 .claude/scripts/ceo-info.py --check --hooks-diff\` for the"
echo "       framework-side mirror (registered-vs-effective hook count)."
if has_profile "fintech"; then
  echo ""
  echo "==> Fintech domain installed:"
  echo "    - 12 fintech skills in .claude/skills/domains/fintech/skills/"
  echo "    - FIN-*/EX-* pitfalls in .claude/skills/domains/fintech/pitfalls.yaml"
  echo "    - Reference personas in .claude/skills/domains/fintech/team-personas.md"
  echo "    - Additional commands in .claude/skills/domains/fintech/commands/"
fi

# Release workflow (.github/workflows/release.yml) replaces the
# PLACEHOLDER_RELEASE_FILL value below with the sha256 of everything
# above this trailer line at tag cut. DO NOT EDIT MANUALLY.
# CEO-INSTALL-SHA256: PLACEHOLDER_RELEASE_FILL
