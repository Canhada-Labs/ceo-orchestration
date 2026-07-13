"""PLAN-156 Wave 2 — hermetic CI teeth for the decision→exit chokepoint.

## What class of bug this exists to make impossible

On Grok Build, a PreToolUse hook denies by writing ``{"decision":"deny"}``
to stdout **and** (belt-and-suspenders) exiting 2. Two independent failure
modes were live before PLAN-156:

1. **vocabulary-half (the load-bearing one).** Grok does not know the word
   ``block``. Our legacy hooks (``check_codex_filewrite.py``) hardcode
   ``{"decision": "block"}``. On grok that is *malformed hook output* →
   hook failure → **fail-OPEN — and exit 2 does NOT rescue it** (probe P5:
   block+exit-2 ⇒ the tool RAN). The shim rewrites ``block`` → ``deny``
   under ``CEO_HOOK_ADAPTER=grok``. This rewrite is the ENFORCEMENT
   mechanism on grok; it is NOT disableable by ``CEO_HOOK_EXIT_MAP=0``.
2. **exit-half.** A deny-shaped stdout with exit 0. On grok the JSON deny
   blocks on its own (probe P2), so this is belt-and-suspenders — but a
   future grok release tightening the docs.x.ai "deny REQUIRES exit 2"
   rule is covered by mapping deny→exit 2.

## ADAPTER-AWARE (grok-gated), per the plan's lacuna-(h) fork

The plan's Wave-2 conditional: "UNCONDITIONAL mapping SAFE iff lacuna (h)
confirms exit 2 is INERT on Codex; if not, adapter-aware." Lacuna (h) found
exit 2 is NOT inert on Codex — it is an ACTIVE deny on PreToolUse (probe
P9a). So both halves fire ONLY under ``CEO_HOOK_ADAPTER=grok``; Claude and
Codex preserve the hook's own exit code byte-for-byte (their JSON already
blocks with exit 0). Remapping them would change an observable with zero
enforcement gain while breaking every test that pins "deny → exit 0".

## Why hermetic (no grok, no codex binary)

These tests drive the SHIM directly with stub hooks and assert its
observable contract. They ride the standard hooks suite → RED-on-absence in
CI. "Impossible to forget" is a test, not reviewer vigilance (debate C2).
"""

from __future__ import annotations

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

_SHIM = _HOOKS_DIR / "_python-hook.sh"

_STUBS: Dict[str, str] = {
    "deny_grok": (
        "import json, sys\n"
        "sys.stdout.write(json.dumps({'decision': 'deny', 'reason': 'STUB-DENY'}) + '\\n')\n"
    ),
    "block_claude": (
        "import json, sys\n"
        "sys.stdout.write(json.dumps({'decision': 'block', 'reason': 'STUB-BLOCK'}) + '\\n')\n"
    ),
    "deny_codex": (
        "import json, sys\n"
        "sys.stdout.write(json.dumps({'hookSpecificOutput': {'hookEventName': 'PreToolUse',\n"
        "    'permissionDecision': 'deny', 'permissionDecisionReason': 'STUB-DENY'}}) + '\\n')\n"
    ),
    "allow": (
        "import json, sys\n"
        "sys.stdout.write(json.dumps({'decision': 'allow'}) + '\\n')\n"
    ),
    "allow_empty": (
        "import json, sys\n"
        "sys.stdout.write(json.dumps({}) + '\\n')\n"
    ),
    "crash_import": (
        "import sys\n"
        "raise ImportError('simulated missing dependency')\n"
    ),
    "crash_nonzero": (
        "import sys\n"
        "sys.stderr.write('[stub] infra failure\\n')\n"
        "sys.exit(7)\n"
    ),
}


class _ChokepointBase(TestEnvContext):
    """Drive the real shim with stub hooks in an isolated project."""

    def _write_stub(self, name: str) -> str:
        hooks_dir = self.project_dir / ".claude" / "hooks"
        hooks_dir.mkdir(parents=True, exist_ok=True)
        # Copy the shim into the isolated project (the repo hooks dir is
        # read-only in CI) and put stubs beside it — same bytes, no repo write.
        shim_copy = hooks_dir / "_python-hook.sh"
        shim_copy.write_text(_SHIM.read_text(encoding="utf-8"), encoding="utf-8")
        shim_copy.chmod(0o755)
        stub = hooks_dir / "{0}.py".format(name)
        stub.write_text(_STUBS[name], encoding="utf-8")
        return str(shim_copy)

    def _run(
        self,
        stub: str,
        adapter: Optional[str] = None,
        event: Optional[str] = None,
        exit_map: Optional[str] = None,
    ) -> Tuple[int, str, str]:
        shim = self._write_stub(stub)
        env = {k: v for k, v in os.environ.items() if v is not None}
        for key in ("CEO_HOOK_ADAPTER", "CLAUDE_HOOK_EVENT", "GROK_HOOK_EVENT",
                    "CODEX_HOOK_EVENT", "CEO_HOOK_EXIT_MAP"):
            env.pop(key, None)
        if adapter is not None:
            env["CEO_HOOK_ADAPTER"] = adapter
        if event is not None:
            # grok spells events snake_case; the shim reads GROK_HOOK_EVENT too.
            env["CLAUDE_HOOK_EVENT"] = event
            env["GROK_HOOK_EVENT"] = event
        if exit_map is not None:
            env["CEO_HOOK_EXIT_MAP"] = exit_map
        proc = subprocess.run(
            ["bash", shim, "{0}.py".format(stub)],
            input="{}",
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
            cwd=str(self.project_dir),
        )
        return proc.returncode, proc.stdout, proc.stderr


