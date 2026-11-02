"""PLAN-176 semantic model currency regression tests."""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

_HOOKS = Path(__file__).resolve().parents[1]
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))

from _lib import model_currency as currency  # noqa: E402
from _lib import effective_config as effective  # noqa: E402
from _lib.agent_frontmatter import check_veto_floor_for_role  # noqa: E402
from _subprocess_helpers import run_python


def test_fu144_model_currency_accepts_homologated_families() -> None:
    for name in ("claude-sonnet-9-1", "gpt-6.1-sol", "o3-mini", "gemini-2.5", "grok-3-fast"):
        assert currency.is_allowed_model(name)
    assert currency.is_veto_floor_model("claude-opus-4-9")
    assert not currency.is_veto_floor_model("claude-sonnet-9-1")


def test_fu144_model_currency_blocks_retired_and_malformed() -> None:
    for name in ("claude-opus-4-1", "gpt-4o", "gpt-5 bad", "claude-opus-4-1x"):
        assert not currency.is_allowed_model(name, ["claude-opus-4-1"])
    assert currency.is_veto_floor_model("claude-fable-5", ["claude-fable-5"])


def test_fu144_effective_config_accepts_future_family_without_adr_edit() -> None:
    resolved = {"project_dir": "/unused", "layers": []}
    with patch.object(effective, "get_model_allowlist", return_value=["claude-opus-4-8"]):
        findings = effective.classify_tampering(resolved, {"ANTHROPIC_MODEL": "gpt-6.1-sol"})
    assert [f for f in findings if f["class"] == effective.TAMPER_MODEL_REMAP] == []


def test_fu144_frontmatter_uses_floor_family_but_expected_pin_stays_exact() -> None:
    with tempfile.TemporaryDirectory() as raw:
        agents = Path(raw)
        (agents / "security-engineer.md").write_text(
            "---\nname: security-engineer\nmodel: claude-opus-9-1\n---\n", encoding="utf-8"
        )
        assert check_veto_floor_for_role("security-engineer", agents)[0]
        (agents / "security-engineer.md").write_text(
            "---\nname: security-engineer\nmodel: claude-sonnet-9-1\n---\n", encoding="utf-8"
        )
        assert not check_veto_floor_for_role("security-engineer", agents)[0]
        assert not check_veto_floor_for_role(
            "security-engineer", agents, expected_model="claude-opus-9-1"
        )[0]


def test_fu144_model_currency_cli_preserves_family_and_veto_rejections() -> None:
    script = str(_HOOKS / "_lib" / "model_currency.py")
    run_python([script, "gpt-9.2-sol"])
    run_python([script, "claude-opus-4-1"], expected_returncode=1)
    run_python([script, "--veto", "claude-sonnet-9-1"], expected_returncode=1)
    run_python([script], expected_returncode=2)
