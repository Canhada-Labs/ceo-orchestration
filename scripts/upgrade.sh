#!/usr/bin/env bash
# upgrade.sh — update an existing ceo-orchestration install in a target repo
#
# Usage:
#   ./upgrade.sh <target-repo-path> [--profile <list>] [--stack <name>]
#                                    [--pin <tag>] [--dry-run]
#                                    [--skip <glob>] [--no-diff-warn]
#                                    [--no-deprecation-warn]
#
# What it does:
#   - Backs up the current .claude/team.md, .claude/frontend-team.md, .claude/skills/,
#     .claude/hooks/, .claude/scripts/, .claude/commands/, .claude/pitfalls-catalog.yaml,
#     .claude/task-chains.yaml to .claude.bak/{timestamp}/
#   - (F-CHAOS-3) Before overwriting any adopter file that differs from the source,
#     emits a `diff -q`-style WARNING line (shown on stderr) so the Owner is aware
#     a customization will be replaced. Pass --no-diff-warn to silence.
#     Pass --skip=<glob> to exclude files from the overwrite entirely (one --skip per pattern).
#   - Replaces them with the latest from this repo, respecting --profile and --stack
#   - Leaves CLAUDE.md, MEMORY.md, .claude/agent-metrics.md untouched — those are
#     user-customized files. .claude/settings.json is preserved as-is for its
#     existing keys, but the PLAN-135 W2 settings-merge step (below) ADDITIVELY
#     registers new framework lifecycle hooks into it (idempotent, non-clobbering).
#   - (DevOps-P1-4) Refreshes the PROTOCOL.md pointer to keep it aligned with the
#     current source layout (framework-derived content, not user data).
#   - (PLAN-135 W1 w0r) Pre-flight ADVISORY model-deprecation scan of the target
#     via .claude/scripts/check-model-deprecations.py when present: already-retired
#     or <=60-days-to-retirement Claude model ids emit stderr WARNING lines.
#     NEVER blocks the upgrade — any infra failure degrades to a NOTE (fail-open).
#     Pass --no-deprecation-warn to silence.
#   - (PLAN-135 W2 H8) Idempotent settings-merge step. install.sh EXISTS-SKIPs an
#     existing .claude/settings.json, so a fresh-install-only hook registration
#     never reaches the S217 population of existing adopters. This step registers
#     the new framework lifecycle hooks (today: the `Setup`/`init` post-install
#     self-verification hook check_setup_verification.py) into the adopter's
#     existing settings.json via an idempotent `jq` merge — additive, never
#     clobbers existing entries, re-applying is a no-op. Fail-open: missing jq /
#     malformed settings / merge error => stderr NOTE + the upgrade proceeds.
#     Pass --no-settings-merge to opt out.
#   - Owner-gated, no-silent-update: this script is NEVER auto-invoked. The Owner
#     runs it explicitly after a deliberate `git pull`; the framework never
#     self-updates or auto-downloads in the background (convergent with kooky's
#     manual-only update checker — see PLAN-125 WS-3c / E5).
#   - (PLAN-153 Wave B item B2) REPLAYS the RECORDED install request: when
#     $TARGET/.claude/.install-state.json (written by install.sh since Wave B;
#     schema ceo.install-state/v1) is present and valid, --profile/--stack
#     DEFAULT to the recorded request.profile/request.stack. Explicit flags
#     always win; --no-replay opts out entirely. BACK-COMPAT (debate C
#     must-fix): a missing state file (every pre-Wave-B install) or an
#     unreadable/invalid one NEVER errors and NEVER no-ops — the upgrade
#     proceeds exactly as before on the ADR-155 path (--dry-run previews +
#     the baseline drift-classifier below preserve/refuse customizations,
#     degrading to diff -q warn-then-clobber when no baseline manifest
#     exists either). After a successful non-dry upgrade the state file is
#     (re)written, so the pre-Wave-B population acquires one (mirrors
#     ADR-155 decision iv for the manifest). Replayed values are charset-
#     validated data — the state file is UNSIGNED and advisory, never a
#     trust anchor, and is never eval-ed.
#
# Run after `git pull` in the source ceo-orchestration repo.

# Bash 3.2 portability guard (DevOps-P1-3 parity with install.sh)
if [ -z "${BASH_VERSINFO:-}" ]; then
  echo "ERROR: upgrade.sh requires bash (detected non-bash shell)" >&2
  exit 1
fi
if [ "${BASH_VERSINFO[0]}" -lt 3 ] || \
   { [ "${BASH_VERSINFO[0]}" -eq 3 ] && [ "${BASH_VERSINFO[1]}" -lt 2 ]; }; then
  echo "ERROR: upgrade.sh requires bash >= 3.2 (detected ${BASH_VERSION})" >&2
  exit 1
fi

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SOURCE_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

# PLAN-138 Wave C (ADR-155) — portable SHA-256 helpers + the single shared
# framework-owned enumeration, sourced (not executed). Both back the baseline
# classifier below. Fail-open: if a helper is absent (partial checkout) the
# classifier degrades to today's diff -q warn-then-clobber behavior.
if [ -f "$SCRIPT_DIR/_hash_lib.sh" ]; then
  # shellcheck source=scripts/_hash_lib.sh
  . "$SCRIPT_DIR/_hash_lib.sh"
fi
if [ -f "$SCRIPT_DIR/_framework_manifest_set.sh" ]; then
  # shellcheck source=scripts/_framework_manifest_set.sh
  . "$SCRIPT_DIR/_framework_manifest_set.sh"
fi

# PLAN-153 Wave B item B2 — capture the ORIGINAL upgrade argv verbatim BEFORE
# parsing, for the post-upgrade state record (data only, never eval-ed).
ORIG_UP_ARGV=( "$@" )

TARGET=""
PROFILE="core,frontend"
STACK="none"
PIN_REF=""
DRY_RUN=0
DIFF_WARN=1
DEPRECATION_WARN=1
SETTINGS_MERGE=1
ON_CONFLICT="refuse"   # PLAN-138 Wave C (ADR-155): {refuse|theirs|backup}; default refuse (OQ2)
REPLAY=1               # PLAN-153 Wave B item B2: replay the recorded install request (opt out: --no-replay)
PROFILE_EXPLICIT=0      # PLAN-153 B2: explicit --profile always beats a replayed value
STACK_EXPLICIT=0        # PLAN-153 B2: explicit --stack always beats a replayed value
SKIP_GLOBS=()

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)
      PROFILE="${2:-}"
      PROFILE_EXPLICIT=1
      shift 2
      ;;
    --stack)
      STACK="${2:-}"
      STACK_EXPLICIT=1
      shift 2
      ;;
    --pin)
      PIN_REF="${2:-}"
      shift 2
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --no-diff-warn)
      DIFF_WARN=0
      shift
      ;;
    --no-deprecation-warn)
      DEPRECATION_WARN=0
      shift
      ;;
    --no-settings-merge)
      SETTINGS_MERGE=0
      shift
      ;;
    --no-replay)
      # PLAN-153 Wave B item B2: ignore .claude/.install-state.json entirely.
      REPLAY=0
      shift
      ;;
    --skip)
      SKIP_GLOBS+=( "${2:-}" )
      shift 2
      ;;
    --skip=*)
      SKIP_GLOBS+=( "${1#--skip=}" )
      shift
      ;;
    --on-conflict)
      ON_CONFLICT="${2:-}"
      case "$ON_CONFLICT" in
        refuse|theirs|backup) ;;
        *) echo "ERROR: --on-conflict must be refuse|theirs|backup (got: $ON_CONFLICT)" >&2; exit 1 ;;
      esac
      shift 2
      ;;
    --on-conflict=*)
      ON_CONFLICT="${1#--on-conflict=}"
      case "$ON_CONFLICT" in
        refuse|theirs|backup) ;;
        *) echo "ERROR: --on-conflict must be refuse|theirs|backup (got: $ON_CONFLICT)" >&2; exit 1 ;;
      esac
      shift
      ;;
    -h|--help)
      cat <<'HELP'
Usage:
  ./upgrade.sh <target-repo-path> [options]

What it does:
  Refreshes the framework-derived content (team.md, skills/, hooks/,
  scripts/, commands/, pitfalls-catalog.yaml, task-chains.yaml) in an
  existing adopter install. User-customized files (CLAUDE.md, MEMORY.md,
  .claude/settings.json, .claude/agent-metrics.md) are NOT touched.

