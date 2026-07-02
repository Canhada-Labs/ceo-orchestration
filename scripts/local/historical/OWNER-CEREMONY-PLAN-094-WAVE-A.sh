#!/usr/bin/env bash
# OWNER-CEREMONY-PLAN-094-WAVE-A.sh — S124 single-script Wave A ceremony
#
# Single Owner-runs script that lands PLAN-094 Wave A in one external
# terminal session.
#
# Idempotent state machine (6 states):
#   A_fresh        no sentinel.asc, no expected commit          → full path
#   B_signed       sentinel.asc verifies; no edits yet          → skip Step A
#   B_partial      sentinel signed; spool_writer.py present BUT
#                  audit_emit.py registration incomplete        → rerun patcher
#   C_applied      sentinel + ALL ceremony outputs present; no
#                  commit yet                                   → skip A+B+C
#   D_committed    PLAN-094 Wave A commit on local HEAD          → push-only / skip
#   E_pushed       commit already at origin/main                → no-op
#
# Codex R2 pre-reviewed (S120 doctrine
# `feedback_codex_r2_review_own_ceremony_scripts.md`). All P0+P1
# findings folded inline.
#
# WHY KERNEL BYPASS: ceremony Python writes files via Path.write_text()
# which does NOT trigger claude-code Edit/Write hooks. The Owner-signed
# `approved.md.asc` is the tamper-evident audit trail. No
# CEO_KERNEL_OVERRIDE env needed.
#
# Usage:
#   cd /Users/devuser/ceo-orchestration
#   bash scripts/local/OWNER-CEREMONY-PLAN-094-WAVE-A.sh
#
# Owner is prompted ONCE by gpg pinentry to unlock key 00000000.

set -euo pipefail

# ============================================================================
# Configuration
# ============================================================================

REPO="/Users/devuser/ceo-orchestration"
PLAN_DIR="${REPO}/.claude/plans/PLAN-094"
SENTINEL_MD="${PLAN_DIR}/architect/round-2/approved.md"
SENTINEL_ASC="${PLAN_DIR}/architect/round-2/approved.md.asc"
DRAFT="${PLAN_DIR}/spool_writer_DRAFT.py"
CODEX_MARKER="${PLAN_DIR}/codex-r2-accept.md"
CEREMONY_PY="${REPO}/scripts/local/plan-094-apply-wave-a-c-e.py"
# P1-5 fix (iter-2): pinned full fingerprint constant. The runtime
# helper `verify_owner_fpr_in_keyring()` cross-checks that this exact
# fpr is in the keyring as a secret key — defense-in-depth against
# keyring contamination.
OWNER_GPG_FPR="0000000000000000000000000000000000000000"

# Commit subject prefix used to detect state D / state E
EXPECTED_COMMIT_PREFIX="feat(plan-094,wave-a): spool_writer.py"

# Files this script touches (whitelist for clean-tree check)
declare -a CEREMONY_PATHS=(
    "${SENTINEL_ASC#"${REPO}"/}"
    ".claude/hooks/_lib/spool_writer.py"
    ".claude/hooks/_lib/audit_emit.py"
    ".claude/hooks/tests/test_audit_emit_async_flush.py"
)
# This script + the python patcher are themselves untracked initially
# (delivered by S124 commit 917ffa0 + later); they're benign for the
# clean-tree check. P1-2 fix.
declare -a SELF_PATHS=(
    "scripts/local/OWNER-CEREMONY-PLAN-094-WAVE-A.sh"
)

# ============================================================================
# Utilities
# ============================================================================

color_red()    { printf '\033[31m%s\033[0m\n' "$*"; }
color_green()  { printf '\033[32m%s\033[0m\n' "$*"; }
color_yellow() { printf '\033[33m%s\033[0m\n' "$*"; }
color_bold()   { printf '\033[1m%s\033[0m\n' "$*"; }

step_banner() {
    echo
    color_bold "=================================================================="
    color_bold "  $*"
    color_bold "=================================================================="
}

