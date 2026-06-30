"""Unit tests for skill-index-build.py and skill-retrieve.py.

PLAN-011 Phase 2. Exercises the full retrieval pipeline end-to-end on
synthetic SKILL.md fixtures, so the tests never touch the real repo's
skills and the assertions are stable regardless of SKILL.md churn.
"""

from __future__ import annotations

import importlib.util
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_SCRIPTS_DIR = _REPO_ROOT / ".claude" / "scripts"
_HOOKS_LIB = _REPO_ROOT / ".claude" / "hooks"
sys.path.insert(0, str(_HOOKS_LIB))
sys.path.insert(0, str(_SCRIPTS_DIR))


def _load_script(name: str, filename: str):
    """Dynamically load a hyphenated script file as a Python module."""
    spec = importlib.util.spec_from_file_location(name, str(_SCRIPTS_DIR / filename))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


build_mod = _load_script("skill_index_build", "skill-index-build.py")
retrieve_mod = _load_script("skill_retrieve", "skill-retrieve.py")


_MINIMAL_SKILLS = {
    "core/security-and-auth": {
        "name": "security-and-auth",
        "description": (
            "Security, authentication, JWT token handling, authorization, encryption, "
            "threat modeling, and defense-in-depth patterns. Use when building "
            "authentication systems, session management, or security reviews."
        ),
        "body": "# Security and Auth\n\nThis skill covers HTTPS, TLS, CSRF, JWT.",
    },
    "core/testing-strategy": {
        "name": "testing-strategy",
        "description": (
            "Testing patterns, unit tests, integration tests, coverage, "
            "mutation testing, chaos testing, and CI integration."
        ),
        "body": "# Testing Strategy\n\nUse vitest, pytest, coverage reporting.",
    },
    "core/performance-engineering": {
        "name": "performance-engineering",
        "description": (
            "Performance profiling, memory leaks, event loop analysis, "
            "garbage collection tuning, latency budgets."
        ),
        "body": "# Performance\n\nProfile CPU and memory.",
    },
    "frontend/accessibility-and-wcag": {
        "name": "accessibility-and-wcag",
        "description": (
            "WCAG 2.1 AA, screen reader, focus traps, color contrast, "
            "keyboard navigation, ARIA."
        ),
        "body": "# Accessibility\n\nFocus rings, aria-label.",
    },
    "domains/fintech/skills/financial-display": {
        "name": "financial-display",
        "description": (
            "Financial display rounding, locale-aware currency formatting, "
            "decimal precision, P&L rendering."
        ),
        "body": "# Financial Display\n\nRound to cent, format BRL USD.",
    },
    "domains/lgpd-heavy-saas/skills/consent-lifecycle": {
        "name": "consent-lifecycle",
        "description": (
            "LGPD consent lifecycle, consent state machine, "
            "data subject access requests, opt-in flow."
        ),
        "body": "# Consent\n\nTrack consent per purpose.",
    },
}


def _write_skills(repo_root: Path):
    """Write the minimal synthetic SKILL.md fixtures under repo_root/.claude/skills/."""
    for rel_path, spec in _MINIMAL_SKILLS.items():
        skill_dir = repo_root / ".claude" / "skills" / rel_path
        skill_dir.mkdir(parents=True, exist_ok=True)
        content = textwrap.dedent(f"""\
            ---
            name: {spec['name']}
            description: {spec['description']}
            owner: test
            ---

            {spec['body']}
            """)
        (skill_dir / "SKILL.md").write_text(content, encoding="utf-8")


class _TempRepoTestCase(unittest.TestCase):
    """Base: gives each test a fresh temp repo + isolated env."""

    def setUp(self):
        self._env_snapshot = {
            k: os.environ.get(k)
            for k in (
                "CEO_SKILL_INDEX_PATH",
                "CEO_SOTA_DISABLE",
                "CEO_REAL_EMBEDDINGS",
                "CEO_PROJECT_NAME",
                "HOME",
                "CEO_AUDIT_LOG_ERR",
            )
        }
        self.tmpdir = Path(tempfile.mkdtemp(prefix="ceo-skill-retr-"))
        self.repo_root = self.tmpdir / "repo"
        self.home_dir = self.tmpdir / "home"
        self.repo_root.mkdir()
        self.home_dir.mkdir()
        os.environ["HOME"] = str(self.home_dir)
        os.environ.pop("CEO_SKILL_INDEX_PATH", None)
        os.environ.pop("CEO_SOTA_DISABLE", None)
        os.environ.pop("CEO_REAL_EMBEDDINGS", None)
        self.index_path = self.tmpdir / "skill-index.sqlite"
        _write_skills(self.repo_root)

    def tearDown(self):
        for k, v in self._env_snapshot.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)


