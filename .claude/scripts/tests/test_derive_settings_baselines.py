"""Tests for ``derive-settings-baselines.py`` (lane C2 — fast lane, gap c).

The upgrade.sh T5.4 table (``_T54_BASELINES_JSON``) is derived from what the
GA tags actually SHIPPED in ``templates/settings/settings.base.json``. Every
case below builds a THROWAWAY git repository holding synthetic tags (the
write-path discipline: nothing is written outside the per-test tmp tree), so
the history is controlled byte for byte:

- the shipped history reproduces the hand-kept table (old / superseded / new);
- appending a model moves the previous NEW into ``superseded`` (the class the
  literal used to miss silently);
- a scalar pin change exits 2 (named) unless the key is a declared
  ``SCALAR_SUPERSEDED_CONSUMERS`` entry, and then gains a ``superseded`` list;
- ``--check`` is green on a matching literal and names every difference in
  the DERIVED fields (old / superseded / new); every other field of a leaf is
  a policy attribute, passed through and named, whatever it is called (the
  PLAN-193 wave-opus55 table shape is pinned here);
  unmodelled keys, ambiguous or concatenated literals, a malformed
  ``superseded``, tagless (shallow) clones and non-JSON templates fail
  CLOSED (exit 2) — never a false MATCH;
- tags order by SemVer precedence (``rc.2`` before ``rc.10``);
- prerelease-only values are warned about and included only on request;
- the LIVE upgrade.sh literal matches the LIVE tags (skipped, visibly, when
  the checkout carries no GA tags — a shallow CI clone).

Every test class name carries ``Superseded``: the PLAN-193 W5 Check selects
with ``-k "... or superseded"`` and the module name does not contain that
keyword — ``SupersededSelectorTest`` guards the convention.
"""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / ".claude" / "scripts" / "derive-settings-baselines.py"
import importlib.util  # noqa: E402
_SPEC = importlib.util.spec_from_file_location("derive_settings_baselines", str(SCRIPT))
MOD = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(MOD)  # type: ignore[union-attr]
LIVE_UPGRADE_SH = REPO_ROOT / "scripts" / "upgrade.sh"

_HOOKS_DIR = REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

A4 = ["claude-opus-4-8", "claude-fable-5", "claude-sonnet-4-6", "claude-haiku-4-5"]
A6 = A4 + ["claude-opus-5", "claude-sonnet-5"]
A7 = A6 + ["claude-fable-5-1"]
A8 = A7 + ["claude-opus-5-5"]

_UNSET = object()

#: The PLAN-193 wave-opus55 T5.4 table (WOPUS55.patch r13, sha256 587df9f4…,
#: scripts/upgrade.sh _T54_BASELINES_JSON) with its long strings shortened:
#: model and effortLevel carry the six policy attributes of ADR-149
#: Amendment 3, and model gains the scalar superseded list. Before the
#: cure --check exited 2 on it ("scalar key model gains a 'superseded'
#: list", then "literal effortLevel carries unmodelled field(s):
#: on_migrate_of, on_migrate_note").
WAVE_TABLE: Dict[str, Any] = {
    "availableModels": {"old": A4, "superseded": [A6, A7], "new": A8},
    "fallbackModel": {"old": ["claude-opus-4-8"], "new": ["claude-opus-5"]},
    "model": {"old": None, "superseded": ["claude-opus-5"], "new": "claude-opus-5-5",
              "requires_member_of": "availableModels",
              "notice": "needs Claude Code 2.1.280 or later"},
    "effortLevel": {"old": None, "new": "xhigh", "opt_in": True,
                    "cost_note": "xhigh typically spends more tokens",
                    "on_migrate_of": {"model": {"claude-opus-5": "high"}},
                    "on_migrate_note": "is the default effort of claude-opus-5"},
    "permissions.defaultMode": {"old": "default", "new": "manual"},
}
WAVE_POLICY = ("model.requires_member_of, model.notice, effortLevel.opt_in, "
               "effortLevel.cost_note, effortLevel.on_migrate_of, effortLevel.on_migrate_note")

#: Identity + no system config for the throwaway repo's git (HOME is already
#: TestEnvContext's tmp tree, so no global config is read either).
_GIT_IDENTITY = {
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid",
    "GIT_CONFIG_NOSYSTEM": "1",
}

REGISTRATIONS = {
    "Notification": {"match": "check_notification.py", "entry": {"matcher": "", "hooks": []}},
}


