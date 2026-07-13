#!/usr/bin/env bash
# pre-push-review-gate.sh -- inverted pair-rail push backstop (PLAN-156 Wave 5, grok).
#
# THIRD install surface: the installer copies this to
# `.git/hooks/pre-push-grok-review` on a `--harness grok` target (the
# operator wires it as pre-push). Grok's Stop event is NON-blocking, so
# unlike codex this push gate is not merely the abandoned-Stop backstop —
# it is the PRIMARY enforcement point for cross-model review under grok. No manifest walk
# reaches `.git/` naturally, so Wave 5's lifecycle-symmetry criteria must
# list it explicitly (manifest + uninstall + backup + restore).
#
# ## What it enforces
#
# The teeth for the PARTIAL inverted pair-rail when the Stop gate was
# abandoned (session killed / refused twice). Push is BLOCKED when commits
# being pushed touch L3/canonical paths without a recorded cross-model
# review. A review record is EITHER:
#
#   (a) a `Pair-Rail-Reviewed: APPROVE` trailer in each canonical-touching
#       commit message (git-native; survives a fresh clone -- the ONLY path
#       that works in CI / on another machine), OR
#   (b) an APPROVE record in the local review-log sidecar written by
#       `check_codex_stop_review.py (or its grok equivalent) --record`, matched by the path-set
#       fingerprint (machine-local; absent on a fresh clone -- see residual).
#
# ## RED-on-absence (debate A2)
#
# Canonical commits present AND neither an (a) trailer nor a (b) matching
# APPROVE record => RED (exit 1, push blocked). Silence is NOT health: an
# empty/absent review-log with canonical commits to push is RED, not green.
#
# ## Residuals (named, per house vocabulary)
#
# - `git push --no-verify` bypasses every client-side hook. Backstops:
#   CODEOWNERS + branch protection + the CI review-record rider
#   (validate.yml) which re-checks the (a) trailer path server-side.
# - The (b) sidecar is machine-local; on a fresh clone only the (a) trailer
#   survives. CI therefore checks (a) only.
# - Coarse first-segment path classifier (mirror of
#   check_canonical_edit._CANONICAL_PREFIXES): it OVER-triggers review
#   (safe direction; a missed L3 touch is the danger, an extra review is
#   not).
#
# ## Controls
#
# - `CEO_GROK_PUSH_GATE=0`  -> disabled (no-op, exit 0).
# - `CEO_GROK_PUSH_GATE_ADVISORY=1` -> warn but do not block (exit 0).
# - `CEO_GROK_REVIEW_STATE_DIR` / `CEO_AUDIT_LOG_DIR` -> sidecar location
#   (matches check_codex_stop_review.py (or its grok equivalent) resolution).
#
# stdin (git pre-push protocol): `<local ref> <local sha> <remote ref> <remote sha>`
# argv: `<remote name> <remote url>` (unused here).
#
# Stdlib tools only (git, sha256sum/shasum, sort, grep). shellcheck -S warning clean.

set -euo pipefail

if [ "${CEO_GROK_PUSH_GATE:-1}" = "0" ]; then
  exit 0
fi

ADVISORY="${CEO_GROK_PUSH_GATE_ADVISORY:-0}"

_zero="0000000000000000000000000000000000000000"

