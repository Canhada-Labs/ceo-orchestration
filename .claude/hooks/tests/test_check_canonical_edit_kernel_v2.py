"""PLAN-089 Wave A.5 — kernel HARD-DENY v2 parametrized subsumption tests.

Source of truth: `.claude/plans/PLAN-089/kernel-extension-v2-enumeration.md`.

Wave A.1 enumerates +65 net-new kernel-tier paths (with 5 honest
deferrals). The deployable-subset per §Final tallies §3 is the
~30 highest-leverage rows: all 14 `_lib/` entries + 5 tier_policy
entries + 6 hot-path hooks + 5 governance anchors.

This test asserts:

1. **Subset row coverage (parametrized)**: every row in the
   deployable subset (~30 rows) is detected by `_is_kernel_path`
   *post-Wave-A.4 ceremony*. Pre-ceremony these are decorated with
   `xfail(strict=True, reason="pending PLAN-089 Wave A.4 ceremony")`
   so the test author removes the xfail decorator (or the test
   passes naturally) after `_KERNEL_PATHS` is extended.
2. **Cardinality gate**: post-Wave-A.4, `_KERNEL_PATHS` cardinality
   is ≥58. Pre-ceremony this is xfail-strict; passes after.
3. **Negative regression**: a path that IS in current
   `_KERNEL_PATHS` (e.g., `.claude/hooks/check_canonical_edit.py`)
   is still blocked. This test is NOT xfailed — it confirms that
   the Wave A.4 ceremony did not accidentally remove pre-existing
   entries (anti-regression).
4. **Decide-level integration**: the `decide()` function emits a
   `decision=block` payload with `ARBITRATION-KERNEL` in the
   reason when Edit is attempted on a kernel-tier path without
   sentinel + override. Tested against the negative-regression
   path so it passes pre-Wave-A.4.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
_HOOKS = REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS) not in sys.path:
    sys.path.insert(0, str(_HOOKS))

from check_arbitration_kernel import (  # noqa: E402
    _KERNEL_PATHS,
    _is_kernel_path,
    decide,
)


# R2 Codex iter-1 Q10 fold (2026-05-13): conditional xfail keyed on
# `_KERNEL_PATHS` cardinality. Pre-Wave-A.4 (cardinality 30) the xfail
# fires; post-Wave-A.4 (cardinality ≥58) `condition=False` AUTOMATICALLY
# de-activates the marker — no manual decorator removal required.
# Strict=True still catches xpass before ceremony (regression-safe).
_PLAN_089_WAVE_A_APPLIED = len(_KERNEL_PATHS) >= 58
_PENDING_WAVE_A4 = pytest.mark.xfail(
    condition=not _PLAN_089_WAVE_A_APPLIED,
    strict=True,
    reason="pending PLAN-089 Wave A.4 ceremony (_KERNEL_PATHS extension)",
)


# Deployable-subset (~30 rows) from kernel-extension-v2-enumeration.md
# §Final tallies §3: "all 14 `_lib/` entries + 5 tier_policy entries +
# 6 hot-path hooks + 5 governance anchors". Each row is annotated with
# its source enumeration row number (e.g., "row01" → row #1 in
# `kernel-extension-v2-enumeration.md`).
SUBSET_KERNEL_ROWS = [
    # --- 14 `_lib/` entries (enumeration rows #1..#11, #12, #13, #14) ---
    pytest.param(
        ".claude/hooks/_lib/mcp/canonical_guard.py",
        id="row01_mcp_canonical_guard",
        marks=_PENDING_WAVE_A4,
    ),
    pytest.param(
        ".claude/hooks/_lib/mcp/bearer_replay.py",
        id="row02_mcp_bearer_replay",
        marks=_PENDING_WAVE_A4,
    ),
    pytest.param(
        ".claude/hooks/_lib/credentials.py",
        id="row03_lib_credentials",
        marks=_PENDING_WAVE_A4,
    ),
    pytest.param(
        ".claude/hooks/_lib/canonical_json.py",
        id="row04_lib_canonical_json",
        marks=_PENDING_WAVE_A4,
    ),
    pytest.param(
        ".claude/hooks/_lib/audit_rotation.py",
        id="row05_lib_audit_rotation",
        marks=_PENDING_WAVE_A4,
    ),
    pytest.param(
        ".claude/hooks/_lib/replay_redact.py",
        id="row06_lib_replay_redact",
        marks=_PENDING_WAVE_A4,
    ),
    pytest.param(
        ".claude/hooks/_lib/injection_salt.py",
        id="row07_lib_injection_salt",
        marks=_PENDING_WAVE_A4,
    ),
    pytest.param(
        ".claude/hooks/_lib/mcp_injection_scan.py",
        id="row08_lib_mcp_injection_scan",
        marks=_PENDING_WAVE_A4,
    ),
    pytest.param(
        ".claude/hooks/_lib/spec_context_sanitizer.py",
        id="row09_lib_spec_context_sanitizer",
        marks=_PENDING_WAVE_A4,
    ),
    pytest.param(
        ".claude/hooks/_lib/state_store.py",
        id="row10_lib_state_store",
        marks=_PENDING_WAVE_A4,
    ),
    pytest.param(
        ".claude/hooks/_lib/filelock.py",
        id="row11_lib_filelock",
        marks=_PENDING_WAVE_A4,
    ),
    pytest.param(
        ".claude/hooks/_lib/adapters/codex.py",
        id="row12_adapter_codex",
        marks=_PENDING_WAVE_A4,
    ),
    pytest.param(
        ".claude/hooks/_lib/adapters/_constants.py",
        id="row13_adapter_constants",
        marks=_PENDING_WAVE_A4,
    ),
    pytest.param(
        ".claude/hooks/_lib/__init__.py",
        id="row14_lib_init",
        marks=_PENDING_WAVE_A4,
    ),
    # --- 5 tier_policy/ entries (enumeration rows #17..#21) ---
    pytest.param(
        ".claude/hooks/_lib/tier_policy/loader.py",
        id="row17_tier_policy_loader",
        marks=_PENDING_WAVE_A4,
    ),
    pytest.param(
        ".claude/hooks/_lib/tier_policy/__init__.py",
        id="row18_tier_policy_init",
        marks=_PENDING_WAVE_A4,
    ),
    pytest.param(
        ".claude/hooks/_lib/tier_policy/_constants.py",
        id="row19_tier_policy_constants",
        marks=_PENDING_WAVE_A4,
    ),
    pytest.param(
        ".claude/hooks/_lib/tier_policy/_agent_frontmatter.py",
        id="row20_tier_policy_agent_frontmatter",
        marks=_PENDING_WAVE_A4,
    ),
    pytest.param(
        ".claude/hooks/_lib/tier_policy/_types.py",
        id="row21_tier_policy_types",
        marks=_PENDING_WAVE_A4,
    ),
    # --- 6 hot-path hooks (enumeration rows #27..#30, #38, #39) ---
    pytest.param(
        ".claude/hooks/check_pair_rail.py",
        id="row27_check_pair_rail",
        marks=_PENDING_WAVE_A4,
    ),
    pytest.param(
        ".claude/hooks/check_bash_safety.py",
        id="row28_check_bash_safety",
        marks=_PENDING_WAVE_A4,
    ),
    pytest.param(
        ".claude/hooks/check_bash_canonical_forensic.py",
        id="row29_check_bash_canonical_forensic",
        marks=_PENDING_WAVE_A4,
    ),
    pytest.param(
        ".claude/hooks/check_codex_filewrite.py",
        id="row30_check_codex_filewrite",
        marks=_PENDING_WAVE_A4,
    ),
    pytest.param(
        ".claude/hooks/check_mcp_response.py",
        id="row38_check_mcp_response",
        marks=_PENDING_WAVE_A4,
    ),
    pytest.param(
        ".claude/hooks/check_tier_policy.py",
        id="row39_check_tier_policy",
        marks=_PENDING_WAVE_A4,
    ),
    # --- 5 governance anchors (enumeration rows #55..#59) ---
    pytest.param(
        ".claude/governance/governance-waivers.yaml",
        id="row55_gov_waivers",
        marks=_PENDING_WAVE_A4,
    ),
    pytest.param(
        ".claude/governance/codex-cli-pin.txt",
        id="row56_gov_codex_cli_pin",
        marks=_PENDING_WAVE_A4,
    ),
    pytest.param(
        ".claude/governance/codex-cli-binary-sha256.txt",
        id="row57_gov_codex_cli_sha256",
        marks=_PENDING_WAVE_A4,
    ),
    pytest.param(
        ".claude/governance/pair-rail-inputs-hash-manifest.txt",
        id="row58_gov_pair_rail_inputs_manifest",
        marks=_PENDING_WAVE_A4,
    ),
    pytest.param(
        ".claude/governance/pair-rail-verdict-template.md",
        id="row59_gov_pair_rail_verdict_template",
        marks=_PENDING_WAVE_A4,
    ),
]


@pytest.mark.parametrize("path", SUBSET_KERNEL_ROWS)
def test_subset_row_is_kernel_path(path, tmp_path, monkeypatch):
    """Wave A.1 deployable-subset row resolves to kernel-tier.

    Pre-Wave-A.4: xfail-strict (row is NOT in `_KERNEL_PATHS` yet).
    Post-Wave-A.4: passes — `_is_kernel_path` matches the row.

    Uses a temporary repo root with a stub file at the target path so
    `Path.resolve()` succeeds. The kernel-tier match is purely against
    the relative path under `repo_root` (no I/O on `_KERNEL_PATHS`).
    """
    target = tmp_path / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# PLAN-089 Wave A.5 stub\n")
    assert _is_kernel_path(str(target), tmp_path), (
        f"Wave A.1 subset row {path!r} is NOT matched by _is_kernel_path. "
        f"Either the row is missing from `_KERNEL_PATHS` (Wave A.4 not "
        f"landed) or the glob pattern in `_KERNEL_PATHS` does not cover "
        f"this path."
    )


@pytest.mark.parametrize("path", SUBSET_KERNEL_ROWS)
def test_subset_row_decide_blocks_edit_without_override(
    path, tmp_path, monkeypatch
):
    """Edit attempt on a subset row without sentinel + override → block.

    Pre-Wave-A.4: xfail-strict (row is NOT in `_KERNEL_PATHS` yet, so
    `decide` returns allow `{}`). Post-Wave-A.4: passes — `decide`
    returns `{"decision":"block","reason":"ARBITRATION-KERNEL-BLOCKED..."}`.
    """
    target = tmp_path / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# PLAN-089 Wave A.5 stub\n")
    monkeypatch.delenv("CEO_KERNEL_OVERRIDE", raising=False)
    monkeypatch.delenv("CEO_KERNEL_OVERRIDE_ACK", raising=False)
    out = decide(
        tool_name="Edit",
        file_path=str(target),
        repo_root=tmp_path,
        env={},
    )
    payload = json.loads(out)
    assert payload.get("decision") == "block", (
        f"expected decide() to block Edit on {path!r}; got payload={payload!r}"
    )
    assert "ARBITRATION-KERNEL" in payload.get("reason", ""), (
        f"expected ARBITRATION-KERNEL in reason; got reason="
        f"{payload.get('reason')!r}"
    )


@pytest.mark.xfail(
    condition=not _PLAN_089_WAVE_A_APPLIED,
    strict=True,
    reason="pending PLAN-089 Wave A.4 ceremony (_KERNEL_PATHS extension)",
)
def test_kernel_paths_cardinality_post_plan_089_wave_a4():
    """`_KERNEL_PATHS` is >=58 entries post-Wave-A.4.

    Pre-ceremony: xfail-strict (current cardinality = 30).
    Post-ceremony: passes (cardinality jumps to ~58-95 per
    kernel-extension-v2-enumeration.md §Final tallies).
    """
    assert len(_KERNEL_PATHS) >= 58, (
        f"got {len(_KERNEL_PATHS)} — expected >=58 post-PLAN-089 Wave A.4"
    )


# ------------------------------------------------------------------
# Anti-regression — NOT xfailed. These confirm Wave A.4 ceremony did
# NOT accidentally remove pre-existing kernel entries (the Wave E.2
# 13-entry ADR-116 extension that landed in S111). If Wave A.4 ships
# correctly these continue passing; if it regresses, these fail.
# ------------------------------------------------------------------


# Selected pre-existing kernel rows (S111 ADR-116 baseline). These
# rows are ALREADY in `_KERNEL_PATHS` on current main and must stay
# matched after Wave A.4 lands.
PRE_EXISTING_KERNEL_ROWS = [
    pytest.param(
        ".claude/hooks/check_canonical_edit.py",
        id="pre01_check_canonical_edit",
    ),
    pytest.param(
        ".claude/hooks/check_arbitration_kernel.py",
        id="pre02_check_arbitration_kernel",
    ),
    pytest.param(
        ".claude/hooks/_lib/contract.py",
        id="pre03_lib_contract",
    ),
    pytest.param(
        ".claude/hooks/_lib/audit_emit.py",
        id="pre04_lib_audit_emit",
    ),
    pytest.param(
        ".claude/hooks/_lib/adapters/claude.py",
        id="pre05_lib_adapter_claude",
    ),
    pytest.param(
        ".claude/settings.json",
        id="pre06_settings_json",
    ),
    pytest.param(
        ".claude/hooks/_lib/gpg_verify.py",
        id="pre07_lib_gpg_verify",
    ),
    pytest.param(
        ".claude/hooks/_lib/audit_hmac.py",
        id="pre08_lib_audit_hmac",
    ),
    pytest.param(
        ".claude/hooks/_lib/trusted_env.py",
        id="pre09_lib_trusted_env",
    ),
    pytest.param(
        ".github/workflows/release.yml",
        id="pre10_workflow_release",
    ),
]


@pytest.mark.parametrize("path", PRE_EXISTING_KERNEL_ROWS)
def test_preexisting_kernel_row_still_blocked(path, tmp_path, monkeypatch):
    """Anti-regression: pre-Wave-A.4 kernel row stays kernel post-ceremony."""
    target = tmp_path / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# anti-regression probe\n")
    assert _is_kernel_path(str(target), tmp_path), (
        f"anti-regression FAILED: pre-existing kernel row {path!r} no "
        f"longer matches `_is_kernel_path`. Wave A.4 ceremony may have "
        f"accidentally removed entries — review _KERNEL_PATHS diff."
    )


@pytest.mark.parametrize("path", PRE_EXISTING_KERNEL_ROWS)
def test_preexisting_kernel_row_decide_blocks(path, tmp_path, monkeypatch):
    """Anti-regression: decide() blocks Edit on pre-existing kernel row."""
    target = tmp_path / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("# anti-regression probe\n")
    monkeypatch.delenv("CEO_KERNEL_OVERRIDE", raising=False)
    monkeypatch.delenv("CEO_KERNEL_OVERRIDE_ACK", raising=False)
    out = decide(
        tool_name="Edit",
        file_path=str(target),
        repo_root=tmp_path,
        env={},
    )
    payload = json.loads(out)
    assert payload.get("decision") == "block", (
        f"anti-regression FAILED: decide() did NOT block Edit on "
        f"pre-existing kernel row {path!r}. Payload={payload!r}."
    )
    assert "ARBITRATION-KERNEL" in payload.get("reason", ""), (
        f"anti-regression FAILED: reason missing ARBITRATION-KERNEL "
        f"marker on {path!r}. Payload={payload!r}."
    )


def test_kernel_paths_cardinality_floor_30():
    """Cardinality floor — never decrease below S111 baseline (30)."""
    assert len(_KERNEL_PATHS) >= 30, (
        f"_KERNEL_PATHS regressed below S111 baseline: got "
        f"{len(_KERNEL_PATHS)}, expected >=30"
    )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
