"""Tests for check_codex_filewrite.py — PLAN-085 Wave F.2 dedicated suite.

PLAN-081 Phase 5 shipped `check_codex_filewrite.py` with ZERO dedicated
tests. PLAN-085 Wave F.2 closes that gap with a subprocess-driven hook
contract suite covering 8 classes:

  1. TestFailClosedOnUnknownTarget       — malformed/unknown payload
  2. TestKillSwitchEnvVar                — CEO_CODEX_FILEWRITE_DISABLE
  3. TestKillSwitchSentinel              — DRY_RUN sentinel allow-path
  4. TestApplyPatchTargetExtraction      — MCP envelope path keys
  5. TestCanonicalPathDenial             — guarded paths → block/DRY_RUN-emit
  6. TestAllowlistedScratchAllow         — scratch + non-canonical paths
  7. TestMalformedToolInputFailClosed    — malformed stdin → allow (spec)
  8. TestAuditEmitOnDeny                 — audit sink contains hash prefix

Hook contract (from `check_codex_filewrite.py` docstring):

  - Trigger: tool_name in {mcp__codex__codex, mcp__codex__codex-reply}.
  - Kill-switch: CEO_CODEX_FILEWRITE_DISABLE=1 → allow.
  - DRY_RUN default ON (CEO_CODEX_FILEWRITE_DRY_RUN=1): canonical match
    emits + returns allow (with systemMessage).
  - DRY_RUN OFF (CEO_CODEX_FILEWRITE_DRY_RUN=0): canonical match → block.
  - Fail-CLOSED on error path (`_ERROR_FAIL_CLOSED` sentinel) when DRY_RUN
    is OFF; DRY_RUN ON allows + emits with diagnostic systemMessage.
  - Unparseable stdin → allow (R1 S-Sec-7 spec note in main(): "spike
    compatibility with unparseable PreToolUse envelopes we fail-OPEN").

stdlib-only. Hooks invoked as subprocesses (Claude Code hook surface).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

_HOOKS_DIR = Path(__file__).resolve().parent.parent
_HOOK = _HOOKS_DIR / "check_codex_filewrite.py"

# TestEnvContext gives us project_dir + env snapshot + tmp tree.
sys.path.insert(0, str(_HOOKS_DIR))
from _lib.testing import TestEnvContext  # noqa: E402


# ---------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------


def _invoke_hook(
    payload: Dict[str, Any],
    *,
    env_overrides: Optional[Dict[str, str]] = None,
    project_dir: Optional[Path] = None,
    timeout: float = 10.0,
) -> Tuple[int, Dict[str, Any], str]:
    """Run the hook as a subprocess; return (rc, decision_dict, stderr).

    Hooks read JSON from stdin and write JSON to stdout. This mirrors
    the real Claude Code hook surface — never import the hook module
    into the test process (sys.path / env-var bleed risk).
    """
    env = {**os.environ}
    if project_dir is not None:
        env["CLAUDE_PROJECT_DIR"] = str(project_dir)
    if env_overrides:
        for k, v in env_overrides.items():
            if v is None:
                env.pop(k, None)
            else:
                env[k] = v
    proc = subprocess.run(
        [sys.executable, str(_HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )
    stdout = (proc.stdout or "").strip()
    if stdout:
        try:
            decision = json.loads(stdout.splitlines()[-1])
        except json.JSONDecodeError:
            decision = {"_raw_stdout": stdout}
    else:
        decision = {}
    return proc.returncode, decision, proc.stderr or ""


def _seed_canonical_guard_files(project_dir: Path) -> None:
    """Create the canonical files the guard list points at.

    `_path_matches_canonical_guard` does a `Path.resolve().relative_to`
    against `repo_root`, then fnmatch against the guard globs. The
    files don't need real content — they just need to exist so the
    relative path is computable when the input path is absolute.
    For path strings that are already relative the resolution step is
    skipped (`if p.is_absolute()` branch).
    """
    (project_dir / ".claude").mkdir(parents=True, exist_ok=True)
    (project_dir / ".claude" / "team.md").write_text("team", encoding="utf-8")
    (project_dir / ".claude" / "frontend-team.md").write_text("ft", encoding="utf-8")
    (project_dir / ".claude" / "pitfalls-catalog.yaml").write_text("pf", encoding="utf-8")
    (project_dir / ".claude" / "skills" / "core" / "demo").mkdir(parents=True, exist_ok=True)
    (project_dir / ".claude" / "skills" / "core" / "demo" / "SKILL.md").write_text(
        "skill", encoding="utf-8"
    )
    (project_dir / ".claude" / "hooks").mkdir(parents=True, exist_ok=True)
    (project_dir / ".claude" / "hooks" / "check_canonical_edit.py").write_text(
        "import x", encoding="utf-8"
    )


# ---------------------------------------------------------------------
# 1. TestFailClosedOnUnknownTarget — unknown/malformed target → behaviour
# ---------------------------------------------------------------------


class TestFailClosedOnUnknownTarget(TestEnvContext):
    """Unknown tool_name / unknown path types → allow (out of scope).

    The hook's `_decide()` only acts on `_ALLOWED_CODEX_TOOLS`. Anything
    else (different MCP tool, no tool_name, or no parseable paths) is
    explicitly outside scope and returns `{"decision": "allow"}`. This
    is intentional — the hook is narrow to Codex's two read-only tools.
    """

    def test_unknown_tool_name_allows(self) -> None:
        payload = {
            "tool_name": "mcp__codex__apply_patch",  # NOT in allow-list
            "tool_input": {"path": ".claude/team.md"},
        }
        rc, decision, _ = _invoke_hook(payload, project_dir=self.project_dir)
        self.assertEqual(rc, 0)
        self.assertEqual(decision.get("decision", "allow"), "allow")

    def test_missing_tool_name_allows(self) -> None:
        payload = {"tool_input": {"path": ".claude/team.md"}}
        rc, decision, _ = _invoke_hook(payload, project_dir=self.project_dir)
        self.assertEqual(rc, 0)
        self.assertEqual(decision.get("decision", "allow"), "allow")

    def test_empty_payload_allows(self) -> None:
        rc, decision, _ = _invoke_hook({}, project_dir=self.project_dir)
        self.assertEqual(rc, 0)
        self.assertEqual(decision.get("decision", "allow"), "allow")

    def test_non_codex_tool_name_with_canonical_path_allows(self) -> None:
        """Other MCP/Edit tools have their own guards — this hook stays narrow."""
        payload = {
            "tool_name": "Edit",
            "tool_input": {"file_path": ".claude/team.md"},
        }
        rc, decision, _ = _invoke_hook(payload, project_dir=self.project_dir)
        self.assertEqual(rc, 0)
        self.assertEqual(decision.get("decision", "allow"), "allow")

    def test_codex_tool_with_no_paths_allows(self) -> None:
        """Codex tool but no path-shaped keys → out of scope, allow."""
        payload = {
            "tool_name": "mcp__codex__codex",
            "tool_input": {"prompt": "summarize foo.py", "model": "gpt-5"},
        }
        rc, decision, _ = _invoke_hook(payload, project_dir=self.project_dir)
        self.assertEqual(rc, 0)
        self.assertEqual(decision.get("decision", "allow"), "allow")


# ---------------------------------------------------------------------
# 2. TestKillSwitchEnvVar — CEO_CODEX_FILEWRITE_DISABLE
# ---------------------------------------------------------------------


class TestKillSwitchEnvVar(TestEnvContext):
    """CEO_CODEX_FILEWRITE_DISABLE=1 short-circuits to allow.

    Per R1 S-Sec-7: this kill-switch is SEPARATE from
    `CEO_PAIR_RAIL_DISABLE` so disabling pair-rail review does NOT
    silently disable the filewrite deny-list, and vice-versa.
    """

    def setUp(self) -> None:
        super().setUp()
        _seed_canonical_guard_files(self.project_dir)

    def test_kill_switch_allows_canonical_path(self) -> None:
        payload = {
            "tool_name": "mcp__codex__codex",
            "tool_input": {"path": ".claude/team.md"},
        }
        rc, decision, _ = _invoke_hook(
            payload,
            project_dir=self.project_dir,
            env_overrides={
                "CEO_CODEX_FILEWRITE_DISABLE": "1",
                "CEO_CODEX_FILEWRITE_DRY_RUN": "0",  # explicit prod mode
            },
        )
        self.assertEqual(rc, 0)
        self.assertEqual(decision.get("decision", "allow"), "allow")
        # Kill-switch returns plain allow without systemMessage diagnostic.
        self.assertNotIn("systemMessage", decision)

    def test_kill_switch_unset_canonical_path_blocks_when_dry_run_off(self) -> None:
        """Without kill-switch + DRY_RUN=0, canonical paths must block."""
        payload = {
            "tool_name": "mcp__codex__codex",
            "tool_input": {"path": ".claude/team.md"},
        }
        rc, decision, _ = _invoke_hook(
            payload,
            project_dir=self.project_dir,
            env_overrides={
                "CEO_CODEX_FILEWRITE_DISABLE": None,
                "CEO_CODEX_FILEWRITE_DRY_RUN": "0",
            },
        )
        self.assertEqual(rc, 0)
        self.assertEqual(decision.get("decision"), "block")
        self.assertIn("CODEX-FILEWRITE-BLOCK", decision.get("reason", ""))

    def test_kill_switch_value_zero_does_not_disable(self) -> None:
        """Only literal '1' enables — '0' / '' / 'false' do NOT bypass."""
        for raw in ("0", "", "false", "yes", "  "):
            with self.subTest(value=raw):
                payload = {
                    "tool_name": "mcp__codex__codex",
                    "tool_input": {"path": ".claude/team.md"},
                }
                rc, decision, _ = _invoke_hook(
                    payload,
                    project_dir=self.project_dir,
                    env_overrides={
                        "CEO_CODEX_FILEWRITE_DISABLE": raw,
                        "CEO_CODEX_FILEWRITE_DRY_RUN": "0",
                    },
                )
                self.assertEqual(rc, 0, f"raw={raw!r}")
                self.assertEqual(
                    decision.get("decision"), "block",
                    f"raw={raw!r}: expected block, got {decision}",
                )

    def test_kill_switch_independent_of_pair_rail_disable(self) -> None:
        """Setting CEO_PAIR_RAIL_DISABLE does NOT disable this hook (R1 S-Sec-7)."""
        payload = {
            "tool_name": "mcp__codex__codex",
            "tool_input": {"path": ".claude/team.md"},
        }
        rc, decision, _ = _invoke_hook(
            payload,
            project_dir=self.project_dir,
            env_overrides={
                "CEO_PAIR_RAIL_DISABLE": "1",  # decoy
                "CEO_CODEX_FILEWRITE_DISABLE": None,
                "CEO_CODEX_FILEWRITE_DRY_RUN": "0",
            },
        )
        self.assertEqual(rc, 0)
        self.assertEqual(decision.get("decision"), "block")

    def test_kill_switch_allows_codex_reply_tool_too(self) -> None:
        """Kill-switch covers both mcp__codex__codex and codex-reply."""
        payload = {
            "tool_name": "mcp__codex__codex-reply",
            "tool_input": {"path": ".claude/team.md"},
        }
        rc, decision, _ = _invoke_hook(
            payload,
            project_dir=self.project_dir,
            env_overrides={"CEO_CODEX_FILEWRITE_DISABLE": "1"},
        )
        self.assertEqual(rc, 0)
        self.assertEqual(decision.get("decision", "allow"), "allow")


# ---------------------------------------------------------------------
# 3. TestKillSwitchSentinel — DRY_RUN sentinel allow-path
# ---------------------------------------------------------------------


class TestKillSwitchSentinel(TestEnvContext):
    """DRY_RUN mode (default ON) allows + emits — second kill-switch surface.

    Per Phase 5 ship discipline: until Phase 4-bis green, the hook is
    advisory only. DRY_RUN=1 forces canonical matches to return allow
    with a diagnostic `systemMessage`. This is the "sentinel" surface
    for opt-in/opt-out (DRY_RUN=0 flips to enforcing).
    """

    def setUp(self) -> None:
        super().setUp()
        _seed_canonical_guard_files(self.project_dir)

    def test_dry_run_default_allows_with_diagnostic(self) -> None:
        """DRY_RUN unset → default '1' → allow + systemMessage on match."""
        payload = {
            "tool_name": "mcp__codex__codex",
            "tool_input": {"path": ".claude/team.md"},
        }
        rc, decision, _ = _invoke_hook(
            payload,
            project_dir=self.project_dir,
            env_overrides={
                "CEO_CODEX_FILEWRITE_DRY_RUN": None,
                "CEO_CODEX_FILEWRITE_DISABLE": None,
            },
        )
        self.assertEqual(rc, 0)
        self.assertEqual(decision.get("decision", "allow"), "allow")
        self.assertIn("DRY_RUN", decision.get("systemMessage", ""))
        self.assertIn(".claude/team.md", decision.get("systemMessage", ""))

    def test_dry_run_explicit_one_allows(self) -> None:
        payload = {
            "tool_name": "mcp__codex__codex",
            "tool_input": {"path": ".claude/team.md"},
        }
        rc, decision, _ = _invoke_hook(
            payload,
            project_dir=self.project_dir,
            env_overrides={"CEO_CODEX_FILEWRITE_DRY_RUN": "1"},
        )
        self.assertEqual(rc, 0)
        self.assertEqual(decision.get("decision", "allow"), "allow")
        self.assertIn("DRY_RUN", decision.get("systemMessage", ""))

    def test_dry_run_zero_blocks(self) -> None:
        """Explicit DRY_RUN=0 → production mode → block on canonical match."""
        payload = {
            "tool_name": "mcp__codex__codex",
            "tool_input": {"path": ".claude/team.md"},
        }
        rc, decision, _ = _invoke_hook(
            payload,
            project_dir=self.project_dir,
            env_overrides={"CEO_CODEX_FILEWRITE_DRY_RUN": "0"},
        )
        self.assertEqual(rc, 0)
        self.assertEqual(decision.get("decision"), "block")

    def test_dry_run_only_value_one_is_truthy(self) -> None:
        """Truthy values OTHER than '1' do not enable DRY_RUN."""
        for raw in ("0", "true", "yes", "2"):
            with self.subTest(value=raw):
                payload = {
                    "tool_name": "mcp__codex__codex",
                    "tool_input": {"path": ".claude/team.md"},
                }
                rc, decision, _ = _invoke_hook(
                    payload,
                    project_dir=self.project_dir,
                    env_overrides={"CEO_CODEX_FILEWRITE_DRY_RUN": raw},
                )
                self.assertEqual(rc, 0)
                self.assertEqual(
                    decision.get("decision"), "block",
                    f"raw={raw!r}: only '1' should enable DRY_RUN",
                )

    def test_dry_run_systemmessage_mentions_kill_switch(self) -> None:
        """DRY_RUN diagnostic mentions the env-var name for Phase 4-bis flip."""
        payload = {
            "tool_name": "mcp__codex__codex",
            "tool_input": {"path": ".claude/team.md"},
        }
        rc, decision, _ = _invoke_hook(
            payload,
            project_dir=self.project_dir,
            env_overrides={"CEO_CODEX_FILEWRITE_DRY_RUN": "1"},
        )
        self.assertEqual(rc, 0)
        msg = decision.get("systemMessage", "")
        # Hook references the operational flip env-var by name.
        self.assertIn("CEO_CODEX_FILEWRITE_DRY_RUN", msg)


# ---------------------------------------------------------------------
# 4. TestApplyPatchTargetExtraction — MCP envelope path-key parsing
# ---------------------------------------------------------------------


class TestApplyPatchTargetExtraction(TestEnvContext):
    """Verify the 9 path-key heuristics from _MCP_WRITE_PATH_KEYS.

    The extractor mirrors `check_canonical_edit._extract_mcp_target_paths`.
    Any of {path, file_path, target_path, file, filename, dest, destination,
    target, uri} reaches the canonical guard.
    """

    PATH_KEYS = (
        "path", "file_path", "target_path", "file",
        "filename", "dest", "destination", "target", "uri",
    )

    def setUp(self) -> None:
        super().setUp()
        _seed_canonical_guard_files(self.project_dir)

    def test_each_path_key_extracts_canonical_target(self) -> None:
        """Every key in _MCP_WRITE_PATH_KEYS should reach the guard."""
        for key in self.PATH_KEYS:
            with self.subTest(key=key):
                payload = {
                    "tool_name": "mcp__codex__codex",
                    "tool_input": {key: ".claude/team.md"},
                }
                rc, decision, _ = _invoke_hook(
                    payload,
                    project_dir=self.project_dir,
                    env_overrides={"CEO_CODEX_FILEWRITE_DRY_RUN": "0"},
                )
                self.assertEqual(rc, 0)
                self.assertEqual(
                    decision.get("decision"), "block",
                    f"key={key!r}: expected canonical guard hit + block",
                )

    def test_unknown_key_not_extracted(self) -> None:
        """Random key name (not in the path-key list) → no extraction → allow."""
        payload = {
            "tool_name": "mcp__codex__codex",
            "tool_input": {"random_field": ".claude/team.md"},
        }
        rc, decision, _ = _invoke_hook(
            payload,
            project_dir=self.project_dir,
            env_overrides={"CEO_CODEX_FILEWRITE_DRY_RUN": "0"},
        )
        self.assertEqual(rc, 0)
        self.assertEqual(decision.get("decision", "allow"), "allow")

    def test_non_string_path_value_skipped(self) -> None:
        """If path value is not str (e.g. int/dict/None) it is skipped."""
        for value in (123, None, {"nested": "x"}, ["list"]):
            with self.subTest(value=value):
                payload = {
                    "tool_name": "mcp__codex__codex",
                    "tool_input": {"path": value},
                }
                rc, decision, _ = _invoke_hook(
                    payload,
                    project_dir=self.project_dir,
                    env_overrides={"CEO_CODEX_FILEWRITE_DRY_RUN": "0"},
                )
                self.assertEqual(rc, 0)
                self.assertEqual(decision.get("decision", "allow"), "allow")

    def test_empty_string_path_skipped(self) -> None:
        """Empty string path is falsy and skipped per `if isinstance(...) and value`."""
        payload = {
            "tool_name": "mcp__codex__codex",
            "tool_input": {"path": ""},
        }
        rc, decision, _ = _invoke_hook(
            payload,
            project_dir=self.project_dir,
            env_overrides={"CEO_CODEX_FILEWRITE_DRY_RUN": "0"},
        )
        self.assertEqual(rc, 0)
        self.assertEqual(decision.get("decision", "allow"), "allow")

    def test_overlong_path_value_skipped(self) -> None:
        """Paths longer than _PATH_LEN_CAP (4096) are skipped — DoS guard."""
        long_path = ".claude/team.md" + ("/" + "x" * 50) * 100  # > 4096 chars
        self.assertGreater(len(long_path), 4096)
        payload = {
            "tool_name": "mcp__codex__codex",
            "tool_input": {"path": long_path},
        }
        rc, decision, _ = _invoke_hook(
            payload,
            project_dir=self.project_dir,
            env_overrides={"CEO_CODEX_FILEWRITE_DRY_RUN": "0"},
        )
        self.assertEqual(rc, 0)
        # Long path skipped → no extraction → allow.
        self.assertEqual(decision.get("decision", "allow"), "allow")

    def test_multiple_keys_first_canonical_match_blocks(self) -> None:
        """If any of the extracted paths is canonical → block, even mixed."""
        payload = {
            "tool_name": "mcp__codex__codex",
            "tool_input": {
                "path": "safe/some-scratch.txt",
                "file_path": ".claude/team.md",  # canonical
            },
        }
        rc, decision, _ = _invoke_hook(
            payload,
            project_dir=self.project_dir,
            env_overrides={"CEO_CODEX_FILEWRITE_DRY_RUN": "0"},
        )
        self.assertEqual(rc, 0)
        self.assertEqual(decision.get("decision"), "block")


# ---------------------------------------------------------------------
# 5. TestCanonicalPathDenial — guarded paths → block/DRY_RUN-emit
# ---------------------------------------------------------------------


class TestCanonicalPathDenial(TestEnvContext):
    """Canonical-guarded paths get blocked under DRY_RUN=0.

    Imports `_CANONICAL_GUARDS` from `check_canonical_edit` at runtime
    (R1 C1 single source of truth). Exercised by routing several
    representative canonical paths through the hook.
    """

    def setUp(self) -> None:
        super().setUp()
        _seed_canonical_guard_files(self.project_dir)

    def test_team_md_blocked(self) -> None:
        payload = {
            "tool_name": "mcp__codex__codex",
            "tool_input": {"path": ".claude/team.md"},
        }
        rc, decision, _ = _invoke_hook(
            payload,
            project_dir=self.project_dir,
            env_overrides={"CEO_CODEX_FILEWRITE_DRY_RUN": "0"},
        )
        self.assertEqual(rc, 0)
        self.assertEqual(decision.get("decision"), "block")
        self.assertIn(".claude/team.md", decision.get("reason", ""))

    def test_frontend_team_md_blocked(self) -> None:
        payload = {
            "tool_name": "mcp__codex__codex",
            "tool_input": {"path": ".claude/frontend-team.md"},
        }
        rc, decision, _ = _invoke_hook(
            payload,
            project_dir=self.project_dir,
            env_overrides={"CEO_CODEX_FILEWRITE_DRY_RUN": "0"},
        )
        self.assertEqual(rc, 0)
        self.assertEqual(decision.get("decision"), "block")

    def test_skill_md_core_blocked(self) -> None:
        payload = {
            "tool_name": "mcp__codex__codex",
            "tool_input": {"path": ".claude/skills/core/demo/SKILL.md"},
        }
        rc, decision, _ = _invoke_hook(
            payload,
            project_dir=self.project_dir,
            env_overrides={"CEO_CODEX_FILEWRITE_DRY_RUN": "0"},
        )
        self.assertEqual(rc, 0)
        self.assertEqual(decision.get("decision"), "block")

    def test_hook_source_file_blocked(self) -> None:
        """`.claude/hooks/*.py` is in the guard list — Codex must not edit."""
        payload = {
            "tool_name": "mcp__codex__codex",
            "tool_input": {"path": ".claude/hooks/check_canonical_edit.py"},
        }
        rc, decision, _ = _invoke_hook(
            payload,
            project_dir=self.project_dir,
            env_overrides={"CEO_CODEX_FILEWRITE_DRY_RUN": "0"},
        )
        self.assertEqual(rc, 0)
        self.assertEqual(decision.get("decision"), "block")

    def test_pitfalls_catalog_blocked(self) -> None:
        payload = {
            "tool_name": "mcp__codex__codex",
            "tool_input": {"path": ".claude/pitfalls-catalog.yaml"},
        }
        rc, decision, _ = _invoke_hook(
            payload,
            project_dir=self.project_dir,
            env_overrides={"CEO_CODEX_FILEWRITE_DRY_RUN": "0"},
        )
        self.assertEqual(rc, 0)
        self.assertEqual(decision.get("decision"), "block")

    def test_block_reason_carries_kill_switch_hint(self) -> None:
        """Block reason exposes CEO_CODEX_FILEWRITE_DISABLE as the escape hatch."""
        payload = {
            "tool_name": "mcp__codex__codex",
            "tool_input": {"path": ".claude/team.md"},
        }
        rc, decision, _ = _invoke_hook(
            payload,
            project_dir=self.project_dir,
            env_overrides={"CEO_CODEX_FILEWRITE_DRY_RUN": "0"},
        )
        self.assertEqual(rc, 0)
        self.assertIn("CEO_CODEX_FILEWRITE_DISABLE", decision.get("reason", ""))


# ---------------------------------------------------------------------
# 6. TestAllowlistedScratchAllow — scratch + non-canonical paths
# ---------------------------------------------------------------------


class TestAllowlistedScratchAllow(TestEnvContext):
    """Non-canonical scratch paths are allowed (no guard match)."""

    def setUp(self) -> None:
        super().setUp()
        _seed_canonical_guard_files(self.project_dir)

    def test_plan_staging_allowed(self) -> None:
        """`.claude/plans/PLAN-X/staging/...` is NOT in the guard list."""
        payload = {
            "tool_name": "mcp__codex__codex",
            "tool_input": {"path": ".claude/plans/PLAN-085/staging/draft.md"},
        }
        rc, decision, _ = _invoke_hook(
            payload,
            project_dir=self.project_dir,
            env_overrides={"CEO_CODEX_FILEWRITE_DRY_RUN": "0"},
        )
        self.assertEqual(rc, 0)
        self.assertEqual(decision.get("decision", "allow"), "allow")

    def test_tmp_path_allowed(self) -> None:
        payload = {
            "tool_name": "mcp__codex__codex",
            "tool_input": {"path": "/tmp/foo.txt"},
        }
        rc, decision, _ = _invoke_hook(
            payload,
            project_dir=self.project_dir,
            env_overrides={"CEO_CODEX_FILEWRITE_DRY_RUN": "0"},
        )
        self.assertEqual(rc, 0)
        self.assertEqual(decision.get("decision", "allow"), "allow")

    def test_source_under_unrelated_dir_allowed(self) -> None:
        payload = {
            "tool_name": "mcp__codex__codex",
            "tool_input": {"path": "src/some_module.py"},
        }
        rc, decision, _ = _invoke_hook(
            payload,
            project_dir=self.project_dir,
            env_overrides={"CEO_CODEX_FILEWRITE_DRY_RUN": "0"},
        )
        self.assertEqual(rc, 0)
        self.assertEqual(decision.get("decision", "allow"), "allow")

    def test_path_outside_repo_root_allowed(self) -> None:
        """Absolute path outside repo root → ValueError on relative_to → allow."""
        with tempfile.TemporaryDirectory() as outside:
            payload = {
                "tool_name": "mcp__codex__codex",
                "tool_input": {"path": str(Path(outside) / "anywhere.md")},
            }
            rc, decision, _ = _invoke_hook(
                payload,
                project_dir=self.project_dir,
                env_overrides={"CEO_CODEX_FILEWRITE_DRY_RUN": "0"},
            )
            self.assertEqual(rc, 0)
            self.assertEqual(decision.get("decision", "allow"), "allow")

    def test_test_directory_allowed(self) -> None:
        """`.claude/hooks/tests/...` is NOT canonical (single-segment glob)."""
        payload = {
            "tool_name": "mcp__codex__codex",
            "tool_input": {"path": ".claude/hooks/tests/test_foo.py"},
        }
        rc, decision, _ = _invoke_hook(
            payload,
            project_dir=self.project_dir,
            env_overrides={"CEO_CODEX_FILEWRITE_DRY_RUN": "0"},
        )
        self.assertEqual(rc, 0)
        self.assertEqual(decision.get("decision", "allow"), "allow")


# ---------------------------------------------------------------------
# 7. TestMalformedToolInputFailClosed — malformed stdin → spec allow
# ---------------------------------------------------------------------


class TestMalformedToolInputFailClosed(TestEnvContext):
    """Malformed stdin — CURRENT Phase 5 fail-OPEN; Phase 6 carryover documented.

    **PLAN-085 R2 Codex iter-1 P0:F finding (contract drift)**: the class
    name + plan §7 inventory says ``FailClosed`` but the hook in Phase 5
    is intentionally fail-OPEN on parse error (``check_codex_filewrite.py``
    `main()` lines 314-321 explicit docstring). These tests PIN the
    current Phase 5 behaviour and document the deviation; the Phase 6
    hook edit (flip parse-error path to fail-CLOSED in production —
    `CEO_CODEX_FILEWRITE_DRY_RUN=0`) is canonical-guarded and **DEFERRED
    to PLAN-086 / v1.20.0** per anti-churn doctrine (ADR-115
    maintenance-mode).

    When Phase 6 hook edit lands:
    1. Flip `check_codex_filewrite.py:314-321` from `allow` to `block` +
       audit-emit `pair_rail_filewrite_failclosed_on_error` when
       `CEO_CODEX_FILEWRITE_DRY_RUN=0`.
    2. Update the 6 assertions below from `"allow"` to `"block"`.
    3. Drop this docstring's Phase 5 carryover note.

    Until then, the class name is INTENTIONAL alignment with PLAN-085 §7
    inventory; the assertions are INTENTIONAL alignment with Phase 5
    runtime reality.
    """

    def test_unparseable_stdin_allows(self) -> None:
        """Raw garbage stdin → JSONDecodeError → allow (Phase 5 spec)."""
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(self.project_dir)}
        env["CEO_CODEX_FILEWRITE_DRY_RUN"] = "0"
        proc = subprocess.run(
            [sys.executable, str(_HOOK)],
            input="not valid json {",
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        self.assertEqual(proc.returncode, 0)
        decision = json.loads(proc.stdout.strip().splitlines()[-1])
        self.assertEqual(decision.get("decision", "allow"), "allow")

    def test_top_level_array_not_dict_allows(self) -> None:
        """JSON array (not dict) → `isinstance(event, dict)` check → allow."""
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(self.project_dir)}
        env["CEO_CODEX_FILEWRITE_DRY_RUN"] = "0"
        proc = subprocess.run(
            [sys.executable, str(_HOOK)],
            input='["array", "not", "dict"]',
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        self.assertEqual(proc.returncode, 0)
        decision = json.loads(proc.stdout.strip().splitlines()[-1])
        self.assertEqual(decision.get("decision", "allow"), "allow")

    def test_top_level_string_allows(self) -> None:
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(self.project_dir)}
        env["CEO_CODEX_FILEWRITE_DRY_RUN"] = "0"
        proc = subprocess.run(
            [sys.executable, str(_HOOK)],
            input='"just a string"',
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        self.assertEqual(proc.returncode, 0)
        decision = json.loads(proc.stdout.strip().splitlines()[-1])
        self.assertEqual(decision.get("decision", "allow"), "allow")

    def test_empty_stdin_allows(self) -> None:
        """Empty stdin → defaults to '{}' → allow."""
        env = {**os.environ, "CLAUDE_PROJECT_DIR": str(self.project_dir)}
        env["CEO_CODEX_FILEWRITE_DRY_RUN"] = "0"
        proc = subprocess.run(
            [sys.executable, str(_HOOK)],
            input="",
            capture_output=True,
            text=True,
            timeout=10,
            env=env,
        )
        self.assertEqual(proc.returncode, 0)
        decision = json.loads(proc.stdout.strip().splitlines()[-1])
        self.assertEqual(decision.get("decision", "allow"), "allow")

    def test_tool_input_not_dict_allows(self) -> None:
        """tool_input as string (instead of dict) → no paths extracted → allow."""
        _seed_canonical_guard_files(self.project_dir)
        payload = {
            "tool_name": "mcp__codex__codex",
            "tool_input": "not a dict",
        }
        rc, decision, _ = _invoke_hook(
            payload,
            project_dir=self.project_dir,
            env_overrides={"CEO_CODEX_FILEWRITE_DRY_RUN": "0"},
        )
        self.assertEqual(rc, 0)
        self.assertEqual(decision.get("decision", "allow"), "allow")

    def test_null_tool_input_allows(self) -> None:
        payload = {"tool_name": "mcp__codex__codex", "tool_input": None}
        rc, decision, _ = _invoke_hook(
            payload,
            project_dir=self.project_dir,
            env_overrides={"CEO_CODEX_FILEWRITE_DRY_RUN": "0"},
        )
        self.assertEqual(rc, 0)
        self.assertEqual(decision.get("decision", "allow"), "allow")


# ---------------------------------------------------------------------
# 8. TestAuditEmitOnDeny — audit sink contains hash prefix
# ---------------------------------------------------------------------


class TestAuditEmitOnDeny(TestEnvContext):
    """Every deny path emits an audit record to CEO_CODEX_FILEWRITE_AUDIT_SINK.

    The hook writes one JSON line per match to the sink file. Record
    contains:
      - action: "codex_writeguard_block"
      - target_path_hash_prefix: 16-hex SHA-256 prefix (LLM06 side-channel guard)
      - matched_glob: glob pattern that matched (or "_ERROR_FAIL_CLOSED")
      - dry_run: bool

    Critically the raw target_path is NOT in the emit (only its hash) —
    asserts the side-channel guard works.
    """

    def setUp(self) -> None:
        super().setUp()
        _seed_canonical_guard_files(self.project_dir)
        self.sink_path = self.project_dir / "audit-sink.jsonl"

    def _read_sink(self) -> list:
        if not self.sink_path.exists():
            return []
        lines = self.sink_path.read_text(encoding="utf-8").strip().splitlines()
        return [json.loads(ln) for ln in lines if ln.strip()]

    def test_block_emits_audit_record(self) -> None:
        payload = {
            "tool_name": "mcp__codex__codex",
            "tool_input": {"path": ".claude/team.md"},
        }
        rc, decision, _ = _invoke_hook(
            payload,
            project_dir=self.project_dir,
            env_overrides={
                "CEO_CODEX_FILEWRITE_DRY_RUN": "0",
                "CEO_CODEX_FILEWRITE_AUDIT_SINK": str(self.sink_path),
            },
        )
        self.assertEqual(rc, 0)
        self.assertEqual(decision.get("decision"), "block")
        records = self._read_sink()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["action"], "codex_writeguard_block")
        self.assertEqual(records[0]["matched_glob"], ".claude/team.md")
        self.assertEqual(records[0]["dry_run"], False)

    def test_audit_record_hashes_path_not_raw(self) -> None:
        """Raw target path MUST NOT appear in the audit record (LLM06).

        Uses a wildcard-matched canonical path so the assertion is
        meaningful: matched_glob is `.claude/skills/core/*/SKILL.md`
        while the actual path is `.claude/skills/core/demo/SKILL.md` —
        the `demo` segment must NOT surface in the record.
        """
        payload = {
            "tool_name": "mcp__codex__codex",
            "tool_input": {"path": ".claude/skills/core/demo/SKILL.md"},
        }
        _invoke_hook(
            payload,
            project_dir=self.project_dir,
            env_overrides={
                "CEO_CODEX_FILEWRITE_DRY_RUN": "0",
                "CEO_CODEX_FILEWRITE_AUDIT_SINK": str(self.sink_path),
            },
        )
        records = self._read_sink()
        self.assertEqual(len(records), 1)
        rec = records[0]
        # Hash prefix is 16 hex chars
        self.assertIn("target_path_hash_prefix", rec)
        self.assertEqual(len(rec["target_path_hash_prefix"]), 16)
        # The specific path segment ("demo") that distinguishes this
        # particular path from its glob MUST NOT appear in the record.
        serialized = json.dumps(rec)
        self.assertNotIn("demo", serialized,
            "wildcard-matched segment leaked into audit record (LLM06 side-channel)")

    def test_dry_run_emit_marks_dry_run_true(self) -> None:
        payload = {
            "tool_name": "mcp__codex__codex",
            "tool_input": {"path": ".claude/team.md"},
        }
        rc, decision, _ = _invoke_hook(
            payload,
            project_dir=self.project_dir,
            env_overrides={
                "CEO_CODEX_FILEWRITE_DRY_RUN": "1",
                "CEO_CODEX_FILEWRITE_AUDIT_SINK": str(self.sink_path),
            },
        )
        self.assertEqual(rc, 0)
        self.assertEqual(decision.get("decision", "allow"), "allow")
        records = self._read_sink()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["dry_run"], True)
        self.assertEqual(records[0]["action"], "codex_writeguard_block")

    def test_no_sink_set_skips_emit_without_crash(self) -> None:
        """No CEO_CODEX_FILEWRITE_AUDIT_SINK → best-effort skip, no crash."""
        payload = {
            "tool_name": "mcp__codex__codex",
            "tool_input": {"path": ".claude/team.md"},
        }
        rc, decision, _ = _invoke_hook(
            payload,
            project_dir=self.project_dir,
            env_overrides={
                "CEO_CODEX_FILEWRITE_DRY_RUN": "0",
                "CEO_CODEX_FILEWRITE_AUDIT_SINK": None,
            },
        )
        self.assertEqual(rc, 0)
        self.assertEqual(decision.get("decision"), "block")
        # No sink → no file created
        self.assertFalse(self.sink_path.exists())

    def test_allow_paths_do_not_emit(self) -> None:
        """Non-canonical paths → no audit record (decision is allow without emit)."""
        payload = {
            "tool_name": "mcp__codex__codex",
            "tool_input": {"path": "src/safe.py"},
        }
        rc, decision, _ = _invoke_hook(
            payload,
            project_dir=self.project_dir,
            env_overrides={
                "CEO_CODEX_FILEWRITE_DRY_RUN": "0",
                "CEO_CODEX_FILEWRITE_AUDIT_SINK": str(self.sink_path),
            },
        )
        self.assertEqual(rc, 0)
        self.assertEqual(decision.get("decision", "allow"), "allow")
        self.assertEqual(self._read_sink(), [])

    def test_glob_truncation_at_80_chars(self) -> None:
        """matched_glob is truncated to 80 chars to bound record size."""
        payload = {
            "tool_name": "mcp__codex__codex",
            "tool_input": {"path": ".claude/hooks/check_canonical_edit.py"},
        }
        _invoke_hook(
            payload,
            project_dir=self.project_dir,
            env_overrides={
                "CEO_CODEX_FILEWRITE_DRY_RUN": "0",
                "CEO_CODEX_FILEWRITE_AUDIT_SINK": str(self.sink_path),
            },
        )
        records = self._read_sink()
        self.assertEqual(len(records), 1)
        self.assertLessEqual(len(records[0]["matched_glob"]), 80)


if __name__ == "__main__":
    unittest.main()
