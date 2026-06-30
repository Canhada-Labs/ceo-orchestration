# Provider pricing — per-model token cost table

> **Consumer:** `.claude/scripts/budget-summary.py` (PLAN-011 Phase 6 / ADR-033).
> **Format:** Markdown table. Columns `Provider`, `Model`, `Input $/1k tokens`,
> `Output $/1k tokens`. The parser is case-insensitive on column headers
> but matches models exactly (lower-cased) — keep model slugs stable.

**Last updated:** 2026-06-12 (added fast-mode premium-lane section for PLAN-135 W4 D7 — informational, not parsed; prior: 2026-06-02 cache-tier multipliers for PLAN-123 MF-A).
**Last verified:** 2026-05-29 (Anthropic rows: Opus 4.8 added at $5/$25; Opus 4-7 retained HISTORICAL; Google/OpenAI rows unchanged from 2026-04-14).
**Next refresh due:** 2026-08-27 (90-day cadence).
**Providers monitored:** Anthropic, Google, OpenAI (plus Local = $0 baseline).
**Snapshot source:** public pricing pages; the authoring session's
knowledge cutoff is 2025-05 — every row below is a documented
extrapolation from that baseline to 2026-Q2 with an explicit
`confidence` field. **Re-verify before production billing use.**

## Refresh cadence

This file refreshes every **≤90 days**. The CI guard in
`.github/workflows/validate.yml` (step `D1 pricing TBD guard`)
fail-fast-rejects any data row that still contains `TBD` in the
input or output cost column once this file is edited. Docs-freshness
(ADR-023 State 1) surfaces stale `Last verified` dates advisory.

Monitored provider pricing pages (authoritative URLs — verify before billing):

- **Anthropic:** `https://www.anthropic.com/pricing`
- **Google:** `https://ai.google.dev/pricing`
- **OpenAI:** `https://openai.com/api/pricing/`
- **Local (Ollama / llama.cpp / vLLM):** zero API fee; compute-only
  cost borne by the operator. Latency + VRAM are the real costs.

Every row below ships a `source` URL, a `last_verified` date, and a
`confidence` field (`high` = directly quoted from the provider's
current published rate card; `medium` = extrapolated from older public
snapshots with conservative rounding; `low` = not used today —
would require a fresh Owner check before billing).

## Pricing policy (ADR-033 §3)

- The budget hook (`check_budget.py`) in Sprint 11 **logs tokens only**.
  The cost column is advisory, consumed by `/agent budget` rollups,
  `audit-dashboard.py`, and offline cost-attribution scripts.
- When a row has `TBD` in either column the rollup emits
  `cost_source: "TBD"` and the `cost_usd` field is `null`. Never
  auto-substitute a zero — the whole point of the TBD marker is that
  we don't have confirmed numbers.
- Prices MUST be sourced from the provider's published pricing page
  (cite the URL inline as an HTML comment on the row). If a 2026 price
  is not yet public, leave `TBD` and open an issue tagged
  `pricing-confirmation`.
- Never invent 6-digit precision — round to the nearest known public
  rate and mark `confidence: medium` when extrapolating.

## Primary pricing table (per-1k tokens — consumed by parser)

> This is the table `budget_summary.load_pricing()` reads. Columns
> `Provider` / `Model` / `Input $/1k` / `Output $/1k` are load-bearing
> (case-insensitive substring match). Extra columns are ignored by the
> parser — safe to extend.

| Provider   | Model                   | Input $/1k | Output $/1k |
|------------|-------------------------|------------|-------------|
| Anthropic  | claude-fable-5          | 0.010      | 0.050       |
| Anthropic  | claude-opus-4-8         | 0.005      | 0.025       |
| Anthropic  | claude-opus-4-7         | 0.005      | 0.025       |
| Anthropic  | claude-opus-4-6         | 0.005      | 0.025       |
| Anthropic  | claude-sonnet-4-6       | 0.003      | 0.015       |
| Anthropic  | claude-haiku-4-5        | 0.001      | 0.005       |
| Anthropic  | claude-haiku-4-5-20251001 | 0.001    | 0.005       |
| Google     | gemini-2.5-pro          | 0.00125    | 0.010       |
| Google     | gemini-2.5-flash        | 0.0003     | 0.0025      |
| OpenAI     | gpt-4o                  | 0.0025     | 0.010       |
| OpenAI     | gpt-4.1                 | 0.002      | 0.008       |
| OpenAI     | gpt-4o-mini             | 0.00015    | 0.0006      |
| Local      | ollama-any              | 0.00       | 0.00        |

