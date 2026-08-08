OpenAI Codex v0.144.6
--------
workdir: /Users/joaocanhada/canhada-labs/ceo-orchestration
model: gpt-5.6-sol
provider: openai
approval: never
sandbox: workspace-write [workdir, /tmp, $TMPDIR]
reasoning effort: xhigh
reasoning summaries: none
session id: 019fdecb-bbfb-78e1-bb2f-c4c3ccb1ab1b
--------
user
current changes
exec
/bin/zsh -lc "git status --short && printf '\\n--- DIFF STAT ---\\n' && git diff --stat && printf '\\n--- CACHED STAT ---\\n' && git diff --cached --stat" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
 A .claude/.framework-version
 A .claude/adr/ADR-155-AMEND-1-delivery-record-ownership.md
 A .claude/governance/npm-trusted-publisher.txt
 M .claude/governance/pair-rail-verdict-template.md
 M .claude/plans/PLAN-166/W1-approved-draft.md
 A .claude/plans/PLAN-166/architect/round-1/approved.md
 M .claude/plans/PLAN-166/staged-manifest.sha256
 M .claude/scripts/check-framework-updates.sh
 M .claude/scripts/tests/test_release_workflow_asserts.py
 M .github/workflows/npm-publish.yml
 M .github/workflows/release.yml
 M .github/workflows/smoke-install.yml
 M INSTALL.md
 M README.md
 M README.pt-BR.md
 M RELEASE.md
 M docs/ARCHITECTURE.md
 M docs/CTO-GUIDE.md
 M docs/FAQ.md
 M docs/GUIA-COMPLETO.md
 M docs/README.md
 M npm/README.md
 M scripts/doctor.sh
 M scripts/tests/_parity_classify.py
 A scripts/tests/test-upgrade-spec-ownership.sh
?? .claude/plans/PLAN-166/OWNER-W1-LAND-step1.sh
?? .claude/plans/PLAN-166/OWNER-W1-LAND-step1b.sh
?? .claude/plans/PLAN-166/W1-ceremony-log.md
?? .claude/plans/PLAN-166/architect/round-1/approved.md.asc
?? .claude/plans/PLAN-166/archive/
?? .claude/plans/PLAN-167/OWNER-PREPARE-TO-SIGN.sh
?? .claude/plans/PLAN-167/W4-approved.md
?? .claude/plans/PLAN-167/W4-approved.md.asc
?? .claude/plans/PLAN-168/archive/

--- DIFF STAT ---
 .claude/.framework-version                         |   1 +
 .../ADR-155-AMEND-1-delivery-record-ownership.md   | 240 ++++++++
 .claude/governance/npm-trusted-publisher.txt       |  36 ++
 .claude/governance/pair-rail-verdict-template.md   |  18 +
 .claude/plans/PLAN-166/W1-approved-draft.md        |   1 +
 .../plans/PLAN-166/architect/round-1/approved.md   | 202 ++++++
 .claude/plans/PLAN-166/staged-manifest.sha256      |  22 +-
 .claude/scripts/check-framework-updates.sh         |  95 ++-
 .../scripts/tests/test_release_workflow_asserts.py | 683 ++++++++++++++++++++-
 .github/workflows/npm-publish.yml                  | 151 +++++
 .github/workflows/release.yml                      | 164 +++++
 .github/workflows/smoke-install.yml                | 119 +++-
 INSTALL.md                                         |  51 +-
 README.md                                          |   4 +-
 README.pt-BR.md                                    |   4 +-
 RELEASE.md                                         |   2 +-
 docs/ARCHITECTURE.md                               |   6 +-
 docs/CTO-GUIDE.md                                  |   4 +-
 docs/FAQ.md                                        |   2 +-
 docs/GUIA-COMPLETO.md                              |   4 +-
 docs/README.md                                     |   2 +-
 npm/README.md                                      |   4 +-
 scripts/doctor.sh                                  |  34 +
 scripts/tests/_parity_classify.py                  |  45 +-
 scripts/tests/test-upgrade-spec-ownership.sh       | 359 +++++++++++
 25 files changed, 2170 insertions(+), 83 deletions(-)

--- CACHED STAT ---

exec
/bin/zsh -lc "find .claude/plans/PLAN-166/archive .claude/plans/PLAN-168/archive -type f -maxdepth 5 -print 2>/dev/null | sort && printf '\\n--- untracked sizes ---\\n' && for f in .claude/plans/PLAN-166/OWNER-W1-LAND-step1.sh .claude/plans/PLAN-166/OWNER-W1-LAND-step1b.sh .claude/plans/PLAN-166/W1-ceremony-log.md .claude/plans/PLAN-166/architect/round-1/approved.md.asc .claude/plans/PLAN-167/OWNER-PREPARE-TO-SIGN.sh .claude/plans/PLAN-167/W4-approved.md .claude/plans/PLAN-167/W4-approved.md.asc; do [ -f \""'$f" ] && wc -lc "$f"; done' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
.claude/plans/PLAN-166/archive/ceremony-porcelain-20260806-1430.txt
.claude/plans/PLAN-166/archive/ceremony-worktree-20260806-1430.diff
.claude/plans/PLAN-166/archive/codex-r6-2059.md
.claude/plans/PLAN-166/archive/codex-r7-stophook-2135.md
.claude/plans/PLAN-166/archive/codex-review-sentinel.md
.claude/plans/PLAN-166/archive/codex-review-w0-residuals.md
.claude/plans/PLAN-166/archive/codex-review-w1-ceremony.md
.claude/plans/PLAN-166/archive/codex-review-w1-round10.md
.claude/plans/PLAN-166/archive/codex-review-w1-round11.md
.claude/plans/PLAN-166/archive/codex-review-w1-round2.md
.claude/plans/PLAN-166/archive/codex-review-w1-round3.md
.claude/plans/PLAN-166/archive/codex-review-w1-round4.md
.claude/plans/PLAN-166/archive/codex-review-w1-round5.md
.claude/plans/PLAN-166/archive/codex-review-w1-round6.md
.claude/plans/PLAN-166/archive/codex-review-w1-round7.md
.claude/plans/PLAN-166/archive/codex-review-w1-round8.md
.claude/plans/PLAN-166/archive/codex-review-w1-round9.md
.claude/plans/PLAN-166/archive/mirror-fixes.sh
.claude/plans/PLAN-166/archive/r6-verdict-decision.md
.claude/plans/PLAN-166/archive/w1-staged-pack-20260806-0159.tar.gz
.claude/plans/PLAN-166/archive/w1-staged-pack-final-20260806-0722.tar.gz
.claude/plans/PLAN-168/archive/0001-plan168-W1-CI-wiring-dos-or-culos-de-propriedade.patch
.claude/plans/PLAN-168/archive/0002-plan168-W2-W3-INV-4-curada-pelo-gerador-nico-ADR-190.patch
.claude/plans/PLAN-168/archive/0003-plan168-baseline-map-re-gravado-62-GREEN-3-RED-run-2.patch
.claude/plans/PLAN-168/archive/0004-plan168-restaura-token-ADOPTER-FORK-na-WARNING-do-fo.patch
.claude/plans/PLAN-168/archive/full-e2e-20260807-2017.log
.claude/plans/PLAN-168/archive/pack-full.diff

--- untracked sizes ---
      83    4151 .claude/plans/PLAN-166/OWNER-W1-LAND-step1.sh
     128    6303 .claude/plans/PLAN-166/OWNER-W1-LAND-step1b.sh
     191   11041 .claude/plans/PLAN-166/W1-ceremony-log.md
       8     265 .claude/plans/PLAN-166/architect/round-1/approved.md.asc
      54    2538 .claude/plans/PLAN-167/OWNER-PREPARE-TO-SIGN.sh
     116    5132 .claude/plans/PLAN-167/W4-approved.md
       8     265 .claude/plans/PLAN-167/W4-approved.md.asc

  ✓ Inventory all changed and untracked files and identify executable surfaces
  → Review shell scripts, workflows, and tests against existing contracts
  • Run targeted read-only checks/tests and validate suspected regressions
  • Return prioritized JSON findings
exec
/bin/zsh -lc 'git diff --no-ext-diff --unified=80 -- ".claude/scripts/check-framework-updates.sh"' in /Users/joaocanhada/canhada-labs/ceo-orchestration
exec
/bin/zsh -lc 'git diff --no-ext-diff --unified=80 -- "scripts/doctor.sh"' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
diff --git a/scripts/doctor.sh b/scripts/doctor.sh
index 20548fd..7425a2a 100755
--- a/scripts/doctor.sh
+++ b/scripts/doctor.sh
@@ -536,164 +536,198 @@ while IFS= read -r line || [ -n "$line" ]; do
         # Hash record but the path is now a symlink / non-regular file. Never
         # hash-through or repair-through it (symlink write-through escape).
         DRIFT_COUNT=$((DRIFT_COUNT + 1))
         BLOCKED_COUNT=$((BLOCKED_COUNT + 1))
         UNRESOLVED=$((UNRESOLVED + 1))
         _log "    DRIFT (type-change: regular file recorded, non-file found — not repairable): $rel"
         continue
       fi
 
       cur="$( _hash_file "$fpath" 2>/dev/null || true )"
       if [ "$cur" = "$base" ]; then
         OK_COUNT=$((OK_COUNT + 1))
         [ "$VERBOSE" -eq 1 ] && _log "    OK: $rel"
         continue
       fi
 
       DRIFT_COUNT=$((DRIFT_COUNT + 1))
       src_hash="$( _hash_file "$SOURCE_DIR/$rel" 2>/dev/null || true )"
       if [ -z "$src_hash" ]; then
         _log "    DRIFT (framework checkout no longer ships this file — not repairable): $rel"
         BLOCKED_COUNT=$((BLOCKED_COUNT + 1))
         UNRESOLVED=$((UNRESOLVED + 1))
       elif [ "$cur" = "$src_hash" ]; then
         _log "    DRIFT (baseline-stale: file matches CURRENT framework; run upgrade.sh to refresh the baseline): $rel"
         BLOCKED_COUNT=$((BLOCKED_COUNT + 1))
         UNRESOLVED=$((UNRESOLVED + 1))
       elif [ "$src_hash" = "$base" ]; then
         _log "    DRIFT (adopter-modified): $rel"
         if [ "$REPAIR" -eq 1 ]; then
           if _confirmed "$rel"; then
             if [ "$DRY_RUN" -eq 1 ]; then
               _log "    (dry-run) would BACKUP + RESTORE: $rel"
               WOULD_REPAIR=$((WOULD_REPAIR + 1))
               UNRESOLVED=$((UNRESOLVED + 1))
             else
               _backup_file "$rel"
               _log "    BACKED-UP: $rel -> $BAK_DIR/$rel"
               if _restore_file "$rel" "$base"; then
                 REPAIRED_COUNT=$((REPAIRED_COUNT + 1))
               else
                 UNRESOLVED=$((UNRESOLVED + 1))
               fi
             fi
           else
             SKIPPED_CONFIRM=$((SKIPPED_CONFIRM + 1))
             UNRESOLVED=$((UNRESOLVED + 1))
             _log "    SKIPPED (needs --yes-file '$rel' or interactive confirm): $rel"
           fi
         else
           UNRESOLVED=$((UNRESOLVED + 1))
         fi
       else
         _log "    DRIFT (conflict: file AND framework both diverged from baseline — run upgrade.sh): $rel"
         BLOCKED_COUNT=$((BLOCKED_COUNT + 1))
         UNRESOLVED=$((UNRESOLVED + 1))
       fi
       ;;
   esac
 done < "$SANITIZED"
 
 # ---------------------------------------------------------------------------
 # Orphan scan (report-only): files present under the framework-owned
 # enumeration (_framework_manifest_set.sh, FMS_ROOT=$TARGET) with NO manifest
 # record. Candidates ONLY — they may be adopter-authored; never removed.
 # ---------------------------------------------------------------------------
 if [ "$NO_ORPHAN_SCAN" -eq 0 ]; then
   if [ "$HAVE_FMS" -eq 1 ]; then
     if [ -n "$PROFILE" ]; then
       PROFILE_PARTS_STR="$( printf '%s' "$PROFILE" | tr ',' ' ' )"
     else
       # Auto-detect: core + frontend (absent dirs are skipped by the
       # enumerator) + every installed domain dir.
       PROFILE_PARTS_STR="core frontend"
       if [ -d "$TARGET/.claude/skills/domains" ]; then
         for d in "$TARGET/.claude/skills/domains"/*/; do
           [ -d "$d" ] || continue
           PROFILE_PARTS_STR="$PROFILE_PARTS_STR $( basename "$d" )"
         done
       fi
     fi
+    # PLAN-166 F3 (ADR-155-AMEND-1): the FMS entries for PROTOCOL.md,
+    # SPEC/v1 and .claude/.framework-version are CONDITIONAL on the
+    # recorded delivery. doctor resolves the flags from the SAME record
+    # the writers use — the sanitized baseline manifest — NEVER from the
+    # ceremony: ceremony-only resolution would re-include paths a
+    # `--ceremony user` install skipped and --strict-orphans would flag
+    # the ADOPTER's own SPEC/PROTOCOL files as orphans (r19), while a
+    # blanket maintainer default would do the same and a blanket user
+    # default would hide a delivered SPEC from a maintainer (r9 P2).
+    _dr_delivered() {  # $1 = ERE fragment anchored at the relpath position
+      grep -Eq "^([0-9a-f]{64}|LINK)  $1" "$SANITIZED" 2>/dev/null
+    }
+    # `SPEC/v1(/|  |$)` and not a bare `SPEC/v1/`: a --mode link install
+    # records the whole tree as ONE directory symlink (`LINK  SPEC/v1
+    # <target>`, no trailing slash) — the same `(  |$)` treatment the
+    # PROTOCOL/marker fragments below already have (re-pass closure; family
+    # swept with upgrade.sh _baseline_has_spec_record).
+    if _dr_delivered 'SPEC/v1(/|  |$)'; then
+      FMS_DELIVERED_SPEC=1
+    else
+      FMS_DELIVERED_SPEC=0
+    fi
+    if _dr_delivered 'PROTOCOL\.md(  |$)'; then
+      FMS_DELIVERED_PROTOCOL=1
+    else
+      FMS_DELIVERED_PROTOCOL=0
+    fi
+    if _dr_delivered '\.claude/\.framework-version(  |$)'; then
+      FMS_DELIVERED_MARKER=1
+    else
+      FMS_DELIVERED_MARKER=0
+    fi
+    export FMS_DELIVERED_SPEC FMS_DELIVERED_PROTOCOL FMS_DELIVERED_MARKER
     export FMS_ROOT="$TARGET"
     export FMS_PROFILE_PARTS="$PROFILE_PARTS_STR"
     _framework_manifest_files > "$WORKDIR/enumerated" 2>/dev/null || : > "$WORKDIR/enumerated"
     unset FMS_ROOT FMS_PROFILE_PARTS
+    unset FMS_DELIVERED_SPEC FMS_DELIVERED_PROTOCOL FMS_DELIVERED_MARKER
     # Manifest relpaths (both record kinds).
     awk '{
       idx = index($0, "  ");
       if (idx == 0) next;
       d = substr($0, 1, idx - 1);
       rest = substr($0, idx + 2);
       if (d == "LINK") { j = index(rest, "  "); if (j > 0) rest = substr(rest, 1, j - 1) }
       print rest;
     }' "$SANITIZED" | LC_ALL=C sort -u > "$WORKDIR/manifest-rels"
     LC_ALL=C sort -u "$WORKDIR/enumerated" > "$WORKDIR/enumerated.sorted"
     comm -23 "$WORKDIR/enumerated.sorted" "$WORKDIR/manifest-rels" > "$WORKDIR/orphans" || : > "$WORKDIR/orphans"
     if [ -s "$WORKDIR/orphans" ]; then
       _log ""
       _log "==> Orphan candidates (present in framework-owned dirs, absent from manifest;"
       _log "    possibly adopter-authored — REPORT-ONLY, nothing is removed):"
       while IFS= read -r orel; do
         [ -n "$orel" ] || continue
         ORPHAN_COUNT=$((ORPHAN_COUNT + 1))
         _log "    ORPHAN?: $orel"
       done < "$WORKDIR/orphans"
     fi
   else
     _log "    NOTE: orphan scan skipped — _framework_manifest_set.sh not found beside doctor.sh"
   fi
 fi
 
 # ---------------------------------------------------------------------------
 # Pair-rail timeout coherence (PLAN-164 / ADR-110-AMEND-1 — ADVISORY,
 # report-only, NEVER drives the exit code): the harness kills a hook at its
 # settings.json registration timeout, so a check_pair_rail.py registration
 # below the hook's INTERNAL default (CEO_PAIR_RAIL_TIMEOUT_S) + the 30s
 # invariant margin means the codex verdict can be killed mid-flight — the
 # historical 12/12 pair_rail_case F/TIMEOUT class (hook-kill risk). The
 # internal default is read with the SAME regex the invariant uses:
 # os.environ.get("CEO_PAIR_RAIL_TIMEOUT_S", "NNN"). Fail-open: missing
 # jq/hook/settings or an unparseable value => NOTE + skip.
 # ---------------------------------------------------------------------------
 _pair_rail_timeout_check() {
   _prt_settings="$TARGET/.claude/settings.json"
   _prt_hook="$TARGET/.claude/hooks/check_pair_rail.py"
   if [ ! -f "$_prt_settings" ] || [ ! -f "$_prt_hook" ]; then
     return 0
   fi
   if ! command -v jq >/dev/null 2>&1; then
     _log "    NOTE: pair-rail timeout check skipped (jq not found) — advisory only"
     return 0
   fi
   _prt_reg="$( jq -r '[ .hooks // {} | to_entries[] | .value
       | select(type == "array") | .[] | .hooks[]?
       | select((type == "object")
           and ((.command? | type) == "string")
           and (.command | test("check_pair_rail\\.py")))
       | .timeout ] | first // empty' "$_prt_settings" 2>/dev/null || true )"
   _prt_int="$( sed -n 's/.*os\.environ\.get("CEO_PAIR_RAIL_TIMEOUT_S", "\([0-9][0-9]*\)").*/\1/p' "$_prt_hook" 2>/dev/null | head -n 1 )"
   case "$_prt_reg" in
     ''|*[!0-9]*)
       _log "    NOTE: pair-rail timeout check skipped (no numeric check_pair_rail.py registration timeout in settings.json) — advisory only"
       return 0 ;;
   esac
   case "$_prt_int" in
     ''|*[!0-9]*)
       _log "    NOTE: pair-rail timeout check skipped (internal CEO_PAIR_RAIL_TIMEOUT_S default not found in check_pair_rail.py) — advisory only"
       return 0 ;;
   esac
   if [ "$_prt_reg" -lt $((_prt_int + 30)) ]; then
     _log ""
     _log "    WARN: check_pair_rail.py registration timeout (${_prt_reg}s) < internal default (${_prt_int}s) + 30s margin —"
     _log "          the harness can KILL the hook before the codex verdict lands (PLAN-164 hook-kill risk;"
     _log "          the historical 12/12 pair_rail_case F/TIMEOUT class). Raise the settings.json registration"
     _log "          timeout to >= $((_prt_int + 30))s (upgrade.sh migrates the old default 60 -> 150)."
   elif [ "$VERBOSE" -eq 1 ]; then
     _log "    OK (pair-rail timeouts): registration ${_prt_reg}s >= internal ${_prt_int}s + 30s margin"
   fi
   return 0
 }
 _pair_rail_timeout_check
 
 # ---------------------------------------------------------------------------
 # Summary + exit code
 # ---------------------------------------------------------------------------

 succeeded in 0ms:
diff --git a/.claude/scripts/check-framework-updates.sh b/.claude/scripts/check-framework-updates.sh
index abe39d0..e867780 100755
--- a/.claude/scripts/check-framework-updates.sh
+++ b/.claude/scripts/check-framework-updates.sh
@@ -2,180 +2,265 @@
 # check-framework-updates.sh — compare local VERSION to upstream tags
 #
 # Fetches upstream tag list via `git ls-remote --tags <repo>` (HTTPS),
 # parses semantic versions (vX.Y.Z, vX.Y.Z-rc.N), compares with local
 # VERSION file, and reports the delta.
 #
 # Network call: HTTPS only. Adopter-invoked. Documented in
 # threat-model.md as opt-in trust boundary.
 #
 # Usage:
 #   check-framework-updates.sh                              # default upstream
 #   check-framework-updates.sh --upstream <git-url>
 #   check-framework-updates.sh --json
 #   check-framework-updates.sh --quiet                       # exit code only
 #
 # Exit codes:
 #   0 — local matches upstream OR cannot determine (network failure)
 #   1 — local is behind (newer GA tag available)
 #   2 — local is behind by ≥ 1 MINOR version (highlighted as urgent)
 #   3 — fatal (no git, no VERSION file, malformed local version)
 
 set -euo pipefail
 
 # Framework upstream URL — points to the canonical ceo-orchestration
 # upstream by default. Adopters who fork the framework override via
 # CEO_FRAMEWORK_UPSTREAM env var OR install.sh
 # `--framework-upstream=<url>` substitution at install time.
 UPSTREAM="${CEO_FRAMEWORK_UPSTREAM:-https://github.com/Canhada-Labs/ceo-orchestration}"
 FORMAT="text"
 QUIET=0
 LOCAL_VERSION_FILE=""
 
 usage() {
   cat <<EOF
 check-framework-updates.sh — compare local VERSION to upstream tags
 
 Usage:
   check-framework-updates.sh [options]
 
 Options:
   --upstream <git-url>     Override default upstream
                            (default: \$CEO_FRAMEWORK_UPSTREAM or
                             https://github.com/Canhada-Labs/ceo-orchestration)
   --version-file <path>    Override default VERSION lookup
   --json                   Machine-readable output
   --quiet                  Suppress output; exit code only
   -h, --help               This message
 
 Exit codes:
   0 — up to date (or cannot determine)
   1 — behind (newer GA tag available)
   2 — behind by ≥ 1 MINOR (urgent)
   3 — fatal
 EOF
 }
 
 while [[ $# -gt 0 ]]; do
   case "$1" in
     --upstream) UPSTREAM="$2"; shift 2 ;;
     --version-file) LOCAL_VERSION_FILE="$2"; shift 2 ;;
     --json) FORMAT="json"; shift ;;
     --quiet) QUIET=1; shift ;;
     -h|--help) usage; exit 0 ;;
     *) echo "unknown arg: $1" >&2; usage >&2; exit 3 ;;
   esac
 done
 
 log() {
   if [ "$QUIET" -eq 0 ]; then
     echo "$@" >&2
   fi
   return 0
 }
 out() {
   if [ "$QUIET" -eq 0 ]; then
     echo "$@"
   fi
   return 0
 }
 
-# Resolve VERSION
+# Resolve the LOCAL framework version — MARKER-FIRST with VERSION fallback
+# (PLAN-166 F3 / ADR-155-AMEND-1). In an ADOPTER tree the root VERSION is an
+# install-time snapshot: upgrade.sh deliberately never touches it (the
+# S238/ADR-155 clobber class), so reading it post-upgrade reports the OLD
+# version forever and this checker would exit behind-minor demanding the
+# SAME upgrade it just performed, in a loop (r8). The upgrade refreshes
+# .claude/.framework-version instead — but the marker is only TRUSTED when
+# the SAME delivery record the writers use (the ADR-155 baseline manifest,
+# .claude/.install-manifest.sha256) records it as framework-delivered: a
+# pre-existing adopter marker that install EXISTS-skipped must not be read
+# at all (r20). Resolution order:
+#   1. --version-file <path>              (explicit override — unchanged)
+#   2. <root>/.claude/.framework-version  when well-formed AND
+#                                         delivery-recorded in the manifest
+#   3. <root>/VERSION                     (pre-v1.3.0 installs, and the
+#                                          framework repo itself, where the
+#                                          tracked marker == VERSION and
+#                                          VERSION stays the authority)
 if [ -n "$LOCAL_VERSION_FILE" ]; then
   VFILE="$LOCAL_VERSION_FILE"
+  VSOURCE="explicit --version-file"
 else
-  # Walk up from CWD looking for a VERSION file
+  # Walk up from CWD to the first directory carrying either signal.
   cur="$(pwd)"
+  VROOT=""
   VFILE=""
+  VSOURCE=""
   while [ "$cur" != "/" ]; do
-    if [ -f "$cur/VERSION" ]; then
-      VFILE="$cur/VERSION"
+    if [ -f "$cur/.claude/.framework-version" ] || [ -f "$cur/VERSION" ]; then
+      VROOT="$cur"
       break
     fi
     cur="$(dirname "$cur")"
   done
+  if [ -z "$VROOT" ]; then
+    echo "fatal: no .claude/.framework-version or VERSION found (looked from $(pwd))" >&2
+    exit 3
+  fi
+  MARKER="$VROOT/.claude/.framework-version"
+  MANIFEST="$VROOT/.claude/.install-manifest.sha256"
+  if [ -f "$MARKER" ]; then
+    MARKER_REC=""
+    if [ -f "$MANIFEST" ]; then
+      MARKER_REC="$(grep -E '^([0-9a-f]{64}|LINK)  \.claude/\.framework-version(  |$)' "$MANIFEST" 2>/dev/null | head -1 || true)"
+    fi
+    if [ -n "$MARKER_REC" ]; then
+      # r20 answered PROVENANCE (is this marker the framework's delivery?)
+      # but never INTEGRITY: a delivered marker edited afterwards to any
+      # well-formed version still satisfied the record check, so hand-editing
+      # 1.3.0 -> 9.9.9 made the checker report up-to-date against an upstream
+      # 1.3.0 and SUPPRESS a real update (codex W1 round 7, P2). Verify the
+      # live bytes against the record before selecting the marker; anything
+      # unverifiable falls back to VERSION — the same conservative direction
+      # r20 already takes for an unrecorded marker.
+      MARKER_OK=""
+      case "$MARKER_REC" in
+        LINK\ \ *)
+          # Fixed double-space delimiter (targets may contain spaces).
+          _rec_tgt="${MARKER_REC#LINK  .claude/.framework-version  }"
+          _live_tgt="$(readlink "$MARKER" 2>/dev/null || true)"
+          if [ -n "$_rec_tgt" ] && [ "$_rec_tgt" = "$_live_tgt" ]; then MARKER_OK=1; fi
+          ;;
+        *)
+          _rec_dg="${MARKER_REC%%  *}"
+          _live_dg=""
+          if command -v shasum >/dev/null 2>&1; then
+            _live_dg="$(shasum -a 256 "$MARKER" 2>/dev/null | cut -d' ' -f1 || true)"
+          elif command -v sha256sum >/dev/null 2>&1; then
+            _live_dg="$(sha256sum "$MARKER" 2>/dev/null | cut -d' ' -f1 || true)"
+          fi
+          if [ -n "$_live_dg" ] && [ "$_rec_dg" = "$_live_dg" ]; then MARKER_OK=1; fi
+          ;;
+      esac
+      if [ -z "$MARKER_OK" ]; then
+        log "note: .claude/.framework-version does NOT match its delivery record (edited, redirected, or no digest tool available) — falling back to VERSION"
+      else
+        MARKER_VAL="$(tr -d '\n\r ' < "$MARKER" 2>/dev/null || true)"
+        if [[ "$MARKER_VAL" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-rc\.[0-9]+)?$ ]]; then
+          VFILE="$MARKER"
+          VSOURCE="marker (.claude/.framework-version, delivery-recorded)"
+        else
+          log "note: .claude/.framework-version malformed ('$MARKER_VAL') — falling back to VERSION"
+        fi
+      fi
+    elif [ ! -f "$MANIFEST" ] && [ ! -f "$VROOT/VERSION" ]; then
+      # No manifest AND no VERSION: the marker is the only signal there is
+      # (fail-open — refusing here would make the checker fatal on a tree
+      # that still has a perfectly readable version value).
+      VFILE="$MARKER"
+      VSOURCE="marker (no manifest — only signal present)"
+    else
+      log "note: .claude/.framework-version present but NOT delivery-recorded in .claude/.install-manifest.sha256 — falling back to VERSION (r20: a pre-existing adopter marker is not the framework's)"
+    fi
+  fi
+  if [ -z "$VFILE" ] && [ -f "$VROOT/VERSION" ]; then
+    VFILE="$VROOT/VERSION"
+    VSOURCE="root VERSION (fallback)"
+  fi
 fi
 
 if [ -z "$VFILE" ] || [ ! -f "$VFILE" ]; then
-  echo "fatal: VERSION file not found (looked from $(pwd))" >&2
+  echo "fatal: version source not found (looked from $(pwd))" >&2
   exit 3
 fi
+log "version source: ${VSOURCE:-unknown} ($VFILE)"
 
 LOCAL="$(tr -d '\n\r ' < "$VFILE")"
 if [ -z "$LOCAL" ]; then
   echo "fatal: VERSION file is empty: $VFILE" >&2
   exit 3
 fi
 
 # Validate local version shape
 if ! [[ "$LOCAL" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-rc\.[0-9]+)?$ ]]; then
   echo "fatal: local VERSION malformed: $LOCAL" >&2
   exit 3
 fi
 
 # Fetch upstream tags
 if ! command -v git >/dev/null 2>&1; then
   echo "fatal: git not available" >&2
   exit 3
 fi
 
 log "fetching tags from $UPSTREAM ..."
 
 # Network call. Tolerate failure with exit 0 (we should not pageop on a
 # transient git fetch failure).
 TAGS_RAW="$(git ls-remote --tags --refs "$UPSTREAM" 2>&1 || true)"
 if [ -z "$TAGS_RAW" ] || echo "$TAGS_RAW" | grep -qiE 'fatal|error|denied'; then
   log "warning: could not fetch upstream tags; assuming up-to-date"
   if [ "$FORMAT" = "json" ]; then
     out '{"status":"unknown","local":"'"$LOCAL"'","upstream":null,"reason":"network_or_perm_failure"}'
   else
     out "status: unknown (could not fetch upstream)"
     out "local:    $LOCAL"
     out "upstream: <unreachable>"
   fi
   exit 0
 fi
 
 # Parse — extract refs/tags/vX.Y.Z[-rc.N], strip leading v
 TAGS=()
 while IFS= read -r tag; do
   [ -n "$tag" ] && TAGS+=("$tag")
 done < <(echo "$TAGS_RAW" | awk '{print $2}' | sed 's|^refs/tags/||' | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+(-rc\.[0-9]+)?$' | sed 's/^v//' | sort -V -u)
 
 if [ "${#TAGS[@]}" -eq 0 ]; then
   log "warning: no semver tags found upstream"
   if [ "$FORMAT" = "json" ]; then
     out '{"status":"unknown","local":"'"$LOCAL"'","upstream":null,"reason":"no_semver_tags"}'
   else
     out "status: unknown (no semver tags upstream)"
   fi
   exit 0
 fi
 
 LATEST="${TAGS[${#TAGS[@]}-1]}"
 
 # Helper: parse "X.Y.Z[-rc.N]" into space-sep "X Y Z RC" (RC=999 if no -rc)
 _parse_version() {
   local v="$1"
   local x y z rc
   if [[ "$v" =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)-rc\.([0-9]+)$ ]]; then
     x="${BASH_REMATCH[1]}"
     y="${BASH_REMATCH[2]}"
     z="${BASH_REMATCH[3]}"
     rc="${BASH_REMATCH[4]}"
   elif [[ "$v" =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
     x="${BASH_REMATCH[1]}"
     y="${BASH_REMATCH[2]}"
     z="${BASH_REMATCH[3]}"
     rc="999"
   else
     echo "0 0 0 0"
     return
   fi
   echo "$x $y $z $rc"
 }
 
 # Compare LOCAL vs LATEST
 read -r LX LY LZ LR < <(_parse_version "$LOCAL")
 read -r UX UY UZ UR < <(_parse_version "$LATEST")
 
 CMP=0

exec
/bin/zsh -lc 'git diff --no-ext-diff --unified=80 -- ".github/workflows/release.yml"' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
diff --git a/.github/workflows/release.yml b/.github/workflows/release.yml
index 69d7836..596197e 100644
--- a/.github/workflows/release.yml
+++ b/.github/workflows/release.yml
@@ -1,151 +1,178 @@
 name: Release
 
 on:
   push:
     tags:
       - "v*"
 
 concurrency:
   group: release-${{ github.ref }}
   cancel-in-progress: false
 
 jobs:
   release-gate:
     # PLAN-012 Phase 2 CEO_SOTA_DISABLE parity.
     if: vars.CEO_SOTA_DISABLE != '1'
     runs-on: ubuntu-latest
     timeout-minutes: 20
     permissions:
       # `contents: read` for checkout; `actions: read` lets the
       # weekly-workflow status gate (see below) call `gh run list`
       # against the public Actions REST API.
       contents: read
       actions: read
     steps:
       - name: Checkout tag
         # SHA-pinned (Sprint 7 Dependabot bump): actions/checkout@v6.0.2
         uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd
         with:
           fetch-depth: 0
 
       - name: Setup Python 3.11
         # SHA-pinned (Sprint 7 Dependabot bump): actions/setup-python@v6.2.0
         uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405
         with:
           python-version: "3.11"
 
       # -----------------------------------------------------------------
       # PLAN-153 Wave B item 5 (c) — RC-aware VERSION↔tag comparison.
       # Closes PLAN-152 §Deferred `release-gate-rc-version-mismatch`
       # (red run 28663453202 precedent).
       #
       # THE RC FLOW (documented so this never regresses): an RC tag
       # `v<X.Y.Z>-rc.N` is cut from a tree whose VERSION file ALREADY
       # reads the GA value `X.Y.Z` — the `-rc.N` pre-release suffix
       # exists only in the tag name, never in the VERSION file. (The
       # 24h RC-hold gate below encodes the same convention: it derives
       # the RC tag family `v${VERSION}-rc.*` from the GA VERSION.)
       # The old comparison (`FILE != TAG#v`) therefore hard-failed
       # every RC tag's own release run: `v1.0.1-rc.1` vs
       # `VERSION=1.0.1`. Fix: strip a trailing `-rc.<digits>` from the
       # tag before comparing. GA tags are unaffected (nothing to
       # strip); a wrong-version RC (`v1.0.2-rc.1` on `VERSION=1.0.1`)
       # still hard-fails.
       # -----------------------------------------------------------------
       - name: Assert VERSION matches tag
         run: |
           set -euo pipefail
           TAG="${GITHUB_REF_NAME}"
           FILE="$(tr -d '[:space:]' < VERSION)"
           EXPECTED="${TAG#v}"
           BASE="${EXPECTED%-rc.[0-9]*}"
           if [[ "$FILE" != "$BASE" ]]; then
             echo "::error::VERSION file ('$FILE') does not match tag ('$TAG' → expected '$BASE')"
             exit 1
           fi
           if [[ "$EXPECTED" != "$BASE" ]]; then
             echo "OK: VERSION=$FILE matches RC tag=$TAG (compared against base '$BASE' after stripping the -rc.N pre-release suffix)"
           else
             echo "OK: VERSION=$FILE matches tag=$TAG"
           fi
 
+      # -----------------------------------------------------------------
+      # PLAN-166 W1 item 2 (F3, ADR-155-AMEND-1 §5, Forma A (ii)) — the
+      # framework version marker `.claude/.framework-version` is a TRACKED
+      # one-line file, byte-identical to VERSION (the version bump writes
+      # it as a site; verify-counts.sh cross-checks it). This assert is
+      # deliberately UNCONDITIONAL and fail-closed: a missing marker in a
+      # release checkout means the ceremony that introduced it was
+      # reverted or the bump skipped a site — either way the tag must not
+      # ship. Kept NEXT TO the VERSION↔tag assert above so the whole
+      # version-consistency family lives in one place (same convention as
+      # the plugin-manifest step below).
+      # -----------------------------------------------------------------
+      - name: Assert framework-version marker matches VERSION
+        run: |
+          set -euo pipefail
+          FILE="$(tr -d '[:space:]' < VERSION)"
+          if [[ ! -f .claude/.framework-version ]]; then
+            echo "::error::.claude/.framework-version is missing — it is a tracked file (PLAN-166 F3 / ADR-155-AMEND-1); a release checkout without it must not ship"
+            exit 1
+          fi
+          MARKER="$(tr -d '[:space:]' < .claude/.framework-version)"
+          if [[ "$MARKER" != "$FILE" ]]; then
+            echo "::error::.claude/.framework-version ('$MARKER') does not match VERSION ('$FILE') — the marker is byte-identical to VERSION by contract (Forma A (ii), fail-closed)"
+            exit 1
+          fi
+          echo "OK: .claude/.framework-version=$MARKER matches VERSION"
+
       # -----------------------------------------------------------------
       # PLAN-153 Wave B item 5 (e) — version↔plugin-manifest sync, kept
       # NEXT TO the VERSION↔tag assert above so the whole
       # version-consistency family lives in one place.
       #
       # `.claude-plugin/{plugin.json,marketplace.json}` are generated by
       # `build-plugin.py` (Wave B item 6). Until item 6 lands, the
       # manifests do not exist and this step passes with a ::notice
       # (self-arming: the equality checks become enforcing the moment
       # the manifests appear in the tree — no workflow re-edit needed).
       # `marketplace.json`'s schema is owned by build-plugin.py, so we
       # assert on EVERY nested `version` field found rather than
       # hardcoding one JSON path.
       # -----------------------------------------------------------------
       - name: Assert plugin manifest versions match VERSION
         run: |
           set -euo pipefail
           FILE="$(tr -d '[:space:]' < VERSION)"
           if [[ ! -f .claude-plugin/plugin.json ]]; then
             echo "::notice::.claude-plugin/plugin.json not present yet (PLAN-153 Wave B item 6) — sync check self-arms once it lands"
             exit 0
           fi
           PLUGIN_V=$(jq -r '.version // empty' .claude-plugin/plugin.json)
           if [[ "$PLUGIN_V" != "$FILE" ]]; then
             echo "::error::.claude-plugin/plugin.json version ('$PLUGIN_V') does not match VERSION ('$FILE')"
             exit 1
           fi
           echo "OK: plugin.json version=$PLUGIN_V matches VERSION"
           if [[ -f .claude-plugin/marketplace.json ]]; then
             BAD=0
             while IFS= read -r v; do
               [[ -z "$v" ]] && continue
               if [[ "$v" != "$FILE" ]]; then
                 echo "::error::.claude-plugin/marketplace.json carries version '$v' != VERSION ('$FILE')"
                 BAD=1
               fi
             done < <(jq -r '.. | objects | .version? // empty' .claude-plugin/marketplace.json)
             if [[ "$BAD" -ne 0 ]]; then
               exit 1
             fi
             echo "OK: every marketplace.json version field matches VERSION"
           else
             echo "::notice::.claude-plugin/marketplace.json not present — skipping"
           fi
 
       # -----------------------------------------------------------------
       # F5 — RC-hold / staleness waiver SUNSET assertion.
       #
       # The pre-GA waivers in .claude/governance/governance-waivers.yaml
       # are honest ONLY while the project is pre-GA (adopter_count=0).
       # Every existing rc_hold/workflow_staleness entry is a 1.x version
       # carrying "Pre-GA ... adopter_count=0". To stop that 100%-waiver
       # escape from silently following the project into GA, this step
       # FAILS the release the moment any waiver `version` parses >= the
       # configured FIRST_GA floor. The floor is the first version at which
       # the framework intends to claim GA / publish to adopters; per
       # ADR-073 the next major (v2.0.0) is the documented GA/breaking
       # boundary, so 2.0.0 is the mechanical sunset. After the first real
       # adopter ships, lower FIRST_GA (or empty the waiver lists) so the
       # ADR-007 RC-hold + 14-day staleness gates resume real enforcement.
       #
       # Today (max waiver 1.0.0 < 2.0.0) this passes; it is a tripwire,
       # not a behavior change for the current pre-GA train.
       #
       # `-rc.N` pre-release suffixes are stripped before comparison: RC
       # tags forensically short-circuit the hold gate (see below), so an
       # rc.* waiver is never an enforcement bypass on its own.
       # -----------------------------------------------------------------
       - name: Assert no waiver has reached the GA sunset floor
         env:
           # First version at which pre-GA waivers are no longer honest.
           # Bump DOWN (or empty the waiver lists) once an adopter ships.
           FIRST_GA: "2.0.0"
         run: |
           set -euo pipefail
           WAIVER_FILE=".claude/governance/governance-waivers.yaml"
           if [[ ! -f "$WAIVER_FILE" ]]; then
             echo "OK: no waiver file present — nothing to sunset"
             exit 0
           fi
@@ -624,160 +651,297 @@ jobs:
       # CEO_PAIR_RAIL_VERDICT_OPTIONAL=1 transition mode. The replacement
       # binds to parent_sha — the commit the verdict was generated
       # against (parent of the verdict-file commit). That value is
       # observable + immutable when the verdict is authored.
       #
       # Step 15 asserts:
       #   - verdict.parent_sha == git log -n1 --format=%H -- <verdict-file>^
       #   - verdict.release_tag == ${GITHUB_REF_NAME}  (replay defense)
       #   - verdict.tool_versions.codex_cli in codex-cli-pin.txt range
       #   - verdict.tool_versions.codex_payload_sha256 (+ codex_target_triple)
       #     == codex-cli-pin-manifest.json payloads[<triple>].sha256
       #     (ADR-182 payload pin — the sha of the NATIVE codex payload,
       #     not the npm JS launcher; PLAN-163 T5.2. The legacy
       #     codex_cli_binary_sha256 launcher pin is retained only for
       #     pre-ADR-182 tags; its pin file is a comment-only tombstone,
       #     which the validator treats as "no launcher pin".)
       #   - verdict generated_at within 24h (TTL per ADR-103)
       #   - inputs_hash deterministically recomputed via inputs-hash-manifest.txt
       #   - GPG signature present + verifies against owner.asc
       #
       # continue-on-error: ONLY when CEO_PAIR_RAIL_VERDICT_OPTIONAL=1 env
       # explicitly set (e.g. legacy rc tags pre-verdict-rollout). Default is
       # hard-block on any validator failure.
       - name: Validate pair-rail verdict (PLAN-081 Phase 6-bis step 15)
         env:
           # Codex iter-8 P1 fix: source the env var from a repository
           # variable so the `continue-on-error` expression has something
           # to evaluate against. Owner sets via `gh variable set
           # CEO_PAIR_RAIL_VERDICT_OPTIONAL --body 1` for transition mode
           # (e.g. legacy v1.16.0-era verdicts shipping only commit_sha:);
           # unset / 0 = hard-block (default).
           CEO_PAIR_RAIL_VERDICT_OPTIONAL: ${{ vars.CEO_PAIR_RAIL_VERDICT_OPTIONAL || '0' }}
         continue-on-error: ${{ vars.CEO_PAIR_RAIL_VERDICT_OPTIONAL == '1' }}
         run: |
           set -euo pipefail
           VERDICT_FILE=".claude/governance/pair-rail-verdict-${GITHUB_REF_NAME}.md"
           if [ ! -f "$VERDICT_FILE" ]; then
             if [ "${CEO_PAIR_RAIL_VERDICT_OPTIONAL:-0}" = "1" ]; then
               echo "::notice::no verdict file at $VERDICT_FILE; CEO_PAIR_RAIL_VERDICT_OPTIONAL=1 → skipping"
               exit 0
             fi
             echo "::error::verdict file missing at $VERDICT_FILE — step 15 blocks release"
             exit 1
           fi
           # S104 redesign: resolve PARENT_SHA = parent of the verdict-file
           # commit. The tag commit (${GITHUB_SHA}) is what we're releasing,
           # and the verdict file at $VERDICT_FILE either:
           #   (a) was committed in the tag commit itself → parent = ${GITHUB_SHA}^
           #   (b) was committed earlier (multi-commit prep) → parent = git log of file
           # We use (b)'s general form: find the commit that introduced the
           # current verdict file, then take its parent. This handles both
           # single-commit-with-verdict and multi-commit-prep flows.
           VERDICT_FILE_COMMIT=$(git log -n1 --format=%H -- "$VERDICT_FILE")
           if [ -z "$VERDICT_FILE_COMMIT" ]; then
             echo "::error::cannot resolve commit for $VERDICT_FILE — step 15 fails"
             exit 1
           fi
           PARENT_SHA=$(git rev-parse "${VERDICT_FILE_COMMIT}^" 2>/dev/null || echo "")
           if [ -z "$PARENT_SHA" ]; then
             echo "::error::cannot resolve parent of $VERDICT_FILE_COMMIT — step 15 fails"
             exit 1
           fi
           echo "::notice::S104 bind: VERDICT_FILE_COMMIT=$VERDICT_FILE_COMMIT, PARENT_SHA=$PARENT_SHA"
           # When transition mode is on, allow parent_sha mismatch (skip bind)
           # by passing empty string. Default is hard-bind on PARENT_SHA.
           PARENT_SHA_ARG="$PARENT_SHA"
           if [ "${CEO_PAIR_RAIL_VERDICT_OPTIONAL:-0}" = "1" ]; then
             PARENT_SHA_ARG=""
           fi
           python3 .github/scripts/validate-pair-rail-verdict.py \
             --verdict-file "$VERDICT_FILE" \
             --parent-sha "$PARENT_SHA_ARG" \
             --release-tag "${GITHUB_REF_NAME}" \
             --max-age-hours 24 \
             --recompute-inputs-hash \
             --codex-cli-pin-file .claude/governance/codex-cli-pin.txt \
             --codex-cli-binary-sha256-file .claude/governance/codex-cli-binary-sha256.txt \
             --codex-pin-manifest-file .claude/governance/codex-cli-pin-manifest.json \
             --inputs-hash-paths-file .claude/governance/pair-rail-inputs-hash-manifest.txt
 
+      # ==========================================================
+      # PLAN-166 W1-B — verdict delta + ancestry gate (F2 server side)
+      # ==========================================================
+      # Re-pass findings r15 + r17 + r18 (PLAN-166), debate r3 scoped VETO.
+      #
+      # WHY A SEPARATE STEP: the step-15 neighbourhood above carries two
+      # escape hatches keyed to CEO_PAIR_RAIL_VERDICT_OPTIONAL —
+      # `continue-on-error:` on the step itself, and an empty
+      # `--parent-sha ""` bind (the validator only binds the field when
+      # args.parent_sha is non-empty). Inheriting that neighbourhood would
+      # inherit the switch. This step therefore:
+      #   - carries NO continue-on-error;
+      #   - FAILS CLOSED when CEO_PAIR_RAIL_VERDICT_OPTIONAL=1: in that
+      #     mode step 15 skipped the parent_sha bind, so the anchor these
+      #     asserts hang off was never validated — there is no transition
+      #     mode here, by design;
+      #   - re-derives and re-binds parent_sha ITSELF (non-empty, 40-hex,
+      #     equal to the verdict's `parent_sha:` read with the SAME parser
+      #     the local tag guard uses) — independent of step 15's outcome,
+      #     which also closes the legacy commit_sha fallback (the
+      #     validator downgrades a missing parent_sha to an ADVISORY when
+      #     a legacy commit_sha is present; this step does not);
+      #   - reuses .claude/scripts/local/_release_tag_guard.py for the
+      #     delta decision — the module marks itself as the reference
+      #     implementation; the semantics are NEVER re-implemented in
+      #     bash (single source of the decision logic);
+      #   - asserts ancestry on origin/main of BOTH the reviewed parent
+      #     AND GITHUB_SHA itself (r18: parent-only lets the
+      #     tag-without-push scenario — verdict V over parent P, tag
+      #     pushed, V never reaches main — pass with P ancestral and V
+      #     orphaned).
+      #
+      # THE INVARIANT (one sentence): nothing landed after what the
+      # re-pass reviewed, other than the verdict for THIS tag and the
+      # evidence it pins by name AND content (sha256 of MANIFEST.sha256
+      # in the signed verdict + `shasum -c` over the evidence set).
+      #
+      # PINNED ORDER (asserted structurally by the W1B* classes of
+      # test_release_workflow_asserts.py, WaveB5 pattern):
+      #   Verify tag GPG signature → Validate pair-rail verdict →
+      #   delta → ancestry.
+      # Do not reorder, do not merge into step 15.
+      - name: Verify verdict delta + ancestry (fail-closed)
+        env:
+          CEO_PAIR_RAIL_VERDICT_OPTIONAL: ${{ vars.CEO_PAIR_RAIL_VERDICT_OPTIONAL || '0' }}
+        run: |
+          set -euo pipefail
+          # (0) No transition mode: with the var on, the parent_sha bind
+          # upstream was skipped — refuse to certify against an
+          # unvalidated anchor. Fail closed, loudly.
+          if [ "${CEO_PAIR_RAIL_VERDICT_OPTIONAL}" = "1" ]; then
+            echo "::error::CEO_PAIR_RAIL_VERDICT_OPTIONAL=1 is set, but the delta+ancestry gate has no transition mode — it fails closed by design (PLAN-166 debate r3). Unset the repo variable (gh variable delete CEO_PAIR_RAIL_VERDICT_OPTIONAL) and re-run."
+            exit 1
+          fi
+          TAG="${GITHUB_REF_NAME}"
+          VERDICT_FILE=".claude/governance/pair-rail-verdict-${TAG}.md"
+          if [ ! -f "$VERDICT_FILE" ]; then
+            echo "::error::no signed verdict at $VERDICT_FILE — the delta+ancestry gate has no optional mode; the re-pass verdict for THIS tag must be committed on the tagged tree."
+            exit 1
+          fi
+          # (1) Checkout sanity: every assert below anchors on HEAD, so
+          # HEAD must BE the tagged commit this run is about.
+          HEAD_SHA="$(git rev-parse HEAD)"
+          if [ "$HEAD_SHA" != "${GITHUB_SHA}" ]; then
+            echo "::error::checkout HEAD ($HEAD_SHA) != GITHUB_SHA (${GITHUB_SHA}) — refusing to assert against the wrong tree"
+            exit 1
+          fi
+          # (2) Independent parent_sha bind — non-empty by construction,
+          # controlled by no variable. Same derivation as step 15 (parent
+          # of the commit that introduced the verdict file); the verdict
+          # field is read with the SAME parser the local tag guard uses
+          # (_parse_verdict), so two readers of the same signed file
+          # cannot disagree about what it says.
+          VERDICT_FILE_COMMIT="$(git log -n1 --format=%H -- "$VERDICT_FILE")"
+          if [ -z "$VERDICT_FILE_COMMIT" ]; then
+            echo "::error::cannot resolve the commit that introduced $VERDICT_FILE — refusing an empty bind"
+            exit 1
+          fi
+          PARENT_SHA="$(git rev-parse "${VERDICT_FILE_COMMIT}^" 2>/dev/null || echo "")"
+          if [ -z "$PARENT_SHA" ]; then
+            echo "::error::cannot resolve parent of ${VERDICT_FILE_COMMIT} — refusing an empty bind"
+            exit 1
+          fi
+          python3 - "$VERDICT_FILE" "$PARENT_SHA" <<'PYBIND'
+          import importlib.util
+          import io
+          import re
+          import sys
+
+          verdict_path, expected = sys.argv[1], sys.argv[2]
+          if not re.match(r"\A[0-9a-f]{40}\Z", expected):
+              sys.exit("FAIL: derived parent %r is not a 40-hex SHA" % expected)
+          spec = importlib.util.spec_from_file_location(
+              "release_tag_guard", ".claude/scripts/local/_release_tag_guard.py"
+          )
+          mod = importlib.util.module_from_spec(spec)
+          spec.loader.exec_module(mod)
+          with io.open(verdict_path, encoding="utf-8") as fh:
+              fields = mod._parse_verdict(fh.read())
+          declared = fields.get("parent_sha")
+          if declared != expected:
+              sys.exit(
+                  "FAIL: verdict parent_sha %r != parent of the verdict-file "
+                  "commit (%s) — the anchor was not validated with a "
+                  "non-empty bind; a legacy commit_sha fallback does NOT "
+                  "count here." % (declared, expected)
+              )
+          print("  ok   parent_sha bind: %s (derived independently of step 15)" % expected)
+          PYBIND
+          # (3) DELTA (r15): git diff <reviewed parent>..<tag commit>
+          # must be contained in the CLOSED set pinned in the signed
+          # verdict — exact names per tag (never the pair-rail-verdict-*
+          # wildcard, never repass-<N>/**), set equality against the
+          # evidence MANIFEST.sha256, AND content equality (the verdict
+          # pins the manifest's sha256; the guard runs `shasum -c` over
+          # it). Any extra path = FAIL. Decision logic lives in the local
+          # tag guard module — reused, never re-implemented in bash.
+          python3 .claude/scripts/local/_release_tag_guard.py delta \
+            --repo . --tag "$TAG"
+          # (4) ANCESTRY (r17+r18): both the reviewed parent AND the
+          # tagged commit itself must be ancestors of origin/main. The
+          # module's ancestry subcommand judges HEAD (== GITHUB_SHA,
+          # asserted in (1)) after a FAIL-CLOSED fetch of origin/main —
+          # a failed fetch is a stop, never a stale-ref approval. The
+          # reviewed parent is then judged against the same freshly
+          # fetched ref.
+          python3 .claude/scripts/local/_release_tag_guard.py ancestry \
+            --repo . --remote origin --branch main
+          if git merge-base --is-ancestor "$PARENT_SHA" origin/main; then
+            echo "  ok   reviewed parent $PARENT_SHA is an ancestor of origin/main"
+          else
+            RC=$?
+            echo "::error::reviewed parent $PARENT_SHA is not on origin/main (merge-base exit $RC) — the verdict is anchored on a commit main never saw (tag-without-push / orphan-verdict scenario, r17+r18)"
+            exit 1
+          fi
+          echo "OK: verdict delta + ancestry asserts all green for $TAG"
+
   publish-release:
     name: Publish GitHub Release + assets
     needs: release-gate
     runs-on: ubuntu-latest
     permissions:
       contents: write
     steps:
       - name: Checkout tag
         # SHA-pinned: actions/checkout@v6.0.2
         uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd
         with:
           fetch-depth: 0
       - name: Setup Python 3.11
         # SHA-pinned: actions/setup-python@v6.2.0
         uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405
         with:
           python-version: "3.11"
       - name: Compute install.sh.sha256 (body excluding self-SHA trailer)
         run: |
           set -euo pipefail
           FILE="scripts/install.sh"
           HASH=$(awk 'NR==FNR{n++; next} FNR < n' "$FILE" "$FILE" | sha256sum | awk '{print $1}')
           printf '%s  install.sh\n' "$HASH" > install.sh.sha256
           echo "install.sh.sha256 = $HASH"
       - name: Generate CycloneDX SBOM
         run: |
           set -euo pipefail
           python3 .claude/scripts/generate-sbom.py --output sbom.cyclonedx.json
       # -----------------------------------------------------------------
       # PLAN-153 Wave B item 5 (d) — templatized release notes.
       # Closes PLAN-152 §Deferred `release-notes-hardcoded-first-release`:
       # the notes string used to hardcode a v1.0.0-only launch sentence,
       # stale for every later tag. Notes are now rendered from
       # `.github/release-notes-template.md` with {{TAG}} / {{VERSION}} /
       # {{BASE_VERSION}} interpolation (BASE_VERSION = VERSION with any
       # -rc.N suffix stripped, so RC notes point at the GA CHANGELOG
       # section). Fail-closed on a missing template or an unrendered
       # placeholder.
       # -----------------------------------------------------------------
       - name: Render release notes from template
         run: |
           set -euo pipefail
           TAG="${GITHUB_REF_NAME}"
           VERSION="${TAG#v}"
           BASE_VERSION="${VERSION%-rc.[0-9]*}"
           TEMPLATE=".github/release-notes-template.md"
           if [[ ! -f "$TEMPLATE" ]]; then
             echo "::error::release-notes template missing at $TEMPLATE"
             exit 1
           fi
           sed -e "s/{{TAG}}/${TAG}/g" \
               -e "s/{{VERSION}}/${VERSION}/g" \
               -e "s/{{BASE_VERSION}}/${BASE_VERSION}/g" \
               "$TEMPLATE" > release-notes.md
           if grep -q '{{' release-notes.md; then
             echo "::error::unrendered placeholders remain in release-notes.md"
             exit 1
           fi
           echo "Rendered release notes:"
           cat release-notes.md
 
       # -----------------------------------------------------------------
       # PLAN-153 Wave B item 5 (b) — idempotent release creation
       # (`gh release view || gh release create`). A re-run of this job
       # (workflow re-run, transient asset-upload failure) must not fail
       # on an existing release: if the release already exists we
       # re-sync the assets with `--clobber` and succeed-as-noop —
       # covering the partial-failure case where `gh release create`
       # made the release but died mid-asset-upload.
       # RC tags (which reach this job since the RC-aware VERSION gate
       # fix) are marked --prerelease so they never show as "Latest".
       # NOTE: bash arrays are fine here — this runs on ubuntu-latest
       # (bash 5); the bash-3.2 house rule applies to adopter-machine
       # scripts (install.sh), and release.yml already uses arrays in
       # the weekly-workflow gate (WORKFLOWS=(...)).
       # -----------------------------------------------------------------
       - name: Create GitHub Release with assets (idempotent)
         env:
           GH_TOKEN: ${{ github.token }}
         run: |

exec
/bin/zsh -lc 'git diff --no-ext-diff --unified=80 -- ".github/workflows/smoke-install.yml"' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
diff --git a/.github/workflows/smoke-install.yml b/.github/workflows/smoke-install.yml
index e1317fb..5794f0b 100644
--- a/.github/workflows/smoke-install.yml
+++ b/.github/workflows/smoke-install.yml
@@ -1,127 +1,242 @@
 name: Smoke Install
 
 on:
   pull_request:
     paths:
       - "scripts/install.sh"
       - "scripts/upgrade.sh"
       # PLAN-161 (CI wiring): upgrade oracles + the manifest lib they
       # exercise — keep BOTH filter lists (pull_request + push) in sync.
       - "scripts/_framework_manifest_set.sh"
+      # The ownership + parity e2e call _hash_file/_hash_stdin from here, and
+      # this workflow is their ONLY CI execution — without the helper in the
+      # filter, a PR touching only it skips the gate entirely (codex W1
+      # round 10, P2: the "red gate nobody runs" class, one level deeper).
+      - "scripts/_hash_lib.sh"
       - "scripts/tests/test-upgrade-dryrun-identity.sh"
       - "scripts/tests/test-upgrade-exclusions.sh"
       - "scripts/tests/smoke-install.sh"
+      # PLAN-166 F4 (OQ-4): the install/upgrade parity e2e and its classifier.
+      # The finding this closes is "a red gate nobody runs" (5th instance) --
+      # an unwired test is the same as no test.
+      - "scripts/tests/test-install-upgrade-parity-e2e.sh"
+      - "scripts/tests/_parity_classify.py"
+      # PLAN-166 F3 (ADR-155-AMEND-1): delivery-record ownership e2e —
+      # scripts/tests/*.sh runs ONLY in this workflow (same r11/r20 wiring
+      # rule as the parity e2e above).
+      - "scripts/tests/test-upgrade-spec-ownership.sh"
       - "templates/**"
-      - "SPEC/v1/install-cli.md"
+      # Widened from SPEC/v1/install-cli.md: SPEC/v1 is delivered by install.sh
+      # and (until F3) by nothing in upgrade.sh, so ANY SPEC/v1 change is a
+      # parity event, not just the CLI contract doc.
+      - "SPEC/v1/**"
+      # PLAN-166 F4 wiring (r11/r20): scripts/tests/*.sh runs ONLY here, so a
+      # PR touching just one of these would otherwise skip the regression.
+      - "scripts/doctor.sh"
+      - ".claude/.framework-version"
+      - ".claude/scripts/check-framework-updates.sh"
       - ".github/workflows/smoke-install.yml"
       # PLAN-006 Phase 1 (Sprint 6): Adapter Layer migration changes
       # install-time expectations (hook import paths, contract). Scope
       # broadened for the sprint; narrow back post-Sprint-7 closeout.
       - ".claude/hooks/**"
   push:
     branches:
       - main
     paths:
+      # KEEP IDENTICAL to the pull_request list above. The two had already
+      # drifted (push was missing SPEC/v1 and this workflow file); PLAN-166 F4
+      # re-syncs them, because a filter that fires on the PR and not on the
+      # merge is a gate with a hole in it.
       - "scripts/install.sh"
       - "scripts/upgrade.sh"
       - "scripts/_framework_manifest_set.sh"
+      - "scripts/_hash_lib.sh"
       - "scripts/tests/test-upgrade-dryrun-identity.sh"
       - "scripts/tests/test-upgrade-exclusions.sh"
       - "scripts/tests/smoke-install.sh"
+      - "scripts/tests/test-install-upgrade-parity-e2e.sh"
+      - "scripts/tests/_parity_classify.py"
+      - "scripts/tests/test-upgrade-spec-ownership.sh"
       - "templates/**"
+      - "SPEC/v1/**"
+      - "scripts/doctor.sh"
+      - ".claude/.framework-version"
+      - ".claude/scripts/check-framework-updates.sh"
+      - ".github/workflows/smoke-install.yml"
       - ".claude/hooks/**"
 
 concurrency:
   group: smoke-install-${{ github.ref }}
   cancel-in-progress: true
 
 jobs:
   smoke:
     # PLAN-012 Phase 2 CEO_SOTA_DISABLE parity.
     if: vars.CEO_SOTA_DISABLE != '1'
     runs-on: ubuntu-latest
     # PLAN-161: 5 -> 8 — headroom for the two upgrade oracles (each runs
     # full install + upgrade legs against fixture adopter repos).
-    timeout-minutes: 8
+    # PLAN-166 F4: 8 -> 20. MEASURED, not guessed. The parity e2e runs 2 full
+    # install legs + 1 upgrade leg PER ceremony mode, and the positive control
+    # runs the same again with a planted divergence: 12 install/upgrade
+    # operations added to this job. Local wall time (Darwin arm64, 16 cores,
+    # 2026-08-05): gate 122s + control 118s = 240s. A 2-core ubuntu-latest
+    # runner is the usual 2-3x slower, i.e. 8-12 min of NEW work on top of the
+    # ~5 min this job already spent. 15 would sit inside the noise band, and
+    # the perf-gate N=20 flake (PLAN-159) was exactly that mistake. Re-tighten
+    # once real CI runs give a p95.
+    # PLAN-166 F3 (assembler): 20 -> 25. The spec-ownership e2e adds 4 more
+    # installs + 3 upgrades (S1-S8; ~3-4 min local per the W1-C measurement),
+    # i.e. up to ~8-10 more CI minutes at the same 2-3x factor. Same
+    # anti-flake sizing rule as the F4 bump above.
+    timeout-minutes: 25
     permissions:
       contents: read
     steps:
       - name: Checkout
         # SHA-pinned (Sprint 7 Dependabot bump): actions/checkout@v6.0.2
         uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd
         with:
           fetch-depth: 1
 
+      # PLAN-166 F4: the parity e2e's historical leg installs from a PINNED
+      # TAG. `fetch-depth: 1` produces a checkout with NO tags, so the pin
+      # would not resolve and the gate would die before comparing a single
+      # tree - "it passes on my clone" is precisely the hole this test exists
+      # to close. The pin is READ FROM THE TEST (--print-pin) so the workflow
+      # never becomes a second copy of that truth.
+      - name: Fetch the parity pin tag
+        run: |
+          set -euo pipefail
+          PIN="$(bash scripts/tests/test-install-upgrade-parity-e2e.sh --print-pin)"
+          echo "parity historical pin: $PIN"
+          git fetch --no-tags --depth 1 origin "+refs/tags/$PIN:refs/tags/$PIN"
+          git rev-parse --verify "refs/tags/$PIN^{commit}"
+
       - name: Setup Python 3.11
         # SHA-pinned (Sprint 7 Dependabot bump): actions/setup-python@v6.2.0
         uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405
         with:
           python-version: "3.11"
 
       - name: Install jq (for settings.json merge)
         run: |
           set -euo pipefail
           if ! command -v jq >/dev/null 2>&1; then
             sudo apt-get update -qq
             sudo apt-get install -y -qq jq
           fi
           jq --version
 
       - name: Run smoke install
         run: |
           set -euo pipefail
           bash scripts/tests/smoke-install.sh
 
       # PLAN-161 upgrade oracles (green only once the U1/U2/U3 upgrade.sh
       # fixes are in-tree — land atomically with them).
       - name: Upgrade oracle — --dry-run identity (U1)
         run: |
           set -euo pipefail
           bash scripts/tests/test-upgrade-dryrun-identity.sh
 
       - name: Upgrade oracle — exclusion parity + opt-in purge (U2/U3)
         run: |
           set -euo pipefail
           bash scripts/tests/test-upgrade-exclusions.sh
 
       # WS4-user-ceremony-leg
       - name: Install with --ceremony user (governance rc=0 + no out-of-.claude writes)
         run: |
           set -euo pipefail
           U="$(mktemp -d)"
           ( cd "$U" && git init -q )
           CEO_INSTALL_SKIP_SELF_SHA=1 CEO_RAG_INSTALL_PROMPT=0 \
             bash scripts/install.sh "$U" --ceremony user
           echo '--- validate-governance.sh (user) ---'
           ( cd "$U" && bash .claude/scripts/validate-governance.sh )
           echo '--- assert only .claude/ at top level ---'  # WS4-sc2010-glob
           extra=""
           for _e in "$U"/* "$U"/.[!.]* "$U"/..?*; do
             [ -e "$_e" ] || continue
             _b="$(basename "$_e")"
             case "$_b" in .claude|.git) continue ;; esac
             extra="$extra $_b"
           done
           if [ -n "$extra" ]; then
             echo "::error::--ceremony user wrote outside .claude/:$extra"
             exit 1
           fi
           echo 'user-ceremony leg: PASS'
 
+      # PLAN-166 F4 (OQ-4) - install/upgrade parity on the RESULTING TREES,
+      # per ceremony mode. NO continue-on-error, deliberately: the assertion
+      # this replaces was dead twice over (tautological AND wired into no
+      # workflow), and an escape hatch here would reinstate exactly that.
+      # Exit 2 (KNOWN-OPEN) is a FAILURE too - it NAMES the outstanding
+      # PLAN-166 W1 prerequisites instead of skipping them silently.
+      - name: Install/upgrade parity e2e (maintainer + user ceremony)
+        run: |
+          set -euo pipefail
+          bash scripts/tests/test-install-upgrade-parity-e2e.sh
+
+      # Control of the control (AC-4). With ONE backup_and_replace line deleted
+      # from a COPY of upgrade.sh, the gate above must come back RED in EVERY
+      # ceremony mode. rc must be exactly 1: rc 0/2 means the gate went blind,
+      # rc 9 means the plant stopped biting (vacuous control). Both fail here.
+      # This step MUST stay AFTER the plain gate: if the un-planted run were
+      # already fatal, rc=1 here would prove nothing about the plant.
+      - name: Install/upgrade parity - positive control (planted divergence)
+        run: |
+          set -uo pipefail
+          rc=0
+          bash scripts/tests/test-install-upgrade-parity-e2e.sh \
+            --positive-control > /tmp/parity-control.log 2>&1 || rc=$?
+          if [ "$rc" -ne 1 ]; then
+            cat /tmp/parity-control.log
+            echo "::error::parity positive control returned rc=$rc, expected 1 - the planted install/upgrade divergence did NOT turn the gate red, so the gate above proves nothing"
+            exit 1
+          fi
+          # Second factor, LOAD-BEARING (re-pass closure): under `set -uo
+          # pipefail` (no -e) a non-matching grep would NOT fail the step, so
+          # an rc=1 from a failure UNRELATED to the plant (log with none of
+          # the plant markers) would pass — the registered-vacuous class
+          # (S292) this step exists to close. Demand plant evidence or fail.
+          grep -E "PLANTED|per-mode verdicts|positive control:" /tmp/parity-control.log || {
+            cat /tmp/parity-control.log
+            echo "::error::rc=1 but the log carries no PLANTED/per-mode-verdict evidence - the control went red for an unrelated reason, which proves nothing about the plant (vacuous control)"
+            exit 1
+          }
+          echo "positive control OK: planted divergence -> exit 1 in every ceremony mode"
+
+      # PLAN-166 F3 (ADR-155-AMEND-1, AC-3) — delivery-record ownership of
+      # the three conditional framework surfaces (SPEC/v1, root PROTOCOL.md,
+      # .claude/.framework-version) across install -> upgrade -> doctor ->
+      # updater. Scenarios S1-S8 incl. the forced-refresh route (S2), the
+      # legacy ADOPTER-FORK preserve (S4) and the marker-first updater
+      # regression (S6). Same wiring rationale as the parity e2e above:
+      # scripts/tests/*.sh runs ONLY here — unwired = no test. NO
+      # continue-on-error, deliberately.
+      - name: Upgrade SPEC/marker delivery-record ownership (S1-S8)
+        run: |
+          set -euo pipefail
+          bash scripts/tests/test-upgrade-spec-ownership.sh
+
       - name: Assert npx/npm shim contract (if present)
         # Phase 4 deliverable; skip if directory missing
         run: |
           set -euo pipefail
           if [[ -d "npm" ]]; then
             # Check no runtime deps
             if [[ -f npm/package.json ]]; then
               deps=$(jq '.dependencies // {} | length' npm/package.json)
               if [[ "$deps" -ne 0 ]]; then
                 echo "::error::ceo-orchestration must ship with 0 runtime deps (got $deps)"
                 exit 1
               fi
               echo "OK: npm shim has zero runtime dependencies"
             fi
           else
             echo "npm/ shim not yet present — skipping"
           fi

exec
/bin/zsh -lc 'git diff --no-ext-diff --unified=80 -- "scripts/tests/_parity_classify.py"' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
diff --git a/scripts/tests/_parity_classify.py b/scripts/tests/_parity_classify.py
index d8809bd..b1f86bd 100644
--- a/scripts/tests/_parity_classify.py
+++ b/scripts/tests/_parity_classify.py
@@ -80,202 +80,167 @@ from typing import Dict, List, Optional, Tuple
 SKIP_DIRS = (".git", ".claude.bak", "__pycache__")
 SKIP_SUFFIX = (".pyc",)
 
 # ---------------------------------------------------------------------------
 # ACCEPTED divergence — generated per-install or adopter-owned by contract.
 # Every entry carries the AUTHORITY for the claim, not a shrug. These are
 # printed as their own census block on every run so the list cannot grow
 # quietly.
 #   (regex, applies-to-modes or None for all, reason)
 # ---------------------------------------------------------------------------
 ACCEPTED: List[Tuple[str, Optional[str], str]] = [
     (
         r"^\.claude/\.install-manifest\.sha256$",
         None,
         "derived baseline manifest — regenerated by BOTH routes "
         "(_write_baseline_manifest); it is a hash OF the set under comparison, "
         "so comparing it would be circular",
     ),
     (
         r"^\.claude/\.install-state\.json$",
         None,
         "records the invocation itself (argv, timestamps, source sha, upgrade "
         "ops) — differs by construction between a fresh install and an "
         "install+upgrade; the `ceremony` field is asserted separately below",
     ),
     (
         r"^\.claude/settings\.json$",
         None,
         "install seeds it; upgrade does an ADDITIVE hook merge (PLAN-135 W2 H8) "
         "plus the 3-state baseline migration (PLAN-163 T5.4) and never "
         "clobbers — the two routes converge on keys, not on bytes",
     ),
     (
         r"^\.claude/agent-metrics\.md$",
         None,
         "adopter data — upgrade.sh header: 'Leaves CLAUDE.md, MEMORY.md, "
         ".claude/agent-metrics.md untouched'",
     ),
     (
         r"^(CLAUDE|MEMORY)\.md$",
         None,
         "seed-once adopter doc — same upgrade.sh preserve contract",
     ),
     (
         r"^\.gitignore$",
         None,
         "adopter-owned append-only surface. install.sh APPENDS marker-guarded "
         "blocks (install_posture_state_ignores, PLAN-165 CX-3); upgrade.sh has "
         "no append step, so an upgraded adopter never gets them. A REAL "
         "install-only delivery gap — accepted here (never fatal) only because "
         "the file is adopter-owned and must not be clobbered; reported every "
         "run so it stays visible",
     ),
     (
         r"^PROTOCOL\.md$",
         "maintainer",
         "generated pointer. install.sh substitutes the resolved SOURCE_DIR; "
         "upgrade.sh's _refresh_protocol_pointer emits the literal "
         "{{PROTOCOL_SOURCE}} placeholder. Body-only divergence, pre-existing "
         "asymmetry of the same pointer file",
     ),
     (
         r"^VERSION$",
         "maintainer",
         "BY DESIGN (PLAN-166 OQ-3 / ADR-155-AMEND-1): the upgrade must NOT "
         "touch the adopter's root VERSION — install_one is skip-if-exists, so "
         "in an adopter that owns a VERSION the framework never wrote there and "
         "backup_and_replace would TAKE the file (the verified S238 worst "
         "case). The framework's own version marker moves to "
         ".claude/.framework-version. Asserted positively below: B/VERSION must "
         "be byte-identical to the pinned source's VERSION (untouched), not "
         "merely different",
     ),
 ]
 
 # ---------------------------------------------------------------------------
 # KNOWN_OPEN — PLAN-166 W1 prerequisites. MANDATORY-FIRE (see module docstring).
 #   id, modes (None = all), class, regex, reason, unblocked_by
 # ---------------------------------------------------------------------------
 KNOWN_OPEN: List[Dict[str, Optional[str]]] = [
-    {
-        "id": "F3-spec-stale",
-        "modes": "maintainer",
-        "cls": "STALE",
-        "re": r"^SPEC/v1/",
-        "reason": (
-            "upgrade.sh delivers SPEC/v1 through NO surface: it is absent from "
-            "the backup_and_replace sequence AND from "
-            "_framework_target_entries(). An adopter upgrading v1.2 -> v1.3 "
-            "keeps the v1.2 contract — the trust boundary of the sentinel "
-            "unlock, +21 lines in this very release"
-        ),
-        "unblocked_by": (
-            "PLAN-166 W1 item 2 / OQ-3(a): forced-refresh route for SPEC/v1 in "
-            "upgrade.sh + delivery-record-gated entry in "
-            "_framework_target_entries() + INSTALL.md refresh list"
-        ),
-    },
-    {
-        "id": "F3-protocol-user-mode",
-        "modes": "user",
-        "cls": "ONLY_IN_B_OUTSIDE_CLAUDE",
-        "re": r"^PROTOCOL\.md$",
-        "reason": (
-            "upgrade.sh calls _refresh_protocol_pointer() UNCONDITIONALLY "
-            "(upgrade.sh:2441) and writes PROTOCOL.md at the repo ROOT. A "
-            "fresh `--ceremony user` install forbids exactly that "
-            "(install.sh:1876 gates install_protocol_pointer, and "
-            "smoke-install.yml's WS4 leg fails the build on any top-level "
-            "write outside .claude/). So `install --ceremony user` followed "
-            "later by an upgrade silently violates the guarantee the install "
-            "advertised. This is a latent adjacent bug that only a TREE "
-            "comparison exposes — not an allowlist case"
-        ),
-        "unblocked_by": (
-            "PLAN-166 W1 item 2 / OQ-3: ceremony-gate the protocol refresh in "
-            "upgrade.sh from the same .install-state.json read (own read, "
-            "independent of --no-replay)"
-        ),
-    },
+    # (empty — PLAN-166 W1 landed. F3-spec-stale and F3-protocol-user-mode
+    # were deleted IN the W1 ceremony commit, per the mandatory-fire
+    # contract above: a ledger can never outlive its bug. Add new entries
+    # here ONLY with a mandatory-fire reason + unblocked_by.)
 ]
 
+
 # Paths that must EXIST in both routes once W1 lands. Absent today, so each
 # reports as KNOWN-OPEN (class=expect-path) and holds the run at exit 2.
 # DELIBERATELY NOT mandatory-fire, unlike KNOWN_OPEN above: once the path
 # exists in both trees the entry goes quiet and remains as a PERMANENT
 # existence assert — it re-fires if either route ever stops delivering the
 # marker. No W1 deletion is required for these. Content freshness of a path
 # that IS present is not this list's job either: a present-but-stale marker
 # is caught by the main classification loop (STALE there is FATAL).
 EXPECT_PATHS: List[Dict[str, Optional[str]]] = [
     {
         "id": "F3-framework-version-marker",
         "modes": None,
         "path": ".claude/.framework-version",
         "reason": (
             "OQ-3 moves the framework's own version marker off the adopter's "
             "root VERSION and into .claude/.framework-version, as a TRACKED "
             "file of the framework repo written explicitly by BOTH install "
             "(install_one) and upgrade. Until it exists there is no surface on "
             "which install and upgrade can agree about which framework "
             "generation the adopter is running, and "
             "check-framework-updates.sh keeps resolving the stale root VERSION"
         ),
         "unblocked_by": "PLAN-166 W1 item 2 / OQ-3 (marker) + AC-3",
     },
 ]
 
 
 def _norm_bytes(data: bytes, subs: List[Tuple[bytes, bytes]]) -> bytes:
     for needle, repl in subs:
         if needle:
             data = data.replace(needle, repl)
     return data
 
 
 def _digest(path: str, subs: List[Tuple[bytes, bytes]]) -> Optional[str]:
     try:
         with open(path, "rb") as fh:
             data = fh.read()
     except (IOError, OSError):
         return None
     return hashlib.sha256(_norm_bytes(data, subs)).hexdigest()
 
 
 def _exec_bit(path: str) -> Optional[bool]:
     """True/False for the owner-exec bit; None when the path is unreadable."""
     try:
         return bool(os.stat(path).st_mode & 0o100)
     except OSError:
         return None
 
 
 def _walk(root: str) -> List[str]:
     out: List[str] = []
     for dirpath, dirnames, filenames in os.walk(root):
         dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
         for name in filenames:
             if name.endswith(SKIP_SUFFIX):
                 continue
             full = os.path.join(dirpath, name)
             out.append(os.path.relpath(full, root))
     out.sort()
     return out
 
 
 def _src_digest(root: str, rel: str, subs: List[Tuple[bytes, bytes]]) -> Optional[str]:
     """Source lookup: identity map first, then the templates/ map."""
     for candidate in (os.path.join(root, rel), os.path.join(root, "templates", rel)):
         digest = _digest(candidate, subs)
         if digest is not None:
             return digest
     return None
 
 
 def _matches(rel: str, pattern: str) -> bool:
     return re.search(pattern, rel) is not None
 
 
 def main() -> int:
     ap = argparse.ArgumentParser(description=__doc__)
     ap.add_argument("--a", required=True, help="route A tree (fresh install)")

exec
/bin/zsh -lc 'git diff --no-ext-diff --unified=80 -- "scripts/tests/test-upgrade-spec-ownership.sh"' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
diff --git a/scripts/tests/test-upgrade-spec-ownership.sh b/scripts/tests/test-upgrade-spec-ownership.sh
new file mode 100755
index 0000000..687db56
--- /dev/null
+++ b/scripts/tests/test-upgrade-spec-ownership.sh
@@ -0,0 +1,359 @@
+#!/usr/bin/env bash
+# scripts/tests/test-upgrade-spec-ownership.sh
+# PLAN-166 F3 (ADR-155-AMEND-1) — delivery-record ownership of the three
+# conditional framework surfaces (SPEC/v1, root PROTOCOL.md,
+# .claude/.framework-version) across install → upgrade → doctor → updater.
+#
+# AC-3 scenarios exercised:
+#   S1  maintainer fresh install: SPEC/v1 + PROTOCOL.md + marker DELIVERED
+#       and recorded in the baseline manifest; marker == source VERSION;
+#       delivered_* ops journaled in .install-state.json
+#   S2  2nd-upgrade FORCED route (r6 — the load-bearing fixture): baseline
+#       ALREADY contains SPEC/v1 records, SPEC edited locally => upgrade
+#       REPLACES it (backup in .claude.bak/<ts>/SPEC/v1) — the generic
+#       classified walk would have PRESERVED the edit; root VERSION
+#       sentinel is NOT touched (S238/ADR-155 class)
+#   S3  user-ceremony install + `upgrade --no-replay` (r9 MANDATORY):
+#       neither install nor upgrade creates SPEC/v1 or a root PROTOCOL.md
+#       (the ceremony is read by the replay-INDEPENDENT reader)
+#   S4  legacy ADOPTER-FORK (r20): baseline without SPEC records (v1.2-and-
+#       earlier shape) + locally edited SPEC => PRESERVED in place + named
+#       WARNING + forensic snapshot (no pristine fingerprint match)
+#   S5  pre-existing marker (r20) AND pre-existing root PROTOCOL.md (r13/
+#       r17) on a MAINTAINER install: both EXISTS-skipped => NO delivery
+#       record => neither is inventoried as framework-owned; the checker
+#       refuses the unrecorded marker and falls back to VERSION; doctor
+#       does not flag the adopter's PROTOCOL.md as an orphan
+#   S6  updater no-loop regression (r8): post-upgrade tree with stale root
+#       VERSION reports the NEW version via the recorded marker
+#       (up-to-date, exit 0); stripping the marker record flips it back to
+#       the stale VERSION (behind, exit != 0) — proves marker-first is
+#       load-bearing, not decorative
+#   S7  doctor, user mode (r19): adopter's OWN SPEC/v1 + root PROTOCOL.md
+#       are NOT orphan candidates under --strict-orphans (flags resolved
+#       from the baseline, not from a ceremony default)
+#   S8  doctor, maintainer mode (r9 P2): a stray file inside the DELIVERED
+#       SPEC/v1 IS an orphan candidate (positive control — the enumeration
+#       does include SPEC when the record says delivered)
+#
+# The pristine-match branch of the legacy migration (target SPEC/v1 byte-
+# identical to a shipped v1.2.0-or-earlier tree) deliberately lives in the
+# F4 install-v1.2.0→upgrade e2e (needs real tag content); it is NOT
+# duplicated here.
+#
+# bash 3.2-safe. mktemp -d only (xdist/parallel safe). Exits 0 on success,
+# non-zero on any failed assertion.
+#
+# Run:  bash scripts/tests/test-upgrade-spec-ownership.sh ; echo rc=$?
+
+set -uo pipefail   # NOT -e: we assert on command failures explicitly.
+
+SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
+SOURCE_DIR="$( cd "$SCRIPT_DIR/../.." && pwd )"
+# Override points so the test can be pointed at staged/candidate scripts
+# while they still live in a plan-staging mirror (PLAN-153 discipline).
+# NOTE: an override must point INTO a full framework checkout — install.sh /
+# upgrade.sh derive their source tree from their own resolved location.
+INSTALL="${CEO_INSTALL_UNDER_TEST:-$SOURCE_DIR/scripts/install.sh}"
+UPGRADE="${CEO_UPGRADE_UNDER_TEST:-$SOURCE_DIR/scripts/upgrade.sh}"
+DOCTOR="${CEO_DOCTOR_UNDER_TEST:-$SOURCE_DIR/scripts/doctor.sh}"
+CHECKER="${CEO_UPDATE_CHECKER_UNDER_TEST:-$SOURCE_DIR/.claude/scripts/check-framework-updates.sh}"
+
+export CEO_INSTALL_SKIP_SELF_SHA=1
+export CEO_RAG_INSTALL_PROMPT=0
+
+if ! command -v python3 >/dev/null 2>&1; then
+  echo "==> SKIP: python3 not installed (install-state machinery is python3-backed)"
+  exit 0
+fi
+
+SRC_VERSION="$(tr -d '[:space:]' < "$SOURCE_DIR/VERSION" 2>/dev/null || true)"
+if [ -z "$SRC_VERSION" ]; then
+  echo "FATAL: cannot read $SOURCE_DIR/VERSION" >&2
+  exit 2
+fi
+if [ ! -f "$SOURCE_DIR/.claude/.framework-version" ]; then
+  echo "FATAL: source has no .claude/.framework-version (F3 marker missing)" >&2
+  exit 2
+fi
+
+FAIL=0
+PASS=0
+WORKROOT="$( mktemp -d -t ceo-f3-own-XXXXXX )"
+cleanup() { [ -n "${WORKROOT:-}" ] && rm -rf "$WORKROOT" 2>/dev/null || true; }
+trap cleanup EXIT
+
+ok()   { PASS=$((PASS+1)); printf '  ok   %s\n' "$1"; }
+bad()  { FAIL=$((FAIL+1)); printf '  FAIL %s\n' "$1" >&2; }
+
+_git_init_retry() {
+  local d="$1" n=0
+  while [ "$n" -lt 5 ]; do
+    if ( cd "$d" && git init -q 2>/dev/null ); then return 0; fi
+    n=$((n+1)); sleep 1
+  done
+  ( cd "$d" && git init -q )
+}
+
+run_install() {
+  local t="$1"; shift
+  bash "$INSTALL" "$t" "$@" >"$t.install.log" 2>&1
+}
+
+run_upgrade() {
+  local t="$1"; shift
+  bash "$UPGRADE" "$t" --no-deprecation-warn "$@" >"$t.upgrade.log" 2>&1
+}
+
+fresh_install() {
+  # $1 = leg tag, rest = install args. Echoes the target path.
+  local tag="$1"; shift
+  local t
+  t="$( mktemp -d "$WORKROOT/tgt-$tag-XXXXXX" )"
+  _git_init_retry "$t"
+  if ! run_install "$t" "$@"; then
+    echo "INSTALL_FAILED ($tag)" >&2
+    tail -30 "$t.install.log" >&2
+    return 1
+  fi
+  printf '%s\n' "$t"
+}
+
+MANIFEST_REL=".claude/.install-manifest.sha256"
+MARKER_REL=".claude/.framework-version"
+
+manifest_has() {  # $1 = target, $2 = ERE fragment at the relpath position
+  grep -Eq "^([0-9a-f]{64}|LINK)  $2" "$1/$MANIFEST_REL" 2>/dev/null
+}
+
+# --------------------------------------------------------------------------
+# S1 — maintainer fresh install: delivery recorded end-to-end.
+# --------------------------------------------------------------------------
+echo "==> S1: maintainer install — SPEC/marker/PROTOCOL delivered + recorded"
+T1="$( fresh_install m1 --profile core )" || exit 1
+
+[ -d "$T1/SPEC/v1" ]            && ok "SPEC/v1 installed"            || bad "SPEC/v1 missing after maintainer install"
+[ -f "$T1/PROTOCOL.md" ]        && ok "root PROTOCOL.md installed"   || bad "root PROTOCOL.md missing"
+[ -f "$T1/$MARKER_REL" ]        && ok "marker installed"             || bad "marker missing"
+[ "$(tr -d '[:space:]' < "$T1/$MARKER_REL" 2>/dev/null)" = "$SRC_VERSION" ] \
+  && ok "marker == source VERSION ($SRC_VERSION)" \
+  || bad "marker != source VERSION (got: $(cat "$T1/$MARKER_REL" 2>/dev/null))"
+
+manifest_has "$T1" 'SPEC/v1/'                              && ok "baseline records SPEC/v1/"    || bad "baseline has NO SPEC/v1/ record"
+manifest_has "$T1" 'PROTOCOL\.md(  |$)'                    && ok "baseline records PROTOCOL.md" || bad "baseline has NO PROTOCOL.md record"
+manifest_has "$T1" '\.claude/\.framework-version(  |$)'    && ok "baseline records marker"      || bad "baseline has NO marker record"
+
+grep -q '"delivered_spec_v1"' "$T1/.claude/.install-state.json" 2>/dev/null \
+  && ok "install-state journals delivered_spec_v1" \
+  || bad "install-state missing delivered_spec_v1 op"
+grep -q '"delivered_framework_marker"' "$T1/.claude/.install-state.json" 2>/dev/null \
+  && ok "install-state journals delivered_framework_marker" \
+  || bad "install-state missing delivered_framework_marker op"
+
+# --------------------------------------------------------------------------
+# S2 — 2nd-upgrade forced route: record-owned edited SPEC is REPLACED with
+# backup; root VERSION sentinel untouched (AC-3 load-bearing fixture).
+# --------------------------------------------------------------------------
+echo "==> S2: 2nd upgrade — forced SPEC refresh (baseline already has SPEC)"
+SPEC_FILE="$( ls "$T1"/SPEC/v1/*.md 2>/dev/null | head -1 )"
+if [ -z "$SPEC_FILE" ]; then
+  bad "no SPEC file found to edit"
+else
+  printf '\nADOPTER-EDIT sentinel S2\n' >> "$SPEC_FILE"
+fi
+printf '1.0.0\n' > "$T1/VERSION"   # adopter-owned root VERSION sentinel
+
+if run_upgrade "$T1"; then ok "upgrade rc=0 (record-owned fixture)"; else bad "upgrade failed (see $T1.upgrade.log)"; fi
+
+SPEC_REL="${SPEC_FILE#"$T1"/}"
+if [ -n "$SPEC_FILE" ]; then
+  cmp -s "$SOURCE_DIR/$SPEC_REL" "$SPEC_FILE" \
+    && ok "edited SPEC file was FORCE-replaced with source bytes" \
+    || bad "edited SPEC file NOT replaced (classified walk preserved the fork?)"
+  BAK_HIT="$( ls -d "$T1"/.claude.bak/*/SPEC/v1 2>/dev/null | head -1 )"
+  if [ -n "$BAK_HIT" ] && grep -rq 'ADOPTER-EDIT sentinel S2' "$BAK_HIT" 2>/dev/null; then
+    ok "backup of the edited SPEC present under .claude.bak/<ts>/SPEC/v1"
+  else
+    bad "no .claude.bak backup carrying the edited SPEC content"
+  fi
+fi
+grep -q 'REFRESHED (forced' "$T1.upgrade.log" \
+  && ok "upgrade log names the forced route" \
+  || bad "upgrade log has no 'REFRESHED (forced' line"
+[ "$(tr -d '[:space:]' < "$T1/VERSION" 2>/dev/null)" = "1.0.0" ] \
+  && ok "root VERSION sentinel untouched by upgrade (ADR-155-AMEND-1)" \
+  || bad "root VERSION was modified by upgrade (got: $(cat "$T1/VERSION" 2>/dev/null))"
+[ "$(tr -d '[:space:]' < "$T1/$MARKER_REL" 2>/dev/null)" = "$SRC_VERSION" ] \
+  && ok "marker refreshed to source VERSION post-upgrade" \
+  || bad "marker not refreshed post-upgrade"
+manifest_has "$T1" 'SPEC/v1/' \
+  && ok "rewritten baseline still records SPEC/v1/ (ownership continuity)" \
+  || bad "rewritten baseline dropped the SPEC/v1 records"
+
+# --------------------------------------------------------------------------
+# S6 — updater no-loop (r8) on the S2 fixture: marker-first wins over the
+# stale root VERSION; stripping the marker record flips the source back.
+# --------------------------------------------------------------------------
+echo "==> S6: check-framework-updates.sh — marker-first, record-gated"
+STUB="$WORKROOT/stub-upstream"
+mkdir -p "$STUB"
+_git_init_retry "$STUB"
+( cd "$STUB" \
+  && git -c user.email=t@t -c user.name=t commit -q --allow-empty -m x \
+  && git tag "v$SRC_VERSION" ) 2>/dev/null \
+  && ok "stub upstream tagged v$SRC_VERSION" \
+  || bad "stub upstream construction failed"
+
+CHK_OUT="$WORKROOT/chk1.out"; CHK_ERR="$WORKROOT/chk1.err"
+( cd "$T1" && bash "$CHECKER" --upstream "$STUB" ) >"$CHK_OUT" 2>"$CHK_ERR"
+CHK_RC=$?
+[ "$CHK_RC" -eq 0 ] && grep -q 'up-to-date' "$CHK_OUT" \
+  && ok "post-upgrade tree reports up-to-date via marker (no behind-minor loop)" \
+  || bad "updater loop regression: rc=$CHK_RC (expected 0/up-to-date via marker; VERSION=1.0.0 is stale by design)"
+grep -q 'version source: marker' "$CHK_ERR" \
+  && ok "checker names the marker as its version source" \
+  || bad "checker did not use the marker (stderr: $(head -3 "$CHK_ERR" 2>/dev/null | tr '\n' ' '))"
+
+# Negative control: strip the marker record => fallback to stale VERSION.
+sed -i.bak '/  \.claude\/\.framework-version/d' "$T1/$MANIFEST_REL" 2>/dev/null \
+  || sed -i '' '/  \.claude\/\.framework-version/d' "$T1/$MANIFEST_REL" 2>/dev/null
+( cd "$T1" && bash "$CHECKER" --upstream "$STUB" ) >"$WORKROOT/chk2.out" 2>"$WORKROOT/chk2.err"
+CHK2_RC=$?
+[ "$CHK2_RC" -ne 0 ] \
+  && ok "marker record stripped => fallback to stale VERSION => behind (rc=$CHK2_RC)" \
+  || bad "checker still up-to-date after stripping the marker record — record gate is dead"
+grep -q 'falling back to VERSION' "$WORKROOT/chk2.err" \
+  && ok "checker names the r20 fallback" \
+  || bad "no 'falling back to VERSION' note on stripped record"
+
+# --------------------------------------------------------------------------
+# S8 — doctor, maintainer mode: delivered SPEC IS enumerated (orphan
+# positive control).
+# --------------------------------------------------------------------------
+echo "==> S8: doctor maintainer mode — stray file in delivered SPEC is an orphan"
+# Restore the marker record stripped by S6's negative control (the .bak of
+# the GNU-sed branch, if present, is the pristine manifest).
+if [ -f "$T1/$MANIFEST_REL.bak" ]; then mv "$T1/$MANIFEST_REL.bak" "$T1/$MANIFEST_REL"; fi
+printf 'stray\n' > "$T1/SPEC/v1/zz-orphan-probe.md"
+DOC_OUT="$WORKROOT/doc1.out"
+bash "$DOCTOR" "$T1" --strict-orphans >"$DOC_OUT" 2>&1
+DOC_RC=$?
+grep -q 'ORPHAN?: SPEC/v1/zz-orphan-probe.md' "$DOC_OUT" && [ "$DOC_RC" -ne 0 ] \
+  && ok "delivered SPEC is enumerated: stray file flagged, rc=$DOC_RC" \
+  || bad "stray file in delivered SPEC NOT flagged (rc=$DOC_RC) — FMS_DELIVERED_SPEC resolution dead"
+rm -f "$T1/SPEC/v1/zz-orphan-probe.md"
+
+# --------------------------------------------------------------------------
+# S4 — legacy ADOPTER-FORK (fresh fixture; simulate the v1.2-and-earlier
+# baseline shape by stripping SPEC records, then fork the SPEC).
+# --------------------------------------------------------------------------
+echo "==> S4: legacy baseline (no SPEC records) + edited SPEC => preserve + WARNING"
+T2="$( fresh_install m2 --profile core )" || exit 1
+sed -i.bak '/  SPEC\/v1\//d' "$T2/$MANIFEST_REL" 2>/dev/null \
+  || sed -i '' '/  SPEC\/v1\//d' "$T2/$MANIFEST_REL" 2>/dev/null
+rm -f "$T2/$MANIFEST_REL.bak"
+SPEC2="$( ls "$T2"/SPEC/v1/*.md 2>/dev/null | head -1 )"
+printf '\nADOPTER-FORK sentinel S4\n' >> "$SPEC2"
+
+if run_upgrade "$T2"; then ok "upgrade rc=0 (fork is preserved, never fatal)"; else bad "upgrade failed on adopter-fork fixture"; fi
+grep -q 'ADOPTER-FORK' "$T2.upgrade.log" \
+  && ok "named ADOPTER-FORK warning emitted" \
+  || bad "no ADOPTER-FORK warning in upgrade log"
+grep -q 'ADOPTER-FORK sentinel S4' "$SPEC2" 2>/dev/null \
+  && ok "forked SPEC preserved in place" \
+  || bad "forked SPEC was clobbered despite missing delivery record"
+manifest_has "$T2" 'SPEC/v1/' \
+  && bad "rewritten baseline claims the adopter-fork SPEC as framework-owned" \
+  || ok "rewritten baseline does NOT claim the adopter-fork SPEC"
+SNAP_HIT="$( ls -d "$T2"/.claude.bak/*/SPEC/v1 2>/dev/null | head -1 )"
+[ -n "$SNAP_HIT" ] \
+  && ok "forensic snapshot of the fork present under .claude.bak" \
+  || bad "no forensic snapshot of the preserved fork"
+
+# --------------------------------------------------------------------------
+# S3 — user ceremony + upgrade --no-replay (r9): no SPEC, no root files.
+# --------------------------------------------------------------------------
+echo "==> S3: --ceremony user install + upgrade --no-replay"
+T3="$( fresh_install u1 --profile core --ceremony user )" || exit 1
+[ ! -e "$T3/SPEC" ]        && ok "user install has no SPEC/"            || bad "user install received SPEC/"
+[ ! -e "$T3/PROTOCOL.md" ] && ok "user install has no root PROTOCOL.md" || bad "user install received root PROTOCOL.md"
+[ -f "$T3/$MARKER_REL" ]   && ok "user install DOES receive the marker (inside .claude/)" \
+                           || bad "user install missing the marker"
+manifest_has "$T3" '\.claude/\.framework-version(  |$)' \
+  && ok "user baseline records the marker" || bad "user baseline missing marker record"
+
+if run_upgrade "$T3" --no-replay; then ok "upgrade --no-replay rc=0 on user fixture"; else bad "upgrade --no-replay failed on user fixture"; fi
+[ ! -e "$T3/SPEC" ] \
+  && ok "upgrade --no-replay did NOT deliver SPEC (ceremony read is replay-independent)" \
+  || bad "r9 REGRESSION: upgrade --no-replay forced SPEC into a user install"
+[ ! -e "$T3/PROTOCOL.md" ] \
+  && ok "upgrade --no-replay did NOT create root PROTOCOL.md (gated _refresh_protocol_pointer)" \
+  || bad "r13 REGRESSION: protocol pointer created on a user install"
+grep -Eq 'Ceremony: user' "$T3.upgrade.log" \
+  && ok "upgrade banner names the recorded user ceremony" \
+  || bad "upgrade banner missing 'Ceremony: user'"
+
+# --------------------------------------------------------------------------
+# S7 — doctor, user mode: adopter's own SPEC + root PROTOCOL.md are not
+# orphan candidates.
+# --------------------------------------------------------------------------
+echo "==> S7: doctor user mode — adopter SPEC/PROTOCOL not orphans"
+mkdir -p "$T3/SPEC/v1"
+printf 'the ADOPTERs own contract\n' > "$T3/SPEC/v1/own.md"
+printf 'the ADOPTERs own protocol\n' > "$T3/PROTOCOL.md"
+DOC3_OUT="$WORKROOT/doc3.out"
+bash "$DOCTOR" "$T3" --strict-orphans >"$DOC3_OUT" 2>&1
+DOC3_RC=$?
+if grep -Eq 'ORPHAN\?: (SPEC/v1/|PROTOCOL\.md)' "$DOC3_OUT"; then
+  bad "r19 REGRESSION: doctor flags the adopter's own SPEC/PROTOCOL as orphans (rc=$DOC3_RC)"
+else
+  ok "adopter's own SPEC/PROTOCOL not flagged (rc=$DOC3_RC)"
+fi
+[ "$DOC3_RC" -eq 0 ] \
+  && ok "doctor --strict-orphans clean on the user fixture" \
+  || bad "doctor --strict-orphans rc=$DOC3_RC on user fixture (see $DOC3_OUT)"
+rm -f "$T3/PROTOCOL.md"
+
+# --------------------------------------------------------------------------
+# S5 — pre-existing marker (r20): EXISTS-skip => no record => VERSION wins.
+# --------------------------------------------------------------------------
+echo "==> S5: pre-existing marker + pre-existing root PROTOCOL.md not delivered, not trusted"
+T4="$( mktemp -d "$WORKROOT/tgt-m3-XXXXXX" )"
+_git_init_retry "$T4"
+mkdir -p "$T4/.claude"
+printf '9.9.9\n' > "$T4/$MARKER_REL"
+printf '# the ADOPTERs own protocol (pre-existing)\n' > "$T4/PROTOCOL.md"
+if run_install "$T4" --profile core; then ok "install rc=0 with pre-existing marker+protocol"; else bad "install failed (see $T4.install.log)"; fi
+[ "$(tr -d '[:space:]' < "$T4/$MARKER_REL" 2>/dev/null)" = "9.9.9" ] \
+  && ok "pre-existing marker EXISTS-skipped (adopter bytes intact)" \
+  || bad "install overwrote a pre-existing marker"
+manifest_has "$T4" '\.claude/\.framework-version(  |$)' \
+  && bad "baseline claims a marker the install never wrote (r17/r20)" \
+  || ok "baseline does NOT record the skipped marker"
+grep -q 'ADOPTERs own protocol' "$T4/PROTOCOL.md" 2>/dev/null \
+  && ok "pre-existing root PROTOCOL.md EXISTS-skipped (adopter bytes intact)" \
+  || bad "install overwrote a pre-existing root PROTOCOL.md"
+manifest_has "$T4" 'PROTOCOL\.md(  |$)' \
+  && bad "r13/r17 REGRESSION: baseline claims a PROTOCOL.md the install never wrote" \
+  || ok "baseline does NOT record the skipped PROTOCOL.md"
+DOC4_OUT="$WORKROOT/doc4.out"
+bash "$DOCTOR" "$T4" --strict-orphans >"$DOC4_OUT" 2>&1
+DOC4_RC=$?
+if grep -Eq 'ORPHAN\?: PROTOCOL\.md' "$DOC4_OUT"; then
+  bad "doctor flags the adopter's pre-existing PROTOCOL.md as an orphan (rc=$DOC4_RC)"
+else
+  ok "doctor does not orphan-flag the adopter's pre-existing PROTOCOL.md (rc=$DOC4_RC)"
+fi
+( cd "$T4" && bash "$CHECKER" --upstream "$STUB" ) >"$WORKROOT/chk3.out" 2>"$WORKROOT/chk3.err"
+CHK3_RC=$?
+grep -q 'falling back to VERSION' "$WORKROOT/chk3.err" \
+  && ok "checker refuses the unrecorded marker (r20)" \
+  || bad "checker trusted an unrecorded marker (stderr: $(head -3 "$WORKROOT/chk3.err" 2>/dev/null | tr '\n' ' '))"
+[ "$CHK3_RC" -eq 0 ] && grep -q 'up-to-date' "$WORKROOT/chk3.out" \
+  && ok "fallback VERSION ($SRC_VERSION) matches stub upstream — up-to-date" \
+  || bad "fallback path wrong rc=$CHK3_RC"
+
+echo ""
+echo "==> RESULT: pass=$PASS fail=$FAIL"
+[ "$FAIL" -eq 0 ] || exit 1
+exit 0

exec
/bin/zsh -lc 'git diff --no-ext-diff --unified=80 -- ".claude/scripts/tests/test_release_workflow_asserts.py"' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
diff --git a/.claude/scripts/tests/test_release_workflow_asserts.py b/.claude/scripts/tests/test_release_workflow_asserts.py
index bc68a9f..3518bb3 100644
--- a/.claude/scripts/tests/test_release_workflow_asserts.py
+++ b/.claude/scripts/tests/test_release_workflow_asserts.py
@@ -1,139 +1,292 @@
 """PLAN-153 Wave B item 5 — release-workflow VERSION-consistency + idempotency asserts.
 
 Extends the existing VERSION-consistency test family
 (test_npm_rebuild.py::NpmRebuildTest.test_version_files_in_sync —
 VERSION == npm/VERSION == npm/package.json.version) and the grey-box
 workflow-invariant convention (test_workflow_devops_p2.py) with:
 
 - version↔plugin-manifest sync: VERSION == .claude-plugin/plugin.json
   version == every `version` field in .claude-plugin/marketplace.json
   (skip-if-absent until PLAN-153 Wave B item 6 generates the manifests
   via build-plugin.py — same skipTest pattern test_npm_rebuild.py uses
   for the release-only npm bundle);
 - RC posture pins on npm-publish.yml: RC tags stay hard-excluded from
   npm publishing (PLAN-013 anti-goals #3/#16, re-ratified by the
   PLAN-153 debate: the `next` dist-tag idea was DROPPED);
 - release-notes template invariants (.github/release-notes-template.md,
   closes PLAN-152 §Deferred release-notes-hardcoded-first-release);
 - dual-context asserts on the Wave B workflow edits themselves
   (npm-publish.yml `already_published` guard; release.yml
   `gh release view || gh release create` idempotency; `-rc.N` strip in
   the VERSION + CHANGELOG gates, closing PLAN-152 §Deferred
   release-gate-rc-version-mismatch / red run 28663453202): enforced
   against the STAGED copy while it exists on disk
   (.claude/plans/PLAN-153/staged/wave-B/ is gitignored → absent in CI)
   and against the LIVE workflow once Wave B lands (detected via the
   "PLAN-153 Wave B item 5" marker). They skip only in the pre-landing
   CI window where neither context is available.
+
+PLAN-166 W1 items 1 + 4 (F1, P0) extend the same dual-context convention
+(staged mirror under .claude/plans/PLAN-166/staged/ pre-landing,
+"PLAN-166 W1 item 1" marker in the live file post-landing) with:
+
+- await-gate asserts: the publish OBSERVES release.yml's `release-gate`
+  job — `await-release-gate` job present, `needs:` on the publish job,
+  `GH_TOKEN: ${{ github.token }}` in the await job's env (permissions:
+  alone does NOT authenticate the gh CLI on a hosted runner; without the
+  token every poll dies on auth = fail-closed BLOCK breaking every
+  release), permissions/timeout pinned, and NO environment / NO RC
+  exclusion on the await job (RC tags are the live positive control).
+  Posture pins are STRENGTHENED, not relocated: NpmPublishRcPostureTest
+  keeps asserting the RC exclusion + environment on the live file.
+- trusted-publisher binding asserts: the npmjs OIDC registration triple
+  (repository / workflow FILENAME / environment) is cross-checked by
+  READING .claude/governance/npm-trusted-publisher.txt — embedding the
+  values in the test would create a 4th copy of the truth. Includes
+  positive controls: mutating `environment:` (or the repository slug) in
+  a COPY of the workflow text must go red.
+
+PLAN-166 W1-B (F2 server side; merged in by the ceremony assembler —
+one runnable asserts file) adds the W1B* classes at the bottom:
+structural asserts for release.yml's verdict delta + ancestry gate step
+(no continue-on-error, fail-closed on the transition var, delegation to
+_release_tag_guard.py, parent+GITHUB_SHA ancestry, pinned step order,
+`release-gate` job-name pin) plus the guard-module contract pins.
 """
 from __future__ import annotations
 
 import json
 import re
 import sys
 import unittest
 from pathlib import Path
 from typing import Iterator, Optional, Tuple
 
-_REPO = Path(__file__).resolve().parent.parent.parent.parent
+def _find_repo() -> Path:
+    """Repo root — robust to BOTH homes this file can run from.
+
+    At its landed path (.claude/scripts/tests/) four parents reach the
+    root; at its staged path (.claude/plans/PLAN-166/staged/...) they
+    reach the staged mirror instead. Walk up to the first ancestor that
+    actually looks like the repo (has the live workflow AND the hooks
+    tree) so pre-land verification runs from the staged location give
+    the same answers as post-land runs. (Merged in from the W1-B slice
+    by the PLAN-166 ceremony assembler.)
+    """
+    here = Path(__file__).resolve()
+    for candidate in here.parents:
+        if (
+            (candidate / ".github" / "workflows" / "release.yml").is_file()
+            and (candidate / ".claude" / "hooks" / "_lib").is_dir()
+        ):
+            return candidate
+    # Fall back to the landed-layout arithmetic; setUp guards will skip
+    # or fail loudly if this is wrong.
+    return here.parent.parent.parent.parent
+
+
+_REPO = _find_repo()
 _WF = _REPO / ".github" / "workflows"
 _STAGED_WF = (
     _REPO / ".claude" / "plans" / "PLAN-153" / "staged" / "wave-B"
     / ".github" / "workflows"
 )
 _TEMPLATE = _REPO / ".github" / "release-notes-template.md"
 _PLUGIN_DIR = _REPO / ".claude-plugin"
 
 # Bootstrap TestEnvContext so env isolation holds (env-hygiene gate).
 _HOOKS_DIR = _REPO / ".claude" / "hooks"
 if str(_HOOKS_DIR) not in sys.path:
     sys.path.insert(0, str(_HOOKS_DIR))
 from _lib.testing import TestEnvContext  # noqa: E402
 
 # Marker written into both Wave B workflow edits; its presence in the
 # LIVE file means Wave B has landed and the live copy is authoritative.
 _MARKER = "PLAN-153 Wave B item 5"
 
 # The load-bearing RC exclusion (PLAN-013 anti-goals #3/#16).
 _RC_EXCLUSION = "!contains(github.ref, '-rc.')"
 
+# --- PLAN-166 W1 items 1 + 4 (F1, P0) --------------------------------
+# Marker written into the PLAN-166 npm-publish.yml edit; its presence in
+# the LIVE file means the W1 ceremony landed and the live copy is
+# authoritative (same convention as _MARKER above).
+_MARKER_166 = "PLAN-166 W1 item 1"
+
+_STAGED_166 = _REPO / ".claude" / "plans" / "PLAN-166" / "staged"
+_STAGED_166_WF = _STAGED_166 / ".github" / "workflows"
+
+# Repo-side record of the npmjs trusted-publisher OIDC binding triple.
+_TRUSTED_PUBLISHER = (
+    _REPO / ".claude" / "governance" / "npm-trusted-publisher.txt"
+)
+_STAGED_166_TRUSTED_PUBLISHER = (
+    _STAGED_166 / ".claude" / "governance" / "npm-trusted-publisher.txt"
+)
+_TRUSTED_PUBLISHER_KEYS = frozenset({"repository", "workflow", "environment"})
+
+
+def _plan166_text(name: str) -> Optional[Tuple[str, str]]:
+    """Return (text, context) for a PLAN-166 workflow edit, or None pre-landing.
+
+    Priority: live copy carrying the PLAN-166 marker (post-landing,
+    authoritative) → staged copy under .claude/plans/PLAN-166/staged/
+    (pre-landing, local ceremony mirror; gitignored so absent in CI) →
+    None (pre-landing CI: skip). Unlike _wave_b_text this tolerates a
+    missing live file — the filename-binding test reports that as a
+    FAILURE, not a collection error.
+    """
+    live = _WF / name
+    if live.is_file():
+        text = live.read_text(encoding="utf-8")
+        if _MARKER_166 in text:
+            return text, "live"
+    staged = _STAGED_166_WF / name
+    if staged.is_file():
+        return staged.read_text(encoding="utf-8"), "staged"
+    return None
+
+
+def _trusted_publisher_values() -> Optional[Tuple[dict, str]]:
+    """Parse npm-trusted-publisher.txt (live → staged), or None pre-landing.
+
+    Format contract (documented in the file itself): `key=value` lines;
+    `#`-prefixed and blank lines are comments; keys are EXACTLY
+    repository/workflow/environment. Malformed content raises — a
+    binding record we cannot parse must never silently skip the binding
+    asserts (fail-closed, ADR-186 posture).
+    """
+    for path, context in (
+        (_TRUSTED_PUBLISHER, "live"),
+        (_STAGED_166_TRUSTED_PUBLISHER, "staged"),
+    ):
+        if not path.is_file():
+            continue
+        values = {}
+        for lineno, raw in enumerate(
+            path.read_text(encoding="utf-8").splitlines(), 1
+        ):
+            line = raw.strip()
+            if not line or line.startswith("#"):
+                continue
+            key, sep, value = line.partition("=")
+            key, value = key.strip(), value.strip()
+            if not sep or not key or not value:
+                raise AssertionError(
+                    "%s:%d: expected key=value, got %r" % (path, lineno, raw)
+                )
+            if key in values:
+                raise AssertionError(
+                    "%s:%d: duplicate key %r" % (path, lineno, key)
+                )
+            values[key] = value
+        if set(values) != set(_TRUSTED_PUBLISHER_KEYS):
+            raise AssertionError(
+                "%s must define exactly %s, got %s"
+                % (path, sorted(_TRUSTED_PUBLISHER_KEYS), sorted(values))
+            )
+        return values, context
+    return None
+
+
+def _binding_mismatches(values: dict, workflow_text: str) -> list:
+    """Which parts of the trusted-publisher triple the workflow does NOT honour.
+
+    Pure text→list (no filesystem) so the positive-control tests can run
+    it against a deliberately mutated COPY of the workflow text.
+    """
+    mismatches = []
+    if ("environment: " + values["environment"]) not in workflow_text:
+        mismatches.append(
+            "workflow does not gate through `environment: %s` — the npmjs "
+            "trusted-publisher registration names that environment"
+            % values["environment"]
+        )
+    if values["repository"] not in workflow_text:
+        mismatches.append(
+            "workflow no longer names the registered repository %r (the "
+            "OIDC registration comment is the in-file record)"
+            % values["repository"]
+        )
+    return mismatches
+
 
 def _wave_b_text(name: str) -> Optional[Tuple[str, str]]:
     """Return (text, context) for a Wave B workflow, or None pre-landing.
 
     Priority: live copy carrying the Wave B marker (post-landing,
     authoritative) → staged copy (pre-landing, local ceremony mirror;
     gitignored so absent in CI) → None (pre-landing CI: skip).
     """
     live = (_WF / name).read_text(encoding="utf-8")
     if _MARKER in live:
         return live, "live"
     staged = _STAGED_WF / name
     if staged.is_file():
         return staged.read_text(encoding="utf-8"), "staged"
     return None
 
 
 def _iter_version_fields(obj: object) -> Iterator[str]:
     """Yield every string-valued `version` field nested anywhere in obj."""
     if isinstance(obj, dict):
         for key, value in obj.items():
             if key == "version" and isinstance(value, str):
                 yield value
             else:
                 yield from _iter_version_fields(value)
     elif isinstance(obj, list):
         for item in obj:
             yield from _iter_version_fields(item)
 
 
 class PluginManifestVersionSyncTest(TestEnvContext):
     """VERSION ↔ .claude-plugin manifest sync (Wave B item 5 (e)).
 
     Sits NEXT TO the existing family member
     test_npm_rebuild.py::test_version_files_in_sync, extending the
     equality chain to the plugin manifests generated by build-plugin.py
     (Wave B item 6). Skips while the manifests do not exist yet; becomes
     enforcing the moment item 6 lands — no test edit needed.
     """
 
     def setUp(self):
         super().setUp()
         self.version = (_REPO / "VERSION").read_text(encoding="utf-8").strip()
 
     def test_plugin_json_version_matches_version_file(self):
         plugin_json = _PLUGIN_DIR / "plugin.json"
         if not plugin_json.is_file():
             self.skipTest(
                 ".claude-plugin/plugin.json not present yet "
                 "(generated by PLAN-153 Wave B item 6 build-plugin.py)"
             )
         data = json.loads(plugin_json.read_text(encoding="utf-8"))
         self.assertIn(
             "version", data,
             ".claude-plugin/plugin.json must carry a version field",
         )
         self.assertEqual(
             data["version"], self.version,
             f"plugin.json version ({data['version']}) != VERSION "
             f"({self.version}) — regenerate via build-plugin.py",
         )
 
     def test_marketplace_json_versions_match_version_file(self):
         marketplace_json = _PLUGIN_DIR / "marketplace.json"
         if not marketplace_json.is_file():
             self.skipTest(
                 ".claude-plugin/marketplace.json not present yet "
                 "(generated by PLAN-153 Wave B item 6 build-plugin.py)"
             )
         data = json.loads(marketplace_json.read_text(encoding="utf-8"))
         # Schema is owned by build-plugin.py, so assert on EVERY nested
         # `version` field rather than hardcoding one JSON path.
         mismatched = [
             v for v in _iter_version_fields(data) if v != self.version
         ]
         self.assertEqual(
             mismatched, [],
             f"marketplace.json carries version field(s) {mismatched} != "
             f"VERSION ({self.version}) — regenerate via build-plugin.py",
         )
@@ -142,198 +295,722 @@ class PluginManifestVersionSyncTest(TestEnvContext):
 class NpmPublishRcPostureTest(TestEnvContext):
     """RC tags stay hard-excluded from npm publishing — LIVE workflow.
 
     PLAN-013 anti-goals #3/#16; PLAN-153 Wave B item 5 (f) explicitly
     keeps this posture UNCHANGED. These asserts run against the live
     workflow in every context (pre- and post-landing).
     """
 
     def setUp(self):
         super().setUp()
         self.source = (_WF / "npm-publish.yml").read_text(encoding="utf-8")
 
     def test_rc_exclusion_present(self):
         self.assertIn(
             _RC_EXCLUSION, self.source,
             "npm-publish.yml lost the RC tag exclusion — RC tags must "
             "NEVER trigger an npm publish (PLAN-013 anti-goals #3/#16)",
         )
 
     def test_rc_exclusion_precedes_publish_command(self):
         # Ordering sanity: the job-level guard must appear before any
         # `npm publish` invocation in the file.
         self.assertLess(
             self.source.index(_RC_EXCLUSION),
             self.source.index("npm publish --provenance"),
             "RC exclusion must guard the job containing the publish step",
         )
 
     def test_manual_approval_environment_gate_present(self):
         self.assertIn(
             "environment: production-npm", self.source,
             "the Owner-in-the-loop manual approval environment gate "
             "(PLAN-013 anti-goal #16) must stay on the publish job",
         )
 
 
 class ReleaseNotesTemplateTest(TestEnvContext):
     """Template invariants for the templatized release notes (item 5 (d))."""
 
     def setUp(self):
         super().setUp()
         self.assertTrue(
             _TEMPLATE.is_file(),
             ".github/release-notes-template.md missing — the Wave B "
             "release.yml renders notes from it (fail-closed)",
         )
         self.source = _TEMPLATE.read_text(encoding="utf-8")
 
     def test_has_tag_placeholder(self):
         self.assertIn("{{TAG}}", self.source)
 
     def test_has_base_version_placeholder(self):
         # BASE_VERSION (= VERSION minus -rc.N) points RC notes at the
         # GA CHANGELOG section.
         self.assertIn("{{BASE_VERSION}}", self.source)
 
     def test_no_stale_release_specific_hardcode(self):
         # The exact stale string this template replaces (PLAN-152
         # §Deferred release-notes-hardcoded-first-release).
         self.assertNotIn("first public release", self.source)
 
     def test_only_known_placeholders_used(self):
         # The workflow substitutes exactly TAG/VERSION/BASE_VERSION and
         # fails closed on any '{{' left after rendering; an unknown
         # token here would brick every release.
         unknown = set(re.findall(r"\{\{([^}]*)\}\}", self.source)) - {
             "TAG", "VERSION", "BASE_VERSION",
         }
         self.assertEqual(unknown, set(), f"unknown placeholders: {unknown}")
 
 
 class WorkflowHygieneTest(TestEnvContext):
     """Parse + SHA-pin discipline for both tag-triggered workflows."""
 
     def test_workflows_parse_as_yaml(self):
         try:
             import yaml  # type: ignore
         except ImportError:  # pragma: no cover - CI installs pyyaml
             self.skipTest("pyyaml not installed")
         for name in ("release.yml", "npm-publish.yml"):
-            for path in ((_WF / name), (_STAGED_WF / name)):
+            for path in ((_WF / name), (_STAGED_WF / name),
+                         (_STAGED_166_WF / name)):
                 if not path.is_file():
                     continue
                 with self.subTest(path=str(path)):
                     data = yaml.safe_load(path.read_text(encoding="utf-8"))
                     self.assertIsInstance(data, dict)
                     self.assertIn("jobs", data)
 
     def test_all_action_uses_are_sha_pinned(self):
         # Every `uses:` in both workflows (live + staged copies) must
         # pin to a 40-hex commit SHA — no floating tags.
         pattern = re.compile(r"^\s*(?:-\s+)?uses:\s*(\S+)", re.MULTILINE)
         pinned = re.compile(r".+@[0-9a-f]{40}$")
         for name in ("release.yml", "npm-publish.yml"):
-            for path in ((_WF / name), (_STAGED_WF / name)):
+            for path in ((_WF / name), (_STAGED_WF / name),
+                         (_STAGED_166_WF / name)):
                 if not path.is_file():
                     continue
                 text = path.read_text(encoding="utf-8")
                 for used in pattern.findall(text):
                     with self.subTest(path=str(path), uses=used):
                         self.assertRegex(
                             used, pinned,
                             f"{path.name}: `uses: {used}` is not "
                             "SHA-pinned to a 40-hex commit",
                         )
 
 
 class WaveB5ReleaseYmlTest(TestEnvContext):
     """Wave B item 5 edits to release.yml (dual-context: staged/live)."""
 
     def setUp(self):
         super().setUp()
         resolved = _wave_b_text("release.yml")
         if resolved is None:
             self.skipTest(
                 "Wave B release.yml not landed and staged mirror absent "
                 "(pre-landing CI window)"
             )
         self.source, self.context = resolved
 
     def test_version_gate_strips_rc_suffix(self):
         # PLAN-152 §Deferred release-gate-rc-version-mismatch fix:
         # the tag is normalized before comparing against VERSION.
         self.assertIn('BASE="${EXPECTED%-rc.[0-9]*}"', self.source)
         self.assertIn('if [[ "$FILE" != "$BASE" ]]', self.source)
 
     def test_changelog_gate_strips_rc_suffix(self):
         # Without this the fixed VERSION gate would just move the RC
         # red run one step later (RC tags have no own CHANGELOG section).
         self.assertIn('VERSION="${VERSION%-rc.[0-9]*}"', self.source)
 
     def test_plugin_manifest_sync_step_present(self):
         self.assertIn(
             "Assert plugin manifest versions match VERSION", self.source
         )
         self.assertIn(".claude-plugin/plugin.json", self.source)
         self.assertIn(".claude-plugin/marketplace.json", self.source)
 
     def test_release_create_is_idempotent(self):
         # `gh release view || gh release create` shape: re-runs re-sync
         # assets instead of failing on the existing release.
         self.assertIn('if gh release view "$TAG"', self.source)
         self.assertIn("--clobber install.sh.sha256 sbom.cyclonedx.json",
                       self.source)
         self.assertIn('gh release create "$TAG"', self.source)
 
     def test_rc_tags_marked_prerelease(self):
         self.assertIn("--prerelease", self.source)
 
     def test_notes_are_templatized_not_hardcoded(self):
         self.assertIn("release-notes-template.md", self.source)
         self.assertIn("--notes-file release-notes.md", self.source)
         self.assertNotIn(
             "first public release", self.source,
             "stale per-release hardcode back in release.yml "
             "(PLAN-152 §Deferred release-notes-hardcoded-first-release)",
         )
 
 
 class WaveB5NpmPublishYmlTest(TestEnvContext):
     """Wave B item 5 edits to npm-publish.yml (dual-context: staged/live)."""
 
     def setUp(self):
         super().setUp()
         resolved = _wave_b_text("npm-publish.yml")
         if resolved is None:
             self.skipTest(
                 "Wave B npm-publish.yml not landed and staged mirror "
                 "absent (pre-landing CI window)"
             )
         self.source, self.context = resolved
 
     def test_already_published_guard_present(self):
         self.assertIn("id: already_published", self.source)
         self.assertIn(
             'npm view "${PKG_NAME}@${PKG_VERSION}" version', self.source
         )
 
     def test_publish_step_gated_on_guard(self):
         self.assertIn(
             "if: steps.already_published.outputs.published != 'true'",
             self.source,
         )
 
     def test_noop_success_path_is_explicit(self):
         self.assertIn(
             "if: steps.already_published.outputs.published == 'true'",
             self.source,
         )
 
     def test_rc_exclusion_survives_wave_b(self):
         # Item 5 (f): the Wave B edit must NOT weaken the RC posture.
         self.assertIn(_RC_EXCLUSION, self.source)
         self.assertIn("environment: production-npm", self.source)
 
 
+class Plan166AwaitGateTest(TestEnvContext):
+    """PLAN-166 W1 item 1 — the publish must OBSERVE release.yml's gate.
+
+    Dual-context (staged/live) like the Wave B classes above. These pins
+    STRENGTHEN the posture pins — NpmPublishRcPostureTest keeps running
+    against the live file in every context.
+    """
+
+    def setUp(self):
+        super().setUp()
+        resolved = _plan166_text("npm-publish.yml")
+        if resolved is None:
+            self.skipTest(
+                "PLAN-166 npm-publish.yml not landed and staged mirror "
+                "absent (pre-landing CI window)"
+            )
+        self.source, self.context = resolved
+
+    def _jobs(self) -> dict:
+        try:
+            import yaml  # type: ignore
+        except ImportError:  # pragma: no cover - CI installs pyyaml
+            self.skipTest("pyyaml not installed")
+        return yaml.safe_load(self.source)["jobs"]
+
+    def test_publish_needs_await_gate(self):
+        # String-level (runs even without pyyaml): the load-bearing edge.
+        self.assertIn(
+            "needs: await-release-gate", self.source,
+            "publish no longer waits for the await-release-gate job — "
+            "the npm publish would stop observing release.yml's "
+            "release-gate (PLAN-166 F1, P0)",
+        )
+
+    def test_publish_needs_await_gate_structurally(self):
+        jobs = self._jobs()
+        self.assertEqual(
+            jobs["publish"].get("needs"), "await-release-gate",
+            "the `needs:` must sit on the PUBLISH job itself",
+        )
+
+    def test_await_job_authenticates_gh_cli(self):
+        # `permissions:` alone does NOT authenticate the gh CLI on a
+        # hosted runner; without GH_TOKEN every poll dies on auth →
+        # fail-closed BLOCK breaking every release, RC and GA alike.
+        self.assertIn("GH_TOKEN: ${{ github.token }}", self.source)
+        jobs = self._jobs()
+        env = jobs["await-release-gate"].get("env") or {}
+        self.assertEqual(
+            env.get("GH_TOKEN"), "${{ github.token }}",
+            "await-release-gate must carry GH_TOKEN at the JOB level",
+        )
+
+    def test_await_job_permissions_and_timeout(self):
+        jobs = self._jobs()
+        gate = jobs["await-release-gate"]
+        self.assertEqual(
+            gate.get("permissions"),
+            {"contents": "read", "actions": "read"},
+            "await job needs exactly contents:read (checkout) + "
+            "actions:read (runs/jobs REST) — and nothing more (no "
+            "id-token: the gate job must not be able to publish)",
+        )
+        self.assertEqual(
+            gate.get("timeout-minutes"), 35,
+            "35 > the poller's 30-minute deadline so a timeout surfaces "
+            "as the decision function's fail-CLOSED BLOCK, not an opaque "
+            "runner kill",
+        )
+
+    def test_await_job_is_the_rc_positive_control(self):
+        # NO environment (no manual approval before evidence) and NO RC
+        # exclusion: the await job runs on rc tags, so every RC is a live
+        # positive control of the gate before GA depends on it.
+        jobs = self._jobs()
+        gate = jobs["await-release-gate"]
+        self.assertNotIn(
+            "environment", gate,
+            "await-release-gate must NOT gate through an environment — "
+            "manual approval belongs AFTER the machine evidence",
+        )
+        self.assertNotIn(
+            "if", gate,
+            "await-release-gate must NOT exclude RC tags — RC runs are "
+            "the live positive control",
+        )
+
+    def test_await_job_invokes_decision_function(self):
+        self.assertIn(".claude/scripts/await_release_gate.py", self.source)
+        # The deadline is what makes every non-GRANT state collapse to
+        # BLOCK (fail-closed) instead of polling forever.
+        self.assertIn("--deadline-epoch", self.source)
+
+    def test_publish_posture_verbatim(self):
+        jobs = self._jobs()
+        pub = jobs["publish"]
+        self.assertEqual(pub.get("environment"), "production-npm")
+        self.assertIn(_RC_EXCLUSION, pub.get("if", ""))
+
+    def test_already_published_guard_stays_in_publish_after_needs(self):
+        # Deliberate ordering (PLAN-166 OQ-1): gate first, manual
+        # approval second, last-resort idempotency guard INSIDE publish.
+        self.assertLess(
+            self.source.index("needs: await-release-gate"),
+            self.source.index("id: already_published"),
+            "already_published must remain in the publish job, after "
+            "the needs: edge — do not move it into the gate job",
+        )
+
+
+class TrustedPublisherBindingTest(TestEnvContext):
+    """PLAN-166 W1 item 4 — the npmjs OIDC trusted-publisher triple.
+
+    npm trusted publishing binds by repository + workflow FILENAME +
+    environment (oidc-failure-playbook.md:18). This class READS
+    .claude/governance/npm-trusted-publisher.txt and cross-checks the
+    workflow — it embeds NO values (a 4th copy of the truth).
+    """
+
+    def setUp(self):
+        super().setUp()
+        resolved = _trusted_publisher_values()
+        if resolved is None:
+            self.skipTest(
+                "npm-trusted-publisher.txt not landed and staged copy "
+                "absent (pre-landing CI window)"
+            )
+        self.values, self.txt_context = resolved
+        wf_name = self.values["workflow"]
+        wf = _plan166_text(wf_name)
+        if wf is not None:
+            self.workflow_text, self.wf_context = wf
+        else:
+            live = _WF / wf_name
+            if not live.is_file():
+                self.fail(
+                    "trusted publisher registers workflow %r but "
+                    ".github/workflows/%s does not exist — the OIDC "
+                    "binding is by FILENAME; publishing would die "
+                    "ENEEDAUTH at GA" % (wf_name, wf_name)
+                )
+            self.workflow_text = live.read_text(encoding="utf-8")
+            self.wf_context = "live-pre-plan166"
+
+    def test_registered_workflow_file_publishes(self):
+        self.assertIn(
+            "npm publish --provenance", self.workflow_text,
+            "the workflow the npmjs console points at must be the one "
+            "actually publishing",
+        )
+
+    def test_workflow_honours_registered_binding(self):
+        self.assertEqual(
+            _binding_mismatches(self.values, self.workflow_text), [],
+            "npm-publish.yml drifted from the npmjs trusted-publisher "
+            "registration recorded in npm-trusted-publisher.txt",
+        )
+
+    def test_positive_control_environment_mutation_goes_red(self):
+        # PLAN-166 W1 item 4 required control: flipping `environment:`
+        # in a COPY must be detected — otherwise this whole class is a
+        # vacuous gate (registered-vacuous class, S292).
+        needle = "environment: " + self.values["environment"]
+        self.assertIn(needle, self.workflow_text)
+        mutated = self.workflow_text.replace(
+            needle, "environment: NOT-THE-REGISTERED-ENV"
+        )
+        self.assertNotEqual(
+            _binding_mismatches(self.values, mutated), [],
+            "positive control failed: a mutated environment was not "
+            "flagged — the binding check is vacuous",
+        )
+
+    def test_positive_control_repository_mutation_goes_red(self):
+        self.assertIn(self.values["repository"], self.workflow_text)
+        mutated = self.workflow_text.replace(
+            self.values["repository"], "someone-else/some-fork"
+        )
+        self.assertNotEqual(
+            _binding_mismatches(self.values, mutated), [],
+            "positive control failed: a mutated repository slug was not "
+            "flagged — the binding check is vacuous",
+        )
+
+
+# ---------------------------------------------------------------------
+# PLAN-166 W1-B — structural asserts for the release.yml verdict delta +
+# ancestry gate (F2 server side; re-pass r15+r17+r18, debate r3 scoped
+# VETO). Merged verbatim from the W1-B slice file
+# (test_release_workflow_asserts_w1b.py) by the PLAN-166 ceremony
+# assembler — one runnable asserts file per the W1 pack discipline. Only
+# names that would collide with the W1-A section above were renamed
+# (_MARKER → _MARKER_W1B, _LIVE_WF/_STAGED_WF → _W1B_*).
+#
+# What is pinned here, and why each pin exists:
+# - The gate step exists, carries NO continue-on-error, and FAILS CLOSED
+#   on CEO_PAIR_RAIL_VERDICT_OPTIONAL=1 — the step-15 neighbourhood has
+#   two escape hatches keyed to that var (`continue-on-error:` and the
+#   empty `--parent-sha ""` bind, which the validator only binds when
+#   non-empty); the new gate must never inherit the switch.
+# - The delta decision is DELEGATED to
+#   .claude/scripts/local/_release_tag_guard.py (the reference
+#   implementation) — never re-implemented in bash.
+# - Ancestry covers BOTH the reviewed parent AND GITHUB_SHA (r18:
+#   parent-only lets the tag-without-push / orphan-verdict scenario pass).
+# - PINNED ORDER: Verify tag GPG signature → Validate pair-rail verdict →
+#   delta → ancestry.
+# - The job keeps the exact name `release-gate` — the W1-A
+#   await-release-gate poller resolves the job BY NAME via the Actions
+#   jobs endpoint; renaming the job silently breaks the npm-publish gate.
+# ---------------------------------------------------------------------
+
+# Marker written into the W1-B step's comment block; its presence in the
+# LIVE file means the ceremony landed and the live copy is authoritative.
+_MARKER_W1B = "PLAN-166 W1-B"
+
+_W1B_LIVE_WF = _WF / "release.yml"
+_W1B_STAGED_WF = _STAGED_166_WF / "release.yml"
+
+_W1B_STEP_NAME = "Verify verdict delta + ancestry (fail-closed)"
+_W1B_STEP15_NAME = "Validate pair-rail verdict"
+_W1B_GPG_STEP_NAME = "Verify tag GPG signature"
+_GUARD_MODULE = ".claude/scripts/local/_release_tag_guard.py"
+
+
+def _w1b_release_text() -> Optional[Tuple[str, str]]:
+    """Return (text, context) for release.yml, or None pre-landing.
+
+    Priority: live copy carrying the W1-B marker (post-landing,
+    authoritative) → staged ceremony copy (pre-landing local mirror;
+    gitignored so absent in CI) → None (pre-landing CI: skip).
+    """
+    if _W1B_LIVE_WF.is_file():
+        live = _W1B_LIVE_WF.read_text(encoding="utf-8")
+        if _MARKER_W1B in live:
+            return live, "live"
+    if _W1B_STAGED_WF.is_file():
+        return _W1B_STAGED_WF.read_text(encoding="utf-8"), "staged"
+    return None
+
+
+def _step_block(source: str, step_name: str) -> str:
+    """The text of one step: from its `- name:` to the next step/job."""
+    start = source.index("- name: %s" % step_name)
+    nxt = source.find("\n      - name:", start + 1)
+    job = source.find("\n  publish-release:", start + 1)
+    candidates = [i for i in (nxt, job) if i != -1]
+    end = min(candidates) if candidates else len(source)
+    return source[start:end]
+
+
+class W1BReleaseGateDeltaAncestryTest(TestEnvContext):
+    """The verdict delta + ancestry gate step (dual-context)."""
+
+    def setUp(self):
+        super().setUp()
+        resolved = _w1b_release_text()
+        if resolved is None:
+            self.skipTest(
+                "PLAN-166 W1-B release.yml not landed and staged mirror "
+                "absent (pre-landing CI window)"
+            )
+        self.source, self.context = resolved
+
+    # -- existence + independence from the step-15 escape hatches --------
+
+    def test_gate_step_present(self):
+        self.assertIn(
+            "- name: %s" % _W1B_STEP_NAME, self.source,
+            "the W1-B verdict delta + ancestry gate step is missing",
+        )
+
+    def test_gate_step_has_no_continue_on_error(self):
+        block = _step_block(self.source, _W1B_STEP_NAME)
+        self.assertNotIn(
+            "continue-on-error", block,
+            "the W1-B gate must NEVER carry continue-on-error — that is "
+            "exactly the step-15 escape hatch it exists to be independent "
+            "of (debate r3 scoped VETO)",
+        )
+
+    def test_file_carries_exactly_one_continue_on_error(self):
+        # The legacy step 15 keeps its documented transition hatch
+        # UNCHANGED (the plan adds a new step; it does not rewrite the
+        # neighbourhood). Exactly one KEY occurrence pins both
+        # directions at once: the hatch was not silently removed from
+        # step 15, and no step (new or old) gained a second one. Comment
+        # mentions of the phrase do not count — only the YAML key form.
+        key_form = re.findall(
+            r"^\s*continue-on-error:", self.source, re.MULTILINE
+        )
+        self.assertEqual(
+            len(key_form), 1,
+            "release.yml must carry exactly one continue-on-error KEY "
+            "(the legacy step-15 transition hatch); found %d"
+            % len(key_form),
+        )
+
+    def test_gate_fails_closed_on_transition_var(self):
+        block = _step_block(self.source, _W1B_STEP_NAME)
+        self.assertIn(
+            'if [ "${CEO_PAIR_RAIL_VERDICT_OPTIONAL}" = "1" ]', block,
+            "the W1-B gate must test the transition var explicitly",
+        )
+        guard = block.index(
+            'if [ "${CEO_PAIR_RAIL_VERDICT_OPTIONAL}" = "1" ]'
+        )
+        self.assertIn(
+            "exit 1", block[guard:guard + 400],
+            "the transition-var guard must FAIL CLOSED (exit 1), not skip",
+        )
+
+    def test_gate_never_builds_an_empty_parent_bind(self):
+        # The step-15 hatch shape: PARENT_SHA_ARG="" under the var. The
+        # W1-B block must not contain that shape in any form.
+        block = _step_block(self.source, _W1B_STEP_NAME)
+        self.assertNotIn('PARENT_SHA_ARG=""', block)
+        self.assertNotIn('--parent-sha ""', block)
+
+    def test_gate_binds_parent_sha_independently(self):
+        block = _step_block(self.source, _W1B_STEP_NAME)
+        self.assertIn(
+            'VERDICT_FILE_COMMIT="$(git log -n1 --format=%H -- "$VERDICT_FILE")"',
+            block,
+            "the gate must derive the verdict-file commit itself",
+        )
+        self.assertIn(
+            "_parse_verdict", block,
+            "the verdict's parent_sha must be read with the guard "
+            "module's parser — two readers of the same signed file must "
+            "not be able to disagree",
+        )
+
+    # -- delegation to the reference implementation ----------------------
+
+    def test_delta_delegates_to_guard_module(self):
+        block = _step_block(self.source, _W1B_STEP_NAME)
+        self.assertIn(
+            "%s delta" % _GUARD_MODULE, block,
+            "the delta decision must be delegated to the tag-guard "
+            "module (single source of the decision logic)",
+        )
+
+    def test_ancestry_delegates_to_guard_module(self):
+        block = _step_block(self.source, _W1B_STEP_NAME)
+        self.assertIn(
+            "%s ancestry" % _GUARD_MODULE, block,
+            "the HEAD-ancestry judgment (fail-closed fetch included) "
+            "must be delegated to the tag-guard module",
+        )
+
+    def test_delta_semantics_not_reimplemented_in_bash(self):
+        # The bash body must not carry the decision vocabulary of the
+        # module — reading the allowlist or hashing the manifest in
+        # shell would be a second implementation of the same closed-set
+        # semantics. Comment lines are excluded: the step's rationale
+        # comment legitimately NAMES what the module does; only CODE
+        # lines may not do it.
+        block = _step_block(self.source, _W1B_STEP_NAME)
+        code_lines = "\n".join(
+            line for line in block.splitlines()
+            if not line.lstrip().startswith("#")
+        )
+        for forbidden in ("delta_allowlist", "shasum -c", "shasum -a 256"):
+            self.assertNotIn(
+                forbidden, code_lines,
+                "the W1-B step re-implements delta semantics in bash "
+                "(%r found outside comments) — the module is the only "
+                "implementation" % forbidden,
+            )
+
+    # -- ancestry covers parent AND GITHUB_SHA (r18) ----------------------
+
+    def test_ancestry_covers_reviewed_parent(self):
+        block = _step_block(self.source, _W1B_STEP_NAME)
+        self.assertIn(
+            'git merge-base --is-ancestor "$PARENT_SHA" origin/main',
+            block,
+            "the reviewed parent must be judged against origin/main "
+            "(r17: the delta alone never proves the parent was on main)",
+        )
+
+    def test_ancestry_covers_github_sha_via_head_identity(self):
+        block = _step_block(self.source, _W1B_STEP_NAME)
+        self.assertIn(
+            'if [ "$HEAD_SHA" != "${GITHUB_SHA}" ]', block,
+            "HEAD == GITHUB_SHA must be asserted so the module's "
+            "HEAD-ancestry check covers the tagged commit itself (r18)",
+        )
+
+    # -- pinned order (WaveB5 order-assert pattern) -----------------------
+
+    def test_pinned_step_order(self):
+        i_gpg = self.source.index("- name: %s" % _W1B_GPG_STEP_NAME)
+        i_verdict = self.source.index("- name: %s" % _W1B_STEP15_NAME)
+        i_gate = self.source.index("- name: %s" % _W1B_STEP_NAME)
+        self.assertLess(
+            i_gpg, i_verdict,
+            "pinned order broken: GPG verify must precede the verdict "
+            "validation",
+        )
+        self.assertLess(
+            i_verdict, i_gate,
+            "pinned order broken: the verdict validation (step 15) must "
+            "precede the delta+ancestry gate",
+        )
+
+    def test_pinned_order_inside_gate_delta_before_ancestry(self):
+        block = _step_block(self.source, _W1B_STEP_NAME)
+        self.assertLess(
+            block.index("%s delta" % _GUARD_MODULE),
+            block.index("%s ancestry" % _GUARD_MODULE),
+            "pinned order broken inside the gate: delta before ancestry",
+        )
+        self.assertLess(
+            block.index("%s ancestry" % _GUARD_MODULE),
+            block.index('git merge-base --is-ancestor "$PARENT_SHA"'),
+            "pinned order broken inside the gate: module ancestry "
+            "(fetch + HEAD) before the parent merge-base judgment — the "
+            "parent must be judged against the freshly fetched ref",
+        )
+
+    def test_gate_lives_inside_release_gate_job(self):
+        # The step must run in the same job whose success the W1-A await
+        # poller grants on — a gate in another job would not gate the
+        # publish path.
+        i_job = self.source.index("\n  release-gate:")
+        i_next_job = self.source.index("\n  publish-release:")
+        i_gate = self.source.index("- name: %s" % _W1B_STEP_NAME)
+        self.assertTrue(
+            i_job < i_gate < i_next_job,
+            "the delta+ancestry gate must be a step of the release-gate "
+            "job",
+        )
+
+
+class W1BReleaseGateJobNameTest(TestEnvContext):
+    """The exact job name `release-gate` is load-bearing (W1-A await)."""
+
+    def setUp(self):
+        super().setUp()
+        resolved = _w1b_release_text()
+        if resolved is None:
+            self.skipTest(
+                "PLAN-166 W1-B release.yml not landed and staged mirror "
+                "absent (pre-landing CI window)"
+            )
+        self.source, self.context = resolved
+
+    def test_release_gate_job_name_exact(self):
+        self.assertRegex(
+            self.source, re.compile(r"^  release-gate:$", re.MULTILINE),
+            "the job MUST keep the exact name `release-gate` — the "
+            "W1-A await-release-gate poller resolves it BY NAME via the "
+            "Actions jobs endpoint",
+        )
+
+    def test_publish_release_still_needs_release_gate(self):
+        self.assertIn(
+            "needs: release-gate", self.source,
+            "publish-release must stay gated on release-gate",
+        )
+
+
+class W1BGuardModuleContractTest(TestEnvContext):
+    """The live module surface the workflow step depends on.
+
+    These asserts pin the CONTRACT the W1-B step consumes, so a module
+    refactor that renames a subcommand or the parser is caught by the
+    suite before it bricks a release run.
+    """
+
+    def setUp(self):
+        super().setUp()
+        self.module_path = _REPO / _GUARD_MODULE
+        if not self.module_path.is_file():
+            self.fail(
+                "%s missing — the W1-B release.yml step invokes it; "
+                "landing the workflow without the module bricks every "
+                "release run" % _GUARD_MODULE
+            )
+        import importlib.util
+
+        spec = importlib.util.spec_from_file_location(
+            "release_tag_guard_w1b_contract", str(self.module_path)
+        )
+        self.mod = importlib.util.module_from_spec(spec)
+        spec.loader.exec_module(self.mod)
+
+    def test_module_exposes_the_consumed_surface(self):
+        for attr in ("_parse_verdict", "delta", "ancestry", "main"):
+            self.assertTrue(
+                hasattr(self.mod, attr),
+                "module lost %r — the W1-B workflow step consumes it"
+                % attr,
+            )
+
+    def test_parse_verdict_reads_parent_sha(self):
+        fields = self.mod._parse_verdict(
+            "# t\n\n```yaml\nparent_sha: "
+            "4111a115190d375c39c90cc33ac1d9d5899c1cf2\n```\n"
+        )
+        self.assertEqual(
+            fields.get("parent_sha"),
+            "4111a115190d375c39c90cc33ac1d9d5899c1cf2",
+        )
+
+    def test_module_exit_codes_are_distinct_nonzero(self):
+        # The workflow relies on ANY non-zero exit failing the step
+        # (set -euo pipefail); pin that the module's failure codes are
+        # non-zero and mutually distinct so the failure MODE stays
+        # testable.
+        codes = [
+            self.mod.E_USAGE, self.mod.E_FETCH, self.mod.E_NOT_ANCESTOR,
+            self.mod.E_REMOTE_REF, self.mod.E_DELTA,
+            self.mod.E_MANIFEST_PIN, self.mod.E_MANIFEST_CONTENT,
+            self.mod.E_MANIFEST_SET, self.mod.E_VERDICT, self.mod.E_VACUOUS,
+        ]
+        self.assertNotIn(0, codes)
+        self.assertEqual(len(codes), len(set(codes)))
+
+
 if __name__ == "__main__":
     unittest.main()

exec
/bin/zsh -lc 'git diff --no-ext-diff --unified=80 -- ".github/workflows/npm-publish.yml"' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
diff --git a/.github/workflows/npm-publish.yml b/.github/workflows/npm-publish.yml
index aa2e29c..03071be 100644
--- a/.github/workflows/npm-publish.yml
+++ b/.github/workflows/npm-publish.yml
@@ -1,145 +1,296 @@
 name: NPM Publish
 
 # Sprint 5 Phase 4; registry auth migrated to npm **Trusted Publishing**
 # (OIDC) by PLAN-158 Wave 1 (PLAN-152 §Deferred backlog-oidc successor).
 # Publishes ceo-orchestration on tag push (`v*`): the npm CLI (>=11.5.1,
 # upgraded in-job — Node 20 bundles npm 10.x, which cannot do the
 # exchange) detects the GitHub Actions OIDC context (`id-token: write`)
 # and exchanges the per-run JWT for a short-lived publish credential
 # scoped to this repo + workflow + `production-npm` environment as
 # registered in the npmjs.com trusted-publisher config (Owner console).
 # The same JWT keeps feeding the Sigstore `--provenance` attestation.
 # The long-lived NPM_TOKEN is NOT read by this workflow anymore and is
 # REVOKED once the first OIDC GA publish succeeds (until then it exists
 # solely as the rollback path:
 # .claude/plans/PLAN-158/staged/wave1/rollback-oidc-to-token.patch +
 # .claude/plans/PLAN-158/oidc-failure-playbook.md — tag runs pin the
 # workflow to the tag's tree, so a failed GA publish means rollback +
 # delete/re-tag; there is no workflow_dispatch here by design).
 # Manual `npm publish` is not used. The workflow:
 #   1. Verifies VERSION + npm/package.json version + tag are consistent
 #   2. Asserts package.json has zero runtime dependencies
 #   3. Checks the registry for the exact version (PLAN-153 Wave B item 5
 #      `already_published` idempotency guard) — if already present, the
 #      run succeeds as a no-op instead of failing on EPUBLISHCONFLICT
 #   4. Publishes with --provenance (Sigstore-attested)
 #
 # PLAN-013 Phase 0 item 0.2 hardening (debate Round 1 consensus §C5
 # CRITICAL, 2/5 agents — DevOps + Staff Backend):
 #   - Skip RC tags entirely (`if: !contains(github.ref, '-rc.')`) —
 #     pushing `v1.4.0-rc.1` MUST NOT trigger a public npm publish;
 #     that would violate PLAN-013 anti-goal #3 ("NO NPM publish during
 #     Sprint 13") and anti-goal #16 ("NO auto-publish from tag without
 #     manual approval").
 #   - GA tags (`v1.4.0`) gate through `environment: production-npm`,
 #     which requires a manual approval step in GitHub's Environments
 #     settings before the job runs. The manual approval is the
 #     Owner-in-the-loop gate covering the Sprint 17 public-launch
 #     go/no-go decision (private-first strategy per
 #     `project_closure_strategy.md`).
+#
+# ---------------------------------------------------------------------
+# PLAN-166 W1 item 1 (F1, P0) — the publish now OBSERVES the governance
+# gate. `release.yml` and this workflow both fire on `push: tags: v*` as
+# two INDEPENDENT runs; until PLAN-166 nothing made the publish observe
+# the gate, so the only barrier was a human approving `production-npm`
+# with no machine evidence that `release-gate` was green — a live path
+# to publishing an unreviewed tree. A first job (`await-release-gate` —
+# deliberately NO `environment:` and NO RC exclusion, so it runs on RC
+# tags as a live positive control) polls release.yml's `release-gate`
+# JOB (never the run conclusion: CEO_SOTA_DISABLE=1 skips the job while
+# the run stays green) for THIS tag at THIS commit and fail-CLOSED
+# blocks unless it concluded success. `publish` gains
+# `needs: await-release-gate`; its `environment: production-npm`
+# approval and the RC exclusion are VERBATIM unchanged. Deliberate
+# ordering: the Owner's manual-approval prompt only appears AFTER the
+# gate is green — approval can never race ahead of machine evidence —
+# and the `already_published` idempotency guard STAYS in the publish
+# job (last-resort idempotency), not in the gate job. Do not "optimise"
+# the order back.
+#
+# Alternatives REJECTED (do not resurrect without a new debate):
+#   - `workflow_run` trigger: GitHub executes the workflow file from
+#     the DEFAULT branch, not the tag's tree — that kills the rollback
+#     invariant documented above (tag runs pin this workflow to the
+#     tag's tree; a failed GA publish means rollback + delete/re-tag).
+#   - moving the publish into release.yml: npm trusted publishing binds
+#     OIDC by workflow FILENAME
+#     (.claude/plans/PLAN-158/oidc-failure-playbook.md:18) — renaming
+#     the publishing workflow breaks the npmjs registration, plus ~6
+#     test pins on the npm-publish.yml path.
+#   - a reusable `workflow_call` gate shared by both workflows:
+#     refactor candidate, post-GA only (PLAN-166 §Deferred) — not
+#     during an open release window.
+#
+# The trusted-publisher binding triple (repository / workflow filename /
+# environment) is recorded in
+# .claude/governance/npm-trusted-publisher.txt and cross-checked by
+# .claude/scripts/tests/test_release_workflow_asserts.py, which READS
+# that file (embedding the values in the test would be a 4th copy of
+# the truth).
 
 on:
   push:
     tags:
       - "v*"
 
 concurrency:
   group: npm-publish-${{ github.ref }}
   cancel-in-progress: false
 
 permissions:
   contents: read
   id-token: write   # required for OIDC trusted publishing + provenance
 
 jobs:
+  # ---------------------------------------------------------------------
+  # PLAN-166 W1 item 1 (F1, P0) — OBSERVE THE GOVERNANCE GATE.
+  # This job is the machine evidence that release.yml's `release-gate`
+  # job passed for this exact tag+SHA+push. It deliberately carries NO
+  # `environment:` and NO RC exclusion: it runs on rc tags too, which
+  # makes every RC a live positive control of the gate before GA ever
+  # depends on it.
+  # Decision function + battery: .claude/scripts/await_release_gate.py,
+  # .claude/scripts/tests/test_await_release_gate.py.
+  await-release-gate:
+    name: Await release-gate (release.yml)
+    runs-on: ubuntu-latest
+    # 35 > the poller's own 30-minute deadline, so a timeout surfaces as
+    # the decision function's fail-CLOSED BLOCK (with its inputs printed),
+    # not as an opaque runner kill.
+    timeout-minutes: 35
+    permissions:
+      contents: read   # checkout the tag to get the decision script
+      actions: read    # read release.yml's runs + jobs over the REST API
+    env:
+      # `permissions:` alone does NOT authenticate the `gh` CLI on a
+      # hosted runner. Without GH_TOKEN every poll dies on auth, which is
+      # BLOCK (fail-closed) — i.e. it would break EVERY release, RC and
+      # GA alike. This token is the job's only credential; the job has no
+      # id-token and no environment.
+      GH_TOKEN: ${{ github.token }}
+    steps:
+      - name: Checkout tag
+        # SHA-pinned (Sprint 7 Dependabot bump): actions/checkout@v6.0.2
+        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd
+
+      - name: Poll release.yml until release-gate concludes
+        # No `${{ }}` interpolation inside this script by design — every
+        # value arrives through the environment, so no workflow expression
+        # is ever spliced into shell text.
+        run: |
+          set -euo pipefail
+          TAG="${GITHUB_REF_NAME}"
+          DEADLINE=$(( $(date +%s) + 1800 ))
+          SELF_CREATED_AT="$(gh api \
+            "repos/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}" \
+            --jq '.created_at' < /dev/null)"
+          echo "inputs: tag=${TAG} head_sha=${GITHUB_SHA} run_id=${GITHUB_RUN_ID}"
+          echo "inputs: self_created_at=${SELF_CREATED_AT} deadline_epoch=${DEADLINE}"
+
+          fetch_payload() {
+            # One document: every run for THIS head_sha, each carrying its
+            # jobs. A run whose jobs endpoint is unreadable keeps no `jobs`
+            # key — the decision function reads that as WAIT, never GRANT.
+            if ! gh api --paginate \
+                "repos/${GITHUB_REPOSITORY}/actions/runs?head_sha=${GITHUB_SHA}&per_page=100" \
+                --jq '.workflow_runs[] | {id, run_attempt, path, event, head_branch, head_sha, created_at, status, conclusion}' \
+                > runs.ndjson < /dev/null; then
+              # An API error is BLOCK by design (ADR-186: input we cannot
+              # verify is blocked, not waved through).
+              echo '{"api_error": "runs listing failed"}' > payload.json
+              return 0
+            fi
+            : > runs_with_jobs.ndjson
+            while read -r run; do
+              [ -n "${run}" ] || continue
+              rid="$(printf '%s' "${run}" | jq -r '.id')"
+              if ! run_jobs="$(gh api \
+                  "repos/${GITHUB_REPOSITORY}/actions/runs/${rid}/jobs?per_page=100" \
+                  --jq '[.jobs[] | {name, status, conclusion}]' < /dev/null)"; then
+                printf '%s\n' "${run}" >> runs_with_jobs.ndjson
+                continue
+              fi
+              printf '%s' "${run}" \
+                | jq -c --argjson jobs "${run_jobs}" '. + {jobs: $jobs}' \
+                >> runs_with_jobs.ndjson
+            done < runs.ndjson
+            jq -c -s '{workflow_runs: .}' runs_with_jobs.ndjson > payload.json
+          }
+
+          attempt=0
+          while true; do
+            attempt=$(( attempt + 1 ))
+            fetch_payload
+            set +e
+            python3 .claude/scripts/await_release_gate.py \
+              --payload-file payload.json \
+              --tag "${TAG}" \
+              --head-sha "${GITHUB_SHA}" \
+              --self-created-at "${SELF_CREATED_AT}" \
+              --deadline-epoch "${DEADLINE}"
+            rc=$?
+            set -e
+            case "${rc}" in
+              0)
+                echo "::notice::release-gate green for ${TAG} at ${GITHUB_SHA} — publish authorised (poll ${attempt})"
+                exit 0
+                ;;
+              3)
+                sleep 20
+                ;;
+              *)
+                echo "::error::release-gate did not authorise this publish (decision exit ${rc}, poll ${attempt}) — the printed inputs above name the run and job that were evaluated"
+                exit 1
+                ;;
+            esac
+          done
+
   publish:
     # PLAN-013 Phase 0 item 0.2 — RC tag guard.
     # RC tags contain `-rc.` (e.g. `v1.4.0-rc.1`). Skip them entirely.
     # Only GA tags (`v1.4.0`) proceed, and those gate through the
     # `production-npm` environment (manual approval).
     # PLAN-153 Wave B item 5 (f): RC posture UNCHANGED — this exclusion
     # is load-bearing (PLAN-013 anti-goals #3/#16) and MUST survive any
     # future edit to this file; the draft `next` dist-tag idea was
     # DROPPED by ratified debate. Pinned by
     # .claude/scripts/tests/test_release_workflow_asserts.py.
     if: "!contains(github.ref, '-rc.')"
+    # PLAN-166 W1 item 1: publish only starts after `await-release-gate`
+    # proved release.yml's release-gate job green for this exact tag+SHA
+    # (default `success()` semantics of `needs:` — an await failure skips
+    # this job while the run itself goes red). Deliberate ordering: the
+    # production-npm manual-approval prompt appears only AFTER the gate
+    # is green. The `already_published` guard stays below, in this job.
+    needs: await-release-gate
     runs-on: ubuntu-latest
     environment: production-npm
     timeout-minutes: 8
     steps:
       - name: Checkout tag
         # SHA-pinned (Sprint 7 Dependabot bump): actions/checkout@v6.0.2
         uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd
         with:
           fetch-depth: 0
 
       - name: Setup Node 20
         # SHA-pinned: actions/setup-node@v4.1.0
         uses: actions/setup-node@48b55a011bda9f5d6aeb4c2d9c7362e8dae4041e
         with:
           node-version: "20"
           registry-url: "https://registry.npmjs.org"
 
       - name: Upgrade npm CLI for Trusted Publishing (OIDC)
         # PLAN-158 W1 (debate, all 3 critics): Node 20 bundles npm 10.x,
         # which does NOT implement the trusted-publishing token exchange —
         # without this step the OIDC publish dies ENEEDAUTH at GA, and
         # there is no earlier proof point (RC tags skip this workflow
         # entirely). npm >=11.5.1 is the first trusted-publishing-GA CLI.
         run: |
           set -euo pipefail
           npm install -g npm@^11.5.1
           NPM_V="$(npm --version)"
           case "$NPM_V" in
             10.*|11.0.*|11.1.*|11.2.*|11.3.*|11.4.*|11.5.0)
               echo "::error::npm $NPM_V < 11.5.1 — trusted publishing unsupported"
               exit 1
               ;;
           esac
           echo "OK: npm $NPM_V (>=11.5.1, trusted-publishing capable)"
 
       - name: Verify VERSION matches tag
         run: |
           set -euo pipefail
           TAG="${GITHUB_REF_NAME}"
           VERSION_FILE="$(tr -d '[:space:]' < VERSION)"
           EXPECTED="${TAG#v}"
           if [[ "$VERSION_FILE" != "$EXPECTED" ]]; then
             echo "::error::VERSION ($VERSION_FILE) does not match tag ($TAG → $EXPECTED)"
             exit 1
           fi
           echo "OK: VERSION=$VERSION_FILE matches tag=$TAG"
 
       - name: Verify npm/package.json version matches VERSION
         run: |
           set -euo pipefail
           PKG_VERSION=$(node -p "require('./npm/package.json').version")
           VERSION_FILE="$(tr -d '[:space:]' < VERSION)"
           if [[ "$PKG_VERSION" != "$VERSION_FILE" ]]; then
             echo "::error::npm/package.json version ($PKG_VERSION) does not match VERSION ($VERSION_FILE)"
             exit 1
           fi
           echo "OK: npm/package.json version=$PKG_VERSION matches VERSION"
 
       - name: Verify zero runtime dependencies
         run: |
           set -euo pipefail
           DEP_COUNT=$(node -p "Object.keys(require('./npm/package.json').dependencies || {}).length")
           if [[ "$DEP_COUNT" -ne 0 ]]; then
             echo "::error::ceo-orchestration must ship with 0 runtime dependencies (got $DEP_COUNT)"
             exit 1
           fi
           echo "OK: ceo-orchestration has zero runtime dependencies"
 
       - name: Stage bundle into npm/
         # The npm package needs the framework source tree relative to npm/.
         # Copy (don't symlink — npm pack walks symlinks unpredictably across hosts).
         # PLAN-152 tarball-01: SELECTIVE staging. The root .npmignore is INERT
         # (package.json "files" whitelist takes precedence in npm-packlist), so
         # exclusion must happen at stage time. Framework-internal artifacts
         # (test harness, fixture corpora, eval/, red-team corpus, numbered plan
         # trees, _lib/testing.py + _lib/test_isolation.py per the PLAN-120
         # contract install.sh already honors) must NOT ship. Kept deliberately:
         # .claude/plans/ schemas + README + examples/ (install.sh provisions
         # them) and .claude/policies/fixtures/ (install.sh PLAN-014 A.8 ships
         # the policy bundle including fixtures).

exec
/bin/zsh -lc 'git diff --no-ext-diff --unified=60 -- ".github/workflows/npm-publish.yml"' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
diff --git a/.github/workflows/npm-publish.yml b/.github/workflows/npm-publish.yml
index aa2e29c..03071be 100644
--- a/.github/workflows/npm-publish.yml
+++ b/.github/workflows/npm-publish.yml
@@ -1,125 +1,276 @@
 name: NPM Publish
 
 # Sprint 5 Phase 4; registry auth migrated to npm **Trusted Publishing**
 # (OIDC) by PLAN-158 Wave 1 (PLAN-152 §Deferred backlog-oidc successor).
 # Publishes ceo-orchestration on tag push (`v*`): the npm CLI (>=11.5.1,
 # upgraded in-job — Node 20 bundles npm 10.x, which cannot do the
 # exchange) detects the GitHub Actions OIDC context (`id-token: write`)
 # and exchanges the per-run JWT for a short-lived publish credential
 # scoped to this repo + workflow + `production-npm` environment as
 # registered in the npmjs.com trusted-publisher config (Owner console).
 # The same JWT keeps feeding the Sigstore `--provenance` attestation.
 # The long-lived NPM_TOKEN is NOT read by this workflow anymore and is
 # REVOKED once the first OIDC GA publish succeeds (until then it exists
 # solely as the rollback path:
 # .claude/plans/PLAN-158/staged/wave1/rollback-oidc-to-token.patch +
 # .claude/plans/PLAN-158/oidc-failure-playbook.md — tag runs pin the
 # workflow to the tag's tree, so a failed GA publish means rollback +
 # delete/re-tag; there is no workflow_dispatch here by design).
 # Manual `npm publish` is not used. The workflow:
 #   1. Verifies VERSION + npm/package.json version + tag are consistent
 #   2. Asserts package.json has zero runtime dependencies
 #   3. Checks the registry for the exact version (PLAN-153 Wave B item 5
 #      `already_published` idempotency guard) — if already present, the
 #      run succeeds as a no-op instead of failing on EPUBLISHCONFLICT
 #   4. Publishes with --provenance (Sigstore-attested)
 #
 # PLAN-013 Phase 0 item 0.2 hardening (debate Round 1 consensus §C5
 # CRITICAL, 2/5 agents — DevOps + Staff Backend):
 #   - Skip RC tags entirely (`if: !contains(github.ref, '-rc.')`) —
 #     pushing `v1.4.0-rc.1` MUST NOT trigger a public npm publish;
 #     that would violate PLAN-013 anti-goal #3 ("NO NPM publish during
 #     Sprint 13") and anti-goal #16 ("NO auto-publish from tag without
 #     manual approval").
 #   - GA tags (`v1.4.0`) gate through `environment: production-npm`,
 #     which requires a manual approval step in GitHub's Environments
 #     settings before the job runs. The manual approval is the
 #     Owner-in-the-loop gate covering the Sprint 17 public-launch
 #     go/no-go decision (private-first strategy per
 #     `project_closure_strategy.md`).
+#
+# ---------------------------------------------------------------------
+# PLAN-166 W1 item 1 (F1, P0) — the publish now OBSERVES the governance
+# gate. `release.yml` and this workflow both fire on `push: tags: v*` as
+# two INDEPENDENT runs; until PLAN-166 nothing made the publish observe
+# the gate, so the only barrier was a human approving `production-npm`
+# with no machine evidence that `release-gate` was green — a live path
+# to publishing an unreviewed tree. A first job (`await-release-gate` —
+# deliberately NO `environment:` and NO RC exclusion, so it runs on RC
+# tags as a live positive control) polls release.yml's `release-gate`
+# JOB (never the run conclusion: CEO_SOTA_DISABLE=1 skips the job while
+# the run stays green) for THIS tag at THIS commit and fail-CLOSED
+# blocks unless it concluded success. `publish` gains
+# `needs: await-release-gate`; its `environment: production-npm`
+# approval and the RC exclusion are VERBATIM unchanged. Deliberate
+# ordering: the Owner's manual-approval prompt only appears AFTER the
+# gate is green — approval can never race ahead of machine evidence —
+# and the `already_published` idempotency guard STAYS in the publish
+# job (last-resort idempotency), not in the gate job. Do not "optimise"
+# the order back.
+#
+# Alternatives REJECTED (do not resurrect without a new debate):
+#   - `workflow_run` trigger: GitHub executes the workflow file from
+#     the DEFAULT branch, not the tag's tree — that kills the rollback
+#     invariant documented above (tag runs pin this workflow to the
+#     tag's tree; a failed GA publish means rollback + delete/re-tag).
+#   - moving the publish into release.yml: npm trusted publishing binds
+#     OIDC by workflow FILENAME
+#     (.claude/plans/PLAN-158/oidc-failure-playbook.md:18) — renaming
+#     the publishing workflow breaks the npmjs registration, plus ~6
+#     test pins on the npm-publish.yml path.
+#   - a reusable `workflow_call` gate shared by both workflows:
+#     refactor candidate, post-GA only (PLAN-166 §Deferred) — not
+#     during an open release window.
+#
+# The trusted-publisher binding triple (repository / workflow filename /
+# environment) is recorded in
+# .claude/governance/npm-trusted-publisher.txt and cross-checked by
+# .claude/scripts/tests/test_release_workflow_asserts.py, which READS
+# that file (embedding the values in the test would be a 4th copy of
+# the truth).
 
 on:
   push:
     tags:
       - "v*"
 
 concurrency:
   group: npm-publish-${{ github.ref }}
   cancel-in-progress: false
 
 permissions:
   contents: read
   id-token: write   # required for OIDC trusted publishing + provenance
 
 jobs:
+  # ---------------------------------------------------------------------
+  # PLAN-166 W1 item 1 (F1, P0) — OBSERVE THE GOVERNANCE GATE.
+  # This job is the machine evidence that release.yml's `release-gate`
+  # job passed for this exact tag+SHA+push. It deliberately carries NO
+  # `environment:` and NO RC exclusion: it runs on rc tags too, which
+  # makes every RC a live positive control of the gate before GA ever
+  # depends on it.
+  # Decision function + battery: .claude/scripts/await_release_gate.py,
+  # .claude/scripts/tests/test_await_release_gate.py.
+  await-release-gate:
+    name: Await release-gate (release.yml)
+    runs-on: ubuntu-latest
+    # 35 > the poller's own 30-minute deadline, so a timeout surfaces as
+    # the decision function's fail-CLOSED BLOCK (with its inputs printed),
+    # not as an opaque runner kill.
+    timeout-minutes: 35
+    permissions:
+      contents: read   # checkout the tag to get the decision script
+      actions: read    # read release.yml's runs + jobs over the REST API
+    env:
+      # `permissions:` alone does NOT authenticate the `gh` CLI on a
+      # hosted runner. Without GH_TOKEN every poll dies on auth, which is
+      # BLOCK (fail-closed) — i.e. it would break EVERY release, RC and
+      # GA alike. This token is the job's only credential; the job has no
+      # id-token and no environment.
+      GH_TOKEN: ${{ github.token }}
+    steps:
+      - name: Checkout tag
+        # SHA-pinned (Sprint 7 Dependabot bump): actions/checkout@v6.0.2
+        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd
+
+      - name: Poll release.yml until release-gate concludes
+        # No `${{ }}` interpolation inside this script by design — every
+        # value arrives through the environment, so no workflow expression
+        # is ever spliced into shell text.
+        run: |
+          set -euo pipefail
+          TAG="${GITHUB_REF_NAME}"
+          DEADLINE=$(( $(date +%s) + 1800 ))
+          SELF_CREATED_AT="$(gh api \
+            "repos/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}" \
+            --jq '.created_at' < /dev/null)"
+          echo "inputs: tag=${TAG} head_sha=${GITHUB_SHA} run_id=${GITHUB_RUN_ID}"
+          echo "inputs: self_created_at=${SELF_CREATED_AT} deadline_epoch=${DEADLINE}"
+
+          fetch_payload() {
+            # One document: every run for THIS head_sha, each carrying its
+            # jobs. A run whose jobs endpoint is unreadable keeps no `jobs`
+            # key — the decision function reads that as WAIT, never GRANT.
+            if ! gh api --paginate \
+                "repos/${GITHUB_REPOSITORY}/actions/runs?head_sha=${GITHUB_SHA}&per_page=100" \
+                --jq '.workflow_runs[] | {id, run_attempt, path, event, head_branch, head_sha, created_at, status, conclusion}' \
+                > runs.ndjson < /dev/null; then
+              # An API error is BLOCK by design (ADR-186: input we cannot
+              # verify is blocked, not waved through).
+              echo '{"api_error": "runs listing failed"}' > payload.json
+              return 0
+            fi
+            : > runs_with_jobs.ndjson
+            while read -r run; do
+              [ -n "${run}" ] || continue
+              rid="$(printf '%s' "${run}" | jq -r '.id')"
+              if ! run_jobs="$(gh api \
+                  "repos/${GITHUB_REPOSITORY}/actions/runs/${rid}/jobs?per_page=100" \
+                  --jq '[.jobs[] | {name, status, conclusion}]' < /dev/null)"; then
+                printf '%s\n' "${run}" >> runs_with_jobs.ndjson
+                continue
+              fi
+              printf '%s' "${run}" \
+                | jq -c --argjson jobs "${run_jobs}" '. + {jobs: $jobs}' \
+                >> runs_with_jobs.ndjson
+            done < runs.ndjson
+            jq -c -s '{workflow_runs: .}' runs_with_jobs.ndjson > payload.json
+          }
+
+          attempt=0
+          while true; do
+            attempt=$(( attempt + 1 ))
+            fetch_payload
+            set +e
+            python3 .claude/scripts/await_release_gate.py \
+              --payload-file payload.json \
+              --tag "${TAG}" \
+              --head-sha "${GITHUB_SHA}" \
+              --self-created-at "${SELF_CREATED_AT}" \
+              --deadline-epoch "${DEADLINE}"
+            rc=$?
+            set -e
+            case "${rc}" in
+              0)
+                echo "::notice::release-gate green for ${TAG} at ${GITHUB_SHA} — publish authorised (poll ${attempt})"
+                exit 0
+                ;;
+              3)
+                sleep 20
+                ;;
+              *)
+                echo "::error::release-gate did not authorise this publish (decision exit ${rc}, poll ${attempt}) — the printed inputs above name the run and job that were evaluated"
+                exit 1
+                ;;
+            esac
+          done
+
   publish:
     # PLAN-013 Phase 0 item 0.2 — RC tag guard.
     # RC tags contain `-rc.` (e.g. `v1.4.0-rc.1`). Skip them entirely.
     # Only GA tags (`v1.4.0`) proceed, and those gate through the
     # `production-npm` environment (manual approval).
     # PLAN-153 Wave B item 5 (f): RC posture UNCHANGED — this exclusion
     # is load-bearing (PLAN-013 anti-goals #3/#16) and MUST survive any
     # future edit to this file; the draft `next` dist-tag idea was
     # DROPPED by ratified debate. Pinned by
     # .claude/scripts/tests/test_release_workflow_asserts.py.
     if: "!contains(github.ref, '-rc.')"
+    # PLAN-166 W1 item 1: publish only starts after `await-release-gate`
+    # proved release.yml's release-gate job green for this exact tag+SHA
+    # (default `success()` semantics of `needs:` — an await failure skips
+    # this job while the run itself goes red). Deliberate ordering: the
+    # production-npm manual-approval prompt appears only AFTER the gate
+    # is green. The `already_published` guard stays below, in this job.
+    needs: await-release-gate
     runs-on: ubuntu-latest
     environment: production-npm
     timeout-minutes: 8
     steps:
       - name: Checkout tag
         # SHA-pinned (Sprint 7 Dependabot bump): actions/checkout@v6.0.2
         uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd
         with:
           fetch-depth: 0
 
       - name: Setup Node 20
         # SHA-pinned: actions/setup-node@v4.1.0
         uses: actions/setup-node@48b55a011bda9f5d6aeb4c2d9c7362e8dae4041e
         with:
           node-version: "20"
           registry-url: "https://registry.npmjs.org"
 
       - name: Upgrade npm CLI for Trusted Publishing (OIDC)
         # PLAN-158 W1 (debate, all 3 critics): Node 20 bundles npm 10.x,
         # which does NOT implement the trusted-publishing token exchange —
         # without this step the OIDC publish dies ENEEDAUTH at GA, and
         # there is no earlier proof point (RC tags skip this workflow
         # entirely). npm >=11.5.1 is the first trusted-publishing-GA CLI.
         run: |
           set -euo pipefail
           npm install -g npm@^11.5.1
           NPM_V="$(npm --version)"
           case "$NPM_V" in
             10.*|11.0.*|11.1.*|11.2.*|11.3.*|11.4.*|11.5.0)
               echo "::error::npm $NPM_V < 11.5.1 — trusted publishing unsupported"
               exit 1
               ;;
           esac
           echo "OK: npm $NPM_V (>=11.5.1, trusted-publishing capable)"
 
       - name: Verify VERSION matches tag
         run: |
           set -euo pipefail
           TAG="${GITHUB_REF_NAME}"
           VERSION_FILE="$(tr -d '[:space:]' < VERSION)"
           EXPECTED="${TAG#v}"
           if [[ "$VERSION_FILE" != "$EXPECTED" ]]; then
             echo "::error::VERSION ($VERSION_FILE) does not match tag ($TAG → $EXPECTED)"
             exit 1
           fi
           echo "OK: VERSION=$VERSION_FILE matches tag=$TAG"
 
       - name: Verify npm/package.json version matches VERSION
         run: |
           set -euo pipefail
           PKG_VERSION=$(node -p "require('./npm/package.json').version")
           VERSION_FILE="$(tr -d '[:space:]' < VERSION)"
           if [[ "$PKG_VERSION" != "$VERSION_FILE" ]]; then
             echo "::error::npm/package.json version ($PKG_VERSION) does not match VERSION ($VERSION_FILE)"
             exit 1
           fi
           echo "OK: npm/package.json version=$PKG_VERSION matches VERSION"
 
       - name: Verify zero runtime dependencies
         run: |

exec
/bin/zsh -lc 'git diff --no-ext-diff --unified=60 -- ".github/workflows/release.yml"' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
diff --git a/.github/workflows/release.yml b/.github/workflows/release.yml
index 69d7836..596197e 100644
--- a/.github/workflows/release.yml
+++ b/.github/workflows/release.yml
@@ -12,120 +12,147 @@ concurrency:
 jobs:
   release-gate:
     # PLAN-012 Phase 2 CEO_SOTA_DISABLE parity.
     if: vars.CEO_SOTA_DISABLE != '1'
     runs-on: ubuntu-latest
     timeout-minutes: 20
     permissions:
       # `contents: read` for checkout; `actions: read` lets the
       # weekly-workflow status gate (see below) call `gh run list`
       # against the public Actions REST API.
       contents: read
       actions: read
     steps:
       - name: Checkout tag
         # SHA-pinned (Sprint 7 Dependabot bump): actions/checkout@v6.0.2
         uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd
         with:
           fetch-depth: 0
 
       - name: Setup Python 3.11
         # SHA-pinned (Sprint 7 Dependabot bump): actions/setup-python@v6.2.0
         uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405
         with:
           python-version: "3.11"
 
       # -----------------------------------------------------------------
       # PLAN-153 Wave B item 5 (c) — RC-aware VERSION↔tag comparison.
       # Closes PLAN-152 §Deferred `release-gate-rc-version-mismatch`
       # (red run 28663453202 precedent).
       #
       # THE RC FLOW (documented so this never regresses): an RC tag
       # `v<X.Y.Z>-rc.N` is cut from a tree whose VERSION file ALREADY
       # reads the GA value `X.Y.Z` — the `-rc.N` pre-release suffix
       # exists only in the tag name, never in the VERSION file. (The
       # 24h RC-hold gate below encodes the same convention: it derives
       # the RC tag family `v${VERSION}-rc.*` from the GA VERSION.)
       # The old comparison (`FILE != TAG#v`) therefore hard-failed
       # every RC tag's own release run: `v1.0.1-rc.1` vs
       # `VERSION=1.0.1`. Fix: strip a trailing `-rc.<digits>` from the
       # tag before comparing. GA tags are unaffected (nothing to
       # strip); a wrong-version RC (`v1.0.2-rc.1` on `VERSION=1.0.1`)
       # still hard-fails.
       # -----------------------------------------------------------------
       - name: Assert VERSION matches tag
         run: |
           set -euo pipefail
           TAG="${GITHUB_REF_NAME}"
           FILE="$(tr -d '[:space:]' < VERSION)"
           EXPECTED="${TAG#v}"
           BASE="${EXPECTED%-rc.[0-9]*}"
           if [[ "$FILE" != "$BASE" ]]; then
             echo "::error::VERSION file ('$FILE') does not match tag ('$TAG' → expected '$BASE')"
             exit 1
           fi
           if [[ "$EXPECTED" != "$BASE" ]]; then
             echo "OK: VERSION=$FILE matches RC tag=$TAG (compared against base '$BASE' after stripping the -rc.N pre-release suffix)"
           else
             echo "OK: VERSION=$FILE matches tag=$TAG"
           fi
 
+      # -----------------------------------------------------------------
+      # PLAN-166 W1 item 2 (F3, ADR-155-AMEND-1 §5, Forma A (ii)) — the
+      # framework version marker `.claude/.framework-version` is a TRACKED
+      # one-line file, byte-identical to VERSION (the version bump writes
+      # it as a site; verify-counts.sh cross-checks it). This assert is
+      # deliberately UNCONDITIONAL and fail-closed: a missing marker in a
+      # release checkout means the ceremony that introduced it was
+      # reverted or the bump skipped a site — either way the tag must not
+      # ship. Kept NEXT TO the VERSION↔tag assert above so the whole
+      # version-consistency family lives in one place (same convention as
+      # the plugin-manifest step below).
+      # -----------------------------------------------------------------
+      - name: Assert framework-version marker matches VERSION
+        run: |
+          set -euo pipefail
+          FILE="$(tr -d '[:space:]' < VERSION)"
+          if [[ ! -f .claude/.framework-version ]]; then
+            echo "::error::.claude/.framework-version is missing — it is a tracked file (PLAN-166 F3 / ADR-155-AMEND-1); a release checkout without it must not ship"
+            exit 1
+          fi
+          MARKER="$(tr -d '[:space:]' < .claude/.framework-version)"
+          if [[ "$MARKER" != "$FILE" ]]; then
+            echo "::error::.claude/.framework-version ('$MARKER') does not match VERSION ('$FILE') — the marker is byte-identical to VERSION by contract (Forma A (ii), fail-closed)"
+            exit 1
+          fi
+          echo "OK: .claude/.framework-version=$MARKER matches VERSION"
+
       # -----------------------------------------------------------------
       # PLAN-153 Wave B item 5 (e) — version↔plugin-manifest sync, kept
       # NEXT TO the VERSION↔tag assert above so the whole
       # version-consistency family lives in one place.
       #
       # `.claude-plugin/{plugin.json,marketplace.json}` are generated by
       # `build-plugin.py` (Wave B item 6). Until item 6 lands, the
       # manifests do not exist and this step passes with a ::notice
       # (self-arming: the equality checks become enforcing the moment
       # the manifests appear in the tree — no workflow re-edit needed).
       # `marketplace.json`'s schema is owned by build-plugin.py, so we
       # assert on EVERY nested `version` field found rather than
       # hardcoding one JSON path.
       # -----------------------------------------------------------------
       - name: Assert plugin manifest versions match VERSION
         run: |
           set -euo pipefail
           FILE="$(tr -d '[:space:]' < VERSION)"
           if [[ ! -f .claude-plugin/plugin.json ]]; then
             echo "::notice::.claude-plugin/plugin.json not present yet (PLAN-153 Wave B item 6) — sync check self-arms once it lands"
             exit 0
           fi
           PLUGIN_V=$(jq -r '.version // empty' .claude-plugin/plugin.json)
           if [[ "$PLUGIN_V" != "$FILE" ]]; then
             echo "::error::.claude-plugin/plugin.json version ('$PLUGIN_V') does not match VERSION ('$FILE')"
             exit 1
           fi
           echo "OK: plugin.json version=$PLUGIN_V matches VERSION"
           if [[ -f .claude-plugin/marketplace.json ]]; then
             BAD=0
             while IFS= read -r v; do
               [[ -z "$v" ]] && continue
               if [[ "$v" != "$FILE" ]]; then
                 echo "::error::.claude-plugin/marketplace.json carries version '$v' != VERSION ('$FILE')"
                 BAD=1
               fi
             done < <(jq -r '.. | objects | .version? // empty' .claude-plugin/marketplace.json)
             if [[ "$BAD" -ne 0 ]]; then
               exit 1
             fi
             echo "OK: every marketplace.json version field matches VERSION"
           else
             echo "::notice::.claude-plugin/marketplace.json not present — skipping"
           fi
 
       # -----------------------------------------------------------------
       # F5 — RC-hold / staleness waiver SUNSET assertion.
       #
       # The pre-GA waivers in .claude/governance/governance-waivers.yaml
       # are honest ONLY while the project is pre-GA (adopter_count=0).
       # Every existing rc_hold/workflow_staleness entry is a 1.x version
       # carrying "Pre-GA ... adopter_count=0". To stop that 100%-waiver
       # escape from silently following the project into GA, this step
       # FAILS the release the moment any waiver `version` parses >= the
       # configured FIRST_GA floor. The floor is the first version at which
       # the framework intends to claim GA / publish to adopters; per
       # ADR-073 the next major (v2.0.0) is the documented GA/breaking
       # boundary, so 2.0.0 is the mechanical sunset. After the first real
       # adopter ships, lower FIRST_GA (or empty the waiver lists) so the
       # ADR-007 RC-hold + 14-day staleness gates resume real enforcement.
@@ -644,120 +671,257 @@ jobs:
       # continue-on-error: ONLY when CEO_PAIR_RAIL_VERDICT_OPTIONAL=1 env
       # explicitly set (e.g. legacy rc tags pre-verdict-rollout). Default is
       # hard-block on any validator failure.
       - name: Validate pair-rail verdict (PLAN-081 Phase 6-bis step 15)
         env:
           # Codex iter-8 P1 fix: source the env var from a repository
           # variable so the `continue-on-error` expression has something
           # to evaluate against. Owner sets via `gh variable set
           # CEO_PAIR_RAIL_VERDICT_OPTIONAL --body 1` for transition mode
           # (e.g. legacy v1.16.0-era verdicts shipping only commit_sha:);
           # unset / 0 = hard-block (default).
           CEO_PAIR_RAIL_VERDICT_OPTIONAL: ${{ vars.CEO_PAIR_RAIL_VERDICT_OPTIONAL || '0' }}
         continue-on-error: ${{ vars.CEO_PAIR_RAIL_VERDICT_OPTIONAL == '1' }}
         run: |
           set -euo pipefail
           VERDICT_FILE=".claude/governance/pair-rail-verdict-${GITHUB_REF_NAME}.md"
           if [ ! -f "$VERDICT_FILE" ]; then
             if [ "${CEO_PAIR_RAIL_VERDICT_OPTIONAL:-0}" = "1" ]; then
               echo "::notice::no verdict file at $VERDICT_FILE; CEO_PAIR_RAIL_VERDICT_OPTIONAL=1 → skipping"
               exit 0
             fi
             echo "::error::verdict file missing at $VERDICT_FILE — step 15 blocks release"
             exit 1
           fi
           # S104 redesign: resolve PARENT_SHA = parent of the verdict-file
           # commit. The tag commit (${GITHUB_SHA}) is what we're releasing,
           # and the verdict file at $VERDICT_FILE either:
           #   (a) was committed in the tag commit itself → parent = ${GITHUB_SHA}^
           #   (b) was committed earlier (multi-commit prep) → parent = git log of file
           # We use (b)'s general form: find the commit that introduced the
           # current verdict file, then take its parent. This handles both
           # single-commit-with-verdict and multi-commit-prep flows.
           VERDICT_FILE_COMMIT=$(git log -n1 --format=%H -- "$VERDICT_FILE")
           if [ -z "$VERDICT_FILE_COMMIT" ]; then
             echo "::error::cannot resolve commit for $VERDICT_FILE — step 15 fails"
             exit 1
           fi
           PARENT_SHA=$(git rev-parse "${VERDICT_FILE_COMMIT}^" 2>/dev/null || echo "")
           if [ -z "$PARENT_SHA" ]; then
             echo "::error::cannot resolve parent of $VERDICT_FILE_COMMIT — step 15 fails"
             exit 1
           fi
           echo "::notice::S104 bind: VERDICT_FILE_COMMIT=$VERDICT_FILE_COMMIT, PARENT_SHA=$PARENT_SHA"
           # When transition mode is on, allow parent_sha mismatch (skip bind)
           # by passing empty string. Default is hard-bind on PARENT_SHA.
           PARENT_SHA_ARG="$PARENT_SHA"
           if [ "${CEO_PAIR_RAIL_VERDICT_OPTIONAL:-0}" = "1" ]; then
             PARENT_SHA_ARG=""
           fi
           python3 .github/scripts/validate-pair-rail-verdict.py \
             --verdict-file "$VERDICT_FILE" \
             --parent-sha "$PARENT_SHA_ARG" \
             --release-tag "${GITHUB_REF_NAME}" \
             --max-age-hours 24 \
             --recompute-inputs-hash \
             --codex-cli-pin-file .claude/governance/codex-cli-pin.txt \
             --codex-cli-binary-sha256-file .claude/governance/codex-cli-binary-sha256.txt \
             --codex-pin-manifest-file .claude/governance/codex-cli-pin-manifest.json \
             --inputs-hash-paths-file .claude/governance/pair-rail-inputs-hash-manifest.txt
 
+      # ==========================================================
+      # PLAN-166 W1-B — verdict delta + ancestry gate (F2 server side)
+      # ==========================================================
+      # Re-pass findings r15 + r17 + r18 (PLAN-166), debate r3 scoped VETO.
+      #
+      # WHY A SEPARATE STEP: the step-15 neighbourhood above carries two
+      # escape hatches keyed to CEO_PAIR_RAIL_VERDICT_OPTIONAL —
+      # `continue-on-error:` on the step itself, and an empty
+      # `--parent-sha ""` bind (the validator only binds the field when
+      # args.parent_sha is non-empty). Inheriting that neighbourhood would
+      # inherit the switch. This step therefore:
+      #   - carries NO continue-on-error;
+      #   - FAILS CLOSED when CEO_PAIR_RAIL_VERDICT_OPTIONAL=1: in that
+      #     mode step 15 skipped the parent_sha bind, so the anchor these
+      #     asserts hang off was never validated — there is no transition
+      #     mode here, by design;
+      #   - re-derives and re-binds parent_sha ITSELF (non-empty, 40-hex,
+      #     equal to the verdict's `parent_sha:` read with the SAME parser
+      #     the local tag guard uses) — independent of step 15's outcome,
+      #     which also closes the legacy commit_sha fallback (the
+      #     validator downgrades a missing parent_sha to an ADVISORY when
+      #     a legacy commit_sha is present; this step does not);
+      #   - reuses .claude/scripts/local/_release_tag_guard.py for the
+      #     delta decision — the module marks itself as the reference
+      #     implementation; the semantics are NEVER re-implemented in
+      #     bash (single source of the decision logic);
+      #   - asserts ancestry on origin/main of BOTH the reviewed parent
+      #     AND GITHUB_SHA itself (r18: parent-only lets the
+      #     tag-without-push scenario — verdict V over parent P, tag
+      #     pushed, V never reaches main — pass with P ancestral and V
+      #     orphaned).
+      #
+      # THE INVARIANT (one sentence): nothing landed after what the
+      # re-pass reviewed, other than the verdict for THIS tag and the
+      # evidence it pins by name AND content (sha256 of MANIFEST.sha256
+      # in the signed verdict + `shasum -c` over the evidence set).
+      #
+      # PINNED ORDER (asserted structurally by the W1B* classes of
+      # test_release_workflow_asserts.py, WaveB5 pattern):
+      #   Verify tag GPG signature → Validate pair-rail verdict →
+      #   delta → ancestry.
+      # Do not reorder, do not merge into step 15.
+      - name: Verify verdict delta + ancestry (fail-closed)
+        env:
+          CEO_PAIR_RAIL_VERDICT_OPTIONAL: ${{ vars.CEO_PAIR_RAIL_VERDICT_OPTIONAL || '0' }}
+        run: |
+          set -euo pipefail
+          # (0) No transition mode: with the var on, the parent_sha bind
+          # upstream was skipped — refuse to certify against an
+          # unvalidated anchor. Fail closed, loudly.
+          if [ "${CEO_PAIR_RAIL_VERDICT_OPTIONAL}" = "1" ]; then
+            echo "::error::CEO_PAIR_RAIL_VERDICT_OPTIONAL=1 is set, but the delta+ancestry gate has no transition mode — it fails closed by design (PLAN-166 debate r3). Unset the repo variable (gh variable delete CEO_PAIR_RAIL_VERDICT_OPTIONAL) and re-run."
+            exit 1
+          fi
+          TAG="${GITHUB_REF_NAME}"
+          VERDICT_FILE=".claude/governance/pair-rail-verdict-${TAG}.md"
+          if [ ! -f "$VERDICT_FILE" ]; then
+            echo "::error::no signed verdict at $VERDICT_FILE — the delta+ancestry gate has no optional mode; the re-pass verdict for THIS tag must be committed on the tagged tree."
+            exit 1
+          fi
+          # (1) Checkout sanity: every assert below anchors on HEAD, so
+          # HEAD must BE the tagged commit this run is about.
+          HEAD_SHA="$(git rev-parse HEAD)"
+          if [ "$HEAD_SHA" != "${GITHUB_SHA}" ]; then
+            echo "::error::checkout HEAD ($HEAD_SHA) != GITHUB_SHA (${GITHUB_SHA}) — refusing to assert against the wrong tree"
+            exit 1
+          fi
+          # (2) Independent parent_sha bind — non-empty by construction,
+          # controlled by no variable. Same derivation as step 15 (parent
+          # of the commit that introduced the verdict file); the verdict
+          # field is read with the SAME parser the local tag guard uses
+          # (_parse_verdict), so two readers of the same signed file
+          # cannot disagree about what it says.
+          VERDICT_FILE_COMMIT="$(git log -n1 --format=%H -- "$VERDICT_FILE")"
+          if [ -z "$VERDICT_FILE_COMMIT" ]; then
+            echo "::error::cannot resolve the commit that introduced $VERDICT_FILE — refusing an empty bind"
+            exit 1
+          fi
+          PARENT_SHA="$(git rev-parse "${VERDICT_FILE_COMMIT}^" 2>/dev/null || echo "")"
+          if [ -z "$PARENT_SHA" ]; then
+            echo "::error::cannot resolve parent of ${VERDICT_FILE_COMMIT} — refusing an empty bind"
+            exit 1
+          fi
+          python3 - "$VERDICT_FILE" "$PARENT_SHA" <<'PYBIND'
+          import importlib.util
+          import io
+          import re
+          import sys
+
+          verdict_path, expected = sys.argv[1], sys.argv[2]
+          if not re.match(r"\A[0-9a-f]{40}\Z", expected):
+              sys.exit("FAIL: derived parent %r is not a 40-hex SHA" % expected)
+          spec = importlib.util.spec_from_file_location(
+              "release_tag_guard", ".claude/scripts/local/_release_tag_guard.py"
+          )
+          mod = importlib.util.module_from_spec(spec)
+          spec.loader.exec_module(mod)
+          with io.open(verdict_path, encoding="utf-8") as fh:
+              fields = mod._parse_verdict(fh.read())
+          declared = fields.get("parent_sha")
+          if declared != expected:
+              sys.exit(
+                  "FAIL: verdict parent_sha %r != parent of the verdict-file "
+                  "commit (%s) — the anchor was not validated with a "
+                  "non-empty bind; a legacy commit_sha fallback does NOT "
+                  "count here." % (declared, expected)
+              )
+          print("  ok   parent_sha bind: %s (derived independently of step 15)" % expected)
+          PYBIND
+          # (3) DELTA (r15): git diff <reviewed parent>..<tag commit>
+          # must be contained in the CLOSED set pinned in the signed
+          # verdict — exact names per tag (never the pair-rail-verdict-*
+          # wildcard, never repass-<N>/**), set equality against the
+          # evidence MANIFEST.sha256, AND content equality (the verdict
+          # pins the manifest's sha256; the guard runs `shasum -c` over
+          # it). Any extra path = FAIL. Decision logic lives in the local
+          # tag guard module — reused, never re-implemented in bash.
+          python3 .claude/scripts/local/_release_tag_guard.py delta \
+            --repo . --tag "$TAG"
+          # (4) ANCESTRY (r17+r18): both the reviewed parent AND the
+          # tagged commit itself must be ancestors of origin/main. The
+          # module's ancestry subcommand judges HEAD (== GITHUB_SHA,
+          # asserted in (1)) after a FAIL-CLOSED fetch of origin/main —
+          # a failed fetch is a stop, never a stale-ref approval. The
+          # reviewed parent is then judged against the same freshly
+          # fetched ref.
+          python3 .claude/scripts/local/_release_tag_guard.py ancestry \
+            --repo . --remote origin --branch main
+          if git merge-base --is-ancestor "$PARENT_SHA" origin/main; then
+            echo "  ok   reviewed parent $PARENT_SHA is an ancestor of origin/main"
+          else
+            RC=$?
+            echo "::error::reviewed parent $PARENT_SHA is not on origin/main (merge-base exit $RC) — the verdict is anchored on a commit main never saw (tag-without-push / orphan-verdict scenario, r17+r18)"
+            exit 1
+          fi
+          echo "OK: verdict delta + ancestry asserts all green for $TAG"
+
   publish-release:
     name: Publish GitHub Release + assets
     needs: release-gate
     runs-on: ubuntu-latest
     permissions:
       contents: write
     steps:
       - name: Checkout tag
         # SHA-pinned: actions/checkout@v6.0.2
         uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd
         with:
           fetch-depth: 0
       - name: Setup Python 3.11
         # SHA-pinned: actions/setup-python@v6.2.0
         uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405
         with:
           python-version: "3.11"
       - name: Compute install.sh.sha256 (body excluding self-SHA trailer)
         run: |
           set -euo pipefail
           FILE="scripts/install.sh"
           HASH=$(awk 'NR==FNR{n++; next} FNR < n' "$FILE" "$FILE" | sha256sum | awk '{print $1}')
           printf '%s  install.sh\n' "$HASH" > install.sh.sha256
           echo "install.sh.sha256 = $HASH"
       - name: Generate CycloneDX SBOM
         run: |
           set -euo pipefail
           python3 .claude/scripts/generate-sbom.py --output sbom.cyclonedx.json
       # -----------------------------------------------------------------
       # PLAN-153 Wave B item 5 (d) — templatized release notes.
       # Closes PLAN-152 §Deferred `release-notes-hardcoded-first-release`:
       # the notes string used to hardcode a v1.0.0-only launch sentence,
       # stale for every later tag. Notes are now rendered from
       # `.github/release-notes-template.md` with {{TAG}} / {{VERSION}} /
       # {{BASE_VERSION}} interpolation (BASE_VERSION = VERSION with any
       # -rc.N suffix stripped, so RC notes point at the GA CHANGELOG
       # section). Fail-closed on a missing template or an unrendered
       # placeholder.
       # -----------------------------------------------------------------
       - name: Render release notes from template
         run: |
           set -euo pipefail
           TAG="${GITHUB_REF_NAME}"
           VERSION="${TAG#v}"
           BASE_VERSION="${VERSION%-rc.[0-9]*}"
           TEMPLATE=".github/release-notes-template.md"
           if [[ ! -f "$TEMPLATE" ]]; then
             echo "::error::release-notes template missing at $TEMPLATE"
             exit 1
           fi
           sed -e "s/{{TAG}}/${TAG}/g" \
               -e "s/{{VERSION}}/${VERSION}/g" \
               -e "s/{{BASE_VERSION}}/${BASE_VERSION}/g" \
               "$TEMPLATE" > release-notes.md
           if grep -q '{{' release-notes.md; then
             echo "::error::unrendered placeholders remain in release-notes.md"
             exit 1
           fi
           echo "Rendered release notes:"
           cat release-notes.md

exec
/bin/zsh -lc 'git diff --no-ext-diff --unified=60 -- ".github/workflows/smoke-install.yml"' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
diff --git a/.github/workflows/smoke-install.yml b/.github/workflows/smoke-install.yml
index e1317fb..5794f0b 100644
--- a/.github/workflows/smoke-install.yml
+++ b/.github/workflows/smoke-install.yml
@@ -1,127 +1,242 @@
 name: Smoke Install
 
 on:
   pull_request:
     paths:
       - "scripts/install.sh"
       - "scripts/upgrade.sh"
       # PLAN-161 (CI wiring): upgrade oracles + the manifest lib they
       # exercise — keep BOTH filter lists (pull_request + push) in sync.
       - "scripts/_framework_manifest_set.sh"
+      # The ownership + parity e2e call _hash_file/_hash_stdin from here, and
+      # this workflow is their ONLY CI execution — without the helper in the
+      # filter, a PR touching only it skips the gate entirely (codex W1
+      # round 10, P2: the "red gate nobody runs" class, one level deeper).
+      - "scripts/_hash_lib.sh"
       - "scripts/tests/test-upgrade-dryrun-identity.sh"
       - "scripts/tests/test-upgrade-exclusions.sh"
       - "scripts/tests/smoke-install.sh"
+      # PLAN-166 F4 (OQ-4): the install/upgrade parity e2e and its classifier.
+      # The finding this closes is "a red gate nobody runs" (5th instance) --
+      # an unwired test is the same as no test.
+      - "scripts/tests/test-install-upgrade-parity-e2e.sh"
+      - "scripts/tests/_parity_classify.py"
+      # PLAN-166 F3 (ADR-155-AMEND-1): delivery-record ownership e2e —
+      # scripts/tests/*.sh runs ONLY in this workflow (same r11/r20 wiring
+      # rule as the parity e2e above).
+      - "scripts/tests/test-upgrade-spec-ownership.sh"
       - "templates/**"
-      - "SPEC/v1/install-cli.md"
+      # Widened from SPEC/v1/install-cli.md: SPEC/v1 is delivered by install.sh
+      # and (until F3) by nothing in upgrade.sh, so ANY SPEC/v1 change is a
+      # parity event, not just the CLI contract doc.
+      - "SPEC/v1/**"
+      # PLAN-166 F4 wiring (r11/r20): scripts/tests/*.sh runs ONLY here, so a
+      # PR touching just one of these would otherwise skip the regression.
+      - "scripts/doctor.sh"
+      - ".claude/.framework-version"
+      - ".claude/scripts/check-framework-updates.sh"
       - ".github/workflows/smoke-install.yml"
       # PLAN-006 Phase 1 (Sprint 6): Adapter Layer migration changes
       # install-time expectations (hook import paths, contract). Scope
       # broadened for the sprint; narrow back post-Sprint-7 closeout.
       - ".claude/hooks/**"
   push:
     branches:
       - main
     paths:
+      # KEEP IDENTICAL to the pull_request list above. The two had already
+      # drifted (push was missing SPEC/v1 and this workflow file); PLAN-166 F4
+      # re-syncs them, because a filter that fires on the PR and not on the
+      # merge is a gate with a hole in it.
       - "scripts/install.sh"
       - "scripts/upgrade.sh"
       - "scripts/_framework_manifest_set.sh"
+      - "scripts/_hash_lib.sh"
       - "scripts/tests/test-upgrade-dryrun-identity.sh"
       - "scripts/tests/test-upgrade-exclusions.sh"
       - "scripts/tests/smoke-install.sh"
+      - "scripts/tests/test-install-upgrade-parity-e2e.sh"
+      - "scripts/tests/_parity_classify.py"
+      - "scripts/tests/test-upgrade-spec-ownership.sh"
       - "templates/**"
+      - "SPEC/v1/**"
+      - "scripts/doctor.sh"
+      - ".claude/.framework-version"
+      - ".claude/scripts/check-framework-updates.sh"
+      - ".github/workflows/smoke-install.yml"
       - ".claude/hooks/**"
 
 concurrency:
   group: smoke-install-${{ github.ref }}
   cancel-in-progress: true
 
 jobs:
   smoke:
     # PLAN-012 Phase 2 CEO_SOTA_DISABLE parity.
     if: vars.CEO_SOTA_DISABLE != '1'
     runs-on: ubuntu-latest
     # PLAN-161: 5 -> 8 — headroom for the two upgrade oracles (each runs
     # full install + upgrade legs against fixture adopter repos).
-    timeout-minutes: 8
+    # PLAN-166 F4: 8 -> 20. MEASURED, not guessed. The parity e2e runs 2 full
+    # install legs + 1 upgrade leg PER ceremony mode, and the positive control
+    # runs the same again with a planted divergence: 12 install/upgrade
+    # operations added to this job. Local wall time (Darwin arm64, 16 cores,
+    # 2026-08-05): gate 122s + control 118s = 240s. A 2-core ubuntu-latest
+    # runner is the usual 2-3x slower, i.e. 8-12 min of NEW work on top of the
+    # ~5 min this job already spent. 15 would sit inside the noise band, and
+    # the perf-gate N=20 flake (PLAN-159) was exactly that mistake. Re-tighten
+    # once real CI runs give a p95.
+    # PLAN-166 F3 (assembler): 20 -> 25. The spec-ownership e2e adds 4 more
+    # installs + 3 upgrades (S1-S8; ~3-4 min local per the W1-C measurement),
+    # i.e. up to ~8-10 more CI minutes at the same 2-3x factor. Same
+    # anti-flake sizing rule as the F4 bump above.
+    timeout-minutes: 25
     permissions:
       contents: read
     steps:
       - name: Checkout
         # SHA-pinned (Sprint 7 Dependabot bump): actions/checkout@v6.0.2
         uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd
         with:
           fetch-depth: 1
 
+      # PLAN-166 F4: the parity e2e's historical leg installs from a PINNED
+      # TAG. `fetch-depth: 1` produces a checkout with NO tags, so the pin
+      # would not resolve and the gate would die before comparing a single
+      # tree - "it passes on my clone" is precisely the hole this test exists
+      # to close. The pin is READ FROM THE TEST (--print-pin) so the workflow
+      # never becomes a second copy of that truth.
+      - name: Fetch the parity pin tag
+        run: |
+          set -euo pipefail
+          PIN="$(bash scripts/tests/test-install-upgrade-parity-e2e.sh --print-pin)"
+          echo "parity historical pin: $PIN"
+          git fetch --no-tags --depth 1 origin "+refs/tags/$PIN:refs/tags/$PIN"
+          git rev-parse --verify "refs/tags/$PIN^{commit}"
+
       - name: Setup Python 3.11
         # SHA-pinned (Sprint 7 Dependabot bump): actions/setup-python@v6.2.0
         uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405
         with:
           python-version: "3.11"
 
       - name: Install jq (for settings.json merge)
         run: |
           set -euo pipefail
           if ! command -v jq >/dev/null 2>&1; then
             sudo apt-get update -qq
             sudo apt-get install -y -qq jq
           fi
           jq --version
 
       - name: Run smoke install
         run: |
           set -euo pipefail
           bash scripts/tests/smoke-install.sh
 
       # PLAN-161 upgrade oracles (green only once the U1/U2/U3 upgrade.sh
       # fixes are in-tree — land atomically with them).
       - name: Upgrade oracle — --dry-run identity (U1)
         run: |
           set -euo pipefail
           bash scripts/tests/test-upgrade-dryrun-identity.sh
 
       - name: Upgrade oracle — exclusion parity + opt-in purge (U2/U3)
         run: |
           set -euo pipefail
           bash scripts/tests/test-upgrade-exclusions.sh
 
       # WS4-user-ceremony-leg
       - name: Install with --ceremony user (governance rc=0 + no out-of-.claude writes)
         run: |
           set -euo pipefail
           U="$(mktemp -d)"
           ( cd "$U" && git init -q )
           CEO_INSTALL_SKIP_SELF_SHA=1 CEO_RAG_INSTALL_PROMPT=0 \
             bash scripts/install.sh "$U" --ceremony user
           echo '--- validate-governance.sh (user) ---'
           ( cd "$U" && bash .claude/scripts/validate-governance.sh )
           echo '--- assert only .claude/ at top level ---'  # WS4-sc2010-glob
           extra=""
           for _e in "$U"/* "$U"/.[!.]* "$U"/..?*; do
             [ -e "$_e" ] || continue
             _b="$(basename "$_e")"
             case "$_b" in .claude|.git) continue ;; esac
             extra="$extra $_b"
           done
           if [ -n "$extra" ]; then
             echo "::error::--ceremony user wrote outside .claude/:$extra"
             exit 1
           fi
           echo 'user-ceremony leg: PASS'
 
+      # PLAN-166 F4 (OQ-4) - install/upgrade parity on the RESULTING TREES,
+      # per ceremony mode. NO continue-on-error, deliberately: the assertion
+      # this replaces was dead twice over (tautological AND wired into no
+      # workflow), and an escape hatch here would reinstate exactly that.
+      # Exit 2 (KNOWN-OPEN) is a FAILURE too - it NAMES the outstanding
+      # PLAN-166 W1 prerequisites instead of skipping them silently.
+      - name: Install/upgrade parity e2e (maintainer + user ceremony)
+        run: |
+          set -euo pipefail
+          bash scripts/tests/test-install-upgrade-parity-e2e.sh
+
+      # Control of the control (AC-4). With ONE backup_and_replace line deleted
+      # from a COPY of upgrade.sh, the gate above must come back RED in EVERY
+      # ceremony mode. rc must be exactly 1: rc 0/2 means the gate went blind,
+      # rc 9 means the plant stopped biting (vacuous control). Both fail here.
+      # This step MUST stay AFTER the plain gate: if the un-planted run were
+      # already fatal, rc=1 here would prove nothing about the plant.
+      - name: Install/upgrade parity - positive control (planted divergence)
+        run: |
+          set -uo pipefail
+          rc=0
+          bash scripts/tests/test-install-upgrade-parity-e2e.sh \
+            --positive-control > /tmp/parity-control.log 2>&1 || rc=$?
+          if [ "$rc" -ne 1 ]; then
+            cat /tmp/parity-control.log
+            echo "::error::parity positive control returned rc=$rc, expected 1 - the planted install/upgrade divergence did NOT turn the gate red, so the gate above proves nothing"
+            exit 1
+          fi
+          # Second factor, LOAD-BEARING (re-pass closure): under `set -uo
+          # pipefail` (no -e) a non-matching grep would NOT fail the step, so
+          # an rc=1 from a failure UNRELATED to the plant (log with none of
+          # the plant markers) would pass — the registered-vacuous class
+          # (S292) this step exists to close. Demand plant evidence or fail.
+          grep -E "PLANTED|per-mode verdicts|positive control:" /tmp/parity-control.log || {
+            cat /tmp/parity-control.log
+            echo "::error::rc=1 but the log carries no PLANTED/per-mode-verdict evidence - the control went red for an unrelated reason, which proves nothing about the plant (vacuous control)"
+            exit 1
+          }
+          echo "positive control OK: planted divergence -> exit 1 in every ceremony mode"
+
+      # PLAN-166 F3 (ADR-155-AMEND-1, AC-3) — delivery-record ownership of
+      # the three conditional framework surfaces (SPEC/v1, root PROTOCOL.md,
+      # .claude/.framework-version) across install -> upgrade -> doctor ->
+      # updater. Scenarios S1-S8 incl. the forced-refresh route (S2), the
+      # legacy ADOPTER-FORK preserve (S4) and the marker-first updater
+      # regression (S6). Same wiring rationale as the parity e2e above:
+      # scripts/tests/*.sh runs ONLY here — unwired = no test. NO
+      # continue-on-error, deliberately.
+      - name: Upgrade SPEC/marker delivery-record ownership (S1-S8)
+        run: |
+          set -euo pipefail
+          bash scripts/tests/test-upgrade-spec-ownership.sh
+
       - name: Assert npx/npm shim contract (if present)
         # Phase 4 deliverable; skip if directory missing
         run: |
           set -euo pipefail
           if [[ -d "npm" ]]; then
             # Check no runtime deps
             if [[ -f npm/package.json ]]; then
               deps=$(jq '.dependencies // {} | length' npm/package.json)
               if [[ "$deps" -ne 0 ]]; then
                 echo "::error::ceo-orchestration must ship with 0 runtime deps (got $deps)"
                 exit 1
               fi
               echo "OK: npm shim has zero runtime dependencies"
             fi
           else
             echo "npm/ shim not yet present — skipping"
           fi

exec
/bin/zsh -lc 'git diff --no-ext-diff --unified=25 -- .github/workflows/release.yml' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
diff --git a/.github/workflows/release.yml b/.github/workflows/release.yml
index 69d7836..596197e 100644
--- a/.github/workflows/release.yml
+++ b/.github/workflows/release.yml
@@ -47,50 +47,77 @@ jobs:
       # the RC tag family `v${VERSION}-rc.*` from the GA VERSION.)
       # The old comparison (`FILE != TAG#v`) therefore hard-failed
       # every RC tag's own release run: `v1.0.1-rc.1` vs
       # `VERSION=1.0.1`. Fix: strip a trailing `-rc.<digits>` from the
       # tag before comparing. GA tags are unaffected (nothing to
       # strip); a wrong-version RC (`v1.0.2-rc.1` on `VERSION=1.0.1`)
       # still hard-fails.
       # -----------------------------------------------------------------
       - name: Assert VERSION matches tag
         run: |
           set -euo pipefail
           TAG="${GITHUB_REF_NAME}"
           FILE="$(tr -d '[:space:]' < VERSION)"
           EXPECTED="${TAG#v}"
           BASE="${EXPECTED%-rc.[0-9]*}"
           if [[ "$FILE" != "$BASE" ]]; then
             echo "::error::VERSION file ('$FILE') does not match tag ('$TAG' → expected '$BASE')"
             exit 1
           fi
           if [[ "$EXPECTED" != "$BASE" ]]; then
             echo "OK: VERSION=$FILE matches RC tag=$TAG (compared against base '$BASE' after stripping the -rc.N pre-release suffix)"
           else
             echo "OK: VERSION=$FILE matches tag=$TAG"
           fi
 
+      # -----------------------------------------------------------------
+      # PLAN-166 W1 item 2 (F3, ADR-155-AMEND-1 §5, Forma A (ii)) — the
+      # framework version marker `.claude/.framework-version` is a TRACKED
+      # one-line file, byte-identical to VERSION (the version bump writes
+      # it as a site; verify-counts.sh cross-checks it). This assert is
+      # deliberately UNCONDITIONAL and fail-closed: a missing marker in a
+      # release checkout means the ceremony that introduced it was
+      # reverted or the bump skipped a site — either way the tag must not
+      # ship. Kept NEXT TO the VERSION↔tag assert above so the whole
+      # version-consistency family lives in one place (same convention as
+      # the plugin-manifest step below).
+      # -----------------------------------------------------------------
+      - name: Assert framework-version marker matches VERSION
+        run: |
+          set -euo pipefail
+          FILE="$(tr -d '[:space:]' < VERSION)"
+          if [[ ! -f .claude/.framework-version ]]; then
+            echo "::error::.claude/.framework-version is missing — it is a tracked file (PLAN-166 F3 / ADR-155-AMEND-1); a release checkout without it must not ship"
+            exit 1
+          fi
+          MARKER="$(tr -d '[:space:]' < .claude/.framework-version)"
+          if [[ "$MARKER" != "$FILE" ]]; then
+            echo "::error::.claude/.framework-version ('$MARKER') does not match VERSION ('$FILE') — the marker is byte-identical to VERSION by contract (Forma A (ii), fail-closed)"
+            exit 1
+          fi
+          echo "OK: .claude/.framework-version=$MARKER matches VERSION"
+
       # -----------------------------------------------------------------
       # PLAN-153 Wave B item 5 (e) — version↔plugin-manifest sync, kept
       # NEXT TO the VERSION↔tag assert above so the whole
       # version-consistency family lives in one place.
       #
       # `.claude-plugin/{plugin.json,marketplace.json}` are generated by
       # `build-plugin.py` (Wave B item 6). Until item 6 lands, the
       # manifests do not exist and this step passes with a ::notice
       # (self-arming: the equality checks become enforcing the moment
       # the manifests appear in the tree — no workflow re-edit needed).
       # `marketplace.json`'s schema is owned by build-plugin.py, so we
       # assert on EVERY nested `version` field found rather than
       # hardcoding one JSON path.
       # -----------------------------------------------------------------
       - name: Assert plugin manifest versions match VERSION
         run: |
           set -euo pipefail
           FILE="$(tr -d '[:space:]' < VERSION)"
           if [[ ! -f .claude-plugin/plugin.json ]]; then
             echo "::notice::.claude-plugin/plugin.json not present yet (PLAN-153 Wave B item 6) — sync check self-arms once it lands"
             exit 0
           fi
           PLUGIN_V=$(jq -r '.version // empty' .claude-plugin/plugin.json)
           if [[ "$PLUGIN_V" != "$FILE" ]]; then
             echo "::error::.claude-plugin/plugin.json version ('$PLUGIN_V') does not match VERSION ('$FILE')"
@@ -679,50 +706,187 @@ jobs:
             exit 1
           fi
           PARENT_SHA=$(git rev-parse "${VERDICT_FILE_COMMIT}^" 2>/dev/null || echo "")
           if [ -z "$PARENT_SHA" ]; then
             echo "::error::cannot resolve parent of $VERDICT_FILE_COMMIT — step 15 fails"
             exit 1
           fi
           echo "::notice::S104 bind: VERDICT_FILE_COMMIT=$VERDICT_FILE_COMMIT, PARENT_SHA=$PARENT_SHA"
           # When transition mode is on, allow parent_sha mismatch (skip bind)
           # by passing empty string. Default is hard-bind on PARENT_SHA.
           PARENT_SHA_ARG="$PARENT_SHA"
           if [ "${CEO_PAIR_RAIL_VERDICT_OPTIONAL:-0}" = "1" ]; then
             PARENT_SHA_ARG=""
           fi
           python3 .github/scripts/validate-pair-rail-verdict.py \
             --verdict-file "$VERDICT_FILE" \
             --parent-sha "$PARENT_SHA_ARG" \
             --release-tag "${GITHUB_REF_NAME}" \
             --max-age-hours 24 \
             --recompute-inputs-hash \
             --codex-cli-pin-file .claude/governance/codex-cli-pin.txt \
             --codex-cli-binary-sha256-file .claude/governance/codex-cli-binary-sha256.txt \
             --codex-pin-manifest-file .claude/governance/codex-cli-pin-manifest.json \
             --inputs-hash-paths-file .claude/governance/pair-rail-inputs-hash-manifest.txt
 
+      # ==========================================================
+      # PLAN-166 W1-B — verdict delta + ancestry gate (F2 server side)
+      # ==========================================================
+      # Re-pass findings r15 + r17 + r18 (PLAN-166), debate r3 scoped VETO.
+      #
+      # WHY A SEPARATE STEP: the step-15 neighbourhood above carries two
+      # escape hatches keyed to CEO_PAIR_RAIL_VERDICT_OPTIONAL —
+      # `continue-on-error:` on the step itself, and an empty
+      # `--parent-sha ""` bind (the validator only binds the field when
+      # args.parent_sha is non-empty). Inheriting that neighbourhood would
+      # inherit the switch. This step therefore:
+      #   - carries NO continue-on-error;
+      #   - FAILS CLOSED when CEO_PAIR_RAIL_VERDICT_OPTIONAL=1: in that
+      #     mode step 15 skipped the parent_sha bind, so the anchor these
+      #     asserts hang off was never validated — there is no transition
+      #     mode here, by design;
+      #   - re-derives and re-binds parent_sha ITSELF (non-empty, 40-hex,
+      #     equal to the verdict's `parent_sha:` read with the SAME parser
+      #     the local tag guard uses) — independent of step 15's outcome,
+      #     which also closes the legacy commit_sha fallback (the
+      #     validator downgrades a missing parent_sha to an ADVISORY when
+      #     a legacy commit_sha is present; this step does not);
+      #   - reuses .claude/scripts/local/_release_tag_guard.py for the
+      #     delta decision — the module marks itself as the reference
+      #     implementation; the semantics are NEVER re-implemented in
+      #     bash (single source of the decision logic);
+      #   - asserts ancestry on origin/main of BOTH the reviewed parent
+      #     AND GITHUB_SHA itself (r18: parent-only lets the
+      #     tag-without-push scenario — verdict V over parent P, tag
+      #     pushed, V never reaches main — pass with P ancestral and V
+      #     orphaned).
+      #
+      # THE INVARIANT (one sentence): nothing landed after what the
+      # re-pass reviewed, other than the verdict for THIS tag and the
+      # evidence it pins by name AND content (sha256 of MANIFEST.sha256
+      # in the signed verdict + `shasum -c` over the evidence set).
+      #
+      # PINNED ORDER (asserted structurally by the W1B* classes of
+      # test_release_workflow_asserts.py, WaveB5 pattern):
+      #   Verify tag GPG signature → Validate pair-rail verdict →
+      #   delta → ancestry.
+      # Do not reorder, do not merge into step 15.
+      - name: Verify verdict delta + ancestry (fail-closed)
+        env:
+          CEO_PAIR_RAIL_VERDICT_OPTIONAL: ${{ vars.CEO_PAIR_RAIL_VERDICT_OPTIONAL || '0' }}
+        run: |
+          set -euo pipefail
+          # (0) No transition mode: with the var on, the parent_sha bind
+          # upstream was skipped — refuse to certify against an
+          # unvalidated anchor. Fail closed, loudly.
+          if [ "${CEO_PAIR_RAIL_VERDICT_OPTIONAL}" = "1" ]; then
+            echo "::error::CEO_PAIR_RAIL_VERDICT_OPTIONAL=1 is set, but the delta+ancestry gate has no transition mode — it fails closed by design (PLAN-166 debate r3). Unset the repo variable (gh variable delete CEO_PAIR_RAIL_VERDICT_OPTIONAL) and re-run."
+            exit 1
+          fi
+          TAG="${GITHUB_REF_NAME}"
+          VERDICT_FILE=".claude/governance/pair-rail-verdict-${TAG}.md"
+          if [ ! -f "$VERDICT_FILE" ]; then
+            echo "::error::no signed verdict at $VERDICT_FILE — the delta+ancestry gate has no optional mode; the re-pass verdict for THIS tag must be committed on the tagged tree."
+            exit 1
+          fi
+          # (1) Checkout sanity: every assert below anchors on HEAD, so
+          # HEAD must BE the tagged commit this run is about.
+          HEAD_SHA="$(git rev-parse HEAD)"
+          if [ "$HEAD_SHA" != "${GITHUB_SHA}" ]; then
+            echo "::error::checkout HEAD ($HEAD_SHA) != GITHUB_SHA (${GITHUB_SHA}) — refusing to assert against the wrong tree"
+            exit 1
+          fi
+          # (2) Independent parent_sha bind — non-empty by construction,
+          # controlled by no variable. Same derivation as step 15 (parent
+          # of the commit that introduced the verdict file); the verdict
+          # field is read with the SAME parser the local tag guard uses
+          # (_parse_verdict), so two readers of the same signed file
+          # cannot disagree about what it says.
+          VERDICT_FILE_COMMIT="$(git log -n1 --format=%H -- "$VERDICT_FILE")"
+          if [ -z "$VERDICT_FILE_COMMIT" ]; then
+            echo "::error::cannot resolve the commit that introduced $VERDICT_FILE — refusing an empty bind"
+            exit 1
+          fi
+          PARENT_SHA="$(git rev-parse "${VERDICT_FILE_COMMIT}^" 2>/dev/null || echo "")"
+          if [ -z "$PARENT_SHA" ]; then
+            echo "::error::cannot resolve parent of ${VERDICT_FILE_COMMIT} — refusing an empty bind"
+            exit 1
+          fi
+          python3 - "$VERDICT_FILE" "$PARENT_SHA" <<'PYBIND'
+          import importlib.util
+          import io
+          import re
+          import sys
+
+          verdict_path, expected = sys.argv[1], sys.argv[2]
+          if not re.match(r"\A[0-9a-f]{40}\Z", expected):
+              sys.exit("FAIL: derived parent %r is not a 40-hex SHA" % expected)
+          spec = importlib.util.spec_from_file_location(
+              "release_tag_guard", ".claude/scripts/local/_release_tag_guard.py"
+          )
+          mod = importlib.util.module_from_spec(spec)
+          spec.loader.exec_module(mod)
+          with io.open(verdict_path, encoding="utf-8") as fh:
+              fields = mod._parse_verdict(fh.read())
+          declared = fields.get("parent_sha")
+          if declared != expected:
+              sys.exit(
+                  "FAIL: verdict parent_sha %r != parent of the verdict-file "
+                  "commit (%s) — the anchor was not validated with a "
+                  "non-empty bind; a legacy commit_sha fallback does NOT "
+                  "count here." % (declared, expected)
+              )
+          print("  ok   parent_sha bind: %s (derived independently of step 15)" % expected)
+          PYBIND
+          # (3) DELTA (r15): git diff <reviewed parent>..<tag commit>
+          # must be contained in the CLOSED set pinned in the signed
+          # verdict — exact names per tag (never the pair-rail-verdict-*
+          # wildcard, never repass-<N>/**), set equality against the
+          # evidence MANIFEST.sha256, AND content equality (the verdict
+          # pins the manifest's sha256; the guard runs `shasum -c` over
+          # it). Any extra path = FAIL. Decision logic lives in the local
+          # tag guard module — reused, never re-implemented in bash.
+          python3 .claude/scripts/local/_release_tag_guard.py delta \
+            --repo . --tag "$TAG"
+          # (4) ANCESTRY (r17+r18): both the reviewed parent AND the
+          # tagged commit itself must be ancestors of origin/main. The
+          # module's ancestry subcommand judges HEAD (== GITHUB_SHA,
+          # asserted in (1)) after a FAIL-CLOSED fetch of origin/main —
+          # a failed fetch is a stop, never a stale-ref approval. The
+          # reviewed parent is then judged against the same freshly
+          # fetched ref.
+          python3 .claude/scripts/local/_release_tag_guard.py ancestry \
+            --repo . --remote origin --branch main
+          if git merge-base --is-ancestor "$PARENT_SHA" origin/main; then
+            echo "  ok   reviewed parent $PARENT_SHA is an ancestor of origin/main"
+          else
+            RC=$?
+            echo "::error::reviewed parent $PARENT_SHA is not on origin/main (merge-base exit $RC) — the verdict is anchored on a commit main never saw (tag-without-push / orphan-verdict scenario, r17+r18)"
+            exit 1
+          fi
+          echo "OK: verdict delta + ancestry asserts all green for $TAG"
+
   publish-release:
     name: Publish GitHub Release + assets
     needs: release-gate
     runs-on: ubuntu-latest
     permissions:
       contents: write
     steps:
       - name: Checkout tag
         # SHA-pinned: actions/checkout@v6.0.2
         uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd
         with:
           fetch-depth: 0
       - name: Setup Python 3.11
         # SHA-pinned: actions/setup-python@v6.2.0
         uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405
         with:
           python-version: "3.11"
       - name: Compute install.sh.sha256 (body excluding self-SHA trailer)
         run: |
           set -euo pipefail
           FILE="scripts/install.sh"
           HASH=$(awk 'NR==FNR{n++; next} FNR < n' "$FILE" "$FILE" | sha256sum | awk '{print $1}')
           printf '%s  install.sh\n' "$HASH" > install.sh.sha256
           echo "install.sh.sha256 = $HASH"
       - name: Generate CycloneDX SBOM

exec
/bin/zsh -lc "sed -n '1,360p' .claude/scripts/local/_release_tag_guard.py && printf '\\n--- rest ---\\n' && sed -n '360,760p' .claude/scripts/local/_release_tag_guard.py" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
#!/usr/bin/env python3
# ============================================================================
# _release_tag_guard.py — the two fail-closed asserts `tag()` runs before it
# asks the Owner's key to sign anything.
#
# WHY THIS EXISTS (v1.3.0-rc.1 re-pass, F2 + the F1/F2 composite risk):
#
#   (a) ANCESTRY. Nothing verified that the commit being tagged is on main.
#       `bump` could create a local commit AFTER the preflight proved CI green
#       for a different SHA, and `tag()` would sign that never-tested tree.
#       Two DISTINCT failures, never merged into one message: "could not talk
#       to origin" (network/offline — has a named escape hatch) and "HEAD is
#       not an ancestor of origin/main" (a real governance stop). The fetch and
#       the merge-base are SEPARATE statements: a failed fetch followed by a
#       merge-base against a stale ref is a FALSE APPROVAL.
#
#   (b) RESTRICTED DELTA. The invariant is "nothing landed after what the
#       re-pass reviewed, other than the verdict itself". The anchor is the
#       REVIEWED PARENT recorded in the signed verdict — one rule for RC and
#       GA. Anchoring on "the last RC" is wrong in both directions: for the GA
#       it coincides by accident, and for an rc.2 it would reject the very
#       W0/W1 fixes the re-pass just reviewed.
#
#       The allowlist is TAG-SPECIFIC and CLOSED:
#         * never the wildcard `pair-rail-verdict-*.md` — that would let a
#           historical verdict or the template be touched and still pass;
#         * never `repass-<N>/**` — any file dropped into that directory after
#           the review would pass the guard, and the pair-rail step-15 replay
#           does not cover plan artifacts;
#         * so the set closes by NAME (exact paths, set equality against the
#           re-pass MANIFEST) *and* by CONTENT (the verdict pins the sha256 of
#           MANIFEST.sha256, and the manifest itself is verified with
#           `shasum -a 256 -c`);
#         * and a plan path OUTSIDE the manifest directory — where no sha256
#           pins content — is admitted ONLY as `verdict-fields-<TAG>.md` with
#           the literal target tag, at its ONE canonical path (directly in
#           the plan directory containing the manifest dir): the plan file
#           itself, immutable repass history, another tag's verdict-fields,
#           and same-basename look-alikes in any other directory all close by
#           name alone and would carry a post-review edit onto the tag;
#         * the reviewed parent itself must be an ANCESTOR of HEAD —
#           `cat-file -e` proves existence, not lineage, and a fabricated
#           `commit-tree` anchor makes the whole delta trivially clean.
#
# THE LOCAL ASSERT IS NOT ENOUGH. A tag signed by hand skips this driver
# entirely, and the pair-rail step 15 recomputes inputs_hash only over the
# manifest — which deliberately EXCLUDES the bump surfaces. The same assert
# therefore goes server-side into `.github/workflows/release.yml` in PLAN-166
# W1 (release.yml is canonical; it is changed under the GPG ceremony, not
# here). Keep the two implementations in sync: this file is the reference.
#
# Exit codes are distinct so the failure MODE is testable, not just the
# failure:
#   2 usage   3 fetch failed   4 not-ancestor   5 remote ref unusable
#   6 delta outside allowlist  7 manifest sha pin mismatch
#   8 manifest content mismatch (shasum -c)  9 manifest/allowlist set mismatch
#  10 verdict unusable (missing file/field, wildcard, wrong tag, bad parent)
#  11 the assert would be VACUOUS (the verdict is not inside the delta it
#     anchors — e.g. parent_sha == HEAD, which makes the verdict review itself)
#  12 parent_sha is not an ancestor of HEAD (a fabricated/orphan anchor:
#     `cat-file -e` proves existence, not lineage — a `commit-tree` object
#     carrying HEAD's own tree makes diff(parent..HEAD) contain only the
#     verdict while unreviewed work sits on main)
# ============================================================================
"""Ancestry + restricted-delta asserts for the release tag phase."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import subprocess
import sys
from typing import Dict, List, Optional, Sequence, Set, Tuple

E_USAGE = 2
E_FETCH = 3
E_NOT_ANCESTOR = 4
E_REMOTE_REF = 5
E_DELTA = 6
E_MANIFEST_PIN = 7
E_MANIFEST_CONTENT = 8
E_MANIFEST_SET = 9
E_VERDICT = 10
E_VACUOUS = 11
E_PARENT_NOT_ANCESTOR = 12

HEX40 = re.compile(r"\A[0-9a-f]{40}\Z")
HEX64 = re.compile(r"\A[0-9a-f]{64}\Z")
GLOB_CHARS = "*?["
VERDICT_PREFIX = ".claude/governance/pair-rail-verdict-"
# The allowlist is EXHAUSTIVE, not merely closed: the verdict for this tag plus
# plan-side evidence (the `verdict-fields-<TAG>` pair and the re-pass artifact
# directory both live under `.claude/plans/`). Anything else — a version site, a
# workflow, any code path — would re-open the very hole the delta assert exists
# to close: a post-review bump commit riding in on the tag.
EVIDENCE_PREFIX = ".claude/plans/"


def _fail(code: int, msg: str) -> int:
    # Flush the ok-lines first: an operator reading a release failure must see
    # WHICH checks passed before the one that stopped it, in order.
    sys.stdout.flush()
    print("FAIL: %s" % msg, file=sys.stderr)
    sys.stderr.flush()
    return code


def _git(repo: str, *args: str) -> Tuple[int, str, str]:
    proc = subprocess.run(
        ["git"] + list(args),
        cwd=repo,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


# ---------------------------------------------------------------------------
# (a) ancestry
# ---------------------------------------------------------------------------
def ancestry(repo: str, remote: str, branch: str, offline_ack: bool) -> int:
    ref = "%s/%s" % (remote, branch)
    if offline_ack:
        print(
            "  --   ancestry: --offline-ack given, NOT fetching; the "
            "merge-base below is judged against a possibly STALE %s" % ref
        )
    else:
        rc, _out, err = _git(repo, "fetch", "--quiet", remote, branch)
        # NEVER `;` between the fetch and the merge-base: a failed fetch plus a
        # stale ref reads as approval.
        if rc != 0:
            return _fail(
                E_FETCH,
                "could not talk to origin: `git fetch %s %s` exited %d.\n"
                "      This is NOT a verdict on the commit — the check did not "
                "run.\n"
                "      Fix the network/remote and re-run, or, if you are "
                "deliberately\n"
                "      offline and accept judging against the last-known ref, "
                "re-run\n"
                "      with --offline-ack (it is recorded in the output).\n"
                "      git said: %s" % (remote, branch, rc, err.strip()),
            )
        print("  ok   fetched %s" % ref)

    rc, out, err = _git(repo, "rev-parse", "--verify", "--quiet", ref)
    if rc != 0 or not out.strip():
        return _fail(
            E_REMOTE_REF,
            "no usable ref %s in this repo — cannot judge ancestry "
            "(git said: %s)" % (ref, err.strip()),
        )
    remote_sha = out.strip()

    rc, _out, err = _git(repo, "merge-base", "--is-ancestor", "HEAD", ref)
    if rc == 0:
        print("  ok   HEAD is an ancestor of %s (%s)" % (ref, remote_sha[:12]))
        return 0
    if rc == 1:
        return _fail(
            E_NOT_ANCESTOR,
            "HEAD is not an ancestor of %s — push main and re-run the "
            "preflight.\n"
            "      A tag on an unpushed commit points at a tree CI never "
            "saw; the\n"
            "      preflight's green verdict was about a different SHA."
            % ref,
        )
    return _fail(
        E_REMOTE_REF,
        "`git merge-base --is-ancestor HEAD %s` exited %d (neither yes nor "
        "no) — refusing to guess (git said: %s)" % (ref, rc, err.strip()),
    )


# ---------------------------------------------------------------------------
# (b) restricted delta
# ---------------------------------------------------------------------------
def _parse_verdict(text: str) -> Dict[str, object]:
    """Minimal, stdlib-only reader for the verdict's fenced YAML block.

    Deliberately NOT a YAML parser: it accepts `key: value` and a single level
    of `  - item` list entries, and ignores everything else. Anything it cannot
    read is absent, and every consumer below treats absent as fail-closed.

    Parity with the step-15 reader (`.github/scripts/
    validate-pair-rail-verdict.py`, parse_verdict_file), stated at its REAL
    scope: block selection (the regex below is the validator's own — the
    first ```yaml fence, not the first fence of any language) and inline
    comment stripping MATCH; list parsing (`- item`) exists ONLY here —
    parse_verdict_file reads key:value and sub-dicts and would drop
    `delta_allowlist` silently. The W1 server-side port must therefore extend
    ONE shared reader (this file is the declared reference), never grow a
    third parser of the same signed file.
    """
    fields: Dict[str, object] = {}
    block = re.search(r"```yaml\s*\n(.*?)```", text, re.DOTALL)
    if block is None:
        # No yaml block -> no fields -> every consumer below fails closed.
        return fields
    cur_list: Optional[str] = None
    for raw in block.group(1).splitlines():
        line = raw.split("#", 1)[0].rstrip() if "#" in raw else raw.rstrip()
        if not line.strip():
            continue
        if line.startswith(("  - ", "- ")) and cur_list:
            item = line.split("-", 1)[1].strip()
            if item:
                fields[cur_list].append(item)  # type: ignore[union-attr]
            continue
        m = re.match(r"\A([A-Za-z0-9_]+):\s*(.*)\Z", line)
        if not m:
            continue
        key, val = m.group(1), m.group(2).strip()
        if val == "":
            fields[key] = []
            cur_list = key
        else:
            fields[key] = val
            cur_list = None
    return fields


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _read_manifest(path: str) -> List[Tuple[str, str]]:
    """`shasum -a 256` format: '<sha>  <name>' — returns [(sha, name)]."""
    entries: List[Tuple[str, str]] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.rstrip("\n")
            if not line.strip():
                continue
            m = re.match(r"\A([0-9a-f]{64}) [ *](.+)\Z", line)
            if not m:
                raise ValueError("unparsable manifest line: %r" % line)
            entries.append((m.group(1), m.group(2)))
    return entries


def _verify_manifest_content(manifest: str) -> Tuple[bool, str]:
    """Run `shasum -a 256 -c`; fall back to hashlib when shasum is absent."""
    directory = os.path.dirname(manifest) or "."
    name = os.path.basename(manifest)
    try:
        proc = subprocess.run(
            ["shasum", "-a", "256", "-c", name],
            cwd=directory,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
        )
        return proc.returncode == 0, proc.stdout.strip()
    except (OSError, FileNotFoundError):
        bad: List[str] = []
        for want, rel in _read_manifest(manifest):
            full = os.path.join(directory, rel)
            if not os.path.isfile(full) or _sha256(full) != want:
                bad.append(rel)
        if bad:
            return False, "hashlib fallback: mismatch/missing: %s" % ", ".join(bad)
        return True, "hashlib fallback: all entries match"


def delta(repo: str, tag: str, verdict_rel: Optional[str]) -> int:
    verdict_rel = verdict_rel or (VERDICT_PREFIX + tag + ".md")
    verdict_abs = os.path.join(repo, verdict_rel)
    if not os.path.isfile(verdict_abs):
        return _fail(
            E_VERDICT,
            "no signed verdict at %s — the re-pass verdict for THIS tag must "
            "be committed before the tag is cut (release.yml validates it per "
            "tag on the tagged tree)." % verdict_rel,
        )
    with open(verdict_abs, encoding="utf-8") as fh:
        fields = _parse_verdict(fh.read())

    release_tag = fields.get("release_tag")
    if release_tag != tag:
        return _fail(
            E_VERDICT,
            "verdict %s declares release_tag=%r, target tag is %r — refusing "
            "to judge this tag against another tag's verdict."
            % (verdict_rel, release_tag, tag),
        )
    parent = fields.get("parent_sha")
    if not isinstance(parent, str) or not HEX40.match(parent):
        return _fail(
            E_VERDICT,
            "verdict %s has no usable 40-hex `parent_sha:` — that field IS "
            "the review anchor." % verdict_rel,
        )
    rc, _out, _err = _git(repo, "cat-file", "-e", parent + "^{commit}")
    if rc != 0:
        return _fail(
            E_VERDICT,
            "parent_sha %s from %s is not a commit in this repo."
            % (parent, verdict_rel),
        )
    # Existence is not lineage. A fabricated anchor (`git commit-tree` over
    # HEAD's own tree, parented anywhere, on no branch) passes `cat-file -e`
    # and makes diff(parent..HEAD) contain ONLY the verdict + evidence while
    # unreviewed work sits on main — every check below then passes and the
    # guard prints approval over a tree the re-pass never saw. The anchor has
    # to be a commit HEAD actually descends from. (The staged W1 server-side
    # port asserts the same against origin/main — keep the two in sync.)
    rc, _out, err = _git(repo, "merge-base", "--is-ancestor", parent, "HEAD")
    if rc == 1:
        return _fail(
            E_PARENT_NOT_ANCESTOR,
            "parent_sha %s from %s is not an ancestor of HEAD — the review "
            "anchor is not in\n"
            "      the history this tag would sign. `cat-file -e` proves the "
            "object exists, not\n"
            "      that main descends from it; a fabricated commit carrying "
            "HEAD's own tree\n"
            "      makes the delta below trivially clean while unreviewed "
            "work rides the tag."
            % (parent[:12], verdict_rel),
        )
    if rc != 0:
        return _fail(
            E_PARENT_NOT_ANCESTOR,
            "`git merge-base --is-ancestor %s HEAD` exited %d (neither yes "
            "nor no) — refusing to guess (git said: %s)"
            % (parent[:12], rc, err.strip()),
        )
    print("  ok   parent_sha %s is an ancestor of HEAD" % parent[:12])

    allow = fields.get("delta_allowlist")
    if not isinstance(allow, list) or not allow:
        return _fail(
            E_VERDICT,
            "verdict %s carries no `delta_allowlist:` entries — the closed "
            "set is what makes the delta assert meaningful." % verdict_rel,
        )
    for entry in allow:
        if any(ch in entry for ch in GLOB_CHARS):
            return _fail(
                E_VERDICT,
                "delta_allowlist entry %r contains a glob metacharacter. The "
                "set is CLOSED and literal: a pattern like "
                "`pair-rail-verdict-*.md` would let a historical verdict or "
                "the template be edited and still pass." % entry,
            )
        if entry.startswith("/") or ".." in entry.split("/"):
            return _fail(
                E_VERDICT,
                "delta_allowlist entry %r must be a repo-relative path with "
                "no `..` segment." % entry,

--- rest ---
                "no `..` segment." % entry,
            )
        if entry.startswith(VERDICT_PREFIX) and entry != verdict_rel:
            return _fail(
                E_VERDICT,
                "delta_allowlist entry %r is another tag's verdict (or the "
                "template). Only %s may move for this tag."
                % (entry, verdict_rel),
            )
        if entry != verdict_rel and not entry.startswith(EVIDENCE_PREFIX):
            return _fail(
                E_VERDICT,
                "delta_allowlist entry %r is neither this tag's verdict nor "
                "plan-side evidence under %s\n"
                "      The allowlist is EXHAUSTIVE: the verdict, its "
                "verdict-fields, and the\n"
                "      re-pass artifacts — nothing else. Allowlisting a "
                "version site, a\n"
                "      workflow or any code path turns this assert into "
                "permission to land\n"
                "      unreviewed work on the tag, which is the hole it "
                "exists to close."
                % (entry, EVIDENCE_PREFIX),
            )
    allow_set: Set[str] = set(allow)
    if verdict_rel not in allow_set:
        return _fail(
            E_VERDICT,
            "the verdict itself (%s) is not in its own delta_allowlist — it "
            "has to be committed, so it has to be allowed." % verdict_rel,
        )

    manifest_rel = fields.get("delta_manifest")
    manifest_sha = fields.get("delta_manifest_sha256")
    if not isinstance(manifest_rel, str) or not manifest_rel:
        return _fail(
            E_VERDICT,
            "verdict %s carries no `delta_manifest:` — without it the "
            "re-pass artifacts close by NAME only, and any file dropped into "
            "the directory after the review would pass." % verdict_rel,
        )
    if not isinstance(manifest_sha, str) or not HEX64.match(manifest_sha):
        return _fail(
            E_VERDICT,
            "verdict %s has no usable 64-hex `delta_manifest_sha256:`."
            % verdict_rel,
        )
    if manifest_rel not in allow_set:
        return _fail(
            E_VERDICT,
            "delta_manifest %s is not in delta_allowlist." % manifest_rel,
        )

    # --- content pin: the manifest itself, then everything it lists ---
    manifest_abs = os.path.join(repo, manifest_rel)
    if not os.path.isfile(manifest_abs):
        return _fail(E_MANIFEST_PIN, "delta_manifest %s missing" % manifest_rel)
    actual = _sha256(manifest_abs)
    if actual != manifest_sha:
        return _fail(
            E_MANIFEST_PIN,
            "delta_manifest sha256 mismatch for %s\n"
            "      verdict pins %s\n"
            "      on disk      %s" % (manifest_rel, manifest_sha, actual),
        )
    print("  ok   %s matches the sha256 pinned in the verdict" % manifest_rel)

    try:
        entries = _read_manifest(manifest_abs)
    except (OSError, ValueError) as exc:
        return _fail(E_MANIFEST_CONTENT, "cannot read %s: %s" % (manifest_rel, exc))
    good, detail = _verify_manifest_content(manifest_abs)
    if not good:
        return _fail(
            E_MANIFEST_CONTENT,
            "re-pass artifacts do not match %s (shasum -c failed):\n      %s"
            % (manifest_rel, detail),
        )
    print("  ok   shasum -a 256 -c %s (%d entries)" % (manifest_rel, len(entries)))

    # --- plan-side entries OUTSIDE the manifest directory ---
    # Everything inside the manifest directory is content-pinned (sha256 of
    # the manifest in the signed verdict + shasum -c + name equality below).
    # An EVIDENCE_PREFIX entry outside it closes by NAME ONLY — the plan file
    # itself, immutable repass history, or ANOTHER tag's verdict-fields could
    # be allowlisted and a post-review edit would ride the tag. The one such
    # file the plan promises is the verdict-fields for THIS tag, at its ONE
    # canonical path: directly inside the plan directory that CONTAINS the
    # manifest dir. A basename-only rule would admit any number of
    # look-alikes anywhere under EVIDENCE_PREFIX (plans/archive/, a sibling
    # repass dir, ...), each an unpinned name-only pass-through. Mirror this
    # rule in the W1 server-side port.
    man_dir = os.path.dirname(manifest_rel)
    plan_dir = os.path.dirname(man_dir)
    vf_name = "verdict-fields-%s.md" % tag
    vf_expected = "%s/%s" % (plan_dir, vf_name) if plan_dir else vf_name
    for entry in sorted(allow_set):
        if entry == verdict_rel or entry == manifest_rel:
            continue
        if entry.startswith(man_dir + "/"):
            continue
        if entry != vf_expected:
            return _fail(
                E_VERDICT,
                "delta_allowlist entry %r is outside the manifest directory "
                "(%s/) and is not this\n"
                "      tag's verdict-fields at its canonical path (%s).\n"
                "      Outside the manifest nothing pins content — a "
                "post-review edit there\n"
                "      would ride the tag by NAME alone, and a basename "
                "match in any other\n"
                "      directory is a look-alike, not the plan's file. Move "
                "the file into the\n"
                "      re-pass manifest, or it must be exactly %s."
                % (entry, man_dir, vf_expected, vf_expected),
            )

    # --- set equality by NAME, both directions, inside the manifest dir ---
    listed = set(
        os.path.normpath(os.path.join(man_dir, name)).replace(os.sep, "/")
        for _sha, name in entries
    )
    listed.add(manifest_rel)
    allowed_in_dir = set(
        e for e in allow_set if man_dir and (e == manifest_rel or e.startswith(man_dir + "/"))
    )
    if allowed_in_dir != listed:
        extra = sorted(allowed_in_dir - listed)
        missing = sorted(listed - allowed_in_dir)
        return _fail(
            E_MANIFEST_SET,
            "re-pass artifact set is not closed under %s\n"
            "      allowlisted but not in the manifest: %s\n"
            "      in the manifest but not allowlisted: %s"
            % (manifest_rel, extra or "-", missing or "-"),
        )
    print("  ok   re-pass artifact set closes (name equality with the manifest)")

    # --- the delta itself ---
    # --no-renames on purpose: with rename detection a file moved OUT of the
    # allowlisted evidence directory is reported only under its destination
    # name, and the disappearance of the reviewed original goes unmentioned.
    # Literal paths on both sides or the set comparison is not a set comparison.
    rc, out, err = _git(repo, "diff", "--no-renames", "%s..HEAD" % parent, "--name-only")
    if rc != 0:
        return _fail(
            E_DELTA,
            "`git diff --no-renames %s..HEAD --name-only` failed: %s"
            % (parent, err.strip()),
        )
    changed = [line for line in out.splitlines() if line.strip()]
    outside = sorted(p for p in changed if p not in allow_set)
    if outside:
        return _fail(
            E_DELTA,
            "files changed after the reviewed parent %s that the verdict does "
            "NOT allow:\n%s\n"
            "      The invariant is: NOTHING landed after what the re-pass "
            "reviewed,\n"
            "      other than the verdict and its pinned evidence. Either "
            "re-run the\n"
            "      re-pass against this tree, or drop these commits."
            % (parent[:12], "\n".join("        - %s" % p for p in outside)),
        )

    # VACUITY. Everything above is satisfied trivially by an anchor that sits
    # AT (or after) the verdict: the delta is then empty or verdict-free and
    # "all files are inside the allowlist" proves nothing at all. The verdict
    # has to have LANDED after the tree it certifies.
    if verdict_rel not in changed:
        return _fail(
            E_VACUOUS,
            "the verdict %s is not part of the delta %s..HEAD — this assert "
            "would pass\n"
            "      VACUOUSLY. parent_sha has to be the commit the re-pass "
            "reviewed, with\n"
            "      the verdict landing after it; parent_sha == HEAD (or any "
            "anchor whose\n"
            "      tree already carried the verdict) is the v1.16.0 "
            "self-reference bug that\n"
            "      the parent_sha field was introduced to kill."
            % (verdict_rel, parent[:12]),
        )

    # State the inputs, not just the verdict: an operator reading a release log
    # has to be able to tell what this assert actually examined.
    print(
        "  ok   delta %s..HEAD is %d file(s), all inside the verdict's closed "
        "allowlist of %d (verdict present in the delta)"
        % (parent[:12], len(changed), len(allow_set))
    )
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(prog="_release_tag_guard.py")
    sub = parser.add_subparsers(dest="cmd")

    p_anc = sub.add_parser("ancestry", help="HEAD must be on origin/<branch>")
    p_anc.add_argument("--repo", default=".")
    p_anc.add_argument("--remote", default="origin")
    p_anc.add_argument("--branch", default="main")
    p_anc.add_argument(
        "--offline-ack",
        action="store_true",
        help="named escape hatch: skip the fetch and judge against the "
        "last-known remote ref (loudly announced)",
    )

    p_delta = sub.add_parser("delta", help="restricted delta vs the verdict")
    p_delta.add_argument("--repo", default=".")
    p_delta.add_argument("--tag", required=True)
    p_delta.add_argument("--verdict", default=None)

    args = parser.parse_args(argv)
    if args.cmd == "ancestry":
        return ancestry(args.repo, args.remote, args.branch, args.offline_ack)
    if args.cmd == "delta":
        return delta(args.repo, args.tag, args.verdict)
    parser.print_usage(sys.stderr)
    return E_USAGE


if __name__ == "__main__":
    sys.exit(main())

exec
/bin/zsh -lc "sed -n '1,360p' .claude/scripts/await_release_gate.py && printf '\\n--- existing tests ---\\n' && sed -n '1,420p' .claude/scripts/tests/test_await_release_gate.py" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
#!/usr/bin/env python3
"""await_release_gate.py — PLAN-166 W0 item 6 (F1): decision function that
tells ``npm-publish.yml`` whether the ``release.yml`` **release-gate** job
actually passed for *this* tag, at *this* commit, in *this* push.

## The bug this closes (F1, P0)

``npm-publish.yml`` and ``release.yml`` both fire on ``push: tags: v*``.
They are INDEPENDENT runs — nothing made the publish observe the gate. The
only barrier was the ``production-npm`` environment approval, i.e. a human
clicking "approve" with no machine evidence that the governance gate was
even green. That is a live path to publishing an unreviewed tree.

## Contract

Pure, offline, stdlib-only. Input is the JSON the caller already fetched
(``gh api .../actions/runs?head_sha=...`` merged with each run's
``.../jobs``); output is exactly one of three decisions **per evaluation
point** (the caller polls; each poll is one independent decision):

* ``GRANT`` — only when ONE run satisfies EVERY condition simultaneously:
  workflow file ``release.yml``, ``event == "push"``,
  ``head_branch == <tag>``, ``head_sha == <GITHUB_SHA>``, it is FRESH
  (see below), and its **job** ``release-gate`` has
  ``conclusion == "success"``. Never the RUN conclusion: ``release.yml``
  carries ``if: vars.CEO_SOTA_DISABLE != '1'`` on ``release-gate``, so a
  disabled gate SKIPS the job while the run itself stays green. Reading the
  run conclusion would grant on a gate that never executed.

* ``WAIT`` — evidence is legitimately not in yet and the deadline has not
  passed: (a) no candidate run yet — workflows from the same push start in
  ARBITRARY order, absence is neither failure nor permission; (b) the
  candidate run exists but the ``release-gate`` job has not materialised in
  the jobs endpoint yet (eventual consistency — without this state a
  "BLOCK on mismatch" rule produces an instant false block in the rc.2/GA
  race); (c) the job exists with ``conclusion: null`` (queued/running).

* ``BLOCK`` — fail-CLOSED: the candidate's gate job concluded anything
  other than ``success`` (``failure``, ``skipped``, ``cancelled``, …),
  malformed JSON, an API error payload, or **the deadline elapsed in ANY
  non-GRANT state**. Per ADR-186 this is INPUT verification, not
  infrastructure: content we cannot verify is blocked, not waved through.

## Candidate semantics (load-bearing — do not "optimise" this away)

The head-SHA run list contains UNRELATED runs, **including the npm-publish
run doing the asking**. Non-candidate runs are IGNORED — never BLOCK.
"Mismatch" is only ever evaluated against the exact candidate
(workflow + tag + SHA + event). If any near-miss run could BLOCK, every
release would lose the race against its own presence in the list.

## Freshness (delete + re-tag of the SAME sha)

Re-tagging the same commit leaves the OLD Release run in the list with the
same ``head_sha``/``head_branch``. Polling before the NEW Release run is
created would otherwise find the old ``success`` as "most recent" and grant
— even if the new run later fails. So a candidate must have been created no
earlier than the asking run's own creation, minus ``--freshness-skew-seconds``
(default 120s) to absorb same-push jitter: both workflows are created by one
push event, and their ``created_at`` ordering is arbitrary within seconds.
Runs older than that window are not candidates at all (→ WAIT, then BLOCK at
the deadline). KNOWN LIMIT, stated rather than hidden: a delete+re-tag
completed FASTER than the skew window can still admit the previous run; the
skew is a jitter allowance, not a proof, and it is printed with every
decision so the value used is auditable.

``--self-created-at`` is REQUIRED. It is the input that switches this whole
leg on, so it gets no default: omitting it (or passing an empty/unparseable
value) is a usage error (exit 2), never a run that silently grants stale
successes. Same doctrine as ``_release_bump_sites.py --today``: a parameter
that changes the verdict has no default. The doctrine holds at BOTH layers:
``GateContext.self_created_at_epoch`` is likewise a required field with no
default (and an explicit ``None`` raises), so an in-process caller of
``decide()`` cannot construct a context with the freshness leg silently off.

## Required fields per run object

``path`` (or ``workflow_path``), ``event``, ``head_branch``, ``head_sha``,
``created_at``, optional ``run_attempt``/``id`` (tie-break), and ``jobs``
(a list, or the raw ``{"jobs": [...]}`` envelope). A run with no ``path``
cannot be attributed to a workflow and is therefore not a candidate.

## Usage

    python3 .claude/scripts/await_release_gate.py \
        --payload-file runs.json --tag v1.3.0 --head-sha "$GITHUB_SHA" \
        --self-created-at "$SELF_CREATED_AT" --deadline-epoch "$DEADLINE"

``--payload-file -`` reads stdin.

Exit codes:
    0 — GRANT   (publish may proceed)
    1 — BLOCK   (fail-closed; caller must fail the job)
    2 — usage error (bad arguments)
    3 — WAIT    (caller sleeps and polls again)
"""

from __future__ import annotations

import argparse
import calendar
import json
import re
import sys
import time
from typing import Any, Dict, List, NamedTuple, Optional, Sequence, Tuple

GRANT = "GRANT"
WAIT = "WAIT"
BLOCK = "BLOCK"

EXIT_GRANT = 0
EXIT_BLOCK = 1
EXIT_USAGE = 2
EXIT_WAIT = 3

_EXIT_BY_DECISION = {GRANT: EXIT_GRANT, BLOCK: EXIT_BLOCK, WAIT: EXIT_WAIT}

DEFAULT_WORKFLOW = "release.yml"
DEFAULT_GATE_JOB = "release-gate"
DEFAULT_EVENT = "push"
DEFAULT_FRESHNESS_SKEW_SECONDS = 120


class MalformedPayload(Exception):
    """Input we cannot parse — fail-CLOSED (BLOCK), never ignore."""


class GateContext(NamedTuple):
    """Every input the decision depends on. Printed with every decision."""

    tag: str
    head_sha: str
    now_epoch: int
    # REQUIRED — no default, one layer below the CLI for the same reason the
    # CLI has ``required=True``: this field arms the delete+re-tag freshness
    # leg, and a verdict-changing parameter with a default is a fail-open
    # waiting for the first in-process caller of ``decide()`` that forgets
    # it. Enforcing the doctrine only at argparse left exactly that hole.
    self_created_at_epoch: int
    workflow: str = DEFAULT_WORKFLOW
    gate_job: str = DEFAULT_GATE_JOB
    event: str = DEFAULT_EVENT
    deadline_epoch: Optional[int] = None
    freshness_skew_seconds: int = DEFAULT_FRESHNESS_SKEW_SECONDS

    @property
    def deadline_passed(self) -> bool:
        return self.deadline_epoch is not None and self.now_epoch > self.deadline_epoch

    @property
    def freshness_floor(self) -> int:
        if self.self_created_at_epoch is None:
            # A NamedTuple cannot stop an explicit None; refusing loudly here
            # keeps "freshness leg silently off" unrepresentable at every
            # layer instead of only at the CLI.
            raise ValueError(
                "freshness leg unarmed: self_created_at_epoch is None — the "
                "delete+re-tag freshness leg cannot be silently disabled"
            )
        return self.self_created_at_epoch - self.freshness_skew_seconds


class Decision(NamedTuple):
    decision: str
    reason: str
    facts: Dict[str, Any]

    @property
    def exit_code(self) -> int:
        return _EXIT_BY_DECISION[self.decision]


_TS_RE = re.compile(
    r"^(\d{4})-(\d{2})-(\d{2})[Tt ](\d{2}):(\d{2}):(\d{2})"
    r"(?:\.\d+)?(Z|z|[+-]\d{2}:?\d{2})?$"
)


def parse_timestamp(raw: Any) -> Optional[int]:
    """ISO-8601 (GitHub flavour) -> epoch seconds UTC. ``None`` if unparseable.

    ``datetime.fromisoformat`` cannot read a trailing ``Z`` on Python 3.9, so
    this parses explicitly instead of depending on interpreter version.
    """
    if not isinstance(raw, str):
        return None
    m = _TS_RE.match(raw.strip())
    if m is None:
        return None
    parts = [int(m.group(i)) for i in range(1, 7)]
    try:
        epoch = calendar.timegm(
            (parts[0], parts[1], parts[2], parts[3], parts[4], parts[5], 0, 1, -1)
        )
    except (ValueError, OverflowError):
        return None
    off = m.group(7)
    if off and off not in ("Z", "z"):
        sign = 1 if off[0] == "+" else -1
        digits = off[1:].replace(":", "")
        epoch -= sign * (int(digits[:2]) * 3600 + int(digits[2:4]) * 60)
    return epoch


def extract_runs(payload: Any) -> List[Dict[str, Any]]:
    """Pull the run list out of the payload, or raise MalformedPayload.

    Accepts the raw GitHub envelope (``workflow_runs``) or a plain ``runs``
    list. An API error body (``{"message": "Bad credentials", ...}``) has
    neither key and therefore raises — BLOCK, by design.
    """
    if not isinstance(payload, dict):
        raise MalformedPayload("payload is %s, expected a JSON object" % type(payload).__name__)
    for key in ("workflow_runs", "runs"):
        if key in payload:
            value = payload[key]
            if not isinstance(value, list):
                raise MalformedPayload("payload['%s'] is not a list" % key)
            for item in value:
                if not isinstance(item, dict):
                    raise MalformedPayload("payload['%s'] holds a non-object entry" % key)
            return value
    raise MalformedPayload("payload has no 'workflow_runs' (or 'runs') key")


def _workflow_file(run: Dict[str, Any]) -> Optional[str]:
    for key in ("path", "workflow_path"):
        value = run.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().rsplit("/", 1)[-1]
    return None


def _same_sha(left: Any, right: Any) -> bool:
    if not isinstance(left, str) or not isinstance(right, str):
        return False
    return left.strip().lower() == right.strip().lower()


def is_identity_match(run: Dict[str, Any], ctx: GateContext) -> bool:
    """workflow + event + tag + head_sha, all four, no partial credit."""
    return (
        _workflow_file(run) == ctx.workflow
        and run.get("event") == ctx.event
        and run.get("head_branch") == ctx.tag
        and _same_sha(run.get("head_sha"), ctx.head_sha)
    )


def _sort_key(run: Dict[str, Any], created_at: int) -> Tuple[int, int, int]:
    attempt = run.get("run_attempt")
    run_id = run.get("id")
    return (
        created_at,
        attempt if isinstance(attempt, int) else 0,
        run_id if isinstance(run_id, int) else 0,
    )


def select_candidate(
    runs: Sequence[Dict[str, Any]], ctx: GateContext
) -> Tuple[Optional[Dict[str, Any]], Dict[str, int]]:
    """Most recent FRESH identity-matching run, plus a census of what was seen.

    Raises MalformedPayload when an identity-matching run carries a
    ``created_at`` we cannot parse: a candidate we cannot date cannot be
    proven fresh, and unverifiable input is fail-CLOSED.
    """
    census = {"runs_total": len(runs), "identity_matches": 0, "stale_candidates": 0}
    best: Optional[Dict[str, Any]] = None
    best_key: Optional[Tuple[int, int, int]] = None
    floor = ctx.freshness_floor
    for run in runs:
        if not is_identity_match(run, ctx):
            continue
        census["identity_matches"] += 1
        created_at = parse_timestamp(run.get("created_at"))
        if created_at is None:
            raise MalformedPayload(
                "candidate run id=%r has an unparseable created_at=%r"
                % (run.get("id"), run.get("created_at"))
            )
        if created_at < floor:
            census["stale_candidates"] += 1
            continue
        key = _sort_key(run, created_at)
        if best_key is None or key > best_key:
            best, best_key = run, key
    census["fresh_candidates"] = census["identity_matches"] - census["stale_candidates"]
    return best, census


def find_gate_job(run: Dict[str, Any], gate_job: str) -> Optional[Dict[str, Any]]:
    """The ``release-gate`` job inside a run, or None if not materialised yet."""
    jobs = run.get("jobs")
    if isinstance(jobs, dict):
        jobs = jobs.get("jobs")
    if not isinstance(jobs, list):
        return None
    for job in jobs:
        if isinstance(job, dict) and job.get("name") == gate_job:
            return job
    return None


def _wait_or_block(reason: str, ctx: GateContext, facts: Dict[str, Any]) -> Decision:
    """Every non-GRANT state collapses to BLOCK once the deadline elapses."""
    if ctx.deadline_passed:
        return Decision(BLOCK, "deadline-exceeded:" + reason, facts)
    return Decision(WAIT, reason, facts)


def _candidate_facts(run: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "candidate_run_id": run.get("id"),
        "candidate_run_attempt": run.get("run_attempt"),
        "candidate_created_at": run.get("created_at"),
        "candidate_run_status": run.get("status"),
        "candidate_run_conclusion": run.get("conclusion"),
    }


def decide(payload: Any, ctx: GateContext) -> Decision:
    """The whole decision. Pure: no network, no clock, no filesystem."""
    facts: Dict[str, Any] = {}
    try:
        runs = extract_runs(payload)
        candidate, census = select_candidate(runs, ctx)
    except MalformedPayload as exc:
        facts["error"] = str(exc)
        return Decision(BLOCK, "malformed-payload", facts)
    facts.update(census)
    if candidate is None:
        reason = "stale-candidates-only" if census["stale_candidates"] else "candidate-not-yet-created"
        return _wait_or_block(reason, ctx, facts)
    facts.update(_candidate_facts(candidate))
    job = find_gate_job(candidate, ctx.gate_job)
    if job is None:
        facts["gate_job_present"] = False
        return _wait_or_block("gate-job-not-materialised", ctx, facts)
    facts["gate_job_present"] = True
    facts["gate_job_status"] = job.get("status")
    conclusion = job.get("conclusion")
    facts["gate_job_conclusion"] = conclusion
    if conclusion is None:
        return _wait_or_block("gate-job-not-concluded", ctx, facts)
    if not isinstance(conclusion, str):
        facts["error"] = "gate job conclusion is %s, expected string or null" % type(conclusion).__name__
        return Decision(BLOCK, "malformed-payload", facts)
    if conclusion == "success":
        return Decision(GRANT, "gate-job-success", facts)
    return Decision(BLOCK, "gate-job-" + conclusion, facts)


def render(decision: Decision, ctx: GateContext) -> str:
    """Human-readable record. A decision that hides its inputs is unauditable."""
    remaining = "n/a"
    if ctx.deadline_epoch is not None:
        remaining = str(ctx.deadline_epoch - ctx.now_epoch)

--- existing tests ---
"""Behaviour battery for ``await_release_gate.decide`` (PLAN-166 W0 item 6, F1).

The AC-2 enumeration in PLAN-166 is the ONLY source for what is covered here.
No test count is asserted or written anywhere — a mirrored numeral has drifted
from reality four times in this plan; the enumeration below IS the census.

Case classes, in AC-2 order:

* GRANT — exact candidate (release.yml + push + tag + sha + fresh) whose
  ``release-gate`` job concluded ``success``. MANDATORY: without it an
  always-BLOCK implementation would pass the entire battery.
* NEVER-GRANT — payloads holding ONLY green NON-candidate runs (rc tag,
  other sha, wrong workflow, workflow_dispatch). Each proves twice over that
  a look-alike green run neither grants NOR falsely blocks the race.
* BLOCK — candidate gate ``skipped``; candidate gate ``failure``; no
  candidate with the deadline elapsed; malformed JSON.
* WAIT — empty run list in time; candidate present with the ``release-gate``
  job absent from the jobs payload in time (eventual consistency); candidate
  with ``conclusion: null`` in time (this one kills the naive
  ``!= "failure"`` implementation).
* FRESHNESS — a ``success`` candidate created BEFORE the asking run started
  (delete + re-tag of the same sha) does not count as GRANT.
* USAGE — the freshness input is load-bearing, so it has no default:
  omitting ``--self-created-at`` (or passing an empty value) is a usage
  error (exit 2), NEVER a run with the delete+re-tag leg silently off.
  Without this class the FRESHNESS tests above prove nothing about the W1
  wiring — the same stale payload they reject becomes a GRANT the moment
  the caller forgets one flag.
"""

from __future__ import annotations

import calendar
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# Env-hygiene gate (check-test-env-hygiene.py): test classes subclass
# TestEnvContext, not bare unittest.TestCase, so HOME / CLAUDE_PROJECT_DIR /
# os.environ / sys.path are snapshot-restored around every test.
_HOOKS_DIR = Path(__file__).resolve().parents[2] / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

from await_release_gate import (
    BLOCK,
    EXIT_BLOCK,
    EXIT_GRANT,
    EXIT_USAGE,
    EXIT_WAIT,
    GRANT,
    WAIT,
    GateContext,
    decide,
)

SCRIPT = Path(__file__).resolve().parent.parent / "await_release_gate.py"

TAG = "v1.3.0"
HEAD_SHA = "a" * 40
OTHER_SHA = "b" * 40

# Independent clock: built with calendar.timegm, NOT with the module's own
# parser, so the fixtures are not graded by the code under test.
SELF_CREATED_AT = "2026-08-05T12:00:00Z"
SELF_EPOCH = calendar.timegm((2026, 8, 5, 12, 0, 0, 0, 1, -1))
CANDIDATE_CREATED_AT = "2026-08-05T12:00:05Z"       # same push, +5s jitter
STALE_CREATED_AT = "2026-08-05T11:00:00Z"           # previous tag push, -1h
NOW = SELF_EPOCH + 60
DEADLINE_OPEN = SELF_EPOCH + 1800                   # 30 min of head-room
NOW_PAST_DEADLINE = DEADLINE_OPEN + 1


def ctx(now=NOW, deadline=DEADLINE_OPEN):
    """Context with EVERY input pinned explicitly (no ambient clock)."""
    return GateContext(
        tag=TAG,
        head_sha=HEAD_SHA,
        now_epoch=now,
        deadline_epoch=deadline,
        self_created_at_epoch=SELF_EPOCH,
        freshness_skew_seconds=120,
    )


def gate_job(conclusion="success", status="completed"):
    return {"name": "release-gate", "status": status, "conclusion": conclusion}


def release_run(**over):
    """A run that matches the candidate identity on every field by default."""
    run = {
        "id": 1001,
        "run_attempt": 1,
        "path": ".github/workflows/release.yml",
        "event": "push",
        "head_branch": TAG,
        "head_sha": HEAD_SHA,
        "created_at": CANDIDATE_CREATED_AT,
        "status": "completed",
        "conclusion": "success",
        "jobs": [gate_job()],
    }
    run.update(over)
    return run


def self_run():
    """The npm-publish run doing the asking — always in its own head_sha list."""
    return {
        "id": 1002,
        "run_attempt": 1,
        "path": ".github/workflows/npm-publish.yml",
        "event": "push",
        "head_branch": TAG,
        "head_sha": HEAD_SHA,
        "created_at": SELF_CREATED_AT,
        "status": "in_progress",
        "conclusion": None,
        "jobs": [{"name": "await-release-gate", "status": "in_progress", "conclusion": None}],
    }


def payload(*runs):
    return {"workflow_runs": list(runs)}


def run_cli(raw_body, extra=(), self_created_at=SELF_CREATED_AT):
    """CLI harness. ``self_created_at=None`` OMITS the flag entirely."""
    handle, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(handle, "w", encoding="utf-8") as fh:
        fh.write(raw_body)
    freshness = [] if self_created_at is None else ["--self-created-at", self_created_at]
    try:
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--payload-file", path,
                "--tag", TAG,
                "--head-sha", HEAD_SHA,
                "--deadline-epoch", str(DEADLINE_OPEN),
                "--now-epoch", str(NOW),
            ] + freshness + list(extra),
            capture_output=True,
            text=True,
        )
    finally:
        os.unlink(path)


class GrantTests(TestEnvContext):
    """The mandatory positive control."""

    def test_exact_candidate_with_successful_gate_job_grants(self):
        # The list deliberately also holds the asking npm-publish run: the
        # sibling must be ignored, not raced against.
        result = decide(payload(self_run(), release_run()), ctx())
        self.assertEqual(GRANT, result.decision)
        self.assertEqual("gate-job-success", result.reason)
        self.assertEqual(1, result.facts["fresh_candidates"])

    def test_grant_exits_zero_and_prints_its_inputs(self):
        proc = run_cli(json.dumps(payload(self_run(), release_run())))
        self.assertEqual(EXIT_GRANT, proc.returncode, proc.stderr)
        self.assertIn("decision=GRANT", proc.stdout)
        self.assertIn("freshness_skew_s=120", proc.stdout)
        self.assertIn("head_sha=" + HEAD_SHA, proc.stdout)


class NeverGrantTests(TestEnvContext):
    """Green look-alikes: never GRANT, and never a false BLOCK in time."""

    def _assert_never_grants(self, run):
        body = payload(self_run(), run)
        in_time = decide(body, ctx())
        self.assertEqual(WAIT, in_time.decision)
        self.assertEqual("candidate-not-yet-created", in_time.reason)
        self.assertEqual(0, in_time.facts["identity_matches"])
        expired = decide(body, ctx(now=NOW_PAST_DEADLINE))
        self.assertEqual(BLOCK, expired.decision)

    def test_release_gate_success_on_a_different_tag_does_not_grant(self):
        self._assert_never_grants(release_run(head_branch="v1.3.0-rc.2", id=2001))

    def test_release_gate_success_on_another_commit_does_not_grant(self):
        self._assert_never_grants(release_run(head_sha=OTHER_SHA, id=2002))

    def test_release_gate_success_from_the_wrong_workflow_does_not_grant(self):
        self._assert_never_grants(
            release_run(path=".github/workflows/validate.yml", id=2003)
        )

    def test_release_gate_success_from_workflow_dispatch_does_not_grant(self):
        self._assert_never_grants(release_run(event="workflow_dispatch", id=2004))


class BlockTests(TestEnvContext):
    def test_candidate_with_skipped_gate_job_blocks(self):
        # CEO_SOTA_DISABLE=1 skips the job while the RUN stays green.
        run = release_run(jobs=[gate_job(conclusion="skipped")])
        result = decide(payload(self_run(), run), ctx())
        self.assertEqual(BLOCK, result.decision)
        self.assertEqual("gate-job-skipped", result.reason)

    def test_candidate_with_failed_gate_job_blocks(self):
        run = release_run(conclusion="failure", jobs=[gate_job(conclusion="failure")])
        result = decide(payload(self_run(), run), ctx())
        self.assertEqual(BLOCK, result.decision)
        self.assertEqual("gate-job-failure", result.reason)
        proc = run_cli(json.dumps(payload(self_run(), run)))
        self.assertEqual(EXIT_BLOCK, proc.returncode)
        self.assertIn("decision=BLOCK", proc.stdout)

    def test_no_candidate_past_the_deadline_blocks(self):
        result = decide(payload(self_run()), ctx(now=NOW_PAST_DEADLINE))
        self.assertEqual(BLOCK, result.decision)
        self.assertEqual("deadline-exceeded:candidate-not-yet-created", result.reason)

    def test_malformed_payloads_block(self):
        for body in ([], "workflow_runs", {"message": "Bad credentials"},
                     {"workflow_runs": {"nope": 1}}, {"workflow_runs": ["not-an-object"]}):
            result = decide(body, ctx())
            self.assertEqual(BLOCK, result.decision, body)
            self.assertEqual("malformed-payload", result.reason, body)
        proc = run_cli("{not json at all")
        self.assertEqual(EXIT_BLOCK, proc.returncode)
        self.assertIn("reason=malformed-payload", proc.stdout)


class WaitTests(TestEnvContext):
    def test_empty_run_list_in_time_waits(self):
        result = decide(payload(), ctx())
        self.assertEqual(WAIT, result.decision)
        self.assertEqual("candidate-not-yet-created", result.reason)
        proc = run_cli(json.dumps(payload()))
        self.assertEqual(EXIT_WAIT, proc.returncode)

    def test_candidate_without_the_gate_job_yet_waits(self):
        # Eventual consistency of the jobs endpoint: absent list AND empty list.
        other_job = {"name": "publish-release", "status": "queued", "conclusion": None}
        for run in (release_run(jobs=[]), release_run(jobs=[other_job])):
            body = payload(self_run(), run)
            result = decide(body, ctx())
            self.assertEqual(WAIT, result.decision)
            self.assertEqual("gate-job-not-materialised", result.reason)
        no_jobs_key = release_run()
        del no_jobs_key["jobs"]
        result = decide(payload(self_run(), no_jobs_key), ctx())
        self.assertEqual(WAIT, result.decision)
        self.assertEqual("gate-job-not-materialised", result.reason)

    def test_running_gate_job_waits(self):
        # Kills `conclusion != "failure"` implementations.
        run = release_run(
            status="in_progress",
            conclusion=None,
            jobs=[gate_job(conclusion=None, status="in_progress")],
        )
        result = decide(payload(self_run(), run), ctx())
        self.assertEqual(WAIT, result.decision)
        self.assertEqual("gate-job-not-concluded", result.reason)
        expired = decide(payload(self_run(), run), ctx(now=NOW_PAST_DEADLINE))
        self.assertEqual(BLOCK, expired.decision)


class FreshnessTests(TestEnvContext):
    def test_success_predating_the_asking_run_does_not_grant(self):
        # delete + re-tag of the SAME sha: the OLD green run is still listed.
        stale = release_run(id=900, created_at=STALE_CREATED_AT)
        body = payload(self_run(), stale)
        result = decide(body, ctx())
        self.assertNotEqual(GRANT, result.decision)
        self.assertEqual(WAIT, result.decision)
        self.assertEqual("stale-candidates-only", result.reason)
        self.assertEqual(1, result.facts["stale_candidates"])
        self.assertEqual(BLOCK, decide(body, ctx(now=NOW_PAST_DEADLINE)).decision)

    def test_fresh_rerun_wins_over_the_stale_success(self):
        stale = release_run(id=900, created_at=STALE_CREATED_AT)
        fresh_failure = release_run(
            id=901, created_at=CANDIDATE_CREATED_AT,
            conclusion="failure", jobs=[gate_job(conclusion="failure")],
        )
        result = decide(payload(self_run(), stale, fresh_failure), ctx())
        self.assertEqual(BLOCK, result.decision)
        self.assertEqual("gate-job-failure", result.reason)


class UsageTests(TestEnvContext):
    """A parameter that changes the verdict has no default (FIXER pass, W0).

    ``--self-created-at`` used to be optional with ``default=None`` — and
    ``None`` DISABLES the freshness floor, so omitting one flag turned the
    exact stale-success payload FreshnessTests rejects into a GRANT. Same
    class as F2's ``--today`` in ``_release_bump_sites.py``: the input that
    flips the verdict must be explicit or the run must refuse.
    """

    def _stale_only_body(self):
        # The delete+re-tag payload: ONLY a success predating the asking run.
        return json.dumps(payload(self_run(), release_run(id=900, created_at=STALE_CREATED_AT)))

    def test_omitting_self_created_at_refuses_instead_of_granting(self):
        proc = run_cli(self._stale_only_body(), self_created_at=None)
        self.assertNotEqual(
            EXIT_GRANT, proc.returncode,
            "omitting --self-created-at must never GRANT a stale success:\n" + proc.stdout,
        )
        self.assertEqual(EXIT_USAGE, proc.returncode, proc.stdout + proc.stderr)
        self.assertIn("--self-created-at", proc.stderr)

    def test_empty_self_created_at_is_a_usage_error_not_a_disabled_leg(self):
        # required=True alone would still let `--self-created-at ""` slip
        # through the old `if args.self_created_at:` truthiness parse-skip.
        proc = run_cli(self._stale_only_body(), self_created_at="")
        self.assertNotEqual(EXIT_GRANT, proc.returncode, proc.stdout)
        self.assertEqual(EXIT_USAGE, proc.returncode, proc.stdout + proc.stderr)


class ContextLayerTests(TestEnvContext):
    """W0 re-pass r2 P2: the CLI closed the fail-open default, but
    ``GateContext.self_created_at_epoch`` kept ``= None`` one layer down, and
    ``freshness_floor`` mapped None to "leg silently off" — any in-process
    caller of ``decide()`` reproduced the exact GRANT-on-stale-success the
    UsageTests prove the CLI refuses. The doctrine has to hold at EVERY
    construction surface, not just argparse."""

    def _stale_only_payload(self):
        return payload(self_run(), release_run(id=900, created_at=STALE_CREATED_AT))

    def test_gate_context_requires_self_created_at_epoch(self):
        # No default: an in-process caller that forgets the field cannot
        # construct a context at all — same failure mode as omitting the flag.
        with self.assertRaises(TypeError):
            GateContext(
                tag=TAG,
                head_sha=HEAD_SHA,
                now_epoch=NOW,
                deadline_epoch=DEADLINE_OPEN,
            )

    def test_explicit_none_fails_loud_instead_of_disarming_the_leg(self):
        # NamedTuple cannot stop an explicit None; it must refuse loudly,
        # never decide with the delete+re-tag freshness leg silently off.
        disarmed = GateContext(
            tag=TAG,
            head_sha=HEAD_SHA,
            now_epoch=NOW,
            self_created_at_epoch=None,
            deadline_epoch=DEADLINE_OPEN,
        )
        with self.assertRaises(ValueError):
            decide(self._stale_only_payload(), disarmed)


if __name__ == "__main__":
    unittest.main()

exec
/bin/zsh -lc "sed -n '360,620p' .claude/scripts/await_release_gate.py" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
        remaining = str(ctx.deadline_epoch - ctx.now_epoch)
    lines = [
        "decision=%s reason=%s" % (decision.decision, decision.reason),
        "inputs: workflow=%s gate_job=%s event=%s tag=%s head_sha=%s"
        % (ctx.workflow, ctx.gate_job, ctx.event, ctx.tag, ctx.head_sha),
        "inputs: now_epoch=%s deadline_epoch=%s deadline_remaining_s=%s"
        % (ctx.now_epoch, ctx.deadline_epoch, remaining),
        "inputs: self_created_at_epoch=%s freshness_skew_s=%s freshness_floor_epoch=%s"
        % (ctx.self_created_at_epoch, ctx.freshness_skew_seconds, ctx.freshness_floor),
    ]
    for key in sorted(decision.facts):
        lines.append("fact: %s=%r" % (key, decision.facts[key]))
    return "\n".join(lines)


def _load_payload(path: str) -> Any:
    raw = sys.stdin.read() if path == "-" else open(path, "r", encoding="utf-8").read()
    return json.loads(raw)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Decide whether release-gate authorises an npm publish.")
    parser.add_argument("--payload-file", default="-", help="JSON of runs+jobs ('-' = stdin)")
    parser.add_argument("--tag", required=True, help="tag name, i.e. head_branch of the release run")
    parser.add_argument("--head-sha", required=True, help="GITHUB_SHA the publish is running against")
    parser.add_argument("--workflow", default=DEFAULT_WORKFLOW)
    parser.add_argument("--gate-job", default=DEFAULT_GATE_JOB)
    parser.add_argument("--event", default=DEFAULT_EVENT)
    parser.add_argument(
        "--deadline-epoch",
        type=int,
        required=True,
        help="epoch seconds after which any non-GRANT state becomes BLOCK (fail-closed)",
    )
    parser.add_argument("--now-epoch", type=int, default=None, help="override the clock (tests)")
    parser.add_argument(
        "--self-created-at",
        required=True,
        help=(
            "created_at of the ASKING run; candidates older than this minus "
            "the skew are stale. Required: this input arms the delete+re-tag "
            "freshness leg, and a verdict-changing parameter has no default"
        ),
    )
    parser.add_argument(
        "--freshness-skew-seconds", type=int, default=DEFAULT_FRESHNESS_SKEW_SECONDS
    )
    parser.add_argument("--json", action="store_true", help="emit the decision record as JSON")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    # Unconditional parse: `required=True` rejects the OMITTED flag, and this
    # rejects the empty/garbage value that a truthiness guard would have
    # silently mapped to "freshness leg off".
    self_created_at_epoch = parse_timestamp(args.self_created_at)
    if self_created_at_epoch is None:
        sys.stderr.write(
            "error: --self-created-at %r is not an ISO-8601 timestamp "
            "(the freshness leg cannot run without it)\n" % args.self_created_at
        )
        return EXIT_USAGE
    ctx = GateContext(
        tag=args.tag,
        head_sha=args.head_sha,
        now_epoch=args.now_epoch if args.now_epoch is not None else int(time.time()),
        workflow=args.workflow,
        gate_job=args.gate_job,
        event=args.event,
        deadline_epoch=args.deadline_epoch,
        self_created_at_epoch=self_created_at_epoch,
        freshness_skew_seconds=args.freshness_skew_seconds,
    )
    try:
        payload = _load_payload(args.payload_file)
    except (OSError, ValueError) as exc:
        decision = Decision(BLOCK, "malformed-payload", {"error": str(exc)})
    else:
        decision = decide(payload, ctx)
    if args.json:
        print(json.dumps({
            "decision": decision.decision,
            "reason": decision.reason,
            "facts": decision.facts,
            "inputs": ctx._asdict(),
        }, sort_keys=True, default=str))
    else:
        print(render(decision, ctx))
    return decision.exit_code


if __name__ == "__main__":
    sys.exit(main())

exec
/bin/zsh -lc "git diff --no-ext-diff --unified=100 -- scripts/tests/_parity_classify.py && printf '\\n--- full file ---\\n' && nl -ba scripts/tests/_parity_classify.py | sed -n '1,320p'" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
diff --git a/scripts/tests/_parity_classify.py b/scripts/tests/_parity_classify.py
index d8809bd..b1f86bd 100644
--- a/scripts/tests/_parity_classify.py
+++ b/scripts/tests/_parity_classify.py
@@ -60,242 +60,207 @@ Declarations decay, so both directions are checked:
     harmless).
   * Any divergence matching no declaration at all is FATAL. That is the live
     gate; the driver's --positive-control trips exactly there.
 
 Exit: 0 parity | 1 fatal | 2 only KNOWN_OPEN outstanding.
 Python >= 3.9, stdlib only.
 """
 
 from __future__ import annotations
 
 import argparse
 import hashlib
 import os
 import re
 import sys
 from typing import Dict, List, Optional, Tuple
 
 # ---------------------------------------------------------------------------
 # Structural skips: never framework content, never comparable.
 # ---------------------------------------------------------------------------
 SKIP_DIRS = (".git", ".claude.bak", "__pycache__")
 SKIP_SUFFIX = (".pyc",)
 
 # ---------------------------------------------------------------------------
 # ACCEPTED divergence — generated per-install or adopter-owned by contract.
 # Every entry carries the AUTHORITY for the claim, not a shrug. These are
 # printed as their own census block on every run so the list cannot grow
 # quietly.
 #   (regex, applies-to-modes or None for all, reason)
 # ---------------------------------------------------------------------------
 ACCEPTED: List[Tuple[str, Optional[str], str]] = [
     (
         r"^\.claude/\.install-manifest\.sha256$",
         None,
         "derived baseline manifest — regenerated by BOTH routes "
         "(_write_baseline_manifest); it is a hash OF the set under comparison, "
         "so comparing it would be circular",
     ),
     (
         r"^\.claude/\.install-state\.json$",
         None,
         "records the invocation itself (argv, timestamps, source sha, upgrade "
         "ops) — differs by construction between a fresh install and an "
         "install+upgrade; the `ceremony` field is asserted separately below",
     ),
     (
         r"^\.claude/settings\.json$",
         None,
         "install seeds it; upgrade does an ADDITIVE hook merge (PLAN-135 W2 H8) "
         "plus the 3-state baseline migration (PLAN-163 T5.4) and never "
         "clobbers — the two routes converge on keys, not on bytes",
     ),
     (
         r"^\.claude/agent-metrics\.md$",
         None,
         "adopter data — upgrade.sh header: 'Leaves CLAUDE.md, MEMORY.md, "
         ".claude/agent-metrics.md untouched'",
     ),
     (
         r"^(CLAUDE|MEMORY)\.md$",
         None,
         "seed-once adopter doc — same upgrade.sh preserve contract",
     ),
     (
         r"^\.gitignore$",
         None,
         "adopter-owned append-only surface. install.sh APPENDS marker-guarded "
         "blocks (install_posture_state_ignores, PLAN-165 CX-3); upgrade.sh has "
         "no append step, so an upgraded adopter never gets them. A REAL "
         "install-only delivery gap — accepted here (never fatal) only because "
         "the file is adopter-owned and must not be clobbered; reported every "
         "run so it stays visible",
     ),
     (
         r"^PROTOCOL\.md$",
         "maintainer",
         "generated pointer. install.sh substitutes the resolved SOURCE_DIR; "
         "upgrade.sh's _refresh_protocol_pointer emits the literal "
         "{{PROTOCOL_SOURCE}} placeholder. Body-only divergence, pre-existing "
         "asymmetry of the same pointer file",
     ),
     (
         r"^VERSION$",
         "maintainer",
         "BY DESIGN (PLAN-166 OQ-3 / ADR-155-AMEND-1): the upgrade must NOT "
         "touch the adopter's root VERSION — install_one is skip-if-exists, so "
         "in an adopter that owns a VERSION the framework never wrote there and "
         "backup_and_replace would TAKE the file (the verified S238 worst "
         "case). The framework's own version marker moves to "
         ".claude/.framework-version. Asserted positively below: B/VERSION must "
         "be byte-identical to the pinned source's VERSION (untouched), not "
         "merely different",
     ),
 ]
 
 # ---------------------------------------------------------------------------
 # KNOWN_OPEN — PLAN-166 W1 prerequisites. MANDATORY-FIRE (see module docstring).
 #   id, modes (None = all), class, regex, reason, unblocked_by
 # ---------------------------------------------------------------------------
 KNOWN_OPEN: List[Dict[str, Optional[str]]] = [
-    {
-        "id": "F3-spec-stale",
-        "modes": "maintainer",
-        "cls": "STALE",
-        "re": r"^SPEC/v1/",
-        "reason": (
-            "upgrade.sh delivers SPEC/v1 through NO surface: it is absent from "
-            "the backup_and_replace sequence AND from "
-            "_framework_target_entries(). An adopter upgrading v1.2 -> v1.3 "
-            "keeps the v1.2 contract — the trust boundary of the sentinel "
-            "unlock, +21 lines in this very release"
-        ),
-        "unblocked_by": (
-            "PLAN-166 W1 item 2 / OQ-3(a): forced-refresh route for SPEC/v1 in "
-            "upgrade.sh + delivery-record-gated entry in "
-            "_framework_target_entries() + INSTALL.md refresh list"
-        ),
-    },
-    {
-        "id": "F3-protocol-user-mode",
-        "modes": "user",
-        "cls": "ONLY_IN_B_OUTSIDE_CLAUDE",
-        "re": r"^PROTOCOL\.md$",
-        "reason": (
-            "upgrade.sh calls _refresh_protocol_pointer() UNCONDITIONALLY "
-            "(upgrade.sh:2441) and writes PROTOCOL.md at the repo ROOT. A "
-            "fresh `--ceremony user` install forbids exactly that "
-            "(install.sh:1876 gates install_protocol_pointer, and "
-            "smoke-install.yml's WS4 leg fails the build on any top-level "
-            "write outside .claude/). So `install --ceremony user` followed "
-            "later by an upgrade silently violates the guarantee the install "
-            "advertised. This is a latent adjacent bug that only a TREE "
-            "comparison exposes — not an allowlist case"
-        ),
-        "unblocked_by": (
-            "PLAN-166 W1 item 2 / OQ-3: ceremony-gate the protocol refresh in "
-            "upgrade.sh from the same .install-state.json read (own read, "
-            "independent of --no-replay)"
-        ),
-    },
+    # (empty — PLAN-166 W1 landed. F3-spec-stale and F3-protocol-user-mode
+    # were deleted IN the W1 ceremony commit, per the mandatory-fire
+    # contract above: a ledger can never outlive its bug. Add new entries
+    # here ONLY with a mandatory-fire reason + unblocked_by.)
 ]
 
+
 # Paths that must EXIST in both routes once W1 lands. Absent today, so each
 # reports as KNOWN-OPEN (class=expect-path) and holds the run at exit 2.
 # DELIBERATELY NOT mandatory-fire, unlike KNOWN_OPEN above: once the path
 # exists in both trees the entry goes quiet and remains as a PERMANENT
 # existence assert — it re-fires if either route ever stops delivering the
 # marker. No W1 deletion is required for these. Content freshness of a path
 # that IS present is not this list's job either: a present-but-stale marker
 # is caught by the main classification loop (STALE there is FATAL).
 EXPECT_PATHS: List[Dict[str, Optional[str]]] = [
     {
         "id": "F3-framework-version-marker",
         "modes": None,
         "path": ".claude/.framework-version",
         "reason": (
             "OQ-3 moves the framework's own version marker off the adopter's "
             "root VERSION and into .claude/.framework-version, as a TRACKED "
             "file of the framework repo written explicitly by BOTH install "
             "(install_one) and upgrade. Until it exists there is no surface on "
             "which install and upgrade can agree about which framework "
             "generation the adopter is running, and "
             "check-framework-updates.sh keeps resolving the stale root VERSION"
         ),
         "unblocked_by": "PLAN-166 W1 item 2 / OQ-3 (marker) + AC-3",
     },
 ]
 
 
 def _norm_bytes(data: bytes, subs: List[Tuple[bytes, bytes]]) -> bytes:
     for needle, repl in subs:
         if needle:
             data = data.replace(needle, repl)
     return data
 
 
 def _digest(path: str, subs: List[Tuple[bytes, bytes]]) -> Optional[str]:
     try:
         with open(path, "rb") as fh:
             data = fh.read()
     except (IOError, OSError):
         return None
     return hashlib.sha256(_norm_bytes(data, subs)).hexdigest()
 
 
 def _exec_bit(path: str) -> Optional[bool]:
     """True/False for the owner-exec bit; None when the path is unreadable."""
     try:
         return bool(os.stat(path).st_mode & 0o100)
     except OSError:
         return None
 
 
 def _walk(root: str) -> List[str]:
     out: List[str] = []
     for dirpath, dirnames, filenames in os.walk(root):
         dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
         for name in filenames:
             if name.endswith(SKIP_SUFFIX):
                 continue
             full = os.path.join(dirpath, name)
             out.append(os.path.relpath(full, root))
     out.sort()
     return out
 
 
 def _src_digest(root: str, rel: str, subs: List[Tuple[bytes, bytes]]) -> Optional[str]:
     """Source lookup: identity map first, then the templates/ map."""
     for candidate in (os.path.join(root, rel), os.path.join(root, "templates", rel)):
         digest = _digest(candidate, subs)
         if digest is not None:
             return digest
     return None
 
 
 def _matches(rel: str, pattern: str) -> bool:
     return re.search(pattern, rel) is not None
 
 
 def main() -> int:
     ap = argparse.ArgumentParser(description=__doc__)
     ap.add_argument("--a", required=True, help="route A tree (fresh install)")
     ap.add_argument("--b", required=True, help="route B tree (pinned install + upgrade)")
     ap.add_argument("--head-src", required=True, help="working-tree framework source")
     ap.add_argument("--pin-src", required=True, help="extracted <pin> framework source")
     ap.add_argument("--pin", required=True, help="the pinned tag name")
     ap.add_argument("--mode", required=True, help="ceremony mode of this fixture")
     ap.add_argument(
         "--extra-source",
         action="append",
         default=[],
         metavar="DIR",
         help=(
             "additional source root to FOLD to {SOURCE} during normalization "
             "(no content lookups happen against it). The driver passes the "
             "planted-source farm under --positive-control so that the control "
             "fails for the PLANTED reason and not for unfolded absolute paths."
         ),
     )
     args = ap.parse_args()
 
     a_root = os.path.abspath(args.a)

--- full file ---
     1	#!/usr/bin/env python3
     2	"""Classifier for the install/upgrade parity e2e (PLAN-166 W0 / F4, OQ-4).
     3	
     4	Driver: scripts/tests/test-install-upgrade-parity-e2e.sh (read its header for
     5	the why). This module owns the MEASUREMENT and the DECLARATIONS.
     6	
     7	The instrument
     8	--------------
     9	Two adopter trees are handed in:
    10	
    11	    A = install.sh (working tree)
    12	    B = install.sh @ <pin>  ->  upgrade.sh (working tree)
    13	
    14	For every path A delivered, B's bytes are classified against BOTH source
    15	generations, so the verdict is about the *generation of framework content the
    16	adopter ends up running*, not about byte-equality of two installs:
    17	
    18	    IDENTICAL     A(p) == B(p)
    19	    PERSONALIZED  B(p) == head_src(p)  -- upgrade shipped CURRENT framework
    20	                  bytes; install.sh additionally substitutes {{PROJECT_NAME}}
    21	                  and friends.  Advisory: content generation is correct.
    22	    STALE         B(p) == pin_src(p) != head_src(p)  -- the upgrade left the
    23	                  OLD generation in place.  This is F3's exact signature and
    24	                  it is FATAL.
    25	    MISSING_IN_B  install delivered p, upgrade never did.  FATAL.
    26	    UNCLASSIFIED  diverges and matches neither generation.  FATAL unless the
    27	                  path is DECLARED below (generated / adopter-owned).
    28	
    29	Plus, from the other direction, ONLY_IN_B: content upgrade.sh's `cp -R` drags
    30	in that install.sh's selective walk never ships. Advisory in general (ADR-155
    31	documents this as pre-existing install/upgrade drift, and making it fatal today
    32	would only get it neutered by an allowlist), FATAL when it lands outside
    33	`.claude/` in `--ceremony user` mode, because that is the WS4 invariant
    34	smoke-install.yml already asserts for install and nobody asserts for upgrade.
    35	
    36	And MODE_DIFF: same bytes, different executable bit. Bytes-only comparison is
    37	blind to it, and "cp lost the exec bit" is a verified failure mode of this repo
    38	(S286). A hook or script that arrives non-executable through one route and
    39	executable through the other is a real delivery divergence, so it is FATAL.
    40	
    41	W1 CHECKLIST (do not skip)
    42	--------------------------
    43	Every KNOWN_OPEN entry below is MANDATORY-FIRE. When PLAN-166 W1 lands the F3
    44	fix, those entries stop matching and this classifier goes FATAL on ledger-rot
    45	BY DESIGN. Deleting them is part of the W1 commit, in the same commit as the
    46	upgrade.sh/_framework_manifest_set.sh change — that is the mechanism that keeps
    47	a ledger from outliving its bug, not an accident. EXPECT_PATHS is the opposite
    48	shape on purpose: its entries are NOT deleted at W1 — they go quiet when
    49	satisfied and stay behind as permanent existence asserts (see that list's own
    50	comment).
    51	
    52	Anti-rot
    53	--------
    54	Declarations decay, so both directions are checked:
    55	
    56	  * KNOWN_OPEN entries are MANDATORY-FIRE. An entry that matches nothing is
    57	    FATAL: the bug it names is closed, so the entry must be deleted. A ledger
    58	    can never outlive its bug.
    59	  * ACCEPTED entries that turn out IDENTICAL emit a WARNING (stale declaration,
    60	    harmless).
    61	  * Any divergence matching no declaration at all is FATAL. That is the live
    62	    gate; the driver's --positive-control trips exactly there.
    63	
    64	Exit: 0 parity | 1 fatal | 2 only KNOWN_OPEN outstanding.
    65	Python >= 3.9, stdlib only.
    66	"""
    67	
    68	from __future__ import annotations
    69	
    70	import argparse
    71	import hashlib
    72	import os
    73	import re
    74	import sys
    75	from typing import Dict, List, Optional, Tuple
    76	
    77	# ---------------------------------------------------------------------------
    78	# Structural skips: never framework content, never comparable.
    79	# ---------------------------------------------------------------------------
    80	SKIP_DIRS = (".git", ".claude.bak", "__pycache__")
    81	SKIP_SUFFIX = (".pyc",)
    82	
    83	# ---------------------------------------------------------------------------
    84	# ACCEPTED divergence — generated per-install or adopter-owned by contract.
    85	# Every entry carries the AUTHORITY for the claim, not a shrug. These are
    86	# printed as their own census block on every run so the list cannot grow
    87	# quietly.
    88	#   (regex, applies-to-modes or None for all, reason)
    89	# ---------------------------------------------------------------------------
    90	ACCEPTED: List[Tuple[str, Optional[str], str]] = [
    91	    (
    92	        r"^\.claude/\.install-manifest\.sha256$",
    93	        None,
    94	        "derived baseline manifest — regenerated by BOTH routes "
    95	        "(_write_baseline_manifest); it is a hash OF the set under comparison, "
    96	        "so comparing it would be circular",
    97	    ),
    98	    (
    99	        r"^\.claude/\.install-state\.json$",
   100	        None,
   101	        "records the invocation itself (argv, timestamps, source sha, upgrade "
   102	        "ops) — differs by construction between a fresh install and an "
   103	        "install+upgrade; the `ceremony` field is asserted separately below",
   104	    ),
   105	    (
   106	        r"^\.claude/settings\.json$",
   107	        None,
   108	        "install seeds it; upgrade does an ADDITIVE hook merge (PLAN-135 W2 H8) "
   109	        "plus the 3-state baseline migration (PLAN-163 T5.4) and never "
   110	        "clobbers — the two routes converge on keys, not on bytes",
   111	    ),
   112	    (
   113	        r"^\.claude/agent-metrics\.md$",
   114	        None,
   115	        "adopter data — upgrade.sh header: 'Leaves CLAUDE.md, MEMORY.md, "
   116	        ".claude/agent-metrics.md untouched'",
   117	    ),
   118	    (
   119	        r"^(CLAUDE|MEMORY)\.md$",
   120	        None,
   121	        "seed-once adopter doc — same upgrade.sh preserve contract",
   122	    ),
   123	    (
   124	        r"^\.gitignore$",
   125	        None,
   126	        "adopter-owned append-only surface. install.sh APPENDS marker-guarded "
   127	        "blocks (install_posture_state_ignores, PLAN-165 CX-3); upgrade.sh has "
   128	        "no append step, so an upgraded adopter never gets them. A REAL "
   129	        "install-only delivery gap — accepted here (never fatal) only because "
   130	        "the file is adopter-owned and must not be clobbered; reported every "
   131	        "run so it stays visible",
   132	    ),
   133	    (
   134	        r"^PROTOCOL\.md$",
   135	        "maintainer",
   136	        "generated pointer. install.sh substitutes the resolved SOURCE_DIR; "
   137	        "upgrade.sh's _refresh_protocol_pointer emits the literal "
   138	        "{{PROTOCOL_SOURCE}} placeholder. Body-only divergence, pre-existing "
   139	        "asymmetry of the same pointer file",
   140	    ),
   141	    (
   142	        r"^VERSION$",
   143	        "maintainer",
   144	        "BY DESIGN (PLAN-166 OQ-3 / ADR-155-AMEND-1): the upgrade must NOT "
   145	        "touch the adopter's root VERSION — install_one is skip-if-exists, so "
   146	        "in an adopter that owns a VERSION the framework never wrote there and "
   147	        "backup_and_replace would TAKE the file (the verified S238 worst "
   148	        "case). The framework's own version marker moves to "
   149	        ".claude/.framework-version. Asserted positively below: B/VERSION must "
   150	        "be byte-identical to the pinned source's VERSION (untouched), not "
   151	        "merely different",
   152	    ),
   153	]
   154	
   155	# ---------------------------------------------------------------------------
   156	# KNOWN_OPEN — PLAN-166 W1 prerequisites. MANDATORY-FIRE (see module docstring).
   157	#   id, modes (None = all), class, regex, reason, unblocked_by
   158	# ---------------------------------------------------------------------------
   159	KNOWN_OPEN: List[Dict[str, Optional[str]]] = [
   160	    # (empty — PLAN-166 W1 landed. F3-spec-stale and F3-protocol-user-mode
   161	    # were deleted IN the W1 ceremony commit, per the mandatory-fire
   162	    # contract above: a ledger can never outlive its bug. Add new entries
   163	    # here ONLY with a mandatory-fire reason + unblocked_by.)
   164	]
   165	
   166	
   167	# Paths that must EXIST in both routes once W1 lands. Absent today, so each
   168	# reports as KNOWN-OPEN (class=expect-path) and holds the run at exit 2.
   169	# DELIBERATELY NOT mandatory-fire, unlike KNOWN_OPEN above: once the path
   170	# exists in both trees the entry goes quiet and remains as a PERMANENT
   171	# existence assert — it re-fires if either route ever stops delivering the
   172	# marker. No W1 deletion is required for these. Content freshness of a path
   173	# that IS present is not this list's job either: a present-but-stale marker
   174	# is caught by the main classification loop (STALE there is FATAL).
   175	EXPECT_PATHS: List[Dict[str, Optional[str]]] = [
   176	    {
   177	        "id": "F3-framework-version-marker",
   178	        "modes": None,
   179	        "path": ".claude/.framework-version",
   180	        "reason": (
   181	            "OQ-3 moves the framework's own version marker off the adopter's "
   182	            "root VERSION and into .claude/.framework-version, as a TRACKED "
   183	            "file of the framework repo written explicitly by BOTH install "
   184	            "(install_one) and upgrade. Until it exists there is no surface on "
   185	            "which install and upgrade can agree about which framework "
   186	            "generation the adopter is running, and "
   187	            "check-framework-updates.sh keeps resolving the stale root VERSION"
   188	        ),
   189	        "unblocked_by": "PLAN-166 W1 item 2 / OQ-3 (marker) + AC-3",
   190	    },
   191	]
   192	
   193	
   194	def _norm_bytes(data: bytes, subs: List[Tuple[bytes, bytes]]) -> bytes:
   195	    for needle, repl in subs:
   196	        if needle:
   197	            data = data.replace(needle, repl)
   198	    return data
   199	
   200	
   201	def _digest(path: str, subs: List[Tuple[bytes, bytes]]) -> Optional[str]:
   202	    try:
   203	        with open(path, "rb") as fh:
   204	            data = fh.read()
   205	    except (IOError, OSError):
   206	        return None
   207	    return hashlib.sha256(_norm_bytes(data, subs)).hexdigest()
   208	
   209	
   210	def _exec_bit(path: str) -> Optional[bool]:
   211	    """True/False for the owner-exec bit; None when the path is unreadable."""
   212	    try:
   213	        return bool(os.stat(path).st_mode & 0o100)
   214	    except OSError:
   215	        return None
   216	
   217	
   218	def _walk(root: str) -> List[str]:
   219	    out: List[str] = []
   220	    for dirpath, dirnames, filenames in os.walk(root):
   221	        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
   222	        for name in filenames:
   223	            if name.endswith(SKIP_SUFFIX):
   224	                continue
   225	            full = os.path.join(dirpath, name)
   226	            out.append(os.path.relpath(full, root))
   227	    out.sort()
   228	    return out
   229	
   230	
   231	def _src_digest(root: str, rel: str, subs: List[Tuple[bytes, bytes]]) -> Optional[str]:
   232	    """Source lookup: identity map first, then the templates/ map."""
   233	    for candidate in (os.path.join(root, rel), os.path.join(root, "templates", rel)):
   234	        digest = _digest(candidate, subs)
   235	        if digest is not None:
   236	            return digest
   237	    return None
   238	
   239	
   240	def _matches(rel: str, pattern: str) -> bool:
   241	    return re.search(pattern, rel) is not None
   242	
   243	
   244	def main() -> int:
   245	    ap = argparse.ArgumentParser(description=__doc__)
   246	    ap.add_argument("--a", required=True, help="route A tree (fresh install)")
   247	    ap.add_argument("--b", required=True, help="route B tree (pinned install + upgrade)")
   248	    ap.add_argument("--head-src", required=True, help="working-tree framework source")
   249	    ap.add_argument("--pin-src", required=True, help="extracted <pin> framework source")
   250	    ap.add_argument("--pin", required=True, help="the pinned tag name")
   251	    ap.add_argument("--mode", required=True, help="ceremony mode of this fixture")
   252	    ap.add_argument(
   253	        "--extra-source",
   254	        action="append",
   255	        default=[],
   256	        metavar="DIR",
   257	        help=(
   258	            "additional source root to FOLD to {SOURCE} during normalization "
   259	            "(no content lookups happen against it). The driver passes the "
   260	            "planted-source farm under --positive-control so that the control "
   261	            "fails for the PLANTED reason and not for unfolded absolute paths."
   262	        ),
   263	    )
   264	    args = ap.parse_args()
   265	
   266	    a_root = os.path.abspath(args.a)
   267	    b_root = os.path.abspath(args.b)
   268	    head_src = os.path.abspath(args.head_src)
   269	    pin_src = os.path.abspath(args.pin_src)
   270	
   271	    # Normalization: an installed tree legitimately embeds its own absolute
   272	    # target path and the absolute source path (PROTOCOL.md pointer, CLAUDE.md
   273	    # bootstrap line). Those are INSTALLATION-INSTANCE facts, not framework
   274	    # content, so they are folded to placeholders before hashing. Both the
   275	    # logical and the realpath form are folded (macOS mktemp hands out
   276	    # /var/... which is a symlink to /private/var).
   277	    norm_roots = [
   278	        (a_root, b"{TARGET}"),
   279	        (b_root, b"{TARGET}"),
   280	        (head_src, b"{SOURCE}"),
   281	        (pin_src, b"{SOURCE}"),
   282	    ]
   283	    for extra in args.extra_source:
   284	        norm_roots.append((os.path.abspath(extra), b"{SOURCE}"))
   285	    subs: List[Tuple[bytes, bytes]] = []
   286	    for root, token in norm_roots:
   287	        for form in (root, os.path.realpath(root)):
   288	            pair = (form.encode("utf-8"), token)
   289	            if pair not in subs:
   290	                subs.append(pair)
   291	    # Longest needle first: /private/var/... must be folded before /var/...
   292	    subs.sort(key=lambda p: len(p[0]), reverse=True)
   293	
   294	    a_files = _walk(a_root)
   295	    b_files = _walk(b_root)
   296	    a_set = set(a_files)
   297	    b_set = set(b_files)
   298	
   299	    buckets: Dict[str, List[str]] = {
   300	        "IDENTICAL": [],
   301	        "PERSONALIZED": [],
   302	        "STALE": [],
   303	        "MISSING_IN_B": [],
   304	        "UNCLASSIFIED": [],
   305	        "ONLY_IN_B": [],
   306	        "ONLY_IN_B_OUTSIDE_CLAUDE": [],
   307	        "MODE_DIFF": [],
   308	    }
   309	    accepted_hits: List[Tuple[str, str]] = []      # (rel, reason)
   310	    accepted_seen: Dict[int, int] = {}
   311	
   312	    for rel in a_files:
   313	        ha = _digest(os.path.join(a_root, rel), subs)
   314	        hb = _digest(os.path.join(b_root, rel), subs)
   315	        if hb is None:
   316	            cls = "MISSING_IN_B"
   317	        elif ha == hb:
   318	            cls = "IDENTICAL"
   319	        else:
   320	            h_head = _src_digest(head_src, rel, subs)

exec
/bin/zsh -lc 'git diff --no-ext-diff --unified=20 -- .claude/scripts/tests/test_release_workflow_asserts.py' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
diff --git a/.claude/scripts/tests/test_release_workflow_asserts.py b/.claude/scripts/tests/test_release_workflow_asserts.py
index bc68a9f..3518bb3 100644
--- a/.claude/scripts/tests/test_release_workflow_asserts.py
+++ b/.claude/scripts/tests/test_release_workflow_asserts.py
@@ -8,72 +8,225 @@ workflow-invariant convention (test_workflow_devops_p2.py) with:
 - version↔plugin-manifest sync: VERSION == .claude-plugin/plugin.json
   version == every `version` field in .claude-plugin/marketplace.json
   (skip-if-absent until PLAN-153 Wave B item 6 generates the manifests
   via build-plugin.py — same skipTest pattern test_npm_rebuild.py uses
   for the release-only npm bundle);
 - RC posture pins on npm-publish.yml: RC tags stay hard-excluded from
   npm publishing (PLAN-013 anti-goals #3/#16, re-ratified by the
   PLAN-153 debate: the `next` dist-tag idea was DROPPED);
 - release-notes template invariants (.github/release-notes-template.md,
   closes PLAN-152 §Deferred release-notes-hardcoded-first-release);
 - dual-context asserts on the Wave B workflow edits themselves
   (npm-publish.yml `already_published` guard; release.yml
   `gh release view || gh release create` idempotency; `-rc.N` strip in
   the VERSION + CHANGELOG gates, closing PLAN-152 §Deferred
   release-gate-rc-version-mismatch / red run 28663453202): enforced
   against the STAGED copy while it exists on disk
   (.claude/plans/PLAN-153/staged/wave-B/ is gitignored → absent in CI)
   and against the LIVE workflow once Wave B lands (detected via the
   "PLAN-153 Wave B item 5" marker). They skip only in the pre-landing
   CI window where neither context is available.
+
+PLAN-166 W1 items 1 + 4 (F1, P0) extend the same dual-context convention
+(staged mirror under .claude/plans/PLAN-166/staged/ pre-landing,
+"PLAN-166 W1 item 1" marker in the live file post-landing) with:
+
+- await-gate asserts: the publish OBSERVES release.yml's `release-gate`
+  job — `await-release-gate` job present, `needs:` on the publish job,
+  `GH_TOKEN: ${{ github.token }}` in the await job's env (permissions:
+  alone does NOT authenticate the gh CLI on a hosted runner; without the
+  token every poll dies on auth = fail-closed BLOCK breaking every
+  release), permissions/timeout pinned, and NO environment / NO RC
+  exclusion on the await job (RC tags are the live positive control).
+  Posture pins are STRENGTHENED, not relocated: NpmPublishRcPostureTest
+  keeps asserting the RC exclusion + environment on the live file.
+- trusted-publisher binding asserts: the npmjs OIDC registration triple
+  (repository / workflow FILENAME / environment) is cross-checked by
+  READING .claude/governance/npm-trusted-publisher.txt — embedding the
+  values in the test would create a 4th copy of the truth. Includes
+  positive controls: mutating `environment:` (or the repository slug) in
+  a COPY of the workflow text must go red.
+
+PLAN-166 W1-B (F2 server side; merged in by the ceremony assembler —
+one runnable asserts file) adds the W1B* classes at the bottom:
+structural asserts for release.yml's verdict delta + ancestry gate step
+(no continue-on-error, fail-closed on the transition var, delegation to
+_release_tag_guard.py, parent+GITHUB_SHA ancestry, pinned step order,
+`release-gate` job-name pin) plus the guard-module contract pins.
 """
 from __future__ import annotations
 
 import json
 import re
 import sys
 import unittest
 from pathlib import Path
 from typing import Iterator, Optional, Tuple
 
-_REPO = Path(__file__).resolve().parent.parent.parent.parent
+def _find_repo() -> Path:
+    """Repo root — robust to BOTH homes this file can run from.
+
+    At its landed path (.claude/scripts/tests/) four parents reach the
+    root; at its staged path (.claude/plans/PLAN-166/staged/...) they
+    reach the staged mirror instead. Walk up to the first ancestor that
+    actually looks like the repo (has the live workflow AND the hooks
+    tree) so pre-land verification runs from the staged location give
+    the same answers as post-land runs. (Merged in from the W1-B slice
+    by the PLAN-166 ceremony assembler.)
+    """
+    here = Path(__file__).resolve()
+    for candidate in here.parents:
+        if (
+            (candidate / ".github" / "workflows" / "release.yml").is_file()
+            and (candidate / ".claude" / "hooks" / "_lib").is_dir()
+        ):
+            return candidate
+    # Fall back to the landed-layout arithmetic; setUp guards will skip
+    # or fail loudly if this is wrong.
+    return here.parent.parent.parent.parent
+
+
+_REPO = _find_repo()
 _WF = _REPO / ".github" / "workflows"
 _STAGED_WF = (
     _REPO / ".claude" / "plans" / "PLAN-153" / "staged" / "wave-B"
     / ".github" / "workflows"
 )
 _TEMPLATE = _REPO / ".github" / "release-notes-template.md"
 _PLUGIN_DIR = _REPO / ".claude-plugin"
 
 # Bootstrap TestEnvContext so env isolation holds (env-hygiene gate).
 _HOOKS_DIR = _REPO / ".claude" / "hooks"
 if str(_HOOKS_DIR) not in sys.path:
     sys.path.insert(0, str(_HOOKS_DIR))
 from _lib.testing import TestEnvContext  # noqa: E402
 
 # Marker written into both Wave B workflow edits; its presence in the
 # LIVE file means Wave B has landed and the live copy is authoritative.
 _MARKER = "PLAN-153 Wave B item 5"
 
 # The load-bearing RC exclusion (PLAN-013 anti-goals #3/#16).
 _RC_EXCLUSION = "!contains(github.ref, '-rc.')"
 
+# --- PLAN-166 W1 items 1 + 4 (F1, P0) --------------------------------
+# Marker written into the PLAN-166 npm-publish.yml edit; its presence in
+# the LIVE file means the W1 ceremony landed and the live copy is
+# authoritative (same convention as _MARKER above).
+_MARKER_166 = "PLAN-166 W1 item 1"
+
+_STAGED_166 = _REPO / ".claude" / "plans" / "PLAN-166" / "staged"
+_STAGED_166_WF = _STAGED_166 / ".github" / "workflows"
+
+# Repo-side record of the npmjs trusted-publisher OIDC binding triple.
+_TRUSTED_PUBLISHER = (
+    _REPO / ".claude" / "governance" / "npm-trusted-publisher.txt"
+)
+_STAGED_166_TRUSTED_PUBLISHER = (
+    _STAGED_166 / ".claude" / "governance" / "npm-trusted-publisher.txt"
+)
+_TRUSTED_PUBLISHER_KEYS = frozenset({"repository", "workflow", "environment"})
+
+
+def _plan166_text(name: str) -> Optional[Tuple[str, str]]:
+    """Return (text, context) for a PLAN-166 workflow edit, or None pre-landing.
+
+    Priority: live copy carrying the PLAN-166 marker (post-landing,
+    authoritative) → staged copy under .claude/plans/PLAN-166/staged/
+    (pre-landing, local ceremony mirror; gitignored so absent in CI) →
+    None (pre-landing CI: skip). Unlike _wave_b_text this tolerates a
+    missing live file — the filename-binding test reports that as a
+    FAILURE, not a collection error.
+    """
+    live = _WF / name
+    if live.is_file():
+        text = live.read_text(encoding="utf-8")
+        if _MARKER_166 in text:
+            return text, "live"
+    staged = _STAGED_166_WF / name
+    if staged.is_file():
+        return staged.read_text(encoding="utf-8"), "staged"
+    return None
+
+
+def _trusted_publisher_values() -> Optional[Tuple[dict, str]]:
+    """Parse npm-trusted-publisher.txt (live → staged), or None pre-landing.
+
+    Format contract (documented in the file itself): `key=value` lines;
+    `#`-prefixed and blank lines are comments; keys are EXACTLY
+    repository/workflow/environment. Malformed content raises — a
+    binding record we cannot parse must never silently skip the binding
+    asserts (fail-closed, ADR-186 posture).
+    """
+    for path, context in (
+        (_TRUSTED_PUBLISHER, "live"),
+        (_STAGED_166_TRUSTED_PUBLISHER, "staged"),
+    ):
+        if not path.is_file():
+            continue
+        values = {}
+        for lineno, raw in enumerate(
+            path.read_text(encoding="utf-8").splitlines(), 1
+        ):
+            line = raw.strip()
+            if not line or line.startswith("#"):
+                continue
+            key, sep, value = line.partition("=")
+            key, value = key.strip(), value.strip()
+            if not sep or not key or not value:
+                raise AssertionError(
+                    "%s:%d: expected key=value, got %r" % (path, lineno, raw)
+                )
+            if key in values:
+                raise AssertionError(
+                    "%s:%d: duplicate key %r" % (path, lineno, key)
+                )
+            values[key] = value
+        if set(values) != set(_TRUSTED_PUBLISHER_KEYS):
+            raise AssertionError(
+                "%s must define exactly %s, got %s"
+                % (path, sorted(_TRUSTED_PUBLISHER_KEYS), sorted(values))
+            )
+        return values, context
+    return None
+
+
+def _binding_mismatches(values: dict, workflow_text: str) -> list:
+    """Which parts of the trusted-publisher triple the workflow does NOT honour.
+
+    Pure text→list (no filesystem) so the positive-control tests can run
+    it against a deliberately mutated COPY of the workflow text.
+    """
+    mismatches = []
+    if ("environment: " + values["environment"]) not in workflow_text:
+        mismatches.append(
+            "workflow does not gate through `environment: %s` — the npmjs "
+            "trusted-publisher registration names that environment"
+            % values["environment"]
+        )
+    if values["repository"] not in workflow_text:
+        mismatches.append(
+            "workflow no longer names the registered repository %r (the "
+            "OIDC registration comment is the in-file record)"
+            % values["repository"]
+        )
+    return mismatches
+
 
 def _wave_b_text(name: str) -> Optional[Tuple[str, str]]:
     """Return (text, context) for a Wave B workflow, or None pre-landing.
 
     Priority: live copy carrying the Wave B marker (post-landing,
     authoritative) → staged copy (pre-landing, local ceremony mirror;
     gitignored so absent in CI) → None (pre-landing CI: skip).
     """
     live = (_WF / name).read_text(encoding="utf-8")
     if _MARKER in live:
         return live, "live"
     staged = _STAGED_WF / name
     if staged.is_file():
         return staged.read_text(encoding="utf-8"), "staged"
     return None
 
 
 def _iter_version_fields(obj: object) -> Iterator[str]:
     """Yield every string-valued `version` field nested anywhere in obj."""
     if isinstance(obj, dict):
@@ -202,55 +355,57 @@ class ReleaseNotesTemplateTest(TestEnvContext):
 
     def test_only_known_placeholders_used(self):
         # The workflow substitutes exactly TAG/VERSION/BASE_VERSION and
         # fails closed on any '{{' left after rendering; an unknown
         # token here would brick every release.
         unknown = set(re.findall(r"\{\{([^}]*)\}\}", self.source)) - {
             "TAG", "VERSION", "BASE_VERSION",
         }
         self.assertEqual(unknown, set(), f"unknown placeholders: {unknown}")
 
 
 class WorkflowHygieneTest(TestEnvContext):
     """Parse + SHA-pin discipline for both tag-triggered workflows."""
 
     def test_workflows_parse_as_yaml(self):
         try:
             import yaml  # type: ignore
         except ImportError:  # pragma: no cover - CI installs pyyaml
             self.skipTest("pyyaml not installed")
         for name in ("release.yml", "npm-publish.yml"):
-            for path in ((_WF / name), (_STAGED_WF / name)):
+            for path in ((_WF / name), (_STAGED_WF / name),
+                         (_STAGED_166_WF / name)):
                 if not path.is_file():
                     continue
                 with self.subTest(path=str(path)):
                     data = yaml.safe_load(path.read_text(encoding="utf-8"))
                     self.assertIsInstance(data, dict)
                     self.assertIn("jobs", data)
 
     def test_all_action_uses_are_sha_pinned(self):
         # Every `uses:` in both workflows (live + staged copies) must
         # pin to a 40-hex commit SHA — no floating tags.
         pattern = re.compile(r"^\s*(?:-\s+)?uses:\s*(\S+)", re.MULTILINE)
         pinned = re.compile(r".+@[0-9a-f]{40}$")
         for name in ("release.yml", "npm-publish.yml"):
-            for path in ((_WF / name), (_STAGED_WF / name)):
+            for path in ((_WF / name), (_STAGED_WF / name),
+                         (_STAGED_166_WF / name)):
                 if not path.is_file():
                     continue
                 text = path.read_text(encoding="utf-8")
                 for used in pattern.findall(text):
                     with self.subTest(path=str(path), uses=used):
                         self.assertRegex(
                             used, pinned,
                             f"{path.name}: `uses: {used}` is not "
                             "SHA-pinned to a 40-hex commit",
                         )
 
 
 class WaveB5ReleaseYmlTest(TestEnvContext):
     """Wave B item 5 edits to release.yml (dual-context: staged/live)."""
 
     def setUp(self):
         super().setUp()
         resolved = _wave_b_text("release.yml")
         if resolved is None:
             self.skipTest(
@@ -318,22 +473,544 @@ class WaveB5NpmPublishYmlTest(TestEnvContext):
         )
 
     def test_publish_step_gated_on_guard(self):
         self.assertIn(
             "if: steps.already_published.outputs.published != 'true'",
             self.source,
         )
 
     def test_noop_success_path_is_explicit(self):
         self.assertIn(
             "if: steps.already_published.outputs.published == 'true'",
             self.source,
         )
 
     def test_rc_exclusion_survives_wave_b(self):
         # Item 5 (f): the Wave B edit must NOT weaken the RC posture.
         self.assertIn(_RC_EXCLUSION, self.source)
         self.assertIn("environment: production-npm", self.source)
 
 
+class Plan166AwaitGateTest(TestEnvContext):
+    """PLAN-166 W1 item 1 — the publish must OBSERVE release.yml's gate.
+
+    Dual-context (staged/live) like the Wave B classes above. These pins
+    STRENGTHEN the posture pins — NpmPublishRcPostureTest keeps running
+    against the live file in every context.
+    """
+
+    def setUp(self):
+        super().setUp()
+        resolved = _plan166_text("npm-publish.yml")
+        if resolved is None:
+            self.skipTest(
+                "PLAN-166 npm-publish.yml not landed and staged mirror "
+                "absent (pre-landing CI window)"
+            )
+        self.source, self.context = resolved
+
+    def _jobs(self) -> dict:
+        try:
+            import yaml  # type: ignore
+        except ImportError:  # pragma: no cover - CI installs pyyaml
+            self.skipTest("pyyaml not installed")
+        return yaml.safe_load(self.source)["jobs"]
+
+    def test_publish_needs_await_gate(self):
+        # String-level (runs even without pyyaml): the load-bearing edge.
+        self.assertIn(
+            "needs: await-release-gate", self.source,
+            "publish no longer waits for the await-release-gate job — "
+            "the npm publish would stop observing release.yml's "
+            "release-gate (PLAN-166 F1, P0)",
+        )
+
+    def test_publish_needs_await_gate_structurally(self):
+        jobs = self._jobs()
+        self.assertEqual(
+            jobs["publish"].get("needs"), "await-release-gate",
+            "the `needs:` must sit on the PUBLISH job itself",
+        )
+
+    def test_await_job_authenticates_gh_cli(self):
+        # `permissions:` alone does NOT authenticate the gh CLI on a
+        # hosted runner; without GH_TOKEN every poll dies on auth →
+        # fail-closed BLOCK breaking every release, RC and GA alike.
+        self.assertIn("GH_TOKEN: ${{ github.token }}", self.source)
+        jobs = self._jobs()
+        env = jobs["await-release-gate"].get("env") or {}
+        self.assertEqual(
+            env.get("GH_TOKEN"), "${{ github.token }}",
+            "await-release-gate must carry GH_TOKEN at the JOB level",
+        )
+
+    def test_await_job_permissions_and_timeout(self):
+        jobs = self._jobs()
+        gate = jobs["await-release-gate"]
+        self.assertEqual(
+            gate.get("permissions"),
+            {"contents": "read", "actions": "read"},
+            "await job needs exactly contents:read (checkout) + "
+            "actions:read (runs/jobs REST) — and nothing more (no "
+            "id-token: the gate job must not be able to publish)",
+        )
+        self.assertEqual(
+            gate.get("timeout-minutes"), 35,
+            "35 > the poller's 30-minute deadline so a timeout surfaces "
+            "as the decision function's fail-CLOSED BLOCK, not an opaque "
+            "runner kill",
+        )
+
+    def test_await_job_is_the_rc_positive_control(self):
+        # NO environment (no manual approval before evidence) and NO RC
+        # exclusion: the await job runs on rc tags, so every RC is a live
+        # positive control of the gate before GA depends on it.
+        jobs = self._jobs()
+        gate = jobs["await-release-gate"]
+        self.assertNotIn(
+            "environment", gate,
+            "await-release-gate must NOT gate through an environment — "
+            "manual approval belongs AFTER the machine evidence",
+        )
+        self.assertNotIn(
+            "if", gate,
+            "await-release-gate must NOT exclude RC tags — RC runs are "
+            "the live positive control",
+        )
+
+    def test_await_job_invokes_decision_function(self):
+        self.assertIn(".claude/scripts/await_release_gate.py", self.source)
+        # The deadline is what makes every non-GRANT state collapse to
+        # BLOCK (fail-closed) instead of polling forever.
+        self.assertIn("--deadline-epoch", self.source)
+
+    def test_publish_posture_verbatim(self):
+        jobs = self._jobs()
+        pub = jobs["publish"]
+        self.assertEqual(pub.get("environment"), "production-npm")
+        self.assertIn(_RC_EXCLUSION, pub.get("if", ""))
+
+    def test_already_published_guard_stays_in_publish_after_needs(self):
+        # Deliberate ordering (PLAN-166 OQ-1): gate first, manual
+        # approval second, last-resort idempotency guard INSIDE publish.
+        self.assertLess(
+            self.source.index("needs: await-release-gate"),
+            self.source.index("id: already_published"),
+            "already_published must remain in the publish job, after "
+            "the needs: edge — do not move it into the gate job",
+        )
+
+
+class TrustedPublisherBindingTest(TestEnvContext):
+    """PLAN-166 W1 item 4 — the npmjs OIDC trusted-publisher triple.
+
+    npm trusted publishing binds by repository + workflow FILENAME +
+    environment (oidc-failure-playbook.md:18). This class READS
+    .claude/governance/npm-trusted-publisher.txt and cross-checks the
+    workflow — it embeds NO values (a 4th copy of the truth).
+    """
+
+    def setUp(self):
+        super().setUp()
+        resolved = _trusted_publisher_values()
+        if resolved is None:
+            self.skipTest(
+                "npm-trusted-publisher.txt not landed and staged copy "
+                "absent (pre-landing CI window)"
+            )
+        self.values, self.txt_context = resolved
+        wf_name = self.values["workflow"]
+        wf = _plan166_text(wf_name)
+        if wf is not None:
+            self.workflow_text, self.wf_context = wf
+        else:
+            live = _WF / wf_name
+            if not live.is_file():
+                self.fail(
+                    "trusted publisher registers workflow %r but "
+                    ".github/workflows/%s does not exist — the OIDC "
+                    "binding is by FILENAME; publishing would die "
+                    "ENEEDAUTH at GA" % (wf_name, wf_name)
+                )
+            self.workflow_text = live.read_text(encoding="utf-8")
+            self.wf_context = "live-pre-plan166"
+
+    def test_registered_workflow_file_publishes(self):
+        self.assertIn(
+            "npm publish --provenance", self.workflow_text,
+            "the workflow the npmjs console points at must be the one "
+            "actually publishing",
+        )
+
+    def test_workflow_honours_registered_binding(self):
+        self.assertEqual(
+            _binding_mismatches(self.values, self.workflow_text), [],
+            "npm-publish.yml drifted from the npmjs trusted-publisher "
+            "registration recorded in npm-trusted-publisher.txt",
+        )
+
+    def test_positive_control_environment_mutation_goes_red(self):
+        # PLAN-166 W1 item 4 required control: flipping `environment:`
+        # in a COPY must be detected — otherwise this whole class is a
+        # vacuous gate (registered-vacuous class, S292).
+        needle = "environment: " + self.values["environment"]
+        self.assertIn(needle, self.workflow_text)
+        mutated = self.workflow_text.replace(
+            needle, "environment: NOT-THE-REGISTERED-ENV"
+        )
+        self.assertNotEqual(
+            _binding_mismatches(self.values, mutated), [],
+            "positive control failed: a mutated environment was not "
+            "flagged — the binding check is vacuous",
+        )
+
+    def test_positive_control_repository_mutation_goes_red(self):
+        self.assertIn(self.values["repository"], self.workflow_text)
+        mutated = self.workflow_text.replace(
+            self.values["repository"], "someone-else/some-fork"
+        )
+        self.assertNotEqual(
+            _binding_mismatches(self.values, mutated), [],
+            "positive control failed: a mutated repository slug was not "
+            "flagged — the binding check is vacuous",
+        )
+
+
+# ---------------------------------------------------------------------
+# PLAN-166 W1-B — structural asserts for the release.yml verdict delta +
+# ancestry gate (F2 server side; re-pass r15+r17+r18, debate r3 scoped
+# VETO). Merged verbatim from the W1-B slice file
+# (test_release_workflow_asserts_w1b.py) by the PLAN-166 ceremony
+# assembler — one runnable asserts file per the W1 pack discipline. Only
+# names that would collide with the W1-A section above were renamed
+# (_MARKER → _MARKER_W1B, _LIVE_WF/_STAGED_WF → _W1B_*).
+#
+# What is pinned here, and why each pin exists:
+# - The gate step exists, carries NO continue-on-error, and FAILS CLOSED
+#   on CEO_PAIR_RAIL_VERDICT_OPTIONAL=1 — the step-15 neighbourhood has
+#   two escape hatches keyed to that var (`continue-on-error:` and the
+#   empty `--parent-sha ""` bind, which the validator only binds when
+#   non-empty); the new gate must never inherit the switch.
+# - The delta decision is DELEGATED to
+#   .claude/scripts/local/_release_tag_guard.py (the reference
+#   implementation) — never re-implemented in bash.
+# - Ancestry covers BOTH the reviewed parent AND GITHUB_SHA (r18:
+#   parent-only lets the tag-without-push / orphan-verdict scenario pass).
+# - PINNED ORDER: Verify tag GPG signature → Validate pair-rail verdict →
+#   delta → ancestry.
+# - The job keeps the exact name `release-gate` — the W1-A
+#   await-release-gate poller resolves the job BY NAME via the Actions
+#   jobs endpoint; renaming the job silently breaks the npm-publish gate.
+# ---------------------------------------------------------------------
+
+# Marker written into the W1-B step's comment block; its presence in the
+# LIVE file means the ceremony landed and the live copy is authoritative.
+_MARKER_W1B = "PLAN-166 W1-B"
+
+_W1B_LIVE_WF = _WF / "release.yml"
+_W1B_STAGED_WF = _STAGED_166_WF / "release.yml"
+
+_W1B_STEP_NAME = "Verify verdict delta + ancestry (fail-closed)"
+_W1B_STEP15_NAME = "Validate pair-rail verdict"
+_W1B_GPG_STEP_NAME = "Verify tag GPG signature"
+_GUARD_MODULE = ".claude/scripts/local/_release_tag_guard.py"
+
+
+def _w1b_release_text() -> Optional[Tuple[str, str]]:
+    """Return (text, context) for release.yml, or None pre-landing.
+
+    Priority: live copy carrying the W1-B marker (post-landing,
+    authoritative) → staged ceremony copy (pre-landing local mirror;
+    gitignored so absent in CI) → None (pre-landing CI: skip).
+    """
+    if _W1B_LIVE_WF.is_file():
+        live = _W1B_LIVE_WF.read_text(encoding="utf-8")
+        if _MARKER_W1B in live:
+            return live, "live"
+    if _W1B_STAGED_WF.is_file():
+        return _W1B_STAGED_WF.read_text(encoding="utf-8"), "staged"
+    return None
+
+
+def _step_block(source: str, step_name: str) -> str:
+    """The text of one step: from its `- name:` to the next step/job."""
+    start = source.index("- name: %s" % step_name)
+    nxt = source.find("\n      - name:", start + 1)
+    job = source.find("\n  publish-release:", start + 1)
+    candidates = [i for i in (nxt, job) if i != -1]
+    end = min(candidates) if candidates else len(source)
+    return source[start:end]
+
+
+class W1BReleaseGateDeltaAncestryTest(TestEnvContext):
+    """The verdict delta + ancestry gate step (dual-context)."""
+
+    def setUp(self):
+        super().setUp()
+        resolved = _w1b_release_text()
+        if resolved is None:
+            self.skipTest(
+                "PLAN-166 W1-B release.yml not landed and staged mirror "
+                "absent (pre-landing CI window)"
+            )
+        self.source, self.context = resolved
+
+    # -- existence + independence from the step-15 escape hatches --------
+
+    def test_gate_step_present(self):
+        self.assertIn(
+            "- name: %s" % _W1B_STEP_NAME, self.source,
+            "the W1-B verdict delta + ancestry gate step is missing",
+        )
+
+    def test_gate_step_has_no_continue_on_error(self):
+        block = _step_block(self.source, _W1B_STEP_NAME)
+        self.assertNotIn(
+            "continue-on-error", block,
+            "the W1-B gate must NEVER carry continue-on-error — that is "
+            "exactly the step-15 escape hatch it exists to be independent "
+            "of (debate r3 scoped VETO)",
+        )
+
+    def test_file_carries_exactly_one_continue_on_error(self):
+        # The legacy step 15 keeps its documented transition hatch
+        # UNCHANGED (the plan adds a new step; it does not rewrite the
+        # neighbourhood). Exactly one KEY occurrence pins both
+        # directions at once: the hatch was not silently removed from
+        # step 15, and no step (new or old) gained a second one. Comment
+        # mentions of the phrase do not count — only the YAML key form.
+        key_form = re.findall(
+            r"^\s*continue-on-error:", self.source, re.MULTILINE
+        )
+        self.assertEqual(
+            len(key_form), 1,
+            "release.yml must carry exactly one continue-on-error KEY "
+            "(the legacy step-15 transition hatch); found %d"
+            % len(key_form),
+        )
+
+    def test_gate_fails_closed_on_transition_var(self):
+        block = _step_block(self.source, _W1B_STEP_NAME)
+        self.assertIn(
+            'if [ "${CEO_PAIR_RAIL_VERDICT_OPTIONAL}" = "1" ]', block,
+            "the W1-B gate must test the transition var explicitly",
+        )
+        guard = block.index(
+            'if [ "${CEO_PAIR_RAIL_VERDICT_OPTIONAL}" = "1" ]'
+        )
+        self.assertIn(
+            "exit 1", block[guard:guard + 400],
+            "the transition-var guard must FAIL CLOSED (exit 1), not skip",
+        )
+
+    def test_gate_never_builds_an_empty_parent_bind(self):
+        # The step-15 hatch shape: PARENT_SHA_ARG="" under the var. The
+        # W1-B block must not contain that shape in any form.
+        block = _step_block(self.source, _W1B_STEP_NAME)
+        self.assertNotIn('PARENT_SHA_ARG=""', block)
+        self.assertNotIn('--parent-sha ""', block)
+
+    def test_gate_binds_parent_sha_independently(self):
+        block = _step_block(self.source, _W1B_STEP_NAME)
+        self.assertIn(
+            'VERDICT_FILE_COMMIT="$(git log -n1 --format=%H -- "$VERDICT_FILE")"',
+            block,
+            "the gate must derive the verdict-file commit itself",
+        )
+        self.assertIn(
+            "_parse_verdict", block,
+            "the verdict's parent_sha must be read with the guard "
+            "module's parser — two readers of the same signed file must "
+            "not be able to disagree",
+        )
+
+    # -- delegation to the reference implementation ----------------------
+
+    def test_delta_delegates_to_guard_module(self):
+        block = _step_block(self.source, _W1B_STEP_NAME)
+        self.assertIn(
+            "%s delta" % _GUARD_MODULE, block,
+            "the delta decision must be delegated to the tag-guard "
+            "module (single source of the decision logic)",
+        )
+
+    def test_ancestry_delegates_to_guard_module(self):
+        block = _step_block(self.source, _W1B_STEP_NAME)
+        self.assertIn(
+            "%s ancestry" % _GUARD_MODULE, block,
+            "the HEAD-ancestry judgment (fail-closed fetch included) "
+            "must be delegated to the tag-guard module",
+        )
+
+    def test_delta_semantics_not_reimplemented_in_bash(self):
+        # The bash body must not carry the decision vocabulary of the
+        # module — reading the allowlist or hashing the manifest in
+        # shell would be a second implementation of the same closed-set
+        # semantics. Comment lines are excluded: the step's rationale
+        # comment legitimately NAMES what the module does; only CODE
+        # lines may not do it.
+        block = _step_block(self.source, _W1B_STEP_NAME)
+        code_lines = "\n".join(
+            line for line in block.splitlines()
+            if not line.lstrip().startswith("#")
+        )
+        for forbidden in ("delta_allowlist", "shasum -c", "shasum -a 256"):
+            self.assertNotIn(
+                forbidden, code_lines,
+                "the W1-B step re-implements delta semantics in bash "
+                "(%r found outside comments) — the module is the only "
+                "implementation" % forbidden,
+            )
+
+    # -- ancestry covers parent AND GITHUB_SHA (r18) ----------------------
+
+    def test_ancestry_covers_reviewed_parent(self):
+        block = _step_block(self.source, _W1B_STEP_NAME)
+        self.assertIn(
+            'git merge-base --is-ancestor "$PARENT_SHA" origin/main',
+            block,
+            "the reviewed parent must be judged against origin/main "
+            "(r17: the delta alone never proves the parent was on main)",
+        )
+
+    def test_ancestry_covers_github_sha_via_head_identity(self):
+        block = _step_block(self.source, _W1B_STEP_NAME)
+        self.assertIn(
+            'if [ "$HEAD_SHA" != "${GITHUB_SHA}" ]', block,
+            "HEAD == GITHUB_SHA must be asserted so the module's "
+            "HEAD-ancestry check covers the tagged commit itself (r18)",
+        )
+
+    # -- pinned order (WaveB5 order-assert pattern) -----------------------
+
+    def test_pinned_step_order(self):
+        i_gpg = self.source.index("- name: %s" % _W1B_GPG_STEP_NAME)
+        i_verdict = self.source.index("- name: %s" % _W1B_STEP15_NAME)
+        i_gate = self.source.index("- name: %s" % _W1B_STEP_NAME)
+        self.assertLess(
+            i_gpg, i_verdict,
+            "pinned order broken: GPG verify must precede the verdict "
+            "validation",
+        )
+        self.assertLess(
+            i_verdict, i_gate,
+            "pinned order broken: the verdict validation (step 15) must "
+            "precede the delta+ancestry gate",
+        )
+
+    def test_pinned_order_inside_gate_delta_before_ancestry(self):
+        block = _step_block(self.source, _W1B_STEP_NAME)
+        self.assertLess(
+            block.index("%s delta" % _GUARD_MODULE),
+            block.index("%s ancestry" % _GUARD_MODULE),
+            "pinned order broken inside the gate: delta before ancestry",
+        )
+        self.assertLess(
+            block.index("%s ancestry" % _GUARD_MODULE),
+            block.index('git merge-base --is-ancestor "$PARENT_SHA"'),
+            "pinned order broken inside the gate: module ancestry "
+            "(fetch + HEAD) before the parent merge-base judgment — the "
+            "parent must be judged against the freshly fetched ref",
+        )
+
+    def test_gate_lives_inside_release_gate_job(self):
+        # The step must run in the same job whose success the W1-A await
+        # poller grants on — a gate in another job would not gate the
+        # publish path.
+        i_job = self.source.index("\n  release-gate:")
+        i_next_job = self.source.index("\n  publish-release:")
+        i_gate = self.source.index("- name: %s" % _W1B_STEP_NAME)
+        self.assertTrue(
+            i_job < i_gate < i_next_job,
+            "the delta+ancestry gate must be a step of the release-gate "
+            "job",
+        )
+
+
+class W1BReleaseGateJobNameTest(TestEnvContext):
+    """The exact job name `release-gate` is load-bearing (W1-A await)."""
+
+    def setUp(self):
+        super().setUp()
+        resolved = _w1b_release_text()
+        if resolved is None:
+            self.skipTest(
+                "PLAN-166 W1-B release.yml not landed and staged mirror "
+                "absent (pre-landing CI window)"
+            )
+        self.source, self.context = resolved
+
+    def test_release_gate_job_name_exact(self):
+        self.assertRegex(
+            self.source, re.compile(r"^  release-gate:$", re.MULTILINE),
+            "the job MUST keep the exact name `release-gate` — the "
+            "W1-A await-release-gate poller resolves it BY NAME via the "
+            "Actions jobs endpoint",
+        )
+
+    def test_publish_release_still_needs_release_gate(self):
+        self.assertIn(
+            "needs: release-gate", self.source,
+            "publish-release must stay gated on release-gate",
+        )
+
+
+class W1BGuardModuleContractTest(TestEnvContext):
+    """The live module surface the workflow step depends on.
+
+    These asserts pin the CONTRACT the W1-B step consumes, so a module
+    refactor that renames a subcommand or the parser is caught by the
+    suite before it bricks a release run.
+    """
+
+    def setUp(self):
+        super().setUp()
+        self.module_path = _REPO / _GUARD_MODULE
+        if not self.module_path.is_file():
+            self.fail(
+                "%s missing — the W1-B release.yml step invokes it; "
+                "landing the workflow without the module bricks every "
+                "release run" % _GUARD_MODULE
+            )
+        import importlib.util
+
+        spec = importlib.util.spec_from_file_location(
+            "release_tag_guard_w1b_contract", str(self.module_path)
+        )
+        self.mod = importlib.util.module_from_spec(spec)
+        spec.loader.exec_module(self.mod)
+
+    def test_module_exposes_the_consumed_surface(self):
+        for attr in ("_parse_verdict", "delta", "ancestry", "main"):
+            self.assertTrue(
+                hasattr(self.mod, attr),
+                "module lost %r — the W1-B workflow step consumes it"
+                % attr,
+            )
+
+    def test_parse_verdict_reads_parent_sha(self):
+        fields = self.mod._parse_verdict(
+            "# t\n\n```yaml\nparent_sha: "
+            "4111a115190d375c39c90cc33ac1d9d5899c1cf2\n```\n"
+        )
+        self.assertEqual(
+            fields.get("parent_sha"),
+            "4111a115190d375c39c90cc33ac1d9d5899c1cf2",
+        )
+
+    def test_module_exit_codes_are_distinct_nonzero(self):
+        # The workflow relies on ANY non-zero exit failing the step
+        # (set -euo pipefail); pin that the module's failure codes are
+        # non-zero and mutually distinct so the failure MODE stays
+        # testable.
+        codes = [
+            self.mod.E_USAGE, self.mod.E_FETCH, self.mod.E_NOT_ANCESTOR,
+            self.mod.E_REMOTE_REF, self.mod.E_DELTA,
+            self.mod.E_MANIFEST_PIN, self.mod.E_MANIFEST_CONTENT,
+            self.mod.E_MANIFEST_SET, self.mod.E_VERDICT, self.mod.E_VACUOUS,
+        ]
+        self.assertNotIn(0, codes)
+        self.assertEqual(len(codes), len(set(codes)))
+
+
 if __name__ == "__main__":
     unittest.main()

exec
/bin/zsh -lc "printf 'VERSION='; cat VERSION; printf 'MARKER='; cat .claude/.framework-version; printf '\\n--- trusted publisher ---\\n'; cat .claude/governance/npm-trusted-publisher.txt; printf '\\n--- pair rail template diff ---\\n'; git diff --no-ext-diff --unified=50 -- .claude/governance/pair-rail-verdict-template.md; printf '\\n--- plan manifest diff ---\\n'; git diff --no-ext-diff --unified=10 -- .claude/plans/PLAN-166/staged-manifest.sha256" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
VERSION=1.3.0
MARKER=1.3.0

--- trusted publisher ---
# npm Trusted Publisher registration — PLAN-166 W1 item 4
#
# The npmjs.com Owner console binds OIDC trusted publishing (PLAN-158
# Wave 1) to EXACTLY this triple: repository + workflow FILENAME +
# environment. If ANY of the three drifts, the token exchange dies
# ENEEDAUTH at publish time — at GA, with no earlier proof point,
# because RC tags skip the publish job. This file is the repo-side
# record of what the console must say; until it existed the triple
# lived only in comments inside npm-publish.yml and in the Owner's
# browser (F1 re-pass finding, PLAN-166).
#
# Format: `key=value` lines; `#` lines and blank lines are comments.
# Keys are exactly: repository, workflow, environment.
#
# Consumers:
# - .claude/scripts/tests/test_release_workflow_asserts.py
#   (TrustedPublisherBindingTest) READS this file and cross-checks
#   .github/workflows/npm-publish.yml — the test embeds NO values
#   (that would be a 4th copy of the truth; the copies are: the npmjs
#   console, the workflow, and this file — the test collapses the two
#   repo-side copies into one checked invariant). Includes a positive
#   control: mutating `environment:` in a copy of the workflow goes red.
# - Humans re-registering the trusted publisher after an OIDC failure:
#   .claude/plans/PLAN-158/oidc-failure-playbook.md (binding is by
#   FILENAME — playbook line 18 — which is why the publish stays in
#   npm-publish.yml instead of moving into release.yml).
#
# Update ceremony: this file matches `.claude/governance/*.txt` in
# _CANONICAL_GUARDS — edits require an Owner-signed sentinel, same as
# the workflow it describes. Change the npmjs console FIRST, then this
# file + the workflow in one ceremony; the structural test keeps the
# repo side from drifting silently.

repository=Canhada-Labs/ceo-orchestration
workflow=npm-publish.yml
environment=production-npm

--- pair rail template diff ---
diff --git a/.claude/governance/pair-rail-verdict-template.md b/.claude/governance/pair-rail-verdict-template.md
index 94296a3..fcb1865 100644
--- a/.claude/governance/pair-rail-verdict-template.md
+++ b/.claude/governance/pair-rail-verdict-template.md
@@ -1,66 +1,84 @@
 # Pair-Rail Verdict — TEMPLATE (Phase 6)
 
 Owner authors a verdict file at
 `.claude/governance/pair-rail-verdict-<release-tag>.md` BEFORE
 each `git tag <release-tag>` push. The release.yml step 15
 (`validate-pair-rail-verdict.py`) reads this file + asserts the
 verdict was signed against the same release_tag + inputs_hash the
 release run is computing.
 
 ## Required fields (validator parses YAML frontmatter)
 
 ```yaml
 verdict: GO | NO-GO | GO-WITH-CONDITIONS
 generated_at: <ISO 8601 UTC>
 ttl_hours: 24
 parent_sha: <40-char SHA — the commit the verdict was generated AGAINST (parent of the verdict-file commit). Resolves the v1.16.0 self-reference bug per S104 redesign. Compute via `git rev-parse HEAD` BEFORE creating the verdict commit.>
 # commit_sha: <DEPRECATED — kept for v1.16.0-era backward-compat. Use parent_sha for new verdicts.>
 release_tag: <e.g. v1.16.0-rc.1>
 inputs_hash: <SHA256 of canonical_json envelope of git-hash-object SHAs for ALL paths in pair-rail-inputs-hash-manifest.txt>
 inputs_hash_paths_manifest_sha: <SHA-256 of pair-rail-inputs-hash-manifest.txt itself>
+delta_allowlist:  # PLAN-166 W0 — ENFORCED by tag() (_release_tag_guard.py delta) and by the release.yml fail-closed step. CLOSED set: every path allowed to differ between parent_sha and the tag commit. Literal repo-relative paths, NO glob metacharacters. MUST include this verdict file itself, the tag's verdict-fields file at the plan dir's canonical path (verdict-fields-<TAG>.md — basename elsewhere is rejected), and the re-pass evidence files of THIS tag only.
+  - .claude/governance/pair-rail-verdict-<release-tag>.md
+  - .claude/plans/PLAN-<NNN>/verdict-fields-<release-tag>.md
+  - .claude/plans/PLAN-<NNN>/repass-<N>/<each evidence file, named one by one>
+delta_manifest: <repo-relative path of the re-pass evidence MANIFEST.sha256 — the allowlist closes by CONTENT, not just by name: the guard runs `shasum -a 256 -c` on it>
+delta_manifest_sha256: <64-hex sha256 OF the MANIFEST.sha256 file itself — pins the pin>
 tool_versions:
   codex_cli: <version, must match codex-cli-pin.txt range>
   codex_target_triple: <targetTriple of the run that generated this verdict, e.g. aarch64-apple-darwin (ADR-182 wire-shape)>
   codex_payload_sha256: <64-hex; sha256 of the NATIVE codex payload for that triple — must equal codex-cli-pin-manifest.json payloads.<triple>.sha256. Compute via `python3 .claude/hooks/check_pair_rail.py --verify-codex-pin` (the `sha256` field). NOT the hash of `which codex` (that is the npm JS launcher).>
   # codex_cli_binary_sha256: <DEPRECATED (ADR-182) — launcher-hash pin, pre-ADR-182 tags only. The pin file is now a comment-only tombstone; do not declare this field in new verdicts.>
   claude_code: <version>
   python: <e.g. 3.9.6>
 transcript_hash: <SHA-256 of session transcript that produced this verdict>
 findings: []  # List of P0/P1/P2/P3 with file:line if any
 gpg_signature: <armored GPG signature of the above fields>
 ```
 
+## tag() guard semantics (PLAN-166 W0 — local AND server-side)
+
+- `delta_allowlist` / `delta_manifest` / `delta_manifest_sha256` are
+  REQUIRED for every new verdict (RC and stable). `tag()` refuses to
+  sign when `git diff <parent_sha>..HEAD --name-only` contains any path
+  outside the allowlist, when the allowlist carries a glob
+  metacharacter or another tag's artifacts, when the parent_sha is not
+  an ancestor of HEAD (E_PARENT_NOT_ANCESTOR=12), or when
+  `shasum -a 256 -c <delta_manifest>` fails. The same asserts run
+  server-side in release.yml, independent of
+  CEO_PAIR_RAIL_VERDICT_OPTIONAL (fail-closed step).
+
 ## Validator semantics
 
 - `--parent-sha $PARENT_SHA` arg MUST equal the verdict's
   `parent_sha` (S104 redesign — replaces the unsolvable
   `commit_sha` self-reference). The release.yml step 15
   resolves PARENT_SHA via `git log -n1 --format=%H -- <verdict-file>^`.
   Mismatch → exit `VERDICT_INVALID` (3).
 - `--release-tag $RELEASE_TAG` arg MUST equal the verdict's
   `release_tag` (R1 S-Sec-3 replay defense — exit non-zero on
   mismatch).
 - `--max-age-hours 24`: assert `now - generated_at < ttl_hours`.
   Beyond TTL → distinct exit code `VERDICT_EXPIRED` (NOT infra
   error; release.yml routes appropriately per R1 S-QA-Unseen-2).
 - `--codex-cli-pin-file`: assert `tool_versions.codex_cli` in pin
   range (R1 C5 enforcement).
 - `--codex-pin-manifest-file`: assert
   `tool_versions.codex_payload_sha256` equals
   `payloads[tool_versions.codex_target_triple].sha256` in
   `codex-cli-pin-manifest.json` (ADR-182 payload pin). Missing
   fields, triple absent from the manifest, or sha mismatch → exit
   `VERDICT_INVALID` (3), fail-CLOSED.
 - `--inputs-hash-paths-file`: read manifest + recompute
   `inputs_hash` via git hash-object + canonical_json (R1 S-Sec-4).
   Mismatch → exit non-zero.
 
 ## Phase 6 ship scope
 
 The TEMPLATE is shipped. Per-release verdict instances are authored
 by Owner BEFORE each tag push. The release.yml step 15 is wired
 with `continue-on-error: true` only when
 `CEO_PAIR_RAIL_VERDICT_OPTIONAL=1` (transition mode for v1.16.0-rc.1).
 
 For v1.16.0 GA tag, `CEO_PAIR_RAIL_VERDICT_OPTIONAL` is unset →
 verdict file MUST be present + valid.

--- plan manifest diff ---
diff --git a/.claude/plans/PLAN-166/staged-manifest.sha256 b/.claude/plans/PLAN-166/staged-manifest.sha256
index c1d4d0d..e77ebf6 100644
--- a/.claude/plans/PLAN-166/staged-manifest.sha256
+++ b/.claude/plans/PLAN-166/staged-manifest.sha256
@@ -1,32 +1,34 @@
 64d23f858ef51b0f996e4966d4e27c0371b437e2d2787890b1f7ad22d4ec5663  .claude/plans/PLAN-166/staged/.claude/.framework-version
 3c64b45a627bc4c1a5c9bf9c4e26eff793c0e4c92250bdd307ad267b1576a8af  .claude/plans/PLAN-166/staged/.claude/adr/ADR-155-AMEND-1-delivery-record-ownership.md
 df7be2195cf197dfd881c5a18a3811132d20824cf3b935f1d084aef18b5f7692  .claude/plans/PLAN-166/staged/.claude/governance/npm-trusted-publisher.txt
 d79d36ad28ea73f06d28a8b22ffeecf01ad8286647383f3cef1f96f802b564a8  .claude/plans/PLAN-166/staged/.claude/governance/pair-rail-verdict-template.md
-198dcec214dbb4def43be626eae5a6a74b540a00dad4872e5a601216541bf5f6  .claude/plans/PLAN-166/staged/.claude/scripts/check-framework-updates.sh
+ac84cd8194549f42394a7f2ac45786bc537391f27b67dde33c4c4b4c1bb0cefd  .claude/plans/PLAN-166/staged/.claude/scripts/check-framework-updates.sh
 8589420213deb0970b267f15690c33acca31f42363b4b3464d3281d752a9a365  .claude/plans/PLAN-166/staged/.claude/scripts/tests/test_release_workflow_asserts.py
 3ddd855970f8f4b337ba16810f85fdd4d61cc559bf6da4243e39721535d46d1c  .claude/plans/PLAN-166/staged/.github/workflows/npm-publish.yml
 bf24d80621d24104c7e387efe64d7e9284ec4f1dc1fb875dc085618d24005162  .claude/plans/PLAN-166/staged/.github/workflows/release.yml
-4548a87b15b51aafa5f731c2168810ba6ee4561b576d2c3e6061ba8d2715ffcd  .claude/plans/PLAN-166/staged/.github/workflows/smoke-install.yml
+eaa0f3c9c3d70f96c81777d92dece0ffecd91f2a07ac8db217b5c269b7550d4a  .claude/plans/PLAN-166/staged/.github/workflows/smoke-install.yml
 4935a60cb1227449a6a22bb913fb14c6ca76219bb603a9a031f3802e0f022d88  .claude/plans/PLAN-166/staged/INSTALL.md
 813ffe5198eeac04f982023da1592210ac70682d8ccc2d6ef4e6b2dd24a5ac9c  .claude/plans/PLAN-166/staged/notes-w1b-kernel-override.md
 61464f7a7cec04ecaa959904319c516a405ee9a98442383e596cea09e6c7cedf  .claude/plans/PLAN-166/staged/notes-w1c-f3.md
 9a3b22f45cfa944aaddfb1ae6073a847f8abf39296ffc5eb47fa52accbfdbd47  .claude/plans/PLAN-166/staged/patches/f3-adr-155-amend-1.patch
-fa68c9eccd57031969e9976a35b0f118e573795c8b661d042317bab0d9235b92  .claude/plans/PLAN-166/staged/patches/f3-check-framework-updates-marker-first.patch
+7af7cf6a6c46a32042cb73f0761277e8ddd8869d5b596278e63013dfc6c435d9  .claude/plans/PLAN-166/staged/patches/f3-check-framework-updates-marker-first.patch
 55af1b44196627f85e14bfdea023205900db74fe4c7e8884f8364bc3dfe14426  .claude/plans/PLAN-166/staged/patches/f3-doctor-delivery-flags.patch
-7ed64e92a6f541f58499b560249f012bc712e34e7e5e73baba3f04f36fec58dd  .claude/plans/PLAN-166/staged/patches/f3-fms-conditional-entries.patch
+9d3e40a2f97f0a238dcd8d49dfea4f78bc0dbc309311b34bf0212cc9ad05c3af  .claude/plans/PLAN-166/staged/patches/f3-fms-conditional-entries.patch
 f340d81741e7cde417ea11463e56e7cbbd9f04b9227908b5c455eebedbc3f4d4  .claude/plans/PLAN-166/staged/patches/f3-framework-version-marker.patch
-c9c71fc42ad22c1b56b190641c4489758571b590999a10c19d7ae0bfc8be9713  .claude/plans/PLAN-166/staged/patches/f3-install-delivery-record.patch
+e0acdbb60a0e0a60f53dd495dd535371f2a24d54de8c3fdba2c0b484299dc192  .claude/plans/PLAN-166/staged/patches/f3-install-delivery-record.patch
 01c5627b5b449820d2fbf2f33ed020f30b8ea094afe9474fd7b1cf8d35abfed8  .claude/plans/PLAN-166/staged/patches/f3-install-md-consequences.patch
 3c027435e5df55dc39e66aa1e5c0fbef1b17f21553e07c64bca0606eb534a29b  .claude/plans/PLAN-166/staged/patches/f3-test-upgrade-spec-ownership.patch
-8240fc2f083a64e34690b6760c04489488f4a53ccba86e397a6c0a14579b6e92  .claude/plans/PLAN-166/staged/patches/f3-upgrade-spec-forced-refresh.patch
+0c67bdcdb267388bd60c9143bf6203495de14ebb562720feaeb37719d26fb8e9  .claude/plans/PLAN-166/staged/patches/f3-upgrade-spec-forced-refresh.patch
 a83d8bc2353054d816342978962127e99cbc432c5e0ab8c1b4fe2a2365cfea2d  .claude/plans/PLAN-166/staged/patches/release-yml-verdict-delta-ancestry.patch
-d51a5299e3d17126283b5fe0412bee7fad14f604c1543ab7315130375d207c99  .claude/plans/PLAN-166/staged/patches/smoke-install-parity-e2e-wiring.patch
+bf52d60642eb3392cd286db16a8c0d57036c394b117d2654fb7c0e9955873632  .claude/plans/PLAN-166/staged/patches/smoke-install-parity-e2e-wiring.patch
 c3558235089ae461d4597e203a4c1466a0ca9d3c8b0805b5cffbecc48b6d355d  .claude/plans/PLAN-166/staged/patches/w0-verdict-template-delta-fields.patch
+947bff3ff3e2b2c990abc59dd101a27f75065b97476f9814f62ee70c7e4fd88a  .claude/plans/PLAN-166/staged/patches/w1-parity-classify-known-open-purge.patch
 2903e84dc079c45c085bafca751a20c99d3f199b2001ab6f96b4d04cd7e7307a  .claude/plans/PLAN-166/staged/patches/w1a-npm-publish-await-gate.patch
 7a90547a50be440563e91603e921e51acbec10fa6942f9e25fa1635dd997d4c9  .claude/plans/PLAN-166/staged/patches/w1a-npm-trusted-publisher-txt.patch
 f0d1489af60ef3d1d0c2ac236525d6f827686fc140cd23a282236137b036c440  .claude/plans/PLAN-166/staged/patches/w1a-release-workflow-asserts.patch
-29998d78fb6363c6dd1450435bc57f38d45e52cb8e016651f40a8a71636d1509  .claude/plans/PLAN-166/staged/scripts/_framework_manifest_set.sh
+efe81bd8a6e22073cd701279efb2572f379e513bd5f4456a194d49e00dd54c56  .claude/plans/PLAN-166/staged/scripts/_framework_manifest_set.sh
 c01160165c561e7ae0bb05315b36a187ea4c76d0c4d442426524300a6f14d02e  .claude/plans/PLAN-166/staged/scripts/doctor.sh
-e1926bd826d23043b2eeb3e812ab4ff55ecaea7cf4f18efbc036c2407db8c267  .claude/plans/PLAN-166/staged/scripts/install.sh
+1812463fe152f9c9656e297f73b5248b3916aa54e6e3857bc33fba6e3b40eb31  .claude/plans/PLAN-166/staged/scripts/install.sh
+d8d706554018b5ea326331bd0e66a3924295df2ced0de4f7f89439ce7304e66a  .claude/plans/PLAN-166/staged/scripts/tests/_parity_classify.py
 5dbe355071c072cd3e5d78a9155cb6ef3cb4f9636a11cc797116542c47d00f38  .claude/plans/PLAN-166/staged/scripts/tests/test-upgrade-spec-ownership.sh
-3531a61f3dc0a6f96cec14ad6b591681b3856b8745f4d62e34bab5d7432c01b7  .claude/plans/PLAN-166/staged/scripts/upgrade.sh
+886429851f7b6480846e4aee0511036762edda0864b37aed9cbec73ad7a1ad4b  .claude/plans/PLAN-166/staged/scripts/upgrade.sh

exec
/bin/zsh -lc "git diff --no-ext-diff --unified=0 -- '*.md' '*.txt' | grep '"'^+'"' | grep -viE '"'^'"\\+\\+\\+|speed|throughput|faster|x faster|performance' || true; printf '\\n--- added claim scan ---\\n'; git diff --no-ext-diff --unified=0 -- '*.md' '*.txt' | grep '"'^+'"' | grep -iE 'speed|throughput|faster|performance|[0-9]+x' || true" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
+# ADR-155-AMEND-1 — Framework ownership derives from the REGISTERED DELIVERY; SPEC/v1 joins the upgrade surface (forced route); root VERSION stays out — deliberately
+
+
+---
+adr_id: ADR-155-AMEND-1
+title: Install/upgrade ownership model — every conditional framework-owned entry (PROTOCOL.md, SPEC/v1, .claude/.framework-version) derives from the registered delivery record, never from ceremony alone or file presence; SPEC/v1 gets a FORCED refresh route with pristine-content legacy migration; the root VERSION is exempt from upgrade forever
+status: ACCEPTED
+amends: ADR-155
+proposed_at: 2026-08-05
+proposed_by: CEO (PLAN-166 F3 — ADR-103 re-pass NO-GO finding on v1.3.0-rc.1; debate rounds r6/r7/r8/r9/r13/r17/r19/r20)
+session_origin: 2026-08-05 (S295, W1 ceremony pack)
+accepted_at: 2026-08-05
+authorization: PLAN-166 W1 Owner-GPG ceremony — this file reaches the canonical tree ONLY via that ceremony; a landed copy implies the gate fired
+risk_tier: A
+debate_required: true
+debate_record: .claude/plans/PLAN-166/debate/ (3 rounds, 3 scoped VETOs raised and LIFTED with literal verification) + codex pair-rail 20 rounds (~55 findings applied)
+related_plans: [PLAN-138, PLAN-153, PLAN-161, PLAN-166]
+related_adrs: [ADR-155]
+---
+
+## §1 What this amendment changes
+
+ADR-155 built the baseline-manifest engine on one shared enumeration
+(`scripts/_framework_manifest_set.sh`) and enumerated the root
+`PROTOCOL.md` **unconditionally** (decision (i)). The v1.3.0-rc.1 re-pass
+(PLAN-166 finding F3) showed that unconditional — or ceremony-only —
+enumeration is itself an ownership defect, and that `SPEC/v1` (shipped by
+`install.sh` since PLAN-087 but never enumerated, never refreshed) had
+become a stale, unwatched contract on every upgraded adopter. This
+amendment decides four things:
+
+1. **The delivery-record ownership rule (general).** Every CONDITIONAL
+   entry of the framework-owned enumeration — `PROTOCOL.md`, `SPEC/v1`
+   and the new `.claude/.framework-version` marker — derives from the
+   **registered delivery**, never from the ceremony alone and never from
+   file presence (§3).
+2. **`SPEC/v1` joins the upgrade surface via a FORCED route** — not the
+   generic `backup_and_replace` classified walk — with a deterministic
+   pristine-content migration for v1.2-and-earlier legacy installs (§4).
+3. **`.claude/.framework-version`** becomes a tracked file of the
+   framework repo, written explicitly on install (`install_one`,
+   skip-if-exists) and force-refreshed + read-back-validated on upgrade;
+   marker-first readers consult the SAME delivery record before trusting
+   it (§5).
+4. **The root `VERSION` file stays OUT of the upgrade surface and OUT of
+   the enumeration — permanently and deliberately** (§2). This section
+   exists so the next maintainer does not "fix" the asymmetry and reopen
+   the class.
+
+## §2 Why root VERSION is exempt — do not repair this asymmetry
+
+`install.sh`'s `install_one` is **skip-if-exists**: on an adopter repo
+that already carries its own `VERSION` (most real repos version
+themselves), the framework **never wrote that file**. Any upgrade-side
+refresh of `VERSION` — `backup_and_replace` or a forced route — would
+therefore TAKE an adopter-owned file. That is not hypothetical: it is the
+exact shape of the S238 acme data-loss ("the verified worst case" in
+ADR-155's own words), and the baseline classifier would *confirm* the
+clobber rather than prevent it, because the recorded baseline would hash
+the framework's value (trap C.5, documented inside
+`_framework_manifest_set.sh`).
+
+So the asymmetry is: **every other framework-derived surface refreshes on
+upgrade; `VERSION` does not, ever.** The consequence — the root `VERSION`
+of an upgraded adopter reports the ORIGINAL install version forever — is
+absorbed by the marker (§5) and named in `INSTALL.md` (the forensic-anchor
+section now prefers `.claude/.framework-version` with a `VERSION`
+fallback). A future maintainer who notices "upgrade refreshes the marker
+but not VERSION — inconsistent!" is looking at a decided invariant, not an
+oversight. Reopening it requires amending THIS amendment.
+
+Inside the framework repo itself nothing changes: every framework-repo
+gate (`check-canonical-doc-freshness.py`, `verify-counts.sh`,
+`check_tier_a_spec_version_drift`) keeps reading `VERSION` as the
+authority. The marker-first preference is exclusive to readers operating
+on an ADOPTER tree — today, `.claude/scripts/check-framework-updates.sh`
+(without it, the checker re-reads the stale root `VERSION` post-upgrade,
+exits `behind-minor` and demands the same upgrade in an eternal loop —
+r8). `check_tier_a_npm_version_match` deliberately does NOT adopt the
+marker: in an adopter tree the root `package.json` is the APP's, and
+comparing the framework marker against the app version would be a
+permanent false-red; that check keeps its VERSION×package.json semantics
+(or skips when VERSION is absent).
+
+## §3 The delivery-record ownership rule
+
+**"Delivered" means REGISTERED ACTUAL DELIVERY, not ceremony (r17), and
+not file presence (r7/r13):**
+
+- A `--ceremony user` install SKIPS `install_spec_v1`,
+  `install_version` and `install_protocol_pointer` (WS4 guards). If the
+  enumeration emitted those paths unconditionally,
+  `write_install_manifest` would hash the ADOPTER's own `SPEC/v1` or root
+  `PROTOCOL.md` as framework-owned — and a later `uninstall.sh` (which
+  removes manifest-recorded, hash-matching files) could DELETE the
+  adopter's files (r7/r13).
+- Ceremony-conditional enumeration is still not enough: on a
+  `maintainer` install where the destination ALREADY had its own
+  `SPEC/v1`, `install_one` EXISTS-skips — the file on disk is the
+  adopter's, under a maintainer ceremony (r17).
+
+Mechanics (both writers, one reader):
+
+- `install.sh` flips `_DELIVERED_{SPEC,PROTOCOL,MARKER}` only where the
+  write ACTUALLY happened (`install_one` reports COPIED/LINKED via
+  `INSTALL_ONE_WROTE`; the pointer heredoc sets the flag on its own write
+  path, unreachable from the pre-existing early-return), journals a
+  `delivered_*` op into `.install-state.json`, and exports the flags as
+  `FMS_DELIVERED_*` to the shared enumeration.
+- The **baseline manifest** (`.claude/.install-manifest.sha256`) is
+  thereby the persistent delivery record: it carries records for the
+  three conditional paths **iff** they were delivered.
+- `upgrade.sh` resolves prior ownership from the pre-upgrade baseline
+  records (`_baseline_has_spec_record` / `_baseline_has_marker_record` /
+  the existing `_baseline_lookup "PROTOCOL.md"`), refreshes what it owns,
+  and re-exports the flags for the post-upgrade C.7 rewrite.
+- `doctor.sh` resolves the SAME flags from the sanitized baseline —
+  never from ceremony — before its orphan-scan enumeration: only-ceremony
+  would re-include paths a user install skipped and `--strict-orphans`
+  would flag the adopter's own files as orphans (r19); a blanket
+  maintainer default would do the same, and a blanket user default would
+  hide a delivered SPEC from a maintainer (r9 P2).
+- The enumeration's fail direction is pinned: an unset flag means NOT
+  enumerated. **Under-claiming ownership is recoverable (a file goes
+  unwatched); over-claiming is the delete-the-adopter's-file class.**
+
+The upgrade-side ceremony read is **replay-independent** (r9):
+`upgrade.sh --no-replay` sets `REPLAY=0` and skips
+`_read_install_state_request` entirely, so a ceremony that rode the
+replay would silently revert a user install to maintainer under the
+documented `--no-replay` flag. A dedicated `_read_install_state_ceremony`
+reader always runs, validates against the closed enum
+`{maintainer, user}`, and **fails open to `maintainer`** when the state
+is absent/unreadable (all pre-Wave-B installs) — the pre-existing
+behavior, named as a consequence in `INSTALL.md`. The same read gates
+`_refresh_protocol_pointer`, which previously ran unconditionally and
+`cat >`-created a root `PROTOCOL.md` that a user install deliberately
+never has (the latent bug the PLAN-166 F4 tree-comparison e2e exposes).
+
+## §4 SPEC/v1: forced route + pristine-content legacy migration
+
+The generic route cannot carry the SPEC. For a directory target with a
+baseline, `backup_and_replace` runs the per-file classified walk — which
+PRESERVES adopter edits. From the **second** upgrade on (baseline then
+contains SPEC records), an edited SPEC would classify ADOPTER-CUSTOMIZED
+and the stale-contract failure would return (r6). The declared semantics
+(OQ-3): `SPEC/v1` is the published compliance CONTRACT — an adopter edit
+is a **fork of the contract**, not a customization. Three-way merge is
+complexity without a consumer; refuse-and-instruct would block every
+upgrade that ships a SPEC change. Hence `_refresh_spec_contract`:
+framework-owned ⇒ backup whole tree to `.claude.bak/<ts>/SPEC/v1` +
+replace wholesale; user-ceremony installs never receive it.
+
+**Legacy migration (r20).** v1.2-and-earlier installs have NO delivery
+record for SPEC (the enumeration never included it), so
+framework-installed and adopter-authored `SPEC/v1` are indistinguishable
+by record. The ambiguity resolves by CONTENT: the target tree's
+fingerprint (sha256 over the `LC_ALL=C`-sorted `"<sha256(file)>  <relpath>"`
+lines of every file under `SPEC/v1`) is compared against the PRISTINE
+fingerprints of every SPEC/v1 the framework shipped at **v1.2.0 and
+earlier** — nine tags, three distinct trees, derived deterministically
+from pinned tag content (`git ls-tree` + `git show`; the derivation
+command is embedded next to the constants in `upgrade.sh`):
+
+| pristine fingerprint (sha256) | shipped by |
+|---|---|
+| `a4a4504a224d72a975a853dd71a75d8e678fef034a70deb49df291dbb712c161` | v1.0.0, v1.0.1, v1.0.1-rc.1 |
+| `94aa62f781285ce4897ad1220edf15e97b4e9d7b629f9f7ba3389da5d45f22b1` | v1.1.0, v1.1.0-rc.1 |
+| `469a49238867be181490214305b43bc7299f2bae3ef0b282a5452f6caf327f0b` | v1.2.0, v1.2.0-rc.1, v1.2.0-rc.2, v1.2.0-rc.3 |
+
+Match ⇒ framework-owned (byte-identical to a shipped release; the forced
+refresh loses nothing) ⇒ refresh + named NOTE. No match ⇒ ADOPTER-FORK ⇒
+**preserve in place** + snapshot to `.claude.bak/<ts>/SPEC/v1` + named
+WARNING with the hand-refresh instruction. A partial/unhashable tree
+never produces a fingerprint (fail toward preserve). Both legacy cases
+are fixtures; the pristine-match branch is additionally exercised
+end-to-end by the F4 install-v1.2.0→upgrade comparison job.
+
+## §5 The marker: forced+validated write, record-gated readers
+
+`.claude/.framework-version` is a **tracked file of the framework repo**
+(one line, byte-identical to `VERSION`) — not generated-only-at-destination,
+so the release protections are real and unconditional: the version bump
+writes it as its 12th site, `verify-counts.sh` cross-checks it against
+`VERSION` in every release, and `release.yml` asserts marker == VERSION
+fail-closed. In the enumeration it is a NORMAL file entry (the
+`FMS_HASH_ROOT` baseline rewrite preserves it with no special-case),
+conditional on delivery like the other two.
+
+Delivery is by **explicit writes on both paths** (the enumeration never
+delivers — it only records; r7): `install_one ".claude/.framework-version"`
+on install (skip-if-exists ⇒ a pre-existing adopter marker is NOT
+delivered), and a **forced + read-back-validated** rewrite on upgrade
+(differing pre-existing copy backed up first; a write that fails
+validation is NOT recorded as delivered). It lives inside `.claude/`, so
+both ceremonies receive it (the WS4 guard only forbids root files) and it
+is committable like the rest of `.claude/`.
+
+**Every marker-first reader consults the SAME record** (r20):
+`check-framework-updates.sh` trusts the marker only when the baseline
+manifest carries its delivery record, else falls back to `VERSION` — on a
+target where the marker pre-existed and was skipped, an unconditional
+read would report a stale version in a loop.
+
+## §6 Enforcement
+
+- `scripts/tests/test-upgrade-spec-ownership.sh` — record-owned forced
+  refresh with backup (the 2nd-upgrade scenario), user-ceremony +
+  `--no-replay` skip, legacy adopter-fork preserve, marker delivery +
+  pre-existing-marker fallback, doctor orphan-scan in both modes,
+  update-checker no-loop regression (AC-3).
+- The PLAN-166 F4 e2e (`smoke-install.yml`) compares install-built vs
+  upgrade-built trees per ceremony mode; its historical leg
+  (install v1.2.0 → upgrade) exercises the pristine-match migration.
+- `_framework_manifest_set.sh`, `install.sh`, `upgrade.sh` remain
+  `_CANONICAL_GUARDS` surfaces; this amendment's edits land only via the
+  PLAN-166 W1 Owner-GPG ceremony.
+
+## Consequences
+
+- **(+)** A `--ceremony user` install can never have its own `SPEC/v1`,
+  root `PROTOCOL.md` or marker inventoried as framework-owned — closing
+  the uninstall-deletes-adopter-files corridor (r7/r13/r17).
+- **(+)** Upgraded adopters get a fresh SPEC contract every upgrade, with
+  fork preservation and a deterministic legacy migration.
+- **(+)** Post-upgrade version reporting is truthful (marker), without
+  ever touching the adopter's root `VERSION`.
+- **(−)** Pre-Wave-B installs (no `.install-state.json`) are treated as
+  `maintainer` on upgrade — fail-open, named in `INSTALL.md`; a user-mode
+  pre-Wave-B adopter must re-run `install.sh --ceremony user` once to
+  record the ceremony.
+- **(−)** The delivery record inherits the baseline manifest's trust
+  class: target-side, UNSIGNED, advisory (ADR-155 Consequences). A
+  tampered record can add/remove ownership — the fail direction on a
+  MISSING record is preserve/fallback (today's behavior), never a new
+  escalation.
+- **(~)** An adopter whose fork of `SPEC/v1` is byte-identical to a
+  shipped release is claimed as framework-owned by the legacy migration —
+  accepted: the forced refresh is content-preserving up to the shipped
+  bytes they already had.
+# npm Trusted Publisher registration — PLAN-166 W1 item 4
+#
+# The npmjs.com Owner console binds OIDC trusted publishing (PLAN-158
+# Wave 1) to EXACTLY this triple: repository + workflow FILENAME +
+# environment. If ANY of the three drifts, the token exchange dies
+# ENEEDAUTH at publish time — at GA, with no earlier proof point,
+# because RC tags skip the publish job. This file is the repo-side
+# record of what the console must say; until it existed the triple
+# lived only in comments inside npm-publish.yml and in the Owner's
+# browser (F1 re-pass finding, PLAN-166).
+#
+# Format: `key=value` lines; `#` lines and blank lines are comments.
+# Keys are exactly: repository, workflow, environment.
+#
+# Consumers:
+# - .claude/scripts/tests/test_release_workflow_asserts.py
+#   (TrustedPublisherBindingTest) READS this file and cross-checks
+#   .github/workflows/npm-publish.yml — the test embeds NO values
+#   (that would be a 4th copy of the truth; the copies are: the npmjs
+#   console, the workflow, and this file — the test collapses the two
+#   repo-side copies into one checked invariant). Includes a positive
+#   control: mutating `environment:` in a copy of the workflow goes red.
+# - Humans re-registering the trusted publisher after an OIDC failure:
+#   .claude/plans/PLAN-158/oidc-failure-playbook.md (binding is by
+#   FILENAME — playbook line 18 — which is why the publish stays in
+#   npm-publish.yml instead of moving into release.yml).
+#
+# Update ceremony: this file matches `.claude/governance/*.txt` in
+# _CANONICAL_GUARDS — edits require an Owner-signed sentinel, same as
+# the workflow it describes. Change the npmjs console FIRST, then this
+# file + the workflow in one ceremony; the structural test keeps the
+# repo side from drifting silently.
+
+repository=Canhada-Labs/ceo-orchestration
+workflow=npm-publish.yml
+environment=production-npm
+delta_allowlist:  # PLAN-166 W0 — ENFORCED by tag() (_release_tag_guard.py delta) and by the release.yml fail-closed step. CLOSED set: every path allowed to differ between parent_sha and the tag commit. Literal repo-relative paths, NO glob metacharacters. MUST include this verdict file itself, the tag's verdict-fields file at the plan dir's canonical path (verdict-fields-<TAG>.md — basename elsewhere is rejected), and the re-pass evidence files of THIS tag only.
+  - .claude/governance/pair-rail-verdict-<release-tag>.md
+  - .claude/plans/PLAN-<NNN>/verdict-fields-<release-tag>.md
+  - .claude/plans/PLAN-<NNN>/repass-<N>/<each evidence file, named one by one>
+delta_manifest: <repo-relative path of the re-pass evidence MANIFEST.sha256 — the allowlist closes by CONTENT, not just by name: the guard runs `shasum -a 256 -c` on it>
+delta_manifest_sha256: <64-hex sha256 OF the MANIFEST.sha256 file itself — pins the pin>
+## tag() guard semantics (PLAN-166 W0 — local AND server-side)
+
+- `delta_allowlist` / `delta_manifest` / `delta_manifest_sha256` are
+  REQUIRED for every new verdict (RC and stable). `tag()` refuses to
+  sign when `git diff <parent_sha>..HEAD --name-only` contains any path
+  outside the allowlist, when the allowlist carries a glob
+  metacharacter or another tag's artifacts, when the parent_sha is not
+  an ancestor of HEAD (E_PARENT_NOT_ANCESTOR=12), or when
+  `shasum -a 256 -c <delta_manifest>` fails. The same asserts run
+  server-side in release.yml, independent of
+  CEO_PAIR_RAIL_VERDICT_OPTIONAL (fail-closed step).
+
+  - scripts/tests/_parity_classify.py
+---
+plan: PLAN-166
+round: 1
+type: architect-sentinel
+segment: W1-FINDINGS-CLOSURE
+---
+
+# PLAN-166 W1 — release-hold findings-closure ceremony (Owner sentinel)
+
+Anchor-SHA: 05e4845060f16d5b5bbce0fe1eea792a14118ed0
+
+Approved-By: @Canhada-Labs (Owner GPG — signed inline by the ceremony)
+Approved-At: 2026-08-07
+
+## What this sentinel authorizes (sign this KNOWINGLY)
+
+Single declared PLAN-166 W1 ceremony (plan `reviewed` at `92c8c3c`; debate
+3 rounds with 3 scoped VETOs raised-and-lifted + codex rail 20 rounds; the
+re-pass of rc.1 was NO-GO with 6 findings and the Owner mandated closing
+ALL of them — this commit is the canonical half of that closure; W0 free
+surfaces land separately). One commit, two REVERT GROUPS (the Scope below
+is grouped so either half can be reverted without splitting the ceremony
+— with ONE deliberate coupling, sign it knowingly: release.yml (group A)
+carries the UNCONDITIONAL `.claude/.framework-version == VERSION` assert
+while the marker file itself is in group B, so reverting ONLY group B
+leaves every tag run red until release.yml is re-edited, which means a
+NEW kernel-override route. The failure direction is CLOSED — it blocks a
+ship, never publishes — but the operational cost of a partial group-B
+revert is a second ceremony):
+
+**Group A — release train (F1 + F2 server side + item 4):**
+
+1. `npm-publish.yml` gains the `await-release-gate` job (fail-closed
+   poller over release.yml's `release-gate` job via
+   `.claude/scripts/await_release_gate.py`, timeout-minutes 35, GH_TOKEN
+   at job level, NO environment / NO RC exclusion — RC tags are the live
+   positive control) + `needs: await-release-gate` on `publish`. Posture
+   pins STRENGTHENED, not relocated: `environment: production-npm` and
+   the `-rc.` exclusion stay VERBATIM on the publish job.
+2. `release.yml` gains (i) the verdict delta + ancestry gate step
+   (delegates to `.claude/scripts/local/_release_tag_guard.py`; no
+   continue-on-error; fails CLOSED on `CEO_PAIR_RAIL_VERDICT_OPTIONAL=1`;
+   ancestry covers the reviewed parent AND `GITHUB_SHA`, r15+r17+r18) and
+   (ii) the UNCONDITIONAL `.claude/.framework-version == VERSION` assert
+   (Forma A (ii), next to the VERSION↔tag asserts).
+3. `.claude/governance/npm-trusted-publisher.txt` — the npmjs OIDC
+   trusted-publisher triple (repository / workflow FILENAME /
+   environment) as a tracked record.
+4. `test_release_workflow_asserts.py` — structural asserts for 1-3
+   (await-gate pins, W1B delta+ancestry pins merged in by the assembler,
+   trusted-publisher binding asserts that READ the txt, with positive
+   controls).
+5. `RELEASE.md` — derived step count in the release.yml pointer block
+   29 → 31 (item 2 adds two named steps to release-gate; the
+   `verify-counts.sh` release_steps rule is exact/tolerance-0 and scans
+   RELEASE.md, so WITHOUT this edit the ceremony's own §6(d) gate goes
+   red post-apply and forces an out-of-scope fix mid-ceremony).
+
+**Group B — adopter upgrade (F3 + F4 + ADR-155-AMEND-1):**
+
+6. `ADR-155-AMEND-1-delivery-record-ownership.md` — delivery-record
+   ownership of the three conditional surfaces (SPEC/v1, root
+   PROTOCOL.md, `.claude/.framework-version`); ADR file count 188 → 189.
+7. `.claude/.framework-version` — NEW tracked one-line marker,
+   byte-identical to VERSION (1.3.0).
+8. `install.sh` / `upgrade.sh` / `_framework_manifest_set.sh` /
+   `doctor.sh` / `check-framework-updates.sh` — explicit delivery writes
+   + record-gated readers + forced/validated marker refresh + SPEC
+   forced-refresh with pristine-fingerprint legacy migration (v1.0.0..
+   v1.2.0-rc.3 set; ADOPTER-FORK preserved in place). The SPEC
+   delivery-record readers (`upgrade.sh _baseline_has_spec_record`,
+   `doctor.sh _dr_delivered`) match `SPEC/v1(/|  |$)` — a --mode link
+   install records the tree as ONE `LINK  SPEC/v1  <target>` line, no
+   trailing slash (re-pass closure; family swept).
+9. `smoke-install.yml` — wires the F4 parity e2e (+ LOAD-BEARING
+   positive control: rc==1 AND plant evidence greped from the log, else
+   red) AND the F3 spec-ownership e2e (S1-S8) into CI, path filters
+   re-synced between pull_request and push, timeout-minutes 8 → 25.
+   **Explicit plan deviation, ratified by this signature:** PLAN-166 W1
+   item 3 says "8→~15"; the staged value is 25, from MEASURED wall time
+   (F4: 122s gate + 118s control local, 2-3x CI factor; F3 e2e adds
+   ~3-4 min local) + the PLAN-159 N=20-flake lesson — 15 sits inside
+   the noise band. Signing this sentinel ratifies 25 KNOWINGLY, not by
+   silence; re-tighten once real CI runs give a p95.
+10. `scripts/tests/test-upgrade-spec-ownership.sh` — NEW e2e (S1-S8).
+11. `INSTALL.md` — post-upgrade verify instructions prefer the marker;
+    delivery-record consequences documented.
+12. ADR-count sweep 188 → 189 in the SAME commit, sites derived from the
+    `verify-counts.sh` matchers themselves (12 matcher-reachable
+    occurrences across 8 docs — the W1-C census note says "9 docs";
+    recount at land time from the gate, not from either number): the
+    docs listed in Group B below. `docs/ARCHITECTURE.md:56` and `:237`
+    are NOT matcher-reachable but sit in an already-touched file and are
+    updated in the same pass. Same treatment for the TWO
+    matcher-INVISIBLE ADR-count claims in `docs/GUIA-COMPLETO.md`
+    (":167 `188 ADRs document every architectural decision`" and
+    ":1225 `— 188 Architecture Decision Records`") — GUIA is in the
+    gate's DOCS but neither phrasing is reachable by any matcher, so
+    left alone they would silently claim 188 with 189 on disk (the
+    exact [[feedback-adr-count-drift-unwatched-docs]] class W0/F5 just
+    closed elsewhere); swept in §4 of the runbook, file added to this
+    Scope. The 189 in `verify-counts.sh` is DERIVED (file count), not a
+    typed constant — no edit to it for the count.
+
+**Kernel-override route (release.yml ONLY):** `release.yml` is canonical
+AND an exact `_KERNEL_PATHS` entry (`check_arbitration_kernel.py:134`).
+Its apply runs under the PER-CEREMONY pair
+`CEO_KERNEL_OVERRIDE=PLAN-166-W1-RELEASE-YML-AWAIT-GATE` +
+`CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT`, armed inline immediately before the
+apply and disarmed immediately after (never exported in
+settings.local.json or shell profile). The audit-ledger event
+(`plan_id` truncated to `PLAN-166-W1-RELEASE-YML-AWAIT-GA`, 32 chars) is
+the proof artifact — see `staged/notes-w1b-kernel-override.md` and the
+land runbook. Editing release.yml is literally the "CI gate bypass"
+vector the kernel exists to impede; the privilege stays armed only for
+the duration of the signature window.
+
+**Conditional entries (OWNER-DECISION at signing — runbook §4 has the
+verified detail):** the two deferred-apply marker sites of
+`staged/notes-w1c-f3.md` §1 — `.claude/scripts/local/_release_bump_sites.py`
+(12th bump site) and `.claude/scripts/local/verify-counts.sh`
+(VERSION_SITES entry). Status re-checked at closure (2026-08-06, HEAD
+`346f4ea`): the W0 fleet HAS committed both files and the sites are
+absent, so the original condition fires — BUT simulation showed §1a as
+written reds the fleet's new dry-run tests (their fixture lacks the
+marker file; verified 2-line fixture cure → 47/47). Route A: apply
+§1a+§1b+fixture cure and ADD the three paths to Scope. Route B
+(recommended default): SKIP; the fleet lands all three in its own
+follow-up — Forma A (ii) is unconditional either way, and this train
+(VERSION already 1.3.0 == marker) needs no marker bump site before the
+1.4.0 cycle. Whichever route, the mechanical re-derivation enforces the Scope.
+**OWNER-DECISION resolved at signing (2026-08-06): Route B — deferred-apply
+SKIPPED; the three paths stay OUT of this Scope. The follow-up (free
+surfaces, no sentinel) MUST land before the first 1.4.0-cycle bump.**
+
+Ceremony inputs are integrity-pinned: the TRACKED manifest
+`.claude/plans/PLAN-166/staged-manifest.sha256` covers every staged file;
+`shasum -a 256 -c` runs fail-closed BEFORE any apply (lesson
+[[feedback-staged-inputs-need-tracked-hash-manifest]]).
+
+Commit subject tag: `[SENT-PLAN166-W1]`.
+
+## Scope
+
+Scope:
+
+Release train (revert group A):
+  - .claude/governance/npm-trusted-publisher.txt
+  - .claude/governance/pair-rail-verdict-template.md
+  - .claude/scripts/tests/test_release_workflow_asserts.py
+  - .github/workflows/npm-publish.yml
+  - .github/workflows/release.yml
+  - RELEASE.md
+
+Adopter upgrade + ADR + count sweep (revert group B):
+  - .claude/.framework-version
+  - .claude/adr/ADR-155-AMEND-1-delivery-record-ownership.md
+  - .claude/scripts/check-framework-updates.sh
+  - .github/workflows/smoke-install.yml
+  - CLAUDE.md
+  - INSTALL.md
+  - README.md
+  - README.pt-BR.md
+  - docs/ARCHITECTURE.md
+  - docs/CTO-GUIDE.md
+  - docs/FAQ.md
+  - docs/GUIA-COMPLETO.md
+  - docs/README.md
+  - npm/README.md
+  - scripts/_framework_manifest_set.sh
+  - scripts/doctor.sh
+  - scripts/install.sh
+  - scripts/tests/_parity_classify.py
+  - scripts/tests/test-upgrade-spec-ownership.sh
+  - scripts/upgrade.sh
+
+---
+
+## Adendo (2026-08-06, pré-assinatura — CEO)
+
+**15º patch adicionado ao pack:** o template do verdito
+(`pair-rail-verdict-template.md`, canônico em governance) ganha os 3
+campos que o guard novo EXIGE de todo verdito (`delta_allowlist` /
+`delta_manifest` / `delta_manifest_sha256`) + seção "tag() guard
+semantics". Sem isso, o primeiro verdito de rc.2 autorado a partir do
+template morre em E_VERDICT (achado P2 do round 1 da refutação; o
+template é canônico e por isso entra na cerimônia, não no W0).
+**Scope: adicionar este path ao grupo A (trem de release).**
+Manifesto regenerado: 32 entradas (template staged + patch novo).
+
+---
+
+## Adendo (2026-08-06, re-assinatura — rail codex round 4)
+
+Uma linha adicionada ao Scope grupo B: `scripts/tests/_parity_classify.py`.
+Motivo: as entradas KNOWN_OPEN F3-spec-stale / F3-protocol-user-mode são
+MANDATORY-FIRE por contrato do próprio arquivo — com o F3 fechado por esta
+cerimônia elas param de casar e o gate recém-fiado nasceria FATAL; o
+docstring exige deletá-las NO MESMO commit. Rounds 1-4 do rail: 13 achados
+aplicados (install rerun continuity; FMS_MODE link; fingerprint
+completeness; SPEC/marker ancestor-symlink + LINK-record validation;
+backup-before-replace 2x; recovery por current-source match; KNOWN_OPEN).
+To verify what framework version a target is running:
+cat TARGET/.claude/.framework-version   # preferred — refreshed on every upgrade
+# Example output: 1.3.0
+cat TARGET/VERSION                      # fallback (pre-v1.3.0 installs)
+Prefer `.claude/.framework-version` as the forensic anchor when an
+adopter reports a bug. The root `VERSION` file matches the git tag of
+the source framework checkout **at install time only**: `upgrade.sh`
+deliberately never touches it (an adopter repo may have its own
+`VERSION`, and taking it over is the S238/ADR-155 clobber class — see
+`ADR-155-AMEND-1`), so on an upgraded install `VERSION` reports the
+ORIGINAL install version, not the current one. The marker is refreshed
+on every upgrade and is cross-checked against `VERSION` in every
+framework release; fall back to `VERSION` only on pre-v1.3.0 installs
+that have not upgraded yet.
+- `PROTOCOL.md` pointer (skipped on `--ceremony user` installs — a user
+  install never creates root files)
+- `SPEC/v1/` — **forced route** (skipped on `--ceremony user` installs):
+  the SPEC is the published compliance contract, so a local edit is a
+  *fork of the contract*, not a customization — a framework-owned
+  `SPEC/v1` is backed up to `.claude.bak/<timestamp>/SPEC/v1` and
+  replaced wholesale. Ownership follows the recorded delivery (the
+  ADR-155 baseline manifest); a pre-existing `SPEC/v1` with no delivery
+  record is byte-compared against the pristine SPECs shipped at v1.2.0
+  and earlier — a match refreshes it, anything else is preserved in
+  place with a named WARNING (ADR-155-AMEND-1).
+- `.claude/.framework-version` — the framework version marker, rewritten
+  to the source version on every upgrade (this is what
+  `check-framework-updates.sh` and forensic triage read post-upgrade).
+- `VERSION` (root) — **deliberately**: `install.sh` is skip-if-exists,
+  so on an adopter repo with its own `VERSION` the framework never
+  wrote there, and an upgrade overwrite would take the adopter's file
+  (the S238/ADR-155 class). The root `VERSION` is an install-time
+  snapshot forever; the current framework version lives in
+  `.claude/.framework-version`. Do not "fix" this asymmetry — see
+  `ADR-155-AMEND-1`.
+
+Ceremony on upgrade: `upgrade.sh` reads the recorded install ceremony
+from `.claude/.install-state.json` with a dedicated reader that runs
+even under `--no-replay`. **Installs without a readable
+`.install-state.json` (all pre-Wave-B installs) are treated as
+`maintainer` on upgrade** — that is the fail-open, pre-existing
+behavior; if your install was `--ceremony user` and predates the state
+file, re-run `install.sh --ceremony user` once so the ceremony is
+recorded before upgrading.
+| Architecture decision records | **189** | under `.claude/adr/` |
+ls .claude/adr | grep -c '^ADR-'                  # 189 ADRs
+| Architecture decision records | **189** | em `.claude/adr/` |
+ls .claude/adr | grep -c '^ADR-'                  # 189 ADRs
+> - `.github/workflows/release.yml` — release-gate + publish-release (31 steps,
+    ├── adr/                        # 189 architecture decision records
+| ADRs               | 189                          | `ls .claude/adr/ADR-*.md \| wc -l`                        |
+Records in `.claude/adr/` (189 to date), with a documented lifecycle
+| ADRs shipped | 189 | `ls .claude/adr/ADR-*.md \| wc -l` |
+grep -h '^# ADR-' .claude/adr/ADR-*.md | sort             # 189 ADRs on disk
+ls .claude/adr | grep -c '^ADR-'                  # 189 ADRs
+- **Governed by ADR.** 189 ADRs document every architectural decision.
+- `.claude/adr/` — 189 Architecture Decision Records
+| Architecture decision records | **189** | count `ADR-*.md` in `.claude/adr/` |
+| Architecture decision records | **189** | under `.claude/adr/` |
+ls .claude/adr | grep -c '^ADR-'                  # 189 ADRs

--- added claim scan ---
+   (F4: 122s gate + 118s control local, 2-3x CI factor; F3 e2e adds
+backup-before-replace 2x; recovery por current-source match; KNOWN_OPEN).

exec
/bin/zsh -lc "printf '%s\\n' '--- .claude/plans/PLAN-166/OWNER-W1-LAND-step1.sh ---'; nl -ba \".claude/plans/PLAN-166/OWNER-W1-LAND-step1.sh\"" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
--- .claude/plans/PLAN-166/OWNER-W1-LAND-step1.sh ---
     1	#!/bin/bash
     2	# PLAN-166 W1 — LAND step 1 (Owner-run): applies NÃO-kernel + sweep de contagens.
     3	# Espelho exato dos comandos validados na simulação em clone limpo (land-sim.sh,
     4	# 2026-08-06: verify-counts EXIT=0, asserts 52/52, e2e 45/45, bateria 5010 pass,
     5	# touched−scope=∅). release.yml fica FORA — rota kernel-override (step 2).
     6	set -euo pipefail
     7	cd "$(git rev-parse --show-toplevel)"
     8	
     9	APPROVED=.claude/plans/PLAN-166/architect/round-1/approved.md
    10	
    11	# ---- Guards fail-closed (R-rail essencial do generate-ceremony, inline) ----
    12	echo "== G1: assinatura GPG do sentinel"
    13	# NUNCA `| grep -q` sob pipefail (SIGPIPE mata o produtor — lição
    14	# feedback-grep-q-pipefail-kills-producer): capture e case.
    15	GPG_OUT=$(gpg --verify "$APPROVED.asc" "$APPROVED" 2>&1) || { echo "FAIL: gpg --verify rc!=0"; echo "$GPG_OUT"; exit 1; }
    16	case "$GPG_OUT" in
    17	  *"Good signature"*) echo "   OK" ;;
    18	  *) echo "FAIL: assinatura inválida"; echo "$GPG_OUT"; exit 1 ;;
    19	esac
    20	
    21	echo "== G2: anchor == HEAD"
    22	ANCHOR=$(grep '^Anchor-SHA:' "$APPROVED" | awk '{print $2}')
    23	HEAD_SHA=$(git rev-parse HEAD)
    24	[ "$ANCHOR" = "$HEAD_SHA" ] || { echo "FAIL: anchor $ANCHOR != HEAD $HEAD_SHA — re-instanciar e re-assinar"; exit 1; }
    25	echo "   OK ($ANCHOR)"
    26	
    27	echo "== G3: manifesto staged fail-closed"
    28	shasum -a 256 -c .claude/plans/PLAN-166/staged-manifest.sha256 > /dev/null || { echo "FAIL: manifesto"; exit 1; }
    29	echo "   OK (32 entradas)"
    30	
    31	echo "== G4: árvore limpa antes do apply"
    32	DIRT=$(git status --porcelain | grep -v '^?? .claude/plans/PLAN-166/' || true)
    33	[ -z "$DIRT" ] || { echo "FAIL: árvore suja fora de PLAN-166/:"; echo "$DIRT"; exit 1; }
    34	echo "   OK"
    35	
    36	S=.claude/plans/PLAN-166/staged
    37	
    38	# ---- §3 applies (grupo A menos release.yml; grupo B; template 15º) ----
    39	echo "== applies"
    40	for f in \
    41	  .github/workflows/npm-publish.yml \
    42	  .github/workflows/smoke-install.yml \
    43	  .claude/governance/npm-trusted-publisher.txt \
    44	  .claude/governance/pair-rail-verdict-template.md \
    45	  .claude/scripts/tests/test_release_workflow_asserts.py \
    46	  .claude/.framework-version \
    47	  .claude/adr/ADR-155-AMEND-1-delivery-record-ownership.md \
    48	  .claude/scripts/check-framework-updates.sh \
    49	  INSTALL.md \
    50	  scripts/_framework_manifest_set.sh \
    51	  scripts/doctor.sh \
    52	  scripts/install.sh \
    53	  scripts/tests/_parity_classify.py \
    54	  scripts/tests/test-upgrade-spec-ownership.sh \
    55	  scripts/upgrade.sh
    56	do
    57	  cp -p "$S/$f" "$f"
    58	  echo "   applied $f"
    59	done
    60	chmod +x scripts/install.sh scripts/upgrade.sh scripts/doctor.sh \
    61	  scripts/tests/test-upgrade-spec-ownership.sh .claude/scripts/check-framework-updates.sh
    62	
    63	# ---- §4 sweep (BSD sed; content-anchored — validado na simulação) ----
    64	echo "== sweep 188->189 + 29->31"
    65	sed -i '' 's/\*\*188 ADRs\*\*/**189 ADRs**/' CLAUDE.md
    66	sed -i '' 's/# 188 ADRs/# 189 ADRs/' README.md README.pt-BR.md npm/README.md docs/FAQ.md
    67	sed -i '' 's/| Architecture decision records | \*\*188\*\*/| Architecture decision records | **189**/' README.md README.pt-BR.md docs/README.md npm/README.md
    68	sed -i '' 's/| ADRs shipped | 188 |/| ADRs shipped | 189 |/' docs/CTO-GUIDE.md
    69	sed -i '' 's/# 188 ADRs on disk/# 189 ADRs on disk/' docs/CTO-GUIDE.md
    70	sed -i '' -E 's/(\| ADRs +\| )188/\1189/' docs/ARCHITECTURE.md
    71	sed -i '' 's/# 188 architecture decision records/# 189 architecture decision records/' docs/ARCHITECTURE.md
    72	sed -i '' 's/(188 to date)/(189 to date)/' docs/ARCHITECTURE.md
    73	sed -i '' 's/188 ADRs document every architectural decision/189 ADRs document every architectural decision/' docs/GUIA-COMPLETO.md
    74	sed -i '' 's/188 Architecture Decision Records/189 Architecture Decision Records/' docs/GUIA-COMPLETO.md
    75	sed -i '' 's/release-gate + publish-release (29 steps,/release-gate + publish-release (31 steps,/' RELEASE.md
    76	
    77	echo "== census pós-sweep (tem de sair 'sweep clean')"
    78	grep -rn "188" CLAUDE.md README.md README.pt-BR.md docs/ARCHITECTURE.md \
    79	  docs/FAQ.md docs/README.md docs/CTO-GUIDE.md docs/GUIA-COMPLETO.md \
    80	  npm/README.md INSTALL.md 2>/dev/null \
    81	  | grep -iv "S188\|PLAN-188\|#188\|0188\|1188" | grep -i "adr\|decision record" || echo "sweep clean"
    82	
    83	echo "==== STEP 1 CONCLUÍDO — volte para a sessão: o CEO roda os gates §6 ===="

exec
/bin/zsh -lc "printf '%s\\n' '--- .claude/plans/PLAN-166/OWNER-W1-LAND-step1b.sh ---'; nl -ba \".claude/plans/PLAN-166/OWNER-W1-LAND-step1b.sh\"" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
--- .claude/plans/PLAN-166/OWNER-W1-LAND-step1b.sh ---
     1	#!/bin/bash
     2	# =============================================================================
     3	# PLAN-166 W1 — LAND step 1b (SUBSTITUI o step1, obsoleto em 07/08).
     4	#
     5	# Por que o step1 original não pode rodar mais (auditado S297-noite):
     6	#   - G4 dele exige árvore LIMPA e faria os applies — mas a árvore JÁ carrega
     7	#     os applies como sujeira desde a pausa de S296 (12 arquivos byte-==
     8	#     staged, verificado), e
     9	#   - 3 arquivos do apply-list (install.sh, upgrade.sh,
    10	#     _framework_manifest_set.sh) foram SUBSUMIDOS pelo land do PLAN-167
    11	#     (`7c0828a`) — re-aplicar as cópias staged de 06/08 REVERTERIA aquele
    12	#     land. Eles estão LIMPOS no git e assim devem ficar.
    13	#
    14	# Este script portanto NÃO aplica nada: ele AUDITA que a sujeira é exatamente
    15	# o pack, roda os gates na árvore de hoje e imprime a lista de commit.
    16	#
    17	#   bash .claude/plans/PLAN-166/OWNER-W1-LAND-step1b.sh
    18	# =============================================================================
    19	set -euo pipefail
    20	cd "$(git rev-parse --show-toplevel)"
    21	
    22	APPROVED=.claude/plans/PLAN-166/architect/round-1/approved.md
    23	S=.claude/plans/PLAN-166/staged
    24	
    25	echo "== G1: assinatura GPG do sentinel"
    26	GPG_OUT=$(gpg --verify "$APPROVED.asc" "$APPROVED" 2>&1) || { echo "FAIL: gpg --verify rc!=0"; echo "$GPG_OUT"; exit 1; }
    27	case "$GPG_OUT" in
    28	  *"Good signature"*) echo "   OK" ;;
    29	  *) echo "FAIL: assinatura inválida"; echo "$GPG_OUT"; exit 1 ;;
    30	esac
    31	
    32	echo "== G2: anchor == HEAD"
    33	ANCHOR=$(grep '^Anchor-SHA:' "$APPROVED" | awk '{print $2}')
    34	HEAD_SHA=$(git rev-parse HEAD)
    35	[ "$ANCHOR" = "$HEAD_SHA" ] || { echo "FAIL: anchor $ANCHOR != HEAD $HEAD_SHA — re-instanciar e re-assinar (ver W1-approved-draft.md, passos 1-4 do header)"; exit 1; }
    36	echo "   OK ($ANCHOR)"
    37	
    38	echo "== G3: manifesto staged fail-closed"
    39	shasum -a 256 -c .claude/plans/PLAN-166/staged-manifest.sha256 > /dev/null || { echo "FAIL: manifesto"; exit 1; }
    40	echo "   OK (32 entradas)"
    41	
    42	echo "== G4b: a sujeira É o pack (inventário + bytes), e os 3 subsumidos estão limpos"
    43	# 12 arquivos que DEVEM estar sujos e byte-idênticos ao staged:
    44	PACK12=".github/workflows/npm-publish.yml
    45	.github/workflows/smoke-install.yml
    46	.claude/governance/npm-trusted-publisher.txt
    47	.claude/governance/pair-rail-verdict-template.md
    48	.claude/scripts/tests/test_release_workflow_asserts.py
    49	.claude/.framework-version
    50	.claude/adr/ADR-155-AMEND-1-delivery-record-ownership.md
    51	.claude/scripts/check-framework-updates.sh
    52	INSTALL.md
    53	scripts/doctor.sh
    54	scripts/tests/_parity_classify.py
    55	scripts/tests/test-upgrade-spec-ownership.sh"
    56	# Arquivos do sweep de contagens (sed na árvore em S296; validados pelo gate
    57	# verify-counts abaixo, não por bytes) + release.yml (rota kernel, step 2):
    58	SWEEP="README.md
    59	README.pt-BR.md
    60	RELEASE.md
    61	docs/ARCHITECTURE.md
    62	docs/CTO-GUIDE.md
    63	docs/FAQ.md
    64	docs/GUIA-COMPLETO.md
    65	docs/README.md
    66	npm/README.md
    67	.github/workflows/release.yml"
    68	FAILS=0
    69	while IFS= read -r f; do
    70	  if ! cmp -s "$f" "$S/$f"; then echo "   FAIL: $f difere do staged"; FAILS=$((FAILS+1)); fi
    71	done <<< "$PACK12"
    72	for f in scripts/install.sh scripts/upgrade.sh scripts/_framework_manifest_set.sh; do
    73	  st=$(git status --porcelain -- "$f")
    74	  [ -z "$st" ] || { echo "   FAIL: $f deveria estar LIMPO (subsumido pelo PLAN-167)"; FAILS=$((FAILS+1)); }
    75	done
    76	# nenhuma sujeira tracked fora do inventário (plan files têm carona §7):
    77	while IFS= read -r line; do
    78	  [ -z "$line" ] && continue
    79	  p="${line:3}"
    80	  case "$p" in .claude/plans/*) continue ;; esac
    81	  if ! grep -qxF "$p" <<< "$PACK12"$'\n'"$SWEEP"; then
    82	    echo "   FAIL: sujeira tracked FORA do inventário do pack: $line"; FAILS=$((FAILS+1))
    83	  fi
    84	done <<< "$(git status --porcelain | grep -v '^??')"
    85	[ "$FAILS" -eq 0 ] || { echo "FAIL: G4b — $FAILS divergência(s); não commite"; exit 1; }
    86	echo "   OK (12 byte-== staged; 3 subsumidos limpos; zero sujeira estranha)"
    87	
    88	echo "== G5: gates na árvore de HOJE"
    89	python3 .claude/scripts/check-claude-md-claims.py >/dev/null || { echo "FAIL: claims"; exit 1; }
    90	bash .claude/scripts/local/verify-counts.sh >/dev/null || { echo "FAIL: verify-counts"; exit 1; }
    91	python3 -m pytest .claude/scripts/tests/test_release_workflow_asserts.py -q >/dev/null || { echo "FAIL: asserts"; exit 1; }
    92	echo "   OK: claims · verify-counts · asserts 52/52"
    93	
    94	echo "== G6: e2e parity (≈4 min)"
    95	bash scripts/tests/test-install-upgrade-parity-e2e.sh >/tmp/p166-parity-land.log 2>&1 || { echo "FAIL: parity"; tail -5 /tmp/p166-parity-land.log; exit 1; }
    96	echo "   OK: parity PASS"
    97	
    98	echo "== G7: e2e F3 spec-ownership (≈4 min) — 45/45, OU 44/45 com a ÚNICA exceção nomeada"
    99	bash scripts/tests/test-upgrade-spec-ownership.sh >/tmp/p166-f3-land.log 2>&1 || true
   100	RESULT=$(grep -E '^==> RESULT' /tmp/p166-f3-land.log || true)
   101	if grep -q "pass=45 fail=0" <<< "$RESULT"; then
   102	  echo "   OK: 45/45 (a regressão ADOPTER-FORK já foi curada — provavelmente o PLAN-168 landou antes)"
   103	elif grep -q "pass=44 fail=1" <<< "$RESULT" \
   104	     && [ "$(grep -c '^  FAIL' /tmp/p166-f3-land.log)" -eq 1 ] \
   105	     && grep -q "FAIL no ADOPTER-FORK warning" /tmp/p166-f3-land.log; then
   106	  echo "   OK (exceção NOMEADA): 44/45 — a única falha é a WARNING sem o token"
   107	  echo "   ADOPTER-FORK, regressão do rewrite do PLAN-167 (7c0828a), corrigida"
   108	  echo "   no pack do PLAN-168 (staged/scripts/upgrade.sh; provado 45/45 no overlay)."
   109	else
   110	  echo "FAIL: F3 fora do contrato ($RESULT) — investigue antes de commitar"
   111	  grep '^  FAIL' /tmp/p166-f3-land.log | head -5
   112	  exit 1
   113	fi
   114	
   115	echo ""
   116	echo "==== STEP 1b VERDE — commit da cerimônia ===="
   117	echo "Confira touched−scope=∅ (exceção §7: .claude/plans/PLAN-166/**):"
   118	git status --porcelain | grep -v '^??' | awk '{print "   "$2}'
   119	echo ""
   120	echo "git add explícito (NUNCA -A):"
   121	printf '  git add '
   122	{ git status --porcelain | grep -v '^??' | awk '{print $2}'; echo ".claude/plans/PLAN-166"; } | tr '\n' ' '
   123	echo ""
   124	echo "  git commit -S -m 'ceremony(PLAN-166 W1): findings-closure landada — applies+sweep commitados; install/upgrade/FMS subsumidos pelo PLAN-167; F3 44/45 com exceção nomeada (fecha no PLAN-168)'"
   125	echo ""
   126	echo "⚠️  NÃO PUSHE AINDA. Lande o PLAN-168 em seguida (PREPARE-TO-SIGN → gpg →"
   127	echo "    OWNER-LAND) e pushe os DOIS commits juntos: o smoke-install roda o F3"
   128	echo "    no push, e entre os dois lands ele daria 44/45 (vermelho transitório)."

exec
/bin/zsh -lc "printf '%s\\n' '--- .claude/plans/PLAN-167/OWNER-PREPARE-TO-SIGN.sh ---'; nl -ba \".claude/plans/PLAN-167/OWNER-PREPARE-TO-SIGN.sh\"" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
--- .claude/plans/PLAN-167/OWNER-PREPARE-TO-SIGN.sh ---
     1	#!/usr/bin/env bash
     2	# =============================================================================
     3	# PLAN-167 — prepara o approved.md para assinatura.
     4	#
     5	#   bash .claude/plans/PLAN-167/OWNER-PREPARE-TO-SIGN.sh
     6	#
     7	# Faz só o trabalho mecânico: confere o manifesto, fixa o Anchor-SHA no HEAD
     8	# atual e gera W4-approved.md a partir do draft. NÃO assina — a assinatura é
     9	# sua, com a sua chave, e é ela que autoriza a edição canônica.
    10	# =============================================================================
    11	set -euo pipefail
    12	
    13	D=".claude/plans/PLAN-167"
    14	[ -f "scripts/install.sh" ] || { echo "ABORT: rode da raiz do repositório" >&2; exit 1; }
    15	
    16	echo "== 1. o manifesto do pack confere? =="
    17	shasum -c "$D/staged-manifest.sha256" >/dev/null 2>&1 \
    18	  || { echo "ABORT: o manifesto NÃO confere — não assine" >&2; exit 1; }
    19	echo "   ok — $(wc -l < "$D/staged-manifest.sha256" | tr -d ' ') arquivos íntegros"
    20	
    21	echo "== 2. o pack aplica sem conflito? (ensaio, não altera nada) =="
    22	bash "$D/OWNER-W4-LAND.sh" --dry-run >/dev/null 2>&1 \
    23	  || { echo "ABORT: o ensaio falhou — não assine" >&2; exit 1; }
    24	echo "   ok — ensaio limpo"
    25	
    26	echo "== 3. fixando o Anchor-SHA no HEAD atual =="
    27	HEAD_SHA="$( git rev-parse HEAD )"
    28	sed "s|^Anchor-SHA: .*|Anchor-SHA: $HEAD_SHA|" "$D/W4-approved-draft.md" > "$D/W4-approved.md"
    29	grep -q "Anchor-SHA: $HEAD_SHA" "$D/W4-approved.md" \
    30	  || { echo "ABORT: não consegui fixar o anchor" >&2; rm -f "$D/W4-approved.md"; exit 1; }
    31	echo "   ok — $HEAD_SHA"
    32	
    33	cat <<EOF
    34	
    35	────────────────────────────────────────────────────────────────────
    36	PRONTO PARA ASSINAR.
    37	
    38	O que a sua assinatura autoriza: substituir a lógica de decisão de
    39	propriedade em scripts/install.sh, scripts/upgrade.sh e
    40	scripts/_framework_manifest_set.sh — código que TODO ADOTANTE executa.
    41	
    42	Evidência: 58 de 62 células verdes, 0 regressões, 4 rodadas de revisão
    43	cross-model. Os 4 vermelhos são deliberados (2 são defeito do TESTE) e
    44	estão nomeados em W4-approved-draft.md.
    45	
    46	Agora rode estes dois comandos:
    47	
    48	  gpg --detach-sign --armor $D/W4-approved.md
    49	  bash $D/OWNER-W4-LAND.sh
    50	
    51	Se o gpg reclamar de "No pinentry":
    52	  export GPG_TTY=\$(tty); gpgconf --kill gpg-agent
    53	────────────────────────────────────────────────────────────────────
    54	EOF

exec
/bin/zsh -lc "grep -R \"LINK  .*framework-version\\|\\.framework-version\" -n scripts/install.sh scripts/upgrade.sh scripts/_framework_manifest_set.sh scripts/doctor.sh .claude/scripts/check-framework-updates.sh | head -200 && printf '\\n--- manifest writer ---\\n' && grep -R \"LINK  \\|write_baseline_manifest\\|FMS_HASH_ROOT\" -n scripts/install.sh scripts/upgrade.sh scripts/_framework_manifest_set.sh | head -240" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
scripts/install.sh:1358:# .claude/.framework-version is a TRACKED file of the framework repo (one
scripts/install.sh:1370:  if [[ ! -f "$SOURCE_DIR/.claude/.framework-version" ]]; then
scripts/install.sh:1371:    echo "    SKIP: .claude/.framework-version absent in source (pre-v1.3.0 checkout)"
scripts/install.sh:1375:  echo "==> Installing framework version marker (.claude/.framework-version — $(tr -d '[:space:]' < "$SOURCE_DIR/.claude/.framework-version"))"
scripts/install.sh:1376:  _state_record_op "install_framework_marker" ".claude/.framework-version"
scripts/install.sh:1377:  install_one ".claude/.framework-version"
scripts/install.sh:1380:    _state_record_op "delivered_framework_marker" ".claude/.framework-version"
scripts/install.sh:2385:     && grep -Eq '^([0-9a-f]{64}|LINK)  \.claude/\.framework-version(  |$)' "$manifest" 2>/dev/null \
scripts/install.sh:2386:     && _prior_link_target_matches "$manifest" ".claude/.framework-version"; then
scripts/install.sh:2390:.claude/.framework-version"
scripts/install.sh:2391:    echo "    ownership continuity: .framework-version delivery record preserved from prior manifest"
scripts/install.sh:2411:      *".claude/.framework-version"*) export FMS_HASH_SOURCE_MARKER="HASH_SOURCE" ;;
scripts/install.sh:2438:      *".claude/.framework-version"*) export FMS_HASH_SOURCE_MARKER="HASH_SOURCE" ;;
scripts/upgrade.sh:344:  and the .claude/.framework-version marker) in an existing adopter
scripts/upgrade.sh:348:  .claude/.framework-version for the installed framework version). NOTE: .claude/settings.json IS
scripts/upgrade.sh:1660:# .claude/.framework-version) derives from the REGISTERED DELIVERY — here,
scripts/upgrade.sh:1676:  grep -Eq '^([0-9a-f]{64}|LINK)  \.claude/\.framework-version(  |$)' "$_BASELINE_MANIFEST_FILE" 2>/dev/null
scripts/upgrade.sh:1851:  if [ -L "$TARGET/SPEC/v1" ] || [ -L "$TARGET/.claude/.framework-version" ]; then
scripts/upgrade.sh:2028:  local src="$SOURCE_DIR/.claude/.framework-version"
scripts/upgrade.sh:2029:  local dst="$TARGET/.claude/.framework-version"
scripts/upgrade.sh:2030:  local bak="$BAK_DIR/.claude/.framework-version"
scripts/upgrade.sh:2034:  if _lg_ancestor_is_symlink "$TARGET" ".claude/.framework-version"; then
scripts/upgrade.sh:2039:  _pr="$( _ov_obs_prior_record ".claude/.framework-version" )"
scripts/upgrade.sh:2053:  _sk="$( _ov_obs_skip ".claude/.framework-version" )"
scripts/upgrade.sh:2059:    echo "    WARNING: .claude/.framework-version dimensions are not a legal cell" >&2
scripts/upgrade.sh:2071:        ancestor_symlink/*) echo "    SKIP: .claude/.framework-version has a symlinked ancestor (refusing to write through it — F11a)" ;;
scripts/upgrade.sh:2072:        symlink/*)          echo "    SKIP: .claude/.framework-version is the recorded --mode link delivery (target unchanged)" ;;
scripts/upgrade.sh:2073:        */self)             echo "    SKIPPED (--skip): .claude/.framework-version" ;;
scripts/upgrade.sh:2074:        *)                  echo "    SKIP: .claude/.framework-version (ownership carried forward)" ;;
scripts/upgrade.sh:2084:        echo "    SKIP: .claude/.framework-version absent in source (pre-v1.3.0 checkout)"
scripts/upgrade.sh:2090:        echo "    WARNING: .claude/.framework-version is a symlink that does NOT match the" >&2
scripts/upgrade.sh:2094:        echo "    SKIP: .claude/.framework-version is $_lt — adopter-owned, refusing to write into/through it"
scripts/upgrade.sh:2101:        echo "    (dry-run) would REFRESH: .claude/.framework-version ($(tr -d '[:space:]' < "$src" 2>/dev/null || true))"
scripts/upgrade.sh:2107:          echo "    BACKED UP: .claude/.framework-version -> $bak"
scripts/upgrade.sh:2110:          echo "    WARNING: could not back up differing .claude/.framework-version —" >&2
scripts/upgrade.sh:2113:          _up_record_op "preserve_marker_backup_failed" ".claude/.framework-version"
scripts/upgrade.sh:2129:        echo "    REFRESHED: .claude/.framework-version ($(tr -d '[:space:]' < "$dst" 2>/dev/null || true))"
scripts/upgrade.sh:2131:        echo "    WARNING: .claude/.framework-version write did not validate — NOT recorded as" >&2
scripts/upgrade.sh:3077:echo "==> Refreshing framework version marker (.claude/.framework-version)"
scripts/upgrade.sh:3133:  elif [[ -L "$TARGET/.claude/skills" || -L "$TARGET/SPEC/v1" || -L "$TARGET/.claude/.framework-version" ]]; then
scripts/_framework_manifest_set.sh:36:#     PROTOCOL.md, SPEC/v1 and .claude/.framework-version are enumerated ONLY
scripts/_framework_manifest_set.sh:40:#         FMS_DELIVERED_MARKER     .claude/.framework-version marker
scripts/_framework_manifest_set.sh:141:      printf '%s\n' ".claude/.framework-version"
scripts/_framework_manifest_set.sh:301:    .claude/.framework-version) printf '%s' "${FMS_HASH_SOURCE_MARKER:-}" ;;
scripts/_framework_manifest_set.sh:308:    SPEC/v1|SPEC/v1/*|PROTOCOL.md|.claude/.framework-version) return 0 ;;
scripts/doctor.sh:617:    # SPEC/v1 and .claude/.framework-version are CONDITIONAL on the
scripts/doctor.sh:643:    if _dr_delivered '\.claude/\.framework-version(  |$)'; then
.claude/scripts/check-framework-updates.sh:88:# .claude/.framework-version instead — but the marker is only TRUSTED when
.claude/scripts/check-framework-updates.sh:94:#   2. <root>/.claude/.framework-version  when well-formed AND
.claude/scripts/check-framework-updates.sh:110:    if [ -f "$cur/.claude/.framework-version" ] || [ -f "$cur/VERSION" ]; then
.claude/scripts/check-framework-updates.sh:117:    echo "fatal: no .claude/.framework-version or VERSION found (looked from $(pwd))" >&2
.claude/scripts/check-framework-updates.sh:120:  MARKER="$VROOT/.claude/.framework-version"
.claude/scripts/check-framework-updates.sh:125:      MARKER_REC="$(grep -E '^([0-9a-f]{64}|LINK)  \.claude/\.framework-version(  |$)' "$MANIFEST" 2>/dev/null | head -1 || true)"
.claude/scripts/check-framework-updates.sh:140:          _rec_tgt="${MARKER_REC#LINK  .claude/.framework-version  }"
.claude/scripts/check-framework-updates.sh:156:        log "note: .claude/.framework-version does NOT match its delivery record (edited, redirected, or no digest tool available) — falling back to VERSION"
.claude/scripts/check-framework-updates.sh:161:          VSOURCE="marker (.claude/.framework-version, delivery-recorded)"
.claude/scripts/check-framework-updates.sh:163:          log "note: .claude/.framework-version malformed ('$MARKER_VAL') — falling back to VERSION"
.claude/scripts/check-framework-updates.sh:173:      log "note: .claude/.framework-version present but NOT delivery-recorded in .claude/.install-manifest.sha256 — falling back to VERSION (r20: a pre-existing adopter marker is not the framework's)"

--- manifest writer ---
scripts/install.sh:2267:#   LINK  <relpath>  <target>     — a --mode link symlink (content == source,
scripts/install.sh:2280:  if ! command -v _write_baseline_manifest >/dev/null 2>&1; then
scripts/install.sh:2323:        "LINK  $2  "*) _plt_rec="${_plt_line#LINK  $2  }"; break ;;
scripts/install.sh:2362:    # FMS_HASH_ROOT does NOT reach PROTOCOL.md: _write_baseline_manifest
scripts/install.sh:2373:       || grep -Eq '^LINK  PROTOCOL\.md(  |$)' "$manifest" 2>/dev/null; then
scripts/install.sh:2402:  # so a global FMS_HASH_ROOT rewrote every rendered file's baseline to the
scripts/install.sh:2454:  _write_baseline_manifest "$manifest"
scripts/install.sh:2455:  unset FMS_ROOT FMS_PROFILE_PARTS FMS_MODE FMS_HASH_ROOT FMS_PROTOCOL_HASH \
scripts/upgrade.sh:848:# A `LINK  <relpath>  <target>` record describes a --mode link delivery whose
scripts/upgrade.sh:942:        rest="${line#LINK  }"
scripts/upgrade.sh:977:        printf 'LINK  %s  %s\n' "$rel" "$target" >> "$sanitized"
scripts/upgrade.sh:1668:  # the WHOLE tree as one directory symlink — `LINK  SPEC/v1  <target>`, no
scripts/upgrade.sh:1783:  _opr_link="$( grep -E "^LINK  ${_opr_rel}  " "$_BASELINE_MANIFEST_FILE" 2>/dev/null | head -1 || true )"
scripts/upgrade.sh:1788:    _opr_rec="${_opr_link#LINK  ${_opr_rel}  }"
scripts/upgrade.sh:1848:     && grep -Eq '^LINK  ' "$_BASELINE_MANIFEST_FILE" 2>/dev/null; then
scripts/upgrade.sh:3042:  # empty, and _write_baseline_manifest then hashes the LIVE pointer —
scripts/upgrade.sh:3053:       || grep -Eq '^LINK  PROTOCOL\.md(  |$)' "$_BASELINE_MANIFEST_FILE" 2>/dev/null; then
scripts/upgrade.sh:3094:if [[ "$DRY_RUN" -eq 0 ]] && command -v _write_baseline_manifest >/dev/null 2>&1; then
scripts/upgrade.sh:3097:  _up_record_op "rewrite_baseline_manifest" ".claude/.install-manifest.sha256"
scripts/upgrade.sh:3099:  export FMS_HASH_ROOT="$SOURCE_DIR"   # but record the FRAMEWORK hash, not the
scripts/upgrade.sh:3114:     && grep -Eq '^LINK  ' "$_BASELINE_MANIFEST_FILE" 2>/dev/null; then
scripts/upgrade.sh:3156:  _write_baseline_manifest "$TARGET/.claude/.install-manifest.sha256"
scripts/upgrade.sh:3157:  unset FMS_ROOT FMS_HASH_ROOT FMS_PROFILE_PARTS FMS_MODE FMS_PROTOCOL_HASH FMS_LINK_PATHS
scripts/_framework_manifest_set.sh:134:    # present in the source tree, so the FMS_HASH_ROOT baseline rewrite
scripts/_framework_manifest_set.sh:215:# _write_baseline_manifest — THE single baseline-manifest generator (ADR-155
scripts/_framework_manifest_set.sh:230:#   LINK  <relpath>  <target>   — link-mode symlink (content == source)
scripts/_framework_manifest_set.sh:232:# Does FMS_HASH_ROOT apply to this relpath? UNSET FMS_HASH_ROOT_PATHS means
scripts/_framework_manifest_set.sh:238:# FMS_HASH_ROOT on an install rerun rewrote every rendered file's hash to the
scripts/_framework_manifest_set.sh:247:  [ -n "${FMS_HASH_ROOT_PATHS:-}" ] || return 0
scripts/_framework_manifest_set.sh:252:  for _hra_p in $FMS_HASH_ROOT_PATHS; do
scripts/_framework_manifest_set.sh:320:_write_baseline_manifest() {
scripts/_framework_manifest_set.sh:327:  : "${FMS_ROOT:?_write_baseline_manifest requires FMS_ROOT}"
scripts/_framework_manifest_set.sh:328:  # FMS_HASH_ROOT (optional): hash the FRAMEWORK version of each file from here
scripts/_framework_manifest_set.sh:337:  # from FMS_ROOT (the target pointer), never FMS_HASH_ROOT. (Codex R1 + dry-run)
scripts/_framework_manifest_set.sh:338:  _wbm_hash_root="${FMS_HASH_ROOT:-$FMS_ROOT}"
scripts/_framework_manifest_set.sh:359:      printf 'LINK  %s  %s\n' "$_wbm_rel" "$_wbm_target" >> "$_wbm_tmp"
scripts/_framework_manifest_set.sh:377:            # FMS_SOURCE_ROOT, never FMS_HASH_ROOT: the global override is an
scripts/_framework_manifest_set.sh:403:        # Hash the FRAMEWORK version. When FMS_HASH_ROOT is set (upgrade) and the
scripts/_framework_manifest_set.sh:409:        if [ -n "${FMS_HASH_ROOT:-}" ] && _wbm_hash_root_applies "$_wbm_rel"; then

exec
/bin/zsh -lc "sed -n '1,220p' scripts/_hash_lib.sh && grep -R \"check-framework-updates\" -n .claude/settings.json templates scripts .claude | head -80" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 204ms:
Binary file scripts/tests/__pycache__/_parity_classify.cpython-311.pyc matches
scripts/tests/test-upgrade-spec-ownership.sh:60:CHECKER="${CEO_UPDATE_CHECKER_UNDER_TEST:-$SOURCE_DIR/.claude/scripts/check-framework-updates.sh}"
scripts/tests/test-upgrade-spec-ownership.sh:197:echo "==> S6: check-framework-updates.sh — marker-first, record-gated"
scripts/tests/_parity_classify.py:187:            "check-framework-updates.sh keeps resolving the stale root VERSION"
.claude/adr/ADR-155-AMEND-1-delivery-record-ownership.md:76:on an ADOPTER tree — today, `.claude/scripts/check-framework-updates.sh`
.claude/adr/ADR-155-AMEND-1-delivery-record-ownership.md:200:`check-framework-updates.sh` trusts the marker only when the baseline
.claude/plans/PLAN-167/rail/codex-r2.md:20: .claude/scripts/check-framework-updates.sh         |  95 ++-
.claude/plans/PLAN-167/rail/codex-r2.md:2691:/bin/zsh -lc "git diff -- .claude/scripts/check-framework-updates.sh .claude/scripts/check-model-deprecations.py scripts/doctor.sh scripts/tests/_parity_classify.py scripts/tests/ownership_table.tsv scripts/tests/test-ownership-table.sh && printf '\\n--- UNTRACKED UNIT ---\\n' && sed -n '1,220p' scripts/tests/test-ownership-verdict-unit.sh && printf '\\n--- UNTRACKED E2E ---\\n' && sed -n '1,420p' scripts/tests/test-upgrade-spec-ownership.sh" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
.claude/plans/PLAN-167/rail/codex-r2.md:2697:diff --git a/.claude/scripts/check-framework-updates.sh b/.claude/scripts/check-framework-updates.sh
.claude/plans/PLAN-167/rail/codex-r2.md:2699:--- a/.claude/scripts/check-framework-updates.sh
.claude/plans/PLAN-167/rail/codex-r2.md:2700:+++ b/.claude/scripts/check-framework-updates.sh
.claude/plans/PLAN-167/rail/codex-r2.md:3251:CHECKER="${CEO_UPDATE_CHECKER_UNDER_TEST:-$SOURCE_DIR/.claude/scripts/check-framework-updates.sh}"
.claude/plans/PLAN-167/rail/codex-r2.md:3388:echo "==> S6: check-framework-updates.sh — marker-first, record-gated"
.claude/plans/PLAN-167/rail/codex-r2.md:4680:+      - ".claude/scripts/check-framework-updates.sh"
.claude/plans/PLAN-167/rail/codex-r2.md:4706:+      - ".claude/scripts/check-framework-updates.sh"
.claude/plans/PLAN-167/rail/codex-r2.md:6563:+  `check-framework-updates.sh` and forensic triage read post-upgrade).
.claude/plans/PLAN-167/rail/codex-r2.md:6845:on an ADOPTER tree — today, `.claude/scripts/check-framework-updates.sh`
.claude/plans/PLAN-167/rail/codex-r2.md:6969:`check-framework-updates.sh` trusts the marker only when the baseline
.claude/plans/PLAN-167/rail/codex-r2.md:10856:/bin/zsh -lc "grep -R \"framework-version\" -n .claude/scripts scripts .github | head -120; printf '\\n--- current counts ---\\n'; find .claude/adr -maxdepth 1 -name 'ADR-*.md' | wc -l; grep -c '"'^      - name:'"' .github/workflows/release.yml; printf '\\n--- syntax checks ---\\n'; bash -n scripts/_framework_manifest_set.sh && echo fms-ok; bash -n scripts/install.sh && echo install-ok; bash -n scripts/upgrade.sh && echo upgrade-ok; bash -n scripts/doctor.sh && echo doctor-ok; bash -n .claude/scripts/check-framework-updates.sh && echo checker-ok; bash -n scripts/tests/test-ownership-table.sh && echo table-ok; bash -n scripts/tests/test-ownership-verdict-unit.sh && echo unit-ok; bash -n scripts/tests/test-upgrade-spec-ownership.sh && echo spec-test-ok" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
.claude/plans/PLAN-167/rail/codex-r2.md:10858:.claude/scripts/check-framework-updates.sh:88:# .claude/.framework-version instead — but the marker is only TRUSTED when
.claude/plans/PLAN-167/rail/codex-r2.md:10859:.claude/scripts/check-framework-updates.sh:94:#   2. <root>/.claude/.framework-version  when well-formed AND
.claude/plans/PLAN-167/rail/codex-r2.md:10860:.claude/scripts/check-framework-updates.sh:110:    if [ -f "$cur/.claude/.framework-version" ] || [ -f "$cur/VERSION" ]; then
.claude/plans/PLAN-167/rail/codex-r2.md:10861:.claude/scripts/check-framework-updates.sh:117:    echo "fatal: no .claude/.framework-version or VERSION found (looked from $(pwd))" >&2
.claude/plans/PLAN-167/rail/codex-r2.md:10862:.claude/scripts/check-framework-updates.sh:120:  MARKER="$VROOT/.claude/.framework-version"
.claude/plans/PLAN-167/rail/codex-r2.md:10863:.claude/scripts/check-framework-updates.sh:125:      MARKER_REC="$(grep -E '^([0-9a-f]{64}|LINK)  \.claude/\.framework-version(  |$)' "$MANIFEST" 2>/dev/null | head -1 || true)"
.claude/plans/PLAN-167/rail/codex-r2.md:10864:.claude/scripts/check-framework-updates.sh:140:          _rec_tgt="${MARKER_REC#LINK  .claude/.framework-version  }"
.claude/plans/PLAN-167/rail/codex-r2.md:10865:.claude/scripts/check-framework-updates.sh:156:        log "note: .claude/.framework-version does NOT match its delivery record (edited, redirected, or no digest tool available) — falling back to VERSION"
.claude/plans/PLAN-167/rail/codex-r2.md:10866:.claude/scripts/check-framework-updates.sh:161:          VSOURCE="marker (.claude/.framework-version, delivery-recorded)"
.claude/plans/PLAN-167/rail/codex-r2.md:10867:.claude/scripts/check-framework-updates.sh:163:          log "note: .claude/.framework-version malformed ('$MARKER_VAL') — falling back to VERSION"
.claude/plans/PLAN-167/rail/codex-r2.md:10868:.claude/scripts/check-framework-updates.sh:173:      log "note: .claude/.framework-version present but NOT delivery-recorded in .claude/.install-manifest.sha256 — falling back to VERSION (r20: a pre-existing adopter marker is not the framework's)"
.claude/plans/PLAN-167/rail/codex-r2.md:12718:-198dcec214dbb4def43be626eae5a6a74b540a00dad4872e5a601216541bf5f6  .claude/plans/PLAN-166/staged/.claude/scripts/check-framework-updates.sh
.claude/plans/PLAN-167/rail/codex-r2.md:12719:+ac84cd8194549f42394a7f2ac45786bc537391f27b67dde33c4c4b4c1bb0cefd  .claude/plans/PLAN-166/staged/.claude/scripts/check-framework-updates.sh
.claude/plans/PLAN-167/rail/codex-r2.md:12729:-fa68c9eccd57031969e9976a35b0f118e573795c8b661d042317bab0d9235b92  .claude/plans/PLAN-166/staged/patches/f3-check-framework-updates-marker-first.patch
.claude/plans/PLAN-167/rail/codex-r2.md:12730:+7af7cf6a6c46a32042cb73f0761277e8ddd8869d5b596278e63013dfc6c435d9  .claude/plans/PLAN-166/staged/patches/f3-check-framework-updates-marker-first.patch
.claude/plans/PLAN-167/rail/codex-r2.md:12762:ac84cd8194549f42394a7f2ac45786bc537391f27b67dde33c4c4b4c1bb0cefd  .claude/plans/PLAN-166/staged/.claude/scripts/check-framework-updates.sh
.claude/plans/PLAN-167/rail/codex-r2.md:12771:7af7cf6a6c46a32042cb73f0761277e8ddd8869d5b596278e63013dfc6c435d9  .claude/plans/PLAN-166/staged/patches/f3-check-framework-updates-marker-first.patch
.claude/plans/PLAN-167/rail/codex-r2.md:13404:   187	            "check-framework-updates.sh keeps resolving the stale root VERSION"
.claude/plans/PLAN-167/rail/codex-r3.md:20: .claude/scripts/check-framework-updates.sh         |  95 ++-
.claude/plans/PLAN-167/rail/codex-r3.md:105:-198dcec214dbb4def43be626eae5a6a74b540a00dad4872e5a601216541bf5f6  .claude/plans/PLAN-166/staged/.claude/scripts/check-framework-updates.sh
.claude/plans/PLAN-167/rail/codex-r3.md:106:+ac84cd8194549f42394a7f2ac45786bc537391f27b67dde33c4c4b4c1bb0cefd  .claude/plans/PLAN-166/staged/.claude/scripts/check-framework-updates.sh
.claude/plans/PLAN-167/rail/codex-r3.md:116:-fa68c9eccd57031969e9976a35b0f118e573795c8b661d042317bab0d9235b92  .claude/plans/PLAN-166/staged/patches/f3-check-framework-updates-marker-first.patch
.claude/plans/PLAN-167/rail/codex-r3.md:117:+7af7cf6a6c46a32042cb73f0761277e8ddd8869d5b596278e63013dfc6c435d9  .claude/plans/PLAN-166/staged/patches/f3-check-framework-updates-marker-first.patch
.claude/plans/PLAN-167/rail/codex-r3.md:145:diff --git a/.claude/scripts/check-framework-updates.sh b/.claude/scripts/check-framework-updates.sh
.claude/plans/PLAN-167/rail/codex-r3.md:147:--- a/.claude/scripts/check-framework-updates.sh
.claude/plans/PLAN-167/rail/codex-r3.md:148:+++ b/.claude/scripts/check-framework-updates.sh
.claude/plans/PLAN-167/rail/codex-r3.md:1418:+      - ".claude/scripts/check-framework-updates.sh"
.claude/plans/PLAN-167/rail/codex-r3.md:1444:+      - ".claude/scripts/check-framework-updates.sh"
.claude/plans/PLAN-167/rail/codex-r3.md:1618:+  `check-framework-updates.sh` and forensic triage read post-upgrade).
.claude/plans/PLAN-167/rail/codex-r3.md:3834:on an ADOPTER tree — today, `.claude/scripts/check-framework-updates.sh`
.claude/plans/PLAN-167/rail/codex-r3.md:3958:`check-framework-updates.sh` trusts the marker only when the baseline
.claude/plans/PLAN-167/rail/codex-r3.md:4093:   `doctor.sh` / `check-framework-updates.sh` — explicit delivery writes
.claude/plans/PLAN-167/rail/codex-r3.md:4182:  - .claude/scripts/check-framework-updates.sh
.claude/plans/PLAN-167/rail/codex-r3.md:4277:CHECKER="${CEO_UPDATE_CHECKER_UNDER_TEST:-$SOURCE_DIR/.claude/scripts/check-framework-updates.sh}"
.claude/plans/PLAN-167/rail/codex-r3.md:4414:echo "==> S6: check-framework-updates.sh — marker-first, record-gated"
.claude/plans/PLAN-167/rail/codex-r3.md:8338:/bin/zsh -lc "git diff --unified=50 -- scripts/doctor.sh; printf '\\n--- checker diff ---\\n'; git diff --unified=40 -- .claude/scripts/check-framework-updates.sh; printf '\\n--- model dep diff ---\\n'; git diff --unified=40 -- .claude/scripts/check-model-deprecations.py" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
.claude/plans/PLAN-167/rail/codex-r3.md:8493:diff --git a/.claude/scripts/check-framework-updates.sh b/.claude/scripts/check-framework-updates.sh
.claude/plans/PLAN-167/rail/codex-r3.md:8495:--- a/.claude/scripts/check-framework-updates.sh
.claude/plans/PLAN-167/rail/codex-r3.md:8496:+++ b/.claude/scripts/check-framework-updates.sh
.claude/plans/PLAN-167/rail/codex-r3.md:9204:+      - ".claude/scripts/check-framework-updates.sh"
.claude/plans/PLAN-167/rail/codex-r3.md:9232:+      - ".claude/scripts/check-framework-updates.sh"
.claude/plans/PLAN-167/rail/codex-r3.md:11518:for f in .claude/scripts/check-framework-updates.sh scripts/_framework_manifest_set.sh scripts/doctor.sh scripts/install.sh scripts/upgrade.sh scripts/tests/test-ownership-table.sh scripts/tests/test-ownership-verdict-unit.sh scripts/tests/test-upgrade-spec-ownership.sh; do bash -n "$f" || exit; done
.claude/plans/PLAN-167/rail/codex-r3.md:11717:    60	CHECKER="${CEO_UPDATE_CHECKER_UNDER_TEST:-$SOURCE_DIR/.claude/scripts/check-framework-updates.sh}"
.claude/plans/PLAN-167/rail/codex-r3.md:11854:   197	echo "==> S6: check-framework-updates.sh — marker-first, record-gated"
.claude/plans/PLAN-167/rail/codex-r3.md:12002:+  `check-framework-updates.sh` and forensic triage read post-upgrade).
.claude/plans/PLAN-167/rail/codex-r3.md:12315:   `doctor.sh` / `check-framework-updates.sh` — explicit delivery writes
.claude/plans/PLAN-167/rail/codex-r3.md:12406:  - .claude/scripts/check-framework-updates.sh
.claude/plans/PLAN-167/rail/codex-r3.md:16452:/bin/zsh -lc 'shellcheck -S warning .claude/scripts/check-framework-updates.sh scripts/_framework_manifest_set.sh scripts/doctor.sh scripts/install.sh scripts/upgrade.sh scripts/tests/test-ownership-table.sh scripts/tests/test-ownership-verdict-unit.sh scripts/tests/test-upgrade-spec-ownership.sh' in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
.claude/plans/PLAN-167/rail/codex-r3.md:19702: M .claude/scripts/check-framework-updates.sh
.claude/plans/PLAN-167/rail/codex-r3.md:19739: .claude/scripts/check-framework-updates.sh         |  95 ++-
.claude/plans/PLAN-167/rail/codex-r3.md:19771:90	5	.claude/scripts/check-framework-updates.sh
.claude/plans/PLAN-167/rail/codex-r3.md:20480:/bin/zsh -lc "nl -ba scripts/upgrade.sh | sed -n '2990,3155p'; nl -ba scripts/upgrade.sh | sed -n '3155,3215p'; git diff -- .claude/scripts/check-framework-updates.sh; git diff -- scripts/doctor.sh; git diff -- .claude/scripts/check-model-deprecations.py" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
.claude/plans/PLAN-167/rail/codex-r3.md:20713:diff --git a/.claude/scripts/check-framework-updates.sh b/.claude/scripts/check-framework-updates.sh
.claude/plans/PLAN-167/rail/codex-r3.md:20715:--- a/.claude/scripts/check-framework-updates.sh
.claude/plans/PLAN-167/rail/codex-r3.md:20716:+++ b/.claude/scripts/check-framework-updates.sh
.claude/plans/PLAN-167/rail/codex-r3.md:21323:+      - ".claude/scripts/check-framework-updates.sh"
.claude/plans/PLAN-167/rail/codex-r3.md:21349:+      - ".claude/scripts/check-framework-updates.sh"
.claude/plans/PLAN-167/rail/codex-r3.md:24616:CHECKER="${CEO_UPDATE_CHECKER_UNDER_TEST:-$SOURCE_DIR/.claude/scripts/check-framework-updates.sh}"
.claude/plans/PLAN-167/rail/codex-r3.md:24753:echo "==> S6: check-framework-updates.sh — marker-first, record-gated"
.claude/plans/PLAN-167/rail/codex-r3.md:26254:.claude/scripts/check-framework-updates.sh:88:# .claude/.framework-version instead — but the marker is only TRUSTED when
.claude/plans/PLAN-167/rail/codex-r3.md:26255:.claude/scripts/check-framework-updates.sh:94:#   2. <root>/.claude/.framework-version  when well-formed AND

exec
/bin/zsh -lc 'set -o pipefail
bash -n .claude/scripts/check-framework-updates.sh scripts/doctor.sh scripts/tests/test-upgrade-spec-ownership.sh .claude/plans/PLAN-166/OWNER-W1-LAND-step1.sh .claude/plans/PLAN-166/OWNER-W1-LAND-step1b.sh .claude/plans/PLAN-167/OWNER-PREPARE-TO-SIGN.sh
PYTHONDONTWRITEBYTECODE=1 python3 -m pytest -p no:cacheprovider .claude/scripts/tests/test_release_workflow_asserts.py -q
python3 .claude/scripts/check-claude-md-claims.py
bash .claude/scripts/local/verify-counts.sh' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 5891ms:
....................................................                     [100%]
52 passed in 0.39s
=== verify-counts.sh — bidirectional drift check ===
Live-derived counts:
  skills             = 166
  core               = 42
  frontend           = 8
  domain             = 116
  adrs               = 189
  hook_py            = 57
  registered         = 46
  registrations      = 48
  lib                = 68
  lib_recursive      = 140
  spec_v1            = 32
  schema_files       = 28
  tests              = 14294
  test_files         = 739
  release_steps      = 31
  commands           = 27
  workflows          = 21
  mutation_fixtures  = 85
  tla_specs          = 4
  version            = 1.3.0

Approx metrics (band +/-5%):
  test_files
    command        = git ls-files '*test_*.py' '*_test.py' | wc -l
    observed       = 739
    collect errors = n/a
    accepted band  = [702..775]
    cited in docs  = ~730
  tests
    command        = python3 -m pytest --collect-only -q   # pytest.ini testpaths == `make test-collect`
    observed       = 14294
    collect errors = 0
    accepted band  = [13579..15008]
    cited in docs  = ~14000

  (no drift detected — all doc counts match the live source)

exec
/bin/zsh -lc 'bash scripts/tests/test-upgrade-spec-ownership.sh' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 exited 1 in 170719ms:
  ok   SPEC/v1 installed
  ok   root PROTOCOL.md installed
  ok   marker installed
  ok   marker == source VERSION (1.3.0)
  ok   baseline records SPEC/v1/
  ok   baseline records PROTOCOL.md
  ok   baseline records marker
  ok   install-state journals delivered_spec_v1
  ok   install-state journals delivered_framework_marker
==> S2: 2nd upgrade — forced SPEC refresh (baseline already has SPEC)
  ok   upgrade rc=0 (record-owned fixture)
  ok   edited SPEC file was FORCE-replaced with source bytes
  ok   backup of the edited SPEC present under .claude.bak/<ts>/SPEC/v1
  ok   upgrade log names the forced route
  ok   root VERSION sentinel untouched by upgrade (ADR-155-AMEND-1)
  ok   marker refreshed to source VERSION post-upgrade
  ok   rewritten baseline still records SPEC/v1/ (ownership continuity)
==> S6: check-framework-updates.sh — marker-first, record-gated
  ok   stub upstream tagged v1.3.0
  ok   post-upgrade tree reports up-to-date via marker (no behind-minor loop)
  ok   checker names the marker as its version source
  ok   marker record stripped => fallback to stale VERSION => behind (rc=2)
  ok   checker names the r20 fallback
==> S8: doctor maintainer mode — stray file in delivered SPEC is an orphan
  ok   delivered SPEC is enumerated: stray file flagged, rc=1
==> S4: legacy baseline (no SPEC records) + edited SPEC => preserve + WARNING
  ok   upgrade rc=0 (fork is preserved, never fatal)
  FAIL no ADOPTER-FORK warning in upgrade log
  ok   forked SPEC preserved in place
  ok   rewritten baseline does NOT claim the adopter-fork SPEC
  ok   forensic snapshot of the fork present under .claude.bak
==> S3: --ceremony user install + upgrade --no-replay
  ok   user install has no SPEC/
  ok   user install has no root PROTOCOL.md
  ok   user install DOES receive the marker (inside .claude/)
  ok   user baseline records the marker
  ok   upgrade --no-replay rc=0 on user fixture
  ok   upgrade --no-replay did NOT deliver SPEC (ceremony read is replay-independent)
  ok   upgrade --no-replay did NOT create root PROTOCOL.md (gated _refresh_protocol_pointer)
  ok   upgrade banner names the recorded user ceremony
==> S7: doctor user mode — adopter SPEC/PROTOCOL not orphans
  ok   adopter's own SPEC/PROTOCOL not flagged (rc=0)
  ok   doctor --strict-orphans clean on the user fixture
==> S5: pre-existing marker + pre-existing root PROTOCOL.md not delivered, not trusted
  ok   install rc=0 with pre-existing marker+protocol
  ok   pre-existing marker EXISTS-skipped (adopter bytes intact)
  ok   baseline does NOT record the skipped marker
  ok   pre-existing root PROTOCOL.md EXISTS-skipped (adopter bytes intact)
  ok   baseline does NOT record the skipped PROTOCOL.md
  ok   doctor does not orphan-flag the adopter's pre-existing PROTOCOL.md (rc=0)
  ok   checker refuses the unrecorded marker (r20)
  ok   fallback VERSION (1.3.0) matches stub upstream — up-to-date

==> RESULT: pass=44 fail=1

exec
/bin/zsh -lc 'bash scripts/tests/test-install-upgrade-parity-e2e.sh' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 104539ms:

##############################################################
# ceremony mode: maintainer
##############################################################
--> [A] install.sh (working tree) --ceremony maintainer --profile core
--> [B1] install.sh @ v1.2.0 --ceremony maintainer --profile core
--> [B2] upgrade.sh (source: /Users/joaocanhada/canhada-labs/ceo-orchestration)
--> classify

---- parity classification (mode=maintainer) --------------------------
  inputs:
    A (fresh install)        : /var/folders/9n/hm9srl0s1nz45_p12tj61pd80000gn/T/ceo-parity-e2e-XXXXXX.QiDivZqx2P/maintainer/route-a/adopter  [555 files]
    B (pin v1.2.0   + upgrade): /var/folders/9n/hm9srl0s1nz45_p12tj61pd80000gn/T/ceo-parity-e2e-XXXXXX.QiDivZqx2P/maintainer/route-b/adopter  [946 files]
    head source              : /Users/joaocanhada/canhada-labs/ceo-orchestration
    pinned source (v1.2.0)  : /var/folders/9n/hm9srl0s1nz45_p12tj61pd80000gn/T/ceo-parity-e2e-XXXXXX.QiDivZqx2P/src-v1.2.0
    normalization            : {SOURCE}, {TARGET}
  counts (UNDECLARED residue — declared paths are broken out below):
    IDENTICAL                    519
    PERSONALIZED                  31
    STALE                          0   <-- FATAL if non-zero
    MISSING_IN_B                   0   <-- FATAL if non-zero
    UNCLASSIFIED                   0   <-- FATAL if non-zero
    ONLY_IN_B                    391
    ONLY_IN_B_OUTSIDE_CLAUDE       0   <-- FATAL if non-zero
    MODE_DIFF                      0   <-- FATAL if non-zero
    ACCEPTED (declared)            5
    KNOWN-OPEN (declared)          0

  ACCEPTED divergence (by design / generated / adopter-owned):
    - .claude/.install-manifest.sha256
        derived baseline manifest — regenerated by BOTH routes (_write_baseline_manifest); it is a hash OF the set under comparison, so comparing it would be circular
    - .claude/.install-state.json
        records the invocation itself (argv, timestamps, source sha, upgrade ops) — differs by construction between a fresh install and an install+upgrade; the `ceremony` field is asserted separately below
    - .claude/settings.json
        install seeds it; upgrade does an ADDITIVE hook merge (PLAN-135 W2 H8) plus the 3-state baseline migration (PLAN-163 T5.4) and never clobbers — the two routes converge on keys, not on bytes
    - .gitignore
        adopter-owned append-only surface. install.sh APPENDS marker-guarded blocks (install_posture_state_ignores, PLAN-165 CX-3); upgrade.sh has no append step, so an upgraded adopter never gets them. A REAL install-only delivery gap — accepted here (never fatal) only because the file is adopter-owned and must not be clobbered; reported every run so it stays visible
    - VERSION
        BY DESIGN (PLAN-166 OQ-3 / ADR-155-AMEND-1): the upgrade must NOT touch the adopter's root VERSION — install_one is skip-if-exists, so in an adopter that owns a VERSION the framework never wrote there and backup_and_replace would TAKE the file (the verified S238 worst case). The framework's own version marker moves to .claude/.framework-version. Asserted positively below: B/VERSION must be byte-identical to the pinned source's VERSION (untouched), not merely different

  VERSION assertion: B/VERSION byte-identical to v1.2.0 source (untouched) — OK

  ADVISORY — upgrade shipped CURRENT framework bytes but install
  personalizes them ({{PROJECT_NAME}}-class placeholders survive an
  upgrade). Content generation is correct; presentation is not.
  31 path(s):
    - .claude/skills/core/ai-llm-orchestration/SKILL.md
    - .claude/skills/core/architecture-decisions/SKILL.md
    - .claude/skills/core/ceo-orchestration/SKILL-frontend.md
    - .claude/skills/core/ceo-orchestration/SKILL.md
    - .claude/skills/core/chaos-and-resilience/SKILL.md
    - .claude/skills/core/code-intelligence-lsp/SKILL.md
    - .claude/skills/core/code-review-checklist/SKILL.md
    - .claude/skills/core/codebase-onboarding/SKILL.md
    - .claude/skills/core/compliance-lgpd/SKILL-frontend.md
    - .claude/skills/core/compliance-lgpd/SKILL.md
    - .claude/skills/core/devops-ci-cd/SKILL.md
    - .claude/skills/core/evidence-based-qa/SKILL.md
    - .claude/skills/core/git-workflow-discipline/SKILL.md
    - .claude/skills/core/growth-and-launch/SKILL-frontend.md
    - .claude/skills/core/growth-and-launch/SKILL.md
    - .claude/skills/core/identity-and-trust-architecture/SKILL.md
    - .claude/skills/core/incident-management/SKILL.md
    - .claude/skills/core/llm-routing-and-finops/SKILL.md
    - .claude/skills/core/mcp-server-authoring/SKILL.md
    - .claude/skills/core/minimal-change-discipline/SKILL.md
    ... and 11 more

  ADVISORY — upgrade over-delivery (`cp -R` drags what install's
  selective walk never ships; ADR-155 pre-existing drift, opposite
  direction from F3). 391 path(s), first 15:
    - .claude/agents/code-reviewer.md
    - .claude/agents/devops.md
    - .claude/agents/performance-engineer.md
    - .claude/agents/qa-architect.md
    - .claude/agents/security-engineer.md
    - .claude/hooks/.coverage
    - .claude/scripts/.known_actions_floor.lock
    - .claude/scripts/audit-log-labels.jsonl
    - .claude/scripts/benchmark/plan-071-import-floor/README.md
    - .claude/scripts/benchmark/plan-071-import-floor/fixtures/baseline.json
    - .claude/scripts/benchmark/plan-071-import-floor/fixtures/expected_quantiles.json
    - .claude/scripts/benchmark/plan-071-import-floor/import_floor_bench.py
    - .claude/scripts/benchmark/plan-071-import-floor/run_bench.sh
    - .claude/scripts/detectors/__init__.py
    - .claude/scripts/detectors/looping.py

  WARNING — declared ACCEPTED patterns that matched nothing in this
  mode. For a GENERATED path that means the declaration is dead and
  should go; for a PRESERVE-CONTRACT path (agent-metrics, CLAUDE.md,
  MEMORY.md) it just means the template did not change between the
  two generations, which is expected. Informational, never fatal:
    - ^\.claude/agent-metrics\.md$
    - ^(CLAUDE|MEMORY)\.md$
    - ^PROTOCOL\.md$

  verdict(mode=maintainer): PARITY
--------------------------------------------------------------

##############################################################
# ceremony mode: user
##############################################################
--> [A] install.sh (working tree) --ceremony user --profile core
--> [B1] install.sh @ v1.2.0 --ceremony user --profile core
--> [B2] upgrade.sh (source: /Users/joaocanhada/canhada-labs/ceo-orchestration)
--> classify

---- parity classification (mode=user) --------------------------
  inputs:
    A (fresh install)        : /var/folders/9n/hm9srl0s1nz45_p12tj61pd80000gn/T/ceo-parity-e2e-XXXXXX.QiDivZqx2P/user/route-a/adopter  [512 files]
    B (pin v1.2.0   + upgrade): /var/folders/9n/hm9srl0s1nz45_p12tj61pd80000gn/T/ceo-parity-e2e-XXXXXX.QiDivZqx2P/user/route-b/adopter  [903 files]
    head source              : /Users/joaocanhada/canhada-labs/ceo-orchestration
    pinned source (v1.2.0)  : /var/folders/9n/hm9srl0s1nz45_p12tj61pd80000gn/T/ceo-parity-e2e-XXXXXX.QiDivZqx2P/src-v1.2.0
    normalization            : {SOURCE}, {TARGET}
  counts (UNDECLARED residue — declared paths are broken out below):
    IDENTICAL                    478
    PERSONALIZED                  31
    STALE                          0   <-- FATAL if non-zero
    MISSING_IN_B                   0   <-- FATAL if non-zero
    UNCLASSIFIED                   0   <-- FATAL if non-zero
    ONLY_IN_B                    391
    ONLY_IN_B_OUTSIDE_CLAUDE       0   <-- FATAL if non-zero
    MODE_DIFF                      0   <-- FATAL if non-zero
    ACCEPTED (declared)            3
    KNOWN-OPEN (declared)          0

  ACCEPTED divergence (by design / generated / adopter-owned):
    - .claude/.install-manifest.sha256
        derived baseline manifest — regenerated by BOTH routes (_write_baseline_manifest); it is a hash OF the set under comparison, so comparing it would be circular
    - .claude/.install-state.json
        records the invocation itself (argv, timestamps, source sha, upgrade ops) — differs by construction between a fresh install and an install+upgrade; the `ceremony` field is asserted separately below
    - .claude/settings.json
        install seeds it; upgrade does an ADDITIVE hook merge (PLAN-135 W2 H8) plus the 3-state baseline migration (PLAN-163 T5.4) and never clobbers — the two routes converge on keys, not on bytes

  VERSION assertion: no root VERSION in B (expected in --ceremony user)

  ADVISORY — upgrade shipped CURRENT framework bytes but install
  personalizes them ({{PROJECT_NAME}}-class placeholders survive an
  upgrade). Content generation is correct; presentation is not.
  31 path(s):
    - .claude/skills/core/ai-llm-orchestration/SKILL.md
    - .claude/skills/core/architecture-decisions/SKILL.md
    - .claude/skills/core/ceo-orchestration/SKILL-frontend.md
    - .claude/skills/core/ceo-orchestration/SKILL.md
    - .claude/skills/core/chaos-and-resilience/SKILL.md
    - .claude/skills/core/code-intelligence-lsp/SKILL.md
    - .claude/skills/core/code-review-checklist/SKILL.md
    - .claude/skills/core/codebase-onboarding/SKILL.md
    - .claude/skills/core/compliance-lgpd/SKILL-frontend.md
    - .claude/skills/core/compliance-lgpd/SKILL.md
    - .claude/skills/core/devops-ci-cd/SKILL.md
    - .claude/skills/core/evidence-based-qa/SKILL.md
    - .claude/skills/core/git-workflow-discipline/SKILL.md
    - .claude/skills/core/growth-and-launch/SKILL-frontend.md
    - .claude/skills/core/growth-and-launch/SKILL.md
    - .claude/skills/core/identity-and-trust-architecture/SKILL.md
    - .claude/skills/core/incident-management/SKILL.md
    - .claude/skills/core/llm-routing-and-finops/SKILL.md
    - .claude/skills/core/mcp-server-authoring/SKILL.md
    - .claude/skills/core/minimal-change-discipline/SKILL.md
    ... and 11 more

  ADVISORY — upgrade over-delivery (`cp -R` drags what install's
  selective walk never ships; ADR-155 pre-existing drift, opposite
  direction from F3). 391 path(s), first 15:
    - .claude/agents/code-reviewer.md
    - .claude/agents/devops.md
    - .claude/agents/performance-engineer.md
    - .claude/agents/qa-architect.md
    - .claude/agents/security-engineer.md
    - .claude/hooks/.coverage
    - .claude/scripts/.known_actions_floor.lock
    - .claude/scripts/audit-log-labels.jsonl
    - .claude/scripts/benchmark/plan-071-import-floor/README.md
    - .claude/scripts/benchmark/plan-071-import-floor/fixtures/baseline.json
    - .claude/scripts/benchmark/plan-071-import-floor/fixtures/expected_quantiles.json
    - .claude/scripts/benchmark/plan-071-import-floor/import_floor_bench.py
    - .claude/scripts/benchmark/plan-071-import-floor/run_bench.sh
    - .claude/scripts/detectors/__init__.py
    - .claude/scripts/detectors/looping.py

  WARNING — declared ACCEPTED patterns that matched nothing in this
  mode. For a GENERATED path that means the declaration is dead and
  should go; for a PRESERVE-CONTRACT path (agent-metrics, CLAUDE.md,
  MEMORY.md) it just means the template did not change between the
  two generations, which is expected. Informational, never fatal:
    - ^\.claude/agent-metrics\.md$
    - ^(CLAUDE|MEMORY)\.md$
    - ^\.gitignore$

  verdict(mode=user): PARITY
--------------------------------------------------------------

--------------------------------------------------------------
per-mode verdicts (0 parity / 1 fail / 2 known-open): maintainer:0 user:0

==============================================================
RESULT: PASS — install and upgrade converge on the same framework
        content in every ceremony mode tested (maintainer user).
==============================================================

2026-08-08T00:42:25.220049Z ERROR codex_core::tools::router: error=exec_command failed for `/bin/zsh -lc 'set -e
T=$(mktemp -d /tmp/fetch-test.XXXXXX)
trap '"'rm -rf \""'$T"'"' EXIT
git init -q --bare \""'$T/remote.git"
git clone -q "$T/remote.git" "$T/src"
cd "$T/src"
git -c user.name=x -c user.email=x@y commit --allow-empty -m one -q
git branch -M main
git push -q -u origin main
cd "$T"
git clone -q --no-checkout "$T/remote.git" dst
cd src
git -c user.name=x -c user.email=x@y commit --allow-empty -m two -q
git push -q
NEW=$(git rev-parse HEAD)
cd "$T/dst"
OLD=$(git rev-parse refs/remotes/origin/main)
git fetch --quiet origin main
AFTER=$(git rev-parse refs/remotes/origin/main)
FETCH=$(git rev-parse FETCH_HEAD)
printf '"'old=%s\\nnew=%s\\nafter=%s\\nfetch_head=%s\\n' \""'$OLD" "$NEW" "$AFTER" "$FETCH"'`: CreateProcess { message: "Rejected(\"`/bin/zsh -lc 'set -e\\nT=$(mktemp -d /tmp/fetch-test.XXXXXX)\\ntrap '\\\"'rm -rf \\\\\\\"\\\"'$T\\\"'\\\"' EXIT\\ngit init -q --bare \\\\\\\"\\\"'$T/remote.git\\\"\\ngit clone -q \\\"$T/remote.git\\\" \\\"$T/src\\\"\\ncd \\\"$T/src\\\"\\ngit -c user.name=x -c user.email=x@y commit --allow-empty -m one -q\\ngit branch -M main\\ngit push -q -u origin main\\ncd \\\"$T\\\"\\ngit clone -q --no-checkout \\\"$T/remote.git\\\" dst\\ncd src\\ngit -c user.name=x -c user.email=x@y commit --allow-empty -m two -q\\ngit push -q\\nNEW=$(git rev-parse HEAD)\\ncd \\\"$T/dst\\\"\\nOLD=$(git rev-parse refs/remotes/origin/main)\\ngit fetch --quiet origin main\\nAFTER=$(git rev-parse refs/remotes/origin/main)\\nFETCH=$(git rev-parse FETCH_HEAD)\\nprintf '\\\"'old=%s\\\\\\\\nnew=%s\\\\\\\\nafter=%s\\\\\\\\nfetch_head=%s\\\\\\\\n' \\\\\\\"\\\"'$OLD\\\" \\\"$NEW\\\" \\\"$AFTER\\\" \\\"$FETCH\\\"'` rejected: rm -f style commands are not permitted. Use a safer approach\")" }
exec
/bin/zsh -lc 'set -e
T=$(mktemp -d /tmp/fetch-test.XXXXXX)
git init -q --bare "$T/remote.git"
git clone -q "$T/remote.git" "$T/src"
cd "$T/src"
git -c user.name=x -c user.email=x@y commit --allow-empty -m one -q
git branch -M main
git push -q -u origin main
cd "$T"
git clone -q --no-checkout "$T/remote.git" dst
cd src
git -c user.name=x -c user.email=x@y commit --allow-empty -m two -q
git push -q
NEW=$(git rev-parse HEAD)
cd "$T/dst"
OLD=$(git rev-parse refs/remotes/origin/main)
git fetch --quiet origin main
AFTER=$(git rev-parse refs/remotes/origin/main)
FETCH=$(git rev-parse FETCH_HEAD)
printf '"'tmp=%s\\nold=%s\\nnew=%s\\nafter=%s\\nfetch_head=%s\\n' \""'$T" "$OLD" "$NEW" "$AFTER" "$FETCH"' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 254ms:
tmp=/tmp/fetch-test.0Hwq1Y
old=83d4bbbd3c2d4a4b7cdc854a9e7a98195079c116
new=269dceb17b4069e295ea47218ee2c12a727b5404
after=269dceb17b4069e295ea47218ee2c12a727b5404
fetch_head=269dceb17b4069e295ea47218ee2c12a727b5404

exec
/bin/zsh -lc "nl -ba scripts/_framework_manifest_set.sh | sed -n '1,190p'; nl -ba scripts/doctor.sh | sed -n '1,180p'; nl -ba scripts/doctor.sh | sed -n '600,680p'" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
     1	# shellcheck shell=bash
     2	# scripts/_framework_manifest_set.sh — the SINGLE canonical enumeration of
     3	# framework-owned files that an upgrade overwrites (PLAN-138 Wave C / ADR-155).
     4	#
     5	# WHY (ADR-155 decision (i)): install.sh writes a SELECTIVE list
     6	# (install_hooks_selective / install_scripts_selective / install_one
     7	# ".claude/commands" / the install_protocol_pointer at install.sh:1425) while
     8	# upgrade.sh `cp -R` drags whole directory trees (backup_and_replace at
     9	# upgrade.sh:654-679 + _refresh_protocol_pointer at :450-486). Those two
    10	# divergent enumerations are the install≠upgrade drift. This file is the ONE
    11	# source of truth, sourced by BOTH write_install_manifest (install side) and
    12	# _classify_against_baseline (upgrade side), so the recorded baseline and the
    13	# classifier walk the exact same set.
    14	#
    15	# Contract:
    16	#   * bash 3.2-safe: no associative arrays, no mapfile, no GNU-only flags.
    17	#   * Profile-aware: a `--profile core` install must NOT enumerate absent
    18	#     frontend / domain files. Callers export FMS_PROFILE_PARTS as a
    19	#     space-separated profile list (e.g. "core frontend fintech") before
    20	#     calling the functions; if unset it defaults to "core frontend".
    21	#   * Two surfaces:
    22	#       _framework_target_entries  -> the TOP-LEVEL target relpaths (mix of
    23	#                                     files + directories) install/upgrade
    24	#                                     operate on, one per line, sorted, deduped.
    25	#                                     Used for the install==upgrade set assertion.
    26	#       _framework_manifest_files  -> the EXPANDED per-file relpaths (every
    27	#                                     regular file under each target entry,
    28	#                                     directories walked), one per line, sorted.
    29	#                                     Used by the manifest writer + classifier.
    30	#   * EXCLUDES the manifest dotfile itself (.claude/.install-manifest.sha256)
    31	#     and the backup tree (.claude.bak/).
    32	#   * Includes the root PROTOCOL.md plus the .claude/{team.md,frontend-team.md,
    33	#     skills,hooks,scripts,commands,pitfalls-catalog.yaml,task-chains.yaml}
    34	#     targets, gated by profile where applicable.
    35	#   * DELIVERY-RECORD-CONDITIONAL entries (PLAN-166 F3 / ADR-155-AMEND-1):
    36	#     PROTOCOL.md, SPEC/v1 and .claude/.framework-version are enumerated ONLY
    37	#     when the caller exports the matching flag as "1":
    38	#         FMS_DELIVERED_PROTOCOL   root PROTOCOL.md pointer
    39	#         FMS_DELIVERED_SPEC       SPEC/v1 contract tree
    40	#         FMS_DELIVERED_MARKER     .claude/.framework-version marker
    41	#     The flags MUST derive from the REGISTERED DELIVERY (install.sh's
    42	#     install_one actually wrote the path this run, or the pre-upgrade
    43	#     baseline manifest already carried the record) — NEVER from the
    44	#     ceremony alone and NEVER from file presence: a target that already
    45	#     had the path (install_one EXISTS-skip) stays OUTSIDE framework
    46	#     ownership, else the baseline hashes an ADOPTER file as
    47	#     framework-owned, the update-checker trusts a stale value, and
    48	#     uninstall.sh may delete it. Unset/other values => NOT enumerated:
    49	#     the deliberate fail direction is UNDER-claiming ownership.
    50	#   * The root VERSION file is deliberately ABSENT from this enumeration:
    51	#     install_one is skip-if-exists (an adopter with its own VERSION never
    52	#     received the framework's), and upgrade.sh never touches it — see
    53	#     ADR-155-AMEND-1 (the S238/ADR-155 "verified worst case" class, C.5).
    54	#
    55	# This file is CANONICAL (added to _CANONICAL_GUARDS in check_canonical_edit.py).
    56	#
    57	# Callers must set FMS_ROOT to the tree the entries are relative to:
    58	#   - install side: FMS_ROOT="$TARGET"   (paths exist after the copy)
    59	#   - to derive the set itself the root only matters for the file-expansion
    60	#     pass (which directories actually have files); _framework_target_entries
    61	#     is root-independent (it is the static intended set).
    62	
    63	# Internal: emit the profile parts, defaulting to "core frontend".
    64	_fms_profile_parts() {
    65	  if [ -n "${FMS_PROFILE_PARTS:-}" ]; then
    66	    printf '%s\n' $FMS_PROFILE_PARTS
    67	  else
    68	    printf '%s\n' core frontend
    69	  fi
    70	}
    71	
    72	# Internal: is profile $1 present in the active profile list?
    73	_fms_has_profile() {
    74	  _fms_want="$1"
    75	  _fms_p=""
    76	  for _fms_p in $( _fms_profile_parts ); do
    77	    if [ "$_fms_p" = "$_fms_want" ]; then
    78	      return 0
    79	    fi
    80	  done
    81	  return 1
    82	}
    83	
    84	# _framework_path_excluded — PLAN-161 U2 (CF-7): the SINGLE canonical
    85	# framework-internal exclusion predicate. $1 = repo-relative path. Returns 0
    86	# (excluded) for content the framework NEVER ships to adopters — the dogfood
    87	# test/legacy trees, the two pytest-importing _lib helpers, __pycache__ dirs
    88	# and *.pyc anywhere. Also matches the bare directory paths themselves (no
    89	# trailing slash/content) so callers can test dirs. Mirrors install.sh's
    90	# structural exclusions (install_hooks_selective / install_lib_selective /
    91	# install_scripts_selective); install.sh's _lib walk now calls THIS predicate,
    92	# and upgrade.sh applies it at its three write surfaces (classified union
    93	# walk, legacy cp -R prune, manifest enumeration below).
    94	# bash 3.2-safe: pure case globs, no arrays.
    95	_framework_path_excluded() {
    96	  case "$1" in
    97	    .claude/hooks/tests|.claude/hooks/tests/*) return 0 ;;
    98	    .claude/hooks/legacy|.claude/hooks/legacy/*) return 0 ;;
    99	    .claude/scripts/tests|.claude/scripts/tests/*) return 0 ;;
   100	    .claude/hooks/_lib/tests|.claude/hooks/_lib/tests/*) return 0 ;;
   101	    .claude/hooks/_lib/test_isolation.py) return 0 ;;
   102	    .claude/hooks/_lib/testing.py) return 0 ;;
   103	    __pycache__|*/__pycache__|__pycache__/*|*/__pycache__/*) return 0 ;;
   104	    *.pyc) return 0 ;;
   105	  esac
   106	  return 1
   107	}
   108	
   109	# _framework_target_entries — the top-level target relpaths (files + dirs),
   110	# profile-aware, sorted + deduped. This is the STATIC intended set; it does not
   111	# touch disk (so install and upgrade derive an identical list regardless of
   112	# what is currently present).
   113	_framework_target_entries() {
   114	  {
   115	    # Root governance pointer (the verified S238 driver target — outside
   116	    # .claude/). PLAN-166 F3 (ADR-155-AMEND-1): CONDITIONAL on the recorded
   117	    # delivery. A `--ceremony user` install SKIPS install_protocol_pointer
   118	    # (install.sh WS4-guard-proto), and a maintainer target that ALREADY had
   119	    # its own root PROTOCOL.md was never written by the framework —
   120	    # enumerating it unconditionally records the ADOPTER's file as
   121	    # framework-owned (r13/r17).
   122	    if [ "${FMS_DELIVERED_PROTOCOL:-0}" = "1" ]; then
   123	      printf '%s\n' "PROTOCOL.md"
   124	    fi
   125	
   126	    # SPEC/v1 published contract (PLAN-166 F3): an upgrade surface as of
   127	    # v1.3.0 — same delivery-record condition (never ceremony alone, never
   128	    # file presence; r7/r17).
   129	    if [ "${FMS_DELIVERED_SPEC:-0}" = "1" ]; then
   130	      printf '%s\n' "SPEC/v1"
   131	    fi
   132	
   133	    # Framework version marker (PLAN-166 F3): a NORMAL tracked-file entry —
   134	    # present in the source tree, so the FMS_HASH_ROOT baseline rewrite
   135	    # (below) preserves it with no generated-file special-case — but
   136	    # ownership still derives from the registered delivery: a target whose
   137	    # marker pre-existed (install_one EXISTS-skip) stays adopter-owned and
   138	    # every marker-first reader keyed off this same record falls back to
   139	    # VERSION (r20).
   140	    if [ "${FMS_DELIVERED_MARKER:-0}" = "1" ]; then
   141	      printf '%s\n' ".claude/.framework-version"
   142	    fi
   143	
   144	    # Always-installed team rosters + universal catalogs.
   145	    printf '%s\n' ".claude/team.md"
   146	    printf '%s\n' ".claude/frontend-team.md"
   147	    printf '%s\n' ".claude/pitfalls-catalog.yaml"
   148	    printf '%s\n' ".claude/task-chains.yaml"
   149	
   150	    # Protocol-enforcement directory targets (always installed).
   151	    printf '%s\n' ".claude/hooks"
   152	    printf '%s\n' ".claude/scripts"
   153	    printf '%s\n' ".claude/commands"
   154	
   155	    # Skills are profile-gated.
   156	    if _fms_has_profile "core"; then
   157	      printf '%s\n' ".claude/skills/core"
   158	    fi
   159	    if _fms_has_profile "frontend"; then
   160	      printf '%s\n' ".claude/skills/frontend"
   161	    fi
   162	    # Domain profiles: any profile part that is neither core nor frontend.
   163	    for _fms_part in $( _fms_profile_parts ); do
   164	      case "$_fms_part" in
   165	        core|frontend) : ;;
   166	        *) printf '%s\n' ".claude/skills/domains/$_fms_part" ;;
   167	      esac
   168	    done
   169	  } | LC_ALL=C sort -u
   170	}
   171	
   172	# _framework_manifest_files — expand every target entry into its per-file
   173	# relpaths, relative to FMS_ROOT. Directories are walked (regular files only;
   174	# symlinks are NOT followed into — a symlinked file is emitted as its own
   175	# relpath and the manifest writer records it as a LINK record). EXCLUDES the
   176	# manifest dotfile + .claude.bak/. Sorted + deduped. Missing entries (e.g. a
   177	# profile dir absent on disk) are silently skipped — profile-awareness.
   178	_framework_manifest_files() {
   179	  _fms_root="${FMS_ROOT:-.}"
   180	  {
   181	    _framework_target_entries | while IFS= read -r _fms_entry; do
   182	      [ -n "$_fms_entry" ] || continue
   183	      _fms_abs="$_fms_root/$_fms_entry"
   184	      if [ -f "$_fms_abs" ] || [ -L "$_fms_abs" ]; then
   185	        # A plain file (or symlinked file) target.
   186	        printf '%s\n' "$_fms_entry"
   187	      elif [ -d "$_fms_abs" ]; then
   188	        # Walk the directory for regular files + symlinks. `-print` with a
   189	        # leading "./"-stripped relpath; we re-root each hit at $_fms_entry.
   190	        # bash 3.2-safe: no mapfile; pipe find into a read loop.
     1	#!/usr/bin/env bash
     2	# scripts/doctor.sh — installed-state diagnostician + selective repair
     3	# (PLAN-153 Wave B item B3)
     4	#
     5	# Diffs an installed target repo against the baseline recorded at install
     6	# time in .claude/.install-manifest.sha256 (written by install.sh
     7	# write_install_manifest / upgrade.sh via _write_baseline_manifest) and
     8	# reports, per manifest record:
     9	#
    10	#   OK        current sha256 == recorded baseline (framework-pristine)
    11	#   DRIFT     file exists, sha256 != baseline (sub-classified against the
    12	#             framework checkout: adopter-modified / baseline-stale / conflict)
    13	#   MISSING   manifest record present, file absent on disk
    14	#   ORPHAN?   file present under a framework-owned directory but NOT in the
    15	#             manifest (candidates only — NEVER removed by this script)
    16	#
    17	# --repair restores drifted/missing files SELECTIVELY from the framework
    18	# checkout this script lives in (SOURCE_DIR resolution mirrors install.sh).
    19	#
    20	# SAFETY INVARIANTS (uninstall.sh depends on these):
    21	#   * uninstall.sh removes ONLY files whose current sha256 matches the
    22	#     manifest record (uninstall.sh:227). doctor.sh preserves that property:
    23	#     a repair copies a file ONLY when the framework source still hashes to
    24	#     the recorded baseline (H_src == H_base), and verifies the restored
    25	#     content re-hashes to the baseline. Post-repair state is therefore
    26	#     exactly the recorded install state.
    27	#   * doctor.sh NEVER writes .claude/.install-manifest.sha256. If the
    28	#     framework checkout has moved past the baseline, repair is BLOCKED for
    29	#     that file and upgrade.sh (which owns baseline rewrites) is advised.
    30	#   * Adopter-modified files are NEVER overwritten without an explicit
    31	#     per-file confirmation: --yes-file <relpath> (repeatable) or an
    32	#     interactive [y/N] prompt when stdin is a TTY. Overwritten files are
    33	#     first backed up to .claude.bak/doctor-<UTC-ts>/<relpath>.
    34	#   * Orphan candidates are report-only. doctor.sh deletes nothing, ever.
    35	#
    36	# Usage:
    37	#   ./doctor.sh <target-repo-path> [options]
    38	#
    39	# Options:
    40	#   --repair             Restore drifted/missing framework files (selective)
    41	#   --dry-run            With --repair: print what WOULD be restored, write
    42	#                        nothing. (Without --repair, report-only is already
    43	#                        the default posture.)
    44	#   --yes-file <rel>     Pre-approve restore of ONE adopter-modified file
    45	#                        (repeatable; exact manifest relpath)
    46	#   --profile <list>     Comma-separated profile list for the orphan scan
    47	#                        (default: auto-detect core,frontend + installed
    48	#                        domain dirs under .claude/skills/domains/)
    49	#   --strict-orphans     Orphan candidates also drive exit code 1
    50	#   --no-orphan-scan     Skip the orphan scan
    51	#   --verbose            Also print OK lines (default: findings only)
    52	#   -h, --help           Show this help
    53	#
    54	# Exit codes:
    55	#   0  clean (no unresolved drift/missing; orphans ignored unless --strict-orphans)
    56	#   1  findings remain after the run (drift/missing, or orphans under --strict-orphans)
    57	#   2  usage error / infrastructure problem (bad args, no manifest, no hasher)
    58	#
    59	# bash 3.2-safe (macOS /bin/bash): no mapfile, no associative arrays.
    60	
    61	# Bash portability guard (mirrors uninstall.sh:30-38).
    62	if [ -z "${BASH_VERSINFO:-}" ]; then
    63	  echo "ERROR: doctor.sh requires bash" >&2
    64	  exit 2
    65	fi
    66	if [ "${BASH_VERSINFO[0]}" -lt 3 ] || \
    67	   { [ "${BASH_VERSINFO[0]}" -eq 3 ] && [ "${BASH_VERSINFO[1]}" -lt 2 ]; }; then
    68	  echo "ERROR: doctor.sh requires bash >= 3.2 (detected ${BASH_VERSION})" >&2
    69	  exit 2
    70	fi
    71	
    72	set -euo pipefail
    73	
    74	# ---------------------------------------------------------------------------
    75	# Argument parsing
    76	# ---------------------------------------------------------------------------
    77	TARGET=""
    78	REPAIR=0
    79	DRY_RUN=0
    80	PROFILE=""
    81	STRICT_ORPHANS=0
    82	NO_ORPHAN_SCAN=0
    83	VERBOSE=0
    84	YES_FILES="
    85	"   # newline-delimited set of pre-approved relpaths (bash-3.2 "set" idiom)
    86	
    87	usage() {
    88	  # Header spans line 2 .. the "bash 3.2-safe" sentinel line (keep in sync).
    89	  sed -n '2,59p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
    90	}
    91	
    92	while [ $# -gt 0 ]; do
    93	  case "$1" in
    94	    --repair)          REPAIR=1; shift ;;
    95	    --dry-run)         DRY_RUN=1; shift ;;
    96	    --yes-file)
    97	      if [ -z "${2:-}" ]; then
    98	        echo "ERROR: --yes-file requires a relpath argument" >&2
    99	        exit 2
   100	      fi
   101	      YES_FILES="${YES_FILES}${2}
   102	"
   103	      shift 2 ;;
   104	    --yes-file=*)
   105	      YES_FILES="${YES_FILES}${1#--yes-file=}
   106	"
   107	      shift ;;
   108	    --profile)
   109	      if [ -z "${2:-}" ]; then
   110	        echo "ERROR: --profile requires a comma-separated list" >&2
   111	        exit 2
   112	      fi
   113	      PROFILE="$2"; shift 2 ;;
   114	    --profile=*)       PROFILE="${1#--profile=}"; shift ;;
   115	    --strict-orphans)  STRICT_ORPHANS=1; shift ;;
   116	    --no-orphan-scan)  NO_ORPHAN_SCAN=1; shift ;;
   117	    --verbose)         VERBOSE=1; shift ;;
   118	    -h|--help)         usage; exit 0 ;;
   119	    -*)
   120	      echo "ERROR: unknown option: $1" >&2
   121	      echo "Usage: $0 <target-repo-path> [--repair] [--dry-run] [--yes-file <rel>]..." >&2
   122	      exit 2 ;;
   123	    *)
   124	      if [ -n "$TARGET" ]; then
   125	        echo "ERROR: multiple target paths given ('$TARGET' and '$1')" >&2
   126	        exit 2
   127	      fi
   128	      TARGET="$1"; shift ;;
   129	  esac
   130	done
   131	
   132	if [ -z "$TARGET" ]; then
   133	  echo "Usage: $0 <target-repo-path> [--repair] [--dry-run] [--yes-file <rel>]..." >&2
   134	  exit 2
   135	fi
   136	if [ ! -d "$TARGET" ]; then
   137	  echo "ERROR: target directory does not exist: $TARGET" >&2
   138	  exit 2
   139	fi
   140	TARGET="$( cd "$TARGET" && pwd )"
   141	
   142	# ---------------------------------------------------------------------------
   143	# Resolve SCRIPT_DIR / SOURCE_DIR (mirrors install.sh:178-204 so doctor's
   144	# restore source is the SAME framework checkout install.sh would copy from,
   145	# including when invoked via a symlink).
   146	# ---------------------------------------------------------------------------
   147	_resolve_script_path() {
   148	  local src="$1"
   149	  if command -v readlink >/dev/null 2>&1; then
   150	    local resolved
   151	    if resolved="$(readlink -f "$src" 2>/dev/null)" && [ -n "$resolved" ]; then
   152	      printf '%s\n' "$resolved"
   153	      return 0
   154	    fi
   155	    while [ -L "$src" ]; do
   156	      local link_target
   157	      link_target="$(readlink "$src")"
   158	      case "$link_target" in
   159	        /*) src="$link_target" ;;
   160	        *)  src="$(cd "$(dirname "$src")" && pwd)/$link_target" ;;
   161	      esac
   162	    done
   163	  fi
   164	  printf '%s\n' "$src"
   165	}
   166	
   167	SCRIPT_SRC="$(_resolve_script_path "${BASH_SOURCE[0]}")"
   168	SCRIPT_DIR="$( cd "$( dirname "$SCRIPT_SRC" )" && pwd )"
   169	SOURCE_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
   170	
   171	# _hash_lib.sh is REQUIRED — without a portable hasher every verdict here
   172	# would be a guess. Fail-closed to rc=2 (infra), matching the exit contract.
   173	if [ ! -f "$SCRIPT_DIR/_hash_lib.sh" ]; then
   174	  echo "ERROR: $SCRIPT_DIR/_hash_lib.sh not found — partial checkout? doctor cannot hash." >&2
   175	  exit 2
   176	fi
   177	# shellcheck source=scripts/_hash_lib.sh
   178	. "$SCRIPT_DIR/_hash_lib.sh"
   179	if ! _hash_resolver >/dev/null 2>&1; then
   180	  echo "ERROR: neither shasum nor sha256sum found on PATH — doctor cannot hash." >&2
   600	# ---------------------------------------------------------------------------
   601	if [ "$NO_ORPHAN_SCAN" -eq 0 ]; then
   602	  if [ "$HAVE_FMS" -eq 1 ]; then
   603	    if [ -n "$PROFILE" ]; then
   604	      PROFILE_PARTS_STR="$( printf '%s' "$PROFILE" | tr ',' ' ' )"
   605	    else
   606	      # Auto-detect: core + frontend (absent dirs are skipped by the
   607	      # enumerator) + every installed domain dir.
   608	      PROFILE_PARTS_STR="core frontend"
   609	      if [ -d "$TARGET/.claude/skills/domains" ]; then
   610	        for d in "$TARGET/.claude/skills/domains"/*/; do
   611	          [ -d "$d" ] || continue
   612	          PROFILE_PARTS_STR="$PROFILE_PARTS_STR $( basename "$d" )"
   613	        done
   614	      fi
   615	    fi
   616	    # PLAN-166 F3 (ADR-155-AMEND-1): the FMS entries for PROTOCOL.md,
   617	    # SPEC/v1 and .claude/.framework-version are CONDITIONAL on the
   618	    # recorded delivery. doctor resolves the flags from the SAME record
   619	    # the writers use — the sanitized baseline manifest — NEVER from the
   620	    # ceremony: ceremony-only resolution would re-include paths a
   621	    # `--ceremony user` install skipped and --strict-orphans would flag
   622	    # the ADOPTER's own SPEC/PROTOCOL files as orphans (r19), while a
   623	    # blanket maintainer default would do the same and a blanket user
   624	    # default would hide a delivered SPEC from a maintainer (r9 P2).
   625	    _dr_delivered() {  # $1 = ERE fragment anchored at the relpath position
   626	      grep -Eq "^([0-9a-f]{64}|LINK)  $1" "$SANITIZED" 2>/dev/null
   627	    }
   628	    # `SPEC/v1(/|  |$)` and not a bare `SPEC/v1/`: a --mode link install
   629	    # records the whole tree as ONE directory symlink (`LINK  SPEC/v1
   630	    # <target>`, no trailing slash) — the same `(  |$)` treatment the
   631	    # PROTOCOL/marker fragments below already have (re-pass closure; family
   632	    # swept with upgrade.sh _baseline_has_spec_record).
   633	    if _dr_delivered 'SPEC/v1(/|  |$)'; then
   634	      FMS_DELIVERED_SPEC=1
   635	    else
   636	      FMS_DELIVERED_SPEC=0
   637	    fi
   638	    if _dr_delivered 'PROTOCOL\.md(  |$)'; then
   639	      FMS_DELIVERED_PROTOCOL=1
   640	    else
   641	      FMS_DELIVERED_PROTOCOL=0
   642	    fi
   643	    if _dr_delivered '\.claude/\.framework-version(  |$)'; then
   644	      FMS_DELIVERED_MARKER=1
   645	    else
   646	      FMS_DELIVERED_MARKER=0
   647	    fi
   648	    export FMS_DELIVERED_SPEC FMS_DELIVERED_PROTOCOL FMS_DELIVERED_MARKER
   649	    export FMS_ROOT="$TARGET"
   650	    export FMS_PROFILE_PARTS="$PROFILE_PARTS_STR"
   651	    _framework_manifest_files > "$WORKDIR/enumerated" 2>/dev/null || : > "$WORKDIR/enumerated"
   652	    unset FMS_ROOT FMS_PROFILE_PARTS
   653	    unset FMS_DELIVERED_SPEC FMS_DELIVERED_PROTOCOL FMS_DELIVERED_MARKER
   654	    # Manifest relpaths (both record kinds).
   655	    awk '{
   656	      idx = index($0, "  ");
   657	      if (idx == 0) next;
   658	      d = substr($0, 1, idx - 1);
   659	      rest = substr($0, idx + 2);
   660	      if (d == "LINK") { j = index(rest, "  "); if (j > 0) rest = substr(rest, 1, j - 1) }
   661	      print rest;
   662	    }' "$SANITIZED" | LC_ALL=C sort -u > "$WORKDIR/manifest-rels"
   663	    LC_ALL=C sort -u "$WORKDIR/enumerated" > "$WORKDIR/enumerated.sorted"
   664	    comm -23 "$WORKDIR/enumerated.sorted" "$WORKDIR/manifest-rels" > "$WORKDIR/orphans" || : > "$WORKDIR/orphans"
   665	    if [ -s "$WORKDIR/orphans" ]; then
   666	      _log ""
   667	      _log "==> Orphan candidates (present in framework-owned dirs, absent from manifest;"
   668	      _log "    possibly adopter-authored — REPORT-ONLY, nothing is removed):"
   669	      while IFS= read -r orel; do
   670	        [ -n "$orel" ] || continue
   671	        ORPHAN_COUNT=$((ORPHAN_COUNT + 1))
   672	        _log "    ORPHAN?: $orel"
   673	      done < "$WORKDIR/orphans"
   674	    fi
   675	  else
   676	    _log "    NOTE: orphan scan skipped — _framework_manifest_set.sh not found beside doctor.sh"
   677	  fi
   678	fi
   679	
   680	# ---------------------------------------------------------------------------

exec
/bin/zsh -lc 'git diff --no-ext-diff --unified=12 -- "INSTALL.md"' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
diff --git a/INSTALL.md b/INSTALL.md
index e9b7471..480ef7f 100644
--- a/INSTALL.md
+++ b/INSTALL.md
@@ -578,60 +578,97 @@ versions:
   block/allow decision schema, fail-open rule, env-var contract).
 - Plus per-subsystem schemas: ADR template, debate fixture format,
   red-team-corpus, secret-patterns-exchange, etc.
 
 After install, `ls TARGET/SPEC/v1/*.md` should list all schemas.
 The schemas are **read-only contracts** — adopters that need to
 customize behavior do so via `settings.json` env-var overrides
 (documented in `docs/GOVERNANCE.md`), never by editing the schema
 files. A version bump in `VERSION` carries the SemVer guarantee
 that minor/patch changes do NOT break the schemas; major bumps
 publish a new `SPEC/v2/` alongside.
 
-To verify what version you installed:
+To verify what framework version a target is running:
 
 ```bash
-cat TARGET/VERSION
-# Example output: 1.18.0
+cat TARGET/.claude/.framework-version   # preferred — refreshed on every upgrade
+# Example output: 1.3.0
+cat TARGET/VERSION                      # fallback (pre-v1.3.0 installs)
 ```
 
-The `VERSION` file matches the git tag of the source framework
-checkout at install time. Use it as a forensic anchor when an
-adopter reports a bug: ask for the `VERSION` value first.
+Prefer `.claude/.framework-version` as the forensic anchor when an
+adopter reports a bug. The root `VERSION` file matches the git tag of
+the source framework checkout **at install time only**: `upgrade.sh`
+deliberately never touches it (an adopter repo may have its own
+`VERSION`, and taking it over is the S238/ADR-155 clobber class — see
+`ADR-155-AMEND-1`), so on an upgraded install `VERSION` reports the
+ORIGINAL install version, not the current one. The marker is refreshed
+on every upgrade and is cross-checked against `VERSION` in every
+framework release; fall back to `VERSION` only on pre-v1.3.0 installs
+that have not upgraded yet.
 
 ---
 
 ## Upgrade flow
 
 To refresh framework-derived content in an existing adopter install
 (without touching user-customized files), use `scripts/upgrade.sh`:
 
 ```bash
 cd /path/to/ceo-orchestration   # source framework checkout
 git pull                         # get the latest framework
 bash scripts/upgrade.sh /path/to/your/project --pin v1.3.0
 ```
 
 What gets refreshed:
 
 - `.claude/team.md`, `.claude/frontend-team.md`
 - `.claude/skills/`, `.claude/hooks/`, `.claude/scripts/`,
   `.claude/commands/`
 - `.claude/pitfalls-catalog.yaml`, `.claude/task-chains.yaml`
-- `PROTOCOL.md` pointer
+- `PROTOCOL.md` pointer (skipped on `--ceremony user` installs — a user
+  install never creates root files)
+- `SPEC/v1/` — **forced route** (skipped on `--ceremony user` installs):
+  the SPEC is the published compliance contract, so a local edit is a
+  *fork of the contract*, not a customization — a framework-owned
+  `SPEC/v1` is backed up to `.claude.bak/<timestamp>/SPEC/v1` and
+  replaced wholesale. Ownership follows the recorded delivery (the
+  ADR-155 baseline manifest); a pre-existing `SPEC/v1` with no delivery
+  record is byte-compared against the pristine SPECs shipped at v1.2.0
+  and earlier — a match refreshes it, anything else is preserved in
+  place with a named WARNING (ADR-155-AMEND-1).
+- `.claude/.framework-version` — the framework version marker, rewritten
+  to the source version on every upgrade (this is what
+  `check-framework-updates.sh` and forensic triage read post-upgrade).
 
 What is **NOT** touched (user data):
 
 - `CLAUDE.md`, `MEMORY.md`
 - `.claude/agent-metrics.md`
+- `VERSION` (root) — **deliberately**: `install.sh` is skip-if-exists,
+  so on an adopter repo with its own `VERSION` the framework never
+  wrote there, and an upgrade overwrite would take the adopter's file
+  (the S238/ADR-155 class). The root `VERSION` is an install-time
+  snapshot forever; the current framework version lives in
+  `.claude/.framework-version`. Do not "fix" this asymmetry — see
+  `ADR-155-AMEND-1`.
+
+Ceremony on upgrade: `upgrade.sh` reads the recorded install ceremony
+from `.claude/.install-state.json` with a dedicated reader that runs
+even under `--no-replay`. **Installs without a readable
+`.install-state.json` (all pre-Wave-B installs) are treated as
+`maintainer` on upgrade** — that is the fail-open, pre-existing
+behavior; if your install was `--ceremony user` and predates the state
+file, re-run `install.sh --ceremony user` once so the ceremony is
+recorded before upgrading.
 
 `.claude/settings.json` is a special case since v1.2.0: `upgrade.sh` runs a
 3-state per-leaf-key **baseline migration** on it (e.g. the pair-rail
 registration-timeout cap 150 → 210 s, ADR-110-AMEND-2). A key is only
 changed when it still holds the old framework default — operator-chosen
 values are preserved — and the pre-migration file is copied to
 `.claude.bak/<timestamp>/` first.
 
 Run `bash scripts/upgrade.sh --help` for the full flag list. Key
 flags:
 
 - `--pin <tag>` — pin source to a specific tag/SHA (refuses if

exec
/bin/zsh -lc 'git diff --no-ext-diff --unified=12 -- "README.md"' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
diff --git a/README.md b/README.md
index a247fe0..e04e721 100644
--- a/README.md
+++ b/README.md
@@ -47,25 +47,25 @@ When installed, the framework registers a set of [Claude Code hooks](https://doc
 
 ## What's in the box
 
 All counts below are verifiable from a clean checkout (see *Verifying the numbers*).
 
 | Component | Count | Notes |
 |---|---|---|
 | Skill checklists | **166** | 42 core + 8 frontend + 116 domain |
 | Hook scripts (on disk) | **57** | Python entrypoints under `.claude/hooks/` |
 | Hooks wired in `settings.json` | **46** | distinct scripts, 48 event registrations |
 | Shared library modules | **68** | stdlib-only, under `.claude/hooks/_lib/` (excluding the package `__init__.py`) |
 | Slash commands | **27** | under `.claude/commands/` |
-| Architecture decision records | **188** | under `.claude/adr/` |
+| Architecture decision records | **189** | under `.claude/adr/` |
 | Tests | **~14,000 cases** | reported by `pytest --collect-only` across the hook, script, and conformance suites |
 
 The gap between **57 on disk** and **46 wired** is benign: several non-event modules are activated through in-process dispatch (invoked by other hooks) rather than by a direct `settings.json` event registration.
 
 **Runtime dependencies: none.** Hooks and scripts are Python ≥ 3.9, **standard library only** — zero third-party runtime packages. See [`SBOM.md`](SBOM.md). (Development and CI use third-party test tooling such as pytest; the installed runtime does not.)
 
 There is also a **published compliance contract** under `SPEC/v1/` (32 files — 28 `*.schema.md` plus contract docs, version-pinned), a TLA+ specification of the core circuit-breaker state machine, a conformance harness, and a local read-only audit dashboard.
 
 ---
 
 ## Which skill should I use?
 
@@ -174,25 +174,25 @@ To remove the framework cleanly:
 /path/to/ceo-orchestration/scripts/uninstall.sh /path/to/your-app
 ```
 
 ---
 
 ## Verifying the numbers
 
 Don't take the table on faith. From a clean checkout:
 
 ```bash
 find .claude/skills -name SKILL.md | wc -l        # 166 skills
 ls .claude/commands/*.md | wc -l                  # 27 slash commands
-ls .claude/adr | grep -c '^ADR-'                  # 188 ADRs
+ls .claude/adr | grep -c '^ADR-'                  # 189 ADRs
 python3 -m pytest --collect-only -q | tail -1     # ~14,000 collected cases
 ```
 
 ---
 
 ## Risks and what this is *not*
 
 Intellectual honesty is the point, so the caveats are first-class:
 
 - **Bus factor of one.** This is built and maintained by a single maintainer. There is no team behind it, no SLA, and no guarantee of continuity. Evaluate it accordingly.
 - **Same-vendor reviewer caveat.** The cross-model pair-rail reduces single-model blind spots, but the reviewer is still a large language model and can share failure modes with the model under review. It is defense-in-depth, not an independent oracle.
 - **Codex is not bundled — the pair-rail is inert until you install it.** The cross-model review rail invokes the [Codex CLI](https://github.com/openai/codex), which is **not** shipped with this framework. On a fresh install with no Codex present, the pair-rail **fails open and contributes zero review** — protected-path edits still pass the GPG ceremony, but no second model looks at them. You only get the cross-model rung after installing Codex separately. See [`docs/HONEST-LIMITATIONS.md`](docs/HONEST-LIMITATIONS.md) and ADR-145.

exec
/bin/zsh -lc 'git diff --no-ext-diff --unified=12 -- "README.pt-BR.md"' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
diff --git a/README.pt-BR.md b/README.pt-BR.md
index 344f556..3c1c28c 100644
--- a/README.pt-BR.md
+++ b/README.pt-BR.md
@@ -45,25 +45,25 @@ Quando instalado, o framework registra um conjunto de [hooks do Claude Code](htt
 
 ## O que vem na caixa
 
 Todas as contagens abaixo são verificáveis a partir de um checkout limpo (veja *Verificando os números*).
 
 | Componente | Contagem | Notas |
 |---|---|---|
 | Checklists de skills | **166** | 42 core + 8 frontend + 116 de domínio |
 | Scripts de hook (em disco) | **57** | entrypoints Python em `.claude/hooks/` |
 | Hooks ligados em `settings.json` | **46** | scripts distintos, 48 registros de evento |
 | Módulos de biblioteca compartilhada | **68** | apenas stdlib, em `.claude/hooks/_lib/` (excluindo o `__init__.py` do pacote) |
 | Slash commands | **27** | em `.claude/commands/` |
-| Architecture decision records | **188** | em `.claude/adr/` |
+| Architecture decision records | **189** | em `.claude/adr/` |
 | Testes | **~14.000 casos** | reportados por `pytest --collect-only` nas suítes de hook, script e conformidade |
 
 A diferença entre **57 em disco** e **46 ligados** é benigna: vários módulos que não respondem a eventos são ativados via dispatch in-process (invocados por outros hooks), e não por um registro de evento direto em `settings.json`.
 
 **Dependências de runtime: nenhuma.** Hooks e scripts são Python ≥ 3.9, **apenas biblioteca padrão** — zero pacotes de terceiros em runtime. Veja [`SBOM.md`](SBOM.md). (Desenvolvimento e CI usam ferramentas de teste de terceiros, como o pytest; o runtime instalado não usa.)
 
 Há também um **contrato de conformidade publicado** em `SPEC/v1/` (32 arquivos — 28 `*.schema.md` mais os docs de contrato, com versão fixada), uma especificação TLA+ da máquina de estados central do circuit-breaker, um harness de conformidade e um dashboard de auditoria local somente leitura.
 
 ---
 
 ## Qual skill devo usar?
 
@@ -154,25 +154,25 @@ Para remover o framework de forma limpa:
 /path/to/ceo-orchestration/scripts/uninstall.sh /path/to/your-app
 ```
 
 ---
 
 ## Verificando os números
 
 Não acredite na tabela por fé. A partir de um checkout limpo:
 
 ```bash
 find .claude/skills -name SKILL.md | wc -l        # 166 skills
 ls .claude/commands/*.md | wc -l                  # 27 slash commands
-ls .claude/adr | grep -c '^ADR-'                  # 188 ADRs
+ls .claude/adr | grep -c '^ADR-'                  # 189 ADRs
 python3 -m pytest --collect-only -q | tail -1     # ~14.000 casos coletados
 ```
 
 ---
 
 ## Riscos e o que isto *não* é
 
 A honestidade intelectual é o ponto central, então as ressalvas são de primeira classe:
 
 - **Fator-ônibus de um.** Isto é construído e mantido por um único mantenedor. Não há um time por trás, nem SLA, nem garantia de continuidade. Avalie-o de acordo.
 - **Ressalva do revisor do mesmo fornecedor.** O pair-rail cross-model reduz os pontos cegos de modelo único, mas o revisor ainda é um modelo de linguagem grande e pode compartilhar modos de falha com o modelo sob revisão. É defesa em profundidade, não um oráculo independente.
 - **O Codex não vem incluído — o pair-rail fica inerte até você instalá-lo.** O trilho de revisão cross-model invoca a [CLI do Codex](https://github.com/openai/codex), que **não** é distribuída com este framework. Em uma instalação nova, sem o Codex presente, o pair-rail **falha em aberto e não contribui com nenhuma revisão** — as edições em caminhos protegidos ainda passam pela cerimônia GPG, mas nenhum segundo modelo as examina. Você só ganha o degrau cross-model depois de instalar o Codex separadamente. Veja [`docs/HONEST-LIMITATIONS.md`](docs/HONEST-LIMITATIONS.md) e o ADR-145.

exec
/bin/zsh -lc 'git diff --no-ext-diff --unified=12 -- "RELEASE.md"' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
diff --git a/RELEASE.md b/RELEASE.md
index ccae549..4bc6476 100644
--- a/RELEASE.md
+++ b/RELEASE.md
@@ -7,25 +7,25 @@
 > retracted), **não há mais cadência formal de release por
 > calendário**: a tag sai quando o Owner decide, sem o antigo hold
 > de 7 dias e sem cron de revisão. O `release.yml` ainda exige a
 > janela mecânica de re-pass do Codex de 24h (ADR-103) entre a tag
 > `-rc.N` e a GA. CHANGELOG.md é o registro autoritativo de cadência
 > observável.
 >
 > **Para ver a versão atual e changelog:**
 >
 > - `cat VERSION` — versão semântica corrente (`1.0.0`)
 > - `git tag -l 'v*' --sort=-creatordate | head -5` — últimas 5 tags
 > - `CHANGELOG.md` — entries por versão
-> - `.github/workflows/release.yml` — release-gate + publish-release (29 steps,
+> - `.github/workflows/release.yml` — release-gate + publish-release (31 steps,
 >   GPG-signed tags)
 >
 > Histórico preservado abaixo apenas como referência de como o
 > framework operava em v1.0.0-rc.1.
 
 > Guia passo-a-passo para o Owner tagear `v1.0.0-rc.1` e, após
 > 7 dias de hold, promover para `v1.0.0` estável. Todos os comandos
 > são copy-paste ready (absolutos, sem placeholder).
 
 ## Pré-requisitos
 
 Antes de começar, confirme:

exec
/bin/zsh -lc 'git diff --no-ext-diff --unified=12 -- "docs/ARCHITECTURE.md"' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
diff --git a/docs/ARCHITECTURE.md b/docs/ARCHITECTURE.md
index af2f07e..d59fb70 100644
--- a/docs/ARCHITECTURE.md
+++ b/docs/ARCHITECTURE.md
@@ -44,40 +44,40 @@ ceo-orchestration/
     ├── settings.json               # hook registrations for this repo (dogfood)
     ├── hooks/
     │   ├── _python-hook.sh         # resolves newest Python ≥ 3.9, fails with guidance
     │   ├── _lib/                   # 68 stdlib-only shared modules (140 recursive)
     │   ├── *.py                    # 57 hook scripts on disk
     │   └── tests/                  # hook unit tests
     ├── scripts/                    # protocol toolkit (validate, inject, audit-query, …)
     ├── commands/                   # 27 slash commands (*.md)
     ├── skills/
     │   ├── core/                   # 42 universal backend skills
     │   ├── frontend/               # 8 universal frontend skills
     │   └── domains/                # 116 skills across 33 domain profiles
-    ├── adr/                        # 188 architecture decision records
+    ├── adr/                        # 189 architecture decision records
     └── plans/                      # plan schemas + per-plan working files
 ```
 
 The counts above are verifiable from a clean checkout. Don't take them on
 faith — run the commands:
 
 | Component          | Count                        | Verify command                                            |
 |--------------------|------------------------------|-----------------------------------------------------------|
 | Skills             | 166                          | `find .claude/skills -name SKILL.md \| wc -l`             |
 | └ core / frontend / domain | 42 / 8 / 116         | `find .claude/skills/core -name SKILL.md \| wc -l` (etc.) |
 | Hook scripts       | 57 on disk                   | `ls .claude/hooks/*.py \| wc -l`                          |
 | Hook registrations | 46 wired into `settings.json`| (parse the `hooks` block of `.claude/settings.json`)      |
 | `_lib` modules     | 68 top-level (140 recursive) | `ls .claude/hooks/_lib/*.py \| grep -v __init__ \| wc -l` |
 | Slash commands     | 27                           | `ls .claude/commands/*.md \| wc -l`                       |
-| ADRs               | 188                          | `ls .claude/adr/ADR-*.md \| wc -l`                        |
+| ADRs               | 189                          | `ls .claude/adr/ADR-*.md \| wc -l`                        |
 | SPEC/v1 files      | 32 (28 `*.schema.md`)        | `ls SPEC/v1/*.md \| wc -l`                                |
 | Test files         | ~730                         | `git ls-files '*test_*.py' '*_test.py' \| wc -l`          |
 | Collected cases    | ~14k parametrized cases      | `make test-collect` (pytest `--collect-only`)             |
 
 > **On the "57 vs 46" hook gap.** 57 is the number of hook *scripts* present in
 > `.claude/hooks/`. 46 is the number of those scripts *wired into* this repo's
 > `.claude/settings.json` (across 48 event registrations — one script can fire on
 > more than one event). The difference is real and intentional: some scripts are
 > opt-in, stack-specific, superseded, or invoked indirectly by other hooks. Both
 > numbers are reported here rather than conflated into one impressive figure.
 
 > **On "~14k tests."** That is the count of *collected, parametrized* cases
@@ -225,25 +225,25 @@ the honest *Risks / Not-For* caveat in the [README](../README.md).
 `SPEC/v1/` is the published, versioned compliance contract (SemVer; currently
 v1.3.0, aligned with the repo `VERSION`). It contains 28 schema files defining
 the stable interfaces an adopter can pin to — among them `audit-log.schema.md`,
 `hook-io.schema.md`, `plan.schema.md`, `debate.schema.md`,
 `skill-frontmatter.schema.md`, `tier-policy.schema.md`, and
 `install-cli.md` (which versions the `install.sh` CLI flags as an API).
 
 The SPEC matters because it separates *what the framework promises* from *how
 this repository happens to implement it today*. An install pins a SPEC version;
 internal refactors that keep the schemas stable do not break adopters.
 
 Decisions that shape these contracts are recorded as Architecture Decision
-Records in `.claude/adr/` (188 to date), with a documented lifecycle
+Records in `.claude/adr/` (189 to date), with a documented lifecycle
 (PROPOSED → ACCEPTED, plus SUPERSEDED / RETRACTED).[^adr]
 
 The repository also includes a TLA+ specification of the core state machine
 under `docs/formal-verification/` (the breaker, plan-lifecycle, and
 debate-convergence models). A CI job (`formal-verify.yml`) downloads a
 SHA-pinned TLC toolchain and model-checks these specs on a weekly schedule and
 on spec changes. Be precise about what that buys you: the TLC job is
 **advisory-only — it does not block merges**, and the project therefore does
 **not** claim to be "formally verified." The specs are a design aid and a
 regression tripwire, not a proof gate.
 
 ---

exec
/bin/zsh -lc 'git diff --no-ext-diff --unified=12 -- "docs/CTO-GUIDE.md"' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
diff --git a/docs/CTO-GUIDE.md b/docs/CTO-GUIDE.md
index 812a4aa..b0e59bc 100644
--- a/docs/CTO-GUIDE.md
+++ b/docs/CTO-GUIDE.md
@@ -32,25 +32,25 @@ replacement. It is a protocol shipped as files.
 ---
 
 ## 2. What ships in the box
 
 Reproduce the table below via the commands in the right column. Counts
 refresh every release; if a number drifts, file an issue — that is a
 documentation bug.
 
 | Artifact | Count | Verify |
 |---|---|---|
 | Python tests collected | ~14,000 | `make test-collect` (or `python3 -m pytest --collect-only -q \| tail -1` — pytest.ini pins the testpath roots) |
 | Test files | ~730 | `git ls-files '*test_*.py' '*_test.py' \| wc -l` |
-| ADRs shipped | 188 | `ls .claude/adr/ADR-*.md \| wc -l` |
+| ADRs shipped | 189 | `ls .claude/adr/ADR-*.md \| wc -l` |
 | SPEC/v1 files | 32 (28 `*.schema.md`) | `ls SPEC/v1/*.md \| wc -l` |
 | Workflows | 21 | `ls .github/workflows/*.yml \| wc -l` |
 | GitHub Actions SHA-pinned refs | every `uses:` pinned | `grep -rEc 'uses: [^#]+@(v[0-9]+\|main\|master\|latest)\s*$' .github/workflows/*` — must be 0 everywhere |
 | Skills | 166 (42 core + 8 frontend + 116 domain) | `find .claude/skills -name SKILL.md \| wc -l` |
 | Hooks | 57 .py on disk; 46 wired into `settings.json` (48 event registrations) | `ls .claude/hooks/*.py \| wc -l` |
 | `_lib/` stdlib-only modules | 68 | `ls .claude/hooks/_lib/*.py \| grep -v __init__ \| wc -l` |
 | Runtime 3rd-party deps | 0 | see `SBOM.md` §1 |
 
 Secondary (not strictly reproducible via one-liner, but derivable):
 
 - **Mutation conformance:** 85 mutation fixtures under
   `tests/formal_verification/mutation_fixtures/`. The contract is the
@@ -100,25 +100,25 @@ grep -rE 'uses:.*@[a-f0-9]{40}' .github/workflows/ | wc -l
 # No network call inside hooks
 grep -rE 'urllib|requests|httpx|socket\.' .claude/hooks/check_*.py
 # Empty. (audit_log.py uses socket only for loopback dashboard.)
 ```
 
 ### 3.4 Governance surface — 5 minutes
 
 ```bash
 # Every PreToolUse + PostToolUse hook
 ls .claude/hooks/check_*.py .claude/hooks/audit_log.py
 
 # Every ADR title
-grep -h '^# ADR-' .claude/adr/ADR-*.md | sort             # 188 ADRs on disk
+grep -h '^# ADR-' .claude/adr/ADR-*.md | sort             # 189 ADRs on disk
 
 # SPEC/v1 published contract
 ls SPEC/v1/*.schema.md                                    # 28 schema files
 ```
 
 ### 3.5 Remediation transparency — 5 minutes
 
 Read `.claude/plans/PLAN-152-v1-0-1-hardening-sweep.md` — the
 post-v1.0.0 self-audit sweep: 41 confirmed findings (32 fix / 6 accept
 / 3 defer), P0 security fail-opens included, with wave-by-wave
 remediation tracked in-tree. Then read
 `.claude/plans/PLAN-143-repo-hygiene-debt.md` — repo debt collected

exec
/bin/zsh -lc 'git diff --no-ext-diff --unified=12 -- "docs/FAQ.md"' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
diff --git a/docs/FAQ.md b/docs/FAQ.md
index e0e628f..ad3ad62 100644
--- a/docs/FAQ.md
+++ b/docs/FAQ.md
@@ -96,25 +96,25 @@ A SHA-pinned manifest tracks every file the installer placed, so removal is clea
 
 It removes the governance hooks, scripts, and skill profiles it added, leaving your application code untouched. The local audit log lives outside the repo and is yours to keep or delete.
 
 ---
 
 ### 11. What exactly do I get — how do I verify the numbers?
 
 Don't take the README table on faith. From a clean checkout:
 
 ```bash
 find .claude/skills -name SKILL.md | wc -l        # 166 skills (42 core + 8 frontend + 116 domain)
 ls .claude/commands/*.md | wc -l                  # 27 slash commands
-ls .claude/adr | grep -c '^ADR-'                  # 188 ADRs
+ls .claude/adr | grep -c '^ADR-'                  # 189 ADRs
 python3 -m pytest --collect-only -q | tail -1     # ~14,000 collected cases
 ```
 
 Every count in the README is reproducible this way. See the README "Verifying the numbers" section.
 
 ---
 
 ### 12. Does the framework let me run overnight?
 
 Yes — deliberately, per machine, never by default. The shipped posture is fail-closed (`permissions.defaultMode: "manual"`), so sessions ask before acting. To arm an unattended run on your machine, `/night-mode on` writes `permissions.defaultMode: "acceptEdits"` into the gitignored `.claude/settings.local.json`; the **next** session starts in that mode, `/ceo-boot` shows an advisory banner while it's active, and `/night-mode off` restores the ratified posture. The tracked settings and published defaults never change. For a single fully-unattended session there is an explicit, ephemeral escape valve: `claude --permission-mode bypassPermissions` — `/night-mode` itself never writes `bypassPermissions` (a persistent bypass trips the tamper tripwire by design). See [`docs/TROUBLESHOOTING.md`](TROUBLESHOOTING.md) "Automode comes disabled by default".
 
 ---

exec
/bin/zsh -lc 'git diff --no-ext-diff --unified=12 -- "docs/GUIA-COMPLETO.md"' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
diff --git a/docs/GUIA-COMPLETO.md b/docs/GUIA-COMPLETO.md
index 41ca561..3aaf2cc 100644
--- a/docs/GUIA-COMPLETO.md
+++ b/docs/GUIA-COMPLETO.md
@@ -155,25 +155,25 @@ For those, use Claude Code directly. Spawn overhead > benefit.
 ## 3. What it is, what it is not
 
 ### It is:
 - **A portable framework.** Files you install into `.claude/` in your
   project.
 - **Opinionated.** Enforces a protocol. You can customize, but not
   ignore.
 - **Stdlib-only in Python.** Zero external dependencies in the hooks.
 - **Claude Code first.** A Gemini adapter stub exists, but real parity
   is deferred to v2+.
 - **Audited.** Every spawn, every decision, every veto becomes a JSONL
   event.
-- **Governed by ADR.** 188 ADRs document every architectural decision.
+- **Governed by ADR.** 189 ADRs document every architectural decision.
 
 ### It is NOT:
 - **A product.** No UI, no SaaS, no login.
 - **A library.** You do not `npm install` or `pip install`. You run
   an `install.sh` that copies files.
 - **A remote controller.** You do NOT open this repo and command
   Claude to work on another repo. You install the framework INTO the
   other repo and open Claude Code there.
 - **A substitute for discipline.** If the codebase is chaotic, the
   framework amplifies chaos. It amplifies good discipline; it does
   not create it.
 - **Model-independent.** The "agents" are all the same Claude. The
@@ -1213,25 +1213,25 @@ mv .claude .claude.disabled
 - `docs/GLOSSARY.md` — full vocabulary
 - `docs/TROUBLESHOOTING.md` — common problems
 - `docs/ROADMAP.md` — future of the framework
 - `docs/BRANCH-PROTECTION.md` — GitHub branch protection setup
 - `docs/audit-dashboard.md` — how to run the local dashboard
 - `docs/provider-pricing.md` — LLM prices for `/agent budget`
 
 ### Key files in `.claude/`
 - `.claude/team.md` — backend roster + ROUTING TABLE + SKILL MAP
 - `.claude/frontend-team.md` — frontend roster
 - `.claude/pitfalls-catalog.yaml` — universal pitfalls
 - `.claude/task-chains.yaml` — 6 universal workflows
-- `.claude/adr/` — 188 Architecture Decision Records
+- `.claude/adr/` — 189 Architecture Decision Records
 - `.claude/plans/` — active plans + archive
 - `.claude/skills/core/` — 42 universal skills
 - `.claude/skills/frontend/` — 8 frontend skills
 - `.claude/skills/domains/<squad>/` — installed squads
 
 ### Contracts in `SPEC/v1/`
 - `state-stores.schema.md` — unified state backend
 - `adapters.schema.md` — LLM adapters (Claude, Gemini, OpenAI, local)
 - `normalized_envelope.schema.md` — canonical request envelope
 - `judge-payload.schema.md` — LLM-as-judge payload
 - `scratchpad.schema.md` — shared memory
 - `session-graph.schema.md` — derived session graph

exec
/bin/zsh -lc 'git diff --no-ext-diff --unified=12 -- "docs/README.md"' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
diff --git a/docs/README.md b/docs/README.md
index 03e3350..4a50bbb 100644
--- a/docs/README.md
+++ b/docs/README.md
@@ -69,25 +69,25 @@ Pick the row that matches your role and follow it down.
 
 ## What the numbers are
 
 Every count below is reproducible from a clean checkout. The CTO guide lists the
 full set of commands; here is the summary you can spot-check in a minute.
 
 | Thing | Count | How to verify |
 |-------|-------|---------------|
 | Skills | **166** (42 core + 8 frontend + 116 domain) | `find .claude/skills -name SKILL.md \| wc -l` |
 | Hook scripts on disk | **57** Python scripts | count `*.py` in `.claude/hooks/` |
 | Hooks registered | **46** distinct scripts (48 event registrations) | inspect `.claude/settings.json` |
 | Slash commands | **27** | count `*.md` in `.claude/commands/` |
-| Architecture decision records | **188** | count `ADR-*.md` in `.claude/adr/` |
+| Architecture decision records | **189** | count `ADR-*.md` in `.claude/adr/` |
 | Shared library modules | **68** stdlib-only (top-level `_lib/`) | count `*.py` in `.claude/hooks/_lib/` |
 | Tests | **~730 test files**; `make test-collect` (pytest `--collect-only`) reports **~14,000** collected cases | `make test-collect` |
 
 Two of these are easy to misread, so we state them plainly: the **57** hook
 scripts on disk are not all wired at once — **46** distinct scripts (across 48 event registrations) are registered in
 `settings.json` for this repo's install. And the test figure is *collected
 cases*, not hand-written functions; parametrization inflates the count, which is
 why we cite `make test-collect` as the authority rather than a grep.
 
 **Runtime:** Python ≥ 3.9, **stdlib-only** — zero third-party runtime
 dependencies (see [../SBOM.md](../SBOM.md)).
 

exec
/bin/zsh -lc 'git diff --no-ext-diff --unified=12 -- "npm/README.md"' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
diff --git a/npm/README.md b/npm/README.md
index 9203de5..a19a95f 100644
--- a/npm/README.md
+++ b/npm/README.md
@@ -47,25 +47,25 @@ When installed, the framework registers a set of [Claude Code hooks](https://doc
 
 ## What's in the box
 
 All counts below are verifiable from a clean checkout (see *Verifying the numbers*).
 
 | Component | Count | Notes |
 |---|---|---|
 | Skill checklists | **166** | 42 core + 8 frontend + 116 domain |
 | Hook scripts (on disk) | **57** | Python entrypoints under `.claude/hooks/` |
 | Hooks wired in `settings.json` | **46** | distinct scripts, 48 event registrations |
 | Shared library modules | **68** | stdlib-only, under `.claude/hooks/_lib/` (excluding the package `__init__.py`) |
 | Slash commands | **27** | under `.claude/commands/` |
-| Architecture decision records | **188** | under `.claude/adr/` |
+| Architecture decision records | **189** | under `.claude/adr/` |
 | Tests | **~14,000 cases** | reported by `pytest --collect-only` across the hook, script, and conformance suites |
 
 The gap between **57 hook scripts** on disk and **46 wired** is benign: several non-event modules are activated through in-process dispatch (invoked by other hooks) rather than by a direct `settings.json` event registration.
 
 **Runtime dependencies: none.** Hooks and scripts are Python ≥ 3.9, **standard library only** — zero third-party runtime packages. See [`SBOM.md`](SBOM.md). (Development and CI use third-party test tooling such as pytest; the installed runtime does not.)
 
 There is also a **published compliance contract** under `SPEC/v1/` (32 files — 28 `*.schema.md` plus contract docs, version-pinned), a TLA+ specification of the core circuit-breaker state machine, a conformance harness, and a local read-only audit dashboard.
 
 ---
 
 ## Quick start
 
@@ -110,25 +110,25 @@ To remove the framework cleanly:
 /path/to/ceo-orchestration/scripts/uninstall.sh /path/to/your-app
 ```
 
 ---
 
 ## Verifying the numbers
 
 Don't take the table on faith. From a clean checkout:
 
 ```bash
 find .claude/skills -name SKILL.md | wc -l        # 166 skills
 ls .claude/commands/*.md | wc -l                  # 27 slash commands
-ls .claude/adr | grep -c '^ADR-'                  # 188 ADRs
+ls .claude/adr | grep -c '^ADR-'                  # 189 ADRs
 python3 -m pytest --collect-only -q | tail -1     # ~14,000 collected cases
 ```
 
 ---
 
 ## Risks and what this is *not*
 
 Intellectual honesty is the point, so the caveats are first-class:
 
 - **Bus factor of one.** This is built and maintained by a single maintainer. There is no team behind it, no SLA, and no guarantee of continuity. Evaluate it accordingly.
 - **Same-vendor reviewer caveat.** The cross-model pair-rail reduces single-model blind spots, but the reviewer is still a large language model and can share failure modes with the model under review. It is defense-in-depth, not an independent oracle.
 - **Codex is not bundled — the pair-rail is inert until you install it.** The cross-model review rail invokes the [Codex CLI](https://github.com/openai/codex), which is **not** shipped with this framework. On a fresh install with no Codex present, the pair-rail **fails open and contributes zero review** — protected-path edits still pass the GPG ceremony, but no second model looks at them. You only get the cross-model rung after installing Codex separately. See [`docs/HONEST-LIMITATIONS.md`](docs/HONEST-LIMITATIONS.md) and ADR-145.

exec
/bin/zsh -lc "grep -n \"positive.control\\|PLANTED\\|per-mode verdicts\\|exit 9\\|CONTROL\" scripts/tests/test-install-upgrade-parity-e2e.sh | head -160 && nl -ba scripts/tests/test-install-upgrade-parity-e2e.sh | sed -n '1,260p' && nl -ba scripts/tests/test-install-upgrade-parity-e2e.sh | sed -n '260,620p'" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
63:#     the positive control trips exactly there.
67:#   1  FAIL     — undeclared divergence (what the positive control must
78:# POSITIVE CONTROL
79:#   --positive-control deletes ONE `backup_and_replace "<dir>"` line from a COPY
81:#   EVERY mode tested. If any mode does NOT go fatal, the run ends in exit 9
95:#   bash scripts/tests/test-install-upgrade-parity-e2e.sh --positive-control
113:POSITIVE_CONTROL=0
114:# The single line deleted from a COPY of upgrade.sh by --positive-control.
124:    --positive-control) POSITIVE_CONTROL=1; shift ;;
125:    # Only meaningful with --positive-control. Exists so the vacuity guard
127:    # $PIN and HEAD must end in exit 9, not in a green.
136:    *) echo "ERROR: unknown argument: $1" >&2; exit 9 ;;
146:scaffold() { echo "" >&2; echo "SCAFFOLD-ERROR: $*" >&2; exit 9; }
179:echo "  positive control      : $POSITIVE_CONTROL"
203:# --- optional planted-divergence source for the positive control ------------
208:# exactly one line, which is what a positive control is for.
209:PLANTED_SRC=""
210:if [ "$POSITIVE_CONTROL" -eq 1 ]; then
211:  PLANTED_SRC="$WORK/src-planted"
212:  mkdir -p "$PLANTED_SRC/scripts"
217:    ln -s "$_e" "$PLANTED_SRC/$_b" 2>/dev/null || true
223:    ln -s "$_f" "$PLANTED_SRC/scripts/$_b" 2>/dev/null || true
227:    "$REPO_ROOT/scripts/upgrade.sh" > "$PLANTED_SRC/scripts/upgrade.sh" \
229:  _after="$( grep -c "^backup_and_replace \"$PLANT_TARGET\"\$" "$PLANTED_SRC/scripts/upgrade.sh" || true )"
233:  echo "  PLANTED: dropped backup_and_replace \"$PLANT_TARGET\" from a COPY of"
281:  [ -n "$PLANTED_SRC" ] && UP_SRC="$PLANTED_SRC"
295:  [ -n "$PLANTED_SRC" ] && EXTRA_ARGS="--extra-source $PLANTED_SRC"
313:echo "per-mode verdicts (0 parity / 1 fail / 2 known-open):$MODE_VERDICTS"
315:# --- positive-control self-check ------------------------------------------
319:if [ "$POSITIVE_CONTROL" -eq 1 ]; then
335:    scaffold "positive control did not fire in every mode"
337:  echo "positive control: FIRED in every mode (rc=1 each) — the gate is alive."
     1	#!/usr/bin/env bash
     2	# scripts/tests/test-install-upgrade-parity-e2e.sh
     3	# PLAN-166 W0 / F4 (OQ-4) — install≠upgrade parity, measured on the RESULTING
     4	# TREES, per ceremony mode.
     5	#
     6	# WHY THIS EXISTS (F4, P1)
     7	# ------------------------
     8	# The previous parity gate was dead twice over:
     9	#   (a) TAUTOLOGICAL — scripts/tests/test_install_baseline_manifest.sh "C.2"
    10	#       compared `_framework_target_entries()` with `_framework_target_entries()`
    11	#       and admitted it in a comment ("the enumeration is static
    12	#       (root-independent), so an 'install context' and an 'upgrade context'
    13	#       derive an identical target set by construction"). It also carried a
    14	#       hand-written closed list of "required entries".
    15	#   (b) INVISIBLE — no workflow ran scripts/tests/*.sh except smoke-install.yml,
    16	#       and neither the old assertion nor this file was wired into it. 5th
    17	#       instance of the "red gate nobody runs" class.
    18	# Set-equality of ENUMERATIONS — even independently derived ones — can NEVER
    19	# reach the delivery sites that live OUTSIDE the enumeration. That is exactly
    20	# how F3 was born: `SPEC/v1` is delivered by install.sh (`install_one "SPEC/v1"`,
    21	# install.sh:1307) and by NOTHING in upgrade.sh, and it is absent from
    22	# `_framework_target_entries()`. So this test compares REAL TREES.
    23	#
    24	# WHAT IT DOES
    25	# ------------
    26	#   Route A (fresh)      : install.sh (WORKING TREE)                      -> A
    27	#   Route B (historical) : install.sh @ $PIN -> upgrade.sh (WORKING TREE) -> B
    28	# for EACH ceremony mode (maintainer, user). Both targets get the SAME basename
    29	# so install.sh's {{PROJECT_NAME}} substitution is identical on both sides.
    30	#
    31	# THE MEASUREMENT (why "diff -r A B" is the wrong instrument)
    32	# -----------------------------------------------------------
    33	# A raw byte-diff of the two trees answers "are these two installs identical",
    34	# which is not the question. The question is "did the upgrade deliver the
    35	# CURRENT generation of framework content?" So every path is classified against
    36	# BOTH source generations (the working tree and the $PIN archive):
    37	#
    38	#   IDENTICAL      A(p) == B(p)                                      ok
    39	#   PERSONALIZED   B(p) == head_src(p): upgrade shipped CURRENT       advisory
    40	#                  framework bytes; install.sh additionally
    41	#                  substitutes {{PROJECT_NAME}}-class placeholders
    42	#   STALE          B(p) == pin_src(p) != head_src(p): the upgrade     FATAL
    43	#                  LEFT THE OLD GENERATION IN PLACE   <-- F3 signature
    44	#   MISSING_IN_B   install delivered p, upgrade did not               FATAL
    45	#   UNCLASSIFIED   diverges and matches neither generation            FATAL
    46	#                  (generated/adopter-owned paths must be DECLARED)
    47	#   MODE_DIFF      same bytes, different +x bit ("cp lost the exec     FATAL
    48	#                  bit" is a verified S286 failure mode here)
    49	#   ONLY_IN_B      upgrade's `cp -R` drags content install's          advisory
    50	#                  selective walk never ships (ADR-155 pre-existing
    51	#                  drift) -- EXCEPT outside .claude/ in `user` mode,
    52	#                  which is FATAL (the WS4 no-writes-outside-.claude
    53	#                  invariant that smoke-install.yml already asserts
    54	#                  for install and nobody asserts for upgrade)
    55	#
    56	# Declarations are checked for ROT in both directions:
    57	#   * KNOWN-OPEN ledger entries are MANDATORY-FIRE: an entry that matches
    58	#     nothing is FATAL ("the bug you named is closed -- delete the entry").
    59	#     A ledger cannot outlive its bug.
    60	#   * DECLARED generated/adopter-owned paths that turn out IDENTICAL emit a
    61	#     WARNING (declaration is stale; harmless).
    62	#   * Any divergence matching NO declaration is FATAL. That is the live gate;
    63	#     the positive control trips exactly there.
    64	#
    65	# EXIT CODES
    66	#   0  parity   — no fatal divergence and no KNOWN-OPEN entry outstanding
    67	#   1  FAIL     — undeclared divergence (what the positive control must
    68	#                 produce, and what a real install/upgrade regression produces)
    69	#   2  KNOWN-OPEN — only the explicitly named PLAN-166 W1 prerequisites are
    70	#                 outstanding. STILL A FAILURE, never a silent skip: the
    71	#                 printed ledger names each one and what unblocks it. This is
    72	#                 the expected pre-W1 result.
    73	#   9  SCAFFOLD-ERROR — the fixture itself broke (tag unresolvable, install or
    74	#                 upgrade returned non-zero, python3 missing). NEVER a verdict
    75	#                 on the bug. In CI the historical leg needs the TAG: a
    76	#                 `fetch-depth: 1` checkout does not have it.
    77	#
    78	# POSITIVE CONTROL
    79	#   --positive-control deletes ONE `backup_and_replace "<dir>"` line from a COPY
    80	#   of upgrade.sh and re-runs the whole thing. The expected outcome is exit 1 in
    81	#   EVERY mode tested. If any mode does NOT go fatal, the run ends in exit 9
    82	#   SCAFFOLD-ERROR ("the control is vacuous"), never in a green — a control that
    83	#   silently stops firing is worse than no control at all. That happens for a
    84	#   real reason: the plant only bites if the planted directory actually drifted
    85	#   between $PIN and HEAD, so the guard is DERIVED from the run, not asserted
    86	#   from memory.
    87	#   ORDERING MATTERS: the control only proves something when the UN-planted run
    88	#   was not already fatal, otherwise rc=1 could come from a pre-existing
    89	#   divergence rather than from the plant. So CI runs the plain gate FIRST and
    90	#   the control only after it passed; run it the same way by hand.
    91	#
    92	# USAGE
    93	#   bash scripts/tests/test-install-upgrade-parity-e2e.sh
    94	#   bash scripts/tests/test-install-upgrade-parity-e2e.sh --mode user
    95	#   bash scripts/tests/test-install-upgrade-parity-e2e.sh --positive-control
    96	#   bash scripts/tests/test-install-upgrade-parity-e2e.sh --print-pin
    97	#
    98	# W1 CHECKLIST: the KNOWN_OPEN ledger in _parity_classify.py is MANDATORY-FIRE.
    99	# When W1 lands the F3 fix those entries stop matching and the classifier goes
   100	# fatal on ledger-rot BY DESIGN — deleting them belongs to the same commit.
   101	#
   102	# bash-3.2 safe (no associative arrays, no mapfile). Network-free. Writes only
   103	# under mktemp -d. Requires: git, python3, tar.
   104	
   105	set -uo pipefail   # NOT -e: failures are classified, not fatal-by-default.
   106	
   107	SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
   108	REPO_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
   109	
   110	PIN="${CEO_PARITY_PIN:-v1.2.0}"
   111	PROFILE="${CEO_PARITY_PROFILE:-core}"
   112	MODES="maintainer user"
   113	POSITIVE_CONTROL=0
   114	# The single line deleted from a COPY of upgrade.sh by --positive-control.
   115	PLANT_TARGET='.claude/commands'
   116	
   117	PRINT_PIN=0
   118	
   119	while [ $# -gt 0 ]; do
   120	  case "$1" in
   121	    --mode) MODES="${2:-}"; shift 2 ;;
   122	    --profile) PROFILE="${2:-}"; shift 2 ;;
   123	    --pin) PIN="${2:-}"; shift 2 ;;
   124	    --positive-control) POSITIVE_CONTROL=1; shift ;;
   125	    # Only meaningful with --positive-control. Exists so the vacuity guard
   126	    # itself can be exercised: planting a target that did NOT drift between
   127	    # $PIN and HEAD must end in exit 9, not in a green.
   128	    --plant-target) PLANT_TARGET="${2:-}"; shift 2 ;;
   129	    # Single source of truth for the historical pin: CI must FETCH this tag
   130	    # (the checkout is fetch-depth:1 and has no tags), and hardcoding the value
   131	    # in the workflow would make a second copy of the truth that drifts.
   132	    --print-pin) PRINT_PIN=1; shift ;;
   133	    # Print the header block, whatever its length — a hardcoded `sed -n '2,80p'`
   134	    # silently truncates the help the first time the header grows.
   135	    -h|--help) awk 'NR>1 && /^[^#]/ {exit} NR>1 {print}' "$0"; exit 0 ;;
   136	    *) echo "ERROR: unknown argument: $1" >&2; exit 9 ;;
   137	  esac
   138	done
   139	
   140	if [ "$PRINT_PIN" -eq 1 ]; then
   141	  printf '%s\n' "$PIN"
   142	  exit 0
   143	fi
   144	[ "$MODES" = "both" ] && MODES="maintainer user"
   145	
   146	scaffold() { echo "" >&2; echo "SCAFFOLD-ERROR: $*" >&2; exit 9; }
   147	
   148	command -v python3 >/dev/null 2>&1 || scaffold "python3 not on PATH"
   149	command -v git     >/dev/null 2>&1 || scaffold "git not on PATH"
   150	command -v tar     >/dev/null 2>&1 || scaffold "tar not on PATH"
   151	
   152	CLASSIFY="$SCRIPT_DIR/_parity_classify.py"
   153	[ -f "$CLASSIFY" ] || scaffold "classifier missing: $CLASSIFY"
   154	
   155	WORK="$( mktemp -d -t ceo-parity-e2e-XXXXXX )" || scaffold "mktemp -d failed"
   156	# shellcheck disable=SC2329  # invoked indirectly by the EXIT trap below
   157	cleanup() {
   158	  [ "${CEO_PARITY_KEEP_WORK:-0}" = "1" ] && return 0
   159	  [ -n "${WORK:-}" ] || return 0
   160	  find "$WORK" -mindepth 1 -depth -exec chmod u+w {} + 2>/dev/null || true
   161	  find "$WORK" -mindepth 1 -depth -delete 2>/dev/null || true
   162	  rmdir "$WORK" 2>/dev/null || true
   163	}
   164	trap cleanup EXIT
   165	
   166	# Non-interactive install/upgrade. A source checkout carries a placeholder
   167	# self-SHA; skipping it keeps the fixture deterministic regardless of
   168	# release-fill state (the same knobs smoke-install.yml already uses).
   169	export CEO_INSTALL_SKIP_SELF_SHA=1
   170	export CEO_RAG_INSTALL_PROMPT=0
   171	
   172	echo "=============================================================="
   173	echo " install/upgrade parity e2e  (PLAN-166 F4 / OQ-4)"
   174	echo "=============================================================="
   175	echo "  repo (route A source) : $REPO_ROOT"
   176	echo "  historical pin        : $PIN"
   177	echo "  profile               : $PROFILE"
   178	echo "  ceremony modes        : $MODES"
   179	echo "  positive control      : $POSITIVE_CONTROL"
   180	echo "  workdir               : $WORK"
   181	echo "  git describe (repo)   : $( git -C "$REPO_ROOT" describe --tags --always --dirty 2>/dev/null || echo '(n/a)' )"
   182	echo "--------------------------------------------------------------"
   183	
   184	# --- historical source: pure read of the tag, never a repo mutation ---------
   185	if ! git -C "$REPO_ROOT" rev-parse --verify --quiet "refs/tags/$PIN" >/dev/null 2>&1; then
   186	  {
   187	    echo ""
   188	    echo "  tag '$PIN' does not resolve in $REPO_ROOT."
   189	    echo "  In CI this is the fetch-depth:1 hole — the checkout has no tags, so"
   190	    echo "  the historical leg cannot run, and 'it passes on my clone' is"
   191	    echo "  exactly the gap this test exists to close. Fetch the tag first:"
   192	    echo "      git fetch --no-tags --depth 1 origin +refs/tags/$PIN:refs/tags/$PIN"
   193	  } >&2
   194	  scaffold "historical pin '$PIN' unresolvable — refusing to skip"
   195	fi
   196	PIN_SRC="$WORK/src-$PIN"
   197	mkdir -p "$PIN_SRC"
   198	if ! git -C "$REPO_ROOT" archive "$PIN" | tar -x -C "$PIN_SRC"; then
   199	  scaffold "git archive $PIN | tar -x failed"
   200	fi
   201	[ -f "$PIN_SRC/scripts/install.sh" ] || scaffold "$PIN archive has no scripts/install.sh"
   202	
   203	# --- optional planted-divergence source for the positive control ------------
   204	# A depth-1 symlink farm over the working tree with ONE edited file. upgrade.sh
   205	# derives SOURCE_DIR from its own location ("cd $SCRIPT_DIR/.." with a logical
   206	# pwd), so the farm root becomes the source and every other path resolves
   207	# through the symlinks to the live tree. Cheap (no 75MB copy) and it perturbs
   208	# exactly one line, which is what a positive control is for.
   209	PLANTED_SRC=""
   210	if [ "$POSITIVE_CONTROL" -eq 1 ]; then
   211	  PLANTED_SRC="$WORK/src-planted"
   212	  mkdir -p "$PLANTED_SRC/scripts"
   213	  for _e in "$REPO_ROOT"/* "$REPO_ROOT"/.[!.]* "$REPO_ROOT"/..?*; do
   214	    [ -e "$_e" ] || continue
   215	    _b="$( basename "$_e" )"
   216	    [ "$_b" = "scripts" ] && continue
   217	    ln -s "$_e" "$PLANTED_SRC/$_b" 2>/dev/null || true
   218	  done
   219	  for _f in "$REPO_ROOT"/scripts/* "$REPO_ROOT"/scripts/.[!.]*; do
   220	    [ -e "$_f" ] || continue
   221	    _b="$( basename "$_f" )"
   222	    [ "$_b" = "upgrade.sh" ] && continue
   223	    ln -s "$_f" "$PLANTED_SRC/scripts/$_b" 2>/dev/null || true
   224	  done
   225	  _before="$( grep -c "^backup_and_replace \"$PLANT_TARGET\"\$" "$REPO_ROOT/scripts/upgrade.sh" || true )"
   226	  grep -v "^backup_and_replace \"$PLANT_TARGET\"\$" \
   227	    "$REPO_ROOT/scripts/upgrade.sh" > "$PLANTED_SRC/scripts/upgrade.sh" \
   228	    || scaffold "could not write planted upgrade.sh"
   229	  _after="$( grep -c "^backup_and_replace \"$PLANT_TARGET\"\$" "$PLANTED_SRC/scripts/upgrade.sh" || true )"
   230	  if [ "${_before:-0}" -lt 1 ] || [ "${_after:-1}" -ne 0 ]; then
   231	    scaffold "planting failed: backup_and_replace \"$PLANT_TARGET\" occurrences before=$_before after=$_after — the control perturbed nothing"
   232	  fi
   233	  echo "  PLANTED: dropped backup_and_replace \"$PLANT_TARGET\" from a COPY of"
   234	  echo "           upgrade.sh (occurrences $_before -> $_after). The live"
   235	  echo "           scripts/upgrade.sh is untouched."
   236	  echo "--------------------------------------------------------------"
   237	fi
   238	
   239	_git_init() {
   240	  _n=0
   241	  while [ "$_n" -lt 5 ]; do
   242	    ( cd "$1" && git init -q 2>/dev/null ) && return 0
   243	    _n=$(( _n + 1 )); sleep 1
   244	  done
   245	  ( cd "$1" && git init -q )
   246	}
   247	
   248	OVERALL=0          # 0 parity | 1 fail | 2 known-open
   249	MODE_VERDICTS=""   # "mode:rc" pairs, bash-3.2 has no associative arrays
   250	for MODE in $MODES; do
   251	  echo ""
   252	  echo "##############################################################"
   253	  echo "# ceremony mode: $MODE"
   254	  echo "##############################################################"
   255	
   256	  # SAME basename on both sides: install.sh substitutes {{PROJECT_NAME}} with
   257	  # basename($TARGET). Different basenames would fabricate ~30 phantom
   258	  # divergences that say nothing about install/upgrade parity.
   259	  A_DIR="$WORK/$MODE/route-a/adopter"
   260	  B_DIR="$WORK/$MODE/route-b/adopter"
   260	  B_DIR="$WORK/$MODE/route-b/adopter"
   261	  mkdir -p "$A_DIR" "$B_DIR"
   262	  _git_init "$A_DIR"; _git_init "$B_DIR"
   263	
   264	  echo "--> [A] install.sh (working tree) --ceremony $MODE --profile $PROFILE"
   265	  if ! bash "$REPO_ROOT/scripts/install.sh" "$A_DIR" \
   266	        --profile "$PROFILE" --ceremony "$MODE" \
   267	        >"$WORK/$MODE-a-install.log" 2>&1; then
   268	    tail -40 "$WORK/$MODE-a-install.log" >&2
   269	    scaffold "[A] install.sh failed (mode=$MODE)"
   270	  fi
   271	
   272	  echo "--> [B1] install.sh @ $PIN --ceremony $MODE --profile $PROFILE"
   273	  if ! bash "$PIN_SRC/scripts/install.sh" "$B_DIR" \
   274	        --profile "$PROFILE" --ceremony "$MODE" \
   275	        >"$WORK/$MODE-b-install.log" 2>&1; then
   276	    tail -40 "$WORK/$MODE-b-install.log" >&2
   277	    scaffold "[B1] install.sh @ $PIN failed (mode=$MODE)"
   278	  fi
   279	
   280	  UP_SRC="$REPO_ROOT"
   281	  [ -n "$PLANTED_SRC" ] && UP_SRC="$PLANTED_SRC"
   282	  echo "--> [B2] upgrade.sh (source: $UP_SRC)"
   283	  if ! bash "$UP_SRC/scripts/upgrade.sh" "$B_DIR" \
   284	        --profile "$PROFILE" --no-diff-warn \
   285	        >"$WORK/$MODE-b-upgrade.log" 2>&1; then
   286	    tail -40 "$WORK/$MODE-b-upgrade.log" >&2
   287	    scaffold "[B2] upgrade.sh failed (mode=$MODE)"
   288	  fi
   289	
   290	  echo "--> classify"
   291	  # When planted, the farm root is a THIRD absolute source path that can be
   292	  # embedded in generated files; fold it too, so the control fails for the
   293	  # planted reason instead of for an unfolded /tmp path.
   294	  EXTRA_ARGS=""
   295	  [ -n "$PLANTED_SRC" ] && EXTRA_ARGS="--extra-source $PLANTED_SRC"
   296	  # shellcheck disable=SC2086  # EXTRA_ARGS is a controlled, space-free pair
   297	  python3 "$CLASSIFY" \
   298	    --a "$A_DIR" --b "$B_DIR" \
   299	    --head-src "$REPO_ROOT" --pin-src "$PIN_SRC" --pin "$PIN" \
   300	    --mode "$MODE" $EXTRA_ARGS
   301	  rc=$?
   302	  case "$rc" in
   303	    0) : ;;
   304	    2) [ "$OVERALL" -eq 0 ] && OVERALL=2 ;;
   305	    1) OVERALL=1 ;;
   306	    *) scaffold "classifier returned unexpected rc=$rc (mode=$MODE)" ;;
   307	  esac
   308	  MODE_VERDICTS="$MODE_VERDICTS $MODE:$rc"
   309	done
   310	
   311	echo ""
   312	echo "--------------------------------------------------------------"
   313	echo "per-mode verdicts (0 parity / 1 fail / 2 known-open):$MODE_VERDICTS"
   314	
   315	# --- positive-control self-check ------------------------------------------
   316	# A control that stops firing must never read as a pass. Requiring rc==1 in
   317	# EVERY mode is DERIVED from the run: the plant only bites if the planted
   318	# directory actually drifted between $PIN and HEAD.
   319	if [ "$POSITIVE_CONTROL" -eq 1 ]; then
   320	  _not_fatal=""
   321	  for _pair in $MODE_VERDICTS; do
   322	    _m="${_pair%%:*}"; _r="${_pair##*:}"
   323	    [ "$_r" = "1" ] || _not_fatal="$_not_fatal $_m(rc=$_r)"
   324	  done
   325	  if [ -n "$_not_fatal" ]; then
   326	    {
   327	      echo ""
   328	      echo "  The plant removed backup_and_replace \"$PLANT_TARGET\" from the copy"
   329	      echo "  of upgrade.sh, yet these modes did NOT go FATAL:$_not_fatal"
   330	      echo "  Most likely cause: nothing under '$PLANT_TARGET' changed between"
   331	      echo "  $PIN and HEAD, so removing its refresh is undetectable — the"
   332	      echo "  control is vacuous and proves nothing. Pick a PLANT_TARGET with"
   333	      echo "  real drift, or advance the pin."
   334	    } >&2
   335	    scaffold "positive control did not fire in every mode"
   336	  fi
   337	  echo "positive control: FIRED in every mode (rc=1 each) — the gate is alive."
   338	fi
   339	
   340	echo ""
   341	echo "=============================================================="
   342	case "$OVERALL" in
   343	  0) echo "RESULT: PASS — install and upgrade converge on the same framework"
   344	     echo "        content in every ceremony mode tested ($MODES)." ;;
   345	  2) {
   346	       echo "RESULT: KNOWN-OPEN (exit 2) — the ONLY outstanding divergences are the"
   347	       echo "        explicitly named PLAN-166 W1 prerequisites printed above."
   348	       echo "        This is a FAILURE, not a skip. It goes green when W1 lands."
   349	     } >&2 ;;
   350	  1) echo "RESULT: FAIL (exit 1) — undeclared install/upgrade divergence above." >&2 ;;
   351	esac
   352	echo "=============================================================="
   353	exit "$OVERALL"

exec
/bin/zsh -lc "grep -R \"test-install-upgrade-parity-e2e.sh\\|test-upgrade-spec-ownership.sh\" -n .github/workflows .claude | grep -v '/plans/' | head -80 && printf '\\n--- installed surface top-level ---\\n' && sed -n '108,170p' scripts/_framework_manifest_set.sh" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 1680ms:
.github/workflows/smoke-install.yml:22:      - "scripts/tests/test-install-upgrade-parity-e2e.sh"
.github/workflows/smoke-install.yml:27:      - "scripts/tests/test-upgrade-spec-ownership.sh"
.github/workflows/smoke-install.yml:58:      - "scripts/tests/test-install-upgrade-parity-e2e.sh"
.github/workflows/smoke-install.yml:60:      - "scripts/tests/test-upgrade-spec-ownership.sh"
.github/workflows/smoke-install.yml:112:          PIN="$(bash scripts/tests/test-install-upgrade-parity-e2e.sh --print-pin)"
.github/workflows/smoke-install.yml:182:          bash scripts/tests/test-install-upgrade-parity-e2e.sh
.github/workflows/smoke-install.yml:194:          bash scripts/tests/test-install-upgrade-parity-e2e.sh \
.github/workflows/smoke-install.yml:224:          bash scripts/tests/test-upgrade-spec-ownership.sh
.claude/adr/ADR-155-AMEND-1-delivery-record-ownership.md:207:- `scripts/tests/test-upgrade-spec-ownership.sh` — record-owned forced

--- installed surface top-level ---

# _framework_target_entries — the top-level target relpaths (files + dirs),
# profile-aware, sorted + deduped. This is the STATIC intended set; it does not
# touch disk (so install and upgrade derive an identical list regardless of
# what is currently present).
_framework_target_entries() {
  {
    # Root governance pointer (the verified S238 driver target — outside
    # .claude/). PLAN-166 F3 (ADR-155-AMEND-1): CONDITIONAL on the recorded
    # delivery. A `--ceremony user` install SKIPS install_protocol_pointer
    # (install.sh WS4-guard-proto), and a maintainer target that ALREADY had
    # its own root PROTOCOL.md was never written by the framework —
    # enumerating it unconditionally records the ADOPTER's file as
    # framework-owned (r13/r17).
    if [ "${FMS_DELIVERED_PROTOCOL:-0}" = "1" ]; then
      printf '%s\n' "PROTOCOL.md"
    fi

    # SPEC/v1 published contract (PLAN-166 F3): an upgrade surface as of
    # v1.3.0 — same delivery-record condition (never ceremony alone, never
    # file presence; r7/r17).
    if [ "${FMS_DELIVERED_SPEC:-0}" = "1" ]; then
      printf '%s\n' "SPEC/v1"
    fi

    # Framework version marker (PLAN-166 F3): a NORMAL tracked-file entry —
    # present in the source tree, so the FMS_HASH_ROOT baseline rewrite
    # (below) preserves it with no generated-file special-case — but
    # ownership still derives from the registered delivery: a target whose
    # marker pre-existed (install_one EXISTS-skip) stays adopter-owned and
    # every marker-first reader keyed off this same record falls back to
    # VERSION (r20).
    if [ "${FMS_DELIVERED_MARKER:-0}" = "1" ]; then
      printf '%s\n' ".claude/.framework-version"
    fi

    # Always-installed team rosters + universal catalogs.
    printf '%s\n' ".claude/team.md"
    printf '%s\n' ".claude/frontend-team.md"
    printf '%s\n' ".claude/pitfalls-catalog.yaml"
    printf '%s\n' ".claude/task-chains.yaml"

    # Protocol-enforcement directory targets (always installed).
    printf '%s\n' ".claude/hooks"
    printf '%s\n' ".claude/scripts"
    printf '%s\n' ".claude/commands"

    # Skills are profile-gated.
    if _fms_has_profile "core"; then
      printf '%s\n' ".claude/skills/core"
    fi
    if _fms_has_profile "frontend"; then
      printf '%s\n' ".claude/skills/frontend"
    fi
    # Domain profiles: any profile part that is neither core nor frontend.
    for _fms_part in $( _fms_profile_parts ); do
      case "$_fms_part" in
        core|frontend) : ;;
        *) printf '%s\n' ".claude/skills/domains/$_fms_part" ;;
      esac
    done
  } | LC_ALL=C sort -u
}

exec
/bin/zsh -lc "grep -R \"test_release_workflow_asserts\\|pytest.*\\.claude/scripts/tests\\|check-claude-md-claims\" -n .github/workflows | head -100 && grep -R \"paths:\" -n .github/workflows/validate.yml .github/workflows/*.yml | head -80" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
.github/workflows/coverage.yml:132:            -m pytest .claude/scripts/tests .claude/scripts/optimizer/tests --ignore=.claude/scripts/tests/perf \
.github/workflows/chaos.yml:96:          python3 -m pytest .claude/scripts/tests/test_chaos_inject_lockdown.py \
.github/workflows/release.yml:359:        run: python3 -m pytest .claude/scripts/tests -q --tb=short
.github/workflows/release.yml:769:      # test_release_workflow_asserts.py, WaveB5 pattern):
.github/workflows/npm-publish.yml:78:# .claude/scripts/tests/test_release_workflow_asserts.py, which READS
.github/workflows/npm-publish.yml:208:    # .claude/scripts/tests/test_release_workflow_asserts.py.
.github/workflows/validate.yml:61:      # ``python3 .claude/scripts/check-claude-md-claims.py --verbose``
.github/workflows/validate.yml:64:      - name: Run check-claude-md-claims.py
.github/workflows/validate.yml:67:          python3 .claude/scripts/check-claude-md-claims.py
.github/workflows/validate.yml:424:          python3 -m pytest .claude/scripts/tests/ .claude/scripts/optimizer/tests/ -n auto -m 'not serial' --strict-markers --tb=no -q
.github/workflows/validate.yml:425:          python3 -m pytest .claude/scripts/tests/ .claude/scripts/optimizer/tests/ -m 'serial' --strict-markers --tb=no -q
.github/workflows/validate.yml:863:      # test_release_workflow_asserts.py -> .claude/scripts/tests/) are
.github/workflows/validate.yml:1454:          python3 -m pytest .claude/hooks/tests/ .claude/scripts/tests/ .claude/scripts/optimizer/tests/ \
.github/workflows/validate.yml:1456:          python3 -m pytest .claude/hooks/tests/ .claude/scripts/tests/ .claude/scripts/optimizer/tests/ \
.github/workflows/validate.yml:104:      # N+ floor). Closes F-3-3.1 / F-4-docs-001. No `paths:` filter — this
.github/workflows/validate.yml:1127:    # on TLA+ specs (paths: docs/formal-verification/**) but not the Python
.github/workflows/actionlint.yml:20:    paths:
.github/workflows/actionlint.yml:25:    paths:
.github/workflows/adapter-live.yml:18:    paths:
.github/workflows/benchmarks.yml:8:    paths:
.github/workflows/benchmarks.yml:14:    paths:
.github/workflows/chaos.yml:16:    paths:
.github/workflows/coverage.yml:12:    paths:
.github/workflows/formal-verify.yml:8:    paths:
.github/workflows/mcp-smoke.yml:56:    paths:
.github/workflows/mcp-smoke.yml:66:    paths:
.github/workflows/otel-smoke.yml:28:    paths:
.github/workflows/perf-profile.yml:16:    paths:
.github/workflows/red-team.yml:27:    paths:
.github/workflows/red-team.yml:33:    paths:
.github/workflows/shadow-ci.yml:30:    paths:
.github/workflows/smoke-install.yml:5:    paths:
.github/workflows/smoke-install.yml:46:    paths:
.github/workflows/translations-drift.yml:19:    paths:
.github/workflows/translations-drift.yml:36:    paths:
.github/workflows/validate.yml:104:      # N+ floor). Closes F-3-3.1 / F-4-docs-001. No `paths:` filter — this
.github/workflows/validate.yml:1127:    # on TLA+ specs (paths: docs/formal-verification/**) but not the Python

exec
/bin/zsh -lc "if command -v actionlint >/dev/null 2>&1; then actionlint .github/workflows/npm-publish.yml .github/workflows/release.yml .github/workflows/smoke-install.yml; else echo 'actionlint unavailable'; fi" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 173ms:
exec
/bin/zsh -lc 'if command -v shellcheck >/dev/null 2>&1; then shellcheck -S warning .claude/scripts/check-framework-updates.sh scripts/doctor.sh scripts/tests/test-upgrade-spec-ownership.sh .claude/plans/PLAN-166/OWNER-W1-LAND-step1.sh .claude/plans/PLAN-166/OWNER-W1-LAND-step1b.sh .claude/plans/PLAN-167/OWNER-PREPARE-TO-SIGN.sh; else echo unavailable; fi' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 650ms:
exec
/bin/zsh -lc "printf '%s\\n' '--- possible secrets/private paths in untracked ---'; find .claude/plans/PLAN-166/archive .claude/plans/PLAN-168/archive -type f "'! -name '"'*.tar.gz' -print0 2>/dev/null | xargs -0 grep -nE '(/Users/|BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY|gh[pousr]_[A-Za-z0-9]|sk-[A-Za-z0-9]|AKIA[0-9A-Z]{16})' 2>/dev/null | head -100 || true; printf '%s\\n' '--- archive sizes ---'; du -ah .claude/plans/PLAN-166/archive .claude/plans/PLAN-168/archive 2>/dev/null | sort -h | tail -30" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
--- possible secrets/private paths in untracked ---
.claude/plans/PLAN-166/archive/codex-review-w1-round8.md:5:- [P1] Preserve rendered hashes on installer reruns — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/install.sh:2338-2339
.claude/plans/PLAN-166/archive/codex-review-w1-round8.md:8:- [P2] Make missing LINK records follow the preserve path — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1781-1781
.claude/plans/PLAN-166/archive/codex-review-w1-round8.md:11:- [P2] Apply the staged parity-classifier edit in the landing script — /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/plans/PLAN-166/OWNER-W1-LAND-step1.sh:52-54
.claude/plans/PLAN-166/archive/codex-r6-2059.md:3:workdir: /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:18:/bin/zsh -lc "git status --short && printf '\\n--- unstaged stat ---\\n' && git diff --stat && printf '\\n--- staged stat ---\\n' && git diff --cached --stat && printf '\\n--- untracked ---\\n' && git ls-files --others --exclude-standard" in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:117:/bin/zsh -lc "printf '\\n===== .claude/scripts/check-framework-updates.sh =====\\n'; git diff --no-ext-diff -- \".claude/scripts/check-framework-updates.sh\"" in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:244:/bin/zsh -lc "printf '\\n===== .github/workflows/npm-publish.yml =====\\n'; git diff --no-ext-diff -- \".github/workflows/npm-publish.yml\"" in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:426:/bin/zsh -lc "printf '\\n===== .github/workflows/release.yml =====\\n'; git diff --no-ext-diff -- \".github/workflows/release.yml\"" in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:614:/bin/zsh -lc "printf '\\n===== .github/workflows/smoke-install.yml =====\\n'; git diff --no-ext-diff -- \".github/workflows/smoke-install.yml\"" in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:789:/bin/zsh -lc "printf '\\n===== scripts/doctor.sh =====\\n'; git diff --no-ext-diff -- \"scripts/doctor.sh\"" in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:844:/bin/zsh -lc "printf '\\n===== scripts/tests/_parity_classify.py =====\\n'; git diff --no-ext-diff -- \"scripts/tests/_parity_classify.py\"" in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:908:/bin/zsh -lc "printf '\\n===== scripts/tests/test-upgrade-spec-ownership.sh =====\\n'; git diff --no-ext-diff -- \"scripts/tests/test-upgrade-spec-ownership.sh\"" in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:1279:/bin/zsh -lc "git diff --unified=80 -- .github/workflows/release.yml | sed -n '1,360p'" in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:1643:/bin/zsh -lc "git diff --unified=80 -- .github/workflows/smoke-install.yml | sed -n '1,360p'" in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:1896:/bin/zsh -lc "git diff --unified=80 -- scripts/doctor.sh | sed -n '1,300p'" in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:2103:/bin/zsh -lc "git diff --unified=80 -- scripts/tests/_parity_classify.py | sed -n '1,320p'" in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:2319:/bin/zsh -lc "nl -ba .github/workflows/release.yml | sed -n '720,920p'; printf '\\n--- guard implementation ---\\n'; sed -n '1,320p' .claude/scripts/local/_release_tag_guard.py; printf '\\n--- verdict template diff ---\\n'; git diff --unified=60 -- .claude/governance/pair-rail-verdict-template.md" in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:2937:/bin/zsh -lc "sed -n '260,620p' .claude/scripts/local/_release_tag_guard.py; printf '\\n--- release tests diff headers ---\\n'; git diff --unified=10 -- .claude/scripts/tests/test_release_workflow_asserts.py | grep -n '"'^+class'"\\|"'^+    def test'"\\|"'^@@'"' | sed -n '1,260p'; printf '\\n--- npm current numbered ---\\n'; nl -ba .github/workflows/npm-publish.yml | sed -n '80,260p'" in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:3491:/bin/zsh -lc "sed -n '1,360p' .claude/scripts/await_release_gate.py; printf '\\n--- tests ---\\n'; sed -n '1,460p' .claude/scripts/tests/test_await_release_gate.py" in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4221:/bin/zsh -lc "sed -n '360,560p' .claude/scripts/await_release_gate.py; git status --short .claude/scripts/await_release_gate.py .claude/scripts/tests/test_await_release_gate.py; git log -1 --oneline -- .claude/scripts/await_release_gate.py" in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4320:/bin/zsh -lc 'git diff --unified=25 -- .github/workflows/smoke-install.yml' in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4568:/bin/zsh -lc "printf 'VERSION='; cat VERSION; printf 'marker='; cat .claude/.framework-version; printf '\\n--- framework marker base status ---\\n'; git ls-files .claude/.framework-version; printf '\\n--- framework update script full numbered ---\\n'; nl -ba .claude/scripts/check-framework-updates.sh | sed -n '1,260p'; printf '\\n--- framework checker tests refs ---\\n'; rg -n \"check-framework-updates|framework-version\" .claude/scripts/tests scripts/tests tests | head -240" in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4862:/bin/zsh -lc "rg -n \"framework-version|FMS_DELIVERED|_baseline_has_spec|delivered_spec|delivered_protocol|delivered_framework\" scripts/install.sh scripts/upgrade.sh scripts/_framework_manifest_set.sh | sed -n '1,300p'; printf '\\n--- nearby install ---\\n'; nl -ba scripts/install.sh | sed -n '1680,1940p'; printf '\\n--- nearby upgrade ---\\n'; rg -n \"_refresh_protocol_pointer|refresh.*SPEC|framework_marker|DELIVERED_SPEC|FMS_DELIVERED\" scripts/upgrade.sh" in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:5207:/bin/zsh -lc "nl -ba scripts/install.sh | sed -n '740,820p;1290,1405p;2350,2470p'; printf '\\n--- marker upgrade ---\\n'; nl -ba scripts/upgrade.sh | sed -n '1640,1700p;1835,2150p;3020,3170p'; printf '\\n--- manifest set ---\\n'; nl -ba scripts/_framework_manifest_set.sh | sed -n '100,160p;280,325p'" in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:5290:  1290	install_one ".claude/task-chains.yaml"
.claude/plans/PLAN-166/archive/codex-r6-2059.md:6107:   148	    printf '%s\n' ".claude/task-chains.yaml"
.claude/plans/PLAN-166/archive/codex-r6-2059.md:6168:/bin/zsh -lc 'for f in INSTALL.md README.md README.pt-BR.md RELEASE.md docs/ARCHITECTURE.md docs/CTO-GUIDE.md docs/FAQ.md docs/GUIA-COMPLETO.md docs/README.md npm/README.md; do echo "===== $f ====="; git diff --unified=20 -- "$f"; done' in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:6262:/bin/zsh -lc "find .claude/adr -maxdepth 1 -name 'ADR-*.md' | wc -l; ls .claude/adr | grep -c '"'^ADR-'"'; git diff --name-only | wc -l; python3 .claude/scripts/check-claude-md-claims.py; python3 .claude/scripts/check-agents-md.py" in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:6270:/bin/zsh -lc "cat .claude/governance/npm-trusted-publisher.txt; printf '\\n--- ADR headings ---\\n'; sed -n '1,300p' .claude/adr/ADR-155-AMEND-1-delivery-record-ownership.md; printf '\\n--- plan draft diff ---\\n'; git diff --unified=30 -- .claude/plans/PLAN-166/W1-approved-draft.md .claude/plans/PLAN-166/staged-manifest.sha256" in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:6655:/bin/zsh -lc "find .claude/plans/PLAN-166/archive .claude/plans/PLAN-168/archive -maxdepth 2 -type f -print0 2>/dev/null | xargs -0 ls -lh; printf '\\n--- top-level untracked scripts/docs sizes ---\\n'; ls -lh .claude/plans/PLAN-166/OWNER-W1-LAND-step1.sh .claude/plans/PLAN-166/W1-ceremony-log.md .claude/plans/PLAN-166/architect/round-1/approved.md.asc .claude/plans/PLAN-167/OWNER-PREPARE-TO-SIGN.sh .claude/plans/PLAN-167/W4-approved.md .claude/plans/PLAN-167/W4-approved.md.asc; printf '\\n--- file types ---\\n'; file "'$(git ls-files --others --exclude-standard | tr '"'\\n' ' ')" in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:6723:/bin/zsh -lc 'bash .claude/scripts/check-contamination.sh' in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:6749:/bin/zsh -lc 'export PYTHONDONTWRITEBYTECODE=1; bash -n .claude/scripts/check-framework-updates.sh scripts/doctor.sh scripts/tests/test-upgrade-spec-ownership.sh .claude/plans/PLAN-166/OWNER-W1-LAND-step1.sh .claude/plans/PLAN-167/OWNER-PREPARE-TO-SIGN.sh; python3 -m unittest .claude/scripts/tests/test_release_workflow_asserts.py' in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:6773:/bin/zsh -lc 'export PYTHONDONTWRITEBYTECODE=1; python3 .claude/scripts/tests/test_release_workflow_asserts.py' in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:6782:/bin/zsh -lc 'export PYTHONDONTWRITEBYTECODE=1; bash scripts/tests/test-upgrade-spec-ownership.sh' in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:6840:/bin/zsh -lc "rg -n \"ADOPTER|fork|legacy\" scripts/upgrade.sh | sed -n '1,240p'; nl -ba scripts/upgrade.sh | sed -n '1680,2030p'; nl -ba scripts/tests/test-upgrade-spec-ownership.sh | sed -n '235,275p'" in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7270:/bin/zsh -lc 'export PYTHONDONTWRITEBYTECODE=1; bash scripts/tests/test-install-upgrade-parity-e2e.sh' in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7278:--> [B2] upgrade.sh (source: /Users/joaocanhada/canhada-labs/ceo-orchestration)
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7285:    head source              : /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7376:--> [B2] upgrade.sh (source: /Users/joaocanhada/canhada-labs/ceo-orchestration)
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7383:    head source              : /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7474:/bin/zsh -lc 'command -v actionlint || true; command -v yamllint || true; command -v ruby || true; command -v jq || true; git diff --check' in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7481:/bin/zsh -lc 'actionlint .github/workflows/npm-publish.yml .github/workflows/release.yml .github/workflows/smoke-install.yml' in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7484:/bin/zsh -lc "rg -n 'head_branch|workflow_runs' .claude docs tests replay-fixtures .github | head -300" in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7643:/bin/zsh -lc 'for f in .claude/plans/PLAN-166/archive/codex-review-w1-round{6,7,8,9,10,11}.md .claude/plans/PLAN-166/archive/codex-r6-2059.md; do echo =====$f; rg -n '"'\"title\"|\\[P[0-3]\\]|findings|overall_correctness|REJECT|APPROVE' \""'$f" | tail -30; done' in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7648:/bin/zsh -lc "rg -n '\"title\"|\\[P[0-3]\\]|findings|overall_correctness|REJECT|APPROVE' \".claude/plans/PLAN-166/archive/codex-review-w1-round6.md\" | tail -40" in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7650:5:- [P2] Keep sanitized LINK records available for validation — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1728-1730
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7653:/bin/zsh -lc "rg -n '\"title\"|\\[P[0-3]\\]|findings|overall_correctness|REJECT|APPROVE' \".claude/plans/PLAN-166/archive/codex-review-w1-round7.md\" | tail -40" in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7655:5:- [P2] Verify the live marker against its manifest record — /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/scripts/check-framework-updates.sh:123-128
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7656:8:- [P2] Preserve delivery records when switching to user ceremony — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1747-1749
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7657:11:- [P2] Parse LINK targets without splitting on spaces — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1760-1760
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7660:/bin/zsh -lc "rg -n '\"title\"|\\[P[0-3]\\]|findings|overall_correctness|REJECT|APPROVE' \".claude/plans/PLAN-166/archive/codex-review-w1-round8.md\" | tail -40" in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7662:5:- [P1] Preserve rendered hashes on installer reruns — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/install.sh:2338-2339
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7663:8:- [P2] Make missing LINK records follow the preserve path — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1781-1781
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7664:11:- [P2] Apply the staged parity-classifier edit in the landing script — /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/plans/PLAN-166/OWNER-W1-LAND-step1.sh:52-54
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7667:/bin/zsh -lc "rg -n '\"title\"|\\[P[0-3]\\]|findings|overall_correctness|REJECT|APPROVE' \".claude/plans/PLAN-166/archive/codex-review-w1-round9.md\" | tail -40" in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7669:5:- [P1] Preserve the prior PROTOCOL digest on installer reruns — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/install.sh:2350-2353
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7670:8:- [P1] Retain the canonical PROTOCOL hash on user-mode skips — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:2943-2948
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7671:11:- [P2] Reject special files before backing up SPEC/v1 — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1931-1933
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7672:14:- [P2] Generate the marker when pinning pre-v1.3 releases — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1961-1964
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7675:/bin/zsh -lc "rg -n '\"title\"|\\[P[0-3]\\]|findings|overall_correctness|REJECT|APPROVE' \".claude/plans/PLAN-166/archive/codex-review-w1-round10.md\" | tail -40" in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7677:5:- [P2] Validate LINK targets before preserving ownership — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/install.sh:2311-2313
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7678:8:- [P2] Restrict link serialization to previously owned paths — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:3048-3050
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7679:11:- [P2] Include symlinks in descendant skip detection — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1834-1835
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7680:14:- [P2] Trigger ownership tests when the hash helper changes — /Users/joaocanhada/canhada-labs/ceo-orchestration/.github/workflows/smoke-install.yml:19-22
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7683:/bin/zsh -lc "rg -n '\"title\"|\\[P[0-3]\\]|findings|overall_correctness|REJECT|APPROVE' \".claude/plans/PLAN-166/archive/codex-review-w1-round11.md\" | tail -40" in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7685:5:- [P2] Reject hash-to-link transitions during continuity — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/install.sh:2326-2328
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7686:8:- [P2] Preserve records when continuity finds missing SPEC files — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/install.sh:2330-2337
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7687:11:- [P2] Keep downgrade version reporting tied to the pinned source — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1987-1992
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7688:14:- [P2] Gate forensic marker guidance on its delivery record — /Users/joaocanhada/canhada-labs/ceo-orchestration/INSTALL.md:592-595
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7691:/bin/zsh -lc "rg -n '\"title\"|\\[P[0-3]\\]|findings|overall_correctness|REJECT|APPROVE' \".claude/plans/PLAN-166/archive/codex-r6-2059.md\" | tail -40" in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7706:7643:/bin/zsh -lc 'for f in .claude/plans/PLAN-166/archive/codex-review-w1-round{6,7,8,9,10,11}.md .claude/plans/PLAN-166/archive/codex-r6-2059.md; do echo =====$f; rg -n '"'\"title\"|\\[P[0-3]\\]|findings|overall_correctness|REJECT|APPROVE' \""'$f" | tail -30; done' in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7707:7648:/bin/zsh -lc "rg -n '\"title\"|\\[P[0-3]\\]|findings|overall_correctness|REJECT|APPROVE' \".claude/plans/PLAN-166/archive/codex-review-w1-round6.md\" | tail -40" in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7708:7650:5:- [P2] Keep sanitized LINK records available for validation — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1728-1730
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7709:7653:/bin/zsh -lc "rg -n '\"title\"|\\[P[0-3]\\]|findings|overall_correctness|REJECT|APPROVE' \".claude/plans/PLAN-166/archive/codex-review-w1-round7.md\" | tail -40" in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7710:7655:5:- [P2] Verify the live marker against its manifest record — /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/scripts/check-framework-updates.sh:123-128
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7711:7656:8:- [P2] Preserve delivery records when switching to user ceremony — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1747-1749
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7712:7657:11:- [P2] Parse LINK targets without splitting on spaces — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1760-1760
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7713:7660:/bin/zsh -lc "rg -n '\"title\"|\\[P[0-3]\\]|findings|overall_correctness|REJECT|APPROVE' \".claude/plans/PLAN-166/archive/codex-review-w1-round8.md\" | tail -40" in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7714:7662:5:- [P1] Preserve rendered hashes on installer reruns — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/install.sh:2338-2339
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7715:7663:8:- [P2] Make missing LINK records follow the preserve path — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1781-1781
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7716:7664:11:- [P2] Apply the staged parity-classifier edit in the landing script — /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/plans/PLAN-166/OWNER-W1-LAND-step1.sh:52-54
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7717:7667:/bin/zsh -lc "rg -n '\"title\"|\\[P[0-3]\\]|findings|overall_correctness|REJECT|APPROVE' \".claude/plans/PLAN-166/archive/codex-review-w1-round9.md\" | tail -40" in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7718:7669:5:- [P1] Preserve the prior PROTOCOL digest on installer reruns — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/install.sh:2350-2353
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7719:7670:8:- [P1] Retain the canonical PROTOCOL hash on user-mode skips — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:2943-2948
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7720:7671:11:- [P2] Reject special files before backing up SPEC/v1 — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1931-1933
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7721:7672:14:- [P2] Generate the marker when pinning pre-v1.3 releases — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1961-1964
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7722:7675:/bin/zsh -lc "rg -n '\"title\"|\\[P[0-3]\\]|findings|overall_correctness|REJECT|APPROVE' \".claude/plans/PLAN-166/archive/codex-review-w1-round10.md\" | tail -40" in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7723:7677:5:- [P2] Validate LINK targets before preserving ownership — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/install.sh:2311-2313
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7724:7678:8:- [P2] Restrict link serialization to previously owned paths — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:3048-3050
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7725:7679:11:- [P2] Include symlinks in descendant skip detection — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1834-1835
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7726:7680:14:- [P2] Trigger ownership tests when the hash helper changes — /Users/joaocanhada/canhada-labs/ceo-orchestration/.github/workflows/smoke-install.yml:19-22
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7727:7683:/bin/zsh -lc "rg -n '\"title\"|\\[P[0-3]\\]|findings|overall_correctness|REJECT|APPROVE' \".claude/plans/PLAN-166/archive/codex-review-w1-round11.md\" | tail -40" in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7728:7685:5:- [P2] Reject hash-to-link transitions during continuity — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/install.sh:2326-2328
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7729:7686:8:- [P2] Preserve records when continuity finds missing SPEC files — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/install.sh:2330-2337
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7730:7687:11:- [P2] Keep downgrade version reporting tied to the pinned source — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1987-1992
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7731:7688:14:- [P2] Gate forensic marker guidance on its delivery record — /Users/joaocanhada/canhada-labs/ceo-orchestration/INSTALL.md:592-595
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7734:/bin/zsh -lc "nl -ba .claude/plans/PLAN-166/OWNER-W1-LAND-step1.sh | sed -n '1,260p'; printf '\\n--- PLAN167 script ---\\n'; nl -ba .claude/plans/PLAN-167/OWNER-PREPARE-TO-SIGN.sh | sed -n '1,260p'; printf '\\n--- mirror fixes ---\\n'; nl -ba .claude/plans/PLAN-166/archive/mirror-fixes.sh | sed -n '1,260p'" in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7886:    10	cd /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7916:/bin/zsh -lc 'shasum -a 256 -c .claude/plans/PLAN-166/staged-manifest.sha256 >/tmp/plan166-manifest.out 2>&1; rc=$?; echo rc=$rc; tail -40 /tmp/plan166-manifest.out; printf '"'\\nactual entries='; wc -l < .claude/plans/PLAN-166/staged-manifest.sha256; printf '\\nstaged files='; find .claude/plans/PLAN-166/staged -type f "'! -name .DS_Store | wc -l' in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:7959:/bin/zsh -lc "rg -n \"188 ADR|188 Architecture|\\| ADRs["'^'"\\n]*188|architecture decision records["'^'"\\n]*188|ADRs on disk["'^'"\\n]*188\" CLAUDE.md README.md README.pt-BR.md docs npm/README.md || true; rg -n \"189 ADR|189 Architecture|\\| ADRs["'^'"\\n]*189|architecture decision records["'^'"\\n]*189|ADRs on disk["'^'"\\n]*189\" CLAUDE.md README.md README.pt-BR.md docs npm/README.md | head -80" in /Users/joaocanhada/canhada-labs/ceo-orchestration
--- archive sizes ---
4.0K	.claude/plans/PLAN-166/archive/ceremony-porcelain-20260806-1430.txt
4.0K	.claude/plans/PLAN-166/archive/codex-review-sentinel.md
4.0K	.claude/plans/PLAN-166/archive/codex-review-w0-residuals.md
4.0K	.claude/plans/PLAN-166/archive/codex-review-w1-ceremony.md
4.0K	.claude/plans/PLAN-166/archive/codex-review-w1-round10.md
4.0K	.claude/plans/PLAN-166/archive/codex-review-w1-round11.md
4.0K	.claude/plans/PLAN-166/archive/codex-review-w1-round2.md
4.0K	.claude/plans/PLAN-166/archive/codex-review-w1-round3.md
4.0K	.claude/plans/PLAN-166/archive/codex-review-w1-round4.md
4.0K	.claude/plans/PLAN-166/archive/codex-review-w1-round5.md
4.0K	.claude/plans/PLAN-166/archive/codex-review-w1-round6.md
4.0K	.claude/plans/PLAN-166/archive/codex-review-w1-round7.md
4.0K	.claude/plans/PLAN-166/archive/codex-review-w1-round8.md
4.0K	.claude/plans/PLAN-166/archive/codex-review-w1-round9.md
4.0K	.claude/plans/PLAN-166/archive/mirror-fixes.sh
4.0K	.claude/plans/PLAN-166/archive/r6-verdict-decision.md
4.0K	.claude/plans/PLAN-168/archive/0003-plan168-baseline-map-re-gravado-62-GREEN-3-RED-run-2.patch
4.0K	.claude/plans/PLAN-168/archive/0004-plan168-restaura-token-ADOPTER-FORK-na-WARNING-do-fo.patch
 12K	.claude/plans/PLAN-168/archive/full-e2e-20260807-2017.log
 36K	.claude/plans/PLAN-168/archive/0001-plan168-W1-CI-wiring-dos-or-culos-de-propriedade.patch
 72K	.claude/plans/PLAN-168/archive/0002-plan168-W2-W3-INV-4-curada-pelo-gerador-nico-ADR-190.patch
100K	.claude/plans/PLAN-168/archive/pack-full.diff
176K	.claude/plans/PLAN-166/archive/ceremony-worktree-20260806-1430.diff
220K	.claude/plans/PLAN-166/archive/w1-staged-pack-20260806-0159.tar.gz
228K	.claude/plans/PLAN-166/archive/w1-staged-pack-final-20260806-0722.tar.gz
228K	.claude/plans/PLAN-168/archive
524K	.claude/plans/PLAN-166/archive/codex-r7-stophook-2135.md
580K	.claude/plans/PLAN-166/archive/codex-r6-2059.md
1.8M	.claude/plans/PLAN-166/archive

exec
/bin/zsh -lc 'bash .claude/scripts/check-contamination.sh' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 exited 1 in 593ms:
❌ Contamination found in the following files:
  - scripts/tests/ownership-baseline-map.txt

Allowed zones:
  - LICENSE
  - CHANGELOG.md
  - .claude/skills/domains/**
  - .claude/plans/PLAN-*.md (all plan files)
  - npm/** (NPM shim — uses owner handle in URLs)
  - .github/workflows/validate.yml
  - .github/CODEOWNERS (live config — Owner handle expected)
  - .claude/scripts/check-contamination.sh
  - .claude/scripts/check_contamination.py
  - .claude/scripts/tests/test_check_contamination.py (uses pattern as fixture)
  - CLAUDE.md (framework master context — Owner path expected)
  - RELEASE.md (release procedure — Owner path + canonical repo URL)
  - SECURITY.md (vulnerability disclosure — Owner contact + canonical URL expected)
  - docs/QUICKSTART.md (install instructions — canonical repo URL)
  - docs/UPGRADE-PROCEDURE.md (upgrade playbook — canonical repo for gh CLI)
  - docs/SLO-SLA.md (SLO doc — references named adopter for production data point)
  - .claude/scripts/check-framework-updates.sh (tool — default upstream URL)
  - templates/.github/workflows/* (copies of live CI files)

exec
/bin/zsh -lc "sed -n '1,260p' .claude/scripts/check-contamination.sh; printf '\\n--- tracked status baseline file ---\\n'; git log -1 --oneline -- scripts/tests/ownership-baseline-map.txt; grep -nE 'Canhada|joao|/Users/' scripts/tests/ownership-baseline-map.txt | head -20" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
#!/bin/bash
# check-contamination.sh — thin wrapper around check_contamination.py
#
# Sprint 3 Item E.2 (per debate consensus R-VP2): the Python
# implementation lives in `check_contamination.py`, sharing the
# file-walking + allowlist machinery with check-tier-boundaries via
# .claude/hooks/_lib/file_walker.py. This wrapper exists so the CI
# workflow step and any existing docs that invoke the .sh path keep
# working without change. Sprint 4+ may retire the wrapper.
#
# Exit codes are preserved:
#   0 — clean
#   1 — contamination found
#   2 — fatal error (git not available, etc.)

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"

if ! command -v python3 >/dev/null 2>&1; then
  echo "FATAL: python3 not found" >&2
  exit 2
fi

exec python3 "$REPO_ROOT/.claude/scripts/check_contamination.py" "$@"

--- tracked status baseline file ---
36eb667 feat(PLAN-167): W3 rail (4 rodadas, teto) + W4 pack pronto para assinatura
2:   table:  /tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553/scripts/tests/ownership_table.tsv
3:   source: /tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553

exec
/bin/zsh -lc "grep -n \"plans\\|ALLOW\" .claude/scripts/check_contamination.py | head -100 && sed -n '30,150p' .claude/scripts/check_contamination.py" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
28:Exact paths + glob patterns (see `_ALLOWLIST_*` below). Binary file
90:_ALLOWLIST_EXACT = {
190:_ALLOWLIST_GLOBS = {
194:    # Plan artifacts (all file types under .claude/plans/, including
199:    ".claude/plans/*",
271:        path_allowlist_exact=_ALLOWLIST_EXACT,
272:        path_allowlist_globs=_ALLOWLIST_GLOBS,
318:    print("  - .claude/plans/PLAN-*.md (all plan files)")

## Exit codes

- 0 — clean
- 1 — contamination found (printed to stdout)
- 2 — fatal error
"""

from __future__ import annotations

import re
import sys
import unicodedata
from pathlib import Path
from typing import List

# Import the shared walker from _lib/
_HOOKS_DIR = Path(__file__).resolve().parent.parent / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))
from _lib.file_walker import FileWalker  # noqa: E402


# Identity tokens that must not leak into the distributed framework core.
#
# Two groups of alternatives:
#   1. EXAMPLE placeholders (acme ledger / example owner) — a maintainer
#      publishing their own fork should replace these with their personal
#      handle / private project names so this lint guards their identity
#      instead of the example ones.
#   2. The maintainer's REAL identity ([Jj]oao[\s._\-]*[Cc]anhada and the
#      bare first name Jo[aã]o) — these defend THIS framework's published
#      core (e.g. .claude/skills/core/) against shipping the real name.
#      They were dropped from the live pattern at some point while the
#      docstring still advertised them, turning the guard false-green
#      (it exited 0 while "João" was provably present in non-allowlisted
#      shipped files). Restored here so the guard actually fails-closed.
#      The bare Jo[aã]o alternative is intentionally case-sensitive
#      (capital J + a/ã + o) so it catches the proper noun ("João",
#      "Joao") without over-matching common lowercase substrings.
_PATTERN = re.compile(
    r"acme\s*[Ll]edger|example[\s._\-]*owner|Example\s+Owner"
    r"|[Jj]oao[\s._\-]*[Cc]anhada|Jo[aã]o"
)

# Allowlist — mirrors the case block in check-contamination.sh
#
# Philosophy: the check defends the FRAMEWORK CORE (hooks, scripts,
# skills/core, skills/frontend, templates) from leaking project-specific
# references. It does NOT apply to:
#   - Historical decision records (ADRs carry Accepted-By owner handles)
#   - Plan artifacts (PLAN-*/ subfolders document adopter context)
#   - Adopter-facing documentation (docs/ explains framework to adopters)
#   - Adopter-specific tooling (check-originator-residue, compare-adopters,
#     adopter-metrics, log-friction — explicitly about adopter workflow)
#   - Published compliance contract (SPEC/v1/ references concrete examples)
#   - Benchmarks against named peers (benchmarks/public/vs-*.md)
#   - Case studies (docs/case-studies/ inherits adopter names by design)
#   - Issue templates (.github/ISSUE_TEMPLATE surfaces project context)
#   - Historical archives (CLAUDE_FULL.md is the overflow-log for CLAUDE.md)
_ALLOWLIST_EXACT = {
    "LICENSE",
    "CHANGELOG.md",
    # ---- S214: audit report + plugin builder reference identity tokens by-design ----
    "MORNING-REPORT-S214.md",   # CTO audit report that AUDITS the Owner-identity leak (must name the tokens)
    "REPORT-S225-fable-audit.md",  # S225 Fable audit: documents identity-leak findings (E5-F10, E7) — same rationale as MORNING-REPORT-S214
    "scripts/build-plugin.py",  # plugin builder: sanitize_paths()/identity_report() match these tokens to strip/report them (same rationale as check_contamination.py itself)
    ".github/workflows/validate.yml",
    ".github/CODEOWNERS",
    ".claude/scripts/check-contamination.sh",
    ".claude/scripts/check_contamination.py",
    ".claude/scripts/tests/test_check_contamination.py",
    ".claude/hooks/tests/test_check_canonical_edit.py",
    "CLAUDE.md",
    "CLAUDE_FULL.md",
    "RELEASE.md",
    "SECURITY.md",
    "docs/QUICKSTART.md",
    "docs/QUICKSTART.pt-BR.md",
    "docs/GUIA-COMPLETO.md",
    "docs/GUIA-COMPLETO.pt-BR.md",
    "docs/HONEST-LIMITATIONS.md",
    "docs/ROADMAP-CLOSURE.md",
    "docs/threat-model.md",
    "docs/soc2-audit-mapping.md",
    "docs/fixture-budget.md",
    "docs/opus-4-7-baseline.md",
    "docs/opus-4-7-operations.md",
    "docs/opus-4-7-phase6-report.md",
    "docs/UPGRADE-PROCEDURE.md",
    "docs/SLO-SLA.md",
    ".claude/scripts/check-framework-updates.sh",
    ".claude/scripts/adopter-metrics.py",
    ".claude/scripts/compare-adopters.py",
    ".claude/scripts/check-originator-residue.py",
    ".claude/scripts/log-friction.sh",
    ".claude/scripts/tests/test_admin_invite.py",
    ".claude/scripts/tests/test_check_originator_residue.py",
    ".claude/scripts/tests/test_compare_adopters.py",
    ".claude/policies/.drift-manifest.json",
    # ---- audit-v2 Wave C-bis hot-fix (2026-04-27) ------------------
    # Pre-existing legitimate references to the Owner / canonical
    # repo URL surfaced after CLAUDE.md ADR-count drift was fixed
    # (which was masking these in CI). Each entry below is a
    # human-reviewed legitimate reference (Owner attribution in
    # ceremony scripts, GPG roster, design-intent github URLs, etc).
    # ----------------------------------------------------------------
    # Hook-lib files with Owner attribution in docstrings (canonical;
    # fix would require new sentinel ceremony — defer to future cleanup
    # ADR; allowlist now to unblock CI):
    ".claude/hooks/_lib/escalation_signals.py",
    ".claude/hooks/_lib/rag_events.py",
    ".claude/hooks/check_tier_policy.py",
    # Owner GPG fingerprint roster (by design — references Owner's key):
    ".claude/sentinel-signers.txt",
    ".claude/skill-patch-signers.txt",
    # Operational docs with design-intent github.com/<owner>/ URLs
    # (issue tracker, release page, etc.):
    "docs/READINESS-STATUS.md",
    "docs/CEO-MODEL-ROUTING.md",
    "docs/ROADMAP.md",

exec
/bin/zsh -lc "sed -n '180,215p' .claude/scripts/check_contamination.py; grep -n \"def .*allow\\|path_allowlist_globs\" -n .claude/hooks/_lib/file_walker.py | head -50; sed -n '80,150p' .claude/hooks/_lib/file_walker.py" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
    # sentinel-signers.txt / skill-patch-signers.txt above):
    ".claude/security/sentinel-signers-registry.yaml",
    # Owner brief + internal design docs (Owner attribution / setup paths;
    # like the operational docs allowlisted above):
    "BUNDLE-OWNER-BRIEF.md",
    "docs/GIF-CAPTURE-SPEC.md",
    "docs/PERMISSION-MODEL-DESIGN.md",
    "docs/security-bash-canonical-guards.md",
}

_ALLOWLIST_GLOBS = {
    # NOTE: fnmatch `*` matches across `/` boundaries here (unlike the
    # `glob` module). A single `*` after the directory prefix is enough
    # to cover all nested files — no need for `**`.
    # Plan artifacts (all file types under .claude/plans/, including
    # WAR-ROOM/, SPRINT-NN-ROADMAP.md, PLAN-NNN-*.md, PLAN-NNN/...).
    # Wave C-bis (2026-04-27): broadened from `PLAN-*.md` + `PLAN-*`
    # to `*` so non-PLAN- artifacts (WAR-ROOM, SPRINT-NN, README) get
    # covered without per-file additions.
    ".claude/plans/*",
    # Domain squads (by design — each domain lists real-world owners)
    ".claude/skills/domains/*",
    # CI workflow templates distributed to adopters
    "templates/.github/workflows/*",
    # NPM shim — URLs reference canonical repo owner
    "npm/*",
    # ADRs — architectural decision records carry Owner Accepted-By
    ".claude/adr/ADR-*.md",
    # Published SPEC — concrete examples reference owner/projects
    "SPEC/*",
    # Docs subfolders that document the framework's ecosystem:
    # case studies, research (external competitive analysis),
    # site HTML, etc.
    "docs/case-studies/*",
    "docs/research/*",
    "docs/site/*",
13:        path_allowlist_globs={".claude/skills/domains/*"},
60:        path_allowlist_globs: Optional[Set[str]] = None,
70:        self.path_allowlist_globs = path_allowlist_globs or set()
117:    def is_allowlisted(self, path: Path) -> bool:
132:        for pattern in self.path_allowlist_globs:
141:    def iter_non_allowlisted(self) -> Iterable[Path]:
    def _iter_git_tracked(self) -> Iterator[Path]:
        """Enumerate `git ls-files` output. Safe on missing git / bad repo."""
        try:
            proc = subprocess.run(
                ["git", "ls-files", "-z"],
                cwd=str(self.repo_root),
                capture_output=True,
                check=False,
                timeout=30,
            )
        except (FileNotFoundError, subprocess.SubprocessError):
            return
        if proc.returncode != 0:
            return
        # -z emits NUL-separated paths
        raw = proc.stdout.decode("utf-8", errors="replace")
        for rel in raw.split("\x00"):
            if not rel:
                continue
            p = self.repo_root / rel
            if self.suffixes and p.suffix not in self.suffixes:
                continue
            yield p

    def _iter_filesystem(self) -> Iterator[Path]:
        """Walk repo_root via rglob. Skips subdirs in skip_subdir_names."""
        for p in self.repo_root.rglob("*"):
            if not p.is_file():
                continue
            if self.suffixes and p.suffix not in self.suffixes:
                continue
            # Skip if any ancestor directory name is in skip_subdir_names
            parts = set(p.relative_to(self.repo_root).parts[:-1])
            if self.skip_subdir_names and parts & self.skip_subdir_names:
                continue
            yield p

    def is_allowlisted(self, path: Path) -> bool:
        """Return True if `path` matches any allowlist style.

        Supports:
        - exact relative path match
        - glob against relative path (fnmatch)
        - substring token anywhere in the absolute path string
        """
        try:
            rel = str(path.relative_to(self.repo_root))
        except ValueError:
            rel = str(path)

        if rel in self.path_allowlist_exact:
            return True
        for pattern in self.path_allowlist_globs:
            if fnmatch.fnmatch(rel, pattern):
                return True
        abs_str = str(path)
        for token in self.path_allowlist_tokens:
            if token in abs_str:
                return True
        return False

    def iter_non_allowlisted(self) -> Iterable[Path]:
        """Convenience: iterate files that are NOT allowlisted."""
        for p in self.iter_files():
            if not self.is_allowlisted(p):
                yield p

exec
/bin/zsh -lc "grep -n \"framework-version\\|VERSION_SITES\\|version sites\\|EXPECTED_SITE\" .claude/scripts/local/_release_bump_sites.py .claude/scripts/local/verify-counts.sh | head -120; git status --short .claude/scripts/local/_release_bump_sites.py .claude/scripts/local/verify-counts.sh; git log -1 --oneline -- .claude/scripts/local/_release_bump_sites.py .claude/scripts/local/verify-counts.sh" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
.claude/scripts/local/_release_bump_sites.py:30:# verify-counts' VERSION_SITES; SBOM.md / SECURITY.md / VERSIONING.md are
.claude/scripts/local/_release_bump_sites.py:36:# verify-counts' VERSION_SITES also watches "Current MINOR (vX.Y.x)" and
.claude/scripts/local/_release_bump_sites.py:95:    # --- the support window (oracle: verify-counts VERSION_SITES modes
.claude/scripts/local/_release_bump_sites.py:257:    p_bump = sub.add_parser("bump", help="rewrite the version sites")
.claude/scripts/local/verify-counts.sh:1014:    VERSION_SITES = [
.claude/scripts/local/verify-counts.sh:1043:    for doc, rx, mode in VERSION_SITES:
f492545 governance(PLAN-166): W0 residuais round 2 (12/12) + codex round (2 P2)

exec
/bin/zsh -lc "nl -ba .claude/scripts/local/_release_bump_sites.py | sed -n '45,150p'; nl -ba .claude/scripts/local/verify-counts.sh | sed -n '995,1065p'; grep -R \"_release_bump_sites.py\" -n .claude/commands .claude/scripts/local docs RELEASE.md | head -80" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
    45	# cannot value-check it either (it derives prev="" at X.0), and a MAJOR
    46	# support-window transition is release-train judgment, not sed.
    47	# ============================================================================
    48	"""Release version-site table + writer (stdlib only, Python >= 3.9)."""
    49	
    50	from __future__ import annotations
    51	
    52	import argparse
    53	import os
    54	import re
    55	import sys
    56	from typing import Callable, List, Optional, Sequence, Tuple
    57	
    58	SEMVER = r"\d+\.\d+\.\d+"
    59	STAMP_RX = r"(last-reviewed: )(\d{4}-\d{2}-\d{2})( +v)(" + SEMVER + r")"
    60	DATE_RX = re.compile(r"\A\d{4}-\d{2}-\d{2}\Z")
    61	
    62	# Kinds:
    63	#   "plain"      — literal regex substitution, no stamp semantics.
    64	#   "stamp"      — "last-reviewed: <date> v<version>"; skipped wholesale when
    65	#                  the version already equals the target (unless --restamp).
    66	#   "minor"      — support-window site carrying the TARGET's minor (vX.Y.x).
    67	#   "prev_minor" — support-window site carrying the minor immediately BEFORE
    68	#                  the target; not derivable at X.0.0 (skipped loudly there).
    69	PLAIN = "plain"
    70	STAMP = "stamp"
    71	MINOR = "minor"
    72	PREV_MINOR = "prev_minor"
    73	
    74	# (path, kind, pattern) — patterns anchored exactly as their oracle checks
    75	# them, so historical version mentions elsewhere in the file are never touched.
    76	_SITES: List[Tuple[str, str, str]] = [
    77	    ("VERSION", PLAIN, r"\A\s*" + SEMVER + r"\s*\Z"),
    78	    ("npm/package.json", PLAIN, r'("version"\s*:\s*")' + SEMVER + r'(")'),
    79	    ("pyproject.toml", PLAIN, r'(?m)^(version\s*=\s*")' + SEMVER + r'(")'),
    80	    ("INSTALL.md", PLAIN, r"(--pin v)" + SEMVER),
    81	    (
    82	        "docs/ARCHITECTURE.md",
    83	        PLAIN,
    84	        r"(currently\s+v)" + SEMVER + r"(, aligned with the repo)",
    85	    ),
    86	    # README.md and CLAUDE.md are deliberately NOT rows here: neither is a
    87	    # version site. `VERSION=` never existed in either (verify-counts dropped
    88	    # its dead rules for both in S291 — `git log -S 'VERSION='` finds no
    89	    # commit that added one — and the release checklist states the same). A
    90	    # writer row for a site no oracle watches would be that dead rule
    91	    # reintroduced on the WRITE side: the day someone adds a `VERSION=` line
    92	    # to README.md, the bump would rewrite a file every other surface
    93	    # declares out of scope.
    94	    ("SBOM.md", PLAIN, r"(\*\*Version:\*\* `)" + SEMVER + r"(`)"),
    95	    # --- the support window (oracle: verify-counts VERSION_SITES modes
    96	    #     "minor"/"prev_minor", S293). Patterns anchored exactly as the
    97	    #     oracle's — SECURITY.md bolds the label, VERSIONING.md does not. ---
    98	    ("SECURITY.md", MINOR, r"(\*\*Current MINOR\*\* \(`v)\d+\.\d+(\.x`\))"),
    99	    ("VERSIONING.md", MINOR, r"(Current MINOR \(`v)\d+\.\d+(\.x`\))"),
   100	    ("SECURITY.md", PREV_MINOR, r"(\*\*Previous MINOR\*\* \(`v)\d+\.\d+(\.x`\))"),
   101	    ("VERSIONING.md", PREV_MINOR, r"(Previous MINOR \(`v)\d+\.\d+(\.x`\))"),
   102	    # --- the review stamps (idempotence-critical; the table IS the census,
   103	    #     a numeral here would be a mirror that drifts) ---
   104	    ("npm/README.md", STAMP, STAMP_RX),
   105	    ("SBOM.md", STAMP, STAMP_RX),
   106	    ("SECURITY.md", STAMP, STAMP_RX),
   107	    ("VERSIONING.md", STAMP, STAMP_RX),
   108	]
   109	
   110	# Written by the bump PHASE but not by this module: `build-plugin.py
   111	# --write-manifests` regenerates them from VERSION. They belong in any
   112	# derived restore/guard list, which is why they are exported here instead of
   113	# being re-typed by every caller (the duplicated-list failure this module
   114	# exists to kill).
   115	GENERATED_BY_BUMP: List[str] = [
   116	    ".claude-plugin/plugin.json",
   117	    ".claude-plugin/marketplace.json",
   118	]
   119	
   120	
   121	def site_paths(include_generated: bool = False) -> List[str]:
   122	    """Every path this module may write, de-duplicated, in table order."""
   123	    out: List[str] = []
   124	    for path, _kind, _rx in _SITES:
   125	        if path not in out:
   126	            out.append(path)
   127	    if include_generated:
   128	        for path in GENERATED_BY_BUMP:
   129	            if path not in out:
   130	                out.append(path)
   131	    return out
   132	
   133	
   134	def _plain_replacement(pattern: str, target: str) -> str:
   135	    """Replacement string for a PLAIN site, rebuilt from its group count."""
   136	    if pattern.startswith(r"\A"):  # the bare VERSION file
   137	        return target + "\n"
   138	    groups = re.compile(pattern).groups
   139	    if groups == 0:
   140	        return target
   141	    if groups == 1:
   142	        return r"\g<1>" + target
   143	    return r"\g<1>" + target + r"\g<2>"
   144	
   145	
   146	def _stamp_replacer(
   147	    target: str, today: str, restamp: bool
   148	) -> Callable[["re.Match"], str]:
   149	    def _repl(m: "re.Match") -> str:
   150	        if not restamp and m.group(4) == target:
   995	            "%s:%d: thousands-shaped approximation '%s' is consumed by NO "
   996	            "approx rule — give it a live metric + matcher, or delete the "
   997	            "numeral  (rule: approx/unmatched-sweep)"
   998	            % (_doc, _text.count("\n", 0, _m.start()) + 1, _m.group(0).strip())
   999	        )
  1000	
  1001	# ---- E9-F10 (iii): VERSION-string coherence ----
  1002	# Anchored to the current-version DECLARATION sites ONLY (not historical
  1003	# CHANGELOG prose). Each (doc, regex) yields the literal version string, which
  1004	# must equal the live VERSION file. npm/package.json is read here (it is not in
  1005	# DOCS). A doc with zero matches contributes no violation.
  1006	if live_version:
  1007	    # S291 (pair-rail R2, P2): `VERSION=` NEVER existed in CLAUDE.md or
  1008	    # README.md — `git log -S 'VERSION='` finds no commit that added or
  1009	    # removed it. Both rules were dead from birth (the `registered` class
  1010	    # again), while the release checklist advertised them as checked.
  1011	    # Removed rather than faked: neither doc declares a version literal by
  1012	    # design (they point at the VERSION file). Every remaining site is
  1013	    # liveness-accounted below — a site that matches nothing now FAILS.
  1014	    VERSION_SITES = [
  1015	        ("INSTALL.md", r'--pin v(\d+\.\d+\.\d+)', "full"),
  1016	        # PLAN-161 V1 — current-version declaration sites in the newly-watched
  1017	        # docs (the npm README review stamp is a deliberate release tripwire:
  1018	        # a version bump forces a fresh review of the npm-facing copy).
  1019	        ("docs/ARCHITECTURE.md", r'currently\s+v(\d+\.\d+\.\d+), aligned with the repo', "full"),
  1020	        ("npm/README.md", r'last-reviewed: \d{4}-\d{2}-\d{2} v(\d+\.\d+\.\d+)', "full"),
  1021	        # S293 (codex NO-GO no rc.1 do v1.3.0 — P0s 2-4): TRÊS declarações de
  1022	        # versão corrente que estavam FORA desta lista e ficaram stale no
  1023	        # bump (a classe unwatched-doc de S291, de novo). SBOM declara o
  1024	        # triple completo; SECURITY/VERSIONING declaram a janela de suporte
  1025	        # como vMAJOR.MINOR.x — comparadas ao major.minor do VERSION vivo.
  1026	        ("SBOM.md", r'\*\*Version:\*\* `(\d+\.\d+\.\d+)`', "full"),
  1027	        ("SECURITY.md", r'\*\*Current MINOR\*\* \(`v(\d+\.\d+)\.x`\)', "minor"),
  1028	        ("VERSIONING.md", r'Current MINOR \(`v(\d+\.\d+)\.x`\)', "minor"),
  1029	        # S293 r3 P1: vigiar SÓ o Current deixa o PREVIOUS envelhecer em
  1030	        # silêncio — e a janela de suporte publicada é uma promessa a
  1031	        # adopters, não decoração. Previous = minor imediatamente anterior
  1032	        # ao vivo (rebase de MAJOR não é expressável aqui e falharia alto,
  1033	        # que é o comportamento correto para uma transição que exige juízo).
  1034	        ("SECURITY.md", r'\*\*Previous MINOR\*\* \(`v(\d+\.\d+)\.x`\)', "prev_minor"),
  1035	        ("VERSIONING.md", r'Previous MINOR \(`v(\d+\.\d+)\.x`\)', "prev_minor"),
  1036	    ]
  1037	    _live_minor = ".".join(live_version.split(".")[:2])
  1038	    try:
  1039	        _maj, _min = (int(x) for x in _live_minor.split("."))
  1040	        _prev_minor = "%d.%d" % (_maj, _min - 1) if _min > 0 else ""
  1041	    except ValueError:
  1042	        _prev_minor = ""
  1043	    for doc, rx, mode in VERSION_SITES:
  1044	        _text = texts.get(doc, "")
  1045	        # S293: SBOM/SECURITY/VERSIONING não estão em DOCS (as regras de
  1046	        # contagem não se aplicam a eles) — carregue direto, senão o site
  1047	        # nasce "morto" sobre texto nunca lido.
  1048	        if not _text:
  1049	            _p = os.path.join(root, doc)
  1050	            if os.path.isfile(_p):
  1051	                try:
  1052	                    _text = open(_p, encoding="utf-8").read()
  1053	                except OSError:
  1054	                    _text = ""
  1055	        _hits = 0
  1056	        if mode == "full":
  1057	            _expected = live_version
  1058	        elif mode == "prev_minor":
  1059	            _expected = _prev_minor
  1060	        else:
  1061	            _expected = _live_minor
  1062	        if not _expected:
  1063	            # Sem previous derivável (X.0): o site não é checável por valor;
  1064	            # a liveness abaixo ainda exige que ele EXISTA.
  1065	            _expected = None
Binary file .claude/scripts/local/__pycache__/_release_bump_sites.cpython-311.pyc matches
.claude/scripts/local/release.sh:44:#                    list is DERIVED from _release_bump_sites.py, never typed.
.claude/scripts/local/release.sh:105:BUMP_SITES=".claude/scripts/local/_release_bump_sites.py"
.claude/scripts/local/release.sh:424:# The site table lives in `_release_bump_sites.py` and NOWHERE else: this
.claude/scripts/local/release.sh:538:  # mirror it into _release_bump_sites.py.
.claude/scripts/local/release.sh:570:${TARGET_TAG}. The site table is .claude/scripts/local/_release_bump_sites.py.
.claude/scripts/local/_release_bump_sites.py:3:# _release_bump_sites.py — the ONE source of truth for the release version
.claude/scripts/local/_release_bump_sites.py:242:        prog="_release_bump_sites.py",

exec
/bin/zsh -lc "grep -R \"framework-version\\|_release_bump_sites\\|VERSION_SITES\" -n .claude/plans/PLAN-168/archive .claude/plans/PLAN-167/W4-approved.md 2>/dev/null | head -120; grep -R \"framework-version\\|_release_bump_sites\\|VERSION_SITES\" -n .claude/plans/PLAN-166 2>/dev/null | head -120" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
.claude/plans/PLAN-168/archive/0002-plan168-W2-W3-INV-4-curada-pelo-gerador-nico-ADR-190.patch:361:-- **Install/upgrade ownership is ONE decision, not a cascade (PLAN-167, landed `7c0828a`).** Whether the framework owns `PROTOCOL.md`, `SPEC/v1` or `.claude/.framework-version` is answered by `_ownership_verdict()` in `scripts/_framework_manifest_set.sh` — a pure function of 10 dimensions returning `"<VERDICT> <HASH_SOURCE>"`. `install.sh` and `upgrade.sh` **observe → call → execute**; they do not decide. Contract: `docs/ownership-decision-table.md`. Truth: `scripts/tests/ownership_table.tsv`. Two oracles read that same table — a unit one (`test-ownership-verdict-unit.sh`, milliseconds: catches a wrong DECISION) and an e2e one (`test-ownership-table.sh`, ~25 min of real installs: catches a wrong OBSERVATION). **The e2e ends 58 green / 4 red by design**; the 4 are named with causes: `OWN-0024`/`0027` are defects in the TEST; `OWN-0016` and `OWN-0074` are product defects (the latter is INV-4 surfacing in the recorded digest) — closing in PLAN-168. An all-green run means the table changed — stop and find out why. Adding a branch that decides ownership locally re-opens the class this replaced.
.claude/plans/PLAN-168/archive/0002-plan168-W2-W3-INV-4-curada-pelo-gerador-nico-ADR-190.patch:362:+- **Install/upgrade ownership is ONE decision, not a cascade (PLAN-167, landed `7c0828a`; PLAN-168 closed the follow-ups).** Whether the framework owns `PROTOCOL.md`, `SPEC/v1` or `.claude/.framework-version` is answered by `_ownership_verdict()` in `scripts/_framework_manifest_set.sh` — a pure function of 10 dimensions returning `"<VERDICT> <HASH_SOURCE>"`. `install.sh` and `upgrade.sh` **observe → call → execute**; they do not decide. Contract: `docs/ownership-decision-table.md`. Truth: `scripts/tests/ownership_table.tsv`. Two oracles read that same table — a unit one (`test-ownership-verdict-unit.sh`, milliseconds: catches a wrong DECISION) and an e2e one (`test-ownership-table.sh`, ~25 min of real installs: catches a wrong OBSERVATION), plus the INV-4 e2e (`test-protocol-pointer-inv4.sh`: install and upgrade render the pointer through the ONE shared generator — byte-identical, degraded bodies CURED with backup, adopter edits preserved). CI: the unit oracle + fast controls run per-PR in `smoke-install.yml`; the full e2e runs in `ownership-nightly.yml`, whose gate (`ownership-nightly-gate.sh`) compares the exact RED id set against `ownership-expected-reds.txt` and fails on ANY difference. **The e2e ends 62 green / 3 red by design** (`OWN-0024`/`0027` test defects, `OWN-0016` product — causes in ADR-190; `OWN-0074` was closed by PLAN-168 W2). An all-green run means the table changed — stop and find out why. Adding a branch that decides ownership locally re-opens the class this replaced.
.claude/plans/PLAN-168/archive/pack-full.diff:539:-- **Install/upgrade ownership is ONE decision, not a cascade (PLAN-167, landed `7c0828a`).** Whether the framework owns `PROTOCOL.md`, `SPEC/v1` or `.claude/.framework-version` is answered by `_ownership_verdict()` in `scripts/_framework_manifest_set.sh` — a pure function of 10 dimensions returning `"<VERDICT> <HASH_SOURCE>"`. `install.sh` and `upgrade.sh` **observe → call → execute**; they do not decide. Contract: `docs/ownership-decision-table.md`. Truth: `scripts/tests/ownership_table.tsv`. Two oracles read that same table — a unit one (`test-ownership-verdict-unit.sh`, milliseconds: catches a wrong DECISION) and an e2e one (`test-ownership-table.sh`, ~25 min of real installs: catches a wrong OBSERVATION). **The e2e ends 58 green / 4 red by design**; the 4 are named with causes: `OWN-0024`/`0027` are defects in the TEST; `OWN-0016` and `OWN-0074` are product defects (the latter is INV-4 surfacing in the recorded digest) — closing in PLAN-168. An all-green run means the table changed — stop and find out why. Adding a branch that decides ownership locally re-opens the class this replaced.
.claude/plans/PLAN-168/archive/pack-full.diff:540:+- **Install/upgrade ownership is ONE decision, not a cascade (PLAN-167, landed `7c0828a`; PLAN-168 closed the follow-ups).** Whether the framework owns `PROTOCOL.md`, `SPEC/v1` or `.claude/.framework-version` is answered by `_ownership_verdict()` in `scripts/_framework_manifest_set.sh` — a pure function of 10 dimensions returning `"<VERDICT> <HASH_SOURCE>"`. `install.sh` and `upgrade.sh` **observe → call → execute**; they do not decide. Contract: `docs/ownership-decision-table.md`. Truth: `scripts/tests/ownership_table.tsv`. Two oracles read that same table — a unit one (`test-ownership-verdict-unit.sh`, milliseconds: catches a wrong DECISION) and an e2e one (`test-ownership-table.sh`, ~25 min of real installs: catches a wrong OBSERVATION), plus the INV-4 e2e (`test-protocol-pointer-inv4.sh`: install and upgrade render the pointer through the ONE shared generator — byte-identical, degraded bodies CURED with backup, adopter edits preserved). CI: the unit oracle + fast controls run per-PR in `smoke-install.yml`; the full e2e runs in `ownership-nightly.yml`, whose gate (`ownership-nightly-gate.sh`) compares the exact RED id set against `ownership-expected-reds.txt` and fails on ANY difference. **The e2e ends 62 green / 3 red by design** (`OWN-0024`/`0027` test defects, `OWN-0016` product — causes in ADR-190; `OWN-0074` was closed by PLAN-168 W2). An all-green run means the table changed — stop and find out why. Adding a branch that decides ownership locally re-opens the class this replaced.
.claude/plans/PLAN-166/OWNER-W1-LAND-step1b.sh:49:.claude/.framework-version
.claude/plans/PLAN-166/OWNER-W1-LAND-step1.sh:46:  .claude/.framework-version \
.claude/plans/PLAN-166/W1-land-runbook.md:63:  .claude/scripts/local/_release_bump_sites.py \
.claude/plans/PLAN-166/W1-land-runbook.md:81:| `.claude/scripts/local/_release_bump_sites.py` | `11719fbfb6207235e487624879eb09aa079e8392e14b9e4beeccb556ca3bf2b8` | in-flight (W0); W1-C authored its §1a snippet against `0387725...c226` | deferred-apply §1a |
.claude/plans/PLAN-166/W1-land-runbook.md:97:> `test_release_bump_sites.py`, `test_verify_counts.py` dirty at closure
.claude/plans/PLAN-166/W1-land-runbook.md:157:cp -p "$S/.claude/.framework-version"                            .claude/.framework-version
.claude/plans/PLAN-166/W1-land-runbook.md:235:`test_release_bump_sites.py::test_dry_run_leaves_index_and_worktree_clean`
.claude/plans/PLAN-166/W1-land-runbook.md:237:synthesized fixture repo does not create `.claude/.framework-version`;
.claude/plans/PLAN-166/W1-land-runbook.md:243:    (repo / ".claude" / ".framework-version").write_text(version + "\n", encoding="utf-8")
.claude/plans/PLAN-166/W1-land-runbook.md:252:  `.claude/scripts/tests/test_release_bump_sites.py`, then ADD all THREE
.claude/plans/PLAN-166/W1-land-runbook.md:269:grep -q '\.framework-version' .claude/scripts/local/_release_bump_sites.py \
.claude/plans/PLAN-166/W1-land-runbook.md:271:grep -q '\.framework-version' .claude/scripts/local/verify-counts.sh \
.claude/plans/PLAN-166/W1-land-runbook.md:352:  .claude/.framework-version \
.claude/plans/PLAN-166/W1-land-runbook.md:386:   (group A) asserts `.claude/.framework-version == VERSION`
.claude/plans/PLAN-166/archive/codex-r6-2059.md:20: A .claude/.framework-version
.claude/plans/PLAN-166/archive/codex-r6-2059.md:55: .claude/.framework-version                         |   1 +
.claude/plans/PLAN-166/archive/codex-r6-2059.md:136:+# .claude/.framework-version instead — but the marker is only TRUSTED when
.claude/plans/PLAN-166/archive/codex-r6-2059.md:142:+#   2. <root>/.claude/.framework-version  when well-formed AND
.claude/plans/PLAN-166/archive/codex-r6-2059.md:161:+    if [ -f "$cur/.claude/.framework-version" ] || [ -f "$cur/VERSION" ]; then
.claude/plans/PLAN-166/archive/codex-r6-2059.md:168:+    echo "fatal: no .claude/.framework-version or VERSION found (looked from $(pwd))" >&2
.claude/plans/PLAN-166/archive/codex-r6-2059.md:171:+  MARKER="$VROOT/.claude/.framework-version"
.claude/plans/PLAN-166/archive/codex-r6-2059.md:176:+      MARKER_REC="$(grep -E '^([0-9a-f]{64}|LINK)  \.claude/\.framework-version(  |$)' "$MANIFEST" 2>/dev/null | head -1 || true)"
.claude/plans/PLAN-166/archive/codex-r6-2059.md:191:+          _rec_tgt="${MARKER_REC#LINK  .claude/.framework-version  }"
.claude/plans/PLAN-166/archive/codex-r6-2059.md:207:+        log "note: .claude/.framework-version does NOT match its delivery record (edited, redirected, or no digest tool available) — falling back to VERSION"
.claude/plans/PLAN-166/archive/codex-r6-2059.md:212:+          VSOURCE="marker (.claude/.framework-version, delivery-recorded)"
.claude/plans/PLAN-166/archive/codex-r6-2059.md:214:+          log "note: .claude/.framework-version malformed ('$MARKER_VAL') — falling back to VERSION"
.claude/plans/PLAN-166/archive/codex-r6-2059.md:224:+      log "note: .claude/.framework-version present but NOT delivery-recorded in .claude/.install-manifest.sha256 — falling back to VERSION (r20: a pre-existing adopter marker is not the framework's)"
.claude/plans/PLAN-166/archive/codex-r6-2059.md:440:+      # framework version marker `.claude/.framework-version` is a TRACKED
.claude/plans/PLAN-166/archive/codex-r6-2059.md:450:+      - name: Assert framework-version marker matches VERSION
.claude/plans/PLAN-166/archive/codex-r6-2059.md:454:+          if [[ ! -f .claude/.framework-version ]]; then
.claude/plans/PLAN-166/archive/codex-r6-2059.md:455:+            echo "::error::.claude/.framework-version is missing — it is a tracked file (PLAN-166 F3 / ADR-155-AMEND-1); a release checkout without it must not ship"
.claude/plans/PLAN-166/archive/codex-r6-2059.md:458:+          MARKER="$(tr -d '[:space:]' < .claude/.framework-version)"
.claude/plans/PLAN-166/archive/codex-r6-2059.md:460:+            echo "::error::.claude/.framework-version ('$MARKER') does not match VERSION ('$FILE') — the marker is byte-identical to VERSION by contract (Forma A (ii), fail-closed)"
.claude/plans/PLAN-166/archive/codex-r6-2059.md:463:+          echo "OK: .claude/.framework-version=$MARKER matches VERSION"
.claude/plans/PLAN-166/archive/codex-r6-2059.md:652:+      - ".claude/.framework-version"
.claude/plans/PLAN-166/archive/codex-r6-2059.md:678:+      - ".claude/.framework-version"
.claude/plans/PLAN-166/archive/codex-r6-2059.md:773:+      # .claude/.framework-version) across install -> upgrade -> doctor ->
.claude/plans/PLAN-166/archive/codex-r6-2059.md:802:+    # SPEC/v1 and .claude/.framework-version are CONDITIONAL on the
.claude/plans/PLAN-166/archive/codex-r6-2059.md:828:+    if _dr_delivered '\.claude/\.framework-version(  |$)'; then
.claude/plans/PLAN-166/archive/codex-r6-2059.md:922:+# .claude/.framework-version) across install → upgrade → doctor → updater.
.claude/plans/PLAN-166/archive/codex-r6-2059.md:992:+if [ ! -f "$SOURCE_DIR/.claude/.framework-version" ]; then
.claude/plans/PLAN-166/archive/codex-r6-2059.md:993:+  echo "FATAL: source has no .claude/.framework-version (F3 marker missing)" >&2
.claude/plans/PLAN-166/archive/codex-r6-2059.md:1040:+MARKER_REL=".claude/.framework-version"
.claude/plans/PLAN-166/archive/codex-r6-2059.md:1061:+manifest_has "$T1" '\.claude/\.framework-version(  |$)'    && ok "baseline records marker"      || bad "baseline has NO marker record"
.claude/plans/PLAN-166/archive/codex-r6-2059.md:1135:+sed -i.bak '/  \.claude\/\.framework-version/d' "$T1/$MANIFEST_REL" 2>/dev/null \
.claude/plans/PLAN-166/archive/codex-r6-2059.md:1136:+  || sed -i '' '/  \.claude\/\.framework-version/d' "$T1/$MANIFEST_REL" 2>/dev/null
.claude/plans/PLAN-166/archive/codex-r6-2059.md:1199:+manifest_has "$T3" '\.claude/\.framework-version(  |$)' \
.claude/plans/PLAN-166/archive/codex-r6-2059.md:1247:+manifest_has "$T4" '\.claude/\.framework-version(  |$)' \
.claude/plans/PLAN-166/archive/codex-r6-2059.md:1359:+      # framework version marker `.claude/.framework-version` is a TRACKED
.claude/plans/PLAN-166/archive/codex-r6-2059.md:1369:+      - name: Assert framework-version marker matches VERSION
.claude/plans/PLAN-166/archive/codex-r6-2059.md:1373:+          if [[ ! -f .claude/.framework-version ]]; then
.claude/plans/PLAN-166/archive/codex-r6-2059.md:1374:+            echo "::error::.claude/.framework-version is missing — it is a tracked file (PLAN-166 F3 / ADR-155-AMEND-1); a release checkout without it must not ship"
.claude/plans/PLAN-166/archive/codex-r6-2059.md:1377:+          MARKER="$(tr -d '[:space:]' < .claude/.framework-version)"
.claude/plans/PLAN-166/archive/codex-r6-2059.md:1379:+            echo "::error::.claude/.framework-version ('$MARKER') does not match VERSION ('$FILE') — the marker is byte-identical to VERSION by contract (Forma A (ii), fail-closed)"
.claude/plans/PLAN-166/archive/codex-r6-2059.md:1382:+          echo "OK: .claude/.framework-version=$MARKER matches VERSION"
.claude/plans/PLAN-166/archive/codex-r6-2059.md:1686:+      - ".claude/.framework-version"
.claude/plans/PLAN-166/archive/codex-r6-2059.md:1714:+      - ".claude/.framework-version"
.claude/plans/PLAN-166/archive/codex-r6-2059.md:1866:+      # .claude/.framework-version) across install -> upgrade -> doctor ->
.claude/plans/PLAN-166/archive/codex-r6-2059.md:1984:+    # SPEC/v1 and .claude/.framework-version are CONDITIONAL on the
.claude/plans/PLAN-166/archive/codex-r6-2059.md:2010:+    if _dr_delivered '\.claude/\.framework-version(  |$)'; then
.claude/plans/PLAN-166/archive/codex-r6-2059.md:2179:         ".claude/.framework-version. Asserted positively below: B/VERSION must "
.claude/plans/PLAN-166/archive/codex-r6-2059.md:2247:         "id": "F3-framework-version-marker",
.claude/plans/PLAN-166/archive/codex-r6-2059.md:2249:         "path": ".claude/.framework-version",
.claude/plans/PLAN-166/archive/codex-r6-2059.md:2252:             "root VERSION and into .claude/.framework-version, as a TRACKED "
.claude/plans/PLAN-166/archive/codex-r6-2059.md:3562:successes. Same doctrine as ``_release_bump_sites.py --today``: a parameter
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4156:    class as F2's ``--today`` in ``_release_bump_sites.py``: the input that
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4363:+      - ".claude/.framework-version"
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4391:+      - ".claude/.framework-version"
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4538:+      # .claude/.framework-version) across install -> upgrade -> doctor ->
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4568:/bin/zsh -lc "printf 'VERSION='; cat VERSION; printf 'marker='; cat .claude/.framework-version; printf '\\n--- framework marker base status ---\\n'; git ls-files .claude/.framework-version; printf '\\n--- framework update script full numbered ---\\n'; nl -ba .claude/scripts/check-framework-updates.sh | sed -n '1,260p'; printf '\\n--- framework checker tests refs ---\\n'; rg -n \"check-framework-updates|framework-version\" .claude/scripts/tests scripts/tests tests | head -240" in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4574:.claude/.framework-version
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4664:    88	# .claude/.framework-version instead — but the marker is only TRUSTED when
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4670:    94	#   2. <root>/.claude/.framework-version  when well-formed AND
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4686:   110	    if [ -f "$cur/.claude/.framework-version" ] || [ -f "$cur/VERSION" ]; then
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4693:   117	    echo "fatal: no .claude/.framework-version or VERSION found (looked from $(pwd))" >&2
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4696:   120	  MARKER="$VROOT/.claude/.framework-version"
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4701:   125	      MARKER_REC="$(grep -E '^([0-9a-f]{64}|LINK)  \.claude/\.framework-version(  |$)' "$MANIFEST" 2>/dev/null | head -1 || true)"
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4716:   140	          _rec_tgt="${MARKER_REC#LINK  .claude/.framework-version  }"
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4732:   156	        log "note: .claude/.framework-version does NOT match its delivery record (edited, redirected, or no digest tool available) — falling back to VERSION"
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4737:   161	          VSOURCE="marker (.claude/.framework-version, delivery-recorded)"
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4739:   163	          log "note: .claude/.framework-version malformed ('$MARKER_VAL') — falling back to VERSION"
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4749:   173	      log "note: .claude/.framework-version present but NOT delivery-recorded in .claude/.install-manifest.sha256 — falling back to VERSION (r20: a pre-existing adopter marker is not the framework's)"
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4839:scripts/tests/test-ownership-table.sh:100:    marker)   printf '.claude/.framework-version' ;;
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4840:scripts/tests/test-ownership-table.sh:257:  printf '1.3.1\n' > "$nxt/.claude/.framework-version"
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4841:scripts/tests/_parity_classify.py:149:        ".claude/.framework-version. Asserted positively below: B/VERSION must "
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4842:scripts/tests/_parity_classify.py:177:        "id": "F3-framework-version-marker",
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4843:scripts/tests/_parity_classify.py:179:        "path": ".claude/.framework-version",
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4844:scripts/tests/_parity_classify.py:182:            "root VERSION and into .claude/.framework-version, as a TRACKED "
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4846:scripts/tests/ownership_table.tsv:59:OWN-0064	marker	hash	regular	pristine	yes	copy	maintainer	upgrade	self	none	PRESERVE_OWNED	HASH_SOURCE	adr-155-amend-1	--skip .claude/.framework-version
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4847:scripts/tests/test-upgrade-spec-ownership.sh:5:# .claude/.framework-version) across install → upgrade → doctor → updater.
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4849:scripts/tests/test-upgrade-spec-ownership.sh:75:if [ ! -f "$SOURCE_DIR/.claude/.framework-version" ]; then
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4850:scripts/tests/test-upgrade-spec-ownership.sh:76:  echo "FATAL: source has no .claude/.framework-version (F3 marker missing)" >&2
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4851:scripts/tests/test-upgrade-spec-ownership.sh:123:MARKER_REL=".claude/.framework-version"
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4852:scripts/tests/test-upgrade-spec-ownership.sh:144:manifest_has "$T1" '\.claude/\.framework-version(  |$)'    && ok "baseline records marker"      || bad "baseline has NO marker record"
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4854:scripts/tests/test-upgrade-spec-ownership.sh:218:sed -i.bak '/  \.claude\/\.framework-version/d' "$T1/$MANIFEST_REL" 2>/dev/null \
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4855:scripts/tests/test-upgrade-spec-ownership.sh:219:  || sed -i '' '/  \.claude\/\.framework-version/d' "$T1/$MANIFEST_REL" 2>/dev/null
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4856:scripts/tests/test-upgrade-spec-ownership.sh:282:manifest_has "$T3" '\.claude/\.framework-version(  |$)' \
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4857:scripts/tests/test-upgrade-spec-ownership.sh:330:manifest_has "$T4" '\.claude/\.framework-version(  |$)' \
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4862:/bin/zsh -lc "rg -n \"framework-version|FMS_DELIVERED|_baseline_has_spec|delivered_spec|delivered_protocol|delivered_framework\" scripts/install.sh scripts/upgrade.sh scripts/_framework_manifest_set.sh | sed -n '1,300p'; printf '\\n--- nearby install ---\\n'; nl -ba scripts/install.sh | sed -n '1680,1940p'; printf '\\n--- nearby upgrade ---\\n'; rg -n \"_refresh_protocol_pointer|refresh.*SPEC|framework_marker|DELIVERED_SPEC|FMS_DELIVERED\" scripts/upgrade.sh" in /Users/joaocanhada/canhada-labs/ceo-orchestration
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4864:scripts/_framework_manifest_set.sh:36:#     PROTOCOL.md, SPEC/v1 and .claude/.framework-version are enumerated ONLY
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4867:scripts/_framework_manifest_set.sh:40:#         FMS_DELIVERED_MARKER     .claude/.framework-version marker
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4871:scripts/_framework_manifest_set.sh:141:      printf '%s\n' ".claude/.framework-version"
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4872:scripts/_framework_manifest_set.sh:301:    .claude/.framework-version) printf '%s' "${FMS_HASH_SOURCE_MARKER:-}" ;;
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4873:scripts/_framework_manifest_set.sh:308:    SPEC/v1|SPEC/v1/*|PROTOCOL.md|.claude/.framework-version) return 0 ;;
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4876:scripts/install.sh:1358:# .claude/.framework-version is a TRACKED file of the framework repo (one
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4877:scripts/install.sh:1370:  if [[ ! -f "$SOURCE_DIR/.claude/.framework-version" ]]; then
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4878:scripts/install.sh:1371:    echo "    SKIP: .claude/.framework-version absent in source (pre-v1.3.0 checkout)"
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4879:scripts/install.sh:1375:  echo "==> Installing framework version marker (.claude/.framework-version — $(tr -d '[:space:]' < "$SOURCE_DIR/.claude/.framework-version"))"
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4880:scripts/install.sh:1376:  _state_record_op "install_framework_marker" ".claude/.framework-version"
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4881:scripts/install.sh:1377:  install_one ".claude/.framework-version"
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4882:scripts/install.sh:1380:    _state_record_op "delivered_framework_marker" ".claude/.framework-version"
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4884:scripts/install.sh:2385:     && grep -Eq '^([0-9a-f]{64}|LINK)  \.claude/\.framework-version(  |$)' "$manifest" 2>/dev/null \
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4885:scripts/install.sh:2386:     && _prior_link_target_matches "$manifest" ".claude/.framework-version"; then
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4886:scripts/install.sh:2390:.claude/.framework-version"
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4887:scripts/install.sh:2391:    echo "    ownership continuity: .framework-version delivery record preserved from prior manifest"
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4888:scripts/install.sh:2411:      *".claude/.framework-version"*) export FMS_HASH_SOURCE_MARKER="HASH_SOURCE" ;;
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4889:scripts/install.sh:2438:      *".claude/.framework-version"*) export FMS_HASH_SOURCE_MARKER="HASH_SOURCE" ;;
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4894:scripts/upgrade.sh:344:  and the .claude/.framework-version marker) in an existing adopter
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4895:scripts/upgrade.sh:348:  .claude/.framework-version for the installed framework version). NOTE: .claude/settings.json IS
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4897:scripts/upgrade.sh:1660:# .claude/.framework-version) derives from the REGISTERED DELIVERY — here,

exec
/bin/zsh -lc "for f in .github/workflows/*.yml; do if grep -qE '"'^'"\\s+tags:' \""'$f"; then echo "$f"; grep -nE '"'"'^on:|''^  (push|pull_request|workflow_dispatch|schedule):|tags:'"' \""'$f" | head -20; fi; done' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
.github/workflows/npm-publish.yml
43:# gate. `release.yml` and this workflow both fire on `push: tags: v*` as
82:on:
83:  push:
84:    tags:
.github/workflows/release.yml
3:on:
4:  push:
5:    tags:

exec
/bin/zsh -lc "python3 - <<'PY'
from pathlib import Path
import yaml
for p in Path('.github/workflows').glob('*.yml'):
 d=yaml.safe_load(p.read_text()) or {}
 on=d.get('on') if 'on' in d else d.get(True)
 if isinstance(on,dict) and 'push' in on:
  push=on['push']
  if push is None or push=={} or (isinstance(push,dict) and not any(k in push for k in ('branches','branches-ignore','tags','tags-ignore'))):
   print(p, push)
PY" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 229ms:
.github/workflows/formal-verify.yml {'paths': ['docs/formal-verification/**']}

exec
/bin/zsh -lc 'git diff --check && git status --short' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
 A .claude/.framework-version
 A .claude/adr/ADR-155-AMEND-1-delivery-record-ownership.md
 A .claude/governance/npm-trusted-publisher.txt
 M .claude/governance/pair-rail-verdict-template.md
 M .claude/plans/PLAN-166/W1-approved-draft.md
 A .claude/plans/PLAN-166/architect/round-1/approved.md
 M .claude/plans/PLAN-166/staged-manifest.sha256
 M .claude/scripts/check-framework-updates.sh
 M .claude/scripts/tests/test_release_workflow_asserts.py
 M .github/workflows/npm-publish.yml
 M .github/workflows/release.yml
 M .github/workflows/smoke-install.yml
 M INSTALL.md
 M README.md
 M README.pt-BR.md
 M RELEASE.md
 M docs/ARCHITECTURE.md
 M docs/CTO-GUIDE.md
 M docs/FAQ.md
 M docs/GUIA-COMPLETO.md
 M docs/README.md
 M npm/README.md
 M scripts/doctor.sh
 M scripts/tests/_parity_classify.py
 A scripts/tests/test-upgrade-spec-ownership.sh
?? .claude/plans/PLAN-166/OWNER-W1-LAND-step1.sh
?? .claude/plans/PLAN-166/OWNER-W1-LAND-step1b.sh
?? .claude/plans/PLAN-166/W1-ceremony-log.md
?? .claude/plans/PLAN-166/architect/round-1/approved.md.asc
?? .claude/plans/PLAN-166/archive/
?? .claude/plans/PLAN-167/OWNER-PREPARE-TO-SIGN.sh
?? .claude/plans/PLAN-167/W4-approved.md
?? .claude/plans/PLAN-167/W4-approved.md.asc
?? .claude/plans/PLAN-168/archive/

exec
/bin/zsh -lc "cat .claude/plans/PLAN-166/archive/codex-review-w1-round11.md 2>/dev/null || true; printf '\\n--- latest W1 ceremony review ---\\n'; cat .claude/plans/PLAN-166/archive/codex-review-w1-ceremony.md 2>/dev/null || true" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
The new ownership-continuity logic can both legitimize foreign symlinks and silently discard prior SPEC ownership. Version reporting is also incorrect for pinned downgrades and for preserved pre-existing marker files.

Full review comments:

- [P2] Reject hash-to-link transitions during continuity — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/install.sh:2326-2328
  On a `--link` rerun after a copy-installed SPEC or marker has been replaced by a symlink, the prior manifest contains only HASH rows, so this early success bypasses target validation. The continuity branch then marks the destination delivered and records the arbitrary live symlink as a trusted LINK entry. Require the live type to agree with the prior record rather than treating the absence of a LINK row as a match.

- [P2] Preserve records when continuity finds missing SPEC files — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/install.sh:2330-2337
  When a previously delivered `SPEC/v1` still exists but has become empty, `install_one` skips it and this branch claims continuity, yet the manifest rewrite emits no SPEC file records from the empty target. The next upgrade therefore classifies the tree as an unowned adopter fork and will not restore the compliance contract. Carry forward validated prior rows or re-deliver missing files instead of setting only the delivery flag.

- [P2] Keep downgrade version reporting tied to the pinned source — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1987-1992
  For an external target downgraded with `--pin` to a pre-marker release, dropping the marker record does not make the target's root `VERSION` reflect the pinned source: this upgrader deliberately never modifies that adopter-owned file. Readers therefore fall back to the original install version and can report the target as newer than its actual framework content. Derive a version signal from the pinned source rather than relying on the unchanged target `VERSION`.

- [P2] Gate forensic marker guidance on its delivery record — /Users/joaocanhada/canhada-labs/ceo-orchestration/INSTALL.md:592-595
  If `.claude/.framework-version` existed before installation, the installer intentionally preserves it without adding a delivery record, but this command still reports its arbitrary value as the framework version. The checker and upgrader trust the marker only when its manifest record is valid, so the documented forensic procedure should use that checker or first verify the delivery record.

--- latest W1 ceremony review ---
The delivery-record implementation loses ownership information on installer reruns and mishandles link-mode baseline rewrites. Its legacy SPEC fingerprint can also misclassify customized trees and force-refresh them.

Full review comments:

- [P1] Preserve earlier delivery records on installer reruns — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/install.sh:2301-2303
  When `install.sh` is rerun on an already-installed target, `install_one` returns EXISTS for these paths, leaving all three flags zero, and this rewrite replaces the existing manifest without consulting its prior delivery records. The rerun therefore drops ownership of SPEC, PROTOCOL, and the marker; a user install then has no trusted version source, and a v1.3 SPEC will be preserved indefinitely as an ADOPTER-FORK because it is absent from the legacy fingerprints. Preserve valid pre-run delivery records rather than treating every EXISTS result as adopter-owned.

- [P2] Retain LINK records during baseline rewrites — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1817-1819
  For a target installed with `--mode link`, the new refresh branches preserve the symlinks and mark them delivered, but the later manifest rewrite still uses `FMS_MODE=copy`. Consequently the `SPEC/v1` directory symlink is omitted from the rewritten manifest, while the marker symlink becomes a hash record that `doctor.sh` reports as a type-change drift. Preserve LINK serialization or recover the original install mode when rewriting the baseline.

- [P2] Reject non-regular entries from pristine SPEC matching — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1657-1658
  On a legacy tree whose regular files match a pristine release but which also contains an adopter-added symlink, `find -type f` omits that entry, so the fingerprint still matches and the forced refresh replaces the tree instead of preserving it as an ADOPTER-FORK. Traversal errors can similarly produce a partial fingerprint because the pipeline status is not checked. Include the complete entry inventory or reject non-regular/partially traversed trees.
exec
/bin/zsh -lc "grep -n \"ADOPTER-FORK\\|adopter fork\\|fork\" scripts/upgrade.sh | head -80; nl -ba scripts/tests/test-upgrade-spec-ownership.sh | sed -n '240,272p'; nl -ba .github/workflows/smoke-install.yml | sed -n '212,228p'" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
1617:        # pointer is CONTENT, not a fork — it is preserved, and the record keeps
1722:  # fingerprint (rc 1) => the caller's safe path (ADOPTER-FORK preserve).
1869:#     no match => ADOPTER-FORK: preserve + snapshot + named WARNING.
1928:      # recovery guidance is the true ADOPTER-FORK: content the framework
1932:          echo "    (dry-run) would PRESERVE (SPEC/v1 ADOPTER-FORK): SPEC/v1"
1948:          # would destroy the only copy of the fork.
1952:        _up_record_op "preserve_spec_v1_adopter_fork" "SPEC/v1"
   240	DOC_RC=$?
   241	grep -q 'ORPHAN?: SPEC/v1/zz-orphan-probe.md' "$DOC_OUT" && [ "$DOC_RC" -ne 0 ] \
   242	  && ok "delivered SPEC is enumerated: stray file flagged, rc=$DOC_RC" \
   243	  || bad "stray file in delivered SPEC NOT flagged (rc=$DOC_RC) — FMS_DELIVERED_SPEC resolution dead"
   244	rm -f "$T1/SPEC/v1/zz-orphan-probe.md"
   245	
   246	# --------------------------------------------------------------------------
   247	# S4 — legacy ADOPTER-FORK (fresh fixture; simulate the v1.2-and-earlier
   248	# baseline shape by stripping SPEC records, then fork the SPEC).
   249	# --------------------------------------------------------------------------
   250	echo "==> S4: legacy baseline (no SPEC records) + edited SPEC => preserve + WARNING"
   251	T2="$( fresh_install m2 --profile core )" || exit 1
   252	sed -i.bak '/  SPEC\/v1\//d' "$T2/$MANIFEST_REL" 2>/dev/null \
   253	  || sed -i '' '/  SPEC\/v1\//d' "$T2/$MANIFEST_REL" 2>/dev/null
   254	rm -f "$T2/$MANIFEST_REL.bak"
   255	SPEC2="$( ls "$T2"/SPEC/v1/*.md 2>/dev/null | head -1 )"
   256	printf '\nADOPTER-FORK sentinel S4\n' >> "$SPEC2"
   257	
   258	if run_upgrade "$T2"; then ok "upgrade rc=0 (fork is preserved, never fatal)"; else bad "upgrade failed on adopter-fork fixture"; fi
   259	grep -q 'ADOPTER-FORK' "$T2.upgrade.log" \
   260	  && ok "named ADOPTER-FORK warning emitted" \
   261	  || bad "no ADOPTER-FORK warning in upgrade log"
   262	grep -q 'ADOPTER-FORK sentinel S4' "$SPEC2" 2>/dev/null \
   263	  && ok "forked SPEC preserved in place" \
   264	  || bad "forked SPEC was clobbered despite missing delivery record"
   265	manifest_has "$T2" 'SPEC/v1/' \
   266	  && bad "rewritten baseline claims the adopter-fork SPEC as framework-owned" \
   267	  || ok "rewritten baseline does NOT claim the adopter-fork SPEC"
   268	SNAP_HIT="$( ls -d "$T2"/.claude.bak/*/SPEC/v1 2>/dev/null | head -1 )"
   269	[ -n "$SNAP_HIT" ] \
   270	  && ok "forensic snapshot of the fork present under .claude.bak" \
   271	  || bad "no forensic snapshot of the preserved fork"
   272	
   212	
   213	      # PLAN-166 F3 (ADR-155-AMEND-1, AC-3) — delivery-record ownership of
   214	      # the three conditional framework surfaces (SPEC/v1, root PROTOCOL.md,
   215	      # .claude/.framework-version) across install -> upgrade -> doctor ->
   216	      # updater. Scenarios S1-S8 incl. the forced-refresh route (S2), the
   217	      # legacy ADOPTER-FORK preserve (S4) and the marker-first updater
   218	      # regression (S6). Same wiring rationale as the parity e2e above:
   219	      # scripts/tests/*.sh runs ONLY here — unwired = no test. NO
   220	      # continue-on-error, deliberately.
   221	      - name: Upgrade SPEC/marker delivery-record ownership (S1-S8)
   222	        run: |
   223	          set -euo pipefail
   224	          bash scripts/tests/test-upgrade-spec-ownership.sh
   225	
   226	      - name: Assert npx/npm shim contract (if present)
   227	        # Phase 4 deliverable; skip if directory missing
   228	        run: |

exec
/bin/zsh -lc "nl -ba scripts/upgrade.sh | sed -n '1900,1962p'" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
  1900	    # The decision function refuses combinations its legality rules forbid.
  1901	    # Fail toward preserve — under-claiming is recoverable, over-claiming is
  1902	    # the delete-the-adopter's-file class (ADR-155-AMEND-1 §3).
  1903	    echo "    WARNING: SPEC/v1 dimensions are not a legal cell" >&2
  1904	    echo "             ($_pr/$_lt/$_lc/$_sh/$_md/$CEREMONY_EFFECTIVE/$_sk) —" >&2
  1905	    echo "             PRESERVED without ownership. Please report this combination." >&2
  1906	    return 0
  1907	  fi
  1908	  _verdict="${_pair%% *}"; _hash="${_pair##* }"
  1909	  _SPEC_HASH_SOURCE="$_hash"   # consumed by the baseline rewrite
  1910	
  1911	  # ---- EXECUTE -------------------------------------------------------------
  1912	  case "$_verdict" in
  1913	    PRESERVE_OWNED)
  1914	      _SPEC_DELIVERED=1
  1915	      case "$_lt/$_sk/$_sh" in
  1916	        ancestor_symlink/*/*) echo "    SKIP: SPEC/v1 has a symlinked ancestor (refusing to write through it — F11a)" ;;
  1917	        symlink/*/*)          echo "    SKIP: SPEC/v1 is the recorded --mode link delivery (target unchanged)" ;;
  1918	        */self/*)             echo "    SKIPPED (--skip): SPEC/v1" ;;
  1919	        */descendant/*)       echo "    SKIPPED (--skip matches a descendant): SPEC/v1 refreshes as ONE contract unit — preserving the whole tree" ;;
  1920	        */*/no)               echo "    SKIP: SPEC/v1 absent in source (ownership carried forward)" ;;
  1921	        *)                    echo "    SKIP: SPEC/v1 (recorded --ceremony user install — root surfaces are out of scope, WS4)" ;;
  1922	      esac
  1923	      return 0
  1924	      ;;
  1925	
  1926	    PRESERVE_UNOWNED|OMIT_RECORD)
  1927	      # An adopter-owned surface. The ONLY case that earns a snapshot plus
  1928	      # recovery guidance is the true ADOPTER-FORK: content the framework
  1929	      # cannot claim, with no gate having refused first.
  1930	      if [ "$_lt" = "dir" ] || [ "$_lt" = "dir_empty" ]; then
  1931	        if [ "$DRY_RUN" -eq 1 ]; then
  1932	          echo "    (dry-run) would PRESERVE (SPEC/v1 ADOPTER-FORK): SPEC/v1"
  1933	          return 0
  1934	        fi
  1935	        local _snap_ok=0
  1936	        if mkdir -p "$( dirname "$bdir" )" 2>/dev/null && cp -R "$ddir" "$bdir" 2>/dev/null; then
  1937	          _snap_ok=1
  1938	        fi
  1939	        echo "    WARNING: SPEC/v1 is not framework-owned (no delivery record, and it" >&2
  1940	        echo "             matches neither this checkout nor any pristine shipped SPEC)" >&2
  1941	        if [ "$_snap_ok" -eq 1 ]; then
  1942	          echo "             — PRESERVED in place (snapshot in $BAK_DIR/SPEC/v1)." >&2
  1943	          echo "             To hand it back to the framework: remove the target SPEC/v1," >&2
  1944	          echo "             copy this checkout's tree in, and re-run — a byte-identical" >&2
  1945	          echo "             tree is taken over and recorded." >&2
  1946	        else
  1947	          # Recovery guidance is WITHHELD without a snapshot: following it
  1948	          # would destroy the only copy of the fork.
  1949	          echo "             — PRESERVED in place, but the forensic snapshot COULD NOT be" >&2
  1950	          echo "             created. Back SPEC/v1 up yourself before any manual takeover." >&2
  1951	        fi
  1952	        _up_record_op "preserve_spec_v1_adopter_fork" "SPEC/v1"
  1953	      else
  1954	        echo "    SKIP: SPEC/v1 is $_lt — adopter-owned, preserved without ownership" >&2
  1955	      fi
  1956	      return 0
  1957	      ;;
  1958	
  1959	    DELIVER|REFRESH)
  1960	      if [ "$DRY_RUN" -eq 1 ]; then
  1961	        if [ "$_verdict" = "REFRESH" ]; then
  1962	          echo "    (dry-run) would FORCE-REFRESH (backup to $BAK_DIR/SPEC/v1): SPEC/v1"

exec
/bin/zsh -lc "nl -ba .github/workflows/smoke-install.yml | sed -n '1,72p'; nl -ba INSTALL.md | sed -n '584,632p'; nl -ba .github/workflows/release.yml | sed -n '66,105p'; nl -ba .claude/adr/ADR-155-AMEND-1-delivery-record-ownership.md | sed -n '175,215p'" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
     1	name: Smoke Install
     2	
     3	on:
     4	  pull_request:
     5	    paths:
     6	      - "scripts/install.sh"
     7	      - "scripts/upgrade.sh"
     8	      # PLAN-161 (CI wiring): upgrade oracles + the manifest lib they
     9	      # exercise — keep BOTH filter lists (pull_request + push) in sync.
    10	      - "scripts/_framework_manifest_set.sh"
    11	      # The ownership + parity e2e call _hash_file/_hash_stdin from here, and
    12	      # this workflow is their ONLY CI execution — without the helper in the
    13	      # filter, a PR touching only it skips the gate entirely (codex W1
    14	      # round 10, P2: the "red gate nobody runs" class, one level deeper).
    15	      - "scripts/_hash_lib.sh"
    16	      - "scripts/tests/test-upgrade-dryrun-identity.sh"
    17	      - "scripts/tests/test-upgrade-exclusions.sh"
    18	      - "scripts/tests/smoke-install.sh"
    19	      # PLAN-166 F4 (OQ-4): the install/upgrade parity e2e and its classifier.
    20	      # The finding this closes is "a red gate nobody runs" (5th instance) --
    21	      # an unwired test is the same as no test.
    22	      - "scripts/tests/test-install-upgrade-parity-e2e.sh"
    23	      - "scripts/tests/_parity_classify.py"
    24	      # PLAN-166 F3 (ADR-155-AMEND-1): delivery-record ownership e2e —
    25	      # scripts/tests/*.sh runs ONLY in this workflow (same r11/r20 wiring
    26	      # rule as the parity e2e above).
    27	      - "scripts/tests/test-upgrade-spec-ownership.sh"
    28	      - "templates/**"
    29	      # Widened from SPEC/v1/install-cli.md: SPEC/v1 is delivered by install.sh
    30	      # and (until F3) by nothing in upgrade.sh, so ANY SPEC/v1 change is a
    31	      # parity event, not just the CLI contract doc.
    32	      - "SPEC/v1/**"
    33	      # PLAN-166 F4 wiring (r11/r20): scripts/tests/*.sh runs ONLY here, so a
    34	      # PR touching just one of these would otherwise skip the regression.
    35	      - "scripts/doctor.sh"
    36	      - ".claude/.framework-version"
    37	      - ".claude/scripts/check-framework-updates.sh"
    38	      - ".github/workflows/smoke-install.yml"
    39	      # PLAN-006 Phase 1 (Sprint 6): Adapter Layer migration changes
    40	      # install-time expectations (hook import paths, contract). Scope
    41	      # broadened for the sprint; narrow back post-Sprint-7 closeout.
    42	      - ".claude/hooks/**"
    43	  push:
    44	    branches:
    45	      - main
    46	    paths:
    47	      # KEEP IDENTICAL to the pull_request list above. The two had already
    48	      # drifted (push was missing SPEC/v1 and this workflow file); PLAN-166 F4
    49	      # re-syncs them, because a filter that fires on the PR and not on the
    50	      # merge is a gate with a hole in it.
    51	      - "scripts/install.sh"
    52	      - "scripts/upgrade.sh"
    53	      - "scripts/_framework_manifest_set.sh"
    54	      - "scripts/_hash_lib.sh"
    55	      - "scripts/tests/test-upgrade-dryrun-identity.sh"
    56	      - "scripts/tests/test-upgrade-exclusions.sh"
    57	      - "scripts/tests/smoke-install.sh"
    58	      - "scripts/tests/test-install-upgrade-parity-e2e.sh"
    59	      - "scripts/tests/_parity_classify.py"
    60	      - "scripts/tests/test-upgrade-spec-ownership.sh"
    61	      - "templates/**"
    62	      - "SPEC/v1/**"
    63	      - "scripts/doctor.sh"
    64	      - ".claude/.framework-version"
    65	      - ".claude/scripts/check-framework-updates.sh"
    66	      - ".github/workflows/smoke-install.yml"
    67	      - ".claude/hooks/**"
    68	
    69	concurrency:
    70	  group: smoke-install-${{ github.ref }}
    71	  cancel-in-progress: true
    72	
   584	customize behavior do so via `settings.json` env-var overrides
   585	(documented in `docs/GOVERNANCE.md`), never by editing the schema
   586	files. A version bump in `VERSION` carries the SemVer guarantee
   587	that minor/patch changes do NOT break the schemas; major bumps
   588	publish a new `SPEC/v2/` alongside.
   589	
   590	To verify what framework version a target is running:
   591	
   592	```bash
   593	cat TARGET/.claude/.framework-version   # preferred — refreshed on every upgrade
   594	# Example output: 1.3.0
   595	cat TARGET/VERSION                      # fallback (pre-v1.3.0 installs)
   596	```
   597	
   598	Prefer `.claude/.framework-version` as the forensic anchor when an
   599	adopter reports a bug. The root `VERSION` file matches the git tag of
   600	the source framework checkout **at install time only**: `upgrade.sh`
   601	deliberately never touches it (an adopter repo may have its own
   602	`VERSION`, and taking it over is the S238/ADR-155 clobber class — see
   603	`ADR-155-AMEND-1`), so on an upgraded install `VERSION` reports the
   604	ORIGINAL install version, not the current one. The marker is refreshed
   605	on every upgrade and is cross-checked against `VERSION` in every
   606	framework release; fall back to `VERSION` only on pre-v1.3.0 installs
   607	that have not upgraded yet.
   608	
   609	---
   610	
   611	## Upgrade flow
   612	
   613	To refresh framework-derived content in an existing adopter install
   614	(without touching user-customized files), use `scripts/upgrade.sh`:
   615	
   616	```bash
   617	cd /path/to/ceo-orchestration   # source framework checkout
   618	git pull                         # get the latest framework
   619	bash scripts/upgrade.sh /path/to/your/project --pin v1.3.0
   620	```
   621	
   622	What gets refreshed:
   623	
   624	- `.claude/team.md`, `.claude/frontend-team.md`
   625	- `.claude/skills/`, `.claude/hooks/`, `.claude/scripts/`,
   626	  `.claude/commands/`
   627	- `.claude/pitfalls-catalog.yaml`, `.claude/task-chains.yaml`
   628	- `PROTOCOL.md` pointer (skipped on `--ceremony user` installs — a user
   629	  install never creates root files)
   630	- `SPEC/v1/` — **forced route** (skipped on `--ceremony user` installs):
   631	  the SPEC is the published compliance contract, so a local edit is a
   632	  *fork of the contract*, not a customization — a framework-owned
    66	          if [[ "$EXPECTED" != "$BASE" ]]; then
    67	            echo "OK: VERSION=$FILE matches RC tag=$TAG (compared against base '$BASE' after stripping the -rc.N pre-release suffix)"
    68	          else
    69	            echo "OK: VERSION=$FILE matches tag=$TAG"
    70	          fi
    71	
    72	      # -----------------------------------------------------------------
    73	      # PLAN-166 W1 item 2 (F3, ADR-155-AMEND-1 §5, Forma A (ii)) — the
    74	      # framework version marker `.claude/.framework-version` is a TRACKED
    75	      # one-line file, byte-identical to VERSION (the version bump writes
    76	      # it as a site; verify-counts.sh cross-checks it). This assert is
    77	      # deliberately UNCONDITIONAL and fail-closed: a missing marker in a
    78	      # release checkout means the ceremony that introduced it was
    79	      # reverted or the bump skipped a site — either way the tag must not
    80	      # ship. Kept NEXT TO the VERSION↔tag assert above so the whole
    81	      # version-consistency family lives in one place (same convention as
    82	      # the plugin-manifest step below).
    83	      # -----------------------------------------------------------------
    84	      - name: Assert framework-version marker matches VERSION
    85	        run: |
    86	          set -euo pipefail
    87	          FILE="$(tr -d '[:space:]' < VERSION)"
    88	          if [[ ! -f .claude/.framework-version ]]; then
    89	            echo "::error::.claude/.framework-version is missing — it is a tracked file (PLAN-166 F3 / ADR-155-AMEND-1); a release checkout without it must not ship"
    90	            exit 1
    91	          fi
    92	          MARKER="$(tr -d '[:space:]' < .claude/.framework-version)"
    93	          if [[ "$MARKER" != "$FILE" ]]; then
    94	            echo "::error::.claude/.framework-version ('$MARKER') does not match VERSION ('$FILE') — the marker is byte-identical to VERSION by contract (Forma A (ii), fail-closed)"
    95	            exit 1
    96	          fi
    97	          echo "OK: .claude/.framework-version=$MARKER matches VERSION"
    98	
    99	      # -----------------------------------------------------------------
   100	      # PLAN-153 Wave B item 5 (e) — version↔plugin-manifest sync, kept
   101	      # NEXT TO the VERSION↔tag assert above so the whole
   102	      # version-consistency family lives in one place.
   103	      #
   104	      # `.claude-plugin/{plugin.json,marketplace.json}` are generated by
   105	      # `build-plugin.py` (Wave B item 6). Until item 6 lands, the
   175	never produces a fingerprint (fail toward preserve). Both legacy cases
   176	are fixtures; the pristine-match branch is additionally exercised
   177	end-to-end by the F4 install-v1.2.0→upgrade comparison job.
   178	
   179	## §5 The marker: forced+validated write, record-gated readers
   180	
   181	`.claude/.framework-version` is a **tracked file of the framework repo**
   182	(one line, byte-identical to `VERSION`) — not generated-only-at-destination,
   183	so the release protections are real and unconditional: the version bump
   184	writes it as its 12th site, `verify-counts.sh` cross-checks it against
   185	`VERSION` in every release, and `release.yml` asserts marker == VERSION
   186	fail-closed. In the enumeration it is a NORMAL file entry (the
   187	`FMS_HASH_ROOT` baseline rewrite preserves it with no special-case),
   188	conditional on delivery like the other two.
   189	
   190	Delivery is by **explicit writes on both paths** (the enumeration never
   191	delivers — it only records; r7): `install_one ".claude/.framework-version"`
   192	on install (skip-if-exists ⇒ a pre-existing adopter marker is NOT
   193	delivered), and a **forced + read-back-validated** rewrite on upgrade
   194	(differing pre-existing copy backed up first; a write that fails
   195	validation is NOT recorded as delivered). It lives inside `.claude/`, so
   196	both ceremonies receive it (the WS4 guard only forbids root files) and it
   197	is committable like the rest of `.claude/`.
   198	
   199	**Every marker-first reader consults the SAME record** (r20):
   200	`check-framework-updates.sh` trusts the marker only when the baseline
   201	manifest carries its delivery record, else falls back to `VERSION` — on a
   202	target where the marker pre-existed and was skipped, an unconditional
   203	read would report a stale version in a loop.
   204	
   205	## §6 Enforcement
   206	
   207	- `scripts/tests/test-upgrade-spec-ownership.sh` — record-owned forced
   208	  refresh with backup (the 2nd-upgrade scenario), user-ceremony +
   209	  `--no-replay` skip, legacy adopter-fork preserve, marker delivery +
   210	  pre-existing-marker fallback, doctor orphan-scan in both modes,
   211	  update-checker no-loop regression (AC-3).
   212	- The PLAN-166 F4 e2e (`smoke-install.yml`) compares install-built vs
   213	  upgrade-built trees per ceremony mode; its historical leg
   214	  (install v1.2.0 → upgrade) exercises the pristine-match migration.
   215	- `_framework_manifest_set.sh`, `install.sh`, `upgrade.sh` remain

exec
/bin/zsh -lc 'python3 .claude/scripts/local/_release_bump_sites.py paths --include-generated 2>&1 || python3 .claude/scripts/local/_release_bump_sites.py --help' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
usage: _release_bump_sites.py [-h] {print-sites,bump} ...
_release_bump_sites.py: error: argument cmd: invalid choice: 'paths' (choose from 'print-sites', 'bump')
usage: _release_bump_sites.py [-h] {print-sites,bump} ...

Release version-site table + writer (single source).

positional arguments:
  {print-sites,bump}
    print-sites       print every path the bump may write, one per line
    bump              rewrite the version sites

optional arguments:
  -h, --help          show this help message and exit

exec
/bin/zsh -lc "python3 .claude/scripts/local/_release_bump_sites.py print-sites --help; printf '\\n--- sites ---\\n'; python3 .claude/scripts/local/_release_bump_sites.py print-sites" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
usage: _release_bump_sites.py print-sites [-h] [--include-generated]

optional arguments:
  -h, --help           show this help message and exit
  --include-generated  also print the plugin manifests regenerated by build-
                       plugin.py

--- sites ---
VERSION
npm/package.json
pyproject.toml
INSTALL.md
docs/ARCHITECTURE.md
SBOM.md
SECURITY.md
VERSIONING.md
npm/README.md

exec
/bin/zsh -lc "nl -ba scripts/upgrade.sh | sed -n '2010,2150p'" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
  2010	      mkdir -p "$( dirname "$ddir" )"
  2011	      cp -R "$sdir" "$ddir"
  2012	      _SPEC_DELIVERED=1
  2013	      echo "    REFRESHED (forced — $_pr/$_lc): SPEC/v1"
  2014	      return 0
  2015	      ;;
  2016	  esac
  2017	}
  2018	
  2019	# _refresh_framework_marker — FORCED + VALIDATED write (r20 option (a)):
  2020	# the marker is generated-refresh content — the upgrade rewrites it to the
  2021	# source VERSION every run, backs up a differing pre-existing copy, and
  2022	# read-back-validates the write. A marker the upgrade could not validate is
  2023	# NOT recorded as delivered, so the FMS entry (and every marker-first
  2024	# reader keyed off the SAME record) falls back to VERSION instead of
  2025	# trusting a stale value. Delivered in BOTH ceremonies (inside .claude/).
  2026	_MARKER_DELIVERED=0
  2027	_refresh_framework_marker() {
  2028	  local src="$SOURCE_DIR/.claude/.framework-version"
  2029	  local dst="$TARGET/.claude/.framework-version"
  2030	  local bak="$BAK_DIR/.claude/.framework-version"
  2031	
  2032	  # ---- OBSERVE -------------------------------------------------------------
  2033	  local _lt _pr _lc _sh _md _sk
  2034	  if _lg_ancestor_is_symlink "$TARGET" ".claude/.framework-version"; then
  2035	    _lt="ancestor_symlink"
  2036	  else
  2037	    _lt="$( _ov_obs_live_type "$dst" )"
  2038	  fi
  2039	  _pr="$( _ov_obs_prior_record ".claude/.framework-version" )"
  2040	  _sh=no; [ -f "$src" ] && _sh=yes
  2041	  # Inspect CONTENT only for a regular file. `cmp` on a FIFO blocks waiting for
  2042	  # a writer, hanging the upgrade before the verdict can say PRESERVE_UNOWNED —
  2043	  # the third instance of "a reader opens what lstat already classified"
  2044	  # (codex W3 r4 P1; the OWN-0029 timeout).
  2045	  if [ "$_lt" != "regular" ]; then
  2046	    _lc="-"
  2047	  elif [ "$_sh" = yes ] && cmp -s "$src" "$dst" 2>/dev/null; then
  2048	    _lc="pristine"
  2049	  else
  2050	    _lc="edited"
  2051	  fi
  2052	  _md="$( _ov_obs_mode )"
  2053	  _sk="$( _ov_obs_skip ".claude/.framework-version" )"
  2054	
  2055	  # ---- DECIDE --------------------------------------------------------------
  2056	  local _pair _verdict
  2057	  if ! _pair="$( _ownership_verdict marker "$_pr" "$_lt" "$_lc" "$_sh" "$_md" \
  2058	                   "$CEREMONY_EFFECTIVE" upgrade "$_sk" )"; then
  2059	    echo "    WARNING: .claude/.framework-version dimensions are not a legal cell" >&2
  2060	    echo "             — PRESERVED without ownership. Please report this combination." >&2
  2061	    return 0
  2062	  fi
  2063	  _verdict="${_pair%% *}"
  2064	  _MARKER_HASH_SOURCE="${_pair##* }"
  2065	
  2066	  # ---- EXECUTE -------------------------------------------------------------
  2067	  case "$_verdict" in
  2068	    PRESERVE_OWNED)
  2069	      _MARKER_DELIVERED=1
  2070	      case "$_lt/$_sk" in
  2071	        ancestor_symlink/*) echo "    SKIP: .claude/.framework-version has a symlinked ancestor (refusing to write through it — F11a)" ;;
  2072	        symlink/*)          echo "    SKIP: .claude/.framework-version is the recorded --mode link delivery (target unchanged)" ;;
  2073	        */self)             echo "    SKIPPED (--skip): .claude/.framework-version" ;;
  2074	        *)                  echo "    SKIP: .claude/.framework-version (ownership carried forward)" ;;
  2075	      esac
  2076	      return 0
  2077	      ;;
  2078	
  2079	    OMIT_RECORD|PRESERVE_UNOWNED)
  2080	      if [ "$_sh" = no ]; then
  2081	        # The documented --pin downgrade: this source predates the marker, so a
  2082	        # retained record would keep advertising a newer version over older
  2083	        # content. Readers fall back to VERSION, which the pin DID update.
  2084	        echo "    SKIP: .claude/.framework-version absent in source (pre-v1.3.0 checkout)"
  2085	        if [ "$_pr" != "none" ]; then
  2086	          echo "    NOTE: the prior delivery record is NOT carried forward — version" >&2
  2087	          echo "          readers fall back to VERSION (which reflects the pinned source)" >&2
  2088	        fi
  2089	      elif [ "$_lt" = "symlink" ]; then
  2090	        echo "    WARNING: .claude/.framework-version is a symlink that does NOT match the" >&2
  2091	        echo "             recorded LINK delivery — preserved WITHOUT framework ownership" >&2
  2092	        echo "             (readers fall back to VERSION)" >&2
  2093	      else
  2094	        echo "    SKIP: .claude/.framework-version is $_lt — adopter-owned, refusing to write into/through it"
  2095	      fi
  2096	      return 0
  2097	      ;;
  2098	
  2099	    DELIVER|REFRESH)
  2100	      if [ "$DRY_RUN" -eq 1 ]; then
  2101	        echo "    (dry-run) would REFRESH: .claude/.framework-version ($(tr -d '[:space:]' < "$src" 2>/dev/null || true))"
  2102	        return 0
  2103	      fi
  2104	      if [ "$_verdict" = "REFRESH" ] && [ "$_lc" = "edited" ]; then
  2105	        mkdir -p "$( dirname "$bak" )" 2>/dev/null || true
  2106	        if { cp "$dst" "$bak" 2>/dev/null || false; }; then
  2107	          echo "    BACKED UP: .claude/.framework-version -> $bak"
  2108	        else
  2109	          # INV-3: an execution failure never advances the record.
  2110	          echo "    WARNING: could not back up differing .claude/.framework-version —" >&2
  2111	          echo "             REFUSING to overwrite it (backup-before-replace)" >&2
  2112	          # INV-3, same as the SPEC branch above.
  2113	          _up_record_op "preserve_marker_backup_failed" ".claude/.framework-version"
  2114	          if [ "$_pr" = "hash" ]; then
  2115	            _MARKER_DELIVERED=1
  2116	            _MARKER_HASH_SOURCE="HASH_PRIOR_RECORD"
  2117	          fi
  2118	          return 0
  2119	        fi
  2120	      fi
  2121	      mkdir -p "$( dirname "$dst" )"
  2122	      cp "$src" "$dst"
  2123	      # Read-back validation: a write that cannot be confirmed is NOT recorded
  2124	      # as delivered, so every marker-first reader falls back to VERSION rather
  2125	      # than trusting a value the upgrade could not verify.
  2126	      if cmp -s "$src" "$dst" 2>/dev/null; then
  2127	        _MARKER_DELIVERED=1
  2128	        _up_record_op "refresh_framework_marker" "$(tr -d '[:space:]' < "$src" 2>/dev/null || true)"
  2129	        echo "    REFRESHED: .claude/.framework-version ($(tr -d '[:space:]' < "$dst" 2>/dev/null || true))"
  2130	      else
  2131	        echo "    WARNING: .claude/.framework-version write did not validate — NOT recorded as" >&2
  2132	        echo "             delivered (marker-first readers fall back to VERSION; r20)" >&2
  2133	      fi
  2134	      return 0
  2135	      ;;
  2136	  esac
  2137	}
  2138	
  2139	has_profile() {
  2140	  local p="$1"
  2141	  for part in "${PROFILE_PARTS[@]}"; do
  2142	    if [[ "$part" == "$p" ]]; then
  2143	      return 0
  2144	    fi
  2145	  done
  2146	  return 1
  2147	}
  2148	
  2149	# ---------------------------------------------------------------------------
  2150	# PLAN-135 W1 (unit w0r) — pre-flight model-deprecation advisory.

exec
/bin/zsh -lc 'python3 .claude/scripts/local/_release_bump_sites.py bump --help' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
usage: _release_bump_sites.py bump [-h] --today TODAY --target TARGET
                                   [--restamp] [--root ROOT]

optional arguments:
  -h, --help       show this help message and exit
  --today TODAY    YYYY-MM-DD (required)
  --target TARGET  bare semver, e.g. 1.3.0
  --restamp        force the review stamps to move even at the same version
  --root ROOT      repo root (default: cwd)

exec
/bin/zsh -lc "grep -R '\"head_branch\".*v1\\.' -n replay-fixtures .claude/data .claude/plans 2>/dev/null | head -30" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 176ms:
exec
/bin/zsh -lc "git rev-parse HEAD; grep '"'^Anchor-SHA:'"' .claude/plans/PLAN-166/architect/round-1/approved.md .claude/plans/PLAN-167/W4-approved.md; gpg --verify .claude/plans/PLAN-166/architect/round-1/approved.md.asc .claude/plans/PLAN-166/architect/round-1/approved.md >/tmp/gpg166.out 2>&1; echo gpg166="'$?; tail -5 /tmp/gpg166.out; gpg --verify .claude/plans/PLAN-167/W4-approved.md.asc .claude/plans/PLAN-167/W4-approved.md >/tmp/gpg167.out 2>&1; echo gpg167=$?; tail -5 /tmp/gpg167.out' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
05e4845060f16d5b5bbce0fe1eea792a14118ed0
.claude/plans/PLAN-166/architect/round-1/approved.md:Anchor-SHA: 05e4845060f16d5b5bbce0fe1eea792a14118ed0
.claude/plans/PLAN-167/W4-approved.md:Anchor-SHA: 08feef1a83d724eb3201518c3dbf12ddc2864d92
gpg166=2
gpg: error opening key DB: No Keybox daemon running
gpg: failed to create temporary file '/Users/joaocanhada/.gnupg/.#lk0x0000000100c3d8c0.MacBook-Pro-de-Joao-2.local.52004': Operation not permitted
gpg: can't connect to the keyboxd: Operation not permitted
gpg: error opening key DB: No Keybox daemon running
gpg: Can't check signature: No public key
gpg167=2
gpg: error opening key DB: No Keybox daemon running
gpg: failed to create temporary file '/Users/joaocanhada/.gnupg/.#lk0x0000000104c71870.MacBook-Pro-de-Joao-2.local.52006': Operation not permitted
gpg: can't connect to the keyboxd: Operation not permitted
gpg: error opening key DB: No Keybox daemon running
gpg: Can't check signature: No public key

exec
/bin/zsh -lc 'git log --oneline --decorate -12' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
05e4845 (HEAD -> main) plan(PLAN-168): fix ADOPTER-FORK no pack (regressão do 167 pega pelo e2e do 166 + codex r6 independente); manifesto regenerado; fluxo de land encadeado 166→168 com push único
c73423e plan(PLAN-168): OWNER-PREPARE-TO-SIGN — ensaio recusa até o PLAN-166 landar; anchor fixado só então
33f0d7d plan(PLAN-168): W1+W2+W3 executados no overlay — pack pronto-para-assinar
11cd4f6 (origin/main, origin/HEAD) plan(PLAN-167): §9 final — cerimônia executada, pack landado
287c14d governance(PLAN-168): registro de colisão de escrita no debate — erro meu
ec4bdcf fix(PLAN-168): premissa do W2 estava OBSOLETA — meu próprio land a invalidou
8ab0557 fix(PLAN-168): fecho um gate vacuoso no harness que EU construí
b0ec35f plan(PLAN-168): reviewed — debate 3 ADJUST/0 VETO; e uma classificação MINHA corrigida
7c0828a feat(PLAN-167): ownership decision table — one function decides, callers execute
08feef1 chore(PLAN-167): OWNER-W4-LAND.sh — o script que faltava no pack
36eb667 feat(PLAN-167): W3 rail (4 rodadas, teto) + W4 pack pronto para assinatura
0d2e49c plan(PLAN-167): W2.2 completo (3/3 callers); parado no gate do W2

exec
/bin/zsh -lc 'wc -l .claude/plans/PLAN-166/staged-manifest.sha256; find .claude/plans/PLAN-166/staged -type f ! -name .DS_Store | wc -l; shasum -a 256 -c .claude/plans/PLAN-166/staged-manifest.sha256 >/tmp/plan166-manifest-check.out 2>&1; echo rc=$?; tail -20 /tmp/plan166-manifest-check.out' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
      34 .claude/plans/PLAN-166/staged-manifest.sha256
      34
rc=0
.claude/plans/PLAN-166/staged/patches/f3-doctor-delivery-flags.patch: OK
.claude/plans/PLAN-166/staged/patches/f3-fms-conditional-entries.patch: OK
.claude/plans/PLAN-166/staged/patches/f3-framework-version-marker.patch: OK
.claude/plans/PLAN-166/staged/patches/f3-install-delivery-record.patch: OK
.claude/plans/PLAN-166/staged/patches/f3-install-md-consequences.patch: OK
.claude/plans/PLAN-166/staged/patches/f3-test-upgrade-spec-ownership.patch: OK
.claude/plans/PLAN-166/staged/patches/f3-upgrade-spec-forced-refresh.patch: OK
.claude/plans/PLAN-166/staged/patches/release-yml-verdict-delta-ancestry.patch: OK
.claude/plans/PLAN-166/staged/patches/smoke-install-parity-e2e-wiring.patch: OK
.claude/plans/PLAN-166/staged/patches/w0-verdict-template-delta-fields.patch: OK
.claude/plans/PLAN-166/staged/patches/w1-parity-classify-known-open-purge.patch: OK
.claude/plans/PLAN-166/staged/patches/w1a-npm-publish-await-gate.patch: OK
.claude/plans/PLAN-166/staged/patches/w1a-npm-trusted-publisher-txt.patch: OK
.claude/plans/PLAN-166/staged/patches/w1a-release-workflow-asserts.patch: OK
.claude/plans/PLAN-166/staged/scripts/_framework_manifest_set.sh: OK
.claude/plans/PLAN-166/staged/scripts/doctor.sh: OK
.claude/plans/PLAN-166/staged/scripts/install.sh: OK
.claude/plans/PLAN-166/staged/scripts/tests/_parity_classify.py: OK
.claude/plans/PLAN-166/staged/scripts/tests/test-upgrade-spec-ownership.sh: OK
.claude/plans/PLAN-166/staged/scripts/upgrade.sh: OK

exec
/bin/zsh -lc "tail -260 .claude/plans/PLAN-166/archive/codex-r6-2059.md | sed -n '1,260p'" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
                 text = path.read_text(encoding="utf-8")
@@ -335,5 +490,527 @@ class WaveB5NpmPublishYmlTest(TestEnvContext):
         self.assertIn("environment: production-npm", self.source)
 
 
+class Plan166AwaitGateTest(TestEnvContext):
+    """PLAN-166 W1 item 1 — the publish must OBSERVE release.yml's gate.
+
+    Dual-context (staged/live) like the Wave B classes above. These pins
+    STRENGTHEN the posture pins — NpmPublishRcPostureTest keeps running
+    against the live file in every context.
+    """
+
+    def setUp(self):
+        super().setUp()
+        resolved = _plan166_text("npm-publish.yml")
+        if resolved is None:
+            self.skipTest(
+                "PLAN-166 npm-publish.yml not landed and staged mirror "
+                "absent (pre-landing CI window)"
+            )
+        self.source, self.context = resolved
+
+    def _jobs(self) -> dict:
+        try:
+            import yaml  # type: ignore
+        except ImportError:  # pragma: no cover - CI installs pyyaml
+            self.skipTest("pyyaml not installed")
+        return yaml.safe_load(self.source)["jobs"]
+
+    def test_publish_needs_await_gate(self):
+        # String-level (runs even without pyyaml): the load-bearing edge.
+        self.assertIn(
+            "needs: await-release-gate", self.source,
+            "publish no longer waits for the await-release-gate job — "
+            "the npm publish would stop observing release.yml's "
+            "release-gate (PLAN-166 F1, P0)",
+        )
+
+    def test_publish_needs_await_gate_structurally(self):
+        jobs = self._jobs()

exec
/bin/zsh -lc "git status --short; printf '\\nnew files under repo created by tests?\\n'; git status --short --untracked-files=all | tail -60" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
 A .claude/.framework-version
 A .claude/adr/ADR-155-AMEND-1-delivery-record-ownership.md
 A .claude/governance/npm-trusted-publisher.txt
 M .claude/governance/pair-rail-verdict-template.md
 M .claude/plans/PLAN-166/W1-approved-draft.md
 A .claude/plans/PLAN-166/architect/round-1/approved.md
 M .claude/plans/PLAN-166/staged-manifest.sha256
 M .claude/plans/PLAN-168/staged-manifest.sha256
 M .claude/scripts/check-framework-updates.sh
 M .claude/scripts/tests/test_release_workflow_asserts.py
 M .github/workflows/npm-publish.yml
 M .github/workflows/release.yml
 M .github/workflows/smoke-install.yml
 M INSTALL.md
 M README.md
 M README.pt-BR.md
 M RELEASE.md
 M docs/ARCHITECTURE.md
 M docs/CTO-GUIDE.md
 M docs/FAQ.md
 M docs/GUIA-COMPLETO.md
 M docs/README.md
 M npm/README.md
 M scripts/doctor.sh
 M scripts/tests/_parity_classify.py
 A scripts/tests/test-upgrade-spec-ownership.sh
?? .claude/plans/PLAN-166/OWNER-W1-LAND-step1.sh
?? .claude/plans/PLAN-166/W1-ceremony-log.md
?? .claude/plans/PLAN-166/architect/round-1/approved.md.asc
?? .claude/plans/PLAN-166/archive/
?? .claude/plans/PLAN-167/OWNER-PREPARE-TO-SIGN.sh
?? .claude/plans/PLAN-167/W4-approved.md
?? .claude/plans/PLAN-167/W4-approved.md.asc
?? .claude/plans/PLAN-168/archive/

new files under repo created by tests?
 A .claude/.framework-version
 A .claude/adr/ADR-155-AMEND-1-delivery-record-ownership.md
 A .claude/governance/npm-trusted-publisher.txt
 M .claude/governance/pair-rail-verdict-template.md
 M .claude/plans/PLAN-166/W1-approved-draft.md
 A .claude/plans/PLAN-166/architect/round-1/approved.md
 M .claude/plans/PLAN-166/staged-manifest.sha256
 M .claude/plans/PLAN-168/staged-manifest.sha256
 M .claude/scripts/check-framework-updates.sh
 M .claude/scripts/tests/test_release_workflow_asserts.py
 M .github/workflows/npm-publish.yml
 M .github/workflows/release.yml
 M .github/workflows/smoke-install.yml
 M INSTALL.md
 M README.md
 M README.pt-BR.md
 M RELEASE.md
 M docs/ARCHITECTURE.md
 M docs/CTO-GUIDE.md
 M docs/FAQ.md
 M docs/GUIA-COMPLETO.md
 M docs/README.md
 M npm/README.md
 M scripts/doctor.sh
 M scripts/tests/_parity_classify.py
 A scripts/tests/test-upgrade-spec-ownership.sh
?? .claude/plans/PLAN-166/OWNER-W1-LAND-step1.sh
?? .claude/plans/PLAN-166/W1-ceremony-log.md
?? .claude/plans/PLAN-166/architect/round-1/approved.md.asc
?? .claude/plans/PLAN-166/archive/ceremony-porcelain-20260806-1430.txt
?? .claude/plans/PLAN-166/archive/ceremony-worktree-20260806-1430.diff
?? .claude/plans/PLAN-166/archive/codex-r6-2059.md
?? .claude/plans/PLAN-166/archive/codex-review-sentinel.md
?? .claude/plans/PLAN-166/archive/codex-review-w0-residuals.md
?? .claude/plans/PLAN-166/archive/codex-review-w1-ceremony.md
?? .claude/plans/PLAN-166/archive/codex-review-w1-round10.md
?? .claude/plans/PLAN-166/archive/codex-review-w1-round11.md
?? .claude/plans/PLAN-166/archive/codex-review-w1-round2.md
?? .claude/plans/PLAN-166/archive/codex-review-w1-round3.md
?? .claude/plans/PLAN-166/archive/codex-review-w1-round4.md
?? .claude/plans/PLAN-166/archive/codex-review-w1-round5.md
?? .claude/plans/PLAN-166/archive/codex-review-w1-round6.md
?? .claude/plans/PLAN-166/archive/codex-review-w1-round7.md
?? .claude/plans/PLAN-166/archive/codex-review-w1-round8.md
?? .claude/plans/PLAN-166/archive/codex-review-w1-round9.md
?? .claude/plans/PLAN-166/archive/mirror-fixes.sh
?? .claude/plans/PLAN-166/archive/w1-staged-pack-20260806-0159.tar.gz
?? .claude/plans/PLAN-166/archive/w1-staged-pack-final-20260806-0722.tar.gz
?? .claude/plans/PLAN-167/OWNER-PREPARE-TO-SIGN.sh
?? .claude/plans/PLAN-167/W4-approved.md
?? .claude/plans/PLAN-167/W4-approved.md.asc
?? .claude/plans/PLAN-168/archive/0001-plan168-W1-CI-wiring-dos-or-culos-de-propriedade.patch
?? .claude/plans/PLAN-168/archive/0002-plan168-W2-W3-INV-4-curada-pelo-gerador-nico-ADR-190.patch
?? .claude/plans/PLAN-168/archive/0003-plan168-baseline-map-re-gravado-62-GREEN-3-RED-run-2.patch
?? .claude/plans/PLAN-168/archive/0004-plan168-restaura-token-ADOPTER-FORK-na-WARNING-do-fo.patch
?? .claude/plans/PLAN-168/archive/full-e2e-20260807-2017.log
?? .claude/plans/PLAN-168/archive/pack-full.diff

exec
/bin/zsh -lc "git diff -- .claude/plans/PLAN-168/staged-manifest.sha256; printf '\\n--- new patch ---\\n'; sed -n '1,260p' .claude/plans/PLAN-168/archive/0004-plan168-restaura-token-ADOPTER-FORK-na-WARNING-do-fo.patch; printf '\\n--- plan168 status files ---\\n'; find .claude/plans/PLAN-168 -maxdepth 2 -type f -print | sort | sed -n '1,260p'" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
diff --git a/.claude/plans/PLAN-168/staged-manifest.sha256 b/.claude/plans/PLAN-168/staged-manifest.sha256
index adefb18..f7ddb2e 100644
--- a/.claude/plans/PLAN-168/staged-manifest.sha256
+++ b/.claude/plans/PLAN-168/staged-manifest.sha256
@@ -21,4 +21,4 @@ d7a4c49877933e4938e735ba5a063e62159012c1235c1367e05f327d03069402  .claude/plans/
 6ba1e21c1e94d49b37544531372f29f1a0377a241078165d46a7a5a9aed2d838  .claude/plans/PLAN-168/staged/scripts/tests/test-ownership-table.sh
 ce9864e7bb995cec539e07d50bde84afe342c0bb3268a6e1957f0916b7a5a296  .claude/plans/PLAN-168/staged/scripts/tests/test-protocol-pointer-inv4.sh
 52b0f66bad01be7f1737b270a85571fd5b01601b69bac2dc63472312e52c2fb9  .claude/plans/PLAN-168/staged/scripts/tests/test-protocol-pointer-render.sh
-c49f7ffebc729842f10126719ca65888aa52dcdccaef782f71f4a73921daf6f4  .claude/plans/PLAN-168/staged/scripts/upgrade.sh
+8e59d206b8f36babb61cd22ceee0c00d580d7cb132faac4d3cb5c4d1e230aff7  .claude/plans/PLAN-168/staged/scripts/upgrade.sh

--- new patch ---
From a23976841b86c0674d8915db11812f99c2da15fa Mon Sep 17 00:00:00 2001
From: =?UTF-8?q?Jo=C3=A3o=20Canhada?= <joaocanhada@users.noreply.github.com>
Date: Fri, 7 Aug 2026 21:12:47 -0300
Subject: [PATCH 4/4] plan168: restaura token ADOPTER-FORK na WARNING do fork
 preservado
MIME-Version: 1.0
Content-Type: text/plain; charset=UTF-8
Content-Transfer-Encoding: 8bit

Regressão do rewrite do PLAN-167 (7c0828a): o comentário §1869 promete
'named WARNING' e o F3 e2e (S4) grepa o token — a mensagem o perdeu.
Pego pelo e2e do PLAN-166 no land (44/45); overlay volta a 45/45.
---
 scripts/upgrade.sh | 8 ++++++--
 1 file changed, 6 insertions(+), 2 deletions(-)

diff --git a/scripts/upgrade.sh b/scripts/upgrade.sh
index 0bce369..cde1ff2 100755
--- a/scripts/upgrade.sh
+++ b/scripts/upgrade.sh
@@ -1982,8 +1982,12 @@ _refresh_spec_contract() {
         if mkdir -p "$( dirname "$bdir" )" 2>/dev/null && cp -R "$ddir" "$bdir" 2>/dev/null; then
           _snap_ok=1
         fi
-        echo "    WARNING: SPEC/v1 is not framework-owned (no delivery record, and it" >&2
-        echo "             matches neither this checkout nor any pristine shipped SPEC)" >&2
+        # The token "ADOPTER-FORK" is CONTRACT, not prose: the §1869 route
+        # comment promises a NAMED warning, and the F3 e2e (S4) greps for it.
+        # The PLAN-167 rewrite dropped it — caught by that e2e on the PLAN-166
+        # land (44/45) and restored here (PLAN-168).
+        echo "    WARNING: SPEC/v1 ADOPTER-FORK — not framework-owned (no delivery" >&2
+        echo "             record; matches neither this checkout nor any pristine shipped SPEC)" >&2
         if [ "$_snap_ok" -eq 1 ]; then
           echo "             — PRESERVED in place (snapshot in $BAK_DIR/SPEC/v1)." >&2
           echo "             To hand it back to the framework: remove the target SPEC/v1," >&2
-- 
2.50.1 (Apple Git-155)


--- plan168 status files ---
.claude/plans/PLAN-168/OWNER-LAND.sh
.claude/plans/PLAN-168/OWNER-PREPARE-TO-SIGN.sh
.claude/plans/PLAN-168/W-approved-draft.md
.claude/plans/PLAN-168/archive/0001-plan168-W1-CI-wiring-dos-or-culos-de-propriedade.patch
.claude/plans/PLAN-168/archive/0002-plan168-W2-W3-INV-4-curada-pelo-gerador-nico-ADR-190.patch
.claude/plans/PLAN-168/archive/0003-plan168-baseline-map-re-gravado-62-GREEN-3-RED-run-2.patch
.claude/plans/PLAN-168/archive/0004-plan168-restaura-token-ADOPTER-FORK-na-WARNING-do-fo.patch
.claude/plans/PLAN-168/archive/full-e2e-20260807-2017.log
.claude/plans/PLAN-168/archive/pack-full.diff
.claude/plans/PLAN-168/land-table.tsv
.claude/plans/PLAN-168/rail/README-scope.md
.claude/plans/PLAN-168/rail/codex-r0-misscoped.md
.claude/plans/PLAN-168/rail/codex-r1.md
.claude/plans/PLAN-168/rail/codex-r2.md
.claude/plans/PLAN-168/rail/codex-r3.md
.claude/plans/PLAN-168/staged-manifest.sha256
.claude/plans/PLAN-168/staged/CLAUDE.md
.claude/plans/PLAN-168/staged/README.md
.claude/plans/PLAN-168/staged/README.pt-BR.md

exec
/bin/zsh -lc 'shasum -a 256 -c .claude/plans/PLAN-168/staged-manifest.sha256 >/tmp/plan168check.out 2>&1; echo rc=$?; tail -8 /tmp/plan168check.out; printf '"'\\n--- smoke PR/push filter equality ---\\n'; python3 - <<'PY'
from pathlib import Path
import yaml
p=yaml.safe_load(Path('.github/workflows/smoke-install.yml').read_text())
on=p.get('on') or p.get(True)
a=on['pull_request']['paths']; b=on['push']['paths']
print(a==b, len(a), len(b), sorted(set(a)"'^set(b)))
PY' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
rc=0
.claude/plans/PLAN-168/staged/scripts/tests/ownership-expected-reds.txt: OK
.claude/plans/PLAN-168/staged/scripts/tests/ownership-nightly-gate.sh: OK
.claude/plans/PLAN-168/staged/scripts/tests/ownership_table.tsv: OK
.claude/plans/PLAN-168/staged/scripts/tests/test-ownership-nightly-gate.sh: OK
.claude/plans/PLAN-168/staged/scripts/tests/test-ownership-table.sh: OK
.claude/plans/PLAN-168/staged/scripts/tests/test-protocol-pointer-inv4.sh: OK
.claude/plans/PLAN-168/staged/scripts/tests/test-protocol-pointer-render.sh: OK
.claude/plans/PLAN-168/staged/scripts/upgrade.sh: OK

--- smoke PR/push filter equality ---
True 17 17 []

Inspected all current changes, traced release/install paths, ran actionlint and focused tests; one newly wired ownership test fails and the positive-control evidence check is ineffective.
  ✓ Inspect staged, unstaged, and untracked changes
  ✓ Trace affected code paths and run focused checks
  ✓ Return prioritized review findings
codex
The newly mandatory ownership test currently fails deterministically, which makes the smoke-install workflow red. The positive-control wrapper also accepts non-causal evidence and therefore does not enforce its documented safeguard.

Full review comments:

- [P1] Match the S4 assertion to the emitted warning — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/tests/test-upgrade-spec-ownership.sh:259-261
  When the newly wired test reaches S4, `upgrade.sh` emits `WARNING: SPEC/v1 is not framework-owned...` without the literal `ADOPTER-FORK`, so this grep always records a failure. Running `bash scripts/tests/test-upgrade-spec-ownership.sh` currently ends with `pass=44 fail=1` and exit 1, causing every smoke-install run that executes the new step to fail despite the fork being preserved correctly.

- [P2] Require plant-specific failure evidence — /Users/joaocanhada/canhada-labs/ceo-orchestration/.github/workflows/smoke-install.yml:206-206
  If the positive-control run exits 1 because of an unrelated classifier divergence after plant setup, this check still passes: `PLANTED` is printed whenever the mutation is constructed, and `per-mode verdicts` is printed by every completed run. Consequently this claimed second factor does not prove that removing the `.claude/commands` refresh caused the red result; it should require evidence naming the expected planted divergence.
The newly mandatory ownership test currently fails deterministically, which makes the smoke-install workflow red. The positive-control wrapper also accepts non-causal evidence and therefore does not enforce its documented safeguard.

Full review comments:

- [P1] Match the S4 assertion to the emitted warning — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/tests/test-upgrade-spec-ownership.sh:259-261
  When the newly wired test reaches S4, `upgrade.sh` emits `WARNING: SPEC/v1 is not framework-owned...` without the literal `ADOPTER-FORK`, so this grep always records a failure. Running `bash scripts/tests/test-upgrade-spec-ownership.sh` currently ends with `pass=44 fail=1` and exit 1, causing every smoke-install run that executes the new step to fail despite the fork being preserved correctly.

- [P2] Require plant-specific failure evidence — /Users/joaocanhada/canhada-labs/ceo-orchestration/.github/workflows/smoke-install.yml:206-206
  If the positive-control run exits 1 because of an unrelated classifier divergence after plant setup, this check still passes: `PLANTED` is printed whenever the mutation is constructed, and `per-mode verdicts` is printed by every completed run. Consequently this claimed second factor does not prove that removing the `.claude/commands` refresh caused the red result; it should require evidence naming the expected planted divergence.

exec
/bin/zsh -lc "nl -ba .github/workflows/smoke-install.yml | sed -n '188,212p'" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
   188	      # This step MUST stay AFTER the plain gate: if the un-planted run were
   189	      # already fatal, rc=1 here would prove nothing about the plant.
   190	      - name: Install/upgrade parity - positive control (planted divergence)
   191	        run: |
   192	          set -uo pipefail
   193	          rc=0
   194	          bash scripts/tests/test-install-upgrade-parity-e2e.sh \
   195	            --positive-control > /tmp/parity-control.log 2>&1 || rc=$?
   196	          if [ "$rc" -ne 1 ]; then
   197	            cat /tmp/parity-control.log
   198	            echo "::error::parity positive control returned rc=$rc, expected 1 - the planted install/upgrade divergence did NOT turn the gate red, so the gate above proves nothing"
   199	            exit 1
   200	          fi
   201	          # Second factor, LOAD-BEARING (re-pass closure): under `set -uo
   202	          # pipefail` (no -e) a non-matching grep would NOT fail the step, so
   203	          # an rc=1 from a failure UNRELATED to the plant (log with none of
   204	          # the plant markers) would pass — the registered-vacuous class
   205	          # (S292) this step exists to close. Demand plant evidence or fail.
   206	          grep -E "PLANTED|per-mode verdicts|positive control:" /tmp/parity-control.log || {
   207	            cat /tmp/parity-control.log
   208	            echo "::error::rc=1 but the log carries no PLANTED/per-mode-verdict evidence - the control went red for an unrelated reason, which proves nothing about the plant (vacuous control)"
   209	            exit 1
   210	          }
   211	          echo "positive control OK: planted divergence -> exit 1 in every ceremony mode"
   212	

exec
/bin/zsh -lc "tail -220 .claude/plans/PLAN-166/archive/codex-r7-stophook-2135.md | sed -n '1,220p'" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
 A scripts/tests/test-upgrade-spec-ownership.sh
?? .claude/plans/PLAN-166/OWNER-W1-LAND-step1.sh
?? .claude/plans/PLAN-166/W1-ceremony-log.md
?? .claude/plans/PLAN-166/architect/round-1/approved.md.asc
?? .claude/plans/PLAN-166/archive/
?? .claude/plans/PLAN-167/OWNER-PREPARE-TO-SIGN.sh
?? .claude/plans/PLAN-167/W4-approved.md
?? .claude/plans/PLAN-167/W4-approved.md.asc
?? .claude/plans/PLAN-168/archive/

new files under repo created by tests?
 A .claude/.framework-version
 A .claude/adr/ADR-155-AMEND-1-delivery-record-ownership.md
 A .claude/governance/npm-trusted-publisher.txt
 M .claude/governance/pair-rail-verdict-template.md
 M .claude/plans/PLAN-166/W1-approved-draft.md
 A .claude/plans/PLAN-166/architect/round-1/approved.md
 M .claude/plans/PLAN-166/staged-manifest.sha256
 M .claude/plans/PLAN-168/staged-manifest.sha256
 M .claude/scripts/check-framework-updates.sh
 M .claude/scripts/tests/test_release_workflow_asserts.py
 M .github/workflows/npm-publish.yml
 M .github/workflows/release.yml
 M .github/workflows/smoke-install.yml
 M INSTALL.md
 M README.md
 M README.pt-BR.md
 M RELEASE.md
 M docs/ARCHITECTURE.md
 M docs/CTO-GUIDE.md
 M docs/FAQ.md
 M docs/GUIA-COMPLETO.md
 M docs/README.md
 M npm/README.md
 M scripts/doctor.sh
 M scripts/tests/_parity_classify.py
 A scripts/tests/test-upgrade-spec-ownership.sh
?? .claude/plans/PLAN-166/OWNER-W1-LAND-step1.sh
?? .claude/plans/PLAN-166/W1-ceremony-log.md
?? .claude/plans/PLAN-166/architect/round-1/approved.md.asc
?? .claude/plans/PLAN-166/archive/ceremony-porcelain-20260806-1430.txt
?? .claude/plans/PLAN-166/archive/ceremony-worktree-20260806-1430.diff
?? .claude/plans/PLAN-166/archive/codex-r6-2059.md
?? .claude/plans/PLAN-166/archive/codex-review-sentinel.md
?? .claude/plans/PLAN-166/archive/codex-review-w0-residuals.md
?? .claude/plans/PLAN-166/archive/codex-review-w1-ceremony.md
?? .claude/plans/PLAN-166/archive/codex-review-w1-round10.md
?? .claude/plans/PLAN-166/archive/codex-review-w1-round11.md
?? .claude/plans/PLAN-166/archive/codex-review-w1-round2.md
?? .claude/plans/PLAN-166/archive/codex-review-w1-round3.md
?? .claude/plans/PLAN-166/archive/codex-review-w1-round4.md
?? .claude/plans/PLAN-166/archive/codex-review-w1-round5.md
?? .claude/plans/PLAN-166/archive/codex-review-w1-round6.md
?? .claude/plans/PLAN-166/archive/codex-review-w1-round7.md
?? .claude/plans/PLAN-166/archive/codex-review-w1-round8.md
?? .claude/plans/PLAN-166/archive/codex-review-w1-round9.md
?? .claude/plans/PLAN-166/archive/mirror-fixes.sh
?? .claude/plans/PLAN-166/archive/w1-staged-pack-20260806-0159.tar.gz
?? .claude/plans/PLAN-166/archive/w1-staged-pack-final-20260806-0722.tar.gz
?? .claude/plans/PLAN-167/OWNER-PREPARE-TO-SIGN.sh
?? .claude/plans/PLAN-167/W4-approved.md
?? .claude/plans/PLAN-167/W4-approved.md.asc
?? .claude/plans/PLAN-168/archive/0001-plan168-W1-CI-wiring-dos-or-culos-de-propriedade.patch
?? .claude/plans/PLAN-168/archive/0002-plan168-W2-W3-INV-4-curada-pelo-gerador-nico-ADR-190.patch
?? .claude/plans/PLAN-168/archive/0003-plan168-baseline-map-re-gravado-62-GREEN-3-RED-run-2.patch
?? .claude/plans/PLAN-168/archive/0004-plan168-restaura-token-ADOPTER-FORK-na-WARNING-do-fo.patch
?? .claude/plans/PLAN-168/archive/full-e2e-20260807-2017.log
?? .claude/plans/PLAN-168/archive/pack-full.diff

exec
/bin/zsh -lc "git diff -- .claude/plans/PLAN-168/staged-manifest.sha256; printf '\\n--- new patch ---\\n'; sed -n '1,260p' .claude/plans/PLAN-168/archive/0004-plan168-restaura-token-ADOPTER-FORK-na-WARNING-do-fo.patch; printf '\\n--- plan168 status files ---\\n'; find .claude/plans/PLAN-168 -maxdepth 2 -type f -print | sort | sed -n '1,260p'" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
diff --git a/.claude/plans/PLAN-168/staged-manifest.sha256 b/.claude/plans/PLAN-168/staged-manifest.sha256
index adefb18..f7ddb2e 100644
--- a/.claude/plans/PLAN-168/staged-manifest.sha256
+++ b/.claude/plans/PLAN-168/staged-manifest.sha256
@@ -21,4 +21,4 @@ d7a4c49877933e4938e735ba5a063e62159012c1235c1367e05f327d03069402  .claude/plans/
 6ba1e21c1e94d49b37544531372f29f1a0377a241078165d46a7a5a9aed2d838  .claude/plans/PLAN-168/staged/scripts/tests/test-ownership-table.sh
 ce9864e7bb995cec539e07d50bde84afe342c0bb3268a6e1957f0916b7a5a296  .claude/plans/PLAN-168/staged/scripts/tests/test-protocol-pointer-inv4.sh
 52b0f66bad01be7f1737b270a85571fd5b01601b69bac2dc63472312e52c2fb9  .claude/plans/PLAN-168/staged/scripts/tests/test-protocol-pointer-render.sh
-c49f7ffebc729842f10126719ca65888aa52dcdccaef782f71f4a73921daf6f4  .claude/plans/PLAN-168/staged/scripts/upgrade.sh
+8e59d206b8f36babb61cd22ceee0c00d580d7cb132faac4d3cb5c4d1e230aff7  .claude/plans/PLAN-168/staged/scripts/upgrade.sh

--- new patch ---
From a23976841b86c0674d8915db11812f99c2da15fa Mon Sep 17 00:00:00 2001
From: =?UTF-8?q?Jo=C3=A3o=20Canhada?= <joaocanhada@users.noreply.github.com>
Date: Fri, 7 Aug 2026 21:12:47 -0300
Subject: [PATCH 4/4] plan168: restaura token ADOPTER-FORK na WARNING do fork
 preservado
MIME-Version: 1.0
Content-Type: text/plain; charset=UTF-8
Content-Transfer-Encoding: 8bit

Regressão do rewrite do PLAN-167 (7c0828a): o comentário §1869 promete
'named WARNING' e o F3 e2e (S4) grepa o token — a mensagem o perdeu.
Pego pelo e2e do PLAN-166 no land (44/45); overlay volta a 45/45.
---
 scripts/upgrade.sh | 8 ++++++--
 1 file changed, 6 insertions(+), 2 deletions(-)

diff --git a/scripts/upgrade.sh b/scripts/upgrade.sh
index 0bce369..cde1ff2 100755
--- a/scripts/upgrade.sh
+++ b/scripts/upgrade.sh
@@ -1982,8 +1982,12 @@ _refresh_spec_contract() {
         if mkdir -p "$( dirname "$bdir" )" 2>/dev/null && cp -R "$ddir" "$bdir" 2>/dev/null; then
           _snap_ok=1
         fi
-        echo "    WARNING: SPEC/v1 is not framework-owned (no delivery record, and it" >&2
-        echo "             matches neither this checkout nor any pristine shipped SPEC)" >&2
+        # The token "ADOPTER-FORK" is CONTRACT, not prose: the §1869 route
+        # comment promises a NAMED warning, and the F3 e2e (S4) greps for it.
+        # The PLAN-167 rewrite dropped it — caught by that e2e on the PLAN-166
+        # land (44/45) and restored here (PLAN-168).
+        echo "    WARNING: SPEC/v1 ADOPTER-FORK — not framework-owned (no delivery" >&2
+        echo "             record; matches neither this checkout nor any pristine shipped SPEC)" >&2
         if [ "$_snap_ok" -eq 1 ]; then
           echo "             — PRESERVED in place (snapshot in $BAK_DIR/SPEC/v1)." >&2
           echo "             To hand it back to the framework: remove the target SPEC/v1," >&2
-- 
2.50.1 (Apple Git-155)


--- plan168 status files ---
.claude/plans/PLAN-168/OWNER-LAND.sh
.claude/plans/PLAN-168/OWNER-PREPARE-TO-SIGN.sh
.claude/plans/PLAN-168/W-approved-draft.md
.claude/plans/PLAN-168/archive/0001-plan168-W1-CI-wiring-dos-or-culos-de-propriedade.patch
.claude/plans/PLAN-168/archive/0002-plan168-W2-W3-INV-4-curada-pelo-gerador-nico-ADR-190.patch
.claude/plans/PLAN-168/archive/0003-plan168-baseline-map-re-gravado-62-GREEN-3-RED-run-2.patch
.claude/plans/PLAN-168/archive/0004-plan168-restaura-token-ADOPTER-FORK-na-WARNING-do-fo.patch
.claude/plans/PLAN-168/archive/full-e2e-20260807-2017.log
.claude/plans/PLAN-168/archive/pack-full.diff
.claude/plans/PLAN-168/land-table.tsv
.claude/plans/PLAN-168/rail/README-scope.md
.claude/plans/PLAN-168/rail/codex-r0-misscoped.md
.claude/plans/PLAN-168/rail/codex-r1.md
.claude/plans/PLAN-168/rail/codex-r2.md
.claude/plans/PLAN-168/rail/codex-r3.md
.claude/plans/PLAN-168/staged-manifest.sha256
.claude/plans/PLAN-168/staged/CLAUDE.md
.claude/plans/PLAN-168/staged/README.md
.claude/plans/PLAN-168/staged/README.pt-BR.md

exec
/bin/zsh -lc 'shasum -a 256 -c .claude/plans/PLAN-168/staged-manifest.sha256 >/tmp/plan168check.out 2>&1; echo rc=$?; tail -8 /tmp/plan168check.out; printf '"'\\n--- smoke PR/push filter equality ---\\n'; python3 - <<'PY'
from pathlib import Path
import yaml
p=yaml.safe_load(Path('.github/workflows/smoke-install.yml').read_text())
on=p.get('on') or p.get(True)
a=on['pull_request']['paths']; b=on['push']['paths']
print(a==b, len(a), len(b), sorted(set(a)"'^set(b)))
PY' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
rc=0
.claude/plans/PLAN-168/staged/scripts/tests/ownership-expected-reds.txt: OK
.claude/plans/PLAN-168/staged/scripts/tests/ownership-nightly-gate.sh: OK
.claude/plans/PLAN-168/staged/scripts/tests/ownership_table.tsv: OK
.claude/plans/PLAN-168/staged/scripts/tests/test-ownership-nightly-gate.sh: OK
.claude/plans/PLAN-168/staged/scripts/tests/test-ownership-table.sh: OK
.claude/plans/PLAN-168/staged/scripts/tests/test-protocol-pointer-inv4.sh: OK
.claude/plans/PLAN-168/staged/scripts/tests/test-protocol-pointer-render.sh: OK
.claude/plans/PLAN-168/staged/scripts/upgrade.sh: OK

--- smoke PR/push filter equality ---
True 17 17 []

Inspected all current changes, traced release/install paths, ran actionlint and focused tests; one newly wired ownership test fails and the positive-control evidence check is ineffective.
  ✓ Inspect staged, unstaged, and untracked changes
  ✓ Trace affected code paths and run focused checks
  ✓ Return prioritized review findings
codex
The newly mandatory ownership test currently fails deterministically, which makes the smoke-install workflow red. The positive-control wrapper also accepts non-causal evidence and therefore does not enforce its documented safeguard.

Full review comments:

- [P1] Match the S4 assertion to the emitted warning — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/tests/test-upgrade-spec-ownership.sh:259-261
  When the newly wired test reaches S4, `upgrade.sh` emits `WARNING: SPEC/v1 is not framework-owned...` without the literal `ADOPTER-FORK`, so this grep always records a failure. Running `bash scripts/tests/test-upgrade-spec-ownership.sh` currently ends with `pass=44 fail=1` and exit 1, causing every smoke-install run that executes the new step to fail despite the fork being preserved correctly.

- [P2] Require plant-specific failure evidence — /Users/joaocanhada/canhada-labs/ceo-orchestration/.github/workflows/smoke-install.yml:206-206
  If the positive-control run exits 1 because of an unrelated classifier divergence after plant setup, this check still passes: `PLANTED` is printed whenever the mutation is constructed, and `per-mode verdicts` is printed by every completed run. Consequently this claimed second factor does not prove that removing the `.claude/commands` refresh caused the red result; it should require evidence naming the expected planted divergence.
The newly mandatory ownership test currently fails deterministically, which makes the smoke-install workflow red. The positive-control wrapper also accepts non-causal evidence and therefore does not enforce its documented safeguard.

Full review comments:

- [P1] Match the S4 assertion to the emitted warning — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/tests/test-upgrade-spec-ownership.sh:259-261
  When the newly wired test reaches S4, `upgrade.sh` emits `WARNING: SPEC/v1 is not framework-owned...` without the literal `ADOPTER-FORK`, so this grep always records a failure. Running `bash scripts/tests/test-upgrade-spec-ownership.sh` currently ends with `pass=44 fail=1` and exit 1, causing every smoke-install run that executes the new step to fail despite the fork being preserved correctly.

- [P2] Require plant-specific failure evidence — /Users/joaocanhada/canhada-labs/ceo-orchestration/.github/workflows/smoke-install.yml:206-206
  If the positive-control run exits 1 because of an unrelated classifier divergence after plant setup, this check still passes: `PLANTED` is printed whenever the mutation is constructed, and `per-mode verdicts` is printed by every completed run. Consequently this claimed second factor does not prove that removing the `.claude/commands` refresh caused the red result; it should require evidence naming the expected planted divergence.

exec
/bin/zsh -lc "nl -ba .github/workflows/smoke-install.yml | sed -n '188,212p'" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
   188	      # This step MUST stay AFTER the plain gate: if the un-planted run were
   189	      # already fatal, rc=1 here would prove nothing about the plant.
   190	      - name: Install/upgrade parity - positive control (planted divergence)
   191	        run: |
   192	          set -uo pipefail
   193	          rc=0
   194	          bash scripts/tests/test-install-upgrade-parity-e2e.sh \
   195	            --positive-control > /tmp/parity-control.log 2>&1 || rc=$?
   196	          if [ "$rc" -ne 1 ]; then
   197	            cat /tmp/parity-control.log
   198	            echo "::error::parity positive control returned rc=$rc, expected 1 - the planted install/upgrade divergence did NOT turn the gate red, so the gate above proves nothing"
   199	            exit 1
   200	          fi
   201	          # Second factor, LOAD-BEARING (re-pass closure): under `set -uo
   202	          # pipefail` (no -e) a non-matching grep would NOT fail the step, so
   203	          # an rc=1 from a failure UNRELATED to the plant (log with none of
   204	          # the plant markers) would pass — the registered-vacuous class
   205	          # (S292) this step exists to close. Demand plant evidence or fail.
   206	          grep -E "PLANTED|per-mode verdicts|positive control:" /tmp/parity-control.log || {
   207	            cat /tmp/parity-control.log
   208	            echo "::error::rc=1 but the log carries no PLANTED/per-mode-verdict evidence - the control went red for an unrelated reason, which proves nothing about the plant (vacuous control)"
   209	            exit 1
   210	          }
   211	          echo "positive control OK: planted divergence -> exit 1 in every ceremony mode"
   212	


Reviewed executable diffs and untracked runbooks, ran syntax/actionlint/count checks and focused e2e tests. The ownership e2e deterministically fails 44/45, and the parity control's evidence grep is non-causal.
  ✓ Inventory all changed and untracked files and identify executable surfaces
  ✓ Review shell scripts, workflows, and tests against existing contracts
  ✓ Run targeted read-only checks/tests and validate suspected regressions
  → Return prioritized JSON findings
  ✓ Inventory all changed and untracked files and identify executable surfaces
  ✓ Review shell scripts, workflows, and tests against existing contracts
  ✓ Run targeted read-only checks/tests and validate suspected regressions
  ✓ Return prioritized JSON findings
codex
The patch makes a deterministically failing ownership test mandatory in CI. Its new parity positive control also accepts non-causal evidence and can pass vacuously.

Full review comments:

- [P1] Restore the S4 warning token before wiring the test — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/tests/test-upgrade-spec-ownership.sh:259-261
  When this newly mandatory test reaches S4, the current `upgrade.sh` warning does not contain the literal `ADOPTER-FORK`, so this assertion records a failure even though the fork is preserved. Running `bash scripts/tests/test-upgrade-spec-ownership.sh` currently ends with `pass=44 fail=1` and exit 1, making every triggered smoke-install workflow fail.

- [P2] Require evidence of the planted divergence — /Users/joaocanhada/canhada-labs/ceo-orchestration/.github/workflows/smoke-install.yml:206-206
  If the positive-control run exits 1 because of an unrelated classifier failure after plant setup, this grep still succeeds: `PLANTED` is emitted whenever the mutation is constructed, while `per-mode verdicts` appears in every completed run. The workflow can therefore report that the control is alive without proving that removing the `.claude/commands` refresh caused the failure; require output identifying the expected planted path or classification.
The patch makes a deterministically failing ownership test mandatory in CI. Its new parity positive control also accepts non-causal evidence and can pass vacuously.

Full review comments:

- [P1] Restore the S4 warning token before wiring the test — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/tests/test-upgrade-spec-ownership.sh:259-261
  When this newly mandatory test reaches S4, the current `upgrade.sh` warning does not contain the literal `ADOPTER-FORK`, so this assertion records a failure even though the fork is preserved. Running `bash scripts/tests/test-upgrade-spec-ownership.sh` currently ends with `pass=44 fail=1` and exit 1, making every triggered smoke-install workflow fail.

- [P2] Require evidence of the planted divergence — /Users/joaocanhada/canhada-labs/ceo-orchestration/.github/workflows/smoke-install.yml:206-206
  If the positive-control run exits 1 because of an unrelated classifier failure after plant setup, this grep still succeeds: `PLANTED` is emitted whenever the mutation is constructed, while `per-mode verdicts` appears in every completed run. The workflow can therefore report that the control is alive without proving that removing the `.claude/commands` refresh caused the failure; require output identifying the expected planted path or classification.