def _template(avail: Any, fallback: Any, model: Any = _UNSET, mode: Any = _UNSET,
              effort: Any = _UNSET) -> Dict[str, Any]:
    data: Dict[str, Any] = {"_comment": "synthetic", "hooks": {}}
    if avail is not _UNSET:
        data["availableModels"] = avail
    if fallback is not _UNSET:
        data["fallbackModel"] = fallback
    if model is not _UNSET:
        data["model"] = model
    if effort is not _UNSET:
        data["effortLevel"] = effort
    perms: Dict[str, Any] = {"deny": ["Bash(git push --force*)"]}
    if mode is not _UNSET:
        perms["defaultMode"] = mode
    data["permissions"] = perms
    return data


OLD_T = _template(A4, ["claude-opus-4-8"])
MID_T = _template(A6, ["claude-opus-5"], "claude-opus-5", "manual")
CUR_T = _template(A7, ["claude-opus-5"], "claude-opus-5", "manual")


def _literal_sh(table: Dict[str, Any], registrations: Optional[Dict[str, Any]] = None,
                assignments: int = 1) -> str:
    body = dict(table)
    body["registrations"] = registrations if registrations is not None else REGISTRATIONS
    lit = "_T54_BASELINES_JSON='" + json.dumps(body, indent=2) + "'\n"
    return "#!/usr/bin/env bash\n# synthetic upgrade.sh\n" + lit * assignments + "echo done\n"


class _SyntheticRepo(TestEnvContext):
    """A throwaway git repo whose tags ship chosen templates."""

    def setUp(self) -> None:
        super().setUp()
        self.repo = self._tmp_root / "synthetic-repo"
        self.repo.mkdir()
        self._git("init", "-q")
        self._n = 0

    def _git(self, *args: str) -> str:
        proc = subprocess.run(
            ["git", "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false",
             "-c", "init.defaultBranch=main"] + list(args),
            cwd=str(self.repo), env=self.subprocess_env(**_GIT_IDENTITY),
            capture_output=True, text=True, timeout=60)
        if proc.returncode != 0:
            raise AssertionError("git {} failed: {}".format(args, proc.stderr))
        return proc.stdout

    def _write_template(self, data: Any, raw: Optional[str] = None) -> None:
        path = self.repo / "templates" / "settings" / "settings.base.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(raw if raw is not None else json.dumps(data, indent=2), encoding="utf-8")

    def ship(self, tag: str, data: Any = None, raw: Optional[str] = None) -> None:
        self._n += 1
        if data is None and raw is None:
            (self.repo / "README").write_text("r{}\n".format(self._n), encoding="utf-8")
        else:
            self._write_template(data, raw)
        self._git("add", "-A")
        self._git("commit", "-q", "--allow-empty", "-m", "c{}".format(self._n))
        self._git("tag", tag)

    def worktree(self, data: Any) -> None:
        self._write_template(data)

    def ship_history(self) -> None:
        """The shape the real repo shipped (v1.0.0 .. v1.4.0 with rc tags)."""
        self.ship("v1.0.0", OLD_T)
        self.ship("v1.1.0-rc.1", OLD_T)
        self.ship("v1.1.0", OLD_T)
        self.ship("v1.2.0", MID_T)
        self.ship("v1.3.0", MID_T)
        self.ship("v1.4.0-rc.1", CUR_T)
        self.ship("v1.4.0", CUR_T)

    def run_script(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPT), "--repo", str(self.repo)] + list(args),
            capture_output=True, text=True, timeout=120, env=self.subprocess_env(**_GIT_IDENTITY))

    def derived(self, *args: str) -> Dict[str, Any]:
        proc = self.run_script(*args)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return json.loads(proc.stdout)

    def write_upgrade_sh(self, text: str) -> Path:
        path = self._tmp_root / "upgrade.sh"
        path.write_text(text, encoding="utf-8")
        return path


