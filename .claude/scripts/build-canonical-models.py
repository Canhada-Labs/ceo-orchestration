#!/usr/bin/env python3
"""Build / verify / reconcile the canonical model-pricing table (PLAN-133 B1).

This is the **AUGMENT** layer for model pricing: ``.claude/data/canonical_models.json``
sits alongside the existing ``scripts/cost-table.yaml`` and the version-aware
``MODEL_PRICING`` tiers in ``PLAN-128/wave1/measure_multiplier.py``. It does NOT
replace them; it gives them a single provenance-stamped, checksum-protected
source that the Owner refreshes from models.dev.

SAFETY / PROVENANCE (PLAN-133 §2 + §B B1):
  * **Agents must not fetch.** This script NEVER opens a network socket. The
    ``--fetch`` mode reads an Owner-supplied JSON blob (file path or stdin) that
    the **Owner** downloaded from models.dev out-of-band. There is no
    ``urllib.request`` import anywhere in this module by design.
  * **Fail-CLOSED on checksum mismatch.** ``--verify`` recomputes the sha256 over
    the canonical serialization of the ``models`` block and exits non-zero if it
    does not match ``provenance.sha256`` (unless the seed sentinel
    ``PENDING_OWNER_FETCH`` is present — then it warns fail-open, because the
    real fetch has not happened yet; per the S220 'flag, do not guess' doctrine).
  * **Staleness is advisory.** ``--check-staleness`` mirrors ``check-staleness.py``:
    exit 0 by default, warn when ``today > staleness.valid_until``; ``--strict``
    turns the stale finding into a non-zero exit for CI.
  * **Reconcile, do not blind-overwrite.** ``--reconcile`` diffs the canonical
    rows against ``cost-table.yaml`` and the ``measure_multiplier`` tier regexes
    and FLAGS divergence. It never writes either of those files.
  * **S220 unknown=0 fallback preserved.** ``price_for(model)`` returns the
    ``unknown_model_fallback`` (all-zero, flagged) for an unrecognized id; it
    never guesses.

Stdlib-only, py>=3.9 compatible, ``from __future__ import annotations``. Fail-open
on infra (a missing/garbled file degrades to an advisory warning + the zero
fallback; it never crashes a caller). The behavioral surface this script gates
(whether a downstream consumer ADOPTS the canonical table over its hardcoded
tiers) is OFF by default — gated by the env flag ``CEO_CANONICAL_MODELS=1``
documented in ``canonical_price_source_enabled()``.

Usage::

    python3 .claude/scripts/build-canonical-models.py --verify
    python3 .claude/scripts/build-canonical-models.py --check-staleness [--strict]
    python3 .claude/scripts/build-canonical-models.py --reconcile [--json]
    # OWNER-ONLY (out-of-band fetch first):
    python3 .claude/scripts/build-canonical-models.py --fetch models-dev.json [-o out.json]
    cat models-dev.json | python3 .claude/scripts/build-canonical-models.py --fetch -
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Paths (all relative to repo root, derived from this file's location).
# ---------------------------------------------------------------------------
_SCRIPTS_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPTS_DIR.parent.parent
_DEFAULT_CANONICAL = _REPO_ROOT / ".claude" / "data" / "canonical_models.json"
_DEFAULT_COST_TABLE = _SCRIPTS_DIR / "cost-table.yaml"

# Seed sentinel — present until the Owner runs the real models.dev fetch.
_PENDING_SENTINEL = "PENDING_OWNER_FETCH"

# Env flag that flips a downstream consumer from its hardcoded tiers to this
# canonical table. Default-OFF (PLAN-133 §3 doctrine #1). B3 wires the consumer;
# B1 only ships the source + the flag contract.
_ENABLE_FLAG = "CEO_CANONICAL_MODELS"

# Cache multiplier pins (PLAN-133 B3 regression contract). Authoritative copy
# lives in the data file's `cache_multipliers`; these are the fallback if the
# data file is unreadable.
_CACHE_MULT_5M = 1.25
_CACHE_MULT_1H = 2.0
_CACHE_MULT_READ = 0.1


class CanonicalModelsError(Exception):
    """Raised on a structural problem with the canonical table."""


# ---------------------------------------------------------------------------
# Load + checksum
# ---------------------------------------------------------------------------
def _canonical_models_blob(models: Dict[str, Any]) -> bytes:
    """Deterministic serialization of the `models` object for checksumming.

    sort_keys + compact separators → byte-stable across Python versions and
    insertion order. This is what `provenance.sha256` is computed over.
    """
    return json.dumps(
        models, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode("utf-8")


def compute_models_sha256(models: Dict[str, Any]) -> str:
    """sha256 hex digest over the canonical `models` serialization."""
    return hashlib.sha256(_canonical_models_blob(models)).hexdigest()


def load_canonical_models(path: Optional[Path] = None) -> Dict[str, Any]:
    """Read + parse canonical_models.json. Raises CanonicalModelsError on a
    structural problem. Callers that want fail-open should use
    ``load_canonical_models_safe`` instead."""
    if path is None:
        path = _DEFAULT_CANONICAL
    if not path.is_file():
        raise CanonicalModelsError(f"canonical_models.json not found at {path}")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise CanonicalModelsError(
            f"cannot read/parse canonical_models.json {path}: {exc}"
        ) from exc
    for required in ("models", "provenance", "unknown_model_fallback"):
        if required not in data:
            raise CanonicalModelsError(
                f"canonical_models.json missing required field `{required}`"
            )
    if not isinstance(data["models"], dict):
        raise CanonicalModelsError("`models` must be an object")
    return data


def load_canonical_models_safe(
    path: Optional[Path] = None,
) -> Optional[Dict[str, Any]]:
    """Fail-open variant: returns None (and never raises) on any problem.

    Use from hot paths / hooks where a broken data file must degrade to the
    consumer's own fallback rather than crash the session."""
    try:
        return load_canonical_models(path)
    except CanonicalModelsError:
        return None
    except Exception:  # pragma: no cover — defensive belt-and-suspenders
        return None


