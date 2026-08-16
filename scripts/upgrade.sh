#!/usr/bin/env bash
# upgrade.sh — update an existing ceo-orchestration install in a target repo
#
# Usage:
#   ./upgrade.sh <target-repo-path> [--profile <list>] [--stack <name>]
#                                    [--pin <tag>] [--dry-run]
#                                    [--skip <glob>] [--no-diff-warn]
#                                    [--no-deprecation-warn]
#                                    [--ceremony <maintainer|user>]
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
#   - (PLAN-163 T5.4) BASELINE-AWARE SETTINGS MIGRATION: availableModels,
#     fallbackModel and permissions.defaultMode are migrated with an explicit
#     IDEMPOTENT 3-state policy PER LEAF KEY (absent -> write the new
#     baseline; equal to the OLD baseline (arrays byte-compared, exact order)
#     -> updated to the new baseline; customized -> PRESERVED + a named
#     WARNING). The new DirectoryAdded/Notification hook registrations are
#     added only when not yet registered AND the T3.4 version-floor feature
#     gate is on; customized registrations under the same events are always
#     preserved. Opt out with --no-settings-migrate. Oracles derive their
#     expectations from `upgrade.sh --print-settings-baselines` (the
#     normative table IS the artifact — literals are never re-hardcoded).
#   - (PLAN-164 W1, ADR-110-AMEND-1) PAIR-RAIL REGISTRATION-TIMEOUT VALUE
#     MIGRATION: the check_pair_rail.py PreToolUse registration timeout is
#     bumped to the template-derived cap IFF the adopter's current value is
#     one of the frozen SUPERSEDED SHIPPED caps (60 pre-PLAN-164; 150 from
#     PLAN-164/ADR-110-AMEND-1, shipped in v1.2.0 and superseded by
#     ADR-110-AMEND-2's 210); any other adopter-chosen value is
#     PRESERVED + a named WARNING; idempotent. Runs inside the same T5.4
#     migration step (same opt-out, same --dry-run preview); the NEW cap is
#     derived from templates/settings/settings.base.json, never hardcoded.
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
# PLAN-155 Wave 5 — codex harness emission helper (sourced, not executed).
# Fail-open: absent => --harness codex round-trip degrades to a warning.
if [ -f "$SCRIPT_DIR/_codex_harness.sh" ]; then
  # shellcheck source=scripts/_codex_harness.sh
  . "$SCRIPT_DIR/_codex_harness.sh"
fi

# PLAN-156 Wave 4 — Grok harness (sourced). Fail-open: absent => --harness
# grok round-trip degrades to a warning (mirrors the codex source above).
if [ -f "$SCRIPT_DIR/_grok_harness.sh" ]; then
  # shellcheck source=scripts/_grok_harness.sh
  . "$SCRIPT_DIR/_grok_harness.sh"
fi

# ===========================================================================
# PLAN-163 T5.4 — settings baseline-migration NORMATIVE TABLE (W0b literals).
# ---------------------------------------------------------------------------
# ONE source of truth for the baseline-aware settings migration below
# (_migrate_settings_baseline). Oracles derive their expectations from
# `upgrade.sh --print-settings-baselines` (this exact JSON) instead of
# hardcoding the literals — keep the table and the migration in lockstep.
# Order is NORMATIVE: new model ids are APPENDED AT THE END (the arrays are
# byte-compared and the first entry participates in default resolution —
# ADR-149:95-102; mirror test :127-149,193-200); any other order needs an
# ADR-181 justification. permissions.defaultMode follows the exact read
# contract of _lib/effective_config.py:178-180,534-542 (stripped string).
# The top-level scalar "model" leaf (the CC 2.1.220 session-default pin,
# ADR-181 T1.1) has NO old-baseline value — old installs carry NO top-level
# "model" key at all ("old": null documents that ABSENCE). Absence therefore
# IS the old baseline: it is migrated to the new pin (claude-opus-5), closing
# the T1.1 silent-flip (adding claude-sonnet-5 to availableModels must not
# re-flip the session default) — BUT ONLY when claude-opus-5 is actually in
# the resulting effective availableModels. C6 (codex R4): if an adopter has
# CUSTOMIZED availableModels to a set that EXCLUDES claude-opus-5, setting the
# pin would place it outside the allowlist and enforceAvailableModels would
# reject it, so in that case the pin is NOT set and a named warning is emitted
# (session default left to the adopter/harness). In the normal migrated case
# claude-opus-5 IS present, so the pin is set and enforceAvailableModels
# accepts it. Any PRESENT model value != the new pin is adopter-custom and
# PRESERVED with a named warning (never re-flipped).
# Each registration carries a "match" filename used for the idempotent
# append (mirrors the H8 jq `_reg` semantics: an event entry whose
# hooks[].command references the filename counts as already registered).
_T54_BASELINES_JSON='{
  "availableModels": {
    "old": ["claude-opus-4-8","claude-fable-5","claude-sonnet-4-6","claude-haiku-4-5"],
    "new": ["claude-opus-4-8","claude-fable-5","claude-sonnet-4-6","claude-haiku-4-5","claude-opus-5","claude-sonnet-5"]
  },
  "fallbackModel": {
    "old": ["claude-opus-4-8"],
    "new": ["claude-opus-5"]
  },
  "model": {
    "old": null,
    "new": "claude-opus-5"
  },
  "permissions.defaultMode": {
    "old": "default",
    "new": "manual"
  },
  "registrations": {
    "DirectoryAdded": {
      "match": "check_directory_added.py",
      "entry": {
        "_comment": "PLAN-163 T3.1: DirectoryAdded observer-writer - records session-added workspace roots into the session-roots registry (and, where the harness supports a block decision, enforces the narrowed hardblock floor). Posture per the T3.1 blockability probe; fail-open on infra. Kill: CEO_DIRECTORY_ADDED_GUARD=0.",
        "matcher": "",
        "hooks": [ { "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh\" check_directory_added.py", "timeout": 5, "statusMessage": "Recording added workspace root..." } ]
      }
    },
    "Notification": {
      "match": "check_notification.py",
      "entry": {
        "_comment": "PLAN-163 T3.2: Notification lifecycle telemetry (agent_needs_input / agent_completed) -> typed audit emit with no-value-echo; feeds liveness telemetry. ADVISORY, fail-open. Kill: CEO_NOTIFICATION_TELEMETRY=0.",
        "matcher": "",
        "hooks": [ { "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh\" check_notification.py", "timeout": 5, "statusMessage": "Recording notification lifecycle event..." } ]
      }
    }
  }
}'

# PLAN-163 T3.4 FEATURE GATE — new-event registrations (DirectoryAdded,
# Notification). SUPPORT.md declares the adopter floor >=2.0; until the
# T3.4 version-floor probe (unknown-event-key tolerance on the floor
# version) is recorded — or the floor is explicitly raised with
# SUPPORT/install/upgrade kept coherent — emitting the new event keys into
# ADOPTER settings stays OFF. Flip _T34_VERSION_FLOOR_PROBE_PASSED to 1 in
# the SAME change that records the probe verdict
# ({{FILL-FROM-PROBES}}: T3.4 version-floor probe — pending at authoring
# time). Env override CEO_T34_NEW_EVENT_REGISTRATIONS={1|0} always wins
# (test seam + operator escape hatch). The gate NEVER affects the three
# model/permission leaf keys — those migrate regardless.
_T34_VERSION_FLOOR_PROBE_PASSED=0
_t34_new_event_registrations_enabled() {
  case "${CEO_T34_NEW_EVENT_REGISTRATIONS:-}" in
    1) return 0 ;;
    0) return 1 ;;
  esac
  [ "$_T34_VERSION_FLOOR_PROBE_PASSED" -eq 1 ]
}

# PLAN-153 Wave B item B2 — capture the ORIGINAL upgrade argv verbatim BEFORE
# parsing, for the post-upgrade state record (data only, never eval-ed).
ORIG_UP_ARGV=( "$@" )

TARGET=""
PROFILE="core,frontend"
STACK="none"
PIN_REF=""
DRY_RUN=0
PURGE_MISINSTALLED=0   # PLAN-161 U3: opt-in hash-gated purge of mis-installed framework-internal files
DIFF_WARN=1
DEPRECATION_WARN=1
SETTINGS_MERGE=1
SETTINGS_MIGRATE=1       # PLAN-163 T5.4: baseline-aware settings migration (opt out: --no-settings-migrate)
SETTINGS_MIGRATE_ONLY=0  # PLAN-163 T5.4: run ONLY the settings migration (test/ops seam)
ON_CONFLICT="refuse"   # PLAN-138 Wave C (ADR-155): {refuse|theirs|backup}; default refuse (OQ2)
REPLAY=1               # PLAN-153 Wave B item B2: replay the recorded install request (opt out: --no-replay)
HARNESS=""             # PLAN-155 Wave 5: "" = infer from recorded request.harness (B2 mirror)
HARNESS_EXPLICIT=0     # explicit --harness always beats a replayed value
CODEX_MANAGED_HOOKS=0  # replayed from request.managed_hooks unless --managed-hooks
# shellcheck disable=SC2034  # CODEX_WITH_SKILLS/CODEX_FORCE consumed by the sourced _codex_harness.sh
CODEX_WITH_SKILLS=0
# shellcheck disable=SC2034
CODEX_FORCE=0          # upgrade derives this from --on-conflict for the codex refresh
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
    --ceremony)
      # Re-pass rc.4 t3 (P1): explicit ceremony for PRE-STATE targets
      # (no readable .install-state.json). A RECORDED ceremony always
      # wins over this flag — the flag exists for the migration case.
      CEREMONY_FLAG="${2:-}"
      case "$CEREMONY_FLAG" in
        maintainer|user) : ;;
        *) echo "ERROR: --ceremony must be 'maintainer' or 'user' (got '$CEREMONY_FLAG')" >&2; exit 2 ;;
      esac
      shift 2
      ;;
    --purge-misinstalled)
      # PLAN-161 U3 (OQ1 Owner-ratified): opt-in, hash-gated purge of
      # mis-installed framework-internal excluded-tree files. NEVER default-on.
      PURGE_MISINSTALLED=1
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
    --no-settings-migrate)
      # PLAN-163 T5.4: skip the baseline-aware settings migration.
      SETTINGS_MIGRATE=0
      shift
      ;;
    --settings-migrate-only)
      # PLAN-163 T5.4: run ONLY the settings migration against <target>
      # and exit (test/ops seam; honors --dry-run + --no-settings-migrate).
      SETTINGS_MIGRATE_ONLY=1
      shift
      ;;
    --print-settings-baselines)
      # PLAN-163 T5.4: introspection for oracles — the normative baseline
      # table IS the artifact; tests parse this output (never hardcode).
      printf '%s\n' "$_T54_BASELINES_JSON"
      exit 0
      ;;
    --no-replay)
      # PLAN-153 Wave B item B2: ignore .claude/.install-state.json entirely.
      REPLAY=0
      shift
      ;;
    --harness)
      # PLAN-155 Wave 5: explicit override of the replayed harness.
      HARNESS="${2:-}"
      case "$HARNESS" in
        claude|codex|grok) ;;
        *) echo "ERROR: --harness must be 'claude', 'codex', or 'grok' (got: $HARNESS)" >&2; exit 2 ;;
      esac
      HARNESS_EXPLICIT=1
      shift 2
      ;;
    --managed-hooks)
      CODEX_MANAGED_HOOKS=1
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
  scripts/, commands/, pitfalls-catalog.yaml, task-chains.yaml, the
  SPEC/v1 contract (forced route, skipped on --ceremony user installs)
  and the .claude/.framework-version marker) in an existing adopter
  install. User-customized files (CLAUDE.md, MEMORY.md,
  .claude/agent-metrics.md) are NOT touched, and the root VERSION file
  is NEVER touched (install-time snapshot — ADR-155-AMEND-1; read
  .claude/.framework-version for the installed framework version). NOTE: .claude/settings.json IS
  updated in place by the default-on baseline migration (the model/permission
  leaf keys: model, availableModels, fallbackModel, permissions.defaultMode)
  and the idempotent settings-merge (new lifecycle-hook registrations) —
  adopter-CUSTOMIZED values are always preserved with a named warning, and a
  pre-migration backup is written to .claude.bak/. Opt out with
  --no-settings-migrate / --no-settings-merge to manage settings.json by hand.

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
  --no-settings-migrate PLAN-163 T5.4: skip the baseline-aware settings
                        migration (model, availableModels, fallbackModel,
                        permissions.defaultMode + T3.4-gated new-event
                        registrations). 3-state policy per LEAF KEY:
                        absent -> write the new baseline; equal to the OLD
                        baseline (byte-compared) -> update; customized ->
                        PRESERVE + named WARNING. Idempotent + fail-open;
                        never blocks the upgrade.
  --settings-migrate-only
                        Run ONLY the T5.4 settings baseline migration
                        against <target-repo-path> and exit 0 (test/ops
                        seam; honors --dry-run + --no-settings-migrate).
  --print-settings-baselines
                        Print the normative T5.4 baseline table (JSON) and
                        exit 0. Oracles derive their expectations from this
                        output instead of hardcoding the literals.
  --no-replay           PLAN-153 Wave B (B2): do NOT replay the recorded
                        install request from .claude/.install-state.json.
                        By default, when that file exists and validates,
                        --profile/--stack DEFAULT to the recorded values
                        (explicit flags always win). Missing/invalid state
                        falls back to the ADR-155 drift-classifier path —
                        never an error, never a no-op.
  --harness <c|codex>   PLAN-155 Wave 5: override the harness. Defaults to the
                        recorded request.harness (B2 replay). When codex, the
                        upgrade also refreshes the .codex/ bundle from the
                        current templates (collision behavior follows
                        --on-conflict; refuse leaves local edits).
  --managed-hooks       PLAN-155 Wave 5 (codex): also refresh requirements.toml
                        (managed-hooks posture). Replayed from state otherwise.
  --skip <glob>         Exclude files from the overwrite (repeat for multiple globs).
                        Example: --skip='.claude/scripts/local/*'
  --skip=<glob>         Alternate inline syntax for --skip.
  --ceremony <maintainer|user>
                        Re-pass rc.4 t3/t5: explicit ceremony for PRE-STATE
                        targets (no readable .claude/.install-state.json).
                        A RECORDED ceremony in the install state ALWAYS wins
                        over this flag; with neither record nor flag the
                        upgrade fails safe to 'user' (root files untouched)
                        and that inference is never persisted. Only an
                        explicit flag/env or a recorded value persists.
                        Env override: CEO_UPGRADE_CEREMONY=<maintainer|user>.
  --purge-misinstalled  PLAN-161 U3 (opt-in — NEVER default): delete files found
                        inside the framework-internal excluded trees
                        (.claude/hooks/{tests,legacy}, .claude/scripts/tests,
                        .claude/hooks/_lib/tests + test_isolation.py/testing.py)
                        ONLY when their sha256 matches the current framework
                        source at the SAME relpath or the recorded baseline
                        digest for that relpath. Every purged file is backed up
                        to .claude.bak/ first; symlinks are never followed.
                        Without this flag (and always under --dry-run) the scan
                        only PREVIEWS would-purge candidates.
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
  echo "Usage: $0 <target-repo-path> [--profile <list>] [--stack <name>] [--pin <tag>] [--dry-run] [--ceremony <maintainer|user>]" >&2
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

# PLAN-161 U1 (codex r2 F4) — ONE composed EXIT cleanup. The --pin block used
# to install an inline EXIT trap restoring the source branch; any later plain
# `trap ... EXIT` would CLOBBER it. All exit-time duties now live in this
# single function, installed ONCE: (a) restore the pinned-source branch,
# guarded by PINNED_CHECKOUT_DONE + ORIGINAL_BRANCH — the non-dry --pin
# restore semantics are preserved exactly, on success AND on mid-run failure;
# (b) reap the sanitized baseline-manifest tempfile, which now lives OUTSIDE
# $TARGET (see _load_baseline_manifest).
_BASELINE_TMP_FILE=""
_upgrade_cleanup() {
  if [[ "${PINNED_CHECKOUT_DONE:-0}" -eq 1 ]] && [[ -n "${ORIGINAL_BRANCH:-}" ]]; then
    ( cd "$SOURCE_DIR" && git checkout --quiet "$ORIGINAL_BRANCH" 2>/dev/null ) || true
  fi
  if [[ -n "${_BASELINE_TMP_FILE:-}" ]]; then
    rm -f "$_BASELINE_TMP_FILE" 2>/dev/null || true
  fi
}
trap _upgrade_cleanup EXIT

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
  # Source-branch restore on any exit is handled by the composed
  # _upgrade_cleanup EXIT trap installed above (PLAN-161 U1, codex r2 F4).
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
# PLAN-155 Wave 5: harness (closed enum) + managed_hooks bool round-trip.
harness = req.get("harness", "")
if harness not in ("", "claude", "codex"):
    harness = ""  # unknown value => fall back to CLI/default, never trust it
