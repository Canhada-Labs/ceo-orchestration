#!/usr/bin/env python3
"""apply-cost-integration.py — DERIVACAO do pack "cost-integration" (PLAN-186
W0, AC-1b), S340.

`ceo-cost.py` e `budget-summary.py` passam a derivar seus totais PRIMARIOS
de `message.usage` dos transcripts, atraves do instrumento
`.claude/scripts/ceo-cost-transcripts.py`; o audit log continua computado e
impresso, rotulado, como fonte SECUNDARIA. `--source audit` restaura a
renderizacao anterior BYTE A BYTE.

Este script E o patch: cada edicao carrega ancora EXATA + contagem esperada,
todo o plano e montado ANTES da primeira escrita, e ancora ausente/ambigua/
ja-aplicada e RECUSA nomeada (nunca best-effort). Arquivo novo cujo destino
ja existe tambem e recusa.

Uso:
    python3 apply-cost-integration.py --root <arvore-em-HEAD>
    python3 apply-cost-integration.py --root <arvore> --check-only
    python3 apply-cost-integration.py --list-paths

Saidas: 0 = aplicado (ou aplicavel); 1 = recusa nomeada; 2 = erro de uso.
Stdlib-only, Python >= 3.9, sem PEP 604 em runtime.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional, Tuple

PAYLOAD_DIR = Path(__file__).resolve().parent / "payload"

# Arquivos NOVOS: (path relativo, origem em payload/)
NEW_FILES: List[str] = [
    ".claude/scripts/tests/test_ceo_cost_integration.py",
]

# ---------------------------------------------------------------------------
# Blocos reutilizados
# ---------------------------------------------------------------------------

_LOADER_BLOCK = '''
# ---------------------------------------------------------------------------
# PLAN-186 W0 (AC-1b) — transcripts as the PRIMARY cost source
# ---------------------------------------------------------------------------
#
# The audit log is a GOVERNANCE ledger (agent_spawn rows; tokens_in/out on
# them are best-effort and frequently absent). The real token ledger is the
# harness-native transcript corpus — `message.usage` per assistant turn —
# which `.claude/scripts/ceo-cost-transcripts.py` reads with the full
# input / output / cache-read / cache-write-5m / cache-write-1h split and
# per-model prices. This module consumes that instrument through its
# programmatic API and prints BOTH sources, labelled, side by side.
# `--source audit` restores the pre-PLAN-186 rendering byte-for-byte.
#
# SCOPE NOTE (deliberate, not an oversight): this repo carries THREE
# independent pricing tables — `ceo-cost.py::_DEFAULT_PRICING`, the model
# registry behind `budget-summary.py::compute_cost_usd`, and the
# instrument's `_EMBEDDED_PRICING` / `cost-table.yaml` loader. Unifying them
# is a separate wave. This integration only REUSES what the instrument
# already exposes: the transcripts block is priced by the instrument, the
# audit block by whatever priced it before, and each block says so.
#
# The loader below is the one thing that cannot live in the instrument: its
# filename is hyphenated, so every caller needs its own importlib bootstrap.
# Everything else (root resolution, collection, rendering) is delegated, so
# the two callers cannot drift apart.

_TRANSCRIPTS_MODULE_NAME = "ceo_cost_transcripts"
_TRANSCRIPTS_FILENAME = "ceo-cost-transcripts.py"


def load_transcripts_instrument():
    """Import `ceo-cost-transcripts.py` from next to this file, or None.

    Fail-soft by construction: an unimportable instrument degrades the
    primary source to a labelled note, it never breaks the audit rollup.
    """
    cached = sys.modules.get(_TRANSCRIPTS_MODULE_NAME)
    if cached is not None:
        return cached
    src = Path(__file__).resolve().parent / _TRANSCRIPTS_FILENAME
    if not src.is_file():
        return None
    try:
        spec = importlib.util.spec_from_file_location(
            _TRANSCRIPTS_MODULE_NAME, src
        )
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        # Registered BEFORE exec_module: with `from __future__ import
        # annotations`, @dataclass resolves sys.modules[cls.__module__] at
        # class-definition time and blows up on a missing entry.
        sys.modules[_TRANSCRIPTS_MODULE_NAME] = mod
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        sys.modules.pop(_TRANSCRIPTS_MODULE_NAME, None)
        return None


#: Resolved ONCE, from the instrument, so the two callers cannot publish a
#: different `--source` domain or a different banner than the block they
#: render. The literals are a fail-soft fallback for a missing instrument
#: (argparse needs a concrete tuple at parser-build time) and are asserted
#: equal to the instrument's in test_ceo_cost_integration.py.
_TX_MODULE = load_transcripts_instrument()
SOURCE_CHOICES = (
    _TX_MODULE.SOURCE_CHOICES
    if _TX_MODULE is not None
    else ("transcripts", "audit", "both")
)
AUDIT_BANNER = (
    _TX_MODULE.AUDIT_BANNER
    if _TX_MODULE is not None
    else "=== SOURCE: AUDIT LOG (governance ledger -- SECONDARY) ==="
)
ROOT_ENV = (
    _TX_MODULE.ROOT_ENV
    if _TX_MODULE is not None
    else "CEO_COST_TRANSCRIPTS_DIR"
)


def transcripts_root(root_arg: Optional[str] = None) -> Optional[Path]:
    """Resolve the transcripts corpus root (flag > env > shared resolver)."""
    mod = load_transcripts_instrument()
    if mod is None:
        return Path(root_arg) if root_arg else None
    return mod.resolve_root(root_arg)


def _tx_audit_pinned(path_arg: Optional[str] = None) -> bool:
    """True when the SECONDARY (audit) ledger was pointed at a specific
    place — by flag or by CEO_AUDIT_LOG_PATH / CEO_AUDIT_LOG_DIR. Rail r3
    P1-1: a flag is not the only carrier, and the cross-project pairing only
    EXISTS when both ledgers are on screen.
    """
    mod = load_transcripts_instrument()
    if mod is None:
        return bool(path_arg)
    return mod.audit_source_is_pinned(path_arg)
'''


_CEO_COST_COLLECT = '''

#: `ceo-cost`'s audit buckets vs the instrument's dimensions. The transcript
#: corpus carries no `skill` field (that is an audit-log-only annotation), so
#: `--by-skill` degrades to the role split WITH A NOTE rather than inventing
#: a dimension.
_BUCKET_TO_TRANSCRIPT_DIM = {
    "by-model": "model",
    "by-day": "day",
    "by-session": "session",
    "by-skill": "role",
}


def collect_transcripts(
    root_arg: Optional[str] = None,
    cutoff: Optional[datetime] = None,
    bucket: str = "by-model",
    audit_override: bool = False,
) -> Dict[str, Any]:
    """Primary-source rollup, or a `{"available": False, "reason": ...}` note.

    `audit_override` says the SECONDARY source was pointed at an explicit
    path (`--log`); with no explicit transcripts root that pairing crosses
    projects and is refused by name (rail r2 P1-1).
    """
    mod = load_transcripts_instrument()
    if mod is None:
        return {
            "available": False,
            "reason": "instrument ceo-cost-transcripts.py is not importable",
        }
    dim = _BUCKET_TO_TRANSCRIPT_DIM.get(bucket, "model")
    note = None
    if bucket == "by-skill":
        note = (
            "note: the transcript corpus carries no skill field "
            "(audit-log-only annotation) - showing the role split instead."
        )
    return mod.collect(
        root_arg=root_arg,
        cutoff=cutoff,
        by=dim,
        note=note,
        audit_override=audit_override,
    )
'''

_BUDGET_COLLECT = '''

def collect_transcripts(
    root_arg: Optional[str] = None,
    cutoff: Optional[datetime] = None,
    audit_override: bool = False,
) -> Dict[str, Any]:
    """Primary-source rollup, or a `{"available": False, "reason": ...}` note.

    `budget-summary` has no `--by` flag, so the breakdown dimension is fixed
    to `model` — the same dimension its audit-side `per_plan` table is most
    comparable against. `audit_override` says `--audit-dir` pointed the
    SECONDARY source at an explicit path; with no explicit transcripts root
    that pairing crosses projects and is refused by name (rail r2 P1-1).
    """
    mod = load_transcripts_instrument()
    if mod is None:
        return {
            "available": False,
            "reason": "instrument ceo-cost-transcripts.py is not importable",
        }
    return mod.collect(
        root_arg=root_arg,
        cutoff=cutoff,
        by="model",
        audit_override=audit_override,
    )
'''


# ---------------------------------------------------------------------------
# (path, ancora EXATA, substituto, ocorrencias esperadas)
# ---------------------------------------------------------------------------
EDITS: List[Tuple[str, str, str, int]] = []

# =========================================================================
# 1. ceo-cost-transcripts.py — API programatica + superficie compartilhada
# =========================================================================

EDITS.append((
    ".claude/scripts/ceo-cost-transcripts.py",
    "# ---------------------------------------------------------------------------\n"
    "# CLI\n"
    "# ---------------------------------------------------------------------------\n"
    "\n"
    '_SINCE_RE = re.compile(r"^(\\d+)([dh])$")\n',
    "# ---------------------------------------------------------------------------\n"
    "# Programmatic API (PLAN-186 W0, AC-1b)\n"
    "# ---------------------------------------------------------------------------\n"
    "#\n"
    "# `ceo-cost.py` and `budget-summary.py` consume THIS surface, never the\n"
    "# CLI's stdout. Everything below the `transcript_rollup` line exists so\n"
    "# the two callers share one root resolver, one collector and one\n"
    "# renderer — a second grafia of any of them is the exact shape of the\n"
    "# D1-D4 defect class (CLAUDE.md \xa75).\n"
    "\n"
    "#: Env override for the transcripts corpus root. Flag > env > the shared\n"
    "#: `_lib.runtime_paths` resolver. Tests MUST set this (or pass the flag):\n"
    "#: nothing here may read the real ~/.claude/projects/<slug> corpus.\n"
    'ROOT_ENV = "CEO_COST_TRANSCRIPTS_DIR"\n'
    "\n"
    "#: The `--source` domain, shared by both callers.\n"
    'SOURCE_CHOICES = ("transcripts", "audit", "both")\n'
    "\n"
    'TRANSCRIPTS_BANNER = "=== SOURCE: TRANSCRIPTS (message.usage -- PRIMARY) ==="\n'
    'AUDIT_BANNER = "=== SOURCE: AUDIT LOG (governance ledger -- SECONDARY) ==="\n'
    "\n"
    "\n"
    "def transcript_rollup(\n"
    "    project_dir: Any,\n"
    "    cutoff: Optional[datetime] = None,\n"
    "    pricing_arg: Optional[str] = None,\n"
    '    by: str = "model",\n'
    ") -> Dict[str, Any]:\n"
    '    """Scan + dedup + price `project_dir`, returning the rollup as data.\n'
    "\n"
    "    `cutoff` is an aware datetime; records strictly older are dropped.\n"
    "    `None` means the whole corpus. This is the single pipeline the CLI\n"
    "    itself runs, so the API and the printed report can never disagree.\n"
    '    """\n'
    "    if by not in _GROUP_KEYS:\n"
    '        raise ValueError("unknown breakdown dimension: %r" % (by,))\n'
    "    project_dir = Path(project_dir)\n"
    "    pricing_result = load_pricing(pricing_arg)\n"
    "\n"
    "    top_files, sub_files = discover_files(project_dir)\n"
    "    counters = ScanCounters()\n"
    '    records = scan_files(top_files, "assento", project_dir, counters)\n'
    '    records += scan_files(sub_files, "subagent", project_dir, counters)\n'
    "\n"
    "    if cutoff is not None:\n"
    "        records = [r for r in records if r.ts >= cutoff]\n"
    "\n"
    "    deduped, dropped = dedup(records)\n"
    "    counters.deduped_records = len(deduped)\n"
    "\n"
    "    priced = price_records(deduped, pricing_result.table)\n"
    "\n"
    "    unresolved: Dict[str, Dict[str, float]] = {}\n"
    "    for p in priced:\n"
    "        if not p.resolved:\n"
    "            d = unresolved.setdefault(p.rec.model, _bucket_totals())\n"
    '            d["turns"] += 1\n'
    "            for cls in _TOKEN_CLASSES:\n"
    "                d[cls] += getattr(p.rec, cls)\n"
    "\n"
    "    grand, role_totals, group_totals = aggregate(priced, by)\n"
    "    return {\n"
    '        "project_dir": str(project_dir),\n'
    '        "pricing_result": pricing_result,\n'
    '        "pricing_source": pricing_result.source,\n'
    '        "pricing_used_fallback": pricing_result.used_fallback,\n'
    '        "by": by,\n'
    '        "files": {"assento": len(top_files), "subagent": len(sub_files)},\n'
    '        "counters": counters,\n'
    '        "dropped_duplicates": dropped,\n'
    '        "unresolved_models": unresolved,\n'
    '        "grand_total": grand,\n'
    '        "by_role": role_totals,\n'
    '        "by_dimension": group_totals,\n'
    "    }\n"
    "\n"
    "\n"
    "def resolve_root(root_arg: Optional[str] = None) -> Optional[Path]:\n"
    '    """Flag > `$CEO_COST_TRANSCRIPTS_DIR` > `_lib.runtime_paths`."""\n'
    "    if root_arg:\n"
    "        return Path(root_arg)\n"
    "    env = os.environ.get(ROOT_ENV)\n"
    "    if env:\n"
    "        return Path(env)\n"
    "    return _default_project_dir()\n"
    "\n"
    "\n"
    "def explicit_root_given(root_arg: Optional[str] = None) -> bool:\n"
    '    """True when the CALLER pinned the corpus (flag or env), not the\n'
    "    ambient project resolver. Rail r2 P1-1 turns on this distinction.\n"
    '    """\n'
    "    return bool(root_arg) or bool(os.environ.get(ROOT_ENV))\n"
    "\n"
    "\n"
    "#: The env carriers that point the SECONDARY (audit) ledger somewhere\n"
    "#: specific. Rail r3 P1-1: a flag is not the only way to override it.\n"
    'AUDIT_PATH_ENV_CARRIERS = ("CEO_AUDIT_LOG_PATH", "CEO_AUDIT_LOG_DIR")\n'
    "\n"
    "\n"
    "def audit_source_is_pinned(path_arg: Optional[str] = None) -> bool:\n"
    '    """True when the audit ledger was pointed at a specific place."""\n'
    "    if path_arg:\n"
    "        return True\n"
    "    return any(os.environ.get(k) for k in AUDIT_PATH_ENV_CARRIERS)\n"
    "\n"
    "\n"
    "def collect(\n"
    "    root_arg: Optional[str] = None,\n"
    "    cutoff: Optional[datetime] = None,\n"
    '    by: str = "model",\n'
    "    note: Optional[str] = None,\n"
    "    audit_override: bool = False,\n"
    ") -> Dict[str, Any]:\n"
    '    """Caller-facing collector: a JSON-safe rollup, or a labelled note.\n'
    "\n"
    "    NEVER raises: an absent root, an unreadable corpus or an internal\n"
    "    failure comes back as `{'available': False, 'reason': ...}` so the\n"
    "    SECONDARY (audit) source keeps rendering unchanged.\n"
    '    """\n'
    "    # Rail r2 P1-1: when the caller pointed the SECONDARY source at an\n"
    "    # explicit path (--log / --audit-dir) but left the PRIMARY one to the\n"
    "    # ambient project resolver, the report would juxtapose project A's\n"
    "    # transcripts with project B's audit log. Refuse the pairing by name\n"
    "    # rather than print two ledgers from two projects side by side.\n"
    "    if audit_override and not explicit_root_given(root_arg):\n"
    "        return {\n"
    '            "available": False,\n'
    '            "reason": (\n'
    '                "the audit source was pointed at an explicit path but no "\n'
    '                "transcripts root was given - refusing to pair one "\n'
    "                \"project's transcripts with another project's audit log \"\n"
    '                "(pass --transcripts-root or set %s)" % ROOT_ENV\n'
    "            ),\n"
    "        }\n"
    "    root = resolve_root(root_arg)\n"
    "    if root is None:\n"
    "        return {\n"
    '            "available": False,\n'
    '            "reason": (\n'
    '                "could not resolve a transcripts root (pass the flag or "\n'
    '                "set %s)" % ROOT_ENV\n'
    "            ),\n"
    "        }\n"
    "    if not root.is_dir():\n"
    "        return {\n"
    '            "available": False,\n'
    '            "reason": "transcripts root does not exist: %s" % root,\n'
    "        }\n"
    "    try:\n"
    "        res = transcript_rollup(root, cutoff=cutoff, by=by)\n"
    "    except Exception as exc:  # pragma: no cover - fail-soft envelope\n"
    "        return {\n"
    '            "available": False,\n'
    '            "reason": "transcripts rollup failed: %s" % type(exc).__name__,\n'
    "        }\n"
    "    # Rail r1 P1-1: a corrupted line, a line without a timestamp or an\n"
    "    # unreadable file is SILENTLY dropped by scan_files() — publishing\n"
    "    # the total without those counters would present a partial figure as\n"
    "    # the authoritative one. They travel with the payload and\n"
    "    # `incomplete` makes the renderers say so.\n"
    '    c = res["counters"]\n'
    "    return {\n"
    '        "available": True,\n'
    '        "root": str(root),\n'
    '        "by": by,\n'
    '        "note": note,\n'
    '        "pricing_source": res["pricing_source"],\n'
    '        "files": res["files"],\n'
    '        "totals": res["grand_total"],\n'
    '        "by_role": res["by_role"],\n'
    '        "by_dimension": res["by_dimension"],\n'
    '        "unresolved_models": res["unresolved_models"],\n'
    '        "scan": {\n'
    '            "files_scanned": c.files_scanned,\n'
    '            "lines_seen": c.lines_seen,\n'
    '            "candidate_lines": c.candidate_lines,\n'
    '            "corrupted_lines": c.corrupted_lines,\n'
    '            "missing_timestamp": c.missing_timestamp,\n'
    '            "unreadable_files": c.unreadable_files,\n'
    '            "missing_usage_keys": c.missing_usage_keys,\n'
    '            "assistant_without_usage": c.assistant_without_usage,\n'
    '            "sidechain_in_toplevel_skipped": (\n'
    "                c.sidechain_in_toplevel_skipped\n"
    "            ),\n"
    '            "dropped_duplicates": res["dropped_duplicates"],\n'
    "        },\n"
    '        "incomplete": bool(\n'
    "            c.corrupted_lines\n"
    "            or c.missing_timestamp\n"
    "            or c.unreadable_files\n"
    "            # Rail r2 P1-2: an assistant record whose `usage` object\n"
    "            # carries NEITHER core token key is schema drift, not\n"
    "            # contract - it is a dropped turn. Measured 0 on the live\n"
    "            # corpus (80,811 candidate lines), so this fires only when\n"
    "            # the harness schema actually moves.\n"
    "            or c.missing_usage_keys\n"
    "            or c.assistant_without_usage\n"
    "        ),\n"
    "    }\n"
    "\n"
    "\n"
    "def render_block(collected: Optional[Dict[str, Any]]) -> List[str]:\n"
    '    """Render the PRIMARY-source block as lines (no trailing blank)."""\n'
    "    out: List[str] = [TRANSCRIPTS_BANNER]\n"
    "    if not collected or not collected.get(\"available\"):\n"
    '        reason = (collected or {}).get("reason") or "unavailable"\n'
    '        out.append("transcripts source UNAVAILABLE: %s" % reason)\n'
    "        return out\n"
    '    out.append("root: %s" % collected["root"])\n'
    '    out.append("pricing: %s" % collected["pricing_source"])\n'
    "    out.append(\n"
    '        "files: %d assento + %d subagent"\n'
    '        % (collected["files"]["assento"], collected["files"]["subagent"])\n'
    "    )\n"
    '    if collected.get("incomplete"):\n'
    '        s = collected.get("scan") or {}\n'
    "        out.append(\n"
    '            "WARNING: INCOMPLETE SCAN - this total is a LOWER BOUND: "\n'
    '            "%d corrupted line(s), %d line(s) without a timestamp, "\n'
    '            "%d unreadable file(s), %d usage record(s) missing both core "\n'
    '            "token keys and %d assistant line(s) with no usage object "\n'
    '            "were skipped."\n'
    "            % (\n"
    '                s.get("corrupted_lines", 0),\n'
    '                s.get("missing_timestamp", 0),\n'
    '                s.get("unreadable_files", 0),\n'
    '                s.get("missing_usage_keys", 0),\n'
    '                s.get("assistant_without_usage", 0),\n'
    "            )\n"
    "        )\n"
    '    if collected.get("note"):\n'
    '        out.append(collected["note"])\n'
    '    unresolved = collected.get("unresolved_models") or {}\n'
    "    if unresolved:\n"
    "        out.append(\n"
    '            "warning: %d model id(s) absent from the pricing table, "\n'
    '            "priced as $0 and never guessed: %s"\n'
    '            % (len(unresolved), ", ".join(sorted(unresolved.keys())))\n'
    "        )\n"
    '    out.append("")\n'
    "    head = \"%-12s %8s %13s %13s %13s %13s %11s\" % (\n"
    '        "role", "turns", "input", "cache_w", "cache_r", "output", "cost",\n'
    "    )\n"
    "    out.append(head)\n"
    '    for role in ("assento", "subagent"):\n'
    '        d = collected["by_role"].get(role) or _bucket_totals()\n'
    "        out.append(\n"
    '            "%-12s %8s %13s %13s %13s %13s %11s"\n'
    "            % (\n"
    "                role,\n"
    '                _fmt_int(d["turns"]),\n'
    '                _fmt_int(d["input_tokens"]),\n'
    '                _fmt_int(d["cache_write_5m"] + d["cache_write_1h"]),\n'
    '                _fmt_int(d["cache_read_tokens"]),\n'
    '                _fmt_int(d["output_tokens"]),\n'
    '                _fmt_usd(d["usd"]),\n'
    "            )\n"
    "        )\n"
    '    g = collected["totals"]\n'
    '    out.append("")\n'
    "    out.append(\n"
    '        "%-40s %8s %11s %8s" % (collected["by"], "turns", "cost", "share%")\n'
    "    )\n"
    "    rows = sorted(\n"
    '        collected["by_dimension"].items(),\n'
    '        key=lambda kv: kv[1]["usd"],\n'
    "        reverse=True,\n"
    "    )\n"
    '    denom = g["usd"] or 1.0\n'
    "    for k, d in rows[:20]:\n"
    "        out.append(\n"
    '            "%-40s %8s %11s %7.1f%%"\n'
    "            % (\n"
    "                str(k)[:40],\n"
    '                _fmt_int(d["turns"]),\n'
    '                _fmt_usd(d["usd"]),\n'
    '                100.0 * d["usd"] / denom,\n'
    "            )\n"
    "        )\n"
    "    if len(rows) > 20:\n"
    '        out.append("... (+%d rows omitted)" % (len(rows) - 20))\n'
    '    out.append("")\n'
    "    out.append(\n"
    '        "TRANSCRIPTS TOTAL: %s turns, %s in, %s out, %s cache-read, "\n'
    '        "%s cache-write, %s"\n'
    "        % (\n"
    '            _fmt_int(g["turns"]),\n'
    '            _fmt_int(g["input_tokens"]),\n'
    '            _fmt_int(g["output_tokens"]),\n'
    '            _fmt_int(g["cache_read_tokens"]),\n'
    '            _fmt_int(g["cache_write_5m"] + g["cache_write_1h"]),\n'
    '            _fmt_usd(g["usd"]),\n'
    "        )\n"
    "    )\n"
    "    return out\n"
    "\n"
    "\n"
    "# ---------------------------------------------------------------------------\n"
    "# CLI\n"
    "# ---------------------------------------------------------------------------\n"
    "\n"
    '_SINCE_RE = re.compile(r"^(\\d+)([dh])$")\n',
    1,
))

