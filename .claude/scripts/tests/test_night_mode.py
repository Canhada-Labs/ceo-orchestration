"""Tests for ``night-mode.py`` — PLAN-165 W1 T1.3.

Owner-invoked autonomy posture toggle. The script under test implements
the PLAN-165 write contract:

- ``on``   — merge-write ``.claude/settings.local.json`` setting
             ``permissions.defaultMode: "acceptEdits"`` (lock, temp file +
             ``fsync`` + ``os.replace``, read-back, snapshot create-only),
             then writes the marker/snapshot file.
- ``off``  — restores the snapshotted prior state (prior value, key
             removal, or unlink when night-mode created the file), then
             removes the marker.
- ``status`` — reports the resolved posture and whether marker and
             resolved configuration AGREE or DISAGREE.

Fixed by W0 (PLAN-165/probes/W0-EVIDENCE.md — do not revisit here):

- marker + snapshot live in ONE file at ``<project>/.claude/state/night-mode.json``;
- no tty gate; refusal under ``CI`` is the enforcement (AC-11, exit 2);
- default target mode is ``acceptEdits``; ``bypassPermissions`` never appears.

Env-hygiene (check-test-env-hygiene.py): every test class subclasses
``TestEnvContext`` and mutates the environment ONLY via
``unittest.mock.patch.dict`` (never a raw ``os.environ[...] =``), so
teardown restores state and the suite stays hermetic. Subprocess
invocations receive an explicitly-constructed env (isolated HOME from
TestEnvContext, ``CI``/``GITHUB_ACTIONS`` stripped except in the AC-11
refusal tests — CI runners export ``CI=true``, which would otherwise trip
the refusal path in every test).

The marker path must be anchored per ``--project-root`` at call time —
never an import-time module constant (PLAN-165 T1.3: a path constant
resolved at import time escapes TestEnvContext isolation). Covered by
``NightModePathAnchoringTest``.

Round-2 security review (PLAN-165/architect/round-2/security-review.md):

- NM-01/NM-10 — ``off`` validates the marker's ``prev_value`` against a
  closed set; a planted ``bypassPermissions`` (or any non-string) marker
  is refused fail-CLOSED (``NightModeRestoreClosedSetTest``).
- NM-02 — after a crash-desync (overlay armed, marker gone), a fresh
  ``on`` must NOT snapshot night-mode's own value
  (``NightModeDesyncReOnTest``).
- NM-04 — ``--project-root`` is confined to the repository unless the
  test-only ``CEO_NIGHT_MODE_TEST_SEAM`` env var is set. The helpers
  below set the seam because every test root is an isolated tmp tree
  (``NightModeRootConfinementTest`` exercises the refusal by omitting it).
- NM-05 — a machine-readable ``night-mode-event ... result=...`` line is
  asserted on refused / noop / failed paths
  (``NightModeSummaryLineTest``).

Round-3 security review (findings NF-01..NF-04):

- NF-01/NF-02 — the restorable set is DERIVED from the harness's real
  ``--permission-mode`` enum and excludes both ``bypassPermissions`` and
  night-mode's own ``acceptEdits``
  (``NightModeRestorableSetDerivationTest``,
  ``NightModePlantedOwnValueTest``); a legitimate ``dontAsk`` overlay
  round-trips (``NightModeDontAskRoundTripTest``).
- NF-02 — ``off --discard-snapshot`` is the sanctioned exit from every
  fail-closed refusal (``NightModeDiscardSnapshotTest``).
- NF-03 — the marker is validated as a WHOLE DOCUMENT before any field is
  acted on (``NightModeMarkerDocumentValidationTest``).
- NF-04 — a STRUCTURAL ``ast`` oracle pins one terminal-summary call
  immediately before every ``return`` in the toggle commands
  (``NightModeTerminalPathOracleTest``).

Round-4 security review (findings NF-05..NF-06 — one class, two surfaces:
untrusted gitignored documents echoed into LINE-ORIENTED records without
collapsing line breaks):

- NF-05 — ``cmd_on``'s success line routes the overlay's raw prior
  ``defaultMode`` through ``_bounded_repr``: a planted ``\n`` can no
  longer forge a second ``night-mode-event`` row and a huge value cannot
  flood stdout (``NightModeSummaryForgeryTest``).
- NF-06 — ``_validate_marker`` also gates ``ts``/``hostname`` (bounded,
  control-char-free strings) and ``status`` RUNS the validator: an
  invalid marker renders ``PRESENT but INVALID`` with a DISAGREE verdict
  — never AGREE — and a planted line break in ``hostname`` cannot forge
  an extra ``reconciliation:`` line
  (``NightModeStatusMarkerValidationTest``).

Round-3 RE-REVIEW (findings NF-07, NF-09 — both about records that claimed
more than the code did):

- NF-07 — ``night_mode_toggled`` shipped REGISTERED and EMPTY: an entry in
  ``_KNOWN_ACTIONS``, a typed wrapper, a signed SPEC row and three surfaces
  claiming the emit, with zero production callers. Both existing gates
  stayed green because they reconcile NAMES, not LIVENESS. Now the emit is
  the sibling of every ``_summary`` call, the ``ast`` oracle pins the PAIR
  (``_TERMINAL_HELPERS``, ``NightModeMainRecordPairingTest``), and the row
  is asserted on the LOG rather than in the source
  (``NightModeAuditRowTest``) — including that it never blocks the toggle
  (``NightModeAuditFailOpenTest``).
- NF-09 — ``off`` on the route where the overlay had already been removed
  by hand wrote nothing and reported ``restored to '<snapshot>'`` /
  ``result=applied`` anyway. It now reports ``absent`` / ``noop``
  (``NightModeOverlayGoneRouteTest``, with the normal restore kept as the
  control so the fix cannot pass by breaking ``off``).
"""

from __future__ import annotations

import ast
import importlib.util
import io
import json
import os
import socket
import subprocess
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))
from _lib.testing import TestEnvContext  # noqa: E402

SCRIPT = REPO_ROOT / ".claude" / "scripts" / "night-mode.py"

# Env keys that must never leak into the subject: CI refusal triggers
# (GitHub Actions exports CI=true on every runner).
_CI_KEYS = ("CI", "GITHUB_ACTIONS")

# NM-04 test seam: every test root is an isolated tmp tree OUTSIDE the
# repository, so the confinement must be lifted for the suite (and
# deliberately NOT lifted in NightModeRootConfinementTest).
_SEAM_ENV = "CEO_NIGHT_MODE_TEST_SEAM"


