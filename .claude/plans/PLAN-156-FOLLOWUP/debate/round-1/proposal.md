---
plan: PLAN-156-FOLLOWUP
round: 1
created_at: 2026-07-13
---

# PLAN-156-FOLLOWUP — Round 1 proposal

> Full plan: `.claude/plans/PLAN-156-FOLLOWUP-council-livefire-findings.md`
> Parent: PLAN-156 (council instrument). OQ1/OQ2 already Owner-ratified
> (S270): guard glob IN, planted-fixture redaction proof IN.

## Thesis

The first live `/council` run (S270) proved the fixture suite validated
parse/fail-loud logic but NOT the live egress path: the run degraded to
1-lane (grok fail-loud correct; codex died pre-send), and the Claude lane
surfaced 7 adversarially-verified findings. All 7 are mechanical defects
with exact file:line anchors. Fix all 7 + regression tests, land Waves
1-3 via ONE sentinel ceremony (touch set is canonical-heavy), then prove
with a full-quorum (3-lane) live-fire re-run on the original scope
(`.claude/hooks/`) including a planted-fixture redaction proof.

## Scope (the 7 findings)

| # | Surface | Fix |
|---|---|---|
| F1 | `_lib/codex_egress_redact.py` | Add `__main__`/argparse CLI entrypoint (absolute-import safe); library API unchanged; smoke test in `_lib/tests/` |
| F2 | `council-audit.js:265-277,328-330` | Refuter error/null → group `verify_failed`, surfaced + blocks CLEAN; never silent `unverifiable` drop; fixture case |
| F3 | `check_canonical_edit.py:320-321` | Guard `.claude/workflows/*.js` as a CLASS (glob), not exact paths; sibling-write regression test |
| F4 | `_grok_harness.sh:333,348` | Trust probe parses exact path entries (no substring/commented false-ARMED); prefix-sibling fixture |
| F5 | `pre-push-review-gate.sh` vs `check_codex_stop_review.py:472` | Fingerprint parity: both hash the precise `_is_canonical` path set; parity test |
| F6 | `_python-hook.sh:463-464` | Exit-2 map parses the decision FIELD, not whole-stdout substring; allow-payload-with-quoted-deny regression |
| F7 | `council-audit.js` | Propagate `args.scope` into lane prompts + report header; fixture asserts round-trip |

## Wave shape

- W0: this debate → Owner ratifies draft→reviewed.
- W1 (F1) + W2 (F2+F7) + W3 (F3+F4+F5+F6): ALL canonical or
  ceremony-riding → stage + ONE sentinel ceremony (land-plan156.sh
  pattern), per-file pair-rail verdicts.
- W4: full-quorum live-fire (Owner installs `~/.grok/sandbox.toml` from
  template; no concurrent codex processes; planted fake-secret fixture
  proves redaction; quorum 3-lane + per-lane `council_lane_invoked`).

## Decisions already ratified (NOT up for re-debate)

- OQ1: `.claude/workflows/*.js` becomes ceremony-gated (guard glob) —
  ratified S270; cost accepted (egress-bearing surface).
- OQ2: planted-fixture redaction proof in W4 — ratified S270.

## Open questions for critics

- Single-ceremony batching of W1-3: any ordering/rollback risk a split
  ceremony would avoid?
- F2 fail-loud semantics: is `verify_failed` blocking CLEAN sufficient,
  or must it also fail the run's exit code?
- F5 parity: align gate to recorder's precise set, or recorder to
  gate's coarse set — which direction is correct for the threat model?
- F6: does field-parsing introduce a new bypass (crafted first
  "decision" key)?
- Anything the 7 findings MISS that the live-fire evidence implies?

## Budget / risk

90-140k tokens, 1 session, context_risk medium, no external waits
(W4 needs Owner-local grok CLI + codex budget).
