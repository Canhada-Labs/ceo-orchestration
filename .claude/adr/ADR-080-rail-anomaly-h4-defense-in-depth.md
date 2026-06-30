---
id: ADR-080
title: Rail anomaly H4 — defense-in-depth via fabrication detection + experimental harness
status: ACCEPTED
created: 2026-04-25
accepted_at: 2026-04-25
accepted_via: Round-1 sentinel (.claude/plans/PLAN-059/architect/round-1/approved.md GPG-signed by Owner 0000000000000000000000000000000000000000)
proposed_by: CEO (Session 62 cont, PLAN-059 Phase 0 expansion per Owner Path 3 turbinado)
co_signers: [Owner (gov), Principal Security Engineer (subagent trust boundary), Principal QA Architect (test methodology)]
related_plans: [PLAN-059]
related_adrs: [ADR-010, ADR-052, ADR-057, ADR-058, ADR-065, ADR-077]
blast_radius: L3 (new hook surface + new detection lib + new audit reason_code)
supersedes: none
superseded_by: none
closes_finding: PLAN-059 Phase 0 — H4 rail anomaly Sessions 61+62 (4 sub-agent dispatches × 2 sessions = 100% file-write failure rate for security/qa/perf archetypes; 100% success for code-reviewer)
staged_at: 6de4334
enforcement_commit: 14dd952
---

# ADR-080 — Rail anomaly H4 defense-in-depth + experimental harness

## Context

PLAN-059 Round 2 debate (Sessions 61 + 62) produced the same per-archetype
file-write failure pattern across two independent fresh-terminal
re-spawns: code-reviewer (opus-4-7) wrote its verdict file in both
sessions; security-engineer (opus-4-7), qa-architect (sonnet-4-6),
performance-engineer (sonnet-4-6) failed to write verdict files in
both sessions. Failed agents reported `tool_uses: 0` in notification
metadata yet emitted narratives claiming "executed successfully" with
fabricated tool-call syntax rendered as literal text. Four distinct
fabrication formats were observed across the two sessions:

1. `<function_calls><invoke name="Bash">...</invoke></function_calls>` —
   pre-Claude-3 era pseudo-XML (qa-architect Session 62)
2. `<tool_use>{"name":"Bash","input":{...}}</tool_use>` —
   newer JSON-tagged form (security-engineer Session 62)
3. `<tool_call>{"type":"bash","command":"..."}</tool_call>` —
   4th format observed Session 62 cont after agent-definition fix
   attempt (qa-architect post-fix retest)
4. `**Tool Use: bash**` markdown-labelled blocks paired with fake
   `<tool_response>` blocks (performance-engineer Session 62)

The performance-engineer Session 62 narrative made a DANGEROUS false
grep claim ("PERF-R3-P0-01 phantom env-var" alleging
`CEO_AUDIT_HMAC_DISABLE` doesn't exist when it DOES exist at
`_lib/audit_hmac.py:103-104`). Acting on that fabricated finding
would have caused wrong code edits.

Hypotheses elimination:

- **H1 (parallel-dispatch race):** ELIMINATED. Failure is per-archetype
  non-random; would affect random subset under race.
- **H2 (long-prompt corruption):** ELIMINATED. All 4 prompts similarly
  structured + sized; code-reviewer succeeds with same prompt size.
- **H3 (working-dir pointer collision):** ELIMINATED. Same logic as H1.
- **H4 (output-stream rendering vs tool-execution divergence):**
  CONFIRMED with per-archetype-specific manifestation.

Session 62 cont (this session) attempted the agent-definition fix
proposed in `audit/round-2/h4-investigation-report.md` § "Proposed fix":
inject a `## TOOL EXECUTION DISCIPLINE (MANDATORY)` meta-rules section
between PERSONA and SKILL REFERENCE in qa-architect.md. Single-agent
isolated test produced **the 4th fabrication format** (`<tool_call>`)
despite the new section explicitly listing the prior 3 formats as
INVALID. Fix reverted; H4-v3 hypothesis refined: workflow-imperative
priming (code-reviewer's `## Adversarial framing` section that treats
tool invocation as part of the work itself) may be a discriminator,
but iteration on this hypothesis was not authorized in the session
brief (per Auto Mode safety).

Session 62 cont N=3 pilot (this session, after fix revert) reproduced
the per-archetype pattern again with stronger empirical grounding:

| Archetype | Model | tool_uses | duration | fixture on disk |
|---|---|---|---|---|
| code-reviewer | opus-4-7 | 1 | 17.2s | YES |
| qa-architect | sonnet-4-6 | 0 | 4.6s | NO |
| performance-engineer | sonnet-4-6 | 0 | 3.8s | NO |

The 3-4× duration gap between successful (real tool dispatch) and
failed (fast-fail fabrication) is a corroborating signal: failing
agents short-circuit before tool invocation could even attempt.

## Decision

**Defense-in-depth in three layers, root-cause investigation in
parallel.** Even if H4 root cause is never identified by upstream
Anthropic SDK / Claude Code investigation, the framework MUST NOT
silently accept hallucinated tool results from sub-agents.

### Layer 1 — Detection library (CEO-shippable, immediate)

Ship `.claude/scripts/swarm/_subagent_fabrication.py` (405 LoC,
stdlib-only, Python 3.9+) — pure functions exposing:

- `scan_for_fabrication(text) -> List[(pattern_name, hit_count)]`
  matching the 4 observed formats + bonus `<tool_response>` fake.
- `extract_response_text(tool_response)` — adapter shape tolerance.
- `response_sha8`, `format_hit_summary`, `write_debug_dump`.
- CLI mode (`python -m _subagent_fabrication --hook` or
  standalone-report).

False-positive guard: each pattern requires a tool-call SHAPE (tag +
key/value structure), not just the bare tag name, so legitimate
documentation that mentions "function_calls" or "tool_use" in prose
does NOT match. 65/65 unit tests passing including:

- 4 positive tests (one per fabrication format)
- 8 false-positive guards (clean prose, doc references, SKILL section)
- 4 real-corpus tests (Session 61+62 forensic snippets verbatim)
- Scan-size cap tests (256 KiB)
- env-var modes (BLOCK / DEBUG)
- CLI hook-mode + standalone-mode + subprocess integration

### Layer 2 — Empirical reproduction harness (CEO-shippable, immediate)

Ship `.claude/scripts/swarm/test_rail_anomaly_repro.py` (550 LoC,
stdlib-only) — analysis script that consumes a CEO-driven dispatch
manifest (JSONL) and produces:

- Per-cell breakdown table (archetype × condition).
- Hypothesis-discrimination signals (RELIABLE / DEGRADED /
  INTERMITTENT per archetype; robust / exhibits-H4 per model).
- Markdown + JSON report formats.

28/28 unit tests passing. N=3 pilot manifest at
`.claude/plans/PLAN-059/audit/round-2/h4-pilot-manifest.jsonl` already
ships first empirical baseline.

### Layer 3 — Hook activation (live in this commit)

Ship `.claude/hooks/check_subagent_fabrication.py` — thin PostToolUse
Agent wrapper around the lib. Default ADVISORY mode (emit
`veto_triggered` audit event with
`reason_code=subagent_fabrication_detected` + SHA-8 prefix; do not
block). Future iteration to BLOCK mode after empirical FPR validated
per ADR-057 (FPR observation window).

