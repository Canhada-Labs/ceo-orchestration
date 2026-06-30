"""Cookbook pattern loader + validator — PLAN-092 Wave A.2.

Stdlib-only per ADR-126 (no PyYAML, no jsonschema). Provides:
  - load_cookbook_patterns()   -> dict (parses .claude/data/cookbook_patterns.json)
  - validate_structure(payload) -> None | raises ValueError
  - match_pattern(prompt_text, payload) -> Optional[tuple[pattern_id, trigger_class, confidence_bucket]]

Consumed by:
  - .claude/hooks/check_agent_spawn.py (Wave A.4 callsite)
  - .claude/hooks/tests/test_cookbook_advisor_hook.py (Wave A.6 12 tests)
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# F-5.6-4ff5aff2 fix: expanded to 9 IDs matching PLAN-084/gap-B/B.7-cookbook.yaml.
# The 5 new IDs (COOK-P5..P9) cover the B.7 patterns missing from the catalogue.
CANONICAL_IDS = (
    "COOK-P1", "COOK-P2", "COOK-P3", "COOK-P4",
    "COOK-P5", "COOK-P6", "COOK-P7", "COOK-P8", "COOK-P9",
)
REQUIRED_FIELDS = (
    "title", "trigger_class", "task_signature_regex", "suggestion", "doc_anchor"
)
AUDIT_FIELDS_WHITELIST = ("pattern_id", "trigger_class", "match_confidence_bucket")
KILL_SWITCH_ENV = "CEO_COOKBOOK_ADVISOR_ENABLED"


def _default_data_path() -> Path:
    root = os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd()
    return Path(root) / ".claude" / "data" / "cookbook_patterns.json"


def load_cookbook_patterns(path: Optional[Path] = None) -> Dict[str, Any]:
    """Load + validate cookbook_patterns.json. Raises ValueError on bad shape."""
    p = path or _default_data_path()
    with open(p, "r", encoding="utf-8") as fh:
        payload = json.load(fh)
    validate_structure(payload)
    return payload


def validate_structure(payload: Dict[str, Any]) -> None:
    """Stdlib-only schema enforcement (dict-key checks + required-field assertions)."""
    if not isinstance(payload, dict):
        raise ValueError("cookbook_patterns: top-level must be dict")
    patterns = payload.get("patterns")
    if not isinstance(patterns, dict):
        raise ValueError("cookbook_patterns: 'patterns' must be dict")
    missing_ids = [pid for pid in CANONICAL_IDS if pid not in patterns]
    if missing_ids:
        raise ValueError(f"cookbook_patterns: missing canonical IDs {missing_ids}")
    for pid in CANONICAL_IDS:
        entry = patterns[pid]
        if not isinstance(entry, dict):
            raise ValueError(f"cookbook_patterns[{pid}]: must be dict")
        for field in REQUIRED_FIELDS:
            if field not in entry:
                raise ValueError(
                    f"cookbook_patterns[{pid}]: missing required field '{field}'"
                )
        regexes = entry["task_signature_regex"]
        if not isinstance(regexes, list) or not regexes:
            raise ValueError(
                f"cookbook_patterns[{pid}].task_signature_regex must be non-empty list"
            )
        for rx in regexes:
            if not isinstance(rx, str):
                raise ValueError(
                    f"cookbook_patterns[{pid}].task_signature_regex: entries must be str"
                )
            try:
                re.compile(rx)
            except re.error as exc:
                raise ValueError(
                    f"cookbook_patterns[{pid}]: invalid regex '{rx}': {exc}"
                )


def _confidence_bucket(match_count: int, regex_count: int) -> str:
    """Map (match_count / regex_count) ratio to coarse bucket. Privacy-preserving."""
    if regex_count <= 0:
        return "low"
    ratio = match_count / regex_count
    if ratio >= 0.50:
        return "high"
    if ratio >= 0.25:
        return "medium"
    return "low"


def match_pattern(
    prompt_text: str,
    payload: Optional[Dict[str, Any]] = None,
) -> Optional[Tuple[str, str, str]]:
    """Match prompt_text against pattern regexes. Returns (pattern_id, trigger_class, bucket) or None.

    Returns FIRST match in canonical order (COOK-P1 -> COOK-P2 -> COOK-P3 -> COOK-P4).
    Raw prompt_text is NEVER persisted by callers (privacy invariant per AC3b).
    """
    if not isinstance(prompt_text, str) or not prompt_text:
        return None
    if payload is None:
        try:
            payload = load_cookbook_patterns()
        except (OSError, ValueError):
            return None
    patterns = payload.get("patterns", {})
    for pid in CANONICAL_IDS:
        entry = patterns.get(pid)
        if not isinstance(entry, dict):
            continue
        regexes: List[str] = entry.get("task_signature_regex", []) or []
        match_count = 0
        for rx in regexes:
            try:
                if re.search(rx, prompt_text):
                    match_count += 1
            except re.error:
                continue
        if match_count >= 1:
            trigger_class = str(entry.get("trigger_class", "unknown"))
            bucket = _confidence_bucket(match_count, len(regexes))
            return (pid, trigger_class, bucket)
    return None


def kill_switch_enabled() -> bool:
    """True if cookbook-advisor emit is ENABLED (default ON; opt-out via env=0)."""
    val = os.environ.get(KILL_SWITCH_ENV, "1").strip()
    return val not in ("0", "false", "False", "no", "off")
