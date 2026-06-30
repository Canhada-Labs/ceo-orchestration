"""Routing matrix loader — PLAN-081 Phase 2 deliverable.

Loads ``.claude/dispatcher/routing-matrix.yaml`` (the Pair-Rail capability
matrix) and exposes a typed read-only API consumed by:

- ``.claude/scripts/inject-agent-context.sh --pair-mode`` to resolve
  coder/reviewer providers per archetype.
- ``.claude/hooks/check_pair_rail.py`` (Phase 3 asymmetric-VETO matrix
  arms) to look up the per-archetype reviewer + sandbox mode + fallback
  policy.
- ``.claude/dispatcher/disable_predicate_eval.py`` to evaluate
  ``disable_predicates`` lists and emit ``dispatcher_route`` audit
  events with the chosen rail (pair-rail vs. fallback).

## Threat-model T-4 mitigations (archetype-spoofing)

The matrix YAML is canonical-guarded under ``.claude/dispatcher/*.yaml``
(``check_canonical_edit.py`` _CANONICAL_GUARDS) plus the kernel-hard-deny
gate on ``audit_emit.py``. The loader adds **defense-in-depth**:

1. **Schema validation** at load time — required fields enforced; unknown
   archetypes/predicate types cause ``RoutingMatrixError`` (caller-side
   fail-closed semantics under ``CEO_PAIR_RAIL_FAILCLOSED=1`` env, else
   advisory).
2. **SHA-pin assertion** — when ``CEO_PAIR_RAIL_MATRIX_SHA256`` env var
   is set, the loader verifies that the SHA-256 digest of the loaded YAML
   matches the pinned value and emits ``dispatcher_route`` with
   ``digest_match=False`` on mismatch (pre-flight runs in
   ``pair-rail-gate.sh`` Phase 6 before tag).
3. **Singleton matrix file** — only the canonical
   ``.claude/dispatcher/routing-matrix.yaml`` is honored; alternate paths
   are rejected.

## Public API (pure functions / dataclass-like NamedTuples)

    load_routing_matrix(path: Optional[Path] = None) -> RoutingMatrix
    get_archetype_route(matrix, archetype) -> ArchetypeRoute
    list_archetypes(matrix) -> list[str]
    is_pair_rail_enabled(matrix, archetype, audit_log_path=None) -> bool
    get_disable_predicates(matrix, archetype) -> list[Predicate]
    compute_matrix_sha256(path: Path) -> str

All functions are side-effect-free except ``is_pair_rail_enabled`` which
delegates to ``disable_predicate_eval`` (which performs a bounded
tail-scan of audit-log.jsonl).

## Stdlib-only

YAML parsing is performed via a small purpose-built parser (no PyYAML
dependency) tailored to the matrix shape. The parser supports nested
mappings, lists, scalars (str/int/float/bool/null), inline comments
(``#`` to end-of-line), and block-style indentation only. Anchors,
references, and flow-style are rejected with ``RoutingMatrixError``.

Python ≥3.9 compatibility — uses ``typing.Optional/Union/List/Dict``
(no PEP 604 ``X | Y`` syntax).
"""

from __future__ import annotations

import hashlib
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Tuple, Union

# ---------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------

#: SemVer for the loader implementation (matches matrix schema_version).
LOADER_VERSION: str = "1.0.0-rc.1"

#: Default canonical path of the routing matrix relative to repo root.
_DEFAULT_MATRIX_PATH: str = ".claude/dispatcher/routing-matrix.yaml"

#: Known archetype IDs — must match team.md ROUTING TABLE entries.
_KNOWN_ARCHETYPES: Tuple[str, ...] = (
    "code-reviewer",
    "security-engineer",
    "qa-architect",
    "performance-engineer",
    "refactoring",
    "docs-writer",
    "test-author",
    "threat-detection-engineer",
)

