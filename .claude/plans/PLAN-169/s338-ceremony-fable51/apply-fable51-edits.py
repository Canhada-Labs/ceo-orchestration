#!/usr/bin/env python3
"""apply-fable51-edits.py — a DERIVACAO do patch da wave-fable51 (PLAN-169, S338).

Este script E o material versionado da cerimonia `adopt-fable-5.1` (ADR-149
Amendment 2, rota (c) ratificada pelo Owner na S338: `claude-fable-5-1`
entra SO no `AVAILABLE_MODELS_WORKING_SET`; VETO floor, fallback e o pin
`model` ficam como estao). Ele aplica TODAS as edicoes da wave sobre uma
arvore em HEAD, com ancora EXATA por edicao e contagem declarada — uma
ancora ausente, ambigua ou ja aplicada e RECUSA nomeada, nunca um "best
effort". O `finalize-fable51.sh` (passo 4a) e o `OWNER-S338-FABLE51-LAND.sh`
(V3) provam que `HEAD + este script == patch` BYTE A BYTE em cada path,
como o 183batch provou `base | jq-frag == settings`.

Por que um script e nao um `.jq`: a wave toca 25 paths de 6 formas
diferentes (JSON gerado do ADR, case-arm de shell, tuplas Python, tabelas
YAML/markdown, uma linha de manifesto sha256). Um unico derivador
deterministico e a menor superficie que reproduz o patch inteiro.

Uso:
    python3 apply-fable51-edits.py --root <arvore-em-HEAD>
    python3 apply-fable51-edits.py --root <arvore> --check-only   (so ancoras)

Saidas: 0 = aplicado (ou, com --check-only, aplicavel); 1 = recusa nomeada;
2 = erro de uso. Stdlib-only, Python >= 3.9, sem PEP 604 em runtime.
"""
from __future__ import annotations

import argparse
import hashlib
import re
import sys
from pathlib import Path
from typing import List, Tuple

NEW_ID = "claude-fable-5-1"
MANIFEST_REL = ".claude/governance/gate-scripts-manifest.txt"
VALIDATE_REL = ".claude/scripts/validate-governance.sh"

SHIPPED_6 = (
    '"claude-opus-4-8","claude-fable-5","claude-sonnet-4-6",'
    '"claude-haiku-4-5","claude-opus-5","claude-sonnet-5"'
)