# Rail r3 P1-2: o prefiltro rapido descarta a linha ANTES de qualquer
# contador. Uma linha com `"assistant"` e SEM `"usage"` (rename/remocao do
# campo, ou cauda truncada) sumia em silencio. Medido no corpus vivo:
# 424.089 linhas, 80.935 com `"assistant"`, ZERO sem `"usage"` — o contador
# so acende sob drift real.
EDITS.append((
    ".claude/scripts/ceo-cost-transcripts.py",
    "    missing_usage_keys: int = 0\n",
    "    missing_usage_keys: int = 0\n"
    "    assistant_without_usage: int = 0\n",
    1,
))

EDITS.append((
    ".claude/scripts/ceo-cost-transcripts.py",
    "                    if b'\"assistant\"' not in raw or b'\"usage\"' not in raw:\n"
    "                        continue\n",
    "                    if b'\"assistant\"' not in raw:\n"
    "                        continue\n"
    "                    if b'\"usage\"' not in raw:\n"
    "                        # Rail r3 P1-2: an assistant-shaped line with no\n"
    "                        # usage substring is either a renamed/removed\n"
    "                        # field or a torn write - a DROPPED turn, not a\n"
    "                        # user record. Counted so completeness detection\n"
    "                        # can see it. (A tear that also loses the\n"
    "                        # `\"assistant\"` substring is indistinguishable\n"
    "                        # from a user turn by construction - that is the\n"
    "                        # price of the prefilter, and it is declared.)\n"
    "                        counters.assistant_without_usage += 1\n"
    "                        continue\n",
    1,
))

