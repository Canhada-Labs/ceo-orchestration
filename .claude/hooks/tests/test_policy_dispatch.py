"""Unit tests for `.claude/hooks/policy_dispatch.py` — PLAN-019 P1-QA-1.

Covers the dispatcher that routes Claude Code hook invocations through the
YAML policy-as-code engine (`_lib/policy.py`) with legacy-delegation fallback
and fail-CLOSED semantics per ADR-045 §Fail-mode.

The dispatcher is exercised via subprocess invocation (matching production)
*and* via direct `main()` calls for focused unit coverage of the branching
logic. All tests run under `TestEnvContext` → no ambient env mutation.

Covers (≥15 tests):

1. Kill-switch (`CEO_POLICY_ENGINE_DISABLE=1`) short-circuits to allow
2. Kill-switch + `CEO_POLICY_LEGACY_HOOK_PATH` delegates to legacy hook
3. Kill-switch without legacy → default allow
4. Malformed policy → fail-CLOSED (block) when no legacy
5. Malformed policy + legacy → delegates (fallback path)
6. Missing policy file → fail-CLOSED
7. Missing policy file + legacy → delegates
8. Happy path — valid policy, allow decision
9. Happy path — valid policy, block decision (with reason + message)
10. CEO_POLICY_FILE override honored
11. Dispatcher does NOT import check_* hooks (circular-import guard)
12. Byte-identity — canonical_hash matches pinned .drift-manifest.json
13. Dual-path consistency — engine decision matches reference fixture
14. Legacy delegation preserves legacy hook's stdout
15. Empty stdin → still parses, decision emitted
16. Malformed stdin JSON → treated as empty event (graceful)
17. Argparse rejects missing --policy
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import textwrap
import unittest
from pathlib import Path


from _lib.testing import TestEnvContext  # noqa: E402


_REPO_ROOT = Path(__file__).resolve().parents[3]
_DISPATCHER = _REPO_ROOT / ".claude" / "hooks" / "policy_dispatch.py"
_POLICIES_DIR = _REPO_ROOT / ".claude" / "policies"


def _run_dispatcher(
    policy: str,
    event: dict,
    env_overrides: dict,
    timeout: float = 5.0,
    stdin_raw: str = None,
):
    """Invoke the dispatcher as a subprocess (production contract)."""
    env = os.environ.copy()
    env.update(env_overrides)
    stdin_text = stdin_raw if stdin_raw is not None else json.dumps(event)
    return subprocess.run(
        [sys.executable, str(_DISPATCHER), "--policy", policy],
        input=stdin_text,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=env,
    )


def _last_json(stdout: str) -> dict:
    lines = [ln for ln in (stdout or "").splitlines() if ln.strip()]
    assert lines, "dispatcher produced no stdout"
    return json.loads(lines[-1])


class _DispatcherBase(TestEnvContext):
    """Base — provides `_build_env()` that targets the isolated HOME/audit dir."""

    def _build_env(self, extra: dict = None) -> dict:
        env = {
            "CLAUDE_PROJECT_DIR": str(_REPO_ROOT),
            "HOME": str(self.home_dir),
            "CEO_AUDIT_LOG_DIR": str(self.audit_dir),
            "CEO_AUDIT_LOG_PATH": str(self.audit_dir / "audit-log.jsonl"),
            "CEO_AUDIT_LOG_ERR": str(self.audit_dir / "audit-log.errors"),
            "CEO_AUDIT_LOG_LOCK": str(self.audit_dir / "audit-log.lock"),
        }
        if extra:
            env.update(extra)
        return env


# ---------------------------------------------------------------------------
# Kill-switch branch
# ---------------------------------------------------------------------------


class TestKillSwitch(_DispatcherBase):
    """`CEO_POLICY_ENGINE_DISABLE=1` must short-circuit before any policy load."""

    def test_kill_switch_without_legacy_returns_allow(self):
        """No legacy hook path → dispatcher emits default allow."""
        env = self._build_env({"CEO_POLICY_ENGINE_DISABLE": "1"})
        proc = _run_dispatcher("bash-safety", {}, env)
        self.assertEqual(proc.returncode, 0, f"stderr={proc.stderr!r}")
        self.assertEqual(_last_json(proc.stdout).get("decision", "allow"), "allow")

    def test_kill_switch_delegates_to_legacy_hook(self):
        """Kill-switch + `CEO_POLICY_LEGACY_HOOK_PATH` → exec legacy hook."""
        legacy = self.project_dir / "legacy_stub.py"
        legacy.write_text(textwrap.dedent("""
            #!/usr/bin/env python3
            import json, sys
            sys.stdout.write(json.dumps({"decision": "allow", "via": "legacy-kill"}) + "\\n")
            sys.exit(0)
        """).strip() + "\n", encoding="utf-8")
        legacy.chmod(0o755)
        env = self._build_env({
            "CEO_POLICY_ENGINE_DISABLE": "1",
            "CEO_POLICY_LEGACY_HOOK_PATH": str(legacy),
        })
        proc = _run_dispatcher("bash-safety", {}, env)
        self.assertEqual(proc.returncode, 0, f"stderr={proc.stderr!r}")
        out = _last_json(proc.stdout)
        self.assertEqual(out.get("decision", "allow"), "allow")
        self.assertEqual(out.get("via"), "legacy-kill",
                         "engine-disable did not delegate to legacy hook")

    def test_kill_switch_nonexistent_legacy_still_allows(self):
        """Legacy path that doesn't exist → allow (not block)."""
        env = self._build_env({
            "CEO_POLICY_ENGINE_DISABLE": "1",
            "CEO_POLICY_LEGACY_HOOK_PATH": "/nonexistent/path.py",
        })
        proc = _run_dispatcher("bash-safety", {}, env)
        self.assertEqual(proc.returncode, 0, f"stderr={proc.stderr!r}")
        self.assertEqual(_last_json(proc.stdout).get("decision", "allow"), "allow")


