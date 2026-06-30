from __future__ import annotations

import hashlib
import importlib.util
import sys
from pathlib import Path
from typing import Dict, List

import pytest

# ---------------------------------------------------------------------------
# Import routing-matrix-loader via importlib (hyphen in filename)
# ---------------------------------------------------------------------------
_DISPATCHER_DIR = Path(__file__).resolve().parent.parent
_LOADER_PATH = _DISPATCHER_DIR / "routing-matrix-loader.py"

_spec = importlib.util.spec_from_file_location("routing_matrix_loader", _LOADER_PATH)
_mod = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
_spec.loader.exec_module(_mod)  # type: ignore[union-attr]

load_routing_matrix = _mod.load_routing_matrix
get_archetype_route = _mod.get_archetype_route
list_archetypes = _mod.list_archetypes
is_pair_rail_enabled = _mod.is_pair_rail_enabled
get_disable_predicates = _mod.get_disable_predicates
compute_matrix_sha256 = _mod.compute_matrix_sha256
RoutingMatrixError = _mod.RoutingMatrixError
Predicate = _mod.Predicate
ArchetypeRoute = _mod.ArchetypeRoute
RoutingMatrix = _mod.RoutingMatrix
_KNOWN_ARCHETYPES: tuple = _mod._KNOWN_ARCHETYPES

# Real matrix YAML shipped in Phase 2 staging
_REAL_MATRIX_PATH = _DISPATCHER_DIR / "routing-matrix.yaml"

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ALL_ARCHETYPES = (
    "code-reviewer",
    "security-engineer",
    "qa-architect",
    "performance-engineer",
    "refactoring",
    "docs-writer",
    "test-author",
    "threat-detection-engineer",
)

_VETO_FLOOR_ARCHETYPES = (
    "code-reviewer",
    "security-engineer",
    "threat-detection-engineer",
)

_NON_VETO_ARCHETYPES = (
    "qa-architect",
    "performance-engineer",
    "refactoring",
    "docs-writer",
    "test-author",
)

# ---------------------------------------------------------------------------
# Minimal synthetic matrix builder (for negative-path tests)
# ---------------------------------------------------------------------------

# Codex iter 1 P0-2: VETO-floor archetypes must use coder_model=opus
# (not sonnet). The template now branches per-archetype to satisfy the
# loader invariant.
_VETO_FLOOR = ("code-reviewer", "security-engineer", "threat-detection-engineer")

# Archetype block template: 2-space indent for name, 4-space for fields.
# {name} is the archetype identifier placeholder; {model} is the floor.
_ARCH_BLOCK = (
    "  {name}:\n"
    "    coder: claude\n"
    "    coder_model: {model}\n"
    "    reviewer: codex\n"
    "    reviewer_sandbox: read-only\n"
    "    fallback_provider: claude\n"
    "    health_prereq:\n"
    "      - u1_pass\n"
    "    disable_predicates:\n"
    "      - id: codex_outage_5min\n"
    "        type: duration_threshold\n"
    "        metric: codex_outage_minutes\n"
    '        operator: ">"\n'
    "        value: 5\n"
    "        window_minutes: 60\n"
)


def _build_minimal_yaml(
    archetypes: tuple = _ALL_ARCHETYPES,
    override_blocks: Dict[str, str] = None,
) -> str:
    """Return a minimal valid routing-matrix YAML string.

    ``archetypes`` controls which archetype names are included.
    ``override_blocks`` maps archetype name to a replacement YAML block
    (already correctly indented at 2-space for the name).
    """
    ob = override_blocks or {}
    lines: List[str] = [
        'schema_version: "1.0.0-rc.1"',
        "plan: PLAN-081",
        "phase: 2",
        "",
        "archetypes:",
    ]
    for name in archetypes:
        if name in ob:
            lines.append(ob[name])
        else:
            # VETO-floor archetypes require opus per Codex iter 1 P0-2.
            model = "opus" if name in _VETO_FLOOR else "sonnet"
            lines.append(_ARCH_BLOCK.format(name=name, model=model))
    lines += [
        "",
        "predicate_types:",
        "  duration_threshold:",
        "    description: test",
        "    required_keys: [metric, operator, value, window_minutes]",
        "    operators: [>, >=, <, <=, ==]",
        "",
        "metrics:",
        "  codex_outage_minutes:",
        "    description: test",
        "    source_action: pair_rail_codex_unavailable",
        "    aggregation: window_sum_minutes",
        "",
        "defaults:",
        "  reviewer_sandbox: read-only",
        "  fallback_provider: claude",
    ]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Happy-path tests
# ---------------------------------------------------------------------------