die() {
    color_red "FATAL: $*"
    exit 2
}

confirm() {
    local prompt="$1"
    local ans=""
    read -r -p "$(color_yellow "${prompt} [y/N] ")" ans
    [[ "${ans}" == "y" || "${ans}" == "Y" ]]
}

# P0-2 fix: GPG verify via --status-fd capturing into variable. NO
# pipelines. Requires VALIDSIG with the exact full fingerprint.
gpg_verify_strict() {
    local sig_file="$1"
    local data_file="$2"
    local expected_fpr="$3"

    local status_output=""
    # --status-fd 1 sends machine-parseable status to stdout; we capture.
    # 2>/dev/null suppresses the human-readable "Good signature" English.
    if ! status_output="$(gpg --status-fd 1 --verify "${sig_file}" "${data_file}" 2>/dev/null)"; then
        return 1
    fi

    # P1-1 fix (iter-2): NO pipelines (avoid SIGPIPE/pipefail).
    # Look for an exact VALIDSIG line. Format:
    #   [GNUPG:] VALIDSIG <fpr> <date> <ts> <expire-ts> <ver> ...
    if grep -qE "^\[GNUPG:\] VALIDSIG ${expected_fpr} " <<< "${status_output}"; then
        return 0
    fi
    return 1
}

# Resolve full fingerprint from short id. P0-2 fix: store fpr globally
# so all later checks use the same value.
verify_owner_fpr_in_keyring() {
    # P1-5 fix (iter-2): cross-check that the pinned OWNER_GPG_FPR
    # corresponds to a secret key in the keyring. Refuses to proceed
    # if the keyring has been tampered/replaced.
    local listing
    if ! listing="$(gpg --list-secret-keys --with-colons "${OWNER_GPG_FPR}" 2>/dev/null)"; then
        die "GPG secret key fpr=${OWNER_GPG_FPR} not in keyring"
    fi
    if ! grep -qE "^fpr:::::::::${OWNER_GPG_FPR}:" <<< "${listing}"; then
        die "GPG keyring lookup did not return expected fpr=${OWNER_GPG_FPR}"
    fi
    echo "  GPG fpr verified in keyring: ${OWNER_GPG_FPR}"
}

# ============================================================================
# State detection — A_fresh / B_signed / C_applied / D_committed / E_pushed
# ============================================================================

