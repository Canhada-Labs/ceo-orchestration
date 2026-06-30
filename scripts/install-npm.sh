#!/usr/bin/env bash
# install-npm.sh — local NPM tarball build + smoke-test for ceo-orchestration.
#
# Sprint 13 Phase 2 (PLAN-013) / ROADMAP-CLOSURE Marco 1 — does NOT
# publish. Builds a local tarball + optionally tests it in a temp
# directory. Use this to validate the npm shim before any tag-push
# triggers the real publish workflow (.github/workflows/npm-publish.yml).
#
# Usage:
#   bash scripts/install-npm.sh                   # build tarball only
#   bash scripts/install-npm.sh --smoke           # build + smoke-test in /tmp
#   bash scripts/install-npm.sh --smoke --keep    # smoke + leave artifacts
#
# Exit codes:
#   0 — tarball built (and optional smoke passed)
#   1 — build error
#   2 — smoke-test failure
#   3 — environment missing (node / npm / bash)
#
# Stays disabled for actual publish. The CI workflow npm-publish.yml is
# the only path to npmjs.org and gates through OIDC + manual approval
# in production-npm environment.

set -euo pipefail

# -------------------------------- args ---------------------------------------
SMOKE=0
KEEP=0
for arg in "$@"; do
  case "$arg" in
    --smoke) SMOKE=1 ;;
    --keep)  KEEP=1 ;;
    -h|--help)
      cat <<'HELP'
Usage:
  bash scripts/install-npm.sh                   Build local ceo-orchestration tarball only.
  bash scripts/install-npm.sh --smoke           Build + smoke-test the tarball in a /tmp dir.
  bash scripts/install-npm.sh --smoke --keep    Smoke-test and KEEP the temp artifacts for inspection.

Flags:
  --smoke           Run the smoke-test harness against the freshly built tarball.
                    Creates a throwaway $TMPDIR install + validates that `npx ceo-orchestration`
                    bootstraps a minimal target. Exits 2 on smoke failure.
  --keep            Used with --smoke; preserves the temp install dir for forensic inspection.
                    Without this flag the temp dir is removed on smoke completion.
  -h, --help        Show this help and exit 0.

Exit codes:
  0 — tarball built (and optional smoke passed)
  1 — build error or unknown arg
  2 — smoke-test failure
  3 — environment missing (node / npm / bash)

Notes:
  This script DOES NOT publish to the npm registry. It only builds the local tarball
  + optionally validates it locally. Real publishing flows through:
      .github/workflows/npm-publish.yml
  which gates on OIDC + manual approval in the production-npm environment.

  Use this to validate the npm shim BEFORE any tag-push triggers the real publish
  workflow. The CI workflow expects this script to have been run on the release
  candidate; manual local validation is the source of truth for the smoke harness.
HELP
      exit 0
      ;;
    *)
      echo "::error::unknown arg: $arg" >&2
      exit 1
      ;;
  esac
done

# -------------------------------- env check ----------------------------------
for cmd in node npm bash; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "::error::required command missing: $cmd" >&2
    exit 3
  fi
done

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NPM_DIR="$ROOT/npm"

if [[ ! -d "$NPM_DIR" ]]; then
  echo "::error::npm/ directory missing at $NPM_DIR" >&2
  exit 1
fi

# -------------------------------- version sync check -------------------------
VERSION_FILE="$(tr -d '[:space:]' < "$ROOT/VERSION")"
PKG_VERSION="$(node -p "require('$NPM_DIR/package.json').version")"
if [[ "$VERSION_FILE" != "$PKG_VERSION" ]]; then
  echo "::error::VERSION ($VERSION_FILE) ≠ npm/package.json ($PKG_VERSION)" >&2
  echo "Update npm/package.json::version to $VERSION_FILE before building." >&2
  exit 1
fi
echo "OK: version sync — $VERSION_FILE"