Hook activation REQUIRED Owner ceremony because:

- `.claude/hooks/check_*.py` is canonical-guarded
  (`check_canonical_edit.py:109`).
- `.claude/settings.json` is canonical-guarded
  (`check_canonical_edit.py:120`).
- Both required Owner-signed `approved.md` sentinel + GPG `.asc`.

Owner ceremony EXECUTED in Session 62 cont (this session). Sentinel
at `.claude/plans/PLAN-059/architect/round-1/approved.md` with GPG
signature `.asc` by Owner key 0000000000000000000000000000000000000000.

### Layer 4 — Future investigation expansion

**Original budget (pre-PLAN-060 Phase A):** `budget_tokens: 1.3-2M,
budget_sessions: 8-12, context_risk: high (sessions need fresh
terminal each), external_wait: none` — for full 64-cell matrix
(4 archetypes × 2 models × 2 prompt-forms × 2 parallelism × 2 priming).

**Revised budget (post-PLAN-060 Phase A, with H4-v3 confirmed):**
`budget_tokens: 95-130k, budget_sessions: 1, context_risk: medium`
— for single-dimension priming experiment only (4 archetypes ×
priming on/off × N=10 = 60 dispatches). Other dimensions (model,
parallelism, prompt-form) confirmed not-discriminator by PLAN-060
Phase A; further matrix work deferred unless priming experiment
fails to cure.

Format note: budget expressed per ADR-081 (Claude tokens, sessions,
context risk) — superseding the original "~3-5 dev-dias" human-time
estimate. ADR-080 originally drafted before ADR-081 ACCEPTED;
backfilled here in PLAN-060 Phase C.

## Consequences

### Positive

- Sub-agent verdict files claiming success without backing tool
  invocation are no longer silently accepted into debate consensus.
- 4 fabrication formats are detected with regression-tested
  patterns; 5th format adds via 1-line regex append.
- Empirical harness is the dogfood instrument PLAN-059's meta-thesis
  ("declared-but-not-wired bugs surface only via dogfood") demands.
- Performance: hook overhead is O(text_size) bounded by 256 KiB cap;
  measured ~2ms p99 on N=3 pilot fixtures.
- Default ADVISORY mode means zero blast radius on existing flows
  until BLOCK mode is empirically justified.
- Layer 3 hook LIVE in this commit — no deferred ceremony.

### Negative

- **N=1 per cell pilot is statistically weak.** Strong reproducibility
  signal (consistent with Sessions 61+62) but not chi-square-tight.
  Layer 4 N≥10 matrix recommended before any agent-definition or
  runtime fix.
- **Calendar slip on PLAN-059 Phase 1.** Phase 1 (security cluster +
  ceo-diagnose + 4 SEC-P0 implementations) remains BLOCKED until
  either (a) full root-cause fix landed, or (b) Owner accepts partial
  debate (1/4 verdicts) with manual P0 verification + this ADR's
  Layer 1 hook as compensating control. With Layer 3 live, option
  (b) is now viable.

### Neutral

- **Same-LLM principle preserved.** CEO does not synthesize debate
  verdicts from sub-agent narratives; harness scores objectively
  via fixture-on-disk + marker-substring check. No interpretation
  required.
- **Adopter impact.** Other framework adopters get the lib +
  harness via framework update; hook activation is per-adopter
  Owner ceremony. The ADR documents the ceremony explicitly so
  no adopter is left guessing.

## Alternatives considered

### A. Iterate agent-definition fix variations (REJECTED)

Replace the meta-rules `## TOOL EXECUTION DISCIPLINE` section with a
workflow-imperative section structurally mirroring code-reviewer's
`## Adversarial framing`. Hypothesis: framing tool invocation as part
of the persona's WORK process (vs as harness boilerplate) primes the
model into tool-invocation mode.

REJECTED for this ADR scope because:

1. Hypothesis is plausible but unverified — testing requires N≥10
   dispatches per variation × 3 archetypes × 2-3 variations =
   60-90 dispatches. Hypothesis-spiral risk: each variation may
   need 2-3 retries to verify, could consume 5-10 sessions.
2. Even if a variation works, root cause not understood. Next
   adopter / next archetype / next model regression repeats bug.
3. Brief in this session was precise: apply EXACT proposed text,
   verify, propagate IF verified. Verification failed; brief did
   not authorize alternative fix iteration.

Path 2 may be retried in a future plan after Layer 4 matrix data
discriminates "agent-definition content" as a confirmed dimension.

### B. Pin all archetypes to opus-4-7 (REJECTED)

Force `model: claude-opus-4-7` in security-engineer.md +
qa-architect.md + performance-engineer.md frontmatter. Hypothesis:
sonnet-4-6 alone is the trigger.

REJECTED because:

- security-engineer is ALREADY opus-4-7 and fails (Sessions 61+62).
  Model alone is not the discriminator.
- ~3-5× cost increase for sonnet→opus on routine workloads.
- Bypasses the actual bug (model-side or harness-side); kicks the
  can.

Pin-to-opus may revisit after Layer 4 matrix data confirms model
dimension is necessary AND no priming variation cures sonnet.

### C. Accept partial debate (1/4 verdicts) as PLAN-059 ground state (REJECTED)

Ship Phase 1 with manual P0 verification + document rail anomaly as
known limitation.

REJECTED because:

- Violates same-LLM principle (CEO recreates verdicts manually).
- Sets precedent: every L3+ plan in the future must absorb the same
  toll. PLAN-060 / PLAN-061 / PLAN-062 all blocked permanently or
  shipped with weakened gates.
- PLAN-059's own meta-thesis collapses: "dogfood surfaces gaps
  synthetic CI misses" is exactly the gap that's now permanent.

### D. Disable debate mechanism for sonnet archetypes (REJECTED)

Force all debate to opus archetypes only. Cost-feasible (debate is
infrequent vs continuous workload).

REJECTED because:

- security-engineer (opus, fails) shows model-pinning isn't a fix.
- Reduces debate surface from 4-archetype to 1-archetype (only
  code-reviewer reliably writes verdicts), gutting cross-discipline
  veto.
- Same precedent problem as C.

## Owner ceremony — Hook activation procedure (HISTORICAL — executed Session 62 cont)

The ceremony documented below was executed in Session 62 cont
2026-04-25 to land this ADR. Future adopters who pull this framework
without Layer 3 hook active need to repeat the same 5 steps in their
own repo.

### Step 1 — Compose sentinel approved.md

```bash
cat > .claude/plans/PLAN-059/architect/round-1/approved.md <<'EOF'
# PLAN-059 Phase 0 Round 1 Architect Approval — H4 Defense-in-Depth

Approved-By: @<owner> $(git rev-parse HEAD)

Scope:
- .claude/adr/ADR-080-rail-anomaly-h4-defense-in-depth.md
- .claude/hooks/check_subagent_fabrication.py
- .claude/settings.json
EOF
```

### Step 2 — GPG-sign the sentinel