class SupersededDeriveFromTagsTest(_SyntheticRepo):

    def test_superseded_derived_from_ga_tags_reproduces_shipped_table(self) -> None:
        self.ship_history()
        table = self.derived()
        self.assertEqual(table, {
            "availableModels": {"old": A4, "superseded": [A6], "new": A7},
            "fallbackModel": {"old": ["claude-opus-4-8"], "new": ["claude-opus-5"]},
            "model": {"old": None, "new": "claude-opus-5"},
            "permissions.defaultMode": {"old": "default", "new": "manual"},
        })
        self.assertEqual(list(table), ["availableModels", "fallbackModel", "model",
                                       "permissions.defaultMode"])

    def test_superseded_gains_previous_new_when_a_model_is_appended(self) -> None:
        self.ship_history()
        self.worktree(_template(A8, ["claude-opus-5"], "claude-opus-5", "manual"))
        spec = self.derived()["availableModels"]
        self.assertEqual(spec["old"], A4)
        self.assertEqual(spec["superseded"], [A6, A7])
        self.assertEqual(spec["new"], A8)

    def test_scalar_change_without_a_declared_consumer_fails_named_exit_2(self) -> None:
        # C-R1-05 / DOCS-R1-01: the DOTTED scalar permissions.defaultMode has
        # no superseded branch in upgrade.sh (ADR-149 A3 walks top-level
        # scalars only); a superseded list there is a promise the code never
        # keeps. Run with the DEFAULT tuple (subprocess), never a patched one.
        self.ship_history()
        self.worktree(_template(A7, ["claude-opus-5"], "claude-opus-5", "acceptEdits"))
        proc = self.run_script("--quiet")
        self.assertEqual(proc.returncode, 2, proc.stderr)
        self.assertIn("scalar key permissions.defaultMode gains a 'superseded' list", proc.stderr)
        self.assertIn("SCALAR_SUPERSEDED_CONSUMERS", proc.stderr)
        self.assertEqual(proc.stdout, "")

    def test_scalar_pin_change_with_a_declared_consumer_derives_superseded(self) -> None:
        # The DEFAULT tuple declares model (the ADR-149 A3 generic branch).
        self.ship_history()
        self.worktree(_template(A8, ["claude-opus-5"], "claude-opus-5-5", "manual"))
        self.assertEqual(self.derived("--quiet")["model"],
                         {"old": None, "superseded": ["claude-opus-5"], "new": "claude-opus-5-5"})

    def test_declared_scalar_consumers_are_the_top_level_scalar_leaves(self) -> None:
        # Mirror of the ADR-149 A3 branch rule: every TOP-LEVEL scalar leaf
        # consults superseded, no dotted one does. A leaf added to _LEAVES
        # must be classified here in the same patch.
        top = tuple(k for k, kind, _a in MOD._LEAVES if kind == "scalar" and "." not in k)
        self.assertEqual(MOD.SCALAR_SUPERSEDED_CONSUMERS, top)

    def test_tags_are_ordered_by_version_not_lexically(self) -> None:
        self.ship("v1.9.0", _template(A4, ["x-old"], mode="default"))
        self.ship("v1.10.0", _template(A6, ["x-new"], mode="default"))
        self.worktree(_template(A6, ["x-new"], mode="default"))
        self.assertEqual(self.derived()["fallbackModel"], {"old": ["x-old"], "new": ["x-new"]})

    def test_prerelease_tags_are_ordered_by_semver_precedence(self) -> None:
        # rc.10 is created FIRST so neither creation order nor lexical order
        # (rc.10 < rc.2) can produce the right OLD by accident.
        self.ship("v1.0.0-rc.10", _template(A6, ["x-rc10"], mode="default"))
        self.ship("v1.0.0-rc.2", _template(A4, ["x-rc2"], mode="default"))
        self.ship("v1.0.0", _template(A7, ["x-ga"], mode="default"))
        self.worktree(_template(A7, ["x-ga"], mode="default"))
        spec = self.derived("--include-prereleases", "--quiet")["fallbackModel"]
        self.assertEqual(spec, {"old": ["x-rc2"], "superseded": [["x-rc10"]], "new": ["x-ga"]})

    def test_prerelease_tags_are_ignored_by_default(self) -> None:
        self.ship("v1.0.0", OLD_T)
        self.ship("v1.1.0-rc.1", _template(A6, ["claude-opus-4-8"]))
        self.ship("v1.1.0", OLD_T)
        self.worktree(OLD_T)
        self.assertNotIn("superseded", self.derived("--quiet")["availableModels"])

    def test_prerelease_only_value_warned_and_superseded_with_flag(self) -> None:
        rc_only = A4 + ["claude-opus-5"]
        self.ship("v1.0.0", OLD_T)
        self.ship("v1.1.0-rc.1", _template(rc_only, ["claude-opus-4-8"]))
        self.ship("v1.1.0", CUR_T)
        proc = self.run_script()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("prerelease v1.1.0-rc.1 shipped availableModels", proc.stderr)
        with_rc = self.derived("--include-prereleases", "--quiet")["availableModels"]
        self.assertEqual(with_rc["superseded"], [rc_only])

    def test_check_quiet_names_a_prerelease_only_value_as_mismatch_exit_1(self) -> None:
        # C-R2-03: --quiet must not hide it; under --check it is a named MISMATCH.
        rc_only = A4 + ["claude-opus-5"]
        self.ship("v1.0.0", OLD_T)
        self.ship("v1.1.0-rc.1", _template(rc_only, ["claude-opus-4-8"]))
        self.ship("v1.1.0", CUR_T)
        self.worktree(CUR_T)
        up = self.write_upgrade_sh(_literal_sh(self.derived("--quiet")))
        proc = self.run_script("--check", str(up), "--quiet")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("prerelease-only: WARNING: prerelease v1.1.0-rc.1 shipped "
                      "availableModels", proc.stdout)
        self.assertEqual(proc.stderr, "")

    def test_tags_without_the_template_are_skipped(self) -> None:
        self.ship("v0.9.0")  # README only — no template at this tag
        self.ship_history()
        proc = self.run_script()
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("v0.9.0: no templates/settings/settings.base.json (skipped)", proc.stderr)
        self.assertEqual(json.loads(proc.stdout)["availableModels"]["old"], A4)

    def test_new_from_ref_reads_the_template_at_that_ref(self) -> None:
        self.ship_history()
        self.worktree(_template(A8, ["claude-opus-5"], "claude-opus-5", "manual"))
        self.assertEqual(self.derived("--new-from", "v1.3.0", "--quiet")["availableModels"]["new"], A6)

    def test_new_from_ref_counts_only_the_tags_in_its_history(self) -> None:
        # C-R2M-08: before the fix every tag counted, so --new-from v1.3.0
        # carried v1.4.0's list as 'superseded' and the v1.3.0 literal never
        # reproduced.
        self.ship_history()
        proc = self.run_script("--new-from", "v1.3.0")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        spec = json.loads(proc.stdout)["availableModels"]
        self.assertEqual(spec, {"old": A4, "new": A6})
        for tag in ("v1.4.0-rc.1", "v1.4.0"):
            self.assertIn("{}: outside the history of the NEW source and newer than every tag "
                          "in it — excluded".format(tag), proc.stderr)
        up = self.write_upgrade_sh(_literal_sh(self.derived("--new-from", "v1.3.0", "--quiet")))
        check = self.run_script("--new-from", "v1.3.0", "--check", str(up), "--quiet")
        self.assertEqual(check.returncode, 0, check.stdout + check.stderr)

    def test_side_branch_ga_tag_that_precedes_new_fails_closed_exit_2(self) -> None:
        self.ship("v1.0.0", OLD_T)
        self._git("checkout", "-q", "-b", "hotfix", "v1.0.0")
        self.ship("v1.0.1", _template(A6, ["claude-opus-4-8"]))
        self._git("checkout", "-q", "main")
        self.ship("v1.1.0", CUR_T)
        self.worktree(CUR_T)
        proc = self.run_script("--quiet")
        self.assertEqual(proc.returncode, 2, proc.stdout + proc.stderr)
        self.assertIn("GA tag v1.0.1 is not in the history of the NEW source (HEAD)", proc.stderr)
        self.assertEqual(proc.stdout, "")

    def test_block_is_the_literal_layout_and_valid_json(self) -> None:
        self.ship_history()
        proc = self.run_script("--quiet")
        lines = proc.stdout.splitlines()
        self.assertEqual(lines[0], "{")
        self.assertIn('    "old": ["claude-opus-4-8","claude-fable-5","claude-sonnet-4-6","claude-haiku-4-5"],', lines)
        self.assertIn('    "old": null,', lines)
        json.loads(proc.stdout)