# `os` nao estava importado no instrumento (resolve_root le o env).
EDITS.append((
    ".claude/scripts/ceo-cost-transcripts.py",
    "import argparse\nimport glob\nimport json\nimport re\nimport sys\nimport time\n",
    "import argparse\nimport glob\nimport json\nimport os\nimport re\nimport sys\nimport time\n",
    1,
))

# main() passa a consumir a MESMA pipeline (CLI byte-compativel).
EDITS.append((
    ".claude/scripts/ceo-cost-transcripts.py",
    "    pricing_result = load_pricing(args.pricing)\n"
    "\n"
    "    top_files, sub_files = discover_files(project_dir)\n"
    "    args.n_top_files = len(top_files)\n"
    "    args.n_sub_files = len(sub_files)\n"
    "\n"
    "    counters = ScanCounters()\n"
    '    records = scan_files(top_files, "assento", project_dir, counters)\n'
    '    records += scan_files(sub_files, "subagent", project_dir, counters)\n'
    "\n"
    "    cutoff = datetime.now(timezone.utc) - args.since\n"
    "    records = [r for r in records if r.ts >= cutoff]\n"
    "\n"
    "    deduped, dropped = dedup(records)\n"
    "    counters.deduped_records = len(deduped)\n"
    "    args.n_dropped_dupes = dropped\n"
    "\n"
    "    priced = price_records(deduped, pricing_result.table)\n"
    "\n"
    "    unresolved_by_model: Dict[str, Dict[str, float]] = {}\n"
    "    for p in priced:\n"
    "        if not p.resolved:\n"
    "            d = unresolved_by_model.setdefault(p.rec.model, _bucket_totals())\n"
    '            d["turns"] += 1\n'
    "            for cls in _TOKEN_CLASSES:\n"
    "                d[cls] += getattr(p.rec, cls)\n"
    "\n"
    "    grand, role_totals, group_totals = aggregate(priced, args.by)\n",
    "    # ONE pipeline for the CLI and for the programmatic callers\n"
    "    # (PLAN-186 W0, AC-1b): a second copy here is how the printed report\n"
    "    # and ceo-cost.py's block would silently disagree.\n"
    "    rolled = transcript_rollup(\n"
    "        project_dir,\n"
    "        cutoff=datetime.now(timezone.utc) - args.since,\n"
    "        pricing_arg=args.pricing,\n"
    "        by=args.by,\n"
    "    )\n"
    '    pricing_result = rolled["pricing_result"]\n'
    '    counters = rolled["counters"]\n'
    '    args.n_top_files = rolled["files"]["assento"]\n'
    '    args.n_sub_files = rolled["files"]["subagent"]\n'
    '    args.n_dropped_dupes = rolled["dropped_duplicates"]\n'
    '    unresolved_by_model = rolled["unresolved_models"]\n'
    '    grand = rolled["grand_total"]\n'
    '    role_totals = rolled["by_role"]\n'
    '    group_totals = rolled["by_dimension"]\n',
    1,
))

# =========================================================================
# 2. ceo-cost.py
# =========================================================================

EDITS.append((
    ".claude/scripts/ceo-cost.py",
    "import argparse\nimport json\nimport os\nimport re\nimport sys\n",
    "import argparse\nimport importlib.util\nimport json\nimport os\nimport re\nimport sys\n",
    1,
))

EDITS.append((
    ".claude/scripts/ceo-cost.py",
    "# ---------------------------------------------------------------------------\n"
    "# Rendering\n"
    "# ---------------------------------------------------------------------------\n"
    "\n"
    "\n"
    "def _format_cost(c: float) -> str:\n",
    _LOADER_BLOCK.lstrip("\n") + _CEO_COST_COLLECT + "\n"
    "\n"
    "# ---------------------------------------------------------------------------\n"
    "# Rendering\n"
    "# ---------------------------------------------------------------------------\n"
    "\n"
    "\n"
    "def _format_cost(c: float) -> str:\n",
    1,
))

EDITS.append((
    ".claude/scripts/ceo-cost.py",
    "def render_text(\n"
    "    agg: Dict[str, Any],\n"
    "    bucket: str,\n"
    "    since_label: str,\n"
    ") -> str:\n"
    '    """Render text-table output."""\n'
    "    out: List[str] = []\n"
    "    totals = agg[\"totals\"]\n"
    "\n"
    '    out.append(f"since={since_label}  by={bucket}")\n'
    '    out.append("")\n',
    "def render_text(\n"
    "    agg: Dict[str, Any],\n"
    "    bucket: str,\n"
    "    since_label: str,\n"
    "    transcripts: Optional[Dict[str, Any]] = None,\n"
    '    source: str = "audit",\n'
    ") -> str:\n"
    '    """Render text-table output.\n'
    "\n"
    "    `source` selects which of the two ledgers is rendered (PLAN-186 W0,\n"
    "    AC-1b). With the default `\"audit\"` the output is byte-for-byte the\n"
    "    pre-integration rendering — no banner, no extra line — which is what\n"
    "    the frozen-literal regression test pins.\n"
    '    """\n'
    "    out: List[str] = []\n"
    "\n"
    '    if source in ("transcripts", "both"):\n'
    "        mod = load_transcripts_instrument()\n"
    "        if mod is None:\n"
    "            out.append(\n"
    '                "transcripts source UNAVAILABLE: instrument "\n'
    '                "ceo-cost-transcripts.py is not importable"\n'
    "            )\n"
    "        else:\n"
    "            out.extend(mod.render_block(transcripts))\n"
    '        out.append("")\n'
    '    if source == "transcripts":\n'
    '        return "\\n".join(out)\n'
    '    if source == "both":\n'
    "        out.append(AUDIT_BANNER)\n"
    '        out.append("")\n'
    "\n"
    "    totals = agg[\"totals\"]\n"
    "\n"
    '    out.append(f"since={since_label}  by={bucket}")\n'
    '    out.append("")\n',
    1,
))

EDITS.append((
    ".claude/scripts/ceo-cost.py",
    "def render_json(agg: Dict[str, Any]) -> str:\n"
    "    return json.dumps(agg, indent=2, sort_keys=True, default=str)\n",
    "def render_json(\n"
    "    agg: Dict[str, Any],\n"
    "    transcripts: Optional[Dict[str, Any]] = None,\n"
    '    source: str = "audit",\n'
    ") -> str:\n"
    "    # `--source audit` keeps the historical top-level shape EXACTLY (no\n"
    "    # new keys); `both` keeps every audit key and ADDS the primary source\n"
    "    # beside it, so existing JSON consumers never break.\n"
    '    if source == "audit":\n'
    "        return json.dumps(agg, indent=2, sort_keys=True, default=str)\n"
    '    payload: Dict[str, Any] = {} if source == "transcripts" else dict(agg)\n'
    '    payload["source"] = source\n'
    '    payload["transcripts"] = transcripts\n'
    "    return json.dumps(payload, indent=2, sort_keys=True, default=str)\n",
    1,
))

EDITS.append((
    ".claude/scripts/ceo-cost.py",
    "    p.add_argument(\n"
    '        "--include-rotated",\n'
    '        action="store_true",\n'
    '        help="Aggregate across rotated audit-log*.jsonl siblings",\n'
    "    )\n",
    "    p.add_argument(\n"
    '        "--include-rotated",\n'
    '        action="store_true",\n'
    '        help="Aggregate across rotated audit-log*.jsonl siblings",\n'
    "    )\n"
    "    # --- PLAN-186 W0 (AC-1b) two-source flags -----------------------------\n"
    "    p.add_argument(\n"
    '        "--source",\n'
    "        choices=SOURCE_CHOICES,\n"
    '        default="both",\n'
    "        help=(\n"
    '            "Which ledger to report. \'transcripts\' = harness-native "\n'
    '            "message.usage (PRIMARY, cache-aware); \'audit\' = the "\n'
    '            "governance audit log (SECONDARY, byte-identical to the "\n'
    '            "pre-PLAN-186 output); \'both\' (default) prints them "\n'
    '            "labelled, side by side."\n'
    "        ),\n"
    "    )\n"
    "    p.add_argument(\n"
    '        "--transcripts-root",\n'
    "        default=None,\n"
    "        help=(\n"
    '            "Transcripts corpus root (the dir holding <session>.jsonl + "\n'
    '            "<session>/subagents/**). Default: $%s, else the shared "\n'
    '            "_lib.runtime_paths resolver." % ROOT_ENV\n'
    "        ),\n"
    "    )\n",
    1,
))

