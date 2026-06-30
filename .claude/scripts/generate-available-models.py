#!/usr/bin/env python3
"""generate-available-models.py — availableModels mirror GENERATED from ADR-149.

PLAN-135 W1 unit s1 (HARVEST-REPORT S1; ADR-149 Amendment 1 §A1.2).

Single source: the machine-parseable ``AVAILABLE_MODELS_WORKING_SET`` block
inside ``.claude/adr/ADR-149-model-id-allowlist.md``. This script:

- **generate mode** (default): emits the ``{"availableModels": [...]}`` JSON
  fragment derived from the ADR block, preserving ADR order (the tuple order
  is normative — byte-deterministic generation).
- **--check mode**: resolves the live settings (project ``.claude/settings.json``
  plus ``.claude/settings.local.json`` overlay, mimicking the documented
  harness merge semantics: ``availableModels`` arrays merge+dedupe across
  layers; ``fallbackModel`` does NOT merge — highest-precedence layer wins
  wholesale) and diffs them against the ADR:
    * ``availableModels`` absent  -> graceful note, exit 0 (pre-ceremony state)
    * ``availableModels`` present -> must equal the generated list exactly
    * ``fallbackModel``  absent  -> graceful note (pre-ceremony state)
    * ``fallbackModel``  present -> chain length 1..3, every member inside
      the working set (ADR-149 Amendment 1 clause (a))

Pre-amendment tolerance: when the live ADR does not yet carry Amendment 1
(the amendment ships STAGED and lands only at the Owner ceremony), the
parser falls back to the base ``VETO_FLOOR_ALLOWED`` block members and
prints a loud stderr note — the script runs green on the unamended tree.

Exit codes: 0 = OK / graceful-absent; 1 = drift or clause violation;
2 = infrastructure (ADR or settings file unreadable, no parseable block).

Advisory + read-only: never writes any file. Stdlib-only. Python >= 3.9.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ADR = REPO_ROOT / ".claude" / "adr" / "ADR-149-model-id-allowlist.md"
DEFAULT_SETTINGS = REPO_ROOT / ".claude" / "settings.json"

WORKING_SET_TOKEN = "AVAILABLE_MODELS_WORKING_SET"
VETO_FLOOR_TOKEN = "VETO_FLOOR_ALLOWED"
FALLBACK_CHAIN_MAX = 3  # documented harness cap (model-config: "capped at three")

# Model-id / alias shape: claude-opus-4-8, claude-fable-5, sonnet, opus[1m], ...
_ID_RE = re.compile(r'"([A-Za-z0-9][A-Za-z0-9._\[\]-]*)"')


def _extract_block_ids(adr_text: str, token: str) -> Optional[List[str]]:
    """Return the quoted ids inside the ``token = (...)`` / ``{...}`` block.

    Tolerant of frozenset({...}) and tuple (...) literals, comments, and
    trailing commas. Returns None when the token is absent; [] only when the
    block exists but carries no quoted ids (treated as infra error upstream).
    """
    idx = adr_text.find(token)
    if idx < 0:
        return None
    # Find the first opening bracket after the token, then scan to its match.
    open_idx = -1
    open_ch = ""
    for i in range(idx, min(len(adr_text), idx + 200)):
        if adr_text[i] in "({":
            open_idx = i
            open_ch = adr_text[i]
            break
    if open_idx < 0:
        return []
    close_ch = ")" if open_ch == "(" else "}"
    depth = 0
    end_idx = -1
    for i in range(open_idx, len(adr_text)):
        ch = adr_text[i]
        if ch == open_ch:
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0:
                end_idx = i
                break
    if end_idx < 0:
        return []
    block = adr_text[open_idx : end_idx + 1]
    seen = set()
    ids: List[str] = []
    for match in _ID_RE.finditer(block):
        mid = match.group(1)
        if mid not in seen:
            seen.add(mid)
            ids.append(mid)
    return ids


def parse_working_set(adr_path: Path) -> Tuple[List[str], str]:
    """Parse the ADR; return (ids, source) where source is the block used."""
    try:
        text = adr_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RuntimeError("cannot read ADR at {}: {}".format(adr_path, exc))
    ids = _extract_block_ids(text, WORKING_SET_TOKEN)
    if ids:
        return ids, WORKING_SET_TOKEN
    fallback = _extract_block_ids(text, VETO_FLOOR_TOKEN)
    if fallback:
        sys.stderr.write(
            "[generate-available-models] NOTE: ADR-149 Amendment 1 "
            "({}) not found in {} — falling back to the base {} members "
            "(pre-amendment state; the working-set block lands at the "
            "PLAN-135 W1 Owner ceremony).\n".format(
                WORKING_SET_TOKEN, adr_path, VETO_FLOOR_TOKEN
            )
        )
        return fallback, VETO_FLOOR_TOKEN
    raise RuntimeError(
        "no parseable {} or {} block in {}".format(
            WORKING_SET_TOKEN, VETO_FLOOR_TOKEN, adr_path
        )
    )


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise RuntimeError("cannot read settings at {}: {}".format(path, exc))
    except ValueError as exc:
        raise RuntimeError("settings file {} is not valid JSON: {}".format(path, exc))


def resolve_settings(settings_path: Path) -> Tuple[Optional[List[str]], Optional[List[str]]]:
    """Resolve (availableModels, fallbackModel) across project + local layers.

    Mimics the documented harness semantics for the two repo-scope layers:
    - availableModels: arrays MERGE + dedupe (project order first, then any
      local additions) — a local layer can only ADD, which --check flags.
    - fallbackModel: NO merge — the highest-precedence layer that defines it
      supplies the entire chain (local wins over project).
    User-level and managed layers are outside repo scope (honest boundary,
    ADR-149 Amendment 1 §A1.4).
    """
    project = _load_json(settings_path)
    local_path = settings_path.with_name("settings.local.json")
    local = _load_json(local_path) if local_path.exists() else {}

    def _as_list(value: object) -> Optional[List[str]]:
        if value is None:
            return None
        if isinstance(value, str):
            return [value]
        if isinstance(value, list):
            return [str(v) for v in value]
        return None

    avail_project = _as_list(project.get("availableModels"))
    avail_local = _as_list(local.get("availableModels"))
    if avail_project is None and avail_local is None:
        available: Optional[List[str]] = None
    else:
        merged: List[str] = []
        for layer in (avail_project or [], avail_local or []):
            for mid in layer:
                if mid not in merged:
                    merged.append(mid)
        available = merged

    fallback = _as_list(local.get("fallbackModel"))
    if fallback is None:
        fallback = _as_list(project.get("fallbackModel"))
    return available, fallback


def run_check(working_set: List[str], settings_path: Path) -> int:
    available, fallback = resolve_settings(settings_path)
    failures: List[str] = []

    if available is None:
        print(
            "CHECK availableModels: key absent in resolved settings "
            "(pre-ceremony state) — OK"
        )
    elif available == working_set:
        print(
            "CHECK availableModels: MATCH ({} ids, ADR order preserved)".format(
                len(available)
            )
        )
    else:
        failures.append(
            "availableModels drift:\n  ADR-149  : {}\n  resolved : {}".format(
                json.dumps(working_set), json.dumps(available)
            )
        )

    if fallback is None:
        print(
            "CHECK fallbackModel: key absent in resolved settings "
            "(pre-ceremony state) — OK"
        )
    else:
        if not 1 <= len(fallback) <= FALLBACK_CHAIN_MAX:
            failures.append(
                "fallbackModel chain length {} outside 1..{}: {}".format(
                    len(fallback), FALLBACK_CHAIN_MAX, json.dumps(fallback)
                )
            )
        escapees = [m for m in fallback if m not in working_set]
        if escapees:
            failures.append(
                "fallbackModel escapes the working set (clause (a) "
                "violation): {}".format(json.dumps(escapees))
            )
        if not failures:
            print(
                "CHECK fallbackModel: chain {} inside working set, "
                "length {} <= {}".format(
                    json.dumps(fallback), len(fallback), FALLBACK_CHAIN_MAX
                )
            )

    for failure in failures:
        sys.stderr.write("[generate-available-models] FAIL: {}\n".format(failure))
    return 1 if failures else 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Emit (or --check) the availableModels fragment "
        "generated from ADR-149."
    )
    parser.add_argument(
        "--adr",
        type=Path,
        default=DEFAULT_ADR,
        help="ADR-149 path (default: live repo copy)",
    )
    parser.add_argument(
        "--settings",
        type=Path,
        default=DEFAULT_SETTINGS,
        help="settings.json to diff in --check mode "
        "(a sibling settings.local.json is overlaid when present)",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="diff resolved settings against the ADR instead of emitting JSON",
    )
    args = parser.parse_args(argv)

    try:
        working_set, source = parse_working_set(args.adr)
    except RuntimeError as exc:
        sys.stderr.write("[generate-available-models] ERROR: {}\n".format(exc))
        return 2

    if args.check:
        try:
            return run_check(working_set, args.settings)
        except RuntimeError as exc:
            sys.stderr.write("[generate-available-models] ERROR: {}\n".format(exc))
            return 2

    fragment = {"availableModels": working_set}
    print(json.dumps(fragment, indent=2))
    if source == WORKING_SET_TOKEN:
        sys.stderr.write(
            "[generate-available-models] source: ADR-149 Amendment 1 "
            "{} ({} ids)\n".format(WORKING_SET_TOKEN, len(working_set))
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