detect_state() {
    local state="A_fresh"

    # P1-2 fix (iter-2): explicit refspec so origin/main ref is refreshed.
    # P1-3 fix (iter-2): D/E detection also requires sentinel.asc to verify
    # AND the commit to be signed by OWNER_GPG_FPR. Otherwise a spoofed
    # commit subject would short-circuit to push-only.
    if git log -1 --format='%s' 2>/dev/null | grep -qF "${EXPECTED_COMMIT_PREFIX}"; then
        local head_sig_fpr
        head_sig_fpr="$(git log -1 --format='%GP' 2>/dev/null || echo '')"
        if [[ "${head_sig_fpr}" != "${OWNER_GPG_FPR}" ]]; then
            die "HEAD commit subject matches ceremony but signature fpr='${head_sig_fpr}' != expected '${OWNER_GPG_FPR}'"
        fi
        # Sentinel asc must also verify (defense-in-depth — caller may
        # have tampered with the .asc after the commit)
        if [[ ! -f "${SENTINEL_ASC}" ]] \
           || ! gpg_verify_strict "${SENTINEL_ASC}" "${SENTINEL_MD}" "${OWNER_GPG_FPR}"; then
            die "HEAD ceremony commit present but sentinel.asc missing/invalid"
        fi
        local local_head remote_head=""
        local_head="$(git rev-parse HEAD)"
        if git fetch --quiet origin main:refs/remotes/origin/main 2>/dev/null; then
            remote_head="$(git rev-parse origin/main 2>/dev/null || echo "")"
        fi
        if [[ -n "${remote_head}" && "${local_head}" == "${remote_head}" ]]; then
            state="E_pushed"
        else
            state="D_committed"
        fi
        printf '%s' "${state}"
        return 0
    fi

    # P0-1 fix (iter-2): C_applied detection MUST require a valid
    # signed sentinel — otherwise an attacker can apply edits, delete
    # the .asc, rerun script, and the wrapper commits unsigned content.
    #
    # P1 fix (iter-3): C_applied requires ALL ceremony outputs (full
    # apply), not just `spool_writer.py`. If spool_writer landed but
    # audit_emit didn't get the 8 _KNOWN_ACTIONS, that's a partial
    # apply — stay in B_signed so the (idempotent) patcher reruns and
    # finishes the missing edits, instead of stranding the working
    # tree by skipping Step C.
    if [[ -f "${REPO}/.claude/hooks/_lib/spool_writer.py" ]] \
       && grep -q "PLAN-094 Wave A — spool_writer" "${REPO}/.claude/hooks/_lib/spool_writer.py" 2>/dev/null; then
        if [[ ! -f "${SENTINEL_ASC}" ]] \
           || ! gpg_verify_strict "${SENTINEL_ASC}" "${SENTINEL_MD}" "${OWNER_GPG_FPR}"; then
            die "ceremony edits applied on disk but sentinel.asc missing/invalid — refuse to commit without verified Owner authorization"
        fi
        # Check all 8 _KNOWN_ACTIONS are present in audit_emit.py
        local audit_emit_py="${REPO}/.claude/hooks/_lib/audit_emit.py"
        local need_actions=(
            "audit_flush_dropped_count"
            "audit_spool_stale_recovered"
            "audit_spool_partial_line_discarded"
            "audit_spool_tamper_detected"
            "audit_spool_duplicate_tuple_rejected"
            "audit_spool_intentionally_deleted"
            "audit_spool_unexpected_skip"
            "skill_cache_stats"
        )
        local missing_actions=""
        for action in "${need_actions[@]}"; do
            if ! grep -q "\"${action}\"" "${audit_emit_py}" 2>/dev/null; then
                missing_actions="${missing_actions}${action} "
            fi
        done
        if [[ -n "${missing_actions}" ]]; then
            # P1 fix (iter-4): NEW B_partial state. The patcher reruns
            # (idempotent on the spool_writer.py promote via marker check;
            # the audit_emit step2 anchor is also idempotent — replaces
            # the closing `}` block only when marker absent). Clean-tree
            # check uses B_partial whitelist which allows the already-
            # written ceremony output paths.
            color_yellow "  partial-apply detected: audit_emit missing actions: ${missing_actions}"
            color_yellow "  state=B_partial; patcher will rerun to finish registration"
            state="B_partial"
            printf '%s' "${state}"
            return 0
        fi
        state="C_applied"
        printf '%s' "${state}"
        return 0
    fi

    # B_signed: sentinel asc exists + verifies
    if [[ -f "${SENTINEL_ASC}" ]]; then
        if gpg_verify_strict "${SENTINEL_ASC}" "${SENTINEL_MD}" "${OWNER_GPG_FPR}"; then
            state="B_signed"
        else
            die "sentinel.asc exists but signature does not verify against fpr=${OWNER_GPG_FPR}"
        fi
    fi

    printf '%s' "${state}"
}

# ============================================================================
# Clean-tree check (allows known ceremony paths + self)
# ============================================================================

