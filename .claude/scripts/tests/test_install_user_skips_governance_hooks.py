#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PLAN-122 WS-4 — install-ceremony tests.

Convention (matches test_install_sh_session_75_flags.py): subclass TestEnvContext
from _lib/testing.py; drive scripts/install.sh via subprocess; CEO_INSTALL_SKIP_SELF_SHA=1.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
# .claude/scripts/tests -> repo root (3 dirs up)
_REPO_ROOT = os.path.abspath(os.path.join(_HERE, os.pardir, os.pardir, os.pardir))
INSTALL_SH = os.path.join(_REPO_ROOT, "scripts", "install.sh")

# TestEnvContext lives under .claude/hooks
sys.path.insert(0, os.path.join(_REPO_ROOT, ".claude", "hooks"))
from _lib.testing import TestEnvContext  # noqa: E402


def _install_env():
    env = dict(os.environ)
    env["CEO_INSTALL_SKIP_SELF_SHA"] = "1"
    env["CEO_RAG_INSTALL_PROMPT"] = "0"
    return env


def _run_install(target, *extra):
    cmd = ["bash", INSTALL_SH, target] + list(extra)
    return subprocess.run(
        cmd, cwd=_REPO_ROOT, env=_install_env(),
        capture_output=True, text=True, timeout=600,
    )


def _run_validate(target):
    vg = os.path.join(target, ".claude", "scripts", "validate-governance.sh")
    return subprocess.run(
        ["bash", vg], cwd=target, capture_output=True, text=True, timeout=600,
    )


def _all_commands(settings):
    out = []
    for _ev, arr in (settings.get("hooks") or {}).items():
        for block in arr:
            for h in block.get("hooks", []):
                out.append(h.get("command", ""))
    return out


# wave-s330-F (PLAN-169 OQ-E5): the excluded roster is DERIVED from the
# `_derivation.exclude_hooks` spec embedded in the user template — the same
# source the generator (.claude/scripts/gen-settings-user-template.py) reads.
# Before this wave the tuple below was a second frozen copy of the template's
# `_comment` list of 10, and it went red the moment the classification
# (PLAN-169/s330-ceremony-F/hook-classification-S330.md §2) ruled two of
# those ten back IN by merit. A literal here would re-open that drift class;
# the oracle must ask "does `install --ceremony user` honour the spec?",
# not "does it honour a list someone typed once?".
_USER_TEMPLATE = os.path.join(
    _REPO_ROOT, "templates", "settings", "settings.user.json"
)
_BASE_TEMPLATE = os.path.join(
    _REPO_ROOT, "templates", "settings", "settings.base.json"
)


def _excluded_hooks_from_spec():
    """``(bare_names, scoped_pairs)`` from BOTH exclusion buckets.

    The event matters (pair-rail round 3). An entry WITHOUT ``event`` removes
    every registration of the basename, so the basename must appear in no
    installed command. An entry WITH one removes only that registration, and
    the generator deliberately KEEPS the others — flattening both to a basename
    made the oracle assert something the spec does not claim, and it would have
    failed on the day someone wrote a legitimate scoped exclusion.

    ``exclude_hooks_pending`` is read too: its entries are subtracted from the
    output exactly like the main bucket, and omitting it left a blind spot the
    size of that bucket.
    """
    with open(_USER_TEMPLATE, encoding="utf-8") as fh:
        spec = json.load(fh)["_derivation"]
    return _split_exclusions(spec)


def _split_exclusions(spec):
    """The parsing half, pure, so the scoped path is testable.

    The shipped spec has ZERO event-qualified exclusions today, so the scoped
    assertions in the test below are vacuous against the real artifact. A
    vacuous assertion proves nothing, and this is what lets a synthetic spec
    exercise the branch that the real one does not reach yet.
    """

    def _stem(name):
        return name[:-3] if name.endswith(".py") else name

    bare = []
    scoped = []
    for bucket in ("exclude_hooks", "exclude_hooks_pending"):
        for entry in spec.get(bucket, []):
            event = entry.get("event")
            if event:
                scoped.append((event, _stem(entry["name"])))
            else:
                bare.append(_stem(entry["name"]))
    # Fail LOUD if the spec ever degenerates: an empty exclusion list would
    # make every assertNotIn below vacuous, and the sentinel-ceremony guard
    # is the one hook the user profile can never register (no GPG, no
    # approved.md) — if it is not in the spec, the spec is wrong, not this test.
    assert bare, "_derivation exclusions are empty — the oracle would be vacuous"
    assert "check_canonical_edit" in bare, (
        "check_canonical_edit missing from the spec exclusions: %r" % (bare,)
    )
    return tuple(bare), tuple(scoped)


_GOVERNANCE_HOOKS, _SCOPED_EXCLUSIONS = _excluded_hooks_from_spec()
_KEEP_HOOKS = (
    "check_agent_spawn",
    "check_bash_safety",
    "audit_log",
    "UserPromptSubmit",
)