managed = "1" if req.get("managed_hooks") is True else "0"
sys.stdout.write(prof + "\t" + stack + "\t" + harness + "\t" + managed + "\n")
' "$_INSTALL_STATE_FILE" 2>/dev/null
}

if [[ "$REPLAY" -eq 1 ]]; then
  if [[ -f "$_INSTALL_STATE_FILE" ]]; then
    _rp_line=""
    if _rp_line="$(_read_install_state_request)" && [[ -n "$_rp_line" ]]; then
      # TAB-separated: profile<TAB>stack<TAB>harness<TAB>managed (PLAN-155 W5).
      IFS=$'\t' read -r _rp_profile _rp_stack _rp_harness _rp_managed <<< "$_rp_line"
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
      if [[ "$HARNESS_EXPLICIT" -eq 0 && -n "$_rp_harness" ]]; then
        HARNESS="$_rp_harness"
        _rp_used=1
        echo "    REPLAY: --harness $HARNESS (recorded request in .claude/.install-state.json; pass --harness or --no-replay to override)" >&2
      fi
      if [[ "$CODEX_MANAGED_HOOKS" -eq 0 && "${_rp_managed:-0}" = "1" ]]; then
        CODEX_MANAGED_HOOKS=1
        _rp_used=1
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

# ===========================================================================
# PLAN-166 F3 (ADR-155-AMEND-1) — resolve the RECORDED install ceremony with
# a reader of its OWN, INDEPENDENT of the replay path: --no-replay sets
# REPLAY=0 and the replay block above (incl. _read_install_state_request) is
# skipped entirely, so if the ceremony rode the replay, the documented
# `upgrade.sh <target> --no-replay` would treat a `--ceremony user` install
# as maintainer and force SPEC/protocol into the adopter's root (r9). This
# reader ALWAYS runs. Fail-open: state absent/unreadable/invalid (ALL
# pre-Wave-B installs) => "maintainer" — the pre-existing behavior; the
# consequence is named in INSTALL.md §Upgrade flow. Same trust class as the
# replay reader: target-side, UNSIGNED, advisory; the value is validated
# against the closed enum {maintainer,user} and never eval-ed.
# ===========================================================================
_read_install_state_ceremony() {
  command -v python3 >/dev/null 2>&1 || return 3
  [ -f "$_INSTALL_STATE_FILE" ] && [ -r "$_INSTALL_STATE_FILE" ] || return 3
  PYTHONNOUSERSITE=1 python3 -I -c '
import json, sys
try:
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        d = json.load(f)
except (OSError, ValueError):
    sys.exit(3)
if not isinstance(d, dict) or d.get("schema_version") != 1:
    sys.exit(3)
req = d.get("request")
if not isinstance(req, dict):
    sys.exit(3)
cer = req.get("ceremony", "")
if cer not in ("maintainer", "user"):
    sys.exit(3)
sys.stdout.write(cer + "\n")
' "$_INSTALL_STATE_FILE" 2>/dev/null
}

# Re-pass rc.4 t2 (P2): with NO readable install-state the old default was
# maintainer (fail-open) — a pre-v1.2 USER-ceremony install could receive
# root .gitignore writes across the user boundary. The fail-SAFE default is
# user (root surfaces skipped, loudly); a pre-state MAINTAINER install opts
# back in explicitly via CEO_UPGRADE_CEREMONY=maintainer.
CEREMONY_EFFECTIVE="user"
_CEREMONY_SOURCE="default (no readable install-state — fail-safe user; pass --ceremony maintainer to opt back in)"
# t5 P1: only RECORDED or EXPLICIT resolutions may persist into the state
# file — persisting the fail-safe INFERENCE would make one missed migration
# flag permanent (recorded state wins on the next run by design).
_CEREMONY_PERSIST="0"
_cer_line=""
if _cer_line="$(_read_install_state_ceremony)" && [[ -n "$_cer_line" ]]; then
  CEREMONY_EFFECTIVE="$_cer_line"
  _CEREMONY_SOURCE="recorded install request (.claude/.install-state.json)"
  _CEREMONY_PERSIST="1"
elif [[ -n "${CEREMONY_FLAG:-}" ]]; then
  CEREMONY_EFFECTIVE="$CEREMONY_FLAG"
  _CEREMONY_SOURCE="explicit --ceremony flag (no install-state)"
  _CEREMONY_PERSIST="1"
elif [[ "${CEO_UPGRADE_CEREMONY:-}" == "maintainer" || "${CEO_UPGRADE_CEREMONY:-}" == "user" ]]; then
  CEREMONY_EFFECTIVE="$CEO_UPGRADE_CEREMONY"
  _CEREMONY_SOURCE="explicit CEO_UPGRADE_CEREMONY override (no install-state)"
  _CEREMONY_PERSIST="1"
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
echo "    Ceremony: $CEREMONY_EFFECTIVE — $_CEREMONY_SOURCE"  # PLAN-166 F3
if [[ "$_REPLAY_SOURCE" == "replay" ]]; then
  echo "    Request: replayed from .claude/.install-state.json (PLAN-153 B2)"
fi
if [[ -n "$PIN_REF" ]]; then
  echo "    Pinned:  $PIN_REF"
fi
echo ""

# PLAN-161 U1: --dry-run must write NOTHING inside the target — eagerly
# creating the (timestamped, thus always-new) backup dir was one of the three
# dry-run-ignoring writer families found live in the 2026-07-21 adopter
# upgrade. Real runs still create it up front (the U3 purge backup and the
# agents-pin backup below rely on it existing).
if [[ "$DRY_RUN" -eq 0 ]]; then
  mkdir -p "$BAK_DIR"
fi

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

# PLAN-155 Wave 5 — override the codex helper's no-op recorder so a codex
# refresh during upgrade is journaled into the upgrade operation log.
codex_journal() { _up_record_op "$1" "${2:-}"; }

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
#
# $2 = record KIND, mirroring doctor.sh `_relpath_unsafe` (family sweep):
# "link" tolerates a symlinked LEAF, anything else (default "file") does not.
# A `LINK  <relpath>  <target>` record describes a --mode link delivery whose
# leaf IS a symlink by construction, so rejecting it here silently dropped the
# record from the sanitized manifest: _baseline_has_spec_record and both
# readlink-vs-recorded-target checks could then NEVER match, and every
# link-mode upgrade lost framework ownership of SPEC/v1 and the marker, with
# marker-first readers falling back to the stale root VERSION (codex W1
# round 6, P2). The leaf is never FOLLOWED here — validation stays at the
# consumers, which compare `readlink` against the recorded target. Hash
# records keep the strict leaf check: a managed regular file swapped for a
# symlink must not retain its record (_hash_file WOULD follow it). Symlinked
# PARENT components remain a genuine traversal hazard for both kinds.
_baseline_relpath_unsafe() {
  _bru_rel="$1"
  _bru_kind="${2:-file}"
  case "$_bru_rel" in
    /*) return 0 ;;                       # absolute
    *..*) return 0 ;;                      # parent traversal (covers ../ and /..)
  esac
  # Control chars / whitespace-only / empty.
  case "$_bru_rel" in
    ""|*[$'\n\r\t']*) return 0 ;;
  esac
  # Count the significant components first, so the leaf can be identified by
  # INDEX — reconstructing "$TARGET/$_bru_rel" for a leaf test would differ
  # from the walk on `./` and trailing-slash forms.
  _bru_n=0
  _bru_oldIFS="$IFS"
  IFS='/'
  for _bru_comp in $_bru_rel; do
    [ -n "$_bru_comp" ] || continue
    [ "$_bru_comp" = "." ] && continue
    _bru_n=$(( _bru_n + 1 ))
  done
  # Symlinked-component check: walk each path component under $TARGET; if any
  # EXISTING component is a symlink, reject (do not follow it).
  _bru_cur="$TARGET"
  _bru_i=0
  for _bru_comp in $_bru_rel; do
    [ -n "$_bru_comp" ] || continue
    [ "$_bru_comp" = "." ] && continue
    _bru_i=$(( _bru_i + 1 ))
    _bru_cur="$_bru_cur/$_bru_comp"
    if [ -L "$_bru_cur" ]; then
      if [ "$_bru_kind" = "link" ] && [ "$_bru_i" -eq "$_bru_n" ]; then
        continue                          # the LINK record's own leaf
      fi
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

  # PLAN-161 U1: the sanitized manifest used to be mktemp'd INSIDE $BAK_DIR —
  # a write inside the target even under --dry-run (and the reason dry-run
  # could not keep classification alive once BAK_DIR creation was gated). It
  # now lives in a secure temp OUTSIDE $TARGET in ALL runs; the composed
  # _upgrade_cleanup EXIT trap reaps it via the _BASELINE_TMP_FILE global.
  #
  # PLAN-161 U1 (codex r1 F5): "outside $TARGET" must hold even when the
  # CALLER's TMPDIR is $TARGET or lies under it — otherwise --dry-run writes
  # in the target again. Resolve the tmp base physically (cd + pwd -P) and
  # prefix-check it against the physically-resolved $TARGET (trailing-slash
  # safe case glob, bash-3.2-safe); on equal-or-under, fall back to /tmp.
  # If the base cannot be resolved (nonexistent), leave it — mktemp fails
  # below and we return 0 (the existing no-manifest fallback).
  local _lbm_base _lbm_base_abs _lbm_target_abs
  _lbm_base="${TMPDIR:-/tmp}"
  _lbm_base_abs="$( cd "$_lbm_base" 2>/dev/null && pwd -P )" || _lbm_base_abs=""
  _lbm_target_abs="$( cd "$TARGET" 2>/dev/null && pwd -P )" || _lbm_target_abs=""
  if [[ -n "$_lbm_base_abs" && -n "$_lbm_target_abs" ]]; then
    case "${_lbm_base_abs%/}/" in
      "${_lbm_target_abs%/}/"*) _lbm_base="/tmp" ;;
    esac
  fi
  local sanitized
  sanitized="$( mktemp "$_lbm_base/ceo-baseline-manifest.XXXXXX" 2>/dev/null )" || return 0
  _BASELINE_TMP_FILE="$sanitized"

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
        # KIND=link: the leaf of a LINK record IS a symlink by construction
        # (codex W1 round 6, P2). Symlinked PARENTS still reject.
        if _baseline_relpath_unsafe "$rel" link; then continue; fi
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

# PLAN-161 U1 (codex r1 F4) — manifest-load observability. Byte-identity alone
# cannot prove a --dry-run kept provenance classification alive (a dry-run
# that silently lost the baseline would also write nothing), so EVERY run
# states which classification mode it operates in.
if [ -n "$_BASELINE_MANIFEST_FILE" ]; then
  echo "==> Baseline manifest: loaded (provenance classification ACTIVE)"
else
  echo "==> Baseline manifest: none — fallback diff -q classification"
fi

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
    # PLAN-161 U2 (CF-7): the canonical framework-internal exclusion set —
    # never install, never re-add after an adopter deletes, never report.
    # Silent skip; the opt-in U3 purge is the ONLY code allowed to touch
    # these paths (and only hash-gated).
    if command -v _framework_path_excluded >/dev/null 2>&1 && _framework_path_excluded "$rel"; then
      continue
    fi
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

# PLAN-161 W2 fix-3 (codex r3 F11a): TRUE (rc 0) iff any STRICT ancestor
# component of relpath $2 under root $1 is a symlink. A preserved excluded
# SYMLINK must be an opaque leaf: a -f/-d/-L test (or rm/rmdir) on a path
# that runs THROUGH it resolves into the link TARGET, so an unguarded
# prune could delete adopter data OUTSIDE the tree. Every prune-side
# test/delete on "$TARGET/$rel" must first pass this lstat-walk guard.
# bash 3.2-safe: pure string splitting, [[ -L ]] never follows the leaf.
_lg_ancestor_is_symlink() {
  local _as_root="$1" _as_rel="$2" _as_walk=""
  while [[ "$_as_rel" == */* ]]; do
    _as_walk="${_as_walk:+$_as_walk/}${_as_rel%%/*}"
    _as_rel="${_as_rel#*/}"
    if [[ -L "$_as_root/$_as_walk" ]]; then return 0; fi
  done
  return 1
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
    # PLAN-161 U1 (codex r1 F4): classification-aware preview for single-FILE
    # targets when a baseline manifest is loaded — the dry-run log must PROVE
    # the provenance classifier still runs (byte-identity alone would pass on
    # a dry-run that silently lost classification). DIRECTORY targets keep
    # the legacy one-line preview.
    if [[ -f "$dst" && -f "$src" && -n "$_BASELINE_MANIFEST_FILE" ]]; then
      local _drv
      _drv="$( _classify_against_baseline "$rel_path" )"
      case "$_drv" in
        IDENTICAL)
          echo "    (dry-run) would SKIP (IDENTICAL): $rel_path" ;;
        ADOPTER-CUSTOMIZED)
          echo "    (dry-run) would PRESERVE (ADOPTER-CUSTOMIZED): $rel_path" ;;
        CONFLICT)
          echo "    (dry-run) would apply --on-conflict=$ON_CONFLICT (CONFLICT): $rel_path" ;;
        FRAMEWORK-CHANGED)
          echo "    (dry-run) would UPDATE (FRAMEWORK-CHANGED; original would be backed up to $BAK_DIR/$rel_path): $rel_path" ;;
        FALLBACK|*)
          echo "    (dry-run) would BACKUP + UPDATE (no usable baseline): $rel_path" ;;
      esac
      return
    fi
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

  # PLAN-161 W2 fix-2 (codex r2 F11): the legacy DIRECTORY branch used to
  # empty $dst WHOLESALE (find -delete + rmdir) before the copy — which
  # silently DELETED any excluded-tree content already present at dst
  # (adopter-owned OR mis-installed), before any preview/hash gate: an
  # implicit purge that violated the opt-in-only --purge-misinstalled
  # contract (U3). The pre-copy delete now SKIPS excluded paths (files AND
  # dirs, contents intact) and the copy below never writes them, so a
  # legacy upgrade neither ADDS nor REMOVES excluded-tree files; the U3
  # opt-in flag remains the ONLY path that deletes them. Survivors are
  # recorded (relpaths, one per line) so the r1 post-copy prune can tell
  # pre-existing excluded content (keep byte-for-byte) from a copy-path
  # regression artifact (prune). Fail-open: predicate unavailable (older
  # sourced lib) => exactly the pre-U2 wholesale behavior. NEVER rm -rf.
  local _lg_excl_aware=0
  local _lg_survivors=""
  if command -v _framework_path_excluded >/dev/null 2>&1 \
     && [[ -d "$dst" && -d "$src" ]]; then
    _lg_survivors="$( mktemp "${TMPDIR:-/tmp}/ceo-upg-survivors.XXXXXX" )"
    _lg_excl_aware=1
  fi

  if [[ "$_lg_excl_aware" -eq 1 ]]; then
    local _lg_hit _lg_rel
    # F11a symlink-safety note: find runs PHYSICAL traversal (no -L/-H/
    # -follow), so it never descends into a symlinked dir — a symlink is
    # emitted as its own leaf (matches ! -type d, never -type d) and
    # rm -f unlinks the LINK itself, never its target. Every path find
    # emits here is symlink-free above the leaf by construction.
    # Non-dir entries (files/symlinks/etc): delete non-excluded, record
    # excluded survivors untouched.
    while IFS= read -r _lg_hit; do
      [[ -n "$_lg_hit" ]] || continue
      _lg_rel="${_lg_hit#"$TARGET"/}"
      if _framework_path_excluded "$_lg_rel"; then
        printf '%s\n' "$_lg_rel" >> "$_lg_survivors"
      else
        rm -f "$_lg_hit"
      fi
    done < <( find "$dst" ! -type d -print 2>/dev/null )
    # Dirs, children before parents (-depth): rmdir non-excluded (only
    # succeeds once empty — a dir still holding excluded survivors stays);
    # record excluded dirs so the prune's rmdir pass keeps them too.
    while IFS= read -r _lg_hit; do
      [[ -n "$_lg_hit" ]] || continue
      _lg_rel="${_lg_hit#"$TARGET"/}"
      if _framework_path_excluded "$_lg_rel"; then
        printf '%s\n' "$_lg_rel" >> "$_lg_survivors"
      else
        rmdir "$_lg_hit" 2>/dev/null || true
      fi
    done < <( find "$dst" -depth -type d -print 2>/dev/null )
  elif [[ -d "$dst" ]]; then
    # Use find+delete instead of rm -rf to satisfy safety hooks on dev machines
    find "$dst" -mindepth 1 -delete
    rmdir "$dst"
  elif [[ -e "$dst" ]]; then
    rm -f "$dst"
  fi

  mkdir -p "$( dirname "$dst" )"
  if [[ -d "$src" ]]; then
    if [[ "$_lg_excl_aware" -eq 1 ]]; then
      # PLAN-161 W2 fix-2 (codex r2 F11): exclusion-aware per-file copy —
      # non-excluded dirs first (preserves empty framework dirs), then
      # non-excluded files + symlinks (per-operand cp -R copies a symlink
      # as a symlink, POSIX). Excluded SOURCE paths are NEVER written, so
      # pre-existing excluded dst content (the pre-delete survivors) stays
      # byte-for-byte identical across the upgrade — neither deleted,
      # re-copied, nor overwritten by source bytes at a shadowed relpath.
      while IFS= read -r _lg_hit; do
        [[ -n "$_lg_hit" ]] || continue
        _lg_rel="${_lg_hit#"$SOURCE_DIR"/}"
        if _framework_path_excluded "$_lg_rel"; then continue; fi
        mkdir -p "$TARGET/$_lg_rel"
      done < <( find "$src" -type d -print 2>/dev/null )
      while IFS= read -r _lg_hit; do
        [[ -n "$_lg_hit" ]] || continue
        _lg_rel="${_lg_hit#"$SOURCE_DIR"/}"
        if _framework_path_excluded "$_lg_rel"; then continue; fi
        mkdir -p "$( dirname "$TARGET/$_lg_rel" )"
        cp -R "$_lg_hit" "$TARGET/$_lg_rel"
      done < <( find "$src" \( -type f -o -type l \) -print 2>/dev/null )
    else
      cp -R "$src" "$dst"
    fi
    # PLAN-161 U2 (CF-7) r1 prune, F11-NARROWED (belt-and-suspenders): in
    # the wholesale-cp fallback this removes the excluded source content
    # cp -R just dragged in (~967 files in the live 2026-07-21 adopter
    # upgrade). In the exclusion-aware path above the copy never writes
    # excluded paths, so an excluded file found at dst here is either a
    # recorded pre-delete SURVIVOR (adopter-owned or mis-installed — F11:
    # MUST be left exactly as-is; only U3 --purge-misinstalled may delete
    # it) or the artifact of a future copy-path regression (prune it).
    # Per-file rm -f plus rmdir for the emptied dirs — NEVER rm -rf.
    if command -v _framework_path_excluded >/dev/null 2>&1; then
      local _pr_hit _pr_rel
      while IFS= read -r _pr_hit; do
        [[ -n "$_pr_hit" ]] || continue
        _pr_rel="${_pr_hit#"$SOURCE_DIR"/}"
        if _framework_path_excluded "$_pr_rel"; then
          # F11a: never test or delete THROUGH a symlinked ancestor — the
          # dst path would resolve into the link target (adopter data
          # possibly outside the tree). Preserved symlink == opaque leaf.
          if _lg_ancestor_is_symlink "$TARGET" "$_pr_rel"; then continue; fi
          # Leaf: -L before -f (lstat-first; -f alone would follow a link).
          if [[ -L "$TARGET/$_pr_rel" || -f "$TARGET/$_pr_rel" ]]; then
            if [[ -n "$_lg_survivors" ]] \
               && grep -Fxq "$_pr_rel" "$_lg_survivors" 2>/dev/null; then
              :  # pre-existing excluded content — keep exactly as-is (F11)
            else
              rm -f "$TARGET/$_pr_rel"
            fi
          fi
        fi
      done < <( find "$src" \( -type f -o -type l \) -print 2>/dev/null )
      # Remove the now-empty excluded dirs, children before parents (-depth)
      # — but never a recorded survivor dir (pre-existing, adopter-held).
      while IFS= read -r _pr_hit; do
        [[ -n "$_pr_hit" ]] || continue
        _pr_rel="${_pr_hit#"$SOURCE_DIR"/}"
        # F11a: ancestor-symlink guard first, then -L BEFORE -d (lstat-first
        # — -d follows a leaf symlink; a preserved excluded symlink-to-dir
        # must be kept whole and its target never rmdir'd).
        if _framework_path_excluded "$_pr_rel" \
           && ! _lg_ancestor_is_symlink "$TARGET" "$_pr_rel" \
           && [[ ! -L "$TARGET/$_pr_rel" && -d "$TARGET/$_pr_rel" ]]; then
          if [[ -n "$_lg_survivors" ]] \
             && grep -Fxq "$_pr_rel" "$_lg_survivors" 2>/dev/null; then
            :  # pre-existing excluded dir — keep (F11)
          else
            rmdir "$TARGET/$_pr_rel" 2>/dev/null || true
          fi
        fi
      done < <( find "$src" -depth -type d -print 2>/dev/null )
    fi
  else
    cp "$src" "$dst"
  fi
  if [[ -n "$_lg_survivors" ]]; then
    rm -f "$_lg_survivors"
  fi
  echo "    UPDATED: $rel_path"
}

