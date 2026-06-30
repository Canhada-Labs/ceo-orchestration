"""PLAN-085 Wave A install acceptance — yaml glob + tier-policy + protocol rendering.

3-case acceptance harness covering the 4 P0 + 1 P1 surface fixes
shipped by Wave A:

  A.1 — install.sh:install_scripts_selective now globs *.yaml in
        addition to *.sh and *.py (was the silent-drop root cause
        for the cap-table P0).

  A.2 — smart-loading-cap-table.yaml moved from .claude/scripts/ to
        .claude/policies/ (canonical first-run-wizard expectation
        location per PLAN-084 Wave C.4 / R-002).

  A.3 — install.sh now ships templates/.claude/tier-policy.json +
        templates/.claude/tier-policy.json.sigchain to adopter
        .claude/ (was missing entirely — canonical-guard tier
        enforcement was dead at adopter sites).

  A.5 — install.sh:build_sed_script() now substitutes the
        {{PROTOCOL_SOURCE}} placeholder so freshly installed
        PROTOCOL.md pointers don't leak the raw marker.

  A.4 (covered out-of-band) — scripts/install-v2.sh moved to
        .claude/plans/PLAN-083/staging/install-v2.sh; v1.19.0
        ships ONE canonical install: install.sh. Not asserted here
        (negative test would couple to staging path).

Discipline: stdlib-only, Python >= 3.9, from __future__ annotations,
typing.Optional/Union (no PEP 604, no match). No TestEnvContext —
this is a subprocess invocation test, not an env-isolated hook test.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


class TestInstallYamlGlob(unittest.TestCase):
    """3 acceptance tests for PLAN-085 Wave A install surface fixes."""

    def setUp(self) -> None:
        # Each test gets a fresh, empty target directory. install.sh
        # requires the target directory to already exist.
        self.tmpdir = tempfile.mkdtemp(prefix="plan-085-wave-a-")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _run_install(self) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["bash", str(REPO_ROOT / "scripts" / "install.sh"), self.tmpdir],
            capture_output=True,
            text=True,
            timeout=180,
        )

    def test_smart_loading_cap_table_yaml_installed(self) -> None:
        """A.1 + A.2: cap-table ships and lands at canonical policies/ path."""
        result = self._run_install()
        self.assertEqual(
            result.returncode, 0,
            "install.sh failed: stderr={s!r}".format(s=result.stderr),
        )
        cap_table = (
            Path(self.tmpdir) / ".claude" / "policies"
            / "smart-loading-cap-table.yaml"
        )
        self.assertTrue(
            cap_table.is_file(),
            "missing canonical cap-table: {p}".format(p=cap_table),
        )
        # And it must NOT linger at the legacy scripts/ path (which
        # would mean install.sh duplicated it instead of moving).
        legacy = (
            Path(self.tmpdir) / ".claude" / "scripts"
            / "smart-loading-cap-table.yaml"
        )
        self.assertFalse(
            legacy.is_file(),
            "cap-table still at legacy scripts/ path: {p}".format(p=legacy),
        )

    def test_tier_policy_json_installed(self) -> None:
        """A.3: tier-policy.json + .sigchain ship from templates/.claude/."""
        result = self._run_install()
        self.assertEqual(
            result.returncode, 0,
            "install.sh failed: stderr={s!r}".format(s=result.stderr),
        )
        tier_policy = Path(self.tmpdir) / ".claude" / "tier-policy.json"
        sigchain = Path(self.tmpdir) / ".claude" / "tier-policy.json.sigchain"
        self.assertTrue(
            tier_policy.is_file(),
            "missing tier-policy.json: {p}".format(p=tier_policy),
        )
        self.assertTrue(
            sigchain.is_file(),
            "missing tier-policy.json.sigchain: {p}".format(p=sigchain),
        )

    def test_protocol_source_placeholder_substituted(self) -> None:
        """A.5: {{PROTOCOL_SOURCE}} placeholder is substituted in PROTOCOL.md."""
        result = self._run_install()
        self.assertEqual(
            result.returncode, 0,
            "install.sh failed: stderr={s!r}".format(s=result.stderr),
        )
        protocol = Path(self.tmpdir) / "PROTOCOL.md"
        self.assertTrue(
            protocol.is_file(),
            "PROTOCOL.md not created: {p}".format(p=protocol),
        )
        body = protocol.read_text(encoding="utf-8")
        self.assertNotIn(
            "{{PROTOCOL_SOURCE}}", body,
            "PROTOCOL.md still contains {{PROTOCOL_SOURCE}} literal marker:\n"
            + body,
        )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