def verify_checksum(
    data: Dict[str, Any],
) -> Tuple[bool, str]:
    """Return (ok, message).

    ok=True  → checksum matches, OR the seed sentinel is present (pre-fetch).
    ok=False → real checksum present and MISMATCHED (fail-CLOSED for callers).

    The seed sentinel path returns ok=True with a 'pending' message so that a
    fresh checkout (before the Owner's fetch) does not hard-block; the message
    makes the pending state visible.
    """
    prov = data.get("provenance") or {}
    declared = prov.get("sha256")
    if declared == _PENDING_SENTINEL or not declared:
        return (True, f"provenance.sha256={_PENDING_SENTINEL!r} — Owner fetch pending (fail-open)")
    actual = compute_models_sha256(data["models"])
    if actual != declared:
        return (
            False,
            "CHECKSUM MISMATCH (fail-CLOSED): canonical_models.json `models` "
            f"hashes to {actual} but provenance.sha256={declared}. The table was "
            "edited without re-running build-canonical-models.py --fetch — refusing "
            "to trust it.",
        )
    return (True, f"checksum OK ({actual})")


# ---------------------------------------------------------------------------
# Pricing lookup (S220 unknown=0 fallback)
# ---------------------------------------------------------------------------
def _normalize_lookup_key(model: str) -> str:
    """Lowercase + trim. Intentionally minimal: full alias canonicalization is
    B2's `normalize_model_name`. This only fixes case/whitespace so a JSONL
    `Claude-Opus-4-8 ` row resolves."""
    return (model or "").strip().lower()