# DevOps-P1-4: refresh PROTOCOL.md pointer on upgrade. This is
# framework-derived content (not user data), so preserving it as-is
# across upgrades traps stale pointers when the framework moves. We
# regenerate it with the same heuristic install.sh uses.
_refresh_protocol_pointer() {
  local pointer="$TARGET/PROTOCOL.md"

  # PLAN-168 W2 (AC-6, Owner decision D1-b): the body comes from the ONE
  # shared generator in _framework_manifest_set.sh — never a private heredoc.
  # INV-4 existed because this function and install.sh each carried their own
  # copy of this text: install substituted {{PROTOCOL_SOURCE}}, this one did
  # not — two bodies for the same file, and the recorded digest never matched
  # the disk (OWN-0074). A missing generator preserves the surface (upgrade's
  # fail-toward-preservation posture, same as an illegal cell below).
  if ! command -v _render_protocol_pointer >/dev/null 2>&1; then
    echo "    WARNING: _render_protocol_pointer unavailable — PROTOCOL.md pointer PRESERVED" >&2
    return 0
  fi

  # Resolve the PROTOCOL_SOURCE the pointer should name (AC-6c, Owner
  # decision D3). Precedence:
  #   1. request.placeholders.PROTOCOL_SOURCE from the install-state — the
  #      install has ALWAYS persisted it there (union across runs; the
  #      PLAN-168 debate's claim that it was never persisted checked the
  #      wrong key — codex rail r1 P1).
  #   2. A HEALTHY on-disk pointer: extract the value it already names and
  #      keep it — never silently rename a sound pointer to today's checkout.
  #   3. $SOURCE_DIR (this upgrade's checkout) — last resort, used for
  #      genuinely old installs with no state and no sound pointer (incl.
  #      the degraded-cure path, where the pointer names nothing usable).
  local _ptr_psource=""
  if [ -f "$_INSTALL_STATE_FILE" ] && command -v python3 >/dev/null 2>&1; then
    _ptr_psource="$( python3 - "$_INSTALL_STATE_FILE" <<'PYEOF' 2>/dev/null || true
import json, sys
try:
    with open(sys.argv[1], "r", encoding="utf-8") as f:
        doc = json.load(f)
    v = (doc.get("request") or {}).get("placeholders", {}).get("PROTOCOL_SOURCE", "")
    if isinstance(v, str) and v and "{{" not in v:
        sys.stdout.write(v)
except Exception:
    pass
PYEOF
)"
  fi
  if [ -z "$_ptr_psource" ] && [ -f "$pointer" ]; then
    # D3 route 2: trust a SOUND pointer. Extract the source it names and
    # accept it only if re-rendering with that value reproduces the file
    # byte-for-byte (the same reconstruction discipline as the degraded
    # recognizer — anything else is adopter content, not a source of truth).
    local _ptr_cand
    _ptr_cand="$( sed -n 's|^\(.*\)/PROTOCOL\.md$|\1|p' "$pointer" 2>/dev/null | sed -n '1p' )"
    if [ -n "$_ptr_cand" ] && [ "${_ptr_cand#\{\{}" = "$_ptr_cand" ]; then
      if _render_protocol_pointer "$SOURCE_DIR" "$TARGET" "$PROFILE" "$STACK" "$_ptr_cand" \
           | cmp -s - "$pointer" 2>/dev/null; then
        _ptr_psource="$_ptr_cand"
      fi
    fi
  fi
  if [ -z "$_ptr_psource" ]; then
    _ptr_psource="$SOURCE_DIR"
  fi

  local _ptr_full
  _ptr_full="$( _render_protocol_pointer "$SOURCE_DIR" "$TARGET" "$PROFILE" "$STACK" "$_ptr_psource" )"

  # The CANONICAL digest: the hash of exactly what the framework WOULD write.
  # Computed on every path, because the baseline rewrite must record it even
  # when the pointer is preserved — recording the customised bytes instead
  # would make the NEXT upgrade read H_dst == H_base and clobber them (C.5).
  # Post-PLAN-168 this is the hash of the SUBSTITUTED body — the same bytes
  # install writes — so the recorded digest finally matches the disk (INV-4).
  _REFRESH_PROTOCOL_CANON_HASH=""
  if command -v _hash_stdin >/dev/null 2>&1; then
    _REFRESH_PROTOCOL_CANON_HASH="$( printf '%s\n' "$_ptr_full" | _hash_stdin 2>/dev/null || true )"
  fi

  # ---- OBSERVE -------------------------------------------------------------
  local _lt _pr _lc
  _lt="$( _ov_obs_live_type "$pointer" )"
  _pr="$( _ov_obs_prior_record "PROTOCOL.md" )"
  if [ "$_lt" != "regular" ]; then
    _lc="-"
  elif _protocol_pointer_is_degraded "$pointer"; then
    # PLAN-168 W2 (AC-6b, Owner decision D2): byte-exact reconstruction of
    # the {{PROTOCOL_SOURCE}}-literal template this script used to write.
    # Framework garbage, not adopter content — the verdict routes it to the
    # REFRESH cure below. Checked BEFORE pristine/edited: a degraded body
    # can never equal the substituted canonical, and classifying it `edited`
    # is exactly the immortal-defect route this wave closes.
    _lc="degraded"
  elif [ -n "$_REFRESH_PROTOCOL_CANON_HASH" ] \
       && [ "$( _hash_file "$pointer" 2>/dev/null || true )" = "$_REFRESH_PROTOCOL_CANON_HASH" ]; then
    _lc="pristine"
  else
    _lc="edited"
  fi

  # ---- DECIDE --------------------------------------------------------------
  local _pair _verdict
  if ! _pair="$( _ownership_verdict protocol "$_pr" "$_lt" "$_lc" yes copy \
                   "$CEREMONY_EFFECTIVE" upgrade none )"; then
    echo "    WARNING: PROTOCOL.md dimensions are not a legal cell — PRESERVED" >&2
    return 0
  fi
  _verdict="${_pair%% *}"
  _PROTOCOL_HASH_SOURCE="${_pair##* }"

  # ---- EXECUTE -------------------------------------------------------------
  # The guards this surface never had are not new branches: they are what the
  # decision already says. A destination that is not a regular file is
  # adopter-owned, so the verdict is unowned and nothing is written — which is
  # exactly the leaf-symlink / directory / FIFO protection SPEC and the marker
  # acquired during the S296 rounds and the pointer did not.
  case "$_verdict" in
    PRESERVE_UNOWNED|OMIT_RECORD)
      case "$_lt" in
        symlink) echo "    SKIP: PROTOCOL.md is a symlink — refusing to write THROUGH it (would mutate a path outside the target)" >&2 ;;
        dir|dir_empty) echo "    SKIP: PROTOCOL.md is a directory — adopter-owned, refusing to write into it" >&2 ;;
        special) echo "    SKIP: PROTOCOL.md is an unsupported special file — preserved, surface untouched" >&2 ;;
        *) echo "    SKIP: PROTOCOL.md pointer (recorded --ceremony user install — a user install never creates root files, WS4)" ;;
      esac
      return 0
      ;;

    PRESERVE_OWNED)
      _PROTOCOL_DELIVERED=1
      if [ "$_lc" = "edited" ]; then
        # ADR-155 decision (iii): the verified S238 case. An adopter-customised
        # pointer is CONTENT, not a fork — it is preserved, and the record keeps
        # the canonical digest so the next upgrade does not read it as pristine.
        if [ "$DRY_RUN" -eq 0 ] && [ -f "$pointer" ]; then
          mkdir -p "$BAK_DIR" 2>/dev/null || true
          cp "$pointer" "$BAK_DIR/PROTOCOL.md" 2>/dev/null || true
        fi
        echo "    PRESERVED (root PROTOCOL.md is adopter-customised — pointer NOT refreshed; backup in $BAK_DIR/PROTOCOL.md)" >&2
      else
        echo "    SKIP: PROTOCOL.md pointer (ownership carried forward)"
      fi
      return 0
      ;;

    DELIVER|REFRESH)
      if [ "$DRY_RUN" -eq 1 ]; then
        echo "    (dry-run) would REFRESH: PROTOCOL.md pointer"
        return 0
      fi
      _up_record_op "refresh_protocol_pointer" "PROTOCOL.md"
      # Backup-always before the overwrite, even with no baseline manifest —
      # this is what made the S238 loss recoverable on a FIRST upgrade.
      if [ -f "$pointer" ]; then
        mkdir -p "$BAK_DIR" 2>/dev/null || true
        cp "$pointer" "$BAK_DIR/PROTOCOL.md" 2>/dev/null || true
        echo "    BACKED UP: PROTOCOL.md (root) -> $BAK_DIR/PROTOCOL.md"
      fi
      printf '%s\n' "$_ptr_full" > "$pointer"
      _PROTOCOL_DELIVERED=1
      if [ "$_lc" = "degraded" ]; then
        echo "    CURED: PROTOCOL.md pointer was framework-degraded ({{PROTOCOL_SOURCE}} left literal by an old upgrade) — refreshed; original in $BAK_DIR/PROTOCOL.md"
      else
        echo "    REFRESHED: PROTOCOL.md pointer"
      fi
      return 0
      ;;
  esac
}

# ===========================================================================
# PLAN-166 F3 (ADR-155-AMEND-1) — delivery-record lookups + SPEC/v1 FORCED
# refresh + framework version marker refresh.
# ---------------------------------------------------------------------------
# Ownership of the three conditional surfaces (PROTOCOL.md, SPEC/v1,
# .claude/.framework-version) derives from the REGISTERED DELIVERY — here,
# the PRE-upgrade baseline manifest records (the same record install.sh
# writes and doctor.sh reads) — never from the ceremony alone and never from
# file presence (r7/r13/r17/r19/r20).
# ===========================================================================
_baseline_has_spec_record() {
  [[ -n "$_BASELINE_MANIFEST_FILE" && -f "$_BASELINE_MANIFEST_FILE" ]] || return 1
  # `(/|  |$)` and not a bare trailing slash: a --mode link install records
  # the WHOLE tree as one directory symlink — `LINK  SPEC/v1  <target>`, no
  # trailing slash — which a `SPEC/v1/` fragment can never match (the same
  # `(  |$)` treatment the marker/PROTOCOL readers already have; family
  # swept with doctor.sh _dr_delivered, re-pass closure).
  grep -Eq '^([0-9a-f]{64}|LINK)  SPEC/v1(/|  |$)' "$_BASELINE_MANIFEST_FILE" 2>/dev/null
}
_baseline_has_marker_record() {
  [[ -n "$_BASELINE_MANIFEST_FILE" && -f "$_BASELINE_MANIFEST_FILE" ]] || return 1
  grep -Eq '^([0-9a-f]{64}|LINK)  \.claude/\.framework-version(  |$)' "$_BASELINE_MANIFEST_FILE" 2>/dev/null
}
# Third sibling of the family (codex W1 round 7, P2): the `--ceremony user`
# skip needs the same ownership-continuity question the SPEC/marker skips
# already ask. `_baseline_lookup` is not a substitute — it resolves HASH
# records only, and a --mode link PROTOCOL.md is a LINK record.
_baseline_has_protocol_record() {
  [[ -n "$_BASELINE_MANIFEST_FILE" && -f "$_BASELINE_MANIFEST_FILE" ]] || return 1
  grep -Eq '^([0-9a-f]{64}|LINK)  PROTOCOL\.md(  |$)' "$_BASELINE_MANIFEST_FILE" 2>/dev/null
}