#: VETO-floor archetypes per ADR-052 (PLAN-074 Wave 1c expansion). For
#: these archetypes the matrix MUST declare ``coder_model: opus``,
#: ``coder: claude``, and ``coder != reviewer`` (cross-LLM diversity
#: invariant). Any matrix entry violating these constraints raises
#: ``RoutingMatrixError`` at load time, closing T-4 archetype-spoofing
#: variants that swap coder/reviewer providers or downgrade model floor.
#: Codex iter 1 P0-2 fix.
_VETO_FLOOR_ARCHETYPES: Tuple[str, ...] = (
    "code-reviewer",
    "security-engineer",
    "threat-detection-engineer",
)

#: Known predicate types — each maps to an arm in
#: ``disable_predicate_eval.evaluate_predicate``.
_KNOWN_PREDICATE_TYPES: Tuple[str, ...] = (
    "duration_threshold",
    "numeric_threshold",
    "boolean",
)

#: Known operators for threshold predicates.
_KNOWN_OPERATORS: Tuple[str, ...] = (">", ">=", "<", "<=", "==")

#: Known providers (mirror of ``_lib.contract.KNOWN_ADAPTERS``).
_KNOWN_PROVIDERS: Tuple[str, ...] = ("claude", "codex")

#: Known sandbox modes (subset valid for reviewer per ADR-106).
_KNOWN_SANDBOX_MODES: Tuple[str, ...] = (
    "read-only",
    "workspace-write",
    "danger-full-access",
)


# ---------------------------------------------------------------------
# Public datatypes
# ---------------------------------------------------------------------


class Predicate(NamedTuple):
    """A typed disable-predicate entry. Immutable."""

    id: str
    type: str  # one of _KNOWN_PREDICATE_TYPES
    metric: str
    operator: str  # one of _KNOWN_OPERATORS
    value: Union[float, int, bool]
    window_minutes: Optional[int]
    window_days: Optional[int]


class ArchetypeRoute(NamedTuple):
    """A frozen routing decision for a single archetype."""

    archetype: str
    coder: str  # one of _KNOWN_PROVIDERS
    coder_model: Optional[str]
    reviewer: str  # one of _KNOWN_PROVIDERS
    reviewer_sandbox: str  # one of _KNOWN_SANDBOX_MODES
    fallback_provider: str  # one of _KNOWN_PROVIDERS
    health_prereq: Tuple[str, ...]
    disable_predicates: Tuple[Predicate, ...]


class RoutingMatrix(NamedTuple):
    """Top-level matrix container."""

    schema_version: str
    plan: str
    phase: int
    archetypes: Dict[str, ArchetypeRoute]
    predicate_types: Dict[str, Dict[str, Any]]
    metrics: Dict[str, Dict[str, Any]]
    defaults: Dict[str, Any]
    sha256: str  # digest of the source YAML bytes


class RoutingMatrixError(ValueError):
    """Raised on schema violations or unparseable YAML."""


# ---------------------------------------------------------------------
# YAML parser — purpose-built minimal subset (block style only)
# ---------------------------------------------------------------------


def _strip_inline_comment(line: str) -> str:
    """Strip ``# ...`` to end-of-line, respecting quoted strings.

    Conservative: only strips ``#`` that's preceded by whitespace OR is
    at start-of-line. This preserves ``#`` inside strings like
    ``"foo#bar"`` (we don't double-quote in the matrix; this is defensive).
    """
    in_single = False
    in_double = False
    out = []
    prev = ""
    for ch in line:
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double
        elif ch == "#" and not in_single and not in_double:
            if not prev or prev.isspace():
                break
        out.append(ch)
        prev = ch
    return "".join(out).rstrip()


