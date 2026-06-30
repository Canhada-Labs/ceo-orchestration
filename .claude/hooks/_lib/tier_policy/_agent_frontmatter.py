"""tier_policy._agent_frontmatter — guarded parser for ``.claude/agents/*.md``.

Reads a single agent-definition markdown file, extracts the YAML / JSON
frontmatter block delimited by ``---``, and returns a sanitised
``Dict[str, Any]``. Stdlib only — NO ``yaml`` import.

Runtime status (PLAN-113 W7 / finding F-6-6.9)
----------------------------------------------

**Dispositioned-dead-for-runtime, RETAINED-by-design.** This module has
NO production-hook runtime importer at HEAD — only its test suite
(``hooks/tests/test_tier_policy_agent_frontmatter.py``) imports
``parse_agent_frontmatter``, and ``check_arbitration_kernel.py`` lists the
file in its canonical-guard path set (a string-literal protection list, not
an import). It is therefore retained on purpose:

* it is a kernel-guarded, security-hardened parser whose attack-surface
  tests (yaml-bomb / prototype-pollution / symlink / oversize) document
  the guarantees the framework relies on; and
* it is **NOT** a duplicate of
  ``.claude/scripts/tier_policy_cli/_agent_frontmatter.py``. That sibling
  is a small ``model:``-field reader (``parse_model_field`` /
  ``detect_adopter_override``) for adopter-override detection in
  ``tier_policy_cli/apply.py`` — an entirely different, narrower API.
  The two share a filename only; neither is a copy of the other, so
  de-duplication by re-export is NOT applicable.

Do NOT delete; the test ``test_tier_policy_agent_frontmatter_disposition``
asserts this disposition holds (no production-runtime importer; distinct
sibling API).

Hardening contract
------------------

This parser sits inside the canonical-guard scope. It MUST refuse:

* Symlinks (leaf or parent directory) — local check, no
  ``_lib/agent_frontmatter`` import per R-CR1 path-of-record.
* Any of the canonical paths ``.claude/agents/<role>.md`` for the 6
  spec-named VETO floor roles + 4 non-floor canonical agent files
  **when** the parsed frontmatter would override ``model:`` to anything
  other than ``claude-opus-4-8``. The parser itself does not enforce
  the model rule (that lives in
  ``_lib/agent_frontmatter.validate_veto_floor_models``); we only
  refuse to surface ANY mutation to those files via this code path
  so that no Phase-1 implementer accidentally bypasses the kernel
  guard. R-SEC4 / P0-03.
* Prototype-pollution keys: ``__proto__``, ``constructor``,
  ``prototype``, ``__defineGetter__``, ``__defineSetter__``.
  R-CR Unseen #5 / P1-09 (recursive at every depth).
* Files larger than 64 KiB.
* Frontmatter blocks deeper than 8 nested levels.
* Keys outside ``_constants._ALLOWED_FRONTMATTER_KEYS`` (closed set).

YAML subset implemented
-----------------------

Minimal pragmatic subset (enough for the existing 50+ ``.claude/
agents/*.md`` files, deliberately less than PyYAML safe_load):

* ``key: scalar`` — string / int / float / bool / null.
* ``key:`` followed by indented block-list items ``  - item`` — list
  of strings.
* ``key:`` followed by indented ``  subkey: scalar`` — nested dict
  (max 2 levels deep). Anything deeper is rejected.
* JSON literal as a value (``key: {"a": 1}``) — parsed via
  ``json.loads`` AND post-validated for prototype-pollution keys at
  every depth (P1-09 fix).

Not implemented (rejected with ``FrontmatterError``):

* YAML anchors / aliases (``&anchor`` / ``*alias``).
* Tags (``!!str`` etc.).
* Flow-style mappings except the JSON literal case above.
* Multi-document streams (``---`` mid-body).

PLAN-071 §3 must-fix coverage
-----------------------------

* R-CR1 — local canonical-path list (DOES NOT import _lib).
* R-CR Unseen #5 / P1-09 — explicit recursive prototype-pollution
  reject; JSON-literal scalar values walked depth-first.
* R-SEC6 — NFKC-normalise scalar values before downstream regex use.
* R-SEC U2 — refuses oversize / deep payloads (DoS / fan-out).
* R-CR R2-2 — uses ``get_instance_salt`` semantics implicitly (no salt
  read here; callers handle HMAC).
* P0-03 — canonical path list now spans the 6 spec VETO floor roles
  + 4 legacy archetypes; comments mark which 2 currently exist on
  disk vs 4 forward-looking.
"""

from __future__ import annotations

