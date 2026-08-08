OpenAI Codex v0.144.6
--------
workdir: /Users/joaocanhada/canhada-labs/ceo-orchestration
model: gpt-5.6-sol
provider: openai
approval: never
sandbox: workspace-write [workdir, /tmp, $TMPDIR]
reasoning effort: xhigh
reasoning summaries: none
session id: 019fdeaa-ca48-7cb2-bf85-9f84a795a7b5
--------
user
current changes
  → Inspect staged, unstaged, and untracked changes
  • Trace affected code paths and run focused checks
  • Return prioritized review findings
exec
/bin/zsh -lc "git status --short && printf '\\n--- unstaged stat ---\\n' && git diff --stat && printf '\\n--- staged stat ---\\n' && git diff --cached --stat && printf '\\n--- untracked ---\\n' && git ls-files --others --exclude-standard" in /Users/joaocanhada/canhada-labs/ceo-orchestration
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
?? .claude/plans/PLAN-166/W1-ceremony-log.md
?? .claude/plans/PLAN-166/architect/round-1/approved.md.asc
?? .claude/plans/PLAN-166/archive/
?? .claude/plans/PLAN-167/OWNER-PREPARE-TO-SIGN.sh
?? .claude/plans/PLAN-167/W4-approved.md
?? .claude/plans/PLAN-167/W4-approved.md.asc
?? .claude/plans/PLAN-168/archive/

--- unstaged stat ---
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

--- staged stat ---

--- untracked ---
.claude/plans/PLAN-166/OWNER-W1-LAND-step1.sh
.claude/plans/PLAN-166/W1-ceremony-log.md
.claude/plans/PLAN-166/architect/round-1/approved.md.asc
.claude/plans/PLAN-166/archive/ceremony-porcelain-20260806-1430.txt
.claude/plans/PLAN-166/archive/ceremony-worktree-20260806-1430.diff
.claude/plans/PLAN-166/archive/codex-r6-2059.md
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
.claude/plans/PLAN-166/archive/w1-staged-pack-20260806-0159.tar.gz
.claude/plans/PLAN-166/archive/w1-staged-pack-final-20260806-0722.tar.gz
.claude/plans/PLAN-167/OWNER-PREPARE-TO-SIGN.sh
.claude/plans/PLAN-167/W4-approved.md
.claude/plans/PLAN-167/W4-approved.md.asc
.claude/plans/PLAN-168/archive/0001-plan168-W1-CI-wiring-dos-or-culos-de-propriedade.patch
.claude/plans/PLAN-168/archive/0002-plan168-W2-W3-INV-4-curada-pelo-gerador-nico-ADR-190.patch
.claude/plans/PLAN-168/archive/0003-plan168-baseline-map-re-gravado-62-GREEN-3-RED-run-2.patch
.claude/plans/PLAN-168/archive/full-e2e-20260807-2017.log
.claude/plans/PLAN-168/archive/pack-full.diff

exec
/bin/zsh -lc "printf '\\n===== .claude/scripts/check-framework-updates.sh =====\\n'; git diff --no-ext-diff -- \".claude/scripts/check-framework-updates.sh\"" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:

===== .claude/scripts/check-framework-updates.sh =====
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

exec
/bin/zsh -lc "printf '\\n===== .github/workflows/npm-publish.yml =====\\n'; git diff --no-ext-diff -- \".github/workflows/npm-publish.yml\"" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:

===== .github/workflows/npm-publish.yml =====
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

exec
/bin/zsh -lc "printf '\\n===== .github/workflows/release.yml =====\\n'; git diff --no-ext-diff -- \".github/workflows/release.yml\"" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:

===== .github/workflows/release.yml =====
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

exec
/bin/zsh -lc "printf '\\n===== .github/workflows/smoke-install.yml =====\\n'; git diff --no-ext-diff -- \".github/workflows/smoke-install.yml\"" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:

===== .github/workflows/smoke-install.yml =====
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
/bin/zsh -lc "printf '\\n===== scripts/doctor.sh =====\\n'; git diff --no-ext-diff -- \"scripts/doctor.sh\"" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:

===== scripts/doctor.sh =====
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

exec
/bin/zsh -lc "printf '\\n===== scripts/tests/_parity_classify.py =====\\n'; git diff --no-ext-diff -- \"scripts/tests/_parity_classify.py\"" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:

===== scripts/tests/_parity_classify.py =====
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

exec
/bin/zsh -lc "printf '\\n===== scripts/tests/test-upgrade-spec-ownership.sh =====\\n'; git diff --no-ext-diff -- \"scripts/tests/test-upgrade-spec-ownership.sh\"" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:

===== scripts/tests/test-upgrade-spec-ownership.sh =====
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
/bin/zsh -lc "git diff --unified=80 -- .github/workflows/release.yml | sed -n '1,360p'" in /Users/joaocanhada/canhada-labs/ceo-orchestration
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

exec
/bin/zsh -lc "git diff --unified=80 -- .github/workflows/smoke-install.yml | sed -n '1,360p'" in /Users/joaocanhada/canhada-labs/ceo-orchestration
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
/bin/zsh -lc "git diff --unified=80 -- scripts/doctor.sh | sed -n '1,300p'" in /Users/joaocanhada/canhada-labs/ceo-orchestration
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

exec
/bin/zsh -lc "git diff --unified=80 -- scripts/tests/_parity_classify.py | sed -n '1,320p'" in /Users/joaocanhada/canhada-labs/ceo-orchestration
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
/bin/zsh -lc "nl -ba .github/workflows/release.yml | sed -n '720,920p'; printf '\\n--- guard implementation ---\\n'; sed -n '1,320p' .claude/scripts/local/_release_tag_guard.py; printf '\\n--- verdict template diff ---\\n'; git diff --unified=60 -- .claude/governance/pair-rail-verdict-template.md" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
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
   901	      # `.github/release-notes-template.md` with {{TAG}} / {{VERSION}} /
   902	      # {{BASE_VERSION}} interpolation (BASE_VERSION = VERSION with any
   903	      # -rc.N suffix stripped, so RC notes point at the GA CHANGELOG
   904	      # section). Fail-closed on a missing template or an unrendered
   905	      # placeholder.
   906	      # -----------------------------------------------------------------
   907	      - name: Render release notes from template
   908	        run: |
   909	          set -euo pipefail
   910	          TAG="${GITHUB_REF_NAME}"
   911	          VERSION="${TAG#v}"
   912	          BASE_VERSION="${VERSION%-rc.[0-9]*}"
   913	          TEMPLATE=".github/release-notes-template.md"
   914	          if [[ ! -f "$TEMPLATE" ]]; then
   915	            echo "::error::release-notes template missing at $TEMPLATE"
   916	            exit 1
   917	          fi
   918	          sed -e "s/{{TAG}}/${TAG}/g" \
   919	              -e "s/{{VERSION}}/${VERSION}/g" \
   920	              -e "s/{{BASE_VERSION}}/${BASE_VERSION}/g" \

--- guard implementation ---
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

--- verdict template diff ---
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

exec
/bin/zsh -lc "sed -n '260,620p' .claude/scripts/local/_release_tag_guard.py; printf '\\n--- release tests diff headers ---\\n'; git diff --unified=10 -- .claude/scripts/tests/test_release_workflow_asserts.py | grep -n '"'^+class'"\\|"'^+    def test'"\\|"'^@@'"' | sed -n '1,260p'; printf '\\n--- npm current numbered ---\\n'; nl -ba .github/workflows/npm-publish.yml | sed -n '80,260p'" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
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

--- release tests diff headers ---
5:@@ -18,31 +18,81 @@ workflow-invariant convention (test_workflow_devops_p2.py) with:
88:@@ -50,20 +100,123 @@ if str(_HOOKS_DIR) not in sys.path:
212:@@ -212,35 +365,37 @@ class ReleaseNotesTemplateTest(TestEnvContext):
252:@@ -328,12 +483,534 @@ class WaveB5NpmPublishYmlTest(TestEnvContext):
263:+class Plan166AwaitGateTest(TestEnvContext):
288:+    def test_publish_needs_await_gate(self):
297:+    def test_publish_needs_await_gate_structurally(self):
304:+    def test_await_job_authenticates_gh_cli(self):
316:+    def test_await_job_permissions_and_timeout(self):
333:+    def test_await_job_is_the_rc_positive_control(self):
350:+    def test_await_job_invokes_decision_function(self):
356:+    def test_publish_posture_verbatim(self):
362:+    def test_already_published_guard_stays_in_publish_after_needs(self):
373:+class TrustedPublisherBindingTest(TestEnvContext):
407:+    def test_registered_workflow_file_publishes(self):
414:+    def test_workflow_honours_registered_binding(self):
421:+    def test_positive_control_environment_mutation_goes_red(self):
436:+    def test_positive_control_repository_mutation_goes_red(self):
514:+class W1BReleaseGateDeltaAncestryTest(TestEnvContext):
529:+    def test_gate_step_present(self):
535:+    def test_gate_step_has_no_continue_on_error(self):
544:+    def test_file_carries_exactly_one_continue_on_error(self):
561:+    def test_gate_fails_closed_on_transition_var(self):
575:+    def test_gate_never_builds_an_empty_parent_bind(self):
582:+    def test_gate_binds_parent_sha_independently(self):
598:+    def test_delta_delegates_to_guard_module(self):
606:+    def test_ancestry_delegates_to_guard_module(self):
614:+    def test_delta_semantics_not_reimplemented_in_bash(self):
636:+    def test_ancestry_covers_reviewed_parent(self):
645:+    def test_ancestry_covers_github_sha_via_head_identity(self):
655:+    def test_pinned_step_order(self):
670:+    def test_pinned_order_inside_gate_delta_before_ancestry(self):
685:+    def test_gate_lives_inside_release_gate_job(self):
699:+class W1BReleaseGateJobNameTest(TestEnvContext):
712:+    def test_release_gate_job_name_exact(self):
720:+    def test_publish_release_still_needs_release_gate(self):
727:+class W1BGuardModuleContractTest(TestEnvContext):
752:+    def test_module_exposes_the_consumed_surface(self):
760:+    def test_parse_verdict_reads_parent_sha(self):
770:+    def test_module_exit_codes_are_distinct_nonzero(self):

--- npm current numbered ---
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

exec
/bin/zsh -lc "sed -n '1,360p' .claude/scripts/await_release_gate.py; printf '\\n--- tests ---\\n'; sed -n '1,460p' .claude/scripts/tests/test_await_release_gate.py" in /Users/joaocanhada/canhada-labs/ceo-orchestration
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

--- tests ---
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
/bin/zsh -lc "sed -n '360,560p' .claude/scripts/await_release_gate.py; git status --short .claude/scripts/await_release_gate.py .claude/scripts/tests/test_await_release_gate.py; git log -1 --oneline -- .claude/scripts/await_release_gate.py" in /Users/joaocanhada/canhada-labs/ceo-orchestration
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
f492545 governance(PLAN-166): W0 residuais round 2 (12/12) + codex round (2 P2)

exec
/bin/zsh -lc 'git diff --unified=25 -- .github/workflows/smoke-install.yml' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
diff --git a/.github/workflows/smoke-install.yml b/.github/workflows/smoke-install.yml
index e1317fb..5794f0b 100644
--- a/.github/workflows/smoke-install.yml
+++ b/.github/workflows/smoke-install.yml
@@ -1,79 +1,141 @@
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
@@ -86,42 +148,95 @@ jobs:
 
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
/bin/zsh -lc "printf 'VERSION='; cat VERSION; printf 'marker='; cat .claude/.framework-version; printf '\\n--- framework marker base status ---\\n'; git ls-files .claude/.framework-version; printf '\\n--- framework update script full numbered ---\\n'; nl -ba .claude/scripts/check-framework-updates.sh | sed -n '1,260p'; printf '\\n--- framework checker tests refs ---\\n'; rg -n \"check-framework-updates|framework-version\" .claude/scripts/tests scripts/tests tests | head -240" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
VERSION=1.3.0
marker=1.3.0

--- framework marker base status ---
.claude/.framework-version

--- framework update script full numbered ---
     1	#!/bin/bash
     2	# check-framework-updates.sh — compare local VERSION to upstream tags
     3	#
     4	# Fetches upstream tag list via `git ls-remote --tags <repo>` (HTTPS),
     5	# parses semantic versions (vX.Y.Z, vX.Y.Z-rc.N), compares with local
     6	# VERSION file, and reports the delta.
     7	#
     8	# Network call: HTTPS only. Adopter-invoked. Documented in
     9	# threat-model.md as opt-in trust boundary.
    10	#
    11	# Usage:
    12	#   check-framework-updates.sh                              # default upstream
    13	#   check-framework-updates.sh --upstream <git-url>
    14	#   check-framework-updates.sh --json
    15	#   check-framework-updates.sh --quiet                       # exit code only
    16	#
    17	# Exit codes:
    18	#   0 — local matches upstream OR cannot determine (network failure)
    19	#   1 — local is behind (newer GA tag available)
    20	#   2 — local is behind by ≥ 1 MINOR version (highlighted as urgent)
    21	#   3 — fatal (no git, no VERSION file, malformed local version)
    22	
    23	set -euo pipefail
    24	
    25	# Framework upstream URL — points to the canonical ceo-orchestration
    26	# upstream by default. Adopters who fork the framework override via
    27	# CEO_FRAMEWORK_UPSTREAM env var OR install.sh
    28	# `--framework-upstream=<url>` substitution at install time.
    29	UPSTREAM="${CEO_FRAMEWORK_UPSTREAM:-https://github.com/Canhada-Labs/ceo-orchestration}"
    30	FORMAT="text"
    31	QUIET=0
    32	LOCAL_VERSION_FILE=""
    33	
    34	usage() {
    35	  cat <<EOF
    36	check-framework-updates.sh — compare local VERSION to upstream tags
    37	
    38	Usage:
    39	  check-framework-updates.sh [options]
    40	
    41	Options:
    42	  --upstream <git-url>     Override default upstream
    43	                           (default: \$CEO_FRAMEWORK_UPSTREAM or
    44	                            https://github.com/Canhada-Labs/ceo-orchestration)
    45	  --version-file <path>    Override default VERSION lookup
    46	  --json                   Machine-readable output
    47	  --quiet                  Suppress output; exit code only
    48	  -h, --help               This message
    49	
    50	Exit codes:
    51	  0 — up to date (or cannot determine)
    52	  1 — behind (newer GA tag available)
    53	  2 — behind by ≥ 1 MINOR (urgent)
    54	  3 — fatal
    55	EOF
    56	}
    57	
    58	while [[ $# -gt 0 ]]; do
    59	  case "$1" in
    60	    --upstream) UPSTREAM="$2"; shift 2 ;;
    61	    --version-file) LOCAL_VERSION_FILE="$2"; shift 2 ;;
    62	    --json) FORMAT="json"; shift ;;
    63	    --quiet) QUIET=1; shift ;;
    64	    -h|--help) usage; exit 0 ;;
    65	    *) echo "unknown arg: $1" >&2; usage >&2; exit 3 ;;
    66	  esac
    67	done
    68	
    69	log() {
    70	  if [ "$QUIET" -eq 0 ]; then
    71	    echo "$@" >&2
    72	  fi
    73	  return 0
    74	}
    75	out() {
    76	  if [ "$QUIET" -eq 0 ]; then
    77	    echo "$@"
    78	  fi
    79	  return 0
    80	}
    81	
    82	# Resolve the LOCAL framework version — MARKER-FIRST with VERSION fallback
    83	# (PLAN-166 F3 / ADR-155-AMEND-1). In an ADOPTER tree the root VERSION is an
    84	# install-time snapshot: upgrade.sh deliberately never touches it (the
    85	# S238/ADR-155 clobber class), so reading it post-upgrade reports the OLD
    86	# version forever and this checker would exit behind-minor demanding the
    87	# SAME upgrade it just performed, in a loop (r8). The upgrade refreshes
    88	# .claude/.framework-version instead — but the marker is only TRUSTED when
    89	# the SAME delivery record the writers use (the ADR-155 baseline manifest,
    90	# .claude/.install-manifest.sha256) records it as framework-delivered: a
    91	# pre-existing adopter marker that install EXISTS-skipped must not be read
    92	# at all (r20). Resolution order:
    93	#   1. --version-file <path>              (explicit override — unchanged)
    94	#   2. <root>/.claude/.framework-version  when well-formed AND
    95	#                                         delivery-recorded in the manifest
    96	#   3. <root>/VERSION                     (pre-v1.3.0 installs, and the
    97	#                                          framework repo itself, where the
    98	#                                          tracked marker == VERSION and
    99	#                                          VERSION stays the authority)
   100	if [ -n "$LOCAL_VERSION_FILE" ]; then
   101	  VFILE="$LOCAL_VERSION_FILE"
   102	  VSOURCE="explicit --version-file"
   103	else
   104	  # Walk up from CWD to the first directory carrying either signal.
   105	  cur="$(pwd)"
   106	  VROOT=""
   107	  VFILE=""
   108	  VSOURCE=""
   109	  while [ "$cur" != "/" ]; do
   110	    if [ -f "$cur/.claude/.framework-version" ] || [ -f "$cur/VERSION" ]; then
   111	      VROOT="$cur"
   112	      break
   113	    fi
   114	    cur="$(dirname "$cur")"
   115	  done
   116	  if [ -z "$VROOT" ]; then
   117	    echo "fatal: no .claude/.framework-version or VERSION found (looked from $(pwd))" >&2
   118	    exit 3
   119	  fi
   120	  MARKER="$VROOT/.claude/.framework-version"
   121	  MANIFEST="$VROOT/.claude/.install-manifest.sha256"
   122	  if [ -f "$MARKER" ]; then
   123	    MARKER_REC=""
   124	    if [ -f "$MANIFEST" ]; then
   125	      MARKER_REC="$(grep -E '^([0-9a-f]{64}|LINK)  \.claude/\.framework-version(  |$)' "$MANIFEST" 2>/dev/null | head -1 || true)"
   126	    fi
   127	    if [ -n "$MARKER_REC" ]; then
   128	      # r20 answered PROVENANCE (is this marker the framework's delivery?)
   129	      # but never INTEGRITY: a delivered marker edited afterwards to any
   130	      # well-formed version still satisfied the record check, so hand-editing
   131	      # 1.3.0 -> 9.9.9 made the checker report up-to-date against an upstream
   132	      # 1.3.0 and SUPPRESS a real update (codex W1 round 7, P2). Verify the
   133	      # live bytes against the record before selecting the marker; anything
   134	      # unverifiable falls back to VERSION — the same conservative direction
   135	      # r20 already takes for an unrecorded marker.
   136	      MARKER_OK=""
   137	      case "$MARKER_REC" in
   138	        LINK\ \ *)
   139	          # Fixed double-space delimiter (targets may contain spaces).
   140	          _rec_tgt="${MARKER_REC#LINK  .claude/.framework-version  }"
   141	          _live_tgt="$(readlink "$MARKER" 2>/dev/null || true)"
   142	          if [ -n "$_rec_tgt" ] && [ "$_rec_tgt" = "$_live_tgt" ]; then MARKER_OK=1; fi
   143	          ;;
   144	        *)
   145	          _rec_dg="${MARKER_REC%%  *}"
   146	          _live_dg=""
   147	          if command -v shasum >/dev/null 2>&1; then
   148	            _live_dg="$(shasum -a 256 "$MARKER" 2>/dev/null | cut -d' ' -f1 || true)"
   149	          elif command -v sha256sum >/dev/null 2>&1; then
   150	            _live_dg="$(sha256sum "$MARKER" 2>/dev/null | cut -d' ' -f1 || true)"
   151	          fi
   152	          if [ -n "$_live_dg" ] && [ "$_rec_dg" = "$_live_dg" ]; then MARKER_OK=1; fi
   153	          ;;
   154	      esac
   155	      if [ -z "$MARKER_OK" ]; then
   156	        log "note: .claude/.framework-version does NOT match its delivery record (edited, redirected, or no digest tool available) — falling back to VERSION"
   157	      else
   158	        MARKER_VAL="$(tr -d '\n\r ' < "$MARKER" 2>/dev/null || true)"
   159	        if [[ "$MARKER_VAL" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-rc\.[0-9]+)?$ ]]; then
   160	          VFILE="$MARKER"
   161	          VSOURCE="marker (.claude/.framework-version, delivery-recorded)"
   162	        else
   163	          log "note: .claude/.framework-version malformed ('$MARKER_VAL') — falling back to VERSION"
   164	        fi
   165	      fi
   166	    elif [ ! -f "$MANIFEST" ] && [ ! -f "$VROOT/VERSION" ]; then
   167	      # No manifest AND no VERSION: the marker is the only signal there is
   168	      # (fail-open — refusing here would make the checker fatal on a tree
   169	      # that still has a perfectly readable version value).
   170	      VFILE="$MARKER"
   171	      VSOURCE="marker (no manifest — only signal present)"
   172	    else
   173	      log "note: .claude/.framework-version present but NOT delivery-recorded in .claude/.install-manifest.sha256 — falling back to VERSION (r20: a pre-existing adopter marker is not the framework's)"
   174	    fi
   175	  fi
   176	  if [ -z "$VFILE" ] && [ -f "$VROOT/VERSION" ]; then
   177	    VFILE="$VROOT/VERSION"
   178	    VSOURCE="root VERSION (fallback)"
   179	  fi
   180	fi
   181	
   182	if [ -z "$VFILE" ] || [ ! -f "$VFILE" ]; then
   183	  echo "fatal: version source not found (looked from $(pwd))" >&2
   184	  exit 3
   185	fi
   186	log "version source: ${VSOURCE:-unknown} ($VFILE)"
   187	
   188	LOCAL="$(tr -d '\n\r ' < "$VFILE")"
   189	if [ -z "$LOCAL" ]; then
   190	  echo "fatal: VERSION file is empty: $VFILE" >&2
   191	  exit 3
   192	fi
   193	
   194	# Validate local version shape
   195	if ! [[ "$LOCAL" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-rc\.[0-9]+)?$ ]]; then
   196	  echo "fatal: local VERSION malformed: $LOCAL" >&2
   197	  exit 3
   198	fi
   199	
   200	# Fetch upstream tags
   201	if ! command -v git >/dev/null 2>&1; then
   202	  echo "fatal: git not available" >&2
   203	  exit 3
   204	fi
   205	
   206	log "fetching tags from $UPSTREAM ..."
   207	
   208	# Network call. Tolerate failure with exit 0 (we should not pageop on a
   209	# transient git fetch failure).
   210	TAGS_RAW="$(git ls-remote --tags --refs "$UPSTREAM" 2>&1 || true)"
   211	if [ -z "$TAGS_RAW" ] || echo "$TAGS_RAW" | grep -qiE 'fatal|error|denied'; then
   212	  log "warning: could not fetch upstream tags; assuming up-to-date"
   213	  if [ "$FORMAT" = "json" ]; then
   214	    out '{"status":"unknown","local":"'"$LOCAL"'","upstream":null,"reason":"network_or_perm_failure"}'
   215	  else
   216	    out "status: unknown (could not fetch upstream)"
   217	    out "local:    $LOCAL"
   218	    out "upstream: <unreachable>"
   219	  fi
   220	  exit 0
   221	fi
   222	
   223	# Parse — extract refs/tags/vX.Y.Z[-rc.N], strip leading v
   224	TAGS=()
   225	while IFS= read -r tag; do
   226	  [ -n "$tag" ] && TAGS+=("$tag")
   227	done < <(echo "$TAGS_RAW" | awk '{print $2}' | sed 's|^refs/tags/||' | grep -E '^v[0-9]+\.[0-9]+\.[0-9]+(-rc\.[0-9]+)?$' | sed 's/^v//' | sort -V -u)
   228	
   229	if [ "${#TAGS[@]}" -eq 0 ]; then
   230	  log "warning: no semver tags found upstream"
   231	  if [ "$FORMAT" = "json" ]; then
   232	    out '{"status":"unknown","local":"'"$LOCAL"'","upstream":null,"reason":"no_semver_tags"}'
   233	  else
   234	    out "status: unknown (no semver tags upstream)"
   235	  fi
   236	  exit 0
   237	fi
   238	
   239	LATEST="${TAGS[${#TAGS[@]}-1]}"
   240	
   241	# Helper: parse "X.Y.Z[-rc.N]" into space-sep "X Y Z RC" (RC=999 if no -rc)
   242	_parse_version() {
   243	  local v="$1"
   244	  local x y z rc
   245	  if [[ "$v" =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)-rc\.([0-9]+)$ ]]; then
   246	    x="${BASH_REMATCH[1]}"
   247	    y="${BASH_REMATCH[2]}"
   248	    z="${BASH_REMATCH[3]}"
   249	    rc="${BASH_REMATCH[4]}"
   250	  elif [[ "$v" =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)$ ]]; then
   251	    x="${BASH_REMATCH[1]}"
   252	    y="${BASH_REMATCH[2]}"
   253	    z="${BASH_REMATCH[3]}"
   254	    rc="999"
   255	  else
   256	    echo "0 0 0 0"
   257	    return
   258	  fi
   259	  echo "$x $y $z $rc"
   260	}