class SupersededDeriveFailClosedTest(_SyntheticRepo):

    def test_no_ga_tag_fails_closed_with_the_unshallow_hint(self) -> None:
        self.ship("v1.0.0-rc.1", OLD_T)
        self.worktree(OLD_T)
        proc = self.run_script()
        self.assertEqual(proc.returncode, 2)
        self.assertIn("no GA tag", proc.stderr)
        self.assertIn("git fetch --tags --unshallow", proc.stderr)
        self.assertEqual(proc.stdout, "")

    def test_template_that_is_not_json_at_a_tag_fails_closed(self) -> None:
        self.ship("v1.0.0", OLD_T)
        self.ship("v1.1.0", raw="{ not json")
        self.worktree(OLD_T)
        proc = self.run_script()
        self.assertEqual(proc.returncode, 2)
        self.assertIn("v1.1.0:templates/settings/settings.base.json is not JSON", proc.stderr)

    def test_key_absent_from_the_new_template_fails_closed(self) -> None:
        self.ship_history()
        self.worktree(_template(A7, _UNSET, "claude-opus-5", "manual"))
        proc = self.run_script()
        self.assertEqual(proc.returncode, 2)
        self.assertIn("fallbackModel is absent", proc.stderr)

    def test_wrong_value_shape_fails_closed(self) -> None:
        self.ship("v1.0.0", _template("claude-opus-4-8", ["claude-opus-4-8"]))
        self.worktree(OLD_T)
        proc = self.run_script()
        self.assertEqual(proc.returncode, 2)
        self.assertIn("availableModels is not an array of strings", proc.stderr)


