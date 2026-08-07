OpenAI Codex v0.144.6
--------
workdir: /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
model: gpt-5.6-sol
provider: openai
approval: never
sandbox: read-only
reasoning effort: xhigh
reasoning summaries: none
session id: 019fdcb3-3f15-7443-930a-7b29adc25a46
--------
user
current changes
exec
/bin/zsh -lc "git status --short && printf '\\n--- DIFF STAT ---\\n' && git diff --stat && printf '\\n--- STAGED STAT ---\\n' && git diff --cached --stat" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 597ms:
 .claude/governance/pair-rail-verdict-template.md   |  18 +
 .claude/plans/PLAN-166/W1-approved-draft.md        |   1 +
 .claude/plans/PLAN-166/staged-manifest.sha256      |  22 +-
 .claude/scripts/check-framework-updates.sh         |  95 ++-
 .claude/scripts/check-model-deprecations.py        |  13 +-
 .../scripts/tests/test_release_workflow_asserts.py | 683 ++++++++++++++++-
 .github/workflows/npm-publish.yml                  | 151 ++++
 .github/workflows/release.yml                      | 164 +++++
 .github/workflows/smoke-install.yml                | 119 ++-
 CLAUDE.md                                          |   2 +-
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
 scripts/_framework_manifest_set.sh                 | 335 ++++++++-
 scripts/doctor.sh                                  |  34 +
 scripts/install.sh                                 | 208 +++++-
 scripts/tests/_parity_classify.py                  |  45 +-
 scripts/tests/ownership_table.tsv                  |  21 +-
 scripts/tests/test-ownership-table.sh              |  32 +-
 scripts/upgrade.sh                                 | 805 +++++++++++++++++++--
 27 files changed, 2664 insertions(+), 167 deletions(-)

--- STAGED STAT ---
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-rF4ixbGU' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-ZL4O1A0G' (errno=Operation not permitted)

  → Inspect all changed and untracked files plus surrounding implementation context
  • Run targeted static checks and tests for affected install/upgrade/release paths
  • Validate candidate defects against repository contracts and produce findings
exec
/bin/zsh -lc "printf '%s\\n' '--- UNTRACKED ---'; find .claude/plans/PLAN-166/architect -type f -maxdepth 2 -print 2>/dev/null; printf '\\n--- DIFF NAME STATUS ---\\n'; git diff --name-status; printf '\\n--- UNTRACKED FILE SIZES ---\\n'; for f in .claude/.framework-version .claude/adr/ADR-155-AMEND-1-delivery-record-ownership.md .claude/governance/npm-trusted-publisher.txt scripts/tests/test-ownership-verdict-unit.sh scripts/tests/test-upgrade-spec-ownership.sh; do [ -e \""'$f" ] && wc -l "$f"; done; find .claude/plans/PLAN-166/architect -type f -maxdepth 2 -exec wc -l {} + 2>/dev/null' in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 117ms:
      36 .claude/governance/npm-trusted-publisher.txt
     107 scripts/tests/test-ownership-verdict-unit.sh
     359 scripts/tests/test-upgrade-spec-ownership.sh
     202 .claude/plans/PLAN-166/architect/round-1/approved.md

exec
/bin/zsh -lc 'git diff -- scripts/_framework_manifest_set.sh scripts/install.sh' in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-x2mpCjWk' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-pJR936Mi' (errno=Operation not permitted)
diff --git a/scripts/_framework_manifest_set.sh b/scripts/_framework_manifest_set.sh
index 937db7f..6a7bc1b 100644
--- a/scripts/_framework_manifest_set.sh
+++ b/scripts/_framework_manifest_set.sh
@@ -32,6 +32,25 @@
 #   * Includes the root PROTOCOL.md plus the .claude/{team.md,frontend-team.md,
 #     skills,hooks,scripts,commands,pitfalls-catalog.yaml,task-chains.yaml}
 #     targets, gated by profile where applicable.
+#   * DELIVERY-RECORD-CONDITIONAL entries (PLAN-166 F3 / ADR-155-AMEND-1):
+#     PROTOCOL.md, SPEC/v1 and .claude/.framework-version are enumerated ONLY
+#     when the caller exports the matching flag as "1":
+#         FMS_DELIVERED_PROTOCOL   root PROTOCOL.md pointer
+#         FMS_DELIVERED_SPEC       SPEC/v1 contract tree
+#         FMS_DELIVERED_MARKER     .claude/.framework-version marker
+#     The flags MUST derive from the REGISTERED DELIVERY (install.sh's
+#     install_one actually wrote the path this run, or the pre-upgrade
+#     baseline manifest already carried the record) — NEVER from the
+#     ceremony alone and NEVER from file presence: a target that already
+#     had the path (install_one EXISTS-skip) stays OUTSIDE framework
+#     ownership, else the baseline hashes an ADOPTER file as
+#     framework-owned, the update-checker trusts a stale value, and
+#     uninstall.sh may delete it. Unset/other values => NOT enumerated:
+#     the deliberate fail direction is UNDER-claiming ownership.
+#   * The root VERSION file is deliberately ABSENT from this enumeration:
+#     install_one is skip-if-exists (an adopter with its own VERSION never
+#     received the framework's), and upgrade.sh never touches it — see
+#     ADR-155-AMEND-1 (the S238/ADR-155 "verified worst case" class, C.5).
 #
 # This file is CANONICAL (added to _CANONICAL_GUARDS in check_canonical_edit.py).
 #
@@ -93,8 +112,34 @@ _framework_path_excluded() {
 # what is currently present).
 _framework_target_entries() {
   {
-    # Root governance pointer (the verified S238 driver target — outside .claude/).
-    printf '%s\n' "PROTOCOL.md"
+    # Root governance pointer (the verified S238 driver target — outside
+    # .claude/). PLAN-166 F3 (ADR-155-AMEND-1): CONDITIONAL on the recorded
+    # delivery. A `--ceremony user` install SKIPS install_protocol_pointer
+    # (install.sh WS4-guard-proto), and a maintainer target that ALREADY had
+    # its own root PROTOCOL.md was never written by the framework —
+    # enumerating it unconditionally records the ADOPTER's file as
+    # framework-owned (r13/r17).
+    if [ "${FMS_DELIVERED_PROTOCOL:-0}" = "1" ]; then
+      printf '%s\n' "PROTOCOL.md"
+    fi
+
+    # SPEC/v1 published contract (PLAN-166 F3): an upgrade surface as of
+    # v1.3.0 — same delivery-record condition (never ceremony alone, never
+    # file presence; r7/r17).
+    if [ "${FMS_DELIVERED_SPEC:-0}" = "1" ]; then
+      printf '%s\n' "SPEC/v1"
+    fi
+
+    # Framework version marker (PLAN-166 F3): a NORMAL tracked-file entry —
+    # present in the source tree, so the FMS_HASH_ROOT baseline rewrite
+    # (below) preserves it with no generated-file special-case — but
+    # ownership still derives from the registered delivery: a target whose
+    # marker pre-existed (install_one EXISTS-skip) stays adopter-owned and
+    # every marker-first reader keyed off this same record falls back to
+    # VERSION (r20).
+    if [ "${FMS_DELIVERED_MARKER:-0}" = "1" ]; then
+      printf '%s\n' ".claude/.framework-version"
+    fi
 
     # Always-installed team rosters + universal catalogs.
     printf '%s\n' ".claude/team.md"
@@ -183,6 +228,95 @@ _framework_manifest_files() {
 # Grammar:
 #   <64hex>  <relpath>          — content hash
 #   LINK  <relpath>  <target>   — link-mode symlink (content == source)
+
+# Does FMS_HASH_ROOT apply to this relpath? UNSET FMS_HASH_ROOT_PATHS means
+# ALL of them — the upgrade posture, where every enumerated file must record
+# what the framework SHIPS. install.sh needs the opposite default for most of
+# the tree: it RENDERS templates (`.claude/team.md`, skills, `{{X}}`
+# placeholders under --project et al), so those legitimately differ from
+# source and their baseline must be the rendered TARGET. A global
+# FMS_HASH_ROOT on an install rerun rewrote every rendered file's hash to the
+# unrendered source, which doctor.sh reads as widespread adopter drift and
+# later upgrades read as customized => the files stop being refreshed (codex
+# W1 round 8, P1). Scoping the override to the ownership-continuity paths
+# keeps the round-5 fix (an EDITED delivered SPEC must not be re-baselined as
+# framework-owned, or uninstall would delete the adopter's fork) without
+# touching the rendered tree. Prefix match: an entry covers the path itself
+# and everything under it.
+_wbm_hash_root_applies() {
+  [ -n "${FMS_HASH_ROOT_PATHS:-}" ] || return 0
+  _hra_rel="$1"
+  _hra_oldIFS="$IFS"
+  IFS='
+'
+  for _hra_p in $FMS_HASH_ROOT_PATHS; do
+    [ -n "$_hra_p" ] || continue
+    case "$_hra_rel" in
+      "$_hra_p"|"$_hra_p"/*)
+        IFS="$_hra_oldIFS"
+        return 0
+        ;;
+    esac
+  done
+  IFS="$_hra_oldIFS"
+  return 1
+}
+
+# May this relpath be serialized as a LINK record? UNSET FMS_LINK_PATHS means
+# ANY live symlink may — correct on the INSTALL path, where the installer
+# itself created every symlink it is about to record. On the UPGRADE rewrite
+# that default is too wide (codex W1 round 10, P2): FMS_MODE=link is inferred
+# from the presence of ANY prior LINK record, and every live symlink then
+# serializes as a delivery record — including an adopter's OWN symlink
+# preserved inside an enumerated directory like `.claude/hooks/`, converting
+# an unowned path into framework-managed content that doctor.sh polices.
+# upgrade.sh passes the exact set of pre-upgrade LINK relpaths instead.
+_wbm_link_allowed() {
+  [ -n "${FMS_LINK_PATHS:-}" ] || return 0
+  _wla_rel="$1"
+  _wla_oldIFS="$IFS"
+  IFS='
+'
+  for _wla_p in $FMS_LINK_PATHS; do
+    [ -n "$_wla_p" ] || continue
+    if [ "$_wla_rel" = "$_wla_p" ]; then
+      IFS="$_wla_oldIFS"
+      return 0
+    fi
+  done
+  IFS="$_wla_oldIFS"
+  return 1
+}
+
+# --- PLAN-167 W2.3: the DECISION reaches the generator ----------------------
+# _ownership_verdict chooses a hash_source per conditional surface; the writer
+# obeys it instead of falling back to a default. Across all 62 rows of the
+# table the default (HASH_TARGET) is never the correct answer, and it is
+# exactly what let three P1 defects re-baseline adopter content as
+# framework-owned (docs §3.4).
+_wbm_declared_hash_source() {
+  case "$1" in
+    SPEC/v1|SPEC/v1/*)          printf '%s' "${FMS_HASH_SOURCE_SPEC:-}" ;;
+    PROTOCOL.md)                printf '%s' "${FMS_HASH_SOURCE_PROTOCOL:-}" ;;
+    .claude/.framework-version) printf '%s' "${FMS_HASH_SOURCE_MARKER:-}" ;;
+    *)                          printf '' ;;
+  esac
+}
+
+_wbm_is_conditional() {
+  case "$1" in
+    SPEC/v1|SPEC/v1/*|PROTOCOL.md|.claude/.framework-version) return 0 ;;
+  esac
+  return 1
+}
+
+# The digest the PRE-run manifest recorded. Empty when unavailable, which the
+# fail-closed branch turns into "do not record" rather than a guess.
+_wbm_prior_digest() {
+  [ -n "${FMS_PRIOR_MANIFEST:-}" ] && [ -f "$FMS_PRIOR_MANIFEST" ] || { printf ''; return 0; }
+  grep -E "^[0-9a-f]{64}  $1\$" "$FMS_PRIOR_MANIFEST" 2>/dev/null | head -1 | cut -d' ' -f1 || printf ''
+}
+
 _write_baseline_manifest() {
   _wbm_manifest="$1"
   if ! command -v _framework_manifest_files >/dev/null 2>&1 \
@@ -215,7 +349,8 @@ _write_baseline_manifest() {
     case "$_wbm_rel" in
       *[$'\n\r\t']*) continue ;;
     esac
-    if [ "${FMS_MODE:-copy}" = "link" ] && [ -L "$_wbm_abs" ]; then
+    if [ "${FMS_MODE:-copy}" = "link" ] && [ -L "$_wbm_abs" ] \
+       && _wbm_link_allowed "$_wbm_rel"; then
       _wbm_target="$( readlink "$_wbm_abs" 2>/dev/null || true )"
       [ -n "$_wbm_target" ] || continue
       case "$_wbm_target" in
@@ -235,6 +370,35 @@ _write_baseline_manifest() {
         else
           _wbm_digest="$( _hash_file "$_wbm_abs" 2>/dev/null || true )"
         fi
+      elif _wbm_is_conditional "$_wbm_rel"; then
+        _wbm_decl="$( _wbm_declared_hash_source "$_wbm_rel" )"
+        case "$_wbm_decl" in
+          HASH_SOURCE)
+            # FMS_SOURCE_ROOT, never FMS_HASH_ROOT: the global override is an
+            # upgrade-only mechanism, and borrowing it here is what dragged
+            # install into the r8-F1 rendered-tree regression.
+            if [ -n "${FMS_SOURCE_ROOT:-}" ] && [ -f "$FMS_SOURCE_ROOT/$_wbm_rel" ]; then
+              _wbm_digest="$( _hash_file "$FMS_SOURCE_ROOT/$_wbm_rel" 2>/dev/null || true )"
+            else
+              continue   # the framework no longer ships it: record nothing
+            fi
+            ;;
+          HASH_PRIOR_RECORD)   _wbm_digest="$( _wbm_prior_digest "$_wbm_rel" )" ;;
+          HASH_CANONICAL_POINTER) _wbm_digest="${FMS_PROTOCOL_HASH:-}" ;;
+          HASH_TARGET)         _wbm_digest="$( _hash_file "$_wbm_abs" 2>/dev/null || true )" ;;
+          HASH_NONE)           continue ;;
+          *)
+            # FAIL-CLOSED, scoped to the three conditional surfaces (Owner
+            # ratified 2026-08-07). Under-claiming is recoverable; over-claiming
+            # is the delete-the-adopter's-file class.
+            echo "    NOTE: $_wbm_rel delivered but declared no hash_source —" >&2
+            echo "          NOT recorded (fail-closed; ownership under-claimed)" >&2
+            continue
+            ;;
+        esac
+        case "$_wbm_digest" in
+          "" ) continue ;;
+        esac
       else
         # Hash the FRAMEWORK version. When FMS_HASH_ROOT is set (upgrade) and the
         # path is ABSENT there, the framework no longer ships it — OMIT it from
@@ -242,7 +406,7 @@ _write_baseline_manifest() {
         # mark it FRAMEWORK-CHANGED if the framework later reintroduces the
         # path). Codex R2 P1.
         _wbm_hash_path="$_wbm_abs"
-        if [ -n "${FMS_HASH_ROOT:-}" ]; then
+        if [ -n "${FMS_HASH_ROOT:-}" ] && _wbm_hash_root_applies "$_wbm_rel"; then
           if [ -f "$_wbm_hash_root/$_wbm_rel" ]; then
             _wbm_hash_path="$_wbm_hash_root/$_wbm_rel"
           else
@@ -268,3 +432,166 @@ _write_baseline_manifest() {
   fi
   return 0
 }
+
+# =============================================================================
+# PLAN-167 — _ownership_verdict: THE ownership decision.
+#
+# install.sh and upgrade.sh stop deciding and start executing. Every defect in
+# the 35-finding S296 review series was a cell of this space whose answer was
+# decided branch-locally, so two branches could disagree about the same
+# question and nothing detected it.
+#
+#   $1 surface        spec | protocol | marker
+#   $2 prior_record   none | hash | link_match | link_retargeted
+#   $3 live_type      absent | dir | dir_empty | regular | symlink | special
+#                     | ancestor_symlink
+#   $4 live_content   pristine | legacy_pristine | legacy_pristine_partial
+#                     | edited | -
+#   $5 source_has     yes | no
+#   $6 mode           copy | link
+#   $7 ceremony       user | maintainer
+#   $8 operation      install_fresh | install_rerun | upgrade
+#   $9 skip_requested none | self | descendant
+#
+#   stdout: "<VERDICT> <HASH_SOURCE>", rc 0
+#   rc 1, no output: a combination the legality rules forbid.
+#
+# PURE: no filesystem, no globals, no environment. Callers observe the nine
+# dimensions and pass them in. That purity is what lets the same table drive a
+# millisecond unit oracle as well as the ~25-minute end-to-end suite; S296 had
+# only the slow instrument, at one cell per ~40-minute round.
+#
+# ABORT_SURFACE is deliberately NOT produced here (round-1 consensus C2). A
+# failed backup is not a property of these nine dimensions — it is the CALLER
+# failing to carry out a verdict it was handed. And per INV-3 that failure
+# NEVER advances the record: recording a delivery that did not happen is the
+# over-claiming direction ADR-155-AMEND-1 §3 forbids.
+#
+# Contract: docs/ownership-decision-table.md · Truth: scripts/tests/ownership_table.tsv
+# =============================================================================
+_ownership_verdict() {
+  _ov_surface="$1"; _ov_prior="$2";  _ov_ltype="$3"; _ov_lcontent="$4"
+  _ov_shas="$5";    _ov_mode="$6";   _ov_cer="$7";   _ov_op="$8"; _ov_skip="$9"
+
+  # Do not touch the surface; decide the RECORD. Ownership continuity and the
+  # digit it carries are separate decisions, and moving one without the other
+  # produced four distinct defects — so they are resolved together, once.
+  _ov_carry() {
+    case "$_ov_prior" in
+      link_match)      printf 'PRESERVE_OWNED LINK_RECORD';  return 0 ;;
+      link_retargeted) printf 'PRESERVE_UNOWNED HASH_NONE'; return 0 ;;
+      none)            printf 'PRESERVE_UNOWNED HASH_NONE';  return 0 ;;
+    esac
+    # prior_record=hash. HASH_TARGET is never an option: it re-baselines the
+    # bytes now on disk, which is how a later upgrade comes to overwrite an
+    # adopter edit and uninstall comes to delete it.
+    if [ "$_ov_surface" = "protocol" ] \
+       || [ "$_ov_shas" = "no" ] \
+       || [ "$_ov_ltype" = "dir_empty" ]; then
+      printf 'PRESERVE_OWNED HASH_PRIOR_RECORD'   # no source bytes to hash
+    else
+      printf 'PRESERVE_OWNED HASH_SOURCE'
+    fi
+  }
+
+  # The framework must not claim this path. Whether a record existed changes
+  # only which NAME the observation takes (OQ-9 — the evidence that these are
+  # one outcome, not two).
+  # OQ-9 (ratificada pelo Owner 2026-08-07): PRESERVE_UNOWNED é o único nome.
+  # OMIT_RECORD dizia a mesma coisa — sem registro no disco — e diferia apenas
+  # por já existir registro antes, que é a coluna prior_record. Um membro de
+  # enum redundante é onde dois ramos discordam sobre qual deles se aplica.
+  _ov_unowned() { printf 'PRESERVE_UNOWNED HASH_NONE'; }
+
+  # --- Stage A: gates that refuse to act, in priority order ------------------
+
+  # A1. The source cannot deliver this surface.
+  if [ "$_ov_shas" = "no" ]; then
+    case "$_ov_surface" in
+      marker)   printf 'PRESERVE_UNOWNED HASH_NONE'; return 0 ;;  # --pin: readers fall back to VERSION
+      protocol) return 1 ;;                                  # R-03: generated, never absent
+      *)        _ov_carry; return 0 ;;
+    esac
+  fi
+
+  # A2. A user ceremony never receives the root surfaces (WS4).
+  if [ "$_ov_cer" = "user" ] && [ "$_ov_surface" != "marker" ]; then
+    if [ "$_ov_op" = "install_fresh" ]; then printf 'PRESERVE_UNOWNED HASH_NONE'
+    else _ov_carry; fi
+    return 0
+  fi
+
+  # A3. Reachable only by writing THROUGH a symlink, out of the target tree.
+  # Always unowned: the relpath sanitizer already dropped any record whose path
+  # crosses a symlink, so there is no record left to carry (docs §5.8).
+  if [ "$_ov_ltype" = "ancestor_symlink" ]; then _ov_unowned; return 0; fi
+
+  # A4. A leaf symlink is healthy ONLY as the recorded link-mode delivery.
+  # The absence of a LINK row is not a match — it is the absence of evidence.
+  if [ "$_ov_ltype" = "symlink" ]; then
+    if [ "$_ov_prior" = "link_match" ]; then printf 'PRESERVE_OWNED LINK_RECORD'
+    else _ov_unowned; fi
+    return 0
+  fi
+
+  # A5. Anything that exists but is not shaped like this surface is
+  # adopter-owned: never write into it, never through it, never block on it.
+  case "$_ov_surface" in
+    spec)
+      case "$_ov_ltype" in special) _ov_unowned; return 0 ;; esac ;;
+    protocol|marker)
+      case "$_ov_ltype" in dir|dir_empty|special) _ov_unowned; return 0 ;; esac ;;
+  esac
+
+  # A6. An explicit skip is honoured as a UNIT — a partial contract refresh is
+  # incoherent, so a descendant skip preserves the whole tree.
+  if [ "$_ov_skip" != "none" ]; then _ov_carry; return 0; fi
+
+  # --- Stage B: ownership resolution ----------------------------------------
+  _ov_owned=""
+  if [ "$_ov_prior" = "hash" ] || [ "$_ov_prior" = "link_match" ]; then
+    _ov_owned=1
+  elif [ "$_ov_ltype" = "absent" ]; then
+    _ov_owned=1                                   # new delivery
+  elif [ "$_ov_lcontent" = "pristine" ] || [ "$_ov_lcontent" = "legacy_pristine" ]; then
+    _ov_owned=1                                   # current-source takeover / legacy migration
+  fi
+  # legacy_pristine_partial is deliberately NOT owned: every regular file may
+  # match a shipped release, but a tree carrying an entry the fingerprint
+  # cannot inventory has not been inventoried, and a partial inventory must
+  # never certify a wholesale replace (ADR-155-AMEND-1 §4).
+
+  if [ -z "$_ov_owned" ]; then _ov_unowned; return 0; fi
+
+  # --- Stage C: execution ---------------------------------------------------
+  if [ "$_ov_ltype" = "absent" ]; then
+    case "$_ov_surface" in
+      protocol) printf 'DELIVER HASH_CANONICAL_POINTER' ;;
+      *)        printf 'DELIVER HASH_SOURCE' ;;
+    esac
+    return 0
+  fi
+
+  # An install rerun does not re-deliver an existing surface; it decides the
+  # record. Only the upgrade's forced route replaces content.
+  if [ "$_ov_op" != "upgrade" ]; then _ov_carry; return 0; fi
+
+  # The pointer is the ONE surface where an adopter edit is PRESERVED rather
+  # than treated as a fork. SPEC/v1 is deliberately the opposite: it is the
+  # published compliance CONTRACT, so an edit is a fork and the forced route
+  # replaces it (ADR-155-AMEND-1 §4). The root PROTOCOL.md is adopter-editable
+  # prose, and overwriting a customised one is the verified S238 data loss that
+  # ADR-155 decision (iii) exists to close.
+  #
+  # The recorded digest stays CANONICAL either way: recording the customised
+  # bytes would make the NEXT upgrade read H_dst==H_base and clobber them.
+  if [ "$_ov_surface" = "protocol" ] && [ "$_ov_lcontent" = "edited" ]; then
+    printf 'PRESERVE_OWNED HASH_CANONICAL_POINTER'
+    return 0
+  fi
+
+  case "$_ov_surface" in
+    protocol) printf 'REFRESH HASH_CANONICAL_POINTER' ;;
+    *)        printf 'REFRESH HASH_SOURCE' ;;
+  esac
+}
diff --git a/scripts/install.sh b/scripts/install.sh
index 0535b51..ad2a422 100755
--- a/scripts/install.sh
+++ b/scripts/install.sh
@@ -777,6 +777,21 @@ _state_record_op() {
   return 0
 }
 
+# ---------------------------------------------------------------------
+# PLAN-166 F3 (ADR-155-AMEND-1) — DELIVERY RECORD for the conditional
+# framework-ownership surfaces. Each flag flips to 1 ONLY when THIS run
+# actually wrote the path (install_one COPIED/LINKED, or the pointer
+# heredoc ran) — an EXISTS-skip is NOT a delivery (r17): the pre-existing
+# file is the ADOPTER's, and recording it as framework-owned would let the
+# baseline hash it, doctor call it drifted, and uninstall delete it.
+# write_install_manifest exports these as FMS_DELIVERED_* so the shared
+# enumeration (_framework_manifest_set.sh) only records what the framework
+# de facto delivered.
+# ---------------------------------------------------------------------
+_DELIVERED_SPEC=0
+_DELIVERED_PROTOCOL=0
+_DELIVERED_MARKER=0
+
 # PLAN-155 Wave 5 — the codex harness helper records its operations through
 # this recorder, mapped onto the install-state journal (overrides the helper's
 # no-op default so codex emissions land in .claude/.install-state.json).
@@ -851,6 +866,11 @@ install_one() {
   local src="$SOURCE_DIR/$rel_path"
   local dst="$TARGET/$rel_path"
 
+  # PLAN-166 F3 (ADR-155-AMEND-1): delivery signal for the caller — 1 only
+  # when THIS call actually wrote the destination (COPIED/LINKED). An
+  # EXISTS-skip, a missing source and a dry-run all leave it 0.
+  INSTALL_ONE_WROTE=0
+
   if [[ ! -e "$src" ]]; then
     echo "    SKIP (source missing): $rel_path"
     return
@@ -877,6 +897,7 @@ install_one() {
 
   if [[ "$MODE" == "link" ]]; then
     ln -s "$src" "$dst"
+    INSTALL_ONE_WROTE=1
     echo "    LINKED: $rel_path"
   else
     if [[ -d "$src" ]]; then
@@ -884,6 +905,7 @@ install_one() {
     else
       cp "$src" "$dst"
     fi
+    INSTALL_ONE_WROTE=1
     echo "    COPIED: $rel_path"
   fi
 }
@@ -1305,6 +1327,14 @@ install_spec_v1() {
   echo "==> Installing SPEC v1 schemas (~$(ls "$SOURCE_DIR"/SPEC/v1/*.md 2>/dev/null | wc -l | tr -d ' ') files)"
   _state_record_op "install_spec_v1" "SPEC/v1"
   install_one "SPEC/v1"
+  # PLAN-166 F3 (ADR-155-AMEND-1): the op line above records the ATTEMPT;
+  # framework ownership requires the REGISTERED DELIVERY — install_one may
+  # have EXISTS-skipped a pre-existing adopter SPEC/v1 (r17), which must
+  # NOT be inventoried as framework-owned.
+  if [[ "${INSTALL_ONE_WROTE:-0}" -eq 1 ]]; then
+    _DELIVERED_SPEC=1
+    _state_record_op "delivered_spec_v1" "SPEC/v1"
+  fi
 }
 
 if [[ "$CEREMONY" != "user" ]]; then install_spec_v1; fi  # WS4-guard-spec
@@ -1324,6 +1354,35 @@ install_version() {
 
 if [[ "$CEREMONY" != "user" ]]; then install_version; fi  # WS4-guard-version
 
+# ---- 5c-bis-3 framework version marker (PLAN-166 F3 / ADR-155-AMEND-1) ----
+# .claude/.framework-version is a TRACKED file of the framework repo (one
+# line, byte-identical to VERSION — the bump writes it as its 12th site and
+# verify-counts.sh cross-checks it every release). It is the forensic anchor
+# that stays true POST-UPGRADE: upgrade.sh deliberately never touches the
+# root VERSION (S238/ADR-155 class), so on an upgraded adopter only this
+# marker reports the installed framework version. It lives inside .claude/,
+# so it is delivered in BOTH ceremonies (the WS4 user-ceremony guard only
+# forbids root files). The write is EXPLICIT — the manifest enumeration
+# never delivers anything, it only records (r7) — and skip-if-exists: a
+# pre-existing marker stays adopter-owned (no delivery record), and every
+# marker-first reader keyed off that record falls back to VERSION (r20).
+install_framework_marker() {
+  if [[ ! -f "$SOURCE_DIR/.claude/.framework-version" ]]; then
+    echo "    SKIP: .claude/.framework-version absent in source (pre-v1.3.0 checkout)"
+    return 0
+  fi
+  echo ""
+  echo "==> Installing framework version marker (.claude/.framework-version — $(tr -d '[:space:]' < "$SOURCE_DIR/.claude/.framework-version"))"
+  _state_record_op "install_framework_marker" ".claude/.framework-version"
+  install_one ".claude/.framework-version"
+  if [[ "${INSTALL_ONE_WROTE:-0}" -eq 1 ]]; then
+    _DELIVERED_MARKER=1
+    _state_record_op "delivered_framework_marker" ".claude/.framework-version"
+  fi
+}
+
+install_framework_marker  # both ceremonies: inside .claude/ (WS4-safe)
+
 # ---- 5c.bis Reference personas (PLAN-004 Phase 10) ----
 
 install_reference_personas() {
@@ -1871,6 +1930,12 @@ $pointer_body
 EOF
   echo "    CREATED: PROTOCOL.md (pointer)"
   _state_record_op "install_protocol_pointer" "PROTOCOL.md"
+  # PLAN-166 F3 (ADR-155-AMEND-1): registered delivery — this line is only
+  # reached when the heredoc actually wrote the pointer (the pre-existing
+  # early-return above never gets here, so an adopter's own root
+  # PROTOCOL.md is never inventoried as framework-owned; r13/r17).
+  _DELIVERED_PROTOCOL=1
+  _state_record_op "delivered_protocol_pointer" "PROTOCOL.md"
 }
 
 if [[ "$CEREMONY" != "user" ]]; then install_protocol_pointer; fi  # WS4-guard-proto
@@ -2228,8 +2293,149 @@ write_install_manifest() {
   export FMS_ROOT="$TARGET"
   export FMS_PROFILE_PARTS="${PROFILE_PARTS[*]}"
   export FMS_MODE="$MODE"
+  # PLAN-166 F3 (ADR-155-AMEND-1): conditional ownership from the DELIVERY
+  # RECORD — never the ceremony alone, never file presence. A path
+  # install_one EXISTS-skipped stays out of the baseline, so doctor, the
+  # update-checker and uninstall never treat an adopter file as
+  # framework-owned (r7/r13/r17).
+  #
+  # Ownership CONTINUITY on reruns (codex W1-ceremony round, P1): a rerun
+  # over an already-installed target EXISTS-skips all three paths, so the
+  # THIS-RUN flags are 0 — but the manifest rewrite below REPLACES the old
+  # manifest. Without consulting the PRIOR manifest's records, a rerun
+  # would silently drop framework ownership of SPEC/PROTOCOL/marker (and a
+  # v1.3 SPEC would later misclassify as ADOPTER-FORK — it is absent from
+  # the legacy pristine fingerprints). Preserve a valid prior record: the
+  # regexes mirror upgrade.sh _baseline_has_*_record byte-for-byte
+  # (family-swept; `(/|  |$)` covers the --mode link single-LINK-line form).
+  # A prior LINK record carries ownership forward only while the live symlink
+  # still points where it was RECORDED (codex W1 round 10, P2). On a --link
+  # reinstall over a RETARGETED managed symlink, install_one EXISTS-skips the
+  # path and the continuity check used to accept the record blindly; the
+  # rewrite then serialized the redirected target as the new delivery record
+  # and every later upgrade accepted the foreign tree as healthy. Mirrors the
+  # readlink-vs-record checks upgrade.sh already applies on its refresh
+  # routes. Returns 0 (carry on) when there is no LINK record to compare.
+  _prior_link_target_matches() {   # $1 = manifest, $2 = relpath
+    local _plt_line _plt_rec="" _plt_live
+    while IFS= read -r _plt_line || [[ -n "$_plt_line" ]]; do
+      case "$_plt_line" in
+        "LINK  $2  "*) _plt_rec="${_plt_line#LINK  $2  }"; break ;;
+      esac
+    done < "$1"
+    [[ -n "$_plt_rec" ]] || return 0
+    _plt_live="$( readlink "$TARGET/$2" 2>/dev/null || true )"
+    [[ "$_plt_rec" == "$_plt_live" ]]
+  }
+  if [[ "${_DELIVERED_SPEC:-0}" != "1" ]] && [[ -f "$manifest" ]] \
+     && grep -Eq '^([0-9a-f]{64}|LINK)  SPEC/v1(/|  |$)' "$manifest" 2>/dev/null \
+     && _prior_link_target_matches "$manifest" "SPEC/v1"; then
+    _DELIVERED_SPEC=1
+    _CONTINUITY_FIRED=1
+    _CONTINUITY_PATHS="${_CONTINUITY_PATHS:-}
+SPEC/v1"
+    echo "    ownership continuity: SPEC/v1 delivery record preserved from prior manifest"
+  fi
+  if [[ "${_DELIVERED_PROTOCOL:-0}" != "1" ]] && [[ -f "$manifest" ]] \
+     && grep -Eq '^([0-9a-f]{64}|LINK)  PROTOCOL\.md(  |$)' "$manifest" 2>/dev/null \
+     && _prior_link_target_matches "$manifest" "PROTOCOL.md"; then
+    # FMS_HASH_ROOT does NOT reach PROTOCOL.md: _write_baseline_manifest
+    # special-cases the generated pointer and hashes the TARGET unless
+    # FMS_PROTOCOL_HASH is supplied — which install never set. So a rerun over
+    # a CUSTOMIZED delivered pointer re-baselined the adopter's own bytes as
+    # framework-owned; the next upgrade would then overwrite them and
+    # uninstall could DELETE them (codex W1 round 9, P1). Carry the PRIOR
+    # recorded digest. A LINK record needs none (the rewrite's link branch
+    # fires before the PROTOCOL special case); with neither, DROP the
+    # ownership claim rather than record a knowingly wrong baseline.
+    _PRIOR_PROTOCOL_HASH="$( grep -E '^[0-9a-f]{64}  PROTOCOL\.md$' "$manifest" 2>/dev/null | head -1 | cut -d' ' -f1 || true )"
+    if [[ -n "$_PRIOR_PROTOCOL_HASH" ]] \
+       || grep -Eq '^LINK  PROTOCOL\.md(  |$)' "$manifest" 2>/dev/null; then
+      _DELIVERED_PROTOCOL=1
+      _CONTINUITY_FIRED=1
+      _CONTINUITY_PATHS="${_CONTINUITY_PATHS:-}
+PROTOCOL.md"
+      echo "    ownership continuity: PROTOCOL.md delivery record preserved from prior manifest"
+    else
+      echo "    NOTE: PROTOCOL.md record present but its digest is unrecoverable —" >&2
+      echo "          ownership NOT claimed (the pointer stays adopter-owned)" >&2
+    fi
+  fi
+  if [[ "${_DELIVERED_MARKER:-0}" != "1" ]] && [[ -f "$manifest" ]] \
+     && grep -Eq '^([0-9a-f]{64}|LINK)  \.claude/\.framework-version(  |$)' "$manifest" 2>/dev/null \
+     && _prior_link_target_matches "$manifest" ".claude/.framework-version"; then
+    _DELIVERED_MARKER=1
+    _CONTINUITY_FIRED=1
+    _CONTINUITY_PATHS="${_CONTINUITY_PATHS:-}
+.claude/.framework-version"
+    echo "    ownership continuity: .framework-version delivery record preserved from prior manifest"
+  fi
+  # For the continuity-preserved paths ONLY, hash the FRAMEWORK's pristine
+  # copies instead of the (possibly edited) target's (codex W1 round 5, P1):
+  # install normally hashes FMS_ROOT=$TARGET — on a rerun over an EDITED
+  # delivered SPEC that would re-baseline the fork's bytes as framework-owned,
+  # and a later uninstall would happily DELETE the user's modified tree (its
+  # hash matches the manifest). Same C.5 idempotency posture upgrade.sh uses.
+  #
+  # SCOPED, not global (codex W1 round 8, P1): install RENDERS templates
+  # (`.claude/team.md`, skills, `{{X}}` placeholders under --project et al),
+  # so a global FMS_HASH_ROOT rewrote every rendered file's baseline to the
+  # UNRENDERED source — doctor.sh then reports repo-wide adopter drift and
+  # later upgrades classify those files as customized and stop refreshing
+  # them. PLAN-167 W2.3 replaced that confinement with an EXPLICIT per-surface
+  # hash_source: the decision says which paths take the framework's bytes,
+  # so no global override is set here at all.
+  if [[ "${_CONTINUITY_FIRED:-0}" = "1" ]]; then
+    : # per-surface hash_source below replaces the global override
+    case "$_CONTINUITY_PATHS" in
+      *".claude/.framework-version"*) export FMS_HASH_SOURCE_MARKER="HASH_SOURCE" ;;
+    esac
+    case "$_CONTINUITY_PATHS" in
+      # The generated pointer has no source bytes; carry what was recorded.
+      *"PROTOCOL.md"*)               export FMS_HASH_SOURCE_PROTOCOL="HASH_PRIOR_RECORD" ;;
+    esac
+    echo "    ownership continuity: manifest hashes the preserved paths from the framework source (edited target content stays adopter-owned; rendered files keep their target hash)"
+  fi
+  # Declare on EVERY delivery path, not only continuity. A fresh install
+  # genuinely delivers these surfaces, and the previous attempt at this wave
+  # regressed 24 cells precisely because it left fresh installs undeclared.
+  #
+  # Fresh delivery: the target IS the bytes just written, so HASH_TARGET is
+  # both correct and observationally identical to HASH_SOURCE.
+  # Continuity: the target may be an EDITED fork, so the record must come from
+  # the framework's copy (spec/marker) or the prior record (the generated
+  # pointer, which has no source file).
+  export FMS_SOURCE_ROOT="$SOURCE_DIR"
+  export FMS_PRIOR_MANIFEST="$manifest"
+  if [[ "${_DELIVERED_SPEC:-0}" = "1" ]]; then
+    case "${_CONTINUITY_PATHS:-}" in
+      *"SPEC/v1"*) export FMS_HASH_SOURCE_SPEC="HASH_SOURCE" ;;
+      *)           export FMS_HASH_SOURCE_SPEC="HASH_TARGET" ;;
+    esac
+  fi
+  if [[ "${_DELIVERED_MARKER:-0}" = "1" ]]; then
+    case "${_CONTINUITY_PATHS:-}" in
+      *".claude/.framework-version"*) export FMS_HASH_SOURCE_MARKER="HASH_SOURCE" ;;
+      *)                              export FMS_HASH_SOURCE_MARKER="HASH_TARGET" ;;
+    esac
+  fi
+  if [[ "${_DELIVERED_PROTOCOL:-0}" = "1" ]]; then
+    case "${_CONTINUITY_PATHS:-}" in
+      *"PROTOCOL.md"*) export FMS_HASH_SOURCE_PROTOCOL="HASH_PRIOR_RECORD" ;;
+      *)               export FMS_HASH_SOURCE_PROTOCOL="HASH_TARGET" ;;
+    esac
+  fi
+  export FMS_DELIVERED_SPEC="${_DELIVERED_SPEC:-0}"
+  export FMS_DELIVERED_PROTOCOL="${_DELIVERED_PROTOCOL:-0}"
+  export FMS_DELIVERED_MARKER="${_DELIVERED_MARKER:-0}"
+  # Empty on a fresh install (target IS the freshly written pointer, hashing it
+  # is correct); set only by the continuity path above.
+  export FMS_PROTOCOL_HASH="${_PRIOR_PROTOCOL_HASH:-}"
   _write_baseline_manifest "$manifest"
-  unset FMS_ROOT FMS_PROFILE_PARTS FMS_MODE
+  unset FMS_ROOT FMS_PROFILE_PARTS FMS_MODE FMS_HASH_ROOT FMS_PROTOCOL_HASH \
+        FMS_PRIOR_MANIFEST FMS_HASH_SOURCE_SPEC FMS_HASH_SOURCE_PROTOCOL \
+        FMS_HASH_SOURCE_MARKER
+  unset FMS_DELIVERED_SPEC FMS_DELIVERED_PROTOCOL FMS_DELIVERED_MARKER
   return 0
 }
 

exec
/bin/zsh -lc 'git diff -- scripts/upgrade.sh' in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-5E7cHZ7R' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-AYhR7yW6' (errno=Operation not permitted)
diff --git a/scripts/upgrade.sh b/scripts/upgrade.sh
index 0ec7c4b..3bc6e05 100755
--- a/scripts/upgrade.sh
+++ b/scripts/upgrade.sh
@@ -339,9 +339,13 @@ Usage:
 
 What it does:
   Refreshes the framework-derived content (team.md, skills/, hooks/,
-  scripts/, commands/, pitfalls-catalog.yaml, task-chains.yaml) in an
-  existing adopter install. User-customized files (CLAUDE.md, MEMORY.md,
-  .claude/agent-metrics.md) are NOT touched. NOTE: .claude/settings.json IS
+  scripts/, commands/, pitfalls-catalog.yaml, task-chains.yaml, the
+  SPEC/v1 contract (forced route, skipped on --ceremony user installs)
+  and the .claude/.framework-version marker) in an existing adopter
+  install. User-customized files (CLAUDE.md, MEMORY.md,
+  .claude/agent-metrics.md) are NOT touched, and the root VERSION file
+  is NEVER touched (install-time snapshot — ADR-155-AMEND-1; read
+  .claude/.framework-version for the installed framework version). NOTE: .claude/settings.json IS
   updated in place by the default-on baseline migration (the model/permission
   leaf keys: model, availableModels, fallbackModel, permissions.defaultMode)
   and the idempotent settings-merge (new lifecycle-hook registrations) —
@@ -724,6 +728,49 @@ if [[ "$REPLAY" -eq 1 ]]; then
   fi
 fi
 
+# ===========================================================================
+# PLAN-166 F3 (ADR-155-AMEND-1) — resolve the RECORDED install ceremony with
+# a reader of its OWN, INDEPENDENT of the replay path: --no-replay sets
+# REPLAY=0 and the replay block above (incl. _read_install_state_request) is
+# skipped entirely, so if the ceremony rode the replay, the documented
+# `upgrade.sh <target> --no-replay` would treat a `--ceremony user` install
+# as maintainer and force SPEC/protocol into the adopter's root (r9). This
+# reader ALWAYS runs. Fail-open: state absent/unreadable/invalid (ALL
+# pre-Wave-B installs) => "maintainer" — the pre-existing behavior; the
+# consequence is named in INSTALL.md §Upgrade flow. Same trust class as the
+# replay reader: target-side, UNSIGNED, advisory; the value is validated
+# against the closed enum {maintainer,user} and never eval-ed.
+# ===========================================================================
+_read_install_state_ceremony() {
+  command -v python3 >/dev/null 2>&1 || return 3
+  [ -f "$_INSTALL_STATE_FILE" ] && [ -r "$_INSTALL_STATE_FILE" ] || return 3
+  PYTHONNOUSERSITE=1 python3 -I -c '
+import json, sys
+try:
+    with open(sys.argv[1], "r", encoding="utf-8") as f:
+        d = json.load(f)
+except (OSError, ValueError):
+    sys.exit(3)
+if not isinstance(d, dict) or d.get("schema_version") != 1:
+    sys.exit(3)
+req = d.get("request")
+if not isinstance(req, dict):
+    sys.exit(3)
+cer = req.get("ceremony", "")
+if cer not in ("maintainer", "user"):
+    sys.exit(3)
+sys.stdout.write(cer + "\n")
+' "$_INSTALL_STATE_FILE" 2>/dev/null
+}
+
+CEREMONY_EFFECTIVE="maintainer"
+_CEREMONY_SOURCE="default (no readable install-state — pre-Wave-B fail-open)"
+_cer_line=""
+if _cer_line="$(_read_install_state_ceremony)" && [[ -n "$_cer_line" ]]; then
+  CEREMONY_EFFECTIVE="$_cer_line"
+  _CEREMONY_SOURCE="recorded install request (.claude/.install-state.json)"
+fi
+
 TIMESTAMP="$( date +%Y%m%d-%H%M%S )"
 BAK_DIR="$TARGET/.claude.bak/$TIMESTAMP"
 
@@ -735,6 +782,7 @@ echo "    Target:  $TARGET"
 echo "    Backup:  $BAK_DIR"
 echo "    Profile: $PROFILE"
 echo "    Stack:   $STACK"
+echo "    Ceremony: $CEREMONY_EFFECTIVE — $_CEREMONY_SOURCE"  # PLAN-166 F3
 if [[ "$_REPLAY_SOURCE" == "replay" ]]; then
   echo "    Request: replayed from .claude/.install-state.json (PLAN-153 B2)"
 fi
@@ -794,8 +842,23 @@ _BASELINE_INVALID=""         # newline-list of relpaths seen >1x: AMBIGUOUS prov
 # / 1 (accept). Checks: absolute, `..` segment, control chars, and a symlinked
 # component anywhere along the path under $TARGET (lstat per component, never
 # follow). Duplicate relpaths are rejected by the caller via _BASELINE_DUP_GUARD.
+#
+# $2 = record KIND, mirroring doctor.sh `_relpath_unsafe` (family sweep):
+# "link" tolerates a symlinked LEAF, anything else (default "file") does not.
+# A `LINK  <relpath>  <target>` record describes a --mode link delivery whose
+# leaf IS a symlink by construction, so rejecting it here silently dropped the
+# record from the sanitized manifest: _baseline_has_spec_record and both
+# readlink-vs-recorded-target checks could then NEVER match, and every
+# link-mode upgrade lost framework ownership of SPEC/v1 and the marker, with
+# marker-first readers falling back to the stale root VERSION (codex W1
+# round 6, P2). The leaf is never FOLLOWED here — validation stays at the
+# consumers, which compare `readlink` against the recorded target. Hash
+# records keep the strict leaf check: a managed regular file swapped for a
+# symlink must not retain its record (_hash_file WOULD follow it). Symlinked
+# PARENT components remain a genuine traversal hazard for both kinds.
 _baseline_relpath_unsafe() {
   _bru_rel="$1"
+  _bru_kind="${2:-file}"
   case "$_bru_rel" in
     /*) return 0 ;;                       # absolute
     *..*) return 0 ;;                      # parent traversal (covers ../ and /..)
@@ -804,16 +867,30 @@ _baseline_relpath_unsafe() {
   case "$_bru_rel" in
     ""|*[$'\n\r\t']*) return 0 ;;
   esac
+  # Count the significant components first, so the leaf can be identified by
+  # INDEX — reconstructing "$TARGET/$_bru_rel" for a leaf test would differ
+  # from the walk on `./` and trailing-slash forms.
+  _bru_n=0
+  _bru_oldIFS="$IFS"
+  IFS='/'
+  for _bru_comp in $_bru_rel; do
+    [ -n "$_bru_comp" ] || continue
+    [ "$_bru_comp" = "." ] && continue
+    _bru_n=$(( _bru_n + 1 ))
+  done
   # Symlinked-component check: walk each path component under $TARGET; if any
   # EXISTING component is a symlink, reject (do not follow it).
   _bru_cur="$TARGET"
-  _bru_oldIFS="$IFS"
-  IFS='/'
+  _bru_i=0
   for _bru_comp in $_bru_rel; do
     [ -n "$_bru_comp" ] || continue
     [ "$_bru_comp" = "." ] && continue
+    _bru_i=$(( _bru_i + 1 ))
     _bru_cur="$_bru_cur/$_bru_comp"
     if [ -L "$_bru_cur" ]; then
+      if [ "$_bru_kind" = "link" ] && [ "$_bru_i" -eq "$_bru_n" ]; then
+        continue                          # the LINK record's own leaf
+      fi
       IFS="$_bru_oldIFS"
       return 0
     fi
@@ -871,7 +948,9 @@ _load_baseline_manifest() {
             ;;
           *) continue ;;   # malformed LINK (no target) — drop
         esac
-        if _baseline_relpath_unsafe "$rel"; then continue; fi
+        # KIND=link: the leaf of a LINK record IS a symlink by construction
+        # (codex W1 round 6, P2). Symlinked PARENTS still reject.
+        if _baseline_relpath_unsafe "$rel" link; then continue; fi
         # Duplicate relpath? Ambiguous provenance — invalidate the relpath
         # ENTIRELY (not first-wins): the lookup will refuse it -> fallback.
         case "$_BASELINE_DUP_GUARD" in
@@ -1482,72 +1561,575 @@ To pull updates:
       ;;
   esac
 
-  # PLAN-138 C.7 fix (Codex R2 P0): compute the CANONICAL pointer hash — the
-  # hash of exactly what the framework WOULD write below (heredoc body) — and
-  # export it so the post-upgrade manifest rewrite records THAT as the
-  # PROTOCOL.md baseline, never the current target file. Without this, a
-  # preserved adopter-customized PROTOCOL.md would be re-recorded as its own
-  # baseline and the NEXT upgrade would read H_dst==H_base and clobber it.
-  # Computed on ALL paths (preserve + refresh) so it is set whenever the C.7
-  # rewrite runs. printf reproduces the heredoc byte-for-byte.
+  # The CANONICAL digest: the hash of exactly what the framework WOULD write.
+  # Computed on every path, because the baseline rewrite must record it even
+  # when the pointer is preserved — recording the customised bytes instead
+  # would make the NEXT upgrade read H_dst == H_base and clobber them (C.5).
   _REFRESH_PROTOCOL_CANON_HASH=""
   if command -v _hash_stdin >/dev/null 2>&1; then
     _REFRESH_PROTOCOL_CANON_HASH="$( printf '# Protocol reference\n\n%s\n' "$body" | _hash_stdin 2>/dev/null || true )"
   fi
 
-  if [[ "$DRY_RUN" -eq 1 ]]; then
-    echo "    (dry-run) would REFRESH: PROTOCOL.md pointer"
-    return 0
+  # ---- OBSERVE -------------------------------------------------------------
+  local _lt _pr _lc
+  _lt="$( _ov_obs_live_type "$pointer" )"
+  _pr="$( _ov_obs_prior_record "PROTOCOL.md" )"
+  if [ "$_lt" != "regular" ]; then
+    _lc="-"
+  elif [ -n "$_REFRESH_PROTOCOL_CANON_HASH" ] \
+       && [ "$( _hash_file "$pointer" 2>/dev/null || true )" = "$_REFRESH_PROTOCOL_CANON_HASH" ]; then
+    _lc="pristine"
+  else
+    _lc="edited"
   fi
 
-  _up_record_op "refresh_protocol_pointer" "PROTOCOL.md"
-
-  # PLAN-138 Wave C (ADR-155) C.6 — close the verified S238 driver.
-  #
-  # (a) ALWAYS back up an existing root PROTOCOL.md to $BAK_DIR/PROTOCOL.md
-  #     BEFORE the `cat >` overwrite. The legacy code had NO backup here, so an
-  #     adopter who turned the pointer into a real customized protocol (the
-  #     S238 acme case) lost it irrecoverably. This backup applies EVEN when
-  #     no baseline manifest exists — making the loss recoverable on a first
-  #     upgrade (Codex R1 P0 first-upgrade safety).
-  if [[ -f "$pointer" ]]; then
-    mkdir -p "$BAK_DIR" 2>/dev/null || true
-    cp "$pointer" "$BAK_DIR/PROTOCOL.md" 2>/dev/null || true
-    echo "    BACKED UP: PROTOCOL.md (root) -> $BAK_DIR/PROTOCOL.md"
-  fi
-
-  # (b) When a baseline manifest is loaded, classify the root PROTOCOL.md
-  #     against the recorded install-time pointer hash. The pointer's "source"
-  #     is a generated string (not a file in $SOURCE_DIR), so we compare the
-  #     CURRENT target hash against the recorded BASELINE only:
-  #       H_dst == H_base  -> still the generated pointer -> safe to refresh
-  #       H_dst != H_base  -> adopter customized it -> ADOPTER-CUSTOMIZED:
-  #                           preserve (default/refuse) or overwrite per
-  #                           --on-conflict={theirs|backup}.
-  if [[ -f "$pointer" && -n "$_BASELINE_MANIFEST_FILE" ]] && command -v _hash_file >/dev/null 2>&1; then
-    local _rp_base _rp_dst
-    _rp_base="$( _baseline_lookup "PROTOCOL.md" || true )"
-    _rp_dst="$( _hash_file "$pointer" 2>/dev/null || true )"
-    if [[ -n "$_rp_base" && -n "$_rp_dst" && "$_rp_dst" != "$_rp_base" ]]; then
-      case "$ON_CONFLICT" in
-        theirs|backup)
-          # Original already backed up above; proceed to refresh.
-          echo "    OVERWROTE (root PROTOCOL.md ADOPTER-CUSTOMIZED, --on-conflict=$ON_CONFLICT; original in $BAK_DIR/PROTOCOL.md)" >&2
-          ;;
-        *)  # refuse (default): preserve the customized root PROTOCOL.md.
-          echo "    PRESERVED (root PROTOCOL.md ADOPTER-CUSTOMIZED — pointer NOT refreshed; backup in $BAK_DIR/PROTOCOL.md)" >&2
-          return 0
-          ;;
-      esac
-    fi
+  # ---- DECIDE --------------------------------------------------------------
+  local _pair _verdict
+  if ! _pair="$( _ownership_verdict protocol "$_pr" "$_lt" "$_lc" yes copy \
+                   "$CEREMONY_EFFECTIVE" upgrade none )"; then
+    echo "    WARNING: PROTOCOL.md dimensions are not a legal cell — PRESERVED" >&2
+    return 0
   fi
+  _verdict="${_pair%% *}"
+  _PROTOCOL_HASH_SOURCE="${_pair##* }"
+
+  # ---- EXECUTE -------------------------------------------------------------
+  # The guards this surface never had are not new branches: they are what the
+  # decision already says. A destination that is not a regular file is
+  # adopter-owned, so the verdict is unowned and nothing is written — which is
+  # exactly the leaf-symlink / directory / FIFO protection SPEC and the marker
+  # acquired during the S296 rounds and the pointer did not.
+  case "$_verdict" in
+    PRESERVE_UNOWNED|OMIT_RECORD)
+      case "$_lt" in
+        symlink) echo "    SKIP: PROTOCOL.md is a symlink — refusing to write THROUGH it (would mutate a path outside the target)" >&2 ;;
+        dir|dir_empty) echo "    SKIP: PROTOCOL.md is a directory — adopter-owned, refusing to write into it" >&2 ;;
+        special) echo "    SKIP: PROTOCOL.md is an unsupported special file — preserved, surface untouched" >&2 ;;
+        *) echo "    SKIP: PROTOCOL.md pointer (recorded --ceremony user install — a user install never creates root files, WS4)" ;;
+      esac
+      return 0
+      ;;
+
+    PRESERVE_OWNED)
+      _PROTOCOL_DELIVERED=1
+      if [ "$_lc" = "edited" ]; then
+        # ADR-155 decision (iii): the verified S238 case. An adopter-customised
+        # pointer is CONTENT, not a fork — it is preserved, and the record keeps
+        # the canonical digest so the next upgrade does not read it as pristine.
+        if [ "$DRY_RUN" -eq 0 ] && [ -f "$pointer" ]; then
+          mkdir -p "$BAK_DIR" 2>/dev/null || true
+          cp "$pointer" "$BAK_DIR/PROTOCOL.md" 2>/dev/null || true
+        fi
+        echo "    PRESERVED (root PROTOCOL.md is adopter-customised — pointer NOT refreshed; backup in $BAK_DIR/PROTOCOL.md)" >&2
+      else
+        echo "    SKIP: PROTOCOL.md pointer (ownership carried forward)"
+      fi
+      return 0
+      ;;
 
-  cat > "$pointer" <<EOF
+    DELIVER|REFRESH)
+      if [ "$DRY_RUN" -eq 1 ]; then
+        echo "    (dry-run) would REFRESH: PROTOCOL.md pointer"
+        return 0
+      fi
+      _up_record_op "refresh_protocol_pointer" "PROTOCOL.md"
+      # Backup-always before the overwrite, even with no baseline manifest —
+      # this is what made the S238 loss recoverable on a FIRST upgrade.
+      if [ -f "$pointer" ]; then
+        mkdir -p "$BAK_DIR" 2>/dev/null || true
+        cp "$pointer" "$BAK_DIR/PROTOCOL.md" 2>/dev/null || true
+        echo "    BACKED UP: PROTOCOL.md (root) -> $BAK_DIR/PROTOCOL.md"
+      fi
+      cat > "$pointer" <<EOF
 # Protocol reference
 
 $body
 EOF
-  echo "    REFRESHED: PROTOCOL.md pointer"
+      _PROTOCOL_DELIVERED=1
+      echo "    REFRESHED: PROTOCOL.md pointer"
+      return 0
+      ;;
+  esac
+}
+
+# ===========================================================================
+# PLAN-166 F3 (ADR-155-AMEND-1) — delivery-record lookups + SPEC/v1 FORCED
+# refresh + framework version marker refresh.
+# ---------------------------------------------------------------------------
+# Ownership of the three conditional surfaces (PROTOCOL.md, SPEC/v1,
+# .claude/.framework-version) derives from the REGISTERED DELIVERY — here,
+# the PRE-upgrade baseline manifest records (the same record install.sh
+# writes and doctor.sh reads) — never from the ceremony alone and never from
+# file presence (r7/r13/r17/r19/r20).
+# ===========================================================================
+_baseline_has_spec_record() {
+  [[ -n "$_BASELINE_MANIFEST_FILE" && -f "$_BASELINE_MANIFEST_FILE" ]] || return 1
+  # `(/|  |$)` and not a bare trailing slash: a --mode link install records
+  # the WHOLE tree as one directory symlink — `LINK  SPEC/v1  <target>`, no
+  # trailing slash — which a `SPEC/v1/` fragment can never match (the same
+  # `(  |$)` treatment the marker/PROTOCOL readers already have; family
+  # swept with doctor.sh _dr_delivered, re-pass closure).
+  grep -Eq '^([0-9a-f]{64}|LINK)  SPEC/v1(/|  |$)' "$_BASELINE_MANIFEST_FILE" 2>/dev/null
+}
+_baseline_has_marker_record() {
+  [[ -n "$_BASELINE_MANIFEST_FILE" && -f "$_BASELINE_MANIFEST_FILE" ]] || return 1
+  grep -Eq '^([0-9a-f]{64}|LINK)  \.claude/\.framework-version(  |$)' "$_BASELINE_MANIFEST_FILE" 2>/dev/null
+}
+# Third sibling of the family (codex W1 round 7, P2): the `--ceremony user`
+# skip needs the same ownership-continuity question the SPEC/marker skips
+# already ask. `_baseline_lookup` is not a substitute — it resolves HASH
+# records only, and a --mode link PROTOCOL.md is a LINK record.
+_baseline_has_protocol_record() {
+  [[ -n "$_BASELINE_MANIFEST_FILE" && -f "$_BASELINE_MANIFEST_FILE" ]] || return 1
+  grep -Eq '^([0-9a-f]{64}|LINK)  PROTOCOL\.md(  |$)' "$_BASELINE_MANIFEST_FILE" 2>/dev/null
+}
+
+# PRISTINE fingerprints of every SPEC/v1 tree the framework shipped at
+# v1.2.0 and earlier (r20 LEGACY MIGRATION: v1.2-and-earlier installs never
+# enumerated SPEC/v1, so no historical delivery record can distinguish a
+# framework-installed SPEC from an adopter's own — the ambiguity resolves by
+# CONTENT). Derivation (deterministic — pinned tag content; run in the
+# framework repo, reproduces _spec_tree_fingerprint byte-for-byte):
+#   for t in v1.0.0 v1.0.1 v1.0.1-rc.1 v1.1.0 v1.1.0-rc.1 \
+#            v1.2.0 v1.2.0-rc.1 v1.2.0-rc.2 v1.2.0-rc.3; do
+#     git ls-tree -r --name-only "$t" -- SPEC/v1 | LC_ALL=C sort \
+#     | while IFS= read -r f; do
+#         printf '%s  %s\n' \
+#           "$(git show "$t:$f" | shasum -a 256 | awk '{print $1}')" "$f"
+#       done | shasum -a 256 | awk '{print $1}'
+#   done
+# Three distinct trees across the nine shipped tags:
+#   a4a4... = v1.0.0 / v1.0.1 / v1.0.1-rc.1
+#   94aa... = v1.1.0 / v1.1.0-rc.1
+#   469a... = v1.2.0 / v1.2.0-rc.1 / v1.2.0-rc.2 / v1.2.0-rc.3
+_SPEC_PRISTINE_FINGERPRINTS="a4a4504a224d72a975a853dd71a75d8e678fef034a70deb49df291dbb712c161 94aa62f781285ce4897ad1220edf15e97b4e9d7b629f9f7ba3389da5d45f22b1 469a49238867be181490214305b43bc7299f2bae3ef0b282a5452f6caf327f0b"
+
+# _spec_tree_fingerprint <root> — sha256 over the LC_ALL=C-sorted
+# "<sha256(file)>  <relpath>" lines of every regular file under
+# <root>/SPEC/v1 (the derivation comment above reproduces this from a tag).
+# Fails (rc 1, no output) on a missing tree/hasher or any unhashable file —
+# a PARTIAL fingerprint must never be compared against a pristine one.
+_spec_tree_fingerprint() {
+  local _sf_root="$1"
+  command -v _hash_file >/dev/null 2>&1 || return 1
+  command -v _hash_stdin >/dev/null 2>&1 || return 1
+  [[ -d "$_sf_root/SPEC/v1" ]] || return 1
+  # COMPLETENESS gate (codex W1-ceremony round, P2): the fingerprint hashes
+  # regular files only, so an adopter-ADDED symlink/fifo/etc would be
+  # invisible — the partial fingerprint could still byte-match a pristine
+  # release and the forced refresh would REPLACE an adopter-modified tree
+  # (the S238 class). Any non-regular, non-directory entry => no
+  # fingerprint (rc 1) => the caller's safe path (ADOPTER-FORK preserve).
+  # A find traversal error (unreadable subdir) is the same: partial
+  # inventory must never be compared against a pristine fingerprint.
+  local _sf_odd
+  _sf_odd="$( ( cd "$_sf_root" && find SPEC/v1 -mindepth 1 ! -type f ! -type d -print 2>&1 ) )" || return 1
+  [[ -z "$_sf_odd" ]] || return 1
+  local _sf_lines
+  _sf_lines="$(
+    ( cd "$_sf_root" && find SPEC/v1 -type f -print 2>/dev/null ) \
+      | LC_ALL=C sort | while IFS= read -r _sf_rel; do
+          [[ -n "$_sf_rel" ]] || continue
+          _sf_h="$( _hash_file "$_sf_root/$_sf_rel" 2>/dev/null || true )"
+          if [[ -z "$_sf_h" ]]; then
+            printf 'HASH-FAILED\n'
+            break
+          fi
+          printf '%s  %s\n' "$_sf_h" "$_sf_rel"
+        done
+  )"
+  case "$_sf_lines" in
+    ""|*HASH-FAILED*) return 1 ;;
+  esac
+  printf '%s\n' "$_sf_lines" | _hash_stdin
+}
+
+
+# =============================================================================
+# PLAN-167 W2.2 — OBSERVERS.
+#
+# The callers no longer decide. They observe the nine dimensions, hand them to
+# _ownership_verdict, and execute what comes back. Everything below answers a
+# question about the world; nothing below chooses an outcome.
+#
+# That separation is the entire point. In S296 the answer to "is this owned?"
+# was recomputed inline at every branch, so two branches could answer the same
+# question differently and nothing detected the contradiction.
+# =============================================================================
+
+# _ov_obs_live_type <abs path> — lstat vocabulary, never following.
+_ov_obs_live_type() {
+  _olt_p="$1"
+  # Classify NON-REGULAR entries before anything opens the path. `ls -A` on a
+  # FIFO blocks forever waiting for a writer, so testing -d before -p turned
+  # the observer itself into the hang it was written to detect.
+  if   [ -L "$_olt_p" ]; then printf 'symlink'
+  elif [ ! -e "$_olt_p" ]; then printf 'absent'
+  elif [ -p "$_olt_p" ] || [ -S "$_olt_p" ]; then printf 'special'
+  elif [ -d "$_olt_p" ]; then
+    if [ -z "$( ls -A "$_olt_p" 2>/dev/null )" ]; then printf 'dir_empty'; else printf 'dir'; fi
+  elif [ -f "$_olt_p" ]; then printf 'regular'
+  else printf 'special'; fi
+}
+
+# _ov_obs_prior_record <relpath> — what the PRE-run sanitized baseline says.
+# link_match only when the recorded target still equals the live readlink; a
+# LINK row whose target moved is link_retargeted, and so is a LINK row whose
+# live path is no longer a symlink at all (readlink yields empty, which never
+# equals a recorded non-empty target).
+_ov_obs_prior_record() {
+  _opr_rel="$1"
+  [ -n "${_BASELINE_MANIFEST_FILE:-}" ] && [ -f "$_BASELINE_MANIFEST_FILE" ] || { printf 'none'; return 0; }
+  _opr_link="$( grep -E "^LINK  ${_opr_rel}  " "$_BASELINE_MANIFEST_FILE" 2>/dev/null | head -1 || true )"
+  if [ -n "$_opr_link" ]; then
+    # Fixed double-space delimiter, never whitespace field-splitting: a
+    # checkout path containing a space made awk '{print $3}' read an unchanged
+    # delivery as redirected.
+    _opr_rec="${_opr_link#LINK  ${_opr_rel}  }"
+    _opr_live="$( readlink "$TARGET/$_opr_rel" 2>/dev/null || true )"
+    if [ -n "$_opr_rec" ] && [ "$_opr_rec" = "$_opr_live" ]; then printf 'link_match'
+    else printf 'link_retargeted'; fi
+    return 0
+  fi
+  if grep -Eq "^[0-9a-f]{64}  ${_opr_rel}(/|$)" "$_BASELINE_MANIFEST_FILE" 2>/dev/null; then
+    printf 'hash'; return 0
+  fi
+  printf 'none'
+}
+
+# _ov_obs_spec_content — pristine | legacy_pristine | legacy_pristine_partial
+#                        | edited | -
+# A tree the fingerprint cannot fully inventory is NOT "pristine with a note":
+# it is its own observable, because a partial inventory must never certify a
+# wholesale replace (ADR-155-AMEND-1 §4).
+_ov_obs_spec_content() {
+  [ -e "$TARGET/SPEC/v1" ] || { printf '-'; return 0; }
+  _osc_fp="$( _spec_tree_fingerprint "$TARGET" 2>/dev/null || true )"
+  if [ -z "$_osc_fp" ]; then
+    # No fingerprint. Distinguish "cannot inventory" (a non-regular entry is
+    # present) from "not comparable at all".
+    _osc_odd="$( ( cd "$TARGET" && find SPEC/v1 -mindepth 1 ! -type f ! -type d -print 2>/dev/null ) )"
+    if [ -n "$_osc_odd" ]; then printf 'legacy_pristine_partial'; else printf 'edited'; fi
+    return 0
+  fi
+  _osc_src="$( _spec_tree_fingerprint "$SOURCE_DIR" 2>/dev/null || true )"
+  if [ -n "$_osc_src" ] && [ "$_osc_fp" = "$_osc_src" ]; then printf 'pristine'; return 0; fi
+  for _osc_pf in $_SPEC_PRISTINE_FINGERPRINTS; do
+    if [ "$_osc_fp" = "$_osc_pf" ]; then printf 'legacy_pristine'; return 0; fi
+  done
+  printf 'edited'
+}
+
+# _ov_obs_skip <relpath> — none | self | descendant.
+# The descendant scan walks the UNION of source and target and includes every
+# removable entry, not just regular files: the forced route find-deletes them
+# all, so a target-only symlink must be visible to skip detection too.
+_ov_obs_skip() {
+  _osk_rel="$1"
+  if _path_is_skipped "$_osk_rel"; then printf 'self'; return 0; fi
+  if [ "$_osk_rel" = "SPEC/v1" ]; then
+    _osk_hit=""
+    while IFS= read -r _osk_f; do
+      [ -n "$_osk_f" ] || continue
+      if _path_is_skipped "$_osk_f"; then _osk_hit=1; break; fi
+    done <<EOF
+$( { ( cd "$SOURCE_DIR" && find SPEC/v1 ! -type d -print 2>/dev/null );
+     [ -d "$TARGET/SPEC/v1" ] && ( cd "$TARGET" && find SPEC/v1 ! -type d -print 2>/dev/null ); } | LC_ALL=C sort -u )
+EOF
+    [ -n "$_osk_hit" ] && { printf 'descendant'; return 0; }
+  fi
+  printf 'none'
+}
+
+# _ov_obs_mode — the delivery mode this run carries. Evidence order: a prior
+# LINK record (authoritative), else a symlink probe on the owned roots.
+_ov_obs_mode() {
+  if [ -n "${_BASELINE_MANIFEST_FILE:-}" ] && [ -f "$_BASELINE_MANIFEST_FILE" ] \
+     && grep -Eq '^LINK  ' "$_BASELINE_MANIFEST_FILE" 2>/dev/null; then
+    printf 'link'; return 0
+  fi
+  if [ -L "$TARGET/SPEC/v1" ] || [ -L "$TARGET/.claude/.framework-version" ]; then
+    printf 'link'; return 0
+  fi
+  printf 'copy'
+}
+
+# _refresh_spec_contract — SPEC/v1 takes a FORCED route, NOT the generic
+# backup_and_replace: for a directory target with a baseline, the classified
+# walk PRESERVES adopter edits — so from the 2nd upgrade on, an edited SPEC
+# would classify ADOPTER-CUSTOMIZED and the stale-contract class would
+# return (r6). SPEC/v1 is the published compliance CONTRACT: an adopter edit
+# is a FORK of the contract, not a customization (OQ-3) => backup to
+# $BAK_DIR/SPEC/v1 + replace.
+#   * ceremony: a recorded `--ceremony user` install NEVER receives SPEC/v1
+#     (mirrors install.sh WS4-guard-spec), independent of --no-replay (r9).
+#   * ownership: baseline SPEC records => framework-owned (forced refresh);
+#     no target SPEC => new delivery; target SPEC with NO record => LEGACY
+#     MIGRATION by pristine content (r20): match => framework-owned refresh,
+#     no match => ADOPTER-FORK: preserve + snapshot + named WARNING.
+#   * root VERSION: this function (and the whole upgrade) NEVER touches it —
+#     install_one is skip-if-exists, so on an adopter with its own VERSION
+#     the framework never wrote there; backup_and_replace would TAKE the
+#     file (the S238/ADR-155 "verified worst case", trap C.5). See
+#     ADR-155-AMEND-1 for why the asymmetry is deliberate.
+_SPEC_DELIVERED=0
+_refresh_spec_contract() {
+  local sdir="$SOURCE_DIR/SPEC/v1"
+  local ddir="$TARGET/SPEC/v1"
+  local bdir="$BAK_DIR/SPEC/v1"
+
+  # ---- OBSERVE -------------------------------------------------------------
+  # Nothing here chooses an outcome. Each line answers one question about the
+  # world, and the answers go to _ownership_verdict as the nine dimensions.
+  local _lt _pr _lc _sh _md _sk
+  if _lg_ancestor_is_symlink "$TARGET" "SPEC/v1"; then
+    _lt="ancestor_symlink"           # reachable only by writing THROUGH a symlink
+  else
+    _lt="$( _ov_obs_live_type "$ddir" )"
+  fi
+  _pr="$( _ov_obs_prior_record "SPEC/v1" )"
+  _lc="$( _ov_obs_spec_content )"
+  _sh=no; [ -d "$sdir" ] && _sh=yes
+  _md="$( _ov_obs_mode )"
+  _sk="$( _ov_obs_skip "SPEC/v1" )"
+
+  # ---- DECIDE --------------------------------------------------------------
+  local _pair _verdict _hash
+  if ! _pair="$( _ownership_verdict spec "$_pr" "$_lt" "$_lc" "$_sh" "$_md" \
+                   "$CEREMONY_EFFECTIVE" upgrade "$_sk" )"; then
+    # The decision function refuses combinations its legality rules forbid.
+    # Fail toward preserve — under-claiming is recoverable, over-claiming is
+    # the delete-the-adopter's-file class (ADR-155-AMEND-1 §3).
+    echo "    WARNING: SPEC/v1 dimensions are not a legal cell" >&2
+    echo "             ($_pr/$_lt/$_lc/$_sh/$_md/$CEREMONY_EFFECTIVE/$_sk) —" >&2
+    echo "             PRESERVED without ownership. Please report this combination." >&2
+    return 0
+  fi
+  _verdict="${_pair%% *}"; _hash="${_pair##* }"
+  _SPEC_HASH_SOURCE="$_hash"   # consumed by the baseline rewrite
+
+  # ---- EXECUTE -------------------------------------------------------------
+  case "$_verdict" in
+    PRESERVE_OWNED)
+      _SPEC_DELIVERED=1
+      case "$_lt/$_sk/$_sh" in
+        ancestor_symlink/*/*) echo "    SKIP: SPEC/v1 has a symlinked ancestor (refusing to write through it — F11a)" ;;
+        symlink/*/*)          echo "    SKIP: SPEC/v1 is the recorded --mode link delivery (target unchanged)" ;;
+        */self/*)             echo "    SKIPPED (--skip): SPEC/v1" ;;
+        */descendant/*)       echo "    SKIPPED (--skip matches a descendant): SPEC/v1 refreshes as ONE contract unit — preserving the whole tree" ;;
+        */*/no)               echo "    SKIP: SPEC/v1 absent in source (ownership carried forward)" ;;
+        *)                    echo "    SKIP: SPEC/v1 (recorded --ceremony user install — root surfaces are out of scope, WS4)" ;;
+      esac
+      return 0
+      ;;
+
+    PRESERVE_UNOWNED|OMIT_RECORD)
+      # An adopter-owned surface. The ONLY case that earns a snapshot plus
+      # recovery guidance is the true ADOPTER-FORK: content the framework
+      # cannot claim, with no gate having refused first.
+      if [ "$_lt" = "dir" ] || [ "$_lt" = "dir_empty" ]; then
+        if [ "$DRY_RUN" -eq 1 ]; then
+          echo "    (dry-run) would PRESERVE (SPEC/v1 ADOPTER-FORK): SPEC/v1"
+          return 0
+        fi
+        local _snap_ok=0
+        if mkdir -p "$( dirname "$bdir" )" 2>/dev/null && cp -R "$ddir" "$bdir" 2>/dev/null; then
+          _snap_ok=1
+        fi
+        echo "    WARNING: SPEC/v1 is not framework-owned (no delivery record, and it" >&2
+        echo "             matches neither this checkout nor any pristine shipped SPEC)" >&2
+        if [ "$_snap_ok" -eq 1 ]; then
+          echo "             — PRESERVED in place (snapshot in $BAK_DIR/SPEC/v1)." >&2
+          echo "             To hand it back to the framework: remove the target SPEC/v1," >&2
+          echo "             copy this checkout's tree in, and re-run — a byte-identical" >&2
+          echo "             tree is taken over and recorded." >&2
+        else
+          # Recovery guidance is WITHHELD without a snapshot: following it
+          # would destroy the only copy of the fork.
+          echo "             — PRESERVED in place, but the forensic snapshot COULD NOT be" >&2
+          echo "             created. Back SPEC/v1 up yourself before any manual takeover." >&2
+        fi
+        _up_record_op "preserve_spec_v1_adopter_fork" "SPEC/v1"
+      else
+        echo "    SKIP: SPEC/v1 is $_lt — adopter-owned, preserved without ownership" >&2
+      fi
+      return 0
+      ;;
+
+    DELIVER|REFRESH)
+      if [ "$DRY_RUN" -eq 1 ]; then
+        if [ "$_verdict" = "REFRESH" ]; then
+          echo "    (dry-run) would FORCE-REFRESH (backup to $BAK_DIR/SPEC/v1): SPEC/v1"
+        else
+          echo "    (dry-run) would ADD: SPEC/v1"
+        fi
+        return 0
+      fi
+      _up_record_op "refresh_spec_v1" "$_pr/$_lc"
+
+      if [ "$_lt" = "dir" ] || [ "$_lt" = "dir_empty" ]; then
+        mkdir -p "$( dirname "$bdir" )" 2>/dev/null || true
+        # `|| true` is load-bearing: under `set -euo pipefail` a failing cp
+        # KILLS the run before the guard below can refuse the surface, so the
+        # upgrade dies mid-way instead of leaving this surface untouched.
+        if ! { cp -R "$ddir" "$bdir" 2>/dev/null || false; }; then
+          # INV-3: an execution failure NEVER advances the record. The surface
+          # is left exactly as it was, and so is its prior ownership record.
+          echo "    WARNING: could not back up SPEC/v1 — REFUSING to replace it" >&2
+          echo "             (backup-before-replace is the contract; surface untouched)" >&2
+          # INV-3: the REFRESH did not happen, so the record must not advance
+          # to source hashes. Retain the prior digest with the ownership.
+          _up_record_op "preserve_spec_v1_backup_failed" "SPEC/v1"
+          if [ "$_pr" = "hash" ]; then
+            _SPEC_DELIVERED=1
+            _SPEC_HASH_SOURCE="HASH_PRIOR_RECORD"
+          fi
+          return 0
+        fi
+        echo "    BACKED UP: SPEC/v1 -> $BAK_DIR/SPEC/v1"
+        find "$ddir" -mindepth 1 -delete
+        rmdir "$ddir" 2>/dev/null || true
+      elif [ "$_lt" = "regular" ]; then
+        mkdir -p "$( dirname "$bdir" )"
+        if cp "$ddir" "$bdir" 2>/dev/null; then
+          rm -f "$ddir"
+          echo "    BACKED UP: SPEC/v1 (non-directory) -> $BAK_DIR/SPEC/v1"
+        else
+          echo "    WARNING: could not back up non-directory SPEC/v1 — REFUSING to remove it" >&2
+          # INV-3: the REFRESH did not happen, so the record must not advance
+          # to source hashes. Retain the prior digest with the ownership.
+          _up_record_op "preserve_spec_v1_backup_failed" "SPEC/v1"
+          if [ "$_pr" = "hash" ]; then
+            _SPEC_DELIVERED=1
+            _SPEC_HASH_SOURCE="HASH_PRIOR_RECORD"
+          fi
+          return 0
+        fi
+      fi
+
+      mkdir -p "$( dirname "$ddir" )"
+      cp -R "$sdir" "$ddir"
+      _SPEC_DELIVERED=1
+      echo "    REFRESHED (forced — $_pr/$_lc): SPEC/v1"
+      return 0
+      ;;
+  esac
+}
+
+# _refresh_framework_marker — FORCED + VALIDATED write (r20 option (a)):
+# the marker is generated-refresh content — the upgrade rewrites it to the
+# source VERSION every run, backs up a differing pre-existing copy, and
+# read-back-validates the write. A marker the upgrade could not validate is
+# NOT recorded as delivered, so the FMS entry (and every marker-first
+# reader keyed off the SAME record) falls back to VERSION instead of
+# trusting a stale value. Delivered in BOTH ceremonies (inside .claude/).
+_MARKER_DELIVERED=0
+_refresh_framework_marker() {
+  local src="$SOURCE_DIR/.claude/.framework-version"
+  local dst="$TARGET/.claude/.framework-version"
+  local bak="$BAK_DIR/.claude/.framework-version"
+
+  # ---- OBSERVE -------------------------------------------------------------
+  local _lt _pr _lc _sh _md _sk
+  if _lg_ancestor_is_symlink "$TARGET" ".claude/.framework-version"; then
+    _lt="ancestor_symlink"
+  else
+    _lt="$( _ov_obs_live_type "$dst" )"
+  fi
+  _pr="$( _ov_obs_prior_record ".claude/.framework-version" )"
+  _sh=no; [ -f "$src" ] && _sh=yes
+  if [ ! -e "$dst" ] || [ -L "$dst" ]; then
+    _lc="-"
+  elif [ "$_sh" = yes ] && cmp -s "$src" "$dst" 2>/dev/null; then
+    _lc="pristine"
+  else
+    _lc="edited"
+  fi
+  _md="$( _ov_obs_mode )"
+  _sk="$( _ov_obs_skip ".claude/.framework-version" )"
+
+  # ---- DECIDE --------------------------------------------------------------
+  local _pair _verdict
+  if ! _pair="$( _ownership_verdict marker "$_pr" "$_lt" "$_lc" "$_sh" "$_md" \
+                   "$CEREMONY_EFFECTIVE" upgrade "$_sk" )"; then
+    echo "    WARNING: .claude/.framework-version dimensions are not a legal cell" >&2
+    echo "             — PRESERVED without ownership. Please report this combination." >&2
+    return 0
+  fi
+  _verdict="${_pair%% *}"
+  _MARKER_HASH_SOURCE="${_pair##* }"
+
+  # ---- EXECUTE -------------------------------------------------------------
+  case "$_verdict" in
+    PRESERVE_OWNED)
+      _MARKER_DELIVERED=1
+      case "$_lt/$_sk" in
+        ancestor_symlink/*) echo "    SKIP: .claude/.framework-version has a symlinked ancestor (refusing to write through it — F11a)" ;;
+        symlink/*)          echo "    SKIP: .claude/.framework-version is the recorded --mode link delivery (target unchanged)" ;;
+        */self)             echo "    SKIPPED (--skip): .claude/.framework-version" ;;
+        *)                  echo "    SKIP: .claude/.framework-version (ownership carried forward)" ;;
+      esac
+      return 0
+      ;;
+
+    OMIT_RECORD|PRESERVE_UNOWNED)
+      if [ "$_sh" = no ]; then
+        # The documented --pin downgrade: this source predates the marker, so a
+        # retained record would keep advertising a newer version over older
+        # content. Readers fall back to VERSION, which the pin DID update.
+        echo "    SKIP: .claude/.framework-version absent in source (pre-v1.3.0 checkout)"
+        if [ "$_pr" != "none" ]; then
+          echo "    NOTE: the prior delivery record is NOT carried forward — version" >&2
+          echo "          readers fall back to VERSION (which reflects the pinned source)" >&2
+        fi
+      elif [ "$_lt" = "symlink" ]; then
+        echo "    WARNING: .claude/.framework-version is a symlink that does NOT match the" >&2
+        echo "             recorded LINK delivery — preserved WITHOUT framework ownership" >&2
+        echo "             (readers fall back to VERSION)" >&2
+      else
+        echo "    SKIP: .claude/.framework-version is $_lt — adopter-owned, refusing to write into/through it"
+      fi
+      return 0
+      ;;
+
+    DELIVER|REFRESH)
+      if [ "$DRY_RUN" -eq 1 ]; then
+        echo "    (dry-run) would REFRESH: .claude/.framework-version ($(tr -d '[:space:]' < "$src" 2>/dev/null || true))"
+        return 0
+      fi
+      if [ "$_verdict" = "REFRESH" ] && [ "$_lc" = "edited" ]; then
+        mkdir -p "$( dirname "$bak" )" 2>/dev/null || true
+        if { cp "$dst" "$bak" 2>/dev/null || false; }; then
+          echo "    BACKED UP: .claude/.framework-version -> $bak"
+        else
+          # INV-3: an execution failure never advances the record.
+          echo "    WARNING: could not back up differing .claude/.framework-version —" >&2
+          echo "             REFUSING to overwrite it (backup-before-replace)" >&2
+          # INV-3, same as the SPEC branch above.
+          _up_record_op "preserve_marker_backup_failed" ".claude/.framework-version"
+          if [ "$_pr" = "hash" ]; then
+            _MARKER_DELIVERED=1
+            _MARKER_HASH_SOURCE="HASH_PRIOR_RECORD"
+          fi
+          return 0
+        fi
+      fi
+      mkdir -p "$( dirname "$dst" )"
+      cp "$src" "$dst"
+      # Read-back validation: a write that cannot be confirmed is NOT recorded
+      # as delivered, so every marker-first reader falls back to VERSION rather
+      # than trusting a value the upgrade could not verify.
+      if cmp -s "$src" "$dst" 2>/dev/null; then
+        _MARKER_DELIVERED=1
+        _up_record_op "refresh_framework_marker" "$(tr -d '[:space:]' < "$src" 2>/dev/null || true)"
+        echo "    REFRESHED: .claude/.framework-version ($(tr -d '[:space:]' < "$dst" 2>/dev/null || true))"
+      else
+        echo "    WARNING: .claude/.framework-version write did not validate — NOT recorded as" >&2
+        echo "             delivered (marker-first readers fall back to VERSION; r20)" >&2
+      fi
+      return 0
+      ;;
+  esac
 }
 
 has_profile() {
@@ -2436,9 +3018,60 @@ _migrate_settings_baseline
 
 # DevOps-P1-4: PROTOCOL.md is framework-derived (pointer), not user data —
 # refresh it so it stays aligned with the current source layout.
+# PLAN-166 F3 (ADR-155-AMEND-1): CEREMONY-GATED — the refresh used to run
+# unconditionally and `cat >`-created a root PROTOCOL.md that a
+# `--ceremony user` install deliberately never has (install.sh
+# WS4-guard-proto forbids root files); the F4 tree-comparison e2e exposes
+# exactly this divergence (r7/r13). The gate reads the ceremony from
+# .claude/.install-state.json via the replay-independent reader above.
+_PROTOCOL_DELIVERED=0
 echo ""
 echo "==> Refreshing PROTOCOL.md pointer"
-_refresh_protocol_pointer
+if [[ "$CEREMONY_EFFECTIVE" == "user" ]]; then
+  echo "    SKIP: PROTOCOL.md pointer (recorded --ceremony user install — a user install never creates root files, WS4; r13)"
+  # Ownership continuity on the analogous skip (codex W1 round 7, P2) — see
+  # the SPEC/v1 ceremony skip: preserving the tree while erasing its record
+  # strands a framework-delivered pointer as unowned.
+  #
+  # But the flag alone is NOT enough (codex W1 round 9, P1): this skip never
+  # runs _refresh_protocol_pointer, so _REFRESH_PROTOCOL_CANON_HASH stays
+  # empty, and _write_baseline_manifest then hashes the LIVE pointer —
+  # re-recording an adopter-CUSTOMIZED PROTOCOL.md as the framework baseline,
+  # which the next upgrade overwrites and uninstall can DELETE. Retaining
+  # ownership must never retain the wrong bytes. Carry the PRIOR canonical
+  # digest; a LINK record needs none (the link branch of the rewrite fires
+  # before the PROTOCOL special case). When neither is available, DROP the
+  # claim — the pointer stays adopter-owned and preserved, which is the
+  # pre-continuity behaviour and loses nothing.
+  if _baseline_has_protocol_record; then
+    _REFRESH_PROTOCOL_CANON_HASH="$( _baseline_lookup "PROTOCOL.md" 2>/dev/null || true )"
+    if [[ -n "$_REFRESH_PROTOCOL_CANON_HASH" ]] \
+       || grep -Eq '^LINK  PROTOCOL\.md(  |$)' "$_BASELINE_MANIFEST_FILE" 2>/dev/null; then
+      _PROTOCOL_DELIVERED=1
+    else
+      echo "    NOTE: PROTOCOL.md delivery record present but its canonical digest is" >&2
+      echo "          unrecoverable (ambiguous record) — ownership NOT claimed; the" >&2
+      echo "          pointer stays adopter-owned and preserved" >&2
+    fi
+  fi
+else
+  # _refresh_protocol_pointer sets _PROTOCOL_DELIVERED itself, from the
+  # VERDICT. Forcing it to 1 here overrode a PRESERVE_UNOWNED decision and
+  # recorded an adopter's own pre-existing PROTOCOL.md as framework-owned —
+  # a caller computing the right answer and then ignoring it (codex W3 r1 P1).
+  _refresh_protocol_pointer
+fi
+
+# PLAN-166 F3 (ADR-155-AMEND-1): SPEC/v1 forced refresh + framework version
+# marker. Both run BEFORE the baseline-manifest rewrite so the delivery
+# flags they set are what the rewritten baseline records.
+echo ""
+echo "==> Refreshing SPEC/v1 contract (PLAN-166 F3 — forced route)"
+_refresh_spec_contract
+
+echo ""
+echo "==> Refreshing framework version marker (.claude/.framework-version)"
+_refresh_framework_marker
 
 # PLAN-161 U3 — mis-install scan/purge. Runs in ALL modes (flag-absent and
 # --dry-run runs emit the would-purge PREVIEW; deletion requires the explicit
@@ -2465,14 +3098,60 @@ if [[ "$DRY_RUN" -eq 0 ]] && command -v _write_baseline_manifest >/dev/null 2>&1
                                        # (C.5 idempotency fix). PROTOCOL.md pointer
                                        # still hashes from FMS_ROOT inside the gen.
   export FMS_PROFILE_PARTS="${PROFILE_PARTS[*]}"
-  export FMS_MODE="copy"   # upgrade.sh always copies (never --mode link)
+  # FMS_MODE mirrors the INSTALL's mode, not the upgrade's copy behavior
+  # (codex W1-ceremony round, P2): on a --mode link target the refresh
+  # branches preserve the symlinks, but a `copy`-mode rewrite would OMIT
+  # the SPEC/v1 directory-LINK record and hash the marker symlink as a
+  # file — doctor.sh then reports a type-change drift on a healthy tree.
+  # Evidence order: prior baseline LINK record (authoritative), else a
+  # symlink probe on the framework-owned roots, else copy.
+  FMS_MODE="copy"
+  if [[ -n "$_BASELINE_MANIFEST_FILE" && -f "$_BASELINE_MANIFEST_FILE" ]] \
+     && grep -Eq '^LINK  ' "$_BASELINE_MANIFEST_FILE" 2>/dev/null; then
+    FMS_MODE="link"
+    # Confine LINK serialization to the paths that ALREADY were LINK records
+    # (codex W1 round 10, P2). Without this, inferring link-mode from the
+    # prior manifest also promoted every OTHER live symlink — e.g. an
+    # adopter's own file under `.claude/hooks/` — into a framework delivery
+    # record. The probe branch below leaves FMS_LINK_PATHS unset (no baseline
+    # to derive from), keeping its pre-existing behaviour.
+    FMS_LINK_PATHS="$( awk '
+      {
+        idx = index($0, "  ");
+        if (idx == 0) next;
+        if (substr($0, 1, idx - 1) != "LINK") next;
+        rest = substr($0, idx + 2);
+        j = index(rest, "  ");
+        print (j == 0 ? rest : substr(rest, 1, j - 1));
+      }' "$_BASELINE_MANIFEST_FILE" 2>/dev/null || true )"
+    export FMS_LINK_PATHS
+    echo "    baseline rewrite: --mode link install detected (LINK records in prior manifest) — preserving LINK serialization for $( printf '%s\n' "$FMS_LINK_PATHS" | grep -c . || true ) recorded path(s)"
+  elif [[ -L "$TARGET/.claude/skills" || -L "$TARGET/SPEC/v1" || -L "$TARGET/.claude/.framework-version" ]]; then
+    FMS_MODE="link"
+    echo "    baseline rewrite: --mode link install detected (symlink probe) — preserving LINK serialization"
+  fi
+  export FMS_MODE
   # Canonical PROTOCOL.md pointer hash (Codex R2 P0): record what the framework
   # WOULD generate, never a preserved adopter customization. Empty if the
   # pointer refresh did not run; the generator then falls back to hashing the
   # target (install semantics).
   export FMS_PROTOCOL_HASH="${_REFRESH_PROTOCOL_CANON_HASH:-}"
+  # PLAN-166 F3 (ADR-155-AMEND-1): conditional ownership from what THIS
+  # upgrade delivered/refreshed (or what the pre-upgrade baseline already
+  # recorded — ownership continuity), never the ceremony alone, never file
+  # presence (r17/r19/r20).
+  # The decision travels with the delivery flag.
+  export FMS_SOURCE_ROOT="$SOURCE_DIR"
+  export FMS_PRIOR_MANIFEST="${_BASELINE_MANIFEST_FILE:-}"
+  export FMS_HASH_SOURCE_SPEC="${_SPEC_HASH_SOURCE:-}"
+  export FMS_HASH_SOURCE_MARKER="${_MARKER_HASH_SOURCE:-}"
+  export FMS_HASH_SOURCE_PROTOCOL="${_PROTOCOL_HASH_SOURCE:-}"
+  export FMS_DELIVERED_SPEC="${_SPEC_DELIVERED:-0}"
+  export FMS_DELIVERED_PROTOCOL="${_PROTOCOL_DELIVERED:-0}"
+  export FMS_DELIVERED_MARKER="${_MARKER_DELIVERED:-0}"
   _write_baseline_manifest "$TARGET/.claude/.install-manifest.sha256"
-  unset FMS_ROOT FMS_HASH_ROOT FMS_PROFILE_PARTS FMS_MODE FMS_PROTOCOL_HASH
+  unset FMS_ROOT FMS_HASH_ROOT FMS_PROFILE_PARTS FMS_MODE FMS_PROTOCOL_HASH FMS_LINK_PATHS
+  unset FMS_DELIVERED_SPEC FMS_DELIVERED_PROTOCOL FMS_DELIVERED_MARKER
 fi
 
 # ===========================================================================
@@ -2505,6 +3184,7 @@ _write_upgrade_state() {
     "replay_source" "$_REPLAY_SOURCE"
     "harness" "$HARNESS"
     "managed_hooks" "$CODEX_MANAGED_HOOKS"
+    "ceremony_effective" "$CEREMONY_EFFECTIVE"
   )
   echo ""
   echo "==> (Re)writing install-state (.claude/.install-state.json — PLAN-153 Wave B)"
@@ -2597,6 +3277,7 @@ state = {
         "on_conflict": vals.get("on_conflict", ""),
         "pin": vals.get("pin", ""),
         "replay_source": vals.get("replay_source", ""),
+        "ceremony_effective": vals.get("ceremony_effective", ""),
     },
     "operations": ops,
     "result": {"upgrade_succeeded": True,

exec
/bin/zsh -lc "nl -ba scripts/upgrade.sh | sed -n '1520,2260p'" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
  1520	            rmdir "$TARGET/$_pr_rel" 2>/dev/null || true
  1521	          fi
  1522	        fi
  1523	      done < <( find "$src" -depth -type d -print 2>/dev/null )
  1524	    fi
  1525	  else
  1526	    cp "$src" "$dst"
  1527	  fi
  1528	  if [[ -n "$_lg_survivors" ]]; then
  1529	    rm -f "$_lg_survivors"
  1530	  fi
  1531	  echo "    UPDATED: $rel_path"
  1532	}
  1533	
  1534	# DevOps-P1-4: refresh PROTOCOL.md pointer on upgrade. This is
  1535	# framework-derived content (not user data), so preserving it as-is
  1536	# across upgrades traps stale pointers when the framework moves. We
  1537	# regenerate it with the same heuristic install.sh uses.
  1538	_refresh_protocol_pointer() {
  1539	  local pointer="$TARGET/PROTOCOL.md"
  1540	  local body
  1541	  case "$SOURCE_DIR" in
  1542	    "$TARGET"/*)
  1543	      local rel="${SOURCE_DIR#$TARGET/}"
  1544	      body="The full CEO orchestration protocol lives at:
  1545	./${rel}/PROTOCOL.md
  1546	
  1547	To pull updates:
  1548	  ( cd ./${rel} && git pull )
  1549	  ./${rel}/scripts/upgrade.sh . --profile $PROFILE --stack $STACK"
  1550	      ;;
  1551	    *)
  1552	      body="The full CEO orchestration protocol lives at:
  1553	{{PROTOCOL_SOURCE}}/PROTOCOL.md
  1554	
  1555	Edit {{PROTOCOL_SOURCE}} to point at your ceo-orchestration checkout
  1556	(e.g. ../ceo-orchestration or \$HOME/src/ceo-orchestration).
  1557	
  1558	To pull updates:
  1559	  ( cd {{PROTOCOL_SOURCE}} && git pull )
  1560	  {{PROTOCOL_SOURCE}}/scripts/upgrade.sh $TARGET --profile $PROFILE --stack $STACK"
  1561	      ;;
  1562	  esac
  1563	
  1564	  # The CANONICAL digest: the hash of exactly what the framework WOULD write.
  1565	  # Computed on every path, because the baseline rewrite must record it even
  1566	  # when the pointer is preserved — recording the customised bytes instead
  1567	  # would make the NEXT upgrade read H_dst == H_base and clobber them (C.5).
  1568	  _REFRESH_PROTOCOL_CANON_HASH=""
  1569	  if command -v _hash_stdin >/dev/null 2>&1; then
  1570	    _REFRESH_PROTOCOL_CANON_HASH="$( printf '# Protocol reference\n\n%s\n' "$body" | _hash_stdin 2>/dev/null || true )"
  1571	  fi
  1572	
  1573	  # ---- OBSERVE -------------------------------------------------------------
  1574	  local _lt _pr _lc
  1575	  _lt="$( _ov_obs_live_type "$pointer" )"
  1576	  _pr="$( _ov_obs_prior_record "PROTOCOL.md" )"
  1577	  if [ "$_lt" != "regular" ]; then
  1578	    _lc="-"
  1579	  elif [ -n "$_REFRESH_PROTOCOL_CANON_HASH" ] \
  1580	       && [ "$( _hash_file "$pointer" 2>/dev/null || true )" = "$_REFRESH_PROTOCOL_CANON_HASH" ]; then
  1581	    _lc="pristine"
  1582	  else
  1583	    _lc="edited"
  1584	  fi
  1585	
  1586	  # ---- DECIDE --------------------------------------------------------------
  1587	  local _pair _verdict
  1588	  if ! _pair="$( _ownership_verdict protocol "$_pr" "$_lt" "$_lc" yes copy \
  1589	                   "$CEREMONY_EFFECTIVE" upgrade none )"; then
  1590	    echo "    WARNING: PROTOCOL.md dimensions are not a legal cell — PRESERVED" >&2
  1591	    return 0
  1592	  fi
  1593	  _verdict="${_pair%% *}"
  1594	  _PROTOCOL_HASH_SOURCE="${_pair##* }"
  1595	
  1596	  # ---- EXECUTE -------------------------------------------------------------
  1597	  # The guards this surface never had are not new branches: they are what the
  1598	  # decision already says. A destination that is not a regular file is
  1599	  # adopter-owned, so the verdict is unowned and nothing is written — which is
  1600	  # exactly the leaf-symlink / directory / FIFO protection SPEC and the marker
  1601	  # acquired during the S296 rounds and the pointer did not.
  1602	  case "$_verdict" in
  1603	    PRESERVE_UNOWNED|OMIT_RECORD)
  1604	      case "$_lt" in
  1605	        symlink) echo "    SKIP: PROTOCOL.md is a symlink — refusing to write THROUGH it (would mutate a path outside the target)" >&2 ;;
  1606	        dir|dir_empty) echo "    SKIP: PROTOCOL.md is a directory — adopter-owned, refusing to write into it" >&2 ;;
  1607	        special) echo "    SKIP: PROTOCOL.md is an unsupported special file — preserved, surface untouched" >&2 ;;
  1608	        *) echo "    SKIP: PROTOCOL.md pointer (recorded --ceremony user install — a user install never creates root files, WS4)" ;;
  1609	      esac
  1610	      return 0
  1611	      ;;
  1612	
  1613	    PRESERVE_OWNED)
  1614	      _PROTOCOL_DELIVERED=1
  1615	      if [ "$_lc" = "edited" ]; then
  1616	        # ADR-155 decision (iii): the verified S238 case. An adopter-customised
  1617	        # pointer is CONTENT, not a fork — it is preserved, and the record keeps
  1618	        # the canonical digest so the next upgrade does not read it as pristine.
  1619	        if [ "$DRY_RUN" -eq 0 ] && [ -f "$pointer" ]; then
  1620	          mkdir -p "$BAK_DIR" 2>/dev/null || true
  1621	          cp "$pointer" "$BAK_DIR/PROTOCOL.md" 2>/dev/null || true
  1622	        fi
  1623	        echo "    PRESERVED (root PROTOCOL.md is adopter-customised — pointer NOT refreshed; backup in $BAK_DIR/PROTOCOL.md)" >&2
  1624	      else
  1625	        echo "    SKIP: PROTOCOL.md pointer (ownership carried forward)"
  1626	      fi
  1627	      return 0
  1628	      ;;
  1629	
  1630	    DELIVER|REFRESH)
  1631	      if [ "$DRY_RUN" -eq 1 ]; then
  1632	        echo "    (dry-run) would REFRESH: PROTOCOL.md pointer"
  1633	        return 0
  1634	      fi
  1635	      _up_record_op "refresh_protocol_pointer" "PROTOCOL.md"
  1636	      # Backup-always before the overwrite, even with no baseline manifest —
  1637	      # this is what made the S238 loss recoverable on a FIRST upgrade.
  1638	      if [ -f "$pointer" ]; then
  1639	        mkdir -p "$BAK_DIR" 2>/dev/null || true
  1640	        cp "$pointer" "$BAK_DIR/PROTOCOL.md" 2>/dev/null || true
  1641	        echo "    BACKED UP: PROTOCOL.md (root) -> $BAK_DIR/PROTOCOL.md"
  1642	      fi
  1643	      cat > "$pointer" <<EOF
  1644	# Protocol reference
  1645	
  1646	$body
  1647	EOF
  1648	      _PROTOCOL_DELIVERED=1
  1649	      echo "    REFRESHED: PROTOCOL.md pointer"
  1650	      return 0
  1651	      ;;
  1652	  esac
  1653	}
  1654	
  1655	# ===========================================================================
  1656	# PLAN-166 F3 (ADR-155-AMEND-1) — delivery-record lookups + SPEC/v1 FORCED
  1657	# refresh + framework version marker refresh.
  1658	# ---------------------------------------------------------------------------
  1659	# Ownership of the three conditional surfaces (PROTOCOL.md, SPEC/v1,
  1660	# .claude/.framework-version) derives from the REGISTERED DELIVERY — here,
  1661	# the PRE-upgrade baseline manifest records (the same record install.sh
  1662	# writes and doctor.sh reads) — never from the ceremony alone and never from
  1663	# file presence (r7/r13/r17/r19/r20).
  1664	# ===========================================================================
  1665	_baseline_has_spec_record() {
  1666	  [[ -n "$_BASELINE_MANIFEST_FILE" && -f "$_BASELINE_MANIFEST_FILE" ]] || return 1
  1667	  # `(/|  |$)` and not a bare trailing slash: a --mode link install records
  1668	  # the WHOLE tree as one directory symlink — `LINK  SPEC/v1  <target>`, no
  1669	  # trailing slash — which a `SPEC/v1/` fragment can never match (the same
  1670	  # `(  |$)` treatment the marker/PROTOCOL readers already have; family
  1671	  # swept with doctor.sh _dr_delivered, re-pass closure).
  1672	  grep -Eq '^([0-9a-f]{64}|LINK)  SPEC/v1(/|  |$)' "$_BASELINE_MANIFEST_FILE" 2>/dev/null
  1673	}
  1674	_baseline_has_marker_record() {
  1675	  [[ -n "$_BASELINE_MANIFEST_FILE" && -f "$_BASELINE_MANIFEST_FILE" ]] || return 1
  1676	  grep -Eq '^([0-9a-f]{64}|LINK)  \.claude/\.framework-version(  |$)' "$_BASELINE_MANIFEST_FILE" 2>/dev/null
  1677	}
  1678	# Third sibling of the family (codex W1 round 7, P2): the `--ceremony user`
  1679	# skip needs the same ownership-continuity question the SPEC/marker skips
  1680	# already ask. `_baseline_lookup` is not a substitute — it resolves HASH
  1681	# records only, and a --mode link PROTOCOL.md is a LINK record.
  1682	_baseline_has_protocol_record() {
  1683	  [[ -n "$_BASELINE_MANIFEST_FILE" && -f "$_BASELINE_MANIFEST_FILE" ]] || return 1
  1684	  grep -Eq '^([0-9a-f]{64}|LINK)  PROTOCOL\.md(  |$)' "$_BASELINE_MANIFEST_FILE" 2>/dev/null
  1685	}
  1686	
  1687	# PRISTINE fingerprints of every SPEC/v1 tree the framework shipped at
  1688	# v1.2.0 and earlier (r20 LEGACY MIGRATION: v1.2-and-earlier installs never
  1689	# enumerated SPEC/v1, so no historical delivery record can distinguish a
  1690	# framework-installed SPEC from an adopter's own — the ambiguity resolves by
  1691	# CONTENT). Derivation (deterministic — pinned tag content; run in the
  1692	# framework repo, reproduces _spec_tree_fingerprint byte-for-byte):
  1693	#   for t in v1.0.0 v1.0.1 v1.0.1-rc.1 v1.1.0 v1.1.0-rc.1 \
  1694	#            v1.2.0 v1.2.0-rc.1 v1.2.0-rc.2 v1.2.0-rc.3; do
  1695	#     git ls-tree -r --name-only "$t" -- SPEC/v1 | LC_ALL=C sort \
  1696	#     | while IFS= read -r f; do
  1697	#         printf '%s  %s\n' \
  1698	#           "$(git show "$t:$f" | shasum -a 256 | awk '{print $1}')" "$f"
  1699	#       done | shasum -a 256 | awk '{print $1}'
  1700	#   done
  1701	# Three distinct trees across the nine shipped tags:
  1702	#   a4a4... = v1.0.0 / v1.0.1 / v1.0.1-rc.1
  1703	#   94aa... = v1.1.0 / v1.1.0-rc.1
  1704	#   469a... = v1.2.0 / v1.2.0-rc.1 / v1.2.0-rc.2 / v1.2.0-rc.3
  1705	_SPEC_PRISTINE_FINGERPRINTS="a4a4504a224d72a975a853dd71a75d8e678fef034a70deb49df291dbb712c161 94aa62f781285ce4897ad1220edf15e97b4e9d7b629f9f7ba3389da5d45f22b1 469a49238867be181490214305b43bc7299f2bae3ef0b282a5452f6caf327f0b"
  1706	
  1707	# _spec_tree_fingerprint <root> — sha256 over the LC_ALL=C-sorted
  1708	# "<sha256(file)>  <relpath>" lines of every regular file under
  1709	# <root>/SPEC/v1 (the derivation comment above reproduces this from a tag).
  1710	# Fails (rc 1, no output) on a missing tree/hasher or any unhashable file —
  1711	# a PARTIAL fingerprint must never be compared against a pristine one.
  1712	_spec_tree_fingerprint() {
  1713	  local _sf_root="$1"
  1714	  command -v _hash_file >/dev/null 2>&1 || return 1
  1715	  command -v _hash_stdin >/dev/null 2>&1 || return 1
  1716	  [[ -d "$_sf_root/SPEC/v1" ]] || return 1
  1717	  # COMPLETENESS gate (codex W1-ceremony round, P2): the fingerprint hashes
  1718	  # regular files only, so an adopter-ADDED symlink/fifo/etc would be
  1719	  # invisible — the partial fingerprint could still byte-match a pristine
  1720	  # release and the forced refresh would REPLACE an adopter-modified tree
  1721	  # (the S238 class). Any non-regular, non-directory entry => no
  1722	  # fingerprint (rc 1) => the caller's safe path (ADOPTER-FORK preserve).
  1723	  # A find traversal error (unreadable subdir) is the same: partial
  1724	  # inventory must never be compared against a pristine fingerprint.
  1725	  local _sf_odd
  1726	  _sf_odd="$( ( cd "$_sf_root" && find SPEC/v1 -mindepth 1 ! -type f ! -type d -print 2>&1 ) )" || return 1
  1727	  [[ -z "$_sf_odd" ]] || return 1
  1728	  local _sf_lines
  1729	  _sf_lines="$(
  1730	    ( cd "$_sf_root" && find SPEC/v1 -type f -print 2>/dev/null ) \
  1731	      | LC_ALL=C sort | while IFS= read -r _sf_rel; do
  1732	          [[ -n "$_sf_rel" ]] || continue
  1733	          _sf_h="$( _hash_file "$_sf_root/$_sf_rel" 2>/dev/null || true )"
  1734	          if [[ -z "$_sf_h" ]]; then
  1735	            printf 'HASH-FAILED\n'
  1736	            break
  1737	          fi
  1738	          printf '%s  %s\n' "$_sf_h" "$_sf_rel"
  1739	        done
  1740	  )"
  1741	  case "$_sf_lines" in
  1742	    ""|*HASH-FAILED*) return 1 ;;
  1743	  esac
  1744	  printf '%s\n' "$_sf_lines" | _hash_stdin
  1745	}
  1746	
  1747	
  1748	# =============================================================================
  1749	# PLAN-167 W2.2 — OBSERVERS.
  1750	#
  1751	# The callers no longer decide. They observe the nine dimensions, hand them to
  1752	# _ownership_verdict, and execute what comes back. Everything below answers a
  1753	# question about the world; nothing below chooses an outcome.
  1754	#
  1755	# That separation is the entire point. In S296 the answer to "is this owned?"
  1756	# was recomputed inline at every branch, so two branches could answer the same
  1757	# question differently and nothing detected the contradiction.
  1758	# =============================================================================
  1759	
  1760	# _ov_obs_live_type <abs path> — lstat vocabulary, never following.
  1761	_ov_obs_live_type() {
  1762	  _olt_p="$1"
  1763	  # Classify NON-REGULAR entries before anything opens the path. `ls -A` on a
  1764	  # FIFO blocks forever waiting for a writer, so testing -d before -p turned
  1765	  # the observer itself into the hang it was written to detect.
  1766	  if   [ -L "$_olt_p" ]; then printf 'symlink'
  1767	  elif [ ! -e "$_olt_p" ]; then printf 'absent'
  1768	  elif [ -p "$_olt_p" ] || [ -S "$_olt_p" ]; then printf 'special'
  1769	  elif [ -d "$_olt_p" ]; then
  1770	    if [ -z "$( ls -A "$_olt_p" 2>/dev/null )" ]; then printf 'dir_empty'; else printf 'dir'; fi
  1771	  elif [ -f "$_olt_p" ]; then printf 'regular'
  1772	  else printf 'special'; fi
  1773	}
  1774	
  1775	# _ov_obs_prior_record <relpath> — what the PRE-run sanitized baseline says.
  1776	# link_match only when the recorded target still equals the live readlink; a
  1777	# LINK row whose target moved is link_retargeted, and so is a LINK row whose
  1778	# live path is no longer a symlink at all (readlink yields empty, which never
  1779	# equals a recorded non-empty target).
  1780	_ov_obs_prior_record() {
  1781	  _opr_rel="$1"
  1782	  [ -n "${_BASELINE_MANIFEST_FILE:-}" ] && [ -f "$_BASELINE_MANIFEST_FILE" ] || { printf 'none'; return 0; }
  1783	  _opr_link="$( grep -E "^LINK  ${_opr_rel}  " "$_BASELINE_MANIFEST_FILE" 2>/dev/null | head -1 || true )"
  1784	  if [ -n "$_opr_link" ]; then
  1785	    # Fixed double-space delimiter, never whitespace field-splitting: a
  1786	    # checkout path containing a space made awk '{print $3}' read an unchanged
  1787	    # delivery as redirected.
  1788	    _opr_rec="${_opr_link#LINK  ${_opr_rel}  }"
  1789	    _opr_live="$( readlink "$TARGET/$_opr_rel" 2>/dev/null || true )"
  1790	    if [ -n "$_opr_rec" ] && [ "$_opr_rec" = "$_opr_live" ]; then printf 'link_match'
  1791	    else printf 'link_retargeted'; fi
  1792	    return 0
  1793	  fi
  1794	  if grep -Eq "^[0-9a-f]{64}  ${_opr_rel}(/|$)" "$_BASELINE_MANIFEST_FILE" 2>/dev/null; then
  1795	    printf 'hash'; return 0
  1796	  fi
  1797	  printf 'none'
  1798	}
  1799	
  1800	# _ov_obs_spec_content — pristine | legacy_pristine | legacy_pristine_partial
  1801	#                        | edited | -
  1802	# A tree the fingerprint cannot fully inventory is NOT "pristine with a note":
  1803	# it is its own observable, because a partial inventory must never certify a
  1804	# wholesale replace (ADR-155-AMEND-1 §4).
  1805	_ov_obs_spec_content() {
  1806	  [ -e "$TARGET/SPEC/v1" ] || { printf '-'; return 0; }
  1807	  _osc_fp="$( _spec_tree_fingerprint "$TARGET" 2>/dev/null || true )"
  1808	  if [ -z "$_osc_fp" ]; then
  1809	    # No fingerprint. Distinguish "cannot inventory" (a non-regular entry is
  1810	    # present) from "not comparable at all".
  1811	    _osc_odd="$( ( cd "$TARGET" && find SPEC/v1 -mindepth 1 ! -type f ! -type d -print 2>/dev/null ) )"
  1812	    if [ -n "$_osc_odd" ]; then printf 'legacy_pristine_partial'; else printf 'edited'; fi
  1813	    return 0
  1814	  fi
  1815	  _osc_src="$( _spec_tree_fingerprint "$SOURCE_DIR" 2>/dev/null || true )"
  1816	  if [ -n "$_osc_src" ] && [ "$_osc_fp" = "$_osc_src" ]; then printf 'pristine'; return 0; fi
  1817	  for _osc_pf in $_SPEC_PRISTINE_FINGERPRINTS; do
  1818	    if [ "$_osc_fp" = "$_osc_pf" ]; then printf 'legacy_pristine'; return 0; fi
  1819	  done
  1820	  printf 'edited'
  1821	}
  1822	
  1823	# _ov_obs_skip <relpath> — none | self | descendant.
  1824	# The descendant scan walks the UNION of source and target and includes every
  1825	# removable entry, not just regular files: the forced route find-deletes them
  1826	# all, so a target-only symlink must be visible to skip detection too.
  1827	_ov_obs_skip() {
  1828	  _osk_rel="$1"
  1829	  if _path_is_skipped "$_osk_rel"; then printf 'self'; return 0; fi
  1830	  if [ "$_osk_rel" = "SPEC/v1" ]; then
  1831	    _osk_hit=""
  1832	    while IFS= read -r _osk_f; do
  1833	      [ -n "$_osk_f" ] || continue
  1834	      if _path_is_skipped "$_osk_f"; then _osk_hit=1; break; fi
  1835	    done <<EOF
  1836	$( { ( cd "$SOURCE_DIR" && find SPEC/v1 ! -type d -print 2>/dev/null );
  1837	     [ -d "$TARGET/SPEC/v1" ] && ( cd "$TARGET" && find SPEC/v1 ! -type d -print 2>/dev/null ); } | LC_ALL=C sort -u )
  1838	EOF
  1839	    [ -n "$_osk_hit" ] && { printf 'descendant'; return 0; }
  1840	  fi
  1841	  printf 'none'
  1842	}
  1843	
  1844	# _ov_obs_mode — the delivery mode this run carries. Evidence order: a prior
  1845	# LINK record (authoritative), else a symlink probe on the owned roots.
  1846	_ov_obs_mode() {
  1847	  if [ -n "${_BASELINE_MANIFEST_FILE:-}" ] && [ -f "$_BASELINE_MANIFEST_FILE" ] \
  1848	     && grep -Eq '^LINK  ' "$_BASELINE_MANIFEST_FILE" 2>/dev/null; then
  1849	    printf 'link'; return 0
  1850	  fi
  1851	  if [ -L "$TARGET/SPEC/v1" ] || [ -L "$TARGET/.claude/.framework-version" ]; then
  1852	    printf 'link'; return 0
  1853	  fi
  1854	  printf 'copy'
  1855	}
  1856	
  1857	# _refresh_spec_contract — SPEC/v1 takes a FORCED route, NOT the generic
  1858	# backup_and_replace: for a directory target with a baseline, the classified
  1859	# walk PRESERVES adopter edits — so from the 2nd upgrade on, an edited SPEC
  1860	# would classify ADOPTER-CUSTOMIZED and the stale-contract class would
  1861	# return (r6). SPEC/v1 is the published compliance CONTRACT: an adopter edit
  1862	# is a FORK of the contract, not a customization (OQ-3) => backup to
  1863	# $BAK_DIR/SPEC/v1 + replace.
  1864	#   * ceremony: a recorded `--ceremony user` install NEVER receives SPEC/v1
  1865	#     (mirrors install.sh WS4-guard-spec), independent of --no-replay (r9).
  1866	#   * ownership: baseline SPEC records => framework-owned (forced refresh);
  1867	#     no target SPEC => new delivery; target SPEC with NO record => LEGACY
  1868	#     MIGRATION by pristine content (r20): match => framework-owned refresh,
  1869	#     no match => ADOPTER-FORK: preserve + snapshot + named WARNING.
  1870	#   * root VERSION: this function (and the whole upgrade) NEVER touches it —
  1871	#     install_one is skip-if-exists, so on an adopter with its own VERSION
  1872	#     the framework never wrote there; backup_and_replace would TAKE the
  1873	#     file (the S238/ADR-155 "verified worst case", trap C.5). See
  1874	#     ADR-155-AMEND-1 for why the asymmetry is deliberate.
  1875	_SPEC_DELIVERED=0
  1876	_refresh_spec_contract() {
  1877	  local sdir="$SOURCE_DIR/SPEC/v1"
  1878	  local ddir="$TARGET/SPEC/v1"
  1879	  local bdir="$BAK_DIR/SPEC/v1"
  1880	
  1881	  # ---- OBSERVE -------------------------------------------------------------
  1882	  # Nothing here chooses an outcome. Each line answers one question about the
  1883	  # world, and the answers go to _ownership_verdict as the nine dimensions.
  1884	  local _lt _pr _lc _sh _md _sk
  1885	  if _lg_ancestor_is_symlink "$TARGET" "SPEC/v1"; then
  1886	    _lt="ancestor_symlink"           # reachable only by writing THROUGH a symlink
  1887	  else
  1888	    _lt="$( _ov_obs_live_type "$ddir" )"
  1889	  fi
  1890	  _pr="$( _ov_obs_prior_record "SPEC/v1" )"
  1891	  _lc="$( _ov_obs_spec_content )"
  1892	  _sh=no; [ -d "$sdir" ] && _sh=yes
  1893	  _md="$( _ov_obs_mode )"
  1894	  _sk="$( _ov_obs_skip "SPEC/v1" )"
  1895	
  1896	  # ---- DECIDE --------------------------------------------------------------
  1897	  local _pair _verdict _hash
  1898	  if ! _pair="$( _ownership_verdict spec "$_pr" "$_lt" "$_lc" "$_sh" "$_md" \
  1899	                   "$CEREMONY_EFFECTIVE" upgrade "$_sk" )"; then
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
  1963	        else
  1964	          echo "    (dry-run) would ADD: SPEC/v1"
  1965	        fi
  1966	        return 0
  1967	      fi
  1968	      _up_record_op "refresh_spec_v1" "$_pr/$_lc"
  1969	
  1970	      if [ "$_lt" = "dir" ] || [ "$_lt" = "dir_empty" ]; then
  1971	        mkdir -p "$( dirname "$bdir" )" 2>/dev/null || true
  1972	        # `|| true` is load-bearing: under `set -euo pipefail` a failing cp
  1973	        # KILLS the run before the guard below can refuse the surface, so the
  1974	        # upgrade dies mid-way instead of leaving this surface untouched.
  1975	        if ! { cp -R "$ddir" "$bdir" 2>/dev/null || false; }; then
  1976	          # INV-3: an execution failure NEVER advances the record. The surface
  1977	          # is left exactly as it was, and so is its prior ownership record.
  1978	          echo "    WARNING: could not back up SPEC/v1 — REFUSING to replace it" >&2
  1979	          echo "             (backup-before-replace is the contract; surface untouched)" >&2
  1980	          # INV-3: the REFRESH did not happen, so the record must not advance
  1981	          # to source hashes. Retain the prior digest with the ownership.
  1982	          _up_record_op "preserve_spec_v1_backup_failed" "SPEC/v1"
  1983	          if [ "$_pr" = "hash" ]; then
  1984	            _SPEC_DELIVERED=1
  1985	            _SPEC_HASH_SOURCE="HASH_PRIOR_RECORD"
  1986	          fi
  1987	          return 0
  1988	        fi
  1989	        echo "    BACKED UP: SPEC/v1 -> $BAK_DIR/SPEC/v1"
  1990	        find "$ddir" -mindepth 1 -delete
  1991	        rmdir "$ddir" 2>/dev/null || true
  1992	      elif [ "$_lt" = "regular" ]; then
  1993	        mkdir -p "$( dirname "$bdir" )"
  1994	        if cp "$ddir" "$bdir" 2>/dev/null; then
  1995	          rm -f "$ddir"
  1996	          echo "    BACKED UP: SPEC/v1 (non-directory) -> $BAK_DIR/SPEC/v1"
  1997	        else
  1998	          echo "    WARNING: could not back up non-directory SPEC/v1 — REFUSING to remove it" >&2
  1999	          # INV-3: the REFRESH did not happen, so the record must not advance
  2000	          # to source hashes. Retain the prior digest with the ownership.
  2001	          _up_record_op "preserve_spec_v1_backup_failed" "SPEC/v1"
  2002	          if [ "$_pr" = "hash" ]; then
  2003	            _SPEC_DELIVERED=1
  2004	            _SPEC_HASH_SOURCE="HASH_PRIOR_RECORD"
  2005	          fi
  2006	          return 0
  2007	        fi
  2008	      fi
  2009	
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
  2041	  if [ ! -e "$dst" ] || [ -L "$dst" ]; then
  2042	    _lc="-"
  2043	  elif [ "$_sh" = yes ] && cmp -s "$src" "$dst" 2>/dev/null; then
  2044	    _lc="pristine"
  2045	  else
  2046	    _lc="edited"
  2047	  fi
  2048	  _md="$( _ov_obs_mode )"
  2049	  _sk="$( _ov_obs_skip ".claude/.framework-version" )"
  2050	
  2051	  # ---- DECIDE --------------------------------------------------------------
  2052	  local _pair _verdict
  2053	  if ! _pair="$( _ownership_verdict marker "$_pr" "$_lt" "$_lc" "$_sh" "$_md" \
  2054	                   "$CEREMONY_EFFECTIVE" upgrade "$_sk" )"; then
  2055	    echo "    WARNING: .claude/.framework-version dimensions are not a legal cell" >&2
  2056	    echo "             — PRESERVED without ownership. Please report this combination." >&2
  2057	    return 0
  2058	  fi
  2059	  _verdict="${_pair%% *}"
  2060	  _MARKER_HASH_SOURCE="${_pair##* }"
  2061	
  2062	  # ---- EXECUTE -------------------------------------------------------------
  2063	  case "$_verdict" in
  2064	    PRESERVE_OWNED)
  2065	      _MARKER_DELIVERED=1
  2066	      case "$_lt/$_sk" in
  2067	        ancestor_symlink/*) echo "    SKIP: .claude/.framework-version has a symlinked ancestor (refusing to write through it — F11a)" ;;
  2068	        symlink/*)          echo "    SKIP: .claude/.framework-version is the recorded --mode link delivery (target unchanged)" ;;
  2069	        */self)             echo "    SKIPPED (--skip): .claude/.framework-version" ;;
  2070	        *)                  echo "    SKIP: .claude/.framework-version (ownership carried forward)" ;;
  2071	      esac
  2072	      return 0
  2073	      ;;
  2074	
  2075	    OMIT_RECORD|PRESERVE_UNOWNED)
  2076	      if [ "$_sh" = no ]; then
  2077	        # The documented --pin downgrade: this source predates the marker, so a
  2078	        # retained record would keep advertising a newer version over older
  2079	        # content. Readers fall back to VERSION, which the pin DID update.
  2080	        echo "    SKIP: .claude/.framework-version absent in source (pre-v1.3.0 checkout)"
  2081	        if [ "$_pr" != "none" ]; then
  2082	          echo "    NOTE: the prior delivery record is NOT carried forward — version" >&2
  2083	          echo "          readers fall back to VERSION (which reflects the pinned source)" >&2
  2084	        fi
  2085	      elif [ "$_lt" = "symlink" ]; then
  2086	        echo "    WARNING: .claude/.framework-version is a symlink that does NOT match the" >&2
  2087	        echo "             recorded LINK delivery — preserved WITHOUT framework ownership" >&2
  2088	        echo "             (readers fall back to VERSION)" >&2
  2089	      else
  2090	        echo "    SKIP: .claude/.framework-version is $_lt — adopter-owned, refusing to write into/through it"
  2091	      fi
  2092	      return 0
  2093	      ;;
  2094	
  2095	    DELIVER|REFRESH)
  2096	      if [ "$DRY_RUN" -eq 1 ]; then
  2097	        echo "    (dry-run) would REFRESH: .claude/.framework-version ($(tr -d '[:space:]' < "$src" 2>/dev/null || true))"
  2098	        return 0
  2099	      fi
  2100	      if [ "$_verdict" = "REFRESH" ] && [ "$_lc" = "edited" ]; then
  2101	        mkdir -p "$( dirname "$bak" )" 2>/dev/null || true
  2102	        if { cp "$dst" "$bak" 2>/dev/null || false; }; then
  2103	          echo "    BACKED UP: .claude/.framework-version -> $bak"
  2104	        else
  2105	          # INV-3: an execution failure never advances the record.
  2106	          echo "    WARNING: could not back up differing .claude/.framework-version —" >&2
  2107	          echo "             REFUSING to overwrite it (backup-before-replace)" >&2
  2108	          # INV-3, same as the SPEC branch above.
  2109	          _up_record_op "preserve_marker_backup_failed" ".claude/.framework-version"
  2110	          if [ "$_pr" = "hash" ]; then
  2111	            _MARKER_DELIVERED=1
  2112	            _MARKER_HASH_SOURCE="HASH_PRIOR_RECORD"
  2113	          fi
  2114	          return 0
  2115	        fi
  2116	      fi
  2117	      mkdir -p "$( dirname "$dst" )"
  2118	      cp "$src" "$dst"
  2119	      # Read-back validation: a write that cannot be confirmed is NOT recorded
  2120	      # as delivered, so every marker-first reader falls back to VERSION rather
  2121	      # than trusting a value the upgrade could not verify.
  2122	      if cmp -s "$src" "$dst" 2>/dev/null; then
  2123	        _MARKER_DELIVERED=1
  2124	        _up_record_op "refresh_framework_marker" "$(tr -d '[:space:]' < "$src" 2>/dev/null || true)"
  2125	        echo "    REFRESHED: .claude/.framework-version ($(tr -d '[:space:]' < "$dst" 2>/dev/null || true))"
  2126	      else
  2127	        echo "    WARNING: .claude/.framework-version write did not validate — NOT recorded as" >&2
  2128	        echo "             delivered (marker-first readers fall back to VERSION; r20)" >&2
  2129	      fi
  2130	      return 0
  2131	      ;;
  2132	  esac
  2133	}
  2134	
  2135	has_profile() {
  2136	  local p="$1"
  2137	  for part in "${PROFILE_PARTS[@]}"; do
  2138	    if [[ "$part" == "$p" ]]; then
  2139	      return 0
  2140	    fi
  2141	  done
  2142	  return 1
  2143	}
  2144	
  2145	# ---------------------------------------------------------------------------
  2146	# PLAN-135 W1 (unit w0r) — pre-flight model-deprecation advisory.
  2147	# Runs check-model-deprecations.py --check against the TARGET when the checker
  2148	# is available (source copy preferred — fresher ledger; falls back to the
  2149	# target's installed copy). NEVER blocks the upgrade: findings emit stderr
  2150	# WARNING lines (F-CHAOS-3 convention); any infra failure (no python3, corrupt
  2151	# ledger, unexpected rc) degrades to a NOTE and the upgrade proceeds
  2152	# (fail-open per CLAUDE.md §5). Suppress with --no-deprecation-warn.
  2153	# ---------------------------------------------------------------------------
  2154	_emit_deprecation_warnings() {
  2155	  [[ "$DEPRECATION_WARN" -eq 1 ]] || return 0
  2156	  local checker=""
  2157	  if [[ -f "$SOURCE_DIR/.claude/scripts/check-model-deprecations.py" ]]; then
  2158	    checker="$SOURCE_DIR/.claude/scripts/check-model-deprecations.py"
  2159	  elif [[ -f "$TARGET/.claude/scripts/check-model-deprecations.py" ]]; then
  2160	    checker="$TARGET/.claude/scripts/check-model-deprecations.py"
  2161	  fi
  2162	  [[ -n "$checker" ]] || return 0
  2163	  if ! command -v python3 >/dev/null 2>&1; then
  2164	    echo "    NOTE: model-deprecation scan skipped (python3 not found) — advisory only" >&2
  2165	    return 0
  2166	  fi
  2167	  local dep_rc=0
  2168	  python3 "$checker" --check "$TARGET" >/dev/null 2>&1 || dep_rc=$?
  2169	  if [[ "$dep_rc" -eq 1 ]]; then
  2170	    echo "    WARNING: deprecated/retiring Claude model ids detected in target" >&2
  2171	    echo "             (already retired, or <=60 days to retirement). Full report:" >&2
  2172	    echo "             python3 $checker $TARGET" >&2
  2173	  elif [[ "$dep_rc" -ne 0 ]]; then
  2174	    echo "    NOTE: model-deprecation scan inconclusive (rc=$dep_rc) — advisory only" >&2
  2175	  fi
  2176	  return 0
  2177	}
  2178	
  2179	_emit_deprecation_warnings
  2180	
  2181	# ---------------------------------------------------------------------------
  2182	# PLAN-135 W2 (unit h8) — idempotent settings-merge: register new framework
  2183	# lifecycle hooks into the adopter's EXISTING .claude/settings.json.
  2184	#
  2185	# WHY THIS EXISTS (constraint b, debate R1): install.sh EXISTS-SKIPs an
  2186	# existing settings.json, so a hook that is only baked into the fresh-install
  2187	# template (settings.base.json) NEVER reaches the S217 population of existing
  2188	# adopters. Without this step the Setup/init self-verification hook would be a
  2189	# silent no-op for every already-installed repo. We therefore merge the new
  2190	# registration(s) into the live settings.json here, at upgrade time, in the
  2191	# SAME ceremony.
  2192	#
  2193	# This registers the FIVE new W2 lifecycle events: PreCompact + PostCompact
  2194	# (check_precompact_continuity.py / check_postcompact_reinject.py), ConfigChange
  2195	# (check_config_change.py), SubagentStart (check_subagent_start.py), and
  2196	# Setup/init (check_setup_verification.py). The jq program is IDEMPOTENT (per
  2197	# event: filters any pre-existing block that registers the hook, then
  2198	# re-appends the single canonical block) so re-running the upgrade is a no-op.
  2199	# It is ADDITIVE — existing settings keys + hooks are preserved untouched.
  2200	#
  2201	# Fail-open per CLAUDE.md §5: no jq, malformed settings, or a merge error =>
  2202	# stderr NOTE + the upgrade proceeds. A backup of the pre-merge settings.json
  2203	# is written under $BAK_DIR first so the Owner can always roll back.
  2204	# Suppress entirely with --no-settings-merge.
  2205	# ---------------------------------------------------------------------------
  2206	_merge_lifecycle_hooks_into_settings() {
  2207	  [[ "$SETTINGS_MERGE" -eq 1 ]] || return 0
  2208	  local settings="$TARGET/.claude/settings.json"
  2209	  if [[ ! -f "$settings" ]]; then
  2210	    echo "    NOTE: settings-merge skipped — no $settings (fresh install builds it from template)" >&2
  2211	    return 0
  2212	  fi
  2213	  if ! command -v jq >/dev/null 2>&1; then
  2214	    echo "    NOTE: settings-merge skipped (jq not found) — register the Setup hook manually; advisory only" >&2
  2215	    return 0
  2216	  fi
  2217	
  2218	  echo ""
  2219	  echo "==> Registering new lifecycle hooks into .claude/settings.json (PLAN-135 W2 H8)"
  2220	  _up_record_op "merge_lifecycle_hooks" "additive settings.json merge"
  2221	
  2222	  # Idempotent jq program — mirrors staged merges/{60,62,64,70}-*.jq. Registers
  2223	  # ALL FIVE new W2 lifecycle hooks (Codex V2 P2: registering only Setup left
  2224	  # PreCompact/PostCompact/ConfigChange/SubagentStart dead for upgraded
  2225	  # adopters). The `_reg` helper filters any pre-existing entry that registers
  2226	  # the hook filename, then re-appends the single canonical block — so each
  2227	  # event is idempotent and every other settings key/hook is preserved.
  2228	  local jq_prog
  2229	  jq_prog='
  2230	def _reg($event; $name; $entry):
  2231	  .hooks[$event] = (
  2232	    [ (.hooks[$event] // [])[]
  2233	      | select(([.hooks[]? | .command // ""] | map(test($name)) | any) | not) ]
  2234	    + [$entry]
  2235	  );
  2236	.hooks = (.hooks // {})
  2237	| _reg("PreCompact"; "check_precompact_continuity\\.py"; {
  2238	    "_comment": "PLAN-135 W2 H1 (ADR-153): PreCompact continuity snapshot — plan-id + execution-unit + ceremony flags + HMAC-chain anchor to the plan scratchpad before the transcript collapses. ADVISORY, fail-open. Kill: CEO_COMPACTION_CONTINUITY=0.",
  2239	    "matcher": "",
  2240	    "hooks": [ { "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh\" check_precompact_continuity.py", "timeout": 5, "statusMessage": "Snapshotting governance state before compaction..." } ]
  2241	  })
  2242	| _reg("PostCompact"; "check_postcompact_reinject\\.py"; {
  2243	    "_comment": "PLAN-135 W2 H1 (ADR-153): PostCompact governance reinjection — reinjects governance POINTERS (active PLAN, unit position, Gate-1 reminder) via additionalContext after compaction. POINTERS ONLY, never file contents. ADVISORY, fail-open. Kill: CEO_COMPACTION_CONTINUITY=0.",
  2244	    "matcher": "",
  2245	    "hooks": [ { "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh\" check_postcompact_reinject.py", "timeout": 5, "statusMessage": "Reinjecting governance pointers after compaction..." } ]
  2246	  })
  2247	| _reg("ConfigChange"; "check_config_change\\.py"; {
  2248	    "_comment": "PLAN-135 W2 H2: ConfigChange guard — advisory audit + advisory-block of out-of-band settings tamper (the S197 class) via _lib/effective_config. Fail-open, never blocks on infra. Kill: CEO_CONFIG_CHANGE_GUARD=0.",
  2249	    "matcher": "",
  2250	    "hooks": [ { "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh\" check_config_change.py", "timeout": 5, "statusMessage": "Checking config change for tamper..." } ]
  2251	  })
  2252	| _reg("SubagentStart"; "check_subagent_start\\.py"; {
  2253	    "_comment": "PLAN-135 W2 H3: SubagentStart lifecycle recorder — spawn instant + context into a local sidecar (raw agent_id never persisted); the SubagentStop half consumes it for the per-agent bracket. ADVISORY, fail-open. Kill: CEO_SUBAGENT_LIFECYCLE=0.",
  2254	    "matcher": "",
  2255	    "hooks": [ { "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh\" check_subagent_start.py", "timeout": 5, "statusMessage": "Recording sub-agent spawn instant..." } ]
  2256	  })
  2257	| _reg("Setup"; "check_setup_verification\\.py"; {
  2258	    "_comment": "PLAN-135 W2 H8: Setup-event post-install self-verification (init matcher) — validate-governance --fast + verify-counts + hook exec-bits (the S228 exec-bit class) + CLAUDE_ENV_FILE allowlist persistence (explicit CEO_* include-list; every override/escape-hatch/kill-switch EXCLUDED, S185/S197 stale-override class). ADVISORY + fail-open; NEVER blocks. Kill-switch: CEO_SETUP_VERIFICATION=0.",
  2259	    "matcher": "init",
  2260	    "hooks": [ { "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh\" check_setup_verification.py", "timeout": 15, "statusMessage": "Post-install self-verification..." } ]

exec
/bin/zsh -lc "nl -ba scripts/upgrade.sh | sed -n '1740,2030p'" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
  1740	  )"
  1741	  case "$_sf_lines" in
  1742	    ""|*HASH-FAILED*) return 1 ;;
  1743	  esac
  1744	  printf '%s\n' "$_sf_lines" | _hash_stdin
  1745	}
  1746	
  1747	
  1748	# =============================================================================
  1749	# PLAN-167 W2.2 — OBSERVERS.
  1750	#
  1751	# The callers no longer decide. They observe the nine dimensions, hand them to
  1752	# _ownership_verdict, and execute what comes back. Everything below answers a
  1753	# question about the world; nothing below chooses an outcome.
  1754	#
  1755	# That separation is the entire point. In S296 the answer to "is this owned?"
  1756	# was recomputed inline at every branch, so two branches could answer the same
  1757	# question differently and nothing detected the contradiction.
  1758	# =============================================================================
  1759	
  1760	# _ov_obs_live_type <abs path> — lstat vocabulary, never following.
  1761	_ov_obs_live_type() {
  1762	  _olt_p="$1"
  1763	  # Classify NON-REGULAR entries before anything opens the path. `ls -A` on a
  1764	  # FIFO blocks forever waiting for a writer, so testing -d before -p turned
  1765	  # the observer itself into the hang it was written to detect.
  1766	  if   [ -L "$_olt_p" ]; then printf 'symlink'
  1767	  elif [ ! -e "$_olt_p" ]; then printf 'absent'
  1768	  elif [ -p "$_olt_p" ] || [ -S "$_olt_p" ]; then printf 'special'
  1769	  elif [ -d "$_olt_p" ]; then
  1770	    if [ -z "$( ls -A "$_olt_p" 2>/dev/null )" ]; then printf 'dir_empty'; else printf 'dir'; fi
  1771	  elif [ -f "$_olt_p" ]; then printf 'regular'
  1772	  else printf 'special'; fi
  1773	}
  1774	
  1775	# _ov_obs_prior_record <relpath> — what the PRE-run sanitized baseline says.
  1776	# link_match only when the recorded target still equals the live readlink; a
  1777	# LINK row whose target moved is link_retargeted, and so is a LINK row whose
  1778	# live path is no longer a symlink at all (readlink yields empty, which never
  1779	# equals a recorded non-empty target).
  1780	_ov_obs_prior_record() {
  1781	  _opr_rel="$1"
  1782	  [ -n "${_BASELINE_MANIFEST_FILE:-}" ] && [ -f "$_BASELINE_MANIFEST_FILE" ] || { printf 'none'; return 0; }
  1783	  _opr_link="$( grep -E "^LINK  ${_opr_rel}  " "$_BASELINE_MANIFEST_FILE" 2>/dev/null | head -1 || true )"
  1784	  if [ -n "$_opr_link" ]; then
  1785	    # Fixed double-space delimiter, never whitespace field-splitting: a
  1786	    # checkout path containing a space made awk '{print $3}' read an unchanged
  1787	    # delivery as redirected.
  1788	    _opr_rec="${_opr_link#LINK  ${_opr_rel}  }"
  1789	    _opr_live="$( readlink "$TARGET/$_opr_rel" 2>/dev/null || true )"
  1790	    if [ -n "$_opr_rec" ] && [ "$_opr_rec" = "$_opr_live" ]; then printf 'link_match'
  1791	    else printf 'link_retargeted'; fi
  1792	    return 0
  1793	  fi
  1794	  if grep -Eq "^[0-9a-f]{64}  ${_opr_rel}(/|$)" "$_BASELINE_MANIFEST_FILE" 2>/dev/null; then
  1795	    printf 'hash'; return 0
  1796	  fi
  1797	  printf 'none'
  1798	}
  1799	
  1800	# _ov_obs_spec_content — pristine | legacy_pristine | legacy_pristine_partial
  1801	#                        | edited | -
  1802	# A tree the fingerprint cannot fully inventory is NOT "pristine with a note":
  1803	# it is its own observable, because a partial inventory must never certify a
  1804	# wholesale replace (ADR-155-AMEND-1 §4).
  1805	_ov_obs_spec_content() {
  1806	  [ -e "$TARGET/SPEC/v1" ] || { printf '-'; return 0; }
  1807	  _osc_fp="$( _spec_tree_fingerprint "$TARGET" 2>/dev/null || true )"
  1808	  if [ -z "$_osc_fp" ]; then
  1809	    # No fingerprint. Distinguish "cannot inventory" (a non-regular entry is
  1810	    # present) from "not comparable at all".
  1811	    _osc_odd="$( ( cd "$TARGET" && find SPEC/v1 -mindepth 1 ! -type f ! -type d -print 2>/dev/null ) )"
  1812	    if [ -n "$_osc_odd" ]; then printf 'legacy_pristine_partial'; else printf 'edited'; fi
  1813	    return 0
  1814	  fi
  1815	  _osc_src="$( _spec_tree_fingerprint "$SOURCE_DIR" 2>/dev/null || true )"
  1816	  if [ -n "$_osc_src" ] && [ "$_osc_fp" = "$_osc_src" ]; then printf 'pristine'; return 0; fi
  1817	  for _osc_pf in $_SPEC_PRISTINE_FINGERPRINTS; do
  1818	    if [ "$_osc_fp" = "$_osc_pf" ]; then printf 'legacy_pristine'; return 0; fi
  1819	  done
  1820	  printf 'edited'
  1821	}
  1822	
  1823	# _ov_obs_skip <relpath> — none | self | descendant.
  1824	# The descendant scan walks the UNION of source and target and includes every
  1825	# removable entry, not just regular files: the forced route find-deletes them
  1826	# all, so a target-only symlink must be visible to skip detection too.
  1827	_ov_obs_skip() {
  1828	  _osk_rel="$1"
  1829	  if _path_is_skipped "$_osk_rel"; then printf 'self'; return 0; fi
  1830	  if [ "$_osk_rel" = "SPEC/v1" ]; then
  1831	    _osk_hit=""
  1832	    while IFS= read -r _osk_f; do
  1833	      [ -n "$_osk_f" ] || continue
  1834	      if _path_is_skipped "$_osk_f"; then _osk_hit=1; break; fi
  1835	    done <<EOF
  1836	$( { ( cd "$SOURCE_DIR" && find SPEC/v1 ! -type d -print 2>/dev/null );
  1837	     [ -d "$TARGET/SPEC/v1" ] && ( cd "$TARGET" && find SPEC/v1 ! -type d -print 2>/dev/null ); } | LC_ALL=C sort -u )
  1838	EOF
  1839	    [ -n "$_osk_hit" ] && { printf 'descendant'; return 0; }
  1840	  fi
  1841	  printf 'none'
  1842	}
  1843	
  1844	# _ov_obs_mode — the delivery mode this run carries. Evidence order: a prior
  1845	# LINK record (authoritative), else a symlink probe on the owned roots.
  1846	_ov_obs_mode() {
  1847	  if [ -n "${_BASELINE_MANIFEST_FILE:-}" ] && [ -f "$_BASELINE_MANIFEST_FILE" ] \
  1848	     && grep -Eq '^LINK  ' "$_BASELINE_MANIFEST_FILE" 2>/dev/null; then
  1849	    printf 'link'; return 0
  1850	  fi
  1851	  if [ -L "$TARGET/SPEC/v1" ] || [ -L "$TARGET/.claude/.framework-version" ]; then
  1852	    printf 'link'; return 0
  1853	  fi
  1854	  printf 'copy'
  1855	}
  1856	
  1857	# _refresh_spec_contract — SPEC/v1 takes a FORCED route, NOT the generic
  1858	# backup_and_replace: for a directory target with a baseline, the classified
  1859	# walk PRESERVES adopter edits — so from the 2nd upgrade on, an edited SPEC
  1860	# would classify ADOPTER-CUSTOMIZED and the stale-contract class would
  1861	# return (r6). SPEC/v1 is the published compliance CONTRACT: an adopter edit
  1862	# is a FORK of the contract, not a customization (OQ-3) => backup to
  1863	# $BAK_DIR/SPEC/v1 + replace.
  1864	#   * ceremony: a recorded `--ceremony user` install NEVER receives SPEC/v1
  1865	#     (mirrors install.sh WS4-guard-spec), independent of --no-replay (r9).
  1866	#   * ownership: baseline SPEC records => framework-owned (forced refresh);
  1867	#     no target SPEC => new delivery; target SPEC with NO record => LEGACY
  1868	#     MIGRATION by pristine content (r20): match => framework-owned refresh,
  1869	#     no match => ADOPTER-FORK: preserve + snapshot + named WARNING.
  1870	#   * root VERSION: this function (and the whole upgrade) NEVER touches it —
  1871	#     install_one is skip-if-exists, so on an adopter with its own VERSION
  1872	#     the framework never wrote there; backup_and_replace would TAKE the
  1873	#     file (the S238/ADR-155 "verified worst case", trap C.5). See
  1874	#     ADR-155-AMEND-1 for why the asymmetry is deliberate.
  1875	_SPEC_DELIVERED=0
  1876	_refresh_spec_contract() {
  1877	  local sdir="$SOURCE_DIR/SPEC/v1"
  1878	  local ddir="$TARGET/SPEC/v1"
  1879	  local bdir="$BAK_DIR/SPEC/v1"
  1880	
  1881	  # ---- OBSERVE -------------------------------------------------------------
  1882	  # Nothing here chooses an outcome. Each line answers one question about the
  1883	  # world, and the answers go to _ownership_verdict as the nine dimensions.
  1884	  local _lt _pr _lc _sh _md _sk
  1885	  if _lg_ancestor_is_symlink "$TARGET" "SPEC/v1"; then
  1886	    _lt="ancestor_symlink"           # reachable only by writing THROUGH a symlink
  1887	  else
  1888	    _lt="$( _ov_obs_live_type "$ddir" )"
  1889	  fi
  1890	  _pr="$( _ov_obs_prior_record "SPEC/v1" )"
  1891	  _lc="$( _ov_obs_spec_content )"
  1892	  _sh=no; [ -d "$sdir" ] && _sh=yes
  1893	  _md="$( _ov_obs_mode )"
  1894	  _sk="$( _ov_obs_skip "SPEC/v1" )"
  1895	
  1896	  # ---- DECIDE --------------------------------------------------------------
  1897	  local _pair _verdict _hash
  1898	  if ! _pair="$( _ownership_verdict spec "$_pr" "$_lt" "$_lc" "$_sh" "$_md" \
  1899	                   "$CEREMONY_EFFECTIVE" upgrade "$_sk" )"; then
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
  1963	        else
  1964	          echo "    (dry-run) would ADD: SPEC/v1"
  1965	        fi
  1966	        return 0
  1967	      fi
  1968	      _up_record_op "refresh_spec_v1" "$_pr/$_lc"
  1969	
  1970	      if [ "$_lt" = "dir" ] || [ "$_lt" = "dir_empty" ]; then
  1971	        mkdir -p "$( dirname "$bdir" )" 2>/dev/null || true
  1972	        # `|| true` is load-bearing: under `set -euo pipefail` a failing cp
  1973	        # KILLS the run before the guard below can refuse the surface, so the
  1974	        # upgrade dies mid-way instead of leaving this surface untouched.
  1975	        if ! { cp -R "$ddir" "$bdir" 2>/dev/null || false; }; then
  1976	          # INV-3: an execution failure NEVER advances the record. The surface
  1977	          # is left exactly as it was, and so is its prior ownership record.
  1978	          echo "    WARNING: could not back up SPEC/v1 — REFUSING to replace it" >&2
  1979	          echo "             (backup-before-replace is the contract; surface untouched)" >&2
  1980	          # INV-3: the REFRESH did not happen, so the record must not advance
  1981	          # to source hashes. Retain the prior digest with the ownership.
  1982	          _up_record_op "preserve_spec_v1_backup_failed" "SPEC/v1"
  1983	          if [ "$_pr" = "hash" ]; then
  1984	            _SPEC_DELIVERED=1
  1985	            _SPEC_HASH_SOURCE="HASH_PRIOR_RECORD"
  1986	          fi
  1987	          return 0
  1988	        fi
  1989	        echo "    BACKED UP: SPEC/v1 -> $BAK_DIR/SPEC/v1"
  1990	        find "$ddir" -mindepth 1 -delete
  1991	        rmdir "$ddir" 2>/dev/null || true
  1992	      elif [ "$_lt" = "regular" ]; then
  1993	        mkdir -p "$( dirname "$bdir" )"
  1994	        if cp "$ddir" "$bdir" 2>/dev/null; then
  1995	          rm -f "$ddir"
  1996	          echo "    BACKED UP: SPEC/v1 (non-directory) -> $BAK_DIR/SPEC/v1"
  1997	        else
  1998	          echo "    WARNING: could not back up non-directory SPEC/v1 — REFUSING to remove it" >&2
  1999	          # INV-3: the REFRESH did not happen, so the record must not advance
  2000	          # to source hashes. Retain the prior digest with the ownership.
  2001	          _up_record_op "preserve_spec_v1_backup_failed" "SPEC/v1"
  2002	          if [ "$_pr" = "hash" ]; then
  2003	            _SPEC_DELIVERED=1
  2004	            _SPEC_HASH_SOURCE="HASH_PRIOR_RECORD"
  2005	          fi
  2006	          return 0
  2007	        fi
  2008	      fi
  2009	
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

exec
/bin/zsh -lc "git diff -- .claude/scripts/check-framework-updates.sh .claude/scripts/check-model-deprecations.py scripts/doctor.sh scripts/tests/_parity_classify.py scripts/tests/ownership_table.tsv scripts/tests/test-ownership-table.sh && printf '\\n--- UNTRACKED UNIT ---\\n' && sed -n '1,220p' scripts/tests/test-ownership-verdict-unit.sh && printf '\\n--- UNTRACKED E2E ---\\n' && sed -n '1,420p' scripts/tests/test-upgrade-spec-ownership.sh" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-lC8z2X8h' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-nZav892V' (errno=Operation not permitted)
diff --git a/.claude/scripts/check-framework-updates.sh b/.claude/scripts/check-framework-updates.sh
index abe39d0..e867780 100755
--- a/.claude/scripts/check-framework-updates.sh
+++ b/.claude/scripts/check-framework-updates.sh
@@ -79,26 +79,111 @@ out() {
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
diff --git a/.claude/scripts/check-model-deprecations.py b/.claude/scripts/check-model-deprecations.py
index 7264c01..981014d 100644
--- a/.claude/scripts/check-model-deprecations.py
+++ b/.claude/scripts/check-model-deprecations.py
@@ -43,6 +43,7 @@ import datetime
 import json
 import os
 import re
+import stat
 import sys
 from typing import Dict, List, Optional, Tuple
 
@@ -203,7 +204,17 @@ def scan_root(
         for fn in filenames:
             path = os.path.join(dirpath, fn)
             try:
-                if os.path.getsize(path) > MAX_BYTES:
+                # lstat + S_ISREG, not getsize: opening a FIFO BLOCKS FOREVER
+                # waiting for a writer, and getsize reports 0 for one, so the
+                # size cap never sees it. An adopter with a FIFO anywhere under
+                # the target used to hang the whole upgrade here — mid-run,
+                # after earlier surfaces had already been modified
+                # (PLAN-167 docs §5.7). Symlinks are skipped for the same
+                # no-follow reason the rest of the install surface uses.
+                st = os.lstat(path)
+                if not stat.S_ISREG(st.st_mode):
+                    continue
+                if st.st_size > MAX_BYTES:
                     continue
                 with open(path, "rb") as fh:
                     raw = fh.read()
diff --git a/scripts/doctor.sh b/scripts/doctor.sh
index 20548fd..7425a2a 100755
--- a/scripts/doctor.sh
+++ b/scripts/doctor.sh
@@ -613,10 +613,44 @@ if [ "$NO_ORPHAN_SCAN" -eq 0 ]; then
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
diff --git a/scripts/tests/_parity_classify.py b/scripts/tests/_parity_classify.py
index d8809bd..b1f86bd 100644
--- a/scripts/tests/_parity_classify.py
+++ b/scripts/tests/_parity_classify.py
@@ -157,48 +157,13 @@ ACCEPTED: List[Tuple[str, Optional[str], str]] = [
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
diff --git a/scripts/tests/ownership_table.tsv b/scripts/tests/ownership_table.tsv
index 10f3398..e51d2c3 100644
--- a/scripts/tests/ownership_table.tsv
+++ b/scripts/tests/ownership_table.tsv
@@ -28,28 +28,28 @@ OWN-0021	spec	hash	dir	pristine	yes	copy	maintainer	upgrade	none	none	REFRESH	HA
 OWN-0022	spec	hash	dir	edited	yes	copy	maintainer	upgrade	none	none	REFRESH	HASH_SOURCE	adr-155-amend-1	contract fork is refreshed, not preserved (OQ-3 of ADR)
 OWN-0023	spec	hash	regular	edited	yes	copy	maintainer	upgrade	none	none	REFRESH	HASH_SOURCE	r3-F1	degenerate: delivered tree replaced by a regular file
 OWN-0024	spec	hash	regular	edited	yes	copy	maintainer	upgrade	none	backup_unwritable	ABORT_SURFACE	HASH_PRIOR_RECORD	r3-F1	backup-before-replace is the contract
-OWN-0025	spec	hash	special	-	yes	copy	maintainer	upgrade	none	none	ABORT_SURFACE	HASH_PRIOR_RECORD	r9-F3	FIFO: cp would block and hang the run mid-upgrade
+OWN-0025	spec	hash	special	-	yes	copy	maintainer	upgrade	none	none	PRESERVE_UNOWNED	HASH_NONE	r9-F3	FIFO: cp would block and hang the run mid-upgrade
 OWN-0026	marker	hash	regular	edited	yes	copy	maintainer	upgrade	none	none	REFRESH	HASH_SOURCE	adr-155-amend-1	forced + read-back-validated write
 OWN-0027	marker	hash	regular	edited	yes	copy	maintainer	upgrade	none	backup_unwritable	ABORT_SURFACE	HASH_PRIOR_RECORD	r4-F5	
-OWN-0028	marker	hash	dir	-	yes	copy	maintainer	upgrade	none	none	OMIT_RECORD	HASH_NONE	r2-F3	adopter directory at the marker path: correctly unowned, and a prior record existed => OMIT
+OWN-0028	marker	hash	dir	-	yes	copy	maintainer	upgrade	none	none	PRESERVE_UNOWNED	HASH_NONE	r2-F3	adopter directory at the marker path: correctly unowned, and a prior record existed => OMIT
 OWN-0029	marker	hash	special	-	yes	copy	maintainer	upgrade	none	none	PRESERVE_UNOWNED	HASH_NONE	r2-F3	FIFO destination blocks the upgrade
-OWN-0030	spec	hash	ancestor_symlink	*	yes	copy	maintainer	upgrade	none	none	OMIT_RECORD	HASH_NONE	r2-F1	dead-branch: the continuity line here can never fire — the relpath sanitizer drops any record whose path traverses a symlink BEFORE _baseline_has_*_record is consulted
-OWN-0031	marker	hash	ancestor_symlink	*	yes	copy	maintainer	upgrade	none	none	OMIT_RECORD	HASH_NONE	r4-F2	dead-branch: the continuity line here can never fire — the relpath sanitizer drops any record whose path traverses a symlink BEFORE _baseline_has_*_record is consulted
+OWN-0030	spec	hash	ancestor_symlink	*	yes	copy	maintainer	upgrade	none	none	PRESERVE_UNOWNED	HASH_NONE	r2-F1	dead-branch: the continuity line here can never fire — the relpath sanitizer drops any record whose path traverses a symlink BEFORE _baseline_has_*_record is consulted
+OWN-0031	marker	hash	ancestor_symlink	*	yes	copy	maintainer	upgrade	none	none	PRESERVE_UNOWNED	HASH_NONE	r4-F2	dead-branch: the continuity line here can never fire — the relpath sanitizer drops any record whose path traverses a symlink BEFORE _baseline_has_*_record is consulted
 OWN-0032	protocol	hash	dir	-	yes	copy	maintainer	upgrade	none	none	PRESERVE_UNOWNED	HASH_NONE	derived	GAP: no non-regular guard; cat > fails and set -e ABORTS the run
 OWN-0033	protocol	hash	special	-	yes	copy	maintainer	upgrade	none	none	PRESERVE_UNOWNED	HASH_NONE	derived	GAP: FIFO blocks the run; sibling of r9-F3/r2-F3
 OWN-0034	protocol	hash	symlink	edited	yes	copy	maintainer	upgrade	none	none	PRESERVE_UNOWNED	HASH_NONE	derived	GAP: cat > follows the leaf symlink OUTSIDE the target
 OWN-0040	spec	link_match	symlink	-	yes	link	maintainer	upgrade	none	none	PRESERVE_OWNED	LINK_RECORD	r4-F3	recorded link-mode delivery, target unchanged
 OWN-0041	marker	link_match	symlink	-	yes	link	maintainer	upgrade	none	none	PRESERVE_OWNED	LINK_RECORD	r4-F4	family sibling
-OWN-0042	spec	link_retargeted	symlink	-	yes	link	maintainer	upgrade	none	none	OMIT_RECORD	HASH_NONE	r4-F3	redirected link must not inherit ownership; a prior record existed, so the mechanical observation is OMIT (see OQ-9)
-OWN-0043	marker	link_retargeted	symlink	-	yes	link	maintainer	upgrade	none	none	OMIT_RECORD	HASH_NONE	r4-F4	readers fall back to VERSION; a prior record existed, so the mechanical observation is OMIT (see OQ-9)
+OWN-0042	spec	link_retargeted	symlink	-	yes	link	maintainer	upgrade	none	none	PRESERVE_UNOWNED	HASH_NONE	r4-F3	redirected link must not inherit ownership; a prior record existed, so the mechanical observation is OMIT (see OQ-9)
+OWN-0043	marker	link_retargeted	symlink	-	yes	link	maintainer	upgrade	none	none	PRESERVE_UNOWNED	HASH_NONE	r4-F4	readers fall back to VERSION; a prior record existed, so the mechanical observation is OMIT (see OQ-9)
 OWN-0044	spec	none	symlink	-	yes	copy	maintainer	upgrade	none	none	PRESERVE_UNOWNED	HASH_NONE	r8-F2	no LINK row BY DESIGN — must reach preserve, never set -e abort
 OWN-0045	marker	none	symlink	-	yes	copy	maintainer	upgrade	none	none	PRESERVE_UNOWNED	HASH_NONE	r8-F2	sibling site of the same set -e abort
 OWN-0046	spec	link_match	symlink	-	yes	link	maintainer	upgrade	none	none	PRESERVE_OWNED	LINK_RECORD	r6-F1	LINK record must survive relpath sanitization (leaf IS a symlink)
 OWN-0047	marker	link_match	symlink	-	yes	link	maintainer	upgrade	none	none	PRESERVE_OWNED	LINK_RECORD	r6-F1	sibling lookup
 OWN-0048	spec	link_match	symlink	-	yes	link	maintainer	upgrade	none	none	PRESERVE_OWNED	LINK_RECORD	r7-F3	note: link target path CONTAINS A SPACE — fixed double-space delimiter
 OWN-0049	marker	link_match	symlink	-	yes	link	maintainer	upgrade	none	none	PRESERVE_OWNED	LINK_RECORD	r7-F3	sibling site
-OWN-0050	spec	link_retargeted	symlink	-	yes	link	maintainer	install_rerun	none	none	OMIT_RECORD	HASH_NONE	r10-F1	continuity must compare prior LINK target to live readlink; a prior record existed, so the mechanical observation is OMIT (see OQ-9)
-OWN-0051	marker	link_retargeted	symlink	-	yes	link	maintainer	install_rerun	none	none	OMIT_RECORD	HASH_NONE	r10-F1	sibling site; a prior record existed, so the mechanical observation is OMIT (see OQ-9)
+OWN-0050	spec	link_retargeted	symlink	-	yes	link	maintainer	install_rerun	none	none	PRESERVE_UNOWNED	HASH_NONE	r10-F1	continuity must compare prior LINK target to live readlink; a prior record existed, so the mechanical observation is OMIT (see OQ-9)
+OWN-0051	marker	link_retargeted	symlink	-	yes	link	maintainer	install_rerun	none	none	PRESERVE_UNOWNED	HASH_NONE	r10-F1	sibling site; a prior record existed, so the mechanical observation is OMIT (see OQ-9)
 OWN-0052	spec	hash	symlink	-	yes	link	maintainer	install_rerun	none	none	PRESERVE_UNOWNED	HASH_NONE	r11-F1	open=r11-F1; absence of a LINK row is NOT a match
 OWN-0053	marker	hash	symlink	-	yes	link	maintainer	install_rerun	none	none	PRESERVE_UNOWNED	HASH_NONE	r11-F1	open=r11-F1; sibling site
 OWN-0060	spec	hash	dir	pristine	yes	copy	maintainer	upgrade	self	none	PRESERVE_OWNED	HASH_SOURCE	adr-155-amend-1	--skip SPEC/v1
@@ -61,8 +61,9 @@ OWN-0070	spec	hash	dir	pristine	yes	copy	user	upgrade	none	none	PRESERVE_OWNED	H
 OWN-0071	protocol	hash	regular	pristine	yes	copy	user	upgrade	none	none	PRESERVE_OWNED	HASH_PRIOR_RECORD	r7-F2	analogous PROTOCOL skip
 OWN-0072	protocol	hash	regular	edited	yes	copy	user	upgrade	none	none	PRESERVE_OWNED	HASH_PRIOR_RECORD	r9-F2	flag alone re-baselines the customized pointer
 OWN-0073	marker	hash	regular	pristine	yes	copy	user	upgrade	none	none	REFRESH	HASH_SOURCE	adr-155-amend-1	marker is delivered in BOTH ceremonies
-OWN-0080	marker	hash	regular	pristine	no	copy	maintainer	upgrade	none	none	OMIT_RECORD	HASH_NONE	r9-F4	--pin to a pre-v1.3 tag: readers fall back to VERSION
-OWN-0081	marker	hash	regular	pristine	no	copy	maintainer	upgrade	none	none	OMIT_RECORD	HASH_NONE	r11-F3	open=r11-F3; external target: VERSION is adopter-owned and never written
+OWN-0080	marker	hash	regular	pristine	no	copy	maintainer	upgrade	none	none	PRESERVE_UNOWNED	HASH_NONE	r9-F4	--pin to a pre-v1.3 tag: readers fall back to VERSION
+OWN-0081	marker	hash	regular	pristine	no	copy	maintainer	upgrade	none	none	PRESERVE_UNOWNED	HASH_NONE	r11-F3	open=r11-F3; external target: VERSION is adopter-owned and never written
 OWN-0082	spec	hash	dir	pristine	no	copy	maintainer	upgrade	none	none	PRESERVE_OWNED	HASH_PRIOR_RECORD	adr-155-amend-1	source lacks SPEC/v1: continuity, but no source bytes to hash
 OWN-0090	marker	hash	regular	edited	yes	copy	maintainer	upgrade	none	none	REFRESH	HASH_SOURCE	r7-F1	reader rule: checker must verify live bytes against the record
 OWN-0091	marker	hash	regular	edited	yes	copy	maintainer	install_rerun	none	none	PRESERVE_OWNED	HASH_SOURCE	r7-F1	1.3.0->9.9.9 edit must not suppress a real update
+OWN-0074	protocol	hash	regular	edited	yes	copy	maintainer	upgrade	none	none	PRESERVE_OWNED	HASH_CANONICAL_POINTER	derived	ADOPTER-CUSTOMIZED pointer on the NORMAL upgrade path — the verified S238 case; the digest stays canonical so the next upgrade does not read H_dst==H_base and clobber it
diff --git a/scripts/tests/test-ownership-table.sh b/scripts/tests/test-ownership-table.sh
index a510d43..c899879 100755
--- a/scripts/tests/test-ownership-table.sh
+++ b/scripts/tests/test-ownership-table.sh
@@ -179,7 +179,11 @@ _obs_record() {  # $1 = manifest abs path, $2 = relpath
 # defined by the framework having ATTEMPTED and declined, which leaves no
 # filesystem trace at all. If this wording changes, this test fails loudly —
 # which is correct, because the operator-visible contract changed.
-_ABORT_MARKERS='REFUSING to|could not back up|unsupported special file|backup-before-replace'
+# Only GENUINE execution failures. Refusing to act on an unsupported
+# destination is a DECISION (the surface is adopter-owned), not a failed
+# attempt — conflating them made the e2e and the decision function disagree
+# about the same cell (round-1 consensus C2).
+_ABORT_MARKERS='REFUSING to|could not back up|backup-before-replace'
 
 # =============================================================================
 # Fixtures
@@ -413,7 +417,8 @@ _derive_verdict() {  # $1 bd $2 ad $3 br $4 ar $5 out $6 surface $7 rel $8 opera
   if [[ "$op" == "upgrade" && "$_MTIME_BEFORE" != "$_MTIME_AFTER" ]]; then
     printf 'REFRESH'; return 0
   fi
-  if [[ -n "$br" && -z "$ar" ]]; then printf 'OMIT_RECORD'; return 0; fi
+  # OQ-9 colapsada: sem registro ao final é PRESERVE_UNOWNED, tenha ou não
+  # existido um antes. O 'tinha antes?' é prior_record, que já é uma coluna.
   if [[ -n "$ar" ]]; then printf 'PRESERVE_OWNED'; else printf 'PRESERVE_UNOWNED'; fi
 }
 
@@ -447,7 +452,20 @@ _derive_hash_source() {  # $1 surface $2 after_rec $3 prior_rec $4 src_root
     printf 'HASH_UNCLASSIFIED'; return 0
   fi
 
+  # The canonical pointer digest is the hash of what the framework WOULD
+  # generate — it matches no file on disk when the pointer is customised, so it
+  # has to be recognised explicitly or every correct record reads as
+  # unclassified.
+  # Order matters and is NOT arbitrary. For a PRISTINE pointer the canonical
+  # digest and the prior record are the SAME bytes, so whichever is tested
+  # first wins the name. Testing the prior record first keeps continuity rows
+  # reading as HASH_PRIOR_RECORD, and the canonical name is then reached only
+  # when the two genuinely differ — i.e. when the pointer was customised, which
+  # is the one cell where the distinction carries meaning.
   [[ -n "$c_prior"   && "$got" == "$c_prior"   ]] && { printf 'HASH_PRIOR_RECORD'; return 0; }
+  if [[ "$surface" == "protocol" && -n "$c_pointer" && "$got" == "$c_pointer" ]]; then
+    printf 'HASH_CANONICAL_POINTER'; return 0
+  fi
   [[ -n "$c_source"  && "$got" == "$c_source"  ]] && { printf 'HASH_SOURCE'; return 0; }
   [[ -n "$c_pointer" && "$got" == "$c_pointer" ]] && { printf 'HASH_CANONICAL_POINTER'; return 0; }
   [[ -n "$c_target"  && "$got" == "$c_target"  ]] && { printf 'HASH_TARGET'; return 0; }
@@ -530,8 +548,12 @@ _run_row() {
   local bak_guard=""
   case "$fault" in
     backup_unwritable)
-      bak_guard="$T/.claude.bak"
-      rm -rf "$bak_guard"; mkdir -p "$bak_guard"; chmod 500 "$bak_guard" ;;
+      # Make the SURFACE unbackupable, not the upgrade unstartable. upgrade.sh
+      # creates $BAK_DIR at startup, so locking .claude.bak killed the run
+      # before any surface was reached — the branch under test never ran.
+      # An unreadable SOURCE makes the copy fail while everything else proceeds.
+      bak_guard="$T/$rel"
+      chmod 000 "$bak_guard" 2>/dev/null || true ;;
   esac
 
   # --- BEFORE snapshot -----------------------------------------------------
@@ -571,7 +593,7 @@ _run_row() {
     _run_with_timeout "$CELL_TIMEOUT" "$src/scripts/install.sh" "${iargs[@]}" >> "$out" 2>&1
     rc=$?
   fi
-  [[ -n "$bak_guard" ]] && chmod 700 "$bak_guard" 2>/dev/null
+  [[ -n "$bak_guard" ]] && chmod -R u+rwX "$bak_guard" 2>/dev/null
 
   local timed_out=0
   [[ $rc -eq 124 || $rc -eq 137 ]] && timed_out=1

--- UNTRACKED UNIT ---
#!/usr/bin/env bash
# =============================================================================
# PLAN-167 W2 — UNIT oracle for _ownership_verdict().
#
# The same table, the other half of the contract:
#
#   this script            — does the DECISION match the model?   (milliseconds)
#   test-ownership-table.sh — do the callers OBSERVE the dimensions
#                             correctly and EXECUTE the verdict?  (~25 minutes)
#
# Both are required and they fail for different reasons. A wrong decision shows
# up here; a caller that reads the world wrong, or ignores the verdict it was
# handed, only shows up there.
#
# This one exists because of how PLAN-167 was caused. In S296 the only
# instrument was the slow one, one cell per ~40-minute round — a loop too long
# to converge in. An oracle that answers in milliseconds is what makes
# "drive the map to 100% green" a normal edit-run cycle instead of an
# overnight gamble.
#
# Usage:
#   test-ownership-verdict-unit.sh            every row
#   test-ownership-verdict-unit.sh --only OWN-0013,OWN-0021
#   test-ownership-verdict-unit.sh --quiet    only the summary
#
# Exit: 0 all rows match · 1 at least one mismatch · 2 harness/usage error.
# =============================================================================
set -uo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
TSV="$SCRIPT_DIR/ownership_table.tsv"
LIB="$REPO_ROOT/scripts/_framework_manifest_set.sh"

ONLY=""
QUIET=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --only)  ONLY="${2:-}"; shift 2 ;;
    --quiet) QUIET=1; shift ;;
    -h|--help) sed -n '2,26p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) echo "ERROR: unknown argument: $1" >&2; exit 2 ;;
  esac
done

[[ -f "$TSV" ]] || { echo "ERROR: table not found: $TSV" >&2; exit 2; }
[[ -f "$LIB" ]] || { echo "ERROR: library not found: $LIB" >&2; exit 2; }

# shellcheck source=/dev/null
. "$LIB" 2>/dev/null || { echo "ERROR: cannot source $LIB" >&2; exit 2; }
command -v _ownership_verdict >/dev/null 2>&1 || {
  echo "ERROR: _ownership_verdict is not defined in $LIB" >&2
  echo "       (W2 has not landed the function yet)" >&2
  exit 2
}

PASS=0; FAIL=0; SKIPPED=0
SKIP_IDS=""
LINES=""

while IFS=$'\t' read -r id surface prior_record live_type live_content \
      source_has mode ceremony operation skip_requested fault \
      exp_verdict exp_hash origin note; do
  [[ -z "${id:-}" ]] && continue
  case "$id" in \#*|id) continue ;; esac
  if [[ -n "$ONLY" && ",$ONLY," != *",$id,"* ]]; then continue; fi

  # Rows with an injected fault assert what the CALLER does when it cannot
  # carry out a verdict. That is execution, not decision (round-1 consensus
  # C2), so the pure function has nothing to say about them and the e2e suite
  # covers them. Counted and named, never silently skipped: a suite that goes
  # green by quietly not running rows is the vacuous-gate class.
  if [[ "${fault:-none}" != "none" ]]; then
    SKIPPED=$((SKIPPED+1))
    SKIP_IDS+="$id "
    continue
  fi

  got="$( _ownership_verdict "$surface" "$prior_record" "$live_type" \
            "$live_content" "$source_has" "$mode" "$ceremony" \
            "$operation" "$skip_requested" 2>/dev/null )"
  rc=$?
  exp="$exp_verdict $exp_hash"

  # A non-zero return or unparseable output is a FAILURE, never a skip: a
  # decision function that cannot answer for a legal cell has a hole in it,
  # and a hole that reports as "not applicable" is how a gap stays invisible.
  if [[ $rc -ne 0 || -z "$got" ]]; then
    LINES+="$( printf '%-10s FAIL   exp=%-40s got=<no answer, rc=%s>  %s\n' "$id" "$exp" "$rc" "$origin" )"$'\n'
    FAIL=$((FAIL+1)); continue
  fi

  if [[ "$got" == "$exp" ]]; then
    PASS=$((PASS+1))
    [[ "$QUIET" -eq 1 ]] || LINES+="$( printf '%-10s ok     %-40s %s\n' "$id" "$exp" "$origin" )"$'\n'
  else
    FAIL=$((FAIL+1))
    LINES+="$( printf '%-10s FAIL   exp=%-40s got=%-40s %s\n' "$id" "$exp" "$got" "$origin" )"$'\n'
  fi
done < "$TSV"

printf '%s' "$LINES" | LC_ALL=C sort
echo ""
echo "unit oracle: PASS=$PASS  FAIL=$FAIL  SKIPPED(execution-fault rows)=$SKIPPED"
[[ -n "$SKIP_IDS" ]] && echo "  not decision cells, covered by the e2e: $SKIP_IDS"
[[ "$FAIL" -gt 0 ]] && exit 1
exit 0

--- UNTRACKED E2E ---
#!/usr/bin/env bash
# scripts/tests/test-upgrade-spec-ownership.sh
# PLAN-166 F3 (ADR-155-AMEND-1) — delivery-record ownership of the three
# conditional framework surfaces (SPEC/v1, root PROTOCOL.md,
# .claude/.framework-version) across install → upgrade → doctor → updater.
#
# AC-3 scenarios exercised:
#   S1  maintainer fresh install: SPEC/v1 + PROTOCOL.md + marker DELIVERED
#       and recorded in the baseline manifest; marker == source VERSION;
#       delivered_* ops journaled in .install-state.json
#   S2  2nd-upgrade FORCED route (r6 — the load-bearing fixture): baseline
#       ALREADY contains SPEC/v1 records, SPEC edited locally => upgrade
#       REPLACES it (backup in .claude.bak/<ts>/SPEC/v1) — the generic
#       classified walk would have PRESERVED the edit; root VERSION
#       sentinel is NOT touched (S238/ADR-155 class)
#   S3  user-ceremony install + `upgrade --no-replay` (r9 MANDATORY):
#       neither install nor upgrade creates SPEC/v1 or a root PROTOCOL.md
#       (the ceremony is read by the replay-INDEPENDENT reader)
#   S4  legacy ADOPTER-FORK (r20): baseline without SPEC records (v1.2-and-
#       earlier shape) + locally edited SPEC => PRESERVED in place + named
#       WARNING + forensic snapshot (no pristine fingerprint match)
#   S5  pre-existing marker (r20) AND pre-existing root PROTOCOL.md (r13/
#       r17) on a MAINTAINER install: both EXISTS-skipped => NO delivery
#       record => neither is inventoried as framework-owned; the checker
#       refuses the unrecorded marker and falls back to VERSION; doctor
#       does not flag the adopter's PROTOCOL.md as an orphan
#   S6  updater no-loop regression (r8): post-upgrade tree with stale root
#       VERSION reports the NEW version via the recorded marker
#       (up-to-date, exit 0); stripping the marker record flips it back to
#       the stale VERSION (behind, exit != 0) — proves marker-first is
#       load-bearing, not decorative
#   S7  doctor, user mode (r19): adopter's OWN SPEC/v1 + root PROTOCOL.md
#       are NOT orphan candidates under --strict-orphans (flags resolved
#       from the baseline, not from a ceremony default)
#   S8  doctor, maintainer mode (r9 P2): a stray file inside the DELIVERED
#       SPEC/v1 IS an orphan candidate (positive control — the enumeration
#       does include SPEC when the record says delivered)
#
# The pristine-match branch of the legacy migration (target SPEC/v1 byte-
# identical to a shipped v1.2.0-or-earlier tree) deliberately lives in the
# F4 install-v1.2.0→upgrade e2e (needs real tag content); it is NOT
# duplicated here.
#
# bash 3.2-safe. mktemp -d only (xdist/parallel safe). Exits 0 on success,
# non-zero on any failed assertion.
#
# Run:  bash scripts/tests/test-upgrade-spec-ownership.sh ; echo rc=$?

set -uo pipefail   # NOT -e: we assert on command failures explicitly.

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SOURCE_DIR="$( cd "$SCRIPT_DIR/../.." && pwd )"
# Override points so the test can be pointed at staged/candidate scripts
# while they still live in a plan-staging mirror (PLAN-153 discipline).
# NOTE: an override must point INTO a full framework checkout — install.sh /
# upgrade.sh derive their source tree from their own resolved location.
INSTALL="${CEO_INSTALL_UNDER_TEST:-$SOURCE_DIR/scripts/install.sh}"
UPGRADE="${CEO_UPGRADE_UNDER_TEST:-$SOURCE_DIR/scripts/upgrade.sh}"
DOCTOR="${CEO_DOCTOR_UNDER_TEST:-$SOURCE_DIR/scripts/doctor.sh}"
CHECKER="${CEO_UPDATE_CHECKER_UNDER_TEST:-$SOURCE_DIR/.claude/scripts/check-framework-updates.sh}"

export CEO_INSTALL_SKIP_SELF_SHA=1
export CEO_RAG_INSTALL_PROMPT=0

if ! command -v python3 >/dev/null 2>&1; then
  echo "==> SKIP: python3 not installed (install-state machinery is python3-backed)"
  exit 0
fi

SRC_VERSION="$(tr -d '[:space:]' < "$SOURCE_DIR/VERSION" 2>/dev/null || true)"
if [ -z "$SRC_VERSION" ]; then
  echo "FATAL: cannot read $SOURCE_DIR/VERSION" >&2
  exit 2
fi
if [ ! -f "$SOURCE_DIR/.claude/.framework-version" ]; then
  echo "FATAL: source has no .claude/.framework-version (F3 marker missing)" >&2
  exit 2
fi

FAIL=0
PASS=0
WORKROOT="$( mktemp -d -t ceo-f3-own-XXXXXX )"
cleanup() { [ -n "${WORKROOT:-}" ] && rm -rf "$WORKROOT" 2>/dev/null || true; }
trap cleanup EXIT

ok()   { PASS=$((PASS+1)); printf '  ok   %s\n' "$1"; }
bad()  { FAIL=$((FAIL+1)); printf '  FAIL %s\n' "$1" >&2; }

_git_init_retry() {
  local d="$1" n=0
  while [ "$n" -lt 5 ]; do
    if ( cd "$d" && git init -q 2>/dev/null ); then return 0; fi
    n=$((n+1)); sleep 1
  done
  ( cd "$d" && git init -q )
}

run_install() {
  local t="$1"; shift
  bash "$INSTALL" "$t" "$@" >"$t.install.log" 2>&1
}

run_upgrade() {
  local t="$1"; shift
  bash "$UPGRADE" "$t" --no-deprecation-warn "$@" >"$t.upgrade.log" 2>&1
}

fresh_install() {
  # $1 = leg tag, rest = install args. Echoes the target path.
  local tag="$1"; shift
  local t
  t="$( mktemp -d "$WORKROOT/tgt-$tag-XXXXXX" )"
  _git_init_retry "$t"
  if ! run_install "$t" "$@"; then
    echo "INSTALL_FAILED ($tag)" >&2
    tail -30 "$t.install.log" >&2
    return 1
  fi
  printf '%s\n' "$t"
}

MANIFEST_REL=".claude/.install-manifest.sha256"
MARKER_REL=".claude/.framework-version"

manifest_has() {  # $1 = target, $2 = ERE fragment at the relpath position
  grep -Eq "^([0-9a-f]{64}|LINK)  $2" "$1/$MANIFEST_REL" 2>/dev/null
}

# --------------------------------------------------------------------------
# S1 — maintainer fresh install: delivery recorded end-to-end.
# --------------------------------------------------------------------------
echo "==> S1: maintainer install — SPEC/marker/PROTOCOL delivered + recorded"
T1="$( fresh_install m1 --profile core )" || exit 1

[ -d "$T1/SPEC/v1" ]            && ok "SPEC/v1 installed"            || bad "SPEC/v1 missing after maintainer install"
[ -f "$T1/PROTOCOL.md" ]        && ok "root PROTOCOL.md installed"   || bad "root PROTOCOL.md missing"
[ -f "$T1/$MARKER_REL" ]        && ok "marker installed"             || bad "marker missing"
[ "$(tr -d '[:space:]' < "$T1/$MARKER_REL" 2>/dev/null)" = "$SRC_VERSION" ] \
  && ok "marker == source VERSION ($SRC_VERSION)" \
  || bad "marker != source VERSION (got: $(cat "$T1/$MARKER_REL" 2>/dev/null))"

manifest_has "$T1" 'SPEC/v1/'                              && ok "baseline records SPEC/v1/"    || bad "baseline has NO SPEC/v1/ record"
manifest_has "$T1" 'PROTOCOL\.md(  |$)'                    && ok "baseline records PROTOCOL.md" || bad "baseline has NO PROTOCOL.md record"
manifest_has "$T1" '\.claude/\.framework-version(  |$)'    && ok "baseline records marker"      || bad "baseline has NO marker record"

grep -q '"delivered_spec_v1"' "$T1/.claude/.install-state.json" 2>/dev/null \
  && ok "install-state journals delivered_spec_v1" \
  || bad "install-state missing delivered_spec_v1 op"
grep -q '"delivered_framework_marker"' "$T1/.claude/.install-state.json" 2>/dev/null \
  && ok "install-state journals delivered_framework_marker" \
  || bad "install-state missing delivered_framework_marker op"

# --------------------------------------------------------------------------
# S2 — 2nd-upgrade forced route: record-owned edited SPEC is REPLACED with
# backup; root VERSION sentinel untouched (AC-3 load-bearing fixture).
# --------------------------------------------------------------------------
echo "==> S2: 2nd upgrade — forced SPEC refresh (baseline already has SPEC)"
SPEC_FILE="$( ls "$T1"/SPEC/v1/*.md 2>/dev/null | head -1 )"
if [ -z "$SPEC_FILE" ]; then
  bad "no SPEC file found to edit"
else
  printf '\nADOPTER-EDIT sentinel S2\n' >> "$SPEC_FILE"
fi
printf '1.0.0\n' > "$T1/VERSION"   # adopter-owned root VERSION sentinel

if run_upgrade "$T1"; then ok "upgrade rc=0 (record-owned fixture)"; else bad "upgrade failed (see $T1.upgrade.log)"; fi

SPEC_REL="${SPEC_FILE#"$T1"/}"
if [ -n "$SPEC_FILE" ]; then
  cmp -s "$SOURCE_DIR/$SPEC_REL" "$SPEC_FILE" \
    && ok "edited SPEC file was FORCE-replaced with source bytes" \
    || bad "edited SPEC file NOT replaced (classified walk preserved the fork?)"
  BAK_HIT="$( ls -d "$T1"/.claude.bak/*/SPEC/v1 2>/dev/null | head -1 )"
  if [ -n "$BAK_HIT" ] && grep -rq 'ADOPTER-EDIT sentinel S2' "$BAK_HIT" 2>/dev/null; then
    ok "backup of the edited SPEC present under .claude.bak/<ts>/SPEC/v1"
  else
    bad "no .claude.bak backup carrying the edited SPEC content"
  fi
fi
grep -q 'REFRESHED (forced' "$T1.upgrade.log" \
  && ok "upgrade log names the forced route" \
  || bad "upgrade log has no 'REFRESHED (forced' line"
[ "$(tr -d '[:space:]' < "$T1/VERSION" 2>/dev/null)" = "1.0.0" ] \
  && ok "root VERSION sentinel untouched by upgrade (ADR-155-AMEND-1)" \
  || bad "root VERSION was modified by upgrade (got: $(cat "$T1/VERSION" 2>/dev/null))"
[ "$(tr -d '[:space:]' < "$T1/$MARKER_REL" 2>/dev/null)" = "$SRC_VERSION" ] \
  && ok "marker refreshed to source VERSION post-upgrade" \
  || bad "marker not refreshed post-upgrade"
manifest_has "$T1" 'SPEC/v1/' \
  && ok "rewritten baseline still records SPEC/v1/ (ownership continuity)" \
  || bad "rewritten baseline dropped the SPEC/v1 records"

# --------------------------------------------------------------------------
# S6 — updater no-loop (r8) on the S2 fixture: marker-first wins over the
# stale root VERSION; stripping the marker record flips the source back.
# --------------------------------------------------------------------------
echo "==> S6: check-framework-updates.sh — marker-first, record-gated"
STUB="$WORKROOT/stub-upstream"
mkdir -p "$STUB"
_git_init_retry "$STUB"
( cd "$STUB" \
  && git -c user.email=t@t -c user.name=t commit -q --allow-empty -m x \
  && git tag "v$SRC_VERSION" ) 2>/dev/null \
  && ok "stub upstream tagged v$SRC_VERSION" \
  || bad "stub upstream construction failed"

CHK_OUT="$WORKROOT/chk1.out"; CHK_ERR="$WORKROOT/chk1.err"
( cd "$T1" && bash "$CHECKER" --upstream "$STUB" ) >"$CHK_OUT" 2>"$CHK_ERR"
CHK_RC=$?
[ "$CHK_RC" -eq 0 ] && grep -q 'up-to-date' "$CHK_OUT" \
  && ok "post-upgrade tree reports up-to-date via marker (no behind-minor loop)" \
  || bad "updater loop regression: rc=$CHK_RC (expected 0/up-to-date via marker; VERSION=1.0.0 is stale by design)"
grep -q 'version source: marker' "$CHK_ERR" \
  && ok "checker names the marker as its version source" \
  || bad "checker did not use the marker (stderr: $(head -3 "$CHK_ERR" 2>/dev/null | tr '\n' ' '))"

# Negative control: strip the marker record => fallback to stale VERSION.
sed -i.bak '/  \.claude\/\.framework-version/d' "$T1/$MANIFEST_REL" 2>/dev/null \
  || sed -i '' '/  \.claude\/\.framework-version/d' "$T1/$MANIFEST_REL" 2>/dev/null
( cd "$T1" && bash "$CHECKER" --upstream "$STUB" ) >"$WORKROOT/chk2.out" 2>"$WORKROOT/chk2.err"
CHK2_RC=$?
[ "$CHK2_RC" -ne 0 ] \
  && ok "marker record stripped => fallback to stale VERSION => behind (rc=$CHK2_RC)" \
  || bad "checker still up-to-date after stripping the marker record — record gate is dead"
grep -q 'falling back to VERSION' "$WORKROOT/chk2.err" \
  && ok "checker names the r20 fallback" \
  || bad "no 'falling back to VERSION' note on stripped record"

# --------------------------------------------------------------------------
# S8 — doctor, maintainer mode: delivered SPEC IS enumerated (orphan
# positive control).
# --------------------------------------------------------------------------
echo "==> S8: doctor maintainer mode — stray file in delivered SPEC is an orphan"
# Restore the marker record stripped by S6's negative control (the .bak of
# the GNU-sed branch, if present, is the pristine manifest).
if [ -f "$T1/$MANIFEST_REL.bak" ]; then mv "$T1/$MANIFEST_REL.bak" "$T1/$MANIFEST_REL"; fi
printf 'stray\n' > "$T1/SPEC/v1/zz-orphan-probe.md"
DOC_OUT="$WORKROOT/doc1.out"
bash "$DOCTOR" "$T1" --strict-orphans >"$DOC_OUT" 2>&1
DOC_RC=$?
grep -q 'ORPHAN?: SPEC/v1/zz-orphan-probe.md' "$DOC_OUT" && [ "$DOC_RC" -ne 0 ] \
  && ok "delivered SPEC is enumerated: stray file flagged, rc=$DOC_RC" \
  || bad "stray file in delivered SPEC NOT flagged (rc=$DOC_RC) — FMS_DELIVERED_SPEC resolution dead"
rm -f "$T1/SPEC/v1/zz-orphan-probe.md"

# --------------------------------------------------------------------------
# S4 — legacy ADOPTER-FORK (fresh fixture; simulate the v1.2-and-earlier
# baseline shape by stripping SPEC records, then fork the SPEC).
# --------------------------------------------------------------------------
echo "==> S4: legacy baseline (no SPEC records) + edited SPEC => preserve + WARNING"
T2="$( fresh_install m2 --profile core )" || exit 1
sed -i.bak '/  SPEC\/v1\//d' "$T2/$MANIFEST_REL" 2>/dev/null \
  || sed -i '' '/  SPEC\/v1\//d' "$T2/$MANIFEST_REL" 2>/dev/null
rm -f "$T2/$MANIFEST_REL.bak"
SPEC2="$( ls "$T2"/SPEC/v1/*.md 2>/dev/null | head -1 )"
printf '\nADOPTER-FORK sentinel S4\n' >> "$SPEC2"

if run_upgrade "$T2"; then ok "upgrade rc=0 (fork is preserved, never fatal)"; else bad "upgrade failed on adopter-fork fixture"; fi
grep -q 'ADOPTER-FORK' "$T2.upgrade.log" \
  && ok "named ADOPTER-FORK warning emitted" \
  || bad "no ADOPTER-FORK warning in upgrade log"
grep -q 'ADOPTER-FORK sentinel S4' "$SPEC2" 2>/dev/null \
  && ok "forked SPEC preserved in place" \
  || bad "forked SPEC was clobbered despite missing delivery record"
manifest_has "$T2" 'SPEC/v1/' \
  && bad "rewritten baseline claims the adopter-fork SPEC as framework-owned" \
  || ok "rewritten baseline does NOT claim the adopter-fork SPEC"
SNAP_HIT="$( ls -d "$T2"/.claude.bak/*/SPEC/v1 2>/dev/null | head -1 )"
[ -n "$SNAP_HIT" ] \
  && ok "forensic snapshot of the fork present under .claude.bak" \
  || bad "no forensic snapshot of the preserved fork"

# --------------------------------------------------------------------------
# S3 — user ceremony + upgrade --no-replay (r9): no SPEC, no root files.
# --------------------------------------------------------------------------
echo "==> S3: --ceremony user install + upgrade --no-replay"
T3="$( fresh_install u1 --profile core --ceremony user )" || exit 1
[ ! -e "$T3/SPEC" ]        && ok "user install has no SPEC/"            || bad "user install received SPEC/"
[ ! -e "$T3/PROTOCOL.md" ] && ok "user install has no root PROTOCOL.md" || bad "user install received root PROTOCOL.md"
[ -f "$T3/$MARKER_REL" ]   && ok "user install DOES receive the marker (inside .claude/)" \
                           || bad "user install missing the marker"
manifest_has "$T3" '\.claude/\.framework-version(  |$)' \
  && ok "user baseline records the marker" || bad "user baseline missing marker record"

if run_upgrade "$T3" --no-replay; then ok "upgrade --no-replay rc=0 on user fixture"; else bad "upgrade --no-replay failed on user fixture"; fi
[ ! -e "$T3/SPEC" ] \
  && ok "upgrade --no-replay did NOT deliver SPEC (ceremony read is replay-independent)" \
  || bad "r9 REGRESSION: upgrade --no-replay forced SPEC into a user install"
[ ! -e "$T3/PROTOCOL.md" ] \
  && ok "upgrade --no-replay did NOT create root PROTOCOL.md (gated _refresh_protocol_pointer)" \
  || bad "r13 REGRESSION: protocol pointer created on a user install"
grep -Eq 'Ceremony: user' "$T3.upgrade.log" \
  && ok "upgrade banner names the recorded user ceremony" \
  || bad "upgrade banner missing 'Ceremony: user'"

# --------------------------------------------------------------------------
# S7 — doctor, user mode: adopter's own SPEC + root PROTOCOL.md are not
# orphan candidates.
# --------------------------------------------------------------------------
echo "==> S7: doctor user mode — adopter SPEC/PROTOCOL not orphans"
mkdir -p "$T3/SPEC/v1"
printf 'the ADOPTERs own contract\n' > "$T3/SPEC/v1/own.md"
printf 'the ADOPTERs own protocol\n' > "$T3/PROTOCOL.md"
DOC3_OUT="$WORKROOT/doc3.out"
bash "$DOCTOR" "$T3" --strict-orphans >"$DOC3_OUT" 2>&1
DOC3_RC=$?
if grep -Eq 'ORPHAN\?: (SPEC/v1/|PROTOCOL\.md)' "$DOC3_OUT"; then
  bad "r19 REGRESSION: doctor flags the adopter's own SPEC/PROTOCOL as orphans (rc=$DOC3_RC)"
else
  ok "adopter's own SPEC/PROTOCOL not flagged (rc=$DOC3_RC)"
fi
[ "$DOC3_RC" -eq 0 ] \
  && ok "doctor --strict-orphans clean on the user fixture" \
  || bad "doctor --strict-orphans rc=$DOC3_RC on user fixture (see $DOC3_OUT)"
rm -f "$T3/PROTOCOL.md"

# --------------------------------------------------------------------------
# S5 — pre-existing marker (r20): EXISTS-skip => no record => VERSION wins.
# --------------------------------------------------------------------------
echo "==> S5: pre-existing marker + pre-existing root PROTOCOL.md not delivered, not trusted"
T4="$( mktemp -d "$WORKROOT/tgt-m3-XXXXXX" )"
_git_init_retry "$T4"
mkdir -p "$T4/.claude"
printf '9.9.9\n' > "$T4/$MARKER_REL"
printf '# the ADOPTERs own protocol (pre-existing)\n' > "$T4/PROTOCOL.md"
if run_install "$T4" --profile core; then ok "install rc=0 with pre-existing marker+protocol"; else bad "install failed (see $T4.install.log)"; fi
[ "$(tr -d '[:space:]' < "$T4/$MARKER_REL" 2>/dev/null)" = "9.9.9" ] \
  && ok "pre-existing marker EXISTS-skipped (adopter bytes intact)" \
  || bad "install overwrote a pre-existing marker"
manifest_has "$T4" '\.claude/\.framework-version(  |$)' \
  && bad "baseline claims a marker the install never wrote (r17/r20)" \
  || ok "baseline does NOT record the skipped marker"
grep -q 'ADOPTERs own protocol' "$T4/PROTOCOL.md" 2>/dev/null \
  && ok "pre-existing root PROTOCOL.md EXISTS-skipped (adopter bytes intact)" \
  || bad "install overwrote a pre-existing root PROTOCOL.md"
manifest_has "$T4" 'PROTOCOL\.md(  |$)' \
  && bad "r13/r17 REGRESSION: baseline claims a PROTOCOL.md the install never wrote" \
  || ok "baseline does NOT record the skipped PROTOCOL.md"
DOC4_OUT="$WORKROOT/doc4.out"
bash "$DOCTOR" "$T4" --strict-orphans >"$DOC4_OUT" 2>&1
DOC4_RC=$?
if grep -Eq 'ORPHAN\?: PROTOCOL\.md' "$DOC4_OUT"; then
  bad "doctor flags the adopter's pre-existing PROTOCOL.md as an orphan (rc=$DOC4_RC)"
else
  ok "doctor does not orphan-flag the adopter's pre-existing PROTOCOL.md (rc=$DOC4_RC)"
fi
( cd "$T4" && bash "$CHECKER" --upstream "$STUB" ) >"$WORKROOT/chk3.out" 2>"$WORKROOT/chk3.err"
CHK3_RC=$?
grep -q 'falling back to VERSION' "$WORKROOT/chk3.err" \
  && ok "checker refuses the unrecorded marker (r20)" \
  || bad "checker trusted an unrecorded marker (stderr: $(head -3 "$WORKROOT/chk3.err" 2>/dev/null | tr '\n' ' '))"
[ "$CHK3_RC" -eq 0 ] && grep -q 'up-to-date' "$WORKROOT/chk3.out" \
  && ok "fallback VERSION ($SRC_VERSION) matches stub upstream — up-to-date" \
  || bad "fallback path wrong rc=$CHK3_RC"

echo ""
echo "==> RESULT: pass=$PASS fail=$FAIL"
[ "$FAIL" -eq 0 ] || exit 1
exit 0

exec
/bin/zsh -lc 'git diff -- .github/workflows/npm-publish.yml .github/workflows/release.yml .github/workflows/smoke-install.yml .claude/scripts/tests/test_release_workflow_asserts.py' in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-rJBiL3GF' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-QANda9bT' (errno=Operation not permitted)
diff --git a/.claude/scripts/tests/test_release_workflow_asserts.py b/.claude/scripts/tests/test_release_workflow_asserts.py
index bc68a9f..3518bb3 100644
--- a/.claude/scripts/tests/test_release_workflow_asserts.py
+++ b/.claude/scripts/tests/test_release_workflow_asserts.py
@@ -25,6 +25,33 @@ workflow-invariant convention (test_workflow_devops_p2.py) with:
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
 
@@ -35,7 +62,30 @@ import unittest
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
@@ -57,6 +107,109 @@ _MARKER = "PLAN-153 Wave B item 5"
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
@@ -219,7 +372,8 @@ class WorkflowHygieneTest(TestEnvContext):
         except ImportError:  # pragma: no cover - CI installs pyyaml
             self.skipTest("pyyaml not installed")
         for name in ("release.yml", "npm-publish.yml"):
-            for path in ((_WF / name), (_STAGED_WF / name)):
+            for path in ((_WF / name), (_STAGED_WF / name),
+                         (_STAGED_166_WF / name)):
                 if not path.is_file():
                     continue
                 with self.subTest(path=str(path)):
@@ -233,7 +387,8 @@ class WorkflowHygieneTest(TestEnvContext):
         pattern = re.compile(r"^\s*(?:-\s+)?uses:\s*(\S+)", re.MULTILINE)
         pinned = re.compile(r".+@[0-9a-f]{40}$")
         for name in ("release.yml", "npm-publish.yml"):
-            for path in ((_WF / name), (_STAGED_WF / name)):
+            for path in ((_WF / name), (_STAGED_WF / name),
+                         (_STAGED_166_WF / name)):
                 if not path.is_file():
                     continue
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
diff --git a/.github/workflows/npm-publish.yml b/.github/workflows/npm-publish.yml
index aa2e29c..03071be 100644
--- a/.github/workflows/npm-publish.yml
+++ b/.github/workflows/npm-publish.yml
@@ -37,6 +37,47 @@ name: NPM Publish
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
@@ -52,6 +93,109 @@ permissions:
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
@@ -63,6 +207,13 @@ jobs:
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
diff --git a/.github/workflows/release.yml b/.github/workflows/release.yml
index 69d7836..596197e 100644
--- a/.github/workflows/release.yml
+++ b/.github/workflows/release.yml
@@ -69,6 +69,33 @@ jobs:
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
@@ -701,6 +728,143 @@ jobs:
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
diff --git a/.github/workflows/smoke-install.yml b/.github/workflows/smoke-install.yml
index e1317fb..5794f0b 100644
--- a/.github/workflows/smoke-install.yml
+++ b/.github/workflows/smoke-install.yml
@@ -8,11 +8,33 @@ on:
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
@@ -22,13 +44,26 @@ on:
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
@@ -42,7 +77,20 @@ jobs:
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
@@ -52,6 +100,20 @@ jobs:
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
@@ -108,6 +170,59 @@ jobs:
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

exec
/bin/zsh -lc "nl -ba .github/workflows/npm-publish.yml | sed -n '1,300p'; printf '\\n--- release changed segment ---\\n'; nl -ba .github/workflows/release.yml | sed -n '690,900p'; printf '\\n--- trusted publisher ---\\n'; cat .claude/governance/npm-trusted-publisher.txt" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
     1	name: NPM Publish
     2	
     3	# Sprint 5 Phase 4; registry auth migrated to npm **Trusted Publishing**
     4	# (OIDC) by PLAN-158 Wave 1 (PLAN-152 §Deferred backlog-oidc successor).
     5	# Publishes ceo-orchestration on tag push (`v*`): the npm CLI (>=11.5.1,
     6	# upgraded in-job — Node 20 bundles npm 10.x, which cannot do the
     7	# exchange) detects the GitHub Actions OIDC context (`id-token: write`)
     8	# and exchanges the per-run JWT for a short-lived publish credential
     9	# scoped to this repo + workflow + `production-npm` environment as
    10	# registered in the npmjs.com trusted-publisher config (Owner console).
    11	# The same JWT keeps feeding the Sigstore `--provenance` attestation.
    12	# The long-lived NPM_TOKEN is NOT read by this workflow anymore and is
    13	# REVOKED once the first OIDC GA publish succeeds (until then it exists
    14	# solely as the rollback path:
    15	# .claude/plans/PLAN-158/staged/wave1/rollback-oidc-to-token.patch +
    16	# .claude/plans/PLAN-158/oidc-failure-playbook.md — tag runs pin the
    17	# workflow to the tag's tree, so a failed GA publish means rollback +
    18	# delete/re-tag; there is no workflow_dispatch here by design).
    19	# Manual `npm publish` is not used. The workflow:
    20	#   1. Verifies VERSION + npm/package.json version + tag are consistent
    21	#   2. Asserts package.json has zero runtime dependencies
    22	#   3. Checks the registry for the exact version (PLAN-153 Wave B item 5
    23	#      `already_published` idempotency guard) — if already present, the
    24	#      run succeeds as a no-op instead of failing on EPUBLISHCONFLICT
    25	#   4. Publishes with --provenance (Sigstore-attested)
    26	#
    27	# PLAN-013 Phase 0 item 0.2 hardening (debate Round 1 consensus §C5
    28	# CRITICAL, 2/5 agents — DevOps + Staff Backend):
    29	#   - Skip RC tags entirely (`if: !contains(github.ref, '-rc.')`) —
    30	#     pushing `v1.4.0-rc.1` MUST NOT trigger a public npm publish;
    31	#     that would violate PLAN-013 anti-goal #3 ("NO NPM publish during
    32	#     Sprint 13") and anti-goal #16 ("NO auto-publish from tag without
    33	#     manual approval").
    34	#   - GA tags (`v1.4.0`) gate through `environment: production-npm`,
    35	#     which requires a manual approval step in GitHub's Environments
    36	#     settings before the job runs. The manual approval is the
    37	#     Owner-in-the-loop gate covering the Sprint 17 public-launch
    38	#     go/no-go decision (private-first strategy per
    39	#     `project_closure_strategy.md`).
    40	#
    41	# ---------------------------------------------------------------------
    42	# PLAN-166 W1 item 1 (F1, P0) — the publish now OBSERVES the governance
    43	# gate. `release.yml` and this workflow both fire on `push: tags: v*` as
    44	# two INDEPENDENT runs; until PLAN-166 nothing made the publish observe
    45	# the gate, so the only barrier was a human approving `production-npm`
    46	# with no machine evidence that `release-gate` was green — a live path
    47	# to publishing an unreviewed tree. A first job (`await-release-gate` —
    48	# deliberately NO `environment:` and NO RC exclusion, so it runs on RC
    49	# tags as a live positive control) polls release.yml's `release-gate`
    50	# JOB (never the run conclusion: CEO_SOTA_DISABLE=1 skips the job while
    51	# the run stays green) for THIS tag at THIS commit and fail-CLOSED
    52	# blocks unless it concluded success. `publish` gains
    53	# `needs: await-release-gate`; its `environment: production-npm`
    54	# approval and the RC exclusion are VERBATIM unchanged. Deliberate
    55	# ordering: the Owner's manual-approval prompt only appears AFTER the
    56	# gate is green — approval can never race ahead of machine evidence —
    57	# and the `already_published` idempotency guard STAYS in the publish
    58	# job (last-resort idempotency), not in the gate job. Do not "optimise"
    59	# the order back.
    60	#
    61	# Alternatives REJECTED (do not resurrect without a new debate):
    62	#   - `workflow_run` trigger: GitHub executes the workflow file from
    63	#     the DEFAULT branch, not the tag's tree — that kills the rollback
    64	#     invariant documented above (tag runs pin this workflow to the
    65	#     tag's tree; a failed GA publish means rollback + delete/re-tag).
    66	#   - moving the publish into release.yml: npm trusted publishing binds
    67	#     OIDC by workflow FILENAME
    68	#     (.claude/plans/PLAN-158/oidc-failure-playbook.md:18) — renaming
    69	#     the publishing workflow breaks the npmjs registration, plus ~6
    70	#     test pins on the npm-publish.yml path.
    71	#   - a reusable `workflow_call` gate shared by both workflows:
    72	#     refactor candidate, post-GA only (PLAN-166 §Deferred) — not
    73	#     during an open release window.
    74	#
    75	# The trusted-publisher binding triple (repository / workflow filename /
    76	# environment) is recorded in
    77	# .claude/governance/npm-trusted-publisher.txt and cross-checked by
    78	# .claude/scripts/tests/test_release_workflow_asserts.py, which READS
    79	# that file (embedding the values in the test would be a 4th copy of
    80	# the truth).
    81	
    82	on:
    83	  push:
    84	    tags:
    85	      - "v*"
    86	
    87	concurrency:
    88	  group: npm-publish-${{ github.ref }}
    89	  cancel-in-progress: false
    90	
    91	permissions:
    92	  contents: read
    93	  id-token: write   # required for OIDC trusted publishing + provenance
    94	
    95	jobs:
    96	  # ---------------------------------------------------------------------
    97	  # PLAN-166 W1 item 1 (F1, P0) — OBSERVE THE GOVERNANCE GATE.
    98	  # This job is the machine evidence that release.yml's `release-gate`
    99	  # job passed for this exact tag+SHA+push. It deliberately carries NO
   100	  # `environment:` and NO RC exclusion: it runs on rc tags too, which
   101	  # makes every RC a live positive control of the gate before GA ever
   102	  # depends on it.
   103	  # Decision function + battery: .claude/scripts/await_release_gate.py,
   104	  # .claude/scripts/tests/test_await_release_gate.py.
   105	  await-release-gate:
   106	    name: Await release-gate (release.yml)
   107	    runs-on: ubuntu-latest
   108	    # 35 > the poller's own 30-minute deadline, so a timeout surfaces as
   109	    # the decision function's fail-CLOSED BLOCK (with its inputs printed),
   110	    # not as an opaque runner kill.
   111	    timeout-minutes: 35
   112	    permissions:
   113	      contents: read   # checkout the tag to get the decision script
   114	      actions: read    # read release.yml's runs + jobs over the REST API
   115	    env:
   116	      # `permissions:` alone does NOT authenticate the `gh` CLI on a
   117	      # hosted runner. Without GH_TOKEN every poll dies on auth, which is
   118	      # BLOCK (fail-closed) — i.e. it would break EVERY release, RC and
   119	      # GA alike. This token is the job's only credential; the job has no
   120	      # id-token and no environment.
   121	      GH_TOKEN: ${{ github.token }}
   122	    steps:
   123	      - name: Checkout tag
   124	        # SHA-pinned (Sprint 7 Dependabot bump): actions/checkout@v6.0.2
   125	        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd
   126	
   127	      - name: Poll release.yml until release-gate concludes
   128	        # No `${{ }}` interpolation inside this script by design — every
   129	        # value arrives through the environment, so no workflow expression
   130	        # is ever spliced into shell text.
   131	        run: |
   132	          set -euo pipefail
   133	          TAG="${GITHUB_REF_NAME}"
   134	          DEADLINE=$(( $(date +%s) + 1800 ))
   135	          SELF_CREATED_AT="$(gh api \
   136	            "repos/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}" \
   137	            --jq '.created_at' < /dev/null)"
   138	          echo "inputs: tag=${TAG} head_sha=${GITHUB_SHA} run_id=${GITHUB_RUN_ID}"
   139	          echo "inputs: self_created_at=${SELF_CREATED_AT} deadline_epoch=${DEADLINE}"
   140	
   141	          fetch_payload() {
   142	            # One document: every run for THIS head_sha, each carrying its
   143	            # jobs. A run whose jobs endpoint is unreadable keeps no `jobs`
   144	            # key — the decision function reads that as WAIT, never GRANT.
   145	            if ! gh api --paginate \
   146	                "repos/${GITHUB_REPOSITORY}/actions/runs?head_sha=${GITHUB_SHA}&per_page=100" \
   147	                --jq '.workflow_runs[] | {id, run_attempt, path, event, head_branch, head_sha, created_at, status, conclusion}' \
   148	                > runs.ndjson < /dev/null; then
   149	              # An API error is BLOCK by design (ADR-186: input we cannot
   150	              # verify is blocked, not waved through).
   151	              echo '{"api_error": "runs listing failed"}' > payload.json
   152	              return 0
   153	            fi
   154	            : > runs_with_jobs.ndjson
   155	            while read -r run; do
   156	              [ -n "${run}" ] || continue
   157	              rid="$(printf '%s' "${run}" | jq -r '.id')"
   158	              if ! run_jobs="$(gh api \
   159	                  "repos/${GITHUB_REPOSITORY}/actions/runs/${rid}/jobs?per_page=100" \
   160	                  --jq '[.jobs[] | {name, status, conclusion}]' < /dev/null)"; then
   161	                printf '%s\n' "${run}" >> runs_with_jobs.ndjson
   162	                continue
   163	              fi
   164	              printf '%s' "${run}" \
   165	                | jq -c --argjson jobs "${run_jobs}" '. + {jobs: $jobs}' \
   166	                >> runs_with_jobs.ndjson
   167	            done < runs.ndjson
   168	            jq -c -s '{workflow_runs: .}' runs_with_jobs.ndjson > payload.json
   169	          }
   170	
   171	          attempt=0
   172	          while true; do
   173	            attempt=$(( attempt + 1 ))
   174	            fetch_payload
   175	            set +e
   176	            python3 .claude/scripts/await_release_gate.py \
   177	              --payload-file payload.json \
   178	              --tag "${TAG}" \
   179	              --head-sha "${GITHUB_SHA}" \
   180	              --self-created-at "${SELF_CREATED_AT}" \
   181	              --deadline-epoch "${DEADLINE}"
   182	            rc=$?
   183	            set -e
   184	            case "${rc}" in
   185	              0)
   186	                echo "::notice::release-gate green for ${TAG} at ${GITHUB_SHA} — publish authorised (poll ${attempt})"
   187	                exit 0
   188	                ;;
   189	              3)
   190	                sleep 20
   191	                ;;
   192	              *)
   193	                echo "::error::release-gate did not authorise this publish (decision exit ${rc}, poll ${attempt}) — the printed inputs above name the run and job that were evaluated"
   194	                exit 1
   195	                ;;
   196	            esac
   197	          done
   198	
   199	  publish:
   200	    # PLAN-013 Phase 0 item 0.2 — RC tag guard.
   201	    # RC tags contain `-rc.` (e.g. `v1.4.0-rc.1`). Skip them entirely.
   202	    # Only GA tags (`v1.4.0`) proceed, and those gate through the
   203	    # `production-npm` environment (manual approval).
   204	    # PLAN-153 Wave B item 5 (f): RC posture UNCHANGED — this exclusion
   205	    # is load-bearing (PLAN-013 anti-goals #3/#16) and MUST survive any
   206	    # future edit to this file; the draft `next` dist-tag idea was
   207	    # DROPPED by ratified debate. Pinned by
   208	    # .claude/scripts/tests/test_release_workflow_asserts.py.
   209	    if: "!contains(github.ref, '-rc.')"
   210	    # PLAN-166 W1 item 1: publish only starts after `await-release-gate`
   211	    # proved release.yml's release-gate job green for this exact tag+SHA
   212	    # (default `success()` semantics of `needs:` — an await failure skips
   213	    # this job while the run itself goes red). Deliberate ordering: the
   214	    # production-npm manual-approval prompt appears only AFTER the gate
   215	    # is green. The `already_published` guard stays below, in this job.
   216	    needs: await-release-gate
   217	    runs-on: ubuntu-latest
   218	    environment: production-npm
   219	    timeout-minutes: 8
   220	    steps:
   221	      - name: Checkout tag
   222	        # SHA-pinned (Sprint 7 Dependabot bump): actions/checkout@v6.0.2
   223	        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd
   224	        with:
   225	          fetch-depth: 0
   226	
   227	      - name: Setup Node 20
   228	        # SHA-pinned: actions/setup-node@v4.1.0
   229	        uses: actions/setup-node@48b55a011bda9f5d6aeb4c2d9c7362e8dae4041e
   230	        with:
   231	          node-version: "20"
   232	          registry-url: "https://registry.npmjs.org"
   233	
   234	      - name: Upgrade npm CLI for Trusted Publishing (OIDC)
   235	        # PLAN-158 W1 (debate, all 3 critics): Node 20 bundles npm 10.x,
   236	        # which does NOT implement the trusted-publishing token exchange —
   237	        # without this step the OIDC publish dies ENEEDAUTH at GA, and
   238	        # there is no earlier proof point (RC tags skip this workflow
   239	        # entirely). npm >=11.5.1 is the first trusted-publishing-GA CLI.
   240	        run: |
   241	          set -euo pipefail
   242	          npm install -g npm@^11.5.1
   243	          NPM_V="$(npm --version)"
   244	          case "$NPM_V" in
   245	            10.*|11.0.*|11.1.*|11.2.*|11.3.*|11.4.*|11.5.0)
   246	              echo "::error::npm $NPM_V < 11.5.1 — trusted publishing unsupported"
   247	              exit 1
   248	              ;;
   249	          esac
   250	          echo "OK: npm $NPM_V (>=11.5.1, trusted-publishing capable)"
   251	
   252	      - name: Verify VERSION matches tag
   253	        run: |
   254	          set -euo pipefail
   255	          TAG="${GITHUB_REF_NAME}"
   256	          VERSION_FILE="$(tr -d '[:space:]' < VERSION)"
   257	          EXPECTED="${TAG#v}"
   258	          if [[ "$VERSION_FILE" != "$EXPECTED" ]]; then
   259	            echo "::error::VERSION ($VERSION_FILE) does not match tag ($TAG → $EXPECTED)"
   260	            exit 1
   261	          fi
   262	          echo "OK: VERSION=$VERSION_FILE matches tag=$TAG"
   263	
   264	      - name: Verify npm/package.json version matches VERSION
   265	        run: |
   266	          set -euo pipefail
   267	          PKG_VERSION=$(node -p "require('./npm/package.json').version")
   268	          VERSION_FILE="$(tr -d '[:space:]' < VERSION)"
   269	          if [[ "$PKG_VERSION" != "$VERSION_FILE" ]]; then
   270	            echo "::error::npm/package.json version ($PKG_VERSION) does not match VERSION ($VERSION_FILE)"
   271	            exit 1
   272	          fi
   273	          echo "OK: npm/package.json version=$PKG_VERSION matches VERSION"
   274	
   275	      - name: Verify zero runtime dependencies
   276	        run: |
   277	          set -euo pipefail
   278	          DEP_COUNT=$(node -p "Object.keys(require('./npm/package.json').dependencies || {}).length")
   279	          if [[ "$DEP_COUNT" -ne 0 ]]; then
   280	            echo "::error::ceo-orchestration must ship with 0 runtime dependencies (got $DEP_COUNT)"
   281	            exit 1
   282	          fi
   283	          echo "OK: ceo-orchestration has zero runtime dependencies"
   284	
   285	      - name: Stage bundle into npm/
   286	        # The npm package needs the framework source tree relative to npm/.
   287	        # Copy (don't symlink — npm pack walks symlinks unpredictably across hosts).
   288	        # PLAN-152 tarball-01: SELECTIVE staging. The root .npmignore is INERT
   289	        # (package.json "files" whitelist takes precedence in npm-packlist), so
   290	        # exclusion must happen at stage time. Framework-internal artifacts
   291	        # (test harness, fixture corpora, eval/, red-team corpus, numbered plan
   292	        # trees, _lib/testing.py + _lib/test_isolation.py per the PLAN-120
   293	        # contract install.sh already honors) must NOT ship. Kept deliberately:
   294	        # .claude/plans/ schemas + README + examples/ (install.sh provisions
   295	        # them) and .claude/policies/fixtures/ (install.sh PLAN-014 A.8 ships
   296	        # the policy bundle including fixtures).
   297	        run: |
   298	          set -euo pipefail
   299	          RSYNC_EXCLUDES=(
   300	            --include='.claude/policies/fixtures/'

--- release changed segment ---
   690	              exit 0
   691	            fi
   692	            echo "::error::verdict file missing at $VERDICT_FILE — step 15 blocks release"
   693	            exit 1
   694	          fi
   695	          # S104 redesign: resolve PARENT_SHA = parent of the verdict-file
   696	          # commit. The tag commit (${GITHUB_SHA}) is what we're releasing,
   697	          # and the verdict file at $VERDICT_FILE either:
   698	          #   (a) was committed in the tag commit itself → parent = ${GITHUB_SHA}^
   699	          #   (b) was committed earlier (multi-commit prep) → parent = git log of file
   700	          # We use (b)'s general form: find the commit that introduced the
   701	          # current verdict file, then take its parent. This handles both
   702	          # single-commit-with-verdict and multi-commit-prep flows.
   703	          VERDICT_FILE_COMMIT=$(git log -n1 --format=%H -- "$VERDICT_FILE")
   704	          if [ -z "$VERDICT_FILE_COMMIT" ]; then
   705	            echo "::error::cannot resolve commit for $VERDICT_FILE — step 15 fails"
   706	            exit 1
   707	          fi
   708	          PARENT_SHA=$(git rev-parse "${VERDICT_FILE_COMMIT}^" 2>/dev/null || echo "")
   709	          if [ -z "$PARENT_SHA" ]; then
   710	            echo "::error::cannot resolve parent of $VERDICT_FILE_COMMIT — step 15 fails"
   711	            exit 1
   712	          fi
   713	          echo "::notice::S104 bind: VERDICT_FILE_COMMIT=$VERDICT_FILE_COMMIT, PARENT_SHA=$PARENT_SHA"
   714	          # When transition mode is on, allow parent_sha mismatch (skip bind)
   715	          # by passing empty string. Default is hard-bind on PARENT_SHA.
   716	          PARENT_SHA_ARG="$PARENT_SHA"
   717	          if [ "${CEO_PAIR_RAIL_VERDICT_OPTIONAL:-0}" = "1" ]; then
   718	            PARENT_SHA_ARG=""
   719	          fi
   720	          python3 .github/scripts/validate-pair-rail-verdict.py \
   721	            --verdict-file "$VERDICT_FILE" \
   722	            --parent-sha "$PARENT_SHA_ARG" \
   723	            --release-tag "${GITHUB_REF_NAME}" \
   724	            --max-age-hours 24 \
   725	            --recompute-inputs-hash \
   726	            --codex-cli-pin-file .claude/governance/codex-cli-pin.txt \
   727	            --codex-cli-binary-sha256-file .claude/governance/codex-cli-binary-sha256.txt \
   728	            --codex-pin-manifest-file .claude/governance/codex-cli-pin-manifest.json \
   729	            --inputs-hash-paths-file .claude/governance/pair-rail-inputs-hash-manifest.txt
   730	
   731	      # ==========================================================
   732	      # PLAN-166 W1-B — verdict delta + ancestry gate (F2 server side)
   733	      # ==========================================================
   734	      # Re-pass findings r15 + r17 + r18 (PLAN-166), debate r3 scoped VETO.
   735	      #
   736	      # WHY A SEPARATE STEP: the step-15 neighbourhood above carries two
   737	      # escape hatches keyed to CEO_PAIR_RAIL_VERDICT_OPTIONAL —
   738	      # `continue-on-error:` on the step itself, and an empty
   739	      # `--parent-sha ""` bind (the validator only binds the field when
   740	      # args.parent_sha is non-empty). Inheriting that neighbourhood would
   741	      # inherit the switch. This step therefore:
   742	      #   - carries NO continue-on-error;
   743	      #   - FAILS CLOSED when CEO_PAIR_RAIL_VERDICT_OPTIONAL=1: in that
   744	      #     mode step 15 skipped the parent_sha bind, so the anchor these
   745	      #     asserts hang off was never validated — there is no transition
   746	      #     mode here, by design;
   747	      #   - re-derives and re-binds parent_sha ITSELF (non-empty, 40-hex,
   748	      #     equal to the verdict's `parent_sha:` read with the SAME parser
   749	      #     the local tag guard uses) — independent of step 15's outcome,
   750	      #     which also closes the legacy commit_sha fallback (the
   751	      #     validator downgrades a missing parent_sha to an ADVISORY when
   752	      #     a legacy commit_sha is present; this step does not);
   753	      #   - reuses .claude/scripts/local/_release_tag_guard.py for the
   754	      #     delta decision — the module marks itself as the reference
   755	      #     implementation; the semantics are NEVER re-implemented in
   756	      #     bash (single source of the decision logic);
   757	      #   - asserts ancestry on origin/main of BOTH the reviewed parent
   758	      #     AND GITHUB_SHA itself (r18: parent-only lets the
   759	      #     tag-without-push scenario — verdict V over parent P, tag
   760	      #     pushed, V never reaches main — pass with P ancestral and V
   761	      #     orphaned).
   762	      #
   763	      # THE INVARIANT (one sentence): nothing landed after what the
   764	      # re-pass reviewed, other than the verdict for THIS tag and the
   765	      # evidence it pins by name AND content (sha256 of MANIFEST.sha256
   766	      # in the signed verdict + `shasum -c` over the evidence set).
   767	      #
   768	      # PINNED ORDER (asserted structurally by the W1B* classes of
   769	      # test_release_workflow_asserts.py, WaveB5 pattern):
   770	      #   Verify tag GPG signature → Validate pair-rail verdict →
   771	      #   delta → ancestry.
   772	      # Do not reorder, do not merge into step 15.
   773	      - name: Verify verdict delta + ancestry (fail-closed)
   774	        env:
   775	          CEO_PAIR_RAIL_VERDICT_OPTIONAL: ${{ vars.CEO_PAIR_RAIL_VERDICT_OPTIONAL || '0' }}
   776	        run: |
   777	          set -euo pipefail
   778	          # (0) No transition mode: with the var on, the parent_sha bind
   779	          # upstream was skipped — refuse to certify against an
   780	          # unvalidated anchor. Fail closed, loudly.
   781	          if [ "${CEO_PAIR_RAIL_VERDICT_OPTIONAL}" = "1" ]; then
   782	            echo "::error::CEO_PAIR_RAIL_VERDICT_OPTIONAL=1 is set, but the delta+ancestry gate has no transition mode — it fails closed by design (PLAN-166 debate r3). Unset the repo variable (gh variable delete CEO_PAIR_RAIL_VERDICT_OPTIONAL) and re-run."
   783	            exit 1
   784	          fi
   785	          TAG="${GITHUB_REF_NAME}"
   786	          VERDICT_FILE=".claude/governance/pair-rail-verdict-${TAG}.md"
   787	          if [ ! -f "$VERDICT_FILE" ]; then
   788	            echo "::error::no signed verdict at $VERDICT_FILE — the delta+ancestry gate has no optional mode; the re-pass verdict for THIS tag must be committed on the tagged tree."
   789	            exit 1
   790	          fi
   791	          # (1) Checkout sanity: every assert below anchors on HEAD, so
   792	          # HEAD must BE the tagged commit this run is about.
   793	          HEAD_SHA="$(git rev-parse HEAD)"
   794	          if [ "$HEAD_SHA" != "${GITHUB_SHA}" ]; then
   795	            echo "::error::checkout HEAD ($HEAD_SHA) != GITHUB_SHA (${GITHUB_SHA}) — refusing to assert against the wrong tree"
   796	            exit 1
   797	          fi
   798	          # (2) Independent parent_sha bind — non-empty by construction,
   799	          # controlled by no variable. Same derivation as step 15 (parent
   800	          # of the commit that introduced the verdict file); the verdict
   801	          # field is read with the SAME parser the local tag guard uses
   802	          # (_parse_verdict), so two readers of the same signed file
   803	          # cannot disagree about what it says.
   804	          VERDICT_FILE_COMMIT="$(git log -n1 --format=%H -- "$VERDICT_FILE")"
   805	          if [ -z "$VERDICT_FILE_COMMIT" ]; then
   806	            echo "::error::cannot resolve the commit that introduced $VERDICT_FILE — refusing an empty bind"
   807	            exit 1
   808	          fi
   809	          PARENT_SHA="$(git rev-parse "${VERDICT_FILE_COMMIT}^" 2>/dev/null || echo "")"
   810	          if [ -z "$PARENT_SHA" ]; then
   811	            echo "::error::cannot resolve parent of ${VERDICT_FILE_COMMIT} — refusing an empty bind"
   812	            exit 1
   813	          fi
   814	          python3 - "$VERDICT_FILE" "$PARENT_SHA" <<'PYBIND'
   815	          import importlib.util
   816	          import io
   817	          import re
   818	          import sys
   819	
   820	          verdict_path, expected = sys.argv[1], sys.argv[2]
   821	          if not re.match(r"\A[0-9a-f]{40}\Z", expected):
   822	              sys.exit("FAIL: derived parent %r is not a 40-hex SHA" % expected)
   823	          spec = importlib.util.spec_from_file_location(
   824	              "release_tag_guard", ".claude/scripts/local/_release_tag_guard.py"
   825	          )
   826	          mod = importlib.util.module_from_spec(spec)
   827	          spec.loader.exec_module(mod)
   828	          with io.open(verdict_path, encoding="utf-8") as fh:
   829	              fields = mod._parse_verdict(fh.read())
   830	          declared = fields.get("parent_sha")
   831	          if declared != expected:
   832	              sys.exit(
   833	                  "FAIL: verdict parent_sha %r != parent of the verdict-file "
   834	                  "commit (%s) — the anchor was not validated with a "
   835	                  "non-empty bind; a legacy commit_sha fallback does NOT "
   836	                  "count here." % (declared, expected)
   837	              )
   838	          print("  ok   parent_sha bind: %s (derived independently of step 15)" % expected)
   839	          PYBIND
   840	          # (3) DELTA (r15): git diff <reviewed parent>..<tag commit>
   841	          # must be contained in the CLOSED set pinned in the signed
   842	          # verdict — exact names per tag (never the pair-rail-verdict-*
   843	          # wildcard, never repass-<N>/**), set equality against the
   844	          # evidence MANIFEST.sha256, AND content equality (the verdict
   845	          # pins the manifest's sha256; the guard runs `shasum -c` over
   846	          # it). Any extra path = FAIL. Decision logic lives in the local
   847	          # tag guard module — reused, never re-implemented in bash.
   848	          python3 .claude/scripts/local/_release_tag_guard.py delta \
   849	            --repo . --tag "$TAG"
   850	          # (4) ANCESTRY (r17+r18): both the reviewed parent AND the
   851	          # tagged commit itself must be ancestors of origin/main. The
   852	          # module's ancestry subcommand judges HEAD (== GITHUB_SHA,
   853	          # asserted in (1)) after a FAIL-CLOSED fetch of origin/main —
   854	          # a failed fetch is a stop, never a stale-ref approval. The
   855	          # reviewed parent is then judged against the same freshly
   856	          # fetched ref.
   857	          python3 .claude/scripts/local/_release_tag_guard.py ancestry \
   858	            --repo . --remote origin --branch main
   859	          if git merge-base --is-ancestor "$PARENT_SHA" origin/main; then
   860	            echo "  ok   reviewed parent $PARENT_SHA is an ancestor of origin/main"
   861	          else
   862	            RC=$?
   863	            echo "::error::reviewed parent $PARENT_SHA is not on origin/main (merge-base exit $RC) — the verdict is anchored on a commit main never saw (tag-without-push / orphan-verdict scenario, r17+r18)"
   864	            exit 1
   865	          fi
   866	          echo "OK: verdict delta + ancestry asserts all green for $TAG"
   867	
   868	  publish-release:
   869	    name: Publish GitHub Release + assets
   870	    needs: release-gate
   871	    runs-on: ubuntu-latest
   872	    permissions:
   873	      contents: write
   874	    steps:
   875	      - name: Checkout tag
   876	        # SHA-pinned: actions/checkout@v6.0.2
   877	        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd
   878	        with:
   879	          fetch-depth: 0
   880	      - name: Setup Python 3.11
   881	        # SHA-pinned: actions/setup-python@v6.2.0
   882	        uses: actions/setup-python@a309ff8b426b58ec0e2a45f0f869d46889d02405
   883	        with:
   884	          python-version: "3.11"
   885	      - name: Compute install.sh.sha256 (body excluding self-SHA trailer)
   886	        run: |
   887	          set -euo pipefail
   888	          FILE="scripts/install.sh"
   889	          HASH=$(awk 'NR==FNR{n++; next} FNR < n' "$FILE" "$FILE" | sha256sum | awk '{print $1}')
   890	          printf '%s  install.sh\n' "$HASH" > install.sh.sha256
   891	          echo "install.sh.sha256 = $HASH"
   892	      - name: Generate CycloneDX SBOM
   893	        run: |
   894	          set -euo pipefail
   895	          python3 .claude/scripts/generate-sbom.py --output sbom.cyclonedx.json
   896	      # -----------------------------------------------------------------
   897	      # PLAN-153 Wave B item 5 (d) — templatized release notes.
   898	      # Closes PLAN-152 §Deferred `release-notes-hardcoded-first-release`:
   899	      # the notes string used to hardcode a v1.0.0-only launch sentence,
   900	      # stale for every later tag. Notes are now rendered from

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

exec
/bin/zsh -lc "sed -n '1,320p' .claude/scripts/await_release_gate.py; printf '\\n--- TESTS ---\\n'; sed -n '1,360p' .claude/scripts/tests/test_await_release_gate.py; printf '\\n--- TAG GUARD CLI ---\\n'; sed -n '1,360p' .claude/scripts/local/_release_tag_guard.py" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
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

--- TESTS ---
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

--- TAG GUARD CLI ---
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

exec
/bin/zsh -lc 'grep -R "head_branch" -n .claude .github docs scripts tests 2>/dev/null | head -80' in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 1148ms:
.claude/plans/PLAN-166/debate/round-1/consensus.md:43:`head_branch==<tag GA>` + `head_sha` + conclusão do **job**
.claude/plans/PLAN-166/debate/round-1/security-engineer.md:55:**E** `head_branch == $GITHUB_REF_NAME` (nome da tag) **E**
.claude/plans/PLAN-166/debate/round-1/security-engineer.md:143:   `head_branch == <nome da tag GA>`, `head_sha == <SHA da tag>`, e
.claude/plans/PLAN-166/debate/round-1/security-engineer.md:192:   `head_branch` da rc; (iii) `head_branch` certo mas `head_sha` de outro
.claude/plans/PLAN-166/debate/round-2/security-engineer.md:26:| `head_branch == <nome da tag>` | AC-2: "`head_branch==<tag>`" | ✅ |
.claude/plans/PLAN-166/debate/round-3/devops-engineer.md:106:  contra a lista de fixtures NUNCA-GRANT (head_branch de rc, head_sha de
.claude/plans/PLAN-166/debate/round-3/security-engineer.md:34:  construção, e o `head_branch` permanece como defesa em profundidade, não
.claude/plans/PLAN-166/debate/round-3/security-engineer.md:209:  bind: os quatro fixtures NUNCA-GRANT (head_branch de rc, SHA de outro
.claude/plans/PLAN-166-release-hold-findings-closure.md:73:  `head_branch == <nome da tag>`, `head_sha == GITHUB_SHA`, e **job
.claude/plans/PLAN-166-release-hold-findings-closure.md:604:      `event==push` + `head_branch==<tag>` + `head_sha==GITHUB_SHA` +
.claude/plans/PLAN-166-release-hold-findings-closure.md:616:      head_branch de rc; head_sha de outro commit; workflow errado com
.claude/scripts/tests/test_await_release_gate.py:103:        "head_branch": TAG,
.claude/scripts/tests/test_await_release_gate.py:121:        "head_branch": TAG,
.claude/scripts/tests/test_await_release_gate.py:190:        self._assert_never_grants(release_run(head_branch="v1.3.0-rc.2", id=2001))
.claude/scripts/await_release_gate.py:23:  ``head_branch == <tag>``, ``head_sha == <GITHUB_SHA>``, it is FRESH
.claude/scripts/await_release_gate.py:55:same ``head_sha``/``head_branch``. Polling before the NEW Release run is
.claude/scripts/await_release_gate.py:78:``path`` (or ``workflow_path``), ``event``, ``head_branch``, ``head_sha``,
.claude/scripts/await_release_gate.py:246:        and run.get("head_branch") == ctx.tag
.claude/scripts/await_release_gate.py:383:    parser.add_argument("--tag", required=True, help="tag name, i.e. head_branch of the release run")
.github/workflows/npm-publish.yml:147:                --jq '.workflow_runs[] | {id, run_attempt, path, event, head_branch, head_sha, created_at, status, conclusion}' \

exec
/bin/zsh -lc "git diff -- CLAUDE.md INSTALL.md README.md README.pt-BR.md RELEASE.md docs/ARCHITECTURE.md docs/CTO-GUIDE.md docs/FAQ.md docs/GUIA-COMPLETO.md docs/README.md npm/README.md .claude/governance/pair-rail-verdict-template.md .claude/plans/PLAN-166/W1-approved-draft.md && printf '\\n--- UNTRACKED ADR ---\\n' && sed -n '1,280p' .claude/adr/ADR-155-AMEND-1-delivery-record-ownership.md && printf '\\n--- MARKER ---\\n'; cat .claude/.framework-version" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-5SfMX7AW' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-mTrRTCgW' (errno=Operation not permitted)
diff --git a/.claude/governance/pair-rail-verdict-template.md b/.claude/governance/pair-rail-verdict-template.md
index 94296a3..fcb1865 100644
--- a/.claude/governance/pair-rail-verdict-template.md
+++ b/.claude/governance/pair-rail-verdict-template.md
@@ -18,6 +18,12 @@ parent_sha: <40-char SHA — the commit the verdict was generated AGAINST (paren
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
@@ -30,6 +36,18 @@ findings: []  # List of P0/P1/P2/P3 with file:line if any
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
diff --git a/.claude/plans/PLAN-166/W1-approved-draft.md b/.claude/plans/PLAN-166/W1-approved-draft.md
index 17bd644..cf50f43 100644
--- a/.claude/plans/PLAN-166/W1-approved-draft.md
+++ b/.claude/plans/PLAN-166/W1-approved-draft.md
@@ -194,6 +194,7 @@ Adopter upgrade + ADR + count sweep (revert group B):
   - scripts/_framework_manifest_set.sh
   - scripts/doctor.sh
   - scripts/install.sh
+  - scripts/tests/_parity_classify.py
   - scripts/tests/test-upgrade-spec-ownership.sh
   - scripts/upgrade.sh
 
diff --git a/CLAUDE.md b/CLAUDE.md
index ba8ae08..e0b988c 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -51,7 +51,7 @@ library — you install it *into* an existing repository with
 - **A cross-LLM pair-rail** — a second model (Codex) reviews canonical edits Claude proposes, so no single model is both author and sole reviewer.
 - **A skill library** — **166 skills** ready-made (42 core + 8 frontend + 116 domain).
 - **Governance hooks** — 57 Python hook scripts on disk (46 wired into `.claude/settings.json` (48 event registrations)), built on 68 stdlib-only `_lib/` modules.
-- **188 ADRs** (architecture decision records, `.claude/adr/`) and **27 slash commands** (`.claude/commands/`).
+- **189 ADRs** (architecture decision records, `.claude/adr/`) and **27 slash commands** (`.claude/commands/`).
 
 A note this repo keeps deliberately: **there is no speed claim.** Six
 internal experiments found no general speedup over an optimized solo
diff --git a/INSTALL.md b/INSTALL.md
index e9b7471..480ef7f 100644
--- a/INSTALL.md
+++ b/INSTALL.md
@@ -587,16 +587,24 @@ files. A version bump in `VERSION` carries the SemVer guarantee
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
 
@@ -617,12 +625,41 @@ What gets refreshed:
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
diff --git a/README.md b/README.md
index a247fe0..e04e721 100644
--- a/README.md
+++ b/README.md
@@ -56,7 +56,7 @@ All counts below are verifiable from a clean checkout (see *Verifying the number
 | Hooks wired in `settings.json` | **46** | distinct scripts, 48 event registrations |
 | Shared library modules | **68** | stdlib-only, under `.claude/hooks/_lib/` (excluding the package `__init__.py`) |
 | Slash commands | **27** | under `.claude/commands/` |
-| Architecture decision records | **188** | under `.claude/adr/` |
+| Architecture decision records | **189** | under `.claude/adr/` |
 | Tests | **~14,000 cases** | reported by `pytest --collect-only` across the hook, script, and conformance suites |
 
 The gap between **57 on disk** and **46 wired** is benign: several non-event modules are activated through in-process dispatch (invoked by other hooks) rather than by a direct `settings.json` event registration.
@@ -183,7 +183,7 @@ Don't take the table on faith. From a clean checkout:
 ```bash
 find .claude/skills -name SKILL.md | wc -l        # 166 skills
 ls .claude/commands/*.md | wc -l                  # 27 slash commands
-ls .claude/adr | grep -c '^ADR-'                  # 188 ADRs
+ls .claude/adr | grep -c '^ADR-'                  # 189 ADRs
 python3 -m pytest --collect-only -q | tail -1     # ~14,000 collected cases
 ```
 
diff --git a/README.pt-BR.md b/README.pt-BR.md
index 344f556..3c1c28c 100644
--- a/README.pt-BR.md
+++ b/README.pt-BR.md
@@ -54,7 +54,7 @@ Todas as contagens abaixo são verificáveis a partir de um checkout limpo (veja
 | Hooks ligados em `settings.json` | **46** | scripts distintos, 48 registros de evento |
 | Módulos de biblioteca compartilhada | **68** | apenas stdlib, em `.claude/hooks/_lib/` (excluindo o `__init__.py` do pacote) |
 | Slash commands | **27** | em `.claude/commands/` |
-| Architecture decision records | **188** | em `.claude/adr/` |
+| Architecture decision records | **189** | em `.claude/adr/` |
 | Testes | **~14.000 casos** | reportados por `pytest --collect-only` nas suítes de hook, script e conformidade |
 
 A diferença entre **57 em disco** e **46 ligados** é benigna: vários módulos que não respondem a eventos são ativados via dispatch in-process (invocados por outros hooks), e não por um registro de evento direto em `settings.json`.
@@ -163,7 +163,7 @@ Não acredite na tabela por fé. A partir de um checkout limpo:
 ```bash
 find .claude/skills -name SKILL.md | wc -l        # 166 skills
 ls .claude/commands/*.md | wc -l                  # 27 slash commands
-ls .claude/adr | grep -c '^ADR-'                  # 188 ADRs
+ls .claude/adr | grep -c '^ADR-'                  # 189 ADRs
 python3 -m pytest --collect-only -q | tail -1     # ~14.000 casos coletados
 ```
 
diff --git a/RELEASE.md b/RELEASE.md
index ccae549..4bc6476 100644
--- a/RELEASE.md
+++ b/RELEASE.md
@@ -16,7 +16,7 @@
 > - `cat VERSION` — versão semântica corrente (`1.0.0`)
 > - `git tag -l 'v*' --sort=-creatordate | head -5` — últimas 5 tags
 > - `CHANGELOG.md` — entries por versão
-> - `.github/workflows/release.yml` — release-gate + publish-release (29 steps,
+> - `.github/workflows/release.yml` — release-gate + publish-release (31 steps,
 >   GPG-signed tags)
 >
 > Histórico preservado abaixo apenas como referência de como o
diff --git a/docs/ARCHITECTURE.md b/docs/ARCHITECTURE.md
index af2f07e..d59fb70 100644
--- a/docs/ARCHITECTURE.md
+++ b/docs/ARCHITECTURE.md
@@ -53,7 +53,7 @@ ceo-orchestration/
     │   ├── core/                   # 42 universal backend skills
     │   ├── frontend/               # 8 universal frontend skills
     │   └── domains/                # 116 skills across 33 domain profiles
-    ├── adr/                        # 188 architecture decision records
+    ├── adr/                        # 189 architecture decision records
     └── plans/                      # plan schemas + per-plan working files
 ```
 
@@ -68,7 +68,7 @@ faith — run the commands:
 | Hook registrations | 46 wired into `settings.json`| (parse the `hooks` block of `.claude/settings.json`)      |
 | `_lib` modules     | 68 top-level (140 recursive) | `ls .claude/hooks/_lib/*.py \| grep -v __init__ \| wc -l` |
 | Slash commands     | 27                           | `ls .claude/commands/*.md \| wc -l`                       |
-| ADRs               | 188                          | `ls .claude/adr/ADR-*.md \| wc -l`                        |
+| ADRs               | 189                          | `ls .claude/adr/ADR-*.md \| wc -l`                        |
 | SPEC/v1 files      | 32 (28 `*.schema.md`)        | `ls SPEC/v1/*.md \| wc -l`                                |
 | Test files         | ~730                         | `git ls-files '*test_*.py' '*_test.py' \| wc -l`          |
 | Collected cases    | ~14k parametrized cases      | `make test-collect` (pytest `--collect-only`)             |
@@ -234,7 +234,7 @@ this repository happens to implement it today*. An install pins a SPEC version;
 internal refactors that keep the schemas stable do not break adopters.
 
 Decisions that shape these contracts are recorded as Architecture Decision
-Records in `.claude/adr/` (188 to date), with a documented lifecycle
+Records in `.claude/adr/` (189 to date), with a documented lifecycle
 (PROPOSED → ACCEPTED, plus SUPERSEDED / RETRACTED).[^adr]
 
 The repository also includes a TLA+ specification of the core state machine
diff --git a/docs/CTO-GUIDE.md b/docs/CTO-GUIDE.md
index 812a4aa..b0e59bc 100644
--- a/docs/CTO-GUIDE.md
+++ b/docs/CTO-GUIDE.md
@@ -41,7 +41,7 @@ documentation bug.
 |---|---|---|
 | Python tests collected | ~14,000 | `make test-collect` (or `python3 -m pytest --collect-only -q \| tail -1` — pytest.ini pins the testpath roots) |
 | Test files | ~730 | `git ls-files '*test_*.py' '*_test.py' \| wc -l` |
-| ADRs shipped | 188 | `ls .claude/adr/ADR-*.md \| wc -l` |
+| ADRs shipped | 189 | `ls .claude/adr/ADR-*.md \| wc -l` |
 | SPEC/v1 files | 32 (28 `*.schema.md`) | `ls SPEC/v1/*.md \| wc -l` |
 | Workflows | 21 | `ls .github/workflows/*.yml \| wc -l` |
 | GitHub Actions SHA-pinned refs | every `uses:` pinned | `grep -rEc 'uses: [^#]+@(v[0-9]+\|main\|master\|latest)\s*$' .github/workflows/*` — must be 0 everywhere |
@@ -109,7 +109,7 @@ grep -rE 'urllib|requests|httpx|socket\.' .claude/hooks/check_*.py
 ls .claude/hooks/check_*.py .claude/hooks/audit_log.py
 
 # Every ADR title
-grep -h '^# ADR-' .claude/adr/ADR-*.md | sort             # 188 ADRs on disk
+grep -h '^# ADR-' .claude/adr/ADR-*.md | sort             # 189 ADRs on disk
 
 # SPEC/v1 published contract
 ls SPEC/v1/*.schema.md                                    # 28 schema files
diff --git a/docs/FAQ.md b/docs/FAQ.md
index e0e628f..ad3ad62 100644
--- a/docs/FAQ.md
+++ b/docs/FAQ.md
@@ -105,7 +105,7 @@ Don't take the README table on faith. From a clean checkout:
 ```bash
 find .claude/skills -name SKILL.md | wc -l        # 166 skills (42 core + 8 frontend + 116 domain)
 ls .claude/commands/*.md | wc -l                  # 27 slash commands
-ls .claude/adr | grep -c '^ADR-'                  # 188 ADRs
+ls .claude/adr | grep -c '^ADR-'                  # 189 ADRs
 python3 -m pytest --collect-only -q | tail -1     # ~14,000 collected cases
 ```
 
diff --git a/docs/GUIA-COMPLETO.md b/docs/GUIA-COMPLETO.md
index 41ca561..3aaf2cc 100644
--- a/docs/GUIA-COMPLETO.md
+++ b/docs/GUIA-COMPLETO.md
@@ -164,7 +164,7 @@ For those, use Claude Code directly. Spawn overhead > benefit.
   is deferred to v2+.
 - **Audited.** Every spawn, every decision, every veto becomes a JSONL
   event.
-- **Governed by ADR.** 188 ADRs document every architectural decision.
+- **Governed by ADR.** 189 ADRs document every architectural decision.
 
 ### It is NOT:
 - **A product.** No UI, no SaaS, no login.
@@ -1222,7 +1222,7 @@ mv .claude .claude.disabled
 - `.claude/frontend-team.md` — frontend roster
 - `.claude/pitfalls-catalog.yaml` — universal pitfalls
 - `.claude/task-chains.yaml` — 6 universal workflows
-- `.claude/adr/` — 188 Architecture Decision Records
+- `.claude/adr/` — 189 Architecture Decision Records
 - `.claude/plans/` — active plans + archive
 - `.claude/skills/core/` — 42 universal skills
 - `.claude/skills/frontend/` — 8 frontend skills
diff --git a/docs/README.md b/docs/README.md
index 03e3350..4a50bbb 100644
--- a/docs/README.md
+++ b/docs/README.md
@@ -78,7 +78,7 @@ full set of commands; here is the summary you can spot-check in a minute.
 | Hook scripts on disk | **57** Python scripts | count `*.py` in `.claude/hooks/` |
 | Hooks registered | **46** distinct scripts (48 event registrations) | inspect `.claude/settings.json` |
 | Slash commands | **27** | count `*.md` in `.claude/commands/` |
-| Architecture decision records | **188** | count `ADR-*.md` in `.claude/adr/` |
+| Architecture decision records | **189** | count `ADR-*.md` in `.claude/adr/` |
 | Shared library modules | **68** stdlib-only (top-level `_lib/`) | count `*.py` in `.claude/hooks/_lib/` |
 | Tests | **~730 test files**; `make test-collect` (pytest `--collect-only`) reports **~14,000** collected cases | `make test-collect` |
 
diff --git a/npm/README.md b/npm/README.md
index 9203de5..a19a95f 100644
--- a/npm/README.md
+++ b/npm/README.md
@@ -56,7 +56,7 @@ All counts below are verifiable from a clean checkout (see *Verifying the number
 | Hooks wired in `settings.json` | **46** | distinct scripts, 48 event registrations |
 | Shared library modules | **68** | stdlib-only, under `.claude/hooks/_lib/` (excluding the package `__init__.py`) |
 | Slash commands | **27** | under `.claude/commands/` |
-| Architecture decision records | **188** | under `.claude/adr/` |
+| Architecture decision records | **189** | under `.claude/adr/` |
 | Tests | **~14,000 cases** | reported by `pytest --collect-only` across the hook, script, and conformance suites |
 
 The gap between **57 hook scripts** on disk and **46 wired** is benign: several non-event modules are activated through in-process dispatch (invoked by other hooks) rather than by a direct `settings.json` event registration.
@@ -119,7 +119,7 @@ Don't take the table on faith. From a clean checkout:
 ```bash
 find .claude/skills -name SKILL.md | wc -l        # 166 skills
 ls .claude/commands/*.md | wc -l                  # 27 slash commands
-ls .claude/adr | grep -c '^ADR-'                  # 188 ADRs
+ls .claude/adr | grep -c '^ADR-'                  # 189 ADRs
 python3 -m pytest --collect-only -q | tail -1     # ~14,000 collected cases
 ```
 

--- UNTRACKED ADR ---
# ADR-155-AMEND-1 — Framework ownership derives from the REGISTERED DELIVERY; SPEC/v1 joins the upgrade surface (forced route); root VERSION stays out — deliberately


---
adr_id: ADR-155-AMEND-1
title: Install/upgrade ownership model — every conditional framework-owned entry (PROTOCOL.md, SPEC/v1, .claude/.framework-version) derives from the registered delivery record, never from ceremony alone or file presence; SPEC/v1 gets a FORCED refresh route with pristine-content legacy migration; the root VERSION is exempt from upgrade forever
status: ACCEPTED
amends: ADR-155
proposed_at: 2026-08-05
proposed_by: CEO (PLAN-166 F3 — ADR-103 re-pass NO-GO finding on v1.3.0-rc.1; debate rounds r6/r7/r8/r9/r13/r17/r19/r20)
session_origin: 2026-08-05 (S295, W1 ceremony pack)
accepted_at: 2026-08-05
authorization: PLAN-166 W1 Owner-GPG ceremony — this file reaches the canonical tree ONLY via that ceremony; a landed copy implies the gate fired
risk_tier: A
debate_required: true
debate_record: .claude/plans/PLAN-166/debate/ (3 rounds, 3 scoped VETOs raised and LIFTED with literal verification) + codex pair-rail 20 rounds (~55 findings applied)
related_plans: [PLAN-138, PLAN-153, PLAN-161, PLAN-166]
related_adrs: [ADR-155]
---

## §1 What this amendment changes

ADR-155 built the baseline-manifest engine on one shared enumeration
(`scripts/_framework_manifest_set.sh`) and enumerated the root
`PROTOCOL.md` **unconditionally** (decision (i)). The v1.3.0-rc.1 re-pass
(PLAN-166 finding F3) showed that unconditional — or ceremony-only —
enumeration is itself an ownership defect, and that `SPEC/v1` (shipped by
`install.sh` since PLAN-087 but never enumerated, never refreshed) had
become a stale, unwatched contract on every upgraded adopter. This
amendment decides four things:

1. **The delivery-record ownership rule (general).** Every CONDITIONAL
   entry of the framework-owned enumeration — `PROTOCOL.md`, `SPEC/v1`
   and the new `.claude/.framework-version` marker — derives from the
   **registered delivery**, never from the ceremony alone and never from
   file presence (§3).
2. **`SPEC/v1` joins the upgrade surface via a FORCED route** — not the
   generic `backup_and_replace` classified walk — with a deterministic
   pristine-content migration for v1.2-and-earlier legacy installs (§4).
3. **`.claude/.framework-version`** becomes a tracked file of the
   framework repo, written explicitly on install (`install_one`,
   skip-if-exists) and force-refreshed + read-back-validated on upgrade;
   marker-first readers consult the SAME delivery record before trusting
   it (§5).
4. **The root `VERSION` file stays OUT of the upgrade surface and OUT of
   the enumeration — permanently and deliberately** (§2). This section
   exists so the next maintainer does not "fix" the asymmetry and reopen
   the class.

## §2 Why root VERSION is exempt — do not repair this asymmetry

`install.sh`'s `install_one` is **skip-if-exists**: on an adopter repo
that already carries its own `VERSION` (most real repos version
themselves), the framework **never wrote that file**. Any upgrade-side
refresh of `VERSION` — `backup_and_replace` or a forced route — would
therefore TAKE an adopter-owned file. That is not hypothetical: it is the
exact shape of the S238 acme data-loss ("the verified worst case" in
ADR-155's own words), and the baseline classifier would *confirm* the
clobber rather than prevent it, because the recorded baseline would hash
the framework's value (trap C.5, documented inside
`_framework_manifest_set.sh`).

So the asymmetry is: **every other framework-derived surface refreshes on
upgrade; `VERSION` does not, ever.** The consequence — the root `VERSION`
of an upgraded adopter reports the ORIGINAL install version forever — is
absorbed by the marker (§5) and named in `INSTALL.md` (the forensic-anchor
section now prefers `.claude/.framework-version` with a `VERSION`
fallback). A future maintainer who notices "upgrade refreshes the marker
but not VERSION — inconsistent!" is looking at a decided invariant, not an
oversight. Reopening it requires amending THIS amendment.

Inside the framework repo itself nothing changes: every framework-repo
gate (`check-canonical-doc-freshness.py`, `verify-counts.sh`,
`check_tier_a_spec_version_drift`) keeps reading `VERSION` as the
authority. The marker-first preference is exclusive to readers operating
on an ADOPTER tree — today, `.claude/scripts/check-framework-updates.sh`
(without it, the checker re-reads the stale root `VERSION` post-upgrade,
exits `behind-minor` and demands the same upgrade in an eternal loop —
r8). `check_tier_a_npm_version_match` deliberately does NOT adopt the
marker: in an adopter tree the root `package.json` is the APP's, and
comparing the framework marker against the app version would be a
permanent false-red; that check keeps its VERSION×package.json semantics
(or skips when VERSION is absent).

## §3 The delivery-record ownership rule

**"Delivered" means REGISTERED ACTUAL DELIVERY, not ceremony (r17), and
not file presence (r7/r13):**

- A `--ceremony user` install SKIPS `install_spec_v1`,
  `install_version` and `install_protocol_pointer` (WS4 guards). If the
  enumeration emitted those paths unconditionally,
  `write_install_manifest` would hash the ADOPTER's own `SPEC/v1` or root
  `PROTOCOL.md` as framework-owned — and a later `uninstall.sh` (which
  removes manifest-recorded, hash-matching files) could DELETE the
  adopter's files (r7/r13).
- Ceremony-conditional enumeration is still not enough: on a
  `maintainer` install where the destination ALREADY had its own
  `SPEC/v1`, `install_one` EXISTS-skips — the file on disk is the
  adopter's, under a maintainer ceremony (r17).

Mechanics (both writers, one reader):

- `install.sh` flips `_DELIVERED_{SPEC,PROTOCOL,MARKER}` only where the
  write ACTUALLY happened (`install_one` reports COPIED/LINKED via
  `INSTALL_ONE_WROTE`; the pointer heredoc sets the flag on its own write
  path, unreachable from the pre-existing early-return), journals a
  `delivered_*` op into `.install-state.json`, and exports the flags as
  `FMS_DELIVERED_*` to the shared enumeration.
- The **baseline manifest** (`.claude/.install-manifest.sha256`) is
  thereby the persistent delivery record: it carries records for the
  three conditional paths **iff** they were delivered.
- `upgrade.sh` resolves prior ownership from the pre-upgrade baseline
  records (`_baseline_has_spec_record` / `_baseline_has_marker_record` /
  the existing `_baseline_lookup "PROTOCOL.md"`), refreshes what it owns,
  and re-exports the flags for the post-upgrade C.7 rewrite.
- `doctor.sh` resolves the SAME flags from the sanitized baseline —
  never from ceremony — before its orphan-scan enumeration: only-ceremony
  would re-include paths a user install skipped and `--strict-orphans`
  would flag the adopter's own files as orphans (r19); a blanket
  maintainer default would do the same, and a blanket user default would
  hide a delivered SPEC from a maintainer (r9 P2).
- The enumeration's fail direction is pinned: an unset flag means NOT
  enumerated. **Under-claiming ownership is recoverable (a file goes
  unwatched); over-claiming is the delete-the-adopter's-file class.**

The upgrade-side ceremony read is **replay-independent** (r9):
`upgrade.sh --no-replay` sets `REPLAY=0` and skips
`_read_install_state_request` entirely, so a ceremony that rode the
replay would silently revert a user install to maintainer under the
documented `--no-replay` flag. A dedicated `_read_install_state_ceremony`
reader always runs, validates against the closed enum
`{maintainer, user}`, and **fails open to `maintainer`** when the state
is absent/unreadable (all pre-Wave-B installs) — the pre-existing
behavior, named as a consequence in `INSTALL.md`. The same read gates
`_refresh_protocol_pointer`, which previously ran unconditionally and
`cat >`-created a root `PROTOCOL.md` that a user install deliberately
never has (the latent bug the PLAN-166 F4 tree-comparison e2e exposes).

## §4 SPEC/v1: forced route + pristine-content legacy migration

The generic route cannot carry the SPEC. For a directory target with a
baseline, `backup_and_replace` runs the per-file classified walk — which
PRESERVES adopter edits. From the **second** upgrade on (baseline then
contains SPEC records), an edited SPEC would classify ADOPTER-CUSTOMIZED
and the stale-contract failure would return (r6). The declared semantics
(OQ-3): `SPEC/v1` is the published compliance CONTRACT — an adopter edit
is a **fork of the contract**, not a customization. Three-way merge is
complexity without a consumer; refuse-and-instruct would block every
upgrade that ships a SPEC change. Hence `_refresh_spec_contract`:
framework-owned ⇒ backup whole tree to `.claude.bak/<ts>/SPEC/v1` +
replace wholesale; user-ceremony installs never receive it.

**Legacy migration (r20).** v1.2-and-earlier installs have NO delivery
record for SPEC (the enumeration never included it), so
framework-installed and adopter-authored `SPEC/v1` are indistinguishable
by record. The ambiguity resolves by CONTENT: the target tree's
fingerprint (sha256 over the `LC_ALL=C`-sorted `"<sha256(file)>  <relpath>"`
lines of every file under `SPEC/v1`) is compared against the PRISTINE
fingerprints of every SPEC/v1 the framework shipped at **v1.2.0 and
earlier** — nine tags, three distinct trees, derived deterministically
from pinned tag content (`git ls-tree` + `git show`; the derivation
command is embedded next to the constants in `upgrade.sh`):

| pristine fingerprint (sha256) | shipped by |
|---|---|
| `a4a4504a224d72a975a853dd71a75d8e678fef034a70deb49df291dbb712c161` | v1.0.0, v1.0.1, v1.0.1-rc.1 |
| `94aa62f781285ce4897ad1220edf15e97b4e9d7b629f9f7ba3389da5d45f22b1` | v1.1.0, v1.1.0-rc.1 |
| `469a49238867be181490214305b43bc7299f2bae3ef0b282a5452f6caf327f0b` | v1.2.0, v1.2.0-rc.1, v1.2.0-rc.2, v1.2.0-rc.3 |

Match ⇒ framework-owned (byte-identical to a shipped release; the forced
refresh loses nothing) ⇒ refresh + named NOTE. No match ⇒ ADOPTER-FORK ⇒
**preserve in place** + snapshot to `.claude.bak/<ts>/SPEC/v1` + named
WARNING with the hand-refresh instruction. A partial/unhashable tree
never produces a fingerprint (fail toward preserve). Both legacy cases
are fixtures; the pristine-match branch is additionally exercised
end-to-end by the F4 install-v1.2.0→upgrade comparison job.

## §5 The marker: forced+validated write, record-gated readers

`.claude/.framework-version` is a **tracked file of the framework repo**
(one line, byte-identical to `VERSION`) — not generated-only-at-destination,
so the release protections are real and unconditional: the version bump
writes it as its 12th site, `verify-counts.sh` cross-checks it against
`VERSION` in every release, and `release.yml` asserts marker == VERSION
fail-closed. In the enumeration it is a NORMAL file entry (the
`FMS_HASH_ROOT` baseline rewrite preserves it with no special-case),
conditional on delivery like the other two.

Delivery is by **explicit writes on both paths** (the enumeration never
delivers — it only records; r7): `install_one ".claude/.framework-version"`
on install (skip-if-exists ⇒ a pre-existing adopter marker is NOT
delivered), and a **forced + read-back-validated** rewrite on upgrade
(differing pre-existing copy backed up first; a write that fails
validation is NOT recorded as delivered). It lives inside `.claude/`, so
both ceremonies receive it (the WS4 guard only forbids root files) and it
is committable like the rest of `.claude/`.

**Every marker-first reader consults the SAME record** (r20):
`check-framework-updates.sh` trusts the marker only when the baseline
manifest carries its delivery record, else falls back to `VERSION` — on a
target where the marker pre-existed and was skipped, an unconditional
read would report a stale version in a loop.

## §6 Enforcement

- `scripts/tests/test-upgrade-spec-ownership.sh` — record-owned forced
  refresh with backup (the 2nd-upgrade scenario), user-ceremony +
  `--no-replay` skip, legacy adopter-fork preserve, marker delivery +
  pre-existing-marker fallback, doctor orphan-scan in both modes,
  update-checker no-loop regression (AC-3).
- The PLAN-166 F4 e2e (`smoke-install.yml`) compares install-built vs
  upgrade-built trees per ceremony mode; its historical leg
  (install v1.2.0 → upgrade) exercises the pristine-match migration.
- `_framework_manifest_set.sh`, `install.sh`, `upgrade.sh` remain
  `_CANONICAL_GUARDS` surfaces; this amendment's edits land only via the
  PLAN-166 W1 Owner-GPG ceremony.

## Consequences

- **(+)** A `--ceremony user` install can never have its own `SPEC/v1`,
  root `PROTOCOL.md` or marker inventoried as framework-owned — closing
  the uninstall-deletes-adopter-files corridor (r7/r13/r17).
- **(+)** Upgraded adopters get a fresh SPEC contract every upgrade, with
  fork preservation and a deterministic legacy migration.
- **(+)** Post-upgrade version reporting is truthful (marker), without
  ever touching the adopter's root `VERSION`.
- **(−)** Pre-Wave-B installs (no `.install-state.json`) are treated as
  `maintainer` on upgrade — fail-open, named in `INSTALL.md`; a user-mode
  pre-Wave-B adopter must re-run `install.sh --ceremony user` once to
  record the ceremony.
- **(−)** The delivery record inherits the baseline manifest's trust
  class: target-side, UNSIGNED, advisory (ADR-155 Consequences). A
  tampered record can add/remove ownership — the fail direction on a
  MISSING record is preserve/fallback (today's behavior), never a new
  escalation.
- **(~)** An adopter whose fork of `SPEC/v1` is byte-identical to a
  shipped release is claimed as framework-owned by the legacy migration —
  accepted: the forced refresh is content-preserving up to the shipped
  bytes they already had.

--- MARKER ---
1.3.0

exec
/bin/zsh -lc "nl -ba scripts/install.sh | sed -n '840,930p;1280,1385p;1880,1970p;2260,2470p'; printf '\\n--- UPGRADE INIT/SOURCING ---\\n'; nl -ba scripts/upgrade.sh | sed -n '1,240p;760,990p;3010,3190p'" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
   840	# and hard-fails (exit 1, picked up by the rollback trap) if any existing
   841	# component is a symlink. Legitimate `--mode link` installs symlink only
   842	# the LEAF, never a parent, so this never trips them.
   843	_assert_no_symlink_parents() {
   844	  local rel_path="$1"
   845	  # Only validate paths we write under $TARGET.
   846	  local parent_rel
   847	  parent_rel="$( dirname "$rel_path" )"
   848	  [[ "$parent_rel" == "." ]] && return 0
   849	  local cur="$TARGET"
   850	  local IFS='/'
   851	  local comp
   852	  for comp in $parent_rel; do
   853	    [[ -z "$comp" || "$comp" == "." ]] && continue
   854	    cur="$cur/$comp"
   855	    if [[ -L "$cur" ]]; then
   856	      echo "::error::refusing install — symlinked path component under target: $cur" >&2
   857	      echo "::error::an intermediate component of '$rel_path' is a symlink; aborting to avoid write-through escape" >&2
   858	      exit 1
   859	    fi
   860	  done
   861	  return 0
   862	}
   863	
   864	install_one() {
   865	  local rel_path="$1"
   866	  local src="$SOURCE_DIR/$rel_path"
   867	  local dst="$TARGET/$rel_path"
   868	
   869	  # PLAN-166 F3 (ADR-155-AMEND-1): delivery signal for the caller — 1 only
   870	  # when THIS call actually wrote the destination (COPIED/LINKED). An
   871	  # EXISTS-skip, a missing source and a dry-run all leave it 0.
   872	  INSTALL_ONE_WROTE=0
   873	
   874	  if [[ ! -e "$src" ]]; then
   875	    echo "    SKIP (source missing): $rel_path"
   876	    return
   877	  fi
   878	
   879	  if [[ "$DRY_RUN" -eq 1 ]]; then
   880	    if [[ -e "$dst" || -L "$dst" ]]; then
   881	      echo "    (dry-run) EXISTS (would skip): $rel_path"
   882	    elif [[ "$MODE" == "link" ]]; then
   883	      echo "    (dry-run) would LINK: $rel_path"
   884	    else
   885	      echo "    (dry-run) would COPY: $rel_path"
   886	    fi
   887	    return
   888	  fi
   889	
   890	  _assert_no_symlink_parents "$rel_path"
   891	  mkdir -p "$( dirname "$dst" )"
   892	
   893	  if [[ -e "$dst" || -L "$dst" ]]; then
   894	    echo "    EXISTS (skipping): $rel_path"
   895	    return
   896	  fi
   897	
   898	  if [[ "$MODE" == "link" ]]; then
   899	    ln -s "$src" "$dst"
   900	    INSTALL_ONE_WROTE=1
   901	    echo "    LINKED: $rel_path"
   902	  else
   903	    if [[ -d "$src" ]]; then
   904	      cp -R "$src" "$dst"
   905	    else
   906	      cp "$src" "$dst"
   907	    fi
   908	    INSTALL_ONE_WROTE=1
   909	    echo "    COPIED: $rel_path"
   910	  fi
   911	}
   912	
   913	install_template() {
   914	  local src_rel="$1"
   915	  local dst_rel="$2"
   916	  local src="$SOURCE_DIR/$src_rel"
   917	  local dst="$TARGET/$dst_rel"
   918	
   919	  if [[ ! -f "$src" ]]; then
   920	    echo "    SKIP (template missing): $src_rel"
   921	    return
   922	  fi
   923	
   924	  if [[ "$DRY_RUN" -eq 1 ]]; then
   925	    if [[ -e "$dst" ]]; then
   926	      echo "    (dry-run) EXISTS (would skip template): $dst_rel"
   927	    else
   928	      echo "    (dry-run) would COPY template: $src_rel -> $dst_rel"
   929	    fi
   930	    return
  1280	osv_supply_chain_advisory || {
  1281	  _osv_rc=$?
  1282	  if [[ "$_osv_rc" -eq 4 ]]; then
  1283	    echo "    WARNING: supply-chain advisory BLOCKED a target (CEO_OSV_GATE=block)." >&2
  1284	    echo "             Review the breadcrumb above before running that install." >&2
  1285	  fi
  1286	}
  1287	_state_record_op "install_commands_and_catalogs" ".claude/commands + pitfalls-catalog + task-chains + agent-metrics"
  1288	install_one ".claude/commands"
  1289	install_one ".claude/pitfalls-catalog.yaml"
  1290	install_one ".claude/task-chains.yaml"
  1291	install_one ".claude/agent-metrics.md"
  1292	
  1293	# ---- 5b. Plan schemas + debate fixture (PLAN-003 Phase 0 I-1) ----
  1294	
  1295	install_plan_schemas() {
  1296	  echo ""
  1297	  echo "==> Installing plan schemas + debate fixture"
  1298	  _state_record_op "install_plan_schemas" ""
  1299	  install_one ".claude/plans/README.md"
  1300	  install_one ".claude/plans/PLAN-SCHEMA.md"
  1301	  install_one ".claude/plans/AUDIT-LOG-SCHEMA.md"
  1302	  install_one ".claude/plans/DEBATE-SCHEMA.md"
  1303	  install_one ".claude/plans/examples/debate-round-1"
  1304	}
  1305	
  1306	install_plan_schemas
  1307	
  1308	# ---- 5c. ADR template (PLAN-003 Phase 0 I-2) ----
  1309	
  1310	install_adr_template() {
  1311	  echo ""
  1312	  echo "==> Installing ADR template"
  1313	  _state_record_op "install_adr_template" ".claude/adr/README.md"
  1314	  install_one ".claude/adr/README.md"
  1315	}
  1316	
  1317	install_adr_template
  1318	
  1319	# ---- 5c-bis-1 SPEC v1 schemas (PLAN-087 B.1 — closes R-042 cluster) ----
  1320	
  1321	install_spec_v1() {
  1322	  if [[ ! -d "$SOURCE_DIR/SPEC/v1" ]]; then
  1323	    echo "    SKIP: SPEC/v1/ absent in source"
  1324	    return 0
  1325	  fi
  1326	  echo ""
  1327	  echo "==> Installing SPEC v1 schemas (~$(ls "$SOURCE_DIR"/SPEC/v1/*.md 2>/dev/null | wc -l | tr -d ' ') files)"
  1328	  _state_record_op "install_spec_v1" "SPEC/v1"
  1329	  install_one "SPEC/v1"
  1330	  # PLAN-166 F3 (ADR-155-AMEND-1): the op line above records the ATTEMPT;
  1331	  # framework ownership requires the REGISTERED DELIVERY — install_one may
  1332	  # have EXISTS-skipped a pre-existing adopter SPEC/v1 (r17), which must
  1333	  # NOT be inventoried as framework-owned.
  1334	  if [[ "${INSTALL_ONE_WROTE:-0}" -eq 1 ]]; then
  1335	    _DELIVERED_SPEC=1
  1336	    _state_record_op "delivered_spec_v1" "SPEC/v1"
  1337	  fi
  1338	}
  1339	
  1340	if [[ "$CEREMONY" != "user" ]]; then install_spec_v1; fi  # WS4-guard-spec
  1341	
  1342	# ---- 5c-bis-2 VERSION manifest (PLAN-087 B.2 — closes R-042 cluster) ----
  1343	
  1344	install_version() {
  1345	  if [[ ! -f "$SOURCE_DIR/VERSION" ]]; then
  1346	    echo "    SKIP: VERSION file absent in source"
  1347	    return 0
  1348	  fi
  1349	  echo ""
  1350	  echo "==> Installing VERSION manifest ($(tr -d '\n' < "$SOURCE_DIR/VERSION"))"
  1351	  _state_record_op "install_version_manifest" "VERSION"
  1352	  install_one "VERSION"
  1353	}
  1354	
  1355	if [[ "$CEREMONY" != "user" ]]; then install_version; fi  # WS4-guard-version
  1356	
  1357	# ---- 5c-bis-3 framework version marker (PLAN-166 F3 / ADR-155-AMEND-1) ----
  1358	# .claude/.framework-version is a TRACKED file of the framework repo (one
  1359	# line, byte-identical to VERSION — the bump writes it as its 12th site and
  1360	# verify-counts.sh cross-checks it every release). It is the forensic anchor
  1361	# that stays true POST-UPGRADE: upgrade.sh deliberately never touches the
  1362	# root VERSION (S238/ADR-155 class), so on an upgraded adopter only this
  1363	# marker reports the installed framework version. It lives inside .claude/,
  1364	# so it is delivered in BOTH ceremonies (the WS4 user-ceremony guard only
  1365	# forbids root files). The write is EXPLICIT — the manifest enumeration
  1366	# never delivers anything, it only records (r7) — and skip-if-exists: a
  1367	# pre-existing marker stays adopter-owned (no delivery record), and every
  1368	# marker-first reader keyed off that record falls back to VERSION (r20).
  1369	install_framework_marker() {
  1370	  if [[ ! -f "$SOURCE_DIR/.claude/.framework-version" ]]; then
  1371	    echo "    SKIP: .claude/.framework-version absent in source (pre-v1.3.0 checkout)"
  1372	    return 0
  1373	  fi
  1374	  echo ""
  1375	  echo "==> Installing framework version marker (.claude/.framework-version — $(tr -d '[:space:]' < "$SOURCE_DIR/.claude/.framework-version"))"
  1376	  _state_record_op "install_framework_marker" ".claude/.framework-version"
  1377	  install_one ".claude/.framework-version"
  1378	  if [[ "${INSTALL_ONE_WROTE:-0}" -eq 1 ]]; then
  1379	    _DELIVERED_MARKER=1
  1380	    _state_record_op "delivered_framework_marker" ".claude/.framework-version"
  1381	  fi
  1382	}
  1383	
  1384	install_framework_marker  # both ceremonies: inside .claude/ (WS4-safe)
  1385	
  1880	# ---- 8. Drop a pointer to PROTOCOL.md (DevOps-P1-4: relative, not absolute) ----
  1881	
  1882	install_protocol_pointer() {
  1883	  if [[ -e "$TARGET/PROTOCOL.md" ]]; then
  1884	    return 0
  1885	  fi
  1886	
  1887	  # Compute a relative path from $TARGET to $SOURCE_DIR when possible.
  1888	  # If the framework repo lives outside the target repo (common case),
  1889	  # we fall back to {{PROTOCOL_SOURCE}} which the user substitutes
  1890	  # manually. Absolute paths are NOT hardcoded — they break portability
  1891	  # across dev machines and CI runners.
  1892	  #
  1893	  # Relative-path heuristic: if $SOURCE_DIR starts with $TARGET, the
  1894	  # framework was copied INTO the target — use a relative pointer. In
  1895	  # ALL other cases (e.g. adopter clones framework elsewhere), we emit
  1896	  # the user-editable {{PROTOCOL_SOURCE}} marker and document next steps.
  1897	  local pointer_body
  1898	  case "$SOURCE_DIR" in
  1899	    "$TARGET"/*)
  1900	      local rel="${SOURCE_DIR#$TARGET/}"
  1901	      pointer_body="The full CEO orchestration protocol lives at:
  1902	./${rel}/PROTOCOL.md
  1903	
  1904	To pull updates:
  1905	  ( cd ./${rel} && git pull )
  1906	  ./${rel}/scripts/upgrade.sh . --profile $PROFILE --stack $STACK"
  1907	      ;;
  1908	    *)
  1909	      pointer_body="The full CEO orchestration protocol lives at:
  1910	{{PROTOCOL_SOURCE}}/PROTOCOL.md
  1911	
  1912	Edit {{PROTOCOL_SOURCE}} to point at your ceo-orchestration checkout
  1913	(e.g. ../ceo-orchestration or \$HOME/src/ceo-orchestration).
  1914	
  1915	To pull updates:
  1916	  ( cd {{PROTOCOL_SOURCE}} && git pull )
  1917	  {{PROTOCOL_SOURCE}}/scripts/upgrade.sh $TARGET --profile $PROFILE --stack $STACK"
  1918	      ;;
  1919	  esac
  1920	
  1921	  if [[ "$DRY_RUN" -eq 1 ]]; then
  1922	    echo "    (dry-run) would CREATE: PROTOCOL.md (pointer)"
  1923	    return 0
  1924	  fi
  1925	
  1926	  cat > "$TARGET/PROTOCOL.md" <<EOF
  1927	# Protocol reference
  1928	
  1929	$pointer_body
  1930	EOF
  1931	  echo "    CREATED: PROTOCOL.md (pointer)"
  1932	  _state_record_op "install_protocol_pointer" "PROTOCOL.md"
  1933	  # PLAN-166 F3 (ADR-155-AMEND-1): registered delivery — this line is only
  1934	  # reached when the heredoc actually wrote the pointer (the pre-existing
  1935	  # early-return above never gets here, so an adopter's own root
  1936	  # PROTOCOL.md is never inventoried as framework-owned; r13/r17).
  1937	  _DELIVERED_PROTOCOL=1
  1938	  _state_record_op "delivered_protocol_pointer" "PROTOCOL.md"
  1939	}
  1940	
  1941	if [[ "$CEREMONY" != "user" ]]; then install_protocol_pointer; fi  # WS4-guard-proto
  1942	
  1943	# ----------------------------------------------------------------------
  1944	# P1-CR-3 / VP-F1: placeholder substitution pass
  1945	# ----------------------------------------------------------------------
  1946	# Iterate over a deterministic list of placeholder files (the ones
  1947	# templates/ writes out) and apply `sed -i` substitutions for every
  1948	# PH_* variable that is non-empty. Anything left as `{{...}}` after the
  1949	# pass is reported with a stderr warning.
  1950	#
  1951	# We restrict the pass to files install.sh actually placed (the
  1952	# templates/* files) to avoid touching user-authored content. If
  1953	# CLAUDE.md / MEMORY.md already existed at target, we leave them alone
  1954	# (install.sh never overwrites them).
  1955	
  1956	# Portable sed -i for GNU + BSD (macOS): write to .tmp and mv.
  1957	portable_sed_inplace() {
  1958	  # $1 = sed script, $2 = file
  1959	  local script="$1" file="$2"
  1960	  local tmp="${file}.ceo-sed-tmp"
  1961	  sed "$script" "$file" > "$tmp" && mv "$tmp" "$file"
  1962	}
  1963	
  1964	# Build the sed script iteratively. Each non-empty placeholder adds an
  1965	# expression. We use `|` as the delimiter so slashes in values (paths)
  1966	# don't break. Values with `|` are escaped.
  1967	build_sed_script() {
  1968	  local script=""
  1969	  _add_sub() {
  1970	    local key="$1" val="$2"
  2260	# PRESERVE/REFUSE customizations instead of clobbering them (incl. the root
  2261	# PROTOCOL.md — the verified S238 driver). The enumeration is the SINGLE shared
  2262	# set from _framework_manifest_set.sh, so the manifest writer (here) and the
  2263	# upgrade classifier walk an identical list.
  2264	#
  2265	# Manifest grammar (two record kinds):
  2266	#   <64hex>  <relpath>            — content hash of a copied file
  2267	#   LINK  <relpath>  <target>     — a --mode link symlink (content == source,
  2268	#                                   so a content hash is meaningless; the
  2269	#                                   upgrade classifier short-circuits LINK)
  2270	#
  2271	# Written to $TARGET/.claude/.install-manifest.sha256 (distinct from the
  2272	# release skill-manifest.sha256). EXCLUDES the manifest itself + .claude.bak/.
  2273	# Fail-open: any missing helper / unreadable file is skipped with a NOTE; the
  2274	# install never fails because the manifest could not be fully written.
  2275	# ----------------------------------------------------------------------
  2276	write_install_manifest() {
  2277	  # Guarded by the caller for DRY_RUN; defensive re-check here.
  2278	  [[ "${DRY_RUN:-0}" -eq 0 ]] || return 0
  2279	
  2280	  if ! command -v _write_baseline_manifest >/dev/null 2>&1; then
  2281	    echo "    NOTE: baseline manifest skipped — generator helper not sourced" >&2
  2282	    return 0
  2283	  fi
  2284	
  2285	  local manifest="$TARGET/.claude/.install-manifest.sha256"
  2286	  echo ""
  2287	  echo "==> Writing install baseline manifest (.claude/.install-manifest.sha256)"
  2288	  _state_record_op "write_install_manifest" ".claude/.install-manifest.sha256"
  2289	
  2290	  # Profile-aware enumeration rooted at the installed target; the SINGLE shared
  2291	  # generator in _framework_manifest_set.sh does the walk + hashing + LINK
  2292	  # records (the SAME generator upgrade.sh calls after a successful upgrade).
  2293	  export FMS_ROOT="$TARGET"
  2294	  export FMS_PROFILE_PARTS="${PROFILE_PARTS[*]}"
  2295	  export FMS_MODE="$MODE"
  2296	  # PLAN-166 F3 (ADR-155-AMEND-1): conditional ownership from the DELIVERY
  2297	  # RECORD — never the ceremony alone, never file presence. A path
  2298	  # install_one EXISTS-skipped stays out of the baseline, so doctor, the
  2299	  # update-checker and uninstall never treat an adopter file as
  2300	  # framework-owned (r7/r13/r17).
  2301	  #
  2302	  # Ownership CONTINUITY on reruns (codex W1-ceremony round, P1): a rerun
  2303	  # over an already-installed target EXISTS-skips all three paths, so the
  2304	  # THIS-RUN flags are 0 — but the manifest rewrite below REPLACES the old
  2305	  # manifest. Without consulting the PRIOR manifest's records, a rerun
  2306	  # would silently drop framework ownership of SPEC/PROTOCOL/marker (and a
  2307	  # v1.3 SPEC would later misclassify as ADOPTER-FORK — it is absent from
  2308	  # the legacy pristine fingerprints). Preserve a valid prior record: the
  2309	  # regexes mirror upgrade.sh _baseline_has_*_record byte-for-byte
  2310	  # (family-swept; `(/|  |$)` covers the --mode link single-LINK-line form).
  2311	  # A prior LINK record carries ownership forward only while the live symlink
  2312	  # still points where it was RECORDED (codex W1 round 10, P2). On a --link
  2313	  # reinstall over a RETARGETED managed symlink, install_one EXISTS-skips the
  2314	  # path and the continuity check used to accept the record blindly; the
  2315	  # rewrite then serialized the redirected target as the new delivery record
  2316	  # and every later upgrade accepted the foreign tree as healthy. Mirrors the
  2317	  # readlink-vs-record checks upgrade.sh already applies on its refresh
  2318	  # routes. Returns 0 (carry on) when there is no LINK record to compare.
  2319	  _prior_link_target_matches() {   # $1 = manifest, $2 = relpath
  2320	    local _plt_line _plt_rec="" _plt_live
  2321	    while IFS= read -r _plt_line || [[ -n "$_plt_line" ]]; do
  2322	      case "$_plt_line" in
  2323	        "LINK  $2  "*) _plt_rec="${_plt_line#LINK  $2  }"; break ;;
  2324	      esac
  2325	    done < "$1"
  2326	    [[ -n "$_plt_rec" ]] || return 0
  2327	    _plt_live="$( readlink "$TARGET/$2" 2>/dev/null || true )"
  2328	    [[ "$_plt_rec" == "$_plt_live" ]]
  2329	  }
  2330	  if [[ "${_DELIVERED_SPEC:-0}" != "1" ]] && [[ -f "$manifest" ]] \
  2331	     && grep -Eq '^([0-9a-f]{64}|LINK)  SPEC/v1(/|  |$)' "$manifest" 2>/dev/null \
  2332	     && _prior_link_target_matches "$manifest" "SPEC/v1"; then
  2333	    _DELIVERED_SPEC=1
  2334	    _CONTINUITY_FIRED=1
  2335	    _CONTINUITY_PATHS="${_CONTINUITY_PATHS:-}
  2336	SPEC/v1"
  2337	    echo "    ownership continuity: SPEC/v1 delivery record preserved from prior manifest"
  2338	  fi
  2339	  if [[ "${_DELIVERED_PROTOCOL:-0}" != "1" ]] && [[ -f "$manifest" ]] \
  2340	     && grep -Eq '^([0-9a-f]{64}|LINK)  PROTOCOL\.md(  |$)' "$manifest" 2>/dev/null \
  2341	     && _prior_link_target_matches "$manifest" "PROTOCOL.md"; then
  2342	    # FMS_HASH_ROOT does NOT reach PROTOCOL.md: _write_baseline_manifest
  2343	    # special-cases the generated pointer and hashes the TARGET unless
  2344	    # FMS_PROTOCOL_HASH is supplied — which install never set. So a rerun over
  2345	    # a CUSTOMIZED delivered pointer re-baselined the adopter's own bytes as
  2346	    # framework-owned; the next upgrade would then overwrite them and
  2347	    # uninstall could DELETE them (codex W1 round 9, P1). Carry the PRIOR
  2348	    # recorded digest. A LINK record needs none (the rewrite's link branch
  2349	    # fires before the PROTOCOL special case); with neither, DROP the
  2350	    # ownership claim rather than record a knowingly wrong baseline.
  2351	    _PRIOR_PROTOCOL_HASH="$( grep -E '^[0-9a-f]{64}  PROTOCOL\.md$' "$manifest" 2>/dev/null | head -1 | cut -d' ' -f1 || true )"
  2352	    if [[ -n "$_PRIOR_PROTOCOL_HASH" ]] \
  2353	       || grep -Eq '^LINK  PROTOCOL\.md(  |$)' "$manifest" 2>/dev/null; then
  2354	      _DELIVERED_PROTOCOL=1
  2355	      _CONTINUITY_FIRED=1
  2356	      _CONTINUITY_PATHS="${_CONTINUITY_PATHS:-}
  2357	PROTOCOL.md"
  2358	      echo "    ownership continuity: PROTOCOL.md delivery record preserved from prior manifest"
  2359	    else
  2360	      echo "    NOTE: PROTOCOL.md record present but its digest is unrecoverable —" >&2
  2361	      echo "          ownership NOT claimed (the pointer stays adopter-owned)" >&2
  2362	    fi
  2363	  fi
  2364	  if [[ "${_DELIVERED_MARKER:-0}" != "1" ]] && [[ -f "$manifest" ]] \
  2365	     && grep -Eq '^([0-9a-f]{64}|LINK)  \.claude/\.framework-version(  |$)' "$manifest" 2>/dev/null \
  2366	     && _prior_link_target_matches "$manifest" ".claude/.framework-version"; then
  2367	    _DELIVERED_MARKER=1
  2368	    _CONTINUITY_FIRED=1
  2369	    _CONTINUITY_PATHS="${_CONTINUITY_PATHS:-}
  2370	.claude/.framework-version"
  2371	    echo "    ownership continuity: .framework-version delivery record preserved from prior manifest"
  2372	  fi
  2373	  # For the continuity-preserved paths ONLY, hash the FRAMEWORK's pristine
  2374	  # copies instead of the (possibly edited) target's (codex W1 round 5, P1):
  2375	  # install normally hashes FMS_ROOT=$TARGET — on a rerun over an EDITED
  2376	  # delivered SPEC that would re-baseline the fork's bytes as framework-owned,
  2377	  # and a later uninstall would happily DELETE the user's modified tree (its
  2378	  # hash matches the manifest). Same C.5 idempotency posture upgrade.sh uses.
  2379	  #
  2380	  # SCOPED, not global (codex W1 round 8, P1): install RENDERS templates
  2381	  # (`.claude/team.md`, skills, `{{X}}` placeholders under --project et al),
  2382	  # so a global FMS_HASH_ROOT rewrote every rendered file's baseline to the
  2383	  # UNRENDERED source — doctor.sh then reports repo-wide adopter drift and
  2384	  # later upgrades classify those files as customized and stop refreshing
  2385	  # them. PLAN-167 W2.3 replaced that confinement with an EXPLICIT per-surface
  2386	  # hash_source: the decision says which paths take the framework's bytes,
  2387	  # so no global override is set here at all.
  2388	  if [[ "${_CONTINUITY_FIRED:-0}" = "1" ]]; then
  2389	    : # per-surface hash_source below replaces the global override
  2390	    case "$_CONTINUITY_PATHS" in
  2391	      *".claude/.framework-version"*) export FMS_HASH_SOURCE_MARKER="HASH_SOURCE" ;;
  2392	    esac
  2393	    case "$_CONTINUITY_PATHS" in
  2394	      # The generated pointer has no source bytes; carry what was recorded.
  2395	      *"PROTOCOL.md"*)               export FMS_HASH_SOURCE_PROTOCOL="HASH_PRIOR_RECORD" ;;
  2396	    esac
  2397	    echo "    ownership continuity: manifest hashes the preserved paths from the framework source (edited target content stays adopter-owned; rendered files keep their target hash)"
  2398	  fi
  2399	  # Declare on EVERY delivery path, not only continuity. A fresh install
  2400	  # genuinely delivers these surfaces, and the previous attempt at this wave
  2401	  # regressed 24 cells precisely because it left fresh installs undeclared.
  2402	  #
  2403	  # Fresh delivery: the target IS the bytes just written, so HASH_TARGET is
  2404	  # both correct and observationally identical to HASH_SOURCE.
  2405	  # Continuity: the target may be an EDITED fork, so the record must come from
  2406	  # the framework's copy (spec/marker) or the prior record (the generated
  2407	  # pointer, which has no source file).
  2408	  export FMS_SOURCE_ROOT="$SOURCE_DIR"
  2409	  export FMS_PRIOR_MANIFEST="$manifest"
  2410	  if [[ "${_DELIVERED_SPEC:-0}" = "1" ]]; then
  2411	    case "${_CONTINUITY_PATHS:-}" in
  2412	      *"SPEC/v1"*) export FMS_HASH_SOURCE_SPEC="HASH_SOURCE" ;;
  2413	      *)           export FMS_HASH_SOURCE_SPEC="HASH_TARGET" ;;
  2414	    esac
  2415	  fi
  2416	  if [[ "${_DELIVERED_MARKER:-0}" = "1" ]]; then
  2417	    case "${_CONTINUITY_PATHS:-}" in
  2418	      *".claude/.framework-version"*) export FMS_HASH_SOURCE_MARKER="HASH_SOURCE" ;;
  2419	      *)                              export FMS_HASH_SOURCE_MARKER="HASH_TARGET" ;;
  2420	    esac
  2421	  fi
  2422	  if [[ "${_DELIVERED_PROTOCOL:-0}" = "1" ]]; then
  2423	    case "${_CONTINUITY_PATHS:-}" in
  2424	      *"PROTOCOL.md"*) export FMS_HASH_SOURCE_PROTOCOL="HASH_PRIOR_RECORD" ;;
  2425	      *)               export FMS_HASH_SOURCE_PROTOCOL="HASH_TARGET" ;;
  2426	    esac
  2427	  fi
  2428	  export FMS_DELIVERED_SPEC="${_DELIVERED_SPEC:-0}"
  2429	  export FMS_DELIVERED_PROTOCOL="${_DELIVERED_PROTOCOL:-0}"
  2430	  export FMS_DELIVERED_MARKER="${_DELIVERED_MARKER:-0}"
  2431	  # Empty on a fresh install (target IS the freshly written pointer, hashing it
  2432	  # is correct); set only by the continuity path above.
  2433	  export FMS_PROTOCOL_HASH="${_PRIOR_PROTOCOL_HASH:-}"
  2434	  _write_baseline_manifest "$manifest"
  2435	  unset FMS_ROOT FMS_PROFILE_PARTS FMS_MODE FMS_HASH_ROOT FMS_PROTOCOL_HASH \
  2436	        FMS_PRIOR_MANIFEST FMS_HASH_SOURCE_SPEC FMS_HASH_SOURCE_PROTOCOL \
  2437	        FMS_HASH_SOURCE_MARKER
  2438	  unset FMS_DELIVERED_SPEC FMS_DELIVERED_PROTOCOL FMS_DELIVERED_MARKER
  2439	  return 0
  2440	}
  2441	
  2442	
  2443	# ----------------------------------------------------------------------
  2444	# PLAN-153 Wave B item B1 — persist the install-state.
  2445	# ----------------------------------------------------------------------
  2446	# Writes $TARGET/.claude/.install-state.json (next to the ADR-155 baseline
  2447	# manifest): the ORIGINAL request — verbatim argv + every parsed flag + the
  2448	# RESOLVED placeholder map (CLI > env > deterministic default; empty values
  2449	# omitted) — plus the operation journal for THIS run.
  2450	#
  2451	#   * Atomic: python writes a same-directory tempfile, then os.replace().
  2452	#   * Updated on every run: first_recorded_at + run_count + a bounded
  2453	#     history (last 20 runs) survive re-installs; request/operations
  2454	#     reflect the LATEST run.
  2455	#   * Schema-versioned: schema ceo.install-state/v1, schema_version 1.
  2456	#   * Consumed by upgrade.sh (PLAN-153 B2): request.profile/request.stack
  2457	#     become upgrade DEFAULTS when its own flags are omitted. A missing or
  2458	#     invalid state file degrades upgrade.sh to the ADR-155 drift-classifier
  2459	#     path — never an error, never a no-op (debate C back-compat must-fix).
  2460	#   * TRUST: target-side, UNSIGNED, advisory — the same trust class as the
  2461	#     ADR-155 baseline manifest (whoever can write the target tree can
  2462	#     rewrite it). upgrade.sh charset-validates every replayed value and
  2463	#     falls back on anything suspect; values are data, never eval-ed.
  2464	#   * Fail-open: no python3 / write error => stderr NOTE, install still
  2465	#     succeeds. Dry-run never writes (the "no files modified" promise).
  2466	#   * NOT covered by the baseline-manifest enumeration (like the manifest
  2467	#     dotfile itself), so the upgrade classifier never touches it.
  2468	_write_install_state() {
  2469	  [[ "${DRY_RUN:-0}" -eq 0 ]] || return 0
  2470	  if ! command -v python3 >/dev/null 2>&1; then

--- UPGRADE INIT/SOURCING ---
     1	#!/usr/bin/env bash
     2	# upgrade.sh — update an existing ceo-orchestration install in a target repo
     3	#
     4	# Usage:
     5	#   ./upgrade.sh <target-repo-path> [--profile <list>] [--stack <name>]
     6	#                                    [--pin <tag>] [--dry-run]
     7	#                                    [--skip <glob>] [--no-diff-warn]
     8	#                                    [--no-deprecation-warn]
     9	#
    10	# What it does:
    11	#   - Backs up the current .claude/team.md, .claude/frontend-team.md, .claude/skills/,
    12	#     .claude/hooks/, .claude/scripts/, .claude/commands/, .claude/pitfalls-catalog.yaml,
    13	#     .claude/task-chains.yaml to .claude.bak/{timestamp}/
    14	#   - (F-CHAOS-3) Before overwriting any adopter file that differs from the source,
    15	#     emits a `diff -q`-style WARNING line (shown on stderr) so the Owner is aware
    16	#     a customization will be replaced. Pass --no-diff-warn to silence.
    17	#     Pass --skip=<glob> to exclude files from the overwrite entirely (one --skip per pattern).
    18	#   - Replaces them with the latest from this repo, respecting --profile and --stack
    19	#   - Leaves CLAUDE.md, MEMORY.md, .claude/agent-metrics.md untouched — those are
    20	#     user-customized files. .claude/settings.json is preserved as-is for its
    21	#     existing keys, but the PLAN-135 W2 settings-merge step (below) ADDITIVELY
    22	#     registers new framework lifecycle hooks into it (idempotent, non-clobbering).
    23	#   - (DevOps-P1-4) Refreshes the PROTOCOL.md pointer to keep it aligned with the
    24	#     current source layout (framework-derived content, not user data).
    25	#   - (PLAN-135 W1 w0r) Pre-flight ADVISORY model-deprecation scan of the target
    26	#     via .claude/scripts/check-model-deprecations.py when present: already-retired
    27	#     or <=60-days-to-retirement Claude model ids emit stderr WARNING lines.
    28	#     NEVER blocks the upgrade — any infra failure degrades to a NOTE (fail-open).
    29	#     Pass --no-deprecation-warn to silence.
    30	#   - (PLAN-135 W2 H8) Idempotent settings-merge step. install.sh EXISTS-SKIPs an
    31	#     existing .claude/settings.json, so a fresh-install-only hook registration
    32	#     never reaches the S217 population of existing adopters. This step registers
    33	#     the new framework lifecycle hooks (today: the `Setup`/`init` post-install
    34	#     self-verification hook check_setup_verification.py) into the adopter's
    35	#     existing settings.json via an idempotent `jq` merge — additive, never
    36	#     clobbers existing entries, re-applying is a no-op. Fail-open: missing jq /
    37	#     malformed settings / merge error => stderr NOTE + the upgrade proceeds.
    38	#     Pass --no-settings-merge to opt out.
    39	#   - Owner-gated, no-silent-update: this script is NEVER auto-invoked. The Owner
    40	#     runs it explicitly after a deliberate `git pull`; the framework never
    41	#     self-updates or auto-downloads in the background (convergent with kooky's
    42	#     manual-only update checker — see PLAN-125 WS-3c / E5).
    43	#   - (PLAN-153 Wave B item B2) REPLAYS the RECORDED install request: when
    44	#     $TARGET/.claude/.install-state.json (written by install.sh since Wave B;
    45	#     schema ceo.install-state/v1) is present and valid, --profile/--stack
    46	#     DEFAULT to the recorded request.profile/request.stack. Explicit flags
    47	#     always win; --no-replay opts out entirely. BACK-COMPAT (debate C
    48	#     must-fix): a missing state file (every pre-Wave-B install) or an
    49	#     unreadable/invalid one NEVER errors and NEVER no-ops — the upgrade
    50	#     proceeds exactly as before on the ADR-155 path (--dry-run previews +
    51	#     the baseline drift-classifier below preserve/refuse customizations,
    52	#     degrading to diff -q warn-then-clobber when no baseline manifest
    53	#     exists either). After a successful non-dry upgrade the state file is
    54	#     (re)written, so the pre-Wave-B population acquires one (mirrors
    55	#     ADR-155 decision iv for the manifest). Replayed values are charset-
    56	#     validated data — the state file is UNSIGNED and advisory, never a
    57	#     trust anchor, and is never eval-ed.
    58	#   - (PLAN-163 T5.4) BASELINE-AWARE SETTINGS MIGRATION: availableModels,
    59	#     fallbackModel and permissions.defaultMode are migrated with an explicit
    60	#     IDEMPOTENT 3-state policy PER LEAF KEY (absent -> write the new
    61	#     baseline; equal to the OLD baseline (arrays byte-compared, exact order)
    62	#     -> updated to the new baseline; customized -> PRESERVED + a named
    63	#     WARNING). The new DirectoryAdded/Notification hook registrations are
    64	#     added only when not yet registered AND the T3.4 version-floor feature
    65	#     gate is on; customized registrations under the same events are always
    66	#     preserved. Opt out with --no-settings-migrate. Oracles derive their
    67	#     expectations from `upgrade.sh --print-settings-baselines` (the
    68	#     normative table IS the artifact — literals are never re-hardcoded).
    69	#   - (PLAN-164 W1, ADR-110-AMEND-1) PAIR-RAIL REGISTRATION-TIMEOUT VALUE
    70	#     MIGRATION: the check_pair_rail.py PreToolUse registration timeout is
    71	#     bumped to the template-derived cap IFF the adopter's current value is
    72	#     one of the frozen SUPERSEDED SHIPPED caps (60 pre-PLAN-164; 150 from
    73	#     PLAN-164/ADR-110-AMEND-1, shipped in v1.2.0 and superseded by
    74	#     ADR-110-AMEND-2's 210); any other adopter-chosen value is
    75	#     PRESERVED + a named WARNING; idempotent. Runs inside the same T5.4
    76	#     migration step (same opt-out, same --dry-run preview); the NEW cap is
    77	#     derived from templates/settings/settings.base.json, never hardcoded.
    78	#
    79	# Run after `git pull` in the source ceo-orchestration repo.
    80	
    81	# Bash 3.2 portability guard (DevOps-P1-3 parity with install.sh)
    82	if [ -z "${BASH_VERSINFO:-}" ]; then
    83	  echo "ERROR: upgrade.sh requires bash (detected non-bash shell)" >&2
    84	  exit 1
    85	fi
    86	if [ "${BASH_VERSINFO[0]}" -lt 3 ] || \
    87	   { [ "${BASH_VERSINFO[0]}" -eq 3 ] && [ "${BASH_VERSINFO[1]}" -lt 2 ]; }; then
    88	  echo "ERROR: upgrade.sh requires bash >= 3.2 (detected ${BASH_VERSION})" >&2
    89	  exit 1
    90	fi
    91	
    92	set -euo pipefail
    93	
    94	SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    95	SOURCE_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
    96	
    97	# PLAN-138 Wave C (ADR-155) — portable SHA-256 helpers + the single shared
    98	# framework-owned enumeration, sourced (not executed). Both back the baseline
    99	# classifier below. Fail-open: if a helper is absent (partial checkout) the
   100	# classifier degrades to today's diff -q warn-then-clobber behavior.
   101	if [ -f "$SCRIPT_DIR/_hash_lib.sh" ]; then
   102	  # shellcheck source=scripts/_hash_lib.sh
   103	  . "$SCRIPT_DIR/_hash_lib.sh"
   104	fi
   105	if [ -f "$SCRIPT_DIR/_framework_manifest_set.sh" ]; then
   106	  # shellcheck source=scripts/_framework_manifest_set.sh
   107	  . "$SCRIPT_DIR/_framework_manifest_set.sh"
   108	fi
   109	# PLAN-155 Wave 5 — codex harness emission helper (sourced, not executed).
   110	# Fail-open: absent => --harness codex round-trip degrades to a warning.
   111	if [ -f "$SCRIPT_DIR/_codex_harness.sh" ]; then
   112	  # shellcheck source=scripts/_codex_harness.sh
   113	  . "$SCRIPT_DIR/_codex_harness.sh"
   114	fi
   115	
   116	# PLAN-156 Wave 4 — Grok harness (sourced). Fail-open: absent => --harness
   117	# grok round-trip degrades to a warning (mirrors the codex source above).
   118	if [ -f "$SCRIPT_DIR/_grok_harness.sh" ]; then
   119	  # shellcheck source=scripts/_grok_harness.sh
   120	  . "$SCRIPT_DIR/_grok_harness.sh"
   121	fi
   122	
   123	# ===========================================================================
   124	# PLAN-163 T5.4 — settings baseline-migration NORMATIVE TABLE (W0b literals).
   125	# ---------------------------------------------------------------------------
   126	# ONE source of truth for the baseline-aware settings migration below
   127	# (_migrate_settings_baseline). Oracles derive their expectations from
   128	# `upgrade.sh --print-settings-baselines` (this exact JSON) instead of
   129	# hardcoding the literals — keep the table and the migration in lockstep.
   130	# Order is NORMATIVE: new model ids are APPENDED AT THE END (the arrays are
   131	# byte-compared and the first entry participates in default resolution —
   132	# ADR-149:95-102; mirror test :127-149,193-200); any other order needs an
   133	# ADR-181 justification. permissions.defaultMode follows the exact read
   134	# contract of _lib/effective_config.py:178-180,534-542 (stripped string).
   135	# The top-level scalar "model" leaf (the CC 2.1.220 session-default pin,
   136	# ADR-181 T1.1) has NO old-baseline value — old installs carry NO top-level
   137	# "model" key at all ("old": null documents that ABSENCE). Absence therefore
   138	# IS the old baseline: it is migrated to the new pin (claude-opus-5), closing
   139	# the T1.1 silent-flip (adding claude-sonnet-5 to availableModels must not
   140	# re-flip the session default) — BUT ONLY when claude-opus-5 is actually in
   141	# the resulting effective availableModels. C6 (codex R4): if an adopter has
   142	# CUSTOMIZED availableModels to a set that EXCLUDES claude-opus-5, setting the
   143	# pin would place it outside the allowlist and enforceAvailableModels would
   144	# reject it, so in that case the pin is NOT set and a named warning is emitted
   145	# (session default left to the adopter/harness). In the normal migrated case
   146	# claude-opus-5 IS present, so the pin is set and enforceAvailableModels
   147	# accepts it. Any PRESENT model value != the new pin is adopter-custom and
   148	# PRESERVED with a named warning (never re-flipped).
   149	# Each registration carries a "match" filename used for the idempotent
   150	# append (mirrors the H8 jq `_reg` semantics: an event entry whose
   151	# hooks[].command references the filename counts as already registered).
   152	_T54_BASELINES_JSON='{
   153	  "availableModels": {
   154	    "old": ["claude-opus-4-8","claude-fable-5","claude-sonnet-4-6","claude-haiku-4-5"],
   155	    "new": ["claude-opus-4-8","claude-fable-5","claude-sonnet-4-6","claude-haiku-4-5","claude-opus-5","claude-sonnet-5"]
   156	  },
   157	  "fallbackModel": {
   158	    "old": ["claude-opus-4-8"],
   159	    "new": ["claude-opus-5"]
   160	  },
   161	  "model": {
   162	    "old": null,
   163	    "new": "claude-opus-5"
   164	  },
   165	  "permissions.defaultMode": {
   166	    "old": "default",
   167	    "new": "manual"
   168	  },
   169	  "registrations": {
   170	    "DirectoryAdded": {
   171	      "match": "check_directory_added.py",
   172	      "entry": {
   173	        "_comment": "PLAN-163 T3.1: DirectoryAdded observer-writer - records session-added workspace roots into the session-roots registry (and, where the harness supports a block decision, enforces the narrowed hardblock floor). Posture per the T3.1 blockability probe; fail-open on infra. Kill: CEO_DIRECTORY_ADDED_GUARD=0.",
   174	        "matcher": "",
   175	        "hooks": [ { "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh\" check_directory_added.py", "timeout": 5, "statusMessage": "Recording added workspace root..." } ]
   176	      }
   177	    },
   178	    "Notification": {
   179	      "match": "check_notification.py",
   180	      "entry": {
   181	        "_comment": "PLAN-163 T3.2: Notification lifecycle telemetry (agent_needs_input / agent_completed) -> typed audit emit with no-value-echo; feeds liveness telemetry. ADVISORY, fail-open. Kill: CEO_NOTIFICATION_TELEMETRY=0.",
   182	        "matcher": "",
   183	        "hooks": [ { "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh\" check_notification.py", "timeout": 5, "statusMessage": "Recording notification lifecycle event..." } ]
   184	      }
   185	    }
   186	  }
   187	}'
   188	
   189	# PLAN-163 T3.4 FEATURE GATE — new-event registrations (DirectoryAdded,
   190	# Notification). SUPPORT.md declares the adopter floor >=2.0; until the
   191	# T3.4 version-floor probe (unknown-event-key tolerance on the floor
   192	# version) is recorded — or the floor is explicitly raised with
   193	# SUPPORT/install/upgrade kept coherent — emitting the new event keys into
   194	# ADOPTER settings stays OFF. Flip _T34_VERSION_FLOOR_PROBE_PASSED to 1 in
   195	# the SAME change that records the probe verdict
   196	# ({{FILL-FROM-PROBES}}: T3.4 version-floor probe — pending at authoring
   197	# time). Env override CEO_T34_NEW_EVENT_REGISTRATIONS={1|0} always wins
   198	# (test seam + operator escape hatch). The gate NEVER affects the three
   199	# model/permission leaf keys — those migrate regardless.
   200	_T34_VERSION_FLOOR_PROBE_PASSED=0
   201	_t34_new_event_registrations_enabled() {
   202	  case "${CEO_T34_NEW_EVENT_REGISTRATIONS:-}" in
   203	    1) return 0 ;;
   204	    0) return 1 ;;
   205	  esac
   206	  [ "$_T34_VERSION_FLOOR_PROBE_PASSED" -eq 1 ]
   207	}
   208	
   209	# PLAN-153 Wave B item B2 — capture the ORIGINAL upgrade argv verbatim BEFORE
   210	# parsing, for the post-upgrade state record (data only, never eval-ed).
   211	ORIG_UP_ARGV=( "$@" )
   212	
   213	TARGET=""
   214	PROFILE="core,frontend"
   215	STACK="none"
   216	PIN_REF=""
   217	DRY_RUN=0
   218	PURGE_MISINSTALLED=0   # PLAN-161 U3: opt-in hash-gated purge of mis-installed framework-internal files
   219	DIFF_WARN=1
   220	DEPRECATION_WARN=1
   221	SETTINGS_MERGE=1
   222	SETTINGS_MIGRATE=1       # PLAN-163 T5.4: baseline-aware settings migration (opt out: --no-settings-migrate)
   223	SETTINGS_MIGRATE_ONLY=0  # PLAN-163 T5.4: run ONLY the settings migration (test/ops seam)
   224	ON_CONFLICT="refuse"   # PLAN-138 Wave C (ADR-155): {refuse|theirs|backup}; default refuse (OQ2)
   225	REPLAY=1               # PLAN-153 Wave B item B2: replay the recorded install request (opt out: --no-replay)
   226	HARNESS=""             # PLAN-155 Wave 5: "" = infer from recorded request.harness (B2 mirror)
   227	HARNESS_EXPLICIT=0     # explicit --harness always beats a replayed value
   228	CODEX_MANAGED_HOOKS=0  # replayed from request.managed_hooks unless --managed-hooks
   229	# shellcheck disable=SC2034  # CODEX_WITH_SKILLS/CODEX_FORCE consumed by the sourced _codex_harness.sh
   230	CODEX_WITH_SKILLS=0
   231	# shellcheck disable=SC2034
   232	CODEX_FORCE=0          # upgrade derives this from --on-conflict for the codex refresh
   233	PROFILE_EXPLICIT=0      # PLAN-153 B2: explicit --profile always beats a replayed value
   234	STACK_EXPLICIT=0        # PLAN-153 B2: explicit --stack always beats a replayed value
   235	SKIP_GLOBS=()
   236	
   237	while [[ $# -gt 0 ]]; do
   238	  case "$1" in
   239	    --profile)
   240	      PROFILE="${2:-}"
   760	if cer not in ("maintainer", "user"):
   761	    sys.exit(3)
   762	sys.stdout.write(cer + "\n")
   763	' "$_INSTALL_STATE_FILE" 2>/dev/null
   764	}
   765	
   766	CEREMONY_EFFECTIVE="maintainer"
   767	_CEREMONY_SOURCE="default (no readable install-state — pre-Wave-B fail-open)"
   768	_cer_line=""
   769	if _cer_line="$(_read_install_state_ceremony)" && [[ -n "$_cer_line" ]]; then
   770	  CEREMONY_EFFECTIVE="$_cer_line"
   771	  _CEREMONY_SOURCE="recorded install request (.claude/.install-state.json)"
   772	fi
   773	
   774	TIMESTAMP="$( date +%Y%m%d-%H%M%S )"
   775	BAK_DIR="$TARGET/.claude.bak/$TIMESTAMP"
   776	
   777	IFS=',' read -r -a PROFILE_PARTS <<< "$PROFILE"
   778	
   779	echo "==> Upgrading ceo-orchestration"
   780	echo "    Source:  $SOURCE_DIR"
   781	echo "    Target:  $TARGET"
   782	echo "    Backup:  $BAK_DIR"
   783	echo "    Profile: $PROFILE"
   784	echo "    Stack:   $STACK"
   785	echo "    Ceremony: $CEREMONY_EFFECTIVE — $_CEREMONY_SOURCE"  # PLAN-166 F3
   786	if [[ "$_REPLAY_SOURCE" == "replay" ]]; then
   787	  echo "    Request: replayed from .claude/.install-state.json (PLAN-153 B2)"
   788	fi
   789	if [[ -n "$PIN_REF" ]]; then
   790	  echo "    Pinned:  $PIN_REF"
   791	fi
   792	echo ""
   793	
   794	# PLAN-161 U1: --dry-run must write NOTHING inside the target — eagerly
   795	# creating the (timestamped, thus always-new) backup dir was one of the three
   796	# dry-run-ignoring writer families found live in the 2026-07-21 adopter
   797	# upgrade. Real runs still create it up front (the U3 purge backup and the
   798	# agents-pin backup below rely on it existing).
   799	if [[ "$DRY_RUN" -eq 0 ]]; then
   800	  mkdir -p "$BAK_DIR"
   801	fi
   802	
   803	# PLAN-153 Wave B item B2 — upgrade operation journal (same shape as the
   804	# install-side journal): op<TAB>detail lines in a tempfile OUTSIDE $TARGET,
   805	# folded into .claude/.install-state.json by _write_upgrade_state at the end.
   806	# Dry-run never creates it. Fail-open throughout.
   807	if [[ "$DRY_RUN" -eq 0 ]]; then
   808	  _UP_OPS_FILE="$(mktemp "${TMPDIR:-/tmp}/ceo-upgrade-ops.XXXXXX" 2>/dev/null || true)"
   809	fi
   810	_up_record_op() {
   811	  if [[ -n "${_UP_OPS_FILE:-}" && -f "${_UP_OPS_FILE:-}" ]]; then
   812	    printf '%s\t%s\n' "$1" "${2:-}" >> "$_UP_OPS_FILE" 2>/dev/null || true
   813	  fi
   814	  return 0
   815	}
   816	
   817	# PLAN-155 Wave 5 — override the codex helper's no-op recorder so a codex
   818	# refresh during upgrade is journaled into the upgrade operation log.
   819	codex_journal() { _up_record_op "$1" "${2:-}"; }
   820	
   821	# ===========================================================================
   822	# PLAN-138 Wave C (ADR-155) — baseline manifest load + per-file classifier.
   823	# ===========================================================================
   824	# Read $TARGET/.claude/.install-manifest.sha256 ONCE at startup into a
   825	# validated, sanitized lookup file. Every line is re-validated here against the
   826	# two accepted record grammars; any line that matches NEITHER, or whose relpath
   827	# is absolute / contains `..` / control chars / duplicates an earlier relpath /
   828	# traverses a symlinked component, is DROPPED so it can never drive a silent
   829	# FRAMEWORK-CHANGED branch (CWE-345/494/22 provenance hardening). The raw
   830	# manifest is NEVER piped into `shasum -c`; classification recomputes +
   831	# compares in-process per validated relpath.
   832	#
   833	# bash 3.2-safe: no associative arrays. The validated manifest is a temp file;
   834	# lookups use a fixed-string, line-anchored grep.
   835	_BASELINE_MANIFEST_RAW="$TARGET/.claude/.install-manifest.sha256"
   836	_BASELINE_MANIFEST_FILE=""   # set to the sanitized temp file if a manifest loads
   837	_BASELINE_DUP_GUARD=""       # newline-list of relpaths already accepted (dup detection)
   838	_BASELINE_INVALID=""         # newline-list of relpaths seen >1x: AMBIGUOUS provenance,
   839	                             # rejected entirely (NOT first-wins) — Codex R1 P0#2 fold.
   840	
   841	# Reject a relpath that is unsafe to trust from the manifest. Returns 0 (reject)
   842	# / 1 (accept). Checks: absolute, `..` segment, control chars, and a symlinked
   843	# component anywhere along the path under $TARGET (lstat per component, never
   844	# follow). Duplicate relpaths are rejected by the caller via _BASELINE_DUP_GUARD.
   845	#
   846	# $2 = record KIND, mirroring doctor.sh `_relpath_unsafe` (family sweep):
   847	# "link" tolerates a symlinked LEAF, anything else (default "file") does not.
   848	# A `LINK  <relpath>  <target>` record describes a --mode link delivery whose
   849	# leaf IS a symlink by construction, so rejecting it here silently dropped the
   850	# record from the sanitized manifest: _baseline_has_spec_record and both
   851	# readlink-vs-recorded-target checks could then NEVER match, and every
   852	# link-mode upgrade lost framework ownership of SPEC/v1 and the marker, with
   853	# marker-first readers falling back to the stale root VERSION (codex W1
   854	# round 6, P2). The leaf is never FOLLOWED here — validation stays at the
   855	# consumers, which compare `readlink` against the recorded target. Hash
   856	# records keep the strict leaf check: a managed regular file swapped for a
   857	# symlink must not retain its record (_hash_file WOULD follow it). Symlinked
   858	# PARENT components remain a genuine traversal hazard for both kinds.
   859	_baseline_relpath_unsafe() {
   860	  _bru_rel="$1"
   861	  _bru_kind="${2:-file}"
   862	  case "$_bru_rel" in
   863	    /*) return 0 ;;                       # absolute
   864	    *..*) return 0 ;;                      # parent traversal (covers ../ and /..)
   865	  esac
   866	  # Control chars / whitespace-only / empty.
   867	  case "$_bru_rel" in
   868	    ""|*[$'\n\r\t']*) return 0 ;;
   869	  esac
   870	  # Count the significant components first, so the leaf can be identified by
   871	  # INDEX — reconstructing "$TARGET/$_bru_rel" for a leaf test would differ
   872	  # from the walk on `./` and trailing-slash forms.
   873	  _bru_n=0
   874	  _bru_oldIFS="$IFS"
   875	  IFS='/'
   876	  for _bru_comp in $_bru_rel; do
   877	    [ -n "$_bru_comp" ] || continue
   878	    [ "$_bru_comp" = "." ] && continue
   879	    _bru_n=$(( _bru_n + 1 ))
   880	  done
   881	  # Symlinked-component check: walk each path component under $TARGET; if any
   882	  # EXISTING component is a symlink, reject (do not follow it).
   883	  _bru_cur="$TARGET"
   884	  _bru_i=0
   885	  for _bru_comp in $_bru_rel; do
   886	    [ -n "$_bru_comp" ] || continue
   887	    [ "$_bru_comp" = "." ] && continue
   888	    _bru_i=$(( _bru_i + 1 ))
   889	    _bru_cur="$_bru_cur/$_bru_comp"
   890	    if [ -L "$_bru_cur" ]; then
   891	      if [ "$_bru_kind" = "link" ] && [ "$_bru_i" -eq "$_bru_n" ]; then
   892	        continue                          # the LINK record's own leaf
   893	      fi
   894	      IFS="$_bru_oldIFS"
   895	      return 0
   896	    fi
   897	  done
   898	  IFS="$_bru_oldIFS"
   899	  return 1
   900	}
   901	
   902	# Load + sanitize the baseline manifest. On any problem (absent / unreadable /
   903	# empty after sanitization) leaves _BASELINE_MANIFEST_FILE empty => fallback.
   904	_load_baseline_manifest() {
   905	  [ -f "$_BASELINE_MANIFEST_RAW" ] && [ -r "$_BASELINE_MANIFEST_RAW" ] || return 0
   906	  command -v _hash_file >/dev/null 2>&1 || return 0
   907	
   908	  # PLAN-161 U1: the sanitized manifest used to be mktemp'd INSIDE $BAK_DIR —
   909	  # a write inside the target even under --dry-run (and the reason dry-run
   910	  # could not keep classification alive once BAK_DIR creation was gated). It
   911	  # now lives in a secure temp OUTSIDE $TARGET in ALL runs; the composed
   912	  # _upgrade_cleanup EXIT trap reaps it via the _BASELINE_TMP_FILE global.
   913	  #
   914	  # PLAN-161 U1 (codex r1 F5): "outside $TARGET" must hold even when the
   915	  # CALLER's TMPDIR is $TARGET or lies under it — otherwise --dry-run writes
   916	  # in the target again. Resolve the tmp base physically (cd + pwd -P) and
   917	  # prefix-check it against the physically-resolved $TARGET (trailing-slash
   918	  # safe case glob, bash-3.2-safe); on equal-or-under, fall back to /tmp.
   919	  # If the base cannot be resolved (nonexistent), leave it — mktemp fails
   920	  # below and we return 0 (the existing no-manifest fallback).
   921	  local _lbm_base _lbm_base_abs _lbm_target_abs
   922	  _lbm_base="${TMPDIR:-/tmp}"
   923	  _lbm_base_abs="$( cd "$_lbm_base" 2>/dev/null && pwd -P )" || _lbm_base_abs=""
   924	  _lbm_target_abs="$( cd "$TARGET" 2>/dev/null && pwd -P )" || _lbm_target_abs=""
   925	  if [[ -n "$_lbm_base_abs" && -n "$_lbm_target_abs" ]]; then
   926	    case "${_lbm_base_abs%/}/" in
   927	      "${_lbm_target_abs%/}/"*) _lbm_base="/tmp" ;;
   928	    esac
   929	  fi
   930	  local sanitized
   931	  sanitized="$( mktemp "$_lbm_base/ceo-baseline-manifest.XXXXXX" 2>/dev/null )" || return 0
   932	  _BASELINE_TMP_FILE="$sanitized"
   933	
   934	  local line rest rel digest target
   935	  # Read line-by-line; NEVER `eval` or interpret manifest content.
   936	  while IFS= read -r line || [ -n "$line" ]; do
   937	    [ -n "$line" ] || continue
   938	    # Hash record: ^<64hex><2 spaces><relpath>$
   939	    # Link record: ^LINK<2 spaces><relpath><2 spaces><target>$
   940	    case "$line" in
   941	      LINK\ \ *)
   942	        rest="${line#LINK  }"
   943	        # relpath is everything up to the FIRST double-space; target the rest.
   944	        case "$rest" in
   945	          *"  "*)
   946	            rel="${rest%%  *}"
   947	            target="${rest#*  }"
   948	            ;;
   949	          *) continue ;;   # malformed LINK (no target) — drop
   950	        esac
   951	        # KIND=link: the leaf of a LINK record IS a symlink by construction
   952	        # (codex W1 round 6, P2). Symlinked PARENTS still reject.
   953	        if _baseline_relpath_unsafe "$rel" link; then continue; fi
   954	        # Duplicate relpath? Ambiguous provenance — invalidate the relpath
   955	        # ENTIRELY (not first-wins): the lookup will refuse it -> fallback.
   956	        case "$_BASELINE_DUP_GUARD" in
   957	          *"
   958	$rel
   959	"*)
   960	            case "$_BASELINE_INVALID" in
   961	              *"
   962	$rel
   963	"*) ;;
   964	              *) _BASELINE_INVALID="$_BASELINE_INVALID
   965	$rel
   966	" ;;
   967	            esac
   968	            continue ;;
   969	        esac
   970	        _BASELINE_DUP_GUARD="$_BASELINE_DUP_GUARD
   971	$rel
   972	"
   973	        # Re-emit a normalized LINK record (target sanitized of control chars).
   974	        case "$target" in
   975	          *[$'\n\r\t']*) continue ;;
   976	        esac
   977	        printf 'LINK  %s  %s\n' "$rel" "$target" >> "$sanitized"
   978	        ;;
   979	      *)
   980	        # Must be exactly 64-hex, two spaces, then relpath.
   981	        digest="${line%%  *}"
   982	        rel="${line#*  }"
   983	        # Guard: the split must have actually found a double-space separator.
   984	        [ "$digest" != "$line" ] || continue
   985	        case "$digest" in
   986	          [0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]) ;;
   987	          *) continue ;;   # not a 64-hex digest — drop (provenance)
   988	        esac
   989	        if _baseline_relpath_unsafe "$rel"; then continue; fi
   990	        # Duplicate relpath? Ambiguous provenance — invalidate ENTIRELY
  3010	# PLAN-135 W2 H8: register new lifecycle hooks (Setup/init self-verification)
  3011	# into the adopter's existing settings.json (install.sh would EXISTS-SKIP it).
  3012	_merge_lifecycle_hooks_into_settings
  3013	
  3014	# PLAN-163 T5.4: baseline-aware settings migration — fleet/permission leaf
  3015	# keys + (T3.4-gated) new-event registrations. 3-state per key; idempotent;
  3016	# customized values are always PRESERVED with a named WARNING.
  3017	_migrate_settings_baseline
  3018	
  3019	# DevOps-P1-4: PROTOCOL.md is framework-derived (pointer), not user data —
  3020	# refresh it so it stays aligned with the current source layout.
  3021	# PLAN-166 F3 (ADR-155-AMEND-1): CEREMONY-GATED — the refresh used to run
  3022	# unconditionally and `cat >`-created a root PROTOCOL.md that a
  3023	# `--ceremony user` install deliberately never has (install.sh
  3024	# WS4-guard-proto forbids root files); the F4 tree-comparison e2e exposes
  3025	# exactly this divergence (r7/r13). The gate reads the ceremony from
  3026	# .claude/.install-state.json via the replay-independent reader above.
  3027	_PROTOCOL_DELIVERED=0
  3028	echo ""
  3029	echo "==> Refreshing PROTOCOL.md pointer"
  3030	if [[ "$CEREMONY_EFFECTIVE" == "user" ]]; then
  3031	  echo "    SKIP: PROTOCOL.md pointer (recorded --ceremony user install — a user install never creates root files, WS4; r13)"
  3032	  # Ownership continuity on the analogous skip (codex W1 round 7, P2) — see
  3033	  # the SPEC/v1 ceremony skip: preserving the tree while erasing its record
  3034	  # strands a framework-delivered pointer as unowned.
  3035	  #
  3036	  # But the flag alone is NOT enough (codex W1 round 9, P1): this skip never
  3037	  # runs _refresh_protocol_pointer, so _REFRESH_PROTOCOL_CANON_HASH stays
  3038	  # empty, and _write_baseline_manifest then hashes the LIVE pointer —
  3039	  # re-recording an adopter-CUSTOMIZED PROTOCOL.md as the framework baseline,
  3040	  # which the next upgrade overwrites and uninstall can DELETE. Retaining
  3041	  # ownership must never retain the wrong bytes. Carry the PRIOR canonical
  3042	  # digest; a LINK record needs none (the link branch of the rewrite fires
  3043	  # before the PROTOCOL special case). When neither is available, DROP the
  3044	  # claim — the pointer stays adopter-owned and preserved, which is the
  3045	  # pre-continuity behaviour and loses nothing.
  3046	  if _baseline_has_protocol_record; then
  3047	    _REFRESH_PROTOCOL_CANON_HASH="$( _baseline_lookup "PROTOCOL.md" 2>/dev/null || true )"
  3048	    if [[ -n "$_REFRESH_PROTOCOL_CANON_HASH" ]] \
  3049	       || grep -Eq '^LINK  PROTOCOL\.md(  |$)' "$_BASELINE_MANIFEST_FILE" 2>/dev/null; then
  3050	      _PROTOCOL_DELIVERED=1
  3051	    else
  3052	      echo "    NOTE: PROTOCOL.md delivery record present but its canonical digest is" >&2
  3053	      echo "          unrecoverable (ambiguous record) — ownership NOT claimed; the" >&2
  3054	      echo "          pointer stays adopter-owned and preserved" >&2
  3055	    fi
  3056	  fi
  3057	else
  3058	  # _refresh_protocol_pointer sets _PROTOCOL_DELIVERED itself, from the
  3059	  # VERDICT. Forcing it to 1 here overrode a PRESERVE_UNOWNED decision and
  3060	  # recorded an adopter's own pre-existing PROTOCOL.md as framework-owned —
  3061	  # a caller computing the right answer and then ignoring it (codex W3 r1 P1).
  3062	  _refresh_protocol_pointer
  3063	fi
  3064	
  3065	# PLAN-166 F3 (ADR-155-AMEND-1): SPEC/v1 forced refresh + framework version
  3066	# marker. Both run BEFORE the baseline-manifest rewrite so the delivery
  3067	# flags they set are what the rewritten baseline records.
  3068	echo ""
  3069	echo "==> Refreshing SPEC/v1 contract (PLAN-166 F3 — forced route)"
  3070	_refresh_spec_contract
  3071	
  3072	echo ""
  3073	echo "==> Refreshing framework version marker (.claude/.framework-version)"
  3074	_refresh_framework_marker
  3075	
  3076	# PLAN-161 U3 — mis-install scan/purge. Runs in ALL modes (flag-absent and
  3077	# --dry-run runs emit the would-purge PREVIEW; deletion requires the explicit
  3078	# --purge-misinstalled flag AND a non-dry run). Runs BEFORE the baseline-
  3079	# manifest rewrite below so a purged path is never re-recorded.
  3080	echo ""
  3081	echo "==> Scanning excluded trees for mis-installed framework-internal files (PLAN-161 U3)"
  3082	_purge_misinstalled_scan
  3083	
  3084	# PLAN-138 Wave C (ADR-155) C.7 — (re)write the baseline manifest AFTER a
  3085	# successful upgrade, so a long-lived adopter who upgrades but never re-runs
  3086	# install.sh (the S238 acme population) acquires/refreshes a manifest. The
  3087	# NEXT upgrade then runs the manifest-present per-file classified path instead
  3088	# of the fallback. Uses the SAME shared generator install.sh calls. Skipped on
  3089	# --dry-run; fail-open (a generator problem emits a NOTE, never aborts).
  3090	if [[ "$DRY_RUN" -eq 0 ]] && command -v _write_baseline_manifest >/dev/null 2>&1; then
  3091	  echo ""
  3092	  echo "==> (Re)writing install baseline manifest (.claude/.install-manifest.sha256)"
  3093	  _up_record_op "rewrite_baseline_manifest" ".claude/.install-manifest.sha256"
  3094	  export FMS_ROOT="$TARGET"            # enumerate what the target holds post-upgrade
  3095	  export FMS_HASH_ROOT="$SOURCE_DIR"   # but record the FRAMEWORK hash, not the
  3096	                                       # (possibly customized-and-preserved) target
  3097	                                       # file — else the next upgrade clobbers it
  3098	                                       # (C.5 idempotency fix). PROTOCOL.md pointer
  3099	                                       # still hashes from FMS_ROOT inside the gen.
  3100	  export FMS_PROFILE_PARTS="${PROFILE_PARTS[*]}"
  3101	  # FMS_MODE mirrors the INSTALL's mode, not the upgrade's copy behavior
  3102	  # (codex W1-ceremony round, P2): on a --mode link target the refresh
  3103	  # branches preserve the symlinks, but a `copy`-mode rewrite would OMIT
  3104	  # the SPEC/v1 directory-LINK record and hash the marker symlink as a
  3105	  # file — doctor.sh then reports a type-change drift on a healthy tree.
  3106	  # Evidence order: prior baseline LINK record (authoritative), else a
  3107	  # symlink probe on the framework-owned roots, else copy.
  3108	  FMS_MODE="copy"
  3109	  if [[ -n "$_BASELINE_MANIFEST_FILE" && -f "$_BASELINE_MANIFEST_FILE" ]] \
  3110	     && grep -Eq '^LINK  ' "$_BASELINE_MANIFEST_FILE" 2>/dev/null; then
  3111	    FMS_MODE="link"
  3112	    # Confine LINK serialization to the paths that ALREADY were LINK records
  3113	    # (codex W1 round 10, P2). Without this, inferring link-mode from the
  3114	    # prior manifest also promoted every OTHER live symlink — e.g. an
  3115	    # adopter's own file under `.claude/hooks/` — into a framework delivery
  3116	    # record. The probe branch below leaves FMS_LINK_PATHS unset (no baseline
  3117	    # to derive from), keeping its pre-existing behaviour.
  3118	    FMS_LINK_PATHS="$( awk '
  3119	      {
  3120	        idx = index($0, "  ");
  3121	        if (idx == 0) next;
  3122	        if (substr($0, 1, idx - 1) != "LINK") next;
  3123	        rest = substr($0, idx + 2);
  3124	        j = index(rest, "  ");
  3125	        print (j == 0 ? rest : substr(rest, 1, j - 1));
  3126	      }' "$_BASELINE_MANIFEST_FILE" 2>/dev/null || true )"
  3127	    export FMS_LINK_PATHS
  3128	    echo "    baseline rewrite: --mode link install detected (LINK records in prior manifest) — preserving LINK serialization for $( printf '%s\n' "$FMS_LINK_PATHS" | grep -c . || true ) recorded path(s)"
  3129	  elif [[ -L "$TARGET/.claude/skills" || -L "$TARGET/SPEC/v1" || -L "$TARGET/.claude/.framework-version" ]]; then
  3130	    FMS_MODE="link"
  3131	    echo "    baseline rewrite: --mode link install detected (symlink probe) — preserving LINK serialization"
  3132	  fi
  3133	  export FMS_MODE
  3134	  # Canonical PROTOCOL.md pointer hash (Codex R2 P0): record what the framework
  3135	  # WOULD generate, never a preserved adopter customization. Empty if the
  3136	  # pointer refresh did not run; the generator then falls back to hashing the
  3137	  # target (install semantics).
  3138	  export FMS_PROTOCOL_HASH="${_REFRESH_PROTOCOL_CANON_HASH:-}"
  3139	  # PLAN-166 F3 (ADR-155-AMEND-1): conditional ownership from what THIS
  3140	  # upgrade delivered/refreshed (or what the pre-upgrade baseline already
  3141	  # recorded — ownership continuity), never the ceremony alone, never file
  3142	  # presence (r17/r19/r20).
  3143	  # The decision travels with the delivery flag.
  3144	  export FMS_SOURCE_ROOT="$SOURCE_DIR"
  3145	  export FMS_PRIOR_MANIFEST="${_BASELINE_MANIFEST_FILE:-}"
  3146	  export FMS_HASH_SOURCE_SPEC="${_SPEC_HASH_SOURCE:-}"
  3147	  export FMS_HASH_SOURCE_MARKER="${_MARKER_HASH_SOURCE:-}"
  3148	  export FMS_HASH_SOURCE_PROTOCOL="${_PROTOCOL_HASH_SOURCE:-}"
  3149	  export FMS_DELIVERED_SPEC="${_SPEC_DELIVERED:-0}"
  3150	  export FMS_DELIVERED_PROTOCOL="${_PROTOCOL_DELIVERED:-0}"
  3151	  export FMS_DELIVERED_MARKER="${_MARKER_DELIVERED:-0}"
  3152	  _write_baseline_manifest "$TARGET/.claude/.install-manifest.sha256"
  3153	  unset FMS_ROOT FMS_HASH_ROOT FMS_PROFILE_PARTS FMS_MODE FMS_PROTOCOL_HASH FMS_LINK_PATHS
  3154	  unset FMS_DELIVERED_SPEC FMS_DELIVERED_PROTOCOL FMS_DELIVERED_MARKER
  3155	fi
  3156	
  3157	# ===========================================================================
  3158	# PLAN-153 Wave B item B2 — (re)write the install-state after a successful
  3159	# upgrade, mirroring the ADR-155 decision-(iv) manifest rewrite above: a
  3160	# pre-Wave-B adopter (no state file) ACQUIRES one on their first post-Wave-B
  3161	# upgrade, so the NEXT upgrade can replay. Merge semantics preserve the
  3162	# ORIGINAL install request (argv, mode, ceremony, placeholders map) and only
  3163	# update the replayable fields (request.profile/request.stack) to the values
  3164	# THIS run effectively used; the upgrade run itself is recorded under
  3165	# last_upgrade + history. Atomic (same-directory tempfile + os.replace),
  3166	# schema ceo.install-state/v1, fail-open (a write problem emits a NOTE and
  3167	# never aborts the completed upgrade). Skipped on --dry-run.
  3168	_write_upgrade_state() {
  3169	  [[ "$DRY_RUN" -eq 0 ]] || return 0
  3170	  if ! command -v python3 >/dev/null 2>&1; then
  3171	    echo "    NOTE: install-state not (re)written (python3 not found) — the next upgrade uses the ADR-155 fallback path" >&2
  3172	    return 0
  3173	  fi
  3174	  local fw_version=""
  3175	  if [[ -f "$SOURCE_DIR/VERSION" ]]; then
  3176	    fw_version="$(tr -d '[:space:]' < "$SOURCE_DIR/VERSION" 2>/dev/null || true)"
  3177	  fi
  3178	  local pairs=(
  3179	    "target" "$TARGET"
  3180	    "profile" "$PROFILE"
  3181	    "stack" "$STACK"
  3182	    "on_conflict" "$ON_CONFLICT"
  3183	    "pin" "$PIN_REF"
  3184	    "replay_source" "$_REPLAY_SOURCE"
  3185	    "harness" "$HARNESS"
  3186	    "managed_hooks" "$CODEX_MANAGED_HOOKS"
  3187	    "ceremony_effective" "$CEREMONY_EFFECTIVE"
  3188	  )
  3189	  echo ""
  3190	  echo "==> (Re)writing install-state (.claude/.install-state.json — PLAN-153 Wave B)"

exec
/bin/zsh -lc "nl -ba scripts/upgrade.sh | sed -n '1,180p;240,380p;700,840p;990,1120p'; printf '\\n--- MANIFEST LIB FINAL ---\\n'; nl -ba scripts/_framework_manifest_set.sh | sed -n '1,500p'; printf '\\n--- INSTALL FINAL MANIFEST ---\\n'; nl -ba scripts/install.sh | sed -n '2370,2460p'" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
     1	#!/usr/bin/env bash
     2	# upgrade.sh — update an existing ceo-orchestration install in a target repo
     3	#
     4	# Usage:
     5	#   ./upgrade.sh <target-repo-path> [--profile <list>] [--stack <name>]
     6	#                                    [--pin <tag>] [--dry-run]
     7	#                                    [--skip <glob>] [--no-diff-warn]
     8	#                                    [--no-deprecation-warn]
     9	#
    10	# What it does:
    11	#   - Backs up the current .claude/team.md, .claude/frontend-team.md, .claude/skills/,
    12	#     .claude/hooks/, .claude/scripts/, .claude/commands/, .claude/pitfalls-catalog.yaml,
    13	#     .claude/task-chains.yaml to .claude.bak/{timestamp}/
    14	#   - (F-CHAOS-3) Before overwriting any adopter file that differs from the source,
    15	#     emits a `diff -q`-style WARNING line (shown on stderr) so the Owner is aware
    16	#     a customization will be replaced. Pass --no-diff-warn to silence.
    17	#     Pass --skip=<glob> to exclude files from the overwrite entirely (one --skip per pattern).
    18	#   - Replaces them with the latest from this repo, respecting --profile and --stack
    19	#   - Leaves CLAUDE.md, MEMORY.md, .claude/agent-metrics.md untouched — those are
    20	#     user-customized files. .claude/settings.json is preserved as-is for its
    21	#     existing keys, but the PLAN-135 W2 settings-merge step (below) ADDITIVELY
    22	#     registers new framework lifecycle hooks into it (idempotent, non-clobbering).
    23	#   - (DevOps-P1-4) Refreshes the PROTOCOL.md pointer to keep it aligned with the
    24	#     current source layout (framework-derived content, not user data).
    25	#   - (PLAN-135 W1 w0r) Pre-flight ADVISORY model-deprecation scan of the target
    26	#     via .claude/scripts/check-model-deprecations.py when present: already-retired
    27	#     or <=60-days-to-retirement Claude model ids emit stderr WARNING lines.
    28	#     NEVER blocks the upgrade — any infra failure degrades to a NOTE (fail-open).
    29	#     Pass --no-deprecation-warn to silence.
    30	#   - (PLAN-135 W2 H8) Idempotent settings-merge step. install.sh EXISTS-SKIPs an
    31	#     existing .claude/settings.json, so a fresh-install-only hook registration
    32	#     never reaches the S217 population of existing adopters. This step registers
    33	#     the new framework lifecycle hooks (today: the `Setup`/`init` post-install
    34	#     self-verification hook check_setup_verification.py) into the adopter's
    35	#     existing settings.json via an idempotent `jq` merge — additive, never
    36	#     clobbers existing entries, re-applying is a no-op. Fail-open: missing jq /
    37	#     malformed settings / merge error => stderr NOTE + the upgrade proceeds.
    38	#     Pass --no-settings-merge to opt out.
    39	#   - Owner-gated, no-silent-update: this script is NEVER auto-invoked. The Owner
    40	#     runs it explicitly after a deliberate `git pull`; the framework never
    41	#     self-updates or auto-downloads in the background (convergent with kooky's
    42	#     manual-only update checker — see PLAN-125 WS-3c / E5).
    43	#   - (PLAN-153 Wave B item B2) REPLAYS the RECORDED install request: when
    44	#     $TARGET/.claude/.install-state.json (written by install.sh since Wave B;
    45	#     schema ceo.install-state/v1) is present and valid, --profile/--stack
    46	#     DEFAULT to the recorded request.profile/request.stack. Explicit flags
    47	#     always win; --no-replay opts out entirely. BACK-COMPAT (debate C
    48	#     must-fix): a missing state file (every pre-Wave-B install) or an
    49	#     unreadable/invalid one NEVER errors and NEVER no-ops — the upgrade
    50	#     proceeds exactly as before on the ADR-155 path (--dry-run previews +
    51	#     the baseline drift-classifier below preserve/refuse customizations,
    52	#     degrading to diff -q warn-then-clobber when no baseline manifest
    53	#     exists either). After a successful non-dry upgrade the state file is
    54	#     (re)written, so the pre-Wave-B population acquires one (mirrors
    55	#     ADR-155 decision iv for the manifest). Replayed values are charset-
    56	#     validated data — the state file is UNSIGNED and advisory, never a
    57	#     trust anchor, and is never eval-ed.
    58	#   - (PLAN-163 T5.4) BASELINE-AWARE SETTINGS MIGRATION: availableModels,
    59	#     fallbackModel and permissions.defaultMode are migrated with an explicit
    60	#     IDEMPOTENT 3-state policy PER LEAF KEY (absent -> write the new
    61	#     baseline; equal to the OLD baseline (arrays byte-compared, exact order)
    62	#     -> updated to the new baseline; customized -> PRESERVED + a named
    63	#     WARNING). The new DirectoryAdded/Notification hook registrations are
    64	#     added only when not yet registered AND the T3.4 version-floor feature
    65	#     gate is on; customized registrations under the same events are always
    66	#     preserved. Opt out with --no-settings-migrate. Oracles derive their
    67	#     expectations from `upgrade.sh --print-settings-baselines` (the
    68	#     normative table IS the artifact — literals are never re-hardcoded).
    69	#   - (PLAN-164 W1, ADR-110-AMEND-1) PAIR-RAIL REGISTRATION-TIMEOUT VALUE
    70	#     MIGRATION: the check_pair_rail.py PreToolUse registration timeout is
    71	#     bumped to the template-derived cap IFF the adopter's current value is
    72	#     one of the frozen SUPERSEDED SHIPPED caps (60 pre-PLAN-164; 150 from
    73	#     PLAN-164/ADR-110-AMEND-1, shipped in v1.2.0 and superseded by
    74	#     ADR-110-AMEND-2's 210); any other adopter-chosen value is
    75	#     PRESERVED + a named WARNING; idempotent. Runs inside the same T5.4
    76	#     migration step (same opt-out, same --dry-run preview); the NEW cap is
    77	#     derived from templates/settings/settings.base.json, never hardcoded.
    78	#
    79	# Run after `git pull` in the source ceo-orchestration repo.
    80	
    81	# Bash 3.2 portability guard (DevOps-P1-3 parity with install.sh)
    82	if [ -z "${BASH_VERSINFO:-}" ]; then
    83	  echo "ERROR: upgrade.sh requires bash (detected non-bash shell)" >&2
    84	  exit 1
    85	fi
    86	if [ "${BASH_VERSINFO[0]}" -lt 3 ] || \
    87	   { [ "${BASH_VERSINFO[0]}" -eq 3 ] && [ "${BASH_VERSINFO[1]}" -lt 2 ]; }; then
    88	  echo "ERROR: upgrade.sh requires bash >= 3.2 (detected ${BASH_VERSION})" >&2
    89	  exit 1
    90	fi
    91	
    92	set -euo pipefail
    93	
    94	SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    95	SOURCE_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"
    96	
    97	# PLAN-138 Wave C (ADR-155) — portable SHA-256 helpers + the single shared
    98	# framework-owned enumeration, sourced (not executed). Both back the baseline
    99	# classifier below. Fail-open: if a helper is absent (partial checkout) the
   100	# classifier degrades to today's diff -q warn-then-clobber behavior.
   101	if [ -f "$SCRIPT_DIR/_hash_lib.sh" ]; then
   102	  # shellcheck source=scripts/_hash_lib.sh
   103	  . "$SCRIPT_DIR/_hash_lib.sh"
   104	fi
   105	if [ -f "$SCRIPT_DIR/_framework_manifest_set.sh" ]; then
   106	  # shellcheck source=scripts/_framework_manifest_set.sh
   107	  . "$SCRIPT_DIR/_framework_manifest_set.sh"
   108	fi
   109	# PLAN-155 Wave 5 — codex harness emission helper (sourced, not executed).
   110	# Fail-open: absent => --harness codex round-trip degrades to a warning.
   111	if [ -f "$SCRIPT_DIR/_codex_harness.sh" ]; then
   112	  # shellcheck source=scripts/_codex_harness.sh
   113	  . "$SCRIPT_DIR/_codex_harness.sh"
   114	fi
   115	
   116	# PLAN-156 Wave 4 — Grok harness (sourced). Fail-open: absent => --harness
   117	# grok round-trip degrades to a warning (mirrors the codex source above).
   118	if [ -f "$SCRIPT_DIR/_grok_harness.sh" ]; then
   119	  # shellcheck source=scripts/_grok_harness.sh
   120	  . "$SCRIPT_DIR/_grok_harness.sh"
   121	fi
   122	
   123	# ===========================================================================
   124	# PLAN-163 T5.4 — settings baseline-migration NORMATIVE TABLE (W0b literals).
   125	# ---------------------------------------------------------------------------
   126	# ONE source of truth for the baseline-aware settings migration below
   127	# (_migrate_settings_baseline). Oracles derive their expectations from
   128	# `upgrade.sh --print-settings-baselines` (this exact JSON) instead of
   129	# hardcoding the literals — keep the table and the migration in lockstep.
   130	# Order is NORMATIVE: new model ids are APPENDED AT THE END (the arrays are
   131	# byte-compared and the first entry participates in default resolution —
   132	# ADR-149:95-102; mirror test :127-149,193-200); any other order needs an
   133	# ADR-181 justification. permissions.defaultMode follows the exact read
   134	# contract of _lib/effective_config.py:178-180,534-542 (stripped string).
   135	# The top-level scalar "model" leaf (the CC 2.1.220 session-default pin,
   136	# ADR-181 T1.1) has NO old-baseline value — old installs carry NO top-level
   137	# "model" key at all ("old": null documents that ABSENCE). Absence therefore
   138	# IS the old baseline: it is migrated to the new pin (claude-opus-5), closing
   139	# the T1.1 silent-flip (adding claude-sonnet-5 to availableModels must not
   140	# re-flip the session default) — BUT ONLY when claude-opus-5 is actually in
   141	# the resulting effective availableModels. C6 (codex R4): if an adopter has
   142	# CUSTOMIZED availableModels to a set that EXCLUDES claude-opus-5, setting the
   143	# pin would place it outside the allowlist and enforceAvailableModels would
   144	# reject it, so in that case the pin is NOT set and a named warning is emitted
   145	# (session default left to the adopter/harness). In the normal migrated case
   146	# claude-opus-5 IS present, so the pin is set and enforceAvailableModels
   147	# accepts it. Any PRESENT model value != the new pin is adopter-custom and
   148	# PRESERVED with a named warning (never re-flipped).
   149	# Each registration carries a "match" filename used for the idempotent
   150	# append (mirrors the H8 jq `_reg` semantics: an event entry whose
   151	# hooks[].command references the filename counts as already registered).
   152	_T54_BASELINES_JSON='{
   153	  "availableModels": {
   154	    "old": ["claude-opus-4-8","claude-fable-5","claude-sonnet-4-6","claude-haiku-4-5"],
   155	    "new": ["claude-opus-4-8","claude-fable-5","claude-sonnet-4-6","claude-haiku-4-5","claude-opus-5","claude-sonnet-5"]
   156	  },
   157	  "fallbackModel": {
   158	    "old": ["claude-opus-4-8"],
   159	    "new": ["claude-opus-5"]
   160	  },
   161	  "model": {
   162	    "old": null,
   163	    "new": "claude-opus-5"
   164	  },
   165	  "permissions.defaultMode": {
   166	    "old": "default",
   167	    "new": "manual"
   168	  },
   169	  "registrations": {
   170	    "DirectoryAdded": {
   171	      "match": "check_directory_added.py",
   172	      "entry": {
   173	        "_comment": "PLAN-163 T3.1: DirectoryAdded observer-writer - records session-added workspace roots into the session-roots registry (and, where the harness supports a block decision, enforces the narrowed hardblock floor). Posture per the T3.1 blockability probe; fail-open on infra. Kill: CEO_DIRECTORY_ADDED_GUARD=0.",
   174	        "matcher": "",
   175	        "hooks": [ { "type": "command", "command": "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh\" check_directory_added.py", "timeout": 5, "statusMessage": "Recording added workspace root..." } ]
   176	      }
   177	    },
   178	    "Notification": {
   179	      "match": "check_notification.py",
   180	      "entry": {
   240	      PROFILE="${2:-}"
   241	      PROFILE_EXPLICIT=1
   242	      shift 2
   243	      ;;
   244	    --stack)
   245	      STACK="${2:-}"
   246	      STACK_EXPLICIT=1
   247	      shift 2
   248	      ;;
   249	    --pin)
   250	      PIN_REF="${2:-}"
   251	      shift 2
   252	      ;;
   253	    --dry-run)
   254	      DRY_RUN=1
   255	      shift
   256	      ;;
   257	    --purge-misinstalled)
   258	      # PLAN-161 U3 (OQ1 Owner-ratified): opt-in, hash-gated purge of
   259	      # mis-installed framework-internal excluded-tree files. NEVER default-on.
   260	      PURGE_MISINSTALLED=1
   261	      shift
   262	      ;;
   263	    --no-diff-warn)
   264	      DIFF_WARN=0
   265	      shift
   266	      ;;
   267	    --no-deprecation-warn)
   268	      DEPRECATION_WARN=0
   269	      shift
   270	      ;;
   271	    --no-settings-merge)
   272	      SETTINGS_MERGE=0
   273	      shift
   274	      ;;
   275	    --no-settings-migrate)
   276	      # PLAN-163 T5.4: skip the baseline-aware settings migration.
   277	      SETTINGS_MIGRATE=0
   278	      shift
   279	      ;;
   280	    --settings-migrate-only)
   281	      # PLAN-163 T5.4: run ONLY the settings migration against <target>
   282	      # and exit (test/ops seam; honors --dry-run + --no-settings-migrate).
   283	      SETTINGS_MIGRATE_ONLY=1
   284	      shift
   285	      ;;
   286	    --print-settings-baselines)
   287	      # PLAN-163 T5.4: introspection for oracles — the normative baseline
   288	      # table IS the artifact; tests parse this output (never hardcode).
   289	      printf '%s\n' "$_T54_BASELINES_JSON"
   290	      exit 0
   291	      ;;
   292	    --no-replay)
   293	      # PLAN-153 Wave B item B2: ignore .claude/.install-state.json entirely.
   294	      REPLAY=0
   295	      shift
   296	      ;;
   297	    --harness)
   298	      # PLAN-155 Wave 5: explicit override of the replayed harness.
   299	      HARNESS="${2:-}"
   300	      case "$HARNESS" in
   301	        claude|codex|grok) ;;
   302	        *) echo "ERROR: --harness must be 'claude', 'codex', or 'grok' (got: $HARNESS)" >&2; exit 2 ;;
   303	      esac
   304	      HARNESS_EXPLICIT=1
   305	      shift 2
   306	      ;;
   307	    --managed-hooks)
   308	      CODEX_MANAGED_HOOKS=1
   309	      shift
   310	      ;;
   311	    --skip)
   312	      SKIP_GLOBS+=( "${2:-}" )
   313	      shift 2
   314	      ;;
   315	    --skip=*)
   316	      SKIP_GLOBS+=( "${1#--skip=}" )
   317	      shift
   318	      ;;
   319	    --on-conflict)
   320	      ON_CONFLICT="${2:-}"
   321	      case "$ON_CONFLICT" in
   322	        refuse|theirs|backup) ;;
   323	        *) echo "ERROR: --on-conflict must be refuse|theirs|backup (got: $ON_CONFLICT)" >&2; exit 1 ;;
   324	      esac
   325	      shift 2
   326	      ;;
   327	    --on-conflict=*)
   328	      ON_CONFLICT="${1#--on-conflict=}"
   329	      case "$ON_CONFLICT" in
   330	        refuse|theirs|backup) ;;
   331	        *) echo "ERROR: --on-conflict must be refuse|theirs|backup (got: $ON_CONFLICT)" >&2; exit 1 ;;
   332	      esac
   333	      shift
   334	      ;;
   335	    -h|--help)
   336	      cat <<'HELP'
   337	Usage:
   338	  ./upgrade.sh <target-repo-path> [options]
   339	
   340	What it does:
   341	  Refreshes the framework-derived content (team.md, skills/, hooks/,
   342	  scripts/, commands/, pitfalls-catalog.yaml, task-chains.yaml, the
   343	  SPEC/v1 contract (forced route, skipped on --ceremony user installs)
   344	  and the .claude/.framework-version marker) in an existing adopter
   345	  install. User-customized files (CLAUDE.md, MEMORY.md,
   346	  .claude/agent-metrics.md) are NOT touched, and the root VERSION file
   347	  is NEVER touched (install-time snapshot — ADR-155-AMEND-1; read
   348	  .claude/.framework-version for the installed framework version). NOTE: .claude/settings.json IS
   349	  updated in place by the default-on baseline migration (the model/permission
   350	  leaf keys: model, availableModels, fallbackModel, permissions.defaultMode)
   351	  and the idempotent settings-merge (new lifecycle-hook registrations) —
   352	  adopter-CUSTOMIZED values are always preserved with a named warning, and a
   353	  pre-migration backup is written to .claude.bak/. Opt out with
   354	  --no-settings-migrate / --no-settings-merge to manage settings.json by hand.
   355	
   356	Options:
   357	  --profile <list>      Comma-separated profiles to refresh (default: core,frontend).
   358	                        Available: core, frontend, <domain-name>.
   359	                        Example: --profile core,fintech
   360	  --stack <name>        Stack-specific hooks override (default: none).
   361	                        Example: --stack node
   362	  --pin <tag>           Pin source to specific tag/SHA (SPEC v1 install-cli.md).
   363	                        Refuses if target has uncommitted .claude/ changes.
   364	                        Example: --pin v1.18.0
   365	  --dry-run             Print what WOULD be replaced without modifying $TARGET.
   366	  --no-diff-warn        Silence the F-CHAOS-3 "customization will be replaced" warnings.
   367	  --no-deprecation-warn Silence the PLAN-135 advisory model-deprecation scan
   368	                        (the scan never blocks the upgrade either way).
   369	  --no-settings-merge   Skip the PLAN-135 W2 idempotent settings-merge step
   370	                        that registers new lifecycle hooks (e.g. the Setup
   371	                        post-install self-verification hook) into the adopter's
   372	                        existing .claude/settings.json. The merge is idempotent
   373	                        + fail-open (never blocks the upgrade); pass this to opt
   374	                        out entirely and manage settings.json by hand.
   375	  --no-settings-migrate PLAN-163 T5.4: skip the baseline-aware settings
   376	                        migration (model, availableModels, fallbackModel,
   377	                        permissions.defaultMode + T3.4-gated new-event
   378	                        registrations). 3-state policy per LEAF KEY:
   379	                        absent -> write the new baseline; equal to the OLD
   380	                        baseline (byte-compared) -> update; customized ->
   700	        echo "    REPLAY: --stack $STACK (recorded request in .claude/.install-state.json; pass --stack or --no-replay to override)" >&2
   701	      fi
   702	      if [[ "$HARNESS_EXPLICIT" -eq 0 && -n "$_rp_harness" ]]; then
   703	        HARNESS="$_rp_harness"
   704	        _rp_used=1
   705	        echo "    REPLAY: --harness $HARNESS (recorded request in .claude/.install-state.json; pass --harness or --no-replay to override)" >&2
   706	      fi
   707	      if [[ "$CODEX_MANAGED_HOOKS" -eq 0 && "${_rp_managed:-0}" = "1" ]]; then
   708	        CODEX_MANAGED_HOOKS=1
   709	        _rp_used=1
   710	      fi
   711	      if [[ "$_rp_used" -eq 1 ]]; then
   712	        _REPLAY_SOURCE="replay"
   713	      fi
   714	    else
   715	      _REPLAY_SOURCE="fallback-invalid-state"
   716	      echo "    NOTE: .claude/.install-state.json present but unreadable/invalid — IGNORED." >&2
   717	      echo "          Proceeding with CLI/default flags on the ADR-155 path (baseline" >&2
   718	      echo "          drift-classifier; --dry-run previews). Never blocks (PLAN-153" >&2
   719	      echo "          debate C back-compat must-fix); a valid state file is rewritten" >&2
   720	      echo "          after this upgrade completes." >&2
   721	    fi
   722	  else
   723	    _REPLAY_SOURCE="fallback-no-state"
   724	    echo "    NOTE: no .claude/.install-state.json in target (pre-Wave-B install)." >&2
   725	    echo "          Proceeding with CLI/default flags on the ADR-155 path (baseline" >&2
   726	    echo "          drift-classifier when a manifest exists, else diff -q warn-then-" >&2
   727	    echo "          clobber). A state file is recorded after this upgrade completes." >&2
   728	  fi
   729	fi
   730	
   731	# ===========================================================================
   732	# PLAN-166 F3 (ADR-155-AMEND-1) — resolve the RECORDED install ceremony with
   733	# a reader of its OWN, INDEPENDENT of the replay path: --no-replay sets
   734	# REPLAY=0 and the replay block above (incl. _read_install_state_request) is
   735	# skipped entirely, so if the ceremony rode the replay, the documented
   736	# `upgrade.sh <target> --no-replay` would treat a `--ceremony user` install
   737	# as maintainer and force SPEC/protocol into the adopter's root (r9). This
   738	# reader ALWAYS runs. Fail-open: state absent/unreadable/invalid (ALL
   739	# pre-Wave-B installs) => "maintainer" — the pre-existing behavior; the
   740	# consequence is named in INSTALL.md §Upgrade flow. Same trust class as the
   741	# replay reader: target-side, UNSIGNED, advisory; the value is validated
   742	# against the closed enum {maintainer,user} and never eval-ed.
   743	# ===========================================================================
   744	_read_install_state_ceremony() {
   745	  command -v python3 >/dev/null 2>&1 || return 3
   746	  [ -f "$_INSTALL_STATE_FILE" ] && [ -r "$_INSTALL_STATE_FILE" ] || return 3
   747	  PYTHONNOUSERSITE=1 python3 -I -c '
   748	import json, sys
   749	try:
   750	    with open(sys.argv[1], "r", encoding="utf-8") as f:
   751	        d = json.load(f)
   752	except (OSError, ValueError):
   753	    sys.exit(3)
   754	if not isinstance(d, dict) or d.get("schema_version") != 1:
   755	    sys.exit(3)
   756	req = d.get("request")
   757	if not isinstance(req, dict):
   758	    sys.exit(3)
   759	cer = req.get("ceremony", "")
   760	if cer not in ("maintainer", "user"):
   761	    sys.exit(3)
   762	sys.stdout.write(cer + "\n")
   763	' "$_INSTALL_STATE_FILE" 2>/dev/null
   764	}
   765	
   766	CEREMONY_EFFECTIVE="maintainer"
   767	_CEREMONY_SOURCE="default (no readable install-state — pre-Wave-B fail-open)"
   768	_cer_line=""
   769	if _cer_line="$(_read_install_state_ceremony)" && [[ -n "$_cer_line" ]]; then
   770	  CEREMONY_EFFECTIVE="$_cer_line"
   771	  _CEREMONY_SOURCE="recorded install request (.claude/.install-state.json)"
   772	fi
   773	
   774	TIMESTAMP="$( date +%Y%m%d-%H%M%S )"
   775	BAK_DIR="$TARGET/.claude.bak/$TIMESTAMP"
   776	
   777	IFS=',' read -r -a PROFILE_PARTS <<< "$PROFILE"
   778	
   779	echo "==> Upgrading ceo-orchestration"
   780	echo "    Source:  $SOURCE_DIR"
   781	echo "    Target:  $TARGET"
   782	echo "    Backup:  $BAK_DIR"
   783	echo "    Profile: $PROFILE"
   784	echo "    Stack:   $STACK"
   785	echo "    Ceremony: $CEREMONY_EFFECTIVE — $_CEREMONY_SOURCE"  # PLAN-166 F3
   786	if [[ "$_REPLAY_SOURCE" == "replay" ]]; then
   787	  echo "    Request: replayed from .claude/.install-state.json (PLAN-153 B2)"
   788	fi
   789	if [[ -n "$PIN_REF" ]]; then
   790	  echo "    Pinned:  $PIN_REF"
   791	fi
   792	echo ""
   793	
   794	# PLAN-161 U1: --dry-run must write NOTHING inside the target — eagerly
   795	# creating the (timestamped, thus always-new) backup dir was one of the three
   796	# dry-run-ignoring writer families found live in the 2026-07-21 adopter
   797	# upgrade. Real runs still create it up front (the U3 purge backup and the
   798	# agents-pin backup below rely on it existing).
   799	if [[ "$DRY_RUN" -eq 0 ]]; then
   800	  mkdir -p "$BAK_DIR"
   801	fi
   802	
   803	# PLAN-153 Wave B item B2 — upgrade operation journal (same shape as the
   804	# install-side journal): op<TAB>detail lines in a tempfile OUTSIDE $TARGET,
   805	# folded into .claude/.install-state.json by _write_upgrade_state at the end.
   806	# Dry-run never creates it. Fail-open throughout.
   807	if [[ "$DRY_RUN" -eq 0 ]]; then
   808	  _UP_OPS_FILE="$(mktemp "${TMPDIR:-/tmp}/ceo-upgrade-ops.XXXXXX" 2>/dev/null || true)"
   809	fi
   810	_up_record_op() {
   811	  if [[ -n "${_UP_OPS_FILE:-}" && -f "${_UP_OPS_FILE:-}" ]]; then
   812	    printf '%s\t%s\n' "$1" "${2:-}" >> "$_UP_OPS_FILE" 2>/dev/null || true
   813	  fi
   814	  return 0
   815	}
   816	
   817	# PLAN-155 Wave 5 — override the codex helper's no-op recorder so a codex
   818	# refresh during upgrade is journaled into the upgrade operation log.
   819	codex_journal() { _up_record_op "$1" "${2:-}"; }
   820	
   821	# ===========================================================================
   822	# PLAN-138 Wave C (ADR-155) — baseline manifest load + per-file classifier.
   823	# ===========================================================================
   824	# Read $TARGET/.claude/.install-manifest.sha256 ONCE at startup into a
   825	# validated, sanitized lookup file. Every line is re-validated here against the
   826	# two accepted record grammars; any line that matches NEITHER, or whose relpath
   827	# is absolute / contains `..` / control chars / duplicates an earlier relpath /
   828	# traverses a symlinked component, is DROPPED so it can never drive a silent
   829	# FRAMEWORK-CHANGED branch (CWE-345/494/22 provenance hardening). The raw
   830	# manifest is NEVER piped into `shasum -c`; classification recomputes +
   831	# compares in-process per validated relpath.
   832	#
   833	# bash 3.2-safe: no associative arrays. The validated manifest is a temp file;
   834	# lookups use a fixed-string, line-anchored grep.
   835	_BASELINE_MANIFEST_RAW="$TARGET/.claude/.install-manifest.sha256"
   836	_BASELINE_MANIFEST_FILE=""   # set to the sanitized temp file if a manifest loads
   837	_BASELINE_DUP_GUARD=""       # newline-list of relpaths already accepted (dup detection)
   838	_BASELINE_INVALID=""         # newline-list of relpaths seen >1x: AMBIGUOUS provenance,
   839	                             # rejected entirely (NOT first-wins) — Codex R1 P0#2 fold.
   840	
   990	        # Duplicate relpath? Ambiguous provenance — invalidate ENTIRELY
   991	        # (not first-wins): the lookup refuses it -> fallback. (Codex R1 P0#2)
   992	        case "$_BASELINE_DUP_GUARD" in
   993	          *"
   994	$rel
   995	"*)
   996	            case "$_BASELINE_INVALID" in
   997	              *"
   998	$rel
   999	"*) ;;
  1000	              *) _BASELINE_INVALID="$_BASELINE_INVALID
  1001	$rel
  1002	" ;;
  1003	            esac
  1004	            continue ;;
  1005	        esac
  1006	        _BASELINE_DUP_GUARD="$_BASELINE_DUP_GUARD
  1007	$rel
  1008	"
  1009	        printf '%s  %s\n' "$digest" "$rel" >> "$sanitized"
  1010	        ;;
  1011	    esac
  1012	  done < "$_BASELINE_MANIFEST_RAW"
  1013	
  1014	  if [ -s "$sanitized" ]; then
  1015	    _BASELINE_MANIFEST_FILE="$sanitized"
  1016	  else
  1017	    rm -f "$sanitized" 2>/dev/null || true
  1018	  fi
  1019	  return 0
  1020	}
  1021	
  1022	# Echo the baseline digest for $1 if (and only if) it is a validated HASH
  1023	# record. A LINK record or an absent line echoes nothing + returns 1 => the
  1024	# caller falls back. Exact relpath match (the part after the two-space
  1025	# separator must equal $1 exactly). awk does the exact match + 64-hex check in
  1026	# one pass — no fragile nested while/case under set -u.
  1027	_baseline_lookup() {
  1028	  _bl_rel="$1"
  1029	  [ -n "$_BASELINE_MANIFEST_FILE" ] || return 1
  1030	  [ -f "$_BASELINE_MANIFEST_FILE" ] || return 1
  1031	  # Refuse a relpath flagged as duplicate/ambiguous during load (Codex R1 P0#2):
  1032	  # never trust a baseline digest for a relpath that appeared more than once.
  1033	  case "$_BASELINE_INVALID" in
  1034	    *"
  1035	$_bl_rel
  1036	"*) return 1 ;;
  1037	  esac
  1038	  _bl_digest="$( awk -v want="$_bl_rel" '
  1039	    {
  1040	      # Split on the FIRST double-space: field1 = digest-or-LINK, rest = path[+target].
  1041	      idx = index($0, "  ");
  1042	      if (idx == 0) next;
  1043	      d = substr($0, 1, idx - 1);
  1044	      rest = substr($0, idx + 2);
  1045	      if (d == "LINK") next;                 # link record: no content baseline
  1046	      # rest must equal the wanted relpath exactly (hash records have no 2nd
  1047	      # double-space: relpath runs to EOL).
  1048	      if (rest != want) next;
  1049	      if (length(d) != 64) next;
  1050	      if (d ~ /^[0-9a-f]+$/) { print d; exit 0 }
  1051	    }
  1052	  ' "$_BASELINE_MANIFEST_FILE" 2>/dev/null )"
  1053	  [ -n "$_bl_digest" ] || return 1
  1054	  printf '%s\n' "$_bl_digest"
  1055	}
  1056	
  1057	# Classify a single repo-relative file against the baseline. Echoes ONE verdict:
  1058	#   FRAMEWORK-CHANGED  H_dst==H_base && H_src!=H_base  -> safe to auto-update
  1059	#   ADOPTER-CUSTOMIZED H_dst!=H_base && H_src==H_base  -> preserve
  1060	#   CONFLICT           both differ from H_base         -> --on-conflict
  1061	#   IDENTICAL          H_dst==H_src                    -> nothing to do
  1062	#   FALLBACK           no usable baseline / hasher      -> today's behavior
  1063	# H_dst and H_src are BOTH recomputed from disk THIS run (never cached H_src).
  1064	_classify_against_baseline() {
  1065	  _cab_rel="$1"
  1066	  command -v _hash_file >/dev/null 2>&1 || { printf 'FALLBACK\n'; return 0; }
  1067	  _cab_base="$( _baseline_lookup "$_cab_rel" )" || { printf 'FALLBACK\n'; return 0; }
  1068	  _cab_dst="$( _hash_file "$TARGET/$_cab_rel" 2>/dev/null || true )"
  1069	  _cab_src="$( _hash_file "$SOURCE_DIR/$_cab_rel" 2>/dev/null || true )"
  1070	  # If either side cannot be hashed (missing file), fall back to legacy handling.
  1071	  if [ -z "$_cab_dst" ] || [ -z "$_cab_src" ]; then
  1072	    printf 'FALLBACK\n'; return 0
  1073	  fi
  1074	  if [ "$_cab_dst" = "$_cab_src" ]; then
  1075	    printf 'IDENTICAL\n'; return 0
  1076	  fi
  1077	  if [ "$_cab_dst" = "$_cab_base" ] && [ "$_cab_src" != "$_cab_base" ]; then
  1078	    printf 'FRAMEWORK-CHANGED\n'; return 0
  1079	  fi
  1080	  if [ "$_cab_dst" != "$_cab_base" ] && [ "$_cab_src" = "$_cab_base" ]; then
  1081	    printf 'ADOPTER-CUSTOMIZED\n'; return 0
  1082	  fi
  1083	  # Both differ from the baseline.
  1084	  printf 'CONFLICT\n'; return 0
  1085	}
  1086	
  1087	_load_baseline_manifest
  1088	
  1089	# PLAN-161 U1 (codex r1 F4) — manifest-load observability. Byte-identity alone
  1090	# cannot prove a --dry-run kept provenance classification alive (a dry-run
  1091	# that silently lost the baseline would also write nothing), so EVERY run
  1092	# states which classification mode it operates in.
  1093	if [ -n "$_BASELINE_MANIFEST_FILE" ]; then
  1094	  echo "==> Baseline manifest: loaded (provenance classification ACTIVE)"
  1095	else
  1096	  echo "==> Baseline manifest: none — fallback diff -q classification"
  1097	fi
  1098	
  1099	# F-CHAOS-3: match a relative path against the --skip globs list.
  1100	# Returns 0 (true) if matched.
  1101	_path_is_skipped() {
  1102	  local rel="$1"
  1103	  local pattern
  1104	  for pattern in "${SKIP_GLOBS[@]:-}"; do
  1105	    [[ -n "$pattern" ]] || continue
  1106	    # Intentional unquoted glob match (the whole point of --skip patterns).
  1107	    # shellcheck disable=SC2053,SC2254
  1108	    case "$rel" in
  1109	      $pattern) return 0 ;;
  1110	    esac
  1111	  done
  1112	  return 1
  1113	}
  1114	
  1115	# F-CHAOS-3: emit a diff-q-style WARNING line for every adopter file
  1116	# that differs from the source before we overwrite it. Recurses into
  1117	# directories. Respects --no-diff-warn and --skip globs.
  1118	_emit_diff_warnings() {
  1119	  local rel_path="$1"
  1120	  local src="$SOURCE_DIR/$rel_path"

--- MANIFEST LIB FINAL ---
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
   191	        find "$_fms_abs" \( -type f -o -type l \) -print 2>/dev/null | while IFS= read -r _fms_hit; do
   192	          # Strip the "$_fms_root/" prefix to get a repo-relative path.
   193	          _fms_rel="${_fms_hit#"$_fms_root"/}"
   194	          printf '%s\n' "$_fms_rel"
   195	        done
   196	      fi
   197	      # else: entry absent on disk for this profile — skip (profile-aware).
   198	    done
   199	  } | grep -v -e '^\.claude/\.install-manifest\.sha256$' \
   200	            -e '^\.claude\.bak/' \
   201	            -e '/\.claude\.bak/' \
   202	            -e '/__pycache__/' \
   203	            -e '\.pyc$' \
   204	    | while IFS= read -r _fms_out; do
   205	        # PLAN-161 U2 (CF-7): never record framework-internal excluded paths
   206	        # in the baseline — recording them would legitimize a mis-install
   207	        # (and the upgrade would re-add what an adopter deleted by hand).
   208	        if ! _framework_path_excluded "$_fms_out"; then
   209	          printf '%s\n' "$_fms_out"
   210	        fi
   211	      done \
   212	    | LC_ALL=C sort -u
   213	}
   214	
   215	# _write_baseline_manifest — THE single baseline-manifest generator (ADR-155
   216	# decision (iv)). Called by install.sh write_install_manifest AND by upgrade.sh
   217	# after a successful upgrade, so a long-lived adopter who upgrades but never
   218	# re-runs install.sh acquires/refreshes a manifest.
   219	#
   220	# Inputs (callers export these before calling):
   221	#   FMS_ROOT          — the installed target root (paths are relative to it)
   222	#   FMS_PROFILE_PARTS — space-separated profile list (profile-aware enumeration)
   223	#   FMS_MODE          — "link" to emit LINK records for symlinks, else "copy"
   224	# Requires _hash_file (from _hash_lib.sh) on PATH. Writes validated records to
   225	# $1 (the manifest path) atomically. Fail-open: returns 0 with a stderr NOTE on
   226	# any problem; never aborts the caller.
   227	#
   228	# Grammar:
   229	#   <64hex>  <relpath>          — content hash
   230	#   LINK  <relpath>  <target>   — link-mode symlink (content == source)
   231	
   232	# Does FMS_HASH_ROOT apply to this relpath? UNSET FMS_HASH_ROOT_PATHS means
   233	# ALL of them — the upgrade posture, where every enumerated file must record
   234	# what the framework SHIPS. install.sh needs the opposite default for most of
   235	# the tree: it RENDERS templates (`.claude/team.md`, skills, `{{X}}`
   236	# placeholders under --project et al), so those legitimately differ from
   237	# source and their baseline must be the rendered TARGET. A global
   238	# FMS_HASH_ROOT on an install rerun rewrote every rendered file's hash to the
   239	# unrendered source, which doctor.sh reads as widespread adopter drift and
   240	# later upgrades read as customized => the files stop being refreshed (codex
   241	# W1 round 8, P1). Scoping the override to the ownership-continuity paths
   242	# keeps the round-5 fix (an EDITED delivered SPEC must not be re-baselined as
   243	# framework-owned, or uninstall would delete the adopter's fork) without
   244	# touching the rendered tree. Prefix match: an entry covers the path itself
   245	# and everything under it.
   246	_wbm_hash_root_applies() {
   247	  [ -n "${FMS_HASH_ROOT_PATHS:-}" ] || return 0
   248	  _hra_rel="$1"
   249	  _hra_oldIFS="$IFS"
   250	  IFS='
   251	'
   252	  for _hra_p in $FMS_HASH_ROOT_PATHS; do
   253	    [ -n "$_hra_p" ] || continue
   254	    case "$_hra_rel" in
   255	      "$_hra_p"|"$_hra_p"/*)
   256	        IFS="$_hra_oldIFS"
   257	        return 0
   258	        ;;
   259	    esac
   260	  done
   261	  IFS="$_hra_oldIFS"
   262	  return 1
   263	}
   264	
   265	# May this relpath be serialized as a LINK record? UNSET FMS_LINK_PATHS means
   266	# ANY live symlink may — correct on the INSTALL path, where the installer
   267	# itself created every symlink it is about to record. On the UPGRADE rewrite
   268	# that default is too wide (codex W1 round 10, P2): FMS_MODE=link is inferred
   269	# from the presence of ANY prior LINK record, and every live symlink then
   270	# serializes as a delivery record — including an adopter's OWN symlink
   271	# preserved inside an enumerated directory like `.claude/hooks/`, converting
   272	# an unowned path into framework-managed content that doctor.sh polices.
   273	# upgrade.sh passes the exact set of pre-upgrade LINK relpaths instead.
   274	_wbm_link_allowed() {
   275	  [ -n "${FMS_LINK_PATHS:-}" ] || return 0
   276	  _wla_rel="$1"
   277	  _wla_oldIFS="$IFS"
   278	  IFS='
   279	'
   280	  for _wla_p in $FMS_LINK_PATHS; do
   281	    [ -n "$_wla_p" ] || continue
   282	    if [ "$_wla_rel" = "$_wla_p" ]; then
   283	      IFS="$_wla_oldIFS"
   284	      return 0
   285	    fi
   286	  done
   287	  IFS="$_wla_oldIFS"
   288	  return 1
   289	}
   290	
   291	# --- PLAN-167 W2.3: the DECISION reaches the generator ----------------------
   292	# _ownership_verdict chooses a hash_source per conditional surface; the writer
   293	# obeys it instead of falling back to a default. Across all 62 rows of the
   294	# table the default (HASH_TARGET) is never the correct answer, and it is
   295	# exactly what let three P1 defects re-baseline adopter content as
   296	# framework-owned (docs §3.4).
   297	_wbm_declared_hash_source() {
   298	  case "$1" in
   299	    SPEC/v1|SPEC/v1/*)          printf '%s' "${FMS_HASH_SOURCE_SPEC:-}" ;;
   300	    PROTOCOL.md)                printf '%s' "${FMS_HASH_SOURCE_PROTOCOL:-}" ;;
   301	    .claude/.framework-version) printf '%s' "${FMS_HASH_SOURCE_MARKER:-}" ;;
   302	    *)                          printf '' ;;
   303	  esac
   304	}
   305	
   306	_wbm_is_conditional() {
   307	  case "$1" in
   308	    SPEC/v1|SPEC/v1/*|PROTOCOL.md|.claude/.framework-version) return 0 ;;
   309	  esac
   310	  return 1
   311	}
   312	
   313	# The digest the PRE-run manifest recorded. Empty when unavailable, which the
   314	# fail-closed branch turns into "do not record" rather than a guess.
   315	_wbm_prior_digest() {
   316	  [ -n "${FMS_PRIOR_MANIFEST:-}" ] && [ -f "$FMS_PRIOR_MANIFEST" ] || { printf ''; return 0; }
   317	  grep -E "^[0-9a-f]{64}  $1\$" "$FMS_PRIOR_MANIFEST" 2>/dev/null | head -1 | cut -d' ' -f1 || printf ''
   318	}
   319	
   320	_write_baseline_manifest() {
   321	  _wbm_manifest="$1"
   322	  if ! command -v _framework_manifest_files >/dev/null 2>&1 \
   323	     || ! command -v _hash_file >/dev/null 2>&1; then
   324	    echo "    NOTE: baseline manifest skipped — hash/enumeration helpers not sourced" >&2
   325	    return 0
   326	  fi
   327	  : "${FMS_ROOT:?_write_baseline_manifest requires FMS_ROOT}"
   328	  # FMS_HASH_ROOT (optional): hash the FRAMEWORK version of each file from here
   329	  # instead of FMS_ROOT. The ENUMERATION still walks FMS_ROOT (what the target
   330	  # holds), but the recorded baseline must be what the framework SHIPS — never
   331	  # an adopter-customized target file. Without this, upgrade.sh's post-upgrade
   332	  # rewrite (C.7) records hash(customized-but-preserved file) as the baseline,
   333	  # which the NEXT upgrade reads as H_dst==H_base => FRAMEWORK-CHANGED => clobber
   334	  # (the verified C.5 idempotency failure). Default = FMS_ROOT (install path,
   335	  # where the target IS the freshly-written framework version). The root
   336	  # PROTOCOL.md is GENERATED (a pointer), not a source copy, so it always hashes
   337	  # from FMS_ROOT (the target pointer), never FMS_HASH_ROOT. (Codex R1 + dry-run)
   338	  _wbm_hash_root="${FMS_HASH_ROOT:-$FMS_ROOT}"
   339	
   340	  _wbm_tmp="$( mktemp "$_wbm_manifest.XXXXXX" 2>/dev/null )" || {
   341	    echo "    NOTE: baseline manifest skipped (mktemp failed) — advisory only" >&2
   342	    return 0
   343	  }
   344	
   345	  _framework_manifest_files | while IFS= read -r _wbm_rel; do
   346	    [ -n "$_wbm_rel" ] || continue
   347	    _wbm_abs="$FMS_ROOT/$_wbm_rel"
   348	    # Drop relpaths carrying control chars (line-based manifest).
   349	    case "$_wbm_rel" in
   350	      *[$'\n\r\t']*) continue ;;
   351	    esac
   352	    if [ "${FMS_MODE:-copy}" = "link" ] && [ -L "$_wbm_abs" ] \
   353	       && _wbm_link_allowed "$_wbm_rel"; then
   354	      _wbm_target="$( readlink "$_wbm_abs" 2>/dev/null || true )"
   355	      [ -n "$_wbm_target" ] || continue
   356	      case "$_wbm_target" in
   357	        *[$'\n\r\t']*) continue ;;
   358	      esac
   359	      printf 'LINK  %s  %s\n' "$_wbm_rel" "$_wbm_target" >> "$_wbm_tmp"
   360	    elif [ -f "$_wbm_abs" ]; then
   361	      if [ "$_wbm_rel" = "PROTOCOL.md" ]; then
   362	        # Generated pointer. Use the CANONICAL pointer hash (FMS_PROTOCOL_HASH,
   363	        # exported by upgrade.sh _refresh_protocol_pointer) so a PRESERVED
   364	        # adopter-customized PROTOCOL.md is NOT re-recorded as its own baseline
   365	        # (Codex R2 P0 — else the next upgrade reads H_dst==H_base and clobbers
   366	        # it). On install (no FMS_PROTOCOL_HASH) the target IS the freshly
   367	        # written pointer, so hashing it directly is correct.
   368	        if [ -n "${FMS_PROTOCOL_HASH:-}" ]; then
   369	          _wbm_digest="$FMS_PROTOCOL_HASH"
   370	        else
   371	          _wbm_digest="$( _hash_file "$_wbm_abs" 2>/dev/null || true )"
   372	        fi
   373	      elif _wbm_is_conditional "$_wbm_rel"; then
   374	        _wbm_decl="$( _wbm_declared_hash_source "$_wbm_rel" )"
   375	        case "$_wbm_decl" in
   376	          HASH_SOURCE)
   377	            # FMS_SOURCE_ROOT, never FMS_HASH_ROOT: the global override is an
   378	            # upgrade-only mechanism, and borrowing it here is what dragged
   379	            # install into the r8-F1 rendered-tree regression.
   380	            if [ -n "${FMS_SOURCE_ROOT:-}" ] && [ -f "$FMS_SOURCE_ROOT/$_wbm_rel" ]; then
   381	              _wbm_digest="$( _hash_file "$FMS_SOURCE_ROOT/$_wbm_rel" 2>/dev/null || true )"
   382	            else
   383	              continue   # the framework no longer ships it: record nothing
   384	            fi
   385	            ;;
   386	          HASH_PRIOR_RECORD)   _wbm_digest="$( _wbm_prior_digest "$_wbm_rel" )" ;;
   387	          HASH_CANONICAL_POINTER) _wbm_digest="${FMS_PROTOCOL_HASH:-}" ;;
   388	          HASH_TARGET)         _wbm_digest="$( _hash_file "$_wbm_abs" 2>/dev/null || true )" ;;
   389	          HASH_NONE)           continue ;;
   390	          *)
   391	            # FAIL-CLOSED, scoped to the three conditional surfaces (Owner
   392	            # ratified 2026-08-07). Under-claiming is recoverable; over-claiming
   393	            # is the delete-the-adopter's-file class.
   394	            echo "    NOTE: $_wbm_rel delivered but declared no hash_source —" >&2
   395	            echo "          NOT recorded (fail-closed; ownership under-claimed)" >&2
   396	            continue
   397	            ;;
   398	        esac
   399	        case "$_wbm_digest" in
   400	          "" ) continue ;;
   401	        esac
   402	      else
   403	        # Hash the FRAMEWORK version. When FMS_HASH_ROOT is set (upgrade) and the
   404	        # path is ABSENT there, the framework no longer ships it — OMIT it from
   405	        # the baseline (recording the adopter-retained target file would falsely
   406	        # mark it FRAMEWORK-CHANGED if the framework later reintroduces the
   407	        # path). Codex R2 P1.
   408	        _wbm_hash_path="$_wbm_abs"
   409	        if [ -n "${FMS_HASH_ROOT:-}" ] && _wbm_hash_root_applies "$_wbm_rel"; then
   410	          if [ -f "$_wbm_hash_root/$_wbm_rel" ]; then
   411	            _wbm_hash_path="$_wbm_hash_root/$_wbm_rel"
   412	          else
   413	            continue   # framework no longer ships this path — no baseline record
   414	          fi
   415	        fi
   416	        _wbm_digest="$( _hash_file "$_wbm_hash_path" 2>/dev/null || true )"
   417	      fi
   418	      case "$_wbm_digest" in
   419	        [0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]) ;;
   420	        *) continue ;;
   421	      esac
   422	      printf '%s  %s\n' "$_wbm_digest" "$_wbm_rel" >> "$_wbm_tmp"
   423	    fi
   424	  done
   425	
   426	  LC_ALL=C sort -u "$_wbm_tmp" > "$_wbm_tmp.sorted" 2>/dev/null && mv "$_wbm_tmp.sorted" "$_wbm_tmp"
   427	  if mv "$_wbm_tmp" "$_wbm_manifest"; then
   428	    echo "    WROTE: $( wc -l < "$_wbm_manifest" | tr -d ' ' ) baseline records -> $_wbm_manifest"
   429	  else
   430	    rm -f "$_wbm_tmp" "$_wbm_tmp.sorted" 2>/dev/null || true
   431	    echo "    NOTE: baseline manifest atomic mv failed — advisory only" >&2
   432	  fi
   433	  return 0
   434	}
   435	
   436	# =============================================================================
   437	# PLAN-167 — _ownership_verdict: THE ownership decision.
   438	#
   439	# install.sh and upgrade.sh stop deciding and start executing. Every defect in
   440	# the 35-finding S296 review series was a cell of this space whose answer was
   441	# decided branch-locally, so two branches could disagree about the same
   442	# question and nothing detected it.
   443	#
   444	#   $1 surface        spec | protocol | marker
   445	#   $2 prior_record   none | hash | link_match | link_retargeted
   446	#   $3 live_type      absent | dir | dir_empty | regular | symlink | special
   447	#                     | ancestor_symlink
   448	#   $4 live_content   pristine | legacy_pristine | legacy_pristine_partial
   449	#                     | edited | -
   450	#   $5 source_has     yes | no
   451	#   $6 mode           copy | link
   452	#   $7 ceremony       user | maintainer
   453	#   $8 operation      install_fresh | install_rerun | upgrade
   454	#   $9 skip_requested none | self | descendant
   455	#
   456	#   stdout: "<VERDICT> <HASH_SOURCE>", rc 0
   457	#   rc 1, no output: a combination the legality rules forbid.
   458	#
   459	# PURE: no filesystem, no globals, no environment. Callers observe the nine
   460	# dimensions and pass them in. That purity is what lets the same table drive a
   461	# millisecond unit oracle as well as the ~25-minute end-to-end suite; S296 had
   462	# only the slow instrument, at one cell per ~40-minute round.
   463	#
   464	# ABORT_SURFACE is deliberately NOT produced here (round-1 consensus C2). A
   465	# failed backup is not a property of these nine dimensions — it is the CALLER
   466	# failing to carry out a verdict it was handed. And per INV-3 that failure
   467	# NEVER advances the record: recording a delivery that did not happen is the
   468	# over-claiming direction ADR-155-AMEND-1 §3 forbids.
   469	#
   470	# Contract: docs/ownership-decision-table.md · Truth: scripts/tests/ownership_table.tsv
   471	# =============================================================================
   472	_ownership_verdict() {
   473	  _ov_surface="$1"; _ov_prior="$2";  _ov_ltype="$3"; _ov_lcontent="$4"
   474	  _ov_shas="$5";    _ov_mode="$6";   _ov_cer="$7";   _ov_op="$8"; _ov_skip="$9"
   475	
   476	  # Do not touch the surface; decide the RECORD. Ownership continuity and the
   477	  # digit it carries are separate decisions, and moving one without the other
   478	  # produced four distinct defects — so they are resolved together, once.
   479	  _ov_carry() {
   480	    case "$_ov_prior" in
   481	      link_match)      printf 'PRESERVE_OWNED LINK_RECORD';  return 0 ;;
   482	      link_retargeted) printf 'PRESERVE_UNOWNED HASH_NONE'; return 0 ;;
   483	      none)            printf 'PRESERVE_UNOWNED HASH_NONE';  return 0 ;;
   484	    esac
   485	    # prior_record=hash. HASH_TARGET is never an option: it re-baselines the
   486	    # bytes now on disk, which is how a later upgrade comes to overwrite an
   487	    # adopter edit and uninstall comes to delete it.
   488	    if [ "$_ov_surface" = "protocol" ] \
   489	       || [ "$_ov_shas" = "no" ] \
   490	       || [ "$_ov_ltype" = "dir_empty" ]; then
   491	      printf 'PRESERVE_OWNED HASH_PRIOR_RECORD'   # no source bytes to hash
   492	    else
   493	      printf 'PRESERVE_OWNED HASH_SOURCE'
   494	    fi
   495	  }
   496	
   497	  # The framework must not claim this path. Whether a record existed changes
   498	  # only which NAME the observation takes (OQ-9 — the evidence that these are
   499	  # one outcome, not two).
   500	  # OQ-9 (ratificada pelo Owner 2026-08-07): PRESERVE_UNOWNED é o único nome.

--- INSTALL FINAL MANIFEST ---
  2370	.claude/.framework-version"
  2371	    echo "    ownership continuity: .framework-version delivery record preserved from prior manifest"
  2372	  fi
  2373	  # For the continuity-preserved paths ONLY, hash the FRAMEWORK's pristine
  2374	  # copies instead of the (possibly edited) target's (codex W1 round 5, P1):
  2375	  # install normally hashes FMS_ROOT=$TARGET — on a rerun over an EDITED
  2376	  # delivered SPEC that would re-baseline the fork's bytes as framework-owned,
  2377	  # and a later uninstall would happily DELETE the user's modified tree (its
  2378	  # hash matches the manifest). Same C.5 idempotency posture upgrade.sh uses.
  2379	  #
  2380	  # SCOPED, not global (codex W1 round 8, P1): install RENDERS templates
  2381	  # (`.claude/team.md`, skills, `{{X}}` placeholders under --project et al),
  2382	  # so a global FMS_HASH_ROOT rewrote every rendered file's baseline to the
  2383	  # UNRENDERED source — doctor.sh then reports repo-wide adopter drift and
  2384	  # later upgrades classify those files as customized and stop refreshing
  2385	  # them. PLAN-167 W2.3 replaced that confinement with an EXPLICIT per-surface
  2386	  # hash_source: the decision says which paths take the framework's bytes,
  2387	  # so no global override is set here at all.
  2388	  if [[ "${_CONTINUITY_FIRED:-0}" = "1" ]]; then
  2389	    : # per-surface hash_source below replaces the global override
  2390	    case "$_CONTINUITY_PATHS" in
  2391	      *".claude/.framework-version"*) export FMS_HASH_SOURCE_MARKER="HASH_SOURCE" ;;
  2392	    esac
  2393	    case "$_CONTINUITY_PATHS" in
  2394	      # The generated pointer has no source bytes; carry what was recorded.
  2395	      *"PROTOCOL.md"*)               export FMS_HASH_SOURCE_PROTOCOL="HASH_PRIOR_RECORD" ;;
  2396	    esac
  2397	    echo "    ownership continuity: manifest hashes the preserved paths from the framework source (edited target content stays adopter-owned; rendered files keep their target hash)"
  2398	  fi
  2399	  # Declare on EVERY delivery path, not only continuity. A fresh install
  2400	  # genuinely delivers these surfaces, and the previous attempt at this wave
  2401	  # regressed 24 cells precisely because it left fresh installs undeclared.
  2402	  #
  2403	  # Fresh delivery: the target IS the bytes just written, so HASH_TARGET is
  2404	  # both correct and observationally identical to HASH_SOURCE.
  2405	  # Continuity: the target may be an EDITED fork, so the record must come from
  2406	  # the framework's copy (spec/marker) or the prior record (the generated
  2407	  # pointer, which has no source file).
  2408	  export FMS_SOURCE_ROOT="$SOURCE_DIR"
  2409	  export FMS_PRIOR_MANIFEST="$manifest"
  2410	  if [[ "${_DELIVERED_SPEC:-0}" = "1" ]]; then
  2411	    case "${_CONTINUITY_PATHS:-}" in
  2412	      *"SPEC/v1"*) export FMS_HASH_SOURCE_SPEC="HASH_SOURCE" ;;
  2413	      *)           export FMS_HASH_SOURCE_SPEC="HASH_TARGET" ;;
  2414	    esac
  2415	  fi
  2416	  if [[ "${_DELIVERED_MARKER:-0}" = "1" ]]; then
  2417	    case "${_CONTINUITY_PATHS:-}" in
  2418	      *".claude/.framework-version"*) export FMS_HASH_SOURCE_MARKER="HASH_SOURCE" ;;
  2419	      *)                              export FMS_HASH_SOURCE_MARKER="HASH_TARGET" ;;
  2420	    esac
  2421	  fi
  2422	  if [[ "${_DELIVERED_PROTOCOL:-0}" = "1" ]]; then
  2423	    case "${_CONTINUITY_PATHS:-}" in
  2424	      *"PROTOCOL.md"*) export FMS_HASH_SOURCE_PROTOCOL="HASH_PRIOR_RECORD" ;;
  2425	      *)               export FMS_HASH_SOURCE_PROTOCOL="HASH_TARGET" ;;
  2426	    esac
  2427	  fi
  2428	  export FMS_DELIVERED_SPEC="${_DELIVERED_SPEC:-0}"
  2429	  export FMS_DELIVERED_PROTOCOL="${_DELIVERED_PROTOCOL:-0}"
  2430	  export FMS_DELIVERED_MARKER="${_DELIVERED_MARKER:-0}"
  2431	  # Empty on a fresh install (target IS the freshly written pointer, hashing it
  2432	  # is correct); set only by the continuity path above.
  2433	  export FMS_PROTOCOL_HASH="${_PRIOR_PROTOCOL_HASH:-}"
  2434	  _write_baseline_manifest "$manifest"
  2435	  unset FMS_ROOT FMS_PROFILE_PARTS FMS_MODE FMS_HASH_ROOT FMS_PROTOCOL_HASH \
  2436	        FMS_PRIOR_MANIFEST FMS_HASH_SOURCE_SPEC FMS_HASH_SOURCE_PROTOCOL \
  2437	        FMS_HASH_SOURCE_MARKER
  2438	  unset FMS_DELIVERED_SPEC FMS_DELIVERED_PROTOCOL FMS_DELIVERED_MARKER
  2439	  return 0
  2440	}
  2441	
  2442	
  2443	# ----------------------------------------------------------------------
  2444	# PLAN-153 Wave B item B1 — persist the install-state.
  2445	# ----------------------------------------------------------------------
  2446	# Writes $TARGET/.claude/.install-state.json (next to the ADR-155 baseline
  2447	# manifest): the ORIGINAL request — verbatim argv + every parsed flag + the
  2448	# RESOLVED placeholder map (CLI > env > deterministic default; empty values
  2449	# omitted) — plus the operation journal for THIS run.
  2450	#
  2451	#   * Atomic: python writes a same-directory tempfile, then os.replace().
  2452	#   * Updated on every run: first_recorded_at + run_count + a bounded
  2453	#     history (last 20 runs) survive re-installs; request/operations
  2454	#     reflect the LATEST run.
  2455	#   * Schema-versioned: schema ceo.install-state/v1, schema_version 1.
  2456	#   * Consumed by upgrade.sh (PLAN-153 B2): request.profile/request.stack
  2457	#     become upgrade DEFAULTS when its own flags are omitted. A missing or
  2458	#     invalid state file degrades upgrade.sh to the ADR-155 drift-classifier
  2459	#     path — never an error, never a no-op (debate C back-compat must-fix).
  2460	#   * TRUST: target-side, UNSIGNED, advisory — the same trust class as the

exec
/bin/zsh -lc "nl -ba scripts/_framework_manifest_set.sh | sed -n '80,240p;470,680p'" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
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
   191	        find "$_fms_abs" \( -type f -o -type l \) -print 2>/dev/null | while IFS= read -r _fms_hit; do
   192	          # Strip the "$_fms_root/" prefix to get a repo-relative path.
   193	          _fms_rel="${_fms_hit#"$_fms_root"/}"
   194	          printf '%s\n' "$_fms_rel"
   195	        done
   196	      fi
   197	      # else: entry absent on disk for this profile — skip (profile-aware).
   198	    done
   199	  } | grep -v -e '^\.claude/\.install-manifest\.sha256$' \
   200	            -e '^\.claude\.bak/' \
   201	            -e '/\.claude\.bak/' \
   202	            -e '/__pycache__/' \
   203	            -e '\.pyc$' \
   204	    | while IFS= read -r _fms_out; do
   205	        # PLAN-161 U2 (CF-7): never record framework-internal excluded paths
   206	        # in the baseline — recording them would legitimize a mis-install
   207	        # (and the upgrade would re-add what an adopter deleted by hand).
   208	        if ! _framework_path_excluded "$_fms_out"; then
   209	          printf '%s\n' "$_fms_out"
   210	        fi
   211	      done \
   212	    | LC_ALL=C sort -u
   213	}
   214	
   215	# _write_baseline_manifest — THE single baseline-manifest generator (ADR-155
   216	# decision (iv)). Called by install.sh write_install_manifest AND by upgrade.sh
   217	# after a successful upgrade, so a long-lived adopter who upgrades but never
   218	# re-runs install.sh acquires/refreshes a manifest.
   219	#
   220	# Inputs (callers export these before calling):
   221	#   FMS_ROOT          — the installed target root (paths are relative to it)
   222	#   FMS_PROFILE_PARTS — space-separated profile list (profile-aware enumeration)
   223	#   FMS_MODE          — "link" to emit LINK records for symlinks, else "copy"
   224	# Requires _hash_file (from _hash_lib.sh) on PATH. Writes validated records to
   225	# $1 (the manifest path) atomically. Fail-open: returns 0 with a stderr NOTE on
   226	# any problem; never aborts the caller.
   227	#
   228	# Grammar:
   229	#   <64hex>  <relpath>          — content hash
   230	#   LINK  <relpath>  <target>   — link-mode symlink (content == source)
   231	
   232	# Does FMS_HASH_ROOT apply to this relpath? UNSET FMS_HASH_ROOT_PATHS means
   233	# ALL of them — the upgrade posture, where every enumerated file must record
   234	# what the framework SHIPS. install.sh needs the opposite default for most of
   235	# the tree: it RENDERS templates (`.claude/team.md`, skills, `{{X}}`
   236	# placeholders under --project et al), so those legitimately differ from
   237	# source and their baseline must be the rendered TARGET. A global
   238	# FMS_HASH_ROOT on an install rerun rewrote every rendered file's hash to the
   239	# unrendered source, which doctor.sh reads as widespread adopter drift and
   240	# later upgrades read as customized => the files stop being refreshed (codex
   470	# Contract: docs/ownership-decision-table.md · Truth: scripts/tests/ownership_table.tsv
   471	# =============================================================================
   472	_ownership_verdict() {
   473	  _ov_surface="$1"; _ov_prior="$2";  _ov_ltype="$3"; _ov_lcontent="$4"
   474	  _ov_shas="$5";    _ov_mode="$6";   _ov_cer="$7";   _ov_op="$8"; _ov_skip="$9"
   475	
   476	  # Do not touch the surface; decide the RECORD. Ownership continuity and the
   477	  # digit it carries are separate decisions, and moving one without the other
   478	  # produced four distinct defects — so they are resolved together, once.
   479	  _ov_carry() {
   480	    case "$_ov_prior" in
   481	      link_match)      printf 'PRESERVE_OWNED LINK_RECORD';  return 0 ;;
   482	      link_retargeted) printf 'PRESERVE_UNOWNED HASH_NONE'; return 0 ;;
   483	      none)            printf 'PRESERVE_UNOWNED HASH_NONE';  return 0 ;;
   484	    esac
   485	    # prior_record=hash. HASH_TARGET is never an option: it re-baselines the
   486	    # bytes now on disk, which is how a later upgrade comes to overwrite an
   487	    # adopter edit and uninstall comes to delete it.
   488	    if [ "$_ov_surface" = "protocol" ] \
   489	       || [ "$_ov_shas" = "no" ] \
   490	       || [ "$_ov_ltype" = "dir_empty" ]; then
   491	      printf 'PRESERVE_OWNED HASH_PRIOR_RECORD'   # no source bytes to hash
   492	    else
   493	      printf 'PRESERVE_OWNED HASH_SOURCE'
   494	    fi
   495	  }
   496	
   497	  # The framework must not claim this path. Whether a record existed changes
   498	  # only which NAME the observation takes (OQ-9 — the evidence that these are
   499	  # one outcome, not two).
   500	  # OQ-9 (ratificada pelo Owner 2026-08-07): PRESERVE_UNOWNED é o único nome.
   501	  # OMIT_RECORD dizia a mesma coisa — sem registro no disco — e diferia apenas
   502	  # por já existir registro antes, que é a coluna prior_record. Um membro de
   503	  # enum redundante é onde dois ramos discordam sobre qual deles se aplica.
   504	  _ov_unowned() { printf 'PRESERVE_UNOWNED HASH_NONE'; }
   505	
   506	  # --- Stage A: gates that refuse to act, in priority order ------------------
   507	
   508	  # A1. The source cannot deliver this surface.
   509	  if [ "$_ov_shas" = "no" ]; then
   510	    case "$_ov_surface" in
   511	      marker)   printf 'PRESERVE_UNOWNED HASH_NONE'; return 0 ;;  # --pin: readers fall back to VERSION
   512	      protocol) return 1 ;;                                  # R-03: generated, never absent
   513	      *)        _ov_carry; return 0 ;;
   514	    esac
   515	  fi
   516	
   517	  # A2. A user ceremony never receives the root surfaces (WS4).
   518	  if [ "$_ov_cer" = "user" ] && [ "$_ov_surface" != "marker" ]; then
   519	    if [ "$_ov_op" = "install_fresh" ]; then printf 'PRESERVE_UNOWNED HASH_NONE'
   520	    else _ov_carry; fi
   521	    return 0
   522	  fi
   523	
   524	  # A3. Reachable only by writing THROUGH a symlink, out of the target tree.
   525	  # Always unowned: the relpath sanitizer already dropped any record whose path
   526	  # crosses a symlink, so there is no record left to carry (docs §5.8).
   527	  if [ "$_ov_ltype" = "ancestor_symlink" ]; then _ov_unowned; return 0; fi
   528	
   529	  # A4. A leaf symlink is healthy ONLY as the recorded link-mode delivery.
   530	  # The absence of a LINK row is not a match — it is the absence of evidence.
   531	  if [ "$_ov_ltype" = "symlink" ]; then
   532	    if [ "$_ov_prior" = "link_match" ]; then printf 'PRESERVE_OWNED LINK_RECORD'
   533	    else _ov_unowned; fi
   534	    return 0
   535	  fi
   536	
   537	  # A5. Anything that exists but is not shaped like this surface is
   538	  # adopter-owned: never write into it, never through it, never block on it.
   539	  case "$_ov_surface" in
   540	    spec)
   541	      case "$_ov_ltype" in special) _ov_unowned; return 0 ;; esac ;;
   542	    protocol|marker)
   543	      case "$_ov_ltype" in dir|dir_empty|special) _ov_unowned; return 0 ;; esac ;;
   544	  esac
   545	
   546	  # A6. An explicit skip is honoured as a UNIT — a partial contract refresh is
   547	  # incoherent, so a descendant skip preserves the whole tree.
   548	  if [ "$_ov_skip" != "none" ]; then _ov_carry; return 0; fi
   549	
   550	  # --- Stage B: ownership resolution ----------------------------------------
   551	  _ov_owned=""
   552	  if [ "$_ov_prior" = "hash" ] || [ "$_ov_prior" = "link_match" ]; then
   553	    _ov_owned=1
   554	  elif [ "$_ov_ltype" = "absent" ]; then
   555	    _ov_owned=1                                   # new delivery
   556	  elif [ "$_ov_lcontent" = "pristine" ] || [ "$_ov_lcontent" = "legacy_pristine" ]; then
   557	    _ov_owned=1                                   # current-source takeover / legacy migration
   558	  fi
   559	  # legacy_pristine_partial is deliberately NOT owned: every regular file may
   560	  # match a shipped release, but a tree carrying an entry the fingerprint
   561	  # cannot inventory has not been inventoried, and a partial inventory must
   562	  # never certify a wholesale replace (ADR-155-AMEND-1 §4).
   563	
   564	  if [ -z "$_ov_owned" ]; then _ov_unowned; return 0; fi
   565	
   566	  # --- Stage C: execution ---------------------------------------------------
   567	  if [ "$_ov_ltype" = "absent" ]; then
   568	    case "$_ov_surface" in
   569	      protocol) printf 'DELIVER HASH_CANONICAL_POINTER' ;;
   570	      *)        printf 'DELIVER HASH_SOURCE' ;;
   571	    esac
   572	    return 0
   573	  fi
   574	
   575	  # An install rerun does not re-deliver an existing surface; it decides the
   576	  # record. Only the upgrade's forced route replaces content.
   577	  if [ "$_ov_op" != "upgrade" ]; then _ov_carry; return 0; fi
   578	
   579	  # The pointer is the ONE surface where an adopter edit is PRESERVED rather
   580	  # than treated as a fork. SPEC/v1 is deliberately the opposite: it is the
   581	  # published compliance CONTRACT, so an edit is a fork and the forced route
   582	  # replaces it (ADR-155-AMEND-1 §4). The root PROTOCOL.md is adopter-editable
   583	  # prose, and overwriting a customised one is the verified S238 data loss that
   584	  # ADR-155 decision (iii) exists to close.
   585	  #
   586	  # The recorded digest stays CANONICAL either way: recording the customised
   587	  # bytes would make the NEXT upgrade read H_dst==H_base and clobber them.
   588	  if [ "$_ov_surface" = "protocol" ] && [ "$_ov_lcontent" = "edited" ]; then
   589	    printf 'PRESERVE_OWNED HASH_CANONICAL_POINTER'
   590	    return 0
   591	  fi
   592	
   593	  case "$_ov_surface" in
   594	    protocol) printf 'REFRESH HASH_CANONICAL_POINTER' ;;
   595	    *)        printf 'REFRESH HASH_SOURCE' ;;
   596	  esac
   597	}

exec
/bin/zsh -lc "grep -R \"OWN-0052\\|hash.*symlink\\|HASH record\\|prior hash\\|retarget\" -n scripts/tests .claude/plans/PLAN-166 .claude/plans/PLAN-167* docs 2>/dev/null | head -200; printf '\\n--- ownership unit complete ---\\n'; nl -ba scripts/tests/test-ownership-verdict-unit.sh | sed -n '1,180p'; printf '\\n--- table all ---\\n'; cat scripts/tests/ownership_table.tsv" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 186ms:
scripts/tests/test-upgrade-exclusions.sh:6:# flag (hash-gated, backed up, symlink-safe, second-run no-op).
scripts/tests/ownership_table.tsv:36:OWN-0030	spec	hash	ancestor_symlink	*	yes	copy	maintainer	upgrade	none	none	PRESERVE_UNOWNED	HASH_NONE	r2-F1	dead-branch: the continuity line here can never fire — the relpath sanitizer drops any record whose path traverses a symlink BEFORE _baseline_has_*_record is consulted
scripts/tests/ownership_table.tsv:37:OWN-0031	marker	hash	ancestor_symlink	*	yes	copy	maintainer	upgrade	none	none	PRESERVE_UNOWNED	HASH_NONE	r4-F2	dead-branch: the continuity line here can never fire — the relpath sanitizer drops any record whose path traverses a symlink BEFORE _baseline_has_*_record is consulted
scripts/tests/ownership_table.tsv:40:OWN-0034	protocol	hash	symlink	edited	yes	copy	maintainer	upgrade	none	none	PRESERVE_UNOWNED	HASH_NONE	derived	GAP: cat > follows the leaf symlink OUTSIDE the target
scripts/tests/ownership_table.tsv:43:OWN-0042	spec	link_retargeted	symlink	-	yes	link	maintainer	upgrade	none	none	PRESERVE_UNOWNED	HASH_NONE	r4-F3	redirected link must not inherit ownership; a prior record existed, so the mechanical observation is OMIT (see OQ-9)
scripts/tests/ownership_table.tsv:44:OWN-0043	marker	link_retargeted	symlink	-	yes	link	maintainer	upgrade	none	none	PRESERVE_UNOWNED	HASH_NONE	r4-F4	readers fall back to VERSION; a prior record existed, so the mechanical observation is OMIT (see OQ-9)
scripts/tests/ownership_table.tsv:51:OWN-0050	spec	link_retargeted	symlink	-	yes	link	maintainer	install_rerun	none	none	PRESERVE_UNOWNED	HASH_NONE	r10-F1	continuity must compare prior LINK target to live readlink; a prior record existed, so the mechanical observation is OMIT (see OQ-9)
scripts/tests/ownership_table.tsv:52:OWN-0051	marker	link_retargeted	symlink	-	yes	link	maintainer	install_rerun	none	none	PRESERVE_UNOWNED	HASH_NONE	r10-F1	sibling site; a prior record existed, so the mechanical observation is OMIT (see OQ-9)
scripts/tests/ownership_table.tsv:53:OWN-0052	spec	hash	symlink	-	yes	link	maintainer	install_rerun	none	none	PRESERVE_UNOWNED	HASH_NONE	r11-F1	open=r11-F1; absence of a LINK row is NOT a match
scripts/tests/ownership_table.tsv:54:OWN-0053	marker	hash	symlink	-	yes	link	maintainer	install_rerun	none	none	PRESERVE_UNOWNED	HASH_NONE	r11-F1	open=r11-F1; sibling site
scripts/tests/ownership-baseline-map.txt:52:OWN-0052   RED     exp=PRESERVE_UNOWNED/HASH_NONE              got=PRESERVE_OWNED  /LINK_RECORD            rc=0   r11-F1
scripts/tests/test-doctor.sh:277:    # Pre-fix bug: _relpath_unsafe dropped the hash record for a symlinked
scripts/tests/test-ownership-table.sh:277:  # link_retargeted one — the fixture would then agree with the expectation for
scripts/tests/test-ownership-table.sh:503:  case "$prior_record" in link_match|link_retargeted) base_mode="link" ;; esac
scripts/tests/test-ownership-table.sh:538:  if [[ "$prior_record" == "link_retargeted" && -L "$T/$rel" ]]; then
scripts/tests/test-ownership-table.sh:539:    mkdir -p "$WORK/retarget"; printf 'retargeted\n' > "$WORK/retarget/leaf"
scripts/tests/test-ownership-table.sh:540:    rm -f "$T/$rel"; ln -s "$WORK/retarget/leaf" "$T/$rel"
.claude/plans/PLAN-167/debate/round-1/security-engineer.md:261:   the open rows OWN-0052/0053 correctly pin the live OVER-claim of
.claude/plans/PLAN-167/debate/round-1/qa-architect.md:31:- **R-QA6** — SEVERITY: MEDIUM. Three protocol surface rows lack coverage for `prior_record=none` with hostile `live_type`. The table has `OWN-0032` (`protocol + hash + dir + upgrade`) and `OWN-0034` (`protocol + hash + symlink + upgrade`) but no row for `prior_record=none` with the same live types. On upgrade with `prior_record=none`, ownership logic takes a different branch (the framework treats it as unowned and skips the refresh). The skip path for `live_type=dir` on `protocol` is untested: `cat > $TARGET/PROTOCOL.md` fails with "Is a directory" under `set -euo pipefail` if the guard does not fire first. The model claims the table covers these via R-10 equivalence on `prior_record`, but `prior_record=none` is not `*` — it is an explicitly enumerated dimension value, and the branch it takes in the ownership check is structurally different from `prior_record=hash`.
.claude/plans/PLAN-167/debate/round-1/qa-architect.md:47:2. **`ancestor_symlink` + `install_rerun` coverage.** `OWN-0030/0031` cover `ancestor_symlink` for `operation=upgrade` only. `install_rerun` with an ancestor symlink is a legal cell under the legality rules (no rule prunes it), and the ownership check on `install_rerun` takes a different branch than `upgrade`. Two rows (`spec + hash + ancestor_symlink + install_rerun` and `marker + hash + ancestor_symlink + install_rerun`) are absent. The expected verdict is likely `OMIT_RECORD/HASH_NONE` for the same reason as the upgrade rows (§5.8: dead-branch, relpath sanitizer drops the record before the continuity check runs). If correct, these rows are quick GREEN confirmations; if wrong, they are the next open finding.
.claude/plans/PLAN-167/debate/round-1/qa-architect.md:55:1. **C1 (OMIT_RECORD reduction) loses the operator transition signal.** The claim is that every `OMIT_RECORD` row would read `PRESERVE_UNOWNED` if `prior_record=none`, so `OMIT_RECORD` is redundant. This is mechanically true for the filesystem outcome — neither verdict writes anything. But it erases a distinct operator signal: `OMIT_RECORD` says "I found a prior record and dropped it"; `PRESERVE_UNOWNED` says "there was never a record." The operator's next action differs. For `OWN-0028` (marker + prior hash + dir → OMIT_RECORD), the operator learning they had a marker record that was silently dropped should investigate differently from learning there was never a record. The plan's own argument for keeping `ABORT_SURFACE` separate from `PRESERVE_UNOWNED` (§3.1: "the operator must be told") applies with equal force here. C1 is architecturally clean but operationally lossy. A weaker form — "collapse OMIT_RECORD to PRESERVE_UNOWNED only in the dead-branch rows (OWN-0030/0031) where the record drop is a sanitizer artifact, not a framework decision" — would preserve the signal on the rows where it is meaningful.
.claude/plans/PLAN-167-ownership-decision-table.md:61:| `prior_record` | `none` · `hash` · `link_match` · `link_retargeted` |
.claude/plans/PLAN-167-ownership-decision-table.md:495:| 3 | symlink repontado em TODA linha | linhas `link_match` testavam `link_retargeted` | não tocar o symlink quando `prior_record=link_match` |
docs/threat-model.md:207:| **Tampering** | Canonical-path direct FS write (**T-003**, H via `_CANONICAL_GUARDS` list; hook bypass = shell-level). Audit-log corruption race (**T-002**, H via `fcntl.flock` 2.5s retry; M on timeout → breadcrumb fail-open). | Policy-DSL injection (**RR-4**, H via dual-path fallback + `CEO_POLICY_ENGINE_DISABLE=1` kill; novel-vector residual via fuzz-corpus expansion). | Adapter wire-shape drift (**T-005**, H via canonical envelope schema + 121 tests + golden fixtures). State-store poisoning via plan-id spoof (**T-001**, H via audit-log-session-derived plan-id not env var). | Skill-patch tamper via Unicode bidi/zero-width (**T-007**, H via NFKC + zero-width strip + AST validate + diff<200 + 7d shadow + hash trailer). | Judge-output tampering (**T-006**, H via cross-provider guard + position-bias + fallback scorer + golden-prompt hash pin; Tier-4 provider compromise **RR-2** OUT-OF-SCOPE). Pre-auth RCE via malicious tarball (**T-004**, H via sig-before-parse byte-identity test + 5 MiB cap + symlink refuse). |
docs/threat-model.md:1754:hash check, DoS the hook via a giant file, or symlink-traverse outside
docs/ownership-decision-table.md:87:| `link_retargeted` | a `LINK` record whose target does **not** equal the live `readlink` |
docs/ownership-decision-table.md:265:| **R-09** | `prior_record ∈ {link_match, link_retargeted}` ∧ `live_type ≠ symlink` ⇒ collapse to `link_retargeted` | `readlink` on a non-symlink yields empty, which never equals a recorded non-empty target. Keeping both would be two names for one observable state. |
docs/BRANCH-PROTECTION.md:397:can be retargeted post-publication; SHA references cannot. SHA

--- ownership unit complete ---
     1	#!/usr/bin/env bash
     2	# =============================================================================
     3	# PLAN-167 W2 — UNIT oracle for _ownership_verdict().
     4	#
     5	# The same table, the other half of the contract:
     6	#
     7	#   this script            — does the DECISION match the model?   (milliseconds)
     8	#   test-ownership-table.sh — do the callers OBSERVE the dimensions
     9	#                             correctly and EXECUTE the verdict?  (~25 minutes)
    10	#
    11	# Both are required and they fail for different reasons. A wrong decision shows
    12	# up here; a caller that reads the world wrong, or ignores the verdict it was
    13	# handed, only shows up there.
    14	#
    15	# This one exists because of how PLAN-167 was caused. In S296 the only
    16	# instrument was the slow one, one cell per ~40-minute round — a loop too long
    17	# to converge in. An oracle that answers in milliseconds is what makes
    18	# "drive the map to 100% green" a normal edit-run cycle instead of an
    19	# overnight gamble.
    20	#
    21	# Usage:
    22	#   test-ownership-verdict-unit.sh            every row
    23	#   test-ownership-verdict-unit.sh --only OWN-0013,OWN-0021
    24	#   test-ownership-verdict-unit.sh --quiet    only the summary
    25	#
    26	# Exit: 0 all rows match · 1 at least one mismatch · 2 harness/usage error.
    27	# =============================================================================
    28	set -uo pipefail
    29	
    30	SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    31	REPO_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
    32	TSV="$SCRIPT_DIR/ownership_table.tsv"
    33	LIB="$REPO_ROOT/scripts/_framework_manifest_set.sh"
    34	
    35	ONLY=""
    36	QUIET=0
    37	while [[ $# -gt 0 ]]; do
    38	  case "$1" in
    39	    --only)  ONLY="${2:-}"; shift 2 ;;
    40	    --quiet) QUIET=1; shift ;;
    41	    -h|--help) sed -n '2,26p' "${BASH_SOURCE[0]}"; exit 0 ;;
    42	    *) echo "ERROR: unknown argument: $1" >&2; exit 2 ;;
    43	  esac
    44	done
    45	
    46	[[ -f "$TSV" ]] || { echo "ERROR: table not found: $TSV" >&2; exit 2; }
    47	[[ -f "$LIB" ]] || { echo "ERROR: library not found: $LIB" >&2; exit 2; }
    48	
    49	# shellcheck source=/dev/null
    50	. "$LIB" 2>/dev/null || { echo "ERROR: cannot source $LIB" >&2; exit 2; }
    51	command -v _ownership_verdict >/dev/null 2>&1 || {
    52	  echo "ERROR: _ownership_verdict is not defined in $LIB" >&2
    53	  echo "       (W2 has not landed the function yet)" >&2
    54	  exit 2
    55	}
    56	
    57	PASS=0; FAIL=0; SKIPPED=0
    58	SKIP_IDS=""
    59	LINES=""
    60	
    61	while IFS=$'\t' read -r id surface prior_record live_type live_content \
    62	      source_has mode ceremony operation skip_requested fault \
    63	      exp_verdict exp_hash origin note; do
    64	  [[ -z "${id:-}" ]] && continue
    65	  case "$id" in \#*|id) continue ;; esac
    66	  if [[ -n "$ONLY" && ",$ONLY," != *",$id,"* ]]; then continue; fi
    67	
    68	  # Rows with an injected fault assert what the CALLER does when it cannot
    69	  # carry out a verdict. That is execution, not decision (round-1 consensus
    70	  # C2), so the pure function has nothing to say about them and the e2e suite
    71	  # covers them. Counted and named, never silently skipped: a suite that goes
    72	  # green by quietly not running rows is the vacuous-gate class.
    73	  if [[ "${fault:-none}" != "none" ]]; then
    74	    SKIPPED=$((SKIPPED+1))
    75	    SKIP_IDS+="$id "
    76	    continue
    77	  fi
    78	
    79	  got="$( _ownership_verdict "$surface" "$prior_record" "$live_type" \
    80	            "$live_content" "$source_has" "$mode" "$ceremony" \
    81	            "$operation" "$skip_requested" 2>/dev/null )"
    82	  rc=$?
    83	  exp="$exp_verdict $exp_hash"
    84	
    85	  # A non-zero return or unparseable output is a FAILURE, never a skip: a
    86	  # decision function that cannot answer for a legal cell has a hole in it,
    87	  # and a hole that reports as "not applicable" is how a gap stays invisible.
    88	  if [[ $rc -ne 0 || -z "$got" ]]; then
    89	    LINES+="$( printf '%-10s FAIL   exp=%-40s got=<no answer, rc=%s>  %s\n' "$id" "$exp" "$rc" "$origin" )"$'\n'
    90	    FAIL=$((FAIL+1)); continue
    91	  fi
    92	
    93	  if [[ "$got" == "$exp" ]]; then
    94	    PASS=$((PASS+1))
    95	    [[ "$QUIET" -eq 1 ]] || LINES+="$( printf '%-10s ok     %-40s %s\n' "$id" "$exp" "$origin" )"$'\n'
    96	  else
    97	    FAIL=$((FAIL+1))
    98	    LINES+="$( printf '%-10s FAIL   exp=%-40s got=%-40s %s\n' "$id" "$exp" "$got" "$origin" )"$'\n'
    99	  fi
   100	done < "$TSV"
   101	
   102	printf '%s' "$LINES" | LC_ALL=C sort
   103	echo ""
   104	echo "unit oracle: PASS=$PASS  FAIL=$FAIL  SKIPPED(execution-fault rows)=$SKIPPED"
   105	[[ -n "$SKIP_IDS" ]] && echo "  not decision cells, covered by the e2e: $SKIP_IDS"
   106	[[ "$FAIL" -gt 0 ]] && exit 1
   107	exit 0

--- table all ---
# PLAN-167 — ownership decision table. THIS FILE IS THE TRUTH.
# Reasoning lives in docs/ownership-decision-table.md; values live ONLY here.
# Conventions: "*" = don't-care (harness instantiates the canonical
# representative); "-" = not applicable under a §4 legality rule.
# note carries PROSE ONLY. Structured values live in columns (round-1 C1).
# `indistinguishable=` / `open=` remain annotations, never dimensions.
id	surface	prior_record	live_type	live_content	source_has	mode	ceremony	operation	skip_requested	fault	expect_verdict	expect_hash_source	origin	note
OWN-0001	spec	none	absent	-	yes	copy	maintainer	install_fresh	none	none	DELIVER	HASH_SOURCE	adr-155	indistinguishable=HASH_TARGET
OWN-0002	protocol	none	absent	-	yes	copy	maintainer	install_fresh	none	none	DELIVER	HASH_CANONICAL_POINTER	adr-155	indistinguishable=HASH_TARGET
OWN-0003	marker	none	absent	-	yes	copy	maintainer	install_fresh	none	none	DELIVER	HASH_SOURCE	adr-155-amend-1	indistinguishable=HASH_TARGET
OWN-0004	spec	none	dir	edited	yes	copy	maintainer	install_fresh	none	none	PRESERVE_UNOWNED	HASH_NONE	adr-155-amend-1	install_one EXISTS-skips; adopter tree must not be inventoried
OWN-0005	marker	none	regular	edited	yes	copy	maintainer	install_fresh	none	none	PRESERVE_UNOWNED	HASH_NONE	adr-155-amend-1	pre-existing marker is NOT a delivery
OWN-0006	spec	none	absent	-	yes	copy	user	install_fresh	none	none	PRESERVE_UNOWNED	HASH_NONE	adr-155-amend-1	WS4 guard: user ceremony never receives root surfaces
OWN-0007	protocol	none	absent	-	yes	copy	user	install_fresh	none	none	PRESERVE_UNOWNED	HASH_NONE	adr-155-amend-1	WS4 guard
OWN-0008	marker	none	absent	-	yes	copy	user	install_fresh	none	none	DELIVER	HASH_SOURCE	adr-155-amend-1	marker lives inside .claude/ — BOTH ceremonies receive it
OWN-0010	spec	hash	dir	pristine	yes	copy	maintainer	install_rerun	none	none	PRESERVE_OWNED	HASH_SOURCE	r1-F1	continuity: rerun must not drop the record
OWN-0011	protocol	hash	regular	pristine	yes	copy	maintainer	install_rerun	none	none	PRESERVE_OWNED	HASH_PRIOR_RECORD	r1-F1	continuity
OWN-0012	marker	hash	regular	pristine	yes	copy	maintainer	install_rerun	none	none	PRESERVE_OWNED	HASH_SOURCE	r1-F1	continuity
OWN-0013	spec	hash	dir	edited	yes	copy	maintainer	install_rerun	none	none	PRESERVE_OWNED	HASH_SOURCE	r5-F1	edited fork must NOT be re-baselined as framework-owned
OWN-0014	protocol	hash	regular	edited	yes	copy	maintainer	install_rerun	none	none	PRESERVE_OWNED	HASH_PRIOR_RECORD	r9-F1	FMS_HASH_ROOT does not reach the generated pointer
OWN-0015	marker	hash	regular	edited	yes	copy	maintainer	install_rerun	none	none	PRESERVE_OWNED	HASH_SOURCE	r5-F1	family sibling of OWN-0013
OWN-0016	spec	hash	dir_empty	edited	yes	copy	maintainer	install_rerun	none	none	PRESERVE_OWNED	HASH_PRIOR_RECORD	r11-F2	open=r11-F2; flag-only continuity emits zero file records
OWN-0017	spec	none	dir	pristine	yes	copy	maintainer	upgrade	none	none	REFRESH	HASH_SOURCE	r3-F2	current-source takeover: target HAS a pristine tree, so it is replaced (with backup), not newly delivered
OWN-0018	spec	none	dir	legacy_pristine	yes	copy	maintainer	upgrade	none	none	REFRESH	HASH_SOURCE	adr-155-amend-1	legacy migration by pinned fingerprint
OWN-0019	spec	none	dir	edited	yes	copy	maintainer	upgrade	none	none	PRESERVE_UNOWNED	HASH_NONE	adr-155-amend-1	ADOPTER-FORK: preserve + snapshot + named WARNING
OWN-0020	spec	none	dir	legacy_pristine_partial	yes	copy	maintainer	upgrade	none	none	PRESERVE_UNOWNED	HASH_NONE	r1-F3	a tree carrying an entry the fingerprint cannot inventory — a partial inventory must never certify
OWN-0021	spec	hash	dir	pristine	yes	copy	maintainer	upgrade	none	none	REFRESH	HASH_SOURCE	adr-155-amend-1	record-owned forced refresh with backup
OWN-0022	spec	hash	dir	edited	yes	copy	maintainer	upgrade	none	none	REFRESH	HASH_SOURCE	adr-155-amend-1	contract fork is refreshed, not preserved (OQ-3 of ADR)
OWN-0023	spec	hash	regular	edited	yes	copy	maintainer	upgrade	none	none	REFRESH	HASH_SOURCE	r3-F1	degenerate: delivered tree replaced by a regular file
OWN-0024	spec	hash	regular	edited	yes	copy	maintainer	upgrade	none	backup_unwritable	ABORT_SURFACE	HASH_PRIOR_RECORD	r3-F1	backup-before-replace is the contract
OWN-0025	spec	hash	special	-	yes	copy	maintainer	upgrade	none	none	PRESERVE_UNOWNED	HASH_NONE	r9-F3	FIFO: cp would block and hang the run mid-upgrade
OWN-0026	marker	hash	regular	edited	yes	copy	maintainer	upgrade	none	none	REFRESH	HASH_SOURCE	adr-155-amend-1	forced + read-back-validated write
OWN-0027	marker	hash	regular	edited	yes	copy	maintainer	upgrade	none	backup_unwritable	ABORT_SURFACE	HASH_PRIOR_RECORD	r4-F5	
OWN-0028	marker	hash	dir	-	yes	copy	maintainer	upgrade	none	none	PRESERVE_UNOWNED	HASH_NONE	r2-F3	adopter directory at the marker path: correctly unowned, and a prior record existed => OMIT
OWN-0029	marker	hash	special	-	yes	copy	maintainer	upgrade	none	none	PRESERVE_UNOWNED	HASH_NONE	r2-F3	FIFO destination blocks the upgrade
OWN-0030	spec	hash	ancestor_symlink	*	yes	copy	maintainer	upgrade	none	none	PRESERVE_UNOWNED	HASH_NONE	r2-F1	dead-branch: the continuity line here can never fire — the relpath sanitizer drops any record whose path traverses a symlink BEFORE _baseline_has_*_record is consulted
OWN-0031	marker	hash	ancestor_symlink	*	yes	copy	maintainer	upgrade	none	none	PRESERVE_UNOWNED	HASH_NONE	r4-F2	dead-branch: the continuity line here can never fire — the relpath sanitizer drops any record whose path traverses a symlink BEFORE _baseline_has_*_record is consulted
OWN-0032	protocol	hash	dir	-	yes	copy	maintainer	upgrade	none	none	PRESERVE_UNOWNED	HASH_NONE	derived	GAP: no non-regular guard; cat > fails and set -e ABORTS the run
OWN-0033	protocol	hash	special	-	yes	copy	maintainer	upgrade	none	none	PRESERVE_UNOWNED	HASH_NONE	derived	GAP: FIFO blocks the run; sibling of r9-F3/r2-F3
OWN-0034	protocol	hash	symlink	edited	yes	copy	maintainer	upgrade	none	none	PRESERVE_UNOWNED	HASH_NONE	derived	GAP: cat > follows the leaf symlink OUTSIDE the target
OWN-0040	spec	link_match	symlink	-	yes	link	maintainer	upgrade	none	none	PRESERVE_OWNED	LINK_RECORD	r4-F3	recorded link-mode delivery, target unchanged
OWN-0041	marker	link_match	symlink	-	yes	link	maintainer	upgrade	none	none	PRESERVE_OWNED	LINK_RECORD	r4-F4	family sibling
OWN-0042	spec	link_retargeted	symlink	-	yes	link	maintainer	upgrade	none	none	PRESERVE_UNOWNED	HASH_NONE	r4-F3	redirected link must not inherit ownership; a prior record existed, so the mechanical observation is OMIT (see OQ-9)
OWN-0043	marker	link_retargeted	symlink	-	yes	link	maintainer	upgrade	none	none	PRESERVE_UNOWNED	HASH_NONE	r4-F4	readers fall back to VERSION; a prior record existed, so the mechanical observation is OMIT (see OQ-9)
OWN-0044	spec	none	symlink	-	yes	copy	maintainer	upgrade	none	none	PRESERVE_UNOWNED	HASH_NONE	r8-F2	no LINK row BY DESIGN — must reach preserve, never set -e abort
OWN-0045	marker	none	symlink	-	yes	copy	maintainer	upgrade	none	none	PRESERVE_UNOWNED	HASH_NONE	r8-F2	sibling site of the same set -e abort
OWN-0046	spec	link_match	symlink	-	yes	link	maintainer	upgrade	none	none	PRESERVE_OWNED	LINK_RECORD	r6-F1	LINK record must survive relpath sanitization (leaf IS a symlink)
OWN-0047	marker	link_match	symlink	-	yes	link	maintainer	upgrade	none	none	PRESERVE_OWNED	LINK_RECORD	r6-F1	sibling lookup
OWN-0048	spec	link_match	symlink	-	yes	link	maintainer	upgrade	none	none	PRESERVE_OWNED	LINK_RECORD	r7-F3	note: link target path CONTAINS A SPACE — fixed double-space delimiter
OWN-0049	marker	link_match	symlink	-	yes	link	maintainer	upgrade	none	none	PRESERVE_OWNED	LINK_RECORD	r7-F3	sibling site
OWN-0050	spec	link_retargeted	symlink	-	yes	link	maintainer	install_rerun	none	none	PRESERVE_UNOWNED	HASH_NONE	r10-F1	continuity must compare prior LINK target to live readlink; a prior record existed, so the mechanical observation is OMIT (see OQ-9)
OWN-0051	marker	link_retargeted	symlink	-	yes	link	maintainer	install_rerun	none	none	PRESERVE_UNOWNED	HASH_NONE	r10-F1	sibling site; a prior record existed, so the mechanical observation is OMIT (see OQ-9)
OWN-0052	spec	hash	symlink	-	yes	link	maintainer	install_rerun	none	none	PRESERVE_UNOWNED	HASH_NONE	r11-F1	open=r11-F1; absence of a LINK row is NOT a match
OWN-0053	marker	hash	symlink	-	yes	link	maintainer	install_rerun	none	none	PRESERVE_UNOWNED	HASH_NONE	r11-F1	open=r11-F1; sibling site
OWN-0060	spec	hash	dir	pristine	yes	copy	maintainer	upgrade	self	none	PRESERVE_OWNED	HASH_SOURCE	adr-155-amend-1	--skip SPEC/v1
OWN-0061	spec	hash	dir	pristine	yes	copy	maintainer	upgrade	descendant	none	PRESERVE_OWNED	HASH_SOURCE	r2-F2	--skip SPEC/v1/<file> preserves the WHOLE unit
OWN-0062	spec	hash	dir	edited	yes	copy	maintainer	upgrade	descendant	none	PRESERVE_OWNED	HASH_SOURCE	r5-F3	note: skipped file exists ONLY in the target — union scan required
OWN-0063	spec	hash	dir	edited	yes	copy	maintainer	upgrade	descendant	none	PRESERVE_OWNED	HASH_SOURCE	r10-F3	note: target-only entry is a SYMLINK — scan must not be -type f
OWN-0064	marker	hash	regular	pristine	yes	copy	maintainer	upgrade	self	none	PRESERVE_OWNED	HASH_SOURCE	adr-155-amend-1	--skip .claude/.framework-version
OWN-0070	spec	hash	dir	pristine	yes	copy	user	upgrade	none	none	PRESERVE_OWNED	HASH_SOURCE	r7-F2	maintainer install re-run as user: record must NOT be erased
OWN-0071	protocol	hash	regular	pristine	yes	copy	user	upgrade	none	none	PRESERVE_OWNED	HASH_PRIOR_RECORD	r7-F2	analogous PROTOCOL skip
OWN-0072	protocol	hash	regular	edited	yes	copy	user	upgrade	none	none	PRESERVE_OWNED	HASH_PRIOR_RECORD	r9-F2	flag alone re-baselines the customized pointer
OWN-0073	marker	hash	regular	pristine	yes	copy	user	upgrade	none	none	REFRESH	HASH_SOURCE	adr-155-amend-1	marker is delivered in BOTH ceremonies
OWN-0080	marker	hash	regular	pristine	no	copy	maintainer	upgrade	none	none	PRESERVE_UNOWNED	HASH_NONE	r9-F4	--pin to a pre-v1.3 tag: readers fall back to VERSION
OWN-0081	marker	hash	regular	pristine	no	copy	maintainer	upgrade	none	none	PRESERVE_UNOWNED	HASH_NONE	r11-F3	open=r11-F3; external target: VERSION is adopter-owned and never written
OWN-0082	spec	hash	dir	pristine	no	copy	maintainer	upgrade	none	none	PRESERVE_OWNED	HASH_PRIOR_RECORD	adr-155-amend-1	source lacks SPEC/v1: continuity, but no source bytes to hash
OWN-0090	marker	hash	regular	edited	yes	copy	maintainer	upgrade	none	none	REFRESH	HASH_SOURCE	r7-F1	reader rule: checker must verify live bytes against the record
OWN-0091	marker	hash	regular	edited	yes	copy	maintainer	install_rerun	none	none	PRESERVE_OWNED	HASH_SOURCE	r7-F1	1.3.0->9.9.9 edit must not suppress a real update
OWN-0074	protocol	hash	regular	edited	yes	copy	maintainer	upgrade	none	none	PRESERVE_OWNED	HASH_CANONICAL_POINTER	derived	ADOPTER-CUSTOMIZED pointer on the NORMAL upgrade path — the verified S238 case; the digest stays canonical so the next upgrade does not read H_dst==H_base and clobber it

exec
/bin/zsh -lc "git diff -- scripts/tests/test-ownership-table.sh | cat; printf '\\n--- HARNESS relevant ---\\n'; nl -ba scripts/tests/test-ownership-table.sh | sed -n '1,180p;240,340p;430,620p;620,760p'; printf '\\n--- BASELINE MAP ---\\n'; sed -n '1,130p' scripts/tests/ownership-baseline-map.txt" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-7TTBic5R' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-vyKlS6dG' (errno=Operation not permitted)
diff --git a/scripts/tests/test-ownership-table.sh b/scripts/tests/test-ownership-table.sh
index a510d43..c899879 100755
--- a/scripts/tests/test-ownership-table.sh
+++ b/scripts/tests/test-ownership-table.sh
@@ -179,7 +179,11 @@ _obs_record() {  # $1 = manifest abs path, $2 = relpath
 # defined by the framework having ATTEMPTED and declined, which leaves no
 # filesystem trace at all. If this wording changes, this test fails loudly —
 # which is correct, because the operator-visible contract changed.
-_ABORT_MARKERS='REFUSING to|could not back up|unsupported special file|backup-before-replace'
+# Only GENUINE execution failures. Refusing to act on an unsupported
+# destination is a DECISION (the surface is adopter-owned), not a failed
+# attempt — conflating them made the e2e and the decision function disagree
+# about the same cell (round-1 consensus C2).
+_ABORT_MARKERS='REFUSING to|could not back up|backup-before-replace'
 
 # =============================================================================
 # Fixtures
@@ -413,7 +417,8 @@ _derive_verdict() {  # $1 bd $2 ad $3 br $4 ar $5 out $6 surface $7 rel $8 opera
   if [[ "$op" == "upgrade" && "$_MTIME_BEFORE" != "$_MTIME_AFTER" ]]; then
     printf 'REFRESH'; return 0
   fi
-  if [[ -n "$br" && -z "$ar" ]]; then printf 'OMIT_RECORD'; return 0; fi
+  # OQ-9 colapsada: sem registro ao final é PRESERVE_UNOWNED, tenha ou não
+  # existido um antes. O 'tinha antes?' é prior_record, que já é uma coluna.
   if [[ -n "$ar" ]]; then printf 'PRESERVE_OWNED'; else printf 'PRESERVE_UNOWNED'; fi
 }
 
@@ -447,7 +452,20 @@ _derive_hash_source() {  # $1 surface $2 after_rec $3 prior_rec $4 src_root
     printf 'HASH_UNCLASSIFIED'; return 0
   fi
 
+  # The canonical pointer digest is the hash of what the framework WOULD
+  # generate — it matches no file on disk when the pointer is customised, so it
+  # has to be recognised explicitly or every correct record reads as
+  # unclassified.
+  # Order matters and is NOT arbitrary. For a PRISTINE pointer the canonical
+  # digest and the prior record are the SAME bytes, so whichever is tested
+  # first wins the name. Testing the prior record first keeps continuity rows
+  # reading as HASH_PRIOR_RECORD, and the canonical name is then reached only
+  # when the two genuinely differ — i.e. when the pointer was customised, which
+  # is the one cell where the distinction carries meaning.
   [[ -n "$c_prior"   && "$got" == "$c_prior"   ]] && { printf 'HASH_PRIOR_RECORD'; return 0; }
+  if [[ "$surface" == "protocol" && -n "$c_pointer" && "$got" == "$c_pointer" ]]; then
+    printf 'HASH_CANONICAL_POINTER'; return 0
+  fi
   [[ -n "$c_source"  && "$got" == "$c_source"  ]] && { printf 'HASH_SOURCE'; return 0; }
   [[ -n "$c_pointer" && "$got" == "$c_pointer" ]] && { printf 'HASH_CANONICAL_POINTER'; return 0; }
   [[ -n "$c_target"  && "$got" == "$c_target"  ]] && { printf 'HASH_TARGET'; return 0; }
@@ -530,8 +548,12 @@ _run_row() {
   local bak_guard=""
   case "$fault" in
     backup_unwritable)
-      bak_guard="$T/.claude.bak"
-      rm -rf "$bak_guard"; mkdir -p "$bak_guard"; chmod 500 "$bak_guard" ;;
+      # Make the SURFACE unbackupable, not the upgrade unstartable. upgrade.sh
+      # creates $BAK_DIR at startup, so locking .claude.bak killed the run
+      # before any surface was reached — the branch under test never ran.
+      # An unreadable SOURCE makes the copy fail while everything else proceeds.
+      bak_guard="$T/$rel"
+      chmod 000 "$bak_guard" 2>/dev/null || true ;;
   esac
 
   # --- BEFORE snapshot -----------------------------------------------------
@@ -571,7 +593,7 @@ _run_row() {
     _run_with_timeout "$CELL_TIMEOUT" "$src/scripts/install.sh" "${iargs[@]}" >> "$out" 2>&1
     rc=$?
   fi
-  [[ -n "$bak_guard" ]] && chmod 700 "$bak_guard" 2>/dev/null
+  [[ -n "$bak_guard" ]] && chmod -R u+rwX "$bak_guard" 2>/dev/null
 
   local timed_out=0
   [[ $rc -eq 124 || $rc -eq 137 ]] && timed_out=1

--- HARNESS relevant ---
     1	#!/usr/bin/env bash
     2	# =============================================================================
     3	# PLAN-167 W0.3 — ownership decision table runner.
     4	#
     5	# Executes EVERY legal cell of scripts/tests/ownership_table.tsv against the
     6	# REAL scripts/install.sh and scripts/upgrade.sh. There is no mock of the
     7	# subject under test: the fixture is a real target tree, the run is a real
     8	# invocation, and the verdict is DERIVED from observable state, never parsed
     9	# out of prose.
    10	#
    11	# Reasoning + dimension/enum definitions: docs/ownership-decision-table.md
    12	#
    13	# Usage:
    14	#   test-ownership-table.sh              run every row
    15	#   test-ownership-table.sh --only OWN-0013
    16	#   test-ownership-table.sh --map        emit the map only (no pass/fail exit)
    17	#   test-ownership-table.sh --list       list row ids and exit
    18	#   test-ownership-table.sh --keep       keep the scratch dir (debugging)
    19	#
    20	# Exit: 0 = every row matched its expected pair. 1 = at least one mismatch.
    21	#       2 = harness/usage error (never confused with a row failure).
    22	#
    23	# NOT `set -e`: this harness OBSERVES scripts that are expected to fail on
    24	# some rows. Dying on their exit status would erase the observation.
    25	# =============================================================================
    26	set -uo pipefail
    27	
    28	SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    29	REPO_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
    30	TSV="$SCRIPT_DIR/ownership_table.tsv"
    31	
    32	CELL_TIMEOUT="${CELL_TIMEOUT:-60}"
    33	ONLY=""
    34	MAP_ONLY=0
    35	LIST_ONLY=0
    36	KEEP=0
    37	
    38	while [[ $# -gt 0 ]]; do
    39	  case "$1" in
    40	    --only) ONLY="${2:-}"; shift 2 ;;
    41	    --map)  MAP_ONLY=1; shift ;;
    42	    --list) LIST_ONLY=1; shift ;;
    43	    --keep) KEEP=1; shift ;;
    44	    -h|--help) sed -n '2,30p' "${BASH_SOURCE[0]}"; exit 0 ;;
    45	    *) echo "ERROR: unknown argument: $1" >&2; exit 2 ;;
    46	  esac
    47	done
    48	
    49	[[ -f "$TSV" ]] || { echo "ERROR: table not found: $TSV" >&2; exit 2; }
    50	
    51	# --- framework hash helpers (the same ones the scripts use) ------------------
    52	# shellcheck source=/dev/null
    53	. "$REPO_ROOT/scripts/_hash_lib.sh" 2>/dev/null || {
    54	  echo "ERROR: cannot source scripts/_hash_lib.sh" >&2; exit 2; }
    55	command -v _hash_file  >/dev/null 2>&1 || { echo "ERROR: _hash_file missing"  >&2; exit 2; }
    56	command -v _hash_stdin >/dev/null 2>&1 || { echo "ERROR: _hash_stdin missing" >&2; exit 2; }
    57	
    58	# --- scratch ----------------------------------------------------------------
    59	# NEVER $HOME, NEVER inside the repo (PLAN-167 W0.3 hard requirement).
    60	WORK="$( mktemp -d "${TMPDIR:-/tmp}/plan167-own.XXXXXX" )" || exit 2
    61	T="$WORK/t"                 # the ONE target path every row uses (see §fixtures)
    62	cleanup() {
    63	  [[ "$KEEP" -eq 1 ]] && { echo "scratch kept: $WORK" >&2; return; }
    64	  chmod -R u+w "$WORK" 2>/dev/null || true
    65	  rm -rf "$WORK" 2>/dev/null || true
    66	}
    67	trap cleanup EXIT
    68	
    69	# --- portable timeout -------------------------------------------------------
    70	# macOS ships no timeout(1). A cell that hangs (the FIFO class) must be killed,
    71	# not waited on — two separate defects in this space were a blocking cp.
    72	_TIMEOUT_BIN=""
    73	if command -v timeout  >/dev/null 2>&1; then _TIMEOUT_BIN="timeout"
    74	elif command -v gtimeout >/dev/null 2>&1; then _TIMEOUT_BIN="gtimeout"; fi
    75	
    76	_run_with_timeout() {  # $1 = seconds; rest = command
    77	  local secs="$1"; shift
    78	  if [[ -n "$_TIMEOUT_BIN" ]]; then
    79	    "$_TIMEOUT_BIN" "$secs" "$@"
    80	    return $?
    81	  fi
    82	  # Fallback: background + watchdog. Kills the process group so a blocked cp
    83	  # inside the script dies with it.
    84	  "$@" &
    85	  local pid=$!
    86	  ( sleep "$secs"; kill -9 "$pid" 2>/dev/null ) &
    87	  local watch=$!
    88	  wait "$pid" 2>/dev/null
    89	  local rc=$?
    90	  kill "$watch" 2>/dev/null
    91	  wait "$watch" 2>/dev/null
    92	  return $rc
    93	}
    94	
    95	# --- surface geometry -------------------------------------------------------
    96	_relpath_for() {
    97	  case "$1" in
    98	    spec)     printf 'SPEC/v1' ;;
    99	    protocol) printf 'PROTOCOL.md' ;;
   100	    marker)   printf '.claude/.framework-version' ;;
   101	    *) return 1 ;;
   102	  esac
   103	}
   104	MANIFEST_REL=".claude/.install-manifest.sha256"
   105	
   106	# --- observation primitives -------------------------------------------------
   107	_obs_type() {  # $1 = abs path -> the live_type vocabulary
   108	  local p="$1"
   109	  if   [[ -L "$p" ]]; then printf 'symlink'
   110	  elif [[ ! -e "$p" ]]; then printf 'absent'
   111	  elif [[ -d "$p" ]]; then
   112	    if [[ -z "$( ls -A "$p" 2>/dev/null )" ]]; then printf 'dir_empty'; else printf 'dir'; fi
   113	  elif [[ -p "$p" || -S "$p" || -b "$p" || -c "$p" ]]; then printf 'special'
   114	  elif [[ -f "$p" ]]; then printf 'regular'
   115	  else printf 'special'; fi
   116	}
   117	
   118	# Content digest of a surface, whatever its shape. Directory digest reproduces
   119	# upgrade.sh's _spec_tree_fingerprint semantics (sorted "<sha>  <rel>" lines).
   120	_obs_digest() {  # $1 = abs path
   121	  local p="$1" lines
   122	  if [[ -L "$p" ]]; then printf 'link:%s' "$( readlink "$p" 2>/dev/null || true )"; return 0; fi
   123	  if [[ ! -e "$p" ]]; then printf 'absent'; return 0; fi
   124	  if [[ -d "$p" ]]; then
   125	    lines="$( ( cd "$p" && find . -type f -print 2>/dev/null ) | LC_ALL=C sort \
   126	      | while IFS= read -r r; do
   127	          [[ -n "$r" ]] || continue
   128	          printf '%s  %s\n' "$( _hash_file "$p/$r" 2>/dev/null || echo FAIL )" "$r"
   129	        done )"
   130	    [[ -z "$lines" ]] && { printf 'emptydir'; return 0; }
   131	    printf '%s' "$( printf '%s\n' "$lines" | _hash_stdin )"
   132	    return 0
   133	  fi
   134	  if [[ -f "$p" ]]; then printf '%s' "$( _hash_file "$p" 2>/dev/null || echo UNREADABLE )"; return 0; fi
   135	  printf 'special'
   136	}
   137	
   138	# Modification-time signature of a surface. BSD stat takes -f, GNU takes -c;
   139	# both are tried so the harness behaves the same on macOS and CI.
   140	_stat_mtime() {  # $1 = abs path
   141	  stat -f '%m' "$1" 2>/dev/null || stat -c '%Y' "$1" 2>/dev/null || printf '0'
   142	}
   143	_obs_mtime() {  # $1 = abs path -> newest mtime under it (or its own)
   144	  local p="$1" newest=0 m r
   145	  if [[ -L "$p" || ! -e "$p" ]]; then printf '%s' "$( _stat_mtime "$p" )"; return 0; fi
   146	  if [[ -d "$p" ]]; then
   147	    while IFS= read -r r; do
   148	      [[ -n "$r" ]] || continue
   149	      m="$( _stat_mtime "$p/$r" )"
   150	      [[ "$m" =~ ^[0-9]+$ ]] || continue
   151	      (( m > newest )) && newest="$m"
   152	    done < <( cd "$p" && find . -type f -print 2>/dev/null )
   153	    printf '%s' "$newest"; return 0
   154	  fi
   155	  printf '%s' "$( _stat_mtime "$p" )"
   156	}
   157	
   158	# The manifest's record for a relpath: "" | "hash:<64hex>" | "link:<target>"
   159	# For SPEC/v1 the record may be per-file rows; presence of ANY row counts, and
   160	# the digest reported is the tree-shaped roll-up of those rows.
   161	_obs_record() {  # $1 = manifest abs path, $2 = relpath
   162	  local m="$1" rel="$2" line rows
   163	  [[ -f "$m" ]] || { printf ''; return 0; }
   164	  line="$( grep -E "^LINK  ${rel//./\\.}  " "$m" 2>/dev/null | head -1 || true )"
   165	  if [[ -n "$line" ]]; then printf 'link:%s' "${line#LINK  $rel  }"; return 0; fi
   166	  line="$( grep -E "^[0-9a-f]{64}  ${rel//./\\.}$" "$m" 2>/dev/null | head -1 || true )"
   167	  if [[ -n "$line" ]]; then printf 'hash:%s' "${line%% *}"; return 0; fi
   168	  # tree surface: any per-file row under the relpath
   169	  rows="$( grep -E "^[0-9a-f]{64}  ${rel//./\\.}/" "$m" 2>/dev/null || true )"
   170	  if [[ -n "$rows" ]]; then
   171	    printf 'hash:%s' "$( printf '%s\n' "$rows" | LC_ALL=C sort | _hash_stdin )"
   172	    return 0
   173	  fi
   174	  printf ''
   175	}
   176	
   177	# Refusal markers — the operator-visible contract of ABORT_SURFACE. Matching
   178	# output is a deliberate choice, recorded in docs §6 (OQ-1/OQ-2): a refusal is
   179	# defined by the framework having ATTEMPTED and declined, which leaves no
   180	# filesystem trace at all. If this wording changes, this test fails loudly —
   240	# The NEXT version of the framework — a source whose surfaces differ from the
   241	# one that produced the baseline.
   242	#
   243	# This is not decoration. A real upgrade runs against a source NEWER than the
   244	# install that wrote the manifest. Reusing one source makes `HASH_SOURCE` and
   245	# `HASH_PRIOR_RECORD` byte-equal, and a classifier can then only tell them
   246	# apart by preferring one — which is resolving an ambiguity by preference, the
   247	# exact thing docs §5.6 forbids. Perturbing the source is how the fixture is
   248	# DIFFERENTIATED until the two candidates separate.
   249	_next_source() {
   250	  local nxt="$WORK/src-next"
   251	  [[ -d "$nxt" ]] && { printf '%s' "$nxt"; return 0; }
   252	  _clone_source "$nxt" || return 1
   253	  local first
   254	  first="$( ( cd "$nxt/SPEC/v1" && find . -type f -print 2>/dev/null ) | LC_ALL=C sort | head -1 )"
   255	  first="${first#./}"
   256	  [[ -n "$first" ]] && printf '\n<!-- next-version marker (PLAN-167 fixture) -->\n' >> "$nxt/SPEC/v1/$first"
   257	  printf '1.3.1\n' > "$nxt/.claude/.framework-version"
   258	  printf '%s' "$nxt"
   259	}
   260	
   261	_strip_record() {  # $1 = manifest, $2 = relpath — make prior_record=none
   262	  local m="$1" rel="$2" tmp
   263	  [[ -f "$m" ]] || return 0
   264	  tmp="$( mktemp "$m.XXXXXX" )" || return 1
   265	  grep -vE "^([0-9a-f]{64}|LINK)  ${rel//./\\.}(/|  |$)" "$m" > "$tmp" 2>/dev/null
   266	  mv "$tmp" "$m"
   267	}
   268	
   269	_mutate_surface() {  # $1 surface, $2 live_type, $3 live_content, $4 src root, $5 prior_record
   270	  local surface="$1" ltype="$2" lcontent="$3" src_root="$4" prior="${5:-none}"
   271	  local rel; rel="$( _relpath_for "$surface" )"
   272	  local p="$T/$rel"
   273	
   274	  # A `link_match` row means the live symlink IS the recorded delivery. The
   275	  # base --link install already created exactly that, so pointing it somewhere
   276	  # else here would silently convert every link_match row into a
   277	  # link_retargeted one — the fixture would then agree with the expectation for
   278	  # the wrong reason, which is how a row goes green while testing nothing.
   279	  if [[ "$ltype" == "symlink" && "$prior" == "link_match" ]]; then
   280	    [[ -L "$p" ]] || { echo "FIXTURE-ERR: $rel is not a symlink after a --link base install" >&2; return 1; }
   281	    ltype="__keep__"
   282	  fi
   283	
   284	  case "$ltype" in
   285	    absent)   rm -rf "$p" ;;
   286	    dir_empty)
   287	      rm -rf "$p"; mkdir -p "$p" ;;
   288	    regular)
   289	      if [[ -d "$p" ]]; then rm -rf "$p"; fi
   290	      [[ -e "$p" ]] || { mkdir -p "$( dirname "$p" )"; printf 'adopter regular file\n' > "$p"; }
   291	      ;;
   292	    symlink)
   293	      # The foreign leaf is a TRIPWIRE, not scenery. A surface written with
   294	      # `cat >` follows a leaf symlink and mutates whatever it points at —
   295	      # OUTSIDE the target tree, which is adopter or system data. Comparing
   296	      # only the target would let that row report GREEN while the run
   297	      # destroyed a file the test never looked at.
   298	      rm -rf "$p"
   299	      mkdir -p "$( dirname "$p" )" "$WORK/foreign"
   300	      printf 'foreign content — MUST NOT be modified by any run\n' > "$WORK/foreign/leaf"
   301	      ln -s "$WORK/foreign/leaf" "$p"
   302	      ;;
   303	    special)
   304	      rm -rf "$p"; mkdir -p "$( dirname "$p" )"; mkfifo "$p" 2>/dev/null || return 1 ;;
   305	    ancestor_symlink)
   306	      # Move the parent aside and symlink it back — the leaf is then reachable
   307	      # only by writing THROUGH a symlink out of the target tree.
   308	      local parent; parent="$( dirname "$p" )"
   309	      local real="$WORK/ancestor-real-$surface"
   310	      rm -rf "$real"; mkdir -p "$( dirname "$real" )"
   311	      mv "$parent" "$real" 2>/dev/null || return 1
   312	      ln -s "$real" "$parent"
   313	      ;;
   314	    dir)
   315	      # On a rerun the base install already left the tree; on a structurally
   316	      # fresh target there is nothing yet, so the adopter's own directory has
   317	      # to be built here.
   318	      if [[ ! -d "$p" || -L "$p" ]]; then
   319	        rm -rf "$p"; mkdir -p "$p"; printf 'adopter content\n' > "$p/adopter.md"
   320	      fi
   321	      ;;
   322	  esac
   323	
   324	  case "$lcontent" in
   325	    edited)
   326	      if [[ -d "$p" && ! -L "$p" ]]; then
   327	        local victim
   328	        victim="$( ( cd "$p" && find . -type f -print 2>/dev/null ) | LC_ALL=C sort | head -1 )"
   329	        victim="${victim#./}"
   330	        # Guard the empty-tree case: without it the redirect target collapses to
   331	        # "$p/" and the shell reports "Is a directory" instead of mutating.
   332	        # if/fi, NOT `[[ ]] && cmd`: as the last statement of the branch, a
   333	        # false test would make the whole function return 1 and the row would
   334	        # be recorded as a harness error rather than run.
   335	        if [[ -n "$victim" ]]; then
   336	          printf '\nADOPTER EDIT\n' >> "$p/$victim"
   337	        fi
   338	      elif [[ -f "$p" && ! -L "$p" ]]; then
   339	        printf 'ADOPTER EDIT\n' >> "$p"
   340	      fi
   430	  local got="${ar#hash:}"
   431	  local rel; rel="$( _relpath_for "$surface" )"
   432	
   433	  # Candidate 1: the bytes now at the target.
   434	  local c_target; c_target="$( _obs_digest "$T/$rel" )"
   435	  # Candidate 2: the framework's copy in the source checkout.
   436	  local c_source; c_source="$( _obs_digest "$src/$rel" )"
   437	  # Candidate 3: the digest the PRE-run manifest recorded.
   438	  local c_prior="${pr#hash:}"
   439	  # Candidate 4: the canonical pointer digest (protocol only).
   440	  local c_pointer="$CANON_POINTER_HASH"
   441	
   442	  # For tree surfaces the recorded value is the roll-up of per-file rows, which
   443	  # is not comparable to a content fingerprint — compare tree membership by
   444	  # re-deriving both roll-ups instead.
   445	  if [[ "$surface" == "spec" ]]; then
   446	    local roll_t roll_s
   447	    roll_t="$( _rollup_from_tree "$T/$rel" "$rel" )"
   448	    roll_s="$( _rollup_from_tree "$src/$rel" "$rel" )"
   449	    [[ -n "$c_prior" && "$got" == "$c_prior" ]] && { printf 'HASH_PRIOR_RECORD'; return 0; }
   450	    [[ -n "$roll_s" && "$got" == "$roll_s" ]] && { printf 'HASH_SOURCE'; return 0; }
   451	    [[ -n "$roll_t" && "$got" == "$roll_t" ]] && { printf 'HASH_TARGET'; return 0; }
   452	    printf 'HASH_UNCLASSIFIED'; return 0
   453	  fi
   454	
   455	  # The canonical pointer digest is the hash of what the framework WOULD
   456	  # generate — it matches no file on disk when the pointer is customised, so it
   457	  # has to be recognised explicitly or every correct record reads as
   458	  # unclassified.
   459	  # Order matters and is NOT arbitrary. For a PRISTINE pointer the canonical
   460	  # digest and the prior record are the SAME bytes, so whichever is tested
   461	  # first wins the name. Testing the prior record first keeps continuity rows
   462	  # reading as HASH_PRIOR_RECORD, and the canonical name is then reached only
   463	  # when the two genuinely differ — i.e. when the pointer was customised, which
   464	  # is the one cell where the distinction carries meaning.
   465	  [[ -n "$c_prior"   && "$got" == "$c_prior"   ]] && { printf 'HASH_PRIOR_RECORD'; return 0; }
   466	  if [[ "$surface" == "protocol" && -n "$c_pointer" && "$got" == "$c_pointer" ]]; then
   467	    printf 'HASH_CANONICAL_POINTER'; return 0
   468	  fi
   469	  [[ -n "$c_source"  && "$got" == "$c_source"  ]] && { printf 'HASH_SOURCE'; return 0; }
   470	  [[ -n "$c_pointer" && "$got" == "$c_pointer" ]] && { printf 'HASH_CANONICAL_POINTER'; return 0; }
   471	  [[ -n "$c_target"  && "$got" == "$c_target"  ]] && { printf 'HASH_TARGET'; return 0; }
   472	  printf 'HASH_UNCLASSIFIED'
   473	}
   474	
   475	_rollup_from_tree() {  # $1 = tree abs path, $2 = relpath prefix
   476	  local root="$1" pfx="$2"
   477	  [[ -d "$root" ]] || { printf ''; return 0; }
   478	  ( cd "$root" && find . -type f -print 2>/dev/null ) | LC_ALL=C sort \
   479	    | while IFS= read -r r; do
   480	        [[ -n "$r" ]] || continue
   481	        printf '%s  %s/%s\n' "$( _hash_file "$root/$r" 2>/dev/null || echo FAIL )" "$pfx" "${r#./}"
   482	      done | LC_ALL=C sort | _hash_stdin
   483	}
   484	
   485	# =============================================================================
   486	# Row execution
   487	# =============================================================================
   488	PASS=0; FAIL=0; AMBIG=0; ERR=0
   489	MAP_LINES=""
   490	
   491	_run_row() {
   492	  local id="$1" surface="$2" prior_record="$3" live_type="$4" live_content="$5"
   493	  local source_has="$6" mode="$7" ceremony="$8" operation="$9" skip_requested="${10}"
   494	  local fault="${11}"
   495	  local exp_verdict="${12}" exp_hash="${13}" origin="${14}" note="${15}"
   496	
   497	  local rel; rel="$( _relpath_for "$surface" )" || { ERR=$((ERR+1)); return; }
   498	
   499	  # --- base selection ------------------------------------------------------
   500	  # base_mode follows PRIOR_RECORD (the previous run), never `mode` (this run).
   501	  # Conflating them would erase the r11-F1 cell — see docs §4.1.
   502	  local base_mode="copy"
   503	  case "$prior_record" in link_match|link_retargeted) base_mode="link" ;; esac
   504	  local base_ceremony="$ceremony"
   505	  # A user-ceremony row asserting residue of a MAINTAINER install must be built
   506	  # from a maintainer base, then transitioned — that transition is the r7-F2 cell.
   507	  local transition_to_user=0
   508	  if [[ "$ceremony" == "user" && "$prior_record" != "none" && "$surface" != "marker" ]]; then
   509	    base_ceremony="maintainer"; transition_to_user=1
   510	  fi
   511	
   512	  # --- source selection (BEFORE the fixture — `pristine` syncs from it) ----
   513	  local src
   514	  if [[ "$source_has" == "no" ]]; then
   515	    src="$( _alt_source "$surface" )" || { ERR=$((ERR+1)); return; }
   516	  elif [[ "$operation" == "install_fresh" ]]; then
   517	    src="$REPO_ROOT"
   518	  else
   519	    # An upgrade/rerun runs against a source NEWER than the one that wrote the
   520	    # baseline. Without that, HASH_SOURCE and HASH_PRIOR_RECORD are byte-equal.
   521	    src="$( _next_source )" || { ERR=$((ERR+1)); return; }
   522	  fi
   523	
   524	  # --- base tree -----------------------------------------------------------
   525	  if [[ "$operation" == "install_fresh" ]]; then
   526	    # Structurally fresh means NO pre-existing manifest (docs R-01). Extracting
   527	    # a base and stripping one record would leave a manifest behind and make the
   528	    # row an install_rerun wearing a fresh label.
   529	    rm -rf "$T"; mkdir -p "$T"
   530	  else
   531	    local tarball; tarball="$( _base_tar "$base_ceremony" "$base_mode" )" || { ERR=$((ERR+1)); return; }
   532	    rm -rf "$T"; mkdir -p "$T"
   533	    tar -xf "$tarball" -C "$T" || { ERR=$((ERR+1)); return; }
   534	  fi
   535	
   536	  # --- fixture mutation ----------------------------------------------------
   537	  [[ "$prior_record" == "none" ]] && _strip_record "$T/$MANIFEST_REL" "$rel"
   538	  if [[ "$prior_record" == "link_retargeted" && -L "$T/$rel" ]]; then
   539	    mkdir -p "$WORK/retarget"; printf 'retargeted\n' > "$WORK/retarget/leaf"
   540	    rm -f "$T/$rel"; ln -s "$WORK/retarget/leaf" "$T/$rel"
   541	  fi
   542	  _mutate_surface "$surface" "$live_type" "$live_content" "$src" "$prior_record" \
   543	    || { ERR=$((ERR+1)); return; }
   544	
   545	  # Fault injection from the `fault` COLUMN. It rode in `note` until round-1
   546	  # consensus C1 ruled that a dimension the harness parses out of prose is a
   547	  # dimension nothing validates.
   548	  local bak_guard=""
   549	  case "$fault" in
   550	    backup_unwritable)
   551	      # Make the SURFACE unbackupable, not the upgrade unstartable. upgrade.sh
   552	      # creates $BAK_DIR at startup, so locking .claude.bak killed the run
   553	      # before any surface was reached — the branch under test never ran.
   554	      # An unreadable SOURCE makes the copy fail while everything else proceeds.
   555	      bak_guard="$T/$rel"
   556	      chmod 000 "$bak_guard" 2>/dev/null || true ;;
   557	  esac
   558	
   559	  # --- BEFORE snapshot -----------------------------------------------------
   560	  local b_digest b_rec
   561	  b_digest="$( _obs_digest "$T/$rel" )"
   562	  b_rec="$( _obs_record "$T/$MANIFEST_REL" "$rel" )"
   563	  _MTIME_BEFORE="$( _obs_mtime "$T/$rel" )"
   564	  # Everything outside $T that a run could reach. Any change here is an escape.
   565	  _ESCAPE_BEFORE="$( _obs_digest "$WORK/foreign/leaf" 2>/dev/null || printf 'absent' )"
   566	
   567	  # --- run the REAL script -------------------------------------------------
   568	  local out="$WORK/run-$id.log"; : > "$out"
   569	  local rc=0
   570	  # A `ceremony=user` UPGRADE row asserts residue of a maintainer install that
   571	  # was later re-run as `--ceremony user`. The ceremony is read from
   572	  # .claude/.install-state.json, so labelling the row is not enough: the
   573	  # transition has to actually happen, or upgrade.sh still sees `maintainer`
   574	  # and the row silently tests the wrong branch.
   575	  if [[ "$transition_to_user" -eq 1 && "$operation" == "upgrade" ]]; then
   576	    _run_with_timeout "$CELL_TIMEOUT" "$src/scripts/install.sh" "$T" --ceremony user \
   577	      >> "$out" 2>&1 || true
   578	  fi
   579	  if [[ "$operation" == "upgrade" ]]; then
   580	    local uargs=( "$T" )
   581	    [[ "$skip_requested" == "self" ]] && uargs+=( --skip "$rel" )
   582	    if [[ "$skip_requested" == "descendant" ]]; then
   583	      local victim; victim="$( ( cd "$T/$rel" 2>/dev/null && find . ! -type d -print 2>/dev/null | LC_ALL=C sort | head -1 ) )"
   584	      victim="${victim#./}"
   585	      [[ -n "$victim" ]] && uargs+=( --skip "$rel/$victim" )
   586	    fi
   587	    _run_with_timeout "$CELL_TIMEOUT" "$src/scripts/upgrade.sh" "${uargs[@]}" >> "$out" 2>&1
   588	    rc=$?
   589	  else
   590	    local iargs=( "$T" --ceremony "$ceremony" )
   591	    [[ "$mode" == "link" ]] && iargs+=( --link )
   592	    [[ "$transition_to_user" -eq 1 ]] && iargs=( "$T" --ceremony user )
   593	    _run_with_timeout "$CELL_TIMEOUT" "$src/scripts/install.sh" "${iargs[@]}" >> "$out" 2>&1
   594	    rc=$?
   595	  fi
   596	  [[ -n "$bak_guard" ]] && chmod -R u+rwX "$bak_guard" 2>/dev/null
   597	
   598	  local timed_out=0
   599	  [[ $rc -eq 124 || $rc -eq 137 ]] && timed_out=1
   600	
   601	  # --- AFTER snapshot + derivation ----------------------------------------
   602	  local a_digest a_rec got_verdict got_hash
   603	  a_digest="$( _obs_digest "$T/$rel" )"
   604	  a_rec="$( _obs_record "$T/$MANIFEST_REL" "$rel" )"
   605	  _MTIME_AFTER="$( _obs_mtime "$T/$rel" )"
   606	  _ESCAPE_AFTER="$( _obs_digest "$WORK/foreign/leaf" 2>/dev/null || printf 'absent' )"
   607	
   608	  if [[ "$timed_out" -eq 1 ]]; then
   609	    got_verdict="TIMEOUT"; got_hash="TIMEOUT"
   610	  else
   611	    got_verdict="$( _derive_verdict "$b_digest" "$a_digest" "$b_rec" "$a_rec" "$out" "$surface" "$rel" "$operation" )"
   612	    got_hash="$( _derive_hash_source "$surface" "$a_rec" "$b_rec" "$src" )"
   613	  fi
   614	
   615	  # --- compare -------------------------------------------------------------
   616	  local status="RED"
   617	  local alt=""
   618	  case "$note" in *indistinguishable=*) alt="${note##*indistinguishable=}"; alt="${alt%% *}" ;; esac
   619	
   620	  # An escape outranks the verdict comparison. A row whose pair matches while
   620	  # An escape outranks the verdict comparison. A row whose pair matches while
   621	  # the run wrote OUTSIDE the target has not passed: it has demonstrated the
   622	  # exact damage class this table exists to prevent, and calling that GREEN
   623	  # would be the instrument concealing a data loss.
   624	  if [[ "$_ESCAPE_BEFORE" != "$_ESCAPE_AFTER" ]]; then
   625	    status="ESCAPE"; FAIL=$((FAIL+1))
   626	  elif [[ "$got_verdict" == "$exp_verdict" && "$got_hash" == "$exp_hash" ]]; then
   627	    status="GREEN"; PASS=$((PASS+1))
   628	  elif [[ "$got_verdict" == "$exp_verdict" && -n "$alt" && "$got_hash" == "$alt" ]]; then
   629	    status="AMBIG"; AMBIG=$((AMBIG+1))
   630	  elif [[ "$got_verdict" == "TIMEOUT" ]]; then
   631	    status="TIMEOUT"; FAIL=$((FAIL+1))
   632	  else
   633	    FAIL=$((FAIL+1))
   634	  fi
   635	
   636	  MAP_LINES+="$( printf '%-10s %-7s exp=%-16s/%-22s got=%-16s/%-22s rc=%-3s %s\n' \
   637	      "$id" "$status" "$exp_verdict" "$exp_hash" "$got_verdict" "$got_hash" "$rc" "$origin" )"$'\n'
   638	}
   639	
   640	# =============================================================================
   641	# Main
   642	# =============================================================================
   643	if [[ "$LIST_ONLY" -eq 1 ]]; then
   644	  awk -F'\t' '!/^#/ && $1!="id" && NF>1 {print $1"\t"$13}' "$TSV"
   645	  exit 0
   646	fi
   647	
   648	echo "== PLAN-167 ownership decision table =="
   649	echo "   table:  $TSV"
   650	echo "   source: $REPO_ROOT"
   651	echo "   scratch:$WORK"
   652	echo "   timeout:${CELL_TIMEOUT}s/cell   timeout-bin:${_TIMEOUT_BIN:-<fallback>}"
   653	echo ""
   654	
   655	# Prime the canonical pointer digest for $T from a real install. Structurally
   656	# fresh rows build no base, so without this the protocol candidate would be
   657	# unavailable exactly where it is needed.
   658	_base_tar maintainer copy >/dev/null || { echo "ERROR: could not prime base" >&2; exit 2; }
   659	
   660	
   661	# Rows are consumed in file order; the map is sorted by id at emit time so the
   662	# output is deterministic regardless of table order.
   663	while IFS=$'\t' read -r id surface prior_record live_type live_content \
   664	      source_has mode ceremony operation skip_requested fault \
   665	      exp_verdict exp_hash origin note; do
   666	  [[ -z "${id:-}" ]] && continue
   667	  case "$id" in \#*|id) continue ;; esac
   668	  # --only takes a comma-separated list: iterating on a cluster of related rows
   669	  # should cost ONE base install, not one per row.
   670	  if [[ -n "$ONLY" && ",$ONLY," != *",$id,"* ]]; then continue; fi
   671	  _run_row "$id" "$surface" "$prior_record" "$live_type" "$live_content" \
   672	           "$source_has" "$mode" "$ceremony" "$operation" "$skip_requested" \
   673	           "${fault:-none}" "$exp_verdict" "$exp_hash" "$origin" "${note:-}"
   674	done < "$TSV"
   675	
   676	printf '%s' "$MAP_LINES" | LC_ALL=C sort
   677	
   678	echo ""
   679	echo "GREEN=$PASS  RED=$FAIL  AMBIG=$AMBIG  HARNESS-ERR=$ERR"
   680	
   681	[[ "$MAP_ONLY" -eq 1 ]] && exit 0
   682	[[ "$ERR" -gt 0 ]] && exit 2
   683	[[ "$FAIL" -gt 0 ]] && exit 1
   684	exit 0

--- BASELINE MAP ---
== PLAN-167 ownership decision table ==
   table:  /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/tests/ownership_table.tsv
   source: /Users/joaocanhada/canhada-labs/ceo-orchestration
   scratch:/var/folders/9n/hm9srl0s1nz45_p12tj61pd80000gn/T//plan167-own.tJVxLC
   timeout:60s/cell   timeout-bin:<fallback>

OWN-0001   GREEN   exp=DELIVER         /HASH_SOURCE            got=DELIVER         /HASH_SOURCE            rc=0   adr-155
OWN-0002   GREEN   exp=DELIVER         /HASH_CANONICAL_POINTER got=DELIVER         /HASH_CANONICAL_POINTER rc=0   adr-155
OWN-0003   GREEN   exp=DELIVER         /HASH_SOURCE            got=DELIVER         /HASH_SOURCE            rc=0   adr-155-amend-1
OWN-0004   GREEN   exp=PRESERVE_UNOWNED/HASH_NONE              got=PRESERVE_UNOWNED/HASH_NONE              rc=0   adr-155-amend-1
OWN-0005   GREEN   exp=PRESERVE_UNOWNED/HASH_NONE              got=PRESERVE_UNOWNED/HASH_NONE              rc=0   adr-155-amend-1
OWN-0006   GREEN   exp=PRESERVE_UNOWNED/HASH_NONE              got=PRESERVE_UNOWNED/HASH_NONE              rc=0   adr-155-amend-1
OWN-0007   GREEN   exp=PRESERVE_UNOWNED/HASH_NONE              got=PRESERVE_UNOWNED/HASH_NONE              rc=0   adr-155-amend-1
OWN-0008   GREEN   exp=DELIVER         /HASH_SOURCE            got=DELIVER         /HASH_SOURCE            rc=0   adr-155-amend-1
OWN-0010   GREEN   exp=PRESERVE_OWNED  /HASH_SOURCE            got=PRESERVE_OWNED  /HASH_SOURCE            rc=0   r1-F1
OWN-0011   GREEN   exp=PRESERVE_OWNED  /HASH_PRIOR_RECORD      got=PRESERVE_OWNED  /HASH_PRIOR_RECORD      rc=0   r1-F1
OWN-0012   GREEN   exp=PRESERVE_OWNED  /HASH_SOURCE            got=PRESERVE_OWNED  /HASH_SOURCE            rc=0   r1-F1
OWN-0013   GREEN   exp=PRESERVE_OWNED  /HASH_SOURCE            got=PRESERVE_OWNED  /HASH_SOURCE            rc=0   r5-F1
OWN-0014   GREEN   exp=PRESERVE_OWNED  /HASH_PRIOR_RECORD      got=PRESERVE_OWNED  /HASH_PRIOR_RECORD      rc=0   r9-F1
OWN-0015   GREEN   exp=PRESERVE_OWNED  /HASH_SOURCE            got=PRESERVE_OWNED  /HASH_SOURCE            rc=0   r5-F1
OWN-0016   RED     exp=PRESERVE_OWNED  /HASH_PRIOR_RECORD      got=OMIT_RECORD     /HASH_NONE              rc=0   r11-F2
OWN-0017   GREEN   exp=REFRESH         /HASH_SOURCE            got=REFRESH         /HASH_SOURCE            rc=0   r3-F2
OWN-0018   GREEN   exp=REFRESH         /HASH_SOURCE            got=REFRESH         /HASH_SOURCE            rc=0   adr-155-amend-1
OWN-0019   GREEN   exp=PRESERVE_UNOWNED/HASH_NONE              got=PRESERVE_UNOWNED/HASH_NONE              rc=0   adr-155-amend-1
OWN-0020   GREEN   exp=PRESERVE_UNOWNED/HASH_NONE              got=PRESERVE_UNOWNED/HASH_NONE              rc=0   r1-F3
OWN-0021   GREEN   exp=REFRESH         /HASH_SOURCE            got=REFRESH         /HASH_SOURCE            rc=0   adr-155-amend-1
OWN-0022   GREEN   exp=REFRESH         /HASH_SOURCE            got=REFRESH         /HASH_SOURCE            rc=0   adr-155-amend-1
OWN-0023   GREEN   exp=REFRESH         /HASH_SOURCE            got=REFRESH         /HASH_SOURCE            rc=0   r3-F1
OWN-0024   RED     exp=ABORT_SURFACE   /HASH_PRIOR_RECORD      got=PRESERVE_OWNED  /HASH_PRIOR_RECORD      rc=1   r3-F1
OWN-0025   TIMEOUT exp=ABORT_SURFACE   /HASH_PRIOR_RECORD      got=TIMEOUT         /TIMEOUT                rc=137 r9-F3
OWN-0026   GREEN   exp=REFRESH         /HASH_SOURCE            got=REFRESH         /HASH_SOURCE            rc=0   adr-155-amend-1
OWN-0027   RED     exp=ABORT_SURFACE   /HASH_PRIOR_RECORD      got=PRESERVE_OWNED  /HASH_PRIOR_RECORD      rc=1   r4-F5
OWN-0028   GREEN   exp=OMIT_RECORD     /HASH_NONE              got=OMIT_RECORD     /HASH_NONE              rc=0   r2-F3
OWN-0029   TIMEOUT exp=PRESERVE_UNOWNED/HASH_NONE              got=TIMEOUT         /TIMEOUT                rc=137 r2-F3
OWN-0030   GREEN   exp=OMIT_RECORD     /HASH_NONE              got=OMIT_RECORD     /HASH_NONE              rc=0   r2-F1
OWN-0031   GREEN   exp=OMIT_RECORD     /HASH_NONE              got=OMIT_RECORD     /HASH_NONE              rc=0   r4-F2
OWN-0032   RED     exp=PRESERVE_UNOWNED/HASH_NONE              got=PRESERVE_OWNED  /HASH_PRIOR_RECORD      rc=1   derived
OWN-0033   TIMEOUT exp=PRESERVE_UNOWNED/HASH_NONE              got=TIMEOUT         /TIMEOUT                rc=137 derived
OWN-0034   RED     exp=PRESERVE_UNOWNED/HASH_NONE              got=PRESERVE_OWNED  /HASH_UNCLASSIFIED      rc=0   derived
OWN-0040   GREEN   exp=PRESERVE_OWNED  /LINK_RECORD            got=PRESERVE_OWNED  /LINK_RECORD            rc=0   r4-F3
OWN-0041   GREEN   exp=PRESERVE_OWNED  /LINK_RECORD            got=PRESERVE_OWNED  /LINK_RECORD            rc=0   r4-F4
OWN-0042   GREEN   exp=OMIT_RECORD     /HASH_NONE              got=OMIT_RECORD     /HASH_NONE              rc=0   r4-F3
OWN-0043   GREEN   exp=OMIT_RECORD     /HASH_NONE              got=OMIT_RECORD     /HASH_NONE              rc=0   r4-F4
OWN-0044   GREEN   exp=PRESERVE_UNOWNED/HASH_NONE              got=PRESERVE_UNOWNED/HASH_NONE              rc=0   r8-F2
OWN-0045   GREEN   exp=PRESERVE_UNOWNED/HASH_NONE              got=PRESERVE_UNOWNED/HASH_NONE              rc=0   r8-F2
OWN-0046   GREEN   exp=PRESERVE_OWNED  /LINK_RECORD            got=PRESERVE_OWNED  /LINK_RECORD            rc=0   r6-F1
OWN-0047   GREEN   exp=PRESERVE_OWNED  /LINK_RECORD            got=PRESERVE_OWNED  /LINK_RECORD            rc=0   r6-F1
OWN-0048   GREEN   exp=PRESERVE_OWNED  /LINK_RECORD            got=PRESERVE_OWNED  /LINK_RECORD            rc=0   r7-F3
OWN-0049   GREEN   exp=PRESERVE_OWNED  /LINK_RECORD            got=PRESERVE_OWNED  /LINK_RECORD            rc=0   r7-F3
OWN-0050   GREEN   exp=OMIT_RECORD     /HASH_NONE              got=OMIT_RECORD     /HASH_NONE              rc=0   r10-F1
OWN-0051   GREEN   exp=OMIT_RECORD     /HASH_NONE              got=OMIT_RECORD     /HASH_NONE              rc=0   r10-F1
OWN-0052   RED     exp=PRESERVE_UNOWNED/HASH_NONE              got=PRESERVE_OWNED  /LINK_RECORD            rc=0   r11-F1
OWN-0053   RED     exp=PRESERVE_UNOWNED/HASH_NONE              got=PRESERVE_OWNED  /LINK_RECORD            rc=0   r11-F1
OWN-0060   GREEN   exp=PRESERVE_OWNED  /HASH_SOURCE            got=PRESERVE_OWNED  /HASH_SOURCE            rc=0   adr-155-amend-1
OWN-0061   GREEN   exp=PRESERVE_OWNED  /HASH_SOURCE            got=PRESERVE_OWNED  /HASH_SOURCE            rc=0   r2-F2
OWN-0062   GREEN   exp=PRESERVE_OWNED  /HASH_SOURCE            got=PRESERVE_OWNED  /HASH_SOURCE            rc=0   r5-F3
OWN-0063   GREEN   exp=PRESERVE_OWNED  /HASH_SOURCE            got=PRESERVE_OWNED  /HASH_SOURCE            rc=0   r10-F3
OWN-0064   GREEN   exp=PRESERVE_OWNED  /HASH_SOURCE            got=PRESERVE_OWNED  /HASH_SOURCE            rc=0   adr-155-amend-1
OWN-0070   GREEN   exp=PRESERVE_OWNED  /HASH_SOURCE            got=PRESERVE_OWNED  /HASH_SOURCE            rc=0   r7-F2
OWN-0071   GREEN   exp=PRESERVE_OWNED  /HASH_PRIOR_RECORD      got=PRESERVE_OWNED  /HASH_PRIOR_RECORD      rc=0   r7-F2
OWN-0072   GREEN   exp=PRESERVE_OWNED  /HASH_PRIOR_RECORD      got=PRESERVE_OWNED  /HASH_PRIOR_RECORD      rc=0   r9-F2
OWN-0073   GREEN   exp=REFRESH         /HASH_SOURCE            got=REFRESH         /HASH_SOURCE            rc=0   adr-155-amend-1
OWN-0080   GREEN   exp=OMIT_RECORD     /HASH_NONE              got=OMIT_RECORD     /HASH_NONE              rc=0   r9-F4
OWN-0081   GREEN   exp=OMIT_RECORD     /HASH_NONE              got=OMIT_RECORD     /HASH_NONE              rc=0   r11-F3
OWN-0082   RED     exp=PRESERVE_OWNED  /HASH_PRIOR_RECORD      got=OMIT_RECORD     /HASH_NONE              rc=0   adr-155-amend-1
OWN-0090   GREEN   exp=REFRESH         /HASH_SOURCE            got=REFRESH         /HASH_SOURCE            rc=0   r7-F1
OWN-0091   GREEN   exp=PRESERVE_OWNED  /HASH_SOURCE            got=PRESERVE_OWNED  /HASH_SOURCE            rc=0   r7-F1

GREEN=50  RED=11  AMBIG=0  HARNESS-ERR=0

exec
/bin/zsh -lc 'bash scripts/tests/test-ownership-verdict-unit.sh --quiet; rc1=$?; echo unit_rc=$rc1; bash scripts/tests/test-ownership-table.sh --only OWN-0052,OWN-0053; rc2=$?; echo e2e_rc=$rc2; exit 0' in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:

unit oracle: PASS=60  FAIL=0  SKIPPED(execution-fault rows)=2
  not decision cells, covered by the e2e: OWN-0024 OWN-0027 
unit_rc=0
mktemp: mkdtemp failed on /var/folders/9n/hm9srl0s1nz45_p12tj61pd80000gn/T//plan167-own.m8jSHC: Operation not permitted
e2e_rc=2

exec
/bin/zsh -lc "grep -n \"LINK\" -n scripts/uninstall.sh | head -80; nl -ba scripts/uninstall.sh | sed -n '300,520p'; grep -R \"_prior_link_target_matches\" -n ." in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 1794ms:
./scripts/install.sh:2319:  _prior_link_target_matches() {   # $1 = manifest, $2 = relpath
./scripts/install.sh:2332:     && _prior_link_target_matches "$manifest" "SPEC/v1"; then
./scripts/install.sh:2341:     && _prior_link_target_matches "$manifest" "PROTOCOL.md"; then
./scripts/install.sh:2366:     && _prior_link_target_matches "$manifest" ".claude/.framework-version"; then

exec
/bin/zsh -lc "grep -n \"install-manifest\\|manifest\" scripts/uninstall.sh | head -100; wc -l scripts/uninstall.sh; sed -n '1,260p' scripts/uninstall.sh" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
2:# uninstall.sh — manifest-honoring uninstaller for ceo-orchestration
6:# recorded manifest entry. Files modified by the user post-install have
7:# divergent SHAs and are PRESERVED. Files NOT listed in the manifest
18:#   --no-hmac-verify           Skip HMAC verification of the manifest sidecar
24:#   2  target path invalid OR no manifest found
25:#   3  HMAC verification failed (manifest tampered)
154:# UNINSTALL MODE — manifest-honoring removal
156:MANIFEST="$TARGET/.claude/.install-manifest.sha256"
159:  echo "ERROR: install manifest not found at $MANIFEST" >&2
165:_log "==> Uninstall mode (manifest-honoring)"
193:# Walk the manifest; for each entry, verify SHA before delete.
256:  _log "    Preserved: $preserved_count (user-modified — sha didn't match manifest)"
264:# Clean up manifest + empty .claude/ subdirs (only if everything matched)
265:if ! _dry "would REMOVE manifest $MANIFEST"; then
     282 scripts/uninstall.sh
#!/usr/bin/env bash
# uninstall.sh — manifest-honoring uninstaller for ceo-orchestration
# (PLAN-083 sub-1.9)
#
# Safety property: ONLY removes files whose current sha256 matches the
# recorded manifest entry. Files modified by the user post-install have
# divergent SHAs and are PRESERVED. Files NOT listed in the manifest
# (Owner-authored, never installed by us) are also PRESERVED.
#
# Usage:
#   ./uninstall.sh <target-repo-path> [options]
#
# Options:
#   --dry-run                  Preview what WOULD be removed; touch nothing
#   --restore <backup-path>    Inverse mode: restore .claude/ from a backup .tar.gz
#   --force                    Remove files even if SHA mismatches (DESTRUCTIVE)
#   --no-backup                Skip the pre-uninstall backup tarball
#   --no-hmac-verify           Skip HMAC verification of the manifest sidecar
#   -h, --help                 Show this help
#
# Exit codes:
#   0  success (or dry-run preview)
#   1  generic failure / invalid args
#   2  target path invalid OR no manifest found
#   3  HMAC verification failed (manifest tampered)
#   4  --restore: backup tar.gz invalid or HMAC mismatch
#   5  --force not provided when SHA mismatches encountered
#
# Bash 3.2 portability guard
if [ -z "${BASH_VERSINFO:-}" ]; then
  echo "ERROR: uninstall.sh requires bash" >&2
  exit 1
fi
if [ "${BASH_VERSINFO[0]}" -lt 3 ] || \
   { [ "${BASH_VERSINFO[0]}" -eq 3 ] && [ "${BASH_VERSINFO[1]}" -lt 2 ]; }; then
  echo "ERROR: uninstall.sh requires bash >= 3.2 (detected ${BASH_VERSION})" >&2
  exit 1
fi

set -euo pipefail

TARGET=""
DRY_RUN=0
RESTORE_PATH=""
FORCE=0
NO_BACKUP=0
NO_HMAC_VERIFY=0

while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run)         DRY_RUN=1; shift ;;
    --restore)         RESTORE_PATH="${2:-}"; shift 2 ;;
    --restore=*)       RESTORE_PATH="${1#--restore=}"; shift ;;
    --force)           FORCE=1; shift ;;
    --no-backup)       NO_BACKUP=1; shift ;;
    --no-hmac-verify)  NO_HMAC_VERIFY=1; shift ;;
    -h|--help)
      sed -n '1,30p' "${BASH_SOURCE[0]}"
      exit 0
      ;;
    -*)
      echo "ERROR: unknown option: $1" >&2
      exit 1
      ;;
    *)
      TARGET="$1"
      shift
      ;;
  esac
done

if [ -z "$TARGET" ] || [ ! -d "$TARGET" ]; then
  echo "Usage: $0 <target-repo-path> [--dry-run | --restore <backup.tar.gz> | --force]" >&2
  exit 1
fi

TARGET="$( cd "$TARGET" && pwd )"

_log() { printf '%s\n' "$*"; }
_dry() {
  if [ "$DRY_RUN" -eq 1 ]; then
    printf '(dry-run) %s\n' "$*"
    return 0
  fi
  return 1
}

# ---------------------------------------------------------------------------
# Resolve HMAC backup key (same algorithm as install.sh)
# ---------------------------------------------------------------------------
_resolve_backup_key() {
  if [ -f "$TARGET/.claude/.audit-key" ]; then
    printf '%s\n' "$TARGET/.claude/.audit-key"
    return 0
  fi
  if [ -f "$TARGET/.claude/.install-backup-key" ]; then
    printf '%s\n' "$TARGET/.claude/.install-backup-key"
    return 0
  fi
  return 1
}

# ---------------------------------------------------------------------------
# RESTORE MODE — invert a backup
# ---------------------------------------------------------------------------
if [ -n "$RESTORE_PATH" ]; then
  if [ ! -f "$RESTORE_PATH" ]; then
    echo "ERROR: backup file not found: $RESTORE_PATH" >&2
    exit 4
  fi
  _log "==> Restore mode: $RESTORE_PATH -> $TARGET"

  # Optional HMAC verification of backup
  if [ -f "$RESTORE_PATH.hmac" ] && [ "$NO_HMAC_VERIFY" -eq 0 ]; then
    key_path="$(_resolve_backup_key || true)"
    if [ -n "$key_path" ] && [ -f "$key_path" ]; then
      expected_hmac="$(awk '{print $1; exit}' "$RESTORE_PATH.hmac")"
      actual_hmac="$(python3 -c "
import hashlib, hmac, sys
key = open('$key_path', 'rb').read()
tar_sha = hashlib.sha256(open('$RESTORE_PATH', 'rb').read()).digest()
sys.stdout.write(hmac.new(key, tar_sha, hashlib.sha256).hexdigest())
")"
      if [ "$expected_hmac" != "$actual_hmac" ]; then
        echo "ERROR: backup HMAC mismatch — tarball may have been tampered with" >&2
        echo "       expected: $expected_hmac" >&2
        echo "       actual:   $actual_hmac" >&2
        exit 4
      fi
      _log "    Backup HMAC verified."
    else
      _log "    NOTE: no backup key found; skipping HMAC verification"
    fi
  fi

  if _dry "would EXTRACT $RESTORE_PATH into $TARGET"; then
    exit 0
  fi

  # Move existing .claude/ aside (safety net)
  if [ -d "$TARGET/.claude" ]; then
    aside="$TARGET/.claude.pre-restore-$(date -u +%Y%m%d-%H%M%SZ)"
    _log "    Moving current .claude/ aside to: $aside"
    mv "$TARGET/.claude" "$aside"
  fi

  _log "    Extracting backup..."
  ( cd "$TARGET" && tar xzf "$RESTORE_PATH" )
  _log "    Restore complete."
  exit 0
fi

# ---------------------------------------------------------------------------
# UNINSTALL MODE — manifest-honoring removal
# ---------------------------------------------------------------------------
MANIFEST="$TARGET/.claude/.install-manifest.sha256"

if [ ! -f "$MANIFEST" ]; then
  echo "ERROR: install manifest not found at $MANIFEST" >&2
  echo "       This target was not installed via PLAN-083 install.sh." >&2
  echo "       To remove manually, see INSTALL.md §Uninstall." >&2
  exit 2
fi

_log "==> Uninstall mode (manifest-honoring)"
_log "    Target:   $TARGET"
_log "    Manifest: $MANIFEST"
_log "    Dry-run:  $DRY_RUN"
_log "    Force:    $FORCE"
_log ""

# Pre-uninstall backup (unless --no-backup)
if [ "$NO_BACKUP" -eq 0 ]; then
  if ! _dry "would BACKUP .claude/ before uninstall"; then
    timestamp="$(date -u +%Y%m%d-%H%M%SZ)"
    backup="$TARGET/.claude.backup-uninstall-$timestamp.tar.gz"
    _log "==> Pre-uninstall backup: $backup"
    ( cd "$TARGET" && tar czf "$backup" .claude/ 2>/dev/null )
    key_path="$(_resolve_backup_key || true)"
    if [ -n "$key_path" ] && [ -f "$key_path" ]; then
      backup_hmac="$(python3 -c "
import hashlib, hmac, sys
key = open('$key_path', 'rb').read()
tar_sha = hashlib.sha256(open('$backup', 'rb').read()).digest()
sys.stdout.write(hmac.new(key, tar_sha, hashlib.sha256).hexdigest())
")"
      printf '%s  %s\n' "$backup_hmac" "$backup" > "$backup.hmac"
      chmod 0600 "$backup.hmac"
    fi
  fi
fi

# Walk the manifest; for each entry, verify SHA before delete.
mismatch_count=0
removed_count=0
preserved_count=0
absent_count=0
mismatch_files=""

while IFS= read -r line; do
  # Skip comments and blank lines
  case "$line" in
    '#'*|'') continue ;;
  esac
  # Format: <sha>  <relpath>
  recorded_sha="${line%% *}"
  rel="${line#* }"
  rel="${rel#* }"  # strip second space if double-space format
  rel="$(printf '%s' "$line" | awk '{ $1=""; sub(/^ +/, ""); print }')"
  fpath="$TARGET/$rel"

  if [ ! -e "$fpath" ]; then
    absent_count=$((absent_count + 1))
    continue
  fi

  if [ ! -f "$fpath" ]; then
    continue
  fi

  actual_sha="$(python3 -c "
import hashlib, sys
with open(sys.argv[1], 'rb') as f:
    sys.stdout.write(hashlib.sha256(f.read()).hexdigest())
" "$fpath")"

  if [ "$actual_sha" = "$recorded_sha" ]; then
    if _dry "would REMOVE $rel"; then
      removed_count=$((removed_count + 1))
    else
      rm -f "$fpath"
      removed_count=$((removed_count + 1))
    fi
  else
    mismatch_count=$((mismatch_count + 1))
    mismatch_files="$mismatch_files $rel"
    if [ "$FORCE" -eq 1 ]; then
      if _dry "would FORCE-REMOVE (sha mismatch) $rel"; then
        removed_count=$((removed_count + 1))
      else
        rm -f "$fpath"
        removed_count=$((removed_count + 1))
      fi
    else
      preserved_count=$((preserved_count + 1))
      _log "    PRESERVED (sha mismatch, user-modified): $rel"
    fi
  fi
done < "$MANIFEST"

# Refuse if mismatches encountered without --force
if [ "$mismatch_count" -gt 0 ] && [ "$FORCE" -eq 0 ]; then
  _log ""
  _log "==> Uninstall summary (incomplete):"
  _log "    Removed:   $removed_count"
  _log "    Preserved: $preserved_count (user-modified — sha didn't match manifest)"
  _log "    Absent:    $absent_count (already gone)"
  _log ""
  _log "    To force-remove user-modified files: re-run with --force"
  _log "    Preserved files were NOT touched."

exec
/bin/zsh -lc "grep -R \"framework-version\" -n .claude/scripts scripts .github | head -120; printf '\\n--- current counts ---\\n'; find .claude/adr -maxdepth 1 -name 'ADR-*.md' | wc -l; grep -c '"'^      - name:'"' .github/workflows/release.yml; printf '\\n--- syntax checks ---\\n'; bash -n scripts/_framework_manifest_set.sh && echo fms-ok; bash -n scripts/install.sh && echo install-ok; bash -n scripts/upgrade.sh && echo upgrade-ok; bash -n scripts/doctor.sh && echo doctor-ok; bash -n .claude/scripts/check-framework-updates.sh && echo checker-ok; bash -n scripts/tests/test-ownership-table.sh && echo table-ok; bash -n scripts/tests/test-ownership-verdict-unit.sh && echo unit-ok; bash -n scripts/tests/test-upgrade-spec-ownership.sh && echo spec-test-ok" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 351ms:
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
scripts/install.sh:1358:# .claude/.framework-version is a TRACKED file of the framework repo (one
scripts/install.sh:1370:  if [[ ! -f "$SOURCE_DIR/.claude/.framework-version" ]]; then
scripts/install.sh:1371:    echo "    SKIP: .claude/.framework-version absent in source (pre-v1.3.0 checkout)"
scripts/install.sh:1375:  echo "==> Installing framework version marker (.claude/.framework-version — $(tr -d '[:space:]' < "$SOURCE_DIR/.claude/.framework-version"))"
scripts/install.sh:1376:  _state_record_op "install_framework_marker" ".claude/.framework-version"
scripts/install.sh:1377:  install_one ".claude/.framework-version"
scripts/install.sh:1380:    _state_record_op "delivered_framework_marker" ".claude/.framework-version"
scripts/install.sh:2365:     && grep -Eq '^([0-9a-f]{64}|LINK)  \.claude/\.framework-version(  |$)' "$manifest" 2>/dev/null \
scripts/install.sh:2366:     && _prior_link_target_matches "$manifest" ".claude/.framework-version"; then
scripts/install.sh:2370:.claude/.framework-version"
scripts/install.sh:2371:    echo "    ownership continuity: .framework-version delivery record preserved from prior manifest"
scripts/install.sh:2391:      *".claude/.framework-version"*) export FMS_HASH_SOURCE_MARKER="HASH_SOURCE" ;;
scripts/install.sh:2418:      *".claude/.framework-version"*) export FMS_HASH_SOURCE_MARKER="HASH_SOURCE" ;;
scripts/_framework_manifest_set.sh:36:#     PROTOCOL.md, SPEC/v1 and .claude/.framework-version are enumerated ONLY
scripts/_framework_manifest_set.sh:40:#         FMS_DELIVERED_MARKER     .claude/.framework-version marker
scripts/_framework_manifest_set.sh:141:      printf '%s\n' ".claude/.framework-version"
scripts/_framework_manifest_set.sh:301:    .claude/.framework-version) printf '%s' "${FMS_HASH_SOURCE_MARKER:-}" ;;
scripts/_framework_manifest_set.sh:308:    SPEC/v1|SPEC/v1/*|PROTOCOL.md|.claude/.framework-version) return 0 ;;
scripts/tests/ownership_table.tsv:59:OWN-0064	marker	hash	regular	pristine	yes	copy	maintainer	upgrade	self	none	PRESERVE_OWNED	HASH_SOURCE	adr-155-amend-1	--skip .claude/.framework-version
scripts/tests/test-upgrade-spec-ownership.sh:5:# .claude/.framework-version) across install → upgrade → doctor → updater.
scripts/tests/test-upgrade-spec-ownership.sh:75:if [ ! -f "$SOURCE_DIR/.claude/.framework-version" ]; then
scripts/tests/test-upgrade-spec-ownership.sh:76:  echo "FATAL: source has no .claude/.framework-version (F3 marker missing)" >&2
scripts/tests/test-upgrade-spec-ownership.sh:123:MARKER_REL=".claude/.framework-version"
scripts/tests/test-upgrade-spec-ownership.sh:144:manifest_has "$T1" '\.claude/\.framework-version(  |$)'    && ok "baseline records marker"      || bad "baseline has NO marker record"
scripts/tests/test-upgrade-spec-ownership.sh:218:sed -i.bak '/  \.claude\/\.framework-version/d' "$T1/$MANIFEST_REL" 2>/dev/null \
scripts/tests/test-upgrade-spec-ownership.sh:219:  || sed -i '' '/  \.claude\/\.framework-version/d' "$T1/$MANIFEST_REL" 2>/dev/null
scripts/tests/test-upgrade-spec-ownership.sh:282:manifest_has "$T3" '\.claude/\.framework-version(  |$)' \
scripts/tests/test-upgrade-spec-ownership.sh:330:manifest_has "$T4" '\.claude/\.framework-version(  |$)' \
scripts/tests/_parity_classify.py:149:        ".claude/.framework-version. Asserted positively below: B/VERSION must "
scripts/tests/_parity_classify.py:177:        "id": "F3-framework-version-marker",
scripts/tests/_parity_classify.py:179:        "path": ".claude/.framework-version",
scripts/tests/_parity_classify.py:182:            "root VERSION and into .claude/.framework-version, as a TRACKED "
scripts/tests/test-ownership-table.sh:100:    marker)   printf '.claude/.framework-version' ;;
scripts/tests/test-ownership-table.sh:257:  printf '1.3.1\n' > "$nxt/.claude/.framework-version"
scripts/doctor.sh:617:    # SPEC/v1 and .claude/.framework-version are CONDITIONAL on the
scripts/doctor.sh:643:    if _dr_delivered '\.claude/\.framework-version(  |$)'; then
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
scripts/upgrade.sh:2049:  _sk="$( _ov_obs_skip ".claude/.framework-version" )"
scripts/upgrade.sh:2055:    echo "    WARNING: .claude/.framework-version dimensions are not a legal cell" >&2
scripts/upgrade.sh:2067:        ancestor_symlink/*) echo "    SKIP: .claude/.framework-version has a symlinked ancestor (refusing to write through it — F11a)" ;;
scripts/upgrade.sh:2068:        symlink/*)          echo "    SKIP: .claude/.framework-version is the recorded --mode link delivery (target unchanged)" ;;
scripts/upgrade.sh:2069:        */self)             echo "    SKIPPED (--skip): .claude/.framework-version" ;;
scripts/upgrade.sh:2070:        *)                  echo "    SKIP: .claude/.framework-version (ownership carried forward)" ;;
scripts/upgrade.sh:2080:        echo "    SKIP: .claude/.framework-version absent in source (pre-v1.3.0 checkout)"
scripts/upgrade.sh:2086:        echo "    WARNING: .claude/.framework-version is a symlink that does NOT match the" >&2
scripts/upgrade.sh:2090:        echo "    SKIP: .claude/.framework-version is $_lt — adopter-owned, refusing to write into/through it"
scripts/upgrade.sh:2097:        echo "    (dry-run) would REFRESH: .claude/.framework-version ($(tr -d '[:space:]' < "$src" 2>/dev/null || true))"
scripts/upgrade.sh:2103:          echo "    BACKED UP: .claude/.framework-version -> $bak"
scripts/upgrade.sh:2106:          echo "    WARNING: could not back up differing .claude/.framework-version —" >&2
scripts/upgrade.sh:2109:          _up_record_op "preserve_marker_backup_failed" ".claude/.framework-version"
scripts/upgrade.sh:2125:        echo "    REFRESHED: .claude/.framework-version ($(tr -d '[:space:]' < "$dst" 2>/dev/null || true))"
scripts/upgrade.sh:2127:        echo "    WARNING: .claude/.framework-version write did not validate — NOT recorded as" >&2
scripts/upgrade.sh:3073:echo "==> Refreshing framework version marker (.claude/.framework-version)"
scripts/upgrade.sh:3129:  elif [[ -L "$TARGET/.claude/skills" || -L "$TARGET/SPEC/v1" || -L "$TARGET/.claude/.framework-version" ]]; then
.github/workflows/release.yml:74:      # framework version marker `.claude/.framework-version` is a TRACKED
.github/workflows/release.yml:84:      - name: Assert framework-version marker matches VERSION
.github/workflows/release.yml:88:          if [[ ! -f .claude/.framework-version ]]; then
.github/workflows/release.yml:89:            echo "::error::.claude/.framework-version is missing — it is a tracked file (PLAN-166 F3 / ADR-155-AMEND-1); a release checkout without it must not ship"
.github/workflows/release.yml:92:          MARKER="$(tr -d '[:space:]' < .claude/.framework-version)"
.github/workflows/release.yml:94:            echo "::error::.claude/.framework-version ('$MARKER') does not match VERSION ('$FILE') — the marker is byte-identical to VERSION by contract (Forma A (ii), fail-closed)"
.github/workflows/release.yml:97:          echo "OK: .claude/.framework-version=$MARKER matches VERSION"
.github/workflows/smoke-install.yml:36:      - ".claude/.framework-version"
.github/workflows/smoke-install.yml:64:      - ".claude/.framework-version"
.github/workflows/smoke-install.yml:215:      # .claude/.framework-version) across install -> upgrade -> doctor ->

--- current counts ---
     189
31

--- syntax checks ---
fms-ok
install-ok
upgrade-ok
doctor-ok
checker-ok
table-ok
unit-ok
spec-test-ok

exec
/bin/zsh -lc "grep -R \"VERSION.*site\\|bump.*site\\|VERSION_SITES\\|version sites\\|11th\\|12th\" -n .claude/scripts .claude/skills .github/scripts scripts | head -200; find . -iname '*bump*' -o -iname '*version*' | head -120; grep -R \"verify-counts\" -n .claude/scripts | head" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 1004ms:
.claude/scripts/tests/test_token_budget_guard.py:6:  - volume cap: 11th emit in 1h suppressed (per AC5c)
.claude/scripts/tests/test_token_budget_guard.py:267:    def test_volume_cap_suppresses_11th_emit(self):
.claude/scripts/tests/test_await_release_gate.py:302:    class as F2's ``--today`` in ``_release_bump_sites.py``: the input that
.claude/scripts/tests/test_verify_counts_remediation.py:247:        to VERSION_SITES *and* flip this test, so the decision cannot
.claude/scripts/tests/test_release_bump_sites.py:47:SITES_SRC = LOCAL / "_release_bump_sites.py"
.claude/scripts/tests/test_release_bump_sites.py:63:bump_sites = _load(SITES_SRC, "_release_bump_sites_under_test")
.claude/scripts/tests/test_release_bump_sites.py:120:    for rel in bump_sites.site_paths(include_generated=True):
.claude/scripts/tests/test_release_bump_sites.py:142:# It DOES model the support-window family (VERSION_SITES modes "minor" and
.claude/scripts/tests/test_release_bump_sites.py:143:# "prev_minor" on SECURITY.md/VERSIONING.md, added S293): the re-pass F-sites
.claude/scripts/tests/test_release_bump_sites.py:305:        (SITES_SRC, repo / ".claude/scripts/local/_release_bump_sites.py"),
.claude/scripts/tests/test_release_bump_sites.py:347:        [sys.executable, ".claude/scripts/local/_release_bump_sites.py"] + list(args),
.claude/scripts/tests/test_release_bump_sites.py:365:    own = bump_sites.site_paths()
.claude/scripts/tests/test_release_bump_sites.py:366:    both = bump_sites.site_paths(include_generated=True)
.claude/scripts/tests/test_release_bump_sites.py:371:    assert both[len(own):] == bump_sites.GENERATED_BY_BUMP
.claude/scripts/tests/test_release_bump_sites.py:429:# (verify-counts VERSION_SITES, S293) — a writer without them dies MID-PHASE
.claude/scripts/tests/test_release_bump_sites.py:433:def test_minor_bump_rewrites_the_support_window_sites(synth):
.claude/scripts/tests/test_release_bump_sites.py:490:    LIVE verify-counts VERSION_SITES must have a writer site — derived from
.claude/scripts/tests/test_release_bump_sites.py:502:    writer = {(path, kind) for path, kind, _rx in bump_sites._SITES}
.claude/scripts/tests/test_release_bump_sites.py:510:        "verify-counts VERSION_SITES entries with NO writer site (the next "
.claude/scripts/tests/test_release_bump_sites.py:620:    mod = repo / ".claude/scripts/local/_release_bump_sites.py"
.claude/scripts/tests/test_pair_rail_inputs_manifest_bump_guard.py:55:  * bump table         <- `_release_bump_sites.site_paths()`.
.claude/scripts/tests/test_pair_rail_inputs_manifest_bump_guard.py:96:_BUMP_SRC = REPO / ".claude" / "scripts" / "local" / "_release_bump_sites.py"
.claude/scripts/tests/test_pair_rail_inputs_manifest_bump_guard.py:122:BUMP = _load(_BUMP_SRC, "_ceo_t166_release_bump_sites")
.claude/scripts/tests/test_pair_rail_inputs_manifest_bump_guard.py:251:            "  only in _release_bump_sites.site_paths(include_generated=True): %s\n"
.claude/scripts/local/verify-counts.sh:1012:    # design (they point at the VERSION file). Every remaining site is
.claude/scripts/local/verify-counts.sh:1014:    VERSION_SITES = [
.claude/scripts/local/verify-counts.sh:1043:    for doc, rx, mode in VERSION_SITES:
.claude/scripts/local/release.sh:31:#   bump       version sites + plugin manifests + commit
.claude/scripts/local/release.sh:44:#                    list is DERIVED from _release_bump_sites.py, never typed.
.claude/scripts/local/release.sh:105:BUMP_SITES=".claude/scripts/local/_release_bump_sites.py"
.claude/scripts/local/release.sh:188:  || die "cannot enumerate version sites from $BUMP_SITES"
.claude/scripts/local/release.sh:192:  VERSION_FILES+=("$_site")
.claude/scripts/local/release.sh:194:[ "${#VERSION_FILES[@]}" -gt 0 ] || die "$BUMP_SITES returned no version sites"
.claude/scripts/local/release.sh:424:# The site table lives in `_release_bump_sites.py` and NOWHERE else: this
.claude/scripts/local/release.sh:455:# of the SBOM/SECURITY/VERSIONING stamps, which are outside the VERSION_SITES
.claude/scripts/local/release.sh:470:  hdr "bump version sites to $TARGET_BASE"
.claude/scripts/local/release.sh:527:  # version sites invisible to the local oracle.
.claude/scripts/local/release.sh:538:  # mirror it into _release_bump_sites.py.
.claude/scripts/local/release.sh:548:  ok "verify-counts clean across the doc/package version sites"
.claude/scripts/local/release.sh:567:Version bump across every site the three oracles enforce (the doc/package
.claude/scripts/local/release.sh:570:${TARGET_TAG}. The site table is .claude/scripts/local/_release_bump_sites.py.
.claude/scripts/local/_release_bump_sites.py:3:# _release_bump_sites.py — the ONE source of truth for the release version
.claude/scripts/local/_release_bump_sites.py:30:# verify-counts' VERSION_SITES; SBOM.md / SECURITY.md / VERSIONING.md are
.claude/scripts/local/_release_bump_sites.py:36:# verify-counts' VERSION_SITES also watches "Current MINOR (vX.Y.x)" and
.claude/scripts/local/_release_bump_sites.py:95:    # --- the support window (oracle: verify-counts VERSION_SITES modes
.claude/scripts/local/_release_bump_sites.py:242:        prog="_release_bump_sites.py",
.claude/scripts/local/_release_bump_sites.py:257:    p_bump = sub.add_parser("bump", help="rewrite the version sites")
.claude/scripts/substrate-watch.json:59:      "watch_for": "codex `exec` flag-surface drift (the PLAN-142 / S214-S230 class): --color, -s/--sandbox enum (read-only|workspace-write|danger-full-access), -o/--output-last-message, --output-schema, --json (JSONL event stream), -m/--model; AND the removals that broke the rail on 0.139 \u2014 the old read-only/no-color/strict-json flags, and resume becoming an `exec resume` subcommand. All CLI shape lives in .claude/hooks/_lib/codex_cli_shape.py so a new removal/rename there is a NON-kernel edit. Also watch the binary-SHA pin (codex-cli-binary-sha256.txt) + the semver pin (codex-cli-pin.txt) when the binary upgrades. PLAN-156 Wave 1: bumped pin to <0.145.0 for GPT-5.6 (Sol/Terra/Luna first-class @0.143; 0.143 renamed the sandbox permission-profile flag \u2014 re-audit call sites on every bump). Also watch the silent-model-fallback class (a CLI whose bundled model catalog predates a server-side model launch answers 'requires a newer version' \u2014 the S266/gpt-5.6 class)."
.claude/scripts/substrate-watch.json:78:      "watch_for": "PLAN-156: grok hook-surface drift on a DAILY-release proprietary 0.x. Re-run the S269 characterization probes (PLAN-156/artifacts/characterization-grok-codex-S269.md) on every pin bump: (a) the PreToolUse decision semantics \u2014 block still fail-opens even with exit 2? deny-via-stdout still blocks? (probes P2/P4/P5/P7); (b) DOUBLE-FIRE \u2014 do the compat kill switches ([compat.claude] hooks=false, GROK_CLAUDE_HOOKS_ENABLED=0) start working at runtime? if so the native .grok/hooks/ single-surface decision (OQ1) can be revisited (probe P8); (c) tool-name vocabulary on the wire (run_terminal_command vs run_terminal_cmd) + the alias table; (d) the --sandbox council profile still kernel-enforces (negative control: unknown profile name must refuse to start \u2014 on 0.2.93 it only WARNS and runs unsandboxed, so the council asserts a ProfileApplied+enforced line in ~/.grok/sandbox-events.jsonl). Pin files: grok-cli-pin.txt (EXACT version, not a range) + grok-cli-binary-sha256.txt (the real supply-chain gate). Binary at ~/.grok/bin/grok. NO CI can automate this \u2014 no grok binary/secret on any runner (the substrate-watch obligation the Owner ratified at Wave-0).",
.claude/scripts/await_release_gate.py:70:successes. Same doctrine as ``_release_bump_sites.py --today``: a parameter
scripts/install.sh:1359:# line, byte-identical to VERSION — the bump writes it as its 12th site and
./VERSIONING.md
./tools/check-version-drift.py
./.claude/adr/ADR-073-semver-bump-criteria-sprint-32.md
./.claude/adr/ADR-094-claude-sdk-compat-version-pinning.md
./.claude/adr/ADR-142-opus-4-8-model-bump.md
./.claude/hooks/tests/mutations/engine_mutations/mutation_14_compiler_schema_version_passthrough.py
./.claude/scripts/tests/test_release_bump_sites.py
./.claude/scripts/tests/test_pair_rail_inputs_manifest_bump_guard.py
./.claude/scripts/local/_release_bump_sites.py
./.claude/.framework-version
./.claude/skills/core/product-conversion-readiness
./docs/actions-versions.md
./VERSION
.claude/scripts/tests/test_verify_counts.py:1:"""verify-counts.sh hardened-gate unit tests.
.claude/scripts/tests/test_verify_counts.py:23:SCRIPT = REPO_ROOT / ".claude" / "scripts" / "local" / "verify-counts.sh"
.claude/scripts/tests/test_verify_counts.py:194:    # with: verify-counts.sh --json --no-tests | jq .rule_matches_by_doc
.claude/scripts/tests/test_verify_counts_remediation.py:1:"""verify-counts.sh E9-F10 recurrence-guard gate tests (PLAN-120-FOLLOWUP WS-B).
.claude/scripts/tests/test_verify_counts_remediation.py:3:The E9-F10 finding showed verify-counts.sh had 3 blind spots that let the
.claude/scripts/tests/test_verify_counts_remediation.py:34:SCRIPT = REPO_ROOT / ".claude" / "scripts" / "local" / "verify-counts.sh"
.claude/scripts/tests/test_release_bump_sites.py:138:# Fixture stand-in for verify-counts.sh: version equality across the watched
.claude/scripts/tests/test_release_bump_sites.py:310:    (repo / ".claude/scripts/local/verify-counts.sh").write_text(
.claude/scripts/tests/test_release_bump_sites.py:409:    # (verify-counts removed its dead rule in S291 with the archaeology in a
.claude/scripts/tests/test_release_bump_sites.py:429:# (verify-counts VERSION_SITES, S293) — a writer without them dies MID-PHASE

exec
/bin/zsh -lc "sed -n '1,150p' .claude/scripts/local/_release_bump_sites.py; sed -n '990,1065p' .claude/scripts/local/verify-counts.sh; sed -n '350,530p' .claude/scripts/tests/test_release_bump_sites.py" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
#!/usr/bin/env python3
# ============================================================================
# _release_bump_sites.py — the ONE source of truth for the release version
# sites, and the only writer of them.
#
# Why a module and not a heredoc. Until PLAN-166/W0 this table lived inside
# `release.sh` as a `python3 - <<'PY'` heredoc. That had two costs that both
# showed up in the v1.3.0-rc.1 re-pass:
#
#   1. the site list existed TWICE — once in the heredoc (the writer) and once
#      in the driver's `VERSION_FILES` array (the dry-run restore list). A list
#      that must match another list by hand does not stay matched; a restore
#      list shorter than the write list leaves debris (the S273 class).
#   2. it was untestable. `--today` could not be pinned, so the D+1
#      non-idempotence (F2) could not be exercised by a test.
#
# Both are closed here: the driver DERIVES its restore list from
# `print-sites --include-generated`, and `--today` is a REQUIRED parameter with
# NO DEFAULT (a parameter that changes the verdict never has a default —
# frozen-evidence lesson).
#
# Idempotence contract (F2). A `last-reviewed:` stamp asserts "this document
# was re-read FOR THIS RELEASE". Re-dating it without re-reading is a false
# claim on a surface that a signed tag then covers. So the stamp sites
# skip the ENTIRE line — neither date nor version — when the version already
# on the stamp is the target. `--restamp` is the named, explicit route for a
# real re-review.
#
# The two stamp oracles (do not collapse them). `npm/README.md` is watched by
# verify-counts' VERSION_SITES; SBOM.md / SECURITY.md / VERSIONING.md are
# watched ONLY by check-canonical-doc-freshness.py. Both oracles decide on the
# VERSION in the stamp, never on the date — which is what makes freezing the
# date safe.
#
# The support window (kinds "minor"/"prev_minor" — v1.3.0 re-pass, F-sites).
# verify-counts' VERSION_SITES also watches "Current MINOR (vX.Y.x)" and
# "Previous MINOR (vX.Y.x)" in SECURITY.md and VERSIONING.md (S293). Those
# sites were OUTSIDE this table at birth, so the next MINOR bump would write
# everything else, then DIE at the driver's own verify-counts call with a
# half-written tree (outside --dry-run there is no restore trap). The rule the
# oracle enforces is mechanical — Current = the target's minor, Previous = the
# minor immediately before it — so this writer derives both from --target and
# the "ONE source of truth" claim above stays true. The single non-derivable
# case, an X.0.0 target, is SKIPPED loudly and never guessed: the oracle
# cannot value-check it either (it derives prev="" at X.0), and a MAJOR
# support-window transition is release-train judgment, not sed.
# ============================================================================
"""Release version-site table + writer (stdlib only, Python >= 3.9)."""

from __future__ import annotations

import argparse
import os
import re
import sys
from typing import Callable, List, Optional, Sequence, Tuple

SEMVER = r"\d+\.\d+\.\d+"
STAMP_RX = r"(last-reviewed: )(\d{4}-\d{2}-\d{2})( +v)(" + SEMVER + r")"
DATE_RX = re.compile(r"\A\d{4}-\d{2}-\d{2}\Z")

# Kinds:
#   "plain"      — literal regex substitution, no stamp semantics.
#   "stamp"      — "last-reviewed: <date> v<version>"; skipped wholesale when
#                  the version already equals the target (unless --restamp).
#   "minor"      — support-window site carrying the TARGET's minor (vX.Y.x).
#   "prev_minor" — support-window site carrying the minor immediately BEFORE
#                  the target; not derivable at X.0.0 (skipped loudly there).
PLAIN = "plain"
STAMP = "stamp"
MINOR = "minor"
PREV_MINOR = "prev_minor"

# (path, kind, pattern) — patterns anchored exactly as their oracle checks
# them, so historical version mentions elsewhere in the file are never touched.
_SITES: List[Tuple[str, str, str]] = [
    ("VERSION", PLAIN, r"\A\s*" + SEMVER + r"\s*\Z"),
    ("npm/package.json", PLAIN, r'("version"\s*:\s*")' + SEMVER + r'(")'),
    ("pyproject.toml", PLAIN, r'(?m)^(version\s*=\s*")' + SEMVER + r'(")'),
    ("INSTALL.md", PLAIN, r"(--pin v)" + SEMVER),
    (
        "docs/ARCHITECTURE.md",
        PLAIN,
        r"(currently\s+v)" + SEMVER + r"(, aligned with the repo)",
    ),
    # README.md and CLAUDE.md are deliberately NOT rows here: neither is a
    # version site. `VERSION=` never existed in either (verify-counts dropped
    # its dead rules for both in S291 — `git log -S 'VERSION='` finds no
    # commit that added one — and the release checklist states the same). A
    # writer row for a site no oracle watches would be that dead rule
    # reintroduced on the WRITE side: the day someone adds a `VERSION=` line
    # to README.md, the bump would rewrite a file every other surface
    # declares out of scope.
    ("SBOM.md", PLAIN, r"(\*\*Version:\*\* `)" + SEMVER + r"(`)"),
    # --- the support window (oracle: verify-counts VERSION_SITES modes
    #     "minor"/"prev_minor", S293). Patterns anchored exactly as the
    #     oracle's — SECURITY.md bolds the label, VERSIONING.md does not. ---
    ("SECURITY.md", MINOR, r"(\*\*Current MINOR\*\* \(`v)\d+\.\d+(\.x`\))"),
    ("VERSIONING.md", MINOR, r"(Current MINOR \(`v)\d+\.\d+(\.x`\))"),
    ("SECURITY.md", PREV_MINOR, r"(\*\*Previous MINOR\*\* \(`v)\d+\.\d+(\.x`\))"),
    ("VERSIONING.md", PREV_MINOR, r"(Previous MINOR \(`v)\d+\.\d+(\.x`\))"),
    # --- the review stamps (idempotence-critical; the table IS the census,
    #     a numeral here would be a mirror that drifts) ---
    ("npm/README.md", STAMP, STAMP_RX),
    ("SBOM.md", STAMP, STAMP_RX),
    ("SECURITY.md", STAMP, STAMP_RX),
    ("VERSIONING.md", STAMP, STAMP_RX),
]

# Written by the bump PHASE but not by this module: `build-plugin.py
# --write-manifests` regenerates them from VERSION. They belong in any
# derived restore/guard list, which is why they are exported here instead of
# being re-typed by every caller (the duplicated-list failure this module
# exists to kill).
GENERATED_BY_BUMP: List[str] = [
    ".claude-plugin/plugin.json",
    ".claude-plugin/marketplace.json",
]


def site_paths(include_generated: bool = False) -> List[str]:
    """Every path this module may write, de-duplicated, in table order."""
    out: List[str] = []
    for path, _kind, _rx in _SITES:
        if path not in out:
            out.append(path)
    if include_generated:
        for path in GENERATED_BY_BUMP:
            if path not in out:
                out.append(path)
    return out


def _plain_replacement(pattern: str, target: str) -> str:
    """Replacement string for a PLAIN site, rebuilt from its group count."""
    if pattern.startswith(r"\A"):  # the bare VERSION file
        return target + "\n"
    groups = re.compile(pattern).groups
    if groups == 0:
        return target
    if groups == 1:
        return r"\g<1>" + target
    return r"\g<1>" + target + r"\g<2>"


def _stamp_replacer(
    target: str, today: str, restamp: bool
) -> Callable[["re.Match"], str]:
    def _repl(m: "re.Match") -> str:
        if not restamp and m.group(4) == target:
    _consumed = _approx_consumed.get(_doc, set())
    for _m in _THOUSANDS_RX.finditer(_text):
        if _m.start() in _consumed:
            continue
        violations.append(
            "%s:%d: thousands-shaped approximation '%s' is consumed by NO "
            "approx rule — give it a live metric + matcher, or delete the "
            "numeral  (rule: approx/unmatched-sweep)"
            % (_doc, _text.count("\n", 0, _m.start()) + 1, _m.group(0).strip())
        )

# ---- E9-F10 (iii): VERSION-string coherence ----
# Anchored to the current-version DECLARATION sites ONLY (not historical
# CHANGELOG prose). Each (doc, regex) yields the literal version string, which
# must equal the live VERSION file. npm/package.json is read here (it is not in
# DOCS). A doc with zero matches contributes no violation.
if live_version:
    # S291 (pair-rail R2, P2): `VERSION=` NEVER existed in CLAUDE.md or
    # README.md — `git log -S 'VERSION='` finds no commit that added or
    # removed it. Both rules were dead from birth (the `registered` class
    # again), while the release checklist advertised them as checked.
    # Removed rather than faked: neither doc declares a version literal by
    # design (they point at the VERSION file). Every remaining site is
    # liveness-accounted below — a site that matches nothing now FAILS.
    VERSION_SITES = [
        ("INSTALL.md", r'--pin v(\d+\.\d+\.\d+)', "full"),
        # PLAN-161 V1 — current-version declaration sites in the newly-watched
        # docs (the npm README review stamp is a deliberate release tripwire:
        # a version bump forces a fresh review of the npm-facing copy).
        ("docs/ARCHITECTURE.md", r'currently\s+v(\d+\.\d+\.\d+), aligned with the repo', "full"),
        ("npm/README.md", r'last-reviewed: \d{4}-\d{2}-\d{2} v(\d+\.\d+\.\d+)', "full"),
        # S293 (codex NO-GO no rc.1 do v1.3.0 — P0s 2-4): TRÊS declarações de
        # versão corrente que estavam FORA desta lista e ficaram stale no
        # bump (a classe unwatched-doc de S291, de novo). SBOM declara o
        # triple completo; SECURITY/VERSIONING declaram a janela de suporte
        # como vMAJOR.MINOR.x — comparadas ao major.minor do VERSION vivo.
        ("SBOM.md", r'\*\*Version:\*\* `(\d+\.\d+\.\d+)`', "full"),
        ("SECURITY.md", r'\*\*Current MINOR\*\* \(`v(\d+\.\d+)\.x`\)', "minor"),
        ("VERSIONING.md", r'Current MINOR \(`v(\d+\.\d+)\.x`\)', "minor"),
        # S293 r3 P1: vigiar SÓ o Current deixa o PREVIOUS envelhecer em
        # silêncio — e a janela de suporte publicada é uma promessa a
        # adopters, não decoração. Previous = minor imediatamente anterior
        # ao vivo (rebase de MAJOR não é expressável aqui e falharia alto,
        # que é o comportamento correto para uma transição que exige juízo).
        ("SECURITY.md", r'\*\*Previous MINOR\*\* \(`v(\d+\.\d+)\.x`\)', "prev_minor"),
        ("VERSIONING.md", r'Previous MINOR \(`v(\d+\.\d+)\.x`\)', "prev_minor"),
    ]
    _live_minor = ".".join(live_version.split(".")[:2])
    try:
        _maj, _min = (int(x) for x in _live_minor.split("."))
        _prev_minor = "%d.%d" % (_maj, _min - 1) if _min > 0 else ""
    except ValueError:
        _prev_minor = ""
    for doc, rx, mode in VERSION_SITES:
        _text = texts.get(doc, "")
        # S293: SBOM/SECURITY/VERSIONING não estão em DOCS (as regras de
        # contagem não se aplicam a eles) — carregue direto, senão o site
        # nasce "morto" sobre texto nunca lido.
        if not _text:
            _p = os.path.join(root, doc)
            if os.path.isfile(_p):
                try:
                    _text = open(_p, encoding="utf-8").read()
                except OSError:
                    _text = ""
        _hits = 0
        if mode == "full":
            _expected = live_version
        elif mode == "prev_minor":
            _expected = _prev_minor
        else:
            _expected = _live_minor
        if not _expected:
            # Sem previous derivável (X.0): o site não é checável por valor;
            # a liveness abaixo ainda exige que ele EXISTA.
            _expected = None
    )


def guard(synth, *args: str):
    return run(
        [sys.executable, ".claude/scripts/local/_release_tag_guard.py"] + list(args),
        synth["repo"],
        synth["env"],
    )


# ===========================================================================
# the site table is a single source
# ===========================================================================
def test_print_sites_enumerates_the_table_and_the_generated_manifests():
    own = bump_sites.site_paths()
    both = bump_sites.site_paths(include_generated=True)
    for stamp_site in ("npm/README.md", "SBOM.md", "SECURITY.md", "VERSIONING.md"):
        assert stamp_site in own
    assert "VERSION" in own
    assert own == both[: len(own)]
    assert both[len(own):] == bump_sites.GENERATED_BY_BUMP
    # the manifests are NOT written by this module; they must not be silently
    # folded into the writer's own list
    assert ".claude-plugin/plugin.json" not in own


def test_today_is_a_required_parameter_with_no_default(synth):
    proc = module(synth, "bump", "--target", "1.3.0")
    assert proc.returncode != 0
    assert "--today" in proc.stderr
    assert "required" in proc.stderr


# ===========================================================================
# AC-1 — the writer, at the module layer, with D and D+1 explicit
# ===========================================================================
@pytest.mark.parametrize("today", [D0, D1])
def test_stamps_are_frozen_when_the_version_already_matches(synth, today):
    before = tree_fingerprint(synth["repo"])
    proc = module(synth, "bump", "--target", "1.3.0", "--today", today)
    assert proc.returncode == 0, proc.stderr
    assert tree_fingerprint(synth["repo"]) == before, (
        "a stamp moved on --today=%s with the version unchanged" % today
    )
    assert "line untouched" in proc.stdout or "already at" in proc.stdout


def test_a_real_version_change_still_writes_every_site(synth):
    repo = synth["repo"]
    write_sites(repo, "1.2.0", D0)
    proc = module(synth, "bump", "--target", "1.3.0", "--today", D1)
    assert proc.returncode == 0, proc.stderr
    assert (repo / "VERSION").read_text() == "1.3.0\n"
    assert '"version": "1.3.0"' in (repo / "npm/package.json").read_text()
    assert 'version = "1.3.0"' in (repo / "pyproject.toml").read_text()
    assert "--pin v1.3.0" in (repo / "INSTALL.md").read_text()
    assert "currently v1.3.0, aligned" in (repo / "docs/ARCHITECTURE.md").read_text()
    # README.md is NOT a version site: `VERSION=` never existed there
    # (verify-counts removed its dead rule in S291 with the archaeology in a
    # comment; the release checklist says the same). The fixture PLANTS the
    # literal so this asserts the writer leaves it alone — a writer row for a
    # site no oracle watches would rewrite a file every other surface
    # declares out of scope.
    assert (repo / "README.md").read_text() == "VERSION=1.2.0\n"
    for stamped in ("npm/README.md", "SBOM.md", "SECURITY.md", "VERSIONING.md"):
        text = (repo / stamped).read_text()
        assert "last-reviewed: %s v1.3.0" % D1 in text, stamped
    # the support window moved with the version: Current <- target minor,
    # Previous <- the minor before it (the oracle's own derivation)
    for doc in ("SECURITY.md", "VERSIONING.md"):
        text = (repo / doc).read_text()
        assert "v1.3.x" in text, doc
        assert "v1.2.x" in text, doc
        assert "v1.1.x" not in text, doc


# ===========================================================================
# the support window (re-pass F-sites P1): minor/prev_minor are ORACLE modes
# (verify-counts VERSION_SITES, S293) — a writer without them dies MID-PHASE
# at the driver's own verify-counts call on the next MINOR bump, outside
# --dry-run, with no restore trap: a half-bumped dirty tree.
# ===========================================================================
def test_minor_bump_rewrites_the_support_window_sites(synth):
    repo = synth["repo"]
    proc = module(synth, "bump", "--target", "1.4.0", "--today", D2)
    assert proc.returncode == 0, proc.stderr
    for doc in ("SECURITY.md", "VERSIONING.md"):
        text = (repo / doc).read_text()
        assert "v1.4.x" in text, doc  # Current shifted to the target minor
        assert "v1.3.x" in text, doc  # Previous = the old Current
        assert "v1.2.x" not in text, doc  # the stale window is GONE


def test_major_bump_shifts_current_and_leaves_previous_to_judgment(synth):
    """X.0.0: Previous MINOR is NOT derivable from the target alone, and the
    live oracle skips value-checking it there too (it derives prev="" at X.0).
    The writer must neither guess nor die half-written: Current shifts,
    Previous is left byte-identical, and the skip is ANNOUNCED — a silent
    stale support window is the unwatched-doc class wearing a new hat."""
    repo = synth["repo"]
    proc = module(synth, "bump", "--target", "2.0.0", "--today", D2)
    assert proc.returncode == 0, proc.stderr
    for doc in ("SECURITY.md", "VERSIONING.md"):
        text = (repo / doc).read_text()
        assert "v2.0.x" in text, doc
        assert "v1.2.x" in text, doc  # the old Previous, untouched
    assert "release-train judgment" in proc.stdout, proc.stdout


def test_minor_bump_survives_the_drivers_own_oracle_end_to_end(synth):
    """The exact death the finding describes, end-to-end: TARGET_BASE moved to
    the next MINOR, tree at the previous one. Before the fix the phase wrote
    ten sites and then DIED at its own verify-counts call ("a site is
    unpatched") — this asserts it reaches its commit with a clean tree."""
    repo, env = synth["repo"], synth["env"]
    drv = repo / ".claude/scripts/local/release.sh"
    src = drv.read_text(encoding="utf-8")
    m = re.search(r'(?m)^TARGET_BASE="(\d+\.\d+\.\d+)"$', src)
    assert m, "driver has no bare-semver TARGET_BASE"
    drv.write_text(
        src.replace(m.group(0), 'TARGET_BASE="1.4.0"'), encoding="utf-8"
    )
    git(repo, env, "add", "-A")
    git(repo, env, "commit", "-q", "-m", "fixture: retarget driver to 1.4.0")
    head_before = git(repo, env, "rev-parse", "HEAD")

    proc = driver(synth, "bump", "--stable", "--npm-readme-reviewed", "--today", D2)
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "a site is unpatched" not in proc.stderr, proc.stderr
    assert git(repo, env, "rev-parse", "HEAD") != head_before, "no commit made"
    index_and_worktree_clean(repo, env)
    assert (repo / "VERSION").read_text() == "1.4.0\n"
    for doc in ("SECURITY.md", "VERSIONING.md"):
        text = (repo / doc).read_text()
        assert "v1.4.x" in text and "v1.3.x" in text, doc


def test_writer_table_covers_every_mode_of_the_live_oracle():
    """Structural closure of the F-sites class: every (doc, mode) pair in the
    LIVE verify-counts VERSION_SITES must have a writer site — derived from
    the authority's own source, never recalled (closed-set lesson). A pair
    added to the oracle without a writer is a mid-bump death deferred to the
    next bump that moves that mode."""
    text = (LOCAL / "verify-counts.sh").read_text(encoding="utf-8")
    entries = re.findall(
        r'\(\s*"([^"]+)",\s*r\'[^\']*\',\s*"(full|minor|prev_minor)"\s*\)', text
    )
    modes = {mode for _doc, mode in entries}
    # parser liveness first: all three modes must be found, or the regex above
    # went stale and "nothing missing" would mean nothing at all
    assert {"full", "minor", "prev_minor"} <= modes, entries
    writer = {(path, kind) for path, kind, _rx in bump_sites._SITES}
    writer_paths = {path for path, _kind in writer}
    missing = []
    for doc, mode in entries:
        covered = doc in writer_paths if mode == "full" else (doc, mode) in writer
        if not covered:
            missing.append((doc, mode))
    assert not missing, (
        "verify-counts VERSION_SITES entries with NO writer site (the next "
        "bump that moves these modes dies mid-phase): %s" % missing
    )


def test_restamp_moves_the_stamps_at_an_unchanged_version(synth):
    repo = synth["repo"]
    proc = module(synth, "bump", "--target", "1.3.0", "--today", D1, "--restamp")
    assert proc.returncode == 0, proc.stderr
    for stamped in ("npm/README.md", "SBOM.md", "SECURITY.md", "VERSIONING.md"):
        assert "last-reviewed: %s v1.3.0" % D1 in (repo / stamped).read_text()


# ===========================================================================
# AC-1 — the same invariant at the DRIVER layer (the surface the Owner runs)
# ===========================================================================
@pytest.mark.parametrize("today", [D0, D1])
def test_ac1_bump_stable_on_an_already_target_tree_writes_nothing(synth, today):
    repo, env = synth["repo"], synth["env"]
    head_before = git(repo, env, "rev-parse", "HEAD")
    fp_before = tree_fingerprint(repo)

exec
/bin/zsh -lc "grep -n 'VERSION' scripts/upgrade.sh | cat; grep -n 'backup_and_replace' scripts/upgrade.sh | tail -80; grep -n 'PIN_REF\\|--pin' scripts/upgrade.sh | sed -n '1,200p'" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
88:  echo "ERROR: upgrade.sh requires bash >= 3.2 (detected ${BASH_VERSION})" >&2
194:# ADOPTER settings stays OFF. Flip _T34_VERSION_FLOOR_PROBE_PASSED to 1 in
200:_T34_VERSION_FLOOR_PROBE_PASSED=0
206:  [ "$_T34_VERSION_FLOOR_PROBE_PASSED" -eq 1 ]
346:  .claude/agent-metrics.md) are NOT touched, and the root VERSION file
853:# marker-first readers falling back to the stale root VERSION (codex W1
1870:#   * root VERSION: this function (and the whole upgrade) NEVER touches it —
1871:#     install_one is skip-if-exists, so on an adopter with its own VERSION
2021:# source VERSION every run, backs up a differing pre-existing copy, and
2024:# reader keyed off the SAME record) falls back to VERSION instead of
2079:        # content. Readers fall back to VERSION, which the pin DID update.
2083:          echo "          readers fall back to VERSION (which reflects the pinned source)" >&2
2088:        echo "             (readers fall back to VERSION)" >&2
2120:      # as delivered, so every marker-first reader falls back to VERSION rather
2128:        echo "             delivered (marker-first readers fall back to VERSION; r20)" >&2
3175:  if [[ -f "$SOURCE_DIR/VERSION" ]]; then
3176:    fw_version="$(tr -d '[:space:]' < "$SOURCE_DIR/VERSION" 2>/dev/null || true)"
1279:backup_and_replace() {
1858:# backup_and_replace: for a directory target with a baseline, the classified
1872:#     the framework never wrote there; backup_and_replace would TAKE the
2907:backup_and_replace ".claude/team.md"
2908:backup_and_replace ".claude/frontend-team.md"
2912:  backup_and_replace ".claude/skills/core"
2915:  backup_and_replace ".claude/skills/frontend"
2920:      backup_and_replace ".claude/skills/domains/$part"
2928:backup_and_replace ".claude/hooks"
2929:backup_and_replace ".claude/scripts"
2930:backup_and_replace ".claude/commands"
2931:backup_and_replace ".claude/pitfalls-catalog.yaml"
2932:backup_and_replace ".claude/task-chains.yaml"
6:#                                    [--pin <tag>] [--dry-run]
216:PIN_REF=""
249:    --pin)
250:      PIN_REF="${2:-}"
362:  --pin <tag>           Pin source to specific tag/SHA (SPEC v1 install-cli.md).
364:                        Example: --pin v1.18.0
437:  2 — target has uncommitted .claude/ changes when --pin was passed
462:  echo "Usage: $0 <target-repo-path> [--profile <list>] [--stack <name>] [--pin <tag>] [--dry-run]" >&2
469:# Wraps `git checkout --quiet "$PIN_REF"` with a 3-attempt retry on
553:# --pin contract (SPEC v1 install-cli.md, ADR-007):
562:# PLAN-161 U1 (codex r2 F4) — ONE composed EXIT cleanup. The --pin block used
566:# guarded by PINNED_CHECKOUT_DONE + ORIGINAL_BRANCH — the non-dry --pin
581:if [[ -n "$PIN_REF" ]]; then
586:  if ! git rev-parse --verify "$PIN_REF" >/dev/null 2>&1; then
587:    echo "ERROR: unknown --pin ref: $PIN_REF" >&2
604:    echo "==> Dry-run: diff between current source and --pin $PIN_REF"
605:    ( cd "$SOURCE_DIR" && git diff "$PIN_REF"...HEAD -- .claude/ scripts/ templates/ SPEC/ || true )
610:  # bare `git checkout --quiet "$PIN_REF"` call at the previous
613:  if ! _git_checkout_with_lock_retry "$SOURCE_DIR" "$PIN_REF"; then
614:    echo "ERROR: git checkout $PIN_REF failed in source." >&2
789:if [[ -n "$PIN_REF" ]]; then
790:  echo "    Pinned:  $PIN_REF"
2077:        # The documented --pin downgrade: this source predates the marker, so a
3183:    "pin" "$PIN_REF"

exec
/bin/zsh -lc "nl -ba scripts/upgrade.sh | sed -n '3160,3345p'; nl -ba scripts/install.sh | sed -n '2440,2680p'" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
  3160	# pre-Wave-B adopter (no state file) ACQUIRES one on their first post-Wave-B
  3161	# upgrade, so the NEXT upgrade can replay. Merge semantics preserve the
  3162	# ORIGINAL install request (argv, mode, ceremony, placeholders map) and only
  3163	# update the replayable fields (request.profile/request.stack) to the values
  3164	# THIS run effectively used; the upgrade run itself is recorded under
  3165	# last_upgrade + history. Atomic (same-directory tempfile + os.replace),
  3166	# schema ceo.install-state/v1, fail-open (a write problem emits a NOTE and
  3167	# never aborts the completed upgrade). Skipped on --dry-run.
  3168	_write_upgrade_state() {
  3169	  [[ "$DRY_RUN" -eq 0 ]] || return 0
  3170	  if ! command -v python3 >/dev/null 2>&1; then
  3171	    echo "    NOTE: install-state not (re)written (python3 not found) — the next upgrade uses the ADR-155 fallback path" >&2
  3172	    return 0
  3173	  fi
  3174	  local fw_version=""
  3175	  if [[ -f "$SOURCE_DIR/VERSION" ]]; then
  3176	    fw_version="$(tr -d '[:space:]' < "$SOURCE_DIR/VERSION" 2>/dev/null || true)"
  3177	  fi
  3178	  local pairs=(
  3179	    "target" "$TARGET"
  3180	    "profile" "$PROFILE"
  3181	    "stack" "$STACK"
  3182	    "on_conflict" "$ON_CONFLICT"
  3183	    "pin" "$PIN_REF"
  3184	    "replay_source" "$_REPLAY_SOURCE"
  3185	    "harness" "$HARNESS"
  3186	    "managed_hooks" "$CODEX_MANAGED_HOOKS"
  3187	    "ceremony_effective" "$CEREMONY_EFFECTIVE"
  3188	  )
  3189	  echo ""
  3190	  echo "==> (Re)writing install-state (.claude/.install-state.json — PLAN-153 Wave B)"
  3191	  if ! PYTHONNOUSERSITE=1 python3 -I -c '
  3192	import json, os, sys, tempfile, time
  3193	args = sys.argv[1:]
  3194	state_path, ops_path, fw_version = args[0], args[1], args[2]
  3195	n = int(args[3]); kv = args[4:4 + n]; up_argv = list(args[4 + n:])
  3196	vals = {}
  3197	i = 0
  3198	while i + 1 < len(kv):
  3199	    vals[kv[i]] = kv[i + 1]; i += 2
  3200	ops = []
  3201	if ops_path and os.path.isfile(ops_path):
  3202	    try:
  3203	        with open(ops_path, "r", encoding="utf-8", errors="replace") as f:
  3204	            for line in f:
  3205	                line = line.rstrip("\n")
  3206	                if not line:
  3207	                    continue
  3208	                parts = line.split("\t", 1)
  3209	                ops.append({"op": parts[0], "detail": parts[1] if len(parts) > 1 else ""})
  3210	    except OSError:
  3211	        pass
  3212	now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
  3213	prev = None
  3214	try:
  3215	    with open(state_path, "r", encoding="utf-8") as f:
  3216	        prev = json.load(f)
  3217	    if not isinstance(prev, dict):
  3218	        prev = None
  3219	except (OSError, ValueError):
  3220	    prev = None
  3221	first, run_count, history, req = now, 1, [], None
  3222	if prev is not None:
  3223	    v = prev.get("first_recorded_at")
  3224	    if isinstance(v, str) and v:
  3225	        first = v
  3226	    rc = prev.get("run_count")
  3227	    if isinstance(rc, int) and rc > 0:
  3228	        run_count = rc + 1
  3229	    h = prev.get("history")
  3230	    if isinstance(h, list):
  3231	        history = [e for e in h if isinstance(e, dict)][-19:]
  3232	    pr = prev.get("request")
  3233	    if isinstance(pr, dict):
  3234	        req = pr
  3235	    pt = prev.get("tool"); pw = prev.get("written_at")
  3236	    history.append({
  3237	        "at": pw if isinstance(pw, str) else "",
  3238	        "tool": (pt.get("name", "") if isinstance(pt, dict) else ""),
  3239	        "profile": (req.get("profile", "") if isinstance(req, dict) else ""),
  3240	        "stack": (req.get("stack", "") if isinstance(req, dict) else ""),
  3241	    })
  3242	    history = history[-20:]
  3243	if req is None:
  3244	    req = {
  3245	        "argv": [],
  3246	        "target": vals.get("target", ""),
  3247	        "placeholders": {},
  3248	        "note": "synthesized by upgrade.sh - no pre-Wave-B install.sh record existed (back-compat path)",
  3249	    }
  3250	req["profile"] = vals.get("profile", "")
  3251	req["stack"] = vals.get("stack", "")
  3252	# PLAN-155 Wave 5: persist harness so it survives even a pre-Wave-B target
  3253	# whose request was synthesized above. Only overwrite when non-empty so a
  3254	# claude-only upgrade never clobbers a recorded codex harness with "".
  3255	_h = vals.get("harness", "")
  3256	if _h in ("claude", "codex"):
  3257	    req["harness"] = _h
  3258	elif "harness" not in req:
  3259	    req["harness"] = "claude"
  3260	if vals.get("managed_hooks", "0") == "1":
  3261	    req["managed_hooks"] = True
  3262	elif "managed_hooks" not in req:
  3263	    req["managed_hooks"] = False
  3264	state = {
  3265	    "schema": "ceo.install-state/v1",
  3266	    "schema_version": 1,
  3267	    "written_at": now,
  3268	    "first_recorded_at": first,
  3269	    "run_count": run_count,
  3270	    "tool": {"name": "upgrade.sh", "framework_version": fw_version},
  3271	    "request": req,
  3272	    "last_upgrade": {
  3273	        "at": now,
  3274	        "argv": up_argv,
  3275	        "profile": vals.get("profile", ""),
  3276	        "stack": vals.get("stack", ""),
  3277	        "on_conflict": vals.get("on_conflict", ""),
  3278	        "pin": vals.get("pin", ""),
  3279	        "replay_source": vals.get("replay_source", ""),
  3280	        "ceremony_effective": vals.get("ceremony_effective", ""),
  3281	    },
  3282	    "operations": ops,
  3283	    "result": {"upgrade_succeeded": True,
  3284	               "baseline_manifest": ".claude/.install-manifest.sha256"},
  3285	    "history": history,
  3286	    "_comment": "Target-side, UNSIGNED, advisory record (same trust class as the ADR-155 baseline manifest). upgrade.sh replays request.profile/request.stack as DEFAULTS only; explicit flags always win. Not a trust anchor.",
  3287	}
  3288	d = os.path.dirname(state_path) or "."
  3289	if not os.path.isdir(d):
  3290	    sys.exit(3)
  3291	fd, tmp = tempfile.mkstemp(prefix=".install-state.", suffix=".tmp", dir=d)
  3292	try:
  3293	    with os.fdopen(fd, "w", encoding="utf-8") as f:
  3294	        json.dump(state, f, indent=2)
  3295	        f.write("\n")
  3296	    os.replace(tmp, state_path)
  3297	except BaseException:
  3298	    try:
  3299	        os.unlink(tmp)
  3300	    except OSError:
  3301	        pass
  3302	    raise
  3303	' "$_INSTALL_STATE_FILE" "${_UP_OPS_FILE:-}" "$fw_version" "${#pairs[@]}" "${pairs[@]}" \
  3304	    ${ORIG_UP_ARGV[@]+"${ORIG_UP_ARGV[@]}"} 2>/dev/null; then
  3305	    echo "    NOTE: install-state write failed — the next upgrade falls back to the ADR-155 path (fail-open)" >&2
  3306	  else
  3307	    echo "    WROTE: .claude/.install-state.json (schema ceo.install-state/v1, atomic)"
  3308	  fi
  3309	  if [[ -n "${_UP_OPS_FILE:-}" ]]; then rm -f "$_UP_OPS_FILE" 2>/dev/null || true; fi
  3310	  return 0
  3311	}
  3312	# ----------------------------------------------------------------------
  3313	# PLAN-155 Wave 5 — Codex harness refresh (round-trip). When the effective
  3314	# harness (explicit --harness or replayed request.harness) is codex, refresh
  3315	# the .codex/ bundle from the (possibly newer) templates. Collision behavior
  3316	# mirrors the claude upgrade's --on-conflict: refuse (default) leaves a locally
  3317	# changed file, backup/theirs overwrite with a backup. A refusal WARNS, never
  3318	# fails the upgrade (consistent with the ADR-155 default). Runs BEFORE the
  3319	# state rewrite so codex ops are journaled.
  3320	# ----------------------------------------------------------------------
  3321	if [[ "$HARNESS" == "codex" ]]; then
  3322	  # PLAN-161 U1 writer-family audit: this refresh block ignored --dry-run
  3323	  # (codex_emit_bundle writes the .codex/ bundle). Preview + skip.
  3324	  if [[ "$DRY_RUN" -eq 1 ]]; then
  3325	    echo "    (dry-run) would REFRESH: .codex/ harness bundle (--harness codex; on-conflict=$ON_CONFLICT)"
  3326	  elif ! command -v codex_emit_bundle >/dev/null 2>&1; then
  3327	    echo "    NOTE: recorded harness is codex but scripts/_codex_harness.sh is not" >&2
  3328	    echo "          sourced — skipping the .codex/ refresh (fail-open)." >&2
  3329	  else
  3330	    # shellcheck disable=SC2034  # PH_PROJECT_*/CODEX_FORCE consumed by the sourced _codex_harness.sh
  3331	    PH_PROJECT_PATH="$TARGET"
  3332	    # shellcheck disable=SC2034
  3333	    PH_PROJECT_NAME="$( basename "$TARGET" )"
  3334	    # shellcheck disable=SC2034
  3335	    if [[ "$ON_CONFLICT" == "theirs" || "$ON_CONFLICT" == "backup" ]]; then
  3336	      CODEX_FORCE=1
  3337	    else
  3338	      CODEX_FORCE=0
  3339	    fi
  3340	    echo ""
  3341	    echo "==> Codex harness refresh (--harness codex; on-conflict=$ON_CONFLICT)"
  3342	    if codex_emit_bundle; then :; else
  3343	      _cx_rc=$?
  3344	      echo "    NOTE: codex bundle refresh returned rc=$_cx_rc (likely a local edit under" >&2
  3345	      echo "          the default refuse policy). Re-run with --on-conflict backup to" >&2
  2440	}
  2441	
  2442	
  2443	# ----------------------------------------------------------------------
  2444	# PLAN-153 Wave B item B1 — persist the install-state.
  2445	# ----------------------------------------------------------------------
  2446	# Writes $TARGET/.claude/.install-state.json (next to the ADR-155 baseline
  2447	# manifest): the ORIGINAL request — verbatim argv + every parsed flag + the
  2448	# RESOLVED placeholder map (CLI > env > deterministic default; empty values
  2449	# omitted) — plus the operation journal for THIS run.
  2450	#
  2451	#   * Atomic: python writes a same-directory tempfile, then os.replace().
  2452	#   * Updated on every run: first_recorded_at + run_count + a bounded
  2453	#     history (last 20 runs) survive re-installs; request/operations
  2454	#     reflect the LATEST run.
  2455	#   * Schema-versioned: schema ceo.install-state/v1, schema_version 1.
  2456	#   * Consumed by upgrade.sh (PLAN-153 B2): request.profile/request.stack
  2457	#     become upgrade DEFAULTS when its own flags are omitted. A missing or
  2458	#     invalid state file degrades upgrade.sh to the ADR-155 drift-classifier
  2459	#     path — never an error, never a no-op (debate C back-compat must-fix).
  2460	#   * TRUST: target-side, UNSIGNED, advisory — the same trust class as the
  2461	#     ADR-155 baseline manifest (whoever can write the target tree can
  2462	#     rewrite it). upgrade.sh charset-validates every replayed value and
  2463	#     falls back on anything suspect; values are data, never eval-ed.
  2464	#   * Fail-open: no python3 / write error => stderr NOTE, install still
  2465	#     succeeds. Dry-run never writes (the "no files modified" promise).
  2466	#   * NOT covered by the baseline-manifest enumeration (like the manifest
  2467	#     dotfile itself), so the upgrade classifier never touches it.
  2468	_write_install_state() {
  2469	  [[ "${DRY_RUN:-0}" -eq 0 ]] || return 0
  2470	  if ! command -v python3 >/dev/null 2>&1; then
  2471	    echo "    NOTE: install-state skipped (python3 not found) — upgrade.sh will use the ADR-155 fallback path" >&2
  2472	    return 0
  2473	  fi
  2474	  local state_file="$TARGET/.claude/.install-state.json"
  2475	  local fw_version=""
  2476	  if [[ -f "$SOURCE_DIR/VERSION" ]]; then
  2477	    fw_version="$(tr -d '[:space:]' < "$SOURCE_DIR/VERSION" 2>/dev/null || true)"
  2478	  fi
  2479	
  2480	  echo ""
  2481	  echo "==> Writing install-state (.claude/.install-state.json — PLAN-153 Wave B)"
  2482	
  2483	  # Flat key/value pairs, argv-passed (PLAN-106 G.2.b house pattern: never
  2484	  # source-string interpolation; python3 -I + PYTHONNOUSERSITE=1). Keys with
  2485	  # a "ph." prefix land in request.placeholders; empty ph values are omitted.
  2486	  local pairs=(
  2487	    "target" "$TARGET"
  2488	    "mode" "$MODE"
  2489	    "profile" "$PROFILE"
  2490	    "stack" "$STACK"
  2491	    "stack_explicit" "$STACK_EXPLICIT"
  2492	    "ceremony" "$CEREMONY"
  2493	    "github_owner" "$GITHUB_OWNER"
  2494	    "with_reference_personas" "$WITH_REFERENCE_PERSONAS"
  2495	    "strict_placeholders" "$STRICT_PLACEHOLDERS"
  2496	    "verify" "$VERIFY"
  2497	    "harness" "$HARNESS"
  2498	    "managed_hooks" "$CODEX_MANAGED_HOOKS"
  2499	    "ph.OWNER_NAME" "$PH_OWNER_NAME"
  2500	    "ph.PROJECT_NAME" "$PH_PROJECT_NAME"
  2501	    "ph.PROJECT_PATH" "$PH_PROJECT_PATH"
  2502	    "ph.STACK" "$PH_STACK"
  2503	    "ph.PROTOCOL_SOURCE" "$PH_PROTOCOL_SOURCE"
  2504	    "ph.DEPLOY_COMMAND" "$PH_DEPLOY_COMMAND"
  2505	    "ph.DEPLOY_PLATFORM" "$PH_DEPLOY_PLATFORM"
  2506	    "ph.DEPLOY_TARGET" "$PH_DEPLOY_TARGET"
  2507	    "ph.RUNTIME_NOTES" "$PH_RUNTIME_NOTES"
  2508	    "ph.DATABASE" "$PH_DATABASE"
  2509	    "ph.N_BACKEND" "$PH_N_BACKEND"
  2510	    "ph.N_FRONTEND" "$PH_N_FRONTEND"
  2511	    "ph.FRONTEND_STACK" "$PH_FRONTEND_STACK"
  2512	    "ph.FRONTEND_PATH" "$PH_FRONTEND_PATH"
  2513	    "ph.FRONTEND_REPO_PATH" "$PH_FRONTEND_REPO_PATH"
  2514	    "ph.UI_LIBRARY" "$PH_UI_LIBRARY"
  2515	    "ph.STATE_MANAGEMENT" "$PH_STATE_MANAGEMENT"
  2516	    "ph.REALTIME_TRANSPORT" "$PH_REALTIME_TRANSPORT"
  2517	    "ph.CHARTING_LIBRARY" "$PH_CHARTING_LIBRARY"
  2518	    "ph.AUTH_PROVIDER" "$PH_AUTH_PROVIDER"
  2519	    "ph.I18N_FRAMEWORK" "$PH_I18N_FRAMEWORK"
  2520	    "ph.TEST_FRAMEWORK" "$PH_TEST_FRAMEWORK"
  2521	    "ph.TEST_TOOL" "$PH_TEST_TOOL"
  2522	    "ph.TEST_COUNT" "$PH_TEST_COUNT"
  2523	    "ph.LINT_TOOL" "$PH_LINT_TOOL"
  2524	    "ph.CI_TOOL" "$PH_CI_TOOL"
  2525	    "ph.APP_NAME" "$PH_APP_NAME"
  2526	    "ph.SOURCE_FILE_COUNT" "$PH_SOURCE_FILE_COUNT"
  2527	    "ph.LINE_COUNT" "$PH_LINE_COUNT"
  2528	    "ph.LINES" "$PH_LINES"
  2529	    "ph.FILE_COUNT" "$PH_FILE_COUNT"
  2530	    "ph.PAGE_COUNT" "$PH_PAGE_COUNT"
  2531	    "ph.COMPONENT_COUNT" "$PH_COMPONENT_COUNT"
  2532	    "ph.HOOK_COUNT" "$PH_HOOK_COUNT"
  2533	    "ph.BUNDLE_SIZE" "$PH_BUNDLE_SIZE"
  2534	    "ph.CITY" "$PH_CITY"
  2535	    "ph.COUNTRY" "$PH_COUNTRY"
  2536	    "ph.DOMAIN" "$PH_DOMAIN"
  2537	    "ph.FOUNDER_NAME" "$PH_FOUNDER_NAME"
  2538	    "ph.LEGAL_ID" "$PH_LEGAL_ID"
  2539	    "ph.PRODUCTION_URL" "$PH_PRODUCTION_URL"
  2540	  )
  2541	
  2542	  if ! PYTHONNOUSERSITE=1 python3 -I -c '
  2543	import json, os, sys, tempfile, time
  2544	args = sys.argv[1:]
  2545	state_path, ops_path, fw_version = args[0], args[1], args[2]
  2546	n = int(args[3]); kv = args[4:4 + n]; orig_argv = list(args[4 + n:])
  2547	vals = {}; ph = {}
  2548	i = 0
  2549	while i + 1 < len(kv):
  2550	    k, v = kv[i], kv[i + 1]
  2551	    if k.startswith("ph."):
  2552	        if v != "":
  2553	            ph[k[3:]] = v
  2554	    else:
  2555	        vals[k] = v
  2556	    i += 2
  2557	ops = []
  2558	if ops_path and os.path.isfile(ops_path):
  2559	    try:
  2560	        with open(ops_path, "r", encoding="utf-8", errors="replace") as f:
  2561	            for line in f:
  2562	                line = line.rstrip("\n")
  2563	                if not line:
  2564	                    continue
  2565	                parts = line.split("\t", 1)
  2566	                ops.append({"op": parts[0], "detail": parts[1] if len(parts) > 1 else ""})
  2567	    except OSError:
  2568	        pass
  2569	now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
  2570	prev = None
  2571	try:
  2572	    with open(state_path, "r", encoding="utf-8") as f:
  2573	        prev = json.load(f)
  2574	    if not isinstance(prev, dict):
  2575	        prev = None
  2576	except (OSError, ValueError):
  2577	    prev = None
  2578	first, run_count, history = now, 1, []
  2579	if prev is not None:
  2580	    v = prev.get("first_recorded_at")
  2581	    if isinstance(v, str) and v:
  2582	        first = v
  2583	    rc = prev.get("run_count")
  2584	    if isinstance(rc, int) and rc > 0:
  2585	        run_count = rc + 1
  2586	    h = prev.get("history")
  2587	    if isinstance(h, list):
  2588	        history = [e for e in h if isinstance(e, dict)][-19:]
  2589	    pr = prev.get("request"); pt = prev.get("tool"); pw = prev.get("written_at")
  2590	    history.append({
  2591	        "at": pw if isinstance(pw, str) else "",
  2592	        "tool": (pt.get("name", "") if isinstance(pt, dict) else ""),
  2593	        "profile": (pr.get("profile", "") if isinstance(pr, dict) else ""),
  2594	        "stack": (pr.get("stack", "") if isinstance(pr, dict) else ""),
  2595	    })
  2596	    history = history[-20:]
  2597	    # Placeholder map is a UNION across runs: install.sh is EXISTS-SKIP
  2598	    # idempotent and never un-substitutes, so a value recorded by an earlier
  2599	    # run remains in effect on disk even when a later run omits the flag.
  2600	    # New non-empty values override recorded ones.
  2601	    if isinstance(pr, dict):
  2602	        oph = pr.get("placeholders")
  2603	        if isinstance(oph, dict):
  2604	            merged = {}
  2605	            for k in oph:
  2606	                if isinstance(k, str) and isinstance(oph[k], str):
  2607	                    merged[k] = oph[k]
  2608	            merged.update(ph)
  2609	            ph = merged
  2610	req = {
  2611	    "argv": orig_argv,
  2612	    "target": vals.get("target", ""),
  2613	    "mode": vals.get("mode", ""),
  2614	    "profile": vals.get("profile", ""),
  2615	    "stack": vals.get("stack", ""),
  2616	    "stack_explicit": vals.get("stack_explicit", "0") == "1",
  2617	    "ceremony": vals.get("ceremony", ""),
  2618	    "github_owner": vals.get("github_owner", ""),
  2619	    "with_reference_personas": vals.get("with_reference_personas", "0") == "1",
  2620	    "strict_placeholders": vals.get("strict_placeholders", "0") == "1",
  2621	    "verify": vals.get("verify", "0") == "1",
  2622	    # PLAN-155 Wave 5: recorded so upgrade.sh replays the harness (B2 mirror).
  2623	    "harness": vals.get("harness", "claude"),
  2624	    "managed_hooks": vals.get("managed_hooks", "0") == "1",
  2625	    "placeholders": ph,
  2626	}
  2627	state = {
  2628	    "schema": "ceo.install-state/v1",
  2629	    "schema_version": 1,
  2630	    "written_at": now,
  2631	    "first_recorded_at": first,
  2632	    "run_count": run_count,
  2633	    "tool": {"name": "install.sh", "framework_version": fw_version},
  2634	    "request": req,
  2635	    "operations": ops,
  2636	    "result": {"install_succeeded": True,
  2637	               "baseline_manifest": ".claude/.install-manifest.sha256"},
  2638	    "history": history,
  2639	    "_comment": "Target-side, UNSIGNED, advisory record (same trust class as the ADR-155 baseline manifest). upgrade.sh replays request.profile/request.stack as DEFAULTS only; explicit flags always win. Not a trust anchor.",
  2640	}
  2641	d = os.path.dirname(state_path) or "."
  2642	if not os.path.isdir(d):
  2643	    sys.exit(3)
  2644	fd, tmp = tempfile.mkstemp(prefix=".install-state.", suffix=".tmp", dir=d)
  2645	try:
  2646	    with os.fdopen(fd, "w", encoding="utf-8") as f:
  2647	        json.dump(state, f, indent=2)
  2648	        f.write("\n")
  2649	    os.replace(tmp, state_path)
  2650	except BaseException:
  2651	    try:
  2652	        os.unlink(tmp)
  2653	    except OSError:
  2654	        pass
  2655	    raise
  2656	' "$state_file" "${_STATE_OPS_FILE:-}" "$fw_version" "${#pairs[@]}" "${pairs[@]}" \
  2657	    ${ORIG_ARGV[@]+"${ORIG_ARGV[@]}"} 2>/dev/null; then
  2658	    echo "    NOTE: install-state write failed — upgrade.sh will use the ADR-155 fallback path (fail-open)" >&2
  2659	    return 0
  2660	  fi
  2661	  echo "    WROTE: .claude/.install-state.json (schema ceo.install-state/v1, atomic)"
  2662	  return 0
  2663	}
  2664	
  2665	# ----------------------------------------------------------------------
  2666	# PLAN-155 Wave 5 — Codex harness emission. Runs AFTER the claude install
  2667	# completes (so the .claude/ hooks the .codex/ registration points at are in
  2668	# place) and BEFORE the state/manifest are written (so codex ops are journaled
  2669	# into .claude/.install-state.json). Fully gated on --harness codex; the
  2670	# default claude path never enters this block. Honors --dry-run internally.
  2671	# ----------------------------------------------------------------------
  2672	if [[ "$HARNESS" == "codex" ]]; then
  2673	  if ! command -v codex_emit_bundle >/dev/null 2>&1; then
  2674	    echo "ERROR: --harness codex requires scripts/_codex_harness.sh (not sourced)" >&2
  2675	    exit 1
  2676	  fi
  2677	  if codex_emit_bundle; then :; else
  2678	    _cx_rc=$?
  2679	    echo "ERROR: codex harness emission failed/refused (rc=$_cx_rc)" >&2
  2680	    exit "$_cx_rc"

exec
/bin/zsh -lc "grep -n \"pristine\\|takeover\\|marker\\|protocol\" docs/ownership-decision-table.md | sed -n '1,260p'; sed -n '200,340p' docs/ownership-decision-table.md" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
18:>    the proposal is a `live_content` of `legacy_pristine_partial`, meaning a
29:and the `.claude/.framework-version` marker — derives from the **registered
69:| `protocol` | root `PROTOCOL.md` | a **generated pointer** — no source file; the body is a heredoc built from `$SOURCE_DIR`/`$TARGET`/`$PROFILE`/`$STACK` |
70:| `marker` | `.claude/.framework-version` | a tracked single-line file |
75:`protocol` is the only surface with no bytes in the source (so `source_has`
77:canonical hash); `marker` is the only surface inside `.claude/`, so it is
117:| `pristine` | byte-identical to what **this** source would deliver |
118:| `legacy_pristine` | matches a `SPEC/v1` fingerprint the framework shipped at v1.2.0 or earlier |
121:`legacy_pristine` exists because v1.2-and-earlier installs never enumerated
129:a pre-v1.3.0 tag, whose checkout has no marker. A `SPEC/v1` absent from
259:| **R-03** | `surface=protocol` ⇒ `source_has=yes` | The pointer is generated from a heredoc, never copied. There is no source file whose absence could be observed. |
260:| **R-04** | `live_content=legacy_pristine` ⇒ `surface=spec` | The pristine fingerprints are a `SPEC/v1`-tree construct. No equivalent exists, or is needed, for a one-line marker or a generated pointer. |
264:| **R-08** | `ceremony=user` ⇒ `surface ∈ {spec, protocol}` cannot yield `DELIVER` or `REFRESH` | WS4 guards forbid root surfaces under a user ceremony. **This prunes verdicts, not cells:** those surfaces still legally *appear* under `ceremony=user` as residue of a prior maintainer install, and those residue cells are exactly where two defects lived. |
267:| **R-11** | `live_type=ancestor_symlink` ⇒ `surface ∈ {spec, marker}` | `PROTOCOL.md` sits at the target root, so between `$TARGET` and the leaf there is **no intermediate component** that could be a symlink. The guard is vacuous there, not missing. |
303:- **REJECTED: `surface=protocol ⇒ live_type ∈ {absent, regular, symlink}`.**
304:  Nothing in `_refresh_protocol_pointer` prevents a directory or a FIFO at
306:  the leaf-symlink guard that `spec` and `marker` both acquired during the
315:### 5.1 The `protocol` surface is the family's late sibling
317:`spec` and `marker` each acquired, over the review rounds, three guards: a
320:regular file. `protocol` acquired **none of them** — and it is the one
351:`protocol` surface as a leaf symlink — reports `ESCAPE`: `cat >` follows
399:### 5.3 Deliberate asymmetry: the marker under `--pin`
401:Where a pinned pre-v1.3.0 source has no marker, the record is **dropped**
431:so this is matched against a small declared set of operator-visible markers.
465:never reaches the SPEC or marker route at all: an earlier stage —
471:whose only anomaly is a FIFO at the marker path, hangs indefinitely; the same
492:The symlinked-ancestor guard on `spec` and `marker` ends with a line that
528:  Dropping the marker record makes readers fall back to a `VERSION` the
549:  `legacy_pristine_partial` a real `live_content` value. Both were prose
572:  One defect was a *reader* trusting a delivered-then-edited marker and
| `hash_source` | Meaning |
|---|---|
| `HASH_TARGET` | hash the bytes now on disk at the target |
| `HASH_SOURCE` | hash the framework's copy in `$SOURCE_DIR` |
| `HASH_PRIOR_RECORD` | carry the digest the previous manifest recorded |
| `HASH_CANONICAL_POINTER` | the computed hash of what the pointer heredoc *would* generate |
| `HASH_NONE` | emit no record |
| `LINK_RECORD` | emit `LINK  <relpath>  <target>` instead of a digest |

The two fields are **orthogonal**. `PRESERVE_OWNED` with `HASH_TARGET`
records the adopter's edited bytes as the framework baseline — which is how
a later upgrade comes to overwrite them and `uninstall.sh` comes to delete
them. `PRESERVE_OWNED` with `HASH_PRIOR_RECORD` is the safe reading of the
same intent. Nothing in the branch structure made that choice visible; a
column does.

### 3.3 What this replaces

`FMS_HASH_ROOT_PATHS` and `FMS_LINK_PATHS` are per-path override lists added
during the eleven rounds to narrow two global switches that turned out to be
too wide. They are **special cases of an explicit `hash_source`**, and the
implementation replaces them — it does not keep them alongside it. Adding a
third override list is the failure mode this table exists to prevent.

`FMS_PROTOCOL_HASH` carries **two different meanings** today: the canonical
pointer hash on the upgrade path, and a *prior record digest* on the install
continuity path. Under this model those are `HASH_CANONICAL_POINTER` and
`HASH_PRIOR_RECORD` — distinct values that must not share a channel. See
OQ-4.

### 3.4 `HASH_TARGET` is the default, and it is never distinctly correct

Filling the table surfaced something no single branch could show: across all
61 rows, **`HASH_TARGET` is never the right answer.** It appears only as an
`indistinguishable=` annotation on rows where the target was just written
from the framework's own bytes, so the two candidates are equal by
construction and the distinction is unobservable.

Yet `HASH_TARGET` is precisely what the generator falls back to when no
override is supplied. So the default is right only by coincidence — whenever
target and source agree — and wrong in exactly the situation the override
exists to handle: a preserved adopter edit. Three separate P1 defects are
instances of that one sentence.

This is an argument for making `hash_source` an explicit, required parameter
of the verdict rather than a set of opt-in overrides on a permissive default.
Recorded as evidence for the W1 debate, not decided here.

## 4. Legality rules (pruning)

A cell is **illegal** when the combination cannot occur against a real
target. Every rule below removes cells; **each is named with its reason, and
silent pruning is forbidden** — an unexplained absence from the TSV is
indistinguishable from an oversight, which is how a defect class hides.

| Rule | Statement | Reason |
|---|---|---|
| **R-01** | `operation=install_fresh` ⇒ `prior_record=none` | The manifest is written at the *end* of install. "Fresh" is defined as "no pre-existing manifest", so there is no prior testimony to read. |
| **R-02** | `operation ∈ {install_fresh, install_rerun}` ⇒ `skip_requested=none` | `--skip` is an `upgrade.sh` flag. `install.sh` has no equivalent (verified: zero occurrences). |
| **R-03** | `surface=protocol` ⇒ `source_has=yes` | The pointer is generated from a heredoc, never copied. There is no source file whose absence could be observed. |
| **R-04** | `live_content=legacy_pristine` ⇒ `surface=spec` | The pristine fingerprints are a `SPEC/v1`-tree construct. No equivalent exists, or is needed, for a one-line marker or a generated pointer. |
| **R-05** | `live_type=absent` ⇒ `live_content` undefined | Nothing to hash. |
| **R-06** | `skip_requested=descendant` ⇒ `surface=spec` | Only `SPEC/v1` is a tree. A path *under* a single file cannot exist. |
| **R-07** | `live_type=dir_empty` ⇒ `surface=spec` | For the single-file surfaces, an empty directory and a non-empty one behave identically (both yield no record and both are refused as non-regular). The distinction is only load-bearing where per-file records are emitted. |
| **R-08** | `ceremony=user` ⇒ `surface ∈ {spec, protocol}` cannot yield `DELIVER` or `REFRESH` | WS4 guards forbid root surfaces under a user ceremony. **This prunes verdicts, not cells:** those surfaces still legally *appear* under `ceremony=user` as residue of a prior maintainer install, and those residue cells are exactly where two defects lived. |
| **R-09** | `prior_record ∈ {link_match, link_retargeted}` ∧ `live_type ≠ symlink` ⇒ collapse to `link_retargeted` | `readlink` on a non-symlink yields empty, which never equals a recorded non-empty target. Keeping both would be two names for one observable state. |
| **R-10** | Rows are **equivalence classes**, not raw tuples; a dimension the row's outcome does not depend on is written `*` | Forced, not preferred. The raw product is ~24,000 tuples; at the mandated per-cell timeout the suite could not run in a day, so it would not be run — and an unrun suite is worse than a smaller honest one. `*` is the harness's instruction to instantiate the canonical representative, and any dimension that turns out to matter must be split into explicit rows. |
| **R-11** | `live_type=ancestor_symlink` ⇒ `surface ∈ {spec, marker}` | `PROTOCOL.md` sits at the target root, so between `$TARGET` and the leaf there is **no intermediate component** that could be a symlink. The guard is vacuous there, not missing. |

### 4.2 Conventions carried in the TSV

- `*` — don't-care, per R-10.
- `-` — not applicable under a rule above (e.g. `live_content` when the
  target is absent).
- `note` may carry structured directives alongside prose:
  `fault=<enum>` (an injected environmental failure),
  `indistinguishable=<enum>` (two `hash_source` candidates that are equal by
  construction on this row — the harness reports `AMBIG`, never a lucky
  green), `invariant=<id>`, `open=<round-id>` (a defect this row asserts and
  the current tree does not yet satisfy).

### 4.1 Three draft rules, REJECTED with reason

PLAN-167 §W0.1 offered five pruning rules as "already known". Three of them
are wrong, and adopting them would have deleted cells that hold real
defects. Recording the rejections here so they are not re-proposed.

- **REJECTED: `operation=install_fresh ⇒ live_type=absent`.**
  A maintainer install onto a target that already carries its own `SPEC/v1`
  is precisely the case ADR-155-AMEND-1 §3 cites for why ceremony-conditional
  enumeration is insufficient. `install_one` EXISTS-skips it, and the
  question of whether the adopter's tree gets inventoried as framework-owned
  is the whole point. The cell is legal and important.

- **REJECTED: `prior_record=link_* ⇒ mode=link`.**
  `prior_record` describes the previous run; `mode` describes this one. They
  are independent. `mode=link ∧ prior_record=hash` is an open, unfixed defect
  — a `--link` rerun over a copy-installed surface that has since been
  replaced by a symlink, where the absence of a `LINK` row is read as "no
  mismatch" and an arbitrary live symlink is recorded as a trusted delivery.
  `mode=copy ∧ prior_record=link` is a legal re-run after a mode change.
  Pruning either would delete the finding the table exists to hold.

- **REJECTED: `surface=protocol ⇒ live_type ∈ {absent, regular, symlink}`.**
  Nothing in `_refresh_protocol_pointer` prevents a directory or a FIFO at
  `$TARGET/PROTOCOL.md`. It has neither the non-regular-destination guard nor
  the leaf-symlink guard that `spec` and `marker` both acquired during the
  review rounds — see §5.1. The cell is not illegal; it is **unguarded**, and
  those are opposite things. Pruning it would have converted a live defect
  into an invisible one.

## 5. Cells whose pair is not obvious

Only the reasoning lives here; the pairs themselves are in the TSV.

### 5.1 The `protocol` surface is the family's late sibling

`spec` and `marker` each acquired, over the review rounds, three guards: a
symlinked-ancestor refusal, a leaf-symlink check validated against the prior
`LINK` record, and a refusal of any destination that exists but is not a
regular file. `protocol` acquired **none of them** — and it is the one
surface written with `cat >`, which follows a leaf symlink out of the target
tree, fails hard on a directory (aborting the whole run under
`set -euo pipefail`, mid-upgrade, after other surfaces have changed), and
blocks forever on a FIFO.

Two of those three are real gaps. The third is not: R-11 shows the
ancestor guard is **vacuous** for a root-level leaf, so its absence is
correct rather than missing. That correction is itself the point — the same
sweep that found the gaps also stopped a plausible-looking third "gap" from
being patched into existence.

None of this came from the eleven rounds. It came from asking the question
the table forces: *the same cell, on each surface, must have a declared
answer.* Per PLAN-167 §6 rule 2 it is recorded as rows, not patched
branch-locally.

### 5.4b The instrument was blind to the damage it was built to detect

The first version of this harness compared only the target tree. For the
rows where a surface is a symlink, that is not enough: a write that follows

exec
/bin/zsh -lc "sed -n '390,420p' docs/ownership-decision-table.md; sed -n '510,540p' docs/ownership-decision-table.md; sed -n '240,290p' .claude/plans/PLAN-167/debate/round-1/security-engineer.md" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
### 5.2 Ownership continuity and the digest it carries

Carrying ownership forward across a run that did not write anything is
correct — dropping the record strands a delivered tree as unowned forever.
But the flag and the digest are separate decisions, and four separate
defects came from moving one without the other. A `PRESERVE_OWNED` verdict
therefore always has an explicitly declared `hash_source`, and
`HASH_TARGET` is never its default.

### 5.3 Deliberate asymmetry: the marker under `--pin`

Where a pinned pre-v1.3.0 source has no marker, the record is **dropped**
rather than carried forward, so that readers fall back to `VERSION` — which
the pin did update. This is the one place where `OMIT_RECORD` is chosen over
`PRESERVE_OWNED` on purpose, and it is recorded here so it is not "fixed"
into consistency with the other surfaces.

Its residual is real and is open as OQ-3: `VERSION` in an *external* target
is adopter-owned and never written by the upgrade, so the fallback can still
report a version newer than the content.

### 5.4 The root `VERSION` file is not a surface

It is out of the enumeration and out of the upgrade, permanently and
deliberately (ADR-155-AMEND-1 §2). It is named here only so that its absence
from the table is not read as an omission.

### 5.6 One amendment to the plan's observation contract, and why

PLAN-167 §W0.3 drafted the observation contract so that `ABORT_SURFACE` was
recognised by *"target unchanged + named warning + rc 0, and **no record**"*.

## 6. Open questions — the W1 debate agenda

These are the points where the three input authorities — the eleven review
verdicts, the live branch, and ADR-155/AMEND-1 — do **not** agree. PLAN-167
§W0.1 requires that they be recorded rather than resolved unilaterally.

- **OQ-1 — Is `ABORT_SURFACE` one verdict or two?**
  A failed backup and an unsupported special file both leave the target
  untouched with a named warning, but they differ in whether the framework
  *could* have proceeded. If the manifest outcome is identical, the enum
  should merge them; if the operator's next action differs, it should not.

- **OQ-2 — What is the `hash_source` of `ABORT_SURFACE` when a prior record
  exists?** Refusing to touch a surface is not evidence about ownership. The
  live code answers this differently on different branches.

- **OQ-3 — Version reporting under an external-target `--pin` downgrade.**
  Dropping the marker record makes readers fall back to a `VERSION` the
  upgrade never writes on an external target. A truthful signal requires
  deriving from the pinned source; that is a new mechanism, not a cell.

- **OQ-4 — Splitting `FMS_PROTOCOL_HASH`.** It carries
  `HASH_CANONICAL_POINTER` on one path and `HASH_PRIOR_RECORD` on another.
  Splitting is the model-faithful move; it also changes a canonical-guarded
  signature.

- **OQ-5 — Where does `_ownership_verdict()` live?**
  A new library file is a new canonical path, which requires a
  `_CANONICAL_GUARDS` entry and therefore a kernel ceremony. PLAN-167 §4
  states a preference for the already-guarded
   security-sound); the manifest still never nominates a deletion (the
   PLAN-161 amendment constraint stays intact); the fail direction on a
   MISSING record remains preserve/fallback. The one adjacent item is
   R-SEC7 (accepted-risk broadening), which is a documentation
   obligation, not an escalation.
8. `FMS_PROTOCOL_HASH` dual meaning confirmed on disk (supports OQ-4):
   `install.sh:2398` exports a PRIOR-RECORD digest
   (`_PRIOR_PROTOCOL_HASH`), `upgrade.sh:3082` exports the CANONICAL
   pointer hash (`_REFRESH_PROTOCOL_CANON_HASH`) — two semantics, one
   channel. Splitting into `HASH_PRIOR_RECORD` /
   `HASH_CANONICAL_POINTER` is the model-faithful move.

## What I would NOT change

1. The pair (verdict, hash_source) as the cell outcome. The example in
   §3.2 — `PRESERVE_OWNED` + `HASH_TARGET` records adopter bytes as the
   framework baseline, so a later upgrade clobbers and uninstall deletes
   — is the delete-class mechanism stated as a column choice. Keep it
   orthogonal.
2. The fail-direction discipline already in the TSV. Every expected
   `OMIT_RECORD`/`PRESERVE_UNOWNED` pair is the under-claim direction;
   the open rows OWN-0052/0053 correctly pin the live OVER-claim of
   today (an arbitrary live symlink recorded as a trusted LINK delivery)
   to the fail-safe answer. Do not fix those rows toward the live
   behavior.
3. The §5.8 deletion decision (with the regression-pin rows) — see
   Unseen 6.
4. The OQ-5 home preference (`_framework_manifest_set.sh`, already
   canonical-guarded) and the rule that a veto escalates to the Owner
   rather than becoming an overnight kernel ceremony.
5. R-08 pruning verdicts, not cells — the user-ceremony residue cells
   are where two real defects lived; keeping them in the space is
   correct.
6. The purity of `_ownership_verdict()` — no filesystem access keeps
   observation at the trust boundary in ONE place (the callers) and
   makes the decision auditable and cheaply exhaustively testable.
7. Committing the two inconsistencies openly instead of resolving them
   unilaterally — that is what the debate is for, and pre-deciding them
   in code is how contradictory branches were born in the first place.

exec
/bin/zsh -lc "grep -R \"OQ-3\\|OWN-0052\\|external-target\" -n .claude/plans/PLAN-167 | head -200" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
.claude/plans/PLAN-167/debate/round-1/security-engineer.md:261:   the open rows OWN-0052/0053 correctly pin the live OVER-claim of
.claude/plans/PLAN-167/debate/round-1/proposal.md:139:`OQ-3` version reporting under an external-target `--pin` downgrade ·

exec
/bin/zsh -lc "nl -ba scripts/tests/test-ownership-table.sh | sed -n '170,240p;390,430p'" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
   170	  if [[ -n "$rows" ]]; then
   171	    printf 'hash:%s' "$( printf '%s\n' "$rows" | LC_ALL=C sort | _hash_stdin )"
   172	    return 0
   173	  fi
   174	  printf ''
   175	}
   176	
   177	# Refusal markers — the operator-visible contract of ABORT_SURFACE. Matching
   178	# output is a deliberate choice, recorded in docs §6 (OQ-1/OQ-2): a refusal is
   179	# defined by the framework having ATTEMPTED and declined, which leaves no
   180	# filesystem trace at all. If this wording changes, this test fails loudly —
   181	# which is correct, because the operator-visible contract changed.
   182	# Only GENUINE execution failures. Refusing to act on an unsupported
   183	# destination is a DECISION (the surface is adopter-owned), not a failed
   184	# attempt — conflating them made the e2e and the decision function disagree
   185	# about the same cell (round-1 consensus C2).
   186	_ABORT_MARKERS='REFUSING to|could not back up|backup-before-replace'
   187	
   188	# =============================================================================
   189	# Fixtures
   190	#
   191	# Every row runs at the SAME target path ($T). That is load-bearing, not
   192	# convenience: the root PROTOCOL.md pointer body embeds the target path, so a
   193	# base tree captured at one path and restored at another would carry a stale
   194	# canonical pointer digest and silently corrupt every protocol row.
   195	# =============================================================================
   196	BASE_DIR="$WORK/base"; mkdir -p "$BASE_DIR"
   197	CANON_POINTER_HASH=""       # captured from a real install at $T (never recomputed)
   198	
   199	_base_tar() {  # $1 = ceremony, $2 = base mode(copy|link) -> path to tarball
   200	  local ceremony="$1" bmode="$2"
   201	  local tarball="$BASE_DIR/$ceremony-$bmode.tar"
   202	  [[ -f "$tarball" ]] && { printf '%s' "$tarball"; return 0; }
   203	
   204	  rm -rf "$T"; mkdir -p "$T"
   205	  local args=( "$T" --ceremony "$ceremony" )
   206	  [[ "$bmode" == "link" ]] && args+=( --link )
   207	  if ! _run_with_timeout 300 "$REPO_ROOT/scripts/install.sh" "${args[@]}" \
   208	        > "$BASE_DIR/$ceremony-$bmode.install.log" 2>&1; then
   209	    echo "ERROR: base install failed ($ceremony/$bmode) — see $BASE_DIR/$ceremony-$bmode.install.log" >&2
   210	    return 1
   211	  fi
   212	  # The canonical pointer digest for THIS target path, taken from the file the
   213	  # real installer just generated (never reproduced by duplicating the heredoc,
   214	  # which would be an oracle that passes when both sides are wrong together).
   215	  if [[ -z "$CANON_POINTER_HASH" && -f "$T/PROTOCOL.md" ]]; then
   216	    CANON_POINTER_HASH="$( _hash_file "$T/PROTOCOL.md" 2>/dev/null || true )"
   217	  fi
   218	  ( cd "$T" && tar -cf "$tarball" . ) || return 1
   219	  rm -rf "$T"
   220	  printf '%s' "$tarball"
   221	}
   222	
   223	# A source checkout that LACKS a surface — what `--pin <pre-v1.3 tag>` yields.
   224	_alt_source() {  # $1 = surface -> path to a source tree without it
   225	  local surface="$1"
   226	  local alt="$WORK/src-no-$surface"
   227	  [[ -d "$alt" ]] && { printf '%s' "$alt"; return 0; }
   228	  _clone_source "$alt" || return 1
   229	  local rel; rel="$( _relpath_for "$surface" )"
   230	  rm -rf "${alt:?}/$rel"
   231	  printf '%s' "$alt"
   232	}
   233	
   234	_clone_source() {  # $1 = destination
   235	  mkdir -p "$1"
   236	  ( cd "$REPO_ROOT" && tar -cf - --exclude='./.git' --exclude='./node_modules' . ) \
   237	    | ( cd "$1" && tar -xf - )
   238	}
   239	
   240	# The NEXT version of the framework — a source whose surfaces differ from the
   390	  if [[ "$bd" != "$ad" ]]; then
   391	    if [[ "$bd" == "absent" ]]; then printf 'DELIVER'; else printf 'REFRESH'; fi
   392	    return 0
   393	  fi
   394	  # Unchanged target from here on.
   395	  if grep -Eq "$_ABORT_MARKERS" "$out" 2>/dev/null; then printf 'ABORT_SURFACE'; return 0; fi
   396	  # A REFRESH that writes byte-identical content leaves the CONTENT unchanged,
   397	  # so a content digest alone cannot separate it from a PRESERVE.
   398	  #
   399	  # Backup presence does not settle it either: the ADOPTER-FORK preserve path
   400	  # also snapshots into BAK_DIR, so "a backup exists" is evidence the framework
   401	  # looked, not that it wrote.
   402	  #
   403	  # Modification time settles it on the UPGRADE path, from state and without
   404	  # reading prose: the forced route replaces content with `cp -R` (no -p),
   405	  # which stamps new mtimes, while every preserve path leaves bytes AND
   406	  # timestamps alone.
   407	  #
   408	  # Restricted to upgrade deliberately. install.sh re-runs placeholder
   409	  # SUBSTITUTION on every invocation, so it rewrites the pointer with identical
   410	  # bytes and a fresh mtime — a write with no semantic content. Counting that
   411	  # as REFRESH would report an ownership change where none happened.
   412	  #
   413	  # No single signal is valid everywhere here: the content digest cannot see an
   414	  # identical-content refresh, the backup fires on the preserve-with-snapshot
   415	  # path, and mtime fires on install re-substitution. Each is used only where
   416	  # it is sound, and the boundary is stated rather than assumed.
   417	  if [[ "$op" == "upgrade" && "$_MTIME_BEFORE" != "$_MTIME_AFTER" ]]; then
   418	    printf 'REFRESH'; return 0
   419	  fi
   420	  # OQ-9 colapsada: sem registro ao final é PRESERVE_UNOWNED, tenha ou não
   421	  # existido um antes. O 'tinha antes?' é prior_record, que já é uma coluna.
   422	  if [[ -n "$ar" ]]; then printf 'PRESERVE_OWNED'; else printf 'PRESERVE_UNOWNED'; fi
   423	}
   424	
   425	_derive_hash_source() {  # $1 surface $2 after_rec $3 prior_rec $4 src_root
   426	  local surface="$1" ar="$2" pr="$3" src="$4"
   427	  [[ -z "$ar" ]] && { printf 'HASH_NONE'; return 0; }
   428	  case "$ar" in link:*) printf 'LINK_RECORD'; return 0 ;; esac
   429	
   430	  local got="${ar#hash:}"

exec
/bin/zsh -lc "grep -R \"test-ownership-verdict-unit\\|test-ownership-table\" -n .github Makefile scripts .claude/scripts 2>/dev/null | head -100; grep -R \"test-upgrade-spec-ownership\" -n .github .claude scripts | head -100; grep -R \"scripts/tests/.*\\.sh\" -n .github/workflows | head -100" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 1070ms:
scripts/tests/test-ownership-verdict-unit.sh:8:#   test-ownership-table.sh — do the callers OBSERVE the dimensions
scripts/tests/test-ownership-verdict-unit.sh:22:#   test-ownership-verdict-unit.sh            every row
scripts/tests/test-ownership-verdict-unit.sh:23:#   test-ownership-verdict-unit.sh --only OWN-0013,OWN-0021
scripts/tests/test-ownership-verdict-unit.sh:24:#   test-ownership-verdict-unit.sh --quiet    only the summary
scripts/tests/test-ownership-table.sh:14:#   test-ownership-table.sh              run every row
scripts/tests/test-ownership-table.sh:15:#   test-ownership-table.sh --only OWN-0013
scripts/tests/test-ownership-table.sh:16:#   test-ownership-table.sh --map        emit the map only (no pass/fail exit)
scripts/tests/test-ownership-table.sh:17:#   test-ownership-table.sh --list       list row ids and exit
scripts/tests/test-ownership-table.sh:18:#   test-ownership-table.sh --keep       keep the scratch dir (debugging)
.github/workflows/smoke-install.yml:27:      - "scripts/tests/test-upgrade-spec-ownership.sh"
.github/workflows/smoke-install.yml:60:      - "scripts/tests/test-upgrade-spec-ownership.sh"
.github/workflows/smoke-install.yml:224:          bash scripts/tests/test-upgrade-spec-ownership.sh
.claude/adr/ADR-155-AMEND-1-delivery-record-ownership.md:207:- `scripts/tests/test-upgrade-spec-ownership.sh` — record-owned forced
.claude/plans/PLAN-166/W1-land-runbook.md:13:>   `test-upgrade-spec-ownership.sh` are 755; `_framework_manifest_set.sh`
.claude/plans/PLAN-166/W1-land-runbook.md:165:cp -p "$S/scripts/tests/test-upgrade-spec-ownership.sh"          scripts/tests/test-upgrade-spec-ownership.sh
.claude/plans/PLAN-166/W1-land-runbook.md:171:  scripts/tests/test-upgrade-spec-ownership.sh \
.claude/plans/PLAN-166/W1-land-runbook.md:175:  scripts/tests/test-upgrade-spec-ownership.sh \
.claude/plans/PLAN-166/W1-land-runbook.md:304:bash scripts/tests/test-upgrade-spec-ownership.sh
.claude/plans/PLAN-166/W1-land-runbook.md:318:  scripts/_framework_manifest_set.sh scripts/tests/test-upgrade-spec-ownership.sh \
.claude/plans/PLAN-166/W1-land-runbook.md:356:  scripts/install.sh scripts/tests/test-upgrade-spec-ownership.sh \
.claude/plans/PLAN-166/staged-manifest.sha256:20:3c027435e5df55dc39e66aa1e5c0fbef1b17f21553e07c64bca0606eb534a29b  .claude/plans/PLAN-166/staged/patches/f3-test-upgrade-spec-ownership.patch
.claude/plans/PLAN-166/staged-manifest.sha256:33:5dbe355071c072cd3e5d78a9155cb6ef3cb4f9636a11cc797116542c47d00f38  .claude/plans/PLAN-166/staged/scripts/tests/test-upgrade-spec-ownership.sh
.claude/plans/PLAN-166/architect/round-1/approved.md:85:10. `scripts/tests/test-upgrade-spec-ownership.sh` — NEW e2e (S1-S8).
.claude/plans/PLAN-166/architect/round-1/approved.md:174:  - scripts/tests/test-upgrade-spec-ownership.sh
.claude/plans/PLAN-166/W1-approved-draft.md:111:10. `scripts/tests/test-upgrade-spec-ownership.sh` — NEW e2e (S1-S8).
.claude/plans/PLAN-166/W1-approved-draft.md:198:  - scripts/tests/test-upgrade-spec-ownership.sh
scripts/tests/test-upgrade-spec-ownership.sh:2:# scripts/tests/test-upgrade-spec-ownership.sh
scripts/tests/test-upgrade-spec-ownership.sh:47:# Run:  bash scripts/tests/test-upgrade-spec-ownership.sh ; echo rc=$?
.github/workflows/smoke-install.yml:16:      - "scripts/tests/test-upgrade-dryrun-identity.sh"
.github/workflows/smoke-install.yml:17:      - "scripts/tests/test-upgrade-exclusions.sh"
.github/workflows/smoke-install.yml:18:      - "scripts/tests/smoke-install.sh"
.github/workflows/smoke-install.yml:22:      - "scripts/tests/test-install-upgrade-parity-e2e.sh"
.github/workflows/smoke-install.yml:25:      # scripts/tests/*.sh runs ONLY in this workflow (same r11/r20 wiring
.github/workflows/smoke-install.yml:27:      - "scripts/tests/test-upgrade-spec-ownership.sh"
.github/workflows/smoke-install.yml:33:      # PLAN-166 F4 wiring (r11/r20): scripts/tests/*.sh runs ONLY here, so a
.github/workflows/smoke-install.yml:55:      - "scripts/tests/test-upgrade-dryrun-identity.sh"
.github/workflows/smoke-install.yml:56:      - "scripts/tests/test-upgrade-exclusions.sh"
.github/workflows/smoke-install.yml:57:      - "scripts/tests/smoke-install.sh"
.github/workflows/smoke-install.yml:58:      - "scripts/tests/test-install-upgrade-parity-e2e.sh"
.github/workflows/smoke-install.yml:60:      - "scripts/tests/test-upgrade-spec-ownership.sh"
.github/workflows/smoke-install.yml:112:          PIN="$(bash scripts/tests/test-install-upgrade-parity-e2e.sh --print-pin)"
.github/workflows/smoke-install.yml:135:          bash scripts/tests/smoke-install.sh
.github/workflows/smoke-install.yml:142:          bash scripts/tests/test-upgrade-dryrun-identity.sh
.github/workflows/smoke-install.yml:147:          bash scripts/tests/test-upgrade-exclusions.sh
.github/workflows/smoke-install.yml:182:          bash scripts/tests/test-install-upgrade-parity-e2e.sh
.github/workflows/smoke-install.yml:194:          bash scripts/tests/test-install-upgrade-parity-e2e.sh \
.github/workflows/smoke-install.yml:219:      # scripts/tests/*.sh runs ONLY here — unwired = no test. NO
.github/workflows/smoke-install.yml:224:          bash scripts/tests/test-upgrade-spec-ownership.sh
.github/workflows/validate.yml:357:          bash scripts/tests/test-install-harness-codex.sh
.github/workflows/validate.yml:362:          bash scripts/tests/test-install-harness-grok.sh
.github/workflows/validate.yml:869:      # (scripts/tests/test_install_state_replay.sh,
.github/workflows/validate.yml:870:      # scripts/tests/test-doctor.sh) are local/landing-gate only — the

exec
/bin/zsh -lc "sed -n '1,100p' .github/workflows/validate.yml; grep -n \"check-model-deprecations\\|test_model_deprec\" .github/workflows/validate.yml .github/workflows/*.yml; find . -iname '*model*deprecation*test*' -o -name 'test_model_deprecations.py'" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
name: Validate CEO Orchestration governance

on:
  pull_request:
  push:
    branches: [main]

# Cancel in-progress runs when a newer commit lands on the same ref.
# Prevents duplicate compute on rapid-fire PR updates and matches the
# devops-ci-cd skill's concurrency-control mandate.
concurrency:
  group: validate-${{ github.ref }}
  cancel-in-progress: true

# Least-privilege: this workflow only reads the repo to validate.
permissions:
  contents: read

jobs:
  validate:
    name: Governance, health, contamination, shellcheck
    # PLAN-012 Phase 2 CEO_SOTA_DISABLE parity. Job-level `if:` keeps
    # the kill-switch scoped to a single check instead of per-step
    # guards across 18 steps. A repo admin sets `CEO_SOTA_DISABLE=1`
    # as a repo variable to short-circuit without editing YAML.
    if: vars.CEO_SOTA_DISABLE != '1'
    runs-on: Ceo
    # PLAN-014 G.1 ADJ-040 — bumped 5 → 10 to absorb policy-drift + TLA
    # drift + TestEnvContext mandate steps (Phases A.7 + B.7 + C.4)
    # without sporadic CI flakes on slower runners. S166/PLAN-114: 15->25 —
    # validate-governance.sh (47 steps) + lint + pytest + actionlint +
    # contamination + shellcheck legitimately runs ~10-15min; 15 was marginal
    # and timed out (->cancelled) under CI load. Job does not hang; 25 gives headroom.
    timeout-minutes: 25

    steps:
      - name: Checkout
        # SHA-pinned (Sprint 7 Dependabot bump): actions/checkout@v6.0.2
        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd

      # -----------------------------------------------------------------
      # Step: Governance structure validation
      # -----------------------------------------------------------------
      - name: Run validate-governance.sh
        run: |
          set -euo pipefail
          bash .claude/scripts/validate-governance.sh

      # -----------------------------------------------------------------
      # Step: CLAUDE.md drift check (PLAN-045 Wave 3 P0-14)
      #
      # Mechanical gate that asserts numeric claims in CLAUDE.md match
      # disk truth (ADR count, skill count, plan count). Closes the
      # PLAN-044 F-06-01 / F-06-02 / F-06-03 / F-06-06 / F-05-01 /
      # F-15-04 cross-cutting drift finding — previously 6 dimensions
      # independently flagged that CLAUDE.md aspired to numbers the
      # disk did not have.
      #
      # Failure remediation: one-shot CLAUDE.md edit at next session
      # closeout (Gate-1 cache discipline). Run
      # ``python3 .claude/scripts/check-claude-md-claims.py --verbose``
      # locally to see exact claim/disk deltas.
      # -----------------------------------------------------------------
      - name: Run check-claude-md-claims.py
        run: |
          set -euo pipefail
          python3 .claude/scripts/check-claude-md-claims.py

      # -----------------------------------------------------------------
      # Step: AGENTS.md freshness gate (PLAN-153 Wave A follow-up)
      #
      # AGENTS.md lists the governance entry-point paths coding agents are
      # told to read; check-agents-md.py asserts every listed path exists
      # on disk so the file cannot drift into pointing at moved/deleted
      # files. Static, stdlib-only, NO network, NO credential — safe on
      # fork PRs. Kill-switch: the job-level `if:` CEO_SOTA_DISABLE gate
      # above (per-repo variable) covers this step like every other.
      # Exit contract: 0 fresh / non-zero stale — non-zero fails the job.
      # -----------------------------------------------------------------
      - name: Run check-agents-md.py (AGENTS.md freshness)
        run: |
          set -euo pipefail
          python3 .claude/scripts/check-agents-md.py

      # -----------------------------------------------------------------
      # Step: Doc skill-path resolves (PLAN-112-FOLLOWUP-install-md-skill-path)
      #
      # Every `.claude/skills/...SKILL.md` literal in INSTALL/README/CLAUDE.md
      # must resolve on disk (or be a documented placeholder / allowlisted).
      # Closes F-4.2 (INSTALL.md once cited a path missing the `core/` tier).
      # -----------------------------------------------------------------
      - name: Run check-doc-skill-paths.sh
        run: |
          set -euo pipefail
          bash .claude/scripts/local/check-doc-skill-paths.sh

      # -----------------------------------------------------------------
      # Step: Doc count drift — bidirectional + cross-file
      # (PLAN-112-FOLLOWUP-claude-md-count-drift)
      #

exec
/bin/zsh -lc "stat -f '%Sp %N' scripts/tests/test-ownership-verdict-unit.sh scripts/tests/test-upgrade-spec-ownership.sh 2>/dev/null || stat -c '%A %n' scripts/tests/test-ownership-verdict-unit.sh scripts/tests/test-upgrade-spec-ownership.sh; git diff --check; printf '\\n--- changed python py39 scan ---\\n'; python3 - <<'PY'
import ast, pathlib
for p in ['.claude/scripts/check-model-deprecations.py','.claude/scripts/tests/test_release_workflow_asserts.py','scripts/tests/_parity_classify.py']:
    ast.parse(pathlib.Path(p).read_text(), filename=p)
    print('ast-ok', p)
PY" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 exited 1 in 123ms:

--- changed python py39 scan ---
zsh:1: can't create temp file for here document: operation not permitted

exec
/bin/zsh -lc "PYTHONDONTWRITEBYTECODE=1 python3 -c \"import ast,pathlib; ps=['.claude/scripts/check-model-deprecations.py','.claude/scripts/tests/test_release_workflow_asserts.py','scripts/tests/_parity_classify.py']; [(ast.parse(pathlib.Path(p).read_text(),filename=p),print('ast-ok',p)) for p in ps]\"" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
python3: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
python3: error: couldn't create cache file '/tmp/xcrun_db-BhahzXrh' (errno=Operation not permitted)
python3: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
python3: error: couldn't create cache file '/tmp/xcrun_db-JwlsWz1c' (errno=Operation not permitted)
ast-ok .claude/scripts/check-model-deprecations.py
ast-ok .claude/scripts/tests/test_release_workflow_asserts.py
ast-ok scripts/tests/_parity_classify.py

exec
/bin/zsh -lc "PYTHONDONTWRITEBYTECODE=1 python3 -c \"import yaml,pathlib; [(yaml.safe_load(pathlib.Path(p).read_text()),print('yaml-ok',p)) for p in ['.github/workflows/npm-publish.yml','.github/workflows/release.yml','.github/workflows/smoke-install.yml']]\"" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
python3: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
python3: error: couldn't create cache file '/tmp/xcrun_db-rmK58sqP' (errno=Operation not permitted)
python3: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
python3: error: couldn't create cache file '/tmp/xcrun_db-P2jXhZNM' (errno=Operation not permitted)
yaml-ok .github/workflows/npm-publish.yml
yaml-ok .github/workflows/release.yml
yaml-ok .github/workflows/smoke-install.yml

exec
/bin/zsh -lc "grep -R \"188 ADR\\|188 architecture\\|ADRs.*188\\|188 Architecture\\|Architecture.*188\" -n --exclude-dir=.git . 2>/dev/null | head -100; PYTHONDONTWRITEBYTECODE=1 python3 .claude/scripts/check-claude-md-claims.py --verbose; echo claude_claims_rc="'$?; PYTHONDONTWRITEBYTECODE=1 python3 .claude/scripts/check-agents-md.py --format json; echo agents_rc=$?' in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 1917ms:
./CHANGELOG.md:12:> v1.3.0: 166 skills, 27 slash commands, 188 ADRs, 68 `_lib` modules) are
./CHANGELOG.md:122:- ADRs 184 → **188** (ADR-185 night-mode; ADR-186 hook-deadline policy;
./.claude/plans/PLAN-166/W1-land-runbook.md:192:sed -i '' 's/\*\*188 ADRs\*\*/**189 ADRs**/' CLAUDE.md
./.claude/plans/PLAN-166/W1-land-runbook.md:193:sed -i '' 's/# 188 ADRs/# 189 ADRs/' README.md README.pt-BR.md npm/README.md docs/FAQ.md
./.claude/plans/PLAN-166/W1-land-runbook.md:194:sed -i '' 's/| Architecture decision records | \*\*188\*\*/| Architecture decision records | **189**/' README.md README.pt-BR.md docs/README.md npm/README.md
./.claude/plans/PLAN-166/W1-land-runbook.md:195:sed -i '' 's/| ADRs shipped | 188 |/| ADRs shipped | 189 |/' docs/CTO-GUIDE.md
./.claude/plans/PLAN-166/W1-land-runbook.md:196:sed -i '' 's/# 188 ADRs on disk/# 189 ADRs on disk/' docs/CTO-GUIDE.md
./.claude/plans/PLAN-166/W1-land-runbook.md:197:sed -i '' -E 's/(\| ADRs +\| )188/\1189/' docs/ARCHITECTURE.md
./.claude/plans/PLAN-166/W1-land-runbook.md:200:sed -i '' 's/# 188 architecture decision records/# 189 architecture decision records/' docs/ARCHITECTURE.md
./.claude/plans/PLAN-166/W1-land-runbook.md:209:sed -i '' 's/188 ADRs document every architectural decision/189 ADRs document every architectural decision/' docs/GUIA-COMPLETO.md
./.claude/plans/PLAN-166/W1-land-runbook.md:210:sed -i '' 's/188 Architecture Decision Records/189 Architecture Decision Records/' docs/GUIA-COMPLETO.md
./.claude/plans/PLAN-166/W1-land-runbook.md:367:git commit -S -m "governance(PLAN-166): W1 findings-closure ceremony — await-gate, verdict delta+ancestry, delivery-record ownership (ADRs 188->189) [SENT-PLAN166-W1]"
./.claude/plans/PLAN-166/architect/round-1/approved.md:96:    (":167 `188 ADRs document every architectural decision`" and
./.claude/plans/PLAN-166/architect/round-1/approved.md:97:    ":1225 `— 188 Architecture Decision Records`") — GUIA is in the
./.claude/plans/PLAN-166/W1-approved-draft.md:122:    (":167 `188 ADRs document every architectural decision`" and
./.claude/plans/PLAN-166/W1-approved-draft.md:123:    ":1225 `— 188 Architecture Decision Records`") — GUIA is in the
./.claude/plans/PLAN-166/repass-r1/transcript-r1.log:239:+Scope:  PLAN-162 / PLAN-165 (ADRs 184 -> 188)
./.claude/plans/PLAN-166/repass-r1/transcript-r1.log:289:+#   ADRs              ls .claude/adr/ADR-*.md                        exact (188)
./.claude/plans/PLAN-166/repass-r1/transcript-r1.log:837:+> v1.3.0: 166 skills, 27 slash commands, 188 ADRs, 68 `_lib` modules) are
./.claude/plans/PLAN-166/repass-r1/transcript-r1.log:947:+- ADRs 184 → **188** (ADR-185 night-mode; ADR-186 hook-deadline policy;
./.claude/plans/PLAN-166/repass-r1/transcript-r1.log:990:+| Architecture decision records | **188** | under `.claude/adr/` |
./.claude/plans/PLAN-166/repass-r1/transcript-r1.log:1001:+ls .claude/adr | grep -c '^ADR-'                  # 188 ADRs
./.claude/plans/PLAN-166/repass-r1/transcript-r1.log:1025:+| Architecture decision records | **188** | em `.claude/adr/` |
./.claude/plans/PLAN-166/repass-r1/transcript-r1.log:1036:+ls .claude/adr | grep -c '^ADR-'                  # 188 ADRs
./.claude/plans/PLAN-166/repass-r1/transcript-r1.log:1163:+    ├── adr/                        # 188 architecture decision records
./.claude/plans/PLAN-166/repass-r1/transcript-r1.log:1174:+| ADRs               | 188                          | `ls .claude/adr/ADR-*.md \| wc -l`                        |
./.claude/plans/PLAN-166/repass-r1/transcript-r1.log:1224:+| Architecture decision records | **188** | under `.claude/adr/` |
./.claude/plans/PLAN-166/repass-r1/transcript-r1.log:1235:+ls .claude/adr | grep -c '^ADR-'                  # 188 ADRs
./.claude/plans/PLAN-166/repass-r1/transcript-r1.log:1843:Scope:  PLAN-162 / PLAN-165 (ADRs 184 -> 188)
./.claude/plans/PLAN-166/repass-r1/transcript-r1.log:1941:#   ADRs              ls .claude/adr/ADR-*.md                        exact (188)
./.claude/plans/PLAN-166/repass-r1/transcript-r1.log:3050:   476	Scope:  PLAN-162 / PLAN-165 (ADRs 184 -> 188)
./.claude/plans/PLAN-166/repass-r1/transcript-r1.log:4129:   476	Scope:  PLAN-162 / PLAN-165 (ADRs 184 -> 188)
./.claude/plans/PLAN-166/repass-r1/transcript-r1.log:9495:    57	| Architecture decision records | **188** | em `.claude/adr/` |
./.claude/plans/PLAN-166/repass-r1/transcript-r1.log:9535:   166	ls .claude/adr | grep -c '^ADR-'                  # 188 ADRs
./.claude/plans/PLAN-166/repass-r1/transcript-r1.log:9559:    59	| Architecture decision records | **188** | under `.claude/adr/` |
./.claude/plans/PLAN-166/repass-r1/transcript-r1.log:9585:    59	| Architecture decision records | **188** | under `.claude/adr/` |
./.claude/plans/PLAN-166/repass-r1/transcript-r1.log:9637:    33	#   ADRs              ls .claude/adr/ADR-*.md                        exact (188)
./.claude/plans/PLAN-166/repass-r1/payload.redacted.txt:227:+Scope:  PLAN-162 / PLAN-165 (ADRs 184 -> 188)
./.claude/plans/PLAN-166/repass-r1/payload.redacted.txt:277:+#   ADRs              ls .claude/adr/ADR-*.md                        exact (188)
./.claude/plans/PLAN-166/repass-r1/payload.redacted.txt:825:+> v1.3.0: 166 skills, 27 slash commands, 188 ADRs, 68 `_lib` modules) are
./.claude/plans/PLAN-166/repass-r1/payload.redacted.txt:935:+- ADRs 184 → **188** (ADR-185 night-mode; ADR-186 hook-deadline policy;
./.claude/plans/PLAN-166/repass-r1/payload.redacted.txt:978:+| Architecture decision records | **188** | under `.claude/adr/` |
./.claude/plans/PLAN-166/repass-r1/payload.redacted.txt:989:+ls .claude/adr | grep -c '^ADR-'                  # 188 ADRs
./.claude/plans/PLAN-166/repass-r1/payload.redacted.txt:1013:+| Architecture decision records | **188** | em `.claude/adr/` |
./.claude/plans/PLAN-166/repass-r1/payload.redacted.txt:1024:+ls .claude/adr | grep -c '^ADR-'                  # 188 ADRs
./.claude/plans/PLAN-166/repass-r1/payload.redacted.txt:1151:+    ├── adr/                        # 188 architecture decision records
./.claude/plans/PLAN-166/repass-r1/payload.redacted.txt:1162:+| ADRs               | 188                          | `ls .claude/adr/ADR-*.md \| wc -l`                        |
./.claude/plans/PLAN-166/repass-r1/payload.redacted.txt:1212:+| Architecture decision records | **188** | under `.claude/adr/` |
./.claude/plans/PLAN-166/repass-r1/payload.redacted.txt:1223:+ls .claude/adr | grep -c '^ADR-'                  # 188 ADRs
./.claude/plans/PLAN-166-release-hold-findings-closure.md:439:   (r14: hoje diz "PLAN-162 / PLAN-165 (ADRs 184 -> 188)" — rc.2 e GA
./.claude/plans/PLAN-166-release-hold-findings-closure.md:521:   contagem exata de ADRs 188→189 — no MESMO commit da cerimônia,
./.claude/scripts/local/verify-counts.sh:35:#   ADRs              ls .claude/adr/ADR-*.md                        exact (188)
python3: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
python3: error: couldn't create cache file '/tmp/xcrun_db-6k9cSofq' (errno=Operation not permitted)
python3: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
python3: error: couldn't create cache file '/tmp/xcrun_db-ecYxwScE' (errno=Operation not permitted)
[PASS] ADR count: claim=189 disk=189 (tolerance=0) — ok
[PASS] Core skill count: claim=42 disk=42 (tolerance=0) — ok
[PASS] Frontend skill count: claim=8 disk=8 (tolerance=0) — ok
[PASS] Total skill count: claim=166 disk=166 (tolerance=0) — ok
[PASS] PLAN count: optional claim absent (ok)
claude_claims_rc=0
python3: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
python3: error: couldn't create cache file '/tmp/xcrun_db-QyedrtRN' (errno=Operation not permitted)
python3: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
python3: error: couldn't create cache file '/tmp/xcrun_db-nsPd6KXj' (errno=Operation not permitted)
{
  "checked_paths": 52,
  "problem_count": 0,
  "problems": []
}
agents_rc=0

exec
/bin/zsh -lc "sed -n '1,24p' CHANGELOG.md; sed -n '20,45p' .claude/scripts/local/verify-counts.sh; grep -n \"ADR\" .claude/scripts/local/verify-counts.sh | head -40" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
# Changelog

All notable changes to **ceo-orchestration** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> **Scope.** This log records *user-visible* changes — new skills, hooks, slash
> commands, schema/contract changes, and behavior an adopter would notice after
> installing or upgrading the framework. Internal refactors, test-only churn, and
> release-engineering bookkeeping are omitted. Counts cited below (as of
> v1.3.0: 166 skills, 27 slash commands, 188 ADRs, 68 `_lib` modules) are
> reproducible from the repository via
> `bash .claude/scripts/local/verify-counts.sh`.

---

## [1.3.0] - 2026-08-04

Night-mode + doctrine release (PLAN-162/165, ceremony 2). One user-facing
feature, one cross-rail security P0 closed, and one published-contract
conflict settled by ADR instead of by silence. As always: governance and
auditability — no speed claim.

#   - exact  : the doc number MUST equal the live count.
#   - floor  : the doc states "N+"; the live count MUST be >= N (so adding a
#              test never churns the docs — AC6).
#   - approx : the doc states a ROUNDED figure ("~14,000 collected cases",
#              "~730 test files"). See the APPROX CONTRACT block below.
# The check is BIDIRECTIONAL (a doc number that disagrees with live fails)
# and CROSS-FILE (each doc is checked against the live value, so all docs are
# mutually consistent by transitivity — AC3/AC4).
#
#   metric            live source                                   rule
#   ----------------  --------------------------------------------  -----
#   skills (total)    find .claude/skills -name SKILL.md            exact (166)
#   core skills       find .claude/skills/core -name SKILL.md       exact (42)
#   frontend skills   find .claude/skills/frontend -name SKILL.md   exact (8)
#   domain skills     find .claude/skills/domains -name SKILL.md    exact (116)
#   ADRs              ls .claude/adr/ADR-*.md                        exact (188)
#   hook .py files    ls .claude/hooks/*.py                          exact (57)
#   registered hooks  distinct *.py in settings.json hooks{} tree   exact (46)
#   registrations     total hook entries in settings.json hooks{}   exact (48)
#   _lib modules      ls .claude/hooks/_lib/*.py  (TOP-LEVEL glob)   exact (68)
#   SPEC v1 files     ls SPEC/v1/*.md                                exact (32)
#   tests             pytest --collect-only -q  (DOCUMENTED scope)  floor (N+) + approx (~N)
#   test_files        git ls-files '*test_*.py' '*_test.py'         approx (~N)
#   release_steps     grep -c '      - name:' release.yml           exact (29)
#   commands          find .claude/commands -name '*.md'             exact (27)
#   workflows         find .github/workflows -name '*.yml'           exact (21)
35:#   ADRs              ls .claude/adr/ADR-*.md                        exact (188)
196:DERIVED_ADRS=$(ls "$REPO_ROOT"/.claude/adr/ADR-*.md 2>/dev/null | wc -l | tr -d ' ')
349:# ADR existence-by-status gate (E9-F10 ii). bash-3.2 portable: no assoc arrays;
352:# line and handed to the python3 block via VC_ADR_VIOLATIONS for merge.
353:ADR_PRESENT_ACCEPTED="127 128 131"   # MUST exist on disk with status: ACCEPTED
354:ADR_RESERVED_ABSENT="130 134"        # MUST be ABSENT (a file = lifecycle drift)
355:ADR_VIOLATIONS=""
357:_adr_file() {  # echo the first ADR-<n>-*.md path that actually exists, else ""
359:  for hit in "$REPO_ROOT"/.claude/adr/ADR-"$n"-*.md; do
365:# The ADR-lifecycle gate is real-repo-specific: it asserts the fixed
368:# (e.g. test_verify_counts.py, ADR-000..004) legitimately lacks it — gate it on
369:# the RESERVED-ADR enumeration being present in CLAUDE.md so it stays robust and
372:for _n in $ADR_PRESENT_ACCEPTED; do
375:    ADR_VIOLATIONS="${ADR_VIOLATIONS}adr_lifecycle: ADR-${_n} expected present with status: ACCEPTED, but NO file on disk
378:    ADR_VIOLATIONS="${ADR_VIOLATIONS}adr_lifecycle: ADR-${_n} present but its status: frontmatter is not ACCEPTED
382:for _n in $ADR_RESERVED_ABSENT; do
385:    ADR_VIOLATIONS="${ADR_VIOLATIONS}adr_lifecycle: ADR-${_n} is a RESERVED slot and MUST be ABSENT on disk, but a file exists (presence = drift)
397:export VC_DOMAIN="$DERIVED_DOMAIN" VC_ADRS="$DERIVED_ADRS" VC_HOOK_PY="$DERIVED_HOOK_PY"
408:export VC_ADR_VIOLATIONS="$ADR_VIOLATIONS"
410:export VC_ADR_RESERVED_ABSENT="$ADR_RESERVED_ABSENT"
419:    "domain": iv("VC_DOMAIN"), "adrs": iv("VC_ADRS"), "hook_py": iv("VC_HOOK_PY"),
541:# behind (151 skills / 171 ADRs / 53 hooks / 22 commands).
606:    # PLAN-166 W0 F5: `# (\d+) ADRs` is the "verify it yourself" comment that
607:    # both READMEs put next to `ls .claude/adr | grep -c '^ADR-'`. It matched
610:    ("adrs", "exact", [r'(\d+) ADRs total', r'(\d+) ADRs on disk',
611:                       r'#\s*(\d+) ADRs\b']),
696:# A prose regex like "(\d+) ADRs" never matches "| ADRs | 178 |" — the number
701:    ("adrs",      "exact", r'^(?:ADRs|Architecture decision records)\b'),
1134:# ---- E9-F10 (ii): CLAUDE.md §1 RESERVED-ADR list must be exactly {130,134} ----
1135:# Parse the "ADR-<a>/<b> RESERVED (no file ..." enumeration (PLAN-120-FOLLOWUP
1139:    (os.environ.get("VC_ADR_RESERVED_ABSENT", "") or "").split()
1141:_rm = re.search(r'ADR-([\d/]+)\s+RESERVED \(no file', texts.get("CLAUDE.md", ""))
1142:# A tree that does not declare the RESERVED-ADR enumeration (generic synthetic
1150:            f"CLAUDE.md: RESERVED-ADR list cites {{{','.join(sorted(_cited))}}}, "
1154:# ---- E9-F10 (ii): merge ADR existence-by-status violations from the bash layer ----
1155:for _line in (os.environ.get("VC_ADR_VIOLATIONS", "") or "").splitlines():

exec
/bin/zsh -lc 'bash .claude/scripts/local/verify-counts.sh --no-tests; echo rc=$?' in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 129ms:
.claude/scripts/local/verify-counts.sh: line 412: cannot create temp file for here document: Operation not permitted
rc=1

exec
/bin/zsh -lc "git diff -- .claude/plans/PLAN-166/staged-manifest.sha256; cat .claude/plans/PLAN-166/staged-manifest.sha256; printf '\\n--- plan167 git status refs ---\\n'; find .claude/plans/PLAN-167 -maxdepth 3 -type f -print | sort | head -100" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-cUT5ztBO' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-zMFdVTZL' (errno=Operation not permitted)
diff --git a/.claude/plans/PLAN-166/staged-manifest.sha256 b/.claude/plans/PLAN-166/staged-manifest.sha256
index c1d4d0d..e77ebf6 100644
--- a/.claude/plans/PLAN-166/staged-manifest.sha256
+++ b/.claude/plans/PLAN-166/staged-manifest.sha256
@@ -2,31 +2,33 @@
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
64d23f858ef51b0f996e4966d4e27c0371b437e2d2787890b1f7ad22d4ec5663  .claude/plans/PLAN-166/staged/.claude/.framework-version
3c64b45a627bc4c1a5c9bf9c4e26eff793c0e4c92250bdd307ad267b1576a8af  .claude/plans/PLAN-166/staged/.claude/adr/ADR-155-AMEND-1-delivery-record-ownership.md
df7be2195cf197dfd881c5a18a3811132d20824cf3b935f1d084aef18b5f7692  .claude/plans/PLAN-166/staged/.claude/governance/npm-trusted-publisher.txt
d79d36ad28ea73f06d28a8b22ffeecf01ad8286647383f3cef1f96f802b564a8  .claude/plans/PLAN-166/staged/.claude/governance/pair-rail-verdict-template.md
ac84cd8194549f42394a7f2ac45786bc537391f27b67dde33c4c4b4c1bb0cefd  .claude/plans/PLAN-166/staged/.claude/scripts/check-framework-updates.sh
8589420213deb0970b267f15690c33acca31f42363b4b3464d3281d752a9a365  .claude/plans/PLAN-166/staged/.claude/scripts/tests/test_release_workflow_asserts.py
3ddd855970f8f4b337ba16810f85fdd4d61cc559bf6da4243e39721535d46d1c  .claude/plans/PLAN-166/staged/.github/workflows/npm-publish.yml
bf24d80621d24104c7e387efe64d7e9284ec4f1dc1fb875dc085618d24005162  .claude/plans/PLAN-166/staged/.github/workflows/release.yml
eaa0f3c9c3d70f96c81777d92dece0ffecd91f2a07ac8db217b5c269b7550d4a  .claude/plans/PLAN-166/staged/.github/workflows/smoke-install.yml
4935a60cb1227449a6a22bb913fb14c6ca76219bb603a9a031f3802e0f022d88  .claude/plans/PLAN-166/staged/INSTALL.md
813ffe5198eeac04f982023da1592210ac70682d8ccc2d6ef4e6b2dd24a5ac9c  .claude/plans/PLAN-166/staged/notes-w1b-kernel-override.md
61464f7a7cec04ecaa959904319c516a405ee9a98442383e596cea09e6c7cedf  .claude/plans/PLAN-166/staged/notes-w1c-f3.md
9a3b22f45cfa944aaddfb1ae6073a847f8abf39296ffc5eb47fa52accbfdbd47  .claude/plans/PLAN-166/staged/patches/f3-adr-155-amend-1.patch
7af7cf6a6c46a32042cb73f0761277e8ddd8869d5b596278e63013dfc6c435d9  .claude/plans/PLAN-166/staged/patches/f3-check-framework-updates-marker-first.patch
55af1b44196627f85e14bfdea023205900db74fe4c7e8884f8364bc3dfe14426  .claude/plans/PLAN-166/staged/patches/f3-doctor-delivery-flags.patch
9d3e40a2f97f0a238dcd8d49dfea4f78bc0dbc309311b34bf0212cc9ad05c3af  .claude/plans/PLAN-166/staged/patches/f3-fms-conditional-entries.patch
f340d81741e7cde417ea11463e56e7cbbd9f04b9227908b5c455eebedbc3f4d4  .claude/plans/PLAN-166/staged/patches/f3-framework-version-marker.patch
e0acdbb60a0e0a60f53dd495dd535371f2a24d54de8c3fdba2c0b484299dc192  .claude/plans/PLAN-166/staged/patches/f3-install-delivery-record.patch
01c5627b5b449820d2fbf2f33ed020f30b8ea094afe9474fd7b1cf8d35abfed8  .claude/plans/PLAN-166/staged/patches/f3-install-md-consequences.patch
3c027435e5df55dc39e66aa1e5c0fbef1b17f21553e07c64bca0606eb534a29b  .claude/plans/PLAN-166/staged/patches/f3-test-upgrade-spec-ownership.patch
0c67bdcdb267388bd60c9143bf6203495de14ebb562720feaeb37719d26fb8e9  .claude/plans/PLAN-166/staged/patches/f3-upgrade-spec-forced-refresh.patch
a83d8bc2353054d816342978962127e99cbc432c5e0ab8c1b4fe2a2365cfea2d  .claude/plans/PLAN-166/staged/patches/release-yml-verdict-delta-ancestry.patch
bf52d60642eb3392cd286db16a8c0d57036c394b117d2654fb7c0e9955873632  .claude/plans/PLAN-166/staged/patches/smoke-install-parity-e2e-wiring.patch
c3558235089ae461d4597e203a4c1466a0ca9d3c8b0805b5cffbecc48b6d355d  .claude/plans/PLAN-166/staged/patches/w0-verdict-template-delta-fields.patch
947bff3ff3e2b2c990abc59dd101a27f75065b97476f9814f62ee70c7e4fd88a  .claude/plans/PLAN-166/staged/patches/w1-parity-classify-known-open-purge.patch
2903e84dc079c45c085bafca751a20c99d3f199b2001ab6f96b4d04cd7e7307a  .claude/plans/PLAN-166/staged/patches/w1a-npm-publish-await-gate.patch
7a90547a50be440563e91603e921e51acbec10fa6942f9e25fa1635dd997d4c9  .claude/plans/PLAN-166/staged/patches/w1a-npm-trusted-publisher-txt.patch
f0d1489af60ef3d1d0c2ac236525d6f827686fc140cd23a282236137b036c440  .claude/plans/PLAN-166/staged/patches/w1a-release-workflow-asserts.patch
efe81bd8a6e22073cd701279efb2572f379e513bd5f4456a194d49e00dd54c56  .claude/plans/PLAN-166/staged/scripts/_framework_manifest_set.sh
c01160165c561e7ae0bb05315b36a187ea4c76d0c4d442426524300a6f14d02e  .claude/plans/PLAN-166/staged/scripts/doctor.sh
1812463fe152f9c9656e297f73b5248b3916aa54e6e3857bc33fba6e3b40eb31  .claude/plans/PLAN-166/staged/scripts/install.sh
d8d706554018b5ea326331bd0e66a3924295df2ced0de4f7f89439ce7304e66a  .claude/plans/PLAN-166/staged/scripts/tests/_parity_classify.py
5dbe355071c072cd3e5d78a9155cb6ef3cb4f9636a11cc797116542c47d00f38  .claude/plans/PLAN-166/staged/scripts/tests/test-upgrade-spec-ownership.sh
886429851f7b6480846e4aee0511036762edda0864b37aed9cbec73ad7a1ad4b  .claude/plans/PLAN-166/staged/scripts/upgrade.sh

--- plan167 git status refs ---
.claude/plans/PLAN-167/debate/round-1/consensus.md
.claude/plans/PLAN-167/debate/round-1/devops.md
.claude/plans/PLAN-167/debate/round-1/proposal.md
.claude/plans/PLAN-167/debate/round-1/qa-architect.md
.claude/plans/PLAN-167/debate/round-1/security-engineer.md

exec
/bin/zsh -lc 'for f in scripts/_framework_manifest_set.sh scripts/install.sh scripts/upgrade.sh scripts/tests/_parity_classify.py scripts/tests/test-ownership-table.sh scripts/tests/ownership_table.tsv; do sf=.claude/plans/PLAN-166/staged/$f; if [ -f "$sf" ]; then cmp -s "$f" "$sf" && echo SAME:$f || echo DIFF:$f; else echo NO-STAGED:$f; fi; done; printf '"'\\n--- overlays against Plan166 staged core ---\\n'; diff -u .claude/plans/PLAN-166/staged/scripts/_framework_manifest_set.sh scripts/_framework_manifest_set.sh | head -240; diff -u .claude/plans/PLAN-166/staged/scripts/upgrade.sh scripts/upgrade.sh | head -400" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
NO-STAGED:scripts/_framework_manifest_set.sh
NO-STAGED:scripts/install.sh
NO-STAGED:scripts/upgrade.sh
NO-STAGED:scripts/tests/_parity_classify.py
NO-STAGED:scripts/tests/test-ownership-table.sh
NO-STAGED:scripts/tests/ownership_table.tsv

--- overlays against Plan166 staged core ---
diff: .claude/plans/PLAN-166/staged/scripts/_framework_manifest_set.sh: No such file or directory
diff: .claude/plans/PLAN-166/staged/scripts/upgrade.sh: No such file or directory

exec
/bin/zsh -lc 'head -25 .claude/scripts/check-model-deprecations.py; head -25 scripts/tests/_parity_classify.py' in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
#!/usr/bin/env python3
"""check-model-deprecations.py — permanent model-deprecation checker.

PLAN-135 W0/W1 (unit w0r): the S230 heroic sweep made a permanent
instrument. Scans one or more directory trees for Claude model-id literals
listed in the sidecar JSON ledger (`model-deprecations.json`, same dir) and
classifies every hit by retirement proximity:

  BREAK  — id is already retired (API requests fail today) on a non-inert path
  WARN   — id retires within --warn-days (default 60) on a non-inert path
  INFO   — id is deprecated but retirement is farther out (or undated)
  INERT  — path matches a ledger `inert_path_rules` entry (negative fixtures,
           prose docs, historical run results, by-design id carriers — the
           S230 triage classes, configurable in the ledger, NOT hardcoded)

Scan targets (precedence): argv roots > CEO_DEPRECATION_SCAN_ROOTS
(os.pathsep-separated) > this framework repo itself. Matching logic reuses
the S230 sweep (.claude/plans/PLAN-135/research/sweep_deprecated_models.py):
os.walk with SKIP_DIRS pruning, 2MB cap, binary sniff, utf-8/ignore decode,
finditer with line numbers — but with ledger-driven patterns instead of
hardcoded ones and WITHOUT the hardcoded Owner-machine repo list.

Exit codes:
  0 — report mode (always), or --check with no BREAK/WARN, or infra
      fail-open (missing/corrupt ledger, bad --today: advisory + exit 0)
#!/usr/bin/env python3
"""Classifier for the install/upgrade parity e2e (PLAN-166 W0 / F4, OQ-4).

Driver: scripts/tests/test-install-upgrade-parity-e2e.sh (read its header for
the why). This module owns the MEASUREMENT and the DECLARATIONS.

The instrument
--------------
Two adopter trees are handed in:

    A = install.sh (working tree)
    B = install.sh @ <pin>  ->  upgrade.sh (working tree)

For every path A delivered, B's bytes are classified against BOTH source
generations, so the verdict is about the *generation of framework content the
adopter ends up running*, not about byte-equality of two installs:

    IDENTICAL     A(p) == B(p)
    PERSONALIZED  B(p) == head_src(p)  -- upgrade shipped CURRENT framework
                  bytes; install.sh additionally substitutes {{PROJECT_NAME}}
                  and friends.  Advisory: content generation is correct.
    STALE         B(p) == pin_src(p) != head_src(p)  -- the upgrade left the
                  OLD generation in place.  This is F3's exact signature and
                  it is FATAL.
    MISSING_IN_B  install delivered p, upgrade never did.  FATAL.

exec
/bin/zsh -lc "grep -n '"'^from __future__'"' .claude/scripts/check-model-deprecations.py scripts/tests/_parity_classify.py" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
.claude/scripts/check-model-deprecations.py:39:from __future__ import annotations
scripts/tests/_parity_classify.py:68:from __future__ import annotations

exec
/bin/zsh -lc "grep -n '"'^  release-gate:'"\\|"'^    name:'"' .github/workflows/release.yml | head -30; sed -n '30,58p' .github/workflows/release.yml" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
13:  release-gate:
869:    name: Publish GitHub Release + assets

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

exec
/bin/zsh -lc "sed -n '1,32p' .github/workflows/release.yml" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
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

exec
/bin/zsh -lc "grep -n \"release-gate.*name\\|job_name\\|keeps_exact\" .claude/scripts/tests/test_release_workflow_asserts.py | tail -40; sed -n '890,1030p' .claude/scripts/tests/test_release_workflow_asserts.py" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
54:`release-gate` job-name pin) plus the guard-module contract pins.
942:    def test_release_gate_job_name_exact(self):
            i_gpg, i_verdict,
            "pinned order broken: GPG verify must precede the verdict "
            "validation",
        )
        self.assertLess(
            i_verdict, i_gate,
            "pinned order broken: the verdict validation (step 15) must "
            "precede the delta+ancestry gate",
        )

    def test_pinned_order_inside_gate_delta_before_ancestry(self):
        block = _step_block(self.source, _W1B_STEP_NAME)
        self.assertLess(
            block.index("%s delta" % _GUARD_MODULE),
            block.index("%s ancestry" % _GUARD_MODULE),
            "pinned order broken inside the gate: delta before ancestry",
        )
        self.assertLess(
            block.index("%s ancestry" % _GUARD_MODULE),
            block.index('git merge-base --is-ancestor "$PARENT_SHA"'),
            "pinned order broken inside the gate: module ancestry "
            "(fetch + HEAD) before the parent merge-base judgment — the "
            "parent must be judged against the freshly fetched ref",
        )

    def test_gate_lives_inside_release_gate_job(self):
        # The step must run in the same job whose success the W1-A await
        # poller grants on — a gate in another job would not gate the
        # publish path.
        i_job = self.source.index("\n  release-gate:")
        i_next_job = self.source.index("\n  publish-release:")
        i_gate = self.source.index("- name: %s" % _W1B_STEP_NAME)
        self.assertTrue(
            i_job < i_gate < i_next_job,
            "the delta+ancestry gate must be a step of the release-gate "
            "job",
        )


class W1BReleaseGateJobNameTest(TestEnvContext):
    """The exact job name `release-gate` is load-bearing (W1-A await)."""

    def setUp(self):
        super().setUp()
        resolved = _w1b_release_text()
        if resolved is None:
            self.skipTest(
                "PLAN-166 W1-B release.yml not landed and staged mirror "
                "absent (pre-landing CI window)"
            )
        self.source, self.context = resolved

    def test_release_gate_job_name_exact(self):
        self.assertRegex(
            self.source, re.compile(r"^  release-gate:$", re.MULTILINE),
            "the job MUST keep the exact name `release-gate` — the "
            "W1-A await-release-gate poller resolves it BY NAME via the "
            "Actions jobs endpoint",
        )

    def test_publish_release_still_needs_release_gate(self):
        self.assertIn(
            "needs: release-gate", self.source,
            "publish-release must stay gated on release-gate",
        )


class W1BGuardModuleContractTest(TestEnvContext):
    """The live module surface the workflow step depends on.

    These asserts pin the CONTRACT the W1-B step consumes, so a module
    refactor that renames a subcommand or the parser is caught by the
    suite before it bricks a release run.
    """

    def setUp(self):
        super().setUp()
        self.module_path = _REPO / _GUARD_MODULE
        if not self.module_path.is_file():
            self.fail(
                "%s missing — the W1-B release.yml step invokes it; "
                "landing the workflow without the module bricks every "
                "release run" % _GUARD_MODULE
            )
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "release_tag_guard_w1b_contract", str(self.module_path)
        )
        self.mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.mod)

    def test_module_exposes_the_consumed_surface(self):
        for attr in ("_parse_verdict", "delta", "ancestry", "main"):
            self.assertTrue(
                hasattr(self.mod, attr),
                "module lost %r — the W1-B workflow step consumes it"
                % attr,
            )

    def test_parse_verdict_reads_parent_sha(self):
        fields = self.mod._parse_verdict(
            "# t\n\n```yaml\nparent_sha: "
            "4111a115190d375c39c90cc33ac1d9d5899c1cf2\n```\n"
        )
        self.assertEqual(
            fields.get("parent_sha"),
            "4111a115190d375c39c90cc33ac1d9d5899c1cf2",
        )

    def test_module_exit_codes_are_distinct_nonzero(self):
        # The workflow relies on ANY non-zero exit failing the step
        # (set -euo pipefail); pin that the module's failure codes are
        # non-zero and mutually distinct so the failure MODE stays
        # testable.
        codes = [
            self.mod.E_USAGE, self.mod.E_FETCH, self.mod.E_NOT_ANCESTOR,
            self.mod.E_REMOTE_REF, self.mod.E_DELTA,
            self.mod.E_MANIFEST_PIN, self.mod.E_MANIFEST_CONTENT,
            self.mod.E_MANIFEST_SET, self.mod.E_VERDICT, self.mod.E_VACUOUS,
        ]
        self.assertNotIn(0, codes)
        self.assertEqual(len(codes), len(set(codes)))


if __name__ == "__main__":
    unittest.main()

exec
/bin/zsh -lc "grep -n \"RC\\|rc\\.\" .github/workflows/release.yml | sed -n '1,160p'; sed -n '560,690p' .github/workflows/release.yml" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
38:      # PLAN-153 Wave B item 5 (c) — RC-aware VERSION↔tag comparison.
42:      # THE RC FLOW (documented so this never regresses): an RC tag
43:      # `v<X.Y.Z>-rc.N` is cut from a tree whose VERSION file ALREADY
44:      # reads the GA value `X.Y.Z` — the `-rc.N` pre-release suffix
46:      # 24h RC-hold gate below encodes the same convention: it derives
47:      # the RC tag family `v${VERSION}-rc.*` from the GA VERSION.)
49:      # every RC tag's own release run: `v1.0.1-rc.1` vs
50:      # `VERSION=1.0.1`. Fix: strip a trailing `-rc.<digits>` from the
52:      # strip); a wrong-version RC (`v1.0.2-rc.1` on `VERSION=1.0.1`)
61:          BASE="${EXPECTED%-rc.[0-9]*}"
67:            echo "OK: VERSION=$FILE matches RC tag=$TAG (compared against base '$BASE' after stripping the -rc.N pre-release suffix)"
145:      # F5 — RC-hold / staleness waiver SUNSET assertion.
158:      # ADR-007 RC-hold + 14-day staleness gates resume real enforcement.
163:      # `-rc.N` pre-release suffixes are stripped before comparison: RC
165:      # rc.* waiver is never an enforcement bypass on its own.
183:          # any -rc.* suffix, then sort -V -u. Iterated via a while-read
195:              echo "::error::Pre-GA RC-hold/staleness waivers are dishonest at or past GA."
238:      # PLAN-013 Phase 0 item 0.3 — mandatory RC-to-GA hold enforcement.
242:      # Debate Round 1 consensus §S3 HIGH (DevOps): "7-day RC hold is
246:      # RC tag `v1.x.y-rc.N` has existed for ≥24 hours. The 24h window
253:      #   1. If tag contains `-rc.` → skip check (RC tags always pass)
254:      #   2. Else find most recent `v<VERSION>-rc.*` tag (by creator date)
255:      #   3. If none exists → fail (mandatory RC before GA)
264:          # RC tags short-circuit — they are always permitted.
265:          if [[ "$TAG" == *-rc.* ]]; then
266:            echo "::notice::$TAG is an RC tag — skipping 24h hold check"
272:          # the RC-hold window can be waived per Owner authorization
280:              echo "::notice::$TAG has a pre-GA RC-hold waiver in $WAIVER_FILE — skipping hold check"
285:          # Find the most-recent RC tag for this version, by creator date.
288:          LAST_RC=$(git tag -l --sort=-creatordate "v${VERSION}-rc.*" | head -1)
290:          if [[ -z "$LAST_RC" ]]; then
291:            echo "::error::GA tag $TAG has no prior v${VERSION}-rc.* tag"
292:            echo "::error::Mandatory RC-hold requires a prior RC tag"
293:            echo "::error::Cut v${VERSION}-rc.1 first; wait 24h (Codex re-pass turnaround); then cut $TAG"
299:          RC_TS=$(git tag -l --format='%(creatordate:unix)' "$LAST_RC")
302:          if [[ -z "$RC_TS" || -z "$GA_TS" ]]; then
303:            echo "::error::Could not read creator-date for $LAST_RC or $TAG"
307:          DELTA=$((GA_TS - RC_TS))
312:            echo "::error::GA tag $TAG is only $HOURS hours after $LAST_RC"
318:          echo "OK: $TAG is $HOURS hours after $LAST_RC (≥24h Codex re-pass window per ADR-103)"
325:          # PLAN-153 Wave B item 5 (c) — same RC normalization as the
326:          # "Assert VERSION matches tag" step above: RC tags never get
327:          # their own CHANGELOG section; an RC for X.Y.Z validates
328:          # against the GA `## [X.Y.Z]` section (which exists at RC-cut
330:          # the RC is tagged). Without this strip the fixed VERSION gate
331:          # would just move the RC red run one step later.
332:          VERSION="${VERSION%-rc.[0-9]*}"
346:        # Post-tag-v1.6.0-rc.1 hardening (Session 33 CI batch): Hook +
419:          RC=$?
421:          if [ "$RC" -eq 5 ]; then
426:          if [ "$RC" -ne 1 ]; then
427:            echo "::error::populated install.sh rc=$RC (expected 1 for usage exit)"
439:          RC2=$?
441:          if [ "$RC2" -ne 5 ]; then
442:            echo "::error::tampered install.sh did NOT rc=5 (got $RC2) — self-SHA gate broken"
493:          # extension). Same waiver registry as the RC-hold gate:
862:            RC=$?
863:            echo "::error::reviewed parent $PARENT_SHA is not on origin/main (merge-base exit $RC) — the verdict is anchored on a commit main never saw (tag-without-push / orphan-verdict scenario, r17+r18)"
903:      # -rc.N suffix stripped, so RC notes point at the GA CHANGELOG
912:          BASE_VERSION="${VERSION%-rc.[0-9]*}"
937:      # RC tags (which reach this job since the RC-aware VERSION gate
956:          if [[ "$TAG" == *-rc.* ]]; then
            if [ -z "$latest_started" ] || [ "$latest_started" = "null" ]; then
              echo "::error::$wf — cannot parse startedAt for most-recent run"
              FAILED=1
              continue
            fi
            started_secs=$(date -u -d "$latest_started" +%s 2>/dev/null || echo 0)
            if [ "$started_secs" -eq 0 ]; then
              echo "::error::$wf — failed to parse startedAt: $latest_started"
              FAILED=1
              continue
            fi
            delta=$((NOW_SECS - started_secs))
            days=$((delta / 86400))
            if [ "$delta" -gt "$STALENESS_SECS" ]; then
              echo "::error::$wf stale — last run $days days ago (> $STALENESS_DAYS day limit)"
              FAILED=1
            else
              echo "::notice::$wf — recent runs OK; last run $days days ago"
            fi
          done
          if [ "$FAILED" -eq 1 ]; then
            echo "::error::release gate: one or more advisory workflows red or stale"
            exit 1
          fi
          echo "OK: all 6 advisory workflows clean in last 3 runs + fresh within $STALENESS_DAYS days"

      # ==========================================================
      # PLAN-045 F-14 STAGED STEPS (guarded if: false until activation)
      # ==========================================================
      # 3 steps below implement SBOM + sigstore envelope + GPG tag verify
      # on release. DORMANT (if: false) until prereqs land:
      #   1. sigstore-python action SHA is pinned + allowlisted
      #   2. generate-sbom.py ships at .claude/scripts/generate-sbom.py
      #   3. public-key for tag verify committed at .claude/trust/
      # Activation: remove `if: false` (1-line change). Scaffolding here
      # validates YAML well-formed + step composition reviewable.

      - name: Generate CycloneDX SBOM
        # PLAN-044 audit-v2 C2-P0-02 — activated Wave A 2026-04-27 (PLAN-063 round-4: removed `if: true` per actionlint if-cond)
        run: |
          python3 .claude/scripts/generate-sbom.py \
            --output sbom.cyclonedx.json
          echo "SBOM entries: $(jq '.components | length' sbom.cyclonedx.json)"

      - name: Sign release tarball with sigstore
        # STAGED — activate by setting repo var SIGSTORE_ACTIVATED=true (PLAN-063 round-4: replaces `if: false` per actionlint if-cond; default unset → expression false → step skipped)
        if: ${{ vars.SIGSTORE_ACTIVATED == 'true' }}
        env:
          SIGSTORE_KEY: ${{ secrets.SIGSTORE_PRIVATE_KEY }}
        run: |
          python3 -m sigstore sign \
            --key "$SIGSTORE_KEY" \
            --output-signature ceo-orchestration-${{ github.ref_name }}.sig \
            ceo-orchestration-${{ github.ref_name }}.tar.gz

      - name: Verify owner.asc populated
        # Session 75 Codex Finding 1 closure: prior workflow imported
        # `.claude/trust/owner.asc` without validating it carries a real
        # PGP block. Empty file silently no-ops `gpg --import` and the
        # subsequent `git tag --verify` could fall through. Fail-closed
        # gate ensures the trust anchor is populated before the import.
        run: |
          set -euo pipefail
          if [ ! -s .claude/trust/owner.asc ]; then
            echo "::error::.claude/trust/owner.asc is empty — release gate cannot verify tag signature"
            exit 1
          fi
          if ! gpg --show-keys .claude/trust/owner.asc >/dev/null 2>&1; then
            echo "::error::.claude/trust/owner.asc is not a valid PGP public-key block"
            exit 1
          fi
          echo "OK: owner.asc is populated and parseable"

      - name: Verify tag GPG signature
        # PLAN-044 audit-v2 C2-P0-02 — activated Wave A 2026-04-27 (Owner pubkey at .claude/trust/owner.asc; PLAN-063 round-4: removed `if: true` per actionlint if-cond)
        run: |
          gpg --import .claude/trust/owner.asc
          git tag --verify ${{ github.ref_name }}

      # ==========================================================
      # PLAN-081 Phase 6-bis — Pair-Rail verdict gate (step 15)
      # ==========================================================
      # R1 S-Sec-3 (replay defense) + R1 S-Sec-4 (deterministic inputs_hash)
      # + R1 C5 (Codex CLI pin enforcement) + R1 S-QA-Unseen-2 (distinct
      # VERDICT_EXPIRED exit code) + R1 S-CR-Unseen-6 (explicit "step 15 runs
      # after steps 1-14" ordering).
      #
      # S104 redesign: verdict.commit_sha → verdict.parent_sha.
      # The legacy commit_sha bind was an unsolvable self-reference
      # (verdict file cannot declare its own commit SHA — the SHA is only
      # known AFTER the verdict commit lands). v1.16.0 GA bridged via
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

exec
/bin/zsh -lc "grep -n 'Canhada-Labs/ceo-orchestration' .github/workflows/npm-publish.yml" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
433:        # Canhada-Labs/ceo-orchestration, workflow npm-publish.yml,

exec
/bin/zsh -lc "nl -ba .github/workflows/npm-publish.yml | sed -n '410,450p'" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
   410	        working-directory: npm
   411	        run: |
   412	          set -euo pipefail
   413	          PKG_NAME=$(node -p "require('./package.json').name")
   414	          PKG_VERSION=$(node -p "require('./package.json').version")
   415	          set +e
   416	          SEEN=$(npm view "${PKG_NAME}@${PKG_VERSION}" version 2>/dev/null)
   417	          RC=$?
   418	          set -e
   419	          if [[ "$RC" -eq 0 && "$SEEN" == "$PKG_VERSION" ]]; then
   420	            echo "published=true" >> "$GITHUB_OUTPUT"
   421	            echo "::notice::${PKG_NAME}@${PKG_VERSION} already exists in the registry — publish will be skipped (idempotent re-run, succeed-as-noop)"
   422	          else
   423	            echo "published=false" >> "$GITHUB_OUTPUT"
   424	            echo "OK: ${PKG_NAME}@${PKG_VERSION} not in registry (rc=$RC) — proceeding to publish"
   425	          fi
   426	
   427	      - name: Publish (Trusted Publishing — OIDC)
   428	        if: steps.already_published.outputs.published != 'true'
   429	        working-directory: npm
   430	        # PLAN-158 W1: NO long-lived token — npm >=11.5.1 detects the
   431	        # GitHub Actions OIDC context and mints a short-lived credential
   432	        # against the npmjs trusted-publisher registration (repo
   433	        # Canhada-Labs/ceo-orchestration, workflow npm-publish.yml,
   434	        # environment production-npm). --provenance keeps working (same
   435	        # OIDC JWT feeds Sigstore).
   436	        #
   437	        # ROLLBACK (token fallback) — kept dormant BY DESIGN, do not
   438	        # inline-enable: apply
   439	        # .claude/plans/PLAN-158/staged/wave1/rollback-oidc-to-token.patch
   440	        # (restores the `env: NODE_AUTH_TOKEN` block below), regenerate a
   441	        # granular NPM_TOKEN in the Owner console, then delete + re-tag
   442	        # (tag runs pin the workflow to the tag's tree — a re-run of the
   443	        # failed run would re-execute the OIDC tree). Full sequence:
   444	        # .claude/plans/PLAN-158/oidc-failure-playbook.md
   445	        run: npm publish --provenance --access public
   446	
   447	      - name: Publish skipped — version already in registry (no-op success)
   448	        if: steps.already_published.outputs.published == 'true'
   449	        run: |
   450	          echo "::notice::publish skipped — exact version already in the registry; this re-run is an idempotent no-op (PLAN-153 Wave B item 5)"

exec
/bin/zsh -lc "grep -n 'await_release_gate.py\\|_release_tag_guard.py' .claude/governance/pair-rail-inputs-hash-manifest.txt" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 exited 1 in 0ms:
exec
/bin/zsh -lc "grep -n 'open=' scripts/tests/ownership_table.tsv; grep -n 'open=' docs/ownership-decision-table.md" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
6:# `indistinguishable=` / `open=` remain annotations, never dimensions.
22:OWN-0016	spec	hash	dir_empty	edited	yes	copy	maintainer	install_rerun	none	none	PRESERVE_OWNED	HASH_PRIOR_RECORD	r11-F2	open=r11-F2; flag-only continuity emits zero file records
53:OWN-0052	spec	hash	symlink	-	yes	link	maintainer	install_rerun	none	none	PRESERVE_UNOWNED	HASH_NONE	r11-F1	open=r11-F1; absence of a LINK row is NOT a match
54:OWN-0053	marker	hash	symlink	-	yes	link	maintainer	install_rerun	none	none	PRESERVE_UNOWNED	HASH_NONE	r11-F1	open=r11-F1; sibling site
65:OWN-0081	marker	hash	regular	pristine	no	copy	maintainer	upgrade	none	none	PRESERVE_UNOWNED	HASH_NONE	r11-F3	open=r11-F3; external target: VERSION is adopter-owned and never written
173:`open=` survive as annotations because neither changes what the fixture does
278:  green), `invariant=<id>`, `open=<round-id>` (a defect this row asserts and

exec
/bin/zsh -lc "nl -ba scripts/tests/_parity_classify.py | sed -n '125,205p'; grep -n 'VERSION' scripts/tests/test-install-upgrade-parity-e2e.sh | head -80" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
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

Inspected the full working-tree diff, untracked tests/ADR, affected ownership/release code, and ran read-only syntax/static checks plus the pure ownership unit oracle. End-to-end tests could not create temporary directories under the read-only sandbox, so candidate defects were validated directly against the implementation and decision table.
  ✓ Inspect all changed and untracked files plus surrounding implementation context
  ✓ Run targeted static checks and tests for affected install/upgrade/release paths
  ✓ Validate candidate defects against repository contracts and produce findings
codex
The patch would block future releases because the new marker is not part of the bump machinery, and it still contains ownership-continuity paths that over-claim symlinks or lose records. The new ownership oracles are also not executed by CI.

Full review comments:

- [P1] Add the marker to the release bump table — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553/.github/workflows/release.yml:84-84
  On the next version bump, `.claude/scripts/local/_release_bump_sites.py` rewrites `VERSION` but does not include `.claude/.framework-version`, and `verify-counts.sh` does not watch it either. This new unconditional assertion will therefore compare a stale marker against the bumped `VERSION` and block every subsequent tag.

- [P1] Reject hash-record continuity for live symlinks — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553/scripts/install.sh:2326-2328
  When a copy-mode install left a HASH record but the live SPEC or marker was later replaced by a symlink, `_plt_rec` is empty and this helper returns success. A rerun with `--link` then preserves delivery and serializes the arbitrary symlink as a trusted LINK record, incorrectly converting adopter-owned content into framework-owned content; absence of a prior LINK record must not count as a target match for a live symlink.

- [P2] Preserve prior SPEC rows when the rerun tree is empty — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553/scripts/install.sh:2410-2414
  If a framework-managed `SPEC/v1` has been emptied before an install rerun, continuity fires here, but the manifest generator enumerates only live files and therefore emits zero SPEC records. The atomic rewrite drops ownership, so the next upgrade classifies the empty directory as an adopter fork and refuses to restore the contract; this case needs to carry the prior per-file records or an equivalent directory record.

- [P2] Compare the pointer with its prior baseline before preserving — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553/scripts/upgrade.sh:1577-1583
  When the generated pointer legitimately changes because the upgrade uses a different `--profile`, `--stack`, target, or source layout, the existing framework-generated pointer differs from the new canonical hash and is classified as `edited`. Even if its digest still equals the prior manifest, the verdict preserves it permanently as adopter-customized; customization should be determined against the prior baseline before deciding whether to refresh to the new canonical pointer.

- [P2] Run the ownership decision oracles in CI — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553/.github/workflows/smoke-install.yml:219-224
  The workflow still invokes only `test-upgrade-spec-ownership.sh`; neither the new `test-ownership-verdict-unit.sh` nor `test-ownership-table.sh` appears in any workflow or path filter. Consequently caller/table divergences such as the empty-tree and HASH-to-symlink cases can merge despite the new files describing both oracles as required.
The patch would block future releases because the new marker is not part of the bump machinery, and it still contains ownership-continuity paths that over-claim symlinks or lose records. The new ownership oracles are also not executed by CI.

Full review comments:

- [P1] Add the marker to the release bump table — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553/.github/workflows/release.yml:84-84
  On the next version bump, `.claude/scripts/local/_release_bump_sites.py` rewrites `VERSION` but does not include `.claude/.framework-version`, and `verify-counts.sh` does not watch it either. This new unconditional assertion will therefore compare a stale marker against the bumped `VERSION` and block every subsequent tag.

- [P1] Reject hash-record continuity for live symlinks — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553/scripts/install.sh:2326-2328
  When a copy-mode install left a HASH record but the live SPEC or marker was later replaced by a symlink, `_plt_rec` is empty and this helper returns success. A rerun with `--link` then preserves delivery and serializes the arbitrary symlink as a trusted LINK record, incorrectly converting adopter-owned content into framework-owned content; absence of a prior LINK record must not count as a target match for a live symlink.

- [P2] Preserve prior SPEC rows when the rerun tree is empty — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553/scripts/install.sh:2410-2414
  If a framework-managed `SPEC/v1` has been emptied before an install rerun, continuity fires here, but the manifest generator enumerates only live files and therefore emits zero SPEC records. The atomic rewrite drops ownership, so the next upgrade classifies the empty directory as an adopter fork and refuses to restore the contract; this case needs to carry the prior per-file records or an equivalent directory record.

- [P2] Compare the pointer with its prior baseline before preserving — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553/scripts/upgrade.sh:1577-1583
  When the generated pointer legitimately changes because the upgrade uses a different `--profile`, `--stack`, target, or source layout, the existing framework-generated pointer differs from the new canonical hash and is classified as `edited`. Even if its digest still equals the prior manifest, the verdict preserves it permanently as adopter-customized; customization should be determined against the prior baseline before deciding whether to refresh to the new canonical pointer.

- [P2] Run the ownership decision oracles in CI — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553/.github/workflows/smoke-install.yml:219-224
  The workflow still invokes only `test-upgrade-spec-ownership.sh`; neither the new `test-ownership-verdict-unit.sh` nor `test-ownership-table.sh` appears in any workflow or path filter. Consequently caller/table divergences such as the empty-tree and HASH-to-symlink cases can merge despite the new files describing both oracles as required.
