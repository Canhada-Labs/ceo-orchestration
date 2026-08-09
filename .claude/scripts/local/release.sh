#!/usr/bin/env bash
# ============================================================================
# release.sh — operator release driver. Version-neutral BY NAME.
#
# The previous driver carried a release number in its own FILENAME, and was
# still driving the release after that one — the root of a whole class: a
# driver named for one release is a standing invitation for every other version
# literal inside it to go stale too. Everything release-specific now lives in
# the PER-RELEASE block below, and every message derives from it. The old path
# is deliberately left unspelled on every live surface, so the AC-6 control
# needs no "except this one" exemption; `git log --follow` is the archaeology.
#
# Implements the documented procedure in `.github/release-checklist.md`:
# RC first (vX.Y.Z-rc.N), then the ADR-103 24 h hold, then promote stable.
#
# WHAT THE OWNER SIGNS. Nothing here is a canonical-edit ceremony: CHANGELOG.md,
# VERSION and npm/package.json are NOT in `_CANONICAL_GUARDS`
# (`.claude/hooks/check_canonical_edit.py`), so no sentinel `approved.md`
# exists for a release. The Owner signature is the **annotated GPG tag**,
# produced INLINE by the `tag` phase (family lesson: a ceremony script signs
# inline and never demands a pre-existing `.asc`).
#
# WHAT THIS SCRIPT NEVER DOES. It never pushes, and it never publishes.
# Pushing the tag is the irreversible, outward-facing step: it starts BOTH
# `.github/workflows/release.yml` (the release gate) and
# `.github/workflows/npm-publish.yml` — and npm-publish.yml is what actually
# publishes to npm via OIDC. This driver prints the push command and stops.
#
# Phases (run in order):
#   preflight  read-only gates, fail-closed          (default)
#   bump       version sites + plugin manifests + commit
#   tag        annotated GPG tag, signed inline, behind two fail-closed guards
#
# Usage:
#   bash .claude/scripts/local/release.sh preflight
#   bash .claude/scripts/local/release.sh bump --dry-run
#   bash .claude/scripts/local/release.sh bump
#   bash .claude/scripts/local/release.sh tag --dry-run
#   bash .claude/scripts/local/release.sh tag
#
# Options:
#   --dry-run        make no lasting change; restores BOTH working tree and
#                    index on exit (trap), including on failure. The restore
#                    list is DERIVED from _release_bump_sites.py, never typed.
#   --stable         target the bare version instead of -rc.N (post-hold promote)
#   --rc N           RC ordinal (default 1)
#   --key KEYID      GPG key to sign with (default: the key of the last release)
#   --today DATE     YYYY-MM-DD stamped into the `last-reviewed:` lines
#                    (default: today). It exists so the D/D+1 idempotence
#                    invariant is testable at the driver level; it changes only
#                    the stamp date and skips no gate.
#   --restamp        force the four `last-reviewed:` stamps to move even when
#                    the version is unchanged — the named route for a REAL
#                    re-review. Requires --npm-readme-reviewed and disables the
#                    no-op fast path (otherwise it would be dead letter).
#   --offline-ack    ancestry guard: skip the `git fetch` and judge HEAD
#                    against the last-known origin/main (announced loudly)
#   --npm-readme-reviewed
#                    required by `bump` when it writes: acknowledges that
#                    npm/README.md was actually re-read. Its `last-reviewed`
#                    stamp is a release tripwire by design; re-stamping it
#                    silently would defeat the gate.
# ============================================================================
set -euo pipefail

# ---------------------------------------------------------------------------
# PER-RELEASE — the only block that changes between releases. Rewrite all of it
# together. RELEASE_SCOPE and RELEASE_HEADLINE end up inside the SIGNED tag
# annotation, so stale text there is a false claim on a signed surface (the P0
# class of this repo) — and no preflight can prove prose matches a diff.
# The tag stands for the WHOLE release train in CHANGELOG.md, never just the
# newest plan: list every plan of the train and the full ADR range.
# ---------------------------------------------------------------------------
TARGET_BASE="1.3.0"
RELEASE_TITLE="night-mode + release-mechanics hardening"
# repass-r2 part-d P1 (S299): the v1.3.0 train grew past the rc.1 text —
# 167/168 (ownership decision table) and 169 W0-W2 (Linux port + verified
# fixes) landed between rc.1 and rc.2. The tag stands for the WHOLE train.
RELEASE_SCOPE="PLAN-162 / PLAN-165 / PLAN-166 / PLAN-167 / PLAN-168 / PLAN-169 W0-W2 (ADRs 184 -> 190)"
RELEASE_HEADLINE="night-mode — the Owner arms per-machine autonomy for one upcoming
session (gitignored overlay, next-session semantics), and arming it is a
HUMAN action by construction: the writer script self-path-guards, the Bash
rail matches invocation best-effort, and every on/off/refusal lands in the
HMAC chain as night_mode_toggled (proven live, not by fixture).

