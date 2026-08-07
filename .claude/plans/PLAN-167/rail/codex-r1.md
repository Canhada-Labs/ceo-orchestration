OpenAI Codex v0.144.6
--------
workdir: /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
model: gpt-5.6-sol
provider: openai
approval: never
sandbox: read-only
reasoning effort: xhigh
reasoning summaries: none
session id: 019fdc92-015f-7463-94e4-c591436e0c6e
--------
user
current changes
exec
/bin/zsh -lc "git status --short && printf '\\n--- DIFF STAT ---\\n' && git diff --stat && printf '\\n--- CACHED STAT ---\\n' && git diff --cached --stat" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 163ms:
 .claude/governance/pair-rail-verdict-template.md   |  18 +
 .claude/plans/PLAN-166/W1-approved-draft.md        |   1 +
 .claude/plans/PLAN-166/staged-manifest.sha256      |  22 +-
 .claude/scripts/check-framework-updates.sh         |  95 ++-
 .claude/scripts/check-model-deprecations.py        |  13 +-
 .../scripts/tests/test_release_workflow_asserts.py | 683 +++++++++++++++++-
 .github/workflows/npm-publish.yml                  | 151 ++++
 .github/workflows/release.yml                      | 164 +++++
 .github/workflows/smoke-install.yml                | 119 +++-
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
 scripts/upgrade.sh                                 | 792 +++++++++++++++++++--
 27 files changed, 2651 insertions(+), 167 deletions(-)

--- CACHED STAT ---
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-0cRSAne5' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-C9IKiOKZ' (errno=Operation not permitted)

exec
/bin/zsh -lc "find .claude/plans/PLAN-166/architect -type f -maxdepth 2 -print 2>/dev/null; printf '\\n--- all untracked files ---\\n'; git ls-files --others --exclude-standard" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
.claude/plans/PLAN-166/architect/round-1/approved.md

--- all untracked files ---
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-AiKU6eAM' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-ME8pfgT0' (errno=Operation not permitted)
.claude/.framework-version
.claude/adr/ADR-155-AMEND-1-delivery-record-ownership.md
.claude/governance/npm-trusted-publisher.txt
.claude/plans/PLAN-166/architect/round-1/approved.md
scripts/tests/test-ownership-verdict-unit.sh
scripts/tests/test-upgrade-spec-ownership.sh

exec
/bin/zsh -lc "cat .claude/plans/PLAN-166/W1-approved-draft.md; printf '\\n--- APPROVED ---\\n'; cat .claude/plans/PLAN-166/architect/round-1/approved.md; printf '\\n--- ADR ---\\n'; cat .claude/adr/ADR-155-AMEND-1-delivery-record-ownership.md; printf '\\n--- TEMPLATE DIFF ---\\n'; git diff -- .claude/governance/pair-rail-verdict-template.md; printf '\\n--- VERSION ---\\n'; cat .claude/.framework-version; printf '\\n--- TRUSTED ---\\n'; cat .claude/governance/npm-trusted-publisher.txt" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
---
plan: PLAN-166
round: 1
type: architect-sentinel
segment: W1-FINDINGS-CLOSURE
---

<!--
  ============================ DRAFT — DO NOT SIGN AS-IS ============================
  This is the assembler's draft of the W1 ceremony sentinel. Before signing, the
  Owner (or the ceremony session under the Owner's eyes) MUST:

    1. Copy this file to .claude/plans/PLAN-166/architect/round-1/approved.md
       (generate-ceremony.sh guard G2 requires that exact location/name).
    2. Replace <<FILL-AT-SIGNING>> in Anchor-SHA with the REAL sha of origin/main
       at the moment of signing (git rev-parse HEAD after the final fetch) — the
       placeholder is deliberately non-hex so an unsigned/unedited draft can never
       parse as a valid anchor.
    3. RE-DERIVE the Scope block mechanically (PLAN-166 W1 item 6):
         git status --porcelain | awk '{print $2}' | LC_ALL=C sort
       run AFTER applying the staged copies + the ADR-count doc sweep, and diff it
       against the block below. touched−scope=∅ must hold over the WHOLE ceremony
       commit BEFORE the signature is requested. ONE tolerated exception (runbook
       §7, PLAN-165 precedent): plan artifacts under .claude/plans/PLAN-166/**
       (approved.md + .asc, staged-manifest.sha256, W1-approved-draft.md,
       W1-land-runbook.md) ride in the ceremony commit as NON-canonical evidence
       and stay OUT of this Scope block — they are the only comm-23 residual §7
       accepts. Any OTHER difference = fix the tree or fix this file, then
       re-sign (a rewritten approved.md always re-signs).
    4. Fill Approved-At with the signing date.
  ===================================================================================
-->

# PLAN-166 W1 — release-hold findings-closure ceremony (Owner sentinel)

Anchor-SHA: <<FILL-AT-SIGNING>>

Approved-By: @Canhada-Labs (Owner GPG — signed inline by the ceremony)
Approved-At: <<FILL-AT-SIGNING>>

## What this sentinel authorizes (sign this KNOWINGLY)

Single declared PLAN-166 W1 ceremony (plan `reviewed` at `92c8c3c`; debate
3 rounds with 3 scoped VETOs raised-and-lifted + codex rail 20 rounds; the
re-pass of rc.1 was NO-GO with 6 findings and the Owner mandated closing
ALL of them — this commit is the canonical half of that closure; W0 free
surfaces land separately). One commit, two REVERT GROUPS (the Scope below
is grouped so either half can be reverted without splitting the ceremony
— with ONE deliberate coupling, sign it knowingly: release.yml (group A)
carries the UNCONDITIONAL `.claude/.framework-version == VERSION` assert
while the marker file itself is in group B, so reverting ONLY group B
leaves every tag run red until release.yml is re-edited, which means a
NEW kernel-override route. The failure direction is CLOSED — it blocks a
ship, never publishes — but the operational cost of a partial group-B
revert is a second ceremony):

**Group A — release train (F1 + F2 server side + item 4):**

1. `npm-publish.yml` gains the `await-release-gate` job (fail-closed
   poller over release.yml's `release-gate` job via
   `.claude/scripts/await_release_gate.py`, timeout-minutes 35, GH_TOKEN
   at job level, NO environment / NO RC exclusion — RC tags are the live
   positive control) + `needs: await-release-gate` on `publish`. Posture
   pins STRENGTHENED, not relocated: `environment: production-npm` and
   the `-rc.` exclusion stay VERBATIM on the publish job.
2. `release.yml` gains (i) the verdict delta + ancestry gate step
   (delegates to `.claude/scripts/local/_release_tag_guard.py`; no
   continue-on-error; fails CLOSED on `CEO_PAIR_RAIL_VERDICT_OPTIONAL=1`;
   ancestry covers the reviewed parent AND `GITHUB_SHA`, r15+r17+r18) and
   (ii) the UNCONDITIONAL `.claude/.framework-version == VERSION` assert
   (Forma A (ii), next to the VERSION↔tag asserts).
3. `.claude/governance/npm-trusted-publisher.txt` — the npmjs OIDC
   trusted-publisher triple (repository / workflow FILENAME /
   environment) as a tracked record.
4. `test_release_workflow_asserts.py` — structural asserts for 1-3
   (await-gate pins, W1B delta+ancestry pins merged in by the assembler,
   trusted-publisher binding asserts that READ the txt, with positive
   controls).
5. `RELEASE.md` — derived step count in the release.yml pointer block
   29 → 31 (item 2 adds two named steps to release-gate; the
   `verify-counts.sh` release_steps rule is exact/tolerance-0 and scans
   RELEASE.md, so WITHOUT this edit the ceremony's own §6(d) gate goes
   red post-apply and forces an out-of-scope fix mid-ceremony).

**Group B — adopter upgrade (F3 + F4 + ADR-155-AMEND-1):**

6. `ADR-155-AMEND-1-delivery-record-ownership.md` — delivery-record
   ownership of the three conditional surfaces (SPEC/v1, root
   PROTOCOL.md, `.claude/.framework-version`); ADR file count 188 → 189.
7. `.claude/.framework-version` — NEW tracked one-line marker,
   byte-identical to VERSION (1.3.0).
8. `install.sh` / `upgrade.sh` / `_framework_manifest_set.sh` /
   `doctor.sh` / `check-framework-updates.sh` — explicit delivery writes
   + record-gated readers + forced/validated marker refresh + SPEC
   forced-refresh with pristine-fingerprint legacy migration (v1.0.0..
   v1.2.0-rc.3 set; ADOPTER-FORK preserved in place). The SPEC
   delivery-record readers (`upgrade.sh _baseline_has_spec_record`,
   `doctor.sh _dr_delivered`) match `SPEC/v1(/|  |$)` — a --mode link
   install records the tree as ONE `LINK  SPEC/v1  <target>` line, no
   trailing slash (re-pass closure; family swept).
9. `smoke-install.yml` — wires the F4 parity e2e (+ LOAD-BEARING
   positive control: rc==1 AND plant evidence greped from the log, else
   red) AND the F3 spec-ownership e2e (S1-S8) into CI, path filters
   re-synced between pull_request and push, timeout-minutes 8 → 25.
   **Explicit plan deviation, ratified by this signature:** PLAN-166 W1
   item 3 says "8→~15"; the staged value is 25, from MEASURED wall time
   (F4: 122s gate + 118s control local, 2-3x CI factor; F3 e2e adds
   ~3-4 min local) + the PLAN-159 N=20-flake lesson — 15 sits inside
   the noise band. Signing this sentinel ratifies 25 KNOWINGLY, not by
   silence; re-tighten once real CI runs give a p95.
10. `scripts/tests/test-upgrade-spec-ownership.sh` — NEW e2e (S1-S8).
11. `INSTALL.md` — post-upgrade verify instructions prefer the marker;
    delivery-record consequences documented.
12. ADR-count sweep 188 → 189 in the SAME commit, sites derived from the
    `verify-counts.sh` matchers themselves (12 matcher-reachable
    occurrences across 8 docs — the W1-C census note says "9 docs";
    recount at land time from the gate, not from either number): the
    docs listed in Group B below. `docs/ARCHITECTURE.md:56` and `:237`
    are NOT matcher-reachable but sit in an already-touched file and are
    updated in the same pass. Same treatment for the TWO
    matcher-INVISIBLE ADR-count claims in `docs/GUIA-COMPLETO.md`
    (":167 `188 ADRs document every architectural decision`" and
    ":1225 `— 188 Architecture Decision Records`") — GUIA is in the
    gate's DOCS but neither phrasing is reachable by any matcher, so
    left alone they would silently claim 188 with 189 on disk (the
    exact [[feedback-adr-count-drift-unwatched-docs]] class W0/F5 just
    closed elsewhere); swept in §4 of the runbook, file added to this
    Scope. The 189 in `verify-counts.sh` is DERIVED (file count), not a
    typed constant — no edit to it for the count.

**Kernel-override route (release.yml ONLY):** `release.yml` is canonical
AND an exact `_KERNEL_PATHS` entry (`check_arbitration_kernel.py:134`).
Its apply runs under the PER-CEREMONY pair
`CEO_KERNEL_OVERRIDE=PLAN-166-W1-RELEASE-YML-AWAIT-GATE` +
`CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT`, armed inline immediately before the
apply and disarmed immediately after (never exported in
settings.local.json or shell profile). The audit-ledger event
(`plan_id` truncated to `PLAN-166-W1-RELEASE-YML-AWAIT-GA`, 32 chars) is
the proof artifact — see `staged/notes-w1b-kernel-override.md` and the
land runbook. Editing release.yml is literally the "CI gate bypass"
vector the kernel exists to impede; the privilege stays armed only for
the duration of the signature window.

**Conditional entries (OWNER-DECISION at signing — runbook §4 has the
verified detail):** the two deferred-apply marker sites of
`staged/notes-w1c-f3.md` §1 — `.claude/scripts/local/_release_bump_sites.py`
(12th bump site) and `.claude/scripts/local/verify-counts.sh`
(VERSION_SITES entry). Status re-checked at closure (2026-08-06, HEAD
`346f4ea`): the W0 fleet HAS committed both files and the sites are
absent, so the original condition fires — BUT simulation showed §1a as
written reds the fleet's new dry-run tests (their fixture lacks the
marker file; verified 2-line fixture cure → 47/47). Route A: apply
§1a+§1b+fixture cure and ADD the three paths to Scope. Route B
(recommended default): SKIP; the fleet lands all three in its own
follow-up — Forma A (ii) is unconditional either way, and this train
(VERSION already 1.3.0 == marker) needs no marker bump site before the
1.4.0 cycle. Whichever route, the mechanical re-derivation of step 3 in
the header enforces the Scope.

Ceremony inputs are integrity-pinned: the TRACKED manifest
`.claude/plans/PLAN-166/staged-manifest.sha256` covers every staged file;
`shasum -a 256 -c` runs fail-closed BEFORE any apply (lesson
[[feedback-staged-inputs-need-tracked-hash-manifest]]).

Commit subject tag: `[SENT-PLAN166-W1]`.

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
  - scripts/tests/_parity_classify.py
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

--- APPROVED ---
---
plan: PLAN-166
round: 1
type: architect-sentinel
segment: W1-FINDINGS-CLOSURE
---

# PLAN-166 W1 — release-hold findings-closure ceremony (Owner sentinel)

Anchor-SHA: 516e64e671f6e33b7fcf0f0a28a70caf954bd996

Approved-By: @Canhada-Labs (Owner GPG — signed inline by the ceremony)
Approved-At: 2026-08-06

## What this sentinel authorizes (sign this KNOWINGLY)

Single declared PLAN-166 W1 ceremony (plan `reviewed` at `92c8c3c`; debate
3 rounds with 3 scoped VETOs raised-and-lifted + codex rail 20 rounds; the
re-pass of rc.1 was NO-GO with 6 findings and the Owner mandated closing
ALL of them — this commit is the canonical half of that closure; W0 free
surfaces land separately). One commit, two REVERT GROUPS (the Scope below
is grouped so either half can be reverted without splitting the ceremony
— with ONE deliberate coupling, sign it knowingly: release.yml (group A)
carries the UNCONDITIONAL `.claude/.framework-version == VERSION` assert
while the marker file itself is in group B, so reverting ONLY group B
leaves every tag run red until release.yml is re-edited, which means a
NEW kernel-override route. The failure direction is CLOSED — it blocks a
ship, never publishes — but the operational cost of a partial group-B
revert is a second ceremony):

**Group A — release train (F1 + F2 server side + item 4):**

1. `npm-publish.yml` gains the `await-release-gate` job (fail-closed
   poller over release.yml's `release-gate` job via
   `.claude/scripts/await_release_gate.py`, timeout-minutes 35, GH_TOKEN
   at job level, NO environment / NO RC exclusion — RC tags are the live
   positive control) + `needs: await-release-gate` on `publish`. Posture
   pins STRENGTHENED, not relocated: `environment: production-npm` and
   the `-rc.` exclusion stay VERBATIM on the publish job.
2. `release.yml` gains (i) the verdict delta + ancestry gate step
   (delegates to `.claude/scripts/local/_release_tag_guard.py`; no
   continue-on-error; fails CLOSED on `CEO_PAIR_RAIL_VERDICT_OPTIONAL=1`;
   ancestry covers the reviewed parent AND `GITHUB_SHA`, r15+r17+r18) and
   (ii) the UNCONDITIONAL `.claude/.framework-version == VERSION` assert
   (Forma A (ii), next to the VERSION↔tag asserts).
3. `.claude/governance/npm-trusted-publisher.txt` — the npmjs OIDC
   trusted-publisher triple (repository / workflow FILENAME /
   environment) as a tracked record.
4. `test_release_workflow_asserts.py` — structural asserts for 1-3
   (await-gate pins, W1B delta+ancestry pins merged in by the assembler,
   trusted-publisher binding asserts that READ the txt, with positive
   controls).
5. `RELEASE.md` — derived step count in the release.yml pointer block
   29 → 31 (item 2 adds two named steps to release-gate; the
   `verify-counts.sh` release_steps rule is exact/tolerance-0 and scans
   RELEASE.md, so WITHOUT this edit the ceremony's own §6(d) gate goes
   red post-apply and forces an out-of-scope fix mid-ceremony).

**Group B — adopter upgrade (F3 + F4 + ADR-155-AMEND-1):**

6. `ADR-155-AMEND-1-delivery-record-ownership.md` — delivery-record
   ownership of the three conditional surfaces (SPEC/v1, root
   PROTOCOL.md, `.claude/.framework-version`); ADR file count 188 → 189.
7. `.claude/.framework-version` — NEW tracked one-line marker,
   byte-identical to VERSION (1.3.0).
8. `install.sh` / `upgrade.sh` / `_framework_manifest_set.sh` /
   `doctor.sh` / `check-framework-updates.sh` — explicit delivery writes
   + record-gated readers + forced/validated marker refresh + SPEC
   forced-refresh with pristine-fingerprint legacy migration (v1.0.0..
   v1.2.0-rc.3 set; ADOPTER-FORK preserved in place). The SPEC
   delivery-record readers (`upgrade.sh _baseline_has_spec_record`,
   `doctor.sh _dr_delivered`) match `SPEC/v1(/|  |$)` — a --mode link
   install records the tree as ONE `LINK  SPEC/v1  <target>` line, no
   trailing slash (re-pass closure; family swept).
9. `smoke-install.yml` — wires the F4 parity e2e (+ LOAD-BEARING
   positive control: rc==1 AND plant evidence greped from the log, else
   red) AND the F3 spec-ownership e2e (S1-S8) into CI, path filters
   re-synced between pull_request and push, timeout-minutes 8 → 25.
   **Explicit plan deviation, ratified by this signature:** PLAN-166 W1
   item 3 says "8→~15"; the staged value is 25, from MEASURED wall time
   (F4: 122s gate + 118s control local, 2-3x CI factor; F3 e2e adds
   ~3-4 min local) + the PLAN-159 N=20-flake lesson — 15 sits inside
   the noise band. Signing this sentinel ratifies 25 KNOWINGLY, not by
   silence; re-tighten once real CI runs give a p95.
10. `scripts/tests/test-upgrade-spec-ownership.sh` — NEW e2e (S1-S8).
11. `INSTALL.md` — post-upgrade verify instructions prefer the marker;
    delivery-record consequences documented.
12. ADR-count sweep 188 → 189 in the SAME commit, sites derived from the
    `verify-counts.sh` matchers themselves (12 matcher-reachable
    occurrences across 8 docs — the W1-C census note says "9 docs";
    recount at land time from the gate, not from either number): the
    docs listed in Group B below. `docs/ARCHITECTURE.md:56` and `:237`
    are NOT matcher-reachable but sit in an already-touched file and are
    updated in the same pass. Same treatment for the TWO
    matcher-INVISIBLE ADR-count claims in `docs/GUIA-COMPLETO.md`
    (":167 `188 ADRs document every architectural decision`" and
    ":1225 `— 188 Architecture Decision Records`") — GUIA is in the
    gate's DOCS but neither phrasing is reachable by any matcher, so
    left alone they would silently claim 188 with 189 on disk (the
    exact [[feedback-adr-count-drift-unwatched-docs]] class W0/F5 just
    closed elsewhere); swept in §4 of the runbook, file added to this
    Scope. The 189 in `verify-counts.sh` is DERIVED (file count), not a
    typed constant — no edit to it for the count.

**Kernel-override route (release.yml ONLY):** `release.yml` is canonical
AND an exact `_KERNEL_PATHS` entry (`check_arbitration_kernel.py:134`).
Its apply runs under the PER-CEREMONY pair
`CEO_KERNEL_OVERRIDE=PLAN-166-W1-RELEASE-YML-AWAIT-GATE` +
`CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT`, armed inline immediately before the
apply and disarmed immediately after (never exported in
settings.local.json or shell profile). The audit-ledger event
(`plan_id` truncated to `PLAN-166-W1-RELEASE-YML-AWAIT-GA`, 32 chars) is
the proof artifact — see `staged/notes-w1b-kernel-override.md` and the
land runbook. Editing release.yml is literally the "CI gate bypass"
vector the kernel exists to impede; the privilege stays armed only for
the duration of the signature window.

**Conditional entries (OWNER-DECISION at signing — runbook §4 has the
verified detail):** the two deferred-apply marker sites of
`staged/notes-w1c-f3.md` §1 — `.claude/scripts/local/_release_bump_sites.py`
(12th bump site) and `.claude/scripts/local/verify-counts.sh`
(VERSION_SITES entry). Status re-checked at closure (2026-08-06, HEAD
`346f4ea`): the W0 fleet HAS committed both files and the sites are
absent, so the original condition fires — BUT simulation showed §1a as
written reds the fleet's new dry-run tests (their fixture lacks the
marker file; verified 2-line fixture cure → 47/47). Route A: apply
§1a+§1b+fixture cure and ADD the three paths to Scope. Route B
(recommended default): SKIP; the fleet lands all three in its own
follow-up — Forma A (ii) is unconditional either way, and this train
(VERSION already 1.3.0 == marker) needs no marker bump site before the
1.4.0 cycle. Whichever route, the mechanical re-derivation enforces the Scope.
**OWNER-DECISION resolved at signing (2026-08-06): Route B — deferred-apply
SKIPPED; the three paths stay OUT of this Scope. The follow-up (free
surfaces, no sentinel) MUST land before the first 1.4.0-cycle bump.**

Ceremony inputs are integrity-pinned: the TRACKED manifest
`.claude/plans/PLAN-166/staged-manifest.sha256` covers every staged file;
`shasum -a 256 -c` runs fail-closed BEFORE any apply (lesson
[[feedback-staged-inputs-need-tracked-hash-manifest]]).

Commit subject tag: `[SENT-PLAN166-W1]`.

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
  - scripts/tests/_parity_classify.py
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

---

## Adendo (2026-08-06, re-assinatura — rail codex round 4)

Uma linha adicionada ao Scope grupo B: `scripts/tests/_parity_classify.py`.
Motivo: as entradas KNOWN_OPEN F3-spec-stale / F3-protocol-user-mode são
MANDATORY-FIRE por contrato do próprio arquivo — com o F3 fechado por esta
cerimônia elas param de casar e o gate recém-fiado nasceria FATAL; o
docstring exige deletá-las NO MESMO commit. Rounds 1-4 do rail: 13 achados
aplicados (install rerun continuity; FMS_MODE link; fingerprint
completeness; SPEC/marker ancestor-symlink + LINK-record validation;
backup-before-replace 2x; recovery por current-source match; KNOWN_OPEN).

--- ADR ---
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

--- TEMPLATE DIFF ---
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-CkuX3xEr' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-HQAcYb39' (errno=Operation not permitted)
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

--- VERSION ---
1.3.0

--- TRUSTED ---
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
/bin/zsh -lc 'git diff -- .github/workflows/npm-publish.yml .github/workflows/release.yml .github/workflows/smoke-install.yml' in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-bvB3EysD' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-0hmcLoeF' (errno=Operation not permitted)
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
/bin/zsh -lc "sed -n '1,280p' .claude/scripts/await_release_gate.py; printf '\\n--- release guard relevant ---\\n'; grep -n \"def cmd_\\|def _parse_verdict\\|delta\\|ancestry\" .claude/scripts/local/_release_tag_guard.py | head -80; sed -n '1,360p' .claude/scripts/local/_release_tag_guard.py" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
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

--- release guard relevant ---
43:#           `commit-tree` anchor makes the whole delta trivially clean.
55:#   6 delta outside allowlist  7 manifest sha pin mismatch
58:#  11 the assert would be VACUOUS (the verdict is not inside the delta it
65:"""Ancestry + restricted-delta asserts for the release tag phase."""
96:# workflow, any code path — would re-open the very hole the delta assert exists
122:# (a) ancestry
124:def ancestry(repo: str, remote: str, branch: str, offline_ack: bool) -> int:
128:            "  --   ancestry: --offline-ack given, NOT fetching; the "
154:            "no usable ref %s in this repo — cannot judge ancestry "
181:# (b) restricted delta
183:def _parse_verdict(text: str) -> Dict[str, object]:
196:    `delta_allowlist` silently. The W1 server-side port must therefore extend
275:def delta(repo: str, tag: str, verdict_rel: Optional[str]) -> int:
327:            "      makes the delta below trivially clean while unreviewed "
340:    allow = fields.get("delta_allowlist")
344:            "verdict %s carries no `delta_allowlist:` entries — the closed "
345:            "set is what makes the delta assert meaningful." % verdict_rel,
351:                "delta_allowlist entry %r contains a glob metacharacter. The "
359:                "delta_allowlist entry %r must be a repo-relative path with "
365:                "delta_allowlist entry %r is another tag's verdict (or the "
372:                "delta_allowlist entry %r is neither this tag's verdict nor "
388:            "the verdict itself (%s) is not in its own delta_allowlist — it "
392:    manifest_rel = fields.get("delta_manifest")
393:    manifest_sha = fields.get("delta_manifest_sha256")
397:            "verdict %s carries no `delta_manifest:` — without it the "
404:            "verdict %s has no usable 64-hex `delta_manifest_sha256:`."
410:            "delta_manifest %s is not in delta_allowlist." % manifest_rel,
416:        return _fail(E_MANIFEST_PIN, "delta_manifest %s missing" % manifest_rel)
421:            "delta_manifest sha256 mismatch for %s\n"
464:                "delta_allowlist entry %r is outside the manifest directory "
498:    # --- the delta itself ---
526:    # AT (or after) the verdict: the delta is then empty or verdict-free and
532:            "the verdict %s is not part of the delta %s..HEAD — this assert "
547:        "  ok   delta %s..HEAD is %d file(s), all inside the verdict's closed "
548:        "allowlist of %d (verdict present in the delta)"
558:    p_anc = sub.add_parser("ancestry", help="HEAD must be on origin/<branch>")
569:    p_delta = sub.add_parser("delta", help="restricted delta vs the verdict")
570:    p_delta.add_argument("--repo", default=".")
571:    p_delta.add_argument("--tag", required=True)
572:    p_delta.add_argument("--verdict", default=None)
575:    if args.cmd == "ancestry":
576:        return ancestry(args.repo, args.remote, args.branch, args.offline_ack)
577:    if args.cmd == "delta":
578:        return delta(args.repo, args.tag, args.verdict)
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
/bin/zsh -lc "sed -n '1,130p' .github/workflows/release.yml; grep -n \"Checkout\\|fetch-depth\\|release-gate:\" .github/workflows/release.yml | head -30; sed -n '570,755p' .github/workflows/release.yml" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
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

      # -----------------------------------------------------------------
      # PLAN-166 W1 item 2 (F3, ADR-155-AMEND-1 §5, Forma A (ii)) — the
      # framework version marker `.claude/.framework-version` is a TRACKED
      # one-line file, byte-identical to VERSION (the version bump writes
      # it as a site; verify-counts.sh cross-checks it). This assert is
      # deliberately UNCONDITIONAL and fail-closed: a missing marker in a
      # release checkout means the ceremony that introduced it was
      # reverted or the bump skipped a site — either way the tag must not
      # ship. Kept NEXT TO the VERSION↔tag assert above so the whole
      # version-consistency family lives in one place (same convention as
      # the plugin-manifest step below).
      # -----------------------------------------------------------------
      - name: Assert framework-version marker matches VERSION
        run: |
          set -euo pipefail
          FILE="$(tr -d '[:space:]' < VERSION)"
          if [[ ! -f .claude/.framework-version ]]; then
            echo "::error::.claude/.framework-version is missing — it is a tracked file (PLAN-166 F3 / ADR-155-AMEND-1); a release checkout without it must not ship"
            exit 1
          fi
          MARKER="$(tr -d '[:space:]' < .claude/.framework-version)"
          if [[ "$MARKER" != "$FILE" ]]; then
            echo "::error::.claude/.framework-version ('$MARKER') does not match VERSION ('$FILE') — the marker is byte-identical to VERSION by contract (Forma A (ii), fail-closed)"
            exit 1
          fi
          echo "OK: .claude/.framework-version=$MARKER matches VERSION"

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
13:  release-gate:
25:      - name: Checkout tag
29:          fetch-depth: 0
791:          # (1) Checkout sanity: every assert below anchors on HEAD, so
875:      - name: Checkout tag
879:          fetch-depth: 0
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

      # ==========================================================
      # PLAN-166 W1-B — verdict delta + ancestry gate (F2 server side)
      # ==========================================================
      # Re-pass findings r15 + r17 + r18 (PLAN-166), debate r3 scoped VETO.
      #
      # WHY A SEPARATE STEP: the step-15 neighbourhood above carries two
      # escape hatches keyed to CEO_PAIR_RAIL_VERDICT_OPTIONAL —
      # `continue-on-error:` on the step itself, and an empty
      # `--parent-sha ""` bind (the validator only binds the field when
      # args.parent_sha is non-empty). Inheriting that neighbourhood would
      # inherit the switch. This step therefore:
      #   - carries NO continue-on-error;
      #   - FAILS CLOSED when CEO_PAIR_RAIL_VERDICT_OPTIONAL=1: in that
      #     mode step 15 skipped the parent_sha bind, so the anchor these
      #     asserts hang off was never validated — there is no transition
      #     mode here, by design;
      #   - re-derives and re-binds parent_sha ITSELF (non-empty, 40-hex,
      #     equal to the verdict's `parent_sha:` read with the SAME parser
      #     the local tag guard uses) — independent of step 15's outcome,
      #     which also closes the legacy commit_sha fallback (the
      #     validator downgrades a missing parent_sha to an ADVISORY when
      #     a legacy commit_sha is present; this step does not);
      #   - reuses .claude/scripts/local/_release_tag_guard.py for the
      #     delta decision — the module marks itself as the reference
      #     implementation; the semantics are NEVER re-implemented in

exec
/bin/zsh -lc 'git diff -- scripts/_framework_manifest_set.sh' in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-5FZ6EJpr' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-EY3VAR0c' (errno=Operation not permitted)
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

exec
/bin/zsh -lc 'git diff -- scripts/install.sh' in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-lQd4gIYz' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-RVBMwnXU' (errno=Operation not permitted)
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
/bin/zsh -lc "sed -n '90,270p' scripts/_framework_manifest_set.sh; grep -n \"baseline\\|install-manifest\\|LINK\" scripts/uninstall.sh | head -100; sed -n '300,520p' scripts/uninstall.sh 2>/dev/null" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
# structural exclusions (install_hooks_selective / install_lib_selective /
# install_scripts_selective); install.sh's _lib walk now calls THIS predicate,
# and upgrade.sh applies it at its three write surfaces (classified union
# walk, legacy cp -R prune, manifest enumeration below).
# bash 3.2-safe: pure case globs, no arrays.
_framework_path_excluded() {
  case "$1" in
    .claude/hooks/tests|.claude/hooks/tests/*) return 0 ;;
    .claude/hooks/legacy|.claude/hooks/legacy/*) return 0 ;;
    .claude/scripts/tests|.claude/scripts/tests/*) return 0 ;;
    .claude/hooks/_lib/tests|.claude/hooks/_lib/tests/*) return 0 ;;
    .claude/hooks/_lib/test_isolation.py) return 0 ;;
    .claude/hooks/_lib/testing.py) return 0 ;;
    __pycache__|*/__pycache__|__pycache__/*|*/__pycache__/*) return 0 ;;
    *.pyc) return 0 ;;
  esac
  return 1
}

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

# _framework_manifest_files — expand every target entry into its per-file
# relpaths, relative to FMS_ROOT. Directories are walked (regular files only;
# symlinks are NOT followed into — a symlinked file is emitted as its own
# relpath and the manifest writer records it as a LINK record). EXCLUDES the
# manifest dotfile + .claude.bak/. Sorted + deduped. Missing entries (e.g. a
# profile dir absent on disk) are silently skipped — profile-awareness.
_framework_manifest_files() {
  _fms_root="${FMS_ROOT:-.}"
  {
    _framework_target_entries | while IFS= read -r _fms_entry; do
      [ -n "$_fms_entry" ] || continue
      _fms_abs="$_fms_root/$_fms_entry"
      if [ -f "$_fms_abs" ] || [ -L "$_fms_abs" ]; then
        # A plain file (or symlinked file) target.
        printf '%s\n' "$_fms_entry"
      elif [ -d "$_fms_abs" ]; then
        # Walk the directory for regular files + symlinks. `-print` with a
        # leading "./"-stripped relpath; we re-root each hit at $_fms_entry.
        # bash 3.2-safe: no mapfile; pipe find into a read loop.
        find "$_fms_abs" \( -type f -o -type l \) -print 2>/dev/null | while IFS= read -r _fms_hit; do
          # Strip the "$_fms_root/" prefix to get a repo-relative path.
          _fms_rel="${_fms_hit#"$_fms_root"/}"
          printf '%s\n' "$_fms_rel"
        done
      fi
      # else: entry absent on disk for this profile — skip (profile-aware).
    done
  } | grep -v -e '^\.claude/\.install-manifest\.sha256$' \
            -e '^\.claude\.bak/' \
            -e '/\.claude\.bak/' \
            -e '/__pycache__/' \
            -e '\.pyc$' \
    | while IFS= read -r _fms_out; do
        # PLAN-161 U2 (CF-7): never record framework-internal excluded paths
        # in the baseline — recording them would legitimize a mis-install
        # (and the upgrade would re-add what an adopter deleted by hand).
        if ! _framework_path_excluded "$_fms_out"; then
          printf '%s\n' "$_fms_out"
        fi
      done \
    | LC_ALL=C sort -u
}

# _write_baseline_manifest — THE single baseline-manifest generator (ADR-155
# decision (iv)). Called by install.sh write_install_manifest AND by upgrade.sh
# after a successful upgrade, so a long-lived adopter who upgrades but never
# re-runs install.sh acquires/refreshes a manifest.
#
# Inputs (callers export these before calling):
#   FMS_ROOT          — the installed target root (paths are relative to it)
#   FMS_PROFILE_PARTS — space-separated profile list (profile-aware enumeration)
#   FMS_MODE          — "link" to emit LINK records for symlinks, else "copy"
# Requires _hash_file (from _hash_lib.sh) on PATH. Writes validated records to
# $1 (the manifest path) atomically. Fail-open: returns 0 with a stderr NOTE on
# any problem; never aborts the caller.
#
# Grammar:
#   <64hex>  <relpath>          — content hash
#   LINK  <relpath>  <target>   — link-mode symlink (content == source)

# Does FMS_HASH_ROOT apply to this relpath? UNSET FMS_HASH_ROOT_PATHS means
# ALL of them — the upgrade posture, where every enumerated file must record
# what the framework SHIPS. install.sh needs the opposite default for most of
# the tree: it RENDERS templates (`.claude/team.md`, skills, `{{X}}`
# placeholders under --project et al), so those legitimately differ from
# source and their baseline must be the rendered TARGET. A global
# FMS_HASH_ROOT on an install rerun rewrote every rendered file's hash to the
# unrendered source, which doctor.sh reads as widespread adopter drift and
# later upgrades read as customized => the files stop being refreshed (codex
# W1 round 8, P1). Scoping the override to the ownership-continuity paths
# keeps the round-5 fix (an EDITED delivered SPEC must not be re-baselined as
# framework-owned, or uninstall would delete the adopter's fork) without
# touching the rendered tree. Prefix match: an entry covers the path itself
# and everything under it.
_wbm_hash_root_applies() {
  [ -n "${FMS_HASH_ROOT_PATHS:-}" ] || return 0
  _hra_rel="$1"
  _hra_oldIFS="$IFS"
  IFS='
'
  for _hra_p in $FMS_HASH_ROOT_PATHS; do
    [ -n "$_hra_p" ] || continue
    case "$_hra_rel" in
      "$_hra_p"|"$_hra_p"/*)
        IFS="$_hra_oldIFS"
        return 0
        ;;
    esac
  done
  IFS="$_hra_oldIFS"
  return 1
}

# May this relpath be serialized as a LINK record? UNSET FMS_LINK_PATHS means
# ANY live symlink may — correct on the INSTALL path, where the installer
# itself created every symlink it is about to record. On the UPGRADE rewrite
# that default is too wide (codex W1 round 10, P2): FMS_MODE=link is inferred
# from the presence of ANY prior LINK record, and every live symlink then
# serializes as a delivery record — including an adopter's OWN symlink
156:MANIFEST="$TARGET/.claude/.install-manifest.sha256"

exec
/bin/zsh -lc "sed -n '130,280p' scripts/uninstall.sh" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
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
  exit 0
fi

# Clean up manifest + empty .claude/ subdirs (only if everything matched)
if ! _dry "would REMOVE manifest $MANIFEST"; then
  if [ "$mismatch_count" -eq 0 ] || [ "$FORCE" -eq 1 ]; then
    rm -f "$MANIFEST"
  fi
fi

# Clean up empty directories under .claude/ (post-removal sweep)
if [ "$DRY_RUN" -eq 0 ] && [ -d "$TARGET/.claude" ]; then
  find "$TARGET/.claude" -depth -type d -empty -delete 2>/dev/null || true
fi

_log ""
_log "==> Uninstall summary:"
_log "    Removed:   $removed_count"
_log "    Preserved: $preserved_count"
_log "    Absent:    $absent_count"

exec
/bin/zsh -lc "git diff -- scripts/upgrade.sh | sed -n '1,520p'" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-mPHfaedU' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-jeJ0FETR' (errno=Operation not permitted)
diff --git a/scripts/upgrade.sh b/scripts/upgrade.sh
index 0ec7c4b..8f98d6b 100755
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
@@ -1482,72 +1561,561 @@ To pull updates:
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

exec
/bin/zsh -lc "git diff -- scripts/upgrade.sh | sed -n '521,1040p'" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-Bfy5DLgU' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-EO9YKeoY' (errno=Operation not permitted)
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
+          _up_record_op "preserve_spec_v1_backup_failed" "SPEC/v1"
+          [ "$_pr" = "hash" ] && _SPEC_DELIVERED=1
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
+          _up_record_op "preserve_spec_v1_backup_failed" "SPEC/v1"
+          [ "$_pr" = "hash" ] && _SPEC_DELIVERED=1
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
+          _up_record_op "preserve_marker_backup_failed" ".claude/.framework-version"
+          [ "$_pr" = "hash" ] && _MARKER_DELIVERED=1
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
@@ -2436,9 +3004,61 @@ _migrate_settings_baseline
 
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
+  _refresh_protocol_pointer
+  # Registered delivery for the baseline rewrite below: on this path the
+  # refresh either WROTE the pointer or PRESERVED a customized one that the
+  # baseline already records (the preserve branch requires a baseline hit),
+  # so framework ownership holds in every non-user branch.
+  _PROTOCOL_DELIVERED=1
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
@@ -2465,14 +3085,60 @@ if [[ "$DRY_RUN" -eq 0 ]] && command -v _write_baseline_manifest >/dev/null 2>&1
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
@@ -2505,6 +3171,7 @@ _write_upgrade_state() {
     "replay_source" "$_REPLAY_SOURCE"
     "harness" "$HARNESS"
     "managed_hooks" "$CODEX_MANAGED_HOOKS"
+    "ceremony_effective" "$CEREMONY_EFFECTIVE"
   )
   echo ""
   echo "==> (Re)writing install-state (.claude/.install-state.json — PLAN-153 Wave B)"
@@ -2597,6 +3264,7 @@ state = {
         "on_conflict": vals.get("on_conflict", ""),
         "pin": vals.get("pin", ""),
         "replay_source": vals.get("replay_source", ""),
+        "ceremony_effective": vals.get("ceremony_effective", ""),
     },
     "operations": ops,
     "result": {"upgrade_succeeded": True,

exec
/bin/zsh -lc "grep -R \"_PROTOCOL_DELIVERED\\|_SPEC_DELIVERED\\|_MARKER_DELIVERED\\|_PROTOCOL_HASH_SOURCE\" -n scripts/upgrade.sh" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
scripts/upgrade.sh:1594:  _PROTOCOL_HASH_SOURCE="${_pair##* }"
scripts/upgrade.sh:1614:      _PROTOCOL_DELIVERED=1
scripts/upgrade.sh:1648:      _PROTOCOL_DELIVERED=1
scripts/upgrade.sh:1875:_SPEC_DELIVERED=0
scripts/upgrade.sh:1914:      _SPEC_DELIVERED=1
scripts/upgrade.sh:1981:          [ "$_pr" = "hash" ] && _SPEC_DELIVERED=1
scripts/upgrade.sh:1995:          [ "$_pr" = "hash" ] && _SPEC_DELIVERED=1
scripts/upgrade.sh:2002:      _SPEC_DELIVERED=1
scripts/upgrade.sh:2016:_MARKER_DELIVERED=0
scripts/upgrade.sh:2055:      _MARKER_DELIVERED=1
scripts/upgrade.sh:2099:          [ "$_pr" = "hash" ] && _MARKER_DELIVERED=1
scripts/upgrade.sh:2109:        _MARKER_DELIVERED=1
scripts/upgrade.sh:3013:_PROTOCOL_DELIVERED=0
scripts/upgrade.sh:3036:      _PROTOCOL_DELIVERED=1
scripts/upgrade.sh:3049:  _PROTOCOL_DELIVERED=1
scripts/upgrade.sh:3135:  export FMS_HASH_SOURCE_PROTOCOL="${_PROTOCOL_HASH_SOURCE:-}"
scripts/upgrade.sh:3136:  export FMS_DELIVERED_SPEC="${_SPEC_DELIVERED:-0}"
scripts/upgrade.sh:3137:  export FMS_DELIVERED_PROTOCOL="${_PROTOCOL_DELIVERED:-0}"
scripts/upgrade.sh:3138:  export FMS_DELIVERED_MARKER="${_MARKER_DELIVERED:-0}"

exec
/bin/zsh -lc 'grep -n "_lg_ancestor_is_symlink" -A45 -B5 scripts/upgrade.sh; grep -n "_BASELINE_MANIFEST_FILE" scripts/upgrade.sh | head -30' in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
1264-# SYMLINK must be an opaque leaf: a -f/-d/-L test (or rm/rmdir) on a path
1265-# that runs THROUGH it resolves into the link TARGET, so an unguarded
1266-# prune could delete adopter data OUTSIDE the tree. Every prune-side
1267-# test/delete on "$TARGET/$rel" must first pass this lstat-walk guard.
1268-# bash 3.2-safe: pure string splitting, [[ -L ]] never follows the leaf.
1269:_lg_ancestor_is_symlink() {
1270-  local _as_root="$1" _as_rel="$2" _as_walk=""
1271-  while [[ "$_as_rel" == */* ]]; do
1272-    _as_walk="${_as_walk:+$_as_walk/}${_as_rel%%/*}"
1273-    _as_rel="${_as_rel#*/}"
1274-    if [[ -L "$_as_root/$_as_walk" ]]; then return 0; fi
1275-  done
1276-  return 1
1277-}
1278-
1279-backup_and_replace() {
1280-  local rel_path="$1"
1281-  local src="$SOURCE_DIR/$rel_path"
1282-  local dst="$TARGET/$rel_path"
1283-  local bak="$BAK_DIR/$rel_path"
1284-
1285-  if [[ ! -e "$src" ]]; then
1286-    echo "    SKIP (source missing): $rel_path"
1287-    return
1288-  fi
1289-
1290-  _up_record_op "refresh_target" "$rel_path"
1291-
1292-  # F-CHAOS-3: warn the Owner about any customization we're about to
1293-  # clobber, BEFORE the overwrite takes place. The backup under
1294-  # $BAK_DIR is still the rollback path, but the warning surfaces the
1295-  # diff at the moment it happens — without requiring the Owner to
1296-  # notice it via `git diff` later.
1297-  _emit_diff_warnings "$rel_path"
1298-
1299-  # Honour --skip for top-level files/dirs too
1300-  if _path_is_skipped "$rel_path"; then
1301-    echo "    SKIPPED (--skip): $rel_path"
1302-    return
1303-  fi
1304-
1305-  if [[ "$DRY_RUN" -eq 1 ]]; then
1306-    # PLAN-161 U1 (codex r1 F4): classification-aware preview for single-FILE
1307-    # targets when a baseline manifest is loaded — the dry-run log must PROVE
1308-    # the provenance classifier still runs (byte-identity alone would pass on
1309-    # a dry-run that silently lost classification). DIRECTORY targets keep
1310-    # the legacy one-line preview.
1311-    if [[ -f "$dst" && -f "$src" && -n "$_BASELINE_MANIFEST_FILE" ]]; then
1312-      local _drv
1313-      _drv="$( _classify_against_baseline "$rel_path" )"
1314-      case "$_drv" in
--
1488-        _pr_rel="${_pr_hit#"$SOURCE_DIR"/}"
1489-        if _framework_path_excluded "$_pr_rel"; then
1490-          # F11a: never test or delete THROUGH a symlinked ancestor — the
1491-          # dst path would resolve into the link target (adopter data
1492-          # possibly outside the tree). Preserved symlink == opaque leaf.
1493:          if _lg_ancestor_is_symlink "$TARGET" "$_pr_rel"; then continue; fi
1494-          # Leaf: -L before -f (lstat-first; -f alone would follow a link).
1495-          if [[ -L "$TARGET/$_pr_rel" || -f "$TARGET/$_pr_rel" ]]; then
1496-            if [[ -n "$_lg_survivors" ]] \
1497-               && grep -Fxq "$_pr_rel" "$_lg_survivors" 2>/dev/null; then
1498-              :  # pre-existing excluded content — keep exactly as-is (F11)
1499-            else
1500-              rm -f "$TARGET/$_pr_rel"
1501-            fi
1502-          fi
1503-        fi
1504-      done < <( find "$src" \( -type f -o -type l \) -print 2>/dev/null )
1505-      # Remove the now-empty excluded dirs, children before parents (-depth)
1506-      # — but never a recorded survivor dir (pre-existing, adopter-held).
1507-      while IFS= read -r _pr_hit; do
1508-        [[ -n "$_pr_hit" ]] || continue
1509-        _pr_rel="${_pr_hit#"$SOURCE_DIR"/}"
1510-        # F11a: ancestor-symlink guard first, then -L BEFORE -d (lstat-first
1511-        # — -d follows a leaf symlink; a preserved excluded symlink-to-dir
1512-        # must be kept whole and its target never rmdir'd).
1513-        if _framework_path_excluded "$_pr_rel" \
1514:           && ! _lg_ancestor_is_symlink "$TARGET" "$_pr_rel" \
1515-           && [[ ! -L "$TARGET/$_pr_rel" && -d "$TARGET/$_pr_rel" ]]; then
1516-          if [[ -n "$_lg_survivors" ]] \
1517-             && grep -Fxq "$_pr_rel" "$_lg_survivors" 2>/dev/null; then
1518-            :  # pre-existing excluded dir — keep (F11)
1519-          else
1520-            rmdir "$TARGET/$_pr_rel" 2>/dev/null || true
1521-          fi
1522-        fi
1523-      done < <( find "$src" -depth -type d -print 2>/dev/null )
1524-    fi
1525-  else
1526-    cp "$src" "$dst"
1527-  fi
1528-  if [[ -n "$_lg_survivors" ]]; then
1529-    rm -f "$_lg_survivors"
1530-  fi
1531-  echo "    UPDATED: $rel_path"
1532-}
1533-
1534-# DevOps-P1-4: refresh PROTOCOL.md pointer on upgrade. This is
1535-# framework-derived content (not user data), so preserving it as-is
1536-# across upgrades traps stale pointers when the framework moves. We
1537-# regenerate it with the same heuristic install.sh uses.
1538-_refresh_protocol_pointer() {
1539-  local pointer="$TARGET/PROTOCOL.md"
1540-  local body
1541-  case "$SOURCE_DIR" in
1542-    "$TARGET"/*)
1543-      local rel="${SOURCE_DIR#$TARGET/}"
1544-      body="The full CEO orchestration protocol lives at:
1545-./${rel}/PROTOCOL.md
1546-
1547-To pull updates:
1548-  ( cd ./${rel} && git pull )
1549-  ./${rel}/scripts/upgrade.sh . --profile $PROFILE --stack $STACK"
1550-      ;;
1551-    *)
1552-      body="The full CEO orchestration protocol lives at:
1553-{{PROTOCOL_SOURCE}}/PROTOCOL.md
1554-
1555-Edit {{PROTOCOL_SOURCE}} to point at your ceo-orchestration checkout
1556-(e.g. ../ceo-orchestration or \$HOME/src/ceo-orchestration).
1557-
1558-To pull updates:
1559-  ( cd {{PROTOCOL_SOURCE}} && git pull )
--
1880-
1881-  # ---- OBSERVE -------------------------------------------------------------
1882-  # Nothing here chooses an outcome. Each line answers one question about the
1883-  # world, and the answers go to _ownership_verdict as the nine dimensions.
1884-  local _lt _pr _lc _sh _md _sk
1885:  if _lg_ancestor_is_symlink "$TARGET" "SPEC/v1"; then
1886-    _lt="ancestor_symlink"           # reachable only by writing THROUGH a symlink
1887-  else
1888-    _lt="$( _ov_obs_live_type "$ddir" )"
1889-  fi
1890-  _pr="$( _ov_obs_prior_record "SPEC/v1" )"
1891-  _lc="$( _ov_obs_spec_content )"
1892-  _sh=no; [ -d "$sdir" ] && _sh=yes
1893-  _md="$( _ov_obs_mode )"
1894-  _sk="$( _ov_obs_skip "SPEC/v1" )"
1895-
1896-  # ---- DECIDE --------------------------------------------------------------
1897-  local _pair _verdict _hash
1898-  if ! _pair="$( _ownership_verdict spec "$_pr" "$_lt" "$_lc" "$_sh" "$_md" \
1899-                   "$CEREMONY_EFFECTIVE" upgrade "$_sk" )"; then
1900-    # The decision function refuses combinations its legality rules forbid.
1901-    # Fail toward preserve — under-claiming is recoverable, over-claiming is
1902-    # the delete-the-adopter's-file class (ADR-155-AMEND-1 §3).
1903-    echo "    WARNING: SPEC/v1 dimensions are not a legal cell" >&2
1904-    echo "             ($_pr/$_lt/$_lc/$_sh/$_md/$CEREMONY_EFFECTIVE/$_sk) —" >&2
1905-    echo "             PRESERVED without ownership. Please report this combination." >&2
1906-    return 0
1907-  fi
1908-  _verdict="${_pair%% *}"; _hash="${_pair##* }"
1909-  _SPEC_HASH_SOURCE="$_hash"   # consumed by the baseline rewrite
1910-
1911-  # ---- EXECUTE -------------------------------------------------------------
1912-  case "$_verdict" in
1913-    PRESERVE_OWNED)
1914-      _SPEC_DELIVERED=1
1915-      case "$_lt/$_sk/$_sh" in
1916-        ancestor_symlink/*/*) echo "    SKIP: SPEC/v1 has a symlinked ancestor (refusing to write through it — F11a)" ;;
1917-        symlink/*/*)          echo "    SKIP: SPEC/v1 is the recorded --mode link delivery (target unchanged)" ;;
1918-        */self/*)             echo "    SKIPPED (--skip): SPEC/v1" ;;
1919-        */descendant/*)       echo "    SKIPPED (--skip matches a descendant): SPEC/v1 refreshes as ONE contract unit — preserving the whole tree" ;;
1920-        */*/no)               echo "    SKIP: SPEC/v1 absent in source (ownership carried forward)" ;;
1921-        *)                    echo "    SKIP: SPEC/v1 (recorded --ceremony user install — root surfaces are out of scope, WS4)" ;;
1922-      esac
1923-      return 0
1924-      ;;
1925-
1926-    PRESERVE_UNOWNED|OMIT_RECORD)
1927-      # An adopter-owned surface. The ONLY case that earns a snapshot plus
1928-      # recovery guidance is the true ADOPTER-FORK: content the framework
1929-      # cannot claim, with no gate having refused first.
1930-      if [ "$_lt" = "dir" ] || [ "$_lt" = "dir_empty" ]; then
--
2019-  local dst="$TARGET/.claude/.framework-version"
2020-  local bak="$BAK_DIR/.claude/.framework-version"
2021-
2022-  # ---- OBSERVE -------------------------------------------------------------
2023-  local _lt _pr _lc _sh _md _sk
2024:  if _lg_ancestor_is_symlink "$TARGET" ".claude/.framework-version"; then
2025-    _lt="ancestor_symlink"
2026-  else
2027-    _lt="$( _ov_obs_live_type "$dst" )"
2028-  fi
2029-  _pr="$( _ov_obs_prior_record ".claude/.framework-version" )"
2030-  _sh=no; [ -f "$src" ] && _sh=yes
2031-  if [ ! -e "$dst" ] || [ -L "$dst" ]; then
2032-    _lc="-"
2033-  elif [ "$_sh" = yes ] && cmp -s "$src" "$dst" 2>/dev/null; then
2034-    _lc="pristine"
2035-  else
2036-    _lc="edited"
2037-  fi
2038-  _md="$( _ov_obs_mode )"
2039-  _sk="$( _ov_obs_skip ".claude/.framework-version" )"
2040-
2041-  # ---- DECIDE --------------------------------------------------------------
2042-  local _pair _verdict
2043-  if ! _pair="$( _ownership_verdict marker "$_pr" "$_lt" "$_lc" "$_sh" "$_md" \
2044-                   "$CEREMONY_EFFECTIVE" upgrade "$_sk" )"; then
2045-    echo "    WARNING: .claude/.framework-version dimensions are not a legal cell" >&2
2046-    echo "             — PRESERVED without ownership. Please report this combination." >&2
2047-    return 0
2048-  fi
2049-  _verdict="${_pair%% *}"
2050-  _MARKER_HASH_SOURCE="${_pair##* }"
2051-
2052-  # ---- EXECUTE -------------------------------------------------------------
2053-  case "$_verdict" in
2054-    PRESERVE_OWNED)
2055-      _MARKER_DELIVERED=1
2056-      case "$_lt/$_sk" in
2057-        ancestor_symlink/*) echo "    SKIP: .claude/.framework-version has a symlinked ancestor (refusing to write through it — F11a)" ;;
2058-        symlink/*)          echo "    SKIP: .claude/.framework-version is the recorded --mode link delivery (target unchanged)" ;;
2059-        */self)             echo "    SKIPPED (--skip): .claude/.framework-version" ;;
2060-        *)                  echo "    SKIP: .claude/.framework-version (ownership carried forward)" ;;
2061-      esac
2062-      return 0
2063-      ;;
2064-
2065-    OMIT_RECORD|PRESERVE_UNOWNED)
2066-      if [ "$_sh" = no ]; then
2067-        # The documented --pin downgrade: this source predates the marker, so a
2068-        # retained record would keep advertising a newer version over older
2069-        # content. Readers fall back to VERSION, which the pin DID update.
836:_BASELINE_MANIFEST_FILE=""   # set to the sanitized temp file if a manifest loads
903:# empty after sanitization) leaves _BASELINE_MANIFEST_FILE empty => fallback.
1015:    _BASELINE_MANIFEST_FILE="$sanitized"
1029:  [ -n "$_BASELINE_MANIFEST_FILE" ] || return 1
1030:  [ -f "$_BASELINE_MANIFEST_FILE" ] || return 1
1052:  ' "$_BASELINE_MANIFEST_FILE" 2>/dev/null )"
1093:if [ -n "$_BASELINE_MANIFEST_FILE" ]; then
1311:    if [[ -f "$dst" && -f "$src" && -n "$_BASELINE_MANIFEST_FILE" ]]; then
1338:  if [[ -d "$dst" && -d "$src" && -n "$_BASELINE_MANIFEST_FILE" ]]; then
1352:  if [[ -f "$dst" && -f "$src" && -n "$_BASELINE_MANIFEST_FILE" ]]; then
1666:  [[ -n "$_BASELINE_MANIFEST_FILE" && -f "$_BASELINE_MANIFEST_FILE" ]] || return 1
1672:  grep -Eq '^([0-9a-f]{64}|LINK)  SPEC/v1(/|  |$)' "$_BASELINE_MANIFEST_FILE" 2>/dev/null
1675:  [[ -n "$_BASELINE_MANIFEST_FILE" && -f "$_BASELINE_MANIFEST_FILE" ]] || return 1
1676:  grep -Eq '^([0-9a-f]{64}|LINK)  \.claude/\.framework-version(  |$)' "$_BASELINE_MANIFEST_FILE" 2>/dev/null
1683:  [[ -n "$_BASELINE_MANIFEST_FILE" && -f "$_BASELINE_MANIFEST_FILE" ]] || return 1
1684:  grep -Eq '^([0-9a-f]{64}|LINK)  PROTOCOL\.md(  |$)' "$_BASELINE_MANIFEST_FILE" 2>/dev/null
1782:  [ -n "${_BASELINE_MANIFEST_FILE:-}" ] && [ -f "$_BASELINE_MANIFEST_FILE" ] || { printf 'none'; return 0; }
1783:  _opr_link="$( grep -E "^LINK  ${_opr_rel}  " "$_BASELINE_MANIFEST_FILE" 2>/dev/null | head -1 || true )"
1794:  if grep -Eq "^[0-9a-f]{64}  ${_opr_rel}(/|$)" "$_BASELINE_MANIFEST_FILE" 2>/dev/null; then
1847:  if [ -n "${_BASELINE_MANIFEST_FILE:-}" ] && [ -f "$_BASELINE_MANIFEST_FILE" ] \
1848:     && grep -Eq '^LINK  ' "$_BASELINE_MANIFEST_FILE" 2>/dev/null; then
3035:       || grep -Eq '^LINK  PROTOCOL\.md(  |$)' "$_BASELINE_MANIFEST_FILE" 2>/dev/null; then
3096:  if [[ -n "$_BASELINE_MANIFEST_FILE" && -f "$_BASELINE_MANIFEST_FILE" ]] \
3097:     && grep -Eq '^LINK  ' "$_BASELINE_MANIFEST_FILE" 2>/dev/null; then
3113:      }' "$_BASELINE_MANIFEST_FILE" 2>/dev/null || true )"
3132:  export FMS_PRIOR_MANIFEST="${_BASELINE_MANIFEST_FILE:-}"

