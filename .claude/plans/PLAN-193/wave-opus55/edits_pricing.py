"""edits_pricing.py — the PRICING half of the wave-opus55 derivation (PLAN-193 W3).

Data only: this module exposes ``EDITS`` for the cost / telemetry / doc
surfaces of the ``adopt-opus-5.5`` wave (ADR-149 Amendment 3, S357). It
applies nothing. The core derivator (``apply-opus55-edits.py``) imports it,
concatenates it with its own table and applies both, anchor-exact.

Record shape — IDENTICAL to ``apply-fable51-edits.py`` (PLAN-169, S338)::

    (path relative to the repo root, EXACT anchor, replacement, expected count)

The order is the application order. Every anchor was cut from HEAD
``19771fa1`` and is counted BEFORE any write; when two edits share a path,
the later anchor is disjoint from the earlier replacement, so the count also
holds on the progressively edited text (the validator in the lane scratchpad
checks both).

Facts the rows rest on (pricing page + models overview, fetched 2026-09-22,
S357; cross-checked against the claude-api skill bundled with Claude Code
2.1.280): ``claude-opus-5-5`` is dateless; $4 in / $20 out per MTok; cache
READ $0.20/MTok = 0.05x base (NOT the standard 0.10x); cache writes follow
the standard 1.25x (5m) / 2.00x (1h) = $5 / $8; batch $2 / $10; 1M context
at standard price; 128K max output. Decision S357: NO ``claude-opus-5-5-fast``
row anywhere (the id is outside the signed working set, so
``check-model-currency.py`` would report it as a new red).

``build-canonical-models.py``: NO row is added to
``.claude/data/canonical_models.json`` — that table is an Owner
``--fetch`` snapshot of models.dev whose ``provenance.sha256`` covers the
``models`` block; a hand-written row with a recomputed checksum would
certify a fetch that never happened. ``price_for("claude-opus-5-5")``
therefore stays UNKNOWN (flag, never guess — the shipped table carries no
``claude-opus-5*`` row at all). What this module DOES change there is the
``_MM_TIERS`` reconcile table: the generic ``opus-5+`` tier would price
Opus 5.5 at $5/$25 with $0.50 cache reads, so the day an Owner refresh adds
the row ``--reconcile`` would raise five false divergences — the Sonnet 5
class (PLAN-169 S338 follow-up), second occurrence, cured the same way: a
dedicated tier that precedes the generic one.

Stdlib-only, Python >= 3.9, no PEP 604 at runtime.
"""
from __future__ import annotations

from typing import List, Tuple

NEW_ID = "claude-opus-5-5"

# --------------------------------------------------------------------------
# Shared literals (kept here so a row and its test cannot drift apart).
# --------------------------------------------------------------------------
_A3 = "ADR-149 Amendment 3 (S357)"

_COST_TABLE_OPUS5_FAST_ROW = (
    "  claude-opus-5-fast:\n"
    "    input_per_mtok: 10.00\n"
    "    output_per_mtok: 50.00\n"
    "    tier: opus\n"
    '    source_url: "https://docs.anthropic.com/en/docs/about-claude/pricing"  # PLAN-163 T1.5b: fast-mode premium row (Opus 5/4.8 only; removed from 4.7) — cost/latency trade-off, see docs/ACCELERATORS.md\n'
)

_FABLE51_1M_ROW = (
    "| claude-fable-5-1 | Y (1M) | **No** — documentary: the pricing page (fetched 2026-09-01) §Long context pricing states that Claude 4.6 and later models include the full 1M window at STANDARD pricing; the PLAN-137 live probe was not re-run for 5.1 (ADR-149 Amendment 2, S338) | 2026-09-01 |\n"
)

_FABLE51_PROVENANCE_OLD = (
    "| claude-fable-5-1        | 10.00     | 50.00      | 2026-09-01    | medium     | https://platform.claude.com/docs/en/about-claude/models/overview (Fable 5.1 launch 2026-09-01; base rate equals Fable 5; cache hits 0.025x base = $0.25/MTok per the pricing page fetched 2026-09-01 — the ONLY model off the standard 0.1x; ADR-149 Amendment 2, S338) |\n"
)

_FABLE51_PROVENANCE_NEW = (
    "| claude-fable-5-1        | 10.00     | 50.00      | 2026-09-01    | medium     | https://platform.claude.com/docs/en/about-claude/models/overview (Fable 5.1 launch 2026-09-01; base rate equals Fable 5; cache hits 0.025x base = $0.25/MTok per the pricing page fetched 2026-09-01 — a per-model exception to the standard 0.1x, see §Cache-tier multipliers; ADR-149 Amendment 2, S338) |\n"
    "| claude-opus-5-5         | 4.00      | 20.00      | 2026-09-22    | medium     | https://platform.claude.com/docs/en/about-claude/pricing (Opus 5.5; $4/$20; cache hits 0.05x base = $0.20/MTok, cache writes 1.25x/2.0x = $5/$8; batch $2/$10; 1M context at standard pricing; pricing page fetched 2026-09-22; ADR-149 Amendment 3, S357) |\n"
)