class GrokExitMappingTest(_ChokepointBase):
    """Under CEO_HOOK_ADAPTER=grok: an EMITTED deny exits 2; a crash does not."""

    def test_grok_vocabulary_deny_exits_2(self):
        rc, out, _ = self._run("deny_grok", adapter="grok")
        self.assertEqual(rc, 2, "emitted deny must map to exit 2 under grok")
        self.assertIn('"deny"', out)

    def test_codex_vocabulary_deny_exits_2_under_grok(self):
        # A legacy codex-shaped hook that routed through the shim under grok.
        rc, out, _ = self._run("deny_codex", adapter="grok")
        self.assertEqual(rc, 2)

    def test_allow_exits_0(self):
        rc, out, _ = self._run("allow", adapter="grok")
        self.assertEqual(rc, 0)
        self.assertIn('"allow"', out)

    def test_empty_decision_exits_0(self):
        rc, _, _ = self._run("allow_empty", adapter="grok")
        self.assertEqual(rc, 0, "'{}' is a schema-compliant allow")

    def test_import_crash_is_fail_OPEN_not_deny(self):
        """The infra half of CLAUDE.md §4 — asserted, not assumed.

        A hook that dies with NO decision on stdout must NOT come back as
        exit 2. If it did, every ImportError / missing file / timeout would
        BLOCK the user's session — the exact failure mode the fail-open
        doctrine exists to prevent, and the reason the mapping is
        decision-derived rather than exit-code-derived.
        """
        rc, out, _ = self._run("crash_import", adapter="grok")
        self.assertNotEqual(rc, 2, "an infra crash must never be mapped to a deny")
        self.assertNotIn('"deny"', out)
        self.assertNotIn('"block"', out)

    def test_nonzero_without_decision_is_fail_OPEN(self):
        rc, out, _ = self._run("crash_nonzero", adapter="grok")
        self.assertNotEqual(rc, 2)
        self.assertEqual(rc, 7, "the hook's own exit code passes through unchanged")

    def test_exit_map_kill_switch_disables_only_the_exit_half(self):
        # CEO_HOOK_EXIT_MAP=0 turns off exit-2 but the vocabulary rewrite
        # (block->deny) MUST still fire — it is the essential grok fix.
        rc, out, _ = self._run("block_claude", adapter="grok", exit_map="0")
        self.assertEqual(rc, 0, "exit-2 half disabled")
        self.assertIn('"deny"', out, "vocabulary rewrite still fires (not disableable)")
        self.assertNotIn('"block"', out)