def price_for(
    model: str, data: Optional[Dict[str, Any]] = None
) -> Tuple[Dict[str, float], bool]:
    """Return (price_dict, is_known).

    price_dict has keys: input_per_mtok, cache_write_5m_per_mtok,
    cache_write_1h_per_mtok, cache_read_per_mtok, output_per_mtok.

    On an unrecognized model id, returns the `unknown_model_fallback` (all-zero)
    with is_known=False — the S220 'flag, do not guess' contract. Caller is
    responsible for surfacing the unknown id (e.g. unknown_priced_models).

    Fail-open: if the data file is unreadable, returns the all-zero fallback.
    """
    if data is None:
        data = load_canonical_models_safe()
    fallback_price = {
        "input_per_mtok": 0.0,
        "cache_write_5m_per_mtok": 0.0,
        "cache_write_1h_per_mtok": 0.0,
        "cache_read_per_mtok": 0.0,
        "output_per_mtok": 0.0,
    }
    if data is None:
        return (fallback_price, False)
    models = data.get("models") or {}
    fb = data.get("unknown_model_fallback") or {}
    fallback_price = {k: float(fb.get(k, 0.0)) for k in fallback_price}

    key = _normalize_lookup_key(model)
    # 1) exact (case-insensitive) match
    for mid, row in models.items():
        if mid.lower() == key:
            return (_coerce_price_row(row), True)
    # 2) prefix match (a dated id `claude-opus-4-8-20260101` resolves to the
    #    base `claude-opus-4-8` row) — longest prefix wins.
    best: Optional[Tuple[str, Dict[str, Any]]] = None
    for mid, row in models.items():
        if key.startswith(mid.lower() + "-") and (best is None or len(mid) > len(best[0])):
            best = (mid, row)
    if best is not None:
        return (_coerce_price_row(best[1]), True)
    return (fallback_price, False)


def _coerce_price_row(row: Dict[str, Any]) -> Dict[str, float]:
    keys = (
        "input_per_mtok",
        "cache_write_5m_per_mtok",
        "cache_write_1h_per_mtok",
        "cache_read_per_mtok",
        "output_per_mtok",
    )
    return {k: float(row.get(k, 0.0)) for k in keys}


def canonical_price_source_enabled() -> bool:
    """Default-OFF env flag. A downstream consumer (B3) should consult the
    canonical table only when this is set, so the rollout is measure-first."""
    return os.environ.get(_ENABLE_FLAG, "").strip() in ("1", "true", "yes", "on")


# ---------------------------------------------------------------------------
# Staleness (mirror check-staleness.py contract)
# ---------------------------------------------------------------------------
def check_staleness(
    data: Dict[str, Any], today: Optional[date] = None
) -> Tuple[bool, str]:
    """Return (is_stale, message). message empty when fresh.

    Stale means today > staleness.valid_until. Pure function; the CLI wrapper
    prints the warning. Advisory by contract."""
    if today is None:
        today = date.today()
    stale_block = data.get("staleness") or {}
    raw = stale_block.get("valid_until")
    valid_until: Optional[date] = None
    if isinstance(raw, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw):
        try:
            valid_until = date.fromisoformat(raw)
        except ValueError:
            valid_until = None
    if valid_until is None:
        return (True, "staleness.valid_until missing/unparseable; treating as stale")
    if today > valid_until:
        days_over = (today - valid_until).days
        return (
            True,
            f"canonical_models.json expired {days_over} day(s) ago "
            f"(valid_until={valid_until.isoformat()}); Owner should re-run "
            "build-canonical-models.py --fetch <models.dev json>",
        )
    return (False, "")


# ---------------------------------------------------------------------------
# Reconcile vs cost-table.yaml + measure_multiplier tiers (FLAG, never overwrite)
# ---------------------------------------------------------------------------
def _load_cost_table_models(path: Optional[Path] = None) -> Dict[str, Dict[str, float]]:
    """Tiny dependency-free read of cost-table.yaml `models:` rows.

    Reuses no import from token-estimator.py (which is canonical-stable but not
    a library we want to couple B1 to). We only need input_per_mtok +
    output_per_mtok per model id, parsed from the same mini-YAML subset."""
    if path is None:
        path = _DEFAULT_COST_TABLE
    out: Dict[str, Dict[str, float]] = {}
    if not path.is_file():
        return out
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return out
    in_models = False
    cur: Optional[str] = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip())
        stripped = line.strip()
        if indent == 0:
            in_models = stripped.startswith("models:")
            cur = None
            continue
        if not in_models:
            continue
        if indent == 2 and stripped.endswith(":"):
            cur = stripped[:-1].strip()
            out[cur] = {}
        elif indent == 4 and cur is not None and ":" in stripped:
            k, _, v = stripped.partition(":")
            k = k.strip()
            v = v.split(" #", 1)[0].strip()
            try:
                out[cur][k] = float(v)
            except ValueError:
                pass
    return out