def _coerce_scalar(token: str) -> Union[str, int, float, bool, None]:
    """Coerce a YAML scalar token into a Python value."""
    s = token.strip()
    if not s:
        return ""
    # Quoted strings — strip outer quotes, no escape processing (the
    # matrix uses simple ASCII identifiers).
    if (s.startswith('"') and s.endswith('"')) or (
        s.startswith("'") and s.endswith("'")
    ):
        return s[1:-1]
    if s in ("true", "True", "TRUE"):
        return True
    if s in ("false", "False", "FALSE"):
        return False
    if s in ("null", "Null", "NULL", "~"):
        return None
    # Numeric coercion (int first, fall back to float).
    if re.fullmatch(r"-?\d+", s):
        try:
            return int(s)
        except ValueError:
            pass
    if re.fullmatch(r"-?\d+\.\d+", s):
        try:
            return float(s)
        except ValueError:
            pass
    return s


def _indent_of(line: str) -> int:
    """Return the leading-space count (tabs rejected)."""
    if "\t" in line[: len(line) - len(line.lstrip())]:
        raise RoutingMatrixError(
            "tabs in indent are forbidden — use spaces only"
        )
    return len(line) - len(line.lstrip())


def _parse_yaml_block(lines: List[str], start: int, indent: int) -> Tuple[Any, int]:
    """Recursive-descent block-style YAML parser.

    Returns (value, next_line_index). ``value`` is one of:
      - dict[str, Any] (mapping)
      - list[Any] (sequence)
      - scalar (str/int/float/bool/None)
    """
    if start >= len(lines):
        return {}, start
    first = lines[start]
    first_stripped = first.strip()
    # Empty line / comment-only — skip
    if not first_stripped:
        return _parse_yaml_block(lines, start + 1, indent)
    first_indent = _indent_of(first)
    if first_indent < indent:
        return {}, start

    # List entry?
    if first_stripped.startswith("- "):
        return _parse_list(lines, start, indent)

    # Mapping?
    if ":" in first_stripped:
        return _parse_mapping(lines, start, indent)

    # Bare scalar?
    return _coerce_scalar(first_stripped), start + 1


def _parse_mapping(lines: List[str], start: int, indent: int) -> Tuple[Dict[str, Any], int]:
    out: Dict[str, Any] = {}
    i = start
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        cur_indent = _indent_of(line)
        if cur_indent < indent:
            break
        if cur_indent > indent:
            # Stale indent — error
            raise RoutingMatrixError(
                f"line {i + 1}: unexpected indentation (got {cur_indent}, expected {indent})"
            )
        # Reject flow-style and anchors
        if stripped.startswith("{") or stripped.startswith("["):
            raise RoutingMatrixError(
                f"line {i + 1}: flow-style mapping/sequence not supported"
            )
        if "&" in stripped or "*" in stripped.split(":", 1)[0]:
            # Conservative: anchors `&foo` or aliases `*foo` rejected
            if re.search(r"(^|\s)[&*]\w", stripped):
                raise RoutingMatrixError(
                    f"line {i + 1}: anchors/aliases not supported"
                )
        if ":" not in stripped:
            raise RoutingMatrixError(
                f"line {i + 1}: expected key:value mapping entry"
            )
        key, _, rest = stripped.partition(":")
        key = key.strip()
        rest = rest.strip()
        if not key:
            raise RoutingMatrixError(f"line {i + 1}: empty key")
        if rest == "":
            # Block continuation — find children at indent > cur_indent
            child_indent = _find_child_indent(lines, i + 1, cur_indent)
            if child_indent is None:
                # No children — value is None
                out[key] = None
                i += 1
                continue
            value, j = _parse_yaml_block(lines, i + 1, child_indent)
            out[key] = value
            i = j
            continue
        if rest.startswith("|") or rest.startswith(">"):
            # Block-scalar (literal/folded). Read indented continuation.
            block_text, j = _parse_block_scalar(lines, i + 1, cur_indent, rest[0])
            out[key] = block_text
            i = j
            continue
        # Inline scalar
        out[key] = _coerce_scalar(rest)
        i += 1
    return out, i


