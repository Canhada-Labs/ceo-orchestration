---
round: 1
archetype: VP Engineering
skill: architecture-decisions
agent_persona: VP Engineering
generated_at: 2026-07-13T00:00:00Z
---

## Verdict

ADJUST

The thesis is right and the ceremony-batching instinct is correct, but
two of the seven fixes are aimed at the wrong surface: **F7 is
misdiagnosed** (the code it targets already does the right thing —
`git blame` proof below) and **F5's fix closes only one of three
divergences**. Both must be re-scoped before `draft → reviewed`, or W4's
own acceptance criterion ("scoped prompts", 3-lane parity) will fail
again for the same reason it failed at S270.

## Summary (≤ 3 bullets)

- **What it does:** land 7 mechanical fixes surfaced by the first live
  `/council` run (S270) via ONE sentinel ceremony (W1–W3), then prove the
  egress path with a full-quorum live-fire (W4). Every finding carries a
  file:line anchor.
- **Strong:** the batching call is architecturally correct — these are
  guard-consistency fixes that should land as one coherent story, not six
  half-guarded intermediate HEADs on `main`; reversibility is HIGH
  (single-commit revert); no new dependency, no new system boundary.
- **Weak:** F7 fixes code that is already correct (the real gap is the
  invocation layer); F5's "align the predicate" leaves the deeper
  per-commit-vs-working-tree path-source mismatch untouched; and the
  ceremony mechanics under-state the `_KERNEL_PATHS` override coupling for
  F3 and the script-vs-module import crux for F1.

## Risks

Ordered, most severe first.