## Long-context (1M window) pricing — premium check (PLAN-137 A4 gate evidence — informational, NOT parsed)

> **Why this section exists.** PLAN-137 item A4 (rebaseline the per-plan token
> doctrine to the 1M window) is gated on confirming the 1M context window has **no
> long-context premium** — a cap raised on a wrong pricing assumption silently lets
> a run burn many× the intended budget. This is the dated, sourced confirmation
> artifact that opens the A4 gate. `budget_summary.load_pricing()` does NOT parse
> this section (no `Model`/`Input`/`Output` header) — it is doctrine evidence only.

**Gate verdict: GREEN — no long-context premium for any current-generation model.**
**Verified:** 2026-06-15 (PLAN-137 S236 design-review, live fetch).
**Source:** `https://platform.claude.com/docs/en/about-claude/pricing` (Long context
pricing + Fast mode pricing + Data residency pricing sections).

Anthropic's pricing page states the current generation (Opus 4.8 / 4.7 / 4.6,
Sonnet 4.6, Fable 5) includes the **full 1M-token context window at standard
per-token pricing** — a 900k-token request bills at the same per-token rate as a
9k-token request. This is a deliberate change from the historical 1M *beta*, which
DID carry a >200K-input premium on Sonnet 4 / older models; that tiered model is
**gone** for the current generation. Prompt-caching and batch discounts apply at
standard rates across the full window.

| CEO-tier model | 1M window? | Long-context premium? | Last verified |
|---|---|---|---|
| claude-opus-4-8 | Y (1M) | **No** — flat standard rate | 2026-06-15 |
| claude-opus-4-7 | Y (1M) | **No** | 2026-06-15 |
| claude-opus-4-6 | Y (1M) | **No** | 2026-06-15 |
| claude-sonnet-4-6 | Y (1M) | **No** | 2026-06-15 |
| claude-fable-5 | Y (1M) | **No** | 2026-06-15 |
| claude-haiku-4-5 | **N — 200K only** | n/a (window caps at 200K) | 2026-06-15 |

**Three non-classic spend multipliers the doctrine MUST still account for** (none is
the classic >200K context premium, but each multiplies spend at 1M scale):

1. **Haiku 4.5 window = 200K, not 1M.** A 1M-token plan doctrine cannot apply to a
   Haiku-tier arc; over-200K requests on Haiku error rather than over-bill, so cap
   Haiku budgets at its 200K window.
2. **Fast mode (Opus-only premium lane).** The pricing page states the fast-mode
   premium "applies across the full context window, including requests over 200k
   input tokens." Opus 4.6 / Opus 4.7 fast = $30 / $150 (6× base); Opus 4.8 fast =
   $10 / $50 (2× base). A 1M run under fast mode multiplies hard — budget it as
   base × fast-factor. (Fast mode is not available with the Batch API.)
3. **`inference_geo:"us"` data residency = 1.1×** on all token categories (Opus 4.6 /
   Sonnet 4.6 and later). Default global routing bills at standard rates.

**Net for the budget doctrine:** budget a 1M-token run as `tokens × base rate`, and
only layer the 1.1× (US residency) or the fast-mode factor IF those flags are set.
There is no surprise >200K tier underneath — the raise to a 1M per-plan band is safe
on the flat-rate assumption, conditional on the three multipliers above.

## Cache-tier multipliers (PLAN-123 MF-A — informational, NOT parsed)

> Anthropic prompt-caching multipliers applied to the BASE input rate in the
> primary table above. Consumed by the PLAN-123 harness (`.../PLAN-123/harness/
> freeze/pricing.py`), **NOT** by `budget_summary.load_pricing()` — the header
> deliberately avoids the substrings `Model` / `Input` / `Output` so the parser
> skips this table cleanly (same rule as the provenance + embeddings tables).

| Token class                | Cost multiplier | Maps to usage field            |
|----------------------------|-----------------|--------------------------------|
| fresh input                | 1.00x           | `input_tokens`                 |
| cache write (5-minute TTL) | 1.25x           | `cache_creation_input_tokens`  |
| cache write (1-hour TTL)   | 2.00x           | `cache_creation_input_tokens`  |
| cache read                 | 0.10x           | `cache_read_input_tokens`      |
| output                     | 1.00x           | `output_tokens`                |