def _parse_list(lines: List[str], start: int, indent: int) -> Tuple[List[Any], int]:
    out: List[Any] = []
    i = start
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        cur_indent = _indent_of(line)
        if cur_indent < indent:
            break
        if not stripped.startswith("- "):
            if cur_indent == indent:
                break
            raise RoutingMatrixError(
                f"line {i + 1}: expected '- ' list entry"
            )
        item_text = stripped[2:].strip()
        if item_text == "":
            # Empty item marker — block continuation
            child_indent = _find_child_indent(lines, i + 1, cur_indent + 2)
            if child_indent is None:
                out.append(None)
                i += 1
                continue
            value, j = _parse_yaml_block(lines, i + 1, child_indent)
            out.append(value)
            i = j
            continue
        if ":" in item_text and not _looks_like_scalar_with_colon(item_text):
            # Inline mapping entry — synthesize a single-line buffer
            # and parse it as a child mapping with the correct indent.
            buf: List[str] = []
            buf.append(" " * (cur_indent + 2) + item_text)
            j = i + 1
            while j < len(lines):
                next_line = lines[j]
                next_stripped = next_line.strip()
                if not next_stripped:
                    j += 1
                    continue
                nxt_ind = _indent_of(next_line)
                if nxt_ind <= cur_indent:
                    break
                if nxt_ind == cur_indent + 2 and next_stripped.startswith("- "):
                    break
                # Continuation — fold into the synthesized mapping body
                buf.append(next_line)
                j += 1
            value, _ = _parse_mapping(buf, 0, cur_indent + 2)
            out.append(value)
            i = j
            continue
        # Plain scalar list item
        out.append(_coerce_scalar(item_text))
        i += 1
    return out, i


def _looks_like_scalar_with_colon(item_text: str) -> bool:
    """Heuristic: if a colon is inside quotes, it's a scalar."""
    if item_text.startswith('"') and item_text.endswith('"'):
        return True
    if item_text.startswith("'") and item_text.endswith("'"):
        return True
    return False


def _parse_block_scalar(
    lines: List[str], start: int, parent_indent: int, marker: str
) -> Tuple[str, int]:
    """Read a ``|`` (literal) or ``>`` (folded) block scalar."""
    out_lines: List[str] = []
    i = start
    block_indent: Optional[int] = None
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            out_lines.append("")
            i += 1
            continue
        cur_indent = _indent_of(line)
        if cur_indent <= parent_indent:
            break
        if block_indent is None:
            block_indent = cur_indent
        out_lines.append(line[block_indent:])
        i += 1
    if marker == "|":
        text = "\n".join(out_lines).rstrip("\n")
    else:  # ">"
        text = " ".join(s for s in out_lines if s).rstrip()
    return text, i


def _find_child_indent(lines: List[str], start: int, parent_indent: int) -> Optional[int]:
    for j in range(start, len(lines)):
        s = lines[j].strip()
        if not s:
            continue
        ind = _indent_of(lines[j])
        if ind > parent_indent:
            return ind
        return None
    return None


def _parse_yaml(text: str) -> Dict[str, Any]:
    """Parse the matrix YAML body into a nested dict."""
    raw_lines = text.splitlines()
    # Strip inline comments + blank lines preserved for context counting
    cleaned: List[str] = []
    for raw in raw_lines:
        stripped = _strip_inline_comment(raw)
        if stripped.strip().startswith("#"):
            cleaned.append("")
        else:
            cleaned.append(stripped)
    value, _ = _parse_yaml_block(cleaned, 0, 0)
    if not isinstance(value, dict):
        raise RoutingMatrixError("top-level YAML must be a mapping")
    return value


# ---------------------------------------------------------------------
# Schema validation + dataclass coercion
# ---------------------------------------------------------------------


def _require(obj: Dict[str, Any], key: str, ctx: str) -> Any:
    if key not in obj:
        raise RoutingMatrixError(f"{ctx}: missing required key '{key}'")
    return obj[key]


