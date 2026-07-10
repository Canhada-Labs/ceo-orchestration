#!/usr/bin/env bash
# _codex_harness.sh — Codex (OpenAI) harness emission for install.sh / upgrade.sh
# =============================================================================
# PLAN-155 Wave 5 (SENT-CX-C). Single source of truth for the `--harness codex`
# path: it EMITS the `.codex/` registration bundle, the operator `AGENTS.md`,
# the optional managed `requirements.toml`, the inverted-pair-rail reviewer
# guidance, records a lifecycle manifest, and runs the post-install arming
# check. install.sh and upgrade.sh both `source` this file (like _hash_lib.sh),
# so the codex logic lives in exactly one place.
#
# NEW unguarded companion (rides the SENT-CX-C commit; not canonical-guarded).
# Sourced, never executed. Stdlib shell only; bash >= 3.2 (no associative
# arrays / mapfile). shellcheck -S warning clean.
#
# HONESTY (binding, PLAN-155 capability matrix):
#   * NOTHING is enforced until the operator grants /hooks trust. On codex
#     0.139 an untrusted or modified hook is a SILENT no-op. The arming check
#     says this loudly and is printed as the installer's FINAL instruction.
#   * Kill-switch surface protection is ABSENT until PLAN-155 Wave 3b lands.
#   * No speed claim anywhere. The value is governance + auditability.
#
# ENV CONTRACT (set by the caller BEFORE sourcing/calling):
#   Required : TARGET (abs), SOURCE_DIR (abs framework checkout), DRY_RUN (0|1)
#   Rendered : PH_PROJECT_PATH (abs target path), PH_PROJECT_NAME
#   Options  : CODEX_MANAGED_HOOKS (0|1), CODEX_WITH_SKILLS (0|1),
#              CODEX_FORCE (0|1)
#   Optional : a caller-defined `codex_journal <op> <detail>` recorder
#              (maps to install.sh:_state_record_op / upgrade.sh:_up_record_op);
#              a no-op default is provided below if the caller defines none.
#
# The kill-switch / template contents are authored in Waves 2/3
# (templates/codex/**) and guarded in Wave 3b — this file only COPIES +
# substitutes them; it never inlines their bytes.
# =============================================================================

# Fail-open recorder default (overridden by the caller if it has a journal).
if ! command -v codex_journal >/dev/null 2>&1; then
  codex_journal() { return 0; }
fi

# ---------------------------------------------------------------------------
# Version pin (debate A15). Read the semver range shipped in the framework at
# .claude/governance/codex-cli-pin.txt (last non-comment, non-blank line);
# fall back to the PLAN-142-verified range if that file is absent.
# ---------------------------------------------------------------------------
CODEX_VERIFIED_VERSION="0.139.0"   # the pin PLAN-155 fixtures were recorded on

_codex_pin_range() {
  local pin_file="$SOURCE_DIR/.claude/governance/codex-cli-pin.txt"
  local line=""
  if [[ -f "$pin_file" ]]; then
    # last line that is neither blank nor a comment
    line="$(grep -vE '^[[:space:]]*(#|$)' "$pin_file" 2>/dev/null | tail -n 1 | tr -d '[:space:]')"
  fi
  if [[ -n "$line" ]]; then
    printf '%s\n' "$line"
  else
    printf '%s\n' ">=0.128.0,<0.140.0"
  fi
}

# `codex --version` -> bare "X.Y.Z" (or empty if the binary is absent/opaque).
_codex_detect_version() {
  command -v codex >/dev/null 2>&1 || return 0
  local raw=""
  raw="$(codex --version 2>/dev/null | head -n 1 || true)"
  # Extract the first dotted-number token.
  printf '%s\n' "$raw" | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -n 1
}

# $1 >= $2 (semver, via sort -V). Returns 0 (true) / 1 (false).
_codex_ver_ge() {
  [ "$(printf '%s\n%s\n' "$2" "$1" | sort -V 2>/dev/null | head -n 1)" = "$2" ]
}

