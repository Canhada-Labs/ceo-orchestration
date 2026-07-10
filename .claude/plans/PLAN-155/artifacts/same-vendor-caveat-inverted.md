# PLAN-155 Wave 6 — same-vendor caveat, direction-neutral wording

Wave 6 **supplies** this wording; Wave 7 **lands** it into
`docs/HONEST-LIMITATIONS.md`, `docs/provider_capability_matrix.md`,
`docs/adapters.md`, and the ADR-161 pair-rail row. It replaces the
Claude-Code-only phrasing of the pair-rail caveat with a phrasing that holds
in BOTH directions (Claude operates / Codex reviews, AND Codex operates /
Claude reviews).

## The property (direction-neutral)

> **No single model is both the author and the sole reviewer of a canonical
> edit.** The pair-rail runs a *second, different-vendor* model over changes
> the first proposes. Under Claude Code the operating model is Anthropic and
> the cross-model reviewer is OpenAI Codex; under the Codex harness the
> direction inverts — the operating model is OpenAI Codex and the reviewer is
> Anthropic Claude. The guarantee is symmetric: whichever vendor operates,
> the other reviews.

## The caveat (unchanged in force, re-pointed, NOT deleted)

> **This reduces single-model blind spots; it does not eliminate
> shared-substrate failure modes.** A defect both an OpenAI model and an
> Anthropic model make — a shared misconception, a class of prompt injection
> both fall for, an industry-wide training-data blind spot — is caught by
> neither seat. The pair-rail buys *cross-vendor diversity*, not
> *independence*. It is one layer; CODEOWNERS, branch protection, CI, and
> human review at merge are the others.

## Direction-specific residuals (each named)

- **Claude-operates / Codex-reviews** (existing rail, PLAN-081/142): the
  reviewer runs as an MCP tool / subprocess mid-edit (PreToolUse-adjacent);
  residual = the review is advisory-to-block on the *proposed content*, and
  the Codex CLI version pin governs what was certified
  (`.claude/governance/codex-cli-pin.txt`).
- **Codex-operates / Claude-reviews** (this wave, inverted): the reviewer
  runs at **Stop time** (`check_codex_stop_review.py`) and at **push time**
  (`pre-push-review-gate.sh`), not per-edit mid-turn; residual = killing the
  session or refusing twice abandons the Stop gate (the pre-push gate is the
  teeth), and the reviewer-model pin is PROVISIONAL (OQ3, `claude-opus-4-8`,
  override `CEO_PAIR_RAIL_REVIEWER_MODEL`) pending Owner ratification.

## Reviewer-unavailable posture (ADR-161 A20, direction-neutral)

> If the reviewer cannot be reached (binary absent, timeout, empty verdict),
> the rail records the attempt as `UNAVAILABLE` and does **not** silently
> approve and does **not** block forever: it allows with a loud RED-on-absence
> breadcrumb, and the push-time gate + CI remain the backstops. A rail that
> blocked indefinitely on a broken reviewer would be a denial-of-service on
> the operator; a rail that silently approved would be the S254 dead-gate. The
> honest middle is: record the gap, allow with noise, backstop downstream.

## One-line forms (for tables / matrix rows)

- Matrix cell: *"INVERTED pair-rail: Codex operates, Claude reviews (Stop +
  push time). Same-vendor caveat holds direction-neutrally; residual:
  kill-session abandons the Stop gate → pre-push is the teeth."*
- HONEST-LIMITATIONS bullet: *"Cross-vendor review reduces, does not
  eliminate, shared-substrate blind spots — in either direction."*