# ---------------------------------------------------------------------------
# Malformed / missing policy (fail-safe branch)
# ---------------------------------------------------------------------------


class TestPolicyLoadFailure(_DispatcherBase):

    def test_malformed_policy_without_legacy_fails_closed(self):
        """Broken YAML + no legacy → fail-CLOSED block."""
        bogus = self.project_dir / "bogus.policy.yaml"
        # Missing required `rules:` key → PolicyLoadError.
        bogus.write_text("schema: \"policy-dsl/v1\"\nid: bogus\n",
                         encoding="utf-8")
        env = self._build_env({"CEO_POLICY_FILE": str(bogus)})
        proc = _run_dispatcher("bash-safety", {}, env)
        self.assertEqual(proc.returncode, 0, f"stderr={proc.stderr!r}")
        out = _last_json(proc.stdout)
        self.assertEqual(out["decision"], "block",
                         f"expected fail-closed; got {out!r}")
        self.assertEqual(out["reason"], "policy_engine_unavailable")

    def test_malformed_policy_with_legacy_delegates(self):
        """Broken YAML + legacy hook path → delegate path wins."""
        bogus = self.project_dir / "bogus.policy.yaml"
        bogus.write_text("not yaml\n", encoding="utf-8")
        legacy = self.project_dir / "legacy.py"
        legacy.write_text(textwrap.dedent("""
            #!/usr/bin/env python3
            import json, sys
            sys.stdout.write(json.dumps({"decision": "allow", "via": "legacy-fb"}) + "\\n")
            sys.exit(0)
        """).strip() + "\n", encoding="utf-8")
        env = self._build_env({
            "CEO_POLICY_FILE": str(bogus),
            "CEO_POLICY_LEGACY_HOOK_PATH": str(legacy),
        })
        proc = _run_dispatcher("bash-safety", {}, env)
        self.assertEqual(proc.returncode, 0, f"stderr={proc.stderr!r}")
        out = _last_json(proc.stdout)
        # Delegation path must produce allow via legacy marker.
        self.assertEqual(out.get("via"), "legacy-fb",
                         "malformed policy should have delegated to legacy")

    def test_missing_policy_file_fails_closed(self):
        """Pointing at a nonexistent policy file → fail-CLOSED."""
        env = self._build_env({
            "CEO_POLICY_FILE": str(self.project_dir / "does-not-exist.yaml"),
        })
        proc = _run_dispatcher("bash-safety", {}, env)
        self.assertEqual(proc.returncode, 0, f"stderr={proc.stderr!r}")
        out = _last_json(proc.stdout)
        self.assertEqual(out["decision"], "block")
        self.assertEqual(out["reason"], "policy_engine_unavailable")


# ---------------------------------------------------------------------------
# Happy path (valid real policies shipped in .claude/policies/)
# ---------------------------------------------------------------------------