class SupersededCheckAgainstLiteralTest(_SyntheticRepo):

    def setUp(self) -> None:
        super().setUp()
        self.ship_history()
        self.table = self.derived("--quiet")

    def test_check_matching_literal_exit_0(self) -> None:
        up = self.write_upgrade_sh(_literal_sh(self.table))
        proc = self.run_script("--check", str(up), "--quiet")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("CHECK: MATCH (4 leaf keys; not derived: registrations)", proc.stdout)

    def test_check_literal_lacking_a_superseded_value_exit_1_and_named(self) -> None:
        table = json.loads(json.dumps(self.table))
        del table["availableModels"]["superseded"]
        up = self.write_upgrade_sh(_literal_sh(table))
        proc = self.run_script("--check", str(up), "--quiet")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("availableModels.superseded: literal LACKS shipped value", proc.stdout)
        self.assertIn(json.dumps(A6, separators=(",", ":")), proc.stdout)

    def test_check_stale_new_after_a_template_bump_exit_1(self) -> None:
        up = self.write_upgrade_sh(_literal_sh(self.table))
        self.worktree(_template(A8, ["claude-opus-5"], "claude-opus-5", "manual"))
        proc = self.run_script("--check", str(up), "--quiet")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("availableModels.new: literal", proc.stdout)
        self.assertIn("availableModels.superseded: literal LACKS shipped value", proc.stdout)

    def test_check_superseded_value_never_shipped_exit_1(self) -> None:
        table = json.loads(json.dumps(self.table))
        table["fallbackModel"]["superseded"] = [["claude-sonnet-5"]]
        up = self.write_upgrade_sh(_literal_sh(table))
        proc = self.run_script("--check", str(up), "--quiet")
        self.assertEqual(proc.returncode, 1)
        self.assertIn("fallbackModel.superseded: literal declares", proc.stdout)

    def test_check_superseded_order_is_membership_not_sequence(self) -> None:
        self.worktree(_template(A8, ["claude-opus-5"], "claude-opus-5", "manual"))
        table = self.derived("--quiet")
        table["availableModels"]["superseded"] = list(reversed(table["availableModels"]["superseded"]))
        up = self.write_upgrade_sh(_literal_sh(table))
        self.assertEqual(self.run_script("--check", str(up), "--quiet").returncode, 0)

    def test_check_unmodelled_literal_key_fails_closed_exit_2(self) -> None:
        table = dict(self.table)
        table["someFutureLeaf"] = {"old": None, "new": "x"}
        up = self.write_upgrade_sh(_literal_sh(table))
        proc = self.run_script("--check", str(up), "--quiet")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("does not model: someFutureLeaf", proc.stderr)

    def test_check_optional_leaf_the_derivation_omitted_is_a_named_mismatch(self) -> None:
        # C-R1-03: no tag and no NEW template ship effortLevel, so the
        # derived table omits it; a literal that still migrates it must not
        # read as MATCH.
        self.assertNotIn("effortLevel", self.table)
        table = json.loads(json.dumps(self.table))
        table["effortLevel"] = {"old": "high", "new": "xhigh"}
        up = self.write_upgrade_sh(_literal_sh(table))
        proc = self.run_script("--check", str(up), "--quiet")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("effortLevel: the literal migrates it", proc.stdout)
        self.assertIn('{"old":"high","new":"xhigh"}', proc.stdout)

    def test_check_passes_a_planted_unknown_attribute_through_and_names_it(self) -> None:
        # DOCS-R1-01 / RCKIT-M1: a policy attribute is ANY non-derived field,
        # whatever its name or value shape — no allow-list to fall behind.
        table = json.loads(json.dumps(self.table))
        table["model"]["surprise_attribute_2027"] = 1
        table["fallbackModel"]["future_rule"] = {"nested": [1, {"deep": None}], "on": True}
        up = self.write_upgrade_sh(_literal_sh(table))
        proc = self.run_script("--check", str(up), "--quiet")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("CHECK: MATCH (4 leaf keys; not derived: registrations)", proc.stdout)
        self.assertIn("POLICY (passed through, not compared): fallbackModel.future_rule, "
                      "model.surprise_attribute_2027", proc.stdout)
        self.assertEqual(proc.stderr, "")

    def test_check_without_policy_attributes_says_none(self) -> None:
        up = self.write_upgrade_sh(_literal_sh(self.table))
        proc = self.run_script("--check", str(up), "--quiet")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("POLICY (passed through, not compared): none", proc.stdout)

    def test_check_a_policy_attribute_does_not_shelter_a_wrong_derived_field(self) -> None:
        table = json.loads(json.dumps(self.table))
        table["model"]["requires_member_of"] = "availableModels"
        table["model"]["new"] = "claude-opus-5-5"
        del table["permissions.defaultMode"]["old"]
        table["permissions.defaultMode"]["opt_in"] = True
        up = self.write_upgrade_sh(_literal_sh(table))
        proc = self.run_script("--check", str(up), "--quiet")
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn('model.new: literal "claude-opus-5-5" != derived "claude-opus-5"', proc.stdout)
        self.assertIn('permissions.defaultMode.old: literal "<missing>" != derived "default"',
                      proc.stdout)
        self.assertIn("POLICY (passed through, not compared): model.requires_member_of, "
                      "permissions.defaultMode.opt_in", proc.stdout)

    def test_check_malformed_superseded_fails_closed_exit_2(self) -> None:
        for bad in (None, {}, "", 0, False, []):
            with self.subTest(superseded=bad):
                table = json.loads(json.dumps(self.table))
                table["fallbackModel"]["superseded"] = bad
                up = self.write_upgrade_sh(_literal_sh(table))
                proc = self.run_script("--check", str(up), "--quiet")
                self.assertEqual(proc.returncode, 2, proc.stdout)
                self.assertIn("fallbackModel.superseded is not a non-empty JSON array", proc.stderr)

    def test_check_concatenated_literal_fails_closed_exit_2(self) -> None:
        base = _literal_sh(self.table)
        for suffix in ("'x'", '"$X"', "x"):
            with self.subTest(suffix=suffix):
                text = base.replace("}'\n", "}'" + suffix + "\n", 1)
                self.assertNotEqual(text, base)
                up = self.write_upgrade_sh(text)
                proc = self.run_script("--check", str(up), "--quiet")
                self.assertEqual(proc.returncode, 2, proc.stdout)
                self.assertIn("concatenated word", proc.stderr)

    def test_check_any_other_write_of_the_variable_fails_closed_exit_2(self) -> None:
        base = _literal_sh(self.table)
        for extra in ("f() {\n  _T54_BASELINES_JSON='{}'\n}\n",
                      "  local _T54_BASELINES_JSON\n",
                      "read -r _T54_BASELINES_JSON < /dev/null\n",
                      ": \"${_T54_BASELINES_JSON:=x}\"\n",
                      "_T54_BASELINES_JSON+='x'\n"):
            with self.subTest(extra=extra):
                up = self.write_upgrade_sh(base + extra)
                proc = self.run_script("--check", str(up), "--quiet")
                self.assertEqual(proc.returncode, 2, proc.stdout)
                self.assertIn("is also written at line(s)", proc.stderr)

    def test_check_reads_and_comments_are_not_writes(self) -> None:
        extra = ("# the table lives in _T54_BASELINES_JSON\n"
                 "printf '%s\\n' \"$_T54_BASELINES_JSON\"\n"
                 "echo \"${_T54_BASELINES_JSON}\" \"${_T54_BASELINES_JSON:-}\"\n")
        up = self.write_upgrade_sh(_literal_sh(self.table) + extra)
        proc = self.run_script("--check", str(up), "--quiet")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_check_ambiguous_or_missing_literal_fails_closed_exit_2(self) -> None:
        for text, needle in (
            (_literal_sh(self.table, assignments=2), "found 2"),
            ("#!/usr/bin/env bash\necho no table\n", "found 0"),
            ("_T54_BASELINES_JSON='{not json'\n", "is not JSON"),
        ):
            with self.subTest(needle=needle):
                up = self.write_upgrade_sh(text)
                proc = self.run_script("--check", str(up), "--quiet")
                self.assertEqual(proc.returncode, 2)
                self.assertIn(needle, proc.stderr)