# Is $1 inside the range ">=MIN,<MAX"? Best-effort; unknown grammar => "in".
_codex_ver_in_range() {
  local ver="$1" range="$2" min="" max=""
  [[ -n "$ver" ]] || return 1
  min="$(printf '%s\n' "$range" | grep -oE '>=[0-9]+\.[0-9]+\.[0-9]+' | head -n1 | sed 's/^>=//')"
  max="$(printf '%s\n' "$range" | grep -oE '<[0-9]+\.[0-9]+\.[0-9]+'  | head -n1 | sed 's/^<//')"
  if [[ -n "$min" ]] && ! _codex_ver_ge "$ver" "$min"; then return 1; fi
  # max is exclusive: ver < max  <=>  NOT (ver >= max)
  if [[ -n "$max" ]] && _codex_ver_ge "$ver" "$max"; then return 1; fi
  return 0
}

# Codex 0.139 discovers ZERO hooks inside a git WORKTREE (`.git` is a FILE
# pointing at the parent). Enforcement is silently absent there — the arming
# check must flag it loudly (live-fire finding, MANIFEST-A open issue #2).
_codex_is_git_worktree() {
  local dir="$1"
  [[ -f "$dir/.git" ]]
}

CODEX_MANIFEST_REL=".codex/.ceo-harness-manifest"

# ---------------------------------------------------------------------------
# Render a template file: substitute {{PROJECT_PATH}} and {{PROJECT_NAME}} into
# $dst. Collision policy (debate A10):
#   - dst missing            => write (record emit)
#   - dst == rendered bytes  => SKIP (idempotent re-run, no error)
#   - dst differs, no --force=> REFUSE: print a unified diff, set the refusal
#                               flag; NEVER clobber
#   - dst differs, --force   => back up dst to <dst>.ceo-bak-<ts>, write,
#                               record both backup + emit
# Uses only literal string replacement (no sed metachar hazards): python3 when
# present, else a portable awk fallback.
# ---------------------------------------------------------------------------
_CODEX_REFUSED=0          # set to 1 by any refused collision this run
_CODEX_MANIFEST_EMITS=""  # newline list: relpath
_CODEX_MANIFEST_BACKUPS="" # newline list: relpath<TAB>backup-relpath

_codex_render_to_stdout() {
  local src="$1"
  if command -v python3 >/dev/null 2>&1; then
    PYTHONNOUSERSITE=1 python3 -I -c '
import sys
src, pp, pn = sys.argv[1], sys.argv[2], sys.argv[3]
with open(src, "r", encoding="utf-8") as f:
    data = f.read()
data = data.replace("{{PROJECT_PATH}}", pp).replace("{{PROJECT_NAME}}", pn)
sys.stdout.write(data)
' "$src" "$PH_PROJECT_PATH" "$PH_PROJECT_NAME"
  else
    # awk fallback: literal, index-based replacement (no regex).
    awk -v pp="$PH_PROJECT_PATH" -v pn="$PH_PROJECT_NAME" '
      function repl(s, needle, val,   out, i) {
        out = ""
        while ((i = index(s, needle)) > 0) {
          out = out substr(s, 1, i - 1) val
          s = substr(s, i + length(needle))
        }
        return out s
      }
      { line = repl($0, "{{PROJECT_PATH}}", pp); line = repl(line, "{{PROJECT_NAME}}", pn); print line }
    ' "$src"
  fi
}

