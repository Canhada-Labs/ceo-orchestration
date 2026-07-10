"""PLAN-155 Wave 1 — subprocess positive-control replay (debate A3).

THE CERTIFYING ARTIFACT for the "ENFORCED under codex" capability-matrix
rows (PLAN-153 Wave E doctrine, hardened per debate A3): the planted
violation classes are replayed as SUBPROCESSES on the BYTE-IDENTICAL
command line shipped in ``templates/codex/hooks.json`` —
``{{PROJECT_PATH}}`` substituted (the ONLY edit), then executed the way
codex-cli 0.139 executes a ``type: command`` hook: **argv-split from the
session cwd, no shell** (observed live; modeled with ``shlex.split``,
same as ``test_codex_templates.test_commands_execute_from_foreign_cwd``).
stdin = a RECORDED codex-cli 0.139.0 wire envelope. In-process
import-and-call replay is INSUFFICIENT — it would have stayed green
through the S254 dead gate (hooks that hard-import the claude adapter
while the registration promises codex enforcement).

Isolation is INSTALL-SHAPED: each test materializes the tree under test
into the isolated project (``.claude/hooks`` copied minus ``tests/``),
substitutes ``{{PROJECT_PATH}}`` with THAT project dir, and lets the
shipped command's own env prefix provide BOTH ``CEO_HOOK_ADAPTER=codex``
AND ``CLAUDE_PROJECT_DIR`` (S265 pair-rail P2#5: codex never sets
CLAUDE_PROJECT_DIR, so the registration must) — so the replay certifies
the rendered-install resolution end-to-end, independent of this repo's
live sentinel state.

Violation classes (plan §Wave 1 / §Success criteria):

  (a) unsentineled write to a canonical path → ``check_canonical_edit.py``
      → deny, reason class ``CANONICAL-EDIT-BLOCKED``
  (b) destructive bash (``rm -rf`` class)    → ``check_bash_safety.py``
      → deny, reason class ``destructive``
  (c) illegal plan-status transition (new plan file born ``status: done``
      with no ``completed_at`` — blocked by ``decide_write``,
      PLAN-SCHEMA §4) → ``check_plan_edit.py`` → deny, reason class
      ``PLAN-LIFECYCLE``
  (d) S265 pair-rail P1#3 — MULTI-FILE apply_patch smuggle: a benign
      first op plus a LATER op hitting a guarded surface must deny on
      the canonical, kernel, and plan rails.

Per class (a)-(c), two controls:

  - NEGATIVE (benign envelope → NOT denied): proves the rail
    discriminates, not blanket-denies.
  - MALFORMED-envelope pair asserting the PLAN-152 C4 split:
      * INFRASTRUCTURE side — non-JSON stdin → fail-OPEN (rc 0, no deny;
        on the codex wire a foreign/absent decision line is ignored =
        allow, verified `e2-garbage`/`e2-foreign` transcripts).
      * INPUT side — a well-formed codex envelope whose SECURITY-RELEVANT
        payload is unparseable or recognizably cross-harness →
        fail-CLOSED deny (the ``_e3`` whole-command-gate precedent,
        PLAN-152 debate C4; PLAN-155 debate A2).

Landing-order note: this file lives in the SENT-CX-A (wave-1) batch but
READS ``templates/codex/hooks.json`` (wave-2, unguarded L2). Wave 2 lands
templates BEFORE or WITH the wave-1 batch commit that adds this test —
a missing template is a hard FAIL here (A4: never skip-to-green), named
in ``PLAN-155/staged/MANIFEST-A.md``.

Env discipline: ``TestEnvContext`` isolation; the subprocess env derives
from the isolated ``os.environ`` and ``CEO_HOOK_ADAPTER`` /
``CLAUDE_PROJECT_DIR`` are POPPED — the shipped command line's own
``env`` prefix (inside the trust-hashed command string) must supply
both; if that prefix stopped working, this suite goes RED.
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
import subprocess
import unittest
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import sys

_HOOKS_DIR = Path(__file__).resolve().parent.parent
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

#: Repo root (tests → hooks → .claude → root). In the assembled tree the
#: shipped registration template lives at templates/codex/hooks.json.
_REPO_ROOT = Path(__file__).resolve().parents[3]
_TEMPLATE = _REPO_ROOT / "templates" / "codex" / "hooks.json"

_FIXTURES_IN = (
    Path(__file__).resolve().parent / "fixtures" / "adapters" / "codex" / "in"
)

_PLACEHOLDER = "{{PROJECT_PATH}}"

#: hook script → (registration matcher it must be found under, deny class)
_CLASSES: Dict[str, Dict[str, str]] = {
    "canonical": {
        "script": "check_canonical_edit.py",
        "matcher": "apply_patch|Edit|Write",
        "reason_class": "CANONICAL-EDIT-BLOCKED",
    },
    "bash": {
        "script": "check_bash_safety.py",
        "matcher": "^Bash$",
        "reason_class": "destructive",
    },
    "plan": {
        "script": "check_plan_edit.py",
        "matcher": "apply_patch|Edit|Write",
        "reason_class": "PLAN-LIFECYCLE",
    },
    "kernel": {
        "script": "check_arbitration_kernel.py",
        "matcher": "apply_patch|Edit|Write",
        "reason_class": "ARBITRATION-KERNEL-BLOCKED",
    },
}

# New plan file written directly as `done` WITHOUT completed_at — the
# illegal plan-lifecycle write `decide_write` blocks (PLAN-SCHEMA §4).
_ILLEGAL_PLAN_CONTENT = (
    "---\n"
    "id: PLAN-992\n"
    "title: Positive control plan\n"
    "status: done\n"
    "---\n"
    "\n"
    "positive-control body\n"
)


def _apply_patch_text(sections: List[Tuple[str, str, List[str]]]) -> str:
    """apply_patch ``tool_input.command`` in the RECORDED 0.139 grammar.

    ``sections`` = ordered [(verb, path, body_lines)] — multi-file patches
    (the P1#3 smuggle class) are just multiple sections.
    """
    lines = ["*** Begin Patch"]
    for verb, path, body_lines in sections:
        lines.append("*** {0} File: {1}".format(verb, path))
        lines.extend(body_lines)
    lines.append("*** End Patch")
    return "\n".join(lines) + "\n"


class CodexPositiveControlsTest(TestEnvContext):
    """Subprocess replay on the SHIPPED hooks.json command line."""

    # ------------------------------------------------------------------
    # template plumbing
    # ------------------------------------------------------------------

    def _template_commands(self) -> Dict[str, Dict[str, str]]:
        """Extract the shipped command string per violation class.

        FAILS (never skips) when the template is missing — the A3
        replay certifies the SHIPPED registration, so certifying
        without it would be the vacuous-green class (A4).
        """
        self.assertTrue(
            _TEMPLATE.is_file(),
            "templates/codex/hooks.json missing at {0} — the A3 positive "
            "controls replay the SHIPPED command line, so wave-2 templates "
            "must land before/with this test (MANIFEST-A landing order)".format(
                _TEMPLATE
            ),
        )
        registration = json.loads(_TEMPLATE.read_text(encoding="utf-8"))
        pre = registration.get("hooks", {}).get("PreToolUse", [])
        found: Dict[str, Dict[str, str]] = {}
        for klass, meta in _CLASSES.items():
            for entry in pre:
                if entry.get("matcher") != meta["matcher"]:
                    continue
                for h in entry.get("hooks", []):
                    cmd = h.get("command", "")
                    if meta["script"] in cmd:
                        found[klass] = {"command": cmd}
        missing = sorted(set(_CLASSES) - set(found))
        self.assertFalse(
            missing,
            "shipped hooks.json registers no command for class(es) {0} "
            "under the expected matcher — enforcement claim would be "
            "vacuous".format(missing),
        )
        return found

    def _shipped_argv(self, klass: str) -> Tuple[str, List[str]]:
        """(raw_template_command, argv) for a class.

        The ONLY substitution is ``{{PROJECT_PATH}}`` → the isolated
        INSTALLED project dir (see ``_install``). Everything else is
        byte-identical to the shipped string — including the
        ``env CEO_HOOK_ADAPTER=codex CLAUDE_PROJECT_DIR="..."`` prefix
        (S265 P2#5) — and execution models codex 0.139's observed
        argv-split-no-shell semantics via ``shlex.split``.
        """
        raw = self._template_commands()[klass]["command"]
        self.assertIn(
            "env CEO_HOOK_ADAPTER=codex",
            raw,
            "shipped command must select the codex adapter on its own "
            "command line (part of the trust-hashed string): " + raw,
        )
        self.assertIn(
            'CLAUDE_PROJECT_DIR="' + _PLACEHOLDER + '"',
            raw,
            "S265 P2#5: codex never sets CLAUDE_PROJECT_DIR — the shipped "
            "command must carry it explicitly: " + raw,
        )
        self.assertIn(_PLACEHOLDER + "/.claude/hooks/_python-hook.sh", raw)
        executable = raw.replace(_PLACEHOLDER, str(self.project_dir))
        self.assertNotIn("{{", executable, "unsubstituted placeholder left")
        return raw, shlex.split(executable)

    # ------------------------------------------------------------------
    # isolated INSTALL + project layout + envelopes
    # ------------------------------------------------------------------

    def _install(self) -> None:
        """Materialize an install-shaped isolated project.

        ``.claude/hooks`` (the tree under test, minus ``tests/``) is
        copied into the isolated project so the shipped command resolves
        shim + hooks + `_lib` at the INSTALLED location — the replay is
        then independent of this repo's live sentinel/plan state.
        """
        p = self.project_dir
        src = _REPO_ROOT / ".claude" / "hooks"
        dst = p / ".claude" / "hooks"
        if not dst.exists():
            shutil.copytree(
                str(src),
                str(dst),
                ignore=shutil.ignore_patterns("tests", "__pycache__"),
            )
        (p / ".claude" / "team.md").write_text("team\n", encoding="utf-8")
        (p / ".claude" / "plans").mkdir(parents=True, exist_ok=True)
        (p / "src").mkdir(exist_ok=True)
        (p / "src" / "app.ts").write_text("// benign\n", encoding="utf-8")

    def _env(self) -> Dict[str, str]:
        """Subprocess env from the ISOLATED os.environ.

        ``CEO_HOOK_ADAPTER`` and ``CLAUDE_PROJECT_DIR`` are POPPED — the
        shipped command line's own ``env`` prefix must supply both
        (byte-identity requirement, A3 + S265 P2#5). Sentinel plaintext
        bypass mirrors test_check_canonical_edit.py — it exercises the
        Approved-By/Scope path, never GPG; it does NOT relax the
        no-sentinel deny these tests assert.
        """
        env = {k: v for k, v in os.environ.items() if v is not None}
        env.pop("CEO_HOOK_ADAPTER", None)
        env.pop("CLAUDE_PROJECT_DIR", None)
        env.setdefault("CEO_SENTINEL_UNLOCK", "PLAN-091-test-fixture")
        env.setdefault("CEO_SENTINEL_UNLOCK_ACK", "I-ACCEPT")
        return env

    def _run_shipped(self, klass: str, stdin_text: str) -> Tuple[int, str, str]:
        _, argv = self._shipped_argv(klass)
        proc = subprocess.run(
            argv,
            input=stdin_text,
            capture_output=True,
            text=True,
            timeout=60,
            env=self._env(),
            cwd=str(self.project_dir),
        )
        return proc.returncode, proc.stdout, proc.stderr

    def _codex_envelope(
        self,
        fixture: str,
        command: Optional[str] = None,
        tool_name: Optional[str] = None,
        tool_input: Optional[Dict[str, object]] = None,
    ) -> str:
        """An envelope derived from a RECORDED 0.139 fixture.

        Only the violation payload (``tool_input`` / ``tool_name``) and
        ``cwd`` are substituted; every other byte of the recorded wire
        shape is preserved (debate A12: fixtures follow the pin).
        """
        src = _FIXTURES_IN / fixture
        self.assertTrue(
            src.is_file(),
            "recorded codex fixture missing: {0} (A4: fixture-less suites "
            "must FAIL, not skip)".format(src),
        )
        payload = json.loads(src.read_text(encoding="utf-8"))
        payload["cwd"] = str(self.project_dir)
        if command is not None:
            payload["tool_input"]["command"] = command
        if tool_name is not None:
            payload["tool_name"] = tool_name
        if tool_input is not None:
            payload["tool_input"] = tool_input
        return json.dumps(payload)

    def _payloads(self) -> Dict[str, Dict[str, str]]:
        return {
            "canonical": {
                "violation": self._codex_envelope(
                    "pre_tool_use.apply_patch.update-file.json",
                    _apply_patch_text(
                        [("Update", ".claude/team.md", ["@@", "-team", "+tampered"])]
                    ),
                ),
                # benign: the recorded patch targets notes.txt (unguarded)
                "benign": self._codex_envelope(
                    "pre_tool_use.apply_patch.update-file.json"
                ),
                # INPUT side of C4: an apply_patch payload the guard
                # cannot parse (no recognizable file operations).
                "malformed_input": self._codex_envelope(
                    "pre_tool_use.apply_patch.update-file.json",
                    "*** Begin Garbage\nnot a recognizable patch\n",
                ),
            },
            "bash": {
                "violation": self._codex_envelope(
                    "pre_tool_use.bash.echo.json", "rm -rf ~"
                ),
                "benign": self._codex_envelope("pre_tool_use.bash.echo.json"),
                # INPUT side of C4 for the bash rail: a recognizably
                # CROSS-HARNESS envelope (Claude-native tool_name +
                # Claude-native input keys on the codex wire — debate A2).
                "malformed_input": self._codex_envelope(
                    "pre_tool_use.bash.echo.json",
                    tool_name="Edit",
                    tool_input={
                        "file_path": "src/app.ts",
                        "old_string": "a",
                        "new_string": "b",
                    },
                ),
            },
            "plan": {
                "violation": self._codex_envelope(
                    "pre_tool_use.apply_patch.add-file.json",
                    _apply_patch_text(
                        [(
                            "Add",
                            ".claude/plans/PLAN-992-positive-control.md",
                            ["+" + ln for ln in _ILLEGAL_PLAN_CONTENT.splitlines()],
                        )]
                    ),
                ),
                "benign": self._codex_envelope(
                    "pre_tool_use.apply_patch.add-file.json"
                ),
                "malformed_input": self._codex_envelope(
                    "pre_tool_use.apply_patch.add-file.json",
                    "*** Begin Garbage\nnot a recognizable patch\n",
                ),
            },
        }

    def _multifile_payloads(self) -> Dict[str, str]:
        """S265 P1#3: benign FIRST op + guarded LATER op, one patch."""
        benign = ("Add", "notes-multi.txt", ["+benign first op"])
        return {
            "canonical": self._codex_envelope(
                "pre_tool_use.apply_patch.update-file.json",
                _apply_patch_text(
                    [benign, ("Update", ".claude/team.md", ["@@", "-team", "+tampered"])]
                ),
            ),
            "kernel": self._codex_envelope(
                "pre_tool_use.apply_patch.update-file.json",
                _apply_patch_text(
                    [benign, ("Update", ".claude/hooks/audit_log.py", ["@@", "-x", "+y"])]
                ),
            ),
            "plan": self._codex_envelope(
                "pre_tool_use.apply_patch.add-file.json",
                _apply_patch_text(
                    [
                        benign,
                        (
                            "Add",
                            ".claude/plans/PLAN-992-positive-control.md",
                            ["+" + ln for ln in _ILLEGAL_PLAN_CONTENT.splitlines()],
                        ),
                    ]
                ),
            ),
        }

    # ------------------------------------------------------------------
    # shape assertions (codex wire, verified semantics 0.139)
    # ------------------------------------------------------------------

    def _last_json(self, out: str) -> Dict[str, object]:
        stripped = out.strip()
        self.assertTrue(stripped, "empty stdout where a decision was required")
        return json.loads(stripped.splitlines()[-1])

    def _assert_deny(
        self, klass: str, rc: int, out: str, err: str, reason_class: str
    ) -> None:
        self.assertEqual(
            rc, 0, msg="rc={0} out={1!r} err={2!r}".format(rc, out, err)
        )
        parsed = self._last_json(out)
        hso = parsed.get("hookSpecificOutput") or {}
        self.assertEqual(
            hso.get("hookEventName"), "PreToolUse", msg="class=%s out=%s" % (klass, out)
        )
        self.assertEqual(
            hso.get("permissionDecision"),
            "deny",
            msg="class={0}: shipped command line did NOT deny the planted "
            "violation (S254 dead-gate class). out={1} err={2}".format(
                klass, out, err
            ),
        )
        self.assertIn(
            reason_class,
            str(hso.get("permissionDecisionReason") or ""),
            msg=out,
        )

    def _assert_not_denied(self, klass: str, rc: int, out: str, err: str) -> None:
        self.assertEqual(
            rc, 0, msg="rc={0} out={1!r} err={2!r}".format(rc, out, err)
        )
        stripped = out.strip()
        if not stripped:
            return  # silent allow is a legal codex allow
        parsed = json.loads(stripped.splitlines()[-1])
        hso = parsed.get("hookSpecificOutput") or {}
        self.assertNotEqual(
            hso.get("permissionDecision"),
            "deny",
            msg="class={0}: benign envelope denied — blanket-deny is not "
            "enforcement. out={1}".format(klass, out),
        )
        # A Claude-shaped block line would be foreign JSON on the codex
        # wire (= silent fail-open) AND evidence of a mis-dispatched
        # adapter; assert its absence explicitly.
        self.assertNotEqual(parsed.get("decision"), "block", msg=out)

    # ------------------------------------------------------------------
    # the planted violations (the certifying replay)
    # ------------------------------------------------------------------

    def test_planted_violations_denied_on_shipped_command_line(self) -> None:
        self._install()
        payloads = self._payloads()
        for klass in ("canonical", "bash", "plan"):
            with self.subTest(klass=klass):
                rc, out, err = self._run_shipped(klass, payloads[klass]["violation"])
                self._assert_deny(klass, rc, out, err, _CLASSES[klass]["reason_class"])

    def test_multifile_patch_smuggled_guarded_op_denied(self) -> None:
        """S265 pair-rail P1#3: a benign first op must not smuggle a
        later op into a guarded path — canonical, kernel, and plan rails,
        each on its own shipped command line."""
        self._install()
        payloads = self._multifile_payloads()
        for klass in ("canonical", "kernel", "plan"):
            with self.subTest(klass=klass):
                rc, out, err = self._run_shipped(klass, payloads[klass])
                self._assert_deny(klass, rc, out, err, _CLASSES[klass]["reason_class"])

    def test_negative_controls_benign_envelopes_not_denied(self) -> None:
        self._install()
        payloads = self._payloads()
        for klass in ("canonical", "bash", "plan"):
            with self.subTest(klass=klass):
                rc, out, err = self._run_shipped(klass, payloads[klass]["benign"])
                self._assert_not_denied(klass, rc, out, err)

    # ------------------------------------------------------------------
    # malformed-envelope controls — the PLAN-152 C4 split
    # ------------------------------------------------------------------

    def test_malformed_stdin_is_infrastructure_fails_open(self) -> None:
        """Non-JSON stdin is an INFRASTRUCTURE failure (SPEC/v1 §4):
        the hook must NOT deny and must NOT crash the harness (rc 0).
        On the codex wire the resulting legacy/foreign line is ignored
        (verified fail-open, e2-garbage transcript)."""
        self._install()
        for klass in ("canonical", "bash", "plan"):
            with self.subTest(klass=klass):
                rc, out, err = self._run_shipped(klass, "this is { not json\n")
                self.assertEqual(
                    rc, 0, msg="rc={0} out={1!r} err={2!r}".format(rc, out, err)
                )
                self.assertNotIn('"permissionDecision": "deny"', out, msg=out)

    def test_unparseable_security_input_fails_closed(self) -> None:
        """Well-formed envelope, unparseable/cross-harness SECURITY
        payload → INPUT class per PLAN-152 C4 → deny (fail-CLOSED),
        with the C4/A2 reason class on the wire."""
        self._install()
        payloads = self._payloads()
        expected_reason = {
            "canonical": "PLAN-152 C4",
            "plan": "PLAN-152 C4",
            "bash": "cross-harness",
        }
        for klass in ("canonical", "bash", "plan"):
            with self.subTest(klass=klass):
                rc, out, err = self._run_shipped(
                    klass, payloads[klass]["malformed_input"]
                )
                self.assertEqual(
                    rc, 0, msg="rc={0} out={1!r} err={2!r}".format(rc, out, err)
                )
                parsed = self._last_json(out)
                hso = parsed.get("hookSpecificOutput") or {}
                self.assertEqual(
                    hso.get("permissionDecision"),
                    "deny",
                    msg="class={0}: unparseable security input was waved "
                    "through (C4 requires fail-CLOSED on INPUT). out={1}".format(
                        klass, out
                    ),
                )
                self.assertIn(
                    expected_reason[klass],
                    str(hso.get("permissionDecisionReason") or ""),
                    msg=out,
                )

    # ------------------------------------------------------------------
    # registration sanity (cheap, rides the same template read)
    # ------------------------------------------------------------------

    def test_shipped_commands_reference_existing_shim_and_hooks(self) -> None:
        """The substituted command resolves to real on-disk files at the
        INSTALLED location — a renamed shim/hook would otherwise die only
        at live-fire time."""
        self._install()
        for klass, meta in _CLASSES.items():
            with self.subTest(klass=klass):
                raw, argv = self._shipped_argv(klass)
                installed_hooks = self.project_dir / ".claude" / "hooks"
                self.assertTrue((installed_hooks / "_python-hook.sh").is_file())
                self.assertTrue((installed_hooks / meta["script"]).is_file())
                self.assertEqual(
                    raw.count(_PLACEHOLDER),
                    2,
                    "exactly two PROJECT_PATH substitution points "
                    "(CLAUDE_PROJECT_DIR assignment + shim path): " + raw,
                )


if __name__ == "__main__":
    unittest.main()
