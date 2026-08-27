"""PLAN-169 W-E (S329) — upgrade.sh derives its hook roster from the template.

Covers ``scripts/upgrade.sh::_merge_lifecycle_hooks_into_settings`` after the
S329 cure that replaced its hard-coded roster of six lifecycle registrations
with a derivation over ``templates/settings/settings.base.json``.

WHY THE FUNCTION AND NOT THE jq PROGRAM
---------------------------------------
The function text is extracted from the shipped ``upgrade.sh`` (a single
anchored ``^_merge_lifecycle_hooks_into_settings() {$`` .. ``^}$`` range, the
same idiom ``test-upgrade-historical-adopter.sh`` uses for ``_up_tmpbase``) and
SOURCED into a scratch bash harness with ``TARGET`` / ``SOURCE_DIR`` /
``BAK_DIR`` / ``DRY_RUN`` / ``SETTINGS_MERGE`` set and ``_up_record_op``
stubbed. Driving the real bash wrapper — rather than lifting the jq program out
and running it alone — is deliberate: the fail-open guards, the atomic write,
the ``--dry-run`` branch and the NOTE lines the adopter actually reads all live
in the wrapper, and the one defect this file's e2e sibling caught (a non-array
event value aborting the WHOLE merge) surfaced in exactly that seam. A jq-only
harness would have been green through it.

Every expectation is DERIVED from the template artifact, never re-hardcoded —
re-hardcoding the roster here would recreate, in the oracle, precisely the
second-copy defect the cure removes.

The heavy end-to-end evidence (a real install + a real upgrade, the pre-cure
RED control, the synthetic-hook positive control, byte-idempotency) lives in
``scripts/tests/test-upgrade-lifecycle-hooks-derived.sh``; this file is the
fast per-PR oracle for the identity key and the anti-rot guard.

stdlib-only; Python >= 3.9. Skips (with a reason) when ``jq`` is absent.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
UPGRADE_SH = REPO_ROOT / "scripts" / "upgrade.sh"
TEMPLATE_SETTINGS = REPO_ROOT / "templates" / "settings" / "settings.base.json"
TEMPLATE_USER_SETTINGS = REPO_ROOT / "templates" / "settings" / "settings.user.json"

_HOOKS_DIR = REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

FUNC_NAME = "_merge_lifecycle_hooks_into_settings"

# The same whole-token shape the function's jq uses. Kept here as an
# INDEPENDENT re-implementation on purpose: an oracle that imports the
# implementation's own extractor cannot catch that extractor being wrong.
_PY_TOKEN = re.compile(r"(?<![A-Za-z0-9_.-])[A-Za-z0-9_][A-Za-z0-9_.-]*\.py(?![A-Za-z0-9_.-])")

_HAVE_JQ = shutil.which("jq") is not None


def _func_source() -> str:
    """The shipped function body, extracted from upgrade.sh by anchor."""
    text = UPGRADE_SH.read_text(encoding="utf-8")
    starts = [
        i for i, line in enumerate(text.split("\n"))
        if line == "%s() {" % FUNC_NAME
    ]
    if len(starts) != 1:
        raise AssertionError(
            "expected exactly one definition of %s in upgrade.sh, found %d"
            % (FUNC_NAME, len(starts))
        )
    lines = text.split("\n")
    start = starts[0]
    for end in range(start + 1, len(lines)):
        if lines[end] == "}":
            return "\n".join(lines[start:end + 1])
    raise AssertionError("no closing brace found for %s" % FUNC_NAME)


def _tmpbase_source() -> str:
    """The shipped _up_tmpbase, extracted by anchor — the REAL helper, so the
    scratch-confinement test measures the contract the upgrader actually runs."""
    lines = UPGRADE_SH.read_text(encoding="utf-8").split("\n")
    starts = [i for i, line in enumerate(lines) if line == "_up_tmpbase() {"]
    if len(starts) != 1:
        raise AssertionError("expected exactly one _up_tmpbase in upgrade.sh, found %d" % len(starts))
    for end in range(starts[0] + 1, len(lines)):
        if lines[end] == "}":
            return "\n".join(lines[starts[0]:end + 1])
    raise AssertionError("no closing brace found for _up_tmpbase")


def _block_keys(block: Dict) -> List[str]:
    """Registration keys of one hooks block (the oracle's own derivation)."""
    if not isinstance(block, dict):
        return []
    entries = block.get("hooks")
    if not isinstance(entries, list):
        return []
    keys: List[str] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        cmd = entry.get("command")
        if not isinstance(cmd, str):
            continue
        names = _PY_TOKEN.findall(cmd)
        keys.extend(names if names else [" ".join(cmd.split())])
    return keys


def _keybag(doc: Dict) -> List[str]:
    """``"<event> <key>"`` lines WITH MULTIPLICITY, sorted.

    The oracle for "was anything duplicated". ``_keyset`` cannot answer that
    question — it collapses duplicates before the caller ever sees them, so a
    count taken from it is bounded by 1 and the assertion can never fail (rail
    round 1, P2). ``TestDuplicateOracle`` is the positive control that keeps
    this distinction from decaying back into one helper.
    """
    out = []
    hooks = doc.get("hooks")
    if not isinstance(hooks, dict):
        return []
    for event in sorted(hooks):
        blocks = hooks[event]
        if not isinstance(blocks, list):
            continue
        for block in blocks:
            for key in _block_keys(block):
                out.append("%s %s" % (event, key))
    return sorted(out)


def _keyset(doc: Dict) -> List[str]:
    """Sorted UNIQUE ``"<event> <key>"`` lines — "is anything missing/invented"."""
    return sorted(set(_keybag(doc)))


@unittest.skipUnless(_HAVE_JQ, "jq is the merge engine under test and is not on PATH")
class _MergeHarness(TestEnvContext):
    """Drives the REAL bash function against a scratch target + scratch source."""

    def setUp(self) -> None:
        super().setUp()
        self._tmp = tempfile.mkdtemp(prefix="w-e-merge-")
        self.addCleanup(shutil.rmtree, self._tmp, True)
        self.target = Path(self._tmp) / "target"
        (self.target / ".claude").mkdir(parents=True)
        self.source = Path(self._tmp) / "source"
        (self.source / "templates" / "settings").mkdir(parents=True)
        # Default source templates == the shipped artifacts, BOTH of them: the
        # ceremony selects between them (rail round 6, P1), so a scratch source
        # that carried only settings.base.json would make every user-ceremony
        # merge fail-open on "template unreadable" and prove nothing.
        self.set_template(json.loads(TEMPLATE_SETTINGS.read_text(encoding="utf-8")))
        self.set_user_template(json.loads(TEMPLATE_USER_SETTINGS.read_text(encoding="utf-8")))

    # --- fixture setters ---------------------------------------------------

    @property
    def settings_path(self) -> Path:
        return self.target / ".claude" / "settings.json"

    @property
    def template_path(self) -> Path:
        return self.source / "templates" / "settings" / "settings.base.json"

    @property
    def user_template_path(self) -> Path:
        return self.source / "templates" / "settings" / "settings.user.json"

    def set_template(self, obj: Dict) -> None:
        self.template_path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")

    def set_user_template(self, obj: Dict) -> None:
        self.user_template_path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")

    def seed(self, obj: Dict) -> None:
        self.settings_path.write_text(json.dumps(obj, indent=2) + "\n", encoding="utf-8")

    def result(self) -> Dict:
        return json.loads(self.settings_path.read_text(encoding="utf-8"))

    # --- driver ------------------------------------------------------------

    def run_merge(
        self, *, dry: bool = False, ceremony: Optional[str] = "maintainer",
        persist: Optional[str] = "1", tmpdir: Optional[str] = None,
    ) -> "subprocess.CompletedProcess[str]":
        # `ceremony=None` leaves CEREMONY_EFFECTIVE UNSET on purpose — under
        # `set -u` that is the one condition upgrade.sh itself can never
        # produce (it resolves the ceremony before any function runs), and the
        # function has to survive it by taking the fail-safe branch.
        script = "\n".join([
            "set -uo pipefail",
            "SETTINGS_MERGE=1",
            "DRY_RUN=%d" % (1 if dry else 0),
        ] + (["CEREMONY_EFFECTIVE=%s" % json.dumps(ceremony)] if ceremony is not None else [])
          + (["_CEREMONY_PERSIST=%s" % json.dumps(persist)] if persist is not None else []) + [
            'TARGET=%s' % json.dumps(str(self.target)),
            'SOURCE_DIR=%s' % json.dumps(str(self.source)),
            'BAK_DIR=%s' % json.dumps(str(Path(self._tmp) / "bak")),
            "_up_record_op() { :; }",
            "",
            _tmpbase_source(),
            "",
            _func_source(),
            "",
            FUNC_NAME,
        ])
        env = os.environ.copy()
        if tmpdir is not None:
            env["TMPDIR"] = tmpdir
        proc = subprocess.run(
            ["bash", "-c", script], capture_output=True, text=True, timeout=120, env=env,
        )
        self.assertEqual(
            proc.returncode, 0,
            "the merge function must never exit non-zero (fail-open contract); "
            "stderr=%s" % proc.stderr,
        )
        return proc


class TestTemplateIsTheRoster(_MergeHarness):
    """The roster comes from the template — all of it, and only it."""

    def test_every_template_registration_lands_on_an_empty_settings(self) -> None:
        template = json.loads(TEMPLATE_SETTINGS.read_text(encoding="utf-8"))
        expected = _keyset(template)
        self.assertGreaterEqual(
            len(expected), 20,
            "the template yielded %d registrations — a near-empty template "
            "would make this whole file vacuous" % len(expected),
        )
        self.seed({"hooks": {}})
        self.run_merge()
        self.assertEqual(
            _keyset(self.result()), expected,
            "the merge over an empty settings.json must reproduce the template's "
            "registration set exactly — no missing entry, no invented one",
        )

    def test_every_template_python_hook_is_present_by_name(self) -> None:
        """The finding's own shape: a .py in the template must reach the adopter."""
        template = json.loads(TEMPLATE_SETTINGS.read_text(encoding="utf-8"))
        wanted = sorted({
            name
            for blocks in template["hooks"].values() if isinstance(blocks, list)
            for block in blocks
            for name in _block_keys(block)
            if name.endswith(".py")
        })
        self.seed({"hooks": {}})
        self.run_merge()
        got = {line.split(" ", 1)[1] for line in _keyset(self.result())}
        missing = [n for n in wanted if n not in got]
        self.assertEqual(
            missing, [],
            "these template hooks were not registered by the merge: %s" % missing,
        )
        self.assertIn(
            "check_ledger_checkpoint.py", got,
            "check_ledger_checkpoint.py is the S328 finding — if the template "
            "carries it, the upgrade must register it",
        )

    def test_a_synthetic_template_entry_is_registered(self) -> None:
        """Positive control: a name invented here cannot be in any literal list."""
        synth = "check_zz_unit_synthetic.py"
        # assertTrue, not assertNotIn: the container here is a 200 KB script and
        # unittest would paste all of it into the failure message.
        self.assertTrue(
            synth not in UPGRADE_SH.read_text(encoding="utf-8"),
            "%r appears in upgrade.sh — pick another name; this control assumes "
            "the upgrader cannot know it" % synth,
        )
        template = json.loads(TEMPLATE_SETTINGS.read_text(encoding="utf-8"))
        template["hooks"].setdefault("PreToolUse", []).append({
            "matcher": "Bash",
            "hooks": [{"type": "command", "command": "bash h.sh %s" % synth, "timeout": 5}],
        })
        self.set_template(template)
        self.seed({"hooks": {}})
        self.run_merge()
        self.assertIn("PreToolUse %s" % synth, _keyset(self.result()))

    def test_a_template_entry_removed_is_not_registered(self) -> None:
        """Negative half of the control: the roster tracks the template both ways."""
        template = json.loads(TEMPLATE_SETTINGS.read_text(encoding="utf-8"))
        template["hooks"]["PreToolUse"] = [
            b for b in template["hooks"]["PreToolUse"]
            if "check_ledger_checkpoint.py" not in _block_keys(b)
        ]
        self.set_template(template)
        self.seed({"hooks": {}})
        self.run_merge()
        self.assertNotIn(
            "check_ledger_checkpoint.py",
            {line.split(" ", 1)[1] for line in _keyset(self.result())},
            "the merge registered a hook the template does not declare — the "
            "roster is not actually derived",
        )


class TestIdentityKey(_MergeHarness):
    """The presence test compares WHOLE tokens, and covers the no-.py shape."""

    def test_a_prefix_name_does_not_mask_a_longer_one(self) -> None:
        self.set_template({"hooks": {"PreToolUse": [
            {"matcher": "Bash", "hooks": [{"type": "command", "command": "bash h.sh check_x.py"}]},
            {"matcher": "Bash", "hooks": [{"type": "command", "command": "bash h.sh check_xy.py"}]},
        ]}})
        self.seed({"hooks": {"PreToolUse": [
            {"matcher": "Bash", "hooks": [{"type": "command", "command": "bash h.sh check_x.py"}]},
        ]}})
        self.run_merge()
        result = self.result()
        self.assertIn(
            "PreToolUse check_xy.py", _keyset(result),
            "check_x.py being registered must not suppress check_xy.py — the "
            "identity match is not anchored",
        )
        # _keybag, not _keyset: a count taken from the deduplicated set is
        # bounded by 1 and could never catch the duplication it claims to.
        self.assertEqual(
            len([k for k in _keybag(result) if k == "PreToolUse check_x.py"]), 1,
            "check_x.py was duplicated — an already-present registration must "
            "not be re-appended",
        )

    def test_a_longer_name_does_not_mask_a_prefix_one(self) -> None:
        """The mirror direction, which a `test(name)` substring match fails."""
        self.set_template({"hooks": {"PreToolUse": [
            {"matcher": "Bash", "hooks": [{"type": "command", "command": "bash h.sh check_x.py"}]},
        ]}})
        self.seed({"hooks": {"PreToolUse": [
            {"matcher": "Bash", "hooks": [{"type": "command", "command": "bash h.sh check_xy.py"}]},
        ]}})
        self.run_merge()
        self.assertIn("PreToolUse check_x.py", _keyset(self.result()))

    def test_a_path_qualified_command_matches_the_bare_name(self) -> None:
        """A registration written as a PATH is the same registration."""
        self.set_template({"hooks": {"PreToolUse": [
            {"matcher": "Bash", "hooks": [{"type": "command", "command": "bash h.sh check_x.py"}]},
        ]}})
        self.seed({"hooks": {"PreToolUse": [
            {"matcher": "Bash",
             "hooks": [{"type": "command", "command": "python3 .claude/hooks/check_x.py"}]},
        ]}})
        self.run_merge()
        self.assertEqual(
            len(self.result()["hooks"]["PreToolUse"]), 1,
            "the path-qualified form was not recognised as the same hook, so a "
            "duplicate canonical block was appended",
        )

    def test_an_inline_block_without_a_py_is_registered_exactly_once(self) -> None:
        inline = "echo '{\"decision\":\"allow\"}'"
        self.set_template({"hooks": {"PostToolUse": [
            {"matcher": "Agent", "hooks": [{"type": "command", "command": inline}]},
        ]}})
        self.seed({"hooks": {}})
        self.run_merge()
        self.assertEqual(len(self.result()["hooks"]["PostToolUse"]), 1)
        self.run_merge()
        self.assertEqual(
            len(self.result()["hooks"]["PostToolUse"]), 1,
            "the no-.py block is keyed by its full command; a second run "
            "duplicated it, so that key is not stable",
        )


class TestPreservationAndIdempotency(_MergeHarness):
    """Additive: what is already there is never rewritten."""

    def test_an_adopter_edit_survives(self) -> None:
        self.set_template({"hooks": {"PreToolUse": [
            {"_comment": "canonical", "matcher": "Bash",
             "hooks": [{"type": "command", "command": "bash h.sh check_x.py", "timeout": 5}]},
        ]}})
        self.seed({"hooks": {"PreToolUse": [
            {"_comment": "ADOPTER EDITED", "matcher": "Bash",
             "hooks": [{"type": "command", "command": "bash h.sh check_x.py", "timeout": 4242}]},
        ]}, "customKey": "preserve me"})
        self.run_merge()
        result = self.result()
        self.assertEqual(len(result["hooks"]["PreToolUse"]), 1)
        self.assertEqual(result["hooks"]["PreToolUse"][0]["hooks"][0]["timeout"], 4242)
        self.assertEqual(result["hooks"]["PreToolUse"][0]["_comment"], "ADOPTER EDITED")
        self.assertEqual(result["customKey"], "preserve me")

    def test_a_no_op_run_does_not_touch_the_file(self) -> None:
        """Byte-identity, not merely value-identity: no gratuitous reformat."""
        self.seed({"hooks": {}})
        self.run_merge()
        before = self.settings_path.read_bytes()
        proc = self.run_merge()
        self.assertEqual(
            self.settings_path.read_bytes(), before,
            "the second run rewrote settings.json — re-running an upgrade must "
            "be a byte-level no-op",
        )
        self.assertIn("already present", proc.stdout)

    def test_unrelated_settings_keys_and_events_are_untouched(self) -> None:
        self.set_template({"hooks": {"PreToolUse": [
            {"matcher": "Bash", "hooks": [{"type": "command", "command": "bash h.sh check_x.py"}]},
        ]}})
        self.seed({
            "hooks": {"Stop": [
                {"matcher": "", "hooks": [{"type": "command", "command": "bash h.sh adopter_own.py"}]},
            ]},
            "permissions": {"defaultMode": "acceptEdits"},
        })
        self.run_merge()
        result = self.result()
        self.assertEqual(result["permissions"], {"defaultMode": "acceptEdits"})
        self.assertIn("Stop adopter_own.py", _keyset(result))


class TestFailSafe(_MergeHarness):
    """Shapes we cannot parse are preserved and named, never coerced."""

    def test_a_non_array_event_value_is_preserved_and_the_rest_still_merges(self) -> None:
        self.set_template({"hooks": {
            "PreToolUse": [{"matcher": "Bash",
                            "hooks": [{"type": "command", "command": "bash h.sh check_x.py"}]}],
            "SubagentStart": [{"matcher": "",
                               "hooks": [{"type": "command", "command": "bash h.sh check_y.py"}]}],
        }})
        self.seed({"hooks": {"SubagentStart": {"not": "an array"}}})
        proc = self.run_merge()
        result = self.result()
        self.assertEqual(
            result["hooks"]["SubagentStart"], {"not": "an array"},
            "an unparseable event value must be preserved exactly",
        )
        self.assertIn(
            "PreToolUse check_x.py", _keyset(result),
            "one odd event disabled the whole merge — the fail-safe is too coarse",
        )
        self.assertIn("is not an array", proc.stderr)

    def test_a_non_object_hooks_root_is_left_alone(self) -> None:
        self.seed({"hooks": ["not", "an", "object"], "keep": 1})
        proc = self.run_merge()
        result = self.result()
        self.assertEqual(result["hooks"], ["not", "an", "object"])
        self.assertEqual(result["keep"], 1)
        self.assertIn("not an object", proc.stderr)

    def test_an_absent_hooks_root_is_populated(self) -> None:
        self.seed({"keep": 1})
        self.run_merge()
        result = self.result()
        self.assertEqual(result["keep"], 1)
        self.assertGreaterEqual(len(_keyset(result)), 20)


    def test_a_missing_template_is_advisory_not_fatal(self) -> None:
        self.seed({"hooks": {}})
        before = self.settings_path.read_bytes()
        self.template_path.unlink()
        proc = self.run_merge()
        self.assertEqual(self.settings_path.read_bytes(), before)
        self.assertIn("template unreadable", proc.stderr)

    def test_an_invalid_template_is_advisory_not_fatal(self) -> None:
        self.seed({"hooks": {}})
        before = self.settings_path.read_bytes()
        self.template_path.write_text("{ not json", encoding="utf-8")
        proc = self.run_merge()
        self.assertEqual(self.settings_path.read_bytes(), before)
        self.assertIn("not JSON", proc.stderr)

    def test_a_malformed_settings_is_left_untouched(self) -> None:
        self.settings_path.write_text("{ not json", encoding="utf-8")
        proc = self.run_merge()
        self.assertEqual(self.settings_path.read_text(encoding="utf-8"), "{ not json")
        self.assertIn("malformed settings.json", proc.stderr)

    def test_garbage_blocks_are_ignored_without_aborting(self) -> None:
        """jq raises on indexing a number; an uncaught raise kills the merge."""
        self.set_template({"hooks": {"PreToolUse": [
            {"matcher": "Bash", "hooks": [{"type": "command", "command": "bash h.sh check_x.py"}]},
        ]}})
        self.seed({"hooks": {"PreToolUse": [
            1, "x", {"hooks": {"a": 1}}, {"hooks": [{"command": 5}]}, {"hooks": [None]},
        ]}})
        self.run_merge()
        self.assertIn("PreToolUse check_x.py", _keyset(self.result()))


class TestTemplateMustBeStructurallyValid(_MergeHarness):
    """The TEMPLATE is held to a stricter standard than the adopter's file.

    An adopter's malformed event is preserved and named, per event, and the
    other registrations still land. A malformed TEMPLATE event has no such
    salvage: the template is the artifact that DEFINES the roster, so if any
    event value is not an array of blocks we do not know what the correct
    answer is and the whole merge is refused (rail round 2, P2).

    Both failure modes the old guard let through are silent, which is why
    ``.hooks`` being an object was never enough:
      object value -> ``.[]?`` iterates its VALUES and can APPEND something
                      the template never declared as a block
      scalar/null  -> ``.[]?`` yields nothing and the event is DROPPED
    """

    _SMUGGLED = "check_zz_smuggled_unit.py"

    def _bad(self, value) -> None:
        self.set_template({"hooks": {
            "PreToolUse": value,
            "Stop": [{"matcher": "",
                      "hooks": [{"type": "command", "command": "bash h.sh check_ok_stop.py"}]}],
        }})
        self.seed({"hooks": {}})

    def test_an_object_valued_template_event_is_refused_and_smuggles_nothing(self) -> None:
        self._bad({"smuggled": {
            "matcher": "Bash",
            "hooks": [{"type": "command", "command": "bash h.sh %s" % self._SMUGGLED}],
        }})
        before = self.settings_path.read_bytes()
        proc = self.run_merge()
        self.assertEqual(
            self.settings_path.read_bytes(), before,
            "a template event whose value is an object was merged anyway",
        )
        self.assertNotIn(
            self._SMUGGLED, {line.split(" ", 1)[1] for line in _keyset(self.result())},
            "the object's VALUE was registered as if it were a hooks block — "
            "`.[]?` iterates an object and the guard did not stop it",
        )
        self.assertIn("PreToolUse (object)", proc.stderr)

    def test_a_scalar_valued_template_event_refuses_the_WHOLE_merge(self) -> None:
        self._bad(42)
        before = self.settings_path.read_bytes()
        proc = self.run_merge()
        self.assertEqual(self.settings_path.read_bytes(), before)
        self.assertNotIn(
            "Stop check_ok_stop.py", _keyset(self.result()),
            "the well-formed sibling event was merged while another was "
            "invalid — a partial roster is the bug class this wave removes, "
            "so the refusal has to be all-or-nothing",
        )
        self.assertIn("PreToolUse (number)", proc.stderr)

    def test_a_null_valued_template_event_is_refused(self) -> None:
        self._bad(None)
        before = self.settings_path.read_bytes()
        proc = self.run_merge()
        self.assertEqual(self.settings_path.read_bytes(), before)
        self.assertIn("PreToolUse (null)", proc.stderr)

    def test_every_offending_event_is_named_not_just_the_first(self) -> None:
        self.set_template({"hooks": {"PreToolUse": 42, "Stop": {"a": 1}, "PreCompact": None}})
        self.seed({"hooks": {}})
        proc = self.run_merge()
        for expected in ("PreToolUse (number)", "Stop (object)", "PreCompact (null)"):
            self.assertIn(
                expected, proc.stderr,
                "only some offending events were named; a partially reported "
                "template is a partially fixable one",
            )

    def test_dry_run_refuses_the_same_way(self) -> None:
        self._bad(42)
        proc = self.run_merge(dry=True)
        self.assertIn("PreToolUse (number)", proc.stderr)
        self.assertNotIn("would REGISTER", proc.stdout)

    def test_a_well_formed_template_still_merges(self) -> None:
        """The control: the guard must not refuse valid templates."""
        self._bad([{"matcher": "Bash",
                    "hooks": [{"type": "command", "command": "bash h.sh check_x.py"}]}])
        self.run_merge()
        keys = _keyset(self.result())
        self.assertIn("PreToolUse check_x.py", keys)
        self.assertIn("Stop check_ok_stop.py", keys)

    # --- rail round 3, P2(a): an ARRAY of blocks is not enough either --------

    _GOOD = {"matcher": "Bash",
             "hooks": [{"type": "command", "command": "bash h.sh check_good.py"}]}

    def _with_block(self, block) -> None:
        """A template whose PreToolUse holds one good block and one suspect one."""
        self.set_template({"hooks": {"PreToolUse": [self._GOOD, block]}})
        self.seed({"hooks": {}})

    def test_a_malformed_block_refuses_the_merge_instead_of_skipping_it(self) -> None:
        self._with_block(None)
        before = self.settings_path.read_bytes()
        proc = self.run_merge()
        self.assertEqual(
            self.settings_path.read_bytes(), before,
            "an unidentifiable block was silently skipped and its siblings "
            "merged — that is a partial roster through a second door",
        )
        self.assertNotIn(
            "PreToolUse check_good.py", _keyset(self.result()),
            "the well-formed SIBLING was registered while another block in the "
            "same event was unidentifiable; the template rule is all-or-nothing",
        )
        self.assertIn("PreToolUse[1]", proc.stderr)

    def test_every_unidentifiable_block_shape_is_named_with_its_reason(self) -> None:
        for block, reason in (
            (None, "null"),
            ({}, "no .hooks"),
            ({"hooks": []}, ".hooks is empty"),
            ({"hooks": {}}, ".hooks is object"),
            ({"hooks": [{"type": "command"}]}, "a .hooks entry has no string .command"),
            ({"hooks": [{"type": "command", "command": ""}]},
             "a .hooks entry has an empty .command"),
            ({"hooks": ["not-an-object"]}, "a .hooks entry is not an object"),
        ):
            with self.subTest(block=block):
                self._with_block(block)
                before = self.settings_path.read_bytes()
                proc = self.run_merge()
                self.assertEqual(self.settings_path.read_bytes(), before)
                self.assertIn("PreToolUse[1] (%s)" % reason, proc.stderr)

    def test_a_block_index_is_reported_so_the_offender_can_be_found(self) -> None:
        self.set_template({"hooks": {"PreToolUse": [self._GOOD, self._GOOD, {}]}})
        self.seed({"hooks": {}})
        proc = self.run_merge()
        self.assertIn("PreToolUse[2]", proc.stderr)
        self.assertNotIn("PreToolUse[0]", proc.stderr)

    def test_the_shipped_template_passes_the_guard(self) -> None:
        """A guard that would refuse the real artifact is not shippable.

        Mirrors the jq rule at both levels — event values AND blocks. The
        block half matters more than it looks: the guard is fail-closed on the
        whole merge, so one malformed block in the shipped template would
        silently stop registering hooks for every adopter on earth.
        """
        template = json.loads(TEMPLATE_SETTINGS.read_text(encoding="utf-8"))
        bad = []
        for event, value in template["hooks"].items():
            if not isinstance(value, list):
                bad.append("%s (%s)" % (event, type(value).__name__))
                continue
            for index, block in enumerate(value):
                entries = block.get("hooks") if isinstance(block, dict) else None
                if not isinstance(block, dict):
                    why = type(block).__name__
                elif not isinstance(entries, list):
                    why = "hooks is %s" % type(entries).__name__
                elif not entries:
                    why = "hooks is empty"
                elif not all(isinstance(e, dict) for e in entries):
                    why = "an entry is not an object"
                elif not all(isinstance(e.get("command"), str) and e.get("command")
                             for e in entries):
                    why = "an entry has no non-empty string command"
                else:
                    continue
                bad.append("%s[%d] (%s)" % (event, index, why))
        self.assertEqual(
            bad, [],
            "templates/settings/settings.base.json itself would be REFUSED by "
            "the guard, so every upgrade would stop registering hooks: %s" % bad,
        )

    def test_the_guard_accepts_the_shipped_template_end_to_end(self) -> None:
        """The oracle above re-implements the rule; this runs the real thing."""
        self.seed({"hooks": {}})
        proc = self.run_merge()
        self.assertNotIn("structurally invalid", proc.stderr)
        self.assertGreaterEqual(len(_keyset(self.result())), 20)


class TestExplicitFalsyIsNotAbsent(_MergeHarness):
    """ABSENT and PRESENT-BUT-FALSY are different questions (rail round 1, P2).

    ``x // []`` answers both with ``[]``, so before the cure an adopter who had
    written an explicit ``null``/``false`` was read as "nothing here yet" and
    overwritten with the whole template roster. The presence tests ask
    ``has(...)`` on the container instead. The paired ``..._is_populated`` /
    ``..._absent_event...`` cases below are what stop the cure from
    over-correcting into "never register anything".
    """

    def _one_hook_template(self) -> None:
        self.set_template({"hooks": {
            "PreToolUse": [{"matcher": "Bash",
                            "hooks": [{"type": "command", "command": "bash h.sh check_x.py"}]}],
            "PreCompact": [{"matcher": "",
                            "hooks": [{"type": "command", "command": "bash h.sh check_y.py"}]}],
        }})

    def test_an_explicitly_null_hooks_root_is_preserved(self) -> None:
        self._one_hook_template()
        self.seed({"hooks": None, "keep": 1})
        before = self.settings_path.read_bytes()
        proc = self.run_merge()
        self.assertEqual(
            self.settings_path.read_bytes(), before,
            "an explicit \"hooks\": null was overwritten — `// {}` read the "
            "adopter's decision as an absent key",
        )
        self.assertIn("a .hooks that is not an object (found: null)", proc.stderr)

    def test_an_explicitly_false_hooks_root_is_preserved(self) -> None:
        self._one_hook_template()
        self.seed({"hooks": False, "keep": 1})
        before = self.settings_path.read_bytes()
        proc = self.run_merge()
        self.assertEqual(self.settings_path.read_bytes(), before)
        self.assertIn("a .hooks that is not an object (found: boolean)", proc.stderr)

    def test_an_explicitly_null_event_is_preserved_and_the_rest_still_merges(self) -> None:
        self._one_hook_template()
        self.seed({"hooks": {"PreCompact": None}})
        proc = self.run_merge()
        result = self.result()
        self.assertIsNone(
            result["hooks"]["PreCompact"],
            "an event explicitly set to null was refilled from the template",
        )
        self.assertIn(
            "PreToolUse check_x.py", _keyset(result),
            "one preserved event disabled the whole merge — the fail-safe is "
            "too coarse",
        )
        self.assertIn("'PreCompact' in settings.json is not an array (found: null)", proc.stderr)

    def test_an_explicitly_false_event_is_preserved(self) -> None:
        self._one_hook_template()
        self.seed({"hooks": {"PreCompact": False}})
        proc = self.run_merge()
        self.assertIs(self.result()["hooks"]["PreCompact"], False)
        self.assertIn("'PreCompact' in settings.json is not an array (found: boolean)", proc.stderr)

    def test_an_absent_event_key_is_still_registered(self) -> None:
        """The other half: absence must NOT be treated as a decision."""
        self._one_hook_template()
        self.seed({"hooks": {}})
        self.run_merge()
        self.assertIn("PreCompact check_y.py", _keyset(self.result()))

    def test_an_empty_array_event_is_still_registered(self) -> None:
        """`[]` is a well-formed container, not a falsy surprise."""
        self._one_hook_template()
        self.seed({"hooks": {"PreCompact": []}})
        self.run_merge()
        self.assertIn("PreCompact check_y.py", _keyset(self.result()))

    def test_dry_run_names_the_preserved_event(self) -> None:
        """A preservation the adopter cannot see in --dry-run is a surprise."""
        self._one_hook_template()
        self.seed({"hooks": {"PreCompact": None}})
        before = self.settings_path.read_bytes()
        proc = self.run_merge(dry=True)
        self.assertEqual(self.settings_path.read_bytes(), before)
        self.assertIn("'PreCompact' in settings.json is not an array (found: null)", proc.stderr)
        self.assertIn("would REGISTER PreToolUse check_x.py", proc.stdout)

    def test_a_non_object_document_is_preserved_and_named(self) -> None:
        self.settings_path.write_text("[1, 2, 3]\n", encoding="utf-8")
        proc = self.run_merge()
        self.assertEqual(self.settings_path.read_text(encoding="utf-8"), "[1, 2, 3]\n")
        self.assertIn("is not a JSON object (found: array)", proc.stderr)


class TestPreservedIsNotComplete(_MergeHarness):
    """A PRESERVED event is not a registered one (rail round 3, P2).

    With every other registration present, a skipped event leaves ``_adds`` at
    zero — and the old summary read that as "everything in the template is
    already present". It is not: the hooks the template declares under the
    preserved event are exactly the ones that are missing. Reporting that as
    completeness is worse than reporting nothing, because it is the line an
    adopter reads for reassurance.
    """

    _ABSENT = "check_zz_preserved_unit.py"

    def _template(self) -> None:
        self.set_template({"hooks": {
            "PreToolUse": [{"matcher": "Bash",
                            "hooks": [{"type": "command", "command": "bash h.sh check_x.py"}]}],
            "PreCompact": [{"matcher": "",
                            "hooks": [{"type": "command", "command": "bash h.sh %s" % self._ABSENT}]}],
        }})

    def _complete_except_preserved(self) -> None:
        """Everything registered EXCEPT PreCompact, which is an explicit null."""
        self._template()
        self.seed({"hooks": {
            "PreToolUse": [{"matcher": "Bash",
                            "hooks": [{"type": "command", "command": "bash h.sh check_x.py"}]}],
            "PreCompact": None,
        }})

    def _assert_partial(self, stream: str) -> None:
        self.assertNotIn(
            "already present", stream,
            "the run claimed completeness while a preserved event left a "
            "template hook unregistered",
        )
        self.assertIn(self._ABSENT, stream, "the absent hook was not named")
        self.assertIn("PRESERVED", stream)

    def test_apply_reports_partial_not_complete(self) -> None:
        self._complete_except_preserved()
        proc = self.run_merge()
        self._assert_partial(proc.stdout)

    def test_dry_run_reports_partial_not_complete(self) -> None:
        self._complete_except_preserved()
        proc = self.run_merge(dry=True)
        self._assert_partial(proc.stdout)

    def test_a_run_that_registers_AND_preserves_says_both(self) -> None:
        self._template()
        self.seed({"hooks": {"PreCompact": None}})   # PreToolUse missing entirely
        proc = self.run_merge()
        self.assertIn("REGISTERED", proc.stdout)
        self._assert_partial(proc.stdout)

    def test_a_genuinely_complete_adopter_still_says_already_present(self) -> None:
        """The control: the completeness sentence must survive where it is TRUE."""
        self._template()
        template = json.loads(self.template_path.read_text(encoding="utf-8"))
        self.seed({"hooks": template["hooks"]})
        proc = self.run_merge()
        self.assertIn("already present", proc.stdout)
        self.assertNotIn("PRESERVED:", proc.stdout)

    def test_the_summary_says_how_to_fix_it(self) -> None:
        self._complete_except_preserved()
        proc = self.run_merge()
        self.assertIn("re-run the upgrade", proc.stdout)


class TestDuplicateOracle(TestEnvContext):
    """The duplicate oracle must be able to FAIL.

    ``_keyset`` deduplicates, so ``len([k for k in _keyset(d) if k == X]) == 1``
    holds for a document with X twice — the assertion it looks like is not the
    assertion it makes. This class is the positive control: the same planted
    duplicate must be visible to ``_keybag`` and invisible to ``_keyset``.
    """

    _DUP = {"hooks": {"PreToolUse": [
        {"matcher": "Bash", "hooks": [{"type": "command", "command": "bash h.sh check_x.py"}]},
        {"matcher": "Bash", "hooks": [{"type": "command", "command": "bash h.sh check_x.py"}]},
    ]}}

    def test_keybag_reports_a_planted_duplicate(self) -> None:
        self.assertEqual(
            [k for k in _keybag(self._DUP) if k == "PreToolUse check_x.py"],
            ["PreToolUse check_x.py"] * 2,
        )

    def test_keyset_is_blind_to_the_same_duplicate(self) -> None:
        self.assertEqual(
            [k for k in _keyset(self._DUP) if k == "PreToolUse check_x.py"],
            ["PreToolUse check_x.py"],
            "if _keyset ever grew multiplicity this control would stop "
            "demonstrating the blind spot it exists to document",
        )


class TestDryRun(_MergeHarness):
    """--dry-run announces the same derivation and writes nothing."""

    def test_dry_run_names_each_missing_registration_and_writes_nothing(self) -> None:
        self.seed({"hooks": {}})
        before = self.settings_path.read_bytes()
        proc = self.run_merge(dry=True)
        self.assertEqual(
            self.settings_path.read_bytes(), before,
            "--dry-run modified settings.json",
        )
        template = json.loads(TEMPLATE_SETTINGS.read_text(encoding="utf-8"))
        for line in _keyset(template):
            if not line.endswith(".py"):
                continue
            self.assertIn(
                "would REGISTER %s" % line, proc.stdout,
                "--dry-run did not announce %r; a migration silent in dry-run "
                "is one the adopter cannot review" % line,
            )

    def test_dry_run_on_a_current_settings_says_no_op(self) -> None:
        template = json.loads(TEMPLATE_SETTINGS.read_text(encoding="utf-8"))
        # A CURRENT settings carries the template's .env too (rail round 7, P1:
        # the settings travel with the hooks) — a seed without it is a legacy
        # adopter, and for that one the dry-run correctly announces work.
        self.seed({"hooks": template["hooks"], "env": template["env"]})
        proc = self.run_merge(dry=True)
        self.assertIn("ALREADY present", proc.stdout)
        self.assertNotIn("would REGISTER", proc.stdout)


class TestCeremonySelectsTheTemplate(_MergeHarness):
    """The CEREMONY picks the template — the same decision install.sh makes.

    Rail round 6 (P1): deriving from settings.base.json regardless of the
    ceremony would re-register, on upgrade, the governance hooks that
    settings.user.json deliberately omits — the advisory profile silently
    turned into the maintainer profile. Every expectation here is DERIVED from
    the two shipped artifacts; the one literal name is the rail's own example,
    kept as an anchor the way check_ledger_checkpoint.py anchors the S328
    finding above.
    """

    def _base_only(self) -> List[str]:
        base = json.loads(TEMPLATE_SETTINGS.read_text(encoding="utf-8"))
        user = json.loads(TEMPLATE_USER_SETTINGS.read_text(encoding="utf-8"))
        return sorted(set(_keyset(base)) - set(_keyset(user)))

    def _user_keys(self) -> List[str]:
        return _keyset(json.loads(TEMPLATE_USER_SETTINGS.read_text(encoding="utf-8")))

    def test_the_two_templates_actually_differ(self) -> None:
        # Non-vacuity first: if user == base, nothing below can fail.
        only = self._base_only()
        self.assertGreaterEqual(
            len(only), 10,
            "settings.user.json omits only %d registrations of settings.base.json "
            "— the profile this class protects no longer exists in that shape"
            % len(only),
        )
        self.assertIn(
            "PreToolUse check_canonical_edit.py", only,
            "check_canonical_edit.py is the rail's example of a deliberately "
            "omitted blocker — if it is now in settings.user.json, re-read that "
            "template's _comment before trusting this class",
        )

    def test_user_ceremony_derives_from_the_user_template(self) -> None:
        self.seed({"hooks": {}})
        self.run_merge(ceremony="user")
        self.assertEqual(
            _keyset(self.result()), self._user_keys(),
            "under ceremony=user the merge over an empty settings.json must "
            "reproduce settings.user.json's registration set exactly",
        )

    def test_user_ceremony_registers_nothing_the_user_template_omits(self) -> None:
        self.seed({"hooks": {}})
        self.run_merge(ceremony="user")
        got = set(_keyset(self.result()))
        leaked = [k for k in self._base_only() if k in got]
        self.assertEqual(
            leaked, [],
            "a user-ceremony upgrade registered hooks the user profile "
            "deliberately omits: %s — the rail round-6 P1, the advisory profile "
            "turned into the maintainer profile" % leaked,
        )

    def test_maintainer_ceremony_derives_from_the_base_template(self) -> None:
        base = json.loads(TEMPLATE_SETTINGS.read_text(encoding="utf-8"))
        self.seed({"hooks": {}})
        self.run_merge(ceremony="maintainer")
        self.assertEqual(_keyset(self.result()), _keyset(base))

    def test_unset_ceremony_never_selects_the_wider_roster(self) -> None:
        # Round 6 said "unset => user"; round 8 refined it: unset => the roster
        # both profiles SHARE (TestUnknownCeremonyTakesTheSharedRoster). What
        # this test keeps is the invariant both rounds agree on.
        self.seed({"hooks": {}})
        self.run_merge(ceremony=None, persist=None)
        got = set(_keyset(self.result()))
        self.assertTrue(got < set(_keyset(json.loads(TEMPLATE_SETTINGS.read_text(encoding="utf-8")))),
                        "with CEREMONY_EFFECTIVE unset the merge selected the full base roster")

    def test_unknown_ceremony_value_never_selects_the_wider_roster(self) -> None:
        self.seed({"hooks": {}})
        self.run_merge(ceremony="wizard")
        got = set(_keyset(self.result()))
        self.assertTrue(got < set(_keyset(json.loads(TEMPLATE_SETTINGS.read_text(encoding="utf-8")))),
                        "an unrecognised ceremony value selected the full base roster")

    def test_a_fresh_user_install_is_already_complete(self) -> None:
        self.seed(json.loads(TEMPLATE_USER_SETTINGS.read_text(encoding="utf-8")))
        before = self.settings_path.read_bytes()
        proc = self.run_merge(ceremony="user")
        self.assertEqual(
            self.settings_path.read_bytes(), before,
            "a settings.json built from settings.user.json must be a byte-level "
            "no-op under ceremony=user (the same idempotency the maintainer path has)",
        )
        self.assertIn("already present", proc.stdout)

    def test_selection_is_live_not_a_fixpoint(self) -> None:
        """Positive control: a hook planted ONLY in the user template is
        registered under ceremony=user and NOT under ceremony=maintainer."""
        planted = "synthetic_user_only_probe_%d.py" % os.getpid()
        user = json.loads(TEMPLATE_USER_SETTINGS.read_text(encoding="utf-8"))
        user["hooks"].setdefault("SessionStart", []).append({
            "hooks": [{"type": "command", "timeout": 5,
                       "command": 'python3 "$CLAUDE_PROJECT_DIR"/.claude/hooks/%s' % planted}],
        })
        self.set_user_template(user)
        self.seed({"hooks": {}})
        self.run_merge(ceremony="user")
        self.assertIn("SessionStart %s" % planted, _keyset(self.result()))
        self.seed({"hooks": {}})
        self.run_merge(ceremony="maintainer")
        self.assertNotIn(
            "SessionStart %s" % planted, _keyset(self.result()),
            "the hook planted only in settings.user.json reached a MAINTAINER "
            "merge — the ceremony is not selecting the template",
        )
        self.assertNotIn(planted, UPGRADE_SH.read_text(encoding="utf-8"))


class TestEnvTravelsWithTheRoster(_MergeHarness):
    """The template's .env is part of the roster (rail round 7, P1).

    A registration is only as advisory as the setting it reads:
    settings.user.json ships check_config_protection.py TOGETHER with
    env.CEO_CONFIG_PROTECTION_ADVISORY=1, and an adopter that receives the hook
    without the key runs the BLOCKING variant. Expectations are derived from
    the shipped artifacts; the one literal key is the rail's anchor.
    """

    def _tpl(self, which: str) -> Dict:
        path = TEMPLATE_USER_SETTINGS if which == "user" else TEMPLATE_SETTINGS
        return json.loads(path.read_text(encoding="utf-8"))

    def test_a_legacy_user_adopter_receives_the_settings_with_the_hooks(self) -> None:
        self.seed({"hooks": {}})
        self.run_merge(ceremony="user")
        res = self.result()
        self.assertEqual(
            res.get("env"), self._tpl("user")["env"],
            "a user adopter that predates the template's .env must receive it "
            "with the hooks — otherwise the hooks run in a mode the profile "
            "never chose",
        )
        self.assertIn(
            "CEO_CONFIG_PROTECTION_ADVISORY", res.get("env", {}),
            "the rail's anchor: this key is what keeps check_config_protection.py "
            "advisory in the user profile",
        )

    def test_an_adopter_value_is_never_overwritten(self) -> None:
        key = sorted(self._tpl("user")["env"])[0]
        self.seed({"hooks": {}, "env": {key: "adopter-kept"}})
        self.run_merge(ceremony="user")
        res = self.result()
        self.assertEqual(res["env"][key], "adopter-kept")
        for k, v in self._tpl("user")["env"].items():
            if k != key:
                self.assertEqual(res["env"].get(k), v, "missing template key %s" % k)

    def test_env_that_is_not_an_object_is_preserved_and_named(self) -> None:
        self.seed({"hooks": {}, "env": ["nope"]})
        proc = self.run_merge(ceremony="user")
        res = self.result()
        self.assertEqual(res["env"], ["nope"], "an odd .env must be PRESERVED, never coerced")
        self.assertEqual(
            _keyset(res), _keyset(self._tpl("user")),
            "the hooks must still merge when only .env has an unexpected shape",
        )
        self.assertIn(".env in settings.json is not an object (found: array)", proc.stderr)
        self.assertIn("PRESERVED:", proc.stdout)
        self.assertIn("NOT APPLIED to env:", proc.stdout)

    def test_a_template_without_env_creates_no_env_key(self) -> None:
        self.set_template({"hooks": {"PreToolUse": [
            {"matcher": "Bash", "hooks": [{"type": "command", "command": "bash h.sh check_x.py"}]},
        ]}})
        self.seed({"hooks": {}})
        self.run_merge(ceremony="maintainer")
        self.assertNotIn("env", self.result(), "no template env => no .env key invented")

    def test_env_merge_is_idempotent_byte_for_byte(self) -> None:
        self.seed({"hooks": {}})
        self.run_merge(ceremony="user")
        first = self.settings_path.read_bytes()
        proc = self.run_merge(ceremony="user")
        self.assertEqual(self.settings_path.read_bytes(), first)
        self.assertIn("already present", proc.stdout)

    def test_dry_run_announces_env_and_writes_nothing(self) -> None:
        self.seed({"hooks": {}})
        before = self.settings_path.read_bytes()
        proc = self.run_merge(dry=True, ceremony="user")
        self.assertIn("would REGISTER env ", proc.stdout)
        self.assertEqual(self.settings_path.read_bytes(), before)

    def test_a_legacy_maintainer_adopter_receives_the_base_env(self) -> None:
        # Stated on purpose: the same rule widens to the maintainer profile —
        # every key settings.base.json declares reaches a legacy adopter that
        # lacks it. The adopter's own values always win (test above).
        self.seed({"hooks": {}})
        self.run_merge(ceremony="maintainer")
        self.assertEqual(self.result().get("env"), self._tpl("base")["env"])


class TestTemplateMustBeExactlyOneDocument(_MergeHarness):
    """A stream of two JSON documents is a malformed roster (rail round 7, P2)."""

    def test_a_two_document_stream_is_refused_and_named(self) -> None:
        one = {"hooks": {"PreToolUse": [
            {"matcher": "Bash", "hooks": [{"type": "command", "command": "bash h.sh check_x.py"}]},
        ]}}
        two = {"hooks": {"PreToolUse": [
            {"matcher": "Bash", "hooks": [{"type": "command", "command": "bash h.sh check_y.py"}]},
        ]}}
        self.template_path.write_text(
            json.dumps(one) + "\n" + json.dumps(two) + "\n", encoding="utf-8",
        )
        self.seed({"hooks": {}})
        before = self.settings_path.read_bytes()
        proc = self.run_merge(ceremony="maintainer")
        self.assertEqual(self.settings_path.read_bytes(), before, "NOTHING may be written")
        self.assertIn("not exactly ONE JSON document (found: 2)", proc.stderr)

    def test_the_shipped_templates_are_one_document_each(self) -> None:
        # Positive control for the guard: the real artifacts pass it.
        for path in (TEMPLATE_SETTINGS, TEMPLATE_USER_SETTINGS):
            self.assertIsInstance(json.loads(path.read_text(encoding="utf-8")), dict)


class TestHiddenScriptIsNotTheCanonicalRegistration(_MergeHarness):
    """The identity key needs BOTH boundaries (rail round 7, P2)."""

    def _check(self, odd_command: str) -> None:
        self.set_template({"hooks": {"PreToolUse": [
            {"matcher": "Bash", "hooks": [{"type": "command", "command": "bash h.sh check_x.py"}]},
        ]}})
        self.seed({"hooks": {"PreToolUse": [
            {"matcher": "Bash", "hooks": [{"type": "command", "command": odd_command}]},
        ]}})
        self.run_merge(ceremony="maintainer")
        res = self.result()
        self.assertIn(
            "PreToolUse check_x.py", _keyset(res),
            "%r was taken for the canonical check_x.py — the canonical "
            "registration was never wired" % odd_command,
        )
        self.assertEqual(len(res["hooks"]["PreToolUse"]), 2, "the odd block must be preserved too")

    def test_a_dot_prefixed_command_does_not_mask_the_canonical_hook(self) -> None:
        self._check("bash h.sh .check_x.py")

    def test_a_dash_prefixed_command_does_not_mask_the_canonical_hook(self) -> None:
        self._check("bash h.sh -check_x.py")

    def test_the_two_extractors_carry_the_same_boundaries(self) -> None:
        self.assertIn("(?<![A-Za-z0-9_.-])", _func_source())
        self.assertIn("(?<![A-Za-z0-9_.-])", _PY_TOKEN.pattern)


class TestUnknownCeremonyRegistersNoHooks(_MergeHarness):
    """INFERRED is not RECORDED (rail rounds 8 and 9).

    With no install-state and no flag the resolver answers `user` only as a
    root-write fail-safe (_CEREMONY_PERSIST=0): the historical install whose
    ceremony nobody knows. Round 8 gave it the hooks both templates share;
    round 9 showed that is not provable either — a shared hook's BEHAVIOUR can
    depend on a setting the profiles disagree on, through code this script
    cannot read. So: NO hooks, only the settings both profiles declare with
    the same value, a NOTE with the opt-in, and a --dry-run that writes
    nothing. All expectations derived from the shipped artifacts.
    """

    def _tpl(self, which: str) -> Dict:
        path = TEMPLATE_USER_SETTINGS if which == "user" else TEMPLATE_SETTINGS
        return json.loads(path.read_text(encoding="utf-8"))

    def _shared_env(self) -> Dict:
        b, u = self._tpl("base")["env"], self._tpl("user")["env"]
        return {k: v for k, v in u.items() if b.get(k) == v}

    def _user_only_env(self) -> List[str]:
        b, u = self._tpl("base")["env"], self._tpl("user")["env"]
        return sorted(k for k in u if k not in b)

    def test_the_fixture_is_not_vacuous(self) -> None:
        self.assertGreaterEqual(len(self._shared_env()), 1, "the profiles must agree on at least one setting")
        self.assertGreaterEqual(len(self._user_only_env()), 1, "the user profile must declare a setting of its own")
        self.assertGreaterEqual(len(_keyset(self._tpl("base"))), 20)

    def test_inferred_user_registers_no_hooks_and_only_the_shared_settings(self) -> None:
        self.seed({"hooks": {}})
        self.run_merge(ceremony="user", persist="0")
        res = self.result()
        self.assertEqual(_keyset(res), [], "an INFERRED ceremony must register NO hooks")
        self.assertEqual(res.get("env"), self._shared_env())
        for k in self._user_only_env():
            self.assertNotIn(k, res.get("env", {}))

    def test_unset_ceremony_registers_no_hooks(self) -> None:
        self.seed({"hooks": {}})
        self.run_merge(ceremony=None, persist=None)
        self.assertEqual(_keyset(self.result()), [])

    def test_unknown_value_registers_no_hooks(self) -> None:
        self.seed({"hooks": {}})
        self.run_merge(ceremony="wizard", persist="1")
        self.assertEqual(_keyset(self.result()), [])

    def test_the_note_names_the_situation_and_the_opt_in(self) -> None:
        self.seed({"hooks": {}})
        proc = self.run_merge(ceremony="user", persist="0")
        self.assertIn("ceremony UNKNOWN", proc.stderr)
        self.assertIn("--ceremony maintainer|user", proc.stderr)
        self.assertIn("WITHHELD:", proc.stderr)
        self.assertIn("PARTIAL (ceremony unknown)", proc.stdout)
        self.assertNotIn("already present", proc.stdout, "an unknown ceremony must never claim completeness")

    def test_a_current_adopter_is_still_told_it_is_partial(self) -> None:
        # Nothing to add (the shared settings are present) — the summary must
        # still say PARTIAL, never the completeness sentence.
        self.seed({"hooks": {}, "env": self._shared_env()})
        before = self.settings_path.read_bytes()
        proc = self.run_merge(ceremony="user", persist="0")
        self.assertEqual(self.settings_path.read_bytes(), before)
        self.assertIn("PARTIAL (ceremony unknown)", proc.stdout)
        self.assertNotIn("already present", proc.stdout)

    def test_the_audit_copy_is_kept_only_when_something_was_written(self) -> None:
        self.seed({"hooks": {}})
        self.run_merge(ceremony="user", persist="0")
        kept = Path(self._tmp) / "bak" / ".claude" / "settings.template-shared.json"
        self.assertTrue(kept.is_file(), "the derived settings must be kept next to the backup on the apply path")
        doc = json.loads(kept.read_text(encoding="utf-8"))
        self.assertEqual(doc.get("hooks"), {})
        self.assertEqual(doc.get("env"), self._shared_env())

    def test_dry_run_writes_nothing_anywhere(self) -> None:
        self.seed({"hooks": {}})
        before = self.settings_path.read_bytes()
        proc = self.run_merge(dry=True, ceremony="user", persist="0")
        self.assertEqual(self.settings_path.read_bytes(), before)
        self.assertFalse((Path(self._tmp) / "bak").exists(), "--dry-run created the backup dir (rail round 9, P1)")
        self.assertEqual(sorted(p.name for p in (self.target / ".claude").iterdir()), ["settings.json"],
                         "--dry-run left something under the adopter's .claude/")
        self.assertIn("would REGISTER env ", proc.stdout)
        self.assertIn("PARTIAL (ceremony unknown)", proc.stdout)

    def test_a_malformed_source_template_is_refused_before_deriving(self) -> None:
        # Round 9, P2: the SOURCES pass the one-document guard, not only the
        # derived file. Two documents in the base template => refused, named.
        base = self._tpl("base")
        self.template_path.write_text(json.dumps(base) + "\n" + json.dumps(base) + "\n", encoding="utf-8")
        self.seed({"hooks": {}})
        before = self.settings_path.read_bytes()
        proc = self.run_merge(ceremony="user", persist="0")
        self.assertEqual(self.settings_path.read_bytes(), before)
        self.assertIn("not exactly ONE JSON document (found: 2)", proc.stderr)

    def test_recorded_user_still_gets_the_full_user_profile(self) -> None:
        # Control: the posture is about PROVENANCE, not about the value.
        self.seed({"hooks": {}})
        self.run_merge(ceremony="user", persist="1")
        self.assertEqual(_keyset(self.result()), _keyset(self._tpl("user")))
        self.assertEqual(self.result().get("env"), self._tpl("user")["env"])

    def test_recorded_maintainer_still_gets_the_full_base_profile(self) -> None:
        self.seed({"hooks": {}})
        self.run_merge(ceremony="maintainer", persist="1")
        self.assertEqual(_keyset(self.result()), _keyset(self._tpl("base")))
        self.assertEqual(self.result().get("env"), self._tpl("base")["env"])


class TestPartiallyPresentMultiCommandBlock(_MergeHarness):
    """Only the MISSING entries of a block are appended (rail round 8, P2)."""

    def _two(self) -> Dict:
        return {"hooks": {"PreToolUse": [
            {"matcher": "Bash", "hooks": [
                {"type": "command", "command": "bash h.sh check_a.py"},
                {"type": "command", "command": "bash h.sh check_b.py"},
            ]},
        ]}}

    def test_only_the_missing_command_is_appended(self) -> None:
        self.set_template(self._two())
        self.seed({"hooks": {"PreToolUse": [
            {"matcher": "Bash", "hooks": [{"type": "command", "command": "bash h.sh check_a.py"}]},
        ]}})
        self.run_merge()
        res = self.result()
        self.assertIn("PreToolUse check_b.py", _keyset(res))
        self.assertEqual(
            len([k for k in _keybag(res) if k == "PreToolUse check_a.py"]), 1,
            "check_a.py was duplicated — the whole block was appended instead of the missing entry",
        )
        appended = res["hooks"]["PreToolUse"][-1]
        self.assertEqual([h["command"] for h in appended["hooks"]], ["bash h.sh check_b.py"])

    def test_a_fully_present_block_is_a_no_op(self) -> None:
        self.set_template(self._two())
        self.seed(self._two())
        before = self.settings_path.read_bytes()
        self.run_merge()
        self.assertEqual(self.settings_path.read_bytes(), before)


class TestTemplateEnvMustBeAnObject(_MergeHarness):
    """A template with a PRESENT, malformed .env is refused whole (rail round 10, P2)."""

    def test_a_malformed_template_env_refuses_the_whole_template(self) -> None:
        self.set_template({"hooks": {"PreToolUse": [
            {"matcher": "Bash", "hooks": [{"type": "command", "command": "bash h.sh check_x.py"}]},
        ]}, "env": [1]})
        self.seed({"hooks": {}})
        before = self.settings_path.read_bytes()
        proc = self.run_merge(ceremony="maintainer")
        self.assertEqual(self.settings_path.read_bytes(), before,
                         "the hooks were written although the template's .env is malformed")
        self.assertIn("structurally invalid", proc.stderr)
        self.assertIn(".env present but not an object: (array)", proc.stderr)

    def test_an_empty_template_env_object_is_fine(self) -> None:
        # Control: the refusal is about SHAPE, not about presence or size.
        self.set_template({"hooks": {"PreToolUse": [
            {"matcher": "Bash", "hooks": [{"type": "command", "command": "bash h.sh check_x.py"}]},
        ]}, "env": {}})
        self.seed({"hooks": {}})
        self.run_merge(ceremony="maintainer")
        self.assertIn("PreToolUse check_x.py", _keyset(self.result()))
        self.assertNotIn("env", self.result(), "an empty template env must not invent a key")


class TestSettingsMustBeExactlyOneDocument(_MergeHarness):
    """An empty settings.json or a stream of objects is refused, named, untouched
    (rail round 11, P2) — jq would otherwise accept the stream."""

    def test_an_empty_settings_is_refused_and_named(self) -> None:
        self.settings_path.write_bytes(b"")
        proc = self.run_merge(ceremony="maintainer")
        self.assertEqual(self.settings_path.read_bytes(), b"")
        self.assertIn("not exactly ONE JSON document (found: 0)", proc.stderr)
        self.assertNotIn("already present", proc.stdout, "an empty file was announced complete")

    def test_a_two_document_settings_is_refused_and_named(self) -> None:
        doc = json.dumps({"hooks": {}})
        self.settings_path.write_text(doc + "\n" + doc + "\n", encoding="utf-8")
        before = self.settings_path.read_bytes()
        proc = self.run_merge(ceremony="maintainer")
        self.assertEqual(self.settings_path.read_bytes(), before)
        self.assertIn("not exactly ONE JSON document (found: 2)", proc.stderr)


class TestScratchStaysOutsideTheTarget(_MergeHarness):
    """The derived shared roster never lands inside the adopter (rail round 11, P2)."""

    def test_tmpdir_inside_the_target_is_not_used_for_scratch(self) -> None:
        inside = self.target / ".claude" / "scratch"
        inside.mkdir()
        self.seed({"hooks": {}})
        proc = self.run_merge(dry=True, ceremony="user", persist="0", tmpdir=str(inside))
        self.assertIn("PARTIAL (ceremony unknown)", proc.stdout)
        left = [p for p in self.target.rglob("*") if p.is_file() and p.name != "settings.json"]
        self.assertEqual(left, [], "scratch or artifacts were left inside the target: %s" % left)
        self.assertEqual(list(inside.iterdir()), [], "the in-target TMPDIR was written to")

    def test_the_scratch_and_the_trap_are_confined_by_construction(self) -> None:
        source = _func_source()
        self.assertIn('mktemp "$( _up_tmpbase )/ceo-shared-roster', source)
        self.assertIn("trap 'rm -f -- \"$_UP_SHARED_TPL_TMP\"' RETURN", source)
        self.assertNotIn('trap "rm', source, "a trap with an interpolated path came back")


class TestNoSecondRoster(TestEnvContext):
    """Anti-rot: the cure is that there is no literal list. Guard it.

    Reads only, but subclasses TestEnvContext per the S283 env-hygiene mandate
    (check-test-env-hygiene.py rejects a bare unittest.TestCase in this tree).
    """

    def test_the_function_names_no_hook_filenames(self) -> None:
        source = _func_source()
        names = sorted(set(_PY_TOKEN.findall(source)))
        self.assertEqual(
            names, [],
            "%s names hook filenames %s — a second roster is exactly the defect "
            "this cure removed (S328: check_ledger_checkpoint.py shipped without "
            "a registration because a literal list did not know about it). Add "
            "the hook to templates/settings/settings.base.json instead."
            % (FUNC_NAME, names),
        )

    def test_the_function_reads_the_template_from_the_source_checkout(self) -> None:
        # assertTrue over assertIn throughout: the container is the whole
        # function and unittest would paste it into every failure message.
        source = _func_source()
        self.assertTrue(
            '"$SOURCE_DIR/templates/settings/settings.base.json"' in source,
            "%s does not read $SOURCE_DIR/templates/settings/settings.base.json "
            "— the roster must be derived from the template in the checkout "
            "that is EXECUTING the upgrade" % FUNC_NAME,
        )
        self.assertTrue(
            '"$SOURCE_DIR/templates/settings/settings.user.json"' in source,
            "%s does not read $SOURCE_DIR/templates/settings/settings.user.json "
            "— a `--ceremony user` adopter would be upgraded from the maintainer "
            "roster (rail round 6, P1)" % FUNC_NAME,
        )
        self.assertTrue(
            "CEREMONY_EFFECTIVE" in source,
            "%s does not consume CEREMONY_EFFECTIVE — the template must be "
            "selected by the ONE ceremony resolution upgrade.sh already makes, "
            "never by a second decision" % FUNC_NAME,
        )
        self.assertTrue(
            "$TARGET/templates/settings" not in source,
            "%s reads the template from $TARGET — that would make the merge a "
            "fixpoint on the adopter's own drift" % FUNC_NAME,
        )

    def test_the_function_is_defined_exactly_once(self) -> None:
        text = UPGRADE_SH.read_text(encoding="utf-8")
        self.assertEqual(text.count("\n%s() {\n" % FUNC_NAME), 1)
        self.assertEqual(text.count("\n%s\n" % FUNC_NAME), 1, "expected one call site")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
