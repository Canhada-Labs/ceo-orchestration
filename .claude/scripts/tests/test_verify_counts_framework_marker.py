"""verify-counts.sh — persistent RED control for the framework-version marker
site (PLAN-169-FOLLOWUP AC-7).

The oracle under test is the REAL ``.claude/scripts/local/verify-counts.sh``,
specifically the ``.claude/.framework-version`` entry of its ``VERSION_SITES``
list (added by PLAN-169 W2.6: the updater reads the marker marker-first, so a
GA that bumps ``VERSION`` and forgets the marker leaves every adopter looping
"behind-minor" — the desync must be RED here, fail-closed).

Why this file exists
--------------------
The W2.6 evidence for that site was a TRANSIENT control: plant the marker at a
wrong version in the live tree, observe ``rc=1`` naming the site, restore,
observe ``rc=0``, un-plant in the same commit. Nothing was left behind that a
later change to ``verify-counts.sh`` could be re-run against. This file is the
re-executable form of the red leg, plus the green leg on the same tree.

Two oracles that do NOT serve, and why
--------------------------------------
* ``STUB_VERIFY_COUNTS`` (the ``synth`` fixture of ``test_release_bump_sites.py``)
  is a 30-line stand-in that implements ``marker == VERSION`` itself. A control
  planted against it would stay green after the real ``VERSION_SITES`` entry
  was deleted — it tests the stub, not the oracle (fixture != live).
* The live ``.claude/.framework-version``. This test NEVER plants there: every
  run points the script at a throwaway tree through ``VERIFY_COUNTS_ROOT`` (the
  mold of ``test_verify_counts_remediation.py``), asserts that tree is outside
  the repository, and tripwires the live marker's bytes across the class.

The clean tree comes from the mold's own ``_scaffold`` — the exact tree that
file proves GREEN for every other gate — so the ONLY variable between a green
and a red run below is the marker.

What is pinned
--------------
  1. synced marker             -> rc 0, no violation, and the site was actually
                                  consulted (``rule_matches`` == 1) — a green
                                  that skipped the site proves nothing;
  2. same tree, marker desynced then re-synced -> rc 1 then rc 0 (the
                                  red -> green flip with a single variable);
  3. every desync direction    -> rc 1, EXACTLY one violation, naming the site
                                  and both versions (patch/minor/major, ahead and
                                  behind, and "bump forgot the marker");
  4. a marker that does not parse (empty, text, pre-release, ``v`` prefix) -> rc 1
                                  as "dead release gate", never skipped.

Not pinned (deliberately): an ABSENT marker file. The oracle skips a version
site whose file does not exist in the tree (synthetic fixtures ship a subset of
the docs by design); pinning that here would freeze a behaviour this control is
not about.

stdlib-only; Python >= 3.9. Env-isolated via TestEnvContext.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parents[3]
_HOOKS_DIR = REPO_ROOT / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

SCRIPT = REPO_ROOT / ".claude" / "scripts" / "local" / "verify-counts.sh"
LIVE_MARKER = REPO_ROOT / ".claude" / ".framework-version"
_MOLD = REPO_ROOT / ".claude" / "scripts" / "tests" / "test_verify_counts_remediation.py"

MARKER_REL = ".claude/.framework-version"
# Key under which the oracle counts how many times the site's regex matched
# (``"version:" + doc + ":" + mode`` in verify-counts.sh). 1 == the site was
# read and parsed; 0 == it was skipped or dead.
MARKER_RULE_KEY = "version:%s:full" % MARKER_REL


def _load_scaffold():
    """Load ``_scaffold`` from the mold by path (no sys.path / package games).

    Fails LOUD if the mold moved or changed shape — a silent fallback to a
    private copy of the tree builder is how a control drifts from the oracle
    it is meant to guard.
    """
    spec = importlib.util.spec_from_file_location("_vc_remediation_mold", _MOLD)
    if spec is None or spec.loader is None:
        raise ImportError("cannot load the mold at %s" % _MOLD)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    scaffold = getattr(module, "_scaffold", None)
    if not callable(scaffold):
        raise ImportError("mold %s no longer exposes a callable _scaffold" % _MOLD)
    return scaffold


_scaffold = _load_scaffold()


def _is_within(child: Path, parent: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _read_live_marker() -> Optional[bytes]:
    try:
        return LIVE_MARKER.read_bytes()
    except OSError:
        return None


class TestFrameworkMarkerSiteControl(TestEnvContext):
    """Red/green controls for the ``.claude/.framework-version`` version site."""

    _live_marker_before: Optional[bytes] = None

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        if not SCRIPT.is_file():
            raise AssertionError("the oracle is missing: %s" % SCRIPT)
        cls._live_marker_before = _read_live_marker()

    @classmethod
    def tearDownClass(cls) -> None:
        after = _read_live_marker()
        super().tearDownClass()
        if after != cls._live_marker_before:
            raise AssertionError(
                "the LIVE %s changed while this class ran (before=%r after=%r): "
                "a control must never plant in the live marker"
                % (MARKER_REL, cls._live_marker_before, after)
            )

    # ---- helpers ---------------------------------------------------------

    def _tree(self, version: str, marker: Optional[str]) -> Path:
        """Throwaway tree whose every version site reads ``version``, plus a
        marker file holding ``marker`` (None = leave the marker file absent)."""
        root = Path(tempfile.mkdtemp(prefix="vc-marker-", dir=str(self._tmp_root)))
        self.assertFalse(
            _is_within(root, REPO_ROOT),
            "the control tree must live outside the repository: %s" % root,
        )
        _scaffold(root, version=version)
        if marker is not None:
            self._write_marker(root, marker)
        return root

    @staticmethod
    def _write_marker(root: Path, content: str) -> None:
        marker = root / ".claude" / ".framework-version"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(content, encoding="utf-8")

    def _oracle(self, root: Path) -> Tuple[int, Dict[str, Any]]:
        """Run the REAL script over ``root``; return (rc, parsed --json report)."""
        env = os.environ.copy()
        env["VERIFY_COUNTS_ROOT"] = str(root)
        proc = subprocess.run(
            ["bash", str(SCRIPT), "--no-tests", "--json"],
            capture_output=True,
            text=True,
            timeout=120,
            env=env,
        )
        try:
            report = json.loads(proc.stdout)
        except ValueError:
            self.fail(
                "verify-counts.sh --json did not emit JSON (rc=%s)\nstdout=%s\nstderr=%s"
                % (proc.returncode, proc.stdout[-600:], proc.stderr[-600:])
            )
        return proc.returncode, report

    def _marker_hits(self, report: Dict[str, Any]) -> Optional[int]:
        return report.get("rule_matches", {}).get(MARKER_RULE_KEY)

    # ---- (1) green leg: synced marker ------------------------------------

    def test_synced_marker_is_green_and_the_site_was_consulted(self) -> None:
        root = self._tree("9.9.9", "9.9.9\n")
        rc, report = self._oracle(root)
        self.assertEqual(rc, 0, "synced tree must be green: %s" % report["violations"])
        self.assertEqual(report["violations"], [])
        self.assertEqual(
            self._marker_hits(report),
            1,
            "a green that never matched the marker site proves nothing "
            "(rule_matches=%r)" % report.get("rule_matches"),
        )

    # ---- (2) the red -> green flip, single variable ----------------------

    def test_desync_then_resync_on_the_same_tree_flips_red_to_green(self) -> None:
        root = self._tree("9.9.9", "9.9.8\n")  # only the marker disagrees

        rc, report = self._oracle(root)
        self.assertEqual(rc, 1, "desynced marker must be RED: %s" % report["violations"])
        self.assertTrue(
            any(v.startswith(MARKER_REL + ":") for v in report["violations"]),
            "the red must name the marker site: %r" % report["violations"],
        )

        self._write_marker(root, "9.9.9\n")  # restore the single variable
        rc, report = self._oracle(root)
        self.assertEqual(rc, 0, "re-synced marker must be GREEN: %s" % report["violations"])
        self.assertEqual(report["violations"], [])

    # ---- (3) every desync direction is red, and only this site -----------

    def test_every_desync_direction_is_red_naming_only_the_marker_site(self) -> None:
        cases: List[Tuple[str, str, str]] = [
            # (live VERSION, marker, what happened)
            ("9.9.9", "9.9.8", "marker one patch behind"),
            ("9.9.9", "9.9.10", "marker ahead of VERSION"),
            ("9.9.9", "9.8.9", "marker one minor behind"),
            ("9.9.9", "8.9.9", "marker one major behind"),
            ("9.9.10", "9.9.9", "bump moved every site except the marker"),
        ]
        for live, marker, why in cases:
            root = self._tree(live, marker + "\n")
            rc, report = self._oracle(root)
            label = "%s (VERSION=%s marker=%s)" % (why, live, marker)
            self.assertEqual(rc, 1, "%s must be RED" % label)
            violations = report["violations"]
            self.assertEqual(
                len(violations),
                1,
                "%s must trip EXACTLY the marker site, got %r" % (label, violations),
            )
            line = violations[0]
            self.assertTrue(line.startswith(MARKER_REL + ":"), "%s: %r" % (label, line))
            self.assertIn("cites version=%s" % marker, line, label)
            self.assertIn("live VERSION=%s" % live, line, label)
            self.assertIn("(rule: exact)", line, label)
            self.assertEqual(self._marker_hits(report), 1, label)

    # ---- (4) a marker that does not parse is a dead gate, not a skip -----

    def test_unparseable_marker_is_red_as_a_dead_release_gate(self) -> None:
        contents: List[Tuple[str, str]] = [
            ("", "empty file (truncated marker)"),
            ("garbage\n", "text"),
            ("9.9.9-rc.1\n", "pre-release suffix"),
            ("v9.9.9\n", "v prefix"),
            ("9.9\n", "two components"),
        ]
        for content, why in contents:
            root = self._tree("9.9.9", content)
            rc, report = self._oracle(root)
            label = "%s (marker=%r)" % (why, content)
            self.assertEqual(rc, 1, "%s must be RED" % label)
            violations = report["violations"]
            self.assertEqual(len(violations), 1, "%s: %r" % (label, violations))
            self.assertTrue(violations[0].startswith(MARKER_REL + ":"), label)
            self.assertIn("rule: version-liveness", violations[0], label)
            self.assertEqual(self._marker_hits(report), 0, label)


if __name__ == "__main__":
    unittest.main()