# P0-2 fix (iter-2): state-specific clean-tree whitelist. Each state
# permits ONLY the paths that should plausibly be dirty at that state;
# everything else aborts. Prevents unrelated edits to ceremony output
# files from being silently swept into the Owner commit.
#
# Allowed dirty paths per state:
#   A_fresh    → only SELF_PATHS (the ceremony scripts themselves;
#                self-script may be untracked from prior commit `917ffa0`)
#   B_signed   → SELF_PATHS + sentinel.asc
#   C_applied  → SELF_PATHS + sentinel.asc + the 4 ceremony output paths
#   D / E      → no dirty paths permitted (commit already exists; no
#                in-flight edits)
check_tree_clean_for_state() {
    local state="$1"
    local porcelain
    porcelain="$(git status --porcelain)"
    if [[ -z "${porcelain}" ]]; then
        return 0
    fi

    declare -a allowed=()
    case "${state}" in
        A_fresh)
            allowed=("${SELF_PATHS[@]}")
            ;;
        B_signed)
            allowed=("${SELF_PATHS[@]}" "${SENTINEL_ASC#"${REPO}"/}")
            ;;
        B_partial)
            # Partial apply — sentinel signed + spool_writer.py landed,
            # but audit_emit registration incomplete. Allow same set as
            # C_applied (the patcher rerun will finish the work).
            allowed=("${SELF_PATHS[@]}" "${CEREMONY_PATHS[@]}")
            ;;
        C_applied)
            allowed=("${SELF_PATHS[@]}" "${CEREMONY_PATHS[@]}")
            ;;
        D_committed|E_pushed)
            # No untracked/modified entries permitted after the commit
            allowed=()
            ;;
        *)
            die "unknown state in clean-tree check: ${state}"
            ;;
    esac

    local bad_lines=""
    while IFS= read -r line; do
        [[ -z "${line}" ]] && continue
        # `git status --porcelain` format: "XY path"
        local path="${line:3}"
        local ok=0
        for a in "${allowed[@]}"; do
            if [[ "${path}" == "${a}" || "${path}" == "${a} "* ]]; then
                ok=1
                break
            fi
        done
        if [[ ${ok} -eq 0 ]]; then
            bad_lines="${bad_lines}${line}"$'\n'
        fi
    done <<< "${porcelain}"

    if [[ -n "${bad_lines}" ]]; then
        color_red "state=${state}: git tree has unexpected dirty entries:"
        printf '%s' "${bad_lines}"
        die "commit or stash first (these paths are not in the state-${state} whitelist)"
    fi
    return 0
}

# ============================================================================
# Preflight
# ============================================================================

step_banner "Pre-flight"

[[ -d "${REPO}" ]] || die "repo dir not found: ${REPO}"
cd "${REPO}"

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
echo "  branch: ${BRANCH}"
[[ "${BRANCH}" == "main" ]] || die "ceremony expects 'main' (got '${BRANCH}')"

command -v gpg >/dev/null 2>&1 || die "gpg not on PATH"
command -v python3 >/dev/null 2>&1 || die "python3 not on PATH"

# P2 fix: ensure pinentry can find the controlling tty (macOS robustness)
GPG_TTY="$(tty 2>/dev/null || echo /dev/tty)"
export GPG_TTY

verify_owner_fpr_in_keyring

# Required artifacts present
for f in "${SENTINEL_MD}" "${DRAFT}" "${CODEX_MARKER}" "${CEREMONY_PY}"; do
    [[ -f "${f}" ]] || die "missing required file: ${f}"
done
echo "  artifacts: present"

# P1-4 + P2-2 fix: AST-parse (no .pyc cache side-effects) BOTH draft
# and ceremony patcher. py_compile would create __pycache__ that may
# trip the clean-tree check downstream.
python3 -c "
import ast, sys
for p in ['${DRAFT}', '${CEREMONY_PY}']:
    try:
        with open(p, 'r', encoding='utf-8') as f:
            ast.parse(f.read())
        print(f'  ast-parse OK: {p.rsplit(\"/\", 1)[-1]}')
    except SyntaxError as e:
        print(f'  ast-parse FAILED: {p}: {e}', file=sys.stderr)
        sys.exit(1)
" || die "ast.parse failed on draft or ceremony patcher"

grep -q "final_verdict: ACCEPT" "${CODEX_MARKER}" \
    || die "Codex marker missing 'final_verdict: ACCEPT'"
echo "  Codex R2 ACCEPT marker: verified"

grep -q "^Scope:" "${SENTINEL_MD}" || die "sentinel missing 'Scope:' block"
grep -q "END SIGNED SCOPE" "${SENTINEL_MD}" || die "sentinel missing END-SIGNED-SCOPE"
echo "  sentinel scope block: parseable"

