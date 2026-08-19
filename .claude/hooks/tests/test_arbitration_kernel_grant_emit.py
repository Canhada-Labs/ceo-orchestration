#!/usr/bin/env python3
"""PLAN-169 W3-K (ledger E.2) — POSITIVE proof of the kernel GRANT path.

Until this file, only the BLOCK path of ``check_arbitration_kernel`` was
proven. The grant path — the one an Owner takes during a kernel ceremony
with ``CEO_KERNEL_OVERRIDE`` + ``CEO_KERNEL_OVERRIDE_ACK`` — was covered
by nothing, and it carried two defects at once:

1. ``veto_triggered reason_code=kernel_override_used`` was NEVER written.
   ``main()`` gated that emit on ``decision == "allow"`` read back out of
   its own egress JSON, but ``_emit_allow()`` emits ``{}`` /
   ``{"systemMessage": ...}`` and never a ``decision`` key — the branch
   was unreachable from birth. The hook's docstring and the very
   systemMessage the operator reads told them to look for an event that
   did not exist.
2. ``kernel_extension_landed`` DID land (the action rides
   ``_EMIT_GENERIC_PASSTHROUGH``), but with a filesystem PATH in
   ``ceremony_sha`` and the free-text override REASON in ``plan_id``.

The tests below drive the real hook end-to-end as a SUBPROCESS (the
S254 anti-dead-gate doctrine: exercise the entry point, not a helper)
under ``TestEnvContext`` isolation — every write lands in the per-test
temp HOME / project / audit dir, never the real ones.

The hook under test is the SIBLING of this file's parent directory, so
the same file proves the STAGED pack before landing and the LANDED hook
after — there is no path that silently tests the other copy.
"""

from __future__ import annotations

import json
import hashlib
import os
import re
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Dict, List, Optional

_THIS = Path(__file__).resolve()

# The hook under test: sibling of tests/ inside THIS pack (staged today,
# .claude/hooks/ after landing). Never resolved against the repo root, so
# the staged copy cannot be shadowed by the live one.
HOOK_UNDER_TEST = _THIS.parents[1] / "check_arbitration_kernel.py"


def _repo_root() -> Path:
    p = _THIS
    for _ in range(12):
        if (p / ".git").exists():
            return p
        p = p.parent
    return _THIS.parents[3]


REPO = _repo_root()
# `_lib` (audit_emit, testing, adapters) always comes from the LIVE hooks
# tree: a staged pack ships only the files it changes, and after landing
# this IS the hook's own directory.
LIVE_HOOKS = REPO / ".claude" / "hooks"
if str(LIVE_HOOKS) not in sys.path:
    sys.path.insert(0, str(LIVE_HOOKS))

from _lib.testing import TestEnvContext  # noqa: E402

import importlib.util as _ilu  # noqa: E402


def _load_hook_module():
    spec = _ilu.spec_from_file_location(
        "check_arbitration_kernel_w3k", str(HOOK_UNDER_TEST)
    )
    assert spec and spec.loader
    mod = _ilu.module_from_spec(spec)
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


MOD = _load_hook_module()

# A ceremony sha is 64 lowercase hex, or empty when no honest digest
# exists. A PATH must never match.
_SHA_RE = re.compile(r"^(?:[0-9a-f]{64})?$")
# A plan id is PLAN-NNN, or the literal "unknown". The override REASON
# (free text chosen by the operator) must never match.
_PLAN_ID_RE = re.compile(r"^(?:PLAN-[0-9]{3,}|unknown)$")

_OVERRIDE_REASON = "PLAN-169-W3K-grant-emit-test"
_KERNEL_REL = ".claude/hooks/check_agent_spawn.py"


