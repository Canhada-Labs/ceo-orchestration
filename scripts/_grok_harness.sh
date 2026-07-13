#!/usr/bin/env bash
# _grok_harness.sh — xAI Grok Build harness emission for install.sh / upgrade.sh
# =============================================================================
# PLAN-156 Wave 4 (SENT-GK-C). Single source of truth for the `--harness grok`
# path. Unlike the codex harness, it EMITS NO live-hook registration file: the
# grok rail is armed through the legacy-compat `.claude/settings.json` that the
# framework already ships (OQ1, INVERTED by evidence — see below). This file
# emits the grok OPERATOR surface (`AGENTS.md`, `.grok/config.toml.example`,
# `.grok/sandbox.toml.example`, the pre-push gate), records a lifecycle
# manifest, and runs the post-install arming check. install.sh and upgrade.sh
# both `source` this file, so the grok logic lives in exactly one place.
#
# NEW unguarded companion (rides the SENT-GK-C commit; not canonical-guarded).
# Sourced, never executed. Stdlib shell only; bash >= 3.2. shellcheck -S
# warning clean.
#
# HONESTY (binding, PLAN-156 capability matrix):
#   * NOTHING is enforced until the project folder is TRUSTED (/hooks-trust or
#     --trust). Until then project hooks are a SILENT no-op. The arming check
#     says this loudly and is the installer's FINAL instruction.
#   * Hooks FAIL OPEN on grok: a crash, a 5s timeout, malformed stdout, or an
#     unrecognized decision word all let the tool call proceed. Only a
#     well-formed {"decision":"deny"} blocks.
#   * WHY NO .grok/hooks/: arming both native `.grok/hooks/` and the legacy
#     `.claude/settings.json` makes grok 0.2.93 fire every hook TWICE on the
#     same tool call, and neither documented kill switch stops it at runtime
#     (S269 probes P8/P8b/P8c). Single-surface is the only sound resolution;
#     the framework arms the legacy surface it already ships and GUARDS
#     `.grok/hooks/**` so nothing re-creates the second one.
#   * No speed claim anywhere. The value is governance + auditability.
#
# ENV CONTRACT (set by the caller BEFORE sourcing/calling):
#   Required : TARGET (abs), SOURCE_DIR (abs framework checkout), DRY_RUN (0|1)
#   Rendered : PH_PROJECT_PATH (abs target path), PH_PROJECT_NAME
#   Options  : GROK_FORCE (0|1)
#   Optional : a caller-defined `grok_journal <op> <detail>` recorder
#              (maps to install.sh:_state_record_op / upgrade.sh:_up_record_op);
#              a no-op default is provided below if the caller defines none.
# =============================================================================

# Fail-open recorder default (overridden by the caller if it has a journal).
if ! command -v grok_journal >/dev/null 2>&1; then
  grok_journal() { return 0; }
fi

# ---------------------------------------------------------------------------
# Version pin — grok ships an EXACT-version pin (0.x daily cadence makes a
# range meaningless). Read the exact version from
# .claude/governance/grok-cli-pin.txt (last non-comment, non-blank line).
# ---------------------------------------------------------------------------
GROK_VERIFIED_VERSION="0.2.93"   # the pin PLAN-156 fixtures were recorded on

_grok_pin_version() {
  local pin_file="$SOURCE_DIR/.claude/governance/grok-cli-pin.txt"
  local line=""
  if [[ -f "$pin_file" ]]; then
    line="$(grep -vE '^[[:space:]]*(#|$)' "$pin_file" 2>/dev/null | tail -n 1 | tr -d '[:space:]')"
  fi
  if [[ -n "$line" ]]; then
    printf '%s\n' "$line"
  else
    printf '%s\n' "$GROK_VERIFIED_VERSION"
  fi
}

