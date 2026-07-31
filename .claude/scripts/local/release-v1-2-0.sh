#!/usr/bin/env bash
# ============================================================================
# release-v1-2-0.sh — operator release driver for v1.2.0.
#
# Implements the documented procedure in `.github/release-checklist.md`:
# RC first (`v1.2.0-rc.1`), then the ADR-103 24 h hold, then promote stable.
# Both prior releases (v1.0.1, v1.1.0) followed that shape; this script does
# not invent a new one.
#
# WHAT THE OWNER SIGNS. Nothing here is a canonical-edit ceremony: CHANGELOG.md,
# VERSION and npm/package.json are NOT in `_CANONICAL_GUARDS`
# (`.claude/hooks/check_canonical_edit.py:113`), so no sentinel `approved.md`
# exists for a release. The Owner's signature is the **annotated GPG tag**,
# produced INLINE by the `tag` phase (family lesson: a ceremony script signs
# inline and never demands a pre-existing `.asc`).
#
# WHAT THIS SCRIPT NEVER DOES. It never pushes. `git push` of a tag is the
# irreversible, outward-facing step that starts `release.yml` (which publishes
# to npm via OIDC), so it stays a deliberate human command. The script prints
# it and stops.
#
# Phases (run in order):
#   preflight  read-only gates, fail-closed          (default)
#   bump       VERSION + npm/package.json + commit
#   tag        annotated GPG tag, signed inline
#
# Usage:
#   bash .claude/scripts/local/release-v1-2-0.sh preflight
#   bash .claude/scripts/local/release-v1-2-0.sh bump --dry-run
#   bash .claude/scripts/local/release-v1-2-0.sh bump
#   bash .claude/scripts/local/release-v1-2-0.sh tag --dry-run
#   bash .claude/scripts/local/release-v1-2-0.sh tag
#
# Options:
#   --dry-run        make no lasting change; restores BOTH working tree and
#                    index on exit (trap), including on failure
#   --stable         target v1.2.0 instead of v1.2.0-rc.N (post-hold promote)
#   --rc N           RC ordinal (default 1)
#   --key KEYID      GPG key to sign with (default: the key that signed v1.1.0)
#   --npm-readme-reviewed
#                    required by `bump`: acknowledges that npm/README.md was
#                    actually re-read. Its "last-reviewed" stamp is a release
#                    tripwire by design; re-stamping it silently would defeat
#                    the gate.
# ============================================================================
set -euo pipefail

TARGET_BASE="1.2.0"
RC_NUM="1"
STABLE=0
DRY_RUN=0
NPM_README_REVIEWED=0
PHASE=""

# Every file the bump phase may write. Load-bearing for the dry-run trap:
# a restore list shorter than the write list leaves debris behind.
VERSION_FILES=(
  "VERSION"
  "npm/package.json"
  "pyproject.toml"
  "INSTALL.md"
  "docs/ARCHITECTURE.md"
  "npm/README.md"
  "README.md"
)
# Continuity: the key that signed v1.1.0. Overridable, but never guessed at
# signing time — the preflight proves it can actually produce a signature.
SIGN_KEY="CFCFACF00335DC74"

die() { printf 'FAIL: %s\n' "$*" >&2; exit 1; }
ok()  { printf '  ok   %s\n' "$*"; }
note(){ printf '  --   %s\n' "$*"; }
hdr() { printf '\n== %s ==\n' "$*"; }

while [ "$#" -gt 0 ]; do
  case "$1" in
    preflight|bump|tag) PHASE="$1"; shift ;;
    --dry-run) DRY_RUN=1; shift ;;
    --stable)  STABLE=1; shift ;;
    --npm-readme-reviewed) NPM_README_REVIEWED=1; shift ;;
    --rc)      RC_NUM="${2:?--rc needs a number}"; shift 2 ;;
    --key)     SIGN_KEY="${2:?--key needs a keyid}"; shift 2 ;;
    -h|--help) sed -n '2,40p' "$0"; exit 0 ;;
    *) die "unknown argument: $1" ;;
  esac
done
[ -n "$PHASE" ] || die "no phase given (preflight|bump|tag); see --help"

if [ "$STABLE" -eq 1 ]; then
  TARGET_VERSION="$TARGET_BASE"
else
  TARGET_VERSION="${TARGET_BASE}-rc.${RC_NUM}"
fi
TARGET_TAG="v${TARGET_VERSION}"

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || die "not a git repo"
cd "$REPO_ROOT"

# GPG in a non-interactive shell needs an explicit TTY or pinentry fails with
# a misleading "No pinentry" (recurring footgun in this repo's ceremonies).
GPG_TTY="$(tty 2>/dev/null || true)"
export GPG_TTY

printf 'release driver — target %s (tag %s), phase=%s, dry-run=%s\n' \
  "$TARGET_VERSION" "$TARGET_TAG" "$PHASE" "$DRY_RUN"