class _GrantPathBase(TestEnvContext):
    """Shared harness: isolated tree + a real kernel-path target."""

    def setUp(self) -> None:
        super().setUp()
        self.target = self.project_dir / _KERNEL_REL
        self.target.parent.mkdir(parents=True, exist_ok=True)
        self.target.write_bytes(b"# kernel file under test\n")
        self.audit_log = self.audit_dir / "audit-log.jsonl"

    # -- helpers ---------------------------------------------------------

    def _run_hook(self, extra_env: Optional[Dict[str, str]] = None):
        """Invoke the hook as a subprocess on an Edit of the kernel path.

        The environment is inherited from TestEnvContext (HOME,
        CLAUDE_PROJECT_DIR and the CEO_AUDIT_LOG_* trio already point at
        the per-test temp tree), plus PYTHONPATH so the hook resolves
        `_lib` from the live hooks tree the way it will once landed.
        """
        env = dict(os.environ)
        env["PYTHONPATH"] = str(LIVE_HOOKS) + os.pathsep + env.get("PYTHONPATH", "")
        env["CEO_AUDIT_SYNC_MODE"] = "1"
        for key in ("CEO_KERNEL_OVERRIDE", "CEO_KERNEL_OVERRIDE_ACK"):
            env.pop(key, None)
        if extra_env:
            env.update(extra_env)
        payload = json.dumps(
            {
                "tool_name": "Edit",
                "tool_input": {
                    "file_path": str(self.target),
                    "old_string": "a",
                    "new_string": "b",
                },
            }
        )
        return subprocess.run(
            [sys.executable, str(HOOK_UNDER_TEST)],
            input=payload,
            env=env,
            capture_output=True,
            text=True,
            timeout=60,
        )

    def _events(self, action: str) -> List[dict]:
        if not self.audit_log.is_file():
            return []
        out: List[dict] = []
        for line in self.audit_log.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if ev.get("action") == action:
                out.append(ev)
        return out


class GrantPathEmitsHonestEvent(_GrantPathBase):
    """The GRANT path: allow + BOTH audit events, with honest fields."""

    def setUp(self) -> None:
        super().setUp()
        self.proc = self._run_hook(
            {
                "CEO_KERNEL_OVERRIDE": _OVERRIDE_REASON,
                "CEO_KERNEL_OVERRIDE_ACK": "I-ACCEPT",
            }
        )

    # (a) the decision is ALLOW -----------------------------------------

    def test_grant_decision_is_allow(self) -> None:
        self.assertEqual(self.proc.returncode, 0, self.proc.stderr)
        out = json.loads(self.proc.stdout.strip())
        # Allow on the PreToolUse wire = absence of a block decision.
        self.assertNotEqual(out.get("decision"), "block")
        # And it is the OVERRIDE allow, not the adapter fail-open allow:
        # only decide()'s grant branch emits this systemMessage. Without
        # this assertion an ImportError would produce a bare `{}` that
        # still "passes" an allow check — the vacuous-green class.
        self.assertIn("override granted", out.get("systemMessage", ""))
        self.assertIn(_OVERRIDE_REASON, out.get("systemMessage", ""))

    # (b) the event IS present ------------------------------------------

    def test_kernel_extension_landed_is_emitted(self) -> None:
        events = self._events("kernel_extension_landed")
        self.assertEqual(
            len(events),
            1,
            "grant path must emit exactly one kernel_extension_landed; "
            f"audit log: {self.audit_log}",
        )
        self.assertEqual(events[0].get("wave"), "kernel-override")

    # (c) ceremony_sha is a digest or empty — NEVER a path ---------------

    def test_ceremony_sha_is_digest_or_empty(self) -> None:
        ev = self._events("kernel_extension_landed")[0]
        sha = ev.get("ceremony_sha")
        self.assertIsInstance(sha, str)
        self.assertRegex(sha, _SHA_RE)
        self.assertNotIn("/", sha)
        self.assertNotIn(".py", sha)

    def test_ceremony_sha_is_the_targets_actual_digest(self) -> None:
        """Format alone is cheap; the value must also be TRUE."""
        ev = self._events("kernel_extension_landed")[0]
        expected = hashlib.sha256(self.target.read_bytes()).hexdigest()
        self.assertEqual(ev.get("ceremony_sha"), expected)

    # (d) plan_id is a plan id or "unknown" — NEVER the reason -----------

    def test_plan_id_is_plan_or_unknown_never_the_reason(self) -> None:
        ev = self._events("kernel_extension_landed")[0]
        plan_id = ev.get("plan_id")
        self.assertIsInstance(plan_id, str)
        self.assertRegex(plan_id, _PLAN_ID_RE)
        self.assertNotEqual(plan_id, _OVERRIDE_REASON)
        # In an isolated tree there is no plan_transition for the
        # session, so the honest answer is the literal fallback.
        self.assertEqual(plan_id, "unknown")

    # the revived branch: the event the operator is TOLD to look for -----

    def test_veto_triggered_kernel_override_used_is_emitted(self) -> None:
        events = [
            e for e in self._events("veto_triggered")
            if e.get("reason_code") == "kernel_override_used"
        ]
        self.assertEqual(
            len(events),
            1,
            "the hook's systemMessage points the operator at "
            "veto_triggered reason_code=kernel_override_used; it must "
            "actually be written (PLAN-169 E.2 dead-branch cure)",
        )
        ev = events[0]
        self.assertEqual(ev.get("hook"), "check_arbitration_kernel")
        # The override REASON survives — on the event whose schema has a
        # free-text field for it, not laundered through plan_id.
        self.assertIn(_OVERRIDE_REASON, ev.get("reason_preview", ""))
        self.assertIn(_KERNEL_REL, ev.get("reason_preview", ""))

    def test_no_stderr_audit_failure_breadcrumb(self) -> None:
        """Fail-open is now VISIBLE — so silence proves the emit worked."""
        self.assertNotIn("audit emit FAILED", self.proc.stderr)