--- framework checker tests refs ---
scripts/tests/test-ownership-table.sh:100:    marker)   printf '.claude/.framework-version' ;;
scripts/tests/test-ownership-table.sh:257:  printf '1.3.1\n' > "$nxt/.claude/.framework-version"
scripts/tests/_parity_classify.py:149:        ".claude/.framework-version. Asserted positively below: B/VERSION must "
scripts/tests/_parity_classify.py:177:        "id": "F3-framework-version-marker",
scripts/tests/_parity_classify.py:179:        "path": ".claude/.framework-version",
scripts/tests/_parity_classify.py:182:            "root VERSION and into .claude/.framework-version, as a TRACKED "
scripts/tests/_parity_classify.py:187:            "check-framework-updates.sh keeps resolving the stale root VERSION"
scripts/tests/ownership_table.tsv:59:OWN-0064	marker	hash	regular	pristine	yes	copy	maintainer	upgrade	self	none	PRESERVE_OWNED	HASH_SOURCE	adr-155-amend-1	--skip .claude/.framework-version
scripts/tests/test-upgrade-spec-ownership.sh:5:# .claude/.framework-version) across install → upgrade → doctor → updater.
scripts/tests/test-upgrade-spec-ownership.sh:60:CHECKER="${CEO_UPDATE_CHECKER_UNDER_TEST:-$SOURCE_DIR/.claude/scripts/check-framework-updates.sh}"
scripts/tests/test-upgrade-spec-ownership.sh:75:if [ ! -f "$SOURCE_DIR/.claude/.framework-version" ]; then
scripts/tests/test-upgrade-spec-ownership.sh:76:  echo "FATAL: source has no .claude/.framework-version (F3 marker missing)" >&2
scripts/tests/test-upgrade-spec-ownership.sh:123:MARKER_REL=".claude/.framework-version"
scripts/tests/test-upgrade-spec-ownership.sh:144:manifest_has "$T1" '\.claude/\.framework-version(  |$)'    && ok "baseline records marker"      || bad "baseline has NO marker record"
scripts/tests/test-upgrade-spec-ownership.sh:197:echo "==> S6: check-framework-updates.sh — marker-first, record-gated"
scripts/tests/test-upgrade-spec-ownership.sh:218:sed -i.bak '/  \.claude\/\.framework-version/d' "$T1/$MANIFEST_REL" 2>/dev/null \
scripts/tests/test-upgrade-spec-ownership.sh:219:  || sed -i '' '/  \.claude\/\.framework-version/d' "$T1/$MANIFEST_REL" 2>/dev/null
scripts/tests/test-upgrade-spec-ownership.sh:282:manifest_has "$T3" '\.claude/\.framework-version(  |$)' \
scripts/tests/test-upgrade-spec-ownership.sh:330:manifest_has "$T4" '\.claude/\.framework-version(  |$)' \
.claude/scripts/tests/test_ceo_backup.py:279:    """Tests for check-framework-updates.sh — uses --version-file to avoid CWD walk."""
.claude/scripts/tests/test_ceo_backup.py:283:        self.script = REPO_ROOT / ".claude" / "scripts" / "check-framework-updates.sh"