# --------------------------------------------------------------------------
# (path, ancora EXATA, substituto, ocorrencias esperadas)
# A ordem e a ordem de aplicacao; cada ancora e contada ANTES de qualquer
# escrita (passo 1), entao um refuse deixa a arvore intocada.
# --------------------------------------------------------------------------
EDITS: List[Tuple[str, str, str, int]] = [
    # ---------------------------------------------------------------- ADR-149
    (
        ".claude/adr/ADR-149-model-id-allowlist.md",
        '    "claude-sonnet-5",    # advisory tier target (ADR-157 member; OQ2 migrate-now)\n'
        ")\n",
        '    "claude-sonnet-5",    # advisory tier target (ADR-157 member; OQ2 migrate-now)\n'
        "    # -- Fable 5.1 -- ADR-149 Amendment 2, S338 2026-09-01; APPENDED AT END.\n"
        "    #    Working-set ONLY: not a floor member, not the fallback, not the\n"
        "    #    session pin. The legacy claude-fable-5 stays available. --\n"
        '    "claude-fable-5-1",   # Mythos-class flagship 5.1; dateless id per the models overview\n'
        ")\n",
        1,
    ),
    (
        ".claude/adr/ADR-149-model-id-allowlist.md",
        "- A blocked subagent `model:` override **falls back silently** to the\n"
        "  inherited/default model (documented 2.1.172 semantics) rather than\n"
        "  failing the spawn — fine for the routing floor, but it means frontmatter\n"
        "  pins are not self-verifying; the spawn gate (`check_agent_spawn` /\n"
        "  `VETO_FLOOR_ALLOWED`) remains the enforcement layer for VETO personas.\n",
        "- A blocked subagent `model:` override **falls back silently** to the\n"
        "  inherited/default model (documented 2.1.172 semantics) rather than\n"
        "  failing the spawn — fine for the routing floor, but it means frontmatter\n"
        "  pins are not self-verifying; the spawn gate (`check_agent_spawn` /\n"
        "  `VETO_FLOOR_ALLOWED`) remains the enforcement layer for VETO personas.\n"
        "\n"
        "## Amendment 2 (S338 — Fable 5.1 joins the working set; floor, fallback and pin unchanged)\n"
        "\n"
        "> Authored S338 (2026-09-01) under PLAN-169 (fleet-currency remit, W2.10\n"
        "> class cure: functional surfaces DERIVE from this ADR). Ratified by the\n"
        "> Owner via AskUserQuestion at the S338 opening — **route (c) of three**:\n"
        "> working-set append only. Lands through the `wave-fable51` sentinel ceremony\n"
        "> (`.claude/plans/PLAN-169/wave-fable51-approved.md`).\n"
        "\n"
        "### A2.1 Facts the amendment rests on (models overview, fetched 2026-09-01)\n"
        "\n"
        "- Claude Fable 5.1 launched 2026-09-01 alongside Mythos 5.1 (same\n"
        "  underlying model; Fable carries the additional dual-use safety\n"
        "  measures and is the generally available one).\n"
        "- **API id = alias = `claude-fable-5-1`** — dateless. Every id from the\n"
        "  4.6 generation on is a pinned snapshot, so a date suffix must NEVER be\n"
        "  appended (the S337 recon measured 233 files citing `claude-fable-5`\n"
        "  and 0 citing the 5.1 id; the cure is this data change, not a hunt).\n"
        "- $10 in / $50 out per MTok (equal to Fable 5); 1M context; 128K max\n"
        "  output; knowledge cutoff June 2026; adaptive always-on thinking;\n"
        "  retirement no earlier than 2027-09-01.\n"
        "- **Cache hits on Fable 5.1 are 0.025x the base input price ($0.25/MTok)**\n"
        "  — the pricing page (fetched 2026-09-01) resolves the conflict the S337\n"
        "  recon recorded between the models overview (0.1x) and the launch note;\n"
        "  every other model keeps the standard 0.1x. `budget-summary.py` is the\n"
        "  ONE cost surface that prices cache reads (input-equivalents), so it\n"
        "  gains a per-model multiplier instead of the flat 0.10x that would have\n"
        "  overstated Fable 5.1 cache reads 4x (codex rail r1 P2).\n"
        "- `claude-fable-5` remains available as LEGACY: the change is ADDITIVE.\n"
        "\n"
        "### A2.2 Decision\n"
        "\n"
        "1. `AVAILABLE_MODELS_WORKING_SET` gains `claude-fable-5-1` **at the end**\n"
        "   (A1.1 order rule — no reorder, no removal). The generated\n"
        "   `availableModels` mirrors (`.claude/settings.json`,\n"
        "   `templates/settings/settings.base.json`) follow byte-for-byte via\n"
        "   `generate-available-models.py`; every INDEPENDENT mirror bound by\n"
        "   `test_adr149_validator_parity.py` (validate-governance case-arm,\n"
        "   `tier_policy_cli.VALID_MODEL_IDS`, `smoke-install-parity.sh`\n"
        "   `ALLOWED_MODELS`) carries the same append in the same patch.\n"
        "2. `VETO_FLOOR_ALLOWED` is **unchanged**: Fable 5.1 is selectable, not\n"
        "   VETO-eligible. Routes (a)/(b) — floor membership with or without\n"
        "   migrating the six `agents/*.md` pins — stay open as a FUTURE amendment\n"
        "   that the Owner may ratify after measuring the 5.1 verdict quality;\n"
        "   nothing here pre-empts it.\n"
        "3. `FALLBACK_MODEL_CHAIN` is **unchanged** (`claude-opus-5`).\n"
        "4. The session-default `model` pin stays `claude-opus-5` in all three\n"
        "   adopter-facing mirrors. Flipping it is a SEPARATE decision with its own\n"
        "   blast radius (adopter default cost x2; `upgrade.sh` pin migration;\n"
        "   `test_template_dogfood_parity.py` EXPECTED_PIN) and is not made here.\n"
        "   A maintainer who wants 5.1 as the session default on ONE machine sets\n"
        "   it in `.claude/settings.local.json` (highest-precedence project layer;\n"
        "   the generator `--check` resolves that overlay, A1.2).\n"
        "5. `scripts/upgrade.sh` learns a **`superseded`** list for the\n"
        "   `availableModels` leaf: the 6-id array that v1.2.0 and v1.3.0 SHIPPED\n"
        "   is a frozen historical literal (same doctrine as the pair-rail\n"
        "   `OLD_PAIR_RAIL_CAPS`). Without it the 3-state migration would read\n"
        "   every v1.2.0/v1.3.0 adopter as ADOPTER-CUSTOMIZED and never deliver\n"
        "   the seventh id — SILENTLY: the install/upgrade parity e2e declares\n"
        "   `.claude/settings.json` an ACCEPTED divergence (the two routes\n"
        "   converge on keys, not bytes), so CI would not have noticed. The match\n"
        "   stays byte-exact (values AND order), so a genuinely customized array\n"
        "   is still PRESERVED.\n"
        "6. `tier_policy_cli/learn.py` `_tier_rank` ranks the new id ABOVE\n"
        "   `claude-fable-5` (codex rail r1 P1): an id admitted to\n"
        "   `VALID_MODEL_IDS` but unknown to the ladder ranks -1, so a move away\n"
        "   from it would sign as `promote` and bypass the signed-demote gate.\n"
        "   A parity test now requires every allowlisted id to carry a rank.\n"
        "\n"
        "### A2.3 What this amendment does NOT decide\n"
        "\n"
        "- Cost/quality routing for 5.1 (`_lib/model_routing.py` `_ROUTING_TABLE`\n"
        "  is untouched; debate/arch stay on `claude-opus-5`).\n"
        "- The `hooks/_lib/tier_policy` `MODEL_ID` enum (AEK tier targets, a\n"
        "  different contract from availability — it never carried Fable 5 either).\n"
        "- Automatic model currency (PLAN-176): this amendment is the manual\n"
        "  ceremony that plan would only DETECT the need for, never perform.\n"
        "- Sonnet 5 pricing: the same pricing page states the $2/$10 intro rate\n"
        "  became the STANDARD price (the 2026-09-01 increase to $3/$15 will not\n"
        "  occur). The dated flip in `audit-telemetry.py`, `ceo-cost.py`,\n"
        "  `budget-summary.py` and the sticker rows in `cost-table.yaml` /\n"
        "  `docs/cost-of-operation.md` are therefore stale from today — a\n"
        "  FOLLOW-UP on free surfaces, deliberately outside this amendment.\n"
        "\n"
        "The A1.1 prose sentence *\"the primary session model is `claude-fable-5`\"*\n"
        "is historical (it predates the ADR-181 pin); the pin above is the truth.\n",
        1,
    ),
    # ---------------------------------------------- settings mirrors (generated)
    (
        ".claude/settings.json",
        '    "claude-opus-5",\n'
        '    "claude-sonnet-5"\n'
        "  ],\n"
        '  "_enforce_available_models_comment"',
        '    "claude-opus-5",\n'
        '    "claude-sonnet-5",\n'
        '    "claude-fable-5-1"\n'
        "  ],\n"
        '  "_enforce_available_models_comment"',
        1,
    ),
    (
        "templates/settings/settings.base.json",
        '    "claude-opus-5",\n'
        '    "claude-sonnet-5"\n'
        "  ],\n"
        '  "fallbackModel"',
        '    "claude-opus-5",\n'
        '    "claude-sonnet-5",\n'
        '    "claude-fable-5-1"\n'
        "  ],\n"
        '  "fallbackModel"',
        1,
    ),
    # ------------------------------------- validate-governance.sh (mirror + msg)
    (
        VALIDATE_REL,
        "    # AVAILABLE_MODELS_WORKING_SET (opus-4-8, fable-5, sonnet-4-6,\n"
        "    # haiku-4-5, opus-5, sonnet-5) plus the dated haiku id that agent\n",
        "    # AVAILABLE_MODELS_WORKING_SET (opus-4-8, fable-5, sonnet-4-6,\n"
        "    # haiku-4-5, opus-5, sonnet-5, fable-5-1 — ADR-149 Amendment 2,\n"
        "    # S338) plus the dated haiku id that agent\n",
        1,
    ),
    (
        VALIDATE_REL,
        '        claude-fable-5|claude-opus-4-8|claude-sonnet-4-6|claude-haiku-4-5|claude-haiku-4-5-20251001|claude-opus-5|claude-sonnet-5|"")\n',
        '        claude-fable-5|claude-opus-4-8|claude-sonnet-4-6|claude-haiku-4-5|claude-haiku-4-5-20251001|claude-opus-5|claude-sonnet-5|claude-fable-5-1|"")\n',
        1,
    ),
    (
        VALIDATE_REL,
        "claude-haiku-4-5-20251001, claude-opus-5, claude-sonnet-5, or empty (inherit)\"\n",
        "claude-haiku-4-5-20251001, claude-opus-5, claude-sonnet-5, claude-fable-5-1, or empty (inherit)\"\n",
        1,
    ),
    # ------------------------------------------- tier_policy_cli mirror + test
    (
        ".claude/scripts/tier_policy_cli/_types.py",
        "MODEL_ID = \"Literal['claude-fable-5', 'claude-opus-4-8', 'claude-sonnet-4-6', 'claude-haiku-4-5-20251001', 'claude-opus-5', 'claude-sonnet-5']\"\n",
        "MODEL_ID = \"Literal['claude-fable-5', 'claude-opus-4-8', 'claude-sonnet-4-6', 'claude-haiku-4-5-20251001', 'claude-opus-5', 'claude-sonnet-5', 'claude-fable-5-1']\"\n",
        1,
    ),
    (
        ".claude/scripts/tier_policy_cli/_types.py",
        "# Claude 5 refresh working-set members; additive, historical ids stay.\n"
        "# Independent mirror of the ADR-149 AVAILABLE_MODELS_WORKING_SET\n",
        "# Claude 5 refresh working-set members; additive, historical ids stay.\n"
        "# ADR-149 Amendment 2 (S338): claude-fable-5-1 appended — working-set\n"
        "# only (not a VETO-floor member); additive.\n"
        "# Independent mirror of the ADR-149 AVAILABLE_MODELS_WORKING_SET\n",
        1,
    ),
    (
        ".claude/scripts/tier_policy_cli/_types.py",
        '    "claude-opus-5",\n'
        '    "claude-sonnet-5",\n'
        ")\n",
        '    "claude-opus-5",\n'
        '    "claude-sonnet-5",\n'
        '    "claude-fable-5-1",\n'
        ")\n",
        1,
    ),
    (
        ".claude/scripts/tier_policy_cli/tests/test_types.py",
        "        # ADR-181 (PLAN-163 T1.2d): opus-5 + sonnet-5 added — 6 legal IDs.\n"
        "        self.assertEqual(len(VALID_MODEL_IDS), 6)\n",
        "        # ADR-181 (PLAN-163 T1.2d): opus-5 + sonnet-5 added — 6 legal IDs.\n"
        "        # ADR-149 Amendment 2 (S338): fable-5-1 added — 7 legal IDs.\n"
        "        self.assertEqual(len(VALID_MODEL_IDS), 7)\n",
        1,
    ),
    (
        ".claude/scripts/tier_policy_cli/tests/test_types.py",
        '        self.assertIn("claude-sonnet-5", VALID_MODEL_IDS)\n'
        "\n"
        "    def test_retired_generation_not_valid(self):\n",
        '        self.assertIn("claude-sonnet-5", VALID_MODEL_IDS)\n'
        '        self.assertIn("claude-fable-5-1", VALID_MODEL_IDS)\n'
        "\n"
        "    def test_retired_generation_not_valid(self):\n",
        1,
    ),
    # ----------------------------------------------- smoke-install-parity.sh
    (
        "scripts/local/smoke-install-parity.sh",
        "# frontmatter/env lint only, NOT the availableModels evidence — see [6/6]).\n"
        'ALLOWED_MODELS="claude-opus-4-8 claude-fable-5 claude-sonnet-4-6 claude-haiku-4-5-20251001 claude-opus-5 claude-sonnet-5 haiku sonnet opus inherit"\n',
        "# frontmatter/env lint only, NOT the availableModels evidence — see [6/6]).\n"
        "# ADR-149 Amendment 2 (S338): claude-fable-5-1 appended (working set only).\n"
        'ALLOWED_MODELS="claude-opus-4-8 claude-fable-5 claude-sonnet-4-6 claude-haiku-4-5-20251001 claude-opus-5 claude-sonnet-5 claude-fable-5-1 haiku sonnet opus inherit"\n',
        1,
    ),
    (
        "scripts/local/smoke-install-parity.sh",
        '    "claude-opus-5",\n'
        '    "claude-sonnet-5",\n'
        "]\n"
        "# ADR-149 FALLBACK_MODEL_CHAIN",
        '    "claude-opus-5",\n'
        '    "claude-sonnet-5",\n'
        '    "claude-fable-5-1",  # ADR-149 Amendment 2 (S338) — appended at the end\n'
        "]\n"
        "# ADR-149 FALLBACK_MODEL_CHAIN",
        1,
    ),
    # ---------------------------------------------------------- upgrade.sh
    (
        "scripts/upgrade.sh",
        "# Each registration carries a \"match\" filename used for the idempotent\n"
        "# append (mirrors the H8 jq `_reg` semantics: an event entry whose\n"
        "# hooks[].command references the filename counts as already registered).\n"
        "_T54_BASELINES_JSON='{\n"
        '  "availableModels": {\n'
        '    "old": ["claude-opus-4-8","claude-fable-5","claude-sonnet-4-6","claude-haiku-4-5"],\n'
        '    "new": [' + SHIPPED_6 + "]\n"
        "  },\n",
        "# ADR-149 Amendment 2 (S338): an ARRAY leaf may also carry \"superseded\" —\n"
        "# EVERY previously SHIPPED value that is neither the original OLD baseline\n"
        "# nor the NEW one, as frozen historical literals (the same doctrine as\n"
        "# OLD_PAIR_RAIL_CAPS below). v1.2.0 and v1.3.0 shipped the 6-id\n"
        "# availableModels that was \"new\" until claude-fable-5-1 was appended;\n"
        "# without this list the 3-state policy would read every such adopter as\n"
        "# ADOPTER-CUSTOMIZED and never deliver the seventh id — silently: the\n"
        "# install/upgrade parity e2e declares settings.json an ACCEPTED divergence\n"
        "# (keys, not bytes), so CI would not notice. The match is\n"
        "# byte-exact (values AND order): a genuinely customized array still lands\n"
        "# in the PRESERVED branch.\n"
        "# Each registration carries a \"match\" filename used for the idempotent\n"
        "# append (mirrors the H8 jq `_reg` semantics: an event entry whose\n"
        "# hooks[].command references the filename counts as already registered).\n"
        "_T54_BASELINES_JSON='{\n"
        '  "availableModels": {\n'
        '    "old": ["claude-opus-4-8","claude-fable-5","claude-sonnet-4-6","claude-haiku-4-5"],\n'
        '    "superseded": [[' + SHIPPED_6 + "]],\n"
        '    "new": [' + SHIPPED_6 + ',"claude-fable-5-1"]\n'
        "  },\n",
        1,
    ),
    (
        "scripts/upgrade.sh",
        "    elif cur == spec[\"old\"]:\n"
        "        if not dry:\n"
        "            data[key] = list(spec[\"new\"])\n"
        "        resolved = list(spec[\"new\"])\n"
        "        changed[0] = True\n"
        "        act(\"MIGRATE (matched OLD baseline -> new baseline): \" + key)\n"
        "    else:\n"
        "        warn(\"WARNING: \" + key + \" is ADOPTER-CUSTOMIZED - PRESERVED \"\n",
        "    elif cur == spec[\"old\"]:\n"
        "        if not dry:\n"
        "            data[key] = list(spec[\"new\"])\n"
        "        resolved = list(spec[\"new\"])\n"
        "        changed[0] = True\n"
        "        act(\"MIGRATE (matched OLD baseline -> new baseline): \" + key)\n"
        "    elif cur in spec.get(\"superseded\", []):\n"
        "        # ADR-149 Amendment 2 (S338): a previously SHIPPED baseline\n"
        "        # (frozen literal, byte-exact incl. order) migrates like OLD.\n"
        "        if not dry:\n"
        "            data[key] = list(spec[\"new\"])\n"
        "        resolved = list(spec[\"new\"])\n"
        "        changed[0] = True\n"
        "        act(\"MIGRATE (matched SUPERSEDED shipped baseline -> new baseline): \" + key)\n"
        "    else:\n"
        "        warn(\"WARNING: \" + key + \" is ADOPTER-CUSTOMIZED - PRESERVED \"\n",
        1,
    ),
    # ----------------------------------------------------- cost / telemetry
    (
        ".claude/scripts/cost-table.yaml",
        '    source_url: "https://models.dev/api.json"  # Owner fetch 2026-06-10 sha a6f5cb21; live-confirmed by W0b reconciliation 20/20 calls drift~0.0000\n'
        "  claude-opus-4-8:\n",
        '    source_url: "https://models.dev/api.json"  # Owner fetch 2026-06-10 sha a6f5cb21; live-confirmed by W0b reconciliation 20/20 calls drift~0.0000\n'
        "  claude-fable-5-1:\n"
        "    input_per_mtok: 10.00\n"
        "    output_per_mtok: 50.00\n"
        "    tier: fable\n"
        '    source_url: "https://platform.claude.com/docs/en/about-claude/models/overview"  # ADR-149 Amendment 2 (S338, launch 2026-09-01): Fable 5.1 at the Fable 5 base rate; 1M ctx / 128K out; cache hits 0.025x base ($0.25/MTok, pricing page 2026-09-01) — this table has no cache field, budget-summary.py carries the per-model multiplier\n'
        "  claude-opus-4-8:\n",
        1,
    ),
    (
        ".claude/scripts/audit-telemetry.py",
        '    "claude-fable-5": {"input": 10.00, "output": 50.00},\n',
        '    "claude-fable-5": {"input": 10.00, "output": 50.00},\n'
        '    "claude-fable-5-1": {"input": 10.00, "output": 50.00},  # ADR-149 Amendment 2 (S338): Fable 5.1 at the Fable 5 rate\n',
        1,
    ),
    (
        ".claude/scripts/budget-summary.py",
        '    "claude-fable-5":             {"in": 0.010, "out": 0.050},\n',
        '    "claude-fable-5":             {"in": 0.010, "out": 0.050},\n'
        '    "claude-fable-5-1":           {"in": 0.010, "out": 0.050},  # ADR-149 Amendment 2 (S338)\n',
        1,
    ),
    (
        ".claude/scripts/ceo-cost.py",
        '    "claude-fable-5": {"input_per_mtok": 10.00, "output_per_mtok": 50.00},\n',
        '    "claude-fable-5": {"input_per_mtok": 10.00, "output_per_mtok": 50.00},\n'
        '    "claude-fable-5-1": {"input_per_mtok": 10.00, "output_per_mtok": 50.00},  # ADR-149 Amendment 2 (S338)\n',
        1,
    ),
    (
        ".claude/scripts/value-dashboard.py",
        '    "claude-fable-5":              {"in": 0.010, "out": 0.050},\n',
        '    "claude-fable-5":              {"in": 0.010, "out": 0.050},\n'
        '    "claude-fable-5-1":            {"in": 0.010, "out": 0.050},  # ADR-149 Amendment 2 (S338)\n',
        1,
    ),
    (
        ".claude/scripts/detectors/overpowered.py",
        "# historical ids retained for audit-log replay (ADR-142).\n"
        "_LARGE_MODELS = frozenset({\n"
        '    "claude-opus-5",\n'
        '    "claude-fable-5",\n',
        "# ADR-149 Amendment 2 (S338): += claude-fable-5-1 (Fable 5.1 flagship).\n"
        "# historical ids retained for audit-log replay (ADR-142).\n"
        "_LARGE_MODELS = frozenset({\n"
        '    "claude-opus-5",\n'
        '    "claude-fable-5",\n'
        '    "claude-fable-5-1",\n',
        1,
    ),
    (
        ".claude/scripts/detectors/wasteful_thinking.py",
        "_TARGET_MODELS = frozenset({\n"
        '    "claude-opus-5",\n'
        '    "claude-fable-5",\n',
        "_TARGET_MODELS = frozenset({\n"
        '    "claude-opus-5",\n'
        '    "claude-fable-5",\n'
        '    "claude-fable-5-1",  # ADR-149 Amendment 2 (S338)\n',
        1,
    ),
    (
        ".claude/scripts/optimizer/model_normalize.py",
        '    "fable-5": "claude-fable-5",\n',
        '    "fable-5": "claude-fable-5",\n'
        '    "fable-5-1": "claude-fable-5-1",  # ADR-149 Amendment 2 (S338): a distinct minor, never folded into fable-5\n',
        1,
    ),
    # ------------------------------------------------------------- tests
    (
        ".claude/scripts/tests/test_model_fleet_presence.py",
        "_NEW_FLEET = (\n"
        '    "claude-opus-4-8",\n'
        '    "claude-opus-4-8-fast",\n'
        '    "claude-fable-5",\n',
        "#: claude-fable-5-1 added by ADR-149 Amendment 2 (S338) — Fable 5.1 at the\n"
        "#: Fable 5 rate; the same silent-$0 class this file exists to keep honest.\n"
        "_NEW_FLEET = (\n"
        '    "claude-opus-4-8",\n'
        '    "claude-opus-4-8-fast",\n'
        '    "claude-fable-5",\n'
        '    "claude-fable-5-1",\n',
        1,
    ),
    (
        ".claude/scripts/tests/test_model_fleet_presence.py",
        '            "claude-fable-5": (10.00, 50.00),\n'
        '            "claude-opus-5": (5.00, 25.00),\n'
        '            "claude-opus-5-fast": (10.00, 50.00),\n'
        "            # Base-row intro rate; the 2026-08-31 flip is event-date-aware\n",
        '            "claude-fable-5": (10.00, 50.00),\n'
        '            "claude-fable-5-1": (10.00, 50.00),  # ADR-149 A2 (S338)\n'
        '            "claude-opus-5": (5.00, 25.00),\n'
        '            "claude-opus-5-fast": (10.00, 50.00),\n'
        "            # Base-row intro rate; the 2026-08-31 flip is event-date-aware\n",
        1,
    ),
    (
        ".claude/scripts/tests/test_model_fleet_presence.py",
        '        for model in ("claude-fable-5", "claude-opus-5"):\n',
        '        for model in ("claude-fable-5", "claude-fable-5-1", "claude-opus-5"):\n',
        2,
    ),
    (
        ".claude/scripts/tests/test_model_fleet_presence.py",
        '            "claude-fable-5": (0.010, 0.050),\n'
        '            "claude-sonnet-5": (0.002, 0.010),  # base row; dated flip below\n',
        '            "claude-fable-5": (0.010, 0.050),\n'
        '            "claude-fable-5-1": (0.010, 0.050),  # ADR-149 A2 (S338)\n'
        '            "claude-sonnet-5": (0.002, 0.010),  # base row; dated flip below\n',
        1,
    ),
    (
        ".claude/scripts/tests/test_model_fleet_presence.py",
        "    def test_opus48_fast_row(self) -> None:\n",
        "    def test_fable51_row(self) -> None:\n"
        "        \"\"\"ADR-149 Amendment 2 (S338): Fable 5.1 priced at the Fable 5 rate.\"\"\"\n"
        '        text = self._block("claude-fable-5-1")\n'
        '        self.assertIn("input_per_mtok: 10.00", text)\n'
        '        self.assertIn("output_per_mtok: 50.00", text)\n'
        "\n"
        "    def test_opus48_fast_row(self) -> None:\n",
        1,
    ),
    (
        ".claude/scripts/tests/test_generate_available_models.py",
        '    "claude-opus-5",\n'
        '    "claude-sonnet-5",\n'
        "]\n"
        "\n"
        'AMENDED_ADR = """# ADR-149 fixture (amended)\n',
        '    "claude-opus-5",\n'
        '    "claude-sonnet-5",\n'
        '    "claude-fable-5-1",  # ADR-149 Amendment 2, S338\n'
        "]\n"
        "\n"
        'AMENDED_ADR = """# ADR-149 fixture (amended)\n',
        1,
    ),
    (
        ".claude/scripts/tests/test_generate_available_models.py",
        '    "claude-opus-5",      # ADR-181 refresh\n'
        '    "claude-sonnet-5",    # ADR-181 refresh\n'
        ")\n",
        '    "claude-opus-5",      # ADR-181 refresh\n'
        '    "claude-sonnet-5",    # ADR-181 refresh\n'
        '    "claude-fable-5-1",   # ADR-149 Amendment 2, S338\n'
        ")\n",
        1,
    ),
    (
        ".claude/scripts/tests/test_a4_pricing_doctrine.py",
        '    "claude-fable-5": (10.00, 50.00),\n'
        '    "claude-haiku-4-5": (1.00, 5.00),\n'
        "}\n",
        '    "claude-fable-5": (10.00, 50.00),\n'
        '    # ADR-149 Amendment 2 (S338): DOCUMENTARY evidence, not the PLAN-137\n'
        '    # live probe — pricing page (2026-09-01) §Long context: 4.6+ models\n'
        '    # carry the full 1M window at standard pricing (provider-pricing.md row).\n'
        '    "claude-fable-5-1": (10.00, 50.00),\n'
        '    "claude-haiku-4-5": (1.00, 5.00),\n'
        "}\n",
        1,
    ),
    (
        ".claude/hooks/tests/test_adr149_validator_parity.py",
        '        self.assertIn("claude-sonnet-5", ws, "ADR-181 refresh id missing")\n'
        "        self.assertNotIn(RETIRED_ID, ws)\n",
        '        self.assertIn("claude-sonnet-5", ws, "ADR-181 refresh id missing")\n'
        "        self.assertIn(\n"
        '            "claude-fable-5-1", ws,\n'
        '            "ADR-149 Amendment 2 (S338) id missing from the working set",\n'
        "        )\n"
        '        self.assertEqual(ws[-1], "claude-fable-5-1", "A2 append must be LAST")\n'
        "        self.assertNotIn(RETIRED_ID, ws)\n",
        1,
    ),
    (
        ".claude/scripts/tests/test_upgrade_settings_migration.py",
        "class TestDefaultModeBranches(_MigrationHarness):\n",
        "class TestSupersededShippedBaseline(_MigrationHarness):\n"
        "    \"\"\"ADR-149 Amendment 2 (S338) — the ``superseded`` list of an ARRAY leaf.\n"
        "\n"
        "    v1.2.0 and v1.3.0 SHIPPED the 6-id availableModels that was the NEW\n"
        "    baseline until claude-fable-5-1 was appended. Under the 3-state policy\n"
        "    that array is neither OLD nor NEW, so without ``superseded`` every such\n"
        "    adopter would be read as ADOPTER-CUSTOMIZED and never receive the\n"
        "    seventh id — silently, because the install/upgrade parity e2e treats\n"
        "    settings.json as an ACCEPTED divergence (keys, not bytes). The list\n"
        "    carries frozen historical literals, the\n"
        "    same doctrine as SUPERSEDED_SHIPPED_CAPS below; the match is byte-exact\n"
        "    (values AND order), so a reordered array is still PRESERVED.\n"
        "    \"\"\"\n"
        "\n"
        "    #: The availableModels array v1.2.0 AND v1.3.0 shipped (frozen literal:\n"
        "    #: `git show v1.3.0:templates/settings/settings.base.json`). Must stay\n"
        "    #: declared as superseded for as long as such installs exist.\n"
        "    SHIPPED_V12_V13_AVAILABLE = [\n"
        '        "claude-opus-4-8", "claude-fable-5", "claude-sonnet-4-6",\n'
        '        "claude-haiku-4-5", "claude-opus-5", "claude-sonnet-5",\n'
        "    ]\n"
        "\n"
        "    def test_shipped_6_id_array_is_declared_superseded(self) -> None:\n"
        '        spec = baselines()["availableModels"]\n'
        '        self.assertIn(self.SHIPPED_V12_V13_AVAILABLE, spec.get("superseded", []))\n'
        "        # Non-vacuity: it is neither the OLD nor the NEW baseline.\n"
        '        self.assertNotEqual(self.SHIPPED_V12_V13_AVAILABLE, spec["old"])\n'
        '        self.assertNotEqual(self.SHIPPED_V12_V13_AVAILABLE, spec["new"])\n'
        "\n"
        "    def test_new_baseline_appends_fable51_last(self) -> None:\n"
        '        new = baselines()["availableModels"]["new"]\n'
        '        self.assertEqual(new[-1], "claude-fable-5-1")\n'
        "        self.assertEqual(new[:-1], self.SHIPPED_V12_V13_AVAILABLE,\n"
        '                         "order is normative: append at the END only")\n'
        "\n"
        "    def test_every_superseded_array_migrates_to_new(self) -> None:\n"
        '        for key in ("availableModels", "fallbackModel"):\n'
        '            for sup in baselines()[key].get("superseded", []):\n'
        "                with self.subTest(key=key, superseded=sup):\n"
        "                    self.setUp()\n"
        "                    self.seed({key: list(sup)})\n"
        "                    proc = self.run_migration()\n"
        "                    self.assertEqual(self.read_settings()[key],\n"
        '                                     baselines()[key]["new"])\n'
        "                    self.assertIn(\n"
        '                        "MIGRATE (matched SUPERSEDED shipped baseline -> "\n'
        '                        "new baseline): " + key,\n'
        "                        proc.stdout,\n"
        "                    )\n"
        '                    self.assertNotIn("WARNING: " + key + " is ADOPTER-CUSTOMIZED",\n'
        "                                     proc.stderr)\n"
        "\n"
        "    def test_availableModels_superseded_is_exercised(self) -> None:\n"
        "        \"\"\"The loop above must not pass vacuously on an empty list.\"\"\"\n"
        '        self.assertTrue(baselines()["availableModels"].get("superseded"))\n'
        "\n"
        "    def test_reordered_superseded_is_customized_and_preserved(self) -> None:\n"
        '        sup = list(baselines()["availableModels"]["superseded"][0])\n'
        "        custom = list(reversed(sup))\n"
        "        self.assertNotEqual(custom, sup)\n"
        '        self.seed({"availableModels": custom})\n'
        "        proc = self.run_migration()\n"
        '        self.assertEqual(self.read_settings()["availableModels"], custom)\n'
        '        self.assertIn("WARNING: availableModels is ADOPTER-CUSTOMIZED",\n'
        "                      proc.stderr)\n"
        "\n"
        "    def test_second_run_after_superseded_migration_is_noop(self) -> None:\n"
        '        sup = baselines()["availableModels"]["superseded"][0]\n'
        '        self.seed({"availableModels": list(sup)})\n'
        "        self.run_migration()\n"
        "        first = self.settings_path.read_bytes()\n"
        "        proc = self.run_migration()\n"
        "        self.assertEqual(self.settings_path.read_bytes(), first)\n"
        '        self.assertIn("OK (already at new baseline): availableModels",\n'
        "                      proc.stdout)\n"
        "\n"
        "\n"
        "class TestDefaultModeBranches(_MigrationHarness):\n",
        1,
    ),
    # ------------------------------------ codex rail r1 P1: tier ladder rank
    (
        ".claude/scripts/tier_policy_cli/learn.py",
        '        "claude-fable-5": 6,  # ADR-149 flagship (Mythos-class, above Opus)\n'
        "    }\n",
        '        "claude-fable-5": 6,  # ADR-149 flagship (Mythos-class, above Opus)\n'
        '        "claude-fable-5-1": 7,  # ADR-149 Amendment 2 (S338): Fable 5.1, above Fable 5\n'
        "    }\n",
        1,
    ),
    (
        ".claude/scripts/tier_policy_cli/tests/test_learn_mutation.py",
        "    def test_kill_direction_promote_vs_demote(self):\n",
        "    def test_every_valid_model_id_has_a_rank(self):\n"
        "        \"\"\"ADR-149 Amendment 2 (S338, codex rail r1 P1): an id admitted to\n"
        "        VALID_MODEL_IDS but unknown to ``_tier_rank`` ranks -1, so a move\n"
        "        AWAY from it signs as \"promote\" and sails past the signed-demote\n"
        "        gate. Every allowlisted id must carry a rank.\"\"\"\n"
        "        for model_id in VALID_MODEL_IDS:\n"
        "            self.assertGreaterEqual(learn._tier_rank(model_id), 0, model_id)\n"
        "\n"
        "    def test_kill_fable51_ranks_above_fable5(self):\n"
        "        \"\"\"Fable 5.1 is the newer flagship: above Fable 5 and Opus 5;\n"
        "        moving off it is a demote (needs a signature).\"\"\"\n"
        '        self.assertGreater(learn._tier_rank("claude-fable-5-1"),\n'
        '                           learn._tier_rank("claude-fable-5"))\n'
        "        self.assertEqual(\n"
        '            learn._direction("claude-fable-5-1", "claude-opus-5"), "demote"\n'
        "        )\n"
        "        self.assertEqual(\n"
        '            learn._direction("claude-fable-5", "claude-fable-5-1"), "promote"\n'
        "        )\n"
        "\n"
        "    def test_kill_direction_promote_vs_demote(self):\n",
        1,
    ),
    # ------------------------- codex rail r1 P2: per-model cache-read multiplier
    (
        ".claude/scripts/budget-summary.py",
        "def _read_native_spawn(\n"
        "    transcript: Path,\n",
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
        "    \"\"\"Cache-read multiplier for ``model_id`` (0.10x unless overridden).\"\"\"\n"
        "    return _CACHE_READ_MULTIPLIER_OVERRIDES.get(\n"
        "        model_id, _CACHE_READ_MULTIPLIER_DEFAULT\n"
        "    )\n"
        "\n"
        "\n"
        "def _read_native_spawn(\n"
        "    transcript: Path,\n",
        1,
    ),
    (
        ".claude/scripts/budget-summary.py",
        "    # Cache classes are BILLABLE (docs/provider-pricing.md: read @0.10x\n"
        "    # input, write @1.25x on the 5m TTL and @2.00x on the 1h TTL). When the\n",
        "    # Cache classes are BILLABLE (docs/provider-pricing.md: read @0.10x\n"
        "    # input — 0.025x on Fable 5.1, see _CACHE_READ_MULTIPLIER_OVERRIDES —,\n"
        "    # write @1.25x on the 5m TTL and @2.00x on the 1h TTL). When the\n",
        1,
    ),
    (
        ".claude/scripts/budget-summary.py",
        "    cache_equiv_in = int(\n"
        '        0.10 * sums["cache_read_input_tokens"]\n',
        "    cache_equiv_in = int(\n"
        '        _cache_read_multiplier(model_id) * sums["cache_read_input_tokens"]\n',
        1,
    ),
    (
        ".claude/scripts/budget-summary.py",
        '        "                    (cache priced as input-equivalents: read @0.10x,"\n',
        '        "                    (cache priced as input-equivalents: read @0.10x"\n'
        '        " — 0.025x on Fable 5.1 —,"\n',
        1,
    ),
    (
        ".claude/scripts/tests/test_model_fleet_presence.py",
        "    def test_sonnet5_dated_compute_cost(self) -> None:\n"
        "        \"\"\"W2 P2a: compute_cost_usd honours the event's own ts.\"\"\"\n",
        "    def test_fable51_cache_read_multiplier(self) -> None:\n"
        "        \"\"\"ADR-149 A2 (S338): Fable 5.1 cache hits are 0.025x base input\n"
        "        (pricing page 2026-09-01); every other fleet id keeps 0.10x.\"\"\"\n"
        "        self.assertAlmostEqual(\n"
        '            self.mod._cache_read_multiplier("claude-fable-5-1"), 0.025)\n'
        '        for model in ("claude-fable-5", "claude-opus-5", "claude-sonnet-5",\n'
        '                      "some-unknown-model"):\n'
        "            self.assertAlmostEqual(self.mod._cache_read_multiplier(model), 0.10)\n"
        "\n"
        "    def test_sonnet5_dated_compute_cost(self) -> None:\n"
        "        \"\"\"W2 P2a: compute_cost_usd honours the event's own ts.\"\"\"\n",
        1,
    ),
    (
        "docs/provider-pricing.md",
        "Source: Anthropic prompt-caching docs (write 1.25× at the 5-minute TTL, 2.0× at\n"
        "the 1-hour TTL; read 0.10× regardless of tier). Last verified 2026-06-02 for\n",
        "Source: Anthropic prompt-caching docs (write 1.25× at the 5-minute TTL, 2.0× at\n"
        "the 1-hour TTL; read 0.10× regardless of tier — EXCEPT Claude Fable 5.1 /\n"
        "Mythos 5.1, whose cache hits are 0.025× base = $0.25/MTok: pricing page\n"
        "2026-09-01, ADR-149 Amendment 2; `budget-summary.py` carries the per-model\n"
        "multiplier). Last verified 2026-06-02 for\n",
        1,
    ),
    # -------------- codex rail r2 P2-a: ambiguous meta alias -> transcript model
    (
        ".claude/scripts/budget-summary.py",
        "    field degrades the record — it never raises. Model precedence:\n"
        "    ``meta.model`` first, else the first ``message.model`` seen in the\n"
        "    transcript (the workflow-path metas carry NO model at all).\n"
        "    \"\"\"\n",
        "    field degrades the record — it never raises. Model precedence:\n"
        "    ``meta.model`` first, else the first ``message.model`` seen in the\n"
        "    transcript (the workflow-path metas carry NO model at all). A\n"
        "    ``meta.model`` that resolves to NOTHING (a bare family alias such as\n"
        "    ``fable`` once the registry holds two Fable ids — ADR-149 Amendment\n"
        "    2) falls back to the transcript's exact ``message.model``: exact\n"
        "    evidence beats an ambiguous alias, and neither is ever guessed.\n"
        "    \"\"\"\n",
        1,
    ),
    (
        ".claude/scripts/budget-summary.py",
        "    model_raw = meta_model or transcript_model\n"
        "    model_id = _normalize_model_id(model_raw, pricing=pricing)\n",
        "    model_raw = meta_model or transcript_model\n"
        "    model_id = _normalize_model_id(model_raw, pricing=pricing)\n"
        "    if (\n"
        "        model_id is None\n"
        "        and meta_model\n"
        "        and transcript_model\n"
        "        and transcript_model.strip().lower() != meta_model.strip().lower()\n"
        "    ):\n"
        "        # ADR-149 Amendment 2 (S338, codex rail r2 P2): a bare family\n"
        "        # alias in the meta (\"fable\") turned AMBIGUOUS once the registry\n"
        "        # held two Fable ids, and the doctrine never guesses a version.\n"
        "        # The transcript's own message.model is exact evidence, not a\n"
        "        # guess — fall back to it. Still unresolved => TBD, as before.\n"
        "        model_raw = transcript_model\n"
        "        model_id = _normalize_model_id(model_raw, pricing=pricing)\n",
        1,
    ),
    (
        ".claude/scripts/tests/test_model_fleet_presence.py",
        "    def test_sonnet5_dated_compute_cost(self) -> None:\n"
        "        \"\"\"W2 P2a: compute_cost_usd honours the event's own ts.\"\"\"\n",
        "    def test_bare_fable_alias_is_ambiguous_and_versioned_alias_resolves(self) -> None:\n"
        "        \"\"\"ADR-149 A2 (S338, codex r2 P2): with two Fable ids in the\n"
        "        registry the bare family alias resolves to NOTHING (never guess a\n"
        "        version); the versioned aliases and exact ids still resolve.\"\"\"\n"
        '        self.assertIsNone(self.mod._normalize_model_id("fable"))\n'
        '        self.assertEqual(self.mod._normalize_model_id("fable-5-1"), "claude-fable-5-1")\n'
        '        self.assertEqual(self.mod._normalize_model_id("fable-5"), "claude-fable-5")\n'
        '        self.assertEqual(self.mod._normalize_model_id("claude-fable-5-1[1m]"),\n'
        '                         "claude-fable-5-1")\n'
        "\n"
        "    def test_native_spawn_ambiguous_meta_alias_falls_back_to_transcript(self) -> None:\n"
        "        \"\"\"ADR-149 A2 (S338, codex r2 P2): meta.model=\"fable\" (measured in\n"
        "        native metas) must not turn the spawn into cost TBD when the\n"
        "        transcript names the exact model.\"\"\"\n"
        "        import tempfile\n"
        "        from pathlib import Path\n"
        "        with tempfile.TemporaryDirectory() as td:\n"
        '            tr = Path(td) / "agent-x.jsonl"\n'
        '            tr.write_text(\n'
        '                \'{"timestamp": "2026-09-01T00:00:00Z", "message": \'\n'
        '                \'{"model": "claude-fable-5-1", "usage": {"input_tokens": 1000000, \'\n'
        '                \'"output_tokens": 0, "cache_read_input_tokens": 1000000}}}\\n\',\n'
        '                encoding="utf-8",\n'
        "            )\n"
        '            (Path(td) / "agent-x.meta.json").write_text(\n'
        '                \'{"agentType": "t", "spawnDepth": 1, "model": "fable"}\',\n'
        '                encoding="utf-8",\n'
        "            )\n"
        '            rec = self.mod._read_native_spawn(tr, "native", "sess")\n'
        "        self.assertIsNotNone(rec)\n"
        '        self.assertEqual(rec["model_id"], "claude-fable-5-1")\n'
        '        self.assertFalse(rec["cost_tbd"])\n'
        "        # 1M fresh input at $10 + 1M cache reads at 0.025x ($0.25) == $10.25\n"
        '        self.assertAlmostEqual(rec["cost_usd"], 10.25, places=6)\n'
        "\n"
        "    def test_sonnet5_dated_compute_cost(self) -> None:\n"
        "        \"\"\"W2 P2a: compute_cost_usd honours the event's own ts.\"\"\"\n",
        1,
    ),
    # ------- codex rail r2 P2-b: canonical price_for must not collapse a minor
    (
        ".claude/scripts/build-canonical-models.py",
        "def price_for(\n"
        "    model: str, data: Optional[Dict[str, Any]] = None\n"
        ") -> Tuple[Dict[str, float], bool]:\n",
        "#: A DATE-STAMPED release pin of a known row (`-YYYYMMDD`). Only this shape\n"
        "#: may resolve through the prefix rule in price_for — a MINOR version\n"
        "#: (`claude-fable-5-1`) is a different model with its own rate card\n"
        "#: (ADR-149 Amendment 2, S338: cache read 0.025x, not 0.1x).\n"
        '_DATED_SUFFIX_RE = re.compile(r"^\\d{8}$")\n'
        "\n"
        "\n"
        "def price_for(\n"
        "    model: str, data: Optional[Dict[str, Any]] = None\n"
        ") -> Tuple[Dict[str, float], bool]:\n",
        1,
    ),
    (
        ".claude/scripts/build-canonical-models.py",
        "    # 2) prefix match (a dated id `claude-opus-4-8-20260101` resolves to the\n"
        "    #    base `claude-opus-4-8` row) — longest prefix wins.\n"
        "    best: Optional[Tuple[str, Dict[str, Any]]] = None\n"
        "    for mid, row in models.items():\n"
        "        if key.startswith(mid.lower() + \"-\") and (best is None or len(mid) > len(best[0])):\n"
        "            best = (mid, row)\n",
        "    # 2) prefix match — ONLY a DATE-STAMPED release pin of a known row\n"
        "    #    (`claude-opus-4-8-20260101` resolves to the base `claude-opus-4-8`\n"
        "    #    row); longest prefix wins. ADR-149 Amendment 2 (S338, codex rail\n"
        "    #    r2 P2): a MINOR version (`claude-fable-5-1`) is a different model\n"
        "    #    with its own rate card and must NOT collapse onto the\n"
        "    #    `claude-fable-5` row — it resolves UNKNOWN (flag, never guess)\n"
        "    #    until the Owner re-fetches the table.\n"
        "    best: Optional[Tuple[str, Dict[str, Any]]] = None\n"
        "    for mid, row in models.items():\n"
        "        if not key.startswith(mid.lower() + \"-\"):\n"
        "            continue\n"
        "        if not _DATED_SUFFIX_RE.match(key[len(mid) + 1:]):\n"
        "            continue\n"
        "        if best is None or len(mid) > len(best[0]):\n"
        "            best = (mid, row)\n",
        1,
    ),
    (
        ".claude/scripts/tests/test_build_canonical_models.py",
        "    def test_fail_open_on_missing_data(self):\n",
        "    def test_minor_version_does_not_collapse_onto_base_row(self):\n"
        "        # ADR-149 Amendment 2 (S338, codex rail r2 P2): `claude-fable-5-1` is\n"
        "        # a MINOR version with its own rate card (cache read 0.025x), not a\n"
        "        # dated pin of `claude-fable-5`. Without an explicit row it must\n"
        "        # resolve UNKNOWN (flag, never guess); the dated pin keeps resolving.\n"
        "        data = _sample_data()\n"
        '        minor_price, minor_known = bcm.price_for("claude-opus-4-8-1", data=data)\n'
        "        self.assertFalse(minor_known)\n"
        '        self.assertEqual(minor_price["cache_read_per_mtok"], 0.0)\n'
        '        dated_price, dated_known = bcm.price_for("claude-opus-4-8-20260101", data=data)\n'
        "        self.assertTrue(dated_known)\n"
        '        self.assertEqual(dated_price["input_per_mtok"], 5.0)\n'
        "        shipped = bcm.load_canonical_models_safe()\n"
        "        if shipped is not None:\n"
        '            price, known = bcm.price_for("claude-fable-5-1", data=shipped)\n'
        "            self.assertFalse(known, \"the shipped table has no 5.1 row — it must not\"\n"
        "                                    \" borrow the claude-fable-5 cache rate\")\n"
        '            self.assertEqual(price["cache_read_per_mtok"], 0.0)\n'
        "\n"
        "    def test_fail_open_on_missing_data(self):\n",
        1,
    ),
    # ------------ codex rail r3 P1: success-receipt price mirror (pre-gen-5 stale)
    (
        ".claude/scripts/success-receipt.py",
        "#: Pricing table mirror — kept in sync by hand with budget-summary.py\n"
        "#: defaults so the receipt is deterministic when budget-summary is not\n"
        "#: importable (e.g. early Wave 2 staging).\n"
        "_DEFAULT_PRICING: Dict[str, Dict[str, float]] = {\n"
        '    "claude-opus-4-7":   {"in": 0.015, "out": 0.075},\n',
        "#: Pricing table mirror — kept in sync by hand with budget-summary.py\n"
        "#: defaults so the receipt is deterministic when budget-summary is not\n"
        "#: importable (e.g. early Wave 2 staging).\n"
        "#: ADR-149 Amendment 2 (S338, codex rail r3 P1): the mirror had NO gen-5\n"
        "#: row (nor opus-4-8), so in a MIXED session a known model set\n"
        "#: cost_known=True while every current-fleet event was silently omitted\n"
        "#: from the numeric total (1M Fable input == $10 dropped). Current fleet\n"
        "#: rows added at the budget-summary per-1k rates (fable 5.1 == fable 5\n"
        "#: base rate; sonnet-5 $2/$10 is the standard price per the 2026-09-01\n"
        "#: pricing page); historical rows retained (ADR-142 replay).\n"
        "_DEFAULT_PRICING: Dict[str, Dict[str, float]] = {\n"
        '    "claude-fable-5-1":   {"in": 0.010, "out": 0.050},\n'
        '    "claude-fable-5":     {"in": 0.010, "out": 0.050},\n'
        '    "claude-opus-5":      {"in": 0.005, "out": 0.025},\n'
        '    "claude-opus-5-fast": {"in": 0.010, "out": 0.050},\n'
        '    "claude-sonnet-5":    {"in": 0.002, "out": 0.010},\n'
        '    "claude-opus-4-8":    {"in": 0.005, "out": 0.025},\n'
        '    "claude-opus-4-8-fast": {"in": 0.010, "out": 0.050},\n'
        '    "claude-sonnet-4-6":  {"in": 0.003, "out": 0.015},\n'
        '    "claude-haiku-4-5":   {"in": 0.001, "out": 0.005},\n'
        '    "claude-opus-4-7":   {"in": 0.015, "out": 0.075},\n',
        1,
    ),
    (
        ".claude/scripts/tests/test_model_fleet_presence.py",
        "class TestCostTableFleetPresence(TestEnvContext):\n",
        "class TestSuccessReceiptFleetPresence(TestEnvContext):\n"
        "    \"\"\"`_DEFAULT_PRICING` (success-receipt.py) knows the current fleet.\n"
        "\n"
        "    ADR-149 Amendment 2 (S338, codex rail r3 P1): this mirror had no gen-5\n"
        "    row at all, so a MIXED session (one known model + fable-5-1 events)\n"
        "    emitted a numeric `default-pricing-table` total that silently dropped\n"
        "    every Fable 5.1 token. The presence guard binds it to the fleet.\n"
        "    \"\"\"\n"
        "\n"
        "    @classmethod\n"
        "    def setUpClass(cls):\n"
        "        super().setUpClass()\n"
        '        cls.mod = _load_hyphenated("success_receipt_fleet", "success-receipt.py")\n'
        "\n"
        "    def test_new_fleet_present(self) -> None:\n"
        "        pricing = self.mod._DEFAULT_PRICING\n"
        "        for model in _NEW_FLEET:\n"
        "            self.assertIn(\n"
        "                model, pricing,\n"
        '                "%s missing from success-receipt _DEFAULT_PRICING "\n'
        '                "(ADR-149 A2 / rail r3 P1 presence fix)" % model,\n'
        "            )\n"
        "\n"
        "    def test_per_1k_rates_mirror_budget_summary(self) -> None:\n"
        '        bs = _load_hyphenated("budget_summary_for_receipt", "budget-summary.py")\n'
        "        for model in _NEW_FLEET:\n"
        "            row = self.mod._DEFAULT_PRICING[model]\n"
        "            ref = bs._DEFAULT_PRICING[model]\n"
        '            self.assertAlmostEqual(row["in"], ref["in"], msg="%s in" % model)\n'
        '            self.assertAlmostEqual(row["out"], ref["out"], msg="%s out" % model)\n'
        "\n"
        "    def test_historical_rows_retained(self) -> None:\n"
        "        pricing = self.mod._DEFAULT_PRICING\n"
        '        for model in ("claude-opus-4-7", "claude-opus-4", "claude-sonnet-4-5",\n'
        '                      "claude-sonnet-4", "claude-haiku-4"):\n'
        "            self.assertIn(model, pricing, \"%s dropped (ADR-142 replay)\" % model)\n"
        "\n"
        "    def test_mixed_session_receipt_counts_fable51_spend(self) -> None:\n"
        "        \"\"\"The r3 finding, as a receipt: 1M Fable 5.1 input == $10.00 must be\n"
        "        IN the total, not silently dropped behind a known sonnet event.\"\"\"\n"
        "        events = [\n"
        '            {"action": "agent_spawn", "model": "claude-sonnet-4-5",\n'
        '             "tokens_in": 1000, "tokens_out": 0},\n'
        '            {"action": "agent_spawn", "model": "claude-fable-5-1",\n'
        '             "tokens_in": 1_000_000, "tokens_out": 0},\n'
        "        ]\n"
        "        section = self.mod.build_value_created(events)\n"
        '        self.assertEqual(section["cost_source"], "default-pricing-table")\n'
        "        # sonnet-4-5 1k in @0.003 + fable-5-1 1M in @0.010/1k == 0.003 + 10.0\n"
        '        self.assertAlmostEqual(section["cost_usd"], 10.003, places=4)\n'
        "\n"
        "\n"
        "class TestCostTableFleetPresence(TestEnvContext):\n",
        1,
    ),
    # -------------------------------------------------------------- docs
    (
        "docs/CEO-MODEL-ROUTING.md",
        "```\n"
        '["claude-opus-4-8","claude-fable-5","claude-sonnet-4-6","claude-haiku-4-5","claude-opus-5","claude-sonnet-5"]\n'
        "```\n"
        "\n"
        "**Fallback (`fallbackModel`, OQ1=b — full refresh, no soak):** `[\"claude-opus-5\"]`\n",
        "```\n"
        '["claude-opus-4-8","claude-fable-5","claude-sonnet-4-6","claude-haiku-4-5","claude-opus-5","claude-sonnet-5","claude-fable-5-1"]\n'
        "```\n"
        "\n"
        "> **UPDATED S338 (ADR-149 Amendment 2, 2026-09-01):** `claude-fable-5-1`\n"
        "> (Fable 5.1, $10/$50, 1M ctx) appended to the working set — availability\n"
        "> only. The VETO floor, the fallback chain, the session pin and every row\n"
        "> of the table below are unchanged; 5.1 is selectable, not routed to.\n"
        "\n"
        "**Fallback (`fallbackModel`, OQ1=b — full refresh, no soak):** `[\"claude-opus-5\"]`\n",
        1,
    ),
    (
        "docs/cost-of-operation.md",
        "| `claude-fable-5` (current — Mythos-class flagship) | $10.00 | $50.00 | 2.0× |\n",
        "| `claude-fable-5` (current — Mythos-class flagship) | $10.00 | $50.00 | 2.0× |\n"
        "| `claude-fable-5-1` (current — Mythos-class flagship 5.1; ADR-149 Amendment 2, S338 — selectable, not the pin) | $10.00 | $50.00 | 2.0× |\n",
        1,
    ),
    (
        "docs/provider-pricing.md",
        "| Anthropic  | claude-fable-5          | 0.010      | 0.050       |\n",
        "| Anthropic  | claude-fable-5          | 0.010      | 0.050       |\n"
        "| Anthropic  | claude-fable-5-1        | 0.010      | 0.050       |\n",
        1,
    ),
    (
        "docs/provider-pricing.md",
        "| claude-fable-5 | Y (1M) | **No** | 2026-06-15 |\n",
        "| claude-fable-5 | Y (1M) | **No** | 2026-06-15 |\n"
        "| claude-fable-5-1 | Y (1M) | **No** — documentary: the pricing page (fetched 2026-09-01) §Long context pricing states that Claude 4.6 and later models include the full 1M window at STANDARD pricing; the PLAN-137 live probe was not re-run for 5.1 (ADR-149 Amendment 2, S338) | 2026-09-01 |\n",
        1,
    ),
    (
        "docs/provider-pricing.md",
        "| claude-opus-4-8         | 5.00      | 25.00      | 2026-06-10    | high       |",
        "| claude-fable-5-1        | 10.00     | 50.00      | 2026-09-01    | medium     | https://platform.claude.com/docs/en/about-claude/models/overview (Fable 5.1 launch 2026-09-01; base rate equals Fable 5; cache hits 0.025x base = $0.25/MTok per the pricing page fetched 2026-09-01 — the ONLY model off the standard 0.1x; ADR-149 Amendment 2, S338) |\n"
        "| claude-opus-4-8         | 5.00      | 25.00      | 2026-06-10    | high       |",
        1,
    ),
]

