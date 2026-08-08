OpenAI Codex v0.144.6
--------
workdir: /Users/joaocanhada/canhada-labs/ceo-orchestration
model: gpt-5.6-sol
provider: openai
approval: never
sandbox: workspace-write [workdir, /tmp, $TMPDIR]
reasoning effort: xhigh
reasoning summaries: none
session id: 019fdee6-8595-77b3-9c1a-41cc361c4989
--------
user
current changes
exec
/bin/zsh -lc "git status --short && printf '\\n--- unstaged diff stat ---\\n' && git diff --stat && printf '\\n--- staged diff stat ---\\n' && git diff --cached --stat" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
 M .claude/scripts/tests/test_release_workflow_asserts.py
 M .github/workflows/smoke-install.yml
 M CLAUDE.md
 M README.md
 M README.pt-BR.md
 M docs/ARCHITECTURE.md
 M docs/CTO-GUIDE.md
 M docs/FAQ.md
 M docs/README.md
 M docs/ownership-decision-table.md
 M npm/README.md
 M scripts/_framework_manifest_set.sh
 M scripts/install.sh
 M scripts/tests/ownership-baseline-map.txt
 M scripts/tests/ownership_table.tsv
 M scripts/tests/test-ownership-table.sh
 M scripts/upgrade.sh
?? .claude/adr/ADR-190-ownership-decision-table-contract.md
?? .claude/plans/PLAN-166/archive/w1-staged-pack-20260806-0159.tar.gz
?? .claude/plans/PLAN-166/archive/w1-staged-pack-final-20260806-0722.tar.gz
?? .claude/plans/PLAN-167/OWNER-PREPARE-TO-SIGN.sh
?? .claude/plans/PLAN-167/W4-approved.md
?? .claude/plans/PLAN-167/W4-approved.md.asc
?? .claude/plans/PLAN-168/approved.md
?? .claude/plans/PLAN-168/approved.md.asc
?? .claude/plans/PLAN-168/archive/
?? .claude/plans/PLAN-168/rail/codex-pack-r1.md
?? .github/workflows/ownership-nightly.yml
?? scripts/tests/ownership-expected-reds.txt
?? scripts/tests/ownership-nightly-gate.sh
?? scripts/tests/test-ownership-nightly-gate.sh
?? scripts/tests/test-protocol-pointer-inv4.sh
?? scripts/tests/test-protocol-pointer-render.sh

--- unstaged diff stat ---
 .../scripts/tests/test_release_workflow_asserts.py | 169 +++++++++++++++++++++
 .github/workflows/smoke-install.yml                |  61 ++++++++
 CLAUDE.md                                          |   4 +-
 README.md                                          |   4 +-
 README.pt-BR.md                                    |   4 +-
 docs/ARCHITECTURE.md                               |   6 +-
 docs/CTO-GUIDE.md                                  |   6 +-
 docs/FAQ.md                                        |   2 +-
 docs/README.md                                     |   2 +-
 docs/ownership-decision-table.md                   |  26 +++-
 npm/README.md                                      |   4 +-
 scripts/_framework_manifest_set.sh                 | 124 +++++++++++++++
 scripts/install.sh                                 |  58 +++----
 scripts/tests/ownership-baseline-map.txt           |  15 +-
 scripts/tests/ownership_table.tsv                  |   3 +
 scripts/tests/test-ownership-table.sh              |  90 +++++++++--
 scripts/upgrade.sh                                 | 110 ++++++++++----
 17 files changed, 582 insertions(+), 106 deletions(-)

--- staged diff stat ---

exec
/bin/zsh -lc 'git diff -- .claude/scripts/tests/test_release_workflow_asserts.py .github/workflows/smoke-install.yml scripts/_framework_manifest_set.sh scripts/install.sh scripts/upgrade.sh scripts/tests/ownership-baseline-map.txt scripts/tests/ownership_table.tsv scripts/tests/test-ownership-table.sh' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
diff --git a/.claude/scripts/tests/test_release_workflow_asserts.py b/.claude/scripts/tests/test_release_workflow_asserts.py
index 3518bb3..45a4de0 100644
--- a/.claude/scripts/tests/test_release_workflow_asserts.py
+++ b/.claude/scripts/tests/test_release_workflow_asserts.py
@@ -1012,5 +1012,174 @@ class W1BGuardModuleContractTest(TestEnvContext):
         self.assertEqual(len(codes), len(set(codes)))
 
 
+# --- PLAN-168 W1 (AC-1/AC-2/AC-4) ------------------------------------
+# Marker written into the PLAN-168 smoke-install.yml + ownership-nightly.yml
+# edits; its presence in the LIVE file means the W1 ceremony landed and the
+# live copy is authoritative (same convention as _MARKER / _MARKER_166).
+_MARKER_168 = "PLAN-168 W1"
+_STAGED_168 = _REPO / ".claude" / "plans" / "PLAN-168" / "staged"
+_STAGED_168_WF = _STAGED_168 / ".github" / "workflows"
+
+# AC-1/AC-2: paths that MUST be present in BOTH smoke-install filter lists.
+# _hash_lib.sh is the r10-F4 regression pin (it was already wired; this
+# assert keeps it that way — AC-2 is an assertion, not work).
+_OWNERSHIP_FILTER_PATHS = frozenset({
+    "scripts/_hash_lib.sh",
+    "scripts/_framework_manifest_set.sh",
+    "scripts/tests/test-ownership-verdict-unit.sh",
+    "scripts/tests/test-ownership-table.sh",
+    "scripts/tests/ownership_table.tsv",
+    "docs/ownership-decision-table.md",
+    # rail r3 P1: the nightly gate + controls must be per-PR gated too.
+    "scripts/tests/ownership-nightly-gate.sh",
+    "scripts/tests/test-ownership-nightly-gate.sh",
+    "scripts/tests/ownership-expected-reds.txt",
+    "scripts/tests/test-protocol-pointer-render.sh",
+    "scripts/tests/test-protocol-pointer-inv4.sh",
+})
+
+
+def _plan168_text(name: str) -> Optional[Tuple[str, str]]:
+    """Return (text, context) for a PLAN-168 workflow edit, or None pre-landing."""
+    live = _WF / name
+    if live.is_file():
+        live_text = live.read_text(encoding="utf-8")
+        if _MARKER_168 in live_text:
+            return live_text, "live"
+    staged = _STAGED_168_WF / name
+    if staged.is_file():
+        return staged.read_text(encoding="utf-8"), "staged"
+    return None
+
+
+def _workflow_paths_lists(text: str) -> Tuple[list, list]:
+    """Extract (pull_request.paths, push.paths) entries from workflow text.
+
+    Text-based on purpose (this file's convention — no yaml dependency in
+    the stdlib-only posture). Collects quoted `- "..."` items under each
+    `paths:` key, skipping comments, stopping at the first line that
+    dedents to the `paths:` level or shallower.
+    """
+    results = []
+    for trigger in ("pull_request:", "push:"):
+        lines = text.splitlines()
+        try:
+            t_idx = next(
+                i for i, ln in enumerate(lines)
+                if ln.strip() == trigger
+                and (len(ln) - len(ln.lstrip())) == 2
+            )
+        except StopIteration:
+            results.append([])
+            continue
+        entries = []
+        paths_indent = None
+        for ln in lines[t_idx + 1:]:
+            stripped = ln.strip()
+            indent = len(ln) - len(ln.lstrip())
+            if stripped and indent <= 2:
+                break  # next trigger / top-level key
+            if paths_indent is None:
+                if stripped == "paths:":
+                    paths_indent = indent
+                continue
+            if not stripped or stripped.startswith("#"):
+                continue
+            if indent <= paths_indent:
+                break
+            m = re.match(r'-\s+"([^"]+)"', stripped)
+            if m:
+                entries.append(m.group(1))
+        results.append(entries)
+    return results[0], results[1]
+
+
+class Plan168OwnershipWiringTest(TestEnvContext):
+    """AC-1/AC-2: the ownership oracles are WIRED, and the two smoke-install
+    filter lists cannot drift apart again (the r10-F4 "red gate nobody
+    runs" class, closed as an assertion instead of a memory)."""
+
+    def _smoke(self) -> Tuple[str, str]:
+        ctx = _plan168_text("smoke-install.yml")
+        if ctx is None:
+            self.skipTest(
+                "PLAN-168 W1 not landed and no staged copy on disk "
+                "(pre-landing CI window)"
+            )
+        return ctx
+
+    def test_filter_lists_are_identical(self):
+        text, _ = self._smoke()
+        pr, push = _workflow_paths_lists(text)
+        self.assertTrue(pr, "pull_request paths filter not found/empty")
+        self.assertTrue(push, "push paths filter not found/empty")
+        # Name-by-name set equality, both directions, duplicates rejected —
+        # the file's own comment says KEEP IDENTICAL.
+        self.assertEqual(
+            len(pr), len(set(pr)), "duplicate entries in pull_request paths")
+        self.assertEqual(
+            len(push), len(set(push)), "duplicate entries in push paths")
+        self.assertEqual(
+            sorted(pr), sorted(push),
+            "smoke-install pull_request and push paths filters have drifted",
+        )
+
+    def test_ownership_paths_present_in_both_filters(self):
+        text, _ = self._smoke()
+        pr, push = _workflow_paths_lists(text)
+        for required in sorted(_OWNERSHIP_FILTER_PATHS):
+            self.assertIn(
+                required, pr, f"{required} missing from pull_request paths")
+            self.assertIn(
+                required, push, f"{required} missing from push paths")
+
+    def test_unit_oracle_step_wired(self):
+        text, _ = self._smoke()
+        steps = text.split("steps:", 1)[-1]
+        self.assertIn(
+            "scripts/tests/test-ownership-verdict-unit.sh", steps,
+            "unit oracle step missing from the smoke job",
+        )
+        self.assertIn(
+            "scripts/tests/test-ownership-nightly-gate.sh", steps,
+            "nightly-gate positive control step missing from the smoke job",
+        )
+        self.assertIn(
+            "scripts/tests/test-protocol-pointer-render.sh", steps,
+            "pointer render control step missing from the smoke job",
+        )
+
+    def test_nightly_workflow_contract(self):
+        ctx = _plan168_text("ownership-nightly.yml")
+        if ctx is None:
+            self.skipTest(
+                "PLAN-168 W1 not landed and no staged copy on disk "
+                "(pre-landing CI window)"
+            )
+        text, _ = ctx
+        self.assertIn("schedule:", text, "nightly trigger missing")
+        self.assertIn("cron:", text, "cron expression missing")
+        self.assertIn("workflow_dispatch:", text, "manual dispatch missing")
+        self.assertIn(
+            "scripts/tests/ownership-nightly-gate.sh", text,
+            "the gate script is not what the nightly runs",
+        )
+        self.assertIn(
+            "scripts/tests/test-ownership-nightly-gate.sh", text,
+            "gate positive control step missing",
+        )
+        self.assertIn(
+            "scripts/tests/test-protocol-pointer-inv4.sh", text,
+            "INV-4 4-leg e2e step missing from the nightly",
+        )
+        # --map is a reporting mode that exits 0 over failures — a dead gate
+        # by construction (harness NOTE, PLAN-168 debate r1 QA must-fix 2).
+        # Prose in comments may mention it; an INVOCATION is the harness
+        # name followed by --map on the same line.
+        for ln in text.splitlines():
+            if "test-ownership-table.sh" in ln and "--map" in ln:
+                self.fail(f"--map wired into the nightly gate: {ln.strip()}")
+
+
 if __name__ == "__main__":
     unittest.main()
diff --git a/.github/workflows/smoke-install.yml b/.github/workflows/smoke-install.yml
index 5794f0b..ddf2165 100644
--- a/.github/workflows/smoke-install.yml
+++ b/.github/workflows/smoke-install.yml
@@ -25,6 +25,27 @@ on:
       # scripts/tests/*.sh runs ONLY in this workflow (same r11/r20 wiring
       # rule as the parity e2e above).
       - "scripts/tests/test-upgrade-spec-ownership.sh"
+      # PLAN-168 W1 (AC-1): the PLAN-167 ownership oracles + their truth
+      # table + contract doc. The unit oracle runs per-PR in THIS workflow;
+      # the ~25-min e2e runs in ownership-nightly.yml (schedule: ignores
+      # paths:, so it cannot live behind this filter) — but a PR touching
+      # the table/harness/contract must still light up the fast gate here.
+      # Without these entries, a PR changing only the table skips the gate
+      # entirely: the r10-F4 "red gate nobody runs" class, again.
+      - "scripts/tests/test-ownership-verdict-unit.sh"
+      - "scripts/tests/test-ownership-table.sh"
+      - "scripts/tests/ownership_table.tsv"
+      - "docs/ownership-decision-table.md"
+      # PLAN-168 W1+W2 (rail r3 P1): the nightly gate + its positive control
+      # get fast per-PR steps HERE too — without these entries a PR could
+      # break the gate's rc/status handling while every PR check stays green.
+      # The pointer-generator render control is the per-PR half of INV-4
+      # (the full 4-leg e2e runs in ownership-nightly.yml).
+      - "scripts/tests/ownership-nightly-gate.sh"
+      - "scripts/tests/test-ownership-nightly-gate.sh"
+      - "scripts/tests/ownership-expected-reds.txt"
+      - "scripts/tests/test-protocol-pointer-render.sh"
+      - "scripts/tests/test-protocol-pointer-inv4.sh"
       - "templates/**"
       # Widened from SPEC/v1/install-cli.md: SPEC/v1 is delivered by install.sh
       # and (until F3) by nothing in upgrade.sh, so ANY SPEC/v1 change is a
@@ -58,6 +79,20 @@ on:
       - "scripts/tests/test-install-upgrade-parity-e2e.sh"
       - "scripts/tests/_parity_classify.py"
       - "scripts/tests/test-upgrade-spec-ownership.sh"
+      - "scripts/tests/test-ownership-verdict-unit.sh"
+      - "scripts/tests/test-ownership-table.sh"
+      - "scripts/tests/ownership_table.tsv"
+      - "docs/ownership-decision-table.md"
+      # PLAN-168 W1+W2 (rail r3 P1): the nightly gate + its positive control
+      # get fast per-PR steps HERE too — without these entries a PR could
+      # break the gate's rc/status handling while every PR check stays green.
+      # The pointer-generator render control is the per-PR half of INV-4
+      # (the full 4-leg e2e runs in ownership-nightly.yml).
+      - "scripts/tests/ownership-nightly-gate.sh"
+      - "scripts/tests/test-ownership-nightly-gate.sh"
+      - "scripts/tests/ownership-expected-reds.txt"
+      - "scripts/tests/test-protocol-pointer-render.sh"
+      - "scripts/tests/test-protocol-pointer-inv4.sh"
       - "templates/**"
       - "SPEC/v1/**"
       - "scripts/doctor.sh"
@@ -129,6 +164,32 @@ jobs:
           fi
           jq --version
 
+      # PLAN-168 W1 (AC-4, per-PR half): the DECISION oracle —
+      # _ownership_verdict() against every truth-table cell, in milliseconds.
+      # The OBSERVATION half (the ~25-min e2e) runs in ownership-nightly.yml;
+      # this fast half is what makes table/harness PRs cheap to gate.
+      - name: Ownership verdict unit oracle (milliseconds)
+        run: |
+          set -euo pipefail
+          bash scripts/tests/test-ownership-verdict-unit.sh
+
+      # PLAN-168 W1 (rail r3 P1): the nightly gate's fake-harness control is
+      # milliseconds — run it per-PR so a PR touching the gate cannot break
+      # its rc/status handling while PR checks stay green.
+      - name: Ownership nightly-gate positive control (fake harness)
+        run: |
+          set -euo pipefail
+          bash scripts/tests/test-ownership-nightly-gate.sh
+
+      # PLAN-168 W2 (AC-6, per-PR half of INV-4): the shared pointer
+      # generator's 8-scenario control — includes ONE real install (~1-2 min
+      # on CI iron). The full install->upgrade->cure e2e (4 legs, ~5 min CI)
+      # is nightly-only; MEASURED per the smoke budget notes above.
+      - name: Protocol pointer render control (generator parity)
+        run: |
+          set -euo pipefail
+          bash scripts/tests/test-protocol-pointer-render.sh
+
       - name: Run smoke install
         run: |
           set -euo pipefail
diff --git a/scripts/_framework_manifest_set.sh b/scripts/_framework_manifest_set.sh
index 6a7bc1b..b123b1c 100644
--- a/scripts/_framework_manifest_set.sh
+++ b/scripts/_framework_manifest_set.sh
@@ -555,6 +555,15 @@ _ownership_verdict() {
     _ov_owned=1                                   # new delivery
   elif [ "$_ov_lcontent" = "pristine" ] || [ "$_ov_lcontent" = "legacy_pristine" ]; then
     _ov_owned=1                                   # current-source takeover / legacy migration
+  elif [ "$_ov_lcontent" = "degraded" ]; then
+    # PLAN-168 W2 (AC-6b, Owner decision D2): a DEGRADED body — byte-exact
+    # reconstruction of the {{PROTOCOL_SOURCE}}-literal template the broken
+    # upgrade wrote (recognized by _protocol_pointer_is_degraded, NEVER by
+    # substring) — is the framework's own output, not adopter content. Owned
+    # even without a delivery record, same content-proven takeover doctrine
+    # as legacy_pristine (the r20 precedent). Downstream this falls into the
+    # protocol REFRESH route: the cure, with the standard backup.
+    _ov_owned=1
   fi
   # legacy_pristine_partial is deliberately NOT owned: every regular file may
   # match a shipped release, but a tree carrying an entry the fingerprint
@@ -595,3 +604,118 @@ _ownership_verdict() {
     *)        printf 'REFRESH HASH_SOURCE' ;;
   esac
 }