_codex_emit_file() {
  local src_rel="$1" dst_rel="$2"
  local src="$SOURCE_DIR/$src_rel"
  local dst="$TARGET/$dst_rel"

  if [[ ! -f "$src" ]]; then
    echo "    SKIP (template missing): $src_rel" >&2
    return 0
  fi

  # Render to a temp so we can compare + reuse.
  local tmp=""
  tmp="$(mktemp "${TMPDIR:-/tmp}/ceo-codex-render.XXXXXX" 2>/dev/null || true)"
  if [[ -z "$tmp" ]]; then
    echo "    ERROR: cannot allocate tempfile for $dst_rel" >&2
    return 1
  fi
  _codex_render_to_stdout "$src" > "$tmp" 2>/dev/null

  if [[ "$DRY_RUN" -eq 1 ]]; then
    if [[ -e "$dst" ]]; then
      if diff -q "$dst" "$tmp" >/dev/null 2>&1; then
        echo "    (dry-run) EXISTS identical (would skip): $dst_rel"
      elif [[ "${CODEX_FORCE:-0}" -eq 1 ]]; then
        echo "    (dry-run) DIFFERS (would --force backup+overwrite): $dst_rel"
      else
        echo "    (dry-run) DIFFERS (would REFUSE — pass --force to overwrite): $dst_rel"
      fi
    else
      echo "    (dry-run) would CREATE: $dst_rel"
    fi
    rm -f "$tmp" 2>/dev/null || true
    return 0
  fi

  mkdir -p "$( dirname "$dst" )"

  if [[ -e "$dst" ]]; then
    if diff -q "$dst" "$tmp" >/dev/null 2>&1; then
      echo "    EXISTS identical (skipping): $dst_rel"
      _CODEX_MANIFEST_EMITS="${_CODEX_MANIFEST_EMITS}${dst_rel}"$'\n'
      rm -f "$tmp" 2>/dev/null || true
      return 0
    fi
    if [[ "${CODEX_FORCE:-0}" -ne 1 ]]; then
      echo "::error::refusing to overwrite pre-existing $dst_rel (pass --force to override)" >&2
      echo "    --- current (on disk) vs would-install (diff) ---" >&2
      diff -u "$dst" "$tmp" 2>/dev/null | head -40 >&2 || true
      _CODEX_REFUSED=1
      rm -f "$tmp" 2>/dev/null || true
      return 0
    fi
    # --force: back up, then overwrite.
    local ts bak
    ts="$(date +%Y%m%d-%H%M%S)"
    bak="${dst_rel}.ceo-bak-${ts}"
    cp "$dst" "$TARGET/$bak"
    _CODEX_MANIFEST_BACKUPS="${_CODEX_MANIFEST_BACKUPS}${dst_rel}	${bak}"$'\n'
    echo "    BACKED UP: $dst_rel -> $bak (--force)"
  fi

  cp "$tmp" "$dst"
  rm -f "$tmp" 2>/dev/null || true
  echo "    EMITTED: $dst_rel"
  _CODEX_MANIFEST_EMITS="${_CODEX_MANIFEST_EMITS}${dst_rel}"$'\n'
  codex_journal "codex_emit" "$dst_rel"
  return 0
}

# Write the lifecycle manifest (schema ceo.codex-harness/v1). Carries forward
# prior backup lines so a later run never loses a restore target. Wave 6's
# `.git/` pre-push hook APPENDS its emit line to this same ledger, so uninstall
# reaches it (debate A9 — the third install surface).
_codex_write_manifest() {
  [[ "$DRY_RUN" -eq 0 ]] || return 0
  local manifest="$TARGET/$CODEX_MANIFEST_REL"
  local ver range prior_backups=""
  ver="$(_codex_detect_version)"
  range="$(_codex_pin_range)"
  # Preserve any backup lines already recorded by an earlier run.
  if [[ -f "$manifest" ]]; then
    prior_backups="$(grep -E '^backup	' "$manifest" 2>/dev/null || true)"
  fi
  mkdir -p "$( dirname "$manifest" )"
  {
    echo "# ceo-orchestration codex harness install manifest (schema ceo.codex-harness/v1)"
    echo "# TAB-separated: kind<TAB>relpath[<TAB>backup-relpath]; kind in {meta,emit,backup}."
    echo "# uninstall removes 'emit' relpaths (LIFO) and restores 'backup' pairs."
    printf 'meta\tcodex_cli_version\t%s\n' "${ver:-unknown}"
    printf 'meta\tpin_range\t%s\n' "$range"
    printf 'meta\tmanaged_hooks\t%s\n' "${CODEX_MANAGED_HOOKS:-0}"
    # emit lines (unique, in emission order)
    printf '%s' "$_CODEX_MANIFEST_EMITS" | awk 'NF && !seen[$0]++ {printf "emit\t%s\n", $0}'
    # backup lines: prior + this run
    [[ -n "$prior_backups" ]] && printf '%s\n' "$prior_backups"
    printf '%s' "$_CODEX_MANIFEST_BACKUPS" | awk -F'\t' 'NF>=2 {printf "backup\t%s\t%s\n", $1, $2}'
  } > "$manifest"
  echo "    WROTE: $CODEX_MANIFEST_REL (lifecycle ledger — uninstall/backup source of truth)"
  codex_journal "codex_write_manifest" "$CODEX_MANIFEST_REL"
}