# PRISTINE fingerprints of every SPEC/v1 tree the framework shipped at
# v1.2.0 and earlier (r20 LEGACY MIGRATION: v1.2-and-earlier installs never
# enumerated SPEC/v1, so no historical delivery record can distinguish a
# framework-installed SPEC from an adopter's own — the ambiguity resolves by
# CONTENT). Derivation (deterministic — pinned tag content; run in the
# framework repo, reproduces _spec_tree_fingerprint byte-for-byte):
#   for t in v1.0.0 v1.0.1 v1.0.1-rc.1 v1.1.0 v1.1.0-rc.1 \
#            v1.2.0 v1.2.0-rc.1 v1.2.0-rc.2 v1.2.0-rc.3; do
#     git ls-tree -r --name-only "$t" -- SPEC/v1 | LC_ALL=C sort \
#     | while IFS= read -r f; do
#         printf '%s  %s\n' \
#           "$(git show "$t:$f" | shasum -a 256 | awk '{print $1}')" "$f"
#       done | shasum -a 256 | awk '{print $1}'
#   done
# Three distinct trees across the nine shipped tags:
#   a4a4... = v1.0.0 / v1.0.1 / v1.0.1-rc.1
#   94aa... = v1.1.0 / v1.1.0-rc.1
#   469a... = v1.2.0 / v1.2.0-rc.1 / v1.2.0-rc.2 / v1.2.0-rc.3
_SPEC_PRISTINE_FINGERPRINTS="a4a4504a224d72a975a853dd71a75d8e678fef034a70deb49df291dbb712c161 94aa62f781285ce4897ad1220edf15e97b4e9d7b629f9f7ba3389da5d45f22b1 469a49238867be181490214305b43bc7299f2bae3ef0b282a5452f6caf327f0b"

# _spec_tree_fingerprint <root> — sha256 over the LC_ALL=C-sorted
# "<sha256(file)>  <relpath>" lines of every regular file under
# <root>/SPEC/v1 (the derivation comment above reproduces this from a tag).
# Fails (rc 1, no output) on a missing tree/hasher or any unhashable file —
# a PARTIAL fingerprint must never be compared against a pristine one.
_spec_tree_fingerprint() {
  local _sf_root="$1"
  command -v _hash_file >/dev/null 2>&1 || return 1
  command -v _hash_stdin >/dev/null 2>&1 || return 1
  [[ -d "$_sf_root/SPEC/v1" ]] || return 1
  # COMPLETENESS gate (codex W1-ceremony round, P2): the fingerprint hashes
  # regular files only, so an adopter-ADDED symlink/fifo/etc would be
  # invisible — the partial fingerprint could still byte-match a pristine
  # release and the forced refresh would REPLACE an adopter-modified tree
  # (the S238 class). Any non-regular, non-directory entry => no
  # fingerprint (rc 1) => the caller's safe path (ADOPTER-FORK preserve).
  # A find traversal error (unreadable subdir) is the same: partial
  # inventory must never be compared against a pristine fingerprint.
  local _sf_odd
  _sf_odd="$( ( cd "$_sf_root" && find SPEC/v1 -mindepth 1 ! -type f ! -type d -print 2>&1 ) )" || return 1
  [[ -z "$_sf_odd" ]] || return 1
  local _sf_lines
  _sf_lines="$(
    ( cd "$_sf_root" && find SPEC/v1 -type f -print 2>/dev/null ) \
      | LC_ALL=C sort | while IFS= read -r _sf_rel; do
          [[ -n "$_sf_rel" ]] || continue
          _sf_h="$( _hash_file "$_sf_root/$_sf_rel" 2>/dev/null || true )"
          if [[ -z "$_sf_h" ]]; then
            printf 'HASH-FAILED\n'
            break
          fi
          printf '%s  %s\n' "$_sf_h" "$_sf_rel"
        done
  )"
  case "$_sf_lines" in
    ""|*HASH-FAILED*) return 1 ;;
  esac
  printf '%s\n' "$_sf_lines" | _hash_stdin
}


# =============================================================================
# PLAN-167 W2.2 — OBSERVERS.
#
# The callers no longer decide. They observe the nine dimensions, hand them to
# _ownership_verdict, and execute what comes back. Everything below answers a
# question about the world; nothing below chooses an outcome.
#
# That separation is the entire point. In S296 the answer to "is this owned?"
# was recomputed inline at every branch, so two branches could answer the same
# question differently and nothing detected the contradiction.
# =============================================================================

# _ov_obs_live_type <abs path> — lstat vocabulary, never following.
_ov_obs_live_type() {
  _olt_p="$1"
  # Classify NON-REGULAR entries before anything opens the path. `ls -A` on a
  # FIFO blocks forever waiting for a writer, so testing -d before -p turned
  # the observer itself into the hang it was written to detect.
  if   [ -L "$_olt_p" ]; then printf 'symlink'
  elif [ ! -e "$_olt_p" ]; then printf 'absent'
  elif [ -p "$_olt_p" ] || [ -S "$_olt_p" ]; then printf 'special'
  elif [ -d "$_olt_p" ]; then
    if [ -z "$( ls -A "$_olt_p" 2>/dev/null )" ]; then printf 'dir_empty'; else printf 'dir'; fi
  elif [ -f "$_olt_p" ]; then printf 'regular'
  else printf 'special'; fi
}

# _ov_obs_prior_record <relpath> — what the PRE-run sanitized baseline says.
# link_match only when the recorded target still equals the live readlink; a
# LINK row whose target moved is link_retargeted, and so is a LINK row whose
# live path is no longer a symlink at all (readlink yields empty, which never
# equals a recorded non-empty target).
_ov_obs_prior_record() {
  _opr_rel="$1"
  [ -n "${_BASELINE_MANIFEST_FILE:-}" ] && [ -f "$_BASELINE_MANIFEST_FILE" ] || { printf 'none'; return 0; }
  _opr_link="$( grep -E "^LINK  ${_opr_rel}  " "$_BASELINE_MANIFEST_FILE" 2>/dev/null | head -1 || true )"
  if [ -n "$_opr_link" ]; then
    # Fixed double-space delimiter, never whitespace field-splitting: a
    # checkout path containing a space made awk '{print $3}' read an unchanged
    # delivery as redirected.
    _opr_rec="${_opr_link#LINK  ${_opr_rel}  }"
    _opr_live="$( readlink "$TARGET/$_opr_rel" 2>/dev/null || true )"
    if [ -n "$_opr_rec" ] && [ "$_opr_rec" = "$_opr_live" ]; then printf 'link_match'
    else printf 'link_retargeted'; fi
    return 0
  fi
  if grep -Eq "^[0-9a-f]{64}  ${_opr_rel}(/|$)" "$_BASELINE_MANIFEST_FILE" 2>/dev/null; then
    printf 'hash'; return 0
  fi
  printf 'none'
}

# _ov_obs_spec_content — pristine | legacy_pristine | legacy_pristine_partial
#                        | edited | -
# A tree the fingerprint cannot fully inventory is NOT "pristine with a note":
# it is its own observable, because a partial inventory must never certify a
# wholesale replace (ADR-155-AMEND-1 §4).
_ov_obs_spec_content() {
  [ -e "$TARGET/SPEC/v1" ] || { printf '-'; return 0; }
  _osc_fp="$( _spec_tree_fingerprint "$TARGET" 2>/dev/null || true )"
  if [ -z "$_osc_fp" ]; then
    # No fingerprint. Distinguish "cannot inventory" (a non-regular entry is
    # present) from "not comparable at all".
    _osc_odd="$( ( cd "$TARGET" && find SPEC/v1 -mindepth 1 ! -type f ! -type d -print 2>/dev/null ) )"
    if [ -n "$_osc_odd" ]; then printf 'legacy_pristine_partial'; else printf 'edited'; fi
    return 0
  fi
  _osc_src="$( _spec_tree_fingerprint "$SOURCE_DIR" 2>/dev/null || true )"
  if [ -n "$_osc_src" ] && [ "$_osc_fp" = "$_osc_src" ]; then printf 'pristine'; return 0; fi
  for _osc_pf in $_SPEC_PRISTINE_FINGERPRINTS; do
    if [ "$_osc_fp" = "$_osc_pf" ]; then printf 'legacy_pristine'; return 0; fi
  done
  printf 'edited'
}

# _ov_obs_skip <relpath> — none | self | descendant.
# The descendant scan walks the UNION of source and target and includes every
# removable entry, not just regular files: the forced route find-deletes them
# all, so a target-only symlink must be visible to skip detection too.
_ov_obs_skip() {
  _osk_rel="$1"
  if _path_is_skipped "$_osk_rel"; then printf 'self'; return 0; fi
  if [ "$_osk_rel" = "SPEC/v1" ]; then
    _osk_hit=""
    while IFS= read -r _osk_f; do
      [ -n "$_osk_f" ] || continue
      if _path_is_skipped "$_osk_f"; then _osk_hit=1; break; fi
    done <<EOF
$( { ( cd "$SOURCE_DIR" && find SPEC/v1 ! -type d -print 2>/dev/null );
     [ -d "$TARGET/SPEC/v1" ] && ( cd "$TARGET" && find SPEC/v1 ! -type d -print 2>/dev/null ); } | LC_ALL=C sort -u )
EOF
    [ -n "$_osk_hit" ] && { printf 'descendant'; return 0; }
  fi
  printf 'none'
}

# _ov_obs_mode — the delivery mode this run carries. Evidence order: a prior
# LINK record (authoritative), else a symlink probe on the owned roots.
_ov_obs_mode() {
  if [ -n "${_BASELINE_MANIFEST_FILE:-}" ] && [ -f "$_BASELINE_MANIFEST_FILE" ] \
     && grep -Eq '^LINK  ' "$_BASELINE_MANIFEST_FILE" 2>/dev/null; then
    printf 'link'; return 0
  fi
  if [ -L "$TARGET/SPEC/v1" ] || [ -L "$TARGET/.claude/.framework-version" ]; then
    printf 'link'; return 0
  fi
  printf 'copy'
}

# _refresh_spec_contract — SPEC/v1 takes a FORCED route, NOT the generic
# backup_and_replace: for a directory target with a baseline, the classified
# walk PRESERVES adopter edits — so from the 2nd upgrade on, an edited SPEC
# would classify ADOPTER-CUSTOMIZED and the stale-contract class would
# return (r6). SPEC/v1 is the published compliance CONTRACT: an adopter edit
# is a FORK of the contract, not a customization (OQ-3) => backup to
# $BAK_DIR/SPEC/v1 + replace.
#   * ceremony: a recorded `--ceremony user` install NEVER receives SPEC/v1
#     (mirrors install.sh WS4-guard-spec), independent of --no-replay (r9).
#   * ownership: baseline SPEC records => framework-owned (forced refresh);
#     no target SPEC => new delivery; target SPEC with NO record => LEGACY
#     MIGRATION by pristine content (r20): match => framework-owned refresh,
#     no match => ADOPTER-FORK: preserve + snapshot + named WARNING.
#   * root VERSION: this function (and the whole upgrade) NEVER touches it —
#     install_one is skip-if-exists, so on an adopter with its own VERSION
#     the framework never wrote there; backup_and_replace would TAKE the
#     file (the S238/ADR-155 "verified worst case", trap C.5). See
#     ADR-155-AMEND-1 for why the asymmetry is deliberate.
_SPEC_DELIVERED=0
_refresh_spec_contract() {
  local sdir="$SOURCE_DIR/SPEC/v1"
  local ddir="$TARGET/SPEC/v1"
  local bdir="$BAK_DIR/SPEC/v1"

  # ---- OBSERVE -------------------------------------------------------------
  # Nothing here chooses an outcome. Each line answers one question about the
  # world, and the answers go to _ownership_verdict as the nine dimensions.
  local _lt _pr _lc _sh _md _sk
  if _lg_ancestor_is_symlink "$TARGET" "SPEC/v1"; then
    _lt="ancestor_symlink"           # reachable only by writing THROUGH a symlink
  else
    _lt="$( _ov_obs_live_type "$ddir" )"
  fi
  _pr="$( _ov_obs_prior_record "SPEC/v1" )"
  _lc="$( _ov_obs_spec_content )"
  _sh=no; [ -d "$sdir" ] && _sh=yes
  _md="$( _ov_obs_mode )"
  _sk="$( _ov_obs_skip "SPEC/v1" )"

  # ---- DECIDE --------------------------------------------------------------
  local _pair _verdict _hash
  if ! _pair="$( _ownership_verdict spec "$_pr" "$_lt" "$_lc" "$_sh" "$_md" \
                   "$CEREMONY_EFFECTIVE" upgrade "$_sk" )"; then
    # The decision function refuses combinations its legality rules forbid.
    # Fail toward preserve — under-claiming is recoverable, over-claiming is
    # the delete-the-adopter's-file class (ADR-155-AMEND-1 §3).
    echo "    WARNING: SPEC/v1 dimensions are not a legal cell" >&2
    echo "             ($_pr/$_lt/$_lc/$_sh/$_md/$CEREMONY_EFFECTIVE/$_sk) —" >&2
    echo "             PRESERVED without ownership. Please report this combination." >&2
    return 0
  fi
  _verdict="${_pair%% *}"; _hash="${_pair##* }"
  _SPEC_HASH_SOURCE="$_hash"   # consumed by the baseline rewrite

  # ---- EXECUTE -------------------------------------------------------------
  case "$_verdict" in
    PRESERVE_OWNED)
      _SPEC_DELIVERED=1
      case "$_lt/$_sk/$_sh" in
        ancestor_symlink/*/*) echo "    SKIP: SPEC/v1 has a symlinked ancestor (refusing to write through it — F11a)" ;;
        symlink/*/*)          echo "    SKIP: SPEC/v1 is the recorded --mode link delivery (target unchanged)" ;;
        */self/*)             echo "    SKIPPED (--skip): SPEC/v1" ;;
        */descendant/*)       echo "    SKIPPED (--skip matches a descendant): SPEC/v1 refreshes as ONE contract unit — preserving the whole tree" ;;
        */*/no)               echo "    SKIP: SPEC/v1 absent in source (ownership carried forward)" ;;
        *)                    echo "    SKIP: SPEC/v1 (recorded --ceremony user install — root surfaces are out of scope, WS4)" ;;
      esac
      return 0
      ;;

    PRESERVE_UNOWNED|OMIT_RECORD)
      # An adopter-owned surface. The ONLY case that earns a snapshot plus
      # recovery guidance is the true ADOPTER-FORK: content the framework
      # cannot claim, with no gate having refused first.
      if [ "$_lt" = "dir" ] || [ "$_lt" = "dir_empty" ]; then
        if [ "$DRY_RUN" -eq 1 ]; then
          echo "    (dry-run) would PRESERVE (SPEC/v1 ADOPTER-FORK): SPEC/v1"
          return 0
        fi
        local _snap_ok=0
        if mkdir -p "$( dirname "$bdir" )" 2>/dev/null && cp -R "$ddir" "$bdir" 2>/dev/null; then
          _snap_ok=1
        fi
        # The token "ADOPTER-FORK" is CONTRACT, not prose: the §1869 route
        # comment promises a NAMED warning, and the F3 e2e (S4) greps for it.
        # The PLAN-167 rewrite dropped it — caught by that e2e on the PLAN-166
        # land (44/45) and restored here (PLAN-168).
        echo "    WARNING: SPEC/v1 ADOPTER-FORK — not framework-owned (no delivery" >&2
        echo "             record; matches neither this checkout nor any pristine shipped SPEC)" >&2
        if [ "$_snap_ok" -eq 1 ]; then
          echo "             — PRESERVED in place (snapshot in $BAK_DIR/SPEC/v1)." >&2
          echo "             To hand it back to the framework: remove the target SPEC/v1," >&2
          echo "             copy this checkout's tree in, and re-run — a byte-identical" >&2
          echo "             tree is taken over and recorded." >&2
        else
          # Recovery guidance is WITHHELD without a snapshot: following it
          # would destroy the only copy of the fork.
          echo "             — PRESERVED in place, but the forensic snapshot COULD NOT be" >&2
          echo "             created. Back SPEC/v1 up yourself before any manual takeover." >&2
        fi
        _up_record_op "preserve_spec_v1_adopter_fork" "SPEC/v1"
      else
        echo "    SKIP: SPEC/v1 is $_lt — adopter-owned, preserved without ownership" >&2
      fi
      return 0
      ;;

    DELIVER|REFRESH)
      if [ "$DRY_RUN" -eq 1 ]; then
        if [ "$_verdict" = "REFRESH" ]; then
          echo "    (dry-run) would FORCE-REFRESH (backup to $BAK_DIR/SPEC/v1): SPEC/v1"
        else
          echo "    (dry-run) would ADD: SPEC/v1"
        fi
        return 0
      fi
      _up_record_op "refresh_spec_v1" "$_pr/$_lc"

      if [ "$_lt" = "dir" ] || [ "$_lt" = "dir_empty" ]; then
        mkdir -p "$( dirname "$bdir" )" 2>/dev/null || true
        # `|| true` is load-bearing: under `set -euo pipefail` a failing cp
        # KILLS the run before the guard below can refuse the surface, so the
        # upgrade dies mid-way instead of leaving this surface untouched.
        if ! { cp -R "$ddir" "$bdir" 2>/dev/null || false; }; then
          # INV-3: an execution failure NEVER advances the record. The surface
          # is left exactly as it was, and so is its prior ownership record.
          echo "    WARNING: could not back up SPEC/v1 — REFUSING to replace it" >&2
          echo "             (backup-before-replace is the contract; surface untouched)" >&2
          # INV-3: the REFRESH did not happen, so the record must not advance
          # to source hashes. Retain the prior digest with the ownership.
          _up_record_op "preserve_spec_v1_backup_failed" "SPEC/v1"
          if [ "$_pr" = "hash" ]; then
            _SPEC_DELIVERED=1
            _SPEC_HASH_SOURCE="HASH_PRIOR_RECORD"
          fi
          return 0
        fi
        echo "    BACKED UP: SPEC/v1 -> $BAK_DIR/SPEC/v1"
        find "$ddir" -mindepth 1 -delete
        rmdir "$ddir" 2>/dev/null || true
      elif [ "$_lt" = "regular" ]; then
        mkdir -p "$( dirname "$bdir" )"
        if cp "$ddir" "$bdir" 2>/dev/null; then
          rm -f "$ddir"
          echo "    BACKED UP: SPEC/v1 (non-directory) -> $BAK_DIR/SPEC/v1"
        else
          echo "    WARNING: could not back up non-directory SPEC/v1 — REFUSING to remove it" >&2
          # INV-3: the REFRESH did not happen, so the record must not advance
          # to source hashes. Retain the prior digest with the ownership.
          _up_record_op "preserve_spec_v1_backup_failed" "SPEC/v1"
          if [ "$_pr" = "hash" ]; then
            _SPEC_DELIVERED=1
            _SPEC_HASH_SOURCE="HASH_PRIOR_RECORD"
          fi
          return 0
        fi
      fi

      mkdir -p "$( dirname "$ddir" )"
      cp -R "$sdir" "$ddir"
      _SPEC_DELIVERED=1
      echo "    REFRESHED (forced — $_pr/$_lc): SPEC/v1"
      return 0
      ;;
  esac
}