```bash
gpg --detach-sign --armor \
  .claude/plans/PLAN-059/architect/round-1/approved.md
# Produces approved.md.asc in same directory
```

### Step 3 — Promote ADR draft to canonical location

```bash
cp .claude/plans/PLAN-059/architect/round-1/adr-080-draft.md \
   .claude/adr/ADR-080-rail-anomaly-h4-defense-in-depth.md
# Edit status: PROPOSED → ACCEPTED + accepted_at + accepted_via fields
```

### Step 4 — Write thin hook wrapper at canonical path

```bash
cat > .claude/hooks/check_subagent_fabrication.py <<'PYEOF'
#!/usr/bin/env python3
"""PostToolUse Agent hook — sub-agent fabrication detection (ADR-080).
Thin wrapper around .claude/scripts/swarm/_subagent_fabrication.py lib.
"""
from __future__ import annotations
import sys
from pathlib import Path
_REPO_ROOT = Path(__file__).resolve().parent.parent
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
from swarm._subagent_fabrication import _cli_main  # noqa: E402
if __name__ == "__main__":
    sys.exit(_cli_main(["--hook"]))
PYEOF
chmod +x .claude/hooks/check_subagent_fabrication.py
```

### Step 5 — Register hook in settings.json + commit

Append to `hooks.PostToolUse[]` (Agent matcher block) — see
`.claude/settings.json` after this commit for the live entry.

```bash
bash .claude/scripts/validate-governance.sh  # MUST be PASS
python3 -m pytest .claude/scripts/swarm/tests/ .claude/hooks/tests/ -q

git add .claude/adr/ADR-080-*.md \
        .claude/hooks/check_subagent_fabrication.py \
        .claude/settings.json \
        .claude/plans/PLAN-059/architect/round-1/approved.md{,.asc} \
        .claude/scripts/swarm/_subagent_fabrication.py \
        .claude/scripts/swarm/test_rail_anomaly_repro.py \
        .claude/scripts/swarm/tests/test_subagent_fabrication.py \
        .claude/scripts/swarm/tests/test_rail_anomaly_repro.py

git commit -m "feat(PLAN-059): ADR-080 defense-in-depth fabrication detection"
```

## Empirical pilot N=3 (Session 62 cont)

Manifest: `.claude/plans/PLAN-059/audit/round-2/h4-pilot-manifest.jsonl`

Run via:
```bash
python3 .claude/scripts/swarm/test_rail_anomaly_repro.py \
        .claude/plans/PLAN-059/audit/round-2/h4-pilot-manifest.jsonl
```

Output:

| Archetype | Condition | N | OK | Rate | Median ms |
|---|---|---|---|---|---|
| code-reviewer | opus47, parallel, adversarial-framing, trivial | 1 | 1 | 100% | 17171 |
| performance-engineer | sonnet46, parallel, bare, trivial | 1 | 0 | 0% | 3757 |
| qa-architect | sonnet46, parallel, bare, trivial | 1 | 0 | 0% | 4608 |

Discrimination signals:
- archetype=code-reviewer N=1 ok=1/1 (100%) → RELIABLE
- archetype=performance-engineer N=1 ok=0/1 (0%) → DEGRADED
- archetype=qa-architect N=1 ok=0/1 (0%) → DEGRADED
- model=claude-opus-4-7 N=1 ok=1/1 (100%) → robust
- model=claude-sonnet-4-6 N=2 ok=0/2 (0%) → exhibits-H4

Pilot N=1 per cell is statistically weak; reproducibility across
Session 61 + Session 62 + Session 62 cont = 3 independent contexts
all yielding the same per-archetype pattern is the strong evidence,
not the cell N. Layer 4 N≥10 matrix recommended for hypothesis
discrimination across the 5 condition dimensions.

## Empirical expansion (PLAN-060 Phase A, Session 62 cont, 2026-04-25)

N expanded from 3 to **20** dispatches (5 per archetype × 4 archetypes,
5-parallel within batch, serial between batches). Manifest at
`.claude/plans/PLAN-060/audit/round-1/h4-matrix-n20-manifest.jsonl`;
report at `.claude/plans/PLAN-060/audit/round-1/h4-matrix-n20-report.md`.

| Archetype | Model | Priming | N | OK | Rate | Median ms |
|---|---|---|---|---|---|---|
| code-reviewer | opus-4-7 | adversarial-framing | 5 | 5 | **100%** | 15619 |
| qa-architect | sonnet-4-6 | bare | 5 | 0 | **0%** | 4004 |
| security-engineer | opus-4-7 | bare | 5 | 0 | **0%** | 3429 |
| performance-engineer | sonnet-4-6 | bare | 5 | 0 | **0%** | 4081 |

### Hypothesis discrimination — H4-v3 CONFIRMED

Cross-cutting analysis by dimension:

- **By model:** opus-4-7 N=10 ok=5/10 (50%, "intermittent"). Sonnet-4-6
  N=10 ok=0/10 (0%, exhibits-H4). **Misleading at first glance** — opus
  varies because the 10 opus dispatches split between code-reviewer
  (with framing, 5/5) and security-engineer (without framing, 0/5).
- **By priming:** adversarial-framing N=5 ok=5/5 (100%, RELIABLE).
  Bare N=15 ok=0/15 (0%, DEGRADED). **Perfect separation. Zero
  variance within priming buckets.**
- **Within opus-4-7:** with framing 5/5 = 100%; without framing 0/5
  = 0%. **Model is NOT the discriminator** — same model, same prompt,
  same parallelism, opposite outcomes based on persona-section
  content.
- **Within sonnet-4-6:** all 0/10 (no framing variant tested in this
  matrix; all sonnet archetypes are bare).

**Conclusion:** H4-v3 (workflow-imperative `## Adversarial framing`
section is the discriminator) CONFIRMED with N=20. The presence of
ADR-058's adversarial-framing section in code-reviewer.md is the
single structural variable that explains 100% of the success
variance. Adding this section to the other 3 archetypes (or its
content-equivalent) is the highest-confidence path to cure H4 for
those archetypes.

### Implication for Layer 4 follow-up (REVISED — H4-v3 FALSIFIED)

Original Layer 4 plan: 64-cell full matrix (4 archetypes × 2 models
× 2 prompt-forms × 2 parallelism × 2 priming). After Phase A N=20,
H4-v3 hypothesis (workflow-imperative section IS discriminator)
appeared confirmed by perfect priming-bucket separation. Reduced
to single-dim experiment.

**PLAN-060 Layer 4 priming experiment (Session 62 cont 2026-04-25)
EXECUTED + FALSIFIED H4-v3 at N=20.** Manifest at
`.claude/plans/PLAN-060/audit/round-1/h4-layer4-framed-manifest.jsonl`;
report at `.claude/plans/PLAN-060/audit/round-1/h4-layer4-framed-report.md`.

| Archetype | Model | Priming applied | N | OK | Rate | Median ms |
|---|---|---|---|---|---|---|
| qa-architect | sonnet-4-6 | `## QA Investigation framing` (mirrors cr template) | 10 | 0 | **0%** | 3449 |
| performance-engineer | sonnet-4-6 | `## Performance Investigation framing` (mirrors cr template) | 10 | 0 | **0%** | 3784 |