class SupersededWaveTableShapeTest(_SyntheticRepo):
    """The PLAN-193 wave-opus55 literal against a history shaped like the
    real one (RED before the cure: exit 2)."""

    def setUp(self) -> None:
        super().setUp()
        self.ship_history()
        self.worktree(_template(A8, ["claude-opus-5"], "claude-opus-5-5", "manual", "xhigh"))

    def check(self, table: Dict[str, Any]) -> subprocess.CompletedProcess:
        up = self.write_upgrade_sh(_literal_sh(table))
        return self.run_script("--check", str(up), "--quiet")

    def test_wave_table_shape_matches_and_names_every_policy_attribute(self) -> None:
        proc = self.check(WAVE_TABLE)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("CHECK: MATCH (5 leaf keys; not derived: registrations)", proc.stdout)
        self.assertIn("POLICY (passed through, not compared): " + WAVE_POLICY, proc.stdout)
        self.assertEqual(proc.stderr, "")

    def test_wave_policy_fields_alone_no_longer_break_the_check(self) -> None:
        # Isolates the policy class from the scalar-consumer tuple: model is
        # NOT moved, so no scalar superseded list is derived; before the cure
        # this exited 2 on "literal effortLevel carries unmodelled field(s)".
        self.worktree(_template(A7, ["claude-opus-5"], "claude-opus-5", "manual", "xhigh"))
        table = json.loads(json.dumps(WAVE_TABLE))
        table["availableModels"] = {"old": A4, "superseded": [A6], "new": A7}
        table["model"] = {"old": None, "new": "claude-opus-5"}
        proc = self.check(table)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("effortLevel.on_migrate_of, effortLevel.on_migrate_note", proc.stdout)

    def test_wrong_scalar_superseded_still_fails_named_exit_1(self) -> None:
        table = json.loads(json.dumps(WAVE_TABLE))
        table["model"]["superseded"] = ["claude-opus-4-8"]
        proc = self.check(table)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn('model.superseded: literal LACKS shipped value "claude-opus-5"', proc.stdout)
        self.assertIn('model.superseded: literal declares "claude-opus-4-8" which no derived '
                      'tag shipped', proc.stdout)

    def test_missing_array_superseded_value_still_fails_named_exit_1(self) -> None:
        table = json.loads(json.dumps(WAVE_TABLE))
        table["availableModels"]["superseded"] = [A6]
        proc = self.check(table)
        self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
        self.assertIn("availableModels.superseded: literal LACKS shipped value "
                      + json.dumps(A7, separators=(",", ":")), proc.stdout)

    def test_malformed_superseded_beside_policy_fields_fails_closed_exit_2(self) -> None:
        for bad in (None, [], "claude-opus-5"):
            with self.subTest(superseded=bad):
                table = json.loads(json.dumps(WAVE_TABLE))
                table["model"]["superseded"] = bad
                proc = self.check(table)
                self.assertEqual(proc.returncode, 2, proc.stdout)
                self.assertIn("model.superseded is not a non-empty JSON array", proc.stderr)

    def test_wrong_old_or_new_beside_policy_fields_fails_named_exit_1(self) -> None:
        for leaf, field, bad in (("effortLevel", "new", "high"), ("effortLevel", "old", "xhigh"),
                                 ("model", "new", "claude-opus-5")):
            with self.subTest(leaf=leaf, field=field):
                table = json.loads(json.dumps(WAVE_TABLE))
                table[leaf][field] = bad
                proc = self.check(table)
                self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
                self.assertIn("{}.{}: literal {}".format(leaf, field, json.dumps(bad)), proc.stdout)