# _refresh_framework_marker — FORCED + VALIDATED write (r20 option (a)):
# the marker is generated-refresh content — the upgrade rewrites it to the
# source VERSION every run, backs up a differing pre-existing copy, and
# read-back-validates the write. A marker the upgrade could not validate is
# NOT recorded as delivered, so the FMS entry (and every marker-first
# reader keyed off the SAME record) falls back to VERSION instead of
# trusting a stale value. Delivered in BOTH ceremonies (inside .claude/).
_MARKER_DELIVERED=0
_refresh_framework_marker() {
  local src="$SOURCE_DIR/.claude/.framework-version"
  local dst="$TARGET/.claude/.framework-version"
  local bak="$BAK_DIR/.claude/.framework-version"

  # ---- OBSERVE -------------------------------------------------------------
  local _lt _pr _lc _sh _md _sk
  if _lg_ancestor_is_symlink "$TARGET" ".claude/.framework-version"; then
    _lt="ancestor_symlink"
  else
    _lt="$( _ov_obs_live_type "$dst" )"
  fi
  _pr="$( _ov_obs_prior_record ".claude/.framework-version" )"
  _sh=no; [ -f "$src" ] && _sh=yes
  # Inspect CONTENT only for a regular file. `cmp` on a FIFO blocks waiting for
  # a writer, hanging the upgrade before the verdict can say PRESERVE_UNOWNED —
  # the third instance of "a reader opens what lstat already classified"
  # (codex W3 r4 P1; the OWN-0029 timeout).
  if [ "$_lt" != "regular" ]; then
    _lc="-"
  elif [ "$_sh" = yes ] && cmp -s "$src" "$dst" 2>/dev/null; then
    _lc="pristine"
  else
    _lc="edited"
  fi
  _md="$( _ov_obs_mode )"
  _sk="$( _ov_obs_skip ".claude/.framework-version" )"

  # ---- DECIDE --------------------------------------------------------------
  local _pair _verdict
  if ! _pair="$( _ownership_verdict marker "$_pr" "$_lt" "$_lc" "$_sh" "$_md" \
                   "$CEREMONY_EFFECTIVE" upgrade "$_sk" )"; then
    echo "    WARNING: .claude/.framework-version dimensions are not a legal cell" >&2
    echo "             — PRESERVED without ownership. Please report this combination." >&2
    return 0
  fi
  _verdict="${_pair%% *}"
  _MARKER_HASH_SOURCE="${_pair##* }"

  # ---- EXECUTE -------------------------------------------------------------
  case "$_verdict" in
    PRESERVE_OWNED)
      _MARKER_DELIVERED=1
      case "$_lt/$_sk" in
        ancestor_symlink/*) echo "    SKIP: .claude/.framework-version has a symlinked ancestor (refusing to write through it — F11a)" ;;
        symlink/*)          echo "    SKIP: .claude/.framework-version is the recorded --mode link delivery (target unchanged)" ;;
        */self)             echo "    SKIPPED (--skip): .claude/.framework-version" ;;
        *)                  echo "    SKIP: .claude/.framework-version (ownership carried forward)" ;;
      esac
      return 0
      ;;

    OMIT_RECORD|PRESERVE_UNOWNED)
      if [ "$_sh" = no ]; then
        # The documented --pin downgrade: this source predates the marker, so a
        # retained record would keep advertising a newer version over older
        # content. Readers fall back to VERSION, which the pin DID update.
        echo "    SKIP: .claude/.framework-version absent in source (pre-v1.3.0 checkout)"
        if [ "$_pr" != "none" ]; then
          echo "    NOTE: the prior delivery record is NOT carried forward — version" >&2
          echo "          readers fall back to VERSION (which reflects the pinned source)" >&2
        fi
      elif [ "$_lt" = "symlink" ]; then
        echo "    WARNING: .claude/.framework-version is a symlink that does NOT match the" >&2
        echo "             recorded LINK delivery — preserved WITHOUT framework ownership" >&2
        echo "             (readers fall back to VERSION)" >&2
      else
        echo "    SKIP: .claude/.framework-version is $_lt — adopter-owned, refusing to write into/through it"
      fi
      return 0
      ;;

    DELIVER|REFRESH)
      if [ "$DRY_RUN" -eq 1 ]; then
        echo "    (dry-run) would REFRESH: .claude/.framework-version ($(tr -d '[:space:]' < "$src" 2>/dev/null || true))"
        return 0
      fi
      if [ "$_verdict" = "REFRESH" ] && [ "$_lc" = "edited" ]; then
        mkdir -p "$( dirname "$bak" )" 2>/dev/null || true
        if { cp "$dst" "$bak" 2>/dev/null || false; }; then
          echo "    BACKED UP: .claude/.framework-version -> $bak"
        else
          # INV-3: an execution failure never advances the record.
          echo "    WARNING: could not back up differing .claude/.framework-version —" >&2
          echo "             REFUSING to overwrite it (backup-before-replace)" >&2
          # INV-3, same as the SPEC branch above.
          _up_record_op "preserve_marker_backup_failed" ".claude/.framework-version"
          if [ "$_pr" = "hash" ]; then
            _MARKER_DELIVERED=1
            _MARKER_HASH_SOURCE="HASH_PRIOR_RECORD"
          fi
          return 0
        fi
      fi
      mkdir -p "$( dirname "$dst" )"
      cp "$src" "$dst"
      # Read-back validation: a write that cannot be confirmed is NOT recorded
      # as delivered, so every marker-first reader falls back to VERSION rather
      # than trusting a value the upgrade could not verify.
      if cmp -s "$src" "$dst" 2>/dev/null; then
        _MARKER_DELIVERED=1
        _up_record_op "refresh_framework_marker" "$(tr -d '[:space:]' < "$src" 2>/dev/null || true)"
        echo "    REFRESHED: .claude/.framework-version ($(tr -d '[:space:]' < "$dst" 2>/dev/null || true))"
      else
        echo "    WARNING: .claude/.framework-version write did not validate — NOT recorded as" >&2
        echo "             delivered (marker-first readers fall back to VERSION; r20)" >&2
      fi
      return 0
      ;;
  esac
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