# The template-backed emit set (src_rel<TAB>dst_rel). requirements.toml is
# generated inline (not from a template) and handled separately.
_codex_planned_pairs() {
  printf 'templates/codex/hooks.json\t.codex/hooks.json\n'
  printf 'templates/codex/rules/ceo.rules\t.codex/rules/ceo.rules\n'
  printf 'templates/codex/AGENTS.md\tAGENTS.md\n'
}

# Pre-flight collision scan (debate A10): render every planned file, compare to
# any existing target file, and REFUSE the whole bundle (zero writes) if any
# differs without --force. Atomic: a refusal leaves the target untouched, so
# there is never a partial `.codex/` to roll back. Returns 0 (clear) / 2
# (refused — diffs printed).
_codex_preflight() {
  local refused=0 src_rel dst_rel src dst tmp
  while IFS=$'\t' read -r src_rel dst_rel; do
    [[ -n "$src_rel" ]] || continue
    src="$SOURCE_DIR/$src_rel"; dst="$TARGET/$dst_rel"
    [[ -f "$src" ]] || continue
    [[ -e "$dst" ]] || continue
    tmp="$(mktemp "${TMPDIR:-/tmp}/ceo-codex-pf.XXXXXX" 2>/dev/null || true)"
    [[ -n "$tmp" ]] || continue
    _codex_render_to_stdout "$src" > "$tmp" 2>/dev/null
    if ! diff -q "$dst" "$tmp" >/dev/null 2>&1; then
      if [[ "${CODEX_FORCE:-0}" -ne 1 ]]; then
        refused=1
        echo "::error::refusing to overwrite pre-existing $dst_rel (pass --force to override)" >&2
        echo "    --- current (on disk) vs would-install (unified diff, head) ---" >&2
        diff -u "$dst" "$tmp" 2>/dev/null | head -40 >&2 || true
      fi
    fi
    rm -f "$tmp" 2>/dev/null || true
  done <<EOF
$(_codex_planned_pairs)
EOF
  # requirements.toml is generated, not template-backed: a plain differ check.
  if [[ "${CODEX_MANAGED_HOOKS:-0}" -eq 1 && -e "$TARGET/requirements.toml" && "${CODEX_FORCE:-0}" -ne 1 ]]; then
    refused=1
    echo "::error::refusing to overwrite pre-existing requirements.toml (pass --force)" >&2
  fi
  [[ "$refused" -eq 0 ]]
}

# ---------------------------------------------------------------------------
# codex_emit_bundle — the top-level codex install action. Runs an atomic
# pre-flight FIRST so an un-forced collision leaves the target untouched
# (no partial writes). Returns non-zero on a hard error (1) or a refused
# collision (2), so the caller aborts and the rollback trap restores .claude/.
# ---------------------------------------------------------------------------
codex_emit_bundle() {
  echo ""
  echo "==> Codex harness (--harness codex) — emitting .codex/ registration bundle"
  echo "    Verified against codex-cli $CODEX_VERIFIED_VERSION (pin: $(_codex_pin_range))."
  echo "    HONESTY: NOTHING here is enforced until you grant /hooks trust; an"
  echo "             untrusted or modified hook is a SILENT no-op on codex 0.139."

  _CODEX_REFUSED=0
  _CODEX_MANIFEST_EMITS=""
  _CODEX_MANIFEST_BACKUPS=""

  # Atomic collision pre-flight — refuse the whole bundle before ANY write.
  if ! _codex_preflight; then
    echo "::error::codex bundle refused to overwrite pre-existing file(s); no files written." >&2
    echo "         Re-run with --force to back up and overwrite, or resolve by hand." >&2
    return 2
  fi

  # (1) registration surface + (2)/(3) rules + operator contract.
  _codex_emit_file "templates/codex/hooks.json"      ".codex/hooks.json"      || return 1
  _codex_emit_file "templates/codex/rules/ceo.rules" ".codex/rules/ceo.rules" || return 1
  _codex_emit_file "templates/codex/AGENTS.md"       "AGENTS.md"              || return 1

  # (4) managed-hooks policy (OQ1: opt-in, consent-first). requirements.toml is
  # a REVIEWABLE policy file in the repo, not a headless trust write into
  # $CODEX_HOME — the installer never silently trusts its own hooks.
  if [[ "${CODEX_MANAGED_HOOKS:-0}" -eq 1 ]]; then
    _codex_emit_managed_requirements
  fi

  # (5) skills-port row — N/A until Wave 8 lands (OQ2). Guarded, not faked.
  if [[ "${CODEX_WITH_SKILLS:-0}" -eq 1 ]]; then
    echo ""
    echo "    NOTE: --with-codex-skills is a NO-OP until PLAN-155 Wave 8 lands."
    echo "          No .codex/skills/ is created; skill counts are untouched."
    codex_journal "codex_skills_port" "deferred-wave-8"
  fi

  # (6) inverted pair-rail reviewer guidance (Codex operates, Claude reviews).
  _codex_print_reviewer_inversion

  _codex_write_manifest

  # trust-flow guidance always prints (consent-first).
  _codex_print_trust_flow
  return 0
}