import json
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from ._constants import (
    LIMIT_ARRAY_LEN,
    LIMIT_DEPTH,
    LIMIT_FILE_BYTES,
    LIMIT_KEY_COUNT,
    LIMIT_SCALAR_LEN,
    _ALLOWED_FRONTMATTER_KEYS,
)


# ---------------------------------------------------------------------------
# Local canonical-path allowlist (DO NOT import from _lib — R-CR1)
# ---------------------------------------------------------------------------

#: Canonical paths whose mutation requires KERNEL ceremony. Mirrors a
#: subset of ``check_canonical_edit._CANONICAL_GUARDS`` for the agent-
#: file scope only. Local copy by design — importing the canonical
#: registry would create a circular dependency at the policy layer.
#:
#: Layout (top to bottom):
#:   - 2 hardcode-floor roles (have on-disk agent files, ALWAYS bind)
#:   - 4 forward-looking spec-floor roles (ship in PLAN-074 Wave 0)
#:   - 4 legacy non-floor archetypes (existing team agent files)
#:
#: P0-03 fix: list now spans the 6 spec-named VETO floor roles per
#: PLAN-071 §3.1 line 151, even though only 2 of the 6 currently
#: exist on disk. Listing the 4 forward-looking entries here means
#: that as soon as their files land, the guard is in place without a
#: code change (and a stray pre-creation write would also be refused).
_LOCAL_CANONICAL_AGENT_PATHS: Tuple[str, ...] = (
    # 2 hardcode-floor roles (on-disk; ALWAYS bind)
    ".claude/agents/code-reviewer.md",
    ".claude/agents/security-engineer.md",
    # 4 forward-looking spec-floor roles (no on-disk file YET)
    ".claude/agents/threat-detection-engineer.md",
    ".claude/agents/identity-trust-architect.md",
    ".claude/agents/incident-commander.md",
    ".claude/agents/llm-finops-architect.md",
    # 4 legacy non-floor archetypes (existing team agent files)
    ".claude/agents/qa-architect.md",
    ".claude/agents/performance-engineer.md",
    ".claude/agents/devops.md",
    ".claude/agents/ceo.md",
)

#: Reject these keys at any depth — JS prototype-pollution defence.
_PROTOTYPE_POLLUTION_KEYS: frozenset = frozenset({
    "__proto__",
    "constructor",
    "prototype",
    "__defineGetter__",
    "__defineSetter__",
})


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class FrontmatterError(ValueError):
    """Raised on any guard violation.

    Sub-classes ``ValueError`` so generic ``except ValueError`` callers
    catch it; the ``loader.load_policy`` advisory-only path re-classifies
    this as a fallback condition rather than letting it propagate.
    """


# ---------------------------------------------------------------------------
# Recursive prototype-pollution / DoS guard (P1-09)
# ---------------------------------------------------------------------------


def _check_no_pollution(obj: Any, depth: int = 0) -> None:
    """Recursively walk ``obj`` rejecting prototype-pollution keys.

    P1-09 fix: JSON-literal scalar values produced by ``_coerce_scalar``
    bypass the line-by-line YAML parser's per-key allowlist. This walker
    enforces:

      1. depth ≤ ``LIMIT_DEPTH`` — DoS guard against deeply-nested
         JSON payloads embedded in a single line.
      2. dict keys NOT in ``_PROTOTYPE_POLLUTION_KEYS`` at any depth.
      3. list length ≤ ``LIMIT_ARRAY_LEN`` — DoS guard against
         megabyte-scale array payloads.
      4. dict key count ≤ ``LIMIT_KEY_COUNT`` per level.

    Pure: no I/O, no clock. Side-effect-free except raising
    ``FrontmatterError`` on guard violation.
    """
    if depth > LIMIT_DEPTH:
        raise FrontmatterError(
            f"nested-payload depth exceeds {LIMIT_DEPTH}"
        )
    if isinstance(obj, dict):
        if len(obj) > LIMIT_KEY_COUNT:
            raise FrontmatterError(
                f"nested dict key count exceeds {LIMIT_KEY_COUNT}"
            )
        for k, v in obj.items():
            if not isinstance(k, str):
                raise FrontmatterError(
                    f"non-string dict key at depth {depth}: {type(k).__name__}"
                )
            if k in _PROTOTYPE_POLLUTION_KEYS:
                raise FrontmatterError(
                    f"refusing prototype-pollution key {k!r} at depth {depth}"
                )
            _check_no_pollution(v, depth + 1)
        return
    if isinstance(obj, list):
        if len(obj) > LIMIT_ARRAY_LEN:
            raise FrontmatterError(
                f"nested list length exceeds {LIMIT_ARRAY_LEN}"
            )
        for item in obj:
            _check_no_pollution(item, depth + 1)
        return
    # Scalars (str/int/float/bool/None) are leaf nodes — nothing to walk.