# The measure_multiplier version-aware tier regexes (mirrored — see
# PLAN-128/wave1/measure_multiplier.py MODEL_PRICING). Kept here as data so
# reconcile can flag a canonical row whose input/output rate disagrees with the
# tier its id would resolve to. (input, cw5, cw1, read, output) per Mtok.
_MM_TIERS: List[Tuple[str, Tuple[float, float, float, float, float]]] = [
    (r"opus-4-[01](?:\D|$)", (15.0, 18.75, 30.0, 1.50, 75.0)),
    (r"opus-4-(?:[2-9]|1\d)", (5.0, 6.25, 10.0, 0.50, 25.0)),
    (r"opus-(?:[5-9]|\d\d)", (5.0, 6.25, 10.0, 0.50, 25.0)),
    (r"sonnet-[3-9]", (3.0, 3.75, 6.00, 0.30, 15.0)),
    (r"haiku-4", (1.0, 1.25, 2.00, 0.10, 5.0)),
    (r"haiku-3", (0.80, 1.00, 1.60, 0.08, 4.0)),
]


def _mm_tier_for(model: str) -> Optional[Tuple[float, float, float, float, float]]:
    m = (model or "").lower()
    for rx, price in _MM_TIERS:
        if re.search(rx, m):
            return price
    return None


def reconcile(
    data: Dict[str, Any],
    cost_table_path: Optional[Path] = None,
) -> List[Dict[str, Any]]:
    """Diff canonical rows vs cost-table.yaml + measure_multiplier tiers.

    Returns a list of finding dicts ``{model, field, canonical, other, source,
    severity}``. Empty list ⇒ fully reconciled. NEVER writes any file."""
    findings: List[Dict[str, Any]] = []
    models = data.get("models") or {}
    ct = _load_cost_table_models(cost_table_path)

    for mid, row in models.items():
        c_in = float(row.get("input_per_mtok", 0.0))
        c_out = float(row.get("output_per_mtok", 0.0))

        # vs cost-table.yaml (input + output only — that's all it carries)
        if mid in ct:
            for field, cval in (("input_per_mtok", c_in), ("output_per_mtok", c_out)):
                oval = ct[mid].get(field)
                if oval is not None and abs(oval - cval) > 1e-9:
                    findings.append({
                        "model": mid, "field": field,
                        "canonical": cval, "other": oval,
                        "source": "cost-table.yaml", "severity": "warn",
                    })

        # vs measure_multiplier tier regex (full 5-tuple)
        tier = _mm_tier_for(mid)
        if tier is not None:
            pi, p5, p1, pr, po = tier
            checks = (
                ("input_per_mtok", c_in, pi),
                ("cache_write_5m_per_mtok", float(row.get("cache_write_5m_per_mtok", 0.0)), p5),
                ("cache_write_1h_per_mtok", float(row.get("cache_write_1h_per_mtok", 0.0)), p1),
                ("cache_read_per_mtok", float(row.get("cache_read_per_mtok", 0.0)), pr),
                ("output_per_mtok", c_out, po),
            )
            for field, cval, tval in checks:
                if abs(cval - tval) > 1e-9:
                    findings.append({
                        "model": mid, "field": field,
                        "canonical": cval, "other": tval,
                        "source": "measure_multiplier.MODEL_PRICING", "severity": "warn",
                    })
    return findings


