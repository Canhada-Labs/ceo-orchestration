#!/usr/bin/env bash
# =============================================================================
# publish-plugin.sh — regenerate the `ceo` plugin from the live framework and
# publish it to the private plugin-marketplace repo. Idempotent / re-runnable.
#
# WHY YOU run this (not the assistant): the Claude Code auto-mode classifier
# blocks an agent from bulk-pushing a materialized tree to a separate,
# agent-created repo (a generic data-exfiltration guard). Your own shell is
# outside that rail, and your `gh`/git auth is the authorization of record.
#
# Cycle: evolve the framework -> run this -> team runs `/plugin update`.
# The plugin is GENERATED from the live `.claude/`, never hand-edited; `dist/`
# stays gitignored so the build never pollutes or duplicates the framework.
#
# Config (env overrides, all optional):
#   CEO_MARKETPLACE_REPO   target repo      (default: <origin-owner>/ceo-marketplace)
#   CEO_PUBLISH_WORKDIR    scratch clone    (default: /tmp/ceo-marketplace-publish)
#   CEO_PUBLISH_AUTHOR_NAME / _AUTHOR_EMAIL  commit identity
#                          (default: git user.name + <owner>@users.noreply.github.com,
#                           noreply keeps the marketplace history clean for a public open)
# =============================================================================
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# Derive the GitHub owner from this repo's origin (no hard-coded handle).
OWNER="$(gh repo view --json owner -q .owner.login 2>/dev/null || true)"
[ -n "$OWNER" ] || OWNER="$(git remote get-url origin 2>/dev/null | sed -E 's#.*[:/]([^/]+)/[^/]+(\.git)?$#\1#' || true)"

# An explicit CEO_MARKETPLACE_REPO wins and does NOT require owner discovery — the
# script may run from a source archive with no gh auth and no origin (Codex P2).
if [ -n "${CEO_MARKETPLACE_REPO:-}" ]; then
  MARKETPLACE_REPO="$CEO_MARKETPLACE_REPO"
  [ -n "$OWNER" ] || OWNER="${MARKETPLACE_REPO%%/*}"   # derive fallback owner for the default author email
else
  [ -n "$OWNER" ] || { echo "!! could not determine GitHub owner (no gh auth / no origin) — set CEO_MARKETPLACE_REPO=<owner>/<repo>"; exit 1; }
  MARKETPLACE_REPO="${OWNER}/ceo-marketplace"
fi
WORK="${CEO_PUBLISH_WORKDIR:-/tmp/ceo-marketplace-publish}"
AUTHOR_NAME="${CEO_PUBLISH_AUTHOR_NAME:-$(git config user.name || echo "$OWNER")}"
AUTHOR_EMAIL="${CEO_PUBLISH_AUTHOR_EMAIL:-${OWNER}@users.noreply.github.com}"

echo "== publish-plugin =="
echo "  framework:   $REPO_ROOT"
echo "  marketplace: $MARKETPLACE_REPO"
echo "  workdir:     $WORK"

echo
echo "== 1) Build plugin from live .claude/ =="
python3 scripts/build-plugin.py
PLUGIN_SRC="$REPO_ROOT/dist/ceo-plugin"
MKT_SRC="$REPO_ROOT/dist/ceo-marketplace"
[ -d "$PLUGIN_SRC" ] || { echo "  !! build did not produce $PLUGIN_SRC"; exit 1; }
VERSION="$(python3 -c "import json,sys;print(json.load(open('$PLUGIN_SRC/.claude-plugin/plugin.json'))['version'])")"
echo "  plugin version: $VERSION"