exec
/bin/zsh -lc "sed -n '820,1110p' scripts/upgrade.sh; grep -n \"trap\\|_BASELINE_TMP\" scripts/upgrade.sh | head -50; sed -n '1,130p' scripts/upgrade.sh" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:

# ===========================================================================
# PLAN-138 Wave C (ADR-155) — baseline manifest load + per-file classifier.
# ===========================================================================
# Read $TARGET/.claude/.install-manifest.sha256 ONCE at startup into a
# validated, sanitized lookup file. Every line is re-validated here against the
# two accepted record grammars; any line that matches NEITHER, or whose relpath
# is absolute / contains `..` / control chars / duplicates an earlier relpath /
# traverses a symlinked component, is DROPPED so it can never drive a silent
# FRAMEWORK-CHANGED branch (CWE-345/494/22 provenance hardening). The raw
# manifest is NEVER piped into `shasum -c`; classification recomputes +
# compares in-process per validated relpath.
#
# bash 3.2-safe: no associative arrays. The validated manifest is a temp file;
# lookups use a fixed-string, line-anchored grep.
_BASELINE_MANIFEST_RAW="$TARGET/.claude/.install-manifest.sha256"
_BASELINE_MANIFEST_FILE=""   # set to the sanitized temp file if a manifest loads
_BASELINE_DUP_GUARD=""       # newline-list of relpaths already accepted (dup detection)
_BASELINE_INVALID=""         # newline-list of relpaths seen >1x: AMBIGUOUS provenance,
                             # rejected entirely (NOT first-wins) — Codex R1 P0#2 fold.

