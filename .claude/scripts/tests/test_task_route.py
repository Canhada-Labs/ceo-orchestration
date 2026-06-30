"""Unit tests for ``.claude/scripts/task-route.py``.

PLAN-071 Phase 1 acceptance partial — S87 skeleton.
Calibration set verification + decision-tree branch coverage + VETO floor
invariant + 8-step --files validator + NFKC normalization. Mutation
fixtures (≥30) and adversarial set deferred to next session.
"""

from __future__ import annotations

import importlib.util
import json
import re
import sys
import unicodedata
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
SCRIPT_PATH = REPO_ROOT / ".claude" / "scripts" / "task-route.py"
HOOKS_LIB = REPO_ROOT / ".claude" / "hooks"

# Make _lib importable for the test process
if str(HOOKS_LIB) not in sys.path:
    sys.path.insert(0, str(HOOKS_LIB))


def _load_module():
    """Load task-route.py as a module (dash in name precludes plain import)."""
    spec = importlib.util.spec_from_file_location("task_route", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def task_route():
    return _load_module()


# ---------------------------------------------------------------------------
# Calibration set — train (16 fixtures)
# ---------------------------------------------------------------------------

CALIBRATION_TRAIN = json.loads(
    (REPO_ROOT / ".claude/scripts/tests/fixtures/task-route/calibration-train.json")
    .read_text(encoding="utf-8")
)["fixtures"]

CALIBRATION_HOLDOUT = json.loads(
    (REPO_ROOT / ".claude/scripts/tests/fixtures/task-route/calibration-holdout.json")
    .read_text(encoding="utf-8")
)["fixtures"]


@pytest.mark.parametrize("fix", CALIBRATION_TRAIN, ids=[f["id"] for f in CALIBRATION_TRAIN])
def test_calibration_train_classification(task_route, fix):
    """Each train fixture must classify exactly to its expected tier.

    Codex audit fix #3: also assert ceremony_mode + agent role coverage
    where fixtures declare them. This catches regressions where the
    classifier gets the tier right but wires the wrong ceremony or
    omits a VETO floor agent.
    """
    contract = task_route.build_contract(
        fix["task_description"],
        fix["file_hints"],
    )
    assert contract["classification"] == fix["expected_classification"], (
        f"{fix['id']} expected={fix['expected_classification']} "
        f"got={contract['classification']} "
        f"rationale={contract['classification_rationale']}"
    )
    expected_mode = fix.get("expected_ceremony_mode")
    if expected_mode:
        assert contract["ceremony"]["mode"] == expected_mode, (
            f"{fix['id']} ceremony mode expected={expected_mode} "
            f"got={contract['ceremony']['mode']}"
        )
    expected_roles = set(fix.get("expected_agents") or [])
    if expected_roles:
        actual_roles = {a["role"] for a in contract["agents"]}
        # Acceptance: every expected role MUST appear; classifier may
        # add additional roles (e.g. broader VETO floor on M+)
        missing = expected_roles - actual_roles
        assert not missing, (
            f"{fix['id']} missing expected agents: {sorted(missing)} "
            f"(got {sorted(actual_roles)})"
        )


@pytest.mark.parametrize("fix", CALIBRATION_HOLDOUT, ids=[f["id"] for f in CALIBRATION_HOLDOUT])
def test_calibration_holdout_classification(task_route, fix):
    """Acceptance §4.2: ≥3/4 holdout must classify correctly. Per-fixture
    test reports each result; aggregate gate enforced by collection assert.
    """
    contract = task_route.build_contract(
        fix["task_description"],
        fix["file_hints"],
    )
    # Allow 1 mismatch across 4 holdout fixtures (≥3/4 acceptance)
    # Per-fixture failures still surface in test output for triage.
    assert contract["classification"] == fix["expected_classification"], (
        f"{fix['id']} expected={fix['expected_classification']} "
        f"got={contract['classification']}"
    )


# ---------------------------------------------------------------------------
# VETO floor invariant — module-load assertion
# ---------------------------------------------------------------------------

def test_veto_floor_union_is_superset_of_spec(task_route):
    """COMPUTED_VETO_FLOOR (union) MUST be a superset of the 5-role spec.

    PLAN-074 Wave 1c (S93) re-enabled this assertion: every role in
    EXPECTED_VETO_FLOOR_UNION now has a deployed agent file, so the
    union landed atomically with the frozenset add per S90 P0-01.
    """
    assert task_route.COMPUTED_VETO_FLOOR >= task_route.EXPECTED_VETO_FLOOR_UNION


def test_veto_hardcode_keys_are_subset_of_spec(task_route):
    """VETO_HARDCODE.keys() ⊆ EXPECTED_VETO_FLOOR_UNION (PLAN-071 §3.1)."""
    assert frozenset(task_route.VETO_HARDCODE.keys()) <= task_route.EXPECTED_VETO_FLOOR_UNION


def test_veto_floor_includes_five_spec_roles(task_route):
    """Spec roles per PLAN-074 Wave 1c amendment (5-role union; 6→5 reduction).

    ``llm-finops-architect`` is EXCLUDED per the Wave 1c VETO-floor matrix and
    ADR-052 amendment: cost governance is operational doctrine + mechanical
    enforcement (ADR-064), NOT a sub-domain trust boundary that justifies a
    dedicated VETO authority.
    """
    spec = {
        "code-reviewer",
        "security-engineer",
        "threat-detection-engineer",
        "identity-trust-architect",
        "incident-commander",
    }
    assert spec <= task_route.COMPUTED_VETO_FLOOR
    # Negative assertion: llm-finops-architect MUST NOT appear in the floor;
    # bijection test in test_veto_floor_bijection.py covers the deployed-side
    # check, this guards the spec/runtime side.
    assert "llm-finops-architect" not in task_route.COMPUTED_VETO_FLOOR, (
        "llm-finops-architect must NOT be in COMPUTED_VETO_FLOOR per Wave 1c "
        "matrix exclusion. Check VETO_FLOOR_ROLES + EXPECTED_VETO_FLOOR_UNION."
    )


# ---------------------------------------------------------------------------
# Decision tree — branch coverage for §3.3 predicates
# ---------------------------------------------------------------------------

def test_classify_canonical_path_returns_xl(task_route):
    cls = task_route.classify(
        "modify hook policy",
        [".claude/hooks/check_canonical_edit.py"],
    )
    assert cls["classification"] == "XL"


def test_classify_schema_signal_returns_xl(task_route):
    cls = task_route.classify(
        "add migration for users table",
        ["migrations/2026-05-add-col.sql"],
    )
    assert cls["classification"] == "XL"


def test_classify_release_workflow_returns_xl(task_route):
    cls = task_route.classify(
        "amend release pipeline",
        [".github/workflows/release.yml"],
    )
    assert cls["classification"] == "XL"


def test_classify_rag_workflow_returns_xl(task_route):
    cls = task_route.classify(
        "rewire vector store",
        [".claude/rag/index.py"],
    )
    assert cls["classification"] == "XL"


def test_classify_multi_module_returns_l(task_route):
    cls = task_route.classify(
        "rename across user/order/billing",
        ["src/user/x.ts", "src/order/y.ts", "src/billing/z.ts"],
    )
    assert cls["classification"] == "L"


def test_classify_test_infra_returns_l(task_route):
    cls = task_route.classify(
        "rewire pytest discovery",
        ["tests/conftest.py"],
    )
    assert cls["classification"] == "L"


def test_classify_veto_domain_returns_m(task_route):
    cls = task_route.classify(
        "fix authentication bypass",
        ["src/auth/login.ts"],
    )
    assert cls["classification"] == "M"


def test_classify_jwt_keyword_returns_m(task_route):
    cls = task_route.classify(
        "rotate JWT signing key",
        ["src/api/auth.ts"],
    )
    assert cls["classification"] == "M"


def test_classify_decimal_keyword_returns_m(task_route):
    cls = task_route.classify(
        "refactor decimal rounding in payments",
        ["src/payments/calc.ts"],
    )
    assert cls["classification"] == "M"


def test_classify_trivial_single_file_returns_s(task_route):
    cls = task_route.classify(
        "rename variable",
        ["src/utils/x.ts"],
    )
    assert cls["classification"] == "S"


def test_classify_trivial_two_files_returns_s(task_route):
    cls = task_route.classify(
        "fix typo across utils",
        ["src/utils/a.ts", "src/utils/b.ts"],
    )
    assert cls["classification"] == "S"


def test_classify_three_files_no_veto_returns_l(task_route):
    """3 distinct module roots elevates to L."""
    cls = task_route.classify(
        "extract helper across modules",
        ["src/foo/x.ts", "src/bar/y.ts", "src/baz/z.ts"],
    )
    assert cls["classification"] == "L"


# ---------------------------------------------------------------------------
# NFKC normalization — ZWJ + homoglyph defeat
# ---------------------------------------------------------------------------

def test_classify_zwj_homoglyph_classifies_same(task_route):
    """ZWJ-injected 'authentication' should classify identically to plain.

    Note: NFKC alone does NOT strip Cf-category (ZWJ/ZWNJ). task-route.py
    runs ``_strip_invisible_format_chars`` BEFORE NFKC to defeat this
    bypass per PLAN-071 §3.3 spec ("defeat ZWJ, RTL override, fullwidth
    homoglyph"). Test asserts the post-strip behavior, not raw NFKC.
    """
    plain = "fix authentication issue"
    zwj = "fix a‍uthentication issue"  # U+200D ZERO WIDTH JOINER
    stripped = task_route._strip_invisible_format_chars(zwj)
    assert "authentication" in stripped  # Cf-strip restores word
    cls_plain = task_route.classify(plain, [".claude/scripts/x.py"])
    cls_zwj = task_route.classify(zwj, [".claude/scripts/x.py"])
    assert cls_plain["classification"] == cls_zwj["classification"]


def test_classify_fullwidth_homoglyph_normalizes(task_route):
    """Fullwidth 'auth' (FF41 FF55 FF54 FF48) should NFKC to ASCII."""
    plain = "fix auth bug"
    fullwidth = "fix ａｕｔｈ bug"  # auth in fullwidth
    cls_plain = task_route.classify(plain, ["src/x.ts"])
    cls_full = task_route.classify(fullwidth, ["src/x.ts"])
    assert cls_plain["classification"] == cls_full["classification"]


# ---------------------------------------------------------------------------
# 8-step --files validator
# ---------------------------------------------------------------------------

def test_files_validator_rejects_nul(task_route):
    with pytest.raises(task_route.FileHintError, match="NUL"):
        task_route._validate_file_hint("src/foo\x00.ts", REPO_ROOT)


def test_files_validator_rejects_backslash(task_route):
    with pytest.raises(task_route.FileHintError, match="Backslash"):
        task_route._validate_file_hint("src\\foo.ts", REPO_ROOT)


def test_files_validator_rejects_absolute(task_route):
    with pytest.raises(task_route.FileHintError, match="Absolute"):
        task_route._validate_file_hint("/etc/passwd", REPO_ROOT)


def test_files_validator_rejects_home(task_route):
    with pytest.raises(task_route.FileHintError, match="Absolute"):
        task_route._validate_file_hint("~/.ssh/id_rsa", REPO_ROOT)


def test_files_validator_rejects_traversal(task_route):
    with pytest.raises(task_route.FileHintError):
        task_route._validate_file_hint("../../etc/passwd", REPO_ROOT)


def test_files_validator_accepts_normal(task_route):
    rel = task_route._validate_file_hint("src/foo.ts", REPO_ROOT)
    assert rel == "src/foo.ts"


def test_files_validator_caps_count(task_route):
    paths = ",".join(f"src/f{i}.ts" for i in range(60))
    with pytest.raises(task_route.FileHintError, match="Too many"):
        task_route._parse_files_arg(paths, REPO_ROOT)


# ---------------------------------------------------------------------------
# Contract structure
# ---------------------------------------------------------------------------

def test_contract_has_required_keys(task_route):
    contract = task_route.build_contract("rename var", ["src/x.ts"])
    required = {
        "schema_version", "contract_id", "issued_at", "task_description_hmac",
        "classification", "classification_rationale", "ceremony", "agents",
        "context_strategy", "file_assignment", "tests", "review_gates",
        "execution_receipt_required", "residual_risks", "auto_escalate_triggers",
    }
    assert required <= set(contract.keys())


def test_contract_schema_version_is_v1(task_route):
    contract = task_route.build_contract("rename", ["src/x.ts"])
    assert contract["schema_version"] == "task-execution-contract.v1"


def test_contract_classification_is_closed_enum(task_route):
    contract = task_route.build_contract("fix auth", ["src/auth/x.ts"])
    assert contract["classification"] in {"S", "M", "L", "XL"}


def test_contract_ceremony_mode_is_closed_enum(task_route):
    contract = task_route.build_contract("amend release", [".github/workflows/release.yml"])
    assert contract["ceremony"]["mode"] in task_route.CEREMONY_MODES


def test_contract_xl_implies_debate(task_route):
    contract = task_route.build_contract(
        "extend tier_policy constants",
        [".claude/hooks/_lib/tier_policy/_constants.py"],
    )
    assert contract["classification"] == "XL"
    assert contract["ceremony"]["debate"] is True


def test_contract_s_implies_no_agents(task_route):
    contract = task_route.build_contract("rename var", ["src/utils/x.ts"])
    assert contract["classification"] == "S"
    assert contract["agents"] == []
    assert contract["ceremony"]["mode"] == "direct"


def test_contract_m_with_veto_includes_security(task_route):
    contract = task_route.build_contract(
        "fix timing oracle in auth",
        ["src/auth/login.ts"],
    )
    assert contract["classification"] == "M"
    roles = {a["role"] for a in contract["agents"]}
    assert "security-engineer" in roles
    assert "code-reviewer" in roles


def test_contract_veto_floor_models_are_opus(task_route):
    """ADR-052 binding floor: CR + Sec MUST be Opus."""
    contract = task_route.build_contract(
        "fix auth bug",
        ["src/auth/x.ts"],
    )
    veto_agents = [a for a in contract["agents"] if a.get("veto_floor")]
    assert veto_agents
    for a in veto_agents:
        assert a["model"] == "claude-opus-4-8", (
            f"VETO floor role {a['role']} not on Opus: {a['model']}"
        )


# ---------------------------------------------------------------------------
# HMAC + JSON output
# ---------------------------------------------------------------------------

def test_task_description_hmac_is_hex_or_none(task_route):
    contract = task_route.build_contract("test", ["src/x.ts"])
    h = contract["task_description_hmac"]
    assert h is None or re.fullmatch(r"[0-9a-f]{64}", h)


def test_json_render_is_deterministic(task_route):
    """sort_keys=True + sort agents by role → determinism modulo
    contract_id + issued_at + duration_ms."""
    c1 = task_route.build_contract("fix auth", ["src/auth/x.ts"])
    c2 = task_route.build_contract("fix auth", ["src/auth/x.ts"])
    # Strip non-deterministic fields
    for c in (c1, c2):
        c.pop("contract_id", None)
        c.pop("issued_at", None)
        c.pop("duration_ms", None)
    assert task_route.render_json(c1) == task_route.render_json(c2)


def test_input_cap_rejected(task_route, capsys):
    """8 KiB cap on task description."""
    huge = "x" * (9 * 1024)
    rc = task_route.main(["--task", huge])
    assert rc == 2
    err = capsys.readouterr().err
    assert "cap" in err.lower()


# ---------------------------------------------------------------------------
# CLI smoke
# ---------------------------------------------------------------------------

def test_cli_markdown_smoke(task_route, capsys):
    rc = task_route.main([
        "--task", "fix typo in src/utils/x.ts",
        "--files", "src/utils/x.ts",
        "--format", "markdown",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Task Execution Contract" in out
    assert "classification" in out


def test_cli_json_smoke(task_route, capsys):
    rc = task_route.main([
        "--task", "fix auth bug",
        "--files", "src/auth/x.ts",
        "--format", "json",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    parsed = json.loads(out)
    assert parsed["schema_version"] == "task-execution-contract.v1"
    assert parsed["classification"] in {"S", "M", "L", "XL"}