Options:
  --profile <list>      Comma-separated profiles to refresh (default: core,frontend).
                        Available: core, frontend, <domain-name>.
                        Example: --profile core,fintech
  --stack <name>        Stack-specific hooks override (default: none).
                        Example: --stack node
  --pin <tag>           Pin source to specific tag/SHA (SPEC v1 install-cli.md).
                        Refuses if target has uncommitted .claude/ changes.
                        Example: --pin v1.18.0
  --dry-run             Print what WOULD be replaced without modifying $TARGET.
  --no-diff-warn        Silence the F-CHAOS-3 "customization will be replaced" warnings.
  --no-deprecation-warn Silence the PLAN-135 advisory model-deprecation scan
                        (the scan never blocks the upgrade either way).
  --no-settings-merge   Skip the PLAN-135 W2 idempotent settings-merge step
                        that registers new lifecycle hooks (e.g. the Setup
                        post-install self-verification hook) into the adopter's
                        existing .claude/settings.json. The merge is idempotent
                        + fail-open (never blocks the upgrade); pass this to opt
                        out entirely and manage settings.json by hand.
  --no-replay           PLAN-153 Wave B (B2): do NOT replay the recorded
                        install request from .claude/.install-state.json.
                        By default, when that file exists and validates,
                        --profile/--stack DEFAULT to the recorded values
                        (explicit flags always win). Missing/invalid state
                        falls back to the ADR-155 drift-classifier path —
                        never an error, never a no-op.
  --skip <glob>         Exclude files from the overwrite (repeat for multiple globs).
                        Example: --skip='.claude/scripts/local/*'
  --skip=<glob>         Alternate inline syntax for --skip.
  --on-conflict <mode>  PLAN-138 Wave C (ADR-155): how to handle a CONFLICT — a
                        file that differs from BOTH the recorded install
                        baseline AND the new framework source (adopter and
                        framework both changed it). One of:
                          refuse  (default) per-file skip + report, never abort
                          theirs  overwrite with the framework version
                          backup  overwrite, original preserved in .claude.bak/
                        Requires a baseline manifest; without one the upgrade
                        falls back to today's diff -q warn-then-clobber.
  -h, --help            Show this help and exit 0.

Backup behavior:
  Files about to be overwritten are first copied to .claude.bak/{timestamp}/
  inside $TARGET. If a customization exists at the destination, a `diff -q`
  WARNING is emitted on stderr (suppressible via --no-diff-warn).

Exit codes:
  0 — upgrade completed (or --help / --dry-run preview)
  1 — bad usage / unknown option / missing target
  2 — target has uncommitted .claude/ changes when --pin was passed

Notes:
  Run after `git pull` in the source ceo-orchestration repo. The upgrade
  refreshes the PROTOCOL.md pointer to keep the adopter aligned with the
  current source layout (DevOps-P1-4).

See also:
  scripts/install.sh --help     for fresh-install flags + profile semantics
  INSTALL.md §Upgrade flow      for the full upgrade walk-through
HELP
      exit 0
      ;;
    -*)
      echo "ERROR: unknown option: $1" >&2
      exit 1
      ;;
    *)
      TARGET="$1"
      shift
      ;;
  esac
done

if [[ -z "$TARGET" || ! -d "$TARGET" ]]; then
  echo "Usage: $0 <target-repo-path> [--profile <list>] [--stack <name>] [--pin <tag>] [--dry-run]" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# PLAN-106 Wave G.2 — git-checkout retry wrapper around index.lock contention.
# ---------------------------------------------------------------------------
# Wraps `git checkout --quiet "$PIN_REF"` with a 3-attempt retry on
# `.git/index.lock` busy. Per-attempt audit event via emit_git_index_lock_retry.
# Argv-pass invocation per PLAN-106 §3 Wave G.2.b — never source-string
# interpolation; absolute HOOKS_DIR; PYTHONNOUSERSITE=1 python3 -I.
#
# Override budget via CEO_GIT_LOCK_RETRY_MAX (default 3) for tests.
# Override unit-test override via CEO_GIT_LOCK_RETRY_BACKOFF_BASE (default 1)
# so the test can use 0s waits.
_git_checkout_with_lock_retry() {
  local src_dir="$1"
  local pin_ref="$2"
  local max_attempts="${CEO_GIT_LOCK_RETRY_MAX:-3}"
  local backoff_base="${CEO_GIT_LOCK_RETRY_BACKOFF_BASE:-1}"
  local attempt=1
  local rc=0
  local err_out=""
  local repo_root_for_hash
  local hash
  local hooks_dir

  # Derive HASH explicitly as hex-only by construction (collision-resistant):
  # use git rev-parse on the source dir; fall back to $src_dir literal if
  # rev-parse fails (e.g. during sandbox-sim of a fresh init).
  repo_root_for_hash="$( cd "$src_dir" 2>/dev/null && git rev-parse --show-toplevel 2>/dev/null || printf '%s' "$src_dir" )"
  # PLAN-138 Wave C (ADR-155): hash a STRING via the portable _hash_stdin
  # (shasum||sha256sum). This hashes a PATH STRING (not a file), so the
  # stdin/string hasher is correct — NOT a content hash. Fall back to the
  # legacy bare shasum if the helper was not sourced (partial checkout).
  if command -v _hash_stdin >/dev/null 2>&1; then
    hash="$( printf '%s' "$repo_root_for_hash" | _hash_stdin )"
  else
    hash="$( printf '%s' "$repo_root_for_hash" | shasum -a 256 | awk '{print $1}' )"
  fi
  # Resolve hooks directory to ABSOLUTE path (Codex P0 fold — relative
  # sys.path.insert is vulnerable to CWD manipulation):
  hooks_dir="$SOURCE_DIR/.claude/hooks"

  while [[ "$attempt" -le "$max_attempts" ]]; do
    err_out="$( ( cd "$src_dir" && git checkout --quiet "$pin_ref" ) 2>&1 )" && rc=0 || rc=$?
    if [[ "$rc" -eq 0 ]]; then
      return 0
    fi

    # Detect index.lock contention. Two canonical git error strings:
    #   "Another git process seems to be running in this repository"
    #   "fatal: Unable to create '.git/index.lock': File exists"
    if echo "$err_out" | grep -qE 'index\.lock|Another git process seems to be running'; then
      local backoff_seconds=$(( backoff_base * (2 ** (attempt - 1)) ))

      # PLAN-106 Wave G.2 hardened invocation. argv-pass eliminates
      # source-string interpolation (lesson [[feedback-bash-heredoc-paren-in-subshell]]).
      # python3 -I + PYTHONNOUSERSITE=1 shrink env-driven import surface.
      # Best-effort emit — failure must NOT abort the retry chain.
      PYTHONNOUSERSITE=1 python3 -I -c '
import sys
hooks_dir = sys.argv[1]
if hooks_dir not in sys.path:
    sys.path.insert(0, hooks_dir)
from _lib.audit_emit import emit_git_index_lock_retry
emit_git_index_lock_retry(
    attempt=int(sys.argv[2]),
    backoff_seconds=int(sys.argv[3]),
    repo_path_hash=sys.argv[4],
    operation="upgrade_sh_git_checkout",
)' "$hooks_dir" "$attempt" "$backoff_seconds" "$hash" 2>/dev/null || true

      echo "    NOTE: git index.lock busy (attempt $attempt/$max_attempts) — backing off ${backoff_seconds}s" >&2
      if [[ "$attempt" -lt "$max_attempts" ]]; then
        sleep "$backoff_seconds"
      fi
      attempt=$(( attempt + 1 ))
      continue
    fi

    # Non-lock error — surface and bail.
    echo "$err_out" >&2
    return "$rc"
  done

  # Exhausted retries on lock contention.
  echo "ERROR: git checkout $pin_ref retry budget exhausted after $max_attempts attempts (.git/index.lock contention)" >&2
  return 2
}

# --pin contract (SPEC v1 install-cli.md, ADR-007):
# - Resolve <ref> via git rev-parse --verify in the source framework repo
# - Refuse if target has uncommitted .claude/ changes (exit 2)
# - On --dry-run: print diff between current and pinned and exit 0
# - Otherwise: git checkout <ref> in source; run normal upgrade;
#   restore original branch at end
PINNED_CHECKOUT_DONE=0
ORIGINAL_BRANCH=""
if [[ -n "$PIN_REF" ]]; then
  if ! pushd "$SOURCE_DIR" >/dev/null; then
    echo "ERROR: cannot cd to source repo: $SOURCE_DIR" >&2
    exit 1
  fi
  if ! git rev-parse --verify "$PIN_REF" >/dev/null 2>&1; then
    echo "ERROR: unknown --pin ref: $PIN_REF" >&2
    popd >/dev/null || true
    exit 2
  fi
  ORIGINAL_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")"
  popd >/dev/null || true

  # Refuse on uncommitted target .claude/ changes unless CEO_ORCH_FORCE=1
  if [[ -d "$TARGET/.claude" ]] && [[ -d "$TARGET/.git" ]] && [[ "${CEO_ORCH_FORCE:-0}" != "1" ]]; then
    if ( cd "$TARGET" && ! git diff --quiet -- .claude/ 2>/dev/null ); then
      echo "ERROR: target has uncommitted .claude/ changes." >&2
      echo "       Commit, stash, or set CEO_ORCH_FORCE=1 to override." >&2
      exit 2
    fi
  fi

  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "==> Dry-run: diff between current source and --pin $PIN_REF"
    ( cd "$SOURCE_DIR" && git diff "$PIN_REF"...HEAD -- .claude/ scripts/ templates/ SPEC/ || true )
    exit 0
  fi

  # PLAN-106 Wave G.2: wrapped retry around `git checkout`. Replaces the
  # bare `git checkout --quiet "$PIN_REF"` call at the previous
  # upgrade.sh:180. Retry budget is 3 attempts with exponential backoff
  # (1s, 2s, 4s). Per-attempt audit event via emit_git_index_lock_retry.
  if ! _git_checkout_with_lock_retry "$SOURCE_DIR" "$PIN_REF"; then
    echo "ERROR: git checkout $PIN_REF failed in source." >&2
    exit 2
  fi
  PINNED_CHECKOUT_DONE=1

  # Restore source branch on any exit (trap)
  trap '
    if [[ "$PINNED_CHECKOUT_DONE" -eq 1 ]] && [[ -n "$ORIGINAL_BRANCH" ]]; then
      ( cd "$SOURCE_DIR" && git checkout --quiet "$ORIGINAL_BRANCH" 2>/dev/null ) || true
    fi
  ' EXIT