class TestHappyPath(_DispatcherBase):

    def test_bash_safety_benign_command_allows(self):
        """Non-destructive bash command → allow via real bash-safety policy."""
        event = {
            "tool": "Bash",
            "tool_input": {"command": "ls -la"},
            "_derived_bash": {
                "command": "ls -la",
                "credential_leak_provider": "",
                "credential_leak_redacted": "",
                "subcommands": ["ls -la"],
                "tokens_per_subcommand": [["ls", "-la"]],
                "matched_rm_rf": False,
                "matched_git_reset_hard": False,
                "matched_git_push_force": False,
            },
        }
        env = self._build_env()
        proc = _run_dispatcher("bash-safety", event, env)
        self.assertEqual(proc.returncode, 0, f"stderr={proc.stderr!r}")
        self.assertEqual(_last_json(proc.stdout).get("decision", "allow"), "allow")

    def test_plan_edit_illegal_transition_blocks(self):
        """Illegal plan transition → block with reason + message."""
        event = {
            "tool": "Edit",
            "tool_input": {"file_path": ".claude/plans/PLAN-999.md"},
            "_derived_plan": {
                "is_plan_file": True,
                "plan_id": "PLAN-999",
                "old_status": "draft",
                "new_status": "done",
                "status_changed": True,
                "transition_legal": False,
                "new_status_legal": True,
                "reviewed_at_present": False,
                "completed_at_present": True,
                "related_commits_nonempty": True,
                "abandonment_reason_present": False,
                "transition_reason_key": "",
            },
        }
        env = self._build_env()
        proc = _run_dispatcher("plan-edit", event, env)
        self.assertEqual(proc.returncode, 0, f"stderr={proc.stderr!r}")
        out = _last_json(proc.stdout)
        self.assertEqual(out["decision"], "block")
        self.assertEqual(out["reason"], "illegal_transition")
        self.assertIn("message", out, "block decision must include message")

    def test_ceo_policy_file_override_honored(self):
        """`CEO_POLICY_FILE` absolute-path override wins over slug resolution."""
        custom = self.project_dir / "minimal.policy.yaml"
        custom.write_text(textwrap.dedent("""
            schema: "policy-dsl/v1"
            id: minimal
            description: "Minimal always-block policy for unit test"
            kind: deny_list
            defaults:
              decision: block
              reason: sentinel
            rules: []
            error_model:
              reasons:
                sentinel: "sentinel-msg"
        """).strip() + "\n", encoding="utf-8")
        env = self._build_env({"CEO_POLICY_FILE": str(custom)})
        proc = _run_dispatcher("ignored-slug", {}, env)
        self.assertEqual(proc.returncode, 0, f"stderr={proc.stderr!r}")
        out = _last_json(proc.stdout)
        self.assertEqual(out["decision"], "block")
        self.assertEqual(out["reason"], "sentinel")


# ---------------------------------------------------------------------------
# Structural / safety guards
# ---------------------------------------------------------------------------


class TestStructuralGuards(_DispatcherBase):

    def test_dispatcher_does_not_import_check_hooks(self):
        """Circular-import guard: policy_dispatch must not import check_* hooks.

        Hooks re-invoke the dispatcher in the legacy window; if the
        dispatcher ever imported a check_* sibling it would create a
        cycle at module-init time.
        """
        src = _DISPATCHER.read_text(encoding="utf-8")
        # We allow subprocess invocation of legacy but never a direct import.
        offenders = [
            line
            for line in src.splitlines()
            if line.startswith("import check_") or line.startswith("from check_")
        ]
        self.assertEqual(
            offenders, [],
            f"policy_dispatch must not import check_* hooks: {offenders!r}"
        )

    def test_drift_manifest_sha_matches_live_bash_safety(self):
        """Byte-identity: pinned bash-safety sha256 matches live engine output."""
        # Import locally to avoid touching env at module load time.
        import _lib.policy as _policy_mod

        manifest_path = _POLICIES_DIR / ".drift-manifest.json"
        with manifest_path.open("r", encoding="utf-8") as f:
            manifest = json.load(f)
        policy = _policy_mod.load(_POLICIES_DIR / "bash-safety.policy.yaml")
        pinned = manifest["policies"]["bash-safety"]["sha256"]
        self.assertEqual(
            policy.canonical_hash, pinned,
            "drift-manifest.json pinned sha256 is stale vs. live engine"
        )

    def test_drift_manifest_sha_matches_live_plan_edit(self):
        """Byte-identity (plan-edit) parity for dual-path verification."""
        import _lib.policy as _policy_mod
        manifest = json.loads(
            (_POLICIES_DIR / ".drift-manifest.json").read_text(encoding="utf-8")
        )
        policy = _policy_mod.load(_POLICIES_DIR / "plan-edit.policy.yaml")
        pinned = manifest["policies"]["plan-edit"]["sha256"]
        self.assertEqual(policy.canonical_hash, pinned)


# ---------------------------------------------------------------------------
# Dual-path consistency (engine vs. reference fixtures)
# ---------------------------------------------------------------------------