color_green "[preflight] passed"

# ============================================================================
# State detection + dispatch
# ============================================================================

step_banner "State detection"

STATE="$(detect_state)"
color_bold "  detected state: ${STATE}"

case "${STATE}" in
    E_pushed|D_committed|C_applied|B_partial|B_signed|A_fresh)
        : ;;  # valid; clean-tree check below enforces per-state invariant
    *)
        die "unknown state: ${STATE}"
        ;;
esac

# P2-1 fix (iter-3): clean-tree check runs FIRST for ALL states (incl.
# D_committed/E_pushed) so the no-dirty-paths invariant is actually
# enforced post-commit. Then dispatch.
check_tree_clean_for_state "${STATE}"
echo "  git tree: clean (state-${STATE} whitelist)"

case "${STATE}" in
    E_pushed)
        color_green "  PLAN-094 Wave A already on origin/main — nothing to do."
        exit 0
        ;;
    D_committed)
        color_yellow "  PLAN-094 Wave A commit exists locally but is unpushed."
        echo "    HEAD: $(git log -1 --format='%h %s')"
        if confirm "Push to origin/main now?"; then
            git push origin main || die "push failed"
            color_green "  pushed."
            exit 0
        else
            color_yellow "  skipping push; rerun this script when ready."
            exit 0
        fi
        ;;
    C_applied)
        color_yellow "  ceremony edits on disk; commit pending."
        ;;
    B_partial)
        color_yellow "  partial-apply detected; patcher will rerun."
        ;;
    B_signed)
        color_yellow "  sentinel signed; ceremony edits pending."
        ;;
    A_fresh)
        color_yellow "  fresh state."
        ;;
esac

# ============================================================================
# Step A — GPG sign sentinel (only in state A_fresh)
# ============================================================================

if [[ "${STATE}" == "A_fresh" ]]; then
    step_banner "Step A — GPG sign sentinel"

    echo "  signing ${SENTINEL_MD#"${REPO}"/} with key ${OWNER_GPG_FPR}"
    echo "  (pinentry will prompt for passphrase)"

    # No --batch (would disable pinentry per S120 lesson)
    gpg --yes --armor --detach-sign \
        --local-user "${OWNER_GPG_FPR}" \
        --output "${SENTINEL_ASC}" \
        "${SENTINEL_MD}" \
        || die "GPG sign failed"

    # P0-2 fix: re-verify via strict fpr check
    if ! gpg_verify_strict "${SENTINEL_ASC}" "${SENTINEL_MD}" "${OWNER_GPG_FPR}"; then
        die "post-sign verify FAILED for fpr=${OWNER_GPG_FPR}"
    fi
    color_green "  sentinel signed + verified"

    # Advance state
    STATE="B_signed"
fi

# ============================================================================
# Step B — Python ceremony patcher (only in state B_signed)
# ============================================================================

if [[ "${STATE}" == "B_signed" || "${STATE}" == "B_partial" ]]; then
    step_banner "Step B — Ceremony patcher (dry-run preview)"
    if [[ "${STATE}" == "B_partial" ]]; then
        color_yellow "  (rerun after partial apply — patcher steps that already landed will report 'skipped')"
    fi

    # P0-1 fix: pass --skip-preflight because the wrapper has already
    # done the equivalent checks. The python preflight would otherwise
    # reject the freshly-signed .asc as a dirty-tree entry.
    python3 "${CEREMONY_PY}" --dry-run --skip-preflight \
        || die "ceremony dry-run failed"

    echo
    confirm "Apply ceremony edits for real?" || die "Owner aborted at dry-run review"

    step_banner "Step C — Apply ceremony edits"

    python3 "${CEREMONY_PY}" --skip-preflight \
        || die "ceremony apply FAILED — inspect output above"
    color_green "  ceremony python complete"

    STATE="C_applied"
fi

# ============================================================================
# Step D — Sanity checks on what was just landed
# ============================================================================

step_banner "Step D — Sanity tests"