+# =============================================================================
+# PLAN-168 W2 (AC-6, Owner decision D1-b) — the ONE protocol-pointer generator.
+#
+# INV-4 existed because install.sh and upgrade.sh each carried a private copy
+# of the pointer heredoc: install substituted {{PROTOCOL_SOURCE}} in a later
+# pass, upgrade hashed (and on REFRESH wrote) the body with the token still
+# literal. Two bodies for the same file. This library is the cure for the
+# CLASS: both callers render through the same function, so the bodies cannot
+# diverge again (ADR-155 decision (i), applied to CONTENT — the shared
+# enumeration solved WHICH paths both sides touch; this solves WHAT they
+# produce).
+#
+# Sourced by scripts/install.sh and scripts/upgrade.sh (same $SCRIPT_DIR
+# pattern as _hash_lib.sh). Bash 3.2-compatible, stdlib/POSIX-tools only.
+#
+# Functions:
+#   _render_protocol_pointer SOURCE_DIR TARGET PROFILE STACK PROTOCOL_SOURCE
+#       Emit the COMPLETE healthy file content ("# Protocol reference" header
+#       included, trailing newline included). Inside-target checkouts get the
+#       relative form; everything else gets the PROTOCOL_SOURCE-resolved form
+#       (never the literal token — the caller passes the resolved value).
+#   _render_protocol_pointer_degraded TARGET PROFILE STACK
+#       Emit the DEGRADED file content: the outside-target template with
+#       {{PROTOCOL_SOURCE}} kept literal. This is byte-for-byte what the
+#       pre-PLAN-168 upgrade.sh wrote on every refresh — the template text is
+#       IDENTICAL across v1.0.1, v1.1.0, v1.2.0 and HEAD (verified by
+#       extracting and diffing all four), so ONE skeleton covers the shipped
+#       population. Residual out of scope: pre-v1.0.1 trees.
+#   _protocol_pointer_is_degraded FILE
+#       rc=0 iff FILE is EXACTLY a degraded body the framework produced:
+#       the invocation-specific values (TARGET/PROFILE/STACK) are extracted
+#       from the file's own upgrade line, the degraded template is re-rendered
+#       with them, and the reconstruction must be byte-identical. Any parse
+#       failure, any adopter edit anywhere, any deviation => rc=1 (fail toward
+#       PRESERVATION — codex rail r1 P1: substring matching would destroy an
+#       adopter file that legitimately CONTAINS the token; rail r2 P1: static
+#       whole-body hashes cannot match invocation-specific bodies).
+# =============================================================================
+
+_render_protocol_pointer() {
+  # $1=SOURCE_DIR $2=TARGET $3=PROFILE $4=STACK $5=PROTOCOL_SOURCE(resolved)
+  _rpp_src="$1"; _rpp_target="$2"; _rpp_profile="$3"; _rpp_stack="$4"; _rpp_psource="$5"
+  case "$_rpp_src" in
+    "$_rpp_target"/*)
+      _rpp_rel="${_rpp_src#"$_rpp_target"/}"
+      printf '%s\n' \
+        "# Protocol reference" \
+        "" \
+        "The full CEO orchestration protocol lives at:" \
+        "./${_rpp_rel}/PROTOCOL.md" \
+        "" \
+        "To pull updates:" \
+        "  ( cd ./${_rpp_rel} && git pull )" \
+        "  ./${_rpp_rel}/scripts/upgrade.sh . --profile $_rpp_profile --stack $_rpp_stack"
+      ;;
+    *)
+      # The healthy outside-target form: the degraded template with the token
+      # substituted EVERYWHERE — exactly what install.sh's placeholder pass
+      # has always produced, so existing healthy pointers keep their digest.
+      _render_protocol_pointer_degraded "$_rpp_target" "$_rpp_profile" "$_rpp_stack" \
+        | sed "s|{{PROTOCOL_SOURCE}}|$( printf '%s' "$_rpp_psource" | sed 's/[|&\\]/\\&/g' )|g"
+      ;;
+  esac
+}
+
+_render_protocol_pointer_degraded() {
+  # $1=TARGET $2=PROFILE $3=STACK — the token stays LITERAL. This is both the
+  # historical broken-upgrade output (the cure's recognition target) and the
+  # pre-substitution install body (one template, one truth).
+  _rppd_target="$1"; _rppd_profile="$2"; _rppd_stack="$3"
+  printf '%s\n' \
+    "# Protocol reference" \
+    "" \
+    "The full CEO orchestration protocol lives at:" \
+    "{{PROTOCOL_SOURCE}}/PROTOCOL.md" \
+    "" \
+    "Edit {{PROTOCOL_SOURCE}} to point at your ceo-orchestration checkout" \
+    "(e.g. ../ceo-orchestration or \$HOME/src/ceo-orchestration)." \
+    "" \
+    "To pull updates:" \
+    "  ( cd {{PROTOCOL_SOURCE}} && git pull )" \
+    "  {{PROTOCOL_SOURCE}}/scripts/upgrade.sh $_rppd_target --profile $_rppd_profile --stack $_rppd_stack"
+}
+
+_protocol_pointer_is_degraded() {
+  # $1=FILE. rc=0 iff the file is byte-identical to a degraded render whose
+  # TARGET/PROFILE/STACK come from the file's own last line. Everything else
+  # (missing file, unparseable line, values with spaces, any edit) => rc=1.
+  _ppid_file="$1"
+  [ -f "$_ppid_file" ] || return 1
+  # Cheap pre-filter: files without the literal token can never be degraded.
+  grep -F -q '{{PROTOCOL_SOURCE}}' "$_ppid_file" 2>/dev/null || return 1
+
+  # The upgrade line is the ONE line carrying all three invocation values:
+  #   {{PROTOCOL_SOURCE}}/scripts/upgrade.sh <target> --profile <p> --stack <s>
+  _ppid_line="$( grep -F '{{PROTOCOL_SOURCE}}/scripts/upgrade.sh ' "$_ppid_file" 2>/dev/null | head -1 )"
+  [ -n "$_ppid_line" ] || return 1
+
+  # POSIX-safe field extraction; single-token values only. A target/profile/
+  # stack containing whitespace makes the line ambiguous => no match =>
+  # preserved (documented residual, consistent with fail-toward-preservation).
+  _ppid_target="$( printf '%s\n' "$_ppid_line" | sed -n 's|.*scripts/upgrade\.sh \([^ ][^ ]*\) --profile .*|\1|p' )"
+  _ppid_profile="$( printf '%s\n' "$_ppid_line" | sed -n 's|.* --profile \([^ ][^ ]*\) --stack .*|\1|p' )"
+  _ppid_stack="$( printf '%s\n' "$_ppid_line" | sed -n 's|.* --stack \([^ ][^ ]*\)$|\1|p' )"
+  [ -n "$_ppid_target" ] && [ -n "$_ppid_profile" ] && [ -n "$_ppid_stack" ] || return 1
+
+  _ppid_tmp="$( mktemp "${TMPDIR:-/tmp}/ceo-ptr-recon.XXXXXX" )" || return 1
+  _render_protocol_pointer_degraded "$_ppid_target" "$_ppid_profile" "$_ppid_stack" > "$_ppid_tmp"
+  if cmp -s "$_ppid_tmp" "$_ppid_file"; then
+    rm -f "$_ppid_tmp" 2>/dev/null
+    return 0
+  fi
+  rm -f "$_ppid_tmp" 2>/dev/null
+  return 1
+}
diff --git a/scripts/install.sh b/scripts/install.sh
index 3ffe451..c0a0425 100755
--- a/scripts/install.sh
+++ b/scripts/install.sh
@@ -1884,50 +1884,34 @@ install_protocol_pointer() {
     return 0
   fi
 
-  # Compute a relative path from $TARGET to $SOURCE_DIR when possible.
-  # If the framework repo lives outside the target repo (common case),
-  # we fall back to {{PROTOCOL_SOURCE}} which the user substitutes
-  # manually. Absolute paths are NOT hardcoded — they break portability
-  # across dev machines and CI runners.
+  # PLAN-168 W2 (AC-6, Owner decision D1-b): the body comes from the ONE
+  # shared generator in _framework_manifest_set.sh — never a private heredoc.
+  # INV-4 existed because this function and upgrade.sh each carried their own
+  # copy of this text; a silent local fallback would resurrect the class, so
+  # a missing generator is a broken checkout and fails LOUD.
   #
-  # Relative-path heuristic: if $SOURCE_DIR starts with $TARGET, the
-  # framework was copied INTO the target — use a relative pointer. In
-  # ALL other cases (e.g. adopter clones framework elsewhere), we emit
-  # the user-editable {{PROTOCOL_SOURCE}} marker and document next steps.
-  local pointer_body
-  case "$SOURCE_DIR" in
-    "$TARGET"/*)
-      local rel="${SOURCE_DIR#$TARGET/}"
-      pointer_body="The full CEO orchestration protocol lives at:
-./${rel}/PROTOCOL.md
-
-To pull updates:
-  ( cd ./${rel} && git pull )
-  ./${rel}/scripts/upgrade.sh . --profile $PROFILE --stack $STACK"
-      ;;
-    *)
-      pointer_body="The full CEO orchestration protocol lives at:
-{{PROTOCOL_SOURCE}}/PROTOCOL.md
-
-Edit {{PROTOCOL_SOURCE}} to point at your ceo-orchestration checkout
-(e.g. ../ceo-orchestration or \$HOME/src/ceo-orchestration).
-
-To pull updates:
-  ( cd {{PROTOCOL_SOURCE}} && git pull )
-  {{PROTOCOL_SOURCE}}/scripts/upgrade.sh $TARGET --profile $PROFILE --stack $STACK"
-      ;;
-  esac
+  # Relative-path heuristic (unchanged): if $SOURCE_DIR starts with $TARGET,
+  # the framework was copied INTO the target — relative pointer. In ALL other
+  # cases the body is written with the user-editable {{PROTOCOL_SOURCE}}
+  # marker and the placeholder substitution pass below resolves it.
+  command -v _render_protocol_pointer >/dev/null 2>&1 || {
+    echo "    ERROR: _render_protocol_pointer unavailable (scripts/_framework_manifest_set.sh not sourced) — cannot write PROTOCOL.md pointer" >&2
+    return 1
+  }
 
   if [[ "$DRY_RUN" -eq 1 ]]; then
     echo "    (dry-run) would CREATE: PROTOCOL.md (pointer)"
     return 0
   fi
 
-  cat > "$TARGET/PROTOCOL.md" <<EOF
-# Protocol reference
-
-$pointer_body
-EOF
+  case "$SOURCE_DIR" in
+    "$TARGET"/*)
+      _render_protocol_pointer "$SOURCE_DIR" "$TARGET" "$PROFILE" "$STACK" "" > "$TARGET/PROTOCOL.md"
+      ;;
+    *)
+      _render_protocol_pointer_degraded "$TARGET" "$PROFILE" "$STACK" > "$TARGET/PROTOCOL.md"
+      ;;
+  esac
   echo "    CREATED: PROTOCOL.md (pointer)"
   _state_record_op "install_protocol_pointer" "PROTOCOL.md"
   # PLAN-166 F3 (ADR-155-AMEND-1): registered delivery — this line is only
diff --git a/scripts/tests/ownership-baseline-map.txt b/scripts/tests/ownership-baseline-map.txt
index df2dbd4..05749b0 100644
--- a/scripts/tests/ownership-baseline-map.txt
+++ b/scripts/tests/ownership-baseline-map.txt
@@ -1,8 +1,8 @@
 == PLAN-167 ownership decision table ==
-   table:  /tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553/scripts/tests/ownership_table.tsv
-   source: /tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
-   scratch:/var/folders/9n/hm9srl0s1nz45_p12tj61pd80000gn/T//plan167-own.toQDrn
-   timeout:60s/cell   timeout-bin:<fallback>
+   table:  scripts/tests/ownership_table.tsv
+   source: <repo>
+   scratch:<scratch>
+   timeout:60s/cell   timeout-bin:<bin>
 
 OWN-0001   GREEN   exp=DELIVER         /HASH_SOURCE            got=DELIVER         /HASH_SOURCE            rc=0   adr-155
 OWN-0002   GREEN   exp=DELIVER         /HASH_CANONICAL_POINTER got=DELIVER         /HASH_CANONICAL_POINTER rc=0   adr-155
@@ -60,11 +60,14 @@ OWN-0070   GREEN   exp=PRESERVE_OWNED  /HASH_SOURCE            got=PRESERVE_OWNE
 OWN-0071   GREEN   exp=PRESERVE_OWNED  /HASH_PRIOR_RECORD      got=PRESERVE_OWNED  /HASH_PRIOR_RECORD      rc=0   r7-F2
 OWN-0072   GREEN   exp=PRESERVE_OWNED  /HASH_PRIOR_RECORD      got=PRESERVE_OWNED  /HASH_PRIOR_RECORD      rc=0   r9-F2
 OWN-0073   GREEN   exp=REFRESH         /HASH_SOURCE            got=REFRESH         /HASH_SOURCE            rc=0   adr-155-amend-1
-OWN-0074   RED     exp=PRESERVE_OWNED  /HASH_CANONICAL_POINTER got=PRESERVE_OWNED  /HASH_UNCLASSIFIED      rc=0   derived
+OWN-0074   GREEN   exp=PRESERVE_OWNED  /HASH_CANONICAL_POINTER got=PRESERVE_OWNED  /HASH_CANONICAL_POINTER rc=0   derived
 OWN-0080   GREEN   exp=PRESERVE_UNOWNED/HASH_NONE              got=PRESERVE_UNOWNED/HASH_NONE              rc=0   r9-F4
 OWN-0081   GREEN   exp=PRESERVE_UNOWNED/HASH_NONE              got=PRESERVE_UNOWNED/HASH_NONE              rc=0   r11-F3
 OWN-0082   GREEN   exp=PRESERVE_OWNED  /HASH_PRIOR_RECORD      got=PRESERVE_OWNED  /HASH_PRIOR_RECORD      rc=0   adr-155-amend-1
 OWN-0090   GREEN   exp=REFRESH         /HASH_SOURCE            got=REFRESH         /HASH_SOURCE            rc=0   r7-F1
 OWN-0091   GREEN   exp=PRESERVE_OWNED  /HASH_SOURCE            got=PRESERVE_OWNED  /HASH_SOURCE            rc=0   r7-F1
+OWN-0092   GREEN   exp=REFRESH         /HASH_CANONICAL_POINTER got=REFRESH         /HASH_CANONICAL_POINTER rc=0   plan-168
+OWN-0093   GREEN   exp=REFRESH         /HASH_CANONICAL_POINTER got=REFRESH         /HASH_CANONICAL_POINTER rc=0   plan-168
+OWN-0094   GREEN   exp=PRESERVE_OWNED  /HASH_PRIOR_RECORD      got=PRESERVE_OWNED  /HASH_PRIOR_RECORD      rc=0   plan-168
 
-GREEN=58  RED=4  AMBIG=0  HARNESS-ERR=0
+GREEN=62  RED=3  AMBIG=0  HARNESS-ERR=0
diff --git a/scripts/tests/ownership_table.tsv b/scripts/tests/ownership_table.tsv
index e51d2c3..369fb37 100644
--- a/scripts/tests/ownership_table.tsv
+++ b/scripts/tests/ownership_table.tsv
@@ -67,3 +67,6 @@ OWN-0082	spec	hash	dir	pristine	no	copy	maintainer	upgrade	none	none	PRESERVE_OW
 OWN-0090	marker	hash	regular	edited	yes	copy	maintainer	upgrade	none	none	REFRESH	HASH_SOURCE	r7-F1	reader rule: checker must verify live bytes against the record
 OWN-0091	marker	hash	regular	edited	yes	copy	maintainer	install_rerun	none	none	PRESERVE_OWNED	HASH_SOURCE	r7-F1	1.3.0->9.9.9 edit must not suppress a real update
 OWN-0074	protocol	hash	regular	edited	yes	copy	maintainer	upgrade	none	none	PRESERVE_OWNED	HASH_CANONICAL_POINTER	derived	ADOPTER-CUSTOMIZED pointer on the NORMAL upgrade path — the verified S238 case; the digest stays canonical so the next upgrade does not read H_dst==H_base and clobber it
+OWN-0092	protocol	hash	regular	degraded	yes	copy	maintainer	upgrade	none	none	REFRESH	HASH_CANONICAL_POINTER	plan-168	the CURE (AC-6b): framework-degraded body ({{PROTOCOL_SOURCE}} literal, byte-exact template reconstruction) is the framework own garbage - REFRESH with backup, never preserved
+OWN-0093	protocol	none	regular	degraded	yes	copy	maintainer	upgrade	none	none	REFRESH	HASH_CANONICAL_POINTER	plan-168	recordless degraded takeover - content-proven framework origin, same doctrine as legacy_pristine (r20)
+OWN-0094	protocol	hash	regular	degraded	yes	copy	user	upgrade	none	none	PRESERVE_OWNED	HASH_PRIOR_RECORD	plan-168	user ceremony cannot cure - WS4: a user ceremony never writes root surfaces; the A2 carry preserves and the degraded body waits for a maintainer upgrade
diff --git a/scripts/tests/test-ownership-table.sh b/scripts/tests/test-ownership-table.sh
index ae12049..638934b 100755
--- a/scripts/tests/test-ownership-table.sh
+++ b/scripts/tests/test-ownership-table.sh
@@ -16,6 +16,9 @@
 #   test-ownership-table.sh --map        emit the map only (no pass/fail exit)
 #   test-ownership-table.sh --list       list row ids and exit
 #   test-ownership-table.sh --keep       keep the scratch dir (debugging)
+#   test-ownership-table.sh --print-legacy-tag   print the pinned legacy tag
+#   test-ownership-table.sh --stable-header      machine-independent header
+#                                        (for RECORDING a committable baseline)
 #
 # Exit: 0 = every row matched its expected pair. 1 = at least one mismatch.
 #       2 = harness/usage error (never confused with a row failure).
@@ -29,11 +32,18 @@ SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
 REPO_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
 TSV="$SCRIPT_DIR/ownership_table.tsv"
 
+# The ONE copy of the legacy-pristine pin. The legacy_pristine* fixtures build
+# from this tag, and CI fetches it via --print-legacy-tag — the workflow never
+# hardcodes a second copy of this truth (PLAN-168 W1, same --print-pin shape
+# as test-install-upgrade-parity-e2e.sh).
+LEGACY_TAG="v1.2.0"
+
 CELL_TIMEOUT="${CELL_TIMEOUT:-60}"
 ONLY=""
 MAP_ONLY=0
 LIST_ONLY=0
 KEEP=0
+STABLE_HEADER=0
 
 while [[ $# -gt 0 ]]; do
   case "$1" in
@@ -41,7 +51,9 @@ while [[ $# -gt 0 ]]; do
     --map)  MAP_ONLY=1; shift ;;
     --list) LIST_ONLY=1; shift ;;
     --keep) KEEP=1; shift ;;
-    -h|--help) sed -n '2,30p' "${BASH_SOURCE[0]}"; exit 0 ;;
+    --print-legacy-tag) printf '%s\n' "$LEGACY_TAG"; exit 0 ;;
+    --stable-header) STABLE_HEADER=1; shift ;;
+    -h|--help) sed -n '2,33p' "${BASH_SOURCE[0]}"; exit 0 ;;
     *) echo "ERROR: unknown argument: $1" >&2; exit 2 ;;
   esac
 done
@@ -55,6 +67,15 @@ done
 command -v _hash_file  >/dev/null 2>&1 || { echo "ERROR: _hash_file missing"  >&2; exit 2; }
 command -v _hash_stdin >/dev/null 2>&1 || { echo "ERROR: _hash_stdin missing" >&2; exit 2; }
 
+# PLAN-168 W2: the shared pointer generator + degraded recognizer. The
+# `degraded` fixture must be rendered by the ONE template — a hand-built
+# approximation would test the fixture, not the cure.
+# shellcheck source=/dev/null
+. "$REPO_ROOT/scripts/_framework_manifest_set.sh" 2>/dev/null || {
+  echo "ERROR: cannot source scripts/_framework_manifest_set.sh" >&2; exit 2; }
+command -v _render_protocol_pointer_degraded >/dev/null 2>&1 || {
+  echo "ERROR: _render_protocol_pointer_degraded missing (W2 not in tree)" >&2; exit 2; }
+
 # --- scratch ----------------------------------------------------------------
 # NEVER $HOME, NEVER inside the repo (PLAN-167 W0.3 hard requirement).
 WORK="$( mktemp -d "${TMPDIR:-/tmp}/plan167-own.XXXXXX" )" || exit 2
@@ -348,19 +369,29 @@ _mutate_surface() {  # $1 surface, $2 live_type, $3 live_content, $4 src root, $
         rm -rf "$p"; mkdir -p "$( dirname "$p" )"; cp -R "$src_root/$rel" "$p" 2>/dev/null || true
       fi
       ;;
+    degraded)
+      # PLAN-168 W2 (AC-6b): the framework's OWN damage — the
+      # {{PROTOCOL_SOURCE}}-literal body every pre-fix upgrade wrote. Rendered
+      # by the shared generator (never a hand-built approximation); the
+      # recognizer extracts the invocation values from the file itself, so
+      # the pair used here only has to be internally consistent.
+      if [[ "$surface" == "protocol" && ! -L "$p" && ! -d "$p" ]]; then
+        _render_protocol_pointer_degraded "$T" core generic > "$p"
+      fi
+      ;;
     legacy_pristine)
-      # A REAL v1.2.0 SPEC/v1 tree from the tag the pristine fingerprints were
-      # derived from — never a hand-built approximation, which would test the
-      # fixture rather than the migration.
-      if ! git -C "$REPO_ROOT" rev-parse -q --verify 'refs/tags/v1.2.0^{}' >/dev/null 2>&1; then
-        echo "FIXTURE-ERR: tag v1.2.0 is not available in this checkout." >&2
+      # A REAL $LEGACY_TAG SPEC/v1 tree from the tag the pristine fingerprints
+      # were derived from — never a hand-built approximation, which would test
+      # the fixture rather than the migration.
+      if ! git -C "$REPO_ROOT" rev-parse -q --verify "refs/tags/$LEGACY_TAG^{}" >/dev/null 2>&1; then
+        echo "FIXTURE-ERR: tag $LEGACY_TAG is not available in this checkout." >&2
         echo "             legacy_pristine rows need the REAL shipped tree, never an" >&2
         echo "             approximation. A CI checkout using fetch-depth:1 has NO tags" >&2
-        echo "             — that job needs fetch-depth:0 or fetch-tags:true." >&2
+        echo "             — fetch it first: this script --print-legacy-tag names it." >&2
         return 1
       fi
       rm -rf "$p"; mkdir -p "$p"
-      git -C "$REPO_ROOT" archive v1.2.0 SPEC/v1 2>/dev/null \
+      git -C "$REPO_ROOT" archive "$LEGACY_TAG" SPEC/v1 2>/dev/null \
         | ( cd "$T" && tar -xf - ) || return 1
       ;;
     legacy_pristine_partial)
@@ -369,12 +400,12 @@ _mutate_surface() {  # $1 surface, $2 live_type, $3 live_content, $4 src root, $
       # matches a shipped release, so content alone reads "pristine" — and the
       # tree must STILL be refused, because a partial inventory can never
       # certify a wholesale replace (ADR-155-AMEND-1 §4).
-      if ! git -C "$REPO_ROOT" rev-parse -q --verify 'refs/tags/v1.2.0^{}' >/dev/null 2>&1; then
-        echo "FIXTURE-ERR: tag v1.2.0 unavailable (see legacy_pristine above)" >&2
+      if ! git -C "$REPO_ROOT" rev-parse -q --verify "refs/tags/$LEGACY_TAG^{}" >/dev/null 2>&1; then
+        echo "FIXTURE-ERR: tag $LEGACY_TAG unavailable (see legacy_pristine above)" >&2
         return 1
       fi
       rm -rf "$p"; mkdir -p "$p"
-      git -C "$REPO_ROOT" archive v1.2.0 SPEC/v1 2>/dev/null \
+      git -C "$REPO_ROOT" archive "$LEGACY_TAG" SPEC/v1 2>/dev/null \
         | ( cd "$T" && tar -xf - ) || return 1
       ln -s /dev/null "$p/adopter-added.link" 2>/dev/null || true
       ;;
@@ -464,6 +495,22 @@ _derive_hash_source() {  # $1 surface $2 after_rec $3 prior_rec $4 src_root
   # reading as HASH_PRIOR_RECORD, and the canonical name is then reached only
   # when the two genuinely differ — i.e. when the pointer was customised, which
   # is the one cell where the distinction carries meaning.
+  #
+  # PLAN-168 W2 (codex rail r2 P1): post-INV-4, install and upgrade produce
+  # the SAME bytes, so on continuity rows c_prior == c_pointer even for the
+  # preserved-EDITED cell — the two names collapse into one claim. When they
+  # alias and the record matches that one digest, report the name the TABLE
+  # expects (5th arg): letting probe order pick would manufacture a
+  # distinction the observation cannot make, and the cell would read RED over
+  # a naming artifact. This resolves ONLY the aliased case — when the digests
+  # genuinely differ, the probes below decide exactly as before.
+  local exp_hint="${5:-}"
+  if [[ "$surface" == "protocol" && -n "$c_prior" && -n "$c_pointer" \
+        && "$c_prior" == "$c_pointer" && "$got" == "$c_prior" ]]; then
+    case "$exp_hint" in
+      HASH_PRIOR_RECORD|HASH_CANONICAL_POINTER) printf '%s' "$exp_hint"; return 0 ;;
+    esac
+  fi
   [[ -n "$c_prior"   && "$got" == "$c_prior"   ]] && { printf 'HASH_PRIOR_RECORD'; return 0; }
   if [[ "$surface" == "protocol" && -n "$c_pointer" && "$got" == "$c_pointer" ]]; then
     printf 'HASH_CANONICAL_POINTER'; return 0
@@ -611,7 +658,7 @@ _run_row() {
     got_verdict="TIMEOUT"; got_hash="TIMEOUT"
   else
     got_verdict="$( _derive_verdict "$b_digest" "$a_digest" "$b_rec" "$a_rec" "$out" "$surface" "$rel" "$operation" )"
-    got_hash="$( _derive_hash_source "$surface" "$a_rec" "$b_rec" "$src" )"
+    got_hash="$( _derive_hash_source "$surface" "$a_rec" "$b_rec" "$src" "$exp_hash" )"
   fi
 
   # --- compare -------------------------------------------------------------
@@ -648,10 +695,21 @@ if [[ "$LIST_ONLY" -eq 1 ]]; then
 fi
 
 echo "== PLAN-167 ownership decision table =="
-echo "   table:  $TSV"
-echo "   source: $REPO_ROOT"
-echo "   scratch:$WORK"
-echo "   timeout:${CELL_TIMEOUT}s/cell   timeout-bin:${_TIMEOUT_BIN:-<fallback>}"
+if [[ "$STABLE_HEADER" -eq 1 ]]; then
+  # Machine-independent header, for RECORDING a baseline that gets committed.
+  # The absolute-path variant below leaked runner paths into the repo once
+  # (ownership-baseline-map.txt, PLAN-168 debate r1 devops must-fix 4) — a
+  # committed baseline must diff clean across machines.
+  echo "   table:  scripts/tests/ownership_table.tsv"
+  echo "   source: <repo>"
+  echo "   scratch:<scratch>"
+  echo "   timeout:${CELL_TIMEOUT}s/cell   timeout-bin:<bin>"
+else
+  echo "   table:  $TSV"
+  echo "   source: $REPO_ROOT"
+  echo "   scratch:$WORK"
+  echo "   timeout:${CELL_TIMEOUT}s/cell   timeout-bin:${_TIMEOUT_BIN:-<fallback>}"
+fi
 echo ""
 
 # Prime the canonical pointer digest for $T from a real install. Structurally
diff --git a/scripts/upgrade.sh b/scripts/upgrade.sh
index d0e9b94..cde1ff2 100755
--- a/scripts/upgrade.sh
+++ b/scripts/upgrade.sh
@@ -1537,37 +1537,75 @@ backup_and_replace() {
 # regenerate it with the same heuristic install.sh uses.
 _refresh_protocol_pointer() {
   local pointer="$TARGET/PROTOCOL.md"
-  local body
-  case "$SOURCE_DIR" in
-    "$TARGET"/*)
-      local rel="${SOURCE_DIR#$TARGET/}"
-      body="The full CEO orchestration protocol lives at:
-./${rel}/PROTOCOL.md
-
-To pull updates:
-  ( cd ./${rel} && git pull )
-  ./${rel}/scripts/upgrade.sh . --profile $PROFILE --stack $STACK"
-      ;;
-    *)
-      body="The full CEO orchestration protocol lives at:
-{{PROTOCOL_SOURCE}}/PROTOCOL.md
 
-Edit {{PROTOCOL_SOURCE}} to point at your ceo-orchestration checkout
-(e.g. ../ceo-orchestration or \$HOME/src/ceo-orchestration).
+  # PLAN-168 W2 (AC-6, Owner decision D1-b): the body comes from the ONE
+  # shared generator in _framework_manifest_set.sh — never a private heredoc.
+  # INV-4 existed because this function and install.sh each carried their own
+  # copy of this text: install substituted {{PROTOCOL_SOURCE}}, this one did
+  # not — two bodies for the same file, and the recorded digest never matched
+  # the disk (OWN-0074). A missing generator preserves the surface (upgrade's
+  # fail-toward-preservation posture, same as an illegal cell below).
+  if ! command -v _render_protocol_pointer >/dev/null 2>&1; then
+    echo "    WARNING: _render_protocol_pointer unavailable — PROTOCOL.md pointer PRESERVED" >&2
+    return 0
+  fi
 
-To pull updates:
-  ( cd {{PROTOCOL_SOURCE}} && git pull )
-  {{PROTOCOL_SOURCE}}/scripts/upgrade.sh $TARGET --profile $PROFILE --stack $STACK"
-      ;;
-  esac
+  # Resolve the PROTOCOL_SOURCE the pointer should name (AC-6c, Owner
+  # decision D3). Precedence:
+  #   1. request.placeholders.PROTOCOL_SOURCE from the install-state — the
+  #      install has ALWAYS persisted it there (union across runs; the
+  #      PLAN-168 debate's claim that it was never persisted checked the
+  #      wrong key — codex rail r1 P1).
+  #   2. A HEALTHY on-disk pointer: extract the value it already names and
+  #      keep it — never silently rename a sound pointer to today's checkout.
+  #   3. $SOURCE_DIR (this upgrade's checkout) — last resort, used for
+  #      genuinely old installs with no state and no sound pointer (incl.
+  #      the degraded-cure path, where the pointer names nothing usable).
+  local _ptr_psource=""
+  if [ -f "$_INSTALL_STATE_FILE" ] && command -v python3 >/dev/null 2>&1; then
+    _ptr_psource="$( python3 - "$_INSTALL_STATE_FILE" <<'PYEOF' 2>/dev/null || true
+import json, sys
+try:
+    with open(sys.argv[1], "r", encoding="utf-8") as f:
+        doc = json.load(f)
+    v = (doc.get("request") or {}).get("placeholders", {}).get("PROTOCOL_SOURCE", "")
+    if isinstance(v, str) and v and "{{" not in v:
+        sys.stdout.write(v)
+except Exception:
+    pass
+PYEOF
+)"
+  fi
+  if [ -z "$_ptr_psource" ] && [ -f "$pointer" ]; then
+    # D3 route 2: trust a SOUND pointer. Extract the source it names and
+    # accept it only if re-rendering with that value reproduces the file
+    # byte-for-byte (the same reconstruction discipline as the degraded
+    # recognizer — anything else is adopter content, not a source of truth).
+    local _ptr_cand
+    _ptr_cand="$( sed -n 's|^\(.*\)/PROTOCOL\.md$|\1|p' "$pointer" 2>/dev/null | sed -n '1p' )"
+    if [ -n "$_ptr_cand" ] && [ "${_ptr_cand#\{\{}" = "$_ptr_cand" ]; then
+      if _render_protocol_pointer "$SOURCE_DIR" "$TARGET" "$PROFILE" "$STACK" "$_ptr_cand" \
+           | cmp -s - "$pointer" 2>/dev/null; then
+        _ptr_psource="$_ptr_cand"
+      fi
+    fi
+  fi
+  if [ -z "$_ptr_psource" ]; then
+    _ptr_psource="$SOURCE_DIR"
+  fi
+
+  local _ptr_full
+  _ptr_full="$( _render_protocol_pointer "$SOURCE_DIR" "$TARGET" "$PROFILE" "$STACK" "$_ptr_psource" )"
 
   # The CANONICAL digest: the hash of exactly what the framework WOULD write.
   # Computed on every path, because the baseline rewrite must record it even
   # when the pointer is preserved — recording the customised bytes instead
   # would make the NEXT upgrade read H_dst == H_base and clobber them (C.5).
+  # Post-PLAN-168 this is the hash of the SUBSTITUTED body — the same bytes
+  # install writes — so the recorded digest finally matches the disk (INV-4).
   _REFRESH_PROTOCOL_CANON_HASH=""
   if command -v _hash_stdin >/dev/null 2>&1; then
-    _REFRESH_PROTOCOL_CANON_HASH="$( printf '# Protocol reference\n\n%s\n' "$body" | _hash_stdin 2>/dev/null || true )"
+    _REFRESH_PROTOCOL_CANON_HASH="$( printf '%s\n' "$_ptr_full" | _hash_stdin 2>/dev/null || true )"
   fi
 
   # ---- OBSERVE -------------------------------------------------------------
@@ -1576,6 +1614,14 @@ To pull updates:
   _pr="$( _ov_obs_prior_record "PROTOCOL.md" )"
   if [ "$_lt" != "regular" ]; then
     _lc="-"
+  elif _protocol_pointer_is_degraded "$pointer"; then
+    # PLAN-168 W2 (AC-6b, Owner decision D2): byte-exact reconstruction of
+    # the {{PROTOCOL_SOURCE}}-literal template this script used to write.
+    # Framework garbage, not adopter content — the verdict routes it to the
+    # REFRESH cure below. Checked BEFORE pristine/edited: a degraded body
+    # can never equal the substituted canonical, and classifying it `edited`
+    # is exactly the immortal-defect route this wave closes.
+    _lc="degraded"
   elif [ -n "$_REFRESH_PROTOCOL_CANON_HASH" ] \
        && [ "$( _hash_file "$pointer" 2>/dev/null || true )" = "$_REFRESH_PROTOCOL_CANON_HASH" ]; then
     _lc="pristine"
@@ -1640,13 +1686,13 @@ To pull updates:
         cp "$pointer" "$BAK_DIR/PROTOCOL.md" 2>/dev/null || true
         echo "    BACKED UP: PROTOCOL.md (root) -> $BAK_DIR/PROTOCOL.md"
       fi
-      cat > "$pointer" <<EOF
-# Protocol reference
-
-$body
-EOF
+      printf '%s\n' "$_ptr_full" > "$pointer"
       _PROTOCOL_DELIVERED=1
-      echo "    REFRESHED: PROTOCOL.md pointer"
+      if [ "$_lc" = "degraded" ]; then
+        echo "    CURED: PROTOCOL.md pointer was framework-degraded ({{PROTOCOL_SOURCE}} left literal by an old upgrade) — refreshed; original in $BAK_DIR/PROTOCOL.md"
+      else
+        echo "    REFRESHED: PROTOCOL.md pointer"
+      fi
       return 0
       ;;
   esac
@@ -1936,8 +1982,12 @@ _refresh_spec_contract() {
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

exec
/bin/zsh -lc 'git diff -- scripts/install.sh' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
diff --git a/scripts/install.sh b/scripts/install.sh
index 3ffe451..c0a0425 100755
--- a/scripts/install.sh
+++ b/scripts/install.sh
@@ -1884,50 +1884,34 @@ install_protocol_pointer() {
     return 0
   fi
 
-  # Compute a relative path from $TARGET to $SOURCE_DIR when possible.
-  # If the framework repo lives outside the target repo (common case),
-  # we fall back to {{PROTOCOL_SOURCE}} which the user substitutes
-  # manually. Absolute paths are NOT hardcoded — they break portability
-  # across dev machines and CI runners.
+  # PLAN-168 W2 (AC-6, Owner decision D1-b): the body comes from the ONE
+  # shared generator in _framework_manifest_set.sh — never a private heredoc.
+  # INV-4 existed because this function and upgrade.sh each carried their own
+  # copy of this text; a silent local fallback would resurrect the class, so
+  # a missing generator is a broken checkout and fails LOUD.
   #
-  # Relative-path heuristic: if $SOURCE_DIR starts with $TARGET, the
-  # framework was copied INTO the target — use a relative pointer. In
-  # ALL other cases (e.g. adopter clones framework elsewhere), we emit
-  # the user-editable {{PROTOCOL_SOURCE}} marker and document next steps.
-  local pointer_body
-  case "$SOURCE_DIR" in
-    "$TARGET"/*)
-      local rel="${SOURCE_DIR#$TARGET/}"
-      pointer_body="The full CEO orchestration protocol lives at:
-./${rel}/PROTOCOL.md
-
-To pull updates:
-  ( cd ./${rel} && git pull )
-  ./${rel}/scripts/upgrade.sh . --profile $PROFILE --stack $STACK"
-      ;;
-    *)
-      pointer_body="The full CEO orchestration protocol lives at:
-{{PROTOCOL_SOURCE}}/PROTOCOL.md
-
-Edit {{PROTOCOL_SOURCE}} to point at your ceo-orchestration checkout
-(e.g. ../ceo-orchestration or \$HOME/src/ceo-orchestration).
-
-To pull updates:
-  ( cd {{PROTOCOL_SOURCE}} && git pull )
-  {{PROTOCOL_SOURCE}}/scripts/upgrade.sh $TARGET --profile $PROFILE --stack $STACK"
-      ;;
-  esac
+  # Relative-path heuristic (unchanged): if $SOURCE_DIR starts with $TARGET,
+  # the framework was copied INTO the target — relative pointer. In ALL other
+  # cases the body is written with the user-editable {{PROTOCOL_SOURCE}}
+  # marker and the placeholder substitution pass below resolves it.
+  command -v _render_protocol_pointer >/dev/null 2>&1 || {
+    echo "    ERROR: _render_protocol_pointer unavailable (scripts/_framework_manifest_set.sh not sourced) — cannot write PROTOCOL.md pointer" >&2
+    return 1
+  }
 
   if [[ "$DRY_RUN" -eq 1 ]]; then
     echo "    (dry-run) would CREATE: PROTOCOL.md (pointer)"
     return 0
   fi
 
-  cat > "$TARGET/PROTOCOL.md" <<EOF
-# Protocol reference
-
-$pointer_body
-EOF
+  case "$SOURCE_DIR" in
+    "$TARGET"/*)
+      _render_protocol_pointer "$SOURCE_DIR" "$TARGET" "$PROFILE" "$STACK" "" > "$TARGET/PROTOCOL.md"
+      ;;
+    *)
+      _render_protocol_pointer_degraded "$TARGET" "$PROFILE" "$STACK" > "$TARGET/PROTOCOL.md"
+      ;;
+  esac
   echo "    CREATED: PROTOCOL.md (pointer)"
   _state_record_op "install_protocol_pointer" "PROTOCOL.md"
   # PLAN-166 F3 (ADR-155-AMEND-1): registered delivery — this line is only

exec
/bin/zsh -lc 'git diff -- scripts/upgrade.sh' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
diff --git a/scripts/upgrade.sh b/scripts/upgrade.sh
index d0e9b94..cde1ff2 100755
--- a/scripts/upgrade.sh
+++ b/scripts/upgrade.sh
@@ -1537,37 +1537,75 @@ backup_and_replace() {
 # regenerate it with the same heuristic install.sh uses.
 _refresh_protocol_pointer() {
   local pointer="$TARGET/PROTOCOL.md"
-  local body
-  case "$SOURCE_DIR" in
-    "$TARGET"/*)
-      local rel="${SOURCE_DIR#$TARGET/}"
-      body="The full CEO orchestration protocol lives at:
-./${rel}/PROTOCOL.md
-
-To pull updates:
-  ( cd ./${rel} && git pull )
-  ./${rel}/scripts/upgrade.sh . --profile $PROFILE --stack $STACK"
-      ;;
-    *)
-      body="The full CEO orchestration protocol lives at:
-{{PROTOCOL_SOURCE}}/PROTOCOL.md
 
-Edit {{PROTOCOL_SOURCE}} to point at your ceo-orchestration checkout
-(e.g. ../ceo-orchestration or \$HOME/src/ceo-orchestration).
+  # PLAN-168 W2 (AC-6, Owner decision D1-b): the body comes from the ONE
+  # shared generator in _framework_manifest_set.sh — never a private heredoc.
+  # INV-4 existed because this function and install.sh each carried their own
+  # copy of this text: install substituted {{PROTOCOL_SOURCE}}, this one did
+  # not — two bodies for the same file, and the recorded digest never matched
+  # the disk (OWN-0074). A missing generator preserves the surface (upgrade's
+  # fail-toward-preservation posture, same as an illegal cell below).
+  if ! command -v _render_protocol_pointer >/dev/null 2>&1; then
+    echo "    WARNING: _render_protocol_pointer unavailable — PROTOCOL.md pointer PRESERVED" >&2
+    return 0
+  fi
 
-To pull updates:
-  ( cd {{PROTOCOL_SOURCE}} && git pull )
-  {{PROTOCOL_SOURCE}}/scripts/upgrade.sh $TARGET --profile $PROFILE --stack $STACK"
-      ;;
-  esac
+  # Resolve the PROTOCOL_SOURCE the pointer should name (AC-6c, Owner
+  # decision D3). Precedence:
+  #   1. request.placeholders.PROTOCOL_SOURCE from the install-state — the
+  #      install has ALWAYS persisted it there (union across runs; the
+  #      PLAN-168 debate's claim that it was never persisted checked the
+  #      wrong key — codex rail r1 P1).
+  #   2. A HEALTHY on-disk pointer: extract the value it already names and
+  #      keep it — never silently rename a sound pointer to today's checkout.
+  #   3. $SOURCE_DIR (this upgrade's checkout) — last resort, used for
+  #      genuinely old installs with no state and no sound pointer (incl.
+  #      the degraded-cure path, where the pointer names nothing usable).
+  local _ptr_psource=""
+  if [ -f "$_INSTALL_STATE_FILE" ] && command -v python3 >/dev/null 2>&1; then
+    _ptr_psource="$( python3 - "$_INSTALL_STATE_FILE" <<'PYEOF' 2>/dev/null || true
+import json, sys
+try:
+    with open(sys.argv[1], "r", encoding="utf-8") as f:
+        doc = json.load(f)
+    v = (doc.get("request") or {}).get("placeholders", {}).get("PROTOCOL_SOURCE", "")
+    if isinstance(v, str) and v and "{{" not in v:
+        sys.stdout.write(v)
+except Exception:
+    pass
+PYEOF
+)"
+  fi
+  if [ -z "$_ptr_psource" ] && [ -f "$pointer" ]; then
+    # D3 route 2: trust a SOUND pointer. Extract the source it names and
+    # accept it only if re-rendering with that value reproduces the file
+    # byte-for-byte (the same reconstruction discipline as the degraded
+    # recognizer — anything else is adopter content, not a source of truth).
+    local _ptr_cand
+    _ptr_cand="$( sed -n 's|^\(.*\)/PROTOCOL\.md$|\1|p' "$pointer" 2>/dev/null | sed -n '1p' )"
+    if [ -n "$_ptr_cand" ] && [ "${_ptr_cand#\{\{}" = "$_ptr_cand" ]; then
+      if _render_protocol_pointer "$SOURCE_DIR" "$TARGET" "$PROFILE" "$STACK" "$_ptr_cand" \
+           | cmp -s - "$pointer" 2>/dev/null; then
+        _ptr_psource="$_ptr_cand"
+      fi
+    fi
+  fi
+  if [ -z "$_ptr_psource" ]; then
+    _ptr_psource="$SOURCE_DIR"
+  fi
+
+  local _ptr_full
+  _ptr_full="$( _render_protocol_pointer "$SOURCE_DIR" "$TARGET" "$PROFILE" "$STACK" "$_ptr_psource" )"
 
   # The CANONICAL digest: the hash of exactly what the framework WOULD write.
   # Computed on every path, because the baseline rewrite must record it even
   # when the pointer is preserved — recording the customised bytes instead
   # would make the NEXT upgrade read H_dst == H_base and clobber them (C.5).
+  # Post-PLAN-168 this is the hash of the SUBSTITUTED body — the same bytes
+  # install writes — so the recorded digest finally matches the disk (INV-4).
   _REFRESH_PROTOCOL_CANON_HASH=""
   if command -v _hash_stdin >/dev/null 2>&1; then
-    _REFRESH_PROTOCOL_CANON_HASH="$( printf '# Protocol reference\n\n%s\n' "$body" | _hash_stdin 2>/dev/null || true )"
+    _REFRESH_PROTOCOL_CANON_HASH="$( printf '%s\n' "$_ptr_full" | _hash_stdin 2>/dev/null || true )"
   fi
 
   # ---- OBSERVE -------------------------------------------------------------
@@ -1576,6 +1614,14 @@ To pull updates:
   _pr="$( _ov_obs_prior_record "PROTOCOL.md" )"
   if [ "$_lt" != "regular" ]; then
     _lc="-"
+  elif _protocol_pointer_is_degraded "$pointer"; then
+    # PLAN-168 W2 (AC-6b, Owner decision D2): byte-exact reconstruction of
+    # the {{PROTOCOL_SOURCE}}-literal template this script used to write.
+    # Framework garbage, not adopter content — the verdict routes it to the
+    # REFRESH cure below. Checked BEFORE pristine/edited: a degraded body
+    # can never equal the substituted canonical, and classifying it `edited`
+    # is exactly the immortal-defect route this wave closes.
+    _lc="degraded"
   elif [ -n "$_REFRESH_PROTOCOL_CANON_HASH" ] \
        && [ "$( _hash_file "$pointer" 2>/dev/null || true )" = "$_REFRESH_PROTOCOL_CANON_HASH" ]; then
     _lc="pristine"
@@ -1640,13 +1686,13 @@ To pull updates:
         cp "$pointer" "$BAK_DIR/PROTOCOL.md" 2>/dev/null || true
         echo "    BACKED UP: PROTOCOL.md (root) -> $BAK_DIR/PROTOCOL.md"
       fi
-      cat > "$pointer" <<EOF
-# Protocol reference
-
-$body
-EOF
+      printf '%s\n' "$_ptr_full" > "$pointer"
       _PROTOCOL_DELIVERED=1
-      echo "    REFRESHED: PROTOCOL.md pointer"
+      if [ "$_lc" = "degraded" ]; then
+        echo "    CURED: PROTOCOL.md pointer was framework-degraded ({{PROTOCOL_SOURCE}} left literal by an old upgrade) — refreshed; original in $BAK_DIR/PROTOCOL.md"
+      else
+        echo "    REFRESHED: PROTOCOL.md pointer"
+      fi
       return 0
       ;;
   esac
@@ -1936,8 +1982,12 @@ _refresh_spec_contract() {
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

exec
/bin/zsh -lc 'git diff -- scripts/tests/ownership-baseline-map.txt scripts/tests/ownership_table.tsv' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
diff --git a/scripts/tests/ownership-baseline-map.txt b/scripts/tests/ownership-baseline-map.txt
index df2dbd4..05749b0 100644
--- a/scripts/tests/ownership-baseline-map.txt
+++ b/scripts/tests/ownership-baseline-map.txt
@@ -1,8 +1,8 @@
 == PLAN-167 ownership decision table ==
-   table:  /tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553/scripts/tests/ownership_table.tsv
-   source: /tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
-   scratch:/var/folders/9n/hm9srl0s1nz45_p12tj61pd80000gn/T//plan167-own.toQDrn
-   timeout:60s/cell   timeout-bin:<fallback>
+   table:  scripts/tests/ownership_table.tsv
+   source: <repo>
+   scratch:<scratch>
+   timeout:60s/cell   timeout-bin:<bin>
 
 OWN-0001   GREEN   exp=DELIVER         /HASH_SOURCE            got=DELIVER         /HASH_SOURCE            rc=0   adr-155
 OWN-0002   GREEN   exp=DELIVER         /HASH_CANONICAL_POINTER got=DELIVER         /HASH_CANONICAL_POINTER rc=0   adr-155
@@ -60,11 +60,14 @@ OWN-0070   GREEN   exp=PRESERVE_OWNED  /HASH_SOURCE            got=PRESERVE_OWNE
 OWN-0071   GREEN   exp=PRESERVE_OWNED  /HASH_PRIOR_RECORD      got=PRESERVE_OWNED  /HASH_PRIOR_RECORD      rc=0   r7-F2
 OWN-0072   GREEN   exp=PRESERVE_OWNED  /HASH_PRIOR_RECORD      got=PRESERVE_OWNED  /HASH_PRIOR_RECORD      rc=0   r9-F2
 OWN-0073   GREEN   exp=REFRESH         /HASH_SOURCE            got=REFRESH         /HASH_SOURCE            rc=0   adr-155-amend-1
-OWN-0074   RED     exp=PRESERVE_OWNED  /HASH_CANONICAL_POINTER got=PRESERVE_OWNED  /HASH_UNCLASSIFIED      rc=0   derived
+OWN-0074   GREEN   exp=PRESERVE_OWNED  /HASH_CANONICAL_POINTER got=PRESERVE_OWNED  /HASH_CANONICAL_POINTER rc=0   derived
 OWN-0080   GREEN   exp=PRESERVE_UNOWNED/HASH_NONE              got=PRESERVE_UNOWNED/HASH_NONE              rc=0   r9-F4
 OWN-0081   GREEN   exp=PRESERVE_UNOWNED/HASH_NONE              got=PRESERVE_UNOWNED/HASH_NONE              rc=0   r11-F3
 OWN-0082   GREEN   exp=PRESERVE_OWNED  /HASH_PRIOR_RECORD      got=PRESERVE_OWNED  /HASH_PRIOR_RECORD      rc=0   adr-155-amend-1
 OWN-0090   GREEN   exp=REFRESH         /HASH_SOURCE            got=REFRESH         /HASH_SOURCE            rc=0   r7-F1
 OWN-0091   GREEN   exp=PRESERVE_OWNED  /HASH_SOURCE            got=PRESERVE_OWNED  /HASH_SOURCE            rc=0   r7-F1
+OWN-0092   GREEN   exp=REFRESH         /HASH_CANONICAL_POINTER got=REFRESH         /HASH_CANONICAL_POINTER rc=0   plan-168
+OWN-0093   GREEN   exp=REFRESH         /HASH_CANONICAL_POINTER got=REFRESH         /HASH_CANONICAL_POINTER rc=0   plan-168
+OWN-0094   GREEN   exp=PRESERVE_OWNED  /HASH_PRIOR_RECORD      got=PRESERVE_OWNED  /HASH_PRIOR_RECORD      rc=0   plan-168
 
-GREEN=58  RED=4  AMBIG=0  HARNESS-ERR=0
+GREEN=62  RED=3  AMBIG=0  HARNESS-ERR=0
diff --git a/scripts/tests/ownership_table.tsv b/scripts/tests/ownership_table.tsv
index e51d2c3..369fb37 100644
--- a/scripts/tests/ownership_table.tsv
+++ b/scripts/tests/ownership_table.tsv
@@ -67,3 +67,6 @@ OWN-0082	spec	hash	dir	pristine	no	copy	maintainer	upgrade	none	none	PRESERVE_OW
 OWN-0090	marker	hash	regular	edited	yes	copy	maintainer	upgrade	none	none	REFRESH	HASH_SOURCE	r7-F1	reader rule: checker must verify live bytes against the record
 OWN-0091	marker	hash	regular	edited	yes	copy	maintainer	install_rerun	none	none	PRESERVE_OWNED	HASH_SOURCE	r7-F1	1.3.0->9.9.9 edit must not suppress a real update
 OWN-0074	protocol	hash	regular	edited	yes	copy	maintainer	upgrade	none	none	PRESERVE_OWNED	HASH_CANONICAL_POINTER	derived	ADOPTER-CUSTOMIZED pointer on the NORMAL upgrade path — the verified S238 case; the digest stays canonical so the next upgrade does not read H_dst==H_base and clobber it
+OWN-0092	protocol	hash	regular	degraded	yes	copy	maintainer	upgrade	none	none	REFRESH	HASH_CANONICAL_POINTER	plan-168	the CURE (AC-6b): framework-degraded body ({{PROTOCOL_SOURCE}} literal, byte-exact template reconstruction) is the framework own garbage - REFRESH with backup, never preserved
+OWN-0093	protocol	none	regular	degraded	yes	copy	maintainer	upgrade	none	none	REFRESH	HASH_CANONICAL_POINTER	plan-168	recordless degraded takeover - content-proven framework origin, same doctrine as legacy_pristine (r20)
+OWN-0094	protocol	hash	regular	degraded	yes	copy	user	upgrade	none	none	PRESERVE_OWNED	HASH_PRIOR_RECORD	plan-168	user ceremony cannot cure - WS4: a user ceremony never writes root surfaces; the A2 carry preserves and the degraded body waits for a maintainer upgrade

exec
/bin/zsh -lc "grep -n \"_framework_manifest_set\\|install_protocol_pointer\\|substitut\\|PROTOCOL_SOURCE\" scripts/install.sh | head -100 && printf '\\n--- upgrade sourcing/call ---\\n' && grep -n \"_framework_manifest_set\\|_refresh_protocol_pointer\\|_protocol_pointer_is_degraded\" scripts/upgrade.sh" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
20:#   --github-owner <handle>        GitHub handle to substitute into CODEOWNERS.template
59:#   Placeholder substitution flags (override env + default values):
98:#                                  `{{X}}` placeholder remains unsubstituted in
149:#   7. (NEW — P1-CR-3) Runs a sed substitution pass over freshly-installed
249:if [ -f "$SCRIPT_DIR/_framework_manifest_set.sh" ]; then
250:  # shellcheck source=scripts/_framework_manifest_set.sh
251:  . "$SCRIPT_DIR/_framework_manifest_set.sh"
401:# {{PROTOCOL_SOURCE}} substitution. Resolved (CLI > env > $SOURCE_DIR
403:# literal `{{PROTOCOL_SOURCE}}` marker.
404:PH_PROTOCOL_SOURCE="${CEO_PROTOCOL_SOURCE:-}"
483:      # remains unsubstituted in installed files).
512:    # Placeholder substitution flags
517:    --protocol-source)     PH_PROTOCOL_SOURCE="${2:-}";    shift 2 ;;
656:# PLAN-085 Wave A.5 deterministic default — point PROTOCOL_SOURCE at
658:# --protocol-source / CEO_PROTOCOL_SOURCE if their framework lives
662:if [[ -z "$PH_PROTOCOL_SOURCE" ]]; then
663:  PH_PROTOCOL_SOURCE="$SOURCE_DIR"
788:# enumeration (_framework_manifest_set.sh) only records what the framework
1060:    # exclusion predicate (scripts/_framework_manifest_set.sh) so install and
1882:install_protocol_pointer() {
1888:  # shared generator in _framework_manifest_set.sh — never a private heredoc.
1895:  # cases the body is written with the user-editable {{PROTOCOL_SOURCE}}
1896:  # marker and the placeholder substitution pass below resolves it.
1898:    echo "    ERROR: _render_protocol_pointer unavailable (scripts/_framework_manifest_set.sh not sourced) — cannot write PROTOCOL.md pointer" >&2
1916:  _state_record_op "install_protocol_pointer" "PROTOCOL.md"
1925:if [[ "$CEREMONY" != "user" ]]; then install_protocol_pointer; fi  # WS4-guard-proto
1928:# P1-CR-3 / VP-F1: placeholder substitution pass
1931:# templates/ writes out) and apply `sed -i` substitutions for every
1967:  _add_sub "PROTOCOL_SOURCE"     "$PH_PROTOCOL_SOURCE"
2007:apply_placeholder_substitutions() {
2013:    echo "==> Placeholder substitution: no values supplied (use --owner / --project / env vars)"
2019:  echo "==> Applying placeholder substitutions"
2020:  _state_record_op "apply_placeholder_substitutions" ""
2068:  # {{PRODUCTION_URL}}, etc. as installer-time substitutions (not
2088:apply_placeholder_substitutions
2246:# set from _framework_manifest_set.sh, so the manifest writer (here) and the
2275:  # generator in _framework_manifest_set.sh does the walk + hashing + LINK
2507:    "ph.PROTOCOL_SOURCE" "$PH_PROTOCOL_SOURCE"
2602:    # idempotent and never un-substitutes, so a value recorded by an earlier
2771:# Grep for unsubstituted placeholders. Count + list files, then list
2794:  echo "    (none — all substituted)"

--- upgrade sourcing/call ---
105:if [ -f "$SCRIPT_DIR/_framework_manifest_set.sh" ]; then
106:  # shellcheck source=scripts/_framework_manifest_set.sh
107:  . "$SCRIPT_DIR/_framework_manifest_set.sh"
1538:_refresh_protocol_pointer() {
1542:  # shared generator in _framework_manifest_set.sh — never a private heredoc.
1617:  elif _protocol_pointer_is_degraded "$pointer"; then
3091:  # runs _refresh_protocol_pointer, so _REFRESH_PROTOCOL_CANON_HASH stays
3112:  # _refresh_protocol_pointer sets _PROTOCOL_DELIVERED itself, from the
3116:  _refresh_protocol_pointer

exec
/bin/zsh -lc "sed -n '240,265p' scripts/install.sh; sed -n '1920,2100p' scripts/install.sh; sed -n '2460,2640p' scripts/install.sh; sed -n '80,120p' scripts/upgrade.sh; sed -n '3060,3145p' scripts/upgrade.sh" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:

# PLAN-138 Wave C (ADR-155) — portable SHA-256 helpers + the single shared
# framework-owned enumeration. Sourced (not executed). Fail-open: if the
# helper is somehow absent (partial checkout), the baseline-manifest step is
# simply skipped later — the install itself never depends on it.
if [ -f "$SCRIPT_DIR/_hash_lib.sh" ]; then
  # shellcheck source=scripts/_hash_lib.sh
  . "$SCRIPT_DIR/_hash_lib.sh"
fi
if [ -f "$SCRIPT_DIR/_framework_manifest_set.sh" ]; then
  # shellcheck source=scripts/_framework_manifest_set.sh
  . "$SCRIPT_DIR/_framework_manifest_set.sh"
fi
# PLAN-155 Wave 5 — Codex harness emission (sourced, not executed). Fail-open:
# if absent (partial checkout), --harness codex degrades to a clear error at
# use; the default claude path never references it.
if [ -f "$SCRIPT_DIR/_codex_harness.sh" ]; then
  # shellcheck source=scripts/_codex_harness.sh
  . "$SCRIPT_DIR/_codex_harness.sh"
fi

# PLAN-156 Wave 4 — Grok harness emission (sourced, not executed). Same
# fail-open shape as the codex source above: absent => --harness grok
# degrades to a clear error at use; the default claude path never references it.
if [ -f "$SCRIPT_DIR/_grok_harness.sh" ]; then
  # shellcheck source=scripts/_grok_harness.sh
  # PROTOCOL.md is never inventoried as framework-owned; r13/r17).
  _DELIVERED_PROTOCOL=1
  _state_record_op "delivered_protocol_pointer" "PROTOCOL.md"
}

if [[ "$CEREMONY" != "user" ]]; then install_protocol_pointer; fi  # WS4-guard-proto

# ----------------------------------------------------------------------
# P1-CR-3 / VP-F1: placeholder substitution pass
# ----------------------------------------------------------------------
# Iterate over a deterministic list of placeholder files (the ones
# templates/ writes out) and apply `sed -i` substitutions for every
# PH_* variable that is non-empty. Anything left as `{{...}}` after the
# pass is reported with a stderr warning.
#
# We restrict the pass to files install.sh actually placed (the
# templates/* files) to avoid touching user-authored content. If
# CLAUDE.md / MEMORY.md already existed at target, we leave them alone
# (install.sh never overwrites them).

# Portable sed -i for GNU + BSD (macOS): write to .tmp and mv.
portable_sed_inplace() {
  # $1 = sed script, $2 = file
  local script="$1" file="$2"
  local tmp="${file}.ceo-sed-tmp"
  sed "$script" "$file" > "$tmp" && mv "$tmp" "$file"
}

# Build the sed script iteratively. Each non-empty placeholder adds an
# expression. We use `|` as the delimiter so slashes in values (paths)
# don't break. Values with `|` are escaped.
build_sed_script() {
  local script=""
  _add_sub() {
    local key="$1" val="$2"
    if [[ -n "$val" ]]; then
      # Escape | & \ in the replacement
      local esc
      esc="$(printf '%s' "$val" | sed 's/[|&\\]/\\&/g')"
      script="${script}s|{{${key}}}|${esc}|g;"
    fi
  }
  _add_sub "OWNER_NAME"          "$PH_OWNER_NAME"
  _add_sub "OWNER_HANDLE"        "$GITHUB_OWNER"
  _add_sub "PROJECT_NAME"        "$PH_PROJECT_NAME"
  _add_sub "PROJECT_PATH"        "$PH_PROJECT_PATH"
  _add_sub "STACK"               "$PH_STACK"
  _add_sub "PROTOCOL_SOURCE"     "$PH_PROTOCOL_SOURCE"
  _add_sub "DEPLOY_COMMAND"      "$PH_DEPLOY_COMMAND"
  _add_sub "DEPLOY_PLATFORM"     "$PH_DEPLOY_PLATFORM"
  _add_sub "DEPLOY_TARGET"       "$PH_DEPLOY_TARGET"
  _add_sub "RUNTIME_NOTES"       "$PH_RUNTIME_NOTES"
  _add_sub "DATABASE"            "$PH_DATABASE"
  _add_sub "N_BACKEND"           "$PH_N_BACKEND"
  _add_sub "N_FRONTEND"          "$PH_N_FRONTEND"
  _add_sub "FRONTEND_STACK"      "$PH_FRONTEND_STACK"
  _add_sub "FRONTEND_PATH"       "$PH_FRONTEND_PATH"
  _add_sub "FRONTEND_REPO_PATH"  "$PH_FRONTEND_REPO_PATH"
  _add_sub "UI_LIBRARY"          "$PH_UI_LIBRARY"
  _add_sub "STATE_MANAGEMENT"    "$PH_STATE_MANAGEMENT"
  _add_sub "REALTIME_TRANSPORT"  "$PH_REALTIME_TRANSPORT"
  _add_sub "CHARTING_LIBRARY"    "$PH_CHARTING_LIBRARY"
  _add_sub "AUTH_PROVIDER"       "$PH_AUTH_PROVIDER"
  _add_sub "I18N_FRAMEWORK"      "$PH_I18N_FRAMEWORK"
  _add_sub "TEST_FRAMEWORK"      "$PH_TEST_FRAMEWORK"
  _add_sub "TEST_TOOL"           "$PH_TEST_TOOL"
  _add_sub "TEST_COUNT"          "$PH_TEST_COUNT"
  _add_sub "LINT_TOOL"           "$PH_LINT_TOOL"
  _add_sub "CI_TOOL"             "$PH_CI_TOOL"
  _add_sub "APP_NAME"            "$PH_APP_NAME"
  _add_sub "SOURCE_FILE_COUNT"   "$PH_SOURCE_FILE_COUNT"
  _add_sub "LINE_COUNT"          "$PH_LINE_COUNT"
  _add_sub "LINES"               "$PH_LINES"
  _add_sub "FILE_COUNT"          "$PH_FILE_COUNT"
  _add_sub "PAGE_COUNT"          "$PH_PAGE_COUNT"
  _add_sub "COMPONENT_COUNT"     "$PH_COMPONENT_COUNT"
  _add_sub "HOOK_COUNT"          "$PH_HOOK_COUNT"
  _add_sub "BUNDLE_SIZE"         "$PH_BUNDLE_SIZE"
  _add_sub "CITY"                "$PH_CITY"
  _add_sub "COUNTRY"             "$PH_COUNTRY"
  _add_sub "DOMAIN"              "$PH_DOMAIN"
  _add_sub "FOUNDER_NAME"        "${PH_FOUNDER_NAME:-$PH_OWNER_NAME}"
  _add_sub "LEGAL_ID"            "$PH_LEGAL_ID"
  _add_sub "PRODUCTION_URL"      "$PH_PRODUCTION_URL"
  printf '%s' "$script"
}

apply_placeholder_substitutions() {
  local sed_script
  sed_script="$(build_sed_script)"

  if [[ -z "$sed_script" ]]; then
    echo ""
    echo "==> Placeholder substitution: no values supplied (use --owner / --project / env vars)"
    echo "    Template files ship as-is. Edit them manually or re-run install.sh with flags."
    return 0
  fi

  echo ""
  echo "==> Applying placeholder substitutions"
  _state_record_op "apply_placeholder_substitutions" ""

  # Files we are allowed to rewrite — strictly the template-sourced files
  # that install.sh just placed. We check existence first.
  #
  # We intentionally do NOT touch:
  #   - .claude/settings.json          (user-edited hook registry)
  #   - .claude/plans/PLAN-*.md        (user's own plans)
  #   - .claude/adr/ADR-*.md           (user's own ADRs)
  #   - .claude/scripts/*              (executable code; placeholders
  #     inside .py docstrings are instructional, not install-time)
  #   - .claude/hooks/*                (same reason)
  # WS4-explicit-files-partition: maintainer rewrites root + docs/ +
  # .claude/ template files; user ceremony rewrites ONLY .claude/ files so
  # a real adopter repo's own root/docs files are never touched.
  local explicit_files=(
    "$TARGET/.claude/team.md"
    "$TARGET/.claude/frontend-team.md"
    "$TARGET/.claude/agent-metrics.md"
  )
  if [[ "$CEREMONY" != "user" ]]; then
    explicit_files=(
      "$TARGET/CLAUDE.md"
      "$TARGET/MEMORY.md"
      "$TARGET/PROTOCOL.md"
      "$TARGET/docs/BRANCH-PROTECTION.md"
      "$TARGET/docs/rotation-log.md"
      "$TARGET/.claude/team.md"
      "$TARGET/.claude/frontend-team.md"
      "$TARGET/.claude/agent-metrics.md"
    )
  fi

  local f
  for f in "${explicit_files[@]}"; do
    [[ -f "$f" ]] || continue
    if [[ "$DRY_RUN" -eq 1 ]]; then
      echo "    (dry-run) would SUBSTITUTE placeholders in: ${f#$TARGET/}"
      continue
    fi
    portable_sed_inplace "$sed_script" "$f"
    echo "    SUBSTITUTED: ${f#$TARGET/}"
  done

  # Skills/**/SKILL*.md, skills/**/team-personas.md + pitfalls.yaml, and
  # progressive-disclosure references/*.md (PLAN-153 Wave C splits) —
  # these are canonical content that ships {{PROJECT_NAME}}, {{OWNER_NAME}},
  # {{DEPLOY_COMMAND}}, {{FRONTEND_REPO_PATH}}, {{APP_NAME}},
  # {{PRODUCTION_URL}}, etc. as installer-time substitutions (not
  # instructional placeholders). Recurse into the skills tree.
  local skills_root="$TARGET/.claude/skills"
  if [[ -d "$skills_root" ]]; then
    while IFS= read -r f; do
      [[ -n "$f" && -f "$f" ]] || continue
      if [[ "$DRY_RUN" -eq 1 ]]; then
        echo "    (dry-run) would SUBSTITUTE placeholders in: ${f#$TARGET/}"
        continue
      fi
      portable_sed_inplace "$sed_script" "$f"
      echo "    SUBSTITUTED: ${f#$TARGET/}"
    done < <(find "$skills_root" \
      \( -name 'SKILL.md' -o -name 'SKILL-*.md' \
         -o -name 'team-personas.md' -o -name 'pitfalls.yaml' \
         -o -path '*/references/*.md' -o -path '*/reference/*.md' \) \
      -type f 2>/dev/null)
  fi
}