EDITS.append((
    ".claude/scripts/ceo-cost.py",
    "    # --- PLAN-040: streaming path -----------------------------------------\n"
    "    if args.stream:\n"
    "        if os.environ.get(\"CEO_COST_STREAMING\") == \"0\":\n",
    "    # --- PLAN-040: streaming path -----------------------------------------\n"
    "    if args.stream:\n"
    "        # Rail r2 P2-1: stream mode tails the AUDIT log only. Emitting\n"
    "        # the secondary estimate while the caller asked for the primary\n"
    "        # source would be the wrong number under the right flag.\n"
    '        stream_source = getattr(args, "source", "audit")\n'
    '        if stream_source == "transcripts":\n'
    "            print(\n"
    '                "ceo-cost: --stream tails the audit log only and cannot "\n'
    '                "stream the transcripts source; drop --stream or use "\n'
    '                "--source audit",\n'
    "                file=sys.stderr,\n"
    "            )\n"
    "            return 2\n"
    '        if stream_source != "audit":\n'
    "            print(\n"
    '                "ceo-cost: --stream tails the AUDIT log only (SECONDARY "\n'
    '                "source); the transcripts source is not streamed",\n'
    "                file=sys.stderr,\n"
    "            )\n"
    "        if os.environ.get(\"CEO_COST_STREAMING\") == \"0\":\n",
    1,
))

EDITS.append((
    ".claude/scripts/ceo-cost.py",
    "    # --- batch aggregation (pre-PLAN-040 path, unchanged) -----------------\n"
    "    paths = discover_logs(log_path, args.include_rotated)\n"
    "    if not paths:\n"
    '        print(f"audit log not found: {log_path}", file=sys.stderr)\n'
    "        return 1\n",
    "    # --- batch aggregation (pre-PLAN-040 path, unchanged) -----------------\n"
    '    source = getattr(args, "source", "audit")\n'
    "    paths = discover_logs(log_path, args.include_rotated)\n"
    '    if not paths and source != "transcripts":\n'
    '        print(f"audit log not found: {log_path}", file=sys.stderr)\n'
    "        return 1\n",
    1,
))

EDITS.append((
    ".claude/scripts/ceo-cost.py",
    "    entries = read_entries(paths)\n"
    "    agg = aggregate(entries, since=since, pricing=pricing)\n"
    "\n"
    '    if args.format == "json":\n'
    "        print(render_json(agg))\n"
    "    else:\n"
    "        print(render_text(agg, args.bucket, args.since))\n"
    "    return 0\n",
    "    entries = read_entries(paths)\n"
    "    agg = aggregate(entries, since=since, pricing=pricing)\n"
    "\n"
    "    transcripts: Optional[Dict[str, Any]] = None\n"
    '    if source in ("transcripts", "both"):\n'
    "        transcripts = collect_transcripts(\n"
    '            root_arg=getattr(args, "transcripts_root", None),\n'
    "            cutoff=since,\n"
    "            bucket=args.bucket,\n"
    "            audit_override=(\n"
    "                # Rail r3 P1-1: the cross-project pairing only EXISTS\n"
    "                # when both ledgers are on screen, and the audit one can\n"
    "                # be redirected by env as well as by --log.\n"
    '                source == "both" and _tx_audit_pinned(args.log)\n'
    "            ),\n"
    "        )\n"
    "\n"
    '    if args.format == "json":\n'
    "        print(render_json(agg, transcripts=transcripts, source=source))\n"
    "    else:\n"
    "        print(\n"
    "            render_text(\n"
    "                agg,\n"
    "                args.bucket,\n"
    "                args.since,\n"
    "                transcripts=transcripts,\n"
    "                source=source,\n"
    "            )\n"
    "        )\n"
    "    return 0\n",
    1,
))

# =========================================================================
# 3. budget-summary.py
# =========================================================================

EDITS.append((
    ".claude/scripts/budget-summary.py",
    "import argparse\nimport glob\nimport hashlib\nimport json\nimport os\nimport re\nimport sys\n",
    "import argparse\nimport glob\nimport hashlib\nimport importlib.util\nimport json\nimport os\nimport re\nimport sys\n",
    1,
))

EDITS.append((
    ".claude/scripts/budget-summary.py",
    "def format_human(data: Dict[str, Any], memory_claim: Optional[Dict[str, Any]] = None) -> str:\n"
    '    """Render the rollup as a human-readable text block."""\n'
    "    lines: List[str] = []\n"
    "    scope = data.get(\"plan_filter\") or \"(all plans)\"\n",
    _LOADER_BLOCK.lstrip("\n") + _BUDGET_COLLECT + "\n"
    "\n"
    "def format_human(data: Dict[str, Any], memory_claim: Optional[Dict[str, Any]] = None) -> str:\n"
    '    """Render the rollup as a human-readable text block.\n'
    "\n"
    "    PLAN-186 W0 (AC-1b): when `data` carries a `source` key the PRIMARY\n"
    "    transcripts block is rendered first, labelled; `source == 'audit'`\n"
    "    sets NO key at all, so that rendering is byte-identical to the\n"
    "    pre-integration one.\n"
    '    """\n'
    "    lines: List[str] = []\n"
    '    source = data.get("source")\n'
    "    if source is not None:\n"
    "        mod = load_transcripts_instrument()\n"
    "        if mod is None:\n"
    "            lines.append(\n"
    '                "transcripts source UNAVAILABLE: instrument "\n'
    '                "ceo-cost-transcripts.py is not importable"\n'
    "            )\n"
    "        else:\n"
    '            lines.extend(mod.render_block(data.get("transcripts")))\n'
    '        lines.append("")\n'
    '        if source == "transcripts":\n'
    '            return "\\n".join(lines)\n'
    "        lines.append(AUDIT_BANNER)\n"
    '        lines.append("")\n'
    "    scope = data.get(\"plan_filter\") or \"(all plans)\"\n",
    1,
))

EDITS.append((
    ".claude/scripts/budget-summary.py",
    '    sp.add_argument("--native-root", metavar="PATH", default=None,\n'
    '                    help=(\n'
    '                        "Override the native transcript root (default: "\n'
    '                        "~/.claude/projects/<cwd-slug>; env override "\n'
    '                        "CEO_NATIVE_USAGE_DIR)."\n'
    "                    ))\n"
    "    return p\n",
    '    sp.add_argument("--native-root", metavar="PATH", default=None,\n'
    '                    help=(\n'
    '                        "Override the native transcript root (default: "\n'
    '                        "~/.claude/projects/<cwd-slug>; env override "\n'
    '                        "CEO_NATIVE_USAGE_DIR)."\n'
    "                    ))\n"
    "    # PLAN-186 W0 (AC-1b) — the two-source surface.\n"
    '    sp.add_argument("--source", choices=SOURCE_CHOICES, default="both",\n'
    "                    help=(\n"
    '                        "Which ledger to report. \'transcripts\' = "\n'
    '                        "harness-native message.usage (PRIMARY, "\n'
    '                        "cache-aware); \'audit\' = the governance audit "\n'
    '                        "log (SECONDARY, byte-identical to the "\n'
    '                        "pre-PLAN-186 output); \'both\' (default) prints "\n'
    '                        "them labelled, side by side."\n'
    "                    ))\n"
    '    sp.add_argument("--transcripts-root", metavar="PATH", default=None,\n'
    "                    help=(\n"
    '                        "Transcripts corpus root. Default: $%s, else the "\n'
    '                        "shared _lib.runtime_paths resolver. Distinct "\n'
    '                        "from --native-root, which feeds the older "\n'
    '                        "--native cross-check." % ROOT_ENV\n'
    "                    ))\n"
    "    return p\n",
    1,
))

EDITS.append((
    ".claude/scripts/budget-summary.py",
    "        args.benchmarks = False\n"
    "        args.native = False\n"
    "        args.native_root = None\n",
    "        args.benchmarks = False\n"
    "        args.native = False\n"
    "        args.native_root = None\n"
    '        args.source = "both"\n'
    "        args.transcripts_root = None\n",
    1,
))

EDITS.append((
    ".claude/scripts/budget-summary.py",
    "    audit_dir = Path(args.audit_dir) if args.audit_dir else None\n"
    "\n"
    "    data = rollup(\n"
    "        audit_dir=audit_dir,\n"
    "        plan_filter=args.plan_id,\n"
    "        since=since_delta,\n"
    "        by_wave=args.by_wave,\n"
    "    )\n"
    '    data["since"] = args.since\n',
    "    audit_dir = Path(args.audit_dir) if args.audit_dir else None\n"
    "\n"
    "    # Rail r3 P2-1: ONE wall clock for both ledgers. `rollup()` captures\n"
    "    # its own `now` internally; taking a second one after it returns let\n"
    "    # a record land inside the audit window and outside the transcripts\n"
    "    # window while both blocks printed the same `--since`.\n"
    "    _now = datetime.now(timezone.utc)\n"
    "\n"
    "    # PLAN-186 W0 (AC-1b): the PRIMARY source. `--source audit` adds NO\n"
    "    # key to `data`, which is what keeps that rendering byte-identical.\n"
    '    source = getattr(args, "source", "audit")\n'
    "    # Rail r1 P1-2: the transcript corpus carries NO plan field (the same\n"
    "    # limitation the --native cross-check hit in S306). A project-wide\n"
    "    # transcripts total printed as PRIMARY beside a plan-scoped audit\n"
    "    # block is the wrong number for the plan that was asked about. Under\n"
    "    # --plan-id it is suppressed; an EXPLICIT --source transcripts there\n"
    "    # is a named refusal, never a silently unscoped answer.\n"
    '    if source != "audit" and getattr(args, "plan_id", None):\n'
    '        if source == "transcripts":\n'
    "            sys.stderr.write(\n"
    '                "budget-summary: --source transcripts cannot be scoped "\n'
    '                "by --plan-id (the transcript corpus has no plan "\n'
    '                "field); drop one of the two flags\\n"\n'
    "            )\n"
    "            return 2\n"
    "        sys.stderr.write(\n"
    '            "budget-summary: transcripts source suppressed under "\n'
    '            "--plan-id (the transcript corpus has no plan field; run "\n'
    '            "without --plan-id to see it)\\n"\n'
    "        )\n"
    '        source = "audit"\n'
    "    # Rail r2 P2-2: --validate-memory-claim compares the AUDIT total\n"
    "    # against CLAUDE.md's claim band; under --source transcripts there is\n"
    "    # no audit total to validate, and returning 'unknown' would look like\n"
    "    # a verdict. Named refusal instead.\n"
    '    if source == "transcripts" and getattr(\n'
    '        args, "validate_memory_claim", False\n'
    "    ):\n"
    "        sys.stderr.write(\n"
    '            "budget-summary: --validate-memory-claim validates the AUDIT "\n'
    '            "total and cannot run under --source transcripts; use "\n'
    '            "--source both or audit\\n"\n'
    "        )\n"
    "        return 2\n"
    "    if source == \"transcripts\":\n"
    "        # Rail S341 (A): --by-wave shapes the AUDIT rollup (wave_hint\n"
    "        # on agent_spawn rows). With rollup() skipped there is no block\n"
    "        # to shape, so the flag is DROPPED -- named on stderr, never\n"
    "        # silently swallowed, exactly like the two co-reports below.\n"
    '        if getattr(args, "by_wave", False):\n'
    "            sys.stderr.write(\n"
    '                "budget-summary: --by-wave shapes the AUDIT rollup and "\n'
    '                "is dropped under --source transcripts (the transcript "\n'
    '                "corpus has no wave field); use --source both or "\n'
    '                "audit\\n"\n'
    "            )\n"
    "        data: Dict[str, Any] = {\"since\": args.since}\n"
    "    else:\n"
    "        data = rollup(\n"
    "            audit_dir=audit_dir,\n"
    "            plan_filter=args.plan_id,\n"
    "            since=since_delta,\n"
    "            by_wave=args.by_wave,\n"
    "        )\n"
    '        data["since"] = args.since\n'
    '    if source != "audit":\n'
    '        data["source"] = source\n'
    '        data["transcripts"] = collect_transcripts(\n'
    '            root_arg=getattr(args, "transcripts_root", None),\n'
    "            cutoff=(\n"
    "                _now - since_delta if since_delta is not None else None\n"
    "            ),\n"
    "            audit_override=(\n"
    '                source == "both"\n'
    "                and _tx_audit_pinned(\n"
    "                    str(audit_dir) if audit_dir is not None else None\n"
    "                )\n"
    "            ),\n"
    "        )\n",
    1,
))