# Spool writer module imports + API parity
PYTHONPATH="${REPO}/.claude/hooks" python3 - <<'PYEOF' \
    || die "spool_writer import/API check FAILED"
from _lib import spool_writer
required = {
    'spool_append', 'drain_now', 'should_drain',
    'install_exit_handlers', 'reconcile_journal_at_session_start',
    'set_forensic_emitter', 'is_sync_mode',
}
public = {n for n in dir(spool_writer) if not n.startswith('_') and callable(getattr(spool_writer, n))}
missing = required - public
assert not missing, f'spool_writer missing API: {missing}'
print(f'  spool_writer public API: OK ({len(public)} callables, all required present)')
PYEOF

# audit_emit knows the 8 new actions
PYTHONPATH="${REPO}/.claude/hooks" python3 - <<'PYEOF' \
    || die "audit_emit _KNOWN_ACTIONS check FAILED"
from _lib import audit_emit
need = {
    'audit_flush_dropped_count','audit_spool_stale_recovered',
    'audit_spool_partial_line_discarded','audit_spool_tamper_detected',
    'audit_spool_duplicate_tuple_rejected','audit_spool_intentionally_deleted',
    'audit_spool_unexpected_skip','skill_cache_stats',
}
missing = need - audit_emit._KNOWN_ACTIONS
assert not missing, f'audit_emit._KNOWN_ACTIONS missing: {missing}'
print(f'  audit_emit._KNOWN_ACTIONS: contains all 8 new entries')
PYEOF

# Hook test regression suite (best-effort — won't auto-abort, just warn)
echo "  running hook test suite (advisory; review output for regressions)"
if command -v pytest >/dev/null 2>&1; then
    pytest -q "${REPO}/.claude/hooks/tests/" --timeout=30 2>&1 | tail -25 \
        || color_yellow "  pytest had failures — review before commit"
else
    # P2-1 fix (iter-2): under set -e, pipefail the unittest invocation
    # was previously aborting. Wrap in `|| color_yellow ...` like pytest
    # branch — tests are advisory at this point in the ceremony.
    ( cd "${REPO}/.claude/hooks/tests" && python3 -m unittest discover -p 'test_*.py' 2>&1 | tail -10 ) \
        || color_yellow "  unittest had failures — review before commit"
fi

color_green "[sanity] complete"

# ============================================================================
# Step E — Stage + commit (only in state C_applied)
# ============================================================================

if [[ "${STATE}" == "C_applied" ]]; then
    step_banner "Step E — Stage + commit"

    # P1-5 fix: mandatory files use plain `git add` (hard-fail on absence);
    # optional test skeleton (may pre-exist via earlier rerun) checked with -f.
    git add -- \
        "${SENTINEL_ASC}" \
        ".claude/hooks/_lib/spool_writer.py" \
        ".claude/hooks/_lib/audit_emit.py" \
        || die "git add mandatory paths failed"

    # Optional test file — only stage if present
    TEST_FILE=".claude/hooks/tests/test_audit_emit_async_flush.py"
    if [[ -f "${REPO}/${TEST_FILE}" ]]; then
        git add -- "${TEST_FILE}" || die "git add test file failed"
    fi

    # Verify there's something to commit
    if git diff --cached --quiet; then
        die "nothing staged — ceremony python may not have applied edits"
    fi

    echo
    git status --short
    # P2-2 fix (iter-3): re-verify sentinel signature immediately before
    # commit (close last same-run tamper window). The earlier detect_state
    # already verified; this is defense-in-depth against a tampering
    # actor that races between detect_state and commit.
    if ! gpg_verify_strict "${SENTINEL_ASC}" "${SENTINEL_MD}" "${OWNER_GPG_FPR}"; then
        die "pre-commit sentinel re-verify FAILED — refuse to commit"
    fi
    echo "  pre-commit sentinel re-verify: OK"

    echo
    confirm "Create signed commit (GPG key ${OWNER_GPG_FPR})?" \
        || die "Owner aborted before commit"

    # P1-3 fix: explicit signing key (don't trust user.signingkey config)
    git -c "user.signingkey=${OWNER_GPG_FPR}" commit -S \
        --gpg-sign="${OWNER_GPG_FPR}" \
        -m "feat(plan-094,wave-a): spool_writer.py + 8 _KNOWN_ACTIONS + Wave-A test skeleton (S124)