# Canonical first-segment prefixes (mirror of
# check_canonical_edit._CANONICAL_PREFIXES; PROTOCOL.md is a file, matched
# exactly).
_is_canonical_path() {
  # $1 = repo-relative path
  case "$1" in
    .claude/*|.github/*|scripts/*|SPEC/*) return 0 ;;
    PROTOCOL.md) return 0 ;;
    *) return 1 ;;
  esac
}

_sha256() {
  # Read stdin, emit hex digest (portable: sha256sum or shasum -a 256).
  if command -v sha256sum >/dev/null 2>&1; then
    sha256sum | awk '{print $1}'
  else
    shasum -a 256 | awk '{print $1}'
  fi
}

_state_dir() {
  if [ -n "${CEO_GROK_REVIEW_STATE_DIR:-}" ]; then
    printf '%s' "${CEO_GROK_REVIEW_STATE_DIR}"
  elif [ -n "${CEO_AUDIT_LOG_DIR:-}" ]; then
    printf '%s' "${CEO_AUDIT_LOG_DIR}"
  else
    printf '%s' "${HOME:-/tmp}/.claude/projects/ceo-orchestration/state"
  fi
}

_review_log() {
  printf '%s/grok-review-log.jsonl' "$(_state_dir)"
}

# Collect commits to check for one pushed ref range.
# Args: <local_sha> <remote_sha>
_commits_in_range() {
  local local_sha="$1" remote_sha="$2"
  if [ "$local_sha" = "$_zero" ]; then
    return 0  # branch deletion — nothing to push
  fi
  if [ "$remote_sha" = "$_zero" ]; then
    # New branch: commits reachable from local_sha but not from any other ref.
    git rev-list "$local_sha" --not --all 2>/dev/null || true
  else
    git rev-list "${remote_sha}..${local_sha}" 2>/dev/null || true
  fi
}

# Canonical paths changed by one commit.
_canonical_paths_in_commit() {
  local sha="$1" p
  git diff-tree --no-commit-id --name-only -r "$sha" 2>/dev/null | while IFS= read -r p; do
    [ -n "$p" ] || continue
    if _is_canonical_path "$p"; then
      printf '%s\n' "$p"
    fi
  done
}

# Does this commit carry an APPROVE pair-rail trailer? (acceptance path a)
_commit_has_approve_trailer() {
  local sha="$1"
  git log -1 --format='%B' "$sha" 2>/dev/null \
    | grep -Eiq '^Pair-Rail-Reviewed:[[:space:]]*APPROVE' && return 0
  return 1
}

# Does the sidecar review-log carry an APPROVE record matching this
# fingerprint? (acceptance path b)
_sidecar_has_approve() {
  local fp="$1" log
  log="$(_review_log)"
  [ -f "$log" ] || return 1
  # Match a JSON object line that is APPROVE AND carries this fingerprint.
  grep -F "\"fingerprint\": \"${fp}\"" "$log" 2>/dev/null \
    | grep -Eq '"verdict": ?"APPROVE"' && return 0
  # Tolerate compact JSON (no spaces).
  grep -F "\"fingerprint\":\"${fp}\"" "$log" 2>/dev/null \
    | grep -Eq '"verdict":"APPROVE"' && return 0
  return 1
}

_fail_count=0
_all_canonical_paths_file="$(mktemp)"
trap 'rm -f "$_all_canonical_paths_file"' EXIT

while read -r _local_ref _local_sha _remote_ref _remote_sha; do
  [ -n "${_local_sha:-}" ] || continue
  for _c in $(_commits_in_range "$_local_sha" "$_remote_sha"); do
    _cpaths="$(_canonical_paths_in_commit "$_c")"
    [ -n "$_cpaths" ] || continue
    printf '%s\n' "$_cpaths" >> "$_all_canonical_paths_file"

    # Acceptance path (a): commit-local APPROVE trailer.
    if _commit_has_approve_trailer "$_c"; then
      continue
    fi
    # Acceptance path (b): sidecar APPROVE record matching this commit's
    # canonical path-set fingerprint.
    _fp="$(printf '%s' "$(printf '%s\n' "$_cpaths" | sort -u)" | _sha256)"
    if _sidecar_has_approve "$_fp"; then
      continue
    fi

    _fail_count=$((_fail_count + 1))
    {
      echo "PRE-PUSH REVIEW GATE (inverted pair-rail) -- RED"
      echo "  commit ${_c} touches L3/canonical paths with NO cross-model review record:"
      printf '%s\n' "$_cpaths" | sed 's/^/    - /'
      echo "  path-set fingerprint: ${_fp}"
    } >&2
  done
done

# RED-on-absence sweep: canonical paths pushed but the sidecar is empty/absent
# AND no trailers cleared them (already counted above). If we saw canonical
# paths at all and every one failed, that is the abandoned-Stop-gate case.
if [ -s "$_all_canonical_paths_file" ] && [ "$_fail_count" -gt 0 ]; then
  {
    echo ""
    echo "To clear this gate, EITHER:"
    echo "  (a) add a 'Pair-Rail-Reviewed: APPROVE' trailer to the commit(s)"
    echo "      AFTER a real claude -p cross-model review, OR"
    echo "  (b) run the review at Stop time so check_codex_stop_review.py (or its grok equivalent)"
    echo "      --record writes an APPROVE record for the path set."
    echo ""
    echo "Residual: 'git push --no-verify' bypasses this client-side hook;"
    echo "CODEOWNERS + branch protection + the validate.yml review rider are"
    echo "the server-side backstops. This gate is a BACKSTOP, not the sole line."
  } >&2
  if [ "$ADVISORY" = "1" ]; then
    echo "pre-push-review-gate: ADVISORY mode -- ${_fail_count} unreviewed canonical commit(s); NOT blocking." >&2
    exit 0
  fi
  exit 1
fi

exit 0
