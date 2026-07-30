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

import json
import os
import shutil
import subprocess
import sys
import tempfile
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
        )
        if proc.returncode != 0:
            raise AssertionError(
                "upgrade.sh --print-settings-baselines rc=%s stderr=%s"
                % (proc.returncode, proc.stderr)
            )
        _BASELINES_CACHE = json.loads(proc.stdout)
    return _BASELINES_CACHE


def _clean_env(extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    env = os.environ.copy()
    # The T3.4 gate env override must not leak in from the outer session.
    env.pop("CEO_T34_NEW_EVENT_REGISTRATIONS", None)
    if extra:
        env.update(extra)
    return env


class _MigrationHarness(unittest.TestCase):
    """Scratch-target harness driving upgrade.sh --settings-migrate-only."""

    def setUp(self) -> None:
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


class TestDefaultModeBranches(_MigrationHarness):
    """U2 — per-branch oracles for permissions.defaultMode.

    Read contract: _lib/effective_config.py:178-180,534-542 (a stripped
    string under the permissions object).
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

    _PIN_NOT_APPLIED = (
        "WARNING: model pin NOT applied: adopter availableModels excludes "
        "claude-opus-5 (session default left to harness/adopter)"
    )

    def _pin(self) -> str:
        return baselines()["model"]["new"]

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
        self.assertIn(self._PIN_NOT_APPLIED, proc.stderr)

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
        self.assertIn(self._PIN_NOT_APPLIED, proc.stderr)

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
        self.assertIn(self._PIN_NOT_APPLIED, proc2.stderr)


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
    timeout 60 -> 150 IFF the adopter's current value == 60 (the old cap);
    ANY other adopter-chosen value is PRESERVED; round 2 is an idempotent
    no-op. The NEW expectation is DERIVED from the template artifact
    (settings.base.json pair-rail entry — install.sh copies it verbatim, so
    template value == post-install value == migration target); the OLD cap
    (60) is a frozen historical literal, exactly like the "old" column of
    the --print-settings-baselines table. The ratified OQ2 literal (150)
    materializes ONCE, in the U1 template-parity oracle below.

    Base order (_MigrationHarness, TestEnvContext): scratch-target fixtures
    from the family harness + S283 env-hygiene isolation; both setUps are
    chained explicitly because _MigrationHarness.setUp does not call super.
    """

    #: Frozen historical literal — the pre-PLAN-164 registration cap that
    #: produced the F/TIMEOUT class (never derived; it no longer exists in
    #: any live artifact once the migration lands).
    OLD_REGISTRATION_CAP = 60

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

    def test_template_registration_carries_ratified_cap_150(self) -> None:
        """U1 parity: the ratified OQ2 value (150) — pinned once, here."""
        self.assertEqual(self._new_registration_cap(), 150)

    def test_old_cap_60_is_migrated_to_new_cap(self) -> None:
        self._seed_with_pair_rail_timeout(self.OLD_REGISTRATION_CAP)
        self.run_migration()
        self.assertEqual(self._migrated_pair_rail_timeout(),
                         self._new_registration_cap())

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


class TestU1TemplateParity(unittest.TestCase):
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

    def test_template_default_mode_is_new_baseline(self) -> None:
        self.assertEqual(
            self._template()["permissions"]["defaultMode"],
            baselines()["permissions.defaultMode"]["new"],
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