# --------------------------------------------------------------------------
# (path, EXACT anchor, replacement, expected occurrences)
# --------------------------------------------------------------------------
EDITS: List[Tuple[str, str, str, int]] = [
    # ============================================================ cost-table
    (
        ".claude/scripts/cost-table.yaml",
        _COST_TABLE_OPUS5_FAST_ROW,
        _COST_TABLE_OPUS5_FAST_ROW
        + "  claude-opus-5-5:\n"
        "    input_per_mtok: 4.00\n"
        "    output_per_mtok: 20.00\n"
        "    tier: opus\n"
        '    source_url: "https://platform.claude.com/docs/en/about-claude/pricing"  # ADR-149 Amendment 3 (S357, fetched 2026-09-22): Opus 5.5 at $4/$20; 1M ctx at standard price / 128K out; cache hits 0.05x base ($0.20/MTok) — this table has no cache field, budget-summary.py and ceo-cost-transcripts.py carry the per-model multiplier; NO claude-opus-5-5-fast row (outside the signed working set: check-model-currency.py would report it red)\n',
        1,
    ),
    # --------------- model-currency expected reds: cite rows by id, not line
    (
        ".claude/data/model-currency-expected-reds.txt",
        "# subset of it. Publishing four here would make the gate red on day one.\n",
        "# subset of it. Publishing four here would make the gate red on day one.\n"
        "#\n"
        "# Price rows are cited by id (the bare id line that follows each cause),\n"
        "# never by line number: a new cost-table.yaml row shifts every line below\n"
        "# it (ADR-149 Amendment 3, S357, inserted the claude-opus-5-5 row).\n",
        1,
    ),
    (
        ".claude/data/model-currency-expected-reds.txt",
        "# cost-table.yaml:95 — previous flagship generation, price row retained for\n",
        "# cost-table.yaml — previous flagship generation, price row retained for\n",
        1,
    ),
    (
        ".claude/data/model-currency-expected-reds.txt",
        "# cost-table.yaml:100 — same generation, 1M-context variant of the row above.\n",
        "# cost-table.yaml — same generation, 1M-context variant of the row above.\n",
        1,
    ),
    (
        ".claude/data/model-currency-expected-reds.txt",
        "# cost-table.yaml:90 — fast-mode premium row for the Opus 5 flagship. A real\n",
        "# cost-table.yaml — fast-mode premium row for the Opus 5 flagship. A real\n",
        1,
    ),
    (
        ".claude/data/model-currency-expected-reds.txt",
        "# cost-table.yaml:80 AND the replacement of 2 deprecation rows\n",
        "# cost-table.yaml AND the replacement of 2 deprecation rows\n",
        1,
    ),
    (
        ".claude/data/model-currency-expected-reds.txt",
        "# table (cost-table.yaml:120) and 4 deprecation rows both carry the dated one.\n",
        "# table (cost-table.yaml) and 4 deprecation rows both carry the dated one.\n",
        1,
    ),
    # ================================================ build-canonical-models
    (
        ".claude/scripts/build-canonical-models.py",
        '    (r"opus-(?:[5-9]|\\d\\d)", (5.0, 6.25, 10.0, 0.50, 25.0)),\n',
        "    # ADR-149 Amendment 3 (S357): claude-opus-5-5 is $4/$20 with cache\n"
        "    # writes at the standard 1.25x / 2x ($5 / $8) and cache READS at\n"
        "    # 0.05x ($0.20; pricing page fetched 2026-09-22) — its own tier.\n"
        "    # MUST precede the generic opus-5+ tier below, which would otherwise\n"
        "    # price it at $5/$25 and raise five false divergences the day an\n"
        "    # Owner refresh adds the row (the Sonnet 5 class further down,\n"
        "    # second occurrence).\n"
        '    (r"opus-5-5(?:\\D|$)", (4.0, 5.0, 8.0, 0.20, 20.0)),\n'
        '    (r"opus-(?:[5-9]|\\d\\d)", (5.0, 6.25, 10.0, 0.50, 25.0)),\n',
        1,
    ),
    (
        ".claude/scripts/tests/test_build_canonical_models.py",
        '        self.assertEqual(bcm._mm_tier_for("claude-sonnet-4-6"),\n'
        "                         (3.0, 3.75, 6.00, 0.30, 15.0))\n",
        '        self.assertEqual(bcm._mm_tier_for("claude-sonnet-4-6"),\n'
        "                         (3.0, 3.75, 6.00, 0.30, 15.0))\n"
        "\n"
        "    def test_mm_tier_opus55_is_its_own_tier_and_opus5_keeps_generic(self):\n"
        '        """ADR-149 Amendment 3 (S357): Opus 5.5 resolves to its own $4/$20\n'
        "        tier (cache writes 1.25x/2x = $5/$8, cache reads 0.05x = $0.20);\n"
        "        Opus 5 keeps the generic $5/$25 tier. Dated and ``[1m]`` forms\n"
        "        resolve like the bare id; a longer minor token does not match the\n"
        '        5.5 tier (the regex ends on a non-digit or the end of the id)."""\n'
        "        opus55 = (4.0, 5.0, 8.0, 0.20, 20.0)\n"
        '        for mid in ("claude-opus-5-5", "claude-opus-5-5-20260922",\n'
        '                    "claude-opus-5-5[1m]"):\n'
        "            self.assertEqual(bcm._mm_tier_for(mid), opus55, mid)\n"
        "        opus5 = (5.0, 6.25, 10.0, 0.50, 25.0)\n"
        '        for mid in ("claude-opus-5", "claude-opus-5[1m]", "claude-opus-5-50"):\n'
        "            self.assertEqual(bcm._mm_tier_for(mid), opus5, mid)\n",
        1,
    ),
    (
        ".claude/scripts/tests/test_build_canonical_models.py",
        "        self.assertEqual(findings, [])\n"
        "\n"
        "    def test_divergence_is_flagged_not_overwritten(self):\n",
        "        self.assertEqual(findings, [])\n"
        "\n"
        "    def test_reconcile_opus55_row_at_its_rate_is_clean(self):\n"
        '        """ADR-149 Amendment 3 (S357): a canonical Opus 5.5 row at $4/$20\n'
        "        with its own cache rates ($5 / $8 writes, $0.20 reads) reconciles\n"
        "        with ZERO findings against BOTH the cost-table.yaml row and the\n"
        "        tier table; under the generic opus-5+ tier alone the same row\n"
        '        raised five false divergences (all five price fields differ)."""\n'
        '        models = {"claude-opus-5-5": {\n'
        '            "input_per_mtok": 4.0, "cache_write_5m_per_mtok": 5.0,\n'
        '            "cache_write_1h_per_mtok": 8.0, "cache_read_per_mtok": 0.2,\n'
        '            "output_per_mtok": 20.0}}\n'
        "        data = _sample_data(models=models)\n"
        "        findings = bcm.reconcile(data, cost_table_path=_COST_TABLE_PATH)\n"
        "        self.assertEqual(findings, [])\n"
        "\n"
        "    def test_divergence_is_flagged_not_overwritten(self):\n",
        1,
    ),
    # ======================================================= budget-summary
    (
        ".claude/scripts/budget-summary.py",
        "#: follow-up).\n"
        "_DEFAULT_PRICING: Dict[str, Dict[str, float]] = {\n",
        "#: follow-up).\n"
        "#: ADR-149 Amendment 3 (S357): claude-opus-5-5 $4/$20 (pricing page fetched\n"
        "#: 2026-09-22); its 0.05x cache-read rate lives in\n"
        "#: _CACHE_READ_MULTIPLIER_OVERRIDES below.\n"
        "_DEFAULT_PRICING: Dict[str, Dict[str, float]] = {\n",
        1,
    ),
    (
        ".claude/scripts/budget-summary.py",
        '    "claude-opus-5-fast":         {"in": 0.010, "out": 0.050},\n',
        '    "claude-opus-5-fast":         {"in": 0.010, "out": 0.050},\n'
        '    "claude-opus-5-5":            {"in": 0.004, "out": 0.020},  # ADR-149 Amendment 3 (S357)\n',
        1,
    ),
    (
        ".claude/scripts/budget-summary.py",
        "#: ADR-149 Amendment 2 (S338, codex rail r1 P2): the cache-read multiplier\n"
        "#: is PER MODEL. The pricing page (fetched 2026-09-01) prices cache hits on\n"
        "#: Claude Fable 5.1 / Mythos 5.1 at 0.025x the base input price\n"
        "#: ($0.25/MTok); every other model keeps the standard 0.10x. A flat 0.10x\n"
        "#: would OVERSTATE Fable 5.1 cache reads 4x. Keys are canonical ids.\n"
        "_CACHE_READ_MULTIPLIER_DEFAULT: float = 0.10\n"
        "_CACHE_READ_MULTIPLIER_OVERRIDES: Dict[str, float] = {\n"
        '    "claude-fable-5-1": 0.025,\n'
        "}\n"
        "\n"
        "\n"
        "def _cache_read_multiplier(model_id: str) -> float:\n"
        '    """Cache-read multiplier for ``model_id`` (0.10x unless overridden)."""\n'
        "    return _CACHE_READ_MULTIPLIER_OVERRIDES.get(\n"
        "        model_id, _CACHE_READ_MULTIPLIER_DEFAULT\n"
        "    )\n",
        "#: ADR-149 Amendment 2 (S338, codex rail r1 P2): the cache-read multiplier\n"
        "#: is PER MODEL. The pricing page (fetched 2026-09-01) prices cache hits on\n"
        "#: Claude Fable 5.1 / Mythos 5.1 at 0.025x the base input price\n"
        "#: ($0.25/MTok). A flat 0.10x would OVERSTATE Fable 5.1 cache reads 4x.\n"
        "#: ADR-149 Amendment 3 (S357): Claude Opus 5.5 cache hits are 0.05x its $4\n"
        "#: base ($0.20/MTok, pricing page fetched 2026-09-22) — a flat 0.10x would\n"
        "#: overstate them 2x. Every other model of the ADR-149 working set keeps\n"
        "#: the standard 0.10x; Mythos 5.1 (0.025x on the same page) is outside\n"
        "#: the working set and carries no entry. Keys are canonical ids.\n"
        "#: ceo-cost-transcripts.py mirrors this table exactly;\n"
        "#: test_model_fleet_presence.py binds the two.\n"
        "_CACHE_READ_MULTIPLIER_DEFAULT: float = 0.10\n"
        "_CACHE_READ_MULTIPLIER_OVERRIDES: Dict[str, float] = {\n"
        '    "claude-fable-5-1": 0.025,\n'
        '    "claude-opus-5-5": 0.05,\n'
        "}\n"
        "\n"
        "\n"
        "def _cache_read_multiplier(model_id: str) -> float:\n"
        '    """Cache-read multiplier for ``model_id`` (0.10x unless overridden)."""\n'
        "    return _CACHE_READ_MULTIPLIER_OVERRIDES.get(\n"
        "        model_id, _CACHE_READ_MULTIPLIER_DEFAULT\n"
        "    )\n"
        "\n"
        "\n"
        "def _cache_read_exceptions_text() -> str:\n"
        '    """The per-model cache-read exceptions, rendered FROM the table above.\n'
        "\n"
        "    ADR-149 Amendment 3 (S357): the report text is DERIVED, never\n"
        "    re-listed by hand — the hand-written \"0.025x on Fable 5.1\" went stale\n"
        "    on the next model with its own cache-read rate.\n"
        '    """\n'
        '    return ", ".join(\n'
        '        "%gx on %s" % (mult, model_id)\n'
        "        for model_id, mult in sorted(_CACHE_READ_MULTIPLIER_OVERRIDES.items())\n"
        "    )\n",
        1,
    ),
    (
        ".claude/scripts/budget-summary.py",
        "    # Cache classes are BILLABLE (docs/provider-pricing.md: read @0.10x\n"
        "    # input — 0.025x on Fable 5.1, see _CACHE_READ_MULTIPLIER_OVERRIDES —,\n",
        "    # Cache classes are BILLABLE (docs/provider-pricing.md: read @0.10x\n"
        "    # input — per-model exceptions in _CACHE_READ_MULTIPLIER_OVERRIDES —,\n",
        1,
    ),
    (
        ".claude/scripts/budget-summary.py",
        '        "                    (cache priced as input-equivalents: read @0.10x"\n'
        '        " — 0.025x on Fable 5.1 —,"\n'
        '        " write @1.25x — 5m-TTL assumption, docs/provider-pricing.md)"\n',
        '        "                    (cache priced as input-equivalents: read @0.10x"\n'
        '        " — " + _cache_read_exceptions_text() + " —,"\n'
        '        " write @1.25x — 5m-TTL assumption, docs/provider-pricing.md)"\n',
        1,
    ),
    # ================================================= ceo-cost-transcripts
    (
        ".claude/scripts/ceo-cost-transcripts.py",
        "``_CACHE_READ_MULTIPLIER_OVERRIDES`` (Fable 5.1 cache-read at 0.025x\n"
        "base, all other models at 0.10x; cache WRITE is 1.25x base at the\n"
        "5-minute TTL and 2.00x base at the 1-hour TTL — these multipliers are a\n",
        "``_CACHE_READ_MULTIPLIER_OVERRIDES`` (the per-model cache-read\n"
        "exceptions, mirrored below; every other model at 0.10x base; cache\n"
        "WRITE is 1.25x base at the 5-minute TTL and 2.00x base at the 1-hour\n"
        "TTL — these multipliers are a\n",
        1,
    ),
    (
        ".claude/scripts/ceo-cost-transcripts.py",
        "regardless of which base table is in play, applied per-model (Fable 5.1\n"
        "override on cache read only).\n",
        "regardless of which base table is in play, applied per-model (the\n"
        "``_CACHE_READ_MULTIPLIER_OVERRIDES`` exceptions act on cache read only).\n",
        1,
    ),
    (
        ".claude/scripts/ceo-cost-transcripts.py",
        "#: Owner-ratified 2026-09-01 intro rate (CLAUDE.md commit e47bf5d).\n"
        "_EMBEDDED_PRICING: Dict[str, Dict[str, float]] = {\n"
        '    "claude-fable-5-1": {"input_per_mtok": 10.00, "output_per_mtok": 50.00},\n'
        '    "claude-fable-5": {"input_per_mtok": 10.00, "output_per_mtok": 50.00},\n'
        '    "claude-opus-5": {"input_per_mtok": 5.00, "output_per_mtok": 25.00},\n',
        "#: Owner-ratified 2026-09-01 intro rate (CLAUDE.md commit e47bf5d).\n"
        "#: ADR-149 Amendment 3 (S357): claude-opus-5-5 at $4/$20 (pricing page\n"
        "#: fetched 2026-09-22).\n"
        "_EMBEDDED_PRICING: Dict[str, Dict[str, float]] = {\n"
        '    "claude-fable-5-1": {"input_per_mtok": 10.00, "output_per_mtok": 50.00},\n'
        '    "claude-fable-5": {"input_per_mtok": 10.00, "output_per_mtok": 50.00},\n'
        '    "claude-opus-5-5": {"input_per_mtok": 4.00, "output_per_mtok": 20.00},\n'
        '    "claude-opus-5": {"input_per_mtok": 5.00, "output_per_mtok": 25.00},\n',
        1,
    ),
    (
        ".claude/scripts/ceo-cost-transcripts.py",
        "#: read 0.10x (base input rate) — EXCEPT Fable 5.1 / Mythos 5.1 at 0.025x\n"
        "#: (pricing page 2026-09-01, ADR-149 Amendment 2). Mirrors\n"
        "#: budget-summary.py's _CACHE_READ_MULTIPLIER_OVERRIDES exactly.\n"
        "_CACHE_READ_MULTIPLIER_DEFAULT: float = 0.10\n"
        "_CACHE_READ_MULTIPLIER_OVERRIDES: Dict[str, float] = {\n"
        '    "claude-fable-5-1": 0.025,\n'
        "}\n",
        "#: read 0.10x (base input rate) — EXCEPT the per-model entries below:\n"
        "#: claude-fable-5-1 at 0.025x (pricing page 2026-09-01, ADR-149\n"
        "#: Amendment 2) and claude-opus-5-5 at 0.05x (pricing page 2026-09-22,\n"
        "#: ADR-149 Amendment 3). The pricing page also prices Mythos 5.1 cache\n"
        "#: hits at 0.025x; that model is outside the ADR-149 working set and\n"
        "#: carries no entry. Mirrors budget-summary.py's\n"
        "#: _CACHE_READ_MULTIPLIER_OVERRIDES exactly (bound by\n"
        "#: test_model_fleet_presence.py since S357).\n"
        "_CACHE_READ_MULTIPLIER_DEFAULT: float = 0.10\n"
        "_CACHE_READ_MULTIPLIER_OVERRIDES: Dict[str, float] = {\n"
        '    "claude-fable-5-1": 0.025,\n'
        '    "claude-opus-5-5": 0.05,\n'
        "}\n",
        1,
    ),
    (
        ".claude/scripts/ceo-cost-transcripts.py",
        "def _cache_read_multiplier(model_id: str) -> float:\n"
        "    return _CACHE_READ_MULTIPLIER_OVERRIDES.get(model_id, _CACHE_READ_MULTIPLIER_DEFAULT)\n",
        "def _cache_read_multiplier(model_id: str) -> float:\n"
        "    return _CACHE_READ_MULTIPLIER_OVERRIDES.get(model_id, _CACHE_READ_MULTIPLIER_DEFAULT)\n"
        "\n"
        "\n"
        "def _cache_read_exceptions_text() -> str:\n"
        '    """Per-model cache-read exceptions rendered FROM the override table\n'
        "    (ADR-149 Amendment 3, S357: the help text is derived, never re-listed).\"\"\"\n"
        '    return ", ".join(\n'
        '        "%gx for %s" % (mult, model_id)\n'
        "        for model_id, mult in sorted(_CACHE_READ_MULTIPLIER_OVERRIDES.items())\n"
        "    )\n",
        1,
    ),
    (
        ".claude/scripts/ceo-cost-transcripts.py",
        '            "correction applied). Cache-read multiplier: 0.10x base "\n'
        '            "(0.025x for claude-fable-5-1). Cache-write multiplier: 1.25x "\n',
        '            "correction applied). Cache-read multiplier: 0.10x base "\n'
        '            "(" + _cache_read_exceptions_text() + "). Cache-write multiplier: 1.25x "\n',
        1,
    ),
    # ======================================================= success-receipt
    (
        ".claude/scripts/success-receipt.py",
        "#: pricing page); historical rows retained (ADR-142 replay).\n",
        "#: pricing page); historical rows retained (ADR-142 replay).\n"
        "#: ADR-149 Amendment 3 (S357): claude-opus-5-5 at the budget-summary\n"
        "#: per-1k rate ($4/$20 per MTok).\n",
        1,
    ),
    (
        ".claude/scripts/success-receipt.py",
        '    "claude-opus-5-fast": {"in": 0.010, "out": 0.050},\n'
        '    "claude-sonnet-5":    {"in": 0.002, "out": 0.010},\n',
        '    "claude-opus-5-fast": {"in": 0.010, "out": 0.050},\n'
        '    "claude-opus-5-5":    {"in": 0.004, "out": 0.020},  # ADR-149 Amendment 3 (S357)\n'
        '    "claude-sonnet-5":    {"in": 0.002, "out": 0.010},\n',
        1,
    ),
    # ======================================================= audit-telemetry
    (
        ".claude/scripts/audit-telemetry.py",
        '    "claude-opus-5-fast": {"input": 10.00, "output": 50.00},  # fast-mode premium row\n',
        '    "claude-opus-5-fast": {"input": 10.00, "output": 50.00},  # fast-mode premium row\n'
        '    "claude-opus-5-5": {"input": 4.00, "output": 20.00},  # ADR-149 Amendment 3 (S357): Opus 5.5 at $4/$20\n',
        1,
    ),
    # ============================================================== ceo-cost
    (
        ".claude/scripts/ceo-cost.py",
        "# is due and cost-table.yaml now carries the same $2/$10.\n"
        "_DEFAULT_PRICING: Dict[str, Dict[str, float]] = {\n",
        "# is due and cost-table.yaml now carries the same $2/$10.\n"
        "# ADR-149 Amendment 3 (S357): claude-opus-5-5 $4/$20 (pricing page fetched\n"
        "# 2026-09-22).\n"
        "_DEFAULT_PRICING: Dict[str, Dict[str, float]] = {\n",
        1,
    ),
    (
        ".claude/scripts/ceo-cost.py",
        '    "claude-opus-5-fast": {"input_per_mtok": 10.00, "output_per_mtok": 50.00},\n'
        '    "claude-sonnet-5": {"input_per_mtok": 2.00, "output_per_mtok": 10.00},\n',
        '    "claude-opus-5-fast": {"input_per_mtok": 10.00, "output_per_mtok": 50.00},\n'
        '    "claude-opus-5-5": {"input_per_mtok": 4.00, "output_per_mtok": 20.00},  # ADR-149 Amendment 3 (S357)\n'
        '    "claude-sonnet-5": {"input_per_mtok": 2.00, "output_per_mtok": 10.00},\n',
        1,
    ),
    # ======================================================= value-dashboard
    (
        ".claude/scripts/value-dashboard.py",
        '    "claude-opus-5-fast":          {"in": 0.010, "out": 0.050},\n',
        '    "claude-opus-5-fast":          {"in": 0.010, "out": 0.050},\n'
        '    "claude-opus-5-5":             {"in": 0.004, "out": 0.020},  # ADR-149 Amendment 3 (S357)\n',
        1,
    ),
    # ============================================================= detectors
    (
        ".claude/scripts/detectors/overpowered.py",
        "# ADR-149 Amendment 2 (S338): += claude-fable-5-1 (Fable 5.1 flagship).\n"
        "# historical ids retained for audit-log replay (ADR-142).\n"
        "_LARGE_MODELS = frozenset({\n"
        '    "claude-opus-5",\n'
        '    "claude-fable-5",\n'
        '    "claude-fable-5-1",\n',
        "# ADR-149 Amendment 2 (S338): += claude-fable-5-1 (Fable 5.1 flagship).\n"
        "# ADR-149 Amendment 3 (S357): += claude-opus-5-5 (Opus 5.5, the session pin).\n"
        "# historical ids retained for audit-log replay (ADR-142).\n"
        "_LARGE_MODELS = frozenset({\n"
        '    "claude-opus-5",\n'
        '    "claude-fable-5",\n'
        '    "claude-fable-5-1",\n'
        '    "claude-opus-5-5",\n',
        1,
    ),
    (
        ".claude/scripts/detectors/wasteful_thinking.py",
        '    "claude-fable-5-1",  # ADR-149 Amendment 2 (S338)\n'
        '    "claude-opus-4-8",\n',
        '    "claude-fable-5-1",  # ADR-149 Amendment 2 (S338)\n'
        '    "claude-opus-5-5",  # ADR-149 Amendment 3 (S357)\n'
        '    "claude-opus-4-8",\n',
        1,
    ),
    # ====================================================== model_normalize
    (
        ".claude/scripts/optimizer/model_normalize.py",
        "    # PLAN-169 W2.10 F10: gen-5 fleet aliases (bare-family forms were\n"
        "    # undefined -> normalization fell through to the raw string). No [1m]\n"
        "    # rows for gen 5: 1M context is the default there, the suffix does not\n"
        "    # exist in that generation.\n",
        "    # PLAN-169 W2.10 F10: gen-5 fleet aliases (bare-family forms were\n"
        "    # undefined -> normalization fell through to the raw string). No [1m]\n"
        "    # rows are needed for gen 5: the ``[1m]`` tag DOES exist there (a\n"
        "    # Claude Code 2.1.280 session that selected the 1M variant reports\n"
        "    # ``claude-opus-5-5[1m]`` as its model id, observed S357) and\n"
        "    # normalize_model_name folds it generically for every id — ADR-149\n"
        "    # Amendment 3.\n",
        1,
    ),
    (
        ".claude/scripts/optimizer/model_normalize.py",
        '    "opus-5-fast": "claude-opus-5-fast",\n'
        "}\n",
        '    "opus-5-fast": "claude-opus-5-fast",\n'
        '    "opus-5-5": "claude-opus-5-5",  # ADR-149 Amendment 3 (S357): a distinct minor, never folded into opus-5\n'
        "}\n",
        1,
    ),
    (
        ".claude/scripts/optimizer/model_normalize.py",
        "# Whitespace run collapser (after strip).\n"
        '_WS_RX = re.compile(r"\\s+")\n',
        "# Whitespace run collapser (after strip).\n"
        '_WS_RX = re.compile(r"\\s+")\n'
        "\n"
        "# The context-window packaging tag the harness appends to a live model id.\n"
        '_ONE_M_TAG = "[1m]"\n',
        1,
    ),
    (
        ".claude/scripts/optimizer/model_normalize.py",
        "      3. map a known raw alias (incl. a date-stamp or ``[1m]`` packaging tag) onto\n"
        "         its dateless canonical slug.\n"
        "    The ``major.minor`` version token is NEVER altered: ``opus-4-1`` and\n"
        "    ``opus-4-8`` return DISTINCT ids. An unrecognized id is returned in its\n"
        "    case/whitespace-normalized form (callers flag-and-zero-price it; we never\n"
        "    guess). Never raises.\n",
        "      3. map a known raw alias (incl. a date-stamp or ``[1m]`` packaging tag) onto\n"
        "         its dateless canonical slug.\n"
        "      4. otherwise fold a trailing ``[1m]`` packaging tag on ANY id and retry\n"
        "         step 3 (ADR-149 Amendment 3, S357).\n"
        "    The ``major.minor`` version token is NEVER altered: ``opus-4-1`` and\n"
        "    ``opus-4-8`` return DISTINCT ids. An unrecognized id is returned in its\n"
        "    case/whitespace-normalized form, minus a ``[1m]`` tag (callers\n"
        "    flag-and-zero-price it; we never guess). Never raises.\n",
        1,
    ),
    (
        ".claude/scripts/optimizer/model_normalize.py",
        "        if m in _RAW_ALIASES:\n"
        "            return _RAW_ALIASES[m]\n"
        "        return m\n",
        "        if m in _RAW_ALIASES:\n"
        "            return _RAW_ALIASES[m]\n"
        "        # ADR-149 Amendment 3 (S357): the ``[1m]`` tag is packaging on every\n"
        "        # generation, not only on the rows above — strip the literal tag\n"
        "        # (never a version token) and retry the exact map.\n"
        "        if m.endswith(_ONE_M_TAG) and len(m) > len(_ONE_M_TAG):\n"
        "            base = m[: -len(_ONE_M_TAG)]\n"
        "            return _RAW_ALIASES.get(base, base)\n"
        "        return m\n",
        1,
    ),
    # ======================================================== provider-pricing
    (
        "docs/provider-pricing.md",
        "| Anthropic  | claude-fable-5-1        | 0.010      | 0.050       |\n",
        "| Anthropic  | claude-fable-5-1        | 0.010      | 0.050       |\n"
        "| Anthropic  | claude-opus-5-5         | 0.004      | 0.020       |\n",
        1,
    ),
    (
        "docs/provider-pricing.md",
        _FABLE51_1M_ROW,
        _FABLE51_1M_ROW
        + "| claude-opus-5-5 | Y (1M) | **No** — documentary: the pricing page (fetched 2026-09-22) lists Opus 5.5 with the 1M window at standard pricing; the PLAN-137 live probe was not re-run for 5.5 (ADR-149 Amendment 3, S357) | 2026-09-22 |\n",
        1,
    ),
    (
        "docs/provider-pricing.md",
        "the 1-hour TTL; read 0.10× regardless of tier — EXCEPT Claude Fable 5.1 /\n"
        "Mythos 5.1, whose cache hits are 0.025× base = $0.25/MTok: pricing page\n"
        "2026-09-01, ADR-149 Amendment 2; `budget-summary.py` carries the per-model\n"
        "multiplier). Last verified 2026-06-02 for\n",
        "the 1-hour TTL; read 0.10× regardless of tier — EXCEPT the models the\n"
        "pricing page prices at a per-model cache-hit rate: Claude Fable 5.1 and\n"
        "Mythos 5.1 at 0.025× base, Claude Opus 5.5 at 0.05× base (re-read\n"
        "2026-09-24). `budget-summary.py` and `ceo-cost-transcripts.py` carry the\n"
        "working-set ones in `_CACHE_READ_MULTIPLIER_OVERRIDES`: `claude-fable-5-1`\n"
        "at $0.25/MTok (ADR-149 Amendment 2) and `claude-opus-5-5` at $0.20/MTok\n"
        "(ADR-149 Amendment 3; its cache WRITES follow the standard 1.25× / 2.0×\n"
        "= $5 / $8 per MTok)). Last verified 2026-06-02 for\n",
        1,
    ),
    (
        "docs/provider-pricing.md",
        _FABLE51_PROVENANCE_OLD,
        _FABLE51_PROVENANCE_NEW,
        1,
    ),
    # ====================================================== cost-of-operation
    (
        "docs/cost-of-operation.md",
        "opus-5 session). Note the \"Mitigated rail default-on\" row lands at\n",
        "opus-5 session; the session `model` pin is `claude-opus-5-5` since ADR-149\n"
        "Amendment 3 ($4/$20, cache reads $0.20/MTok) and these figures are NOT\n"
        "recomputed for it — at the same token volume its Opus-billed share prices\n"
        "lower than shown). Note the\n"
        "\"Mitigated rail default-on\" row lands at\n",
        1,
    ),
    (
        "docs/cost-of-operation.md",
        "current fleet, whatever Gen-5 model the session runs (Fable 5/Opus 5,\n"
        "same $5-$25+/Mtok tier) — (not the\n",
        "current fleet, whatever Gen-5 model the session runs (the `model` pin\n"
        "`claude-opus-5-5` at $4/$20 since ADR-149 Amendment 3; Opus 5 at $5/$25;\n"
        "Fable 5 at $10/$50) — (not the\n",
        1,
    ),
    (
        "docs/cost-of-operation.md",
        "spawn therefore bills at **Opus rates ($5/$25 per Mtok)**, not\n",
        "spawn therefore bills at **the session model's rates** (Opus 4.8's\n"
        "$5/$25 per Mtok in this computation; $4/$20 on the `claude-opus-5-5`\n"
        "pin), not\n",
        1,
    ),
    (
        "docs/cost-of-operation.md",
        "| `claude-fable-5-1` (current — Mythos-class flagship 5.1; ADR-149 Amendment 2, S338 — selectable, not the pin) | $10.00 | $50.00 | 2.0× |\n",
        "| `claude-fable-5-1` (current — Mythos-class flagship 5.1; ADR-149 Amendment 2, S338 — selectable, not the pin) | $10.00 | $50.00 | 2.0× |\n"
        "| `claude-opus-5-5` (current — the session `model` pin; ADR-149 Amendment 3, S357; cache reads 0.05× base) | $4.00 | $20.00 | 0.8× |\n",
        1,
    ),
    (
        "docs/cost-of-operation.md",
        "Gen-5 rows added 2026-08-09 (PLAN-169 W2.10 D7, mirroring `ceo-cost.py`).\n",
        "Gen-5 rows added 2026-08-09 (PLAN-169 W2.10 D7, mirroring `ceo-cost.py`).\n"
        "Opus 5.5 row added 2026-09-22 (ADR-149 Amendment 3, S357; pricing page https://platform.claude.com/docs/en/about-claude/pricing): $4/$20, cache reads 0.05× base ($0.20/MTok) instead of the standard 0.10× — the per-model cache-read exceptions are listed in `docs/provider-pricing.md` §Cache-tier multipliers.\n",
        1,
    ),
    (
        "docs/cost-of-operation.md",
        "| **CEO orchestrator** (you, the chat session) | Opus 4.8 (now the session model — Fable 5/Opus 5) | Long context, L3+ decisions, debate synthesis |\n",
        "| **CEO orchestrator** (you, the chat session) | Opus 4.8 (now the session `model` pin — `claude-opus-5-5` since ADR-149 Amendment 3) | Long context, L3+ decisions, debate synthesis |\n",
        1,
    ),
    # ======================================================= CEO-MODEL-ROUTING
    (
        "docs/CEO-MODEL-ROUTING.md",
        '["claude-opus-4-8","claude-fable-5","claude-sonnet-4-6","claude-haiku-4-5","claude-opus-5","claude-sonnet-5","claude-fable-5-1"]\n',
        '["claude-opus-4-8","claude-fable-5","claude-sonnet-4-6","claude-haiku-4-5","claude-opus-5","claude-sonnet-5","claude-fable-5-1","claude-opus-5-5"]\n',
        1,
    ),
    (
        "docs/CEO-MODEL-ROUTING.md",
        "> only. The VETO floor, the fallback chain, the session pin and every row\n"
        "> of the table below are unchanged; 5.1 is selectable, not routed to.\n",
        "> only. The VETO floor, the fallback chain, the session pin and every row\n"
        "> of the table below are unchanged; 5.1 is selectable, not routed to.\n"
        "\n"
        "> **UPDATED S357 (ADR-149 Amendment 3, 2026-09-22):** `claude-opus-5-5`\n"
        "> (Opus 5.5 — $4/$20 per MTok, cache reads 0.05× = $0.20/MTok, 1M ctx,\n"
        "> API default effort `medium`) is appended to the working set, joins\n"
        "> `VETO_FLOOR_ALLOWED`, and becomes the session-default `model` pin. The\n"
        "> fallback chain stays `[\"claude-opus-5\"]` and every `veto_floor: true`\n"
        "> agent file in `.claude/agents/` keeps its `claude-fable-5` pin, which\n"
        "> binds agent-definition dispatch when the invocation passes no `model`\n"
        "> (a per-invocation model outranks the file, and no gate observes it).\n"
        "> A mitigated `general-purpose` spawn passed no model runs on the model\n"
        "> the session runs at that moment: the pin by default, or whatever a\n"
        "> `/model`, `--model` or `ANTHROPIC_MODEL` choice, or a content fallback\n"
        "> that persists for the session, selected (ADR-149 A3.3).\n"
        "> On the API, Opus 5.5 has its own rate limit, separate from Opus 5\n"
        "> (rate-limits page, fetched 2026-09-23). This note re-routes no row of\n"
        "> the table below; its first row states the session pin.\n",
        1,
    ),
    (
        "docs/CEO-MODEL-ROUTING.md",
        "| Role / surface | Model (post-PLAN-163) | Notes |\n"
        "|---|---|---|\n",
        "| Role / surface | Model (post-PLAN-163) | Notes |\n"
        "|---|---|---|\n"
        "| CEO orchestrator (session-default `model` pin) | `claude-opus-5-5` | ADR-149 Amendment 3 (S357); was `claude-opus-5`, which stays the `fallbackModel` |\n",
        1,
    ),
    # ============================================================ ACCELERATORS
    (
        "docs/ACCELERATORS.md",
        "  shows up (at the premium rate) in every cost rollup instead of pricing\n"
        "  at $0. Visibility is not authorization.\n",
        "  shows up (at the premium rate) in every cost rollup instead of pricing\n"
        "  at $0. Visibility is not authorization.\n"
        "- **Opus 5.5 fast mode is NOT covered.** The pricing page (fetched\n"
        "  2026-09-23) lists fast mode for Claude Opus 5.5 at $8 / $40 per MTok\n"
        "  (research preview, Claude API only). ADR-149 Amendment 3 (S357)\n"
        "  prices `claude-opus-5-5` at its standard $4 / $20 only; no\n"
        "  `claude-opus-5-5-fast` row exists on any rollup surface — a deliberate\n"
        "  choice of that pack; in `cost-table.yaml` such a row would also be a\n"
        "  new `check-model-currency.py` red, because the id is outside the\n"
        "  signed working set. Fast-mode spend on Opus 5.5 therefore does not get\n"
        "  the premium-rate visibility described above.\n",
        1,
    ),
    # ===================================================== tests: fleet presence
    (
        ".claude/scripts/tests/test_model_fleet_presence.py",
        "  - claude-opus-5-fast    $10 / $50  (fast-mode premium row)\n",
        "  - claude-opus-5-fast    $10 / $50  (fast-mode premium row)\n"
        "  - claude-opus-5-5       $4 / $20   (ADR-149 Amendment 3, S357 — the session\n"
        "                                      pin; cache reads 0.05x base, asserted\n"
        "                                      below together with the class cure that\n"
        "                                      reads the fleet FROM ADR-149)\n",
        1,
    ),
    (
        ".claude/scripts/tests/test_model_fleet_presence.py",
        '_COST_TABLE = _SCRIPTS_DIR / "cost-table.yaml"\n',
        '_COST_TABLE = _SCRIPTS_DIR / "cost-table.yaml"\n'
        '_ADR_149 = _REPO_ROOT / ".claude" / "adr" / "ADR-149-model-id-allowlist.md"\n',
        1,
    ),
    (
        ".claude/scripts/tests/test_model_fleet_presence.py",
        "#: Fable 5 rate; the same silent-$0 class this file exists to keep honest.\n"
        "_NEW_FLEET = (\n"
        '    "claude-opus-4-8",\n'
        '    "claude-opus-4-8-fast",\n'
        '    "claude-fable-5",\n'
        '    "claude-fable-5-1",\n'
        '    "claude-opus-5",\n'
        '    "claude-opus-5-fast",\n'
        '    "claude-sonnet-5",\n'
        ")\n",
        "#: Fable 5 rate; the same silent-$0 class this file exists to keep honest.\n"
        "#: claude-opus-5-5 added by ADR-149 Amendment 3 (S357) — Opus 5.5 at $4/$20.\n"
        "#: Since S357 this hand list is NOT the only guard: the working-set class\n"
        "#: cure below reads the fleet from ADR-149 itself.\n"
        "_NEW_FLEET = (\n"
        '    "claude-opus-4-8",\n'
        '    "claude-opus-4-8-fast",\n'
        '    "claude-fable-5",\n'
        '    "claude-fable-5-1",\n'
        '    "claude-opus-5",\n'
        '    "claude-opus-5-fast",\n'
        '    "claude-opus-5-5",\n'
        '    "claude-sonnet-5",\n'
        ")\n",
        1,
    ),
    (
        ".claude/scripts/tests/test_model_fleet_presence.py",
        "    mod = importlib.util.module_from_spec(spec)\n"
        "    spec.loader.exec_module(mod)\n"
        "    return mod\n",
        "    mod = importlib.util.module_from_spec(spec)\n"
        "    spec.loader.exec_module(mod)\n"
        "    return mod\n"
        "\n"
        "\n"
        "def _load_registered(module_name: str, file_name: str):\n"
        '    """Like ``_load_hyphenated`` but registers the module in ``sys.modules``\n'
        "    BEFORE executing it: ceo-cost-transcripts.py declares dataclasses, which\n"
        "    resolve their module through ``sys.modules`` at class-definition time.\n"
        '    """\n'
        "    spec = importlib.util.spec_from_file_location(\n"
        "        module_name, str(_SCRIPTS_DIR / file_name)\n"
        "    )\n"
        "    mod = importlib.util.module_from_spec(spec)\n"
        "    sys.modules[module_name] = mod\n"
        "    spec.loader.exec_module(mod)\n"
        "    return mod\n",
        1,
    ),
    (
        ".claude/scripts/tests/test_model_fleet_presence.py",
        '            "claude-opus-5-fast": (10.00, 50.00),\n'
        "            # Base-row intro rate; the 2026-08-31 flip is event-date-aware\n",
        '            "claude-opus-5-fast": (10.00, 50.00),\n'
        '            "claude-opus-5-5": (4.00, 20.00),  # ADR-149 A3 (S357)\n'
        "            # Base-row intro rate; the 2026-08-31 flip is event-date-aware\n",
        1,
    ),
    (
        ".claude/scripts/tests/test_model_fleet_presence.py",
        '        for model in ("claude-fable-5", "claude-fable-5-1", "claude-opus-5"):\n',
        '        for model in ("claude-fable-5", "claude-fable-5-1", "claude-opus-5",\n'
        '                      "claude-opus-5-5"):\n',
        2,
    ),
    (
        ".claude/scripts/tests/test_model_fleet_presence.py",
        '            "claude-fable-5-1": (0.010, 0.050),  # ADR-149 A2 (S338)\n'
        '            "claude-sonnet-5": (0.002, 0.010),  # base row; dated flip below\n',
        '            "claude-fable-5-1": (0.010, 0.050),  # ADR-149 A2 (S338)\n'
        '            "claude-opus-5-5": (0.004, 0.020),  # ADR-149 A3 (S357)\n'
        '            "claude-sonnet-5": (0.002, 0.010),  # base row; dated flip below\n',
        1,
    ),
    (
        ".claude/scripts/tests/test_model_fleet_presence.py",
        "            self.assertAlmostEqual(self.mod._cache_read_multiplier(model), 0.10)\n"
        "\n"
        "    def test_bare_fable_alias_is_ambiguous_and_versioned_alias_resolves(self) -> None:\n",
        "            self.assertAlmostEqual(self.mod._cache_read_multiplier(model), 0.10)\n"
        "\n"
        "    def test_opus55_cache_read_multiplier(self) -> None:\n"
        '        """ADR-149 A3 (S357): Opus 5.5 cache hits are 0.05x base input\n'
        "        ($0.20 on the $4 base — pricing page 2026-09-22), NOT the standard\n"
        '        0.10x; claude-opus-5 keeps 0.10x (a distinct minor)."""\n'
        "        self.assertAlmostEqual(\n"
        '            self.mod._cache_read_multiplier("claude-opus-5-5"), 0.05)\n'
        "        self.assertAlmostEqual(\n"
        '            self.mod._cache_read_multiplier("claude-opus-5"), 0.10)\n'
        '        text = self.mod._cache_read_exceptions_text()\n'
        '        self.assertIn("0.05x on claude-opus-5-5", text)\n'
        '        self.assertIn("0.025x on claude-fable-5-1", text)\n'
        "\n"
        "    def test_native_spawn_opus55_one_m_tag_priced_with_its_cache_rate(self) -> None:\n"
        '        """ADR-149 A3 (S357): a session that selected the 1M variant\n'
        '        reports the id WITH the ``[1m]`` tag (``claude-opus-5-5[1m]``,\n'
        '        observed S357 on Claude Code 2.1.280); a bare\n'
        "        ``opus`` meta alias is ambiguous, so the transcript model decides —\n"
        '        and the spawn is priced at $4 input + 0.05x cache reads."""\n'
        "        import tempfile\n"
        "        from pathlib import Path\n"
        "        with tempfile.TemporaryDirectory() as td:\n"
        '            tr = Path(td) / "agent-y.jsonl"\n'
        "            tr.write_text(\n"
        "                '{\"timestamp\": \"2026-09-22T00:00:00Z\", \"message\": '\n"
        "                '{\"model\": \"claude-opus-5-5[1m]\", \"usage\": {\"input_tokens\": 1000000, '\n"
        "                '\"output_tokens\": 0, \"cache_read_input_tokens\": 1000000}}}\\n',\n"
        '                encoding="utf-8",\n'
        "            )\n"
        '            (Path(td) / "agent-y.meta.json").write_text(\n'
        "                '{\"agentType\": \"t\", \"spawnDepth\": 1, \"model\": \"opus\"}',\n"
        '                encoding="utf-8",\n'
        "            )\n"
        '            rec = self.mod._read_native_spawn(tr, "native", "sess")\n'
        "        self.assertIsNotNone(rec)\n"
        '        self.assertEqual(rec["model_id"], "claude-opus-5-5")\n'
        '        self.assertFalse(rec["cost_tbd"])\n'
        "        # 1M fresh input at $4 + 1M cache reads at 0.05x ($0.20) == $4.20\n"
        '        self.assertAlmostEqual(rec["cost_usd"], 4.20, places=6)\n'
        "\n"
        "    def test_bare_fable_alias_is_ambiguous_and_versioned_alias_resolves(self) -> None:\n",
        1,
    ),
    (
        ".claude/scripts/tests/test_model_fleet_presence.py",
        "class TestCostTableFleetPresence(TestEnvContext):\n",
        "class TestWorkingSetPricedOnEverySurface(TestEnvContext):\n"
        '    """ADR-149 Amendment 3 (S357) — the CLASS cure for "a new model id\n'
        '    prices at $0 / TBD on some rollup surface".\n'
        "\n"
        "    A recurring class (PLAN-163 T1.5, PLAN-169 W2.10 F3, the Fable 5.1\n"
        "    codex rail r3 P1), and Opus 5.5 needed the same hand edits again: the\n"
        "    hand-kept ``_NEW_FLEET`` tuple only guards the ids someone remembered\n"
        "    to add. Here the fleet is READ from the signed\n"
        "    authority — ADR-149 ``AVAILABLE_MODELS_WORKING_SET``, through the same\n"
        "    parser the model-currency gate uses — so the NEXT working-set append\n"
        "    fails this test until every rollup surface prices it at the\n"
        "    cost-table.yaml rate.\n"
        '    """\n'
        "\n"
        "    #: (script, table attribute, input key, output key, factor to per-MTok)\n"
        "    _SURFACES = (\n"
        '        ("audit-telemetry.py", "_PRICING_PER_MTOK", "input", "output", 1.0),\n'
        '        ("ceo-cost.py", "_DEFAULT_PRICING", "input_per_mtok", "output_per_mtok", 1.0),\n'
        '        ("budget-summary.py", "_DEFAULT_PRICING", "in", "out", 1000.0),\n'
        '        ("success-receipt.py", "_DEFAULT_PRICING", "in", "out", 1000.0),\n'
        '        ("value-dashboard.py", "_DEFAULT_PRICING", "in", "out", 1000.0),\n'
        '        ("ceo-cost-transcripts.py", "_EMBEDDED_PRICING", "input_per_mtok",\n'
        '         "output_per_mtok", 1.0),\n'
        "    )\n"
        "\n"
        "    @classmethod\n"
        "    def setUpClass(cls):\n"
        "        super().setUpClass()\n"
        "        currency = _load_registered(\n"
        '            "fleet_ws_currency", "check-model-currency.py")\n'
        "        cls.working_set = list(\n"
        "            currency.read_adr_blocks(_ADR_149)[\"AVAILABLE_MODELS_WORKING_SET\"])\n"
        "        cls.cct = _load_registered(\n"
        '            "fleet_ws_transcripts", "ceo-cost-transcripts.py")\n'
        "        cls.cost_table = cls.cct._parse_cost_table_yaml(\n"
        '            _COST_TABLE.read_text(encoding="utf-8"))\n'
        "        cls.tables = {}\n"
        "        for idx, (script, attr, k_in, k_out, factor) in enumerate(cls._SURFACES):\n"
        '            if script == "ceo-cost-transcripts.py":\n'
        "                mod = cls.cct\n"
        "            else:\n"
        '                mod = _load_registered("fleet_ws_surface_%d" % idx, script)\n'
        "            cls.tables[script] = (getattr(mod, attr), k_in, k_out, factor)\n"
        "\n"
        "    def test_working_set_read_from_the_adr(self) -> None:\n"
        '        """Non-vacuity: the fleet came from the ADR, and this pack\'s id is\n'
        '        in it (the ADR append and these price rows land together)."""\n'
        "        self.assertGreaterEqual(len(self.working_set), 8)\n"
        '        self.assertIn("claude-opus-5-5", self.working_set)\n'
        "\n"
        "    def test_every_working_set_id_priced_on_every_surface(self) -> None:\n"
        "        for model in self.working_set:\n"
        "            ref = self.cost_table.get(model)\n"
        '            self.assertIsNotNone(ref, "%s has no cost-table.yaml row" % model)\n'
        "            for script, (table, k_in, k_out, factor) in self.tables.items():\n"
        "                with self.subTest(model=model, surface=script):\n"
        "                    row = table.get(model)\n"
        "                    self.assertIsNotNone(\n"
        '                        row, "%s missing from %s — prices at $0/TBD" % (model, script))\n'
        "                    self.assertAlmostEqual(\n"
        '                        row[k_in] * factor, ref["input_per_mtok"], places=6,\n'
        '                        msg="%s input rate on %s" % (model, script))\n'
        "                    self.assertAlmostEqual(\n"
        '                        row[k_out] * factor, ref["output_per_mtok"], places=6,\n'
        '                        msg="%s output rate on %s" % (model, script))\n'
        "\n"
        "\n"
        "class TestCacheReadMultiplierMirror(TestEnvContext):\n"
        '    """ADR-149 Amendment 3 (S357): the per-model cache-read rate is now a\n'
        "    CLASS (Fable 5.1 0.025x, then Opus 5.5 0.05x) that lives in TWO scripts.\n"
        '    ceo-cost-transcripts.py declares it "mirrors budget-summary.py\'s\n'
        '    _CACHE_READ_MULTIPLIER_OVERRIDES exactly" — this makes that mechanical.\n'
        '    """\n'
        "\n"
        "    @classmethod\n"
        "    def setUpClass(cls):\n"
        "        super().setUpClass()\n"
        '        cls.bs = _load_hyphenated("budget_summary_cache_mirror", "budget-summary.py")\n'
        "        cls.cct = _load_registered(\n"
        '            "transcripts_cache_mirror", "ceo-cost-transcripts.py")\n'
        "\n"
        "    def test_transcripts_mirror_budget_summary_exactly(self) -> None:\n"
        "        self.assertEqual(self.cct._CACHE_READ_MULTIPLIER_OVERRIDES,\n"
        "                         self.bs._CACHE_READ_MULTIPLIER_OVERRIDES)\n"
        "        self.assertEqual(self.cct._CACHE_READ_MULTIPLIER_DEFAULT,\n"
        "                         self.bs._CACHE_READ_MULTIPLIER_DEFAULT)\n"
        "\n"
        "    def test_opus55_is_005_on_both(self) -> None:\n"
        "        for mod in (self.bs, self.cct):\n"
        '            self.assertAlmostEqual(mod._cache_read_multiplier("claude-opus-5-5"), 0.05)\n'
        '            self.assertAlmostEqual(mod._cache_read_multiplier("claude-opus-5"), 0.10)\n'
        "\n"
        "    def test_every_override_is_a_priced_id(self) -> None:\n"
        "        for model in self.bs._CACHE_READ_MULTIPLIER_OVERRIDES:\n"
        "            self.assertIn(model, self.bs._DEFAULT_PRICING)\n"
        "            self.assertIn(model, self.cct._EMBEDDED_PRICING)\n"
        "\n"
        "\n"
        "class TestCostTableFleetPresence(TestEnvContext):\n",
        1,
    ),
    (
        ".claude/scripts/tests/test_model_fleet_presence.py",
        "    def test_opus48_fast_row(self) -> None:\n",
        "    def test_opus55_row(self) -> None:\n"
        '        """ADR-149 Amendment 3 (S357): Opus 5.5 at $4/$20 — and NO fast\n'
        "        row: ``claude-opus-5-5-fast`` is outside the signed working set, so\n"
        '        check-model-currency.py would report it as a new red."""\n'
        '        text = self._block("claude-opus-5-5")\n'
        '        self.assertIn("input_per_mtok: 4.00", text)\n'
        '        self.assertIn("output_per_mtok: 20.00", text)\n'
        "        self.assertIsNone(\n"
        '            re.search(r"^  claude-opus-5-5-fast:", self.cost_table, re.MULTILINE))\n'
        "\n"
        "    def test_opus48_fast_row(self) -> None:\n",
        1,
    ),
    # ================================================= tests: A4 pricing doctrine
    (
        ".claude/scripts/tests/test_a4_pricing_doctrine.py",
        '    "claude-fable-5-1": (10.00, 50.00),\n'
        '    "claude-haiku-4-5": (1.00, 5.00),\n'
        "}\n",
        '    "claude-fable-5-1": (10.00, 50.00),\n'
        "    # ADR-149 Amendment 3 (S357): DOCUMENTARY evidence, not the PLAN-137\n"
        "    # live probe — pricing page (2026-09-22): Opus 5.5 carries the 1M\n"
        "    # window at standard pricing (provider-pricing.md row).\n"
        '    "claude-opus-5-5": (4.00, 20.00),\n'
        '    "claude-haiku-4-5": (1.00, 5.00),\n'
        "}\n",
        1,
    ),
    # ================================================ tests: model_normalize
    (
        ".claude/scripts/optimizer/tests/test_optimizer_model_normalize.py",
        "    # but it must not fold a DIFFERENT version's tag onto 4-8.\n"
        '    assert normalize_model_name("claude-opus-4-1") == "claude-opus-4-1"\n',
        "    # but it must not fold a DIFFERENT version's tag onto 4-8.\n"
        '    assert normalize_model_name("claude-opus-4-1") == "claude-opus-4-1"\n'
        "\n"
        "\n"
        "def test_one_m_tag_folds_on_every_generation():\n"
        "    # ADR-149 Amendment 3 (S357): the harness reports ``claude-opus-5-5[1m]``\n"
        "    # as the live id (Claude Code 2.1.280) — gen 5 carries the tag too, so\n"
        "    # the fold is generic, never a per-row alias.\n"
        '    for canonical in ("claude-opus-5-5", "claude-opus-5", "claude-fable-5-1",\n'
        '                      "claude-fable-5", "claude-sonnet-5"):\n'
        '        assert normalize_model_name(canonical + "[1m]") == canonical\n'
        '    assert normalize_model_name("Some-Future-Model-9-9[1M]") == "some-future-model-9-9"\n'
        '    # the bare tag is not an id — it is returned as-is, never emptied.\n'
        '    assert normalize_model_name("[1m]") == "[1m]"\n'
        "\n"
        "\n"
        "def test_opus_5_5_is_a_distinct_minor_never_folded_into_opus_5():\n"
        '    assert normalize_model_name("opus-5-5") == "claude-opus-5-5"\n'
        '    assert normalize_model_name("opus-5") == "claude-opus-5"\n'
        '    assert normalize_model_name("claude-opus-5-5[1m]") != "claude-opus-5"\n',
        1,
    ),
]

#: Every path this module touches (the core derivator unions it with its own).
PATHS: List[str] = sorted({e[0] for e in EDITS})