TOUCHED_BY_EDITS = sorted({e[0] for e in EDITS} | {MANIFEST_REL})


class Refuse(Exception):
    pass


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _plan(root: Path) -> None:
    """Passo 1 — conta TODAS as ancoras e recusa antes de qualquer escrita."""
    problems = []
    for rel, old, _new, count in EDITS:
        p = root / rel
        if not p.is_file():
            problems.append("%s: arquivo ausente" % rel)
            continue
        text = p.read_text(encoding="utf-8")
        n = text.count(old)
        if n != count:
            problems.append("%s: ancora encontrada %dx, esperado %d — %r"
                            % (rel, n, count, old[:70]))
    # Ja aplicado? O id novo nao pode existir em NENHUM path tocado (ADR-149
    # incluido): aplicar duas vezes duplicaria linhas em silencio.
    for rel in TOUCHED_BY_EDITS:
        p = root / rel
        if p.is_file() and NEW_ID in p.read_text(encoding="utf-8"):
            problems.append("%s: ja contem %s — arvore ja patchada?" % (rel, NEW_ID))
    m = root / MANIFEST_REL
    if not m.is_file():
        problems.append("%s: ausente" % MANIFEST_REL)
    else:
        lines = [ln for ln in m.read_text(encoding="utf-8").splitlines()
                 if ln.endswith("  " + VALIDATE_REL)]
        if len(lines) != 1:
            problems.append("%s: %d linha(s) para %s, esperado 1"
                            % (MANIFEST_REL, len(lines), VALIDATE_REL))
    if problems:
        raise Refuse("\n".join("  - " + x for x in problems))