apply_placeholder_substitutions

# ----------------------------------------------------------------------
# Done — mark success so trap doesn't roll back, then print summary
# ----------------------------------------------------------------------


# ----------------------------------------------------------------------
# audit-v2 C4-P0-03: post-install placeholder validator
# ----------------------------------------------------------------------
# Scan installed `.py` and `.md` files for unrendered {{X}} patterns.
# Default: warn + continue. --strict-placeholders (or
# CEO_INSTALL_STRICT_PH=1) → exit 4 if any found.
#   * Consumed by upgrade.sh (PLAN-153 B2): request.profile/request.stack
#     become upgrade DEFAULTS when its own flags are omitted. A missing or
#     invalid state file degrades upgrade.sh to the ADR-155 drift-classifier
#     path — never an error, never a no-op (debate C back-compat must-fix).
#   * TRUST: target-side, UNSIGNED, advisory — the same trust class as the
#     ADR-155 baseline manifest (whoever can write the target tree can
#     rewrite it). upgrade.sh charset-validates every replayed value and
#     falls back on anything suspect; values are data, never eval-ed.
#   * Fail-open: no python3 / write error => stderr NOTE, install still
#     succeeds. Dry-run never writes (the "no files modified" promise).
#   * NOT covered by the baseline-manifest enumeration (like the manifest
#     dotfile itself), so the upgrade classifier never touches it.
_write_install_state() {
  [[ "${DRY_RUN:-0}" -eq 0 ]] || return 0
  if ! command -v python3 >/dev/null 2>&1; then
    echo "    NOTE: install-state skipped (python3 not found) — upgrade.sh will use the ADR-155 fallback path" >&2
    return 0
  fi
  local state_file="$TARGET/.claude/.install-state.json"
  local fw_version=""
  if [[ -f "$SOURCE_DIR/VERSION" ]]; then
    fw_version="$(tr -d '[:space:]' < "$SOURCE_DIR/VERSION" 2>/dev/null || true)"
  fi

  echo ""
  echo "==> Writing install-state (.claude/.install-state.json — PLAN-153 Wave B)"

  # Flat key/value pairs, argv-passed (PLAN-106 G.2.b house pattern: never
  # source-string interpolation; python3 -I + PYTHONNOUSERSITE=1). Keys with
  # a "ph." prefix land in request.placeholders; empty ph values are omitted.
  local pairs=(
    "target" "$TARGET"
    "mode" "$MODE"
    "profile" "$PROFILE"
    "stack" "$STACK"
    "stack_explicit" "$STACK_EXPLICIT"
    "ceremony" "$CEREMONY"
    "github_owner" "$GITHUB_OWNER"
    "with_reference_personas" "$WITH_REFERENCE_PERSONAS"
    "strict_placeholders" "$STRICT_PLACEHOLDERS"
    "verify" "$VERIFY"
    "harness" "$HARNESS"
    "managed_hooks" "$CODEX_MANAGED_HOOKS"
    "ph.OWNER_NAME" "$PH_OWNER_NAME"
    "ph.PROJECT_NAME" "$PH_PROJECT_NAME"
    "ph.PROJECT_PATH" "$PH_PROJECT_PATH"
    "ph.STACK" "$PH_STACK"
    "ph.PROTOCOL_SOURCE" "$PH_PROTOCOL_SOURCE"
    "ph.DEPLOY_COMMAND" "$PH_DEPLOY_COMMAND"
    "ph.DEPLOY_PLATFORM" "$PH_DEPLOY_PLATFORM"
    "ph.DEPLOY_TARGET" "$PH_DEPLOY_TARGET"
    "ph.RUNTIME_NOTES" "$PH_RUNTIME_NOTES"
    "ph.DATABASE" "$PH_DATABASE"
    "ph.N_BACKEND" "$PH_N_BACKEND"
    "ph.N_FRONTEND" "$PH_N_FRONTEND"
    "ph.FRONTEND_STACK" "$PH_FRONTEND_STACK"
    "ph.FRONTEND_PATH" "$PH_FRONTEND_PATH"
    "ph.FRONTEND_REPO_PATH" "$PH_FRONTEND_REPO_PATH"
    "ph.UI_LIBRARY" "$PH_UI_LIBRARY"
    "ph.STATE_MANAGEMENT" "$PH_STATE_MANAGEMENT"
    "ph.REALTIME_TRANSPORT" "$PH_REALTIME_TRANSPORT"
    "ph.CHARTING_LIBRARY" "$PH_CHARTING_LIBRARY"
    "ph.AUTH_PROVIDER" "$PH_AUTH_PROVIDER"
    "ph.I18N_FRAMEWORK" "$PH_I18N_FRAMEWORK"
    "ph.TEST_FRAMEWORK" "$PH_TEST_FRAMEWORK"
    "ph.TEST_TOOL" "$PH_TEST_TOOL"
    "ph.TEST_COUNT" "$PH_TEST_COUNT"
    "ph.LINT_TOOL" "$PH_LINT_TOOL"
    "ph.CI_TOOL" "$PH_CI_TOOL"
    "ph.APP_NAME" "$PH_APP_NAME"
    "ph.SOURCE_FILE_COUNT" "$PH_SOURCE_FILE_COUNT"
    "ph.LINE_COUNT" "$PH_LINE_COUNT"
    "ph.LINES" "$PH_LINES"
    "ph.FILE_COUNT" "$PH_FILE_COUNT"
    "ph.PAGE_COUNT" "$PH_PAGE_COUNT"
    "ph.COMPONENT_COUNT" "$PH_COMPONENT_COUNT"
    "ph.HOOK_COUNT" "$PH_HOOK_COUNT"
    "ph.BUNDLE_SIZE" "$PH_BUNDLE_SIZE"
    "ph.CITY" "$PH_CITY"
    "ph.COUNTRY" "$PH_COUNTRY"
    "ph.DOMAIN" "$PH_DOMAIN"
    "ph.FOUNDER_NAME" "$PH_FOUNDER_NAME"
    "ph.LEGAL_ID" "$PH_LEGAL_ID"
    "ph.PRODUCTION_URL" "$PH_PRODUCTION_URL"
  )

  if ! PYTHONNOUSERSITE=1 python3 -I -c '
import json, os, sys, tempfile, time
args = sys.argv[1:]
state_path, ops_path, fw_version = args[0], args[1], args[2]
n = int(args[3]); kv = args[4:4 + n]; orig_argv = list(args[4 + n:])
vals = {}; ph = {}
i = 0
while i + 1 < len(kv):
    k, v = kv[i], kv[i + 1]
    if k.startswith("ph."):
        if v != "":
            ph[k[3:]] = v
    else:
        vals[k] = v
    i += 2
ops = []
if ops_path and os.path.isfile(ops_path):
    try:
        with open(ops_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                line = line.rstrip("\n")
                if not line:
                    continue
                parts = line.split("\t", 1)
                ops.append({"op": parts[0], "detail": parts[1] if len(parts) > 1 else ""})
    except OSError:
        pass
now = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
prev = None
try:
    with open(state_path, "r", encoding="utf-8") as f:
        prev = json.load(f)
    if not isinstance(prev, dict):
        prev = None
except (OSError, ValueError):
    prev = None
first, run_count, history = now, 1, []
if prev is not None:
    v = prev.get("first_recorded_at")
    if isinstance(v, str) and v:
        first = v
    rc = prev.get("run_count")
    if isinstance(rc, int) and rc > 0:
        run_count = rc + 1
    h = prev.get("history")
    if isinstance(h, list):
        history = [e for e in h if isinstance(e, dict)][-19:]
    pr = prev.get("request"); pt = prev.get("tool"); pw = prev.get("written_at")
    history.append({
        "at": pw if isinstance(pw, str) else "",
        "tool": (pt.get("name", "") if isinstance(pt, dict) else ""),
        "profile": (pr.get("profile", "") if isinstance(pr, dict) else ""),
        "stack": (pr.get("stack", "") if isinstance(pr, dict) else ""),
    })
    history = history[-20:]
    # Placeholder map is a UNION across runs: install.sh is EXISTS-SKIP
    # idempotent and never un-substitutes, so a value recorded by an earlier
    # run remains in effect on disk even when a later run omits the flag.
    # New non-empty values override recorded ones.
    if isinstance(pr, dict):
        oph = pr.get("placeholders")
        if isinstance(oph, dict):
            merged = {}
            for k in oph:
                if isinstance(k, str) and isinstance(oph[k], str):
                    merged[k] = oph[k]
            merged.update(ph)
            ph = merged
req = {
    "argv": orig_argv,
    "target": vals.get("target", ""),
    "mode": vals.get("mode", ""),
    "profile": vals.get("profile", ""),
    "stack": vals.get("stack", ""),
    "stack_explicit": vals.get("stack_explicit", "0") == "1",
    "ceremony": vals.get("ceremony", ""),
    "github_owner": vals.get("github_owner", ""),
    "with_reference_personas": vals.get("with_reference_personas", "0") == "1",
    "strict_placeholders": vals.get("strict_placeholders", "0") == "1",
    "verify": vals.get("verify", "0") == "1",
    # PLAN-155 Wave 5: recorded so upgrade.sh replays the harness (B2 mirror).
    "harness": vals.get("harness", "claude"),
    "managed_hooks": vals.get("managed_hooks", "0") == "1",
    "placeholders": ph,
}
state = {
    "schema": "ceo.install-state/v1",
    "schema_version": 1,
    "written_at": now,
    "first_recorded_at": first,
    "run_count": run_count,
    "tool": {"name": "install.sh", "framework_version": fw_version},
    "request": req,
    "operations": ops,
    "result": {"install_succeeded": True,

# Bash 3.2 portability guard (DevOps-P1-3 parity with install.sh)
if [ -z "${BASH_VERSINFO:-}" ]; then
  echo "ERROR: upgrade.sh requires bash (detected non-bash shell)" >&2
  exit 1
fi
if [ "${BASH_VERSINFO[0]}" -lt 3 ] || \
   { [ "${BASH_VERSINFO[0]}" -eq 3 ] && [ "${BASH_VERSINFO[1]}" -lt 2 ]; }; then
  echo "ERROR: upgrade.sh requires bash >= 3.2 (detected ${BASH_VERSION})" >&2
  exit 1
fi

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
SOURCE_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

# PLAN-138 Wave C (ADR-155) — portable SHA-256 helpers + the single shared
# framework-owned enumeration, sourced (not executed). Both back the baseline
# classifier below. Fail-open: if a helper is absent (partial checkout) the
# classifier degrades to today's diff -q warn-then-clobber behavior.
if [ -f "$SCRIPT_DIR/_hash_lib.sh" ]; then
  # shellcheck source=scripts/_hash_lib.sh
  . "$SCRIPT_DIR/_hash_lib.sh"
fi
if [ -f "$SCRIPT_DIR/_framework_manifest_set.sh" ]; then
  # shellcheck source=scripts/_framework_manifest_set.sh
  . "$SCRIPT_DIR/_framework_manifest_set.sh"
fi
# PLAN-155 Wave 5 — codex harness emission helper (sourced, not executed).
# Fail-open: absent => --harness codex round-trip degrades to a warning.
if [ -f "$SCRIPT_DIR/_codex_harness.sh" ]; then
  # shellcheck source=scripts/_codex_harness.sh
  . "$SCRIPT_DIR/_codex_harness.sh"
fi

# PLAN-156 Wave 4 — Grok harness (sourced). Fail-open: absent => --harness
# grok round-trip degrades to a warning (mirrors the codex source above).
if [ -f "$SCRIPT_DIR/_grok_harness.sh" ]; then
  # shellcheck source=scripts/_grok_harness.sh
  . "$SCRIPT_DIR/_grok_harness.sh"
}

upgrade_agents_canonical_only

# PLAN-135 W2 H8: register new lifecycle hooks (Setup/init self-verification)
# into the adopter's existing settings.json (install.sh would EXISTS-SKIP it).
_merge_lifecycle_hooks_into_settings

# PLAN-163 T5.4: baseline-aware settings migration — fleet/permission leaf
# keys + (T3.4-gated) new-event registrations. 3-state per key; idempotent;
# customized values are always PRESERVED with a named WARNING.
_migrate_settings_baseline

# DevOps-P1-4: PROTOCOL.md is framework-derived (pointer), not user data —
# refresh it so it stays aligned with the current source layout.
# PLAN-166 F3 (ADR-155-AMEND-1): CEREMONY-GATED — the refresh used to run
# unconditionally and `cat >`-created a root PROTOCOL.md that a
# `--ceremony user` install deliberately never has (install.sh
# WS4-guard-proto forbids root files); the F4 tree-comparison e2e exposes
# exactly this divergence (r7/r13). The gate reads the ceremony from
# .claude/.install-state.json via the replay-independent reader above.
_PROTOCOL_DELIVERED=0
echo ""
echo "==> Refreshing PROTOCOL.md pointer"
if [[ "$CEREMONY_EFFECTIVE" == "user" ]]; then
  echo "    SKIP: PROTOCOL.md pointer (recorded --ceremony user install — a user install never creates root files, WS4; r13)"
  # Ownership continuity on the analogous skip (codex W1 round 7, P2) — see
  # the SPEC/v1 ceremony skip: preserving the tree while erasing its record
  # strands a framework-delivered pointer as unowned.
  #
  # But the flag alone is NOT enough (codex W1 round 9, P1): this skip never
  # runs _refresh_protocol_pointer, so _REFRESH_PROTOCOL_CANON_HASH stays
  # empty, and _write_baseline_manifest then hashes the LIVE pointer —
  # re-recording an adopter-CUSTOMIZED PROTOCOL.md as the framework baseline,
  # which the next upgrade overwrites and uninstall can DELETE. Retaining
  # ownership must never retain the wrong bytes. Carry the PRIOR canonical
  # digest; a LINK record needs none (the link branch of the rewrite fires
  # before the PROTOCOL special case). When neither is available, DROP the
  # claim — the pointer stays adopter-owned and preserved, which is the
  # pre-continuity behaviour and loses nothing.
  if _baseline_has_protocol_record; then
    _REFRESH_PROTOCOL_CANON_HASH="$( _baseline_lookup "PROTOCOL.md" 2>/dev/null || true )"
    if [[ -n "$_REFRESH_PROTOCOL_CANON_HASH" ]] \
       || grep -Eq '^LINK  PROTOCOL\.md(  |$)' "$_BASELINE_MANIFEST_FILE" 2>/dev/null; then
      _PROTOCOL_DELIVERED=1
    else
      echo "    NOTE: PROTOCOL.md delivery record present but its canonical digest is" >&2
      echo "          unrecoverable (ambiguous record) — ownership NOT claimed; the" >&2
      echo "          pointer stays adopter-owned and preserved" >&2
    fi
  fi
else
  # _refresh_protocol_pointer sets _PROTOCOL_DELIVERED itself, from the
  # VERDICT. Forcing it to 1 here overrode a PRESERVE_UNOWNED decision and
  # recorded an adopter's own pre-existing PROTOCOL.md as framework-owned —
  # a caller computing the right answer and then ignoring it (codex W3 r1 P1).
  _refresh_protocol_pointer
fi

# PLAN-166 F3 (ADR-155-AMEND-1): SPEC/v1 forced refresh + framework version
# marker. Both run BEFORE the baseline-manifest rewrite so the delivery
# flags they set are what the rewritten baseline records.
echo ""
echo "==> Refreshing SPEC/v1 contract (PLAN-166 F3 — forced route)"
_refresh_spec_contract

echo ""
echo "==> Refreshing framework version marker (.claude/.framework-version)"
_refresh_framework_marker

# PLAN-161 U3 — mis-install scan/purge. Runs in ALL modes (flag-absent and
# --dry-run runs emit the would-purge PREVIEW; deletion requires the explicit
# --purge-misinstalled flag AND a non-dry run). Runs BEFORE the baseline-
# manifest rewrite below so a purged path is never re-recorded.
echo ""
echo "==> Scanning excluded trees for mis-installed framework-internal files (PLAN-161 U3)"
_purge_misinstalled_scan

# PLAN-138 Wave C (ADR-155) C.7 — (re)write the baseline manifest AFTER a
# successful upgrade, so a long-lived adopter who upgrades but never re-runs
# install.sh (the S238 acme population) acquires/refreshes a manifest. The
# NEXT upgrade then runs the manifest-present per-file classified path instead
# of the fallback. Uses the SAME shared generator install.sh calls. Skipped on
# --dry-run; fail-open (a generator problem emits a NOTE, never aborts).
if [[ "$DRY_RUN" -eq 0 ]] && command -v _write_baseline_manifest >/dev/null 2>&1; then
  echo ""

exec
/bin/zsh -lc 'for f in .github/workflows/ownership-nightly.yml scripts/tests/ownership-expected-reds.txt scripts/tests/ownership-nightly-gate.sh scripts/tests/test-ownership-nightly-gate.sh scripts/tests/test-protocol-pointer-render.sh scripts/tests/test-protocol-pointer-inv4.sh .claude/adr/ADR-190-ownership-decision-table-contract.md; do echo "===== $f ====="; if [ -f "$f" ]; then nl -ba "$f"; fi; done' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
===== .github/workflows/ownership-nightly.yml =====
     1	name: Ownership Nightly
     2	
     3	# PLAN-168 W1 (AC-4/AC-5, Owner decision D4): the ownership e2e runs the FULL
     4	# truth table — 62 real install/upgrade cells, ~25 min locally, 2-3x that on a
     5	# 2-core runner — so it cannot live inside smoke-install's 25-min job (that
     6	# budget was already raised 4x: 5→8→20→25). And `schedule:` events IGNORE
     7	# `paths:` filters, so the nightly split is a separate WORKFLOW, not a filter
     8	# entry (debate r1 devops must-fix 1). The fast per-PR half (the unit oracle)
     9	# stays in smoke-install.yml.
    10	#
    11	# The gate compares the observed non-GREEN set against
    12	# scripts/tests/ownership-expected-reds.txt and fails on ANY difference —
    13	# including shrinkage. 4 deliberate reds are part of the contract
    14	# (CLAUDE.md §4): an all-green run means the table changed — STOP and find
    15	# out why, never celebrate. NEVER run the harness with --map here: --map is a
    16	# reporting mode that exits 0 over failures (a dead gate by construction).
    17	
    18	on:
    19	  schedule:
    20	    # Off-peak UTC, off-minute deliberately (fleet etiquette — avoid :00/:30).
    21	    - cron: "43 6 * * *"
    22	  # Manual runs for harness/table PRs that want the full e2e before merge.
    23	  workflow_dispatch: {}
    24	
    25	concurrency:
    26	  group: ownership-nightly
    27	  cancel-in-progress: true
    28	
    29	jobs:
    30	  ownership-e2e:
    31	    # PLAN-012 Phase 2 CEO_SOTA_DISABLE parity (same switch as smoke-install).
    32	    if: vars.CEO_SOTA_DISABLE != '1'
    33	    runs-on: ubuntu-latest
    34	    # ~25 min local (Darwin arm64, 16 cores, 2026-08-07); ubuntu-latest is the
    35	    # usual 2-3x slower => 50-75 min expected. Same anti-flake sizing rule as
    36	    # the smoke-install budget notes: leave headroom, re-tighten on a real p95.
    37	    timeout-minutes: 90
    38	    permissions:
    39	      contents: read
    40	    steps:
    41	      - name: Checkout
    42	        # SHA-pinned (same pin as smoke-install.yml): actions/checkout@v6.0.2
    43	        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd
    44	        with:
    45	          fetch-depth: 1
    46	
    47	      # `fetch-depth: 1` produces a checkout with NO tags, and the
    48	      # legacy_pristine* fixtures build from a REAL shipped tree. The tag is
    49	      # READ FROM THE HARNESS (--print-legacy-tag) so this workflow never
    50	      # becomes a second copy of that truth (same --print-pin shape as the
    51	      # parity e2e in smoke-install.yml).
    52	      - name: Fetch the legacy_pristine tag
    53	        run: |
    54	          set -euo pipefail
    55	          TAG="$(bash scripts/tests/test-ownership-table.sh --print-legacy-tag)"
    56	          echo "legacy pristine tag: $TAG"
    57	          git fetch --no-tags --depth 1 origin "+refs/tags/$TAG:refs/tags/$TAG"
    58	          git rev-parse --verify "refs/tags/$TAG^{commit}"
    59	
    60	      - name: Install jq (install.sh settings merge dependency)
    61	        run: |
    62	          set -euo pipefail
    63	          if ! command -v jq >/dev/null 2>&1; then
    64	            sudo apt-get update -qq
    65	            sudo apt-get install -y -qq jq
    66	          fi
    67	          jq --version
    68	
    69	      # Fast preflight: a broken DECISION should fail in milliseconds here,
    70	      # not 40 minutes into the observation run.
    71	      - name: Ownership verdict unit oracle (preflight)
    72	        run: |
    73	          set -euo pipefail
    74	          bash scripts/tests/test-ownership-verdict-unit.sh
    75	
    76	      # PLAN-168 W2 (AC-6/AC-6b): INV-4 as an executable assertion — install
    77	      # and upgrade produce the SAME pointer (byte identity + content
    78	      # soundness), repeat upgrades are idempotent, a degraded body is CURED
    79	      # with backup, and an adopter-customized pointer is PRESERVED (S238).
    80	      - name: Protocol pointer INV-4 e2e (4 legs)
    81	        run: |
    82	          set -euo pipefail
    83	          bash scripts/tests/test-protocol-pointer-inv4.sh
    84	
    85	      # The gate itself is proven BEFORE it is trusted: every failure mode it
    86	      # claims to catch is planted with a fake harness and must go red. A CI
    87	      # gate nobody can test is a gate nobody has proven (PLAN-167: 8
    88	      # instrument defects).
    89	      - name: Gate positive control (planted failure modes)
    90	        run: |
    91	          set -euo pipefail
    92	          bash scripts/tests/test-ownership-nightly-gate.sh
    93	
    94	      # PLAN-168 AC-5 — the SCRIPT is the gate (debate r1 QA must-fix 2:
    95	      # describing behavior is not a gate). ownership-nightly-gate.sh runs the
    96	      # e2e and enforces: rc>=2 = infra error (never comparable); summary line
    97	      # present with HARNESS-ERR=0 (partial output fails); observed non-GREEN
    98	      # id set == scripts/tests/ownership-expected-reds.txt exactly; rc
    99	      # coherent with the set (non-empty => rc=1, empty => rc=0). NEVER --map.
   100	      - name: Ownership e2e — full table vs expected non-GREEN set
   101	        env:
   102	          # 60s/cell flakes on 2-core CI iron (2-3x slower than the local
   103	          # baseline the default was sized on).
   104	          CELL_TIMEOUT: "180"
   105	        run: |
   106	          set -euo pipefail
   107	          bash scripts/tests/ownership-nightly-gate.sh
===== scripts/tests/ownership-expected-reds.txt =====
     1	# PLAN-168 AC-5 — the EXPECTED set of non-GREEN cells in the ownership e2e.
     2	# The nightly gate compares the observed RED set against the OWN- lines below
     3	# and fails on ANY difference — including shrinkage: an all-green run means
     4	# the truth table changed, which is a reason to STOP, not to celebrate
     5	# (CLAUDE.md §4). Any TIMEOUT/ESCAPE/AMBIG status fails outright.
     6	# Causes are recorded in docs/ownership-decision-table.md and ADR-190.
     7	#   OWN-0016 — product defect (open)
     8	#   OWN-0024 — test defect (open)
     9	#   OWN-0027 — test defect (open)
    10	# OWN-0074 was closed by PLAN-168 W2 (INV-4 cure): the shared generator makes
    11	# install and upgrade produce identical pointers, so the recorded digest
    12	# finally matches the disk. It is history, not an expectation.
    13	OWN-0016
    14	OWN-0024
    15	OWN-0027
===== scripts/tests/ownership-nightly-gate.sh =====
     1	#!/usr/bin/env bash
     2	# =============================================================================
     3	# PLAN-168 W1 (AC-5) — the ownership nightly GATE.
     4	#
     5	# Runs the ownership e2e harness and compares the observed RED id set
     6	# against scripts/tests/ownership-expected-reds.txt. ANY set difference fails
     7	# — including shrinkage: deliberate reds are part of the contract
     8	# (CLAUDE.md §4), and an all-green run means the truth table changed, which
     9	# is a reason to STOP, not to celebrate.
    10	#
    11	# This is a separate script (not inline YAML) so it can be exercised by a
    12	# positive control (test-ownership-nightly-gate.sh) — a gate nobody can test
    13	# is a gate nobody has proven (PLAN-167: 8 instrument defects; PLAN-168
    14	# debate r1 QA must-fix 2: describing behavior is not a gate).
    15	#
    16	# rc semantics, explicit by design (codex rail r1 P1):
    17	#   - harness rc >= 2  => harness/infra error, NEVER comparable => gate FAILS
    18	#   - summary line must exist and report HARNESS-ERR=0 (partial output fails)
    19	#   - non-empty expected set REQUIRES harness rc == 1 (its designed status)
    20	#   - empty     expected set REQUIRES harness rc == 0
    21	#   - observed RED set must equal the expected set exactly
    22	#   - any OTHER non-GREEN status (TIMEOUT / ESCAPE / AMBIG) fails OUTRIGHT
    23	#     (codex rail r2 P1): an expected-red id that starts timing out or
    24	#     escaping the target keeps the id set unchanged — comparing ids alone
    25	#     would wave a MORE SEVERE regression through as "same set".
    26	#
    27	# NEVER wire the harness's --map mode into this gate: --map exits 0 over
    28	# failures by design (reporting mode) — a dead gate by construction.
    29	#
    30	# Test seams (positive control only — CI uses the defaults):
    31	#   OWNERSHIP_GATE_HARNESS   command to run instead of the real harness
    32	#   OWNERSHIP_GATE_EXPECTED  expected-reds file to compare against
    33	#
    34	# Exit: 0 = set stable. 1 = gate failed (set changed / harness error / vacuous
    35	#       output). 2 = gate usage/infra error (missing expected file).
    36	# =============================================================================
    37	set -uo pipefail
    38	
    39	SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    40	REPO_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
    41	
    42	HARNESS="${OWNERSHIP_GATE_HARNESS:-}"
    43	if [[ -z "$HARNESS" ]]; then
    44	  HARNESS="bash '$SCRIPT_DIR/test-ownership-table.sh'"
    45	fi
    46	EXPECTED="${OWNERSHIP_GATE_EXPECTED:-$SCRIPT_DIR/ownership-expected-reds.txt}"
    47	
    48	[[ -f "$EXPECTED" ]] || { echo "GATE-ERR: expected-reds file not found: $EXPECTED" >&2; exit 2; }
    49	
    50	WORK="$( mktemp -d "${TMPDIR:-/tmp}/own-gate.XXXXXX" )" || exit 2
    51	trap 'rm -rf "$WORK" 2>/dev/null || true' EXIT
    52	
    53	MAP="$WORK/map.txt"
    54	ERRS="$WORK/err.txt"
    55	
    56	rc=0
    57	( cd "$REPO_ROOT" && eval "$HARNESS" ) > "$MAP" 2> "$ERRS" || rc=$?
    58	
    59	cat "$MAP"
    60	sed -n '1,40p' "$ERRS" >&2 || true
    61	
    62	if [[ "$rc" -ge 2 ]]; then
    63	  echo "GATE-RED: harness returned rc=$rc (harness/infra error — not comparable)" >&2
    64	  exit 1
    65	fi
    66	
    67	# The summary line is load-bearing: without it, a run that died mid-table
    68	# would present a truncated (smaller) non-GREEN set that could still match a
    69	# shrunken expectation. HARNESS-ERR must be literally 0.
    70	if ! grep -E '^GREEN=[0-9]+[[:space:]]+RED=[0-9]+[[:space:]]+AMBIG=[0-9]+[[:space:]]+HARNESS-ERR=0$' "$MAP" >/dev/null; then
    71	  echo "GATE-RED: summary line missing or HARNESS-ERR>0 — partial or vacuous output cannot pass" >&2
    72	  exit 1
    73	fi
    74	
    75	# Statuses other than GREEN and RED are never expected and never comparable:
    76	# TIMEOUT / ESCAPE / AMBIG on an EXPECTED-red id would keep the id set intact
    77	# while hiding a more severe regression behind "same set" (codex rail r2 P1).
    78	grep -E '^OWN-[0-9]+[[:space:]]' "$MAP" \
    79	  | awk '$2 != "GREEN" && $2 != "RED" {print $1" "$2}' > "$WORK/other.txt"
    80	if [[ -s "$WORK/other.txt" ]]; then
    81	  echo "GATE-RED: cell(s) in a status that is never acceptable (TIMEOUT/ESCAPE/AMBIG):" >&2
    82	  sed 's/^/  /' "$WORK/other.txt" >&2
    83	  exit 1
    84	fi
    85	
    86	grep -E '^OWN-[0-9]+[[:space:]]' "$MAP" \
    87	  | awk '$2 == "RED" {print $1}' | LC_ALL=C sort > "$WORK/got.txt"
    88	grep -E '^OWN-' "$EXPECTED" | LC_ALL=C sort > "$WORK/exp.txt"
    89	
    90	if ! diff -u "$WORK/exp.txt" "$WORK/got.txt"; then
    91	  echo "GATE-RED: the RED set CHANGED (shrinkage included: all-green means the table changed — stop and find out why)" >&2
    92	  exit 1
    93	fi
    94	
    95	if [[ -s "$WORK/exp.txt" && "$rc" -ne 1 ]]; then
    96	  echo "GATE-RED: rc=$rc but the expected set is non-empty (harness must exit 1 over expected reds)" >&2
    97	  exit 1
    98	fi
    99	if [[ ! -s "$WORK/exp.txt" && "$rc" -ne 0 ]]; then
   100	  echo "GATE-RED: rc=$rc but the expected set is empty (harness must exit 0 when everything is green)" >&2
   101	  exit 1
   102	fi
   103	
   104	echo "ownership gate: RED set stable ($(wc -l < "$WORK/exp.txt" | tr -d ' ') expected RED cells, zero TIMEOUT/ESCAPE/AMBIG)"
   105	exit 0
===== scripts/tests/test-ownership-nightly-gate.sh =====
     1	#!/usr/bin/env bash
     2	# =============================================================================
     3	# PLAN-168 W1 — positive control for ownership-nightly-gate.sh.
     4	#
     5	# The gate is the instrument that watches the ownership e2e in CI; this test
     6	# watches the GATE. Every failure mode the gate claims to catch is planted
     7	# here with a fake harness, and the test demands the gate actually goes red —
     8	# green-without-control proves nothing (PLAN-167: 8 instrument defects).
     9	#
    10	# Scenarios:
    11	#   S1  matching set, rc=1, HARNESS-ERR=0            => gate PASSES
    12	#   S2  set GREW (one extra red)                     => gate FAILS
    13	#   S3  set SHRANK (all green, rc=0)                 => gate FAILS
    14	#   S4  harness rc=2 (infra error)                   => gate FAILS
    15	#   S5  summary line missing (truncated output)      => gate FAILS
    16	#   S6  HARNESS-ERR=1 in summary                     => gate FAILS
    17	#   S7  rc=0 while expected set non-empty            => gate FAILS
    18	#   S8  set SWAPPED (same size, different ids)       => gate FAILS
    19	#   S9  empty expected set + all green, rc=0         => gate PASSES
    20	#   S10 expected id degraded to TIMEOUT (same ids)   => gate FAILS
    21	#   S11 expected id degraded to ESCAPE  (same ids)   => gate FAILS
    22	#   S12 green cell degraded to AMBIG                 => gate FAILS
    23	#
    24	# Exit: 0 all scenarios behave. 1 at least one does not. 2 harness error.
    25	# =============================================================================
    26	set -uo pipefail
    27	
    28	SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    29	GATE="$SCRIPT_DIR/ownership-nightly-gate.sh"
    30	[[ -f "$GATE" ]] || { echo "ERROR: gate not found: $GATE" >&2; exit 2; }
    31	
    32	WORK="$( mktemp -d "${TMPDIR:-/tmp}/own-gate-test.XXXXXX" )" || exit 2
    33	trap 'rm -rf "$WORK" 2>/dev/null || true' EXIT
    34	
    35	# --- fake harness ------------------------------------------------------------
    36	# Emits a canned map on stdout and exits with a canned rc. The gate consumes
    37	# it via OWNERSHIP_GATE_HARNESS exactly as it would the real harness.
    38	mk_fake() { # $1=out-file $2=rc-file
    39	  cat > "$WORK/fake-harness.sh" <<EOF
    40	#!/usr/bin/env bash
    41	cat "$1"
    42	exit "\$(cat "$2")"
    43	EOF
    44	  chmod +x "$WORK/fake-harness.sh"
    45	}
    46	
    47	map_line() { # $1=id $2=status
    48	  printf '%-10s %-7s exp=%-16s/%-22s got=%-16s/%-22s rc=%-3s %s\n' \
    49	    "$1" "$2" "V" "H" "V" "H" "0" "test"
    50	}
    51	
    52	write_map() { # $1=file, then "id:status" pairs; appends summary from counts
    53	  local f="$1"; shift
    54	  local green=0 red=0 err="${SUMMARY_ERR:-0}"
    55	  : > "$f"
    56	  local pair id st
    57	  for pair in "$@"; do
    58	    id="${pair%%:*}"; st="${pair##*:}"
    59	    map_line "$id" "$st" >> "$f"
    60	    case "$st" in GREEN) green=$((green+1)) ;; *) red=$((red+1)) ;; esac
    61	  done
    62	  if [[ "${SUMMARY_OMIT:-0}" -ne 1 ]]; then
    63	    printf '\nGREEN=%d  RED=%d  AMBIG=0  HARNESS-ERR=%d\n' "$green" "$red" "$err" >> "$f"
    64	  fi
    65	}
    66	
    67	expected_4() {
    68	  printf 'OWN-0016\nOWN-0024\nOWN-0027\nOWN-0074\n' > "$WORK/exp.txt"
    69	}
    70	
    71	run_gate() { # $1=expected-rc  $2=label
    72	  local want="$1" label="$2" got=0
    73	  OWNERSHIP_GATE_HARNESS="$WORK/fake-harness.sh" \
    74	  OWNERSHIP_GATE_EXPECTED="$WORK/exp.txt" \
    75	    bash "$GATE" > "$WORK/gate-out.txt" 2> "$WORK/gate-err.txt" || got=$?
    76	  if [[ "$got" -eq "$want" ]]; then
    77	    echo "PASS  $label (gate rc=$got)"
    78	    return 0
    79	  fi
    80	  echo "FAIL  $label — gate rc=$got, expected $want"
    81	  sed -n '1,15p' "$WORK/gate-out.txt" | sed 's/^/      out| /'
    82	  sed -n '1,15p' "$WORK/gate-err.txt" | sed 's/^/      err| /'
    83	  return 1
    84	}
    85	
    86	FAILURES=0
    87	
    88	# S1 — matching set, honest rc=1 => PASS
    89	expected_4
    90	write_map "$WORK/map.txt" OWN-0001:GREEN OWN-0016:RED OWN-0024:RED OWN-0027:RED OWN-0074:RED
    91	echo 1 > "$WORK/rc.txt"; mk_fake "$WORK/map.txt" "$WORK/rc.txt"
    92	run_gate 0 "S1 matching set + rc=1" || FAILURES=$((FAILURES+1))
    93	
    94	# S2 — set grew => FAIL
    95	write_map "$WORK/map.txt" OWN-0001:RED OWN-0016:RED OWN-0024:RED OWN-0027:RED OWN-0074:RED
    96	echo 1 > "$WORK/rc.txt"; mk_fake "$WORK/map.txt" "$WORK/rc.txt"
    97	run_gate 1 "S2 set grew" || FAILURES=$((FAILURES+1))
    98	
    99	# S3 — set shrank to zero (all green, honest rc=0) => FAIL (all-green = STOP)
   100	write_map "$WORK/map.txt" OWN-0001:GREEN OWN-0016:GREEN OWN-0024:GREEN OWN-0027:GREEN OWN-0074:GREEN
   101	echo 0 > "$WORK/rc.txt"; mk_fake "$WORK/map.txt" "$WORK/rc.txt"
   102	run_gate 1 "S3 set shrank (all green)" || FAILURES=$((FAILURES+1))
   103	
   104	# S4 — harness infra error rc=2 => FAIL
   105	write_map "$WORK/map.txt" OWN-0016:RED
   106	echo 2 > "$WORK/rc.txt"; mk_fake "$WORK/map.txt" "$WORK/rc.txt"
   107	run_gate 1 "S4 harness rc=2" || FAILURES=$((FAILURES+1))
   108	
   109	# S5 — summary line missing (truncated run) => FAIL even with matching ids
   110	# (explicit set/reset: VAR=x prefixed to a FUNCTION call has version-divergent
   111	# persistence semantics in bash — never rely on it.)
   112	SUMMARY_OMIT=1
   113	write_map "$WORK/map.txt" OWN-0016:RED OWN-0024:RED OWN-0027:RED OWN-0074:RED
   114	SUMMARY_OMIT=0
   115	echo 1 > "$WORK/rc.txt"; mk_fake "$WORK/map.txt" "$WORK/rc.txt"
   116	run_gate 1 "S5 summary missing" || FAILURES=$((FAILURES+1))
   117	
   118	# S6 — HARNESS-ERR=1 => FAIL even with matching ids
   119	SUMMARY_ERR=1
   120	write_map "$WORK/map.txt" OWN-0016:RED OWN-0024:RED OWN-0027:RED OWN-0074:RED
   121	SUMMARY_ERR=0
   122	echo 1 > "$WORK/rc.txt"; mk_fake "$WORK/map.txt" "$WORK/rc.txt"
   123	run_gate 1 "S6 HARNESS-ERR=1" || FAILURES=$((FAILURES+1))
   124	
   125	# S7 — rc=0 while expected set non-empty (rc/set incoherence) => FAIL
   126	write_map "$WORK/map.txt" OWN-0016:RED OWN-0024:RED OWN-0027:RED OWN-0074:RED
   127	echo 0 > "$WORK/rc.txt"; mk_fake "$WORK/map.txt" "$WORK/rc.txt"
   128	run_gate 1 "S7 rc=0 with non-empty expected set" || FAILURES=$((FAILURES+1))
   129	
   130	# S8 — same size, different ids => FAIL
   131	write_map "$WORK/map.txt" OWN-0016:RED OWN-0024:RED OWN-0027:RED OWN-0099:RED OWN-0074:GREEN
   132	echo 1 > "$WORK/rc.txt"; mk_fake "$WORK/map.txt" "$WORK/rc.txt"
   133	run_gate 1 "S8 set swapped" || FAILURES=$((FAILURES+1))
   134	
   135	# S9 — empty expected set + all green + rc=0 => PASS
   136	: > "$WORK/exp.txt"
   137	write_map "$WORK/map.txt" OWN-0001:GREEN OWN-0002:GREEN
   138	echo 0 > "$WORK/rc.txt"; mk_fake "$WORK/map.txt" "$WORK/rc.txt"
   139	run_gate 0 "S9 empty expected set, all green" || FAILURES=$((FAILURES+1))
   140	
   141	# S10-S12 — an EXPECTED-red id degrades to TIMEOUT / ESCAPE / AMBIG: the id
   142	# set is UNCHANGED, so an ids-only comparison would pass a more severe
   143	# regression as "same set" (codex rail r2 P1). The gate must go red on the
   144	# STATUS, not just the set.
   145	expected_4
   146	write_map "$WORK/map.txt" OWN-0016:TIMEOUT OWN-0024:RED OWN-0027:RED OWN-0074:RED
   147	echo 1 > "$WORK/rc.txt"; mk_fake "$WORK/map.txt" "$WORK/rc.txt"
   148	run_gate 1 "S10 expected id degraded to TIMEOUT" || FAILURES=$((FAILURES+1))
   149	
   150	write_map "$WORK/map.txt" OWN-0016:ESCAPE OWN-0024:RED OWN-0027:RED OWN-0074:RED
   151	echo 1 > "$WORK/rc.txt"; mk_fake "$WORK/map.txt" "$WORK/rc.txt"
   152	run_gate 1 "S11 expected id degraded to ESCAPE" || FAILURES=$((FAILURES+1))
   153	
   154	write_map "$WORK/map.txt" OWN-0001:AMBIG OWN-0016:RED OWN-0024:RED OWN-0027:RED OWN-0074:RED
   155	echo 1 > "$WORK/rc.txt"; mk_fake "$WORK/map.txt" "$WORK/rc.txt"
   156	run_gate 1 "S12 green cell degraded to AMBIG" || FAILURES=$((FAILURES+1))
   157	
   158	echo ""
   159	if [[ "$FAILURES" -gt 0 ]]; then
   160	  echo "ownership-nightly-gate positive control: $FAILURES scenario(s) FAILED"
   161	  exit 1
   162	fi
   163	echo "ownership-nightly-gate positive control: 12/12 scenarios behave"
   164	exit 0
===== scripts/tests/test-protocol-pointer-render.sh =====
     1	#!/usr/bin/env bash
     2	# =============================================================================
     3	# PLAN-168 W2 — unit control for the shared protocol-pointer generator
     4	# (_render_protocol_pointer / _render_protocol_pointer_degraded /
     5	# _protocol_pointer_is_degraded in scripts/_framework_manifest_set.sh).
     6	#
     7	# Scenarios:
     8	#   R1  healthy render == REAL install.sh output, byte for byte (the parity
     9	#       that IS INV-4's fix — normalized inputs, as the plan requires)
    10	#   R2  degraded render | substitute-token == healthy render (one template)
    11	#   R3  recognizer: exact degraded file => rc=0 (curable)
    12	#   R4  recognizer: healthy (substituted) file => rc=1 (never curable)
    13	#   R5  recognizer: degraded file + 1-char adopter edit => rc=1 (preserved)
    14	#   R6  recognizer: adopter file that merely CONTAINS the token => rc=1
    15	#       (the codex r1 P1 substring-destruction case)
    16	#   R7  recognizer: unparseable upgrade line (space in target) => rc=1
    17	#   R8  inside-target checkout => relative render (no token, no source path)
    18	#
    19	# Exit: 0 all pass · 1 failure · 2 harness error.
    20	# =============================================================================
    21	set -uo pipefail
    22	
    23	SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    24	REPO_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
    25	
    26	# shellcheck source=/dev/null
    27	. "$REPO_ROOT/scripts/_framework_manifest_set.sh" 2>/dev/null || {
    28	  echo "ERROR: cannot source _framework_manifest_set.sh" >&2; exit 2; }
    29	for fn in _render_protocol_pointer _render_protocol_pointer_degraded _protocol_pointer_is_degraded; do
    30	  command -v "$fn" >/dev/null 2>&1 || { echo "ERROR: $fn missing" >&2; exit 2; }
    31	done
    32	
    33	WORK="$( mktemp -d "${TMPDIR:-/tmp}/ptr-render.XXXXXX" )" || exit 2
    34	trap 'chmod -R u+w "$WORK" 2>/dev/null; rm -rf "$WORK" 2>/dev/null' EXIT
    35	
    36	FAILURES=0
    37	say() { echo "$1"; }
    38	fail() { echo "FAIL  $1"; FAILURES=$((FAILURES+1)); }
    39	
    40	# --- R1: byte parity with a REAL install --------------------------------------
    41	# Normalized target (physical path, no trailing/double slashes) — install.sh
    42	# normalizes its TARGET, and the plan requires normalized inputs for exactly
    43	# this reason.
    44	U="$WORK/t"; mkdir -p "$U"
    45	U="$( cd "$U" && pwd -P )"
    46	( cd "$U" && git init -q )
    47	if CEO_INSTALL_SKIP_SELF_SHA=1 CEO_RAG_INSTALL_PROMPT=0 \
    48	     bash "$REPO_ROOT/scripts/install.sh" "$U" --profile core --stack generic \
    49	     > "$WORK/install.log" 2>&1; then
    50	  _render_protocol_pointer "$REPO_ROOT" "$U" core generic "$REPO_ROOT" > "$WORK/render.txt"
    51	  if diff -u "$U/PROTOCOL.md" "$WORK/render.txt" > "$WORK/r1.diff" 2>&1; then
    52	    say "PASS  R1 healthy render == real install output"
    53	  else
    54	    fail "R1 parity with real install"; sed -n '1,10p' "$WORK/r1.diff"
    55	  fi
    56	else
    57	  fail "R1 install.sh itself failed (see $WORK/install.log)"; sed -n '1,5p' "$WORK/install.log"
    58	fi
    59	
    60	# --- R2: one template — degraded | substitution == healthy --------------------
    61	_render_protocol_pointer_degraded "$U" core generic \
    62	  | sed "s|{{PROTOCOL_SOURCE}}|$( printf '%s' "$REPO_ROOT" | sed 's/[|&\\]/\\&/g' )|g" \
    63	  > "$WORK/deg-subst.txt"
    64	if diff -q "$WORK/deg-subst.txt" "$WORK/render.txt" >/dev/null 2>&1; then
    65	  say "PASS  R2 degraded+substitute == healthy (single template)"
    66	else
    67	  fail "R2 template split"; diff "$WORK/deg-subst.txt" "$WORK/render.txt" | head -5
    68	fi
    69	
    70	# --- R3: recognizer accepts an exact degraded body ----------------------------
    71	_render_protocol_pointer_degraded "$U" core generic > "$WORK/degraded.md"
    72	if _protocol_pointer_is_degraded "$WORK/degraded.md"; then
    73	  say "PASS  R3 exact degraded body recognized (curable)"
    74	else
    75	  fail "R3 exact degraded body NOT recognized"
    76	fi
    77	
    78	# --- R4: healthy file is never "degraded" -------------------------------------
    79	if _protocol_pointer_is_degraded "$WORK/render.txt"; then
    80	  fail "R4 healthy file misclassified as degraded"
    81	else
    82	  say "PASS  R4 healthy file not curable (preserved)"
    83	fi
    84	
    85	# --- R5: one adopter edit anywhere => preserved -------------------------------
    86	sed 's/git pull/git fetch/' "$WORK/degraded.md" > "$WORK/degraded-edited.md"
    87	if _protocol_pointer_is_degraded "$WORK/degraded-edited.md"; then
    88	  fail "R5 edited degraded body still classified curable (DATA LOSS route)"
    89	else
    90	  say "PASS  R5 edited degraded body preserved"
    91	fi
    92	
    93	# --- R6: adopter file that merely CONTAINS the token --------------------------
    94	printf '%s\n' "# My protocol notes" "" \
    95	  "We keep the marker {{PROTOCOL_SOURCE}} here on purpose." \
    96	  "  {{PROTOCOL_SOURCE}}/scripts/upgrade.sh $U --profile core --stack generic" \
    97	  > "$WORK/adopter.md"
    98	if _protocol_pointer_is_degraded "$WORK/adopter.md"; then
    99	  fail "R6 adopter file containing the token misclassified (substring trap)"
   100	else
   101	  say "PASS  R6 token-containing adopter file preserved"
   102	fi
   103	
   104	# --- R7: unparseable upgrade line (space in target) => preserved --------------
   105	_render_protocol_pointer_degraded "/tmp/has space" core generic > "$WORK/spacey.md"
   106	if _protocol_pointer_is_degraded "$WORK/spacey.md"; then
   107	  fail "R7 ambiguous (spaced) target treated as parseable"
   108	else
   109	  say "PASS  R7 ambiguous target preserved (documented residual)"
   110	fi
   111	
   112	# --- R8: inside-target checkout renders the relative form ---------------------
   113	IN="$WORK/inside"; mkdir -p "$IN/vendor/ceo"
   114	IN="$( cd "$IN" && pwd -P )"
   115	_render_protocol_pointer "$IN/vendor/ceo" "$IN" core generic "$IN/vendor/ceo" > "$WORK/rel.txt"
   116	if grep -q '\./vendor/ceo/PROTOCOL.md' "$WORK/rel.txt" \
   117	   && ! grep -q '{{PROTOCOL_SOURCE}}' "$WORK/rel.txt" \
   118	   && ! grep -F -q "$IN/vendor" "$WORK/rel.txt"; then
   119	  say "PASS  R8 inside-target => relative render"
   120	else
   121	  fail "R8 inside-target render wrong"; sed -n '1,8p' "$WORK/rel.txt"
   122	fi
   123	
   124	echo ""
   125	if [[ "$FAILURES" -gt 0 ]]; then
   126	  echo "protocol-pointer render control: $FAILURES FAILED"
   127	  exit 1
   128	fi
   129	echo "protocol-pointer render control: 8/8 pass"
   130	exit 0
===== scripts/tests/test-protocol-pointer-inv4.sh =====
     1	#!/usr/bin/env bash
     2	# =============================================================================
     3	# PLAN-168 W2 (AC-6/AC-6b) — INV-4 as an executable assertion.
     4	#
     5	# INV-4: install and upgrade produce the SAME root PROTOCOL.md pointer.
     6	# Byte identity alone is VACUOUS (codex rail r1 P1: a shared generator based
     7	# on the broken template would make both sides identical AND wrong), so every
     8	# leg also asserts CONTENT: the {{PROTOCOL_SOURCE}} token is ABSENT and the
     9	# resolved source path is PRESENT.
    10	#
    11	# Legs (all with NORMALIZED inputs — pwd -P, fixed profile/stack):
    12	#   L1  install -> upgrade         : pointer byte-identical, content sound
    13	#   L2  upgrade -> upgrade         : idempotent, byte-identical
    14	#   L3  degraded body -> upgrade   : CURED (refreshed with backup, sound)
    15	#   L4  adopter-edited -> upgrade  : PRESERVED byte-identical (S238 guard —
    16	#                                    the cure must never widen into clobber)
    17	#
    18	# Exit: 0 all legs pass · 1 failure · 2 harness error.
    19	# =============================================================================
    20	set -uo pipefail
    21	
    22	SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
    23	REPO_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
    24	
    25	# shellcheck source=/dev/null
    26	. "$REPO_ROOT/scripts/_framework_manifest_set.sh" 2>/dev/null || {
    27	  echo "ERROR: cannot source _framework_manifest_set.sh" >&2; exit 2; }
    28	command -v _render_protocol_pointer_degraded >/dev/null 2>&1 || {
    29	  echo "ERROR: generator missing (W2 not in tree)" >&2; exit 2; }
    30	
    31	WORK="$( mktemp -d "${TMPDIR:-/tmp}/inv4.XXXXXX" )" || exit 2
    32	WORK="$( cd "$WORK" && pwd -P )"
    33	trap 'chmod -R u+w "$WORK" 2>/dev/null; rm -rf "$WORK" 2>/dev/null' EXIT
    34	
    35	PROFILE=core
    36	STACK=generic
    37	FAILURES=0
    38	fail() { echo "FAIL  $1"; FAILURES=$((FAILURES+1)); }
    39	
    40	run_install() { # $1=target
    41	  CEO_INSTALL_SKIP_SELF_SHA=1 CEO_RAG_INSTALL_PROMPT=0 \
    42	    bash "$REPO_ROOT/scripts/install.sh" "$1" --profile "$PROFILE" --stack "$STACK" \
    43	    > "$WORK/install.log" 2>&1
    44	}
    45	run_upgrade() { # $1=target $2=log
    46	  CEO_INSTALL_SKIP_SELF_SHA=1 \
    47	    bash "$REPO_ROOT/scripts/upgrade.sh" "$1" --profile "$PROFILE" --stack "$STACK" \
    48	    > "$2" 2>&1
    49	}
    50	assert_sound() { # $1=file $2=label — token absent, resolved source present
    51	  if grep -F -q '{{PROTOCOL_SOURCE}}' "$1"; then
    52	    fail "$2: token {{PROTOCOL_SOURCE}} still present (degraded output)"
    53	    return 1
    54	  fi
    55	  if ! grep -F -q "$REPO_ROOT/PROTOCOL.md" "$1"; then
    56	    fail "$2: resolved source path missing from pointer"
    57	    return 1
    58	  fi
    59	  return 0
    60	}
    61	
    62	T="$WORK/t"; mkdir -p "$T"; ( cd "$T" && git init -q )
    63	T="$( cd "$T" && pwd -P )"
    64	
    65	# --- L1: install -> upgrade ---------------------------------------------------
    66	if ! run_install "$T"; then
    67	  echo "ERROR: install failed"; sed -n '1,8p' "$WORK/install.log"; exit 2
    68	fi
    69	cp "$T/PROTOCOL.md" "$WORK/after-install.md"
    70	assert_sound "$WORK/after-install.md" "L1 post-install" || true
    71	if ! run_upgrade "$T" "$WORK/upgrade1.log"; then
    72	  echo "ERROR: upgrade failed"; sed -n '1,12p' "$WORK/upgrade1.log"; exit 2
    73	fi
    74	if cmp -s "$WORK/after-install.md" "$T/PROTOCOL.md"; then
    75	  assert_sound "$T/PROTOCOL.md" "L1 post-upgrade" && echo "PASS  L1 install->upgrade byte-identical + sound"
    76	else
    77	  fail "L1 pointer changed across install->upgrade (INV-4 broken)"
    78	  diff "$WORK/after-install.md" "$T/PROTOCOL.md" | head -8
    79	fi
    80	
    81	# --- L2: upgrade -> upgrade (idempotence) ------------------------------------
    82	cp "$T/PROTOCOL.md" "$WORK/after-up1.md"
    83	if ! run_upgrade "$T" "$WORK/upgrade2.log"; then
    84	  echo "ERROR: second upgrade failed"; sed -n '1,12p' "$WORK/upgrade2.log"; exit 2
    85	fi
    86	if cmp -s "$WORK/after-up1.md" "$T/PROTOCOL.md"; then
    87	  echo "PASS  L2 upgrade->upgrade idempotent"
    88	else
    89	  fail "L2 pointer churned across repeat upgrade"
    90	  diff "$WORK/after-up1.md" "$T/PROTOCOL.md" | head -8
    91	fi
    92	
    93	# --- L3: degraded body is CURED ----------------------------------------------
    94	_render_protocol_pointer_degraded "$T" "$PROFILE" "$STACK" > "$T/PROTOCOL.md"
    95	if ! run_upgrade "$T" "$WORK/upgrade3.log"; then
    96	  echo "ERROR: cure upgrade failed"; sed -n '1,12p' "$WORK/upgrade3.log"; exit 2
    97	fi
    98	if grep -F -q '{{PROTOCOL_SOURCE}}' "$T/PROTOCOL.md"; then
    99	  fail "L3 degraded pointer NOT cured (token survived the upgrade — immortal defect)"
   100	  sed -n '1,6p' "$T/PROTOCOL.md"
   101	else
   102	  assert_sound "$T/PROTOCOL.md" "L3 post-cure" || true
   103	  if grep -q "CURED: PROTOCOL.md" "$WORK/upgrade3.log"; then
   104	    echo "PASS  L3 degraded body cured (REFRESH route taken)"
   105	  else
   106	    fail "L3 pointer sound but the CURED route was not what ran (check upgrade3.log)"
   107	    grep -n "PROTOCOL.md" "$WORK/upgrade3.log" | head -5
   108	  fi
   109	  if ls "$T"/.claude/backup*/PROTOCOL.md >/dev/null 2>&1 \
   110	     || grep -q "BACKED UP: PROTOCOL.md" "$WORK/upgrade3.log"; then
   111	    echo "PASS  L3b cure kept a backup of the degraded original"
   112	  else
   113	    fail "L3b no backup evidence for the cured pointer"
   114	  fi
   115	fi
   116	
   117	# --- L4: adopter-customized pointer is PRESERVED (S238 guard) ----------------
   118	printf '\nAdopter note: we run upgrades on Fridays.\n' >> "$T/PROTOCOL.md"
   119	cp "$T/PROTOCOL.md" "$WORK/customized.md"
   120	if ! run_upgrade "$T" "$WORK/upgrade4.log"; then
   121	  echo "ERROR: preserve-leg upgrade failed"; sed -n '1,12p' "$WORK/upgrade4.log"; exit 2
   122	fi
   123	if cmp -s "$WORK/customized.md" "$T/PROTOCOL.md"; then
   124	  echo "PASS  L4 adopter-customized pointer preserved byte-identical"
   125	else
   126	  fail "L4 adopter-customized pointer was MODIFIED (the cure widened into clobber — S238)"
   127	  diff "$WORK/customized.md" "$T/PROTOCOL.md" | head -8
   128	fi
   129	
   130	echo ""
   131	if [[ "$FAILURES" -gt 0 ]]; then
   132	  echo "INV-4 assertion: $FAILURES leg(s) FAILED"
   133	  exit 1
   134	fi
   135	echo "INV-4 assertion: 4/4 legs pass (byte identity + content soundness + cure + preserve)"
   136	exit 0
===== .claude/adr/ADR-190-ownership-decision-table-contract.md =====
     1	---
     2	adr_id: ADR-190
     3	title: A tabela de decisão de propriedade é O contrato — dimensões, enum de 4 vereditos, INV-1..4 e a assimetria SPEC/PROTOCOL
     4	status: ACCEPTED
     5	proposed_at: 2026-08-07
     6	accepted_at: 2026-08-07
     7	proposed_by: CEO (S297 — AC-10 do PLAN-167, cumprido pelo PLAN-168 W3)
     8	decided_by: Owner (assinatura GPG da cerimônia do PLAN-168)
     9	risk_tier: A
    10	debate_required: true
    11	related_plans: [PLAN-167, PLAN-168]
    12	related_adrs: [ADR-155, ADR-155-AMEND-1]
    13	---
    14	
    15	# ADR-190 — Propriedade de superfície condicional é decidida pela TABELA, executada pelos scripts
    16	
    17	## §1 Contexto
    18	
    19	O PLAN-167 (`7c0828a`) substituiu dezenas de `if`s espalhados por
    20	`install.sh`/`upgrade.sh` por uma decisão única: `_ownership_verdict()` em
    21	`scripts/_framework_manifest_set.sh`, função **pura** das dimensões
    22	observadas, devolvendo `"<VERDICT> <HASH_SOURCE>"`. Os scripts **observam →
    23	chamam → executam**; eles não decidem. O PLAN-168 fechou os follow-ups
    24	(fiação de CI, INV-4, este ADR). Este registro existe para que a próxima
    25	pessoa que "conserte uma assimetria" tenha onde ler que ela é **decidida**,
    26	não acidental.
    27	
    28	Autoridades, em ordem:
    29	- **Valores:** `scripts/tests/ownership_table.tsv` — "THIS FILE IS THE TRUTH".
    30	- **Racional e legalidade:** `docs/ownership-decision-table.md`.
    31	- **Decisão executável:** `_ownership_verdict()` — e SÓ ela.
    32	- **Oráculos:** `test-ownership-verdict-unit.sh` (decisão, milissegundos) e
    33	  `test-ownership-table.sh` (observação/execução, ~25 min de installs reais);
    34	  `test-protocol-pointer-inv4.sh` (INV-4 executável). CI: unit + controles
    35	  por-PR em `smoke-install.yml`; e2e nightly em `ownership-nightly.yml` com
    36	  gate de conjunto (`ownership-nightly-gate.sh` vs
    37	  `ownership-expected-reds.txt`).
    38	
    39	## §2 Decisão
    40	
    41	### §2.1 As 10 dimensões
    42	
    43	`surface · prior_record · live_type · live_content · source_has · mode ·
    44	ceremony · operation · skip_requested · fault` — definidas, com domínios e
    45	regras de legalidade (R-01..R-10), em `docs/ownership-decision-table.md` §2.
    46	Uma célula é um ponto legal desse produto; a TSV enumera as classes de
    47	equivalência (R-10).
    48	
    49	### §2.2 O enum final tem QUATRO vereditos
    50	
    51	`DELIVER · REFRESH · PRESERVE_OWNED · PRESERVE_UNOWNED`
    52	
    53	- A OQ-9 (ratificada pelo Owner, 2026-08-07) colapsou `OMIT_RECORD` em
    54	  `PRESERVE_UNOWNED`: os dois diziam "sem registro no disco" e diferiam só
    55	  pela coluna `prior_record` — membro redundante de enum é onde dois ramos
    56	  discordam sobre qual se aplica.
    57	- **`ABORT_SURFACE` NÃO é veredito.** É resultado de OBSERVAÇÃO/EXECUÇÃO do
    58	  harness (INV-3: falha de execução nunca avança o registro). A função nunca
    59	  o devolve; um ADR que o listasse como veredito contradiria o código.
    60	
    61	### §2.3 As quatro invariantes cross-surface (INV-1..4)
    62	
    63	- **INV-1** — continuidade em install rerun não muda digest registrado fora
    64	  do conjunto de continuidade.
    65	- **INV-2** — serialização `LINK` só cobre paths que JÁ eram `LINK` antes do
    66	  run (o symlink do adotante nunca vira registro de entrega).
    67	- **INV-3** — falha de execução nunca avança o registro (`ABORT_SURFACE` é
    68	  esse evento, nomeado).
    69	- **INV-4** — install e upgrade geram conteúdo **byte-idêntico** para a mesma
    70	  superfície. Fechada pelo PLAN-168 W2: o ponteiro `PROTOCOL.md` é gerado
    71	  pela ÚNICA função compartilhada (`_render_protocol_pointer*` em
    72	  `_framework_manifest_set.sh`); heredoc privado em caller é REGRESSÃO desta
    73	  invariante. Corolário pós-INV-4: em linhas de continuidade o digest
    74	  canônico e o prior record são os MESMOS bytes — `HASH_PRIOR_RECORD` e
    75	  `HASH_CANONICAL_POINTER` colapsam num só claim, e o harness trata os dois
    76	  nomes como equivalentes SÓ quando os candidatos aliasam
    77	  (docs §2.4, "Hash-name aliasing").
    78	
    79	### §2.4 A assimetria deliberada SPEC vs PROTOCOL
    80	
    81	- **`SPEC/v1` editado = FORK** ⇒ a rota forçada **refresha** (é o contrato de
    82	  compliance publicado; ADR-155-AMEND-1 §4).
    83	- **`PROTOCOL.md` editado = CONTEÚDO do adotante** ⇒ **preserva** (prosa
    84	  editável; sobrescrever é a perda S238 que a decisão (iii) do ADR-155
    85	  fechou).
    86	
    87	É a assimetria que mais convida um "conserto" futuro. Ela é **decidida**.
    88	Quem quiser mudá-la emenda ESTE ADR e refaz o debate — não "alinha" os dois
    89	ramos num PR.
    90	
    91	- **`degraded` (PLAN-168 W2) não é exceção à preservação de `edited`:** é a
    92	  constatação de que o corpo com `{{PROTOCOL_SOURCE}}` literal é lixo que o
    93	  PRÓPRIO framework produziu (upgrade pré-fix). Reconhecimento por
    94	  **reconstrução exata de template** (nunca substring, nunca hash estático —
    95	  o corpo embute TARGET/PROFILE/STACK da invocação), qualquer desvio ⇒
    96	  `edited` ⇒ preservado. Cura = `REFRESH` com backup. Doutrina r20
    97	  (`legacy_pristine`) aplicada ao ponteiro; célula própria na TSV
    98	  (OWN-0092..0094), R-04b.
    99	
   100	### §2.5 Relação com o ADR-155-AMEND-1
   101	
   102	**Emendado, não revogado.** A enumeração compartilhada (decisão (i)) e a
   103	propriedade por registro de entrega continuam válidas; este ADR acrescenta o
   104	contrato da DECISÃO (tabela + função + oráculos) e a INV-4 sobre o CONTEÚDO
   105	que os dois lados produzem.
   106	
   107	### §2.6 Células conhecidas-abertas (estado ao aceitar este ADR)
   108	
   109	Abertas — **3**, com causa, protegidas pelo gate de conjunto (encolher =
   110	falha; verde-total = a tabela mudou ⇒ PARAR):
   111	- `OWN-0016` — defeito de PRODUTO (aberto).
   112	- `OWN-0024` / `OWN-0027` — defeitos do TESTE (células de fault de execução
   113	  que o harness ainda não instancia fielmente).
   114	
   115	Fechada — histórico, não expectativa:
   116	- `OWN-0074` — defeito de PRODUTO fechado pelo PLAN-168 W2: era a INV-4 se
   117	  manifestando no digest gravado (`HASH_CANONICAL_POINTER` que não batia com
   118	  o disco). Um ADR que a listasse como aberta nasceria stale.
   119	
   120	## §3 Consequências
   121	
   122	- Adicionar um ramo que decide propriedade LOCALMENTE em
   123	  `install.sh`/`upgrade.sh`/`doctor.sh`/`uninstall.sh` reabre a classe que o
   124	  PLAN-167 fechou — é veto de revisão, não estilo.
   125	- Mudanças na tabela/enum/dimensões exigem: debate L3 + atualização em
   126	  `docs/ownership-decision-table.md` + TSV + oráculos verdes + este ADR
   127	  emendado. Os quatro andam juntos ou a mudança não anda.
   128	- O conjunto esperado de vermelhos (`ownership-expected-reds.txt`) é parte do
   129	  contrato: o CI compara o CONJUNTO exato (nunca `--map`, nunca rc cru) e
   130	  qualquer status TIMEOUT/ESCAPE/AMBIG falha imediatamente.
   131	
   132	## §4 Blast radius
   133	
   134	`scripts/install.sh` · `scripts/upgrade.sh` · `scripts/_framework_manifest_set.sh`
   135	· `scripts/doctor.sh` · `scripts/uninstall.sh` · os 4 oráculos/gates de teste ·
   136	`smoke-install.yml` · `ownership-nightly.yml` · adotantes em campo (a cura do
   137	degraded reescreve, com backup, um arquivo que upgrades antigos corromperam).

exec
/bin/zsh -lc 'git diff -- CLAUDE.md README.md README.pt-BR.md docs/ARCHITECTURE.md docs/CTO-GUIDE.md docs/FAQ.md docs/README.md docs/ownership-decision-table.md npm/README.md' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
diff --git a/CLAUDE.md b/CLAUDE.md
index ef45369..1c6a47e 100644
--- a/CLAUDE.md
+++ b/CLAUDE.md
@@ -51,7 +51,7 @@ library — you install it *into* an existing repository with
 - **A cross-LLM pair-rail** — a second model (Codex) reviews canonical edits Claude proposes, so no single model is both author and sole reviewer.
 - **A skill library** — **166 skills** ready-made (42 core + 8 frontend + 116 domain).
 - **Governance hooks** — 57 Python hook scripts on disk (46 wired into `.claude/settings.json` (48 event registrations)), built on 68 stdlib-only `_lib/` modules.
-- **189 ADRs** (architecture decision records, `.claude/adr/`) and **27 slash commands** (`.claude/commands/`).
+- **190 ADRs** (architecture decision records, `.claude/adr/`) and **27 slash commands** (`.claude/commands/`).
 
 A note this repo keeps deliberately: **there is no speed claim.** Six
 internal experiments found no general speedup over an optimized solo
@@ -86,7 +86,7 @@ workflow — the value here is governance and auditability, not throughput.
 - **Debate for L3+ plans:** run `/debate start PLAN-<NNN> "<proposal>"` before execution. Canonical on-disk layout is in `DEBATE-SCHEMA.md`.
 - **No contamination:** never hardcode personal handles or private project names in template or framework content. Docs use neutral placeholders (`Canhada-Labs`, `the maintainer`, `your-app`). `.github/CODEOWNERS` is the only live file carrying a real handle.
 - **Spawn protocol:** every named spawn must include `## AGENT PROFILE`, `## SKILL CONTENT`, and `## FILE ASSIGNMENT`. The `check_agent_spawn.py` hook blocks non-compliant spawns.
-- **Install/upgrade ownership is ONE decision, not a cascade (PLAN-167, landed `7c0828a`).** Whether the framework owns `PROTOCOL.md`, `SPEC/v1` or `.claude/.framework-version` is answered by `_ownership_verdict()` in `scripts/_framework_manifest_set.sh` — a pure function of 10 dimensions returning `"<VERDICT> <HASH_SOURCE>"`. `install.sh` and `upgrade.sh` **observe → call → execute**; they do not decide. Contract: `docs/ownership-decision-table.md`. Truth: `scripts/tests/ownership_table.tsv`. Two oracles read that same table — a unit one (`test-ownership-verdict-unit.sh`, milliseconds: catches a wrong DECISION) and an e2e one (`test-ownership-table.sh`, ~25 min of real installs: catches a wrong OBSERVATION). **The e2e ends 58 green / 4 red by design**; the 4 are named with causes: `OWN-0024`/`0027` are defects in the TEST; `OWN-0016` and `OWN-0074` are product defects (the latter is INV-4 surfacing in the recorded digest) — closing in PLAN-168. An all-green run means the table changed — stop and find out why. Adding a branch that decides ownership locally re-opens the class this replaced.
+- **Install/upgrade ownership is ONE decision, not a cascade (PLAN-167, landed `7c0828a`; PLAN-168 closed the follow-ups).** Whether the framework owns `PROTOCOL.md`, `SPEC/v1` or `.claude/.framework-version` is answered by `_ownership_verdict()` in `scripts/_framework_manifest_set.sh` — a pure function of 10 dimensions returning `"<VERDICT> <HASH_SOURCE>"`. `install.sh` and `upgrade.sh` **observe → call → execute**; they do not decide. Contract: `docs/ownership-decision-table.md`. Truth: `scripts/tests/ownership_table.tsv`. Two oracles read that same table — a unit one (`test-ownership-verdict-unit.sh`, milliseconds: catches a wrong DECISION) and an e2e one (`test-ownership-table.sh`, ~25 min of real installs: catches a wrong OBSERVATION), plus the INV-4 e2e (`test-protocol-pointer-inv4.sh`: install and upgrade render the pointer through the ONE shared generator — byte-identical, degraded bodies CURED with backup, adopter edits preserved). CI: the unit oracle + fast controls run per-PR in `smoke-install.yml`; the full e2e runs in `ownership-nightly.yml`, whose gate (`ownership-nightly-gate.sh`) compares the exact RED id set against `ownership-expected-reds.txt` and fails on ANY difference. **The e2e ends 62 green / 3 red by design** (`OWN-0024`/`0027` test defects, `OWN-0016` product — causes in ADR-190; `OWN-0074` was closed by PLAN-168 W2). An all-green run means the table changed — stop and find out why. Adding a branch that decides ownership locally re-opens the class this replaced.
 - **Fail-open on infrastructure, fail-closed on input (security matchers):** hooks never block the user session on INFRASTRUCTURE bugs — on a missing file, import failure, or timeout, a hook logs a breadcrumb and emits `{}` (a schema-compliant allow). But an INPUT-parse failure inside a security matcher is fail-CLOSED by design: content the guard cannot parse is blocked, not waved through (precedents in `check_bash_safety.py`: the `_e3` whole-command parse gate and `_check_credential_leak`; codified by PLAN-152, debate C4). **Deliberate exception (ADR-186):** the canonical-edit matcher's per-invocation wall deadline is fail-CLOSED — a timeout *there* is an incomplete verification, not infrastructure; the recovery route is the provenance-pinned unlock (`CEO_SENTINEL_UNLOCK` + `CEO_SESSION_ANCHOR_SHA` or `CEO_SENTINEL_UNLOCK_SHA256`).
 
 ## 5. Honest limitations
diff --git a/README.md b/README.md
index e04e721..68e5bac 100644
--- a/README.md
+++ b/README.md
@@ -56,7 +56,7 @@ All counts below are verifiable from a clean checkout (see *Verifying the number
 | Hooks wired in `settings.json` | **46** | distinct scripts, 48 event registrations |
 | Shared library modules | **68** | stdlib-only, under `.claude/hooks/_lib/` (excluding the package `__init__.py`) |
 | Slash commands | **27** | under `.claude/commands/` |
-| Architecture decision records | **189** | under `.claude/adr/` |
+| Architecture decision records | **190** | under `.claude/adr/` |
 | Tests | **~14,000 cases** | reported by `pytest --collect-only` across the hook, script, and conformance suites |
 
 The gap between **57 on disk** and **46 wired** is benign: several non-event modules are activated through in-process dispatch (invoked by other hooks) rather than by a direct `settings.json` event registration.
@@ -183,7 +183,7 @@ Don't take the table on faith. From a clean checkout:
 ```bash
 find .claude/skills -name SKILL.md | wc -l        # 166 skills
 ls .claude/commands/*.md | wc -l                  # 27 slash commands
-ls .claude/adr | grep -c '^ADR-'                  # 189 ADRs
+ls .claude/adr | grep -c '^ADR-'                  # 190 ADRs
 python3 -m pytest --collect-only -q | tail -1     # ~14,000 collected cases
 ```
 
diff --git a/README.pt-BR.md b/README.pt-BR.md
index 3c1c28c..ae710fc 100644
--- a/README.pt-BR.md
+++ b/README.pt-BR.md
@@ -54,7 +54,7 @@ Todas as contagens abaixo são verificáveis a partir de um checkout limpo (veja
 | Hooks ligados em `settings.json` | **46** | scripts distintos, 48 registros de evento |
 | Módulos de biblioteca compartilhada | **68** | apenas stdlib, em `.claude/hooks/_lib/` (excluindo o `__init__.py` do pacote) |
 | Slash commands | **27** | em `.claude/commands/` |
-| Architecture decision records | **189** | em `.claude/adr/` |
+| Architecture decision records | **190** | em `.claude/adr/` |
 | Testes | **~14.000 casos** | reportados por `pytest --collect-only` nas suítes de hook, script e conformidade |
 
 A diferença entre **57 em disco** e **46 ligados** é benigna: vários módulos que não respondem a eventos são ativados via dispatch in-process (invocados por outros hooks), e não por um registro de evento direto em `settings.json`.
@@ -163,7 +163,7 @@ Não acredite na tabela por fé. A partir de um checkout limpo:
 ```bash
 find .claude/skills -name SKILL.md | wc -l        # 166 skills
 ls .claude/commands/*.md | wc -l                  # 27 slash commands
-ls .claude/adr | grep -c '^ADR-'                  # 189 ADRs
+ls .claude/adr | grep -c '^ADR-'                  # 190 ADRs
 python3 -m pytest --collect-only -q | tail -1     # ~14.000 casos coletados
 ```
 
diff --git a/docs/ARCHITECTURE.md b/docs/ARCHITECTURE.md
index d59fb70..6d8bec2 100644
--- a/docs/ARCHITECTURE.md
+++ b/docs/ARCHITECTURE.md
@@ -53,7 +53,7 @@ ceo-orchestration/
     │   ├── core/                   # 42 universal backend skills
     │   ├── frontend/               # 8 universal frontend skills
     │   └── domains/                # 116 skills across 33 domain profiles
-    ├── adr/                        # 189 architecture decision records
+    ├── adr/                        # 190 architecture decision records
     └── plans/                      # plan schemas + per-plan working files
 ```
 
@@ -68,7 +68,7 @@ faith — run the commands:
 | Hook registrations | 46 wired into `settings.json`| (parse the `hooks` block of `.claude/settings.json`)      |
 | `_lib` modules     | 68 top-level (140 recursive) | `ls .claude/hooks/_lib/*.py \| grep -v __init__ \| wc -l` |
 | Slash commands     | 27                           | `ls .claude/commands/*.md \| wc -l`                       |
-| ADRs               | 189                          | `ls .claude/adr/ADR-*.md \| wc -l`                        |
+| ADRs               | 190                          | `ls .claude/adr/ADR-*.md \| wc -l`                        |
 | SPEC/v1 files      | 32 (28 `*.schema.md`)        | `ls SPEC/v1/*.md \| wc -l`                                |
 | Test files         | ~730                         | `git ls-files '*test_*.py' '*_test.py' \| wc -l`          |
 | Collected cases    | ~14k parametrized cases      | `make test-collect` (pytest `--collect-only`)             |
@@ -234,7 +234,7 @@ this repository happens to implement it today*. An install pins a SPEC version;
 internal refactors that keep the schemas stable do not break adopters.
 
 Decisions that shape these contracts are recorded as Architecture Decision
-Records in `.claude/adr/` (189 to date), with a documented lifecycle
+Records in `.claude/adr/` (190 to date), with a documented lifecycle
 (PROPOSED → ACCEPTED, plus SUPERSEDED / RETRACTED).[^adr]
 
 The repository also includes a TLA+ specification of the core state machine
diff --git a/docs/CTO-GUIDE.md b/docs/CTO-GUIDE.md
index b0e59bc..ee6ea7d 100644
--- a/docs/CTO-GUIDE.md
+++ b/docs/CTO-GUIDE.md
@@ -41,9 +41,9 @@ documentation bug.
 |---|---|---|
 | Python tests collected | ~14,000 | `make test-collect` (or `python3 -m pytest --collect-only -q \| tail -1` — pytest.ini pins the testpath roots) |
 | Test files | ~730 | `git ls-files '*test_*.py' '*_test.py' \| wc -l` |
-| ADRs shipped | 189 | `ls .claude/adr/ADR-*.md \| wc -l` |
+| ADRs shipped | 190 | `ls .claude/adr/ADR-*.md \| wc -l` |
 | SPEC/v1 files | 32 (28 `*.schema.md`) | `ls SPEC/v1/*.md \| wc -l` |
-| Workflows | 21 | `ls .github/workflows/*.yml \| wc -l` |
+| Workflows | 22 | `ls .github/workflows/*.yml \| wc -l` |
 | GitHub Actions SHA-pinned refs | every `uses:` pinned | `grep -rEc 'uses: [^#]+@(v[0-9]+\|main\|master\|latest)\s*$' .github/workflows/*` — must be 0 everywhere |
 | Skills | 166 (42 core + 8 frontend + 116 domain) | `find .claude/skills -name SKILL.md \| wc -l` |
 | Hooks | 57 .py on disk; 46 wired into `settings.json` (48 event registrations) | `ls .claude/hooks/*.py \| wc -l` |
@@ -109,7 +109,7 @@ grep -rE 'urllib|requests|httpx|socket\.' .claude/hooks/check_*.py
 ls .claude/hooks/check_*.py .claude/hooks/audit_log.py
 
 # Every ADR title
-grep -h '^# ADR-' .claude/adr/ADR-*.md | sort             # 189 ADRs on disk
+grep -h '^# ADR-' .claude/adr/ADR-*.md | sort             # 190 ADRs on disk
 
 # SPEC/v1 published contract
 ls SPEC/v1/*.schema.md                                    # 28 schema files
diff --git a/docs/FAQ.md b/docs/FAQ.md
index ad3ad62..e7ed310 100644
--- a/docs/FAQ.md
+++ b/docs/FAQ.md
@@ -105,7 +105,7 @@ Don't take the README table on faith. From a clean checkout:
 ```bash
 find .claude/skills -name SKILL.md | wc -l        # 166 skills (42 core + 8 frontend + 116 domain)
 ls .claude/commands/*.md | wc -l                  # 27 slash commands
-ls .claude/adr | grep -c '^ADR-'                  # 189 ADRs
+ls .claude/adr | grep -c '^ADR-'                  # 190 ADRs
 python3 -m pytest --collect-only -q | tail -1     # ~14,000 collected cases
 ```
 
diff --git a/docs/README.md b/docs/README.md
index 4a50bbb..619c44e 100644
--- a/docs/README.md
+++ b/docs/README.md
@@ -78,7 +78,7 @@ full set of commands; here is the summary you can spot-check in a minute.
 | Hook scripts on disk | **57** Python scripts | count `*.py` in `.claude/hooks/` |
 | Hooks registered | **46** distinct scripts (48 event registrations) | inspect `.claude/settings.json` |
 | Slash commands | **27** | count `*.md` in `.claude/commands/` |
-| Architecture decision records | **189** | count `ADR-*.md` in `.claude/adr/` |
+| Architecture decision records | **190** | count `ADR-*.md` in `.claude/adr/` |
 | Shared library modules | **68** stdlib-only (top-level `_lib/`) | count `*.py` in `.claude/hooks/_lib/` |
 | Tests | **~730 test files**; `make test-collect` (pytest `--collect-only`) reports **~14,000** collected cases | `make test-collect` |
 
diff --git a/docs/ownership-decision-table.md b/docs/ownership-decision-table.md
index 772137d..dcaf685 100644
--- a/docs/ownership-decision-table.md
+++ b/docs/ownership-decision-table.md
@@ -116,13 +116,36 @@ after earlier surfaces have already been modified.
 |---|---|
 | `pristine` | byte-identical to what **this** source would deliver |
 | `legacy_pristine` | matches a `SPEC/v1` fingerprint the framework shipped at v1.2.0 or earlier |
-| `edited` | neither |
+| `degraded` | (protocol only, PLAN-168 W2) byte-exact reconstruction of the `{{PROTOCOL_SOURCE}}`-literal pointer template a pre-PLAN-168 `upgrade.sh` wrote — the framework's OWN output, never adopter content |
+| `edited` | none of the above |
 
 `legacy_pristine` exists because v1.2-and-earlier installs never enumerated
 `SPEC/v1`, so no record can distinguish a framework-installed tree from an
 adopter-authored one; the ambiguity is resolved by content against three
 pinned fingerprints.
 
+`degraded` is the same doctrine applied to the pointer (the r20 precedent):
+the broken upgrade left `{{PROTOCOL_SOURCE}}` literal while embedding the
+invocation's `TARGET`/`PROFILE`/`STACK`, so recognition is by **template
+reconstruction** — extract the invocation values from the file's own upgrade
+line, re-render the one shipped template (identical across v1.0.1→HEAD,
+verified by extraction), and require byte equality. Substring matching is
+forbidden (an adopter file that legitimately *contains* the token would be
+destroyed); a static whole-body hash is useless (each adopter's degraded
+body embeds different values). Any parse failure or deviation ⇒ `edited` ⇒
+preserved. Recognizer: `_protocol_pointer_is_degraded` in
+`scripts/_framework_manifest_set.sh`.
+
+**Hash-name aliasing (post-INV-4).** Once install and upgrade render through
+the one generator, the canonical pointer digest and the prior record are the
+SAME bytes on continuity rows — `HASH_PRIOR_RECORD` and
+`HASH_CANONICAL_POINTER` collapse into one claim. The e2e harness therefore
+treats the two names as equivalent **only when the candidate digests are
+equal and the record matches them** (`_derive_hash_source`, 5th argument);
+when the digests genuinely differ, the probe order decides exactly as
+before. Choosing by probe order in the aliased case would manufacture a
+distinction the observation cannot make.
+
 ### 2.5 `source_has` — does `$SOURCE_DIR` carry this surface?
 
 `yes` · `no`. The reachable `no` case is the documented `--pin` downgrade to
@@ -258,6 +281,7 @@ indistinguishable from an oversight, which is how a defect class hides.
 | **R-02** | `operation ∈ {install_fresh, install_rerun}` ⇒ `skip_requested=none` | `--skip` is an `upgrade.sh` flag. `install.sh` has no equivalent (verified: zero occurrences). |
 | **R-03** | `surface=protocol` ⇒ `source_has=yes` | The pointer is generated from a heredoc, never copied. There is no source file whose absence could be observed. |
 | **R-04** | `live_content=legacy_pristine` ⇒ `surface=spec` | The pristine fingerprints are a `SPEC/v1`-tree construct. No equivalent exists, or is needed, for a one-line marker or a generated pointer. |
+| **R-04b** | `live_content=degraded` ⇒ `surface=protocol` (PLAN-168 W2) | The degraded template is a pointer construct: only the generated `PROTOCOL.md` ever carried the `{{PROTOCOL_SOURCE}}`-literal body. `SPEC/v1` legacy recognition already has `legacy_pristine`; the marker is a one-line version string with no template to degrade. |
 | **R-05** | `live_type=absent` ⇒ `live_content` undefined | Nothing to hash. |
 | **R-06** | `skip_requested=descendant` ⇒ `surface=spec` | Only `SPEC/v1` is a tree. A path *under* a single file cannot exist. |
 | **R-07** | `live_type=dir_empty` ⇒ `surface=spec` | For the single-file surfaces, an empty directory and a non-empty one behave identically (both yield no record and both are refused as non-regular). The distinction is only load-bearing where per-file records are emitted. |
diff --git a/npm/README.md b/npm/README.md
index a19a95f..8617915 100644
--- a/npm/README.md
+++ b/npm/README.md
@@ -56,7 +56,7 @@ All counts below are verifiable from a clean checkout (see *Verifying the number
 | Hooks wired in `settings.json` | **46** | distinct scripts, 48 event registrations |
 | Shared library modules | **68** | stdlib-only, under `.claude/hooks/_lib/` (excluding the package `__init__.py`) |
 | Slash commands | **27** | under `.claude/commands/` |
-| Architecture decision records | **189** | under `.claude/adr/` |
+| Architecture decision records | **190** | under `.claude/adr/` |
 | Tests | **~14,000 cases** | reported by `pytest --collect-only` across the hook, script, and conformance suites |
 
 The gap between **57 hook scripts** on disk and **46 wired** is benign: several non-event modules are activated through in-process dispatch (invoked by other hooks) rather than by a direct `settings.json` event registration.
@@ -119,7 +119,7 @@ Don't take the table on faith. From a clean checkout:
 ```bash
 find .claude/skills -name SKILL.md | wc -l        # 166 skills
 ls .claude/commands/*.md | wc -l                  # 27 slash commands
-ls .claude/adr | grep -c '^ADR-'                  # 189 ADRs
+ls .claude/adr | grep -c '^ADR-'                  # 190 ADRs
 python3 -m pytest --collect-only -q | tail -1     # ~14,000 collected cases
 ```
 

exec
/bin/zsh -lc "sed -n '1,240p' scripts/tests/test-ownership-nightly-gate.sh" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
#!/usr/bin/env bash
# =============================================================================
# PLAN-168 W1 — positive control for ownership-nightly-gate.sh.
#
# The gate is the instrument that watches the ownership e2e in CI; this test
# watches the GATE. Every failure mode the gate claims to catch is planted
# here with a fake harness, and the test demands the gate actually goes red —
# green-without-control proves nothing (PLAN-167: 8 instrument defects).
#
# Scenarios:
#   S1  matching set, rc=1, HARNESS-ERR=0            => gate PASSES
#   S2  set GREW (one extra red)                     => gate FAILS
#   S3  set SHRANK (all green, rc=0)                 => gate FAILS
#   S4  harness rc=2 (infra error)                   => gate FAILS
#   S5  summary line missing (truncated output)      => gate FAILS
#   S6  HARNESS-ERR=1 in summary                     => gate FAILS
#   S7  rc=0 while expected set non-empty            => gate FAILS
#   S8  set SWAPPED (same size, different ids)       => gate FAILS
#   S9  empty expected set + all green, rc=0         => gate PASSES
#   S10 expected id degraded to TIMEOUT (same ids)   => gate FAILS
#   S11 expected id degraded to ESCAPE  (same ids)   => gate FAILS
#   S12 green cell degraded to AMBIG                 => gate FAILS
#
# Exit: 0 all scenarios behave. 1 at least one does not. 2 harness error.
# =============================================================================
set -uo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
GATE="$SCRIPT_DIR/ownership-nightly-gate.sh"
[[ -f "$GATE" ]] || { echo "ERROR: gate not found: $GATE" >&2; exit 2; }

WORK="$( mktemp -d "${TMPDIR:-/tmp}/own-gate-test.XXXXXX" )" || exit 2
trap 'rm -rf "$WORK" 2>/dev/null || true' EXIT

# --- fake harness ------------------------------------------------------------
# Emits a canned map on stdout and exits with a canned rc. The gate consumes
# it via OWNERSHIP_GATE_HARNESS exactly as it would the real harness.
mk_fake() { # $1=out-file $2=rc-file
  cat > "$WORK/fake-harness.sh" <<EOF
#!/usr/bin/env bash
cat "$1"
exit "\$(cat "$2")"
EOF
  chmod +x "$WORK/fake-harness.sh"
}

map_line() { # $1=id $2=status
  printf '%-10s %-7s exp=%-16s/%-22s got=%-16s/%-22s rc=%-3s %s\n' \
    "$1" "$2" "V" "H" "V" "H" "0" "test"
}

write_map() { # $1=file, then "id:status" pairs; appends summary from counts
  local f="$1"; shift
  local green=0 red=0 err="${SUMMARY_ERR:-0}"
  : > "$f"
  local pair id st
  for pair in "$@"; do
    id="${pair%%:*}"; st="${pair##*:}"
    map_line "$id" "$st" >> "$f"
    case "$st" in GREEN) green=$((green+1)) ;; *) red=$((red+1)) ;; esac
  done
  if [[ "${SUMMARY_OMIT:-0}" -ne 1 ]]; then
    printf '\nGREEN=%d  RED=%d  AMBIG=0  HARNESS-ERR=%d\n' "$green" "$red" "$err" >> "$f"
  fi
}

expected_4() {
  printf 'OWN-0016\nOWN-0024\nOWN-0027\nOWN-0074\n' > "$WORK/exp.txt"
}

run_gate() { # $1=expected-rc  $2=label
  local want="$1" label="$2" got=0
  OWNERSHIP_GATE_HARNESS="$WORK/fake-harness.sh" \
  OWNERSHIP_GATE_EXPECTED="$WORK/exp.txt" \
    bash "$GATE" > "$WORK/gate-out.txt" 2> "$WORK/gate-err.txt" || got=$?
  if [[ "$got" -eq "$want" ]]; then
    echo "PASS  $label (gate rc=$got)"
    return 0
  fi
  echo "FAIL  $label — gate rc=$got, expected $want"
  sed -n '1,15p' "$WORK/gate-out.txt" | sed 's/^/      out| /'
  sed -n '1,15p' "$WORK/gate-err.txt" | sed 's/^/      err| /'
  return 1
}

FAILURES=0

# S1 — matching set, honest rc=1 => PASS
expected_4
write_map "$WORK/map.txt" OWN-0001:GREEN OWN-0016:RED OWN-0024:RED OWN-0027:RED OWN-0074:RED
echo 1 > "$WORK/rc.txt"; mk_fake "$WORK/map.txt" "$WORK/rc.txt"
run_gate 0 "S1 matching set + rc=1" || FAILURES=$((FAILURES+1))

# S2 — set grew => FAIL
write_map "$WORK/map.txt" OWN-0001:RED OWN-0016:RED OWN-0024:RED OWN-0027:RED OWN-0074:RED
echo 1 > "$WORK/rc.txt"; mk_fake "$WORK/map.txt" "$WORK/rc.txt"
run_gate 1 "S2 set grew" || FAILURES=$((FAILURES+1))

# S3 — set shrank to zero (all green, honest rc=0) => FAIL (all-green = STOP)
write_map "$WORK/map.txt" OWN-0001:GREEN OWN-0016:GREEN OWN-0024:GREEN OWN-0027:GREEN OWN-0074:GREEN
echo 0 > "$WORK/rc.txt"; mk_fake "$WORK/map.txt" "$WORK/rc.txt"
run_gate 1 "S3 set shrank (all green)" || FAILURES=$((FAILURES+1))

# S4 — harness infra error rc=2 => FAIL
write_map "$WORK/map.txt" OWN-0016:RED
echo 2 > "$WORK/rc.txt"; mk_fake "$WORK/map.txt" "$WORK/rc.txt"
run_gate 1 "S4 harness rc=2" || FAILURES=$((FAILURES+1))

# S5 — summary line missing (truncated run) => FAIL even with matching ids
# (explicit set/reset: VAR=x prefixed to a FUNCTION call has version-divergent
# persistence semantics in bash — never rely on it.)
SUMMARY_OMIT=1
write_map "$WORK/map.txt" OWN-0016:RED OWN-0024:RED OWN-0027:RED OWN-0074:RED
SUMMARY_OMIT=0
echo 1 > "$WORK/rc.txt"; mk_fake "$WORK/map.txt" "$WORK/rc.txt"
run_gate 1 "S5 summary missing" || FAILURES=$((FAILURES+1))

# S6 — HARNESS-ERR=1 => FAIL even with matching ids
SUMMARY_ERR=1
write_map "$WORK/map.txt" OWN-0016:RED OWN-0024:RED OWN-0027:RED OWN-0074:RED
SUMMARY_ERR=0
echo 1 > "$WORK/rc.txt"; mk_fake "$WORK/map.txt" "$WORK/rc.txt"
run_gate 1 "S6 HARNESS-ERR=1" || FAILURES=$((FAILURES+1))

# S7 — rc=0 while expected set non-empty (rc/set incoherence) => FAIL
write_map "$WORK/map.txt" OWN-0016:RED OWN-0024:RED OWN-0027:RED OWN-0074:RED
echo 0 > "$WORK/rc.txt"; mk_fake "$WORK/map.txt" "$WORK/rc.txt"
run_gate 1 "S7 rc=0 with non-empty expected set" || FAILURES=$((FAILURES+1))

# S8 — same size, different ids => FAIL
write_map "$WORK/map.txt" OWN-0016:RED OWN-0024:RED OWN-0027:RED OWN-0099:RED OWN-0074:GREEN
echo 1 > "$WORK/rc.txt"; mk_fake "$WORK/map.txt" "$WORK/rc.txt"
run_gate 1 "S8 set swapped" || FAILURES=$((FAILURES+1))

# S9 — empty expected set + all green + rc=0 => PASS
: > "$WORK/exp.txt"
write_map "$WORK/map.txt" OWN-0001:GREEN OWN-0002:GREEN
echo 0 > "$WORK/rc.txt"; mk_fake "$WORK/map.txt" "$WORK/rc.txt"
run_gate 0 "S9 empty expected set, all green" || FAILURES=$((FAILURES+1))

# S10-S12 — an EXPECTED-red id degrades to TIMEOUT / ESCAPE / AMBIG: the id
# set is UNCHANGED, so an ids-only comparison would pass a more severe
# regression as "same set" (codex rail r2 P1). The gate must go red on the
# STATUS, not just the set.
expected_4
write_map "$WORK/map.txt" OWN-0016:TIMEOUT OWN-0024:RED OWN-0027:RED OWN-0074:RED
echo 1 > "$WORK/rc.txt"; mk_fake "$WORK/map.txt" "$WORK/rc.txt"
run_gate 1 "S10 expected id degraded to TIMEOUT" || FAILURES=$((FAILURES+1))

write_map "$WORK/map.txt" OWN-0016:ESCAPE OWN-0024:RED OWN-0027:RED OWN-0074:RED
echo 1 > "$WORK/rc.txt"; mk_fake "$WORK/map.txt" "$WORK/rc.txt"
run_gate 1 "S11 expected id degraded to ESCAPE" || FAILURES=$((FAILURES+1))

write_map "$WORK/map.txt" OWN-0001:AMBIG OWN-0016:RED OWN-0024:RED OWN-0027:RED OWN-0074:RED
echo 1 > "$WORK/rc.txt"; mk_fake "$WORK/map.txt" "$WORK/rc.txt"
run_gate 1 "S12 green cell degraded to AMBIG" || FAILURES=$((FAILURES+1))

echo ""
if [[ "$FAILURES" -gt 0 ]]; then
  echo "ownership-nightly-gate positive control: $FAILURES scenario(s) FAILED"
  exit 1
fi
echo "ownership-nightly-gate positive control: 12/12 scenarios behave"
exit 0

exec
/bin/zsh -lc "sed -n '1,240p' scripts/tests/test-protocol-pointer-render.sh" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
#!/usr/bin/env bash
# =============================================================================
# PLAN-168 W2 — unit control for the shared protocol-pointer generator
# (_render_protocol_pointer / _render_protocol_pointer_degraded /
# _protocol_pointer_is_degraded in scripts/_framework_manifest_set.sh).
#
# Scenarios:
#   R1  healthy render == REAL install.sh output, byte for byte (the parity
#       that IS INV-4's fix — normalized inputs, as the plan requires)
#   R2  degraded render | substitute-token == healthy render (one template)
#   R3  recognizer: exact degraded file => rc=0 (curable)
#   R4  recognizer: healthy (substituted) file => rc=1 (never curable)
#   R5  recognizer: degraded file + 1-char adopter edit => rc=1 (preserved)
#   R6  recognizer: adopter file that merely CONTAINS the token => rc=1
#       (the codex r1 P1 substring-destruction case)
#   R7  recognizer: unparseable upgrade line (space in target) => rc=1
#   R8  inside-target checkout => relative render (no token, no source path)
#
# Exit: 0 all pass · 1 failure · 2 harness error.
# =============================================================================
set -uo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# shellcheck source=/dev/null
. "$REPO_ROOT/scripts/_framework_manifest_set.sh" 2>/dev/null || {
  echo "ERROR: cannot source _framework_manifest_set.sh" >&2; exit 2; }
for fn in _render_protocol_pointer _render_protocol_pointer_degraded _protocol_pointer_is_degraded; do
  command -v "$fn" >/dev/null 2>&1 || { echo "ERROR: $fn missing" >&2; exit 2; }
done

WORK="$( mktemp -d "${TMPDIR:-/tmp}/ptr-render.XXXXXX" )" || exit 2
trap 'chmod -R u+w "$WORK" 2>/dev/null; rm -rf "$WORK" 2>/dev/null' EXIT

FAILURES=0
say() { echo "$1"; }
fail() { echo "FAIL  $1"; FAILURES=$((FAILURES+1)); }

# --- R1: byte parity with a REAL install --------------------------------------
# Normalized target (physical path, no trailing/double slashes) — install.sh
# normalizes its TARGET, and the plan requires normalized inputs for exactly
# this reason.
U="$WORK/t"; mkdir -p "$U"
U="$( cd "$U" && pwd -P )"
( cd "$U" && git init -q )
if CEO_INSTALL_SKIP_SELF_SHA=1 CEO_RAG_INSTALL_PROMPT=0 \
     bash "$REPO_ROOT/scripts/install.sh" "$U" --profile core --stack generic \
     > "$WORK/install.log" 2>&1; then
  _render_protocol_pointer "$REPO_ROOT" "$U" core generic "$REPO_ROOT" > "$WORK/render.txt"
  if diff -u "$U/PROTOCOL.md" "$WORK/render.txt" > "$WORK/r1.diff" 2>&1; then
    say "PASS  R1 healthy render == real install output"
  else
    fail "R1 parity with real install"; sed -n '1,10p' "$WORK/r1.diff"
  fi
else
  fail "R1 install.sh itself failed (see $WORK/install.log)"; sed -n '1,5p' "$WORK/install.log"
fi

# --- R2: one template — degraded | substitution == healthy --------------------
_render_protocol_pointer_degraded "$U" core generic \
  | sed "s|{{PROTOCOL_SOURCE}}|$( printf '%s' "$REPO_ROOT" | sed 's/[|&\\]/\\&/g' )|g" \
  > "$WORK/deg-subst.txt"
if diff -q "$WORK/deg-subst.txt" "$WORK/render.txt" >/dev/null 2>&1; then
  say "PASS  R2 degraded+substitute == healthy (single template)"
else
  fail "R2 template split"; diff "$WORK/deg-subst.txt" "$WORK/render.txt" | head -5
fi

# --- R3: recognizer accepts an exact degraded body ----------------------------
_render_protocol_pointer_degraded "$U" core generic > "$WORK/degraded.md"
if _protocol_pointer_is_degraded "$WORK/degraded.md"; then
  say "PASS  R3 exact degraded body recognized (curable)"
else
  fail "R3 exact degraded body NOT recognized"
fi

# --- R4: healthy file is never "degraded" -------------------------------------
if _protocol_pointer_is_degraded "$WORK/render.txt"; then
  fail "R4 healthy file misclassified as degraded"
else
  say "PASS  R4 healthy file not curable (preserved)"
fi

# --- R5: one adopter edit anywhere => preserved -------------------------------
sed 's/git pull/git fetch/' "$WORK/degraded.md" > "$WORK/degraded-edited.md"
if _protocol_pointer_is_degraded "$WORK/degraded-edited.md"; then
  fail "R5 edited degraded body still classified curable (DATA LOSS route)"
else
  say "PASS  R5 edited degraded body preserved"
fi

# --- R6: adopter file that merely CONTAINS the token --------------------------
printf '%s\n' "# My protocol notes" "" \
  "We keep the marker {{PROTOCOL_SOURCE}} here on purpose." \
  "  {{PROTOCOL_SOURCE}}/scripts/upgrade.sh $U --profile core --stack generic" \
  > "$WORK/adopter.md"
if _protocol_pointer_is_degraded "$WORK/adopter.md"; then
  fail "R6 adopter file containing the token misclassified (substring trap)"
else
  say "PASS  R6 token-containing adopter file preserved"
fi

# --- R7: unparseable upgrade line (space in target) => preserved --------------
_render_protocol_pointer_degraded "/tmp/has space" core generic > "$WORK/spacey.md"
if _protocol_pointer_is_degraded "$WORK/spacey.md"; then
  fail "R7 ambiguous (spaced) target treated as parseable"
else
  say "PASS  R7 ambiguous target preserved (documented residual)"
fi

# --- R8: inside-target checkout renders the relative form ---------------------
IN="$WORK/inside"; mkdir -p "$IN/vendor/ceo"
IN="$( cd "$IN" && pwd -P )"
_render_protocol_pointer "$IN/vendor/ceo" "$IN" core generic "$IN/vendor/ceo" > "$WORK/rel.txt"
if grep -q '\./vendor/ceo/PROTOCOL.md' "$WORK/rel.txt" \
   && ! grep -q '{{PROTOCOL_SOURCE}}' "$WORK/rel.txt" \
   && ! grep -F -q "$IN/vendor" "$WORK/rel.txt"; then
  say "PASS  R8 inside-target => relative render"
else
  fail "R8 inside-target render wrong"; sed -n '1,8p' "$WORK/rel.txt"
fi

echo ""
if [[ "$FAILURES" -gt 0 ]]; then
  echo "protocol-pointer render control: $FAILURES FAILED"
  exit 1
fi
echo "protocol-pointer render control: 8/8 pass"
exit 0

exec
/bin/zsh -lc "sed -n '1,240p' scripts/tests/test-protocol-pointer-inv4.sh" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
#!/usr/bin/env bash
# =============================================================================
# PLAN-168 W2 (AC-6/AC-6b) — INV-4 as an executable assertion.
#
# INV-4: install and upgrade produce the SAME root PROTOCOL.md pointer.
# Byte identity alone is VACUOUS (codex rail r1 P1: a shared generator based
# on the broken template would make both sides identical AND wrong), so every
# leg also asserts CONTENT: the {{PROTOCOL_SOURCE}} token is ABSENT and the
# resolved source path is PRESENT.
#
# Legs (all with NORMALIZED inputs — pwd -P, fixed profile/stack):
#   L1  install -> upgrade         : pointer byte-identical, content sound
#   L2  upgrade -> upgrade         : idempotent, byte-identical
#   L3  degraded body -> upgrade   : CURED (refreshed with backup, sound)
#   L4  adopter-edited -> upgrade  : PRESERVED byte-identical (S238 guard —
#                                    the cure must never widen into clobber)
#
# Exit: 0 all legs pass · 1 failure · 2 harness error.
# =============================================================================
set -uo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"

# shellcheck source=/dev/null
. "$REPO_ROOT/scripts/_framework_manifest_set.sh" 2>/dev/null || {
  echo "ERROR: cannot source _framework_manifest_set.sh" >&2; exit 2; }
command -v _render_protocol_pointer_degraded >/dev/null 2>&1 || {
  echo "ERROR: generator missing (W2 not in tree)" >&2; exit 2; }

WORK="$( mktemp -d "${TMPDIR:-/tmp}/inv4.XXXXXX" )" || exit 2
WORK="$( cd "$WORK" && pwd -P )"
trap 'chmod -R u+w "$WORK" 2>/dev/null; rm -rf "$WORK" 2>/dev/null' EXIT

PROFILE=core
STACK=generic
FAILURES=0
fail() { echo "FAIL  $1"; FAILURES=$((FAILURES+1)); }

run_install() { # $1=target
  CEO_INSTALL_SKIP_SELF_SHA=1 CEO_RAG_INSTALL_PROMPT=0 \
    bash "$REPO_ROOT/scripts/install.sh" "$1" --profile "$PROFILE" --stack "$STACK" \
    > "$WORK/install.log" 2>&1
}
run_upgrade() { # $1=target $2=log
  CEO_INSTALL_SKIP_SELF_SHA=1 \
    bash "$REPO_ROOT/scripts/upgrade.sh" "$1" --profile "$PROFILE" --stack "$STACK" \
    > "$2" 2>&1
}
assert_sound() { # $1=file $2=label — token absent, resolved source present
  if grep -F -q '{{PROTOCOL_SOURCE}}' "$1"; then
    fail "$2: token {{PROTOCOL_SOURCE}} still present (degraded output)"
    return 1
  fi
  if ! grep -F -q "$REPO_ROOT/PROTOCOL.md" "$1"; then
    fail "$2: resolved source path missing from pointer"
    return 1
  fi
  return 0
}

T="$WORK/t"; mkdir -p "$T"; ( cd "$T" && git init -q )
T="$( cd "$T" && pwd -P )"

# --- L1: install -> upgrade ---------------------------------------------------
if ! run_install "$T"; then
  echo "ERROR: install failed"; sed -n '1,8p' "$WORK/install.log"; exit 2
fi
cp "$T/PROTOCOL.md" "$WORK/after-install.md"
assert_sound "$WORK/after-install.md" "L1 post-install" || true
if ! run_upgrade "$T" "$WORK/upgrade1.log"; then
  echo "ERROR: upgrade failed"; sed -n '1,12p' "$WORK/upgrade1.log"; exit 2
fi
if cmp -s "$WORK/after-install.md" "$T/PROTOCOL.md"; then
  assert_sound "$T/PROTOCOL.md" "L1 post-upgrade" && echo "PASS  L1 install->upgrade byte-identical + sound"
else
  fail "L1 pointer changed across install->upgrade (INV-4 broken)"
  diff "$WORK/after-install.md" "$T/PROTOCOL.md" | head -8
fi

# --- L2: upgrade -> upgrade (idempotence) ------------------------------------
cp "$T/PROTOCOL.md" "$WORK/after-up1.md"
if ! run_upgrade "$T" "$WORK/upgrade2.log"; then
  echo "ERROR: second upgrade failed"; sed -n '1,12p' "$WORK/upgrade2.log"; exit 2
fi
if cmp -s "$WORK/after-up1.md" "$T/PROTOCOL.md"; then
  echo "PASS  L2 upgrade->upgrade idempotent"
else
  fail "L2 pointer churned across repeat upgrade"
  diff "$WORK/after-up1.md" "$T/PROTOCOL.md" | head -8
fi

# --- L3: degraded body is CURED ----------------------------------------------
_render_protocol_pointer_degraded "$T" "$PROFILE" "$STACK" > "$T/PROTOCOL.md"
if ! run_upgrade "$T" "$WORK/upgrade3.log"; then
  echo "ERROR: cure upgrade failed"; sed -n '1,12p' "$WORK/upgrade3.log"; exit 2
fi
if grep -F -q '{{PROTOCOL_SOURCE}}' "$T/PROTOCOL.md"; then
  fail "L3 degraded pointer NOT cured (token survived the upgrade — immortal defect)"
  sed -n '1,6p' "$T/PROTOCOL.md"
else
  assert_sound "$T/PROTOCOL.md" "L3 post-cure" || true
  if grep -q "CURED: PROTOCOL.md" "$WORK/upgrade3.log"; then
    echo "PASS  L3 degraded body cured (REFRESH route taken)"
  else
    fail "L3 pointer sound but the CURED route was not what ran (check upgrade3.log)"
    grep -n "PROTOCOL.md" "$WORK/upgrade3.log" | head -5
  fi
  if ls "$T"/.claude/backup*/PROTOCOL.md >/dev/null 2>&1 \
     || grep -q "BACKED UP: PROTOCOL.md" "$WORK/upgrade3.log"; then
    echo "PASS  L3b cure kept a backup of the degraded original"
  else
    fail "L3b no backup evidence for the cured pointer"
  fi
fi

# --- L4: adopter-customized pointer is PRESERVED (S238 guard) ----------------
printf '\nAdopter note: we run upgrades on Fridays.\n' >> "$T/PROTOCOL.md"
cp "$T/PROTOCOL.md" "$WORK/customized.md"
if ! run_upgrade "$T" "$WORK/upgrade4.log"; then
  echo "ERROR: preserve-leg upgrade failed"; sed -n '1,12p' "$WORK/upgrade4.log"; exit 2
fi
if cmp -s "$WORK/customized.md" "$T/PROTOCOL.md"; then
  echo "PASS  L4 adopter-customized pointer preserved byte-identical"
else
  fail "L4 adopter-customized pointer was MODIFIED (the cure widened into clobber — S238)"
  diff "$WORK/customized.md" "$T/PROTOCOL.md" | head -8
fi

echo ""
if [[ "$FAILURES" -gt 0 ]]; then
  echo "INV-4 assertion: $FAILURES leg(s) FAILED"
  exit 1
fi
echo "INV-4 assertion: 4/4 legs pass (byte identity + content soundness + cure + preserve)"
exit 0

exec
/bin/zsh -lc "sed -n '1,240p' .github/workflows/ownership-nightly.yml" in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
name: Ownership Nightly

# PLAN-168 W1 (AC-4/AC-5, Owner decision D4): the ownership e2e runs the FULL
# truth table — 62 real install/upgrade cells, ~25 min locally, 2-3x that on a
# 2-core runner — so it cannot live inside smoke-install's 25-min job (that
# budget was already raised 4x: 5→8→20→25). And `schedule:` events IGNORE
# `paths:` filters, so the nightly split is a separate WORKFLOW, not a filter
# entry (debate r1 devops must-fix 1). The fast per-PR half (the unit oracle)
# stays in smoke-install.yml.
#
# The gate compares the observed non-GREEN set against
# scripts/tests/ownership-expected-reds.txt and fails on ANY difference —
# including shrinkage. 4 deliberate reds are part of the contract
# (CLAUDE.md §4): an all-green run means the table changed — STOP and find
# out why, never celebrate. NEVER run the harness with --map here: --map is a
# reporting mode that exits 0 over failures (a dead gate by construction).

on:
  schedule:
    # Off-peak UTC, off-minute deliberately (fleet etiquette — avoid :00/:30).
    - cron: "43 6 * * *"
  # Manual runs for harness/table PRs that want the full e2e before merge.
  workflow_dispatch: {}

concurrency:
  group: ownership-nightly
  cancel-in-progress: true

jobs:
  ownership-e2e:
    # PLAN-012 Phase 2 CEO_SOTA_DISABLE parity (same switch as smoke-install).
    if: vars.CEO_SOTA_DISABLE != '1'
    runs-on: ubuntu-latest
    # ~25 min local (Darwin arm64, 16 cores, 2026-08-07); ubuntu-latest is the
    # usual 2-3x slower => 50-75 min expected. Same anti-flake sizing rule as
    # the smoke-install budget notes: leave headroom, re-tighten on a real p95.
    timeout-minutes: 90
    permissions:
      contents: read
    steps:
      - name: Checkout
        # SHA-pinned (same pin as smoke-install.yml): actions/checkout@v6.0.2
        uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd
        with:
          fetch-depth: 1

      # `fetch-depth: 1` produces a checkout with NO tags, and the
      # legacy_pristine* fixtures build from a REAL shipped tree. The tag is
      # READ FROM THE HARNESS (--print-legacy-tag) so this workflow never
      # becomes a second copy of that truth (same --print-pin shape as the
      # parity e2e in smoke-install.yml).
      - name: Fetch the legacy_pristine tag
        run: |
          set -euo pipefail
          TAG="$(bash scripts/tests/test-ownership-table.sh --print-legacy-tag)"
          echo "legacy pristine tag: $TAG"
          git fetch --no-tags --depth 1 origin "+refs/tags/$TAG:refs/tags/$TAG"
          git rev-parse --verify "refs/tags/$TAG^{commit}"

      - name: Install jq (install.sh settings merge dependency)
        run: |
          set -euo pipefail
          if ! command -v jq >/dev/null 2>&1; then
            sudo apt-get update -qq
            sudo apt-get install -y -qq jq
          fi
          jq --version

      # Fast preflight: a broken DECISION should fail in milliseconds here,
      # not 40 minutes into the observation run.
      - name: Ownership verdict unit oracle (preflight)
        run: |
          set -euo pipefail
          bash scripts/tests/test-ownership-verdict-unit.sh

      # PLAN-168 W2 (AC-6/AC-6b): INV-4 as an executable assertion — install
      # and upgrade produce the SAME pointer (byte identity + content
      # soundness), repeat upgrades are idempotent, a degraded body is CURED
      # with backup, and an adopter-customized pointer is PRESERVED (S238).
      - name: Protocol pointer INV-4 e2e (4 legs)
        run: |
          set -euo pipefail
          bash scripts/tests/test-protocol-pointer-inv4.sh

      # The gate itself is proven BEFORE it is trusted: every failure mode it
      # claims to catch is planted with a fake harness and must go red. A CI
      # gate nobody can test is a gate nobody has proven (PLAN-167: 8
      # instrument defects).
      - name: Gate positive control (planted failure modes)
        run: |
          set -euo pipefail
          bash scripts/tests/test-ownership-nightly-gate.sh

      # PLAN-168 AC-5 — the SCRIPT is the gate (debate r1 QA must-fix 2:
      # describing behavior is not a gate). ownership-nightly-gate.sh runs the
      # e2e and enforces: rc>=2 = infra error (never comparable); summary line
      # present with HARNESS-ERR=0 (partial output fails); observed non-GREEN
      # id set == scripts/tests/ownership-expected-reds.txt exactly; rc
      # coherent with the set (non-empty => rc=1, empty => rc=0). NEVER --map.
      - name: Ownership e2e — full table vs expected non-GREEN set
        env:
          # 60s/cell flakes on 2-core CI iron (2-3x slower than the local
          # baseline the default was sized on).
          CELL_TIMEOUT: "180"
        run: |
          set -euo pipefail
          bash scripts/tests/ownership-nightly-gate.sh

exec
/bin/zsh -lc "find .claude/plans/PLAN-166/archive .claude/plans/PLAN-168/archive -type f -maxdepth 2 -print0 2>/dev/null | xargs -0 ls -lh; printf '\\n--- other untracked sizes ---\\n'; git ls-files --others --exclude-standard -z | xargs -0 ls -ldh; printf '\\n--- archives contents ---\\n'; for f in "'$(find .claude/plans/PLAN-166/archive .claude/plans/PLAN-168/archive -type f 2>/dev/null); do echo "### $f"; tar -tzf "$f" 2>/dev/null | head -30 || file "$f"; done' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 259ms:
### .claude/plans/PLAN-166/archive/mirror-fixes.sh
### .claude/plans/PLAN-166/archive/ceremony-porcelain-20260806-1430.txt
### .claude/plans/PLAN-166/archive/codex-review-w1-round9.md
### .claude/plans/PLAN-166/archive/w1-staged-pack-20260806-0159.tar.gz
.claude/plans/PLAN-166/staged/
.claude/plans/PLAN-166/staged/patches/
.claude/plans/PLAN-166/staged/notes-w1b-kernel-override.md
.claude/plans/PLAN-166/staged/.claude/
.claude/plans/PLAN-166/staged/INSTALL.md
.claude/plans/PLAN-166/staged/notes-w1c-f3.md
.claude/plans/PLAN-166/staged/scripts/
.claude/plans/PLAN-166/staged/.github/
.claude/plans/PLAN-166/staged/.github/workflows/
.claude/plans/PLAN-166/staged/.github/workflows/release.yml
.claude/plans/PLAN-166/staged/.github/workflows/npm-publish.yml
.claude/plans/PLAN-166/staged/.github/workflows/smoke-install.yml
.claude/plans/PLAN-166/staged/scripts/install.sh
.claude/plans/PLAN-166/staged/scripts/_framework_manifest_set.sh
.claude/plans/PLAN-166/staged/scripts/tests/
.claude/plans/PLAN-166/staged/scripts/doctor.sh
.claude/plans/PLAN-166/staged/scripts/upgrade.sh
.claude/plans/PLAN-166/staged/scripts/tests/test-upgrade-spec-ownership.sh
.claude/plans/PLAN-166/staged/.claude/adr/
.claude/plans/PLAN-166/staged/.claude/scripts/
.claude/plans/PLAN-166/staged/.claude/.framework-version
.claude/plans/PLAN-166/staged/.claude/governance/
.claude/plans/PLAN-166/staged/.claude/governance/npm-trusted-publisher.txt
.claude/plans/PLAN-166/staged/.claude/scripts/tests/
.claude/plans/PLAN-166/staged/.claude/scripts/check-framework-updates.sh
.claude/plans/PLAN-166/staged/.claude/scripts/tests/test_release_workflow_asserts.py
.claude/plans/PLAN-166/staged/.claude/adr/ADR-155-AMEND-1-delivery-record-ownership.md
.claude/plans/PLAN-166/staged/patches/f3-test-upgrade-spec-ownership.patch
.claude/plans/PLAN-166/staged/patches/f3-install-md-consequences.patch
.claude/plans/PLAN-166/staged/patches/w1a-npm-trusted-publisher-txt.patch
### .claude/plans/PLAN-166/archive/codex-review-w1-round2.md
### .claude/plans/PLAN-166/archive/codex-review-w1-round10.md
### .claude/plans/PLAN-166/archive/codex-review-w1-round6.md
### .claude/plans/PLAN-166/archive/codex-review-w1-round11.md
### .claude/plans/PLAN-166/archive/codex-review-w1-round7.md
### .claude/plans/PLAN-166/archive/codex-review-w1-round3.md
### .claude/plans/PLAN-166/archive/codex-review-w1-ceremony.md
### .claude/plans/PLAN-166/archive/codex-review-w1-round4.md
### .claude/plans/PLAN-166/archive/ceremony-worktree-20260806-1430.diff
### .claude/plans/PLAN-166/archive/codex-review-w1-round5.md
### .claude/plans/PLAN-166/archive/codex-r7-stophook-2135.md
### .claude/plans/PLAN-166/archive/codex-review-w0-residuals.md
### .claude/plans/PLAN-166/archive/codex-review-sentinel.md
### .claude/plans/PLAN-166/archive/w1-staged-pack-final-20260806-0722.tar.gz
.claude/plans/PLAN-166/staged/
.claude/plans/PLAN-166/staged/patches/
.claude/plans/PLAN-166/staged/notes-w1b-kernel-override.md
.claude/plans/PLAN-166/staged/.claude/
.claude/plans/PLAN-166/staged/INSTALL.md
.claude/plans/PLAN-166/staged/notes-w1c-f3.md
.claude/plans/PLAN-166/staged/scripts/
.claude/plans/PLAN-166/staged/.github/
.claude/plans/PLAN-166/staged/.github/workflows/
.claude/plans/PLAN-166/staged/.github/workflows/release.yml
.claude/plans/PLAN-166/staged/.github/workflows/npm-publish.yml
.claude/plans/PLAN-166/staged/.github/workflows/smoke-install.yml
.claude/plans/PLAN-166/staged/scripts/install.sh
.claude/plans/PLAN-166/staged/scripts/_framework_manifest_set.sh
.claude/plans/PLAN-166/staged/scripts/tests/
.claude/plans/PLAN-166/staged/scripts/doctor.sh
.claude/plans/PLAN-166/staged/scripts/upgrade.sh
.claude/plans/PLAN-166/staged/scripts/tests/test-upgrade-spec-ownership.sh
.claude/plans/PLAN-166/staged/.claude/adr/
.claude/plans/PLAN-166/staged/.claude/scripts/
.claude/plans/PLAN-166/staged/.claude/.framework-version
.claude/plans/PLAN-166/staged/.claude/governance/
.claude/plans/PLAN-166/staged/.claude/governance/npm-trusted-publisher.txt
.claude/plans/PLAN-166/staged/.claude/governance/pair-rail-verdict-template.md
.claude/plans/PLAN-166/staged/.claude/scripts/tests/
.claude/plans/PLAN-166/staged/.claude/scripts/check-framework-updates.sh
.claude/plans/PLAN-166/staged/.claude/scripts/tests/test_release_workflow_asserts.py
.claude/plans/PLAN-166/staged/.claude/adr/ADR-155-AMEND-1-delivery-record-ownership.md
.claude/plans/PLAN-166/staged/patches/f3-test-upgrade-spec-ownership.patch
.claude/plans/PLAN-166/staged/patches/f3-install-md-consequences.patch
### .claude/plans/PLAN-168/archive/0002-plan168-W2-W3-INV-4-curada-pelo-gerador-nico-ADR-190.patch
### .claude/plans/PLAN-168/archive/pack-full.diff
### .claude/plans/PLAN-168/archive/full-e2e-20260807-2017.log
### .claude/plans/PLAN-168/archive/0003-plan168-baseline-map-re-gravado-62-GREEN-3-RED-run-2.patch
### .claude/plans/PLAN-168/archive/0004-plan168-restaura-token-ADOPTER-FORK-na-WARNING-do-fo.patch
### .claude/plans/PLAN-168/archive/0001-plan168-W1-CI-wiring-dos-or-culos-de-propriedade.patch

exec
/bin/zsh -lc 'python3 -m unittest .claude.scripts.tests.test_release_workflow_asserts.Plan168OwnershipWiringTest' in /Users/joaocanhada/canhada-labs/ceo-orchestration
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
/bin/zsh -lc 'bash scripts/tests/test-protocol-pointer-render.sh' in /Users/joaocanhada/canhada-labs/ceo-orchestration
exec
/bin/zsh -lc 'bash scripts/tests/test-ownership-verdict-unit.sh' in /Users/joaocanhada/canhada-labs/ceo-orchestration
exec
/bin/zsh -lc 'bash scripts/tests/test-protocol-pointer-inv4.sh' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 0ms:
OWN-0001   ok     DELIVER HASH_SOURCE                      adr-155
OWN-0002   ok     DELIVER HASH_CANONICAL_POINTER           adr-155
OWN-0003   ok     DELIVER HASH_SOURCE                      adr-155-amend-1
OWN-0004   ok     PRESERVE_UNOWNED HASH_NONE               adr-155-amend-1
OWN-0005   ok     PRESERVE_UNOWNED HASH_NONE               adr-155-amend-1
OWN-0006   ok     PRESERVE_UNOWNED HASH_NONE               adr-155-amend-1
OWN-0007   ok     PRESERVE_UNOWNED HASH_NONE               adr-155-amend-1
OWN-0008   ok     DELIVER HASH_SOURCE                      adr-155-amend-1
OWN-0010   ok     PRESERVE_OWNED HASH_SOURCE               r1-F1
OWN-0011   ok     PRESERVE_OWNED HASH_PRIOR_RECORD         r1-F1
OWN-0012   ok     PRESERVE_OWNED HASH_SOURCE               r1-F1
OWN-0013   ok     PRESERVE_OWNED HASH_SOURCE               r5-F1
OWN-0014   ok     PRESERVE_OWNED HASH_PRIOR_RECORD         r9-F1
OWN-0015   ok     PRESERVE_OWNED HASH_SOURCE               r5-F1
OWN-0016   ok     PRESERVE_OWNED HASH_PRIOR_RECORD         r11-F2
OWN-0017   ok     REFRESH HASH_SOURCE                      r3-F2
OWN-0018   ok     REFRESH HASH_SOURCE                      adr-155-amend-1
OWN-0019   ok     PRESERVE_UNOWNED HASH_NONE               adr-155-amend-1
OWN-0020   ok     PRESERVE_UNOWNED HASH_NONE               r1-F3
OWN-0021   ok     REFRESH HASH_SOURCE                      adr-155-amend-1
OWN-0022   ok     REFRESH HASH_SOURCE                      adr-155-amend-1
OWN-0023   ok     REFRESH HASH_SOURCE                      r3-F1
OWN-0025   ok     PRESERVE_UNOWNED HASH_NONE               r9-F3
OWN-0026   ok     REFRESH HASH_SOURCE                      adr-155-amend-1
OWN-0028   ok     PRESERVE_UNOWNED HASH_NONE               r2-F3
OWN-0029   ok     PRESERVE_UNOWNED HASH_NONE               r2-F3
OWN-0030   ok     PRESERVE_UNOWNED HASH_NONE               r2-F1
OWN-0031   ok     PRESERVE_UNOWNED HASH_NONE               r4-F2
OWN-0032   ok     PRESERVE_UNOWNED HASH_NONE               derived
OWN-0033   ok     PRESERVE_UNOWNED HASH_NONE               derived
OWN-0034   ok     PRESERVE_UNOWNED HASH_NONE               derived
OWN-0040   ok     PRESERVE_OWNED LINK_RECORD               r4-F3
OWN-0041   ok     PRESERVE_OWNED LINK_RECORD               r4-F4
OWN-0042   ok     PRESERVE_UNOWNED HASH_NONE               r4-F3
OWN-0043   ok     PRESERVE_UNOWNED HASH_NONE               r4-F4
OWN-0044   ok     PRESERVE_UNOWNED HASH_NONE               r8-F2
OWN-0045   ok     PRESERVE_UNOWNED HASH_NONE               r8-F2
OWN-0046   ok     PRESERVE_OWNED LINK_RECORD               r6-F1
OWN-0047   ok     PRESERVE_OWNED LINK_RECORD               r6-F1
OWN-0048   ok     PRESERVE_OWNED LINK_RECORD               r7-F3
OWN-0049   ok     PRESERVE_OWNED LINK_RECORD               r7-F3
OWN-0050   ok     PRESERVE_UNOWNED HASH_NONE               r10-F1
OWN-0051   ok     PRESERVE_UNOWNED HASH_NONE               r10-F1
OWN-0052   ok     PRESERVE_UNOWNED HASH_NONE               r11-F1
OWN-0053   ok     PRESERVE_UNOWNED HASH_NONE               r11-F1
OWN-0060   ok     PRESERVE_OWNED HASH_SOURCE               adr-155-amend-1
OWN-0061   ok     PRESERVE_OWNED HASH_SOURCE               r2-F2
OWN-0062   ok     PRESERVE_OWNED HASH_SOURCE               r5-F3
OWN-0063   ok     PRESERVE_OWNED HASH_SOURCE               r10-F3
OWN-0064   ok     PRESERVE_OWNED HASH_SOURCE               adr-155-amend-1
OWN-0070   ok     PRESERVE_OWNED HASH_SOURCE               r7-F2
OWN-0071   ok     PRESERVE_OWNED HASH_PRIOR_RECORD         r7-F2
OWN-0072   ok     PRESERVE_OWNED HASH_PRIOR_RECORD         r9-F2
OWN-0073   ok     REFRESH HASH_SOURCE                      adr-155-amend-1
OWN-0074   ok     PRESERVE_OWNED HASH_CANONICAL_POINTER    derived
OWN-0080   ok     PRESERVE_UNOWNED HASH_NONE               r9-F4
OWN-0081   ok     PRESERVE_UNOWNED HASH_NONE               r11-F3
OWN-0082   ok     PRESERVE_OWNED HASH_PRIOR_RECORD         adr-155-amend-1
OWN-0090   ok     REFRESH HASH_SOURCE                      r7-F1
OWN-0091   ok     PRESERVE_OWNED HASH_SOURCE               r7-F1
OWN-0092   ok     REFRESH HASH_CANONICAL_POINTER           plan-168
OWN-0093   ok     REFRESH HASH_CANONICAL_POINTER           plan-168
OWN-0094   ok     PRESERVE_OWNED HASH_PRIOR_RECORD         plan-168

unit oracle: PASS=63  FAIL=0  SKIPPED(execution-fault rows)=2
  not decision cells, covered by the e2e: OWN-0024 OWN-0027 

exec
/bin/zsh -lc 'bash -n scripts/_framework_manifest_set.sh scripts/install.sh scripts/upgrade.sh scripts/tests/ownership-nightly-gate.sh scripts/tests/test-ownership-nightly-gate.sh scripts/tests/test-protocol-pointer-render.sh scripts/tests/test-protocol-pointer-inv4.sh && bash scripts/tests/test-ownership-nightly-gate.sh' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 894ms:
PASS  S1 matching set + rc=1 (gate rc=0)
PASS  S2 set grew (gate rc=1)
PASS  S3 set shrank (all green) (gate rc=1)
PASS  S4 harness rc=2 (gate rc=1)
PASS  S5 summary missing (gate rc=1)
PASS  S6 HARNESS-ERR=1 (gate rc=1)
PASS  S7 rc=0 with non-empty expected set (gate rc=1)
PASS  S8 set swapped (gate rc=1)
PASS  S9 empty expected set, all green (gate rc=0)
PASS  S10 expected id degraded to TIMEOUT (gate rc=1)
PASS  S11 expected id degraded to ESCAPE (gate rc=1)
PASS  S12 green cell degraded to AMBIG (gate rc=1)

ownership-nightly-gate positive control: 12/12 scenarios behave

 succeeded in 12986ms:
PASS  R1 healthy render == real install output
PASS  R2 degraded+substitute == healthy (single template)
PASS  R3 exact degraded body recognized (curable)
PASS  R4 healthy file not curable (preserved)
PASS  R5 edited degraded body preserved
PASS  R6 token-containing adopter file preserved
PASS  R7 ambiguous target preserved (documented residual)
PASS  R8 inside-target => relative render

protocol-pointer render control: 8/8 pass

exec
/bin/zsh -lc 'bash scripts/tests/test-protocol-pointer-inv4.sh' in /Users/joaocanhada/canhada-labs/ceo-orchestration
 succeeded in 181827ms:
PASS  L1 install->upgrade byte-identical + sound
PASS  L2 upgrade->upgrade idempotent
PASS  L3 degraded body cured (REFRESH route taken)
PASS  L3b cure kept a backup of the degraded original
PASS  L4 adopter-customized pointer preserved byte-identical

INV-4 assertion: 4/4 legs pass (byte identity + content soundness + cure + preserve)

