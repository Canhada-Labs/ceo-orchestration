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
# ## Fingerprint parity (PLAN-156-FOLLOWUP F5, debate C2 — unanimous)
#
# The recorder fingerprints the AGGREGATE canonical path set classified by
# `check_canonical_edit._is_canonical` (the fine, single-source-of-truth
# predicate). This gate previously hashed COARSE first-segment paths
# PER-COMMIT — two break axes (classifier + granularity) that made sidecar
# path (b) structurally unmatched. Now:
#
#   - Classification shells out to the single ORACLE:
#     `python3 check_canonical_edit.py --is-canonical -` (path\t0|1 lines).
#     Re-implementing the guard glob list in bash IS the drift class F5
#     fixes; the bash list below survives ONLY as the oracle-failure
#     fallback.
#   - Granularity: the WHOLE pushed range's changed paths are aggregated
#     ONCE (`git diff --name-only <remote>..<local>`, per-commit union on
#     new-branch pushes) into ONE fingerprint — matching the recorder's
#     aggregate working-tree set.
#   - Hash construction unchanged: sha256 over the LC_ALL=C sorted-unique,
#     newline-joined path set, no trailing newline (byte-identical to
#     `check_codex_stop_review.fingerprint`).
#   - Acceptance: sidecar APPROVE matching the aggregate fingerprint
#     clears the WHOLE range; otherwise EVERY canonical-touching commit
#     must carry an (a) trailer.
#
# ## RED-on-absence (debate A2)
#
# Canonical paths pushed AND neither full (a) trailer coverage nor a (b)
# matching APPROVE record => RED (exit 1, push blocked). Silence is NOT
# health: an empty/absent review-log with canonical commits to push is
# RED, not green.
#
# ## Residuals (named, per house vocabulary)
#
# - `git push --no-verify` bypasses every client-side hook. Backstops:
#   CODEOWNERS + branch protection + the CI review-record rider
#   (validate.yml) which re-checks the (a) trailer path server-side.
# - The (b) sidecar is machine-local; on a fresh clone only the (a) trailer
#   survives. CI therefore checks (a) only.
# - Coarse first-segment path classifier (mirror of
#   check_canonical_edit._CANONICAL_PREFIXES) is retained ONLY as the
#   oracle-failure fallback: it OVER-triggers review (fail-CLOSED — a
#   missed L3 touch is the danger, an extra review is not) and its
#   fingerprint will generally NOT match a recorder-written record, so
#   oracle failure degrades to trailer-only acceptance, never to a bypass.
#
# ## Controls
#
# - `CEO_GROK_PUSH_GATE=0`  -> disabled (no-op, exit 0).
# - `CEO_GROK_PUSH_GATE_ADVISORY=1` -> warn but do not block (exit 0).
# - `CEO_GROK_REVIEW_STATE_DIR` / `CEO_AUDIT_LOG_DIR` -> sidecar location
#   (matches check_codex_stop_review.py (or its grok equivalent) resolution).
# - `CEO_CANONICAL_ORACLE` -> path to check_canonical_edit.py (default:
#   `<repo-top>/.claude/hooks/check_canonical_edit.py`). Not a disarm
#   surface beyond what CEO_GROK_PUSH_GATE=0 already grants: pointing it
#   at garbage only triggers the fail-CLOSED coarse fallback.
#
# stdin (git pre-push protocol): `<local ref> <local sha> <remote ref> <remote sha>`
# argv: `<remote name> <remote url>` (unused here).
#
# Stdlib tools only (git, python3 for the oracle with a no-python fallback,
# sha256sum/shasum, sort, grep, awk). shellcheck -S warning clean.

set -euo pipefail

if [ "${CEO_GROK_PUSH_GATE:-1}" = "0" ]; then
  exit 0
fi

ADVISORY="${CEO_GROK_PUSH_GATE_ADVISORY:-0}"

_zero="0000000000000000000000000000000000000000"

_repo_top="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
_oracle="${CEO_CANONICAL_ORACLE:-${_repo_top}/.claude/hooks/check_canonical_edit.py}"
# Set to 1 by _classify_canonical when the fine oracle could not be used.
_ORACLE_DEGRADED=0

