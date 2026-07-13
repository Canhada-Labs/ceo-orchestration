---
plan: PLAN-156
round: 1
created_at: 2026-07-10
---

# PLAN-156 round-1 proposal — Multi-Harness Expansion (Grok + GPT-5.6 + Council)

Full plan: `.claude/plans/PLAN-156-grok-harness-56-refresh-council.md`

## Thesis

PLAN-155's adapter seam makes a third harness a bounded increment. Grok
Build (official xAI CLI) has a blocking PreToolUse hook with a
Claude-shaped JSON envelope — enforcement parity where it matters, with
three Grok-specific semantics that concentrate all the new risk. The
GPT-5.6 refresh is the existing ADR-111 pin ceremony pointed at the codex
lane (empirically REQUIRED: 0.139.0 cannot invoke gpt-5.6-sol/luna — S266
probe). The Cross-Vendor Audit Council converts three-vendor access into
an advisory audit instrument with vendor-attributed verdicts.

## Scope (7 waves)

- **W0** prep: Owner installs grok CLI + upgrades codex; record grok wire
  fixtures (resolve 5 research lacunae empirically); pins + substrate
  watch items; sentinels SENT-GK-{A..E} + ADR-162 drafts.
- **W1** codex 5.6 refresh (independent): pin-update ceremony (ADR-111,
  locked-corpus catch_rate), re-certify the PLAN-155 capability matrix on
  the new CLI (fixtures re-record + drift detector + positive-control
  replays), 5.6 models documented in lanes.
- **W2** `_lib/adapters/grok.py` + `KNOWN_ADAPTERS += "grok"`
  (kernel-class, sentinel + override). Linchpin: **exit-2 discipline** —
  on Grok, any exit ≠ 2 is fail-OPEN, so fail-CLOSED matchers must emit
  structured deny + exit 2 even on INPUT-parse crash (adapter-level wrap,
  Grok-only).
- **W3** `templates/grok/` native hooks JSON + config + trust-flow doc;
  kill-switch guard-list extension (`.grok/hooks/**`, `.grok/config.toml`).
- **W4** audit actions grok_tool_recorded/grok_turn_ended (316→318) +
  installer `--harness grok` (mirror `_codex_harness.sh`) + matrix tests.
- **W5** inverted pair-rail: Stop is NON-blocking on Grok ⇒ Stop review
  ADVISORY, git pre-push gate is the teeth; validate.yml riders.
- **W6** Council: `council-audit.js` workflow + `/council` command —
  audit-fanout shape × 3 vendor lanes (Claude agents; `codex exec
  --sandbox read-only`; `grok -p` headless contained by a
  deny-all-writes CEO hooks profile). Fail-loud lanes (`unavailable`,
  never silent substitution), vendor-attributed verdicts, cross-vendor
  disagreement escalated as first-class signal. Advisory-only.
- **W7** live-fire positive controls (canonical-deny under grok, exit-2
  crash proof, Stop-advisory demo, council degraded-lane run) + docs +
  capability matrix + ADR-162 + counts closeout.

## Key decisions already taken (challenge them)

1. Native `.grok/hooks/` over the undocumented `.claude/settings.json`
   legacy-compat path (OQ1).
2. Exact-version grok pin + weekly substrate watch — daily 0.x releases
   (OQ2).
3. Council containment for the grok lane = our own deny-all-writes hooks
   profile (dogfood-as-sandbox) until a native read-only mode is found.
4. Stop-advisory honesty: no attempt to fake a blocking Stop on Grok;
   push-time is the enforcement point (PLAN-155 inverted-rail precedent).
5. Council is ADVISORY evidence with vendor attribution — never a truth
   gate (verification cascade unchanged).

## Open questions (Owner ratifies at W0 signing)

OQ1 hooks surface; OQ2 pin policy; OQ3 council lane models; OQ4 codex
target version + catch_rate run; OQ5 SuperGrok subscription; OQ6 council
per-lane budget ceilings.

## Known risks to probe in critique

- Grok 0.x volatility vs our pin discipline (is weekly watch enough?).
- Exit-2 wrapper as a NEW security-regression class (future hooks that
  forget it) — should the wrapper live in the shared shim so it's
  impossible to forget?
- Council lanes invoke external LLMs on repo content — egress/injection
  surface, cost ceilings, and the auth/subscription coupling.
- Legacy `.claude/settings.json` compat on Grok could DOUBLE-fire hooks
  if we also ship native `.grok/hooks/` — needs W0 empirical check.
- Matcher tool-name mismatch (native vs mapped names in stdin) could
  silently no-op guards — W0 fixture question (a) is load-bearing.