Also: a case-fold bypass that let .claude/settings.JSON slip past BOTH the
canonical and kernel rails on case-insensitive filesystems (P0, fixed on
both rails); ADR-186 settles the hook-deadline conflict — the canonical
matcher wall deadline fails CLOSED as a named exception to the published
fail-open-on-infrastructure contract, with a provenance-pinned unlock as the
recovery route; sentinel unlock inside a git worktree now REQUIRES that
provenance (ADR-119 Invariant 5); pair-rail 120/150 -> 180/210 with
timeout_ms and a censoring-rate trigger, ratified only after a live probe
proved the harness honors a 210 s registration; four scheduled workflows that
had been red without ever surfacing in push CI; and the release mechanics
themselves — an idempotent bump, plus an ancestry gate and a restricted-delta
gate on the tag phase (PLAN-166)."

RC_NUM="1"
STABLE=0
DRY_RUN=0
NPM_README_REVIEWED=0
RESTAMP=0
OFFLINE_ACK=0
TODAY=""
PHASE=""

BUMP_SITES=".claude/scripts/local/_release_bump_sites.py"
TAG_GUARD=".claude/scripts/local/_release_tag_guard.py"

# Continuity: the key that signed the previous release. Overridable, but never
# guessed at signing time — the preflight proves it can actually produce a
# signature.
SIGN_KEY="CFCFACF00335DC74"

die() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
ok()  { printf '  ok   %s\n' "$*"; }
note(){ printf '  --   %s\n' "$*"; }
hdr() { printf '\n== %s ==\n' "$*"; }

usage() {
  cat <<USAGE
release.sh — operator release driver (target base version: $TARGET_BASE)

  bash $0 preflight [--rc N | --stable]
  bash $0 bump      [--rc N | --stable] --npm-readme-reviewed [--dry-run]
  bash $0 tag       [--rc N | --stable] [--dry-run]

  --dry-run              no lasting change; tree AND index restored on exit
  --stable               target $TARGET_BASE (post-hold promote)
  --rc N                 target ${TARGET_BASE}-rc.N (default N=$RC_NUM)
  --key KEYID            GPG key (default $SIGN_KEY)
  --today YYYY-MM-DD     date stamped into the last-reviewed lines
  --restamp              move the review stamps at an unchanged version
                         (requires --npm-readme-reviewed)
  --offline-ack          ancestry guard judges a possibly stale origin/main
  --npm-readme-reviewed  assert npm/README.md was actually re-read

The header of this file documents what the Owner signs, why this script never
pushes, and why it never publishes.
USAGE
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    preflight|bump|tag) PHASE="$1"; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    --stable)  STABLE=1; shift ;;
    --npm-readme-reviewed) NPM_README_REVIEWED=1; shift ;;
    --restamp) RESTAMP=1; shift ;;
    --offline-ack) OFFLINE_ACK=1; shift ;;
    --today)   TODAY="${2:?--today needs YYYY-MM-DD}"; shift 2 ;;
    --rc)      RC_NUM="${2:?--rc needs a number}"; shift 2 ;;
    --key)     SIGN_KEY="${2:?--key needs a keyid}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done
[ -n "$PHASE" ] || die "no phase given (preflight|bump|tag); see --help"

if [ -n "$TODAY" ]; then
  case "$TODAY" in
    [0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]) ;;
    *) die "--today must be YYYY-MM-DD, got '$TODAY'" ;;
  esac
else
  TODAY="$(date +%F)"
fi

if [ "$STABLE" -eq 1 ]; then
  TARGET_VERSION="$TARGET_BASE"