Source: Anthropic prompt-caching docs (write 1.25× at the 5-minute TTL, 2.0× at
the 1-hour TTL; read 0.10× regardless of tier). Last verified 2026-06-02 for
PLAN-123. Mirrors `freeze/pricing.py` `CACHE_WRITE_MULT` / `CACHE_READ_MULT`; a
cache read billed at the full input rate (the gate-0b accounting) over-bills ~10×.

## Fast mode (`speed: "fast"`) — API-billed premium lane (PLAN-135 W4 D7 — informational, NOT parsed)

> Prose only — no table, so `budget_summary.load_pricing()` never
> touches this section. Doctrine one-liners; the kill ledger is stated,
> not re-litigated.

- Anthropic fast mode is requested via the model `speed` field (e.g.
  `{id: "claude-opus-4-6", speed: "fast"}`) or a `-fast` model-ID
  variant. As of the 2026-06 rate-card snapshot only **Opus 4.6** has a
  fast variant — Opus 4.7/4.8 ship none. Verify before any use.
- Fast mode is **API-billed at a premium over the standard rate card**
  and does **not** draw from subscription quota. There is deliberately
  no row for it in the primary table above: the framework routes
  nothing through it, and under the TBD policy (§Pricing policy) an
  unconfirmed premium rate would have to enter as `TBD` + a
  `pricing-confirmation` issue — which we decline to open until a
  route exists.
- The thesis fast mode would serve — orchestration speed — is dead
  5-6 ways (incl. PLAN-134 W2 E5 parallel-read: p50 51% slower, 37%
  costlier at the quality ceiling). Fast mode is a **future pilot lane
  ONLY** via a PLAN-134 W3-style pre-registration (frozen kill
  criteria + falsifier + budget cap). See
  `docs/HONEST-LIMITATIONS.md` §14 and `docs/CEO-MODEL-ROUTING.md`
  §Routing one-liners.

## Provenance table (metadata per row — human-readable only)

> **Not consumed by the parser.** Column headers deliberately AVOID the
> substrings `model`, `input`, `output` so that
> `budget_summary.load_pricing()` skips this table cleanly (see parser
> rules below). This table documents `last_verified`, `source`, and
> `confidence` for each row in the primary table. A row MUST appear
> in both tables.
>
> The per-1M columns are kept alongside the per-1k columns in the
> primary table so humans can cross-check directly against provider
> pricing pages (which all quote per-1M) without doing the ÷1000 math.

| Slug                    | Per-1M in | Per-1M out | Last verified | Confidence | Source                                                                                         |
|-------------------------|-----------|------------|---------------|------------|------------------------------------------------------------------------------------------------|
| claude-fable-5          | 10.00     | 50.00      | 2026-06-10    | high       | https://models.dev/api.json (Owner fetch sha a6f5cb21; live-confirmed 2026-06-11 by GATE-W0b reconciliation, 20/20 calls drift~0.0000 — docs/fable-5-baseline.md) |
| claude-opus-4-8         | 5.00      | 25.00      | 2026-06-10    | high       | https://models.dev/api.json (Owner fetch sha a6f5cb21; live-confirmed 2026-06-11 by GATE-W0b reconciliation; was live-confirmed 2026-05-29 via PLAN-120 WS-C) |
| claude-opus-4-7         | 5.00      | 25.00      | 2026-06-10    | high       | https://models.dev/api.json (Owner fetch sha a6f5cb21; live-confirmed 2026-06-11 by GATE-W0b reconciliation 20/20. NOTE: billed $15/$75 until the 4.8 launch price cut — pre-4.8 log replay must use the era rate, see git history of this row) |
| claude-opus-4-6         | 5.00      | 25.00      | 2026-06-15    | high       | https://platform.claude.com/docs/en/about-claude/pricing (Opus 4.6 rebased to $5/$25 at the post-4.8 Opus rate-card cut — the prior $15/$75 was the pre-4.8 Opus rate, now retired; PLAN-137 A4 live-verified 2026-06-15) |
| claude-sonnet-4-6       | 3.00      | 15.00      | 2026-04-14    | high       | https://www.anthropic.com/pricing (Sonnet tier)                                                |
| claude-haiku-4-5        | 1.00      | 5.00       | 2026-04-14    | medium     | https://www.anthropic.com/pricing (Haiku tier — conservative estimate pending 4.5 GA rate card) |
| claude-haiku-4-5-20251001 | 1.00    | 5.00       | 2026-04-27    | medium     | https://www.anthropic.com/pricing (Haiku tier — date-suffixed canonical ID per ADR-052 §Role-to-model distribution; same rate card as base claude-haiku-4-5) |
| gemini-2.5-pro          | 1.25      | 10.00      | 2026-04-14    | high       | https://ai.google.dev/pricing (2.5 Pro ≤200k ctx tier; long-context tier is ~2× input)          |
| gemini-2.5-flash        | 0.30      | 2.50       | 2026-04-14    | high       | https://ai.google.dev/pricing (2.5 Flash standard tier)                                         |
| gpt-4o                  | 2.50      | 10.00      | 2026-04-14    | high       | https://openai.com/api/pricing/ (GPT-4o standard)                                               |
| gpt-4.1                 | 2.00      | 8.00       | 2026-04-14    | medium     | https://openai.com/api/pricing/ (GPT-4.1 — extrapolated from 2025-Q2 preview rate; verify at GA) |
| gpt-4o-mini             | 0.15      | 0.60       | 2026-04-14    | high       | https://openai.com/api/pricing/ (GPT-4o-mini)                                                   |
| ollama-any              | 0.00      | 0.00       | 2026-04-14    | high       | Local (Ollama / llama.cpp / vLLM) — zero API fee by construction; operator bears compute cost   |