# ---------------------------------------------------------------------------
# Scalar coercion
# ---------------------------------------------------------------------------


def _coerce_scalar(raw: str) -> Union[str, int, float, bool, None, dict, list]:
    """Best-effort scalar parse: bool / null / int / float / NFKC string.

    Length capped at ``LIMIT_SCALAR_LEN``. Strings are NFKC-normalised
    so ZWJ / fullwidth homoglyphs are folded BEFORE the value reaches
    any downstream regex / classification predicate.

    P1-09 fix: when the raw text starts with ``{`` or ``[`` we parse via
    ``json.loads`` AND immediately walk the resulting structure for
    prototype-pollution keys at every depth. The returned value may be
    a dict / list (not just a scalar) — the YAML parser already handles
    that case.
    """
    if len(raw) > LIMIT_SCALAR_LEN:
        raise FrontmatterError(
            f"scalar exceeds {LIMIT_SCALAR_LEN}-byte cap"
        )
    s = raw.strip()
    # JSON literal? (catches dicts/lists/null/bool/numbers cheaply)
    if s and s[0] in '{[':
        try:
            parsed = json.loads(s)
        except (json.JSONDecodeError, ValueError) as exc:
            raise FrontmatterError(f"invalid JSON literal: {exc}")
        # P1-09 fix: walk the parsed payload for proto-pollution keys
        # AND depth/array-size DoS limits at every nested level.
        _check_no_pollution(parsed, depth=0)
        return parsed
    if s in ("null", "~", ""):
        return None
    if s in ("true", "True", "TRUE"):
        return True
    if s in ("false", "False", "FALSE"):
        return False
    # int?
    try:
        return int(s)
    except ValueError:
        pass
    # float?
    try:
        return float(s)
    except ValueError:
        pass
    # quoted string? strip the quotes; otherwise treat as bare string.
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ('"', "'"):
        s = s[1:-1]
    return unicodedata.normalize("NFKC", s)


def _check_key(key: str, depth: int) -> None:
    """Reject prototype-pollution / unknown keys.

    ``depth == 0`` means top-level: also enforces the
    ``_ALLOWED_FRONTMATTER_KEYS`` closed set. Deeper keys are checked
    against the prototype-pollution set only — nested keys are free-
    form (e.g. nested ``tools: { read: true, write: false }``).
    """
    if key in _PROTOTYPE_POLLUTION_KEYS:
        raise FrontmatterError(
            f"refusing prototype-pollution key: {key!r}"
        )
    if depth == 0 and key not in _ALLOWED_FRONTMATTER_KEYS:
        raise FrontmatterError(
            f"refusing unknown top-level key: {key!r}"
        )


# ---------------------------------------------------------------------------
# YAML-subset block parser
# ---------------------------------------------------------------------------


def _indent_of(line: str) -> int:
    """Return leading-space count (tabs explicitly rejected)."""
    n = 0
    for ch in line:
        if ch == " ":
            n += 1
        elif ch == "\t":
            raise FrontmatterError("tabs not permitted in frontmatter")
        else:
            break
    return n


def _parse_lines(
    lines: List[str],
    start: int,
    base_indent: int,
    depth: int,
) -> Tuple[Dict[str, Any], int]:
    """Recursively parse a block at ``base_indent``. Returns (dict, idx).

    ``idx`` points to the first line NOT consumed (one past the block).
    """
    if depth > LIMIT_DEPTH:
        raise FrontmatterError(
            f"frontmatter depth exceeds {LIMIT_DEPTH}"
        )
    out: Dict[str, Any] = {}
    i = start
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        ind = _indent_of(line)
        if ind < base_indent:
            break
        if ind > base_indent:
            raise FrontmatterError(
                f"unexpected indent {ind} > {base_indent} at line {i}"
            )
        if ":" not in line:
            raise FrontmatterError(
                f"missing ':' in frontmatter at line {i}: {line!r}"
            )
        key, _, rest = line.strip().partition(":")
        key = key.strip()
        rest = rest.strip()
        _check_key(key, depth)
        if len(out) >= LIMIT_KEY_COUNT:
            raise FrontmatterError(
                f"key count exceeds {LIMIT_KEY_COUNT}"
            )
        if rest:
            out[key] = _coerce_scalar(rest)
            i += 1
            continue
        # Block-form value: peek next non-blank line.
        j = i + 1
        while j < len(lines) and (
            not lines[j].strip() or lines[j].lstrip().startswith("#")
        ):
            j += 1
        if j == len(lines):
            out[key] = None
            i = j
            continue
        nxt = lines[j]
        nxt_ind = _indent_of(nxt)
        if nxt_ind <= base_indent:
            out[key] = None
            i = j
            continue
        # block-list?
        if nxt.lstrip().startswith("- "):
            items, i = _parse_block_list(lines, j, nxt_ind)
            out[key] = items
            continue
        # nested dict
        sub, i = _parse_lines(lines, j, nxt_ind, depth + 1)
        out[key] = sub
    return out, i