else
  TARGET_VERSION="${TARGET_BASE}-rc.${RC_NUM}"
fi
TARGET_TAG="v${TARGET_VERSION}"

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || die "not a git repo"
cd "$REPO_ROOT"

# GPG in a non-interactive shell needs an explicit TTY or pinentry fails with
# a misleading "No pinentry" (recurring footgun in this repo ceremonies).
GPG_TTY="$(tty 2>/dev/null || true)"
export GPG_TTY

# Every file the bump phase may write — DERIVED, never typed. A hand-kept
# restore list is how a dry-run left debris behind once already (S273): the
# writer grew a site, the restore list did not. `--include-generated` adds the
# two plugin manifests, which `build-plugin.py --write-manifests` rewrites
# from VERSION during the bump.
sites_out="$(python3 "$BUMP_SITES" print-sites --include-generated)" \
  || die "cannot enumerate version sites from $BUMP_SITES"
VERSION_FILES=()
while IFS= read -r _site; do
  [ -n "$_site" ] || continue
  VERSION_FILES+=("$_site")
done <<< "$sites_out"
[ "${#VERSION_FILES[@]}" -gt 0 ] || die "$BUMP_SITES returned no version sites"

printf 'release driver — target %s (tag %s), phase=%s, dry-run=%s, today=%s\n' \
  "$TARGET_VERSION" "$TARGET_TAG" "$PHASE" "$DRY_RUN" "$TODAY"

# ---------------------------------------------------------------------------
# Dry-run safety net. Snapshot every file the `bump` phase writes plus the
# index state, and restore both on ANY exit path.
# ---------------------------------------------------------------------------
SNAPSHOT_ARMED=0
restore_snapshot() {
  [ "$SNAPSHOT_ARMED" -eq 1 ] || return 0
  # The bump phase refuses to run on a dirty tree (untracked included), so
  # HEAD is exactly the pre-bump state: reset unstages, checkout restores
  # content. Both halves are needed — an index-only restore leaves the files
  # modified, and a content-only restore leaves them staged (the S273 trap).
  #
  # PER PATH, never one multi-path command: `git checkout -- a b c` is
  # ATOMIC — a single path absent from HEAD (a file the bump CREATED, e.g. a
  # plugin manifest on its first appearance) aborts the WHOLE command and
  # restores nothing, and the old `|| true` swallowed that error while the
  # message below still claimed success. A path HEAD carries is checked out;
  # a path HEAD does not carry was created by the bump and is removed.
  local _p _dirty
  for _p in "${VERSION_FILES[@]}"; do
    git reset --quiet HEAD -- "$_p" 2>/dev/null || true
    if git cat-file -e "HEAD:$_p" 2>/dev/null; then
      git checkout --quiet -- "$_p" 2>/dev/null || true
    else
      rm -f "$_p" 2>/dev/null || true
      # a directory created for that file may remain; drop it only if empty
      # (never recursive — this is a restore, not a cleanup)
      rmdir "$(dirname "$_p")" 2>/dev/null || true
    fi
  done
  # ASSERT the postcondition, not the attempt: worktree AND index must be
  # clean across every derived path, or this dry-run left debris and the only
  # honest exit is a loud non-zero — printing "restored" over a dirty tree is
  # the S273 class silenced instead of closed.
  # The verification itself is fail-CLOSED (codex W0-residuals round): if
  # `git status` ERRORS (repo/permission/object failure), an `|| true` here
  # would read as "empty = clean" and print "asserted clean" over a
  # postcondition that was never checked — capture the exit status instead.
  _dirty="$(git status --porcelain -- "${VERSION_FILES[@]}" 2>/dev/null)"
  _status_rc=$?
  if [ "$_status_rc" -ne 0 ]; then
    printf 'FAIL: dry-run restore verification could not run (git status rc=%s) — tree state UNVERIFIED, refusing to report clean\n' "$_status_rc" >&2
    exit 1
  fi
  if [ -n "$_dirty" ]; then
    printf 'FAIL: dry-run restore left these paths dirty (worktree/index != HEAD):\n' >&2
    printf '%s\n' "$_dirty" >&2
    exit 1
  fi
  printf '  --   dry-run: working tree AND index restored to HEAD (asserted clean)\n'
}