def test_load_real_matrix_returns_eight_archetypes():
    """Loading the real routing-matrix.yaml must yield exactly 8 archetypes."""
    matrix = load_routing_matrix(_REAL_MATRIX_PATH)
    assert len(matrix.archetypes) == 8


def test_load_real_matrix_schema_version_is_string():
    """The real matrix schema_version must be a non-empty string."""
    matrix = load_routing_matrix(_REAL_MATRIX_PATH)
    assert isinstance(matrix.schema_version, str)
    assert matrix.schema_version


def test_compute_matrix_sha256_is_deterministic():
    """compute_matrix_sha256 must return the same hex digest on two calls."""
    digest_a = compute_matrix_sha256(_REAL_MATRIX_PATH)
    digest_b = compute_matrix_sha256(_REAL_MATRIX_PATH)
    assert digest_a == digest_b
    assert len(digest_a) == 64


def test_loaded_matrix_sha256_matches_compute_matrix_sha256():
    """matrix.sha256 must equal compute_matrix_sha256 for the same file."""
    matrix = load_routing_matrix(_REAL_MATRIX_PATH)
    expected = compute_matrix_sha256(_REAL_MATRIX_PATH)
    assert matrix.sha256 == expected


def test_list_archetypes_returns_sorted_names():
    """list_archetypes must return archetype names in stable sorted order."""
    matrix = load_routing_matrix(_REAL_MATRIX_PATH)
    names = list_archetypes(matrix)
    assert names == sorted(names)
    assert len(names) == 8


def test_get_archetype_route_unknown_name_raises():
    """get_archetype_route with an unrecognized archetype must raise RoutingMatrixError."""
    matrix = load_routing_matrix(_REAL_MATRIX_PATH)
    with pytest.raises(RoutingMatrixError, match="unknown archetype"):
        get_archetype_route(matrix, "does-not-exist")


# ---------------------------------------------------------------------------
# VETO-floor model assertions (ADR-052)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", _VETO_FLOOR_ARCHETYPES)
def test_veto_floor_archetype_has_coder_model_opus(name: str):
    """ADR-052 VETO-floor archetypes must declare coder_model=opus."""
    matrix = load_routing_matrix(_REAL_MATRIX_PATH)
    route = get_archetype_route(matrix, name)
    assert route.coder_model == "opus", (
        f"{name} should be coder_model=opus per ADR-052 VETO floor"
    )


@pytest.mark.parametrize("name", _NON_VETO_ARCHETYPES)
def test_non_veto_archetype_has_coder_model_sonnet(name: str):
    """Non-VETO archetypes must declare coder_model=sonnet."""
    matrix = load_routing_matrix(_REAL_MATRIX_PATH)
    route = get_archetype_route(matrix, name)
    assert route.coder_model == "sonnet", (
        f"{name} should be coder_model=sonnet"
    )


# ---------------------------------------------------------------------------
# Invariant assertions across all archetypes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", _ALL_ARCHETYPES)
def test_all_archetypes_reviewer_is_codex(name: str):
    """Phase 2 spec: all archetypes must have reviewer=codex."""
    matrix = load_routing_matrix(_REAL_MATRIX_PATH)
    route = get_archetype_route(matrix, name)
    assert route.reviewer == "codex"


@pytest.mark.parametrize("name", _ALL_ARCHETYPES)
def test_all_archetypes_sandbox_is_read_only(name: str):
    """ADR-106: all Phase 2 archetypes must use reviewer_sandbox=read-only."""
    matrix = load_routing_matrix(_REAL_MATRIX_PATH)
    route = get_archetype_route(matrix, name)
    assert route.reviewer_sandbox == "read-only"


@pytest.mark.parametrize("name", _ALL_ARCHETYPES)
def test_all_archetypes_fallback_is_claude(name: str):
    """All Phase 2 archetypes must declare fallback_provider=claude."""
    matrix = load_routing_matrix(_REAL_MATRIX_PATH)
    route = get_archetype_route(matrix, name)
    assert route.fallback_provider == "claude"


@pytest.mark.parametrize("name", _ALL_ARCHETYPES)
def test_all_archetypes_have_at_least_one_disable_predicate(name: str):
    """Every archetype must declare at least 1 disable_predicate."""
    matrix = load_routing_matrix(_REAL_MATRIX_PATH)
    route = get_archetype_route(matrix, name)
    assert len(route.disable_predicates) >= 1, (
        f"{name} must have at least 1 disable_predicate"
    )


def test_code_reviewer_has_three_or_more_predicates():
    """code-reviewer is highest-criticality: must have >= 3 disable_predicates."""
    matrix = load_routing_matrix(_REAL_MATRIX_PATH)
    route = get_archetype_route(matrix, "code-reviewer")
    assert len(route.disable_predicates) >= 3