class TestIndexBuild(_TempRepoTestCase):
    def test_creates_sqlite_file(self):
        summary = build_mod.build_index(self.repo_root, self.index_path)
        self.assertTrue(self.index_path.is_file())
        self.assertEqual(summary["skills_indexed"], len(_MINIMAL_SKILLS))
        self.assertGreater(summary["idf_terms"], 0)

    def test_schema_has_expected_tables(self):
        build_mod.build_index(self.repo_root, self.index_path)
        conn = sqlite3.connect(str(self.index_path))
        try:
            tables = {
                row[0]
                for row in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
        finally:
            conn.close()
        self.assertIn("skills", tables)
        self.assertIn("idf", tables)
        self.assertIn("meta", tables)

    def test_meta_records_total_docs_and_spec_version(self):
        build_mod.build_index(self.repo_root, self.index_path)
        conn = sqlite3.connect(str(self.index_path))
        try:
            meta = {k: v for k, v in conn.execute("SELECT k, v FROM meta").fetchall()}
        finally:
            conn.close()
        self.assertEqual(int(meta["total_docs"]), len(_MINIMAL_SKILLS))
        self.assertIn("spec_version", meta)

    def test_build_raises_when_no_skills(self):
        # Empty repo
        empty_root = self.tmpdir / "empty-repo"
        empty_root.mkdir()
        with self.assertRaises(RuntimeError):
            build_mod.build_index(empty_root, self.index_path)

    def test_tier_resolution(self):
        build_mod.build_index(self.repo_root, self.index_path)
        conn = sqlite3.connect(str(self.index_path))
        try:
            rows = {
                r[0]: r[1]
                for r in conn.execute("SELECT slug, tier FROM skills").fetchall()
            }
        finally:
            conn.close()
        self.assertEqual(rows["security-and-auth"], "core")
        self.assertEqual(rows["accessibility-and-wcag"], "frontend")
        self.assertEqual(rows["financial-display"], "domain:fintech")

    def test_build_idempotent(self):
        # Two builds -> same skill count, no duplicates
        build_mod.build_index(self.repo_root, self.index_path)
        build_mod.build_index(self.repo_root, self.index_path)
        conn = sqlite3.connect(str(self.index_path))
        try:
            count = conn.execute("SELECT COUNT(*) FROM skills").fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(count, len(_MINIMAL_SKILLS))


class TestStaleDetection(_TempRepoTestCase):
    def test_fresh_index_has_no_stale(self):
        build_mod.build_index(self.repo_root, self.index_path)
        stale = build_mod.check_stale(self.repo_root, self.index_path)
        self.assertEqual(stale, [])

    def test_touching_a_skill_marks_it_stale(self):
        build_mod.build_index(self.repo_root, self.index_path)
        # Bump mtime on one skill by rewriting
        target = self.repo_root / ".claude" / "skills" / "core" / "security-and-auth" / "SKILL.md"
        original = target.read_text()
        # Force the mtime forward even if write happens at same wall clock
        import time
        time.sleep(0.01)
        target.write_text(original + "\n# touched\n")
        # Also bump mtime explicitly to be safe on fast filesystems
        now = target.stat().st_mtime + 5.0
        os.utime(target, (now, now))
        stale = build_mod.check_stale(self.repo_root, self.index_path)
        slugs = [s["slug"] for s in stale]
        self.assertIn("security-and-auth", slugs)

    def test_missing_index_returns_empty_list(self):
        stale = build_mod.check_stale(self.repo_root, self.tmpdir / "no-such.sqlite")
        self.assertEqual(stale, [])


class TestRetrievalQuery(_TempRepoTestCase):
    def setUp(self):
        super().setUp()
        build_mod.build_index(self.repo_root, self.index_path)
        self.view = retrieve_mod.load_index(self.index_path)

    def test_load_index_exposes_vectors(self):
        self.assertEqual(len(self.view.skills), len(_MINIMAL_SKILLS))
        for sk in self.view.skills:
            self.assertIsInstance(sk["vector"], dict)

    def test_query_vector_non_empty_for_real_task(self):
        q = retrieve_mod.query_vector("JWT authentication security", self.view.idf_map, self.view.total_docs)
        self.assertGreater(len(q), 0)

    def test_retrieval_returns_relevant_skill_in_top_k(self):
        q = retrieve_mod.query_vector(
            "JWT authentication and session security",
            self.view.idf_map,
            self.view.total_docs,
        )
        results = retrieve_mod.rank(q, self.view.skills, top_k=3)
        slugs = [r["slug"] for r in results]
        self.assertIn("security-and-auth", slugs)

    def test_top_k_limit_respected(self):
        q = retrieve_mod.query_vector(
            "testing code", self.view.idf_map, self.view.total_docs
        )
        results = retrieve_mod.rank(q, self.view.skills, top_k=2)
        self.assertEqual(len(results), 2)

    def test_empty_query_vector_returns_empty_results(self):
        results = retrieve_mod.rank({}, self.view.skills, top_k=5)
        self.assertEqual(results, [])

    def test_archetype_boost_ranks_owned_skill_higher(self):
        # Query matches both testing-strategy AND security-and-auth weakly;
        # supplying archetype_skills=["testing-strategy"] should boost it.
        q = retrieve_mod.query_vector(
            "audit review coverage", self.view.idf_map, self.view.total_docs
        )
        unboosted = retrieve_mod.rank(q, self.view.skills, top_k=10)
        boosted = retrieve_mod.rank(
            q,
            self.view.skills,
            top_k=10,
            archetype_skills=["testing-strategy"],
            archetype_boost=0.5,  # large enough to flip any tie
        )
        # Find testing-strategy rank in both
        unboosted_rank = next(
            i for i, r in enumerate(unboosted) if r["slug"] == "testing-strategy"
        )
        boosted_rank = next(
            i for i, r in enumerate(boosted) if r["slug"] == "testing-strategy"
        )
        self.assertLessEqual(boosted_rank, unboosted_rank)

    def test_retrieval_financial_display_query(self):
        q = retrieve_mod.query_vector(
            "fix the currency rounding on the P&L display",
            self.view.idf_map,
            self.view.total_docs,
        )
        results = retrieve_mod.rank(q, self.view.skills, top_k=3)
        slugs = [r["slug"] for r in results]
        self.assertIn("financial-display", slugs)


class TestMalformedSkills(unittest.TestCase):
    """Malformed SKILL.md files should be skipped, not crash the build."""

    def setUp(self):
        self.tmpdir = Path(tempfile.mkdtemp(prefix="ceo-malformed-"))
        self.repo_root = self.tmpdir / "repo"
        self.index_path = self.tmpdir / "idx.sqlite"
        # One valid skill, one malformed (no frontmatter, empty body)
        good = self.repo_root / ".claude" / "skills" / "core" / "good-skill"
        good.mkdir(parents=True)
        (good / "SKILL.md").write_text(
            "---\nname: good-skill\ndescription: good skill description with useful words\nowner: x\n---\n\n# Body\n",
            encoding="utf-8",
        )
        bad = self.repo_root / ".claude" / "skills" / "core" / "empty-skill"
        bad.mkdir(parents=True)
        (bad / "SKILL.md").write_text("", encoding="utf-8")

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_malformed_skill_skipped(self):
        # Empty SKILL.md yields no tokens -> skipped with warning
        summary = build_mod.build_index(self.repo_root, self.index_path)
        # Only the good skill indexed
        self.assertEqual(summary["skills_indexed"], 1)


class TestCLIFlags(_TempRepoTestCase):
    def test_sota_disable_in_index_build_is_noop(self):
        os.environ["CEO_SOTA_DISABLE"] = "1"
        # Target a path that should NOT be created
        target = self.tmpdir / "should-not-exist.sqlite"
        rc = build_mod._cli(
            ["--repo-root", str(self.repo_root), "--index-path", str(target)]
        )
        self.assertEqual(rc, 0)
        self.assertFalse(target.exists())

    def test_sota_disable_in_retrieve_does_static_fallback(self):
        # Write a minimal team.md so static fallback has something to match
        (self.repo_root / ".claude" / "team.md").write_text(
            textwrap.dedent("""\
                # Team

                ## SKILL MAP

                | Archetype | Primary skill |
                |-----------|---------------|
                | **Security Engineer** | `security-and-auth` |
                | **QA** | `testing-strategy` |
                """),
            encoding="utf-8",
        )
        os.environ["CEO_SOTA_DISABLE"] = "1"
        rc = retrieve_mod._cli([
            "--task", "security authentication",
            "--top-k", "1",
            "--repo-root", str(self.repo_root),
        ])
        self.assertEqual(rc, 0)

    def test_retrieve_cli_empty_task_rejected(self):
        rc = retrieve_mod._cli(["--task", "", "--repo-root", str(self.repo_root)])
        self.assertEqual(rc, 2)

    def test_retrieve_cli_negative_topk_rejected(self):
        rc = retrieve_mod._cli([
            "--task", "anything",
            "--top-k", "0",
            "--repo-root", str(self.repo_root),
        ])
        self.assertEqual(rc, 2)

    def test_retrieve_falls_back_when_index_missing(self):
        # No index at the path, but team.md exists -> static fallback, exit 0
        (self.repo_root / ".claude" / "team.md").write_text(
            "| **X** | `security-and-auth` |\n", encoding="utf-8"
        )
        missing = self.tmpdir / "missing.sqlite"
        rc = retrieve_mod._cli([
            "--task", "security",
            "--index-path", str(missing),
            "--repo-root", str(self.repo_root),
        ])
        self.assertEqual(rc, 0)


class TestUncommittedCheck(_TempRepoTestCase):
    def test_check_uncommitted_returns_list_on_git_repo(self):
        # Init a real git repo and add an uncommitted file
        subprocess.run(["git", "init", "-q"], cwd=self.repo_root, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.local"],
            cwd=self.repo_root,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=self.repo_root,
            check=True,
        )
        # Uncommitted: the freshly-written SKILL.md fixtures
        uncommitted = build_mod.check_uncommitted_skills(self.repo_root)
        self.assertGreater(len(uncommitted), 0)

    def test_check_uncommitted_returns_empty_on_non_git_dir(self):
        uncommitted = build_mod.check_uncommitted_skills(self.tmpdir / "not-a-repo")
        self.assertEqual(uncommitted, [])

    def test_strict_mode_exits_3_on_uncommitted(self):
        subprocess.run(["git", "init", "-q"], cwd=self.repo_root, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.local"],
            cwd=self.repo_root,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=self.repo_root,
            check=True,
        )
        rc = build_mod._cli([
            "--repo-root", str(self.repo_root),
            "--index-path", str(self.index_path),
            "--strict",
        ])
        self.assertEqual(rc, 3)
        self.assertFalse(self.index_path.exists())


class TestArchetypeRowPrimarySkill(unittest.TestCase):
    """PLAN-113 W6 (F-11.14) regression: skill-retrieve.py carried an
    INDEPENDENT copy of the registry.py last-backtick bug. A team.md row
    with both a primary and a secondary backticked skill must resolve to
    the FIRST (primary) skill, not the LAST (secondary)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="ceo-skill-arch-"))
        (self.tmp / ".claude").mkdir()
        (self.tmp / ".claude" / "team.md").write_text(
            "| Role | Primary skill | Secondary |\n"
            "|------|---------------|-----------|\n"
            "| **VP Engineering** | `architecture-decisions` | `incremental-refactoring` |\n"
            "| **QA Architect** | `evidence-based-qa` | manual review |\n",
            encoding="utf-8",
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_archetype_primary_skill_is_first_backtick(self):
        skills = retrieve_mod.archetype_primary_skill(self.tmp, "VP Engineering")
        self.assertIn("architecture-decisions", skills)
        self.assertNotIn("incremental-refactoring", skills)

    def test_archetype_primary_skill_single_backtick_row(self):
        skills = retrieve_mod.archetype_primary_skill(self.tmp, "QA Architect")
        self.assertEqual(skills, ["evidence-based-qa"])

    def test_static_skill_map_lookup_uses_primary(self):
        # Query token "architecture" overlaps the primary skill id.
        results = retrieve_mod.static_skill_map_lookup(
            "architecture decisions review", self.tmp, top_k=5
        )
        slugs = {r["slug"] for r in results}
        self.assertIn("architecture-decisions", slugs)
        # The secondary must NOT be mislabeled as VP Engineering's primary.
        for r in results:
            if r["slug"] == "incremental-refactoring":
                self.assertNotEqual(r.get("archetype"), "VP Engineering")


if __name__ == "__main__":
    unittest.main()