take_snapshot() {
  SNAPSHOT_ARMED=1
  trap restore_snapshot EXIT INT TERM
}

hint_next_phase() {
  # Test the VALUE: `${STABLE:+...}` expands for STABLE=0 (a non-empty string)
  # and would tell the Owner to cut the STABLE tag during an RC run.
  if [ "$STABLE" -eq 1 ]; then
    note "proceed to: bash $0 tag --stable"
  else
    note "proceed to: bash $0 tag --rc $RC_NUM"
  fi
}

# ---------------------------------------------------------------------------
# Preflight — every gate fail-closed. Mirrors `.github/release-checklist.md`
# and runs the SAME suites CI runs (a subset gate passes while CI is red; that
# lesson is expensive and already paid).
# ---------------------------------------------------------------------------
preflight() {
  hdr "git state"
  [ -z "$(git status --porcelain)" ] || die "working tree dirty — commit or stash first"
  ok "tree clean"

  branch="$(git rev-parse --abbrev-ref HEAD)"
  [ "$branch" = "main" ] || die "on branch '$branch' — releases are cut from main"
  ok "on main"

  git fetch --quiet origin main || die "git fetch origin main failed"
  local_sha="$(git rev-parse HEAD)"
  remote_sha="$(git rev-parse origin/main)"
  [ "$local_sha" = "$remote_sha" ] \
    || die "HEAD ($local_sha) != origin/main ($remote_sha) — push or pull first"
  ok "HEAD == origin/main ($local_sha)"

  git rev-parse -q --verify "refs/tags/$TARGET_TAG" >/dev/null 2>&1 \
    && die "tag $TARGET_TAG already exists"
  ok "tag $TARGET_TAG is free"

  hdr "CI for HEAD"
  if command -v gh >/dev/null 2>&1; then
    runs="$(gh run list --limit 40 \
      --json headSha,conclusion,status,workflowName 2>/dev/null || true)"
    if [ -n "$runs" ]; then
      verdict="$(mktemp)"
      printf '%s' "$runs" | HEAD_SHA="$local_sha" python3 -c '
import json, os, sys
sha = os.environ["HEAD_SHA"]
runs = [r for r in json.load(sys.stdin) if r.get("headSha") == sha]
if not runs:
    print("NO_RUNS"); sys.exit(0)
bad = [r for r in runs if r.get("conclusion") not in ("success", "skipped", "")]
pend = [r for r in runs if r.get("status") != "completed"]
val = [r for r in runs if "Validate" in (r.get("workflowName") or "")]
for r in bad:
    print("BAD %s=%s" % (r["workflowName"], r["conclusion"]))
for r in pend:
    print("PENDING %s" % r["workflowName"])
if not any(r.get("conclusion") == "success" for r in val):
    print("NO_VALIDATE_SUCCESS")
' > "$verdict" || die "CI verdict parse failed"
      if grep -q '^BAD ' "$verdict"; then
        cat "$verdict" >&2; rm -f "$verdict"
        die "a workflow for HEAD is not green"
      fi
      if grep -q '^PENDING ' "$verdict"; then
        cat "$verdict" >&2; rm -f "$verdict"
        die "a workflow for HEAD is still running — wait for it"
      fi
      if grep -q 'NO_VALIDATE_SUCCESS' "$verdict"; then
        rm -f "$verdict"
        die "no successful Validate run for HEAD"
      fi
      if grep -q 'NO_RUNS' "$verdict"; then
        rm -f "$verdict"
        die "no CI runs found for HEAD — push it and let CI run"
      fi
      rm -f "$verdict"
      ok "all workflows for HEAD green (Validate success)"
    else
      die "gh returned no run data — cannot confirm CI (fail-closed)"
    fi
  else
    die "gh CLI not available — cannot confirm CI (fail-closed)"
  fi

  # These MUST be the invocations validate.yml uses, not `unittest discover`.
  # The suite is pytest-only BY CONSTRUCTION: conftest.py carries the sys.path
  # bootstrap and the _lib resolution guards as pytest collection hooks, and
  # several modules isolate their environment with pytest `autouse` fixtures.
  # `unittest discover` loads none of that, so those modules run with their
  # declared isolation silently disabled — which leaks CLAUDE_PROJECT_DIR into
  # later modules. test_flip_closures then resolves settings.json /
  # red-team.yml under a dead tmp dir and reports that files which plainly
  # exist "must exist". It passes 12/12 when run alone. Diagnosed 2026-08-02
  # during a GA promote; the old invocation made this gate a FALSE RED that
  # blocked a release whose CI was green.
  hdr "test suites (the same ones CI runs)"
  python3 -m pytest .claude/hooks/tests/ -n auto -m 'not serial' \
    --strict-markers --tb=no -q >/dev/null 2>&1 \
    || die "hooks test suite failed (not serial)"
  python3 -m pytest .claude/hooks/tests/ -m 'serial' \
    --strict-markers --tb=no -q >/dev/null 2>&1 \
    || die "hooks test suite failed (serial)"
  ok "hooks tests pass"
  python3 -m pytest .claude/scripts/tests/ .claude/scripts/optimizer/tests/ \
    -n auto -m 'not serial' --strict-markers --tb=no -q >/dev/null 2>&1 \
    || die "scripts test suite failed (not serial)"
  python3 -m pytest .claude/scripts/tests/ .claude/scripts/optimizer/tests/ \
    -m 'serial' --strict-markers --tb=no -q >/dev/null 2>&1 \
    || die "scripts test suite failed (serial)"
  ok "scripts tests pass"

  hdr "governance gates"
  bash .claude/scripts/validate-governance.sh >/dev/null 2>&1 \
    || die "validate-governance.sh nonzero"
  ok "validate-governance"
  bash .claude/scripts/check-contamination.sh >/dev/null 2>&1 \
    || die "check-contamination.sh nonzero"
  ok "check-contamination"
  python3 .claude/scripts/check-claude-md-claims.py >/dev/null 2>&1 \
    || die "check-claude-md-claims.py nonzero"
  ok "CLAUDE.md claims"
  bash .claude/scripts/local/verify-counts.sh --quiet >/dev/null 2>&1 \
    || die "verify-counts.sh reports drift"
  ok "derived counts (no drift)"

  hdr "release artifacts"
  grep -q "^## \[${TARGET_BASE}\]" CHANGELOG.md \
    || die "CHANGELOG.md has no '## [${TARGET_BASE}]' entry"
  ok "CHANGELOG has [${TARGET_BASE}]"

  # Two gates that burned earlier RCs — release.yml enforces both and neither
  # is covered by verify-counts, so the preflight mirrors them:
  python3 scripts/build-plugin.py --check >/dev/null 2>&1 \
    || die "plugin manifests out of sync (run: python3 scripts/build-plugin.py --write-manifests)"
  ok "plugin manifests in sync with generator"
  python3 .claude/scripts/check-canonical-doc-freshness.py >/dev/null 2>&1 \
    || {
      python3 .claude/scripts/check-canonical-doc-freshness.py 2>&1 | grep '!!' >&2 || true
      die "canonical doc freshness gate red (stale last-reviewed stamps; review + re-stamp the docs listed above)"
    }
  ok "canonical doc freshness (review stamps current)"

  cur_version="$(tr -d ' \n' < VERSION)"
  if [ "$cur_version" = "$TARGET_BASE" ]; then
    note "VERSION already $TARGET_BASE — bump phase is a no-op (expected on promote)"
  else
    note "VERSION is $cur_version, becomes $TARGET_BASE in the bump phase"
  fi

  hdr "signing key (proves it can actually sign — not just that it exists)"
  gpg --list-secret-keys "$SIGN_KEY" >/dev/null 2>&1 \
    || die "no secret key $SIGN_KEY in the keyring"
  ok "secret key $SIGN_KEY present"
  sig_probe="$(mktemp)"
  if printf 'release-preflight-probe' \
      | gpg --local-user "$SIGN_KEY" --armor --detach-sign --output "$sig_probe" \
        >/dev/null 2>&1; then
    ok "inline signature probe succeeded (pinentry works)"
  else
    rm -f "$sig_probe"
    die "the key cannot sign right now — try: gpgconf --kill gpg-agent; export GPG_TTY=\$(tty)"
  fi
  rm -f "$sig_probe"

  printf '\nPREFLIGHT GREEN for %s\n' "$TARGET_TAG"
}

