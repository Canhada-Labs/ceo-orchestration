"""PLAN-163 T5.4/T5.5 — baseline-aware settings-migration oracles (upgrade.sh).

Covers the upgrade.sh `_migrate_settings_baseline` step:

* one fixture per LEAF KEY x branch — absent / equal-to-OLD-baseline /
  customized — for the four migrated keys (``model``, ``availableModels``,
  ``fallbackModel``, ``permissions.defaultMode``). The top-level scalar
  ``model`` pin (ADR-181 T1.1) has NO old-baseline value: absence IS the old
  baseline (SET to the new pin), any present value != the pin is preserved;
* a MIXED-state fixture (one key per branch simultaneously + an unrelated
  custom hook registration that must survive);
* the idempotency oracle (run twice == byte-identical settings.json);
* the T3.4 feature gate for the new-event registrations (DirectoryAdded /
  Notification): default OFF adds nothing; ON adds the canonical entry only
  when missing and PRESERVES customized registrations under the same event;
* the --dry-run preview (no write, no backup dir);
* the PLAN-164 pair-rail registration-timeout VALUE migration (old cap 60
  -> template-derived new cap IFF current value == 60; adopter-custom values
  preserved; round 2 idempotent) — TestPairRailTimeoutValueMigration.

T5.5 U1-U3 mapping:
  U1 (post-install)  -> template parity: templates/settings/settings.base.json
                        must already carry the NEW baselines (install.sh copies
                        the template verbatim for fresh installs).
  U2 (post-upgrade)  -> the per-branch assertions here (baseline -> new;
                        customized -> preserved + named WARN).
  U3 (idempotency)   -> run-twice byte-identity.

EVERY expectation is DERIVED from the artifact under test —
``bash scripts/upgrade.sh --print-settings-baselines`` (the normative T5.4
table) and the template file itself — never re-hardcoded literals. The
customized-branch assertions prove the oracle does NOT require the new value
unconditionally (that would contradict preservation).

The migration is driven through the ``--settings-migrate-only`` seam of the
REAL scripts/upgrade.sh against a scratch target, so each branch is provable
without a full-tree copy. stdlib-only; Python >= 3.9.
"""
from __future__ import annotations

import atexit
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[3]
UPGRADE_SH = REPO_ROOT / "scripts" / "upgrade.sh"
TEMPLATE_SETTINGS = REPO_ROOT / "templates" / "settings" / "settings.base.json"

# S283 env-hygiene baseline: new test classes subclass TestEnvContext
# (import pattern mirrors test_generate_available_models.py in this dir).
_HOOKS_DIR = REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

_BASELINES_CACHE: Optional[Dict] = None


def baselines() -> Dict:
    """The normative T5.4 table, derived FROM THE ARTIFACT (never hardcoded)."""
    global _BASELINES_CACHE
    if _BASELINES_CACHE is None:
        proc = subprocess.run(
            ["bash", str(UPGRADE_SH), "--print-settings-baselines"],
            capture_output=True, text=True, timeout=60,
            env=_clean_env(None),
        )
        if proc.returncode != 0:
            raise AssertionError(
                "upgrade.sh --print-settings-baselines rc=%s stderr=%s"
                % (proc.returncode, proc.stderr)
            )
        _BASELINES_CACHE = json.loads(proc.stdout)
    return _BASELINES_CACHE


#: ADR-149 Amendment 3 (fix round r13, vX): the directory of the FAKE
#: claude that every spawn of this module finds first on PATH (created once
#: per process, removed at exit).
_CLAUDE_STUB_DIR: Optional[str] = None


def _supported_claude_dir() -> str:
    """A directory holding only a FAKE ``claude`` that reports the Claude
    Code floor of scripts/upgrade.sh as its version. install.sh and
    upgrade.sh read the claude found on PATH (ADR-149 A3.2 item 11); a test
    must never read the host CLI - one below the floor would turn every
    spawn into exit 6, and any host version would decide the output. Under
    pytest the suite isolation layer (_lib/test_isolation.py, Axis 4) puts
    one first on PATH too; this module keeps its own so its spawns hold the
    floor under ``python -m unittest`` as well, where no conftest runs."""
    global _CLAUDE_STUB_DIR
    if _CLAUDE_STUB_DIR is None or not os.path.isfile(
            os.path.join(_CLAUDE_STUB_DIR, "claude")):
        floor = [ln.split("=", 1)[1].strip('"')
                 for ln in UPGRADE_SH.read_text(encoding="utf-8").splitlines()
                 if ln.startswith("CC_FLOOR_VERSION=")]
        if len(floor) != 1:
            raise AssertionError("scripts/upgrade.sh must carry ONE "
                                 "CC_FLOOR_VERSION line (found %d)" % len(floor))
        stub_dir = tempfile.mkdtemp(prefix="t54-claude-stub-")
        atexit.register(shutil.rmtree, stub_dir, True)
        exe = os.path.join(stub_dir, "claude")
        with open(exe, "w", encoding="utf-8") as fh:
            fh.write("#!/bin/sh\necho '%s (Claude Code)'\n" % floor[0])
        os.chmod(exe, 0o755)
        _CLAUDE_STUB_DIR = stub_dir
    return _CLAUDE_STUB_DIR