# ===========================================================================
# PLAN-163 T5.4 — BASELINE-AWARE settings migration (3-state per LEAF KEY).
# ---------------------------------------------------------------------------
# WHY: the H8 merge above only registers lifecycle hooks — an adopter whose
# settings.json is otherwise preserved would NEVER receive the Claude-5
# fleet refresh (availableModels/fallbackModel) nor the defaultMode posture.
# This step migrates EXACTLY the leaf keys enumerated in _T54_BASELINES_JSON
# (the normative table above) with an explicit, IDEMPOTENT policy per key:
#   ABSENT                    -> write the NEW baseline
#   EQUAL to the OLD baseline -> update to the NEW baseline
#       (arrays byte-compared: exact values in exact order)
#   CUSTOMIZED (anything else)-> PRESERVE + named WARNING (never clobber)
#   already at the NEW baseline -> no-op (so a re-run changes nothing)
# New-event registrations (DirectoryAdded/Notification) are added ONLY when
# not yet registered AND the T3.4 version-floor feature gate is on
# (_t34_new_event_registrations_enabled). Customized registrations under the
# same events — and every other hooks entry/settings key — stay untouched.
# PLAN-164 W1 (ADR-110-AMEND-1, recalibrated by ADR-110-AMEND-2): the
# check_pair_rail.py PreToolUse registration TIMEOUT VALUE migrates under
# the same 3-state policy — any frozen SUPERSEDED SHIPPED cap (60, 150)
# -> the cap DERIVED from the template artifact
# (templates/settings/settings.base.json pair-rail entry; install.sh copies
# it verbatim, so template value == post-install value == migration target);
# any other adopter-chosen value is PRESERVED + named WARNING; idempotent.
# The file is rewritten ONLY when at least one key actually changed (atomic
# same-directory tempfile + os.replace), so running the upgrade twice is
# byte-identical (idempotency oracle). Fail-open per CLAUDE.md §4: missing
# python3 / unreadable settings / write error => stderr NOTE + the upgrade
# proceeds; a backup always lands under $BAK_DIR first on non-dry runs.
# Opt out: --no-settings-migrate. --dry-run previews every verdict.
# ===========================================================================
_migrate_settings_baseline() {
  [[ "$SETTINGS_MIGRATE" -eq 1 ]] || return 0
  local settings="$TARGET/.claude/settings.json"
  if [[ ! -f "$settings" ]]; then
    echo "    NOTE: settings baseline migration skipped — no $settings (fresh install builds it from template)" >&2
    return 0
  fi
  if ! command -v python3 >/dev/null 2>&1; then
    echo "    NOTE: settings baseline migration skipped (python3 not found) — advisory only" >&2
    return 0
  fi

  echo ""
  echo "==> Settings baseline migration (PLAN-163 T5.4 — 3-state per leaf key)"

  local _mig_mode="apply"
  local _mig_gate="0"
  # PLAN-164 W1: the pair-rail registration-timeout migration target is
  # DERIVED from the source template artifact (see the helper below).
  local _mig_template="$SOURCE_DIR/templates/settings/settings.base.json"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    _mig_mode="preview"
  fi
  if _t34_new_event_registrations_enabled; then
    _mig_gate="1"
  fi

  if [[ "$_mig_mode" == "apply" ]]; then
    _up_record_op "migrate_settings_baseline" "3-state per-leaf-key settings migration (T5.4)"
    mkdir -p "$BAK_DIR/.claude" 2>/dev/null || true
    cp "$settings" "$BAK_DIR/.claude/settings.json.pre-t54-migration" 2>/dev/null || true
    echo "    BACKED UP: .claude/settings.json -> $BAK_DIR/.claude/settings.json.pre-t54-migration"
  fi

  # argv-pass invocation (never source-string interpolation); python3 -I +
  # PYTHONNOUSERSITE=1 shrink the env-driven import surface (same idiom as
  # the B2 state reader/writer above).
  if ! PYTHONNOUSERSITE=1 python3 -I -c '
import json, os, sys, tempfile

mode = sys.argv[1]
path = sys.argv[2]
baselines = json.loads(sys.argv[3])
emit_new = sys.argv[4] == "1"
dry = mode == "preview"
MISSING = object()


def out(msg):
    sys.stdout.write("    " + msg + "\n")


def warn(msg):
    sys.stderr.write("    " + msg + "\n")


def act(msg):
    if dry:
        out("(dry-run) would " + msg)
    else:
        out(msg)


try:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
except (OSError, ValueError):
    sys.exit(3)
if not isinstance(data, dict):
    sys.exit(3)

changed = [False]

# --- 3-state policy, top-level ARRAY leaf keys (byte-compared: exact
# --- values in exact order; a re-ordered array counts as CUSTOMIZED).
# --- eff_available_models captures the EFFECTIVE availableModels value AFTER
# --- this loop resolves its branch (SET/MIGRATE => new baseline; already-new
# --- or CUSTOMIZED => the current value PRESERVED). It is computed
# --- independently of the `if not dry` write guard so it holds in BOTH apply
# --- and dry-run modes, and it is the allowlist the model-pin SET below must
# --- respect (this loop runs BEFORE the model leaf — order is normative).
eff_available_models = MISSING
for key in ("availableModels", "fallbackModel"):
    spec = baselines[key]
    cur = data.get(key, MISSING)
    resolved = cur  # the effective value the key WILL carry post-migration
    if cur is MISSING:
        if not dry:
            data[key] = list(spec["new"])
        resolved = list(spec["new"])
        changed[0] = True
        act("SET (absent -> new baseline): " + key)
    elif cur == spec["new"]:
        out("OK (already at new baseline): " + key)
    elif cur == spec["old"]:
        if not dry:
            data[key] = list(spec["new"])
        resolved = list(spec["new"])
        changed[0] = True
        act("MIGRATE (matched OLD baseline -> new baseline): " + key)
    else:
        warn("WARNING: " + key + " is ADOPTER-CUSTOMIZED - PRESERVED "
             "(not migrated to the new baseline)")
    if key == "availableModels":
        eff_available_models = resolved

# --- model (top-level SCALAR session-default pin; ADR-181 T1.1 anti-silent-
# --- flip). The OLD baseline has NO top-level "model" leaf, so ABSENCE == the
# --- old baseline: SET the new pin. An EXPLICIT null is treated as ABSENT for
# --- the SET decision (null is not a deliberate model choice — no session-
# --- default pin), NOT as a customized value. The SET is CONDITIONAL on the
# --- pin being a member of the EFFECTIVE availableModels resolved above (C6):
# --- an adopter who customized availableModels to EXCLUDE claude-opus-5 would
# --- otherwise get a session-default pin OUTSIDE their own allowlist, which
# --- enforceAvailableModels rejects. If the pin is not provably in the
# --- effective allowlist (excluded, or the allowlist is not a JSON list we can
# --- test) we do NOT pin and emit a NAMED warn, leaving the session default to
# --- the harness/adopter. Any PRESENT non-null value != the new pin is adopter-
# --- custom -> PRESERVED with a named WARN (never re-flipped); no-value-echo
# --- (the adopter value is not printed, only the key name).
spec = baselines["model"]
pin = spec["new"]
cur = data.get("model", MISSING)
absent_or_null = cur is MISSING or cur is None
pin_in_effective_allowlist = (
    isinstance(eff_available_models, list) and pin in eff_available_models
)
if absent_or_null:
    if pin_in_effective_allowlist:
        if not dry:
            data["model"] = pin
        changed[0] = True
        act("SET (absent [== old baseline] -> new baseline): model")
    else:
        warn("WARNING: model pin NOT applied: adopter availableModels "
             "excludes claude-opus-5 (session default left to "
             "harness/adopter)")
elif cur == pin:
    out("OK (already at new baseline): model")
else:
    warn("WARNING: model is ADOPTER-CUSTOMIZED - PRESERVED "
         "(not migrated to the new baseline)")

# --- permissions.defaultMode (read contract: effective_config.py
# --- :178-180,534-542 - a stripped string under the permissions object).
spec = baselines["permissions.defaultMode"]
perms = data.get("permissions", MISSING)
if perms is MISSING:
    if not dry:
        data["permissions"] = {"defaultMode": spec["new"]}
    changed[0] = True
    act("SET (absent -> new baseline): permissions.defaultMode")
elif not isinstance(perms, dict):
    warn("WARNING: permissions is not an object - PRESERVED "
         "(permissions.defaultMode not migrated)")
else:
    cur = perms.get("defaultMode", MISSING)
    curs = cur.strip() if isinstance(cur, str) else None
    if cur is MISSING:
        if not dry:
            perms["defaultMode"] = spec["new"]
        changed[0] = True
        act("SET (absent -> new baseline): permissions.defaultMode")
    elif curs == spec["new"]:
        out("OK (already at new baseline): permissions.defaultMode")
    elif curs == spec["old"]:
        if not dry:
            perms["defaultMode"] = spec["new"]
        changed[0] = True
        act("MIGRATE (matched OLD baseline -> new baseline): "
            "permissions.defaultMode")
    else:
        extra = ""
        if curs == "bypassPermissions":
            extra = (" (NOTE: bypassPermissions is flagged by the "
                     "ConfigChange tamper guard)")
        warn("WARNING: permissions.defaultMode is ADOPTER-CUSTOMIZED - "
             "PRESERVED (not migrated)" + extra)


def registers(block, fname):
    if not isinstance(block, dict):
        return False
    hs = block.get("hooks")
    if not isinstance(hs, list):
        return False
    for h in hs:
        if isinstance(h, dict) and fname in str(h.get("command", "")):
            return True
    return False


# --- New-event registrations (T3.4 FEATURE-GATED). Customized entries under
# --- the same events, and every other hooks key, are preserved untouched.
regs = baselines.get("registrations", {})
if not emit_new:
    out("NOTE: new-event registrations (" + ", ".join(sorted(regs))
        + ") GATED OFF (T3.4 version-floor) - not added")
else:
    hooks = data.get("hooks", MISSING)
    if hooks is MISSING:
        hooks = {}
        if not dry:
            data["hooks"] = hooks
    if not isinstance(hooks, dict):
        warn("WARNING: hooks is not an object - PRESERVED "
             "(new-event registrations not added)")
    else:
        for event in sorted(regs):
            fname = regs[event]["match"]
            entry = regs[event]["entry"]
            lst = hooks.get(event, MISSING)
            if lst is MISSING:
                if not dry:
                    hooks[event] = [entry]
                changed[0] = True
                act("ADD (absent -> canonical registration): hooks." + event)
            elif isinstance(lst, list):
                if any(registers(b, fname) for b in lst):
                    out("OK (canonical registration already present): hooks."
                        + event)
                else:
                    if not dry:
                        lst.append(entry)
                    changed[0] = True
                    act("ADD (canonical registration appended; existing "
                        "custom entries preserved): hooks." + event)
            else:
                warn("WARNING: hooks." + event + " is not a list - PRESERVED "
                     "(canonical registration not added)")

# --- PLAN-164 W1 (ADR-110-AMEND-1) — pair-rail registration-timeout VALUE
# --- migration. WHY: the harness kills a hook at its settings.json
# --- registration timeout, and the pre-PLAN-164 cap (60s) sat BELOW the
# --- measured codex verdict latency (p95 ~75s under load; 12/12 historical
# --- pair_rail_case rows were F/TIMEOUT — PLAN-163/probes/
# --- GATE-V2-2026-07-29-FAIL-diagnosis.md). Ratified semantics
# --- (OQ2=150, recalibrated to 210 by ADR-110-AMEND-2): bump the
# --- check_pair_rail.py PreToolUse registration timeout IFF the current
# --- value is one of the SUPERSEDED SHIPPED caps; ANY other
# --- adopter-chosen value is PRESERVED (named WARN); already-at-target is
# --- a no-op; an entry with NO timeout key is left untouched (harness
# --- default, not an adopter choice of an old cap). The NEW cap is
# --- DERIVED from the template artifact
# --- (settings.base.json pair-rail entry — install.sh copies it verbatim,
# --- so template value == post-install value == migration target); each
# --- OLD cap is a frozen historical literal (none exists in any live
# --- artifact once this migration lands), exactly like the "old" column of
# --- the T5.4 table above. Fail-open: an unreadable template or a
# --- non-unique/non-int template cap skips ONLY this leaf (stderr NOTE) —
# --- the rest of the migration is unaffected.
# ADR-110-AMEND-2: the set of SUPERSEDED SHIPPED defaults, not a single
# literal. 60 was the pre-PLAN-164 cap; 150 was the PLAN-164/AMEND-1 cap
# shipped in v1.2.0 and superseded by the AMEND-2 value 210. A v1.2.0
# adopter sits at exactly 150, and leaving it there is NOT conservative:
# with the hook-internal default now 180, a 150s registration lets the
# HARNESS kill the hook BEFORE the internal codex cap fires -- and a
# killed hook emits NO pair_rail_case at all (AMEND-2 section 6:
# fail-open with no event, invisible to the instrument in both numerator
# and denominator). That is strictly worse than the case F it replaces,
# so a shipped default must keep migrating. Every member is a frozen
# historical literal that no longer exists in any live artifact; an
# adopter value outside this set is a genuine choice and stays PRESERVED
# + WARNED.
# NOTE: this whole block is a bash SINGLE-QUOTED -c string. No apostrophe
# may appear anywhere in it -- one terminates the string and silently
# turns the migration into a no-op (the tests then read the seeded value
# back unchanged, which looks like a logic bug, not a quoting bug).
OLD_PAIR_RAIL_CAPS = (60, 150)
template_path = sys.argv[5]


def pair_rail_hooks(obj):
    found = []
    hooks_obj = obj.get("hooks")
    blocks = hooks_obj.get("PreToolUse") if isinstance(hooks_obj, dict) else None
    for block in blocks if isinstance(blocks, list) else []:
        if not isinstance(block, dict):
            continue
        hs = block.get("hooks")
        if not isinstance(hs, list):
            continue
        for h in hs:
            if isinstance(h, dict) and \
                    "check_pair_rail.py" in str(h.get("command", "")):
                found.append(h)
    return found


new_cap = None
tpl_status = None
try:
    with open(template_path, "r", encoding="utf-8") as f:
        _tpl_hooks = pair_rail_hooks(json.load(f))
    tpl_caps = [h.get("timeout") for h in _tpl_hooks]
    if len(tpl_caps) == 1 and type(tpl_caps[0]) is int:
        new_cap = tpl_caps[0]
        _sm = _tpl_hooks[0].get("statusMessage")
        if isinstance(_sm, str) and _sm.strip():
            tpl_status = _sm
except (OSError, ValueError):
    new_cap = None
if new_cap is None:
    warn("NOTE: pair-rail registration-timeout migration skipped - template "
         "pair-rail cap not derivable (advisory only; other keys unaffected)")
else:
    for h in pair_rail_hooks(data):
        cur = h.get("timeout", MISSING)
        if cur is MISSING:
            continue
        if cur == new_cap:
            out("OK (already at template cap): pair-rail registration timeout")
        elif cur in OLD_PAIR_RAIL_CAPS:
            if not dry:
                h["timeout"] = new_cap
                # grok r1 LOW-3 / codex r2: bring the template statusMessage
                # along IFF absent (same leaf, same migration event; an
                # adopter-customized statusMessage is never overwritten).
                if tpl_status is not None and "statusMessage" not in h:
                    h["statusMessage"] = tpl_status
            changed[0] = True
            act("MIGRATE (matched OLD pair-rail cap -> template cap"
                " + statusMessage if absent): "
                "hooks.PreToolUse[check_pair_rail.py].timeout")
        else:
            warn("WARNING: pair-rail registration timeout is "
                 "ADOPTER-CUSTOMIZED - PRESERVED (not migrated)")

if dry:
    sys.exit(0)
if not changed[0]:
    out("no changes - settings.json already at baseline (idempotent no-op)")
    sys.exit(0)
d = os.path.dirname(path) or "."
fd, tmp = tempfile.mkstemp(prefix=".settings-t54-migrate.", suffix=".tmp",
                           dir=d)
try:
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.write("\n")
    os.replace(tmp, path)
except BaseException:
    try:
        os.unlink(tmp)
    except OSError:
        pass
    sys.exit(3)
out("WROTE: .claude/settings.json (atomic; only migrated leaf keys changed)")
' "$_mig_mode" "$settings" "$_T54_BASELINES_JSON" "$_mig_gate" "$_mig_template"; then
    # NAMED skip (not a silent one): the helper exits 3 on an unparseable /
    # unreadable settings.json (json.load failed) OR on an atomic-write
    # failure. Either way the leaf keys were NOT migrated. Preservation is
    # correct (we never clobber a file we could not parse), but the skip
    # MUST be visible + actionable — hence the explicit re-run pointer.
    echo "    NOTE: settings baseline migration SKIPPED — settings.json was not migrated" >&2
    echo "          (most likely .claude/settings.json is unparseable/corrupt JSON, or the" >&2
    echo "          atomic write failed). settings.json is UNCHANGED (fail-open; the write is" >&2
    echo "          atomic, a partial write never lands). Model/permission baselines were NOT" >&2
    echo "          applied — ACTION: fix/validate the JSON, then re-run the migration alone:" >&2
    echo "              scripts/upgrade.sh \"$TARGET\" --settings-migrate-only" >&2
    echo "          Pre-migration backup: $BAK_DIR/.claude/settings.json.pre-t54-migration" >&2
  fi
  return 0
}

# ===========================================================================
# PLAN-161 U3 — opt-in hash-gated purge of mis-installed framework-internal
# files (--purge-misinstalled; OQ1 Owner-ratified; ADR-155 Amendment).
# ---------------------------------------------------------------------------
# The 2026-07-21 adopter upgrade (bug 2b) shipped the framework's OWN dogfood
# test trees (~967 files) into adopters. U2 stops the (re)install; this scan
# is the cleanup for residue already present:
#   * NOMINATION is a hardcoded walk of the excluded TREES + 2 files under
#     $TARGET only — NEVER manifest-driven (an unsigned manifest must never
#     be able to nominate arbitrary paths for deletion).
#   * lstat/no-follow: find WITHOUT -L; symlinks are reported + skipped.
#   * Relpaths pass the manifest-grade sanitizer (_baseline_relpath_unsafe);
#     anything unsafe is kept + warned, never purged.
#   * AUTHORIZATION per candidate: sha256(target file) equals the CURRENT
#     framework source bytes at the SAME relpath, OR equals the recorded
#     target-manifest baseline digest for that rel (_baseline_lookup). A
#     byte-identical copy at a DIFFERENT relpath is NEVER authorized.
#     Neither match => keep + warn.
#   * Default (flag absent) and ALL --dry-run runs: preview only ('would
#     PURGE' lines + a --purge-misinstalled hint). Deletion requires the
#     explicit flag on a non-dry run, is backed up first (cp -P into
#     $BAK_DIR/<rel>), and a second run is a no-op (nothing authorized left).
# ===========================================================================
_PM_AUTH_COUNT=0
_PM_PURGED_COUNT=0

# PLAN-161 U3 (codex r4 F2): find(1) resolves its COMMAND-LINE path through
# symlinked ANCESTORS even without -L — only descent below the start point is
# no-follow. So a nominated excluded tree whose ancestor (e.g. .claude/hooks
# preserved via --skip as an adopter symlink) is a symlink would be walked —
# and, once any purge elsewhere makes _PM_PURGED_COUNT positive, rmdir'd —
# INSIDE the symlink's external target. Guard: before any find/rmdir over a
# nominated path, walk every component from $TARGET down to the leaf with a
# per-component lstat (same idiom as _baseline_relpath_unsafe) and refuse the
# whole tree when ANY component is a symlink. On hit, prints the first
# symlinked component's target-relative path to stdout and returns 0; returns
# 1 when the component chain is symlink-free. bash-3.2-safe (IFS walk).
_purge_tree_symlinked_component() {
  _pts_rel="$1"
  _pts_cur="$TARGET"
  _pts_relcur=""
  _pts_oldIFS="$IFS"
  IFS='/'
  for _pts_comp in $_pts_rel; do
    [ -n "$_pts_comp" ] || continue
    [ "$_pts_comp" = "." ] && continue
    _pts_cur="$_pts_cur/$_pts_comp"
    if [ -n "$_pts_relcur" ]; then
      _pts_relcur="$_pts_relcur/$_pts_comp"
    else
      _pts_relcur="$_pts_comp"
    fi
    if [ -L "$_pts_cur" ]; then
      IFS="$_pts_oldIFS"
      printf '%s\n' "$_pts_relcur"
      return 0
    fi
  done
  IFS="$_pts_oldIFS"
  return 1
}

# Evaluate ONE nominated candidate relpath (already lstat-screened as a
# regular file by the caller). Prints exactly one verdict line.
_purge_consider_one() {
  local _pc_rel="$1"
  local _pc_dst="$TARGET/$_pc_rel"
  local _pc_h_dst="" _pc_h_src="" _pc_h_base="" _pc_auth=0
  if _baseline_relpath_unsafe "$_pc_rel"; then
    echo "    KEPT (excluded-tree file outside provenance rails — not purged): $_pc_rel"
    return 0
  fi
  _pc_h_dst="$( _hash_file "$_pc_dst" 2>/dev/null || true )"
  if [[ -n "$_pc_h_dst" && -f "$SOURCE_DIR/$_pc_rel" && ! -L "$SOURCE_DIR/$_pc_rel" ]]; then
    _pc_h_src="$( _hash_file "$SOURCE_DIR/$_pc_rel" 2>/dev/null || true )"
  fi
  _pc_h_base="$( _baseline_lookup "$_pc_rel" 2>/dev/null || true )"
  if [[ -n "$_pc_h_dst" && -n "$_pc_h_src" && "$_pc_h_dst" == "$_pc_h_src" ]]; then
    _pc_auth=1
  elif [[ -n "$_pc_h_dst" && -n "$_pc_h_base" && "$_pc_h_dst" == "$_pc_h_base" ]]; then
    _pc_auth=1
  fi
  if [[ "$_pc_auth" -ne 1 ]]; then
    echo "    KEPT (excluded-tree file outside provenance rails — not purged): $_pc_rel"
    return 0
  fi
  _PM_AUTH_COUNT=$(( _PM_AUTH_COUNT + 1 ))
  if [[ "$PURGE_MISINSTALLED" -eq 1 && "$DRY_RUN" -eq 0 ]]; then
    # PLAN-161 U3 (codex r1 F6): every filesystem step here is per-candidate
    # guarded — under `set -e` an unguarded mkdir/cp/rm permission error would
    # abort the WHOLE upgrade mid-purge. Backup failure => KEPT (never delete
    # without a good backup); delete failure AFTER a good backup => warn +
    # continue. The purge scan never changes the upgrade exit status.
    if ! mkdir -p "$( dirname "$BAK_DIR/$_pc_rel" )" 2>/dev/null; then
      echo "    KEPT (backup dir create failed — not purged): $_pc_rel" >&2
      return 0
    fi
    if ! cp -P "$_pc_dst" "$BAK_DIR/$_pc_rel" 2>/dev/null; then
      echo "    KEPT (backup copy failed — not purged): $_pc_rel" >&2
      return 0
    fi
    if ! rm -f "$_pc_dst" 2>/dev/null; then
      echo "    KEPT (delete failed after backup — file left in place): $_pc_rel" >&2
      return 0
    fi
    _up_record_op "purge_misinstalled" "$_pc_rel"
    echo "    PURGED (mis-installed framework-internal; backup in $BAK_DIR/$_pc_rel): $_pc_rel"
    _PM_PURGED_COUNT=$(( _PM_PURGED_COUNT + 1 ))
  else
    echo "    would PURGE (mis-installed framework-internal): $_pc_rel"
  fi
  return 0
}

