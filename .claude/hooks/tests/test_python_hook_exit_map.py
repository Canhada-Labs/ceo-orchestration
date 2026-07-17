"""PLAN-156-FOLLOWUP F6 (consensus C5) — structural exit-2 map, dual fail semantics.

## The bug class this pins shut

The grok blocking path in ``_python-hook.sh`` mapped an emitted deny to
exit 2 with an order-sensitive WHOLE-STDOUT case glob
(``*'"decision"'*'"deny"'*``). The S270 live-fire found it mis-fires:

* an ALLOW payload whose OTHER fields merely quote a deny shape (e.g. a
  reason naming the ``"deny"`` rule it consulted) exited 2 — a spurious
  block on grok;
* the dual failure (rejected adjacency-glob family): a first-occurrence
  substring/regex parser lets a decoy nested ``"decision": "allow"`` mask
  a real top-level deny — silently dropping an enforcement decision.

The fix (security-VETO direction, consensus C5): a STRUCTURAL top-level
JSON parse via the already-resolved ``$FOUND_PY``, with fail semantics in
BOTH directions:

  parse OK      -> the field governs (deny -> 2, else hook rc)
  parse FAILURE -> '"deny"' token present -> exit 2   (fail-CLOSED)
                -> no deny token          -> hook rc  (INFRA fail-open)
  NEVER "nonzero -> deny".

## Which copy is under test

Per the PLAN-156-FOLLOWUP staging protocol the shim resolves through
``CEO_FU_STAGED_ROOT`` (default
``.claude/plans/PLAN-156-FOLLOWUP/staged/root``) — ``_python-hook.sh`` is
canonical-guarded, so pre-ceremony these tests exercise the STAGED copy;
once the ceremony lands it the staged tree is gone and the same tests run
against the canonical file (post-ceremony canonical mode).
"""

from __future__ import annotations

import os
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Optional, Tuple

_HOOKS_DIR = Path(__file__).resolve().parent.parent
_REPO_ROOT = _HOOKS_DIR.parent.parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402


def _shim_under_test() -> Path:
    staged_root = os.environ.get(
        "CEO_FU_STAGED_ROOT",
        str(_REPO_ROOT / ".claude" / "plans" / "PLAN-156-FOLLOWUP" / "staged" / "root"),
    )
    staged = Path(staged_root) / ".claude" / "hooks" / "_python-hook.sh"
    if staged.is_file():
        return staged
    return _HOOKS_DIR / "_python-hook.sh"


# One generic stub: emits CEO_TEST_PAYLOAD verbatim and exits CEO_TEST_RC.
# Payloads live in the TEST (raw strings) so byte order is deterministic —
# the whole point is what the raw byte stream looks like to a substring
# parser vs a structural one.
_STUB_SOURCE = (
    "import os, sys\n"
    "sys.stdout.write(os.environ.get('CEO_TEST_PAYLOAD', ''))\n"
    "sys.exit(int(os.environ.get('CEO_TEST_RC', '0')))\n"
)


class _ExitMapBase(TestEnvContext):
    """Drive the shim under test with a payload-parameterized stub hook."""

    def _run(
        self,
        payload: str,
        hook_rc: int = 0,
        exit_map: Optional[str] = None,
    ) -> Tuple[int, str, str]:
        hooks_dir = self.project_dir / ".claude" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        shim_src = _shim_under_test()
        shim = hooks_dir / "_python-hook.sh"
        shim.write_text(shim_src.read_text(encoding="utf-8"), encoding="utf-8")
        shim.chmod(0o755)
        stub = hooks_dir / "payload_stub.py"
        stub.write_text(_STUB_SOURCE, encoding="utf-8")

        env = {k: v for k, v in os.environ.items() if v is not None}
        for key in (
            "CEO_HOOK_ADAPTER",
            "CLAUDE_HOOK_EVENT",
            "GROK_HOOK_EVENT",
            "CODEX_HOOK_EVENT",
            "CEO_HOOK_EXIT_MAP",
            "CEO_TEST_PAYLOAD",
            "CEO_TEST_RC",
        ):
            env.pop(key, None)
        # The mapping under test is the grok blocking path.
        env["CEO_HOOK_ADAPTER"] = "grok"
        env["GROK_HOOK_EVENT"] = "pre_tool_use"
        env["CEO_TEST_PAYLOAD"] = payload
        env["CEO_TEST_RC"] = str(hook_rc)
        if exit_map is not None:
            env["CEO_HOOK_EXIT_MAP"] = exit_map
        proc = subprocess.run(
            ["bash", str(shim), "payload_stub.py"],
            input="{}",
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
            cwd=str(self.project_dir),
        )
        return proc.returncode, proc.stdout, proc.stderr