# Reject a relpath that is unsafe to trust from the manifest. Returns 0 (reject)
# / 1 (accept). Checks: absolute, `..` segment, control chars, and a symlinked
# component anywhere along the path under $TARGET (lstat per component, never
# follow). Duplicate relpaths are rejected by the caller via _BASELINE_DUP_GUARD.
#
# $2 = record KIND, mirroring doctor.sh `_relpath_unsafe` (family sweep):
# "link" tolerates a symlinked LEAF, anything else (default "file") does not.
# A `LINK  <relpath>  <target>` record describes a --mode link delivery whose
# leaf IS a symlink by construction, so rejecting it here silently dropped the
# record from the sanitized manifest: _baseline_has_spec_record and both
# readlink-vs-recorded-target checks could then NEVER match, and every
# link-mode upgrade lost framework ownership of SPEC/v1 and the marker, with
# marker-first readers falling back to the stale root VERSION (codex W1
# round 6, P2). The leaf is never FOLLOWED here — validation stays at the
# consumers, which compare `readlink` against the recorded target. Hash
# records keep the strict leaf check: a managed regular file swapped for a
# symlink must not retain its record (_hash_file WOULD follow it). Symlinked
# PARENT components remain a genuine traversal hazard for both kinds.
_baseline_relpath_unsafe() {
  _bru_rel="$1"
  _bru_kind="${2:-file}"
  case "$_bru_rel" in
    /*) return 0 ;;                       # absolute
    *..*) return 0 ;;                      # parent traversal (covers ../ and /..)
  esac
  # Control chars / whitespace-only / empty.
  case "$_bru_rel" in
    ""|*[$'\n\r\t']*) return 0 ;;
  esac
  # Count the significant components first, so the leaf can be identified by
  # INDEX — reconstructing "$TARGET/$_bru_rel" for a leaf test would differ
  # from the walk on `./` and trailing-slash forms.
  _bru_n=0
  _bru_oldIFS="$IFS"
  IFS='/'
  for _bru_comp in $_bru_rel; do
    [ -n "$_bru_comp" ] || continue
    [ "$_bru_comp" = "." ] && continue
    _bru_n=$(( _bru_n + 1 ))
  done
  # Symlinked-component check: walk each path component under $TARGET; if any
  # EXISTING component is a symlink, reject (do not follow it).
  _bru_cur="$TARGET"
  _bru_i=0
  for _bru_comp in $_bru_rel; do
    [ -n "$_bru_comp" ] || continue
    [ "$_bru_comp" = "." ] && continue
    _bru_i=$(( _bru_i + 1 ))
    _bru_cur="$_bru_cur/$_bru_comp"
    if [ -L "$_bru_cur" ]; then
      if [ "$_bru_kind" = "link" ] && [ "$_bru_i" -eq "$_bru_n" ]; then
        continue                          # the LINK record's own leaf
      fi
      IFS="$_bru_oldIFS"
      return 0
    fi
  done
  IFS="$_bru_oldIFS"
  return 1
}

# Load + sanitize the baseline manifest. On any problem (absent / unreadable /
# empty after sanitization) leaves _BASELINE_MANIFEST_FILE empty => fallback.
_load_baseline_manifest() {
  [ -f "$_BASELINE_MANIFEST_RAW" ] && [ -r "$_BASELINE_MANIFEST_RAW" ] || return 0
  command -v _hash_file >/dev/null 2>&1 || return 0

  # PLAN-161 U1: the sanitized manifest used to be mktemp'd INSIDE $BAK_DIR —
  # a write inside the target even under --dry-run (and the reason dry-run
  # could not keep classification alive once BAK_DIR creation was gated). It
  # now lives in a secure temp OUTSIDE $TARGET in ALL runs; the composed
  # _upgrade_cleanup EXIT trap reaps it via the _BASELINE_TMP_FILE global.
  #
  # PLAN-161 U1 (codex r1 F5): "outside $TARGET" must hold even when the
  # CALLER's TMPDIR is $TARGET or lies under it — otherwise --dry-run writes
  # in the target again. Resolve the tmp base physically (cd + pwd -P) and
  # prefix-check it against the physically-resolved $TARGET (trailing-slash
  # safe case glob, bash-3.2-safe); on equal-or-under, fall back to /tmp.
  # If the base cannot be resolved (nonexistent), leave it — mktemp fails
  # below and we return 0 (the existing no-manifest fallback).
  local _lbm_base _lbm_base_abs _lbm_target_abs
  _lbm_base="${TMPDIR:-/tmp}"
  _lbm_base_abs="$( cd "$_lbm_base" 2>/dev/null && pwd -P )" || _lbm_base_abs=""
  _lbm_target_abs="$( cd "$TARGET" 2>/dev/null && pwd -P )" || _lbm_target_abs=""
  if [[ -n "$_lbm_base_abs" && -n "$_lbm_target_abs" ]]; then
    case "${_lbm_base_abs%/}/" in
      "${_lbm_target_abs%/}/"*) _lbm_base="/tmp" ;;
    esac
  fi
  local sanitized
  sanitized="$( mktemp "$_lbm_base/ceo-baseline-manifest.XXXXXX" 2>/dev/null )" || return 0
  _BASELINE_TMP_FILE="$sanitized"

  local line rest rel digest target
  # Read line-by-line; NEVER `eval` or interpret manifest content.
  while IFS= read -r line || [ -n "$line" ]; do
    [ -n "$line" ] || continue
    # Hash record: ^<64hex><2 spaces><relpath>$
    # Link record: ^LINK<2 spaces><relpath><2 spaces><target>$
    case "$line" in
      LINK\ \ *)
        rest="${line#LINK  }"
        # relpath is everything up to the FIRST double-space; target the rest.
        case "$rest" in
          *"  "*)
            rel="${rest%%  *}"
            target="${rest#*  }"
            ;;
          *) continue ;;   # malformed LINK (no target) — drop
        esac
        # KIND=link: the leaf of a LINK record IS a symlink by construction
        # (codex W1 round 6, P2). Symlinked PARENTS still reject.
        if _baseline_relpath_unsafe "$rel" link; then continue; fi
        # Duplicate relpath? Ambiguous provenance — invalidate the relpath
        # ENTIRELY (not first-wins): the lookup will refuse it -> fallback.
        case "$_BASELINE_DUP_GUARD" in
          *"
$rel
"*)
            case "$_BASELINE_INVALID" in
              *"
$rel
"*) ;;
              *) _BASELINE_INVALID="$_BASELINE_INVALID
$rel
" ;;
            esac
            continue ;;
        esac
        _BASELINE_DUP_GUARD="$_BASELINE_DUP_GUARD
$rel
"
        # Re-emit a normalized LINK record (target sanitized of control chars).
        case "$target" in
          *[$'\n\r\t']*) continue ;;
        esac
        printf 'LINK  %s  %s\n' "$rel" "$target" >> "$sanitized"
        ;;
      *)
        # Must be exactly 64-hex, two spaces, then relpath.
        digest="${line%%  *}"
        rel="${line#*  }"
        # Guard: the split must have actually found a double-space separator.
        [ "$digest" != "$line" ] || continue
        case "$digest" in
          [0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f][0-9a-f]) ;;
          *) continue ;;   # not a 64-hex digest — drop (provenance)
        esac
        if _baseline_relpath_unsafe "$rel"; then continue; fi
        # Duplicate relpath? Ambiguous provenance — invalidate ENTIRELY
        # (not first-wins): the lookup refuses it -> fallback. (Codex R1 P0#2)
        case "$_BASELINE_DUP_GUARD" in
          *"
$rel
"*)
            case "$_BASELINE_INVALID" in
              *"
$rel
"*) ;;
              *) _BASELINE_INVALID="$_BASELINE_INVALID
$rel
" ;;
            esac
            continue ;;
        esac
        _BASELINE_DUP_GUARD="$_BASELINE_DUP_GUARD
$rel
"
        printf '%s  %s\n' "$digest" "$rel" >> "$sanitized"
        ;;
    esac
  done < "$_BASELINE_MANIFEST_RAW"

  if [ -s "$sanitized" ]; then
    _BASELINE_MANIFEST_FILE="$sanitized"
  else
    rm -f "$sanitized" 2>/dev/null || true
  fi
  return 0
}

# Echo the baseline digest for $1 if (and only if) it is a validated HASH
# record. A LINK record or an absent line echoes nothing + returns 1 => the
# caller falls back. Exact relpath match (the part after the two-space
# separator must equal $1 exactly). awk does the exact match + 64-hex check in
# one pass — no fragile nested while/case under set -u.
_baseline_lookup() {
  _bl_rel="$1"
  [ -n "$_BASELINE_MANIFEST_FILE" ] || return 1
  [ -f "$_BASELINE_MANIFEST_FILE" ] || return 1
  # Refuse a relpath flagged as duplicate/ambiguous during load (Codex R1 P0#2):
  # never trust a baseline digest for a relpath that appeared more than once.
  case "$_BASELINE_INVALID" in
    *"
$_bl_rel
"*) return 1 ;;
  esac
  _bl_digest="$( awk -v want="$_bl_rel" '
    {
      # Split on the FIRST double-space: field1 = digest-or-LINK, rest = path[+target].
      idx = index($0, "  ");
      if (idx == 0) next;
      d = substr($0, 1, idx - 1);
      rest = substr($0, idx + 2);
      if (d == "LINK") next;                 # link record: no content baseline
      # rest must equal the wanted relpath exactly (hash records have no 2nd
      # double-space: relpath runs to EOL).
      if (rest != want) next;
      if (length(d) != 64) next;
      if (d ~ /^[0-9a-f]+$/) { print d; exit 0 }
    }
  ' "$_BASELINE_MANIFEST_FILE" 2>/dev/null )"
  [ -n "$_bl_digest" ] || return 1
  printf '%s\n' "$_bl_digest"
}

# Classify a single repo-relative file against the baseline. Echoes ONE verdict:
#   FRAMEWORK-CHANGED  H_dst==H_base && H_src!=H_base  -> safe to auto-update
#   ADOPTER-CUSTOMIZED H_dst!=H_base && H_src==H_base  -> preserve
#   CONFLICT           both differ from H_base         -> --on-conflict
#   IDENTICAL          H_dst==H_src                    -> nothing to do
#   FALLBACK           no usable baseline / hasher      -> today's behavior
# H_dst and H_src are BOTH recomputed from disk THIS run (never cached H_src).
_classify_against_baseline() {
  _cab_rel="$1"
  command -v _hash_file >/dev/null 2>&1 || { printf 'FALLBACK\n'; return 0; }
  _cab_base="$( _baseline_lookup "$_cab_rel" )" || { printf 'FALLBACK\n'; return 0; }
  _cab_dst="$( _hash_file "$TARGET/$_cab_rel" 2>/dev/null || true )"
  _cab_src="$( _hash_file "$SOURCE_DIR/$_cab_rel" 2>/dev/null || true )"
  # If either side cannot be hashed (missing file), fall back to legacy handling.
  if [ -z "$_cab_dst" ] || [ -z "$_cab_src" ]; then
    printf 'FALLBACK\n'; return 0
  fi
  if [ "$_cab_dst" = "$_cab_src" ]; then
    printf 'IDENTICAL\n'; return 0
  fi
  if [ "$_cab_dst" = "$_cab_base" ] && [ "$_cab_src" != "$_cab_base" ]; then
    printf 'FRAMEWORK-CHANGED\n'; return 0
  fi
  if [ "$_cab_dst" != "$_cab_base" ] && [ "$_cab_src" = "$_cab_base" ]; then
    printf 'ADOPTER-CUSTOMIZED\n'; return 0
  fi
  # Both differ from the baseline.
  printf 'CONFLICT\n'; return 0
}

_load_baseline_manifest

# PLAN-161 U1 (codex r1 F4) — manifest-load observability. Byte-identity alone
# cannot prove a --dry-run kept provenance classification alive (a dry-run
# that silently lost the baseline would also write nothing), so EVERY run
# states which classification mode it operates in.
if [ -n "$_BASELINE_MANIFEST_FILE" ]; then
  echo "==> Baseline manifest: loaded (provenance classification ACTIVE)"
else
  echo "==> Baseline manifest: none — fallback diff -q classification"
fi

# F-CHAOS-3: match a relative path against the --skip globs list.
# Returns 0 (true) if matched.
_path_is_skipped() {
  local rel="$1"
  local pattern
  for pattern in "${SKIP_GLOBS[@]:-}"; do
    [[ -n "$pattern" ]] || continue
    # Intentional unquoted glob match (the whole point of --skip patterns).
    # shellcheck disable=SC2053,SC2254
    case "$rel" in
      $pattern) return 0 ;;
    esac
563:# to install an inline EXIT trap restoring the source branch; any later plain
564:# `trap ... EXIT` would CLOBBER it. All exit-time duties now live in this
570:_BASELINE_TMP_FILE=""
575:  if [[ -n "${_BASELINE_TMP_FILE:-}" ]]; then
576:    rm -f "$_BASELINE_TMP_FILE" 2>/dev/null || true
579:trap _upgrade_cleanup EXIT
619:  # _upgrade_cleanup EXIT trap installed above (PLAN-161 U1, codex r2 F4).
912:  # _upgrade_cleanup EXIT trap reaps it via the _BASELINE_TMP_FILE global.
932:  _BASELINE_TMP_FILE="$sanitized"
1536:# across upgrades traps stale pointers when the framework moves. We
1873:#     file (the S238/ADR-155 "verified worst case", trap C.5). See
#!/usr/bin/env bash
# upgrade.sh — update an existing ceo-orchestration install in a target repo
#
# Usage:
#   ./upgrade.sh <target-repo-path> [--profile <list>] [--stack <name>]
#                                    [--pin <tag>] [--dry-run]
#                                    [--skip <glob>] [--no-diff-warn]
#                                    [--no-deprecation-warn]
#
# What it does:
#   - Backs up the current .claude/team.md, .claude/frontend-team.md, .claude/skills/,
#     .claude/hooks/, .claude/scripts/, .claude/commands/, .claude/pitfalls-catalog.yaml,
#     .claude/task-chains.yaml to .claude.bak/{timestamp}/
#   - (F-CHAOS-3) Before overwriting any adopter file that differs from the source,
#     emits a `diff -q`-style WARNING line (shown on stderr) so the Owner is aware
#     a customization will be replaced. Pass --no-diff-warn to silence.
#     Pass --skip=<glob> to exclude files from the overwrite entirely (one --skip per pattern).
#   - Replaces them with the latest from this repo, respecting --profile and --stack
#   - Leaves CLAUDE.md, MEMORY.md, .claude/agent-metrics.md untouched — those are
#     user-customized files. .claude/settings.json is preserved as-is for its
#     existing keys, but the PLAN-135 W2 settings-merge step (below) ADDITIVELY
#     registers new framework lifecycle hooks into it (idempotent, non-clobbering).
#   - (DevOps-P1-4) Refreshes the PROTOCOL.md pointer to keep it aligned with the
#     current source layout (framework-derived content, not user data).
#   - (PLAN-135 W1 w0r) Pre-flight ADVISORY model-deprecation scan of the target
#     via .claude/scripts/check-model-deprecations.py when present: already-retired
#     or <=60-days-to-retirement Claude model ids emit stderr WARNING lines.
#     NEVER blocks the upgrade — any infra failure degrades to a NOTE (fail-open).
#     Pass --no-deprecation-warn to silence.
#   - (PLAN-135 W2 H8) Idempotent settings-merge step. install.sh EXISTS-SKIPs an
#     existing .claude/settings.json, so a fresh-install-only hook registration
#     never reaches the S217 population of existing adopters. This step registers
#     the new framework lifecycle hooks (today: the `Setup`/`init` post-install
#     self-verification hook check_setup_verification.py) into the adopter's
#     existing settings.json via an idempotent `jq` merge — additive, never
#     clobbers existing entries, re-applying is a no-op. Fail-open: missing jq /
#     malformed settings / merge error => stderr NOTE + the upgrade proceeds.
#     Pass --no-settings-merge to opt out.
#   - Owner-gated, no-silent-update: this script is NEVER auto-invoked. The Owner
#     runs it explicitly after a deliberate `git pull`; the framework never
#     self-updates or auto-downloads in the background (convergent with kooky's
#     manual-only update checker — see PLAN-125 WS-3c / E5).
#   - (PLAN-153 Wave B item B2) REPLAYS the RECORDED install request: when
#     $TARGET/.claude/.install-state.json (written by install.sh since Wave B;
#     schema ceo.install-state/v1) is present and valid, --profile/--stack
#     DEFAULT to the recorded request.profile/request.stack. Explicit flags
#     always win; --no-replay opts out entirely. BACK-COMPAT (debate C
#     must-fix): a missing state file (every pre-Wave-B install) or an
#     unreadable/invalid one NEVER errors and NEVER no-ops — the upgrade
#     proceeds exactly as before on the ADR-155 path (--dry-run previews +
#     the baseline drift-classifier below preserve/refuse customizations,
#     degrading to diff -q warn-then-clobber when no baseline manifest
#     exists either). After a successful non-dry upgrade the state file is
#     (re)written, so the pre-Wave-B population acquires one (mirrors
#     ADR-155 decision iv for the manifest). Replayed values are charset-
#     validated data — the state file is UNSIGNED and advisory, never a
#     trust anchor, and is never eval-ed.
#   - (PLAN-163 T5.4) BASELINE-AWARE SETTINGS MIGRATION: availableModels,
#     fallbackModel and permissions.defaultMode are migrated with an explicit
#     IDEMPOTENT 3-state policy PER LEAF KEY (absent -> write the new
#     baseline; equal to the OLD baseline (arrays byte-compared, exact order)
#     -> updated to the new baseline; customized -> PRESERVED + a named
#     WARNING). The new DirectoryAdded/Notification hook registrations are
#     added only when not yet registered AND the T3.4 version-floor feature
#     gate is on; customized registrations under the same events are always
#     preserved. Opt out with --no-settings-migrate. Oracles derive their
#     expectations from `upgrade.sh --print-settings-baselines` (the
#     normative table IS the artifact — literals are never re-hardcoded).
#   - (PLAN-164 W1, ADR-110-AMEND-1) PAIR-RAIL REGISTRATION-TIMEOUT VALUE
#     MIGRATION: the check_pair_rail.py PreToolUse registration timeout is
#     bumped to the template-derived cap IFF the adopter's current value is
#     one of the frozen SUPERSEDED SHIPPED caps (60 pre-PLAN-164; 150 from
#     PLAN-164/ADR-110-AMEND-1, shipped in v1.2.0 and superseded by
#     ADR-110-AMEND-2's 210); any other adopter-chosen value is
#     PRESERVED + a named WARNING; idempotent. Runs inside the same T5.4
#     migration step (same opt-out, same --dry-run preview); the NEW cap is
#     derived from templates/settings/settings.base.json, never hardcoded.
#
# Run after `git pull` in the source ceo-orchestration repo.

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
fi

# ===========================================================================
# PLAN-163 T5.4 — settings baseline-migration NORMATIVE TABLE (W0b literals).
# ---------------------------------------------------------------------------
# ONE source of truth for the baseline-aware settings migration below
# (_migrate_settings_baseline). Oracles derive their expectations from
# `upgrade.sh --print-settings-baselines` (this exact JSON) instead of
# hardcoding the literals — keep the table and the migration in lockstep.
# Order is NORMATIVE: new model ids are APPENDED AT THE END (the arrays are

exec
/bin/zsh -lc "cat scripts/tests/ownership_table.tsv; printf '\\n--- unit test ---\\n'; cat scripts/tests/test-ownership-verdict-unit.sh; printf '\\n--- ownership table test diff ---\\n'; git diff -- scripts/tests/test-ownership-table.sh scripts/tests/_parity_classify.py; printf '\\n--- spec e2e ---\\n'; sed -n '1,320p' scripts/tests/test-upgrade-spec-ownership.sh" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
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

--- unit test ---
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

--- ownership table test diff ---
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-VFvdabkH' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-3VvSvBSJ' (errno=Operation not permitted)
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

--- spec e2e ---
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

exec
/bin/zsh -lc "sed -n '1,760p' scripts/tests/test-ownership-table.sh" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
#!/usr/bin/env bash
# =============================================================================
# PLAN-167 W0.3 — ownership decision table runner.
#
# Executes EVERY legal cell of scripts/tests/ownership_table.tsv against the
# REAL scripts/install.sh and scripts/upgrade.sh. There is no mock of the
# subject under test: the fixture is a real target tree, the run is a real
# invocation, and the verdict is DERIVED from observable state, never parsed
# out of prose.
#
# Reasoning + dimension/enum definitions: docs/ownership-decision-table.md
#
# Usage:
#   test-ownership-table.sh              run every row
#   test-ownership-table.sh --only OWN-0013
#   test-ownership-table.sh --map        emit the map only (no pass/fail exit)
#   test-ownership-table.sh --list       list row ids and exit
#   test-ownership-table.sh --keep       keep the scratch dir (debugging)
#
# Exit: 0 = every row matched its expected pair. 1 = at least one mismatch.
#       2 = harness/usage error (never confused with a row failure).
#
# NOT `set -e`: this harness OBSERVES scripts that are expected to fail on
# some rows. Dying on their exit status would erase the observation.
# =============================================================================
set -uo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
REPO_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
TSV="$SCRIPT_DIR/ownership_table.tsv"

CELL_TIMEOUT="${CELL_TIMEOUT:-60}"
ONLY=""
MAP_ONLY=0
LIST_ONLY=0
KEEP=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --only) ONLY="${2:-}"; shift 2 ;;
    --map)  MAP_ONLY=1; shift ;;
    --list) LIST_ONLY=1; shift ;;
    --keep) KEEP=1; shift ;;
    -h|--help) sed -n '2,30p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) echo "ERROR: unknown argument: $1" >&2; exit 2 ;;
  esac
done

[[ -f "$TSV" ]] || { echo "ERROR: table not found: $TSV" >&2; exit 2; }

# --- framework hash helpers (the same ones the scripts use) ------------------
# shellcheck source=/dev/null
. "$REPO_ROOT/scripts/_hash_lib.sh" 2>/dev/null || {
  echo "ERROR: cannot source scripts/_hash_lib.sh" >&2; exit 2; }
command -v _hash_file  >/dev/null 2>&1 || { echo "ERROR: _hash_file missing"  >&2; exit 2; }
command -v _hash_stdin >/dev/null 2>&1 || { echo "ERROR: _hash_stdin missing" >&2; exit 2; }

# --- scratch ----------------------------------------------------------------
# NEVER $HOME, NEVER inside the repo (PLAN-167 W0.3 hard requirement).
WORK="$( mktemp -d "${TMPDIR:-/tmp}/plan167-own.XXXXXX" )" || exit 2
T="$WORK/t"                 # the ONE target path every row uses (see §fixtures)
cleanup() {
  [[ "$KEEP" -eq 1 ]] && { echo "scratch kept: $WORK" >&2; return; }
  chmod -R u+w "$WORK" 2>/dev/null || true
  rm -rf "$WORK" 2>/dev/null || true
}
trap cleanup EXIT

# --- portable timeout -------------------------------------------------------
# macOS ships no timeout(1). A cell that hangs (the FIFO class) must be killed,
# not waited on — two separate defects in this space were a blocking cp.
_TIMEOUT_BIN=""
if command -v timeout  >/dev/null 2>&1; then _TIMEOUT_BIN="timeout"
elif command -v gtimeout >/dev/null 2>&1; then _TIMEOUT_BIN="gtimeout"; fi

_run_with_timeout() {  # $1 = seconds; rest = command
  local secs="$1"; shift
  if [[ -n "$_TIMEOUT_BIN" ]]; then
    "$_TIMEOUT_BIN" "$secs" "$@"
    return $?
  fi
  # Fallback: background + watchdog. Kills the process group so a blocked cp
  # inside the script dies with it.
  "$@" &
  local pid=$!
  ( sleep "$secs"; kill -9 "$pid" 2>/dev/null ) &
  local watch=$!
  wait "$pid" 2>/dev/null
  local rc=$?
  kill "$watch" 2>/dev/null
  wait "$watch" 2>/dev/null
  return $rc
}

# --- surface geometry -------------------------------------------------------
_relpath_for() {
  case "$1" in
    spec)     printf 'SPEC/v1' ;;
    protocol) printf 'PROTOCOL.md' ;;
    marker)   printf '.claude/.framework-version' ;;
    *) return 1 ;;
  esac
}
MANIFEST_REL=".claude/.install-manifest.sha256"

# --- observation primitives -------------------------------------------------
_obs_type() {  # $1 = abs path -> the live_type vocabulary
  local p="$1"
  if   [[ -L "$p" ]]; then printf 'symlink'
  elif [[ ! -e "$p" ]]; then printf 'absent'
  elif [[ -d "$p" ]]; then
    if [[ -z "$( ls -A "$p" 2>/dev/null )" ]]; then printf 'dir_empty'; else printf 'dir'; fi
  elif [[ -p "$p" || -S "$p" || -b "$p" || -c "$p" ]]; then printf 'special'
  elif [[ -f "$p" ]]; then printf 'regular'
  else printf 'special'; fi
}

# Content digest of a surface, whatever its shape. Directory digest reproduces
# upgrade.sh's _spec_tree_fingerprint semantics (sorted "<sha>  <rel>" lines).
_obs_digest() {  # $1 = abs path
  local p="$1" lines
  if [[ -L "$p" ]]; then printf 'link:%s' "$( readlink "$p" 2>/dev/null || true )"; return 0; fi
  if [[ ! -e "$p" ]]; then printf 'absent'; return 0; fi
  if [[ -d "$p" ]]; then
    lines="$( ( cd "$p" && find . -type f -print 2>/dev/null ) | LC_ALL=C sort \
      | while IFS= read -r r; do
          [[ -n "$r" ]] || continue
          printf '%s  %s\n' "$( _hash_file "$p/$r" 2>/dev/null || echo FAIL )" "$r"
        done )"
    [[ -z "$lines" ]] && { printf 'emptydir'; return 0; }
    printf '%s' "$( printf '%s\n' "$lines" | _hash_stdin )"
    return 0
  fi
  if [[ -f "$p" ]]; then printf '%s' "$( _hash_file "$p" 2>/dev/null || echo UNREADABLE )"; return 0; fi
  printf 'special'
}

# Modification-time signature of a surface. BSD stat takes -f, GNU takes -c;
# both are tried so the harness behaves the same on macOS and CI.
_stat_mtime() {  # $1 = abs path
  stat -f '%m' "$1" 2>/dev/null || stat -c '%Y' "$1" 2>/dev/null || printf '0'
}
_obs_mtime() {  # $1 = abs path -> newest mtime under it (or its own)
  local p="$1" newest=0 m r
  if [[ -L "$p" || ! -e "$p" ]]; then printf '%s' "$( _stat_mtime "$p" )"; return 0; fi
  if [[ -d "$p" ]]; then
    while IFS= read -r r; do
      [[ -n "$r" ]] || continue
      m="$( _stat_mtime "$p/$r" )"
      [[ "$m" =~ ^[0-9]+$ ]] || continue
      (( m > newest )) && newest="$m"
    done < <( cd "$p" && find . -type f -print 2>/dev/null )
    printf '%s' "$newest"; return 0
  fi
  printf '%s' "$( _stat_mtime "$p" )"
}

# The manifest's record for a relpath: "" | "hash:<64hex>" | "link:<target>"
# For SPEC/v1 the record may be per-file rows; presence of ANY row counts, and
# the digest reported is the tree-shaped roll-up of those rows.
_obs_record() {  # $1 = manifest abs path, $2 = relpath
  local m="$1" rel="$2" line rows
  [[ -f "$m" ]] || { printf ''; return 0; }
  line="$( grep -E "^LINK  ${rel//./\\.}  " "$m" 2>/dev/null | head -1 || true )"
  if [[ -n "$line" ]]; then printf 'link:%s' "${line#LINK  $rel  }"; return 0; fi
  line="$( grep -E "^[0-9a-f]{64}  ${rel//./\\.}$" "$m" 2>/dev/null | head -1 || true )"
  if [[ -n "$line" ]]; then printf 'hash:%s' "${line%% *}"; return 0; fi
  # tree surface: any per-file row under the relpath
  rows="$( grep -E "^[0-9a-f]{64}  ${rel//./\\.}/" "$m" 2>/dev/null || true )"
  if [[ -n "$rows" ]]; then
    printf 'hash:%s' "$( printf '%s\n' "$rows" | LC_ALL=C sort | _hash_stdin )"
    return 0
  fi
  printf ''
}

# Refusal markers — the operator-visible contract of ABORT_SURFACE. Matching
# output is a deliberate choice, recorded in docs §6 (OQ-1/OQ-2): a refusal is
# defined by the framework having ATTEMPTED and declined, which leaves no
# filesystem trace at all. If this wording changes, this test fails loudly —
# which is correct, because the operator-visible contract changed.
# Only GENUINE execution failures. Refusing to act on an unsupported
# destination is a DECISION (the surface is adopter-owned), not a failed
# attempt — conflating them made the e2e and the decision function disagree
# about the same cell (round-1 consensus C2).
_ABORT_MARKERS='REFUSING to|could not back up|backup-before-replace'

# =============================================================================
# Fixtures
#
# Every row runs at the SAME target path ($T). That is load-bearing, not
# convenience: the root PROTOCOL.md pointer body embeds the target path, so a
# base tree captured at one path and restored at another would carry a stale
# canonical pointer digest and silently corrupt every protocol row.
# =============================================================================
BASE_DIR="$WORK/base"; mkdir -p "$BASE_DIR"
CANON_POINTER_HASH=""       # captured from a real install at $T (never recomputed)

_base_tar() {  # $1 = ceremony, $2 = base mode(copy|link) -> path to tarball
  local ceremony="$1" bmode="$2"
  local tarball="$BASE_DIR/$ceremony-$bmode.tar"
  [[ -f "$tarball" ]] && { printf '%s' "$tarball"; return 0; }

  rm -rf "$T"; mkdir -p "$T"
  local args=( "$T" --ceremony "$ceremony" )
  [[ "$bmode" == "link" ]] && args+=( --link )
  if ! _run_with_timeout 300 "$REPO_ROOT/scripts/install.sh" "${args[@]}" \
        > "$BASE_DIR/$ceremony-$bmode.install.log" 2>&1; then
    echo "ERROR: base install failed ($ceremony/$bmode) — see $BASE_DIR/$ceremony-$bmode.install.log" >&2
    return 1
  fi
  # The canonical pointer digest for THIS target path, taken from the file the
  # real installer just generated (never reproduced by duplicating the heredoc,
  # which would be an oracle that passes when both sides are wrong together).
  if [[ -z "$CANON_POINTER_HASH" && -f "$T/PROTOCOL.md" ]]; then
    CANON_POINTER_HASH="$( _hash_file "$T/PROTOCOL.md" 2>/dev/null || true )"
  fi
  ( cd "$T" && tar -cf "$tarball" . ) || return 1
  rm -rf "$T"
  printf '%s' "$tarball"
}

# A source checkout that LACKS a surface — what `--pin <pre-v1.3 tag>` yields.
_alt_source() {  # $1 = surface -> path to a source tree without it
  local surface="$1"
  local alt="$WORK/src-no-$surface"
  [[ -d "$alt" ]] && { printf '%s' "$alt"; return 0; }
  _clone_source "$alt" || return 1
  local rel; rel="$( _relpath_for "$surface" )"
  rm -rf "${alt:?}/$rel"
  printf '%s' "$alt"
}

_clone_source() {  # $1 = destination
  mkdir -p "$1"
  ( cd "$REPO_ROOT" && tar -cf - --exclude='./.git' --exclude='./node_modules' . ) \
    | ( cd "$1" && tar -xf - )
}

# The NEXT version of the framework — a source whose surfaces differ from the
# one that produced the baseline.
#
# This is not decoration. A real upgrade runs against a source NEWER than the
# install that wrote the manifest. Reusing one source makes `HASH_SOURCE` and
# `HASH_PRIOR_RECORD` byte-equal, and a classifier can then only tell them
# apart by preferring one — which is resolving an ambiguity by preference, the
# exact thing docs §5.6 forbids. Perturbing the source is how the fixture is
# DIFFERENTIATED until the two candidates separate.
_next_source() {
  local nxt="$WORK/src-next"
  [[ -d "$nxt" ]] && { printf '%s' "$nxt"; return 0; }
  _clone_source "$nxt" || return 1
  local first
  first="$( ( cd "$nxt/SPEC/v1" && find . -type f -print 2>/dev/null ) | LC_ALL=C sort | head -1 )"
  first="${first#./}"
  [[ -n "$first" ]] && printf '\n<!-- next-version marker (PLAN-167 fixture) -->\n' >> "$nxt/SPEC/v1/$first"
  printf '1.3.1\n' > "$nxt/.claude/.framework-version"
  printf '%s' "$nxt"
}

_strip_record() {  # $1 = manifest, $2 = relpath — make prior_record=none
  local m="$1" rel="$2" tmp
  [[ -f "$m" ]] || return 0
  tmp="$( mktemp "$m.XXXXXX" )" || return 1
  grep -vE "^([0-9a-f]{64}|LINK)  ${rel//./\\.}(/|  |$)" "$m" > "$tmp" 2>/dev/null
  mv "$tmp" "$m"
}

_mutate_surface() {  # $1 surface, $2 live_type, $3 live_content, $4 src root, $5 prior_record
  local surface="$1" ltype="$2" lcontent="$3" src_root="$4" prior="${5:-none}"
  local rel; rel="$( _relpath_for "$surface" )"
  local p="$T/$rel"

  # A `link_match` row means the live symlink IS the recorded delivery. The
  # base --link install already created exactly that, so pointing it somewhere
  # else here would silently convert every link_match row into a
  # link_retargeted one — the fixture would then agree with the expectation for
  # the wrong reason, which is how a row goes green while testing nothing.
  if [[ "$ltype" == "symlink" && "$prior" == "link_match" ]]; then
    [[ -L "$p" ]] || { echo "FIXTURE-ERR: $rel is not a symlink after a --link base install" >&2; return 1; }
    ltype="__keep__"
  fi

  case "$ltype" in
    absent)   rm -rf "$p" ;;
    dir_empty)
      rm -rf "$p"; mkdir -p "$p" ;;
    regular)
      if [[ -d "$p" ]]; then rm -rf "$p"; fi
      [[ -e "$p" ]] || { mkdir -p "$( dirname "$p" )"; printf 'adopter regular file\n' > "$p"; }
      ;;
    symlink)
      # The foreign leaf is a TRIPWIRE, not scenery. A surface written with
      # `cat >` follows a leaf symlink and mutates whatever it points at —
      # OUTSIDE the target tree, which is adopter or system data. Comparing
      # only the target would let that row report GREEN while the run
      # destroyed a file the test never looked at.
      rm -rf "$p"
      mkdir -p "$( dirname "$p" )" "$WORK/foreign"
      printf 'foreign content — MUST NOT be modified by any run\n' > "$WORK/foreign/leaf"
      ln -s "$WORK/foreign/leaf" "$p"
      ;;
    special)
      rm -rf "$p"; mkdir -p "$( dirname "$p" )"; mkfifo "$p" 2>/dev/null || return 1 ;;
    ancestor_symlink)
      # Move the parent aside and symlink it back — the leaf is then reachable
      # only by writing THROUGH a symlink out of the target tree.
      local parent; parent="$( dirname "$p" )"
      local real="$WORK/ancestor-real-$surface"
      rm -rf "$real"; mkdir -p "$( dirname "$real" )"
      mv "$parent" "$real" 2>/dev/null || return 1
      ln -s "$real" "$parent"
      ;;
    dir)
      # On a rerun the base install already left the tree; on a structurally
      # fresh target there is nothing yet, so the adopter's own directory has
      # to be built here.
      if [[ ! -d "$p" || -L "$p" ]]; then
        rm -rf "$p"; mkdir -p "$p"; printf 'adopter content\n' > "$p/adopter.md"
      fi
      ;;
  esac

  case "$lcontent" in
    edited)
      if [[ -d "$p" && ! -L "$p" ]]; then
        local victim
        victim="$( ( cd "$p" && find . -type f -print 2>/dev/null ) | LC_ALL=C sort | head -1 )"
        victim="${victim#./}"
        # Guard the empty-tree case: without it the redirect target collapses to
        # "$p/" and the shell reports "Is a directory" instead of mutating.
        # if/fi, NOT `[[ ]] && cmd`: as the last statement of the branch, a
        # false test would make the whole function return 1 and the row would
        # be recorded as a harness error rather than run.
        if [[ -n "$victim" ]]; then
          printf '\nADOPTER EDIT\n' >> "$p/$victim"
        fi
      elif [[ -f "$p" && ! -L "$p" ]]; then
        printf 'ADOPTER EDIT\n' >> "$p"
      fi
      ;;
    pristine)
      # "byte-identical to what THIS run's source would deliver" — so it must be
      # synced from the RUN source, not left as whatever the base install wrote.
      # The generated pointer has no source file: the base install's own output
      # IS its pristine form, so protocol is left untouched.
      if [[ "$surface" != "protocol" && -e "$src_root/$rel" && ! -L "$p" ]]; then
        rm -rf "$p"; mkdir -p "$( dirname "$p" )"; cp -R "$src_root/$rel" "$p" 2>/dev/null || true
      fi
      ;;
    legacy_pristine)
      # A REAL v1.2.0 SPEC/v1 tree from the tag the pristine fingerprints were
      # derived from — never a hand-built approximation, which would test the
      # fixture rather than the migration.
      if ! git -C "$REPO_ROOT" rev-parse -q --verify 'refs/tags/v1.2.0^{}' >/dev/null 2>&1; then
        echo "FIXTURE-ERR: tag v1.2.0 is not available in this checkout." >&2
        echo "             legacy_pristine rows need the REAL shipped tree, never an" >&2
        echo "             approximation. A CI checkout using fetch-depth:1 has NO tags" >&2
        echo "             — that job needs fetch-depth:0 or fetch-tags:true." >&2
        return 1
      fi
      rm -rf "$p"; mkdir -p "$p"
      git -C "$REPO_ROOT" archive v1.2.0 SPEC/v1 2>/dev/null \
        | ( cd "$T" && tar -xf - ) || return 1
      ;;
    legacy_pristine_partial)
      # A pristine shipped tree that ALSO carries an entry the fingerprint
      # cannot inventory. Distinct from `edited`: every regular file still
      # matches a shipped release, so content alone reads "pristine" — and the
      # tree must STILL be refused, because a partial inventory can never
      # certify a wholesale replace (ADR-155-AMEND-1 §4).
      if ! git -C "$REPO_ROOT" rev-parse -q --verify 'refs/tags/v1.2.0^{}' >/dev/null 2>&1; then
        echo "FIXTURE-ERR: tag v1.2.0 unavailable (see legacy_pristine above)" >&2
        return 1
      fi
      rm -rf "$p"; mkdir -p "$p"
      git -C "$REPO_ROOT" archive v1.2.0 SPEC/v1 2>/dev/null \
        | ( cd "$T" && tar -xf - ) || return 1
      ln -s /dev/null "$p/adopter-added.link" 2>/dev/null || true
      ;;
  esac

}

# =============================================================================
# Verdict derivation
# =============================================================================
_derive_verdict() {  # $1 bd $2 ad $3 br $4 ar $5 out $6 surface $7 rel $8 operation
  local bd="$1" ad="$2" br="$3" ar="$4" out="$5" surface="$6" rel="$7" op="${8:-upgrade}"
  if [[ "$bd" != "$ad" ]]; then
    if [[ "$bd" == "absent" ]]; then printf 'DELIVER'; else printf 'REFRESH'; fi
    return 0
  fi
  # Unchanged target from here on.
  if grep -Eq "$_ABORT_MARKERS" "$out" 2>/dev/null; then printf 'ABORT_SURFACE'; return 0; fi
  # A REFRESH that writes byte-identical content leaves the CONTENT unchanged,
  # so a content digest alone cannot separate it from a PRESERVE.
  #
  # Backup presence does not settle it either: the ADOPTER-FORK preserve path
  # also snapshots into BAK_DIR, so "a backup exists" is evidence the framework
  # looked, not that it wrote.
  #
  # Modification time settles it on the UPGRADE path, from state and without
  # reading prose: the forced route replaces content with `cp -R` (no -p),
  # which stamps new mtimes, while every preserve path leaves bytes AND
  # timestamps alone.
  #
  # Restricted to upgrade deliberately. install.sh re-runs placeholder
  # SUBSTITUTION on every invocation, so it rewrites the pointer with identical
  # bytes and a fresh mtime — a write with no semantic content. Counting that
  # as REFRESH would report an ownership change where none happened.
  #
  # No single signal is valid everywhere here: the content digest cannot see an
  # identical-content refresh, the backup fires on the preserve-with-snapshot
  # path, and mtime fires on install re-substitution. Each is used only where
  # it is sound, and the boundary is stated rather than assumed.
  if [[ "$op" == "upgrade" && "$_MTIME_BEFORE" != "$_MTIME_AFTER" ]]; then
    printf 'REFRESH'; return 0
  fi
  # OQ-9 colapsada: sem registro ao final é PRESERVE_UNOWNED, tenha ou não
  # existido um antes. O 'tinha antes?' é prior_record, que já é uma coluna.
  if [[ -n "$ar" ]]; then printf 'PRESERVE_OWNED'; else printf 'PRESERVE_UNOWNED'; fi
}

_derive_hash_source() {  # $1 surface $2 after_rec $3 prior_rec $4 src_root
  local surface="$1" ar="$2" pr="$3" src="$4"
  [[ -z "$ar" ]] && { printf 'HASH_NONE'; return 0; }
  case "$ar" in link:*) printf 'LINK_RECORD'; return 0 ;; esac

  local got="${ar#hash:}"
  local rel; rel="$( _relpath_for "$surface" )"

  # Candidate 1: the bytes now at the target.
  local c_target; c_target="$( _obs_digest "$T/$rel" )"
  # Candidate 2: the framework's copy in the source checkout.
  local c_source; c_source="$( _obs_digest "$src/$rel" )"
  # Candidate 3: the digest the PRE-run manifest recorded.
  local c_prior="${pr#hash:}"
  # Candidate 4: the canonical pointer digest (protocol only).
  local c_pointer="$CANON_POINTER_HASH"

  # For tree surfaces the recorded value is the roll-up of per-file rows, which
  # is not comparable to a content fingerprint — compare tree membership by
  # re-deriving both roll-ups instead.
  if [[ "$surface" == "spec" ]]; then
    local roll_t roll_s
    roll_t="$( _rollup_from_tree "$T/$rel" "$rel" )"
    roll_s="$( _rollup_from_tree "$src/$rel" "$rel" )"
    [[ -n "$c_prior" && "$got" == "$c_prior" ]] && { printf 'HASH_PRIOR_RECORD'; return 0; }
    [[ -n "$roll_s" && "$got" == "$roll_s" ]] && { printf 'HASH_SOURCE'; return 0; }
    [[ -n "$roll_t" && "$got" == "$roll_t" ]] && { printf 'HASH_TARGET'; return 0; }
    printf 'HASH_UNCLASSIFIED'; return 0
  fi

  # The canonical pointer digest is the hash of what the framework WOULD
  # generate — it matches no file on disk when the pointer is customised, so it
  # has to be recognised explicitly or every correct record reads as
  # unclassified.
  # Order matters and is NOT arbitrary. For a PRISTINE pointer the canonical
  # digest and the prior record are the SAME bytes, so whichever is tested
  # first wins the name. Testing the prior record first keeps continuity rows
  # reading as HASH_PRIOR_RECORD, and the canonical name is then reached only
  # when the two genuinely differ — i.e. when the pointer was customised, which
  # is the one cell where the distinction carries meaning.
  [[ -n "$c_prior"   && "$got" == "$c_prior"   ]] && { printf 'HASH_PRIOR_RECORD'; return 0; }
  if [[ "$surface" == "protocol" && -n "$c_pointer" && "$got" == "$c_pointer" ]]; then
    printf 'HASH_CANONICAL_POINTER'; return 0
  fi
  [[ -n "$c_source"  && "$got" == "$c_source"  ]] && { printf 'HASH_SOURCE'; return 0; }
  [[ -n "$c_pointer" && "$got" == "$c_pointer" ]] && { printf 'HASH_CANONICAL_POINTER'; return 0; }
  [[ -n "$c_target"  && "$got" == "$c_target"  ]] && { printf 'HASH_TARGET'; return 0; }
  printf 'HASH_UNCLASSIFIED'
}

_rollup_from_tree() {  # $1 = tree abs path, $2 = relpath prefix
  local root="$1" pfx="$2"
  [[ -d "$root" ]] || { printf ''; return 0; }
  ( cd "$root" && find . -type f -print 2>/dev/null ) | LC_ALL=C sort \
    | while IFS= read -r r; do
        [[ -n "$r" ]] || continue
        printf '%s  %s/%s\n' "$( _hash_file "$root/$r" 2>/dev/null || echo FAIL )" "$pfx" "${r#./}"
      done | LC_ALL=C sort | _hash_stdin
}

# =============================================================================
# Row execution
# =============================================================================
PASS=0; FAIL=0; AMBIG=0; ERR=0
MAP_LINES=""

_run_row() {
  local id="$1" surface="$2" prior_record="$3" live_type="$4" live_content="$5"
  local source_has="$6" mode="$7" ceremony="$8" operation="$9" skip_requested="${10}"
  local fault="${11}"
  local exp_verdict="${12}" exp_hash="${13}" origin="${14}" note="${15}"

  local rel; rel="$( _relpath_for "$surface" )" || { ERR=$((ERR+1)); return; }

  # --- base selection ------------------------------------------------------
  # base_mode follows PRIOR_RECORD (the previous run), never `mode` (this run).
  # Conflating them would erase the r11-F1 cell — see docs §4.1.
  local base_mode="copy"
  case "$prior_record" in link_match|link_retargeted) base_mode="link" ;; esac
  local base_ceremony="$ceremony"
  # A user-ceremony row asserting residue of a MAINTAINER install must be built
  # from a maintainer base, then transitioned — that transition is the r7-F2 cell.
  local transition_to_user=0
  if [[ "$ceremony" == "user" && "$prior_record" != "none" && "$surface" != "marker" ]]; then
    base_ceremony="maintainer"; transition_to_user=1
  fi

  # --- source selection (BEFORE the fixture — `pristine` syncs from it) ----
  local src
  if [[ "$source_has" == "no" ]]; then
    src="$( _alt_source "$surface" )" || { ERR=$((ERR+1)); return; }
  elif [[ "$operation" == "install_fresh" ]]; then
    src="$REPO_ROOT"
  else
    # An upgrade/rerun runs against a source NEWER than the one that wrote the
    # baseline. Without that, HASH_SOURCE and HASH_PRIOR_RECORD are byte-equal.
    src="$( _next_source )" || { ERR=$((ERR+1)); return; }
  fi

  # --- base tree -----------------------------------------------------------
  if [[ "$operation" == "install_fresh" ]]; then
    # Structurally fresh means NO pre-existing manifest (docs R-01). Extracting
    # a base and stripping one record would leave a manifest behind and make the
    # row an install_rerun wearing a fresh label.
    rm -rf "$T"; mkdir -p "$T"
  else
    local tarball; tarball="$( _base_tar "$base_ceremony" "$base_mode" )" || { ERR=$((ERR+1)); return; }
    rm -rf "$T"; mkdir -p "$T"
    tar -xf "$tarball" -C "$T" || { ERR=$((ERR+1)); return; }
  fi

  # --- fixture mutation ----------------------------------------------------
  [[ "$prior_record" == "none" ]] && _strip_record "$T/$MANIFEST_REL" "$rel"
  if [[ "$prior_record" == "link_retargeted" && -L "$T/$rel" ]]; then
    mkdir -p "$WORK/retarget"; printf 'retargeted\n' > "$WORK/retarget/leaf"
    rm -f "$T/$rel"; ln -s "$WORK/retarget/leaf" "$T/$rel"
  fi
  _mutate_surface "$surface" "$live_type" "$live_content" "$src" "$prior_record" \
    || { ERR=$((ERR+1)); return; }

  # Fault injection from the `fault` COLUMN. It rode in `note` until round-1
  # consensus C1 ruled that a dimension the harness parses out of prose is a
  # dimension nothing validates.
  local bak_guard=""
  case "$fault" in
    backup_unwritable)
      # Make the SURFACE unbackupable, not the upgrade unstartable. upgrade.sh
      # creates $BAK_DIR at startup, so locking .claude.bak killed the run
      # before any surface was reached — the branch under test never ran.
      # An unreadable SOURCE makes the copy fail while everything else proceeds.
      bak_guard="$T/$rel"
      chmod 000 "$bak_guard" 2>/dev/null || true ;;
  esac

  # --- BEFORE snapshot -----------------------------------------------------
  local b_digest b_rec
  b_digest="$( _obs_digest "$T/$rel" )"
  b_rec="$( _obs_record "$T/$MANIFEST_REL" "$rel" )"
  _MTIME_BEFORE="$( _obs_mtime "$T/$rel" )"
  # Everything outside $T that a run could reach. Any change here is an escape.
  _ESCAPE_BEFORE="$( _obs_digest "$WORK/foreign/leaf" 2>/dev/null || printf 'absent' )"

  # --- run the REAL script -------------------------------------------------
  local out="$WORK/run-$id.log"; : > "$out"
  local rc=0
  # A `ceremony=user` UPGRADE row asserts residue of a maintainer install that
  # was later re-run as `--ceremony user`. The ceremony is read from
  # .claude/.install-state.json, so labelling the row is not enough: the
  # transition has to actually happen, or upgrade.sh still sees `maintainer`
  # and the row silently tests the wrong branch.
  if [[ "$transition_to_user" -eq 1 && "$operation" == "upgrade" ]]; then
    _run_with_timeout "$CELL_TIMEOUT" "$src/scripts/install.sh" "$T" --ceremony user \
      >> "$out" 2>&1 || true
  fi
  if [[ "$operation" == "upgrade" ]]; then
    local uargs=( "$T" )
    [[ "$skip_requested" == "self" ]] && uargs+=( --skip "$rel" )
    if [[ "$skip_requested" == "descendant" ]]; then
      local victim; victim="$( ( cd "$T/$rel" 2>/dev/null && find . ! -type d -print 2>/dev/null | LC_ALL=C sort | head -1 ) )"
      victim="${victim#./}"
      [[ -n "$victim" ]] && uargs+=( --skip "$rel/$victim" )
    fi
    _run_with_timeout "$CELL_TIMEOUT" "$src/scripts/upgrade.sh" "${uargs[@]}" >> "$out" 2>&1
    rc=$?
  else
    local iargs=( "$T" --ceremony "$ceremony" )
    [[ "$mode" == "link" ]] && iargs+=( --link )
    [[ "$transition_to_user" -eq 1 ]] && iargs=( "$T" --ceremony user )
    _run_with_timeout "$CELL_TIMEOUT" "$src/scripts/install.sh" "${iargs[@]}" >> "$out" 2>&1
    rc=$?
  fi
  [[ -n "$bak_guard" ]] && chmod -R u+rwX "$bak_guard" 2>/dev/null

  local timed_out=0
  [[ $rc -eq 124 || $rc -eq 137 ]] && timed_out=1

  # --- AFTER snapshot + derivation ----------------------------------------
  local a_digest a_rec got_verdict got_hash
  a_digest="$( _obs_digest "$T/$rel" )"
  a_rec="$( _obs_record "$T/$MANIFEST_REL" "$rel" )"
  _MTIME_AFTER="$( _obs_mtime "$T/$rel" )"
  _ESCAPE_AFTER="$( _obs_digest "$WORK/foreign/leaf" 2>/dev/null || printf 'absent' )"

  if [[ "$timed_out" -eq 1 ]]; then
    got_verdict="TIMEOUT"; got_hash="TIMEOUT"
  else
    got_verdict="$( _derive_verdict "$b_digest" "$a_digest" "$b_rec" "$a_rec" "$out" "$surface" "$rel" "$operation" )"
    got_hash="$( _derive_hash_source "$surface" "$a_rec" "$b_rec" "$src" )"
  fi

  # --- compare -------------------------------------------------------------
  local status="RED"
  local alt=""
  case "$note" in *indistinguishable=*) alt="${note##*indistinguishable=}"; alt="${alt%% *}" ;; esac

  # An escape outranks the verdict comparison. A row whose pair matches while
  # the run wrote OUTSIDE the target has not passed: it has demonstrated the
  # exact damage class this table exists to prevent, and calling that GREEN
  # would be the instrument concealing a data loss.
  if [[ "$_ESCAPE_BEFORE" != "$_ESCAPE_AFTER" ]]; then
    status="ESCAPE"; FAIL=$((FAIL+1))
  elif [[ "$got_verdict" == "$exp_verdict" && "$got_hash" == "$exp_hash" ]]; then
    status="GREEN"; PASS=$((PASS+1))
  elif [[ "$got_verdict" == "$exp_verdict" && -n "$alt" && "$got_hash" == "$alt" ]]; then
    status="AMBIG"; AMBIG=$((AMBIG+1))
  elif [[ "$got_verdict" == "TIMEOUT" ]]; then
    status="TIMEOUT"; FAIL=$((FAIL+1))
  else
    FAIL=$((FAIL+1))
  fi

  MAP_LINES+="$( printf '%-10s %-7s exp=%-16s/%-22s got=%-16s/%-22s rc=%-3s %s\n' \
      "$id" "$status" "$exp_verdict" "$exp_hash" "$got_verdict" "$got_hash" "$rc" "$origin" )"$'\n'
}

# =============================================================================
# Main
# =============================================================================
if [[ "$LIST_ONLY" -eq 1 ]]; then
  awk -F'\t' '!/^#/ && $1!="id" && NF>1 {print $1"\t"$13}' "$TSV"
  exit 0
fi

echo "== PLAN-167 ownership decision table =="
echo "   table:  $TSV"
echo "   source: $REPO_ROOT"
echo "   scratch:$WORK"
echo "   timeout:${CELL_TIMEOUT}s/cell   timeout-bin:${_TIMEOUT_BIN:-<fallback>}"
echo ""

# Prime the canonical pointer digest for $T from a real install. Structurally
# fresh rows build no base, so without this the protocol candidate would be
# unavailable exactly where it is needed.
_base_tar maintainer copy >/dev/null || { echo "ERROR: could not prime base" >&2; exit 2; }


# Rows are consumed in file order; the map is sorted by id at emit time so the
# output is deterministic regardless of table order.
while IFS=$'\t' read -r id surface prior_record live_type live_content \
      source_has mode ceremony operation skip_requested fault \
      exp_verdict exp_hash origin note; do
  [[ -z "${id:-}" ]] && continue
  case "$id" in \#*|id) continue ;; esac
  # --only takes a comma-separated list: iterating on a cluster of related rows
  # should cost ONE base install, not one per row.
  if [[ -n "$ONLY" && ",$ONLY," != *",$id,"* ]]; then continue; fi
  _run_row "$id" "$surface" "$prior_record" "$live_type" "$live_content" \
           "$source_has" "$mode" "$ceremony" "$operation" "$skip_requested" \
           "${fault:-none}" "$exp_verdict" "$exp_hash" "$origin" "${note:-}"
done < "$TSV"

printf '%s' "$MAP_LINES" | LC_ALL=C sort

echo ""
echo "GREEN=$PASS  RED=$FAIL  AMBIG=$AMBIG  HARNESS-ERR=$ERR"

[[ "$MAP_ONLY" -eq 1 ]] && exit 0
[[ "$ERR" -gt 0 ]] && exit 2
[[ "$FAIL" -gt 0 ]] && exit 1
exit 0

exec
/bin/zsh -lc 'bash scripts/tests/test-ownership-verdict-unit.sh --quiet; echo rc=$?; bash -n scripts/install.sh scripts/upgrade.sh scripts/_framework_manifest_set.sh scripts/doctor.sh .claude/scripts/check-framework-updates.sh scripts/tests/test-ownership-table.sh scripts/tests/test-ownership-verdict-unit.sh scripts/tests/test-upgrade-spec-ownership.sh; echo bash_n_rc=$?' in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:

unit oracle: PASS=60  FAIL=0  SKIPPED(execution-fault rows)=2
  not decision cells, covered by the e2e: OWN-0024 OWN-0027 
rc=0
bash_n_rc=0

exec
/bin/zsh -lc "git diff -- .claude/scripts/check-framework-updates.sh; sed -n '1,260p' .claude/scripts/check-framework-updates.sh; grep -n \"--pin\\|PIN=\" scripts/upgrade.sh | head -100" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-cIpufcfz' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-KKEq5tCi' (errno=Operation not permitted)
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
#!/bin/bash
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

# Resolve the LOCAL framework version — MARKER-FIRST with VERSION fallback
# (PLAN-166 F3 / ADR-155-AMEND-1). In an ADOPTER tree the root VERSION is an
# install-time snapshot: upgrade.sh deliberately never touches it (the
# S238/ADR-155 clobber class), so reading it post-upgrade reports the OLD
# version forever and this checker would exit behind-minor demanding the
# SAME upgrade it just performed, in a loop (r8). The upgrade refreshes
# .claude/.framework-version instead — but the marker is only TRUSTED when
# the SAME delivery record the writers use (the ADR-155 baseline manifest,
# .claude/.install-manifest.sha256) records it as framework-delivered: a
# pre-existing adopter marker that install EXISTS-skipped must not be read
# at all (r20). Resolution order:
#   1. --version-file <path>              (explicit override — unchanged)
#   2. <root>/.claude/.framework-version  when well-formed AND
#                                         delivery-recorded in the manifest
#   3. <root>/VERSION                     (pre-v1.3.0 installs, and the
#                                          framework repo itself, where the
#                                          tracked marker == VERSION and
#                                          VERSION stays the authority)
if [ -n "$LOCAL_VERSION_FILE" ]; then
  VFILE="$LOCAL_VERSION_FILE"
  VSOURCE="explicit --version-file"
else
  # Walk up from CWD to the first directory carrying either signal.
  cur="$(pwd)"
  VROOT=""
  VFILE=""
  VSOURCE=""
  while [ "$cur" != "/" ]; do
    if [ -f "$cur/.claude/.framework-version" ] || [ -f "$cur/VERSION" ]; then
      VROOT="$cur"
      break
    fi
    cur="$(dirname "$cur")"
  done
  if [ -z "$VROOT" ]; then
    echo "fatal: no .claude/.framework-version or VERSION found (looked from $(pwd))" >&2
    exit 3
  fi
  MARKER="$VROOT/.claude/.framework-version"
  MANIFEST="$VROOT/.claude/.install-manifest.sha256"
  if [ -f "$MARKER" ]; then
    MARKER_REC=""
    if [ -f "$MANIFEST" ]; then
      MARKER_REC="$(grep -E '^([0-9a-f]{64}|LINK)  \.claude/\.framework-version(  |$)' "$MANIFEST" 2>/dev/null | head -1 || true)"
    fi
    if [ -n "$MARKER_REC" ]; then
      # r20 answered PROVENANCE (is this marker the framework's delivery?)
      # but never INTEGRITY: a delivered marker edited afterwards to any
      # well-formed version still satisfied the record check, so hand-editing
      # 1.3.0 -> 9.9.9 made the checker report up-to-date against an upstream
      # 1.3.0 and SUPPRESS a real update (codex W1 round 7, P2). Verify the
      # live bytes against the record before selecting the marker; anything
      # unverifiable falls back to VERSION — the same conservative direction
      # r20 already takes for an unrecorded marker.
      MARKER_OK=""
      case "$MARKER_REC" in
        LINK\ \ *)
          # Fixed double-space delimiter (targets may contain spaces).
          _rec_tgt="${MARKER_REC#LINK  .claude/.framework-version  }"
          _live_tgt="$(readlink "$MARKER" 2>/dev/null || true)"
          if [ -n "$_rec_tgt" ] && [ "$_rec_tgt" = "$_live_tgt" ]; then MARKER_OK=1; fi
          ;;
        *)
          _rec_dg="${MARKER_REC%%  *}"
          _live_dg=""
          if command -v shasum >/dev/null 2>&1; then
            _live_dg="$(shasum -a 256 "$MARKER" 2>/dev/null | cut -d' ' -f1 || true)"
          elif command -v sha256sum >/dev/null 2>&1; then
            _live_dg="$(sha256sum "$MARKER" 2>/dev/null | cut -d' ' -f1 || true)"
          fi
          if [ -n "$_live_dg" ] && [ "$_rec_dg" = "$_live_dg" ]; then MARKER_OK=1; fi
          ;;
      esac
      if [ -z "$MARKER_OK" ]; then
        log "note: .claude/.framework-version does NOT match its delivery record (edited, redirected, or no digest tool available) — falling back to VERSION"
      else
        MARKER_VAL="$(tr -d '\n\r ' < "$MARKER" 2>/dev/null || true)"
        if [[ "$MARKER_VAL" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-rc\.[0-9]+)?$ ]]; then
          VFILE="$MARKER"
          VSOURCE="marker (.claude/.framework-version, delivery-recorded)"
        else
          log "note: .claude/.framework-version malformed ('$MARKER_VAL') — falling back to VERSION"
        fi
      fi
    elif [ ! -f "$MANIFEST" ] && [ ! -f "$VROOT/VERSION" ]; then
      # No manifest AND no VERSION: the marker is the only signal there is
      # (fail-open — refusing here would make the checker fatal on a tree
      # that still has a perfectly readable version value).
      VFILE="$MARKER"
      VSOURCE="marker (no manifest — only signal present)"
    else
      log "note: .claude/.framework-version present but NOT delivery-recorded in .claude/.install-manifest.sha256 — falling back to VERSION (r20: a pre-existing adopter marker is not the framework's)"
    fi
  fi
  if [ -z "$VFILE" ] && [ -f "$VROOT/VERSION" ]; then
    VFILE="$VROOT/VERSION"
    VSOURCE="root VERSION (fallback)"
  fi
fi

if [ -z "$VFILE" ] || [ ! -f "$VFILE" ]; then
  echo "fatal: version source not found (looked from $(pwd))" >&2
  exit 3
fi
log "version source: ${VSOURCE:-unknown} ($VFILE)"

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
grep: unrecognized option `--pin\|PIN='
usage: grep [-abcdDEFGHhIiJLlMmnOopqRSsUVvwXxZz] [-A num] [-B num] [-C[num]]
	[-e pattern] [-f file] [--binary-files=value] [--color=when]
	[--context[=num]] [--directories=action] [--label] [--line-buffered]
	[--null] [pattern] [file ...]

exec
/bin/zsh -lc "git diff -- .claude/scripts/check-model-deprecations.py scripts/doctor.sh; git diff -- scripts/tests/ownership_table.tsv | sed -n '1,260p'" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-Qjs6rT3j' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-3geNcsVG' (errno=Operation not permitted)
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
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-k21wGAP5' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-IFYNvsnP' (errno=Operation not permitted)
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

exec
/bin/zsh -lc "sed -n '175,235p' .claude/scripts/check-model-deprecations.py; git diff -- .claude/scripts/tests/test_release_workflow_asserts.py | sed -n '1,260p'" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
    if retirement <= today:
        return SEV_BREAK, "ALREADY-RETIRED"
    label = "RETIRE-%s" % retirement.isoformat()
    if (retirement - today).days <= warn_days:
        return SEV_WARN, label
    return SEV_INFO, label


def first_inert_rule(
    rel_path: str, inert_rules: List[Tuple[str, "re.Pattern[str]"]]
) -> Optional[str]:
    for rule_id, rule_re in inert_rules:
        if rule_re.search(rel_path):
            return rule_id
    return None


def scan_root(
    root: str,
    pattern: "re.Pattern[str]",
    literal_map: Dict[str, Dict],
    inert_rules: List[Tuple[str, "re.Pattern[str]"]],
    today: datetime.date,
    warn_days: int,
) -> List[Dict]:
    """S230 sweep walk, ledger-driven; returns one dict per hit."""
    hits: List[Dict] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fn in filenames:
            path = os.path.join(dirpath, fn)
            try:
                # lstat + S_ISREG, not getsize: opening a FIFO BLOCKS FOREVER
                # waiting for a writer, and getsize reports 0 for one, so the
                # size cap never sees it. An adopter with a FIFO anywhere under
                # the target used to hang the whole upgrade here — mid-run,
                # after earlier surfaces had already been modified
                # (PLAN-167 docs §5.7). Symlinks are skipped for the same
                # no-follow reason the rest of the install surface uses.
                st = os.lstat(path)
                if not stat.S_ISREG(st.st_mode):
                    continue
                if st.st_size > MAX_BYTES:
                    continue
                with open(path, "rb") as fh:
                    raw = fh.read()
                if b"\x00" in raw[:8192]:
                    continue
                text = raw.decode("utf-8", errors="ignore")
            except OSError:
                continue
            rel = os.path.relpath(path, root).replace(os.sep, "/")
            inert_rule = first_inert_rule(rel, inert_rules)
            for m in pattern.finditer(text):
                entry = literal_map.get(m.group(0))
                if entry is None:  # pragma: no cover — map covers pattern
                    continue
                severity, label = classify_entry(entry, today, warn_days)
                hit = {
                    "root": root,
                    "path": rel,
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-03S6snPq' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-v19zhr2G' (errno=Operation not permitted)
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

exec
/bin/zsh -lc "find .github/workflows -maxdepth 1 -type f | wc -l; grep -R -l '"'^ *push:'"' .github/workflows/*.yml | wc -l; grep -R -l 'tags:' .github/workflows/*.yml | sed -n '1,100p'; grep -n \"STALENESS\\|weekly-workflow\" .github/workflows/release.yml | head" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
      23
      14
.github/workflows/npm-publish.yml
.github/workflows/release.yml
20:      # weekly-workflow status gate (see below) call `gh run list`
463:      # PLAN-012 Phase 2 §R11 — weekly-workflow status gate.
517:          STALENESS_DAYS=14
518:          STALENESS_SECS=$((STALENESS_DAYS * 86400))
556:            # STALENESS_DAYS of now. startedAt is ISO-8601 UTC
573:            if [ "$delta" -gt "$STALENESS_SECS" ]; then
574:              echo "::error::$wf stale — last run $days days ago (> $STALENESS_DAYS day limit)"
584:          echo "OK: all 6 advisory workflows clean in last 3 runs + fresh within $STALENESS_DAYS days"
942:      # the weekly-workflow gate (WORKFLOWS=(...)).

exec
/bin/zsh -lc "grep -R \"head_branch\" -n .claude/scripts/tests/test_await_release_gate.py | head -30; sed -n '1,420p' .claude/scripts/tests/test_await_release_gate.py" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
.claude/scripts/tests/test_await_release_gate.py:103:        "head_branch": TAG,
.claude/scripts/tests/test_await_release_gate.py:121:        "head_branch": TAG,
.claude/scripts/tests/test_await_release_gate.py:190:        self._assert_never_grants(release_run(head_branch="v1.3.0-rc.2", id=2001))
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
/bin/zsh -lc 'git diff -- CLAUDE.md INSTALL.md README.md README.pt-BR.md RELEASE.md docs/ARCHITECTURE.md docs/CTO-GUIDE.md docs/FAQ.md docs/GUIA-COMPLETO.md docs/README.md npm/README.md' in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 133ms:
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
 

exec
/bin/zsh -lc "find .claude/adr -maxdepth 1 -type f -name 'ADR-*.md' | wc -l; find .github/workflows -maxdepth 1 -type f -name '*.yml' | wc -l; python3 .claude/scripts/check-agents-md.py --format json; printf '\\ncounts gate\\n'; bash .claude/scripts/local/verify-counts.sh 2>&1 | tail -80" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 530ms:
.claude/scripts/local/verify-counts.sh: line 246: cannot create temp file for here document: Operation not permitted
.claude/scripts/local/verify-counts.sh: line 412: cannot create temp file for here document: Operation not permitted

exec
/bin/zsh -lc 'shasum -a 256 -c .claude/plans/PLAN-166/staged-manifest.sha256 2>&1 | tail -50; echo rc=${pipestatus[1]:-${PIPESTATUS[0]}}; printf '"'\\nmanifest diff\\n'; git diff -- .claude/plans/PLAN-166/staged-manifest.sha256" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
.claude/plans/PLAN-166/staged/INSTALL.md: FAILED open or read
shasum: .claude/plans/PLAN-166/staged/notes-w1b-kernel-override.md: No such file or directory
.claude/plans/PLAN-166/staged/notes-w1b-kernel-override.md: FAILED open or read
shasum: .claude/plans/PLAN-166/staged/notes-w1c-f3.md: No such file or directory
.claude/plans/PLAN-166/staged/notes-w1c-f3.md: FAILED open or read
shasum: .claude/plans/PLAN-166/staged/patches/f3-adr-155-amend-1.patch: No such file or directory
.claude/plans/PLAN-166/staged/patches/f3-adr-155-amend-1.patch: FAILED open or read
shasum: .claude/plans/PLAN-166/staged/patches/f3-check-framework-updates-marker-first.patch: No such file or directory
.claude/plans/PLAN-166/staged/patches/f3-check-framework-updates-marker-first.patch: FAILED open or read
shasum: .claude/plans/PLAN-166/staged/patches/f3-doctor-delivery-flags.patch: No such file or directory
.claude/plans/PLAN-166/staged/patches/f3-doctor-delivery-flags.patch: FAILED open or read
shasum: .claude/plans/PLAN-166/staged/patches/f3-fms-conditional-entries.patch: No such file or directory
.claude/plans/PLAN-166/staged/patches/f3-fms-conditional-entries.patch: FAILED open or read
shasum: .claude/plans/PLAN-166/staged/patches/f3-framework-version-marker.patch: No such file or directory
.claude/plans/PLAN-166/staged/patches/f3-framework-version-marker.patch: FAILED open or read
shasum: .claude/plans/PLAN-166/staged/patches/f3-install-delivery-record.patch: No such file or directory
.claude/plans/PLAN-166/staged/patches/f3-install-delivery-record.patch: FAILED open or read
shasum: .claude/plans/PLAN-166/staged/patches/f3-install-md-consequences.patch: No such file or directory
.claude/plans/PLAN-166/staged/patches/f3-install-md-consequences.patch: FAILED open or read
shasum: .claude/plans/PLAN-166/staged/patches/f3-test-upgrade-spec-ownership.patch: No such file or directory
.claude/plans/PLAN-166/staged/patches/f3-test-upgrade-spec-ownership.patch: FAILED open or read
shasum: .claude/plans/PLAN-166/staged/patches/f3-upgrade-spec-forced-refresh.patch: No such file or directory
.claude/plans/PLAN-166/staged/patches/f3-upgrade-spec-forced-refresh.patch: FAILED open or read
shasum: .claude/plans/PLAN-166/staged/patches/release-yml-verdict-delta-ancestry.patch: No such file or directory
.claude/plans/PLAN-166/staged/patches/release-yml-verdict-delta-ancestry.patch: FAILED open or read
shasum: .claude/plans/PLAN-166/staged/patches/smoke-install-parity-e2e-wiring.patch: No such file or directory
.claude/plans/PLAN-166/staged/patches/smoke-install-parity-e2e-wiring.patch: FAILED open or read
shasum: .claude/plans/PLAN-166/staged/patches/w0-verdict-template-delta-fields.patch: No such file or directory
.claude/plans/PLAN-166/staged/patches/w0-verdict-template-delta-fields.patch: FAILED open or read
shasum: .claude/plans/PLAN-166/staged/patches/w1-parity-classify-known-open-purge.patch: No such file or directory
.claude/plans/PLAN-166/staged/patches/w1-parity-classify-known-open-purge.patch: FAILED open or read
shasum: .claude/plans/PLAN-166/staged/patches/w1a-npm-publish-await-gate.patch: No such file or directory
.claude/plans/PLAN-166/staged/patches/w1a-npm-publish-await-gate.patch: FAILED open or read
shasum: .claude/plans/PLAN-166/staged/patches/w1a-npm-trusted-publisher-txt.patch: No such file or directory
.claude/plans/PLAN-166/staged/patches/w1a-npm-trusted-publisher-txt.patch: FAILED open or read
shasum: .claude/plans/PLAN-166/staged/patches/w1a-release-workflow-asserts.patch: No such file or directory
.claude/plans/PLAN-166/staged/patches/w1a-release-workflow-asserts.patch: FAILED open or read
shasum: .claude/plans/PLAN-166/staged/scripts/_framework_manifest_set.sh: No such file or directory
.claude/plans/PLAN-166/staged/scripts/_framework_manifest_set.sh: FAILED open or read
shasum: .claude/plans/PLAN-166/staged/scripts/doctor.sh: No such file or directory
.claude/plans/PLAN-166/staged/scripts/doctor.sh: FAILED open or read
shasum: .claude/plans/PLAN-166/staged/scripts/install.sh: No such file or directory
.claude/plans/PLAN-166/staged/scripts/install.sh: FAILED open or read
shasum: .claude/plans/PLAN-166/staged/scripts/tests/_parity_classify.py: No such file or directory
.claude/plans/PLAN-166/staged/scripts/tests/_parity_classify.py: FAILED open or read
shasum: .claude/plans/PLAN-166/staged/scripts/tests/test-upgrade-spec-ownership.sh: No such file or directory
.claude/plans/PLAN-166/staged/scripts/tests/test-upgrade-spec-ownership.sh: FAILED open or read
shasum: .claude/plans/PLAN-166/staged/scripts/upgrade.sh: No such file or directory
.claude/plans/PLAN-166/staged/scripts/upgrade.sh: FAILED open or read
shasum: WARNING: 34 listed files could not be read
rc=1

manifest diff
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-6irfzZfJ' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-ffLSKjPH' (errno=Operation not permitted)
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

exec
/bin/zsh -lc "grep -n \"BEGIN PGP\\|END PGP\\|Signature\" .claude/plans/PLAN-166/architect/round-1/approved.md; find .claude/plans/PLAN-166 -type f -maxdepth 4 -print | LC_ALL=C sort; grep -n \"architect/round\\|approved.md\\|\\.asc\" .claude/hooks/check_canonical_edit.py | head -100" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
.claude/plans/PLAN-166/W1-approved-draft.md
.claude/plans/PLAN-166/W1-land-runbook.md
.claude/plans/PLAN-166/architect/round-1/approved.md
.claude/plans/PLAN-166/debate/round-1/anonymization-map.md
.claude/plans/PLAN-166/debate/round-1/consensus.md
.claude/plans/PLAN-166/debate/round-1/devops-engineer.md
.claude/plans/PLAN-166/debate/round-1/proposal.md
.claude/plans/PLAN-166/debate/round-1/security-engineer.md
.claude/plans/PLAN-166/debate/round-1/vp-engineering.md
.claude/plans/PLAN-166/debate/round-2/anonymization-map.md
.claude/plans/PLAN-166/debate/round-2/consensus.md
.claude/plans/PLAN-166/debate/round-2/devops-engineer.md
.claude/plans/PLAN-166/debate/round-2/security-engineer.md
.claude/plans/PLAN-166/debate/round-2/vp-engineering.md
.claude/plans/PLAN-166/debate/round-3/anonymization-map.md
.claude/plans/PLAN-166/debate/round-3/devops-engineer.md
.claude/plans/PLAN-166/debate/round-3/security-engineer.md
.claude/plans/PLAN-166/debate/round-3/synthesis.md
.claude/plans/PLAN-166/debate/round-3/vp-engineering.md
.claude/plans/PLAN-166/repass-r1/MANIFEST.sha256
.claude/plans/PLAN-166/repass-r1/PROVENANCE.md
.claude/plans/PLAN-166/repass-r1/build-repass-payload.sh
.claude/plans/PLAN-166/repass-r1/paths.manifest.txt
.claude/plans/PLAN-166/repass-r1/payload.redacted.txt
.claude/plans/PLAN-166/repass-r1/transcript-r1.log
.claude/plans/PLAN-166/repass-r1/verdict-r1.txt
.claude/plans/PLAN-166/staged-manifest.sha256
6:file (`approved.md`) exists in the same Architect bundle directory
31:   a. Look for any sibling `.claude/plans/PLAN-NNN/architect/round-N/approved.md`
92:# PLAN-045 Wave 1 P0-01 — signer allowlist for sentinel .asc signatures.
525:# The GPG `.asc` continues to cover the whole file. Any tamper of any
995:    ``PLAN-EVIL/architect/round-1/approved.md -> /tmp/evil`` no longer
1005:        "PLAN-*/architect/round-*/approved.md",
1006:        "PLAN-*/architect/wave-0a/approved.md",      # PLAN-083 grandfather
1007:        "PLAN-*/architect/wave-0b/approved.md",      # PLAN-083 grandfather
1008:        "PLAN-*/architect/wave-1-2/approved.md",     # PLAN-083 grandfather
1009:        "PLAN-*/architect/wave-minus-1/approved.md", # PLAN-083 grandfather
1010:        "PLAN-*/staging/review/approved.md",         # PLAN-083 grandfather
1011:        "PLAN-*/approved.md",                        # plan-root sentinels
1012:        "PLAN-*/wave-*-approved.md",                 # S109 wave-N-approved.md
1014:        "PLAN-*/audit-v2/architect/round-*/approved.md",  # PLAN-044 audit-v2 historical
1028:    # ``PLAN-*/architect/round-*/approved.md``. The ``PLAN-*`` segment one
1031:    # ``architect/round-1/approved.md`` into the TRUSTED sentinel set —
1093:# transitively covers signer changes via .asc bytes (signer rotation
1126:# #10 observed that the grant key hashes only ``approved.md``'s bytes, so
1127:# mutating the ``.asc`` / signer allowlist / ADR-121 registry left a
1132:# the decision even when ``approved.md`` is byte-identical — closing the
1340:    detached ``.asc``, the legacy signer allowlist, and the ADR-121 YAML
1352:    sig_path = sentinel_path.with_name(sentinel_path.name + ".asc")
1390:    sig_path = sentinel_path.with_name(sentinel_path.name + ".asc")
1507:# ``.claude/plans/PLAN-*/**/approved.md`` is guarded by NEITHER rail, and
1509:# entirely — so an ``approved.md`` the AGENT writes mid-window GRANTS.
1531:# unguarded ``approved.md``, keep its ``Approved-By:`` line, ADD a target
1547:#     ("ceremony authoring where the .asc is being signed in parallel"):
1769:        "approved.md>, e.g. `shasum -a 256 <approved.md> | cut -d' ' -f1` "
1786:    2. **Detached GPG signature** at ``<sentinel>.asc`` — verified
1789:       .asc, bad signature, signer fpr not in allowlist, empty
1794:    in the parent shell short-circuits the .asc requirement. This is a
1802:    3. A sibling ``<sentinel>.asc`` detached GPG signature (unless env
1827:    #     approved.md, so a mutated .asc / allowlist / registry would ride
1881:    #           documentation. The GPG `.asc` continues to cover the
1989:    # to honor freshly-regenerated .asc files even when bytes are unchanged).
2103:            ".claude/plans/PLAN-NNN/architect/round-N/approved.md with "

exec
/bin/zsh -lc "nl -ba .claude/plans/PLAN-166/architect/round-1/approved.md | sed -n '1,24p'; nl -ba .claude/hooks/check_canonical_edit.py | sed -n '1330,1410p'; git diff --name-only | while read f; do case \""'$f" in .claude/hooks/*|.claude/governance/*|.claude/adr/*|.github/workflows/*|scripts/install.sh|scripts/upgrade.sh|scripts/_framework_manifest_set.sh) echo "$f";; esac; done' in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 131ms:
.claude/governance/pair-rail-verdict-template.md
.github/workflows/npm-publish.yml
.github/workflows/release.yml
.github/workflows/smoke-install.yml
scripts/_framework_manifest_set.sh
scripts/install.sh
scripts/upgrade.sh

exec
/bin/zsh -lc 'git check-ignore -v .claude/plans/PLAN-166/architect/round-1/approved.md .claude/plans/PLAN-166/architect/round-1/approved.md.asc || true; ls -la .claude/plans/PLAN-166/architect/round-1; grep -R "approved.md.asc" -n .gitignore .git/info/exclude .claude 2>/dev/null | head -30' in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 4192ms:
.claude/adr/ADR-121-sentinel-signers-rotation-policy.md:51:plus an `approved.md.asc` sentinel — and the canonical-edit hook will
.claude/adr/ADR-101-replay-redact-helper.md:103:- Wave D ceremony: `.claude/plans/PLAN-073/OWNER-WAVE-D-CEREMONY.sh` + sentinel `.claude/architect/round-1-plan-069-wave-d/approved.md.asc`
.claude/adr/ADR-100-trusted-dependencies-re-affirm.md:26:touched. The sentinel format is `architect/round-N/approved.md.asc`
.claude/adr/ADR-100-trusted-dependencies-re-affirm.md:127:GPG sentinels per `architect/round-N/approved.md.asc` covering
.claude/adr/ADR-136-AMEND-1-workflow-primitive-adoption.md:126:  `.claude/plans/PLAN-120/promotion-adr-136-amend-1/approved.md.asc`.
.claude/adr/ADR-042-AMEND-1-read-only-mcp-tools-expansion.md:199:  `.claude/plans/PLAN-096/approved.md.asc` Owner-GPG-signed).
.claude/adr/ADR-116-AMEND-1-kernel-extension-v2.md:499:  `.../approved.md.asc` — Wave A.4 sentinel + detached GPG.
.claude/adr/ADR-080-rail-anomaly-h4-defense-in-depth.md:308:# Produces approved.md.asc in same directory
.claude/adr/ADR-080-rail-anomaly-h4-defense-in-depth.md:824:- `.claude/plans/PLAN-059/architect/round-1/approved.md.asc` — GPG signature
.claude/adr/ADR-060-curated-skill-import-pipeline.md:238:- Sentinel artifact: `.claude/plans/PLAN-NNN/architect/wave-<N>/approved.md.asc`
.claude/adr/ADR-078-sentinel-cosign-clarification.md:35:   `architect/round-N/approved.md.asc` who authorize the canonical
.claude/plans/PLAN-142/staging/EXECUTION-RUNBOOK.md:26:   This produces approved.md.asc. Both rails already carry the Owner hot-key
.claude/plans/PLAN-142/architect/round-2/approved.md:33:Authorization: Owner-signed GPG detached signature (approved.md.asc), signer
.claude/plans/PLAN-156-FOLLOWUP/land-followup.sh:321:  rm -f "$dir/approved.md.asc"
.claude/plans/PLAN-156-FOLLOWUP/land-followup.sh:322:  gpg --local-user "$KEY" --armor --detach-sign --output "$dir/approved.md.asc" "$dir/approved.md" \
.claude/plans/PLAN-140-compaction-hook-origin-dropfix.md:90:    `approved.md.asc` (signer must be in `.claude/sentinel-signers.txt`).
.claude/plans/PLAN-156/land-plan156.sh:101:  rm -f "$dir/approved.md.asc"
.claude/plans/PLAN-156/land-plan156.sh:102:  gpg --local-user "$KEY" --armor --detach-sign --output "$dir/approved.md.asc" "$dir/approved.md" \
.claude/plans/PLAN-158/ga-review-transcript.txt:491:diff --git a/.claude/plans/PLAN-157/architect/grad-cpp/approved.md.asc b/.claude/plans/PLAN-157/architect/grad-cpp/approved.md.asc
.claude/plans/PLAN-158/ga-review-transcript.txt:495:+++ b/.claude/plans/PLAN-157/architect/grad-cpp/approved.md.asc
.claude/plans/PLAN-158/ga-review-transcript.txt:614:diff --git a/.claude/plans/PLAN-157/architect/grad-data-ml/approved.md.asc b/.claude/plans/PLAN-157/architect/grad-data-ml/approved.md.asc
.claude/plans/PLAN-158/ga-review-transcript.txt:618:+++ b/.claude/plans/PLAN-157/architect/grad-data-ml/approved.md.asc
.claude/plans/PLAN-158/ga-review-transcript.txt:700:diff --git a/.claude/plans/PLAN-157/architect/grad-golang/approved.md.asc b/.claude/plans/PLAN-157/architect/grad-golang/approved.md.asc
.claude/plans/PLAN-158/ga-review-transcript.txt:704:+++ b/.claude/plans/PLAN-157/architect/grad-golang/approved.md.asc
.claude/plans/PLAN-158/ga-review-transcript.txt:783:diff --git a/.claude/plans/PLAN-157/architect/grad-jvm/approved.md.asc b/.claude/plans/PLAN-157/architect/grad-jvm/approved.md.asc
.claude/plans/PLAN-158/ga-review-transcript.txt:787:+++ b/.claude/plans/PLAN-157/architect/grad-jvm/approved.md.asc
.claude/plans/PLAN-158/ga-review-transcript.txt:965:diff --git a/.claude/plans/PLAN-157/architect/w1/approved.md.asc b/.claude/plans/PLAN-157/architect/w1/approved.md.asc
.claude/plans/PLAN-158/ga-review-transcript.txt:969:+++ b/.claude/plans/PLAN-157/architect/w1/approved.md.asc
.claude/plans/PLAN-158/ga-review-transcript.txt:1010:-  [ -f "$SENTINEL_DIR/approved.md.asc" ] || die "sentinel signature missing: $SENTINEL_DIR/approved.md.asc"
.claude/plans/PLAN-158/ga-review-transcript.txt:1018:+  rm -f "$SENTINEL_DIR/approved.md.asc"

exec
/bin/zsh -lc "grep -R \"test-ownership-table\\|test-ownership-verdict-unit\" -n .github Makefile .claude scripts 2>/dev/null | head -100; git ls-files scripts/tests/test-ownership-table.sh scripts/tests/ownership_table.tsv; git log -1 --oneline -- scripts/tests/test-ownership-table.sh scripts/tests/ownership_table.tsv" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 4149ms:
.claude/plans/PLAN-167/debate/round-1/consensus.md:99:   is `scripts/tests/test-ownership-verdict-unit.sh`, wired per-PR; the
.claude/plans/PLAN-167/debate/round-1/security-engineer.md:60:   target at `scripts/tests/test-ownership-table.sh:291` and NO line of
.claude/plans/PLAN-167/debate/round-1/security-engineer.md:126:   prose. `_ABORT_MARKERS` (test-ownership-table.sh:182) matches the
.claude/plans/PLAN-167/debate/round-1/proposal.md:40:| `scripts/tests/test-ownership-table.sh` | e2e: real scripts, zero mock, per-cell timeout |
.claude/plans/PLAN-167/debate/round-1/devops.md:32:  scripts/tests/test-ownership-table.sh, scripts/tests/ownership_table.tsv,
.claude/plans/PLAN-167/debate/round-1/devops.md:40:  test-ownership-table.sh:347 calls: git -C REPO_ROOT archive v1.2.0 SPEC/v1
.claude/plans/PLAN-167/debate/round-1/devops.md:77:  The fallback watchdog at test-ownership-table.sh:86-87 starts a subshell
.claude/plans/PLAN-167/debate/round-1/devops.md:87:     scripts/tests/test-ownership-table.sh
.claude/plans/PLAN-167/debate/round-1/devops.md:106:   filename (e.g., scripts/tests/test-ownership-verdict-unit.sh), the
.claude/plans/PLAN-167/debate/round-1/qa-architect.md:17:- OQ-7 (`fault=` as a prose-encoded tenth axis) is a blocking gap the document itself flags as "the one option that should not survive." The harness parses only one fault value (`backup_unwritable`, `test-ownership-table.sh:516`); a second fault type added to `note` without a matching harness case silently skips injection and the row may GREEN for the wrong reason.
.claude/plans/PLAN-167/debate/round-1/qa-architect.md:23:- **R-QA2** — SEVERITY: HIGH. The three TIMEOUT rows (`OWN-0025`, `OWN-0029`, `OWN-0033`) expect verdicts that their surface guards are supposed to produce (`ABORT_SURFACE/HASH_PRIOR_RECORD`, `PRESERVE_UNOWNED/HASH_NONE`, `PRESERVE_UNOWNED/HASH_NONE` respectively). Verified: all three time out at rc=137 (`test-ownership-table.sh --only OWN-0025,OWN-0029,OWN-0033 --keep` output). When W2 fixes the scanner, these rows must not only stop timing out — they must reach the correct SURFACE guard. The harness has no mechanism to distinguish "scanner no longer blocks, surface guard fires correctly" from "scanner no longer blocks, some other pre-guard aborts first." Without a standalone scanner test (FIFO at surface path → scan exits 0), a scanner fix that merely moves the hang point is indistinguishable from a complete fix. These rows will turn GREEN but the guards they claim to test may still be unreachable.
.claude/plans/PLAN-167/debate/round-1/qa-architect.md:41:3. **TIMEOUT rows need a staged verification protocol.** The W2 task that fixes the scanner (§5.7, `_emit_deprecation_warnings`) must be paired with an explicit positive control: a standalone invocation of the scanner subsystem alone, given a target tree containing a FIFO at the `SPEC/v1` path, that exits 0. This control must be documented in the W2 execution record and must precede the green count of the three TIMEOUT rows as evidence. Without it, a scanner "fix" that moves the blocking point (e.g., a second reader further downstream) would make the three rows GREEN without testing the guards they claim to cover. **Actionable as a plan amendment to §W2**: add a step "W2.0 — scanner positive control: `test-ownership-table.sh --only OWN-0025` preceded by a standalone scanner probe that confirms non-blocking exit". This does not change the table or the function signature.
.claude/plans/PLAN-167/debate/round-1/qa-architect.md:57:2. **OWN-0024 and OWN-0027 are RED for a reason the plan does not address.** Running `test-ownership-table.sh --only OWN-0024,OWN-0027` produces `got=PRESERVE_OWNED/HASH_PRIOR_RECORD` for both, not `ABORT_SURFACE`. The `fault=backup_unwritable` injection makes `.claude.bak` unwritable (chmod 500, line 516-518). The scripts do emit the ABORT markers on the backup-failure path (upgrade.sh lines 1954-1955, 2059-2060), and the harness redirects stderr to `$out`. The RED result means the backup-failure path is not being reached — either the backup attempts a different directory, or the chmod 500 on `.claude.bak` does not prevent the actual backup path the scripts use. This is a fixture defect, not a subject defect: the fault injection is not injecting the fault. The plan does not document this specific RED cause, and it is distinct from the four documented fixture defects. It should be verified before W2 treats these rows as "code to fix" rather than "fixture to fix."
.claude/plans/PLAN-167-ownership-decision-table.md:185:#### W0.3 — `scripts/tests/test-ownership-table.sh` (gerador + runner)
.claude/plans/PLAN-167-ownership-decision-table.md:230:        scripts/tests/test-ownership-table.sh \
.claude/plans/PLAN-167-ownership-decision-table.md:356:- [ ] **AC-3** `test-ownership-table.sh` roda toda linha contra os
.claude/plans/PLAN-167-ownership-decision-table.md:460:- `scripts/tests/test-ownership-table.sh` (`bash -n` + `shellcheck -S warning` limpos)
.claude/plans/PLAN-167-ownership-decision-table.md:555:2. **e2e**, o `test-ownership-table.sh` atual (~10 min, prova que os
scripts/tests/test-ownership-verdict-unit.sh:8:#   test-ownership-table.sh — do the callers OBSERVE the dimensions
scripts/tests/test-ownership-verdict-unit.sh:22:#   test-ownership-verdict-unit.sh            every row
scripts/tests/test-ownership-verdict-unit.sh:23:#   test-ownership-verdict-unit.sh --only OWN-0013,OWN-0021
scripts/tests/test-ownership-verdict-unit.sh:24:#   test-ownership-verdict-unit.sh --quiet    only the summary
scripts/tests/test-ownership-table.sh:14:#   test-ownership-table.sh              run every row
scripts/tests/test-ownership-table.sh:15:#   test-ownership-table.sh --only OWN-0013
scripts/tests/test-ownership-table.sh:16:#   test-ownership-table.sh --map        emit the map only (no pass/fail exit)
scripts/tests/test-ownership-table.sh:17:#   test-ownership-table.sh --list       list row ids and exit
scripts/tests/test-ownership-table.sh:18:#   test-ownership-table.sh --keep       keep the scratch dir (debugging)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-KhPvyEOU' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-irn8vEL2' (errno=Operation not permitted)
scripts/tests/ownership_table.tsv
scripts/tests/test-ownership-table.sh
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-NdYlkMdP' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-w8ADYdWT' (errno=Operation not permitted)
bc53747 spec(PLAN-167): C1 do consenso — fault vira coluna, legacy_pristine_partial vira valor

exec
/bin/zsh -lc "sed -n '1,640p' .claude/plans/PLAN-167-ownership-decision-table.md; printf '\\n--- CONSENSUS ---\\n'; cat .claude/plans/PLAN-167/debate/round-1/consensus.md" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
---
id: PLAN-167
title: Tabela de decisão de propriedade — sair do loop de patch-por-ramo no F3
status: reviewed
created: 2026-08-06
reviewed_at: 2026-08-06
owner: CEO
depends_on: [PLAN-166]
budget_tokens: 180-260k
budget_sessions: 1-2
context_risk: high
external_wait: assinatura GPG do Owner (manhã) para o land do pack
tags: [upgrade, install, ownership, testing, canonical, refactor]
---

# PLAN-167 — Tabela de decisão de propriedade

> **Ratificação (2026-08-06, S296).** Owner instruiu, textualmente:
> *"escreve o PLAN-167 pra resolver tudo isso de uma vez… deixa o plano
> pronto para ser executado"* e *"já deixa o plano perfeito e pronto pra
> executar"*. `draft → reviewed` registrado com base nessa instrução.
> **`reviewed` ratifica o PLANO — não libera edição canônica.** Todo
> arquivo guardado continua atrás da cerimônia GPG do W5.

> **Origem.** Este plano nasce de um loop observado, não de uma ideia.
> Na S296 o rail codex rodou **11 rodadas** sobre o F3 do PLAN-166
> (propriedade por registro de entrega). Resultado: **20 achados reais
> aplicados, 4 ainda abertos, zero sinal de convergência** — e cerca de
> metade dos achados recentes eram **regressões do fix da rodada
> imediatamente anterior**. O e2e de 45 checks passou verde durante os
> 20. Este plano ataca a causa, não mais uma célula.

---

## 0. Primeira hora (checklist literal do run)

Faça nesta ordem. Não pule para o W2 — a tabela é o produto, o refactor
é consequência dela.

1. `git rev-parse HEAD` → deve ser `516e64e…`. Se não for, PARE e
   reporte: o estado inicial mudou e este plano assume o de S296.
2. `git status --porcelain` → esperado sujo com grupo A + F3 (S296).
   **Não limpe, não faça `git checkout -- .`, não `git stash`.**
3. Ler, na íntegra, os 11 vereditos:
   `.claude/plans/PLAN-166/archive/codex-review-w1-{ceremony,round2..round11}.md`.
   São a documentação mais densa do espaço que existe.
4. Ler `.claude/plans/PLAN-166/W1-ceremony-log.md` §"Rounds 6-9" e
   §"Follow-ups nomeados".
5. Ler `ADR-155` + `ADR-155-AMEND-1`.
6. Só então começar o W0.1.

---

## 1. Diagnóstico (o porquê do loop)

O F3 é um **produto cartesiano** implementado como `if` espalhado:

| Dimensão | Valores |
|---|---|
| `surface` | `spec` (`SPEC/v1`) · `protocol` (`PROTOCOL.md`) · `marker` (`.claude/.framework-version`) |
| `prior_record` | `none` · `hash` · `link_match` · `link_retargeted` |
| `live_type` | `absent` · `dir` · `regular` · `symlink` · `special` (FIFO/socket) · `dir_empty` |
| `live_content` | `pristine` (== fonte) · `edited` · `legacy_pristine` (fingerprint v1.2−) |
| `source_has` | `yes` · `no` (downgrade `--pin` pré-v1.3) |
| `mode` | `copy` · `link` |
| `ceremony` | `user` · `maintainer` |
| `operation` | `install_fresh` · `install_rerun` · `upgrade` |
| `skip_requested` | `none` · `self` · `descendant` |

Três consequências, todas verificadas na S296:

1. **Sem especificação executável.** "Correto" é decidido ramo a ramo.
   Ramos diferentes codificam premissas **contraditórias sobre a mesma
   pergunta** — por isso consertar A quebra B.
2. **Decisão duplicada entre `install.sh` e `upgrade.sh`.** A classe
   "irmão atrasado" foi **4 dos 20 achados** — 20%.
3. **O e2e não cobre o espaço.** 45 checks lineares, 8 cenários. O rail
   virou o único explorador: **uma célula por rodada de ~40 min.**

**Anti-objetivo explícito:** este plano NÃO é "corrigir os 4 achados
abertos do round 11". Corrigir ramo a ramo É o loop. Os 4 abertos, como
os 20 aplicados, viram **linhas da tabela**.

---

## 2. A solução (5 movimentos)

1. **Escrever a tabela.** Onde as contradições aparecem ANTES de virar bug.
2. **Fechar o veredito num enum pequeno**, derivado da tabela, nunca de
   memória ([[feedback-closed-sets-must-be-derived-not-recalled]]).
3. **UMA função decide.** `_ownership_verdict()`. `install.sh` e
   `upgrade.sh` param de decidir e passam a **executar**.
4. **A tabela vira a suíte.** Fix que quebra outra célula falha na hora.
5. **O rail revisa a TABELA, não o diff.** Espaço finito ⇒ converge.

### 2.1 Enum de veredito (rascunho — o debate do W1 ratifica ou emenda)

```
DELIVER          — escrever a versão do framework no alvo
REFRESH          — substituir conteúdo existente (backup-then-replace)
PRESERVE_OWNED   — não tocar; MANTER o registro de entrega
PRESERVE_UNOWNED — não tocar; NÃO registrar (adotante é dono)
OMIT_RECORD      — alvo permanece; registro sai do manifesto
ABORT_SURFACE    — recusar esta superfície, rc 0, warning nomeado
```

Segundo campo, ortogonal — **de onde sai o hash do manifesto**:

```
HASH_TARGET | HASH_SOURCE | HASH_PRIOR_RECORD | HASH_CANONICAL_POINTER | HASH_NONE | LINK_RECORD
```

O par `(verdict, hash_source)` é a saída completa. **Todo bug da S296
foi uma célula com o par errado.** `FMS_HASH_ROOT_PATHS` e
`FMS_LINK_PATHS`, criados na S296, são casos particulares que o campo
`hash_source` explícito **substitui** — não somar, substituir.

---

## 3. Fronteira canônica (verificada 2026-08-06)

| Superfície | Guard | Quem escreve |
|---|---|---|
| `scripts/install.sh`, `scripts/upgrade.sh` | 🔒 | só sob sentinel |
| `scripts/_framework_manifest_set.sh`, `scripts/_hash_lib.sh` | 🔒 | só sob sentinel |
| `.claude/adr/ADR-*.md`, `.github/workflows/*.yml` | 🔒 | só sob sentinel |
| `scripts/tests/**` | ✅ livre | run autônomo |
| `docs/**`, `.claude/plans/**` (exceto `spec.md`) | ✅ livre | run autônomo |

**Consequência de projeto:** a tabela e a suíte inteira nascem em
superfície LIVRE e **podem ser commitadas pelo run** (foi assim no W0 do
PLAN-166). O refactor dos 4 guardados é desenvolvido em **clone overlay**
(padrão S279) e entregue como pack staged. O Owner assina **uma vez**.

---

## 4. Ondas

### W0 — Tabela + suíte (LIVRE, sem sentinel, COMMITÁVEL)

#### W0.1 — `docs/ownership-decision-table.md`

Prosa: as 9 dimensões, a **regra de poda** (abaixo), o par de cada
célula não-óbvia com justificativa, e as perguntas abertas.

**Fontes de entrada, nesta ordem de autoridade:**
1. os **11 vereditos do codex** — cada achado é uma célula com veredito conhecido;
2. o ramo vivo hoje em `install.sh`/`upgrade.sh` (o que o código faz);
3. `ADR-155` + `ADR-155-AMEND-1` (a intenção declarada).

Onde 1, 2 e 3 discordarem: **registrar como pergunta aberta e levar ao
debate do W1.** Não resolver sozinho.

**Regra de poda (obrigatória — sem ela o espaço explode):** uma célula é
ILEGAL quando a combinação não pode existir num alvo real. Declarar cada
regra de poda com o motivo, no doc. Exemplos que já se sabe:
- `operation=install_fresh` ⇒ `prior_record=none` e `live_type=absent`
- `prior_record=link_*` ⇒ `mode=link`
- `surface=protocol` ⇒ `live_type ∈ {absent, regular, symlink}` (nunca `dir`)
- `skip_requested=descendant` ⇒ `surface=spec` (só ele é árvore)
- `ceremony=user` ⇒ `surface ∈ {marker}` para entrega; `spec`/`protocol`
  só aparecem como resíduo de instalação maintainer anterior

Poda silenciosa é proibida: toda combinação removida sai **nomeada**.

#### W0.2 — `scripts/tests/ownership_table.tsv` (FONTE ÚNICA)

TSV com cabeçalho, uma linha por célula legal. Colunas, nesta ordem:

```
id  surface  prior_record  live_type  live_content  source_has  mode
ceremony  operation  skip_requested  expect_verdict  expect_hash_source
origin  note
```

- `id` — estável, `OWN-0001`… (o teste referencia por id; nunca por linha).
- `origin` — de onde a linha veio: `r7-F2`, `r11-F1`, `adr-155`, `derived`.
  **Os 20 achados aplicados e os 4 abertos DEVEM aparecer aqui pelo id do
  round** (é o AC-5).
- `note` — só quando o veredito não é óbvio.

O doc do W0.1 explica; **o TSV é a verdade**. Nenhum valor duplicado
entre os dois.

#### W0.3 — `scripts/tests/test-ownership-table.sh` (gerador + runner)

**Contrato de observação** — como o veredito é observado sem parsear
prosa. Para cada linha: montar fixture, capturar o estado ANTES, rodar o
script REAL, capturar o estado DEPOIS, e derivar:

*`verdict` observado*, de (estado do alvo, manifesto):

| Alvo depois | Manifesto depois | ⇒ verdict |
|---|---|---|
| conteúdo == fonte, não existia antes | tem registro | `DELIVER` |
| conteúdo == fonte, existia e mudou, cópia em `BAK_DIR` | tem registro | `REFRESH` |
| byte-idêntico ao ANTES | tem registro | `PRESERVE_OWNED` |
| byte-idêntico ao ANTES | sem registro | `PRESERVE_UNOWNED` |
| byte-idêntico ao ANTES | registro sumiu (havia antes) | `OMIT_RECORD` |
| byte-idêntico ao ANTES + warning nomeado + rc 0 | sem registro | `ABORT_SURFACE` |

*`hash_source` observado*: o harness calcula os 4 candidatos —
`sha256(alvo_depois)`, `sha256(fonte)`, digest do registro anterior,
hash canônico do ponteiro — e vê **qual deles** o manifesto gravou. Se
o registro for `LINK  …`, `hash_source = LINK_RECORD`. Se não houver
registro, `HASH_NONE`. **Ambíguo** (dois candidatos iguais) ⇒ o harness
DIFERENCIA os fixtures até desempatar; nunca "resolve" por preferência.

Requisitos duros do harness:
- roda os scripts **REAIS**; zero mock do sujeito sob teste
  ([[feedback-livefire-catches-what-fixtures-miss]]);
- fixture em `mktemp -d`, nunca em `$HOME` nem no repo;
- **timeout por célula** (`timeout 60`) — o achado do FIFO no round 9 era
  literalmente um `cp` que pendura;
- `--only <id>` para rodar uma célula; `--map` para emitir o mapa;
- saída determinística e ordenada por `id`.

#### W0.4 — Mapa-baseline

Rodar a suíte contra a árvore ATUAL (com os 20 fixes) e gravar
`scripts/tests/ownership-baseline-map.txt`: por `id`, verde/vermelho e o
par observado vs esperado. Vermelho é **esperado** aqui — é o ponto de
partida e a métrica de progresso do W2.

#### W0.5 — Commit (superfície livre)

```
git add docs/ownership-decision-table.md \
        scripts/tests/ownership_table.tsv \
        scripts/tests/test-ownership-table.sh \
        scripts/tests/ownership-baseline-map.txt \
        .claude/plans/PLAN-167-ownership-decision-table.md
git commit -m "plan(PLAN-167): tabela de decisão de propriedade + suíte gerada + mapa baseline"
```

**Adds explícitos, NUNCA `git add -A`** — a árvore tem canônicos sujos.

**Gate W0:** a suíte roda, produz o mapa, e o commit contém **só** os 5
paths acima (`git show --stat HEAD` confere).

### W1 — Debate L3 (obrigatório, PROTOCOL.md)

`/debate start PLAN-167 "tabela de decisão + função única de veredito"`

Arquétipos a convocar (routing de `.claude/team.md`): **qa-architect**
(a suíte é o coração), **security-engineer** (apagar conteúdo do
adotante é a consequência das células erradas — dois P1 do round 9 eram
isso), **devops** (install/upgrade são superfície de distribuição).

Pauta fechada em 3 pontos:
1. **O enum é o certo?** 6 vereditos + 6 fontes-de-hash cobrem as células
   sem forçar nenhuma? Falta? Sobra?
2. **As perguntas abertas do W0.1** (onde codex/código/ADR discordam).
3. **Assinatura e domicílio da função.** Uma lib NOVA seria um path
   canônico novo → exige entrada em `_CANONICAL_GUARDS` → **cerimônia de
   kernel**. Preferir `scripts/_framework_manifest_set.sh` (já guardado)
   salvo veto fundamentado; veto escala ao Owner de manhã, não vira
   cerimônia de kernel no meio da noite.

**Saída:** `debate/round-{1,2,3}/consensus.md` (livre) + `ADR-190` em
`staged/` (ADR é guardado — não escrever em `.claude/adr/`).

### W2 — Implementação em clone overlay

```
CLONE="$SCRATCH/plan167-overlay"
git clone --local . "$CLONE"        # pega o commit do W0.5
cd "$CLONE" && git checkout -b plan167-refactor
```

Trabalhar **só** ali. A árvore viva não recebe edição canônica — é a
regra 1 do §6.

- **W2.1** Implementar `_ownership_verdict()` conforme o consenso do W1.
- **W2.2** Refatorar `install.sh`/`upgrade.sh` para **chamar e executar**
  o veredito. Os ramos de decisão antigos SAEM.
- **W2.3** `_framework_manifest_set.sh` passa a receber `hash_source`
  explicitamente. `FMS_HASH_ROOT_PATHS`/`FMS_LINK_PATHS` são removidos —
  substituídos, não somados.
- **W2.4** Dirigir o mapa até **100% verde**. Regressão em célula já
  verde = **para e corrige antes de seguir** (esse é o mecanismo que
  substitui o loop de 40 min).
- **W2.5** Gates completos no clone: e2e F3 45/45, bateria
  `python3 -m pytest .claude/scripts/tests/ -q`, `shellcheck -S warning`,
  `bash -n`.

**Gate W2:** mapa 100% verde **e** toda linha com `origin` de round
(os 20 + os 4) verde.

### W3 — Rail codex sobre a TABELA (limitado por construção)

Alvo da revisão muda — é a diferença central em relação à S296.

```
cd "$CLONE"
caffeinate -dims nohup codex exec review --uncommitted </dev/null \
  > .../codex-plan167-r1.md 2>&1 &
```

Pergunta ao rail: *"algum veredito desta tabela está errado, e falta
alguma célula legal?"* — não "revise o diff".

**Esperar pelo ARTEFATO, nunca por processo:**
`until [ -s "$OUT" ]; do sleep 15; done`. Um `until ! pgrep -f "codex …"`
**nunca termina** — casa o próprio waiter
([[feedback-pgrep-waiter-matches-itself]]).

**Regra de parada (dura, aprendida na S296):**
- APPROVE, **ou**
- 2 rodadas consecutivas sem achado novo, **ou**
- **teto de 4 rodadas** — atingido, o run **PARA e reporta**. Não
  patcheia mais. Sob nenhuma hipótese entra na 5ª.

Todo achado do rail vira **linha de tabela** → suíte re-roda → mapa
volta a 100%. Achado que não couber como linha é **furo do MODELO**:
registrar e levar ao Owner, não remendar.

### W4 — Montagem do pack (staged, sem assinar)

- `.claude/plans/PLAN-167/staged/` com cópias dos guardados + patches + `ADR-190`
- `staged-manifest.sha256` **rastreado**
  ([[feedback-staged-inputs-need-tracked-hash-manifest]])
- `W4-approved-draft.md`: Scope em grupos de revert (**grupo A do
  PLAN-166 + os guardados do PLAN-167**) e `Anchor-SHA: <PLACEHOLDER>`
  — inassinável de propósito
- `W4-land-runbook.md`: applies, gates, §touched−scope, commit.
  **Snippets em POSIX** — `[[:space:]]`, nunca `\s` (BSD não suporta; o
  §7 do PLAN-166 devolvia falso "tudo fora de escopo")
- `OWNER-W4-LAND.sh` cobrindo **todo** path do staged, com espelhamento
  por **tabela path→patch**, nunca lista manual

**Gate W4 (automatizado, não a olho):**
- `shasum -c staged-manifest.sha256` rc=0 (rodar **da raiz** — os paths
  são repo-relative)
- `git apply --check` em todo patch
- diff automatizado **staged-vs-script-de-land**: todo arquivo staged
  aparece no `OWNER-W4-LAND.sh` (a omissão de `_parity_classify.py` foi
  o achado F3 do round 8)

### W5 — Manhã do Owner (não-autônomo)

1. Ler o sumário e o `W4-approved-draft.md`
2. Fixar `Anchor-SHA` = HEAD e assinar (`gpg --detach-sign --armor`;
   se der "No pinentry": `export GPG_TTY=$(tty); gpgconf --kill gpg-agent`)
3. `bash OWNER-W4-LAND.sh` → gates → `git commit -S`
4. `git push` → CI verde → rc.2 → hold 24h → GA

---

## 5. Critérios de aceite

- [ ] **AC-1** `docs/ownership-decision-table.md` enumera as 9 dimensões,
      declara **toda** regra de poda com motivo, e não duplica valores do TSV.
- [ ] **AC-2** `ownership_table.tsv` é a fonte única, com as 14 colunas
      e `id` estável.
- [ ] **AC-3** `test-ownership-table.sh` roda toda linha contra os
      scripts REAIS (zero mock do sujeito), com timeout por célula.
- [ ] **AC-4** Mapa **100% verde** no clone do W2.
- [ ] **AC-5** Os 20 achados aplicados + os 4 abertos do round 11 estão
      no TSV com `origin` nomeando o round, todos verdes. **Enumeração
      literal, não contagem** — a fonte é
      `archive/codex-review-w1-round{2..11}.md`.
- [ ] **AC-6** `grep -n _ownership_verdict scripts/install.sh scripts/upgrade.sh`
      mostra chamada nos dois, e os ramos de decisão antigos saíram.
- [ ] **AC-7** e2e F3 45/45 · bateria sem failure · `shellcheck -S warning`
      limpo · `bash -n` OK.
- [ ] **AC-8** Rail do W3 encerrado por APPROVE, por 2 rodadas limpas, ou
      por teto — **com o motivo registrado**. Encerrar por silêncio é
      proibido ([[feedback-pair-rail-clean-round-not-proof]]).
- [ ] **AC-9** Gates do W4 verdes, incluindo o diff staged-vs-script.
- [ ] **AC-10** `ADR-190` registra a tabela como contrato e declara o
      `ADR-155-AMEND-1` **emendado** (não revogado).

---

## 6. Regras do run autônomo (anti-loop)

Estas regras existem porque a S296 as violou na prática.

1. **Nunca editar arquivo canônico na árvore viva.** Todo W2 é no clone.
   A árvore viva só muda no W5, pelas mãos do Owner.
2. **Nunca corrigir ramo a ramo.** Achado vira **linha de tabela**; a
   correção é na função única.
3. **Teto de 4 rodadas no W3.** Atingido, PARA e reporta.
4. **Toda claim do rail é verificada antes de virar código** — controle
   plantado, positivo E negativo. Foi o que segurou a qualidade na S296.
5. **Ao consertar um, varrer a família.** 4 achados da S296 foram irmãos
   atrasados (`install.sh` fazendo diferente do `upgrade.sh`).
6. **Espelhamento por tabela path→patch**, nunca lista manual — o
   `mirror-fixes.sh` da S296 cobria 2 de 4 arquivos e **nenhum gate
   acusou** (o `shasum -c` valida o staged contra si mesmo, não contra a
   árvore viva).
7. **Snippets em POSIX**, nunca `\s` em `grep`/`sed`.
8. **`git add` explícito, nunca `-A`** — a árvore tem canônicos sujos.
9. **Esperar por artefato, nunca por `pgrep -f`** (o waiter casa a si
   mesmo). Se o log diz que acabou, acabou — o log ganha do pgrep.
10. **Se o mapa não fechar em 100% ou o run travar**, o entregável passa
    a ser o **relatório** (tabela + mapa + o que falta), não um pack
    parcial. Pack parcial assinado é pior que nenhum pack.

---

## 7. Disposição do PLAN-166

- **Grupo A (trem de release)** — `npm-trusted-publisher.txt`,
  `pair-rail-verdict-template.md`, `test_release_workflow_asserts.py`,
  `npm-publish.yml`, `release.yml`, `RELEASE.md`: **zero achados em 11
  rodadas**. Permanece aplicado na árvore viva e entra no mesmo commit
  do W5. Não é objeto deste plano — **não mexer**.
- **Grupo B (F3)** — a lógica de decisão é **substituída** pelo produto
  do W2. Os fixes da S296 seguem na árvore como referência até o W5, e
  são sobrescritos pelas cópias staged no land.
- `ADR-155-AMEND-1` é **emendado** pelo `ADR-190`, não revogado: a
  intenção estava certa; a realização por ramos espalhados é que não.
- O sentinel atual do PLAN-166 (anchor `516e64e`) fica **obsoleto** — o
  W5 assina um novo cobrindo grupo A + os guardados do PLAN-167.
- Os **follow-ups nomeados** no `W1-ceremony-log.md` (transição
  maintainer→user no e2e; emits de GRANT do kernel; matcher do
  GUIA-COMPLETO; deferred-apply Route B) seguem válidos. O primeiro deles
  é **absorvido** por este plano: vira célula da tabela.

---

## 8. Riscos

| Risco | Mitigação |
|---|---|
| A tabela nasce incompleta e o loop volta em outra forma | O W3 revisa a TABELA; célula faltando é achado de primeira classe. Teto de 4 rodadas impede o renascimento. |
| O refactor quebra caminho hoje verde | Mapa-baseline do W0.4 é o controle: célula verde que fica vermelha para o W2 na hora. |
| Espaço grande demais para enumerar | Regra de poda do W0.1, com motivo declarado por regra. Poda silenciosa é proibida. |
| Observação do veredito ambígua (2 candidatos de hash iguais) | O harness diferencia os fixtures até desempatar; nunca resolve por preferência. |
| Run noturno não termina | Regra 10: relatório, não pack parcial. |
| Debate pede lib nova (path canônico novo) | Exigiria cerimônia de kernel. Preferência declarada pela lib existente; veto escala ao Owner de manhã. |

---

## 9. Registro de execução

<!-- o run autônomo anexa aqui: commit ativo, onda corrente, próxima ação concreta -->

- **Estado inicial (2026-08-06, S296):** HEAD `516e64e`, árvore suja com
  os 20 fixes do F3 (rounds 6-11) + grupo A aplicado, **4 achados do
  round 11 abertos e deliberadamente NÃO corrigidos** (viram linhas da
  tabela). 11 vereditos do codex em `.claude/plans/PLAN-166/archive/`.
  e2e 45/45, bateria 5011 passed / 0 failed, manifesto staged 34/34.
- **Próxima ação:** §0 checklist da primeira hora, item 1.

### Run autônomo — 2026-08-06/07 (S297)

> Bloco de retomada. Uma sessão nova lê SÓ isto para continuar.

**§0 (primeira hora): CONCLUÍDO.** HEAD confirmado `516e64e`, árvore suja
preservada (nada de `checkout --`), 11 vereditos + `W1-ceremony-log.md` +
`ADR-155`/`AMEND-1` lidos na íntegra.

**W0.1/W0.2/W0.3: CONCLUÍDOS.** Artefatos na superfície LIVRE, ainda
NÃO commitados:
- `docs/ownership-decision-table.md`
- `scripts/tests/ownership_table.tsv` (61 linhas, 14 colunas, ids estáveis)
- `scripts/tests/test-ownership-table.sh` (`bash -n` + `shellcheck -S warning` limpos)

**Correções de rota já aplicadas (não repetir):**
1. **3 das 5 regras de poda do §W0.1 deste plano são FALSAS** e foram
   rejeitadas com motivo no doc §4.1. A pior: `prior_record=link_* ⇒
   mode=link` teria apagado o achado ABERTO r11-F1 do espaço.
2. **AC-5: são 35 achados literais, não 24.** A contagem de memória estava
   errada. Ledger completo no doc §8 (29 células + 2 invariantes + 4
   não-células nomeadas).
3. **1º mapa-baseline (40 RED) era instrumento quebrado, não código.**
   ~16 vermelhos vinham de o harness desempatar `hash_source` por
   PREFERÊNCIA DE ORDEM. Causa-raiz: o fixture usava a MESMA fonte para o
   install-base e para o upgrade, tornando `HASH_SOURCE` e
   `HASH_PRIOR_RECORD` iguais por construção. Curado DIFERENCIANDO o
   fixture (fonte `src-next` perturbada), nunca relaxando o critério.

**Achados NOVOS da tabela (viram linha, NÃO patch de ramo):**
- `_refresh_protocol_pointer` não tem guard de destino não-regular nem de
  symlink-leaf (doc §5.1). R-11 mostrou que o guard de ancestral seria
  vacuoso ali — não remendar.
- **§5.7 (o mais sério):** o FIFO NÃO trava na rota do marker; trava em
  `check-model-deprecations.py`, scanner que varre a árvore ANTES de
  qualquer refresh. Provado isolado com controle positivo E negativo.
  Efeito colateral pior: os guards r2-F3/r9-F3 estão MASCARADOS — nenhum
  e2e os alcança, então uma suíte verde não prova nada sobre eles.

**Onda corrente:** W0.4 — mapa-baseline **v3** rodando (~25 min).

**Três defeitos de FIXTURE achados em três triagens sucessivas** (o
instrumento precisou de tanto escrutínio quanto o sujeito):

| # | Defeito | Sintoma | Cura |
|---|---|---|---|
| 1 | fonte única p/ install-base e upgrade | `HASH_SOURCE` ≡ `HASH_PRIOR_RECORD`; harness desempatava por PREFERÊNCIA | fonte `src-next` perturbada |
| 2 | `install_fresh` extraía um base | rerun disfarçado de fresh; violava a R-01 | alvo estruturalmente vazio |
| 3 | symlink repontado em TODA linha | linhas `link_match` testavam `link_retargeted` | não tocar o symlink quando `prior_record=link_match` |

**O #3 é o mais instrutivo: no mapa v1 aquelas linhas estavam VERDES.**
Verde falso — passavam pelo motivo errado. Confiar no v1 teria "provado"
preservação de LINK usando um link redirecionado.

**Achado novo #4 (doc §5.8):** a linha de continuidade dentro do guard de
ancestral-symlink é **código morto**. O sanitizador de relpath descarta
qualquer registro cujo caminho atravesse symlink no LOAD, antes de
`_baseline_has_*_record` ser consultado. Cura NÃO é fazê-la disparar
(isso violaria a fence de proveniência da decisão (v) do ADR-155) — é
**apagar a linha**: promessa que não se cumpre é pior que ausência.

**Próxima ação concreta:** ler o mapa v3, triar falso-vermelho MAIS UMA
VEZ (o histórico manda), gravar `scripts/tests/ownership-baseline-map.txt`,
commitar o W0.5 com adds EXPLÍCITOS, então W1.

**Gates já verificados adiantado:** docs-freshness bloqueante = 610
arquivos / 0 refs quebradas / EXIT=0. shellcheck do CI cobre só
`.claude/{scripts,hooks}` — o harness fica fora do gate (rodado limpo
localmente mesmo assim).

**Owner confirmou (2026-08-06, noite):** assina de manhã o que for
necessário. Logo o W4 entrega pack STAGED e INASSINÁVEL
(`Anchor-SHA: <PLACEHOLDER>`); o run NÃO tenta assinar nada.

**⚠️ Correção obrigatória ao §W2 deste plano (descoberta S297).** O §W2
manda `git clone --local .`, que clona o **HEAD** — e os 20 fixes do F3 da
S296 estão SÓ na árvore suja, nunca commitados. O clone nasceria de um
baseline DIFERENTE do que o mapa do W0.4 mediu, e "dirigir o mapa a 100%"
(W2.4) mediria contra outro ponto de partida. Sequência correta:

```
git clone --local . "$CLONE"
git diff HEAD > "$SCRATCH/live-tree.diff"    # tracked, staged E unstaged
git -C "$CLONE" apply "$SCRATCH/live-tree.diff"
```

Conferir depois: `git -C "$CLONE" status --porcelain` deve espelhar o
`git status --porcelain` da árvore viva nos arquivos do grupo A + F3.
Sem isso o W2 otimiza contra o alvo errado.

**Desvio de nomenclatura:** o §W1 deste plano pede
`debate/round-{1,2,3}/consensus.md`, mas o `DEBATE-SCHEMA.md` §3 marca
`debate/` como LEGADO e `architect/` como prática atual (foi o que o
PLAN-166 usou). Vale `architect/`.

**Desenho do W2 (levar ao debate como proposta concreta).**
`_ownership_verdict()` é uma **função PURA das 9 dimensões**:

```
_ownership_verdict <surface> <prior_record> <live_type> <live_content> \
                   <source_has> <mode> <ceremony> <operation> <skip_requested>
# stdout: "<VERDICT> <HASH_SOURCE>"   (o par do doc §3)
```

Consequência que muda a economia da suíte: o mesmo TSV vira **dois**
oráculos —
1. **unitário**, chamando a função direto (milissegundos, 61 linhas, roda
   a cada edição);
2. **e2e**, o `test-ownership-table.sh` atual (~10 min, prova que os
   callers OBSERVAM as dimensões corretamente e EXECUTAM o veredito).

Os dois são necessários e testam coisas diferentes: o unitário pega
decisão errada, o e2e pega observação errada. O loop de 40 min da S296
existia porque só havia o caro — e ele nem cobria as células.

Os callers (`install.sh`/`upgrade.sh`) ficam com: observar as 9 dimensões
→ chamar → executar. Os ramos de decisão antigos SAEM (AC-6).

--- CONSENSUS ---
---
plan: PLAN-167
round: 1
rounds_synthesized: [round-1]
agents_considered: [qa-architect, security-engineer, devops]
decisions_revised_in_plan:
  - "doc §5.5 — INV-3 added: an execution failure never advances the record"
  - "doc §5.4b — escape tripwire; OWN-0034 proven to write OUTSIDE the target"
  - "C2 amended — the ABORT split is adopted, the inherits-hash_source clause is struck"
  - "C3 ratified — legacy_pristine_partial becomes a live_content value; fault becomes a 15th column"
  - "§W2 gains W2.0 — scanner positive control before any TIMEOUT row may count as green"
  - "§W4 gains the CI wiring (canonical: smoke-install.yml lands via the ceremony, not the live tree)"
synthesized_at: 2026-08-06T23:50:00Z
synthesized_by: CEO
---

# Round 1 consensus — PLAN-167

Three critiques, three **ADJUST**, **zero VETO**. No agent rejected the
model; all three attacked its edges, which is the outcome the round was
designed to produce.

Recorded as **design-coherent**. That is not authorization to ship: the
verification cascade (V2 Codex pair-rail, V3 Owner GPG) is what authorizes,
and neither has run.

## Consensus findings (2+ agents flagged)

**C1 — `note`-as-dimension must close BEFORE any function is written.**
Flagged by qa-architect (must-fix 1, 2) and security-engineer (must-fix 2).
Agreed severity: **HIGH, blocking W2.**
A decision function cannot read prose, and the document itself already says
leaving `fault=` in free text is "the one option that should not survive".
Two rows (`OWN-0018`, `OWN-0020`) currently have identical nine-tuples and
opposite expected pairs, so no implementation can satisfy both.
**Resolution (CEO, both agents' preferred shape):**
- `live_content` gains **`legacy_pristine_partial`** — a tree carrying an
  entry the fingerprint cannot inventory. It is not "pristine with a note";
  it is a distinct observable, and it resolves to the **preserve** side
  (ADR-155-AMEND-1 §4: a partial inventory must never certify).
- `fault` becomes a **real 15th column**, not a directive in prose.
  qa-architect offered dropping those rows as the lower-friction path;
  **rejected** on security-engineer's ground: the fault rows are the
  backup-failure *safety* cells, and dropping them drops coverage of a
  data-loss path. A column is cheap; a hole is not.

**C2 — the decision/execution split is adopted, its `hash_source` clause is
struck.** Flagged by security-engineer (must-fix 1); qa-architect's must-fix
3 is the same concern from the verification side.
Agreed severity: **HIGH, blocking.**
The proposal said an `ABORT_SURFACE` "inherits the verdict's `hash_source`".
That would record a delivery **that did not happen** — the framework
claiming bytes it never wrote, which is the over-claiming direction
ADR-155-AMEND-1 §3 explicitly forbids. The split itself is sound and is
kept; the clause is replaced by **INV-3**, which now appears verbatim in
`docs/ownership-decision-table.md` §5.5 and must appear verbatim in ADR-190:

> **INV-3 — an execution failure never advances the record.** A caller
> handed `DELIVER` or `REFRESH` that cannot complete it leaves the manifest
> describing the world as it actually is; the record after a failed attempt
> equals the record before it.

**C3 — the new artifacts are not wired into CI.** Flagged by devops
(must-fix 1, 2, 3); qa-architect's must-fix 3 is the same class one layer
down (a test that cannot reach what it asserts).
Agreed severity: **HIGH.** Verified literally: `grep -c` returns 0 for all
three new paths in `.github/workflows/smoke-install.yml`, and that file uses
`fetch-depth: 1`, which produces a checkout with no tags — so the harness's
`git archive v1.2.0` cannot run there.
**This is the same class as finding r10-F4**, which was itself "a test the
only CI execution of which was skipped". The table caught its own ancestor.
**Resolution:** all CI changes land in the **W4 staged pack**, never in the
live tree — `.github/workflows/*.yml` is canonical-guarded (plan §3).

## Single-agent insights kept

1. **security-engineer must-fix 3 — the harness was blind to out-of-tree
   writes.** Verified and **already fixed during the round**: the fixture's
   foreign file is now a tripwire digested before and after each run, and
   any change yields status `ESCAPE`, which outranks the verdict comparison.
   Positive control: `OWN-0034` now reports `ESCAPE`. Negative control:
   `OWN-0044` (a correctly-preserved symlink) does not.
   **This promoted a finding**: the missing leaf-symlink guard on the
   pointer is no longer a hardening gap, it is a **demonstrated out-of-tree
   write** — the S238 class.
2. **security-engineer must-fix 4 — `hash_source` becomes required and
   fail-closed** for the three conditional surfaces: a conditional-surface
   record with no declared `hash_source` is not emitted, plus a named NOTE.
   Kept because §3.4 already showed `HASH_TARGET` is never correct across
   61 rows while being the permissive default. **Scope is load-bearing**:
   target-hashing of the broader rendered install tree is LEGITIMATE and
   stays — over-widening exactly there caused the r8-F1 P1 regression.
3. **qa-architect must-fix 3 — staged verification for the TIMEOUT rows.**
   A scanner fix that merely moves the blocking point downstream would turn
   three rows green without exercising the guards they claim to cover.
   Adopted as a new plan step **W2.0**: a standalone scanner probe must exit
   0 on a FIFO-bearing tree *before* any TIMEOUT row counts as green.
4. **devops must-fix 3 — name the per-PR gate.** Adopted: the unit oracle
   is `scripts/tests/test-ownership-verdict-unit.sh`, wired per-PR; the
   61-row e2e stays nightly. Without this the per-PR gate covers zero cells
   between nightly runs.

## Single-agent insights rejected / deferred

1. **qa-architect's option (b) for OQ-7** (drop the `fault` rows as
   out-of-scope) — **rejected**, see C1. Those are the safety cells.
2. **devops's alternative for the missing tag** (a harness fallback emitting
   `HARNESS-SKIP` so the suite exits 0) — **rejected**. A suite that goes
   green by skipping the rows it cannot run is the vacuous-gate class this
   repo has been bitten by before. The harness already fails loudly with the
   remedy in its message; CI fetches the tag.
3. **security-engineer must-fix 6** (completeness/uniqueness oracle, plus
   the missing `skip=self × edited` cells) — **deferred to W2**, not
   dropped. It is additive coverage and does not block the specification.

## Plan adjustments

- `§W0.2` — TSV schema goes to **15 columns** (`fault` added).
- `§W2` — new first step **W2.0** (scanner positive control).
- `§W2` — the unit oracle is named and wired per-PR.
- `§W4` — CI wiring added to the staged pack (canonical surface).
- `docs/ownership-decision-table.md` §5.4b, §5.5 (INV-3) — already applied.

## Round verdict

**PROCEED** — with C1 and C2 landing as table/spec changes *before* the
first line of `_ownership_verdict()` is written. No agent raised a VETO and
no two critiques conflict; the disagreements were between an agent and the
proposal, and every one resolved on evidence rather than on preference.

Recorded as `design-coherent`. Shipping remains gated on V2 + V3.

exec
/bin/zsh -lc "grep -n \"_ownership_verdict\" scripts/install.sh scripts/upgrade.sh scripts/_framework_manifest_set.sh; git status --short | sed -n '1,200p'; find .claude/plans/PLAN-167 -maxdepth 3 -type f -print | LC_ALL=C sort | tail -50; find .claude/adr -maxdepth 1 -name '*190*' -print" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 788ms:
 M .claude/governance/pair-rail-verdict-template.md
 M .claude/plans/PLAN-166/W1-approved-draft.md
 M .claude/plans/PLAN-166/staged-manifest.sha256
 M .claude/scripts/check-framework-updates.sh
 M .claude/scripts/check-model-deprecations.py
 M .claude/scripts/tests/test_release_workflow_asserts.py
 M .github/workflows/npm-publish.yml
 M .github/workflows/release.yml
 M .github/workflows/smoke-install.yml
 M CLAUDE.md
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
 M scripts/_framework_manifest_set.sh
 M scripts/doctor.sh
 M scripts/install.sh
 M scripts/tests/_parity_classify.py
 M scripts/tests/ownership_table.tsv
 M scripts/tests/test-ownership-table.sh
 M scripts/upgrade.sh
?? .claude/.framework-version
?? .claude/adr/ADR-155-AMEND-1-delivery-record-ownership.md
?? .claude/governance/npm-trusted-publisher.txt
?? .claude/plans/PLAN-166/architect/
?? scripts/tests/test-ownership-verdict-unit.sh
?? scripts/tests/test-upgrade-spec-ownership.sh
.claude/plans/PLAN-167/debate/round-1/consensus.md
.claude/plans/PLAN-167/debate/round-1/devops.md
.claude/plans/PLAN-167/debate/round-1/proposal.md
.claude/plans/PLAN-167/debate/round-1/qa-architect.md
.claude/plans/PLAN-167/debate/round-1/security-engineer.md

exec
/bin/zsh -lc "sed -n '320,620p' scripts/tests/test-upgrade-spec-ownership.sh; nl -ba scripts/_framework_manifest_set.sh | sed -n '528,560p'; nl -ba scripts/upgrade.sh | sed -n '2020,2118p'; nl -ba scripts/install.sh | sed -n '2290,2425p'; nl -ba .github/workflows/smoke-install.yml | sed -n '205,260p'" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
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
  2020	  local bak="$BAK_DIR/.claude/.framework-version"
  2021	
  2022	  # ---- OBSERVE -------------------------------------------------------------
  2023	  local _lt _pr _lc _sh _md _sk
  2024	  if _lg_ancestor_is_symlink "$TARGET" ".claude/.framework-version"; then
  2025	    _lt="ancestor_symlink"
  2026	  else
  2027	    _lt="$( _ov_obs_live_type "$dst" )"
  2028	  fi
  2029	  _pr="$( _ov_obs_prior_record ".claude/.framework-version" )"
  2030	  _sh=no; [ -f "$src" ] && _sh=yes
  2031	  if [ ! -e "$dst" ] || [ -L "$dst" ]; then
  2032	    _lc="-"
  2033	  elif [ "$_sh" = yes ] && cmp -s "$src" "$dst" 2>/dev/null; then
  2034	    _lc="pristine"
  2035	  else
  2036	    _lc="edited"
  2037	  fi
  2038	  _md="$( _ov_obs_mode )"
  2039	  _sk="$( _ov_obs_skip ".claude/.framework-version" )"
  2040	
  2041	  # ---- DECIDE --------------------------------------------------------------
  2042	  local _pair _verdict
  2043	  if ! _pair="$( _ownership_verdict marker "$_pr" "$_lt" "$_lc" "$_sh" "$_md" \
  2044	                   "$CEREMONY_EFFECTIVE" upgrade "$_sk" )"; then
  2045	    echo "    WARNING: .claude/.framework-version dimensions are not a legal cell" >&2
  2046	    echo "             — PRESERVED without ownership. Please report this combination." >&2
  2047	    return 0
  2048	  fi
  2049	  _verdict="${_pair%% *}"
  2050	  _MARKER_HASH_SOURCE="${_pair##* }"
  2051	
  2052	  # ---- EXECUTE -------------------------------------------------------------
  2053	  case "$_verdict" in
  2054	    PRESERVE_OWNED)
  2055	      _MARKER_DELIVERED=1
  2056	      case "$_lt/$_sk" in
  2057	        ancestor_symlink/*) echo "    SKIP: .claude/.framework-version has a symlinked ancestor (refusing to write through it — F11a)" ;;
  2058	        symlink/*)          echo "    SKIP: .claude/.framework-version is the recorded --mode link delivery (target unchanged)" ;;
  2059	        */self)             echo "    SKIPPED (--skip): .claude/.framework-version" ;;
  2060	        *)                  echo "    SKIP: .claude/.framework-version (ownership carried forward)" ;;
  2061	      esac
  2062	      return 0
  2063	      ;;
  2064	
  2065	    OMIT_RECORD|PRESERVE_UNOWNED)
  2066	      if [ "$_sh" = no ]; then
  2067	        # The documented --pin downgrade: this source predates the marker, so a
  2068	        # retained record would keep advertising a newer version over older
  2069	        # content. Readers fall back to VERSION, which the pin DID update.
  2070	        echo "    SKIP: .claude/.framework-version absent in source (pre-v1.3.0 checkout)"
  2071	        if [ "$_pr" != "none" ]; then
  2072	          echo "    NOTE: the prior delivery record is NOT carried forward — version" >&2
  2073	          echo "          readers fall back to VERSION (which reflects the pinned source)" >&2
  2074	        fi
  2075	      elif [ "$_lt" = "symlink" ]; then
  2076	        echo "    WARNING: .claude/.framework-version is a symlink that does NOT match the" >&2
  2077	        echo "             recorded LINK delivery — preserved WITHOUT framework ownership" >&2
  2078	        echo "             (readers fall back to VERSION)" >&2
  2079	      else
  2080	        echo "    SKIP: .claude/.framework-version is $_lt — adopter-owned, refusing to write into/through it"
  2081	      fi
  2082	      return 0
  2083	      ;;
  2084	
  2085	    DELIVER|REFRESH)
  2086	      if [ "$DRY_RUN" -eq 1 ]; then
  2087	        echo "    (dry-run) would REFRESH: .claude/.framework-version ($(tr -d '[:space:]' < "$src" 2>/dev/null || true))"
  2088	        return 0
  2089	      fi
  2090	      if [ "$_verdict" = "REFRESH" ] && [ "$_lc" = "edited" ]; then
  2091	        mkdir -p "$( dirname "$bak" )" 2>/dev/null || true
  2092	        if { cp "$dst" "$bak" 2>/dev/null || false; }; then
  2093	          echo "    BACKED UP: .claude/.framework-version -> $bak"
  2094	        else
  2095	          # INV-3: an execution failure never advances the record.
  2096	          echo "    WARNING: could not back up differing .claude/.framework-version —" >&2
  2097	          echo "             REFUSING to overwrite it (backup-before-replace)" >&2
  2098	          _up_record_op "preserve_marker_backup_failed" ".claude/.framework-version"
  2099	          [ "$_pr" = "hash" ] && _MARKER_DELIVERED=1
  2100	          return 0
  2101	        fi
  2102	      fi
  2103	      mkdir -p "$( dirname "$dst" )"
  2104	      cp "$src" "$dst"
  2105	      # Read-back validation: a write that cannot be confirmed is NOT recorded
  2106	      # as delivered, so every marker-first reader falls back to VERSION rather
  2107	      # than trusting a value the upgrade could not verify.
  2108	      if cmp -s "$src" "$dst" 2>/dev/null; then
  2109	        _MARKER_DELIVERED=1
  2110	        _up_record_op "refresh_framework_marker" "$(tr -d '[:space:]' < "$src" 2>/dev/null || true)"
  2111	        echo "    REFRESHED: .claude/.framework-version ($(tr -d '[:space:]' < "$dst" 2>/dev/null || true))"
  2112	      else
  2113	        echo "    WARNING: .claude/.framework-version write did not validate — NOT recorded as" >&2
  2114	        echo "             delivered (marker-first readers fall back to VERSION; r20)" >&2
  2115	      fi
  2116	      return 0
  2117	      ;;
  2118	  esac
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
   226	      - name: Assert npx/npm shim contract (if present)
   227	        # Phase 4 deliverable; skip if directory missing
   228	        run: |
   229	          set -euo pipefail
   230	          if [[ -d "npm" ]]; then
   231	            # Check no runtime deps
   232	            if [[ -f npm/package.json ]]; then
   233	              deps=$(jq '.dependencies // {} | length' npm/package.json)
   234	              if [[ "$deps" -ne 0 ]]; then
   235	                echo "::error::ceo-orchestration must ship with 0 runtime deps (got $deps)"
   236	                exit 1
   237	              fi
   238	              echo "OK: npm shim has zero runtime dependencies"
   239	            fi
   240	          else
   241	            echo "npm/ shim not yet present — skipping"
   242	          fi