class TestExclusionParsingKeepsTheEvent(TestEnvContext):
    """The scoped branch, exercised — because the real spec does not reach it.

    The shipped `_derivation` has ZERO event-qualified exclusions and an empty
    pending bucket, so every scoped assertion in the install test below is
    vacuous against the real artifact today. That is precisely why the parsing
    is tested here against a synthetic spec: the branch that nothing exercises
    is the branch that breaks the day someone uses it (pair-rail round 3).
    """

    def test_a_scoped_exclusion_keeps_its_event(self):
        bare, scoped = _split_exclusions({
            "exclude_hooks": [
                {"name": "check_canonical_edit.py"},
                {"name": "foo.py", "event": "PostToolUse"},
            ],
        })
        self.assertEqual(bare, ("check_canonical_edit",))
        self.assertEqual(scoped, (("PostToolUse", "foo"),),
                         "the event was discarded — the oracle would assert "
                         "the hook is gone from EVERY event, which the spec "
                         "does not claim")

    def test_a_sole_registration_scoped_out_needs_no_survivor(self):
        """The round-3 assertion demanded a survivor unconditionally.

        A scoped exclusion on a hook the base registers under that ONE event
        validly removes it entirely, and the unconditional form failed on that
        legitimate spec — an over-correction found by round 4. The parsing side
        is unchanged; what this documents is the shape the install assertion has
        to respect, so the next reader does not "simplify" it back.
        """
        _bare, scoped = _split_exclusions({
            "exclude_hooks": [
                {"name": "check_canonical_edit.py"},
                {"name": "solo.py", "event": "OnlyEvent"},
            ],
        })
        self.assertEqual(scoped, (("OnlyEvent", "solo"),))
        # The install test asks the BASE whether a survivor should exist. With
        # a base that registers `solo.py` only under `OnlyEvent`, the answer is
        # no — and demanding one would be asserting something the spec does not
        # claim.
        base = {"hooks": {"OnlyEvent": [{"matcher": "", "hooks": [
            {"type": "command", "command": "python3 .claude/hooks/solo.py"}]}]}}
        elsewhere = [
            h.get("command", "")
            for ev, arr in base["hooks"].items() if ev != "OnlyEvent"
            for block in arr for h in block.get("hooks", [])
        ]
        self.assertNotIn("solo.py", " ".join(elsewhere))

    def test_the_pending_bucket_is_read(self):
        bare, scoped = _split_exclusions({
            "exclude_hooks": [{"name": "check_canonical_edit.py"}],
            "exclude_hooks_pending": [{"name": "later.py"}],
        })
        self.assertIn("later", bare,
                      "entries held in the pending bucket are subtracted from "
                      "the output too; ignoring them left a blind spot")

    def test_an_empty_spec_fails_loud(self):
        with self.assertRaises(AssertionError):
            _split_exclusions({"exclude_hooks": []})

    def test_a_spec_without_the_sentinel_guard_fails_loud(self):
        with self.assertRaises(AssertionError):
            _split_exclusions({"exclude_hooks": [{"name": "something_else.py"}]})


class TestInstallUserSkipsGovernanceHooks(TestEnvContext):
    """User settings.json omits every hook the template's `_derivation` spec
    excludes (governance/sentinel/kernel — 17 as of wave-s330-F, read live, never
    counted here) but KEEPS the advisory/safety hooks + core spawn/audit + the
    UserPromptSubmit optimizer."""

    def test_install_user_skips_governance_hooks(self):
        with tempfile.TemporaryDirectory() as target:
            cp = _run_install(target, "--ceremony", "user")
            self.assertEqual(cp.returncode, 0, msg=cp.stderr + cp.stdout)
            with open(os.path.join(target, ".claude", "settings.json")) as fh:
                settings = json.load(fh)
            cmds = " ".join(_all_commands(settings))
            # A scoped exclusion removes ONE registration, not the hook.
            # Asserted per event, and asserted POSITIVELY on the survivors —
            # otherwise a generator that dropped both would pass this half.
            for event, stem in _SCOPED_EXCLUSIONS:
                in_event = [
                    h.get("command", "")
                    for block in (settings.get("hooks") or {}).get(event, [])
                    for h in block.get("hooks", [])
                ]
                self.assertNotIn(
                    stem + ".py", " ".join(in_event),
                    msg="%s is excluded for %s but is registered there" % (stem, event),
                )
                # Only demand a survivor if the BASE has one. A scoped
                # exclusion on a hook registered under that single event
                # validly removes it entirely, and the round-3 version of this
                # assertion failed on exactly that legitimate spec — an
                # over-correction found by round 4.
                with open(_BASE_TEMPLATE, encoding="utf-8") as bfh:
                    base_doc = json.load(bfh)
                base_elsewhere = [
                    h.get("command", "")
                    for ev, arr in (base_doc.get("hooks") or {}).items()
                    if ev != event
                    for block in arr for h in block.get("hooks", [])
                ]
                if stem + ".py" in " ".join(base_elsewhere):
                    elsewhere = [
                        h.get("command", "")
                        for ev, arr in (settings.get("hooks") or {}).items()
                        if ev != event
                        for block in arr for h in block.get("hooks", [])
                    ]
                    self.assertIn(
                        stem + ".py", " ".join(elsewhere),
                        msg=("%s is excluded only for %s and the BASE registers "
                             "it elsewhere too, so that registration must "
                             "survive — the spec does not claim the hook is "
                             "gone" % (stem, event)),
                    )
            for gov in _GOVERNANCE_HOOKS:
                self.assertNotIn(
                    gov + ".py", cmds,
                    msg="governance hook %s should NOT be registered for user" % gov,
                )
            for keep in _KEEP_HOOKS:
                self.assertIn(
                    keep + ".py", cmds,
                    msg="hook %s should be registered for user" % keep,
                )


if __name__ == "__main__":
    unittest.main()