# -------------------------------- stage bundle -------------------------------
# Copy framework source tree into npm/ so npm pack picks it up via files: list.
# Mirror npm-publish.yml step "Stage bundle into npm/".
echo "==> Staging bundle into npm/"
for src in scripts templates .claude SPEC VERSION LICENSE README.md PROTOCOL.md; do
  if [[ -e "$ROOT/$src" ]]; then
    cp -r "$ROOT/$src" "$NPM_DIR/"
  fi
done

# Sanity: install.sh present in staged bundle.
if [[ ! -f "$NPM_DIR/scripts/install.sh" ]]; then
  echo "::error::staged bundle missing scripts/install.sh" >&2
  exit 1
fi

# Syntax-check the shim (mirror npm-publish.yml step).
node --check "$NPM_DIR/bin/ceo-orch-init.js"
echo "OK: shim syntax"

# -------------------------------- npm pack -----------------------------------
echo "==> Building tarball"
TARBALL="$(cd "$NPM_DIR" && npm pack 2>/dev/null | tail -1)"
TARBALL_PATH="$NPM_DIR/$TARBALL"

if [[ ! -f "$TARBALL_PATH" ]]; then
  echo "::error::npm pack did not produce $TARBALL_PATH" >&2
  exit 1
fi
TARBALL_SIZE_KB=$(( $(wc -c < "$TARBALL_PATH") / 1024 ))
echo "OK: tarball built — $TARBALL ($TARBALL_SIZE_KB KB)"

# -------------------------------- sha256 emission ----------------------------
# PLAN-019 DevOps-P2-3 — supply-chain tarball integrity.
#
# The shipped NPM tarball MUST carry a sha256 checksum so consumers + CI can
# verify the bytes against what was produced locally. Emit the checksum next
# to the tarball in NPM_DIR/SHA256SUMS.txt (cumulative file; one line per
# build). CI verification (npm-publish.yml) computes the checksum of the
# tarball it publishes and appends to the release notes.
#
# Format is `<64-hex>  <filename>` — compatible with `sha256sum -c` so a
# consumer can do:
#   curl -LO https://registry.npmjs.org/.../tarball
#   curl -LO https://.../SHA256SUMS.txt
#   sha256sum -c SHA256SUMS.txt
#
# Stdlib-only: prefer `sha256sum` (Linux / Ubuntu runners) then fall back
# to `shasum -a 256` (macOS). python3 -m hashlib as last-resort fallback.
SHA_MANIFEST="$NPM_DIR/SHA256SUMS.txt"
if command -v sha256sum >/dev/null 2>&1; then
  HASH_LINE=$(cd "$NPM_DIR" && sha256sum "$TARBALL")
elif command -v shasum >/dev/null 2>&1; then
  HASH_LINE=$(cd "$NPM_DIR" && shasum -a 256 "$TARBALL")