Codex R2 ACCEPT iter-7 (gpt-5.5 thread 019e2889) — convergence
14 -> 10 -> 5 -> 4 -> 1 -> 1 -> ACCEPT. Draft 2098 LoC; 7 smoke tests
PASS (baseline / idempotent re-drain / K_MAX 150 / unterminated-tail
isolation / stale TTL / ordinal recovery / quarantine no-deadlock).

ADR-055-AMEND-1 invariant compliance: 5-phase atomic drain; 4-tuple
total order (wall_ns, pid, spool_uuid, ordinal_within_file); K_MAX=100 /
K_TAIL_WINDOW=200 with processed-not-appended cap; shared
_validate_spool_header_strict between writer + drainer; canonical-tail
prev_hmac reconstruction; CEO_AUDIT_SYNC_MODE=1 kill-switch; 7 forensic
events registered; per-PID spool + journal flocks; asymmetric lock
order deadlock-free; stdlib-only Python 3.9+.

Audit surface: 8 new _KNOWN_ACTIONS in _lib/audit_emit.py
(audit_flush_dropped_count / audit_spool_stale_recovered /
audit_spool_partial_line_discarded / audit_spool_tamper_detected /
audit_spool_duplicate_tuple_rejected / audit_spool_intentionally_deleted /
audit_spool_unexpected_skip / skill_cache_stats).

Sentinel round-2 GPG-signed by Owner ${OWNER_GPG_FPR}.
Deferred: audit_emit hot-path wire-in (step3) + Wave C sentinel cache
(step4) + Wave E lazy-import shim (step5) — each requires its own
Codex R2 iter before ceremony. Wave A test skeleton is scaffold-only;
full 22-test pack TBD post-step3 wire-in." \
        || die "git commit failed"

    # P1-4 fix (iter-2): signature mismatch is FATAL — if the commit
    # wasn't signed by the expected Owner key, the ceremony cannot
    # proceed to push. Owner can override outside the ceremony if
    # intentional (manual re-sign + manual push).
    HEAD_SIG_FPR="$(git log -1 --format='%GP' 2>/dev/null || echo '')"
    if [[ "${HEAD_SIG_FPR}" != "${OWNER_GPG_FPR}" ]]; then
        die "commit signed by '${HEAD_SIG_FPR}' but expected '${OWNER_GPG_FPR}'. Inspect via: git log -1 --show-signature"
    fi
    color_green "  commit signed by ${OWNER_GPG_FPR}"

    STATE="D_committed"
fi

# ============================================================================
# Step F — Push (optional, with confirmation)
# ============================================================================

if [[ "${STATE}" == "D_committed" ]]; then
    step_banner "Step F — Push to origin/main"

    git log -1 --format='%h %s'
    echo
    if confirm "Push to origin/main now?"; then
        git push origin main || die "push failed"
        color_green "  pushed."
        STATE="E_pushed"
    else
        color_yellow "  skipping push; rerun this script to push later."
    fi
fi

# ============================================================================
# Summary
# ============================================================================

step_banner "Ceremony summary"

echo "  final state: ${STATE}"
echo
case "${STATE}" in
    D_committed)
        color_yellow "  commit landed on local main; rerun script to push when ready"
        ;;
    E_pushed)
        color_green "  PLAN-094 Wave A SHIPPED to origin/main"
        echo
        color_bold "Next:"
        echo "    git log -1 --show-signature   # confirm sig"
        echo "    (later) draft Wave C + Wave E + Codex R2 iter; rerun"
        echo "      scripts/local/plan-094-apply-wave-a-c-e.py with steps3/4/5"
        echo "    (when all 5 waves shipped) tag v1.27.0"
        ;;
esac