# ---------------------------------------------------------------------------
# Dry-run safety net. Snapshot the two files the `bump` phase writes plus the
# index state, and restore both on ANY exit path. A dry-run that leaves staged
# deletions behind has bitten this repo before (S273).
# ---------------------------------------------------------------------------
SNAPSHOT_ARMED=0
restore_snapshot() {
  [ "$SNAPSHOT_ARMED" -eq 1 ] || return 0
  # The bump phase refuses to run on a dirty tree, so HEAD is exactly the
  # pre-bump state: reset unstages, checkout restores content. Both halves are
  # needed — an index-only restore leaves the files modified, and a
  # content-only restore leaves them staged (the S273 trap).
  git reset --quiet HEAD -- "${VERSION_FILES[@]}" 2>/dev/null || true
  git checkout --quiet -- "${VERSION_FILES[@]}" 2>/dev/null || true
  printf '  --   dry-run: working tree AND index restored to HEAD\n'
}

take_snapshot() {
  SNAPSHOT_ARMED=1
  trap restore_snapshot EXIT INT TERM
}

# ---------------------------------------------------------------------------
# Preflight — every gate fail-closed. Mirrors `.github/release-checklist.md`
# §Pré-tag and runs the SAME suites CI runs (a subset gate passes while CI is
# red; that lesson is expensive and already paid).
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

  hdr "test suites (the same ones CI runs)"
  python3 -m unittest discover -s .claude/hooks/tests >/dev/null 2>&1 \
    || die "hooks test suite failed"
  ok "hooks tests pass"
  python3 -m unittest discover -s .claude/scripts/tests >/dev/null 2>&1 \
    || die "scripts test suite failed"
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

  cur_version="$(tr -d ' \n' < VERSION)"
  if [ "$cur_version" = "$TARGET_BASE" ]; then
    note "VERSION already $TARGET_BASE — bump phase is a no-op (expected on promote)"
  else
    note "VERSION is $cur_version, becomes $TARGET_BASE in the bump phase (6 sites)"
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
# Bump — SIX version sites, not two.
#
# `verify-counts.sh` enforces exact version equality across VERSION,
# npm/package.json, pyproject.toml, INSTALL.md, docs/ARCHITECTURE.md and
# npm/README.md (`:384-421`). The release checklist mentions only VERSION,
# which is how a manual bump silently misses pyproject + the three docs — the
# `bump --dry-run` of this script is what surfaced that.
#
# The version written is always the BARE semver ($TARGET_BASE), never
# `1.2.0-rc.1`. Two independent reasons: (a) precedent — `v1.1.0-rc.1` and
# `v1.0.1-rc.1` both carry the bare version in VERSION, the RC lives only in
# the tag name; (b) every gate regex matches `\d+\.\d+\.\d+` only, so an
# `-rc.N` string would match NOTHING and the gate would pass VACUOUSLY —
# silently stopping the drift check exactly when it matters most.
#
# Regex-targeted (never a blanket 1.1.0 -> 1.2.0 sweep): the anchored patterns
# below are copied from verify-counts' own sites, so historical version
# mentions in CHANGELOG entries and docs are left untouched.
# ---------------------------------------------------------------------------
bump() {
  hdr "bump version sites to $TARGET_BASE"
  [ -z "$(git status --porcelain)" ] || die "working tree dirty — refusing to bump"

  [ "$DRY_RUN" -eq 1 ] && take_snapshot

  # The npm/README.md stamp is a DELIBERATE release tripwire: its date+version
  # line asserts the npm-facing copy was re-read for this release. Re-stamping
  # it silently would defeat the gate's whole purpose, so it takes an explicit
  # acknowledgement.
  if [ "$NPM_README_REVIEWED" -eq 0 ]; then
    cat >&2 <<'EOF'
FAIL: npm/README.md carries a "last-reviewed: <date> v<version>" stamp, and
      verify-counts treats it as a release tripwire — bumping it asserts that
      the npm-facing README was actually re-read for this release.

      Read npm/README.md, then re-run with --npm-readme-reviewed.
EOF
    exit 1
  fi

  TARGET_BASE="$TARGET_BASE" python3 - <<'PY' || die "version-site bump failed"
import os, re, sys, datetime

target = os.environ["TARGET_BASE"]
today = datetime.date.today().isoformat()
SEMVER = r'\d+\.\d+\.\d+'

# (path, pattern, replacement) — patterns anchored exactly as verify-counts
# checks them, so nothing else in the file can be touched.
SITES = [
    ("VERSION", r'\A\s*' + SEMVER + r'\s*\Z', target + "\n"),
    ("npm/package.json", r'("version"\s*:\s*")' + SEMVER + r'(")', r'\g<1>' + target + r'\g<2>'),
    ("pyproject.toml", r'(?m)^(version\s*=\s*")' + SEMVER + r'(")', r'\g<1>' + target + r'\g<2>'),
    ("INSTALL.md", r'(--pin v)' + SEMVER, r'\g<1>' + target),
    ("docs/ARCHITECTURE.md",
     r'(currently\s+v)' + SEMVER + r'(, aligned with the repo)',
     r'\g<1>' + target + r'\g<2>'),
    ("npm/README.md",
     r'(last-reviewed: )\d{4}-\d{2}-\d{2} v' + SEMVER,
     r'\g<1>' + today + ' v' + target),
    # Present in the watched list but currently has no such literal; a zero
    # match here is fine — verify-counts is the oracle, not this table.
    ("README.md", r'(VERSION=)' + SEMVER, r'\g<1>' + target),
]

for path, rx, repl in SITES:
    try:
        src = open(path, encoding="utf-8").read()
    except OSError:
        print("  --   %s absent, skipped" % path)
        continue
    new, n = re.subn(rx, repl, src)
    if n == 0:
        print("  --   %s: no version site found (ok if unwatched)" % path)
        continue
    if new != src:
        open(path, "w", encoding="utf-8").write(new)
    print("  ok   %s (%d site%s -> %s)" % (path, n, "" if n == 1 else "s", target))
PY

  # verify-counts is the ORACLE for this phase, not the table above. If a
  # seventh site is ever added upstream, this is what catches it.
  bash .claude/scripts/local/verify-counts.sh --quiet --no-tests >/dev/null 2>&1 \
    || {
      bash .claude/scripts/local/verify-counts.sh --json --no-tests 2>&1 \
        | python3 -c 'import json,sys
d = json.load(sys.stdin)
for v in d.get("violations", []):
    print("  !!   " + v, file=sys.stderr)' || true
      die "verify-counts still reports version drift — a site is unpatched (see above)"
    }
  ok "verify-counts clean across every version site"

  if [ "$DRY_RUN" -eq 1 ]; then
    git --no-pager diff --stat || true
    note "dry-run: no commit made"
    return 0
  fi

  git add -A
  git commit -q -m "release: v${TARGET_BASE}

Version bump across all six sites verify-counts enforces (VERSION,
npm/package.json, pyproject.toml, INSTALL.md, docs/ARCHITECTURE.md,
npm/README.md review stamp) for ${TARGET_TAG}.

VERSION carries the BARE semver: the RC lives only in the tag name, matching
v1.1.0-rc.1 / v1.0.1-rc.1. An -rc.N string in VERSION would match none of the
gate's \\d+.\\d+.\\d+ patterns and the drift check would pass vacuously.

CHANGELOG entry [${TARGET_BASE}] landed separately; its counts are
reproducible via .claude/scripts/local/verify-counts.sh."
  ok "commit $(git rev-parse --short HEAD)"
}