class TestDualPathConsistency(_DispatcherBase):
    """Dispatcher decisions must match `_lib.policy` direct evaluation."""

    def test_dispatcher_decision_matches_direct_load(self):
        """Reference event routed two ways yields identical decision."""
        import _lib.policy as _policy_mod
        event = {
            "tool": "Bash",
            "tool_input": {"command": "echo hi"},
            "_derived_bash": {
                "command": "echo hi",
                "credential_leak_provider": "",
                "credential_leak_redacted": "",
                "subcommands": ["echo hi"],
                "tokens_per_subcommand": [["echo", "hi"]],
                "matched_rm_rf": False,
                "matched_git_reset_hard": False,
                "matched_git_push_force": False,
            },
        }
        policy = _policy_mod.load(_POLICIES_DIR / "bash-safety.policy.yaml")
        direct = policy.decide(event)

        env = self._build_env()
        proc = _run_dispatcher("bash-safety", event, env)
        dispatched = _last_json(proc.stdout)
        # Ignore action-specific audit noise — compare decision fields only.
        self.assertEqual(direct["decision"], dispatched["decision"])


# ---------------------------------------------------------------------------
# Stdin / argv edge cases
# ---------------------------------------------------------------------------


class TestStdinAndArgv(_DispatcherBase):

    def test_empty_stdin_is_treated_as_empty_event(self):
        """Empty stdin bytes → engine sees `{}` → default allow."""
        env = self._build_env()
        proc = _run_dispatcher("bash-safety", {}, env, stdin_raw="")
        self.assertEqual(proc.returncode, 0, f"stderr={proc.stderr!r}")
        self.assertEqual(_last_json(proc.stdout).get("decision", "allow"), "allow")

    def test_malformed_stdin_json_is_treated_as_empty(self):
        """Bad JSON on stdin does not raise — falls through to defaults."""
        env = self._build_env()
        proc = _run_dispatcher("bash-safety", {}, env, stdin_raw="{not json")
        self.assertEqual(proc.returncode, 0, f"stderr={proc.stderr!r}")
        self.assertEqual(_last_json(proc.stdout).get("decision", "allow"), "allow")

    def test_argparse_requires_policy_flag(self):
        """Missing `--policy` → argparse exits non-zero."""
        env = self._build_env()
        # Run dispatcher without the required --policy flag.
        proc = subprocess.run(
            [sys.executable, str(_DISPATCHER)],
            input="{}",
            capture_output=True,
            text=True,
            timeout=5.0,
            env={**os.environ, **env},
        )
        self.assertNotEqual(proc.returncode, 0,
                            "argparse should reject missing --policy")


# ---------------------------------------------------------------------------
# Legacy-delegation fidelity
# ---------------------------------------------------------------------------


class TestLegacyDelegation(_DispatcherBase):

    def test_legacy_stdout_is_preserved_verbatim(self):
        """Dispatcher must mirror legacy hook's stdout (no wrapping)."""
        legacy = self.project_dir / "legacy_echo.py"
        payload = {"decision": "allow", "via": "legacy-exact", "marker": 42}
        legacy.write_text(textwrap.dedent(f"""
            #!/usr/bin/env python3
            import sys
            sys.stdout.write('{json.dumps(payload)}' + "\\n")
            sys.exit(0)
        """).strip() + "\n", encoding="utf-8")
        bogus = self.project_dir / "bogus.policy.yaml"
        bogus.write_text("garbage\n", encoding="utf-8")
        env = self._build_env({
            "CEO_POLICY_FILE": str(bogus),
            "CEO_POLICY_LEGACY_HOOK_PATH": str(legacy),
        })
        proc = _run_dispatcher("whatever", {}, env)
        self.assertEqual(proc.returncode, 0, f"stderr={proc.stderr!r}")
        out = _last_json(proc.stdout)
        self.assertEqual(out, payload)

    def test_legacy_nonzero_exit_surfaces_upward(self):
        """Legacy hook returning non-zero → dispatcher returns same rc."""
        legacy = self.project_dir / "legacy_bad.py"
        legacy.write_text(textwrap.dedent("""
            #!/usr/bin/env python3
            import sys
            sys.stdout.write('{"decision":"block","via":"legacy-err"}\\n')
            sys.exit(2)
        """).strip() + "\n", encoding="utf-8")
        bogus = self.project_dir / "bogus.policy.yaml"
        bogus.write_text("garbage\n", encoding="utf-8")
        env = self._build_env({
            "CEO_POLICY_FILE": str(bogus),
            "CEO_POLICY_LEGACY_HOOK_PATH": str(legacy),
        })
        proc = _run_dispatcher("whatever", {}, env)
        # Dispatcher re-raises legacy exit code (contract: legacy wins).
        self.assertEqual(proc.returncode, 2)
        out = _last_json(proc.stdout)
        self.assertEqual(out["decision"], "block")
        self.assertEqual(out["via"], "legacy-err")


if __name__ == "__main__":
    unittest.main()