class StructuralExitMapRegressionTest(_ExitMapBase):
    """The four consensus-C5 regressions, both fail directions."""

    def test_allow_with_quoted_deny_exits_0(self):
        """Regression 1 (the S270 spurious block): a VALID allow whose raw
        bytes contain '"decision"' ... '"deny"' in glob order. The old
        whole-stdout case glob exited 2 on this; the structural parse reads
        the top-level field: allow -> hook rc 0."""
        payload = (
            '{"decision": "allow", "suppressed_action": "deny",'
            ' "reason": "allow-with-quoted-deny"}\n'
        )
        # Old-bug precondition meta-asserts: both tokens present, glob order.
        self.assertIn('"decision"', payload)
        self.assertIn('"deny"', payload)
        self.assertLess(payload.index('"decision"'), payload.index('"deny"'))
        rc, out, err = self._run(payload)
        self.assertEqual(rc, 0, "structural parse must read the FIELD, not bytes: %s" % err)
        self.assertIn('"allow"', out)

    def test_decoy_allow_field_before_real_deny_exits_2(self):
        """Regression 2 (the rejected first-occurrence family): a decoy
        NESTED '"decision": "allow"' appears earlier in the byte stream than
        the real top-level deny. A first-match substring/regex parser reads
        allow -> exit 0 -> silently drops a real enforcement decision. The
        structural parse reads the TOP-LEVEL field: deny -> exit 2."""
        payload = '{"meta": {"decision": "allow"}, "decision": "deny"}\n'
        self.assertLess(payload.index('"allow"'), payload.index('"deny"'))
        rc, out, _ = self._run(payload)
        self.assertEqual(rc, 2, "a real top-level deny must never be masked by a decoy")

    def test_malformed_json_with_deny_token_exits_2(self):
        """Regression 3 (fail-CLOSED, the INPUT half of CLAUDE.md section 4):
        stdout the mapper cannot parse but that carries a deny token is
        never waved through."""
        payload = '{"decision": "deny"'  # unterminated — json.load raises
        rc, _, _ = self._run(payload)
        self.assertEqual(rc, 2, "unparseable deny-bearing output must fail CLOSED")

    def test_malformed_no_deny_token_keeps_hook_rc(self):
        """Regression 4 (INFRA fail-open preserved, never 'nonzero->deny'):
        garbage with no deny token falls through to the hook's own rc."""
        rc, _, _ = self._run("total garbage, not json\n", hook_rc=3)
        self.assertEqual(rc, 3, "infra failure must keep the hook rc (fail-OPEN)")
        self.assertNotEqual(rc, 2)
        # And a clean rc-0 garbage emitter stays 0 (no spurious block).
        rc, _, _ = self._run("still not json\n", hook_rc=0)
        self.assertEqual(rc, 0)


class StructuralExitMapContractTest(_ExitMapBase):
    """Contract sanity around the regressions (unchanged behaviors)."""

    def test_plain_deny_exits_2(self):
        rc, _, _ = self._run('{"decision": "deny", "reason": "x"}\n')
        self.assertEqual(rc, 2)

    def test_codex_shaped_permission_decision_deny_exits_2(self):
        payload = (
            '{"hookSpecificOutput": {"hookEventName": "PreToolUse",'
            ' "permissionDecision": "deny"}}\n'
        )
        rc, _, _ = self._run(payload)
        self.assertEqual(rc, 2)

    def test_block_vocabulary_rewrite_still_feeds_the_map(self):
        # The :447-448 whitespace-tolerant block->deny rewrite is upstream of
        # the parse; a legacy Claude-vocab block must still land as exit 2.
        rc, out, _ = self._run('{"decision" : "block", "reason": "legacy"}\n')
        self.assertEqual(rc, 2)
        self.assertIn('"deny"', out)
        self.assertNotIn('"block"', out)

    def test_exit_map_kill_switch_disables_the_mapping(self):
        rc, out, _ = self._run('{"decision": "deny"}\n', exit_map="0")
        self.assertEqual(rc, 0, "CEO_HOOK_EXIT_MAP=0 disables the exit half")
        self.assertIn('"deny"', out, "the decision itself still flows to stdout")

    def test_empty_stdout_nonzero_rc_passes_through(self):
        rc, _, _ = self._run("", hook_rc=7)
        self.assertEqual(rc, 7, "crash with empty stdout keeps the hook rc")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
