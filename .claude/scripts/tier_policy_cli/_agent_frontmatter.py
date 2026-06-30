"""PLAN-043 C-P0-10 — Agent frontmatter helper (staged non-canonical).

STAGED LOCATION: this module lives at
``.claude/scripts/tier_policy_cli/_agent_frontmatter.py`` (non-canonical;
renamed from ``tier_policy/`` per PLAN-076 fork (f))
until Owner sentinel authorizes promotion to canonical
``.claude/hooks/_lib/agent_frontmatter.py``. The canonical-edit hook
correctly blocked direct write to ``_lib/`` without sentinel (Phase 0
governance boundary holding).

Rationale per Round 1 convergent closure C-P0-10: the previous PLAN-
043 text claimed ``apply.py`` could reuse ``upgrade.sh``'s
``upgrade_agents_canonical_only`` Bash function for adopter-override
diff-detect — but that function is monolithic Bash (``grep`` + ``awk``)
and is NOT importable from Python. This module provides the canonical
Python API; in Phase 5 closeout it moves to ``_lib/`` (via sentinel)
and ``upgrade.sh`` either shells out to ``python3 -m _lib.agent_
frontmatter`` or maintains a dual-implementation contract verified by
a byte-identity test.

API:

    parse_model_field(path) -> Optional[str]
        Returns the ``model:`` value from the file's YAML frontmatter,
        or None if the field is absent / file malformed. Fail-open.

    detect_adopter_override(adopter_path, framework_baseline_path)
            -> bool
        Returns True iff adopter's ``model:`` field diverges from
        framework baseline (implying adopter customization per
        PLAN-021). Conservative on ambiguity (True = do not overwrite).

stdlib-only (ADR-002). Python >= 3.9.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterator, Optional


_MODEL_FIELD_PREFIX = "model:"
_FRONTMATTER_FENCE = "---"


def _iter_frontmatter_lines(path: Path) -> "Iterator[str]":
    """Yield raw lines inside the YAML frontmatter block.

    The frontmatter is delimited by two ``---`` fences at the start
    of the file. Returns empty (no yields) on missing file, missing
    fences, or I/O error — fail-open per ADR-005.
    """
    try:
        with path.open("r", encoding="utf-8-sig") as f:
            first = None
            for line in f:
                stripped = line.strip()
                if not stripped:
                    continue
                first = stripped
                break
            if first != _FRONTMATTER_FENCE:
                return
            for line in f:
                if line.rstrip("\r\n").strip() == _FRONTMATTER_FENCE:
                    return
                yield line
    except OSError:
        return


def parse_model_field(path) -> Optional[str]:
    """Return the ``model:`` value from file's YAML frontmatter.

    Args:
        path: Path or str to ``.claude/agents/<slug>.md``.

    Returns:
        String value (stripped, comments dropped, quotes stripped)
        OR None if:
        - File does not exist
        - File has no frontmatter
        - Frontmatter has no ``model:`` key
        - ``model:`` value is empty (means inherit-CEO per ADR-052)
        - File unreadable (fail-open per ADR-005)
    """
    p = Path(path) if not isinstance(path, Path) else path
    for line in _iter_frontmatter_lines(p):
        stripped = line.lstrip()
        if not stripped.startswith(_MODEL_FIELD_PREFIX):
            continue
        value_raw = stripped[len(_MODEL_FIELD_PREFIX):]
        hash_idx = _find_unquoted_hash(value_raw)
        if hash_idx is not None:
            value_raw = value_raw[:hash_idx]
        value = value_raw.strip()
        if not value:
            return None
        if (
            len(value) >= 2
            and value[0] == value[-1]
            and value[0] in ('"', "'")
        ):
            value = value[1:-1]
        return value if value else None
    return None


def _find_unquoted_hash(s: str) -> Optional[int]:
    """Return index of first ``#`` not inside quotes, or None."""
    in_single = False
    in_double = False
    for i, ch in enumerate(s):
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            return i
    return None


def detect_adopter_override(
    adopter_path,
    framework_baseline_path,
) -> bool:
    """Return True iff adopter's ``model:`` field differs from baseline.

    PLAN-021 contract: adopter customized → PRESERVE (caller must NOT
    overwrite). Used by tier_policy_cli/apply.py before frontmatter writes.

    Args:
        adopter_path: Path to the current (adopter's) agent file.
        framework_baseline_path: Path to the framework baseline
            (templates/ copy or fresh checkout).

    Returns:
        True — adopter modified (or removed) the ``model:`` field;
            caller must skip the write.
        False — adopter's value matches baseline; safe to update.

    Conservative policy: on ambiguity (missing baseline, etc) returns
    True to maximize preservation of adopter state.
    """
    adopter = parse_model_field(adopter_path)
    baseline = parse_model_field(framework_baseline_path)

    if adopter is None and baseline is None:
        return False
    if adopter is None:
        return True
    if baseline is None:
        return True
    return adopter != baseline


def _serialize_for_identity_test(
    adopter_path,
    framework_baseline_path,
) -> str:
    """Canonical string for cross-impl byte-identity testing.

    Used by tests to verify Python helper + Bash upgrade.sh produce
    identical adopter-override decisions.
    """
    a = parse_model_field(adopter_path)
    b = parse_model_field(framework_baseline_path)
    is_override = detect_adopter_override(
        adopter_path, framework_baseline_path
    )
    return "{a}|{b}|{o}".format(
        a=(a if a is not None else ""),
        b=(b if b is not None else ""),
        o=("1" if is_override else "0"),
    )


if __name__ == "__main__":
    # Minimal CLI surface so upgrade.sh can shell out:
    #   python3 .claude/scripts/tier_policy_cli/_agent_frontmatter.py \
    #     --detect-override <adopter_path> <baseline_path>
    # Exit 0 = no override; 1 = adopter override detected; 2 = arg err.
    import sys
    if len(sys.argv) == 4 and sys.argv[1] == "--detect-override":
        result = detect_adopter_override(sys.argv[2], sys.argv[3])
        sys.exit(1 if result else 0)
    if len(sys.argv) == 3 and sys.argv[1] == "--parse-model":
        value = parse_model_field(sys.argv[2])
        sys.stdout.write(value or "")
        sys.stdout.write("\n")
        sys.exit(0)
    sys.stderr.write(
        "usage: _agent_frontmatter.py --detect-override A B\n"
        "       _agent_frontmatter.py --parse-model PATH\n"
    )
    sys.exit(2)