# `--benchmarks` / `--native` blocks sao pulados quando so ha transcripts.
EDITS.append((
    ".claude/scripts/budget-summary.py",
    "    benchmarks_on = bool(getattr(args, \"benchmarks\", False)) or (\n"
    '        os.environ.get("CEO_BUDGET_BENCHMARKS", "") == "1"\n'
    "    )\n",
    "    benchmarks_on = bool(getattr(args, \"benchmarks\", False)) or (\n"
    '        os.environ.get("CEO_BUDGET_BENCHMARKS", "") == "1"\n'
    "    )\n"
    "    # Both co-reports are AUDIT-side; under --source transcripts there is\n"
    "    # no audit rollup to append them to. Rail S341 (A): a REQUESTED\n"
    "    # block that vanishes with rc 0 and an empty stderr is the shape\n"
    "    # this pack removed everywhere else -- so it is dropped by NAME,\n"
    "    # mirroring the CEO_NATIVE_COST_DISABLE / --plan-id lines below.\n"
    '    if source == "transcripts":\n'
    "        if benchmarks_on:\n"
    "            sys.stderr.write(\n"
    '                "budget-summary: --benchmarks is an AUDIT-side "\n'
    '                "co-report and is dropped under --source transcripts; "\n'
    '                "use --source both or audit\\n"\n'
    "            )\n"
    "        benchmarks_on = False\n",
    1,
))

EDITS.append((
    ".claude/scripts/budget-summary.py",
    "    native_on = bool(getattr(args, \"native\", False)) or (\n"
    '        os.environ.get("CEO_BUDGET_NATIVE", "") == "1"\n'
    "    )\n",
    "    native_on = bool(getattr(args, \"native\", False)) or (\n"
    '        os.environ.get("CEO_BUDGET_NATIVE", "") == "1"\n'
    "    )\n"
    '    if source == "transcripts":\n'
    "        if native_on:\n"
    "            sys.stderr.write(\n"
    '                "budget-summary: --native is an AUDIT-side cross-check "\n'
    '                "and is dropped under --source transcripts; use "\n'
    '                "--source both or audit\\n"\n'
    "            )\n"
    "        native_on = False\n",
    1,
))

EDITS.append((
    ".claude/scripts/budget-summary.py",
    "    if memory_claim is not None:\n"
    "        lines.append(\"\")\n"
    '        lines.append("Memory-claim validation:")\n'
    "        lines.append(f\"  status  : {memory_claim['status']}\")\n"
    "        lines.append(f\"  message : {memory_claim['message']}\")\n",
    "    if memory_claim is not None:\n"
    "        lines.append(\"\")\n"
    '        lines.append("Memory-claim validation:")\n'
    "        lines.append(f\"  status  : {memory_claim['status']}\")\n"
    "        lines.append(f\"  message : {memory_claim['message']}\")\n"
    "        # Rail r2 P2-2: say WHICH ledger the verdict is about. Only when\n"
    "        # a second ledger is on screen — audit-only output is unchanged.\n"
    '        if data.get("source") is not None:\n'
    "            lines.append(\n"
    '                "  scope   : validates the AUDIT total (SECONDARY); the "\n'
    '                "transcripts total above is the PRIMARY figure"\n'
    "            )\n",
    1,
))

# =========================================================================
# 4. Testes existentes: isolar a raiz de transcripts (nunca o $HOME real)
# =========================================================================

EDITS.append((
    ".claude/scripts/tests/test_ceo_cost.py",
    "    def setUp(self):\n"
    '        self.tmp = Path(tempfile.mkdtemp(prefix="ceo-cost-cli-")).resolve()\n'
    '        self.log = self.tmp / "audit-log.jsonl"\n'
    "        _write_log(self.log, [_entry()])\n",
    "    def setUp(self):\n"
    '        self.tmp = Path(tempfile.mkdtemp(prefix="ceo-cost-cli-")).resolve()\n'
    '        self.log = self.tmp / "audit-log.jsonl"\n'
    "        _write_log(self.log, [_entry()])\n"
    "        # PLAN-186 W0 (AC-1b): --source now defaults to `both`, so the CLI\n"
    "        # reaches the transcripts corpus. patch.dict restores os.environ on\n"
    "        # teardown (env-hygiene mandate); the root is pinned at an EMPTY\n"
    "        # dir so no test here ever reads the real ~/.claude/projects tree.\n"
    "        self._empty_transcripts = self.tmp / \"transcripts-empty\"\n"
    "        self._empty_transcripts.mkdir()\n"
    "        self._env_patch = patch.dict(\n"
    "            os.environ,\n"
    '            {"CEO_COST_TRANSCRIPTS_DIR": str(self._empty_transcripts)},\n'
    "            clear=False,\n"
    "        )\n"
    "        self._env_patch.start()\n"
    "        self.addCleanup(self._env_patch.stop)\n",
    1,
))

EDITS.append((
    ".claude/scripts/tests/test_ceo_cost.py",
    "import tempfile\nimport unittest\nfrom datetime import datetime, timedelta, timezone\nfrom pathlib import Path\n",
    "import tempfile\nimport unittest\nfrom datetime import datetime, timedelta, timezone\nfrom pathlib import Path\nfrom unittest.mock import patch\n",
    1,
))

EDITS.append((
    ".claude/scripts/tests/test_budget_summary.py",
    "from typing import Any, Dict, List\n"
    "from unittest.mock import patch\n",
    "from typing import Any, Dict, List\n"
    "from unittest.mock import patch\n"
    "\n"
    "# ``_lib.testing`` (TestEnvContext). PLAN-186 W0 (AC-1b) made the two\n"
    "# CLI classes below env-dependent (the `summary --source` default is\n"
    "# `both`), and the contract for an env-touching test is TestEnvContext\n"
    "# COMBINED with patch.dict — the base class sandboxes HOME and\n"
    "# CLAUDE_PROJECT_DIR, patch.dict pins the individual variables.\n"
    "_LIB_HOOKS_DIR = Path(__file__).resolve().parents[3] / \".claude\" / \"hooks\"\n"
    "if str(_LIB_HOOKS_DIR) not in sys.path:\n"
    "    sys.path.insert(0, str(_LIB_HOOKS_DIR))\n"
    "\n"
    "from _lib.testing import TestEnvContext  # noqa: E402\n",
    1,
))

EDITS.append((
    ".claude/scripts/tests/test_budget_summary.py",
    "class TestCli(unittest.TestCase):\n"
    "    @classmethod\n"
    "    def setUpClass(cls) -> None:\n"
    '        cls.tmp = Path(tempfile.mkdtemp(prefix="ceo-cli-"))\n'
    "        generate_fixtures.build_fixture_set(cls.tmp)\n",
    "class TestCli(TestEnvContext):\n"
    "    @classmethod\n"
    "    def setUpClass(cls) -> None:\n"
    '        cls.tmp = Path(tempfile.mkdtemp(prefix="ceo-cli-"))\n'
    "        generate_fixtures.build_fixture_set(cls.tmp)\n"
    "\n"
    "    def setUp(self) -> None:\n"
    "        super().setUp()\n"
    "        # PLAN-186 W0 (AC-1b): `summary --source` defaults to `both`, so\n"
    "        # main() now reaches the transcripts corpus. Pin it at an EMPTY dir\n"
    "        # (patch.dict restores os.environ on teardown) — no test in this\n"
    "        # file may read the real ~/.claude/projects tree.\n"
    '        empty = self.tmp / "transcripts-empty"\n'
    "        empty.mkdir(exist_ok=True)\n"
    "        # `CEO_NATIVE_USAGE_DIR` is pinned in the SAME patch and\n"
    "        # `CEO_BUDGET_NATIVE` forced off (rail r1 P2-2): an ambient\n"
    "        # opt-in in the developer's shell would otherwise send the\n"
    "        # pre-existing --native branch at the real HOME corpus.\n"
    "        self._env_patch = patch.dict(\n"
    "            os.environ,\n"
    "            {\n"
    '                "CEO_COST_TRANSCRIPTS_DIR": str(empty),\n'
    '                "CEO_NATIVE_USAGE_DIR": str(empty),\n'
    '                "CEO_BUDGET_NATIVE": "0",\n'
    "            },\n"
    "            clear=False,\n"
    "        )\n"
    "        self._env_patch.start()\n"
    "        self.addCleanup(self._env_patch.stop)\n",
    1,
))

EDITS.append((
    ".claude/scripts/tests/test_budget_summary.py",
    "class TestBenchmarkCoReport(unittest.TestCase):\n",
    "class TestBenchmarkCoReport(TestEnvContext):\n",
    1,
))

EDITS.append((
    ".claude/scripts/tests/test_budget_summary.py",
    "    def setUp(self) -> None:\n"
    '        self.tmp = Path(tempfile.mkdtemp(prefix="ceo-c4-"))\n'
    "        # patch.dict restores os.environ on teardown (env-hygiene mandate); we\n"
    "        # remove CEO_BUDGET_BENCHMARKS so the default-OFF path is exercised, and\n"
    "        # individual tests overlay it via a nested patch.dict.\n"
    "        self._env_patch = patch.dict(os.environ, {}, clear=False)\n"
    "        self._env_patch.start()\n"
    "        self.addCleanup(self._env_patch.stop)\n"
    '        os.environ.pop("CEO_BUDGET_BENCHMARKS", None)\n',
    "    def setUp(self) -> None:\n"
    "        super().setUp()\n"
    '        self.tmp = Path(tempfile.mkdtemp(prefix="ceo-c4-"))\n'
    "        # patch.dict restores os.environ on teardown (env-hygiene mandate); we\n"
    "        # remove CEO_BUDGET_BENCHMARKS so the default-OFF path is exercised, and\n"
    "        # individual tests overlay it via a nested patch.dict.\n"
    "        # PLAN-186 W0 (AC-1b): the transcripts root is pinned at an EMPTY\n"
    "        # dir inside the SAME patch.dict, so the default `--source both`\n"
    "        # never reaches the real HOME corpus and no bare os.environ write\n"
    "        # is introduced (env-hygiene gate).\n"
    '        _empty_transcripts = self.tmp / "transcripts-empty"\n'
    "        _empty_transcripts.mkdir(parents=True, exist_ok=True)\n"
    "        self._env_patch = patch.dict(\n"
    "            os.environ,\n"
    "            {\n"
    '                "CEO_COST_TRANSCRIPTS_DIR": str(_empty_transcripts),\n'
    '                "CEO_NATIVE_USAGE_DIR": str(_empty_transcripts),\n'
    '                "CEO_BUDGET_NATIVE": "0",\n'
    "            },\n"
    "            clear=False,\n"
    "        )\n"
    "        self._env_patch.start()\n"
    "        self.addCleanup(self._env_patch.stop)\n"
    '        os.environ.pop("CEO_BUDGET_BENCHMARKS", None)\n',
    1,
))