else
  HASH_HEX=$(python3 -c "
import hashlib, sys
h = hashlib.sha256()
with open(sys.argv[1], 'rb') as f:
    for chunk in iter(lambda: f.read(65536), b''):
        h.update(chunk)
print(h.hexdigest())
" "$TARBALL_PATH")
  HASH_LINE="${HASH_HEX}  ${TARBALL}"
fi

# Normalise output to exactly two spaces between hash + filename (sha256sum
# -c strict format), strip any extra whitespace introduced by BSD shasum.
HASH_HEX="${HASH_LINE%% *}"
HASH_LINE="${HASH_HEX}  ${TARBALL}"

# Dedup-or-append (PLAN-023 Phase A F-comp-002 follow-up): replace any
# existing line for the same filename in-place, else append. Prevents
# SHA256SUMS.txt from accumulating stale entries across local rebuilds
# (previously observed: 51 stale entries before PLAN-025 Batch I reset).
# Preserves header comment lines (starting with #) untouched.
if [[ -f "$SHA_MANIFEST" ]] && grep -qE "  ${TARBALL}\$" "$SHA_MANIFEST" 2>/dev/null; then
  # Replace existing line for this filename.
  TMP_MANIFEST="$(mktemp -t ceo-sha-manifest.XXXXXX)"
  awk -v tb="$TARBALL" -v line="$HASH_LINE" '
    $0 ~ ("  " tb "$") { print line; found=1; next }
    { print }
    END { if (!found) print line }
  ' "$SHA_MANIFEST" > "$TMP_MANIFEST"
  mv "$TMP_MANIFEST" "$SHA_MANIFEST"
  echo "OK: sha256 = $HASH_HEX"
  echo "    updated $SHA_MANIFEST (replaced existing line)"
else
  echo "$HASH_LINE" >> "$SHA_MANIFEST"
  echo "OK: sha256 = $HASH_HEX"
  echo "    appended to $SHA_MANIFEST"
fi

# Remove any stale sidecar files for tarball names OTHER than the current
# one. Keeps the npm/ directory free of version-drift sidecars between
# RC→GA cuts (previously observed: 1.5.0-rc.1.tgz.sha256 lingered after
# 1.6.0-rc.1 bump). Glob over ceo-orchestration-*.tgz.sha256 pattern.
for stale in "$NPM_DIR"/ceo-orchestration-*.tgz.sha256; do
  [[ -f "$stale" ]] || continue
  stale_name="$(basename "$stale" .sha256)"
  if [[ "$stale_name" != "$TARBALL" ]]; then
    rm -f "$stale"
    echo "    pruned stale sidecar: $stale_name.sha256"
  fi
done

# Also emit a single-purpose .sha256 sidecar alongside the tarball so CI
# can download it separately without parsing the cumulative manifest.
echo "$HASH_HEX  $TARBALL" > "$TARBALL_PATH.sha256"
echo "    sidecar written $TARBALL_PATH.sha256"

# -------------------------------- smoke test (optional) ---------------------
if [[ $SMOKE -eq 1 ]]; then
  echo "==> Smoke-testing tarball"
  SMOKE_DIR="$(mktemp -d -t ceo-orch-smoke.XXXXXX)"
  trap 'if [[ $KEEP -eq 0 ]]; then rm -rf "$SMOKE_DIR"; fi' EXIT

  echo "    target dir: $SMOKE_DIR"

  # Initialize as a git repo (install.sh requires git for canonical-edit
  # sentinel detection + downstream dogfood checks).
  ( cd "$SMOKE_DIR" && git init -q && git config user.email smoke@local \
    && git config user.name smoke && touch .gitkeep && git add . \
    && git commit -q -m "smoke baseline" )

  # Install the local tarball into a scratch project (npm install reads
  # peer install.sh from the tarball and copies to .claude/).
  cd "$SMOKE_DIR"
  npm init -y >/dev/null 2>&1
  npm install --no-save "$TARBALL_PATH" 2>&1 | tail -3

  # Invoke shim → install.sh
  if ! npx ceo-orchestration "$SMOKE_DIR" --profile core 2>&1 | tail -10; then
    echo "::error::smoke test: ceo-orchestration exited non-zero" >&2
    exit 2
  fi

  # Verify install actually populated .claude/
  for required in .claude/hooks/_python-hook.sh .claude/skills .claude/scripts; do
    if [[ ! -e "$SMOKE_DIR/$required" ]]; then
      echo "::error::smoke test: $required missing post-install" >&2
      exit 2
    fi
  done

  echo "OK: smoke test passed — $SMOKE_DIR"
  if [[ $KEEP -eq 1 ]]; then
    echo "    (artifacts kept; rm -rf '$SMOKE_DIR' when done)"
  fi
fi

echo ""
echo "==> Done"
echo "    Tarball: $TARBALL_PATH"
echo "    Publish: handled by .github/workflows/npm-publish.yml on GA tag (NOT rc)"
echo "    Local install elsewhere: npm install --no-save '$TARBALL_PATH'"