_codex_emit_managed_requirements() {
  local dst="$TARGET/requirements.toml"
  echo ""
  echo "==> Managed hooks (--managed-hooks) — emitting requirements.toml"
  echo "    Managed hooks are trusted-by-policy and NON-DISABLEABLE (enterprise"
  echo "    posture). This writes a REVIEWABLE policy file into the repo; it does"
  echo "    NOT write trust into \$CODEX_HOME. Placement doctrine: admin/org scope"
  echo "    — commit it deliberately (ADR-161)."
  if [[ "$DRY_RUN" -eq 1 ]]; then
    if [[ -e "$dst" ]]; then
      echo "    (dry-run) EXISTS (would REFUSE unless --force): requirements.toml"
    else
      echo "    (dry-run) would CREATE: requirements.toml"
    fi
    return 0
  fi
  if [[ -e "$dst" && "${CODEX_FORCE:-0}" -ne 1 ]]; then
    echo "::error::refusing to overwrite pre-existing requirements.toml (pass --force)" >&2
    _CODEX_REFUSED=1
    return 0
  fi
  if [[ -e "$dst" && "${CODEX_FORCE:-0}" -eq 1 ]]; then
    local ts bak
    ts="$(date +%Y%m%d-%H%M%S)"
    bak="requirements.toml.ceo-bak-${ts}"
    cp "$dst" "$TARGET/$bak"
    _CODEX_MANIFEST_BACKUPS="${_CODEX_MANIFEST_BACKUPS}requirements.toml	${bak}"$'\n'
    echo "    BACKED UP: requirements.toml -> $bak (--force)"
  fi
  # Managed registration points codex at the SAME hooks.json the installer
  # emitted; the operator still reviews it in VCS.
  cat > "$dst" <<EOF
# ceo-orchestration — Codex MANAGED hooks policy (PLAN-155 Wave 5, OQ1).
# Managed hooks are trusted-by-policy and non-disableable. Verified against
# codex-cli $CODEX_VERIFIED_VERSION. Committing this file is the consent act;
# it is reviewable in VCS. NOTHING enforces until codex loads it — run the
# arming check after install. No speed claim; governance + auditability only.
[hooks]
sources = [".codex/hooks.json"]

# Project trust is a SEPARATE consent gate. The installer does NOT write it
# for you (consent-first). Grant it explicitly in \$CODEX_HOME/config.toml:
#   [projects."$PH_PROJECT_PATH"]
#   trust_level = "trusted"
EOF
  echo "    EMITTED: requirements.toml"
  _CODEX_MANIFEST_EMITS="${_CODEX_MANIFEST_EMITS}requirements.toml"$'\n'
  codex_journal "codex_emit" "requirements.toml"
}