# Rail r3 P2-2: o tearDown custom da classe convertida nao chamava super(),
# entao HOME/CLAUDE_PROJECT_DIR/CEO_AUDIT_* do TestEnvContext vazariam.
EDITS.append((
    ".claude/scripts/tests/test_budget_summary.py",
    "    def tearDown(self) -> None:\n"
    "        # os.environ is restored by the patch.dict cleanup registered in setUp.\n"
    "        shutil.rmtree(self.tmp, ignore_errors=True)\n",
    "    def tearDown(self) -> None:\n"
    "        # os.environ is restored by the patch.dict cleanup registered in setUp.\n"
    "        shutil.rmtree(self.tmp, ignore_errors=True)\n"
    "        # TestEnvContext's own teardown restores HOME / CLAUDE_PROJECT_DIR\n"
    "        # / CEO_AUDIT_* and removes its tmp tree; a custom tearDown that\n"
    "        # forgets super() leaves the sandbox installed for the next test.\n"
    "        super().tearDown()\n",
    1,
))

# =========================================================================
# 5. docs/cost-of-operation.md — a secao das duas fontes
# =========================================================================

EDITS.append((
    "docs/cost-of-operation.md",
    "## Measuring cost\n",
    "## The two cost sources (PLAN-186 W0)\n"
    "\n"
    "`ceo-cost.py` and `budget-summary.py` read **two different ledgers**, and\n"
    "since PLAN-186 W0 they print both, labelled, side by side. Which one you\n"
    "get is chosen with `--source transcripts|audit|both` (default `both`).\n"
    "\n"
    "| | PRIMARY — transcripts | SECONDARY — audit log |\n"
    "|---|---|---|\n"
    "| What it is | `message.usage` on every assistant turn of the harness-native transcripts | the HMAC-chained **governance** log (`agent_spawn` rows) |\n"
    "| Where | `<state-dir>/<session>.jsonl` + `<session>/subagents/**/agent-*.jsonl` | `<state-dir>/audit-log*.jsonl` |\n"
    "| Token classes | input, output, cache-read, cache-write 5m, cache-write 1h | `tokens_in`, `tokens_out` only |\n"
    "| Covers the seat (the main session) | yes | no — the seat emits no token fields at all |\n"
    "| Read by | `.claude/scripts/ceo-cost-transcripts.py` | the two callers' own rollups |\n"
    "\n"
    "The audit log is a governance log, not a token ledger: it was never given\n"
    "the seat's own spend, and `tokens_in`/`tokens_out` are best-effort even on\n"
    "the spawns it does carry. That is why a 30-day audit-only rollup can\n"
    "print `$0.00` on a month that cost four figures — the number is not\n"
    "wrong about what it measures, it is measuring the wrong thing. The\n"
    "transcripts source is the one to quote for spend; the audit source stays\n"
    "because it is the one that can attribute a spawn to a plan, a skill and a\n"
    "session.\n"
    "\n"
    "```bash\n"
    "# both ledgers, labelled (default)\n"
    ".claude/scripts/ceo-cost.py --since 24h\n"
    "\n"
    "# only the real spend\n"
    ".claude/scripts/ceo-cost.py --since 30d --source transcripts\n"
    "\n"
    "# only the governance ledger (byte-identical to the pre-PLAN-186 output)\n"
    ".claude/scripts/ceo-cost.py --since 30d --source audit\n"
    "\n"
    "# same three modes on the FinOps rollup\n"
    ".claude/scripts/budget-summary.py summary --since 30d --source both\n"
    "```\n"
    "\n"
    "The transcripts root resolves as `--transcripts-root` >\n"
    "`$CEO_COST_TRANSCRIPTS_DIR` > the shared `_lib.runtime_paths` resolver.\n"
    "Tests always inject it; nothing in the suite reads the real corpus.\n"
    "\n"
    "Three pricing tables still exist in the tree (`ceo-cost.py`'s\n"
    "`_DEFAULT_PRICING`, the model registry behind `budget-summary.py`, and the\n"
    "instrument's `cost-table.yaml` loader). The transcripts block is priced by\n"
    "the instrument and says so in its `pricing:` line; unifying the three is a\n"
    "separate wave, deliberately out of scope here.\n"
    "\n"
    "## Measuring cost\n",
    1,
))


# =========================================================================
# 6. ceo-cost-transcripts.py — a "ratified correction" deixa de ser
#    incondicional (achado B do refutador, S341)
# =========================================================================
#
# `_RATIFIED_OVERRIDES_FOR_DEFAULT_TABLE` sobrescrevia a linha
# claude-sonnet-5 do cost-table.yaml SEMPRE que o caminho era o default —
# e desde b6dce78 o arquivo em arvore JA carrega 2.00/10.00. Hoje isso e um
# no-op numerico que ainda IMPRIME "ratified correction" em todo relatorio
# (corrigindo nada); amanha mascara em silencio um refresh legitimo da
# tabela. Cura: aplicar so quando a linha lida DIFERE da ratificada, e
# dizer no `source` qual dos dois aconteceu. As duas prosas que afirmavam
# "$3/$15 pendente do land" sao FALSAS desde b6dce78 e sao corrigidas.

EDITS.append((
    ".claude/scripts/ceo-cost-transcripts.py",
    "- **Format parses AND the path is the untouched default**: rows load\n"
    "  from the file, then one documented, sourced correction is layered on\n"
    "  top \u2014 ``claude-sonnet-5`` is repriced to the Owner-ratified intro rate\n"
    "  $2/$10 (2026-09-01; CLAUDE.md commit ``e47bf5d``, \"sonnet5-pricing-fu\"\n"
    "  \u2014 the in-tree ``cost-table.yaml`` still carries the pre-intro $3/$15\n"
    "  row pending that pack's land, per the same commit and S339 report\n"
    "  Limitation #3). An EXPLICIT ``--pricing`` path supplied by the caller\n"
    "  is trusted as-is, with no correction \u2014 the caller opted into a\n"
    "  specific pricing config on purpose.\n",
    "- **Format parses AND the path is the untouched default**: rows load\n"
    "  from the file, then the Owner-ratified corrections in\n"
    "  ``_RATIFIED_OVERRIDES_FOR_DEFAULT_TABLE`` are layered on top \u2014 but\n"
    "  ONLY where the parsed row actually DIFFERS from the ratified rate.\n"
    "  As of ``b6dce78`` the in-tree ``cost-table.yaml`` already carries the\n"
    "  ratified ``claude-sonnet-5`` $2/$10 row, so on the default path the\n"
    "  correction is currently a NO-OP and ``source`` says so. An\n"
    "  unconditional overwrite would be worse than useless: it would print\n"
    "  \"ratified correction\" while correcting nothing, and the day the\n"
    "  table is legitimately refreshed it would silently mask the new rate.\n"
    "  An EXPLICIT ``--pricing`` path supplied by the caller is trusted\n"
    "  as-is, with no correction at all \u2014 the caller opted into a specific\n"
    "  pricing config on purpose.\n",
    1,
))

EDITS.append((
    ".claude/scripts/ceo-cost-transcripts.py",
    "#: Applied ONLY on top of a successfully-parsed DEFAULT --pricing path\n"
    "#: (never on an explicit caller-supplied path). See module docstring.\n",
    "#: Applied ONLY on top of a successfully-parsed DEFAULT --pricing path\n"
    "#: (never on an explicit caller-supplied path), and ONLY where the\n"
    "#: parsed row differs from the value below. An entry that matches the\n"
    "#: file is reported as a no-op, never as a correction. See module\n"
    "#: docstring.\n",
    1,
))

EDITS.append((
    ".claude/scripts/ceo-cost-transcripts.py",
    "def load_pricing(pricing_arg: Optional[str]) -> PricingResult:\n",
    "def _override_is_a_no_op(\n"
    "    current: Optional[Dict[str, float]], override: Dict[str, float]\n"
    ") -> bool:\n"
    "    \"\"\"True when the parsed row ALREADY carries every ratified value.\n"
    "\n"
    "    Guards the one thing an unconditional overwrite cannot express: the\n"
    "    difference between a stale file that WAS corrected and a file that\n"
    "    was already right. Missing row / wrong type => not a no-op, so the\n"
    "    override still lands.\n"
    "    \"\"\"\n"
    "    if not isinstance(current, dict):\n"
    "        return False\n"
    "    for key, value in override.items():\n"
    "        have = current.get(key)\n"
    "        if isinstance(have, bool) or not isinstance(have, (int, float)):\n"
    "            return False\n"
    "        if abs(float(have) - float(value)) > 1e-9:\n"
    "            return False\n"
    "    return True\n"
    "\n"
    "\n"
    "def load_pricing(pricing_arg: Optional[str]) -> PricingResult:\n",
    1,
))

EDITS.append((
    ".claude/scripts/ceo-cost-transcripts.py",
    "    if is_default_path:\n"
    "        for mid, override in _RATIFIED_OVERRIDES_FOR_DEFAULT_TABLE.items():\n"
    "            table[mid] = dict(override)\n"
    "        source += (\n"
    "            \" + ratified correction (claude-sonnet-5 $2/$10, 2026-09-01, \"\n"
    "            \"CLAUDE.md e47bf5d)\"\n"
    "        )\n",
    "    if is_default_path:\n"
    "        # Conditional by construction: an override that merely restates\n"
    "        # what the file already says is NOT a correction. Reporting it as\n"
    "        # one prints a fix that fixed nothing, and applying it anyway\n"
    "        # would silently mask a legitimate refresh of the table.\n"
    "        applied: List[str] = []\n"
    "        noop: List[str] = []\n"
    "        for mid in sorted(_RATIFIED_OVERRIDES_FOR_DEFAULT_TABLE):\n"
    "            override = _RATIFIED_OVERRIDES_FOR_DEFAULT_TABLE[mid]\n"
    "            if _override_is_a_no_op(table.get(mid), override):\n"
    "                noop.append(mid)\n"
    "                continue\n"
    "            table[mid] = dict(override)\n"
    "            applied.append(\n"
    "                \"%s -> $%g/$%g\"\n"
    "                % (\n"
    "                    mid,\n"
    "                    override[\"input_per_mtok\"],\n"
    "                    override[\"output_per_mtok\"],\n"
    "                )\n"
    "            )\n"
    "        if applied:\n"
    "            source += (\n"
    "                \" + ratified correction (%s; 2026-09-01, CLAUDE.md \"\n"
    "                \"e47bf5d)\" % \", \".join(applied)\n"
    "            )\n"
    "        if noop:\n"
    "            source += (\n"
    "                \" + ratified correction NOT needed for %s (the file \"\n"
    "                \"already carries the ratified rate)\" % \", \".join(noop)\n"
    "            )\n",
    1,
))

