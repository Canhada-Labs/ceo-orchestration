---
plan: PLAN-152
round: 1
rounds_synthesized: [round-1]
agents_considered: [qa-architect, devops-engineer, security-engineer, vp-engineering]
decisions_revised_in_plan:
  - "Wave B — tests-01/02 rewired (root tests/ → tests/unit/, explicit CI paths, two-pass serial split, outcome Check)"
  - "Wave B — ceremony reclassified (validate.yml + coverage.yml guarded); _lib/tests 128-site burndown moved to v1.0.2"
  - "Wave B — tests-07 pulled IN from §Deferred (serial marker, one-line)"
  - "Wave A — error-handling-01 rewritten: raw-text rescan branch, negative-control Check, default-on kill-switch"
  - "Wave A — governance-01 ordered FIRST; manual codex = hard recorded gate per kernel commit"
  - "Wave C — error-handling-03 relabeled NOT-guarded (lands direct, out of sentinel Scope)"
  - "Wave D — backlog-oidc DEFERRED to v1.0.2 (own plan); npm-publish.yml:3 false OIDC comment fixed in-wave; expiry calendar-flag stays"
  - "Wave D — tarball-02 packlist gate duplicated into validate.yml (PR/push); npm-publish.yml copy = last-line assert"
  - "Wave G — npm/package.json version bump added (release-blocker); fresh-session pair-rail probe added; CLAUDE.md §4 input-vs-infra amendment added"
  - "New §Release floor & degradation ladder; OQ1/OQ2/OQ3 resolved (pending Owner ratification)"
synthesized_at: 2026-07-01T23:30:00Z
synthesized_by: CEO
---

# PLAN-152 round-1 consensus

Verdicts: 4× ADJUST_PROCEED (Critic-A/B/C/D — map in `anonymization-map.md`).
Synthesis consumed anonymized critique text per DEBATE-SCHEMA §13.2.

## Consensus findings (2+ agents flagged)