echo
echo "== 2) Fresh working clone of the marketplace repo =="
# Safety guard (Codex P2): CEO_PUBLISH_WORKDIR is a documented override; never
# rm -rf a path that could be valuable (root, $HOME, the framework repo, or an
# unrelated checkout). Only a fresh path or our own prior marketplace clone is deletable.
WORK_ABS="$(cd "$WORK" 2>/dev/null && pwd || echo "$WORK")"
case "$WORK_ABS" in
  ""|"/"|"$HOME"|"$REPO_ROOT"|"$REPO_ROOT"/*)
    echo "  !! refusing rm -rf on CEO_PUBLISH_WORKDIR='$WORK_ABS' (protected path) — pick a dedicated scratch dir"; exit 1;;
esac
if [ -e "$WORK_ABS" ]; then
  if [ -d "$WORK_ABS/.git" ]; then
    _u="$(git -C "$WORK_ABS" remote get-url origin 2>/dev/null || true)"
    case "$_u" in
      *"$MARKETPLACE_REPO"*) : ;;   # our own prior clone — safe to refresh
      *) echo "  !! '$WORK_ABS' is a git checkout of '${_u:-unknown}', not $MARKETPLACE_REPO — refusing to delete"; exit 1;;
    esac
  elif [ -n "$(ls -A "$WORK_ABS" 2>/dev/null)" ]; then
    echo "  !! '$WORK_ABS' exists, is non-empty, and is not a marketplace clone — refusing to delete (set CEO_PUBLISH_WORKDIR to a fresh path)"; exit 1
  fi
fi
rm -rf "$WORK"
if gh repo view "$MARKETPLACE_REPO" >/dev/null 2>&1; then
  gh repo clone "$MARKETPLACE_REPO" "$WORK" -- -q
  EXISTS=1
  echo "  cloned existing $MARKETPLACE_REPO"
else
  mkdir -p "$WORK"
  git -C "$WORK" init -b main -q
  EXISTS=0
  echo "  repo does not exist yet — will create on push"
fi

echo
echo "== 3) Materialize content (plugin + marketplace.json + README + .gitignore) =="
rm -rf "$WORK/ceo-plugin" "$WORK/.claude-plugin"
mkdir -p "$WORK/.claude-plugin"
cp "$MKT_SRC/.claude-plugin/marketplace.json" "$WORK/.claude-plugin/marketplace.json"
cp -R "$PLUGIN_SRC" "$WORK/ceo-plugin"
# scrub build cruft (scoped to the plugin tree; never touches .git)
find "$WORK/ceo-plugin" -type d -name '__pycache__' -exec rm -rf {} + 2>/dev/null || true
find "$WORK/ceo-plugin" -type f \( -name '*.pyc' -o -name '*.pyo' -o -name '.DS_Store' \) -delete 2>/dev/null || true
# resolve install placeholders in the published plugin README (portable, via python)
python3 - "$WORK/ceo-plugin/README.md" "$MARKETPLACE_REPO" <<'PY'
import sys
path, repo = sys.argv[1], sys.argv[2]
t = open(path, encoding="utf-8").read()
t = t.replace("<owner>/<your-marketplace-repo>", repo).replace("ceo@<your-marketplace>", "ceo@ceo-marketplace")
open(path, "w", encoding="utf-8").write(t)
PY
# marketplace root README + .gitignore
MKT_NAME="$(basename "$MARKETPLACE_REPO")"
printf '# %s (private)\n\nClaude Code plugin marketplace hosting the **ceo** plugin (CEO Orchestration).\n\n## Install\n```\n/plugin marketplace add %s\n/plugin install ceo@ceo-marketplace\n```\n\nGenerated from ceo-orchestration via `scripts/publish-plugin.sh` — do not hand-edit `ceo-plugin/`.\n' "$MKT_NAME" "$MARKETPLACE_REPO" > "$WORK/README.md"
printf '__pycache__/\n*.pyc\n*.pyo\n.DS_Store\n' > "$WORK/.gitignore"

echo
echo "== 4) Cleanliness gate (no OWNER absolute path leaks into the artifact) =="
# Match the OWNER's REAL home + username paths (fixed strings), NOT the generic
# /Users//home/ token: legit runtime modules — notably _lib/replay_redact.py, which
# REDACTS personal paths — carry /Users/ and /home/ as regex patterns and must not
# false-positive. build-plugin.py already sanitizes the owner's own absolute path.
USER_NAME="$(id -un 2>/dev/null || whoami)"
GATE_PATTERNS=(-e "${HOME}/" -e "/Users/${USER_NAME}/" -e "/home/${USER_NAME}/")
HITS=$(grep -rIlF "${GATE_PATTERNS[@]}" "$WORK" --exclude-dir=.git 2>/dev/null | wc -l | tr -d ' ' || true)
echo "  owner-path hits ($USER_NAME): $HITS  (must be 0)"
[ "$HITS" = "0" ] || { echo "  !! owner absolute path present:"; grep -rIlF "${GATE_PATTERNS[@]}" "$WORK" --exclude-dir=.git; exit 1; }

echo
echo "== 5) Commit + push =="
git -C "$WORK" add -A
if [ "$EXISTS" = "1" ] && git -C "$WORK" diff --cached --quiet 2>/dev/null; then
  echo "  no changes vs published marketplace — nothing to publish."
  exit 0
fi
git -C "$WORK" -c user.name="$AUTHOR_NAME" -c user.email="$AUTHOR_EMAIL" \
  commit -q -m "Publish ceo plugin v$VERSION (generated from ceo-orchestration)"
if [ "$EXISTS" = "1" ]; then
  git -C "$WORK" push origin main
else
  gh repo create "$MARKETPLACE_REPO" --private --source="$WORK" --remote=origin --push \
    --description "Private Claude Code plugin marketplace — ceo (CEO Orchestration)"
fi

echo
echo "== Done — ceo v$VERSION published to $MARKETPLACE_REPO =="
echo "  First time:  /plugin marketplace add $MARKETPLACE_REPO  &&  /plugin install ceo@ceo-marketplace"
echo "  Updates:     /plugin update   (run by each team member in their Claude Code)"
