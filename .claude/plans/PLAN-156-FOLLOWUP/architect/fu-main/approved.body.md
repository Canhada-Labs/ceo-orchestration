# FU-MAIN — PLAN-156-FOLLOWUP council live-fire fixes F1+F2+F7+F6+F4

Lands five of the seven S270 council live-fire findings (run
`wf_1adfc111-a79`, 1-lane degraded; debate round-1 consensus C1/C4/C5-sem/
C6/C7 folded into the plan revision). F3+F5 land separately under
FU-KERNEL (own segment — independent rollback of the widest-blast-radius
change, consensus C3).

- **F1 — egress redactor CLI (`codex_egress_redact.py`)**: the mandated
  redaction command (`council-audit.js:145`) was structurally
  non-executable (no CLI entrypoint; relative import fails run-as-file),
  making live council 1-lane forever. Fix: script-safe import shim +
  `--outgoing` CLI with the C4 VETO contract — on ANY internal error exit
  NONZERO and emit NOTHING to stdout (never echo input). Library
  `redact()` single-pass / never-raise / never-echo contract untouched.
- **F2 — verify fail-loud (`council-audit.js`)**: `verify_failed`
  (refuter crash/omission — synthesized default) SPLIT from explicit
  `unverifiable` (refuter ran and judged); CLEAN ⇔ lanes≥3 ∧ confirmed==0
  ∧ verify_failed==0; `verify_failed` count surfaced prominently in the
  report. No exit-code change (advisory instrument). Kills the S-class
  vacuous CLEAN (refuter-null → false-green).
- **F7 — re-anchored to the invocation layer (`council.md`)**: the
  workflow already threads `args.scope` (consensus C1, git-blame proof);
  the S270 scope=`.` bug is the `/council` → `Workflow({args:{scope}})`
  boundary. The command now pins scope propagation; the lane brief folds
  redact→send into a single `redactor | vendor` pipe under
  `set -o pipefail` (a skipped redaction cannot produce a sendable
  prompt — C4/Critic-B).
- **F6 — grok shim exit-2 map (`_python-hook.sh`)**: order-sensitive
  whole-stdout substring match replaced by a structural TOP-LEVEL JSON
  parse via the already-resolved `$FOUND_PY`. Dual fail semantics (C5
  VETO direction): parse OK → field governs; parse failure WITH a deny
  token present → exit 2 (fail-CLOSED); parse failure with no deny token
  → hook rc (infrastructure fail-open preserved). Regressions both
  directions (allow-with-quoted-"deny" → 0; decoy-allow-before-real-deny
  → 2).
- **F4 — grok trust probe (`_grok_harness.sh`)**: substring `grep -qF`
  over `trusted_folders.toml` false-ARMED on prefix siblings and
  commented entries. Fix: exact-entry line-wise parse against the REAL
  schema captured from the pinned grok binary (0.2.93,
  characterize-then-pin, C6), realpath-normalized both sides; ANY parse
  ambiguity → NOT-ARMED (never over-claim). Declined
  (`trusted = false`) entries never arm.

Proof (re-run by the ceremony preflight in staged mode BEFORE this
sentinel is signed, and again post-apply in canonical mode): F1 smoke
16/16 (`_lib` suite + 3.9-3.12 matrix mirror, incl. the LITERAL
`council-audit.js:145` invocation as a subprocess from repo root +
induced-failure path exit≠0/empty-stdout); council verify semantics
20/20 (Python CI mirror) + 21/21 `.mjs` local fixture; hooks named set
green; shellcheck -S warning clean on the touched shells. Staged copies
basepin-verified against canonical sha256 at apply time (abort on
drift).

<!-- BEGIN SIGNED SCOPE -->
Approved-By: @Canhada-Labs AE9B236FDAF0462874060C6BCFCFACF00335DC74
Anchor-SHA: __ANCHOR_SHA__
Plans: PLAN-156-FOLLOWUP
Kernel-Override: (none — no _KERNEL_PATHS in this scope)
Scope:
  - .claude/hooks/_lib/codex_egress_redact.py
  - .claude/hooks/_lib/tests/test_redactor_cli.py
  - .claude/workflows/council-audit.js
  - .claude/commands/council.md
  - .claude/hooks/_python-hook.sh
  - scripts/_grok_harness.sh
  - scripts/tests/test-council-fixture.mjs
  - .claude/scripts/tests/test_redactor_cli_matrix.py
  - .claude/scripts/tests/test_council_verify_semantics.py
  - .claude/scripts/tests/test_grok_trust_probe.py
  - .claude/hooks/tests/test_python_hook_exit_map.py
<!-- END SIGNED SCOPE -->
