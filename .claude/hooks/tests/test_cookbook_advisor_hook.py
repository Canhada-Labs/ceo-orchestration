"""PLAN-092 Wave A.6 - cookbook-advisor hook test suite.

13 tests across 7 classes covering: data validity, SKILL.md bijection (AC1b),
pattern matching + privacy (AC3 + AC3b), kill-switch (AC13), audit emit
contract (AC3b), stdlib-import invariant (AC15), and callsite wiring (AC3).

Plan reference: .claude/plans/PLAN-092-tier-3-real-wire-bucket.md
Sibling module: .claude/hooks/_lib/cookbook_patterns.py (Wave A.2)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
HOOKS_DIR = REPO_ROOT / ".claude" / "hooks"
LIB_DIR = HOOKS_DIR / "_lib"
DATA_PATH = REPO_ROOT / ".claude" / "data" / "cookbook_patterns.json"
SKILL_MD = REPO_ROOT / ".claude" / "skills" / "core" / "cookbook-advisor" / "SKILL.md"

if str(HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(HOOKS_DIR))

from _lib import cookbook_patterns as cp  # noqa: E402
from _lib import audit_emit  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def matching_prompt_p1():
    # Hits COOK-P1 via "emit json" + "tool_choice .* strict" + "downstream automation"
    return "Emit JSON for downstream automation using strict tool_choice in the response"


@pytest.fixture
def matching_prompt_p2():
    # Hits COOK-P2 via "chain-of-verification" + "fact-check"
    return "Use chain-of-verification to fact-check the model's claims"


@pytest.fixture
def matching_prompt_p3():
    # Hits COOK-P3 via "citations api" + "cite the source"
    return "Cite the source document via Citations API for source attribution"


@pytest.fixture
def matching_prompt_p4():
    # Hits COOK-P4 via "message batches api" + "overnight job" + "bulk process"
    return "Batch process 10000 messages overnight via Message Batches API for bulk request workloads"


@pytest.fixture
def non_matching_prompt():
    return "Refactor this code to be more readable"


# ---------------------------------------------------------------------------
# AC1 - data validity
# ---------------------------------------------------------------------------

class TestCookbookPatternsData:
    def test_json_loads_valid(self):
        """AC1: data file parses as valid JSON via stdlib only."""
        with open(DATA_PATH, "r", encoding="utf-8") as f:
            payload = json.load(f)
        assert isinstance(payload, dict)
        assert "patterns" in payload

    def test_loader_helper_returns_validated_payload(self):
        """AC1: load_cookbook_patterns() returns a validated dict with 4 IDs."""
        payload = cp.load_cookbook_patterns()
        assert isinstance(payload, dict)
        patterns = payload["patterns"]
        for pid in ("COOK-P1", "COOK-P2", "COOK-P3", "COOK-P4"):
            assert pid in patterns, "Missing canonical ID " + pid


# ---------------------------------------------------------------------------
# AC1b - bijection between data file and SKILL.md
# ---------------------------------------------------------------------------

class TestSkillMdBijection:
    def test_skill_md_references_all_4_cook_ids(self):
        """AC1b bijection: SKILL.md references all 4 COOK-P{1..4}."""
        text = SKILL_MD.read_text(encoding="utf-8")
        for pid in ("COOK-P1", "COOK-P2", "COOK-P3", "COOK-P4"):
            assert pid in text, "SKILL.md missing " + pid


# ---------------------------------------------------------------------------
# AC3 + AC3b - pattern matching + privacy invariant
# ---------------------------------------------------------------------------

class TestMatchPattern:
    def test_match_pattern_p1(self, matching_prompt_p1):
        """AC3: COOK-P1 fires on structured-extract trigger taxonomy."""
        result = cp.match_pattern(matching_prompt_p1)
        assert result is not None
        pid, trigger_class, bucket = result
        assert pid == "COOK-P1"
        assert trigger_class == "structured-extract"
        assert bucket in ("low", "medium", "high")

    def test_match_pattern_no_match_on_non_cookbook_prompt(self, non_matching_prompt):
        """AC3b: no false-positive emit on non-matching prompt."""
        result = cp.match_pattern(non_matching_prompt)
        assert result is None

    def test_match_pattern_returns_3_tuple_only(self, matching_prompt_p4):
        """AC3b: returned shape is exactly (pattern_id, trigger_class, bucket) - 3 fields."""
        result = cp.match_pattern(matching_prompt_p4)
        assert result is not None
        assert isinstance(result, tuple)
        assert len(result) == 3
        pid, trigger_class, bucket = result
        assert pid == "COOK-P4"


# ---------------------------------------------------------------------------
# AC13 - kill-switch
# ---------------------------------------------------------------------------

class TestKillSwitch:
    def test_kill_switch_default_on(self, monkeypatch):
        """AC13: kill_switch_enabled() returns True when env var absent (default ON)."""
        monkeypatch.delenv("CEO_COOKBOOK_ADVISOR_ENABLED", raising=False)
        assert cp.kill_switch_enabled() is True

    def test_kill_switch_off_when_env_zero(self, monkeypatch):
        """AC13: kill_switch_enabled() returns False when env=0."""
        monkeypatch.setenv("CEO_COOKBOOK_ADVISOR_ENABLED", "0")
        assert cp.kill_switch_enabled() is False


# ---------------------------------------------------------------------------
# AC3b - audit emit contract (no raw prompt leakage)
# ---------------------------------------------------------------------------

class TestAuditEmitContract:
    def test_emit_cookbook_pattern_advised_registered(self):
        """AC1: emit fn exists in audit_emit (PLAN-088 W3.2)."""
        assert hasattr(audit_emit, "emit_cookbook_pattern_advised"), \
            "emit_cookbook_pattern_advised must be registered"

    def test_match_result_never_contains_raw_prompt(self, matching_prompt_p2):
        """AC3b: match result is the 3-tuple ID/class/bucket; raw prompt NEVER returned."""
        result = cp.match_pattern(matching_prompt_p2)
        assert result is not None
        # Each field is a short identifier - assert prompt text is not embedded.
        for field in result:
            assert matching_prompt_p2 not in str(field), \
                "Raw prompt text leaked into match-pattern return field"
            # And each field is reasonably short (ID/class/bucket vocabulary)
            assert len(str(field)) <= 128, \
                "Match field unexpectedly long; possible prompt leakage"


# ---------------------------------------------------------------------------
# AC15 - stdlib-import invariant
# ---------------------------------------------------------------------------

class TestStdlibInvariant:
    def test_cookbook_patterns_module_stdlib_only(self):
        """AC15: cookbook_patterns.py imports only stdlib (no PyYAML, no jsonschema)."""
        src = (LIB_DIR / "cookbook_patterns.py").read_text(encoding="utf-8")
        forbidden = ("import yaml", "from yaml", "import jsonschema", "from jsonschema")
        for token in forbidden:
            assert token not in src, "AC15 FAIL: " + token + " found in cookbook_patterns.py"

    def test_check_agent_spawn_no_pyyaml_no_jsonschema(self):
        """AC15: check_agent_spawn.py does NOT import yaml or jsonschema."""
        src = (HOOKS_DIR / "check_agent_spawn.py").read_text(encoding="utf-8")
        forbidden = ("import yaml", "from yaml", "import jsonschema", "from jsonschema")
        for token in forbidden:
            assert token not in src, "AC15 FAIL: " + token + " found in check_agent_spawn.py"


# ---------------------------------------------------------------------------
# AC3 - callsite wiring (depends on Wave A.4 patch being applied)
# ---------------------------------------------------------------------------

class TestCallsiteWiring:
    def test_callsite_grep_discoverable_in_check_agent_spawn(self):
        """AC3: callsite wired - both definition AND invocation present in check_agent_spawn.py.

        This test FAILS until Wave A.4 patch lands (kernel-protected edit).
        If only the definition is present without the invocation, this catches
        an incomplete real-wire.
        """
        src = (HOOKS_DIR / "check_agent_spawn.py").read_text(encoding="utf-8")
        # The function must be defined exactly once.
        assert src.count("def _emit_cookbook_pattern_advisory(") == 1, \
            "function definition missing or duplicated"
        # And invoked at least once (separate from the def).
        invocation_lines = [
            line for line in src.splitlines()
            if "_emit_cookbook_pattern_advisory(" in line and "def " not in line
        ]
        assert len(invocation_lines) >= 1, \
            "AC3 FAIL: no invocation site found for _emit_cookbook_pattern_advisory"
