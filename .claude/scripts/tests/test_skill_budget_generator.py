"""test_skill_budget_generator.py — PLAN-135 W1 S7 unit tests.

Covers the skill-budget generator (`.claude/scripts/skill-budget-generator.py`):
- fixture skills tree (core/frontend/domain tiers) under tmp_path
- fixture audit JSONL under tmp_path (never the real $HOME — TestEnvContext)
- demotion policy: domain-tier 0-dispatch → name-only; dispatched domain
  skill kept; core/frontend NEVER demoted
- FAIL-SOFT: missing audit log → zero counts, exit 0
- malformed JSONL lines skipped
- --window-days filtering (old dispatches age out)
- --json structural shape + --jq-fragment validity/idempotency (real jq
  when available, structural assertions otherwise)

Stdlib-only. Python >= 3.9.
"""

from __future__ import annotations

import importlib.util
import io
import json
import shutil
import subprocess
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timedelta, timezone
from pathlib import Path

# TestEnvContext (S79 hygiene lesson — every test uses isolated env)
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "hooks"))
from _lib.testing import TestEnvContext  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT = REPO_ROOT / ".claude" / "scripts" / "skill-budget-generator.py"


def _load_module():
    """Load skill-budget-generator.py as an importable module (hyphen name)."""
    spec = importlib.util.spec_from_file_location("skill_budget_generator", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["skill_budget_generator"] = mod
    spec.loader.exec_module(mod)
    return mod


_mod = _load_module()


def _ts(days_ago: float) -> str:
    dt = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


class _FixtureBase(TestEnvContext):
    """Builds a 5-skill fixture tree + helpers. All paths under tmp dirs."""

    def setUp(self):
        super().setUp()
        self.repo = Path(self.project_dir)
        skills = self.repo / ".claude" / "skills"
        self._write_skill(skills / "core" / "core-alpha", "core-alpha",
                          "Core alpha skill. " * 10)
        self._write_skill(skills / "frontend" / "fe-beta", "fe-beta",
                          "Frontend beta skill. " * 10)
        self._write_skill(
            skills / "domains" / "fintech" / "skills" / "dom-hot",
            "dom-hot", "Hot domain skill, frequently dispatched. " * 5)
        self._write_skill(
            skills / "domains" / "fintech" / "skills" / "dom-cold",
            "dom-cold", "Cold domain skill, never dispatched. " * 5)
        # Legacy flat layout: domains/<d>/<name>/SKILL.md
        self._write_skill(
            skills / "domains" / "legacyd" / "dom-flat",
            "dom-flat", "Flat-layout domain skill. " * 5)
        self.audit_dir_fx = self.repo / "audit-fixture"
        self.audit_dir_fx.mkdir(parents=True, exist_ok=True)
        self.audit_log = self.audit_dir_fx / "audit-log.jsonl"

    def _write_skill(self, skill_dir: Path, name: str, desc: str) -> None:
        skill_dir.mkdir(parents=True, exist_ok=True)
        (skill_dir / "SKILL.md").write_text(
            f"---\nname: {name}\ndescription: {desc}\n---\n# {name}\n",
            encoding="utf-8",
        )

    def _write_log(self, entries) -> None:
        with open(self.audit_log, "w", encoding="utf-8") as f:
            for e in entries:
                f.write(e if isinstance(e, str) else json.dumps(e))
                f.write("\n")

    def _run(self, *argv: str):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = _mod.main(list(argv))
        return rc, out.getvalue(), err.getvalue()

    def _run_json(self, *extra: str):
        rc, out, err = self._run(
            "--json", "--repo-root", str(self.repo),
            "--audit-log", str(self.audit_log), *extra)
        self.assertEqual(rc, 0, err)
        return json.loads(out)


class TestDemotionPolicy(_FixtureBase):
    def test_zero_dispatch_domain_skill_demoted_dispatched_kept(self):
        self._write_log([
            {"action": "agent_spawn", "skill": "dom-hot", "ts": _ts(1)},
            {"action": "agent_spawn", "skill": "dom-hot", "ts": _ts(2)},
        ])
        report = self._run_json()
        overrides = report["recommendation"]["skillOverrides"]
        self.assertIn("dom-cold", overrides)
        self.assertEqual(overrides["dom-cold"], "name-only")
        self.assertNotIn("dom-hot", overrides)
        self.assertIn("dom-hot", report["dispatched_domain_skills"])

    def test_core_and_frontend_never_demoted_even_at_zero(self):
        self._write_log([])  # zero dispatches for EVERYONE
        report = self._run_json()
        overrides = report["recommendation"]["skillOverrides"]
        self.assertNotIn("core-alpha", overrides)
        self.assertNotIn("fe-beta", overrides)
        # all three domain skills demoted (incl. legacy flat layout)
        self.assertEqual(
            sorted(overrides), ["dom-cold", "dom-flat", "dom-hot"])
        self.assertTrue(all(v == "name-only" for v in overrides.values()))

    def test_skill_slug_field_also_counts_as_dispatch(self):
        self._write_log([
            {"action": "skill_patch_applied", "skill_slug": "dom-cold",
             "ts": _ts(1)},
        ])
        report = self._run_json()
        self.assertNotIn(
            "dom-cold", report["recommendation"]["skillOverrides"])

    def test_unknown_skill_value_is_not_a_dispatch(self):
        self._write_log([
            {"action": "agent_spawn", "skill": "unknown", "ts": _ts(1)},
        ])
        report = self._run_json()
        self.assertEqual(report["audit_log"]["dispatch_entries"], 0)

    def test_inventory_tier_counts(self):
        self._write_log([])
        report = self._run_json()
        inv = report["inventory"]
        self.assertEqual(
            (inv["core"], inv["frontend"], inv["domain"], inv["total"]),
            (1, 1, 3, 5))

    def test_name_dir_mismatch_emits_both_spellings(self):
        # Domain skill whose frontmatter name differs from its dir slug:
        # both spellings must appear as override keys (no-op keys are
        # harmless; one of them is the one the CLI indexes by).
        skill_dir = (self.repo / ".claude" / "skills" / "domains"
                     / "fintech" / "skills" / "dom-mismatch")
        self._write_skill(skill_dir, "Dom Mismatch Pretty Name", "Mismatch. " * 5)
        self._write_log([])
        report = self._run_json()
        overrides = report["recommendation"]["skillOverrides"]
        self.assertEqual(overrides.get("dom-mismatch"), "name-only")
        self.assertEqual(overrides.get("Dom Mismatch Pretty Name"), "name-only")
        # 4 demoted skills, 5 override keys
        self.assertEqual(report["recommendation"]["demoted_domain_skills"], 4)
        self.assertEqual(report["recommendation"]["override_keys"], 5)

    def test_collision_with_protected_tier_is_suppressed(self):
        # Domain skill whose DIR name equals a frontend skill's NAME:
        # that spelling must NOT be emitted (it could demote the
        # protected-tier skill); the non-colliding spelling still is.
        skill_dir = (self.repo / ".claude" / "skills" / "domains"
                     / "fintech" / "skills" / "fe-beta")
        self._write_skill(skill_dir, "fintech-fe-beta", "Shadowing. " * 5)
        self._write_log([])
        report = self._run_json()
        overrides = report["recommendation"]["skillOverrides"]
        self.assertNotIn("fe-beta", overrides)  # protected spelling
        self.assertEqual(overrides.get("fintech-fe-beta"), "name-only")
        self.assertIn(
            "fe-beta",
            report["recommendation"]["protected_collisions_skipped"])


class TestFailSoft(_FixtureBase):
    def test_missing_audit_log_fail_soft_zero_counts_exit_zero(self):
        # never written → absent file, absent siblings
        rc, out, err = self._run(
            "--json", "--repo-root", str(self.repo),
            "--audit-log", str(self.audit_log))
        self.assertEqual(rc, 0)
        report = json.loads(out)
        self.assertFalse(report["audit_log"]["found"])
        self.assertTrue(report["audit_log"]["fail_soft"])
        self.assertIn("FAIL-SOFT", err)
        # zero counts everywhere → every domain skill demoted
        self.assertEqual(
            report["recommendation"]["demoted_domain_skills"], 3)

    def test_malformed_lines_skipped_valid_lines_counted(self):
        self._write_log([
            "{not json at all",
            json.dumps({"action": "agent_spawn", "skill": "dom-cold",
                        "ts": _ts(1)}),
            "",
            "[1,2,3]",  # valid JSON, not a dict — ignored
        ])
        report = self._run_json()
        self.assertEqual(report["audit_log"]["dispatch_entries"], 1)
        self.assertNotIn(
            "dom-cold", report["recommendation"]["skillOverrides"])

    def test_default_log_path_resolution_stays_inside_test_home(self):
        # No --audit-log: resolution must use the TestEnvContext HOME
        # (or CEO_AUDIT_LOG_PATH), never the real user home.
        p = _mod.default_log_path()
        self.assertIn(str(self.home_dir), str(p))


class TestWindowFiltering(_FixtureBase):
    def test_old_dispatch_outside_window_does_not_protect(self):
        self._write_log([
            {"action": "agent_spawn", "skill": "dom-hot", "ts": _ts(90)},
        ])
        report = self._run_json("--window-days", "30")
        self.assertIn(
            "dom-hot", report["recommendation"]["skillOverrides"])

    def test_recent_dispatch_inside_window_protects(self):
        self._write_log([
            {"action": "agent_spawn", "skill": "dom-hot", "ts": _ts(5)},
        ])
        report = self._run_json("--window-days", "30")
        self.assertNotIn(
            "dom-hot", report["recommendation"]["skillOverrides"])

    def test_unparseable_ts_counts_conservatively(self):
        self._write_log([
            {"action": "agent_spawn", "skill": "dom-hot", "ts": "garbage"},
        ])
        report = self._run_json("--window-days", "30")
        self.assertNotIn(
            "dom-hot", report["recommendation"]["skillOverrides"])


class TestOutputShapes(_FixtureBase):
    def test_json_report_shape_and_fraction_bounds(self):
        self._write_log([])
        report = self._run_json()
        for key in ("provenance", "cli_probe", "inventory", "audit_log",
                    "recommendation"):
            self.assertIn(key, report)
        frac = report["recommendation"]["skillListingBudgetFraction"]
        self.assertGreater(frac, 0)
        self.assertLessEqual(frac, 1)
        # never recommends ABOVE the CLI default
        self.assertLessEqual(frac, _mod.CLI_DEFAULT_FRACTION)

    def test_overrides_sorted_and_deterministic(self):
        self._write_log([])
        r1 = self._run_json()
        r2 = self._run_json()
        self.assertEqual(r1, r2)
        keys = list(r1["recommendation"]["skillOverrides"])
        self.assertEqual(keys, sorted(keys))

    def test_jq_fragment_structure(self):
        self._write_log([])
        rc, frag, err = self._run(
            "--jq-fragment", "--repo-root", str(self.repo),
            "--audit-log", str(self.audit_log))
        self.assertEqual(rc, 0, err)
        self.assertIn('"skillListingBudgetFraction"', frag)
        self.assertIn('"skillOverrides": ((.skillOverrides // {}) + {', frag)
        self.assertIn('"dom-cold": "name-only"', frag)
        self.assertNotIn('"core-alpha"', frag)
        self.assertNotIn('"fe-beta"', frag)

    @unittest.skipUnless(shutil.which("jq"), "jq not installed")
    def test_jq_fragment_applies_idempotently_and_preserves_foreign_keys(self):
        self._write_log([])
        rc, frag, _ = self._run(
            "--jq-fragment", "--repo-root", str(self.repo),
            "--audit-log", str(self.audit_log))
        self.assertEqual(rc, 0)
        frag_path = self.repo / "frag.jq"
        frag_path.write_text(frag, encoding="utf-8")
        settings = {
            "hooks": {"Stop": []},
            "skillOverrides": {"operator-added": "off"},
        }

        def apply(doc):
            proc = subprocess.run(
                ["jq", "-f", str(frag_path)],
                input=json.dumps(doc), capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            return json.loads(proc.stdout)

        once = apply(settings)
        twice = apply(once)
        self.assertEqual(once, twice)  # idempotent
        self.assertEqual(once["skillOverrides"]["operator-added"], "off")
        self.assertEqual(once["skillOverrides"]["dom-cold"], "name-only")
        self.assertEqual(once["hooks"], {"Stop": []})  # untouched
        self.assertLessEqual(
            once["skillListingBudgetFraction"], _mod.CLI_DEFAULT_FRACTION)


class TestEmptyInventory(TestEnvContext):
    def test_missing_skills_tree_yields_empty_recommendation(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = _mod.main([
                "--json", "--repo-root", str(self.project_dir),
                "--audit-log",
                str(Path(self.project_dir) / "nope" / "audit-log.jsonl"),
            ])
        self.assertEqual(rc, 0)
        report = json.loads(out.getvalue())
        self.assertEqual(report["inventory"]["total"], 0)
        self.assertEqual(report["recommendation"]["skillOverrides"], {})


if __name__ == "__main__":
    unittest.main()