# ---------------------------------------------------------------------------
# Predicate NamedTuple shape
# ---------------------------------------------------------------------------


def test_predicate_namedtuple_exposes_seven_fields():
    """Predicate NamedTuple must expose exactly the documented 7 fields."""
    matrix = load_routing_matrix(_REAL_MATRIX_PATH)
    route = get_archetype_route(matrix, "code-reviewer")
    pred = route.disable_predicates[0]
    for field in ("id", "type", "metric", "operator", "value", "window_minutes", "window_days"):
        assert hasattr(pred, field), f"Predicate missing field '{field}'"
    # Type constraints
    assert isinstance(pred.id, str) and pred.id
    assert pred.type in ("duration_threshold", "numeric_threshold", "boolean")
    assert pred.operator in (">", ">=", "<", "<=", "==")


# ---------------------------------------------------------------------------
# Schema validation: negative paths via synthetic YAML in tmp_path
# ---------------------------------------------------------------------------


def test_missing_schema_version_raises(tmp_path: Path):
    """YAML without schema_version must raise RoutingMatrixError."""
    text = _build_minimal_yaml()
    text = "\n".join(
        l for l in text.splitlines() if not l.startswith("schema_version:")
    ) + "\n"
    p = tmp_path / "matrix.yaml"
    p.write_text(text, encoding="utf-8")
    with pytest.raises(RoutingMatrixError):
        load_routing_matrix(p)


def test_unknown_archetype_name_raises(tmp_path: Path):
    """An archetype name not in _KNOWN_ARCHETYPES must raise RoutingMatrixError."""
    # Inject a bogus archetype block after the real 8
    extra = "  totally-bogus-archetype:\n" + _ARCH_BLOCK[_ARCH_BLOCK.index("\n") + 1:].replace("{name}", "")
    text = _build_minimal_yaml()
    text = text.replace("\npredicate_types:", extra + "\npredicate_types:")
    p = tmp_path / "matrix.yaml"
    p.write_text(text, encoding="utf-8")
    with pytest.raises(RoutingMatrixError, match="unknown archetype"):
        load_routing_matrix(p)


def test_unknown_coder_provider_raises(tmp_path: Path):
    """coder=gpt (not in _KNOWN_PROVIDERS) must raise RoutingMatrixError."""
    # Codex iter 1 P0-2 cascade: _ARCH_BLOCK now needs both name + model.
    bad_block = _ARCH_BLOCK.replace("coder: claude", "coder: gpt").format(
        name="code-reviewer", model="opus"
    )
    text = _build_minimal_yaml(override_blocks={"code-reviewer": bad_block})
    p = tmp_path / "matrix.yaml"
    p.write_text(text, encoding="utf-8")
    with pytest.raises(RoutingMatrixError):
        load_routing_matrix(p)


def test_unknown_reviewer_provider_raises(tmp_path: Path):
    """reviewer=openai (not in _KNOWN_PROVIDERS) must raise RoutingMatrixError."""
    bad_block = _ARCH_BLOCK.replace("reviewer: codex", "reviewer: openai").format(
        name="code-reviewer", model="opus"
    )
    text = _build_minimal_yaml(override_blocks={"code-reviewer": bad_block})
    p = tmp_path / "matrix.yaml"
    p.write_text(text, encoding="utf-8")
    with pytest.raises(RoutingMatrixError):
        load_routing_matrix(p)


def test_unknown_predicate_type_raises(tmp_path: Path):
    """Predicate with type=magic_threshold must raise RoutingMatrixError."""
    bad_block = (
        "  code-reviewer:\n"
        "    coder: claude\n"
        "    coder_model: opus\n"
        "    reviewer: codex\n"
        "    reviewer_sandbox: read-only\n"
        "    fallback_provider: claude\n"
        "    health_prereq:\n"
        "      - u1_pass\n"
        "    disable_predicates:\n"
        "      - id: bad_pred\n"
        "        type: magic_threshold\n"
        "        metric: codex_outage_minutes\n"
        '        operator: ">"\n'
        "        value: 5\n"
        "        window_minutes: 60\n"
    )
    text = _build_minimal_yaml(override_blocks={"code-reviewer": bad_block})
    p = tmp_path / "matrix.yaml"
    p.write_text(text, encoding="utf-8")
    with pytest.raises(RoutingMatrixError, match="unknown predicate type"):
        load_routing_matrix(p)