class SupersededLayoutCompareTest(TestEnvContext):
    """The paste-ready comparison over a literal with policy fields."""

    LITERAL = [
        '  "model": {',
        '    "old": null,',
        '    "superseded": ["claude-opus-5"],',
        '    "new": "claude-opus-5-5",',
        '    "requires_member_of": "availableModels",',
        '    "notice": "needs a newer CLI"',
        '  },',
        '  "effortLevel": {',
        '    "old": null,',
        '    "new": "xhigh",',
        '    "opt_in": true,',
        '    "cost_note": "costs more",',
        '    "on_migrate_of": {"model": {"claude-opus-5": "high"}},',
        '    "on_migrate_note": "the claude-opus-5 default"',
        '  },',
        '  "permissions.defaultMode": {',
        '    "old": "default",',
        '    "a_future_rule": {',
        '      "spread": ["over", "lines"],',
        '      "old": "not a field of the leaf"',
        '    },',
        '    "new": "manual"',
        '  }',
    ]
    TABLE = {"model": {"old": None, "superseded": ["claude-opus-5"], "new": "claude-opus-5-5"},
             "effortLevel": {"old": None, "new": "xhigh"},
             "permissions.defaultMode": {"old": "default", "new": "manual"}}

    def test_policy_field_lines_are_dropped_and_order_still_counts(self) -> None:
        literal = self.LITERAL
        table = self.TABLE
        derived = MOD.render_block(table).splitlines()[1:-1]
        self.assertEqual(MOD.leaf_lines_for_compare(derived), MOD.leaf_lines_for_compare(literal))
        swapped = MOD.render_block({k: table[k] for k in ("model", "permissions.defaultMode",
                                                          "effortLevel")}).splitlines()[1:-1]
        self.assertNotEqual(MOD.leaf_lines_for_compare(swapped),
                            MOD.leaf_lines_for_compare(literal))
        self.assertEqual([k for k, _kind, _a in MOD._LEAVES].index("effortLevel") + 1,
                         [k for k, _kind, _a in MOD._LEAVES].index("permissions.defaultMode"))

    def test_a_changed_derived_value_still_differs_beside_policy_lines(self) -> None:
        table = json.loads(json.dumps(self.TABLE))
        table["effortLevel"]["new"] = "high"
        derived = MOD.render_block(table).splitlines()[1:-1]
        self.assertNotEqual(MOD.leaf_lines_for_compare(derived),
                            MOD.leaf_lines_for_compare(self.LITERAL))

    def test_policy_attributes_lists_every_non_derived_field_in_literal_order(self) -> None:
        literal = json.loads(json.dumps(WAVE_TABLE))
        literal["registrations"] = REGISTRATIONS
        self.assertEqual(", ".join(MOD.policy_attributes(literal)), WAVE_POLICY)


