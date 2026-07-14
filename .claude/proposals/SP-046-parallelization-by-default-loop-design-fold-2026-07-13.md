---
id: SP-046
skill_slug: parallelization-by-default
archetype: none   # core-skill fold, CEO-proposed — SP-018/SP-042 precedent (no owning archetype)
proposed_at: 2026-07-13T23:08:00Z
source_lessons:
  - plan-157-w1-fold-loop-design-check
scan_injection_pass: true
diff_size_added: 61
diff_size_removed: 1
sha256_of_diff: 358cbd17c453d43c7c916f51f3a2b97f75ac6b93e92abebec2b1fb7376ee58d0
sha256_of_staged: b7fccb0cd8751ace35d54c0415042ee496f80d630b789abb3e498bfbd8b0181d
claims_declared: false
status: proposed
shadow_mode: false
soak_waiver: owner-ratified-at-signing   # PLAN-157 OQ4 (Owner tie-break S270) via SP-042/S264-OQ4 precedent
proposal_type: fold-distill-append
patch_source: inline diff fence (below)
---

# SP-046 — fold `loop-design-check` → `core/parallelization-by-default` (PLAN-157 W1, applies AFTER SP-045)

**Target:** `.claude/skills/core/parallelization-by-default/SKILL.md`
**Base (load-bearing):** this diff is computed against SP-045's staged
result — base sha256
`280470ba6f887663c7861b27819496d3f197f7ae86e3b113d37f8fa6fd3a4a78`
(= SP-045's `sha256_of_staged`). Apply SP-045 first; hunk offsets
assume it.
**Source:** the agents-meta squad's `loop-design-check` skill (pre-fold
source pin sha256
`a7114359a8a1aada5b14e4291c0231ecbe26fce4b0323344dbfcb6160eb9957c`),
sunset in the same W1 ceremony per OQ2 (git-history-only deletion +
pointer in the plan).
**Kind:** distilled append + one-line declared-budget bump. One target
file = one ceremony vehicle for both agents-meta sources (SP-045 +
SP-046).

## Rationale

`loop-design-check` names `parallelization-by-default` as its sibling
mechanism layer in its own text; both agents-meta skills cross-reference
each other. Co-locating them in the one CEO-primitive core skill
preserves that link with no domain path (tier-check-safe). The
"judgment layer vs mechanism layer" distinction is kept as the section
frame. Runner-up considered: `core/state-machines-and-invariants`
(invariants, fail-fast, hysteresis/anti-flap ≈ damping) — defensible,
but it splits the agents-meta pair and its audience is the Real-Time
Systems archetype, not the CEO.

**What survives (the distill, ~917 est tokens):** the two-level
feedback red-line premise (compressed); the 4-condition build gate
(any miss = veto); the five-point machine-decidable-goal framework
(including reconciliation-over-assertion); the loop-type row set
(servo / regulator / regulator-with-exit, one line each); the
plan/build/judge three iron rules (independent judge = the pair-rail
principle); damping; the 5-failure-mode review table (compressed
rows); and the 3 red lines (human at the last switch; responsibility
does not transfer; self-improving ⇒ stricter review).

**What is dropped, and why:** the green-keeper worked example (the
review table now carries its lessons directly); doc-driven-dispatch
skeleton detail and staged-landing prose (mechanism-layer process the
host harness + plan lifecycle already document); the lineage note,
one-line close, and changelog + import attestation (bookkeeping).

## Budget evidence (repo-canonical chars/4 estimate)

- Distilled section: 3,670 B ≈ 917 tokens (scout estimated 700-800;
  the measured distill runs ~120 tokens over, kept for the review
  table's completeness). Post-both-folds body est ≈ 3,393 tokens
  (1,822 + 654 + 917); post-fold file 14,549 B ≈ 3,637 tokens
  full-file vs the 30,000 per-skill schema ceiling — 26,363 headroom.
- Declared `context_budget_tokens` bumped 2500 → 3500 (not the scout's
  ~3200: this skill's declared value is body-covering today
  (2500 ≥ 1822), and 3200 would fall below the MEASURED post-fold body
  of ≈3,393 — 3500 keeps the declared field conservative). Profile-sum
  delta +1000 declared vs 19,800 live headroom; target not in the
  current active set.
- Tier-boundary safety: appended prose carries no
  `domains/<x>/skills/<y>` or `../../domains/` reference (asserted at
  build time with the `_DOMAIN_REF_RE` pattern); no core file added —
  `check-tier-boundaries.py` stays 92-files clean.

## Soak waiver

WAIVED per the Owner's OQ4 ratification (S270 structured tie-break,
SP-042/S264-OQ4 precedent): content in-tree and import-attested since
2026-07-08; zero new doctrine. Owner ratifies by detach-signing this
proposal. `sha256_of_staged` pins the exact post-apply file (after
BOTH SP-045 and SP-046).

## Apply route