def _coerce_predicate(raw: Dict[str, Any], ctx: str) -> Predicate:
    pid = _require(raw, "id", ctx)
    ptype = _require(raw, "type", ctx)
    if ptype not in _KNOWN_PREDICATE_TYPES:
        raise RoutingMatrixError(
            f"{ctx}: unknown predicate type '{ptype}' "
            f"(must be one of {_KNOWN_PREDICATE_TYPES})"
        )
    metric = _require(raw, "metric", ctx)
    operator = _require(raw, "operator", ctx)
    if operator not in _KNOWN_OPERATORS:
        raise RoutingMatrixError(
            f"{ctx}: unknown operator '{operator}' "
            f"(must be one of {_KNOWN_OPERATORS})"
        )
    value = _require(raw, "value", ctx)
    if not isinstance(value, (int, float, bool)):
        raise RoutingMatrixError(
            f"{ctx}: predicate value must be numeric or boolean, got {type(value).__name__}"
        )
    window_minutes = raw.get("window_minutes")
    if window_minutes is not None and not isinstance(window_minutes, int):
        raise RoutingMatrixError(
            f"{ctx}: window_minutes must be int, got {type(window_minutes).__name__}"
        )
    window_days = raw.get("window_days")
    if window_days is not None and not isinstance(window_days, int):
        raise RoutingMatrixError(
            f"{ctx}: window_days must be int, got {type(window_days).__name__}"
        )
    return Predicate(
        id=str(pid),
        type=str(ptype),
        metric=str(metric),
        operator=str(operator),
        value=value,
        window_minutes=window_minutes,
        window_days=window_days,
    )