class PlanIdIsResolvedNotHardcoded(_GrantPathBase):
    """Teeth for the ``unknown`` assertion above.

    ``unknown`` is the honest answer only when the session has no
    ``plan_transition``. Give it one and the SAME code path must report
    the real plan — otherwise ``_resolve_plan_id_or_unknown`` would be a
    constant dressed up as a resolver.
    """

    def test_plan_id_reports_the_sessions_plan(self) -> None:
        from _lib import audit_emit  # noqa: PLC0415

        session_id = "sess-w3k-plan-resolution"
        audit_emit.emit_plan_transition(
            plan_id="PLAN-169",
            from_status="reviewed",
            to_status="executing",
            file_path=".claude/plans/PLAN-169-closure.md",
            session_id=session_id,
        )
        proc = self._run_hook(
            {
                "CEO_KERNEL_OVERRIDE": _OVERRIDE_REASON,
                "CEO_KERNEL_OVERRIDE_ACK": "I-ACCEPT",
                "CLAUDE_SESSION_ID": session_id,
            }
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        ev = self._events("kernel_extension_landed")[0]
        self.assertEqual(ev.get("plan_id"), "PLAN-169")


class NegativeControlNoOverride(_GrantPathBase):
    """Without the override env the same edit is BLOCKED and unaudited."""

    def setUp(self) -> None:
        super().setUp()
        self.proc = self._run_hook()

    def test_decision_is_block(self) -> None:
        self.assertEqual(self.proc.returncode, 0, self.proc.stderr)
        out = json.loads(self.proc.stdout.strip())
        self.assertEqual(out.get("decision"), "block")
        self.assertIn("ARBITRATION-KERNEL-BLOCKED", out.get("reason", ""))

    def test_no_kernel_extension_landed_event(self) -> None:
        self.assertEqual(self._events("kernel_extension_landed"), [])

    def test_no_kernel_override_used_event(self) -> None:
        self.assertEqual(
            [
                e for e in self._events("veto_triggered")
                if e.get("reason_code") == "kernel_override_used"
            ],
            [],
        )

    def test_block_is_audited(self) -> None:
        """Teeth for the two assertions above: the rail IS writing."""
        blocked = [
            e for e in self._events("veto_triggered")
            if e.get("reason_code") == "kernel_edit_blocked"
        ]
        self.assertEqual(len(blocked), 1)


class AckOnlyIsNotAGrant(_GrantPathBase):
    """Half an override is no override (both env vars are required)."""

    def test_ack_without_reason_blocks(self) -> None:
        proc = self._run_hook({"CEO_KERNEL_OVERRIDE_ACK": "I-ACCEPT"})
        out = json.loads(proc.stdout.strip())
        self.assertEqual(out.get("decision"), "block")
        self.assertEqual(self._events("kernel_extension_landed"), [])

    def test_wrong_ack_token_blocks(self) -> None:
        proc = self._run_hook(
            {
                "CEO_KERNEL_OVERRIDE": _OVERRIDE_REASON,
                "CEO_KERNEL_OVERRIDE_ACK": "i-accept",
            }
        )
        out = json.loads(proc.stdout.strip())
        self.assertEqual(out.get("decision"), "block")
        self.assertEqual(self._events("kernel_extension_landed"), [])


class DeadBranchRegressionGuard(TestEnvContext):
    """Pin the SHAPE that made the grant audit unreachable.

    ``main()`` must not go back to deriving the grant from its own egress
    JSON. These are in-process, on the pure surfaces.
    """

    def test_allow_egress_carries_no_decision_key(self) -> None:
        """The premise of the dead branch, asserted directly."""
        out = json.loads(MOD._emit_allow("hello"))
        self.assertNotIn("decision", out)
        self.assertNotIn("decision", json.loads(MOD._emit_allow()))

    def test_is_override_grant_is_true_for_a_granted_kernel_edit(self) -> None:
        target = self.project_dir / _KERNEL_REL
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"x\n")
        env = {
            "CEO_KERNEL_OVERRIDE": _OVERRIDE_REASON,
            "CEO_KERNEL_OVERRIDE_ACK": "I-ACCEPT",
        }
        self.assertTrue(
            MOD._is_override_grant(
                tool_name="Edit",
                file_path=str(target),
                repo_root=self.project_dir,
                env=env,
            )
        )
        # ... and the decision it drives is an allow with no decision key.
        out = json.loads(
            MOD.decide(
                tool_name="Edit",
                file_path=str(target),
                repo_root=self.project_dir,
                env=env,
            )
        )
        self.assertNotIn("decision", out)

    def test_is_override_grant_false_without_override(self) -> None:
        target = self.project_dir / _KERNEL_REL
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"x\n")
        self.assertFalse(
            MOD._is_override_grant(
                tool_name="Edit",
                file_path=str(target),
                repo_root=self.project_dir,
                env={},
            )
        )

    def test_is_override_grant_false_for_non_kernel_path(self) -> None:
        target = self.project_dir / "README.md"
        target.write_bytes(b"x\n")
        self.assertFalse(
            MOD._is_override_grant(
                tool_name="Edit",
                file_path=str(target),
                repo_root=self.project_dir,
                env={
                    "CEO_KERNEL_OVERRIDE": _OVERRIDE_REASON,
                    "CEO_KERNEL_OVERRIDE_ACK": "I-ACCEPT",
                },
            )
        )

    def test_is_override_grant_false_for_non_edit_tool(self) -> None:
        target = self.project_dir / _KERNEL_REL
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(b"x\n")
        self.assertFalse(
            MOD._is_override_grant(
                tool_name="Read",
                file_path=str(target),
                repo_root=self.project_dir,
                env={
                    "CEO_KERNEL_OVERRIDE": _OVERRIDE_REASON,
                    "CEO_KERNEL_OVERRIDE_ACK": "I-ACCEPT",
                },
            )
        )