## Embeddings (informational — not consumed by budget rollup today)

Embeddings pricing is NOT consumed by `check_budget.py` or
`budget_summary.py` in Sprint 11/12 (no embedding-triggering spawn
surface shipped yet). Ship it here so Sprint 13+ retrieval rollups
can consume without a schema migration. Column headers deliberately
use `Slug` (not `Model`) to keep this table outside the parser's
match pattern.

| Provider  | Slug                     | Per-1M in  | Last verified | Confidence | Source                                                |
|-----------|--------------------------|------------|---------------|------------|-------------------------------------------------------|
| OpenAI    | text-embedding-3-small   | 0.02       | 2026-04-14    | high       | https://openai.com/api/pricing/ (embeddings section)   |
| OpenAI    | text-embedding-3-large   | 0.13       | 2026-04-14    | high       | https://openai.com/api/pricing/ (embeddings section)   |

## How to fill in a confirmed price

1. Visit the provider's official pricing page (URLs listed above).
2. Convert "per-million-tokens" to "per-1k-tokens" (divide by 1000)
   for the **primary** table. Keep the per-1M value in the
   **provenance** table for direct comparison with source docs.
3. Replace `TBD` with the numeric dollar amount (no `$` prefix; the
   parser accepts either but the convention is naked floats).
4. Update BOTH tables in the same commit — the CI guard rejects any
   `TBD` in the primary table, and the docs-freshness advisory
   surfaces stale `Last verified` dates.
5. Update the `Last updated` / `Last verified` / `Next refresh due`
   dates at the top of the file.
6. Open a PR tagged `pricing-refresh`. CI docs-freshness check
   (advisory State 1 per ADR-023) surfaces stale dates > 90 days.

## How the parser reads this file

`budget_summary.load_pricing()`:

1. Finds the first Markdown table whose header contains `Model` AND
   either `Input` or `Output`.
2. Treats each data row as `{model: {in: float|None, out: float|None}}`.
3. Parses `TBD` / empty cells as `None` (returned as `null` in JSON
   output; displayed as `-` in human tables).
4. Lowercases model slugs when doing lookups — keep the table slugs
   lowercase to avoid matchup surprises.
5. Ignores HTML comments, header rows, separator rows, and any line
   not starting with `|`.
6. The provenance + embeddings tables are skipped because their
   headers use `Slug` (not `Model`) and `Per-1M in` / `Per-1M out`
   (not `Input` / `Output`). The parser requires a `model` substring
   in the header to start a table, so these auxiliary tables never
   enter the match loop. If you rename those headers, the parser WILL
   collide and overwrite the primary table — don't.

Adding a new row is additive — no schema migration required.

## References

- ADR-033 — cost-budget-enforcement lifecycle (this file's contract).
- ADR-023 — docs-as-code freshness (this file's refresh cadence gate).
- PLAN-011 Phase 6 — ships the advisory hook + CLI + this doc.
- PLAN-012 Phase 0 D1 — populates TBD rows + CI guard (this edit).
- `.claude/scripts/budget-summary.py` — the sole consumer.
- `.github/workflows/validate.yml` — step `D1 pricing TBD guard`.
- `docs/rotation-log.md` — pricing refresh cadence log.
