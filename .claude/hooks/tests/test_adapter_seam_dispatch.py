"""PLAN-155 Wave 1 — dispatch-seam tests for the four ENFORCED hooks.

Debate A1 (ratified seam option b): the four ENFORCED hooks
(`check_canonical_edit.py`, `check_bash_safety.py`, `check_plan_edit.py`,
`check_arbitration_kernel.py`) resolve their host adapter ONCE per
invocation through the shared seam ``_lib.adapters.resolve()``. Without
this seam, ``CEO_HOOK_ADAPTER=codex`` changes nothing and every ENFORCED
capability-matrix row silently becomes ABSENT (the S254 dead-gate class).

What this suite pins, ALL at subprocess level (the hooks run exactly as
the harness runs them — ``python3 <hook>.py`` with the envelope on stdin):

1. ``CEO_HOOK_ADAPTER=codex`` — each hook parses a RECORDED codex-cli
   0.139.0 wire envelope (fixtures under
   ``fixtures/adapters/codex/in/``, violation variants derived from the
   recorded shapes by substituting only ``tool_input.command``) and emits
   the CODEX decision shape:
   ``{"hookSpecificOutput": {"hookEventName": "PreToolUse",
   "permissionDecision": "deny", "permissionDecisionReason": ...}}``
   with the per-hook deny-reason class asserted. A Claude-shaped
   top-level ``{"decision": "block"}`` line is FOREIGN JSON on the codex
   wire (verified fail-open, `artifacts/failure-semantics-matrix.md`) —
   its absence is asserted explicitly.
2. ``CEO_HOOK_ADAPTER`` unset / ``=claude`` / ``=""`` — legacy Claude
   shapes, and unset vs explicit-"claude" vs empty-string outputs are
   BYTE-IDENTICAL (the Wave 1 regression bar).
3. Debate A2 coherence gate — an explicitly-set-but-unresolvable
   ``CEO_HOOK_ADAPTER`` is an INPUT/mis-configuration failure per the
   PLAN-152 C4 taxonomy: fail-CLOSED. ``_lib.adapters.resolve()``
   returns a ``_FailClosedAdapter`` whose egress ALWAYS denies in a
   single DUAL-VOCABULARY envelope readable by both harnesses —
   top-level ``{"decision": "block", "reason"}`` (Claude Code wire,
   enforced) AND ``hookSpecificOutput.permissionDecision: "deny"``
   (codex PreToolUse wire, enforced per the e1-deny transcript) —
   plus a stderr breadcrumb and an audit breadcrumb in the isolated
   audit area. No allow ever reaches stdout, and NEVER a silent
   fallback to the claude adapter (asserted via the reason class: the
   coherence-gate reason, never the hook's own matcher class).

Env discipline: ``TestEnvContext`` isolation; subprocess env derives from
the isolated ``os.environ`` (never the real ``$HOME`` /
``$CLAUDE_PROJECT_DIR``).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_HOOKS_DIR = Path(__file__).resolve().parent.parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

_FIXTURES_IN = Path(__file__).resolve().parent / "fixtures" / "adapters" / "codex" / "in"

_HOOKS: Dict[str, Path] = {
    "canonical": _HOOKS_DIR / "check_canonical_edit.py",
    "bash": _HOOKS_DIR / "check_bash_safety.py",
    "plan": _HOOKS_DIR / "check_plan_edit.py",
    "kernel": _HOOKS_DIR / "check_arbitration_kernel.py",
}

# Deny-reason CLASS per hook (debate A3: assert the class, not the bytes).
_REASON_CLASS: Dict[str, str] = {
    "canonical": "CANONICAL-EDIT-BLOCKED",
    "bash": "destructive",
    "plan": "PLAN-LIFECYCLE",
    "kernel": "ARBITRATION-KERNEL-BLOCKED",
}

# New-plan file written directly as done WITHOUT completed_at — the
# illegal plan-lifecycle write `decide_write` blocks (PLAN-SCHEMA §4).
_ILLEGAL_PLAN_CONTENT = (
    "---\n"
    "id: PLAN-991\n"
    "title: Seam dispatch positive control\n"
    "status: done\n"
    "---\n"
    "\n"
    "seam-test body\n"
)


def _apply_patch_text(verb: str, path: str, body_lines: List[str]) -> str:
    """Build an apply_patch ``tool_input.command`` in the RECORDED 0.139
    wire grammar (see fixtures/adapters/codex/in/pre_tool_use.apply_patch.*).
    """
    lines = ["*** Begin Patch", "*** {0} File: {1}".format(verb, path)]
    lines.extend(body_lines)
    lines.append("*** End Patch")
    return "\n".join(lines) + "\n"


class _SeamTestBase(TestEnvContext):
    """Shared layout + subprocess plumbing."""

    def _layout(self) -> None:
        p = self.project_dir
        (p / ".claude").mkdir(exist_ok=True)
        (p / ".claude" / "team.md").write_text("team\n", encoding="utf-8")
        (p / ".claude" / "plans").mkdir(parents=True, exist_ok=True)
        (p / ".claude" / "hooks").mkdir(parents=True, exist_ok=True)
        (p / ".claude" / "hooks" / "audit_log.py").write_text(
            "# kernel-path stub for the seam positive control\n",
            encoding="utf-8",
        )
        (p / "src").mkdir(exist_ok=True)
        (p / "src" / "app.ts").write_text("// benign\n", encoding="utf-8")

    def _env(self, adapter: Optional[str]) -> Dict[str, str]:
        """Subprocess env from the ISOLATED os.environ.

        adapter=None → CEO_HOOK_ADAPTER absent (the default path);
        otherwise set verbatim (including the empty string).
        Sentinel plaintext bypass mirrors test_check_canonical_edit.py —
        it exercises the Approved-By/Scope path, never GPG; it does NOT
        relax the no-sentinel deny these tests assert.
        """
        env = {k: v for k, v in os.environ.items() if v is not None}
        env.pop("CEO_HOOK_ADAPTER", None)
        if adapter is not None:
            env["CEO_HOOK_ADAPTER"] = adapter
        env.setdefault("CEO_SENTINEL_UNLOCK", "PLAN-091-test-fixture")
        env.setdefault("CEO_SENTINEL_UNLOCK_ACK", "I-ACCEPT")
        return env

    def _run(
        self,
        hook: str,
        stdin_text: str,
        adapter: Optional[str],
    ) -> Tuple[int, str, str]:
        proc = subprocess.run(
            [sys.executable, str(_HOOKS[hook])],
            input=stdin_text,
            capture_output=True,
            text=True,
            timeout=30,
            env=self._env(adapter),
            cwd=str(self.project_dir),
        )
        return proc.returncode, proc.stdout, proc.stderr

    # -- codex wire helpers -------------------------------------------------

    def _codex_envelope(self, fixture: str, command: Optional[str] = None) -> str:
        """A codex envelope derived from a RECORDED fixture.

        Only ``tool_input.command`` (the violation payload) and ``cwd``
        (the isolated project dir) are substituted; every other byte of
        the recorded 0.139 wire shape is preserved (debate A12: fixtures
        follow the pin, variants derive from recorded shapes).
        """
        src = _FIXTURES_IN / fixture
        self.assertTrue(
            src.is_file(),
            "recorded codex fixture missing: {0} (A4: a fixture-less codex "
            "suite must FAIL, not skip)".format(src),
        )
        payload = json.loads(src.read_text(encoding="utf-8"))
        payload["cwd"] = str(self.project_dir)
        if command is not None:
            payload["tool_input"]["command"] = command
        return json.dumps(payload)

    # -- claude payloads ----------------------------------------------------

    def _claude_payloads(self) -> Dict[str, Dict[str, str]]:
        p = self.project_dir
        return {
            "canonical": {
                "violation": json.dumps(
                    {"tool_name": "Edit", "tool_input": {"file_path": str(p / ".claude" / "team.md")}}
                ),
                "benign": json.dumps(
                    {"tool_name": "Edit", "tool_input": {"file_path": str(p / "src" / "app.ts")}}
                ),
            },
            "bash": {
                "violation": json.dumps(
                    {"tool_name": "Bash", "tool_input": {"command": "rm -rf ~"}}
                ),
                "benign": json.dumps(
                    {"tool_name": "Bash", "tool_input": {"command": "echo hello-seam"}}
                ),
            },
            "plan": {
                "violation": json.dumps(
                    {
                        "tool_name": "Write",
                        "tool_input": {
                            "file_path": str(p / ".claude" / "plans" / "PLAN-991-seam-test.md"),
                            "content": _ILLEGAL_PLAN_CONTENT,
                        },
                    }
                ),
                "benign": json.dumps(
                    {
                        "tool_name": "Write",
                        "tool_input": {"file_path": str(p / "notes.txt"), "content": "x\n"},
                    }
                ),
            },
            "kernel": {
                "violation": json.dumps(
                    {"tool_name": "Edit", "tool_input": {"file_path": str(p / ".claude" / "hooks" / "audit_log.py")}}
                ),
                "benign": json.dumps(
                    {"tool_name": "Edit", "tool_input": {"file_path": str(p / "src" / "app.ts")}}
                ),
            },
        }

    def _codex_payloads(self) -> Dict[str, Dict[str, str]]:
        return {
            "canonical": {
                "violation": self._codex_envelope(
                    "pre_tool_use.apply_patch.update-file.json",
                    _apply_patch_text("Update", ".claude/team.md", ["@@", "-team", "+tampered"]),
                ),
                "benign": self._codex_envelope("pre_tool_use.apply_patch.update-file.json"),
            },
            "bash": {
                "violation": self._codex_envelope("pre_tool_use.bash.echo.json", "rm -rf ~"),
                "benign": self._codex_envelope("pre_tool_use.bash.echo.json"),
            },
            "plan": {
                "violation": self._codex_envelope(
                    "pre_tool_use.apply_patch.add-file.json",
                    _apply_patch_text(
                        "Add",
                        ".claude/plans/PLAN-991-seam-test.md",
                        ["+" + ln for ln in _ILLEGAL_PLAN_CONTENT.splitlines()],
                    ),
                ),
                "benign": self._codex_envelope("pre_tool_use.apply_patch.add-file.json"),
            },
            "kernel": {
                "violation": self._codex_envelope(
                    "pre_tool_use.apply_patch.update-file.json",
                    _apply_patch_text(
                        "Update", ".claude/hooks/audit_log.py", ["@@", "-x", "+y"]
                    ),
                ),
                "benign": self._codex_envelope("pre_tool_use.apply_patch.update-file.json"),
            },
        }

    # -- shape assertions ---------------------------------------------------

    def _assert_codex_deny(self, hook: str, rc: int, out: str, err: str) -> None:
        self.assertEqual(rc, 0, msg="rc={0} out={1!r} err={2!r}".format(rc, out, err))
        self.assertTrue(out.strip(), msg="empty stdout is silent fail-open on the codex wire")
        parsed = json.loads(out.strip().splitlines()[-1])
        self.assertNotIn(
            "decision",
            parsed,
            msg="top-level Claude-shaped decision under CEO_HOOK_ADAPTER=codex "
            "is foreign JSON on the codex wire (silent fail-open — S254 class): "
            + out,
        )
        hso = parsed.get("hookSpecificOutput") or {}
        self.assertEqual(hso.get("hookEventName"), "PreToolUse", msg=out)
        self.assertEqual(hso.get("permissionDecision"), "deny", msg=out)
        reason = hso.get("permissionDecisionReason") or ""
        self.assertIn(_REASON_CLASS[hook], reason, msg=out)

    def _assert_codex_not_deny(self, rc: int, out: str, err: str) -> None:
        self.assertEqual(rc, 0, msg="rc={0} out={1!r} err={2!r}".format(rc, out, err))
        stripped = out.strip()
        if not stripped:
            return  # silent allow is a legal codex allow
        parsed = json.loads(stripped.splitlines()[-1])
        self.assertNotIn(
            "decision",
            parsed,
            msg="Claude-shaped output under CEO_HOOK_ADAPTER=codex: " + out,
        )
        hso = parsed.get("hookSpecificOutput") or {}
        self.assertNotEqual(hso.get("permissionDecision"), "deny", msg=out)

    def _assert_claude_block(self, hook: str, rc: int, out: str, err: str) -> None:
        self.assertEqual(rc, 0, msg="rc={0} out={1!r} err={2!r}".format(rc, out, err))
        parsed = json.loads(out.strip().splitlines()[-1])
        self.assertEqual(parsed.get("decision"), "block", msg=out)
        self.assertIn(_REASON_CLASS[hook], parsed.get("reason") or "", msg=out)
        self.assertNotIn(
            "hookSpecificOutput",
            parsed,
            msg="codex-shaped envelope leaked into the claude wire: " + out,
        )

    def _assert_claude_allow(self, rc: int, out: str, err: str) -> None:
        self.assertEqual(rc, 0, msg="rc={0} out={1!r} err={2!r}".format(rc, out, err))
        parsed = json.loads(out.strip().splitlines()[-1])
        self.assertNotEqual(parsed.get("decision"), "block", msg=out)


class SeamCodexDispatchTest(_SeamTestBase):
    """CEO_HOOK_ADAPTER=codex: recorded envelope in → codex decision out."""

    def test_codex_violation_denied_per_hook(self) -> None:
        self._layout()
        payloads = self._codex_payloads()
        for hook in _HOOKS:
            with self.subTest(hook=hook):
                rc, out, err = self._run(hook, payloads[hook]["violation"], "codex")
                self._assert_codex_deny(hook, rc, out, err)

    def test_codex_benign_not_denied_per_hook(self) -> None:
        self._layout()
        payloads = self._codex_payloads()
        for hook in _HOOKS:
            with self.subTest(hook=hook):
                rc, out, err = self._run(hook, payloads[hook]["benign"], "codex")
                self._assert_codex_not_deny(rc, out, err)


class SeamClaudeRegressionTest(_SeamTestBase):
    """CEO_HOOK_ADAPTER unset / =claude / ="" : legacy shapes, byte-identical."""

    def test_claude_violation_blocked_per_hook(self) -> None:
        self._layout()
        payloads = self._claude_payloads()
        for hook in _HOOKS:
            with self.subTest(hook=hook):
                rc, out, err = self._run(hook, payloads[hook]["violation"], None)
                self._assert_claude_block(hook, rc, out, err)

    def test_claude_benign_allowed_per_hook(self) -> None:
        self._layout()
        payloads = self._claude_payloads()
        for hook in _HOOKS:
            with self.subTest(hook=hook):
                rc, out, err = self._run(hook, payloads[hook]["benign"], None)
                self._assert_claude_allow(rc, out, err)

    def test_unset_vs_explicit_claude_vs_empty_byte_identical(self) -> None:
        """The Wave 1 regression bar: the seam default is not merely
        equivalent — stdout is byte-identical across CEO_HOOK_ADAPTER
        unset, ="claude", and ="" (set-but-empty falls back to the
        default per the registry contract; only NON-empty unresolvable
        values trip the A2 gate)."""
        self._layout()
        payloads = self._claude_payloads()
        for hook in _HOOKS:
            for kind in ("violation", "benign"):
                with self.subTest(hook=hook, kind=kind):
                    rc_u, out_u, _ = self._run(hook, payloads[hook][kind], None)
                    rc_c, out_c, _ = self._run(hook, payloads[hook][kind], "claude")
                    rc_e, out_e, _ = self._run(hook, payloads[hook][kind], "")
                    self.assertEqual(rc_u, rc_c)
                    self.assertEqual(rc_u, rc_e)
                    self.assertEqual(out_u, out_c)
                    self.assertEqual(out_u, out_e)


class SeamCoherenceGateTest(_SeamTestBase):
    """Debate A2: explicitly-set-but-unresolvable CEO_HOOK_ADAPTER is an
    INPUT failure (PLAN-152 C4) → fail-CLOSED deny + audit breadcrumb,
    never a silent fallback to the claude adapter."""

    _BOGUS = "gemini"  # in nobody's KNOWN_ADAPTERS registry

    def _audit_area_text(self) -> str:
        chunks: List[str] = []
        for root in (self.audit_dir,):
            if not root.is_dir():
                continue
            for f in sorted(root.rglob("*")):
                if f.is_file():
                    try:
                        chunks.append(f.read_text(encoding="utf-8", errors="replace"))
                    except OSError:
                        pass
        return "\n".join(chunks)

    def _assert_dual_vocab_coherence_deny(
        self, hook: str, rc: int, out: str, err: str
    ) -> None:
        """The implemented A2 contract: rc 0 + ONE dual-vocabulary deny
        envelope on stdout + a stderr breadcrumb. Enforced on BOTH wires:
        top-level ``decision: block`` (Claude Code) and
        ``hookSpecificOutput.permissionDecision: deny`` (codex PreToolUse,
        e1-deny transcript)."""
        self.assertEqual(
            rc, 0,
            msg="hook={0} rc={1} out={2!r} err={3!r}".format(hook, rc, out, err),
        )
        self.assertIn("CEO_HOOK_ADAPTER", err, msg=err)
        stripped = out.strip()
        self.assertTrue(stripped, msg="empty stdout is silent fail-open")
        parsed = json.loads(stripped.splitlines()[-1])
        # Claude vocabulary: enforced block.
        self.assertEqual(parsed.get("decision"), "block", msg=out)
        # Codex vocabulary: enforced PreToolUse deny.
        hso = parsed.get("hookSpecificOutput") or {}
        self.assertEqual(hso.get("permissionDecision"), "deny", msg=out)
        # The deny must come from the COHERENCE GATE, not from a silently
        # dispatched claude adapter running the hook's own matcher.
        reason = (parsed.get("reason") or "") + (
            hso.get("permissionDecisionReason") or ""
        )
        self.assertIn("adapter coherence gate", reason, msg=out)
        self.assertIn("CEO_HOOK_ADAPTER", reason, msg=out)
        self.assertNotIn(_REASON_CLASS[hook], reason, msg=out)
        # No grant may reach stdout in either vocabulary.
        self.assertNotEqual(stripped, "{}", msg=out)
        self.assertNotIn('"decision": "allow"', stripped, msg=out)
        self.assertNotIn('"permissionDecision": "allow"', stripped, msg=out)

    def test_bogus_adapter_fails_closed_per_hook(self) -> None:
        self._layout()
        payloads = self._claude_payloads()
        for hook in _HOOKS:
            with self.subTest(hook=hook):
                # BENIGN payload: the deny must come from the coherence
                # gate itself, not from the hook's own matcher.
                rc, out, err = self._run(hook, payloads[hook]["benign"], self._BOGUS)
                self._assert_dual_vocab_coherence_deny(hook, rc, out, err)

    def test_bogus_adapter_leaves_audit_breadcrumb(self) -> None:
        self._layout()
        payloads = self._claude_payloads()
        rc, out, err = self._run("bash", payloads["bash"]["benign"], self._BOGUS)
        self._assert_dual_vocab_coherence_deny("bash", rc, out, err)
        area = self._audit_area_text()
        self.assertTrue(
            ("adapter" in area.lower()),
            msg="A2 requires an audit breadcrumb naming the adapter "
            "resolution failure in the isolated audit area; found none. "
            "Audit area contents:\n" + (area[:2000] or "<empty>"),
        )

    def test_bogus_adapter_never_silently_falls_back_to_claude(self) -> None:
        """A VIOLATION under a bogus adapter must come back as the
        COHERENCE deny, never as the hook's own matcher class — the
        hook's class appearing would prove a silent fallback dispatched
        the claude adapter (the exact anti-pattern A2 bans)."""
        self._layout()
        payloads = self._claude_payloads()
        for hook in _HOOKS:
            with self.subTest(hook=hook):
                rc, out, err = self._run(hook, payloads[hook]["violation"], self._BOGUS)
                self._assert_dual_vocab_coherence_deny(hook, rc, out, err)


if __name__ == "__main__":
    unittest.main()