fi

TARGET="$( cd "$TARGET" && pwd )"

# ===========================================================================
# PLAN-153 Wave B item B2 — replay the RECORDED install request.
# ===========================================================================
# install.sh (>= Wave B) records the original request in
# $TARGET/.claude/.install-state.json (schema ceo.install-state/v1). When
# present + valid, request.profile / request.stack become the DEFAULTS for
# this upgrade so an adopter who installed `--profile core,fintech` does not
# silently get the core,frontend default by forgetting the flag. Explicit
# flags always win; --no-replay opts out.
#
# BACK-COMPAT (debate C must-fix): missing state (ALL pre-Wave-B installs)
# or unreadable/invalid state NEVER errors and NEVER no-ops — the upgrade
# proceeds with CLI/default flags on the ADR-155 path (the --dry-run preview
# and the baseline drift-classifier below), and a state file is (re)written
# after a successful non-dry upgrade so the NEXT run can replay.
#
# TRUST: the state file is target-side, UNSIGNED, advisory (ADR-155 trust
# class). Values are parsed by python3 -I under PYTHONNOUSERSITE=1, charset-
# validated (profile: [A-Za-z0-9_,.-]{1,200}; stack: [A-Za-z0-9_.-]{1,100}),
# and NEVER eval-ed; anything suspect => fallback, exactly as if absent.
_INSTALL_STATE_FILE="$TARGET/.claude/.install-state.json"
_REPLAY_SOURCE="cli-default"
_UP_OPS_FILE=""

# Print "<profile>\t<stack>" from a valid state file; non-zero rc on ANY
# problem (missing python3, unreadable file, bad JSON, wrong schema_version,
# non-string or charset-violating values) => caller falls back.
_read_install_state_request() {
  command -v python3 >/dev/null 2>&1 || return 3
  [ -f "$_INSTALL_STATE_FILE" ] && [ -r "$_INSTALL_STATE_FILE" ] || return 3
  PYTHONNOUSERSITE=1 python3 -I -c '
import json, re, sys
try:
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        d = json.load(f)
except (OSError, ValueError):
    sys.exit(3)
if not isinstance(d, dict):
    sys.exit(3)
if d.get("schema_version") != 1:
    sys.exit(3)
req = d.get("request")
if not isinstance(req, dict):
    sys.exit(3)
prof = req.get("profile", "")
stack = req.get("stack", "")
if not isinstance(prof, str) or not isinstance(stack, str):
    sys.exit(3)
if prof and not re.match(r"^[A-Za-z0-9_,.-]{1,200}$", prof):
    sys.exit(3)
if stack and not re.match(r"^[A-Za-z0-9_.-]{1,100}$", stack):
    sys.exit(3)
sys.stdout.write(prof + "\t" + stack + "\n")
' "$_INSTALL_STATE_FILE" 2>/dev/null
}

if [[ "$REPLAY" -eq 1 ]]; then
  if [[ -f "$_INSTALL_STATE_FILE" ]]; then
    _rp_line=""
    if _rp_line="$(_read_install_state_request)" && [[ -n "$_rp_line" ]]; then
      _rp_profile="${_rp_line%%$'\t'*}"
      _rp_stack="${_rp_line#*$'\t'}"
      _rp_used=0
      if [[ "$PROFILE_EXPLICIT" -eq 0 && -n "$_rp_profile" ]]; then
        PROFILE="$_rp_profile"
        _rp_used=1
        echo "    REPLAY: --profile $PROFILE (recorded request in .claude/.install-state.json; pass --profile or --no-replay to override)" >&2
      fi
      if [[ "$STACK_EXPLICIT" -eq 0 && -n "$_rp_stack" ]]; then
        STACK="$_rp_stack"
        _rp_used=1
        echo "    REPLAY: --stack $STACK (recorded request in .claude/.install-state.json; pass --stack or --no-replay to override)" >&2
      fi
      if [[ "$_rp_used" -eq 1 ]]; then
        _REPLAY_SOURCE="replay"
      fi
    else
      _REPLAY_SOURCE="fallback-invalid-state"
      echo "    NOTE: .claude/.install-state.json present but unreadable/invalid — IGNORED." >&2
      echo "          Proceeding with CLI/default flags on the ADR-155 path (baseline" >&2
      echo "          drift-classifier; --dry-run previews). Never blocks (PLAN-153" >&2
      echo "          debate C back-compat must-fix); a valid state file is rewritten" >&2
      echo "          after this upgrade completes." >&2
    fi
  else
    _REPLAY_SOURCE="fallback-no-state"
    echo "    NOTE: no .claude/.install-state.json in target (pre-Wave-B install)." >&2
    echo "          Proceeding with CLI/default flags on the ADR-155 path (baseline" >&2
    echo "          drift-classifier when a manifest exists, else diff -q warn-then-" >&2
    echo "          clobber). A state file is recorded after this upgrade completes." >&2
  fi
fi

TIMESTAMP="$( date +%Y%m%d-%H%M%S )"
BAK_DIR="$TARGET/.claude.bak/$TIMESTAMP"

IFS=',' read -r -a PROFILE_PARTS <<< "$PROFILE"

echo "==> Upgrading ceo-orchestration"
echo "    Source:  $SOURCE_DIR"
echo "    Target:  $TARGET"
echo "    Backup:  $BAK_DIR"
echo "    Profile: $PROFILE"
echo "    Stack:   $STACK"
if [[ "$_REPLAY_SOURCE" == "replay" ]]; then
  echo "    Request: replayed from .claude/.install-state.json (PLAN-153 B2)"
fi
if [[ -n "$PIN_REF" ]]; then
  echo "    Pinned:  $PIN_REF"
fi
echo ""

mkdir -p "$BAK_DIR"

# PLAN-153 Wave B item B2 — upgrade operation journal (same shape as the
# install-side journal): op<TAB>detail lines in a tempfile OUTSIDE $TARGET,
# folded into .claude/.install-state.json by _write_upgrade_state at the end.
# Dry-run never creates it. Fail-open throughout.
if [[ "$DRY_RUN" -eq 0 ]]; then
  _UP_OPS_FILE="$(mktemp "${TMPDIR:-/tmp}/ceo-upgrade-ops.XXXXXX" 2>/dev/null || true)"
fi
_up_record_op() {
  if [[ -n "${_UP_OPS_FILE:-}" && -f "${_UP_OPS_FILE:-}" ]]; then
    printf '%s\t%s\n' "$1" "${2:-}" >> "$_UP_OPS_FILE" 2>/dev/null || true
  fi
  return 0
}

# ===========================================================================
# PLAN-138 Wave C (ADR-155) — baseline manifest load + per-file classifier.
# ===========================================================================
# Read $TARGET/.claude/.install-manifest.sha256 ONCE at startup into a
# validated, sanitized lookup file. Every line is re-validated here against the
# two accepted record grammars; any line that matches NEITHER, or whose relpath
# is absolute / contains `..` / control chars / duplicates an earlier relpath /
# traverses a symlinked component, is DROPPED so it can never drive a silent
# FRAMEWORK-CHANGED branch (CWE-345/494/22 provenance hardening). The raw
# manifest is NEVER piped into `shasum -c`; classification recomputes +
# compares in-process per validated relpath.
#
# bash 3.2-safe: no associative arrays. The validated manifest is a temp file;
# lookups use a fixed-string, line-anchored grep.
_BASELINE_MANIFEST_RAW="$TARGET/.claude/.install-manifest.sha256"
_BASELINE_MANIFEST_FILE=""   # set to the sanitized temp file if a manifest loads
_BASELINE_DUP_GUARD=""       # newline-list of relpaths already accepted (dup detection)
_BASELINE_INVALID=""         # newline-list of relpaths seen >1x: AMBIGUOUS provenance,
                             # rejected entirely (NOT first-wins) — Codex R1 P0#2 fold.