# COARSE first-segment prefixes. FALLBACK ONLY (F5/C2(d)): used when the
# oracle shell-out fails. It must OVER-trigger (e.g. every
# `.claude/plans/*.md`) = fail-CLOSED: with sidecar acceptance disabled while
# degraded, a failed oracle can only DEMAND MORE review (trailers), never wave
# a real L3 touch through.
#
# SUPERSET INVARIANT (pair-rail R2, S272 — the reason this list is not the
# original 4 prefixes): "over-triggers = fail-CLOSED" is only true if this set
# CONTAINS the fine oracle's first segments. The original list omitted
# `templates/`, `.grok/`, `.codex/`, `AGENTS.md` and `requirements.toml` —
# precisely the distribution, egress and kill-switch surfaces the fine
# predicate guards (settings.base.json lives under templates/). A degraded push
# touching ONLY those produced an EMPTY canonical set, and an empty set exits 0:
# an UNDER-trigger — the fail-OPEN direction — on the surfaces that matter most.
#
# Keep this a SUPERSET of the oracle's first segments. Adding a new top-level
# guarded surface to `_CANONICAL_GUARDS` means adding its first segment here.
_is_canonical_path() {
  # $1 = repo-relative path
  case "$1" in
    .claude/*|.github/*|scripts/*|SPEC/*|templates/*|.grok/*|.codex/*) return 0 ;;
    PROTOCOL.md|AGENTS.md|requirements.toml) return 0 ;;
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
    # New branch: commits reachable from local_sha that are NOT already on any
    # remote-tracking ref.
    #
    # `--not --all` (pair-rail R4, S272) was wrong and is now dangerous: `--all`
    # includes LOCAL refs — among them refs/heads/<the branch being pushed>,
    # which points at $local_sha itself. That subtracts the range from itself,
    # so the commit list came back EMPTY and, since the per-commit union (R3) is
    # now the ONLY source of classified paths, a first push of a branch carrying
    # canonical edits sailed through with an empty set. `--remotes` subtracts
    # only what the remote already has — the question the gate actually asks.
    git rev-list "$local_sha" --not --remotes 2>/dev/null || true
  else
    git rev-list "${remote_sha}..${local_sha}" 2>/dev/null || true
  fi
}

# All paths changed by one pushed ref range, one per line (unsorted, dups ok).
# Non-new-branch: ONE endpoint tree diff (net change — matches the
# recorder's working-tree aggregate semantics, and merge-safe).
# PER-COMMIT UNION, always (pair-rail R3, S272).
#
# The endpoint diff (`git diff remote..local`) reports the NET effect of the
# push. That is the wrong question: a range that edits a canonical file in one
# commit and REVERTS it in a later one has an empty net diff — the gate saw
# nothing, exited 0, and the unreviewed canonical edit still travelled to the
# remote inside the intermediate commit (from where a revert-of-the-revert or a
# cherry-pick resurrects it, forever unreviewed). What the gate must classify is
# every path any PUSHED COMMIT touches, so the union is taken over the range in
# both the existing-branch and new-branch cases.
#
# Consequence, intended: for an edit+revert range the gate's aggregate no longer
# equals the recorder's working-tree aggregate, so sidecar path (b) cannot match
# and the push must carry per-commit APPROVE trailers — the fail-CLOSED
# direction.
_changed_paths_in_range() {
  local local_sha="$1" remote_sha="$2" c
  if [ "$local_sha" = "$_zero" ]; then
    return 0
  fi
  for c in $(_commits_in_range "$local_sha" "$remote_sha"); do
    # --root: without it, diff-tree emits NOTHING for a ROOT commit (no parent
    # to diff against), so a first push whose root commit ADDS canonical files
    # classified an empty set and passed (pair-rail R5, S272).
    git diff-tree --root --no-commit-id --name-only -r "$c" 2>/dev/null || true
  done
}

# Classify the paths in file $1 (unique, one per line) -> canonical subset
# on stdout. Single source of truth: the check_canonical_edit.py oracle CLI
# (F5/C2(b)). On ANY oracle failure (missing python3/oracle file, nonzero
# exit, malformed or truncated output) -> fall back to the coarse
# classifier above = OVER-trigger = fail-CLOSED (F5/C2(d)).
_classify_canonical() {
  local in_file="$1" oracle_out expected got malformed p
  expected="$(grep -c . "$in_file" || true)"
  [ "$expected" = "0" ] && return 0
  if [ -f "$_oracle" ] && command -v python3 >/dev/null 2>&1; then
    if oracle_out="$(CLAUDE_PROJECT_DIR="$_repo_top" python3 "$_oracle" \
        --is-canonical - < "$in_file" 2>/dev/null)"; then
      got="$(printf '%s\n' "$oracle_out" | grep -c . || true)"
      malformed="$(printf '%s\n' "$oracle_out" | grep -cEv "	[01]\$" || true)"
      if [ "$got" = "$expected" ] && [ "$malformed" = "0" ]; then
        printf '%s\n' "$oracle_out" | awk -F'\t' '$2=="1" {print $1}'
        return 0
      fi
    fi
  fi
  # DEGRADED: the fine predicate is unavailable. Classification over-triggers
  # (fail-CLOSED), but the aggregate fingerprint computed from a COARSE set is
  # collision-prone — two different pushes touching the same top-level prefixes
  # hash identically, so one recorded APPROVE could clear an unrelated canonical
  # edit (review-reuse). Acceptance path (b) is therefore DISABLED while
  # degraded; only per-commit APPROVE trailers (path a) can clear the push.
  _ORACLE_DEGRADED=1
  echo "pre-push-review-gate: canonical-path ORACLE unavailable/failed;" \
    "falling back to COARSE classifier (over-triggers = fail-CLOSED) and" \
    "DISABLING sidecar acceptance (coarse fingerprints collide) — only" \
    "per-commit APPROVE trailers can clear this push." >&2
  while IFS= read -r p; do
    [ -n "$p" ] || continue
    if _is_canonical_path "$p"; then printf '%s\n' "$p"; fi
  done < "$in_file"
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

_all_changed_file="$(mktemp)"
_uniq_changed_file="$(mktemp)"
_canonical_file="$(mktemp)"
_commits_file="$(mktemp)"
trap 'rm -f "$_all_changed_file" "$_uniq_changed_file" "$_canonical_file" "$_commits_file"' EXIT

while read -r _local_ref _local_sha _remote_ref _remote_sha; do
  [ -n "${_local_sha:-}" ] || continue
  _changed_paths_in_range "$_local_sha" "$_remote_sha" >> "$_all_changed_file"
  _commits_in_range "$_local_sha" "$_remote_sha" >> "$_commits_file"
done

# Aggregate ONCE across everything being pushed (F5/C2(c)): one path set,
# one fingerprint — the recorder-side aggregate is one working-tree set.
LC_ALL=C sort -u "$_all_changed_file" | grep -v '^$' > "$_uniq_changed_file" || true

_classify_canonical "$_uniq_changed_file" > "$_canonical_file"

if ! [ -s "$_canonical_file" ]; then
  exit 0  # no canonical paths in the push — nothing to gate
fi

# Fingerprint: sha256 over LC_ALL=C sorted-unique newline-joined set, NO
# trailing newline — byte-identical to check_codex_stop_review.fingerprint
# ("\n".join(sorted(set(paths)))). The $(...) substitution strips the
# trailing newline; LC_ALL=C sort orders by byte = Python codepoint order.
_fp="$(printf '%s' "$(LC_ALL=C sort -u "$_canonical_file")" | _sha256)"

# Acceptance path (b): sidecar APPROVE record matching the AGGREGATE
# fingerprint clears the whole range — but ONLY when the fingerprint was built
# from the FINE oracle set. Under a degraded (coarse) classification the
# fingerprint is collision-prone, so path (b) is closed and the push must carry
# per-commit APPROVE trailers (pair-rail R1 P1, S272).
if [ "$_ORACLE_DEGRADED" = "0" ] && _sidecar_has_approve "$_fp"; then
  exit 0
fi

# Acceptance path (a): every canonical-touching commit carries an APPROVE
# trailer.
_unreviewed_commits=""
_fail_count=0
while IFS= read -r _c; do
  [ -n "$_c" ] || continue
  # --root: a root commit has no parent; without it diff-tree emits nothing and
  # the commit reads as "touches no canonical path" (pair-rail R5, S272).
  _ctouch="$(git diff-tree --root --no-commit-id --name-only -r "$_c" 2>/dev/null \
    | grep -Fx -f "$_canonical_file" || true)"
  [ -n "$_ctouch" ] || continue
  if _commit_has_approve_trailer "$_c"; then
    continue
  fi
  _fail_count=$((_fail_count + 1))
  _unreviewed_commits="${_unreviewed_commits}    - ${_c}
"
done < "$_commits_file"

if [ "$_fail_count" -gt 0 ]; then
  {
    echo "PRE-PUSH REVIEW GATE (inverted pair-rail) -- RED"
    echo "  pushed range touches L3/canonical paths with NO cross-model review record:"
    sed 's/^/    - /' "$_canonical_file"
    echo "  aggregate path-set fingerprint: ${_fp}"
    echo "  canonical-touching commit(s) without an APPROVE trailer:"
    printf '%s' "$_unreviewed_commits"
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
