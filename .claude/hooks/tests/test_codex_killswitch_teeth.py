"""PLAN-155 Wave 3b (SENT-CX-E) — kill-switch teeth, behavioral controls.

THE CERTIFYING ARTIFACT for the debate-A8 circular-disarm closure: Waves
2/3 emit the `.codex` registration/rules/operator-doc templates as
UNGUARDED L2 files; without teeth an agent under codex could rewrite
`.codex/hooks.json` (or the rest of the surface) and disarm every ENFORCED
rail while the tripwire that should detect it stays silent. This wave adds
the teeth; this suite proves they bite BEHAVIORALLY (not by a static list
diff — that would have stayed green through the S254 dead-gate class):

  (a) a planted UNSENTINELED edit to each kill-switch path, replayed as a
      recorded codex-cli 0.139.0 apply_patch envelope on the BYTE-IDENTICAL
      `check_canonical_edit.py` command line shipped in
      `templates/codex/hooks.json` (CEO_HOOK_ADAPTER=codex, argv-split from
      a project cwd), comes back
      `hookSpecificOutput.permissionDecision: deny` + CANONICAL-EDIT-BLOCKED;

  (b) a foreign approval marker (a sentinel scoping a DIFFERENT path) does
      NOT disarm the surface — the edit still denies (copied-marker-still-
      reddens: scope must list the exact path);

  (c) a MUTATED kill-switch file turns the SessionStart boot re-hash RED —
      run as a subprocess on the shipped `SessionStart.py` command line
      across two boots (baseline → mutate → RED breadcrumb).

Landing-order note: this file is in the SENT-CX-E (wave-3b) batch but
READS `templates/codex/hooks.json` (wave-2, unguarded L2, already on main)
and copies the wave-1/3b hooks tree into an isolated install. A missing
template is a hard FAIL here (never skip-to-green).
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_HOOKS_DIR = Path(__file__).resolve().parent.parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

_REPO_ROOT = Path(__file__).resolve().parents[3]
_TEMPLATE = _REPO_ROOT / "templates" / "codex" / "hooks.json"
_FIXTURES_IN = (
    Path(__file__).resolve().parent / "fixtures" / "adapters" / "codex" / "in"
)
_PLACEHOLDER = "{{PROJECT_PATH}}"

#: The exact kill-switch surface (plan §Wave 3b / file assignment).
_KILLSWITCH_PATHS: Tuple[str, ...] = (
    ".codex/hooks.json",
    ".codex/config.toml",
    ".codex/rules/ceo.rules",
    "requirements.toml",
    "AGENTS.md",
)


def _apply_patch_update(path: str) -> str:
    """apply_patch `tool_input.command` (recorded 0.139 grammar) that
    updates a single file — the planted kill-switch edit."""
    return (
        "*** Begin Patch\n"
        "*** Update File: {0}\n"
        "@@\n-old\n+tampered\n"
        "*** End Patch\n".format(path)
    )


class _KillswitchTeethBase(TestEnvContext):
    """Shared install-shaped isolation + shipped-command plumbing."""

    def _command_for(self, script: str) -> str:
        """The shipped, `{{PROJECT_PATH}}`-substituted command for a hook
        script (FAILS, never skips, if the wave-2 template is missing)."""
        self.assertTrue(
            _TEMPLATE.is_file(),
            "templates/codex/hooks.json missing at {0} — the A8 teeth replay "
            "the SHIPPED command line (wave-2 lands before wave-3b, "
            "MANIFEST-A landing order)".format(_TEMPLATE),
        )
        doc = json.loads(_TEMPLATE.read_text(encoding="utf-8"))
        for groups in doc.get("hooks", {}).values():
            for group in groups:
                for h in group.get("hooks", []):
                    cmd = h.get("command", "")
                    if script in cmd:
                        return cmd
        self.fail("shipped hooks.json registers no command for %s" % script)

    def _install(self) -> None:
        """Materialize an install-shaped isolated project: the hooks tree
        under test (minus tests/) copied to the INSTALLED location, plus a
        full kill-switch surface + a benign non-canonical file."""
        p = self.project_dir
        dst = p / ".claude" / "hooks"
        if not dst.exists():
            shutil.copytree(
                str(_REPO_ROOT / ".claude" / "hooks"),
                str(dst),
                ignore=shutil.ignore_patterns("tests", "__pycache__"),
            )
        (p / ".claude" / "plans").mkdir(parents=True, exist_ok=True)
        (p / ".claude" / "team.md").write_text("team\n", encoding="utf-8")
        # Full kill-switch surface present on disk (real edits target files).
        (p / ".codex" / "rules").mkdir(parents=True, exist_ok=True)
        (p / ".codex" / "hooks.json").write_text('{"hooks": {}}\n', encoding="utf-8")
        (p / ".codex" / "config.toml").write_text("# codex\n", encoding="utf-8")
        (p / ".codex" / "rules" / "ceo.rules").write_text("# rules\n", encoding="utf-8")
        (p / "requirements.toml").write_text("# req\n", encoding="utf-8")
        (p / "AGENTS.md").write_text("# operator\n", encoding="utf-8")
        (p / "src").mkdir(exist_ok=True)
        (p / "src" / "app.ts").write_text("// benign\n", encoding="utf-8")

    def _env(self) -> Dict[str, str]:
        """Subprocess env from the ISOLATED os.environ. CEO_HOOK_ADAPTER and
        CLAUDE_PROJECT_DIR are POPPED — the shipped command's own `env`
        prefix must supply both. The sentinel plaintext bypass is set (it
        exercises the Approved-By/Scope path, never GPG) and does NOT relax
        the no-sentinel deny these tests assert."""
        env = {k: v for k, v in os.environ.items() if v is not None}
        env.pop("CEO_HOOK_ADAPTER", None)
        env.pop("CLAUDE_PROJECT_DIR", None)
        env.setdefault("CEO_SENTINEL_UNLOCK", "PLAN-091-test-fixture")
        env.setdefault("CEO_SENTINEL_UNLOCK_ACK", "I-ACCEPT")
        return env

    def _run(self, script: str, stdin_text: str) -> Tuple[int, str, str]:
        cmd = self._command_for(script).replace(_PLACEHOLDER, str(self.project_dir))
        self.assertNotIn("{{", cmd, "unsubstituted placeholder")
        argv = shlex.split(cmd)
        proc = subprocess.run(
            argv, input=stdin_text, capture_output=True, text=True,
            timeout=60, env=self._env(), cwd=str(self.project_dir),
        )
        return proc.returncode, proc.stdout, proc.stderr

    def _codex_envelope(self, fixture: str, command: str) -> str:
        src = _FIXTURES_IN / fixture
        self.assertTrue(
            src.is_file(),
            "recorded codex fixture missing: {0} (never skip-to-green)".format(src),
        )
        payload = json.loads(src.read_text(encoding="utf-8"))
        payload["cwd"] = str(self.project_dir)
        payload["tool_input"]["command"] = command
        return json.dumps(payload)

    def _last_json(self, out: str) -> Dict[str, object]:
        stripped = out.strip()
        self.assertTrue(stripped, "empty stdout where a decision was required")
        return json.loads(stripped.splitlines()[-1])


class CanonicalDenyOnKillswitchTest(_KillswitchTeethBase):
    """(a)+(b): the edit-time canonical rail denies unsentineled kill-switch
    edits on the shipped command line."""

    def test_each_killswitch_path_denied_unsentineled(self) -> None:
        self._install()
        for rel in _KILLSWITCH_PATHS:
            with self.subTest(path=rel):
                env = self._codex_envelope(
                    "pre_tool_use.apply_patch.update-file.json",
                    _apply_patch_update(rel),
                )
                rc, out, err = self._run("check_canonical_edit.py", env)
                self.assertEqual(rc, 0, msg="rc=%d err=%r" % (rc, err))
                parsed = self._last_json(out)
                hso = parsed.get("hookSpecificOutput") or {}
                self.assertEqual(
                    hso.get("permissionDecision"), "deny",
                    msg="kill-switch path %s NOT denied on the shipped command "
                    "line (circular-disarm gap open). out=%s err=%s"
                    % (rel, out, err),
                )
                self.assertIn(
                    "CANONICAL-EDIT-BLOCKED",
                    str(hso.get("permissionDecisionReason") or ""), msg=out,
                )

    def test_foreign_approval_marker_still_reddens(self) -> None:
        """A sentinel scoping a DIFFERENT path does NOT disarm a kill-switch
        edit — the approval marker is present but the scope does not list
        this path (copied-marker-still-reddens)."""
        self._install()
        sent = (
            self.project_dir / ".claude" / "plans" / "PLAN-155"
            / "architect" / "round-1"
        )
        sent.mkdir(parents=True, exist_ok=True)
        (sent / "approved.md").write_text(
            "---\nplan: PLAN-155\n---\n\n"
            "Approved-By: @Canhada-Labs deadbeef\n"
            "Scope:\n  - .claude/team.md\n",
            encoding="utf-8",
        )
        env = self._codex_envelope(
            "pre_tool_use.apply_patch.update-file.json",
            _apply_patch_update(".codex/hooks.json"),
        )
        rc, out, err = self._run("check_canonical_edit.py", env)
        parsed = self._last_json(out)
        hso = parsed.get("hookSpecificOutput") or {}
        self.assertEqual(hso.get("permissionDecision"), "deny", msg=out)

    def test_scoped_sentinel_grants_killswitch_edit(self) -> None:
        """Control: a sentinel that DOES scope the kill-switch path grants the
        edit — the surface is sentinel-GATED, not blanket-denied."""
        self._install()
        sent = (
            self.project_dir / ".claude" / "plans" / "PLAN-155"
            / "architect" / "round-1"
        )
        sent.mkdir(parents=True, exist_ok=True)
        (sent / "approved.md").write_text(
            "---\nplan: PLAN-155\n---\n\n"
            "Approved-By: @Canhada-Labs deadbeef\n"
            "Scope:\n  - .codex/hooks.json\n",
            encoding="utf-8",
        )
        env = self._codex_envelope(
            "pre_tool_use.apply_patch.update-file.json",
            _apply_patch_update(".codex/hooks.json"),
        )
        rc, out, err = self._run("check_canonical_edit.py", env)
        stripped = out.strip()
        if stripped:
            parsed = json.loads(stripped.splitlines()[-1])
            hso = parsed.get("hookSpecificOutput") or {}
            self.assertNotEqual(
                hso.get("permissionDecision"), "deny",
                msg="scoped sentinel should GRANT the kill-switch edit: " + out,
            )


class BootTripwireRedTest(_KillswitchTeethBase):
    """(c): a mutated kill-switch file turns the SessionStart boot re-hash
    RED, end-to-end on the shipped SessionStart.py command line."""

    def _session_start_stdin(self) -> str:
        src = _FIXTURES_IN / "session_start.startup.a.json"
        self.assertTrue(src.is_file(), "recorded session_start fixture missing")
        payload = json.loads(src.read_text(encoding="utf-8"))
        payload["cwd"] = str(self.project_dir)
        return json.dumps(payload)

    def test_mutated_killswitch_file_reddens_boot_rehash(self) -> None:
        self._install()
        stdin = self._session_start_stdin()
        # Boot #1 — records the baseline (informational, not RED).
        rc1, _out1, err1 = self._run("SessionStart.py", stdin)
        self.assertEqual(rc1, 0, msg=err1)
        self.assertNotIn("KILLSWITCH-TRIPWIRE-RED", err1)
        # Tamper: rewrite the registration to disarm the rails.
        (self.project_dir / ".codex" / "hooks.json").write_text(
            '{"hooks": {"disarmed": true}}\n', encoding="utf-8"
        )
        # Boot #2 — the tripwire must go RED (breadcrumb on stderr).
        rc2, out2, err2 = self._run("SessionStart.py", stdin)
        self.assertEqual(rc2, 0, msg=err2)  # never blocks the boot
        self.assertIn(
            "KILLSWITCH-TRIPWIRE-RED", err2,
            msg="mutated kill-switch file did NOT redden the boot re-hash "
            "(silent fail-open = the S254 dead-gate class). stderr=%s" % err2,
        )
        # The session still starts (continue:true on stdout).
        if out2.strip():
            payload = json.loads(out2.strip().splitlines()[-1])
            self.assertTrue(payload.get("continue") is True)

    def test_absent_surface_no_red(self) -> None:
        """No `.codex/` surface installed → the boot re-hash is a no-op
        (no yellow-fatigue)."""
        p = self.project_dir
        dst = p / ".claude" / "hooks"
        if not dst.exists():
            shutil.copytree(
                str(_REPO_ROOT / ".claude" / "hooks"),
                str(dst),
                ignore=shutil.ignore_patterns("tests", "__pycache__"),
            )
        (p / "AGENTS.md").write_text("# reviewer contract\n", encoding="utf-8")
        rc, _out, err = self._run("SessionStart.py", self._session_start_stdin())
        self.assertEqual(rc, 0, msg=err)
        self.assertNotIn("KILLSWITCH-TRIPWIRE-RED", err)


if __name__ == "__main__":
    unittest.main()