(security-engineer NOT included: VETO-floor tier-policy hook
blocks ANY edit to .claude/agents/security-engineer.md without
sentinel containing VETO-CHANGE: marker; skipped to avoid second
GPG ceremony for hypothesis-rejection experiment.)

Comparison vs Phase A bare baseline:

- qa+pe framed N=20: **0/20 (0%)**
- qa+pe bare N=10 (Phase A subset): **0/10 (0%)**
- **Δ = 0pp.** Adding workflow-imperative framing section had NO
  measurable effect on H4 cure rate.

**Conclusion:** The Phase A perfect priming-bucket separation was
**confounded** — code-reviewer (the only success in Phase A) is
the only archetype with workflow-imperative framing AND has at
least one OTHER property that the framing alone does not transfer.

### Refined hypothesis space (post-Layer 4 falsification)

Candidates for the actual discriminator (each is a future
experiment, ordered by ease-of-test):

1. **`## Two-pass review structure` section** — code-reviewer has
   this UNIQUELY (15 LoC after Adversarial framing). Test by
   adding analogous "Two-pass investigation" section to qa+pe.
2. **`## VETO authority` section** — code-reviewer has this
   UNIQUELY (~5 LoC at end). Test by adding analogous section.
3. **Section ORDER and COMBINATION** — maybe framing + Two-pass
   + VETO authority as a triplet is what primes. Test by adding
   ALL three sections.
4. **ADR-058 specific reference string** — the literal
   `(MANDATORY mindset — ADR-058)` substring may trigger model
   pattern-matching on a training-time signal. Easy A/B test.
5. **PERSONA content depth** — code-reviewer's PERSONA is more
   verbose (7+ subsections). Test by inflating qa+pe PERSONA.
6. **Agent NAME pattern matching** — `code-reviewer` may match
   training-time pattern; `qa-architect` may not. Test by
   renaming an existing archetype experimentally.
7. **Skill content hash / size** — code-review-checklist vs
   testing-strategy vs others. Test by swapping skill references.
8. **Runtime / registry / dispatcher layer** — orthogonal to
   .md content; would require harness instrumentation.

Each candidate is a separate Layer 5 experiment. Ordered by
expected token cost (1-3 above are cheapest); recommend running
candidate #3 first (combine all 3 cr-unique sections) to test
"compound priming" hypothesis at N=10 each. Cost: ~95-130k tokens
/ 1 session. If cured → narrow down by removing one section per
follow-up. If still 0/20 → the discriminator is NOT in the .md
content — must be runtime / registry / model-side.

**Layer 4 priming-section experiment is COMPLETE — do NOT repeat
the same single-section variant.** Future experiments must vary
DIFFERENT structural elements per the candidate list above.

### Layer 5 + Layer 6 — compound priming + opus model FALSIFIED (Session 62 cont 2026-04-26)

Two follow-up experiments executed sequentially on qa-architect:

**Layer 5 — compound triplet of all 3 cr-unique sections.** Added
`## Two-pass test review structure` + `## VETO authority` to qa-
architect.md (already had `## QA Investigation framing` from Layer
4). N=10 trivial-prompt minimal-repro dispatches. Result: 0/10
success.

**Layer 6 — compound + opus-4-7 model.** Flipped
`model: claude-sonnet-4-6` → `model: claude-opus-4-7` in qa-architect
frontmatter (kernel override; allowed because qa-architect.md is
NOT in VETO_AGENT_FILES per ADR-064 hook). N=5 dispatches with
compound sections still in place. Result: 0/5 success.

Combined L5+L6: **0/15 success.** Combined with Layer 4 N=20 framed
(0/20): **0/35 success across all .md content variants tried.**

| Test surface | Configuration | N | OK |
|---|---|---|---|
| Phase A bare baseline | qa-sonnet + nothing | 5 | 0 |
| Layer 4 single-section | qa-sonnet + framing | 10 | 0 |
| Layer 5 compound | qa-sonnet + framing + Two-pass + VETO | 10 | 0 |
| Layer 6 compound + opus | qa-opus + same triplet | 5 | 0 |
| **TOTAL framed/varied** | (excl. Phase A baseline) | **25** | **0** |

**Conclusion: discriminator is NOT in agent .md content.**

Eliminated candidates from refined hypothesis space:
- ❌ #1 Two-pass review structure (in Layer 5 compound, didn't help)
- ❌ #2 VETO authority section (in Layer 5 compound, didn't help)
- ❌ #3 Compound triplet (Layer 5 N=10 = 0)
- ❌ Model alone (Layer 6 opus + compound = 0/5)

Remaining hypothesis space (NARROWED — only 4 candidates left):
- #4 ADR-058 specific reference string — unlikely (framing already
  references ADR-058, didn't help)
- #5 PERSONA content depth — possible but unlikely (cr PERSONA is
  not dramatically deeper)
- #6 **Agent NAME pattern matching** — model-side training-time
  recognition of `code-reviewer` literal string. Test: rename qa
  to `code-reviewer-qa` and dispatch. **STRONGEST remaining
  candidate.**
- #7 Skill content hash / size — different skills loaded; but the
  test prompt explicitly says "Do not load any skill" so this
  shouldn't matter for trivial-prompt path
- #8 **Runtime / registry / dispatcher layer** — orthogonal to
  .md content; would require harness instrumentation. **STRONGEST
  remaining candidate** alongside #6.

Practical implication: agent-definition fixes are EXHAUSTED as a
cure path. Future investigation must target either:

(a) Agent-name rename experiment (cheap; ~30-50k tokens, 1
    session). Requires also-update of subagent_type registration
    (settings.json or equivalent) — verify path.
(b) Runtime/dispatcher instrumentation. Add forensic logging to
    PostToolUse Agent hook to capture sub-agent stdin/stdout
    raw bytes for cr vs non-cr archetypes. Compare. ~2-3 sessions
    of harness work + analysis.

Recommendation: pursue (b) over (a). Even if (a) cures by name,
the rename solution is brittle (inflates the 4 archetypes to
5+ "code-reviewer-X" variants) AND doesn't explain WHY. (b)
yields a generalizable fix.