# ---------------------------------------------------------------------------
# Bump.
#
# The site table lives in `_release_bump_sites.py` and NOWHERE else: this
# driver invokes it, and derives the dry-run restore list from it.
#
# The version written is always the BARE semver ($TARGET_BASE), never
# X.Y.Z-rc.N. Two independent reasons: (a) precedent — every previous RC
# carries the bare version in VERSION, the RC lives only in the tag name;
# (b) every gate regex matches `\d+\.\d+\.\d+` only, so an -rc.N string would
# match NOTHING and the gate would pass VACUOUSLY — silently stopping the
# drift check exactly when it matters most.
#
# IDEMPOTENCE (F2, the v1.3.0-rc.1 re-pass). A bump on a tree that is already
# at the target must write NOTHING — not one byte, not one index entry. It
# used to re-date four `last-reviewed:` stamps with today date, which on D+1
# of the ADR-103 hold produced a dirty tree, then a commit made AFTER the
# preflight proved CI green, which `tag()` then signed. That commit was also
# invisible to the pair-rail step 15 (none of the four files is in
# `pair-rail-inputs-hash-manifest.txt`). Two independent defenses now:
#   1. the same-tree predicate below (four oracles) short-circuits the phase;
#   2. the writer skips each stamp line whose version is already the target.
# ---------------------------------------------------------------------------
_oracle() {
  label="$1"; shift
  if "$@" >/dev/null 2>&1; then
    printf '  --   oracle %s: PASS  (%s)\n' "$label" "$*"
    return 0
  fi
  printf '  --   oracle %s: RED   (%s)\n' "$label" "$*"
  return 1
}