The appended-section hunk is pipeline-expressible (append-only); the
one-line `context_budget_tokens` bump is not (pipeline
`_apply_unified_diff` is append-only by design and cannot express a
removal — SP-042). Applied Owner-shell inside the W1 sentinel ceremony,
immediately after SP-045, with the staged-file hash asserted before
commit. Source-dir sunset rides the same ceremony.

## Diff

```diff
--- a/.claude/skills/core/parallelization-by-default/SKILL.md
+++ b/.claude/skills/core/parallelization-by-default/SKILL.md
@@ -5,7 +5,7 @@
 domain: core
 priority: 2
 risk_class: low
-context_budget_tokens: 2500
+context_budget_tokens: 3500
 inactive_but_retained: false
 repo_profile_binding:
   frontend:
@@ -220,3 +220,63 @@
 docs when a shared skill or status artifact is the real deliverable; multiple
 agents with no ownership, merge gate, or conflict policy; private data
 leaking into committed artifacts.
+
+## Loop Design + Review (judgment layer) — folded from `loop-design-check` (PLAN-157 W1)
+
+Dispatch and harness are the mechanism layer; this is the judgment layer —
+whether a repeating goal-seeking loop should exist, whether its goal is
+machine-decidable, and whether it can run away (distilled from the sunset
+agents-meta squad's `loop-design-check` skill; full text in git history).
+
+**Two-level feedback red line.** Execution feedback — measure distance from
+the literal goal and grind it to zero — belongs to the machine. Judgment
+feedback — whether the goal itself is right, whether it should change,
+whether to stop — belongs to the human/Owner: in this framework the
+Owner-flipped plan lifecycle, the canonical-guard sentinel, the pair-rail,
+and escalate-to-Owner. A loop that bypasses those has removed its own
+top-level feedback.
+
+**Build gate (4 conditions; any miss = veto):** (1) the task repeats weekly
+or more often; (2) verification can be automated; (3) the token budget can
+absorb the iteration; (4) the agent has tools that actually run the work and
+observe the result. Miss any one → do not build a loop.
+
+**Machine-decidable goal (five points; the loop lives or dies here):**
+(1) done-criterion machine-verifiable — one command returns a verdict;
+(2) boundary conditions defined alongside it — "what it must NOT do" is the
+Goodhart antibody; (3) failure fallback — retry cap N, then escalate to a
+human; (4) the goal is layered so a partial result is legible;
+(5) prefer reconciliation over assertion — anchor to an external fact
+(golden sample, upstream total, tie-out): "all tests pass" can be gamed;
+"diff vs the reference < 0.01" cannot.
+
+**Loop types:** clear "done" test → servo (stops on reaching the goal); no
+endpoint, keep maintaining a state → regulator (never stops; a dead-band
+suppresses noise); periodic sampling with a stop condition → regulator with
+an exit; "must happen on time" → wrap either in the scheduler.
+
+**Plan/build/judge iron rules:** the judge is independent — never the same
+agent as Build (the pair-rail principle: the author is never the sole
+reviewer); the judge is deterministic (pytest, a reconciliation diff, a real
+diff — never "looks right"); Build may not weaken the acceptance conditions
+to pass; three failed retries → escalate to a human. Add damping — a retry
+cap, a hard stop, and a human at the last switch; negative feedback with no
+damping oscillates (the loop spins in place, burning tokens).
+
+**Review checklist (a hit on any row = send the loop back):**
+
+| # | Failure mode | Antibody |
+|---|---|---|
+| 1 | Goal is a correct-sounding platitude → spins, burns tokens | replace with a decidable result condition |
+| 2 | "Verification" is "looks ok" / the judge is the defendant | reconcile + exit-code rules + independent judge |
+| 3 | Gates only on "all tests pass" → agent deletes the tests | done-criterion + boundary together |
+| 4 | Counts on the agent asking mid-run → it will not | front-load every clarification before launch |
+| 5 | Bloated context + stale memory → the faster it loops, the more it errs | layered memory + periodic hygiene sweep |
+
+**Three red lines — violate any and the loop may not go automatic:** the
+"done" cell is flipped by a human (the loop is the worker, not the acceptance
+officer); responsibility does not transfer (anything whose failure you cannot
+afford must not receive the loop's authority automatically); the more
+self-improving the loop, the STRICTER the human review — the gate sits before
+the action, exactly as kernel/self-modification routes through the sentinel +
+Owner, never through the loop itself.
```

## Verification

- Precondition: `sha256(SKILL.md) == 280470ba...a78` (SP-045 applied).
- `sha256(SKILL.md post-apply) == sha256_of_staged` (asserted by the
  W1 landing script before commit).
- `python3 .claude/scripts/check-tier-boundaries.py` → clean, exit 0
  (92 files scanned; no core file added).
- `python3 .claude/scripts/smart-loading-resolver.py resolve --json` →
  `context_total_tokens` ≤ 30000 (10,200 today).
- `python3 .claude/scripts/lint-skills.py` → zero ERROR lines.
- Full PLAN-157 per-wave Check set rides the W1 ceremony commit.
