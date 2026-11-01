"""Extracted cost-transcripts implementation: pricing."""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

#: Embedded fallback / correction source. Report 05-finops-routing.md §1.2 +
#: §1.4 (S339, measured 2026-08-03..2026-09-02). Sonnet 5 at the
#: Owner-ratified 2026-09-01 intro rate (CLAUDE.md commit e47bf5d).
#: ADR-149 Amendment 3 (S357): claude-opus-5-5 at $4/$20 (pricing page
#: fetched 2026-09-22).
_EMBEDDED_PRICING: Dict[str, Dict[str, float]] = {
    "claude-fable-5-1": {"input_per_mtok": 10.00, "output_per_mtok": 50.00},
    "claude-fable-5": {"input_per_mtok": 10.00, "output_per_mtok": 50.00},
    "claude-opus-5-5": {"input_per_mtok": 4.00, "output_per_mtok": 20.00},
    "claude-opus-5": {"input_per_mtok": 5.00, "output_per_mtok": 25.00},
    "claude-opus-4-8": {"input_per_mtok": 5.00, "output_per_mtok": 25.00},
    "claude-sonnet-5": {"input_per_mtok": 2.00, "output_per_mtok": 10.00},
    "claude-sonnet-4-6": {"input_per_mtok": 3.00, "output_per_mtok": 15.00},
    "claude-haiku-4-5": {"input_per_mtok": 1.00, "output_per_mtok": 5.00},
}

#: Applied ONLY on top of a successfully-parsed DEFAULT --pricing path
#: (never on an explicit caller-supplied path), and ONLY where the
#: parsed row differs from the value below. An entry that matches the
#: file is reported as a no-op, never as a correction. See module
#: docstring.
_RATIFIED_OVERRIDES_FOR_DEFAULT_TABLE: Dict[str, Dict[str, float]] = {
    "claude-sonnet-5": {"input_per_mtok": 2.00, "output_per_mtok": 10.00},
}

#: docs/provider-pricing.md lines ~130-153 ("Cache-tier multipliers"):
#: fresh input 1.00x, cache write 5m 1.25x, cache write 1h 2.00x, cache
#: read 0.10x (base input rate) — EXCEPT the per-model entries below:
#: claude-fable-5-1 at 0.025x (pricing page 2026-09-01, ADR-149
#: Amendment 2) and claude-opus-5-5 at 0.05x (pricing page 2026-09-22,
#: ADR-149 Amendment 3). The pricing page also prices Mythos 5.1 cache
#: hits at 0.025x; that model is outside the ADR-149 working set and
#: carries no entry. Mirrors budget-summary.py's
#: _CACHE_READ_MULTIPLIER_OVERRIDES exactly (bound by
#: test_model_fleet_presence.py since S357).
_CACHE_READ_MULTIPLIER_DEFAULT: float = 0.10
_CACHE_READ_MULTIPLIER_OVERRIDES: Dict[str, float] = {
    "claude-fable-5-1": 0.025,
    "claude-opus-5-5": 0.05,
}
_CACHE_WRITE_5M_MULTIPLIER: float = 1.25
_CACHE_WRITE_1H_MULTIPLIER: float = 2.00

_MODEL_SUFFIX_RE = re.compile(r"\[[^\[\]]*\]$")


def _cache_read_multiplier(model_id: str) -> float:
    return _CACHE_READ_MULTIPLIER_OVERRIDES.get(model_id, _CACHE_READ_MULTIPLIER_DEFAULT)


def _cache_read_exceptions_text() -> str:
    """Per-model cache-read exceptions rendered FROM the override table
    (ADR-149 Amendment 3, S357: the help text is derived, never re-listed)."""
    return ", ".join(
        "%gx for %s" % (mult, model_id)
        for model_id, mult in sorted(_CACHE_READ_MULTIPLIER_OVERRIDES.items())
    )


def normalize_model_id(raw: Optional[str]) -> Optional[str]:
    """Strip a trailing context-window suffix (e.g. ``[1m]``). No guessing."""
    if not isinstance(raw, str) or not raw.strip():
        return None
    return _MODEL_SUFFIX_RE.sub("", raw.strip())


def _safe_text(value: Any, limit: int = 80) -> str:
    """Untrusted text (a transcript or sidecar field) made safe to PRINT.

    Every non-printable character -- an ESC, a newline, a bidi override --
    becomes ``?``, so a forged ``ROUTING INVARIANT ... GREEN`` line or a
    terminal escape cannot ride in on a model id, a session id, a label or
    an archetype name. It is applied where the text ENTERS the instrument
    (``_extract_record`` for every transcript-derived string, the routing
    reader for every sidecar-derived one), so every renderer downstream --
    the CLI table, the JSON report, the two callers' blocks -- inherits it
    and a new print site cannot forget it.
    """
    return "".join(c if c.isprintable() else "?" for c in str(value))[:limit]