# All four are required. The fourth is not redundant: it is the ONLY watcher
# of the SBOM/SECURITY/VERSIONING stamps, which are outside the VERSION_SITES
# of verify-counts. Without it an external no-op would block the in-loop
# self-heal from ever running over a stale stamp. Freezing the DATE is safe
# because the freshness gate decides on the stamp VERSION, not its date.
tree_already_at_target() {
  cur_version="$(tr -d ' \n' < VERSION)"
  printf '  --   oracle 1/4: VERSION=%s, target=%s\n' "$cur_version" "$TARGET_BASE"
  [ "$cur_version" = "$TARGET_BASE" ] || return 1
  _oracle "2/4" bash .claude/scripts/local/verify-counts.sh --quiet --no-tests || return 1
  _oracle "3/4" python3 scripts/build-plugin.py --check || return 1
  _oracle "4/4" python3 .claude/scripts/check-canonical-doc-freshness.py || return 1
  return 0
}

bump() {
  hdr "bump version sites to $TARGET_BASE"
  [ -z "$(git status --porcelain)" ] || die "working tree dirty — refusing to bump"

  if [ "$RESTAMP" -eq 1 ] && [ "$NPM_README_REVIEWED" -eq 0 ]; then
    die "--restamp moves every last-reviewed stamp — it REQUIRES --npm-readme-reviewed, otherwise it is exactly the tripwire bypass the stamp exists to prevent"
  fi

  if [ "$RESTAMP" -eq 1 ]; then
    hdr "restamp requested — no-op fast path DISABLED by design"
    note "in the normal re-review case (same version, four clean oracles) the"
    note "predicate would return BEFORE any substitution and --restamp would"
    note "be dead letter. It is skipped so a real re-review can be recorded."
  else
    hdr "same-tree predicate — four oracles, ALL required"
    if tree_already_at_target; then
      ok "no-op: tree is already at $TARGET_BASE and all four oracles are clean"
      note "NOTHING was written: not a file, not an index entry. The"
      note "post-condition of this phase (tree at $TARGET_BASE, gates green) is"
      note "already satisfied, so a no-op bump is SUCCESS, not failure."
      note "For a genuine re-review of the docs: --restamp --npm-readme-reviewed"
      hint_next_phase
      return 0
    fi
    note "at least one oracle is unsatisfied — running the bump"
  fi

  # The npm/README.md stamp is a DELIBERATE release tripwire: its date+version
  # line asserts the npm-facing copy was re-read for this release. Re-stamping
  # it silently would defeat the whole purpose of the gate, so it takes an
  # explicit acknowledgement. Checked AFTER the no-op predicate on purpose: a
  # run that writes nothing asserts nothing, and demanding the flag there would
  # be asking the Owner to certify a review that is not happening.
  if [ "$NPM_README_REVIEWED" -eq 0 ]; then
    cat >&2 <<'EOF'
FAIL: npm/README.md carries a "last-reviewed: <date> v<version>" stamp, and
      verify-counts treats it as a release tripwire — bumping it asserts that
      the npm-facing README was actually re-read for this release.

      Read npm/README.md, then re-run with --npm-readme-reviewed.
EOF
    exit 1
  fi

  [ "$DRY_RUN" -eq 1 ] && take_snapshot

  if [ "$RESTAMP" -eq 1 ]; then
    python3 "$BUMP_SITES" bump --target "$TARGET_BASE" --today "$TODAY" --restamp \
      || die "version-site bump failed"
  else
    python3 "$BUMP_SITES" bump --target "$TARGET_BASE" --today "$TODAY" \
      || die "version-site bump failed"
  fi

  # Plugin manifests (.claude-plugin/{plugin,marketplace}.json) are GENERATED
  # from VERSION, never hand-patched. The release.yml gate "Assert plugin
  # manifest versions match VERSION" enforces them — and verify-counts does
  # NOT, which is exactly how the v1.2.0-rc.1 run went red: the manifests were
  # version sites invisible to the local oracle.
  python3 scripts/build-plugin.py --write-manifests >/dev/null 2>&1 \
    || die "build-plugin.py --write-manifests failed"
  python3 scripts/build-plugin.py --check >/dev/null 2>&1 \
    || die "plugin manifests still out of sync with the generator"
  ok "plugin manifests regenerated from VERSION (build-plugin.py)"

  # verify-counts covers the doc/package sites; the release.yml gate family
  # covers the plugin manifests; the freshness gate covers the review stamps
  # outside both. NOT ONE of them is the full oracle — the union is. If a new
  # site is added upstream, expect it to surface in one of the three, and
  # mirror it into _release_bump_sites.py.
  bash .claude/scripts/local/verify-counts.sh --quiet --no-tests >/dev/null 2>&1 \
    || {
      bash .claude/scripts/local/verify-counts.sh --json --no-tests 2>&1 \
        | python3 -c 'import json,sys
d = json.load(sys.stdin)
for v in d.get("violations", []):
    print("  !!   " + v, file=sys.stderr)' || true
      die "verify-counts still reports version drift — a site is unpatched (see above)"
    }
  ok "verify-counts clean across the doc/package version sites"

  if [ "$DRY_RUN" -eq 1 ]; then
    git --no-pager diff --stat || true
    note "dry-run: no commit made"
    return 0
  fi

  git add -A
  # IDEMPOTENCE, second rail. Even past the predicate, if nothing ended up
  # staged an unconditional `git commit` would DIE and the documented
  # three-phase path would be unusable exactly when the gates are green.
  if git diff --cached --quiet; then
    ok "nothing to commit — tree already at ${TARGET_BASE} (idempotent no-op)"
    hint_next_phase
    return 0
  fi
  git commit -q -m "release: v${TARGET_BASE}

Version bump across every site the three oracles enforce (the doc/package
sites of verify-counts, the plugin manifests regenerated by build-plugin.py,
and the last-reviewed stamps watched by check-canonical-doc-freshness.py) for
${TARGET_TAG}. The site table is .claude/scripts/local/_release_bump_sites.py.

VERSION carries the BARE semver: the RC lives only in the tag name. An -rc.N
string in VERSION would match none of the \\d+.\\d+.\\d+ patterns of the gate and
the drift check would pass vacuously.

CHANGELOG entry [${TARGET_BASE}] landed separately; its counts are
reproducible via .claude/scripts/local/verify-counts.sh."
  ok "commit $(git rev-parse --short HEAD)"

  cat >&2 <<EOF

  NOTE: this bump created a commit. The ancestry guard of the tag phase
  requires HEAD to be an ancestor of origin/main, so PUSH main and let CI run
  before tagging — a tag on an unpushed commit points at a tree CI never saw.
EOF
}

