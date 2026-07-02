# ADR-157: Sonnet 5 enters the MODEL_ID enum — member now, routing flip later

**Status:** ACCEPTED (S258, 2026-07-02 — PLAN-152 Wave F, sonnet5-tier)
**Date:** 2026-07-02
**Decision drivers:** the closed `MODEL_ID` enum requires an ADR + KERNEL edit
for every new member (`tier_policy/_types.py` contract); Sonnet 5 shipped
upstream and the framework cannot even *recognize* its wire string; OQ1 of
PLAN-152 was ratified by the Owner as "member + ADR now, routing flip later"
(unanimous, 4/4 debate critics + CEO).

## Context

`tier_policy._types.MODEL_ID` is a deliberately closed enum: the AEK
classifier, the loader fallback, and `is_known_model()` all reject any model
slug not in it. That is the framework's defense against silent model drift
(the S218 footgun class) — and it means a newly released Anthropic model is
invisible to the tier policy until a KERNEL ceremony adds it.

Anthropic released **Claude Sonnet 5** (`claude-sonnet-5`). Until this ADR,
`is_known_model("claude-sonnet-5")` returned `False`, so any on-disk tier
policy naming it would trip the loader's `unknown_model` fallback.

## Decision

1. **ADD the `SONNET5 = "claude-sonnet-5"` member** to `MODEL_ID`
   (KERNEL edit, PLAN-152 sentinel anchor `c88daf9`, kernel-override session
   per ADR-031 audit trail).
2. **Do NOT flip any routing default.** The M-tier default stays
   `MODEL_ID.OPUS47` (`claude-opus-4-8`) in `FROZEN_BASELINE`; the
   token-estimator dispatch default stays `claude-sonnet-4-6` in
   `cost-table.yaml`. A routing flip to Sonnet 5 is a cost/behavior decision
   that needs its own plan (v1.0.2+) with a soak window and a documented
   revert (OQ1 resolution, PLAN-152 §Resolved questions).
3. **"Reconcile OPUS47" = docstrings only.** The member NAME `OPUS47` is a
   frozen stable identifier from the Opus-4.7 era whose VALUE tracks the
   current Opus (`claude-opus-4-8`, R-CR R2-2). Renaming it would be a
   breaking ref-sweep with zero benefit; the docstrings at `_types.py`
   now say so explicitly.
4. **Regression pin:** `hooks/tests/test_tier_policy_sonnet5_routing_pin.py`
   pins `FROZEN_BASELINE.default_model == "claude-opus-4-8"`,
   `default_mode == "M"`, and the cost-table default — a future routing flip
   must consciously edit those tests, it cannot ride an enum addition.

## Cost / capability envelope (recorded for the future routing decision)

Verified against the live API reference (claude-api skill, cached 2026-06-24):

| Surface | Sonnet 5 | vs Sonnet 4.6 |
|---|---|---|
| Model ID | `claude-sonnet-5` (no date suffix) | — |
| Pricing (sticker) | $3 / $15 per MTok in/out | unchanged |
| Pricing (intro, through 2026-08-31) | $2 / $10 per MTok | −33% vs 4.6 sticker |
| Tokenizer | new (Opus-4.7 family) | ~+30% tokens for the same text |
| Context window | 1M | unchanged |
| Max output | 128K | unchanged |
| Effort | full range incl. `xhigh` (first Sonnet with it) | 4.6 lacks `xhigh` |
| Thinking | adaptive ON when `thinking` omitted; `budget_tokens` 400s | 4.6: omitted = off |
| Sampling params | non-default `temperature`/`top_p`/`top_k` rejected (400) | 4.6 accepts |

**Net cost note:** the intro discount (−33%) and the tokenizer inflation
(~+30% tokens) roughly cancel during the intro window; after 2026-08-31 an
equivalent request costs ~+30% more than on 4.6 at identical per-token rates.
This asymmetry is exactly why the routing flip needs its own soaked decision
instead of riding this member addition.

## Consequences

- `is_known_model("claude-sonnet-5")` is now `True`; on-disk tier policies
  may name it without tripping the `unknown_model` fallback.
- No behavior change for any existing route: every default still resolves as
  before (pinned by tests).
- `cost-table.yaml` carries a `claude-sonnet-5` pricing row (sticker rate;
  the estimator does not model intro pricing).
- `.claude/data/canonical_models.json` does NOT yet carry a Sonnet-5 entry:
  that file is provenance-stamped and checksum-protected (PLAN-133 B1 —
  Owner-run `build-canonical-models.py --fetch` from models.dev is the only
  sanctioned write path). The entry rides the next Owner refresh; until
  then this ADR is the in-repo record of the envelope.
- Follow-on (v1.0.2+): a dedicated routing plan may flip M-tier or the
  dispatch default to Sonnet 5, editing the pin tests + this ADR's status
  trail, with soak + revert per OQ1.

## Alternatives considered

- **Flip routing now** — rejected by the Owner-ratified OQ1: cost/behavior
  change bundled into a security-hotfix release, no soak.
- **Rename OPUS47 → OPUS48** — rejected (debate/Critic-D): breaking
  ref-sweep across every consumer for zero semantic gain; the enum NAME is
  an identifier, not documentation.
- **Leave Sonnet 5 unrecognized until the routing plan** — rejected: keeps
  `is_known_model` false for a live production model and forces the future
  plan to bundle a kernel ceremony with a routing change (exactly the
  coupling OQ1 split apart).