def _coerce_route(name: str, raw: Dict[str, Any]) -> ArchetypeRoute:
    ctx = f"archetype '{name}'"
    coder = _require(raw, "coder", ctx)
    if coder not in _KNOWN_PROVIDERS:
        raise RoutingMatrixError(
            f"{ctx}: unknown coder provider '{coder}' "
            f"(must be one of {_KNOWN_PROVIDERS})"
        )
    reviewer = _require(raw, "reviewer", ctx)
    if reviewer not in _KNOWN_PROVIDERS:
        raise RoutingMatrixError(
            f"{ctx}: unknown reviewer provider '{reviewer}' "
            f"(must be one of {_KNOWN_PROVIDERS})"
        )
    # Codex iter 1 P0-2: cross-LLM diversity invariant. A pair-rail entry
    # with coder == reviewer collapses Pair-Rail to single-LLM review
    # (still appears "enabled" but second rail is the same provider).
    # T-4 archetype-spoofing variant #1 closure.
    if coder == reviewer:
        raise RoutingMatrixError(
            f"{ctx}: coder == reviewer ('{coder}') violates Pair-Rail "
            f"cross-LLM diversity invariant. Set distinct providers."
        )
    fallback = raw.get("fallback_provider", "claude")
    if fallback not in _KNOWN_PROVIDERS:
        raise RoutingMatrixError(
            f"{ctx}: unknown fallback_provider '{fallback}'"
        )
    sandbox = raw.get("reviewer_sandbox", "read-only")
    if sandbox not in _KNOWN_SANDBOX_MODES:
        raise RoutingMatrixError(
            f"{ctx}: unknown reviewer_sandbox '{sandbox}'"
        )
    # Codex iter 2 P0-1: Phase 2 enforces ``reviewer_sandbox=read-only``
    # for **every** archetype (not just VETO-floor). Codex acts as
    # reviewer-only across the full matrix; ``workspace-write`` /
    # ``danger-full-access`` for the reviewer presupposes Phase 5
    # codando + Phase 4 promotion gate green, which Phase 2 cannot
    # confirm. T-4 “downgrade reviewer sandbox” mutation closure for
    # the non-VETO archetypes (5/8 missed in iter 1).
    if sandbox != "read-only":
        raise RoutingMatrixError(
            f"{ctx}: Phase 2 reviewer_sandbox MUST be 'read-only' "
            f"(got '{sandbox}'). Workspace-write / danger-full-access "
            f"for the reviewer requires Phase 5 codando + Phase 4 "
            f"promotion gate 15/15; this matrix entry pre-empts that. "
            f"T-4 archetype-spoofing variant blocked."
        )
    coder_model = raw.get("coder_model")
    if coder_model is not None and not isinstance(coder_model, str):
        raise RoutingMatrixError(
            f"{ctx}: coder_model must be string or null"
        )

    # Codex iter 1 P0-2: VETO-floor invariants per ADR-052. For
    # `code-reviewer`, `security-engineer`, `threat-detection-engineer`
    # the matrix MUST declare:
    #   - coder == "claude" (Pair-Rail v1 ships Claude as VETO floor;
    #     Codex coder requires Phase 4 promotion gate 15/15 strict)
    #   - coder_model == "opus" (no haiku/sonnet downgrade)
    #   - reviewer_sandbox == "read-only" (Codex MUST NOT have write
    #     capability under Pair-Rail; Phase 5 deny-list further enforces)
    # T-4 archetype-spoofing variants #2 + #5 closure.
    if name in _VETO_FLOOR_ARCHETYPES:
        if coder != "claude":
            raise RoutingMatrixError(
                f"{ctx}: VETO-floor archetype must have coder='claude' "
                f"per ADR-052 (got '{coder}'). Codex-as-coder for VETO "
                f"floor requires Phase 4 promotion gate 15/15 strict; "
                f"this matrix entry pre-empts that gate."
            )
        if coder_model != "opus":
            raise RoutingMatrixError(
                f"{ctx}: VETO-floor archetype must have coder_model='opus' "
                f"per ADR-052 (got '{coder_model}'). Sonnet/Haiku downgrade "
                f"is forbidden for VETO floor."
            )
        if sandbox != "read-only":
            raise RoutingMatrixError(
                f"{ctx}: VETO-floor archetype must have "
                f"reviewer_sandbox='read-only' (got '{sandbox}'). "
                f"workspace-write/danger-full-access for the reviewer "
                f"violates the Pair-Rail asymmetric-coverage invariant."
            )

    health_prereq_raw = raw.get("health_prereq", []) or []
    if not isinstance(health_prereq_raw, list):
        raise RoutingMatrixError(
            f"{ctx}: health_prereq must be a list"
        )
    health_prereq: Tuple[str, ...] = tuple(str(p) for p in health_prereq_raw)
    predicates_raw = raw.get("disable_predicates", []) or []
    if not isinstance(predicates_raw, list):
        raise RoutingMatrixError(
            f"{ctx}: disable_predicates must be a list"
        )
    # Codex iter 1 P1-2: non-dict entries in disable_predicates are
    # rejected at load time (previously silently dropped, allowing a
    # malformed list to remove protections while still loading).
    predicates_coerced: List[Predicate] = []
    for idx, p in enumerate(predicates_raw):
        if not isinstance(p, dict):
            raise RoutingMatrixError(
                f"{ctx} predicate #{idx}: entry must be a mapping, "
                f"got {type(p).__name__}"
            )
        predicates_coerced.append(
            _coerce_predicate(p, f"{ctx} predicate #{idx}")
        )
    predicates: Tuple[Predicate, ...] = tuple(predicates_coerced)
    return ArchetypeRoute(
        archetype=name,
        coder=coder,
        coder_model=coder_model,
        reviewer=reviewer,
        reviewer_sandbox=sandbox,
        fallback_provider=fallback,
        health_prereq=health_prereq,
        disable_predicates=predicates,
    )


# ---------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------