# Reject a relpath that is unsafe to trust from the manifest. Returns 0 (reject)
# / 1 (accept). Checks: absolute, `..` segment, control chars, and a symlinked
# component anywhere along the path under $TARGET (lstat per component, never
# follow). Duplicate relpaths are rejected by the caller via _BASELINE_DUP_GUARD.
_baseline_relpath_unsafe() {
  _bru_rel="$1"
  case "$_bru_rel" in
    /*) return 0 ;;                       # absolute
    *..*) return 0 ;;                      # parent traversal (covers ../ and /..)
  esac
  # Control chars / whitespace-only / empty.
  case "$_bru_rel" in
    ""|*[$'\n\r\t']*) return 0 ;;
  esac
  # Symlinked-component check: walk each path component under $TARGET; if any
  # EXISTING component is a symlink, reject (do not follow it).
  _bru_cur="$TARGET"
  _bru_oldIFS="$IFS"
  IFS='/'
  for _bru_comp in $_bru_rel; do
    [ -n "$_bru_comp" ] || continue
    [ "$_bru_comp" = "." ] && continue
    _bru_cur="$_bru_cur/$_bru_comp"
    if [ -L "$_bru_cur" ]; then
      IFS="$_bru_oldIFS"
      return 0
    fi
  done
  IFS="$_bru_oldIFS"
  return 1
}

# Load + sanitize the baseline manifest. On any problem (absent / unreadable /
# empty after sanitization) leaves _BASELINE_MANIFEST_FILE empty => fallback.
_load_baseline_manifest() {
  [ -f "$_BASELINE_MANIFEST_RAW" ] && [ -r "$_BASELINE_MANIFEST_RAW" ] || return 0
  command -v _hash_file >/dev/null 2>&1 || return 0

  local sanitized
  sanitized="$( mktemp "$BAK_DIR/.baseline-manifest.XXXXXX" 2>/dev/null )" || return 0

  local line rest rel digest target
  # Read line-by-line; NEVER `eval` or interpret manifest content.
  while IFS= read -r line || [ -n "$line" ]; do
    [ -n "$line" ] || continue
    # Hash record: ^<64hex><2 spaces><relpath>$
    # Link record: ^LINK<2 spaces><relpath><2 spaces><target>$
    case "$line" in
      LINK\ \ *)
        rest="${line#LINK  }"
        # relpath is everything up to the FIRST double-space; target the rest.
        case "$rest" in
          *"  "*)
            rel="${rest%%  *}"
            target="${rest#*  }"
            ;;
          *) continue ;;   # malformed LINK (no target) — drop
        esac
        if _baseline_relpath_unsafe "$rel"; then continue; fi
        # Duplicate relpath? Ambiguous provenance — invalidate the relpath
        # ENTIRELY (not first-wins): the lookup will refuse it -> fallback.
        case "$_BASELINE_DUP_GUARD" in
          *"
$rel
"*)
            case "$_BASELINE_INVALID" in
              *"
$rel
"*) ;;
              *) _BASELINE_INVALID="$_BASELINE_INVALID
$rel
" ;;
            esac
            continue ;;
        esac
        _BASELINE_DUP_GUARD="$_BASELINE_DUP_GUARD
$rel
"
        # Re-emit a normalized LINK record (target sanitized of control chars).
        case "$target" in
          *[$'\n\r\t']*) continue ;;
        esac
        printf 'LINK  %s  %s\n' "$rel" "$target" >> "$sanitized"
        ;;
      *)
        # Must be exactly 64-hex, two spaces, then relpath.
        digest="${line%%  *}"
        rel="${line#*  }"
        # Guard: the split must have actually found a double-space separator.
        [ "$digest" != "$line" ] || continue
        case "$digest" in
          [0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]) ;;
          *) continue ;;   # not a 64-hex digest — drop (provenance)
        esac
        if _baseline_relpath_unsafe "$rel"; then continue; fi
        # Duplicate relpath? Ambiguous provenance — invalidate ENTIRELY
        # (not first-wins): the lookup refuses it -> fallback. (Codex R1 P0#2)
        case "$_BASELINE_DUP_GUARD" in
          *"
$rel
"*)
            case "$_BASELINE_INVALID" in
              *"
$rel
"*) ;;
              *) _BASELINE_INVALID="$_BASELINE_INVALID
$rel
" ;;
            esac
            continue ;;
        esac
        _BASELINE_DUP_GUARD="$_BASELINE_DUP_GUARD
$rel
"
        printf '%s  %s\n' "$digest" "$rel" >> "$sanitized"
        ;;
    esac
  done < "$_BASELINE_MANIFEST_RAW"

  if [ -s "$sanitized" ]; then
    _BASELINE_MANIFEST_FILE="$sanitized"
  else
    rm -f "$sanitized" 2>/dev/null || true
  fi
  return 0
}

# Echo the baseline digest for $1 if (and only if) it is a validated HASH
# record. A LINK record or an absent line echoes nothing + returns 1 => the
# caller falls back. Exact relpath match (the part after the two-space
# separator must equal $1 exactly). awk does the exact match + 64-hex check in
# one pass — no fragile nested while/case under set -u.
_baseline_lookup() {
  _bl_rel="$1"
  [ -n "$_BASELINE_MANIFEST_FILE" ] || return 1
  [ -f "$_BASELINE_MANIFEST_FILE" ] || return 1
  # Refuse a relpath flagged as duplicate/ambiguous during load (Codex R1 P0#2):
  # never trust a baseline digest for a relpath that appeared more than once.
  case "$_BASELINE_INVALID" in
    *"
$_bl_rel
"*) return 1 ;;
  esac
  _bl_digest="$( awk -v want="$_bl_rel" '
    {
      # Split on the FIRST double-space: field1 = digest-or-LINK, rest = path[+target].
      idx = index($0, "  ");
      if (idx == 0) next;
      d = substr($0, 1, idx - 1);
      rest = substr($0, idx + 2);
      if (d == "LINK") next;                 # link record: no content baseline
      # rest must equal the wanted relpath exactly (hash records have no 2nd
      # double-space: relpath runs to EOL).
      if (rest != want) next;
      if (length(d) != 64) next;
      if (d ~ /^[0-9a-f]+$/) { print d; exit 0 }
    }
  ' "$_BASELINE_MANIFEST_FILE" 2>/dev/null )"
  [ -n "$_bl_digest" ] || return 1
  printf '%s\n' "$_bl_digest"
}

# Classify a single repo-relative file against the baseline. Echoes ONE verdict:
#   FRAMEWORK-CHANGED  H_dst==H_base && H_src!=H_base  -> safe to auto-update
#   ADOPTER-CUSTOMIZED H_dst!=H_base && H_src==H_base  -> preserve
#   CONFLICT           both differ from H_base         -> --on-conflict
#   IDENTICAL          H_dst==H_src                    -> nothing to do
#   FALLBACK           no usable baseline / hasher      -> today's behavior
# H_dst and H_src are BOTH recomputed from disk THIS run (never cached H_src).
_classify_against_baseline() {
  _cab_rel="$1"
  command -v _hash_file >/dev/null 2>&1 || { printf 'FALLBACK\n'; return 0; }
  _cab_base="$( _baseline_lookup "$_cab_rel" )" || { printf 'FALLBACK\n'; return 0; }
  _cab_dst="$( _hash_file "$TARGET/$_cab_rel" 2>/dev/null || true )"
  _cab_src="$( _hash_file "$SOURCE_DIR/$_cab_rel" 2>/dev/null || true )"
  # If either side cannot be hashed (missing file), fall back to legacy handling.
  if [ -z "$_cab_dst" ] || [ -z "$_cab_src" ]; then
    printf 'FALLBACK\n'; return 0
  fi
  if [ "$_cab_dst" = "$_cab_src" ]; then
    printf 'IDENTICAL\n'; return 0
  fi
  if [ "$_cab_dst" = "$_cab_base" ] && [ "$_cab_src" != "$_cab_base" ]; then
    printf 'FRAMEWORK-CHANGED\n'; return 0
  fi
  if [ "$_cab_dst" != "$_cab_base" ] && [ "$_cab_src" = "$_cab_base" ]; then
    printf 'ADOPTER-CUSTOMIZED\n'; return 0
  fi
  # Both differ from the baseline.
  printf 'CONFLICT\n'; return 0
}

_load_baseline_manifest

# F-CHAOS-3: match a relative path against the --skip globs list.
# Returns 0 (true) if matched.
_path_is_skipped() {
  local rel="$1"
  local pattern
  for pattern in "${SKIP_GLOBS[@]:-}"; do
    [[ -n "$pattern" ]] || continue
    # Intentional unquoted glob match (the whole point of --skip patterns).
    # shellcheck disable=SC2053,SC2254
    case "$rel" in
      $pattern) return 0 ;;
    esac
  done
  return 1
}

# F-CHAOS-3: emit a diff-q-style WARNING line for every adopter file
# that differs from the source before we overwrite it. Recurses into
# directories. Respects --no-diff-warn and --skip globs.
_emit_diff_warnings() {
  local rel_path="$1"
  local src="$SOURCE_DIR/$rel_path"
  local dst="$TARGET/$rel_path"

  [[ "$DIFF_WARN" -eq 1 ]] || return 0
  [[ -e "$dst" && -e "$src" ]] || return 0

  if [[ -d "$src" && -d "$dst" ]]; then
    # Per-file diff within the directory
    local f rel sub
    while IFS= read -r f; do
      [[ -n "$f" ]] || continue
      sub="${f#$dst/}"
      rel="$rel_path/$sub"
      if _path_is_skipped "$rel"; then
        echo "    SKIP-DIFF (--skip): $rel" >&2
        continue
      fi
      if [[ -f "$SOURCE_DIR/$rel" ]]; then
        if ! diff -q "$f" "$SOURCE_DIR/$rel" >/dev/null 2>&1; then
          echo "    WARNING: adopter customization in $rel will be OVERWRITTEN" >&2
          echo "             (backup preserved in $BAK_DIR/$rel)" >&2
        fi
      fi
    done < <(find "$dst" -type f 2>/dev/null)
  elif [[ -f "$src" && -f "$dst" ]]; then
    if _path_is_skipped "$rel_path"; then
      echo "    SKIP-DIFF (--skip): $rel_path" >&2
      return 0
    fi
    if ! diff -q "$dst" "$src" >/dev/null 2>&1; then
      echo "    WARNING: adopter customization in $rel_path will be OVERWRITTEN" >&2
      echo "             (backup preserved in $BAK_DIR/$rel_path)" >&2
    fi
  fi
}

# PLAN-138 Wave C (ADR-155): update ONE file under a classified directory walk.
# $1 = repo-relative file path. Backs up the dst file then copies src over it.
# Used by _per_file_classified_update for the FRAMEWORK-CHANGED / theirs / backup
# branches. find+delete idiom is unnecessary for a single file (plain cp).
_apply_single_file() {
  local rel="$1"
  local s="$SOURCE_DIR/$rel"
  local d="$TARGET/$rel"
  local b="$BAK_DIR/$rel"
  [[ -f "$s" ]] || return 0
  if [[ -e "$d" ]]; then
    mkdir -p "$( dirname "$b" )"
    cp "$d" "$b" 2>/dev/null || true
  fi
  mkdir -p "$( dirname "$d" )"
  cp "$s" "$d"
}

# PLAN-138 Wave C (ADR-155): per-file walk of a DIRECTORY target driven by the
# baseline classifier. Replaces the whole-tree delete+cp -R when a baseline
# manifest is loaded, so an adopter customization INSIDE a directory is
# preserved/refused per-file instead of being wiped. The union of source + dst
# files is walked so framework-added files land and removed-from-source files
# are reported (never auto-deleted — destructive removals stay manual).
_per_file_classified_update() {
  local rel_dir="$1"
  local sdir="$SOURCE_DIR/$rel_dir"
  local ddir="$TARGET/$rel_dir"
  local listing rel verdict
  # Build the union of relpaths under src + dst (regular files only).
  listing="$( {
    [[ -d "$sdir" ]] && find "$sdir" -type f -print 2>/dev/null | while IFS= read -r h; do printf '%s\n' "${h#"$SOURCE_DIR"/}"; done
    [[ -d "$ddir" ]] && find "$ddir" -type f -print 2>/dev/null | while IFS= read -r h; do printf '%s\n' "${h#"$TARGET"/}"; done
  } | LC_ALL=C sort -u )"

  printf '%s\n' "$listing" | while IFS= read -r rel; do
    [[ -n "$rel" ]] || continue
    if _path_is_skipped "$rel"; then
      echo "    SKIPPED (--skip): $rel"
      continue
    fi
    # Source-removed file: present at dst, absent at src. Report, never delete.
    if [[ ! -f "$SOURCE_DIR/$rel" ]]; then
      echo "    KEPT (no longer shipped by framework — not removed): $rel" >&2
      continue
    fi
    # New framework file: absent at dst. Just install it.
    if [[ ! -f "$TARGET/$rel" ]]; then
      _apply_single_file "$rel"
      echo "    ADDED: $rel"
      continue
    fi
    verdict="$( _classify_against_baseline "$rel" )"
    case "$verdict" in
      IDENTICAL)
        : ;;  # nothing to do
      FRAMEWORK-CHANGED)
        # Quiet auto-update is the intended path (dst matched the recorded
        # baseline => the adopter had not customized this file). BUT the manifest
        # is UNSIGNED/target-side (OQ-trust): a tampered line where H_base==H_dst
        # would mis-classify a customized file into this branch. We cannot detect
        # that without a signed manifest, so per Codex R1 P0#1 this is downgraded
        # to NON-SILENT: _apply_single_file always backs up the original first,
        # and we surface the overwrite + backup location on stderr (recoverable
        # AND visible — worst case equals today's warn-then-clobber).
        _apply_single_file "$rel"
        echo "    UPDATED (framework-changed; unsigned baseline — original backed up to $BAK_DIR/$rel): $rel" >&2
        ;;
      ADOPTER-CUSTOMIZED)
        echo "    PRESERVED (ADOPTER-CUSTOMIZED — not overwritten): $rel" >&2
        ;;
      CONFLICT)
        case "$ON_CONFLICT" in
          theirs)
            _apply_single_file "$rel"
            echo "    OVERWROTE (CONFLICT, --on-conflict=theirs): $rel" >&2
            ;;
          backup)
            _apply_single_file "$rel"
            echo "    OVERWROTE (CONFLICT, --on-conflict=backup; original in $BAK_DIR/$rel): $rel" >&2
            ;;
          *)  # refuse (default): per-file skip-and-report-and-CONTINUE
            echo "    REFUSED (CONFLICT, --on-conflict=refuse — not overwritten): $rel" >&2
            ;;
        esac
        ;;
      FALLBACK|*)
        # No usable baseline for this file — today's diff -q warn-then-clobber.
        if [[ "$DIFF_WARN" -eq 1 ]] && ! diff -q "$TARGET/$rel" "$SOURCE_DIR/$rel" >/dev/null 2>&1; then
          echo "    WARNING: adopter customization in $rel will be OVERWRITTEN (no baseline)" >&2
          echo "             (backup preserved in $BAK_DIR/$rel)" >&2
        fi
        _apply_single_file "$rel"
        echo "    UPDATED (fallback): $rel"
        ;;
    esac
  done
}

backup_and_replace() {
  local rel_path="$1"
  local src="$SOURCE_DIR/$rel_path"
  local dst="$TARGET/$rel_path"
  local bak="$BAK_DIR/$rel_path"

  if [[ ! -e "$src" ]]; then
    echo "    SKIP (source missing): $rel_path"
    return
  fi

  _up_record_op "refresh_target" "$rel_path"

  # F-CHAOS-3: warn the Owner about any customization we're about to
  # clobber, BEFORE the overwrite takes place. The backup under
  # $BAK_DIR is still the rollback path, but the warning surfaces the
  # diff at the moment it happens — without requiring the Owner to
  # notice it via `git diff` later.
  _emit_diff_warnings "$rel_path"

  # Honour --skip for top-level files/dirs too
  if _path_is_skipped "$rel_path"; then
    echo "    SKIPPED (--skip): $rel_path"
    return
  fi

  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "    (dry-run) would BACKUP + UPDATE: $rel_path"
    return
  fi

  # PLAN-138 Wave C (ADR-155): when this is a DIRECTORY target AND a baseline
  # manifest is loaded, do a per-file classified walk so adopter customizations
  # inside the tree are preserved/refused instead of wiped by delete+cp -R.
  # Falls through to the legacy whole-tree path for FILE targets or when no
  # manifest is present (fail-open to today's behavior). The whole-tree backup
  # below still runs first so $BAK_DIR holds the pre-upgrade tree for rollback.
  if [[ -d "$dst" && -d "$src" && -n "$_BASELINE_MANIFEST_FILE" ]]; then
    if [[ -e "$dst" ]]; then
      mkdir -p "$( dirname "$bak" )"
      cp -R "$dst" "$bak"
      echo "    BACKED UP: $rel_path"
    fi
    _per_file_classified_update "$rel_path"
    echo "    UPDATED (per-file classified): $rel_path"
    return
  fi

  # PLAN-138 Wave C (ADR-155): single-FILE target with a baseline loaded —
  # classify it too (e.g. .claude/task-chains.yaml, .claude/team.md). Preserve
  # an ADOPTER-CUSTOMIZED file / refuse a CONFLICT instead of clobbering.
  if [[ -f "$dst" && -f "$src" && -n "$_BASELINE_MANIFEST_FILE" ]]; then
    local _bfr_verdict
    _bfr_verdict="$( _classify_against_baseline "$rel_path" )"
    case "$_bfr_verdict" in
      IDENTICAL)
        return ;;
      ADOPTER-CUSTOMIZED)
        echo "    PRESERVED (ADOPTER-CUSTOMIZED — not overwritten): $rel_path" >&2
        return ;;
      CONFLICT)
        case "$ON_CONFLICT" in
          theirs|backup)
            _apply_single_file "$rel_path"
            echo "    OVERWROTE (CONFLICT, --on-conflict=$ON_CONFLICT; original in $BAK_DIR/$rel_path): $rel_path" >&2
            return ;;
          *)
            echo "    REFUSED (CONFLICT, --on-conflict=refuse — not overwritten): $rel_path" >&2
            return ;;
        esac ;;
      FRAMEWORK-CHANGED)
        _apply_single_file "$rel_path"
        echo "    UPDATED (framework-changed): $rel_path"
        return ;;
      FALLBACK|*)
        : ;;  # fall through to legacy whole-file path below
    esac
  fi

  if [[ -e "$dst" ]]; then
    mkdir -p "$( dirname "$bak" )"
    if [[ -d "$dst" ]]; then
      cp -R "$dst" "$bak"
    else
      cp "$dst" "$bak"
    fi
    echo "    BACKED UP: $rel_path"
  fi

  if [[ -d "$dst" ]]; then
    # Use find+delete instead of rm -rf to satisfy safety hooks on dev machines
    find "$dst" -mindepth 1 -delete
    rmdir "$dst"
  elif [[ -e "$dst" ]]; then
    rm -f "$dst"
  fi

  mkdir -p "$( dirname "$dst" )"
  if [[ -d "$src" ]]; then
    cp -R "$src" "$dst"
  else
    cp "$src" "$dst"
  fi
  echo "    UPDATED: $rel_path"
}

# DevOps-P1-4: refresh PROTOCOL.md pointer on upgrade. This is
# framework-derived content (not user data), so preserving it as-is
# across upgrades traps stale pointers when the framework moves. We
# regenerate it with the same heuristic install.sh uses.
_refresh_protocol_pointer() {
  local pointer="$TARGET/PROTOCOL.md"
  local body
  case "$SOURCE_DIR" in
    "$TARGET"/*)
      local rel="${SOURCE_DIR#$TARGET/}"
      body="The full CEO orchestration protocol lives at:
./${rel}/PROTOCOL.md

To pull updates:
  ( cd ./${rel} && git pull )
  ./${rel}/scripts/upgrade.sh . --profile $PROFILE --stack $STACK"
      ;;
    *)
      body="The full CEO orchestration protocol lives at:
{{PROTOCOL_SOURCE}}/PROTOCOL.md

Edit {{PROTOCOL_SOURCE}} to point at your ceo-orchestration checkout
(e.g. ../ceo-orchestration or \$HOME/src/ceo-orchestration).

To pull updates:
  ( cd {{PROTOCOL_SOURCE}} && git pull )
  {{PROTOCOL_SOURCE}}/scripts/upgrade.sh $TARGET --profile $PROFILE --stack $STACK"
      ;;
  esac

  # PLAN-138 C.7 fix (Codex R2 P0): compute the CANONICAL pointer hash — the
  # hash of exactly what the framework WOULD write below (heredoc body) — and
  # export it so the post-upgrade manifest rewrite records THAT as the
  # PROTOCOL.md baseline, never the current target file. Without this, a
  # preserved adopter-customized PROTOCOL.md would be re-recorded as its own
  # baseline and the NEXT upgrade would read H_dst==H_base and clobber it.
  # Computed on ALL paths (preserve + refresh) so it is set whenever the C.7
  # rewrite runs. printf reproduces the heredoc byte-for-byte.
  _REFRESH_PROTOCOL_CANON_HASH=""
  if command -v _hash_stdin >/dev/null 2>&1; then
    _REFRESH_PROTOCOL_CANON_HASH="$( printf '# Protocol reference\n\n%s\n' "$body" | _hash_stdin 2>/dev/null || true )"
  fi

  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "    (dry-run) would REFRESH: PROTOCOL.md pointer"
    return 0
  fi

  _up_record_op "refresh_protocol_pointer" "PROTOCOL.md"

  # PLAN-138 Wave C (ADR-155) C.6 — close the verified S238 driver.
  #
  # (a) ALWAYS back up an existing root PROTOCOL.md to $BAK_DIR/PROTOCOL.md
  #     BEFORE the `cat >` overwrite. The legacy code had NO backup here, so an
  #     adopter who turned the pointer into a real customized protocol (the
  #     S238 acme case) lost it irrecoverably. This backup applies EVEN when
  #     no baseline manifest exists — making the loss recoverable on a first
  #     upgrade (Codex R1 P0 first-upgrade safety).
  if [[ -f "$pointer" ]]; then
    mkdir -p "$BAK_DIR" 2>/dev/null || true
    cp "$pointer" "$BAK_DIR/PROTOCOL.md" 2>/dev/null || true
    echo "    BACKED UP: PROTOCOL.md (root) -> $BAK_DIR/PROTOCOL.md"
  fi

  # (b) When a baseline manifest is loaded, classify the root PROTOCOL.md
  #     against the recorded install-time pointer hash. The pointer's "source"
  #     is a generated string (not a file in $SOURCE_DIR), so we compare the
  #     CURRENT target hash against the recorded BASELINE only:
  #       H_dst == H_base  -> still the generated pointer -> safe to refresh
  #       H_dst != H_base  -> adopter customized it -> ADOPTER-CUSTOMIZED:
  #                           preserve (default/refuse) or overwrite per
  #                           --on-conflict={theirs|backup}.
  if [[ -f "$pointer" && -n "$_BASELINE_MANIFEST_FILE" ]] && command -v _hash_file >/dev/null 2>&1; then
    local _rp_base _rp_dst
    _rp_base="$( _baseline_lookup "PROTOCOL.md" || true )"
    _rp_dst="$( _hash_file "$pointer" 2>/dev/null || true )"
    if [[ -n "$_rp_base" && -n "$_rp_dst" && "$_rp_dst" != "$_rp_base" ]]; then
      case "$ON_CONFLICT" in
        theirs|backup)
          # Original already backed up above; proceed to refresh.
          echo "    OVERWROTE (root PROTOCOL.md ADOPTER-CUSTOMIZED, --on-conflict=$ON_CONFLICT; original in $BAK_DIR/PROTOCOL.md)" >&2
          ;;
        *)  # refuse (default): preserve the customized root PROTOCOL.md.
          echo "    PRESERVED (root PROTOCOL.md ADOPTER-CUSTOMIZED — pointer NOT refreshed; backup in $BAK_DIR/PROTOCOL.md)" >&2
          return 0
          ;;
      esac
    fi
  fi

  cat > "$pointer" <<EOF
# Protocol reference

$body
EOF
  echo "    REFRESHED: PROTOCOL.md pointer"
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

# ---------------------------------------------------------------------------
# PLAN-135 W1 (unit w0r) — pre-flight model-deprecation advisory.
# Runs check-model-deprecations.py --check against the TARGET when the checker
# is available (source copy preferred — fresher ledger; falls back to the
# target's installed copy). NEVER blocks the upgrade: findings emit stderr
# WARNING lines (F-CHAOS-3 convention); any infra failure (no python3, corrupt
# ledger, unexpected rc) degrades to a NOTE and the upgrade proceeds
# (fail-open per CLAUDE.md §5). Suppress with --no-deprecation-warn.
# ---------------------------------------------------------------------------
_emit_deprecation_warnings() {
  [[ "$DEPRECATION_WARN" -eq 1 ]] || return 0
  local checker=""
  if [[ -f "$SOURCE_DIR/.claude/scripts/check-model-deprecations.py" ]]; then
    checker="$SOURCE_DIR/.claude/scripts/check-model-deprecations.py"
  elif [[ -f "$TARGET/.claude/scripts/check-model-deprecations.py" ]]; then
    checker="$TARGET/.claude/scripts/check-model-deprecations.py"
  fi
  [[ -n "$checker" ]] || return 0
  if ! command -v python3 >/dev/null 2>&1; then
    echo "    NOTE: model-deprecation scan skipped (python3 not found) — advisory only" >&2
    return 0
  fi
  local dep_rc=0
  python3 "$checker" --check "$TARGET" >/dev/null 2>&1 || dep_rc=$?
  if [[ "$dep_rc" -eq 1 ]]; then
    echo "    WARNING: deprecated/retiring Claude model ids detected in target" >&2
    echo "             (already retired, or <=60 days to retirement). Full report:" >&2
    echo "             python3 $checker $TARGET" >&2
  elif [[ "$dep_rc" -ne 0 ]]; then
    echo "    NOTE: model-deprecation scan inconclusive (rc=$dep_rc) — advisory only" >&2
  fi
  return 0
}

_emit_deprecation_warnings

# ---------------------------------------------------------------------------
# PLAN-135 W2 (unit h8) — idempotent settings-merge: register new framework
# lifecycle hooks into the adopter's EXISTING .claude/settings.json.
#
# WHY THIS EXISTS (constraint b, debate R1): install.sh EXISTS-SKIPs an
# existing settings.json, so a hook that is only baked into the fresh-install
# template (settings.base.json) NEVER reaches the S217 population of existing
# adopters. Without this step the Setup/init self-verification hook would be a
# silent no-op for every already-installed repo. We therefore merge the new
# registration(s) into the live settings.json here, at upgrade time, in the
# SAME ceremony.
#
# This registers the FIVE new W2 lifecycle events: PreCompact + PostCompact
# (check_precompact_continuity.py / check_postcompact_reinject.py), ConfigChange
# (check_config_change.py), SubagentStart (check_subagent_start.py), and
# Setup/init (check_setup_verification.py). The jq program is IDEMPOTENT (per
# event: filters any pre-existing block that registers the hook, then
# re-appends the single canonical block) so re-running the upgrade is a no-op.
# It is ADDITIVE — existing settings keys + hooks are preserved untouched.
#
# Fail-open per CLAUDE.md §5: no jq, malformed settings, or a merge error =>
# stderr NOTE + the upgrade proceeds. A backup of the pre-merge settings.json
# is written under $BAK_DIR first so the Owner can always roll back.
# Suppress entirely with --no-settings-merge.
# ---------------------------------------------------------------------------
_merge_lifecycle_hooks_into_settings() {
  [[ "$SETTINGS_MERGE" -eq 1 ]] || return 0
  local settings="$TARGET/.claude/settings.json"
  if [[ ! -f "$settings" ]]; then
    echo "    NOTE: settings-merge skipped — no $settings (fresh install builds it from template)" >&2
    return 0
  fi
  if ! command -v jq >/dev/null 2>&1; then
    echo "    NOTE: settings-merge skipped (jq not found) — register the Setup hook manually; advisory only" >&2
    return 0
  fi

  echo ""
  echo "==> Registering new lifecycle hooks into .claude/settings.json (PLAN-135 W2 H8)"
  _up_record_op "merge_lifecycle_hooks" "additive settings.json merge"

  # Idempotent jq program — mirrors staged merges/{60,62,64,70}-*.jq. Registers
  # ALL FIVE new W2 lifecycle hooks (Codex V2 P2: registering only Setup left
  # PreCompact/PostCompact/ConfigChange/SubagentStart dead for upgraded
  # adopters). The `_reg` helper filters any pre-existing entry that registers
  # the hook filename, then re-appends the single canonical block — so each
  # event is idempotent and every other settings key/hook is preserved.
  local jq_prog
  jq_prog='
def _reg($event; $name; $entry):
  .hooks[$event] = (
    [ (.hooks[$event] // [])[]
      | select(([.hooks[]? | .command // ""] | map(test($name)) | any) | not) ]
    + [$entry]
  );
.hooks = (.hooks // {})
| _reg("PreCompact"; "check_precompact_continuity\\.py"; {
    "_comment": "PLAN-135 W2 H1 (ADR-153): PreCompact continuity snapshot — plan-id + execution-unit + ceremony flags + HMAC-chain anchor to the plan scratchpad before the transcript collapses. ADVISORY, fail-open. Kill: CEO_COMPACTION_CONTINUITY=0.",
    "matcher": "",
    "hooks": [ { "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh\" check_precompact_continuity.py", "timeout": 5, "statusMessage": "Snapshotting governance state before compaction..." } ]
  })
| _reg("PostCompact"; "check_postcompact_reinject\\.py"; {
    "_comment": "PLAN-135 W2 H1 (ADR-153): PostCompact governance reinjection — reinjects governance POINTERS (active PLAN, unit position, Gate-1 reminder) via additionalContext after compaction. POINTERS ONLY, never file contents. ADVISORY, fail-open. Kill: CEO_COMPACTION_CONTINUITY=0.",
    "matcher": "",
    "hooks": [ { "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh\" check_postcompact_reinject.py", "timeout": 5, "statusMessage": "Reinjecting governance pointers after compaction..." } ]
  })
| _reg("ConfigChange"; "check_config_change\\.py"; {
    "_comment": "PLAN-135 W2 H2: ConfigChange guard — advisory audit + advisory-block of out-of-band settings tamper (the S197 class) via _lib/effective_config. Fail-open, never blocks on infra. Kill: CEO_CONFIG_CHANGE_GUARD=0.",
    "matcher": "",
    "hooks": [ { "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh\" check_config_change.py", "timeout": 5, "statusMessage": "Checking config change for tamper..." } ]
  })
| _reg("SubagentStart"; "check_subagent_start\\.py"; {
    "_comment": "PLAN-135 W2 H3: SubagentStart lifecycle recorder — spawn instant + context into a local sidecar (raw agent_id never persisted); the SubagentStop half consumes it for the per-agent bracket. ADVISORY, fail-open. Kill: CEO_SUBAGENT_LIFECYCLE=0.",
    "matcher": "",
    "hooks": [ { "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh\" check_subagent_start.py", "timeout": 5, "statusMessage": "Recording sub-agent spawn instant..." } ]
  })
| _reg("Setup"; "check_setup_verification\\.py"; {
    "_comment": "PLAN-135 W2 H8: Setup-event post-install self-verification (init matcher) — validate-governance --fast + verify-counts + hook exec-bits (the S228 exec-bit class) + CLAUDE_ENV_FILE allowlist persistence (explicit CEO_* include-list; every override/escape-hatch/kill-switch EXCLUDED, S185/S197 stale-override class). ADVISORY + fail-open; NEVER blocks. Kill-switch: CEO_SETUP_VERIFICATION=0.",
    "matcher": "init",
    "hooks": [ { "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh\" check_setup_verification.py", "timeout": 15, "statusMessage": "Post-install self-verification..." } ]
  })'

  if [[ "$DRY_RUN" -eq 1 ]]; then
    local _missing=0 _ev _name
    for pair in "PreCompact:check_precompact_continuity" "PostCompact:check_postcompact_reinject" "ConfigChange:check_config_change" "SubagentStart:check_subagent_start" "Setup:check_setup_verification"; do
      _ev="${pair%%:*}"; _name="${pair##*:}"
      if ! jq -e --arg ev "$_ev" --arg n "$_name" '(.hooks[$ev] // []) | map(.hooks[]?.command // "" | test($n + "\\.py")) | any' "$settings" >/dev/null 2>&1; then
        echo "    (dry-run) would REGISTER $_ev $_name.py"
        _missing=$((_missing+1))
      fi
    done
    [[ "$_missing" -eq 0 ]] && echo "    (dry-run) all 5 W2 lifecycle hooks ALREADY registered — would be a no-op"
    return 0
  fi

  # Backup before the additive merge (rollback path).
  mkdir -p "$BAK_DIR/.claude" 2>/dev/null || true
  cp "$settings" "$BAK_DIR/.claude/settings.json.pre-h8-merge" 2>/dev/null || true

  local tmp
  tmp="$(mktemp "$settings.upgrade-merge.XXXXXX")" || {
    echo "    NOTE: settings-merge skipped (mktemp failed) — advisory only" >&2
    return 0
  }
  if jq "$jq_prog" "$settings" > "$tmp" 2>/dev/null && [[ -s "$tmp" ]]; then
    if mv "$tmp" "$settings"; then
      echo "    REGISTERED: 5 W2 lifecycle hooks — PreCompact, PostCompact, ConfigChange, SubagentStart, Setup/init (idempotent — re-runs are no-ops)"
    else
      rm -f "$tmp"
      echo "    NOTE: settings-merge atomic mv failed — settings.json unchanged; advisory only" >&2
    fi
  else
    rm -f "$tmp"
    echo "    NOTE: settings-merge jq failed (malformed settings.json?) — settings.json unchanged;" >&2
    echo "          backup at $BAK_DIR/.claude/settings.json.pre-h8-merge; advisory only" >&2
  fi
  return 0
}

# Team rosters (templates — user may have customized, still overwrite with backup so they can diff)
backup_and_replace ".claude/team.md"
backup_and_replace ".claude/frontend-team.md"

# Skills per profile
if has_profile "core"; then
  backup_and_replace ".claude/skills/core"
fi
if has_profile "frontend"; then
  backup_and_replace ".claude/skills/frontend"
fi
for part in "${PROFILE_PARTS[@]}"; do
  if [[ "$part" != "core" && "$part" != "frontend" ]]; then
    if [[ -d "$SOURCE_DIR/.claude/skills/domains/$part" ]]; then
      backup_and_replace ".claude/skills/domains/$part"
    else
      echo "    WARNING: domain '$part' not found — skipping"
    fi
  fi
done

# Protocol enforcement
backup_and_replace ".claude/hooks"
backup_and_replace ".claude/scripts"
backup_and_replace ".claude/commands"
backup_and_replace ".claude/pitfalls-catalog.yaml"
backup_and_replace ".claude/task-chains.yaml"
# agent-metrics.md preserved (user data). settings.json is preserved here too —
# the PLAN-135 W2 H8 settings-merge step below is the ONLY thing that touches it,
# and only additively (registers new framework lifecycle hooks; never clobbers).

# ===========================================================================
# PLAN-020 Phase 1 (ADR-050) — native subagents canonical-5 preservation
# ---------------------------------------------------------------------------
# Replace ONLY the 5 canonical-5 native agent files we ship. Adopter-
# authored .claude/agents/custom-*.md or any other adopter-named files
# are PRESERVED (not touched, not backed up). This protects adopter
# extensions while still letting framework upgrades land canonical
# changes.
# ===========================================================================
upgrade_agents_canonical_only() {
  local CANONICAL_AGENTS=(
    "code-reviewer.md"
    "security-engineer.md"
    "qa-architect.md"
    "performance-engineer.md"
    "devops.md"
  )
  if [[ ! -d "$SOURCE_DIR/.claude/agents" ]]; then
    echo "    NOTE: source has no .claude/agents/ — skipping native rail"
    return 0
  fi
  echo ""
  echo "==> Upgrading native subagent canonical-5 (ADR-050 + ADR-052)"
  _up_record_op "upgrade_agents_canonical_only" "canonical-5"
  mkdir -p "$TARGET/.claude/agents"
  for name in "${CANONICAL_AGENTS[@]}"; do
    local SRC="$SOURCE_DIR/.claude/agents/$name"
    local DST="$TARGET/.claude/agents/$name"
    if [[ -f "$SRC" ]]; then
      # PLAN-021 ADR-052: preserve adopter model override.
      # Detect if adopter customized the model: field vs framework default.
      local adopter_model=""
      local framework_model=""
      if [[ -f "$DST" ]]; then
        adopter_model=$(grep -E "^model:" "$DST" | head -1 || true)
        framework_model=$(grep -E "^model:" "$SRC" | head -1 || true)
        cp "$DST" "$BAK_DIR/agents-$name.bak" 2>/dev/null || true
      fi
      cp "$SRC" "$DST"

      # If adopter had a custom model override, restore it in the
      # refreshed file. Only triggers when the adopter's model line
      # differs from the framework baseline for this agent.
      if [[ -n "$adopter_model" && -n "$framework_model" \
            && "$adopter_model" != "$framework_model" ]]; then
        # Replace the framework model line with adopter's choice.
        # Portable BSD/GNU sed in-place edit via temp file.
        local tmp
        tmp=$(mktemp)
        awk -v old="$framework_model" -v new="$adopter_model" '
          $0 == old { print new; next }
          { print }
        ' "$DST" > "$tmp" && mv "$tmp" "$DST"
        echo "    canonical-5: refreshed $name (ADR-052 adopter model override PRESERVED: $adopter_model)"
      else
        echo "    canonical-5: refreshed $name"
      fi
    fi
  done
  echo "    PLAN-020 native-subagent rail installed; set CEO_NATIVE_SUBAGENTS=0 to opt out"
  echo "    PLAN-021 multi-model dispatch active; set CEO_MULTIMODEL_ENABLE=0 to force all-Opus"
}

upgrade_agents_canonical_only

# PLAN-135 W2 H8: register new lifecycle hooks (Setup/init self-verification)
# into the adopter's existing settings.json (install.sh would EXISTS-SKIP it).
_merge_lifecycle_hooks_into_settings

# DevOps-P1-4: PROTOCOL.md is framework-derived (pointer), not user data —
# refresh it so it stays aligned with the current source layout.
echo ""
echo "==> Refreshing PROTOCOL.md pointer"
_refresh_protocol_pointer

# PLAN-138 Wave C (ADR-155) C.7 — (re)write the baseline manifest AFTER a
# successful upgrade, so a long-lived adopter who upgrades but never re-runs
# install.sh (the S238 acme population) acquires/refreshes a manifest. The
# NEXT upgrade then runs the manifest-present per-file classified path instead
# of the fallback. Uses the SAME shared generator install.sh calls. Skipped on
# --dry-run; fail-open (a generator problem emits a NOTE, never aborts).
if [[ "$DRY_RUN" -eq 0 ]] && command -v _write_baseline_manifest >/dev/null 2>&1; then
  echo ""
  echo "==> (Re)writing install baseline manifest (.claude/.install-manifest.sha256)"
  _up_record_op "rewrite_baseline_manifest" ".claude/.install-manifest.sha256"
  export FMS_ROOT="$TARGET"            # enumerate what the target holds post-upgrade
  export FMS_HASH_ROOT="$SOURCE_DIR"   # but record the FRAMEWORK hash, not the
                                       # (possibly customized-and-preserved) target
                                       # file — else the next upgrade clobbers it
                                       # (C.5 idempotency fix). PROTOCOL.md pointer
                                       # still hashes from FMS_ROOT inside the gen.
  export FMS_PROFILE_PARTS="${PROFILE_PARTS[*]}"
  export FMS_MODE="copy"   # upgrade.sh always copies (never --mode link)
  # Canonical PROTOCOL.md pointer hash (Codex R2 P0): record what the framework
  # WOULD generate, never a preserved adopter customization. Empty if the
  # pointer refresh did not run; the generator then falls back to hashing the
  # target (install semantics).
  export FMS_PROTOCOL_HASH="${_REFRESH_PROTOCOL_CANON_HASH:-}"
  _write_baseline_manifest "$TARGET/.claude/.install-manifest.sha256"
  unset FMS_ROOT FMS_HASH_ROOT FMS_PROFILE_PARTS FMS_MODE FMS_PROTOCOL_HASH
fi

# ===========================================================================
# PLAN-153 Wave B item B2 — (re)write the install-state after a successful
# upgrade, mirroring the ADR-155 decision-(iv) manifest rewrite above: a
# pre-Wave-B adopter (no state file) ACQUIRES one on their first post-Wave-B
# upgrade, so the NEXT upgrade can replay. Merge semantics preserve the
# ORIGINAL install request (argv, mode, ceremony, placeholders map) and only
# update the replayable fields (request.profile/request.stack) to the values
# THIS run effectively used; the upgrade run itself is recorded under
# last_upgrade + history. Atomic (same-directory tempfile + os.replace),
# schema ceo.install-state/v1, fail-open (a write problem emits a NOTE and
# never aborts the completed upgrade). Skipped on --dry-run.
_write_upgrade_state() {
  [[ "$DRY_RUN" -eq 0 ]] || return 0
  if ! command -v python3 >/dev/null 2>&1; then
    echo "    NOTE: install-state not (re)written (python3 not found) — the next upgrade uses the ADR-155 fallback path" >&2
    return 0
  fi
  local fw_version=""
  if [[ -f "$SOURCE_DIR/VERSION" ]]; then
    fw_version="$(tr -d '[:space:]' < "$SOURCE_DIR/VERSION" 2>/dev/null || true)"
  fi
  local pairs=(
    "target" "$TARGET"
    "profile" "$PROFILE"
    "stack" "$STACK"
    "on_conflict" "$ON_CONFLICT"
    "pin" "$PIN_REF"
    "replay_source" "$_REPLAY_SOURCE"
  )
  echo ""
  echo "==> (Re)writing install-state (.claude/.install-state.json — PLAN-153 Wave B)"
  if ! PYTHONNOUSERSITE=1 python3 -I -c '
import json, os, sys, tempfile, time
args = sys.argv[1:]
state_path, ops_path, fw_version = args[0], args[1], args[2]
n = int(args[3]); kv = args[4:4 + n]; up_argv = list(args[4 + n:])
vals = {}
i = 0
while i + 1 < len(kv):
    vals[kv[i]] = kv[i + 1]; i += 2
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
first, run_count, history, req = now, 1, [], None
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
    pr = prev.get("request")
    if isinstance(pr, dict):
        req = pr
    pt = prev.get("tool"); pw = prev.get("written_at")
    history.append({
        "at": pw if isinstance(pw, str) else "",
        "tool": (pt.get("name", "") if isinstance(pt, dict) else ""),
        "profile": (req.get("profile", "") if isinstance(req, dict) else ""),
        "stack": (req.get("stack", "") if isinstance(req, dict) else ""),
    })
    history = history[-20:]
if req is None:
    req = {
        "argv": [],
        "target": vals.get("target", ""),
        "placeholders": {},
        "note": "synthesized by upgrade.sh - no pre-Wave-B install.sh record existed (back-compat path)",
    }
req["profile"] = vals.get("profile", "")
req["stack"] = vals.get("stack", "")
state = {
    "schema": "ceo.install-state/v1",
    "schema_version": 1,
    "written_at": now,
    "first_recorded_at": first,
    "run_count": run_count,
    "tool": {"name": "upgrade.sh", "framework_version": fw_version},
    "request": req,
    "last_upgrade": {
        "at": now,
        "argv": up_argv,
        "profile": vals.get("profile", ""),
        "stack": vals.get("stack", ""),
        "on_conflict": vals.get("on_conflict", ""),
        "pin": vals.get("pin", ""),
        "replay_source": vals.get("replay_source", ""),
    },
    "operations": ops,
    "result": {"upgrade_succeeded": True,
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
' "$_INSTALL_STATE_FILE" "${_UP_OPS_FILE:-}" "$fw_version" "${#pairs[@]}" "${pairs[@]}" \
    ${ORIG_UP_ARGV[@]+"${ORIG_UP_ARGV[@]}"} 2>/dev/null; then
    echo "    NOTE: install-state write failed — the next upgrade falls back to the ADR-155 path (fail-open)" >&2
  else
    echo "    WROTE: .claude/.install-state.json (schema ceo.install-state/v1, atomic)"
  fi
  if [[ -n "${_UP_OPS_FILE:-}" ]]; then rm -f "$_UP_OPS_FILE" 2>/dev/null || true; fi
  return 0
}
_write_upgrade_state

echo ""
echo "==> Upgrade complete."
echo "    Preserved: CLAUDE.md, MEMORY.md, .claude/agent-metrics.md (and existing"
echo "    .claude/settings.json keys — only NEW framework lifecycle hooks were"
echo "    additively registered into it; see PLAN-135 W2 H8 above)."
echo "    To roll back, restore from: $BAK_DIR"
echo "    (pre-merge settings.json backup: $BAK_DIR/.claude/settings.json.pre-h8-merge)"
echo ""
echo "    NOTE: The settings-merge step (PLAN-135 W2) only ADDS missing framework"
echo "    lifecycle hooks idempotently; it never rewrites your custom keys. If you"
echo "    want a full rebuild from the latest template instead (e.g. settings.base.json"
echo "    or settings.stack.$STACK.json changed structurally upstream), back up and"
echo "    re-run install.sh manually:"
echo "      cp $TARGET/.claude/settings.json $TARGET/.claude/settings.json.bak"
echo "      rm $TARGET/.claude/settings.json"
echo "      $SCRIPT_DIR/install.sh $TARGET --profile $PROFILE --stack $STACK"