def _load_module():
    """Load night-mode.py by path (it is a script, not a package)."""
    spec = importlib.util.spec_from_file_location("night_mode", str(SCRIPT))
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _NightModeBase(TestEnvContext):
    """Shared fixture: a draft project tree + clean invocation helpers."""

    def setUp(self) -> None:
        super().setUp()
        # Draft project inside the isolated tmp tree (never the real repo).
        self.root = Path(self.project_dir) / "nm-project"
        (self.root / ".claude").mkdir(parents=True)
        # Mirror the live posture: tracked project layer pins manual.
        self._write_json(
            self.project_settings,
            {
                "permissions": {"defaultMode": "manual"},
                "disableAutoMode": "disable",
            },
        )

    # -- paths -------------------------------------------------------------

    @property
    def project_settings(self) -> Path:
        return self.root / ".claude" / "settings.json"

    @property
    def local_settings(self) -> Path:
        return self.root / ".claude" / "settings.local.json"

    @property
    def marker(self) -> Path:
        return self.root / ".claude" / "state" / "night-mode.json"

    # -- helpers -----------------------------------------------------------

    def _write_json(self, path: Path, data: Dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")

    def _read_json(self, path: Path) -> Dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    def _subprocess_env(self, extra: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Isolated env for the child: TestEnvContext HOME, no CI leak.

        Sets the NM-04 test seam because every test root lives in an
        isolated tmp tree outside the repository.
        """
        env = {k: v for k, v in os.environ.items() if k not in _CI_KEYS}
        env[_SEAM_ENV] = "1"
        if extra:
            env.update(extra)
        return env

    def run_cli(
        self,
        *args: str,
        extra_env: Optional[Dict[str, str]] = None,
    ) -> "subprocess.CompletedProcess[str]":
        with mock.patch.dict(os.environ, {}, clear=False):
            return subprocess.run(
                [sys.executable, str(SCRIPT), *args,
                 "--project-root", str(self.root)],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.project_dir),
                env=self._subprocess_env(extra_env),
            )

    def run_inproc(self, mod, argv: List[str]) -> Tuple[int, str, str]:
        """Drive main() in-process; normalize return-int vs SystemExit."""
        out, err = io.StringIO(), io.StringIO()
        patched = {k: "" for k in _CI_KEYS}
        patched[_SEAM_ENV] = "1"  # NM-04: in-proc roots are tmp trees too
        with mock.patch.dict(os.environ, patched, clear=False):
            for k in _CI_KEYS:
                os.environ.pop(k, None)
            with redirect_stdout(out), redirect_stderr(err):
                try:
                    rc = mod.main(argv)
                except SystemExit as exc:  # main() may sys.exit()
                    rc = 0 if exc.code is None else int(exc.code)
        return (0 if rc is None else int(rc)), out.getvalue(), err.getvalue()


# ---------------------------------------------------------------------------
# Smoke
# ---------------------------------------------------------------------------


class NightModeSmokeTest(_NightModeBase):
    def test_script_exists(self):
        self.assertTrue(SCRIPT.is_file(), "night-mode.py missing on disk")

    def test_on_creates_local_settings_and_marker(self):
        result = self.run_cli("on")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = self._read_json(self.local_settings)
        self.assertEqual(data["permissions"]["defaultMode"], "acceptEdits")
        self.assertTrue(self.marker.is_file(), "marker/snapshot file missing")
        # Marker + snapshot is one parseable JSON object (W0 T0.7 decision).
        marker = self._read_json(self.marker)
        self.assertIsInstance(marker, dict)

    def test_never_writes_bypass_permissions(self):
        # D1: bypassPermissions was CUT. It must not appear in anything
        # night-mode writes, under any invocation exercised here.
        self.run_cli("on")
        blobs = [self.local_settings.read_text(encoding="utf-8")]
        if self.marker.is_file():
            blobs.append(self.marker.read_text(encoding="utf-8"))
        for blob in blobs:
            self.assertNotIn("bypassPermissions", blob)

    def test_tracked_project_settings_untouched(self):
        before = self.project_settings.read_bytes()
        self.run_cli("on")
        self.run_cli("off")
        self.assertEqual(self.project_settings.read_bytes(), before)


# ---------------------------------------------------------------------------
# Merge preserves unrelated keys
# ---------------------------------------------------------------------------


class NightModeMergeTest(_NightModeBase):
    def test_merge_preserves_unrelated_top_level_and_permissions_subkeys(self):
        self._write_json(
            self.local_settings,
            {
                "model": "opus",
                "env": {"FOO": "1"},
                "permissions": {
                    "allow": ["Bash(ls:*)"],
                    "deny": ["Read(./secret.txt)"],
                    "defaultMode": "plan",
                },
            },
        )
        result = self.run_cli("on")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = self._read_json(self.local_settings)
        # Unrelated top-level keys survive.
        self.assertEqual(data["model"], "opus")
        self.assertEqual(data["env"], {"FOO": "1"})
        # Unrelated permissions subkeys survive.
        self.assertEqual(data["permissions"]["allow"], ["Bash(ls:*)"])
        self.assertEqual(data["permissions"]["deny"], ["Read(./secret.txt)"])
        # Only defaultMode flipped.
        self.assertEqual(data["permissions"]["defaultMode"], "acceptEdits")

    def test_off_preserves_unrelated_keys_too(self):
        self._write_json(
            self.local_settings,
            {"model": "opus", "permissions": {"allow": ["Bash(ls:*)"]}},
        )
        self.run_cli("on")
        result = self.run_cli("off")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = self._read_json(self.local_settings)
        self.assertEqual(data["model"], "opus")
        self.assertEqual(data["permissions"]["allow"], ["Bash(ls:*)"])


# ---------------------------------------------------------------------------
# Snapshot round-trip (present AND absent prior value)
# ---------------------------------------------------------------------------


class NightModeSnapshotRoundTripTest(_NightModeBase):
    def test_roundtrip_prior_value_present_is_restored_exactly(self):
        self._write_json(
            self.local_settings,
            {"permissions": {"defaultMode": "plan", "allow": ["Bash(ls:*)"]}},
        )
        self.run_cli("on")
        result = self.run_cli("off")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = self._read_json(self.local_settings)
        self.assertEqual(data["permissions"]["defaultMode"], "plan")
        self.assertEqual(data["permissions"]["allow"], ["Bash(ls:*)"])

    def test_roundtrip_prior_key_absent_key_is_removed(self):
        # Local file exists but carries no defaultMode: off must remove the
        # key night-mode added, not leave any defaultMode behind.
        self._write_json(self.local_settings, {"model": "opus"})
        self.run_cli("on")
        result = self.run_cli("off")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = self._read_json(self.local_settings)
        self.assertNotIn(
            "defaultMode", data.get("permissions", {}) or {},
            "off must remove the key when the prior state had none",
        )
        self.assertEqual(data["model"], "opus")

    def test_roundtrip_prior_file_absent_created_file_is_unlinked(self):
        # Marker-lifecycle created_file case: night-mode created
        # settings.local.json, so off restores the exact prior state —
        # no file at all.
        self.assertFalse(self.local_settings.exists())
        self.run_cli("on")
        self.assertTrue(self.local_settings.is_file())
        result = self.run_cli("off")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(
            self.local_settings.exists(),
            "off must unlink the settings.local.json night-mode created",
        )
        self.assertFalse(self.marker.exists(), "marker must be gone after off")


# ---------------------------------------------------------------------------
# Snapshot is CREATE-ONLY (AC-3)
# ---------------------------------------------------------------------------


class NightModeSnapshotCreateOnlyTest(_NightModeBase):
    def test_on_on_off_returns_to_manual_not_acceptedits(self):
        # AC-3: a second `on` must NOT re-snapshot the acceptEdits value
        # that night-mode itself wrote — otherwise `off` "restores" to
        # acceptEdits and the weak posture becomes permanent.
        self.assertEqual(self.run_cli("on").returncode, 0)
        self.assertEqual(self.run_cli("on").returncode, 0)
        result = self.run_cli("off")
        self.assertEqual(result.returncode, 0, result.stderr)
        if self.local_settings.exists():
            data = self._read_json(self.local_settings)
            mode = (data.get("permissions") or {}).get("defaultMode")
            self.assertNotEqual(
                mode, "acceptEdits",
                "snapshot was overwritten by the second on (not create-only)",
            )
        # With no prior local override the resolved posture is the
        # project's manual again.
        from _lib.effective_config import resolve_settings

        resolved = resolve_settings(self.root)
        eff_mode = (resolved["effective"].get("permissions") or {}).get(
            "defaultMode"
        )
        self.assertEqual(eff_mode, "manual")

    def test_on_on_off_with_prior_value_returns_to_prior_value(self):
        self._write_json(
            self.local_settings, {"permissions": {"defaultMode": "plan"}}
        )
        self.run_cli("on")
        self.run_cli("on")
        self.run_cli("off")
        data = self._read_json(self.local_settings)
        self.assertEqual(data["permissions"]["defaultMode"], "plan")


# ---------------------------------------------------------------------------
# Idempotency: double-on / double-off are no-op exit 0
# ---------------------------------------------------------------------------


class NightModeIdempotencyTest(_NightModeBase):
    def test_double_on_is_noop_exit_zero(self):
        self.assertEqual(self.run_cli("on").returncode, 0)
        after_first = self._read_json(self.local_settings)
        result = self.run_cli("on")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self._read_json(self.local_settings), after_first)

    def test_double_off_is_noop_exit_zero(self):
        self.run_cli("on")
        self.assertEqual(self.run_cli("off").returncode, 0)
        result = self.run_cli("off")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_off_without_ever_on_is_noop_exit_zero(self):
        result = self.run_cli("off")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(self.marker.exists())


# ---------------------------------------------------------------------------
# Malformed input is fail-CLOSED (AC-4)
# ---------------------------------------------------------------------------


class NightModeMalformedInputTest(_NightModeBase):
    def test_malformed_local_settings_exit_2_bytes_unchanged(self):
        self.local_settings.parent.mkdir(parents=True, exist_ok=True)
        garbage = b'{ "permissions": { this is not json'
        self.local_settings.write_bytes(garbage)
        result = self.run_cli("on")
        self.assertEqual(
            result.returncode, 2,
            "malformed input must be fail-CLOSED with exit 2, got %s\n%s"
            % (result.returncode, result.stderr),
        )
        self.assertEqual(
            self.local_settings.read_bytes(), garbage,
            "the malformed file must not be rewritten or 'repaired'",
        )
        self.assertFalse(
            self.marker.exists(),
            "marker must not be written when settings write was refused",
        )

    def test_malformed_local_settings_blocks_off_too(self):
        self.run_cli("on")
        garbage = b"not json at all"
        self.local_settings.write_bytes(garbage)
        result = self.run_cli("off")
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(self.local_settings.read_bytes(), garbage)


# ---------------------------------------------------------------------------
# Atomic replace + read-back
# ---------------------------------------------------------------------------


class NightModeAtomicWriteTest(_NightModeBase):
    def test_successful_on_leaves_parseable_file(self):
        # A truncating in-place write makes the harness skip the whole
        # file (S286 class). After on, the file must parse.
        self._write_json(
            self.local_settings, {"model": "opus", "permissions": {}}
        )
        result = self.run_cli("on")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = self._read_json(self.local_settings)  # raises if truncated
        self.assertEqual(data["permissions"]["defaultMode"], "acceptEdits")

    def test_readback_failure_exits_nonzero_and_skips_marker(self):
        # The write contract mandates temp + fsync + os.replace, then a
        # read-back re-parse; divergence => non-zero exit WITHOUT touching
        # the marker. Simulate a corrupted landing by wrapping os.replace
        # to clobber the target with garbage after the replace.
        mod = _load_module()
        real_replace = os.replace

        def corrupting_replace(src, dst, *a, **kw):
            real_replace(src, dst, *a, **kw)
            if str(dst).endswith("settings.local.json"):
                Path(dst).write_bytes(b"{ corrupted-after-replace")

        with mock.patch("os.replace", side_effect=corrupting_replace):
            rc, _out, _err = self.run_inproc(
                mod, ["on", "--project-root", str(self.root)]
            )
        self.assertNotEqual(
            rc, 0, "read-back must catch the corrupted write and exit non-zero"
        )
        self.assertFalse(
            self.marker.exists(),
            "marker must not be written after a failed read-back",
        )


# ---------------------------------------------------------------------------
# Crash between settings write and marker write (AC-5)
# ---------------------------------------------------------------------------


class NightModeCrashDesyncTest(_NightModeBase):
    def test_settings_written_marker_missing_status_reports_disagree(self):
        # Ordering contract: settings first, marker second. A crash in
        # between leaves settings flipped and no marker — status must
        # report the disagreement instead of picking a winner.
        self.run_cli("on")
        self.marker.unlink()  # simulate the crash end-state
        self.assertTrue(
            json.loads(self.local_settings.read_text(encoding="utf-8")),
            "settings file must remain parseable after the simulated crash",
        )
        result = self.run_cli("status")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("DISAGREE", result.stdout.upper())

    def test_marker_present_settings_reverted_status_reports_disagree(self):
        # The other desync direction: Owner hand-reverted the overlay but
        # the marker survived.
        self.run_cli("on")
        self._write_json(
            self.local_settings, {"permissions": {"defaultMode": "manual"}}
        )
        result = self.run_cli("status")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("DISAGREE", result.stdout.upper())


# ---------------------------------------------------------------------------
# Status AGREE / DISAGREE reporting
# ---------------------------------------------------------------------------


class NightModeStatusTest(_NightModeBase):
    def test_status_agree_when_on_and_consistent(self):
        self.run_cli("on")
        result = self.run_cli("status")
        self.assertEqual(result.returncode, 0, result.stderr)
        upper = result.stdout.upper()
        self.assertIn("AGREE", upper)
        self.assertNotIn("DISAGREE", upper)

    def test_status_when_fully_off_exits_zero_and_reports_manual(self):
        result = self.run_cli("status")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("manual", result.stdout)
        self.assertNotIn("DISAGREE", result.stdout.upper())

    def test_status_reports_resolved_mode_after_on(self):
        self.run_cli("on")
        result = self.run_cli("status")
        self.assertIn("acceptEdits", result.stdout)


# ---------------------------------------------------------------------------
# CI refusal (AC-11)
# ---------------------------------------------------------------------------


class NightModeCiRefusalTest(_NightModeBase):
    def test_on_refuses_under_ci_exit_2(self):
        # Seam set (NM-04 must not shadow the gate under test), CI set.
        with mock.patch.dict(
            os.environ, {"CI": "true", _SEAM_ENV: "1"}, clear=False
        ):
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "on",
                 "--project-root", str(self.root)],
                capture_output=True, text=True, timeout=30,
                cwd=str(self.project_dir),
                env=dict(os.environ),
            )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertFalse(
            self.local_settings.exists(),
            "refusal under CI must not write the overlay",
        )
        self.assertFalse(self.marker.exists())
        # NM-05: the refusal still leaves a machine-readable record.
        self.assertIn("night-mode-event", result.stdout)
        self.assertIn("result=refused", result.stdout)

    def test_off_refuses_under_ci_exit_2(self):
        self.run_cli("on")
        flipped = self.local_settings.read_bytes()
        with mock.patch.dict(
            os.environ, {"CI": "1", _SEAM_ENV: "1"}, clear=False
        ):
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "off",
                 "--project-root", str(self.root)],
                capture_output=True, text=True, timeout=30,
                cwd=str(self.project_dir),
                env=dict(os.environ),
            )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(self.local_settings.read_bytes(), flipped)
        self.assertIn("result=refused", result.stdout)


# ---------------------------------------------------------------------------
# Marker path anchored per --project-root, never an import-time constant
# ---------------------------------------------------------------------------


class NightModePathAnchoringTest(_NightModeBase):
    def test_marker_path_follows_project_root_within_one_import(self):
        # Load the module ONCE, then drive two different roots through the
        # SAME module object. If the marker path were an import-time
        # constant, both invocations would collapse onto one path.
        mod = _load_module()

        root_a = Path(self.project_dir) / "nm-root-a"
        root_b = Path(self.project_dir) / "nm-root-b"
        for root in (root_a, root_b):
            (root / ".claude").mkdir(parents=True)
            self._write_json(
                root / ".claude" / "settings.json",
                {"permissions": {"defaultMode": "manual"}},
            )

        rc_a, _o, err_a = self.run_inproc(
            mod, ["on", "--project-root", str(root_a)]
        )
        rc_b, _o, err_b = self.run_inproc(
            mod, ["on", "--project-root", str(root_b)]
        )
        self.assertEqual(rc_a, 0, err_a)
        self.assertEqual(rc_b, 0, err_b)

        marker_a = root_a / ".claude" / "state" / "night-mode.json"
        marker_b = root_b / ".claude" / "state" / "night-mode.json"
        self.assertTrue(marker_a.is_file(), "root A marker missing")
        self.assertTrue(marker_b.is_file(), "root B marker missing")

        # off on root A must not disturb root B.
        rc_off, _o, err_off = self.run_inproc(
            mod, ["off", "--project-root", str(root_a)]
        )
        self.assertEqual(rc_off, 0, err_off)
        self.assertFalse(marker_a.exists())
        self.assertTrue(
            marker_b.is_file(),
            "off on root A removed root B's marker — path not anchored "
            "per --project-root",
        )

    def test_no_marker_written_outside_project_root(self):
        # The W0 T0.7 decision moved the marker OUT of ~/.claude into the
        # project tree. Nothing may land under the (isolated) HOME.
        home = Path(os.environ["HOME"])
        before = set(home.rglob("night-mode*"))
        self.run_cli("on")
        after = set(home.rglob("night-mode*"))
        self.assertEqual(
            before, after,
            "night-mode wrote marker state under $HOME — must live at "
            "<project>/.claude/state/night-mode.json",
        )


# ---------------------------------------------------------------------------
# NM-01 / NM-10 — restore is closed-set validated (planted marker refused)
# ---------------------------------------------------------------------------


class NightModeRestoreClosedSetTest(_NightModeBase):
    def _plant_prev_value(self, value: Any) -> None:
        marker = self._read_json(self.marker)
        marker["prev_present"] = True
        marker["prev_value"] = value
        self._write_json(self.marker, marker)

    def test_planted_bypass_marker_off_refuses_exit_2(self):
        # NM-01 CRITICAL: a gitignored, unguarded marker hand-set to
        # bypassPermissions must NOT be laundered into the overlay by the
        # Owner's own `off`. Fail-closed: exit 2, overlay byte-unchanged,
        # marker left in place as evidence.
        self.run_cli("on")
        overlay_before = self.local_settings.read_bytes()
        self._plant_prev_value("bypassPermissions")
        marker_before = self.marker.read_bytes()

        result = self.run_cli("off")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(
            self.local_settings.read_bytes(), overlay_before,
            "off must not touch the overlay when the marker is tampered",
        )
        self.assertEqual(
            self.marker.read_bytes(), marker_before,
            "the tampered marker must be left in place (evidence)",
        )
        self.assertNotIn(
            "bypassPermissions",
            self.local_settings.read_text(encoding="utf-8"),
        )
        self.assertIn("result=refused", result.stdout)

    def test_non_string_prev_value_refused(self):
        # NM-10: a dict/list/number in permissions.defaultMode makes the
        # harness skip the WHOLE settings file (S286 class) — never restore
        # a non-string.
        self.run_cli("on")
        self._plant_prev_value({"defaultMode": "manual"})
        result = self.run_cli("off")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertTrue(self.marker.exists(), "marker must be left in place")
        data = self._read_json(self.local_settings)
        self.assertEqual(data["permissions"]["defaultMode"], "acceptEdits")

    def test_unknown_string_mode_refused(self):
        self.run_cli("on")
        self._plant_prev_value("totallyLegitMode")
        result = self.run_cli("off")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertTrue(self.marker.exists())

    def test_known_safe_modes_still_restore(self):
        # The closed set must not break the legitimate round-trip.
        self._write_json(
            self.local_settings, {"permissions": {"defaultMode": "plan"}}
        )
        self.run_cli("on")
        result = self.run_cli("off")
        self.assertEqual(result.returncode, 0, result.stderr)
        data = self._read_json(self.local_settings)
        self.assertEqual(data["permissions"]["defaultMode"], "plan")


# ---------------------------------------------------------------------------
# NM-02 — desync (overlay armed, marker gone) then on/off must not freeze
# acceptEdits
# ---------------------------------------------------------------------------


class NightModeDesyncReOnTest(_NightModeBase):
    def test_desync_then_on_then_off_ends_on_project_posture(self):
        # Crash end-state: settings armed, marker lost. A fresh `on` must
        # NOT snapshot night-mode's own acceptEdits — otherwise `off`
        # "restores" acceptEdits and the weak posture is permanent.
        self.run_cli("on")
        self.marker.unlink()  # simulated crash

        result_on = self.run_cli("on")
        self.assertEqual(result_on.returncode, 0, result_on.stderr)
        self.assertIn(
            "desync", result_on.stderr.lower(),
            "the desync normalization must be announced",
        )
        marker = self._read_json(self.marker)
        self.assertFalse(
            marker["prev_present"],
            "night-mode must never snapshot its own value (NM-02)",
        )
        self.assertIsNone(marker["prev_value"])

        result_off = self.run_cli("off")
        self.assertEqual(result_off.returncode, 0, result_off.stderr)
        if self.local_settings.exists():
            data = self._read_json(self.local_settings)
            self.assertNotEqual(
                (data.get("permissions") or {}).get("defaultMode"),
                "acceptEdits",
                "off after a desync-on must not leave acceptEdits armed",
            )
        from _lib.effective_config import resolve_settings

        resolved = resolve_settings(self.root)
        eff_mode = (resolved["effective"].get("permissions") or {}).get(
            "defaultMode"
        )
        self.assertEqual(
            eff_mode, "manual",
            "the posture must end on the project layer's manual",
        )
        self.assertFalse(self.marker.exists(), "off must remove the marker")


# ---------------------------------------------------------------------------
# NM-04 — --project-root confinement
# ---------------------------------------------------------------------------


class NightModeRootConfinementTest(_NightModeBase):
    def _run_raw(
        self, *args: str, drop_seam: bool, root: Path
    ) -> "subprocess.CompletedProcess[str]":
        dropped = set(_CI_KEYS) | ({_SEAM_ENV} if drop_seam else set())
        env = {k: v for k, v in os.environ.items() if k not in dropped}
        if not drop_seam:
            env[_SEAM_ENV] = "1"
        return subprocess.run(
            [sys.executable, str(SCRIPT), *args, "--project-root", str(root)],
            capture_output=True, text=True, timeout=30,
            cwd=str(self.project_dir), env=env,
        )

    def test_out_of_tree_root_refused_without_seam(self):
        # The test root is an isolated tmp tree OUTSIDE the repository —
        # exactly the arbitrary-path write primitive NM-04 closes. Without
        # the test seam the invocation must be refused with no writes.
        result = self._run_raw("on", drop_seam=True, root=self.root)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertFalse(
            self.local_settings.exists(),
            "confinement refusal must not write the overlay",
        )
        self.assertFalse(self.marker.exists())
        self.assertIn("result=refused", result.stdout)

    def test_off_out_of_tree_also_refused_without_seam(self):
        result = self._run_raw("off", drop_seam=True, root=self.root)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("result=refused", result.stdout)

    def test_target_without_settings_json_refused_even_with_seam(self):
        # Even with the seam, the target must already be an installed
        # project (.claude/settings.json present).
        bare = Path(self.project_dir) / "bare-root"
        (bare / ".claude").mkdir(parents=True)
        result = self._run_raw("on", drop_seam=False, root=bare)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertFalse(
            (bare / ".claude" / "settings.local.json").exists(),
            "no overlay may be bootstrapped into a bare tree",
        )

    def test_seam_does_not_widen_outside_tempdir(self):
        # NM-04 hardening (S290 review): the seam widens confinement ONLY
        # to targets under the system temp directory. With the seam SET
        # but the child's TMPDIR redirected to a tree DISJOINT from the
        # target root, the invocation must still be refused — the
        # "TEST_MODE-is-a-bypass" class (S284) stays closed even when the
        # env var leaks into a live session.
        faketmp = Path(self.project_dir) / "faketmp"
        faketmp.mkdir()
        dropped = set(_CI_KEYS)
        env = {k: v for k, v in os.environ.items() if k not in dropped}
        env[_SEAM_ENV] = "1"
        env["TMPDIR"] = str(faketmp)  # child gettempdir() != self.root's tree
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "on", "--project-root", str(self.root)],
            capture_output=True, text=True, timeout=30,
            cwd=str(self.project_dir), env=env,
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertFalse(
            self.local_settings.exists(),
            "a seam that widens beyond the temp directory is the NM-04 "
            "bypass class — no overlay may be written",
        )
        self.assertIn("result=refused", result.stdout)


# ---------------------------------------------------------------------------
# NM-05 — machine-readable one-line summary on every terminating path
# ---------------------------------------------------------------------------


class NightModeSummaryLineTest(_NightModeBase):
    def test_applied_paths_emit_summary(self):
        result_on = self.run_cli("on")
        self.assertIn("night-mode-event", result_on.stdout)
        self.assertIn("result=applied", result_on.stdout)
        result_off = self.run_cli("off")
        self.assertIn("result=applied", result_off.stdout)

    def test_noop_paths_emit_summary(self):
        # off-without-on and double-on are both idempotent no-ops.
        result_off = self.run_cli("off")
        self.assertEqual(result_off.returncode, 0)
        self.assertIn("night-mode-event", result_off.stdout)
        self.assertIn("result=noop", result_off.stdout)
        self.run_cli("on")
        result_on2 = self.run_cli("on")
        self.assertIn("result=noop", result_on2.stdout)

    def test_refused_path_malformed_input_emits_summary(self):
        self.local_settings.parent.mkdir(parents=True, exist_ok=True)
        self.local_settings.write_bytes(b"not json")
        result = self.run_cli("on")
        self.assertEqual(result.returncode, 2)
        self.assertIn("night-mode-event", result.stdout)
        self.assertIn("result=refused", result.stdout)

    def test_failed_path_readback_emits_summary(self):
        # Reuse the read-back corruption harness from
        # NightModeAtomicWriteTest: the failure must still leave a record.
        mod = _load_module()
        real_replace = os.replace

        def corrupting_replace(src, dst, *a, **kw):
            real_replace(src, dst, *a, **kw)
            if str(dst).endswith("settings.local.json"):
                Path(dst).write_bytes(b"{ corrupted-after-replace")

        with mock.patch("os.replace", side_effect=corrupting_replace):
            rc, out, _err = self.run_inproc(
                mod, ["on", "--project-root", str(self.root)]
            )
        self.assertNotEqual(rc, 0)
        self.assertIn("night-mode-event", out)
        self.assertIn("result=failed", out)


# ---------------------------------------------------------------------------
# NF-01 / NF-02 — the restorable set is DERIVED from the harness enum
# ---------------------------------------------------------------------------


class NightModeRestorableSetDerivationTest(_NightModeBase):
    """The closed set must be derived, not hand-listed (NF-02).

    The round-2 hand-listed set drifted in BOTH directions at once: it
    carried ``default`` (never a ``--permission-mode`` choice) and omitted
    ``dontAsk`` (a legal one). The omission was the dangerous half — an
    Owner whose overlay legitimately carried ``dontAsk`` had it snapshotted
    by ``on`` and then hit a PERMANENT ``off`` refusal with ``acceptEdits``
    left armed, i.e. a fail-closed gate landing on the permissive side.
    """

    # Verified against `claude --help` on the pinned CLI (2026-08-03).
    _CLI_CHOICES = frozenset(
        {"acceptEdits", "auto", "bypassPermissions", "manual", "dontAsk", "plan"}
    )

    def test_harness_enum_constant_matches_the_cli_choices(self):
        mod = _load_module()
        self.assertEqual(
            set(mod._HARNESS_PERMISSION_MODES), set(self._CLI_CHOICES),
            "the recorded harness --permission-mode enum drifted from the "
            "verified CLI choices — update _HARNESS_PERMISSION_MODES (the "
            "restorable set derives from it)",
        )

    def test_restorable_set_is_the_enum_minus_two_exclusions(self):
        mod = _load_module()
        self.assertEqual(
            set(mod._RESTORABLE_MODES),
            set(self._CLI_CHOICES) - {"bypassPermissions", "acceptEdits"},
            "_RESTORABLE_MODES must be _HARNESS_PERMISSION_MODES minus "
            "bypassPermissions (D1) and acceptEdits (NF-01)",
        )
        self.assertEqual(
            set(mod._RESTORABLE_MODES), {"manual", "auto", "dontAsk", "plan"}
        )

    def test_set_excludes_bypass_and_night_mode_and_the_bogus_default(self):
        mod = _load_module()
        self.assertNotIn("bypassPermissions", mod._RESTORABLE_MODES)
        self.assertNotIn(mod.NIGHT_MODE, mod._RESTORABLE_MODES)
        self.assertNotIn(
            "default", mod._RESTORABLE_MODES,
            "'default' is not a harness permission mode — it was a "
            "hand-listing artefact (NF-02)",
        )
        self.assertIn(
            "dontAsk", mod._RESTORABLE_MODES,
            "'dontAsk' IS a legal harness mode; omitting it strands the "
            "Owner with acceptEdits armed (NF-02)",
        )
        self.assertTrue(set(mod._RESTORABLE_MODES) <= set(mod._HARNESS_PERMISSION_MODES))


class NightModeDontAskRoundTripTest(_NightModeBase):
    def test_legitimate_dontask_overlay_round_trips_cleanly(self):
        # NF-02 regression: with the round-2 hand-listed set this exact
        # sequence exited 2 on EVERY off, forever, with acceptEdits armed.
        self._write_json(
            self.local_settings,
            {"model": "opus", "permissions": {"defaultMode": "dontAsk"}},
        )
        on = self.run_cli("on")
        self.assertEqual(on.returncode, 0, on.stderr)
        marker = self._read_json(self.marker)
        self.assertTrue(marker["prev_present"])
        self.assertEqual(marker["prev_value"], "dontAsk")

        off = self.run_cli("off")
        self.assertEqual(
            off.returncode, 0,
            "a legitimate dontAsk snapshot must restore, not refuse:\n"
            + off.stdout + off.stderr,
        )
        data = self._read_json(self.local_settings)
        self.assertEqual(data["permissions"]["defaultMode"], "dontAsk")
        self.assertEqual(data["model"], "opus")
        self.assertFalse(self.marker.exists(), "off must remove the marker")


# ---------------------------------------------------------------------------
# NF-01 — a planted prev_value of night-mode's OWN value can never re-arm
# ---------------------------------------------------------------------------


class NightModePlantedOwnValueTest(_NightModeBase):
    """A marker carrying ``prev_value="acceptEdits"`` must never re-arm.

    NF-01 (verified live before the fix): ``acceptEdits`` was inside the
    closed set although ``cmd_on``'s NM-02 normalization guarantees a
    healthy marker can never carry it. So a planted marker passed the gate,
    ``off`` exited 0, re-wrote ``acceptEdits`` into the overlay AND removed
    the marker — leaving the posture ARMED WITH NO MARKER, which makes
    every later ``off`` a forever no-op.
    """

    def _plant(self, **fields: Any) -> None:
        marker = self._read_json(self.marker)
        marker.update(fields)
        self._write_json(self.marker, marker)

    def test_planted_own_value_is_refused_and_state_is_not_armed_unmarked(self):
        self.run_cli("on")
        overlay_before = self.local_settings.read_bytes()
        self._plant(prev_present=True, prev_value="acceptEdits")
        marker_before = self.marker.read_bytes()

        result = self.run_cli("off")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("result=refused", result.stdout)
        self.assertEqual(
            self.local_settings.read_bytes(), overlay_before,
            "a refused restore must not touch the overlay",
        )
        # The end state that NF-01 produced — armed, marker gone, off a
        # forever no-op — must be impossible: the marker is still here.
        self.assertTrue(
            self.marker.exists(),
            "the tampered marker must be left in place as evidence; an "
            "armed overlay with NO marker is the NF-01 end state",
        )
        self.assertEqual(self.marker.read_bytes(), marker_before)

    def test_refusal_diagnostic_points_at_the_recovery_flag(self):
        self.run_cli("on")
        self._plant(prev_present=True, prev_value="acceptEdits")
        result = self.run_cli("off")
        self.assertEqual(result.returncode, 2)
        self.assertIn("--discard-snapshot", result.stderr)

    def test_discard_snapshot_recovers_from_the_planted_own_value(self):
        self.run_cli("on")
        self._plant(prev_present=True, prev_value="acceptEdits")
        result = self.run_cli("off", "--discard-snapshot")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(self.marker.exists(), "discard must remove the marker")
        if self.local_settings.exists():
            data = self._read_json(self.local_settings)
            self.assertNotIn("defaultMode", data.get("permissions", {}) or {})
        from _lib.effective_config import resolve_settings

        resolved = resolve_settings(self.root)
        self.assertEqual(
            (resolved["effective"].get("permissions") or {}).get("defaultMode"),
            "manual",
            "after recovery the posture must be the project layer's manual",
        )

    def test_symmetric_normalization_holds_even_if_the_set_is_loosened(self):
        # Belt and braces (NF-01): cmd_off applies cmd_on's normalization
        # too. Today _RESTORABLE_MODES excludes NIGHT_MODE so validation
        # refuses first; this test loosens the SET to prove the second layer
        # independently refuses to re-arm rather than being dead code.
        self._write_json(self.local_settings, {"model": "opus"})
        self.run_cli("on")
        marker = self._read_json(self.marker)
        self.assertFalse(marker["created_file"])
        marker["prev_present"] = True
        marker["prev_value"] = "acceptEdits"
        self._write_json(self.marker, marker)

        mod = _load_module()
        loosened = frozenset(set(mod._RESTORABLE_MODES) | {mod.NIGHT_MODE})
        with mock.patch.object(mod, "_RESTORABLE_MODES", loosened):
            rc, _out, err = self.run_inproc(
                mod, ["off", "--project-root", str(self.root)]
            )
        self.assertEqual(rc, 0, err)
        data = self._read_json(self.local_settings)
        self.assertNotIn(
            "defaultMode", data.get("permissions", {}) or {},
            "the symmetric normalization must REMOVE the override instead "
            "of re-arming acceptEdits",
        )
        self.assertEqual(data["model"], "opus")
        self.assertIn(
            "no prior override", err,
            "the second-layer normalization must announce itself:\n" + err,
        )
        self.assertFalse(self.marker.exists())


# ---------------------------------------------------------------------------
# NF-03 — the marker is validated as a WHOLE DOCUMENT, not field by field
# ---------------------------------------------------------------------------


class NightModeMarkerDocumentValidationTest(_NightModeBase):
    """Every marker field is untrusted input, not just ``prev_value``.

    NF-03 (verified live before the fix): round-2 gated ``prev_value``
    alone, so ``prev_present``, ``created_file``, ``mode_written`` and
    ``version`` were still trusted from the same gitignored,
    agent-writable document — and the overlay ``os.unlink`` branch is
    reachable from ``created_file`` alone, giving silent data loss on an
    exit-0 ``result=applied`` path.
    """

    def _plant(self, **fields: Any) -> bytes:
        marker = self._read_json(self.marker)
        marker.update(fields)
        self._write_json(self.marker, marker)
        return self.marker.read_bytes()

    def _assert_refused(self, field: str) -> "subprocess.CompletedProcess[str]":
        overlay_before = (
            self.local_settings.read_bytes()
            if self.local_settings.exists()
            else None
        )
        result = self.run_cli("off")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("result=refused", result.stdout)
        self.assertIn(
            field, result.stderr,
            "the diagnostic must name the offending field",
        )
        self.assertIn("--discard-snapshot", result.stderr)
        self.assertTrue(self.marker.exists(), "marker must be left in place")
        if overlay_before is not None:
            self.assertEqual(self.local_settings.read_bytes(), overlay_before)
        return result

    def test_wrong_version_refused(self):
        self.run_cli("on")
        self._plant(version=2)
        self._assert_refused("version")

    def test_boolean_true_version_refused(self):
        # `True == 1` in Python: a bare `== MARKER_VERSION` check would pass.
        self.run_cli("on")
        self._plant(version=True)
        self._assert_refused("version")

    def test_wrong_mode_written_refused(self):
        self.run_cli("on")
        self._plant(mode_written="bypassPermissions")
        self._assert_refused("mode_written")

    def test_non_bool_prev_present_refused(self):
        self.run_cli("on")
        self._plant(prev_present="yes", prev_value="manual")
        self._assert_refused("prev_present")

    def test_non_bool_created_file_refused(self):
        self.run_cli("on")
        self._plant(created_file=1)
        self._assert_refused("created_file")

    def test_missing_prev_present_refused(self):
        self.run_cli("on")
        marker = self._read_json(self.marker)
        marker.pop("prev_present")
        self._write_json(self.marker, marker)
        self._assert_refused("prev_present")

    def test_prev_value_set_while_prev_present_false_refused(self):
        # The NF-03 plant: created_file flipped to true while a prior value
        # is still recorded. Honoring it would unlink an overlay night-mode
        # did not create.
        self._write_json(
            self.local_settings, {"permissions": {"defaultMode": "plan"}}
        )
        self.run_cli("on")
        self._plant(created_file=True, prev_present=False, prev_value="plan")
        self._assert_refused("prev_value")
        self.assertTrue(
            self.local_settings.exists(),
            "the overlay must still exist after the refusal (no unlink)",
        )

    def test_created_file_and_prev_present_both_true_refused(self):
        self._write_json(
            self.local_settings, {"permissions": {"defaultMode": "plan"}}
        )
        self.run_cli("on")
        self._plant(created_file=True)  # prev_present stays true
        result = self._assert_refused("created_file")
        self.assertIn("prev_present", result.stderr)
        self.assertTrue(self.local_settings.exists())

    def test_forged_created_file_cannot_unlink_an_owner_authored_overlay(self):
        # The residual NF-03 case that no marker field can distinguish (the
        # "did the file pre-exist" fact lives ONLY in the marker): a fully
        # self-consistent forgery. The destructive branch additionally
        # requires the overlay's CURRENT content to be, in full, exactly
        # what `on` writes when it creates the file — so an Owner-authored
        # overlay survives.
        self._write_json(self.local_settings, {"model": "opus"})
        self.run_cli("on")
        marker = self._read_json(self.marker)
        self.assertFalse(marker["created_file"])
        self._plant(created_file=True)  # prev_present already false
        result = self.run_cli("off")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(
            self.local_settings.exists(),
            "a forged created_file must not unlink an overlay carrying the "
            "Owner's own keys (NF-03)",
        )
        self.assertEqual(self._read_json(self.local_settings)["model"], "opus")

    def test_unparseable_marker_refusal_points_at_the_recovery_flag(self):
        self.run_cli("on")
        self.marker.write_bytes(b"{ not json")
        result = self.run_cli("off")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn("--discard-snapshot", result.stderr)
        self.assertTrue(self.marker.exists())


# ---------------------------------------------------------------------------
# NF-02 — `off --discard-snapshot`: the sanctioned exit from every refusal
# ---------------------------------------------------------------------------


class NightModeDiscardSnapshotTest(_NightModeBase):
    """A fail-closed refusal must never strand the operator.

    NF-02: with no recovery flag, an unknown/refused snapshot left the
    posture armed and exit 2 on every attempt, recoverable only by
    hand-editing two gitignored files. ``off --discard-snapshot`` removes
    the override AND the marker WITHOUT honoring ``prev_value``.
    """

    def _plant(self, **fields: Any) -> None:
        marker = self._read_json(self.marker)
        marker.update(fields)
        self._write_json(self.marker, marker)

    def _assert_disarmed(self) -> None:
        self.assertFalse(self.marker.exists(), "marker must be gone")
        if self.local_settings.exists():
            data = self._read_json(self.local_settings)
            self.assertNotIn("defaultMode", data.get("permissions", {}) or {})
        from _lib.effective_config import resolve_settings

        resolved = resolve_settings(self.root)
        self.assertEqual(
            (resolved["effective"].get("permissions") or {}).get("defaultMode"),
            "manual",
        )

    def test_recovers_from_planted_bypass_permissions(self):
        self.run_cli("on")
        self._plant(prev_present=True, prev_value="bypassPermissions")
        self.assertEqual(self.run_cli("off").returncode, 2)
        result = self.run_cli("off", "--discard-snapshot")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self._assert_disarmed()
        self.assertNotIn(
            "bypassPermissions",
            self.local_settings.read_text(encoding="utf-8")
            if self.local_settings.exists() else "",
        )

    def test_recovers_from_unknown_mode_and_echoes_it_loudly(self):
        self.run_cli("on")
        self._plant(prev_present=True, prev_value="totallyLegitMode")
        self.assertEqual(self.run_cli("off").returncode, 2)
        result = self.run_cli("off", "--discard-snapshot")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(
            "totallyLegitMode", result.stdout,
            "discard must print the raw prev_value it threw away",
        )
        self.assertIn("result=applied", result.stdout)
        self._assert_disarmed()

    def test_recovers_from_non_string_prev_value(self):
        self.run_cli("on")
        self._plant(prev_present=True, prev_value={"defaultMode": "manual"})
        self.assertEqual(self.run_cli("off").returncode, 2)
        self.assertEqual(self.run_cli("off", "--discard-snapshot").returncode, 0)
        self._assert_disarmed()

    def test_recovers_from_invalid_version_and_mode_written(self):
        self.run_cli("on")
        self._plant(version=99, mode_written="nope")
        self.assertEqual(self.run_cli("off").returncode, 2)
        self.assertEqual(self.run_cli("off", "--discard-snapshot").returncode, 0)
        self._assert_disarmed()

    def test_recovers_from_non_bool_fields(self):
        self.run_cli("on")
        self._plant(prev_present="yes", created_file="no")
        self.assertEqual(self.run_cli("off").returncode, 2)
        self.assertEqual(self.run_cli("off", "--discard-snapshot").returncode, 0)
        self._assert_disarmed()

    def test_recovers_from_an_unparseable_marker(self):
        self.run_cli("on")
        self.marker.write_bytes(b"{ not json at all")
        self.assertEqual(self.run_cli("off").returncode, 2)
        result = self.run_cli("off", "--discard-snapshot")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("UNPARSEABLE", result.stdout.upper())
        self._assert_disarmed()

    def test_recovers_the_armed_without_marker_state(self):
        # Plain `off` is a no-op here (no marker); discard is the only exit.
        self.run_cli("on")
        self.marker.unlink()
        noop = self.run_cli("off")
        self.assertEqual(noop.returncode, 0)
        self.assertIn("result=noop", noop.stdout)
        armed = self._read_json(self.local_settings)
        self.assertEqual(armed["permissions"]["defaultMode"], "acceptEdits")

        result = self.run_cli("off", "--discard-snapshot")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self._assert_disarmed()

    def test_discard_preserves_unrelated_keys_and_never_unlinks_the_overlay(self):
        self._write_json(
            self.local_settings,
            {"model": "opus", "permissions": {"allow": ["Bash(ls:*)"]}},
        )
        self.run_cli("on")
        result = self.run_cli("off", "--discard-snapshot")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(
            self.local_settings.exists(),
            "discard removes ONE KEY, never a file",
        )
        data = self._read_json(self.local_settings)
        self.assertEqual(data["model"], "opus")
        self.assertEqual(data["permissions"]["allow"], ["Bash(ls:*)"])
        self.assertNotIn("defaultMode", data["permissions"])

    def test_discard_on_a_created_overlay_leaves_no_default_mode(self):
        self.assertFalse(self.local_settings.exists())
        self.run_cli("on")
        self.assertEqual(self.run_cli("off", "--discard-snapshot").returncode, 0)
        self._assert_disarmed()

    def test_discard_is_fail_closed_on_a_malformed_overlay(self):
        self.run_cli("on")
        garbage = b"{ not json"
        self.local_settings.write_bytes(garbage)
        result = self.run_cli("off", "--discard-snapshot")
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(
            self.local_settings.read_bytes(), garbage,
            "discard must not rewrite an overlay it cannot parse",
        )
        self.assertTrue(self.marker.exists(), "marker left in place")
        self.assertIn("result=refused", result.stdout)

    def test_discard_refuses_under_ci(self):
        self.run_cli("on")
        flipped = self.local_settings.read_bytes()
        with mock.patch.dict(
            os.environ, {"CI": "true", _SEAM_ENV: "1"}, clear=False
        ):
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "off", "--discard-snapshot",
                 "--project-root", str(self.root)],
                capture_output=True, text=True, timeout=30,
                cwd=str(self.project_dir), env=dict(os.environ),
            )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertEqual(self.local_settings.read_bytes(), flipped)
        self.assertIn("result=refused", result.stdout)

    def test_discard_without_marker_or_overlay_is_harmless(self):
        result = self.run_cli("off", "--discard-snapshot")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse(self.local_settings.exists())
        self.assertFalse(self.marker.exists())

    def test_flag_is_rejected_with_on_and_with_status(self):
        on = self.run_cli("on", "--discard-snapshot")
        self.assertEqual(on.returncode, 2, on.stdout + on.stderr)
        self.assertIn("only valid with 'off'", on.stderr)
        self.assertIn("result=refused", on.stdout)
        self.assertFalse(self.local_settings.exists())

        status = self.run_cli("status", "--discard-snapshot")
        self.assertEqual(status.returncode, 2, status.stdout + status.stderr)

    def test_flag_and_recovery_contract_are_documented_in_help(self):
        result = self.run_cli("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--discard-snapshot", result.stdout)
        # The flag's own help text names what it does, and the epilog names
        # it as the sanctioned exit from a refusal (NF-02).
        self.assertIn("prev_value", result.stdout)
        self.assertIn(
            "armed", result.stdout,
            "help must state that a refusal never leaves the posture armed "
            "with no way to disarm it",
        )

    def test_recovery_flag_is_documented_in_the_slash_command(self):
        doc = (REPO_ROOT / ".claude" / "commands" / "night-mode.md").read_text(
            encoding="utf-8"
        )
        self.assertIn("--discard-snapshot", doc)
        troubleshooting = doc.split("## Troubleshooting", 1)
        self.assertEqual(
            len(troubleshooting), 2, "night-mode.md lost its Troubleshooting section"
        )
        self.assertIn(
            "--discard-snapshot", troubleshooting[1],
            "the recovery path must be in the Troubleshooting section — an "
            "operator hitting a fail-closed refusal reads that section, not "
            "the source (NF-02)",
        )


# ---------------------------------------------------------------------------
# NF-05 — cmd_on's success line cannot be used to forge event records
# ---------------------------------------------------------------------------


class NightModeSummaryForgeryTest(_NightModeBase):
    """NF-05 — the overlay's raw prior ``defaultMode`` is untrusted input.

    ``cmd_on``'s success line interpolated it bare (neither
    ``_bounded_repr`` nor ``_summary_token``): a value carrying ``\\n``
    made ONE ``on`` invocation emit TWO ``night-mode-event `` rows — the
    forged one claiming ``result=applied`` — and a 200k-char value
    emitted 200k bytes of stdout. Every assertion here is a LINE COUNT or
    a length bound, because the pre-fix suite only ever asserted
    ``assertIn("night-mode-event", stdout)``, which the forgery passes.
    """

    def _event_lines(self, stdout: str) -> List[str]:
        return [
            line for line in stdout.splitlines()
            if line.startswith("night-mode-event ")
        ]

    def test_newline_in_prior_value_cannot_forge_a_second_event_row(self):
        forged = (
            "plan\nnight-mode-event mode=acceptEdits previous_mode=none "
            "result=applied"
        )
        self._write_json(
            self.local_settings, {"permissions": {"defaultMode": forged}}
        )
        result = self.run_cli("on")
        self.assertEqual(result.returncode, 0, result.stderr)
        events = self._event_lines(result.stdout)
        self.assertEqual(
            len(events), 1,
            "a planted newline in the overlay's defaultMode forged an "
            "extra night-mode-event row (NF-05):\n" + result.stdout,
        )
        # The one real record is the applied summary, token-sanitized.
        self.assertIn("result=applied", events[0])
        # The echo of the prior value is repr-escaped: the payload may
        # appear, but only INSIDE the success line, never at line start.
        for line in result.stdout.splitlines():
            if line.startswith("night-mode-event "):
                continue
            self.assertNotIn(
                "\nnight-mode-event", line,
                "splitlines() cannot yield embedded newlines — harness bug",
            )

    def test_line_separator_variants_cannot_forge_an_event_row(self):
        # str.splitlines() also splits on VT/FF/FS/GS/RS/NEL/LS/PS -- a
        # consumer that splits sees two records even where a raw terminal
        # shows one. repr-escaping neutralizes the whole family. Escapes
        # on purpose: a literal U+2028 in the source is invisible.
        separators = ("\r", "\v", "\f", "\x1c", "\x1d", "\x1e",
                      "\x85", "\u2028", "\u2029")
        for sep in separators:
            if self.marker.exists():
                self.run_cli("off", "--discard-snapshot")
            forged = "plan" + sep + "night-mode-event forged=1 result=applied"
            self._write_json(
                self.local_settings, {"permissions": {"defaultMode": forged}}
            )
            result = self.run_cli("on")
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(
                len(self._event_lines(result.stdout)), 1,
                "separator %r forged an extra event row (NF-05):\n%s"
                % (sep, result.stdout),
            )

    def test_huge_prior_value_is_bounded_on_stdout(self):
        self._write_json(
            self.local_settings,
            {"permissions": {"defaultMode": "x" * 200000}},
        )
        result = self.run_cli("on")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertLess(
            len(result.stdout), 2000,
            "the success line must echo a BOUNDED form of the prior "
            "value, not %d bytes (NF-05)" % len(result.stdout),
        )
        self.assertEqual(len(self._event_lines(result.stdout)), 1)

    def test_clean_on_still_emits_exactly_one_event_row(self):
        # Regression guard for the fix itself: the count-based invariant
        # must hold on the happy path too, not only under attack.
        result = self.run_cli("on")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(self._event_lines(result.stdout)), 1)


# ---------------------------------------------------------------------------
# NF-06 — status validates the marker and cannot be line-forged
# ---------------------------------------------------------------------------


class NightModeStatusMarkerValidationTest(_NightModeBase):
    """NF-06 — status must never bless a marker the writer refuses.

    Pre-fix, ``cmd_status`` never ran ``_validate_marker`` and printed
    ``host=`` / ``ts=`` raw — and ``_validate_marker`` never checked
    those two fields at all. A planted ``hostname`` injected arbitrary
    status lines (a forged ``reconciliation:`` verdict rendered BEFORE
    the true one), and status reported "AGREE — night-mode ON" for the
    very marker ``off`` refuses with exit 2.
    """

    def _plant(self, **fields: Any) -> None:
        marker = self._read_json(self.marker)
        marker.update(fields)
        self._write_json(self.marker, marker)

    def _recon_lines(self, stdout: str) -> List[str]:
        return [
            line for line in stdout.splitlines()
            if line.startswith("reconciliation:")
        ]

    def test_planted_newline_hostname_cannot_forge_a_reconciliation_line(self):
        self.run_cli("on")
        self._plant(
            hostname="host\nreconciliation: AGREE — forged all-clear"
        )
        result = self.run_cli("status")
        self.assertEqual(result.returncode, 0, result.stderr)
        recon = self._recon_lines(result.stdout)
        self.assertEqual(
            len(recon), 1,
            "a planted newline in the marker's hostname forged an extra "
            "reconciliation: line (NF-06):\n" + result.stdout,
        )
        self.assertIn("DISAGREE", recon[0])

    def test_invalid_marker_reads_present_but_invalid_never_agree(self):
        # The marker `off` refuses (planted bypassPermissions) — status
        # must render the SAME verdict class, not bless it.
        self.run_cli("on")
        self._plant(prev_present=True, prev_value="bypassPermissions")
        off = self.run_cli("off")
        self.assertEqual(off.returncode, 2, "precondition: off must refuse")

        result = self.run_cli("status")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PRESENT but INVALID", result.stdout)
        self.assertIn("prev_value", result.stdout,
                      "the verdict must name the offending field")
        for line in result.stdout.splitlines():
            if "AGREE" in line:
                self.assertIn(
                    "DISAGREE", line,
                    "status blessed a marker off refuses with exit 2 "
                    "(NF-06): " + line,
                )

    def test_tampered_hostname_is_refused_by_off_and_flagged_by_status(self):
        # Writer/reporter agreement in the other direction: the field
        # status renders is also a field off refuses.
        self.run_cli("on")
        self._plant(hostname="a\rb")
        off = self.run_cli("off")
        self.assertEqual(off.returncode, 2, off.stdout + off.stderr)
        self.assertIn("hostname", off.stderr)
        status = self.run_cli("status")
        self.assertIn("PRESENT but INVALID", status.stdout)
        self.assertEqual(len(self._recon_lines(status.stdout)), 1)

    def test_healthy_marker_still_agrees_with_one_reconciliation_line(self):
        self.run_cli("on")
        result = self.run_cli("status")
        self.assertEqual(result.returncode, 0, result.stderr)
        recon = self._recon_lines(result.stdout)
        self.assertEqual(len(recon), 1)
        self.assertIn("AGREE", recon[0])
        self.assertNotIn("DISAGREE", recon[0])
        self.assertNotIn("INVALID", result.stdout)

    def test_validate_marker_gates_ts_and_hostname(self):
        # Unit-level: the whole-document validator now covers the two
        # fields round-3 never looked at (type, bound, control chars,
        # presence).
        mod = _load_module()
        self.run_cli("on")
        healthy = self._read_json(self.marker)
        self.assertIsNone(mod._validate_marker(healthy))

        bad_cases = [
            ("ts", 123),
            ("ts", ""),
            ("ts", "x" * 33),
            ("ts", "2026-08-02T23:00:00Z\nfake"),
            ("hostname", None),
            ("hostname", "h" * 254),
            ("hostname", "a\rb"),
            ("hostname", "a\tb"),
        ]
        for field, value in bad_cases:
            doc = dict(healthy)
            doc[field] = value
            diag = mod._validate_marker(doc)
            self.assertIsNotNone(
                diag, "%s=%r must be rejected (NF-06)" % (field, value)
            )
            self.assertIn(field, diag)
        for field in ("ts", "hostname"):
            doc = dict(healthy)
            doc.pop(field)
            diag = mod._validate_marker(doc)
            self.assertIsNotNone(diag, field + " missing must be rejected")
            self.assertIn(field, diag)


# ---------------------------------------------------------------------------
# NF-04 — STRUCTURAL oracle for the one-record-per-terminating-path rule
# ---------------------------------------------------------------------------

# The terminal-record helpers that must sit immediately before every
# `return` in the toggle commands: the NM-05 operator-facing summary line
# AND the NF-07 forensic `night_mode_toggled` emit. Both, always, as a pair
# — the round-3 re-review found the emit registered in `_KNOWN_ACTIONS`,
# SPEC'd and documented in three signed surfaces with ZERO production
# callers, and required the oracle to pin the PAIR precisely so the next
# regression cannot be silent.
_TERMINAL_HELPERS = ("_summary", "_emit_audit")

# Functions the rule applies to. `status` is deliberately absent (read-only,
# not a toggle, must never emit).
_TERMINAL_PATH_FUNCTIONS = ("cmd_on", "cmd_off", "cmd_off_discard_snapshot")

# `main()` is NOT in the tuple above: most of its returns are dispatch
# returns (`return cmd_on(root)`), where the record belongs to the callee.
# Its RECORD-bearing paths — the three pre-dispatch fail-closed refusals
# (NF-08b self-path, `--discard-snapshot` misuse, NM-04 root confinement)
# and the catch-all — are pinned separately by
# `NightModeMainRecordPairingTest`, which walks the whole module.
#
# 3 -> 4 when the NF-08b alias guard landed. Bumping this number is the
# INTENDED cost of adding a refusal path: the pin exists so that a new
# terminating path cannot be wired to one record helper and not the other.
_MAIN_RECORD_PATHS = 4


def _called_helper_name(stmt: ast.stmt) -> Optional[str]:
    """Name of the function called by a bare expression statement, or None."""
    if not isinstance(stmt, ast.Expr):
        return None
    call = stmt.value
    if not isinstance(call, ast.Call):
        return None
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def _statement_lists(node: ast.AST) -> List[List[ast.stmt]]:
    """Every statement LIST reachable under *node* (bodies, else, handlers)."""
    out: List[List[ast.stmt]] = []
    for child in ast.walk(node):
        for _field, value in ast.iter_fields(child):
            if (
                isinstance(value, list)
                and value
                and all(isinstance(item, ast.stmt) for item in value)
            ):
                out.append(value)
    return out


class NightModeTerminalPathOracleTest(_NightModeBase):
    """NF-04/NF-07 — the two-records-per-terminating-path rule needs an ORACLE.

    The requirement is forensic: every terminating path of ``on``/``off``
    leaves exactly one machine-readable summary line AND exactly one
    ``night_mode_toggled`` audit row (``ceremony-staged/README.md`` §"P2
    emit re-insertion": "every ``return`` statement is immediately preceded
    by exactly one ``_emit_audit(...)`` call"). Until the round-3 re-review
    that requirement lived ONLY as prose in a ceremony README — a ceremony
    executor (or a later refactor) could wire the record into just the happy
    path and every behavioural test would still pass, because no test
    enumerates the paths.

    NF-07 is what that gap actually produced: the action shipped
    registered, SPEC'd and documented across three signed surfaces with
    ZERO production callers, and both existing gates
    (``check-audit-registry-coverage.py``, ``verify-counts``) stayed green
    over the hole because they compare NAMES and COUNTS, never liveness.
    So the oracle now pins the PAIR — dropping either helper from any path
    is a test failure, not a silent regression.

    Structural by construction: it parses ``night-mode.py`` with ``ast``
    and asserts the invariant on the syntax tree, path by path, including
    paths no behavioural test reaches.
    """

    def _tree(self) -> ast.Module:
        return ast.parse(SCRIPT.read_text(encoding="utf-8"), filename=str(SCRIPT))

    def _functions(self) -> Dict[str, ast.FunctionDef]:
        found: Dict[str, ast.FunctionDef] = {}
        for node in ast.walk(self._tree()):
            if isinstance(node, ast.FunctionDef) and node.name in _TERMINAL_PATH_FUNCTIONS:
                found[node.name] = node
        return found

    def test_all_toggle_commands_are_present(self):
        found = self._functions()
        self.assertEqual(
            sorted(found), sorted(_TERMINAL_PATH_FUNCTIONS),
            "a toggle command was renamed or removed — the oracle must "
            "cover every function that can terminate a toggle",
        )

    def test_every_return_is_immediately_preceded_by_the_terminal_helpers(self):
        width = len(_TERMINAL_HELPERS)
        expected = sorted(_TERMINAL_HELPERS)
        total_returns = 0
        for name, func in sorted(self._functions().items()):
            for stmts in _statement_lists(func):
                for index, stmt in enumerate(stmts):
                    if not isinstance(stmt, ast.Return):
                        continue
                    total_returns += 1
                    self.assertGreaterEqual(
                        index, width,
                        "%s: return at line %d has no room for the terminal "
                        "record helper(s) %s before it"
                        % (name, stmt.lineno, expected),
                    )
                    window = stmts[index - width:index]
                    got = sorted(
                        n for n in (_called_helper_name(s) for s in window)
                        if n is not None
                    )
                    self.assertEqual(
                        got, expected,
                        "%s: the return at line %d is not immediately "
                        "preceded by exactly one call to each of %s (found "
                        "%s) — every terminating path must leave exactly one "
                        "record (NM-05 / NF-04)"
                        % (name, stmt.lineno, expected, got),
                    )
        self.assertGreater(
            total_returns, 10,
            "the oracle found suspiciously few terminating paths — it is "
            "probably not walking the tree it thinks it is",
        )

    def test_each_helper_is_called_exactly_once_per_terminating_path(self):
        # Companion assertion (extends to _emit_audit for free): a path may
        # not emit twice, and no helper call may sit anywhere else.
        for name, func in sorted(self._functions().items()):
            returns = sum(
                1 for node in ast.walk(func) if isinstance(node, ast.Return)
            )
            for helper in _TERMINAL_HELPERS:
                calls = 0
                for node in ast.walk(func):
                    if not isinstance(node, ast.Call):
                        continue
                    target = node.func
                    got = (
                        target.id if isinstance(target, ast.Name)
                        else target.attr if isinstance(target, ast.Attribute)
                        else None
                    )
                    if got == helper:
                        calls += 1
                self.assertEqual(
                    calls, returns,
                    "%s calls %s() %d time(s) for %d terminating path(s) — "
                    "exactly one record per path, never two, never zero"
                    % (name, helper, calls, returns),
                )

    def test_status_never_emits_a_toggle_record(self):
        for node in ast.walk(self._tree()):
            if isinstance(node, ast.FunctionDef) and node.name == "cmd_status":
                for helper in _TERMINAL_HELPERS:
                    names = [
                        n.func.id for n in ast.walk(node)
                        if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                    ]
                    self.assertNotIn(
                        helper, names,
                        "status is read-only and must never emit a toggle "
                        "record",
                    )
                return
        self.fail("cmd_status not found")


class NightModeMainRecordPairingTest(_NightModeBase):
    """NF-07 — the pair rule, asserted MODULE-WIDE rather than per function.

    ``NightModeTerminalPathOracleTest`` walks the three toggle commands. It
    cannot walk ``main()``: most of ``main``'s returns are DISPATCH returns
    (``return cmd_on(root)``) where the record belongs to the callee, so a
    "record before every return" rule is simply false there. Yet ``main``
    owns three record-bearing terminating paths of its own — the two
    pre-dispatch fail-closed refusals (bad ``--discard-snapshot`` pairing,
    NM-04 root confinement) and the catch-all — and the signed SPEC row
    claims a ``night_mode_toggled`` on EVERY terminating path of
    ``on``/``off``, those three included.

    So the invariant asserted here is the one that actually generalises:
    wherever the module writes ONE of the two records, it writes the OTHER
    one immediately after. That covers ``main`` today and any function a
    later change adds, without needing a hand-maintained function list.
    """

    def _module_statement_lists(self) -> List[List[ast.stmt]]:
        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"), filename=str(SCRIPT))
        return _statement_lists(tree)

    def test_summary_and_emit_are_always_adjacent_siblings(self):
        pairs = 0
        for stmts in self._module_statement_lists():
            for index, stmt in enumerate(stmts):
                name = _called_helper_name(stmt)
                if name == "_summary":
                    following = (
                        _called_helper_name(stmts[index + 1])
                        if index + 1 < len(stmts) else None
                    )
                    self.assertEqual(
                        following, "_emit_audit",
                        "the _summary at line %d is not immediately followed "
                        "by _emit_audit (found %r) — the operator record and "
                        "the forensic record must travel as a pair on every "
                        "terminating path (NF-07)"
                        % (stmt.lineno, following),
                    )
                    pairs += 1
                elif name == "_emit_audit":
                    preceding = (
                        _called_helper_name(stmts[index - 1])
                        if index >= 1 else None
                    )
                    self.assertEqual(
                        preceding, "_summary",
                        "the _emit_audit at line %d is not immediately "
                        "preceded by _summary (found %r) — an audit row with "
                        "no operator line means one of the two records was "
                        "wired to a path the other one is not on"
                        % (stmt.lineno, preceding),
                    )
        self.assertGreater(
            pairs, 25,
            "the module-wide walk found suspiciously few record pairs — it "
            "is probably not walking the tree it thinks it is",
        )

    def test_main_owns_exactly_the_expected_record_paths(self):
        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"), filename=str(SCRIPT))
        main = next(
            (n for n in ast.walk(tree)
             if isinstance(n, ast.FunctionDef) and n.name == "main"),
            None,
        )
        self.assertIsNotNone(main, "main() not found")
        for helper in _TERMINAL_HELPERS:
            calls = sum(
                1 for n in ast.walk(main)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
                and n.func.id == helper
            )
            self.assertEqual(
                calls, _MAIN_RECORD_PATHS,
                "main() calls %s() %d time(s); expected %d — the three "
                "pre-dispatch refusals and the catch-all. A new "
                "record-bearing path in main must add BOTH helpers (and this "
                "pin), never one" % (helper, calls, _MAIN_RECORD_PATHS),
            )

    def test_the_catch_all_handler_emits_both_records_once(self):
        tree = ast.parse(SCRIPT.read_text(encoding="utf-8"), filename=str(SCRIPT))
        main = next(
            n for n in ast.walk(tree)
            if isinstance(n, ast.FunctionDef) and n.name == "main"
        )
        handlers = [n for n in ast.walk(main) if isinstance(n, ast.ExceptHandler)]
        self.assertTrue(handlers, "main() has no catch-all handler")
        found = False
        for handler in handlers:
            names = [
                n.func.id for n in ast.walk(handler)
                if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
            ]
            if "_summary" in names or "_emit_audit" in names:
                found = True
                for helper in _TERMINAL_HELPERS:
                    self.assertEqual(
                        names.count(helper), 1,
                        "the catch-all must leave exactly one %s record — an "
                        "internal error is the path most likely to be the "
                        "only witness of a half-applied toggle" % helper,
                    )
        self.assertTrue(
            found,
            "no exception handler in main() leaves a record — an internal "
            "error would flip nothing but also witness nothing",
        )


# ---------------------------------------------------------------------------
# NF-07 — the forensic row actually lands (AC-7), and never blocks the toggle
# ---------------------------------------------------------------------------


class NightModeAuditRowTest(_NightModeBase):
    """AC-7 behaviourally: `on` and `off` leave `night_mode_toggled` rows.

    The round-3 re-review's NF-07 is precisely the failure this class would
    have caught: action registered, SPEC row signed, three surfaces claiming
    the emit, and no caller. ``check-audit-registry-coverage.py`` stayed
    green over it because it reconciles NAMES, not LIVENESS. So the assertion
    here is on the LOG, not on the source.

    The audit sink is the isolated one TestEnvContext pins
    (``CEO_AUDIT_LOG_*`` + ``HOME`` under this test's tmp tree, sync mode on),
    inherited by the child through ``_subprocess_env`` — no test writes to
    the real chain.
    """

    def _rows(self) -> List[Dict[str, Any]]:
        log = Path(self.audit_dir) / "audit-log.jsonl"
        if not log.is_file():
            return []
        rows: List[Dict[str, Any]] = []
        for line in log.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if isinstance(event, dict) and event.get("action") == "night_mode_toggled":
                rows.append(event)
        return rows

    def test_on_then_off_each_leave_exactly_one_row(self):
        on = self.run_cli("on")
        self.assertEqual(on.returncode, 0, on.stdout + on.stderr)
        rows = self._rows()
        self.assertEqual(
            len(rows), 1,
            "`on` must leave exactly one night_mode_toggled row (AC-7); "
            "got %d" % len(rows),
        )
        self.assertEqual(rows[0].get("mode"), "acceptEdits")
        self.assertEqual(rows[0].get("previous_mode"), "absent")
        self.assertEqual(rows[0].get("result"), "applied")

        off = self.run_cli("off")
        self.assertEqual(off.returncode, 0, off.stdout + off.stderr)
        rows = self._rows()
        self.assertEqual(len(rows), 2, "`off` must leave a second row (AC-7)")
        self.assertEqual(rows[1].get("mode"), "absent")
        self.assertEqual(rows[1].get("previous_mode"), "acceptEdits")
        self.assertEqual(rows[1].get("result"), "applied")

    def test_status_leaves_no_row(self):
        self.run_cli("on")
        before = len(self._rows())
        status = self.run_cli("status")
        self.assertEqual(status.returncode, 0, status.stdout + status.stderr)
        self.assertEqual(
            len(self._rows()), before,
            "status is read-only — it must never write a toggle row",
        )

    def test_refused_and_noop_paths_are_recorded_too(self):
        # Malformed overlay -> fail-closed refusal (exit 2).
        self.local_settings.parent.mkdir(parents=True, exist_ok=True)
        self.local_settings.write_bytes(b"not json")
        refused = self.run_cli("on")
        self.assertEqual(refused.returncode, 2)
        rows = self._rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0].get("result"), "refused")

        # `off` with no marker -> idempotent no-op (exit 0).
        self.local_settings.unlink()
        noop = self.run_cli("off")
        self.assertEqual(noop.returncode, 0, noop.stdout + noop.stderr)
        rows = self._rows()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[1].get("result"), "noop")

    def test_row_carries_only_the_allowlisted_fields(self):
        self.run_cli("on")
        rows = self._rows()
        self.assertEqual(len(rows), 1)
        row = rows[0]
        # Sec MF-3: never a path, never file content, never the raw hostname.
        for forbidden in (
            "settings_path", "marker_path", "path", "content", "hostname",
            "prev_value", "overlay",
        ):
            self.assertNotIn(
                forbidden, row,
                "%r reached the wire — the night_mode_toggled allowlist is "
                "deny-by-default for exactly this reason" % forbidden,
            )
        self.assertNotIn(
            socket.gethostname(), json.dumps(row),
            "the RAW hostname must never appear in the row (only the "
            "12-hex sha256 prefix)",
        )
        self.assertRegex(str(row.get("hostname_hash", "")), r"^[0-9a-f]{12}$")

    def test_lock_contention_records_refused_not_failed(self):
        """The catch-all's result mapping, proven with a REAL second holder.

        A same-process ``flock`` re-acquire does not contend (S281 lesson),
        so the lock is held HERE and the toggle runs in a CHILD process. The
        ceremony's result table maps exit 2 — lock contention included — to
        `refused`; `failed` is reserved for exit 1, a write that was
        attempted and lost (NF-11(b)).
        """
        from _lib.filelock import FileLock  # noqa: E402

        lock = self.root / ".claude" / "state" / "night-mode.lock"
        lock.parent.mkdir(parents=True, exist_ok=True)
        with FileLock(str(lock)):
            result = self.run_cli("on")
        self.assertEqual(
            result.returncode, 2,
            "lock contention must exit 2:\n" + result.stdout + result.stderr,
        )
        self.assertIn("result=refused", result.stdout)
        self.assertFalse(
            self.local_settings.exists(),
            "a refused toggle must not have written the overlay",
        )
        rows = self._rows()
        self.assertEqual(len(rows), 1, "the catch-all must still leave a row")
        self.assertEqual(
            rows[0].get("result"), "refused",
            "lock contention is a refusal, not a failure — the two records "
            "and the exit code must agree (NF-09 lesson, NF-11(b) mapping)",
        )


class NightModeAuditFailOpenTest(_NightModeBase):
    """Observability is INFRASTRUCTURE: it may go dark, never block.

    Repo doctrine is fail-CLOSED on input and fail-OPEN on infrastructure.
    An audit sink that raises must cost the Owner a forensic row, never the
    ability to disarm a posture.
    """

    def test_emit_audit_swallows_a_raising_sink(self):
        mod = _load_module()
        from _lib import audit_emit  # noqa: E402

        with mock.patch.object(
            audit_emit, "emit_night_mode_toggled",
            side_effect=RuntimeError("sink exploded"),
        ):
            mod._emit_audit("acceptEdits", "absent", "applied")  # must not raise

    def test_a_raising_sink_does_not_break_the_toggle(self):
        mod = _load_module()
        from _lib import audit_emit  # noqa: E402

        with mock.patch.object(
            audit_emit, "emit_night_mode_toggled",
            side_effect=RuntimeError("sink exploded"),
        ):
            rc, out, err = self.run_inproc(
                mod, ["on", "--project-root", str(self.root)]
            )
        self.assertEqual(rc, 0, err)
        self.assertIn("result=applied", out)
        self.assertEqual(
            self._read_json(self.local_settings)["permissions"]["defaultMode"],
            "acceptEdits",
            "a dead audit sink must not stop the posture write",
        )


# ---------------------------------------------------------------------------
# NF-09 — `off` when the overlay was removed by hand: nothing written, so
#         nothing may be claimed
# ---------------------------------------------------------------------------


class NightModeOverlayGoneRouteTest(_NightModeBase):
    """NF-09 — the no-write route must not report a restore.

    Before the fix this route printed a stderr warning ("is gone; nothing to
    restore") and then fell through to the shared tail, which announced
    ``restored to 'plan' (snapshot)`` and recorded ``mode=plan
    result=applied`` — while ``settings.local.json`` did not exist and the
    next session would resolve the PROJECT layer's ``manual``. The stderr
    line corrected an attentive human; the structured record, which is what
    a parser reads and what NF-07 now HMAC-signs, stayed false.
    """

    def _arm_with_prior_value(self) -> None:
        self._write_json(
            self.local_settings,
            {"permissions": {"defaultMode": "plan"}, "env": {"KEEP": "me"}},
        )
        result = self.run_cli("on")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(self.marker.is_file(), "arming failed")

    def test_off_reports_noop_and_absent_and_writes_nothing(self):
        self._arm_with_prior_value()
        self.local_settings.unlink()  # hand cleanup between `on` and `off`

        result = self.run_cli("off")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(
            "night-mode-event mode=absent previous_mode=acceptEdits "
            "result=noop",
            result.stdout,
            "the machine record must say nothing was restored",
        )
        self.assertNotIn("result=applied", result.stdout)
        self.assertNotIn(
            "restored to", result.stdout,
            "the human line must not claim a restore that never happened",
        )
        self.assertNotIn(
            "'plan'", result.stdout,
            "the snapshot value must not be named as restored — it was not "
            "written anywhere",
        )
        self.assertFalse(
            self.local_settings.exists(),
            "this route writes NOTHING: `off` must not resurrect an overlay "
            "the Owner deleted",
        )
        self.assertFalse(
            self.marker.exists(), "the marker must still be removed",
        )

    def test_the_audit_row_matches_the_no_write_reality(self):
        self._arm_with_prior_value()
        self.local_settings.unlink()
        self.run_cli("off")

        log = Path(self.audit_dir) / "audit-log.jsonl"
        rows = [
            json.loads(line) for line in
            log.read_text(encoding="utf-8").splitlines() if line.strip()
        ]
        toggles = [r for r in rows if r.get("action") == "night_mode_toggled"]
        self.assertEqual(len(toggles), 2, "one row for `on`, one for `off`")
        self.assertEqual(
            toggles[1].get("result"), "noop",
            "with NF-07 wired, an `applied` here would put a restore that "
            "never happened into the HMAC chain — which is why NF-07 and "
            "NF-09 land in one commit",
        )
        self.assertEqual(toggles[1].get("mode"), "absent")

    def test_a_normal_off_still_reports_the_restore(self):
        # Control: the route that DOES write must keep saying so, otherwise
        # the fix above would be indistinguishable from breaking `off`.
        self._arm_with_prior_value()
        result = self.run_cli("off")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("restored to 'plan'", result.stdout)
        self.assertIn(
            "night-mode-event mode=plan previous_mode=acceptEdits "
            "result=applied",
            result.stdout,
        )
        self.assertEqual(
            self._read_json(self.local_settings)["permissions"]["defaultMode"],
            "plan",
        )


class NightModeSelfPathGuardTest(_NightModeBase):
    """NF-08b (codex S292 r2 P1) — refuse to run through an ALIAS.

    `check_bash_safety`'s `_e4` matcher recognises tokens whose SPELLING
    resolves to `.claude/scripts/night-mode.py`. An alias exists precisely
    to have a different spelling, and the bypass was MEASURED before this
    guard, not theorised:

        ln -s <repo>/.claude/scripts/night-mode.py /tmp/nm
        python3 /tmp/nm on        # -> result=applied, overlay written

    It works because `REPO_ROOT = Path(__file__).resolve().parents[2]`
    follows the link back into the repository. Re-probing widened the class:
    a RENAMED COPY inside the repo (`.claude/scripts/nm2.py`) armed the
    posture too, and no rule about `ln` would have caught it.

    So the boundary lives HERE, in the script, where it holds regardless of
    how the alias was created and regardless of whether the hook rail runs
    at all.
    """

    # -- end-to-end: the exact vector from the review --------------------

    def test_symlink_alias_refuses_to_arm(self):
        alias = Path(self.project_dir) / "nm"
        alias.symlink_to(SCRIPT)
        result = subprocess.run(
            [sys.executable, str(alias), "on", "--project-root", str(self.root)],
            capture_output=True, text=True, timeout=30,
            cwd=str(self.project_dir), env=self._subprocess_env(),
        )
        self.assertEqual(
            result.returncode, 2,
            "alias invocation was not refused: %s" % (result.stdout + result.stderr),
        )
        self.assertFalse(
            self.local_settings.exists(),
            "the alias WROTE the posture overlay — NF-08b is not enforced",
        )
        self.assertFalse(self.marker.exists(), "the alias wrote a marker")
        self.assertIn("night-mode.py", result.stderr)

    def test_canonical_invocation_is_the_positive_control(self):
        """The same command through the real path MUST still work.

        Without this, a guard that refused everything would pass the test
        above (S291: a probe that cannot fail proves nothing).
        """
        result = self.run_cli("on")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(self.local_settings.exists())

    def test_refusal_leaves_the_record_pair_for_on(self):
        """A refusal is a terminating path of `on` — NM-05/NF-07 applies."""
        alias = Path(self.project_dir) / "nm"
        alias.symlink_to(SCRIPT)
        result = subprocess.run(
            [sys.executable, str(alias), "on", "--project-root", str(self.root)],
            capture_output=True, text=True, timeout=30,
            cwd=str(self.project_dir), env=self._subprocess_env(),
        )
        self.assertIn("night-mode-event", result.stdout)
        self.assertIn("result=refused", result.stdout)

    def test_status_through_an_alias_is_refused_too(self):
        """The SCRIPT is the surface, matching `_e4`'s scope decision."""
        alias = Path(self.project_dir) / "nm"
        alias.symlink_to(SCRIPT)
        result = subprocess.run(
            [sys.executable, str(alias), "status", "--project-root", str(self.root)],
            capture_output=True, text=True, timeout=30,
            cwd=str(self.project_dir), env=self._subprocess_env(),
        )
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)

    # -- the pure comparison, driven directly ----------------------------
    #
    # The renamed-copy half cannot be probed end-to-end without writing into
    # a real installation, so it is asserted against the pure function. That
    # is also the S285 shape: a fail-closed validator must be testable
    # OUTSIDE the thing it validates.

    def test_diagnostic_accepts_the_canonical_layout(self):
        mod = _load_module()
        real = Path("/repo/.claude/scripts/night-mode.py")
        self.assertIsNone(mod._self_path_diagnostic(real, real))

    def test_diagnostic_rejects_an_alias(self):
        mod = _load_module()
        real = Path("/repo/.claude/scripts/night-mode.py")
        diag = mod._self_path_diagnostic(Path("/tmp/nm"), real)
        self.assertIsNotNone(diag)
        self.assertIn("/tmp/nm", diag)

    def test_diagnostic_rejects_a_renamed_copy_inside_the_repo(self):
        """`cp night-mode.py .claude/scripts/nm2.py` armed the posture."""
        mod = _load_module()
        copy = Path("/repo/.claude/scripts/nm2.py")
        diag = mod._self_path_diagnostic(copy, copy)
        self.assertIsNotNone(diag, "a renamed copy inside the repo was accepted")

    def test_diagnostic_rejects_a_relocated_copy(self):
        mod = _load_module()
        copy = Path("/repo/.claude/hooks/night-mode.py")
        self.assertIsNotNone(mod._self_path_diagnostic(copy, copy))

    def test_diagnostic_tolerates_a_symlinked_ANCESTOR(self):
        """The FP twin, and the reason the parent is resolved separately.

        `/tmp` is a symlink to `/private/tmp` on this platform, and an
        operator whose repo path traverses any symlinked directory must not
        be locked out of their own toggle. Only the FINAL component being a
        link is an alias.
        """
        mod = _load_module()
        real = Path("/private/repo/.claude/scripts/night-mode.py")
        self.assertIsNone(mod._self_path_diagnostic(real, real))

    def test_diagnostic_carries_a_recovery_route(self):
        mod = _load_module()
        real = Path("/repo/.claude/scripts/night-mode.py")
        diag = mod._self_path_diagnostic(Path("/tmp/nm"), real) or ""
        self.assertIn(".claude/scripts/night-mode.py", diag)

    def test_shallow_path_fails_closed_rather_than_raising(self):
        """`parents[2]` on a 2-component path must not become a traceback."""
        mod = _load_module()
        shallow = Path("/nm.py")
        self.assertIsNotNone(mod._self_path_diagnostic(shallow, shallow))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
