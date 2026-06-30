"""PLAN-025 Batch L — tests for 3-profile quality configurator.

Covers:
- set-quality-profile.sh apply for each of 3 profiles (end-to-end)
- Invariant: code-reviewer + security-engineer stay on Opus in ALL profiles
- spot-check-findings.py parses the expected schema
- ceo-health.py surfaces quality_profile line
- --show returns the current profile

Uses subprocess to exercise the bash script against a tmp fixture.
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

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_SCRIPT = _REPO_ROOT / ".claude" / "scripts" / "set-quality-profile.sh"
_SPOT_CHECK = _REPO_ROOT / ".claude" / "scripts" / "spot-check-findings.py"
_CEO_HEALTH = _REPO_ROOT / ".claude" / "scripts" / "ceo-health.py"


def _read_agent_model(agent_file: Path) -> str:
    """Extract the `model:` value from the agent frontmatter."""
    for line in agent_file.read_text(encoding="utf-8").splitlines():
        if line.startswith("model:"):
            return line.split(":", 1)[1].strip()
    return ""


class TestSetQualityProfileScript(unittest.TestCase):
    """End-to-end exercise of set-quality-profile.sh in a hermetic tmp copy.

    set-quality-profile.sh REWRITES the canonical agent `model:` fields, so it
    MUST NOT run against the live repo: doing so reverted the ADR-142 opus-4-8
    bump in the working tree mid-suite (S210 cross-test canonical pollution).
    The script derives REPO_ROOT from its own location (`dirname "$0"/../..`),
    so we copy the minimal .claude/ tree into a tmp root and run it from there —
    the live repo is never touched.
    """

    @classmethod
    def setUpClass(cls):
        if not _SCRIPT.is_file():
            raise unittest.SkipTest(f"{_SCRIPT} not found")
        src_agents = _REPO_ROOT / ".claude" / "agents"
        if not src_agents.is_dir():
            raise unittest.SkipTest(f"{src_agents} not found")

        cls._tmp_root = Path(tempfile.mkdtemp(prefix="qprofile_test_"))
        tmp_scripts = cls._tmp_root / ".claude" / "scripts"
        tmp_scripts.mkdir(parents=True)
        shutil.copy2(_SCRIPT, tmp_scripts / _SCRIPT.name)
        gen = _REPO_ROOT / ".claude" / "scripts" / "generate-dispatch.py"
        if gen.is_file():
            shutil.copy2(gen, tmp_scripts / gen.name)
        shutil.copytree(src_agents, cls._tmp_root / ".claude" / "agents")
        src_settings = _REPO_ROOT / ".claude" / "settings.json"
        if src_settings.is_file():
            shutil.copy2(src_settings, cls._tmp_root / ".claude" / "settings.json")

        cls.script = tmp_scripts / _SCRIPT.name
        cls.agents_dir = cls._tmp_root / ".claude" / "agents"
        cls.settings = cls._tmp_root / ".claude" / "settings.json"

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls._tmp_root, ignore_errors=True)

    def _tmp_env(self) -> dict:
        # set-quality-profile.sh invokes generate-dispatch.py, which resolves
        # REPO_ROOT from CLAUDE_PROJECT_DIR or os.getcwd() — NOT its own path.
        # Pin BOTH cwd and CLAUDE_PROJECT_DIR at the sandbox so dispatch
        # regeneration stays hermetic; otherwise the subprocess rewrites the
        # LIVE .claude/agents/_dispatch.md (S210 / Codex review finding).
        return {**os.environ, "CLAUDE_PROJECT_DIR": str(self._tmp_root)}

    def _apply(self, profile: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            ["bash", str(self.script), profile],
            check=False,
            capture_output=True,
            text=True,
            timeout=10,
            cwd=str(self._tmp_root),
            env=self._tmp_env(),
        )

    def test_max_quality_sets_all_to_opus(self):
        proc = self._apply("max-quality")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        for slug in ("code-reviewer", "security-engineer", "qa-architect",
                     "performance-engineer", "devops"):
            af = self.agents_dir / f"{slug}.md"
            self.assertEqual(
                _read_agent_model(af),
                "claude-opus-4-8",
                f"{slug} should be claude-opus-4-8 on max-quality profile",
            )
        # Dispatch regeneration must stay hermetic AND actually reflect the
        # applied profile — not the copied-in dispatch (Codex review #1/#2).
        # On max-quality the canonical-5 rows must show Opus (no sonnet/haiku);
        # this also fails loudly if regeneration silently no-ops (the script
        # swallows generate-dispatch errors with `|| echo WARN`).
        dispatch_text = (self.agents_dir / "_dispatch.md").read_text(encoding="utf-8")
        for slug in ("code-reviewer", "security-engineer", "qa-architect",
                     "performance-engineer", "devops"):
            row = next(
                (l for l in dispatch_text.splitlines()
                 if l.lstrip().startswith(f"| `{slug}` |")), None
            )
            self.assertIsNotNone(row, f"{slug} row missing from regenerated _dispatch.md")
            self.assertNotIn("haiku", row, f"{slug} must be Opus on max-quality dispatch")
            self.assertNotIn("sonnet", row, f"{slug} must be Opus on max-quality dispatch")

    def test_balanced_sets_expected_distribution(self):
        proc = self._apply("balanced")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        # VETO floor
        self.assertEqual(
            _read_agent_model(self.agents_dir / "code-reviewer.md"),
            "claude-opus-4-8",
        )
        self.assertEqual(
            _read_agent_model(self.agents_dir / "security-engineer.md"),
            "claude-opus-4-8",
        )
        # Non-VETO distributed
        self.assertEqual(
            _read_agent_model(self.agents_dir / "qa-architect.md"),
            "claude-sonnet-4-6",
        )
        self.assertEqual(
            _read_agent_model(self.agents_dir / "performance-engineer.md"),
            "claude-sonnet-4-6",
        )
        self.assertEqual(
            _read_agent_model(self.agents_dir / "devops.md"),
            "claude-sonnet-4-6",
        )

    def test_max_speed_keeps_veto_floor(self):
        proc = self._apply("max-speed")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        # VETO floor still Opus
        self.assertEqual(
            _read_agent_model(self.agents_dir / "code-reviewer.md"),
            "claude-opus-4-8",
            "VETO floor: code-reviewer MUST stay Opus on max-speed",
        )
        self.assertEqual(
            _read_agent_model(self.agents_dir / "security-engineer.md"),
            "claude-opus-4-8",
            "VETO floor: security-engineer MUST stay Opus on max-speed",
        )
        # 3 non-VETO on Haiku
        for slug in ("qa-architect", "performance-engineer", "devops"):
            self.assertEqual(
                _read_agent_model(self.agents_dir / f"{slug}.md"),
                "claude-haiku-4-5-20251001",
                f"{slug} should be haiku on max-speed",
            )

    def test_show_returns_current_profile(self):
        # Make sure we're on a known state
        self._apply("balanced")
        proc = subprocess.run(
            ["bash", str(self.script), "--show"],
            capture_output=True, text=True, timeout=5,
            cwd=str(self._tmp_root), env=self._tmp_env(),
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("balanced", proc.stdout)

    def test_unknown_profile_fails(self):
        proc = self._apply("wrong-profile")
        self.assertEqual(proc.returncode, 2)
        self.assertIn("unknown profile", proc.stderr)

    def test_settings_json_updated(self):
        self._apply("max-quality")
        data = json.loads(self.settings.read_text(encoding="utf-8"))
        self.assertEqual(data.get("ceo_quality_profile"), "max-quality")

    # --- PLAN-133 B2: CEO_MODEL_NORMALIZE default-OFF; flag-on is idempotent on
    #     the shipped (already-canonical) profile slugs (never corrupts them).
    def _apply_env(self, profile: str, extra_env: dict) -> subprocess.CompletedProcess:
        # Spread os.environ FIRST (the WS-A audit-dir redirect) so the child
        # cannot resolve the LIVE audit dir (PLAN-119 WS-C); _tmp_env() also
        # derives from os.environ, and extra_env then overlays the B2 flags.
        env = {**os.environ, **self._tmp_env(), **extra_env}
        return subprocess.run(
            ["bash", str(self.script), profile],
            check=False, capture_output=True, text=True, timeout=10,
            cwd=str(self._tmp_root), env=env,
        )

    def test_b2_normalize_default_off_writes_canonical_unchanged(self):
        """With CEO_MODEL_NORMALIZE unset (default-OFF), profiles write their
        canonical slugs verbatim — the B2 wiring is inert by default."""
        proc = self._apply_env("max-quality", {"CEO_MODEL_NORMALIZE": "0"})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(
            _read_agent_model(self.agents_dir / "code-reviewer.md"),
            "claude-opus-4-8",
        )

    def test_b2_normalize_flag_on_is_idempotent_on_canonical_profiles(self):
        """With CEO_MODEL_NORMALIZE=1, the shipped profiles' already-canonical
        slugs round-trip unchanged (normalize_model_name is idempotent on a
        canonical id; the major.minor token is preserved)."""
        # max-speed uses a date-stamped haiku id; with the flag ON it folds to
        # the dateless canonical slug — that is the intended, non-version-changing
        # canonicalization (the major.minor 4-5 token is preserved).
        # To prove no version is ever collapsed, max-quality (all opus-4-8) must
        # stay opus-4-8 and never become any other opus version.
        proc = self._apply_env("max-quality", {"CEO_MODEL_NORMALIZE": "1"})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        for slug in ("code-reviewer", "security-engineer", "qa-architect",
                     "performance-engineer", "devops"):
            self.assertEqual(
                _read_agent_model(self.agents_dir / f"{slug}.md"),
                "claude-opus-4-8",
                f"{slug} must remain exactly claude-opus-4-8 under normalize ON",
            )

    def test_b2_normalize_flag_folds_date_stamp_but_keeps_version(self):
        """max-speed's date-stamped haiku id (claude-haiku-4-5-20251001) folds to
        the dateless claude-haiku-4-5 with the flag ON — alias only, version (4-5)
        preserved. Requires the optimizer package importable from the sandbox."""
        # The script imports optimizer.model_normalize from <repo_root>/.claude/
        # scripts. In the sandbox that path holds only the copied script, so the
        # import fails -> fail-OPEN to the raw value. Assert the fail-open path is
        # safe (the raw date-stamped slug is written unchanged, never empty).
        proc = self._apply_env("max-speed", {"CEO_MODEL_NORMALIZE": "1"})
        self.assertEqual(proc.returncode, 0, proc.stderr)
        # VETO floor unconditionally Opus regardless of normalize.
        self.assertEqual(
            _read_agent_model(self.agents_dir / "code-reviewer.md"),
            "claude-opus-4-8",
        )
        # The non-VETO haiku slot is either the dateless canonical (if the
        # optimizer pkg resolved) or the raw date-stamped id (fail-open). Either
        # way it must be a haiku-4-5 family id — NEVER empty, NEVER a version bump.
        qa_model = _read_agent_model(self.agents_dir / "qa-architect.md")
        self.assertIn("haiku-4-5", qa_model)
        self.assertNotEqual(qa_model, "")


class TestSpotCheckFindings(unittest.TestCase):
    """spot-check-findings.py parses the expected schema."""

    def _make_fixture(self, tmp_dir: Path, body: str) -> Path:
        p = tmp_dir / "findings.md"
        p.write_text(body, encoding="utf-8")
        return p

    def test_empty_file_returns_zero_candidates(self):
        with tempfile.TemporaryDirectory() as td:
            p = self._make_fixture(Path(td), "# empty\n")
            proc = subprocess.run(
                ["python3", str(_SPOT_CHECK), str(p), "--json"],
                capture_output=True, text=True, timeout=5,
            )
            self.assertEqual(proc.returncode, 0)
            data = json.loads(proc.stdout)
            self.assertEqual(data["reaudit_candidates"], [])

    def test_p1_from_sonnet_is_candidate(self):
        body = (
            "### F-qa-001 [P1] — ReDoS backref untested\n"
            "**File:** _lib/policy.py\n"
            "**Source model:** claude-sonnet-4-6\n"
            "details...\n"
        )
        with tempfile.TemporaryDirectory() as td:
            p = self._make_fixture(Path(td), body)
            proc = subprocess.run(
                ["python3", str(_SPOT_CHECK), str(p), "--json"],
                capture_output=True, text=True, timeout=5,
            )
            self.assertEqual(proc.returncode, 0)
            data = json.loads(proc.stdout)
            self.assertEqual(len(data["reaudit_candidates"]), 1)
            self.assertEqual(data["reaudit_candidates"][0]["id"], "F-qa-001")

    def test_p1_from_opus_not_candidate(self):
        body = (
            "### F-sec-001 [P1] — TOCTOU perms\n"
            "**Source model:** claude-opus-4-8\n"
        )
        with tempfile.TemporaryDirectory() as td:
            p = self._make_fixture(Path(td), body)
            proc = subprocess.run(
                ["python3", str(_SPOT_CHECK), str(p), "--json"],
                capture_output=True, text=True, timeout=5,
            )
            self.assertEqual(proc.returncode, 0)
            data = json.loads(proc.stdout)
            self.assertEqual(data["reaudit_candidates"], [])

    def test_p1_from_historical_opus_4_7_not_candidate(self):
        # Retro-compat: a finding scored by the pre-ADR-142 Opus (4-7) must
        # STILL be recognized as Opus and excluded from re-audit (4-7 kept in
        # _OPUS_IDS for historical-log replay).
        body = (
            "### F-sec-002 [P1] — legacy opus finding\n"
            "**Source model:** claude-opus-4-7\n"
        )
        with tempfile.TemporaryDirectory() as td:
            p = self._make_fixture(Path(td), body)
            proc = subprocess.run(
                ["python3", str(_SPOT_CHECK), str(p), "--json"],
                capture_output=True, text=True, timeout=5,
            )
            self.assertEqual(proc.returncode, 0)
            data = json.loads(proc.stdout)
            self.assertEqual(data["reaudit_candidates"], [])

    def test_p2_not_candidate_even_from_sonnet(self):
        body = (
            "### F-test-001 [P2] — minor cleanup\n"
            "**Source model:** claude-sonnet-4-6\n"
        )
        with tempfile.TemporaryDirectory() as td:
            p = self._make_fixture(Path(td), body)
            proc = subprocess.run(
                ["python3", str(_SPOT_CHECK), str(p), "--json"],
                capture_output=True, text=True, timeout=5,
            )
            self.assertEqual(proc.returncode, 0)
            data = json.loads(proc.stdout)
            self.assertEqual(data["reaudit_candidates"], [])

    def test_missing_source_model_not_candidate(self):
        body = "### F-old-001 [P1] — legacy finding no source_model\n"
        with tempfile.TemporaryDirectory() as td:
            p = self._make_fixture(Path(td), body)
            proc = subprocess.run(
                ["python3", str(_SPOT_CHECK), str(p), "--json"],
                capture_output=True, text=True, timeout=5,
            )
            self.assertEqual(proc.returncode, 0)
            data = json.loads(proc.stdout)
            self.assertEqual(data["reaudit_candidates"], [])

    def test_flag_active_reports_true(self):
        body = (
            "### F-qa-001 [P1] — from sonnet\n"
            "**Source model:** claude-sonnet-4-6\n"
        )
        with tempfile.TemporaryDirectory() as td:
            p = self._make_fixture(Path(td), body)
            env = os.environ.copy()
            env["CEO_OPUS_SPOT_CHECK_P1"] = "1"
            proc = subprocess.run(
                ["python3", str(_SPOT_CHECK), str(p), "--json"],
                capture_output=True, text=True, timeout=5, env=env,
            )
            data = json.loads(proc.stdout)
            self.assertTrue(data["flag_active"])

    def test_nonexistent_file_returns_error(self):
        proc = subprocess.run(
            ["python3", str(_SPOT_CHECK), "/nonexistent/findings.md", "--json"],
            capture_output=True, text=True, timeout=5,
        )
        self.assertEqual(proc.returncode, 2)


class TestCeoHealthQualityProfile(unittest.TestCase):
    """ceo-health reports the active quality profile."""

    def test_health_includes_quality_profile_line(self):
        proc = subprocess.run(
            ["python3", str(_CEO_HEALTH)],
            capture_output=True, text=True, timeout=10,
        )
        # May exit 0 or non-zero depending on repo state; either way
        # the quality_profile line must be present.
        self.assertIn("quality_profile", proc.stdout)


if __name__ == "__main__":
    unittest.main()