1. **C1 — Root `tests/` stays CI-dark; tests-01/02 wiring as written does not deliver its own success criterion.**
   Flagged: Critic-A (MF1/MF2/MF4), Critic-B (M4), Critic-D (MF-3). Severity: HIGH.
   Mitigation: relocate the 13 root `tests/*.py` to `tests/unit/` (avoids the
   pytest.ini double-collection with the 7 existing `tests/<subdir>` entries,
   preserves swarm→replay ordering + federation scoping); wire `tests/unit` as an
   EXPLICIT path in the CI job; state invocation style = explicit paths with the
   two-pass `not serial`/`serial` split replicated; outcome Check ("collects
   expected count AND green over ≥2 consecutive runs, quarantine lane for flaking
   roots"). Lands in: Wave B tests-01/tests-02.
2. **C2 — Flake-class import: wiring 8 CI-dark roots under `-n auto` while deferring tests-07.**
   Flagged: Critic-A (R3), Critic-B (M3). Severity: HIGH.
   Mitigation: tests-07 pulled INTO Wave B (serial markers already filtered by
   `-m "not serial"` at validate.yml:298); pre-wiring audit of the 8 roots for
   wall-clock/perf tests. Lands in: Wave B (new tests-07 item; tests-01 Check).
3. **C3 — error-handling-03 ceremony label is FALSE (`.claude/workflows/*.js` is not canonical-guarded).**
   Flagged: Critic-C (MF1), Critic-D (MF-2). Severity: MEDIUM.
   Mitigation: relabel "NOT guarded — lands direct"; exclude from sentinel Scope;
   note follow-on evaluation of guarding workflows pairs with deferred
   governance-04. Lands in: Wave C.
4. **C4 — Fail-closed flip (error-handling-01) can brick benign sessions; Check lacks a negative control.**
   Flagged: Critic-A (MF3), Critic-C (MF3), Critic-D (MF-4 + Unseen-1). Severity: HIGH.
   Mitigation: adopt the raw-text-rescan branch (regex-scan the RAW subcommand for
   destructive signatures on `shlex.ValueError`; block only on hit); Check must
   assert BOTH `rm -rf ~ ";"` → block AND a benign unparseable command → allow;
   ship behind a default-on env kill-switch; codify the input-parse-fail-closed
   vs infra-fail-open distinction in CLAUDE.md §4 at Wave G closeout (§4 is
   Gate-1 cache-stable → closeout-only edit). Lands in: Wave A + Wave G.
5. **C5 — The pair-rail fix does NOT self-heal mid-session; the rail is dead for the WHOLE next-terminal run.**
   Flagged: Critic-C (R1/MF2), Critic-D (Nice-3). Severity: HIGH.
   Mitigation: governance-01 ordered FIRST in Wave A; manual
   `codex exec review --uncommitted` is a HARD, RECORDED gate (APPROVE artifact
   per kernel commit, `37867c2` precedent) for EVERY A/C/D/F kernel commit; Wave G
   adds a FRESH-SESSION probe of the restored registration. Lands in: §Approach +
   Wave A + Wave G.
6. **C6 — OIDC auth migration does not belong in this release.**
   Flagged: Critic-B (M5), Critic-C (MF4). Severity: HIGH (availability).
   Mitigation: DEFER backlog-oidc to v1.0.2 as its own plan (fallback window: do
   not delete NPM_TOKEN until one OIDC publish succeeds; npmjs.org web-console
   config is an Owner prereq unverifiable by CI); fix the false "OIDC trusted
   publisher" comment at npm-publish.yml:3 in Wave D (file already touched);
   calendar-flag NPM_TOKEN expiry ~2026-09-28 NOW. Lands in: Wave D + §Deferred.
7. **C7 — No cut line: single-session scope needs a release floor + degradation ladder.**
   Flagged: Critic-A (tag-not-blocked-by-B rule), Critic-B (OQ3 core + cut order),
   Critic-C (OQ3 floor), Critic-D (MF-5 + OQ3). Severity: HIGH.
   Mitigation: new §Release floor & degradation ladder (floor = A + B-core + D +
   G; cut order E → F(P3→P2) → C-economics → D-staging-refactor; packlist gate +
   null-guards never cut; floor-only ship = v1.0.1, remainder v1.0.2). Lands in:
   new plan section + OQ3 resolution.

## Single-agent insights kept

1. Critic-D (MF-1): **Wave B is not ceremony-free** — `.github/workflows/*.yml`
   (check_canonical_edit.py:182) and `.claude/hooks/_lib/**/*.py` (`**` spans
   `tests/`) are canonical-guarded; corroborated by the standing memory lesson
   ("`_lib/tests/` IS guarded"). Accepted: validate.yml + coverage.yml enter the
   sentinel Scope; the 128-site `_lib/tests` env-hygiene burndown moves to
   v1.0.2 (also the single biggest session-scope reducer). Tuple sequencing:
   v1.0.1 adds only cleaned roots (`swarm/tests`, `mcp-server/tests`,
   `detectors/tests`) to `_DEFAULT_SCAN_ROOTS`; `_lib/tests` joins in v1.0.2
   with its burndown.
2. Critic-B (M1): **npm/package.json version bump is a release-blocker**
   (npm-publish.yml:72-81 hard-fails on mismatch). Accepted → Wave G.
3. Critic-B (M2): **packlist gate must run on PR/push** (tag-only is too late).
   Accepted → tarball-02 rewritten (validate.yml stage→pack→assert; publish copy
   stays as last-line assert).
4. Critic-D (Nice-1): **verify install-npm.sh is a real second stager** before
   mirroring (else phantom edit). Accepted → tarball-01 note.
5. Critic-D (OQ1 refinement): **do NOT rename `MODEL_ID.OPUS47`** (stable
   identifier per _types.py:41); reconcile = docstrings :12/:41/:94 only.
   Accepted → sonnet5-tier item.
6. Critic-A (OQ1 addition): **regression test pinning current M-tier routing
   unchanged** so the label reconcile cannot silently repoint. Accepted →
   sonnet5-tier item.
7. Critic-A (R2-note): **swarm→replay S228 ordering reproduced by no CI job**.
   Accepted as a tests-01 wiring note (co-locate `replay/tests` after
   `swarm/tests` in the new job).
8. Critic-D (Unseen-2/3): per-ceremony-wave rollback note; A-before-B safety
   justification (Wave A blast covered by already-wired `.claude/hooks/tests/`).
   Accepted → §Approach.

## Single-agent insights rejected / deferred

1. Critic-C (OQ2): separate tight sentinel for Wave A. Not adopted as mandatory —
   3 of 4 critics prefer ONE sentinel with an enumerated explicit-file allowlist +
   mechanical `touched−scope=∅` gate. Recorded as a zero-cost signing-time variant
   at Owner discretion (same Wave-0 sitting can produce two sentinels).
2. Critic-A (OQ3): split-as-primary with Wave B excluded from the floor.
   Superseded by the floor synthesis (B-core stays in the floor per 3 of 4; the
   quarantine-lane rule absorbs the "B flakes must not block the tag" concern).

## Plan adjustments

Index only — the edits live in the plan file (S255 revision 2):

1. §Approach: manual-codex hard gate for the whole run; A-before-B justification;
   per-ceremony-wave rollback note.
2. Wave A: item order (governance-01 first); error-handling-01 rewritten
   (raw-text rescan + negative control + kill-switch).
3. Wave B: header ceremony note; tests-01/02 rewired per C1/C2; tests-03 split
   (v1.0.1 cleans 55 direct sites; _lib/tests 128 → v1.0.2); tests-07 pulled in.
4. Wave C: error-handling-03 relabeled lands-direct.
5. Wave D: backlog-oidc → §Deferred; tarball-02 PR/push gate; tarball-01
   install-npm.sh verification note; npm-publish.yml:3 comment fix.
6. Wave F: sonnet5-tier OPUS47 rename prohibition + routing-pin regression test.
7. Wave G: npm/package.json bump; fresh-session pair-rail probe; CLAUDE.md §4
   amendment.
8. New §Release floor & degradation ladder; §Open questions → §Resolved questions
   (pending Owner ratification via AskUserQuestion at next-terminal start).

## Round verdict

**PROCEED** — design-coherent after the adjustments above. No REJECT, no VETO,
no unresolved cross-critic contradiction. Per PROTOCOL §Verification cascade this
satisfies **V0 only**: shipping is authorized by V1 (deterministic gates) + V2
(Codex pair-rail truth gate) + V3 (Owner GPG) during execution, never by this
debate. Plan moves `draft → reviewed`.
