# PLAN-161 W2 pack — codex pair-rail round 2 (2026-07-27)

Input: r1 dispositions + fresh HEAD->staged diff (post r1 fixes), redacted via ADR-114.

## Verdict

REJECT

1. F2 [P1] .claude/scripts/ceo-boot.py:1753: `pair_rail_codex_unavailable` counts as a terminal despite being emitted by `codex_invoke.py`, which never emits the new expected denominator. An unrelated outage in the same session can therefore consume a terminal count and mask a missing `pair_rail_case`, defeating the promised per-session deficit escalation.

2. F11 [P1] scripts/upgrade.sh:1147: For manifest-less adopters, the legacy branch deletes the entire destination tree before copying and pruning excluded source paths. Existing excluded-tree files—including unauthorized adopter content—are consequently deleted without `--purge-misinstalled`, before the preview/hash gate runs. This violates the opt-in-only purge contract.

3. F12 [P1] .claude/workflows/council-audit.js:248: Removing `ARTIFACT_KEEP_DIR` did not close the artifact-path redirect class. `mktemp -d -t` honors inherited `TMPDIR`; if it points inside the repo, the lane writes there and the stale sweep at line 250 recursively deletes matching directories there, contradicting read-only containment and “never the repo tree.”

4. F13 [P2] .claude/workflows/council-audit.js:328: The attestation gate identifies Grok by `REQUESTED_VENDORS[i]` but returns the original model-written lane object. Downstream attribution still trusts `l.vendor` at line 354, allowing a lane to impersonate another vendor and corrupt availability, finding attribution, disagreements, audit instructions, and the attestation map.

5. F14 [P2] .github/workflows/validate.yml:1244: The canonical workflow and ADR-163 still claim a 9-case proof, while `proof-retry-matrix.sh` now executes and reports 11 cases after the F8 teeth checks. The round-one fix introduced documentation/proof-count drift.

## CEO triage (S279)

r1 dispositions VERIFIED by codex r2 (no re-raise of F1/F5-F10 substance;
F3/F4 accepted as fixed but surfaced residual redirect/impersonation
classes). 5 findings, all ACCEPTED:
- F2 [P1] re-scoped: codex_unavailable is a DIFFERENT rail's terminal; my
  r1 credit masks a missing pair_rail_case. Fix: terminal = {pair_rail_case}
  ONLY (same producer as review-expected); a genuine in-review outage
  yellows the row (correct — the review did not complete; outage stays
  visible via codex_outage_minutes).
- F11 [P1] NEW (r1-introduced blast-radius surfaced): legacy no-manifest
  cp -R branch wipes the whole dst subtree BEFORE prune → excluded-tree
  content deleted without --purge. Fix: the wholesale delete SKIPS excluded
  paths (invariant: legacy upgrade neither adds nor removes excluded trees).
- F12 [P1] NEW (r1 fix incomplete): mktemp -d -t honors TMPDIR → repo-tree
  redirect + sweep-in-repo still open. Fix: explicit /tmp base (0700
  mkdtemp dir), sweep the same fixed base, ignore TMPDIR.
- F13 [P2]: demotion keyed REQUESTED_VENDORS[i] but returned the
  model-written lane → downstream l.vendor impersonation. Fix: overwrite
  each lane's vendor to its canonical requested position.
- F14 [P2]: r1 F8 grew the proof to 11 cases; validate.yml comment +
  ADR-163 still say 9. Fix: count-free phrasing (or 11).