# ---------------------------------------------------------------------------
# Tag — annotated + GPG-signed INLINE. The tag message is the Owner-visible
# artifact; `release.yml` triggers on `push: tags: v*`.
# ---------------------------------------------------------------------------
tag() {
  hdr "sign tag $TARGET_TAG"
  [ -z "$(git status --porcelain)" ] || die "working tree dirty — refusing to tag"

  # VERSION carries the BARE semver even for an RC tag (see the bump header),
  # so compare against $TARGET_BASE, never $TARGET_VERSION.
  cur_version="$(tr -d ' \n' < VERSION)"
  [ "$cur_version" = "$TARGET_BASE" ] \
    || die "VERSION is '$cur_version', expected $TARGET_BASE for $TARGET_TAG — run the bump phase first"
  ok "VERSION ($cur_version) matches the tag's base version"

  git rev-parse -q --verify "refs/tags/$TARGET_TAG" >/dev/null 2>&1 \
    && die "tag $TARGET_TAG already exists"

  anchor="$(git rev-parse HEAD)"
  msg="$TARGET_TAG — substrate + rail release

Anchor: $anchor
Scope:  PLAN-160 / PLAN-161 / PLAN-163 / PLAN-164 (ADRs 178 -> 184)

Headline: the cross-model pair-rail completed a live in-hook review for the
first time in the audit log's history (case A, 115 s). Before this release
all 12 pair_rail_case events on record were case F / TIMEOUT — the rail was
100% fail-open because its 30 s internal default sat below real verdict
latency (ADR-110-AMEND-1: internal 30->120, registration 60->150, invariant
now tested).

Also: Claude Code 2.1.220 + Claude 5 model registry (ADR-181), Codex payload
pin with verify-then-invoke (ADR-182), canonical-edit fail-closed
multi-candidate resolution (ADR-164/165), adopter upgrade oracles in
smoke-install, and the disableAutoMode fix (a boolean there makes 2.1.220
skip the ENTIRE settings.json — governance silently absent).

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

Pushing starts release.yml, which publishes to npm via OIDC. That is the
irreversible, outward-facing step — it stays yours:

    git push origin $TARGET_TAG

Then, per .github/release-checklist.md:
  - gh run watch                      (all release.yml steps green)
  - GitHub Release from the tag, "pre-release" checked while this is an RC
  - ADR-103 hold: >=24 h, Codex re-pass against the RC, adopter smoke test
  - promote: bash $0 bump --stable && bash $0 tag --stable
EOF
}

case "$PHASE" in
  preflight) preflight ;;
  bump)      bump ;;
  tag)       tag ;;
  *)         die "unreachable phase: $PHASE" ;;
esac