_purge_misinstalled_scan() {
  if ! command -v _hash_file >/dev/null 2>&1; then
    echo "    NOTE: mis-install scan skipped — hash helpers not sourced (fail-open)" >&2
    return 0
  fi
  local _pm_trees=( ".claude/hooks/tests" ".claude/hooks/legacy" ".claude/scripts/tests" ".claude/hooks/_lib/tests" )
  local _pm_files=( ".claude/hooks/_lib/test_isolation.py" ".claude/hooks/_lib/testing.py" )
  local _pm_t _pm_cand _pm_rel _pm_link
  _PM_AUTH_COUNT=0
  _PM_PURGED_COUNT=0

  for _pm_t in "${_pm_trees[@]}"; do
    # codex r4 F2: refuse the whole tree when ANY component from $TARGET down
    # to the leaf is a symlink — never hand find(1) a path it would resolve
    # through a symlinked ancestor into an external target.
    _pm_link="$( _purge_tree_symlinked_component "$_pm_t" )" || _pm_link=""
    if [[ -n "$_pm_link" ]]; then
      if [[ "$_pm_link" == "$_pm_t" ]]; then
        echo "    KEPT (symlink in excluded tree — never followed): $_pm_t"
      else
        echo "    KEPT (symlinked ancestor '$_pm_link' — tree never walked): $_pm_t"
      fi
      continue
    fi
    [[ -d "$TARGET/$_pm_t" ]] || continue
    while IFS= read -r _pm_cand; do
      [[ -n "$_pm_cand" ]] || continue
      _pm_rel="${_pm_cand#"$TARGET"/}"
      if [[ -L "$_pm_cand" ]]; then
        echo "    KEPT (symlink in excluded tree — never followed): $_pm_rel"
        continue
      fi
      _purge_consider_one "$_pm_rel"
    done < <( find "$TARGET/$_pm_t" \( -type f -o -type l \) -print 2>/dev/null | LC_ALL=C sort )
  done
  for _pm_rel in "${_pm_files[@]}"; do
    # codex r4 F2: same ancestor guard for the two nominated single files —
    # `-L`/`-f` on the full path would themselves resolve through a symlinked
    # ancestor (e.g. .claude/hooks -> external).
    _pm_link="$( _purge_tree_symlinked_component "$_pm_rel" )" || _pm_link=""
    if [[ -n "$_pm_link" ]]; then
      if [[ "$_pm_link" == "$_pm_rel" ]]; then
        echo "    KEPT (symlink in excluded tree — never followed): $_pm_rel"
      else
        echo "    KEPT (symlinked ancestor '$_pm_link' — file never touched): $_pm_rel"
      fi
      continue
    fi
    [[ -f "$TARGET/$_pm_rel" ]] || continue
    _purge_consider_one "$_pm_rel"
  done

  if [[ "$_PM_PURGED_COUNT" -gt 0 ]]; then
    # Remove the now-empty excluded dirs, children before parents. rmdir
    # only — a dir still holding adopter-owned (kept) files simply stays.
    # codex r4 F2: re-check the component chain HERE too (not only at
    # nomination) — the sweep must never rmdir through a symlinked ancestor
    # into an external target. Silent skip: the KEPT line already printed
    # during nomination.
    for _pm_t in "${_pm_trees[@]}"; do
      if _purge_tree_symlinked_component "$_pm_t" >/dev/null; then
        continue
      fi
      [[ -d "$TARGET/$_pm_t" && ! -L "$TARGET/$_pm_t" ]] || continue
      while IFS= read -r _pm_cand; do
        [[ -n "$_pm_cand" ]] || continue
        rmdir "$_pm_cand" 2>/dev/null || true
      done < <( find "$TARGET/$_pm_t" -depth -type d -print 2>/dev/null )
    done
  fi
  if [[ "$_PM_AUTH_COUNT" -gt 0 && "$PURGE_MISINSTALLED" -eq 0 ]]; then
    echo "    HINT: $_PM_AUTH_COUNT hash-authorized mis-installed file(s) found — re-run with --purge-misinstalled to delete them (each is backed up to .claude.bak/ first)."
  fi
  if [[ "$_PM_AUTH_COUNT" -eq 0 && "$_PM_PURGED_COUNT" -eq 0 ]]; then
    echo "    clean: no hash-authorized mis-installed framework-internal files"
  fi
  return 0
}

# ===========================================================================
# PLAN-163 T5.4 — test/ops seam: run ONLY the settings baseline migration.
# Everything else (tree refresh, agents pin, H8 merge, PROTOCOL pointer,
# purge scan, manifest/state rewrite) is skipped. Honors --dry-run and
# --no-settings-migrate. The fixtures/oracles in
# test_upgrade_settings_migration.py drive the migration through THIS path
# so each key x branch is provable without a full-tree copy.
# ===========================================================================
if [[ "$SETTINGS_MIGRATE_ONLY" -eq 1 ]]; then
  _migrate_settings_baseline
  if [[ -n "${_UP_OPS_FILE:-}" ]]; then rm -f "$_UP_OPS_FILE" 2>/dev/null || true; fi
  echo ""
  echo "==> Done (--settings-migrate-only: no other upgrade surface touched)."
  exit 0
fi

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
# Re-pass rc.4 t3 (smoke STALE) + t5 P1 (ownership): the plans/ SCHEMA
# docs are FRAMEWORK contract files that install.sh seeds but upgrade never
# refreshed — the first framework edit (S305, DEBATE-SCHEMA) left every
# upgraded adopter on the old generation (F3 STALE). But a blanket
# backup_and_replace would CLOBBER an adopter-modified schema (t5 P1: the
# schemas are not in the baseline ownership enumeration for pre-existing
# installs, so classification falls back to legacy overwrite). Refresh is
# therefore HASH-GATED: only a byte-pristine copy of a KNOWN prior
# framework generation is replaced; anything else is PRESERVED loudly.
_refresh_schema_doc() {
  # $1 = rel path; $2.. = sha256 of KNOWN prior framework generations.
  _rsd_rel="$1"; shift
  _rsd_src="$SOURCE_DIR/$_rsd_rel"; _rsd_dst="$TARGET/$_rsd_rel"
  # Re-pass rc.4 t7 P1 (skip contract): --skip excludes this path from
  # inspection AND write, like every other delivery in this script.
  if _path_is_skipped "$_rsd_rel"; then
    echo "    SKIPPED (--skip): $_rsd_rel"
    return 0
  fi
  [ -e "$_rsd_src" ] || { echo "    SKIP (source missing): $_rsd_rel"; return 0; }
  # Re-pass rc.4 t7 P1 (symlink escape): refuse to read or write through a
  # symlinked LEAF (checked before -e: a BROKEN link would otherwise fall
  # into the install branch and cp would create the referent outside the
  # target) or any symlinked ANCESTOR — a --link install's schema symlink,
  # or a hostile .claude/plans link, would make cp modify the referent
  # outside the adopter target. Preservation is the only safe verdict.
  if [ -L "$_rsd_dst" ]; then
    echo "    WARNING: PRESERVED $_rsd_rel (destination is a symlink — a refresh would write through it, outside the target; replace the link manually if that is intended)"
    return 0
  fi
  _rsd_walk="$(dirname "$_rsd_rel")"
  while [ -n "$_rsd_walk" ] && [ "$_rsd_walk" != "." ] && [ "$_rsd_walk" != "/" ]; do
    if [ -L "$TARGET/$_rsd_walk" ]; then
      echo "    WARNING: PRESERVED $_rsd_rel (ancestor $_rsd_walk is a symlink — refusing to write through it)"
      return 0
    fi
    _rsd_walk="$(dirname "$_rsd_walk")"
  done
  if [ ! -e "$_rsd_dst" ]; then
    mkdir -p "$(dirname "$_rsd_dst")"
    cp "$_rsd_src" "$_rsd_dst"
    echo "    INSTALLED: $_rsd_rel"
    return 0
  fi
  # Re-pass rc.4 t7 P1 (hasher portability): the shared _hash_file
  # abstraction, never a bare `shasum` — absent on Perl-less Linux hosts,
  # where set -e would abort the whole upgrade mid-inspection. No usable
  # hasher => ownership cannot be proven => preserve loudly.
  if ! command -v _hash_file >/dev/null 2>&1; then
    echo "    WARNING: PRESERVED $_rsd_rel (no sha256 hasher available — ownership unprovable, not refreshing)"
    return 0
  fi
  if ! _rsd_h_dst="$(_hash_file "$_rsd_dst")" || [ -z "$_rsd_h_dst" ]; then
    echo "    WARNING: PRESERVED $_rsd_rel (no sha256 hasher available — ownership unprovable, not refreshing)"
    return 0
  fi
  if ! _rsd_h_src="$(_hash_file "$_rsd_src")" || [ -z "$_rsd_h_src" ]; then
    echo "    WARNING: PRESERVED $_rsd_rel (no sha256 hasher available — ownership unprovable, not refreshing)"
    return 0
  fi
  if [ "$_rsd_h_dst" = "$_rsd_h_src" ]; then
    echo "    IDENTICAL: $_rsd_rel"
    return 0
  fi
  for _rsd_prior in "$@"; do
    if [ "$_rsd_h_dst" = "$_rsd_prior" ]; then
      mkdir -p "$BAK_DIR/$(dirname "$_rsd_rel")"
      cp "$_rsd_dst" "$BAK_DIR/$_rsd_rel"
      cp "$_rsd_src" "$_rsd_dst"
      echo "    REFRESHED (pristine prior generation): $_rsd_rel"
      return 0
    fi
  done
  echo "    WARNING: PRESERVED adopter-modified $_rsd_rel (framework schema changed upstream — diff it manually; a pristine copy would have been refreshed)"
  return 0
}
if [[ "$DRY_RUN" -eq 1 ]]; then
  # t7 P1 (accurate dry-run): report the per-path --skip verdict instead of
  # a blanket line that hides the exclusion.
  for _rsd_dry in ".claude/plans/PLAN-SCHEMA.md" ".claude/plans/DEBATE-SCHEMA.md"; do
    if _path_is_skipped "$_rsd_dry"; then
      echo "    (dry-run) schema doc SKIPPED (--skip): $_rsd_dry"
    else
      echo "    (dry-run) schema doc hash-gated refresh (pristine prior generations only): $_rsd_dry"
    fi
  done
else
  # sha256 of every shipped prior generation (git history of each file).
  _refresh_schema_doc ".claude/plans/PLAN-SCHEMA.md" \
    "8a2033d241b113544f1e18abbd13f4c60cc6257140f304d95b29216193035232"
  _refresh_schema_doc ".claude/plans/DEBATE-SCHEMA.md" \
    "574bd22e401308400622b1766a9d090e5afede1fb45938995316f38c554f1bf3"
fi
# agent-metrics.md preserved (user data). settings.json is preserved here too —
# ONLY the PLAN-135 W2 H8 settings-merge (additive lifecycle-hook registration)
# and the PLAN-163 T5.4 baseline migration (3-state per leaf key; customized
# values PRESERVED + named WARNING) below touch it; neither clobbers.

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
  # PLAN-161 U1: this writer family (mkdir + cp + awk-rewrite + $BAK_DIR
  # backups) ignored --dry-run entirely (bug 2a, live 2026-07-21). Preview
  # and return before ANY target write.
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "    (dry-run) would REFRESH agent pins: canonical-5"
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

# PLAN-163 T5.4: baseline-aware settings migration — fleet/permission leaf
# keys + (T3.4-gated) new-event registrations. 3-state per key; idempotent;
# customized values are always PRESERVED with a named WARNING.
_migrate_settings_baseline

# DevOps-P1-4: PROTOCOL.md is framework-derived (pointer), not user data —
# refresh it so it stays aligned with the current source layout.
# PLAN-166 F3 (ADR-155-AMEND-1): CEREMONY-GATED — the refresh used to run
# unconditionally and `cat >`-created a root PROTOCOL.md that a
# `--ceremony user` install deliberately never has (install.sh
# WS4-guard-proto forbids root files); the F4 tree-comparison e2e exposes
# exactly this divergence (r7/r13). The gate reads the ceremony from
# .claude/.install-state.json via the replay-independent reader above.
_PROTOCOL_DELIVERED=0
echo ""
echo "==> Refreshing PROTOCOL.md pointer"
if [[ "$CEREMONY_EFFECTIVE" == "user" ]]; then
  echo "    SKIP: PROTOCOL.md pointer (recorded --ceremony user install — a user install never creates root files, WS4; r13)"
  # Ownership continuity on the analogous skip (codex W1 round 7, P2) — see
  # the SPEC/v1 ceremony skip: preserving the tree while erasing its record
  # strands a framework-delivered pointer as unowned.
  #
  # But the flag alone is NOT enough (codex W1 round 9, P1): this skip never
  # runs _refresh_protocol_pointer, so _REFRESH_PROTOCOL_CANON_HASH stays
  # empty, and _write_baseline_manifest then hashes the LIVE pointer —
  # re-recording an adopter-CUSTOMIZED PROTOCOL.md as the framework baseline,
  # which the next upgrade overwrites and uninstall can DELETE. Retaining
  # ownership must never retain the wrong bytes. Carry the PRIOR canonical
  # digest; a LINK record needs none (the link branch of the rewrite fires
  # before the PROTOCOL special case). When neither is available, DROP the
  # claim — the pointer stays adopter-owned and preserved, which is the
  # pre-continuity behaviour and loses nothing.
  if _baseline_has_protocol_record; then
    _REFRESH_PROTOCOL_CANON_HASH="$( _baseline_lookup "PROTOCOL.md" 2>/dev/null || true )"
    if [[ -n "$_REFRESH_PROTOCOL_CANON_HASH" ]] \
       || grep -Eq '^LINK  PROTOCOL\.md(  |$)' "$_BASELINE_MANIFEST_FILE" 2>/dev/null; then
      _PROTOCOL_DELIVERED=1
    else
      echo "    NOTE: PROTOCOL.md delivery record present but its canonical digest is" >&2
      echo "          unrecoverable (ambiguous record) — ownership NOT claimed; the" >&2
      echo "          pointer stays adopter-owned and preserved" >&2
    fi
  fi
else
  # _refresh_protocol_pointer sets _PROTOCOL_DELIVERED itself, from the
  # VERDICT. Forcing it to 1 here overrode a PRESERVE_UNOWNED decision and
  # recorded an adopter's own pre-existing PROTOCOL.md as framework-owned —
  # a caller computing the right answer and then ignoring it (codex W3 r1 P1).
  _refresh_protocol_pointer
fi

# PLAN-166 F3 (ADR-155-AMEND-1): SPEC/v1 forced refresh + framework version
# marker. Both run BEFORE the baseline-manifest rewrite so the delivery
# flags they set are what the rewritten baseline records.
echo ""
echo "==> Refreshing SPEC/v1 contract (PLAN-166 F3 — forced route)"
_refresh_spec_contract

echo ""
echo "==> Refreshing framework version marker (.claude/.framework-version)"
_refresh_framework_marker

