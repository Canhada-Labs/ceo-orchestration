---
id: ADR-111
title: Locked Corpus Governance — Pair-Rail Promotion Gate
status: SUPERSEDED
superseded_by: ADR-120
proposed: 2026-05-09
accepted: 2026-05-10
related_plan: [PLAN-075, PLAN-081]
related_adr: [ADR-052, ADR-105, ADR-106, ADR-107, ADR-108, ADR-120]
enforcement_commit: <set at Phase 4 ceremony commit time>
---

# ADR-111 — Locked Corpus Governance

## Status: SUPERSEDED by ADR-120 (2026-05-12)

Original ACCEPTED (PLAN-081 Phase 4 ceremony, 2026-05-10). Renamed + superseded by ADR-120 per ADR-117 collision-rename policy (PLAN-085 Wave 0 + Wave B.1). Substance is fully preserved in ADR-120; this file is the retired original-numbered record.

**Superseded-By:** ADR-120

R1 PLAN-081 consensus C4 + S-QA-Unseen lifted ADR-111 from PROPOSED-OPTIONAL
→ RECOMMENDED → ACCEPTED at Phase 4 (corpus-driven governance precedent
from PLAN-050 mutation-fixture-as-ADR pattern).

## Context

PLAN-081 Phase 4 ships the locked corpus N=15 + promotion gate per
spec.md §11 + ADR-108 §Operational. Without ADR-111 governance, the
corpus would be a normal git-tracked directory subject to ad-hoc edits
+ no clear add/retire/freeze protocol. The promotion gate's mechanical
verdict relies on **corpus immutability** as a structural defense
against same-LLM bias drift; mutating the corpus mid-experiment defeats
the cross-LLM disagreement signal.

ADR-013 (mutation-fixture governance, PLAN-050) is the precedent:
mutation fixtures are governed via ADR rather than prose because
fixture mutation = experiment tampering. The same principle applies
here.

## Decision (ACCEPTED)

The locked corpus at `.claude/plans/PLAN-081/corpus/locked/` governs:

### 1. Corpus immutability via SHA-256 frozen MANIFEST

Each fixture file in the corpus is referenced in
`.claude/plans/PLAN-081/corpus/locked/MANIFEST.md` with its SHA-256 +
fixture metadata (stratum, severity, scope, expected verdict). The
MANIFEST + each fixture file become canonical-guarded under three
globs added to `_CANONICAL_GUARDS` in `check_canonical_edit.py`:

- `.claude/plans/PLAN-*/corpus/locked/MANIFEST.md`
- `.claude/plans/PLAN-*/corpus/locked/**/*.py`
- `.claude/plans/PLAN-*/corpus/locked/**/*.js`

**Errata (2026-05-11 S101-cont):** the original ADR-111 ACCEPTED
2026-05-10 stated this guard extension would land in the Phase 4
ceremony alongside the framework. In ship reality, Phase 4 (commit
`93310eb`) shipped only the gate machinery + governance + audit emit
+ MANIFEST format with corpus N=0 — the guard extension was deferred
to Phase 4-bis (the fixture-authoring follow-up) because authoring
the 15 fixtures is a separate pre-condition before guard activation
makes sense. Phase 4-bis ceremony Block 4 lands the
`_CANONICAL_GUARDS` extension atomically with the 15 fixtures + this
errata edit + the updated MANIFEST. Mutation post-Phase 4-bis
requires sentinel-gated edit + ADR-111 amendment per §3.

### 2. Reopen criteria (per consensus C6)

The locked corpus is reopen-able under exactly these conditions:

- **Corpus defect found** (fixture has a true bug — e.g. SQL injection
  fixture has wrong syntax that fails to demonstrate the vulnerability):
  Owner authors a sentinel-gated patch + re-runs promotion gate. The
  fixture's expected verdict may change; the catch_rate baseline
  re-establishes.
- **Codex CLI version bump >5pp catch_rate shift**: per R1 C5 (Phase 6
  Codex CLI pin), if a CLI version upgrade shifts the catch_rate by
  more than 5pp on the fixed corpus, ADR-111 amendment + Phase 4
  re-run + ADR-108 reopen ceremony triggers.
- **New attack class emerges** (e.g. a novel prompt-injection variant):
  Owner authors a NEW fixture in the appropriate stratum + extends the
  corpus from N=15 to N=15+k. Existing fixtures retain their SHA pin;
  new fixtures get their own SHA. Catch rate rebaselines for the
  expanded corpus (denominator changes; numerator preserved for
  existing fixtures).
- **Fixture retirement** (rare): if a fixture becomes obsolete (e.g.
  the underlying language feature no longer exists), Owner authors a
  RETIRE marker in MANIFEST.md (NOT delete). Retired fixtures don't
  count toward catch_rate denominator but remain in git history.

### 3. Add/retire fixture protocol

- **Add**: NEW fixture authored under `corpus/locked/<stratum>/<id>.{py,md,...}`
  + MANIFEST entry with full SHA + metadata + GPG-signed sentinel.
  Stratum balance per C4 (6 trivial + 4 medium + 3 adversarial + 2
  VETO-floor-discriminative); deviations require ADR-111 amendment.