def _clean_env(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    env = os.environ.copy()
    # The T3.4 gate env override must not leak in from the outer session.
    env.pop("CEO_T34_NEW_EVENT_REGISTRATIONS", None)
    # ADR-149 Amendment 3 (fix round r13, vX): a FAKE claude at the floor
    # first on PATH, never the host CLI; a test that needs another CLI
    # (TestClaudeCodeFloor) passes its own PATH through ``extra``.
    env["PATH"] = _supported_claude_dir() + os.pathsep + env.get("PATH", "")
    if extra:
        env.update(extra)
    return env


class _MigrationHarness(TestEnvContext):
    """Scratch-target harness driving upgrade.sh --settings-migrate-only."""

    def setUp(self) -> None:
        super().setUp()
        self._tmp = tempfile.mkdtemp(prefix="t54-mig-")
        self.addCleanup(shutil.rmtree, self._tmp, True)
        self.target = Path(self._tmp) / "target"
        (self.target / ".claude").mkdir(parents=True)

    @property
    def settings_path(self) -> Path:
        return self.target / ".claude" / "settings.json"

    def seed(self, settings_obj: Dict) -> None:
        self.settings_path.write_text(
            json.dumps(settings_obj, indent=2) + "\n", encoding="utf-8"
        )

    def run_migration(
        self,
        *,
        dry: bool = False,
        gate_on: bool = False,
        extra_args: Optional[List[str]] = None,
    ) -> "subprocess.CompletedProcess[str]":
        args = [
            "bash", str(UPGRADE_SH), str(self.target),
            "--settings-migrate-only", "--no-replay", "--no-deprecation-warn",
        ]
        if dry:
            args.append("--dry-run")
        if extra_args:
            args.extend(extra_args)
        extra_env = {"CEO_T34_NEW_EVENT_REGISTRATIONS": "1"} if gate_on else None
        proc = subprocess.run(
            args, capture_output=True, text=True, timeout=120,
            env=_clean_env(extra_env),
        )
        self.assertEqual(
            proc.returncode, 0,
            "upgrade.sh rc=%s\nstdout=%s\nstderr=%s"
            % (proc.returncode, proc.stdout, proc.stderr),
        )
        return proc

    def read_settings(self) -> Dict:
        return json.loads(self.settings_path.read_text(encoding="utf-8"))


class TestArrayLeafKeyBranches(_MigrationHarness):
    """U2 — per-branch oracles for the two ARRAY leaf keys.

    One (key x branch) case per test-method invocation; the branch matrix is
    iterated with subTest so each fixture is individually reported.
    """

    ARRAY_KEYS: Tuple[str, ...] = ("availableModels", "fallbackModel")

    def test_absent_key_gets_new_baseline(self) -> None:
        for key in self.ARRAY_KEYS:
            with self.subTest(key=key, branch="absent"):
                self.setUp()
                self.seed({})
                proc = self.run_migration()
                self.assertEqual(self.read_settings()[key],
                                 baselines()[key]["new"])
                self.assertIn("SET (absent -> new baseline): " + key,
                              proc.stdout)

    def test_old_baseline_is_migrated(self) -> None:
        for key in self.ARRAY_KEYS:
            with self.subTest(key=key, branch="equal-old"):
                self.setUp()
                self.seed({key: list(baselines()[key]["old"])})
                proc = self.run_migration()
                self.assertEqual(self.read_settings()[key],
                                 baselines()[key]["new"])
                self.assertIn(
                    "MIGRATE (matched OLD baseline -> new baseline): " + key,
                    proc.stdout,
                )

    def test_customized_is_preserved_with_named_warn(self) -> None:
        """The oracle must NOT require the new value unconditionally."""
        for key in self.ARRAY_KEYS:
            for label, custom in (
                # extra id appended by the adopter
                ("extra-id", list(baselines()[key]["old"]) + ["my-custom-model"]),
                # same values, adopter-reordered: byte-compare => CUSTOMIZED
                ("reordered", list(reversed(baselines()[key]["old"]))),
            ):
                if custom == baselines()[key]["old"] or \
                        custom == baselines()[key]["new"]:
                    # single-element arrays reverse to themselves — that is
                    # the equal-old branch, not a customized fixture.
                    continue
                with self.subTest(key=key, branch="customized", case=label):
                    self.setUp()
                    self.seed({key: custom})
                    proc = self.run_migration()
                    self.assertEqual(self.read_settings()[key], custom)
                    self.assertNotEqual(self.read_settings()[key],
                                        baselines()[key]["new"])
                    self.assertIn("WARNING: " + key + " is ADOPTER-CUSTOMIZED",
                                  proc.stderr)

    def test_already_new_baseline_is_noop_without_warn(self) -> None:
        for key in self.ARRAY_KEYS:
            with self.subTest(key=key, branch="already-new"):
                self.setUp()
                self.seed({key: list(baselines()[key]["new"])})
                proc = self.run_migration()
                self.assertEqual(self.read_settings()[key],
                                 baselines()[key]["new"])
                self.assertIn("OK (already at new baseline): " + key,
                              proc.stdout)
                self.assertNotIn("WARNING: " + key, proc.stderr)


class TestSupersededShippedBaseline(_MigrationHarness):
    """ADR-149 Amendment 2 (S338) — the ``superseded`` list of an ARRAY leaf.

    v1.2.0 and v1.3.0 SHIPPED the 6-id availableModels that was the NEW
    baseline until claude-fable-5-1 was appended. Under the 3-state policy
    that array is neither OLD nor NEW, so without ``superseded`` every such
    adopter would be read as ADOPTER-CUSTOMIZED and never receive the
    seventh id — silently, because the install/upgrade parity e2e treats
    settings.json as an ACCEPTED divergence (keys, not bytes). The list
    carries frozen historical literals, the
    same doctrine as SUPERSEDED_SHIPPED_CAPS below; the match is byte-exact
    (values AND order), so a reordered array is still PRESERVED.
    """

    #: The availableModels array v1.2.0 AND v1.3.0 shipped (frozen literal:
    #: `git show v1.3.0:templates/settings/settings.base.json`). Must stay
    #: declared as superseded for as long as such installs exist.
    SHIPPED_V12_V13_AVAILABLE = [
        "claude-opus-4-8", "claude-fable-5", "claude-sonnet-4-6",
        "claude-haiku-4-5", "claude-opus-5", "claude-sonnet-5",
    ]

    def test_shipped_6_id_array_is_declared_superseded(self) -> None:
        spec = baselines()["availableModels"]
        self.assertIn(self.SHIPPED_V12_V13_AVAILABLE, spec.get("superseded", []))
        # Non-vacuity: it is neither the OLD nor the NEW baseline.
        self.assertNotEqual(self.SHIPPED_V12_V13_AVAILABLE, spec["old"])
        self.assertNotEqual(self.SHIPPED_V12_V13_AVAILABLE, spec["new"])

    #: The availableModels array every release from v1.4.0-rc.1 to the
    #: last one before ADR-149 Amendment 3 (S357) shipped (frozen literal,
    #: measured S357 with `git show <tag>:templates/settings/
    #: settings.base.json`) — superseded by that amendment.
    SHIPPED_V14_AVAILABLE = SHIPPED_V12_V13_AVAILABLE + ["claude-fable-5-1"]

    def test_new_baseline_appends_fable51_then_opus55_last(self) -> None:
        new = baselines()["availableModels"]["new"]
        self.assertEqual(new[-1], "claude-opus-5-5")
        self.assertEqual(new[:-1], self.SHIPPED_V14_AVAILABLE,
                         "order is normative: append at the END only")

    def test_shipped_7_id_array_is_declared_superseded(self) -> None:
        spec = baselines()["availableModels"]
        self.assertIn(self.SHIPPED_V14_AVAILABLE, spec.get("superseded", []))
        self.assertNotEqual(self.SHIPPED_V14_AVAILABLE, spec["new"])

    def test_every_superseded_array_migrates_to_new(self) -> None:
        for key in ("availableModels", "fallbackModel"):
            for sup in baselines()[key].get("superseded", []):
                with self.subTest(key=key, superseded=sup):
                    self.setUp()
                    self.seed({key: list(sup)})
                    proc = self.run_migration()
                    self.assertEqual(self.read_settings()[key],
                                     baselines()[key]["new"])
                    self.assertIn(
                        "MIGRATE (matched SUPERSEDED shipped baseline -> "
                        "new baseline): " + key,
                        proc.stdout,
                    )
                    self.assertNotIn("WARNING: " + key + " is ADOPTER-CUSTOMIZED",
                                     proc.stderr)

    def test_availableModels_superseded_is_exercised(self) -> None:
        """The loop above must not pass vacuously on an empty list."""
        self.assertTrue(baselines()["availableModels"].get("superseded"))

    def test_reordered_superseded_is_customized_and_preserved(self) -> None:
        sup = list(baselines()["availableModels"]["superseded"][0])
        custom = list(reversed(sup))
        self.assertNotEqual(custom, sup)
        self.seed({"availableModels": custom})
        proc = self.run_migration()
        self.assertEqual(self.read_settings()["availableModels"], custom)
        self.assertIn("WARNING: availableModels is ADOPTER-CUSTOMIZED",
                      proc.stderr)

    def test_second_run_after_superseded_migration_is_noop(self) -> None:
        sup = baselines()["availableModels"]["superseded"][0]
        self.seed({"availableModels": list(sup)})
        self.run_migration()
        first = self.settings_path.read_bytes()
        proc = self.run_migration()
        self.assertEqual(self.settings_path.read_bytes(), first)
        self.assertIn("OK (already at new baseline): availableModels",
                      proc.stdout)


class TestDefaultModeBranches(_MigrationHarness):
    """U2 — per-branch oracles for permissions.defaultMode.

    Read contract: _lib/effective_config.py, its permissions.defaultMode
    row and _check_settings_layer (d) (a stripped string under the
    permissions object).
    """

    def _spec(self) -> Dict:
        return baselines()["permissions.defaultMode"]

    def test_absent_permissions_object(self) -> None:
        self.seed({})
        proc = self.run_migration()
        self.assertEqual(self.read_settings()["permissions"]["defaultMode"],
                         self._spec()["new"])
        self.assertIn("SET (absent -> new baseline): permissions.defaultMode",
                      proc.stdout)

    def test_absent_key_in_existing_permissions_preserves_siblings(self) -> None:
        self.seed({"permissions": {"deny": ["Bash(git push --force*)"]}})
        self.run_migration()
        perms = self.read_settings()["permissions"]
        self.assertEqual(perms["defaultMode"], self._spec()["new"])
        self.assertEqual(perms["deny"], ["Bash(git push --force*)"])

    def test_old_baseline_is_migrated(self) -> None:
        self.seed({"permissions": {"defaultMode": self._spec()["old"]}})
        proc = self.run_migration()
        self.assertEqual(self.read_settings()["permissions"]["defaultMode"],
                         self._spec()["new"])
        self.assertIn(
            "MIGRATE (matched OLD baseline -> new baseline): "
            "permissions.defaultMode",
            proc.stdout,
        )

    def test_customized_is_preserved_with_named_warn(self) -> None:
        self.seed({"permissions": {"defaultMode": "acceptEdits"}})
        proc = self.run_migration()
        self.assertEqual(self.read_settings()["permissions"]["defaultMode"],
                         "acceptEdits")
        self.assertIn(
            "WARNING: permissions.defaultMode is ADOPTER-CUSTOMIZED",
            proc.stderr,
        )


class TestModelScalarLeaf(_MigrationHarness):
    """U2 — per-branch oracles for the top-level SCALAR ``model`` leaf.

    ADR-181 T1.1 anti-silent-flip: the OLD baseline carries NO top-level
    ``model`` key, so absence == the old baseline and is SET to the new pin.
    A present value != the new pin is adopter-custom and PRESERVED. The new
    pin must be a member of ``availableModels`` (enforceAvailableModels).
    """

    def _spec(self) -> Dict:
        return baselines()["model"]

    def test_new_pin_is_a_member_of_available_models(self) -> None:
        """enforceAvailableModels invariant: the pinned value is allowlisted."""
        self.assertIn(self._spec()["new"],
                      baselines()["availableModels"]["new"])

    def test_old_baseline_is_absence(self) -> None:
        """The table documents the old model baseline as ABSENT (null)."""
        self.assertIsNone(self._spec()["old"])

    def test_absent_key_gets_new_baseline(self) -> None:
        self.seed({})
        proc = self.run_migration()
        self.assertEqual(self.read_settings()["model"], self._spec()["new"])
        self.assertIn(
            "SET (absent [== old baseline] -> new baseline): model",
            proc.stdout,
        )

    def test_already_new_baseline_is_noop_without_warn(self) -> None:
        self.seed({"model": self._spec()["new"]})
        proc = self.run_migration()
        self.assertEqual(self.read_settings()["model"], self._spec()["new"])
        self.assertIn("OK (already at new baseline): model", proc.stdout)
        self.assertNotIn("WARNING: model", proc.stderr)

    def test_customized_is_preserved_with_named_warn(self) -> None:
        """The oracle must NOT require the new value unconditionally.

        Both a fleet member (!= new pin) and an off-fleet id must survive.
        """
        for custom in ("claude-sonnet-5", "my-custom-model"):
            self.assertNotEqual(custom, self._spec()["new"])
            with self.subTest(custom=custom):
                self.setUp()
                self.seed({"model": custom})
                proc = self.run_migration()
                self.assertEqual(self.read_settings()["model"], custom)
                self.assertNotEqual(self.read_settings()["model"],
                                    self._spec()["new"])
                self.assertIn("WARNING: model is ADOPTER-CUSTOMIZED",
                              proc.stderr)


class TestModelPinConditionalOnAllowlist(_MigrationHarness):
    """FXdelta (C6) — the model-pin SET is CONDITIONAL on the pin being a
    member of the EFFECTIVE availableModels resolved earlier in the same pass.

    The availableModels leaf is processed BEFORE the model leaf (order is
    normative — new ids append at the array tail, ADR-149). An adopter who
    CUSTOMIZED availableModels to EXCLUDE the pin must NOT be handed a session-
    default pin outside their own allowlist (enforceAvailableModels would
    reject it). An explicit ``model: null`` is treated as ABSENT for the SET
    decision (null is not a deliberate model choice), never as a customized
    value. Every expectation is DERIVED from the artifact baselines().
    """

    def _pin(self) -> str:
        return baselines()["model"]["new"]

    def _pin_not_applied(self) -> str:
        """ADR-149 Amendment 3 (S357): the generic scalar branch names the
        key, the gating array and the FRAMEWORK value (never the adopter
        value) — derived from the artifact, not a literal pin."""
        return ("WARNING: model NOT migrated: " + self._pin()
                + " is not an exact entry of the adopter availableModels"
                " (the harness may still admit it by prefix) - model"
                " left untouched")

    def _with_opus5(self) -> List[str]:
        """The new availableModels baseline — contains the pin by construction."""
        new = list(baselines()["availableModels"]["new"])
        self.assertIn(self._pin(), new)
        return new

    def _custom_without_pin(self) -> List[str]:
        """A CUSTOMIZED allowlist (not old, not new baseline) that EXCLUDES the
        pin — derived by appending an adopter-only id to the OLD baseline."""
        custom = list(baselines()["availableModels"]["old"]) + ["adopter-only-model"]
        self.assertNotIn(self._pin(), custom)
        self.assertNotEqual(custom, baselines()["availableModels"]["old"])
        self.assertNotEqual(custom, baselines()["availableModels"]["new"])
        return custom

    def test_a_custom_allowlist_excludes_pin_model_absent_not_set(self) -> None:
        """(a) availableModels customized w/o pin + model absent -> NOT set + WARN."""
        custom = self._custom_without_pin()
        self.seed({"availableModels": custom})
        proc = self.run_migration()
        self.assertNotIn(
            "model", self.read_settings(),
            "model pin must NOT be written outside the effective allowlist",
        )
        # the customized allowlist itself is preserved (unrelated branch)
        self.assertEqual(self.read_settings()["availableModels"], custom)
        self.assertIn(self._pin_not_applied(), proc.stderr)

    def test_b_old_baseline_migrates_then_model_is_set(self) -> None:
        """(b) availableModels == OLD baseline (migrates -> new, gains pin) +
        model absent -> pin IS set (effective allowlist contains it)."""
        self.seed({"availableModels": list(baselines()["availableModels"]["old"])})
        proc = self.run_migration()
        self.assertEqual(self.read_settings()["availableModels"],
                         baselines()["availableModels"]["new"])
        self.assertEqual(self.read_settings()["model"], self._pin())
        self.assertIn(
            "SET (absent [== old baseline] -> new baseline): model",
            proc.stdout,
        )

    def test_c_model_null_with_pin_in_allowlist_is_set(self) -> None:
        """(c) explicit model:null + allowlist contains pin -> treated as
        absent, pin IS set (null is not a deliberate choice)."""
        self.seed({"model": None, "availableModels": self._with_opus5()})
        proc = self.run_migration()
        self.assertEqual(self.read_settings()["model"], self._pin())
        self.assertIn(
            "SET (absent [== old baseline] -> new baseline): model",
            proc.stdout,
        )

    def test_c2_model_null_with_allowlist_excluding_pin_not_set(self) -> None:
        """(c-cross) explicit model:null + allowlist EXCLUDES pin -> NOT set +
        WARN; null is left in place (no session-default pin)."""
        self.seed({"model": None, "availableModels": self._custom_without_pin()})
        proc = self.run_migration()
        self.assertIsNone(self.read_settings()["model"],
                          "null left in place; pin not forced outside allowlist")
        self.assertIn(self._pin_not_applied(), proc.stderr)

    def test_d_real_custom_model_preserved_with_warn(self) -> None:
        """(d) a real custom model (a fleet member != pin) is PRESERVED + WARN,
        regardless of the allowlist branch."""
        custom_model = "claude-sonnet-5"
        self.assertNotEqual(custom_model, self._pin())
        self.seed({"model": custom_model, "availableModels": self._with_opus5()})
        proc = self.run_migration()
        self.assertEqual(self.read_settings()["model"], custom_model)
        self.assertIn("WARNING: model is ADOPTER-CUSTOMIZED", proc.stderr)

    def test_e_idempotent_when_pin_withheld(self) -> None:
        """Idempotency for the withheld-pin branch: run twice == byte-identical,
        and the model key never appears."""
        self.seed({"availableModels": self._custom_without_pin()})
        self.run_migration()
        first = self.settings_path.read_bytes()
        proc2 = self.run_migration()
        self.assertEqual(self.settings_path.read_bytes(), first)
        self.assertNotIn("model", self.read_settings())
        self.assertIn(self._pin_not_applied(), proc2.stderr)


class TestScalarLeafGenericBranch(_MigrationHarness):
    """ADR-149 Amendment 3 (S357) — ONE generic branch for top-level SCALAR
    leaves, with the ``superseded`` semantics the ARRAY leaves have had
    since Amendment 2 (second occurrence of a SHIPPED baseline read as
    ADOPTER-CUSTOMIZED: cure the class, not the Opus case).

    RED on 19771fa1: the scalar ``model`` leaf had no ``superseded`` list,
    so an adopter still on the pin that every release from v1.2.0-rc.1 to
    the last one before Amendment 3 shipped kept it behind a WARNING — or,
    while that pin was still the table value, never moved at all.
    """

    #: The session-default pin every release from v1.2.0-rc.1 to the last
    #: one before Amendment 3 SHIPPED (frozen literal, measured S357 with
    #: `git show <tag>:templates/settings/settings.base.json`).
    SHIPPED_PIN_BEFORE_A3 = "claude-opus-5"
    #: The availableModels array every release from v1.4.0-rc.1 to the
    #: last one before Amendment 3 shipped.
    SHIPPED_V14_AVAILABLE = [
        "claude-opus-4-8", "claude-fable-5", "claude-sonnet-4-6",
        "claude-haiku-4-5", "claude-opus-5", "claude-sonnet-5",
        "claude-fable-5-1",
    ]

    @staticmethod
    def _scalar_keys() -> List[str]:
        return [k for k, v in baselines().items()
                if "." not in k and isinstance(v, dict)
                and isinstance(v.get("new"), str)]

    def test_shipped_pin_is_declared_superseded(self) -> None:
        spec = baselines()["model"]
        self.assertIn(self.SHIPPED_PIN_BEFORE_A3, spec.get("superseded", []))
        self.assertNotEqual(self.SHIPPED_PIN_BEFORE_A3, spec["new"])

    def test_shipped_pin_migrates_to_new_pin(self) -> None:
        self.seed({"model": self.SHIPPED_PIN_BEFORE_A3,
                   "availableModels": list(baselines()["availableModels"]["new"])})
        proc = self.run_migration()
        self.assertEqual(self.read_settings()["model"], baselines()["model"]["new"])
        self.assertNotEqual(self.read_settings()["model"], self.SHIPPED_PIN_BEFORE_A3)
        self.assertIn(
            "MIGRATE (matched SUPERSEDED shipped baseline -> new baseline): model",
            proc.stdout,
        )
        self.assertNotIn("WARNING: model is ADOPTER-CUSTOMIZED", proc.stderr)

    def test_v14_adopter_as_shipped_gets_the_8th_id_and_the_new_pin(self) -> None:
        self.seed({"availableModels": list(self.SHIPPED_V14_AVAILABLE),
                   "fallbackModel": list(baselines()["fallbackModel"]["new"]),
                   "model": self.SHIPPED_PIN_BEFORE_A3})
        self.run_migration()
        data = self.read_settings()
        self.assertEqual(data["availableModels"], baselines()["availableModels"]["new"])
        self.assertNotEqual(data["availableModels"], self.SHIPPED_V14_AVAILABLE)
        self.assertEqual(data["model"], baselines()["model"]["new"])
        self.assertIn(data["model"], data["availableModels"])
        self.assertEqual(data["fallbackModel"], baselines()["fallbackModel"]["new"])

    def test_superseded_pin_withheld_when_allowlist_excludes_new_pin(self) -> None:
        custom = list(baselines()["availableModels"]["old"]) + ["adopter-only-model"]
        self.assertNotIn(baselines()["model"]["new"], custom)
        self.seed({"model": self.SHIPPED_PIN_BEFORE_A3, "availableModels": custom})
        proc = self.run_migration()
        self.assertEqual(self.read_settings()["model"], self.SHIPPED_PIN_BEFORE_A3)
        self.assertIn(
            "WARNING: model NOT migrated: " + baselines()["model"]["new"]
            + " is not an exact entry of the adopter availableModels"
            " (the harness may still admit it by prefix) - model left"
            " untouched",
            proc.stderr,
        )

    def test_every_scalar_superseded_value_migrates(self) -> None:
        exercised = 0
        for key in self._scalar_keys():
            for sup in baselines()[key].get("superseded", []):
                exercised += 1
                with self.subTest(key=key, superseded=sup):
                    self.setUp()
                    self.seed({key: sup, "availableModels":
                               list(baselines()["availableModels"]["new"])})
                    proc = self.run_migration()
                    self.assertEqual(self.read_settings()[key],
                                     baselines()[key]["new"])
                    self.assertIn(
                        "MIGRATE (matched SUPERSEDED shipped baseline -> "
                        "new baseline): " + key,
                        proc.stdout,
                    )
        self.assertGreater(exercised, 0, "vacuous: no scalar leaf declares superseded")

    def test_second_run_after_scalar_migration_is_noop(self) -> None:
        self.seed({"model": self.SHIPPED_PIN_BEFORE_A3,
                   "availableModels": list(baselines()["availableModels"]["new"])})
        self.run_migration()
        first = self.settings_path.read_bytes()
        proc = self.run_migration()
        self.assertEqual(self.settings_path.read_bytes(), first)
        self.assertIn("OK (already at new baseline): model", proc.stdout)


class TestEffortLevelLeaf(_MigrationHarness):
    """ADR-149 Amendment 3 (S357; Owner OQ-1 «xhigh», narrowed by OQ-7
    «Instalação nova + opt-in») — ``effortLevel`` is an OPT-IN leaf of the
    T5.4 table: a new install gets it from the template; an EXISTING
    install gets it only under ``--adopt-setting effortLevel``, and an
    adopter value is never overwritten. The H8 settings-merge carries
    only hooks and env, so the table is the one route. RED on 19771fa1:
    the table had no such leaf and upgrade.sh had no such flag.
    """

    _FLAG = ["--adopt-setting", "effortLevel"]
    _OPT_IN_WARN = "WARNING: effortLevel NOT written (opt-in leaf)"
    _SET = "SET (absent [== old baseline] -> new baseline): effortLevel"

    def _spec(self) -> Dict:
        return baselines()["effortLevel"]

    def test_leaf_is_declared_opt_in_and_matches_the_template(self) -> None:
        spec = self._spec()
        self.assertIsNone(spec["old"], "absence is the old baseline")
        self.assertIs(spec.get("opt_in"), True)
        self.assertTrue(str(spec.get("cost_note", "")).strip())
        tpl = json.loads(TEMPLATE_SETTINGS.read_text(encoding="utf-8"))
        self.assertEqual(tpl["effortLevel"], spec["new"])

    def test_absent_key_is_not_written_without_the_flag(self) -> None:
        self.seed({})
        proc = self.run_migration()
        self.assertNotIn("effortLevel", self.read_settings())
        self.assertNotIn(self._SET, proc.stdout)
        self.assertIn(self._OPT_IN_WARN, proc.stderr)
        self.assertIn(self._spec()["cost_note"], proc.stderr)
        self.assertIn("--adopt-setting effortLevel", proc.stderr)

    def test_absent_key_is_written_with_the_flag(self) -> None:
        self.seed({})
        proc = self.run_migration(extra_args=self._FLAG)
        self.assertEqual(self.read_settings()["effortLevel"], self._spec()["new"])
        self.assertIn(self._SET, proc.stdout)
        self.assertNotIn(self._OPT_IN_WARN, proc.stderr)

    def test_adopter_value_is_never_overwritten(self) -> None:
        for custom in ("high", "low"):
            self.assertNotEqual(custom, self._spec()["new"])
            for extra in (None, self._FLAG):
                with self.subTest(custom=custom, flag=extra is not None):
                    self.setUp()
                    self.seed({"effortLevel": custom})
                    proc = self.run_migration(extra_args=extra)
                    self.assertEqual(self.read_settings()["effortLevel"], custom)
                    # An opt-in leaf has no baseline to drift from: the
                    # preserved value is named on stdout, never warned.
                    self.assertIn(
                        "OK (present - PRESERVED; opt-in leaf): "
                        "effortLevel", proc.stdout)
                    self.assertNotIn("WARNING: effortLevel", proc.stderr)

    def test_already_new_is_noop_without_warn(self) -> None:
        for extra in (None, self._FLAG):
            with self.subTest(flag=extra is not None):
                self.setUp()
                self.seed({"effortLevel": self._spec()["new"]})
                proc = self.run_migration(extra_args=extra)
                self.assertIn("OK (already at new baseline): effortLevel",
                              proc.stdout)
                self.assertNotIn("WARNING: effortLevel", proc.stderr)

    def test_without_the_flag_repeated_runs_never_add_the_key(self) -> None:
        self.seed({})
        self.run_migration()
        first = self.settings_path.read_bytes()
        self.run_migration()
        self.assertEqual(self.settings_path.read_bytes(), first)
        self.assertNotIn("effortLevel", self.read_settings())

    def test_flag_delivery_is_idempotent(self) -> None:
        self.seed({})
        self.run_migration(extra_args=self._FLAG)
        first = self.settings_path.read_bytes()
        proc = self.run_migration(extra_args=self._FLAG)
        self.assertEqual(self.settings_path.read_bytes(), first)
        self.assertNotIn(self._SET, proc.stdout)
        self.assertIn("OK (already at new baseline): effortLevel", proc.stdout)

    def test_dry_run_with_the_flag_previews_without_writing(self) -> None:
        self.seed({})
        before = self.settings_path.read_bytes()
        proc = self.run_migration(dry=True, extra_args=self._FLAG)
        self.assertEqual(self.settings_path.read_bytes(), before)
        self.assertIn("(dry-run) would " + self._SET, proc.stdout)

    def test_flag_for_a_non_opt_in_leaf_is_named_and_ignored(self) -> None:
        self.seed({"model": "adopter-model"})
        proc = self.run_migration(extra_args=["--adopt-setting", "model"])
        self.assertIn(
            "WARNING: --adopt-setting model ignored - not an opt-in leaf",
            proc.stderr,
        )
        self.assertEqual(self.read_settings()["model"], "adopter-model")
        self.assertIn("WARNING: model is ADOPTER-CUSTOMIZED", proc.stderr)

    def test_malformed_flag_value_is_refused_before_any_write(self) -> None:
        self.seed({})
        before = self.settings_path.read_bytes()
        for bad in ("", "effort-level", "effortLevel,model", "1effort"):
            with self.subTest(value=bad):
                proc = subprocess.run(
                    ["bash", str(UPGRADE_SH), str(self.target),
                     "--settings-migrate-only", "--no-replay",
                     "--no-deprecation-warn", "--adopt-setting", bad],
                    capture_output=True, text=True, timeout=120,
                    env=_clean_env(None),
                )
                self.assertEqual(proc.returncode, 2, proc.stderr)
                self.assertIn("ERROR: --adopt-setting", proc.stderr)
                self.assertEqual(self.settings_path.read_bytes(), before)


class TestScalarBranchIsGeneric(_MigrationHarness):
    """ADR-149 Amendment 3 (S357) - the scalar branch is GENERIC, proved on
    PLANTED leaves that no code names, in a disposable copy of upgrade.sh
    (never a product seam). RED on 19771fa1: the scalar leaf model had its
    own code, and a table entry nothing named was never read.
    """

    _TABLE_ANCHOR = '  "model": {\n'
    _PLANTED = (
        '  "plantedScalarA": {"old": null, "superseded": ["x-a"], "new": "x-b"},\n'
        '  "plantedScalarB": {"old": "y-old", "new": "y-new"},\n'
        '  "plantedOptIn": {"old": null, "new": "z-new", "opt_in": true,\n'
        '                   "cost_note": "planted cost note"},\n'
    )

    def _planted_upgrade(self, plant: Optional[str] = None) -> Path:
        text = UPGRADE_SH.read_text(encoding="utf-8")
        self.assertEqual(text.count(self._TABLE_ANCHOR), 1,
                         "the plant anchor moved: fix the control, never skip it")
        dst = Path(self._tmp) / "fw" / "scripts" / "upgrade.sh"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(
            text.replace(self._TABLE_ANCHOR,
                         (self._PLANTED if plant is None else plant)
                         + self._TABLE_ANCHOR),
            encoding="utf-8",
        )
        return dst

    def _run_planted(
        self, extra: Optional[List[str]] = None, plant: Optional[str] = None
    ) -> "subprocess.CompletedProcess[str]":
        args = ["bash", str(self._planted_upgrade(plant)), str(self.target),
                "--settings-migrate-only", "--no-replay", "--no-deprecation-warn"]
        args.extend(extra or [])
        proc = subprocess.run(args, capture_output=True, text=True, timeout=120,
                              env=_clean_env(None))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        return proc

    def test_planted_superseded_and_old_scalars_migrate(self) -> None:
        self.seed({"plantedScalarA": "x-a", "plantedScalarB": "y-old"})
        proc = self._run_planted()
        data = self.read_settings()
        self.assertEqual(data["plantedScalarA"], "x-b")
        self.assertEqual(data["plantedScalarB"], "y-new")
        self.assertIn("MIGRATE (matched SUPERSEDED shipped baseline -> "
                      "new baseline): plantedScalarA", proc.stdout)
        self.assertIn("MIGRATE (matched OLD baseline -> new baseline): "
                      "plantedScalarB", proc.stdout)
        self.assertIn("REVERT: to keep the previous value, merge "
                      + json.dumps({"plantedScalarA": "x-a"})
                      + " into .claude/settings.local.json", proc.stdout)

    def test_planted_absent_scalar_is_set_and_custom_is_preserved(self) -> None:
        self.seed({"plantedScalarB": "adopter-choice"})
        proc = self._run_planted()
        data = self.read_settings()
        self.assertEqual(data["plantedScalarA"], "x-b")
        self.assertEqual(data["plantedScalarB"], "adopter-choice")
        self.assertIn("WARNING: plantedScalarB is ADOPTER-CUSTOMIZED", proc.stderr)
        self.assertNotIn("adopter-choice", proc.stdout + proc.stderr,
                         "no-value-echo: an adopter value is never printed")

    def test_planted_opt_in_leaf_is_written_only_with_the_flag(self) -> None:
        self.seed({})
        proc = self._run_planted()
        self.assertNotIn("plantedOptIn", self.read_settings())
        self.assertIn("WARNING: plantedOptIn NOT written (opt-in leaf)", proc.stderr)
        self.assertIn("planted cost note", proc.stderr)
        self.setUp()
        self.seed({})
        self._run_planted(["--adopt-setting", "plantedOptIn"])
        self.assertEqual(self.read_settings()["plantedOptIn"], "z-new")
        self.setUp()
        self.seed({"plantedOptIn": "adopter-z"})
        proc = self._run_planted(["--adopt-setting", "plantedOptIn"])
        self.assertEqual(self.read_settings()["plantedOptIn"], "adopter-z")
        self.assertIn("OK (present - PRESERVED; opt-in leaf): "
                      "plantedOptIn", proc.stdout)
        self.assertNotIn("WARNING: plantedOptIn", proc.stderr)

    #: A planted scalar gated on the OTHER array leaf of the table. RED on
    #: the r9 derivation of this wave: the gate saw only availableModels,
    #: so a leaf gated on fallbackModel always failed with a false warning.
    _GATED_ON_FALLBACK = (
        '  "plantedGated": {"old": null, "new": "claude-opus-5",\n'
        '                   "requires_member_of": "fallbackModel"},\n'
    )

    def test_requires_member_of_reads_every_array_leaf(self) -> None:
        member = baselines()["fallbackModel"]["new"]
        self.assertIn("claude-opus-5", member)
        for dry in (False, True):
            with self.subTest(dry=dry):
                self.setUp()
                self.seed({"fallbackModel": list(member)})
                before = self.settings_path.read_bytes()
                proc = self._run_planted(["--dry-run"] if dry else None,
                                         plant=self._GATED_ON_FALLBACK)
                self.assertNotIn("WARNING: plantedGated", proc.stderr)
                if dry:
                    self.assertIn("(dry-run) would SET (absent [== old "
                                  "baseline] -> new baseline): plantedGated",
                                  proc.stdout)
                    self.assertEqual(self.settings_path.read_bytes(), before)
                else:
                    self.assertEqual(self.read_settings()["plantedGated"],
                                     "claude-opus-5")
        self.setUp()
        self.seed({"fallbackModel": ["claude-sonnet-5"]})
        proc = self._run_planted(plant=self._GATED_ON_FALLBACK)
        self.assertNotIn("plantedGated", self.read_settings())
        self.assertIn("WARNING: plantedGated NOT migrated: claude-opus-5 is not "
                      "an exact entry of the adopter fallbackModel", proc.stderr)

    #: A planted ARRAY leaf that no code names, and a scalar gated on it.
    #: RED on the r10 derivation of this wave: the array pass walked a
    #: literal tuple, so the planted array was never migrated and the gate
    #: always read it as missing.
    _PLANTED_ARRAY = (
        '  "plantedArray": {"old": ["pa-old"], "superseded": [["pa-s1", "pa-s2"]],\n'
        '                   "new": ["pa-new", "claude-opus-5"]},\n'
        '  "plantedOnArray": {"old": null, "new": "claude-opus-5",\n'
        '                     "requires_member_of": "plantedArray"},\n'
    )

    def test_array_pass_walks_every_array_leaf_of_the_table(self) -> None:
        new = ["pa-new", "claude-opus-5"]
        for seed, verdict in (
            ({"plantedArray": ["pa-old"]},
             "MIGRATE (matched OLD baseline -> new baseline): plantedArray"),
            ({"plantedArray": ["pa-s1", "pa-s2"]},
             "MIGRATE (matched SUPERSEDED shipped baseline -> new baseline): "
             "plantedArray"),
            ({}, "SET (absent -> new baseline): plantedArray"),
        ):
            with self.subTest(seed=seed):
                self.setUp()
                self.seed(dict(seed))
                proc = self._run_planted(plant=self._PLANTED_ARRAY)
                data = self.read_settings()
                self.assertIn(verdict, proc.stdout)
                self.assertEqual(data["plantedArray"], new)
                self.assertEqual(data["plantedOnArray"], "claude-opus-5")
                self.assertNotIn("WARNING: plantedOnArray", proc.stderr)
        self.setUp()
        self.seed({"plantedArray": ["adopter-a"]})
        proc = self._run_planted(plant=self._PLANTED_ARRAY)
        data = self.read_settings()
        self.assertEqual(data["plantedArray"], ["adopter-a"])
        self.assertIn("WARNING: plantedArray is ADOPTER-CUSTOMIZED", proc.stderr)
        self.assertNotIn("plantedOnArray", data)
        self.assertIn("WARNING: plantedOnArray NOT migrated: claude-opus-5 is "
                      "not an exact entry of the adopter plantedArray", proc.stderr)
        self.assertNotIn("adopter-a", proc.stdout + proc.stderr,
                         "no-value-echo: an adopter value is never printed")

    #: on_migrate_of as DATA (Owner OQ-8, 2026-09-24): a planted opt-in
    #: leaf takes a planted value when a planted scalar migrates off a
    #: named value, and a rule that names a leaf walked AFTER it is a
    #: named warning, never a silent skip. RED on the r11 derivation of
    #: this wave, which had no such attribute.
    _PLANTED_COMPANION = (
        '  "plantedPin": {"old": null, "superseded": ["p-old"], "new": "p-new"},\n'
        '  "plantedKeep": {"old": null, "new": "k-new", "opt_in": true,\n'
        '                  "cost_note": "planted cost note",\n'
        '                  "on_migrate_of": {"plantedPin": {"p-old": "k-kept"}},\n'
        '                  "on_migrate_note": "planted keep note"},\n'
        '  "plantedEarly": {"old": null, "new": "e-new", "opt_in": true,\n'
        '                   "on_migrate_of": {"plantedLate": {"l-old": "e-kept"}}},\n'
        '  "plantedLate": {"old": null, "superseded": ["l-old"], "new": "l-new"},\n'
    )

    def test_on_migrate_of_is_generic_data(self) -> None:
        self.seed({"plantedPin": "p-old", "plantedLate": "l-old"})
        proc = self._run_planted(plant=self._PLANTED_COMPANION)
        data = self.read_settings()
        self.assertEqual(data["plantedPin"], "p-new")
        self.assertEqual(data["plantedKeep"], "k-kept")
        lines = proc.stdout.splitlines()
        at = [i for i, ln in enumerate(lines)
              if "MIGRATE (plantedPin migrated off p-old and plantedKeep was "
                 "absent -> k-kept): plantedKeep" in ln]
        self.assertEqual(len(at), 1, proc.stdout)
        self.assertIn("REVERT: ", lines[at[0] + 1])
        self.assertIn("NOTICE: plantedKeep = k-kept planted keep note", proc.stdout)
        self.assertNotIn("WARNING: plantedKeep", proc.stderr)
        # the rule that names a leaf walked later: named, and not applied
        self.assertEqual(data["plantedLate"], "l-new")
        self.assertNotIn("plantedEarly", data)
        self.assertIn("WARNING: plantedEarly on_migrate_of names plantedLate",
                      proc.stderr)

    def test_on_migrate_of_never_beats_the_flag_or_a_present_value(self) -> None:
        for seed, extra, want in (
            ({"plantedPin": "p-old"}, ["--adopt-setting", "plantedKeep"], "k-new"),
            ({"plantedPin": "p-old", "plantedKeep": "adopter-k"}, None, "adopter-k"),
        ):
            with self.subTest(seed=seed, flag=extra is not None):
                self.setUp()
                self.seed(dict(seed))
                proc = self._run_planted(extra, plant=self._PLANTED_COMPANION)
                self.assertEqual(self.read_settings()["plantedKeep"], want)
                self.assertNotIn("plantedKeep was absent", proc.stdout)


class TestBackupIsAPrecondition(_MigrationHarness):
    """ADR-149 Amendment 3 (S357) - the REVERT lines name the pre-migration
    backup, so a backup that cannot be written must stop the migration
    (named, settings.json untouched). Proved by a planted FAULT in a
    disposable copy of upgrade.sh (never a product seam): the copy of the
    backup is replaced by `false`. RED on the r9 derivation of this wave,
    where the failed copy was swallowed and the migration went on.
    """

    _BACKUP_COPY = ('cp "$settings" '
                    '"$BAK_DIR/.claude/settings.json.pre-t54-migration"')

    def _faulty_upgrade(self) -> Path:
        text = UPGRADE_SH.read_text(encoding="utf-8")
        self.assertEqual(text.count(self._BACKUP_COPY), 1,
                         "the fault anchor moved: fix the control, never skip it")
        dst = Path(self._tmp) / "fw" / "scripts" / "upgrade.sh"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(text.replace(self._BACKUP_COPY, "false"),
                       encoding="utf-8")
        return dst

    def test_a_failed_backup_skips_the_migration(self) -> None:
        self.seed({"availableModels":
                   list(baselines()["availableModels"]["old"])})
        before = self.settings_path.read_bytes()
        proc = subprocess.run(
            ["bash", str(self._faulty_upgrade()), str(self.target),
             "--settings-migrate-only", "--no-replay", "--no-deprecation-warn"],
            capture_output=True, text=True, timeout=120, env=_clean_env(None))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertEqual(self.settings_path.read_bytes(), before)
        self.assertIn("settings baseline migration SKIPPED", proc.stderr)
        self.assertIn("pre-migration backup could", proc.stderr)
        self.assertNotIn("BACKED UP", proc.stdout)
        self.assertNotIn("REVERT", proc.stdout)
        self.assertNotIn("MIGRATE (", proc.stdout)
        self.assertRegex(proc.stderr, r'migration alone:  scripts/upgrade.sh \S+ '
                         r'--settings-migrate-only\n')

    def test_the_rerun_hint_keeps_the_operator_flags(self) -> None:
        """vX (fix round r13): the ACTION line dropped every --adopt-setting
        the operator passed, so the suggested re-run migrated WITHOUT the
        opt-in. RED on the r12 derivation of this wave."""
        self.seed({"availableModels":
                   list(baselines()["availableModels"]["old"])})
        proc = subprocess.run(
            ["bash", str(self._faulty_upgrade()), str(self.target),
             "--settings-migrate-only", "--no-replay", "--no-deprecation-warn",
             "--adopt-setting", "effortLevel", "--adopt-setting", "plantedKey",
             "--allow-old-claude-code"],
            capture_output=True, text=True, timeout=120, env=_clean_env(None))
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertRegex(proc.stderr, r'migration alone:  scripts/upgrade.sh \S+ '
                         r'--settings-migrate-only --adopt-setting effortLevel '
                         r'--adopt-setting plantedKey --allow-old-claude-code\n')


class TestMigrationOutputOracles(_MigrationHarness):
    """ADR-149 Amendment 3 (S357) - what the operator SEES and what the file
    KEEPS: every MIGRATE line is followed by its REVERT line, the model
    notice names the CLI floor, text outside ASCII is written as is, a
    template-shaped file changes only the migrated lines - plus, when the
    migration appends a key, a trailing comma on the line before it (the
    template a release shipped) - and the dry-run and second-run oracles go
    through the scalar MIGRATE branch.
    """

    #: availableModels and pin every release from v1.4.0-rc.1 to the last
    #: one before Amendment 3 shipped (frozen literals, measured S357).
    SHIPPED_V14_AVAILABLE = [
        "claude-opus-4-8", "claude-fable-5", "claude-sonnet-4-6",
        "claude-haiku-4-5", "claude-opus-5", "claude-sonnet-5",
        "claude-fable-5-1",
    ]
    SHIPPED_PIN = "claude-opus-5"

    def _v14_seed(self) -> Dict:
        return {"availableModels": list(self.SHIPPED_V14_AVAILABLE),
                "model": self.SHIPPED_PIN}

    def _every_leaf_migrates_seed(self) -> Dict:
        seed = self._v14_seed()
        seed["permissions"] = {
            "defaultMode": baselines()["permissions.defaultMode"]["old"]}
        seed["hooks"] = {"PreToolUse": [{"matcher": "Edit", "hooks": [
            {"type": "command", "command": "bash h.sh check_pair_rail.py",
             "timeout": 60}]}]}
        return seed

    def _assert_each_migrate_line_has_a_revert_line(self, stdout: str) -> None:
        lines = stdout.splitlines()
        migrate_at = [i for i, ln in enumerate(lines) if "MIGRATE (" in ln]
        self.assertGreaterEqual(len(migrate_at), 4, stdout)
        for i in migrate_at:
            self.assertLess(i + 1, len(lines), lines[i])
            self.assertIn("REVERT: ", lines[i + 1], lines[i])

    def test_every_migrate_line_is_followed_by_its_revert_line(self) -> None:
        old_mode = baselines()["permissions.defaultMode"]["old"]
        self.seed(self._every_leaf_migrates_seed())
        proc = self.run_migration()
        self._assert_each_migrate_line_has_a_revert_line(proc.stdout)
        self.assertIn("merge " + json.dumps({"model": self.SHIPPED_PIN})
                      + " into .claude/settings.local.json", proc.stdout)
        self.assertIn("merge " + json.dumps({"permissions": {"defaultMode": old_mode}}),
                      proc.stdout)
        self.assertIn("REVERT: copy the pre-migration backup", proc.stdout)

    def test_every_dry_run_migrate_line_is_followed_by_a_revert_line(self) -> None:
        """A dry run writes no backup, yet each of its MIGRATE lines still
        carries a REVERT line; RED on the first derivation of this wave,
        where the array and hook MIGRATE lines printed none in a dry run.
        """
        self.seed(self._every_leaf_migrates_seed())
        before = self.settings_path.read_bytes()
        proc = self.run_migration(dry=True)
        self.assertEqual(self.settings_path.read_bytes(), before)
        self._assert_each_migrate_line_has_a_revert_line(proc.stdout)
        self.assertIn("REVERT: an apply run backs up .claude/settings.json",
                      proc.stdout)
        self.assertNotIn("REVERT: copy the pre-migration backup", proc.stdout)

    def test_model_notice_names_the_cli_floor(self) -> None:
        spec = baselines()["model"]
        self.assertIn("2.1.280", spec.get("notice", ""))
        self.seed(self._v14_seed())
        proc = self.run_migration()
        self.assertIn("NOTICE: model = " + spec["new"] + " " + spec["notice"],
                      proc.stdout)

    def test_rewrite_keeps_text_outside_ascii_unescaped(self) -> None:
        """RED on 19771fa1 for exactly this reason: json.dump escaped every
        character outside ASCII. The fixture also migrates on 19771fa1 (the
        OLD availableModels), so only the escaping can fail it.
        """
        text = "ação — ≥ ✅"
        obj = {"_comment": text,
               "availableModels": list(baselines()["availableModels"]["old"])}
        self.settings_path.write_text(
            json.dumps(obj, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        self.run_migration()
        raw = self.settings_path.read_text(encoding="utf-8")
        self.assertIn(text, raw)
        self.assertNotIn("\\u", raw)

    def test_lone_surrogate_falls_back_to_the_escaped_writer(self) -> None:
        """json.load accepts an escaped lone surrogate, which UTF-8 cannot
        encode: the writer falls back to the escaped form, so the file still
        migrates. RED on the r8 derivation of this wave, where the write
        failed and the whole migration was skipped.
        """
        seed = self._v14_seed()
        seed["_x"] = "\ud800"
        self.settings_path.write_text(json.dumps(seed, indent=2) + "\n",
                                      encoding="utf-8")
        proc = self.run_migration()
        data = self.read_settings()
        self.assertEqual(data["model"], baselines()["model"]["new"])
        self.assertEqual(data["_x"], "\ud800")
        self.assertIn("\\ud800", self.settings_path.read_text(encoding="utf-8"))
        self.assertNotIn("SKIPPED", proc.stdout + proc.stderr)

    def test_template_shaped_install_changes_only_the_migrated_lines(self) -> None:
        """The base template with the pin and the last id reverted to what
        the releases before Amendment 3 shipped migrates back to the
        template BYTE FOR BYTE: no line outside the migrated leaves changes.
        """
        tpl = TEMPLATE_SETTINGS.read_text(encoding="utf-8")
        new = baselines()["availableModels"]["new"]
        pin_line = '  "model": "%s",\n' % baselines()["model"]["new"]
        tail = '    "%s",\n    "%s"\n  ],\n' % (new[-2], new[-1])
        self.assertEqual(tpl.count(pin_line), 1)
        self.assertEqual(tpl.count(tail), 1)
        seed = tpl.replace(pin_line, '  "model": "%s",\n' % self.SHIPPED_PIN)
        seed = seed.replace(tail, '    "%s"\n  ],\n' % new[-2])
        self.assertEqual(json.loads(seed)["availableModels"], self.SHIPPED_V14_AVAILABLE)
        self.settings_path.write_text(seed, encoding="utf-8")
        self.run_migration()
        self.assertEqual(self.settings_path.read_text(encoding="utf-8"), tpl)

    #: A release whose base template the OQ-8 append path meets AS SHIPPED
    #: (the last tag before Amendment 3; vX, fix round r13).
    SHIPPED_TEMPLATE_TAG = "v1.4.1-rc.1"

    def test_a_shipped_template_changes_the_migrated_lines_and_one_comma(self) -> None:
        """vX (fix round r13): the base template that v1.4.1-rc.1 shipped,
        read with git as is, through the pin migration that APPENDS
        effortLevel (Owner OQ-8). Every line outside the migrated leaves
        stays byte-identical except the line just before the appended key,
        which gains a trailing comma - the rule ADR-149 A3.2 item 6 states.
        The template test above seeds from the CURRENT template, which
        already carries effortLevel, so it never met the append path; the
        earlier claim ("every line outside the migrated leaves") was false
        on it. Skips, named, in a checkout without the tag.
        """
        git = shutil.which("git")
        if git is None:
            self.skipTest("git is not on PATH: the shipped template cannot be read")
        show = subprocess.run(
            [git, "-C", str(REPO_ROOT), "show",
             self.SHIPPED_TEMPLATE_TAG + ":templates/settings/settings.base.json"],
            capture_output=True, text=True, timeout=60)
        if show.returncode != 0:
            self.skipTest("%s is not in this checkout (a shallow clone fetches no "
                          "tag): the shipped template cannot be read"
                          % self.SHIPPED_TEMPLATE_TAG)
        seed = show.stdout
        shipped = json.loads(seed)
        self.assertEqual(shipped.get("model"), self.SHIPPED_PIN)
        self.assertEqual(shipped.get("availableModels"), self.SHIPPED_V14_AVAILABLE)
        self.assertNotIn("effortLevel", shipped)
        # The shipped file is in the writer's own format (it round-trips).
        self.assertEqual(json.dumps(shipped, indent=2, ensure_ascii=False) + "\n",
                         seed)
        new = baselines()["availableModels"]["new"]
        self.assertEqual(new[:-1], self.SHIPPED_V14_AVAILABLE)
        effort = baselines()["effortLevel"]["on_migrate_of"]["model"][self.SHIPPED_PIN]
        pin_old = '  "model": "%s",\n' % self.SHIPPED_PIN
        tail_old = '    "%s"\n  ],\n' % new[-2]
        self.assertEqual(seed.count(pin_old), 1)
        self.assertEqual(seed.count(tail_old), 1)
        expected = seed.replace(
            pin_old, '  "model": "%s",\n' % baselines()["model"]["new"])
        expected = expected.replace(
            tail_old, '    "%s",\n    "%s"\n  ],\n' % (new[-2], new[-1]))
        lines = expected.splitlines(True)
        self.assertEqual(lines[-1], "}\n")
        self.assertFalse(lines[-2].rstrip("\n").endswith(","), lines[-2])
        lines[-2] = lines[-2][:-1] + ",\n"  # the one line outside the leaves
        lines.insert(-1, '  "effortLevel": "%s"\n' % effort)
        self.settings_path.write_text(seed, encoding="utf-8")
        self.run_migration()
        self.assertEqual(self.settings_path.read_text(encoding="utf-8"),
                         "".join(lines))

    def test_dry_run_goes_through_the_scalar_migrate_branch(self) -> None:
        self.seed(self._v14_seed())
        before = self.settings_path.read_bytes()
        proc = self.run_migration(dry=True)
        self.assertEqual(self.settings_path.read_bytes(), before)
        self.assertIn("(dry-run) would MIGRATE (matched SUPERSEDED shipped "
                      "baseline -> new baseline): model", proc.stdout)
        self.assertFalse((self.target / ".claude.bak").exists(),
                         "--dry-run must not create the backup dir")

    def test_v14_shape_second_run_is_an_idempotent_noop(self) -> None:
        seed = self._v14_seed()
        seed["fallbackModel"] = list(baselines()["fallbackModel"]["new"])
        seed["permissions"] = {
            "defaultMode": baselines()["permissions.defaultMode"]["new"]}
        self.seed(seed)
        self.run_migration()
        first = self.settings_path.read_bytes()
        proc = self.run_migration()
        self.assertEqual(self.settings_path.read_bytes(), first)
        self.assertNotIn("MIGRATE (", proc.stdout)
        self.assertNotIn("SET (", proc.stdout)
        self.assertIn("idempotent no-op", proc.stdout)


class TestEveryShippedShapeIsKnown(_MigrationHarness):
    """ADR-149 Amendment 3 (S357) - every value a TAG shipped, release
    candidates included, must be a known baseline (old, superseded or new)
    of the table, or its adopters are read as ADOPTER-CUSTOMIZED forever.
    Two guards: SHIPPED_AT_S357 is a literal FROZEN over the v1.* tags that
    existed at S357 (measured with `git show <tag>:templates/settings/
    settings.base.json`; it runs in every checkout), and the walk reads
    the same file from EVERY v1.* tag reachable from HEAD, so a release
    tagged later is covered without editing a list (a checkout without
    tags - a shallow CI clone - skips the walk, named).
    """

    _V10 = ["claude-opus-4-8", "claude-fable-5", "claude-sonnet-4-6",
            "claude-haiku-4-5"]
    _V12 = _V10 + ["claude-opus-5", "claude-sonnet-5"]
    _V14 = _V12 + ["claude-fable-5-1"]
    #: (tags, availableModels, model or None when absent, fallbackModel)
    SHIPPED_AT_S357 = (
        (("v1.0.0", "v1.0.1-rc.1", "v1.0.1", "v1.1.0-rc.1", "v1.1.0"),
         _V10, None, ["claude-opus-4-8"]),
        (("v1.2.0-rc.1", "v1.2.0-rc.2", "v1.2.0-rc.3", "v1.2.0",
          "v1.3.0-rc.1", "v1.3.0-rc.2", "v1.3.0-rc.3", "v1.3.0-rc.4", "v1.3.0"),
         _V12, "claude-opus-5", ["claude-opus-5"]),
        (("v1.4.0-rc.1", "v1.4.0", "v1.4.1-rc.1"),
         _V14, "claude-opus-5", ["claude-opus-5"]),
    )

    @staticmethod
    def _known(spec: Dict) -> List:
        return [spec.get("old"), spec["new"]] + list(spec.get("superseded", []))

    def test_every_shipped_value_is_a_known_baseline(self) -> None:
        for tags, avail, model, fallback in self.SHIPPED_AT_S357:
            with self.subTest(tags=tags[0]):
                self.assertIn(avail, self._known(baselines()["availableModels"]))
                self.assertIn(fallback, self._known(baselines()["fallbackModel"]))
                self.assertIn(model, self._known(baselines()["model"]))

    def test_every_shipped_shape_migrates_end_to_end(self) -> None:
        for tags, avail, model, fallback in self.SHIPPED_AT_S357:
            with self.subTest(tags=tags[0]):
                self.setUp()
                seed = {"availableModels": list(avail),
                        "fallbackModel": list(fallback)}
                if model is not None:
                    seed["model"] = model
                self.seed(seed)
                self.run_migration()
                data = self.read_settings()
                self.assertEqual(data["availableModels"],
                                 baselines()["availableModels"]["new"])
                self.assertEqual(data["fallbackModel"],
                                 baselines()["fallbackModel"]["new"])
                self.assertEqual(data["model"], baselines()["model"]["new"])

    def test_every_tag_reachable_from_head_shipped_a_known_shape(self) -> None:
        git = shutil.which("git")
        if git is None:
            self.skipTest("git is not on PATH: the tag walk cannot run")
        proc = subprocess.run(
            [git, "-C", str(REPO_ROOT), "tag", "--merged", "HEAD", "--list",
             "v1.*"],
            capture_output=True, text=True, timeout=60)
        tags = sorted(t for t in proc.stdout.split() if t) if proc.returncode == 0 else []
        if not tags:
            self.skipTest("no v1.* tag reachable from HEAD in this checkout "
                          "(a shallow clone fetches none): nothing to walk; "
                          "SHIPPED_AT_S357 still runs")
        read = 0
        for tag in tags:
            show = subprocess.run(
                [git, "-C", str(REPO_ROOT), "show",
                 tag + ":templates/settings/settings.base.json"],
                capture_output=True, text=True, timeout=60)
            if show.returncode != 0:
                continue
            shipped = json.loads(show.stdout)
            read += 1
            with self.subTest(tag=tag):
                for key in ("availableModels", "fallbackModel", "model"):
                    self.assertIn(shipped.get(key), self._known(baselines()[key]),
                                  "%s shipped a %s the table does not know"
                                  % (tag, key))
        self.assertGreater(read, 0, "v1.* tags found, none carries the template")


class TestPinMigrationKeepsTheEffort(_MigrationHarness):
    """ADR-149 Amendment 3 (S357; Owner OQ-8, 2026-09-24, verbatim «Migrar
    gravando 'high' (Recomendado)») - when the upgrade migrates the shipped
    pin claude-opus-5 to claude-opus-5-5 in a file with NO effortLevel, it
    writes the value the table maps for that pin (high, the Opus 5
    default), with a named MIGRATE line and its REVERT line. RED on the r11
    derivation of this wave: the pin migrated and effortLevel stayed absent
    (the session moved from high to the Opus 5.5 default, medium).
    Expectations derive from the table, not from literals.
    """

    _FLAG = ["--adopt-setting", "effortLevel"]

    @staticmethod
    def _rule() -> Dict:
        return baselines()["effortLevel"]["on_migrate_of"]["model"]

    def _shipped_pin(self) -> str:
        pins = [p for p in baselines()["model"]["superseded"] if p in self._rule()]
        self.assertTrue(pins, "no superseded pin has an effort mapping")
        return pins[0]

    def _seed_shipped(self, **extra) -> None:
        seed = {"model": self._shipped_pin(),
                "availableModels": list(baselines()["availableModels"]["new"])}
        seed.update(extra)
        self.seed(seed)

    def _line(self) -> str:
        pin = self._shipped_pin()
        return ("MIGRATE (model migrated off " + pin + " and effortLevel was "
                "absent -> " + self._rule()[pin] + "): effortLevel")

    def test_the_table_maps_the_shipped_pin_to_high(self) -> None:
        self.assertEqual(self._rule().get("claude-opus-5"), "high")
        self.assertIn("claude-opus-5", baselines()["model"]["superseded"])
        self.assertNotEqual(self._rule()["claude-opus-5"],
                            baselines()["effortLevel"]["new"])

    def test_pin_migration_writes_the_mapped_effort(self) -> None:
        self._seed_shipped()
        proc = self.run_migration()
        data = self.read_settings()
        self.assertEqual(data["model"], baselines()["model"]["new"])
        self.assertEqual(data["effortLevel"], self._rule()[self._shipped_pin()])
        lines = proc.stdout.splitlines()
        at = [i for i, ln in enumerate(lines) if self._line() in ln]
        self.assertEqual(len(at), 1, proc.stdout)
        self.assertIn("REVERT: to drop it, delete effortLevel", lines[at[0] + 1])
        self.assertIn("NOTICE: effortLevel = high", proc.stdout)
        self.assertNotIn("WARNING: effortLevel", proc.stderr)

    def test_second_run_is_an_idempotent_noop(self) -> None:
        self._seed_shipped()
        self.run_migration()
        first = self.settings_path.read_bytes()
        proc = self.run_migration()
        self.assertEqual(self.settings_path.read_bytes(), first)
        self.assertNotIn("MIGRATE (", proc.stdout)
        self.assertIn("OK (present - PRESERVED; opt-in leaf): effortLevel",
                      proc.stdout)

    def test_dry_run_previews_without_writing(self) -> None:
        self._seed_shipped()
        before = self.settings_path.read_bytes()
        proc = self.run_migration(dry=True)
        self.assertEqual(self.settings_path.read_bytes(), before)
        self.assertIn("(dry-run) would " + self._line(), proc.stdout)
        self.assertFalse((self.target / ".claude.bak").exists())

    def test_an_adopter_effort_level_is_never_overwritten(self) -> None:
        for custom in ("medium", "low", "xhigh", "max"):
            for extra in (None, self._FLAG):
                with self.subTest(custom=custom, flag=extra is not None):
                    self.setUp()
                    self._seed_shipped(effortLevel=custom)
                    proc = self.run_migration(extra_args=extra)
                    data = self.read_settings()
                    self.assertEqual(data["effortLevel"], custom)
                    self.assertEqual(data["model"], baselines()["model"]["new"])
                    self.assertNotIn("effortLevel was absent", proc.stdout)

    def test_the_opt_in_flag_wins_over_the_mapped_effort(self) -> None:
        self._seed_shipped()
        proc = self.run_migration(extra_args=self._FLAG)
        self.assertEqual(self.read_settings()["effortLevel"],
                         baselines()["effortLevel"]["new"])
        self.assertNotIn("effortLevel was absent", proc.stdout)

    def test_no_migration_means_no_effort_write(self) -> None:
        cases = (
            # the pin is SET (the file had none): no pin to keep the effort of
            {"availableModels": list(baselines()["availableModels"]["new"])},
            # a custom pin is preserved, not migrated
            {"model": "claude-sonnet-5",
             "availableModels": list(baselines()["availableModels"]["new"])},
            # the allowlist withholds the new pin: the pin is left untouched
            {"model": "claude-opus-5",
             "availableModels": ["claude-opus-5", "adopter-only-model"]},
        )
        for seed in cases:
            with self.subTest(seed=sorted(seed)):
                self.setUp()
                self.seed(dict(seed))
                proc = self.run_migration()
                self.assertNotIn("effortLevel", self.read_settings())
                self.assertNotIn("effortLevel was absent", proc.stdout)

    def test_adopt_setting_under_no_settings_migrate_is_named(self) -> None:
        """A-R3M-03 (rail round 3): the flag feeds only the T5.4 migration;
        under --no-settings-migrate it was dropped with no line at all."""
        self._seed_shipped()
        before = self.settings_path.read_bytes()
        proc = self.run_migration(
            extra_args=["--no-settings-migrate"] + self._FLAG)
        self.assertEqual(self.settings_path.read_bytes(), before)
        self.assertIn("WARNING: --adopt-setting effortLevel ignored: "
                      "--no-settings-migrate skips the T5.4 settings migration",
                      proc.stderr)


class TestClaudeCodeFloor(_MigrationHarness):
    """ADR-149 Amendment 3 (S357; Owner OQ-9, 2026-09-24, verbatim «Exigir
    CC >= 2.1.280 (Recomendado)») - install.sh and upgrade.sh read the
    claude found on PATH: below the floor they REFUSE (exit 6) before any
    write unless --allow-old-claude-code is passed; no claude on PATH or an
    unreadable version is a named WARNING and the run goes on; a dry run
    names the refusal and writes nothing. The PATH here holds a FAKE claude
    (or none), never the operator's. RED on the r11 derivation of this wave:
    neither script read the CLI version. Fix round r13 (vX): the version is
    read only from the line naming (Claude Code) (another program's version
    printed first read as the CLI's, a supported CLI refused), a suffix after
    the three numbers counts as below the floor (2.1.280-beta.1 passed as
    2.1.280), and the probe reads no stdin and is stopped at a wall limit (a
    hanging CLI blocked every run) - RED on the r12 derivation.
    """

    _BEGIN = "# >>> claude-code-floor"
    _END = "# <<< claude-code-floor <<<\n"
    INSTALL_SH = REPO_ROOT / "scripts" / "install.sh"
    SUPPORT_MD = REPO_ROOT / "SUPPORT.md"

    def _block(self, path: Path) -> str:
        text = path.read_text(encoding="utf-8")
        self.assertEqual(text.count(self._BEGIN), 1, path)
        self.assertEqual(text.count(self._END), 1, path)
        start = text.index(self._BEGIN)
        return text[start:text.index(self._END) + len(self._END)]

    def _floor(self) -> str:
        block = self._block(UPGRADE_SH)
        line = [ln for ln in block.splitlines() if ln.startswith("CC_FLOOR_VERSION=")]
        self.assertEqual(len(line), 1, block)
        return line[0].split("=", 1)[1].strip('"')

    def _bin_with(self, output: Optional[str]) -> str:
        """A PATH whose only claude is a fake printing ``output`` (None =
        no claude at all); the rest of PATH minus every dir holding one."""
        if output is None:
            return self._bin_with_script(None)
        return self._bin_with_script("printf '%s\\n' '" + output + "'\n")

    def _bin_with_script(self, body: Optional[str]) -> str:
        """A PATH whose only claude is a fake running the sh ``body`` (None =
        no claude at all); the rest of PATH minus every dir holding one."""
        keep = []
        for d in os.environ.get("PATH", "").split(os.pathsep):
            cand = os.path.join(d, "claude")
            if d and not (os.path.isfile(cand) and os.access(cand, os.X_OK)):
                keep.append(d)
        for tool in ("bash", "python3", "git", "grep", "head", "sed", "sleep"):
            if shutil.which(tool, path=os.pathsep.join(keep)) is None:
                self.skipTest("PATH without claude lost %s" % tool)
        if body is None:
            return os.pathsep.join(keep)
        fake = Path(self._tmp) / "fakebin"
        fake.mkdir(exist_ok=True)
        exe = fake / "claude"
        exe.write_text("#!/bin/sh\n" + body, encoding="utf-8")
        exe.chmod(0o755)
        return os.pathsep.join([str(fake)] + keep)

    def _upgrade(self, path: str, extra: Optional[List[str]] = None,
                 script: Optional[Path] = None, stdin_text: Optional[str] = None
                 ) -> "subprocess.CompletedProcess[str]":
        args = ["bash", str(script or UPGRADE_SH), str(self.target),
                "--settings-migrate-only", "--no-replay", "--no-deprecation-warn"]
        args.extend(extra or [])
        return subprocess.run(args, capture_output=True, text=True, timeout=120,
                              input=stdin_text, env=_clean_env({"PATH": path}))

    def _v14_seed(self) -> None:
        self.seed({"model": "claude-opus-5",
                   "availableModels": list(baselines()["availableModels"]["new"])})

    def test_one_floor_in_both_scripts_the_notice_and_support(self) -> None:
        self.assertEqual(self._block(UPGRADE_SH), self._block(self.INSTALL_SH))
        floor = self._floor()
        self.assertRegex(floor, r"^\d+\.\d+\.\d+$")
        self.assertIn(floor, baselines()["model"]["notice"])
        self.assertIn("| Claude Code ≥ " + floor + " |",
                      self.SUPPORT_MD.read_text(encoding="utf-8"))
        for script in (UPGRADE_SH, self.INSTALL_SH):
            text = script.read_text(encoding="utf-8")
            self.assertIn("--allow-old-claude-code)", text, script)
            self.assertIn('_claude_code_floor_check "$ALLOW_OLD_CLAUDE_CODE" '
                          '"$DRY_RUN"', text, script)

    def test_below_the_floor_is_refused_before_any_write(self) -> None:
        # 2.1.99 < 2.1.280 numerically; a string comparison would pass it.
        for out in ("2.1.279 (Claude Code)", "2.1.99 (Claude Code)",
                    "1.9.999 (Claude Code)"):
            with self.subTest(version=out):
                self.setUp()
                self._v14_seed()
                before = self.settings_path.read_bytes()
                proc = self._upgrade(self._bin_with(out))
                self.assertEqual(proc.returncode, 6, proc.stdout + proc.stderr)
                self.assertIn("ERROR: Claude Code " + out.split()[0]
                              + " is below " + self._floor(), proc.stderr)
                self.assertEqual(self.settings_path.read_bytes(), before)
                self.assertFalse((self.target / ".claude.bak").exists())

    def test_at_or_above_the_floor_passes(self) -> None:
        floor = self._floor()
        # 2.1.1000 > 2.1.280 numerically; a string comparison would refuse it.
        for out in (floor + " (Claude Code)", "2.1.1000 (Claude Code)",
                    "3.0.0 (Claude Code)"):
            with self.subTest(version=out):
                self.setUp()
                self._v14_seed()
                proc = self._upgrade(self._bin_with(out))
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                self.assertIn("Claude Code:  " + out.split()[0] + " (floor "
                              + floor + ": OK)", proc.stdout)
                self.assertNotIn("Claude Code", proc.stderr)
                self.assertEqual(self.read_settings()["model"],
                                 baselines()["model"]["new"])

    def test_the_version_is_read_from_the_claude_code_line_only(self) -> None:
        """vX (fix round r13): the first x.y.z of the whole output was read,
        so another program's version printed first decided - a CLI below the
        floor passed, a supported one was refused. RED on the r12 derivation.
        """
        floor = self._floor()
        cases = (
            ("Node v22.3.0\n2.1.279 (Claude Code)", 6,
             "ERROR: Claude Code 2.1.279 is below " + floor, "stderr"),
            ("dependency 1.0.0\n" + floor + " (Claude Code)", 0,
             "Claude Code:  " + floor + " (floor " + floor + ": OK)", "stdout"),
        )
        for out, rc, line, stream in cases:
            with self.subTest(output=out.splitlines()[0]):
                self.setUp()
                self._v14_seed()
                before = self.settings_path.read_bytes()
                proc = self._upgrade(self._bin_with(out))
                self.assertEqual(proc.returncode, rc, proc.stdout + proc.stderr)
                self.assertIn(line, getattr(proc, stream))
                if rc:
                    self.assertEqual(self.settings_path.read_bytes(), before)

    def test_a_suffix_after_the_three_numbers_counts_as_below(self) -> None:
        """vX (fix round r13): 2.1.280-beta.1 passed as 2.1.280. A version
        with anything after its three numbers counts as below the floor,
        whatever the numbers. RED on the r12 derivation."""
        floor = self._floor()
        major, minor, patch = floor.split(".")
        later = "%s.%s.%d" % (major, minor, int(patch) + 1)
        for tok in (floor + "-beta.1", later + "-beta.1"):
            with self.subTest(version=tok):
                self.setUp()
                self._v14_seed()
                before = self.settings_path.read_bytes()
                proc = self._upgrade(self._bin_with(tok + " (Claude Code)"))
                self.assertEqual(proc.returncode, 6, proc.stdout + proc.stderr)
                self.assertIn("ERROR: Claude Code " + tok + " is below " + floor
                              + " (a version with anything after its three "
                              "numbers counts as below it)", proc.stderr)
                self.assertEqual(self.settings_path.read_bytes(), before)

    def test_the_override_flag_continues_with_a_named_warning(self) -> None:
        self._v14_seed()
        proc = self._upgrade(self._bin_with("2.1.279 (Claude Code)"),
                             ["--allow-old-claude-code"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("continuing because --allow-old-claude-code was passed",
                      proc.stderr)
        self.assertEqual(self.read_settings()["model"], baselines()["model"]["new"])

    def test_no_claude_or_an_unreadable_version_warns_and_goes_on(self) -> None:
        unreadable = ("WARNING: Claude Code version unreadable: no line of "
                      "'claude --version' names (Claude Code) with a version")
        for out, warning in (
            (None, "WARNING: Claude Code CLI not found on PATH"),
            ("claude, a build without a version", unreadable),
            # a version on a line that does not name Claude Code is not read
            ("2.1.1000", unreadable),
        ):
            with self.subTest(output=out):
                self.setUp()
                self._v14_seed()
                proc = self._upgrade(self._bin_with(out))
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                self.assertIn(warning, proc.stderr)
                self.assertEqual(self.read_settings()["model"],
                                 baselines()["model"]["new"])

    def test_a_hanging_cli_is_stopped_and_the_run_goes_on(self) -> None:
        """vX (fix round r13): the probe had no wall limit, so a CLI that
        hangs blocked every install and upgrade. Planted in a disposable copy
        of upgrade.sh with a 2-second limit (never a product seam); the fake
        claude is a shell whose CHILD sleeps holding the output open, so only
        a stop of the process group lets the run go on. RED on the r12
        derivation (no limit: the child held the capture for its full sleep).
        """
        text = UPGRADE_SH.read_text(encoding="utf-8")
        anchor = "\nCC_FLOOR_PROBE_SECONDS="
        self.assertEqual(text.count(anchor), 1,
                         "the plant anchor moved: fix the control, never skip it")
        value = text.split(anchor, 1)[1].split("\n", 1)[0]
        self.assertRegex(value, r"^[0-9]+$")
        self.assertLessEqual(int(value), 60, "the wall limit must stay short")
        dst = Path(self._tmp) / "fw" / "scripts" / "upgrade.sh"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(text.replace(anchor + value + "\n", anchor + "2\n"),
                       encoding="utf-8")
        self._v14_seed()
        path = self._bin_with_script("sleep 60\necho '2.1.1000 (Claude Code)'\n")
        start = time.monotonic()
        proc = self._upgrade(path, script=dst)
        elapsed = time.monotonic() - start
        self.assertLess(elapsed, 30, "the probe was not stopped at its limit")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("WARNING: Claude Code version unreadable: 'claude --version' "
                      "did not finish within 2s and was stopped", proc.stderr)
        self.assertEqual(self.read_settings()["model"], baselines()["model"]["new"])

    def test_the_probe_reads_no_stdin(self) -> None:
        """vX (fix round r13): the probe inherited the script's stdin, so a
        CLI that reads stdin could consume what was meant for the script
        (bash fed through a pipe). The fake claude reports a version below
        the floor when it can read a line: with stdin from /dev/null it
        reads none. RED on the r12 derivation."""
        floor = self._floor()
        self._v14_seed()
        path = self._bin_with_script(
            "if read -r _line; then echo '1.0.0 (Claude Code)'; "
            "else echo '" + floor + " (Claude Code)'; fi\n")
        proc = self._upgrade(path, stdin_text="a line meant for the script\n")
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("Claude Code:  " + floor + " (floor " + floor + ": OK)",
                      proc.stdout)

    def test_the_harness_never_reads_the_host_cli(self) -> None:
        """vX (fix round r13): every spawn of this module (the plain
        run_migration included) runs with a FAKE claude at the floor first on
        PATH, so a host CLI below the floor can never turn these tests into
        exit 6, and a host CLI at any version never decides them. Before the
        cure _clean_env copied the host PATH: on a host with a claude on PATH
        the plain run_migration printed THAT version (measured S357 with
        2.1.281)."""
        floor = self._floor()
        env = _clean_env(None)
        found = shutil.which("claude", path=env["PATH"])
        self.assertIsNotNone(found)
        self.assertEqual(os.path.dirname(found), env["PATH"].split(os.pathsep)[0])
        self._v14_seed()
        proc = self.run_migration()
        self.assertIn("Claude Code:  " + floor + " (floor " + floor + ": OK)",
                      proc.stdout)

    def test_a_dry_run_names_the_refusal_and_writes_nothing(self) -> None:
        self._v14_seed()
        before = self.settings_path.read_bytes()
        proc = self._upgrade(self._bin_with("2.1.279 (Claude Code)"), ["--dry-run"])
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("(dry-run) would REFUSE: Claude Code 2.1.279", proc.stderr)
        self.assertEqual(self.settings_path.read_bytes(), before)

    def test_install_refuses_below_the_floor_before_any_write(self) -> None:
        target = Path(self._tmp) / "fresh"
        target.mkdir()
        proc = subprocess.run(
            ["bash", str(self.INSTALL_SH), str(target)],
            capture_output=True, text=True, timeout=120,
            env=_clean_env({"PATH": self._bin_with("2.1.279 (Claude Code)"),
                            "CEO_INSTALL_SKIP_SELF_SHA": "1"}))
        self.assertEqual(proc.returncode, 6, proc.stdout + proc.stderr)
        self.assertIn("ERROR: Claude Code 2.1.279 is below " + self._floor(),
                      proc.stderr)
        self.assertEqual(sorted(p.name for p in target.iterdir()), [])

    def test_both_helps_document_the_flag(self) -> None:
        for script in (UPGRADE_SH, self.INSTALL_SH):
            proc = subprocess.run(["bash", str(script), "--help"],
                                  capture_output=True, text=True, timeout=60,
                                  env=_clean_env(None))
            self.assertEqual(proc.returncode, 0, script)
            self.assertIn("--allow-old-claude-code", proc.stdout, script)


class TestNoHarnessReadsTheHostCli(_MigrationHarness):
    """ADR-149 Amendment 3, fix round r15 (rail round 2 of the wave, P2): the
    tests and the shell harnesses that run scripts/install.sh or
    scripts/upgrade.sh OUTSIDE this module and the two smokes inherited the
    host PATH, so a host claude below the floor turned them into exit 6
    before they exercised anything (reproduced S357 with a FAKE 2.1.279
    first on PATH). Cured by class at the two points every such run goes
    through, each guarded here: the pytest isolation layer
    (_lib/test_isolation.py, Axis 4) puts a FAKE claude at the floor first on
    the PATH of every test, and every shell harness that names an installer
    carries ONE byte-identical block, right after its first top-level set
    line, that exports a claude FUNCTION answering with that floor. RED on
    the r14 derivation: the suite PATH led to the host CLI and no harness
    carried the block."""

    _BEGIN = "# >>> harness-claude-stub (ADR-149 Amendment 3) >>>\n"
    _END = "# <<< harness-claude-stub <<<\n"
    INSTALL_SH = REPO_ROOT / "scripts" / "install.sh"
    REFERENCE = REPO_ROOT / "scripts" / "tests" / "smoke-install.sh"
    #: Where the census walks, and what it never walks into.
    _ROOTS = ("scripts", "tests", ".claude")
    _PRUNED = frozenset({".git", "__pycache__", "node_modules", "fixtures",
                         "worktrees"})
    _PRUNED_REL = frozenset({".claude/plans"})

    def _floor(self) -> str:
        found = [ln.split("=", 1)[1].strip('"') for ln in
                 self.INSTALL_SH.read_text(encoding="utf-8").splitlines()
                 if ln.startswith("CC_FLOOR_VERSION=")]
        self.assertEqual(len(found), 1, "scripts/install.sh must carry ONE "
                         "CC_FLOOR_VERSION line")
        return found[0]

    def _stub_block(self, path: Path) -> str:
        text = path.read_text(encoding="utf-8")
        self.assertEqual(text.count(self._BEGIN), 1, path)
        self.assertEqual(text.count(self._END), 1, path)
        start = text.index(self._BEGIN)
        return text[start:text.index(self._END) + len(self._END)]

    def _harnesses(self) -> List[Path]:
        """Every shell script under a directory named tests, or under
        scripts/local/, whose text names install.sh or upgrade.sh. A
        superset on purpose: a mention is enough, nothing about HOW the
        script runs an installer is parsed."""
        found = []
        for top in self._ROOTS:
            for dirpath, dirnames, filenames in os.walk(str(REPO_ROOT / top)):
                rel = Path(dirpath).relative_to(REPO_ROOT)
                dirnames[:] = sorted(
                    d for d in dirnames
                    if d not in self._PRUNED
                    and (rel / d).as_posix() not in self._PRUNED_REL)
                if "tests" not in rel.parts and rel.parts[:2] != ("scripts", "local"):
                    continue
                for name in sorted(filenames):
                    if not name.endswith(".sh"):
                        continue
                    path = Path(dirpath) / name
                    text = path.read_text(encoding="utf-8", errors="replace")
                    if "install.sh" in text or "upgrade.sh" in text:
                        found.append(path)
        return found

    def _checkout_with_host_cli(self, version: str) -> Tuple[Path, Path]:
        """A scratch checkout whose scripts/install.sh is the real one (the
        block reads its floor there), and a directory holding a FAKE host
        claude that reports ``version``."""
        checkout = Path(self._tmp) / "checkout"
        (checkout / "scripts" / "tests").mkdir(parents=True)
        (checkout / "scripts" / "install.sh").symlink_to(self.INSTALL_SH)
        host = Path(self._tmp) / "hostbin"
        host.mkdir()
        exe = host / "claude"
        exe.write_text("#!/bin/sh\necho '" + version + " (Claude Code)'\n",
                       encoding="utf-8")
        exe.chmod(0o755)
        return checkout, host

    def _require_the_pytest_session(self) -> None:
        """The suite isolation layer is a pytest SESSION fixture: under
        ``python -m unittest`` it never runs (the CI runs pytest only).
        pytest sets PYTEST_CURRENT_TEST while a test runs, so under pytest
        this never skips and a broken Axis 4 is RED."""
        if "PYTEST_CURRENT_TEST" not in os.environ:
            self.skipTest("the suite isolation layer runs under pytest only")

    def test_the_suite_puts_a_fake_claude_at_the_floor_first_on_path(self) -> None:
        self._require_the_pytest_session()
        floor = self._floor()
        first = os.environ.get("PATH", "").split(os.pathsep)[0]
        found = shutil.which("claude")
        self.assertIsNotNone(found, "no claude on the suite PATH")
        self.assertEqual(os.path.dirname(found), first)
        self.assertEqual(os.path.basename(first), "claude-code-stub")
        self.assertTrue(os.path.basename(os.path.dirname(first))
                        .startswith("ceo-suite-isolation-"), first)
        self.assertNotIn("BASH_FUNC_claude%%", os.environ)
        ver = subprocess.run([found, "--version"], capture_output=True,
                             text=True, timeout=30)
        self.assertEqual((ver.returncode, ver.stdout),
                         (0, floor + " (Claude Code)\n"))
        other = subprocess.run([found, "-p", "hello"], capture_output=True,
                               text=True, timeout=30)
        self.assertEqual((other.returncode, other.stdout), (127, ""))

    def test_an_installer_that_inherits_the_suite_env_reads_the_stub(self) -> None:
        self._require_the_pytest_session()
        floor = self._floor()
        self.seed({"model": "claude-opus-5",
                   "availableModels": list(baselines()["availableModels"]["new"])})
        env = dict(os.environ)
        env.pop("CEO_T34_NEW_EVENT_REGISTRATIONS", None)
        proc = subprocess.run(
            ["bash", str(UPGRADE_SH), str(self.target), "--settings-migrate-only",
             "--no-replay", "--no-deprecation-warn"],
            capture_output=True, text=True, timeout=120, env=env)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("Claude Code:  " + floor + " (floor " + floor + ": OK)",
                      proc.stdout)

    def test_every_shell_harness_that_names_an_installer_carries_the_block(self) -> None:
        reference = self._stub_block(self.REFERENCE)
        harnesses = self._harnesses()
        names = [p.relative_to(REPO_ROOT).as_posix() for p in harnesses]
        for known in ("scripts/tests/smoke-install.sh",
                      "scripts/local/smoke-install-parity.sh",
                      "scripts/tests/test-ownership-table.sh"):
            self.assertIn(known, names)
        for path, name in zip(harnesses, names):
            with self.subTest(harness=name):
                text = path.read_text(encoding="utf-8")
                self.assertEqual(self._stub_block(path), reference)
                offset = None
                position = 0
                for line in text.splitlines(True):
                    position += len(line)
                    if line.startswith("set -"):
                        offset = position
                        break
                self.assertIsNotNone(offset, "no top-level set line")
                self.assertTrue(text.startswith(self._BEGIN, offset),
                                "the block must follow the first set line")

    def test_the_block_shadows_a_host_cli_below_the_floor(self) -> None:
        """The control runs the same harness without the block first: the
        FAKE host 2.1.279 first on PATH is read and upgrade.sh refuses
        (exit 6) with nothing written; with the block the run passes."""
        floor = self._floor()
        checkout, host = self._checkout_with_host_cli("2.1.279")
        env = dict(os.environ)
        env["PATH"] = str(host) + os.pathsep + env.get("PATH", "")
        self.seed({"model": "claude-opus-5",
                   "availableModels": list(baselines()["availableModels"]["new"])})
        before = self.settings_path.read_bytes()
        runs = {}
        for name, body in (("bare", ""), ("stubbed", self._stub_block(self.REFERENCE))):
            harness = checkout / "scripts" / "tests" / (name + ".sh")
            harness.write_text(
                "#!/usr/bin/env bash\nset -uo pipefail\n" + body
                + 'bash "$1" "$2" --settings-migrate-only --no-replay'
                  ' --no-deprecation-warn\n', encoding="utf-8")
            runs[name] = subprocess.run(
                ["bash", str(harness), str(UPGRADE_SH), str(self.target)],
                capture_output=True, text=True, timeout=120, env=env)
            if name == "bare":
                self.assertEqual(self.settings_path.read_bytes(), before)
        bare, stubbed = runs["bare"], runs["stubbed"]
        self.assertEqual(bare.returncode, 6, bare.stdout + bare.stderr)
        self.assertIn("ERROR: Claude Code 2.1.279 is below " + floor, bare.stderr)
        self.assertEqual(stubbed.returncode, 0, stubbed.stdout + stubbed.stderr)
        self.assertIn("Claude Code:  " + floor + " (floor " + floor + ": OK)",
                      stubbed.stdout)

    def test_the_block_answers_under_any_path_a_child_is_given(self) -> None:
        floor = self._floor()
        checkout, host = self._checkout_with_host_cli("2.1.279")
        child = Path(self._tmp) / "child.sh"
        child.write_text('claude --version\nclaude -p hello\necho "rc=$?"\n',
                         encoding="utf-8")
        harness = checkout / "scripts" / "tests" / "path.sh"
        harness.write_text(
            "#!/usr/bin/env bash\nset -uo pipefail\n"
            + self._stub_block(self.REFERENCE)
            + 'env PATH="$1" "$BASH" "$2"\n', encoding="utf-8")
        proc = subprocess.run(["bash", str(harness), str(host), str(child)],
                              capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.stdout, floor + " (Claude Code)\nrc=127\n",
                         proc.stderr)
        self.assertIn("the harness stub answers only --version", proc.stderr)

    def test_the_block_refuses_a_checkout_without_one_floor_line(self) -> None:
        block = self._stub_block(self.REFERENCE)
        for install_text in ("#!/usr/bin/env bash\n",
                             'CC_FLOOR_VERSION="2.1.280"\nCC_FLOOR_VERSION="2.1.281"\n'):
            with self.subTest(install=install_text):
                root = Path(tempfile.mkdtemp(prefix="t54-nofloor-", dir=self._tmp))
                (root / "scripts" / "tests").mkdir(parents=True)
                (root / "scripts" / "install.sh").write_text(install_text,
                                                             encoding="utf-8")
                harness = root / "scripts" / "tests" / "h.sh"
                harness.write_text("#!/usr/bin/env bash\nset -uo pipefail\n"
                                   + block + "echo reached\n", encoding="utf-8")
                proc = subprocess.run(["bash", str(harness)], capture_output=True,
                                      text=True, timeout=60)
                self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
                self.assertNotIn("reached", proc.stdout)
                self.assertIn("carries no single CC_FLOOR_VERSION line", proc.stderr)


class TestEveryFailureExitKeepsTheOperatorFlags(_MigrationHarness):
    """ADR-149 Amendment 3, fix round r16 (rail round 3 of the wave, P2; Owner
    OQ-10, 2026-09-24, verbatim «Corrigir + rodada 4 final c/ anexo
    (Recomendado)»): the failure exit of the migration HELPER (settings.json
    unparseable, or the atomic write failed) printed its re-run WITHOUT the
    operator flags, so following it after repairing the JSON wrote high where
    --adopt-setting effortLevel asked for xhigh, and a present value is never
    overwritten afterwards. Cured by class: ONE builder (_t54_rerun_cmd), and
    every exit of the migration that leaves settings.json unmigrated prints
    what it builds. Each exit is forced here - by an unparseable settings.json
    or by a planted FAULT in a disposable copy of upgrade.sh (never a product
    seam) - and the printed command is parsed back as the shell would: it must
    carry exactly the operator's flags. RED on the r15 derivation of this
    wave: the helper exits printed no flag and the missing-python3 exit
    printed no command."""

    _OPERATOR = ["--adopt-setting", "effortLevel", "--adopt-setting",
                 "plantedKey", "--allow-old-claude-code"]
    #: exit -> (exact anchor in upgrade.sh, planted replacement). An anchor
    #: that is missing or repeated fails the test: a dead plant is never green.
    _FAULTS = {
        "backup": ('cp "$settings" '
                   '"$BAK_DIR/.claude/settings.json.pre-t54-migration"',
                   "false"),
        "atomic-write": ("    os.replace(tmp, path)\n",
                         '    raise OSError("planted atomic-write fault")\n'),
        "helper-crash": ("\nmode = sys.argv[1]\n",
                         '\nraise RuntimeError("planted helper fault")\n'),
        "no-python3": ("  if ! command -v python3 >/dev/null 2>&1; then\n"
                       '    echo "    NOTE: settings baseline migration skipped',
                       "  if true; then\n"
                       '    echo "    NOTE: settings baseline migration skipped'),
    }

    def _faulty(self, label: str, root: Optional[Path] = None) -> Path:
        anchor, planted = self._FAULTS[label]
        text = UPGRADE_SH.read_text(encoding="utf-8")
        self.assertEqual(text.count(anchor), 1, "the %s fault anchor moved: fix "
                         "the control, never skip it" % label)
        if root is None:
            root = Path(tempfile.mkdtemp(prefix="t54-fw-", dir=self._tmp))
        dst = root / "scripts" / "upgrade.sh"
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_text(text.replace(anchor, planted), encoding="utf-8")
        return dst

    def _seed_old(self) -> None:
        self.seed({"availableModels":
                   list(baselines()["availableModels"]["old"])})

    def _run(self, upgrade: Path, extra: List[str],
             extra_env: Optional[Dict[str, str]] = None
             ) -> "subprocess.CompletedProcess[str]":
        return subprocess.run(
            ["bash", str(upgrade), str(self.target), "--settings-migrate-only",
             "--no-replay", "--no-deprecation-warn"] + self._OPERATOR + extra,
            capture_output=True, text=True, timeout=120,
            env=_clean_env(extra_env))

    def _assert_rerun(self, proc: "subprocess.CompletedProcess[str]",
                      tail: List[str]) -> None:
        import shlex  # only this class parses a printed command back
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        hits = [ln for ln in proc.stderr.splitlines()
                if "--settings-migrate-only" in ln]
        self.assertEqual(len(hits), 1, "want ONE re-run line:\n" + proc.stderr)
        self.assertIn("scripts/upgrade.sh", hits[0])
        argv = shlex.split(hits[0][hits[0].index("scripts/upgrade.sh"):])
        self.assertEqual(argv[0], "scripts/upgrade.sh")
        self.assertEqual(os.path.realpath(argv[1]),
                         os.path.realpath(str(self.target)))
        self.assertEqual(argv[2:],
                         ["--settings-migrate-only"] + self._OPERATOR + tail)

    def test_every_failure_exit_prints_the_operator_flags(self) -> None:
        # (exit, planted fault or None, unparseable settings?, extra flags,
        #  names the pre-migration backup?)
        for label, fault, broken, extra, backup_named in (
            ("backup", "backup", False, [], False),
            ("unparseable", None, True, [], True),
            ("unparseable-dry-run", None, True, ["--dry-run"], False),
            ("atomic-write", "atomic-write", False, [], True),
            ("helper-crash", "helper-crash", False, [], True),
            ("helper-crash-dry-run", "helper-crash", False, ["--dry-run"], False),
            ("no-python3", "no-python3", False, [], False),
        ):
            with self.subTest(exit=label):
                self.setUp()
                if broken:
                    self.settings_path.write_text('{"model": ', encoding="utf-8")
                else:
                    self._seed_old()
                before = self.settings_path.read_bytes()
                upgrade = self._faulty(fault) if fault else UPGRADE_SH
                proc = self._run(upgrade, list(extra))
                self._assert_rerun(proc, list(extra))
                self.assertEqual(self.settings_path.read_bytes(), before)
                self.assertRegex(proc.stderr,
                                 r"settings baseline migration (SKIPPED|skipped)")
                self.assertEqual("Pre-migration backup:" in proc.stderr,
                                 backup_named, proc.stderr)

    def test_the_pin_rides_along_quoted_for_the_shell(self) -> None:
        """--pin picks the source checkout whose settings template the
        migration reads: the re-run carries it, quoted so that the shell
        hands the same ref back (a ref name may hold a shell metacharacter)."""
        root = Path(tempfile.mkdtemp(prefix="t54-pinfw-", dir=self._tmp))
        upgrade = self._faulty("helper-crash", root)
        git_env = {"GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull}
        git = ["git", "-C", str(root), "-c", "user.name=selftest",
               "-c", "user.email=selftest@example.invalid",
               "-c", "commit.gpgsign=false"]
        ref = "pin;v1"
        for argv in (["init", "-q"], ["add", "scripts/upgrade.sh"],
                     ["commit", "-q", "-m", "fw"], ["branch", ref]):
            done = subprocess.run(git + argv, capture_output=True, text=True,
                                  timeout=60, env=_clean_env(git_env))
            self.assertEqual(done.returncode, 0, done.stdout + done.stderr)
        self._seed_old()
        before = self.settings_path.read_bytes()
        proc = self._run(upgrade, ["--pin", ref], extra_env=git_env)
        self._assert_rerun(proc, ["--pin", ref])
        self.assertIn("--pin pin\\;v1", proc.stderr)
        self.assertEqual(self.settings_path.read_bytes(), before)

    def test_the_target_rides_along_quoted_for_the_shell(self) -> None:
        """The target is a value the operator supplied too: a space, a dollar
        sign or a quote in its path must reach the shell as the same path."""
        self.target = Path(self._tmp) / "odd dir $HOME 'q'"
        (self.target / ".claude").mkdir(parents=True)
        self.settings_path.write_text('{"model": ', encoding="utf-8")
        before = self.settings_path.read_bytes()
        proc = self._run(UPGRADE_SH, [])
        self._assert_rerun(proc, [])
        self.assertEqual(self.settings_path.read_bytes(), before)

    def test_no_exit_builds_its_own_command(self) -> None:
        """The migration body names flags in its warnings (re-run WITH
        --adopt-setting <key>), but a runnable command - the script path and
        the migrate-only switch - exists only in the builder."""
        text = UPGRADE_SH.read_text(encoding="utf-8")
        self.assertEqual(text.count("\n_t54_rerun_cmd() {\n"), 1)
        start = text.index("\n_migrate_settings_baseline() {\n")
        body = text[start:text.index("\n}\n\n# ====", start)]
        for shape in ("scripts/upgrade.sh", "--settings-migrate-only"):
            self.assertNotIn(shape, body, "an exit builds its own re-run")
        self.assertEqual(body.count("$(_t54_rerun_cmd)"), 3,
                         "the backup, missing-python3 and helper exits")


class TestMixedStateAndIdempotency(_MigrationHarness):
    """U2 mixed-state fixture + U3 idempotency oracle."""

    def _mixed(self) -> Dict:
        return {
            # branch (ii): equal to OLD baseline -> must migrate
            "availableModels": list(baselines()["availableModels"]["old"]),
            # branch (iii): customized -> must be preserved + WARN
            "fallbackModel": ["my-custom-fallback"],
            # branch (i): permissions absent entirely -> SET new baseline
            # branch (i): model absent entirely -> SET new pin (no "model" key)
            # unrelated custom registration: must survive untouched
            "hooks": {
                "PreToolUse": [
                    {"matcher": "Bash",
                     "hooks": [{"type": "command", "command": "echo custom"}]}
                ]
            },
        }

    def test_mixed_state_per_branch(self) -> None:
        self.seed(self._mixed())
        proc = self.run_migration()
        data = self.read_settings()
        self.assertEqual(data["availableModels"],
                         baselines()["availableModels"]["new"])
        self.assertEqual(data["fallbackModel"], ["my-custom-fallback"])
        self.assertIn("WARNING: fallbackModel is ADOPTER-CUSTOMIZED",
                      proc.stderr)
        self.assertEqual(data["permissions"]["defaultMode"],
                         baselines()["permissions.defaultMode"]["new"])
        # model was absent in the fixture -> SET to the new pin.
        self.assertEqual(data["model"], baselines()["model"]["new"])
        self.assertIn(
            "SET (absent [== old baseline] -> new baseline): model",
            proc.stdout,
        )
        self.assertEqual(
            data["hooks"]["PreToolUse"][0]["hooks"][0]["command"],
            "echo custom",
        )

    def test_idempotency_run_twice_is_byte_identical(self) -> None:
        """U3: a second run changes NOTHING (byte-for-byte)."""
        self.seed(self._mixed())
        self.run_migration()
        first = self.settings_path.read_bytes()
        proc2 = self.run_migration()
        second = self.settings_path.read_bytes()
        self.assertEqual(first, second)
        # ... and the second run performs no migration actions at all.
        self.assertNotIn("MIGRATE (", proc2.stdout)
        self.assertNotIn("SET (", proc2.stdout)
        self.assertIn("idempotent no-op", proc2.stdout)

    def test_dry_run_previews_without_writing(self) -> None:
        self.seed(self._mixed())
        before = self.settings_path.read_bytes()
        proc = self.run_migration(dry=True)
        self.assertEqual(self.settings_path.read_bytes(), before)
        self.assertIn("(dry-run) would MIGRATE", proc.stdout)
        self.assertFalse((self.target / ".claude.bak").exists(),
                         "--dry-run must not create the backup dir")

    def test_no_settings_migrate_opt_out(self) -> None:
        self.seed(self._mixed())
        before = self.settings_path.read_bytes()
        self.run_migration(extra_args=["--no-settings-migrate"])
        self.assertEqual(self.settings_path.read_bytes(), before)


class TestNewEventRegistrationsGate(_MigrationHarness):
    """T3.4 feature gate for the DirectoryAdded/Notification registrations."""

    def _events(self) -> Dict:
        return baselines()["registrations"]

    def test_gate_off_by_default_adds_nothing(self) -> None:
        self.seed({})
        proc = self.run_migration()  # gate default: OFF (version-floor pending)
        data = self.read_settings()
        for event in self._events():
            self.assertNotIn(event, data.get("hooks", {}))
        self.assertIn("GATED OFF (T3.4 version-floor)", proc.stdout)

    def test_gate_on_adds_canonical_entries_when_absent(self) -> None:
        self.seed({})
        self.run_migration(gate_on=True)
        data = self.read_settings()
        for event, spec in self._events().items():
            self.assertEqual(data["hooks"][event], [spec["entry"]],
                             "canonical entry derived from the artifact")

    def test_gate_on_preserves_custom_entries_and_appends(self) -> None:
        custom = {"matcher": "",
                  "hooks": [{"type": "command",
                             "command": "echo my-custom-notify"}]}
        self.seed({"hooks": {"Notification": [custom]}})
        self.run_migration(gate_on=True)
        data = self.read_settings()
        notif = data["hooks"]["Notification"]
        self.assertEqual(notif[0], custom, "custom entry preserved in place")
        self.assertEqual(notif[1],
                         self._events()["Notification"]["entry"])

    def test_gate_on_is_idempotent(self) -> None:
        self.seed({})
        self.run_migration(gate_on=True)
        first = self.settings_path.read_bytes()
        proc2 = self.run_migration(gate_on=True)
        self.assertEqual(self.settings_path.read_bytes(), first)
        self.assertNotIn("ADD (", proc2.stdout)
        for event in self._events():
            self.assertEqual(len(self.read_settings()["hooks"][event]), 1)


class TestPairRailTimeoutValueMigration(_MigrationHarness, TestEnvContext):
    """PLAN-164 W1 (debate R1 consensus C2/C5; OQ2=150 ratified): pair-rail
    registration-timeout VALUE migration in upgrade.sh.

    The pre-PLAN-164 registration cap (60) sat below the measured codex
    verdict latency (N=9, p95 ~75s) — 12/12 historical pair_rail_case rows
    were F/TIMEOUT (PLAN-163/probes/GATE-V2-2026-07-29-FAIL-diagnosis.md).
    Ratified migration semantics: bump the check_pair_rail.py registration
    timeout to the template cap IFF the adopter's current value is one of
    the SUPERSEDED SHIPPED caps; ANY other adopter-chosen value is
    PRESERVED; round 2 is an idempotent no-op. The NEW expectation is
    DERIVED from the template artifact (settings.base.json pair-rail entry
    — install.sh copies it verbatim, so template value == post-install
    value == migration target); each superseded cap is a frozen historical
    literal, exactly like the "old" column of the
    --print-settings-baselines table. The ratified literal (210)
    materializes ONCE, in the U1 template-parity oracle below.

    ADR-110-AMEND-2: the superseded set is (60, 150), not just 60. 150 was
    the AMEND-1 cap SHIPPED IN v1.2.0, so every v1.2.0 adopter carries it
    verbatim. Leaving it as "adopter-customized" is not the conservative
    reading — with the hook-internal default now 180, a 150s registration
    means the HARNESS kills the hook before the hook's own codex cap
    fires, and a killed hook emits NO pair_rail_case at all (§6: fail-open
    with NO event, invisible to the instrument in both numerator and
    denominator) — strictly worse than the case F it replaces.

    Base order (_MigrationHarness, TestEnvContext): scratch-target fixtures
    from the family harness + S283 env-hygiene isolation; both setUps are
    chained explicitly because _MigrationHarness.setUp does not call super.
    """

    #: Frozen historical literal — the pre-PLAN-164 registration cap that
    #: produced the F/TIMEOUT class (never derived; it no longer exists in
    #: any live artifact once the migration lands).
    OLD_REGISTRATION_CAP = 60

    #: Every SUPERSEDED SHIPPED cap, frozen (ADR-110-AMEND-2). 60 =
    #: pre-PLAN-164; 150 = the AMEND-1 cap shipped in v1.2.0. Each must
    #: migrate, because each sits BELOW the current internal default + the
    #: 30s inter-layer margin — i.e. each leaves the harness able to kill
    #: the hook before its own codex cap fires (§6, no-event fail-open).
    SUPERSEDED_SHIPPED_CAPS = (60, 150)

    _PAIR_RAIL_CMD = (
        "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh\""
        " check_pair_rail.py"
    )
    _UNRELATED_CMD = (
        "bash \"$CLAUDE_PROJECT_DIR/.claude/hooks/_python-hook.sh\""
        " check_bash_safety.py"
    )

    def setUp(self) -> None:
        TestEnvContext.setUp(self)
        _MigrationHarness.setUp(self)

    # -- artifact-derived expectations ----------------------------------

    @staticmethod
    def _pair_rail_entries(settings_obj: Dict) -> List[Dict]:
        return [
            h
            for block in settings_obj.get("hooks", {}).get("PreToolUse", [])
            for h in block.get("hooks", [])
            if "check_pair_rail.py" in h.get("command", "")
        ]

    def _new_registration_cap(self) -> int:
        """The migration target, DERIVED from the template artifact."""
        entries = self._pair_rail_entries(
            json.loads(TEMPLATE_SETTINGS.read_text(encoding="utf-8")))
        self.assertEqual(
            len(entries), 1,
            "template must carry exactly one pair-rail registration")
        return entries[0]["timeout"]

    def _seed_with_pair_rail_timeout(self, timeout: int) -> None:
        """Adopter settings.json carrying the pre-PLAN-164 pair-rail
        registration shape PLUS one unrelated registration that also uses
        the old cap value (an over-broad `bump every timeout==60` sweep
        must not touch it)."""
        self.seed({
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "Edit|Write|MultiEdit",
                        "hooks": [{
                            "type": "command",
                            "command": self._PAIR_RAIL_CMD,
                            "timeout": timeout,
                        }],
                    },
                    {
                        "matcher": "Bash",
                        "hooks": [{
                            "type": "command",
                            "command": self._UNRELATED_CMD,
                            "timeout": self.OLD_REGISTRATION_CAP,
                        }],
                    },
                ]
            }
        })

    def _migrated_pair_rail_timeout(self) -> int:
        entries = self._pair_rail_entries(self.read_settings())
        self.assertEqual(
            len(entries), 1,
            "exactly one pair-rail registration must survive migration")
        return entries[0]["timeout"]

    # -- oracles ---------------------------------------------------------

    def test_template_registration_carries_ratified_cap_210(self) -> None:
        """U1 parity: the ratified ADR-110-AMEND-2 value (210) — pinned
        once, here. Was 150 under PLAN-164 OQ2."""
        self.assertEqual(self._new_registration_cap(), 210)

    def test_old_cap_60_is_migrated_to_new_cap(self) -> None:
        self._seed_with_pair_rail_timeout(self.OLD_REGISTRATION_CAP)
        self.run_migration()
        self.assertEqual(self._migrated_pair_rail_timeout(),
                         self._new_registration_cap())

    def test_every_superseded_shipped_cap_is_migrated(self) -> None:
        """ADR-110-AMEND-2: the migration matches a SET, not one literal.

        RED-FIRST against the AMEND-1 migration (`cur == 60`): the 150
        case lands in the `else` arm and is PRESERVED as
        "adopter-customized" — leaving every v1.2.0 adopter with a
        registration BELOW internal-default + margin, i.e. the harness
        kills the hook before its own codex cap fires and NO
        pair_rail_case is emitted at all.
        """
        new_cap = self._new_registration_cap()
        for old_cap in self.SUPERSEDED_SHIPPED_CAPS:
            with self.subTest(old_cap=old_cap):
                self.assertNotEqual(
                    old_cap, new_cap,
                    "a superseded cap equal to the live template cap is a "
                    "bookkeeping error — it can never be observed migrating")
                self.setUp()  # fresh scratch target per seeded value
                self._seed_with_pair_rail_timeout(old_cap)
                self.run_migration()
                self.assertEqual(
                    self._migrated_pair_rail_timeout(), new_cap,
                    "superseded shipped cap %ds was not migrated to the "
                    "template cap %ds — an adopter left below "
                    "internal-default + 30s margin has the harness kill "
                    "the hook before its own codex cap fires, and a killed "
                    "hook emits NO pair_rail_case (ADR-110-AMEND-2 §6)"
                    % (old_cap, new_cap))

    def test_superseded_caps_all_below_new_cap(self) -> None:
        """Every frozen member must be a value the CURRENT contract
        rejects — otherwise the set has silently grown a live value."""
        new_cap = self._new_registration_cap()
        for old_cap in self.SUPERSEDED_SHIPPED_CAPS:
            self.assertLess(
                old_cap, new_cap,
                "superseded cap %ds >= live template cap %ds — the frozen "
                "set must contain ONLY retired values" % (old_cap, new_cap))

    def test_migration_brings_template_status_message_iff_absent(self) -> None:
        """grok r1 LOW-3 / codex r2: the SAME migration event that bumps the
        cap also imports the template statusMessage — but only when the
        adopter has none (never overwrites a customized one)."""
        tpl_entries = self._pair_rail_entries(
            json.loads(TEMPLATE_SETTINGS.read_text(encoding="utf-8")))
        tpl_status = tpl_entries[0].get("statusMessage")
        self.assertTrue(
            isinstance(tpl_status, str) and tpl_status.strip(),
            "template pair-rail registration must carry a statusMessage")
        self._seed_with_pair_rail_timeout(self.OLD_REGISTRATION_CAP)
        self.run_migration()
        migrated = self._pair_rail_entries(self.read_settings())[0]
        self.assertEqual(migrated.get("statusMessage"), tpl_status)

    def test_adopter_custom_status_message_is_preserved(self) -> None:
        custom_status = "adopter-tuned message"
        self.seed({
            "hooks": {
                "PreToolUse": [
                    {
                        "matcher": "Edit|Write|MultiEdit",
                        "hooks": [{
                            "type": "command",
                            "command": self._PAIR_RAIL_CMD,
                            "timeout": self.OLD_REGISTRATION_CAP,
                            "statusMessage": custom_status,
                        }],
                    },
                ]
            }
        })
        self.run_migration()
        migrated = self._pair_rail_entries(self.read_settings())[0]
        self.assertEqual(migrated["timeout"], self._new_registration_cap())
        self.assertEqual(migrated["statusMessage"], custom_status)

    def test_unrelated_registration_with_old_cap_value_untouched(self) -> None:
        """Only the check_pair_rail.py registration migrates."""
        self._seed_with_pair_rail_timeout(self.OLD_REGISTRATION_CAP)
        self.run_migration()
        others = [
            h
            for block in self.read_settings()["hooks"]["PreToolUse"]
            for h in block.get("hooks", [])
            if "check_bash_safety.py" in h.get("command", "")
        ]
        self.assertEqual([h["timeout"] for h in others],
                         [self.OLD_REGISTRATION_CAP])

    def test_second_run_is_idempotent_zero_reapplication(self) -> None:
        self._seed_with_pair_rail_timeout(self.OLD_REGISTRATION_CAP)
        self.run_migration()
        first = self.settings_path.read_bytes()
        self.run_migration()
        self.assertEqual(
            self.settings_path.read_bytes(), first,
            "round 2 must be byte-identical (zero re-application)")
        self.assertEqual(self._migrated_pair_rail_timeout(),
                         self._new_registration_cap())

    def test_adopter_custom_timeout_is_preserved(self) -> None:
        """The oracle must NOT require the new value unconditionally."""
        custom = 90
        self.assertNotEqual(custom, self.OLD_REGISTRATION_CAP)
        self.assertNotEqual(custom, self._new_registration_cap())
        self._seed_with_pair_rail_timeout(custom)
        self.run_migration()
        self.assertEqual(self._migrated_pair_rail_timeout(), custom)


class TestU1TemplateParity(TestEnvContext):
    """U1 (post-install): the fresh-install template must already carry the
    NEW baselines — install.sh copies templates/settings/settings.base.json
    verbatim, so template parity IS the post-install oracle. Expectations are
    derived from the artifact (`--print-settings-baselines`), not hardcoded.
    """

    def _template(self) -> Dict:
        return json.loads(TEMPLATE_SETTINGS.read_text(encoding="utf-8"))

    def test_template_available_models_is_new_baseline(self) -> None:
        self.assertEqual(self._template()["availableModels"],
                         baselines()["availableModels"]["new"])

    def test_template_fallback_model_is_new_baseline(self) -> None:
        self.assertEqual(self._template()["fallbackModel"],
                         baselines()["fallbackModel"]["new"])

    def test_template_model_pin_is_new_baseline(self) -> None:
        self.assertEqual(self._template()["model"],
                         baselines()["model"]["new"])

    def test_template_effort_level_is_new_baseline(self) -> None:
        self.assertEqual(self._template()["effortLevel"],
                         baselines()["effortLevel"]["new"])

    def test_template_default_mode_is_new_baseline(self) -> None:
        self.assertEqual(
            self._template()["permissions"]["defaultMode"],
            baselines()["permissions.defaultMode"]["new"],
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