# ---------------------------------------------------------------------------
# Tag — annotated + GPG-signed INLINE. The tag message is the Owner-visible
# artifact; pushing it starts release.yml AND npm-publish.yml.
#
# Two fail-closed guards run first, for RC and stable ALIKE. Scoping them to
# `--stable` would let an rc.N ship a post-review commit and then become the
# unreviewed baseline the GA is promoted from.
#
# THE LOCAL ASSERT IS NOT ENOUGH — say it out loud. A tag signed by hand skips
# this driver entirely, and the pair-rail step 15 recomputes inputs_hash only
# over `pair-rail-inputs-hash-manifest.txt`, which deliberately EXCLUDES the
# bump surfaces (including them would make every legitimate bump change the
# inputs_hash and break the verdict replay). The same restricted-delta assert
# therefore goes SERVER-SIDE into `.github/workflows/release.yml` in PLAN-166
# W1. release.yml is canonical: it changes under the GPG ceremony, not here.
# `_release_tag_guard.py` is the reference implementation for both.
# ---------------------------------------------------------------------------
tag() {
  hdr "sign tag $TARGET_TAG"
  [ -z "$(git status --porcelain)" ] || die "working tree dirty — refusing to tag"

  # VERSION carries the BARE semver even for an RC tag (see the bump header),
  # so compare against $TARGET_BASE, never $TARGET_VERSION.
  cur_version="$(tr -d ' \n' < VERSION)"
  [ "$cur_version" = "$TARGET_BASE" ] \
    || die "VERSION is '$cur_version', expected $TARGET_BASE for $TARGET_TAG — run the bump phase first"
  ok "VERSION ($cur_version) matches the base version of the tag"

  git rev-parse -q --verify "refs/tags/$TARGET_TAG" >/dev/null 2>&1 \
    && die "tag $TARGET_TAG already exists"

  hdr "tag guards (unconditional — RC and stable)"
  if [ "$OFFLINE_ACK" -eq 1 ]; then
    python3 "$TAG_GUARD" ancestry --repo "$REPO_ROOT" --remote origin --branch main --offline-ack \
      || die "ancestry guard refused the tag (see above)"
  else
    python3 "$TAG_GUARD" ancestry --repo "$REPO_ROOT" --remote origin --branch main \
      || die "ancestry guard refused the tag (see above)"
  fi
  python3 "$TAG_GUARD" delta --repo "$REPO_ROOT" --tag "$TARGET_TAG" \
    || die "restricted-delta guard refused the tag (see above)"

  anchor="$(git rev-parse HEAD)"
  msg="$TARGET_TAG — $RELEASE_TITLE

Anchor: $anchor
Scope:  $RELEASE_SCOPE

Headline: $RELEASE_HEADLINE

No speed claim. See CHANGELOG.md [$TARGET_BASE]."

  if [ "$DRY_RUN" -eq 1 ]; then
    note "dry-run: tag NOT created. Message that would be signed:"
    printf '%s\n' "$msg" | sed 's/^/      | /'
    return 0
  fi

  git tag -s -u "$SIGN_KEY" -m "$msg" "$TARGET_TAG" \
    || die "git tag -s failed (key $SIGN_KEY)"
  ok "tag created"

  git tag -v "$TARGET_TAG" >/dev/null 2>&1 \
    || die "tag signature does not verify — delete it and investigate"
  ok "tag signature verifies"

  cat <<EOF

TAG $TARGET_TAG IS SIGNED LOCALLY AND NOT PUSHED.

Pushing starts release.yml (the gate) and npm-publish.yml (which is what
publishes to npm, via OIDC). That is the irreversible, outward-facing step —
it stays yours:

    git push origin $TARGET_TAG

Then, per .github/release-checklist.md:
  - gh run watch                      (all release.yml steps green)
EOF
  if [ "$STABLE" -eq 1 ]; then
    cat <<EOF
  - GitHub Release from the tag, "pre-release" NOT checked (this is the GA)
  - npm view <pkg> version            (OIDC publish landed the bare semver)
  - close the release: CHANGELOG links, memory topic, archive the RC hold
EOF
  else
    cat <<EOF
  - GitHub Release from the tag, "pre-release" checked while this is an RC
  - ADR-103 hold: >=24 h, Codex re-pass against the RC, adopter smoke test
  - promote: bash $0 bump --stable --npm-readme-reviewed && bash $0 tag --stable
EOF
  fi
}

case "$PHASE" in
  preflight) preflight ;;
  bump)      bump ;;
  tag)       tag ;;
  *)         die "unreachable phase: $PHASE" ;;
esac