_grok_pin_sha() {
  local sha_file="$SOURCE_DIR/.claude/governance/grok-cli-binary-sha256.txt"
  local line=""
  if [[ -f "$sha_file" ]]; then
    line="$(grep -vE '^[[:space:]]*(#|$)' "$sha_file" 2>/dev/null | tail -n 1 | tr -d '[:space:]')"
  fi
  printf '%s\n' "$line"
}

# `grok --version` -> bare "X.Y.Z" (or empty if the binary is absent/opaque).
_grok_detect_version() {
  command -v grok >/dev/null 2>&1 || return 0
  local raw=""
  raw="$(grok --version 2>/dev/null | head -n 1 || true)"
  printf '%s\n' "$raw" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -n 1
}

# SHA-256 of the resolved grok binary (following the ~/.grok/bin symlink),
# or empty if grok is absent / no hasher is available.
_grok_detect_sha() {
  local bin=""
  bin="$(command -v grok 2>/dev/null || true)"
  [[ -n "$bin" ]] || return 0
  # Resolve symlinks (macOS has no readlink -f; try python fallback).
  local real=""
  real="$(readlink -f "$bin" 2>/dev/null || true)"
  if [[ -z "$real" ]] && command -v python3 >/dev/null 2>&1; then
    real="$(python3 -c 'import os,sys;print(os.path.realpath(sys.argv[1]))' "$bin" 2>/dev/null || true)"
  fi
  [[ -n "$real" ]] || real="$bin"
  if command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$real" 2>/dev/null | awk '{print $1}'
  elif command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$real" 2>/dev/null | awk '{print $1}'
  fi
}

GROK_MANIFEST_REL=".grok/.ceo-harness-manifest"

# ---------------------------------------------------------------------------
# Render a template file with {{PROJECT_PATH}}/{{PROJECT_NAME}} substitution.
# Collision policy mirrors the codex harness (idempotent skip / refuse-without
# -force / backup-on-force).
# ---------------------------------------------------------------------------
_grok_render_to_stdout() {
  local src="$1"
  sed \
    -e "s|{{PROJECT_PATH}}|${PH_PROJECT_PATH:-$TARGET}|g" \
    -e "s|{{PROJECT_NAME}}|${PH_PROJECT_NAME:-your-app}|g" \
    "$src"
}

_GROK_MANIFEST_EMITS=""
_GROK_MANIFEST_BACKUPS=""
_GROK_REFUSED=0