def _apply(root: Path) -> List[str]:
    written: List[str] = []
    for rel, old, new, count in EDITS:
        p = root / rel
        text = p.read_text(encoding="utf-8")
        assert text.count(old) == count  # _plan ja garantiu
        p.write_text(text.replace(old, new), encoding="utf-8")
        if rel not in written:
            written.append(rel)
    # Manifesto ADR-192: o membro validate-governance.sh mudou => o sha da
    # linha dele e re-derivado do CONTEUDO pos-edicao (shasum -a 256 -c).
    m = root / MANIFEST_REL
    new_sha = _sha256(root / VALIDATE_REL)
    pat = re.compile(r"^[0-9a-f]{64}  " + re.escape(VALIDATE_REL) + r"$", re.M)
    mtext = m.read_text(encoding="utf-8")
    mtext2, n = pat.subn(new_sha + "  " + VALIDATE_REL, mtext, count=1)
    if n != 1:
        raise Refuse("%s: linha do membro nao re-derivada (n=%d)" % (MANIFEST_REL, n))
    m.write_text(mtext2, encoding="utf-8")
    written.append(MANIFEST_REL)
    return sorted(set(written))


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=None, help="arvore em HEAD a patchar")
    ap.add_argument("--check-only", action="store_true",
                    help="so verifica as ancoras; nao escreve nada")
    ap.add_argument("--list-paths", action="store_true",
                    help="imprime os paths tocados (um por linha) e sai")
    args = ap.parse_args(argv)
    if args.list_paths:
        # Sem --root: a lista e uma propriedade do SCRIPT, nao de uma arvore
        # (o finalize, o SIGN e o LAND a consomem para a bijecao com o EXPECTED).
        for rel in TOUCHED_BY_EDITS:
            print(rel)
        return 0
    if not args.root:
        ap.error("--root e obrigatorio (exceto com --list-paths)")
    root = Path(args.root).resolve()
    if not (root / ".claude").is_dir():
        sys.stderr.write("apply-fable51-edits: --root nao parece um checkout: %s\n" % root)
        return 2
    try:
        _plan(root)
        if args.check_only:
            print("apply-fable51-edits: %d edicao(oes) aplicaveis em %d path(s); nada escrito"
                  % (len(EDITS), len(TOUCHED_BY_EDITS)))
            return 0
        written = _apply(root)
    except Refuse as exc:
        sys.stderr.write("apply-fable51-edits: RECUSADO\n%s\n" % exc)
        return 1
    print("apply-fable51-edits: %d edicao(oes) aplicadas em %d path(s):"
          % (len(EDITS), len(written)))
    for rel in written:
        print("  " + rel)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