EDITS.append((
    ".claude/scripts/ceo-cost-transcripts.py",
    "            \"parses, its base input/output rates are used with ONE \"\n"
    "            \"documented correction layered on top (claude-sonnet-5 -> \"\n"
    "            \"$2/$10, ratified 2026-09-01, CLAUDE.md commit e47bf5d) because \"\n"
    "            \"the in-tree file still carries the pre-intro $3/$15 row \"\n"
    "            \"pending the sonnet5-pricing-fu pack's land. Pass --pricing \"\n",
    "            \"parses, its base input/output rates are used and the \"\n"
    "            \"Owner-ratified corrections (claude-sonnet-5 -> $2/$10, \"\n"
    "            \"2026-09-01, CLAUDE.md commit e47bf5d) are layered on top \"\n"
    "            \"ONLY where the file's row actually differs; since \"\n"
    "            \"b6dce78 the in-tree file already carries that row, so \"\n"
    "            \"the correction is a no-op and the report's pricing: line \"\n"
    "            \"says so. Pass --pricing \"\n",
    1,
))

# O arquivo de teste nao importa unittest.mock hoje; os testes novos
# repontam _SCRIPT_DIR para uma tabela sintetica com mock.patch.object.
EDITS.append((
    ".claude/scripts/tests/test_ceo_cost_transcripts.py",
    "from typing import Any, Dict, List, Optional\n",
    "from typing import Any, Dict, List, Optional\n"
    "from unittest import mock\n",
    1,
))

# --- teste existente que assertava a correcao INCONDICIONAL no arquivo real
EDITS.append((
    ".claude/scripts/tests/test_ceo_cost_transcripts.py",
    "    def test_load_pricing_default_applies_ratified_sonnet5_override(self):\n"
    "        # Default path (pricing_arg=None) resolves the in-repo\n"
    "        # cost-table.yaml, which still carries the pre-intro $3/$15\n"
    "        # Sonnet 5 row (S337/S338 note) \u2014 the ratified $2/$10 correction\n"
    "        # must be layered on top when the DEFAULT path is used.\n"
    "        result = cct.load_pricing(None)\n"
    "        self.assertFalse(result.used_fallback)\n"
    "        self.assertEqual(result.table[\"claude-sonnet-5\"][\"input_per_mtok\"], 2.00)\n"
    "        self.assertEqual(result.table[\"claude-sonnet-5\"][\"output_per_mtok\"], 10.00)\n"
    "        self.assertIn(\"ratified correction\", result.source)\n",
    "    def _default_table(self, body: str):\n"
    "        \"\"\"Run load_pricing(None) against a SYNTHETIC default table.\n"
    "\n"
    "        `_SCRIPT_DIR` is read at call time, so pointing it at the tmp dir\n"
    "        makes `pricing_arg=None` resolve there: the DEFAULT-path branch\n"
    "        runs, without the test depending on what the real in-tree\n"
    "        cost-table.yaml happens to say today.\n"
    "        \"\"\"\n"
    "        (self.project_dir / \"cost-table.yaml\").write_text(\n"
    "            body, encoding=\"utf-8\"\n"
    "        )\n"
    "        with mock.patch.object(cct, \"_SCRIPT_DIR\", self.project_dir):\n"
    "            return cct.load_pricing(None)\n"
    "\n"
    "    def test_default_table_with_stale_row_gets_the_ratified_correction(self):\n"
    "        # Achado B (S341): the correction exists for THIS case -- a default\n"
    "        # table whose row differs from the ratified rate.\n"
    "        result = self._default_table(\n"
    "            \"models:\\n\"\n"
    "            \"  claude-sonnet-5:\\n\"\n"
    "            \"    input_per_mtok: 3.00\\n\"\n"
    "            \"    output_per_mtok: 15.00\\n\"\n"
    "        )\n"
    "        self.assertFalse(result.used_fallback)\n"
    "        self.assertEqual(result.table[\"claude-sonnet-5\"][\"input_per_mtok\"], 2.00)\n"
    "        self.assertEqual(result.table[\"claude-sonnet-5\"][\"output_per_mtok\"], 10.00)\n"
    "        self.assertIn(\n"
    "            \"ratified correction (claude-sonnet-5 -> $2/$10\", result.source\n"
    "        )\n"
    "        self.assertNotIn(\"NOT needed\", result.source)\n"
    "\n"
    "    def test_default_table_already_ratified_is_not_corrected(self):\n"
    "        # The S340 residual: overwriting a row that already matches printed\n"
    "        # a \"ratified correction\" that corrected nothing, and would mask a\n"
    "        # legitimate refresh of the table the day one lands.\n"
    "        result = self._default_table(\n"
    "            \"models:\\n\"\n"
    "            \"  claude-sonnet-5:\\n\"\n"
    "            \"    input_per_mtok: 2.00\\n\"\n"
    "            \"    output_per_mtok: 10.00\\n\"\n"
    "        )\n"
    "        self.assertFalse(result.used_fallback)\n"
    "        self.assertEqual(result.table[\"claude-sonnet-5\"][\"input_per_mtok\"], 2.00)\n"
    "        self.assertIn(\n"
    "            \"ratified correction NOT needed for claude-sonnet-5\", result.source\n"
    "        )\n"
    "        self.assertNotIn(\"ratified correction (\", result.source)\n"
    "\n"
    "    def test_refreshed_default_table_is_not_masked(self):\n"
    "        # The consequence the gate exists for: a table refreshed to a NEW\n"
    "        # rate is still corrected while the override IS the ratified\n"
    "        # truth -- and the source NAMES what it did, so a stale override\n"
    "        # is visible instead of silent.\n"
    "        result = self._default_table(\n"
    "            \"models:\\n\"\n"
    "            \"  claude-sonnet-5:\\n\"\n"
    "            \"    input_per_mtok: 2.50\\n\"\n"
    "            \"    output_per_mtok: 12.50\\n\"\n"
    "        )\n"
    "        self.assertEqual(result.table[\"claude-sonnet-5\"][\"input_per_mtok\"], 2.00)\n"
    "        self.assertIn(\"ratified correction (claude-sonnet-5\", result.source)\n"
    "\n"
    "    def test_in_tree_default_table_is_already_ratified(self):\n"
    "        # Ties the prose to the tree: since b6dce78 the shipped\n"
    "        # cost-table.yaml carries the ratified row, so the real default\n"
    "        # path takes the no-op branch. If this ever flips, the docstring\n"
    "        # and the epilog are wrong again and this test says so.\n"
    "        result = cct.load_pricing(None)\n"
    "        self.assertFalse(result.used_fallback)\n"
    "        self.assertEqual(result.table[\"claude-sonnet-5\"][\"input_per_mtok\"], 2.00)\n"
    "        self.assertIn(\"NOT needed\", result.source)\n",
    1,
))

# =========================================================================
# 7. Curas da rodada 1 do pair-rail (S341): 1 P1 + 2 P2, todos verificados
#    contra a arvore antes de curar (medicoes em rail-round-1.md)
# =========================================================================

# --- r1-P1: parar o patch.dict ANTES do teardown da base -------------------
# `addCleanup` roda DEPOIS de `tearDown`, entao um patch.dict parado por
# cleanup re-instala o snapshot tirado DENTRO do sandbox por cima do
# ambiente ambiente que `TestEnvContext.tearDown()` acabou de restaurar --
# deixando HOME/CLAUDE_PROJECT_DIR apontando para um diretorio ja apagado.

EDITS.append((
    ".claude/scripts/tests/test_budget_summary.py",
    "        self._env_patch.start()\n"
    "        self.addCleanup(self._env_patch.stop)\n"
    "\n"
    "    @classmethod\n"
    "    def tearDownClass(cls) -> None:\n",
    "        self._env_patch.start()\n"
    "\n"
    "    def tearDown(self) -> None:\n"
    "        # Rail S341 r1 [P1]: unittest runs addCleanup callbacks AFTER\n"
    "        # tearDown, so stopping this patch.dict from a cleanup would\n"
    "        # restore the snapshot taken INSIDE the sandbox on top of the\n"
    "        # ambient environment super().tearDown() has just put back --\n"
    "        # leaving HOME at a tmp tree that was just deleted. The order\n"
    "        # below is load-bearing.\n"
    "        self._env_patch.stop()\n"
    "        super().tearDown()\n"
    "\n"
    "    @classmethod\n"
    "    def tearDownClass(cls) -> None:\n",
    1,
))

EDITS.append((
    ".claude/scripts/tests/test_budget_summary.py",
    "        self._env_patch.start()\n"
    "        self.addCleanup(self._env_patch.stop)\n"
    '        os.environ.pop("CEO_BUDGET_BENCHMARKS", None)\n',
    "        self._env_patch.start()\n"
    '        os.environ.pop("CEO_BUDGET_BENCHMARKS", None)\n',
    1,
))

EDITS.append((
    ".claude/scripts/tests/test_budget_summary.py",
    "    def tearDown(self) -> None:\n"
    "        # os.environ is restored by the patch.dict cleanup registered in setUp.\n"
    "        shutil.rmtree(self.tmp, ignore_errors=True)\n"
    "        # TestEnvContext's own teardown restores HOME / CLAUDE_PROJECT_DIR\n"
    "        # / CEO_AUDIT_* and removes its tmp tree; a custom tearDown that\n"
    "        # forgets super() leaves the sandbox installed for the next test.\n"
    "        super().tearDown()\n",
    "    def tearDown(self) -> None:\n"
    "        shutil.rmtree(self.tmp, ignore_errors=True)\n"
    "        # Rail S341 r1 [P1]: the patch.dict is stopped HERE, not from an\n"
    "        # addCleanup -- cleanups run after tearDown, so a cleanup-stopped\n"
    "        # patch would re-install the sandbox snapshot on top of the\n"
    "        # ambient environment the line below restores.\n"
    "        self._env_patch.stop()\n"
    "        # TestEnvContext's own teardown restores HOME / CLAUDE_PROJECT_DIR\n"
    "        # / CEO_AUDIT_* and removes its tmp tree; a custom tearDown that\n"
    "        # forgets super() leaves the sandbox installed for the next test.\n"
    "        super().tearDown()\n",
    1,
))

# --- r1-P2a: UM relogio de parede alimenta OS DOIS ledgers -----------------
EDITS.append((
    ".claude/scripts/budget-summary.py",
    "        data = rollup(\n"
    "            audit_dir=audit_dir,\n"
    "            plan_filter=args.plan_id,\n"
    "            since=since_delta,\n"
    "            by_wave=args.by_wave,\n"
    "        )\n",
    "        data = rollup(\n"
    "            audit_dir=audit_dir,\n"
    "            plan_filter=args.plan_id,\n"
    "            since=since_delta,\n"
    "            by_wave=args.by_wave,\n"
    "            # Rail S341 r1 [P2]: capturing `_now` and letting rollup()\n"
    "            # take its own clock delivers HALF of D10 -- a record on the\n"
    "            # window boundary could still land inside one ledger and\n"
    "            # outside the other while both blocks print the same --since.\n"
    "            now=_now,\n"
    "        )\n",
    1,
))