# ---------------------------------------------------------------------------
# Build / regenerate from an OWNER-SUPPLIED models.dev blob (no network here)
# ---------------------------------------------------------------------------
def build_from_models_dev(
    raw: Dict[str, Any], today: Optional[date] = None
) -> Dict[str, Any]:
    """Transform an Owner-fetched models.dev JSON into our canonical schema and
    stamp provenance with a freshly-computed sha256.

    The Owner-supplied blob is expected to be the models.dev `api.json` shape
    (a dict keyed by provider → models). We only consume Anthropic `claude-*`
    rows; everything else is dropped (Claude-only by design, §DO-NOT-BUILD).

    This function does ZERO I/O — it is pure transform + hash. The caller writes
    the result. There is intentionally no urllib import in this module.
    """
    if today is None:
        today = date.today()
    models: Dict[str, Any] = {}
    for _provider, pdata in (raw.items() if isinstance(raw, dict) else []):
        candidate_models = []
        if isinstance(pdata, dict):
            mm = pdata.get("models")
            if isinstance(mm, dict):
                candidate_models = list(mm.items())
            elif isinstance(mm, list):
                candidate_models = [(m.get("id"), m) for m in mm if isinstance(m, dict)]
        for mid, mrow in candidate_models:
            if not isinstance(mid, str) or not mid.lower().startswith("claude"):
                continue
            if not isinstance(mrow, dict):
                continue
            cost = mrow.get("cost") or mrow.get("pricing") or {}
            inp = _f(cost.get("input"))
            out = _f(cost.get("output"))
            cache_read = _f(cost.get("cache_read"), default=round(inp * _CACHE_MULT_READ, 6))
            cw5 = _f(cost.get("cache_write_5m"), default=round(inp * _CACHE_MULT_5M, 6))
            cw1 = _f(cost.get("cache_write_1h"), default=round(inp * _CACHE_MULT_1H, 6))
            limit = mrow.get("limit") or {}
            models[mid] = {
                "input_per_mtok": inp,
                "cache_write_5m_per_mtok": cw5,
                "cache_write_1h_per_mtok": cw1,
                "cache_read_per_mtok": cache_read,
                "output_per_mtok": out,
                "tier": _infer_tier(mid),
                "tier_class": _infer_tier_class(mid),
                "context_window": _i(limit.get("context")),
                "max_output": _i(limit.get("output")),
            }
    if not models:
        raise CanonicalModelsError(
            "models.dev blob produced 0 claude-* rows — refusing to write an "
            "empty canonical table (fail-CLOSED)"
        )
    sha = compute_models_sha256(models)
    valid_until = date(today.year + (1 if today.month > 9 else 0),
                       ((today.month - 1 + 3) % 12) + 1, 1)
    return {
        "schema_version": "1.0",
        "provenance": {
            "source_url": "https://models.dev/api.json",
            "fetched_at": today.isoformat(),
            "fetched_by": "owner-fetch",
            "sha256": sha,
        },
        "staleness": {
            "valid_until": valid_until.isoformat(),
            "refresh_cadence_days": 90,
            "advisory_only": True,
        },
        "unknown_model_fallback": {
            "input_per_mtok": 0.0,
            "cache_write_5m_per_mtok": 0.0,
            "cache_write_1h_per_mtok": 0.0,
            "cache_read_per_mtok": 0.0,
            "output_per_mtok": 0.0,
            "policy": "S220 — unknown models cost 0 and are FLAGGED; never guess.",
        },
        "cache_multipliers": {
            "cache_write_5m": _CACHE_MULT_5M,
            "cache_write_1h": _CACHE_MULT_1H,
            "cache_read": _CACHE_MULT_READ,
        },
        "models": models,
    }