exec
/bin/zsh -lc 'ls -l scripts/tests/ownership-baseline-map.txt docs/ownership-decision-table.md 2>/dev/null; tail -20 scripts/tests/ownership-baseline-map.txt 2>/dev/null; git log -5 --oneline --decorate; git status --branch --short | head' in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 479ms:
## plan167-refactor
 M .claude/governance/pair-rail-verdict-template.md
 M .claude/plans/PLAN-166/W1-approved-draft.md
 M .claude/plans/PLAN-166/staged-manifest.sha256
 M .claude/scripts/check-framework-updates.sh
 M .claude/scripts/check-model-deprecations.py
 M .claude/scripts/tests/test_release_workflow_asserts.py
 M .github/workflows/npm-publish.yml
 M .github/workflows/release.yml
 M .github/workflows/smoke-install.yml

exec
/bin/zsh -lc "grep ' RED ' scripts/tests/ownership-baseline-map.txt; grep -R \"open=\" -n scripts/tests/ownership_table.tsv docs/ownership-decision-table.md | head -100" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
OWN-0016   RED     exp=PRESERVE_OWNED  /HASH_PRIOR_RECORD      got=OMIT_RECORD     /HASH_NONE              rc=0   r11-F2
OWN-0024   RED     exp=ABORT_SURFACE   /HASH_PRIOR_RECORD      got=PRESERVE_OWNED  /HASH_PRIOR_RECORD      rc=1   r3-F1
OWN-0027   RED     exp=ABORT_SURFACE   /HASH_PRIOR_RECORD      got=PRESERVE_OWNED  /HASH_PRIOR_RECORD      rc=1   r4-F5
OWN-0032   RED     exp=PRESERVE_UNOWNED/HASH_NONE              got=PRESERVE_OWNED  /HASH_PRIOR_RECORD      rc=1   derived
OWN-0034   RED     exp=PRESERVE_UNOWNED/HASH_NONE              got=PRESERVE_OWNED  /HASH_UNCLASSIFIED      rc=0   derived
OWN-0052   RED     exp=PRESERVE_UNOWNED/HASH_NONE              got=PRESERVE_OWNED  /LINK_RECORD            rc=0   r11-F1
OWN-0053   RED     exp=PRESERVE_UNOWNED/HASH_NONE              got=PRESERVE_OWNED  /LINK_RECORD            rc=0   r11-F1
OWN-0082   RED     exp=PRESERVE_OWNED  /HASH_PRIOR_RECORD      got=OMIT_RECORD     /HASH_NONE              rc=0   adr-155-amend-1
scripts/tests/ownership_table.tsv:6:# `indistinguishable=` / `open=` remain annotations, never dimensions.
scripts/tests/ownership_table.tsv:22:OWN-0016	spec	hash	dir_empty	edited	yes	copy	maintainer	install_rerun	none	none	PRESERVE_OWNED	HASH_PRIOR_RECORD	r11-F2	open=r11-F2; flag-only continuity emits zero file records
scripts/tests/ownership_table.tsv:53:OWN-0052	spec	hash	symlink	-	yes	link	maintainer	install_rerun	none	none	PRESERVE_UNOWNED	HASH_NONE	r11-F1	open=r11-F1; absence of a LINK row is NOT a match
scripts/tests/ownership_table.tsv:54:OWN-0053	marker	hash	symlink	-	yes	link	maintainer	install_rerun	none	none	PRESERVE_UNOWNED	HASH_NONE	r11-F1	open=r11-F1; sibling site
scripts/tests/ownership_table.tsv:65:OWN-0081	marker	hash	regular	pristine	no	copy	maintainer	upgrade	none	none	PRESERVE_UNOWNED	HASH_NONE	r11-F3	open=r11-F3; external target: VERSION is adopter-owned and never written
docs/ownership-decision-table.md:173:`open=` survive as annotations because neither changes what the fixture does
docs/ownership-decision-table.md:278:  green), `invariant=<id>`, `open=<round-id>` (a defect this row asserts and

exec
/bin/zsh -lc "head -60 .claude/scripts/check-model-deprecations.py; head -45 .claude/scripts/tests/test_release_workflow_asserts.py; grep -R \"| None\\|str |\\|list\\[\" -n .claude/scripts/check-model-deprecations.py .claude/scripts/tests/test_release_workflow_asserts.py | head -50; git diff --check" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 1314ms:
exec
/bin/zsh -lc 'git config --get-all remote.origin.fetch; git remote -v; git rev-parse origin/main HEAD' in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-kxKMJzFB' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-9xFGRJVR' (errno=Operation not permitted)
+refs/heads/*:refs/remotes/origin/*
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-Uh3ozJne' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-OJe915zc' (errno=Operation not permitted)
origin	/Users/joaocanhada/canhada-labs/ceo-orchestration/. (fetch)
origin	/Users/joaocanhada/canhada-labs/ceo-orchestration/. (push)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-YMybaQ4t' (errno=Operation not permitted)
git: warning: confstr() failed with code 5: couldn't get path of DARWIN_USER_TEMP_DIR; using /tmp instead
git: error: couldn't create cache file '/tmp/xcrun_db-II0zQYNE' (errno=Operation not permitted)
bc53747a3e7bd43302c09d98e99ac7640bd8d999
bc53747a3e7bd43302c09d98e99ac7640bd8d999

exec
/bin/zsh -lc "sed -n '330,555p' .claude/scripts/local/_release_tag_guard.py" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
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

exec
/bin/zsh -lc "nl -ba scripts/upgrade.sh | sed -n '1968,2008p'; nl -ba scripts/upgrade.sh | sed -n '2088,2105p'; nl -ba scripts/upgrade.sh | sed -n '3008,3055p'; nl -ba scripts/upgrade.sh | sed -n '3126,3144p'; nl -ba scripts/_framework_manifest_set.sh | sed -n '365,398p'; nl -ba .claude/scripts/check-framework-updates.sh | sed -n '130,175p'; nl -ba .github/workflows/smoke-install.yml | sed -n '1,75p'" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
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
  1980	          _up_record_op "preserve_spec_v1_backup_failed" "SPEC/v1"
  1981	          [ "$_pr" = "hash" ] && _SPEC_DELIVERED=1
  1982	          return 0
  1983	        fi
  1984	        echo "    BACKED UP: SPEC/v1 -> $BAK_DIR/SPEC/v1"
  1985	        find "$ddir" -mindepth 1 -delete
  1986	        rmdir "$ddir" 2>/dev/null || true
  1987	      elif [ "$_lt" = "regular" ]; then
  1988	        mkdir -p "$( dirname "$bdir" )"
  1989	        if cp "$ddir" "$bdir" 2>/dev/null; then
  1990	          rm -f "$ddir"
  1991	          echo "    BACKED UP: SPEC/v1 (non-directory) -> $BAK_DIR/SPEC/v1"
  1992	        else
  1993	          echo "    WARNING: could not back up non-directory SPEC/v1 — REFUSING to remove it" >&2
  1994	          _up_record_op "preserve_spec_v1_backup_failed" "SPEC/v1"
  1995	          [ "$_pr" = "hash" ] && _SPEC_DELIVERED=1
  1996	          return 0
  1997	        fi
  1998	      fi
  1999	
  2000	      mkdir -p "$( dirname "$ddir" )"
  2001	      cp -R "$sdir" "$ddir"
  2002	      _SPEC_DELIVERED=1
  2003	      echo "    REFRESHED (forced — $_pr/$_lc): SPEC/v1"
  2004	      return 0
  2005	      ;;
  2006	  esac
  2007	}
  2008	
  2088	        return 0
  2089	      fi
  2090	      if [ "$_verdict" = "REFRESH" ] && [ "$_lc" = "edited" ]; then
  2091	        mkdir -p "$( dirname "$bak" )" 2>/dev/null || true
  2092	        if { cp "$dst" "$bak" 2>/dev/null || false; }; then
  2093	          echo "    BACKED UP: .claude/.framework-version -> $bak"
  2094	        else
  2095	          # INV-3: an execution failure never advances the record.
  2096	          echo "    WARNING: could not back up differing .claude/.framework-version —" >&2
  2097	          echo "             REFUSING to overwrite it (backup-before-replace)" >&2
  2098	          _up_record_op "preserve_marker_backup_failed" ".claude/.framework-version"
  2099	          [ "$_pr" = "hash" ] && _MARKER_DELIVERED=1
  2100	          return 0
  2101	        fi
  2102	      fi
  2103	      mkdir -p "$( dirname "$dst" )"
  2104	      cp "$src" "$dst"
  2105	      # Read-back validation: a write that cannot be confirmed is NOT recorded
  3008	# unconditionally and `cat >`-created a root PROTOCOL.md that a
  3009	# `--ceremony user` install deliberately never has (install.sh
  3010	# WS4-guard-proto forbids root files); the F4 tree-comparison e2e exposes
  3011	# exactly this divergence (r7/r13). The gate reads the ceremony from
  3012	# .claude/.install-state.json via the replay-independent reader above.
  3013	_PROTOCOL_DELIVERED=0
  3014	echo ""
  3015	echo "==> Refreshing PROTOCOL.md pointer"
  3016	if [[ "$CEREMONY_EFFECTIVE" == "user" ]]; then
  3017	  echo "    SKIP: PROTOCOL.md pointer (recorded --ceremony user install — a user install never creates root files, WS4; r13)"
  3018	  # Ownership continuity on the analogous skip (codex W1 round 7, P2) — see
  3019	  # the SPEC/v1 ceremony skip: preserving the tree while erasing its record
  3020	  # strands a framework-delivered pointer as unowned.
  3021	  #
  3022	  # But the flag alone is NOT enough (codex W1 round 9, P1): this skip never
  3023	  # runs _refresh_protocol_pointer, so _REFRESH_PROTOCOL_CANON_HASH stays
  3024	  # empty, and _write_baseline_manifest then hashes the LIVE pointer —
  3025	  # re-recording an adopter-CUSTOMIZED PROTOCOL.md as the framework baseline,
  3026	  # which the next upgrade overwrites and uninstall can DELETE. Retaining
  3027	  # ownership must never retain the wrong bytes. Carry the PRIOR canonical
  3028	  # digest; a LINK record needs none (the link branch of the rewrite fires
  3029	  # before the PROTOCOL special case). When neither is available, DROP the
  3030	  # claim — the pointer stays adopter-owned and preserved, which is the
  3031	  # pre-continuity behaviour and loses nothing.
  3032	  if _baseline_has_protocol_record; then
  3033	    _REFRESH_PROTOCOL_CANON_HASH="$( _baseline_lookup "PROTOCOL.md" 2>/dev/null || true )"
  3034	    if [[ -n "$_REFRESH_PROTOCOL_CANON_HASH" ]] \
  3035	       || grep -Eq '^LINK  PROTOCOL\.md(  |$)' "$_BASELINE_MANIFEST_FILE" 2>/dev/null; then
  3036	      _PROTOCOL_DELIVERED=1
  3037	    else
  3038	      echo "    NOTE: PROTOCOL.md delivery record present but its canonical digest is" >&2
  3039	      echo "          unrecoverable (ambiguous record) — ownership NOT claimed; the" >&2
  3040	      echo "          pointer stays adopter-owned and preserved" >&2
  3041	    fi
  3042	  fi
  3043	else
  3044	  _refresh_protocol_pointer
  3045	  # Registered delivery for the baseline rewrite below: on this path the
  3046	  # refresh either WROTE the pointer or PRESERVED a customized one that the
  3047	  # baseline already records (the preserve branch requires a baseline hit),
  3048	  # so framework ownership holds in every non-user branch.
  3049	  _PROTOCOL_DELIVERED=1
  3050	fi
  3051	
  3052	# PLAN-166 F3 (ADR-155-AMEND-1): SPEC/v1 forced refresh + framework version
  3053	# marker. Both run BEFORE the baseline-manifest rewrite so the delivery
  3054	# flags they set are what the rewritten baseline records.
  3055	echo ""
  3126	  # PLAN-166 F3 (ADR-155-AMEND-1): conditional ownership from what THIS
  3127	  # upgrade delivered/refreshed (or what the pre-upgrade baseline already
  3128	  # recorded — ownership continuity), never the ceremony alone, never file
  3129	  # presence (r17/r19/r20).
  3130	  # The decision travels with the delivery flag.
  3131	  export FMS_SOURCE_ROOT="$SOURCE_DIR"
  3132	  export FMS_PRIOR_MANIFEST="${_BASELINE_MANIFEST_FILE:-}"
  3133	  export FMS_HASH_SOURCE_SPEC="${_SPEC_HASH_SOURCE:-}"
  3134	  export FMS_HASH_SOURCE_MARKER="${_MARKER_HASH_SOURCE:-}"
  3135	  export FMS_HASH_SOURCE_PROTOCOL="${_PROTOCOL_HASH_SOURCE:-}"
  3136	  export FMS_DELIVERED_SPEC="${_SPEC_DELIVERED:-0}"
  3137	  export FMS_DELIVERED_PROTOCOL="${_PROTOCOL_DELIVERED:-0}"
  3138	  export FMS_DELIVERED_MARKER="${_MARKER_DELIVERED:-0}"
  3139	  _write_baseline_manifest "$TARGET/.claude/.install-manifest.sha256"
  3140	  unset FMS_ROOT FMS_HASH_ROOT FMS_PROFILE_PARTS FMS_MODE FMS_PROTOCOL_HASH FMS_LINK_PATHS
  3141	  unset FMS_DELIVERED_SPEC FMS_DELIVERED_PROTOCOL FMS_DELIVERED_MARKER
  3142	fi
  3143	
  3144	# ===========================================================================
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
    73	jobs:
    74	  smoke:
    75	    # PLAN-012 Phase 2 CEO_SOTA_DISABLE parity.

exec
/bin/zsh -lc "grep -n -e \"--pin\" -e 'PIN=' scripts/upgrade.sh | head -80; sed -n '430,635p' scripts/upgrade.sh" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
6:#                                    [--pin <tag>] [--dry-run]
249:    --pin)
362:  --pin <tag>           Pin source to specific tag/SHA (SPEC v1 install-cli.md).
364:                        Example: --pin v1.18.0
437:  2 — target has uncommitted .claude/ changes when --pin was passed
462:  echo "Usage: $0 <target-repo-path> [--profile <list>] [--stack <name>] [--pin <tag>] [--dry-run]" >&2
553:# --pin contract (SPEC v1 install-cli.md, ADR-007):
562:# PLAN-161 U1 (codex r2 F4) — ONE composed EXIT cleanup. The --pin block used
566:# guarded by PINNED_CHECKOUT_DONE + ORIGINAL_BRANCH — the non-dry --pin
587:    echo "ERROR: unknown --pin ref: $PIN_REF" >&2
604:    echo "==> Dry-run: diff between current source and --pin $PIN_REF"
2067:        # The documented --pin downgrade: this source predates the marker, so a
  Files about to be overwritten are first copied to .claude.bak/{timestamp}/
  inside $TARGET. If a customization exists at the destination, a `diff -q`
  WARNING is emitted on stderr (suppressible via --no-diff-warn).

Exit codes:
  0 — upgrade completed (or --help / --dry-run preview)
  1 — bad usage / unknown option / missing target
  2 — target has uncommitted .claude/ changes when --pin was passed

Notes:
  Run after `git pull` in the source ceo-orchestration repo. The upgrade
  refreshes the PROTOCOL.md pointer to keep the adopter aligned with the
  current source layout (DevOps-P1-4).

See also:
  scripts/install.sh --help     for fresh-install flags + profile semantics
  INSTALL.md §Upgrade flow      for the full upgrade walk-through
HELP
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

if [[ -z "$TARGET" || ! -d "$TARGET" ]]; then
  echo "Usage: $0 <target-repo-path> [--profile <list>] [--stack <name>] [--pin <tag>] [--dry-run]" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# PLAN-106 Wave G.2 — git-checkout retry wrapper around index.lock contention.
# ---------------------------------------------------------------------------
# Wraps `git checkout --quiet "$PIN_REF"` with a 3-attempt retry on
# `.git/index.lock` busy. Per-attempt audit event via emit_git_index_lock_retry.
# Argv-pass invocation per PLAN-106 §3 Wave G.2.b — never source-string
# interpolation; absolute HOOKS_DIR; PYTHONNOUSERSITE=1 python3 -I.
#
# Override budget via CEO_GIT_LOCK_RETRY_MAX (default 3) for tests.
# Override unit-test override via CEO_GIT_LOCK_RETRY_BACKOFF_BASE (default 1)
# so the test can use 0s waits.
_git_checkout_with_lock_retry() {
  local src_dir="$1"
  local pin_ref="$2"
  local max_attempts="${CEO_GIT_LOCK_RETRY_MAX:-3}"
  local backoff_base="${CEO_GIT_LOCK_RETRY_BACKOFF_BASE:-1}"
  local attempt=1
  local rc=0
  local err_out=""
  local repo_root_for_hash
  local hash
  local hooks_dir

  # Derive HASH explicitly as hex-only by construction (collision-resistant):
  # use git rev-parse on the source dir; fall back to $src_dir literal if
  # rev-parse fails (e.g. during sandbox-sim of a fresh init).
  repo_root_for_hash="$( cd "$src_dir" 2>/dev/null && git rev-parse --show-toplevel 2>/dev/null || printf '%s' "$src_dir" )"
  # PLAN-138 Wave C (ADR-155): hash a STRING via the portable _hash_stdin
  # (shasum||sha256sum). This hashes a PATH STRING (not a file), so the
  # stdin/string hasher is correct — NOT a content hash. Fall back to the
  # legacy bare shasum if the helper was not sourced (partial checkout).
  if command -v _hash_stdin >/dev/null 2>&1; then
    hash="$( printf '%s' "$repo_root_for_hash" | _hash_stdin )"
  else
    hash="$( printf '%s' "$repo_root_for_hash" | shasum -a 256 | awk '{print $1}' )"
  fi
  # Resolve hooks directory to ABSOLUTE path (Codex P0 fold — relative
  # sys.path.insert is vulnerable to CWD manipulation):
  hooks_dir="$SOURCE_DIR/.claude/hooks"

  while [[ "$attempt" -le "$max_attempts" ]]; do
    err_out="$( ( cd "$src_dir" && git checkout --quiet "$pin_ref" ) 2>&1 )" && rc=0 || rc=$?
    if [[ "$rc" -eq 0 ]]; then
      return 0
    fi

    # Detect index.lock contention. Two canonical git error strings:
    #   "Another git process seems to be running in this repository"
    #   "fatal: Unable to create '.git/index.lock': File exists"
    if echo "$err_out" | grep -qE 'index\.lock|Another git process seems to be running'; then
      local backoff_seconds=$(( backoff_base * (2 ** (attempt - 1)) ))

      # PLAN-106 Wave G.2 hardened invocation. argv-pass eliminates
      # source-string interpolation (lesson [[feedback-bash-heredoc-paren-in-subshell]]).
      # python3 -I + PYTHONNOUSERSITE=1 shrink env-driven import surface.
      # Best-effort emit — failure must NOT abort the retry chain.
      PYTHONNOUSERSITE=1 python3 -I -c '
import sys
hooks_dir = sys.argv[1]
if hooks_dir not in sys.path:
    sys.path.insert(0, hooks_dir)
from _lib.audit_emit import emit_git_index_lock_retry
emit_git_index_lock_retry(
    attempt=int(sys.argv[2]),
    backoff_seconds=int(sys.argv[3]),
    repo_path_hash=sys.argv[4],
    operation="upgrade_sh_git_checkout",
)' "$hooks_dir" "$attempt" "$backoff_seconds" "$hash" 2>/dev/null || true

      echo "    NOTE: git index.lock busy (attempt $attempt/$max_attempts) — backing off ${backoff_seconds}s" >&2
      if [[ "$attempt" -lt "$max_attempts" ]]; then
        sleep "$backoff_seconds"
      fi
      attempt=$(( attempt + 1 ))
      continue
    fi

    # Non-lock error — surface and bail.
    echo "$err_out" >&2
    return "$rc"
  done

  # Exhausted retries on lock contention.
  echo "ERROR: git checkout $pin_ref retry budget exhausted after $max_attempts attempts (.git/index.lock contention)" >&2
  return 2
}

# --pin contract (SPEC v1 install-cli.md, ADR-007):
# - Resolve <ref> via git rev-parse --verify in the source framework repo
# - Refuse if target has uncommitted .claude/ changes (exit 2)
# - On --dry-run: print diff between current and pinned and exit 0
# - Otherwise: git checkout <ref> in source; run normal upgrade;
#   restore original branch at end
PINNED_CHECKOUT_DONE=0
ORIGINAL_BRANCH=""

# PLAN-161 U1 (codex r2 F4) — ONE composed EXIT cleanup. The --pin block used
# to install an inline EXIT trap restoring the source branch; any later plain
# `trap ... EXIT` would CLOBBER it. All exit-time duties now live in this
# single function, installed ONCE: (a) restore the pinned-source branch,
# guarded by PINNED_CHECKOUT_DONE + ORIGINAL_BRANCH — the non-dry --pin
# restore semantics are preserved exactly, on success AND on mid-run failure;
# (b) reap the sanitized baseline-manifest tempfile, which now lives OUTSIDE
# $TARGET (see _load_baseline_manifest).
_BASELINE_TMP_FILE=""
_upgrade_cleanup() {
  if [[ "${PINNED_CHECKOUT_DONE:-0}" -eq 1 ]] && [[ -n "${ORIGINAL_BRANCH:-}" ]]; then
    ( cd "$SOURCE_DIR" && git checkout --quiet "$ORIGINAL_BRANCH" 2>/dev/null ) || true
  fi
  if [[ -n "${_BASELINE_TMP_FILE:-}" ]]; then
    rm -f "$_BASELINE_TMP_FILE" 2>/dev/null || true
  fi
}
trap _upgrade_cleanup EXIT

if [[ -n "$PIN_REF" ]]; then
  if ! pushd "$SOURCE_DIR" >/dev/null; then
    echo "ERROR: cannot cd to source repo: $SOURCE_DIR" >&2
    exit 1
  fi
  if ! git rev-parse --verify "$PIN_REF" >/dev/null 2>&1; then
    echo "ERROR: unknown --pin ref: $PIN_REF" >&2
    popd >/dev/null || true
    exit 2
  fi
  ORIGINAL_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "")"
  popd >/dev/null || true

  # Refuse on uncommitted target .claude/ changes unless CEO_ORCH_FORCE=1
  if [[ -d "$TARGET/.claude" ]] && [[ -d "$TARGET/.git" ]] && [[ "${CEO_ORCH_FORCE:-0}" != "1" ]]; then
    if ( cd "$TARGET" && ! git diff --quiet -- .claude/ 2>/dev/null ); then
      echo "ERROR: target has uncommitted .claude/ changes." >&2
      echo "       Commit, stash, or set CEO_ORCH_FORCE=1 to override." >&2
      exit 2
    fi
  fi

  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "==> Dry-run: diff between current source and --pin $PIN_REF"
    ( cd "$SOURCE_DIR" && git diff "$PIN_REF"...HEAD -- .claude/ scripts/ templates/ SPEC/ || true )
    exit 0
  fi

  # PLAN-106 Wave G.2: wrapped retry around `git checkout`. Replaces the
  # bare `git checkout --quiet "$PIN_REF"` call at the previous
  # upgrade.sh:180. Retry budget is 3 attempts with exponential backoff
  # (1s, 2s, 4s). Per-attempt audit event via emit_git_index_lock_retry.
  if ! _git_checkout_with_lock_retry "$SOURCE_DIR" "$PIN_REF"; then
    echo "ERROR: git checkout $PIN_REF failed in source." >&2
    exit 2
  fi
  PINNED_CHECKOUT_DONE=1
  # Source-branch restore on any exit is handled by the composed
  # _upgrade_cleanup EXIT trap installed above (PLAN-161 U1, codex r2 F4).
fi

TARGET="$( cd "$TARGET" && pwd )"

# ===========================================================================
# PLAN-153 Wave B item B2 — replay the RECORDED install request.
# ===========================================================================
# install.sh (>= Wave B) records the original request in
# $TARGET/.claude/.install-state.json (schema ceo.install-state/v1). When
# present + valid, request.profile / request.stack become the DEFAULTS for
# this upgrade so an adopter who installed `--profile core,fintech` does not
# silently get the core,frontend default by forgetting the flag. Explicit
# flags always win; --no-replay opts out.
#
# BACK-COMPAT (debate C must-fix): missing state (ALL pre-Wave-B installs)
# or unreadable/invalid state NEVER errors and NEVER no-ops — the upgrade

exec
/bin/zsh -lc "grep -n \"_relpath_unsafe\\|SANITIZED\" scripts/doctor.sh | head -60; sed -n '440,575p' scripts/doctor.sh" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
225:SANITIZED="$WORKDIR/manifest.sanitized"
226:: > "$SANITIZED"
233:_relpath_unsafe() {
306:      if _relpath_unsafe "$rel" link; then continue; fi
309:      printf 'LINK  %s  %s\n' "$rel" "$target" >> "$SANITIZED"
319:      if _relpath_unsafe "$rel" file; then continue; fi
322:      printf '%s  %s\n' "$digest" "$rel" >> "$SANITIZED"
331:  : > "$SANITIZED.f"
342:    printf '%s\n' "$line" >> "$SANITIZED.f"
343:  done < "$SANITIZED"
344:  mv "$SANITIZED.f" "$SANITIZED"
347:if [ ! -s "$SANITIZED" ]; then
427:_log "==> Verifying $( wc -l < "$SANITIZED" | tr -d ' ' ) manifest records"
594:done < "$SANITIZED"
626:      grep -Eq "^([0-9a-f]{64}|LINK)  $1" "$SANITIZED" 2>/dev/null
662:    }' "$SANITIZED" | LC_ALL=C sort -u > "$WORKDIR/manifest-rels"
          [ "$VERBOSE" -eq 1 ] && _log "    OK (link): $rel"
          continue
        fi
      fi
      if [ ! -e "$lpath" ] && [ ! -L "$lpath" ]; then
        MISSING_COUNT=$((MISSING_COUNT + 1))
        _log "    MISSING (link): $rel -> $target"
        if [ "$REPAIR" -eq 1 ]; then
          if [ "$DRY_RUN" -eq 1 ]; then
            _log "    (dry-run) would RE-LINK: $rel -> $target"
            WOULD_REPAIR=$((WOULD_REPAIR + 1))
            UNRESOLVED=$((UNRESOLVED + 1))
          else
            mkdir -p "$TARGET/$( dirname "$rel" )"
            if ln -s "$target" "$lpath" 2>/dev/null; then
              _log "    RE-LINKED: $rel -> $target"
              REPAIRED_COUNT=$((REPAIRED_COUNT + 1))
              [ -e "$lpath" ] || _log "    NOTE: link target does not exist (broken link recreated as recorded): $target"
            else
              _log "    RESTORE-FAILED (ln -s failed): $rel"
              UNRESOLVED=$((UNRESOLVED + 1))
            fi
          fi
        else
          UNRESOLVED=$((UNRESOLVED + 1))
        fi
        continue
      fi
      # Present but wrong: retargeted symlink, or a regular file replaced it.
      DRIFT_COUNT=$((DRIFT_COUNT + 1))
      _log "    DRIFT (link: expected -> $target): $rel"
      if [ "$REPAIR" -eq 1 ]; then
        if _confirmed "$rel"; then
          if [ "$DRY_RUN" -eq 1 ]; then
            _log "    (dry-run) would RE-LINK (replacing current): $rel -> $target"
            WOULD_REPAIR=$((WOULD_REPAIR + 1))
            UNRESOLVED=$((UNRESOLVED + 1))
          else
            if [ -f "$lpath" ] && [ ! -L "$lpath" ]; then
              _backup_file "$rel"
              _log "    BACKED-UP: $rel -> $BAK_DIR/$rel"
            fi
            rm -f "$lpath"
            if ln -s "$target" "$lpath" 2>/dev/null; then
              _log "    RE-LINKED: $rel -> $target"
              REPAIRED_COUNT=$((REPAIRED_COUNT + 1))
            else
              _log "    RESTORE-FAILED (ln -s failed): $rel"
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
      ;;
    *)
      base="${line%%  *}"
      rel="${line#*  }"
      fpath="$TARGET/$rel"

      if [ ! -e "$fpath" ] && [ ! -L "$fpath" ]; then
        MISSING_COUNT=$((MISSING_COUNT + 1))
        src_hash="$( _hash_file "$SOURCE_DIR/$rel" 2>/dev/null || true )"
        if [ -z "$src_hash" ]; then
          _log "    MISSING (framework checkout no longer ships this file): $rel"
          BLOCKED_COUNT=$((BLOCKED_COUNT + 1))
          UNRESOLVED=$((UNRESOLVED + 1))
        elif [ "$src_hash" != "$base" ]; then
          _log "    MISSING (framework source diverged from baseline — run upgrade.sh): $rel"
          BLOCKED_COUNT=$((BLOCKED_COUNT + 1))
          UNRESOLVED=$((UNRESOLVED + 1))
        else
          _log "    MISSING (restorable): $rel"
          if [ "$REPAIR" -eq 1 ]; then
            if [ "$DRY_RUN" -eq 1 ]; then
              _log "    (dry-run) would RESTORE: $rel"
              WOULD_REPAIR=$((WOULD_REPAIR + 1))
              UNRESOLVED=$((UNRESOLVED + 1))
            elif _restore_file "$rel" "$base"; then
              REPAIRED_COUNT=$((REPAIRED_COUNT + 1))
            else
              UNRESOLVED=$((UNRESOLVED + 1))
            fi
          else
            UNRESOLVED=$((UNRESOLVED + 1))
          fi
        fi
        continue
      fi

      if [ -L "$fpath" ] || [ ! -f "$fpath" ]; then
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

exec
/bin/zsh -lc "grep -n \"PLANTED\\|per-mode verdicts\\|positive control:\" scripts/tests/test-install-upgrade-parity-e2e.sh | sed -n '1,120p'; sed -n '1,220p' scripts/tests/test-install-upgrade-parity-e2e.sh | grep -n -C3 \"positive control\" | head -100" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
209:PLANTED_SRC=""
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
337:  echo "positive control: FIRED in every mode (rc=1 each) — the gate is alive."
60-#   * DECLARED generated/adopter-owned paths that turn out IDENTICAL emit a
61-#     WARNING (declaration is stale; harmless).
62-#   * Any divergence matching NO declaration is FATAL. That is the live gate;
63:#     the positive control trips exactly there.
64-#
65-# EXIT CODES
66-#   0  parity   — no fatal divergence and no KNOWN-OPEN entry outstanding
67:#   1  FAIL     — undeclared divergence (what the positive control must
68-#                 produce, and what a real install/upgrade regression produces)
69-#   2  KNOWN-OPEN — only the explicitly named PLAN-166 W1 prerequisites are
70-#                 outstanding. STILL A FAILURE, never a silent skip: the
--
176-echo "  historical pin        : $PIN"
177-echo "  profile               : $PROFILE"
178-echo "  ceremony modes        : $MODES"
179:echo "  positive control      : $POSITIVE_CONTROL"
180-echo "  workdir               : $WORK"
181-echo "  git describe (repo)   : $( git -C "$REPO_ROOT" describe --tags --always --dirty 2>/dev/null || echo '(n/a)' )"
182-echo "--------------------------------------------------------------"
--
200-fi
201-[ -f "$PIN_SRC/scripts/install.sh" ] || scaffold "$PIN archive has no scripts/install.sh"
202-
203:# --- optional planted-divergence source for the positive control ------------
204-# A depth-1 symlink farm over the working tree with ONE edited file. upgrade.sh
205-# derives SOURCE_DIR from its own location ("cd $SCRIPT_DIR/.." with a logical
206-# pwd), so the farm root becomes the source and every other path resolves
207-# through the symlinks to the live tree. Cheap (no 75MB copy) and it perturbs
208:# exactly one line, which is what a positive control is for.
209-PLANTED_SRC=""
210-if [ "$POSITIVE_CONTROL" -eq 1 ]; then
211-  PLANTED_SRC="$WORK/src-planted"

exec
/bin/zsh -lc "sed -n '200,250p' scripts/tests/test-install-upgrade-parity-e2e.sh; sed -n '300,350p' scripts/tests/test-install-upgrade-parity-e2e.sh" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
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
    _b="$( basename "$_f" )"
    [ "$_b" = "upgrade.sh" ] && continue
    ln -s "$_f" "$PLANTED_SRC/scripts/$_b" 2>/dev/null || true
  done
  _before="$( grep -c "^backup_and_replace \"$PLANT_TARGET\"\$" "$REPO_ROOT/scripts/upgrade.sh" || true )"
  grep -v "^backup_and_replace \"$PLANT_TARGET\"\$" \
    "$REPO_ROOT/scripts/upgrade.sh" > "$PLANTED_SRC/scripts/upgrade.sh" \
    || scaffold "could not write planted upgrade.sh"
  _after="$( grep -c "^backup_and_replace \"$PLANT_TARGET\"\$" "$PLANTED_SRC/scripts/upgrade.sh" || true )"
  if [ "${_before:-0}" -lt 1 ] || [ "${_after:-1}" -ne 0 ]; then
    scaffold "planting failed: backup_and_replace \"$PLANT_TARGET\" occurrences before=$_before after=$_after — the control perturbed nothing"
  fi
  echo "  PLANTED: dropped backup_and_replace \"$PLANT_TARGET\" from a COPY of"
  echo "           upgrade.sh (occurrences $_before -> $_after). The live"
  echo "           scripts/upgrade.sh is untouched."
  echo "--------------------------------------------------------------"
fi

_git_init() {
  _n=0
  while [ "$_n" -lt 5 ]; do
    ( cd "$1" && git init -q 2>/dev/null ) && return 0
    _n=$(( _n + 1 )); sleep 1
  done
  ( cd "$1" && git init -q )
}

OVERALL=0          # 0 parity | 1 fail | 2 known-open
MODE_VERDICTS=""   # "mode:rc" pairs, bash-3.2 has no associative arrays
for MODE in $MODES; do
    --mode "$MODE" $EXTRA_ARGS
  rc=$?
  case "$rc" in
    0) : ;;
    2) [ "$OVERALL" -eq 0 ] && OVERALL=2 ;;
    1) OVERALL=1 ;;
    *) scaffold "classifier returned unexpected rc=$rc (mode=$MODE)" ;;
  esac
  MODE_VERDICTS="$MODE_VERDICTS $MODE:$rc"
done

echo ""
echo "--------------------------------------------------------------"
echo "per-mode verdicts (0 parity / 1 fail / 2 known-open):$MODE_VERDICTS"

# --- positive-control self-check ------------------------------------------
# A control that stops firing must never read as a pass. Requiring rc==1 in
# EVERY mode is DERIVED from the run: the plant only bites if the planted
# directory actually drifted between $PIN and HEAD.
if [ "$POSITIVE_CONTROL" -eq 1 ]; then
  _not_fatal=""
  for _pair in $MODE_VERDICTS; do
    _m="${_pair%%:*}"; _r="${_pair##*:}"
    [ "$_r" = "1" ] || _not_fatal="$_not_fatal $_m(rc=$_r)"
  done
  if [ -n "$_not_fatal" ]; then
    {
      echo ""
      echo "  The plant removed backup_and_replace \"$PLANT_TARGET\" from the copy"
      echo "  of upgrade.sh, yet these modes did NOT go FATAL:$_not_fatal"
      echo "  Most likely cause: nothing under '$PLANT_TARGET' changed between"
      echo "  $PIN and HEAD, so removing its refresh is undetectable — the"
      echo "  control is vacuous and proves nothing. Pick a PLANT_TARGET with"
      echo "  real drift, or advance the pin."
    } >&2
    scaffold "positive control did not fire in every mode"
  fi
  echo "positive control: FIRED in every mode (rc=1 each) — the gate is alive."
fi

echo ""
echo "=============================================================="
case "$OVERALL" in
  0) echo "RESULT: PASS — install and upgrade converge on the same framework"
     echo "        content in every ceremony mode tested ($MODES)." ;;
  2) {
       echo "RESULT: KNOWN-OPEN (exit 2) — the ONLY outstanding divergences are the"
       echo "        explicitly named PLAN-166 W1 prerequisites printed above."
       echo "        This is a FAILURE, not a skip. It goes green when W1 lands."
     } >&2 ;;
  1) echo "RESULT: FAIL (exit 1) — undeclared install/upgrade divergence above." >&2 ;;

exec
/bin/zsh -lc "grep -n \"Canhada-Labs/ceo-orchestration\\|repository-url\\|environment:\" .github/workflows/npm-publish.yml" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
34:#   - GA tags (`v1.4.0`) gate through `environment: production-npm`,
48:# deliberately NO `environment:` and NO RC exclusion, so it runs on RC
53:# `needs: await-release-gate`; its `environment: production-npm`
100:  # `environment:` and NO RC exclusion: it runs on rc tags too, which
218:    environment: production-npm
433:        # Canhada-Labs/ceo-orchestration, workflow npm-publish.yml,

exec
/bin/zsh -lc "grep -n \"write_install_manifest\\|Installation complete\" scripts/install.sh | tail -20; sed -n '2420,2495p' scripts/install.sh; tail -100 scripts/install.sh" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
787:# write_install_manifest exports these as FMS_DELIVERED_* so the shared
2276:write_install_manifest() {
2288:  _state_record_op "write_install_manifest" ".claude/.install-manifest.sha256"
2700:  write_install_manifest
    esac
  fi
  if [[ "${_DELIVERED_PROTOCOL:-0}" = "1" ]]; then
    case "${_CONTINUITY_PATHS:-}" in
      *"PROTOCOL.md"*) export FMS_HASH_SOURCE_PROTOCOL="HASH_PRIOR_RECORD" ;;
      *)               export FMS_HASH_SOURCE_PROTOCOL="HASH_TARGET" ;;
    esac
  fi
  export FMS_DELIVERED_SPEC="${_DELIVERED_SPEC:-0}"
  export FMS_DELIVERED_PROTOCOL="${_DELIVERED_PROTOCOL:-0}"
  export FMS_DELIVERED_MARKER="${_DELIVERED_MARKER:-0}"
  # Empty on a fresh install (target IS the freshly written pointer, hashing it
  # is correct); set only by the continuity path above.
  export FMS_PROTOCOL_HASH="${_PRIOR_PROTOCOL_HASH:-}"
  _write_baseline_manifest "$manifest"
  unset FMS_ROOT FMS_PROFILE_PARTS FMS_MODE FMS_HASH_ROOT FMS_PROTOCOL_HASH \
        FMS_PRIOR_MANIFEST FMS_HASH_SOURCE_SPEC FMS_HASH_SOURCE_PROTOCOL \
        FMS_HASH_SOURCE_MARKER
  unset FMS_DELIVERED_SPEC FMS_DELIVERED_PROTOCOL FMS_DELIVERED_MARKER
  return 0
}


# ----------------------------------------------------------------------
# PLAN-153 Wave B item B1 — persist the install-state.
# ----------------------------------------------------------------------
# Writes $TARGET/.claude/.install-state.json (next to the ADR-155 baseline
# manifest): the ORIGINAL request — verbatim argv + every parsed flag + the
# RESOLVED placeholder map (CLI > env > deterministic default; empty values
# omitted) — plus the operation journal for THIS run.
#
#   * Atomic: python writes a same-directory tempfile, then os.replace().
#   * Updated on every run: first_recorded_at + run_count + a bounded
#     history (last 20 runs) survive re-installs; request/operations
#     reflect the LATEST run.
#   * Schema-versioned: schema ceo.install-state/v1, schema_version 1.
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

echo ""
echo "==> Install complete."
echo ""
echo "==> Placeholders remaining (fill in manually):"
echo ""

# Grep for unsubstituted placeholders. Count + list files, then list
# the unique placeholder names per file. Emit a top-level warning if
# any remain (not an error — adopter may want to fill in gradually).
PLACEHOLDER_COUNT=0
PLACEHOLDER_ROOTS=(
  "$TARGET/.claude"
  "$TARGET/CLAUDE.md"
  "$TARGET/MEMORY.md"
  "$TARGET/PROTOCOL.md"
  "$TARGET/docs"
)
REMAINING_FILES=""
for root in "${PLACEHOLDER_ROOTS[@]}"; do
  [[ -e "$root" ]] || continue
  # Portable approach: use grep -l; harmless if no matches.
  while IFS= read -r f; do
    [[ -n "$f" ]] || continue
    REMAINING_FILES="${REMAINING_FILES}${f}"$'\n'
    PLACEHOLDER_COUNT=$((PLACEHOLDER_COUNT + 1))
  done < <(grep -RIl '{{[A-Z_][A-Z0-9_]*}}' "$root" 2>/dev/null || true)
done

if [[ $PLACEHOLDER_COUNT -eq 0 ]]; then
  echo "    (none — all substituted)"
else
  printf '%s' "$REMAINING_FILES" | sort -u | while IFS= read -r f; do
    [[ -n "$f" ]] || continue
    echo "    $f"
    grep -ho '{{[A-Z_][A-Z0-9_]*}}' "$f" 2>/dev/null | sort -u | sed 's/^/        /'
  done
  echo ""
  echo "    WARNING: $PLACEHOLDER_COUNT file(s) still contain {{PLACEHOLDER}} markers." >&2
  echo "             Re-run install.sh with more flags (e.g. --deploy-command ..)" >&2
  echo "             or edit the files manually." >&2
fi

echo ""
echo "==> Next steps:"
echo "    1. Edit CLAUDE.md to fill in your project context."
echo "    2. Edit .claude/team.md to add your personas (or start with archetypes)."
echo "    3. Start a Claude Code session and ask: 'Activate the CEO protocol and load the team.'"
# PLAN-135 W5 O12: close the install ceremony with a harness-native sanity
# check. /doctor validates settings.json / hooks / MCP wiring from inside the
# real Claude Code harness — it catches a malformed settings file BEFORE the
# framework's own gates run against it (the S217/S228 silent-hook class, where
# a settings-skip or exec-bit left a governance rail silently disengaged).
# Advisory + harness-side; install.sh prints it, it does not run claude.
echo "    4. Run \`claude\` and type \`/doctor\` once: confirm settings.json parses,"
echo "       hooks are registered, and no rail is silently skipped before you rely"
echo "       on the governance gates (catches malformed settings the framework"
echo "       would otherwise fail-open past). Then optionally run"
echo "       \`python3 .claude/scripts/ceo-info.py --check --hooks-diff\` for the"
echo "       framework-side mirror (registered-vs-effective hook count)."
if has_profile "fintech"; then
  echo ""
  echo "==> Fintech domain installed:"
  echo "    - 12 fintech skills in .claude/skills/domains/fintech/skills/"
  echo "    - FIN-*/EX-* pitfalls in .claude/skills/domains/fintech/pitfalls.yaml"
  echo "    - Reference personas in .claude/skills/domains/fintech/team-personas.md"
  echo "    - Additional commands in .claude/skills/domains/fintech/commands/"
fi

# PLAN-155 Wave 5 (debate A7) — the codex path closes with the arming check as
# its FINAL instruction: installed != armed. The check states loudly that
# NOTHING is enforced until /hooks trust is granted; a NOT-ARMED-(untrusted)
# verdict is EXPECTED on a fresh install and does NOT fail the install (trust
# is the operator's next, consent-gated step).
if [[ "$HARNESS" == "codex" ]]; then
  echo ""
  echo "==> Codex harness installed. FINAL STEP — arm enforcement:"
  codex_arming_check "$TARGET" || true
  echo ""
  echo "    Re-run the arming check any time:"
  echo "      $0 --harness codex --arming-check $TARGET"
  echo "    Uninstall the codex harness (lifecycle-symmetric):"
  echo "      $0 --harness codex --uninstall $TARGET"
fi

# PLAN-156 Wave 4 — the grok path closes with its arming check as the FINAL
# instruction (installed != armed; folder-trust is the operator's next step).
if [[ "$HARNESS" == "grok" ]]; then
  echo ""
  echo "==> Grok harness installed. FINAL STEP — trust the folder to arm enforcement:"
  grok_arming_check "$TARGET" || true
  echo ""
  echo "    Re-run the arming check any time:"
  echo "      $0 --harness grok --arming-check $TARGET"
fi

# Release workflow (.github/workflows/release.yml) replaces the
# PLACEHOLDER_RELEASE_FILL value below with the sha256 of everything
# above this trailer line at tag cut. DO NOT EDIT MANUALLY.
# CEO-INSTALL-SHA256: PLACEHOLDER_RELEASE_FILL

exec
/bin/zsh -lc "sed -n '1760,1840p' .claude/hooks/check_canonical_edit.py; sed -n '1385,1435p' .claude/hooks/check_canonical_edit.py" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
        return ""
    return (
        "\n\nUNLOCK WINDOW ARMED, NO TRUSTED SENTINEL ({diag}). Inside a "
        "CEO_SENTINEL_UNLOCK window the GPG rail is skipped, so a sentinel "
        "must prove it was not written by the agent, by ONE of:\n"
        "  (a) predating the session — export {anchor}=<sha of a commit "
        "taken BEFORE this agent session started>; capture it in your own "
        "shell (`git rev-parse HEAD`) before launching, never after;\n"
        "  (b) Owner-pinned content — export {digest}=<sha256 of the "
        "approved.md>, e.g. `shasum -a 256 <approved.md> | cut -d' ' -f1` "
        "(space- or comma-separate several).\n"
        "See ADR-119 Invariant 5."
    ).format(
        diag=_UNLOCK_TRUST_DIAG,
        anchor=_SESSION_ANCHOR_ENV,
        digest=_UNLOCK_DIGEST_ENV,
    )


def _sentinel_grants_path(sentinel_path: Path, target_rel: str) -> bool:
    """Check whether a sentinel file grants the given target path.

    PLAN-045 Wave 1 P0-01: verification is now two-tiered:

    1. **Plaintext ``Approved-By:`` line** — existing fast check (visual
       Owner signoff marker).
    2. **Detached GPG signature** at ``<sentinel>.asc`` — verified
       against ``.claude/sentinel-signers.txt`` allowlist via
       ``_lib.gpg_verify.verify_detached``. Fail-CLOSED on: missing
       .asc, bad signature, signer fpr not in allowlist, empty
       allowlist.

    **Environment bypass (interim, per ADR-010 amendment)**: setting
    ``CEO_SENTINEL_UNLOCK=<plan-id>`` + ``CEO_SENTINEL_UNLOCK_ACK=I-ACCEPT``
    in the parent shell short-circuits the .asc requirement. This is a
    dual-auth mechanism mirroring the arbitration-kernel escape hatch;
    a sub-agent cannot forge the env vars. The override is logged via
    ``veto_triggered(reason_code=sentinel_unlock_used)``.

    The sentinel must contain:
    1. A valid ``Approved-By: @<handle> <commit-sha>`` line
    2. A ``Scope:`` block listing the target path (one bullet per line)
    3. A sibling ``<sentinel>.asc`` detached GPG signature (unless env
       override is set)
    """
    # PLAN-094 Wave C — session cache fast-path before expensive GPG verify.
    # Cache key (iter-1 P0 fix): (path, inode, mtime_ns, file_size, sha256_full,
    # target_rel, fmt_version). Cache value: granted (bool). env_override path
    # bypasses cache (CEO_SENTINEL_UNLOCK semantic: must re-verify).
    global _SENTINEL_CACHE_HITS, _SENTINEL_CACHE_MISSES

    # PLAN-045 Wave 1 P0-01: env-override (CEO_SENTINEL_UNLOCK) detection.
    env = os.environ
    unlock_reason = (env.get("CEO_SENTINEL_UNLOCK") or "").strip()
    unlock_ack = (env.get("CEO_SENTINEL_UNLOCK_ACK") or "").strip()
    env_override = bool(
        unlock_reason
        and unlock_ack == "I-ACCEPT"
        and re.match(r'^(ADR-\d{3,4}|PLAN-\d{3})-[a-z0-9-]{3,100}$', unlock_reason)  # PLAN-086 Wave I.1 — ADR-119 tightening
    )

    # PLAN162_FIX_1 — SIGNATURE RAIL FIRST, and it is target-FREE.
    #
    # Two reasons the order changed (both are the fix):
    #   * #1 — verifying once per SENTINEL instead of once per
    #     (sentinel x target) is the whole amplification collapse; and
    #   * #10 — the target-keyed grant cache below hashes only
    #     approved.md, so a mutated .asc / allowlist / registry would ride
    #     a stale True if the grant fast-path ran first. Consulting the
    #     material-keyed rail up front makes a revocation land immediately.
    _trusted_text = None  # type: Optional[str]
    if not env_override:
        if not _signature_rail_ok(sentinel_path):
            return False
    else:
        # PLAN162_FIX_S2 — inside an unlock window the GPG rail is skipped
        # entirely, so the only thing separating an Owner-signed sentinel
        # from one the AGENT just wrote is provenance. See the module note
        # above for the two proof forms and the residual.
        _authorized, _trusted_text = _unlock_trusted_text(sentinel_path, env=env)
        if not _authorized:
    """
    if _gpg_verify is None:
        # _lib.gpg_verify is unavailable — fail-CLOSED. No sentinel
        # can grant canonical edits without the verification helper.
        return False
    sig_path = sentinel_path.with_name(sentinel_path.name + ".asc")
    # PLAN-089 Wave C.4 — dual-rail signer verification (ADR-121).
    # First-class path: legacy `.claude/sentinel-signers.txt` (existing).
    # Defense-in-depth: if YAML registry exists, re-check fingerprint via
    # _lib.sentinel_signers + bootstrap-SHA pin. Either rail rejecting
    # → fail-CLOSED. Post-GENESIS (_BOOTSTRAP_REGISTRY_SHA256 set),
    # parse/hash failure → fail-CLOSED (R2 Codex iter-1 Q5+Q7 fold);
    # pre-GENESIS (None), parse failure → legacy-only fallback.
    # PLAN162_FIX_1 (Codex P1 fold) — the subprocess is bounded by what is
    # LEFT of the invocation budget, minus the margin needed to still emit
    # a decision. ``None`` => not enough budget to verify AND emit: refuse
    # the spawn and latch, so the caller's next deadline poll produces the
    # fail-closed wall-deadline block instead of a harness kill.
    _timeout = _gpg_verify_timeout()
    if _timeout is None:
        _mark_wall_budget_exhausted()
        return False
    ok, _fpr, _reason = _gpg_verify.verify_detached(
        sentinel_path,
        sig_path,
        allowlist_path=_SENTINEL_SIGNERS_FILE,
        timeout=_timeout,
    )
    if not ok:
        return False
    if (
        _sentinel_signers is not None
        and _SENTINEL_SIGNERS_REGISTRY_YAML.exists()
        and _fpr
    ):
        _post_genesis = _BOOTSTRAP_REGISTRY_SHA256 is not None
        try:
            # Bootstrap SHA pin verification (post-GENESIS only).
            if _post_genesis:
                import hashlib as _hashlib
                _yaml_bytes = _SENTINEL_SIGNERS_REGISTRY_YAML.read_bytes()
                _computed_sha = _hashlib.sha256(_yaml_bytes).hexdigest()
                if _computed_sha != _BOOTSTRAP_REGISTRY_SHA256:
                    try:
                        from _lib import audit_emit as _audit_emit
                        if hasattr(_audit_emit, "emit_sentinel_signer_quorum_failed"):
                            _audit_emit.emit_sentinel_signer_quorum_failed(
                                key_id=_fpr,
                                reason="bootstrap_sha_mismatch",
                                source="canonical_edit_bootstrap_pin",
                            )

exec
/bin/zsh -lc "grep -n \"Approved-By\" .claude/hooks/check_canonical_edit.py | sed -n '1,100p'; sed -n '1840,1935p' .claude/hooks/check_canonical_edit.py" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
7:with a valid `Approved-By:` line and the target path declared in its
33:   b. If sentinel exists + `Approved-By:` line valid → allow.
464:    r"^\s*Approved-By:\s*@[\w\-]+\s+\S+", flags=re.MULTILINE
498:    r"Authorization(?:\s+source)?|Anchor\s+commit|Approved-By)"
511:#     Approved-By: @user <commit-sha>
552:    `Approved-By:`) or markdown horizontal rule (---, ***, ___) or
1531:# unguarded ``approved.md``, keep its ``Approved-By:`` line, ADD a target
1784:    1. **Plaintext ``Approved-By:`` line** — existing fast check (visual
1800:    1. A valid ``Approved-By: @<handle> <commit-sha>`` line
1912:    # `Approved-By:`) or markdown horizontal rule (`---`, `***`, `___`)
        if not _authorized:
            return False

    # PLAN-094 Wave C — session cache fast-path (now scope-only).
    # Cache key (iter-1 P0 fix): (path, inode, mtime_ns, file_size, sha256_full,
    # target_rel, fmt_version). Cache value: granted (bool). env_override path
    # bypasses cache (CEO_SENTINEL_UNLOCK semantic: must re-verify).
    _cache_key = None
    if not _sentinel_cache_disabled() and not env_override:
        _cache_key = _compute_sentinel_cache_key(sentinel_path, target_rel)
        if _cache_key is not None:
            _cached = _SENTINEL_VERIFY_CACHE.get(_cache_key)
            if _cached is not None:
                _SENTINEL_CACHE_HITS += 1
                return _cached
            _SENTINEL_CACHE_MISSES += 1

    # PLAN162_FIX_S2R2 (codex P1-1): under an unlock window the bytes that
    # decide are the ANCHORED bytes, never whatever an in-window writer
    # left at that path. ``None`` means "disk bytes ARE the authorized
    # bytes" (Owner-pinned digest, or the non-git residual).
    if _trusted_text is not None:
        text = _trusted_text
    else:
        try:
            text = sentinel_path.read_text(encoding="utf-8")
        except OSError:
            return False

    # Check plaintext signature marker first (cheap).
    if not _APPROVED_BY_RE.search(text):
        return False

    # Parse Scope: block.
    #
    # PLAN-064 Option D (DIM-13 closure, 2026-05-04) — tier-prioritized
    # parser:
    #   Tier 1: if HTML-comment markers <!-- BEGIN SIGNED SCOPE --> /
    #           <!-- END SIGNED SCOPE --> are present, parse Scope: ONLY
    #           from text between those markers. Lifecycle text outside
    #           the markers is ignored for grant decisions; it is
    #           documentation. The GPG `.asc` continues to cover the
    #           whole file (any tamper breaks the signature).
    #   Tier 2: if markers absent (legacy 44 sentinels at 2026-05-04),
    #           fall back to existing _SCOPE_HEADER_RE parser path
    #           below. No env flag — auto-detected.
    #
    # PLAN-044 audit-v2 C6-P0-04 (Tier 2 fallback) — supports two
    # on-disk formats:
    #
    # Format A (PLAN-050 round-17 era — single contiguous bullet list):
    #
    #     Scope:
    #       - .claude/path/one.md
    #       - .claude/path/two.md
    #
    # Format B (Session 67 mega-sentinel — categorized with sub-headers
    # and blank lines between groups):
    #
    #     Scope (24 canonical paths):
    #
    #     ADR canonical promotions (9 files, all from staging):
    #     - .claude/adr/ADR-083-...
    #     - .claude/adr/ADR-084-...
    #
    #     Hook code (PLAN-052):
    #     - .claude/hooks/_lib/foo.py (new)
    #     - .claude/hooks/check_bar.py (new)
    #
    # The Scope block extends from the `Scope` header line to the first
    # top-level continuation header (`Effective:`, `Plans:`, `Rationale`,
    # `Authorization source:`, `Anchor commit:`, a re-encountered
    # `Approved-By:`) or markdown horizontal rule (`---`, `***`, `___`)
    # or end-of-file. Sub-headers within Scope (lines ending with `:`
    # that are NOT in the terminator set) are silently skipped.

    # ---- PLAN162_FIX_4 (finding #4, consensus C5 — narrowed) ----
    #
    # The original council proposal ("parse ONLY inside the markers")
    # would have bricked 31% of live sentinels: 5 of 16 carry no BEGIN
    # marker, including the two most recent ceremonies. What ships is
    # three narrow rules instead:
    #
    #   1. A BEGIN marker with no well-formed PAIR must NEVER silently
    #      downgrade to the Tier-2 whole-file parser. The code already
    #      fail-CLOSES on that exact principle for a marker region with an
    #      unparseable INTERIOR; a BEGIN with a missing/malformed END did
    #      the opposite, which is the containment loss #4 reported —
    #      Scope bullets OUTSIDE the Owner's intended region were honored.
    #   2. Oversize (> _SCOPE_MARKER_CAP_BYTES) REJECTS fail-closed
    #      rather than downgrading to Tier-2. Blast measured ~zero (the
    #      largest live sentinel is 6,801 B = 10.4% of the cap).
    #   3. The END marker terminates a Tier-2 Scope block (added to
    #      _SCOPE_TERMINATOR_RE), so a bullet placed AFTER an END in a
    #      marker-less file is no longer collected.
    #

exec
/bin/zsh -lc 'ls -l scripts/tests/test-ownership-verdict-unit.sh scripts/tests/test-upgrade-spec-ownership.sh .claude/plans/PLAN-166/architect/round-1/approved.md' in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
-rw-r--r--@ 1 joaocanhada  wheel  10357 Aug  6 23:55 .claude/plans/PLAN-166/architect/round-1/approved.md
-rwxr-xr-x@ 1 joaocanhada  wheel   4266 Aug  6 23:57 scripts/tests/test-ownership-verdict-unit.sh
-rwxr-xr-x@ 1 joaocanhada  wheel  18617 Aug  6 23:55 scripts/tests/test-upgrade-spec-ownership.sh

exec
/bin/zsh -lc "nl -ba scripts/_framework_manifest_set.sh | sed -n '340,378p'" in /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553
 succeeded in 0ms:
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

codex
The patch still overclaims adopter-owned surfaces, loses or advances ownership records on several failure/rerun paths, and reports incorrect versions for pinned legacy sources. Its canonical authorization artifact is also unsigned, and the new ownership oracles are not wired into CI.

Full review comments:

- [P1] Require the detached Owner signature — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553/.claude/plans/PLAN-166/architect/round-1/approved.md:12-12
  These guarded workflow, governance, and installer edits rely on this sentinel, but the changes contain no sibling `approved.md.asc`; this line claims signing even though `check_canonical_edit.py` verifies a detached signature and fails closed when it is absent. Without an explicitly recorded unlock, the canonical changes cannot be authorized or landed.

- [P1] Honor the protocol ownership verdict — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553/scripts/upgrade.sh:3049-3049
  When a maintainer install skipped an adopter's pre-existing `PROTOCOL.md`, `_refresh_protocol_pointer` correctly returns `PRESERVE_UNOWNED HASH_NONE`, but this unconditional assignment marks it delivered anyway. The manifest rewrite then records the canonical pointer digest for the adopter-owned file, causing later tooling to treat an undelivered path as framework-owned.

- [P1] Require provenance before taking over pristine markers — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553/scripts/_framework_manifest_set.sh:556-557
  If `.claude/.framework-version` pre-existed and was skipped by install, a byte-identical value produces `prior_record=none`, `live_content=pristine`; this generic clause nevertheless declares it owned and the upgrade records it as a framework delivery. Future upgrades or uninstall can then modify/remove an adopter-owned file, so content-based legacy takeover must be restricted to the explicitly approved SPEC migration.

- [P1] Reject HASH-backed symlinks during installer reruns — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553/scripts/install.sh:2326-2326
  When a copy-installed conditional surface has a prior HASH record but its live path has been replaced by a symlink, the absence of a prior LINK row returns success here. The continuity branches then claim the symlink, and a `--link` rerun serializes its foreign target as a framework LINK delivery; this is the failing OWN-0052/OWN-0053 case and lets later tooling trust adopter-controlled targets.

- [P1] Preserve prior hashes when backup fails — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553/scripts/upgrade.sh:1981-1981
  If backing up a record-owned SPEC fails, `_SPEC_HASH_SOURCE` is still `HASH_SOURCE` from the unexecuted REFRESH verdict; setting only `_SPEC_DELIVERED=1` makes the manifest rewrite advance to source hashes although the target was untouched. This violates INV-3 and OWN-0024; the marker backup-failure branch at line 2099 has the same defect and must retain `HASH_PRIOR_RECORD` too.

- [P2] Retain SPEC provenance for an empty managed tree — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553/scripts/_framework_manifest_set.sh:386-386
  On an installer rerun after a managed `SPEC/v1` has been emptied, continuity requests `HASH_PRIOR_RECORD`, but this branch is reached only for live files emitted by `_framework_manifest_files`; an empty tree emits none, so the manifest replacement drops every SPEC record. The next upgrade sees an unrecorded non-absent tree and preserves it as an adopter fork instead of restoring the contract (OWN-0016).

- [P2] Report the pinned version for pre-marker sources — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553/scripts/upgrade.sh:2067-2073
  With `upgrade.sh --pin` targeting a pre-v1.3 source, this branch drops the marker record and claims readers can fall back to `VERSION`, but upgrade deliberately never updates the target's root `VERSION`. The checker therefore reports the original install version, an adopter application's version, or a fatal missing/malformed value rather than the pinned framework version.

- [P2] Wire the ownership oracles into CI — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553/.github/workflows/smoke-install.yml:221-224
  The workflow adds only the older S1-S8 test; neither `test-ownership-verdict-unit.sh` nor `test-ownership-table.sh` is invoked by any workflow, and their files/table are absent from these path filters. Consequently the known red ownership cells and future decision-table regressions can merge without any CI failure, contrary to the PLAN-167 consensus requiring the unit oracle per PR and the full table nightly.
The patch still overclaims adopter-owned surfaces, loses or advances ownership records on several failure/rerun paths, and reports incorrect versions for pinned legacy sources. Its canonical authorization artifact is also unsigned, and the new ownership oracles are not wired into CI.

Full review comments:

- [P1] Require the detached Owner signature — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553/.claude/plans/PLAN-166/architect/round-1/approved.md:12-12
  These guarded workflow, governance, and installer edits rely on this sentinel, but the changes contain no sibling `approved.md.asc`; this line claims signing even though `check_canonical_edit.py` verifies a detached signature and fails closed when it is absent. Without an explicitly recorded unlock, the canonical changes cannot be authorized or landed.

- [P1] Honor the protocol ownership verdict — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553/scripts/upgrade.sh:3049-3049
  When a maintainer install skipped an adopter's pre-existing `PROTOCOL.md`, `_refresh_protocol_pointer` correctly returns `PRESERVE_UNOWNED HASH_NONE`, but this unconditional assignment marks it delivered anyway. The manifest rewrite then records the canonical pointer digest for the adopter-owned file, causing later tooling to treat an undelivered path as framework-owned.

- [P1] Require provenance before taking over pristine markers — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553/scripts/_framework_manifest_set.sh:556-557
  If `.claude/.framework-version` pre-existed and was skipped by install, a byte-identical value produces `prior_record=none`, `live_content=pristine`; this generic clause nevertheless declares it owned and the upgrade records it as a framework delivery. Future upgrades or uninstall can then modify/remove an adopter-owned file, so content-based legacy takeover must be restricted to the explicitly approved SPEC migration.

- [P1] Reject HASH-backed symlinks during installer reruns — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553/scripts/install.sh:2326-2326
  When a copy-installed conditional surface has a prior HASH record but its live path has been replaced by a symlink, the absence of a prior LINK row returns success here. The continuity branches then claim the symlink, and a `--link` rerun serializes its foreign target as a framework LINK delivery; this is the failing OWN-0052/OWN-0053 case and lets later tooling trust adopter-controlled targets.

- [P1] Preserve prior hashes when backup fails — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553/scripts/upgrade.sh:1981-1981
  If backing up a record-owned SPEC fails, `_SPEC_HASH_SOURCE` is still `HASH_SOURCE` from the unexecuted REFRESH verdict; setting only `_SPEC_DELIVERED=1` makes the manifest rewrite advance to source hashes although the target was untouched. This violates INV-3 and OWN-0024; the marker backup-failure branch at line 2099 has the same defect and must retain `HASH_PRIOR_RECORD` too.

- [P2] Retain SPEC provenance for an empty managed tree — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553/scripts/_framework_manifest_set.sh:386-386
  On an installer rerun after a managed `SPEC/v1` has been emptied, continuity requests `HASH_PRIOR_RECORD`, but this branch is reached only for live files emitted by `_framework_manifest_files`; an empty tree emits none, so the manifest replacement drops every SPEC record. The next upgrade sees an unrecorded non-absent tree and preserves it as an adopter fork instead of restoring the contract (OWN-0016).

- [P2] Report the pinned version for pre-marker sources — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553/scripts/upgrade.sh:2067-2073
  With `upgrade.sh --pin` targeting a pre-v1.3 source, this branch drops the marker record and claims readers can fall back to `VERSION`, but upgrade deliberately never updates the target's root `VERSION`. The checker therefore reports the original install version, an adopter application's version, or a fatal missing/malformed value rather than the pinned framework version.

- [P2] Wire the ownership oracles into CI — /private/tmp/claude-501/-Users-joaocanhada-canhada-labs-ceo-orchestration/c1f32917-17c3-4a44-a74f-30277a04017a/scratchpad/plan167-overlay-235553/.github/workflows/smoke-install.yml:221-224
  The workflow adds only the older S1-S8 test; neither `test-ownership-verdict-unit.sh` nor `test-ownership-table.sh` is invoked by any workflow, and their files/table are absent from these path filters. Consequently the known red ownership cells and future decision-table regressions can merge without any CI failure, contrary to the PLAN-167 consensus requiring the unit oracle per PR and the full table nightly.