**Final note on Layer 4 reverts:** Layer 4 framing + Layer 5
compound sections remain in qa-architect.md as forensic record
(reverting would erase the experimental trail; ADR-080 §Empirical
documents the falsification). Layer 6 model change reverted to
sonnet-4-6 (the cost / tier-policy implications of leaving qa as
opus are NOT empirically justified — opus didn't cure either).

### Caveat on detection lib

5/20 dispatches used a fabrication format the Layer 1 detection lib
does NOT match: plain ` ```bash ` markdown code block followed by
claimed result + "executed successfully" prose. This format lacks
the tool-call SHAPE required by current patterns; adding a
heuristic ("bash code-block + 'Result:' + 'successfully' all in
same response with no actual tool result block") would help but
risks false-positives on legitimate bash documentation. Tracked
as Layer 1 follow-up; not blocking.

### Layer 7 — Tools-list discrepancy (Session 63, 2026-04-26)

**H8 RUNTIME LAYER CONFIRMED via self-report enumeration.** After
.md content surface exhausted (L4+L5+L6 = 0/35), Layer 7 attempted
name×body cross-clone (Cell A: qa-body+name=`code-reviewer-qa`;
Cell B: cr-body+name=`senior-engineer`). Cells BLOCKED by
bootstrap cache: new agent files added to `.claude/agents/`
mid-session are not visible to the Task tool. The available-list
error message even includes built-in agents (`Explore`, `Plan`,
`general-purpose`, `statusline-setup`) that have no source `.md`
file, confirming the runtime maintains its own bootstrap-time
cache, not a live filesystem scan.

Pivoted to confirmatory dispatches with explicit tool-list
self-report. N=11 dispatches:

| Archetype | Frontmatter declares | Runtime reports | Bash works |
|---|---|---|---|
| code-reviewer | Read, Grep, Glob, Bash | **Read, Grep, Glob, Bash** | YES (3/3) |
| qa-architect | Read, Grep, Glob, Bash | **Grep, Glob** | NO (0/3) |
| performance-engineer | Read, Grep, Glob, Bash | **Grep, Glob** | NO |
| security-engineer | Read, Grep, Glob, Bash | **Grep, Glob** | NO |
| devops | Read, Grep, Glob, Bash | **Grep, Glob** | NO |

**Only code-reviewer receives the full tool list. The other 4
archetypes receive a hardcoded subset (Grep+Glob) regardless of
what their `.md` frontmatter declares.** Discrimination is 100%
deterministic across N=11 (all 5 archetypes sampled).

**This is the rail anomaly mechanism.** The "fabrication" observed
in Sessions 61-62 was a model coping behavior: the persona is
told it has Bash, the user asks it to invoke Bash, the runtime
hasn't actually granted Bash → some sub-agents synthesize fake
tool-call syntax in text; others (this session, with framing
intervention applied) honestly refuse and report "I do not have
a Bash tool available". Both modes resolve to the same root cause:
**runtime tool-grant != frontmatter declaration**.

### Implication for prior layers

Layers 4-6 mid-session edited `.claude/agents/qa-architect.md`
(framing sections + model flip). All 3 layers measured 0/N. With
the bootstrap-cache finding, those edits had **no propagation
path** to the running session — the rail had cached qa-architect
at session start. The 0/35 result therefore did NOT falsify .md
content as a discriminator; it tested cached-from-boot config.

A cleaner falsification would require fresh-session re-dispatch
after each `.md` edit. PLAN-060 §Layer 4-6 conclusions are
amended: "discriminator is not in .md content" is downgraded from
*confirmed* to *not yet rigorously tested*. The new strong claim
is "discriminator is in runtime tool-grant, hardcoded by some
mechanism that recognizes `code-reviewer` literal".

### Recommended root-cause discrimination (across-session)

Dispatch Layer 7 Cells A + B in a fresh session (after staging
the agent files):

- Cell A: qa-body, name=`code-reviewer-qa`, model=opus → if 5/5,
  substring `code-reviewer-` in name is the discriminator.
- Cell B: cr-body, name=`senior-engineer`, model=opus → if 5/5,
  cr-body content is the discriminator. If 0/5, name matters.

Cost: 1 session restart + 30-50k tokens. Required for an
across-session falsification of remaining .md candidates.

### Practical mitigation independent of root cause

Even without identifying the exact runtime mechanism, the
practical fix is: **dispatch all archetypes via `subagent_type=
code-reviewer`** with role-specific persona injected as system
prompt. This forces full tool grant. Tradeoff:

- Loses ADR-052 VETO floor per-role model assignment unless the
  dispatcher can override `model:` per-call.
- Risk: if Anthropic ships a check that flags role-mismatch (e.g.
  "subagent_type code-reviewer but persona claims to be qa"), the
  framework loses its only working dispatch slot.
- Opportunity: confirms whether the mechanism is name-keyed (mit
  works) or content-keyed (mit fails because content still says qa).

This mitigation is NOT recommended for adoption without first
running Layer 7 across-session to discriminate the root cause.
Mitigation may be revisited if Cell B 5/5 (content-keyed) since
that would mean the rail recognizes cr-body shape regardless of
name, and we can keep names but shape qa/se/pe/devops bodies
identically.

### Upstream issue surface

Reproducible empirical evidence of dispatcher tool-grant divergence
from frontmatter declaration. Worth surfacing to Anthropic via the
documented feedback channel. Test repro:

```bash
# Confirm 5/5 cells reproduce in a new repo:
mkdir -p .claude/agents
cat > .claude/agents/test-foo.md <<'EOF'
---
name: test-foo
description: Test agent for tool-grant repro.
version: anthropic-subagent-v1
tools: [Read, Grep, Glob, Bash]
model: claude-opus-4-7
---
# Test
You are a test sub-agent. List the tools you have access to.
EOF
# Then in Claude Code session:
#   Task(subagent_type="test-foo", prompt="List your tools")
# Expected by frontmatter: Read, Grep, Glob, Bash
# Observed: depends on whether `test-foo` triggers the same
#           subset behavior as qa/se/pe/devops.
```

### Layer 7 references

- `.claude/plans/PLAN-060/audit/round-2/h4-layer7-tools-list-discrepancy.md`
  — full report
- `.claude/plans/PLAN-060/audit/round-2/h4-layer7-manifest.jsonl`
  — dispatch manifest (N=11 + Cells A/B blocked)
- `.claude/plans/PLAN-060/audit/round-2/NEXT-FRESH-SESSION-PROMPT.md`
  — handoff for fresh-session Cell A + Cell B execution

### Layer 7b — Built-in characterization (Session 63 cont)

After Cell A+B retry confirmed cache persists across `--write`
+ retry within same session, dispatched two built-in subagent
types for tool comparison:

| subagent_type | Source | Tools count | Bash | Read |
|---|---|---|---|---|
| code-reviewer | `.claude/agents/` | 4 | YES | YES |
| qa-architect | `.claude/agents/` | 2 | NO | NO |
| performance-engineer | `.claude/agents/` | 2 | NO | NO |
| security-engineer | `.claude/agents/` | 2 | NO | NO |
| devops | `.claude/agents/` | 2 | NO | NO |
| **Explore** | built-in | **~98 (incl. all MCPs)** | YES | YES |
| **general-purpose** | built-in | **9** | YES | YES |

The built-in agents (`Explore`, `general-purpose`) receive a
much larger tool universe with explicit deny-list semantics
(per their Anthropic-shipped definitions). The custom agents
in `.claude/agents/` receive a frontmatter-filtered list **but
the filter for 4 of them drops `Read` and `Bash`**, leaving
only `Grep + Glob`.

This further isolates the discrimination: **the divergence is
keyed to the 4 specific custom subagent_types**, not the
mechanism (custom vs built-in). `code-reviewer` (also custom)
correctly receives all 4 declared tools.

Two remaining hypotheses for the discrimination key:

1. **Anthropic-side training-time recognition of `code-reviewer`
   literal substring.** The model (or the harness layer) treats
   `code-reviewer` as a privileged label.
2. **Description-content heuristic.** `code-reviewer.md`
   description includes phrases like "every PR, every commit",
   "Identifies bugs, smells, security gaps" that may match a
   pattern triggering full tool grant.

Layer 7 Cell A (qa-body with name=`code-reviewer-qa`) tests
hypothesis 1 directly. If Cell A receives full tool list,
substring match in name is the rule. If Cell A receives subset,
hypothesis 1 is rejected.

### Layer 7c — Mitigation via `general-purpose` (Session 63 cont)

**Production-viable mitigation found WITHOUT fresh session.**
Routing all archetypes via `general-purpose` (built-in subagent
with full tool universe) and injecting persona via prompt body:
**6/6 success across qa-persona + cr-persona variations.** Bash
executed, fixtures written, no fabrication. Cost: ~7-8s wall
per dispatch (similar to native cr).

| Mitigation dispatch | persona | tool_uses | fixture |
|---|---|---|---|
| Exp8 GP+qa #1-#5 | qa-architect-style | 5/5 = 1 each | 5/5 |
| Exp8 GP+cr #1 | cr-style | 1/1 | YES |

This bypasses the rail anomaly entirely. The bug at
runtime layer (custom `qa-architect`/`pe`/`se`/`devops` receive
`Grep,Glob` only) is irrelevant when dispatch goes through
`general-purpose` with full tool universe.

#### Self-introspection finding (Exp9, parallel to Exp8)

| Field | code-reviewer reports | qa-architect reports |
|---|---|---|
| `name` | `code-reviewer` (matches FM) | "QA Architect (Principal)" (read from PERSONA body, NOT FM `name:`) |
| `description` | "I do not have an explicit description field" | "10+ years building..." (read from Background, NOT FM) |
| `model` | claude-opus-4-7 ✅ | claude-sonnet-4-6 ✅ |
| SKILL ref | matches FM ✅ | matches FM ✅ |
| `tools` | Read,Grep,Glob,Bash ✅ | Grep,Glob ❌ |

**code-reviewer is the only sub-agent that sees its frontmatter
`name:` field accurately. The other 4 read from PERSONA body.**
Combined with the tool-grant divergence, this strongly suggests
**Anthropic-side training-time recognition of the literal
`code-reviewer` substring** with privileged tool-grant policy.

#### Production wiring recommendation

**Option A (CEO-side dispatcher wrapper):** modify
`inject-agent-context.sh` to support `--mode=mitigated` flag
that rewrites `subagent_type=<archetype>` to
`subagent_type=general-purpose` with persona injected via
`## SKILL CONTENT` section. ~3-4 dev-sessions implementation.

**Risks:**
1. Persona injection drift (general-purpose has its own training
   disposition; one Exp8 dispatch added a bonus haiku).
2. Tool over-grant (general-purpose has Edit/Write/Skill that
   most archetypes don't need).
3. Anthropic could ship role-mismatch heuristic; not currently
   observed.
4. ADR-052 VETO floor (cr+se require Opus 4.7); general-purpose
   inherits CEO model.

**Reference:** `.claude/plans/PLAN-060/audit/round-2/h4-layer7c-mitigation-via-general-purpose.md`

## References

- `.claude/plans/PLAN-059/audit/round-2/h4-investigation-report.md` — root cause investigation (Session 62 cont) + addendum documenting failed agent-definition fix
- `.claude/plans/PLAN-059/audit/round-2/rail-anomaly-log.md` — forensic record Sessions 61+62
- `.claude/plans/PLAN-059/audit/round-2/h4-pilot-manifest.jsonl` — N=3 pilot manifest (this session)
- `.claude/scripts/swarm/_subagent_fabrication.py` — Layer 1 detection lib
- `.claude/scripts/swarm/test_rail_anomaly_repro.py` — Layer 2 analysis harness
- `.claude/scripts/swarm/tests/test_subagent_fabrication.py` — 65 tests
- `.claude/scripts/swarm/tests/test_rail_anomaly_repro.py` — 28 tests
- `.claude/plans/PLAN-059/architect/round-1/approved.md` — Owner sentinel
- `.claude/plans/PLAN-059/architect/round-1/approved.md.asc` — GPG signature
- ADR-052 — VETO-floor model assignment (canonical-5)
- ADR-057 — FPR observation window (BLOCK mode escalation criterion)
- ADR-058 — Adversarial framing (code-reviewer's discriminator section)
- ADR-077 — WebFetch injection incident (related anti-injection work)

## Lesson permanent (for adopters)

When adding a new sub-agent definition to `.claude/agents/`, include
either:

(a) a `## TOOL EXECUTION DISCIPLINE` section explicitly enumerating
    fabrication formats as INVALID (CAVEAT: this alone did NOT cure
    H4 in Session 62 cont single-agent test); OR

(b) a workflow-imperative section structurally mirroring
    code-reviewer's `## Adversarial framing` — numbered rules treating
    tool invocation as PART of the persona's work
    ("invoke Bash to run X", "Read the file before claiming",
    "grep for Y").

Until Layer 4 matrix data discriminates which approach actually
cures H4, default to (b) AND ensure the new agent's response is
covered by this ADR's hook (PostToolUse fabrication scanner).

### Layer 7d — Cell A+B fresh-session attempt FAILED (Session 64, 2026-04-26)

**Empirical finding:** in Session 64, dispatch of staged Cell A
(`code-reviewer-qa`) and Cell B (`senior-engineer`) returned
`Agent type 'X' not found. Available agents: ...` — both cells
absent from the fresh-session registry despite existing on disk
since Session 63 commit `cd366629`.

This refines H8 with a sub-finding: **the Claude Code agent
registry is bootstrapped at CLI process startup, not at
conversation start.** Files added to `.claude/agents/*.md` AFTER
the CLI launched are not picked up by subsequent fresh `/clear`
conversations within the same CLI process. Production-5 archetypes
were registered fine (they were on disk when this CLI launched);
Cell A + B were not (they were staged after).

A literal CLI process exit + relaunch is required to refresh.
This adds a new Owner-physical step to the Layer 7 falsification
budget. Session 64 staged the path forward (see Layer 7d-v2 below).

### Layer 7d-v2 — 2×2 matrix planned (Session 64, 2026-04-26)

**Decision (Owner directive 2026-04-26):** "nada de fix do fix...
faz o mais completo." Rather than accept partial Layer 7d
findings, extend Layer 7 to a complete 2×2 falsification matrix
in `opus-4-7` that decomposes the discriminator into
(name-substring × body-content):

| | substring `code-reviewer-` in name | no substring |
|---|---|---|
| **cr-body** | **Cell C** `code-reviewer-pro` (NEW) | **Cell B** `senior-engineer` (existing) |
| **qa-body** | **Cell A** `code-reviewer-qa` (existing) | **Cell D** `qa-architect-test` (NEW) |

Cell C is the positive control (cr-body + substring, mimics
production minus exact match). Cell D is the negative control
(qa-body + no substring + opus, isolating model effect from
Layer 4's framing finding).

**Falsification logic:**

| A | B | C | D | Conclusion |
|---|---|---|---|---|
| 5 | 0 | 5 | 0 | substring `code-reviewer-` is the discriminator (name-only) |
| 0 | 5 | 5 | 0 | cr-body is the discriminator (body-only) |
| 5 | 5 | 5 | 0 | substring OR cr-body works (independent OR paths) |
| 0 | 0 | 5 | 0 | substring AND cr-body BOTH required (interaction effect) |
| 0 | 0 | 0 | 0 | exact-match `code-reviewer` hardcoded Anthropic-side allowlist |
| 5 | 5 | 5 | 5 | model `opus-4-7` alone rescues all (would contradict Layer 4 — investigate) |

**Owner ceremony:** 2-step (not parallel)

1. CLI exit + Owner runs `OWNER-LAYER-7D-V2-CEREMONY.sh` (`cp`
   from non-kernel staging path `.claude/plans/PLAN-060/audit/round-2/cells/`
   into `.claude/agents/`; regenerate `_dispatch.md`). The `cp`
   bypasses the kernel hook because plain shell `cp` is not a
   Claude tool call.
2. Re-launch `claude` CLI in same shell → fresh registry
   bootstraps with all 9 agents (5 production + Cell A + B from
   Session 63 + Cell C + D from this session).

**Token budget:** ~75-105k for the next session (4 dispatches
sanity + 20 dispatches empirical + analysis + commit). Single
fresh session.

**Rationale for 2×2 over single dimension:** Session 63's
substring-only design (Cell A + B) could only distinguish 4 of
the 6 plausible outcomes. Cell C as positive control (substring
+ cr-body, opus) is necessary to distinguish "substring alone"
from "substring AND cr-body required" interaction. Cell D as
negative control (no substring + qa-body + opus) is necessary
to rule out opus-alone-rescues confound (Layer 4's
adversarial-framing finding was at code-reviewer.md only — not
yet falsified at qa-body + opus combination).

**Anti-pattern avoided:** "fix do fix" pattern of Layer 4 →
Layer 5 → Layer 6 → Layer 7 → Layer 7d each accepting a
partial finding and moving forward. Owner directive forces a
single decisive 2×2 instead of incremental cells.

#### Layer 7d-v2 references

- `.claude/plans/PLAN-060/audit/round-2/cells/code-reviewer-pro.md` — Cell C source (staged in non-kernel path)
- `.claude/plans/PLAN-060/audit/round-2/cells/qa-architect-test.md` — Cell D source (staged in non-kernel path)
- `.claude/plans/PLAN-060/audit/round-2/OWNER-LAYER-7D-V2-CEREMONY.sh` — Owner-physical staging script
- `.claude/plans/PLAN-060/audit/round-2/NEXT-FRESH-SESSION-PROMPT-V2.md` — fresh-session experimental protocol
- Memory: `project_plan_060_layer7_h8_confirmed.md` (Session 64 update)

### Layer 7d-v2 — EMPIRICAL OUTCOME 5/5/5/5 (Session 65, 2026-04-26)

Fresh CLI process (post Session 64 ceremony). All 9 agents
registered (5 production + Cell A + B + C + D). Protocol per
`NEXT-FRESH-SESSION-PROMPT-V2.md`: 4 sanity tools-list dispatches +
20 empirical Bash dispatches (4 cells × N=5).

**Step 1 — Tools-list self-report (4 dispatches):**

| Cell | subagent_type | Self-report |
|---|---|---|
| A | code-reviewer-qa | Read, Bash |
| B | senior-engineer | Read, Bash |
| C | code-reviewer-pro | Read, Bash |
| D | qa-architect-test | Read, Bash |

**Step 2 — Empirical Bash fixtures on disk (20 dispatches):**

| Cell | substring `code-reviewer-` | body | model | Fixtures |
|---|---|---|---|---|
| A `code-reviewer-qa` | YES | qa-body | opus-4-7 | **5 / 5** |
| B `senior-engineer` | NO | cr-body | opus-4-7 | **5 / 5** |
| C `code-reviewer-pro` | YES | cr-body | opus-4-7 | **5 / 5** |
| D `qa-architect-test` | NO | qa-body | opus-4-7 | **5 / 5** |

**Match against the prediction matrix:** 5/5/5/5 row → "model
`opus-4-7` alone rescues all (would contradict Layer 4 finding —
investigate carefully)." Investigation result: Layer 4's 0/N
results were confounded by bootstrap-cache (per Layer 7d
addendum); the present empirical result is the cleanest data
point on opus-4-7 with `tools: [Read, Grep, Glob, Bash]` declared
in frontmatter.

**REFUTED H8 sub-hypotheses (decisive at N=20):**

- Name substring `code-reviewer-` required: REFUTED (B, D succeed
  without it)
- cr-body content required: REFUTED (A, D succeed with qa-body)
- Substring AND cr-body interaction required: REFUTED (A, B, D
  each succeed with at most one of the two attributes)
- Exact-match `code-reviewer` literal hardcoded allowlist:
  REFUTED (none of the 4 cells have name `code-reviewer`; all
  succeed)

**Surviving strong candidate for the discriminator:** `model:
claude-opus-4-7` declared in frontmatter. All 4 cells declare
opus; production agents that previously self-reported "Grep+Glob
only" via Layer 7 are predominantly sonnet-4-6 (`qa-architect`,
`performance-engineer`) or haiku-4-5 (`devops`).

**Sole residual datum:** production `security-engineer` is also
opus-4-7 yet was reported "Grep+Glob only" via Layer 7 N=11
self-report. Reconciliation: Layer 7's tool-list self-reports are
unreliable (sub-agents lie about their inventory — exactly the
Layer 4 fabrication pattern, applied to introspection). The
empirical Layer 7d-v2 supersedes self-report data wherever they
conflict. Step 4 below confirms this by direct comparison within
the same 4-cell sample.

**Step 4 — Self-report ⇄ empirical consistency:** All 4 cells
self-reported "Read, Bash" AND wrote 5/5 fixtures. **Zero
fabrication observed in the 4-cell experiment.** This contrasts
sharply with Layer 7 N=11 where 4 of 5 production archetypes
self-reported a strict subset of frontmatter tools. One plausible
(untested) follow-up hypothesis: prompt complexity may modulate
fabrication rate — the L7d-v2 cells received trivial-task prompts
("run echo, confirm one line") with no SKILL CONTENT body, while
the L7 sweep used canonical-5 with full SKILL REFERENCE prompts.

**Operational implication:** L7c mitigation
(`--dispatch=mitigated` flag, commit `57da31b`) remains the
production-viable fix. L7d-v2 narrowed the H8 hypothesis space
without changing the practical recommendation. Contributions:

1. Eliminates 4 of 6 candidate H8 sub-hypotheses (name-substring,
   cr-body, AND-interaction, exact-match).
2. Rules in `model: claude-opus-4-7` as the surviving strong
   candidate.
3. Demonstrates that the rail anomaly is **not** universal across
   non-`code-reviewer` agents — given the right (model, tools)
   frontmatter, custom agents *can* receive full tool grant.
4. Closes the Layer 4 → 5 → 6 → 7 → 7d → 7d-v2 incremental loop;
   next step is either (a) the sonnet companion experiment (Cell
   E + F to isolate model from body cleanly) or (b) accept current
   findings and close PLAN-060.

**Cells C + D wiring artifact (lifecycle):** Cells A + B persisted
across sessions in canonical `.claude/agents/` (committed at
`cd366629`); Cells C + D were staged via Owner physical ceremony
(plain shell `cp` from non-kernel `audit/round-2/cells/` into
`.claude/agents/`). All 4 must be removed at experiment closure
to restore production-5 baseline. Cleanup script staged at
`.claude/plans/PLAN-060/audit/round-2/OWNER-LAYER-7D-V2-CLEANUP.sh`
(kernel hook `check_arbitration_kernel.py` blocks Claude tool-call
deletion of `.claude/agents/*.md`; plain shell `rm` bypasses the
hook the same way the ceremony `cp` did).

**Token cost (Session 65):** ~95k tokens against the 75-105k
budget (Step 0 sanity ~3k + Step 1 ~10k + Step 2 ~50k + Step 3-7
docs + commit ~30k).

#### Layer 7d-v2 empirical references

- `.claude/plans/PLAN-060/audit/round-2/h4-layer7d-v2-outcome.md` — full empirical record (Session 65)
- `.claude/plans/PLAN-060/audit/round-2/OWNER-LAYER-7D-V2-CLEANUP.sh` — Owner-physical cleanup script (staged at Session 65)
- `/tmp/h4-layer7-fixtures/cell_{a,b,c,d}_v2_001..005.txt` — 20 fixtures verified on disk
- Memory `project_plan_060_layer7_h8_confirmed.md` (Session 65 sections appended)

### Layer 7d-v2 Sonnet companion — 2×2 follow-up (Session 66, 2026-04-27)

**Goal:** test whether `model: claude-opus-4-7` was the actual
discriminator from Session 65's 4-cell sweep, by holding everything
else equal and flipping model to `claude-sonnet-4-6`. If sonnet
cells fail (0/5), model is decisively the discriminator. If sonnet
cells succeed (5/5), model is NOT the discriminator and the H8
hypothesis space narrows to runtime-layer specifics that cannot be
falsified by `.md` file content changes.

**Setup (Session 66 fresh CLI bootstrap):**
- Cell E `code-reviewer-sonnet`: cr-body (full code-reviewer persona +
  ## Adversarial framing + SKILL REFERENCE to code-review-checklist)
  with `model: claude-sonnet-4-6`. Name has `code-reviewer-` substring.
- Cell F `qa-architect-sonnet`: qa-body (full qa-architect persona +
  ## QA Investigation framing + SKILL REFERENCE to testing-strategy)
  with `model: claude-sonnet-4-6`. Name has `qa-architect-` (no
  `code-reviewer-` substring).

Both staged via plain shell `cp` in `OWNER-A-PLUS-B-MEGA-CEREMONY.sh`
(non-canonical staging path bypass; same as Session 64-65 pattern);
`_dispatch.md` regenerated to 9 agents (5 prod + 4 Cell A/B/C/D from
Session 65 staged then cleaned; in Session 66 only E+F added);
CLI relaunched per Session 64 lesson "registry bootstraps at CLI
process start".

**Empirical (10 dispatches, 4 sanity tools-list + 5+5 Bash):**

| Cell | Tools self-report | Bash fixtures on disk | Verdict |
|---|---|---|---|
| E (cr-body, sonnet-4-6, `code-reviewer-` substring) | "Read, Bash" | **5/5** | ✅ |
| F (qa-body, sonnet-4-6, no `code-reviewer-` substring) | "Read, Bash" | **5/5** | ✅ |

Self-report tools-list: both cells reported "Read, Bash" (subset of
declared `[Read, Grep, Glob, Bash]`). 0 fabrication detected;
all 10 Bash dispatches actually ran (`tool_uses: 1`, durations
6.4-12.2s consistent with real shell exec).

**Outcome interpretation (maps to Session 66 prediction matrix
"5/5 + 5/5" row):**

> Model is **NOT** the discriminator. Sonnet cells succeed identically
> to Session 65's opus cells. The H8 hypothesis space narrows to
> runtime-layer specifics that cannot be falsified by `.md` file
> content changes (i.e., model declaration, name pattern, body
> content, SKILL REFERENCE pattern, framing section, tools list).

**Refuted hypothesis stack (cumulative across Session 65 + 66):**
- ❌ Name-substring `code-reviewer` (Session 65 Cell B `senior-engineer`)
- ❌ Body content `cr-body` (Session 65 Cell D `qa-architect-test` qa-body succeeded)
- ❌ Exact name match `code-reviewer` literal (Session 65 4-cell)
- ❌ AND-interaction (any single attribute suffices)
- ❌ **Model `claude-opus-4-7`** (Session 66 Cell E + F sonnet-4-6 succeed)

**Strong remaining candidates (cannot be falsified by .md content):**

1. **Bootstrap-time registration freshness.** Cells A-F are added
   to `.claude/agents/` then CLI restarted; production agents
   `qa-architect`, `performance-engineer`, `security-engineer`,
   `devops` were registered earlier. This is the only attribute
   that has consistently differed across all working cells (Session
   65 A/B/C/D + Session 66 E/F) vs failing production archetypes
   (Session 62-63 N=11+).
2. **Numerical position in `_dispatch.md`** or order-of-registration
   side effect.
3. **Some Anthropic-side caching keyed on the agent persona contents
   that staled** for production archetypes between when they were
   first registered and the current CLI process.

None of these are testable from CEO-side `.md` edits. Falsification
requires either (a) replicating the production-agent registration
timing pattern (impractical), (b) Anthropic upstream investigation,
or (c) accepting the production rail anomaly as observed and
deploying L7c mitigation as default (Session 66 Phase A wire-up
under PLAN-061 / ADR-082 — shipped this session).

**Op implication:** Sonnet 2×2 confirms the L7c mitigation
(`--dispatch=mitigated`, commit `57da31b` Session 63 cont) is the
correct prod posture regardless of model. PLAN-061's flip of
mitigated-from-opt-in-to-default-on (commit batch 1, Session 66)
is empirically grounded — the discriminator is in territory the
framework cannot reach via `.md` edits, and the working dispatch
path (Task `subagent_type=general-purpose` with persona injected)
works for every model + body combination tested across 30
dispatches (Session 65 N=20 opus + Session 66 N=10 sonnet).

**Cleanup ceremony (Owner physical, post-Session 66):**
`OWNER-SONNET-CLEANUP.sh` removes Cells E+F from `.claude/agents/`
and regenerates `_dispatch.md` to the 5-production-agent baseline.

**Token cost (Session 66 Phase B):** ~50k against the ~50k budget
(2 sanity tools-list + 10 Bash dispatches + outcome documentation).

#### Layer 7d-v2 Sonnet references

- `.claude/plans/PLAN-060/audit/round-2/h4-sonnet-companion-outcome.md` — full empirical record (Session 66)
- `.claude/plans/PLAN-060/audit/round-2/OWNER-SONNET-CLEANUP.sh` — Owner-physical cleanup (staged at Session 66)
- `/tmp/h4-layer7-sonnet-fixtures/cell_{e,f}_v2_001..005.txt` — 10 fixtures verified on disk
- ADR-082 — L7c mitigation default-on (Session 66 deliverable, sister doc)
- Memory `project_plan_060_layer7_h8_confirmed.md` (Session 66 sections appended)