class GrokAdapterAutoDetectTest(_ChokepointBase):
    """Pair-rail S269 P1 #1: the shim auto-selects the grok adapter when grok's
    runner vars are present and CEO_HOOK_ADAPTER is unset.

    THE single-surface fix. The armed `.claude/settings.json` hooks do NOT
    carry `CEO_HOOK_ADAPTER=grok` (they are the shared Claude registrations),
    but grok injects `GROK_HOOK_EVENT`/`GROK_SESSION_ID` on every hook. Without
    auto-detect, the hooks would run as the CLAUDE adapter, misparse the grok
    camelCase wire, and fail-OPEN silently. This proves the shim promotes to
    grok so the block→deny rewrite + exit-2 mapping actually fire.
    """

    def test_grok_runner_var_selects_grok_adapter(self):
        # block_claude emits Claude vocabulary; if the shim auto-detected grok,
        # it rewrites to deny + exits 2. If it defaulted to claude (the bug),
        # the block would pass through and exit 0.
        shim = self._write_stub("block_claude")
        env = {k: v for k, v in os.environ.items() if v is not None}
        for key in ("CEO_HOOK_ADAPTER", "CLAUDE_HOOK_EVENT", "GROK_HOOK_EVENT",
                    "CODEX_HOOK_EVENT", "CEO_HOOK_EXIT_MAP"):
            env.pop(key, None)
        env["GROK_HOOK_EVENT"] = "pre_tool_use"   # grok-injected; adapter UNSET
        env["GROK_SESSION_ID"] = "auto-detect-test"
        proc = subprocess.run(
            ["bash", shim, "block_claude.py"], input="{}", capture_output=True,
            text=True, timeout=30, env=env, cwd=str(self.project_dir),
        )
        self.assertEqual(proc.returncode, 2, "grok runner var must auto-select the grok adapter")
        self.assertIn('"deny"', proc.stdout)
        self.assertNotIn('"block"', proc.stdout, "auto-detect failed → claude adapter → fail-open")

    def test_explicit_adapter_still_wins_over_autodetect(self):
        # An explicit CEO_HOOK_ADAPTER=codex must NOT be overridden by a stray
        # GROK_HOOK_EVENT (explicit intent wins).
        shim = self._write_stub("block_claude")
        env = {k: v for k, v in os.environ.items() if v is not None}
        for key in ("CLAUDE_HOOK_EVENT", "GROK_HOOK_EVENT", "CODEX_HOOK_EVENT",
                    "CEO_HOOK_EXIT_MAP"):
            env.pop(key, None)
        env["CEO_HOOK_ADAPTER"] = "codex"
        env["GROK_HOOK_EVENT"] = "pre_tool_use"
        proc = subprocess.run(
            ["bash", shim, "block_claude.py"], input="{}", capture_output=True,
            text=True, timeout=30, env=env, cwd=str(self.project_dir),
        )
        # codex path is not remapped → block preserved, exit 0.
        self.assertIn('"block"', proc.stdout, "explicit adapter must win over auto-detect")


class GrokVocabularyRewriteTest(_ChokepointBase):
    """The vocabulary half: `block` is not a word grok knows (probe P5)."""

    def test_block_is_rewritten_to_deny_under_grok(self):
        rc, out, _ = self._run("block_claude", adapter="grok")
        self.assertEqual(rc, 2)
        self.assertIn('"deny"', out, "grok fail-OPENs on an unrecognized decision word")
        self.assertNotIn(
            '"block"', out,
            "'block' on the grok wire is malformed output = fail-OPEN, EVEN WITH "
            "exit 2 (S269 probe P5) — the rewrite is the enforcement mechanism",
        )

    def test_block_rewrite_is_whitespace_tolerant(self):
        """Pair-rail S269 finding #3: a `"decision" : "block"` with a space
        BEFORE the colon must still be rewritten (a fixed-string substitution
        missed it → grok fail-OPEN on an unusual-but-valid deny shape)."""
        self.project_dir.joinpath(".claude", "hooks").mkdir(parents=True, exist_ok=True)
        # Register a stub that emits the awkward spacing directly.
        _STUBS["block_spaced"] = (
            "import sys\n"
            "sys.stdout.write('{\"decision\" : \"block\", \"reason\": \"x\"}' + '\\n')\n"
        )
        try:
            rc, out, _ = self._run("block_spaced", adapter="grok")
            self.assertEqual(rc, 2)
            self.assertIn('"deny"', out)
            self.assertNotIn('"block"', out, "whitespace-before-colon block slipped the rewrite")
        finally:
            _STUBS.pop("block_spaced", None)


class ClaudeCodexPreservedTest(_ChokepointBase):
    """Adapter != grok is byte-identical to the historical shim.

    This is the guard against a future UNCONDITIONAL regression: on Claude
    and Codex the hook's OWN exit code must pass through unchanged (their
    JSON already blocks with exit 0; lacuna (h) — exit-2 is a valid deny on
    codex, so nothing breaks in production, but pinning exit 0 keeps every
    existing codex/claude test green and proves the gate is adapter-aware).
    """

    def test_codex_deny_preserves_hook_exit_0(self):
        rc, out, _ = self._run("deny_codex", adapter="codex")
        self.assertEqual(rc, 0, "codex path must NOT be remapped (byte-identical)")
        self.assertIn('permissionDecision', out)

    def test_claude_block_preserves_hook_exit_0(self):
        rc, out, _ = self._run("block_claude", adapter="claude")
        self.assertEqual(rc, 0, "claude path must NOT be remapped")
        self.assertIn('"block"', out, "block is the CORRECT word on the claude wire")

    def test_unset_adapter_preserves_hook_exit_0(self):
        rc, out, _ = self._run("block_claude")
        self.assertEqual(rc, 0)
        self.assertIn('"block"', out)

    def test_codex_grok_named_deny_word_untouched_off_grok(self):
        # A hook that emits the grok `deny` word but runs under codex: still
        # not remapped (the gate is on the ADAPTER, not the word).
        rc, out, _ = self._run("deny_grok", adapter="codex")
        self.assertEqual(rc, 0)