class FieldHelperTests(TestEnvContext):
    """The two field-value helpers, incl. the missing-file case."""

    def test_file_sha256_matches_hashlib(self) -> None:
        f = self.project_dir / "a.bin"
        f.write_bytes(b"abc\n")
        self.assertEqual(
            MOD._file_sha256(str(f)), hashlib.sha256(b"abc\n").hexdigest()
        )

    def test_file_sha256_is_empty_for_missing_file(self) -> None:
        """A Write of a NEW kernel file has no bytes yet — empty, not path."""
        missing = self.project_dir / "does-not-exist.py"
        self.assertEqual(MOD._file_sha256(str(missing)), "")

    def test_plan_id_falls_back_to_unknown(self) -> None:
        # Isolated audit log has no plan_transition for this session.
        self.assertEqual(MOD._resolve_plan_id_or_unknown(), "unknown")


class AssertionsHaveTeeth(TestEnvContext):
    """Mutation control: the field regexes must REJECT the old values.

    Inherits TestEnvContext even though these cases are pure regex checks:
    `check-test-env-hygiene.py` flags a bare `unittest.TestCase` in this tree
    as a `bare-testcase` violation regardless of what the body does, and the
    rule is right — a class that needs no isolation today acquires a case that
    does, and nothing re-checks. (Caught post-land: the W3-K ceremony's CI run
    had its Validate job cancelled by a superseding push, so the gate never
    spoke.)"""

    def test_sha_regex_rejects_a_path(self) -> None:
        self.assertIsNone(_SHA_RE.match(_KERNEL_REL))
        self.assertIsNone(_SHA_RE.match(_KERNEL_REL[:64]))
        self.assertIsNone(_SHA_RE.match("Z" * 64))

    def test_plan_id_regex_rejects_an_override_reason(self) -> None:
        self.assertIsNone(_PLAN_ID_RE.match(_OVERRIDE_REASON))
        self.assertIsNone(_PLAN_ID_RE.match("ADR-045-refactor"))

    def test_hook_under_test_is_this_packs_copy(self) -> None:
        """Guard against silently proving the OTHER copy."""
        self.assertTrue(HOOK_UNDER_TEST.is_file(), str(HOOK_UNDER_TEST))
        self.assertEqual(HOOK_UNDER_TEST.parent, _THIS.parents[1])
        self.assertEqual(
            Path(MOD.__file__).resolve(), HOOK_UNDER_TEST.resolve()
        )


if __name__ == "__main__":
    unittest.main()
