"""M-13 fold: smart-loading-resolver._load_skill_root caching — call-count spy.

PLAN-086 Wave H AC H.1 + H.2.

H.1  Second resolve() does NOT re-invoke _load_skill_root (delta == 0).
H.2  Cache invalidated on skill_root mtime change; subsequent call invokes.

Deterministic spy via unittest.mock.patch — NO timing assertions (M-13).
"""

from __future__ import annotations

import importlib.util as _ilu
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parents[2]
_SCRIPTS_DIR = _REPO_ROOT / ".claude" / "scripts"

_spec = _ilu.spec_from_file_location(
    "smart_loading_resolver",
    str(_SCRIPTS_DIR / "smart-loading-resolver.py"),
)
assert _spec is not None and _spec.loader is not None
slr = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(slr)

_CAP_TABLE_PATH = _SCRIPTS_DIR.parent / "policies" / "smart-loading-cap-table.yaml"


def _make_minimal_skill_md(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n"
        "name: test-skill\n"
        "priority: 5\n"
        "risk_class: medium\n"
        "domain: core\n"
        "context_budget_tokens: 500\n"
        "inactive_but_retained: false\n"
        "repo_profile_binding:\n"
        "  frontend: {active: true, priority: 5}\n"
        "  engine: {active: true, priority: 5}\n"
        "  fintech: {active: true, priority: 5}\n"
        "  trading-readonly: {active: true, priority: 5}\n"
        "  generic: {active: true, priority: 5}\n"
        "---\n\n"
        "Skill body content.\n",
        encoding="utf-8",
    )


class TestSmartLoadingCacheHit(unittest.TestCase):
    """H.1 — second resolve() does NOT re-invoke _load_skill_root."""

    def setUp(self) -> None:
        slr._skill_root_cache = None
        slr._cache_key = None

    def tearDown(self) -> None:
        slr._skill_root_cache = None
        slr._cache_key = None

    def test_second_resolve_hits_cache(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            skill_root = Path(td) / "skills"
            _make_minimal_skill_md(skill_root / "core" / "test-skill" / "SKILL.md")
            profile_file = Path(td) / "repo-profile.yaml"
            profile_file.write_text("risk_class: frontend\n", encoding="utf-8")

            with patch.object(slr, "_load_skill_root", wraps=slr._load_skill_root) as mock_load:
                slr.resolve(
                    profile_path=profile_file,
                    skill_root=skill_root,
                    cap_table_path=_CAP_TABLE_PATH,
                )
                count_first = mock_load.call_count
                slr.resolve(
                    profile_path=profile_file,
                    skill_root=skill_root,
                    cap_table_path=_CAP_TABLE_PATH,
                )
                count_second = mock_load.call_count

        self.assertEqual(count_first, 1)
        self.assertEqual(count_second - count_first, 0, f"H.1 FAIL: delta={count_second - count_first}")


class TestSmartLoadingCacheInvalidation(unittest.TestCase):
    """H.2 — cache invalidated on skill_root mtime change."""

    def setUp(self) -> None:
        slr._skill_root_cache = None
        slr._cache_key = None

    def tearDown(self) -> None:
        slr._skill_root_cache = None
        slr._cache_key = None

    def test_mtime_change_invalidates_cache(self) -> None:
        import os
        with tempfile.TemporaryDirectory() as td:
            skill_root = Path(td) / "skills"
            _make_minimal_skill_md(skill_root / "core" / "test-skill" / "SKILL.md")
            profile_file = Path(td) / "repo-profile.yaml"
            profile_file.write_text("risk_class: frontend\n", encoding="utf-8")

            with patch.object(slr, "_load_skill_root", wraps=slr._load_skill_root) as mock_load:
                slr.resolve(
                    profile_path=profile_file,
                    skill_root=skill_root,
                    cap_table_path=_CAP_TABLE_PATH,
                )
                count_first = mock_load.call_count

                # Invalidate by bumping skill_root mtime (M-13: cache key is
                # `(mtime_ns, inode)` on skill_root itself; production paths
                # that add/remove DIRECT children of skill_root update its
                # mtime naturally. Subdir-only changes do NOT — that is the
                # documented cache semantics).
                st = skill_root.stat()
                os.utime(skill_root, ns=(st.st_atime_ns, st.st_mtime_ns + 1_000_000_000))

                slr.resolve(
                    profile_path=profile_file,
                    skill_root=skill_root,
                    cap_table_path=_CAP_TABLE_PATH,
                )
                count_after = mock_load.call_count

        self.assertEqual(count_first, 1)
        self.assertGreaterEqual(count_after - count_first, 1, "H.2 FAIL: cache not invalidated")


if __name__ == "__main__":
    unittest.main()