- **Retire**: fixture stays on disk; MANIFEST entry marked
  `retired: true` + `retired_at: <date>` + `reason:` field. Promotion
  gate skips retired fixtures in catch_rate computation (denominator
  excludes them).
- **Patch** (in-place edit due to defect): treated as RETIRE + ADD. The
  fixture's old SHA is logged in MANIFEST history block; new SHA
  registered. Promotion gate sees the patched fixture as a new entry.

### 4. Corpus stratification (per R1 C4 + S-Sec NTH-Sec-2)

| Stratum | N | Difficulty | Coverage |
|---|---|---|---|
| trivial | 6 | obvious P0 | SQL injection, hardcoded secret, alg=none JWT, race condition, null-deref, command-injection |
| medium | 4 | non-obvious P1 | TOCTOU, prototype pollution, regex DoS, path-traversal |
| adversarial | 3 | clean code with red-herrings | comment-baited refactor, correct-but-risky pattern, silent-data-corruption |
| VETO-floor-discriminative | 2 | check_codex_response.py ingress sanitization signal | prompt-injection-payload-in-comment, secret-in-source-string |
| **Total** | **15** | | |

R1 S-Sec NTH-Sec-2 added the VETO-floor-discriminative stratum so the
corpus directly exercises Phase 1-full ingress sanitization (not just
Phase 4 promotion gate logic).

### 5. Phase 4 ship scope vs Phase 4-bis follow-up

**Phase 4 (shipped 2026-05-10, commit `93310eb`)** shipped the
**framework only**: MANIFEST format documented (corpus N=0), gate
machinery (`run-promotion-gate.py` with 2-pass-with-triage logic),
ADR-111 ACCEPTED, audit-emit `pair_rail_promotion` registered.
The corpus directory existed but contained no fixture files and no
canonical-guard coverage (see §1 errata).

**Phase 4-bis (shipped 2026-05-11, S101-cont)** ships:
- N=15 authored fixtures across 4 strata (per §4 stratification)
- Updated MANIFEST.md with full SHA-pinned `fixtures:` block
- `_CANONICAL_GUARDS` extension to `check_canonical_edit.py`
  registering 3 globs (MANIFEST + `**/*.py` + `**/*.js`)
- This §5 + §1 errata edit recording the actual ship cadence

**Authoring N=15 fixtures with full content** is scoped to Phase 4-bis
(rather than Phase 4) because each fixture requires careful
adversarial-resistant content design (~150L per fixture; ~2250L total)
that exceeds a single-session budget AND because the canonical-guard
flip is materially meaningful only once the fixtures exist (guarding
an empty directory is a no-op).

The promotion gate was non-functional until N reached 15 (the gate
refuses to engage when corpus_n < 15 unless `CEO_PHASE_4_PARTIAL_OK=1`
env override is set, in which case it emits `manual_triage=True` + a
forensic artifact noting partial corpus). With Phase 4-bis ship,
N=15 condition is met and the override is no longer required for
production runs.

This phased authoring is documented in §6 below.

### 6. Reopen-as-experiment vs reopen-as-defect

Two distinct reopen flavors:

- **Defect** (fixture has true bug): closes via sentinel-gated patch,
  re-runs gate, no ADR amendment unless catch_rate shift >5pp.
- **Experiment** (intentional corpus expansion or retirement):
  requires ADR-111 amendment + Owner physical sign-off + Phase 4 re-run
  ceremony.

The promotion-gate verdict artifact (`pair_rail_promotion`
record) carries `corpus_manifest_sha` so post-hoc analysis can
correlate verdicts with the exact corpus version they were computed
against.

## Sec dissent (R1 C6 4-of-5 endorse vs Sec REJECT)

Sec REJECTED the 2-pass-with-triage compromise (preferred strict
15/15 mechanical bind). 4-of-5 endorsed N-of-M with manual triage as
forensic (NOT silent override). Sec dissent recorded in ADR-108
§Operational + this ADR for permanence.

If post-GA `audit-query.py fp-rate --window-days 30` reveals that >5% of
manual-triage paths resolved as false-negatives (Owner labels
mis-triaged fixtures as `tp` post-hoc), Sec was right and ADR-111 +
ADR-108 reopen ceremony triggers.

## References

- ADR-013 (mutation-fixture governance — precedent for corpus-as-ADR)
- ADR-052 (VETO floor invariant)
- ADR-105 (multi-supersede 084+085+096)
- ADR-106 (Codex MCP adapter PostToolUse advisory)
- ADR-107 (asymmetric VETO matrix Cases A-F)
- ADR-108 (cross-LLM VETO floor §Operational labeling protocol)
- PLAN-050 §mutation-fixture (precedent for corpus-as-ADR)
- PLAN-075 spec.md v5 §11 + Phase 0A SPIKE-VERDICT.md (U7 + U9b empirical baseline)
- PLAN-081 §3 Phase 4 + §4 ADR transitions
- `.claude/plans/PLAN-081/corpus/locked/MANIFEST.md` (SHA pinning)
- `.claude/scripts/run-promotion-gate.py` (gate execution)