class SupersededLiveRepoTest(TestEnvContext):
    """The real upgrade.sh literal against the real GA tags of this checkout."""

    def _has_ga_tags(self) -> bool:
        proc = subprocess.run(["git", "-C", str(REPO_ROOT), "tag", "-l", "v1.4.0"],
                              capture_output=True, text=True, timeout=60)
        return proc.returncode == 0 and proc.stdout.strip() == "v1.4.0"

    def test_live_upgrade_sh_superseded_matches_ga_tags(self) -> None:
        if not self._has_ga_tags():
            self.skipTest("no GA tags in this checkout (shallow clone) — derivation needs them")
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--repo", str(REPO_ROOT), "--check", str(LIVE_UPGRADE_SH),
             "--quiet"], capture_output=True, text=True, timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)

    def test_live_block_is_paste_ready_for_the_literal(self) -> None:
        if not self._has_ga_tags():
            self.skipTest("no GA tags in this checkout (shallow clone) — derivation needs them")
        proc = subprocess.run([sys.executable, str(SCRIPT), "--repo", str(REPO_ROOT), "--quiet"],
                              capture_output=True, text=True, timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        text = LIVE_UPGRADE_SH.read_text(encoding="utf-8")
        start = text.index("_T54_BASELINES_JSON='{\n") + len("_T54_BASELINES_JSON='{\n")
        leaf = text[start:text.index('  "registrations": {', start)].rstrip("\n").rstrip(",")
        derived: List[str] = proc.stdout.splitlines()[1:-1]
        # C-R2M-02: a literal may carry policy attributes the block never
        # renders (PLAN-193's model/effortLevel leaves do); those fields are
        # dropped whole and trailing commas ignored, everything else compares
        # byte for byte.
        self.assertEqual(MOD.leaf_lines_for_compare(derived),
                         MOD.leaf_lines_for_compare(leaf.splitlines()))
        if not MOD.policy_attributes(MOD.extract_literal(LIVE_UPGRADE_SH)):
            self.assertEqual("\n".join(derived), leaf)



class SupersededSelectorTest(TestEnvContext):
    """PLAN-193 W5 selects with ``-k "... or superseded"``: every test class
    here must carry the keyword, or the gate silently stops seeing it."""

    def test_every_test_class_carries_the_selector_keyword(self) -> None:
        classes = [obj for _name, obj in sorted(globals().items())
                   if isinstance(obj, type) and issubclass(obj, unittest.TestCase)
                   and obj.__module__ == __name__
                   and any(n.startswith("test") for n in vars(obj))]
        self.assertTrue(classes)
        self.assertEqual([c.__name__ for c in classes
                          if "superseded" not in c.__name__.lower()], [])


if __name__ == "__main__":
    unittest.main()