class PassiveEventCarveOutTest(_ChokepointBase):
    """Grok passive events can never block — do not map their exits."""

    def test_post_tool_use_does_not_map_under_grok(self):
        rc, _, _ = self._run("deny_grok", adapter="grok", event="post_tool_use")
        self.assertNotEqual(
            rc, 2,
            "post_tool_use is passive on grok; a nonzero exit there is a hook "
            "FAILURE in the host's log, not a deny",
        )

    def test_stop_does_not_map_under_grok(self):
        rc, _, _ = self._run("deny_grok", adapter="grok", event="stop")
        self.assertNotEqual(rc, 2, "grok Stop is passive")

    def test_pre_tool_use_DOES_map_under_grok(self):
        rc, _, _ = self._run("deny_grok", adapter="grok", event="pre_tool_use")
        self.assertEqual(rc, 2, "pre_tool_use is THE blocking event on grok")

    def test_grok_event_var_wins_over_stale_claude_event(self):
        """Pair-rail S269 finding #4: under grok, GROK_HOOK_EVENT is
        authoritative. A stale/injected CLAUDE_HOOK_EVENT=post_tool_use must
        NOT mislabel a real grok pre_tool_use as passive and disable the
        chokepoint (which would fail-OPEN)."""
        shim = self._write_stub("deny_grok")
        env = {k: v for k, v in os.environ.items() if v is not None}
        for key in ("CEO_HOOK_ADAPTER", "CLAUDE_HOOK_EVENT", "GROK_HOOK_EVENT",
                    "CODEX_HOOK_EVENT", "CEO_HOOK_EXIT_MAP"):
            env.pop(key, None)
        env["CEO_HOOK_ADAPTER"] = "grok"
        env["CLAUDE_HOOK_EVENT"] = "post_tool_use"   # stale/injected passive
        env["GROK_HOOK_EVENT"] = "pre_tool_use"      # the real grok event
        proc = subprocess.run(
            ["bash", shim, "deny_grok.py"], input="{}", capture_output=True,
            text=True, timeout=30, env=env, cwd=str(self.project_dir),
        )
        self.assertEqual(
            proc.returncode, 2,
            "grok's own event var must win — else a stale CLAUDE_HOOK_EVENT "
            "disables the chokepoint and grok fail-OPENs",
        )


class RegisteredHookSurfaceTest(TestEnvContext):
    """Every registered python hook must route through the chokepoint.

    The grok rewrite + exit map only protect hooks the shim actually runs. A
    registration that invokes ``python3 <hook>.py`` DIRECTLY bypasses it —
    which is precisely how ``check_codex_filewrite.py`` shipped (settings
    line ~291 + the install template), emitting a Claude-vocabulary ``block``
    with exit 0: fail-OPEN under grok on BOTH halves. This test iterates the
    FULL registered-hook set in the live settings AND the install template,
    so a future direct registration reddens CI (debate C2).
    """

    _SETTINGS: List[Path] = [
        _HOOKS_DIR.parent / "settings.json",
        _HOOKS_DIR.parent.parent / "templates" / "settings" / "settings.base.json",
    ]

    def test_every_python_hook_registration_routes_through_the_shim(self):
        import json as _json

        for settings_path in self._SETTINGS:
            self.assertTrue(
                settings_path.is_file(),
                "missing settings surface {0} — a renamed/moved settings file "
                "must FAIL this gate, not silently skip it".format(settings_path),
            )
            data = _json.loads(settings_path.read_text(encoding="utf-8"))
            offenders: List[str] = []
            for event, groups in (data.get("hooks") or {}).items():
                for gi, group in enumerate(groups):
                    for hi, handler in enumerate(group.get("hooks", [])):
                        cmd = str(handler.get("command") or "")
                        if ".py" not in cmd:
                            continue  # inline `echo` breadcrumbs carry no decision
                        if "_python-hook.sh" in cmd:
                            continue
                        offenders.append(
                            "{0}[{1}][{2}]: {3}".format(event, gi, hi, cmd[:90])
                        )
            self.assertEqual(
                offenders, [],
                "{0}: python hook(s) registered WITHOUT the shim — they bypass the "
                "grok block→deny rewrite AND the decision→exit chokepoint, so their "
                "deny is a silent allow under grok (the S254 dead-gate class). "
                "Route them through _python-hook.sh: {1}".format(
                    settings_path.name, offenders,
                ),
            )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