def compute_matrix_sha256(path: Path) -> str:
    """Return SHA-256 digest of the matrix YAML bytes (canonical_json-equivalent)."""
    if not path.exists():
        raise RoutingMatrixError(f"matrix file not found: {path}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _resolve_matrix_path(path: Optional[Path]) -> Path:
    if path is not None:
        return path
    # Walk up from this module to find the repo root.
    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / _DEFAULT_MATRIX_PATH
        if candidate.exists():
            return candidate
    # Fallback: assume CWD is repo root.
    return Path.cwd() / _DEFAULT_MATRIX_PATH


def load_routing_matrix(path: Optional[Path] = None) -> RoutingMatrix:
    """Load + validate the routing matrix YAML.

    Args:
        path: explicit matrix path (test override). Default resolves
            ``.claude/dispatcher/routing-matrix.yaml`` from repo root.

    Returns:
        ``RoutingMatrix`` immutable container.

    Raises:
        RoutingMatrixError: on missing file, parse error, or schema
            violation.
    """
    matrix_path = _resolve_matrix_path(path)
    if not matrix_path.exists():
        raise RoutingMatrixError(f"matrix file not found: {matrix_path}")
    text = matrix_path.read_text(encoding="utf-8")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()

    # SHA-pin assertion (R1 T-4 mitigation #2).
    expected = os.environ.get("CEO_PAIR_RAIL_MATRIX_SHA256", "").strip()
    if expected and expected != digest:
        # Caller is responsible for fail-closed semantics; we expose the
        # mismatch via the returned digest field. Audit emit is performed
        # by the caller (inject-agent-context.sh) so the loader stays
        # side-effect-free.
        if os.environ.get("CEO_PAIR_RAIL_FAILCLOSED") == "1":
            raise RoutingMatrixError(
                f"matrix SHA-256 mismatch: expected {expected}, got {digest}"
            )

    try:
        data = _parse_yaml(text)
    except RoutingMatrixError:
        raise
    except Exception as e:
        raise RoutingMatrixError(f"YAML parse error: {type(e).__name__}: {e}")

    schema_version = data.get("schema_version")
    if not isinstance(schema_version, str) or not schema_version:
        raise RoutingMatrixError("schema_version must be a non-empty string")
    plan = data.get("plan", "")
    phase_raw = data.get("phase", 0)
    try:
        phase = int(phase_raw)
    except (TypeError, ValueError):
        raise RoutingMatrixError(f"phase must be an integer, got {phase_raw!r}")
    archetypes_raw = data.get("archetypes", {})
    if not isinstance(archetypes_raw, dict) or not archetypes_raw:
        raise RoutingMatrixError("archetypes mapping required and non-empty")

    archetypes: Dict[str, ArchetypeRoute] = {}
    for name, raw in archetypes_raw.items():
        if name not in _KNOWN_ARCHETYPES:
            raise RoutingMatrixError(
                f"unknown archetype '{name}' "
                f"(must be one of {_KNOWN_ARCHETYPES})"
            )
        if not isinstance(raw, dict):
            raise RoutingMatrixError(
                f"archetype '{name}' must be a mapping"
            )
        archetypes[name] = _coerce_route(name, raw)

    # All 8 known archetypes required (closes T-4 archetype-omission).
    missing = set(_KNOWN_ARCHETYPES) - set(archetypes.keys())
    if missing:
        raise RoutingMatrixError(
            f"matrix is missing archetypes: {sorted(missing)}"
        )

    predicate_types = data.get("predicate_types", {}) or {}
    if not isinstance(predicate_types, dict):
        raise RoutingMatrixError("predicate_types must be a mapping")
    metrics = data.get("metrics", {}) or {}
    if not isinstance(metrics, dict):
        raise RoutingMatrixError("metrics must be a mapping")
    defaults = data.get("defaults", {}) or {}
    if not isinstance(defaults, dict):
        raise RoutingMatrixError("defaults must be a mapping")

    # Codex iter 1 P1-1: cross-validate that every predicate's `metric`
    # field references a known metric in the matrix-level `metrics`
    # registry. Previously typos in metric names were silently inert
    # (evaluator returns False for unknown metrics, leaving the
    # predicate disabled while pretending to be active).
    known_metric_names = set(metrics.keys())
    for arch_name, route in archetypes.items():
        for pred in route.disable_predicates:
            if pred.metric not in known_metric_names:
                raise RoutingMatrixError(
                    f"archetype '{arch_name}' predicate '{pred.id}': "
                    f"metric '{pred.metric}' is not declared in the "
                    f"top-level `metrics` registry. Known metrics: "
                    f"{sorted(known_metric_names)}. Typo or registry drift?"
                )

    return RoutingMatrix(
        schema_version=schema_version,
        plan=str(plan),
        phase=phase,
        archetypes=archetypes,
        predicate_types=predicate_types,
        metrics=metrics,
        defaults=defaults,
        sha256=digest,
    )


def get_archetype_route(matrix: RoutingMatrix, archetype: str) -> ArchetypeRoute:
    """Return the routing entry for an archetype.

    Raises ``RoutingMatrixError`` on unknown archetype.
    """
    if archetype not in matrix.archetypes:
        raise RoutingMatrixError(f"unknown archetype '{archetype}'")
    return matrix.archetypes[archetype]


def list_archetypes(matrix: RoutingMatrix) -> List[str]:
    """Return all archetypes in stable sorted order."""
    return sorted(matrix.archetypes.keys())


def get_disable_predicates(matrix: RoutingMatrix, archetype: str) -> List[Predicate]:
    """Return the disable-predicate list for an archetype."""
    route = get_archetype_route(matrix, archetype)
    return list(route.disable_predicates)


def is_pair_rail_enabled(
    matrix: RoutingMatrix,
    archetype: str,
    audit_log_path: Optional[Path] = None,
) -> bool:
    """Return True if the pair-rail is enabled for the archetype.

    Evaluates each ``disable_predicate`` via ``disable_predicate_eval``.
    If ANY predicate fires (returns True), the pair-rail is disabled and
    the archetype falls back to single-LLM coder.

    Args:
        matrix: loaded routing matrix.
        archetype: archetype name.
        audit_log_path: optional explicit audit-log path (test override).

    Returns:
        True if pair-rail enabled (no predicate fired), False otherwise.

    Note: lazily imports ``disable_predicate_eval`` to avoid circular
    import at module load time. Errors during evaluation default to
    "predicate did not fire" — fail-OPEN per pair-rail invariant.
    """
    route = get_archetype_route(matrix, archetype)
    if not route.disable_predicates:
        return True
    try:
        # Defer import to avoid circular dep at load time.
        try:
            from .disable_predicate_eval import evaluate_predicate
        except ImportError:
            # When the dispatcher dir isn't yet on PYTHONPATH (test
            # harness), fall back to the absolute import.
            sys_path_inserted = False
            here = Path(__file__).resolve().parent
            if str(here) not in sys.path:
                sys.path.insert(0, str(here))
                sys_path_inserted = True
            try:
                from disable_predicate_eval import evaluate_predicate  # type: ignore
            finally:
                if sys_path_inserted:
                    try:
                        sys.path.remove(str(here))
                    except ValueError:
                        pass
        for pred in route.disable_predicates:
            try:
                fired = evaluate_predicate(pred, audit_log_path=audit_log_path)
            except Exception:
                # Evaluator error → predicate did not fire (fail-OPEN).
                fired = False
            if fired:
                return False
        return True
    except Exception:
        return True


# ---------------------------------------------------------------------
# CLI smoke test (manual)
# ---------------------------------------------------------------------


def _main() -> int:
    """Manual smoke test: print loaded matrix as a flat report."""
    try:
        m = load_routing_matrix()
    except RoutingMatrixError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 1
    print(f"schema_version={m.schema_version}")
    print(f"plan={m.plan} phase={m.phase}")
    print(f"sha256={m.sha256}")
    print(f"archetypes ({len(m.archetypes)}):")
    for name in list_archetypes(m):
        r = m.archetypes[name]
        print(
            f"  {name}: coder={r.coder} (model={r.coder_model}) "
            f"reviewer={r.reviewer} sandbox={r.reviewer_sandbox} "
            f"fallback={r.fallback_provider} predicates={len(r.disable_predicates)}"
        )
    return 0


if __name__ == "__main__":
    sys.exit(_main())