def _parse_cost_table_yaml(text: str) -> Dict[str, Dict[str, float]]:
    """Minimal parser for the ``models:`` block of cost-table.yaml's mini-YAML
    subset (top-level scalars + one level of 2-space-indented nested dicts —
    see that file's own header comment). Extracts ONLY the two numeric
    fields this instrument needs; anything else (``tier``, ``source_url``,
    ...) is ignored. Never raises — a malformed file just yields {}.
    """
    models: Dict[str, Dict[str, float]] = {}
    in_models = False
    current: Optional[str] = None
    for raw_line in text.splitlines():
        if not raw_line.strip():
            continue
        stripped = raw_line.strip()
        if stripped.startswith("#"):
            continue
        if not raw_line.startswith(" ") and not raw_line.startswith("\t"):
            in_models = raw_line.rstrip() == "models:"
            current = None
            continue
        if not in_models:
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        if indent == 2 and stripped.endswith(":"):
            current = stripped[:-1].strip()
            models.setdefault(current, {})
            continue
        if indent >= 4 and current is not None:
            field_txt = stripped
            if "#" in field_txt:
                field_txt = field_txt.split("#", 1)[0].rstrip()
            if ":" not in field_txt:
                continue
            key, _, val = field_txt.partition(":")
            key = key.strip()
            val = val.strip()
            if key in ("input_per_mtok", "output_per_mtok"):
                try:
                    models[current][key] = float(val)
                except ValueError:
                    continue
    return models


@dataclass
class PricingResult:
    table: Dict[str, Dict[str, float]]
    source: str  # human-readable description for --help / report footer
    used_fallback: bool


def _override_is_a_no_op(
    current: Optional[Dict[str, float]], override: Dict[str, float]
) -> bool:
    """True when the parsed row ALREADY carries every ratified value.

    Guards the one thing an unconditional overwrite cannot express: the
    difference between a stale file that WAS corrected and a file that
    was already right. Missing row / wrong type => not a no-op, so the
    override still lands.
    """
    if not isinstance(current, dict):
        return False
    for key, value in override.items():
        have = current.get(key)
        if isinstance(have, bool) or not isinstance(have, (int, float)):
            return False
        if abs(float(have) - float(value)) > 1e-9:
            return False
    return True


def load_pricing(pricing_arg: Optional[str]) -> PricingResult:
    """Resolve the active {model_id: {input_per_mtok, output_per_mtok}}
    table per the contract in the module docstring."""
    is_default_path = pricing_arg is None
    path = Path(pricing_arg) if pricing_arg else (_SCRIPT_DIR / "cost-table.yaml")

    text: Optional[str] = None
    if path.is_file():
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            text = None

    parsed: Dict[str, Dict[str, float]] = _parse_cost_table_yaml(text) if text else {}
    complete_rows = {
        mid: row
        for mid, row in parsed.items()
        if "input_per_mtok" in row and "output_per_mtok" in row
    }

    if not complete_rows:
        return PricingResult(
            table=dict(_EMBEDDED_PRICING),
            source=(
                "embedded (report 05-finops-routing.md \xa71.4; %s could not "
                "be parsed / had no complete models: rows)" % path
            ),
            used_fallback=True,
        )

    table = dict(complete_rows)
    source = "parsed from %s" % path
    if is_default_path:
        # Conditional by construction: an override that merely restates
        # what the file already says is NOT a correction. Reporting it as
        # one prints a fix that fixed nothing, and applying it anyway
        # would silently mask a legitimate refresh of the table.
        applied: List[str] = []
        noop: List[str] = []
        for mid in sorted(_RATIFIED_OVERRIDES_FOR_DEFAULT_TABLE):
            override = _RATIFIED_OVERRIDES_FOR_DEFAULT_TABLE[mid]
            if _override_is_a_no_op(table.get(mid), override):
                noop.append(mid)
                continue
            table[mid] = dict(override)
            applied.append(
                "%s -> $%g/$%g"
                % (
                    mid,
                    override["input_per_mtok"],
                    override["output_per_mtok"],
                )
            )
        if applied:
            source += (
                " + ratified correction (%s; 2026-09-01, CLAUDE.md "
                "e47bf5d)" % ", ".join(applied)
            )
        if noop:
            source += (
                " + ratified correction NOT needed for %s (the file "
                "already carries the ratified rate)" % ", ".join(noop)
            )
    return PricingResult(table=table, source=source, used_fallback=False)


# ---------------------------------------------------------------------------
# Transcript discovery + parsing
# ---------------------------------------------------------------------------