_grok_emit_file() {
  local src_rel="$1" dst_rel="$2"
  local src="$SOURCE_DIR/$src_rel" dst="$TARGET/$dst_rel"
  [[ -f "$src" ]] || { echo "::error::grok template missing: $src_rel" >&2; return 1; }
  local dst_dir; dst_dir="$(dirname "$dst")"
  if [[ "$DRY_RUN" -eq 1 ]]; then
    if [[ -e "$dst" ]]; then
      echo "    (dry-run) EXISTS (skip-or-refuse): $dst_rel"
    else
      echo "    (dry-run) would CREATE: $dst_rel"
    fi
    return 0
  fi
  mkdir -p "$dst_dir"
  local tmp; tmp="$(mktemp "${TMPDIR:-/tmp}/ceo-grok.XXXXXX")"
  _grok_render_to_stdout "$src" > "$tmp"
  if [[ -e "$dst" ]]; then
    if diff -q "$dst" "$tmp" >/dev/null 2>&1; then
      echo "    EXISTS identical (skipping): $dst_rel"
      rm -f "$tmp"; return 0
    fi
    if [[ "${GROK_FORCE:-0}" -ne 1 ]]; then
      echo "::error::refusing to overwrite pre-existing $dst_rel (pass --force)" >&2
      diff -u "$dst" "$tmp" 2>/dev/null | head -40 >&2 || true
      rm -f "$tmp"; _GROK_REFUSED=1; return 0
    fi
    local ts bak; ts="$(date +%Y%m%d-%H%M%S)"; bak="${dst_rel##*/}.ceo-bak-${ts}"
    cp "$dst" "$dst_dir/$bak"
    _GROK_MANIFEST_BACKUPS="${_GROK_MANIFEST_BACKUPS}${dst_rel}	${dst_rel%/*}/${bak}"$'\n'
    echo "    BACKED UP: $dst_rel -> $bak (--force)"
  fi
  mv -f "$tmp" "$dst"
  # Preserve executability for scripts (pair-rail S269 P1 #3): the render goes
  # through a 0600 mktemp, so a git hook / .sh emitted this way lands
  # NON-executable and git silently refuses to run it — disarming the pre-push
  # gate (the grok pair-rail's teeth). Restore +x for shell scripts and
  # anything under a hooks dir.
  case "$dst_rel" in
    *.sh|.git/hooks/*|*/hooks/*) chmod +x "$dst" 2>/dev/null || true ;;
  esac
  echo "    EMITTED: $dst_rel"
  _GROK_MANIFEST_EMITS="${_GROK_MANIFEST_EMITS}${dst_rel}"$'\n'
  grok_journal "grok_emit" "$dst_rel"
}

# The template-backed emit set (src_rel<TAB>dst_rel). NOTE: no hooks.json —
# the legacy `.claude/settings.json` is the single armed surface (OQ1).
_grok_planned_pairs() {
  printf '%s\t%s\n' "templates/grok/AGENTS.md"                "AGENTS.md"
  printf '%s\t%s\n' "templates/grok/config.toml.example"      ".grok/config.toml.example"
  printf '%s\t%s\n' "templates/grok/sandbox.toml.example"     ".grok/sandbox.toml.example"
  printf '%s\t%s\n' "templates/grok/pre-push-review-gate.sh"  ".git/hooks/pre-push-grok-review"
}

# ---------------------------------------------------------------------------
# grok_emit_bundle — the top-level grok install action. Mirrors the codex
# bundle: atomic collision pre-flight, then emit. Returns non-zero on hard
# error (1) or refused collision (2).
# ---------------------------------------------------------------------------
grok_emit_bundle() {
  echo ""
  echo "==> Grok harness (--harness grok) — emitting operator surface"
  echo "    Verified against grok $GROK_VERIFIED_VERSION (pin: $(_grok_pin_version))."
  echo "    HONESTY: rails are armed through the legacy .claude/settings.json"
  echo "             (grok reads it as Claude-compat). There is NO .grok/hooks/"
  echo "             on purpose — arming both surfaces double-fires every hook"
  echo "             on 0.2.93 and no kill switch stops it (PLAN-156 W0a P8)."
  echo "    HONESTY: NOTHING is enforced until the folder is TRUSTED, and hooks"
  echo "             FAIL OPEN (crash/timeout/malformed = the tool call runs)."

  _GROK_REFUSED=0
  _GROK_MANIFEST_EMITS=""
  _GROK_MANIFEST_BACKUPS=""

  # Atomic collision pre-flight — refuse the whole bundle before ANY write.
  local src_rel dst_rel src dst tmp refused=0
  while IFS=$'\t' read -r src_rel dst_rel; do
    [[ -n "$src_rel" ]] || continue
    src="$SOURCE_DIR/$src_rel"; dst="$TARGET/$dst_rel"
    [[ -f "$src" ]] || continue
    [[ -e "$dst" ]] || continue
    tmp="$(mktemp "${TMPDIR:-/tmp}/ceo-grok-pf.XXXXXX" 2>/dev/null || true)"
    [[ -n "$tmp" ]] || continue
    _grok_render_to_stdout "$src" > "$tmp" 2>/dev/null
    if ! diff -q "$dst" "$tmp" >/dev/null 2>&1 && [[ "${GROK_FORCE:-0}" -ne 1 ]]; then
      refused=1
      echo "::error::refusing to overwrite pre-existing $dst_rel (pass --force)" >&2
      diff -u "$dst" "$tmp" 2>/dev/null | head -40 >&2 || true
    fi
    rm -f "$tmp" 2>/dev/null || true
  done <<EOF
$(_grok_planned_pairs)
EOF
  if [[ "$refused" -eq 1 ]]; then
    echo "::error::grok bundle refused to overwrite pre-existing file(s); no files written." >&2
    return 2
  fi

  _grok_emit_file "templates/grok/AGENTS.md"               "AGENTS.md"                      || return 1
  _grok_emit_file "templates/grok/config.toml.example"     ".grok/config.toml.example"      || return 1
  _grok_emit_file "templates/grok/sandbox.toml.example"    ".grok/sandbox.toml.example"     || return 1
  # The pre-push gate is THE teeth (Stop is advisory on grok). Emitted to a
  # staging path; the operator wires it as `.git/hooks/pre-push` (or chains it)
  # per the trust-flow guidance below — we never silently overwrite an
  # existing pre-push hook.
  _grok_emit_file "templates/grok/pre-push-review-gate.sh" ".git/hooks/pre-push-grok-review" || return 1

  _grok_write_manifest
  _grok_print_reviewer_inversion
  _grok_print_trust_flow
  return 0
}

_grok_write_manifest() {
  [[ "$DRY_RUN" -eq 1 ]] && return 0
  local dst="$TARGET/$GROK_MANIFEST_REL" ver
  mkdir -p "$(dirname "$dst")"
  ver="$(_grok_detect_version)"
  {
    echo "# ceo-orchestration grok harness manifest (PLAN-156 Wave 4)."
    echo "# TAB-separated: kind<TAB>relpath[<TAB>backup-relpath]; kind in {meta,emit,backup}."
    echo "# uninstall removes 'emit' relpaths (LIFO) and restores 'backup' pairs."
    printf 'meta\tgrok_cli_version\t%s\n' "${ver:-unknown}"
    printf 'meta\tpin_version\t%s\n' "$(_grok_pin_version)"
    printf '%s' "$_GROK_MANIFEST_EMITS" | awk 'NF && !seen[$0]++ {printf "emit\t%s\n", $0}'
    printf '%s' "$_GROK_MANIFEST_BACKUPS" | awk -F'\t' 'NF>=2 {printf "backup\t%s\t%s\n", $1, $2}'
  } > "$dst"
  grok_journal "grok_emit" "$GROK_MANIFEST_REL"
}

_grok_print_reviewer_inversion() {
  echo ""
  echo "==> Inverted pair-rail (Grok operates, Claude reviews)"
  echo "    Stop is NON-blocking on grok, so the Stop-review gate is ADVISORY."
  echo "    The TEETH are the git pre-push gate emitted above. Wire it:"
  echo "        ln -sf ../../.git/hooks/pre-push-grok-review .git/hooks/pre-push"
  echo "      (or chain it from an existing pre-push hook)."
  echo "    Reviewer CLI is \`claude -p\` (override model with CEO_REVIEWER_MODEL,"
  echo "    OQ3). Same-vendor caveat is direction-neutral (author=xAI,"
  echo "    reviewer=Anthropic — no single model is both author and sole reviewer)."
  grok_journal "grok_reviewer_inverted" "reviewer_cli=claude"
}

_grok_print_trust_flow() {
  echo ""
  echo "==> Trust + arming (consent-first — the installer trusts NOTHING for you)"
  echo "    1. Trust the folder (unifies MCP+LSP+hooks):  cd $TARGET && grok --trust"
  echo "       (or run \`grok\`, then \`/hooks-trust\`)."
  echo "    2. Confirm the rails loaded:  grok inspect | sed -n '/Hooks/,/Config/p'"
  echo "       — the CEO hooks should list with NO [disabled] tag."
  echo "    3. Re-run the arming check:  scripts/install.sh --harness grok --arming-check $TARGET"
}

# ---------------------------------------------------------------------------
# grok_arming_check — the post-install doctor. Prints exactly one verdict:
# ARMED / NOT-ARMED-(untrusted) / BROKEN. Refuse-on-drift (debate C11 / Sec
# R-SEC7): a version OR binary-SHA mismatch is BROKEN — refuse to certify
# governance against an uncharacterized binary. Returns:
#   0 = ARMED, 1 = NOT-ARMED-(untrusted), 2 = BROKEN.
# ---------------------------------------------------------------------------
grok_arming_check() {
  local target="${1:-$TARGET}"
  local broken=0 reasons=""
  echo ""
  echo "==> Post-install arming check (grok harness) — is enforcement live?"

  # (a) required files present — the shim + the legacy settings surface.
  local settings="$target/.claude/settings.json"
  local shim="$target/.claude/hooks/_python-hook.sh"
  if [[ ! -f "$settings" ]]; then
    broken=1; reasons="${reasons}  - MISSING: .claude/settings.json (the armed grok surface — install the framework)"$'\n'
  fi
  if [[ ! -f "$shim" ]]; then
    broken=1; reasons="${reasons}  - MISSING: .claude/hooks/_python-hook.sh (framework hooks not installed)"$'\n'
  elif [[ ! -x "$shim" ]]; then
    broken=1; reasons="${reasons}  - NOT EXECUTABLE: .claude/hooks/_python-hook.sh (chmod +x)"$'\n'
  fi

  # (b) DOUBLE-FIRE guard: a live .grok/hooks/*.json ALONGSIDE the legacy
  # surface re-opens the double-fire this integration exists to avoid.
  if compgen -G "$target/.grok/hooks/*.json" >/dev/null 2>&1; then
    broken=1
    reasons="${reasons}  - DOUBLE-FIRE RISK: $target/.grok/hooks/*.json exists. Arming both the"$'\n'
    reasons="${reasons}    native surface and the legacy .claude/settings.json fires every hook"$'\n'
    reasons="${reasons}    TWICE on grok 0.2.93 (HMAC double-count). Remove it — the framework"$'\n'
    reasons="${reasons}    arms ONLY the legacy surface (PLAN-156 W0a probe P8)."$'\n'
  fi

  # (c) refuse-on-drift: version AND binary SHA must match the pin.
  local ver pin_ver sha pin_sha
  ver="$(_grok_detect_version)"; pin_ver="$(_grok_pin_version)"
  sha="$(_grok_detect_sha)"; pin_sha="$(_grok_pin_sha)"
  if [[ -z "$ver" ]]; then
    reasons="${reasons}  - grok not on PATH: cannot verify the binary or its version"$'\n'
  elif [[ "$ver" != "$pin_ver" ]]; then
    broken=1
    reasons="${reasons}  - VERSION DRIFT: grok $ver != pinned $pin_ver. Governance was certified"$'\n'
    reasons="${reasons}    on $pin_ver; refusing to arm against an uncharacterized binary. Re-run the"$'\n'
    reasons="${reasons}    Wave-0 characterization probes and bump the pin under a sentinel (ADR-162)."$'\n'
  fi
  if [[ -n "$sha" && -n "$pin_sha" && "$sha" != "$pin_sha" ]]; then
    broken=1
    reasons="${reasons}  - BINARY SHA DRIFT: grok binary sha256 does not match the pin"$'\n'
    reasons="${reasons}    (grok-cli-binary-sha256.txt). This is the real supply-chain gate for a"$'\n'
    reasons="${reasons}    proprietary rolling 0.x — refusing to arm. Verify the upgrade + re-pin."$'\n'
  fi

  # (d) folder trust (best-effort positive check; NEVER assume trusted).
  local trusted=0
  local grok_home="${GROK_HOME:-$HOME/.grok}"
  local tf="$grok_home/trusted_folders.toml"
  if [[ -f "$tf" ]] && grep -qF "$target" "$tf" 2>/dev/null; then
    trusted=1
  fi

  echo ""
  if [[ "$broken" -eq 1 ]]; then
    echo "    VERDICT: BROKEN"
    printf '%s' "$reasons" >&2
    echo "    Enforcement is NOT live (or not trustworthy). Fix the above, then re-run." >&2
    return 2
  fi
  if [[ -n "$reasons" ]]; then
    printf '%s' "$reasons" >&2
  fi
  if [[ "$trusted" -eq 1 ]]; then
    echo "    VERDICT: ARMED (folder trusted in $tf)"
    echo "    REMINDER: hooks FAIL OPEN on grok. A crash / 5s timeout / malformed"
    echo "    output all let the tool call proceed — the pin + substrate-watch keep"
    echo "    the characterized surface honest. Re-verify after every grok update."
    return 0
  fi
  echo "    VERDICT: NOT-ARMED-(untrusted)"
  echo "    NOTHING is enforced until you trust the folder. To arm:"
  echo "      1. cd $target && grok --trust   (or run \`grok\`, then \`/hooks-trust\`)"
  echo "      2. Confirm:  grok inspect | sed -n '/Hooks/,/Config/p'   (no [disabled])"
  echo "      3. Re-run:   scripts/install.sh --harness grok --arming-check $target"
  return 1
}

# ---------------------------------------------------------------------------
# grok_uninstall — manifest-driven removal of the grok operator surface
# (pair-rail S269 P2 #5 — lifecycle symmetry with codex_uninstall). Restores
# --force backups first, then removes emitted paths (skipping any a backup
# just restored). The single armed rail (`.claude/settings.json`) is framework
# state, NOT grok-emitted, so it is deliberately left untouched here — the main
# `scripts/uninstall.sh` owns the framework manifest.
# ---------------------------------------------------------------------------
grok_uninstall() {
  local target="${1:-$TARGET}"
  local manifest="$target/$GROK_MANIFEST_REL"
  echo ""
  echo "==> Grok harness uninstall (manifest-driven)"
  if [[ ! -f "$manifest" ]]; then
    echo "::error::no grok harness manifest at $GROK_MANIFEST_REL — nothing to uninstall" >&2
    return 1
  fi

  # Restore backups FIRST (so a --force-replaced file returns), then remove emits.
  local kind rel bak
  while IFS=$'\t' read -r kind rel bak; do
    [[ "$kind" == "backup" ]] || continue
    if [[ -n "$rel" && -f "$target/$bak" ]]; then
      if [[ "$DRY_RUN" -eq 1 ]]; then
        echo "    (dry-run) would RESTORE: $bak -> $rel"
      else
        cp "$target/$bak" "$target/$rel"
        rm -f "$target/$bak"
        echo "    RESTORED: $rel (from $bak)"
      fi
    fi
  done < "$manifest"

  local restored=""
  restored="$(grep -E '^backup	' "$manifest" 2>/dev/null | cut -f2 || true)"
  while IFS=$'\t' read -r kind rel _; do
    [[ "$kind" == "emit" ]] || continue
    [[ -n "$rel" ]] || continue
    if printf '%s\n' "$restored" | grep -Fxq "$rel"; then
      continue
    fi
    if [[ "$DRY_RUN" -eq 1 ]]; then
      echo "    (dry-run) would REMOVE: $rel"
    else
      rm -f "$target/$rel" 2>/dev/null || true
      echo "    REMOVED: $rel"
    fi
  done < "$manifest"

  if [[ "$DRY_RUN" -eq 0 ]]; then
    rm -f "$manifest" 2>/dev/null || true
    rmdir "$target/.grok" 2>/dev/null || true
    echo "    Uninstall complete. NOTE: the armed rail is the framework's own"
    echo "    .claude/settings.json (NOT grok-emitted) — it is untouched here;"
    echo "    use scripts/uninstall.sh to remove the framework itself."
  fi
  return 0
}