# PLAN-177 W1 (P1-1 / CF-9) — the .gitignore surfaces install.sh has always
# delivered and this script never did.
#
# Root .gitignore: two marker-guarded blocks (MCP shared-secret store, PLAN-019
# P2-SEC-H; posture/runtime state, PLAN-165 CX-3). An adopter who installed at
# v1.2.0 and only ever upgrades got /night-mode without the posture ignores, so
# `on` leaves the permission overlay + state marker untracked (PLAN-165 AC-1
# says `git status` stays empty); an adopter older than v1.2.0 never got the
# secrets entry either. The parity gate named the gap and allowlisted it, so CI
# could not fail on it. Both deliveries are ADDITIVE + idempotent and go
# through the SAME generator install.sh calls (INV-4/PLAN-168 W2 — two copies
# of one emitted text is the class that produced the pointer divergence). The
# ORDER (secrets, then posture) mirrors install.sh's two call sites, because it
# decides the order of the blocks in the resulting file.
#
# CEREMONY-GATED, mirroring the PROTOCOL.md skip above: install.sh guards both
# of its calls with `[[ "$CEREMONY" != "user" ]]` (a user install writes no root
# files at all, WS4), so skipping here is what keeps the two routes in
# agreement. A line number would rot the moment either file moves.
#
# Missing generator = broken checkout, fails LOUD. That is install.sh's posture
# for this library, not the preserve-the-surface posture of
# _refresh_protocol_pointer: nothing here overwrites an adopter file, so there
# is no surface a silent degrade would be protecting.
echo ""
echo "==> Refreshing root .gitignore framework blocks (PLAN-019 P2-SEC-H + PLAN-165 CX-3)"
if [[ "$CEREMONY_EFFECTIVE" == "user" ]]; then
  echo "    SKIP: root .gitignore blocks (recorded --ceremony user install — install.sh writes no root files either)"
else
  command -v _mcp_secrets_ignore_entry >/dev/null 2>&1 || {
    echo "    ERROR: _mcp_secrets_ignore_entry unavailable (scripts/_framework_manifest_set.sh not sourced) — cannot ensure the MCP-secrets .gitignore entry" >&2
    exit 1
  }
  command -v _apply_mcp_secrets_ignore >/dev/null 2>&1 || {
    echo "    ERROR: _apply_mcp_secrets_ignore unavailable (scripts/_framework_manifest_set.sh not sourced) — cannot ensure the MCP-secrets .gitignore entry" >&2
    exit 1
  }
  command -v _posture_state_ignore_entries >/dev/null 2>&1 || {
    echo "    ERROR: _posture_state_ignore_entries unavailable (scripts/_framework_manifest_set.sh not sourced) — cannot ensure posture-state .gitignore entries" >&2
    exit 1
  }
  command -v _apply_posture_state_ignores >/dev/null 2>&1 || {
    echo "    ERROR: _apply_posture_state_ignores unavailable (scripts/_framework_manifest_set.sh not sourced) — cannot ensure posture-state .gitignore entries" >&2
    exit 1
  }
  _UP_MCP_ENTRY="$( _mcp_secrets_ignore_entry )"
  _UP_POSTURE_ENTRIES="$( _posture_state_ignore_entries )"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    if [[ -L "$TARGET/.gitignore" ]]; then
      echo "    (dry-run) ERROR: root .gitignore is a symlink — real run would REFUSE" >&2
      exit 1
    fi
    echo "    (dry-run) would ENSURE .gitignore excludes: $_UP_MCP_ENTRY"
    echo "    (dry-run) would ENSURE .gitignore excludes: $_UP_POSTURE_ENTRIES"
  else
    _up_record_op "ensure_mcp_secrets_ignore" "$_UP_MCP_ENTRY"
    _apply_mcp_secrets_ignore "$TARGET/.gitignore"
    _up_record_op "ensure_posture_state_ignores" "$_UP_POSTURE_ENTRIES"
    _apply_posture_state_ignores "$TARGET/.gitignore"
  fi
fi

# `.claude/.gitignore` — delivered in EVERY ceremony, because it lives inside
# .claude/ and therefore reaches the `--ceremony user` population the root
# blocks structurally cannot (verdict-ga-1.txt:5). Create-if-missing, NEVER
# rewritten: adopter-owned after creation, and absent from the baseline
# manifest so no later upgrade can classify it as framework-owned.
echo ""
echo "==> Refreshing .claude/.gitignore (PLAN-177 W1 / CF-9)"
command -v _apply_claude_dir_gitignore >/dev/null 2>&1 || {
  echo "    ERROR: _apply_claude_dir_gitignore unavailable (scripts/_framework_manifest_set.sh not sourced) — cannot ensure .claude/.gitignore" >&2
  exit 1
}
if [[ "$DRY_RUN" -eq 1 ]]; then
  # Shared per-entry preview (re-pass rc.4 t2 P1): a seeded adopter file
  # must report would-APPEND, never a false would-PRESERVE.
  _preview_claude_dir_gitignore "$TARGET/.claude" || exit 1
else
  _up_record_op "ensure_claude_dir_gitignore" ".claude/.gitignore"
  _apply_claude_dir_gitignore "$TARGET/.claude"
fi

# PLAN-161 U3 — mis-install scan/purge. Runs in ALL modes (flag-absent and
# --dry-run runs emit the would-purge PREVIEW; deletion requires the explicit
# --purge-misinstalled flag AND a non-dry run). Runs BEFORE the baseline-
# manifest rewrite below so a purged path is never re-recorded.
echo ""
echo "==> Scanning excluded trees for mis-installed framework-internal files (PLAN-161 U3)"
_purge_misinstalled_scan

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
  # FMS_MODE mirrors the INSTALL's mode, not the upgrade's copy behavior
  # (codex W1-ceremony round, P2): on a --mode link target the refresh
  # branches preserve the symlinks, but a `copy`-mode rewrite would OMIT
  # the SPEC/v1 directory-LINK record and hash the marker symlink as a
  # file — doctor.sh then reports a type-change drift on a healthy tree.
  # Evidence order: prior baseline LINK record (authoritative), else a
  # symlink probe on the framework-owned roots, else copy.
  FMS_MODE="copy"
  if [[ -n "$_BASELINE_MANIFEST_FILE" && -f "$_BASELINE_MANIFEST_FILE" ]] \
     && grep -Eq '^LINK  ' "$_BASELINE_MANIFEST_FILE" 2>/dev/null; then
    FMS_MODE="link"
    # Confine LINK serialization to the paths that ALREADY were LINK records
    # (codex W1 round 10, P2). Without this, inferring link-mode from the
    # prior manifest also promoted every OTHER live symlink — e.g. an
    # adopter's own file under `.claude/hooks/` — into a framework delivery
    # record. The probe branch below leaves FMS_LINK_PATHS unset (no baseline
    # to derive from), keeping its pre-existing behaviour.
    FMS_LINK_PATHS="$( awk '
      {
        idx = index($0, "  ");
        if (idx == 0) next;
        if (substr($0, 1, idx - 1) != "LINK") next;
        rest = substr($0, idx + 2);
        j = index(rest, "  ");
        print (j == 0 ? rest : substr(rest, 1, j - 1));
      }' "$_BASELINE_MANIFEST_FILE" 2>/dev/null || true )"
    export FMS_LINK_PATHS
    echo "    baseline rewrite: --mode link install detected (LINK records in prior manifest) — preserving LINK serialization for $( printf '%s\n' "$FMS_LINK_PATHS" | grep -c . || true ) recorded path(s)"
  elif [[ -L "$TARGET/.claude/skills" || -L "$TARGET/SPEC/v1" || -L "$TARGET/.claude/.framework-version" ]]; then
    FMS_MODE="link"
    echo "    baseline rewrite: --mode link install detected (symlink probe) — preserving LINK serialization"
  fi
  export FMS_MODE
  # Canonical PROTOCOL.md pointer hash (Codex R2 P0): record what the framework
  # WOULD generate, never a preserved adopter customization. Empty if the
  # pointer refresh did not run; the generator then falls back to hashing the
  # target (install semantics).
  export FMS_PROTOCOL_HASH="${_REFRESH_PROTOCOL_CANON_HASH:-}"
  # PLAN-166 F3 (ADR-155-AMEND-1): conditional ownership from what THIS
  # upgrade delivered/refreshed (or what the pre-upgrade baseline already
  # recorded — ownership continuity), never the ceremony alone, never file
  # presence (r17/r19/r20).
  # The decision travels with the delivery flag.
  export FMS_SOURCE_ROOT="$SOURCE_DIR"
  export FMS_PRIOR_MANIFEST="${_BASELINE_MANIFEST_FILE:-}"
  export FMS_HASH_SOURCE_SPEC="${_SPEC_HASH_SOURCE:-}"
  export FMS_HASH_SOURCE_MARKER="${_MARKER_HASH_SOURCE:-}"
  export FMS_HASH_SOURCE_PROTOCOL="${_PROTOCOL_HASH_SOURCE:-}"
  export FMS_DELIVERED_SPEC="${_SPEC_DELIVERED:-0}"
  export FMS_DELIVERED_PROTOCOL="${_PROTOCOL_DELIVERED:-0}"
  export FMS_DELIVERED_MARKER="${_MARKER_DELIVERED:-0}"
  _write_baseline_manifest "$TARGET/.claude/.install-manifest.sha256"
  unset FMS_ROOT FMS_HASH_ROOT FMS_PROFILE_PARTS FMS_MODE FMS_PROTOCOL_HASH FMS_LINK_PATHS
  unset FMS_DELIVERED_SPEC FMS_DELIVERED_PROTOCOL FMS_DELIVERED_MARKER
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
    "harness" "$HARNESS"
    "managed_hooks" "$CODEX_MANAGED_HOOKS"
    "ceremony_effective" "$CEREMONY_EFFECTIVE"
    "ceremony_persist" "$_CEREMONY_PERSIST"
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
# Re-pass rc.4 t3+t5 (P1): persist the ceremony ONLY when it came from a
# RECORD or an EXPLICIT flag/env — never persist the fail-safe inference
# (one missed migration flag would otherwise become permanent, since the
# recorded value wins on every later run). Never overwrite a recorded one.
_cer = vals.get("ceremony_effective", "")
if (vals.get("ceremony_persist", "0") == "1"
        and "ceremony" not in req and _cer in ("maintainer", "user")):
    req["ceremony"] = _cer
# PLAN-155 Wave 5: persist harness so it survives even a pre-Wave-B target
# whose request was synthesized above. Only overwrite when non-empty so a
# claude-only upgrade never clobbers a recorded codex harness with "".
_h = vals.get("harness", "")
if _h in ("claude", "codex"):
    req["harness"] = _h
elif "harness" not in req:
    req["harness"] = "claude"
if vals.get("managed_hooks", "0") == "1":
    req["managed_hooks"] = True
elif "managed_hooks" not in req:
    req["managed_hooks"] = False
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
        "ceremony_effective": vals.get("ceremony_effective", ""),
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
# ----------------------------------------------------------------------
# PLAN-155 Wave 5 — Codex harness refresh (round-trip). When the effective
# harness (explicit --harness or replayed request.harness) is codex, refresh
# the .codex/ bundle from the (possibly newer) templates. Collision behavior
# mirrors the claude upgrade's --on-conflict: refuse (default) leaves a locally
# changed file, backup/theirs overwrite with a backup. A refusal WARNS, never
# fails the upgrade (consistent with the ADR-155 default). Runs BEFORE the
# state rewrite so codex ops are journaled.
# ----------------------------------------------------------------------
if [[ "$HARNESS" == "codex" ]]; then
  # PLAN-161 U1 writer-family audit: this refresh block ignored --dry-run
  # (codex_emit_bundle writes the .codex/ bundle). Preview + skip.
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "    (dry-run) would REFRESH: .codex/ harness bundle (--harness codex; on-conflict=$ON_CONFLICT)"
  elif ! command -v codex_emit_bundle >/dev/null 2>&1; then
    echo "    NOTE: recorded harness is codex but scripts/_codex_harness.sh is not" >&2
    echo "          sourced — skipping the .codex/ refresh (fail-open)." >&2
  else
    # shellcheck disable=SC2034  # PH_PROJECT_*/CODEX_FORCE consumed by the sourced _codex_harness.sh
    PH_PROJECT_PATH="$TARGET"
    # shellcheck disable=SC2034
    PH_PROJECT_NAME="$( basename "$TARGET" )"
    # shellcheck disable=SC2034
    if [[ "$ON_CONFLICT" == "theirs" || "$ON_CONFLICT" == "backup" ]]; then
      CODEX_FORCE=1
    else
      CODEX_FORCE=0
    fi
    echo ""
    echo "==> Codex harness refresh (--harness codex; on-conflict=$ON_CONFLICT)"
    if codex_emit_bundle; then :; else
      _cx_rc=$?
      echo "    NOTE: codex bundle refresh returned rc=$_cx_rc (likely a local edit under" >&2
      echo "          the default refuse policy). Re-run with --on-conflict backup to" >&2
      echo "          overwrite, or resolve by hand. The upgrade itself is unaffected." >&2
    fi
  fi
fi

# PLAN-156 Wave 4 — Grok harness refresh on upgrade. Mirrors the codex block:
# re-emits the grok operator surface from the (possibly newer) templates and
# RE-ARMS nothing silently (no live hooks). Runs on an explicit or replayed
# --harness grok. A refusal WARNS, never fails the upgrade.
if [[ "$HARNESS" == "grok" ]]; then
  # PLAN-161 U1 writer-family audit: this refresh block ignored --dry-run
  # (grok_emit_bundle writes the grok operator surface). Preview + skip.
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "    (dry-run) would REFRESH: grok harness operator surface (--harness grok; on-conflict=$ON_CONFLICT)"
  elif ! command -v grok_emit_bundle >/dev/null 2>&1; then
    echo "    NOTE: recorded harness is grok but scripts/_grok_harness.sh is not" >&2
    echo "          sourced — skipping the grok surface refresh (fail-open)." >&2
  else
    # shellcheck disable=SC2034  # PH_PROJECT_*/GROK_FORCE consumed by the sourced _grok_harness.sh
    PH_PROJECT_PATH="$TARGET"
    # shellcheck disable=SC2034
    PH_PROJECT_NAME="$( basename "$TARGET" )"
    # shellcheck disable=SC2034
    if [[ "$ON_CONFLICT" == "theirs" || "$ON_CONFLICT" == "backup" ]]; then
      GROK_FORCE=1
    else
      GROK_FORCE=0
    fi
    echo ""
    echo "==> Grok harness refresh (--harness grok; on-conflict=$ON_CONFLICT)"
    if grok_emit_bundle; then :; else
      _gk_rc=$?
      echo "    NOTE: grok surface refresh returned rc=$_gk_rc (likely a local edit under" >&2
      echo "          the default refuse policy). Re-run with --on-conflict backup, or" >&2
      echo "          resolve by hand. The upgrade itself is unaffected." >&2
    fi
  fi
fi

_write_upgrade_state

echo ""
echo "==> Upgrade complete."
echo "    Preserved: CLAUDE.md, MEMORY.md, .claude/agent-metrics.md (and existing"
echo "    .claude/settings.json keys — only NEW framework lifecycle hooks were"
echo "    additively registered into it (PLAN-135 W2 H8) and only the PLAN-163"
echo "    T5.4 baseline leaf keys were migrated — customized values PRESERVED"
echo "    with a named WARNING; see above)."
echo "    To roll back, restore from: $BAK_DIR"
echo "    (pre-merge settings.json backup: $BAK_DIR/.claude/settings.json.pre-h8-merge;"
echo "     pre-migration backup: $BAK_DIR/.claude/settings.json.pre-t54-migration)"
echo ""
echo "    NOTE: The settings-merge step (PLAN-135 W2) only ADDS missing framework"
echo "    lifecycle hooks idempotently; it never rewrites your custom keys. If you"
echo "    want a full rebuild from the latest template instead (e.g. settings.base.json"
echo "    or settings.stack.$STACK.json changed structurally upstream), back up and"
echo "    re-run install.sh manually:"
echo "      cp $TARGET/.claude/settings.json $TARGET/.claude/settings.json.bak"
echo "      rm $TARGET/.claude/settings.json"
echo "      $SCRIPT_DIR/install.sh $TARGET --profile $PROFILE --stack $STACK"
echo ""
echo "    NOTE (PLAN-161 L5 advisory): installs made before PLAN-161 seeded a"
echo "    deny-list baseline into .claude/settings.json that newer framework"
echo "    versions no longer ship. If present in YOUR permissions.deny and"
echo "    unwanted, delete these THREE EXACT rule strings BY HAND — the upgrade"
echo "    never rewrites your deny list (the settings-merge above is"
echo "    additive-only and stays so):"
echo "      \"Write(PROTOCOL.md)\""
echo "      \"Write(.claude/settings.json)\""
echo "      \"Write(SPEC/**)\""