# --- r1-P2b: o chamador declara os carriers que REALMENTE obedece ----------
EDITS.append((
    ".claude/scripts/ceo-cost-transcripts.py",
    "def audit_source_is_pinned(path_arg: Optional[str] = None) -> bool:\n"
    '    """True when the audit ledger was pointed at a specific place."""\n'
    "    if path_arg:\n"
    "        return True\n"
    "    return any(os.environ.get(k) for k in AUDIT_PATH_ENV_CARRIERS)\n",
    "def audit_source_is_pinned(\n"
    "    path_arg: Optional[str] = None,\n"
    "    carriers: Optional[Tuple[str, ...]] = None,\n"
    ") -> bool:\n"
    '    """True when the audit ledger was pointed at a specific place.\n'
    "\n"
    "    ``carriers`` names the env vars the CALLER actually obeys; the\n"
    "    default is every carrier this instrument knows about. A caller that\n"
    "    ignores one of them must say so, or the cross-project pairing check\n"
    "    suppresses its PRIMARY block over an override that moved nothing\n"
    "    (rail S341 r1 [P2]: ``budget-summary.py`` resolves its audit dir\n"
    "    from ``CEO_AUDIT_LOG_DIR`` alone, while ``ceo-cost.py`` honours both\n"
    '    and therefore passes nothing).\n'
    '    """\n'
    "    if path_arg:\n"
    "        return True\n"
    "    keys = AUDIT_PATH_ENV_CARRIERS if carriers is None else tuple(carriers)\n"
    "    return any(os.environ.get(k) for k in keys)\n",
    1,
))

EDITS.append((
    ".claude/scripts/budget-summary.py",
    "def _tx_audit_pinned(path_arg: Optional[str] = None) -> bool:\n",
    "#: The audit-path env carriers THIS caller actually obeys.\n"
    "#: `default_audit_dir()` reads CEO_AUDIT_LOG_DIR and nothing else, so\n"
    "#: CEO_AUDIT_LOG_PATH does not move budget-summary's ledger and must not\n"
    "#: be read as a cross-project pin (rail S341 r1 [P2]; measured: audit_dir\n"
    "#: byte-identical with and without that var). ceo-cost.py honours both\n"
    "#: carriers and passes none.\n"
    '_AUDIT_ENV_CARRIERS = ("CEO_AUDIT_LOG_DIR",)\n'
    "\n"
    "\n"
    "def _tx_audit_pinned(path_arg: Optional[str] = None) -> bool:\n",
    1,
))

EDITS.append((
    ".claude/scripts/budget-summary.py",
    "    mod = load_transcripts_instrument()\n"
    "    if mod is None:\n"
    "        return bool(path_arg)\n"
    "    return mod.audit_source_is_pinned(path_arg)\n",
    "    mod = load_transcripts_instrument()\n"
    "    if mod is None:\n"
    "        return bool(path_arg)\n"
    "    return mod.audit_source_is_pinned(\n"
    "        path_arg, carriers=_AUDIT_ENV_CARRIERS\n"
    "    )\n",
    1,
))


# =========================================================================
# 8. Curas da rodada 2 do pair-rail (S341)
# =========================================================================

# --- r2-P1b: o fallback LEGADO tambem e um "pin" -------------------------
# `default_log_path()` cai no state dir pre-migracao quando o log scoped
# deste projeto ainda nao existe. Nenhum carrier e setado nessa rota, entao
# um check so-de-carriers libera a pareacao — e o resolvedor de transcripts
# devolve o corpus DESTE projeto. Passa a perguntar pelo path RESOLVIDO.

EDITS.append((
    ".claude/scripts/ceo-cost.py",
    "#: `ceo-cost`'s audit buckets vs the instrument's dimensions.",
    "def _audit_path_is_out_of_project(resolved: Path) -> bool:\n"
    '    """True when the RESOLVED audit log lives outside this project\'s\n'
    "    state dir.\n"
    "\n"
    "    Rail S341 r2 [P1]: `default_log_path()` has a sanctioned fallback to\n"
    "    the pre-migration LEGACY state dir when this project's scoped log\n"
    "    does not exist yet. That route sets NO carrier, so\n"
    "    `_tx_audit_pinned()` cannot see it — yet the transcripts resolver\n"
    "    still returns THIS project's corpus, which is exactly the\n"
    "    cross-project pairing the D8 guard refuses. Asking about the\n"
    "    resolved path closes the hole a carrier-only question leaves open.\n"
    "\n"
    "    Fail-soft: an unresolvable path is NOT reported as a pin, so a\n"
    "    filesystem oddity degrades to the pre-existing behaviour instead of\n"
    "    suppressing the primary block.\n"
    '    """\n'
    "    try:\n"
    "        return (\n"
    "            Path(resolved).resolve().parent\n"
    "            != _rp.runtime_state_dir().resolve()\n"
    "        )\n"
    "    except Exception:\n"
    "        return False\n"
    "\n"
    "\n"
    "#: `ceo-cost`'s audit buckets vs the instrument's dimensions.",
    1,
))

EDITS.append((
    ".claude/scripts/ceo-cost.py",
    "            audit_override=(\n"
    "                # Rail r3 P1-1: the cross-project pairing only EXISTS\n"
    "                # when both ledgers are on screen, and the audit one can\n"
    "                # be redirected by env as well as by --log.\n"
    "                source == \"both\" and _tx_audit_pinned(args.log)\n"
    "            ),\n",
    "            audit_override=(\n"
    "                # Rail r3 P1-1: the cross-project pairing only EXISTS\n"
    "                # when both ledgers are on screen, and the audit one can\n"
    "                # be redirected by env as well as by --log.\n"
    "                # Rail S341 r2 [P1]: a carrier is not the only way the\n"
    "                # audit ledger leaves this project — default_log_path()\n"
    "                # falls back to the pre-migration LEGACY dir with no\n"
    "                # carrier set at all. Ask the resolved path too.\n"
    '                source == "both"\n'
    "                and (\n"
    "                    _tx_audit_pinned(args.log)\n"
    "                    or _audit_path_is_out_of_project(log_path)\n"
    "                )\n"
    "            ),\n",
    1,
))

# --- r2-P2: a receita de monitoramento aponta para o total SECUNDARIO -----
EDITS.append((
    "docs/cost-of-operation.md",
    "```bash\n"
    "python3 .claude/scripts/ceo-cost.py --since 30d --format json | \\\n"
    "  jq '.totals.cost_usd'\n"
    "```\n"
    "\n"
    "Wire that into your monitoring dashboard for a continuous spend\n"
    "signal.\n",
    "```bash\n"
    "# PRIMARY — real spend, from message.usage (PLAN-186 W0)\n"
    "python3 .claude/scripts/ceo-cost.py --since 30d --format json | \\\n"
    "  jq '.transcripts.totals.usd'\n"
    "\n"
    "# SECONDARY — the governance ledger's own estimate, for attribution\n"
    "python3 .claude/scripts/ceo-cost.py --since 30d --format json | \\\n"
    "  jq '.totals.cost_usd'\n"
    "```\n"
    "\n"
    "Wire the FIRST one into your monitoring dashboard: `.totals.cost_usd`\n"
    "is the audit rollup, which cannot see the seat's own spend at all and\n"
    "reads `$0.00` on months that cost four figures (see \"The two cost\n"
    "sources\" above). Rail S341 r2 caught this page recommending the\n"
    "secondary number two sections after declaring the primary one\n"
    "authoritative.\n",
    1,
))


# ---------------------------------------------------------------------------
# Motor
# ---------------------------------------------------------------------------


def _plan(root: Path) -> Tuple[List[Tuple[Path, str]], List[str]]:
    """Plan EVERY operation before writing. Returns (writes, refusals)."""
    refusals: List[str] = []
    writes: List[Tuple[Path, str]] = []

    # 1. Arquivos novos.
    for rel in NEW_FILES:
        dst = root / rel
        src = PAYLOAD_DIR / rel
        if not src.is_file():
            refusals.append("payload ausente para arquivo novo: %s" % rel)
            continue
        if dst.exists():
            refusals.append("arquivo novo ja existe no alvo: %s" % rel)
            continue
        writes.append((dst, src.read_text(encoding="utf-8")))

    # 2. Edicoes ancoradas. Aplicadas em memoria, por path, na ordem.
    staged: dict = {}
    for rel, anchor, replacement, expected in EDITS:
        target = root / rel
        if rel not in staged:
            if not target.is_file():
                refusals.append("arquivo alvo ausente: %s" % rel)
                staged[rel] = None
                continue
            staged[rel] = target.read_text(encoding="utf-8")
        text = staged[rel]
        if text is None:
            continue
        # Already-applied guard that does NOT depend on the anchor
        # disappearing: several edits here APPEND to their anchor, so the
        # anchor still matches on a second run and only the presence of the
        # full replacement can tell "pristine" from "already patched".
        if replacement in text:
            refusals.append(
                "%s: substituto JA PRESENTE (patch ja aplicado) — %r"
                % (rel, anchor[:70])
            )
            continue
        found = text.count(anchor)
        if found == 0:
            if replacement in text:
                refusals.append(
                    "%s: ancora ausente e substituto JA PRESENTE (patch ja "
                    "aplicado?) — %r" % (rel, anchor[:70])
                )
            else:
                refusals.append(
                    "%s: ancora ausente — %r" % (rel, anchor[:70])
                )
            continue
        if found != expected:
            refusals.append(
                "%s: ancora ambigua — esperava %d ocorrencia(s), achou %d — %r"
                % (rel, expected, found, anchor[:70])
            )
            continue
        staged[rel] = text.replace(anchor, replacement, expected)

    for rel, text in staged.items():
        if text is None:
            continue
        writes.append((root / rel, text))

    return writes, refusals


def _list_paths() -> int:
    for rel in NEW_FILES:
        print(rel)
    seen = []
    for rel, _a, _r, _c in EDITS:
        if rel not in seen:
            seen.append(rel)
    for rel in seen:
        print(rel)
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--root", default=None, help="arvore alvo (em HEAD)")
    ap.add_argument("--check-only", action="store_true")
    ap.add_argument("--list-paths", action="store_true")
    args = ap.parse_args(argv)

    if args.list_paths:
        return _list_paths()
    if not args.root:
        ap.error("--root e obrigatorio (ou use --list-paths)")
        return 2

    root = Path(args.root).resolve()
    if not root.is_dir():
        print("RECUSA: --root nao e um diretorio: %s" % root, file=sys.stderr)
        return 1

    writes, refusals = _plan(root)
    if refusals:
        print("RECUSA (%d):" % len(refusals), file=sys.stderr)
        for r in refusals:
            print("  - %s" % r, file=sys.stderr)
        print("nenhuma escrita realizada.", file=sys.stderr)
        return 1

    if args.check_only:
        print("OK (check-only): %d escrita(s) aplicavel(is)." % len(writes))
        for p, _t in writes:
            print("  - %s" % p.relative_to(root))
        return 0

    for path, text in writes:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
    print("OK: %d arquivo(s) escrito(s)." % len(writes))
    for p, _t in writes:
        print("  - %s" % p.relative_to(root))
    return 0


if __name__ == "__main__":
    sys.exit(main())