def test_unknown_predicate_operator_raises(tmp_path: Path):
    """Predicate with operator='!=' must raise RoutingMatrixError."""
    bad_block = (
        "  code-reviewer:\n"
        "    coder: claude\n"
        "    coder_model: opus\n"
        "    reviewer: codex\n"
        "    reviewer_sandbox: read-only\n"
        "    fallback_provider: claude\n"
        "    health_prereq:\n"
        "      - u1_pass\n"
        "    disable_predicates:\n"
        "      - id: bad_op\n"
        "        type: duration_threshold\n"
        "        metric: codex_outage_minutes\n"
        '        operator: "!="\n'
        "        value: 5\n"
        "        window_minutes: 60\n"
    )
    text = _build_minimal_yaml(override_blocks={"code-reviewer": bad_block})
    p = tmp_path / "matrix.yaml"
    p.write_text(text, encoding="utf-8")
    with pytest.raises(RoutingMatrixError, match="unknown operator"):
        load_routing_matrix(p)


def test_missing_archetype_from_required_8_raises(tmp_path: Path):
    """A matrix with only 7 archetypes must raise RoutingMatrixError for the missing one."""
    archetypes_7 = _ALL_ARCHETYPES[:-1]  # drop threat-detection-engineer
    text = _build_minimal_yaml(archetypes=archetypes_7)
    p = tmp_path / "matrix.yaml"
    p.write_text(text, encoding="utf-8")
    with pytest.raises(RoutingMatrixError, match="missing archetypes"):
        load_routing_matrix(p)


def test_tab_in_indent_raises(tmp_path: Path):
    """A YAML line with a tab character in leading indent must raise RoutingMatrixError."""
    text = _build_minimal_yaml()
    # Replace the 2-space indent of "  code-reviewer:" with a tab
    text = text.replace("  code-reviewer:", "\tcode-reviewer:", 1)
    p = tmp_path / "matrix.yaml"
    p.write_text(text, encoding="utf-8")
    with pytest.raises(RoutingMatrixError):
        load_routing_matrix(p)


def test_flow_style_mapping_raises(tmp_path: Path):
    """A YAML line starting with '{' (flow-style mapping) must raise RoutingMatrixError."""
    text = _build_minimal_yaml()
    # Inject a flow-style mapping inside the archetypes section
    text = text.replace(
        "  code-reviewer:\n", "  code-reviewer: {coder: claude}\n"
    )
    p = tmp_path / "matrix.yaml"
    p.write_text(text, encoding="utf-8")
    with pytest.raises(RoutingMatrixError):
        load_routing_matrix(p)


# ---------------------------------------------------------------------------
# SHA-pin env-var tests
# ---------------------------------------------------------------------------


def test_sha_pin_mismatch_with_failclosed_raises(tmp_path: Path, monkeypatch):
    """CEO_PAIR_RAIL_MATRIX_SHA256 mismatch + CEO_PAIR_RAIL_FAILCLOSED=1 must raise."""
    text = _build_minimal_yaml()
    p = tmp_path / "matrix.yaml"
    p.write_text(text, encoding="utf-8")
    monkeypatch.setenv("CEO_PAIR_RAIL_MATRIX_SHA256", "dead" * 16)
    monkeypatch.setenv("CEO_PAIR_RAIL_FAILCLOSED", "1")
    with pytest.raises(RoutingMatrixError, match="SHA-256 mismatch"):
        load_routing_matrix(p)


def test_sha_pin_mismatch_without_failclosed_loads_and_returns_actual_digest(
    tmp_path: Path, monkeypatch
):
    """Mismatch without FAILCLOSED=1: loader succeeds and matrix.sha256 reflects actual bytes."""
    text = _build_minimal_yaml()
    p = tmp_path / "matrix.yaml"
    p.write_text(text, encoding="utf-8")
    actual = hashlib.sha256(text.encode("utf-8")).hexdigest()
    monkeypatch.setenv("CEO_PAIR_RAIL_MATRIX_SHA256", "cafe" * 16)
    monkeypatch.delenv("CEO_PAIR_RAIL_FAILCLOSED", raising=False)
    matrix = load_routing_matrix(p)
    assert matrix.sha256 == actual


# ---------------------------------------------------------------------------
# is_pair_rail_enabled fail-OPEN
# ---------------------------------------------------------------------------


def test_is_pair_rail_enabled_returns_true_when_no_audit_log(tmp_path: Path):
    """is_pair_rail_enabled returns True (fail-OPEN) when the audit-log file does not exist."""
    text = _build_minimal_yaml()
    p = tmp_path / "matrix.yaml"
    p.write_text(text, encoding="utf-8")
    matrix = load_routing_matrix(p)
    nonexistent = tmp_path / "nonexistent-audit-log.jsonl"
    result = is_pair_rail_enabled(matrix, "qa-architect", audit_log_path=nonexistent)
    assert result is True