_codex_print_reviewer_inversion() {
  echo ""
  echo "==> Inverted pair-rail (Codex operates, Claude reviews)"
  echo "    Under --harness codex the reviewer CLI is \`claude -p\` (mirror of the"
  echo "    Claude-host \`.mcp.json\` that registers the codex reviewer). The"
  echo "    Stop-hook review gate that USES it lands with PLAN-155 Wave 6; this"
  echo "    installer records the inversion and does NOT install the Claude-host"
  echo "    codex MCP server (.mcp.json) on the codex path."
  echo "    Reviewer model pin: override with CEO_REVIEWER_MODEL (OQ3); the"
  echo "    same-vendor caveat is direction-neutral (author=OpenAI, reviewer="
  echo "    Anthropic — no single model is both author and sole reviewer)."
  codex_journal "codex_reviewer_inverted" "reviewer_cli=claude"
}

_codex_print_trust_flow() {
  echo ""
  echo "==> Trust flow (consent-first — the installer NEVER trusts your hooks for you)"
  echo "    Two gates must BOTH hold before any project hook fires:"
  echo "      1. Project trust — in \$CODEX_HOME/config.toml:"
  echo "           [projects.\"$PH_PROJECT_PATH\"]"
  echo "           trust_level = \"trusted\""
  echo "      2. Per-hook trust — run \`codex\` and use /hooks to review + trust"
  echo "         each entry in .codex/hooks.json (trust is keyed to the command"
  echo "         line; any edit re-prompts)."
  if [[ "${CODEX_MANAGED_HOOKS:-0}" -eq 1 ]]; then
    echo "    (You passed --managed-hooks: requirements.toml makes the hooks"
    echo "     trusted-by-policy once committed — but project trust above is still"
    echo "     yours to grant.)"
  fi
}

# ---------------------------------------------------------------------------
# codex_arming_check — the post-install doctor (debate A7). Prints exactly one
# verdict: ARMED / NOT-ARMED-(untrusted) / BROKEN. Always states loudly that
# NOTHING is enforced until /hooks trust is granted. Returns:
#   0 = ARMED, 1 = NOT-ARMED-(untrusted), 2 = BROKEN.
# Safe to call standalone (install.sh --harness codex --arming-check).
# ---------------------------------------------------------------------------
codex_arming_check() {
  local target="${1:-$TARGET}"
  local broken=0 reasons=""
  echo ""
  echo "==> Post-install arming check (codex harness) — is enforcement live?"

  # (a) required files present.
  local hooks_json="$target/.codex/hooks.json"
  local shim="$target/.claude/hooks/_python-hook.sh"
  if [[ ! -f "$hooks_json" ]]; then
    broken=1; reasons="${reasons}  - MISSING: .codex/hooks.json (run the codex install)"$'\n'
  fi
  if [[ ! -f "$shim" ]]; then
    broken=1; reasons="${reasons}  - MISSING: .claude/hooks/_python-hook.sh (framework hooks not installed)"$'\n'
  elif [[ ! -x "$shim" ]]; then
    broken=1; reasons="${reasons}  - NOT EXECUTABLE: .claude/hooks/_python-hook.sh (chmod +x)"$'\n'
  fi

  # (b) git-worktree discovery gap (codex 0.139 silently finds ZERO hooks).
  if _codex_is_git_worktree "$target"; then
    broken=1
    reasons="${reasons}  - GIT WORKTREE: codex 0.139 discovers ZERO hooks inside a git worktree"$'\n'
    reasons="${reasons}    (\`.git\` is a file). Enforcement is SILENTLY ABSENT here — run from a"$'\n'
    reasons="${reasons}    normal clone, or track the substrate-watch item for a codex fix."$'\n'
  fi

  # (c) codex binary + version skew (A15).
  local ver range
  ver="$(_codex_detect_version)"
  range="$(_codex_pin_range)"
  if [[ -z "$ver" ]]; then
    reasons="${reasons}  - codex not on PATH: cannot verify the binary or its version"$'\n'
  elif ! _codex_ver_in_range "$ver" "$range"; then
    reasons="${reasons}  - VERSION SKEW: codex $ver is OUTSIDE the verified pin ($range);"$'\n'
    reasons="${reasons}    fixtures/enforcement were certified on $CODEX_VERIFIED_VERSION — re-verify."$'\n'
  fi

  # (d) project trust (best-effort positive check; we NEVER assume trusted).
  local trusted=0
  local codex_home="${CODEX_HOME:-$HOME/.codex}"
  local cfg="$codex_home/config.toml"
  if [[ -f "$cfg" ]] && command -v python3 >/dev/null 2>&1; then
    if PYTHONNOUSERSITE=1 python3 -I -c '
import sys
cfg, proj = sys.argv[1], sys.argv[2]
try:
    import tomllib  # py>=3.11
    with open(cfg, "rb") as f:
        d = tomllib.load(f)
    p = d.get("projects", {}).get(proj, {})
    sys.exit(0 if p.get("trust_level") == "trusted" else 1)
except Exception:
    # No tomllib (py<3.11) or parse error: fall back to a literal scan.
    try:
        with open(cfg, "r", encoding="utf-8") as f:
            txt = f.read()
    except OSError:
        sys.exit(1)
    needle = "[projects.\"%s\"]" % proj
    sys.exit(0 if (needle in txt and "trust_level = \"trusted\"" in txt) else 1)
' "$cfg" "$target" 2>/dev/null; then
      trusted=1
    fi
  fi

  echo ""
  if [[ "$broken" -eq 1 ]]; then
    echo "    VERDICT: BROKEN"
    printf '%s' "$reasons" >&2
    echo "    Enforcement is NOT live. Fix the above, then re-run the arming check." >&2
    return 2
  fi
  if [[ -n "$reasons" ]]; then
    # Non-fatal warnings (version/PATH) but files are OK — surface them.
    printf '%s' "$reasons" >&2
  fi
  if [[ "$trusted" -eq 1 ]]; then
    echo "    VERDICT: ARMED (project trusted in $cfg)"
    echo "    REMINDER: per-hook /hooks trust is keyed to each command line; any"
    echo "    edit to .codex/hooks.json re-prompts. NOTHING is enforced for an"
    echo "    untrusted or modified hook — re-verify after every change."
    return 0
  fi
  echo "    VERDICT: NOT-ARMED-(untrusted)"
  echo "    NOTHING is enforced until you grant /hooks trust. To arm:"
  echo "      1. Add project trust in \$CODEX_HOME/config.toml:"
  echo "           [projects.\"$target\"]"
  echo "           trust_level = \"trusted\""
  echo "      2. Run \`codex\`, open /hooks, review + trust each .codex/hooks.json entry."
  echo "      3. Re-run:  scripts/install.sh --harness codex --arming-check $target"
  return 1
}

