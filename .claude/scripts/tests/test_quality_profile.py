"""PLAN-025 Batch L — tests for 3-profile quality configurator.

Covers:
- set-quality-profile.sh apply for each of 3 profiles (end-to-end)
- Invariant: code-reviewer + security-engineer stay on the DERIVED VETO
  floor in ALL profiles (PLAN-169 W4.3 F1 — this file used to assert the
  literal `claude-opus-4-8` for those two slots while the agent files
  shipped `claude-fable-5`, so the suite was green because it encoded the
  downgrade; the expectation now comes from the same authority the script
  reads, and a literal for a VETO role is itself a failure)
- spot-check-findings.py parses the expected schema
- ceo-health.py surfaces quality_profile line
- --show returns the current profile

Uses subprocess to exercise the bash script against a tmp fixture.
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


def _veto_floor_expected(role: str) -> str:
    """The expected VETO floor, read from the authority the SCRIPT reads.

    Hardcoding the value here was exactly the defect: this file asserted
    `claude-opus-4-8` for code-reviewer / security-engineer while the agent
    files lived on `claude-fable-5`, so every profile invocation moved the
    floor two generations down and the suite stayed green by agreeing with
    the downgrade. `claude-opus-4-8` is a member of `VETO_FLOOR_ALLOWED`
    (the ADR-149 N-1 tolerance window), so no hook fired either.
    """
    sys.path.insert(0, str(_REPO_ROOT / ".claude" / "scripts"))
    from tier_policy_cli._constants import VETO_HARDCODE
    return VETO_HARDCODE[role]


_VETO_ROLES = ("code-reviewer", "security-engineer")
_ADVISORY_ROLES = ("qa-architect", "performance-engineer", "devops")


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
        # PLAN-169 W4.3 F1: the script now DERIVES the VETO floor from
        # tier_policy_cli. Without the package in the sandbox its
        # fail-CLOSED path fires and the whole class dies with rc=3
        # instead of measuring the cure.
        # (The `optimizer` package stays DELIBERATELY out —
        # test_b2_normalize_flag_folds_date_stamp_but_keeps_version
        # exercises the fail-OPEN of that import. Do not "fix" it.)
        src_tpc = _REPO_ROOT / ".claude" / "scripts" / "tier_policy_cli"
        if src_tpc.is_dir():
            shutil.copytree(
                src_tpc, tmp_scripts / "tier_policy_cli",
                ignore=shutil.ignore_patterns("__pycache__", "tests"),
            )
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

    def test_max_quality_veto_floor_derived_advisories_opus(self):
        proc = self._apply("max-quality")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        for slug in _VETO_ROLES:
            self.assertEqual(
                _read_agent_model(self.agents_dir / f"{slug}.md"),
                _veto_floor_expected(slug),
                f"{slug} must carry the derived VETO floor on max-quality",
            )
        for slug in _ADVISORY_ROLES:
            self.assertEqual(
                _read_agent_model(self.agents_dir / f"{slug}.md"),
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
        # VETO floor — derived, never a literal
        self.assertEqual(
            _read_agent_model(self.agents_dir / "code-reviewer.md"),
            _veto_floor_expected("code-reviewer"),
        )
        self.assertEqual(
            _read_agent_model(self.agents_dir / "security-engineer.md"),
            _veto_floor_expected("security-engineer"),
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
        # VETO floor still on the DERIVED floor
        self.assertEqual(
            _read_agent_model(self.agents_dir / "code-reviewer.md"),
            _veto_floor_expected("code-reviewer"),
            "VETO floor: code-reviewer MUST stay on the derived floor "
            "on max-speed",
        )
        self.assertEqual(
            _read_agent_model(self.agents_dir / "security-engineer.md"),
            _veto_floor_expected("security-engineer"),
            "VETO floor: security-engineer MUST stay on the derived floor "
            "on max-speed",
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
            _veto_floor_expected("code-reviewer"),
        )
        self.assertEqual(
            _read_agent_model(self.agents_dir / "qa-architect.md"),
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
        for slug in _VETO_ROLES:
            expected = _veto_floor_expected(slug)
            self.assertEqual(
                _read_agent_model(self.agents_dir / f"{slug}.md"),
                expected,
                f"{slug} must remain exactly {expected} under normalize ON",
            )
        for slug in _ADVISORY_ROLES:
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
        # VETO floor unconditionally on the derived floor regardless of
        # normalize.
        self.assertEqual(
            _read_agent_model(self.agents_dir / "code-reviewer.md"),
            _veto_floor_expected("code-reviewer"),
        )
        # The non-VETO haiku slot is either the dateless canonical (if the
        # optimizer pkg resolved) or the raw date-stamped id (fail-open). Either
        # way it must be a haiku-4-5 family id — NEVER empty, NEVER a version bump.
        qa_model = _read_agent_model(self.agents_dir / "qa-architect.md")
        self.assertIn("haiku-4-5", qa_model)
        self.assertNotEqual(qa_model, "")


class TestVetoFloorInvariantIsDerived(TestSetQualityProfileScript):
    """PLAN-169 W4.3 F1 / PLAN-183 W3 — the permanent guard for the class.

    The VETO floor cannot be held up by a literal duplicated across N `case`
    branches. Before this cure the guard enumerated 3 profiles by hand and
    asserted `claude-opus-4-8` — the OLD value — while `.claude/agents/*.md`
    lived on `claude-fable-5`. The instrument defended the defect, and the
    downgrade slipped through `VETO_FLOOR_ALLOWED` (a 3-member allowlist
    that keeps the previous flagship valid during migration), so no hook
    fired.

    The profiles below are EXTRACTED from the script, not listed here: a
    4th profile is covered the moment it is added.
    """

    def _declared_profiles(self):
        """Profile labels the script's `_profile_models` accepts."""
        text = _SCRIPT.read_text(encoding="utf-8")
        body = text.split("_profile_models() {", 1)[1]
        body = body.split("\n}", 1)[0]
        labels = set()
        for match in re.finditer(r"^\s*([a-z0-9|-]+)\)", body, re.M):
            for label in match.group(1).split("|"):
                label = label.strip()
                if label and label != "*":
                    labels.add(label)
        return sorted(labels)

    def _emitting_profiles(self):
        """Labels of the branch that actually EMITS a map."""
        text = _SCRIPT.read_text(encoding="utf-8")
        body = text.split("_profile_models() {", 1)[1].split("\n}", 1)[0]
        labels = set()
        for match in re.finditer(
            r"^\s*([a-z0-9|-]+)\)\s*\n\s*echo \"code-reviewer:", body, re.M
        ):
            for label in match.group(1).split("|"):
                if label.strip():
                    labels.add(label.strip())
        return sorted(labels)

    def test_profile_set_is_non_empty(self):
        """Vacuity guard — a broken parser would make the rest of this
        class green by having nothing to iterate over."""
        profiles = self._declared_profiles()
        self.assertGreaterEqual(len(profiles), 3, profiles)
        self.assertIn("max-quality", profiles)

    def test_accepted_and_emitting_profile_sets_are_identical(self):
        """A label the validator accepts but the emitter has no branch for
        would produce an EMPTY map: rc=0, nothing written, silently. The
        two `case` blocks must stay in lockstep."""
        self.assertEqual(self._declared_profiles(), self._emitting_profiles())

    def test_no_profile_ever_downgrades_the_veto_floor(self):
        """Every profile the script accepts, both VETO holders, compared
        against the authority. Before the cure this failed on all three
        with 'claude-opus-4-8' != 'claude-fable-5'."""
        for profile in self._declared_profiles():
            proc = self._apply(profile)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            for role in _VETO_ROLES:
                self.assertEqual(
                    _read_agent_model(self.agents_dir / f"{role}.md"),
                    _veto_floor_expected(role),
                    f"{profile} moved the VETO floor for {role}",
                )

    def test_script_carries_no_bare_model_literal_for_veto_roles(self):
        """Positive control of the MECHANISM: planting the old literal back
        into any `case` branch has to light this up by name."""
        text = _SCRIPT.read_text(encoding="utf-8")
        for role in _VETO_ROLES:
            hits = re.findall(rf"{re.escape(role)}:claude-[a-z0-9-]+", text)
            self.assertEqual(
                hits, [],
                f"{role} is pinned to a literal model id again ({hits}) — "
                f"the F1-P1 class (PLAN-169/fleet-currency-audit-S298) "
                f"is back",
            )

    def test_managed_veto_roles_match_the_authority_exactly(self):
        """Coverage, declared rather than assumed. Of the 5
        `VETO_FLOOR_ROLES` the script manages 2; the other 3
        (incident-commander, identity-trust-architect,
        threat-detection-engineer) appear in NO profile. That is a
        decision, and pinning it here means a new VETO role can neither
        arrive managed-and-downgraded nor drop out of scope in silence."""
        sys.path.insert(0, str(_REPO_ROOT / ".claude" / "hooks"))
        sys.path.insert(0, str(_REPO_ROOT / ".claude" / "scripts"))
        from _lib.agent_frontmatter import VETO_FLOOR_ROLES
        from tier_policy_cli._constants import VETO_HARDCODE

        text = _SCRIPT.read_text(encoding="utf-8")
        managed = {
            role for role in VETO_FLOOR_ROLES
            if re.search(rf"\b{re.escape(role)}:", text)
        }
        self.assertEqual(
            managed, set(VETO_HARDCODE),
            "the script's managed VETO set drifted from VETO_HARDCODE — "
            "update BOTH or neither",
        )
        self.assertTrue(
            set(VETO_HARDCODE) <= set(VETO_FLOOR_ROLES),
            "VETO_HARDCODE names a role that is not a VETO_FLOOR_ROLE",
        )

    def test_veto_floor_is_the_ceiling_not_merely_an_allowlist_member(self):
        """The allowlist is NOT the floor. `claude-opus-4-8` is a member of
        `VETO_FLOOR_ALLOWED` and is two generations below the ceiling, so
        membership-only checks (`test_veto_floor_bijection.py`) stay green
        through the downgrade. The floor is the authority's value."""
        sys.path.insert(0, str(_REPO_ROOT / ".claude" / "hooks"))
        from _lib.agent_frontmatter import VETO_FLOOR_ALLOWED

        for role in _VETO_ROLES:
            expected = _veto_floor_expected(role)
            self.assertIn(expected, VETO_FLOOR_ALLOWED)
            self.assertGreater(
                len(VETO_FLOOR_ALLOWED), 1,
                "a single-member allowlist would make this test vacuous",
            )

    def test_fail_closed_when_the_authority_is_unreadable(self):
        """The fail-CLOSED path is behaviour, not a comment. With the
        authority gone the script must refuse (rc=3) and leave every agent
        file untouched — falling back to a literal is what created this
        class."""
        moved = self._tmp_root / "authority-moved-aside"
        src = self._tmp_root / ".claude" / "scripts" / "tier_policy_cli"
        self.assertTrue(src.is_dir(), "sandbox has no authority to remove")
        self._apply("max-speed")
        before = {
            role: _read_agent_model(self.agents_dir / f"{role}.md")
            for role in _VETO_ROLES + _ADVISORY_ROLES
        }
        shutil.move(str(src), str(moved))
        try:
            proc = self._apply("max-quality")
            self.assertEqual(proc.returncode, 3, proc.stderr)
            self.assertIn("fail-CLOSED", proc.stderr)
            for role, model in before.items():
                self.assertEqual(
                    _read_agent_model(self.agents_dir / f"{role}.md"), model,
                    f"{role} was rewritten despite the fail-CLOSED refusal",
                )
        finally:
            shutil.move(str(moved), str(src))
        # Control: with the authority restored the same profile succeeds.
        self.assertEqual(self._apply("max-quality").returncode, 0)


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