- **R-VP1 — F7 fix targets already-correct code; the real bug is
  unfixed.** Severity: HIGH.
  `git blame .claude/workflows/council-audit.js` shows `SCOPE` was read
  from `args.scope` (L54) and threaded into the lane brief (L112) and the
  report header (L311) in the file's **first and only** commit
  (`61220ee`, 2026-07-13 08:48). There was never a later "fix" — the
  workflow has always propagated scope. So at S270 the scope was lost at
  the **invocation layer** (`/council` → `Workflow({args:{scope}})` in
  `.claude/commands/council.md:52`), not inside council-audit.js. The
  proposed F7 fix ("propagate args.scope into lane prompts + report
  header; fixture asserts round-trip") therefore modifies code that
  already round-trips scope, and its fixture would go GREEN without
  changing any behavior — the happy-path-of-already-working-code trap.
  Mitigation: re-scope F7 to the invocation surface — assert that the
  operator/command threads the Owner-authorized `<scope>` into
  `args.scope` (integration assertion on the command→workflow boundary),
  not a unit round-trip inside the workflow. Until this is re-diagnosed,
  W4's "scoped prompts" acceptance criterion is not covered.

- **R-VP2 — F5's fix closes 1 of 3 divergences; path (b) stays broken.**
  Severity: HIGH. The recorder (`check_codex_stop_review.py`) fingerprints
  the **working-tree** change-set at Stop time —
  `git diff --name-only HEAD` + `ls-files --others` (L301,L303) — filtered
  by the **precise** imported `_is_canonical` predicate (L264–277,L316,
  L472). The gate (`templates/grok/pre-push-review-gate.sh`) fingerprints
  **per-commit** paths at push time — `git diff-tree ... -r "$sha"` (L119)
  — filtered by a **coarse first-segment** shell classifier (L69–76) and
  hashed once **per commit** (L167). The proposal only addresses the
  predicate divergence (coarse vs precise). It ignores the two structural
  ones: (a) working-tree-aggregate (pre-commit) vs per-commit (post-
  commit) path-source, and (b) after commit, the recorder's `diff HEAD`
  set is empty — the fingerprint it wrote only matches if the operator
  committed the entire working-tree set as exactly ONE commit with no
  amend/split. Multi-commit push, staged subset, or amend → guaranteed
  mismatch → path (b) is dead regardless of predicate alignment.
  Mitigation: either (i) reconcile the path-SOURCE too (both hash the same
  committed diff over the same predicate — hard, because the recorder runs
  pre-commit and has no commit yet), or (ii) accept the architecture's own
  verdict (comments L37–38: "on a fresh clone only the (a) trailer
  survives; CI checks (a) only") and formally DEMOTE path (b) to a
  best-effort local convenience, making (a) the trailer the load-bearing
  mechanism. Do not ship a "parity test" that only pins the predicate — it
  would certify a parity that does not hold end-to-end.

- **R-VP3 — F3 edits a `_KERNEL_PATHS` entry; single-ceremony will HALT
  mid-apply without the kernel override.** Severity: HIGH. The guard list
  F3 broadens lives inside `_KERNEL_PATHS`
  (`check_canonical_edit.py:307–321`); the inline contract (L317–319)
  requires `CEO_KERNEL_OVERRIDE=PLAN-156-COUNCIL-GUARD-EXTENSION` AND
  `CEO_KERNEL_OVERRIDE_ACK=I-ACCEPT` **in addition to** the sentinel to
  extend it. Widening `.claude/workflows/council-audit.js` →
  `.claude/workflows/*.js` is coverage-extension. If the one-ceremony
  script does not pre-declare that override for the F3 hunk, the atomic
  land aborts after the sign step — the worst place to fail. Mitigation:
  the ceremony script MUST export the kernel-override env for the F3 edit
  (or split F3 into its own override-gated step), and the sentinel Scope
  MUST enumerate `check_canonical_edit.py` explicitly.

- **R-VP4 — F1's Check runs the module AS A SCRIPT; argparse alone does
  not make the relative import work.** Severity: MEDIUM. council-audit.js
  invokes the redactor as `python3 .claude/hooks/_lib/codex_egress_redact.py
  --outgoing` (L145) — i.e. run-as-file, which is exactly the mode where
  `from . import secret_patterns` (L47) raises `ImportError: attempted
  relative import with no known parent package`. Adding an argparse
  `__main__` block does NOT fix this unless the import is made script-safe
  (try relative, `except ImportError` → `sys.path.insert(_lib_dir)` +
  absolute import). The Wave 1 Check
  (`printf 'x' | python3 …codex_egress_redact.py --outgoing`) is the right
  gate, but it must be run as a SUBPROCESS from repo root (the exact
  council-audit.js invocation), never via `python3 -m` — `-m` would mask
  the very failure the finding is about. Mitigation: make F1's acceptance
  the literal L145 command string; add the import-fallback shim, not just
  argparse.

- **R-VP5 — atomic multi-surface commit couples 7 independent fixes to
  one Validate result.** Severity: MEDIUM. Landing F1–F6 as one commit
  touching `_KERNEL_PATHS` + a workflow + three hooks + a template means a
  red Validate on any single file's test reverts ALL seven fixes and
  forces a full re-ceremony (re-sign included). Mitigation: run every
  per-wave Check (W1+W2+W3) as a PRE-FLIGHT gate locally BEFORE the GPG
  sign+commit step, so a failing check aborts cheaply before the
  expensive, hard-to-redo signing. This keeps the (correct) atomic land
  while removing the "sign, then discover a red test" failure mode. See
  R-VP8 for why I still endorse batching.

## Must-fix (blocking)

1. **Re-diagnose F7 to the invocation layer** (R-VP1). The plan's Scope
   table row F7 and Wave 2 bullet 2 must move from "propagate args.scope
   inside council-audit.js" to "assert the command→workflow boundary
   threads the Owner-authorized scope into `args.scope`." A round-trip
   fixture inside the workflow is not acceptable evidence — it passes on
   code that already works. If, after re-check, the invocation layer is
   ALSO already correct, then F7 collapses to an operator-error at S270
   and should be closed as NOT-A-CODE-DEFECT with a W4 assertion, not a
   code change.

2. **F5: pick a coherent target for the WHOLE mechanism, not just the
   predicate** (R-VP2). Either reconcile path-source + predicate on both
   sides, or demote path (b) and make the (a) trailer load-bearing. The
   "parity test" must exercise the end-to-end record→gate match on a
   realistic commit shape (commit the working set, then run the gate), not
   a same-input predicate equality. Answering the proposal's OQ directly:
   align the GATE up to the precise predicate (over-triggering on
   `.claude/plans/*.md` is what trains operators to `--no-verify`), but
   only AFTER the path-source mismatch is resolved or (b) is demoted —
   predicate alignment alone is a false fix.

3. **Ceremony script must pre-declare the `_KERNEL_PATHS` override for F3
   and enumerate every touched path in the sentinel Scope** (R-VP3).
   Including the new test/fixture files (`_lib/tests/…`,
   `scripts/tests/test-council-fixture.mjs`), or the atomic land blocks on
   `touched − scope ≠ ∅`.

4. **F1 acceptance must be the literal council-audit.js invocation, and
   the import must be made script-safe** (R-VP4), not merely wrapped in
   argparse.

## Nice-to-have (advisory)

1. **F6: prefer adjacency-glob tightening over a shell JSON parser.** The
   vocab-rewrite step already normalizes any deny to `"decision": "deny"`
   with fixed spacing (`_python-hook.sh:447–448`). So the exit-2 case-glob
   (L464) can match the exact normalized adjacent form
   `*'"decision": "deny"'*` / `*'"permissionDecision": "deny"'*` instead of
   the loose `*'"decision"'*'"deny"'*`. That removes the false-positive
   (an allow whose reason string quotes "deny") with zero new parser code
   — answering the OQ: full field-parsing in shell is over-engineering
   that risks its own bugs; the emitter is the trusted framework hook, so
   there is no new bypass from adjacency-matching.
2. **F2: for an ADVISORY instrument, "verify_failed blocks CLEAN → forces
   DEGRADED + names the failure in the report" is sufficient; no exit-code
   change needed** (answering the OQ). There is no CI gate consuming a
   council exit code — the verdict IS the product. The requirement is
   visibility: the report's Verdict section must state DEGRADED and the
   reason (refuter null/error), never a silent `unverifiable` drop
   (council-audit.js:267,274).
3. **F4: parse `trusted_folders.toml` as TOML array entries, not a
   substring** (`_grok_harness.sh:333`). A shell-native option that avoids
   a real TOML parser: anchor the match to a full quoted array element
   (`grep -Eq "\"$(printf '%s' "$target" | sed 's/[.[]/\\&/g')\""`) and
   skip commented lines, rather than `grep -qF "$target"`.

## Unseen by the original plan

1. **The F5 mechanism may be structurally unsound, not merely
   mis-aligned.** A pre-commit working-tree recorder and a post-commit
   per-commit gate cannot produce equal fingerprints across realistic
   commit shapes (R-VP2). The plan treats F5 as a one-line predicate
   swap; it is actually a "is path (b) reachable at all?" question. This
   deserves a two-line ADR note (reversibility of the decision to keep vs
   demote the sidecar path), since it changes what the grok push-gate's
   contract promises.
2. **F7's misdiagnosis is load-bearing for W4.** Because W4's acceptance
   includes "scoped prompts," a code-only F7 fix leaves W4 to fail on the
   same symptom. The two findings are coupled; the plan lists them as
   independent.
3. **F1's failure is why the S270 codex lane "died pre-send."** The plan's
   Context (L27, L39) attributes it to budget/timeout + binary contention,
   with F1 as a parallel cause. But a non-executable mandatory redaction
   STEP 1 (council-audit.js:145–147) means the lane orchestrator SHOULD
   have returned `status:"unavailable", reason:"egress redactor
   unavailable"` — fail-loud, by design (L146). If instead it "died," the
   fail-loud path itself may not have triggered. Worth confirming in W4
   that a missing/broken redactor yields `unavailable`, not a crash — that
   is the actual invariant the council rests on.
4. **No finding covers the guard on `.claude/commands/council.md`
   (L321).** F3 globs `.claude/workflows/*.js` but leaves the command
   trigger as an exact path. If a sibling command can also invoke the
   egress workflow, the same class-vs-instance gap F3 fixes for workflows
   reopens for commands. Low severity, but it is the symmetric case the
   plan's own reasoning implies.

## What I would NOT change

- **The single-ceremony batching of W1–W3 is the right call** (R-VP8
  rationale). These are guard-CONSISTENCY fixes; landing them as one
  atomic commit means `main` never sits in a half-guarded state (e.g. F3
  glob applied but F6 exit-map not), each canonical file's per-file
  pair-rail verdict rides one sentinel, and the revert is a single commit.
  Six separate ceremonies would multiply GPG/pair-rail overhead for no
  safety gain. Keep it — with the R-VP3/R-VP5 preflight-and-scope
  guardrails.
- **Sequencing W4 (live-fire) last, Owner-gated on local grok + no
  concurrent codex, is correct.** Do not try to prove egress before the
  redactor CLI (W1) and the scope threading (re-scoped F7) exist.
- **Keeping the fixes stdlib-only / no-new-dependency** — every fix is a
  behavioral change to an existing surface. No tool-evaluation ADR is
  triggered; do not introduce jq/a TOML lib to "do F4/F6 properly."
- **The fail-loud-on-unavailable posture of the council itself** — F2
  hardens it; nothing in the plan weakens it. Preserve the mechanical
  verdict override (council-audit.js:328–336) as the last word over the
  synthesizer's wording.