# ---------------------------------------------------------------------------
# codex_uninstall — lifecycle symmetry (debate A9). Manifest-driven: removes
# every 'emit' path (incl. Wave 6's .git/ pre-push hook once it appends its
# line) and restores every 'backup' pair. Refuses if no manifest.
# ---------------------------------------------------------------------------
codex_uninstall() {
  local target="${1:-$TARGET}"
  local manifest="$target/$CODEX_MANIFEST_REL"
  echo ""
  echo "==> Codex harness uninstall (manifest-driven)"
  if [[ ! -f "$manifest" ]]; then
    echo "::error::no codex harness manifest at $CODEX_MANIFEST_REL — nothing to uninstall" >&2
    return 1
  fi

  # Restore backups FIRST (so a force-replaced file returns), then remove emits.
  local rel bak
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

  # Remove emit paths. Skip any that a backup just restored.
  local restored=""
  restored="$(grep -E '^backup	' "$manifest" 2>/dev/null | cut -f2 || true)"
  while IFS=$'\t' read -r kind rel _; do
    [[ "$kind" == "emit" ]] || continue
    [[ -n "$rel" ]] || continue
    if printf '%s\n' "$restored" | grep -Fxq "$rel"; then
      continue  # a backup already restored the original in place
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
    # Prune the .codex dir if now empty (best-effort).
    rmdir "$target/.codex/rules" 2>/dev/null || true
    rmdir "$target/.codex" 2>/dev/null || true
    echo "    Uninstall complete. Verify no enforcement residue: no .codex/, no"
    echo "    operator AGENTS.md, no requirements.toml (unless you kept your own)."
  fi
  return 0
}