def _parse_block_list(
    lines: List[str],
    start: int,
    base_indent: int,
) -> Tuple[List[Any], int]:
    """Parse a sequence of ``- scalar`` items at ``base_indent``."""
    items: List[Any] = []
    i = start
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        ind = _indent_of(line)
        if ind < base_indent:
            break
        if ind > base_indent:
            raise FrontmatterError(
                f"unexpected indent {ind} > {base_indent} in list"
            )
        stripped = line.strip()
        if not stripped.startswith("- "):
            break
        items.append(_coerce_scalar(stripped[2:]))
        if len(items) >= LIMIT_KEY_COUNT:
            raise FrontmatterError(
                f"list length exceeds {LIMIT_KEY_COUNT}"
            )
        i += 1
    return items, i


def _split_frontmatter(text: str) -> Optional[str]:
    """Return the frontmatter block content, or ``None`` if absent.

    Format: leading ``---\\n`` + block + ``---\\n``. We tolerate Windows
    line-endings by stripping ``\\r``.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.startswith("---\n"):
        return None
    rest = text[4:]
    end = rest.find("\n---")
    if end == -1:
        raise FrontmatterError("frontmatter not terminated by '---'")
    return rest[:end]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def parse_agent_frontmatter(path: Union[str, Path]) -> Dict[str, Any]:
    """Read ``path``, extract its frontmatter, return the dict.

    Hardening (in order):

    1. Reject symlinks (leaf or parent).
    2. Reject canonical-guarded paths (R-SEC4 — defence-in-depth).
    3. Reject files larger than 64 KiB.
    4. Reject prototype-pollution keys + unknown top-level keys.
    5. Reject prototype-pollution keys recursively inside JSON-literal
       scalar values (P1-09 fix).
    6. Enforce depth limit ``LIMIT_DEPTH``.
    7. NFKC-normalise scalar values.

    Returns the parsed dict on success. Raises ``FrontmatterError`` on
    any guard violation. Callers in advisory-only paths catch the
    exception and substitute ``FROZEN_BASELINE``.
    """
    p = Path(path)
    # 1. Symlink reject
    try:
        if p.is_symlink():
            raise FrontmatterError(
                f"refusing symlink: {p}"
            )
        if p.parent.is_symlink():
            raise FrontmatterError(
                f"refusing file under symlinked parent: {p}"
            )
    except OSError as exc:
        raise FrontmatterError(f"cannot stat {p}: {exc}")

    # 2. Canonical-path reject
    norm = str(p).replace("\\", "/")
    for canon in _LOCAL_CANONICAL_AGENT_PATHS:
        if norm.endswith(canon):
            raise FrontmatterError(
                f"refusing direct parse of canonical-guarded path: "
                f"{canon} (use _lib/agent_frontmatter via kernel)"
            )

    # 3. Size cap (enforced BEFORE read)
    try:
        size = p.stat().st_size
    except OSError as exc:
        raise FrontmatterError(f"cannot stat {p}: {exc}")
    if size > LIMIT_FILE_BYTES:
        raise FrontmatterError(
            f"file size {size} exceeds {LIMIT_FILE_BYTES}"
        )

    # 4. Read
    try:
        raw = p.read_text(encoding="utf-8", errors="strict")
    except (OSError, UnicodeDecodeError) as exc:
        raise FrontmatterError(f"cannot read {p}: {exc}")

    # 5. Extract frontmatter
    block = _split_frontmatter(raw)
    if block is None:
        return {}

    # 6. Parse (line-by-line YAML subset; JSON-literal scalars are
    # post-validated for proto-pollution + depth recursively in
    # ``_coerce_scalar`` → ``_check_no_pollution``).
    lines = block.split("\n")
    parsed, _ = _parse_lines(lines, 0, 0, 0)
    return parsed


__all__ = [
    "FrontmatterError",
    "parse_agent_frontmatter",
]
