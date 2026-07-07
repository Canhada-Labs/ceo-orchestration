"""PLAN-153 Wave B item B6 — build-plugin.py manifest determinism + regen-diff gate.

Covers scripts/build-plugin.py (NOT .claude/scripts/ — the generator lives at
repo-root scripts/):

* deterministic generation of the generator-owned, committed
  ``.claude-plugin/{plugin.json,marketplace.json}`` (sorted keys, trailing
  newline, no timestamps, version flows only from the VERSION argument);
* the ``--check`` regen+diff idempotency gate (skill-inventory pattern from
  validate.yml): rc=0 when the committed files match a fresh regeneration,
  rc=1 with a unified diff on drift or on a missing file;
* end-to-end CLI behavior in a hermetic temp "repo" clone of the script; and
* a live-repo sync smoke (the same assertion CI's ``--check`` step makes),
  so a VERSION bump without regenerated manifests fails here first.

Hermetic: all mutation happens in tempdirs; live-repo tests are read-only.
The script itself reads no env vars; TestEnvContext is used as the base per
the env-hygiene gate (belt-and-braces isolation of env/HOME/sys.path).
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts" / "build-plugin.py"

# Ensure ``_lib.testing`` (TestEnvContext) is importable for env-isolation
# (self-sufficient even outside the conftest's sys.path seeding).
_HOOKS_DIR = REPO / ".claude" / "hooks"
if str(_HOOKS_DIR) not in sys.path:
    sys.path.insert(0, str(_HOOKS_DIR))

from _lib.testing import TestEnvContext  # noqa: E402

_spec = importlib.util.spec_from_file_location("build_plugin", SCRIPT)
build_plugin = importlib.util.module_from_spec(_spec)  # type: ignore[arg-type]
assert _spec.loader is not None
_spec.loader.exec_module(build_plugin)  # type: ignore[union-attr]


class _TmpDirTest(TestEnvContext):
    def setUp(self) -> None:
        super().setUp()
        self.tmp = Path(tempfile.mkdtemp(prefix="ceo-plugin-b6-test-"))

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)
        super().tearDown()


class TestDeterministicGeneration(_TmpDirTest):
    def test_double_generation_byte_identical(self) -> None:
        a, b = self.tmp / "a", self.tmp / "b"
        build_plugin.write_manifest_files(a, "9.9.9")
        build_plugin.write_manifest_files(b, "9.9.9")
        for name in ("plugin.json", "marketplace.json"):
            self.assertEqual((a / name).read_bytes(), (b / name).read_bytes(),
                             f"{name} not byte-stable across runs")

    def test_rewrite_in_place_idempotent(self) -> None:
        dest = self.tmp / "m"
        build_plugin.write_manifest_files(dest, "1.2.3")
        first = {n: (dest / n).read_bytes() for n in ("plugin.json", "marketplace.json")}
        build_plugin.write_manifest_files(dest, "1.2.3")
        for name, blob in first.items():
            self.assertEqual((dest / name).read_bytes(), blob)

    def test_serialization_sorted_keys_and_trailing_newline(self) -> None:
        for builder in (build_plugin.plugin_manifest, build_plugin.marketplace_manifest):
            text = build_plugin.dump_manifest(builder("1.2.3"))
            self.assertTrue(text.endswith("}\n"))
            self.assertEqual(
                text, json.dumps(json.loads(text), indent=2, sort_keys=True) + "\n",
                "dump_manifest must be canonical (indent=2, sort_keys, one trailing NL)")

    def test_no_timestamps_or_dates_in_content(self) -> None:
        dest = self.tmp / "m"
        build_plugin.write_manifest_files(dest, "1.2.3")
        for name in ("plugin.json", "marketplace.json"):
            text = (dest / name).read_text()
            self.assertNotRegex(text, r"20\d\d-\d\d-\d\d", f"date-like token in {name}")
            self.assertNotIn("timestamp", text.lower())

    def test_version_flows_from_argument_only(self) -> None:
        self.assertEqual(build_plugin.plugin_manifest("7.7.7")["version"], "7.7.7")
        mkt = build_plugin.marketplace_manifest("7.7.7")
        self.assertEqual(mkt["plugins"][0]["version"], "7.7.7")
        # semantic identity guard: names stay pinned
        self.assertEqual(build_plugin.plugin_manifest("7.7.7")["name"], "ceo")
        self.assertEqual(mkt["plugins"][0]["source"], "./ceo-plugin")


class TestCheckGate(_TmpDirTest):
    """check_manifests() unit behavior against a synthetic committed dir."""

    def setUp(self) -> None:
        super().setUp()
        self.committed = self.tmp / ".claude-plugin"
        build_plugin.write_manifest_files(self.committed, "3.2.1")

    def _check(self) -> "tuple[int, str]":
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc = build_plugin.check_manifests(self.committed, "3.2.1")
        return rc, buf.getvalue()

    def test_clean_returns_zero(self) -> None:
        rc, out = self._check()
        self.assertEqual(rc, 0, out)
        self.assertIn("in sync", out)

    def test_content_drift_returns_one_with_diff(self) -> None:
        p = self.committed / "plugin.json"
        d = json.loads(p.read_text())
        d["version"] = "0.0.0"
        p.write_text(json.dumps(d, indent=2, sort_keys=True) + "\n")
        rc, out = self._check()
        self.assertEqual(rc, 1)
        self.assertIn("DRIFT", out)
        self.assertIn("plugin.json", out)
        self.assertIn("+++ generated/plugin.json", out)
        self.assertIn('-  "version": "0.0.0"', out)

    def test_key_order_drift_is_drift(self) -> None:
        # hand-edit that keeps JSON-equal content but breaks canonical bytes
        p = self.committed / "marketplace.json"
        p.write_text(json.dumps(json.loads(p.read_text()), indent=2, sort_keys=False))
        rc, out = self._check()
        self.assertEqual(rc, 1, "non-canonical bytes must count as drift")

    def test_missing_file_returns_one(self) -> None:
        (self.committed / "marketplace.json").unlink()
        rc, out = self._check()
        self.assertEqual(rc, 1)
        self.assertIn("missing", out)

    def test_missing_dir_returns_one(self) -> None:
        shutil.rmtree(self.committed)
        rc, _ = self._check()
        self.assertEqual(rc, 1)


class TestCliHermetic(_TmpDirTest):
    """Full argparse surface in a throwaway 'repo' (script copy + VERSION),
    so the CLI drift path is exercised without touching the live tree."""

    def setUp(self) -> None:
        super().setUp()
        (self.tmp / "scripts").mkdir()
        shutil.copy2(SCRIPT, self.tmp / "scripts" / "build-plugin.py")
        (self.tmp / "VERSION").write_text("0.0.9\n")
        self.cli = [sys.executable, str(self.tmp / "scripts" / "build-plugin.py")]

    def _run(self, *args: str) -> "subprocess.CompletedProcess[str]":
        return subprocess.run(self.cli + list(args), capture_output=True, text=True)

    def test_check_before_write_fails_then_roundtrips(self) -> None:
        r = self._run("--check")
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn("missing", r.stdout)
        w = self._run("--write-manifests")
        self.assertEqual(w.returncode, 0, w.stdout + w.stderr)
        manifest = json.loads((self.tmp / ".claude-plugin" / "plugin.json").read_text())
        self.assertEqual(manifest["version"], "0.0.9")
        r2 = self._run("--check")
        self.assertEqual(r2.returncode, 0, r2.stdout + r2.stderr)

    def test_cli_check_detects_planted_drift(self) -> None:
        self._run("--write-manifests")
        p = self.tmp / ".claude-plugin" / "plugin.json"
        p.write_text(p.read_text().replace('"0.0.9"', '"9.0.0"'))
        r = self._run("--check")
        self.assertEqual(r.returncode, 1)
        self.assertIn("DRIFT", r.stdout)

    def test_check_and_write_are_mutually_exclusive(self) -> None:
        r = self._run("--check", "--write-manifests")
        self.assertEqual(r.returncode, 2)  # argparse usage error

    def test_check_mode_writes_nothing(self) -> None:
        self._run("--write-manifests")
        before = sorted(str(p.relative_to(self.tmp)) for p in self.tmp.rglob("*"))
        self._run("--check")
        after = sorted(str(p.relative_to(self.tmp)) for p in self.tmp.rglob("*"))
        self.assertEqual(before, after, "--check must not create/remove files (incl. dist/)")


class TestLiveRepoSync(TestEnvContext):
    """Read-only: the committed .claude-plugin/ must match the generator —
    the exact assertion the CI --check step makes."""

    def test_committed_manifests_in_sync(self) -> None:
        r = subprocess.run([sys.executable, str(SCRIPT), "--check"],
                           capture_output=True, text=True)
        self.assertEqual(
            r.returncode, 0,
            "committed .claude-plugin/ drifted from build-plugin.py — run "
            "`python3 scripts/build-plugin.py --write-manifests` and commit:\n"
            + r.stdout + r.stderr)

    def test_committed_version_matches_VERSION_file(self) -> None:
        version = (REPO / "VERSION").read_text().strip()
        self.assertRegex(version, re.compile(r"^\d+\.\d+\.\d+"))
        plugin = json.loads((REPO / ".claude-plugin" / "plugin.json").read_text())
        market = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text())
        self.assertEqual(plugin["version"], version)
        self.assertEqual(market["plugins"][0]["version"], version)


if __name__ == "__main__":
    unittest.main()
