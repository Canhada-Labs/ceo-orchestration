---
plan: PLAN-166
round: 1
type: architect-sentinel
segment: W1-FINDINGS-CLOSURE
---

# PLAN-166 W1 — release-hold findings-closure ceremony (Owner sentinel)

Anchor-SHA: 05e4845060f16d5b5bbce0fe1eea792a14118ed0

Approved-By: @Canhada-Labs (Owner GPG — signed inline by the ceremony)
Approved-At: 2026-08-07

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