exec
/bin/zsh -lc "rg -n \"framework-version|FMS_DELIVERED|_baseline_has_spec|delivered_spec|delivered_protocol|delivered_framework\" scripts/install.sh scripts/upgrade.sh scripts/_framework_manifest_set.sh | sed -n '1,300p'; printf '\\n--- nearby install ---\\n'; nl -ba scripts/install.sh | sed -n '1680,1940p'; printf '\\n--- nearby upgrade ---\\n'; rg -n \"_refresh_protocol_pointer|refresh.*SPEC|framework_marker|DELIVERED_SPEC|FMS_DELIVERED\" scripts/upgrade.sh" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
scripts/_framework_manifest_set.sh:36:#     PROTOCOL.md, SPEC/v1 and .claude/.framework-version are enumerated ONLY
scripts/_framework_manifest_set.sh:38:#         FMS_DELIVERED_PROTOCOL   root PROTOCOL.md pointer
scripts/_framework_manifest_set.sh:39:#         FMS_DELIVERED_SPEC       SPEC/v1 contract tree
scripts/_framework_manifest_set.sh:40:#         FMS_DELIVERED_MARKER     .claude/.framework-version marker
scripts/_framework_manifest_set.sh:122:    if [ "${FMS_DELIVERED_PROTOCOL:-0}" = "1" ]; then
scripts/_framework_manifest_set.sh:129:    if [ "${FMS_DELIVERED_SPEC:-0}" = "1" ]; then
scripts/_framework_manifest_set.sh:140:    if [ "${FMS_DELIVERED_MARKER:-0}" = "1" ]; then
scripts/_framework_manifest_set.sh:141:      printf '%s\n' ".claude/.framework-version"
scripts/_framework_manifest_set.sh:301:    .claude/.framework-version) printf '%s' "${FMS_HASH_SOURCE_MARKER:-}" ;;
scripts/_framework_manifest_set.sh:308:    SPEC/v1|SPEC/v1/*|PROTOCOL.md|.claude/.framework-version) return 0 ;;
scripts/install.sh:787:# write_install_manifest exports these as FMS_DELIVERED_* so the shared
scripts/install.sh:1336:    _state_record_op "delivered_spec_v1" "SPEC/v1"
scripts/install.sh:1358:# .claude/.framework-version is a TRACKED file of the framework repo (one
scripts/install.sh:1370:  if [[ ! -f "$SOURCE_DIR/.claude/.framework-version" ]]; then
scripts/install.sh:1371:    echo "    SKIP: .claude/.framework-version absent in source (pre-v1.3.0 checkout)"
scripts/install.sh:1375:  echo "==> Installing framework version marker (.claude/.framework-version — $(tr -d '[:space:]' < "$SOURCE_DIR/.claude/.framework-version"))"
scripts/install.sh:1376:  _state_record_op "install_framework_marker" ".claude/.framework-version"
scripts/install.sh:1377:  install_one ".claude/.framework-version"
scripts/install.sh:1380:    _state_record_op "delivered_framework_marker" ".claude/.framework-version"
scripts/install.sh:1938:  _state_record_op "delivered_protocol_pointer" "PROTOCOL.md"
scripts/install.sh:2385:     && grep -Eq '^([0-9a-f]{64}|LINK)  \.claude/\.framework-version(  |$)' "$manifest" 2>/dev/null \
scripts/install.sh:2386:     && _prior_link_target_matches "$manifest" ".claude/.framework-version"; then
scripts/install.sh:2390:.claude/.framework-version"
scripts/install.sh:2391:    echo "    ownership continuity: .framework-version delivery record preserved from prior manifest"
scripts/install.sh:2411:      *".claude/.framework-version"*) export FMS_HASH_SOURCE_MARKER="HASH_SOURCE" ;;
scripts/install.sh:2438:      *".claude/.framework-version"*) export FMS_HASH_SOURCE_MARKER="HASH_SOURCE" ;;
scripts/install.sh:2448:  export FMS_DELIVERED_SPEC="${_DELIVERED_SPEC:-0}"
scripts/install.sh:2449:  export FMS_DELIVERED_PROTOCOL="${_DELIVERED_PROTOCOL:-0}"
scripts/install.sh:2450:  export FMS_DELIVERED_MARKER="${_DELIVERED_MARKER:-0}"
scripts/install.sh:2458:  unset FMS_DELIVERED_SPEC FMS_DELIVERED_PROTOCOL FMS_DELIVERED_MARKER
scripts/upgrade.sh:344:  and the .claude/.framework-version marker) in an existing adopter
scripts/upgrade.sh:348:  .claude/.framework-version for the installed framework version). NOTE: .claude/settings.json IS
scripts/upgrade.sh:850:# record from the sanitized manifest: _baseline_has_spec_record and both
scripts/upgrade.sh:1660:# .claude/.framework-version) derives from the REGISTERED DELIVERY — here,
scripts/upgrade.sh:1665:_baseline_has_spec_record() {
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
scripts/upgrade.sh:3153:  export FMS_DELIVERED_SPEC="${_SPEC_DELIVERED:-0}"
scripts/upgrade.sh:3154:  export FMS_DELIVERED_PROTOCOL="${_PROTOCOL_DELIVERED:-0}"
scripts/upgrade.sh:3155:  export FMS_DELIVERED_MARKER="${_MARKER_DELIVERED:-0}"
scripts/upgrade.sh:3158:  unset FMS_DELIVERED_SPEC FMS_DELIVERED_PROTOCOL FMS_DELIVERED_MARKER

--- nearby install ---
  1680	  if [[ "$DRY_RUN" -eq 1 ]]; then
  1681	    if [[ "$SETTINGS_PRE_EXISTING" -eq 1 ]]; then
  1682	      echo "    (dry-run) settings.json pre-existed — would NOT touch deny baseline"
  1683	    else
  1684	      echo "    (dry-run) would MERGE ${#DENY_BASELINE_ENTRIES[@]} deny-baseline entries into .claude/settings.json"
  1685	    fi
  1686	    return 0
  1687	  fi
  1688	
  1689	  if [[ "$SETTINGS_PRE_EXISTING" -eq 1 ]]; then
  1690	    echo "    SKIP: settings.json pre-existed this run (add entries manually if wanted — docs/deny-baseline.md)"
  1691	    return 0
  1692	  fi
  1693	  if [[ ! -f "$SETTINGS_DST" ]]; then
  1694	    # build_settings decided not to produce one; nothing to inject into.
  1695	    return 0
  1696	  fi
  1697	
  1698	  # Build a JSON array literal from the entries. All entries are static
  1699	  # literals controlled above (no embedded double quotes or backslashes),
  1700	  # so direct interpolation is safe.
  1701	  local entries_json="[" e first=1
  1702	  for e in "${DENY_BASELINE_ENTRIES[@]}"; do
  1703	    if [[ "$first" -eq 1 ]]; then first=0; else entries_json+=","; fi
  1704	    entries_json+="\"$e\""
  1705	  done
  1706	  entries_json+="]"
  1707	
  1708	  local tmp="$SETTINGS_DST.deny-baseline.$$"
  1709	
  1710	  if command -v jq >/dev/null 2>&1; then
  1711	    # Order-preserving dedup: keep existing deny list as-is, append only
  1712	    # baseline entries not already present (jq array subtraction).
  1713	    if jq --argjson newdeny "$entries_json" '
  1714	         (.permissions.deny // []) as $cur
  1715	         | .permissions.deny = ($cur + ($newdeny - $cur))
  1716	       ' "$SETTINGS_DST" > "$tmp" 2>/dev/null; then
  1717	      mv "$tmp" "$SETTINGS_DST"
  1718	      echo "    MERGED: ${#DENY_BASELINE_ENTRIES[@]}-entry coarse deny baseline -> .claude/settings.json (docs/deny-baseline.md)"
  1719	      return 0
  1720	    fi
  1721	    rm -f "$tmp"
  1722	    echo "    WARNING: jq merge of the deny baseline failed — settings.json left untouched." >&2
  1723	    echo "             Add the permissions.deny entries manually: docs/deny-baseline.md." >&2
  1724	    return 0
  1725	  fi
  1726	
  1727	  if command -v python3 >/dev/null 2>&1; then
  1728	    if python3 - "$SETTINGS_DST" "$entries_json" > "$tmp" <<'PY'
  1729	import json
  1730	import sys
  1731	
  1732	with open(sys.argv[1], "r", encoding="utf-8") as fh:
  1733	    settings = json.load(fh)
  1734	new = json.loads(sys.argv[2])
  1735	perms = settings.setdefault("permissions", {})
  1736	cur = perms.get("deny") or []
  1737	perms["deny"] = cur + [e for e in new if e not in cur]
  1738	sys.stdout.write(json.dumps(settings, indent=2) + "\n")
  1739	PY
  1740	    then
  1741	      mv "$tmp" "$SETTINGS_DST"
  1742	      echo "    MERGED: ${#DENY_BASELINE_ENTRIES[@]}-entry coarse deny baseline -> .claude/settings.json (python3; docs/deny-baseline.md)"
  1743	      return 0
  1744	    fi
  1745	    rm -f "$tmp"
  1746	    echo "    WARNING: python3 merge of the deny baseline failed — settings.json left untouched." >&2
  1747	    echo "             Add the permissions.deny entries manually: docs/deny-baseline.md." >&2
  1748	    return 0
  1749	  fi
  1750	
  1751	  echo "    WARNING: neither jq nor python3 found — deny baseline NOT applied." >&2
  1752	  echo "             Add the permissions.deny entries manually: docs/deny-baseline.md." >&2
  1753	  return 0
  1754	}
  1755	
  1756	echo ""
  1757	echo "==> Deny baseline (coarse backstop — PLAN-153 Wave E; docs/deny-baseline.md)"
  1758	_state_record_op "apply_deny_baseline" "install.sh section 6a"
  1759	apply_deny_baseline
  1760	
  1761	# ---- 6b. P2-SEC-H (PLAN-019 Phase 3 Wave 3B): MCP secrets directory ----
  1762	#
  1763	# The MCP server authenticates clients via HMAC shared secrets stored at
  1764	# $TARGET/state/mcp_client_secrets/<client_id>.key. auth.load_secret()
  1765	# rejects any file whose perms are not exactly 0o600. If the containing
  1766	# directory is world-traversable (0o755 default umask), it's possible
  1767	# for a coexisting process to enumerate client_ids. Force 0o700 at
  1768	# install time and emit a banner. Additionally, ensure target/.gitignore
  1769	# excludes the secrets dir so keys never end up in VCS.
  1770	install_mcp_secrets_dir() {
  1771	  local secrets_dir="$TARGET/state/mcp_client_secrets"
  1772	  local gitignore="$TARGET/.gitignore"
  1773	
  1774	  if [[ "$DRY_RUN" -eq 1 ]]; then
  1775	    echo ""
  1776	    echo "==> MCP secrets directory (P2-SEC-H)"
  1777	    if [[ -d "$secrets_dir" ]]; then
  1778	      echo "    (dry-run) EXISTS: state/mcp_client_secrets (would chmod 700)"
  1779	    else
  1780	      echo "    (dry-run) would CREATE: state/mcp_client_secrets (chmod 700)"
  1781	    fi
  1782	    echo "    (dry-run) would ENSURE .gitignore excludes state/mcp_client_secrets/"
  1783	    return 0
  1784	  fi
  1785	
  1786	  echo ""
  1787	  echo "==> MCP secrets directory (P2-SEC-H)"
  1788	  _state_record_op "ensure_mcp_secrets_dir" "state/mcp_client_secrets 0700"
  1789	  mkdir -p "$secrets_dir"
  1790	  chmod 700 "$secrets_dir"
  1791	  echo "    ENSURED: $secrets_dir (mode 0700)"
  1792	  echo ""
  1793	  echo "    NOTE: this directory stores HMAC shared secrets for MCP clients."
  1794	  echo "          File perms MUST be 0600; auth.load_secret() fail-closes otherwise."
  1795	  echo "          DO NOT commit its contents to VCS."
  1796	
  1797	  # .gitignore entry — additive, idempotent.
  1798	  local ignore_line="state/mcp_client_secrets/"
  1799	  if [[ -f "$gitignore" ]]; then
  1800	    if ! grep -Fxq "$ignore_line" "$gitignore" 2>/dev/null; then
  1801	      {
  1802	        echo ""
  1803	        echo "# PLAN-019 P2-SEC-H: MCP shared-secret store (never commit)"
  1804	        echo "$ignore_line"
  1805	      } >> "$gitignore"
  1806	      echo "    APPENDED to .gitignore: $ignore_line"
  1807	    else
  1808	      echo "    .gitignore already excludes $ignore_line"
  1809	    fi
  1810	  else
  1811	    {
  1812	      echo "# PLAN-019 P2-SEC-H: MCP shared-secret store (never commit)"
  1813	      echo "$ignore_line"
  1814	    } > "$gitignore"
  1815	    echo "    CREATED .gitignore with: $ignore_line"
  1816	  fi
  1817	}
  1818	
  1819	
  1820	# PLAN-165 CX-3: night-mode / posture runtime state must never reach the
  1821	# adopter's VCS. `.claude/state/` is per-machine runtime state as a whole
  1822	# (PLAN-163 T3.1 declared it NON-COMMIT in the framework repo; an adopter
  1823	# tree needs the same posture) and `.claude/settings.local.json` is the
  1824	# per-machine permission overlay that decides the NEXT session's posture
  1825	# (PLAN-165). Without these entries, `/night-mode on` in an adopter leaves
  1826	# the overlay + marker as untracked files — falsifying PLAN-165 AC-1
  1827	# ("git status stays empty" after `on`) and risking an accidental commit
  1828	# of a machine-specific permission posture. Additive + idempotent, same
  1829	# contract as install_mcp_secrets_dir above.
  1830	install_posture_state_ignores() {
  1831	  local gitignore="$TARGET/.gitignore"
  1832	  local entries=".claude/state/ .claude/settings.local.json"
  1833	
  1834	  if [[ "$DRY_RUN" -eq 1 ]]; then
  1835	    echo ""
  1836	    echo "==> Posture-state .gitignore entries (PLAN-165 CX-3)"
  1837	    echo "    (dry-run) would ENSURE .gitignore excludes: $entries"
  1838	    return 0
  1839	  fi
  1840	
  1841	  echo ""
  1842	  echo "==> Posture-state .gitignore entries (PLAN-165 CX-3)"
  1843	  _state_record_op "ensure_posture_state_ignores" "$entries"
  1844	  local line
  1845	  for line in $entries; do
  1846	    if [[ -f "$gitignore" ]] && grep -Fxq "$line" "$gitignore" 2>/dev/null; then
  1847	      echo "    .gitignore already excludes $line"
  1848	      continue
  1849	    fi
  1850	    {
  1851	      echo ""
  1852	      echo "# PLAN-165 CX-3: per-machine posture/runtime state (never commit)"
  1853	      echo "$line"
  1854	    } >> "$gitignore"
  1855	    echo "    APPENDED to .gitignore: $line"
  1856	  done
  1857	}
  1858	
  1859	if [[ "$CEREMONY" != "user" ]]; then install_mcp_secrets_dir; fi  # WS4-guard-mcp
  1860	if [[ "$CEREMONY" != "user" ]]; then install_posture_state_ignores; fi  # PLAN-165 CX-3
  1861	
  1862	# ---- 7. Project-local templates (CLAUDE.md, MEMORY.md, .mcp.json — never overwrite) ----
  1863	
  1864	echo ""
  1865	echo "==> Installing project templates"
  1866	_state_record_op "install_project_templates" "ceremony=$CEREMONY"
  1867	if [[ "$CEREMONY" != "user" ]]; then  # WS4-guard-projtmpl
  1868	install_template "templates/CLAUDE.md" "CLAUDE.md"
  1869	install_template "templates/MEMORY.md" "MEMORY.md"
  1870	# PLAN-135 W1 S5-lite: project-scope MCP registration for the Codex
  1871	# pair-rail (the 'codex' server backs the mcp__codex__codex |
  1872	# mcp__codex__codex-reply matchers in settings.json). install_template
  1873	# is idempotent EXISTS->SKIP — an adopter's own .mcp.json is never
  1874	# clobbered. Credentials via ${ENV} expansion only; no secrets on disk.
  1875	# Root-level file => stays inside the WS4-guard-projtmpl maintainer
  1876	# guard (user ceremony writes .claude/ only).
  1877	install_template "templates/.mcp.json" ".mcp.json"
  1878	fi  # WS4-guard-projtmpl
  1879	
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

--- nearby upgrade ---
1538:_refresh_protocol_pointer() {
1857:# _refresh_spec_contract — SPEC/v1 takes a FORCED route, NOT the generic
2019:# _refresh_framework_marker — FORCED + VALIDATED write (r20 option (a)):
2027:_refresh_framework_marker() {
2128:        _up_record_op "refresh_framework_marker" "$(tr -d '[:space:]' < "$src" 2>/dev/null || true)"
3041:  # runs _refresh_protocol_pointer, so _REFRESH_PROTOCOL_CANON_HASH stays
3062:  # _refresh_protocol_pointer sets _PROTOCOL_DELIVERED itself, from the
3066:  _refresh_protocol_pointer
3078:_refresh_framework_marker
3153:  export FMS_DELIVERED_SPEC="${_SPEC_DELIVERED:-0}"
3154:  export FMS_DELIVERED_PROTOCOL="${_PROTOCOL_DELIVERED:-0}"
3155:  export FMS_DELIVERED_MARKER="${_MARKER_DELIVERED:-0}"
3158:  unset FMS_DELIVERED_SPEC FMS_DELIVERED_PROTOCOL FMS_DELIVERED_MARKER

exec
/bin/zsh -lc "nl -ba scripts/install.sh | sed -n '740,820p;1290,1405p;2350,2470p'; printf '\\n--- marker upgrade ---\\n'; nl -ba scripts/upgrade.sh | sed -n '1640,1700p;1835,2150p;3020,3170p'; printf '\\n--- manifest set ---\\n'; nl -ba scripts/_framework_manifest_set.sh | sed -n '100,160p;280,325p'" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
   740	  fi
   741	  if [[ "$INSTALL_SUCCEEDED" -eq 1 ]]; then
   742	    # Success — clean the backup silently.
   743	    if [[ -n "$BACKUP_DIR" && -d "$BACKUP_DIR" ]]; then
   744	      rm -rf "$BACKUP_DIR" 2>/dev/null || true
   745	    fi
   746	    exit "$rc"
   747	  fi
   748	  if [[ $rc -ne 0 && -n "$BACKUP_DIR" && -d "$BACKUP_DIR/.claude" ]]; then
   749	    echo "::error::install failed (rc=$rc) — restoring $TARGET/.claude from $BACKUP_DIR" >&2
   750	    if [[ -d "$TARGET/.claude" ]]; then
   751	      rm -rf "$TARGET/.claude" 2>/dev/null || true
   752	    fi
   753	    mv "$BACKUP_DIR/.claude" "$TARGET/.claude" 2>/dev/null || true
   754	    rm -rf "$BACKUP_DIR" 2>/dev/null || true
   755	    echo "::error::rollback complete — target restored to pre-install state" >&2
   756	  fi
   757	  exit "$rc"
   758	}
   759	trap cleanup_on_failure EXIT
   760	
   761	# ---------------------------------------------------------------------
   762	# PLAN-153 Wave B item B1 — install-state operation journal.
   763	# Each major install operation appends one TAB-separated line
   764	# (op<TAB>detail) to a tempfile OUTSIDE $TARGET; _write_install_state
   765	# folds the journal into .claude/.install-state.json at the end of a
   766	# successful run. Dry-run never creates the journal (the "no files
   767	# modified" promise). Fail-open: journal problems never abort anything.
   768	# ---------------------------------------------------------------------
   769	_STATE_OPS_FILE=""
   770	if [[ "$DRY_RUN" -eq 0 ]]; then
   771	  _STATE_OPS_FILE="$(mktemp "${TMPDIR:-/tmp}/ceo-install-ops.XXXXXX" 2>/dev/null || true)"
   772	fi
   773	_state_record_op() {
   774	  if [[ -n "${_STATE_OPS_FILE:-}" && -f "${_STATE_OPS_FILE:-}" ]]; then
   775	    printf '%s\t%s\n' "$1" "${2:-}" >> "$_STATE_OPS_FILE" 2>/dev/null || true
   776	  fi
   777	  return 0
   778	}
   779	
   780	# ---------------------------------------------------------------------
   781	# PLAN-166 F3 (ADR-155-AMEND-1) — DELIVERY RECORD for the conditional
   782	# framework-ownership surfaces. Each flag flips to 1 ONLY when THIS run
   783	# actually wrote the path (install_one COPIED/LINKED, or the pointer
   784	# heredoc ran) — an EXISTS-skip is NOT a delivery (r17): the pre-existing
   785	# file is the ADOPTER's, and recording it as framework-owned would let the
   786	# baseline hash it, doctor call it drifted, and uninstall delete it.
   787	# write_install_manifest exports these as FMS_DELIVERED_* so the shared
   788	# enumeration (_framework_manifest_set.sh) only records what the framework
   789	# de facto delivered.
   790	# ---------------------------------------------------------------------
   791	_DELIVERED_SPEC=0
   792	_DELIVERED_PROTOCOL=0
   793	_DELIVERED_MARKER=0
   794	
   795	# PLAN-155 Wave 5 — the codex harness helper records its operations through
   796	# this recorder, mapped onto the install-state journal (overrides the helper's
   797	# no-op default so codex emissions land in .claude/.install-state.json).
   798	codex_journal() { _state_record_op "$1" "${2:-}"; }
   799	
   800	if [[ "$DRY_RUN" -eq 0 ]]; then
   801	  if [[ -d "$TARGET/.claude" ]]; then
   802	    BACKUP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/ceo-install-backup.XXXXXX")"
   803	    cp -R "$TARGET/.claude" "$BACKUP_DIR/.claude"
   804	    echo "    SNAPSHOT: $TARGET/.claude -> $BACKUP_DIR/.claude (for rollback)"
   805	  fi
   806	  mkdir -p "$TARGET/.claude"
   807	  # WS4-presnapshot: record pre-existing non-.claude top-level entries so
   808	  # the post-install guard (user ceremony) can detect any CREATE or MODIFY
   809	  # outside .claude/. Snapshot = "name<TAB>size<TAB>mtime" per entry.
   810	  _WS4_PRESNAP=""
   811	  if [[ "$CEREMONY" == "user" ]]; then
   812	    _WS4_PRESNAP="$(mktemp -t ceo-ws4-presnap-XXXXXX)"
   813	    for _ws4_e in "$TARGET"/* "$TARGET"/.[!.]* "$TARGET"/..?*; do
   814	      [[ -e "$_ws4_e" ]] || continue
   815	      _ws4_b="$(basename "$_ws4_e")"
   816	      case "$_ws4_b" in
   817	        .claude|.git) continue ;;
   818	      esac
   819	      if [[ -f "$_ws4_e" ]]; then
   820	        _ws4_sz="$(wc -c < "$_ws4_e" 2>/dev/null | tr -d ' ')"
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
  1386	# ---- 5c.bis Reference personas (PLAN-004 Phase 10) ----
  1387	
  1388	install_reference_personas() {
  1389	  if [[ "$WITH_REFERENCE_PERSONAS" -eq 1 ]]; then
  1390	    echo ""
  1391	    echo "==> Installing reference personas (opt-in)"
  1392	    _state_record_op "install_reference_personas" "opt-in"
  1393	    local src="$SOURCE_DIR/templates/team-personas-reference.md"
  1394	    local dst="$TARGET/.claude/team-personas-reference.md"
  1395	    if [[ "$DRY_RUN" -eq 1 ]]; then
  1396	      if [[ -e "$dst" ]]; then
  1397	        echo "    (dry-run) KEEP (would exist): .claude/team-personas-reference.md"
  1398	      else
  1399	        echo "    (dry-run) would COPY: .claude/team-personas-reference.md"
  1400	      fi
  1401	      return
  1402	    fi
  1403	    if [[ -f "$src" ]]; then
  1404	      if [[ -e "$dst" ]]; then
  1405	        echo "    KEEP (exists): .claude/team-personas-reference.md"
  2350	  if [[ "${_DELIVERED_SPEC:-0}" != "1" ]] && [[ -f "$manifest" ]] \
  2351	     && grep -Eq '^([0-9a-f]{64}|LINK)  SPEC/v1(/|  |$)' "$manifest" 2>/dev/null \
  2352	     && _prior_link_target_matches "$manifest" "SPEC/v1"; then
  2353	    _DELIVERED_SPEC=1
  2354	    _CONTINUITY_FIRED=1
  2355	    _CONTINUITY_PATHS="${_CONTINUITY_PATHS:-}
  2356	SPEC/v1"
  2357	    echo "    ownership continuity: SPEC/v1 delivery record preserved from prior manifest"
  2358	  fi
  2359	  if [[ "${_DELIVERED_PROTOCOL:-0}" != "1" ]] && [[ -f "$manifest" ]] \
  2360	     && grep -Eq '^([0-9a-f]{64}|LINK)  PROTOCOL\.md(  |$)' "$manifest" 2>/dev/null \
  2361	     && _prior_link_target_matches "$manifest" "PROTOCOL.md"; then
  2362	    # FMS_HASH_ROOT does NOT reach PROTOCOL.md: _write_baseline_manifest
  2363	    # special-cases the generated pointer and hashes the TARGET unless
  2364	    # FMS_PROTOCOL_HASH is supplied — which install never set. So a rerun over
  2365	    # a CUSTOMIZED delivered pointer re-baselined the adopter's own bytes as
  2366	    # framework-owned; the next upgrade would then overwrite them and
  2367	    # uninstall could DELETE them (codex W1 round 9, P1). Carry the PRIOR
  2368	    # recorded digest. A LINK record needs none (the rewrite's link branch
  2369	    # fires before the PROTOCOL special case); with neither, DROP the
  2370	    # ownership claim rather than record a knowingly wrong baseline.
  2371	    _PRIOR_PROTOCOL_HASH="$( grep -E '^[0-9a-f]{64}  PROTOCOL\.md$' "$manifest" 2>/dev/null | head -1 | cut -d' ' -f1 || true )"
  2372	    if [[ -n "$_PRIOR_PROTOCOL_HASH" ]] \
  2373	       || grep -Eq '^LINK  PROTOCOL\.md(  |$)' "$manifest" 2>/dev/null; then
  2374	      _DELIVERED_PROTOCOL=1
  2375	      _CONTINUITY_FIRED=1
  2376	      _CONTINUITY_PATHS="${_CONTINUITY_PATHS:-}
  2377	PROTOCOL.md"
  2378	      echo "    ownership continuity: PROTOCOL.md delivery record preserved from prior manifest"
  2379	    else
  2380	      echo "    NOTE: PROTOCOL.md record present but its digest is unrecoverable —" >&2
  2381	      echo "          ownership NOT claimed (the pointer stays adopter-owned)" >&2
  2382	    fi
  2383	  fi
  2384	  if [[ "${_DELIVERED_MARKER:-0}" != "1" ]] && [[ -f "$manifest" ]] \
  2385	     && grep -Eq '^([0-9a-f]{64}|LINK)  \.claude/\.framework-version(  |$)' "$manifest" 2>/dev/null \
  2386	     && _prior_link_target_matches "$manifest" ".claude/.framework-version"; then
  2387	    _DELIVERED_MARKER=1
  2388	    _CONTINUITY_FIRED=1
  2389	    _CONTINUITY_PATHS="${_CONTINUITY_PATHS:-}
  2390	.claude/.framework-version"
  2391	    echo "    ownership continuity: .framework-version delivery record preserved from prior manifest"
  2392	  fi
  2393	  # For the continuity-preserved paths ONLY, hash the FRAMEWORK's pristine
  2394	  # copies instead of the (possibly edited) target's (codex W1 round 5, P1):
  2395	  # install normally hashes FMS_ROOT=$TARGET — on a rerun over an EDITED
  2396	  # delivered SPEC that would re-baseline the fork's bytes as framework-owned,
  2397	  # and a later uninstall would happily DELETE the user's modified tree (its
  2398	  # hash matches the manifest). Same C.5 idempotency posture upgrade.sh uses.
  2399	  #
  2400	  # SCOPED, not global (codex W1 round 8, P1): install RENDERS templates
  2401	  # (`.claude/team.md`, skills, `{{X}}` placeholders under --project et al),
  2402	  # so a global FMS_HASH_ROOT rewrote every rendered file's baseline to the
  2403	  # UNRENDERED source — doctor.sh then reports repo-wide adopter drift and
  2404	  # later upgrades classify those files as customized and stop refreshing
  2405	  # them. PLAN-167 W2.3 replaced that confinement with an EXPLICIT per-surface
  2406	  # hash_source: the decision says which paths take the framework's bytes,
  2407	  # so no global override is set here at all.
  2408	  if [[ "${_CONTINUITY_FIRED:-0}" = "1" ]]; then
  2409	    : # per-surface hash_source below replaces the global override
  2410	    case "$_CONTINUITY_PATHS" in
  2411	      *".claude/.framework-version"*) export FMS_HASH_SOURCE_MARKER="HASH_SOURCE" ;;
  2412	    esac
  2413	    case "$_CONTINUITY_PATHS" in
  2414	      # The generated pointer has no source bytes; carry what was recorded.
  2415	      *"PROTOCOL.md"*)               export FMS_HASH_SOURCE_PROTOCOL="HASH_PRIOR_RECORD" ;;
  2416	    esac
  2417	    echo "    ownership continuity: manifest hashes the preserved paths from the framework source (edited target content stays adopter-owned; rendered files keep their target hash)"
  2418	  fi
  2419	  # Declare on EVERY delivery path, not only continuity. A fresh install
  2420	  # genuinely delivers these surfaces, and the previous attempt at this wave
  2421	  # regressed 24 cells precisely because it left fresh installs undeclared.
  2422	  #
  2423	  # Fresh delivery: the target IS the bytes just written, so HASH_TARGET is
  2424	  # both correct and observationally identical to HASH_SOURCE.
  2425	  # Continuity: the target may be an EDITED fork, so the record must come from
  2426	  # the framework's copy (spec/marker) or the prior record (the generated
  2427	  # pointer, which has no source file).
  2428	  export FMS_SOURCE_ROOT="$SOURCE_DIR"
  2429	  export FMS_PRIOR_MANIFEST="$manifest"
  2430	  if [[ "${_DELIVERED_SPEC:-0}" = "1" ]]; then
  2431	    case "${_CONTINUITY_PATHS:-}" in
  2432	      *"SPEC/v1"*) export FMS_HASH_SOURCE_SPEC="HASH_SOURCE" ;;
  2433	      *)           export FMS_HASH_SOURCE_SPEC="HASH_TARGET" ;;
  2434	    esac
  2435	  fi
  2436	  if [[ "${_DELIVERED_MARKER:-0}" = "1" ]]; then
  2437	    case "${_CONTINUITY_PATHS:-}" in
  2438	      *".claude/.framework-version"*) export FMS_HASH_SOURCE_MARKER="HASH_SOURCE" ;;
  2439	      *)                              export FMS_HASH_SOURCE_MARKER="HASH_TARGET" ;;
  2440	    esac
  2441	  fi
  2442	  if [[ "${_DELIVERED_PROTOCOL:-0}" = "1" ]]; then
  2443	    case "${_CONTINUITY_PATHS:-}" in
  2444	      *"PROTOCOL.md"*) export FMS_HASH_SOURCE_PROTOCOL="HASH_PRIOR_RECORD" ;;
  2445	      *)               export FMS_HASH_SOURCE_PROTOCOL="HASH_TARGET" ;;
  2446	    esac
  2447	  fi
  2448	  export FMS_DELIVERED_SPEC="${_DELIVERED_SPEC:-0}"
  2449	  export FMS_DELIVERED_PROTOCOL="${_DELIVERED_PROTOCOL:-0}"
  2450	  export FMS_DELIVERED_MARKER="${_DELIVERED_MARKER:-0}"
  2451	  # Empty on a fresh install (target IS the freshly written pointer, hashing it
  2452	  # is correct); set only by the continuity path above.
  2453	  export FMS_PROTOCOL_HASH="${_PRIOR_PROTOCOL_HASH:-}"
  2454	  _write_baseline_manifest "$manifest"
  2455	  unset FMS_ROOT FMS_PROFILE_PARTS FMS_MODE FMS_HASH_ROOT FMS_PROTOCOL_HASH \
  2456	        FMS_PRIOR_MANIFEST FMS_HASH_SOURCE_SPEC FMS_HASH_SOURCE_PROTOCOL \
  2457	        FMS_HASH_SOURCE_MARKER
  2458	  unset FMS_DELIVERED_SPEC FMS_DELIVERED_PROTOCOL FMS_DELIVERED_MARKER
  2459	  return 0
  2460	}
  2461	
  2462	
  2463	# ----------------------------------------------------------------------
  2464	# PLAN-153 Wave B item B1 — persist the install-state.
  2465	# ----------------------------------------------------------------------
  2466	# Writes $TARGET/.claude/.install-state.json (next to the ADR-155 baseline
  2467	# manifest): the ORIGINAL request — verbatim argv + every parsed flag + the
  2468	# RESOLVED placeholder map (CLI > env > deterministic default; empty values
  2469	# omitted) — plus the operation journal for THIS run.
  2470	#

--- marker upgrade ---
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
  3020	# customized values are always PRESERVED with a named WARNING.
  3021	_migrate_settings_baseline
  3022	
  3023	# DevOps-P1-4: PROTOCOL.md is framework-derived (pointer), not user data —
  3024	# refresh it so it stays aligned with the current source layout.
  3025	# PLAN-166 F3 (ADR-155-AMEND-1): CEREMONY-GATED — the refresh used to run
  3026	# unconditionally and `cat >`-created a root PROTOCOL.md that a
  3027	# `--ceremony user` install deliberately never has (install.sh
  3028	# WS4-guard-proto forbids root files); the F4 tree-comparison e2e exposes
  3029	# exactly this divergence (r7/r13). The gate reads the ceremony from
  3030	# .claude/.install-state.json via the replay-independent reader above.
  3031	_PROTOCOL_DELIVERED=0
  3032	echo ""
  3033	echo "==> Refreshing PROTOCOL.md pointer"
  3034	if [[ "$CEREMONY_EFFECTIVE" == "user" ]]; then
  3035	  echo "    SKIP: PROTOCOL.md pointer (recorded --ceremony user install — a user install never creates root files, WS4; r13)"
  3036	  # Ownership continuity on the analogous skip (codex W1 round 7, P2) — see
  3037	  # the SPEC/v1 ceremony skip: preserving the tree while erasing its record
  3038	  # strands a framework-delivered pointer as unowned.
  3039	  #
  3040	  # But the flag alone is NOT enough (codex W1 round 9, P1): this skip never
  3041	  # runs _refresh_protocol_pointer, so _REFRESH_PROTOCOL_CANON_HASH stays
  3042	  # empty, and _write_baseline_manifest then hashes the LIVE pointer —
  3043	  # re-recording an adopter-CUSTOMIZED PROTOCOL.md as the framework baseline,
  3044	  # which the next upgrade overwrites and uninstall can DELETE. Retaining
  3045	  # ownership must never retain the wrong bytes. Carry the PRIOR canonical
  3046	  # digest; a LINK record needs none (the link branch of the rewrite fires
  3047	  # before the PROTOCOL special case). When neither is available, DROP the
  3048	  # claim — the pointer stays adopter-owned and preserved, which is the
  3049	  # pre-continuity behaviour and loses nothing.
  3050	  if _baseline_has_protocol_record; then
  3051	    _REFRESH_PROTOCOL_CANON_HASH="$( _baseline_lookup "PROTOCOL.md" 2>/dev/null || true )"
  3052	    if [[ -n "$_REFRESH_PROTOCOL_CANON_HASH" ]] \
  3053	       || grep -Eq '^LINK  PROTOCOL\.md(  |$)' "$_BASELINE_MANIFEST_FILE" 2>/dev/null; then
  3054	      _PROTOCOL_DELIVERED=1
  3055	    else
  3056	      echo "    NOTE: PROTOCOL.md delivery record present but its canonical digest is" >&2
  3057	      echo "          unrecoverable (ambiguous record) — ownership NOT claimed; the" >&2
  3058	      echo "          pointer stays adopter-owned and preserved" >&2
  3059	    fi
  3060	  fi
  3061	else
  3062	  # _refresh_protocol_pointer sets _PROTOCOL_DELIVERED itself, from the
  3063	  # VERDICT. Forcing it to 1 here overrode a PRESERVE_UNOWNED decision and
  3064	  # recorded an adopter's own pre-existing PROTOCOL.md as framework-owned —
  3065	  # a caller computing the right answer and then ignoring it (codex W3 r1 P1).
  3066	  _refresh_protocol_pointer
  3067	fi
  3068	
  3069	# PLAN-166 F3 (ADR-155-AMEND-1): SPEC/v1 forced refresh + framework version
  3070	# marker. Both run BEFORE the baseline-manifest rewrite so the delivery
  3071	# flags they set are what the rewritten baseline records.
  3072	echo ""
  3073	echo "==> Refreshing SPEC/v1 contract (PLAN-166 F3 — forced route)"
  3074	_refresh_spec_contract
  3075	
  3076	echo ""
  3077	echo "==> Refreshing framework version marker (.claude/.framework-version)"
  3078	_refresh_framework_marker
  3079	
  3080	# PLAN-161 U3 — mis-install scan/purge. Runs in ALL modes (flag-absent and
  3081	# --dry-run runs emit the would-purge PREVIEW; deletion requires the explicit
  3082	# --purge-misinstalled flag AND a non-dry run). Runs BEFORE the baseline-
  3083	# manifest rewrite below so a purged path is never re-recorded.
  3084	echo ""
  3085	echo "==> Scanning excluded trees for mis-installed framework-internal files (PLAN-161 U3)"
  3086	_purge_misinstalled_scan
  3087	
  3088	# PLAN-138 Wave C (ADR-155) C.7 — (re)write the baseline manifest AFTER a
  3089	# successful upgrade, so a long-lived adopter who upgrades but never re-runs
  3090	# install.sh (the S238 acme population) acquires/refreshes a manifest. The
  3091	# NEXT upgrade then runs the manifest-present per-file classified path instead
  3092	# of the fallback. Uses the SAME shared generator install.sh calls. Skipped on
  3093	# --dry-run; fail-open (a generator problem emits a NOTE, never aborts).
  3094	if [[ "$DRY_RUN" -eq 0 ]] && command -v _write_baseline_manifest >/dev/null 2>&1; then
  3095	  echo ""
  3096	  echo "==> (Re)writing install baseline manifest (.claude/.install-manifest.sha256)"
  3097	  _up_record_op "rewrite_baseline_manifest" ".claude/.install-manifest.sha256"
  3098	  export FMS_ROOT="$TARGET"            # enumerate what the target holds post-upgrade
  3099	  export FMS_HASH_ROOT="$SOURCE_DIR"   # but record the FRAMEWORK hash, not the
  3100	                                       # (possibly customized-and-preserved) target
  3101	                                       # file — else the next upgrade clobbers it
  3102	                                       # (C.5 idempotency fix). PROTOCOL.md pointer
  3103	                                       # still hashes from FMS_ROOT inside the gen.
  3104	  export FMS_PROFILE_PARTS="${PROFILE_PARTS[*]}"
  3105	  # FMS_MODE mirrors the INSTALL's mode, not the upgrade's copy behavior
  3106	  # (codex W1-ceremony round, P2): on a --mode link target the refresh
  3107	  # branches preserve the symlinks, but a `copy`-mode rewrite would OMIT
  3108	  # the SPEC/v1 directory-LINK record and hash the marker symlink as a
  3109	  # file — doctor.sh then reports a type-change drift on a healthy tree.
  3110	  # Evidence order: prior baseline LINK record (authoritative), else a
  3111	  # symlink probe on the framework-owned roots, else copy.
  3112	  FMS_MODE="copy"
  3113	  if [[ -n "$_BASELINE_MANIFEST_FILE" && -f "$_BASELINE_MANIFEST_FILE" ]] \
  3114	     && grep -Eq '^LINK  ' "$_BASELINE_MANIFEST_FILE" 2>/dev/null; then
  3115	    FMS_MODE="link"
  3116	    # Confine LINK serialization to the paths that ALREADY were LINK records
  3117	    # (codex W1 round 10, P2). Without this, inferring link-mode from the
  3118	    # prior manifest also promoted every OTHER live symlink — e.g. an
  3119	    # adopter's own file under `.claude/hooks/` — into a framework delivery
  3120	    # record. The probe branch below leaves FMS_LINK_PATHS unset (no baseline
  3121	    # to derive from), keeping its pre-existing behaviour.
  3122	    FMS_LINK_PATHS="$( awk '
  3123	      {
  3124	        idx = index($0, "  ");
  3125	        if (idx == 0) next;
  3126	        if (substr($0, 1, idx - 1) != "LINK") next;
  3127	        rest = substr($0, idx + 2);
  3128	        j = index(rest, "  ");
  3129	        print (j == 0 ? rest : substr(rest, 1, j - 1));
  3130	      }' "$_BASELINE_MANIFEST_FILE" 2>/dev/null || true )"
  3131	    export FMS_LINK_PATHS
  3132	    echo "    baseline rewrite: --mode link install detected (LINK records in prior manifest) — preserving LINK serialization for $( printf '%s\n' "$FMS_LINK_PATHS" | grep -c . || true ) recorded path(s)"
  3133	  elif [[ -L "$TARGET/.claude/skills" || -L "$TARGET/SPEC/v1" || -L "$TARGET/.claude/.framework-version" ]]; then
  3134	    FMS_MODE="link"
  3135	    echo "    baseline rewrite: --mode link install detected (symlink probe) — preserving LINK serialization"
  3136	  fi
  3137	  export FMS_MODE
  3138	  # Canonical PROTOCOL.md pointer hash (Codex R2 P0): record what the framework
  3139	  # WOULD generate, never a preserved adopter customization. Empty if the
  3140	  # pointer refresh did not run; the generator then falls back to hashing the
  3141	  # target (install semantics).
  3142	  export FMS_PROTOCOL_HASH="${_REFRESH_PROTOCOL_CANON_HASH:-}"
  3143	  # PLAN-166 F3 (ADR-155-AMEND-1): conditional ownership from what THIS
  3144	  # upgrade delivered/refreshed (or what the pre-upgrade baseline already
  3145	  # recorded — ownership continuity), never the ceremony alone, never file
  3146	  # presence (r17/r19/r20).
  3147	  # The decision travels with the delivery flag.
  3148	  export FMS_SOURCE_ROOT="$SOURCE_DIR"
  3149	  export FMS_PRIOR_MANIFEST="${_BASELINE_MANIFEST_FILE:-}"
  3150	  export FMS_HASH_SOURCE_SPEC="${_SPEC_HASH_SOURCE:-}"
  3151	  export FMS_HASH_SOURCE_MARKER="${_MARKER_HASH_SOURCE:-}"
  3152	  export FMS_HASH_SOURCE_PROTOCOL="${_PROTOCOL_HASH_SOURCE:-}"
  3153	  export FMS_DELIVERED_SPEC="${_SPEC_DELIVERED:-0}"
  3154	  export FMS_DELIVERED_PROTOCOL="${_PROTOCOL_DELIVERED:-0}"
  3155	  export FMS_DELIVERED_MARKER="${_MARKER_DELIVERED:-0}"
  3156	  _write_baseline_manifest "$TARGET/.claude/.install-manifest.sha256"
  3157	  unset FMS_ROOT FMS_HASH_ROOT FMS_PROFILE_PARTS FMS_MODE FMS_PROTOCOL_HASH FMS_LINK_PATHS
  3158	  unset FMS_DELIVERED_SPEC FMS_DELIVERED_PROTOCOL FMS_DELIVERED_MARKER
  3159	fi
  3160	
  3161	# ===========================================================================
  3162	# PLAN-153 Wave B item B2 — (re)write the install-state after a successful
  3163	# upgrade, mirroring the ADR-155 decision-(iv) manifest rewrite above: a
  3164	# pre-Wave-B adopter (no state file) ACQUIRES one on their first post-Wave-B
  3165	# upgrade, so the NEXT upgrade can replay. Merge semantics preserve the
  3166	# ORIGINAL install request (argv, mode, ceremony, placeholders map) and only
  3167	# update the replayable fields (request.profile/request.stack) to the values
  3168	# THIS run effectively used; the upgrade run itself is recorded under
  3169	# last_upgrade + history. Atomic (same-directory tempfile + os.replace),
  3170	# schema ceo.install-state/v1, fail-open (a write problem emits a NOTE and

--- manifest set ---
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

exec
/bin/zsh -lc 'for f in INSTALL.md README.md README.pt-BR.md RELEASE.md docs/ARCHITECTURE.md docs/CTO-GUIDE.md docs/FAQ.md docs/GUIA-COMPLETO.md docs/README.md npm/README.md; do echo "===== $f ====="; git diff --unified=20 -- "$f"; done' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 110ms:
diff --git a/npm/README.md b/npm/README.md
index 9203de5..a19a95f 100644
--- a/npm/README.md
+++ b/npm/README.md
@@ -39,41 +39,41 @@ When installed, the framework registers a set of [Claude Code hooks](https://doc
 
 **2. Tamper-evident audit log.** Every governed event appends one JSONL line to a local audit log, each entry HMAC-chained to the previous one. A `verify_chain()` routine walks the log and reports the first break. This **detects tampering** — a removed or edited entry breaks the chain — but it does not *prove* the absence of tampering, and it is a local control, not a notarization service. Treat it as an integrity tripwire, not a court exhibit.
 
 **3. Cross-model pair-rail.** When an agent tries to edit a canonical (protected) path, a hook routes the proposed change to a second model for read-only review. If that reviewer returns anything write-shaped, the edit is blocked. The honest caveat: the default reviewer is another large language model, and same-class reviewers share blind spots (see *Risks*).
 
 **4. Skill checklists.** The framework ships **166 skill files** — reusable, domain-specific checklists (security review, audit fan-out, onboarding to an unfamiliar codebase, and so on) that an agent loads when relevant instead of reinventing the steps each time.
 
 ---
 
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
 
 **Prerequisites:** Python ≥ 3.9, Git, and Bash. On macOS the system Bash is 3.2; install a modern one with `brew install bash` before installing.
 
 ```bash
 # 1. Clone the framework somewhere outside your project
 git clone https://github.com/Canhada-Labs/ceo-orchestration.git
 cd ceo-orchestration
 
 # 2. Install it INTO your target repository
@@ -102,41 +102,41 @@ To verify the safety guards actually block what they claim, run the in-process s
 ```bash
 # from inside your installed project, in Claude Code
 /self-test
 ```
 
 To remove the framework cleanly:
 
 ```bash
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
 - **Per-edit overhead.** Each governed tool call runs the hook chain before the action lands, adding roughly **~0.3–1.0s** of latency per edit on typical hardware. That is the cost of the gate; if you want zero overhead on routine work, the governance layer is not free.
 - **A gate can be wrong — there is an escape hatch.** Hooks fail *open* on their own infrastructure bugs, but a correct gate can still issue a DENY you disagree with (a false block on a protected path). The intended path is `/architect` (which routes the change through review) or, for a structural framework change, a PLAN-NNN with an Owner-signed sentinel (a GPG-signed approval record that authorizes a specific protected-path edit). For a deliberate, *audited* override of the canonical-edit gate, the Owner can set `CEO_SENTINEL_UNLOCK=<plan-id>` + `CEO_SENTINEL_UNLOCK_ACK=I-ACCEPT` for that action — the override itself is logged. (Because that window removes the signature check, the sentinel used inside it must also prove it is not one the agent wrote; the block reason names the value to set, and ADR-119 Invariant 5 explains both forms.) Kernel-path hard-denies (an unconditional block on the most safety-critical files, which no sentinel can lift) need the stronger `CEO_KERNEL_OVERRIDE` ceremony. See [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md). To trial the framework without any of this friction, install with `--ceremony user` (advisory hooks, no signing).
 - **Detection, not prevention, on the audit chain.** The HMAC chain tells you *that* the recorded log was altered; it cannot prevent an attacker with local write access from doing damage, and it is not a substitute for proper access controls or backups.
 - **Formal verification is scoped, not universal.** A TLA+ specification exists for the core state machine, but model-checking is **not** part of the enforcing CI gate — do not read "has a TLA+ spec" as "formally verified." The overwhelming majority of behavior is covered by conventional tests, not mechanized proof.
 - **It is a framework, not a product.** No UI, no managed runtime, no "operating system." It installs into your repo and gets out of the way.
 - **No speed benefit.** Restated because it matters: this will not make your agent faster.
 
 **Alternatives worth comparing** if multi-agent orchestration (rather than governance) is your goal: [AutoGen](https://github.com/microsoft/autogen), [MetaGPT](https://github.com/geekan/MetaGPT), and [LangGraph](https://github.com/langchain-ai/langgraph). Those optimize for agent collaboration and workflow expressiveness; this project optimizes for *gating and auditing* a single capable agent's changes to a real repository.

exec
/bin/zsh -lc "find .claude/adr -maxdepth 1 -name 'ADR-*.md' | wc -l; ls .claude/adr | grep -c '"'^ADR-'"'; git diff --name-only | wc -l; python3 .claude/scripts/check-claude-md-claims.py; python3 .claude/scripts/check-agents-md.py" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
     189
189
      25
OK: AGENTS.md fresh — 52 listed path(s) all exist.

exec
/bin/zsh -lc "cat .claude/governance/npm-trusted-publisher.txt; printf '\\n--- ADR headings ---\\n'; sed -n '1,300p' .claude/adr/ADR-155-AMEND-1-delivery-record-ownership.md; printf '\\n--- plan draft diff ---\\n'; git diff --unified=30 -- .claude/plans/PLAN-166/W1-approved-draft.md .claude/plans/PLAN-166/staged-manifest.sha256" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
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

--- ADR headings ---
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

--- plan draft diff ---
diff --git a/.claude/plans/PLAN-166/W1-approved-draft.md b/.claude/plans/PLAN-166/W1-approved-draft.md
index 17bd644..cf50f43 100644
--- a/.claude/plans/PLAN-166/W1-approved-draft.md
+++ b/.claude/plans/PLAN-166/W1-approved-draft.md
@@ -167,46 +167,47 @@ Commit subject tag: `[SENT-PLAN166-W1]`.
 ## Scope
 
 Scope:
 
 Release train (revert group A):
   - .claude/governance/npm-trusted-publisher.txt
   - .claude/governance/pair-rail-verdict-template.md
   - .claude/scripts/tests/test_release_workflow_asserts.py
   - .github/workflows/npm-publish.yml
   - .github/workflows/release.yml
   - RELEASE.md
 
 Adopter upgrade + ADR + count sweep (revert group B):
   - .claude/.framework-version
   - .claude/adr/ADR-155-AMEND-1-delivery-record-ownership.md
   - .claude/scripts/check-framework-updates.sh
   - .github/workflows/smoke-install.yml
   - CLAUDE.md
   - INSTALL.md
   - README.md
   - README.pt-BR.md
   - docs/ARCHITECTURE.md
   - docs/CTO-GUIDE.md
   - docs/FAQ.md
   - docs/GUIA-COMPLETO.md
   - docs/README.md
   - npm/README.md
   - scripts/_framework_manifest_set.sh
   - scripts/doctor.sh
   - scripts/install.sh
+  - scripts/tests/_parity_classify.py
   - scripts/tests/test-upgrade-spec-ownership.sh
   - scripts/upgrade.sh
 
 ---
 
 ## Adendo (2026-08-06, pré-assinatura — CEO)
 
 **15º patch adicionado ao pack:** o template do verdito
 (`pair-rail-verdict-template.md`, canônico em governance) ganha os 3
 campos que o guard novo EXIGE de todo verdito (`delta_allowlist` /
 `delta_manifest` / `delta_manifest_sha256`) + seção "tag() guard
 semantics". Sem isso, o primeiro verdito de rc.2 autorado a partir do
 template morre em E_VERDICT (achado P2 do round 1 da refutação; o
 template é canônico e por isso entra na cerimônia, não no W0).
 **Scope: adicionar este path ao grupo A (trem de release).**
 Manifesto regenerado: 32 entradas (template staged + patch novo).
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
/bin/zsh -lc "find .claude/plans/PLAN-166/archive .claude/plans/PLAN-168/archive -maxdepth 2 -type f -print0 2>/dev/null | xargs -0 ls -lh; printf '\\n--- top-level untracked scripts/docs sizes ---\\n'; ls -lh .claude/plans/PLAN-166/OWNER-W1-LAND-step1.sh .claude/plans/PLAN-166/W1-ceremony-log.md .claude/plans/PLAN-166/architect/round-1/approved.md.asc .claude/plans/PLAN-167/OWNER-PREPARE-TO-SIGN.sh .claude/plans/PLAN-167/W4-approved.md .claude/plans/PLAN-167/W4-approved.md.asc; printf '\\n--- file types ---\\n'; file "'$(git ls-files --others --exclude-standard | tr '"'\\n' ' ')" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
-rw-r--r--@ 1 joaocanhada  staff   1.1K Aug  6 14:30 .claude/plans/PLAN-166/archive/ceremony-porcelain-20260806-1430.txt
-rw-r--r--@ 1 joaocanhada  staff   175K Aug  6 14:30 .claude/plans/PLAN-166/archive/ceremony-worktree-20260806-1430.diff
-rw-r--r--@ 1 joaocanhada  staff   335K Aug  7 21:01 .claude/plans/PLAN-166/archive/codex-r6-2059.md
-rw-r--r--@ 1 joaocanhada  staff   1.3K Aug  6 14:30 .claude/plans/PLAN-166/archive/codex-review-sentinel.md
-rw-r--r--@ 1 joaocanhada  staff   1.2K Aug  6 14:30 .claude/plans/PLAN-166/archive/codex-review-w0-residuals.md
-rw-r--r--@ 1 joaocanhada  staff   2.1K Aug  6 14:30 .claude/plans/PLAN-166/archive/codex-review-w1-ceremony.md
-rw-r--r--@ 1 joaocanhada  staff   2.6K Aug  6 18:28 .claude/plans/PLAN-166/archive/codex-review-w1-round10.md
-rw-r--r--@ 1 joaocanhada  staff   2.5K Aug  6 20:14 .claude/plans/PLAN-166/archive/codex-review-w1-round11.md
-rw-r--r--@ 1 joaocanhada  staff   1.8K Aug  6 14:30 .claude/plans/PLAN-166/archive/codex-review-w1-round2.md
-rw-r--r--@ 1 joaocanhada  staff   1.3K Aug  6 14:30 .claude/plans/PLAN-166/archive/codex-review-w1-round3.md
-rw-r--r--@ 1 joaocanhada  staff   2.8K Aug  6 14:30 .claude/plans/PLAN-166/archive/codex-review-w1-round4.md
-rw-r--r--@ 1 joaocanhada  staff   2.1K Aug  6 14:30 .claude/plans/PLAN-166/archive/codex-review-w1-round5.md
-rw-r--r--@ 1 joaocanhada  staff   852B Aug  6 15:54 .claude/plans/PLAN-166/archive/codex-review-w1-round6.md
-rw-r--r--@ 1 joaocanhada  staff   2.1K Aug  6 16:13 .claude/plans/PLAN-166/archive/codex-review-w1-round7.md
-rw-r--r--@ 1 joaocanhada  staff   2.1K Aug  6 17:13 .claude/plans/PLAN-166/archive/codex-review-w1-round8.md
-rw-r--r--@ 1 joaocanhada  staff   2.5K Aug  6 17:37 .claude/plans/PLAN-166/archive/codex-review-w1-round9.md
-rw-r--r--@ 1 joaocanhada  staff   1.7K Aug  6 19:43 .claude/plans/PLAN-166/archive/mirror-fixes.sh
-rw-r--r--@ 1 joaocanhada  staff   218K Aug  6 01:59 .claude/plans/PLAN-166/archive/w1-staged-pack-20260806-0159.tar.gz
-rw-r--r--@ 1 joaocanhada  staff   226K Aug  6 07:22 .claude/plans/PLAN-166/archive/w1-staged-pack-final-20260806-0722.tar.gz
-rw-r--r--@ 1 joaocanhada  staff    34K Aug  7 20:48 .claude/plans/PLAN-168/archive/0001-plan168-W1-CI-wiring-dos-or-culos-de-propriedade.patch
-rw-r--r--@ 1 joaocanhada  staff    71K Aug  7 20:48 .claude/plans/PLAN-168/archive/0002-plan168-W2-W3-INV-4-curada-pelo-gerador-nico-ADR-190.patch
-rw-r--r--@ 1 joaocanhada  staff   3.4K Aug  7 20:48 .claude/plans/PLAN-168/archive/0003-plan168-baseline-map-re-gravado-62-GREEN-3-RED-run-2.patch
-rw-r--r--@ 1 joaocanhada  staff   8.4K Aug  7 20:48 .claude/plans/PLAN-168/archive/full-e2e-20260807-2017.log
-rw-r--r--@ 1 joaocanhada  staff    97K Aug  7 20:48 .claude/plans/PLAN-168/archive/pack-full.diff

--- top-level untracked scripts/docs sizes ---
-rwxr-xr-x@ 1 joaocanhada  staff   4.1K Aug  6 17:16 .claude/plans/PLAN-166/OWNER-W1-LAND-step1.sh
-rw-r--r--@ 1 joaocanhada  staff    11K Aug  6 17:30 .claude/plans/PLAN-166/W1-ceremony-log.md
-rw-r--r--@ 1 joaocanhada  staff   265B Aug  6 13:42 .claude/plans/PLAN-166/architect/round-1/approved.md.asc
-rwxr-xr-x@ 1 joaocanhada  staff   2.5K Aug  7 16:37 .claude/plans/PLAN-167/OWNER-PREPARE-TO-SIGN.sh
-rw-r--r--@ 1 joaocanhada  staff   5.0K Aug  7 16:38 .claude/plans/PLAN-167/W4-approved.md
-rw-r--r--@ 1 joaocanhada  staff   265B Aug  7 16:38 .claude/plans/PLAN-167/W4-approved.md.asc

--- file types ---
.claude/plans/PLAN-166/OWNER-W1-LAND-step1.sh:                                                  Bourne-Again shell script text executable, Unicode text, UTF-8 text
.claude/plans/PLAN-166/W1-ceremony-log.md:                                                      Unicode text, UTF-8 text
.claude/plans/PLAN-166/architect/round-1/approved.md.asc:                                       PGP signature Signature (old)
.claude/plans/PLAN-166/archive/ceremony-porcelain-20260806-1430.txt:                            ASCII text
.claude/plans/PLAN-166/archive/ceremony-worktree-20260806-1430.diff:                            unified diff output text, Unicode text, UTF-8 text, with very long lines (467)
.claude/plans/PLAN-166/archive/codex-r6-2059.md:                                                Unicode text, UTF-8 text
.claude/plans/PLAN-166/archive/codex-review-sentinel.md:                                        Unicode text, UTF-8 text, with very long lines (433)
.claude/plans/PLAN-166/archive/codex-review-w0-residuals.md:                                    Unicode text, UTF-8 text, with very long lines (359)
.claude/plans/PLAN-166/archive/codex-review-w1-ceremony.md:                                     Unicode text, UTF-8 text, with very long lines (569)
.claude/plans/PLAN-166/archive/codex-review-w1-round10.md:                                      Unicode text, UTF-8 text, with very long lines (513)
.claude/plans/PLAN-166/archive/codex-review-w1-round11.md:                                      Unicode text, UTF-8 text, with very long lines (468)
.claude/plans/PLAN-166/archive/codex-review-w1-round2.md:                                       Unicode text, UTF-8 text, with very long lines (417)
.claude/plans/PLAN-166/archive/codex-review-w1-round3.md:                                       Unicode text, UTF-8 text, with very long lines (490)
.claude/plans/PLAN-166/archive/codex-review-w1-round4.md:                                       Unicode text, UTF-8 text, with very long lines (474)
.claude/plans/PLAN-166/archive/codex-review-w1-round5.md:                                       Unicode text, UTF-8 text, with very long lines (504)
.claude/plans/PLAN-166/archive/codex-review-w1-round6.md:                                       Unicode text, UTF-8 text, with very long lines (515)
.claude/plans/PLAN-166/archive/codex-review-w1-round7.md:                                       Unicode text, UTF-8 text, with very long lines (579)
.claude/plans/PLAN-166/archive/codex-review-w1-round8.md:                                       Unicode text, UTF-8 text, with very long lines (565)
.claude/plans/PLAN-166/archive/codex-review-w1-round9.md:                                       Unicode text, UTF-8 text, with very long lines (461)
.claude/plans/PLAN-166/archive/mirror-fixes.sh:                                                 Bourne-Again shell script text executable, Unicode text, UTF-8 text
.claude/plans/PLAN-166/archive/w1-staged-pack-20260806-0159.tar.gz:                             gzip compressed data, last modified: Thu Aug  6 04:59:14 2026, from Unix, original size modulo 2^32 817152
.claude/plans/PLAN-166/archive/w1-staged-pack-final-20260806-0722.tar.gz:                       gzip compressed data, last modified: Thu Aug  6 10:22:20 2026, from Unix, original size modulo 2^32 845312
.claude/plans/PLAN-167/OWNER-PREPARE-TO-SIGN.sh:                                                Bourne-Again shell script text executable, Unicode text, UTF-8 text
.claude/plans/PLAN-167/W4-approved.md:                                                          Unicode text, UTF-8 text
.claude/plans/PLAN-167/W4-approved.md.asc:                                                      PGP signature Signature (old)
.claude/plans/PLAN-168/archive/0001-plan168-W1-CI-wiring-dos-or-culos-de-propriedade.patch:     unified diff output text, Unicode text, UTF-8 text
.claude/plans/PLAN-168/archive/0002-plan168-W2-W3-INV-4-curada-pelo-gerador-nico-ADR-190.patch: unified diff output text, Unicode text, UTF-8 text, with very long lines (1513)
.claude/plans/PLAN-168/archive/0003-plan168-baseline-map-re-gravado-62-GREEN-3-RED-run-2.patch: unified diff output text, ASCII text
.claude/plans/PLAN-168/archive/full-e2e-20260807-2017.log:                                      ASCII text
.claude/plans/PLAN-168/archive/pack-full.diff:                                                  unified diff output text, Unicode text, UTF-8 text, with very long lines (1513)

exec
/bin/zsh -lc 'bash .claude/scripts/check-contamination.sh' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 exited 1 in 681ms:
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
/bin/zsh -lc 'export PYTHONDONTWRITEBYTECODE=1; bash -n .claude/scripts/check-framework-updates.sh scripts/doctor.sh scripts/tests/test-upgrade-spec-ownership.sh .claude/plans/PLAN-166/OWNER-W1-LAND-step1.sh .claude/plans/PLAN-167/OWNER-PREPARE-TO-SIGN.sh; python3 -m unittest .claude/scripts/tests/test_release_workflow_asserts.py' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 exited 1 in 0ms:
Traceback (most recent call last):
  File "/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/runpy.py", line 197, in _run_module_as_main
    return _run_code(code, main_globals, None,
  File "/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/runpy.py", line 87, in _run_code
    exec(code, run_globals)
  File "/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/unittest/__main__.py", line 18, in <module>
    main(module=None)
  File "/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/unittest/main.py", line 100, in __init__
    self.parseArgs(argv)
  File "/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/unittest/main.py", line 147, in parseArgs
    self.createTests()
  File "/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/unittest/main.py", line 158, in createTests
    self.test = self.testLoader.loadTestsFromNames(self.testNames,
  File "/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/unittest/loader.py", line 220, in loadTestsFromNames
    suites = [self.loadTestsFromName(name, module) for name in names]
  File "/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/unittest/loader.py", line 220, in <listcomp>
    suites = [self.loadTestsFromName(name, module) for name in names]
  File "/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/lib/python3.9/unittest/loader.py", line 154, in loadTestsFromName
    module = __import__(module_name)
ValueError: Empty module name

exec
/bin/zsh -lc 'export PYTHONDONTWRITEBYTECODE=1; python3 .claude/scripts/tests/test_release_workflow_asserts.py' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 314ms:
...........................................
----------------------------------------------------------------------
Ran 52 tests in 0.294s

OK

exec
/bin/zsh -lc 'export PYTHONDONTWRITEBYTECODE=1; bash scripts/tests/test-upgrade-spec-ownership.sh' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 exited 1 in 197350ms:
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
/bin/zsh -lc "rg -n \"ADOPTER|fork|legacy\" scripts/upgrade.sh | sed -n '1,240p'; nl -ba scripts/upgrade.sh | sed -n '1680,2030p'; nl -ba scripts/tests/test-upgrade-spec-ownership.sh | sed -n '235,275p'" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
194:# ADOPTER settings stays OFF. Flip _T34_VERSION_FLOOR_PROBE_PASSED to 1 in
410:                        (.claude/hooks/{tests,legacy}, .claude/scripts/tests,
496:  # legacy bare shasum if the helper was not sourced (partial checkout).
1059:#   ADOPTER-CUSTOMIZED H_dst!=H_base && H_src==H_base  -> preserve
1070:  # If either side cannot be hashed (missing file), fall back to legacy handling.
1081:    printf 'ADOPTER-CUSTOMIZED\n'; return 0
1231:      ADOPTER-CUSTOMIZED)
1232:        echo "    PRESERVED (ADOPTER-CUSTOMIZED — not overwritten): $rel" >&2
1310:    # the legacy one-line preview.
1317:        ADOPTER-CUSTOMIZED)
1318:          echo "    (dry-run) would PRESERVE (ADOPTER-CUSTOMIZED): $rel_path" ;;
1335:  # Falls through to the legacy whole-tree path for FILE targets or when no
1351:  # an ADOPTER-CUSTOMIZED file / refuse a CONFLICT instead of clobbering.
1358:      ADOPTER-CUSTOMIZED)
1359:        echo "    PRESERVED (ADOPTER-CUSTOMIZED — not overwritten): $rel_path" >&2
1376:        : ;;  # fall through to legacy whole-file path below
1390:  # PLAN-161 W2 fix-2 (codex r2 F11): the legacy DIRECTORY branch used to
1397:  # legacy upgrade neither ADDS nor REMOVES excluded-tree files; the U3
1617:        # pointer is CONTENT, not a fork — it is preserved, and the record keeps
1722:  # fingerprint (rc 1) => the caller's safe path (ADOPTER-FORK preserve).
1800:# _ov_obs_spec_content — pristine | legacy_pristine | legacy_pristine_partial
1812:    if [ -n "$_osc_odd" ]; then printf 'legacy_pristine_partial'; else printf 'edited'; fi
1818:    if [ "$_osc_fp" = "$_osc_pf" ]; then printf 'legacy_pristine'; return 0; fi
1860:# would classify ADOPTER-CUSTOMIZED and the stale-contract class would
1869:#     no match => ADOPTER-FORK: preserve + snapshot + named WARNING.
1928:      # recovery guidance is the true ADOPTER-FORK: content the framework
1932:          echo "    (dry-run) would PRESERVE (SPEC/v1 ADOPTER-FORK): SPEC/v1"
1948:          # would destroy the only copy of the fork.
1952:        _up_record_op "preserve_spec_v1_adopter_fork" "SPEC/v1"
2437:        warn("WARNING: " + key + " is ADOPTER-CUSTOMIZED - PRESERVED "
2476:    warn("WARNING: model is ADOPTER-CUSTOMIZED - PRESERVED "
2512:        warn("WARNING: permissions.defaultMode is ADOPTER-CUSTOMIZED - "
2662:                 "ADOPTER-CUSTOMIZED - PRESERVED (not migrated)")
2820:  local _pm_trees=( ".claude/hooks/tests" ".claude/hooks/legacy" ".claude/scripts/tests" ".claude/hooks/_lib/tests" )
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
   235	# the GNU-sed branch, if present, is the pristine manifest).
   236	if [ -f "$T1/$MANIFEST_REL.bak" ]; then mv "$T1/$MANIFEST_REL.bak" "$T1/$MANIFEST_REL"; fi
   237	printf 'stray\n' > "$T1/SPEC/v1/zz-orphan-probe.md"
   238	DOC_OUT="$WORKROOT/doc1.out"
   239	bash "$DOCTOR" "$T1" --strict-orphans >"$DOC_OUT" 2>&1
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
   273	# --------------------------------------------------------------------------
   274	# S3 — user ceremony + upgrade --no-replay (r9): no SPEC, no root files.
   275	# --------------------------------------------------------------------------

exec
/bin/zsh -lc 'export PYTHONDONTWRITEBYTECODE=1; bash scripts/tests/test-install-upgrade-parity-e2e.sh' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 121470ms:

##############################################################
# ceremony mode: maintainer
##############################################################
--> [A] install.sh (working tree) --ceremony maintainer --profile core
--> [B1] install.sh @ v1.2.0 --ceremony maintainer --profile core
--> [B2] upgrade.sh (source: /Users/joaocanhada/canhada-labs/ceo-orchestration)
--> classify

---- parity classification (mode=maintainer) --------------------------
  inputs:
    A (fresh install)        : /var/folders/9n/hm9srl0s1nz45_p12tj61pd80000gn/T/ceo-parity-e2e-XXXXXX.15ZumKQ34t/maintainer/route-a/adopter  [555 files]
    B (pin v1.2.0   + upgrade): /var/folders/9n/hm9srl0s1nz45_p12tj61pd80000gn/T/ceo-parity-e2e-XXXXXX.15ZumKQ34t/maintainer/route-b/adopter  [946 files]
    head source              : /Users/joaocanhada/canhada-labs/ceo-orchestration
    pinned source (v1.2.0)  : /var/folders/9n/hm9srl0s1nz45_p12tj61pd80000gn/T/ceo-parity-e2e-XXXXXX.15ZumKQ34t/src-v1.2.0
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
    A (fresh install)        : /var/folders/9n/hm9srl0s1nz45_p12tj61pd80000gn/T/ceo-parity-e2e-XXXXXX.15ZumKQ34t/user/route-a/adopter  [512 files]
    B (pin v1.2.0   + upgrade): /var/folders/9n/hm9srl0s1nz45_p12tj61pd80000gn/T/ceo-parity-e2e-XXXXXX.15ZumKQ34t/user/route-b/adopter  [903 files]
    head source              : /Users/joaocanhada/canhada-labs/ceo-orchestration
    pinned source (v1.2.0)  : /var/folders/9n/hm9srl0s1nz45_p12tj61pd80000gn/T/ceo-parity-e2e-XXXXXX.15ZumKQ34t/src-v1.2.0
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

exec
/bin/zsh -lc 'command -v actionlint || true; command -v yamllint || true; command -v ruby || true; command -v jq || true; git diff --check' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
/opt/homebrew/bin/actionlint
/usr/bin/ruby
/usr/bin/jq

exec
/bin/zsh -lc 'actionlint .github/workflows/npm-publish.yml .github/workflows/release.yml .github/workflows/smoke-install.yml' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 161ms:
exec
/bin/zsh -lc "rg -n 'head_branch|workflow_runs' .claude docs tests replay-fixtures .github | head -300" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
.github/workflows/npm-publish.yml:147:                --jq '.workflow_runs[] | {id, run_attempt, path, event, head_branch, head_sha, created_at, status, conclusion}' \
.github/workflows/npm-publish.yml:168:            jq -c -s '{workflow_runs: .}' runs_with_jobs.ndjson > payload.json
.claude/plans/PLAN-167/rail/codex-r1.md:929:+                --jq '.workflow_runs[] | {id, run_attempt, path, event, head_branch, head_sha, created_at, status, conclusion}' \
.claude/plans/PLAN-167/rail/codex-r1.md:950:+            jq -c -s '{workflow_runs: .}' runs_with_jobs.ndjson > payload.json
.claude/plans/PLAN-167/rail/codex-r1.md:1375:  ``head_branch == <tag>``, ``head_sha == <GITHUB_SHA>``, it is FRESH
.claude/plans/PLAN-167/rail/codex-r1.md:1407:same ``head_sha``/``head_branch``. Polling before the NEW Release run is
.claude/plans/PLAN-167/rail/codex-r1.md:1430:``path`` (or ``workflow_path``), ``event``, ``head_branch``, ``head_sha``,
.claude/plans/PLAN-167/rail/codex-r1.md:1561:    Accepts the raw GitHub envelope (``workflow_runs``) or a plain ``runs``
.claude/plans/PLAN-167/rail/codex-r1.md:1567:    for key in ("workflow_runs", "runs"):
.claude/plans/PLAN-167/rail/codex-r1.md:1576:    raise MalformedPayload("payload has no 'workflow_runs' (or 'runs') key")
.claude/plans/PLAN-167/rail/codex-r1.md:1598:        and run.get("head_branch") == ctx.tag
.claude/plans/PLAN-167/rail/codex-r1.md:7237:/bin/zsh -lc "grep -R \"head_branch\" -n .claude/scripts/tests/test_await_release_gate.py | head -30; sed -n '1,420p' .claude/scripts/tests/test_await_release_gate.py" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
.claude/plans/PLAN-167/rail/codex-r1.md:7239:.claude/scripts/tests/test_await_release_gate.py:103:        "head_branch": TAG,
.claude/plans/PLAN-167/rail/codex-r1.md:7240:.claude/scripts/tests/test_await_release_gate.py:121:        "head_branch": TAG,
.claude/plans/PLAN-167/rail/codex-r1.md:7241:.claude/scripts/tests/test_await_release_gate.py:190:        self._assert_never_grants(release_run(head_branch="v1.3.0-rc.2", id=2001))
.claude/plans/PLAN-167/rail/codex-r1.md:7344:        "head_branch": TAG,
.claude/plans/PLAN-167/rail/codex-r1.md:7362:        "head_branch": TAG,
.claude/plans/PLAN-167/rail/codex-r1.md:7372:    return {"workflow_runs": list(runs)}
.claude/plans/PLAN-167/rail/codex-r1.md:7431:        self._assert_never_grants(release_run(head_branch="v1.3.0-rc.2", id=2001))
.claude/plans/PLAN-167/rail/codex-r1.md:7468:        for body in ([], "workflow_runs", {"message": "Bad credentials"},
.claude/plans/PLAN-167/rail/codex-r1.md:7469:                     {"workflow_runs": {"nope": 1}}, {"workflow_runs": ["not-an-object"]}):
.claude/plans/PLAN-162/ceremony-2-staged/plan165-merge-resolved/ceo-boot.py.resolved:2324:                "[.workflow_runs[] | {path: .path, status: .status, "
.claude/plans/PLAN-167/rail/codex-r4.md:7243:+                --jq '.workflow_runs[] | {id, run_attempt, path, event, head_branch, head_sha, created_at, status, conclusion}' \
.claude/plans/PLAN-167/rail/codex-r4.md:7264:+            jq -c -s '{workflow_runs: .}' runs_with_jobs.ndjson > payload.json
.claude/plans/PLAN-167/rail/codex-r4.md:7735:/bin/zsh -lc "sed -n '1,360p' .claude/scripts/await_release_gate.py; rg -n \"release-gate|path|head_branch|created_at|decision\" .claude/scripts/await_release_gate.py .claude/scripts/tests/test_await_release_gate.py | head -200; cat .claude/governance/npm-trusted-publisher.txt" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
.claude/plans/PLAN-167/rail/codex-r4.md:7759:  ``head_branch == <tag>``, ``head_sha == <GITHUB_SHA>``, it is FRESH
.claude/plans/PLAN-167/rail/codex-r4.md:7791:same ``head_sha``/``head_branch``. Polling before the NEW Release run is
.claude/plans/PLAN-167/rail/codex-r4.md:7814:``path`` (or ``workflow_path``), ``event``, ``head_branch``, ``head_sha``,
.claude/plans/PLAN-167/rail/codex-r4.md:7945:    Accepts the raw GitHub envelope (``workflow_runs``) or a plain ``runs``
.claude/plans/PLAN-167/rail/codex-r4.md:7951:    for key in ("workflow_runs", "runs"):
.claude/plans/PLAN-167/rail/codex-r4.md:7960:    raise MalformedPayload("payload has no 'workflow_runs' (or 'runs') key")
.claude/plans/PLAN-167/rail/codex-r4.md:7982:        and run.get("head_branch") == ctx.tag
.claude/plans/PLAN-167/rail/codex-r4.md:8102:.claude/scripts/await_release_gate.py:23:  ``head_branch == <tag>``, ``head_sha == <GITHUB_SHA>``, it is FRESH
.claude/plans/PLAN-167/rail/codex-r4.md:8106:.claude/scripts/await_release_gate.py:55:same ``head_sha``/``head_branch``. Polling before the NEW Release run is
.claude/plans/PLAN-167/rail/codex-r4.md:8110:.claude/scripts/await_release_gate.py:78:``path`` (or ``workflow_path``), ``event``, ``head_branch``, ``head_sha``,
.claude/plans/PLAN-167/rail/codex-r4.md:8122:.claude/scripts/await_release_gate.py:246:        and run.get("head_branch") == ctx.tag
.claude/plans/PLAN-167/rail/codex-r4.md:8145:.claude/scripts/await_release_gate.py:383:    parser.add_argument("--tag", required=True, help="tag name, i.e. head_branch of the release run")
.claude/plans/PLAN-167/rail/codex-r4.md:8168:.claude/scripts/tests/test_await_release_gate.py:103:        "head_branch": TAG,
.claude/plans/PLAN-167/rail/codex-r4.md:8171:.claude/scripts/tests/test_await_release_gate.py:121:        "head_branch": TAG,
.claude/plans/PLAN-167/rail/codex-r4.md:8184:.claude/scripts/tests/test_await_release_gate.py:190:        self._assert_never_grants(release_run(head_branch="v1.3.0-rc.2", id=2001))
.claude/plans/PLAN-167/rail/codex-r4.md:16037:+                --jq '.workflow_runs[] | {id, run_attempt, path, event, head_branch, head_sha, created_at, status, conclusion}' \
.claude/plans/PLAN-167/rail/codex-r4.md:16058:+            jq -c -s '{workflow_runs: .}' runs_with_jobs.ndjson > payload.json
.claude/plans/PLAN-167/rail/codex-r4.md:16421:  ``head_branch == <tag>``, ``head_sha == <GITHUB_SHA>``, it is FRESH
.claude/plans/PLAN-167/rail/codex-r4.md:16453:same ``head_sha``/``head_branch``. Polling before the NEW Release run is
.claude/plans/PLAN-167/rail/codex-r4.md:16476:``path`` (or ``workflow_path``), ``event``, ``head_branch``, ``head_sha``,
.claude/plans/PLAN-167/rail/codex-r4.md:16607:    Accepts the raw GitHub envelope (``workflow_runs``) or a plain ``runs``
.claude/plans/PLAN-167/rail/codex-r4.md:16613:    for key in ("workflow_runs", "runs"):
.claude/plans/PLAN-167/rail/codex-r4.md:16622:    raise MalformedPayload("payload has no 'workflow_runs' (or 'runs') key")
.claude/plans/PLAN-167/rail/codex-r4.md:16644:        and run.get("head_branch") == ctx.tag
.claude/plans/PLAN-167/rail/codex-r3.md:1132:+                --jq '.workflow_runs[] | {id, run_attempt, path, event, head_branch, head_sha, created_at, status, conclusion}' \
.claude/plans/PLAN-167/rail/codex-r3.md:1153:+            jq -c -s '{workflow_runs: .}' runs_with_jobs.ndjson > payload.json
.claude/plans/PLAN-167/rail/codex-r3.md:9036:+                --jq '.workflow_runs[] | {id, run_attempt, path, event, head_branch, head_sha, created_at, status, conclusion}' \
.claude/plans/PLAN-167/rail/codex-r3.md:9057:+            jq -c -s '{workflow_runs: .}' runs_with_jobs.ndjson > payload.json
.claude/plans/PLAN-167/rail/codex-r3.md:9813:  ``head_branch == <tag>``, ``head_sha == <GITHUB_SHA>``, it is FRESH
.claude/plans/PLAN-167/rail/codex-r3.md:9845:same ``head_sha``/``head_branch``. Polling before the NEW Release run is
.claude/plans/PLAN-167/rail/codex-r3.md:9868:``path`` (or ``workflow_path``), ``event``, ``head_branch``, ``head_sha``,
.claude/plans/PLAN-167/rail/codex-r3.md:9999:    Accepts the raw GitHub envelope (``workflow_runs``) or a plain ``runs``
.claude/plans/PLAN-167/rail/codex-r3.md:10005:    for key in ("workflow_runs", "runs"):
.claude/plans/PLAN-167/rail/codex-r3.md:10014:    raise MalformedPayload("payload has no 'workflow_runs' (or 'runs') key")
.claude/plans/PLAN-167/rail/codex-r3.md:10036:        and run.get("head_branch") == ctx.tag
.claude/plans/PLAN-167/rail/codex-r3.md:10850:    parser.add_argument("--tag", required=True, help="tag name, i.e. head_branch of the release run")
.claude/plans/PLAN-167/rail/codex-r3.md:21037:+                --jq '.workflow_runs[] | {id, run_attempt, path, event, head_branch, head_sha, created_at, status, conclusion}' \
.claude/plans/PLAN-167/rail/codex-r3.md:21058:+            jq -c -s '{workflow_runs: .}' runs_with_jobs.ndjson > payload.json
.claude/plans/PLAN-167/rail/codex-r3.md:21672:  ``head_branch == <tag>``, ``head_sha == <GITHUB_SHA>``, it is FRESH
.claude/plans/PLAN-167/rail/codex-r3.md:21704:same ``head_sha``/``head_branch``. Polling before the NEW Release run is
.claude/plans/PLAN-167/rail/codex-r3.md:21727:``path`` (or ``workflow_path``), ``event``, ``head_branch``, ``head_sha``,
.claude/plans/PLAN-167/rail/codex-r3.md:21858:    Accepts the raw GitHub envelope (``workflow_runs``) or a plain ``runs``
.claude/plans/PLAN-167/rail/codex-r3.md:21864:    for key in ("workflow_runs", "runs"):
.claude/plans/PLAN-167/rail/codex-r3.md:21873:    raise MalformedPayload("payload has no 'workflow_runs' (or 'runs') key")
.claude/plans/PLAN-167/rail/codex-r3.md:21895:        and run.get("head_branch") == ctx.tag
.claude/plans/PLAN-167/rail/codex-r2.md:4394:+                --jq '.workflow_runs[] | {id, run_attempt, path, event, head_branch, head_sha, created_at, status, conclusion}' \
.claude/plans/PLAN-167/rail/codex-r2.md:4415:+            jq -c -s '{workflow_runs: .}' runs_with_jobs.ndjson > payload.json
.claude/plans/PLAN-167/rail/codex-r2.md:4964:   147	                --jq '.workflow_runs[] | {id, run_attempt, path, event, head_branch, head_sha, created_at, status, conclusion}' \
.claude/plans/PLAN-167/rail/codex-r2.md:4985:   168	            jq -c -s '{workflow_runs: .}' runs_with_jobs.ndjson > payload.json
.claude/plans/PLAN-167/rail/codex-r2.md:5395:  ``head_branch == <tag>``, ``head_sha == <GITHUB_SHA>``, it is FRESH
.claude/plans/PLAN-167/rail/codex-r2.md:5427:same ``head_sha``/``head_branch``. Polling before the NEW Release run is
.claude/plans/PLAN-167/rail/codex-r2.md:5450:``path`` (or ``workflow_path``), ``event``, ``head_branch``, ``head_sha``,
.claude/plans/PLAN-167/rail/codex-r2.md:5581:    Accepts the raw GitHub envelope (``workflow_runs``) or a plain ``runs``
.claude/plans/PLAN-167/rail/codex-r2.md:5587:    for key in ("workflow_runs", "runs"):
.claude/plans/PLAN-167/rail/codex-r2.md:5596:    raise MalformedPayload("payload has no 'workflow_runs' (or 'runs') key")
.claude/plans/PLAN-167/rail/codex-r2.md:5618:        and run.get("head_branch") == ctx.tag
.claude/plans/PLAN-167/rail/codex-r2.md:5797:        "head_branch": TAG,
.claude/plans/PLAN-167/rail/codex-r2.md:5815:        "head_branch": TAG,
.claude/plans/PLAN-167/rail/codex-r2.md:5825:    return {"workflow_runs": list(runs)}
.claude/plans/PLAN-167/rail/codex-r2.md:5884:        self._assert_never_grants(release_run(head_branch="v1.3.0-rc.2", id=2001))
.claude/plans/PLAN-167/rail/codex-r2.md:5921:        for body in ([], "workflow_runs", {"message": "Bad credentials"},
.claude/plans/PLAN-167/rail/codex-r2.md:5922:                     {"workflow_runs": {"nope": 1}}, {"workflow_runs": ["not-an-object"]}):
.claude/plans/PLAN-167/rail/codex-r2.md:6419:/bin/zsh -lc 'grep -R "head_branch" -n .claude .github docs scripts tests 2>/dev/null | head -80' in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
.claude/plans/PLAN-167/rail/codex-r2.md:6421:.claude/plans/PLAN-166/debate/round-1/consensus.md:43:`head_branch==<tag GA>` + `head_sha` + conclusão do **job**
.claude/plans/PLAN-167/rail/codex-r2.md:6422:.claude/plans/PLAN-166/debate/round-1/security-engineer.md:55:**E** `head_branch == $GITHUB_REF_NAME` (nome da tag) **E**
.claude/plans/PLAN-167/rail/codex-r2.md:6423:.claude/plans/PLAN-166/debate/round-1/security-engineer.md:143:   `head_branch == <nome da tag GA>`, `head_sha == <SHA da tag>`, e
.claude/plans/PLAN-167/rail/codex-r2.md:6424:.claude/plans/PLAN-166/debate/round-1/security-engineer.md:192:   `head_branch` da rc; (iii) `head_branch` certo mas `head_sha` de outro
.claude/plans/PLAN-167/rail/codex-r2.md:6425:.claude/plans/PLAN-166/debate/round-2/security-engineer.md:26:| `head_branch == <nome da tag>` | AC-2: "`head_branch==<tag>`" | ✅ |
.claude/plans/PLAN-167/rail/codex-r2.md:6426:.claude/plans/PLAN-166/debate/round-3/devops-engineer.md:106:  contra a lista de fixtures NUNCA-GRANT (head_branch de rc, head_sha de
.claude/plans/PLAN-167/rail/codex-r2.md:6427:.claude/plans/PLAN-166/debate/round-3/security-engineer.md:34:  construção, e o `head_branch` permanece como defesa em profundidade, não
.claude/plans/PLAN-167/rail/codex-r2.md:6428:.claude/plans/PLAN-166/debate/round-3/security-engineer.md:209:  bind: os quatro fixtures NUNCA-GRANT (head_branch de rc, SHA de outro
.claude/plans/PLAN-167/rail/codex-r2.md:6429:.claude/plans/PLAN-166-release-hold-findings-closure.md:73:  `head_branch == <nome da tag>`, `head_sha == GITHUB_SHA`, e **job
.claude/plans/PLAN-167/rail/codex-r2.md:6430:.claude/plans/PLAN-166-release-hold-findings-closure.md:604:      `event==push` + `head_branch==<tag>` + `head_sha==GITHUB_SHA` +
.claude/plans/PLAN-167/rail/codex-r2.md:6431:.claude/plans/PLAN-166-release-hold-findings-closure.md:616:      head_branch de rc; head_sha de outro commit; workflow errado com
.claude/plans/PLAN-167/rail/codex-r2.md:6432:.claude/scripts/tests/test_await_release_gate.py:103:        "head_branch": TAG,
.claude/plans/PLAN-167/rail/codex-r2.md:6433:.claude/scripts/tests/test_await_release_gate.py:121:        "head_branch": TAG,
.claude/plans/PLAN-167/rail/codex-r2.md:6434:.claude/scripts/tests/test_await_release_gate.py:190:        self._assert_never_grants(release_run(head_branch="v1.3.0-rc.2", id=2001))
.claude/plans/PLAN-167/rail/codex-r2.md:6435:.claude/scripts/await_release_gate.py:23:  ``head_branch == <tag>``, ``head_sha == <GITHUB_SHA>``, it is FRESH
.claude/plans/PLAN-167/rail/codex-r2.md:6436:.claude/scripts/await_release_gate.py:55:same ``head_sha``/``head_branch``. Polling before the NEW Release run is
.claude/plans/PLAN-167/rail/codex-r2.md:6437:.claude/scripts/await_release_gate.py:78:``path`` (or ``workflow_path``), ``event``, ``head_branch``, ``head_sha``,
.claude/plans/PLAN-167/rail/codex-r2.md:6438:.claude/scripts/await_release_gate.py:246:        and run.get("head_branch") == ctx.tag
.claude/plans/PLAN-167/rail/codex-r2.md:6439:.claude/scripts/await_release_gate.py:383:    parser.add_argument("--tag", required=True, help="tag name, i.e. head_branch of the release run")
.claude/plans/PLAN-167/rail/codex-r2.md:6440:.github/workflows/npm-publish.yml:147:                --jq '.workflow_runs[] | {id, run_attempt, path, event, head_branch, head_sha, created_at, status, conclusion}' \
.claude/scripts/await_release_gate.py:23:  ``head_branch == <tag>``, ``head_sha == <GITHUB_SHA>``, it is FRESH
.claude/scripts/await_release_gate.py:55:same ``head_sha``/``head_branch``. Polling before the NEW Release run is
.claude/scripts/await_release_gate.py:78:``path`` (or ``workflow_path``), ``event``, ``head_branch``, ``head_sha``,
.claude/scripts/await_release_gate.py:209:    Accepts the raw GitHub envelope (``workflow_runs``) or a plain ``runs``
.claude/scripts/await_release_gate.py:215:    for key in ("workflow_runs", "runs"):
.claude/scripts/await_release_gate.py:224:    raise MalformedPayload("payload has no 'workflow_runs' (or 'runs') key")
.claude/scripts/await_release_gate.py:246:        and run.get("head_branch") == ctx.tag
.claude/scripts/await_release_gate.py:383:    parser.add_argument("--tag", required=True, help="tag name, i.e. head_branch of the release run")
.claude/plans/PLAN-166/debate/round-3/security-engineer.md:34:  construção, e o `head_branch` permanece como defesa em profundidade, não
.claude/plans/PLAN-166/debate/round-3/security-engineer.md:209:  bind: os quatro fixtures NUNCA-GRANT (head_branch de rc, SHA de outro
.claude/plans/PLAN-166-release-hold-findings-closure.md:73:  `head_branch == <nome da tag>`, `head_sha == GITHUB_SHA`, e **job
.claude/plans/PLAN-166-release-hold-findings-closure.md:604:      `event==push` + `head_branch==<tag>` + `head_sha==GITHUB_SHA` +
.claude/plans/PLAN-166-release-hold-findings-closure.md:616:      head_branch de rc; head_sha de outro commit; workflow errado com
.claude/plans/PLAN-166/debate/round-1/security-engineer.md:55:**E** `head_branch == $GITHUB_REF_NAME` (nome da tag) **E**
.claude/plans/PLAN-166/debate/round-1/security-engineer.md:143:   `head_branch == <nome da tag GA>`, `head_sha == <SHA da tag>`, e
.claude/plans/PLAN-166/debate/round-1/security-engineer.md:192:   `head_branch` da rc; (iii) `head_branch` certo mas `head_sha` de outro
.claude/plans/PLAN-166/debate/round-3/devops-engineer.md:106:  contra a lista de fixtures NUNCA-GRANT (head_branch de rc, head_sha de
.claude/plans/PLAN-166/debate/round-1/consensus.md:43:`head_branch==<tag GA>` + `head_sha` + conclusão do **job**
.claude/plans/PLAN-166/debate/round-2/security-engineer.md:26:| `head_branch == <nome da tag>` | AC-2: "`head_branch==<tag>`" | ✅ |
.claude/plans/PLAN-166/archive/ceremony-worktree-20260806-1430.diff:1503:+                --jq '.workflow_runs[] | {id, run_attempt, path, event, head_branch, head_sha, created_at, status, conclusion}' \
.claude/plans/PLAN-166/archive/ceremony-worktree-20260806-1430.diff:1524:+            jq -c -s '{workflow_runs: .}' runs_with_jobs.ndjson > payload.json
.claude/plans/PLAN-166/archive/codex-r6-2059.md:355:+                --jq '.workflow_runs[] | {id, run_attempt, path, event, head_branch, head_sha, created_at, status, conclusion}' \
.claude/plans/PLAN-166/archive/codex-r6-2059.md:376:+            jq -c -s '{workflow_runs: .}' runs_with_jobs.ndjson > payload.json
.claude/plans/PLAN-166/archive/codex-r6-2059.md:3375:   147	                --jq '.workflow_runs[] | {id, run_attempt, path, event, head_branch, head_sha, created_at, status, conclusion}' \
.claude/plans/PLAN-166/archive/codex-r6-2059.md:3396:   168	            jq -c -s '{workflow_runs: .}' runs_with_jobs.ndjson > payload.json
.claude/plans/PLAN-166/archive/codex-r6-2059.md:3515:  ``head_branch == <tag>``, ``head_sha == <GITHUB_SHA>``, it is FRESH
.claude/plans/PLAN-166/archive/codex-r6-2059.md:3547:same ``head_sha``/``head_branch``. Polling before the NEW Release run is
.claude/plans/PLAN-166/archive/codex-r6-2059.md:3570:``path`` (or ``workflow_path``), ``event``, ``head_branch``, ``head_sha``,
.claude/plans/PLAN-166/archive/codex-r6-2059.md:3701:    Accepts the raw GitHub envelope (``workflow_runs``) or a plain ``runs``
.claude/plans/PLAN-166/archive/codex-r6-2059.md:3707:    for key in ("workflow_runs", "runs"):
.claude/plans/PLAN-166/archive/codex-r6-2059.md:3716:    raise MalformedPayload("payload has no 'workflow_runs' (or 'runs') key")
.claude/plans/PLAN-166/archive/codex-r6-2059.md:3738:        and run.get("head_branch") == ctx.tag
.claude/plans/PLAN-166/archive/codex-r6-2059.md:3957:        "head_branch": TAG,
.claude/plans/PLAN-166/archive/codex-r6-2059.md:3975:        "head_branch": TAG,
.claude/plans/PLAN-166/archive/codex-r6-2059.md:3985:    return {"workflow_runs": list(runs)}
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4044:        self._assert_never_grants(release_run(head_branch="v1.3.0-rc.2", id=2001))
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4081:        for body in ([], "workflow_runs", {"message": "Bad credentials"},
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4082:                     {"workflow_runs": {"nope": 1}}, {"workflow_runs": ["not-an-object"]}):
.claude/plans/PLAN-166/archive/codex-r6-2059.md:4246:    parser.add_argument("--tag", required=True, help="tag name, i.e. head_branch of the release run")
.claude/scripts/tests/test_await_release_gate.py:103:        "head_branch": TAG,
.claude/scripts/tests/test_await_release_gate.py:121:        "head_branch": TAG,
.claude/scripts/tests/test_await_release_gate.py:131:    return {"workflow_runs": list(runs)}
.claude/scripts/tests/test_await_release_gate.py:190:        self._assert_never_grants(release_run(head_branch="v1.3.0-rc.2", id=2001))
.claude/scripts/tests/test_await_release_gate.py:227:        for body in ([], "workflow_runs", {"message": "Bad credentials"},
.claude/scripts/tests/test_await_release_gate.py:228:                     {"workflow_runs": {"nope": 1}}, {"workflow_runs": ["not-an-object"]}):
.claude/scripts/ceo-boot.py:2314:                "[.workflow_runs[] | {path: .path, status: .status, "
.claude/scripts/ceo-boot.py:2377:                "[.workflow_runs[] | {path: .path, status: .status, "

exec
/bin/zsh -lc 'for f in .claude/plans/PLAN-166/archive/codex-review-w1-round{6,7,8,9,10,11}.md .claude/plans/PLAN-166/archive/codex-r6-2059.md; do echo =====$f; rg -n '"'\"title\"|\\[P[0-3]\\]|findings|overall_correctness|REJECT|APPROVE' \""'$f" | tail -30; done' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 exited 1 in 0ms:
zsh:1: ====.claude/plans/PLAN-166/archive/codex-review-w1-round6.md not found

exec
/bin/zsh -lc "rg -n '\"title\"|\\[P[0-3]\\]|findings|overall_correctness|REJECT|APPROVE' \".claude/plans/PLAN-166/archive/codex-review-w1-round6.md\" | tail -40" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
5:- [P2] Keep sanitized LINK records available for validation — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1728-1730

exec
/bin/zsh -lc "rg -n '\"title\"|\\[P[0-3]\\]|findings|overall_correctness|REJECT|APPROVE' \".claude/plans/PLAN-166/archive/codex-review-w1-round7.md\" | tail -40" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
5:- [P2] Verify the live marker against its manifest record — /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/scripts/check-framework-updates.sh:123-128
8:- [P2] Preserve delivery records when switching to user ceremony — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1747-1749
11:- [P2] Parse LINK targets without splitting on spaces — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1760-1760

exec
/bin/zsh -lc "rg -n '\"title\"|\\[P[0-3]\\]|findings|overall_correctness|REJECT|APPROVE' \".claude/plans/PLAN-166/archive/codex-review-w1-round8.md\" | tail -40" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
5:- [P1] Preserve rendered hashes on installer reruns — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/install.sh:2338-2339
8:- [P2] Make missing LINK records follow the preserve path — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1781-1781
11:- [P2] Apply the staged parity-classifier edit in the landing script — /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/plans/PLAN-166/OWNER-W1-LAND-step1.sh:52-54

exec
/bin/zsh -lc "rg -n '\"title\"|\\[P[0-3]\\]|findings|overall_correctness|REJECT|APPROVE' \".claude/plans/PLAN-166/archive/codex-review-w1-round9.md\" | tail -40" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
5:- [P1] Preserve the prior PROTOCOL digest on installer reruns — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/install.sh:2350-2353
8:- [P1] Retain the canonical PROTOCOL hash on user-mode skips — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:2943-2948
11:- [P2] Reject special files before backing up SPEC/v1 — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1931-1933
14:- [P2] Generate the marker when pinning pre-v1.3 releases — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1961-1964

exec
/bin/zsh -lc "rg -n '\"title\"|\\[P[0-3]\\]|findings|overall_correctness|REJECT|APPROVE' \".claude/plans/PLAN-166/archive/codex-review-w1-round10.md\" | tail -40" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
5:- [P2] Validate LINK targets before preserving ownership — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/install.sh:2311-2313
8:- [P2] Restrict link serialization to previously owned paths — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:3048-3050
11:- [P2] Include symlinks in descendant skip detection — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1834-1835
14:- [P2] Trigger ownership tests when the hash helper changes — /Users/joaocanhada/canhada-labs/ceo-orchestration/.github/workflows/smoke-install.yml:19-22

exec
/bin/zsh -lc "rg -n '\"title\"|\\[P[0-3]\\]|findings|overall_correctness|REJECT|APPROVE' \".claude/plans/PLAN-166/archive/codex-review-w1-round11.md\" | tail -40" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
5:- [P2] Reject hash-to-link transitions during continuity — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/install.sh:2326-2328
8:- [P2] Preserve records when continuity finds missing SPEC files — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/install.sh:2330-2337
11:- [P2] Keep downgrade version reporting tied to the pinned source — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1987-1992
14:- [P2] Gate forensic marker guidance on its delivery record — /Users/joaocanhada/canhada-labs/ceo-orchestration/INSTALL.md:592-595

exec
/bin/zsh -lc "rg -n '\"title\"|\\[P[0-3]\\]|findings|overall_correctness|REJECT|APPROVE' \".claude/plans/PLAN-166/archive/codex-r6-2059.md\" | tail -40" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
16:  • Return prioritized review findings
277:+# Alternatives REJECTED (do not resurrect without a new debate):
475:+      # Re-pass findings r15 + r17 + r18 (PLAN-166), debate r3 scoped VETO.
1548:+      # Re-pass findings r15 + r17 + r18 (PLAN-166), debate r3 scoped VETO.
2335:   734	      # Re-pass findings r15 + r17 + r18 (PLAN-166), debate r3 scoped VETO.
2885: findings: []  # List of P0/P1/P2/P3 with file:line if any
6325:debate_record: .claude/plans/PLAN-166/debate/ (3 rounds, 3 scoped VETOs raised and LIFTED with literal verification) + codex pair-rail 20 rounds (~55 findings applied)
7582:.claude/plans/PLAN-167/rail/codex-r2.md:6429:.claude/plans/PLAN-166-release-hold-findings-closure.md:73:  `head_branch == <nome da tag>`, `head_sha == GITHUB_SHA`, e **job
7583:.claude/plans/PLAN-167/rail/codex-r2.md:6430:.claude/plans/PLAN-166-release-hold-findings-closure.md:604:      `event==push` + `head_branch==<tag>` + `head_sha==GITHUB_SHA` +
7584:.claude/plans/PLAN-167/rail/codex-r2.md:6431:.claude/plans/PLAN-166-release-hold-findings-closure.md:616:      head_branch de rc; head_sha de outro commit; workflow errado com
7604:.claude/plans/PLAN-166-release-hold-findings-closure.md:73:  `head_branch == <nome da tag>`, `head_sha == GITHUB_SHA`, e **job
7605:.claude/plans/PLAN-166-release-hold-findings-closure.md:604:      `event==push` + `head_branch==<tag>` + `head_sha==GITHUB_SHA` +
7606:.claude/plans/PLAN-166-release-hold-findings-closure.md:616:      head_branch de rc; head_sha de outro commit; workflow errado com
7643:/bin/zsh -lc 'for f in .claude/plans/PLAN-166/archive/codex-review-w1-round{6,7,8,9,10,11}.md .claude/plans/PLAN-166/archive/codex-r6-2059.md; do echo =====$f; rg -n '"'\"title\"|\\[P[0-3]\\]|findings|overall_correctness|REJECT|APPROVE' \""'$f" | tail -30; done' in /Users/joaocanhada/canhada-labs/ceo-orchestration
7648:/bin/zsh -lc "rg -n '\"title\"|\\[P[0-3]\\]|findings|overall_correctness|REJECT|APPROVE' \".claude/plans/PLAN-166/archive/codex-review-w1-round6.md\" | tail -40" in /Users/joaocanhada/canhada-labs/ceo-orchestration
7650:5:- [P2] Keep sanitized LINK records available for validation — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1728-1730
7653:/bin/zsh -lc "rg -n '\"title\"|\\[P[0-3]\\]|findings|overall_correctness|REJECT|APPROVE' \".claude/plans/PLAN-166/archive/codex-review-w1-round7.md\" | tail -40" in /Users/joaocanhada/canhada-labs/ceo-orchestration
7655:5:- [P2] Verify the live marker against its manifest record — /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/scripts/check-framework-updates.sh:123-128
7656:8:- [P2] Preserve delivery records when switching to user ceremony — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1747-1749
7657:11:- [P2] Parse LINK targets without splitting on spaces — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1760-1760
7660:/bin/zsh -lc "rg -n '\"title\"|\\[P[0-3]\\]|findings|overall_correctness|REJECT|APPROVE' \".claude/plans/PLAN-166/archive/codex-review-w1-round8.md\" | tail -40" in /Users/joaocanhada/canhada-labs/ceo-orchestration
7662:5:- [P1] Preserve rendered hashes on installer reruns — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/install.sh:2338-2339
7663:8:- [P2] Make missing LINK records follow the preserve path — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1781-1781
7664:11:- [P2] Apply the staged parity-classifier edit in the landing script — /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/plans/PLAN-166/OWNER-W1-LAND-step1.sh:52-54
7667:/bin/zsh -lc "rg -n '\"title\"|\\[P[0-3]\\]|findings|overall_correctness|REJECT|APPROVE' \".claude/plans/PLAN-166/archive/codex-review-w1-round9.md\" | tail -40" in /Users/joaocanhada/canhada-labs/ceo-orchestration
7669:5:- [P1] Preserve the prior PROTOCOL digest on installer reruns — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/install.sh:2350-2353
7670:8:- [P1] Retain the canonical PROTOCOL hash on user-mode skips — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:2943-2948
7671:11:- [P2] Reject special files before backing up SPEC/v1 — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1931-1933
7672:14:- [P2] Generate the marker when pinning pre-v1.3 releases — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1961-1964
7675:/bin/zsh -lc "rg -n '\"title\"|\\[P[0-3]\\]|findings|overall_correctness|REJECT|APPROVE' \".claude/plans/PLAN-166/archive/codex-review-w1-round10.md\" | tail -40" in /Users/joaocanhada/canhada-labs/ceo-orchestration
7677:5:- [P2] Validate LINK targets before preserving ownership — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/install.sh:2311-2313
7678:8:- [P2] Restrict link serialization to previously owned paths — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:3048-3050
7679:11:- [P2] Include symlinks in descendant skip detection — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1834-1835
7680:14:- [P2] Trigger ownership tests when the hash helper changes — /Users/joaocanhada/canhada-labs/ceo-orchestration/.github/workflows/smoke-install.yml:19-22
7683:/bin/zsh -lc "rg -n '\"title\"|\\[P[0-3]\\]|findings|overall_correctness|REJECT|APPROVE' \".claude/plans/PLAN-166/archive/codex-review-w1-round11.md\" | tail -40" in /Users/joaocanhada/canhada-labs/ceo-orchestration
7685:5:- [P2] Reject hash-to-link transitions during continuity — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/install.sh:2326-2328
7686:8:- [P2] Preserve records when continuity finds missing SPEC files — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/install.sh:2330-2337
7687:11:- [P2] Keep downgrade version reporting tied to the pinned source — /Users/joaocanhada/canhada-labs/ceo-orchestration/scripts/upgrade.sh:1987-1992
7688:14:- [P2] Gate forensic marker guidance on its delivery record — /Users/joaocanhada/canhada-labs/ceo-orchestration/INSTALL.md:592-595

exec
/bin/zsh -lc "nl -ba .claude/plans/PLAN-166/OWNER-W1-LAND-step1.sh | sed -n '1,260p'; printf '\\n--- PLAN167 script ---\\n'; nl -ba .claude/plans/PLAN-167/OWNER-PREPARE-TO-SIGN.sh | sed -n '1,260p'; printf '\\n--- mirror fixes ---\\n'; nl -ba .claude/plans/PLAN-166/archive/mirror-fixes.sh | sed -n '1,260p'" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
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

--- PLAN167 script ---
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

--- mirror fixes ---
     1	#!/bin/bash
     2	# Espelha os fixes do round codex (árvore viva -> cópias staged), regenera
     3	# os patches e o manifesto. Só ESCREVE sob .claude/plans/PLAN-166/.
     4	#
     5	# O round 7 tocou um TERCEIRO canônico (o checker), que também tem cópia
     6	# staged e patch próprio no pack — espelhar só install/upgrade deixaria o
     7	# staged divergente do vivo sem nenhum gate acusar. Tabela path->patch para
     8	# que acrescentar um arquivo seja uma linha, não uma edição em 4 lugares.
     9	set -euo pipefail
    10	cd /Users/joaocanhada/canhada-labs/ceo-orchestration
    11	S=.claude/plans/PLAN-166/staged
    12	
    13	MIRRORED="
    14	scripts/install.sh|f3-install-delivery-record.patch
    15	scripts/upgrade.sh|f3-upgrade-spec-forced-refresh.patch
    16	.claude/scripts/check-framework-updates.sh|f3-check-framework-updates-marker-first.patch
    17	scripts/_framework_manifest_set.sh|f3-fms-conditional-entries.patch
    18	.github/workflows/smoke-install.yml|smoke-install-parity-e2e-wiring.patch
    19	"
    20	
    21	echo "$MIRRORED" | while IFS='|' read -r src patch; do
    22	  [ -n "$src" ] || continue
    23	  mkdir -p "$S/$( dirname "$src" )"
    24	  cp -p "$src" "$S/$src"
    25	  git diff HEAD -- "$src" > "$S/patches/$patch"
    26	  git apply --check --reverse "$S/patches/$patch" \
    27	    && echo "reverse-apply OK (patch == vivo): $src"
    28	  cmp -s "$src" "$S/$src" && echo "staged == vivo: $src"
    29	done
    30	
    31	( cd "$S" && find . -type f ! -name '.DS_Store' | sed 's|^\./||' | LC_ALL=C sort \
    32	  | while read -r f; do shasum -a 256 "$f"; done ) \
    33	  | awk -v pre="$S/" '{print $1 "  " pre $2}' > .claude/plans/PLAN-166/staged-manifest.sha256
    34	
    35	BAD=$(shasum -a 256 -c .claude/plans/PLAN-166/staged-manifest.sha256 | grep -cv ': OK$' || true)
    36	echo "manifesto não-OK: $BAD  |  entradas: $(wc -l < .claude/plans/PLAN-166/staged-manifest.sha256 | tr -d ' ')"
    37	[ "$BAD" = "0" ]

exec
/bin/zsh -lc 'shasum -a 256 -c .claude/plans/PLAN-166/staged-manifest.sha256 >/tmp/plan166-manifest.out 2>&1; rc=$?; echo rc=$rc; tail -40 /tmp/plan166-manifest.out; printf '"'\\nactual entries='; wc -l < .claude/plans/PLAN-166/staged-manifest.sha256; printf '\\nstaged files='; find .claude/plans/PLAN-166/staged -type f "'! -name .DS_Store | wc -l' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
rc=0
.claude/plans/PLAN-166/staged/.claude/.framework-version: OK
.claude/plans/PLAN-166/staged/.claude/adr/ADR-155-AMEND-1-delivery-record-ownership.md: OK
.claude/plans/PLAN-166/staged/.claude/governance/npm-trusted-publisher.txt: OK
.claude/plans/PLAN-166/staged/.claude/governance/pair-rail-verdict-template.md: OK
.claude/plans/PLAN-166/staged/.claude/scripts/check-framework-updates.sh: OK
.claude/plans/PLAN-166/staged/.claude/scripts/tests/test_release_workflow_asserts.py: OK
.claude/plans/PLAN-166/staged/.github/workflows/npm-publish.yml: OK
.claude/plans/PLAN-166/staged/.github/workflows/release.yml: OK
.claude/plans/PLAN-166/staged/.github/workflows/smoke-install.yml: OK
.claude/plans/PLAN-166/staged/INSTALL.md: OK
.claude/plans/PLAN-166/staged/notes-w1b-kernel-override.md: OK
.claude/plans/PLAN-166/staged/notes-w1c-f3.md: OK
.claude/plans/PLAN-166/staged/patches/f3-adr-155-amend-1.patch: OK
.claude/plans/PLAN-166/staged/patches/f3-check-framework-updates-marker-first.patch: OK
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

actual entries=      34

staged files=      34

exec
/bin/zsh -lc "rg -n \"188 ADR|188 Architecture|\\| ADRs["'^'"\\n]*188|architecture decision records["'^'"\\n]*188|ADRs on disk["'^'"\\n]*188\" CLAUDE.md README.md README.pt-BR.md docs npm/README.md || true; rg -n \"189 ADR|189 Architecture|\\| ADRs["'^'"\\n]*189|architecture decision records["'^'"\\n]*189|ADRs on disk["'^'"\\n]*189\" CLAUDE.md README.md README.pt-BR.md docs npm/README.md | head -80" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
npm/README.md:122:ls .claude/adr | grep -c '^ADR-'                  # 189 ADRs
CLAUDE.md:54:- **189 ADRs** (architecture decision records, `.claude/adr/`) and **27 slash commands** (`.claude/commands/`).
README.md:186:ls .claude/adr | grep -c '^ADR-'                  # 189 ADRs
README.pt-BR.md:166:ls .claude/adr | grep -c '^ADR-'                  # 189 ADRs
docs/ARCHITECTURE.md:71:| ADRs               | 189                          | `ls .claude/adr/ADR-*.md \| wc -l`                        |
docs/CTO-GUIDE.md:44:| ADRs shipped | 189 | `ls .claude/adr/ADR-*.md \| wc -l` |
docs/CTO-GUIDE.md:112:grep -h '^# ADR-' .claude/adr/ADR-*.md | sort             # 189 ADRs on disk
docs/FAQ.md:108:ls .claude/adr | grep -c '^ADR-'                  # 189 ADRs
docs/GUIA-COMPLETO.md:167:- **Governed by ADR.** 189 ADRs document every architectural decision.
docs/GUIA-COMPLETO.md:1225:- `.claude/adr/` — 189 Architecture Decision Records

2026-08-08T00:09:04.066279Z ERROR codex_core::tools::router: error=exec_command failed for `/bin/zsh -lc 'set -e; t=$(mktemp -d); git init -q --bare "$t/r.git"; git clone -q "$t/r.git" "$t/a"; cd "$t/a"; git config user.name t; git config user.email t@t; echo a>a; git add a; git commit -qm a; git branch -M main; git push -q -u origin main; old=$(git rev-parse origin/main); git clone -q "$t/r.git" "$t/b" 2>/dev/null; cd "$t/b"; git config user.name t; git config user.email t@t; git checkout -qb main origin/main; echo b>>a; git commit -qam b; git push -q origin main; new=$(git rev-parse HEAD); cd "$t/a"; git fetch -q origin main; got=$(git rev-parse origin/main); fh=$(git rev-parse FETCH_HEAD); echo old=$old; echo new=$new; echo originmain=$got; echo fetchhead=$fh; rm -rf "$t"'`: CreateProcess { message: "Rejected(\"`/bin/zsh -lc 'set -e; t=$(mktemp -d); git init -q --bare \\\"$t/r.git\\\"; git clone -q \\\"$t/r.git\\\" \\\"$t/a\\\"; cd \\\"$t/a\\\"; git config user.name t; git config user.email t@t; echo a>a; git add a; git commit -qm a; git branch -M main; git push -q -u origin main; old=$(git rev-parse origin/main); git clone -q \\\"$t/r.git\\\" \\\"$t/b\\\" 2>/dev/null; cd \\\"$t/b\\\"; git config user.name t; git config user.email t@t; git checkout -qb main origin/main; echo b>>a; git commit -qam b; git push -q origin main; new=$(git rev-parse HEAD); cd \\\"$t/a\\\"; git fetch -q origin main; got=$(git rev-parse origin/main); fh=$(git rev-parse FETCH_HEAD); echo old=$old; echo new=$new; echo originmain=$got; echo fetchhead=$fh; rm -rf \\\"$t\\\"'` rejected: rm -f style commands are not permitted. Use a safer approach\")" }
exec
/bin/zsh -lc 'set -e; t=$(mktemp -d); git init -q --bare "$t/r.git"; git clone -q "$t/r.git" "$t/a"; cd "$t/a"; git config user.name t; git config user.email t@t; echo a>a; git add a; git commit -qm a; git branch -M main; git push -q -u origin main; old=$(git rev-parse origin/main); git clone -q "$t/r.git" "$t/b" 2>/dev/null; cd "$t/b"; git config user.name t; git config user.email t@t; git checkout -qb main origin/main; echo b>>a; git commit -qam b; git push -q origin main; new=$(git rev-parse HEAD); cd "$t/a"; git fetch -q origin main; got=$(git rev-parse origin/main); fh=$(git rev-parse FETCH_HEAD); echo tmp=$t; echo old=$old; echo new=$new; echo originmain=$got; echo fetchhead=$fh' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 exited 128 in 240ms:
fatal: a branch named 'main' already exists

exec
/bin/zsh -lc 'set -e; t=$(mktemp -d); git init -q --bare "$t/r.git"; git clone -q "$t/r.git" "$t/a"; cd "$t/a"; git config user.name t; git config user.email t@t; echo a>a; git add a; git commit -qm a; git branch -M main; git push -q -u origin main; git --git-dir="$t/r.git" symbolic-ref HEAD refs/heads/main; old=$(git rev-parse origin/main); git clone -q "$t/r.git" "$t/b"; cd "$t/b"; git config user.name t; git config user.email t@t; echo b>>a; git commit -qam b; git push -q origin main; new=$(git rev-parse HEAD); cd "$t/a"; git fetch -q origin main; got=$(git rev-parse origin/main); fh=$(git rev-parse FETCH_HEAD); echo tmp=$t; echo old=$old; echo new=$new; echo originmain=$got; echo fetchhead=$fh' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 420ms:
tmp=/var/folders/9n/hm9srl0s1nz45_p12tj61pd80000gn/T/tmp.33ng9YktvW
old=17e5babf3c65f93fdfa2a05dacf1b10f074eb45a
new=dca0b70f32f5c39b85240c76324bc65c50c9c831
originmain=dca0b70f32f5c39b85240c76324bc65c50c9c831
fetchhead=dca0b70f32f5c39b85240c76324bc65c50c9c831

exec
/bin/zsh -lc 'ls .claude/scripts/check-*adr* .claude/scripts/*adr* 2>/dev/null | head -100; rg -n "ADR-155-AMEND|adr_id" .claude/scripts/tests tests | head -100' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
.claude/scripts/check-adr-chain.py
.claude/scripts/check-adr-chain.py
.claude/scripts/generate-adr-index.py
.claude/scripts/verify-adr-118-rationale.py
.claude/scripts/tests/test_generate_adr_index.py:100:            adr_id, title, status = gen._parse_adr(p)
.claude/scripts/tests/test_generate_adr_index.py:101:            self.assertEqual(adr_id, "ADR-055-AMEND-1")
.claude/scripts/tests/test_generate_adr_index.py:114:            adr_id, title, status = gen._parse_adr(p)
.claude/scripts/tests/test_generate_adr_index.py:115:            self.assertEqual(adr_id, "ADR-019-AMEND-1")
.claude/scripts/tests/test_generate_adr_index.py:125:                "adr_id: ADR-042-AMEND-1\n"
.claude/scripts/tests/test_generate_adr_index.py:131:            adr_id, title, status = gen._parse_adr(p)
.claude/scripts/tests/test_generate_adr_index.py:132:            self.assertEqual(adr_id, "ADR-042-AMEND-1")
.claude/scripts/tests/test_generate_adr_index.py:139:            adr_id, title, status = gen._parse_adr(p)
.claude/scripts/tests/test_generate_adr_index.py:140:            self.assertEqual(adr_id, "ADR-104-AMEND-1")
.claude/scripts/tests/test_check_threat_model_coverage.py:27:    adr_id: str,
.claude/scripts/tests/test_check_threat_model_coverage.py:33:    path = adr_dir / f"ADR-{adr_id}-{slug}.md"
tests/integration/test_threat_model_coverage.py:358:        adr_ids = {r["adr"] for r in rows}
tests/integration/test_threat_model_coverage.py:360:            self.assertIn(adr, adr_ids, f"Missing per-ADR row: {adr}")

exec
/bin/zsh -lc 'export PYTHONDONTWRITEBYTECODE=1; python3 .claude/scripts/check-adr-chain.py' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 exited 1 in 135ms:
ERROR: /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/adr/ADR-145-cross-model-review-persona-demand-modality.md: missing `Status:` field
ERROR: /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/adr/ADR-149-model-id-allowlist.md: missing `Status:` field
ERROR: /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/adr/ADR-150-commit-signing-policy.md: missing `Status:` field
ERROR: /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/adr/ADR-162-grok-harness-capability-matrix.md: missing `Status:` field
ERROR: /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/adr/ADR-163-hook-latency-gate-percentile-stability.md: missing `Status:` field
ERROR: /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/adr/ADR-164-canonical-multicandidate-and-failclosed.md: missing `Status:` field
ERROR: /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/adr/ADR-165-canonical-shared-predicate-dual-anchor.md: missing `Status:` field
ERROR: /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/adr/ADR-181-claude-5-model-refresh.md: missing `Status:` field
ERROR: /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/adr/ADR-183-directory-added-notification-events.md: missing `Status:` field
ERROR: /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/adr/ADR-120-pii-core-promotion.md: declares Supersedes=ADR-111, but /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/adr/ADR-111-locked-corpus-governance.md has `Status: ACCEPTED` — should be SUPERSEDED
ERROR: /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/adr/ADR-182-codex-payload-pin-enforcement.md: declares Supersedes=ADR-111, but /Users/joaocanhada/canhada-labs/ceo-orchestration/.claude/adr/ADR-111-locked-corpus-governance.md has `Status: ACCEPTED` — should be SUPERSEDED
FAIL: 11 error(s), 0 warning(s)

exec
/bin/zsh -lc "find . -iname '*adr*index*' -maxdepth 4 -type f -print; rg -n \"ADR-155-AMEND\" . --glob '"'!*.diff'"' --glob '"'!*.patch'"' --glob '"'!*.md.asc'"' | head -100" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 135ms:
./.claude/scripts/tests/test_generate_adr_index.py
./.claude/scripts/generate-adr-index.py
./INSTALL.md:603:`ADR-155-AMEND-1`), so on an upgraded install `VERSION` reports the
./INSTALL.md:638:  place with a named WARNING (ADR-155-AMEND-1).
./INSTALL.md:653:  `ADR-155-AMEND-1`.
./scripts/upgrade.sh:347:  is NEVER touched (install-time snapshot — ADR-155-AMEND-1; read
./scripts/upgrade.sh:732:# PLAN-166 F3 (ADR-155-AMEND-1) — resolve the RECORDED install ceremony with
./scripts/upgrade.sh:1656:# PLAN-166 F3 (ADR-155-AMEND-1) — delivery-record lookups + SPEC/v1 FORCED
./scripts/upgrade.sh:1804:# wholesale replace (ADR-155-AMEND-1 §4).
./scripts/upgrade.sh:1874:#     ADR-155-AMEND-1 for why the asymmetry is deliberate.
./scripts/upgrade.sh:1902:    # the delete-the-adopter's-file class (ADR-155-AMEND-1 §3).
./scripts/upgrade.sh:3025:# PLAN-166 F3 (ADR-155-AMEND-1): CEREMONY-GATED — the refresh used to run
./scripts/upgrade.sh:3069:# PLAN-166 F3 (ADR-155-AMEND-1): SPEC/v1 forced refresh + framework version
./scripts/upgrade.sh:3143:  # PLAN-166 F3 (ADR-155-AMEND-1): conditional ownership from what THIS
./docs/ownership-decision-table.md:27:`ADR-155-AMEND-1` decided that framework ownership of the three
./docs/ownership-decision-table.md:91:delivery" in ADR-155-AMEND-1 §3.
./docs/ownership-decision-table.md:289:  is precisely the case ADR-155-AMEND-1 §3 cites for why ceremony-conditional
./docs/ownership-decision-table.md:409:| `SPEC/v1` | a **fork of the contract** → forced refresh | it is the published compliance contract (ADR-155-AMEND-1 §4) |
./docs/ownership-decision-table.md:478:  direction ADR-155-AMEND-1 §3 forbids. The failure path keeps the record
./docs/ownership-decision-table.md:509:deliberately (ADR-155-AMEND-1 §2). It is named here only so that its absence
./docs/ownership-decision-table.md:602:direction (ADR-155-AMEND-1 §3). The branch should be **deleted as dead
./scripts/_framework_manifest_set.sh:35:#   * DELIVERY-RECORD-CONDITIONAL entries (PLAN-166 F3 / ADR-155-AMEND-1):
./scripts/_framework_manifest_set.sh:53:#     ADR-155-AMEND-1 (the S238/ADR-155 "verified worst case" class, C.5).
./scripts/_framework_manifest_set.sh:116:    # .claude/). PLAN-166 F3 (ADR-155-AMEND-1): CONDITIONAL on the recorded
./scripts/_framework_manifest_set.sh:468:# over-claiming direction ADR-155-AMEND-1 §3 forbids.
./scripts/_framework_manifest_set.sh:562:  # never certify a wholesale replace (ADR-155-AMEND-1 §4).
./scripts/_framework_manifest_set.sh:582:  # replaces it (ADR-155-AMEND-1 §4). The root PROTOCOL.md is adopter-editable
./scripts/doctor.sh:616:    # PLAN-166 F3 (ADR-155-AMEND-1): the FMS entries for PROTOCOL.md,
./scripts/tests/test-upgrade-spec-ownership.sh:3:# PLAN-166 F3 (ADR-155-AMEND-1) — delivery-record ownership of the three
./scripts/tests/test-upgrade-spec-ownership.sh:184:  && ok "root VERSION sentinel untouched by upgrade (ADR-155-AMEND-1)" \
./scripts/tests/test-ownership-table.sh:371:      # certify a wholesale replace (ADR-155-AMEND-1 §4).
./scripts/install.sh:781:# PLAN-166 F3 (ADR-155-AMEND-1) — DELIVERY RECORD for the conditional
./scripts/install.sh:869:  # PLAN-166 F3 (ADR-155-AMEND-1): delivery signal for the caller — 1 only
./scripts/install.sh:1330:  # PLAN-166 F3 (ADR-155-AMEND-1): the op line above records the ATTEMPT;
./scripts/install.sh:1357:# ---- 5c-bis-3 framework version marker (PLAN-166 F3 / ADR-155-AMEND-1) ----
./scripts/install.sh:1933:  # PLAN-166 F3 (ADR-155-AMEND-1): registered delivery — this line is only
./scripts/install.sh:2296:  # PLAN-166 F3 (ADR-155-AMEND-1): conditional ownership from the DELIVERY
./scripts/tests/_parity_classify.py:144:        "BY DESIGN (PLAN-166 OQ-3 / ADR-155-AMEND-1): the upgrade must NOT "

exec
/bin/zsh -lc 'for f in .claude/plans/PLAN-166/archive/*.tar.gz; do echo "==== $f"; tar -tzf "$f" | sed -n '"'1,120p'; done; printf '\\n--- obvious secret/private-key markers in untracked text ---\\n'; git ls-files --others --exclude-standard -z | while IFS= read -r -d '' f; do case \""'$f" in *.gz|*.asc) continue;; esac; grep -nE '"'BEGIN (RSA |EC |OPENSSH |PGP )?PRIVATE KEY|ghp_[A-Za-z0-9]{20,}|github_pat_|npm_[A-Za-z0-9]{20,}' \""'$f" 2>/dev/null && echo "FILE=$f"; done' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 exited 1 in 106ms:
exec
/bin/zsh -lc "rg -n \"32|34|entries|entrad|manifest|_parity_classify\" .claude/plans/PLAN-166/architect/round-1/approved.md .claude/plans/PLAN-166/W1-approved-draft.md .claude/plans/PLAN-166/W1-ceremony-log.md .claude/plans/PLAN-166/OWNER-W1-LAND-step1.sh | sed -n '1,260p'; printf '\\n--- gpg verify ---\\n'; gpg --verify .claude/plans/PLAN-166/architect/round-1/approved.md.asc .claude/plans/PLAN-166/architect/round-1/approved.md 2>&1; echo rc="'$?' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
.claude/plans/PLAN-166/OWNER-W1-LAND-step1.sh:27:echo "== G3: manifesto staged fail-closed"
.claude/plans/PLAN-166/OWNER-W1-LAND-step1.sh:28:shasum -a 256 -c .claude/plans/PLAN-166/staged-manifest.sha256 > /dev/null || { echo "FAIL: manifesto"; exit 1; }
.claude/plans/PLAN-166/OWNER-W1-LAND-step1.sh:29:echo "   OK (32 entradas)"
.claude/plans/PLAN-166/OWNER-W1-LAND-step1.sh:50:  scripts/_framework_manifest_set.sh \
.claude/plans/PLAN-166/OWNER-W1-LAND-step1.sh:53:  scripts/tests/_parity_classify.py \
.claude/plans/PLAN-166/architect/round-1/approved.md:66:8. `install.sh` / `upgrade.sh` / `_framework_manifest_set.sh` /
.claude/plans/PLAN-166/architect/round-1/approved.md:106:AND an exact `_KERNEL_PATHS` entry (`check_arbitration_kernel.py:134`).
.claude/plans/PLAN-166/architect/round-1/approved.md:112:(`plan_id` truncated to `PLAN-166-W1-RELEASE-YML-AWAIT-GA`, 32 chars) is
.claude/plans/PLAN-166/architect/round-1/approved.md:118:**Conditional entries (OWNER-DECISION at signing — runbook §4 has the
.claude/plans/PLAN-166/architect/round-1/approved.md:123:`346f4ea`): the W0 fleet HAS committed both files and the sites are
.claude/plans/PLAN-166/architect/round-1/approved.md:136:Ceremony inputs are integrity-pinned: the TRACKED manifest
.claude/plans/PLAN-166/architect/round-1/approved.md:137:`.claude/plans/PLAN-166/staged-manifest.sha256` covers every staged file;
.claude/plans/PLAN-166/architect/round-1/approved.md:139:[[feedback-staged-inputs-need-tracked-hash-manifest]]).
.claude/plans/PLAN-166/architect/round-1/approved.md:170:  - scripts/_framework_manifest_set.sh
.claude/plans/PLAN-166/architect/round-1/approved.md:173:  - scripts/tests/_parity_classify.py
.claude/plans/PLAN-166/architect/round-1/approved.md:184:`delta_manifest` / `delta_manifest_sha256`) + seção "tag() guard
.claude/plans/PLAN-166/architect/round-1/approved.md:189:Manifesto regenerado: 32 entradas (template staged + patch novo).
.claude/plans/PLAN-166/architect/round-1/approved.md:195:Uma linha adicionada ao Scope grupo B: `scripts/tests/_parity_classify.py`.
.claude/plans/PLAN-166/architect/round-1/approved.md:196:Motivo: as entradas KNOWN_OPEN F3-spec-stale / F3-protocol-user-mode são
.claude/plans/PLAN-166/W1-approved-draft.md:25:       (approved.md + .asc, staged-manifest.sha256, W1-approved-draft.md,
.claude/plans/PLAN-166/W1-approved-draft.md:92:8. `install.sh` / `upgrade.sh` / `_framework_manifest_set.sh` /
.claude/plans/PLAN-166/W1-approved-draft.md:132:AND an exact `_KERNEL_PATHS` entry (`check_arbitration_kernel.py:134`).
.claude/plans/PLAN-166/W1-approved-draft.md:138:(`plan_id` truncated to `PLAN-166-W1-RELEASE-YML-AWAIT-GA`, 32 chars) is
.claude/plans/PLAN-166/W1-approved-draft.md:144:**Conditional entries (OWNER-DECISION at signing — runbook §4 has the
.claude/plans/PLAN-166/W1-approved-draft.md:149:`346f4ea`): the W0 fleet HAS committed both files and the sites are
.claude/plans/PLAN-166/W1-approved-draft.md:160:Ceremony inputs are integrity-pinned: the TRACKED manifest
.claude/plans/PLAN-166/W1-approved-draft.md:161:`.claude/plans/PLAN-166/staged-manifest.sha256` covers every staged file;
.claude/plans/PLAN-166/W1-approved-draft.md:163:[[feedback-staged-inputs-need-tracked-hash-manifest]]).
.claude/plans/PLAN-166/W1-approved-draft.md:194:  - scripts/_framework_manifest_set.sh
.claude/plans/PLAN-166/W1-approved-draft.md:197:  - scripts/tests/_parity_classify.py
.claude/plans/PLAN-166/W1-approved-draft.md:208:`delta_manifest` / `delta_manifest_sha256`) + seção "tag() guard
.claude/plans/PLAN-166/W1-approved-draft.md:213:Manifesto regenerado: 32 entradas (template staged + patch novo).
.claude/plans/PLAN-166/W1-ceremony-log.md:38:   (probe, sessão `6d29323e`) → BLOCK com a mensagem literal
.claude/plans/PLAN-166/W1-ceremony-log.md:42:4. Bytes: `release.yml` vivo == cópia staged pinada no manifesto
.claude/plans/PLAN-166/W1-ceremony-log.md:139:  (c) P2 `OWNER-W1-LAND-step1.sh` não copiava `_parity_classify.py`,
.claude/plans/PLAN-166/W1-ceremony-log.md:140:  embora esteja no escopo assinado e no manifesto — o script documentado
.claude/plans/PLAN-166/W1-ceremony-log.md:146:  de 4 canônicos alterados — o checker e o `_framework_manifest_set.sh`

--- gpg verify ---
gpg: Signature made Thu Aug  6 13:42:31 2026 -03
gpg:                using EDDSA key AE9B236FDAF0462874060C6BCFCFACF00335DC74
gpg: failed to create temporary file '/Users/joaocanhada/.gnupg/.#lk0x0000000101696240.MacBook-Pro-de-Joao-2.local.52733': Operation not permitted
gpg: can't connect to the keyboxd: Operation not permitted
gpg: error opening key DB: No Keybox daemon running
gpg: failed to create temporary file '/Users/joaocanhada/.gnupg/.#lk0x0000000101695250.MacBook-Pro-de-Joao-2.local.52733': Operation not permitted
gpg: can't connect to the keyboxd: Operation not permitted
gpg: error opening key DB: No Keybox daemon running
gpg: Can't check signature: No public key
rc=2

exec
/bin/zsh -lc "sed -n '1,220p' scripts/tests/test-install-upgrade-parity-e2e.sh; rg -n \"print-pin|PIN_TAG|HISTORICAL\" scripts/tests/test-install-upgrade-parity-e2e.sh" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
#!/usr/bin/env bash
# scripts/tests/test-install-upgrade-parity-e2e.sh
# PLAN-166 W0 / F4 (OQ-4) — install≠upgrade parity, measured on the RESULTING
# TREES, per ceremony mode.
#
# WHY THIS EXISTS (F4, P1)
# ------------------------
# The previous parity gate was dead twice over:
#   (a) TAUTOLOGICAL — scripts/tests/test_install_baseline_manifest.sh "C.2"
#       compared `_framework_target_entries()` with `_framework_target_entries()`
#       and admitted it in a comment ("the enumeration is static
#       (root-independent), so an 'install context' and an 'upgrade context'
#       derive an identical target set by construction"). It also carried a
#       hand-written closed list of "required entries".
#   (b) INVISIBLE — no workflow ran scripts/tests/*.sh except smoke-install.yml,
#       and neither the old assertion nor this file was wired into it. 5th
#       instance of the "red gate nobody runs" class.
# Set-equality of ENUMERATIONS — even independently derived ones — can NEVER
# reach the delivery sites that live OUTSIDE the enumeration. That is exactly
# how F3 was born: `SPEC/v1` is delivered by install.sh (`install_one "SPEC/v1"`,
# install.sh:1307) and by NOTHING in upgrade.sh, and it is absent from
# `_framework_target_entries()`. So this test compares REAL TREES.
#
# WHAT IT DOES
# ------------
#   Route A (fresh)      : install.sh (WORKING TREE)                      -> A
#   Route B (historical) : install.sh @ $PIN -> upgrade.sh (WORKING TREE) -> B
# for EACH ceremony mode (maintainer, user). Both targets get the SAME basename
# so install.sh's {{PROJECT_NAME}} substitution is identical on both sides.
#
# THE MEASUREMENT (why "diff -r A B" is the wrong instrument)
# -----------------------------------------------------------
# A raw byte-diff of the two trees answers "are these two installs identical",
# which is not the question. The question is "did the upgrade deliver the
# CURRENT generation of framework content?" So every path is classified against
# BOTH source generations (the working tree and the $PIN archive):
#
#   IDENTICAL      A(p) == B(p)                                      ok
#   PERSONALIZED   B(p) == head_src(p): upgrade shipped CURRENT       advisory
#                  framework bytes; install.sh additionally
#                  substitutes {{PROJECT_NAME}}-class placeholders
#   STALE          B(p) == pin_src(p) != head_src(p): the upgrade     FATAL
#                  LEFT THE OLD GENERATION IN PLACE   <-- F3 signature
#   MISSING_IN_B   install delivered p, upgrade did not               FATAL
#   UNCLASSIFIED   diverges and matches neither generation            FATAL
#                  (generated/adopter-owned paths must be DECLARED)
#   MODE_DIFF      same bytes, different +x bit ("cp lost the exec     FATAL
#                  bit" is a verified S286 failure mode here)
#   ONLY_IN_B      upgrade's `cp -R` drags content install's          advisory
#                  selective walk never ships (ADR-155 pre-existing
#                  drift) -- EXCEPT outside .claude/ in `user` mode,
#                  which is FATAL (the WS4 no-writes-outside-.claude
#                  invariant that smoke-install.yml already asserts
#                  for install and nobody asserts for upgrade)
#
# Declarations are checked for ROT in both directions:
#   * KNOWN-OPEN ledger entries are MANDATORY-FIRE: an entry that matches
#     nothing is FATAL ("the bug you named is closed -- delete the entry").
#     A ledger cannot outlive its bug.
#   * DECLARED generated/adopter-owned paths that turn out IDENTICAL emit a
#     WARNING (declaration is stale; harmless).
#   * Any divergence matching NO declaration is FATAL. That is the live gate;
#     the positive control trips exactly there.
#
# EXIT CODES
#   0  parity   — no fatal divergence and no KNOWN-OPEN entry outstanding
#   1  FAIL     — undeclared divergence (what the positive control must
#                 produce, and what a real install/upgrade regression produces)
#   2  KNOWN-OPEN — only the explicitly named PLAN-166 W1 prerequisites are
#                 outstanding. STILL A FAILURE, never a silent skip: the
#                 printed ledger names each one and what unblocks it. This is
#                 the expected pre-W1 result.
#   9  SCAFFOLD-ERROR — the fixture itself broke (tag unresolvable, install or
#                 upgrade returned non-zero, python3 missing). NEVER a verdict
#                 on the bug. In CI the historical leg needs the TAG: a
#                 `fetch-depth: 1` checkout does not have it.
#
# POSITIVE CONTROL
#   --positive-control deletes ONE `backup_and_replace "<dir>"` line from a COPY
#   of upgrade.sh and re-runs the whole thing. The expected outcome is exit 1 in
#   EVERY mode tested. If any mode does NOT go fatal, the run ends in exit 9
#   SCAFFOLD-ERROR ("the control is vacuous"), never in a green — a control that
#   silently stops firing is worse than no control at all. That happens for a
#   real reason: the plant only bites if the planted directory actually drifted
#   between $PIN and HEAD, so the guard is DERIVED from the run, not asserted
#   from memory.
#   ORDERING MATTERS: the control only proves something when the UN-planted run
#   was not already fatal, otherwise rc=1 could come from a pre-existing
#   divergence rather than from the plant. So CI runs the plain gate FIRST and
#   the control only after it passed; run it the same way by hand.
#
# USAGE
#   bash scripts/tests/test-install-upgrade-parity-e2e.sh
#   bash scripts/tests/test-install-upgrade-parity-e2e.sh --mode user
#   bash scripts/tests/test-install-upgrade-parity-e2e.sh --positive-control
#   bash scripts/tests/test-install-upgrade-parity-e2e.sh --print-pin
#
# W1 CHECKLIST: the KNOWN_OPEN ledger in _parity_classify.py is MANDATORY-FIRE.
# When W1 lands the F3 fix those entries stop matching and the classifier goes
# fatal on ledger-rot BY DESIGN — deleting them belongs to the same commit.
#
# bash-3.2 safe (no associative arrays, no mapfile). Network-free. Writes only
# under mktemp -d. Requires: git, python3, tar.

set -uo pipefail   # NOT -e: failures are classified, not fatal-by-default.

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

PIN="${CEO_PARITY_PIN:-v1.2.0}"
PROFILE="${CEO_PARITY_PROFILE:-core}"
MODES="maintainer user"
POSITIVE_CONTROL=0
# The single line deleted from a COPY of upgrade.sh by --positive-control.
PLANT_TARGET='.claude/commands'

PRINT_PIN=0

while [ $# -gt 0 ]; do
  case "$1" in
    --mode) MODES="${2:-}"; shift 2 ;;
    --profile) PROFILE="${2:-}"; shift 2 ;;
    --pin) PIN="${2:-}"; shift 2 ;;
    --positive-control) POSITIVE_CONTROL=1; shift ;;
    # Only meaningful with --positive-control. Exists so the vacuity guard
    # itself can be exercised: planting a target that did NOT drift between
    # $PIN and HEAD must end in exit 9, not in a green.
    --plant-target) PLANT_TARGET="${2:-}"; shift 2 ;;
    # Single source of truth for the historical pin: CI must FETCH this tag
    # (the checkout is fetch-depth:1 and has no tags), and hardcoding the value
    # in the workflow would make a second copy of the truth that drifts.
    --print-pin) PRINT_PIN=1; shift ;;
    # Print the header block, whatever its length — a hardcoded `sed -n '2,80p'`
    # silently truncates the help the first time the header grows.
    -h|--help) awk 'NR>1 && /^[^#]/ {exit} NR>1 {print}' "$0"; exit 0 ;;
    *) echo "ERROR: unknown argument: $1" >&2; exit 9 ;;
  esac
done

if [ "$PRINT_PIN" -eq 1 ]; then
  printf '%s\n' "$PIN"
  exit 0
fi
[ "$MODES" = "both" ] && MODES="maintainer user"

scaffold() { echo "" >&2; echo "SCAFFOLD-ERROR: $*" >&2; exit 9; }

command -v python3 >/dev/null 2>&1 || scaffold "python3 not on PATH"
command -v git     >/dev/null 2>&1 || scaffold "git not on PATH"
command -v tar     >/dev/null 2>&1 || scaffold "tar not on PATH"

CLASSIFY="$SCRIPT_DIR/_parity_classify.py"
[ -f "$CLASSIFY" ] || scaffold "classifier missing: $CLASSIFY"

WORK="$( mktemp -d -t ceo-parity-e2e-XXXXXX )" || scaffold "mktemp -d failed"
# shellcheck disable=SC2329  # invoked indirectly by the EXIT trap below
cleanup() {
  [ "${CEO_PARITY_KEEP_WORK:-0}" = "1" ] && return 0
  [ -n "${WORK:-}" ] || return 0
  find "$WORK" -mindepth 1 -depth -exec chmod u+w {} + 2>/dev/null || true
  find "$WORK" -mindepth 1 -depth -delete 2>/dev/null || true
  rmdir "$WORK" 2>/dev/null || true
}
trap cleanup EXIT

# Non-interactive install/upgrade. A source checkout carries a placeholder
# self-SHA; skipping it keeps the fixture deterministic regardless of
# release-fill state (the same knobs smoke-install.yml already uses).
export CEO_INSTALL_SKIP_SELF_SHA=1
export CEO_RAG_INSTALL_PROMPT=0

echo "=============================================================="
echo " install/upgrade parity e2e  (PLAN-166 F4 / OQ-4)"
echo "=============================================================="
echo "  repo (route A source) : $REPO_ROOT"
echo "  historical pin        : $PIN"
echo "  profile               : $PROFILE"
echo "  ceremony modes        : $MODES"
echo "  positive control      : $POSITIVE_CONTROL"
echo "  workdir               : $WORK"
echo "  git describe (repo)   : $( git -C "$REPO_ROOT" describe --tags --always --dirty 2>/dev/null || echo '(n/a)' )"
echo "--------------------------------------------------------------"

# --- historical source: pure read of the tag, never a repo mutation ---------
if ! git -C "$REPO_ROOT" rev-parse --verify --quiet "refs/tags/$PIN" >/dev/null 2>&1; then
  {
    echo ""
    echo "  tag '$PIN' does not resolve in $REPO_ROOT."
    echo "  In CI this is the fetch-depth:1 hole — the checkout has no tags, so"
    echo "  the historical leg cannot run, and 'it passes on my clone' is"
    echo "  exactly the gap this test exists to close. Fetch the tag first:"
    echo "      git fetch --no-tags --depth 1 origin +refs/tags/$PIN:refs/tags/$PIN"
  } >&2
  scaffold "historical pin '$PIN' unresolvable — refusing to skip"
fi
PIN_SRC="$WORK/src-$PIN"
mkdir -p "$PIN_SRC"
if ! git -C "$REPO_ROOT" archive "$PIN" | tar -x -C "$PIN_SRC"; then
  scaffold "git archive $PIN | tar -x failed"
fi
[ -f "$PIN_SRC/scripts/install.sh" ] || scaffold "$PIN archive has no scripts/install.sh"

# --- optional planted-divergence source for the positive control ------------
# A depth-1 symlink farm over the working tree with ONE edited file. upgrade.sh
# derives SOURCE_DIR from its own location ("cd $SCRIPT_DIR/.." with a logical
# pwd), so the farm root becomes the source and every other path resolves
# through the symlinks to the live tree. Cheap (no 75MB copy) and it perturbs
# exactly one line, which is what a positive control is for.
PLANTED_SRC=""
if [ "$POSITIVE_CONTROL" -eq 1 ]; then
  PLANTED_SRC="$WORK/src-planted"
  mkdir -p "$PLANTED_SRC/scripts"
  for _e in "$REPO_ROOT"/* "$REPO_ROOT"/.[!.]* "$REPO_ROOT"/..?*; do
    [ -e "$_e" ] || continue
    _b="$( basename "$_e" )"
    [ "$_b" = "scripts" ] && continue
    ln -s "$_e" "$PLANTED_SRC/$_b" 2>/dev/null || true
  done
  for _f in "$REPO_ROOT"/scripts/* "$REPO_ROOT"/scripts/.[!.]*; do
    [ -e "$_f" ] || continue
96:#   bash scripts/tests/test-install-upgrade-parity-e2e.sh --print-pin
132:    --print-pin) PRINT_PIN=1; shift ;;

exec
/bin/zsh -lc "rg -n \"PLANTED|positive control:|per-mode verdicts|PLANT\" scripts/tests/test-install-upgrade-parity-e2e.sh | sed -n '1,240p'; nl -ba scripts/tests/test-install-upgrade-parity-e2e.sh | sed -n '205,430p'; nl -ba .github/workflows/smoke-install.yml | sed -n '180,225p'" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
115:PLANT_TARGET='.claude/commands'
128:    --plant-target) PLANT_TARGET="${2:-}"; shift 2 ;;
209:PLANTED_SRC=""
211:  PLANTED_SRC="$WORK/src-planted"
212:  mkdir -p "$PLANTED_SRC/scripts"
217:    ln -s "$_e" "$PLANTED_SRC/$_b" 2>/dev/null || true
223:    ln -s "$_f" "$PLANTED_SRC/scripts/$_b" 2>/dev/null || true
225:  _before="$( grep -c "^backup_and_replace \"$PLANT_TARGET\"\$" "$REPO_ROOT/scripts/upgrade.sh" || true )"
226:  grep -v "^backup_and_replace \"$PLANT_TARGET\"\$" \
227:    "$REPO_ROOT/scripts/upgrade.sh" > "$PLANTED_SRC/scripts/upgrade.sh" \
229:  _after="$( grep -c "^backup_and_replace \"$PLANT_TARGET\"\$" "$PLANTED_SRC/scripts/upgrade.sh" || true )"
231:    scaffold "planting failed: backup_and_replace \"$PLANT_TARGET\" occurrences before=$_before after=$_after — the control perturbed nothing"
233:  echo "  PLANTED: dropped backup_and_replace \"$PLANT_TARGET\" from a COPY of"
281:  [ -n "$PLANTED_SRC" ] && UP_SRC="$PLANTED_SRC"
295:  [ -n "$PLANTED_SRC" ] && EXTRA_ARGS="--extra-source $PLANTED_SRC"
313:echo "per-mode verdicts (0 parity / 1 fail / 2 known-open):$MODE_VERDICTS"
328:      echo "  The plant removed backup_and_replace \"$PLANT_TARGET\" from the copy"
330:      echo "  Most likely cause: nothing under '$PLANT_TARGET' changed between"
332:      echo "  control is vacuous and proves nothing. Pick a PLANT_TARGET with"
337:  echo "positive control: FIRED in every mode (rc=1 each) — the gate is alive."
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
   180	        run: |
   181	          set -euo pipefail
   182	          bash scripts/tests/test-install-upgrade-parity-e2e.sh
   183	
   184	      # Control of the control (AC-4). With ONE backup_and_replace line deleted
   185	      # from a COPY of upgrade.sh, the gate above must come back RED in EVERY
   186	      # ceremony mode. rc must be exactly 1: rc 0/2 means the gate went blind,
   187	      # rc 9 means the plant stopped biting (vacuous control). Both fail here.
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

exec
/bin/zsh -lc 'cat npm/package.json; rg -n "framework-version|npm.*files|files.*npm|build.*npm|vendor" npm scripts .github/workflows | head -240' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
{
  "name": "ceo-orchestration",
  "version": "1.3.0",
  "description": "NPM shim that runs the ceo-orchestration install.sh inside a published bundle.",
  "type": "commonjs",
  "bin": {
    "ceo-orchestration": "bin/ceo-orch-init.js"
  },
  "files": [
    "bin/",
    "scripts/",
    "templates/",
    ".claude/",
    "SPEC/",
    "VERSION",
    "LICENSE",
    "README.md",
    "PROTOCOL.md"
  ],
  "engines": {
    "node": ">=20"
  },
  "scripts": {
    "test": "node --check bin/ceo-orch-init.js && echo 'syntax OK'"
  },
  "repository": {
    "type": "git",
    "url": "git+https://github.com/Canhada-Labs/ceo-orchestration.git"
  },
  "license": "MIT",
  "keywords": [
    "ceo-orchestration",
    "claude-code",
    "agent",
    "framework",
    "install"
  ],
  "publishConfig": {
    "access": "public",
    "provenance": true
  }
}
.github/workflows/actionlint.yml:50:        # PLAN-063 round-3 (DIM-20 #1 partial closure): SHA-pinned vendored
.github/workflows/actionlint.yml:82:            echo "- **Install:** SHA-pinned 1.7.7 vendored asset (round-3)"
npm/README.md:133:- **Same-vendor reviewer caveat.** The cross-model pair-rail reduces single-model blind spots, but the reviewer is still a large language model and can share failure modes with the model under review. It is defense-in-depth, not an independent oracle.
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
.github/workflows/npm-publish.yml:289:        # (package.json "files" whitelist takes precedence in npm-packlist), so
npm/INTEGRITY.md:23:| SHA-256 manifest per file | `sha256sum` over every file in `files:` array | `.github/workflows/validate.yml` (to-add) + manifest committed to `npm/SHA256SUMS.txt` during release prep |
npm/INTEGRITY.md:26:| Reproducible build | `SOURCE_DATE_EPOCH` set to VERSION tag commit date | Release script (Sprint 17 scope) sets env var before `npm pack` |
npm/INTEGRITY.md:99:- **Reproducible build** (`SOURCE_DATE_EPOCH`-pinned `npm pack`) is specified
scripts/install-npm.sh:103:# Copy framework source tree into npm/ so npm pack picks it up via files: list.
scripts/install-npm.sh:183:# build). CI verification (npm-publish.yml) computes the checksum of the
scripts/_framework_manifest_set.sh:36:#     PROTOCOL.md, SPEC/v1 and .claude/.framework-version are enumerated ONLY
scripts/_framework_manifest_set.sh:40:#         FMS_DELIVERED_MARKER     .claude/.framework-version marker
scripts/_framework_manifest_set.sh:141:      printf '%s\n' ".claude/.framework-version"
scripts/_framework_manifest_set.sh:301:    .claude/.framework-version) printf '%s' "${FMS_HASH_SOURCE_MARKER:-}" ;;
scripts/_framework_manifest_set.sh:308:    SPEC/v1|SPEC/v1/*|PROTOCOL.md|.claude/.framework-version) return 0 ;;
.github/workflows/validate.yml:991:      # script, then asserts that the only npm/ files git considers
.github/workflows/validate.yml:1015:            echo "::error::Run: bash scripts/npm-rebuild.sh && git add npm/package.json && commit"
.github/workflows/validate.yml:1024:      # seeded from the TRACKED npm/ files (git archive) — the working npm/
.github/workflows/validate.yml:1028:      # .npmignore is INERT under the package.json "files" whitelist, so this
scripts/measure-repo-size.sh:26:EXCLUDE_RE='/(\.git|node_modules|vendor|\.venv|venv|dist|build|__pycache__|\.pytest_cache|target|out)/'
scripts/measure-repo-size.sh:88:Excluded: .git/ node_modules/ vendor/ .venv/ venv/ dist/ build/
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
scripts/_grok_harness.sh:260:  echo "    OQ3). Same-vendor caveat is direction-neutral (author=xAI,"
scripts/doctor.sh:617:    # SPEC/v1 and .claude/.framework-version are CONDITIONAL on the
scripts/doctor.sh:643:    if _dr_delivered '\.claude/\.framework-version(  |$)'; then
.github/workflows/GOVERNANCE-MAP.md:65:> `actions/attest-build-provenance` or `npm publish --provenance` could use
scripts/npm-rebuild.sh:3:# scripts/npm-rebuild.sh — regenerate the npm/ bundle from canonical sources.
scripts/npm-rebuild.sh:15:#   5. Copy VERSION → npm/VERSION (so the two files are bit-identical).
scripts/npm-rebuild.sh:52:info "Rebuilding npm/ bundle for VERSION=$VERSION"
scripts/npm-rebuild.sh:72:# `npm/.claude/` is gitignored build state. `npm-rebuild.sh` only owns
scripts/npm-rebuild.sh:159:    fail "npm pack would ship $pack_files files (> $NPM_PACK_FILE_CEILING ceiling) — a stale .claude/plans/ or other out-of-scope tree likely leaked into the bundle (PLAN-118 AC-B8 / PLAN-119-FOLLOWUP WS-1)."
scripts/npm-rebuild.sh:162:  ok "npm pack file count $pack_files within ceiling $NPM_PACK_FILE_CEILING"
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
scripts/tests/ownership_table.tsv:59:OWN-0064	marker	hash	regular	pristine	yes	copy	maintainer	upgrade	self	none	PRESERVE_OWNED	HASH_SOURCE	adr-155-amend-1	--skip .claude/.framework-version
scripts/tests/test-council-grok-artifact.sh:97:echo '{"vendor":"grok","status":"ok","findings":[]}'
scripts/_codex_harness.sh:398:  echo "    same-vendor caveat is direction-neutral (author=OpenAI, reviewer="
scripts/tests/test-install-sandbox-merge.sh:88:             "registry.npmjs.org", "pypi.org", "files.pythonhosted.org",
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
scripts/tests/test-council-fixture.mjs:9:// egress happens and no vendor binary/secret is touched.
scripts/tests/test-council-fixture.mjs:15://   4. a confirmed finding raised by only one vendor is flagged as a
scripts/tests/test-council-fixture.mjs:16://      cross-vendor DISAGREEMENT (the council's headline signal).
scripts/tests/test-council-fixture.mjs:23:// vendor-specific transport guards: codex keeps the redactor pipe fold
scripts/tests/test-council-fixture.mjs:39://  10. lane vendor identity is canonicalized to the REQUESTED_VENDORS
scripts/tests/test-council-fixture.mjs:41://      model-written vendor differs from its requested position cannot
scripts/tests/test-council-fixture.mjs:42://      impersonate another vendor downstream (scenario J, SRC9).
scripts/tests/test-council-fixture.mjs:48://      redactor/vendor pipeline block (scenario K, SRC10).
scripts/tests/test-council-fixture.mjs:138:const mkFinding = (vendor, n, file, claim) => ({
scripts/tests/test-council-fixture.mjs:139:  finding_id: `${vendor}-${n}`, map_key: 'security', disposition: 'fix',
scripts/tests/test-council-fixture.mjs:141:  risk_tags: ['sec'], author: `council/${vendor}`, file, claim, vendor,
scripts/tests/test-council-fixture.mjs:157:    claude: { vendor: 'claude', status: 'ok', findings: [mkFinding('claude', 1, 'foo.py', shared)] },
scripts/tests/test-council-fixture.mjs:158:    codex: { vendor: 'codex', status: 'ok', findings: [
scripts/tests/test-council-fixture.mjs:162:    grok: { vendor: 'grok', status: 'unavailable', unavailable_reason: 'subscription lapsed', findings: [] },
scripts/tests/test-council-fixture.mjs:174:  const grokUnavail = out.lanes.unavailable.find((u) => u.vendor === 'grok')
scripts/tests/test-council-fixture.mjs:186:  // 4. the codex-only 'bar.py' finding is a cross-vendor DISAGREEMENT
scripts/tests/test-council-fixture.mjs:187:  //    (raised by 1 of 2 available vendors); the shared foo.py one is not.
scripts/tests/test-council-fixture.mjs:188:  const disagreeFiles = out.cross_vendor_disagreements.map((d) => d.file)
scripts/tests/test-council-fixture.mjs:190:    ok('A4: codex-only finding flagged as cross-vendor disagreement; shared one is not')
scripts/tests/test-council-fixture.mjs:201:    claude: { vendor: 'claude', status: 'unavailable', unavailable_reason: 'x', findings: [] },
scripts/tests/test-council-fixture.mjs:202:    codex: { vendor: 'codex', status: 'unavailable', unavailable_reason: 'no binary', findings: [] },
scripts/tests/test-council-fixture.mjs:203:    grok: { vendor: 'grok', status: 'unavailable', unavailable_reason: 'no auth', findings: [] },
scripts/tests/test-council-fixture.mjs:218:    claude: { vendor: 'claude', status: 'ok', findings: [] },
scripts/tests/test-council-fixture.mjs:219:    codex: { vendor: 'codex', status: 'ok', findings: [] },
scripts/tests/test-council-fixture.mjs:220:    grok: { vendor: 'grok', status: 'ok', artifact_sha256: GROK_SHA, findings: [] },
scripts/tests/test-council-fixture.mjs:236:    claude: { vendor: 'claude', status: 'ok', findings: [mkFinding('claude', 1, 'foo.py', 'raised but never re-checked')] },
scripts/tests/test-council-fixture.mjs:237:    codex: { vendor: 'codex', status: 'ok', findings: [] },
scripts/tests/test-council-fixture.mjs:238:    grok: { vendor: 'grok', status: 'ok', artifact_sha256: GROK_SHA, findings: [] },
scripts/tests/test-council-fixture.mjs:260:    claude: { vendor: 'claude', status: 'ok', findings: [mkFinding('claude', 1, 'foo.py', 'claim one')] },
scripts/tests/test-council-fixture.mjs:261:    codex: { vendor: 'codex', status: 'ok', findings: [mkFinding('codex', 1, 'bar.py', 'claim two')] },
scripts/tests/test-council-fixture.mjs:262:    grok: { vendor: 'grok', status: 'ok', artifact_sha256: GROK_SHA, findings: [] },
scripts/tests/test-council-fixture.mjs:288:    claude: { vendor: 'claude', status: 'ok', findings: [mkFinding('claude', 1, 'foo.py', 'stale claim')] },
scripts/tests/test-council-fixture.mjs:289:    codex: { vendor: 'codex', status: 'ok', findings: [mkFinding('codex', 1, 'bar.py', 'another stale claim')] },
scripts/tests/test-council-fixture.mjs:290:    grok: { vendor: 'grok', status: 'ok', artifact_sha256: GROK_SHA, findings: [] },
scripts/tests/test-council-fixture.mjs:310:    claude: { vendor: 'claude', status: 'ok', findings: [mkFinding('claude', 1, 'gone.py', 'pointer into a deleted file')] },
scripts/tests/test-council-fixture.mjs:311:    codex: { vendor: 'codex', status: 'ok', findings: [] },
scripts/tests/test-council-fixture.mjs:312:    grok: { vendor: 'grok', status: 'ok', artifact_sha256: GROK_SHA, findings: [] },
scripts/tests/test-council-fixture.mjs:332:  const grokLane = { vendor: 'grok', status: 'ok',
scripts/tests/test-council-fixture.mjs:336:    claude: { vendor: 'claude', status: 'ok', findings: [] },
scripts/tests/test-council-fixture.mjs:337:    codex: { vendor: 'codex', status: 'ok', findings: [] },
scripts/tests/test-council-fixture.mjs:342:  const grokU = out.lanes.unavailable.find((u) => u.vendor === 'grok')
scripts/tests/test-council-fixture.mjs:360:    claude: { vendor: 'claude', status: 'ok', findings: [] },
scripts/tests/test-council-fixture.mjs:361:    codex: { vendor: 'codex', status: 'ok', findings: [] },
scripts/tests/test-council-fixture.mjs:362:    grok: { vendor: 'grok', status: 'ok', artifact_sha256: GROK_SHA, findings: [] },
scripts/tests/test-council-fixture.mjs:373:// Scenario J (PLAN-161 W2 fix-round-2, codex r2 F13) — vendor impersonation
scripts/tests/test-council-fixture.mjs:374:// neutralized. A lane's model-written vendor field is UNTRUSTED: identity is
scripts/tests/test-council-fixture.mjs:378:// codex-POSITION lane claims vendor:"grok" (with a plausible sha) and stamps
scripts/tests/test-council-fixture.mjs:379:// its finding vendor:"grok" too. Expect: the lane counts as codex,
scripts/tests/test-council-fixture.mjs:384:    vendor: 'grok', status: 'ok', artifact_sha256: 'cd'.repeat(32),
scripts/tests/test-council-fixture.mjs:388:    claude: { vendor: 'claude', status: 'ok', findings: [] },
scripts/tests/test-council-fixture.mjs:389:    codex: impersonator, // the codex-position lane lies about its vendor
scripts/tests/test-council-fixture.mjs:390:    grok: { vendor: 'grok', status: 'ok', artifact_sha256: GROK_SHA, findings: [] },
scripts/tests/test-council-fixture.mjs:417:// no vendor CLI is touched). The operator-controlled scope must arrive in
scripts/tests/test-council-fixture.mjs:431:        const vendor = label.slice('lane:'.length)
scripts/tests/test-council-fixture.mjs:432:        return { vendor, status: 'unavailable', unavailable_reason: 'prompt captured (hermetic test — no live egress)', findings: [] }
scripts/tests/test-council-fixture.mjs:479:// redactor/vendor CLI lines are PARSED by (a) but never executed — only the
scripts/tests/test-council-fixture.mjs:480:// git-ls-files budget line runs, so zero egress and zero vendor calls.
scripts/tests/test-council-fixture.mjs:493:          const vendor = label.slice('lane:'.length)
scripts/tests/test-council-fixture.mjs:494:          return { vendor, status: 'unavailable', unavailable_reason: 'prompt captured (hermetic test — no live egress)', findings: [] }
scripts/tests/test-council-fixture.mjs:562:  // ONE redaction chokepoint, TWO vendor transports. codex — redactor
scripts/tests/test-council-fixture.mjs:635:  // vendor is written back onto every surviving lane object. Behavioral
scripts/tests/test-council-fixture.mjs:638:      && /return \{ \.\.\.l, vendor: requested \}/.test(src)) {
scripts/tests/test-council-fixture.mjs:639:    ok('SRC9: canonical vendor write-back present — lane identity from REQUESTED_VENDORS position (F13)')
scripts/tests/test-council-fixture.mjs:640:  } else bad('SRC9: lane vendor canonicalization write-back MISSING (F13) — a lane can impersonate another vendor downstream')
scripts/tests/test-ownership-table.sh:100:    marker)   printf '.claude/.framework-version' ;;
scripts/tests/test-ownership-table.sh:257:  printf '1.3.1\n' > "$nxt/.claude/.framework-version"

exec
/bin/zsh -lc 'export PYTHONDONTWRITEBYTECODE=1; bash scripts/tests/test-install-upgrade-parity-e2e.sh --positive-control > /tmp/parity-control-review.log 2>&1; rc=$?; echo rc=$rc; grep -E "PLANTED|per-mode verdicts|positive control:" /tmp/parity-control-review.log; tail -80 /tmp/parity-control-review.log' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 118447ms:
rc=1
  PLANTED: dropped backup_and_replace ".claude/commands" from a COPY of
per-mode verdicts (0 parity / 1 fail / 2 known-open): maintainer:1 user:1
positive control: FIRED in every mode (rc=1 each) — the gate is alive.
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

  FATAL [MISSING_IN_B] — install delivered these; the upgrade never did — an upgraded adopter simply does not have them
    - .claude/commands/night-mode.md

  FATAL [STALE] — the upgrade left the v1.2.0 generation in place while the framework changed the file — F3's exact signature
    - .claude/commands/ceo-boot.md

  WARNING — declared ACCEPTED patterns that matched nothing in this
  mode. For a GENERATED path that means the declaration is dead and
  should go; for a PRESERVE-CONTRACT path (agent-metrics, CLAUDE.md,
  MEMORY.md) it just means the template did not change between the
  two generations, which is expected. Informational, never fatal:
    - ^\.claude/agent-metrics\.md$
    - ^(CLAUDE|MEMORY)\.md$
    - ^\.gitignore$

  verdict(mode=user): FAIL
--------------------------------------------------------------

--------------------------------------------------------------
per-mode verdicts (0 parity / 1 fail / 2 known-open): maintainer:1 user:1
positive control: FIRED in every mode (rc=1 each) — the gate is alive.

==============================================================
RESULT: FAIL (exit 1) — undeclared install/upgrade divergence above.
==============================================================

exec
/bin/zsh -lc "git diff -- .claude/scripts/tests/test_release_workflow_asserts.py | rg -n \"os\\.environ|patch\\.dict|TestEnvContext|tempfile|NamedTemporary\" | sed -n '1,260p'; git diff -- .claude/scripts/tests/test_release_workflow_asserts.py | sed -n '1,240p'" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
181:@@ -219,7 +372,8 @@ class WorkflowHygieneTest(TestEnvContext):
191:@@ -233,7 +387,8 @@ class WorkflowHygieneTest(TestEnvContext):
201:@@ -335,5 +490,527 @@ class WaveB5NpmPublishYmlTest(TestEnvContext):
205:+class Plan166AwaitGateTest(TestEnvContext):
315:+class TrustedPublisherBindingTest(TestEnvContext):
456:+class W1BReleaseGateDeltaAncestryTest(TestEnvContext):
641:+class W1BReleaseGateJobNameTest(TestEnvContext):
669:+class W1BGuardModuleContractTest(TestEnvContext):
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
