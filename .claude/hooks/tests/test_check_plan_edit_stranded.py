"""PLAN-065 §4.4.B — stranded-plan detection unit tests.

Tests target the STAGED replacement at
``.claude/plans/PLAN-065/staged-patches/phase-4-b-stranded/check_plan_edit.py.new``
**before** the canonical ceremony (so coverage starts in the same
session that authors the patch). Once the staged `.new` file is
promoted to canonical via Owner-signed sentinel + GPG, this test
file's loader fallback will pick the canonical path automatically.

Stranded modes per PLAN-065 §4.4.B:

- **Mode 8.2 paperclip** — ``status: executing`` with no commit
  touching the plan in >24h. Hook surfaces breadcrumb.
- **Mode 8.1 todo-dispatch-failed** — ``status: reviewed`` with
  ``reviewed_at`` >7d. Hook surfaces breadcrumb.

Real-fs invariant per S7/U7: every test synthesizes plan files
inside ``TestEnvContext.project_dir`` and (when needed) initializes
a real git repo via ``subprocess`` so ``git log`` returns a
deterministic timestamp. No mocks.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import time
import unittest
from pathlib import Path

from _lib.testing import TestEnvContext  # noqa: E402

# Loader: prefer the canonical hook (`check_plan_edit`) when it
# already contains `detect_stranded`; otherwise fall back to the
# STAGED replacement at the PLAN-065 staged-patches path. This
# matches PLAN-019 P1-SEC-D loader pattern + the canonical-edit
# sentinel discipline (the test stays green across the ceremony).

_REPO = Path(__file__).resolve().parents[3]
_STAGED = (
    _REPO / ".claude" / "plans" / "PLAN-065" / "staged-patches"
    / "phase-4-b-stranded" / "check_plan_edit.py.new"
)
_CANONICAL = _REPO / ".claude" / "hooks" / "check_plan_edit.py"


def _load_module():
    # Try canonical first.
    try:
        import check_plan_edit as canonical  # type: ignore
        if hasattr(canonical, "detect_stranded"):
            return canonical
    except Exception:
        pass
    # Fall back to staged .new file.
    # Use SourceFileLoader directly because spec_from_file_location's
    # default loader chain rejects ``.new`` suffixes on Py3.9.
    from importlib.machinery import SourceFileLoader
    loader = SourceFileLoader("check_plan_edit_staged", str(_STAGED))
    spec = importlib.util.spec_from_loader("check_plan_edit_staged", loader)
    if spec is None:  # pragma: no cover
        raise ImportError(f"cannot load staged module from {_STAGED}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules["check_plan_edit_staged"] = mod
    loader.exec_module(mod)
    return mod


cpe = _load_module()


_NOW = 1_750_000_000  # frozen reference unix-ts (~2025-06-15 UTC)
_DAY = 86400


def _iso(unix_ts: int) -> str:
    """Render a unix timestamp as full ISO 8601 UTC (Z-suffix).

    Uses datetime-precision (not date-only) so boundary tests can hit
    the exact threshold seconds — date-only collapses to 00:00 UTC and
    smudges the age computation by up to 24h.
    """
    import datetime as _dt
    return _dt.datetime.fromtimestamp(unix_ts, tz=_dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _make_plan(
    plans_dir: Path,
    plan_id: str,
    status: str,
    *,
    reviewed_at: str = "",
    last_commit_at: str = "",
    related_commits: str = "[]",
    extra_fm: str = "",
) -> Path:
    """Write a synthetic PLAN-NNN-test.md under plans_dir."""
    fm_lines = [
        "---",
        f"id: {plan_id}",
        f"title: Test {plan_id}",
        f"status: {status}",
        "created: 2026-04-12",
        "owner: CEO",
        "depends_on: []",
        f"related_commits: {related_commits}",
    ]
    if reviewed_at:
        fm_lines.append(f"reviewed_at: {reviewed_at}")
    if last_commit_at:
        fm_lines.append(f"last_commit_at: {last_commit_at}")
    if extra_fm:
        fm_lines.append(extra_fm)
    fm_lines.append("---")
    body = "\n## Context\nTest body.\n"
    text = "\n".join(fm_lines) + body
    path = plans_dir / f"{plan_id}-test.md"
    path.write_text(text, encoding="utf-8")
    return path


class _StrandedBase(TestEnvContext):
    """Shared setup: an isolated .claude/plans/ dir + helpers."""

    def setUp(self) -> None:
        super().setUp()
        self.plans_dir = self.project_dir / ".claude" / "plans"
        self.plans_dir.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------
# Mode 8.1 — reviewed >7d → stranded; <7d / no-reviewed_at → not stranded
# ---------------------------------------------------------------------


class TestMode_8_1_DispatchFailed(_StrandedBase):
    """Plan with ``status: reviewed`` and stale ``reviewed_at``."""

    def test_reviewed_more_than_7d_is_stranded(self):
        """8 days old → mode 8.1."""
        old_iso = _iso(_NOW - 8 * _DAY)
        _make_plan(self.plans_dir, "PLAN-901", "reviewed", reviewed_at=old_iso)
        results = cpe.detect_stranded(self.plans_dir, now_unix=_NOW)
        self.assertEqual(len(results), 1)
        s = results[0]
        self.assertEqual(s.plan_id, "PLAN-901")
        self.assertEqual(s.mode, "8.1")
        self.assertEqual(s.status, "reviewed")
        self.assertGreaterEqual(s.age_days, 8)

    def test_reviewed_exactly_7d_is_not_stranded(self):
        """Threshold is strict ``> 7d`` (mirror of 24h boundary)."""
        boundary_iso = _iso(_NOW - 7 * _DAY)
        _make_plan(self.plans_dir, "PLAN-902", "reviewed", reviewed_at=boundary_iso)
        results = cpe.detect_stranded(self.plans_dir, now_unix=_NOW)
        self.assertEqual(results, [])

    def test_reviewed_less_than_7d_is_not_stranded(self):
        """Fresh dispatch — 3 days old."""
        fresh_iso = _iso(_NOW - 3 * _DAY)
        _make_plan(self.plans_dir, "PLAN-903", "reviewed", reviewed_at=fresh_iso)
        results = cpe.detect_stranded(self.plans_dir, now_unix=_NOW)
        self.assertEqual(results, [])

    def test_reviewed_without_reviewed_at_is_skipped(self):
        """No ``reviewed_at`` field → cannot decide → fail-open skip."""
        _make_plan(self.plans_dir, "PLAN-904", "reviewed", reviewed_at="")
        results = cpe.detect_stranded(self.plans_dir, now_unix=_NOW)
        self.assertEqual(results, [])


# ---------------------------------------------------------------------
# Mode 8.2 — executing, no commit in >24h
# ---------------------------------------------------------------------


class TestMode_8_2_Paperclip(_StrandedBase):
    """Plan with ``status: executing`` and stale last commit.

    Mode 8.2 priority: when both conditions could match, only 8.2
    is reported (an executing plan is never simultaneously 8.1).
    """

    def test_executing_more_than_24h_is_stranded_via_frontmatter_override(self):
        """``last_commit_at`` overrides git-log query (S7/U7 testability)."""
        old_iso = _iso(_NOW - 30 * 3600)  # 30 hours ago
        _make_plan(
            self.plans_dir,
            "PLAN-911",
            "executing",
            reviewed_at=_iso(_NOW - 40 * 3600),
            last_commit_at=old_iso,
            related_commits="[abc123]",
        )
        results = cpe.detect_stranded(self.plans_dir, now_unix=_NOW)
        self.assertEqual(len(results), 1)
        s = results[0]
        self.assertEqual(s.plan_id, "PLAN-911")
        self.assertEqual(s.mode, "8.2")
        self.assertEqual(s.status, "executing")
        self.assertGreaterEqual(s.age_days, 1)

    def test_executing_exactly_24h_is_not_stranded(self):
        """Boundary: strict ``> 24h`` per ``_STRANDED_EXECUTING_MAX_AGE_SECS``."""
        boundary_iso = _iso(_NOW - 24 * 3600)
        _make_plan(
            self.plans_dir,
            "PLAN-912",
            "executing",
            reviewed_at=_iso(_NOW - 30 * 3600),
            last_commit_at=boundary_iso,
            related_commits="[abc123]",
        )
        results = cpe.detect_stranded(self.plans_dir, now_unix=_NOW)
        self.assertEqual(results, [])

    def test_executing_less_than_24h_is_not_stranded(self):
        """Fresh commit — 6 hours ago."""
        fresh_iso = _iso(_NOW - 6 * 3600)
        _make_plan(
            self.plans_dir,
            "PLAN-913",
            "executing",
            reviewed_at=_iso(_NOW - 8 * 3600),
            last_commit_at=fresh_iso,
            related_commits="[abc123]",
        )
        results = cpe.detect_stranded(self.plans_dir, now_unix=_NOW)
        self.assertEqual(results, [])

    def test_executing_with_frontmatter_override_takes_priority_over_git(self):
        """Even with a real git repo, ``last_commit_at`` wins.

        Initialize a real git repo, commit the plan file (so
        ``git log`` would return ~now), but set ``last_commit_at``
        to 30h ago in the frontmatter — must report 8.2 stranded.
        """
        # Real-fs git init
        try:
            subprocess.run(
                ["git", "init", "-q"], cwd=str(self.project_dir),
                check=True, timeout=5.0, capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.email", "test@example.com"],
                cwd=str(self.project_dir), check=True, timeout=5.0, capture_output=True,
            )
            subprocess.run(
                ["git", "config", "user.name", "test"],
                cwd=str(self.project_dir), check=True, timeout=5.0, capture_output=True,
            )
        except (subprocess.SubprocessError, FileNotFoundError) as e:
            self.skipTest(f"git unavailable: {e}")

        old_iso = _iso(_NOW - 30 * 3600)
        plan_path = _make_plan(
            self.plans_dir,
            "PLAN-914",
            "executing",
            reviewed_at=_iso(_NOW - 40 * 3600),
            last_commit_at=old_iso,  # this WINS
            related_commits="[abc123]",
        )
        # Add + commit so git log would return current ts
        subprocess.run(
            ["git", "add", str(plan_path.relative_to(self.project_dir))],
            cwd=str(self.project_dir), check=True, timeout=5.0, capture_output=True,
        )
        subprocess.run(
            ["git", "commit", "-q", "-m", "initial"],
            cwd=str(self.project_dir), check=True, timeout=5.0, capture_output=True,
        )

        # detect_stranded should pick last_commit_at (frontmatter) and
        # report 8.2 stranded despite the fresh git commit.
        results = cpe.detect_stranded(
            self.plans_dir, now_unix=_NOW, repo_root=self.project_dir,
        )
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].mode, "8.2")
        self.assertEqual(results[0].plan_id, "PLAN-914")


# ---------------------------------------------------------------------
# Fail-open invariant — corrupt plan file must not block detection
# ---------------------------------------------------------------------


class TestFailOpen(_StrandedBase):
    """Hook fail-open contract: never block on stranded-detection bugs."""

    def test_corrupt_plan_file_is_skipped_other_plans_still_walked(self):
        """A non-decodable / corrupt plan should not abort the walk."""
        # Write a deliberately-bad plan (binary garbage)
        bad = self.plans_dir / "PLAN-995-broken.md"
        bad.write_bytes(b"\x00\xff\x00\xff--- not a valid plan ---")
        # And one valid stranded plan
        _make_plan(
            self.plans_dir, "PLAN-996", "reviewed",
            reviewed_at=_iso(_NOW - 9 * _DAY),
        )
        # Must not raise; must still find PLAN-996
        results = cpe.detect_stranded(self.plans_dir, now_unix=_NOW)
        ids = [r.plan_id for r in results]
        self.assertIn("PLAN-996", ids)


if __name__ == "__main__":
    unittest.main()