def _f(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _i(v: Any) -> Optional[int]:
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _infer_tier(mid: str) -> str:
    m = mid.lower()
    if "opus" in m:
        return "opus"
    if "sonnet" in m:
        return "sonnet"
    if "haiku" in m:
        return "haiku"
    return "unknown"


def _infer_tier_class(mid: str) -> str:
    m = mid.lower()
    if re.search(r"opus-4-[01](?:\D|$)", m):
        return "opus_legacy"
    if "opus" in m:
        return "opus_new"
    if "sonnet" in m:
        return "sonnet"
    if re.search(r"haiku-4", m):
        return "haiku_45"
    if re.search(r"haiku-3", m):
        return "haiku_35"
    return "unknown"


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _cmd_verify(args: argparse.Namespace) -> int:
    try:
        data = load_canonical_models(_path(args))
    except CanonicalModelsError as exc:
        print(f"[verify] FAIL: {exc}", file=sys.stderr)
        return 1
    ok, msg = verify_checksum(data)
    if ok:
        print(f"[verify] {msg}")
        return 0
    print(f"[verify] {msg}", file=sys.stderr)
    return 1


def _cmd_staleness(args: argparse.Namespace) -> int:
    try:
        data = load_canonical_models(_path(args))
    except CanonicalModelsError as exc:
        # Fail-open advisory: a missing file is a warning, not a hard error,
        # unless --strict.
        print(f"[staleness] cannot load: {exc}", file=sys.stderr)
        return 1 if args.strict else 0
    stale, msg = check_staleness(data)
    if stale:
        print(f"[staleness] WARN: {msg}", file=sys.stderr)
        return 1 if args.strict else 0
    print("[staleness] fresh")
    return 0


def _cmd_reconcile(args: argparse.Namespace) -> int:
    try:
        data = load_canonical_models(_path(args))
    except CanonicalModelsError as exc:
        print(f"[reconcile] cannot load: {exc}", file=sys.stderr)
        return 1 if args.strict else 0
    findings = reconcile(data)
    if args.json:
        print(json.dumps({"findings": findings}, indent=2))
    else:
        if not findings:
            print("[reconcile] all canonical rows agree with cost-table.yaml + tiers")
        else:
            for f in findings:
                print(
                    f"[reconcile] DIVERGENCE {f['model']}.{f['field']}: "
                    f"canonical={f['canonical']} vs {f['source']}={f['other']}",
                    file=sys.stderr,
                )
    # Reconcile is advisory: exit 0 unless --strict AND there are findings.
    return 1 if (args.strict and findings) else 0


def _cmd_fetch(args: argparse.Namespace) -> int:
    """OWNER-ONLY. Reads an Owner-downloaded models.dev JSON (file or stdin) and
    regenerates canonical_models.json. NO network access in this process."""
    src = args.source
    try:
        if src == "-":
            raw_text = sys.stdin.read()
        else:
            raw_text = Path(src).read_text(encoding="utf-8")
        raw = json.loads(raw_text)
    except (OSError, ValueError) as exc:
        print(f"[fetch] cannot read/parse source {src!r}: {exc}", file=sys.stderr)
        return 1
    try:
        built = build_from_models_dev(raw)
    except CanonicalModelsError as exc:
        print(f"[fetch] {exc}", file=sys.stderr)
        return 1
    out_path = Path(args.output) if args.output else _path(args)
    out_path.write_text(
        json.dumps(built, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    ok, msg = verify_checksum(built)
    print(f"[fetch] wrote {out_path} ({len(built['models'])} claude rows); {msg}")
    return 0 if ok else 1


def _path(args: argparse.Namespace) -> Path:
    return Path(args.canonical) if getattr(args, "canonical", None) else _DEFAULT_CANONICAL


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Build/verify/reconcile the canonical model-pricing table (PLAN-133 B1)."
    )
    p.add_argument("--canonical", help="Override path to canonical_models.json")
    sub = p.add_subparsers(dest="cmd")
    # Default (no subcommand) → verify.
    p.add_argument("--verify", action="store_true", help="Verify provenance checksum (fail-CLOSED)")
    p.add_argument("--check-staleness", dest="check_staleness", action="store_true",
                   help="Warn if past valid_until (advisory)")
    p.add_argument("--reconcile", action="store_true",
                   help="Diff vs cost-table.yaml + tiers; FLAG divergence (never overwrites)")
    p.add_argument("--strict", action="store_true",
                   help="Make staleness/reconcile findings non-zero exit (CI)")
    p.add_argument("--json", action="store_true", help="JSON output (reconcile)")
    p.add_argument("--fetch", dest="fetch_source", metavar="SRC",
                   help="OWNER-ONLY: build from an Owner-downloaded models.dev JSON (file or '-')")
    p.add_argument("-o", "--output", help="Output path for --fetch (default: in place)")
    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    # Map flat flags to handlers (no subparsers → simpler for CI calls).
    if args.fetch_source:
        args.source = args.fetch_source
        return _cmd_fetch(args)
    if args.reconcile:
        return _cmd_reconcile(args)
    if args.check_staleness:
        return _cmd_staleness(args)
    # default + --verify
    return _cmd_verify(args)


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
